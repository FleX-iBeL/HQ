"""H3: what is Jarvis doing right now? Sent to the call page so the user can see it.

States: "listening" (your turn), "hearing" (you are talking), "thinking" (working on the answer),
"speaking". H11/H12, both shown in yellow: "transcribing" (he let go of the talk button and his last
words are still being turned into text) and "waiting" (a pause in free talking: she waits a moment
longer, in case he goes on). Two small pass-through processors (StateTap) feed one shared CallState; every change
is sent once, as {"type": "jarvis-state", "state": ...}, over the call's data channel.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Callable

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    InterruptionFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TranscriptionFrame,
    TTSStartedFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

NO_REPLY_SECS = 10.0  # he stopped talking and nothing at all came of it (a cough): back to listening
QUIET_END_SECS = 2.5  # the reply finished without any sound (bug F4): back to listening


class CallState:
    def __init__(self, send: Callable[[dict], None] | None):
        self._send = send
        self.state = "listening"
        self.history: list[tuple[float, str]] = []  # (time, state), for tests
        self._user_talking = False
        self._bot_speaking = False
        self._llm_active = False
        self._heard_text = False
        self._timer: asyncio.TimerHandle | None = None

    def _set(self, state: str) -> None:
        if state == self.state:
            return
        self.state = state
        self.history.append((time.time(), state))
        if self._send:
            try:
                self._send({"type": "jarvis-state", "state": state})
            except Exception:
                pass

    def _later(self, secs: float, check: Callable[[], None]) -> None:
        if self._timer:
            self._timer.cancel()
        self._timer = asyncio.get_running_loop().call_later(secs, check)

    def _settle(self) -> None:
        """Nothing is happening any more: it is his turn."""
        if not (self._user_talking or self._bot_speaking or self._llm_active):
            self._set("listening")

    def turn_wait(self, kind: str | None) -> None:
        """From the turn logic (pipeline.py): "transcribing", "waiting", or None (he talks again).
        After letting go with nothing said, the current state is sent again, so the page knows."""
        if not self._user_talking:
            if kind is None and self._send:
                try:
                    self._send({"type": "jarvis-state", "state": self.state})
                except Exception:
                    pass
            return
        self._set(kind or "hearing")

    def cancelled(self) -> None:
        """H31: he tapped Cancel while she was thinking: the turn is dropped, it is his turn."""
        self._llm_active = False
        self._bot_speaking = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        self._set("listening")

    def on_frame(self, frame: Frame) -> None:
        if isinstance(frame, (UserStartedSpeakingFrame, InterruptionFrame)):
            self._user_talking = isinstance(frame, UserStartedSpeakingFrame) or self._user_talking
            self._bot_speaking = False
            self._heard_text = False
            if isinstance(frame, UserStartedSpeakingFrame):
                self._set("hearing")
        elif isinstance(frame, UserStoppedSpeakingFrame):
            self._user_talking = False
            self._heard_text = False
            self._set("thinking")
            self._later(NO_REPLY_SECS, lambda: self._settle() if not self._heard_text else None)
        elif isinstance(frame, TranscriptionFrame):
            self._heard_text = True
            if not self._user_talking:
                self._set("thinking")
        elif isinstance(frame, LLMFullResponseStartFrame):
            self._llm_active = True
            if not self._bot_speaking:
                self._set("thinking")
        elif isinstance(frame, (BotStartedSpeakingFrame, TTSStartedFrame)):
            self._bot_speaking = True
            if not self._user_talking:
                self._set("speaking")
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._bot_speaking = False
            if self._llm_active:
                self._set("thinking")
            else:
                self._settle()
        elif isinstance(frame, LLMFullResponseEndFrame):
            self._llm_active = False
            if not self._bot_speaking:
                self._later(QUIET_END_SECS, self._settle)


class StateTap(FrameProcessor):
    """Passes every frame on unchanged, and tells the shared CallState about it."""

    def __init__(self, state: CallState, **kwargs):
        super().__init__(**kwargs)
        self._call_state = state

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        try:
            self._call_state.on_frame(frame)
        except Exception:
            pass
        await self.push_frame(frame, direction)
