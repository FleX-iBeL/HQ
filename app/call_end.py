"""F59 (28 October 2026): how a call ended, told apart: his button, the agent's goodbye, a drop, or the server.

His words on the call of 26 October 2026 (Moneypenny): "This is twice today, why do our calls keep dropping out?"
Both drops that day were his sound stopping mid-call and the browser closing about 30 seconds later; the
server took every closed connection as a hang-up, so both transcripts said "<name> hung up". Scope, his words
on 28 October 2026: "The whole point is that we know what happened, right?"

One EndWatch per call. The pipeline's first processor (AudioSeen) tells it each time a piece of his audio comes
in (a phone sends packets the whole call, also in a silence; they stop when the app goes to the background or
the network lets go). bot.py tells it the button, the agent's goodbye, the connection closing and the server
stopping. `words()` is the transcript's last line, `log_words()` the call line's log. Only times and which side
are kept: no sound, no words.
"""
from __future__ import annotations

import time
from datetime import datetime

from pipecat.frames.frames import Frame, InputAudioRawFrame
from pipecat.processors.frame_processor import FrameProcessor

# His audio counts as gone quiet first when the last piece came in this many seconds or more before the close.
# Packets come every 20 ms; a phone that's on sends them all the time, so 3 s without one is a real gap.
QUIET_GAP_SECS = 3.0


def _hms(t: float | None) -> str:
    return datetime.fromtimestamp(t).strftime("%H:%M:%S") if t else "?"


class EndWatch:
    def __init__(self, user: str = "Me", clock=time.time):
        self.user = user
        self.clock = clock
        self.started = clock()
        self.last_audio: float | None = None  # wall clock of his last audio piece
        self.how: str | None = None  # button, agent, drop, server (the first one wins)
        self.closed_at: float | None = None
        self.state: str | None = None  # the connection's last state from WebRTC: failed, closed, disconnected

    def connection(self, state: str) -> None:
        """WebRTC's state as the connection went: 'failed' (the network let go: no answer from his side),
        'closed' (his browser closed it), 'disconnected'. Kept for the reason; the first close counts."""
        if self.state is None or self.how is None:
            self.state = state

    def heard(self) -> None:
        self.last_audio = self.clock()

    def _mark(self, how: str) -> bool:
        if self.how is None:
            self.how = how
            self.closed_at = self.clock()
            return True
        return False

    def button(self) -> bool:
        return self._mark("button")

    def agent(self) -> bool:
        return self._mark("agent")

    def closed(self) -> bool:
        """The connection closed. A drop unless the button, the goodbye or the server came first."""
        return self._mark("drop")

    def server(self) -> bool:
        """The call line stopped the call itself (shutting down, a restart) before anything else ended it."""
        return self._mark("server")

    def quiet_first(self) -> str:
        """Which side went quiet first: 'audio' (his sound stopped well before the close), 'network' (it came in
        until the connection failed), 'page' (it came in until his browser closed the connection without the
        button), or 'server'."""
        if self.how == "server":
            return "server"
        end = self.closed_at or self.clock()
        if self.last_audio is None or end - self.last_audio >= QUIET_GAP_SECS:
            return "audio"
        return "page" if self.state == "closed" else "network"

    def reason(self) -> str:
        side = self.quiet_first()
        if side == "server":
            last = f", his audio last came in at {_hms(self.last_audio)}" if self.last_audio else ""
            return f"the server stopped the call at {_hms(self.closed_at)}{last}"
        if side == "audio":
            if self.last_audio is None:
                return f"no audio of his ever came in; the connection closed at {_hms(self.closed_at)}"
            gap = (self.closed_at or self.clock()) - self.last_audio
            how = {"failed": ", the network gave up", "closed": ", his browser closed it"}.get(self.state or "", "")
            return (f"his audio went quiet first, at {_hms(self.last_audio)}, and the connection closed "
                    f"{gap:.0f} s later, at {_hms(self.closed_at)}{how}")
        if side == "page":
            return (f"his page closed the connection at {_hms(self.closed_at)} without the hang-up button; "
                    f"his audio came in until {_hms(self.last_audio)}")
        return (f"the network: his audio came in until {_hms(self.last_audio)} and the connection failed at "
                f"{_hms(self.closed_at)}")

    def is_drop(self) -> bool:
        return self.how in ("drop", "server")

    def words(self, agent_name: str = "") -> str:
        """The transcript's ending line (the caller of this keeps H79's hand-over line before it)."""
        if self.how == "agent":
            return f"{agent_name} hung up after the goodbye"
        if self.is_drop():
            return f"the call dropped ({self.reason()}), not a hang-up"
        return f"{self.user} hung up"

    def log_words(self) -> str:
        if self.how == "button":
            return "The caller hung up (button)"
        if self.how == "agent":
            return "The agent hung up after the goodbye"
        return f"The call dropped: {self.reason()}"


# F59 (job 454): the calls that are on, each with how to end it. A stop of the call line (the stop script's polite
# stop, an update's restart) used to leave a call on: uvicorn waits for the call's request to finish before it shuts
# down, and the forced stop after 60 s is a SIGTERM, which it doesn't treat as forcing. So the stop itself now marks
# every live call as the server's and ends it, and the after-call work runs as after a hang-up.
_live: dict = {}


def live(watch: EndWatch, stop) -> None:
    """A call is on: `stop` is an async function that ends it (the call's worker.cancel)."""
    _live[watch] = stop


def gone(watch: EndWatch) -> None:
    _live.pop(watch, None)


def live_calls() -> int:
    return len(_live)


async def server_stopping(log=None) -> int:
    """The call line is stopping: every call that's on is marked as stopped by the server (unless something ended it
    first) and ended. Returns how many were ended; `log` gets each call's log line."""
    n = 0
    for watch, stop in list(_live.items()):
        if watch.server() and log is not None:
            log(watch.log_words())
        try:
            await stop()
        except Exception:
            pass
        n += 1
    return n


class AudioSeen(FrameProcessor):
    """Right after the transport's input: notes each piece of his audio for the EndWatch, passes everything on."""

    def __init__(self, watch: EndWatch, **kwargs):
        super().__init__(**kwargs)
        self._watch = watch

    async def process_frame(self, frame: Frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, InputAudioRawFrame):
            self._watch.heard()
        await self.push_frame(frame, direction)
