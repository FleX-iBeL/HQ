"""Fillers: "Let me check." while Claude is still thinking, "On it, one second." while a
tool runs. An idea of 8 October 2026: "maybe if claude has to think, it can
first say let me check, or something?"

The FillerPlayer sits right after the voice (Kokoro), just before the audio goes out. At
call start it records every filler once with Kokoro, so a filler plays instantly. The
Claude step (claude_llm.py) decides when a filler is due and calls say(); the player
plays it only when Jarvis isn't already talking, and rotates through the list.

Fillers are not Claude's words: they don't go into the Claude session or into Pipecat's
context, and the transcript marks them as filler. When the user cuts in, the output drops
the filler audio like any other audio (the frames are interruptible).
"""
from __future__ import annotations

import asyncio
import hashlib
import random
import threading
import time

import numpy as np
import soxr
from loguru import logger

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    InterruptionFrame,
    SpeechOutputAudioRawFrame,
    StartFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

import config

CHUNK_SECS = 0.02

# Recorded lines are kept for good (in memory and in scratch/fillers on disk), per voice and
# sample rate, so each line is recorded once, not at every call. One recording at a time: when
# every call re-recorded all its lines, back-to-back calls piled up and starved the live voice
# (9 October 2026, "suddenly it stopped working").
_CACHE: dict[tuple[str, int, str], bytes] = {}
_CACHE_DIR = config.ROOT / "scratch" / "fillers"
_RENDER_LOCK = threading.Lock()
TAIL_SILENCE_SECS = 0.45  # lets the output notice the filler ended (it waits 0.35 s)


class FillerPlayer(FrameProcessor):
    def __init__(self, kokoro, *, voice: str = config.VOICE, on_play=None, waiting_lines: bool = True):
        super().__init__(name="FillerPlayer")
        self.waiting_lines = waiting_lines  # H1: off = only the greeting, no lines while she works
        self._kokoro = kokoro
        self._voice = voice
        self._texts = {"greeting": config.greetings_now(), "wait": list(config.FILLERS), **{k: list(v) for k, v in config.TOOL_FILLERS.items()}}
        self._rotation = {k: 0 for k in self._texts}  # (not _next: FrameProcessor uses that name)
        self._last: str | None = None
        self._audio: dict[str, bytes] = {}
        self._sample_rate: int | None = None
        self._ready = asyncio.Event()
        self._greet_ready = asyncio.Event()
        self._render_task: asyncio.Task | None = None
        self._sample_rate_hint: int | None = None
        self.on_play = on_play  # called with the filler text when one plays (transcript)
        self.bot_speaking = False
        self.last_bot_stop = 0.0  # perf_counter time Jarvis last went quiet
        self.played: list[tuple[float, str]] = []  # for tests
        self._filler_until = 0.0  # a filler just sent counts as talking until it has played

    # -- recording the fillers once --------------------------------------------

    def _render(self, text: str, sample_rate: int) -> bytes:
        key = (self._voice, sample_rate, text)
        if key in _CACHE:
            return _CACHE[key]
        name = hashlib.sha1(f"{self._voice}|{sample_rate}|{text}".encode()).hexdigest()[:16]
        path = _CACHE_DIR / self._voice / f"{name}.pcm"
        if path.exists():
            _CACHE[key] = path.read_bytes()
            return _CACHE[key]
        with _RENDER_LOCK:
            audio, sr = self._kokoro.create(text, voice=self._voice, speed=1.0, lang=config.voice_lang(self._voice))
        audio = soxr.resample(audio.astype(np.float32), sr, sample_rate)
        pcm = (np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(pcm)
        except OSError:
            pass
        _CACHE[key] = pcm
        return pcm

    async def prepare(self, sample_rate: int) -> float:
        """Record the lines one by one: first one of each kind (so every kind works within a
        few seconds of the call starting), then the rest. say() only uses recorded lines."""
        t = time.perf_counter()
        self._sample_rate = sample_rate
        greeting = self._texts["greeting"]
        first = [texts[0] for k, texts in self._texts.items() if k != "greeting"]
        rest = [x for k, texts in self._texts.items() for x in (texts if k == "greeting" else texts[1:])
                if x != greeting[0]]
        order = [greeting[0]] + first + rest
        for i, text in enumerate(order):
            if text not in self._audio:
                self._audio[text] = await asyncio.to_thread(self._render, text, sample_rate)
            if i == 0:
                self._greet_ready.set()
            if i == len(first):
                self._ready.set()
        self._ready.set()
        return time.perf_counter() - t

    # -- frames -----------------------------------------------------------------

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, StartFrame) and not self._render_task:
            rate = self._sample_rate_hint or 24000
            self._render_task = self.create_task(self._prepare_logged(rate), "filler-render")
        elif isinstance(frame, InterruptionFrame):
            self._filler_until = 0.0  # the output drops what was still queued
        elif isinstance(frame, BotStartedSpeakingFrame):
            self.bot_speaking = True
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self.bot_speaking = False
            self.last_bot_stop = time.perf_counter()
        await self.push_frame(frame, direction)

    async def setup(self, setup):
        await super().setup(setup)
        self._sample_rate_hint = getattr(setup, "audio_out_sample_rate", None)

    async def _prepare_logged(self, rate: int):
        try:
            s = await self.prepare(rate)
            logger.info(f"Fillers recorded in {s:.2f}s ({len(self._audio)} of them)")
        except Exception as e:
            logger.warning(f"Fillers could not be recorded: {e}")

    # -- playing ----------------------------------------------------------------

    async def greet(self, delay: float = 0.6, timeout: float = 10.0) -> str | None:
        """Open the call: as soon as the greeting is recorded and the line is up."""
        try:
            await asyncio.wait_for(self._greet_ready.wait(), timeout)
        except asyncio.TimeoutError:
            return None
        await asyncio.sleep(delay)
        return await self.say("greeting")

    def silent_for(self, since: float) -> float:
        """Seconds Jarvis has been quiet, counting from `since` at the earliest."""
        now = time.perf_counter()
        if self.talking:
            return 0.0
        return now - max(self.last_bot_stop, self._filler_until, since)

    @property
    def talking(self) -> bool:
        return self.bot_speaking or time.perf_counter() < self._filler_until

    async def say(self, kind: str = "wait") -> str | None:
        """Play the next filler of this kind right now. Returns its text, or None if it
        didn't play (Jarvis is talking, or the fillers aren't recorded yet)."""
        if kind != "greeting" and not self.waiting_lines:
            return None
        ready = self._greet_ready if kind == "greeting" else self._ready
        if self.talking or not ready.is_set():
            return None
        texts = [t for t in self._texts.get(kind) or self._texts["tool"] if t in self._audio]
        if len(texts) > 1 and self._last in texts:
            texts.remove(self._last)  # never the same line twice in a row
        if not texts:
            return None
        text = random.choice(texts)  # a person doesn't say them in a fixed order
        self._last = text
        audio = self._audio.get(text)
        if not audio:
            return None
        rate = self._sample_rate
        step = int(rate * CHUNK_SECS) * 2  # bytes per 20 ms of 16-bit mono
        self._filler_until = time.perf_counter() + len(audio) / 2 / rate
        audio += b"\x00" * (int(rate * TAIL_SILENCE_SECS) * 2)
        for i in range(0, len(audio), step):
            await self.push_frame(
                SpeechOutputAudioRawFrame(audio=audio[i : i + step], sample_rate=rate, num_channels=1)
            )
        self.played.append((time.perf_counter(), text))
        if self.on_play:
            try:
                self.on_play(text)
            except Exception:
                pass
        logger.info(f"Filler: {text}")
        return text
