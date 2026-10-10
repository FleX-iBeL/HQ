"""A3 headless test: a call with the real Claude (the workspace), no microphone.

Same fake microphone as test_turn.py (Kokoro speaks the question, fed in at real-time
pace). The call runs in test mode: the policy refuses every file change and every git
command, even ones a real call may do, and the after-call work is a dry run. The
transcript goes to a scratch folder and is deleted at the end (keep it with --keep).

    .venv/bin/python app/test_a3.py              # all four: a, b, c, d
    .venv/bin/python app/test_a3.py --only a     # just the calendar question

  a  a question that needs a tool (the calendar, read-only): time to the filler and to
     the first real words; a filler played
  b  the permission flow: something that needs a yes, answered "no": not done
  c  cutting in while a tool runs
  d  the transcript is written; the dry after-call work changes nothing in git

Uses about six turns of the Max plan.
"""
from __future__ import annotations

import argparse
import asyncio
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brain as _brain  # noqa: F401  (clears API key variables first)
import config

import numpy as np
import soxr
from kokoro_onnx import Kokoro
from loguru import logger

from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.workers.runner import WorkerRunner

from call import Call
from pipeline import build_pipeline
from test_turn import SR, AudioFeeder, Tap, fmt, wait_for

Q_CALENDAR = "Hey Jarvis, what's on my calendar tomorrow?"
Q_PERMISSION = "Jarvis, please put a new event in my calendar tomorrow at noon, called test call."
A_NO = "No, don't."
Q_TOOL_LONG = "Jarvis, can you search my email for the latest message from my bank?"
CUT_IN = "Wait, stop for a second."


def git_status() -> str:
    return subprocess.run(
        ["git", "status", "--porcelain"], cwd=config.FOLDER, capture_output=True, text=True
    ).stdout


async def main(args) -> bool:
    only = set(args.only.split(",")) if args.only else {"a", "b", "c", "d"}
    print(f"== Jarvis VA A3 test · brain {config.MODEL_ALIASES.get(args.model, args.model)} · parts {sorted(only)}")
    status_before = git_status()
    calls_dir = Path(tempfile.mkdtemp(prefix="jarvis-a3-"))

    kokoro = Kokoro(str(config.KOKORO_MODEL), str(config.KOKORO_VOICES))

    def _speak16(text: str) -> np.ndarray:
        audio, sr = kokoro.create(text, voice=config.VOICE, speed=1.0, lang="en-us")
        return soxr.resample(audio.astype(np.float32), sr, SR)

    async def speak16(text: str) -> np.ndarray:
        return await asyncio.to_thread(_speak16, text)

    call = Call(model=args.model, calls_dir=calls_dir, wrap_up="dry", test_mode=True)
    t = time.perf_counter()
    await call.warm()
    info = call.brain.init_info or {}
    print(f"warm-up {time.perf_counter() - t:.1f}s (Claude primed in {call.prime_s or 0:.1f}s)")
    print("connectors:", ", ".join(f"{s['name']} ({s['status']})" for s in await call.brain.connectors()) or "none")
    print("skills:", ", ".join(info.get("skills", [])))

    mic = AudioFeeder()
    after_stt, after_llm, after_tts = Tap("after_stt"), Tap("after_llm"), Tap("after_tts")
    pipeline, _ = build_pipeline(
        source=mic, sink=Tap("sink"), stt=call.stt, llm=call.llm, tts=call.tts, fillers=call.fillers,
        taps={"after_stt": after_stt, "after_llm": after_llm, "after_tts": after_tts},
    )
    worker = PipelineWorker(pipeline, params=PipelineParams(enable_metrics=True))
    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)
    run = asyncio.create_task(runner.run())
    await asyncio.sleep(1.0)
    await wait_for(lambda: call.fillers._ready.is_set(), 20, "the fillers to be recorded")

    llm = call.llm
    results: dict[str, bool] = {}

    async def say_and_wait(q: str, label: str, timeout=90) -> dict:
        print(f"\n-- {label}: saying: {q}")
        n = len(llm.turns)
        mic.say(await speak16(q))
        await wait_for(lambda: mic.speech_end is not None, 30, "the question to be spoken")
        end = mic.speech_end
        await wait_for(lambda: len(llm.turns) > n and after_llm.first("llm_end", end)[0] is not None
                       and not llm._replying, timeout, "Claude's reply")
        t_end = after_llm.all("llm_end", end)[-1][0]
        await wait_for(lambda: not call.fillers.talking and after_tts.first("tts_stopped", t_end)[0] is not None, 30, "the voice to finish")
        await asyncio.sleep(0.5)
        turn = llm.turns[-1]
        t_txt, _ = after_llm.first("llm_text", end)
        t_aud, _ = after_tts.first("audio", end)
        fill = [(ts, txt) for ts, txt in call.fillers.played if ts >= end]
        r = {
            "turn": turn,
            "filler": (fill[0][0] - end) if fill else None,
            "filler_text": [f[1] for f in fill],
            "first_text": None if t_txt is None else t_txt - end,
            "first_audio": None if t_aud is None else t_aud - end,
            "heard": " ".join(v for _, v in after_stt.all("transcript", end - 30)),
        }
        print(f"   Claude got: {turn['sent']!r}")
        print(f"   Jarvis said: {turn['reply'].strip()!r}")
        print(f"   tools: {[n for _, n in turn['tools']]} | fillers: {r['filler_text']}")
        print(f"   after he stopped: filler {fmt(r['filler'])} s | first real words (text) {fmt(r['first_text'])} s"
              f" | first real audio {fmt(r['first_audio'])} s | Claude's own first text {fmt(turn['first_text_s'])} s from sending")
        return r

    try:
        if "a" in only:
            r = await say_and_wait(Q_CALENDAR, "a · calendar question")
            cal = [(tool, d.verdict) for tool, _, d in call.policy.log if "Calendar" in tool]
            print(f"   calendar calls: {cal}")
            results["a"] = bool(r["filler_text"]) and r["first_audio"] is not None and any(v == "allow" for _, v in cal)

        if "b" in only:
            log_start = len(call.policy.log)
            r1 = await say_and_wait(Q_PERMISSION, "b · something that needs a yes")
            asked = [(t, d.verdict) for t, _, d in call.policy.log[log_start:] if d.verdict == "ask"]
            print(f"   asked about: {asked} | pending: {[q for _, _, q in call.policy.pending]}")
            r2 = await say_and_wait(A_NO, "b · answering no")
            creates = [(t, d.verdict, d.why) for t, _, d in call.policy.log[log_start:] if "create_event" in t]
            print(f"   create_event decisions: {creates}")
            results["b"] = (
                bool(asked)
                and "not approved" in r2["turn"]["sent"]
                and not any(v == "allow" for _, v, _ in creates)
                and not call.policy.pending
            )

        if "c" in only:
            print(f"\n-- c · cutting in while a tool runs: saying: {Q_TOOL_LONG}")
            n = len(llm.turns)
            ints_before = call.brain.interrupts_sent
            mic.say(await speak16(Q_TOOL_LONG))
            await wait_for(lambda: mic.speech_end is not None, 30, "the question to be spoken")
            await wait_for(lambda: len(llm.turns) > n and llm.turns[-1]["tools"]
                           and any(x[1].startswith("mcp__") for x in llm.turns[-1]["tools"]), 60, "a tool call")
            i_cut = len(llm.turns) - 1
            cut_audio = await speak16(CUT_IN)
            t_cut = time.perf_counter()
            print(f"   tool started: {llm.turns[i_cut]['tools']}; cutting in: {CUT_IN}")
            mic.say(cut_audio)
            await wait_for(lambda: after_llm.first("interruption", t_cut)[0] is not None, 15, "the interruption")
            t_int, _ = after_llm.first("interruption", t_cut)
            await wait_for(lambda: len(llm.turns) > i_cut + 1 and not llm._replying
                           and after_llm.first("llm_end", t_int + 0.5)[0] is not None, 90, "the follow-up reply")
            await wait_for(lambda: not call.fillers.talking and after_tts.first("tts_stopped", t_int)[0] is not None, 30, "the voice")
            await asyncio.sleep(0.5)
            t1, t2 = llm.turns[i_cut], llm.turns[-1]
            print(f"   the tool reply was stopped: {t1['interrupted']} | interrupts sent: {call.brain.interrupts_sent - ints_before}")
            print(f"   follow-up sent to Claude: {t2['sent']!r}")
            print(f"   follow-up reply: {t2['reply'].strip()!r}")
            results["c"] = t1["interrupted"] and call.brain.interrupts_sent > ints_before and bool(t2["reply"].strip())
    finally:
        await worker.cancel()
        try:
            await asyncio.wait_for(run, 10)
        except Exception:
            pass

    # d: the transcript, then the (dry) after-call work, then git must be unchanged.
    path = call.transcript.path
    await call.finish()
    text = path.read_text() if path.exists() else ""
    print(f"\n-- d · transcript {path.name}:\n{text}")
    print(f"   after-call work (dry run) said: {call.wrap_up_reply!r}")
    status_after = git_status()
    if "d" in only:
        results["d"] = (
            f"**{config.USER_LABEL}:**" in text and "**Jarvis:**" in text and "Ended" in text
            and ("filler" in text or "a" not in only)
            and status_after == status_before
        )
    print(f"   git status unchanged: {status_after == status_before}")
    if not args.keep:
        shutil.rmtree(calls_dir, ignore_errors=True)
    print("\n== results:", ", ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in sorted(results.items())))
    return all(results.values())


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="sonnet")
    p.add_argument("--only", default="")
    p.add_argument("--keep", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args()
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if a.verbose else "WARNING")
    sys.exit(0 if asyncio.run(main(a)) else 1)
