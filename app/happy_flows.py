"""The happy flows: the main things a call must do when all goes well (phase G of the roadmap).
Run them before and after every update; they print a short pass/fail table at the end.

    .venv/bin/python app/happy_flows.py                # all ten flows
    .venv/bin/python app/happy_flows.py --quick        # only the flows without Claude turns (1, 8, 9, 10, 15, 16, 18, 19, 20, 21, 23, 25, 26, 27, 28, 29, 30, 31, 33, 34)
    .venv/bin/python app/happy_flows.py --only 3,5     # just these flows
    .venv/bin/python app/happy_flows.py --keep         # keep the scratch folder (server log, transcripts)

  1  the call server starts and the call page loads
  2  the greeting plays first, before the caller says anything, on Quick and on Deep
  3  a plain question gets a spoken answer (time to the first words recorded); the call page
     is told thinking, then speaking (H3; flow 2 checks "your turn" after the greeting)
  4  a calendar question: a waiting line plays, the answer says what's there, read-only
  5  something that needs a yes: she checks it in one sentence; "no" -> nothing is done
  6  cutting in stops her voice, and she answers what was said
  7  hanging up saves the transcript; the (dry) after-call work changes nothing in git
  8  the waiting lines: none start with "Mm", never the same one twice in a row
  9  a restart really restarts, also when the stop step can't see the server (9 Oct 03:10)
  10 the status page reads the roadmap, and the weekly stop lines move through the week (F1)
  11 free mode (H7, H8): a plain Claude with none of his files or connectors, only web search
     and reading pages, on Quick's or Deep's model; it can read a web page; a spoken question
     gets an answer, the call page gets both lines (H6), and nothing is kept: no transcript,
     no after-call work, his words not in the server log, git unchanged
  15 Quick and Deep load different things (B1): Quick has the rules, where things go, the
     to-do list, the mail list, two days of notes and Claude's memory, not the vision
     or the current situation; Deep loads everything
  16 the open loops (J): the hourly mail check's template, the mail list, the computer chat's
     start, Quick and the call's warm-up all use one shape for the very important items
  17 the open loops on a real call: a made-up very important item is named in the first reply
  18 the queue (L): jobs added, stopped, cancelled and switched off read back; the status page
     reads it; the usage gate answers; a call may add and stop jobs, not mark them done
  19 the status page on the phone (H13): its own Tailscale address (8444, tailnet only) answers
     over HTTPS with its own home-screen icon, apart from the call line; the routine keeps it up;
     the call page has the status button below the chat bubble, opening the page inside the app
  20 the usage check (L9), without Claude: a call may run it (and only it, no options), the call
     rules say when; the routine runs it every few minutes while a job runs, rides along with the
     mail check, and opens it hidden in a window that closes itself; it runs from an empty folder
  21 the usage check reads the real usage: one tiny Haiku run from the empty folder saves the
     5-hour and weekly numbers for the status page, Weekly Fable kept from a normal chat
  22 typing to Jarvis during a call (H18): the call page has a text box in the chat while on a call
     and sends what he types; on the call it goes in as his turn (marked typed in the transcript,
     and Claude is told), she answers out loud, and both lines reach the chat log
  23 the call page (H24): a short buzz the moment holding the talk button turns into talking
     (vibrate on Android, the iOS 18 switch tick on the iPhone, a soft click before iOS 18), not on
     a tap; Hang up asks
     "Are you sure?" first, Stay on or a tap beside it keeps the call, and the question sits on top
  24 Cancel while she thinks (H31): the call page shows Cancel only when the server says what he said
     can still be taken back, and sends it; on the call a cancelled turn gets no answer and no sound,
     the thinking stops at once, the transcript marks his line cancelled, and the next turn tells
     Claude not to answer it (she answers only the new question)
  26 a low sound on push to talk (H32): the moment the hold turns into Talking… (not on a tap) a
     short sound plays, a lot lower than the thinking tick; the audio is unlocked inside the touch,
     the mic sends silence while it sounds, and the buzz and click stay as they were
  27 the talk button stays green (F10): the real call page in a headless browser, a fake live call;
     a 12-second hold, a second hold right after letting go (past H11's 8-second Transcribing timer),
     and a hold through the server's state updates all stay Talking…, and letting go turns it yellow
  28 the jobs in the routines graph (H33): the status server writes the running job's state every minute
     and serves each job's runs; the page has a Jobs row on top, folded closed, whose arrow opens one bar
     per job in the status band's own colours, with its own legend; a running routine isn't yellow
  29 the chat and status buttons always on the call page (H34): before, during and after a call; before
     any call in the app the chat shows the last saved call (read only, tool lines left out), after a
     call that call stays; with no saved calls a short note; the server's /api/last-call changes nothing
  30 the laptop's temperature (H35): the real sensors read without a password; normal, warm and hot
     judged right (hot also when macOS slows down); the routine runs it every minute; the status server
     serves it and its history; a hot laptop shows the bar, graph and heat warning, both lights red
  31 the laptop's battery (H37): the real battery read from pmset; low, getting low and fine judged right
     (on the charger never an alarm); the routine runs it every minute; the status server serves it and
     its history; a low battery on battery shows the bar, the graph, and both lights red
  32 Cancel stays, a late tap sends "Cancel last message" (H38): on the call page (headless browser) the
     button stays after she starts answering, until his next turn or 20 seconds after she's done; a tap
     within three seconds sends at once, later it asks "Are you sure you want to cancel?" (Keep keeps,
     a double tap can't confirm it); on the call a late Cancel stops her, his line is marked cancelled,
     and "Cancel last message" goes in as his turn from the button, which Claude is told to treat as such
  33 A quiet job is woken up (H36): no Claude turns. The rules (10 minutes quiet, no internet waits, 3 nudges
     4 minutes apart, then stuck) and a whole run with a made-up job: the incident log gets every nudge and
     its answer, a stuck job shows STOPPED, a job that wakes shows BUILDING again; the status line leaves its
     sign of life; then two real throwaway Terminal windows: continue is typed into the one asked for only,
     and both close themselves
  35 a mute button for her voice (H40): on the call page (headless browser) a button bottom left, before
     and during a call, mutes her audio and switches her incoming track off; her lines still reach the
     chat, the talk button, its low sound and Cancel work as before, and the next load remembers it
  37 a failed routine run says why (H42), on copies, no Claude: the 17:00 mail check's own output reads
     as no internet (not "exit 1", not the usage lines after it); the incident and the routine line keep
     the reason and its last lines; failures in a row are counted outside the Documents folder; the
     watchdog notes a routine that keeps failing once, asks for one more try when the helper gave up and
     the internet is there, notes when it works again; the helper starts that try; each mail check
     keeps its own output file; the status page shows what it said last
  38 more laptop stats (H44), no Claude: CPU, GPU, memory, disk and network read without a password, the
     per-minute maths right (a restart leaves a gap); the routine runs it every minute, with no routine
     line; under the open Laptop section a second arrow, folded closed at the start and remembered, opens
     five rows with graphs; no light coloured; fits a phone-wide screen
  39 the lid-closed sleep switch (H45), no Claude: read for real without a password; on and off flip
     through sudo -n on exactly one pmset command (a fake sudo and pmset, never the real ones); without
     the one-time setup it says the line to type; the setup rule passes visudo and allows only the two
     commands; a call may read it or flip it, nothing else; the routine reads it every minute; the
     status page shows it under Laptop
  41 the clean template (M2), no Claude: HQ's template/ has every file the app reads from a workspace,
     blank and saying put your own things here; nothing of his in it; the Quick load, the open loops,
     the status block and the queue read it; it's in HQ's repo, workspace isn't; Free is explained
     plainly on the call page; Heart is the default of all the voices
  46 the Mac desktop app (H27), no Claude: the watchdog part judges made-up routine lines like the
     status page's light (green, running, waiting, a stopped helper, a hot laptop, the status page
     down) and gives the dog its mood; turning things on only starts what's off and never stops
     anything; the strip (headless browser) shows each mood, the light, the tabs and the button only
     when something is off; the app builds, checks its files, and its real window, never shown, loads
     the strip and the status page
  47 the phone version of the Mac app (H28), no Claude: the status server (its own test port) serves the
     Mac app's own strip at /hq with the phone's script and look, its icon and manifest; the dog's
     reading is the Mac app's; Turn everything on only answers the HQ page (and only says what it would
     do here); at phone width the strip shows the dog and the status page below, the call page only
     loads when Call is opened, on 127.0.0.1:7860 here and the call line's address on the phone
  48 the agents (H29): Donna (Quick, Sonnet) and Pepper (Deep, Opus) replace Quick and Deep, with headshots
  49 an agent knows who she is: Pepper says her name (one Claude turn)
  50 H46, no Claude: Donna left and Pepper right, Voice Donna Paulsen and Voice Pepper Potts in Settings
     (each her own, sent with the call), no waiting lines (the server turns them off too), and inside the
     app (?app) no status button on the call page

Safe to run while the live phone line is up: the flows use their own server on port 7871
(JARVIS_NO_PHONE=1, so Tailscale serve is never touched), calls in test mode (no file
changes, no git, no calendar writes, never email) and a scratch folder that is deleted
at the end. Flows 2-7 use Claude turns on the Max plan: about ten for a full run (one
Opus turn, for the Deep greeting). Flow 11 uses four more (reading a web page, the free call's warm-up and its answer).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402  (light: settings only; the heavy imports wait until a flow needs them)
import privacy  # noqa: E402  (M5: the privacy check)

ROOT = config.ROOT
APP = ROOT / "app"
# M1: HQ is the app; the roadmap is the user's own, in the workspace.
ROADMAP = config.DATA / "roadmap.md"


def site_roadmap(site: Path) -> Path:
    """A test copy of HQ (site/status, site/routine, ...) finds its roadmap where HQ does: in its workspace."""
    p = site / "workspace" / "Jarvis VA" / "roadmap.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
TEST_PORT = int(os.environ.get("JARVIS_TEST_PORT", "7871"))
TEST_URL = f"http://127.0.0.1:{TEST_PORT}"
GREETING_WITHIN_SECS = 15.0  # from "connected" to the first sound
FIRST_AUDIO_WITHIN_SECS = 15.0  # a plain question: the user stops talking -> first sound (seen: 4 to 7 s)

Q_PLAIN = "Hey Jarvis, what's a good way to start a quiet morning? Keep it short."
Q_CALENDAR = "Hey Jarvis, what's on my calendar tomorrow?"
A_NO = "No, don't."
Q_HELLO = "Hey Jarvis, say hello to me in four words."
Q_FREE = "Hey Jarvis, what is the capital of France? Answer in one short sentence."
Q_TYPED = "I can't talk right now. What is the capital of Italy? Answer in one short sentence."
Q_CANCEL = "What is the capital of France? Answer in one short sentence."  # H31: cancelled, never answered
Q_AFTER_CANCEL = "What is two plus two? Answer in one short sentence."
Q_LATE_CANCEL = "Count slowly from one to forty in words, one number per sentence, nothing else."  # H38


# -- reporting ---------------------------------------------------------------------------

class Failed(Exception):
    """A flow did not pass; the message says why in one plain line."""


@dataclass
class Result:
    num: int
    name: str
    status: str = "SKIP"  # PASS, FAIL or SKIP
    secs: float = 0.0
    note: str = ""
    why: list[str] = field(default_factory=list)


def say(text: str = "") -> None:
    print(("    " + text) if text else "", flush=True)


def need(cond, message) -> None:
    """A check inside a flow: the first one that fails ends the flow. The message may be a
    function, for the cases where building it only works when the check failed."""
    if not cond:
        raise Failed(message() if callable(message) else message)


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", "", s.lower()).split())


def heard_share(heard: str, said: str) -> float:
    """How much of what was said Whisper heard (share of the spoken words found in the transcript)."""
    want, got = norm(said).split(), set(norm(heard).split())
    return sum(w in got for w in want) / max(1, len(want))


def plain_calendar_answer(reply: str) -> bool:
    return bool(re.search(
        r"\d|noon|midnight|o'clock|half|quarter|morning|afternoon|evening|nothing|free|clear|empty|"
        r"no events|don't have|do not have|nothing scheduled|appointment|breakfast|lunch|dinner|call|meeting",
        reply.lower()))


# -- shell helpers -------------------------------------------------------------------------

def run(cmd: list[str], *, env: dict | None = None, timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env, cwd=ROOT)


def listening_pids(port: int, path_prefix: str | None = None) -> list[int]:
    env = dict(os.environ)
    if path_prefix:
        env["PATH"] = path_prefix + os.pathsep + env["PATH"]
    out = run(["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"], env=env).stdout
    return [int(x) for x in out.split()]


def alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def started_at(pid: int) -> datetime | None:
    out = run(["ps", "-o", "lstart=", "-p", str(pid)]).stdout.strip()
    try:
        return datetime.strptime(" ".join(out.split()), "%a %b %d %H:%M:%S %Y")
    except ValueError:
        return None


def http_get(path: str, base: str = TEST_URL, timeout: float = 10) -> tuple[int, bytes, str]:
    try:
        with urllib.request.urlopen(base + path, timeout=timeout) as r:
            return r.status, r.read(), r.headers.get("content-type", "")
    except urllib.error.HTTPError as e:
        return e.code, b"", ""
    except Exception:
        return 0, b"", ""


def git_state() -> tuple[str, str]:
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.FOLDER, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=config.FOLDER, capture_output=True, text=True).stdout
    return head, status


# -- the test server (flows 1, 2, 9), started and stopped with the real start.sh / stop.sh --------

class Server:
    """Our own call server on another port. Never the live one: the port is checked, Tailscale
    serve is switched off for these scripts (JARVIS_NO_PHONE), and log and pid file are apart."""

    def __init__(self, tmp: Path):
        assert TEST_PORT != config.PORT, "the test server must not use the live port"
        self.tmp = tmp
        self.log = tmp / "server.log"
        self.pidfile = tmp / "server.pid"
        self.calls = tmp / "calls-server"
        self.env = {
            **os.environ,
            "JARVIS_PORT": str(TEST_PORT), "JARVIS_NO_PHONE": "1", "JARVIS_WRAP_UP": "dry",
            "JARVIS_CALLS": str(self.calls), "JARVIS_LOG": str(self.log), "JARVIS_PID_FILE": str(self.pidfile),
        }

    @property
    def pid(self) -> int | None:
        try:
            return int(self.pidfile.read_text().strip())
        except (OSError, ValueError):
            return None

    def up(self) -> bool:
        return http_get("/")[0] == 200

    def start(self) -> subprocess.CompletedProcess:
        return run([str(APP / "start.sh")], env=self.env, timeout=120)

    def stop(self, path_prefix: str | None = None) -> subprocess.CompletedProcess:
        env = dict(self.env)
        if path_prefix:
            env["PATH"] = path_prefix + os.pathsep + env["PATH"]
        return run([str(APP / "stop.sh")], env=env, timeout=120)

    def log_size(self) -> int:
        try:
            return self.log.stat().st_size
        except OSError:
            return 0

    def log_since(self, offset: int) -> str:
        try:
            with open(self.log, "rb") as f:
                f.seek(offset)
                return f.read().decode("utf8", "replace")
        except OSError:
            return ""


# -- the in-process call (flows 3-7), like test_a3.py ---------------------------------------------

class Live:
    """One real call without a microphone: the Claude session of the folder in test mode,
    a fake microphone (Kokoro speaks the questions), the whole pipeline."""

    ready = False
    pipeline_stopped = False
    wrapped_up = False

    async def open(self, tmp: Path, model: str = "sonnet", loops=None) -> None:
        import brain as _brain  # noqa: F401  (clears API key variables first)
        import numpy as np
        import soxr
        from kokoro_onnx import Kokoro
        from pipecat.pipeline.worker import PipelineParams, PipelineWorker
        from pipecat.workers.runner import WorkerRunner

        from call import Call
        from call_state import CallState
        from pipeline import PushToTalk, build_pipeline
        from test_turn import SR, AudioFeeder, Tap, wait_for

        self.np, self.SR, self.wait_for = np, SR, wait_for
        self.git_before = git_state()
        self.calls_dir = tmp / "calls-live"
        kokoro = Kokoro(str(config.KOKORO_MODEL), str(config.KOKORO_VOICES))

        def _speak16(text: str):
            audio, sr = kokoro.create(text, voice=config.VOICE, speed=1.0, lang="en-us")
            return soxr.resample(audio.astype(np.float32), sr, SR)

        self.speak16 = lambda text: asyncio.to_thread(_speak16, text)
        self.call = Call(model=model, calls_dir=self.calls_dir, wrap_up="dry", test_mode=True, loops=loops)
        t = time.perf_counter()
        await self.call.warm()
        say(f"warm-up {time.perf_counter() - t:.1f} s (Claude primed in {self.call.prime_s or 0:.1f} s)")
        self.mic = AudioFeeder()
        self.after_stt, self.after_llm, self.after_tts = Tap("after_stt"), Tap("after_llm"), Tap("after_tts")
        pipeline, _ = build_pipeline(
            source=self.mic, sink=Tap("sink"), stt=self.call.stt, llm=self.call.llm, tts=self.call.tts,
            fillers=self.call.fillers,
            taps={"after_stt": self.after_stt, "after_llm": self.after_llm, "after_tts": self.after_tts},
            call_state=(call_state := CallState(None)), ptt=(ptt := PushToTalk()),
        )
        self.call_state = call_state
        self.ptt = ptt  # H9: flow 12 holds the talk button
        self.worker = PipelineWorker(pipeline, params=PipelineParams(enable_metrics=True))
        self.runner = WorkerRunner(handle_sigint=False)
        await self.runner.add_workers(self.worker)
        self.run_task = asyncio.create_task(self.runner.run())
        await asyncio.sleep(1.0)
        await wait_for(lambda: self.call.fillers._ready.is_set(), 30, "the fillers to be recorded")
        self.llm = self.call.llm
        self.ready = True

    async def ask(self, q: str, label: str, timeout: float = 90) -> dict:
        """Say a sentence into the fake microphone and wait until the reply has been spoken."""
        from test_turn import fmt

        llm, mic, wait_for = self.llm, self.mic, self.wait_for
        say(f"{label}: saying: {q}")
        n = len(llm.turns)
        mic.say(await self.speak16(q))
        await wait_for(lambda: mic.speech_end is not None, 30, "the question to be spoken")
        end = mic.speech_end
        await wait_for(lambda: len(llm.turns) > n and self.after_llm.first("llm_end", end)[0] is not None
                       and not llm._replying, timeout, "Claude's reply")
        t_end = self.after_llm.all("llm_end", end)[-1][0]
        await wait_for(lambda: not self.call.fillers.talking
                       and self.after_tts.first("tts_stopped", t_end)[0] is not None, 30, "the voice to finish")
        await asyncio.sleep(0.5)
        turn = llm.turns[-1]
        t_txt, _ = self.after_llm.first("llm_text", end)
        t_aud, _ = self.after_tts.first("audio", end)
        fill = [(ts, txt) for ts, txt in self.call.fillers.played if ts >= end]
        r = {
            "turn": turn, "turns": llm.turns[n:],
            "filler": (fill[0][0] - end) if fill else None, "filler_text": [f[1] for f in fill],
            "first_text": None if t_txt is None else t_txt - end,
            "first_audio": None if t_aud is None else t_aud - end,
            "heard": " ".join(v for _, v in self.after_stt.all("transcript", end - 30)),
            "reply": " ".join(t["reply"].strip() for t in llm.turns[n:]).strip(),
        }
        say(f"   Jarvis said: {r['reply']!r}")
        say(f"   tools {[n_ for _, n_ in turn['tools']]} | fillers {r['filler_text']} | after he stopped: filler "
            f"{fmt(r['filler']).strip()} s, first words {fmt(r['first_text']).strip()} s, first sound {fmt(r['first_audio']).strip()} s")
        return r

    async def stop_pipeline(self) -> None:
        if self.pipeline_stopped or not hasattr(self, "worker"):
            return
        self.pipeline_stopped = True
        await self.worker.cancel()
        try:
            await asyncio.wait_for(self.run_task, 10)
        except Exception:
            pass

    async def close(self) -> None:
        await self.stop_pipeline()
        if not self.wrapped_up and hasattr(self, "call"):  # no flow 7: just close the session, no after-call turn
            self.call._finished = True
            self.call.transcript.path.unlink(missing_ok=True)
            await self.call.brain.stop()

    @property
    def turns_used(self) -> int:
        if not self.ready:
            return 1 if hasattr(self, "call") else 0
        return 1 + len(self.llm.turns) + (1 if self.wrapped_up and self.call.wrap_up_reply else 0)


# -- the flows -----------------------------------------------------------------------------

class Run:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.server = Server(tmp)
        self.live: Live | None = None
        self.turns = 0  # Claude turns used by the server flows (the live call counts its own)
        self.live_pid_before = (listening_pids(config.PORT) or [None])[0]

    async def ensure_server(self) -> None:
        if self.server.up():
            return
        if listening_pids(TEST_PORT):
            await asyncio.to_thread(self.server.stop)
        r = await asyncio.to_thread(self.server.start)
        need(self.server.up(), f"the test server did not come up on port {TEST_PORT}: {r.stdout.strip()[-200:]}")

    async def get_live(self) -> Live:
        if self.live and self.live.pipeline_stopped:  # flow 7 hung up the call: start a fresh one
            await self.live.close()
            self.turns += self.live.turns_used
            self.live = None
        if not self.live:
            self.live = Live()  # set first, so a half-open call is still closed at the end
            await self.live.open(self.tmp)
        need(self.live.ready, "the test call could not be opened")
        return self.live

    # 1
    async def flow1(self) -> str:
        if listening_pids(TEST_PORT):
            await asyncio.to_thread(self.server.stop)
        t = time.perf_counter()
        r = await asyncio.to_thread(self.server.start)
        up = time.perf_counter() - t
        need(self.server.up(), f"the server did not answer on port {TEST_PORT}: {r.stdout.strip()[-200:]}")
        say(f"server up in {up:.1f} s (pid {self.server.pid})")
        pids = listening_pids(TEST_PORT)
        need(pids and self.server.pid in pids, f"the pid file says {self.server.pid} but port {TEST_PORT} is held by {pids}")
        who = run(["lsof", "-nP", f"-iTCP:{TEST_PORT}", "-sTCP:LISTEN"]).stdout
        need(f"127.0.0.1:{TEST_PORT}" in who, "the server listens on more than this MacBook")
        code, body, _ = http_get("/")
        page = body.decode("utf8", "replace")
        need(code == 200 and "<title>Jarvis</title>" in page, f"the call page did not load ({code})")
        need('data-mode="quick"' in page and 'data-mode="deep"' in page, "the Quick and Deep buttons are missing")
        need('id="btn"' in page and 'id="mute"' in page, "the call button or the mute button is missing")
        need('id="orb"' in page and 'id="sound"' in page and "pointerdown" in page,
             "the thinking animation, the thinking sound switch or push to talk is missing (H3-H5)")
        need('id="chatbtn"' in page and 'id="chatlog"' in page and "jarvis-chat" in page,
             "the chat bubble and its log are missing (H6)")
        need('id="free"' in page and 'data-mode="free"' not in page and "free, voice" in page,
             "Free is not a switch on top of Quick and Deep (H8)")
        need("body.chatting #mute" in page and "body.chatting #orbwrap" in page and "showLayout" in page,
             "the talk button and the thinking circle don't stay on screen with the chat open (H8)")
        need("text-size-adjust:100%" in page, "the text can still grow after turning the phone (H9)")
        need('type: "ptt"' in page and 'addEventListener("touchend"' in page,
             "holding the talk button doesn't tell the server, or a cancelled touch can end a hold (H9)")
        start = page[page.index("<body>"):page.index('<div id="settings"')]
        need('id="setbtn"' in page and 'id="settings"' in page
             and not any(f'id="{x}"' in start for x in ("free", "voice", "lines", "sound")),
             "Free, the voice, the waiting lines or the thinking sound are still on the start screen (H9)")
        need('id="chatclose"' in page and "showChat(false);  // H10" in page,
             "the chat has no Close button, or hanging up doesn't close it (H10)")
        for path, kind in [("/manifest.webmanifest", "json"), ("/apple-touch-icon.png", "image/png"),
                           ("/icon-192.png", "image/png"), ("/icon-512.png", "image/png"), ("/call", "text/html")]:
            code, body, ctype = http_get(path)
            need(code == 200 and kind in ctype and body, f"{path} did not load ({code}, {ctype})")
        log = self.server.log_since(0)
        bad = [ln for ln in log.splitlines() if " | ERROR " in ln or "Traceback" in ln]
        need(not bad, lambda: f"errors in the server log at start: {bad[0][:160]}")
        return f"up in {up:.0f} s, page, buttons and icons load"

    # 2
    async def flow2(self) -> str:
        await self.ensure_server()
        out = []
        import agents  # H46: each load on its agent's model (Donna, Quick, on Sonnet; Pepper, Deep, on Opus)
        for mode in ("quick", "deep"):
            a = agents.find(config.FOLDER, None, mode)
            model = config.MODEL_ALIASES.get(a["model"], a["model"])
            s = await self.greeting_call(mode, model)
            out.append(f"{mode} {s:.1f} s")
            self.turns += 1  # the call's warm-up turn
        return "greeting before a word, " + ", ".join(out)

    async def greeting_call(self, mode: str, model: str) -> float:
        """A silent caller, the way the phone page connects. Returns seconds from connected to the greeting."""
        import fractions  # noqa: F401
        import aiohttp
        import numpy as np
        from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription

        from test_a4 import FakeMic

        say(f"{mode}: calling {TEST_URL}, saying nothing")
        offset = self.server.log_size()
        pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        pc.addTrack(FakeMic(np.zeros(0, np.int16)))
        dc = pc.createDataChannel("chat", ordered=True)
        heard = {"first": None}
        states: list[str] = []  # H3: what the call page is told (listening, thinking, speaking)
        chats: list[tuple[str, str]] = []  # H6: the chat log lines the page is sent

        @dc.on("message")
        def on_message(msg):
            try:
                m = json.loads(msg)
            except (TypeError, ValueError):
                return
            if isinstance(m, dict) and m.get("type") == "jarvis-state":
                states.append(m.get("state"))
            elif isinstance(m, dict) and m.get("type") == "jarvis-chat":
                chats.append((m.get("who"), m.get("text")))

        @pc.on("track")
        def on_track(track):
            async def read():
                while True:
                    try:
                        f = await track.recv()
                    except Exception:
                        return
                    if heard["first"] is None and np.abs(f.to_ndarray().astype(np.int32)).mean() > 200:
                        heard["first"] = time.perf_counter()
            asyncio.ensure_future(read())

        async def pinger():
            while True:
                await asyncio.sleep(1)
                if dc.readyState == "open":
                    dc.send("ping: " + str(time.time()))

        ping = asyncio.ensure_future(pinger())
        try:
            await pc.setLocalDescription(await pc.createOffer())
            async with aiohttp.ClientSession() as s:
                async with s.post(TEST_URL + "/api/offer", json={
                        "sdp": pc.localDescription.sdp, "type": "offer", "request_data": {"mode": mode}}) as r:
                    need(r.status == 200, f"{mode}: the offer was refused ({r.status})")
                    answer = await r.json()
            await pc.setRemoteDescription(RTCSessionDescription(answer["sdp"], answer["type"]))
            t0 = time.perf_counter()
            while pc.connectionState != "connected" and time.perf_counter() - t0 < 20:
                await asyncio.sleep(0.1)
            need(pc.connectionState == "connected", f"{mode}: the call did not connect")
            t_conn = time.perf_counter()
            while heard["first"] is None and time.perf_counter() - t_conn < GREETING_WITHIN_SECS:
                await asyncio.sleep(0.1)
            need(heard["first"] is not None,
                 f"{mode}: no greeting within {GREETING_WITHIN_SECS:.0f} s of connecting, and the caller said nothing")
            t_greet = heard["first"] - t_conn
            t_wait = time.perf_counter()  # let the greeting finish before hanging up (a long one takes ~5 s)
            while (not states or states[-1] != "listening" or "speaking" not in states) and time.perf_counter() - t_wait < 12:
                await asyncio.sleep(0.2)
            need("speaking" in states, f"{mode}: the call page was not told she is speaking (H3): {states}")
            need(states[-1] == "listening", f"{mode}: the call page was not told it's his turn after the greeting (H3): {states}")
            dc.send(json.dumps({"type": "hangup"}))
            await asyncio.sleep(0.5)
        finally:
            ping.cancel()
            await pc.close()
        # The server side: which greeting, which model, and the hang-up noticed.
        log = ""
        for _ in range(60):
            log = self.server.log_since(offset)
            if "Nobody said anything" in log:
                break
            await asyncio.sleep(0.5)
        greeting = re.findall(r"Filler: (.+)", log)
        all_greetings = {g for part in config.GREETINGS.values() for g in part}
        need(any(g in all_greetings for g in greeting), f"{mode}: the server log has no greeting line (Filler: ...): {greeting}")
        need(f"Call started on {model}" in log, f"{mode}: the call did not start on {model}")
        need(any(w == "filler" and t in all_greetings for w, t in chats),
             f"{mode}: the greeting did not reach the chat log on the page (H6): {chats}")
        need("The caller hung up (button)" in log, f"{mode}: the hang-up was not noticed")
        need("Nobody said anything" in log, f"{mode}: the call did not wind down (no after-call line)")
        say(f"   greeting {greeting[0]!r} came {t_greet:.1f} s after connecting, on {model}; page told: {states}")
        return t_greet

    # 3
    async def flow3(self) -> str:
        live = await self.get_live()
        t_before = time.time()
        r = await live.ask(Q_PLAIN, "plain question")
        seen = [st for ts, st in live.call_state.history if ts >= t_before]
        say(f"   the page was told: {seen}")
        share = heard_share(r["heard"], Q_PLAIN)
        need(share >= 0.7, f"she misheard the question: {r['heard']!r}")
        need(len(r["reply"].split()) >= 3, f"no spoken answer: {r['reply']!r}")
        need(r["first_audio"] is not None, "no sound came out")
        need(r["first_audio"] <= FIRST_AUDIO_WITHIN_SECS,
             lambda: f"first sound took {r['first_audio']:.1f} s (limit {FIRST_AUDIO_WITHIN_SECS:.0f})")
        need(not r["turn"]["tools"], f"a plain question used tools: {[n for _, n in r['turn']['tools']]}")
        order = [st for st in seen if st in ("hearing", "thinking", "speaking")]
        need("thinking" in order and "speaking" in order and order.index("thinking") < len(order) - 1 - order[::-1].index("speaking"),
             f"the call page did not go thinking then speaking (H3): {seen}")
        return f"page went {' > '.join(dict.fromkeys(seen))}; first words {r['first_text']:.1f} s, first sound {r['first_audio']:.1f} s"

    # 12
    async def flow12(self) -> str:
        live = await self.get_live()
        llm, mic, ptt, wait_for = live.llm, live.mic, live.ptt, live.wait_for
        pause = 8.0  # longer than smart-turn and the 5-second stop watchdog
        n = len(llm.turns)
        say("holding the talk button")
        await ptt.set_held(True)
        try:
            part1, part2 = "What is the capital of France,", "and the capital of Germany? One short sentence."
            say(f"   saying: {part1}")
            mic.say(await live.speak16(part1))
            await wait_for(lambda: mic.speech_end is not None, 30, "the first half to be spoken")
            first_end = mic.speech_end
            say(f"   {pause:.0f} s of silence, still holding")
            await asyncio.sleep(pause)
            need(len(llm.turns) == n, f"she took the turn {pause:.0f} s into a pause while the button was held")
            say(f"   saying: {part2}")
            mic.say(await live.speak16(part2))
            await wait_for(lambda: mic.speech_end is not None and mic.speech_end > first_end, 30, "the second half to be spoken")
            await asyncio.sleep(2.0)
            need(len(llm.turns) == n, "she took the turn before the button was let go")
        finally:
            say("letting go")
            t_go = time.perf_counter()
            await ptt.set_held(False)
        await wait_for(lambda: len(llm.turns) > n, 20, "her turn after letting go")
        took = time.perf_counter() - t_go
        await wait_for(lambda: not llm._replying, 90, "Claude's reply")
        end = live.after_llm.all("llm_end", t_go)
        await wait_for(lambda: not live.call.fillers.talking and (not end or live.after_tts.first("tts_stopped", end[-1][0])[0] is not None),
                       30, "the voice to finish")
        await asyncio.sleep(0.5)
        heard = norm(" ".join(t["words"] for t in llm.turns[n:]))
        reply = norm(" ".join(t["reply"] for t in llm.turns[n:]))
        say(f"   turns {len(llm.turns) - n}, heard {heard!r}, Jarvis said {reply!r}")
        need(len(llm.turns) - n == 1, f"the held turn was split in {len(llm.turns) - n}")
        need("france" in heard and "germany" in heard, f"not both halves in one turn: {heard!r}")
        need("paris" in reply and "berlin" in reply, f"the answer missed a half: {reply!r}")
        return f"one turn through a {pause:.0f} s pause while held; she took it {took:.1f} s after letting go"

    async def _wait_reply(self, live, n: int, t_from: float) -> tuple[str, str, int]:
        llm, wait_for = live.llm, live.wait_for
        await wait_for(lambda: not llm._replying, 90, "Claude's reply")
        end = live.after_llm.all("llm_end", t_from)
        await wait_for(lambda: not live.call.fillers.talking and (not end or live.after_tts.first("tts_stopped", end[-1][0])[0] is not None),
                       30, "the voice to finish")
        await asyncio.sleep(0.5)
        heard = norm(" ".join(t["words"] for t in llm.turns[n:]))
        reply = norm(" ".join(t["reply"] for t in llm.turns[n:]))
        return heard, reply, len(llm.turns) - n

    # 13
    async def flow13(self) -> str:
        live = await self.get_live()
        llm, mic, ptt, wait_for = live.llm, live.mic, live.ptt, live.wait_for
        n = len(llm.turns)
        part1, part2 = "What is the capital of Japan,", "and the capital of Spain? One short sentence."
        say("holding the talk button")
        await ptt.set_held(True)
        try:
            say(f"   saying: {part1}")
            mic.say(await live.speak16(part1))
            await wait_for(lambda: mic.speech_end is not None, 30, "the first half to be spoken")
            first_end = mic.speech_end
            await asyncio.sleep(3.0)  # the first half is text by now
            say(f"   saying: {part2}, letting go the moment it ends")
            mic.say(await live.speak16(part2))
            await wait_for(lambda: mic.speech_end is not None and mic.speech_end > first_end, 30, "the second half to be spoken")
        finally:
            t_go = time.time()
            await ptt.set_held(False)
        await wait_for(lambda: len(llm.turns) > n, 20, "her turn after letting go")
        heard, reply, turns = await self._wait_reply(live, n, time.perf_counter() - 30)
        seen = [st for ts, st in live.call_state.history if ts >= t_go]
        say(f"   turns {turns}, heard {heard!r}, Jarvis said {reply!r}; page told: {seen}")
        need(turns == 1, f"letting go split the turn in {turns}: the last words came in late")
        need("japan" in heard and "spain" in heard, f"the last words were lost: {heard!r}")
        need("tokyo" in reply and "madrid" in reply, f"the answer missed a half: {reply!r}")
        need(seen[:1] == ["transcribing"] and "thinking" in seen, f"the page wasn't told transcribing, then thinking (H11): {seen}")
        return f"let go right at the last word: one turn with both halves; page went {' > '.join(dict.fromkeys(seen))}"

    # 14
    async def flow14(self) -> str:
        import numpy as np

        live = await self.get_live()
        llm, mic, wait_for = live.llm, live.mic, live.wait_for
        n = len(llm.turns)
        pause = 1.0
        part1, part2 = "What is the capital of Austria,", "and the capital of Portugal? One short sentence."
        say(f"free talking: {part1} ({pause:.1f} s pause) {part2}")
        audio = np.concatenate([await live.speak16(part1), np.zeros(int(live.SR * pause), dtype=np.float32),
                                await live.speak16(part2)])
        t0 = time.time()
        mic.say(audio)
        await wait_for(lambda: mic.speech_end is not None, 30, "the question to be spoken")
        await wait_for(lambda: len(llm.turns) > n, 30, "her turn")
        heard, reply, turns = await self._wait_reply(live, n, time.perf_counter() - 30)
        seen = [st for ts, st in live.call_state.history if ts >= t0]
        say(f"   turns {turns}, heard {heard!r}, Jarvis said {reply!r}; page told: {seen}")
        need(turns == 1, f"a {pause:.1f} s pause split the sentence in {turns} turns")
        need("austria" in heard and "portugal" in heard, f"not both halves in one turn: {heard!r}")
        need("vienna" in reply and "lisbon" in reply, f"the answer missed a half: {reply!r}")
        need("waiting" in seen and seen.index("waiting") < seen.index("thinking"),
             f"the page wasn't shown the yellow wait before thinking (H12): {seen}")
        return f"one turn through a {pause:.1f} s pause; page went {' > '.join(dict.fromkeys(seen))}"

    # 4
    async def flow4(self) -> str:
        live = await self.get_live()
        start = len(live.call.policy.log)
        r = await live.ask(Q_CALENDAR, "calendar question")
        calls = [(t, d.verdict) for t, _, d in live.call.policy.log[start:] if "alendar" in t]
        say(f"   calendar calls: {calls}")
        need(calls, "she did not look at the calendar")
        from policy import CALENDAR_READ
        writes = [(t, v) for t, v in calls if t.split("__")[-1] not in CALENDAR_READ]
        need(not writes, f"a calendar change was attempted: {writes}")
        need(all(v == "allow" for _, v in calls), f"a calendar read was refused: {calls}")
        need(r["first_audio"] is not None, "no sound came out")
        waiting = r["filler_text"]
        need(waiting, "no waiting line played while she looked")
        need(not any(norm(f).startswith("mm") for f in waiting), f"a waiting line starts with Mm: {waiting}")
        need(plain_calendar_answer(r["reply"]) and len(r["reply"].split()) >= 3,
             f"the answer does not say what is on the calendar: {r['reply']!r}")
        return f"waiting line after {r['filler']:.1f} s, calendar read, first sound {r['first_audio']:.1f} s"

    # 5
    async def flow5(self) -> str:
        live = await self.get_live()
        start = len(live.call.policy.log)
        # A day with no doubt about which one is meant ("tomorrow" at four in the morning is ambiguous).
        day = (datetime.now() + timedelta(days=2)).strftime("%A")
        r1 = await live.ask(f"Jarvis, please put a new event in my calendar on {day} at noon, called test call.",
                            "needs a yes")
        asked = [(t, d.verdict) for t, _, d in live.call.policy.log[start:] if d.verdict == "ask"]
        say(f"   asked about: {asked} | pending: {[q for _, _, q in live.call.policy.pending]}")
        done = [t for t, _, d in live.call.policy.log[start:] if "create_event" in t and d.verdict == "allow"]
        need(not done, "the event was created before he said anything")
        # Usually she tries the calendar, is stopped by the call system and asks; sometimes she
        # asks first without trying. Both are fine: she checked with him, and nothing is done.
        need("?" in r1["reply"], f"she did not ask him anything: {r1['reply']!r}")
        if asked:
            need(live.call.policy.pending, "no question was waiting for his answer")
        n_sentences = len([x for x in re.split(r"[.?!]+", r1["reply"]) if x.strip()])
        need(n_sentences <= 3, lambda: f"the check-in is not one natural sentence ({n_sentences} sentences): {r1['reply']!r}")
        need(not re.search(r"say yes|yes or no", r1["reply"].lower()), f"robotic check-in: {r1['reply']!r}")
        r2 = await live.ask(A_NO, "answering no")
        creates = [(t, d.verdict) for t, _, d in live.call.policy.log[start:] if "create_event" in t]
        say(f"   create_event decisions: {creates}")
        if asked:
            need("not approved" in r2["turn"]["sent"], "the call system did not note that the answer was a no")
        need(not any(v == "allow" for _, v in creates), "the event was created after a no")
        need(not live.call.policy.pending, "a question is still pending after the no")
        return "checked in " + ("after the calendar stopped her" if asked else "before trying") + "; a no changed nothing"

    # 6
    async def flow6(self) -> str:
        live = await self.get_live()
        from test_turn import interrupt_test

        say("cutting in while she tells a long story")
        ok = await interrupt_test(live.speak16, live.mic, live.after_stt, live.after_llm, live.after_tts,
                                  live.llm, live.call.brain)
        need(ok, "cutting in did not stop her cleanly (see the lines above)")
        return "her voice stopped, and she answered the cut-in"

    # 7
    async def flow7(self) -> str:
        live = await self.get_live()
        if not live.llm.turns:
            await live.ask(Q_HELLO, "a first sentence")
        await live.stop_pipeline()
        call = live.call
        path = call.transcript.path
        t = time.perf_counter()
        live.wrapped_up = True
        await call.finish()
        secs = time.perf_counter() - t
        text = path.read_text() if path.exists() else ""
        say(f"transcript {path.name}: {len(text.splitlines())} lines; after-call work (dry) said: {call.wrap_up_reply!r}")
        need(path.exists(), "no transcript was saved")
        need(f"**{config.USER_LABEL}:**" in text and "**Jarvis:**" in text and "Ended" in text, "the transcript misses his words, hers or the end")
        need(call.wrap_up_reply and call.wrap_up_reply.strip(), "the after-call work said nothing")
        after = git_state()
        if after != live.git_before:
            old, new = set(live.git_before[1].splitlines()), set(after[1].splitlines())
            diff = sorted(old ^ new)[:3]
            raise Failed(f"git changed during the test: head {live.git_before[0][:7]} -> {after[0][:7]}; status lines {diff}")
        return f"transcript saved, git unchanged, after-call work {secs:.0f} s"

    # 8
    async def flow8(self) -> str:
        from fillers import FillerPlayer

        class Quiet(FillerPlayer):
            async def push_frame(self, *a, **k):  # no pipeline here: the audio goes nowhere
                return None

        p = Quiet(None, voice=config.VOICE)
        p._sample_rate = 24000
        p._ready.set()
        p._greet_ready.set()
        for texts in p._texts.values():
            for t in texts:
                p._audio[t] = b"\x00" * 480
        every = {k: list(v) for k, v in p._texts.items()}
        need(len(every["wait"]) >= 20, f"only {len(every['wait'])} waiting lines")
        lines = [(k, t) for k, v in every.items() for t in v]
        mm = [t for _, t in lines if norm(t).startswith("mm")]
        need(not mm, f"lines that start with Mm: {mm}")
        need("Mm," not in config.VOICE_RULES and "Mm " not in config.VOICE_RULES, "the call instructions still tell her to say Mm")
        for kind in every:
            seen = []
            for _ in range(1000):
                p._filler_until = 0.0
                t = await p.say(kind)
                need(t, f"the {kind} line did not play")
                need(t in every[kind], f"{t!r} is not one of the {kind} lines")
                seen.append(t)
            same = [a for a, b in zip(seen, seen[1:]) if a == b]
            need(not same, lambda: f"the same {kind} line twice in a row: {same[0]!r}")
            need(set(seen) == set(every[kind]), f"some {kind} lines never play: {set(every[kind]) - set(seen)}")
            p._last = None
        return f"{len(every['wait'])} waiting lines, {len(lines)} lines in all, no Mm, no repeats"

    # 9
    async def flow9(self) -> str:
        srv = self.server
        await self.ensure_server()
        pid1 = srv.pid
        need(alive(pid1), "no running test server to restart")
        # a normal stop
        t = time.perf_counter()
        r = await asyncio.to_thread(srv.stop)
        need(not listening_pids(TEST_PORT), f"stop.sh left something on port {TEST_PORT}: {r.stdout.strip()}")
        need(not alive(pid1), f"stop.sh left the server (pid {pid1}) running")
        need(not srv.pidfile.exists(), "stop.sh left the pid file")
        say(f"stopped in {time.perf_counter() - t:.1f} s")
        # a start: a new process, newer than the code
        r = await asyncio.to_thread(srv.start)
        pid2 = srv.pid
        need(srv.up(), f"the server did not come back: {r.stdout.strip()[-200:]}")
        need(pid2 and pid2 != pid1, f"the new server has the old pid ({pid2})")
        need(listening_pids(TEST_PORT) == [pid2], f"port {TEST_PORT} is held by {listening_pids(TEST_PORT)}, not the new server {pid2}")
        newest = max(p.stat().st_mtime for p in [*APP.glob("*.py"), *(APP / "web").glob("*")])
        began = started_at(pid2)
        need(began and began.timestamp() >= int(newest) - 1, "the running server is older than the code: it answers with old code")
        say(f"restarted: pid {pid1} -> {pid2}, started after the newest code change")
        # the 9 October 03:10 case: the stop step cannot see the server (lsof shows nothing)
        fake = self.tmp / "fakebin"
        fake.mkdir(exist_ok=True)
        (fake / "lsof").write_text("#!/bin/sh\nexit 1\n")
        (fake / "lsof").chmod(0o755)
        need(not listening_pids(TEST_PORT, str(fake)), "the blind lsof stand-in does not work")
        r = await asyncio.to_thread(srv.stop, str(fake))
        stopped = not alive(pid2) and not listening_pids(TEST_PORT)
        if not stopped:
            await asyncio.to_thread(srv.stop)  # clean up with the real lsof
            raise Failed(f"stop.sh could not stop the server when lsof can't see it (it said: {r.stdout.strip()!r}); "
                         "the old version keeps answering")
        # and starting again after that still gives a working server
        r = await asyncio.to_thread(srv.start)
        need(srv.up() and srv.pid not in (pid1, pid2), "the server did not start again after the blind stop")
        return f"stop and start swap the process ({pid1}, {pid2}, {srv.pid}); stops even when lsof is blind"

    # 10
    async def flow10(self) -> str:
        status = ROOT / "status"
        js = f"""
import {{ readFileSync }} from 'node:fs';
import {{ parseRoadmap }} from '{(status / "parse.mjs").as_uri()}';
import {{ stopLine }} from '{(status / "usage.mjs").as_uri()}';
const r = parseRoadmap(readFileSync({json.dumps(str(ROADMAP))}, 'utf8'));
const reset = new Date('2026-10-13T12:00:00Z');
const week = {{ label: 'Weekly · all models', resetsAt: reset.toISOString() }};
const at = (ms) => stopLine(week, r.usageLimit, new Date(reset.getTime() - ms)).line;
const DAY = 864e5;
const steps = Array.from({{ length: 29 }}, (_, i) => at(7 * DAY - 6e4 - i * 6 * 36e5));
console.log(JSON.stringify({{
  problems: r.problems, state: r.state, usageLimit: r.usageLimit, weeklyLimit: r.weeklyLimit,
  phases: r.phases.map((p) => p.id), start: at(7 * DAY - 6e4), mid: at(3.5 * DAY), end: at(36e5),
  five: stopLine({{ label: '5-hour limit', resetsAt: reset.toISOString() }}, r.usageLimit).line,
  rising: steps.every((v, i) => i === 0 || v >= steps[i - 1]), distinct: new Set(steps).size,
}}));
"""
        r = await asyncio.to_thread(run, ["node", "--input-type=module", "-e", js])
        need(r.returncode == 0, f"node failed: {r.stderr.strip()[-200:]}")
        d = json.loads(r.stdout.strip().splitlines()[-1])
        need(not d["problems"], f"the status page cannot read the roadmap: {d['problems']}")
        need(d["state"] and "G" in d["phases"], f"the roadmap's state or phases are off: {d['state']}, {d['phases']}")
        need(d["usageLimit"] == 70, f"the 5-hour stop line is {d['usageLimit']}, not 70")
        need(d["weeklyLimit"] is None, f"a flat weekly line ({d['weeklyLimit']}%) is set in the roadmap: the weekly lines won't move")
        need(d["five"] == 70, f"the 5-hour line moved: {d['five']}")
        need(d["start"] == 20, f"a weekly line starts at {d['start']}, not 20")
        need(d["end"] == 100, f"a weekly line ends at {d['end']}, not 100")
        need(45 <= d["mid"] <= 60, f"a weekly line halfway is {d['mid']}")
        need(d["rising"] and d["distinct"] > 20, "the weekly line does not rise step by step")
        # the page itself, when its server is running (it is only on this MacBook)
        code, body, _ = http_get("/roadmap.md", "http://127.0.0.1:4748", timeout=3)
        extra = ""
        if code == 200:
            need(body.decode("utf8", "replace").startswith("#"), "the status page serves a roadmap that does not start with the state")
            extra = ", page on 4748 serves it"
        return f"roadmap reads clean; weekly line {d['start']}% -> {d['mid']}% -> {d['end']}%, 5-hour {d['five']}%{extra}"

    # 11
    async def flow11(self) -> str:
        """H7, free mode, and H6 end to end: a real call to the test server on Free, one spoken question."""
        # The free Claude itself: nothing of his can be loaded from where it works.
        import brain as _brain  # noqa: F401  (clears API key variables first)
        from call import Call

        c = Call(model="sonnet", free=True)
        o = c.brain._options
        need(c.policy is None and c.transcript.path is None and c.wrap_up_mode == "off",
             "free mode still has a policy, a transcript file or after-call work")
        need(o.tools == config.FREE_TOOLS == ["WebSearch", "WebFetch"] and o.allowed_tools == o.tools
             and o.setting_sources == [] and o.strict_mcp_config and not o.mcp_servers,
             f"the free Claude has other tools, settings or connectors: tools {o.tools}, settings {o.setting_sources}")
        need(c.brain.model == config.MODEL_ALIASES["sonnet"], f"free on Quick is not Sonnet: {c.brain.model}")
        c_deep = Call(model="opus", free=True)
        need(c_deep.brain.model == config.MODEL_ALIASES["opus"] and c_deep.policy is None,
             f"free on Deep is not a plain Opus: {c_deep.brain.model}")
        cwd = Path(o.cwd).resolve()
        need(cwd == config.FREE_DIR.resolve() and config.FOLDER.resolve() not in [cwd, *cwd.parents],
             f"the free Claude works inside his folder: {cwd}")
        need(not any((d / "CLAUDE.md").exists() for d in [cwd, *cwd.parents]),
             "there is a CLAUDE.md where the free Claude works, or above it")
        need(c.stt._quiet, "free mode still writes his words to the server log")

        # H8: the internet. The free Claude reads a web page (no audio, straight to the session).
        reply = ""
        try:
            async for piece in c.brain.ask("Open the web page https://example.com and tell me its main heading, in a few words."):
                if isinstance(piece, str):
                    reply += piece
            used = list(c.brain.last_turn.tools if c.brain.last_turn else [])
        finally:
            await c.brain.stop()
        self.turns += 1
        say(f"   web: tools {used}, reply: {reply.strip()[:120]}")
        need(any(t in ("WebFetch", "WebSearch") for t in used), f"free mode did not use the internet: tools {used}")
        need("example domain" in norm(reply), f"free mode did not read the page: {reply[:160]}")

        # A real call on Free.
        import fractions  # noqa: F401
        import aiohttp
        import numpy as np
        import soxr
        from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
        from kokoro_onnx import Kokoro

        from test_a4 import SR, FakeMic

        await self.ensure_server()
        git_before = git_state()
        calls_before = set(self.server.calls.glob("*.md")) if self.server.calls.exists() else set()
        k = Kokoro(str(config.KOKORO_MODEL), str(config.KOKORO_VOICES))
        audio, sr = await asyncio.to_thread(k.create, Q_FREE, voice=config.VOICE, speed=1.0, lang="en-us")
        speech = (soxr.resample(audio.astype(np.float32), sr, SR) * 32767).astype(np.int16)
        mic = FakeMic(np.concatenate([np.zeros(SR * 6, np.int16), speech]))  # after the greeting
        offset = self.server.log_size()
        pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        pc.addTrack(mic)
        dc = pc.createDataChannel("chat", ordered=True)
        chats: list[tuple[str, str]] = []

        @dc.on("message")
        def on_message(msg):
            try:
                m = json.loads(msg)
            except (TypeError, ValueError):
                return
            if isinstance(m, dict) and m.get("type") == "jarvis-chat":
                chats.append((m.get("who"), m.get("text")))

        @pc.on("track")
        def on_track(track):
            async def read():
                while True:
                    try:
                        await track.recv()
                    except Exception:
                        return
            asyncio.ensure_future(read())

        async def pinger():
            while True:
                await asyncio.sleep(1)
                if dc.readyState == "open":
                    dc.send("ping: " + str(time.time()))

        say(f"free: calling {TEST_URL}, then saying: {Q_FREE}")
        ping = asyncio.ensure_future(pinger())
        try:
            await pc.setLocalDescription(await pc.createOffer())
            async with aiohttp.ClientSession() as s:
                async with s.post(TEST_URL + "/api/offer", json={
                        "sdp": pc.localDescription.sdp, "type": "offer", "request_data": {"mode": "quick", "free": True}}) as r:
                    need(r.status == 200, f"free: the offer was refused ({r.status})")
                    answer = await r.json()
            await pc.setRemoteDescription(RTCSessionDescription(answer["sdp"], answer["type"]))
            t0 = time.perf_counter()
            # A pause in the question can split it in two turns; wait for an answer that wasn't cut off.
            while not any(w == "jarvis" and not t.endswith("(cut off)") for w, t in chats) and time.perf_counter() - t0 < 60:
                await asyncio.sleep(0.2)
            await asyncio.sleep(1)
            dc.send(json.dumps({"type": "hangup"}))
            await asyncio.sleep(0.5)
        finally:
            ping.cancel()
            await pc.close()
        self.turns += 2  # the warm-up and the answer
        log = ""
        for _ in range(60):
            log = self.server.log_since(offset)
            if "Free mode: nothing kept" in log:
                break
            await asyncio.sleep(0.5)
        say(f"   the page got: {chats}")
        need("free mode, nothing kept" in log, "the server did not start the call in free mode")
        mine = [t for w, t in chats if w == "user"]
        hers = [t for w, t in chats if w == "jarvis"]
        # A pause can split the question in two turns, and the second half may come after the answer.
        need(mine and "capital of france" in norm(" ".join(mine)), f"the page did not get his words (H6): {mine}")
        need(hers and "paris" in norm(" ".join(hers)), f"no answer on the page, or a wrong one (H6): {hers}")
        need("Free mode: nothing kept" in log, "the call did not wind down the free way")
        need("After-call work" not in log, "after-call work ran on a free call")
        leak = [ln for ln in log.splitlines() if "Transcription:" in ln or re.search(r"capital|france|paris", ln, re.I)]
        need(not leak, lambda: f"his words were written to the server log: {leak[0][:200]}")
        calls_after = set(self.server.calls.glob("*.md")) if self.server.calls.exists() else set()
        need(calls_after == calls_before, f"a transcript was saved: {sorted(p.name for p in calls_after - calls_before)}")
        need(git_state() == git_before, "git changed during the free call")
        return "plain Claude with the internet, page got both lines, nothing kept: no transcript, no after-call work, not in the log"

    # 22
    async def flow22(self) -> str:
        """H18: he types in the chat on the call page; she takes it as his turn and answers out loud."""
        page = (APP / "web/index.html").read_text()
        need('id="typeform"' in page and 'id="typein"' in page and 'id="typesend"' in page,
             "the text box is missing from the chat on the call page")
        need(page.index('id="chatlog"') < page.index('id="typeform"') < page.index('id="chatbtn"'),
             "the text box is not inside the chat panel, below the log")
        need('type: "typed", text' in page, "the call page doesn't send what he types")
        need('typeForm.classList.toggle("show", state === "live")' in page, "the text box isn't tied to being on a call")
        bot_src = (APP / "bot.py").read_text()
        need('message.get("type") == "typed"' in bot_src and "type_to_jarvis(worker, call.llm, call_state" in bot_src,
             "the call server doesn't pass a typed message on to Jarvis")

        from pipeline import type_to_jarvis

        live = await self.get_live()
        llm = live.llm
        lines: list[tuple[str, str]] = []
        live.call.transcript.on_line = lambda who, text: lines.append((who, text))
        need(not await type_to_jarvis(live.worker, llm, live.call_state, "   "), "an empty message was sent on")
        n = len(llm.turns)
        say(f"typing: {Q_TYPED}")
        t0 = time.perf_counter()
        need(await type_to_jarvis(live.worker, llm, live.call_state, Q_TYPED), "the typed message was refused")
        await live.wait_for(lambda: len(llm.turns) > n and not llm._replying, 90, "Claude's reply to the typed message")
        await live.wait_for(lambda: not live.call.fillers.talking
                            and live.after_tts.first("tts_stopped", t0)[0] is not None, 30, "the voice to finish")
        await asyncio.sleep(0.5)
        turn = llm.turns[n]
        t_aud, _ = live.after_tts.first("audio", t0)
        reply = " ".join(t["reply"].strip() for t in llm.turns[n:]).strip()
        say(f"   Jarvis said: {reply!r}; first sound {(t_aud - t0) if t_aud else float('nan'):.1f} s after sending")
        need(turn["words"] == Q_TYPED, f"the turn didn't get his typed words: {turn['words']!r}")
        need("typed this in the chat" in turn["sent"], "Claude wasn't told the message was typed")
        need("rome" in norm(reply), f"no answer, or a wrong one: {reply!r}")
        need(t_aud is not None, "she didn't answer out loud")
        need(("user", Q_TYPED) in lines and any(w == "jarvis" and "rome" in norm(t) for w, t in lines),
             f"the chat log didn't get both lines: {lines}")
        tx = live.call.transcript.path.read_text()
        need(f"**{config.USER_LABEL}:** {Q_TYPED} *(typed)*" in tx, "the transcript doesn't mark the line as typed")
        return f"typed turn answered out loud ({(t_aud - t0):.1f} s to first sound), both lines in the chat, marked typed"

    # 15
    async def flow15(self) -> str:
        """B1: Quick loads only part of his folder, Deep everything. No Claude turns: the options
        and the Quick text are checked as built (the live check was done once, 9 October 2026)."""
        import datetime as _dt

        import quick_context
        from call import Call
        from policy import Policy
        from pipeline import make_brain

        folder = config.FOLDER
        text = quick_context.build(folder)
        def has(rel: str, probe: int = 400) -> bool:  # a solid piece from the middle of the file
            body = (folder / rel).read_text()
            mid = len(body) // 2
            return body[mid:mid + probe].strip()[:200] in text
        for rel in ("rules.md", "where-things-go.md", "challenges.md", "inbox.md"):
            need(has(rel), f"Quick is missing {rel}")
        left_out = re.findall(r"`([^`]+)` \(not loaded on a Quick call", text)
        need(left_out, "Quick doesn't say which files it leaves out")
        for rel in left_out:
            need(not has(rel), f"Quick still has {rel} in full")
            need(f"`{rel}` (not loaded on a Quick call" in text, f"Quick doesn't say {rel} can be read when needed")
        mem = quick_context.memory_dir(folder) / "MEMORY.md"
        if mem.exists():
            first = next((l for l in mem.read_text().splitlines() if l.startswith("- ")), "")
            need(first and first in text, "Quick is missing Claude's memory")
        # The log: open commitments and only the last two days.
        log = (folder / "coaching/log.md").read_text()
        days = sorted({m for m in re.findall(r"^## (\d{4}-\d{2}-\d{2})", log, re.M)}, reverse=True)
        need("## Open commitments" in text, "Quick is missing the log's open commitments")
        first = _dt.date.today() - _dt.timedelta(days=quick_context.LOG_DAYS - 1)
        old = [d for d in days if _dt.date.fromisoformat(d) < first]
        need(not any(f"\n## {d} " in text for d in old), "Quick has log entries older than two days")
        # The sessions: Quick switches the CLI's CLAUDE.md off and brings its own text; Deep doesn't.
        pol = Policy(folder, dry_run=True)
        q = make_brain(config.MODEL_ALIASES["sonnet"], pol, load="quick")._options
        d = make_brain(config.MODEL_ALIASES["opus"], pol, load="deep")._options
        need(q.env.get("CLAUDE_CODE_DISABLE_CLAUDE_MDS") == "1" and "This is a Quick call" in q.system_prompt["append"],
             "the Quick session still loads CLAUDE.md, or misses its own text")
        need("CLAUDE_CODE_DISABLE_CLAUDE_MDS" not in d.env and "This is a Quick call" not in d.system_prompt["append"],
             "the Deep session doesn't load everything")
        for opts in (q, d):
            need(opts.setting_sources == ["user", "project", "local"], "settings (deny list, rules hook) don't load")
            need(any("send_message" in t for t in opts.disallowed_tools), "sending email isn't blocked")
        need((Call.__init__.__kwdefaults__ or {}).get("load", "x") is None
             and "load=load" in (config.ROOT / "app" / "bot.py").read_text(),
             "the call page's Quick or Deep doesn't reach the call's load")
        # Phase K: each switch does what it says (they're on unless switched off).
        if config.LIGHT_NOTES:
            need(not any(f"\n## {d} " in text for d in days), "K1: Quick still has log entries")
        for opts in (q, d):
            need((config.DOCS_SERVER in opts.disallowed_tools) == config.NO_DOCS, "K2: the Docs switch isn't followed")
            need(opts.env.get("ENABLE_TOOL_SEARCH") == ("true" if config.TOOLS_ON_DEMAND else "false"), "K3: the tool switch isn't followed")
        need("set_model(config.AFTER_CALL_MODEL)" in (config.ROOT / "app" / "call.py").read_text(), "K4: the after-call model switch is gone")
        kb = len(text) // 1024
        return f"Quick: rules, where things go, to-do list, mail list, notes, memory ({kb} KB); Deep: everything; {config.light_switches()}"


    # 16
    async def flow19(self) -> str:
        """H13: the status page on its own phone address, and the status button on the call page.
        No Claude turns; the live phone line is only read, never changed."""
        import subprocess as sp
        jv = ROOT
        # The call page: the bubble moved up, the status button below it, the page inside the app.
        page = (jv / "app/web/index.html").read_text()
        need('id="statbtn"' in page and 'id="statsheet"' in page and 'id="statframe"' in page,
             "the status button or its sheet is missing on the call page")
        need("right:16px; bottom:calc(84px" in page.split("#chatbtn {", 1)[1][:200]
             and "bottom:calc(16px" in page.split("#statbtn {", 1)[1][:200],
             "the chat bubble is not above the status button")
        need(":8444/" in page and ":4748/" in page and 'statFrame.setAttribute("src", want)' in page
             and '"about:blank"' in page, "the status sheet doesn't load the status page's own address, or keeps it loaded when closed")
        need("if (open) showStatus(false)" in page, "the chat and the status page can be open at the same time")
        # The status server, on this MacBook only, with its home-screen icon.
        def get(url, resolve=None):
            cmd = ["curl", "-s", "--max-time", "10", "-o", "-", "-w", "\n%{http_code} %{content_type}", url]
            if resolve:
                cmd[1:1] = ["--resolve", resolve]
            r = sp.run(cmd, capture_output=True)
            body, _, tail = r.stdout.rpartition(b"\n")
            code, _, ctype = tail.decode().partition(" ")
            return code, body, ctype
        who = sp.run(["lsof", "-nP", "-iTCP:4748", "-sTCP:LISTEN"], capture_output=True, text=True).stdout
        need("127.0.0.1:4748" in who and "*:4748" not in who, "the status server is not running, or listens on more than this MacBook")
        for path, kind in [("/", "text/html"), ("/roadmap.md", "markdown"), ("/manifest.webmanifest", "manifest"),
                           ("/apple-touch-icon.png", "image/png"), ("/icon-192.png", "image/png"), ("/icon-512.png", "image/png")]:
            code, body, ctype = get(f"http://127.0.0.1:4748{path}")
            need(code == "200" and kind in ctype and body, f"status {path} did not load ({code}, {ctype})")
        code, body, _ = get("http://127.0.0.1:4748/")
        need(b'rel="apple-touch-icon"' in body and b'rel="manifest"' in body, "the status page has no home-screen icon")
        # Its own Tailscale address: tailnet only, never Funnel, not the call line's port.
        ts = "/usr/local/bin/tailscale"
        st = sp.run([ts, "serve", "status", "--json"], capture_output=True, text=True).stdout
        cfg = json.loads(st or "{}")
        web = {k: v for k, v in (cfg.get("Web") or {}).items() if k.endswith(":8444")}
        need(web and any(h.get("Proxy") == "http://127.0.0.1:4748" for v in web.values() for h in (v.get("Handlers") or {}).values()),
             "Tailscale doesn't serve the status page on 8444")
        need(not any(k.endswith(":8444") and on for k, on in (cfg.get("AllowFunnel") or {}).items()),
             "the status page is on Funnel (the open internet)")
        host = next(iter(web)).rsplit(":", 1)[0]
        ip = sp.run([ts, "ip", "-4"], capture_output=True, text=True).stdout.split()[0]
        for path in ["/", "/roadmap.md", "/apple-touch-icon.png"]:
            code, body, _ = get(f"https://{host}:8444{path}", f"{host}:8444:{ip}")
            need(code == "200" and body, f"the phone address https://{host}:8444{path} did not answer ({code})")
        # Apart from the call line: stopping the line leaves 8444 alone; the routine keeps it up.
        stop = (jv / "app/stop.sh").read_text()
        need("8444" not in stop and "4748" not in stop, "stopping the call line touches the status page")
        tick = (jv / "routine/tick.py").read_text()
        need("status_page()" in tick and "phone.sh" in tick, "the routine doesn't keep the status page up")
        r = sp.run(["/bin/zsh", str(jv / "status/phone.sh")], capture_output=True, text=True)
        need(r.returncode == 0 and not r.stdout.strip(), f"phone.sh changed something on a second run: {r.stdout.strip()}")
        return f"https://{host}:8444 answers with its icon; status button below the chat bubble"

    async def flow18(self) -> str:
        """L: the queue of jobs from calls. No Claude turns and no job is started: the queue script
        on a copy of the roadmap, the status page reading it, the usage gate, what a call may do,
        and the call rules and the helper app being in place."""
        import subprocess as sp
        from policy import Policy, ALLOW, DENY
        jv = ROOT
        rm = self.tmp / "roadmap-L.md"
        rm.write_text(ROADMAP.read_text())
        env = {**os.environ, "JARVIS_ROADMAP": str(rm)}
        def jobs(*a):
            r = sp.run(["python3", str(jv / "routine/jobs.py"), *a], capture_output=True, text=True, env=env)
            need(r.returncode == 0, f"jobs.py {a[0]} failed: {r.stderr.strip()}")
            return r.stdout
        before = len(json.loads(jobs("next"))["ready"])
        jobs("add", "flow 18 test job · one")
        jobs("add", "flow 18 test job two", "--past-the-line")
        q = json.loads(jobs("next"))
        need(len(q["ready"]) == before + 2 and q["ready"][-1]["past"], "added jobs don't read back as ready, in order")
        n1, n2 = q["ready"][-2]["n"], q["ready"][-1]["n"]
        jobs("mark", str(n1), "running since 12:00")
        need("waits its turn" in jobs("add", "flow 18 three"), "a job added while one runs isn't told to wait")
        jobs("stop")
        need(any(j["state"] == "stop asked" for j in json.loads(jobs("next"))["running"]), "stop didn't ask the running job to stop")
        jobs("stop", str(n2))
        jobs("off")
        q = json.loads(jobs("next"))
        need(not q["on"] and all(j["n"] != n2 for j in q["ready"]), "off or cancel didn't stick")
        # L8: the mail check has its own switch, apart from the jobs.
        need(q["mail"] is True, "switching jobs off switched the mail check off too")
        jobs("mail-off")
        q = json.loads(jobs("next"))
        need(q["mail"] is False and not q["on"], "the mail check switch doesn't read back")
        # The status page reads the same queue, and the status block still reads clean.
        js = f"""import {{ parseRoadmap }} from {json.dumps(str(jv / 'status/parse.mjs'))};
import {{ readFileSync }} from 'node:fs';
const r = parseRoadmap(readFileSync({json.dumps(str(rm))}, 'utf8'));
console.log(JSON.stringify({{problems: r.problems, on: r.queue.on, n: r.queue.jobs.length}}));"""
        r = sp.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True)
        d = json.loads(r.stdout)
        need(not d["problems"] and d["on"] is False and d["n"] >= 3, f"the status page reads the queue wrong: {d}")
        # The usage gate answers without starting anything.
        g = sp.run(["node", str(jv / "status/save-usage.mjs"), "--gate"], capture_output=True, text=True)
        need(g.returncode in (0, 2) and g.stdout.startswith(("OK", "STOP")), f"the usage gate didn't answer: {g.stdout}{g.stderr}")
        # What a call may do with the queue.
        pol = Policy(config.FOLDER)
        q_ = f'python3 "{ROOT}/routine/jobs.py"'  # M1: HQ's own script
        need(pol.decide("Bash", {"command": f'{q_} add "build X"'}).verdict == ALLOW, "a call can't add a job")
        need(pol.decide("Bash", {"command": f"{q_} stop"}).verdict == ALLOW, "a call can't stop a job")
        need(pol.decide("Bash", {"command": f"{q_} done 3"}).verdict == DENY, "a call may mark a job done")
        need("jobs.py\" add" in config.VOICE_RULES and "clear go" in config.VOICE_RULES, "the call rules don't say how to queue a job")
        app = Path.home() / "Applications/Jarvis Routine.app"
        need(app.exists(), "the Jarvis Routine helper app isn't built")
        need("--no-chrome" in (jv / "routine/tick.py").read_text() and "-g" in (jv / "routine/tick.py").read_text(),
             "jobs would ask about Chrome or open in front")
        # L7: windows close themselves once their chat ends; L8: the mail check is started by the
        # routine (since H30 also next to a job), with only reading tools and the mail list's own commit.
        tick = (jv / "routine/tick.py").read_text()
        need("CLOSE_WINDOW" in tick and "exec {CLAUDE}" not in tick and "end_chat(pid)" in tick,
             "a job's window wouldn't close by itself")
        need("if mail_running():" in tick and "start_mail()" in tick and "dontAsk" in tick,
             "the mail check isn't started by the routine, one at a time, without asking")
        for t in ("send_message", "reply", "forward", "create_draft", "label_message", "trash_thread", "update_message_labels"):
            need(f'"{t}"' in tick, f"the mail check may {t}")
        mc = (jv / "routine/mail-check.md").read_text()
        need("never send, reply, forward or draft" in mc and "sh .claude/mail-commit.sh" in mc,
             "the mail check's instructions lost their hard limits")
        return f"queue add/stop/cancel/off read back; mail switch apart; windows close; page reads it; gate says {g.stdout.split('.')[0]}; call may add and stop, not mark done"


    async def flow20(self) -> str:
        """L9/L10: the usage check, without Claude. What a call may do, the call rules, the routine
        running it every minute, and the mail check saving the usage its own run brings back."""
        from policy import Policy, ALLOW, DENY
        jv = ROOT
        pol = Policy(config.FOLDER)
        u = f'python3 "{ROOT}/routine/usage-check.py"'  # M1: HQ's own script
        need(pol.decide("Bash", {"command": u}).verdict == ALLOW, "a call can't run the usage check")
        need(pol.decide("Bash", {"command": f"{u} --fresh"}).verdict == DENY, "a call may run the usage check with options")
        need("usage-check.py" in config.VOICE_RULES and "how old they are" in config.VOICE_RULES,
             "the call rules don't say to read the latest usage with its age")
        tick = (jv / "routine/tick.py").read_text()
        main_ = tick.split('if __name__ == "__main__":')[1]
        need("usage()" in main_.split("tick()")[0], "the routine doesn't run the usage check every minute")
        need("--output-format stream-json" in tick and "{json.dumps(STREAM)}" in tick,
             "the mail check doesn't save the usage its own run brings back")
        need("usage-check.command" not in tick and "Jarvis usage check" not in tick,
             "the routine still opens a window for a usage check")
        uc = (jv / "routine/usage-check.py").read_text()
        need("bin/claude" not in uc and '"-p"' not in uc, "the usage check can still start Claude (a paid run)")
        return "a call may run it, no options; every minute by the routine; mail check saves its own usage; no Claude anywhere"

    async def flow21(self) -> str:
        """L10: the usage check reads and shows the latest saved numbers, no Claude. In a copy: the
        mail check's stream saves the usage; a newer one is put on the page with its own time; a newer
        full reading from a normal chat isn't overwritten; Weekly Fable is kept. Then the real one."""
        jv = ROOT
        tmp = Path(tempfile.mkdtemp(prefix="usage-", dir=config.SCRATCH))
        try:
            for f in ("routine/usage-check.py", "routine/stream-usage.py", "status/save-usage.mjs",
                      "status/parse.mjs", "status/usage.mjs", "status/paths.mjs", "roadmap.md"):
                dst = site_roadmap(tmp) if f == "roadmap.md" else tmp / f
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROADMAP if f == "roadmap.md" else jv / f, dst)
            (tmp / ".status").mkdir()
            saved = tmp / ".status/usage.json"
            old = datetime.now().astimezone() - timedelta(hours=2)
            saved.write_text(json.dumps({"checkedAt": old.isoformat(), "by": "a normal chat", "readable": True,
                "plan": "Max", "limits": [{"label": "5-hour limit", "percent": 5, "resetsAt": None},
                {"label": "Weekly · all models", "percent": 30, "resetsAt": None},
                {"label": "Weekly · Fable", "percent": 21, "resetsAt": None}], "context": None}))
            stream = "\n".join(json.dumps(x) for x in (
                {"type": "system"},
                {"type": "rate_limit_event", "rate_limit_info": {"unifiedWindows": {
                    "five_hour": {"utilization": 0.17, "resetsAt": int(time.time()) + 3600},
                    "seven_day": {"utilization": 0.45, "resetsAt": int(time.time()) + 86400}}}},
                {"type": "result", "result": "Nothing new."})) + "\n"
            r = subprocess.run(["python3", str(tmp / "routine/stream-usage.py")], input=stream,
                               capture_output=True, text=True, timeout=30)
            need("Nothing new." in r.stdout and "usage saved" in r.stdout, f"the mail check's stream wasn't read: {r.stdout}")
            r = subprocess.run(["python3", str(tmp / "routine/usage-check.py")], capture_output=True, text=True, timeout=60)
            got = json.loads(saved.read_text())
            fresh = {l["label"]: l["percent"] for l in got["limits"] if not l.get("kept")}
            need(fresh == {"5-hour limit": 17, "Weekly · all models": 45}, f"the mail check's usage wasn't put on the page: {fresh}")
            need(got["by"] == "usage check · from the hourly mail check", f"wrong source on the page: {got['by']}")
            need([l for l in got["limits"] if "Fable" in l["label"]][0].get("kept"), "Weekly Fable wasn't kept")
            need("17%  5-hour limit  (read just now)" in r.stdout, f"the report doesn't say the age: {r.stdout}")
            # A newer full reading from a normal chat stays.
            newer = dict(got, checkedAt=(datetime.now().astimezone() + timedelta(minutes=1)).isoformat(), by="a normal chat",
                         limits=[dict(l, kept=False) for l in got["limits"] if not l.get("kept")])
            saved.write_text(json.dumps(newer))
            subprocess.run(["python3", str(tmp / "routine/usage-check.py")], capture_output=True, text=True, timeout=60)
            need(json.loads(saved.read_text())["by"] == "a normal chat", "a newer reading from a normal chat was overwritten")
            # An old reading is reported as old.
            saved.write_text(json.dumps(dict(newer, checkedAt=old.isoformat())))
            (tmp / "scratch/routine/usage-live.json").unlink()
            r = subprocess.run(["python3", str(tmp / "routine/usage-check.py")], capture_output=True, text=True, timeout=60)
            need("read 2 h 0 min ago" in r.stdout and "These numbers are old" in r.stdout, f"an old reading isn't called old: {r.stdout}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        # The real one: reads and reports, no Claude.
        r = subprocess.run(["python3", str(jv / "routine/usage-check.py")], capture_output=True, text=True, timeout=60)
        need(r.returncode == 0 and "5-hour limit" in r.stdout, f"the usage check failed: {r.stdout.strip()} {r.stderr.strip()}")
        first = r.stdout.strip().splitlines()[0]
        return f"stream saved; newer shown with its time; normal chat's reading kept; old called old; now: {first}"

    async def flow16(self) -> str:
        """J: the hourly mail check (the writer) and the start of every chat and call (the readers)
        agree on one shape. No Claude turns: the real list, the writer's own template and the readers
        are checked as they are."""
        import open_loops
        from call import Call
        import quick_context

        folder = config.FOLDER
        inbox = (folder / open_loops.INBOX).read_text()
        loops = open_loops.read(folder)
        need(loops.found, "the mail list is missing its Very important or To check section")
        need(inbox.index(open_loops.VERY_IMPORTANT) < inbox.index(open_loops.TO_CHECK),
             "Very important doesn't come before To check")
        # The writer's template, filled in, must read back as one item, without its link.
        m = re.search(r"`(- <received date> · .*?Status: new · \[Gmail\]\(<link>\))`", inbox)
        need(m, "the mail list doesn't give the writer the exact shape of a very important line")
        line = (m.group(1).replace("<received date>", "2026-10-09").replace("<sender>", "CJIB")
                .replace("<subject>", "Boete").replace("<link>", "https://mail.google.com/x"))
        line = re.sub(r"<[^>]+>", "test", line)
        fake = inbox.replace(open_loops.VERY_IMPORTANT + "\n", open_loops.VERY_IMPORTANT + "\n\n" + line + "\n", 1)
        tmp = self.tmp / "loops"
        tmp.mkdir(exist_ok=True)
        (tmp / open_loops.INBOX).write_text(fake)
        back = open_loops.read(tmp)
        need(len(back.very_important) == len(loops.very_important) + 1, "the filled-in template didn't read back as one item")
        need("CJIB" in back.very_important[0] and "mail.google" not in back.very_important[0],
             f"the item read back wrong: {back.very_important[0]!r}")
        need("very important" in open_loops.call_note(back).lower(), "the call's note doesn't carry the item")
        need(open_loops.call_note(open_loops.OpenLoops([], 3, True)) == "", "an empty list still gives the call a note")
        # The writer: the hourly task follows the same list and section.
        task = folder / "inbox.md"  # M5: the routine's mail check follows the steps in inbox.md
        mc = (ROOT / "routine/mail-check.md").read_text()
        need(task.exists() and "## Very important" in task.read_text() and "What counts as very important" in task.read_text()
             and "## Very important" in mc, "the hourly mail check doesn't write the Very important section")
        # The readers: the computer chat, Quick and Deep.
        claude_md = (folder / "CLAUDE.md").read_text()
        need("@inbox.md" in claude_md and "very important items first" in claude_md,
             "the computer chat's start doesn't read the very important items first")
        need(open_loops.VERY_IMPORTANT in quick_context.build(folder), "Quick doesn't have the Very important section")
        need("very important open items" in config.VOICE_RULES, "the call rules don't say to bring them up")
        need((Call.__init__.__kwdefaults__ or {}).get("loops", "x") is None
             and "open_loops.call_note" in (config.ROOT / "app" / "call.py").read_text(),
             "the call's warm-up doesn't read the open loops")
        return (f"one shape for writer and readers; the list now has {len(loops.very_important)} very important, "
                f"{loops.to_check} to check")

    # 17
    async def flow17(self) -> str:
        """J2 on a real call: a very important item (a made-up one, the real list is not touched)
        is named in the first reply, after answering what he says."""
        import open_loops

        fake = open_loops.OpenLoops(
            ["2026-10-09 · CJIB · Boete · a fine of 95 euros for cycling without a light, to pay before "
             "23 October · Why: money with a date · Status: new"], 2, True)
        live = Live()
        try:
            await live.open(self.tmp, loops=fake)
            need(live.ready, "the test call could not be opened")
            need("CJIB" in live.call.open_loops_note, "the warm-up message didn't carry the item")
            r = await live.ask("Hey, can you hear me?", "first words")
            reply = norm(r["reply"])
            need(any(w in reply for w in ("fine", "cjib", "95", "ninety five", "light")),
                 f"the first reply didn't name the very important item: {r['reply']!r}")
            return f"first reply named it: {r['reply'][:120]!r}"
        finally:
            await live.close()
            self.turns += live.turns_used

    # 23
    async def flow23(self) -> str:
        """H24: a buzz when holding the talk button turns into talking, and Hang up asks first.
        No Claude turns; the page is only read (a phone's buzz can't be felt from here)."""
        page = (APP / "web/index.html").read_text()
        need("function buzz()" in page and "navigator.vibrate" in page and 'setAttribute("switch", "")' in page,
             "the buzz is missing (vibrate for Android, the switch tick for the iPhone)")
        need("if (oldIos()) { try { click(); }" in page and "< 18" in page, "no click for an iPhone that can't buzz (before iOS 18)")
        hold = page.split("holdTimer = setTimeout(() => {", 1)[1].split("}, HOLD_MS)", 1)[0]
        need("holding = true" in hold and "buzz()" in hold, "the buzz isn't tied to the moment the hold turns into talking")
        tap = page.split("function letGo(ev)", 1)[1].split("\n}", 1)[0]
        need("buzz()" not in tap, "a short tap (mute) buzzes too")
        need('id="hangask"' in page and ">Are you sure?<" in page and 'id="hangyes"' in page and 'id="hangno"' in page,
             "the Are you sure? question is missing on the call page")
        click = page.split('btn.addEventListener("click"', 1)[1].split("\n", 1)[0]
        need("askHangup(true)" in click and "hangup()" not in click, "tapping Hang up ends the call without asking")
        yes = page.split('getElementById("hangyes").addEventListener("click", () => {', 1)[1].split("});", 1)[0]
        need("Date.now() - hangAskedAt < 500" in yes and 'askHangup(false); if (state === "live") hangup();' in yes,
             "the question's Hang up doesn't end the call, or a double tap on Hang up gets through")
        need('getElementById("hangno").addEventListener("click", () => askHangup(false))' in page
             and 'hangShade.addEventListener("click", () => askHangup(false))' in page,
             "Stay on, or a tap beside the question, doesn't keep the call")
        need("function cleanup(text) {\n  askHangup(false);" in page, "the question stays open after the call ends by itself")
        # H38: a rule may be shared with Cancel's question ("#hangask, #cxask {").
        z = lambda sel: int(re.search(re.escape(sel) + r"(?:, [#.\w-]+)* \{[^}]*?z-index:(\d+)", page).group(1))
        need(z("#hangask") > max(z("#chat"), z("#statsheet"), z("#chatbtn"), z("#statbtn"), z("#settings")),
             "the question can sit under the chat or the status page")
        return "buzz when Talking… starts (not on a tap); Hang up asks Are you sure?, Stay on keeps the call"

    # 24
    async def flow24(self) -> str:
        """H31: Cancel while she thinks. The page is read; on the call a typed question is cancelled
        the moment her turn starts, then a second question shows she only answers the new one."""
        page = (APP / "web/index.html").read_text()
        need('id="cancel"' in page and ">Cancel<" in page, "the Cancel button is missing from the call page")
        need(page.index('id="mute"') < page.index('id="cancel"') < page.index('id="orbwrap"'),
             "Cancel doesn't sit next to the talk button")
        need('m.type === "jarvis-cancellable") showCancel(m.on === true)' in page,
             "Cancel isn't tied to the server saying it can still be taken back")
        tap = page.split("function sendCancel() {", 1)[1].split("\n}", 1)[0]  # H38: the tap goes through sendCancel
        need('type: "cancel"' in tap and 'showOrb("listening")' in tap,
             "a tap on Cancel doesn't send it, or the thinking circle and tick don't stop at once")
        need('m.type === "jarvis-cancelled") markCancelled()' in page and ".me.cancelled" in page,
             "the chat doesn't mark his line as cancelled")
        bot_src = (APP / "bot.py").read_text()
        need('message.get("type") == "cancel"' in bot_src and "cancel_turn(ptt.user_aggregator, call.llm, call_state)" in bot_src
             and "call.llm.on_cancellable = cancellable" in bot_src, "the call server doesn't handle Cancel")

        from pipeline import cancel_turn, type_to_jarvis

        live = await self.get_live()
        llm = live.llm
        agg = live.ptt.user_aggregator
        need(not await cancel_turn(agg, llm, live.call_state), "Cancel did something with nothing to cancel")
        flags: list[bool] = []
        llm.on_cancellable = flags.append
        n = len(llm.turns)
        say(f"typing, then cancelling: {Q_CANCEL}")
        need(await type_to_jarvis(live.worker, llm, live.call_state, Q_CANCEL), "the typed message was refused")
        await live.wait_for(lambda: llm.cancellable, 30, "her turn to start (Cancel showing)")
        t0 = time.perf_counter()
        need(await cancel_turn(agg, llm, live.call_state), "Cancel was refused while she was thinking")
        need(live.call_state.state == "listening", f"the thinking didn't stop at once ({live.call_state.state})")
        await live.wait_for(lambda: not llm._replying, 20, "the cancelled turn to stop")
        await asyncio.sleep(3.0)
        turn = llm.turns[n]
        need(turn.get("cancelled") and turn["interrupted"], f"the turn wasn't dropped: { {k: turn.get(k) for k in ('cancelled', 'interrupted', 'reply', 'first_text_s')} }")
        need(not turn["reply"].strip(), f"she answered the cancelled question: {turn['reply']!r}")
        need(live.after_tts.first("audio", t0 + 0.5)[0] is None, "she made a sound after Cancel")
        need(flags[:2] == [True, False] and not llm.cancellable, f"Cancel showed or hid at the wrong moments: {flags}")
        tx = live.call.transcript.path.read_text()
        need(f"**{config.USER_LABEL}:** {Q_CANCEL} *(typed)* *(cancelled)*" in tx, "the transcript doesn't mark the line as cancelled")
        need("rome" not in norm(tx.split(Q_CANCEL, 1)[1]) and "paris" not in norm(tx.split(Q_CANCEL, 1)[1]),
             "the transcript has an answer to the cancelled question")

        m = len(llm.turns)
        say(f"typing: {Q_AFTER_CANCEL}")
        t1 = time.perf_counter()
        need(await type_to_jarvis(live.worker, llm, live.call_state, Q_AFTER_CANCEL), "the second message was refused")
        await live.wait_for(lambda: len(llm.turns) > m and not llm._replying, 90, "Claude's reply to the second question")
        await live.wait_for(lambda: not live.call.fillers.talking
                            and live.after_tts.first("tts_stopped", t1)[0] is not None, 30, "the voice to finish")
        nxt = llm.turns[m]
        reply = " ".join(t["reply"].strip() for t in llm.turns[m:]).strip()
        say(f"   Jarvis said: {reply!r}")
        need(nxt["words"] == Q_AFTER_CANCEL, f"the cancelled words came back into the next turn: {nxt['words']!r}")
        need("cancelled what he said" in nxt["sent"] and Q_CANCEL[:20] in nxt["sent"], "Claude wasn't told about the cancel")
        need(f"{config.USER} cut in" not in nxt["sent"], "the cancel was told to Claude as a cut-in")
        need("four" in norm(reply) or "4" in reply, f"no answer to the new question: {reply!r}")
        need("paris" not in norm(reply), f"she answered the cancelled question anyway: {reply!r}")
        return "cancelled before a word: no answer, no sound, thinking stopped, marked cancelled; the next question answered alone"

    async def flow25(self) -> str:
        """H30: the routines respond, not only report. No Claude and nothing live is changed: the
        incident log, the mail check's catch-up and retry, and the commit lock run on copies in the
        test folder; the status page and the watchdog are checked for their parts."""
        import importlib, subprocess as sp, sys as _sys, urllib.request
        jv = ROOT
        _sys.path.insert(0, str(jv / "routine"))
        import incidents, routines, tick
        importlib.reload(incidents)
        # 1. The incident log, on a copy: down, why, what was done, back.
        incidents.FILE = str(self.tmp / "incidents.json")
        incidents.EVENTS = str(self.tmp / "events.jsonl")
        incidents.down("call", "Down: calls won't connect", at=1000)
        incidents.down("call", "again")  # the same outage: no second entry
        incidents.fix("call", "started it again", at=1200)
        incidents.up("call", at=1300)
        incidents.past("helper", 500, 900, "The MacBook restarted", [(900, "macOS started it at login")])
        log_ = incidents.read()["incidents"]
        need(len(log_) == 2 and log_[0]["key"] == "helper", f"the incident log isn't in order: {log_}")
        c = log_[1]
        need(c["why"] == "Down: calls won't connect" and c["back"] == 1300 and c["fixes"][0]["what"] == "started it again",
             f"an incident doesn't keep why, fix and back: {c}")
        open(incidents.EVENTS, "w").write(json.dumps({"at": 950, "what": "The helper wasn't running: started it again"}) + "\n")
        need(incidents.watchdog_events() == [(950, "The helper wasn't running: started it again")] and incidents.watchdog_events() == [],
             "the watchdog's events aren't picked up once")
        # 2. The mail check: a missed hour is caught up with its why; a failed run is tried again.
        tick.incidents = incidents
        # H42's failure counter on its own copy too, so this flow never writes a made-up failure into the real one.
        tick.failures.SUPPORT, tick.failures.FILE = str(self.tmp), str(self.tmp / "failures.json")
        for name in ("MAIL_LAST", "MAIL_RETRY", "MAIL_STATE", "MAIL_PID"):
            setattr(tick, name, str(self.tmp / name.lower()))
        routines.FILE = str(self.tmp / "routines.json")
        started = []
        tick.start_mail = lambda: started.append(time.time())
        now = time.time()
        open(tick.MAIL_LAST, "w").write(str(int(now // 3600 * 3600 - 3600 + 30)))  # last ran just after the previous hour
        incidents.past("helper", now // 3600 * 3600 - 120, now - 30, "The MacBook was asleep", [])
        if now % 3600 > tick.MAIL_LATE:
            tick.mail({"mail": True, "on": True})
            inc = incidents.is_down("mail")
            need(started and inc and "helper wasn't running" in inc["why"] and "Started the missed run" in inc["fixes"][0]["what"],
                 f"a missed mail check wasn't caught up with its why: {inc}")
        started.clear()
        tick.mail({"mail": False, "on": True})
        need(not started and routines.read()["mail"]["state"] == "off", "a switched-off mail check still started")
        open(tick.MAIL_LAST, "w").write(str(int(now)))
        log = self.tmp / "mail.log"
        json.dump({"pid": None, "started": now - 100}, open(tick.MAIL_STATE, "w"))
        tick.RUN = str(self.tmp)
        open(self.tmp / "mail.log", "w").write("--- 2026-10-10 16:00:00\nsomething broke\n--- exit 1\n")
        need(tick.mail_running() is False, "a finished mail check reads as running")
        r = json.load(open(tick.MAIL_RETRY))
        need(r["n"] == 1 and r["at"] > now, f"a failed mail check isn't tried again: {r}")
        json.dump({**r, "at": now - 1}, open(tick.MAIL_RETRY, "w"))
        need(tick.mail_due(), "the retry doesn't make the mail check due")
        # 3. Jobs waiting for the usage line show as waiting, with why.
        tick.GATE_NOTE = str(self.tmp / "gate-note")
        open(tick.GATE_NOTE, "w").write("31 STOP: 5-hour limit at 72%, stop line 70%")
        tick.jobs_line({"running": [], "ready": [{"n": 31}], "held": [], "on": True})
        j = routines.read()["jobs"]
        need(j["state"] == "waiting" and "usage line" in j["text"] and "72%" in j["text"], f"a waiting job doesn't show as waiting: {j}")
        # 4. The commit lock: one at a time, and only the named files are committed.
        repo = self.tmp / "repo"
        repo.mkdir()
        hq = self.tmp / "hq"  # M1: the lock is HQ's; git runs in the workspace, a link to the user's repo
        (hq / "routine").mkdir(parents=True)
        for f in ("gitlock.py", "hqpaths.py"):
            (hq / "routine" / f).write_text((jv / "routine" / f).read_text())
        (hq / "workspace").symlink_to(repo)
        g = lambda *a: sp.run(["git", *a], cwd=repo, capture_output=True, text=True)
        sp.run(["git", "init", "-q", "--bare", str(self.tmp / "remote.git")])
        g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
        g("remote", "add", "origin", str(self.tmp / "remote.git"))
        (repo / "inbox.md").write_text("a"); (repo / "job.md").write_text("b")
        g("add", "inbox.md", "job.md"); g("commit", "-qm", "init"); g("push", "-q", "-u", "origin", "HEAD")
        (repo / "inbox.md").write_text("a2"); (repo / "job.md").write_text("b2"); g("add", "job.md")
        lock = hq / "routine/gitlock.py"
        hold = sp.Popen(["python3", str(lock), "run", "sleep", "2"])
        time.sleep(0.4)
        t0 = time.time()
        r = sp.run(["python3", str(lock), "commit", "Mail check: test", "inbox.md"], capture_output=True, text=True)
        waited = time.time() - t0
        hold.wait()
        need(r.returncode == 0, f"the locked commit failed: {r.stderr}")
        need(waited > 1.2, f"the commit didn't wait for the lock ({waited:.1f} s)")
        files = g("show", "--name-only", "--format=", "HEAD").stdout.split()
        need(files == ["inbox.md"] and g("status", "--porcelain").stdout.startswith("M  job.md"),
             f"the mail commit took a job's staged file: {files}")
        need(not g("status", "-sb").stdout.split("\n")[0].endswith("]"), "the mail commit wasn't pushed")
        mc = (config.FOLDER / ".claude/mail-commit.sh").read_text()
        need("HQ/routine/gitlock.py\" commit" in mc and "inbox.md" in mc, "the mail check's commit doesn't go through the lock")
        # 5. The status page and the watchdog have their parts.
        page = (jv / "status/index.html").read_text()
        need("function drawIncidents" in page and ".routine.waiting i" in page and "'waiting'" in page,
             "the status page has no incident log or no waiting colour")
        with urllib.request.urlopen("http://127.0.0.1:4748/routines.json", timeout=5) as resp:
            need("incidents" in json.loads(resp.read()), "the status server doesn't serve the incident log")
        wd = (jv / "routine/watchdog.py").read_text()
        installed = Path.home() / "Library/Application Support/JarvisVA/watchdog.py"
        need("events.jsonl" in wd and installed.exists() and installed.read_text() == wd,
             "the watchdog doesn't log what it fixes, or the installed one is old")
        t = (jv / "routine/tick.py").read_text()
        need("def watchdog_check" in t and "def helper_gap" in t and "kickstart" in t and "app\", \"start.sh" in t,
             "the helper doesn't check the watchdog, its own gaps, or the call line")
        return f"incident log keeps why, fix and back; missed mail caught up, failed one retried; waiting jobs yellow; commits wait their turn ({waited:.1f} s) and take only their own files; page, server and watchdog in place"

    # 26
    async def flow26(self) -> str:
        """H32: a low sound when push to talk switches on. No Claude turns; the page is read
        (the sound itself can only be heard on the phone)."""
        page = (APP / "web/index.html").read_text()
        need("function talkSound()" in page, "the talk sound is missing")
        hold = page.split("holdTimer = setTimeout(() => {", 1)[1].split("}, HOLD_MS)", 1)[0]
        need("holding = true" in hold and "talkSound()" in hold and "buzz()" in hold,
             "the talk sound (or the buzz) isn't tied to the moment the hold turns into talking")
        need(hold.index("setMuted(false, true)") < hold.index("talkSound()"),
             "the sound plays before the mic opens, so the gate can't hold the mic shut")
        tap = page.split("function letGo(ev)", 1)[1].split("\n}", 1)[0]
        need("talkSound()" not in tap, "a short tap (mute) plays the talk sound too")
        need("clearTimeout(talkGate)" in tap, "letting go during the sound can open the mic again")
        fn = page.split("function talkSound()", 1)[1].split("\nfunction ", 1)[0]
        freqs = [float(f) for f in re.findall(r"frequency\.(?:setValueAtTime|exponentialRampToValueAtTime)\((\d+)", fn)]
        tick = page.split("function tick()", 1)[1].split("\n}", 1)[0]
        tick_low = min(float(f) for f in re.findall(r"frequency\.(?:setValueAtTime|exponentialRampToValueAtTime)\((\d+)", tick))
        need(freqs and max(freqs) * 2 <= tick_low, f"the talk sound isn't a lot lower than the thinking tick ({freqs} vs {tick_low})")
        need("micOpen(false)" in fn and "TALK_SOUND_MS" in fn and "if (holding && !muted) micOpen(true)" in fn,
             "the mic isn't kept silent while the sound plays")
        down = page.split('muteBtn.addEventListener("pointerdown"', 1)[1].split("});", 1)[0]
        need("startAudio()" in down, "the audio isn't unlocked inside the touch (the iPhone may stay silent)")
        need("if (oldIos()) { try { click(); }" in page and 'setAttribute("switch", "")' in page,
             "the H24 buzz or click changed")
        return f"low sound ({int(max(freqs))}→{int(min(freqs))} Hz, tick {int(tick_low)}+ Hz) on Talking…, not on a tap; mic silent while it sounds; audio unlocked in the touch"

    # 27
    async def flow27(self) -> str:
        """F10: the talk button stays green (Talking…) the whole time it's held. No Claude turns: the
        real call page runs in a headless browser, with a fake live call, and its button is held down."""
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const press = () => muteBtn.dispatchEvent(new PointerEvent("pointerdown", { pointerId: 1, bubbles: true }));
  const lift = () => document.dispatchEvent(new PointerEvent("pointerup", { pointerId: 1, bubbles: true }));
  const server = st => onServerMessage({ data: JSON.stringify({ type: "jarvis-state", state: st }) });
  async function held(name, ms, during) {
    let bad = 0, n = 0, seen = "";
    for (let t = 0; t < ms; t += 250) {
      if (during) during(t);
      await wait(250); n++;
      if (!muteBtn.classList.contains("talk") || muteBtn.textContent !== "Talking…") { bad++; seen = muteBtn.className + "/" + muteBtn.textContent; }
    }
    out.push(name + ":" + (bad ? "LOST " + bad + "/" + n + " (" + seen + ")" : "ok"));
  }
  setState("live", "On the call");
  press(); await wait(500); server("hearing");
  await held("long", 12000);
  lift(); await wait(100);
  out.push("letgo:" + (muteBtn.classList.contains("transcribing") ? "ok" : "NOT YELLOW (" + muteBtn.className + ")"));
  await wait(700); press(); await wait(500); server("hearing");
  await held("again", 12000);
  lift(); await wait(300); server("thinking"); await wait(300); server("listening"); await wait(300);
  press(); await wait(500);
  await held("messages", 4000, t => {
    if (t === 500) server("hearing"); if (t === 1000) server("thinking"); if (t === 1500) server("speaking");
    if (t === 2000) server("listening"); if (t === 2500) setState("live", "On the call"); if (t === 3000) showCancel(true);
  });
  lift(); await wait(300);
  out.push("after:" + (muteBtn.classList.contains("talk") ? "STILL GREEN" : "ok"));
  const pre = document.createElement("pre"); pre.id = "f10"; pre.textContent = "F10RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f = self.tmp / "f10.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", "--autoplay-policy=no-user-gesture-required",
                                          "--virtual-time-budget=60000", "--dump-dom", f.as_uri()], timeout=120)
        m = re.search(r'<pre id="f10">F10RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        res = m.group(1)
        say(f"   {res}")
        need(all(part.endswith(":ok") for part in res.split(" | ")), f"the button lost its colour: {res}")
        return "held 12 s, held again right after letting go (past the 8 s Transcribing timer), held through server updates: green all the time; yellow on letting go"

    async def flow28(self) -> str:
        """H33: the jobs in the routines graph. No Claude turns. A copy of the status page runs on its own
        port from a scratch folder, with a made-up queue and history: the server writes the running job's
        state every minute and serves each job's runs (backfill only before its own record starts); the page
        draws a Jobs row on top, folded closed, with an arrow to one bar per job, in the status band's own
        colours, with its own legend; a running routine is no longer warning yellow."""
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the status page in")
        node = shutil.which("node") or "/opt/homebrew/bin/node"
        site = self.tmp / "h33"
        shutil.copytree(ROOT / "status", site / "status", ignore=shutil.ignore_patterns("icons"))
        (site / ".status").mkdir()
        road = ROADMAP.read_text()
        road = "# 🧪 TESTING" + road[road.index("\n"):]
        road = re.sub(r"^- Job \d+ · .*\n", "", road, flags=re.M)
        road = re.sub(r"^(\*\*Mail check:\*\*.*\n)", r"\1\n- Job 98 · done 10:00 · agreed 2026-10-10 09:00 · Build H33 on the Jarvis VA roadmap\n"
                      r"- Job 99 · running since 10:05 · agreed 2026-10-10 09:01 · Fix F10 on the Jarvis VA roadmap\n", road, count=1, flags=re.M)
        site_roadmap(site).write_text(road)
        now = int(time.time())
        t0 = now - 30 * 60
        ok = {k: "ok" for k in ["helper", "watchdog", "mail", "jobs", "usage", "phone", "call"]}
        hist = []
        for i in range(30):
            j = [{"n": 98, "st": "BUILDING"}] if i < 10 else [{"n": 98, "st": "RELEASING"}] if i < 15 else \
                [{"n": 98, "st": "DONE"}] if i == 15 else [{"n": 99, "st": "TESTING"}]
            hist.append(json.dumps({"t": t0 + i * 60, "s": {**ok, "jobs": "running"}, "j": j}))
        (site / ".status/routines-history.jsonl").write_text("\n".join(hist) + "\n")
        (site / ".status/jobs-backfill.json").write_text(json.dumps({"segments": [
            {"n": 97, "st": "STOPPED", "start": now - 3600, "end": now - 2700},
            {"n": 97, "st": "BUILDING", "start": now - 600, "end": now - 300}], "texts": {"97": "Build H23 on the roadmap"}}))
        port = 4791
        env = {**os.environ, "JARVIS_STATUS_PORT": str(port)}
        proc = subprocess.Popen([node, str(site / "status/server.mjs"), "--quiet"], env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                if http_get("/routines.json", base)[0] == 200:
                    break
                await asyncio.sleep(0.2)
            await asyncio.sleep(0.5)
            last = json.loads((site / ".status/routines-history.jsonl").read_text().splitlines()[-1])
            need(last.get("j") == [{"n": 99, "st": "TESTING"}], f"the server didn't write the running job's state: {last.get('j')}")
            _, body, _ = http_get("/jobs-history.json?h=6", base)
            segs = json.loads(body)["segments"]
            runs = [(g["n"], g["st"], bool(g.get("filled"))) for g in segs]
            need(runs == [(97, "STOPPED", True), (98, "BUILDING", False), (98, "RELEASING", False), (98, "DONE", False), (99, "TESTING", False)],
                 f"the job runs aren't right: {runs}")
            need(segs[-1]["end"] >= now + 60, "the running job's bar doesn't reach now")
            _, page, _ = http_get("/", base)
            css = page.decode()
            colours = {"BUILDING": "#8a5a00", "TESTING": "#0f6e66", "RELEASING": "#6639ba", "WAITING": "#0b5fbf", "DONE": "#1a7f37", "STOPPED": "#b42318"}
            for st, hx in colours.items():
                need(re.search(rf"\.{st}\b[^{{]*\{{ --band: {hx}; \}}", css), f"the status band colour for {st} isn't {hx}")
            need(".strip b.job { background: var(--band); }" in css and ".key i.job { background: var(--band); }" in css,
                 "the job bars and legend don't take the band colours")
            for rule in [".strip b.running", ".key i.running", ".routine.running i", ".light.running"]:
                need(f"{rule} {{ background: var(--running); }}" in css, f"{rule} is still a warning colour")
            harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 40 && !document.querySelector('.jobs-toggle'); i++) await wait(250);
  const t = document.querySelector('.jobs-toggle');
  const rgb = sel => { const e = document.querySelector(sel); return e ? getComputedStyle(e).backgroundColor : 'none'; };
  out.push('toggle:' + (t ? t.getAttribute('aria-expanded') : 'missing'));
  out.push('first:' + (t && t.closest('.lanes').firstElementChild === t.closest('.lane') ? 'ok' : 'no'));
  out.push('folded:' + [...document.querySelectorAll('.lane.jobs .strip b.job')].map(b => b.className.split(' ')[1]).join(','));
  out.push('legend:' + [...document.querySelectorAll('.jobs-key span')].map(s => s.textContent).join(','));
  out.push('colours:' + ['BUILDING','TESTING','RELEASING','WAITING','DONE','STOPPED'].map(s => rgb('.jobs-key i.' + s)).join(','));
  const r = document.createElement('div'); r.className = 'strip'; const b = document.createElement('b'); b.className = 'running'; r.append(b); document.body.append(r);
  out.push('running:' + getComputedStyle(b).backgroundImage.slice(0, 26));
  t.click(); await wait(600);
  out.push('open:' + document.querySelector('.jobs-toggle').getAttribute('aria-expanded'));
  out.push('lanes:' + [...document.querySelectorAll('.lane.sub')].map(l => l.querySelector('.who').textContent + '=' + [...l.querySelectorAll('b.job')].map(b => b.className.split(' ')[1]).join('+')).join(';'));
  const bar = document.querySelector('.lane.sub b.job.TESTING');
  bar && bar.dispatchEvent(new PointerEvent('pointerenter'));
  out.push('tip:' + document.querySelector('.picked-line').textContent);
  const pre = document.createElement('pre'); pre.id = 'h33'; pre.textContent = 'H33RESULT ' + out.join(' | ') + ' END';
  document.body.appendChild(pre);
})();
</script>
"""
            idx = site / "status/index.html"
            idx.write_text(idx.read_text().replace("</body>", harness + "</body>", 1))
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", f"--user-data-dir={self.tmp / 'h33-profile'}",
                                              "--virtual-time-budget=20000", "--dump-dom", base + "/"], timeout=120)
            m = re.search(r'<pre id="h33">H33RESULT (.*?) END</pre>', r.stdout)
            need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
            res = dict(part.split(":", 1) for part in m.group(1).split(" | "))
            say(f"   {m.group(1)[:400]}")
            need(res["toggle"] == "false", "the Jobs row isn't folded closed at first")
            need(res["first"] == "ok", "the Jobs row isn't at the top of the graph")
            need(res["folded"] == "STOPPED,BUILDING,RELEASING,DONE,TESTING", f"the folded Jobs row isn't right: {res['folded']}")
            need(res["legend"] == "Building,Testing,Merging and releasing,Waiting for you,Done,Stopped", f"the jobs legend isn't right: {res['legend']}")
            want = ["rgb(138, 90, 0)", "rgb(15, 110, 102)", "rgb(102, 57, 186)", "rgb(11, 95, 191)", "rgb(26, 127, 55)", "rgb(180, 35, 24)"]
            need(res["colours"] == ",".join(want), f"the legend colours aren't the band colours: {res['colours']}")
            need(res["running"].startswith("repeating-linear-gradient"), f"a running routine isn't the green stripes: {res['running']}")
            need(res["open"] == "true", "the arrow doesn't open the Jobs row")
            lanes = res["lanes"].split(";")
            need(len(lanes) == 3 and lanes[0].startswith("Job 97 · H23") and lanes[0].endswith("=STOPPED")
                 and lanes[1].startswith("Job 98 · H33") and lanes[1].endswith("=BUILDING+RELEASING+DONE")
                 and lanes[2].startswith("Job 99 · F10") and lanes[2].endswith("=TESTING"), f"the job bars aren't right: {res['lanes']}")
            need("Testing" in res["tip"] and "to now" in res["tip"], f"hover doesn't say the job, state and times: {res['tip']}")
        finally:
            proc.terminate()
            proc.wait(timeout=5)
        return "the server writes the running job's state each minute; Jobs row on top, folded, opens to one bar per job in the band colours, own legend; running is green stripes"

    # 29
    async def flow29(self) -> str:
        """H34: the chat and status buttons are always on the call page, also before a call, and before
        any call in the app the chat shows the last saved call (read only). No Claude turns: made-up
        transcripts in the test server's own calls folder, and the real call page in a headless browser."""
        import transcript
        calls = self.server.calls
        calls.mkdir(parents=True, exist_ok=True)
        head = "# Call\n\n> **Private.**\n\nStarted 10:00:00 · brain test\n\n"
        (calls / "2099-12-31-2300.md").write_text(head + (
            "- 23:00:01 *filler: Hi there! What's up?*\n"
            "- 23:00:02 *call: connected; connectors: none*\n"
            f"- 23:00:05 **{config.USER_LABEL}:** What's on tomorrow? *(typed)*\n"
            "- 23:00:06 `Read challenges.md` · done (reading in the folder)\n"
            "- 23:00:09 **Jarvis:** Only the dentist at ten.\n"
            f"- 23:00:12 **{config.USER_LABEL}:** Shoes. *(cut in)* *(cancelled)*\n"
            "- 23:00:14 **Jarvis:** Right, so *(cut off)*\n\nEnded 23:00:20\n"))
        (calls / "2099-12-31-2300-2.md").write_text(head + "- 23:00:40 *filler: Hi there!*\n- 23:00:41 *call: The caller hung up*\n")
        last = transcript.last_call(calls)
        need(last and last["name"] == "2099-12-31-2300", f"the last call with something said wasn't picked: {last and last['name']}")
        lines = last["lines"]
        need([l["who"] for l in lines] == ["filler", "user", "jarvis", "user", "jarvis"],
             f"the wrong lines came out of the transcript (tools or call notes in it?): {[l['who'] for l in lines]}")
        need(lines[1]["text"] == "What's on tomorrow?" and lines[3]["cancelled"] and not lines[1]["cancelled"]
             and lines[4]["text"] == "Right, so (cut off)", f"the marks weren't read right: {lines}")
        empty = self.tmp / "no-calls"
        empty.mkdir(exist_ok=True)
        need(transcript.last_call(empty) is None, "an empty calls folder still gave a call")
        # The call server serves it, read only.
        await self.ensure_server()
        before = sorted(p.name for p in calls.iterdir())
        code, body, ctype = http_get("/api/last-call")
        need(code == 200 and "json" in ctype, f"/api/last-call did not answer ({code}, {ctype})")
        data = json.loads(body)
        need(data.get("name") == "2099-12-31-2300" and len(data.get("lines", [])) == 5, f"/api/last-call gave {str(data)[:200]}")
        need(sorted(p.name for p in calls.iterdir()) == before, "asking for the last call changed the calls folder")
        # The page, before, during and after a call.
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const shown = el => getComputedStyle(el).display !== "none" && el.getBoundingClientRect().width > 0;
  const both = () => shown(chatBtn) && shown(statBtn);
  await wait(400);
  out.push("start:" + (both() ? "ok" : "MISSING chat=" + shown(chatBtn) + " status=" + shown(statBtn)));
  out.push("nobadge:" + (badge.classList.contains("show") ? "BADGE" : "ok"));
  chatBtn.click(); await wait(400);
  const msgs = chatLog.querySelectorAll(".msg");
  out.push("lastcall:" + (chatOpen() && chatTitle.textContent.startsWith("Last call · ") && msgs.length === 5
    && chatLog.querySelectorAll(".msg.me.cancelled").length === 1 ? "ok" : "WRONG " + chatTitle.textContent + " " + msgs.length));
  out.push("notyping:" + (typeForm.classList.contains("show") ? "TYPEBOX" : "ok"));
  showChat(false);
  calledHere = true; clearChat(); setState("live", "On the call");
  out.push("live:" + (both() ? "ok" : "MISSING"));
  out.push("livechat:" + (chatLog.querySelector(".msg") ? "OLD LINES" : "ok"));
  addChat("user", "New line"); addChat("jarvis", "New answer");
  cleanup("Call ended");
  out.push("after:" + (both() ? "ok" : "MISSING"));
  chatBtn.click(); await wait(400);
  out.push("afterchat:" + (chatLog.querySelectorAll(".msg").length === 2 && chatTitle.textContent === "What was said" ? "ok" : "REPLACED"));
  showChat(false);
  // No saved calls at all: a short empty note.
  calledHere = false; lastCallName = null; stubEmpty = true; chatBtn.click(); await wait(400);
  out.push("empty:" + (chatLog.querySelector(".empty") && chatLog.querySelector(".empty").textContent === "No calls yet" ? "ok" : "WRONG"));
  const pre = document.createElement("pre"); pre.id = "h34"; pre.textContent = "H34RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        stub = "<script>var stubEmpty = false; const LASTCALL = " + json.dumps(data) + """;
window.fetch = async (url) => ({ ok: true, json: async () => (stubEmpty ? { lines: [] } : LASTCALL) });</script>"""
        f = self.tmp / "h34.html"
        f.write_text(page.replace("<style>", stub + "<style>", 1).replace("</body>", harness + "</body>", 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", "--window-size=390,844",
                                          "--virtual-time-budget=20000", "--dump-dom", f.as_uri()], timeout=120)
        m = re.search(r'<pre id="h34">H34RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        res = m.group(1)
        say(f"   {res}")
        need(all(part.endswith(":ok") for part in res.split(" | ")), f"the buttons or the chat aren't right: {res}")
        return ("chat and status buttons before, during and after a call; before a call the chat shows the last saved call "
                "(tool lines left out, cancelled marked), read only; after a call that call stays; no calls: a short note")

    # 30
    async def flow30(self) -> str:
        """H35: the laptop's temperature. No Claude turns. The real sensors are read without a password
        (IOKit, the reader built with clang); the ranges (normal under 70, warm 70-89, hot from 90 or when
        macOS slows down) are judged right; the routine runs it every minute. Then a copy of the status page
        on its own port, with a made-up hot laptop: the Laptop section shows the bar, the graph and the heat
        warning, and the Laptop light and the Routines light turn red."""
        sys.path.insert(0, str(ROOT / "routine"))
        import temperature as T
        r = await asyncio.to_thread(run, [sys.executable, str(ROOT / "routine/temperature.py"), "--dry"], timeout=180)
        need(r.returncode == 0, f"the temperature can't be read: {(r.stdout + r.stderr).strip()[-200:]}")
        x = json.loads(r.stdout.strip().splitlines()[-1])
        need(20 < x["cpu"] < 120 and x["lvl"] in ("normal", "warm", "hot"), f"odd reading: {x}")
        need(os.geteuid() != 0, "the check must run without admin rights")
        cases = [((60, 1, 0, 0, 100), ("normal", False)), ((75, 0, 0, 0, 100), ("warm", False)),
                 ((92, 0, 0, 0, 100), ("hot", False)), ((65, 2, 0, 0, 100), ("hot", True)),
                 ((65, 0, 0, 0, 80), ("hot", True)), ((65, 0, 1, 0, 100), ("hot", True))]
        for args, want in cases:
            need(T.judge(*args) == want, f"judge{args} gave {T.judge(*args)}, wanted {want}")
        tick = (ROOT / "routine/tick.py").read_text()
        need("TEMPERATURE = os.path.join(HERE, \"temperature.py\")" in tick and "[PY, TEMPERATURE]" in tick,
             "the routine doesn't run the temperature check every minute")
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the status page in")
        node = shutil.which("node") or "/opt/homebrew/bin/node"
        site = self.tmp / "h35"
        shutil.copytree(ROOT / "status", site / "status", ignore=shutil.ignore_patterns("icons"))
        (site / ".status").mkdir()
        shutil.copy(ROADMAP, site_roadmap(site))
        now = int(time.time())
        ok = {k: {"state": "ok", "text": "fine", "at": now, "every": 60} for k in ["helper", "watchdog", "mail", "jobs", "usage", "phone", "call"]}
        ok["temp"] = {"state": "down", "text": "Hot: 95°C on the chip · Slowing itself down: CPU held to 80%", "at": now, "every": 60}
        (site / ".status/routines.json").write_text(json.dumps(ok))
        (site / ".status/temperature.json").write_text(json.dumps({"t": now, "cpu": 95.0, "avg": 88.0, "bat": 38.0, "st": 2, "therm": 0, "perf": 0,
                                                                  "speed": 80, "lvl": "hot", "slow": True, "heat": "Slowing itself down: CPU held to 80%",
                                                                  "ranges": {"warm": 70, "hot": 90}}))
        hist = [{"t": now - (30 - i) * 60, "cpu": c, "avg": c - 5, "bat": 35, "st": 0, "lvl": T.judge(c, 0, 0, 0, 100)[0], "slow": False}
                for i, c in enumerate([60] * 10 + [75] * 10 + [95] * 10)]
        (site / ".status/temperature-history.jsonl").write_text("\n".join(json.dumps(h) for h in hist) + "\n")
        port = 4792
        env = {**os.environ, "JARVIS_STATUS_PORT": str(port)}
        proc = subprocess.Popen([node, str(site / "status/server.mjs"), "--quiet"], env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                if http_get("/routines.json", base)[0] == 200:
                    break
                await asyncio.sleep(0.2)
            _, body, _ = http_get("/routines.json", base)
            need(json.loads(body).get("temperature", {}).get("cpu") == 95.0, "the server doesn't serve the temperature")
            _, body, _ = http_get("/temperature-history.json?h=1", base)
            need(len(json.loads(body)["samples"]) == 30, "the server doesn't serve the temperature history")
            harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 40 && !document.querySelector('.laptop .tgraph b'); i++) await wait(250);
  const lap = document.querySelector('.laptop');
  out.push('laptop:' + (lap ? 'ok' : 'missing'));
  out.push('lightlap:' + (lap && lap.querySelector('.light').className));
  const rl = [...document.querySelectorAll('section')].find(s => /Routines/.test(s.querySelector('h2')?.textContent || ''));
  out.push('lightrout:' + (rl && rl.querySelector('.light').className));
  out.push('routsum:' + (rl && rl.querySelector('summary .soft').textContent));
  out.push('fill:' + (lap && lap.querySelector('.tbar .fill').className));
  out.push('deg:' + (lap && lap.querySelector('.deg').textContent));
  out.push('heat:' + (lap && lap.querySelector('.now-row small').textContent));
  out.push('cols:' + [...document.querySelectorAll('.tgraph b')].map(b => b.className).filter((c, i, a) => a.indexOf(c) === i).join(','));
  out.push('n:' + document.querySelectorAll('.tgraph b').length);
  out.push('key:' + [...lap.querySelectorAll('.key span')].map(s => s.textContent).join(','));
  out.push('spans:' + [...lap.querySelectorAll('.card.temp .chip.range')].map(b => b.textContent).join(','));
  const b = document.querySelector('.tgraph b.hot'); b && b.dispatchEvent(new PointerEvent('pointerenter'));
  out.push('tip:' + lap.querySelector('.picked-line').textContent);
  const pre = document.createElement('pre'); pre.id = 'h35'; pre.textContent = 'H35RESULT ' + out.join(' | ') + ' END';
  document.body.appendChild(pre);
})();
</script>
"""
            idx = site / "status/index.html"
            idx.write_text(idx.read_text().replace("</body>", harness + "</body>", 1))
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", f"--user-data-dir={self.tmp / 'h35-profile'}",
                                              "--virtual-time-budget=20000", "--dump-dom", base + "/"], timeout=120)
            m = re.search(r'<pre id="h35">H35RESULT (.*?) END</pre>', r.stdout)
            need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
            res = dict(part.split(":", 1) for part in m.group(1).split(" | "))
            say(f"   {m.group(1)[:400]}")
            need(res["laptop"] == "ok", "no Laptop section")
            need(res["lightlap"] == "light down", f"the Laptop light isn't red when hot: {res['lightlap']}")
            need(res["lightrout"] == "light down", f"the Routines light isn't red when hot: {res['lightrout']}")
            need(res["routsum"].startswith("Laptop hot"), f"the Routines heading doesn't say the laptop is hot: {res['routsum']}")
            need(res["fill"] == "fill hot" and res["deg"] == "95°C", f"the bar isn't right: {res['fill']} {res['deg']}")
            need("Slowing itself down" in res["heat"], f"the heat warning doesn't show: {res['heat']}")
            need(res["cols"] == "normal,warm,hot" and res["n"] == "30", f"the graph isn't right: {res['cols']} ({res['n']})")
            need(res["key"].startswith("Normal, under 70°C,Warm, 70 to 89°C,Hot, 90°C"), f"the ranges legend isn't right: {res['key']}")
            need(res["spans"] == "1 h,6 h,24 h", f"the time spans aren't 1, 6 and 24 h: {res['spans']}")
            need("95°C" in res["tip"] and "Hot" in res["tip"], f"hover doesn't say time and degrees: {res['tip']}")
        finally:
            proc.terminate()
            proc.wait(timeout=5)
        return (f"read without a password: {x['cpu']:.0f}°C now ({x['lvl']}); ranges judged right; the routine runs it each minute; "
                "a hot laptop: bar, graph, heat warning, Laptop and Routines lights red")

    # 31
    async def flow31(self) -> str:
        """H37: the laptop's battery. No Claude turns. The real battery is read from pmset; low (under 20%),
        getting low (20-39%) and fine are judged right, and on the charger it's never an alarm; the routine
        runs it every minute. Then a copy of the status page on its own port, with a made-up low battery on
        battery: the Laptop section shows the battery bar, the graph and the words, and the Laptop light and
        the Routines light turn red."""
        sys.path.insert(0, str(ROOT / "routine"))
        import battery as B
        r = await asyncio.to_thread(run, [sys.executable, str(ROOT / "routine/battery.py"), "--dry"], timeout=60)
        need(r.returncode == 0, f"the battery can't be read: {(r.stdout + r.stderr).strip()[-200:]}")
        x = json.loads(r.stdout.strip().splitlines()[-1])
        need(0 <= x["pct"] <= 100 and x["lvl"] in ("fine", "getting-low", "low"), f"odd reading: {x}")
        for args, want in [((10, False), "low"), ((19, False), "low"), ((20, False), "getting-low"), ((39, False), "getting-low"),
                           ((40, False), "fine"), ((5, True), "fine"), ((100, True), "fine")]:
            need(B.judge(*args) == want, f"judge{args} gave {B.judge(*args)}, wanted {want}")
        for text, want in [("Now drawing from 'Battery Power'\n -InternalBattery-0 (id=1)\t45%; discharging; 3:10 remaining present: true", (45, False, False, "discharging", 190)),
                           ("Now drawing from 'AC Power'\n -InternalBattery-0 (id=1)\t83%; charging; 0:46 remaining present: true", (83, True, True, "charging", 46)),
                           ("Now drawing from 'AC Power'\n -InternalBattery-0 (id=1)\t80%; AC attached; not charging present: true", (80, True, False, "ac attached", None)),
                           ("Now drawing from 'Battery Power'\n -InternalBattery-0 (id=1)\t12%; discharging; (no estimate) present: true", (12, False, False, "discharging", None))]:
            need(B.parse(text) == want, f"pmset read wrong: {B.parse(text)}, wanted {want}")
        tick = (ROOT / "routine/tick.py").read_text()
        need("BATTERY = os.path.join(HERE, \"battery.py\")" in tick and "[PY, BATTERY]" in tick,
             "the routine doesn't run the battery check every minute")
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the status page in")
        node = shutil.which("node") or "/opt/homebrew/bin/node"
        site = self.tmp / "h37"
        shutil.copytree(ROOT / "status", site / "status", ignore=shutil.ignore_patterns("icons"))
        (site / ".status").mkdir()
        shutil.copy(ROADMAP, site_roadmap(site))
        now = int(time.time())
        ok = {k: {"state": "ok", "text": "fine", "at": now, "every": 60} for k in ["helper", "watchdog", "mail", "jobs", "usage", "phone", "call"]}
        ok["temp"] = {"state": "ok", "text": "Normal: 60°C on the chip · No heat warning, not slowing down", "at": now, "every": 60}
        ok["battery"] = {"state": "down", "text": "Low battery: 12% · On battery, 0:25 left", "at": now, "every": 60}
        (site / ".status/routines.json").write_text(json.dumps(ok))
        (site / ".status/temperature.json").write_text(json.dumps({"t": now, "cpu": 60.0, "avg": 55.0, "bat": 30.0, "st": 0, "therm": 0, "perf": 0,
                                                                  "speed": 100, "lvl": "normal", "slow": False, "heat": "No heat warning, not slowing down",
                                                                  "ranges": {"warm": 70, "hot": 90}}))
        (site / ".status/battery.json").write_text(json.dumps({"t": now, "pct": 12, "plugged": False, "charging": False, "how": "discharging",
                                                              "left": 25, "lvl": "low", "words": "On battery, 0:25 left",
                                                              "ranges": {"low": 20, "getting_low": 40}}))
        hist = [{"t": now - (30 - i) * 60, "pct": p, "plugged": i < 5, "charging": i < 5, "lvl": B.judge(p, i < 5)}
                for i, p in enumerate([60 - i * 2 for i in range(30)])]
        (site / ".status/battery-history.jsonl").write_text("\n".join(json.dumps(h) for h in hist) + "\n")
        port = 4793
        env = {**os.environ, "JARVIS_STATUS_PORT": str(port)}
        proc = subprocess.Popen([node, str(site / "status/server.mjs"), "--quiet"], env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                if http_get("/routines.json", base)[0] == 200:
                    break
                await asyncio.sleep(0.2)
            _, body, _ = http_get("/routines.json", base)
            need(json.loads(body).get("battery", {}).get("pct") == 12, "the server doesn't serve the battery")
            _, body, _ = http_get("/battery-history.json?h=1", base)
            need(len(json.loads(body)["samples"]) == 30, "the server doesn't serve the battery history")
            harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 40 && !document.querySelector('.laptop .tgraph.battery b'); i++) await wait(250);
  const lap = document.querySelector('.laptop');
  out.push('laptop:' + (lap ? 'ok' : 'missing'));
  out.push('lightlap:' + (lap && lap.querySelector('.light').className));
  out.push('lapsum:' + (lap && lap.querySelector('summary .soft').textContent));
  const rl = [...document.querySelectorAll('section')].find(s => /Routines/.test(s.querySelector('h2')?.textContent || ''));
  out.push('lightrout:' + (rl && rl.querySelector('.light').className));
  out.push('routsum:' + (rl && rl.querySelector('summary .soft').textContent));
  const row = lap.querySelector('.now-row.battery');
  out.push('fill:' + (row && row.querySelector('.tbar .fill').className));
  out.push('pct:' + (row && row.querySelector('.pct').textContent));
  out.push('words:' + (row && row.querySelector('small').textContent));
  out.push('cols:' + [...lap.querySelectorAll('.tgraph.battery b')].map(b => b.className).filter((c, i, a) => a.indexOf(c) === i).join(','));
  out.push('n:' + lap.querySelectorAll('.tgraph.battery b').length);
  out.push('key:' + [...lap.querySelectorAll('.bkey span')].map(s => s.textContent).join(','));
  const b = lap.querySelector('.tgraph.battery b.low'); b && b.dispatchEvent(new PointerEvent('pointerenter'));
  out.push('tip:' + [...lap.querySelectorAll('.card.temp .picked-line')].pop().textContent);
  const pill = document.querySelector('.top .batpill');
  out.push('pill:' + (pill ? pill.className + '=' + pill.textContent + '=' + getComputedStyle(pill).backgroundColor : 'missing'));
  const pre = document.createElement('pre'); pre.id = 'h37'; pre.textContent = 'H37RESULT ' + out.join(' | ') + ' END';
  document.body.appendChild(pre);
})();
</script>
"""
            idx = site / "status/index.html"
            idx.write_text(idx.read_text().replace("</body>", harness + "</body>", 1))
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", f"--user-data-dir={self.tmp / 'h37-profile'}",
                                              "--virtual-time-budget=20000", "--dump-dom", base + "/"], timeout=120)
            m = re.search(r'<pre id="h37">H37RESULT (.*?) END</pre>', r.stdout)
            need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
            res = dict(part.split(":", 1) for part in m.group(1).split(" | "))
            say(f"   {m.group(1)[:500]}")
            need(res["laptop"] == "ok", "no Laptop section")
            need(res["lightlap"] == "light down", f"the Laptop light isn't red when the battery is low: {res['lightlap']}")
            need("battery 12%, on battery" in res["lapsum"], f"the Laptop heading doesn't say the battery: {res['lapsum']}")
            need(res["lightrout"] == "light down", f"the Routines light isn't red when the battery is low: {res['lightrout']}")
            need(res["routsum"].startswith("Low battery, 12%") and "not working" not in res["routsum"], f"the Routines heading isn't right: {res['routsum']}")
            need(res["fill"] == "fill low" and res["pct"] == "12%", f"the battery bar isn't right: {res['fill']} {res['pct']}")
            need("On battery, 0:25 left" in res["words"], f"charging or not doesn't show: {res['words']}")
            cols = set(res["cols"].split(","))
            need({"fine plugged", "fine", "getting-low", "low"} <= cols and res["n"] == "30", f"the battery graph isn't right: {res['cols']} ({res['n']})")
            need(res["key"].startswith("Fine, 40% and up,Getting low, 20 to 39%,Low, under 20%"), f"the ranges legend isn't right: {res['key']}")
            need("on battery" in res["tip"] and "%" in res["tip"], f"hover doesn't say time and battery: {res['tip']}")
            need(res["pill"].startswith("batpill low=Battery 12%=") and "rgba(0, 0, 0, 0)" not in res["pill"],
                 f"the battery doesn't show red in the top line: {res['pill']}")
        finally:
            proc.terminate()
            proc.wait(timeout=5)
        return (f"read from pmset: {x['pct']}% now, {'charging' if x['charging'] else 'on the charger' if x['plugged'] else 'on battery'} ({x['lvl']}); "
                "ranges judged right; the routine runs it each minute; a low battery: bar, graph, Laptop and Routines lights red")

    # 38
    async def flow38(self) -> str:
        """H44: more laptop stats. No Claude turns. The real counters are read without a password (CPU, GPU,
        memory, disk, network); the per-minute maths is right on made-up counters, and a restart (a counter
        going down) leaves that part empty; the routine runs it every minute. Then a copy of the status page
        on its own port with a made-up hour: under the open Laptop section a second arrow, folded closed at
        the start, opens the five rows with their graphs; the choice is remembered; the stats colour no light;
        on a phone-wide screen nothing sticks out sideways."""
        sys.path.insert(0, str(ROOT / "routine"))
        import stats as S
        r = await asyncio.to_thread(run, [sys.executable, str(ROOT / "routine/stats.py"), "--dry"], timeout=150)
        need(r.returncode == 0, f"the stats can't be read: {(r.stdout + r.stderr).strip()[-200:]}")
        x = json.loads(r.stdout.strip().splitlines()[-1])
        need(x["cpu"] is not None and 0 <= x["cpu"] <= 100, f"odd CPU reading: {x.get('cpu')}")
        need(x["mem_total"] > 0 and 0 < x["mem_used"] <= x["mem_total"] * 1.1, f"odd memory reading: {x.get('mem_used')} of {x.get('mem_total')}")
        need(all(x[k] is not None and x[k] >= 0 for k in ("disk_read", "disk_write", "net_in", "net_out")), f"odd disk or network reading: {x}")
        need(x["mem_level"] in ("normal", "warning", "critical"), f"no memory pressure level: {x.get('mem_level')}")
        a = {"t": 1000.0, "cpu": {"user": 100, "system": 50, "idle": 800, "nice": 50}, "gpu": 10,
             "mem": {"total": 16 * 2**30, "page": 16384, "internal": 300000, "purgeable": 0, "wired": 100000, "compressed": 50000, "free": 1, "swapouts": 0},
             "disk": {"read": 1_000_000, "written": 0}, "net": {"in": 0, "out": 6_000_000}}
        b = json.loads(json.dumps(a)); b["t"] = 1060.0
        b["cpu"] = {"user": 400, "system": 150, "idle": 1300, "nice": 50}
        b["disk"] = {"read": 7_000_000, "written": 600_000}; b["net"] = {"in": 60_000, "out": 0}
        y = S.reading(b, a, 69, 1, None)
        need(y["cpu"] == 44.4 and y["cpu_user"] == 33.3 and y["cpu_system"] == 11.1, f"CPU maths wrong: {y['cpu']} {y.get('cpu_user')} {y.get('cpu_system')}")
        need(y["disk_read"] == 100_000 and y["disk_write"] == 10_000 and y["net_in"] == 1000, f"speed maths wrong: {y}")
        need(y["net_out"] is None, "a counter that went down (a restart) should leave that speed empty")
        need(y["mem_used"] == 450000 * 16384 and y["mem_pressure"] == 31 and y["mem_level"] == "normal", f"memory maths wrong: {y}")
        need(S.size(16 * 2**30) == "16.0 GB" and S.size(1500, True) == "1.5 KB/s", f"sizes in words wrong: {S.size(16 * 2**30)} {S.size(1500, True)}")
        tick = (ROOT / "routine/tick.py").read_text()
        need('STATS = os.path.join(HERE, "stats.py")' in tick and "[PY, STATS]" in tick, "the routine doesn't run the stats every minute")
        need("routines.beat" not in (ROOT / "routine/stats.py").read_text(), "the stats write a routine line (they shouldn't touch the lights)")
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the status page in")
        node = shutil.which("node") or "/opt/homebrew/bin/node"
        site = self.tmp / "h44"
        shutil.copytree(ROOT / "status", site / "status", ignore=shutil.ignore_patterns("icons"))
        (site / ".status").mkdir()
        shutil.copy(ROADMAP, site_roadmap(site))
        now = int(time.time())
        ok = {k: {"state": "ok", "text": "fine", "at": now, "every": 60} for k in ["helper", "watchdog", "mail", "jobs", "usage", "phone", "call"]}
        ok["temp"] = {"state": "ok", "text": "Normal: 60°C on the chip · No heat warning, not slowing down", "at": now, "every": 60}
        ok["battery"] = {"state": "ok", "text": "Battery: 90% · Charging", "at": now, "every": 60}
        (site / ".status/routines.json").write_text(json.dumps(ok))
        (site / ".status/temperature.json").write_text(json.dumps({"t": now, "cpu": 60.0, "avg": 55.0, "bat": 30.0, "st": 0, "therm": 0, "perf": 0,
                                                                  "speed": 100, "lvl": "normal", "slow": False, "heat": "No heat warning, not slowing down",
                                                                  "ranges": {"warm": 70, "hot": 90}}))
        (site / ".status/battery.json").write_text(json.dumps({"t": now, "pct": 90, "plugged": True, "charging": True, "how": "charging",
                                                              "left": 20, "lvl": "fine", "words": "Charging, full in 0:20",
                                                              "ranges": {"low": 20, "getting_low": 40}}))
        hist = [{"t": now - (30 - i) * 60, "cpu": 99.0 if i == 10 else 20.0 + i, "gpu": 95 if i == 10 else 5, "mem_used": 14 * 2**30, "mem_total": 16 * 2**30,
                 "mem_pressure": 80, "mem_level": "critical", "disk_read": 50_000_000, "disk_write": 2_000_000, "net_in": 30_000, "net_out": 10_000}
                for i in range(30)]
        (site / ".status/stats-history.jsonl").write_text("\n".join(json.dumps(h) for h in hist) + "\n")
        (site / ".status/stats.json").write_text(json.dumps({**hist[-1], "t": now, "cpu_user": 30.0, "cpu_system": 19.0, "swap": 2**30,
                                                            "mem_app": 0, "mem_wired": 0, "mem_compressed": 0, "over": 60, "words": "x"}))
        port = 4794
        env = {**os.environ, "JARVIS_STATUS_PORT": str(port)}
        proc = subprocess.Popen([node, str(site / "status/server.mjs"), "--quiet"], env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                if http_get("/routines.json", base)[0] == 200:
                    break
                await asyncio.sleep(0.2)
            _, body, _ = http_get("/routines.json", base)
            need(json.loads(body).get("stats", {}).get("cpu") == 49.0, "the server doesn't serve the stats")
            _, body, _ = http_get("/stats-history.json?h=1", base)
            need(len(json.loads(body)["samples"]) == 30, "the server doesn't serve the stats history")
            harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 40 && !document.querySelector('.laptop .tgraph.battery b'); i++) await wait(250);
  const lap = document.querySelector('.laptop');
  const sub = () => [...lap.querySelectorAll('details.fold.sub')].find(d => /More stats/.test(d.querySelector('summary').textContent));
  let f = sub();
  out.push('fold:' + (f ? 'ok' : 'missing'));
  out.push('last:' + (f && f === [...lap.querySelector('details.fold').children].pop() ? 'yes' : 'no'));
  out.push('closed:' + (f && !f.open ? 'yes' : 'no'));
  out.push('sum:' + (f && f.querySelector('summary').textContent));
  out.push('lightlap:' + lap.querySelector('.light').className);
  const rl = [...document.querySelectorAll('section')].find(s => /Routines/.test(s.querySelector('h2')?.textContent || ''));
  out.push('lightrout:' + (rl && rl.querySelector('.light').className));
  f.open = true; f.dispatchEvent(new Event('toggle'));
  out.push('saved:' + localStorage.getItem('fold:laptop-stats'));
  await wait(3500);
  f = sub();
  out.push('stillopen:' + (f && f.open ? 'yes' : 'no'));
  out.push('rows:' + [...f.querySelectorAll('.stat .head b')].map(b => b.textContent).join(','));
  out.push('cols:' + [...f.querySelectorAll('.stat')].map(s => s.querySelectorAll('.sgraph b').length).join(','));
  out.push('mem:' + f.querySelector('.stat.mem .head span').textContent);
  out.push('cpu:' + f.querySelector('.stat.cpu .head span').textContent);
  const peak = [...f.querySelectorAll('.stat.cpu .sgraph b')].find(b => b.style.height === '99%');
  peak && peak.dispatchEvent(new PointerEvent('pointerenter'));
  out.push('tip:' + f.querySelector('.picked-line').textContent);
  out.push('red:' + [...f.querySelectorAll('.sgraph b')].some(b => /rgb\(180, 35, 24\)|rgb\(240, 118, 106\)/.test(getComputedStyle(b).backgroundColor)));
  out.push('wide:' + document.documentElement.scrollWidth + '/' + window.innerWidth);
  const pre = document.createElement('pre'); pre.id = 'h44'; pre.textContent = 'H44RESULT ' + out.join(' | ') + ' END';
  document.body.appendChild(pre);
})();
</script>
"""
            idx = site / "status/index.html"
            idx.write_text(idx.read_text().replace("</body>", harness + "</body>", 1))
            results = []
            for name, size in (("computer", "1280,1600"), ("phone", "390,3000")):
                r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", f"--user-data-dir={self.tmp / ('h44-' + name)}",
                                                  f"--window-size={size}", "--virtual-time-budget=25000", "--dump-dom", base + "/"], timeout=120)
                m = re.search(r'<pre id="h44">H44RESULT (.*?) END</pre>', r.stdout)
                need(m, f"the page test ({name}) didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
                res = dict(part.split(":", 1) for part in m.group(1).split(" | "))
                say(f"   {name}: {m.group(1)[:600]}")
                need(res["fold"] == "ok" and res["last"] == "yes", f"no More stats fold at the bottom of Laptop ({name})")
                need(res["closed"] == "yes", f"the More stats fold isn't folded closed at the start ({name})")
                need("CPU 49%" in res["sum"] and "GPU 5%" in res["sum"], f"the fold's heading doesn't say the numbers: {res['sum']}")
                need(res["lightlap"] == "light" and res["lightrout"] == "light", f"the stats coloured a light: {res['lightlap']} / {res['lightrout']}")
                need(res["saved"] == "yes" and res["stillopen"] == "yes", f"opening the fold isn't remembered ({name}): {res['saved']} {res['stillopen']}")
                need(res["rows"] == "CPU,GPU,Memory,Disk,Network", f"the rows aren't right: {res['rows']}")
                need(res["cols"] == "30,30,30,60,60", f"the graphs aren't right: {res['cols']}")
                need(res["mem"].startswith("14.0 GB of 16.0 GB · pressure 80%, critical · swap 1.0 GB"), f"the memory line isn't right: {res['mem']}")
                need("user 30%, system 19%" in res["cpu"], f"the CPU line isn't right: {res['cpu']}")
                need("CPU 99%" in res["tip"], f"hover doesn't say the time and the number: {res['tip']}")
                need(res["red"] == "false", "the stats graphs use an alarm colour")
                w, iw = (int(v) for v in res["wide"].split("/"))
                need(w <= iw, f"the page sticks out sideways ({name}): {w} wide on {iw}")
                results.append(name)
        finally:
            proc.terminate()
            proc.wait(timeout=5)
        return (f"read without a password: CPU {x['cpu']:.0f}%, GPU {x['gpu']}%, memory {S.size(x['mem_used'])} of {S.size(x['mem_total'])} ({x['mem_level']}); "
                "maths right, a restart leaves a gap; the routine runs it each minute; folded closed under Laptop, opens to five graphs, "
                "remembered, no light coloured, fits a phone")

    async def flow33(self) -> str:
        """H36: a job that has gone quiet gets continue typed into its own window. No Claude turns."""
        sys.path.insert(0, str(ROOT / "routine"))
        import quiet as Q
        import tick as TK
        tmp = self.tmp / "h36"
        tmp.mkdir()
        Q.REQUEST, Q.RESULT, Q.ACTIVITY = str(tmp / "nudge-request.json"), str(tmp / "nudge-result.json"), str(tmp / "act.json")
        M = 60
        for args, want in [((1000, 1000 - 9 * M, 0, 0, True), "ok"), ((1000, 1000 - 10 * M, 0, 0, False), "offline"),
                           ((1000, 1000 - 10 * M, 0, 0, True), "nudge"), ((1000, 0, 1, 1000 - 3 * M, True), "wait"),
                           ((1000, 0, 1, 1000 - 4 * M, True), "nudge"), ((1000, 0, 3, 1000 - 4 * M, True), "stuck")]:
            need(Q.decide(*args) == want, f"decide{args} gave {Q.decide(*args)}, wanted {want}")

        class Inc:
            def __init__(self): self.calls = []
            def down(self, k, why, at=None): self.calls.append(("down", why))
            def fix(self, k, what, at=None): self.calls.append(("fix", what))
            def up(self, k, at=None): self.calls.append(("up", ""))
        inc, sts, beats = Inc(), [], []
        s = {"n": 7, "pid": None, "started": 0.0}
        t0 = 100000.0
        def look(now, online):
            return Q.check(7, s, lambda x: None, lambda *a: sts.append(a), lambda **f: beats.append(f), inc,
                           lambda m: None, now=now, is_online=online)
        need(look(t0 + 11 * M, False) == "offline", "quiet without internet should wait")
        need(any("no internet" in w for c, w in inc.calls), "no internet isn't in the incident log")
        need(not os.path.exists(Q.REQUEST), "it typed while there was no internet")
        need(look(t0 + 12 * M, True) == "nudge" and Q.pending(7), "online again: no continue asked for")
        json.dump({"n": 7, "at": t0 + 12 * M + 3, "ok": True, "said": "typed"}, open(Q.RESULT, "w"))
        Q.clear_request()
        need(look(t0 + 13 * M, True) == "wait", "it should wait four minutes between tries")
        need(any("Typed continue into job 7's window (try 1 of 3)" in w for c, w in inc.calls), "the nudge's answer isn't logged")
        need(look(t0 + 16 * M, True) == "nudge" and look(t0 + 20 * M, True) == "nudge", "tries 2 and 3 didn't come")
        need(s["nudges"] == 3, f"{s['nudges']} tries, wanted 3")
        need(look(t0 + 24 * M, True) == "stuck", "still quiet after 3 tries should be stuck")
        need(sts and sts[-1][0] == "STOPPED" and "looks stuck" in sts[-1][1], f"the status block wasn't set to stuck: {sts[-1:]}")
        need(beats[-1].get("state") == "down", "the jobs line isn't red when stuck")
        json.dump({"at": t0 + 25 * M}, open(Q.ACTIVITY, "w"))
        need(look(t0 + 25 * M + 30, True) == "ok", "a sign of life should count as awake")
        need(sts[-1][0] == "BUILDING" and "working again" in sts[-1][1], "awake again isn't shown as BUILDING")
        need(inc.calls[-1][0] == "up" and "nudges" not in s, "the incident wasn't closed, or the tries weren't reset")
        need(len([x for x in sts if x[0] == "STOPPED"]) == 1, "stuck was written more than once")

        # The status line leaves a sign of life.
        act = tmp / "sl.json"
        await asyncio.to_thread(subprocess.run, [sys.executable, str(ROOT / "routine/statusline.py")], input="{}",
                                capture_output=True, text=True, env={**os.environ, "JARVIS_ACTIVITY": str(act)}, timeout=30)
        need(act.exists() and json.loads(act.read_text())["at"] > time.time() - 60, "the status line leaves no sign of life")

        tick = (ROOT / "routine/tick.py").read_text()
        need("nudge.py" in tick and '"$JT" $$' in tick and "quiet.check(" in tick and "quiet.clear_request()" in tick,
             "the routine doesn't start nudge.py in the job's window, or doesn't run the quiet check")

        # Two real throwaway windows: continue goes into the one asked for, never the other.
        outs = {}
        for n in (9901, 9902):
            out = tmp / f"w{n}.out"
            cmd = tmp / f"w{n}.command"
            cmd.write_text(f"""#!/bin/zsh
printf '\\e[2t'
printf '\\e]0;Jarvis happy flow 33\\a'
export JARVIS_NUDGE_DIR={json.dumps(str(tmp))}
JT=$(tty)
/usr/bin/python3 {json.dumps(str(ROOT / 'routine/nudge.py'))} {n} "$JT" $$ </dev/null >/dev/null 2>&1 &!
echo started > {json.dumps(str(out))}
read -r line; echo "got:$line" >> {json.dumps(str(out))}
""" + TK.CLOSE_WINDOW)
            cmd.chmod(0o755)
            outs[n] = out
            await asyncio.to_thread(run, ["/usr/bin/open", "-g", "-a", "Terminal", str(cmd)], timeout=30)
        for _ in range(40):
            if all(o.exists() for o in outs.values()):
                break
            await asyncio.sleep(0.5)
        need(all(o.exists() for o in outs.values()), "the test windows didn't start")
        await asyncio.sleep(1)
        os.environ["JARVIS_NUDGE_DIR"] = str(tmp)
        try:
            for n, other in ((9901, 9902), (9902, None)):
                t = time.time()
                Q.request(n)
                for _ in range(40):
                    if Q.result(n, t - 1):
                        break
                    await asyncio.sleep(0.5)
                r = Q.result(n, t - 1)
                need(r and r["ok"], f"window {n} wasn't typed into: {r}")
                await asyncio.sleep(1.5)
                need("got:continue" in outs[n].read_text(), f"window {n} didn't receive continue")
                if other:
                    need("got:" not in outs[other].read_text(), "continue landed in the other window too")
        finally:
            os.environ.pop("JARVIS_NUDGE_DIR", None)
        closed = 0
        for _ in range(30):
            # A closed window can linger in the list for a while with no tabs and invisible: that counts as closed.
            names = await asyncio.to_thread(run, ["/usr/bin/osascript", "-e", """tell application "Terminal"
set n to 0
repeat with w in (every window)
try
if (name of w contains "happy flow 33") and (count of tabs of w) > 0 then set n to n + 1
end try
end repeat
return n
end tell"""], timeout=20)
            if names.stdout.strip() == "0":
                closed = 1
                break
            await asyncio.sleep(1)
        need(closed, "the test windows didn't close themselves")
        return "rules right; incident log, stuck and awake right; continue typed into the right window only"

    async def flow34(self) -> str:
        """H39: the queue runs in list order, and a call can move waiting jobs. No Claude turns and no job
        is started: the queue script on a copy of the roadmap, the routine taking the top of the line,
        the place in line on the status page, and what a call may do."""
        import subprocess as sp
        from policy import Policy, ALLOW, DENY
        jv = ROOT
        rm = self.tmp / "roadmap-H39.md"
        rm.write_text(ROADMAP.read_text())
        env = {**os.environ, "JARVIS_ROADMAP": str(rm)}
        def jobs(*a, ok=True):
            r = sp.run(["python3", str(jv / "routine/jobs.py"), *a], capture_output=True, text=True, env=env)
            need((r.returncode == 0) == ok, f"jobs.py {' '.join(a)}: {r.stdout.strip()} {r.stderr.strip()}")
            return r.stdout + r.stderr
        def line():
            return [j["n"] for j in json.loads(jobs("next"))["waiting"]]
        # Clear the copy's own waiting jobs, so only the test's jobs wait.
        for n in line():
            jobs("stop", str(n))
        a, b, c = (int(jobs("add", f"flow 34 job {x}").split()[1]) for x in "abc")
        need(line() == [a, b, c], f"new jobs don't wait in the order they were added: {line()}")
        jobs("move", str(c), "top")
        need(line() == [c, a, b], f"move top: {line()}")
        jobs("move", str(c), "down")
        need(line() == [a, c, b], f"move down: {line()}")
        jobs("move", str(b), "up")
        need(line() == [a, b, c], f"move up: {line()}")
        jobs("move", str(a), "after", str(c))
        need(line() == [b, c, a], f"move after: {line()}")
        out = jobs("move", str(a), "before", str(b))
        need(line() == [a, b, c] and "number 1 in line" in out, f"move before: {line()} {out}")
        jobs("move", str(a), "bottom")
        need(line() == [b, c, a], f"move bottom: {line()}")
        # Held jobs keep their place too; the job numbers never change.
        jobs("held", str(c))
        need(line() == [b, c, a], f"a held job lost its place: {line()}")
        jobs("mark", str(b), "running since 12:00")
        jobs("move", str(b), "top", ok=False)
        jobs("move", str(a), "before", str(a), ok=False)
        jobs("move", str(a), "sideways", ok=False)
        need(line() == [c, a], f"the line after one started: {line()}")
        lst = jobs("list")
        need(f"Job {c} · held: usage over the line · number 1 in line" in lst and f"Job {a} · ready · number 2 in line" in lst,
             f"list doesn't show the place in line: {lst}")
        need("move N top" in jobs("--help"), "--help doesn't say how to move a job")
        # The routine takes the first of the line, not the oldest ready one.
        tick = (jv / "routine/tick.py").read_text()
        need('line = q.get("waiting")' in tick and "job = line[0]" in tick and 'ready = q["ready"]' not in tick,
             "the routine doesn't take the top of the line")
        # The status page numbers the waiting jobs in their order.
        js = f"""import {{ parseRoadmap }} from {json.dumps(str(jv / 'status/parse.mjs'))};
import {{ readFileSync }} from 'node:fs';
const r = parseRoadmap(readFileSync({json.dumps(str(rm))}, 'utf8'));
console.log(JSON.stringify({{problems: r.problems, w: r.queue.jobs.filter((j) => j.place).map((j) => [j.n, j.place])}}));"""
        d = json.loads(sp.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True).stdout)
        need(not d["problems"] and d["w"] == [[c, 1], [a, 2]], f"the status page reads the place in line wrong: {d}")
        page = (jv / "status/index.html").read_text()
        need("j.place ? `${j.place}. `" in page, "the status page doesn't show the place in line")
        # A call may move jobs; the call rules say how.
        pol = Policy(config.FOLDER)
        q_ = f'python3 "{ROOT}/routine/jobs.py"'  # M1: HQ's own script
        need(pol.decide("Bash", {"command": f"{q_} move 28 top"}).verdict == ALLOW, "a call can't move a job")
        need(pol.decide("Bash", {"command": f"{q_} mark 28 ready"}).verdict == DENY, "a call may mark a job")
        need("move N before M" in config.VOICE_RULES, "the call rules don't say how to move a job")
        return "top, up, down, bottom, before and after keep the line right; held keeps its place; routine takes the top; page numbers them; call may move"

    async def flow32(self) -> str:
        """H38: the Cancel button stays, and a late tap sends "Cancel last message". First the real call
        page in a headless browser, with a fake live call whose data channel only records what is sent;
        then on the live test call a long answer is cancelled while she talks (two Claude turns)."""
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms)), sent = [];
  dc = { readyState: "open", send: x => { if (String(x).startsWith("{")) sent.push(JSON.parse(x).type); }, close() {} };
  const server = st => onServerMessage({ data: JSON.stringify({ type: "jarvis-state", state: st }) });
  const can = on => onServerMessage({ data: JSON.stringify({ type: "jarvis-cancellable", on }) });
  const shown = () => cancelBtn.classList.contains("show");
  const asking = () => cxAsk.classList.contains("open");
  const check = (name, ok, why) => out.push(name + ":" + (ok ? "ok" : "WRONG " + why));
  const nsent = () => sent.filter(t => t === "cancel").length;
  setState("live", "On the call");
  check("place", cancelBtn.className === "live" && getComputedStyle(cancelBtn).display !== "none", cancelBtn.className);
  // 1. early, within three seconds: sent at once, no question
  can(true); server("thinking"); await wait(500);
  check("shows", shown(), cancelBtn.className);
  cancelBtn.click(); await wait(50);
  check("early", nsent() === 1 && !asking() && !shown(), nsent() + "/" + asking() + "/" + shown());
  // 2. she starts answering: the button stays
  can(true); server("thinking"); await wait(300); can(false); server("speaking"); await wait(300);
  check("stays", shown(), cancelBtn.className);
  // 3. past three seconds: the question first; a double tap can't confirm; Keep keeps
  await wait(3000);
  cancelBtn.click(); await wait(50);
  check("asks", asking() && nsent() === 1, asking() + "/" + nsent());
  document.getElementById("cxyes").click(); await wait(50);
  check("doubletap", asking() && nsent() === 1, asking() + "/" + nsent());
  document.getElementById("cxno").click(); await wait(50);
  check("keep", !asking() && shown() && nsent() === 1, asking() + "/" + shown() + "/" + nsent());
  // 4. asked again, confirmed after half a second: sent, button gone
  cancelBtn.click(); await wait(600);
  document.getElementById("cxyes").click(); await wait(50);
  check("confirm", !asking() && !shown() && nsent() === 2, asking() + "/" + shown() + "/" + nsent());
  // 5. she's done: still there after 19 s, gone after 20 s; carrying on restarts the wait
  can(true); server("thinking"); await wait(200); can(false); server("speaking"); await wait(200); server("listening");
  await wait(10000); server("speaking"); await wait(200); server("listening");
  await wait(19000);
  check("linger", shown(), cancelBtn.className);
  await wait(1500);
  check("gone", !shown() && cancelBtn.className === "live", cancelBtn.className);
  // 6. his next turn hides it: holding the talk button, talking, typing
  can(true); server("thinking");
  muteBtn.dispatchEvent(new PointerEvent("pointerdown", { pointerId: 1, bubbles: true })); await wait(500);
  check("hold", !shown(), cancelBtn.className);
  document.dispatchEvent(new PointerEvent("pointerup", { pointerId: 1, bubbles: true })); await wait(100);
  can(true); can(false); server("speaking"); await wait(100); server("hearing"); await wait(50);
  check("talk", !shown(), cancelBtn.className);
  can(true); can(false); await wait(100); typeIn.value = "hello"; typeForm.dispatchEvent(new Event("submit", { cancelable: true })); await wait(50);
  check("typed", !shown(), cancelBtn.className);
  // 7. the question closes when the button goes, and when the call ends
  can(true); await wait(3200); cancelBtn.click(); await wait(50); server("hearing"); await wait(50);
  check("closes", !asking(), asking());
  check("late-strike", typeof markCancelled === "function", "");
  const pre = document.createElement("pre"); pre.id = "h38"; pre.textContent = "H38RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f = self.tmp / "h38.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", "--autoplay-policy=no-user-gesture-required",
                                          "--virtual-time-budget=120000", "--dump-dom", f.as_uri()], timeout=180)
        m = re.search(r'<pre id="h38">H38RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        res = m.group(1)
        say(f"   {res}")
        need(all(part.endswith(":ok") for part in res.split(" | ")), f"the call page's Cancel is wrong: {res}")
        need("(Cancel button)" in (APP / "transcript.py").read_text(), "the transcript doesn't mark the button's line")
        bot_src = (APP / "bot.py").read_text()
        need("late_cancel(worker, call.llm, call_state" in bot_src, "the call server doesn't send a late Cancel on")

        from pipeline import late_cancel, type_to_jarvis

        live = await self.get_live()
        llm = live.llm
        flags: list[bool] = []
        llm.on_cancellable = flags.append
        struck: list[bool] = []
        n = len(llm.turns)
        say(f"typing, then cancelling late: {Q_LATE_CANCEL}")
        t0 = time.perf_counter()
        need(await type_to_jarvis(live.worker, llm, live.call_state, Q_LATE_CANCEL), "the typed message was refused")
        await live.wait_for(lambda: len(llm.turns) > n and llm.turns[n]["reply"].strip(), 90, "her answer to start")
        await live.wait_for(lambda: live.after_tts.first("audio", t0)[0] is not None, 30, "her voice to start")
        await asyncio.sleep(1.5)
        need(not llm.cancellable, "the early Cancel was still offered while she talked")
        flags.clear()
        t1 = time.perf_counter()
        need(await late_cancel(live.worker, llm, live.call_state, lambda: struck.append(True)), "the late Cancel was refused")
        need(struck == [True], "the call page wasn't told to strike his line through")
        await live.wait_for(lambda: len(llm.turns) > n + 1 and not llm._replying, 90, "Claude's reply to the Cancel line")
        await live.wait_for(lambda: not live.call.fillers.talking
                            and live.after_tts.first("tts_stopped", t1 + 0.5)[0] is not None, 30, "the voice to finish")
        first, btn = llm.turns[n], llm.turns[n + 1]
        # Her text may already be complete while the voice still reads it, so the voice is checked:
        # an interruption reaches it, and nothing more of that answer is heard after it.
        ctx = [v for _, v in live.after_tts.all("audio", t0, t1)][-1]
        ti, _ = live.after_tts.first("interruption", t1)
        need(first.get("cancelled") and ti is not None, f"her answer wasn't stopped: cancelled {first.get('cancelled')}, interruption {ti}")
        more = [t for t, v in live.after_tts.all("audio", ti + 0.3) if v == ctx]
        need(not more, f"she went on with the cancelled answer for {len(more)} audio frames")
        need(btn["words"] == "Cancel last message" and btn.get("button"), f"the Cancel line didn't go in as his turn: {btn['words']!r}")
        need("Cancel button" in btn["sent"] and Q_LATE_CANCEL[:20] in btn["sent"], "Claude wasn't told the line came from the button")
        need(f"{config.USER} typed this" not in btn["sent"], "the button's line was told to Claude as something he typed")
        need(True not in flags, f"the Cancel line itself was offered for cancelling: {flags}")
        reply = btn["reply"].strip()
        say(f"   Jarvis said: {reply!r}")
        need(len(reply) < 120 and not re.search(r"\b(twenty|thirty|forty)\b", norm(reply)), f"she went on counting: {reply!r}")
        need(not await late_cancel(live.worker, llm, live.call_state), "a second late Cancel took back the Cancel line")
        tx = live.call.transcript.path.read_text()
        need(f"**{config.USER_LABEL}:** {Q_LATE_CANCEL} *(typed)* *(cancelled)*" in tx, "the transcript doesn't mark his line cancelled")
        need(f"**{config.USER_LABEL}:** Cancel last message *(Cancel button)*" in tx, "the transcript doesn't mark the line as from the button")
        return ("page: stays after she starts, gone on his next turn or 20 s after; asks after 3 s, Keep keeps, no double tap; "
                f"call: a late Cancel stopped her, Cancel last message went in from the button, she said {reply!r}")

    async def flow35(self) -> str:
        """H40: a mute button for her voice. No Claude turns. The real call page in a headless browser,
        twice with the same profile: before a call the button is there and switches her voice off (the
        audio element muted, her incoming track off), during a fake live call too, the chat still gets
        her lines, the talk button, the low talk sound and Cancel work as before; the second load
        remembers the choice."""
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        first = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const check = (name, ok, why) => out.push(name + ":" + (ok ? "ok" : "WRONG " + why));
  const server = st => onServerMessage({ data: JSON.stringify({ type: "jarvis-state", state: st }) });
  const on = () => voiceBtn.getAttribute("aria-pressed") === "true";
  try { localStorage.removeItem("jarvis-voice-off"); } catch (e) {}
  voiceOff = false; applyVoice();
  const cs = getComputedStyle(voiceBtn);
  check("there", cs.display !== "none" && cs.position === "fixed" && !on() && !audioEl.muted, cs.display + "/" + cs.position + "/" + on());
  // before a call: off, remembered
  voiceBtn.click(); await wait(50);
  check("idle-off", on() && audioEl.muted && localStorage.getItem("jarvis-voice-off") === "on", on() + "/" + audioEl.muted);
  // her track arrives while it's off: switched off too
  const ctx = new AudioContext(), dst = ctx.createMediaStreamDestination();
  audioEl.srcObject = dst.stream; applyVoice();
  const tr = () => dst.stream.getAudioTracks()[0].enabled;
  check("track-off", !tr() && audioEl.muted, tr() + "/" + audioEl.muted);
  // on a live call: status says so, the orb says so while she speaks, her lines still reach the chat
  setState("live", "On the call"); setMuted(false);
  check("status", statusEl.textContent.includes("voice off"), statusEl.textContent);
  server("speaking"); await wait(50);
  check("orb", orbLabel.textContent === "Speaking · voice off", orbLabel.textContent);
  onServerMessage({ data: JSON.stringify({ type: "jarvis-chat", who: "jarvis", text: "Paris is the capital." }) });
  check("chat", [...chatLog.querySelectorAll(".msg.jarvis")].some(d => d.textContent === "Paris is the capital."), chatLog.textContent);
  // the talk button, its low sound, and Cancel as before
  server("listening");
  let sounds = 0; const ts = talkSound; talkSound = () => { sounds++; return ts(); };
  muteBtn.dispatchEvent(new PointerEvent("pointerdown", { pointerId: 1, bubbles: true })); await wait(600);
  check("talk", muteBtn.classList.contains("talk") && sounds === 1 && audioEl.muted, muteBtn.className + "/" + sounds);
  document.dispatchEvent(new PointerEvent("pointerup", { pointerId: 1, bubbles: true })); await wait(100);
  onServerMessage({ data: JSON.stringify({ type: "jarvis-cancellable", on: true }) }); server("thinking"); await wait(50);
  check("cancel", cancelBtn.classList.contains("show"), cancelBtn.className);
  // on again during the call: track and element back on, status without it
  voiceBtn.click(); await wait(50);
  check("live-on", !on() && !audioEl.muted && tr() && localStorage.getItem("jarvis-voice-off") === "off", on() + "/" + audioEl.muted + "/" + tr());
  check("status-on", !statusEl.textContent.includes("voice off"), statusEl.textContent);
  // and off again, to be remembered by the second load
  voiceBtn.click(); await wait(50);
  check("live-off", on() && audioEl.muted && !tr(), on() + "/" + audioEl.muted + "/" + tr());
  const pre = document.createElement("pre"); pre.id = "h40"; pre.textContent = "H40RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        second = r"""
<script>
(async () => {
  const out = [];
  const check = (name, ok, why) => out.push(name + ":" + (ok ? "ok" : "WRONG " + why));
  check("remembered", voiceBtn.getAttribute("aria-pressed") === "true" && audioEl.muted, voiceBtn.getAttribute("aria-pressed") + "/" + audioEl.muted);
  const pre = document.createElement("pre"); pre.id = "h40"; pre.textContent = "H40RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        prof = self.tmp / "h40-profile"
        res_all = []
        for name, harness in (("h40a", first), ("h40b", second)):
            f = self.tmp / f"{name}.html"
            f.write_text(page.replace("</body>", harness + "</body>", 1))
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", "--autoplay-policy=no-user-gesture-required",
                                              f"--user-data-dir={prof}", "--virtual-time-budget=20000", "--dump-dom", f.as_uri()], timeout=90)
            m = re.search(r'<pre id="h40">H40RESULT (.*?) END</pre>', r.stdout)
            need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
            res_all.append(m.group(1))
        res = " | ".join(res_all)
        say(f"   {res}")
        need(all(part.endswith(":ok") for part in res.split(" | ")), f"the voice button is wrong: {res}")
        # The page's own sounds never go through her audio element, so they stay whatever this button says.
        for fn in ("function tick()", "function click()", "function talkSound()"):
            body = page.split(fn, 1)[1].split("\n}\n", 1)[0]
            need("audioEl" not in body and "audioCtx.destination" in body, f"{fn} goes through her voice now")
        need('setAttribute("switch", "")' in page and "CANCEL_ASK_MS = 3000" in page, "the H24 tick or the H31/H38 Cancel changed")
        return "her voice off before and during a call (element muted, track off); chat still gets her lines; talk button, low sound, Cancel unchanged; remembered on the next load"

    # 36
    async def flow36(self) -> str:
        """H41: the Type to Jarvis box is a text field that grows downward as he types, up to about six
        lines, then scrolls inside. No Claude turns. The real call page in a headless browser at phone
        width, on a fake live call: one line stays one line high, a few lines grow it so all of it shows,
        a long text stops at the max and scrolls; on the computer Enter sends and Shift+Enter doesn't,
        on a phone Enter is a new line and Send sends; after sending the box is one line again."""
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const check = (name, ok, why) => out.push(name + ":" + (ok ? "ok" : "WRONG " + why));
  const sent = [];
  dc = { readyState: "open", send: t => sent.push(JSON.parse(t)), close() {} };
  setState("live", "On the call"); showChat(true); await wait(50);
  const type = v => { typeIn.value = v; typeIn.dispatchEvent(new Event("input", { bubbles: true })); };
  const h = () => typeIn.getBoundingClientRect().height;
  const all = () => typeIn.scrollHeight <= typeIn.clientHeight + 1;
  check("textarea", typeIn.tagName === "TEXTAREA" && typeForm.classList.contains("show"), typeIn.tagName + "/" + typeForm.className);
  type("What's on tomorrow?"); await wait(30);
  const one = h();
  check("one-line", one >= 40 && one <= 50 && all(), one);
  type("Line one of what I want to say\nline two\nline three\nline four"); await wait(30);
  const four = h();
  check("grows", four > one + 40 && four <= 150 && all() && getComputedStyle(typeIn).overflowY === "hidden", one + "->" + four);
  const sendBox = typeSend.getBoundingClientRect(), inBox = typeIn.getBoundingClientRect();
  check("send-bottom", Math.abs(sendBox.bottom - inBox.bottom) < 2, sendBox.bottom + "/" + inBox.bottom);
  type(Array.from({ length: 20 }, (_, i) => "line " + (i + 1)).join("\n")); await wait(30);
  check("max-scrolls", Math.round(h()) === 150 && getComputedStyle(typeIn).overflowY === "auto" && typeIn.scrollHeight > typeIn.clientHeight, h() + "/" + getComputedStyle(typeIn).overflowY);
  // the computer: Shift+Enter doesn't send, Enter does, and the box is one line again
  type("Hello from the computer");
  let ev = new KeyboardEvent("keydown", { key: "Enter", shiftKey: true, bubbles: true, cancelable: true });
  typeIn.dispatchEvent(ev); await wait(30);
  check("shift-enter", sent.length === 0 && !ev.defaultPrevented, sent.length);
  ev = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
  typeIn.dispatchEvent(ev); await wait(30);
  check("enter-sends", sent.length === 1 && sent[0].type === "typed" && sent[0].text === "Hello from the computer" && ev.defaultPrevented, JSON.stringify(sent));
  check("reset", typeIn.value === "" && Math.abs(h() - one) < 1 && typeSend.disabled, typeIn.value + "/" + h());
  // a phone: Enter is a new line, Send sends
  const mm = window.matchMedia;
  window.matchMedia = q => q.includes("coarse") ? { matches: true } : mm.call(window, q);
  type("Hello from the phone\nsecond line");
  ev = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
  typeIn.dispatchEvent(ev); await wait(30);
  check("phone-enter", sent.length === 1 && !ev.defaultPrevented, sent.length);
  typeSend.click(); await wait(30);
  check("phone-send", sent.length === 2 && sent[1].text === "Hello from the phone\nsecond line" && typeIn.value === "", JSON.stringify(sent[1]));
  window.matchMedia = mm;
  const pre = document.createElement("pre"); pre.id = "h41"; pre.textContent = "H41RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f = self.tmp / "h41.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", "--window-size=390,844",
                                          f"--user-data-dir={self.tmp / 'h41-profile'}", "--virtual-time-budget=20000", "--dump-dom", f.as_uri()], timeout=90)
        m = re.search(r'<pre id="h41">H41RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        res = m.group(1)
        say(f"   {res}")
        need(all(part.endswith(":ok") for part in res.split(" | ")), f"the text field is wrong: {res}")
        return "a text field: one line stays one line, more lines grow it so all shows, stops at about six and scrolls; Enter sends on the computer, a new line on the phone; one line again after sending"

    async def flow37(self) -> str:
        """H42: a failed routine run says why, and the watchdog notices one that keeps failing. On copies
        in the test folder; nothing live is changed, no Claude, no Terminal window opened."""
        import importlib, importlib.util, subprocess as sp, sys as _sys
        jv = ROOT
        _sys.path.insert(0, str(jv / "routine"))
        import incidents, routines, failures, tick
        for m in (incidents, routines, failures, tick):
            importlib.reload(m)
        tmp = self.tmp / "h42"  # its own folder: flow 25 leaves its copies in the test folder
        tmp.mkdir()
        sup = tmp / "support"
        sup.mkdir()
        incidents.FILE, incidents.EVENTS = str(tmp / "incidents.json"), str(sup / "events.jsonl")
        routines.FILE = str(tmp / "routines.json")
        failures.SUPPORT, failures.FILE = str(sup), str(sup / "failures.json")
        tick.incidents, tick.routines, tick.failures = incidents, routines, failures
        tick.RUN, tick.MAIL_RUNS = str(tmp), str(tmp / "mail-runs")
        for name in ("MAIL_LAST", "MAIL_RETRY", "MAIL_STATE", "MAIL_PID"):
            setattr(tick, name, str(tmp / name.lower()))
        # 1. The 17:00 run, as its log had it: the reason is in its own output, not in the usage lines after it.
        block = ("--- 2026-10-10 17:00:11\nAPI Error: Can't reach the API server — check your internet or DNS (ENOTFOUND)\n"
                 "(the mail check's run brought no usage back)\n--- exit 1\n41%  5-hour limit  (read 34 min ago)\n"
                 "These numbers are old: nothing has read the usage since; they're greyed out on the status page.\n")
        open(tmp / "mail.log", "w").write(block)
        r = tick.mail_result()
        need(not r["ok"] and r["why"].startswith("No internet") and "exit 1" in r["text"] and "old" not in r["text"]
             and any("ENOTFOUND" in l for l in r["detail"]), f"the 17:00 run doesn't say why: {r}")
        open(tmp / "mail.log", "a").write("--- 2026-10-10 18:00:31\nNothing new.\n--- exit 0\n3%  5-hour limit\n")
        need(tick.mail_result() == {"ok": True, "text": "Nothing new.", "run": ""}, f"a good run doesn't read as fine: {tick.mail_result()}")
        # 2. A finished run that failed: the routine line, the incident and the count in a row keep why.
        now = time.time()
        open(tick.MAIL_LAST, "w").write(str(int(now)))
        open(tmp / "mail.log", "w").write(block)
        json.dump({"pid": None, "started": now - 200}, open(tick.MAIL_STATE, "w"))
        need(tick.mail_running() is False, "a finished mail check reads as running")
        line = routines.read()["mail"]
        inc = incidents.is_down("mail")
        need(line["state"] == "down" and "No internet" in line["text"] and line["detail"], f"the routine line doesn't say why: {line}")
        need(inc and "No internet" in inc["why"] and any("ENOTFOUND" in l for l in inc["detail"]), f"the incident doesn't keep why: {inc}")
        need(failures.read()["mail"]["n"] == 1, f"the failure isn't counted: {failures.read()}")
        # the retry fails again: counted, and noted on the same incident; after the last try it has given up.
        for _ in range(tick.MAIL_RETRIES):
            json.dump({"pid": None, "started": now - 100}, open(tick.MAIL_STATE, "w"))
            tick.mail_running()
        f = failures.read()["mail"]
        inc = incidents.is_down("mail")
        need(f["n"] == 3 and f["gave_up"] and any(x["what"].startswith("Failed again: No internet") for x in inc["fixes"]),
             f"failures in a row aren't counted or noted: {f} {inc['fixes']}")
        # 3. The watchdog, on a copy: notes it once, asks for one more try when the internet is there.
        spec = importlib.util.spec_from_file_location("wd_h42", jv / "routine" / "watchdog.py")
        wd = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(wd)
        wd.SUPPORT = str(sup)
        wd.online = lambda: True
        seen = wd.failing()
        need(seen and "3 times in a row" in seen[0] and "No internet" in seen[0], f"the watchdog didn't notice: {seen}")
        ev = [json.loads(l) for l in open(sup / "events.jsonl")]
        need(len(ev) == 2 and all(e["key"] == "mail" for e in ev) and ev[0]["what"].startswith("Noticed")
             and "one more try" in ev[1]["what"] and (sup / "retry-mail").exists(), f"the watchdog's notes are wrong: {ev}")
        wd.failing()
        need(len(open(sup / "events.jsonl").read().splitlines()) == 2, "the watchdog noted the same streak twice")
        # its notes go with the mail check's incident
        incidents.watchdog_events()
        inc = incidents.is_down("mail")
        need(sum(x["what"].startswith("Watchdog:") for x in inc["fixes"]) == 2, f"the watchdog's notes aren't with the incident: {inc['fixes']}")
        # 4. The helper starts the try the watchdog asked for, once.
        started = []
        real_start = tick.start_mail
        tick.start_mail = lambda: started.append(1)
        tick.mail({"mail": True, "on": True})
        tick.start_mail = real_start
        need(started == [1] and not (sup / "retry-mail").exists()
             and any("watchdog asked" in x["what"] for x in incidents.is_down("mail")["fixes"]), "the asked-for try didn't start")
        # 5. It works again: the count ends, the watchdog notes it.
        open(tmp / "mail.log", "w").write("--- 2026-10-10 18:00:31\nNothing new.\n--- exit 0\n")
        json.dump({"pid": None, "started": now - 100}, open(tick.MAIL_STATE, "w"))
        tick.mail_running()
        need(failures.read()["mail"]["n"] == 0 and not incidents.is_down("mail"), "a good run doesn't end the failures")
        wd.failing()
        need("works again" in open(sup / "events.jsonl").read().splitlines()[-1], "the watchdog didn't note it works again")
        # 6. Each mail check keeps its own output file (the window's script tees into it); nothing is opened.
        calls = []
        real_run = tick.subprocess.run
        tick.subprocess.run = lambda *a, **k: calls.append(a)
        try:
            tick.start_mail()
        finally:
            tick.subprocess.run = real_run
        cmd = open(tmp / "mail-check.command").read()
        runs = list((tmp / "mail-runs").glob("*.log")) or [None]
        need(calls and "mail-runs/" in cmd and "tee -a" in cmd, "the mail check doesn't keep its own output")
        # 7. stream-usage says when the run ended with an error; the page and the installed watchdog.
        out = sp.run([_sys.executable, str(jv / "routine/stream-usage.py")], input=json.dumps(
            {"type": "result", "is_error": True, "subtype": "error_during_execution", "result": ""}) + "\n",
            capture_output=True, text=True).stdout
        need("(the run ended with an error: error_during_execution)" in out, f"stream-usage doesn't say the error: {out!r}")
        html = (jv / "status/index.html").read_text()
        need("What it said last" in html and "i.detail" in html, "the status page doesn't show what a failed run said")
        installed = Path.home() / "Library/Application Support/JarvisVA/watchdog.py"
        need(installed.exists() and installed.read_text() == (jv / "routine/watchdog.py").read_text(),
             "the installed watchdog isn't the new one: run routine/install-watchdog.sh")
        return ("the 17:00 run reads as no internet, with its last lines; counted in a row; the watchdog notes it once, "
                "asks for one more try, and notes it works again; each mail check keeps its own output")

    async def flow39(self) -> str:
        """H45: the lid-closed sleep switch. No Claude turns, and never the real sudo or a real change: the
        real setting is only read; flipping runs against a fake sudo and pmset in the scratch folder."""
        sys.path.insert(0, str(ROOT / "routine"))
        import importlib
        import lidsleep as L
        importlib.reload(L)
        r = await asyncio.to_thread(run, [sys.executable, str(ROOT / "routine/lidsleep.py"), "--dry"], timeout=30)
        need(r.returncode == 0 and ("On:" in r.stdout or "Off:" in r.stdout), f"the setting can't be read: {(r.stdout + r.stderr).strip()[-200:]}")
        real = "on" if r.stdout.startswith("On:") else "off"
        # A fake pmset that keeps its setting in a file, and a fake sudo that, like sudo -n, refuses unless "set up".
        d = self.tmp / "h45"; d.mkdir()
        state, calls, allowed = d / "state", d / "calls", d / "allowed"
        state.write_text("0")
        (d / "pmset").write_text(f"""#!/bin/sh
if [ "$1" = "-g" ]; then printf 'System-wide power settings:\\n SleepDisabled\\t\\t%s\\n' "$(cat '{state}')"; exit 0; fi
if [ "$1 $2" = "-a disablesleep" ]; then echo "$3" > '{state}'; exit 0; fi
exit 1
""")
        (d / "sudo").write_text(f"""#!/bin/sh
echo "$@" >> '{calls}'
[ "$1" = "-n" ] || exit 9
[ -f '{allowed}' ] || {{ echo "sudo: a password is required" >&2; exit 1; }}
shift; exec "$@"
""")
        for f in ("pmset", "sudo"):
            os.chmod(d / f, 0o755)
        L.PMSET, L.SUDO, L.SUDOERS = str(d / "pmset"), str(d / "sudo"), str(d / "sudoers-installed")
        L.NOW_FILE = str(d / "lidsleep.json")
        L.COMMAND = {"on": [L.PMSET, "-a", "disablesleep", "1"], "off": [L.PMSET, "-a", "disablesleep", "0"]}
        ok, msg = L.flip("on")
        need(not ok and "one-time setup" in msg and "install-lidsleep.sh" in msg and state.read_text().strip() == "0",
             f"without the setup it should refuse and say the line to type: {msg}")
        allowed.write_text("x"); Path(L.SUDOERS).write_text("x")
        ok, msg = L.flip("on")
        need(ok and state.read_text().strip() == "1" and L.read() is True and msg.startswith("Done. On"), f"turning it on didn't work: {msg}")
        ok, msg = L.flip("on")
        need(ok and "already" in msg, f"turning it on twice should say it already was: {msg}")
        ok, msg = L.flip("off")
        need(ok and state.read_text().strip() == "0" and msg.startswith("Done. Off"), f"turning it off didn't work: {msg}")
        lines = calls.read_text().splitlines()
        need(lines and all(c.startswith("-n ") and c.endswith(("disablesleep 1", "disablesleep 0")) for c in lines),
             f"sudo was asked for something else than the two commands, or without -n: {lines}")
        L.write(False)
        need(json.loads(Path(L.NOW_FILE).read_text())["on"] is False, "the reading isn't written for the status page")
        # The one-time setup: only the two exact commands, checked by visudo, the real pmset path.
        rule = (ROOT / "routine/jarvis-lidsleep.sudoers").read_text()
        body = [x for x in rule.splitlines() if x.strip() and not x.startswith("#")]
        need(body == ["YOUR_USER ALL=(root) NOPASSWD: /usr/bin/pmset -a disablesleep 1, /usr/bin/pmset -a disablesleep 0"],
             f"the sudoers rule allows more than the two commands: {body}")
        v = await asyncio.to_thread(run, ["/usr/sbin/visudo", "-cf", str(ROOT / "routine/jarvis-lidsleep.sudoers")], timeout=20)
        need(v.returncode == 0, f"the sudoers rule doesn't pass visudo: {(v.stdout + v.stderr).strip()}")
        inst = (ROOT / "routine/install-lidsleep.sh").read_text()
        need("visudo -cf" in inst and inst.index("visudo -cf") < inst.index("mv ") and "chmod 440" in inst,
             "the setup doesn't check the rule with visudo before putting it in")
        # A call: read it, flip it on or off, nothing else.
        from policy import Policy, ALLOW, DENY
        pol = Policy(config.FOLDER)
        c = f'python3 "{ROOT}/routine/lidsleep.py"'  # M1: HQ's own script
        for extra, want in (("", ALLOW), (" on", ALLOW), (" off", ALLOW), (" --dry", DENY), (" on off", DENY)):
            need(pol.decide("Bash", {"command": c + extra}).verdict == want, f"a call and '{c + extra}': not {want}")
        need(pol.decide("Bash", {"command": "sudo pmset -a disablesleep 1"}).verdict != ALLOW, "a call may run sudo itself")
        need("lidsleep.py" in config.VOICE_RULES and "lid closed" in config.VOICE_RULES, "the call rules don't say how to flip it")
        tick = (ROOT / "routine/tick.py").read_text()
        need('LIDSLEEP = os.path.join(HERE, "lidsleep.py")' in tick and "[PY, LIDSLEEP]" in tick, "the routine doesn't read it every minute")
        need("sudo" not in tick.split("[PY, LIDSLEEP]")[0].split("H45")[-1], "the routine flips it")
        # The status page: served, and shown under Laptop.
        site = self.tmp / "h45site"
        shutil.copytree(ROOT / "status", site / "status", ignore=shutil.ignore_patterns("icons"))
        (site / ".status").mkdir()
        shutil.copy(ROADMAP, site_roadmap(site))
        now = int(time.time())
        (site / ".status/lidsleep.json").write_text(json.dumps({"t": now, "on": True, "words": "x", "setup": False, "setup_line": "y"}))
        port = 4795
        proc = subprocess.Popen([shutil.which("node") or "/opt/homebrew/bin/node", str(site / "status/server.mjs"), "--quiet"],
                                env={**os.environ, "JARVIS_STATUS_PORT": str(port)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                if http_get("/routines.json", base)[0] == 200:
                    break
                await asyncio.sleep(0.2)
            _, body, _ = http_get("/routines.json", base)
            need(json.loads(body).get("lidsleep", {}).get("on") is True, "the server doesn't serve the lid-closed sleep")
        finally:
            proc.terminate()
            proc.wait(timeout=5)
        html = (ROOT / "status/index.html").read_text()
        need("'Lid closed: '" in html and "keeps working (sleep off)" in html and "routines.lidsleep" in html,
             "the status page doesn't show the lid-closed sleep under Laptop")
        return (f"read for real ({real}); refuses without the setup and says the line; on, again, off through sudo -n on "
                "only the two commands; the rule passes visudo; a call may read or flip, nothing else; read every minute; on the page")

    async def flow40(self) -> str:
        """F13: a job let past the line only skips the 5-hour line. The weekly line always counts, so a
        past-the-line job held at the weekly line waits at the gate instead of being started every minute.
        No Claude turns, nothing started: the verdict on made-up readings, the gate's answer, and the
        helper, the queue script, the call rules and the build notes saying so."""
        import subprocess as sp
        jv = ROOT
        js = f"""import {{ usageVerdict }} from {json.dumps(str(jv / 'status/usage.mjs'))};
const future = new Date(Date.now() + 3 * 86400000).toISOString();
const r = (five, week, kept = false) => ({{ readable: true, limits: [
  {{ label: '5-hour limit', percent: five, resetsAt: future }},
  {{ label: 'Weekly · all models', percent: week, resetsAt: future, kept }} ] }});
const v = (x, o) => usageVerdict(x, 70, new Date(), 50, o).stop;
console.log(JSON.stringify({{
  fiveOverNormal: v(r(90, 10)), fiveOverPast: v(r(90, 10), {{ weeklyOnly: true }}),
  weekOverPast: v(r(10, 60), {{ weeklyOnly: true }}), bothOverPast: v(r(90, 60), {{ weeklyOnly: true }}),
  keptWeekPast: v(r(90, 99, true), {{ weeklyOnly: true }}),
  unreadablePast: usageVerdict({{ readable: false }}, 70, new Date(), 50, {{ weeklyOnly: true }}).stop }}));"""
        out = sp.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True)
        need(out.returncode == 0, f"the verdict check didn't run: {out.stderr.strip()[:200]}")
        d = json.loads(out.stdout)
        need(d["fiveOverNormal"], "a normal job doesn't stop at the 5-hour line")
        need(not d["fiveOverPast"], "a past-the-line job still stops at the 5-hour line")
        need(d["weekOverPast"] and d["bothOverPast"], "a past-the-line job goes past the weekly line")
        need(not d["keptWeekPast"], "an old kept weekly number stops a past-the-line job")
        need(d["unreadablePast"], "a past-the-line job goes on when the usage can't be read")
        g = sp.run(["node", str(jv / "status/save-usage.mjs"), "--gate", "--weekly-only"], capture_output=True, text=True)
        need(g.returncode in (0, 2) and g.stdout.startswith(("OK", "STOP")), f"the weekly-only gate didn't answer: {g.stdout}{g.stderr}")
        need("5-hour" not in g.stdout or g.returncode == 0, f"the weekly-only gate stops on the 5-hour line: {g.stdout}")
        tick = (jv / "routine/tick.py").read_text()
        need('if not job["past"]:' not in tick, "the helper still skips the usage check for a past-the-line job")
        need('(["--weekly-only"] if job["past"] else [])' in tick, "the helper doesn't check the weekly line for a past-the-line job")
        need("--weekly-only, and on STOP hold" in tick, "a past-the-line job isn't told the weekly line still counts")
        need("the weekly line still counts" in (jv / "routine/jobs.py").read_text(), "the queue script doesn't say the weekly line counts")
        need("the weekly line always counts" in config.VOICE_RULES, "the call rules don't say the weekly line always counts")
        notes = (config.DATA / "CLAUDE.md").read_text()  # M1: the build notes are in the workspace
        need("--weekly-only" in notes and 'go past the usage line", go on' not in notes, "the build notes still let a past job go past the weekly line")
        return f"past the line skips only the 5-hour line; weekly over, both over or unreadable stop it; old kept numbers don't; gate says {g.stdout.split('.')[0].split('(')[0].strip()}; helper, queue, call rules and notes agree"

    async def flow41(self) -> str:
        """M2: the clean template. No Claude turns, nothing started. HQ's template/ has every file the app
        reads from a workspace, blank and saying "put your own things here" (me.md with the name, what's
        important, what HQ should manage); nothing of his is in it; the app can read it like a workspace
        (the Quick load, the open loops, the status block and the queue); it is in HQ's repo while
        workspace/ is not; Free is explained plainly on the call page; Heart is the default voice."""
        import subprocess as sp
        tpl = ROOT / "template"
        need(tpl.is_dir(), "HQ has no template folder")
        files = ["README.md", "CLAUDE.md", "rules.md", "where-things-go.md", "me.md", "vision.md",
                 "current-situation.md", "challenges.md", "inbox.md", "coaching/log.md", "Jarvis VA/roadmap.md",
                 "Jarvis VA/calls/.gitkeep", "reviews/.gitkeep", ".claude/settings.json", ".claude/mail-commit.sh",
                 ".claude/skills/life-coach/SKILL.md"]
        missing = [f for f in files if not (tpl / f).exists()]
        need(not missing, f"the template is missing {missing}")
        for rel in re.findall(r"@([\w./-]+\.md)", (tpl / "CLAUDE.md").read_text()):
            need((tpl / rel).exists(), f"the template's CLAUDE.md loads {rel}, which isn't there")
        for f in ("README.md", "rules.md", "me.md", "vision.md", "current-situation.md", "challenges.md", "Jarvis VA/roadmap.md"):
            need("put your own things here" in (tpl / f).read_text().lower(), f"{f} doesn't say put your own things here")
        me = (tpl / "me.md").read_text()
        need("**Name:**" in me and "What's important to me" in me and "What HQ should manage for me" in me,
             "me.md doesn't ask for the name, what's important and what HQ should manage")
        # Nothing of his: names, places, his work and care, his addresses and paths.
        personal = privacy.pattern(privacy.words(config.FOLDER))  # M5: the user's private words, from me.md
        hits = []
        for p in tpl.rglob("*"):
            if p.is_file():
                for m in personal.finditer(p.read_text(errors="replace")):
                    hits.append(f"{p.relative_to(tpl)}: {m.group(0)}")
        need(not hits, f"the template has something of his: {hits[:6]}")
        settings = json.loads((tpl / ".claude/settings.json").read_text())
        need(all(f"mcp__claude_ai_Gmail__{a}" in settings["permissions"]["deny"] for a in ("send_message", "reply", "forward")),
             "the template doesn't deny sending mail")
        need("rules.md" in json.dumps(settings.get("hooks", {})), "the template doesn't repeat rules.md with every message")
        # The app reads it like a workspace.
        import quick_context, open_loops
        q = quick_context.build(tpl)
        need("Contents of" in q and "challenges.md" in q and "inbox.md" in q, "the Quick load doesn't read the template")
        loops = open_loops.read(tpl)
        need(not loops.very_important, f"the blank mail list has very important items: {loops.very_important}")
        roadmap = tpl / "Jarvis VA/roadmap.md"
        js = f"""import {{ readFileSync }} from 'node:fs';
import {{ parseRoadmap }} from '{(ROOT / "status/parse.mjs").as_uri()}';
const r = parseRoadmap(readFileSync({json.dumps(str(roadmap))}, 'utf8'));
console.log(JSON.stringify({{ problems: r.problems, state: r.state, phases: r.phases.length, queue: r.queue }}));"""
        out = sp.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True, timeout=30)
        need(out.returncode == 0, f"the status page's parser failed on the template: {out.stderr[-300:]}")
        r = json.loads(out.stdout)
        need(not r["problems"] and r["state"] == "WAITING" and r["phases"] >= 1,
             f"the status page can't read the template's roadmap: {r}")
        env = dict(os.environ, JARVIS_ROADMAP=str(roadmap))
        q2 = sp.run([sys.executable, str(ROOT / "routine/jobs.py"), "list"], capture_output=True, text=True, env=env, timeout=30)
        need(q2.returncode == 0 and "Routine: on" in q2.stdout and "No jobs yet" in q2.stdout,
             f"the queue can't read the template's roadmap: {q2.stdout}{q2.stderr}")
        # In HQ's repo; the workspace never is.
        ign = lambda rel: sp.run(["git", "-C", str(ROOT), "check-ignore", "-q", rel]).returncode == 0
        need(not ign("template/me.md") and not ign("template/.claude/settings.json"), "the template is ignored by HQ's repo")
        need(ign("workspace"), "the workspace isn't ignored by HQ's repo")
        # Free explained plainly; all the voices, Heart the default.
        page = (ROOT / "app/web/index.html").read_text()
        need(all(w in page for w in ("no connectors", "none of your files", "no notes", "for testing and showing others")),
             "the call page doesn't explain Free plainly")
        need(config.VOICE == "af_heart" and len(config.VOICES) > 1 and config.KOKORO_VOICES.exists(),
             f"the voices: default {config.VOICE}, {len(config.VOICES)} voices")
        return (f"{len(files)} files, blank, nothing of his; the Quick load, the open loops, the status block and the queue "
                f"read it; in HQ's repo, workspace not; Free explained; {len(config.VOICES)} voices, Heart the default")

    async def flow42(self) -> str:
        """M3: the explanations. No Claude turns. README.md tells the user's Claude how to install and check
        everything (the workspace from the template, never over an existing one; the passwords asked up front;
        the happy flows), what's Mac-only and that on Windows Claude builds those itself, and that mail is
        built for Gmail and the calendar for Google Calendar, else Claude researches and builds an alternative.
        ABOUT.md has the big picture: what HQ is, how it works, the agents, what's coming, still in development.
        Nothing of his in either, and both are in HQ's repo."""
        import subprocess as sp
        readme, about = ROOT / "README.md", ROOT / "ABOUT.md"
        need(readme.exists() and about.exists(), "HQ has no README.md or ABOUT.md")
        r, a = readme.read_text(), about.read_text()
        for words, what in ((("install everything and check everything", "cp -R template workspace", "never overwrite",
                              "password", "happy_flows.py"), "the install and check"),
                            (("Mac-only", "Windows", "Claude builds them itself", "Task Scheduler", "start at login",
                              "watchdog", "Terminal", "lid"), "what's Mac-only"),
                            (("Gmail", "Google Calendar", "connector", "research", "alternative"), "mail and calendar"),
                            (("Free", "no connectors", "for testing and showing"), "Free")):
            missing = [w for w in words if w.lower() not in r.lower()]
            need(not missing, f"the readme doesn't cover {what}: {missing}")
        for w in ("still in development", "What HQ is", "How it works", "Agents", "Coming next", "workspace",
                  "Mac", "Gmail", "Google Calendar", "Quick", "Deep", "Free", "watchdog", "status page", "happy flows"):
            need(w.lower() in a.lower(), f"ABOUT.md doesn't cover {w}")
        personal = privacy.pattern(privacy.words(config.FOLDER))  # M5: the user's private words, from me.md
        hits = [f"{f.name}: {m.group(0)}" for f, t in ((readme, r), (about, a)) for m in personal.finditer(t)]
        need(not hits, f"the explanations have something of his: {hits[:6]}")
        ign = lambda rel: sp.run(["git", "-C", str(ROOT), "check-ignore", "-q", rel]).returncode == 0
        need(not ign("README.md") and not ign("ABOUT.md"), "the explanations are ignored by HQ's repo")
        return "the readme (install, check, Mac-only, mail and calendar, Free) and the big picture, nothing of his"

    async def flow43(self) -> str:
        """M4: the installer, in a throwaway copy of HQ, with every step that touches the computer outside
        HQ simulated (HQ_INSTALL_FAKE=1). No Claude turns, no prompts, nothing of his touched. A fresh
        install makes the workspace from the template as its own git repo and ticks every step on the
        checklist; a second run keeps an existing workspace byte for byte; a step made to fail stops the
        checklist there, with why and what to do, and the rest not run. The heads-up names the password and
        Allow; the checklist page is served live, and the status page serves it at /install afterwards."""
        import hashlib, importlib.util, subprocess as sp, urllib.request
        tmp = self.tmp / "m4"
        hq = tmp / "HQ"
        hq.mkdir(parents=True)
        shutil.copytree(ROOT / "install", hq / "install")
        shutil.copytree(ROOT / "template", hq / "template", symlinks=True)
        env = dict(os.environ, HQ_INSTALL_FAKE="1", HQ_INSTALL_PORT="4793")
        env.pop("HQ_WORKSPACE", None)
        inst = [ "/usr/bin/python3", str(hq / "install" / "install.py"), "--yes", "--no-wait", "--no-browser"]
        load = lambda: json.loads((hq / "scratch" / "install" / "checklist.json").read_text())

        r = sp.run(inst, env=env, capture_output=True, text=True, timeout=60, stdin=sp.DEVNULL)
        need(r.returncode == 0, f"a fresh simulated install failed: {(r.stdout + r.stderr)[-400:]}")
        d = load()
        need(d["result"] == "passed" and d["fake"], f"the checklist says {d['result']}")
        states = {(x["phase"], x["id"]): x["state"] for x in d["steps"]}
        need({p for p, _ in states} == {"setup", "test"}, "the checklist doesn't have both rounds, setup and test")
        need(all(v in ("ok", "warn") for v in states.values()), f"not every step ticked: {states}")
        need(states[("setup", "workspace")] == "ok", "a fresh install didn't make the workspace")
        for sid in ("helper", "terminal", "lidsleep"):
            need(next(x for x in d["steps"] if x["phase"] == "setup" and x["id"] == sid)["asks"],
                 f"{sid} isn't marked as a step that asks once")
        for sid in ("helper", "terminal", "lidsleep", "flows"):
            need(("test", sid) in states, f"the test round doesn't check {sid}")
        ws = hq / "workspace"
        made = sorted(str(p.relative_to(ws)) for p in ws.rglob("*") if ".git" not in p.parts)
        want = sorted(str(p.relative_to(hq / "template")) for p in (hq / "template").rglob("*"))
        need(made == want, "the workspace isn't a copy of the template")
        need(sp.run(["git", "-C", str(ws), "log", "--oneline"], capture_output=True).returncode == 0,
             "the new workspace isn't its own git repo")
        hu = d["heads_up"].lower()
        need("password" in hu and "allow" in hu and "once" in hu, "the heads-up doesn't name the password and Allow")
        need("password" in r.stdout.lower(), "the installer didn't tell the user about the password in Terminal")

        # An existing workspace is never touched.
        (ws / "me.md").write_text("their own words\n")
        digest = lambda: hashlib.md5(b"".join(p.read_bytes() for p in sorted(ws.rglob("*")) if p.is_file())).hexdigest()
        before = digest()
        r = sp.run(inst, env=env, capture_output=True, text=True, timeout=60, stdin=sp.DEVNULL)
        need(r.returncode == 0 and digest() == before, "a second run changed the existing workspace")
        need(next(x for x in load()["steps"] if x["id"] == "workspace")["state"] == "warn", "a kept workspace isn't said")

        # A step that fails stops the checklist there, says why and what to do.
        r = sp.run(inst, env=dict(env, HQ_INSTALL_FAIL="terminal"), capture_output=True, text=True, timeout=60, stdin=sp.DEVNULL)
        d = load()
        need(r.returncode != 0 and d["result"] == "failed", "a failed step didn't fail the run")
        bad = next(x for x in d["steps"] if x["phase"] == "setup" and x["id"] == "terminal")
        need(bad["state"] == "fail" and bad["detail"] and bad["fix"], "the failed step has no why or no fix")
        after = d["steps"][d["steps"].index(bad) + 1:]
        need(after and all(x["state"] == "not run" for x in after), "steps after the failure still ran")
        need("Stopped at" in r.stdout, "Terminal doesn't say where it stopped")

        # The page, live: served by the installer, and by the status page at /install.
        spec = importlib.util.spec_from_file_location("hq_install", hq / "install" / "install.py")
        os.environ["HQ_INSTALL_PORT"] = "4793"
        try:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        finally:
            os.environ.pop("HQ_INSTALL_PORT", None)
        srv = mod.serve_page()
        need(srv is not None, "the checklist page couldn't start")
        try:
            page = urllib.request.urlopen("http://127.0.0.1:4793/", timeout=5).read().decode()
            data = json.loads(urllib.request.urlopen("http://127.0.0.1:4793/install.json", timeout=5).read())
        finally:
            srv.shutdown()
        need("install.json" in page and "setInterval" in page and "To fix" in page, "the page doesn't poll the checklist or show the fix")
        need(data["result"] == "failed", "the page doesn't serve this run's checklist")
        server = (ROOT / "status" / "server.mjs").read_text()
        need("'/install'" in server and "checklist.json" in server, "the status page doesn't serve the checklist")
        text = (ROOT / "install" / "install.py").read_text() + (ROOT / "install" / "checklist.html").read_text()
        need(not privacy.scan_text(text, privacy.pattern(privacy.words(config.FOLDER))), "the installer has something of his in it")
        return "fresh install ticks both rounds; an existing workspace untouched; a failure stops with why and fix; page live"

    async def flow44(self) -> str:
        """M5: nothing personal in HQ itself, in its files or in its git history. No Claude turns."""
        private = privacy.words(config.FOLDER)
        pat = privacy.pattern(private)
        # The check itself catches what it should (made-up examples, never real ones).
        # Put together here, so this file doesn't trip its own check.
        for probe in ("/Users" + "/someone/HQ", "mac" + ".tail1a2b3c.ts.net", "100." + "101.102.103",
                      "someone" + "@mail.com", "sk-ant-" + "x" * 20, "ghp_" + "y" * 30,
                      "-----BEGIN " + "OPENSSH PRIVATE KEY-----"):
            need(privacy.scan_text(probe, pat), f"the privacy check misses {probe.split('@')[0][:12]}...")
        for fine in ("/Users/you/HQ/", "100.64.0.0/10", "127.0.0.1", "noreply@anthropic.com", "name@example.com"):
            need(not privacy.scan_text(fine, pat), f"the privacy check flags something harmless: {fine}")
        tree = await asyncio.to_thread(privacy.scan_tree, pat)
        need(not tree, f"HQ's files have something personal in them: {tree[:6]}")
        history = await asyncio.to_thread(privacy.scan_history, pat)
        need(not history, f"HQ's git history has something personal in it: {history[:6]}")
        return f"{len(privacy.files())} files and the history checked against {len(private)} private words and the general checks; nothing found"

    async def flow45(self) -> str:
        """H43: the scheduler. No Claude turns and no job is started: the schedule script on a copy of the
        roadmap (planning, the job list first, an item becoming a job, looking back, cancel and move), the
        routine asking it only when nothing runs or waits, the status page, and what a call may do."""
        import subprocess as sp
        from policy import Policy, ALLOW, DENY
        jv = ROOT
        rm = self.tmp / "roadmap-H43.md"
        rm.write_text(ROADMAP.read_text())
        env = {**os.environ, "JARVIS_ROADMAP": str(rm)}
        def run(script, *a, ok=True):
            r = sp.run(["python3", str(jv / "routine" / script), *a], capture_output=True, text=True, env=env)
            need((r.returncode == 0) == ok, f"{script} {' '.join(a)}: {r.stdout.strip()} {r.stderr.strip()}")
            return r.stdout + r.stderr
        sched = lambda *a, ok=True: run("schedule.py", *a, ok=ok)
        jobs = lambda *a, ok=True: run("jobs.py", *a, ok=ok)
        q = lambda: json.loads(jobs("next"))
        # Only the test's own jobs: finish whatever the copy has waiting or running.
        for j in q()["waiting"] + q()["running"]:
            jobs("mark", str(j["n"]), "done 00:00")
        later = sched("add", "tuesday 15:00", "flow 45 later")
        need("Tuesday" in later and "planned" in later, f"a weekday isn't understood: {later}")
        now = sched("add", "now", "flow 45 now", "--past-the-line")
        n_later, n_now = int(later.split()[1]), int(now.split()[1])
        sched("add", "2020-01-01 10:00", "too late", ok=False)
        sched("add", "friday 25:00", "no such time", ok=False)
        sched("add", "someday", "no day", ok=False)
        # The job list goes first: with a job waiting, a due item stays put.
        blocker = int(jobs("add", "flow 45 blocker").split()[1])
        need("Nothing to start" in sched("promote"), "a due item started while a job was waiting")
        st = json.loads(sched("status"))
        need(st["state"] == "ok" and f"Item {n_now} is due" in st["text"] and "job list goes first" in st["text"],
             f"the routine line doesn't say the due item waits for the job list: {st}")
        jobs("mark", str(blocker), "running since 00:01")
        need("Nothing to start" in sched("promote"), "a due item started while a job was running")
        jobs("done", str(blocker))
        # Switched off: nothing starts either.
        jobs("off")
        need("Nothing to start" in sched("promote"), "a due item started while the routine was off")
        jobs("on")
        # Empty and on: the due item becomes a job at the bottom of the queue, past the line as planned.
        did = sched("promote")
        need(f"item {n_now} became job" in did, f"the due item didn't become a job: {did}")
        job = q()["waiting"]
        need(len(job) == 1 and job[0]["past"] and f"Scheduled item {n_now}" in job[0]["text"] and "flow 45 now" in job[0]["text"],
             f"the job made from the item is wrong: {job}")
        jn = job[0]["n"]
        need("Nothing to start" in sched("promote"), "the same item started twice")
        # Looking back: the item takes over how its job finished.
        jobs("done", str(jn))
        sched("promote")
        lst = sched("list")
        need(f"job {jn} done" in lst and "Looking back" in lst, f"looking back doesn't say how it went: {lst}")
        # The later one: moved, then cancelled; a finished one can't be.
        need("Sunday" in sched("move", str(n_later), "sunday 10:00") or "Sunday" in sched("list"), "move didn't take")
        sched("cancel", str(n_now), ok=False)
        sched("cancel", str(n_later))
        need("Nothing planned." in sched("list"), "a cancelled item is still planned")
        need("add \"WHEN\"" in sched("--help") or 'add "WHEN"' in sched("--help"), "--help doesn't say how to plan")
        # The queue keeps working with the schedule under it, and the schedule survives the queue's writes.
        text = rm.read_text()
        need(text.count("## The schedule") == 1 and text.count("## The queue") == 1
             and text.index("## The queue") < text.index("## The schedule"), "the schedule isn't right under the queue")
        # The routine asks the scheduler only when nothing runs or waits.
        tick = (jv / "routine/tick.py").read_text()
        i_line, i_prom = tick.index("if not line:\n        # H43"), tick.index("did = schedule_promote()")
        need(i_line < i_prom < tick.index("job = line[0]"), "the routine asks the scheduler before the job list")
        need("schedule_line()" in tick, "the scheduler has no routine line")
        # The status page reads it and shows it, with its own routine line.
        js = f"""import {{ parseRoadmap }} from {json.dumps(str(jv / 'status/parse.mjs'))};
import {{ readFileSync }} from 'node:fs';
const r = parseRoadmap(readFileSync({json.dumps(str(rm))}, 'utf8'));
console.log(JSON.stringify({{problems: r.problems, items: r.schedule.items.map((i) => [i.n, i.state])}}));"""
        d = json.loads(sp.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True).stdout)
        need(not d["problems"] and [n_later, f"cancelled"] in [[n, s.split()[0]] for n, s in d["items"]], f"the status page reads the schedule wrong: {d}")
        page = (jv / "status/index.html").read_text()
        need("foldPart('schedule'" in page and "Looking back" in page and "['schedule', 'Scheduler'" in page,
             "the status page doesn't show the schedule")
        need("'schedule'" in (jv / "status/server.mjs").read_text(), "the routines graph doesn't keep the scheduler")
        # A call may plan, list, move and cancel; promoting is the routine's own.
        pol = Policy(config.FOLDER)
        s_ = f'python3 "{ROOT}/routine/schedule.py"'
        for sub in ('add "tuesday 15:00" "x"', "list", "cancel 3", 'move 3 "tomorrow 9:30"'):
            need(pol.decide("Bash", {"command": f"{s_} {sub}"}).verdict == ALLOW, f"a call can't {sub.split()[0]}")
        need(pol.decide("Bash", {"command": f"{s_} promote"}).verdict == DENY, "a call may promote an item")
        need("schedule.py" in config.VOICE_RULES and "job list always goes first" in config.VOICE_RULES,
             "the call rules don't say how to plan work")
        return "plans by day and time; waits while a job runs, waits or the routine is off; then becomes one job, past the line kept; looking back, move, cancel; page, routine line, call rules"

    async def flow46(self) -> str:
        """H27: the Mac desktop app. No Claude turns. The watchdog part on made-up routine lines, its turning-on
        plan with everything faked off, the strip in a headless browser, then the real app built and its window
        (never shown) loaded once with --selftest."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("hq_control_t", ROOT / "desktop/hq_control.py")
        hc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hc)
        now = time.time()

        def line(state="ok", text="fine", every=60, ago=10):
            return {"state": state, "text": text, "every": every, "at": now - ago, "last": now - ago}

        def lines(**over):
            base = {k: line() for k in ["helper", "mail", "jobs", "schedule", "usage", "phone", "call", "temp", "battery"]}
            base["watchdog"] = line(every=300, ago=60)
            base.update(over)
            return {"now": now, "routines": base}

        cases = [
            ("all fine", lines(), "ok", "happy", []),
            ("a job running", lines(jobs=line("running", "1 running")), "running", "happy", []),
            ("waiting on purpose", lines(jobs=line("waiting", "waiting for the usage line")), "waiting", "alert", []),
            ("the helper stopped", lines(helper=line(ago=600)), "down", "bark", ["helper"]),
            ("the call line down", lines(call=line("down", "Down: nothing answers")), "down", "bark", ["call"]),
            ("the laptop hot", lines(temp=line("down", "Hot: 95°C on the chip")), "down", "bark", []),
            ("the watchdog missing", {"now": now, "routines": {k: v for k, v in lines()["routines"].items() if k != "watchdog"}}, "down", "bark", ["watchdog"]),
        ]
        for name, data, light, mood, off in cases:
            j = hc.judge(data)
            need((j["light"], j["mood"], j["off"]) == (light, mood, off), f"{name}: got {j['light']}, {j['mood']}, {j['off']}")
        need(hc.judge(lines(temp=line("down", "Hot: 95°C")))["headline"] == "The laptop is hot", "a hot laptop isn't the headline")
        down = hc.judge(None)
        need((down["mood"], down["light"]) == ("sleep", "down") and down["off"] == ["status"], f"status page down: {down}")
        need([r["key"] for r in hc.judge(lines())["routines"]] == [k for k, _ in hc.ROUTINES], "the routines aren't in the status page's order")
        # The real routines right now: the same JSON the app reads.
        live = json.loads(run(["/usr/bin/python3", str(ROOT / "desktop/hq_control.py"), "health"]).stdout)
        need({"light", "mood", "headline", "routines", "off"} <= set(live), f"health misses fields: {sorted(live)}")
        # Turning on: with everything faked off, it starts each of the four; nothing it runs stops anything.
        orig = (hc.listening, hc.helper_pids, hc.watchdog_loaded, hc.os.path.isdir, hc.os.path.exists)
        try:
            hc.listening = lambda port: False
            hc.helper_pids = lambda: []
            hc.watchdog_loaded = lambda label: False
            hc.os.path.isdir = lambda p: True
            hc.os.path.exists = lambda p: True
            todo = hc.plan(None)
            hc.listening = lambda port: True
            hc.helper_pids = lambda: [1]
            hc.watchdog_loaded = lambda label: True
            nothing = hc.plan(lines())
        finally:
            hc.listening, hc.helper_pids, hc.watchdog_loaded, hc.os.path.isdir, hc.os.path.exists = orig
        need([k for k, _, _ in todo] == ["phone", "helper", "watchdog", "call"], f"the turning-on plan is wrong: {todo}")
        need(nothing == [], f"something is turned on while everything runs: {nothing}")
        cmds = " ".join(" ".join(c) for _, _, c in todo)
        need(not re.search(r"\b(kill|pkill|stop|unload|bootout|terminate)\b", cmds), f"turning on would stop something: {cmds}")
        need("--quiet" in cmds and "start.sh" in cmds and "open -g" in cmds, f"turning on isn't the usual start: {cmds}")
        src = (ROOT / "desktop/hq_control.py").read_text() + (ROOT / "desktop/HQ.swift").read_text()
        need(not re.search(r"pkill|killall|os\.kill|\.terminate\(\)", src), "the app or its watchdog part can stop processes")
        dry = json.loads(run(["/usr/bin/python3", str(ROOT / "desktop/hq_control.py"), "fix", "--dry"]).stdout)
        need(all(f.get("ok") is None for f in dry["fixed"]), "fix --dry did something")
        # The strip in a headless browser: each mood, the light, the tabs, the button only when something is off.
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the strip in")
        page = (ROOT / "desktop/shell.html").read_text()
        harness = r"""<script>
(() => {
  const out = [], one = (h) => { hq.update(h); const s = hq.state(); return `${s.mood}/${s.light}/${s.fix}`; };
  out.push('happy:' + one({ light: 'ok', mood: 'happy', headline: 'All working', off: [], routines: [] }));
  out.push('alert:' + one({ light: 'waiting', mood: 'alert', headline: 'All working', off: [], routines: [] }));
  out.push('bark:' + one({ light: 'down', mood: 'bark', headline: 'Not working: Call line', off: ['call'], routines: [{ name: 'Call line', state: 'down', text: 'Down' }] }));
  out.push('sleep:' + one({ light: 'down', mood: 'sleep', headline: 'The status page does not answer', off: ['status'], routines: [] }));
  document.getElementById('fix').click();
  out.push('fixing:' + hq.state().mood + '/' + hq.state().fix);
  hq.fixing(false, 'Started the call line');
  out.push('after:' + hq.state().mood + '/' + document.getElementById('said').textContent);
  document.getElementById('tab-call').click();
  out.push('tab:' + hq.state().tab);
  out.push('calldog:' + getComputedStyle(document.getElementById('dog')).display + '/' + getComputedStyle(document.getElementById('fix')).display);
  document.getElementById('tab-status').click();
  document.getElementById('dog').dispatchEvent(new MouseEvent('click', { bubbles: true }));
  out.push('panel:' + hq.state().open + '/' + document.querySelectorAll('#rows .row').length);
  out.push('anim:' + ['happy', 'alert', 'bark', 'run', 'sleep'].map((m) => { document.getElementById('dog').setAttribute('class', 'dog ' + m);
    return [...document.querySelectorAll('#dog *')].some((e) => getComputedStyle(e).animationName !== 'none') ? 1 : 0; }).join(''));
  const pre = document.createElement('pre'); pre.id = 'h27'; pre.textContent = 'H27RESULT ' + out.join(' | ') + ' END'; document.body.append(pre);
})();
</script>"""
        f = self.tmp / "h27-shell.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", f"--user-data-dir={self.tmp / 'h27-profile'}",
                                          "--virtual-time-budget=3000", "--dump-dom", f.as_uri()], timeout=60)
        m = re.search(r'<pre id="h27">H27RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the strip test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        res = dict(part.split(":", 1) for part in m.group(1).split(" | "))
        say(f"   {m.group(1)}")
        need(res["happy"] == "happy/ok/false" and res["alert"] == "alert/waiting/false", f"the calm moods are wrong: {res}")
        need(res["bark"] == "bark/down/true" and res["sleep"] == "sleep/down/true", f"the alarm moods are wrong: {res}")
        need(res["fixing"] == "run/false" and res["after"] == "sleep/Started the call line", f"turning on doesn't show: {res}")
        need(res["tab"] == "call" and res["panel"] == "true/0", f"the tabs or the dog's panel don't work: {res}")
        need(res["calldog"] == "none/none", f"the dog or Turn everything on still show on Call (H46): {res}")
        need(res["anim"] == "11111", f"not every mood moves: {res['anim']}")
        # The real app: built with swiftc, its own files found, its window (never shown) loads the strip and the status page.
        b = await asyncio.to_thread(run, [str(ROOT / "desktop/build.sh")], timeout=300)
        need(b.returncode == 0, f"the app didn't build: {(b.stderr or b.stdout)[-400:]}")
        app = ROOT / "scratch/desktop/HQ.app"
        plist = (app / "Contents/Info.plist").read_text()
        need("NSMicrophoneUsageDescription" in plist and f"<string>{ROOT}</string>" in plist, "the app's Info.plist misses the microphone or HQ's folder")
        need((app / "Contents/Resources/HQ.icns").exists(), "the app has no dog icon")
        chk = json.loads(run([str(app / "Contents/MacOS/HQ"), "--check"]).stdout)
        need(chk["shell"] and chk["control"] and chk["hq"] == str(ROOT), f"the app doesn't find its files: {chk}")
        st = await asyncio.to_thread(run, [str(app / "Contents/MacOS/HQ"), "--selftest"], timeout=60)
        need(st.returncode == 0 and st.stdout.strip().startswith("{"), f"the app's window didn't load: {(st.stdout + st.stderr)[-300:]}")
        got = json.loads(st.stdout.strip().splitlines()[-1])
        need(got["strip"]["mood"] in ("happy", "alert", "bark", "sleep") and got["strip"]["head"] not in ("", "Looking…"),
             f"the app's strip got no reading: {got['strip']}")
        if live["mood"] != "sleep":
            need(got["status_loaded"] and "Jarvis VA" in got["status_title"][0], f"the app didn't load the status page: {got}")
        swift = (ROOT / "desktop/HQ.swift").read_text()
        need("status.pageZoom = next" in swift and 'item("Smaller", #selector(zoomOut), "-"' in swift and 'id="zoom-in"' in page,
             "the status page can't be made bigger or smaller (H47)")
        need('var tab = "call"' in swift and "_setICECandidateFilteringEnabled:" in swift and "7860/?app=1" in swift,
             "the app doesn't open on Call, or its call page still hides the address (H46)")
        need('origin.host == "127.0.0.1"' in swift and "applicationShouldTerminateAfterLastWindowClosed" in swift,
             "the microphone isn't limited to this MacBook, or closing doesn't quit")
        return f"seven made-up states judged like the status page; turning on starts only what's off, stops nothing; the strip's five moods move; the app builds and its window read: {got['strip']['head']}"

    async def flow47(self) -> str:
        """H28: the phone version of the Mac app. No Claude turns. Its own status server on a test port, with
        Turn everything on set to say only what it would do."""
        import urllib.request, urllib.error
        port = 4797
        env = {**os.environ, "JARVIS_STATUS_PORT": str(port), "HQ_FIX_DRY": "1"}
        log = open(self.tmp / "h28-server.log", "w")
        srv = subprocess.Popen(["node", str(ROOT / "status/server.mjs"), "--quiet"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        base = f"http://127.0.0.1:{port}"

        def get(path, method="GET", headers=None):
            req = urllib.request.Request(base + path, method=method, headers=headers or {})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return r.status, r.headers.get("content-type", ""), r.read()
            except urllib.error.HTTPError as e:
                return e.code, "", e.read()
        try:
            for _ in range(50):
                try:
                    get("/hq.webmanifest")
                    break
                except Exception:
                    await asyncio.sleep(0.2)
            st, ct, body = await asyncio.to_thread(get, "/hq")
            page = body.decode()
            shell = (ROOT / "desktop/shell.html").read_text()
            need(st == 200 and "text/html" in ct, f"/hq didn't answer: {st}")
            need('id="dog"' in page and 'id="fix"' in page and 'id="tab-call"' in page, "/hq isn't the Mac app's strip")
            need('/hq/phone.js' in page and '/hq/phone.css' in page and 'apple-touch-icon' in page and '/hq.webmanifest' in page,
                 "/hq misses the phone's script, look, icon or manifest")
            need(page.count('name="viewport"') == 1 and "viewport-fit=cover" in page, "the phone page's viewport is wrong")
            need("webkit.messageHandlers.hq" in shell and "phone.js" not in shell, "the Mac app's strip was changed for the phone")
            for path, kind in [("/hq/phone.js", "javascript"), ("/hq/phone.css", "css"), ("/hq.webmanifest", "manifest"),
                               ("/hq-icon-180.png", "image/png"), ("/hq-icon-192.png", "image/png"), ("/hq-icon-512.png", "image/png")]:
                st, ct, body = await asyncio.to_thread(get, path)
                need(st == 200 and kind in ct and body, f"{path} didn't come: {st} {ct}")
            man = json.loads((await asyncio.to_thread(get, "/hq.webmanifest"))[2])
            need(man["start_url"] == "/hq" and man["name"] == "HQ" and man["display"] == "standalone", f"the manifest is wrong: {man}")
            # The dog's reading: the same JSON the Mac app reads.
            st, _, body = await asyncio.to_thread(get, "/hq.json")
            h = json.loads(body)
            need(st == 200 and {"light", "mood", "headline", "routines", "off"} <= set(h), f"/hq.json isn't the Mac app's reading: {st} {h}")
            # Turn everything on: only from the HQ page (a header no plain form can send); here it only says what it would do.
            need((await asyncio.to_thread(get, "/hq/fix", "POST"))[0] == 403, "/hq/fix answers a POST without the HQ header")
            need((await asyncio.to_thread(get, "/hq/fix", "GET", {"x-hq": "fix"}))[0] == 403, "/hq/fix answers a GET")
            st, _, body = await asyncio.to_thread(get, "/hq/fix", "POST", {"x-hq": "fix"})
            out = json.loads(body)
            need(st == 200 and all(f.get("ok") is None for f in out["fixed"]), f"/hq/fix did something in the test: {out}")
            js = (ROOT / "desktop/phone.js").read_text()
            need(":8443/" in js and "127.0.0.1:7860" in js and "location.port === '8444'" in js, "the call page's address isn't the call line's")
            need('microphone' in js, "the call frame may not use the microphone")
            need(not re.search(r"pkill|killall|process\.kill", js + (ROOT / "status/server.mjs").read_text()), "the phone version can stop processes")
            # At phone width in a headless browser: the strip, the status page below, Call loads the call page only when opened.
            cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
            chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            need(Path(chrome).exists(), "no headless browser found")
            harness = r"""<script>
window.addEventListener('load', () => setTimeout(() => {
  const out = [], f = window.hqPhone.frames();
  const callBefore = f.call.getAttribute('src') || 'none';
  out.push('status:' + f.status.getAttribute('src') + '/' + !f.status.hidden);
  out.push('callBefore:' + callBefore);
  out.push('head:' + document.getElementById('head').textContent);
  out.push('mood:' + hq.state().mood);
  document.getElementById('tab-call').click();
  out.push('call:' + f.call.getAttribute('src') + '/' + !f.call.hidden + '/' + f.status.hidden + '/' + hq.state().tab);
  document.getElementById('tab-status').click();
  out.push('back:' + !f.status.hidden + '/' + f.call.hidden);
  const bar = document.querySelector('.bar').getBoundingClientRect(), dog = document.getElementById('dog').getBoundingClientRect();
  const main = document.getElementById('frames').getBoundingClientRect();
  out.push('fits:' + (bar.width <= innerWidth) + '/' + (dog.left < 40) + '/' + (main.height > 300) + '/' + (document.documentElement.scrollWidth <= innerWidth));
  const pre = document.createElement('pre'); pre.id = 'h28'; pre.textContent = 'H28RESULT ' + out.join(' | ') + ' END'; document.body.append(pre);
}, 1500));
</script>"""
            # A copy of the page with the test harness, pointed at the test server (its <base>); web security is off
            # in this throwaway browser only, so the copy may read the test server's /hq.json.
            (self.tmp / "h28.html").write_text(page.replace("</body>", harness + "</body>", 1).replace("<head>", f'<head><base href="{base}/">', 1))
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", f"--user-data-dir={self.tmp / 'h28-profile'}",
                                              "--disable-web-security", "--window-size=390,844", "--virtual-time-budget=6000", "--dump-dom", (self.tmp / "h28.html").as_uri()], timeout=60)
            m = re.search(r'<pre id="h28">H28RESULT (.*?) END</pre>', r.stdout)
            need(m, f"the phone page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
            res = dict(part.split(":", 1) for part in m.group(1).split(" | "))
            say(f"   {m.group(1)}")
            need(res["status"] == "//true", f"the status page isn't under the strip: {res}")
            need(not res["head"].startswith("The Mac"), f"the strip got no reading: {res}")
            need(res["callBefore"] == "none", f"the call page loaded before Call was opened: {res}")
            need(res["call"] == "http://127.0.0.1:7860/?app=1/true/true/call", f"Call doesn't open the call page: {res}")
            need(res["back"] == "true/true", f"Status doesn't come back: {res}")
            need(res["fits"] == "true/true/true/true", f"the strip doesn't fit a phone: {res}")
            return f"/hq is the Mac app's strip with the phone's look, icon and manifest; the dog reads {h['mood']}; Turn everything on only from the page; at phone width: status below, Call loads only when opened"
        finally:
            srv.terminate()
            try:
                srv.wait(timeout=10)
            except Exception:
                pass
            log.close()

    # 48
    async def flow48(self) -> str:
        """H29: the agents. Pepper (Quick's load, Sonnet) and Donna (Deep's load, Opus) replace the Quick and
        Deep buttons; a workspace can change or add agents and give them headshots. No Claude turns."""
        import agents
        from pipeline import make_brain
        from policy import Policy

        # The defaults, and a page from before H29 still gets the right agent.
        every = agents.load(config.FOLDER)
        ids = [a["id"] for a in every]
        need(ids[:2] == ["donna", "pepper"], f"Donna and Pepper aren't the first two agents (H46: Donna left): {ids}")
        need(agents.find(config.FOLDER, None, "quick")["id"] == "donna" and agents.find(config.FOLDER, None, "deep")["id"] == "pepper",
             "a call with only Quick or Deep doesn't get Pepper or Donna")
        need(agents.find(config.FOLDER, "nobody", None)["id"] == "donna", "an unknown agent doesn't fall back to the first one")
        need(all(a["personality"] and a["speciality"] for a in every[:2]), "an agent has no personality or speciality")
        # A workspace's own agents: a change, a new one, a hidden one, a headshot; bad entries ignored.
        ws = self.tmp / "agents-ws"
        (ws / "Jarvis VA" / "agents").mkdir(parents=True)
        (ws / "Jarvis VA" / "agents" / "agents.json").write_text(json.dumps([
            {"id": "donna", "personality": "Test personality.", "model": "evil; rm"},
            {"id": "coach", "name": "Coach", "load": "deep", "speciality": "Life coaching"},
            {"id": "pepper", "hidden": True},
            {"id": "../x", "name": "Bad", "load": "quick"}, {"id": "noload", "name": "No load"}, "junk"]))
        (ws / "Jarvis VA" / "agents" / "coach.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        mine = agents.load(ws)
        need([a["id"] for a in mine] == ["donna", "pepper", "coach"], f"the workspace's agents aren't read right: {[a['id'] for a in mine]}")
        need([a["id"] for a in agents.visible(ws)] == ["donna", "coach"], "a hidden agent still shows")
        need(mine[0]["personality"] == "Test personality." and mine[0]["name"] == "Donna", "a workspace change isn't applied")
        need(agents.picture(ws, "coach") and not agents.picture(ws, "donna") and not agents.picture(ws, "../coach"),
             "headshots aren't found in the workspace only")
        svg = agents.picture_svg(mine[0])
        need(svg.startswith("<svg") and ">D</text>" in svg, "the placeholder headshot isn't drawn")
        # The sessions: her personality after the call rules, on her model and load.
        pol = Policy(config.FOLDER, dry_run=True)
        p_ = agents.find(config.FOLDER, "pepper"); d_ = agents.find(config.FOLDER, "donna")
        q = make_brain(config.MODEL_ALIASES[p_["model"]], pol, load=p_["load"], persona=agents.persona(p_, config.USER))._options
        d = make_brain(config.MODEL_ALIASES[d_["model"]], pol, load=d_["load"], persona=agents.persona(d_, config.USER))._options
        need("You are Pepper" in q.system_prompt["append"] and "This is a Quick call" not in q.system_prompt["append"]
             and q.model == config.MODEL_ALIASES["opus"], "Pepper's session isn't Deep's load on Opus with her personality (H46)")
        need("You are Donna" in d.system_prompt["append"] and "This is a Quick call" in d.system_prompt["append"]
             and d.model == config.MODEL_ALIASES["sonnet"], "Donna's session isn't Quick's load on Sonnet with her personality (H46)")
        need(d.system_prompt["append"].index("# This chat is a live voice call") < d.system_prompt["append"].index("You are Donna"),
             "her personality doesn't come after the call rules")
        need("Pepper" in config.WHISPER_PROMPT and "Donna" in config.WHISPER_PROMPT, "speech recognition doesn't know the agents' names")
        # The test server: the list for the page (no personality text), the headshots, the page itself.
        await self.ensure_server()
        code, body, ctype = http_get("/api/agents")
        listed = json.loads(body or b"{}").get("agents", [])
        need(code == 200 and [a["id"] for a in listed][:2] == ["donna", "pepper"], f"/api/agents is wrong: {code} {body[:120]!r}")
        need(all("personality" not in a and a["picture"] == f"/agents/{a['id']}/picture" for a in listed), "/api/agents gives too much or no picture")
        for a in listed:
            code, body, ctype = http_get(a["picture"])
            need(code == 200 and ctype.startswith("image/") and body, f"{a['name']}'s headshot doesn't load: {code} {ctype}")
        need(http_get("/agents/nobody/picture")[0] == 404, "an unknown agent's picture doesn't say not found")
        code, body, _ = http_get("/")
        page = body.decode()
        need('data-agent="pepper"' in page and 'data-agent="donna"' in page and "/api/agents" in page and "request_data: { mode, agent," in page,
             "the call page doesn't show the agents or doesn't send which one")
        need(">Quick<" not in page and ">Deep<" not in page, "the Quick and Deep buttons are still there")
        # The transcript names her.
        from transcript import CallTranscript
        t = CallTranscript(self.tmp / "calls48", model=config.MODEL_ALIASES["opus"], agent="Donna")
        need("agent Donna · brain" in t.path.read_text(), "the transcript doesn't say which agent")
        src = (ROOT / "app/call.py").read_text() + (ROOT / "app/bot.py").read_text()
        need("agents.find(config.FOLDER, agent, self.load)" in src and 'agent=agent["id"]' in src, "the call doesn't take the agent the page sent")
        return f"Donna (Quick, Sonnet) left and Pepper (Deep, Opus) right; a workspace's own agents and headshots; {len(listed)} on the page with their pictures"

    # 49
    async def flow49(self) -> str:
        """H29: she knows who she is. One Claude turn on a plain session with Pepper's personality."""
        import agents
        from pipeline import make_brain

        p_ = agents.find(config.FOLDER, "pepper")
        folder = self.tmp / "agent49"
        folder.mkdir()
        b = make_brain(config.MODEL_ALIASES[p_["model"]], None, cwd=folder, free=True, persona=agents.persona(p_, config.USER))
        await b.start()
        try:
            out = ""
            async for part in b.ask("Quick test: what's your name? Just the name."):
                if isinstance(part, str):
                    out += part
        finally:
            await b.stop()
        self.turns += 1
        need("pepper" in out.lower(), f"she didn't say she's Pepper: {out!r}")
        return f"asked her name, she said {out.strip()[:40]!r}"

    # 50
    async def flow50(self) -> str:
        """H46: the call page's own changes. No Claude turns. Donna left, Pepper right; a voice each in Settings
        ("Voice Donna Paulsen", "Voice Pepper Potts"), remembered per agent and sent with the call; no waiting
        lines; inside the app (?app) no status button. The server always turns the waiting lines off."""
        await self.ensure_server()
        code, body, _ = http_get("/")
        page = body.decode()
        need(code == 200 and 'id="lines"' not in page and "waitingLines" not in page and "waiting_lines" not in page,
             "the waiting lines are still on the call page")
        need(page.index('data-agent="donna"') < page.index('data-agent="pepper"'), "Pepper is still left of Donna")
        src = (ROOT / "app/bot.py").read_text()
        need("waiting_lines = False" in src, "the server still lets a page turn the waiting lines on")
        # The app's calls (WebKit offers only Wi-Fi addresses): the call line answers this MacBook on its own
        # addresses too, a phone still only on Tailscale, and a hidden address (name.local) counts as not here.
        import bot
        mine = sorted(a for a in bot.own_addresses() if ":" not in a and not a.startswith("100."))
        need(mine, "this MacBook has no Wi-Fi address to test with")
        offer = lambda addr: json.dumps({"sdp": f"v=0\r\na=candidate:1 1 udp 2113937151 {addr} 50000 typ host generation 0\r\n"}).encode()
        need(bot.offer_from_this_mac(offer(mine[0])), "a call from this MacBook isn't recognised")
        need(not bot.offer_from_this_mac(offer("203.0.113.5")) and not bot.offer_from_this_mac(offer("1a2b.local"))
             and not bot.offer_from_this_mac(b"junk"), "a call from elsewhere counts as this MacBook")
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        harness = r"""<script>
setTimeout(() => {
  const out = [];
  out.push('order:' + [...document.querySelectorAll('#modes button')].map(b => b.dataset.agent).join(','));
  out.push('voices:' + [...document.querySelectorAll('#voices .row span')].map(s => s.textContent).join(','));
  const sel = document.querySelector('#voices select[data-agent="pepper"]');
  sel.value = 'bf_emma'; sel.dispatchEvent(new Event('change'));
  out.push('sent:' + voiceFor('pepper') + '/' + voiceFor('donna'));
  out.push('inapp:' + getComputedStyle(document.getElementById('statbtn')).display);
  const pre = document.createElement('pre'); pre.id = 'h46'; pre.textContent = 'H46RESULT ' + out.join(' | ') + ' END'; document.body.append(pre);
}, 1500);
</script>"""
        f = self.tmp / "h46.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1).replace("<head>", f'<head><base href="{TEST_URL.rstrip("/")}/">', 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", f"--user-data-dir={self.tmp / 'h46-profile'}",
                                          "--disable-web-security", "--virtual-time-budget=5000", "--dump-dom", f.as_uri() + "?app=1"], timeout=60)
        m = re.search(r'<pre id="h46">H46RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the call page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        res = dict(part.split(":", 1) for part in m.group(1).split(" | "))
        say(f"   {m.group(1)}")
        need(res["order"].startswith("donna,pepper"), f"the agents aren't Donna then Pepper: {res}")
        need(res["voices"].startswith("Voice Donna Paulsen,Voice Pepper Potts"), f"Settings doesn't have a voice for each: {res}")
        need(res["sent"] == "bf_emma/af_heart", f"Pepper's voice isn't her own: {res}")
        need(res["inapp"] == "none", f"the status button still shows inside the app: {res}")
        return "Donna left, Pepper right; Voice Donna Paulsen and Voice Pepper Potts, each her own; no waiting lines; no status button inside the app"

FLOWS = {
    1: ("The call server starts and the page loads", False, "flow1"),
    2: ("The greeting plays first, on Quick and Deep", True, "flow2"),
    3: ("A plain question gets a spoken answer", True, "flow3"),
    4: ("A calendar question: waiting line, answer, read-only", True, "flow4"),
    5: ("Something that needs a yes: asked, and a no does nothing", True, "flow5"),
    6: ("Cutting in stops her voice", True, "flow6"),
    7: ("Hanging up saves the transcript, git unchanged", True, "flow7"),
    8: ("The waiting lines: no Mm, no repeats", False, "flow8"),
    9: ("A restart really restarts", False, "flow9"),
    10: ("The status page reads the roadmap; weekly lines move", False, "flow10"),
    11: ("Free mode: plain Claude with internet, chat log, nothing kept", True, "flow11"),
    12: ("Holding the talk button keeps the turn through a long pause", True, "flow12"),
    13: ("Letting go keeps the last words; the page shows transcribing", True, "flow13"),
    14: ("Free talking: a short pause doesn't split the sentence", True, "flow14"),
    15: ("Quick loads part of his folder, Deep everything", False, "flow15"),
    16: ("Open loops: the mail check and every start read one shape", False, "flow16"),
    17: ("Open loops: a call names a very important item first thing", True, "flow17"),
    18: ("The queue: jobs from calls, stop, gate, what a call may do", False, "flow18"),
    19: ("The status page on the phone, and the status button", False, "flow19"),
    20: ("The usage check: no Claude, every minute, what a call may do", False, "flow20"),
    21: ("The usage check shows the latest saved usage and its age", False, "flow21"),
    22: ("Typing to Jarvis on a call: she answers out loud, chat gets both", True, "flow22"),
    23: ("A buzz on push to talk; Hang up asks Are you sure?", False, "flow23"),
    24: ("Cancel while she thinks: no answer, line marked cancelled", True, "flow24"),
    25: ("Routines respond: missed runs caught up, incidents logged, commits locked", False, "flow25"),
    26: ("A low sound when push to talk switches on", False, "flow26"),
    27: ("The talk button stays green the whole time it is held", False, "flow27"),
    28: ("Jobs in the routines graph, in the development colours", False, "flow28"),
    29: ("Chat and status buttons always there; the last call before one", False, "flow29"),
    30: ("The laptop's temperature: no password, ranges, graph, red when hot", False, "flow30"),
    31: ("The laptop's battery: percentage, charging, ranges, graph, red when low", False, "flow31"),
    32: ("Cancel stays; a late tap asks, then sends Cancel last message", True, "flow32"),
    33: ("A quiet job gets continue typed into its own window; stuck shows", False, "flow33"),
    34: ("The queue runs in list order; a call can move waiting jobs", False, "flow34"),
    35: ("A mute button for her voice; the chat still gets her lines", False, "flow35"),
    36: ("Typing to Jarvis: the text field grows; Enter on phone and computer", False, "flow36"),
    37: ("A failed routine run says why; the watchdog sees one that keeps failing", False, "flow37"),
    38: ("More laptop stats folded in under Laptop: CPU, GPU, memory, disk, network", False, "flow38"),
    39: ("The lid-closed sleep switch: read, flipped from a call, shown under Laptop", False, "flow39"),
    40: ("Past the line skips only the 5-hour line; the weekly line always holds", False, "flow40"),
    41: ("The clean template: blank, nothing of his, readable as a workspace", False, "flow41"),
    42: ("The explanations: the readme and the big picture, nothing of his", False, "flow42"),
    43: ("The installer: fresh, kept workspace, a failure, the live checklist", False, "flow43"),
    44: ("Nothing personal in HQ: its files and its git history", False, "flow44"),
    45: ("The scheduler: planned work, after the job list, looking back", False, "flow45"),
    46: ("The Mac desktop app: the watchdog dog, status and call in one", False, "flow46"),
    47: ("The phone version of the Mac app: the same strip, status and call", False, "flow47"),
    48: ("The agents: Pepper and Donna replace Quick and Deep, with headshots", False, "flow48"),
    49: ("An agent knows who she is: Pepper says her name", True, "flow49"),
    50: ("H46: Donna left, Pepper right, a voice each, no waiting lines, no status button in the app", False, "flow50"),
}


async def main(args) -> bool:
    chosen = sorted(int(x) for x in args.only.split(",")) if args.only else sorted(FLOWS)
    bad = [n for n in chosen if n not in FLOWS]
    if bad:
        print(f"No such flow: {bad}. The flows are 1 to {len(FLOWS)}.")
        return False
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"== Jarvis VA happy flows · {stamp} · flows {chosen}" + (" · quick (no Claude turns)" if args.quick else ""))
    tmp = Path(tempfile.mkdtemp(prefix="happy-flows-", dir=config.SCRATCH))
    run_ = Run(tmp)
    # Flow 7 closes the live call; if it runs, it must come after the others that use that call.
    results: list[Result] = []
    t_all = time.perf_counter()
    try:
        for n in chosen:
            name, uses_claude, method = FLOWS[n]
            res = Result(n, name)
            results.append(res)
            if args.quick and uses_claude:
                res.note = "skipped (--quick)"
                continue
            print(f"\n-- {n} · {name}", flush=True)
            t = time.perf_counter()
            try:
                res.note = await asyncio.wait_for(getattr(run_, method)(), timeout=360)
                res.status = "PASS"
            except Failed as e:
                res.status, res.note = "FAIL", str(e)
            except asyncio.TimeoutError as e:  # a wait inside the flow, or the six-minute limit
                res.status, res.note = "FAIL", str(e) or "took longer than six minutes"
            except Exception as e:  # a crash in a flow is a failed flow, not a failed run
                res.status, res.note = "FAIL", f"{type(e).__name__}: {e}"
            res.secs = time.perf_counter() - t
            say(f"{res.status}: {res.note}")
    finally:
        try:
            if run_.live:
                await run_.live.close()
        except Exception as e:
            print(f"(closing the live test call: {e!r})")
        if listening_pids(TEST_PORT):
            await asyncio.to_thread(run_.server.stop)
        live_after = (listening_pids(config.PORT) or [None])[0]
        turns = run_.turns + (run_.live.turns_used if run_.live else 0)
        if not args.keep:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n== Result")
    for r in results:
        print(f" {r.num:>2}  {r.name:<58} {r.status:<5} {r.secs:5.0f} s" if r.status != "SKIP"
              else f" {r.num:>2}  {r.name:<58} SKIP")
    ran = [r for r in results if r.status != "SKIP"]
    failed = [r for r in ran if r.status == "FAIL"]
    for r in results:
        print(f"      {r.num:>2}: {r.note}" if r.status != "FAIL" else f"      {r.num:>2}: FAILED - {r.note}")
    guard = "live server on 7860 untouched" if live_after == run_.live_pid_before else \
        f"WARNING: the live server's pid changed ({run_.live_pid_before} -> {live_after})"
    print(f"\n{len(ran) - len(failed)} of {len(ran)} passed · {turns} Claude turns · {time.perf_counter() - t_all:.0f} s · {guard}")
    return not failed and live_after == run_.live_pid_before


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Jarvis VA happy flows (phase G)")
    p.add_argument("--only", default="", help="comma-separated flow numbers, e.g. 3,5")
    p.add_argument("--quick", action="store_true", help="skip the flows that use Claude turns (2-7)")
    p.add_argument("--keep", action="store_true", help="keep the scratch folder")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args()
    if a.verbose:
        from loguru import logger
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        from loguru import logger
        logger.remove()
        logger.add(sys.stderr, level="WARNING")
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(1))
    sys.exit(0 if asyncio.run(main(a)) else 1)
