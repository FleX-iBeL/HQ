"""A2 headless test: a whole call without a microphone.

Kokoro speaks a question; the audio is fed into the real call pipeline at real-time pace
(20 ms chunks, silence around it), exactly as the browser would send it. Silero VAD and
smart-turn decide when the turn is over, Whisper hears it, the Claude session answers,
Kokoro speaks. We time it from the moment the spoken question ends.

    .venv/bin/python app/test_turn.py                 # Sonnet: a cold turn, then a warm one
    .venv/bin/python app/test_turn.py --model haiku   # the same with Haiku 4.5
    .venv/bin/python app/test_turn.py --interrupt     # cut in mid-reply, then a follow-up

Uses a few turns on the Max plan per run (two, or two with --interrupt).
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brain as _brain  # noqa: F401  (clears API key variables first)
import config

import numpy as np
import soxr
from kokoro_onnx import Kokoro
from loguru import logger

from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    InputAudioRawFrame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    StartFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    TTSStoppedFrame,
)
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.workers.runner import WorkerRunner

from claude_llm import ClaudeSessionLLMService
from pipeline import build_pipeline, make_brain, make_stt, make_tts, warm_up_tts

SR = 16000
CHUNK = 320  # 20 ms at 16 kHz

QUESTIONS = [
    "Hey there, what's a good way to start a quiet morning? Keep it short.",
    "Nice, and what's one small thing I can do in the evening",
]
LONG_QUESTION = "Hey there, tell me a long story about a lighthouse keeper in at least forty sentences, in several chapters"
CUT_IN = "Wait, stop for a second."


class AudioFeeder(FrameProcessor):
    """Stands in for the browser's microphone: silence, with speech when asked."""

    def __init__(self):
        super().__init__(name="FakeMic")
        self._buf = np.zeros(0, dtype=np.int16)
        self._task = None
        self.speech_end: float | None = None
        self.speech_start: float | None = None

    def say(self, audio16: np.ndarray):
        pcm = (np.clip(audio16, -1, 1) * 32767).astype(np.int16)
        self.speech_end = None
        self.speech_start = None
        self._buf = np.concatenate([self._buf, pcm])

    @property
    def speaking(self) -> bool:
        return len(self._buf) > 0

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, (EndFrame, CancelFrame)) and self._task:
            await self.cancel_task(self._task)
            self._task = None
        await self.push_frame(frame, direction)
        if isinstance(frame, StartFrame) and not self._task:
            self._task = self.create_task(self._feed(), "fake-mic")

    async def _feed(self):
        silence = np.zeros(CHUNK, dtype=np.int16)
        t0 = time.perf_counter()
        n = 0
        while True:
            if len(self._buf):
                if self.speech_start is None:
                    self.speech_start = time.perf_counter()
                chunk, self._buf = self._buf[:CHUNK], self._buf[CHUNK:]
                if len(chunk) < CHUNK:
                    chunk = np.concatenate([chunk, silence[: CHUNK - len(chunk)]])
                if not len(self._buf):
                    self.speech_end = time.perf_counter() + 0.02
            else:
                chunk = silence
            await self.push_frame(InputAudioRawFrame(audio=chunk.tobytes(), sample_rate=SR, num_channels=1))
            n += 1
            delay = t0 + n * 0.02 - time.perf_counter()
            if delay < -0.1:
                # The loop was busy (a model load). A browser doesn't burst a backlog of
                # audio afterwards, so neither do we: start the clock again.
                t0, n = time.perf_counter(), 0
                delay = 0
            await asyncio.sleep(max(0, delay))


class Tap(FrameProcessor):
    """Passes everything through and writes down when interesting frames go by."""

    def __init__(self, name: str):
        super().__init__(name=name)
        self.events: list[tuple[float, str, object]] = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        now = time.perf_counter()
        if isinstance(frame, TranscriptionFrame):
            self.events.append((now, "transcript", frame.text))
        elif isinstance(frame, LLMFullResponseStartFrame):
            self.events.append((now, "llm_start", None))
        elif isinstance(frame, LLMTextFrame):
            self.events.append((now, "llm_text", frame.text))
        elif isinstance(frame, LLMFullResponseEndFrame):
            self.events.append((now, "llm_end", None))
        elif isinstance(frame, TTSAudioRawFrame):
            self.events.append((now, "audio", frame.context_id))
        elif isinstance(frame, TTSStoppedFrame):
            self.events.append((now, "tts_stopped", frame.context_id))
        elif isinstance(frame, InterruptionFrame):
            self.events.append((now, "interruption", None))
        await self.push_frame(frame, direction)

    def first(self, kind: str, after: float):
        for t, k, v in self.events:
            if k == kind and t >= after:
                return t, v
        return None, None

    def all(self, kind: str, after: float = 0.0, before: float = float("inf")):
        return [(t, v) for t, k, v in self.events if k == kind and after <= t < before]


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", "", s.lower()).split())


async def wait_for(cond, timeout: float, what: str):
    t = time.perf_counter()
    while not cond():
        if time.perf_counter() - t > timeout:
            raise TimeoutError(f"timed out waiting for {what}")
        await asyncio.sleep(0.02)


async def main(args):
    model = config.MODEL_ALIASES.get(args.model, args.model)
    print(f"== HQ A2 test · brain {model} · effort {config.EFFORT}")

    kokoro = Kokoro(str(config.KOKORO_MODEL), str(config.KOKORO_VOICES))

    def _speak16(text: str) -> np.ndarray:
        audio, sr = kokoro.create(text, voice=config.VOICE, speed=1.0, lang="en-us")
        return soxr.resample(audio.astype(np.float32), sr, SR)

    async def speak16(text: str) -> np.ndarray:
        return await asyncio.to_thread(_speak16, text)  # keep the fake mic steady

    claude = make_brain(model)
    stt = make_stt()
    tts = make_tts()
    t = time.perf_counter()
    await claude.start()
    w = await asyncio.to_thread(stt.warm_up)
    k = await asyncio.to_thread(warm_up_tts, tts)
    print(f"warm-up: Claude session {time.perf_counter() - t - w - k:.2f}s, Whisper {w:.2f}s, Kokoro {k:.2f}s")

    mic = AudioFeeder()
    after_stt, after_llm, after_tts = Tap("after_stt"), Tap("after_llm"), Tap("after_tts")
    llm = ClaudeSessionLLMService(claude)
    pipeline, aggregators = build_pipeline(
        source=mic,
        sink=Tap("sink"),
        stt=stt,
        llm=llm,
        tts=tts,
        taps={"after_stt": after_stt, "after_llm": after_llm, "after_tts": after_tts},
    )
    worker = PipelineWorker(pipeline, params=PipelineParams(enable_metrics=True))
    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)
    run = asyncio.create_task(runner.run())
    await asyncio.sleep(1.0)  # let the pipeline start and the VAD settle on silence

    results = []
    ok = True
    try:
        if not args.interrupt:
            for i, q in enumerate(QUESTIONS):
                label = "cold (first turn)" if i == 0 else "warm (second turn)"
                r = await one_turn(q, label, speak16, mic, after_stt, after_llm, after_tts, llm)
                results.append(r)
                ok &= r["heard_ok"] and r["first_audio"] is not None
        else:
            ok = await interrupt_test(speak16, mic, after_stt, after_llm, after_tts, llm, claude)
    finally:
        await worker.cancel()
        try:
            await asyncio.wait_for(run, 10)
        except Exception:
            pass
        await claude.stop()

    print("\n== every turn the brain got")
    for i, t in enumerate(llm.turns):
        print(f"  {i}: sent={t['sent']!r} interrupted={t['interrupted']} first_text={t['first_text_s']} reply={t['reply'].strip()[:120]!r}")
    if results:
        print("\n== summary (seconds after the spoken question ended)")
        for r in results:
            print(
                f"{r['label']:<20} heard right: {r['heard_ok']!s:<5} | Claude turns: {r['turns']}"
                f" | last words heard {fmt(r['transcript'])} | brain first text {fmt(r['first_text'])}"
                f" | first audio out {fmt(r['first_audio'])} | last audio made {fmt(r['done'])}"
                f" || Claude alone {fmt(r['claude_first'])} | voice, text to audio {fmt(r['tts_first'])}"
            )
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return ok


def fmt(x):
    return "  -  " if x is None else f"{x:5.2f}"


async def one_turn(q, label, speak16, mic, after_stt, after_llm, after_tts, llm):
    print(f"\n-- {label}: saying: {q}")
    audio = await speak16(q)
    mark = time.perf_counter()
    n_turns = len(llm.turns)
    mic.say(audio)
    await wait_for(lambda: mic.speech_end is not None, 30, "the question to be spoken")
    end = mic.speech_end
    await wait_for(lambda: after_llm.first("llm_end", end)[0] is not None, 60, "Claude's reply")
    await wait_for(lambda: after_tts.first("tts_stopped", end)[0] is not None, 30, "the voice to finish")
    await asyncio.sleep(0.3)

    # the user's question may reach Claude as more than one turn (a pause after the
    # question mark looks like the end of a turn); the answer that counts is the last one.
    starts = after_llm.all("llm_start", mark)
    t_start = starts[-1][0] if starts else end
    t_tr = after_stt.all("transcript", mark)[-1][0] if after_stt.all("transcript", mark) else None
    t_txt, _ = after_llm.first("llm_text", t_start)
    t_aud, _ = after_tts.first("audio", t_start)
    audio = after_tts.all("audio", t_start)
    t_done = audio[-1][0] if audio else None
    new_turns = llm.turns[n_turns:]
    final = new_turns[-1] if new_turns else {}
    heard = " ".join(v for _, v in after_stt.all("transcript", mark))
    print(f"   heard:   {heard}")
    print(f"   Claude got it as {len(new_turns)} turn(s); answered: {final.get('reply', '').strip()}")
    rel = lambda t: None if t is None else t - end  # noqa: E731
    return {
        "label": label,
        "heard_ok": norm(heard) == norm(q),
        "turns": len(new_turns),
        "transcript": rel(t_tr),
        "first_text": rel(t_txt),
        "first_audio": rel(t_aud),
        "done": rel(t_done),
        "claude_first": final.get("first_text_s"),
        "tts_first": None if (t_aud is None or t_txt is None) else t_aud - t_txt,
    }


async def interrupt_test(speak16, mic, after_stt, after_llm, after_tts, llm, claude):
    print(f"\n-- interruption: saying: {LONG_QUESTION}")
    mic.say(await speak16(LONG_QUESTION))
    await wait_for(lambda: mic.speech_end is not None, 30, "the question to be spoken")
    end = mic.speech_end
    await wait_for(lambda: after_tts.first("audio", end)[0] is not None, 60, "the voice to start")
    t_first_audio, ctx = after_tts.first("audio", end)
    # The TTS runs faster than real time and nothing plays it here, so wait a little to
    # be sure Claude is still writing, then cut in by voice.
    await asyncio.sleep(0.6)
    cut_in = await speak16(CUT_IN)
    i_cut = len(llm.turns) - 1  # the reply that is talking now
    print(f"   voice started {t_first_audio - end:.2f}s after the question; cutting in: {CUT_IN}")
    mic.say(cut_in)
    await wait_for(lambda: after_llm.first("interruption", t_first_audio)[0] is not None, 10, "the interruption")
    t_int, _ = after_llm.first("interruption", t_first_audio)
    print(f"   interruption reached Claude's step {t_int - mic.speech_start:.2f}s after the cut-in began")

    # Old reply: no more text from Claude and no more audio from that reply after the cut-in.
    await asyncio.sleep(2.0)
    t1 = llm.turns[i_cut]
    t_next, _ = after_llm.first("llm_start", t_int)
    late_text = after_llm.all("llm_text", t_int + 0.05, t_next or float("inf"))
    late_audio = [t for t, c in after_tts.all("audio", t_int + 0.3) if c == ctx]
    print(f"   first reply interrupted: {t1['interrupted']} | interrupt sent to Claude: {claude.interrupts_sent}"
          f" | Claude's turn ended as: {claude.last_turn.terminal_reason if claude.last_turn else None}")
    print(f"   text of the cut reply: {t1['reply'].strip()!r}")
    print(f"   text after the cut-in from the old reply: {len(late_text)} pieces; audio frames of the old reply after the cut-in: {len(late_audio)}")

    # The cut-in is itself a turn: Claude answers it, knowing it was cut off.
    def answered():
        return [t for t in llm.turns[i_cut + 1:] if t["reply"] and not t["interrupted"]]

    await wait_for(lambda: answered() and after_llm.first("llm_end", mic.speech_end)[0] is not None, 60, "the follow-up reply")
    await wait_for(lambda: after_tts.first("tts_stopped", mic.speech_end)[0] is not None, 30, "the follow-up voice")
    t2 = answered()[0]
    print(f"   follow-up sent to Claude: {t2['sent']!r}")
    print(f"   follow-up reply: {t2['reply'].strip()!r} (first text {t2['first_text_s']:.2f}s)")
    passed = (
        t1["interrupted"]
        and claude.interrupts_sent >= 1
        and not late_audio
        and "cut in" in t2["sent"]
        and bool(t2["reply"].strip())
    )
    return passed


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=config.MODEL)
    p.add_argument("--interrupt", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args()
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if a.verbose else "WARNING")
    sys.exit(0 if asyncio.run(main(a)) else 1)
