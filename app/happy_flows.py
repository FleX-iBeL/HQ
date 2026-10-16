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
  22 typing to HQ during a call (H18): the call page has a text box in the chat while on a call
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
     H115: on a call the chat's top line is only who's on it: one name, both, or all of them
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
  35 a mute button for her voice (H40): on the call page (headless browser) a button in the dock, before
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
     the strip and the status page; the strip's empty top bar moves the window, its buttons don't (F15)
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
  51 H51, no Claude: a call's session saves the usage it gets back (the rate limit event) to the same file and
     shape as the mail check, marked as from a call; it never reaches a turn; a broken one doesn't stop the
     call; the usage check puts it on the status page as "from a call"; a Free call's brain does the same
  52 H49, no Claude: in the desktop app (?app) the space bar is the talk button: a short press mutes and
     unmutes, held down it's push to talk, letting go sends; not before a call, not while typing in the text
     box, not inside the Hang up question; in the browser and on the phone space does nothing
  53 H57, no Claude: every past call. The transcript code lists the saved calls newest first with date, time
     and agent (calls without anything said left out), reads one by name and refuses any other name; the call
     server serves both read only; on the call page (headless browser) the button sits in the dock before the voice
     button, before, during and after a call, in the browser and in the app; the list opens, a tap shows that
     call (no tools, cancelled struck through), Back returns, Close closes; one sheet at a time
  58 H60, one Claude turn: continue an earlier call. What the new call gets of the earlier one (his and her
     lines, trimmed from the start), the continue greeting with the name from me.md, never on Free; on the
     call page Continue at the foot of an opened call, only when not on a call and not as Free, the offer it
     sends and the chat it starts with; a real continued call greets so, and its transcript says which call
  71 H87, no Claude: the 5-hour stop line moves 10% every half hour after a reset, up to 100% in the last,
     or stays at a fixed number: the line on made-up readings, the roadmap's setting (moving by default), the
     switch script and the status server's switch on copies, what a call may run, the call rules
  72 H83, no Claude: which HQ this is (the label, else Local and the system) in Python and the status server,
     on the status page, /where.json and the strip's reading, with and without a label; the call page's line
     takes no room
  82 H104 and H108, no Claude: times as "5 30 in the afternoon". Quick and Deep are told to write 12-hour
     digits with a space, then the part of the day, never a colon, words, half, quarter or o'clock; no example
     in the call rules says a time another way; the speech filter says a stray 5:30 as "5 30"; Kokoro reads
     "5 30" as five thirty with no pause (when the model is there)
  83 H105, no Claude: the notes button. Notes kept one line each in a throwaway notes file (a line a call
     wrote by hand read too), cleared one by one or all, just text since H117 (no doodle endpoints, a picture
     saved before left alone); /api/notes only from the page; the real call page in a headless browser, phone
     and app: the button in the dock before Past calls before, during and after a call, the sheet without paper, the
     note field growing with what's typed and back after Add, add, clear, clear all on a second tap
  91 H101, no Claude: the calendar. A stand-in for the read-only Claude run (only list_calendars and
     list_events allowed, everything that writes refused): the tool results read from its stream, word for
     word (an answer too big for the chat read from Claude Code's own file, nothing outside it), cancelled
     ones left out, the main calendar called Main, a failed read keeping the last days; hourly in the day only,
     again on opening after a quarter of an hour; /api/calendar on the test server's own copy, ?fresh=1
     reading again; the call's note, greeting and transcript line; the real call page in a headless
     browser, phone and app: the round button on the right before and after a call (gone on a call), the
     days, a tap on one, Back, a swipe right back to the days (H147), "Call about this" sending the appointment, off on Free, one sheet at a time
  73 H92, no Claude: no laptop on a server. The status page in a headless browser, served as a server
     (HQ_LAPTOP=0) and as the laptop (HQ_LAPTOP=1), with a hot laptop and a low battery: on a server no Laptop
     section, no battery in the top line, no laptop lines or bars under Routines, and the Routines light green;
     on the laptop all of it as before, the light red
  64 F16, no Claude: the call page fits the screen. The real call page (with Moneypenny's card) in a headless
     browser at iPhone 13 sizes (Safari and the home screen), a small phone, and the desktop app's size (?app):
     on a call the old layout stays (the picker and her card keep their room) and the page can't be scrolled
     into white space, and after Past calls is opened and closed it's back where it was (F20); a screen too short
     for the status line still scrolls; nothing scrolls before or after
  69 H76 and H77, no Claude: each agent her own character. Donna, Pepper and Moneypenny in HQ's defaults with the
     agreed greeting first and push-back line, nothing personal, the name from me.md filled in; her character and
     the human rules after the call rules, no talk while thinking; a call greets in her words; a workspace's own
     character (agents.json) wins and is marked as its own; /api/agents, Settings and the readme show the defaults;
     H131: no agent says "honestly", and Pepper's character has no one-liners
  75 F18, no Claude: the status page never gets wider than the phone. A copy of the status page in a headless
     browser at phone widths (iPhone 13, a small phone), with a job and a roadmap note holding a long path and a
     key that can't be broken at a space, every fold open: nothing sticks out sideways and the page can't be
     swiped sideways; the redraw only scrolls the page back when it moved

Safe to run while the live phone line is up: the flows use their own server on port 7871
(HQ_NO_PHONE=1, so Tailscale serve is never touched), calls in test mode (no file
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
    p = site / "workspace" / "HQ" / "roadmap.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
TEST_PORT = int(os.environ.get("HQ_TEST_PORT", "7871"))
TEST_URL = f"http://127.0.0.1:{TEST_PORT}"
GREETING_WITHIN_SECS = 15.0  # from "connected" to the first sound
FIRST_AUDIO_WITHIN_SECS = 15.0  # a plain question: the user stops talking -> first sound (seen: 4 to 7 s)

Q_PLAIN = "Hey there, what's a good way to start a quiet morning? Keep it short."
Q_CALENDAR = "Hey there, what's on my calendar tomorrow?"
A_NO = "No, don't."
Q_HELLO = "Hey there, say hello to me in four words."
Q_FREE = "Hey there, what is the capital of France? Answer in one short sentence."
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
    serve is switched off for these scripts (HQ_NO_PHONE), and log and pid file are apart."""

    def __init__(self, tmp: Path):
        assert TEST_PORT != config.PORT, "the test server must not use the live port"
        self.tmp = tmp
        self.log = tmp / "server.log"
        self.pidfile = tmp / "server.pid"
        self.calls = tmp / "calls-server"
        self.notes = tmp / "notes-server" / "notes.md"  # H105: never the workspace's own notes
        self.env = {
            **os.environ,
            "HQ_PORT": str(TEST_PORT), "HQ_NO_PHONE": "1", "HQ_WRAP_UP": "dry",
            "HQ_CALLS": str(self.calls), "HQ_LOG": str(self.log), "HQ_PID_FILE": str(self.pidfile),
            "HQ_NOTES": str(self.notes),
            # H101: never the workspace's own calendar copy, and never a real Claude run to read Google
            "HQ_CALENDAR_FILE": str(tmp / "calendar-server" / "calendar.json"),
            "HQ_CALENDAR_FAKE": str(tmp / "calendar-server" / "stream.txt"),
            # H124: never the workspace's own pings or her notes
            "HQ_DIRECT_DIR": str(tmp / "direct-server"), "HQ_AGENT_NOTES": str(tmp / "direct-server" / "notes-donna.md"),
            # H143: an X never reaches Google from a test
            "HQ_PLANNING_FAKE": str(tmp / "planning-server"),
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
        return run([str(APP / ("start-linux.sh" if sys.platform.startswith("linux") else "start.sh"))], env=self.env, timeout=120)

    def stop(self, path_prefix: str | None = None) -> subprocess.CompletedProcess:
        env = dict(self.env)
        if path_prefix:
            env["PATH"] = path_prefix + os.pathsep + env["PATH"]
        return run([str(APP / ("stop-linux.sh" if sys.platform.startswith("linux") else "stop.sh"))], env=env, timeout=120)

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
        say(f"   She said: {r['reply']!r}")
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
        need(code == 200 and "<title>HQ</title>" in page, f"the call page did not load ({code})")
        need('data-mode="quick"' in page and 'data-mode="deep"' in page, "the Quick and Deep buttons are missing")
        need('id="btn"' in page and 'id="mute"' in page, "the call button or the mute button is missing")
        need('id="orb"' in page and 'id="sound"' in page and "pointerdown" in page,
             "the thinking animation, the thinking sound switch or push to talk is missing (H3-H5)")
        need('id="chatbtn"' in page and 'id="chatlog"' in page and "hq-chat" in page,
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
            if isinstance(m, dict) and m.get("type") == "hq-state":
                states.append(m.get("state"))
            elif isinstance(m, dict) and m.get("type") == "hq-chat":
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
        import agents  # H76: each agent greets in her own words
        all_greetings = {g for part in config.GREETINGS.values() for g in part} | {
            g for a in agents.load(config.FOLDER) for part in agents.PARTS for g in agents.greetings(a, config.ME["name"] or None, part)}
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
        say(f"   turns {len(llm.turns) - n}, heard {heard!r}, she said {reply!r}")
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
        say(f"   turns {turns}, heard {heard!r}, she said {reply!r}; page told: {seen}")
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
        say(f"   turns {turns}, heard {heard!r}, she said {reply!r}; page told: {seen}")
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
        # H78: his own calendar entries go without asking now; one with someone else invited still needs a yes.
        r1 = await live.ask(f"Please put a new event in my calendar on {day} at noon, called test call, "
                            "and invite test at example dot com.", "needs a yes")
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
        need(f"**{config.USER_LABEL}:**" in text and "**HQ:**" in text and "Ended" in text, "the transcript misses his words, hers or the end")
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
const L = r.usageLines ?? {{}};
const mv = {{ ...L, weekly: {{ moving: true, fixed: 90 }} }};
const at = (ms) => stopLine(week, mv, new Date(reset.getTime() - ms)).line;
const DAY = 864e5;
const steps = Array.from({{ length: 29 }}, (_, i) => at(7 * DAY - 6e4 - i * 6 * 36e5));
console.log(JSON.stringify({{
  problems: r.problems, state: r.state, usageLimit: r.usageLimit, weeklyLimit: r.weeklyLimit,
  phases: r.phases.map((p) => p.id), start: at(7 * DAY - 6e4), mid: at(3.5 * DAY), end: at(3e4),
  five: stopLine({{ label: '5-hour limit', resetsAt: reset.toISOString() }}, {{ ...mv, five: {{ moving: false, fixed: r.usageLimit }} }}).line,
  lines: Object.keys(L).sort().join(','),
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
        need(d["five"] == 70, f"the fixed 5-hour line moved: {d['five']}")
        need(d["lines"] == "fable,five,weekly", f"the roadmap's three stop lines aren't read: {d['lines']}")
        need(d["start"] == 20, f"a weekly line starts at {d['start']}, not 20")
        need(d["end"] == 100, f"a weekly line ends at {d['end']}, not 100")
        need(45 <= d["mid"] <= 60, f"a weekly line halfway is {d['mid']}")
        need(d["rising"] and d["distinct"] > 20, "the weekly line does not rise through the week")
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
            if isinstance(m, dict) and m.get("type") == "hq-chat":
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
            while not any(w == "hq" and not t.endswith("(cut off)") for w, t in chats) and time.perf_counter() - t0 < 60:
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
        hers = [t for w, t in chats if w == "hq"]
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
        need('message.get("type") == "typed"' in bot_src and "type_to_agent(worker, call.llm, call_state" in bot_src,
             "the call server doesn't pass a typed message on to HQ")

        from pipeline import type_to_agent

        live = await self.get_live()
        llm = live.llm
        lines: list[tuple[str, str]] = []
        live.call.transcript.on_line = lambda who, text: lines.append((who, text))
        need(not await type_to_agent(live.worker, llm, live.call_state, "   "), "an empty message was sent on")
        n = len(llm.turns)
        say(f"typing: {Q_TYPED}")
        t0 = time.perf_counter()
        need(await type_to_agent(live.worker, llm, live.call_state, Q_TYPED), "the typed message was refused")
        await live.wait_for(lambda: len(llm.turns) > n and not llm._replying, 90, "Claude's reply to the typed message")
        await live.wait_for(lambda: not live.call.fillers.talking
                            and live.after_tts.first("tts_stopped", t0)[0] is not None, 30, "the voice to finish")
        await asyncio.sleep(0.5)
        turn = llm.turns[n]
        t_aud, _ = live.after_tts.first("audio", t0)
        reply = " ".join(t["reply"].strip() for t in llm.turns[n:]).strip()
        say(f"   She said: {reply!r}; first sound {(t_aud - t0) if t_aud else float('nan'):.1f} s after sending")
        need(turn["words"] == Q_TYPED, f"the turn didn't get his typed words: {turn['words']!r}")
        need("typed this in the chat" in turn["sent"], "Claude wasn't told the message was typed")
        need("rome" in norm(reply), f"no answer, or a wrong one: {reply!r}")
        need(t_aud is not None, "she didn't answer out loud")
        need(("user", Q_TYPED) in lines and any(w == "hq" and "rome" in norm(t) for w, t in lines),
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
        sys.path.insert(0, str(ROOT / "routine"))
        import log_cycle
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
        # The log: open commitments and only the recent entries (K1, H100: three hours; off: two days).
        log = (folder / "coaching/log.md").read_text()
        heads = re.findall(r"^## \d{4}-\d{2}-\d{2}.*$", log, re.M)
        need("## Open commitments" in text, "Quick is missing the log's open commitments")
        if config.LIGHT_NOTES:
            cut = _dt.datetime.now() - _dt.timedelta(hours=quick_context.LOG_HOURS, minutes=1)
            old = [h for h in heads if log_cycle.when(h) < cut]
            fresh = [h for h in heads if log_cycle.when(h) >= cut + _dt.timedelta(minutes=2)]
            need(all(h in text for h in fresh), "Quick is missing log entries of the last three hours")
        else:
            first = _dt.date.today() - _dt.timedelta(days=quick_context.LOG_DAYS - 1)
            old = [h for h in heads if log_cycle.when(h).date() < first]
        need(not any(f"\n{h}\n" in text for h in old), "Quick has log entries older than it should")
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
        # The call page: the chat and status buttons in the dock, the page inside the app.
        page = (jv / "app/web/index.html").read_text()
        need('id="statbtn"' in page and 'id="statsheet"' in page and 'id="statframe"' in page,
             "the status button or its sheet is missing on the call page")
        # H140: both round buttons sit in the dock at the bottom, the chat before the status button.
        dock = page.split('<nav id="dock"', 1)[1].split("</nav>", 1)[0]
        need('id="chatbtn"' in dock and 'id="statbtn"' in dock and dock.index('id="chatbtn"') < dock.index('id="statbtn"'),
             "the chat and status buttons aren't in the dock, the chat first")
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
        env = {**os.environ, "HQ_ROADMAP": str(rm)}
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
        # Until it's rebuilt under its new name (H54, M9), the helper from before still runs the routine.
        app = next((a for a in (Path.home() / "Applications/HQ Routine.app", Path.home() / "Applications/Jarvis Routine.app")
                    if a.exists()), Path.home() / "Applications/HQ Routine.app")
        need(app.exists(), "the HQ Routine helper app isn't built")
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
        need("usage-check.command" not in tick,
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
            for f in ("routine/usage-check.py", "routine/hqpaths.py", "routine/stream-usage.py", "routine/usagelive.py", "status/save-usage.mjs",
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
        need(z("#hangask") > max(z("#chat"), z("#statsheet"), z("#dock"), z("#settings")),  # H140: the round buttons sit in the dock
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
        need('m.type === "hq-cancellable") showCancel(m.on === true)' in page,
             "Cancel isn't tied to the server saying it can still be taken back")
        tap = page.split("function sendCancel() {", 1)[1].split("\n}", 1)[0]  # H38: the tap goes through sendCancel
        need('type: "cancel"' in tap and 'showOrb("listening")' in tap,
             "a tap on Cancel doesn't send it, or the thinking circle and tick don't stop at once")
        need('m.type === "hq-cancelled") markCancelled()' in page and ".me.cancelled" in page,
             "the chat doesn't mark his line as cancelled")
        bot_src = (APP / "bot.py").read_text()
        need('message.get("type") == "cancel"' in bot_src and "cancel_turn(ptt.user_aggregator, call.llm, call_state)" in bot_src
             and "call.llm.on_cancellable = cancellable" in bot_src, "the call server doesn't handle Cancel")

        from pipeline import cancel_turn, type_to_agent

        live = await self.get_live()
        llm = live.llm
        agg = live.ptt.user_aggregator
        need(not await cancel_turn(agg, llm, live.call_state), "Cancel did something with nothing to cancel")
        flags: list[bool] = []
        llm.on_cancellable = flags.append
        n = len(llm.turns)
        say(f"typing, then cancelling: {Q_CANCEL}")
        need(await type_to_agent(live.worker, llm, live.call_state, Q_CANCEL), "the typed message was refused")
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
        need(await type_to_agent(live.worker, llm, live.call_state, Q_AFTER_CANCEL), "the second message was refused")
        await live.wait_for(lambda: len(llm.turns) > m and not llm._replying, 90, "Claude's reply to the second question")
        await live.wait_for(lambda: not live.call.fillers.talking
                            and live.after_tts.first("tts_stopped", t1)[0] is not None, 30, "the voice to finish")
        nxt = llm.turns[m]
        reply = " ".join(t["reply"].strip() for t in llm.turns[m:]).strip()
        say(f"   She said: {reply!r}")
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
        # H148: every 15 minutes in its test window, on the quarter; hourly before and after it, by itself.
        f0, f1 = tick.MAIL_FAST_FROM, tick.MAIL_FAST_UNTIL
        need(tick.mail_next(f0 - 3600) == f0 and tick.mail_next(f0) == f0 + 900 and tick.mail_next(f1 - 900) == f1
             and tick.mail_next(f1) == f1 + 3600 and tick.mail_every(f1) == 3600,
             "the H148 test window doesn't go every 15 minutes, or doesn't go back to hourly by itself")
        tick.MAIL_FAST_UNTIL = 0  # the rest of this flow counts in hours, whatever the time it runs
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
        for f in ("gitlock.py", "hqpaths.py", "role.py"):
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
        installed = Path.home() / "Library/Application Support/HQ/watchdog.py"
        need("events.jsonl" in wd and installed.exists() and installed.read_text() == wd,
             "the watchdog doesn't log what it fixes, or the installed one is old")
        t = (jv / "routine/tick.py").read_text()
        need("def watchdog_check" in t and "def helper_gap" in t and "kickstart" in t and "hqpaths.start_script()" in t,
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
        # Since H49 the touch and the space bar share pressStart, which unlocks the audio.
        press = page.split("function pressStart(", 1)[1].split("\n}", 1)[0]
        need("startAudio()" in down or ("pressStart(" in down and "startAudio()" in press),
             "the audio isn't unlocked inside the touch (the iPhone may stay silent)")
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
  const server = st => onServerMessage({ data: JSON.stringify({ type: "hq-state", state: st }) });
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
        road = re.sub(r"^(\*\*Mail check:\*\*.*\n)", r"\1\n- Job 98 · done 10:00 · agreed 2026-10-10 09:00 · Build H33 on the HQ roadmap\n"
                      r"- Job 99 · running since 10:05 · agreed 2026-10-10 09:01 · Fix F10 on the HQ roadmap\n", road, count=1, flags=re.M)
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
        env = {**os.environ, "HQ_STATUS_PORT": str(port)}
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
        transcripts in the test server's own calls folder, and the real call page in a headless browser.
        H115: on a call the chat's top line says only who's on it (one name, both, all of them)."""
        import transcript
        calls = self.server.calls
        calls.mkdir(parents=True, exist_ok=True)
        head = "# Call\n\n> **Private.**\n\nStarted 10:00:00 · brain test\n\n"
        (calls / "2099-12-31-2300.md").write_text(head + (
            "- 23:00:01 *filler: Hi there! What's up?*\n"
            "- 23:00:02 *call: connected; connectors: none*\n"
            f"- 23:00:05 **{config.USER_LABEL}:** What's on tomorrow? *(typed)*\n"
            "- 23:00:06 `Read challenges.md` · done (reading in the folder)\n"
            "- 23:00:09 **HQ:** Only the dentist at ten.\n"
            f"- 23:00:12 **{config.USER_LABEL}:** Shoes. *(cut in)* *(cancelled)*\n"
            "- 23:00:14 **Jarvis:** Right, so *(cut off)*\n\nEnded 23:00:20\n"))
        (calls / "2099-12-31-2300-2.md").write_text(head + "- 23:00:40 *filler: Hi there!*\n- 23:00:41 *call: The caller hung up*\n")
        last = transcript.last_call(calls)
        need(last and last["name"] == "2099-12-31-2300", f"the last call with something said wasn't picked: {last and last['name']}")
        lines = last["lines"]
        need([l["who"] for l in lines] == ["filler", "user", "hq", "user", "hq"],
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
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
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
  addChat("user", "New line"); addChat("hq", "New answer");
  // H115: on a call the chat's top line is only who's on it: one name, both on a three-way call, all with more.
  AGENTS = { pa: { name: "Ann" }, pb: { name: "Bea" }, pc: { name: "Cat" } }; agent = "pa"; panel = [];
  showCallTitle(); const one = chatTitle.textContent;
  panel = ["pa", "pb"]; showCallTitle(); const two = chatTitle.textContent;
  panel = ["pa", "pb", "pc"]; showCallTitle(); const three = chatTitle.textContent;
  out.push("names:" + (one === "Ann" && two === "Ann & Bea" && three === "Ann, Bea & Cat" ? "ok" : "WRONG " + [one, two, three].join("/")));
  cleanup("Call ended");
  out.push("after:" + (both() ? "ok" : "MISSING"));
  chatBtn.click(); await wait(400);
  out.push("afterchat:" + (chatLog.querySelectorAll(".msg").length === 2 && chatTitle.textContent === "Ann, Bea & Cat" ? "ok" : "REPLACED " + chatTitle.textContent));
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
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []), "--window-size=390,844",
                                          "--virtual-time-budget=20000", "--dump-dom", f.as_uri()], timeout=120)
        m = re.search(r'<pre id="h34">H34RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        res = m.group(1)
        say(f"   {res}")
        need(all(part.endswith(":ok") for part in res.split(" | ")), f"the buttons or the chat aren't right: {res}")
        return ("chat and status buttons before, during and after a call; before a call the chat shows the last saved call "
                "(tool lines left out, cancelled marked), read only; on a call its top line is only who's on it (H115); after a call "
                "that call stays; no calls: a short note")

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
        need("TEMPERATURE = os.path.join(HERE, \"temperature.py\")" in tick and "(\"temperature\", TEMPERATURE, 150)" in tick and "[PY, script]" in tick,
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
        env = {**os.environ, "HQ_STATUS_PORT": str(port)}
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
        need("BATTERY = os.path.join(HERE, \"battery.py\")" in tick and "(\"battery\", BATTERY, 60)" in tick and "[PY, script]" in tick,
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
        env = {**os.environ, "HQ_STATUS_PORT": str(port)}
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
        need('STATS = os.path.join(HERE, "stats.py")' in tick and "(\"stats\", STATS, 150)" in tick and "[PY, script]" in tick, "the routine doesn't run the stats every minute")
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
        env = {**os.environ, "HQ_STATUS_PORT": str(port)}
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
                                capture_output=True, text=True, env={**os.environ, "HQ_ACTIVITY": str(act)}, timeout=30)
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
printf '\\e]0;HQ happy flow 33\\a'
export HQ_NUDGE_DIR={json.dumps(str(tmp))}
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
        os.environ["HQ_NUDGE_DIR"] = str(tmp)
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
            os.environ.pop("HQ_NUDGE_DIR", None)
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
        env = {**os.environ, "HQ_ROADMAP": str(rm)}
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

    async def flow60(self) -> str:
        """H65: a call reads HQ freely, like the workspace: its files, its logs, git to look, and the
        status page's data with curl on this computer. Changing anything in HQ still asks; curl
        anywhere else, or with options that send or save, asks. H103: web search and reading a web
        page never ask. No Claude turns."""
        from policy import Policy, ALLOW, ASK
        pol = Policy(config.FOLDER)
        hq = Path(os.path.realpath(ROOT))
        log = hq / "scratch/routine/mail.log"
        def v(tool, inp):
            return pol.decide(tool, inp).verdict
        allow = [
            ("Read", {"file_path": str(hq / "app/policy.py")}),
            ("Read", {"file_path": str(log)}),
            ("Grep", {"pattern": "mail", "path": str(hq / "scratch/routine")}),
            ("Glob", {"pattern": "*.log", "path": str(hq / "scratch")}),
            ("Bash", {"command": f'tail -n 20 "{log}"'}),
            ("Bash", {"command": f'cat "{hq}/scratch/routine/mail-last"'}),
            ("Bash", {"command": f'ls -la "{hq}/scratch/routine" | head'}),
            ("Bash", {"command": f'cd "{hq}" && ls'}),
            ("Bash", {"command": f'git -C "{hq}" log --oneline -5'}),
            ("Bash", {"command": "curl -s http://localhost:4748/routines.json"}),
            ("Bash", {"command": "curl -sS --max-time 5 http://127.0.0.1:4748/usage.json"}),
            ("Bash", {"command": "curl -s localhost:4748/jobs-history.json?h=6"}),
        ]
        for tool, inp in allow:
            need(v(tool, inp) == ALLOW, f"a call has to ask to read HQ: {tool} {inp}")
        ask = [
            ("Edit", {"file_path": str(hq / "app/policy.py"), "old_string": "a", "new_string": "b"}),
            ("Write", {"file_path": str(hq / "scratch/routine/mail-last"), "content": "0"}),
            ("Bash", {"command": f'git -C "{hq}" commit -m x'}),
            ("Bash", {"command": f'git -C "{hq}" checkout main'}),
            ("Bash", {"command": f'find "{hq}/scratch" -delete'}),
            ("Bash", {"command": f'python3 "{hq}/routine/tick.py" --mail-now'}),
            ("Bash", {"command": "curl -s -X POST -H x-hq:fix http://localhost:4748/hq/fix"}),
            ("Bash", {"command": "curl -s -d x http://localhost:4748/api/update/start"}),
            ("Bash", {"command": "curl -s -o /tmp/x http://localhost:4748/usage.json"}),
            ("Bash", {"command": "curl -s https://example.com"}),
            ("Bash", {"command": "curl -s http://localhost:9999/x"}),
            ("Read", {"file_path": str(Path.home() / ".ssh/config")}),
        ]
        for tool, inp in ask:
            need(v(tool, inp) == ASK, f"a call may change HQ or read elsewhere without asking: {tool} {inp}")
        need(pol.decide("Edit", {"file_path": str(hq / "app/x.py")}).question.endswith("in HQ?"),
             "a change in HQ isn't asked about as a change in HQ")
        # H103: web search and reading a web page go without asking, on every call and after hang-up too.
        for tool, inp in (("WebSearch", {"query": "library opening hours today"}),
                          ("WebFetch", {"url": "https://example.com", "prompt": "the main heading"})):
            need(v(tool, inp) == ALLOW, f"a call still asks before a web lookup: {tool}")
            need(Policy(config.FOLDER, unattended=True).decide(tool, inp).verdict == ALLOW,
                 f"a web lookup after hang-up is refused: {tool}")
        # The workspace still works as before, through HQ's workspace link too.
        need(v("Read", {"file_path": str(config.FOLDER / "rules.md")}) == ALLOW, "reading the workspace now asks")
        need(v("Edit", {"file_path": str(config.FOLDER / "inbox.md")}) == ALLOW, "writing in the workspace now asks")
        if (ROOT / "workspace").exists():
            need(v("Edit", {"file_path": str(ROOT / "workspace" / "inbox.md")}) == ALLOW,
                 "writing through HQ's workspace link is counted as HQ")
        need("H65" in config.VOICE_RULES and "localhost:4748/routines.json" in config.VOICE_RULES
             and "mail.log" in config.VOICE_RULES, "the call rules don't say HQ may be read freely")
        need("{HQ}" not in config.VOICE_RULES, "the call rules still have a placeholder")
        return f"{len(allow)} reads in HQ and the status page go freely; {len(ask)} changes or reads elsewhere still ask"

    async def flow61(self) -> str:
        """H56.1: HQ's routine and watchdog on a Linux server. No Claude turns. On this computer: the Mac's own
        parts are as they were (where HQ keeps its memory, the programs, the crash check). With a Linux machine
        (this one, or HQ_TEST_LINUX=<ssh host>): HQ's files and the blank template go to a throwaway folder
        there, with their own units, memory and ports and nothing of the user's; the routine must run on the
        minute by itself, the status page it starts must outlive the run, the watchdog must start a stopped
        routine again and end a hanging run without the status page, the units must be enabled with lingering
        on (so they start after a restart), and the crash check must read Linux's boot time. Then everything
        is removed again. Tailscale is never changed (HQ_NO_PHONE) and no call line is started (HQ_CALL_FIX=off)."""
        import subprocess as sp, importlib
        jv = ROOT
        sys.path.insert(0, str(jv / "routine"))
        hqpaths = importlib.import_module("hqpaths")
        crash = importlib.import_module("crash")
        notes = []
        if hqpaths.IS_MAC:
            need(hqpaths.SUPPORT == os.path.expanduser("~/Library/Application Support/HQ") or os.environ.get("HQ_SUPPORT"),
                 f"on the Mac HQ's memory moved: {hqpaths.SUPPORT}")
            need(crash.PANIC_DIR == "/Library/Logs/DiagnosticReports" and crash.PANIC_GLOB == "*.panic",
                 "on the Mac the crash check no longer reads macOS's panic reports")
            need(hqpaths.tool("node", "/opt/homebrew/bin/node") == (os.environ.get("HQ_NODE") or "/opt/homebrew/bin/node"),
                 "on the Mac node is looked for somewhere else")
            need(hqpaths.tailscale("serve", "status")[0] != "sudo" and hqpaths.shell() == "/bin/zsh"
                 and hqpaths.start_script().endswith("app/start.sh"), "on the Mac the call line or its scripts changed")
            r = sp.run(["/usr/sbin/sysctl", "-n", "kern.boottime"], capture_output=True, text=True)
            need(f"sec = {hqpaths.boottime()}," in r.stdout, "the Mac's boot time isn't read as before")
            notes.append("the Mac's parts are as they were")
        for f, sh in (("routine/install-linux.sh", "sh"), ("app/start-linux.sh", "bash"), ("app/stop-linux.sh", "bash"),
                      ("status/phone.sh", "sh")):
            r = sp.run([sh, "-n", str(jv / f)], capture_output=True, text=True)
            need(r.returncode == 0, f"{f} doesn't read as a shell script: {r.stderr.strip()}")
        host = os.environ.get("HQ_TEST_LINUX")
        if not hqpaths.IS_LINUX and not host:
            return "; ".join(notes + ["the Linux part skipped: set HQ_TEST_LINUX=<ssh host> to run it on a Linux machine"])
        run_there = (lambda cmd, **k: sp.run(["ssh", "-o", "BatchMode=yes", host, cmd], **k)) if host else \
            (lambda cmd, **k: sp.run(["bash", "-c", cmd], **k))
        tag = f"hqflow61-{os.getpid()}"
        files = sp.run(["git", "-C", str(jv), "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True).stdout
        files = "\n".join(l for l in files.splitlines() if l and not l.startswith("workspace"))
        tar = sp.run(["tar", "--no-xattrs", "-czf", "-", "-T", "-"] if hqpaths.IS_MAC else ["tar", "-czf", "-", "-T", "-"],
                     input=files.encode(), capture_output=True, cwd=str(jv), env={**os.environ, "COPYFILE_DISABLE": "1"})
        need(tar.returncode == 0, f"couldn't pack HQ: {tar.stderr.decode()[:200]}")
        r = run_there(f'T="$HOME/{tag}"; mkdir -p "$T/HQ" && tar -xzf - -C "$T/HQ"', input=tar.stdout, capture_output=True)
        need(r.returncode == 0, f"couldn't unpack HQ on the Linux machine: {r.stderr.decode()[:200]}")
        script = r"""
T="$HOME/@TAG@"; H="$T/HQ"; S="$T/state"; U="@TAG@"; CP=7899; SP=4799
export HQ_UNIT=$U HQ_SUPPORT=$S HQ_NO_PHONE=1 HQ_CALL_FIX=off HQ_PORT=$CP HQ_STATUS_PORT=$SP
spid() { ss -Hltnp "sport = :$SP" 2>/dev/null | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2; }
SERVER_BEFORE=$(spid)
cleanup() {
  M=$(systemctl --user show -p MainPID --value $U-routine.service 2>/dev/null); [ -n "$M" ] && [ "$M" != 0 ] && kill "$M" 2>/dev/null
  rm -rf "$HOME/.config/systemd/user/$U-routine.service.d"
  sh "$H/routine/install-linux.sh" --remove >/dev/null 2>&1
  P=$(spid); [ -n "$P" ] && [ "$P" != "$SERVER_BEFORE" ] && kill "$P"
  rm -rf "$T"
}
trap cleanup EXIT
fail() { echo "FAIL $*"; exit 1; }
[ -z "$SERVER_BEFORE" ] || fail "port $SP is already in use on the Linux machine"
ss -Hltn "sport = :$CP" | grep -q . && fail "port $CP is already in use on the Linux machine"
cp -r "$H/template" "$T/workspace" && ln -s "$T/workspace" "$H/workspace"
(cd "$H" && python3 routine/jobs.py mail-off >/dev/null) || fail "couldn't switch the test's mail check off"
sh "$H/routine/install-linux.sh" --no-start >/dev/null || fail "the Linux install failed"
for x in routine.timer watchdog.timer start.service; do
  [ "$(systemctl --user is-enabled $U-$x)" = enabled ] || fail "$U-$x isn't enabled, so it wouldn't start after a restart"
done
[ "$(loginctl show-user "$USER" -p Linger --value)" = yes ] || fail "lingering is off: nothing would start after a restart"
systemctl --user start $U-routine.timer $U-watchdog.timer
timeout 80 bash -c "until [ -s $S/heartbeat ]; do sleep 2; done" || fail "the routine didn't run by itself within a minute"
timeout 80 bash -c "until ss -Hltn 'sport = :$SP' | grep -q .; do sleep 2; done" || fail "the status page didn't start"
python3 - "$H" <<'PYC' || fail "the routine's lines are wrong"
import json, sys
d = json.load(open(sys.argv[1] + "/.status/routines.json"))
assert d["helper"]["state"] == "ok", d["helper"]
assert d["jobs"]["state"] in ("ok", "off"), d["jobs"]  # H56.2: with tmux there, jobs can run (nothing waits here)
assert d["mail"]["state"] == "off", d["mail"]  # switched off for the test: never a real mail check
assert "temp" not in d and "battery" not in d, "laptop readings on a server"
PYC
echo "OK the routine runs on the minute; no laptop readings"
SRV=$(spid)
systemctl --user stop $U-routine.timer
systemctl --user start $U-watchdog.service
systemctl --user is-active --quiet $U-routine.timer || fail "the watchdog didn't start the stopped routine again"
grep -q "wasn't running: started its timer again" "$S/watchdog.log" || fail "the watchdog didn't say what it did"
echo "OK a stopped routine is started again by the watchdog"
mkdir -p "$HOME/.config/systemd/user/$U-routine.service.d"
printf '[Service]\nExecStart=\nExecStart=/bin/sleep 600\n' > "$HOME/.config/systemd/user/$U-routine.service.d/hang.conf"
systemctl --user daemon-reload
systemctl --user start --no-block $U-routine.service
timeout 20 bash -c "until [ \"\$(systemctl --user show -p MainPID --value $U-routine.service)\" != 0 ]; do sleep 1; done"
HANG=$(systemctl --user show -p MainPID --value $U-routine.service)
rm -rf "$HOME/.config/systemd/user/$U-routine.service.d"; systemctl --user daemon-reload
python3 -c "import time; open('$S/heartbeat', 'w').write(str(time.time() - 700))"
systemctl --user start $U-watchdog.service
sleep 1
kill -0 "$HANG" 2>/dev/null && fail "the watchdog didn't end the hanging run"
[ "$(spid)" = "$SRV" ] || fail "ending the hanging run took the status page down too"
grep -q "a run was hanging, ended it" "$S/watchdog.log" || fail "the watchdog didn't say it ended the hanging run"
echo "OK a hanging run is ended and the routine restarted; the status page stays up"
timeout 80 bash -c "until grep -q '\"key\": \"helper\"' $H/.status/incidents.json 2>/dev/null; do sleep 2; done" \
  || fail "the next run didn't put the helper's time away in the incidents"
echo "OK the incident says the routine was away, and what the watchdog did"
cd "$H" && python3 - <<'PYC' || fail "the crash check doesn't read Linux's boot time"
import sys; sys.path.insert(0, "routine"); import hqpaths, crash
btime = int(open("/proc/stat").read().split("btime ")[1].split()[0])
assert hqpaths.boottime() == btime and crash.boottime() == btime
assert crash.went_down({"n": 1, "state": ""}, {"n": 1, "started": btime - 60}) == btime
assert crash.went_down({"n": 1, "state": ""}, {"n": 1, "started": btime + 60}) is None
assert crash.PANIC_DIR == "/var/lib/systemd/pstore"
PYC
echo "OK the crash check reads Linux's boot time"
echo "ALL OK"
""".replace("@TAG@", tag)
        r = run_there("bash -s", input=script.encode(), capture_output=True, timeout=330)
        out = r.stdout.decode() + r.stderr.decode()
        left = run_there(f'ls -d "$HOME/{tag}" ~/.config/systemd/user/{tag}-* 2>/dev/null', capture_output=True).stdout.decode().strip()
        need("ALL OK" in out, next((l[5:] for l in out.splitlines() if l.startswith("FAIL ")), out.strip()[-300:]))
        need(not left, f"the test left something behind on the Linux machine: {left}")
        oks = [l[3:] for l in out.splitlines() if l.startswith("OK ")]
        return "; ".join(notes + [f"on Linux ({host or 'here'}): " + "; ".join(oks) + "; everything removed again"])

    async def flow63(self) -> str:
        """H56.2: job windows and the mail check on Linux, in tmux. No Claude turns: a stand-in for Claude (a small
        script given as HQ_CLAUDE) plays the job's chat and the mail check. On this computer: the Mac still opens
        Terminal windows (the scripts are zsh, as before). With a Linux machine (this one, or HQ_TEST_LINUX=<ssh
        host>): HQ and the blank template go to a throwaway folder there with their own memory, ports and session
        names, nothing of the user's; the routine (tick.py, run by hand) must start the mail check in its own hidden
        tmux session that ends by itself with the check counted as ok; start a throwaway job in its own tmux session
        with the watch line on the status page; nudge.py must type continue into that session's pane; and once the
        job says done, the routine must end its chat so the session closes. Then everything is removed again."""
        import subprocess as sp, importlib
        jv = ROOT
        sys.path.insert(0, str(jv / "routine"))
        hqpaths = importlib.import_module("hqpaths")
        notes = []
        if hqpaths.IS_MAC:
            tick = importlib.import_module("tick")
            need(hqpaths.window_kind() in ("terminal", "own") and not tick.LINUX_WINDOWS,
                 "on the Mac jobs no longer open in Terminal")
            need(tick.watch_line(1) == "", "the Mac's status page got a tmux watch line")
            need(tick.CLOSE_WINDOW.startswith("T=$(tty)"), "the Mac's windows no longer close themselves")
            notes.append("the Mac still opens Terminal windows")
        host = os.environ.get("HQ_TEST_LINUX")
        if not hqpaths.IS_LINUX and not host:
            return "; ".join(notes + ["the Linux part skipped: set HQ_TEST_LINUX=<ssh host> to run it on a Linux machine"])
        run_there = (lambda cmd, **k: sp.run(["ssh", "-o", "BatchMode=yes", host, cmd], **k)) if host else \
            (lambda cmd, **k: sp.run(["bash", "-c", cmd], **k))
        tag = f"hqflow63-{os.getpid()}"
        files = sp.run(["git", "-C", str(jv), "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True).stdout
        files = "\n".join(l for l in files.splitlines() if l and not l.startswith("workspace"))
        tar = sp.run(["tar", "--no-xattrs", "-czf", "-", "-T", "-"] if hqpaths.IS_MAC else ["tar", "-czf", "-", "-T", "-"],
                     input=files.encode(), capture_output=True, cwd=str(jv), env={**os.environ, "COPYFILE_DISABLE": "1"})
        need(tar.returncode == 0, f"couldn't pack HQ: {tar.stderr.decode()[:200]}")
        r = run_there(f'T="$HOME/{tag}"; mkdir -p "$T/HQ" && tar -xzf - -C "$T/HQ"', input=tar.stdout, capture_output=True)
        need(r.returncode == 0, f"couldn't unpack HQ on the Linux machine: {r.stderr.decode()[:200]}")
        script = r"""
T="$HOME/@TAG@"; H="$T/HQ"; S="$T/state"; U="@TAG@"; CP=7898; SP=4798
export HQ_UNIT=$U HQ_SUPPORT=$S HQ_NO_PHONE=1 HQ_CALL_FIX=off HQ_PORT=$CP HQ_STATUS_PORT=$SP
export HQ_CLAUDE="$T/bin/claude" HQ_SSH_HOST=testvps HQ_FAKE_HQ="$H" HQ_FAKE_DIR="$T" HQ_CLAUDE_JSON="$T/claude.json"
spid() { ss -Hltnp "sport = :$SP" 2>/dev/null | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2; }
SERVER_BEFORE=$(spid)
cleanup() {
  for s in $(tmux ls -F '#S' 2>/dev/null | grep "^$U-"); do tmux kill-session -t "=$s"; done
  P=$(spid); [ -n "$P" ] && [ "$P" != "$SERVER_BEFORE" ] && kill "$P"
  rm -rf "$T"
}
trap cleanup EXIT
fail() { echo "FAIL $* | log: $(tail -3 "$H/scratch/routine/routine.log" 2>/dev/null | tr '\n' ' ')"; exit 1; }
[ -z "$SERVER_BEFORE" ] || fail "port $SP is already in use on the Linux machine"
command -v tmux >/dev/null || fail "tmux isn't installed"
cp -r "$H/template" "$T/workspace" && ln -s "$T/workspace" "$H/workspace"
mkdir -p "$T/bin" "$H/scratch/routine"
cat > "$T/bin/claude" <<'FAKE'
#!/bin/bash
# A stand-in for Claude (happy flow 63). The mail check (-p): one answer in the stream's shape.
if [[ " $* " == *" -p "* ]]; then
  cat >/dev/null
  echo '{"type":"result","subtype":"success","result":"Flow 63: nothing new"}'
  exit 0
fi
# A job: wait for what's typed into this pane, then say done, then wait to be ended by the routine.
N=$(grep -o 'HQ job [0-9]*' <<<"$*" | head -1 | awk '{print $3}')
echo "flow 63 job $N: waiting for continue"
read -r line
echo "$line" > "$HQ_FAKE_DIR/typed"
python3 "$HQ_FAKE_HQ/routine/jobs.py" done "$N" > "$HQ_FAKE_DIR/done.out" 2>&1
exec sleep 600
FAKE
chmod +x "$T/bin/claude"
cd "$H"
# A saved usage reading well under the lines, so the routine may start a job.
python3 - <<'PYC'
import json, time
from datetime import datetime
r = {"five_hour": {"used_percentage": 5, "resets_at": int(time.time()) + 3600},
     "seven_day": {"used_percentage": 5, "resets_at": int(time.time()) + 86400}}
json.dump({"savedAt": datetime.now().astimezone().isoformat(timespec="seconds"), "rate_limits": r},
          open("scratch/routine/usage-live.json", "w"))
PYC
node status/save-usage.mjs --statusline --any --by "flow 63" >/dev/null || fail "couldn't save a usage reading"
N=$(python3 routine/jobs.py add "flow 63 throwaway job" | grep -o 'Job [0-9]*\|job [0-9]*' | head -1 | awk '{print $2}')
[ -n "$N" ] || fail "couldn't add the throwaway job"
echo '{"projects": {}}' > "$T/claude.json"
python3 routine/tick.py || fail "the routine's look failed"
[ -e scratch/routine/job.json ] && fail "a job was started while Claude doesn't trust the workspace here"
grep -q "hasn't been told to trust the workspace" .status/routines.json || fail "the jobs line doesn't say why the job waits"
grep -q "doesn't trust the workspace" workspace/HQ/roadmap.md || fail "the status block doesn't say why the job waits"
echo "OK a job waits, and says why, while Claude doesn't trust the workspace on this server"
python3 -c "import json; json.dump({'projects': {'$T': {'hasTrustDialogAccepted': True}}}, open('$T/claude.json', 'w'))"
python3 routine/tick.py || fail "the routine's look failed"
timeout 30 bash -c "until [ -s scratch/routine/job.pid ]; do sleep 1; done" || fail "the job's script didn't start"
tmux has-session -t "=$U-job-$N" 2>/dev/null || fail "the job has no tmux session $U-job-$N"
OUT=$(python3 - "$N" "$U" 2>&1 <<'PYC'

import json, re, sys
n, u = sys.argv[1], sys.argv[2]
head = open("workspace/HQ/roadmap.md").read().partition("\n---\n")[0]
want = f"ssh -t testvps tmux attach -t {u}-job-{n}"
assert "tmux session" in head and want in head, head[:400]
PYC
) || fail "the status page doesn't say how to watch the job: $(echo "$OUT" | tail -2 | tr '\n' ' ' | cut -c1-500)"
python3 routine/tick.py >/dev/null 2>&1  # the next minute's look: the jobs line with the watch line
grep -q "watch it: ssh -t testvps tmux attach -t $U-job-$N" .status/routines.json || fail "the jobs line doesn't say how to watch it"
echo "OK the job runs in its own tmux session, and the status page says: ssh -t testvps tmux attach -t <session>"
timeout 60 bash -c "until [ ! -s scratch/routine/mail.pid ] || ! kill -0 \$(cat scratch/routine/mail.pid) 2>/dev/null; do sleep 1; done"
tmux has-session -t "=$U-mail" 2>/dev/null && fail "the mail check's session didn't end by itself"
grep -q -- "--- exit 0" scratch/routine/mail.log || fail "the mail check didn't run to its end: $(tail -3 scratch/routine/mail.log)"
python3 routine/tick.py >/dev/null 2>&1
python3 - <<'PYC' || fail "the mail check's line isn't ok"
import json
d = json.load(open(".status/routines.json"))
assert d["mail"]["state"] == "ok" and "nothing new" in d["mail"]["text"], d["mail"]
PYC
echo "OK the mail check ran hidden in its own tmux session, ended by itself, and counts as ok"
sleep 2
python3 -c "import sys; sys.path.insert(0, 'routine'); import quiet; quiet.request($N)"
timeout 30 bash -c "until [ -s '$T/typed' ]; do sleep 1; done" || fail "continue wasn't typed into the job's pane"
grep -qx continue "$T/typed" || fail "something else was typed: $(cat $T/typed)"
grep -q '"ok": true' scratch/routine/nudge-result.json || fail "nudge.py didn't say it typed"
echo "OK continue is typed into the job's own pane"
timeout 20 bash -c "until grep -q 'Job $N · done' workspace/HQ/roadmap.md; do sleep 1; done" || fail "the job's done mark didn't land: $(cat $T/done.out)"
tmux has-session -t "=$U-job-$N" 2>/dev/null || fail "the session closed before the routine ended it"
python3 routine/tick.py >/dev/null 2>&1
sleep 2
tmux has-session -t "=$U-job-$N" 2>/dev/null && fail "the job's session is still open after its done mark"
grep -q "job $N finished; closed its window" scratch/routine/routine.log || fail "the routine didn't say it closed the job"
[ -e scratch/routine/job.json ] && fail "the routine still thinks a job runs"
echo "OK after its done mark the routine ends the chat and the session closes by itself"
echo "ALL OK"
""".replace("@TAG@", tag)
        r = run_there("bash -s", input=script.encode(), capture_output=True, timeout=240)
        out = r.stdout.decode() + r.stderr.decode()
        left = run_there(f'ls -d "$HOME/{tag}" 2>/dev/null; tmux ls -F "#S" 2>/dev/null | grep "^{tag}-"',
                         capture_output=True).stdout.decode().strip()
        need("ALL OK" in out, next((l[5:] for l in out.splitlines() if l.startswith("FAIL ")), out.strip()[-300:]))
        need(not left, f"the test left something behind on the Linux machine: {left}")
        oks = [l[3:] for l in out.splitlines() if l.startswith("OK ")]
        return "; ".join(notes + [f"on Linux ({host or 'here'}): " + "; ".join(oks) + "; everything removed again"])

    async def flow59(self) -> str:
        """H62: after a crash the job carries on. No Claude turns, no job started, nothing written outside
        the test: a made-up crash on a copy of the roadmap (a boot time after the job's start, a fake panic
        report), with the incident log and the status block caught in the test."""
        import subprocess as sp, importlib
        from policy import Policy, DENY
        jv = ROOT
        sys.path.insert(0, str(jv / "routine"))
        crash = importlib.import_module("crash")
        rm = self.tmp / "roadmap-H62.md"
        rm.write_text(ROADMAP.read_text())
        env = {**os.environ, "HQ_ROADMAP": str(rm)}
        def jobs(*a, ok=True):
            r = sp.run(["python3", str(jv / "routine/jobs.py"), *a], capture_output=True, text=True, env=env)
            need((r.returncode == 0) == ok, f"jobs.py {' '.join(a)}: {r.stdout.strip()} {r.stderr.strip()}")
            return r.stdout + r.stderr
        def waiting():
            return {j["n"]: j for j in json.loads(jobs("next"))["waiting"]}
        def line():
            return [j["n"] for j in json.loads(jobs("next"))["waiting"]]
        def state(n):
            for l in rm.read_text().splitlines():
                if l.startswith(f"- Job {n} · "):
                    return l.split(" · ")[1]
            return None
        # Only the test's jobs in the copy: the copy's own waiting ones cancelled, its running one stopped.
        for n in line():
            jobs("stop", str(n))
        for j in json.loads(jobs("next"))["running"]:
            jobs("mark", str(j["n"]), "stopped 00:00")
        a, b, c = (int(jobs("add", f"flow 59 job {x}").split()[1]) for x in "abc")
        an_hour_ago = time.time() - 3600
        jobs("mark", str(a), "running since " + time.strftime("%H:%M", time.localtime(an_hour_ago)))
        job = json.loads(jobs("next"))["running"][0]
        s = {"n": a, "pid": 999999, "started": an_hour_ago}
        caught = {"inc": [], "status": [], "log": []}
        class Inc:
            @staticmethod
            def past(key, since, until, why, fixes):
                caught["inc"].append((key, why, [w for _, w in fixes]))
        st = lambda state_, step, logline: caught["status"].append((state_, step, logline))
        lg = lambda m: caught["log"].append(m)
        panics = self.tmp / "panics"
        panics.mkdir(exist_ok=True)
        # Not a crash: the Mac was already up before the job started (a closed window, say).
        need(not crash.recover(job, s, jobs, Inc, st, lg, boot=an_hour_ago - 600, panic_dir=str(panics)),
             "a job whose chat closed without a restart was taken for a crash")
        need(state(a).startswith("running") and not caught["inc"], "a job that wasn't a crash was changed")
        # A crash: the Mac started again after the job's start, and macOS wrote a panic report.
        (panics / "panic-full-test.panic").write_text("test")
        boot = an_hour_ago + 900
        need(crash.recover(job, s, jobs, Inc, st, lg, boot=boot, panic_dir=str(panics)), "a crash wasn't seen")
        d = max(waiting())
        need(line() == [d, b, c], f"the rerun isn't first in line, or the line changed: {line()}")
        need(state(a).startswith("ended") and f"by a crash; requeued as job {d}" in state(a), f"the crashed job says: {state(a)}")
        rerun = waiting()[d]["text"]
        need(rerun.startswith(f"Rerun of job {a},") and "pick up from there instead of starting over" in rerun
             and rerun.endswith("Then the job as it was: flow 59 job a") and "panic report" in rerun,
             f"the rerun's text: {rerun}")
        need(caught["inc"] and caught["inc"][-1][0] == "jobs" and "crash" in caught["inc"][-1][1]
             and f"job {d}" in caught["inc"][-1][2][0] and "top of the line" in caught["inc"][-1][2][0],
             f"the incident doesn't say it was a crash and was queued again: {caught['inc']}")
        need(caught["status"][-1][0] == "STOPPED" and "crash" in caught["status"][-1][1] and f"job {d}" in caught["status"][-1][1],
             f"the status block doesn't say so: {caught['status']}")
        lst = jobs("list")
        need(f"Job {a} · ended" in lst and "by a crash" in lst and f"Job {d} · ready · number 1 in line · Rerun of job {a}" in lst,
             f"jobs.py list doesn't say so (a call reads it): {lst}")
        # A second crash in the same job: not queued again; the rest of the line goes on.
        jobs("mark", str(d), "running since " + time.strftime("%H:%M", time.localtime(boot + 60)))
        job2 = json.loads(jobs("next"))["running"][0]
        need(crash.recover(job2, {"n": d, "pid": 1, "started": boot + 60}, jobs, Inc, st, lg, boot=boot + 1200,
                           panic_dir=str(panics)), "the second crash wasn't seen")
        need(line() == [b, c] and "by a crash, again; not run again by itself" in state(d) and state(d + 1) is None,
             f"a second crash was queued again, or the line is wrong: {line()} {state(d)} {state(d + 1)}")
        need("already crashed once" in caught["inc"][-1][2][0] and "not run again" in caught["status"][-1][1],
             f"the second crash doesn't say it isn't run again: {caught['inc'][-1]} {caught['status'][-1]}")
        # Lost track of the job (no job.json): its "running since" still tells when it started.
        need(crash.went_down({"n": 1, "state": "running since " + time.strftime("%H:%M", time.localtime(an_hour_ago))},
                             None, boot=boot) == boot, "without job.json the start time isn't read from the queue")
        # The routine checks for a crash first; a pid from before a restart counts as gone.
        tick = (jv / "routine/tick.py").read_text()
        need("crash.went_down(job, s)" in tick and "crash.recover(job, s, jobs, incidents, status, log" in tick
             and tick.index("crash.recover(") < tick.index('"ended " + time.strftime'),
             "the routine doesn't check for a crash first")
        # The status page reads the copy fine: the crashed jobs finished, the line numbered.
        js = f"""import {{ parseRoadmap }} from {json.dumps(str(jv / 'status/parse.mjs'))};
import {{ readFileSync }} from 'node:fs';
const r = parseRoadmap(readFileSync({json.dumps(str(rm))}, 'utf8'));
console.log(JSON.stringify({{problems: r.problems, w: r.queue.jobs.filter((j) => j.place).map((j) => [j.n, j.place])}}));"""
        pd = json.loads(sp.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True).stdout)
        need(not pd["problems"] and pd["w"] == [[b, 1], [c, 2]], f"the status page reads it wrong: {pd}")
        # Only the routine marks a crash; a call can't.
        pol = Policy(config.FOLDER)
        need(pol.decide("Bash", {"command": f'python3 "{ROOT}/routine/jobs.py" crashed 28 test'}).verdict == DENY,
             "a call may mark a job as crashed")
        return "a crash (boot after the job's start, panic report) queues it again first in line with a pick-up note; incident and status say so; once only; not a crash left alone"

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
  const server = st => onServerMessage({ data: JSON.stringify({ type: "hq-state", state: st }) });
  const can = on => onServerMessage({ data: JSON.stringify({ type: "hq-cancellable", on }) });
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

        from pipeline import late_cancel, type_to_agent

        live = await self.get_live()
        llm = live.llm
        flags: list[bool] = []
        llm.on_cancellable = flags.append
        struck: list[bool] = []
        n = len(llm.turns)
        say(f"typing, then cancelling late: {Q_LATE_CANCEL}")
        t0 = time.perf_counter()
        need(await type_to_agent(live.worker, llm, live.call_state, Q_LATE_CANCEL), "the typed message was refused")
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
        say(f"   She said: {reply!r}")
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
  const server = st => onServerMessage({ data: JSON.stringify({ type: "hq-state", state: st }) });
  const on = () => voiceBtn.getAttribute("aria-pressed") === "true";
  try { localStorage.removeItem("hq-voice-off"); } catch (e) {}
  voiceOff = false; applyVoice();
  const cs = getComputedStyle(voiceBtn);
  check("there", cs.display !== "none" && cs.position === "fixed" && !on() && !audioEl.muted, cs.display + "/" + cs.position + "/" + on());
  // before a call: off, remembered
  voiceBtn.click(); await wait(50);
  check("idle-off", on() && audioEl.muted && localStorage.getItem("hq-voice-off") === "on", on() + "/" + audioEl.muted);
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
  onServerMessage({ data: JSON.stringify({ type: "hq-chat", who: "hq", text: "Paris is the capital." }) });
  check("chat", [...chatLog.querySelectorAll(".msg.hq")].some(d => d.textContent === "Paris is the capital."), chatLog.textContent);
  // the talk button, its low sound, and Cancel as before
  server("listening");
  let sounds = 0; const ts = talkSound; talkSound = () => { sounds++; return ts(); };
  muteBtn.dispatchEvent(new PointerEvent("pointerdown", { pointerId: 1, bubbles: true })); await wait(600);
  check("talk", muteBtn.classList.contains("talk") && sounds === 1 && audioEl.muted, muteBtn.className + "/" + sounds);
  document.dispatchEvent(new PointerEvent("pointerup", { pointerId: 1, bubbles: true })); await wait(100);
  onServerMessage({ data: JSON.stringify({ type: "hq-cancellable", on: true }) }); server("thinking"); await wait(50);
  check("cancel", cancelBtn.classList.contains("show"), cancelBtn.className);
  // on again during the call: track and element back on, status without it
  voiceBtn.click(); await wait(50);
  check("live-on", !on() && !audioEl.muted && tr() && localStorage.getItem("hq-voice-off") === "off", on() + "/" + audioEl.muted + "/" + tr());
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
        return "her voice off before and during a call (element muted, track off); chat still gets her lines; talk button and Cancel unchanged (the low sound is silent since F14); remembered on the next load"

    # 36
    async def flow36(self) -> str:
        """H41: the Type to HQ box is a text field that grows downward as he types, up to about six
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
        installed = Path.home() / "Library/Application Support/HQ/watchdog.py"
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
        rule = (ROOT / "routine/hq-lidsleep.sudoers").read_text()
        body = [x for x in rule.splitlines() if x.strip() and not x.startswith("#")]
        need(body == ["YOUR_USER ALL=(root) NOPASSWD: /usr/bin/pmset -a disablesleep 1, /usr/bin/pmset -a disablesleep 0"],
             f"the sudoers rule allows more than the two commands: {body}")
        v = await asyncio.to_thread(run, ["/usr/sbin/visudo", "-cf", str(ROOT / "routine/hq-lidsleep.sudoers")], timeout=20)
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
        need('LIDSLEEP = os.path.join(HERE, "lidsleep.py")' in tick and "(\"lid sleep\", LIDSLEEP, 30)" in tick and "[PY, script]" in tick, "the routine doesn't read it every minute")
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
                                env={**os.environ, "HQ_STATUS_PORT": str(port)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
const L = {{ five: {{ moving: false, fixed: 70 }}, weekly: {{ moving: false, fixed: 50 }}, fable: {{ moving: false, fixed: 50 }} }};
const v = (x, o) => usageVerdict(x, L, new Date(), o).stop;
console.log(JSON.stringify({{
  fiveOverNormal: v(r(90, 10)), fiveOverPast: v(r(90, 10), {{ weeklyOnly: true }}),
  weekOverPast: v(r(10, 60), {{ weeklyOnly: true }}), bothOverPast: v(r(90, 60), {{ weeklyOnly: true }}),
  keptWeekPast: v(r(90, 99, true), {{ weeklyOnly: true }}),
  unreadablePast: usageVerdict({{ readable: false }}, L, new Date(), {{ weeklyOnly: true }}).stop }}));"""
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
                 "current-situation.md", "challenges.md", "inbox.md", "coaching/log.md", "HQ/roadmap.md",
                 "HQ/calls/.gitkeep", "reviews/.gitkeep", ".claude/settings.json", ".claude/mail-commit.sh",
                 ".claude/skills/life-coach/SKILL.md"]
        missing = [f for f in files if not (tpl / f).exists()]
        need(not missing, f"the template is missing {missing}")
        for rel in re.findall(r"@([\w./-]+\.md)", (tpl / "CLAUDE.md").read_text()):
            need((tpl / rel).exists(), f"the template's CLAUDE.md loads {rel}, which isn't there")
        for f in ("README.md", "rules.md", "me.md", "vision.md", "current-situation.md", "challenges.md", "HQ/roadmap.md"):
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
        roadmap = tpl / "HQ/roadmap.md"
        js = f"""import {{ readFileSync }} from 'node:fs';
import {{ parseRoadmap }} from '{(ROOT / "status/parse.mjs").as_uri()}';
const r = parseRoadmap(readFileSync({json.dumps(str(roadmap))}, 'utf8'));
console.log(JSON.stringify({{ problems: r.problems, state: r.state, phases: r.phases.length, queue: r.queue }}));"""
        out = sp.run(["node", "--input-type=module", "-e", js], capture_output=True, text=True, timeout=30)
        need(out.returncode == 0, f"the status page's parser failed on the template: {out.stderr[-300:]}")
        r = json.loads(out.stdout)
        need(not r["problems"] and r["state"] == "WAITING" and r["phases"] >= 1,
             f"the status page can't read the template's roadmap: {r}")
        env = dict(os.environ, HQ_ROADMAP=str(roadmap))
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
        env = {**os.environ, "HQ_ROADMAP": str(rm)}
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
        # And only its own items: the copy's planned items could be due already.
        for l in sched("list").split("Looking back")[0].splitlines():
            if l.startswith("Item "):
                sched("cancel", l.split()[1])
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
        # H99: the priority tag. A tagged item goes ahead of the waiting jobs, never stops a running one, and
        # a later tagged item lines up after the tagged ones before it.
        b1, b2 = (int(jobs("add", f"flow 45 waiting {k}").split()[1]) for k in (1, 2))
        p1_out = sched("add", "now", "flow 45 priority one", "--priority")
        need("priority" in p1_out, f"planning with --priority doesn't say so: {p1_out}")
        p1 = int(p1_out.split()[1])
        need(f"Item {p1} " in sched("list") and ", priority" in sched("list").split("Looking back")[0],
             "list doesn't show the priority tag")
        st = json.loads(sched("status"))
        need(f"Item {p1} is due with priority" in st["text"], f"the routine line doesn't say the tagged item goes first: {st}")
        jobs("mark", str(b1), "running since 00:02")
        need("Nothing to start" in sched("promote"), "a tagged item went in while a job was running")
        jobs("done", str(b1))
        did = sched("promote")
        need(f"item {p1} became job" in did and "first in line" in did, f"the tagged item didn't go first: {did}")
        w = q()["waiting"]
        need([x["n"] for x in w][1:] == [b2] and "flow 45 priority one" in w[0]["text"],
             f"the tagged item's job isn't first in line, ahead of the waiting job: {w}")
        j1 = w[0]["n"]
        p2 = int(sched("add", "now", "flow 45 priority two").split()[1])
        need("Nothing to start" in sched("promote"), "an untagged item went in while jobs were waiting")
        need("has priority now" in sched("priority", str(p2)), "tagging a planned item later doesn't work")
        did = sched("promote")
        w = q()["waiting"]
        need(f"item {p2} became job" in did and [x["n"] for x in w][0] == j1 and [x["n"] for x in w][2:] == [b2]
             and "flow 45 priority two" in w[1]["text"], f"a second tagged item doesn't line up after the first: {w}")
        p3 = int(sched("add", "sunday 10:00", "flow 45 priority three", "--priority").split()[1])
        ep = sp.run(["python3", "-c", "import sys, json; sys.path.insert(0, sys.argv[1]); import estimate; "
                     "print(json.dumps(estimate.plan()['items']))", str(jv / "routine")],
                    capture_output=True, text=True, env=env)
        need(json.loads(ep.stdout or "{}").get(str(p3), {}).get("priority"), f"the estimate doesn't know the tag: {ep.stdout} {ep.stderr}")
        need("no priority tag now" in sched("priority", str(p3), "off") and ", priority" not in sched("list").split("Looking back")[0],
             "taking the tag off doesn't work")
        sched("priority", str(p1), ok=False)  # it's a job now, not waiting
        sched("cancel", str(p3))
        for x in q()["waiting"]:
            jobs("done", str(x["n"]))
        sched("promote")
        # H111: looking back. Items whose time passed while the job list (or the usage) held them back are
        # never skipped: when the scheduler's turn comes they all run, one after another, earliest first.
        held = int(jobs("add", "flow 45 held by the usage").split()[1])
        jobs("mark", str(held), "held: usage over the line")
        past = {}
        for at, name in (("09:15", "b"), ("08:05", "a"), ("11:40", "c")):
            k = int(sched("add", "now", f"flow 45 passed {name}").split()[1])
            past[name] = k
            yday = (time.time() - 86400) if name == "a" else time.time()  # one from yesterday too
            stamp = time.strftime("%Y-%m-%d", time.localtime(yday)) + " " + at
            rm.write_text(re.sub(rf"^(- Item {k} · waiting · at )\S+ \S+", rf"\g<1>{stamp}", rm.read_text(), flags=re.M))
        need("Nothing to start" in sched("promote"), "a passed item went ahead of a job held by the usage")
        st = json.loads(sched("status"))
        need(f"Item {past['a']} is due, 2 more after it, earliest first" in st["text"] and "job list goes first" in st["text"],
             f"the routine line doesn't say the passed items wait their turn: {st}")
        jobs("done", str(held))
        for name in ("a", "b", "c"):
            did = sched("promote")
            need(f"item {past[name]} became job" in did, f"the passed items don't run earliest first ({name}): {did}")
            w = q()["waiting"]
            need(len(w) == 1, f"more than one passed item went in at once: {w}")
            need("Nothing to start" in sched("promote"), "a passed item went in while its turn wasn't there")
            jobs("done", str(w[0]["n"]))
        sched("promote")
        lst = sched("list")
        need(all(f"Item {past[x]} " in lst.split("Looking back")[1] for x in past)
             and not any(f"Item {past[x]} " in lst.split("Looking back")[0] for x in past),
             f"a passed item got lost or is still planned: {lst}")
        # The queue keeps working with the schedule under it, and the schedule survives the queue's writes.
        text = rm.read_text()
        need(text.count("## The schedule") == 1 and text.count("## The queue") == 1
             and text.index("## The queue") < text.index("## The schedule"), "the schedule isn't right under the queue")
        # The routine asks the scheduler only when nothing runs or waits.
        tick = (jv / "routine/tick.py").read_text()
        # H99: every minute with nothing running it asks (promote itself keeps the job list first, untagged).
        i_prom = tick.index("did = schedule_promote()")
        need(tick.index("    if not q[\"on\"]:\n        return") < i_prom < tick.index("job = line[0]") and "H99" in tick,
             "the routine doesn't ask the scheduler before it picks a job")
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
        for sub in ('add "tuesday 15:00" "x"', "list", "cancel 3", 'move 3 "tomorrow 9:30"', "priority 3", "priority 3 off"):
            need(pol.decide("Bash", {"command": f"{s_} {sub}"}).verdict == ALLOW, f"a call can't {sub.split()[0]}")
        need(pol.decide("Bash", {"command": f"{s_} promote"}).verdict == DENY, "a call may promote an item")
        need("schedule.py" in config.VOICE_RULES and "job list always goes first" in config.VOICE_RULES,
             "the call rules don't say how to plan work")
        need("--priority" in config.VOICE_RULES and "'prio'" in page and "Due, goes first" in page,
             "the call rules or the status page don't know the priority tag (H99)")
        need("H111" in config.VOICE_RULES and "earliest first" in config.VOICE_RULES,
             "the call rules don't say passed items still run, earliest first (H111)")
        return "plans by day and time; waits while a job runs, waits or the routine is off; then becomes one job, past the line kept; looking back, move, cancel; priority tag goes first in line, never stops a running job (H99); passed items all run after the job list, earliest first, none lost (H111); page, routine line, call rules"

    async def flow46(self) -> str:
        """H27: the Mac desktop app. No Claude turns. The watchdog part on made-up routine lines, its turning-on
        plan with everything faked off, the strip in a headless browser, then the real app built and its window
        (never shown) loaded once with --selftest. H145: her texts in the app: the strip's third tab with her name and
        a red dot, each of her texts a notification once (never his own, never while he looks at her chat, nothing
        old on the first look), her chat inside the app without the phone's back arrow or notification button.
        Off a Mac the app itself isn't built; the rest runs."""
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
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
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
  // H145: her tab. The first look takes everything there as read; a new text of hers is a notification once and
  // the dot; his own text never; looking at her chat clears the dot and shows nothing.
  const th = (...m) => ({ agent: { name: 'Ann', colour: '#123456' }, messages: m.map(([from, at, text]) => ({ from, at, text })) });
  const a = [['agent', 100, 'old one'], ['me', 110, 'mine']];
  const i1 = hq.inbox(th(...a), null, null, false);
  out.push('first:' + i1.unread + '/' + i1.notify.length + '/' + i1.seen + '/' + i1.told + '/' + document.getElementById('direct-name').textContent + '/' + hq.state().dot);
  const b = [...a, ['agent', 120, 'new one']];
  const i2 = hq.inbox(th(...b), i1.seen, i1.told, false);
  out.push('new:' + i2.unread + '/' + i2.notify.map((m) => m.text).join('+') + '/' + i2.told + '/' + hq.state().dot);
  const i3 = hq.inbox(th(...b), i2.seen, i2.told, false);
  out.push('again:' + i3.notify.length + '/' + i3.unread);
  const c = [...b, ['me', 130, 'answer']];
  const i4 = hq.inbox(th(...c), i3.seen, i3.told, false);
  out.push('his:' + i4.notify.length + '/' + i4.unread);
  const i5 = hq.inbox(th(...c), i4.seen, i4.told, true);
  out.push('looking:' + i5.unread + '/' + hq.state().dot + '/' + i5.seen);
  const i6 = hq.inbox(th(...c, ['agent', 140, 'while looking']), i5.seen, i5.told, true);
  out.push('whilelooking:' + i6.notify.length + '/' + i6.unread);
  document.getElementById('tab-direct').click();
  out.push('directtab:' + hq.state().tab + '/' + getComputedStyle(document.getElementById('dog')).display);
  document.getElementById('tab-status').click();
  out.push('anim:' + ['happy', 'alert', 'bark', 'run', 'sleep'].map((m) => { document.getElementById('dog').setAttribute('class', 'dog ' + m);
    return [...document.querySelectorAll('#dog *')].some((e) => getComputedStyle(e).animationName !== 'none') ? 1 : 0; }).join(''));
  const pre = document.createElement('pre'); pre.id = 'h27'; pre.textContent = 'H27RESULT ' + out.join(' | ') + ' END'; document.body.append(pre);
})();
</script>"""
        f = self.tmp / "h27-shell.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []), f"--user-data-dir={self.tmp / 'h27-profile'}",
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
        need(res["first"] == "0/0/110/110/Ann/false", f"her first look shows old texts as new (H145): {res['first']}")
        need(res["new"] == "1/new one/120/true", f"her new text isn't a notification with a dot (H145): {res['new']}")
        need(res["again"] == "0/1", f"her text would be shown twice (H145): {res['again']}")
        need(res["his"] == "0/1", f"his own text is a notification (H145): {res['his']}")
        need(res["looking"] == "0/false/130", f"looking at her chat doesn't clear the dot (H145): {res['looking']}")
        need(res["whilelooking"] == "0/0", f"a text while he looks at her chat still pops up (H145): {res['whilelooking']}")
        need(res["directtab"] == "direct/none", f"her tab doesn't open, or the dog shows on it (H145): {res['directtab']}")
        swift = (ROOT / "desktop/HQ.swift").read_text()
        need("UNUserNotificationCenter.current()" in swift and 'self.show("direct")' in swift and '"directTold"' in swift
             and "hq.inbox(" in swift and "/direct?app=1" in swift and "/direct.json" in swift,
             "the app doesn't show her texts as Mac notifications that open her chat (H145)")
        need("push(" not in swift and "/direct/send" not in swift, "the app sends or pushes her texts itself (H145)")
        dh = (ROOT / "status/direct.html").read_text()
        need("has('app')" in dh and "if (APP) document.querySelector('header a').remove();" in dh and "if (!SHEET && !APP) bellState();" in dh,
             "her chat in the app still shows the phone's back arrow or notification button (H145)")
        if sys.platform != "darwin":
            return ("seven made-up states judged like the status page; turning on starts only what's off, stops nothing; the strip's five "
                    "moods move; her tab: a dot and a notification once per text of hers, none for old ones, his own or while he looks; "
                    "off a Mac the app itself isn't built (run this flow on the laptop for that)")
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
            need(got["status_loaded"] and "HQ" in got["status_title"][0], f"the app didn't load the status page: {got}")
        if got["status_loaded"]:
            need(got.get("direct", {}).get("read") is True and got["strip"].get("direct") not in ("", "Texts", None),
                 f"the app didn't read her thread or name her tab (H145): {got.get('direct')} {got['strip'].get('direct')}")
        # F15: the strip's empty space moves the window like a normal Mac app; its buttons don't.
        d = got.get("drag") or {}
        need(d.get("bar", 0) >= 80 and d.get("buttons", 0) >= 1 and d.get("empty_moves") is True and d.get("button_moves") is False,
             f"the window can't be dragged from the strip's top bar, or a button drags it (F15): {d}")
        need("status.pageZoom = next" in swift and 'item("Smaller", #selector(zoomOut), "-"' in swift and 'id="zoom-in"' in page,
             "the status page can't be made bigger or smaller (H47)")
        need('var tab = "call"' in swift and "_setICECandidateFilteringEnabled:" in swift and "7860/?app=1" in swift,
             "the app doesn't open on Call, or its call page still hides the address (H46)")
        need('origin.host == "127.0.0.1"' in swift and "applicationShouldTerminateAfterLastWindowClosed" in swift,
             "the microphone isn't limited to this MacBook, or closing doesn't quit")
        return f"seven made-up states judged like the status page; turning on starts only what's off, stops nothing; the strip's five moods move; the app builds and its window read: {got['strip']['head']}; the bar drags the window, its {d['buttons']} buttons don't"

    async def flow47(self) -> str:
        """H28: the phone version of the Mac app. No Claude turns. Its own status server on a test port, with
        Turn everything on set to say only what it would do."""
        import urllib.request, urllib.error
        port = 4797
        env = {**os.environ, "HQ_STATUS_PORT": str(port), "HQ_FIX_DRY": "1"}
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

    # 62
    async def flow62(self) -> str:
        """H73: Moneypenny, coming soon. In HQ's defaults (Fable, yellow), not on the picker; the call
        page shows her as a smaller locked card under Donna and Pepper, greyed out, her icon yellow with an M.
        The page is the same in the desktop app and the phone version. No Claude turns."""
        import agents
        every = {a["id"]: a for a in agents.load(config.FOLDER)}
        m = every.get("moneypenny")
        need(m and m["coming_soon"] and m["model"] == "fable" and m["colour"].lower() == "#ca8a04",
             f"Moneypenny isn't in the defaults as a locked Fable agent in yellow: {m}")
        need([a["id"] for a in agents.visible(config.FOLDER)] == ["donna", "pepper"]
             and [a["id"] for a in agents.soon(config.FOLDER)] == ["moneypenny"], "Moneypenny can be picked, or isn't listed as coming soon")
        need(agents.find(config.FOLDER, None, "deep")["id"] == "pepper" and agents.find(config.FOLDER, "nobody")["id"] == "donna",
             "a call without her asked for lands on Moneypenny")
        # H121: she can be brought into a call, on Opus while there's no Fable, so the ears know her name
        need(agents.runs_on(m["model"]) == "opus" and agents.runs_on("sonnet") == "sonnet"
             and agents.runs_on("claude-x-1") == "claude-x-1", "a model HQ doesn't know isn't run on Opus")
        need("Moneypenny" in config.WHISPER_PROMPT, "Moneypenny isn't in the speech recognition prompt")
        need(">M</text>" in agents.picture_svg(m) and "#ca8a04" in agents.picture_svg(m), "her placeholder isn't a yellow M")
        # A workspace can unlock her, or hide her.
        ws = self.tmp / "agents62"
        (ws / "HQ" / "agents").mkdir(parents=True)
        (ws / "HQ" / "agents" / "agents.json").write_text(json.dumps([{"id": "moneypenny", "coming_soon": False}]))
        need([a["id"] for a in agents.visible(ws)] == ["donna", "pepper", "moneypenny"] and not agents.soon(ws), "a workspace can't unlock her")
        (ws / "HQ" / "agents" / "agents.json").write_text(json.dumps([{"id": "moneypenny", "hidden": True}]))
        need(not agents.soon(ws), "a hidden locked agent still shows")
        await self.ensure_server()
        code, body, _ = http_get("/api/agents")
        j = json.loads(body or b"{}")
        need(code == 200 and [a["id"] for a in j.get("agents", [])] == ["donna", "pepper"]
             and [a["id"] for a in j.get("soon", [])] == ["moneypenny"] and "personality" not in j["soon"][0],
             f"/api/agents doesn't list her apart as coming soon: {body[:200]!r}")
        code, body, ctype = http_get("/agents/moneypenny/picture")
        need(code == 200 and ctype.startswith("image/"), "her picture doesn't load")
        page = http_get("/")[1].decode()
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        harness = r"""<script>
setTimeout(() => {
  const out = [], card = document.querySelector('#soon .card[data-soon="moneypenny"]');
  out.push('buttons:' + [...document.querySelectorAll('#modes button')].map(b => b.dataset.agent).join(','));
  out.push('card:' + (card ? card.textContent.replace(/\s+/g, ' ').trim() : 'none'));
  out.push('below:' + (card ? String(card.getBoundingClientRect().top > document.getElementById('modes').getBoundingClientRect().bottom) : 'none'));
  out.push('smaller:' + (card ? String(card.querySelector('img').getBoundingClientRect().width < document.querySelector('#modes img').getBoundingClientRect().width) : 'none'));
  out.push('greyed:' + (card ? getComputedStyle(card.querySelector('div')).opacity + '/' + getComputedStyle(card.querySelector('img')).opacity : 'none'));
  if (card) card.click();
  out.push('picked:' + agent + '/' + mode + ' inagents:' + ('moneypenny' in AGENTS));
  out.push('voices:' + [...document.querySelectorAll('#voices .row span')].map(s => s.firstChild.textContent).join(','));
  setState('live', 'x'); out.push('oncall:' + (getComputedStyle(document.getElementById('soon')).display === 'none' ? 'hidden' : 'shown'));  // H140: steps aside setState('idle', 'x');
  out.push('oldsaved:' + localStorage.getItem('hq-cards'));
  if (card) for (let i = 0; i < 11; i++) card.click();  // with the tap above, twelve
  out.push('egg:' + [...document.querySelectorAll('#modes button')].map(b => b.dataset.agent).join(',') + '/' + localStorage.getItem('hq-cards') + '/' + sessionStorage.getItem('hq-cards'));
  const pre = document.createElement('pre'); pre.id = 'h73'; pre.textContent = 'H73RESULT ' + out.join(' | ') + ' END'; document.body.append(pre);
}, 1500);
</script>"""
        f = self.tmp / "h73.html"
        # H126: an unlock saved by the old page (before H126) is dropped when the page opens.
        saved = "<script>try { localStorage.setItem('hq-cards', '[\"moneypenny\"]'); } catch (e) {}</script>"
        f.write_text(page.replace("</body>", harness + "</body>", 1).replace("<head>", f'<head><base href="{TEST_URL.rstrip("/")}/">' + saved, 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []), f"--user-data-dir={self.tmp / 'h73-profile'}",
                                          "--disable-web-security", "--virtual-time-budget=5000", "--dump-dom", f.as_uri()], timeout=60)
        mm = re.search(r'<pre id="h73">H73RESULT (.*?) END</pre>', r.stdout)
        need(mm, f"the call page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        res = dict(part.split(":", 1) for part in mm.group(1).split(" | "))
        say(f"   {mm.group(1)}")
        need(res["buttons"] == "donna,pepper", f"Moneypenny is a button you can pick: {res}")
        need(res["card"].startswith("Moneypenny") and "Coming soon" in res["card"], f"her card doesn't say coming soon: {res}")
        need(res["below"] == "true" and res["smaller"] == "true", f"her card isn't smaller and under Donna and Pepper: {res}")
        need(float(res["greyed"].split("/")[0]) < 1 and res["greyed"].split("/")[1] == "1", f"her card isn't greyed out, or her yellow icon is: {res}")
        need(res["picked"].startswith("donna/quick inagents:false"), f"tapping her card picked her: {res}")
        need("Moneypenny" not in res["voices"], f"she has a voice in Settings: {res}")
        need(res["oncall"] == "hidden", f"her card shows during a call: {res}")
        # H126: the easter egg unlocks her only for this page; nothing is kept for the next time the app opens.
        need(res["oldsaved"] == "null", f"an old saved unlock is still kept: {res}")
        need(res["egg"] == "donna,pepper,moneypenny/null/null", f"twelve fast taps don't unlock her only for this page: {res}")
        return "Moneypenny: a smaller locked card under Donna and Pepper, coming soon, yellow M, not on the picker; brought in on Opus; the easter egg lasts only until the app closes"

    async def flow64(self) -> str:
        """F16: on a call the page can't be scrolled into white space. Since H140 (Modern, the one look) the agent
        picker and Moneypenny's card step aside on a call and her orb leads, then the status line, Mute and the
        round button, in that order (before H140, Classic kept their room). The scrolling is locked as long as the listening
        line fits on the screen. F20: after Past calls is opened and closed on a call, the call screen is back where
        it was, also when the phone's scrolling carries on a moment after the close. The real page in a headless
        browser. No Claude turns."""
        await self.ensure_server()
        page = http_get("/")[1].decode()
        need("html.calllock, html.calllock body { overflow:hidden; overscroll-behavior:none; }" in page,
             "the call page doesn't lock its scrolling on a call")
        need("body.oncall" not in page, "the picker and her card take no room on a call again (job 72), so the call screen sits too high")
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        # Phones and the Mac app draw scrollbars over the page; headless Chrome takes room for them, so it doesn't here.
        harness = r"""<style>html{scrollbar-width:none}</style><script>
setTimeout(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const over = () => document.scrollingElement.scrollHeight - innerHeight;
  const locked = () => getComputedStyle(document.documentElement).overflowY === 'hidden' && getComputedStyle(document.body).overflowY === 'hidden';
  const box = id => { const r = document.getElementById(id).getBoundingClientRect(); return [r.top, r.bottom, r.height]; };
  const card = document.querySelector('#soon .card');
  out.push('card:' + (card ? 'yes' : 'no'));
  const [, mb] = box('modes'), [ht] = box('modehint'), [st] = box('soon');
  out.push('idle:' + over());
  out.push('apart:' + (ht >= mb && st >= mb ? 'yes' : 'no'));
  out.push('sizes:' + Math.round(box('modes')[2]) + '/' + (card ? Math.round(card.getBoundingClientRect().height) : 0));
  calledHere = true; setState('connecting', ''); await wait(100); out.push('connecting:' + (locked() ? 'locked' : 'free'));
  setState('live', 'On the call'); setMuted(false); await wait(100);
  out.push('live:' + (locked() ? 'locked' : 'free'));
  out.push('room:' + (box('modes')[2] === 0 && box('soon')[2] === 0 ? 'aside' : 'kept'));
  out.push('order:' + (box('orbwrap')[0] < box('status')[0] && box('status')[0] < box('mute')[0] && box('mute')[0] < box('btn')[0] ? 'ok' : 'wrong'));
  out.push('btn:' + Math.round(box('btn')[0]) + ' mute:' + Math.round(box('mute')[0]));
  out.push('statusfits:' + (box('orbwrap')[1] <= innerHeight ? 'yes' : 'no'));
  out.push('orb:' + Math.round(box('orbwrap')[1]) + ' status:' + Math.round(box('status')[1]) + ' h:' + innerHeight);
  chatBtn.click(); await wait(200); out.push('chat:' + (locked() || over() <= 0 ? 'ok' : 'scrolls')); showChat(false); await wait(100);
  out.push('back:' + (locked() ? 'locked' : 'free'));
  // F20: Past calls opened and closed on a call; the phone's own scrolling carries on a moment after the close.
  const b0 = Math.round(box('btn')[0]), s0 = Math.round(box('status')[1]);
  showHistory(true); await wait(300); showHistory(false); scrollTo(0, 60); await wait(500);
  out.push('past:' + (scrollY === 0 && Math.round(box('btn')[0]) === b0 && Math.round(box('status')[1]) === s0 ? 'back' : 'moved'));
  // H144: the calendar on a call: its button in the dock, clear of the call's buttons; open, the page stays put and
  // the call's buttons stay clear of the dock and the sheet; closed, the call screen is back where it was.
  const cb = calBtn.getBoundingClientRect(), dk = document.getElementById('dock').getBoundingClientRect(), hb = btn.getBoundingClientRect();
  out.push('calbtn:' + (cb.width > 0 && cb.top >= dk.top - 1 && cb.bottom <= dk.bottom + 1 && hb.bottom <= dk.top + 1 ? 'ok' : 'wrong'));
  calBtn.click(); await wait(300);
  const sb = calEl.getBoundingClientRect();
  out.push('cal:' + (calOpen() && (locked() || over() <= 0) && sb.bottom <= box('mute')[0] + 1 && box('btn')[1] <= dk.top + 1 ? 'ok' : 'wrong'));
  showCal(false); scrollTo(0, 60); await wait(500);
  out.push('calback:' + (scrollY === 0 && Math.round(box('btn')[0]) === b0 && Math.round(box('status')[1]) === s0 ? 'back' : 'moved'));
  cleanup('Call ended'); await wait(200); out.push('after:' + over()); out.push('afterlock:' + (locked() ? 'locked' : 'free'));
  const pre = document.createElement('pre'); pre.id = 'f16'; pre.textContent = 'F16RESULT ' + out.join(' | ') + ' END'; document.body.append(pre);
}, 1500);
</script>"""
        f = self.tmp / "f16.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1).replace("<head>", f'<head><base href="{TEST_URL.rstrip("/")}/">', 1))
        fa = self.tmp / "f16app.html"  # the desktop app loads the page with ?app
        fa.write_text(f.read_text().replace('new URLSearchParams(location.search).has("app")', "true", 1))
        # The last field: whether the status line fits there on a call, so the page locks.
        sizes = [("iPhone 13 in Safari", "390,664", f, True), ("iPhone 13 from the home screen", "390,844", f, True),
                 ("a small phone in Safari", "375,553", f, False), ("the desktop app", "1180,780", fa, True)]
        seen = []
        for name, size, page_file, fits in sizes:
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []),
                                              f"--user-data-dir={self.tmp / 'f16-profile'}",
                                              "--disable-web-security", f"--window-size={size}", "--virtual-time-budget=8000", "--dump-dom", page_file.as_uri()], timeout=60)
            mm = re.search(r'<pre id="f16">F16RESULT (.*?) END</pre>', r.stdout)
            need(mm, f"{name}: the call page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
            res = dict(part.split(":", 1) for part in mm.group(1).replace(" mute:", " | mute:").replace(" status:", " | status:").replace(" h:", " | h:").split(" | "))
            say(f"   {name} ({size}): {mm.group(1)}")
            need(res["card"] == "yes", f"{name}: Moneypenny's card isn't on the page, so the test proves nothing: {res}")
            need(int(res["idle"]) <= 0 and int(res["after"]) <= 0, f"{name}: the page scrolls past the screen before or after a call: {res}")
            need(res["apart"] == "yes", f"{name}: the hint or her card overlaps Donna and Pepper: {res}")
            need(res["room"] == "aside" and res["order"] == "ok", f"{name}: on a call the picker or her card still takes room, or her orb, the status line, Mute and the button aren't in that order (H140): {res}")
            need(res["afterlock"] == "free", f"{name}: the page stays locked after the call: {res}")
            need(res["chat"] == "ok", f"{name}: with the chat open the page scrolls: {res}")
            if fits:
                need(res["statusfits"] == "yes", f"{name}: the listening line doesn't fit on a call: {res}")
                for when in ("connecting", "live", "back"):
                    need(res[when] == "locked", f"{name}: the page can be scrolled into white space on a call ({when}): {res}")
                need(res["past"] == "back", f"{name}: after Past calls opened and closed on a call, the call screen isn't back where it was (F20): {res}")
                need(res["calbtn"] == "ok" and res["cal"] == "ok" and res["calback"] == "back",
                     f"{name}: the calendar on a call (H144) isn't in the dock, scrolls the page, covers the call's buttons, or doesn't close back to the same place: {res}")
            else:
                # Off a Mac the fonts are a pixel smaller, so here it may just fit; then it's locked, rightly.
                need(res["live"] == "free" or res["statusfits"] == "yes", f"{name}: the listening line is off the screen and can't be scrolled to: {res}")
            seen.append(res["sizes"])
        # H140: Modern draws Donna and Pepper a little tighter on a short screen (under 700 high), on purpose; her card stays the same.
        need(len({s.split("/")[1] for s in seen[:2]}) == 1, f"her card looks different between the iPhone 13 sizes: {seen}")
        return "on a call her orb leads and the picker steps aside (H140), the page can't be scrolled and Past calls closes back to the same place (iPhone 13 Safari and home screen, desktop app); a small phone still scrolls to its listening line; the calendar opens on a call above the call's buttons and closes back to the same place (H144)"

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
        (ws / "HQ" / "agents").mkdir(parents=True)
        (ws / "HQ" / "agents" / "agents.json").write_text(json.dumps([
            {"id": "donna", "personality": "Test personality.", "model": "evil; rm"},
            {"id": "coach", "name": "Coach", "load": "deep", "speciality": "Life coaching"},
            {"id": "pepper", "hidden": True},
            {"id": "../x", "name": "Bad", "load": "quick"}, {"id": "noload", "name": "No load"}, "junk"]))
        (ws / "HQ" / "agents" / "coach.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        mine = agents.load(ws)
        need([a["id"] for a in mine] == ["donna", "pepper", "moneypenny", "coach"], f"the workspace's agents aren't read right: {[a['id'] for a in mine]}")
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
  out.push('voices:' + [...document.querySelectorAll('#voices .row span')].map(s => s.firstChild.textContent).join(','));
  out.push('defaults:' + voiceFor('donna') + '/' + voiceFor('pepper'));
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
        need(res["defaults"] == "af_bella/af_heart", f"a fresh install doesn't give Donna Bella and Pepper Heart (H66): {res}")
        need(res["sent"] == "bf_emma/af_bella", f"Pepper's voice isn't her own: {res}")
        need(res["inapp"] == "none", f"the status button still shows inside the app: {res}")
        return "Donna left, Pepper right; Voice Donna Paulsen and Voice Pepper Potts, each her own; no waiting lines; no status button inside the app"

    async def flow51(self) -> str:
        """H51: the usage a call gets back. A made-up session feeds the brain's reader a rate limit
        event, then a turn; usage-live.json is redirected to a scratch copy, never the real one."""
        from claude_agent_sdk import RateLimitEvent, RateLimitInfo, ResultMessage, StreamEvent
        from pipeline import make_brain
        import brain as brain_
        import usagelive
        tmp = Path(tempfile.mkdtemp(prefix="h51-", dir=config.SCRATCH))
        real = usagelive.LIVE
        usagelive.LIVE = str(tmp / "usage-live.json")
        try:
            reset = int(time.time()) + 3600
            ev = lambda raw: RateLimitEvent(rate_limit_info=RateLimitInfo(status="allowed", raw=raw), uuid="u", session_id="s")
            good = ev({"status": "allowed", "unifiedWindows": {"five_hour": {"utilization": 0.23, "resetsAt": reset},
                                                               "seven_day": {"utilization": 0.61, "resetsAt": reset * 1000}}})

            class FakeClient:
                async def receive_messages(self):
                    yield ev({"status": "allowed", "unifiedWindows": "broken"})  # a broken one: skipped, no crash
                    yield good
                    yield StreamEvent(uuid="x", session_id="s", event={"type": "content_block_delta",
                                      "delta": {"type": "text_delta", "text": "Hi."}}, parent_tool_use_id=None)
                    yield ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
                                        num_turns=1, session_id="s")
                    await asyncio.sleep(3600)

                async def query(self, text):
                    pass

            # A Free call's brain and a normal call's brain are the same class: both save.
            free = make_brain(config.MODEL_ALIASES["sonnet"], None, cwd=config.FREE_DIR, free=True)
            need(isinstance(free, brain_.ClaudeBrain), "a Free call doesn't use the call's brain")
            b = brain_.ClaudeBrain(model="haiku", system_prompt="", cwd=tmp / "cwd")
            b._client = FakeClient()
            b._reader = asyncio.create_task(b._read_forever())
            got = [p async for p in b.ask("hello")]
            b._reader.cancel()
            need(got == ["Hi."], f"the turn didn't get just its answer: {got}")
            need(b.rate_limit_events == 2, f"the brain counted {b.rate_limit_events} usage readings, not 2")
            live = json.loads(Path(usagelive.LIVE).read_text())
            need(live.get("by") == "call", f"not marked as from a call: {live}")
            need(live["rate_limits"] == {"five_hour": {"used_percentage": 23.0, "resets_at": reset},
                                         "seven_day": {"used_percentage": 61.0, "resets_at": reset}},
                 f"not the mail check's shape: {live['rate_limits']}")
            need(set(live) == {"savedAt", "rate_limits", "by"}, f"more than the numbers was saved: {sorted(live)}")
            # The mail check's stream writes the same shape through the same code.
            stream = json.dumps({"type": "rate_limit_event", "rate_limit_info": {"unifiedWindows": good.rate_limit_info.raw["unifiedWindows"]}})
            r = subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(ROOT / 'routine')!r}); import usagelive; "
                                f"usagelive.LIVE = {str(tmp / 'mail.json')!r}; sys.argv=['x']; "
                                f"exec(open({str(ROOT / 'routine/stream-usage.py')!r}).read())"],
                               input=stream + "\n", capture_output=True, text=True, timeout=30)
            mail = json.loads((tmp / "mail.json").read_text())
            need(mail["rate_limits"] == live["rate_limits"] and mail["by"] == "mail check", f"the mail check saves it differently: {r.stdout}{r.stderr}")
            # The usage check names the call as the source.
            src = (ROOT / "routine/usage-check.py").read_text()
            need('"call": "a call"' in src, "the usage check doesn't name a call as the source")
        finally:
            usagelive.LIVE = real
            shutil.rmtree(tmp, ignore_errors=True)
        return "saved from the call's session as from a call, same shape and code as the mail check; never in a turn; a broken one skipped; Free too"

    async def flow52(self) -> str:
        """H49: the space bar in the desktop app. No Claude turns: the real call page in a headless browser, with a
        fake live call. Inside the app (?app) a short press mutes and unmutes, a hold is push to talk (green, key
        repeats ignored) and letting go sends (yellow, muted); not before a call, not while typing in the text box,
        not inside the Hang up question. Outside the app (the browser, the phone) space does nothing."""
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const key = (type, el, repeat) => (el || document.body).dispatchEvent(new KeyboardEvent(type, { code: "Space", key: " ", repeat: !!repeat, bubbles: true, cancelable: true }));
  const server = st => onServerMessage({ data: JSON.stringify({ type: "hq-state", state: st }) });  // as on a real call
  const look = () => (muted ? "muted" : "open") + "/" + (muteBtn.classList.contains("talk") ? "talk" : muteBtn.classList.contains("transcribing") ? "yellow" : "-");
  key("keydown"); await wait(50); key("keyup"); await wait(50);
  out.push("before:" + look() + "/" + pressId);
  setState("live", "On the call");
  key("keydown"); await wait(80); key("keyup"); await wait(50);
  out.push("tap1:" + look());
  key("keydown"); await wait(80); key("keyup"); await wait(50);
  out.push("tap2:" + look());
  key("keydown");
  for (let i = 0; i < 8; i++) { await wait(120); key("keydown", null, true); if (i === 4) server("hearing"); }
  out.push("hold:" + look() + "/" + muteBtn.textContent);
  key("keyup"); await wait(80);
  out.push("release:" + look());
  setMuted(false); setTranscribing(false);
  const t = document.getElementById("typein");
  t.focus(); const free = key("keydown", t); await wait(500); key("keyup", t); await wait(50);
  out.push("typing:" + look() + "/" + (free ? "typed" : "BLOCKED"));
  const hb = document.querySelector("#hangask button");
  const freeQ = key("keydown", hb); await wait(80); key("keyup", hb); await wait(50);
  out.push("question:" + look() + "/" + (freeQ ? "button" : "BLOCKED"));
  out.push("title:" + (muteBtn.title ? "yes" : "no"));
  const pre = document.createElement("pre"); pre.id = "h49"; pre.textContent = "H49RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f = self.tmp / "h49.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1))
        got = {}
        for where, q in (("app", "?app=1"), ("browser", "")):
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", "--autoplay-policy=no-user-gesture-required",
                                              f"--user-data-dir={self.tmp / ('h49-' + where)}", "--virtual-time-budget=20000", "--dump-dom", f.as_uri() + q], timeout=90)
            m = re.search(r'<pre id="h49">H49RESULT (.*?) END</pre>', r.stdout)
            need(m, f"the page test didn't finish ({where}): {(r.stderr or r.stdout)[-300:]!r}")
            say(f"   {where}: {m.group(1)}")
            got[where] = dict(part.split(":", 1) for part in m.group(1).split(" | "))
        a, b = got["app"], got["browser"]
        need(a["before"] == "open/-/null", f"space did something before a call: {a}")
        need(a["tap1"] == "muted/-" and a["tap2"] == "open/-", f"a short press doesn't mute and unmute: {a}")
        need(a["hold"] == "open/talk/Talking…", f"holding space isn't push to talk: {a}")
        need(a["release"] == "muted/yellow", f"letting go of space doesn't send (yellow, muted): {a}")
        need(a["typing"] == "open/-/typed", f"space while typing in the text box was taken: {a}")
        need(a["question"] == "open/-/button", f"space inside the Hang up question was taken: {a}")
        need(a["title"] == "yes", f"the talk button doesn't say what space does in the app: {a}")
        need(b["tap1"] == "open/-" and b["hold"].startswith("open/-") and b["release"] == "open/-" and b["title"] == "no",
             f"space does something outside the app: {b}")
        src = (ROOT / "desktop/HQ.swift").read_text()
        need("makeFirstResponder(call)" in src, "the app doesn't give the call page the keys")
        return "in the app: tap mutes and unmutes, hold talks (repeats ignored), letting go sends; not before a call, not while typing, not in a question; outside the app nothing"

    async def flow53(self) -> str:
        """H57: a button for every past call. No Claude turns: made-up transcripts in the test server's own calls
        folder, the server's /api/calls read only, and the real call page in a headless browser."""
        import transcript
        calls = self.server.calls
        calls.mkdir(parents=True, exist_ok=True)
        head = lambda agent: "# Call\n\n> **Private.**\n\nStarted 10:00:00 · " + (f"agent {agent} · " if agent else "") + "brain test\n\n"
        (calls / "2099-12-30-0900.md").write_text(head("") + f"- 09:00:05 **{config.USER_LABEL}:** An old one.\n- 09:00:07 **Jarvis:** Old answer.\n")
        (calls / "2099-12-31-2300.md").write_text(head("Donna") + (
            "- 23:00:01 *filler: Hi there!*\n"
            "- 23:00:02 *call: connected; connectors: none*\n"
            f"- 23:00:05 **{config.USER_LABEL}:** What's on tomorrow? *(typed)*\n"
            "- 23:00:06 `Read challenges.md` · done (reading in the folder)\n"
            "- 23:00:09 **HQ:** Only the dentist at ten.\n"
            f"- 23:00:12 **{config.USER_LABEL}:** Shoes. *(cut in)* *(cancelled)*\n\nEnded 23:00:20\n"))
        (calls / "2099-12-31-2300-2.md").write_text(head("Pepper") + f"- 23:00:40 **{config.USER_LABEL}:** Second in the same minute.\n")
        (calls / "2099-12-31-2310.md").write_text(head("Pepper") + "- 23:10:01 *filler: Hi!*\n- 23:10:02 *call: The caller hung up*\n")
        got = transcript.list_calls(calls)
        names = [c["name"] for c in got]
        need(names[:3] == ["2099-12-31-2300-2", "2099-12-31-2300", "2099-12-30-0900"] and "2099-12-31-2310" not in names,
             f"the list isn't newest first, or kept a call where nothing was said: {names}")
        need(got[1]["agent"] == "Donna" and got[1]["time"] == "23:00" and got[1]["date"] == "2099-12-31" and got[1]["said"] == 3
             and got[2]["agent"] == "", f"date, time, agent or lines are wrong: {got[:3]}")
        one = transcript.read_call("2099-12-31-2300", calls)
        need(one and [l["who"] for l in one["lines"]] == ["filler", "user", "hq", "user"] and one["lines"][3]["cancelled"],
             f"one call isn't read as the chat shows it: {one}")
        for bad in ("../roadmap", "2099-12-31-2300.md", "", "x", "2099-12-31-2300/../../me"):
            need(transcript.read_call(bad, calls) is None, f"a name that isn't a saved call's was read: {bad!r}")
        await self.ensure_server()
        before = sorted(p.name for p in calls.iterdir())
        code, body, ctype = http_get("/api/calls")
        need(code == 200 and "json" in ctype, f"/api/calls did not answer ({code}, {ctype})")
        listed = json.loads(body)["calls"]
        need([c["name"] for c in listed][:3] == names[:3], f"/api/calls gave {str(listed)[:200]}")
        code, body, _ = http_get("/api/calls/2099-12-31-2300")
        need(code == 200 and len(json.loads(body)["lines"]) == 4, f"/api/calls/<name> gave {code} {body[:200]!r}")
        code, _, _ = http_get("/api/calls/..%2Froadmap")
        need(code == 404, f"a name that isn't a saved call's didn't get a 404 ({code})")
        need(sorted(p.name for p in calls.iterdir()) == before, "asking for the calls changed the calls folder")
        one_json = json.dumps(one)
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const shown = el => getComputedStyle(el).display !== "none" && el.getBoundingClientRect().width > 0;
  const voice = document.getElementById("voicebtn");
  // H140: in the dock, before her voice button.
  const placed = () => ((a, b) => shown(a) && a.parentElement.id === "dock" && b.parentElement.id === "dock" && a.compareDocumentPosition(b) === Node.DOCUMENT_POSITION_FOLLOWING)(histBtn, voice);
  await wait(300);
  out.push("start:" + (placed() ? "ok" : "WRONG"));
  histBtn.click(); await wait(400);
  const rows = histList.querySelectorAll("button");
  out.push("list:" + (histOpen() && rows.length === 3 && rows[1].textContent.includes("23:00") && rows[1].textContent.includes("Donna")
    && histList.querySelector(".day") ? "ok" : "WRONG " + rows.length + " " + histList.textContent.slice(0, 80)));
  rows[1].click(); await wait(400);
  const msgs = histLog.querySelectorAll(".msg");
  out.push("call:" + (histEl.classList.contains("reading") && shown(histLog) && !shown(histList) && msgs.length === 4
    && histLog.querySelectorAll(".msg.me.cancelled").length === 1 && histTitle.textContent.startsWith("Donna · ")
    && !histLog.textContent.includes("challenges.md") && !histLog.textContent.includes("connected") ? "ok" : "WRONG " + msgs.length + " " + histTitle.textContent));
  document.getElementById("histback").click(); await wait(400);
  out.push("back:" + (!histEl.classList.contains("reading") && shown(histList) && histList.querySelectorAll("button").length === 3 ? "ok" : "WRONG"));
  chatBtn.click(); await wait(300);
  out.push("onesheet:" + (chatOpen() && !histOpen() ? "ok" : "WRONG"));
  histBtn.click(); await wait(300);
  out.push("onesheet2:" + (histOpen() && !chatOpen() ? "ok" : "WRONG"));
  document.getElementById("histclose").click(); await wait(200);
  out.push("close:" + (!histOpen() && histBtn.getAttribute("aria-expanded") === "false" ? "ok" : "WRONG"));
  calledHere = true; setState("live", "On the call");
  out.push("live:" + (shown(histBtn) && shown(chatBtn) ? "ok" : "MISSING"));
  histBtn.click(); await wait(300);
  out.push("livesheet:" + (histOpen() && document.body.classList.contains("chatting") ? "ok" : "WRONG"));
  showHistory(false);
  cleanup("Call ended");
  out.push("after:" + (placed() ? "ok" : "MISSING"));
  stubEmpty = true; histBtn.click(); await wait(300);
  out.push("empty:" + (histList.querySelector(".empty") && histList.querySelector(".empty").textContent === "No calls yet" ? "ok" : "WRONG"));
  const pre = document.createElement("pre"); pre.id = "h57"; pre.textContent = "H57RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        stub = ("<script>var stubEmpty = false; const CALLS = " + json.dumps({"calls": listed[:3]}) + ", ONE = " + one_json + """;
window.fetch = async (url) => ({ ok: true, json: async () => (String(url).startsWith("api/calls/") ? ONE
  : String(url) === "api/calls" ? (stubEmpty ? { calls: [] } : CALLS) : { lines: [] }) });</script>""")
        f = self.tmp / "h57.html"
        f.write_text(page.replace("<style>", stub + "<style>", 1).replace("</body>", harness + "</body>", 1))
        for where, q in (("phone", ""), ("app", "?app=1")):
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []), "--window-size=390,844",
                                              f"--user-data-dir={self.tmp / ('h57-' + where)}", "--virtual-time-budget=20000", "--dump-dom", f.as_uri() + q], timeout=120)
            m = re.search(r'<pre id="h57">H57RESULT (.*?) END</pre>', r.stdout)
            need(m, f"the page test didn't finish ({where}): {(r.stderr or r.stdout)[-300:]!r}")
            res = m.group(1)
            say(f"   {where}: {res}")
            need(all(part.endswith(":ok") for part in res.split(" | ")), f"the past-calls button or sheet isn't right ({where}): {res}")
        return ("every saved call newest first with date, time and agent, one call read by name only, served read only; "
                "the button in the dock before the voice button before, during and after a call, in the browser and the app; list, call, Back, Close")
    async def flow83(self) -> str:
        """H105, no Claude: the notes button. The notes file itself (notes.py on a throwaway copy), the call server's
        /api/notes on the test server's own notes file (the workspace's is never touched), and the real call page in a
        headless browser, phone and desktop app: the button in the dock before Past calls, before, during and after a call;
        the sheet, adding a note, clearing one and all. Since H117 just text: no paper and no doodle endpoints, a
        picture saved before is left alone, and the note field grows with what's typed like the chat's."""
        import notes as _notes
        real = _notes.NOTES
        real_before = real.read_bytes() if real.exists() else None
        real_pic = real.with_name("notes-doodle.png")
        pic_before = real_pic.stat().st_mtime if real_pic.exists() else None
        f = self.tmp / "h105" / "HQ" / "notes.md"
        need(_notes.read(f) == {"items": []}, "a missing notes file isn't read as no notes")
        a = _notes.add("  Call the dentist  ", f)
        b = _notes.add("Two lines\nsecond one", f)
        need(a and a["text"] == "Call the dentist" and len(a["when"]) == 19 and b and b["text"] == "Two lines\nsecond one",
             f"adding notes went wrong: {a} {b}")
        need(_notes.add("   ", f) is None, "an empty note was added")
        text = f.read_text()
        need(text.startswith("# Quick notes") and "## Notes" in text and "Two lines<br>second one" in text
             and text.index("Call the dentist") < text.index("Two lines"), f"the notes file isn't as a call reads it: {text!r}")
        f.write_text(text.rstrip("\n") + "\n- Written by a call\n\n## Later\n\nkept as it is\n")
        got = _notes.items(f)
        need([i["text"] for i in got] == ["Call the dentist", "Two lines\nsecond one", "Written by a call"] and got[2]["when"] == "",
             f"a line written by hand isn't read as a note: {got}")
        c = _notes.add("After the hand one", f)
        need(_notes.items(f)[3]["text"] == "After the hand one" and "kept as it is" in f.read_text()
             and f.read_text().index("After the hand one") < f.read_text().index("## Later"), "a new note didn't go at the end of Notes")
        need(_notes.clear(got[1]["id"], f) and not _notes.clear("nope", f), "clearing one note by its id went wrong")
        need([i["text"] for i in _notes.items(f)] == ["Call the dentist", "Written by a call", "After the hand one"], "the wrong note was cleared")
        need(_notes.clear_all(f) == 3 and _notes.items(f) == [] and "kept as it is" in f.read_text() and "# Quick notes" in f.read_text(),
             "clear all didn't keep the rest of the file")
        need(not hasattr(_notes, "save_doodle") and not hasattr(_notes, "doodle_path"), "the doodle is still in the notes code (H117)")

        await self.ensure_server()
        def post(path, body, ctype="application/json", hq="notes"):
            req = urllib.request.Request(TEST_URL + path, data=body, method="POST", headers={"content-type": ctype, **({"x-hq": hq} if hq else {})})
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                return e.code, None
        sf = self.server.notes
        code, body, _ = http_get("/api/notes")
        need(code == 200 and json.loads(body)["items"] == [], f"/api/notes didn't answer with no notes ({code} {body[:100]!r})")
        need(post("/api/notes", b'{"add": "From elsewhere"}', hq="")[0] == 403 and not sf.exists(), "a change without the page's header was let in")
        code, d = post("/api/notes", json.dumps({"add": "From the page"}).encode())
        need(code == 200 and [i["text"] for i in d["items"]] == ["From the page"] and "From the page" in sf.read_text(),
             f"adding through the server went wrong ({code} {d})")
        need(post("/api/notes", b'{"add": "  "}')[0] == 400 and post("/api/notes", b'{"clear": "nope"}')[0] == 404
             and post("/api/notes", b'[]')[0] == 400, "a bad change wasn't refused")
        old_pic = sf.with_name("notes-doodle.png")  # H117: a picture saved before stays where it is, unread
        old_pic.write_bytes(b"\x89PNG\r\n\x1a\nold")
        code, d = post("/api/notes", json.dumps({"clear": d["items"][0]["id"]}).encode())
        need(code == 200 and d.get("items") == [], f"clearing through the server went wrong ({code} {d})")
        need(post("/api/notes/doodle", b"\x89PNG\r\n\x1a\nnew", "image/png")[0] != 200 and http_get("/api/notes/doodle")[0] != 200
             and old_pic.read_bytes() == b"\x89PNG\r\n\x1a\nold", "the doodle endpoints are still there, or the old picture was touched (H117)")
        old_pic.unlink()

        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        stub = r"""<script>
var NOTES = [{ id: "a1", when: "2099-12-31 09:00:00", text: "Ask about the dentist" }, { id: "b2", when: "", text: "Two\nlines" }],
    SENT = [], nextId = 1;
window.fetch = async (url, opt) => {
  url = String(url); const m = (opt && opt.method) || "GET", hq = opt && opt.headers && opt.headers["x-hq"];
  const answer = () => ({ items: NOTES.slice() });
  if (url === "api/notes" && m === "POST") {
    const b = JSON.parse(opt.body); SENT.push((hq === "notes" ? "" : "NOHEADER ") + Object.keys(b)[0]);
    if (b.add) NOTES.push({ id: "n" + (nextId++), when: "2099-12-31 10:00:00", text: b.add });
    if (b.clear) NOTES = NOTES.filter(n => n.id !== b.clear);
    if (b.clear_all) NOTES = [];
    return { ok: true, json: async () => answer() };
  }
  if (url === "api/notes") return { ok: true, json: async () => answer() };
  return { ok: true, json: async () => ({ lines: [], calls: [] }) };
};</script>"""
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const shown = el => getComputedStyle(el).display !== "none" && el.getBoundingClientRect().width > 0;
  // H140: in the dock, before Past calls.
  const placed = () => ((a, b) => shown(a) && a.parentElement.id === "dock" && b.parentElement.id === "dock" && a.compareDocumentPosition(b) === Node.DOCUMENT_POSITION_FOLLOWING)(notesBtn, histBtn);
  await wait(300);
  out.push("start:" + (placed() ? "ok" : "WRONG"));
  notesBtn.click(); await wait(400);
  const rows = () => notesList.querySelectorAll(".note");
  out.push("open:" + (notesOpen() && notesBtn.getAttribute("aria-expanded") === "true" && rows().length === 2
    && rows()[0].textContent.includes("Ask about the dentist") && rows()[0].textContent.includes("2099-12-31 09:00")
    && shown(notesIn) && !notesEl.querySelector("canvas") && !document.getElementById("doodle") ? "ok" : "WRONG " + rows().length));
  const lastIn = notesForm.getBoundingClientRect(), nb = notesBtn.getBoundingClientRect();
  out.push("clear-of-buttons:" + (lastIn.bottom <= nb.top + 1 ? "ok" : "WRONG " + lastIn.bottom + " " + nb.top));
  const one = notesIn.getBoundingClientRect().height;
  notesIn.value = "Line one\nline two\nline three"; notesIn.dispatchEvent(new Event("input")); await wait(50);
  const three = notesIn.getBoundingClientRect().height;
  notesIn.value = Array.from({ length: 40 }, (_, i) => "line " + i).join("\n"); notesIn.dispatchEvent(new Event("input")); await wait(50);
  const most = notesIn.getBoundingClientRect().height, cap = parseFloat(getComputedStyle(notesIn).maxHeight);
  out.push("grows:" + (Math.abs(one - 46) < 2 && three > one + 30 && most > three && most <= cap + 1 && getComputedStyle(notesIn).overflowY === "auto"
    ? "ok" : "WRONG " + [one, three, most, cap]));
  notesIn.value = "Buy tie wraps"; notesIn.dispatchEvent(new Event("input"));
  notesForm.requestSubmit(); await wait(300);
  out.push("add:" + (rows().length === 3 && rows()[2].textContent.includes("Buy tie wraps") && notesIn.value === "" && SENT.includes("add")
    && Math.abs(notesIn.getBoundingClientRect().height - 46) < 2 ? "ok" : "WRONG " + SENT + " " + notesIn.getBoundingClientRect().height));
  rows()[0].querySelector(".clr").click(); await wait(300);
  out.push("clearone:" + (rows().length === 2 && !notesList.textContent.includes("dentist") && SENT.includes("clear") ? "ok" : "WRONG"));
  notesAll.click(); await wait(100);
  out.push("allasks:" + (rows().length === 2 && notesAll.classList.contains("sure") && !SENT.includes("clear_all") ? "ok" : "WRONG"));
  notesAll.click(); await wait(300);
  out.push("all:" + (rows().length === 0 && notesList.textContent.includes("No notes yet") && notesAll.disabled ? "ok" : "WRONG"));
  out.push("header:" + (!SENT.some(x => x.startsWith("NOHEADER")) ? "ok" : "WRONG"));
  chatBtn.click(); await wait(300);
  out.push("onesheet:" + (chatOpen() && !notesOpen() ? "ok" : "WRONG"));
  notesBtn.click(); await wait(300);
  out.push("onesheet2:" + (notesOpen() && !chatOpen() ? "ok" : "WRONG"));
  histBtn.click(); await wait(300);
  out.push("onesheet3:" + (histOpen() && !notesOpen() ? "ok" : "WRONG"));
  showHistory(false);
  calledHere = true; setState("live", "On the call");
  out.push("live:" + (shown(notesBtn) ? "ok" : "MISSING"));
  notesBtn.click(); await wait(300);
  out.push("livesheet:" + (notesOpen() && document.body.classList.contains("chatting") ? "ok" : "WRONG"));
  document.getElementById("notesclose").click(); await wait(200);
  out.push("close:" + (!notesOpen() && notesBtn.getAttribute("aria-expanded") === "false" ? "ok" : "WRONG"));
  cleanup("Call ended");
  out.push("after:" + (placed() ? "ok" : "MISSING"));
  const pre = document.createElement("pre"); pre.id = "h105"; pre.textContent = "H105RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f2 = self.tmp / "h105.html"
        f2.write_text(page.replace("<style>", stub + "<style>", 1).replace("</body>", harness + "</body>", 1))
        for where, q in (("phone", ""), ("app", "?app=1")):
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []), "--window-size=390,844",
                                              f"--user-data-dir={self.tmp / ('h105-' + where)}", "--virtual-time-budget=20000", "--dump-dom", f2.as_uri() + q], timeout=120)
            m = re.search(r'<pre id="h105">H105RESULT (.*?) END</pre>', r.stdout)
            need(m, f"the page test didn't finish ({where}): {(r.stderr or r.stdout)[-300:]!r}")
            res = m.group(1)
            say(f"   {where}: {res}")
            need(all(part.endswith(":ok") for part in res.split(" | ")), f"the notes button or sheet isn't right ({where}): {res}")
        need((real.read_bytes() if real.exists() else None) == real_before
             and (real_pic.stat().st_mtime if real_pic.exists() else None) == pic_before, "the workspace's own notes were touched")
        return ("notes kept one line each in a throwaway notes file, a hand-written line read too, cleared one by one or all, just text "
                "(no doodle endpoints, an old picture left alone); the server's /api/notes only from the page; the button in the dock before Past calls "
                "before, during and after a call, phone and app: the sheet without paper, the note field growing and back after Add, add, "
                "clear, clear all on a second tap")

    async def flow91(self) -> str:
        """H101, no Claude: the calendar inside HQ. agenda.py with a stand-in for the read-only Claude run, the
        test server's /api/calendar on its own copy (the workspace's is never touched), the call's note, greeting
        and transcript line, and the real call page in a headless browser, phone and desktop app."""
        import agenda
        import transcript
        real = Path(os.path.join(agenda.hqpaths.DATA, "calendar.json"))
        real_before = real.read_bytes() if real.exists() else None
        need(not any(t in x for x in agenda.ALLOW for t in ("create", "update", "delete", "respond")) and
             all(agenda.TOOL + t in agenda.DENY for t in ("create_event", "update_event", "delete_event", "respond_to_event")),
             "the calendar read may write to the calendar")
        src = (APP / "agenda.py").read_text()
        need("--permission-mode\", \"dontAsk\"" in src and "--allowedTools" in src, "the calendar read isn't a dontAsk run with only its tools")
        d = self.tmp / "h101"
        d.mkdir(parents=True, exist_ok=True)
        big = Path.home() / ".claude" / f"hq-flow91-{os.getpid()}.txt"
        outside = d / "outside.txt"
        def stream(main_answer: str) -> str:
            cals = {"calendars": [{"id": "me@example.com", "summary": "me@example.com"},
                                  {"id": "work-calendar-id", "summary": "Work"}]}
            work = {"events": [
                {"id": "w1", "summary": "Dentist", "start": {"dateTime": "2099-01-02T10:00:00+01:00"}, "end": {"dateTime": "2099-01-02T10:30:00+01:00"},
                 "location": "Main street 1", "description": "Bring the card", "htmlLink": "https://x"},
                {"id": "w2", "summary": "Gone", "status": "cancelled", "start": {"dateTime": "2099-01-02T11:00:00+01:00"}},
                {"id": "w3", "summary": "Her lecture", "transparency": "transparent", "start": {"dateTime": "2099-01-01T09:00:00+01:00"},
                 "end": {"dateTime": "2099-01-01T11:00:00+01:00"}}]}
            lines = [
                {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": agenda.TOOL + "list_calendars", "input": {}}]}},
                {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": json.dumps(cals)}]}]}},
                {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t2", "name": agenda.TOOL + "list_events", "input": {"calendarId": "me@example.com"}},
                                                              {"type": "tool_use", "id": "t3", "name": agenda.TOOL + "list_events", "input": {"calendarId": "work-calendar-id"}}]}},
                {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t2", "content": main_answer}]}},
                {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t3", "content": json.dumps(work)}]}},
                {"type": "result", "result": "done"}]
            return "\n".join(json.dumps(l) for l in lines) + "\nnot json\n"
        mine = {"events": [{"id": "m1", "summary": "Birthday", "start": {"date": "2099-01-01"}, "end": {"date": "2099-01-02"}},
                           {"id": "m1", "summary": "Birthday", "start": {"date": "2099-01-01"}, "end": {"date": "2099-01-02"}}]}
        big.write_text(json.dumps(mine))
        fake = d / "stream.txt"
        fake.write_text(stream(f"<persisted-output>\nOutput too large (63KB). Full output saved to: {big}\n\nPreview: ..."))
        env_before = {k: os.environ.get(k) for k in ("HQ_CALENDAR_FILE", "HQ_CALENDAR_FAKE", "HQ_CALENDAR")}
        os.environ["HQ_CALENDAR_FILE"] = str(d / "calendar.json")
        os.environ["HQ_CALENDAR_FAKE"] = str(fake)
        os.environ.pop("HQ_CALENDAR", None)
        try:
            t0 = datetime(2099, 1, 1, 12, 0).timestamp()
            st = agenda.look(now=t0)
            ev = st.get("events") or []
            need(not st.get("error") and [e["title"] for e in ev] == ["Birthday", "Her lecture", "Dentist"],
                 f"the appointments weren't read as Google gave them: {st.get('error')} {[e['title'] for e in ev]}")
            need(not big.exists(), "the saved big answer wasn't read and removed")
            b, l, dn = ev
            need(b["all_day"] and b["calendar"] == "Main" and l["free"] and l["calendar"] == "Work" and dn["where"] == "Main street 1"
                 and dn["notes"] == "Bring the card" and not dn["all_day"] and len({e["id"] for e in ev}) == 3,
                 f"the appointments' details aren't right: {ev}")
            need([c["name"] for c in st["calendars"]] == ["Main", "Work"], f"the calendars aren't named right: {st['calendars']}")
            outside.write_text(json.dumps(mine))
            need(agenda._persisted(f"<persisted-output>\nFull output saved to: {outside}\n") .startswith("<persisted-output>")
                 and outside.exists(), "a file outside Claude Code's own folder was read")
            fake.write_text("")
            st2 = agenda.look(now=t0 + 60)
            need(st2.get("error") and [e["title"] for e in st2.get("events") or []] == ["Birthday", "Her lecture", "Dentist"]
                 and st2.get("looked") == st["looked"], f"a failed read didn't keep the last days with the error: {st2}")
            need(agenda.read(now=t0)["error"] and len(agenda.read(now=t0)["events"]) == 3, "the page doesn't get the last days and the error")
            need(len(agenda.read(now=datetime(2099, 1, 5, 12, 0).timestamp())["events"]) == 0,
                 "appointments from before this week aren't left out")
            need(len(agenda.read(now=datetime(2099, 1, 4, 12, 0).timestamp())["events"]) == 3,
                 "this week's past days aren't kept (H143)")
            s0 = {"looked": t0}
            need(not agenda.due(datetime(2099, 1, 1, 12, 30).timestamp(), s0) and agenda.due(datetime(2099, 1, 1, 13, 1).timestamp(), s0)
                 and not agenda.due(datetime(2099, 1, 2, 3, 0).timestamp(), s0) and not agenda.due(datetime(2099, 1, 1, 23, 30).timestamp(), s0),
                 "the hourly read isn't every hour in the day only")
            need(not agenda.due(datetime(2099, 1, 1, 14, 0).timestamp(), {"looked": t0, "running": datetime(2099, 1, 1, 13, 59).timestamp()}),
                 "a read was started while one runs")
            os.environ["HQ_CALENDAR"] = "0"
            need(not agenda.due(datetime(2099, 1, 1, 14, 0).timestamp(), s0) and not agenda.refresh(), "HQ_CALENDAR=0 doesn't switch it off")
            os.environ.pop("HQ_CALENDAR")
            # H153: a whole day as the connector gives it (midnight UTC) is its date, first on its day, and the list
            # is in time order, also a copy saved before the fix
            _, ev3 = agenda.events_from([(agenda.TOOL + "list_events", {"calendarId": "primary"}, {"events": [
                {"id": "a", "summary": "Late", "start": {"dateTime": "2099-01-02T21:00:00+01:00"}},
                {"id": "b", "summary": "A whole day", "start": {"date": "2099-01-02T00:00:00Z"}, "end": {"date": "2099-01-03T00:00:00Z"}},
                {"id": "c", "summary": "Sleep", "start": {"dateTime": "2099-01-02T00:00:00+01:00"}},
                {"id": "d", "summary": "Night call", "start": {"dateTime": "2099-01-02T01:00:00+01:00"}}]})])
            need([e["title"] for e in ev3] == ["A whole day", "Sleep", "Night call", "Late"] and ev3[0]["start"] == "2099-01-02"
                 and ev3[0]["end"] == "2099-01-03", f"a whole day or the order isn't right (H153): {[(e['title'], e['start']) for e in ev3]}")
            old = [{**ev3[3]}, {**ev3[0], "start": "2099-01-02T00:00:00Z", "end": "2099-01-03T00:00:00Z"}, {**ev3[2]}, {**ev3[1]}]
            agenda._write({"looked": t0, "events": old})
            rd3 = agenda.read(now=t0)["events"]
            need([e["title"] for e in rd3] == ["A whole day", "Sleep", "Night call", "Late"] and rd3[0]["start"] == "2099-01-02",
                 f"the page doesn't get the saved list in time order (H153): {[(e['title'], e['start']) for e in rd3]}")
            # H153: a write in the calendar (a call, Donna, planning) reads it again within the minute, at any hour,
            # once; a look that started after the write is enough, one that was running during it isn't
            import role as _role
            started, real_start, real_acting = [], agenda.start, _role.acting
            agenda.start = lambda t=None: started.append(t) or True
            try:
                night = datetime(2099, 1, 2, 3, 0).timestamp()
                agenda._write({"looked": night - 600})
                _role.acting = lambda: "backup"
                need(not agenda.changed("update_event", now=night - 5) and started == [] and agenda.changed_at() == night - 5,
                     "a write on the backup didn't leave the mark for the main, or read here")
                _role.acting = lambda: "main"
                need(agenda.changed("update_event", now=night) and started == [night] and agenda.changed_at() == night
                     and agenda.changed_file().parent == d, f"a write didn't ask for a read right away on the main: {started}")
                need(agenda.due(night + 30, {"looked": night - 600}), "a write in the calendar doesn't make a read due at night")
                need(not agenda.due(night + 90, {"looked": night - 600, "asked": night + 60}), "a read after the write isn't enough")
                need(not agenda.due(night + 30, {"looked": night - 600, "running": night - 10}), "a read was started while one runs")
                need(agenda.due(night + 120, {"looked": night - 10}), "a write while a read ran didn't ask for one more")
                import policy as _pol
                calls, real_changed = [], agenda.changed
                agenda.changed = lambda why="", now=None: calls.append(why) or True
                try:
                    pl = _pol.Policy(self.tmp)
                    pl.seen("mcp__claude_ai_Google_Calendar__update_event", {"id": "x"})
                    pl.seen("mcp__claude_ai_Google_Calendar__create_event", {"id": "y"})
                    pl.seen("mcp__claude_ai_Google_Calendar__list_events", {"events": []})
                    pl.seen("mcp__claude_ai_Gmail__create_draft", {})
                    _pol.Policy(self.tmp, dry_run=True).seen("mcp__claude_ai_Google_Calendar__delete_event", {})
                    need(calls == ["update_event", "create_event"], f"a call's or Donna's calendar write doesn't ask for a read: {calls}")
                finally:
                    agenda.changed = real_changed
                need('agenda.changed("planning")' in (APP / "planning.py").read_text(),
                     "an X's move doesn't ask for a read right away")
            finally:
                agenda.start, _role.acting = real_start, real_acting
                agenda.changed_file().unlink(missing_ok=True)
            agenda._write(st2)
            note = agenda.call_note(dn, "Sam")
            need("<appointment>" in note and "Dentist" in note and "Main street 1" in note and "Bring the card" in note
                 and "read only" in note, f"the call's note isn't right: {note!r}")
            g = agenda.greetings({"title": "Dentist 🦷"}, "Sam")
            need(g and all("Dentist" in x and "Sam" in x and "🦷" not in x for x in g), f"the greeting doesn't name the appointment: {g}")
            tr = transcript.CallTranscript(d / "calls", model="test", agent="Pepper", about=agenda.when_line(dn))
            tr.user("Hello")
            head = tr.path.read_text()
            need("About the appointment: Dentist (" in head and transcript.read_call(tr.path.stem, d / "calls") is not None,
                 f"the transcript doesn't say which appointment, or can't be read back: {head!r}")
            csrc, bsrc = (APP / "call.py").read_text(), (APP / "bot.py").read_text()
            need("agenda.call_note(self.about" in csrc and "None if free or not isinstance(about, dict)" in csrc
                 and "None if free else _agenda.about(" in bsrc, "the call doesn't get the appointment, or gets it on Free")
        finally:
            for k, v in env_before.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            big.unlink(missing_ok=True)

        await self.ensure_server()
        sfile = Path(self.server.env["HQ_CALENDAR_FILE"])
        sfile.parent.mkdir(parents=True, exist_ok=True)
        now = time.time()
        sfile.write_text(json.dumps({"looked": now, "calendars": [], "events": [
            {"id": "s1", "title": "Soon", "start": datetime.fromtimestamp(now + 3600).astimezone().isoformat(), "end": "", "all_day": False}]}))
        code, body, _ = http_get("/api/calendar")
        got = json.loads(body) if code == 200 else {}
        need(code == 200 and [e["title"] for e in got.get("events", [])] == ["Soon"] and not got.get("looking"),
             f"/api/calendar didn't answer with the test copy ({code} {body[:120]!r})")
        Path(self.server.env["HQ_CALENDAR_FAKE"]).write_text(stream(json.dumps(mine)))
        code, body, _ = http_get("/api/calendar?fresh=1")
        need(code == 200 and not json.loads(body).get("looking"), "a fresh read was started though the last one is minutes old")
        sfile.write_text(json.dumps({"looked": now - 3600, "events": []}))
        code, body, _ = http_get("/api/calendar?fresh=1")
        need(code == 200, f"/api/calendar?fresh=1 failed ({code})")
        for _ in range(40):
            if [e["title"] for e in json.loads(http_get("/api/calendar")[1] or b"{}").get("events", [])][:1] == ["Birthday"]:
                break
            await asyncio.sleep(0.5)
        else:
            need(False, f"opening the calendar didn't read it again: {sfile.read_text()[:300]!r}")
        need((real.read_bytes() if real.exists() else None) == real_before, "the workspace's own calendar copy was touched")

        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        need("...(appt && !free ? { about: appt.id } : {})" in page, "the call's offer doesn't carry the appointment")
        stub = r"""<script>
var ASKED = [], T = new Date(); T.setHours(0, 0, 0, 0);
function at(days, h, m) { const d = new Date(T); d.setDate(d.getDate() + days); d.setHours(h, m || 0); return d.toISOString(); }
var EVENTS = [
  { id: "e1", title: "Shower and yoga", start: at(0, 23, 0), end: at(0, 23, 45), all_day: false, where: "", notes: "", calendar: "Main", free: false },
  { id: "e2", title: "Her lecture", start: at(1, 11), end: at(1, 12, 45), all_day: false, where: "Town hall", notes: "", calendar: "Family", free: true },
  { id: "e3", title: "Dentist", start: at(2, 10), end: at(2, 10, 30), all_day: false, where: "Main street 1", notes: "Bring the card", calendar: "Main", free: false }];
window.fetch = async (url, opt) => {
  url = String(url);
  if (url.startsWith("api/calendar")) { ASKED.push(url); return { ok: true, json: async () => ({ on: true, looked: Date.now() / 1000 - 120, looking: false, error: "", events: EVENTS }) }; }
  return { ok: true, json: async () => ({ lines: [], calls: [], items: [] }) };
};</script>"""
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const shown = el => getComputedStyle(el).display !== "none" && el.getBoundingClientRect().width > 0;
  const CALLED = []; call = function () { CALLED.push(aboutNext ? aboutNext.id : "none"); aboutNext = null; };
  // H140: in the dock, after the chat button.
  const placed = () => shown(calBtn) && ((a, b) => shown(a) && a.parentElement.id === "dock" && b.parentElement.id === "dock" && a.compareDocumentPosition(b) === Node.DOCUMENT_POSITION_FOLLOWING)(chatBtn, calBtn);
  await wait(300);
  out.push("start:" + (placed() ? "ok" : "WRONG"));
  calBtn.click(); await wait(400);
  const appts = () => calList.querySelectorAll(".appt"), days = () => calList.querySelectorAll(".day");
  out.push("open:" + (calOpen() && calBtn.getAttribute("aria-expanded") === "true" && appts().length === 3 && days().length === 3
    && days()[0].textContent.startsWith("Today") && days()[1].textContent.startsWith("Tomorrow")
    && appts()[1].classList.contains("free") && appts()[1].textContent.includes("Family") && ASKED[0] === "api/calendar?fresh=1"
    && calNote.textContent.includes("2 min ago") ? "ok" : "WRONG " + appts().length + " " + days().length + " " + ASKED));
  const lastRow = appts()[2].getBoundingClientRect(), cb = calBtn.getBoundingClientRect();
  out.push("clear-of-buttons:" + (calList.getBoundingClientRect().bottom <= cb.top + 1 ? "ok" : "WRONG"));
  appts()[2].click(); await wait(200);
  const go = document.getElementById("calgo");
  out.push("one:" + (calEl.classList.contains("reading") && calOne.textContent.includes("Dentist") && calOne.textContent.includes("Bring the card")
    && calOne.textContent.includes("Main street 1") && go && !go.disabled && shown(document.getElementById("calback")) ? "ok" : "WRONG"));
  document.getElementById("calback").click(); await wait(300);
  out.push("back:" + (!calEl.classList.contains("reading") && appts().length === 3 ? "ok" : "WRONG"));
  // H147: a swipe to the right goes back to the days; up and down, to the left, a short slow one or from a field don't.
  const reading = () => calEl.classList.contains("reading");
  const touch = (type, x, y, el) => { const t = new Touch({ identifier: 1, target: el, clientX: x, clientY: y });
    el.dispatchEvent(new TouchEvent(type, { bubbles: true, cancelable: true, touches: type === "touchend" ? [] : [t], targetTouches: type === "touchend" ? [] : [t], changedTouches: [t] })); };
  const swipe = async (dx, dy, ms, el) => { el = el || calOne.querySelector("h3"); touch("touchstart", 60, 300, el);
    for (let i = 1; i <= 6; i++) { await wait(ms / 6); touch("touchmove", 60 + dx * i / 6, 300 + dy * i / 6, el); } touch("touchend", 60 + dx, 300 + dy, el); await wait(400); };
  appts()[2].click(); await wait(200);
  await swipe(5, 160, 120);
  out.push("swipe-scroll:" + (reading() && !calOne.style.transform ? "ok" : "WRONG"));
  await swipe(-160, 0, 120);
  out.push("swipe-left:" + (reading() ? "ok" : "WRONG"));
  await swipe(40, 0, 600);
  out.push("swipe-short:" + (reading() && calOne.style.transform === "" ? "ok" : "WRONG " + calOne.style.transform));
  const field = document.createElement("textarea"); calOne.appendChild(field); field.focus();
  await swipe(200, 0, 120, field);
  out.push("swipe-field:" + (reading() ? "ok" : "WRONG")); field.blur(); field.remove();
  await swipe(160, 8, 120);
  out.push("swipe-back:" + (!reading() && appts().length === 3 && calTitle.textContent === "Calendar" && !calOne.style.transform ? "ok" : "WRONG"));
  const wheel = async (dx, dy) => { for (let i = 0; i < 6; i++) { calOne.dispatchEvent(new WheelEvent("wheel", { bubbles: true, cancelable: true, deltaX: dx, deltaY: dy })); await wait(16); } await wait(500); };
  appts()[2].click(); await wait(200);
  await wheel(-2, 40);
  out.push("pad-scroll:" + (reading() ? "ok" : "WRONG"));
  await wheel(-8, 0);
  out.push("pad-short:" + (reading() && !calOne.style.transform ? "ok" : "WRONG"));
  await wheel(-40, 0);
  out.push("pad-back:" + (!reading() && appts().length === 3 ? "ok" : "WRONG"));
  await wheel(-40, 0);
  out.push("pad-days-stay:" + (calOpen() && !reading() ? "ok" : "WRONG"));
  agent = "pepper"; showMode();  // F30: whoever is picked, an appointment is called about with the agenda's agent
  appts()[2].click(); await wait(100);
  out.push("label:" + (document.getElementById("calgo").textContent === "Call Donna about this" ? "ok" : "WRONG " + document.getElementById("calgo").textContent));
  document.getElementById("calgo").click(); await wait(100);
  out.push("call:" + (CALLED.join() === "e3" && agent === "donna" && !calOpen() ? "ok" : "WRONG " + CALLED + " " + agent));
  free = true; calBtn.click(); await wait(300); appts()[0].click(); await wait(100);
  out.push("free:" + (document.getElementById("calgo").disabled && calOne.textContent.includes("Free is on") ? "ok" : "WRONG"));
  document.getElementById("calgo").click(); await wait(50);
  out.push("freecall:" + (CALLED.length === 1 ? "ok" : "WRONG")); free = false;
  chatBtn.click(); await wait(300);
  out.push("onesheet:" + (chatOpen() && !calOpen() ? "ok" : "WRONG"));
  calBtn.click(); await wait(300);
  out.push("onesheet2:" + (calOpen() && !chatOpen() ? "ok" : "WRONG"));
  notesBtn.click(); await wait(300);
  out.push("onesheet3:" + (notesOpen() && !calOpen() ? "ok" : "WRONG"));
  showNotes(false); calBtn.click(); await wait(300);
  // H144: on a call the button stays, next to the call's Mic button, and an open sheet stays open; the call goes on.
  calledHere = true; setState("live", "On the call"); await wait(200);
  const tracks = [], stopped = []; stream = { getAudioTracks: () => tracks, getTracks: () => tracks };
  tracks.push({ enabled: true, stop() { stopped.push(1); } });
  out.push("live:" + (placed() && shown(devBtn) && calOpen() && appts().length === 3 && document.body.classList.contains("chatting") ? "ok" : "WRONG"));
  const sb = calEl.getBoundingClientRect(), hb = btn.getBoundingClientRect(), mb = muteBtn.getBoundingClientRect(), db = document.getElementById("dock").getBoundingClientRect();
  out.push("call-buttons-free:" + (shown(btn) && shown(muteBtn) && sb.bottom <= Math.min(hb.top, mb.top) + 1 && hb.bottom <= db.top + 1 ? "ok" : "WRONG " + [sb.bottom, mb.top, hb.top, hb.bottom, db.top].map(Math.round)));
  appts()[2].click(); await wait(200);
  out.push("oncall-one:" + (document.getElementById("calgo").disabled && document.getElementById("calbusy") && calOne.textContent.includes("Bring the card") ? "ok" : "WRONG"));
  document.getElementById("calgo").click(); await wait(50);
  out.push("oncall-nocall:" + (CALLED.length === 1 && state === "live" && calOpen() ? "ok" : "WRONG " + CALLED + " " + state));
  document.getElementById("calback").click(); await wait(200);
  devBtn.click(); await wait(200);
  out.push("mic-sheet:" + (setEl.classList.contains("open") && !calOpen() ? "ok" : "WRONG"));
  calBtn.click(); await wait(300);
  out.push("cal-again:" + (calOpen() && !setEl.classList.contains("open") ? "ok" : "WRONG"));
  panel = ["donna", "pepper"]; paintTint(onCall()); setState("live", "On the call"); await wait(200);  // H79: three-way
  out.push("three-way:" + (calOpen() && placed() && appts().length === 3 ? "ok" : "WRONG"));
  showCal(false); await wait(100); calBtn.click(); await wait(200); showCal(false);
  out.push("mic-on:" + (state === "live" && !stopped.length && tracks[0].enabled && pc === null ? "ok" : "WRONG " + state + " " + stopped.length));
  calBtn.click(); await wait(200); appts()[2].click(); await wait(100);
  stream = null; panel = []; cleanup("Call ended"); await wait(200);
  out.push("after:" + (placed() && !shown(devBtn) && calOpen() && !document.getElementById("calgo").disabled && !document.getElementById("calbusy") ? "ok" : "WRONG"));
  document.getElementById("calclose").click();
  const pre = document.createElement("pre"); pre.id = "h101"; pre.textContent = "H101RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f2 = self.tmp / "h101.html"
        f2.write_text(page.replace("<style>", stub + "<style>", 1).replace("</body>", harness + "</body>", 1))
        for where, q in (("phone", ""), ("app", "?app=1")):
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []), "--window-size=390,844",
                                              f"--user-data-dir={self.tmp / ('h101-' + where)}", "--virtual-time-budget=20000", "--dump-dom", f2.as_uri() + q], timeout=120)
            m = re.search(r'<pre id="h101">H101RESULT (.*?) END</pre>', r.stdout)
            need(m, f"the page test didn't finish ({where}): {(r.stderr or r.stdout)[-300:]!r}")
            res = m.group(1)
            say(f"   {where}: {res}")
            need(all(part.endswith(":ok") for part in res.split(" | ")), f"the calendar button or sheet isn't right ({where}): {res}")
        return ("read only through a stand-in run (only the two reading tools), the tool results word for word (a big answer from "
                "Claude Code's own file, nothing outside it), cancelled left out, Main, a failed read keeping the last days; hourly in "
                "the day, again on opening; H153: a whole day as its date and first on its day, the list in time order (also a copy "
                "saved before), a write by a call, Donna or an X read again within the minute at any hour (right away on the main, "
                "through the synced mark from the backup; a dry run never); /api/calendar on its own copy, ?fresh=1 reading again; the call's note, greeting and "
                "transcript line; the page, phone and app: the button on the right before and after a call, the days, one "
                "appointment, Back, a swipe to the right back to the days (finger and trackpad; not up or down, left, short or from a field; H147), Call about this sending it to the agenda's agent (F30), off on Free, one sheet at a time; on a call "
                "(also three-way) the button and an open sheet stay, the call's buttons free below it, Call about this waits, "
                "the Mic sheet and the calendar take turns, the call and the mic go on (H144)")

    async def flow92(self) -> str:
        """H124, no Claude: Donna texts first. routine/pings.py on its own copies (picking appointments, reminders,
        her notes, what's due and sent once, her own look), the texts' kinds in direct_line (dry, nothing pushed),
        the call's and her chat's rules and policy, agenda's bell, the test server's /api/calendar/ping and her
        notes in /api/notes, and the real call page in a headless browser: the bell and the button."""
        import pings
        import direct_line
        from policy import Policy, ALLOW, DENY
        d = self.tmp / "h124"
        d.mkdir(parents=True, exist_ok=True)
        keep = {k: os.environ.get(k) for k in ("HQ_DIRECT_DIR", "HQ_CALENDAR_FILE", "HQ_AGENT_NOTES", "HQ_DIRECT_DRY",
                                               "HQ_INITIATIVE_SAYS", "HQ_INITIATIVE", "HQ_DIRECT_LOCAL")}
        real = Path(os.path.join(pings.hqpaths.DATA, "direct-line", "pings.json"))
        real_before = real.read_bytes() if real.exists() else None
        os.environ.update({"HQ_DIRECT_DIR": str(d / "line"), "HQ_CALENDAR_FILE": str(d / "calendar.json"),
                           "HQ_AGENT_NOTES": str(d / "notes-donna.md"), "HQ_DIRECT_DRY": "1",
                           "HQ_DIRECT_LOCAL": str(d / "local.json")})
        os.environ.pop("HQ_INITIATIVE", None)
        try:
            t0 = datetime(2099, 1, 1, 12, 0).timestamp()
            iso = lambda h, m=0, day=1: datetime(2099, 1, day, h, m).astimezone().isoformat()
            (d / "calendar.json").write_text(json.dumps({"looked": t0, "events": [
                {"id": "a1", "title": "Dentist check", "start": iso(12, 30), "end": iso(13), "all_day": False, "where": "Main street 1", "notes": ""},
                {"id": "a2", "title": "Lunch", "start": iso(13), "end": iso(14), "all_day": False, "where": "", "notes": ""},
                {"id": "a3", "title": "Lunch", "start": iso(13, day=2), "end": iso(14, day=2), "all_day": False, "where": "", "notes": ""},
                {"id": "a4", "title": "Birthday", "start": "2099-01-01", "end": "2099-01-02", "all_day": True}]}))
            need(not pings.pinged() and not pings.due(t0), "an appointment gets a ping without being picked")
            need([e["id"] for e in pings.find_events("dentist", now=t0)] == ["a1"] and len(pings.find_events("lunch", now=t0)) == 2
                 and [e["id"] for e in pings.find_events("lunch 2099-01-02", now=t0)] == ["a3"]
                 and [e["id"] for e in pings.find_events("a2", now=t0)] == ["a2"] and not pings.find_events("birthday", now=t0),
                 "finding the appointment by its words, date or id isn't right")
            pings.appt_on(pings.find_events("dentist", now=t0)[0], before=10)
            pings.appt_on(pings.find_events("a2", now=t0)[0])
            need(pings.pinged() == {"a1", "a2"}, f"the bell's list isn't the picked ones: {pings.pinged()}")
            need(not pings.due(datetime(2099, 1, 1, 12, 15).timestamp()), "the ping came before its ten minutes")
            got = pings.watch(datetime(2099, 1, 1, 12, 21).timestamp(), spawn=lambda *a: None)
            need([w for w, _ in got] == ["appt"] and "Dentist check" in got[0][1] and "in 9 minutes" in got[0][1]
                 and "Main street 1" in got[0][1], f"the ping ten minutes before isn't right: {got}")
            need(not pings.watch(datetime(2099, 1, 1, 12, 22).timestamp(), spawn=lambda *a: None), "a ping was sent twice")
            need(pings.pinged() == {"a2"}, "a sent ping still shows the bell")
            need(not pings.watch(datetime(2099, 1, 1, 13, 20).timestamp(), spawn=lambda *a: None) and
                 not pings.read()["appointments"]["a2"].get("sent"), "a ping long after its start (HQ was off) was sent late")
            pings.appt_off("a2")
            need(not pings.pinged(), "appt off didn't stop the ping")
            now = datetime(2099, 1, 1, 12, 0)
            need(pings.when("in 20 minutes", now) == datetime(2099, 1, 1, 12, 20) and pings.when("15:00", now) == datetime(2099, 1, 1, 15)
                 and pings.when("9:30", now) == datetime(2099, 1, 2, 9, 30) and pings.when("tomorrow 9.30", now) == datetime(2099, 1, 2, 9, 30)
                 and pings.when("2099-01-05 08:00", now) == datetime(2099, 1, 5, 8), "reading a reminder's time isn't right")
            try:
                pings.when("25:00", now)
                need(False, "a time that doesn't exist was taken")
            except ValueError:
                pass
            r1 = pings.remind(datetime(2099, 1, 1, 15), "take the laundry out")
            r2 = pings.remind(datetime(2099, 1, 1, 16), "call the plumber")
            need(pings.cancel(r2["n"]) and not pings.cancel(r2["n"]), "cancelling a reminder isn't right")
            got = pings.watch(datetime(2099, 1, 1, 15, 0, 30).timestamp(), spawn=lambda *a: None)
            need([w for w, _ in got] == ["remind"] and "take the laundry out" in got[0][1] and "late" not in got[0][1],
                 f"the reminder wasn't due at its time: {got}")
            need(not pings.watch(datetime(2099, 1, 1, 15, 2).timestamp(), spawn=lambda *a: None), "a reminder was sent twice")
            pings.remind(datetime(2099, 1, 1, 15, 10), "stretch")
            got = pings.watch(datetime(2099, 1, 1, 15, 40).timestamp(), spawn=lambda *a: None)
            need(got and "30 minutes late" in got[0][1], f"a late reminder doesn't say it's late: {got}")
            # her own notes, and her own look at them
            need(not pings.initiative_due(datetime(2099, 1, 1, 12).timestamp()), "she looks at her notes while she has none")
            it = pings.note_add("Follow up on the dentist booking")
            need(it and (d / "notes-donna.md").exists() and "Donna's notes" in (d / "notes-donna.md").read_text()
                 and [i["text"] for i in pings.her_notes()] == ["Follow up on the dentist booking"], "her notes aren't kept like his")
            need(pings.initiative_due(datetime(2099, 1, 1, 12).timestamp()) and not pings.initiative_due(datetime(2099, 1, 1, 22).timestamp())
                 and not pings.initiative_due(datetime(2099, 1, 1, 7).timestamp()), "her own look isn't only in the day")
            spawned = []
            pings.watch(datetime(2099, 1, 1, 16).timestamp(), spawn=lambda w, f: spawned.append(w))
            need(spawned == ["initiative"] and not pings.initiative_due(datetime(2099, 1, 1, 17).timestamp())
                 and pings.initiative_due(datetime(2099, 1, 1, 19, 1).timestamp()), f"her own look isn't every three hours: {spawned}")
            facts = pings.initiative_facts(datetime(2099, 1, 1, 12).timestamp())
            need("Follow up on the dentist booking" in facts and "Lunch" in facts, f"her look doesn't see her notes and the day: {facts!r}")
            os.environ["HQ_INITIATIVE_SAYS"] = "QUIET"
            n0 = len(direct_line.thread())
            need(direct_line.initiative() is None and len(direct_line.thread()) == n0, "she texted though she chose to stay quiet")
            os.environ["HQ_INITIATIVE_SAYS"] = "Still want me to chase the dentist for you? They wrote again."
            m = direct_line.initiative()
            need(m and m["why"] == "initiative" and len(direct_line.thread()) == n0 + 1, "her own text didn't go in the thread")
            for _ in range(pings.INITIATIVE_MAX - 1):
                pings.initiative_sent()
            st = pings.read()["initiative"]
            need(int(st["texts"]) == pings.INITIATIVE_MAX, f"her own texts aren't counted per day: {st}")
            day_t = datetime.strptime(st["day"] + " 20:59", "%Y-%m-%d %H:%M").timestamp()
            need(not pings.initiative_due(day_t), "she may text on her own more than the day's most")
            need(pings.note_clear("dentist") and not pings.her_notes(), "clearing her note didn't work")
            # her texts' kinds, dry
            for why, word in (("appt", "appointment"), ("remind", "remind")):
                txt = direct_line.compose(why, "Dentist check")
                need(why in direct_line.PLAIN and "Dentist check" in txt, f"no plain line for {why}: {txt!r}")
                need(word in direct_line.compose_prompt(why, "x").lower(), f"her prompt for {why} isn't there")
            # the rules and the policy: a call and her chat may set them, nothing else in the script
            need("pings.py" in config.VOICE_RULES and "never all by default" in config.VOICE_RULES and "{pings}" not in config.VOICE_RULES,
                 "the call rules don't say how to set her pings")
            need("pings.py" in direct_line._text_rules(), "her chat doesn't know how to set pings")
            pol = Policy(config.FOLDER)
            script = str(ROOT / "routine" / "pings.py")
            for cmd in (f'python3 "{script}" appt on "dentist"', f'python3 "{script}" remind "in 20 minutes" "tea"',
                        f'python3 "{script}" note "x"', f'python3 "{script}" list'):
                dec = pol.decide("Bash", {"command": cmd})
                need(dec.verdict == ALLOW, f"a call may not run {cmd}: {dec}")
            need(pol.decide("Bash", {"command": f'python3 "{script}" match 1 "x"'}).verdict == DENY, "a call may run the mail check's part")
            # the bell from agenda
            import agenda
            pings.appt_on({"id": "a3", "title": "Lunch", "start": iso(13, day=2)})
            rd = agenda.read(now=t0)
            need([e["id"] for e in rd["events"] if e.get("ping")] == ["a3"], f"agenda doesn't mark the bell: {rd['events']}")
            tsrc = (ROOT / "routine" / "tick.py").read_text()
            need("pings.watch()" in tsrc and tsrc.index("pings.watch()") > tsrc.index("import weather"),
                 "the routine doesn't look for due pings on the main")
            need("create_event" not in (ROOT / "routine" / "pings.py").read_text(), "the pings may write to Google Calendar")
        finally:
            for k, v in keep.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        need((real.read_bytes() if real.exists() else None) == real_before, "the workspace's own pings were touched")

        # the test server: the bell's button and her notes
        await self.ensure_server()
        sfile = Path(self.server.env["HQ_CALENDAR_FILE"])
        sfile.parent.mkdir(parents=True, exist_ok=True)
        now = time.time()
        sfile.write_text(json.dumps({"looked": now, "calendars": [], "events": [
            {"id": "s1", "title": "Soon", "start": datetime.fromtimestamp(now + 3600).astimezone().isoformat(), "end": "", "all_day": False}]}))

        def post(path, body, hq):
            req = urllib.request.Request(TEST_URL + path, data=json.dumps(body).encode(), method="POST",
                                         headers={"content-type": "application/json", **({"x-hq": hq} if hq else {})})
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.status, json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as e:
                return e.code, {}
        need(post("/api/calendar/ping", {"id": "s1", "on": True}, "")[0] == 403, "the pings could be changed without the page's header")
        code, got = post("/api/calendar/ping", {"id": "s1", "on": True}, "calendar")
        need(code == 200 and [e.get("ping") for e in got.get("events", [])] == [True], f"the bell didn't go on ({code} {got})")
        need(post("/api/calendar/ping", {"id": "nope", "on": True}, "calendar")[0] == 404, "a ping for an appointment that isn't there")
        code, got = post("/api/calendar/ping", {"id": "s1", "on": False}, "calendar")
        need(code == 200 and [e.get("ping") for e in got.get("events", [])] == [False], "the bell didn't go off")
        sp = Path(self.server.env["HQ_AGENT_NOTES"])
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text("# Donna's notes\n\n## Notes\n\n- 2099-01-01 12:00:00 · Chase the dentist\n")
        code, body, _ = http_get("/api/notes")
        got = json.loads(body) if code == 200 else {}
        hers = (got.get("hers") or {}).get("items") or []
        need(code == 200 and [i["text"] for i in hers] == ["Chase the dentist"] and got["hers"]["name"], f"/api/notes doesn't give her notes: {got}")
        code, got = post("/api/notes", {"clear_hers": hers[0]["id"]}, "notes")
        need(code == 200 and not got["hers"]["items"] and "Chase" not in sp.read_text(), "clearing her note from the page didn't work")

        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        stub = r"""<script>
var POSTED = [], T = new Date(); T.setHours(0, 0, 0, 0);
function at(days, h, m) { const d = new Date(T); d.setDate(d.getDate() + days); d.setHours(h, m || 0); return d.toISOString(); }
var EVENTS = [
  { id: "e1", title: "Shower", start: at(0, 23, 0), end: at(0, 23, 45), all_day: false, where: "", notes: "", calendar: "Main", free: false, ping: true },
  { id: "e2", title: "Dentist", start: at(2, 10), end: at(2, 10, 30), all_day: false, where: "", notes: "", calendar: "Main", free: false, ping: false }];
var NOTES = { items: [{ id: "n1", when: "2099-01-01 12:00:00", text: "Mine" }], hers: { name: "Donna", items: [{ id: "h1", when: "2099-01-01 12:00:00", text: "Chase the dentist" }] } };
window.fetch = async (url, opt) => {
  url = String(url);
  if (url.startsWith("api/calendar/ping")) { const b = JSON.parse(opt.body); POSTED.push(b.id + ":" + b.on + ":" + (opt.headers || {})["x-hq"]);
    EVENTS.find(e => e.id === b.id).ping = b.on; return { ok: true, json: async () => ({ on: true, looked: Date.now() / 1000, events: EVENTS }) }; }
  if (url.startsWith("api/calendar")) return { ok: true, json: async () => ({ on: true, looked: Date.now() / 1000 - 60, looking: false, error: "", events: EVENTS }) };
  if (url.startsWith("api/notes")) { if (opt && opt.body) { const b = JSON.parse(opt.body); POSTED.push("note:" + b.clear_hers); NOTES.hers.items = []; } return { ok: true, json: async () => NOTES }; }
  return { ok: true, json: async () => ({ lines: [], calls: [], items: [] }) };
};</script>"""
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  await wait(300);
  calBtn.click(); await wait(400);
  const appts = () => calList.querySelectorAll(".appt");
  out.push("bell:" + (appts().length === 2 && appts()[0].querySelector("svg.bell") && !appts()[1].querySelector("svg.bell") ? "ok" : "WRONG"));
  appts()[1].click(); await wait(200);
  let p = document.getElementById("calping");
  out.push("button:" + (p && !p.classList.contains("on") && p.textContent.includes("Ask Donna") ? "ok" : "WRONG"));
  p.click(); await wait(200); p = document.getElementById("calping");
  out.push("on:" + (POSTED[0] === "e2:true:calendar" && p.classList.contains("on") && p.textContent.includes("Donna texts you") ? "ok" : "WRONG " + POSTED));
  document.getElementById("calback").click(); await wait(300);
  out.push("listbell:" + (appts()[1].querySelector("svg.bell") ? "ok" : "WRONG"));
  document.getElementById("calclose").click(); await wait(100);
  notesBtn.click(); await wait(400);
  const hh = notesList.querySelector(".hershead"), hr = notesList.querySelector(".note.hers");
  out.push("hers:" + (hh && hh.textContent === "Donna's notes" && hr && hr.textContent.includes("Chase the dentist") && notesList.querySelectorAll(".note").length === 2 ? "ok" : "WRONG"));
  hr.querySelector(".clr").click(); await wait(300);
  out.push("clearhers:" + (POSTED.includes("note:h1") && !notesList.querySelector(".note.hers") ? "ok" : "WRONG"));
  const pre = document.createElement("pre"); pre.id = "h124"; pre.textContent = "H124RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f2 = self.tmp / "h124.html"
        f2.write_text(page.replace("<style>", stub + "<style>", 1).replace("</body>", harness + "</body>", 1))
        for where, q in (("phone", ""), ("app", "?app=1")):
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []), "--window-size=390,844",
                                              f"--user-data-dir={self.tmp / ('h124-' + where)}", "--virtual-time-budget=20000", "--dump-dom", f2.as_uri() + q], timeout=120)
            m = re.search(r'<pre id="h124">H124RESULT (.*?) END</pre>', r.stdout)
            need(m, f"the page test didn't finish ({where}): {(r.stderr or r.stdout)[-300:]!r}")
            res = m.group(1)
            say(f"   {where}: {res}")
            need(all(part.endswith(":ok") for part in res.split(" | ")), f"the bell or her notes aren't right on the page ({where}): {res}")
        return ("only picked appointments get a ping (by words, date or id), ten minutes early when asked, once, never late after "
                "HQ was off, off again; reminders at their time, once, cancelled, a late one saying so; her own notes like his, "
                "her own look only in the day every three hours, quiet when she chooses, counted per day; the call's and her "
                "chat's rules and policy; the bell from agenda; /api/calendar/ping and her notes in /api/notes on the test "
                "server; the page, phone and app: the bell, the button, her notes under his")

    async def flow58(self) -> str:
        """H60: continue an earlier call. The transcript code (what goes in, trimmed from the start, refused
        names), the call (greeting, warm-up note, never on Free), the call page in a headless browser (the
        Continue button, only when not on a call, not as Free, the offer it sends, the chat it starts with),
        and one real call to the test server that continues a made-up call: one Claude turn (its warm-up)."""
        import transcript
        import brain as _brain  # noqa: F401  (clears API key variables first)
        from call import Call
        calls = self.server.calls
        calls.mkdir(parents=True, exist_ok=True)
        head = "# Call\n\n> **Private.**\n\nStarted 22:00:00 · agent Pepper · brain test\n\n"
        name = "2099-12-29-2200"
        (calls / f"{name}.md").write_text(head + (
            "- 22:00:01 *filler: Hi there!*\n"
            "- 22:00:02 *call: connected; connectors: none*\n"
            f"- 22:00:05 **{config.USER_LABEL}:** Let's plan the dentist. *(typed)*\n"
            "- 22:00:06 `Read challenges.md` · done (reading in the folder)\n"
            "- 22:00:09 **HQ:** Tuesday at ten works.\n"
            f"- 22:00:12 **{config.USER_LABEL}:** Never mind that. *(cancelled)*\n"
            f"- 22:00:15 **{config.USER_LABEL}:** And the shoes after.\n\nEnded 22:00:20\n"))
        (calls / "2099-12-29-2210.md").write_text(head + "- 22:10:01 *filler: Hi!*\n")
        c = transcript.continue_from(name, calls)
        need(c and c["agent"] == "Pepper" and c["lines"] == 3 and c["trimmed"] == 0
             and "Let's plan the dentist." in c["text"] and "You: Tuesday at ten works." in c["text"]
             and "Never mind" not in c["text"] and "challenges.md" not in c["text"] and "Hi there" not in c["text"],
             f"the earlier call isn't given as his and her lines only: {c}")
        short = transcript.continue_from(name, calls, max_chars=40)
        need(short and short["trimmed"] >= 1 and short["text"].endswith("And the shoes after.") and "left out" in short["text"],
             f"a long call isn't trimmed from the start: {short}")
        for bad in ("2099-12-29-2210", "../roadmap", "", "2099-12-29-2200.md", "2099-12-01-0000"):
            need(transcript.continue_from(bad, calls) is None, f"{bad!r} could be continued")
        # The call: her greeting, what its Claude is told, the transcript's line; never on Free.
        cc = Call(model="sonnet", calls_dir=calls, wrap_up="dry", test_mode=True, continues=name)
        need(cc.fillers._texts["greeting"] == config.continue_greetings(cc.agent) and cc.fillers._texts["greeting"],
             f"the greeting isn't her continue one (H76): {cc.fillers._texts['greeting']}")
        note = cc._continue_note()
        need("picking up where you left off" in note and "Tuesday at ten works." in note and "Pepper" in note,
             f"the warm-up note doesn't carry the earlier call: {note[:200]}")
        cc.transcript.path.unlink(missing_ok=True)
        import agents
        for g in config.CONTINUE_GREETINGS + config.continue_greetings(agents.find(config.FOLDER, "pepper")):
            need(not config.ME["name"] or config.ME["name"] in g, f"the name from me.md isn't in the greeting: {g}")
        cf = Call(model="sonnet", free=True, continues=name)
        need(cf.continued is None and cf.fillers._texts["greeting"] == config.greetings_now(cf.agent) and cf.transcript.path is None,
             "a Free call continued an earlier call")
        t = transcript.CallTranscript(self.tmp / "h60-calls", model="test", agent="Pepper", continues=c)
        t.user("Test.")
        need(transcript.read_call(t.path.stem, t.path.parent)["continues"] == name, "the new transcript doesn't say which call it continues")
        need(transcript.read_call(name, calls)["continues"] == "", "a call that continues nothing says it does")

        # The call page: the Continue button.
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        one = transcript.read_call(name, calls)
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const shown = el => getComputedStyle(el).display !== "none" && el.getBoundingClientRect().width > 0;
  const foot = document.getElementById("histfoot"), cont = document.getElementById("histcont");
  showAgents([{ id: "donna", name: "Donna", load: "quick", model: "sonnet", picture: "", speciality: "x" },
              { id: "pepper", name: "Pepper", load: "deep", model: "opus", picture: "", speciality: "y" }]);
  agent = "donna"; mode = "quick"; showMode();
  await wait(200);
  histBtn.click(); await wait(400);
  out.push("list:" + (histOpen() && !shown(foot) ? "ok" : "WRONG"));
  histList.querySelector("button").click(); await wait(400);
  out.push("foot:" + (shown(foot) && !cont.disabled && cont.textContent === "Continue this call with Pepper"
    && cont.getBoundingClientRect().bottom <= document.getElementById("dock").getBoundingClientRect().top + 1 ? "ok" : "WRONG " + cont.textContent));
  document.getElementById("histback").click(); await wait(300);
  out.push("back:" + (!shown(foot) ? "ok" : "WRONG"));
  histList.querySelector("button").click(); await wait(300);
  free = true; showMode(); showHistFoot();
  out.push("free:" + (cont.disabled && document.getElementById("histcontnote").textContent.includes("Free") ? "ok" : "WRONG"));
  cont.click(); await wait(200);
  out.push("freenocall:" + (state === "idle" && !OFFERS.length ? "ok" : "WRONG"));
  free = false; showMode(); showHistFoot();
  setState("live", "On the call");
  out.push("live:" + (!shown(foot) ? "ok" : "WRONG"));
  setState("idle", "Tap to call");
  out.push("idle:" + (shown(foot) ? "ok" : "WRONG"));
  cont.click();
  for (let i = 0; i < 200 && !OFFERS.length; i++) await wait(100);
  await wait(300);
  const rd = OFFERS.length ? OFFERS[0].request_data : {};
  out.push("offer:" + (rd.continue === "__NAME__" && rd.agent === "pepper" && rd.mode === "deep" && rd.free === false ? "ok" : "WRONG " + JSON.stringify(rd) + " err=" + errEl.textContent + " st=" + statusEl.textContent));
  const msgs = chatLog.querySelectorAll(".msg");
  out.push("chat:" + (!histOpen() && msgs.length === 4 && chatLog.querySelector(".divider") && chatLog.querySelectorAll(".msg.me.cancelled").length === 1
    && chatTitle.textContent === "Pepper" ? "ok" : "WRONG " + msgs.length + " " + chatTitle.textContent));  // H115: only who's on it
  // H119: after reopening the app the chat shows the last call, with Call back at its foot.
  for (let i = 0; i < 50 && state !== "idle"; i++) await wait(100);
  continueFrom = null; histShown = null; showHistory(false);
  calledHere = false; lastCallName = null; agent = "donna"; mode = "quick"; showMode(); clearChat(); setState("idle", "Tap to call");
  const cfoot = document.getElementById("chatfoot"), ccont = document.getElementById("chatcont");
  out.push("chatnofoot:" + (!shown(cfoot) ? "ok" : "WRONG"));
  chatBtn.click(); await wait(400);
  out.push("chatfoot:" + (chatOpen() && shown(cfoot) && !ccont.disabled && ccont.textContent === "Call back and continue with Pepper"
    && ccont.getBoundingClientRect().bottom <= document.getElementById("dock").getBoundingClientRect().top + 1 ? "ok" : "WRONG " + ccont.textContent));
  free = true; showMode(); showChatFoot();
  out.push("chatfree:" + (ccont.disabled && document.getElementById("chatcontnote").textContent.includes("Free") ? "ok" : "WRONG"));
  ccont.click(); await wait(200);
  out.push("chatfreenocall:" + (state === "idle" && OFFERS.length === 1 ? "ok" : "WRONG"));
  free = false; showMode(); showChatFoot();
  // The offer itself is checked above with Continue; here what Call back hands to the call.
  const CALLED = [], realCall = call;
  call = () => { CALLED.push({ cont: continueFrom && continueFrom.name, agent, mode, free }); };
  ccont.click(); await wait(200);
  call = realCall;
  const c2 = CALLED[0] || {};
  out.push("chatcall:" + (CALLED.length === 1 && c2.cont === "__NAME__" && c2.agent === "pepper" && c2.mode === "deep" && c2.free === false ? "ok" : "WRONG " + JSON.stringify(CALLED)));
  // F36: the desktop app is never reloaded: after a call made there, coming back to it brings Call back again,
  // but only once that call is saved (a newer last call than the chat showed before it).
  showChat(false); calledHere = true; lastCallName = "__NAME__"; clearChat(); setState("idle", "Tap to call");
  window.dispatchEvent(new Event("focus")); await wait(300);
  out.push("backunsaved:" + (calledHere && !shown(cfoot) ? "ok" : "WRONG"));
  lastCallName = "an older call"; window.dispatchEvent(new Event("focus")); await wait(300);
  chatBtn.click(); await wait(400);
  out.push("backsaved:" + (!calledHere && chatOpen() && shown(cfoot) && ccont.textContent === "Call back and continue with Pepper"
    && chatLog.querySelectorAll(".msg").length > 0 ? "ok" : "WRONG " + calledHere + " " + ccont.textContent));
  showChat(false); calledHere = true; lastCallName = "an older call"; clearChat(); setState("idle", "Tap to call");
  chatBtn.click(); await wait(400);
  out.push("backchat:" + (!calledHere && shown(cfoot) ? "ok" : "WRONG"));
  showChat(false);
  continueFrom = null; histShown = null;
  const pre = document.createElement("pre"); pre.id = "h60"; pre.textContent = "H60RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
""".replace("__NAME__", name)
        stub = ("<script>const OFFERS = []; const CALLS = " + json.dumps({"calls": transcript.list_calls(calls)[:1]}) + ", ONE = " + json.dumps(one) + """;
window.fetch = async (url, opts) => {
  if (String(url) === "api/offer") { OFFERS.push(JSON.parse(opts.body)); return { ok: false, status: 599, json: async () => ({}) }; }
  return { ok: true, json: async () => (String(url).startsWith("api/calls/") || String(url) === "api/last-call" ? ONE : String(url) === "api/calls" ? CALLS : { lines: [] }) };
};
try { Object.defineProperty(navigator, "mediaDevices", { value: { getUserMedia: async () => new MediaStream() } }); } catch (e) {}</script>""")
        f = self.tmp / "h60.html"
        f.write_text(page.replace("<style>", stub + "<style>", 1).replace("</body>", harness + "</body>", 1))
        for where, q in (("phone", ""), ("app", "?app=1")):
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []), "--window-size=390,844",
                                              f"--user-data-dir={self.tmp / ('h60-' + where)}", "--virtual-time-budget=60000", "--dump-dom", f.as_uri() + q], timeout=120)
            m = re.search(r'<pre id="h60">H60RESULT (.*?) END</pre>', r.stdout)
            need(m, f"the page test didn't finish ({where}): {(r.stderr or r.stdout)[-300:]!r}")
            res = m.group(1)
            say(f"   {where}: {res}")
            need(all(part.endswith(":ok") for part in res.split(" | ")), f"the Continue button isn't right ({where}): {res}")

        # One real call that continues the made-up one: the continue greeting, and the transcript says so.
        import fractions  # noqa: F401
        import aiohttp
        import numpy as np
        from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
        from test_a4 import FakeMic
        await self.ensure_server()
        offset = self.server.log_size()
        before = set(calls.glob("*.md"))
        pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        pc.addTrack(FakeMic(np.zeros(0, np.int16)))
        dc = pc.createDataChannel("chat", ordered=True)
        chats: list[tuple[str, str]] = []

        @dc.on("message")
        def on_message(msg):
            try:
                m = json.loads(msg)
            except (TypeError, ValueError):
                return
            if isinstance(m, dict) and m.get("type") == "hq-chat":
                chats.append((m.get("who"), m.get("text")))
        new_head = ""
        try:
            await pc.setLocalDescription(await pc.createOffer())
            async with aiohttp.ClientSession() as sess:
                async with sess.post(TEST_URL + "/api/offer", json={"sdp": pc.localDescription.sdp, "type": "offer",
                                     "request_data": {"mode": "quick", "agent": "donna", "continue": name}}) as r:
                    need(r.status == 200, f"the offer was refused ({r.status})")
                    answer = await r.json()
            await pc.setRemoteDescription(RTCSessionDescription(answer["sdp"], answer["type"]))
            t0 = time.perf_counter()
            while not any(w == "filler" for w, _ in chats) and time.perf_counter() - t0 < 30:
                await asyncio.sleep(0.2)
            new = [p for p in calls.glob("*.md") if p not in before]
            new_head = new[0].read_text()[:800] if new else ""
            await asyncio.sleep(4)
            dc.send(json.dumps({"type": "hangup"}))
            await asyncio.sleep(0.5)
        finally:
            await pc.close()
        log = ""
        for _ in range(60):
            log = self.server.log_since(offset)
            if "Nobody said anything" in log:
                break
            await asyncio.sleep(0.5)
        self.turns += 1
        greet = [t for w, t in chats if w == "filler"]
        every_continue = set(config.CONTINUE_GREETINGS) | {g for a in agents.load(config.FOLDER) for g in config.continue_greetings(a)}
        need(greet and greet[0] in every_continue, f"the greeting wasn't the continue one: {greet}")
        need(f"continues {name}" in log, "the server log doesn't say the call continues the earlier one")
        need(f"({name})" in new_head and "Continues the call of" in new_head, f"the new transcript doesn't say which call it continues: {new_head[:300]!r}")
        say(f"   greeting {greet[0]!r}")
        return ("the earlier call's lines (no tools, waiting lines or cancelled), trimmed from the start; the continue greeting "
                "with the name from me.md; never on Free; Continue at the foot of an opened call, not on a call, not as Free; "
                "the offer and the chat; a real continued call greets so and its transcript says which call")

    async def flow54(self) -> str:
        """H61: estimated time to completion for the jobs. No Claude turns and no job is started: the queue
        script and the estimator on a copy of the roadmap (its estimates in their own files next to it),
        made-up past jobs, a held job, a finished job teaching the next estimate, and the live status page."""
        import subprocess as sp
        from policy import Policy, ALLOW
        jv = ROOT
        rm = self.tmp / "roadmap-H61.md"
        rm.write_text(ROADMAP.read_text())
        est_dir = self.tmp / "roadmap-H61-estimates"
        env = {**os.environ, "HQ_ROADMAP": str(rm)}
        env.pop("HQ_ESTIMATES", None)
        env.pop("HQ_ROUTINES_HISTORY", None)
        def jobs(*a, ok=True):
            r = sp.run(["python3", str(jv / "routine/jobs.py"), *a], capture_output=True, text=True, env=env)
            need((r.returncode == 0) == ok, f"jobs.py {' '.join(a)}: {r.stdout.strip()} {r.stderr.strip()}")
            return r.stdout + r.stderr
        def est(*a):
            r = sp.run(["python3", str(jv / "routine/estimate.py"), *a], capture_output=True, text=True, env=env)
            need(r.returncode == 0, f"estimate.py {' '.join(a)}: {r.stderr.strip()}")
            return r.stdout
        real = (jv / ".status/job-estimates-history.jsonl")
        before = real.read_text() if real.exists() else None
        # The kinds, from the words a call writes in a job.
        for text, kind in (("Transcribe the four videos on the VPS", "transcribe"),
                           ("Build H1. This is a big change, so run the whole happy flow set at the end", "big"),
                           ("Build H2, not the whole set. Restart the call line as the very last step", "call"),
                           ("Build H3, not the whole set. Don't restart the call line.", "build"),
                           ("Measure the token cost of one run", "other")):
            need(est("kind", text).strip() == kind, f"{text!r} isn't seen as {kind}")
        # H70: build work by its wording anywhere, and a negated "build" doesn't count.
        for text, kind in (("H56.2 on the HQ roadmap (step 2 of 7). Build exactly what the H56.2 row says", "build"),
                           ("H56.6 on the HQ roadmap (step 6 of 7). Do exactly what the H56.6 row says", "build"),
                           ("Continue H55: set up a test call line. Don't build the backup or the sync (H56)", "other"),
                           ("H68 on the roadmap: research only for H56. Nothing built", "other")):
            need(est("kind", text).strip() == kind, f"H70: {text!r} isn't seen as {kind}")
        # Made-up past jobs: calls took 10 to 16 minutes, builds 5 to 7.
        est_dir.mkdir(parents=True, exist_ok=True)
        # F34: only jobs whose time was measured when they finished count; a seeded line (from before H61) doesn't.
        hist = [{"n": 900 + i, "kind": k, "est": None, "actual": a, "done": 1, "how": "seen"}
                for i, (k, a) in enumerate([("call", 10), ("build", 5), ("call", 12), ("build", 6), ("call", 14), ("build", 7), ("call", 16)])]
        hist.insert(0, {"n": 899, "kind": "call", "est": None, "actual": 90, "done": 1, "how": "seed"})
        (est_dir / "job-estimates-history.jsonl").write_text("".join(json.dumps(h) + "\n" for h in hist))
        for j in json.loads(jobs("next"))["waiting"] + json.loads(jobs("next"))["running"]:
            jobs("mark", str(j["n"]), "cancelled 12:00")
        a_out = jobs("add", "Build H2, flow 54. Restart the call line as the very last step")
        a = int(a_out.split()[1])
        b = int(jobs("add", "Build H3, flow 54. Don't restart the call line.").split()[1])
        need("Estimate: about 14 min" in a_out, f"a new job doesn't get its estimate from the calls before it: {a_out}")
        state = json.loads((est_dir / "job-estimates.json").read_text())
        need(state[str(a)]["est"] == 14 and state[str(a)]["kind"] == "call" and state[str(b)]["est"] == 6,
             f"the estimates set when added are wrong: {state}")
        p = json.loads(est("plan"))
        need(p["jobs"][str(a)]["eta"] and p["jobs"][str(b)]["eta"] - p["jobs"][str(a)]["eta"] == (6 + 1) * 60,
             f"the second job's done-around doesn't count the one before it: {p['jobs']}")
        need(p["total"]["jobs"] == 2 and p["total"]["minutes"] == 14 + 1 + 6 and p["total"]["eta"] == p["jobs"][str(b)]["eta"],
             f"the total for the whole list is wrong: {p['total']}")
        lst = jobs("list")
        need("Estimate: about 14 min, done around" in lst and "All 2 jobs: about 21 min, all done around" in lst and "(estimate)" in lst,
             f"list doesn't say the estimates: {lst}")
        need("No estimate has been checked" in lst, f"list doesn't say how close the estimates have been: {lst}")
        # A held job, and everything after it, waits on the usage. H109: the times stay, as if the usage
        # allowed it, and the words say they'll be later because of the usage limit.
        jobs("held", str(a))
        p = json.loads(est("plan"))
        need(p["jobs"][str(a)]["waits"] == "usage" and p["jobs"][str(b)]["waits"] == "usage" and p["total"]["waits"] == "usage",
             f"a held job doesn't wait on the usage: {p['jobs']} {p['total']}")
        need(p["jobs"][str(a)]["eta"] and p["jobs"][str(b)]["eta"] - p["jobs"][str(a)]["eta"] == (6 + 1) * 60
             and p["total"]["eta"] == p["jobs"][str(b)]["eta"], f"H109: held by the usage, the times are gone: {p['jobs']} {p['total']}")
        lst = jobs("list")
        need("done around" in lst and "later, because the usage limit holds the jobs" in lst and "all done around" in lst,
             f"H109: list doesn't keep the times with the usage note: {lst}")
        # It runs, and finishes: its estimate next to how long it really took, and the next estimate learns.
        jobs("mark", str(a), "running since " + time.strftime("%H:%M", time.localtime(time.time() - 30 * 60)))
        st = json.loads((est_dir / "job-estimates.json").read_text())[str(a)]
        need(st.get("started"), f"starting doesn't note when: {st}")
        st["started"] = int(time.time()) - 30 * 60
        s2 = json.loads((est_dir / "job-estimates.json").read_text()); s2[str(a)] = st
        (est_dir / "job-estimates.json").write_text(json.dumps(s2))
        p = json.loads(est("plan"))
        need(p["jobs"][str(a)]["over"] and p["jobs"][str(a)]["so_far"] == 30, f"a job running longer than estimated isn't said: {p['jobs'][str(a)]}")
        done = jobs("done", str(a))
        need("Took 30 min; the estimate was 14 min" in done, f"done doesn't write the real time next to the estimate: {done}")
        last = json.loads((est_dir / "job-estimates-history.jsonl").read_text().splitlines()[-1])
        need(last["n"] == a and last["est"] == 14 and last["actual"] == 30 and last["kind"] == "call", f"the history line is wrong: {last}")
        p = json.loads(est("plan"))
        need(p["accuracy"]["count"] == 1 and p["accuracy"]["avg_off"] == 16 and p["accuracy"]["longer"] == 1,
             f"how close the estimates have been is wrong: {p['accuracy']}")
        c_out = jobs("add", "Build H4, flow 54. Restart the call line as the very last step")
        need("Estimate: about 16 min" in c_out, f"the next estimate didn't learn from the real time: {c_out}")
        # H70: --kind wins over the guess, is stored with the estimate, and the job learns under it.
        jobs("add", "Measure something, flow 54", "--kind", "nonsense", ok=False)
        d_out = jobs("add", "Measure the token cost of one run, flow 54", "--kind", "call")
        d = int(d_out.split()[1])
        need("Estimate: about 16 min" in d_out, f"H70: --kind call doesn't take the calls' estimate: {d_out}")
        sd = json.loads((est_dir / "job-estimates.json").read_text())[str(d)]
        need(sd["kind"] == "call" and sd.get("by_hand"), f"H70: the hand-set kind isn't stored: {sd}")
        need("--kind" not in json.loads(jobs("next"))["waiting"][-1]["text"], "H70: --kind ended up in the job's text")
        e_ = int(jobs("add", "Build H5, flow 54. Restart the call line as the very last step", "--kind=build").split()[1])
        need(json.loads((est_dir / "job-estimates.json").read_text())[str(e_)]["kind"] == "build", "H70: --kind=build isn't taken")
        jobs("mark", str(d), "running since " + time.strftime("%H:%M"))
        jobs("done", str(d))
        last = json.loads((est_dir / "job-estimates-history.jsonl").read_text().splitlines()[-1])
        need(last["n"] == d and last["kind"] == "call", f"H70: a hand-set kind doesn't learn in its own pile: {last}")
        need("--kind" in config.VOICE_RULES and "H70" in config.VOICE_RULES, "H70: the call rules don't say to pass --kind")
        # H95: planned items get a kind and an estimate when planned, and when they should be done, counting
        # the job list and the items before them; the kind goes with the item when it becomes a job.
        def sched(*a, ok=True):
            r = sp.run(["python3", str(jv / "routine/schedule.py"), *a], capture_output=True, text=True, env=env)
            need((r.returncode == 0) == ok, f"schedule.py {' '.join(a)}: {r.stdout.strip()} {r.stderr.strip()}")
            return r.stdout + r.stderr
        for l in sched("list").split("Looking back")[0].splitlines():  # only the test's own items
            if l.startswith("Item "):
                sched("cancel", l.split()[1])
        need(est("kind", "F18 on the HQ roadmap: the page swipes. Read the F18 row first and fix it as it says.").strip() == "build",
             "H95: a planned item's wording isn't seen as a build")
        sched("add", "tomorrow 15:00", "Measure something, flow 54", "--kind", "nonsense", ok=False)
        i1_out = sched("add", "tomorrow 15:00", "H1 on the HQ roadmap, flow 54. Read the H1 row first and build it as it says.")
        i1 = int(i1_out.split()[1])
        need("Estimate: about" in i1_out and "(estimate)" in i1_out, f"H95: planning an item doesn't say its estimate: {i1_out}")
        i2 = int(sched("add", "tomorrow 15:01", "Measure the token cost of one run, flow 54", "--kind", "call").split()[1])
        i3 = int(sched("add", "now", "Measure the token cost of a call, flow 54", "--kind=transcribe").split()[1])
        kinds = json.loads((est_dir / "schedule-kinds.json").read_text())
        need(kinds[str(i1)]["kind"] == "build" and not kinds[str(i1)].get("by_hand") and kinds[str(i2)]["kind"] == "call"
             and kinds[str(i2)].get("by_hand") and kinds[str(i3)]["kind"] == "transcribe", f"H95: the items' kinds are wrong: {kinds}")
        need("--kind" not in sched("list"), "H95: --kind ended up in the item's text")
        p = json.loads(est("plan"))
        it = p["items"]
        at1 = time.mktime(time.strptime(time.strftime("%Y-%m-%d", time.localtime(time.time() + 86400)) + " 15:00", "%Y-%m-%d %H:%M"))
        need(it[str(i3)]["start"] == p["total"]["eta"] + 60 and it[str(i3)]["later"],
             f"H95: a due item doesn't wait for the job list in its estimate: {it[str(i3)]} {p['total']}")
        need(it[str(i1)]["start"] == at1 + 60 and it[str(i1)]["eta"] == it[str(i1)]["start"] + it[str(i1)]["est"] * 60,
             f"H95: an item later on doesn't start at its own time: {it[str(i1)]}")
        need(it[str(i2)]["start"] == max(at1 + 60, it[str(i1)]["eta"]) + 60 and it[str(i2)]["kind"] == "call",
             f"H95: an item doesn't count the item before it: {it[str(i2)]}")
        lst = sched("list")
        need(lst.count("Estimate: about") == 3 and "done around" in lst, f"H95: the scheduler's list doesn't say the estimates: {lst}")
        # H107: all planned items together, as the job list has: how long, and when the last should be done.
        tot = p["items_total"]
        need(tot["items"] == 3 and tot["minutes"] == sum(it[k]["est"] for k in it) and tot["eta"] == max(it[k]["eta"] for k in it),
             f"H107: the planned items' total is wrong: {tot} {it}")
        need("All 3 planned items: about" in lst and "all done around" in lst, f"H107: the scheduler's list doesn't say the total: {lst}")
        # H109: a job held by the usage: the planned items keep their times, with the usage note.
        h_ = int(jobs("add", "Build H6, flow 54", "--kind=build").split()[1])
        jobs("held", str(h_))
        ph = json.loads(est("plan"))
        need(all(ph["items"][k]["eta"] and ph["items"][k]["waits"] == "usage" for k in ph["items"])
             and ph["items_total"]["eta"] and ph["items_total"]["waits"] == "usage",
             f"H109: held by the usage, the planned items lose their times: {ph['items']} {ph['items_total']}")
        lh = sched("list")
        need(lh.count("later, because the usage limit holds the jobs") >= 4, f"H109: the scheduler's list doesn't say they'll be later: {lh}")
        jobs("mark", str(h_), "cancelled 12:00")
        page9 = (jv / "status/index.html").read_text()
        need("function etaSpan" in page9 and ".late {" in page9 and "lateNote(E?.total)" in page9 and "itemsLate" in page9,
             "H109: the status page doesn't show the soft red usage note")
        need("H109" in config.VOICE_RULES, "H109: the call rules don't say the times stay with the usage note")
        jobs("off")
        need(json.loads(est("plan"))["items"][str(i1)]["waits"] == "off" and "the routine is off" in sched("list"),
             "H95: with the routine off, a planned item still says when it's done")
        need(json.loads(est("plan"))["items_total"]["waits"] == "off" and json.loads(est("plan"))["items_total"]["eta"] is None,
             "H107: with the routine off, the planned items' total still says when it's done")
        jobs("on")
        # The job list empty: the due item becomes a job, its hand-set kind with it; its line in the kinds file goes.
        for j in json.loads(jobs("next"))["waiting"]:
            jobs("mark", str(j["n"]), "cancelled 12:00")
        did = sched("promote")
        need(f"item {i3} became job" in did, f"H95: the due item didn't become a job: {did}")
        jn = did.split()[-1]
        sj = json.loads((est_dir / "job-estimates.json").read_text())[jn]
        need(sj["kind"] == "transcribe" and sj.get("by_hand"), f"H95: the item's kind didn't go with it to its job: {sj}")
        sched("cancel", str(i2))
        kinds = json.loads((est_dir / "schedule-kinds.json").read_text())
        need(str(i3) not in kinds and str(i2) not in kinds and str(i1) in kinds, f"H95: the kinds file keeps what's gone: {kinds}")
        sched("cancel", str(i1))
        jobs("mark", jn, "cancelled 12:00")
        need("function etaItem" in (jv / "status/index.html").read_text(), "H95: the status page doesn't show planned items' estimates")
        need("function etaItemsTotal" in (jv / "status/index.html").read_text() and "itemsTotal ? ` · ${itemsTotal}`" in (jv / "status/index.html").read_text(),
             "H107: the status page's Scheduled heading doesn't show the planned items' total")
        need("H107" in config.VOICE_RULES, "H107: the call rules don't say the scheduler's list has a total")
        need("H95" in config.VOICE_RULES and "each item with its estimate" in config.VOICE_RULES,
             "H95: the call rules don't say planned items have estimates")
        need(real.exists() == (before is not None) and (before is None or real.read_text() == before),
             "the test touched the real estimates history")
        # The status page: the server serves the plan, the page shows it in words.
        srv = (jv / "status/server.mjs").read_text()
        page = (jv / "status/index.html").read_text()
        need("routine/estimate.py" in srv and "estimate };" in srv, "the status server doesn't serve the estimates")
        need("function etaWords" in page and "etaTotal(E)" in page and "etaAccuracy(E.accuracy)" in page and "(estimate)" in page,
             "the status page doesn't show the estimates")
        code, body, _ = await asyncio.to_thread(http_get, "/routines.json", "http://127.0.0.1:4748")
        live = json.loads(body) if code == 200 else {}
        need("estimate" in live and "accuracy" in (live["estimate"] or {}), f"the live status server has no estimates: {code}")
        q = json.loads(sp.run(["python3", str(jv / "routine/jobs.py"), "next"], capture_output=True, text=True).stdout)
        # The page in a headless browser only where there is one (a Mac); on a server the parts above suffice (H56.7).
        browsers = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        if (q["running"] or q["waiting"]) and browsers:
            chrome = browsers[-1]
            r = await asyncio.to_thread(run, [str(chrome), "--headless", "--disable-gpu", "--no-first-run", "--window-size=900,3000",
                                              f"--user-data-dir={self.tmp / 'h61'}", "--virtual-time-budget=8000", "--dump-dom", "http://127.0.0.1:4748/"], timeout=120)
            need("(estimate)" in r.stdout and "Estimates" in r.stdout, "the live status page doesn't show the estimates on the job list")
        # A call may read the list, and the call rules say the estimates are estimates.
        pol = Policy(config.FOLDER)
        need(pol.decide("Bash", {"command": f'python3 "{ROOT}/routine/jobs.py" list'}).verdict == ALLOW, "a call can't read the list")
        need("H61" in config.VOICE_RULES and "estimate" in config.VOICE_RULES, "the call rules don't say the list has estimates")
        return ("kinds from the job's words; estimate set when added; per job and total with done-around; held waits on the usage; "
                "done writes estimate next to real time and the next estimate learns; page and list show them; "
                "planned items too, after the job list and the items before them, their kind going with them (H95), and their total (H107); held by the usage, the times stay with a soft red note (H109)")

    # 55
    async def flow55(self) -> str:
        """F14: the voice-off button (H40) also silences the page's own sounds: the thinking tick,
        the low talk sound (H32) and the click (H24). Turned back on, the tick comes back only if the
        thinking-sound switch is on. The switch itself is never changed. No Claude turns: the real
        call page in a headless browser, on a fake live call."""
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const check = (name, ok, why) => out.push(name + ":" + (ok ? "ok" : "WRONG " + why));
  const server = st => onServerMessage({ data: JSON.stringify({ type: "hq-state", state: st }) });
  try { localStorage.setItem("hq-sound", "on"); localStorage.setItem("hq-voice-off", "off"); } catch (e) {}
  soundOn = true; showSound(); voiceOff = false; applyVoice();
  startAudio();
  let oscs = 0; const co = audioCtx.createOscillator.bind(audioCtx); audioCtx.createOscillator = () => { oscs++; return co(); };
  setState("live", "On the call");
  server("thinking"); await wait(50);
  check("tick-on", tickTimer !== null, String(tickTimer));
  voiceBtn.click(); await wait(50);
  check("voice-off-tick", voiceOff && tickTimer === null, voiceOff + "/" + tickTimer);
  check("switch-kept", soundOn && soundBtn.getAttribute("aria-pressed") === "true" && localStorage.getItem("hq-sound") === "on",
        soundOn + "/" + localStorage.getItem("hq-sound"));
  server("listening"); server("thinking"); await wait(50);
  check("still-silent", tickTimer === null, String(tickTimer));
  oscs = 0; const r = talkSound(); click();
  check("talk-click-silent", r === false && oscs === 0, r + "/" + oscs);
  voiceBtn.click(); await wait(50);
  check("voice-on-tick", !voiceOff && tickTimer !== null, voiceOff + "/" + tickTimer);
  oscs = 0; const r2 = talkSound();
  check("talk-back", r2 === true && oscs === 1, r2 + "/" + oscs);
  // the thinking-sound switch off: voice off and on again, and the tick stays off
  soundOn = false; thinkingSound(true); voiceBtn.click(); await wait(50); voiceBtn.click(); await wait(50);
  check("switch-off-stays", !voiceOff && tickTimer === null && !soundOn, voiceOff + "/" + tickTimer + "/" + soundOn);
  server("listening");
  const pre = document.createElement("pre"); pre.id = "f14"; pre.textContent = "F14RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f = self.tmp / "f14.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", "--autoplay-policy=no-user-gesture-required",
                                          f"--user-data-dir={self.tmp / 'f14-profile'}", "--virtual-time-budget=20000", "--dump-dom", f.as_uri()], timeout=90)
        m = re.search(r'<pre id="f14">F14RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        res = m.group(1)
        say(f"   {res}")
        need(all(part.endswith(":ok") for part in res.split(" | ")), f"the voice button doesn't silence the page's sounds right: {res}")
        return "voice off silences the tick, the talk sound and the click; back on, the tick follows the switch; the switch never changes"

    # 56
    async def flow56(self) -> str:
        """H59: an update to a fake newer version, without the network: a made-up HQ repo in a folder as the
        public repo (tags v0.2, then v0.3 and v0.3.1), a copy of it as the user's HQ. The check sees v0.3 and
        what's new; offline is quiet; Update saves the user's changes on a backup branch, moves to v0.3, leaves
        local/ and the workspace as they were, and writes the note for their Claude (as on a computer that isn't a
        Mac); with a call on, the next update waits and starts by itself when the call ends. Restarts nothing."""
        import subprocess as sp
        import http.server, socketserver, threading
        base = self.tmp / "h59"
        up, me = base / "upstream", base / "mine"
        if base.exists():
            shutil.rmtree(base)
        (up / "routine").mkdir(parents=True)
        for f in ("routine/update.py", "routine/hqpaths.py", ".gitignore"):
            shutil.copy(ROOT / f, up / f)
        (up / "README.md").write_text("A made-up HQ, for flow 56.\n")
        log = lambda body: "# Changelog\n\n" + body + "## 0.2 · 1 January 2026\n\n### New\n- The first version.\n"
        (up / "CHANGELOG.md").write_text(log(""))
        genv = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_TERMINAL_PROMPT": "0"}
        def g(where, *a):
            r = sp.run(["git", "-C", str(where), *a], capture_output=True, text=True, env=genv)
            need(r.returncode == 0, f"git {' '.join(a)}: {r.stderr.strip()}")
            return r.stdout.strip()
        g(up, "init", "-q", "-b", "main"); g(up, "add", "-A"); g(up, "commit", "-qm", "0.2"); g(up, "tag", "-a", "v0.2", "-m", "HQ 0.2")
        g(base, "clone", "-q", str(up), str(me))
        # The user's own things: a part in local/, a workspace file, a change to HQ's own file, a new file.
        (me / "local").mkdir()
        (me / "local/open-window.ps1").write_text("# my own Windows part, flow 56\n")
        (me / "workspace").mkdir()
        (me / "workspace/me.md").write_text("# mine\n")
        with open(me / "README.md", "a") as f:
            f.write("my own line, flow 56\n")
        (me / "mine.txt").write_text("my own file, flow 56\n")
        # The newer version on the "public repo".
        (up / "app").mkdir()
        (up / "app/hello.txt").write_text("new in 0.3\n")
        (up / "CHANGELOG.md").write_text(log("## 0.3 · 2 January 2026\n\n### New\n- Flow fifty-six's new thing.\n\n### Fixed\n- A fix in 0.3.\n\n"))
        g(up, "add", "-A"); g(up, "commit", "-qm", "0.3"); g(up, "tag", "-a", "v0.3", "-m", "HQ 0.3")
        rm = self.tmp / "roadmap-H59.md"
        rm.write_text("# test\n\n## The queue\n\n**Routine:** on\n")
        busy = {"calls": 0}
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                b = json.dumps(busy).encode()
                self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(b)
            def log_message(self, *a):
                pass
        srv = socketserver.TCPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        env = {**os.environ, "HQ_UPDATE_URL": str(up), "HQ_PLATFORM": "win32", "HQ_UPDATE_RESTART": "0",
               "HQ_ROADMAP": str(rm), "HQ_CALL_URL": f"http://127.0.0.1:{srv.server_address[1]}"}
        env.pop("HQ_LOCAL", None)
        def upd(*a, e=env):
            r = sp.run(["python3", str(me / "routine/update.py"), *a], capture_output=True, text=True, env=e, timeout=120)
            need(r.returncode == 0, f"update.py {' '.join(a)}: {r.stderr.strip()[-300:]}")
            return json.loads(r.stdout.strip().splitlines()[-1]) if a[0] != "run" else None
        def wait_run(until, secs=60):
            end = time.time() + secs
            while time.time() < end:
                s = upd("status")
                if until(s["run"]):
                    return s
                time.sleep(0.5)
            need(False, f"the update didn't get there in time: {upd('status')['run']}")
        try:
            v = json.loads(sp.run(["python3", str(me / "routine/update.py"), "version"], capture_output=True, text=True, env=env).stdout)
            need(v["version"] == "0.2", f"it doesn't know its own version: {v}")
            # Offline: quiet, nothing breaks.
            off = upd("check", "--force", e={**env, "HQ_UPDATE_URL": str(base / "nowhere")})
            need(off["offline"] and not off["available"], f"offline isn't quiet: {off}")
            c = upd("check", "--force")
            need(c["available"] and c["latest"] == "0.3" and not c["offline"], f"the check doesn't see v0.3: {c}")
            s = upd("status")
            items = [i for sec in s["new"] for grp in sec["groups"] for i in grp["items"]]
            need(s["available"] and not s["mac"] and "Flow fifty-six's new thing." in items, f"what's new isn't there: {s}")
            need(not (me / "app/hello.txt").exists(), "the check changed HQ before Update was tapped")
            # Update.
            upd("start")
            s = wait_run(lambda r: r.get("state") in ("done", "failed"))
            need(s["run"]["state"] == "done", f"the update didn't go through: {s['run']}")
            need(g(me, "describe", "--tags") == "v0.3" and (me / "app/hello.txt").exists(), "HQ isn't on v0.3 after the update")
            need((me / "local/open-window.ps1").read_text() == "# my own Windows part, flow 56\n", "the own part in local/ didn't survive")
            need((me / "workspace/me.md").read_text() == "# mine\n", "the workspace didn't survive")
            br = s["run"]["saved"]["changes"]["branch"]
            need(br.startswith("hq-backup/") and "my own line, flow 56" in g(me, "show", f"{br}:README.md")
                 and "my own file" in g(me, "show", f"{br}^3:mine.txt"), f"the user's changes aren't on the backup branch: {br}")
            need(g(me, "remote", "get-url", "origin") == str(up) and not g(me, "branch", "-r", "--contains", br),
                 "the backup went somewhere")
            note = (me / s["run"]["notes"]).read_text()
            need("Flow fifty-six's new thing." in note and br in note and "isn't a Mac" in note and "local/" in note,
                 f"the note for their Claude is missing something: {note[:400]}")
            s = upd("status")
            need(s["version"] == "0.3" and not s["available"] and s["latest"] == "0.3", f"after the update it isn't the latest: {s}")
            need("updating" not in s["run"]["state"], "the update still says it's running")
            # A call on: the next update waits, says so, and starts by itself when the call ends.
            (up / "app/hello.txt").write_text("new in 0.3.1\n")
            g(up, "commit", "-qam", "0.3.1"); g(up, "tag", "-a", "v0.3.1", "-m", "HQ 0.3.1")
            need(upd("check", "--force")["available"], "the check doesn't see v0.3.1")
            busy["calls"] = 1
            upd("start")
            s = wait_run(lambda r: "call to end" in (r.get("step") or ""), 30)
            need(g(me, "describe", "--tags") == "v0.3", "the update went ahead during a call")
            busy["calls"] = 0
            s = wait_run(lambda r: r.get("state") in ("done", "failed"), 60)
            need(s["run"]["state"] == "done" and g(me, "describe", "--tags") == "v0.3.1", f"it didn't update once the call ended: {s['run']}")
            need((me / "local/open-window.ps1").exists(), "local/ didn't survive the second update")
        finally:
            srv.shutdown()
        return ("sees v0.3 and what's new; offline quiet; Update saves changes on a backup branch, moves to v0.3, "
                "local/ and workspace kept, note for their Claude (not a Mac); waits for a call to end, then updates")

    # 57
    async def flow57(self) -> str:
        """H59 on the pages: the small grey version, the new-version bar, the changelog, the warning off a Mac,
        nothing during a call, and 'the latest version' when there's nothing newer. update-ui.js in a headless
        browser with made-up answers (no network, no update); then that the status page, the call page, the Mac
        app's strip and the phone version carry it, and the live status server answers."""
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found")
        js = (ROOT / "status/update-ui.js").read_text()
        harness = r"""<!doctype html><html><head><meta charset="utf-8"></head><body>
<div id="line"></div><div id="banner"></div>
<script>
const NEW = {version:"0.2", tag:"v0.2", ahead:0, latest:"0.3", available:true, new_tag:"v0.3", checked:1, offline:false, mac:false,
  new:[{title:"0.3 · 2 January 2026", version:"0.3", coming:false, groups:[{name:"New", items:["Flow fifty-seven's thing"]}]}], run:{state:"idle"}};
const LOG = {version:"0.2", ahead:0, versions:[{title:"0.2 · 1 January 2026", version:"0.2", coming:false, current:true, groups:[{name:"New", items:["The first version"]}]}]};
let ST = NEW, posted = [], onCall = false;
window.fetch = async (p, o) => { if (o && o.method === "POST") posted.push(p);
  const body = p.includes("changelog") ? LOG : ST; return { ok: true, json: async () => JSON.parse(JSON.stringify(body)) }; };
</script>
<script>__JS__</script>
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const check = (n, ok, why) => out.push(n + ":" + (ok ? "ok" : "WRONG " + why));
  HQUpdate.mount({ line: document.getElementById("line"), banner: document.getElementById("banner"), busy: () => onCall });
  await wait(100);
  const ver = document.getElementById("hqu-ver"), bar = document.getElementById("hqu-bar"), sheet = document.getElementById("hqu-sheet");
  check("grey-version", ver.textContent.startsWith("v0.2") && getComputedStyle(ver).fontSize === "12px", ver.textContent);
  check("bar", bar.classList.contains("show") && bar.textContent.includes("v0.3 is out") && bar.textContent.includes("Flow fifty-seven") && bar.textContent.includes("Update"), bar.textContent);
  onCall = true; hqUpdate.render();
  check("no-bar-on-call", !bar.classList.contains("show"), bar.className);
  onCall = false; hqUpdate.render();
  [...bar.querySelectorAll("button")].find(b => b.textContent === "Update").click(); await wait(50);
  check("warning-off-mac", sheet.classList.contains("open") && sheet.textContent.includes("isn’t a Mac") && sheet.textContent.includes("instructions")
        && posted.length === 0, sheet.textContent.slice(0, 80) + "/" + posted.length);
  [...sheet.querySelectorAll("button")].find(b => b.textContent === "Cancel").click(); await wait(50);
  check("cancel", !sheet.classList.contains("open") && posted.length === 0, posted.length);
  [...bar.querySelectorAll("button")].find(b => b.textContent === "Update").click(); await wait(50);
  [...sheet.querySelectorAll("button")].find(b => b.textContent === "Update").click(); await wait(50);
  check("update-starts", posted.length === 1 && posted[0].includes("api/update/start"), posted.join(","));
  ST = { ...NEW, mac: true }; posted = []; await hqUpdate.poll(); await wait(50);
  [...bar.querySelectorAll("button")].find(b => b.textContent === "Update").click(); await wait(50);
  check("mac-no-warning", posted.length === 1 && !sheet.classList.contains("open"), posted.length);
  ST = { ...NEW, available:false, latest:"0.2", new:[], new_tag:null, mac:true }; await hqUpdate.poll(); await wait(50);
  check("latest", ver.textContent.includes("the latest version") && !bar.classList.contains("show"), ver.textContent);
  ver.click(); await wait(100);
  check("changelog", sheet.classList.contains("open") && sheet.textContent.includes("running the latest version, v0.2") && sheet.textContent.includes("The first version")
        && sheet.textContent.includes("you’re here"), sheet.textContent.slice(0, 160));
  const pre = document.createElement("pre"); pre.id = "r"; pre.textContent = "H59RESULT " + out.join(" | ") + " END"; document.body.appendChild(pre);
})();
</script></body></html>"""
        f = self.tmp / "h59.html"
        f.write_text(harness.replace("__JS__", js.replace("</script", "<\\/script")))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", f"--user-data-dir={self.tmp / 'h59-profile'}",
                                          "--virtual-time-budget=10000", "--dump-dom", f.as_uri()], timeout=90)
        m = re.search(r'<pre id="r">H59RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        say(f"   {m.group(1)}")
        need(all(p.endswith(":ok") for p in m.group(1).split(" | ")), f"the version bar doesn't behave: {m.group(1)}")
        # The pages carry it.
        status_page = (ROOT / "status/index.html").read_text()
        call_page = (APP / "web/index.html").read_text()
        need("update-ui.js" in status_page and "HQUpdate.mount" in status_page, "the status page doesn't show the version")
        need("update-ui.js" in call_page and "HQUpdate.mount" in call_page and "state !== \"idle\"" in call_page, "the call page doesn't show the version, or not quiet on a call")
        shell = (ROOT / "desktop/shell.html").read_text()
        need('id="ver"' in shell and 'id="newver"' in shell and "changelog" in (ROOT / "desktop/HQ.swift").read_text()
             and "changelog" in (ROOT / "desktop/phone.js").read_text(), "the Mac app's strip or the phone version doesn't show the version")
        bot = (APP / "bot.py").read_text()
        need("/api/busy" in bot and "/api/update" in bot and "/update-ui.js" in bot, "the call server doesn't answer the version")
        need("/local/" in (ROOT / ".gitignore").read_text(), "local/ isn't ignored by HQ's repo")
        need((ROOT / "CHANGELOG.md").exists() and "## 0.1" in (ROOT / "CHANGELOG.md").read_text() and "## 0.2" in (ROOT / "CHANGELOG.md").read_text(),
             "there's no changelog with 0.1 and 0.2")
        need("0.2.1" in (ROOT / "README.md").read_text() and "local/" in (ROOT / "ABOUT.md").read_text(), "the readme or the big picture doesn't say it")
        code, body, _ = await asyncio.to_thread(http_get, "/api/update", "http://127.0.0.1:4748")
        live = json.loads(body) if code == 200 else {}
        need(live.get("version") and "available" in live, f"the live status server doesn't answer the version: {code}")
        code, body, _ = await asyncio.to_thread(http_get, "/api/changelog", "http://127.0.0.1:4748")
        need(code == 200 and json.loads(body).get("versions"), f"the live status server doesn't serve the changelog: {code}")
        code, _, _ = await asyncio.to_thread(http_get, "/api/update/start", "http://127.0.0.1:4748")
        need(code == 403, f"an update can be started without the page's header: {code}")
        return "grey version, bar, quiet on a call, warning off a Mac with Cancel, no warning on a Mac, latest version, changelog; all pages carry it"

    async def flow65(self) -> str:
        """H56.3: main and backup. Two throwaway HQs (A, the laptop, and B, the server), each a copy of HQ with the
        blank template and its own memory and status server on spare ports, nothing of the user's, both with their
        routine and mail check switched off so nothing real ever starts. On this computer, and with a Linux machine
        too (HQ_TEST_LINUX=<ssh host>). Checked: alone, an HQ is main and never looks for another; paired, the
        choice of main reaches the other one; on the backup a call's job and planned item go to the main, git isn't
        committed and the routine's mail, jobs and scheduler lines say they run on the main; with the main down
        the backup keeps a request, takes over after the few minutes (here 4 seconds) and runs it, opening an
        incident; when the main is back it becomes the backup until the other has finished its job, then gets
        the role back; making this one main from a call works with the other one down, and the other one takes
        that choice over when it's back. Then everything is removed again."""
        import subprocess as sp, importlib
        jv = ROOT
        sys.path.insert(0, str(jv / "routine"))
        hqpaths = importlib.import_module("hqpaths")
        files = sp.run(["git", "-C", str(jv), "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True).stdout
        files = "\n".join(l for l in files.splitlines() if l and not l.startswith("workspace"))
        tar = sp.run(["tar", "--no-xattrs", "-czf", "-", "-T", "-"] if hqpaths.IS_MAC else ["tar", "-czf", "-", "-T", "-"],
                     input=files.encode(), capture_output=True, cwd=str(jv), env={**os.environ, "COPYFILE_DISABLE": "1"})
        need(tar.returncode == 0, f"couldn't pack HQ: {tar.stderr.decode()[:200]}")
        # H56.7: a test's roadmap copy is always on its own, so flows run on a paired backup never reach the
        # real main's job list.
        iso = sp.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import role; print(role.config())",
                      str(jv / "routine")], capture_output=True, text=True,
                     env={**{k: v for k, v in os.environ.items() if k != "HQ_SUPPORT"}, "HQ_ROADMAP": "/nonexistent/roadmap.md"})
        need(iso.stdout.strip() == "{}", f"a test's roadmap copy reads the real pairing: {iso.stdout.strip()[:120]}")
        tag = f"hqflow65-{os.getpid()}"
        script = FLOW65_SCRIPT.replace("@TAG@", tag)
        notes = []
        places = [("this Mac" if hqpaths.IS_MAC else "here", lambda cmd, **k: sp.run(["bash", "-c", cmd], **k), "/tmp")]
        host = os.environ.get("HQ_TEST_LINUX")
        if host and not hqpaths.IS_LINUX:
            places.append((host, lambda cmd, **k: sp.run(["ssh", "-o", "BatchMode=yes", host, cmd], **k), "$HOME"))
        for where, run_there, base in places:
            r = run_there(f'T="{base}/{tag}"; mkdir -p "$T" && cat > "$T/hq.tgz"', input=tar.stdout, capture_output=True)
            need(r.returncode == 0, f"couldn't copy HQ to {where}: {r.stderr.decode()[:200]}")
            r = run_there("bash -s", input=script.replace("@BASE@", base).encode(), capture_output=True, timeout=300)
            out = r.stdout.decode() + r.stderr.decode()
            left = run_there(f'ls -d "{base}/{tag}" 2>/dev/null', capture_output=True).stdout.decode().strip()
            need("ALL OK" in out, f"on {where}: " + next((l[5:] for l in out.splitlines() if l.startswith("FAIL ")), out.strip()[-400:]))
            need(not left, f"the test left something behind on {where}: {left}")
            oks = [l[3:] for l in out.splitlines() if l.startswith("OK ")]
            notes.append(f"on {where}: " + "; ".join(oks) + "; everything removed again")
        if not host and not hqpaths.IS_LINUX:
            notes.append("on Linux skipped: set HQ_TEST_LINUX=<ssh host> to run it there too")
        return " · ".join(notes)


    async def flow66(self) -> str:
        """H56.4: the two-way sync. Two private, throwaway Syncthings (A, the laptop, and B, the server) on spare
        ports, talking only to each other on this computer (no discovery, no relays), each with a throwaway HQ,
        the blank template as its workspace (a git repo with a throwaway origin) and its own memory folder;
        nothing of the user's, and the user's own Syncthing is never touched. On this computer, and with a Linux
        machine too (HQ_TEST_LINUX=<ssh host>). Checked: alone, the sync does nothing and shows no line; set up,
        a change on either side shows up on the other within seconds, the memory folder too; video, audio, git's
        folder and this computer's own Claude settings never go over; the main commits what came over and pushes
        it, the backup commits nothing; both sides changing the same note at once keeps both (a conflict copy),
        the line and the incidents say so and the main queues one merge job (once); once merged, the line is
        green and the incident closed; an HQ that becomes main lines its git up with GitHub, keeping the files;
        the routine's own minute writes the sync line; remove stops it and leaves the files. Then everything is
        removed again."""
        import subprocess as sp, importlib
        jv = ROOT
        sys.path.insert(0, str(jv / "routine"))
        hqpaths = importlib.import_module("hqpaths")
        files = sp.run(["git", "-C", str(jv), "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True).stdout
        files = "\n".join(l for l in files.splitlines() if l and not l.startswith("workspace"))
        tar = sp.run(["tar", "--no-xattrs", "-czf", "-", "-T", "-"] if hqpaths.IS_MAC else ["tar", "-czf", "-", "-T", "-"],
                     input=files.encode(), capture_output=True, cwd=str(jv), env={**os.environ, "COPYFILE_DISABLE": "1"})
        need(tar.returncode == 0, f"couldn't pack HQ: {tar.stderr.decode()[:200]}")
        tag = f"hqflow66-{os.getpid()}"
        script = FLOW66_SCRIPT.replace("@TAG@", tag)
        notes = []
        places = [("this Mac" if hqpaths.IS_MAC else "here", lambda cmd, **k: sp.run(["bash", "-c", cmd], **k), "/tmp")]
        host = os.environ.get("HQ_TEST_LINUX")
        if host and not hqpaths.IS_LINUX:
            places.append((host, lambda cmd, **k: sp.run(["ssh", "-o", "BatchMode=yes", host, cmd], **k), "$HOME"))
        for where, run_there, base in places:
            r = run_there(f'T="{base}/{tag}"; mkdir -p "$T" && cat > "$T/hq.tgz"', input=tar.stdout, capture_output=True)
            need(r.returncode == 0, f"couldn't copy HQ to {where}: {r.stderr.decode()[:200]}")
            r = run_there("bash -s", input=script.replace("@BASE@", base).encode(), capture_output=True, timeout=330)
            out = r.stdout.decode() + r.stderr.decode()
            left = run_there(f'ls -d "{base}/{tag}" 2>/dev/null', capture_output=True).stdout.decode().strip()
            need("ALL OK" in out, f"on {where}: " + next((l[5:] for l in out.splitlines() if l.startswith("FAIL ")), out.strip()[-400:]))
            need(not left, f"the test left something behind on {where}: {left}")
            oks = [l[3:] for l in out.splitlines() if l.startswith("OK ")]
            notes.append(f"on {where}: " + "; ".join(oks) + "; everything removed again")
        if not host and not hqpaths.IS_LINUX:
            notes.append("on Linux skipped: set HQ_TEST_LINUX=<ssh host> to run it there too")
        return " · ".join(notes)


    async def flow67(self) -> str:
        """F17: under a test, jobs.py, schedule.py and set-status.py refuse the real workspace's roadmap, and the real
        pairing is never used. Proven on throwaway copies standing in for the real ones; the real job list is only
        read, before and after."""
        import subprocess as sp
        sys.path.insert(0, str(ROOT / "routine"))
        def queue_parts(text):
            parts = []
            for heading in ("## The queue", "## The schedule"):
                i = text.find("\n" + heading + "\n")
                j = text.find("\n## ", i + 1) if i >= 0 else -1
                parts.append(text[i:j] if i >= 0 else "")
            return parts
        real_before = queue_parts(ROADMAP.read_text())
        need(os.environ.get("HQ_UNDER_TEST") == "1", "the happy flows don't mark themselves as a test")
        need(os.path.realpath(os.environ.get("HQ_REAL_ROADMAP", "")) == os.path.realpath(ROADMAP),
             f"the happy flows don't name the real roadmap: {os.environ.get('HQ_REAL_ROADMAP')}")
        fake_real = self.tmp / "f17-real" / "roadmap.md"   # stands in for the real one
        fake_real.parent.mkdir(parents=True, exist_ok=True)
        fake_real.write_text(ROADMAP.read_text())
        own = self.tmp / "f17-own.md"                      # a test's own copy
        own.write_text(ROADMAP.read_text())
        support = self.tmp / "f17-support"                 # stands in for this computer's real HQ memory
        support.mkdir(exist_ok=True)
        (support / "role.json").write_text(json.dumps({"name": "here", "peer": "https://127.0.0.1:9/", "peer_name": "there",
                                                      "main": "there", "chosen_at": 1}))
        (support / "role-state.json").write_text(json.dumps({"acting": "backup"}))
        base = {**os.environ, "HQ_UNDER_TEST": "1", "HQ_REAL_ROADMAP": str(fake_real), "HQ_REAL_SUPPORT": str(support),
                "HQ_SUPPORT": str(support)}
        def run(script, *a, roadmap, extra=None):
            env = {**base, "HQ_ROADMAP": str(roadmap), **(extra or {})}
            path = ROOT / ("status" if script == "set-status.py" else "routine") / script
            return sp.run([sys.executable, str(path), *a], capture_output=True, text=True, env=env, timeout=60)
        untouched = fake_real.read_text()
        for script, args in (("jobs.py", ["add", "flow 67 job", "--kind", "other"]), ("jobs.py", ["off"]),
                             ("schedule.py", ["add", "tomorrow 9:30", "flow 67 planned"]),
                             ("set-status.py", ["BUILDING", "flow 67", "", "", "Phase F|F17 🔨", "flow 67"])):
            r = run(script, *args, roadmap=fake_real, extra={"HQ_SUPPORT": str(self.tmp / "f17-other")})
            need(r.returncode != 0 and "F17" in r.stderr, f"{script} {args[0]} wasn't refused on the real roadmap: {r.returncode} {r.stdout[-200:]} {r.stderr[-200:]}")
        need(fake_real.read_text() == untouched, "a refused write still changed the real roadmap")
        r = run("jobs.py", "list", roadmap=fake_real, extra={"HQ_SUPPORT": str(self.tmp / "f17-other")})
        need(r.returncode == 0, f"reading the real list under a test was refused: {r.stderr[-200:]}")
        r = run("jobs.py", "add", "flow 67 own job", "--kind", "other", roadmap=own, extra={"HQ_SUPPORT": str(self.tmp / "f17-other")})
        need(r.returncode == 0 and "flow 67 own job" in own.read_text(), f"a test's own copy can't be written: {r.stderr[-200:]}")
        # The real pairing: a test on this computer's real HQ memory (here a stand-in, paired as the backup) isn't
        # paired, so a call's write stays on the test's own copy and nothing is handed on or kept for the main.
        own2 = self.tmp / "f17-own2.md"
        own2.write_text(ROADMAP.read_text())
        r = run("jobs.py", "add", "flow 67 not forwarded", "--kind", "other", roadmap=own2)
        need(r.returncode == 0 and "flow 67 not forwarded" in own2.read_text() and "handed" not in r.stdout,
             f"a test on the real pairing didn't stay on its own copy: {r.returncode} {r.stdout[-200:]} {r.stderr[-200:]}")
        need(not (support / "role-pending.jsonl").exists(), "a test's request was kept to be handed to the real main")
        r = sp.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import role; sys.exit(role.forward('jobs', ['add', 'x']))",
                    str(ROOT / "routine")], capture_output=True, text=True, env={**base, "HQ_ROADMAP": str(own2)}, timeout=30)
        need(r.returncode == 3 and "F17" in r.stderr and not (support / "role-pending.jsonl").exists(),
             f"handing on through the real pairing wasn't refused: {r.returncode} {r.stderr[-200:]}")
        probe = "import sys; sys.path.insert(0, sys.argv[1]); import role; print(bool(role.config()), role.acting())"
        r = sp.run([sys.executable, "-c", probe, str(ROOT / "routine")], capture_output=True, text=True,
                   env={**base, "HQ_ROADMAP": str(own2)}, timeout=30)
        need(r.stdout.split() == ["False", "main"], f"a test still reads the real pairing: {r.stdout} {r.stderr[-200:]}")
        env = {k: v for k, v in base.items() if k not in ("HQ_UNDER_TEST", "HQ_ROADMAP")}
        r = sp.run([sys.executable, "-c", probe, str(ROOT / "routine")], capture_output=True, text=True, env=env, timeout=30)
        need(r.stdout.split() == ["True", "backup"], f"outside a test the pairing should be read (the check itself is wrong): {r.stdout} {r.stderr[-200:]}")
        # Throwaway HQs with their own memory may still pair under a test (flow 65).
        r = sp.run([sys.executable, "-c", probe, str(ROOT / "routine")], capture_output=True, text=True,
                   env={**base, "HQ_ROADMAP": str(own2), "HQ_REAL_SUPPORT": str(self.tmp / "f17-other")}, timeout=30)
        need(r.stdout.split() == ["True", "backup"], f"a throwaway HQ's own pairing is refused under a test: {r.stdout} {r.stderr[-200:]}")
        need(queue_parts(ROADMAP.read_text()) == real_before, "the real job list or schedule changed during the flow")
        return ("jobs.py, schedule.py and set-status.py refuse the real roadmap under a test (a stand-in copy, unchanged); "
                "reading it still works, a test's own copy is written; the real pairing is never read or used; "
                "throwaway HQs still pair; the real job list unchanged")

    # 68
    async def flow68(self) -> str:
        """H72: the hidden Yes. No Claude turns. The real call page in a headless browser at phone width,
        on a fake live call: with nothing typed Send stays greyed out; a short hold shows nothing and sends
        nothing; a hold of a moment shows a small Yes above it, Send still greyed out; sliding onto Yes and
        letting go sends "Yes" as a typed turn; letting go elsewhere sends nothing; with text typed, or off a
        call, no Yes ever shows. No hint on the page. On the server a typed "Yes" goes the same way as a
        typed or spoken yes, so it answers a question waiting for his yes."""
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
  const shown = () => yesBtn.classList.contains("show") && yesBtn.getBoundingClientRect().height > 0;
  const mid = el => { const r = el.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; };
  const at = (el) => { const [x, y] = mid(el); return document.elementFromPoint(x, y); };
  const pe = (type, x, y) => sendWrap.dispatchEvent(new PointerEvent(type, { pointerId: 7, pointerType: "touch", isPrimary: true, clientX: x, clientY: y, bubbles: true, cancelable: true }));
  const [sx, sy] = mid(typeSend);
  check("greyed", typeSend.disabled && getComputedStyle(typeSend).opacity < 0.6 && !shown(), typeSend.disabled + "/" + getComputedStyle(typeSend).opacity);
  check("touch-reaches", sendWrap.contains(at(typeSend)), String(at(typeSend) && at(typeSend).id));
  // a short hold: nothing shows, nothing goes
  pe("pointerdown", sx, sy); await wait(600);
  check("short-hidden", !shown(), yesBtn.className);
  pe("pointerup", sx, sy); await wait(30);
  check("short-nothing", sent.length === 0, JSON.stringify(sent));
  // a hold of a moment: Yes shows above Send, Send still greyed out
  pe("pointerdown", sx, sy); await wait(1700);
  const yb = yesBtn.getBoundingClientRect(), sb = typeSend.getBoundingClientRect();
  check("shows", shown() && yb.bottom <= sb.top && typeSend.disabled, yesBtn.className + " " + yb.bottom + "/" + sb.top);
  const [yx, yy] = mid(yesBtn);
  pe("pointermove", yx, yy); await wait(30);
  check("over", yesBtn.classList.contains("over"), yesBtn.className);
  pe("pointerup", yx, yy); await wait(30);
  check("sends-yes", sent.length === 1 && sent[0].type === "typed" && sent[0].text === "Yes", JSON.stringify(sent));
  check("gone-after", !shown() && typeIn.value === "" && typeSend.disabled, yesBtn.className);
  // shown, but let go on Send itself: nothing
  pe("pointerdown", sx, sy); await wait(1700);
  pe("pointermove", yx, yy); pe("pointermove", sx, sy); await wait(30);
  check("off-again", shown() && !yesBtn.classList.contains("over"), yesBtn.className);
  pe("pointerup", sx, sy); await wait(30);
  check("elsewhere-nothing", sent.length === 1 && !shown(), JSON.stringify(sent));
  // a cancelled touch: nothing
  pe("pointerdown", sx, sy); await wait(1700); pe("pointercancel", yx, yy); await wait(30);
  check("cancel-nothing", sent.length === 1 && !shown(), JSON.stringify(sent));
  // something typed: Send is Send, no Yes
  typeIn.value = "hello"; typeIn.dispatchEvent(new Event("input", { bubbles: true })); await wait(30);
  pe("pointerdown", sx, sy); await wait(1700);
  check("typed-no-yes", !typeSend.disabled && !shown(), typeSend.disabled + "/" + yesBtn.className);
  pe("pointerup", sx, sy);
  typeIn.value = ""; typeIn.dispatchEvent(new Event("input", { bubbles: true })); await wait(30);
  // a Yes showing when the call ends goes away; off a call nothing shows
  pe("pointerdown", sx, sy); await wait(1700);
  setState("idle", ""); await wait(30);
  check("call-ends", !shown(), yesBtn.className);
  pe("pointerup", yx, yy); pe("pointerdown", sx, sy); await wait(1700);
  check("off-call", !shown() && sent.length === 1, yesBtn.className + " " + sent.length);
  pe("pointerup", yx, yy);
  // hidden: no hint anywhere
  check("hidden", yesBtn.getAttribute("aria-hidden") === "true" && !yesBtn.title && !typeSend.title && !sendWrap.title && yesBtn.tabIndex === -1, "hint");
  const pre = document.createElement("pre"); pre.id = "h72"; pre.textContent = "H72RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f = self.tmp / "h72.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", "--window-size=390,844",
                                          f"--user-data-dir={self.tmp / 'h72-profile'}", "--virtual-time-budget=30000", "--dump-dom", f.as_uri()], timeout=90)
        m = re.search(r'<pre id="h72">H72RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        res = m.group(1)
        say(f"   {res}")
        need(all(part.endswith(":ok") for part in res.split(" | ")), f"the hidden Yes is wrong: {res}")
        # No hint in the page's words: the only visible "Yes" is the button itself, and no hold or swipe hint.
        visible = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", page, flags=re.S)
        need(len(re.findall(r">\s*Yes\s*<", visible)) == 1 and not re.search(r"(?i)hold send|swipe|slide up", visible),
             "the page hints at the hidden Yes")
        # The server: a typed line is his turn like a spoken one, and that turn answers a waiting question.
        llm_src = (APP / "claude_llm.py").read_text()
        need("self.policy.answer(words)" in llm_src and 'message.get("type") == "typed"' in (APP / "bot.py").read_text(),
             "a typed line no longer answers a waiting question")
        from policy import is_clear_yes
        need(is_clear_yes("Yes"), "a typed Yes isn't a clear yes")
        return "nothing typed: Send greyed out; a moment's hold shows Yes above it; sliding onto it and letting go sends Yes as a typed turn, which answers a waiting yes question; elsewhere, a short hold, typed text or off a call: nothing; no hint"


    # 69
    async def flow69(self) -> str:
        """H76 and H77: each agent her own character on calls, as HQ's defaults a workspace can change. No Claude turns."""
        import agents
        from call import Call
        name = config.ME["name"] or None
        every = {a["id"]: a for a in agents.load(config.FOLDER)}
        agreed = {"donna": ("Hey you. What do you need?", "You said that yesterday too. Shall I just put it in?"),
                  "pepper": ("Hey{s}. What's on your mind?", "So... that's the third build today. Is this the needle mover, or the fun one?"),
                  "moneypenny": ("{N}Go ahead.", "Noted. It'll be done. Just not tonight.")}
        base = {a["id"]: a for a in agents.DEFAULTS}
        for aid, (greet, push) in agreed.items():
            a = base[aid]
            need(a.get("character") and a.get("personality") and a.get("pushback") == push and a.get("continue_greetings"),
                 f"{aid}: no character, personality, the agreed push-back or continue greetings in HQ's defaults")
            g = agents._greetings(a["greetings"])
            need(set(g) == set(agents.PARTS) and all(v[0] == greet for v in g.values()),
                 f"{aid}: the agreed greeting isn't first at every part of the day: {g}")
            need(agents.is_default(every[aid]) or (ROOT / "workspace/HQ/agents/agents.json").exists(), f"{aid} isn't marked HQ's default")
        need(agents.fill("Hey{s}. What's on your mind?", "Sam") == "Hey Sam. What's on your mind?"
             and agents.fill("Hey{s}. What's on your mind?", None) == "Hey. What's on your mind?"
             and agents.fill("{N}Go ahead.", "Sam") == "Sam. Go ahead." and agents.fill("{N}Go ahead.", None) == "Go ahead."
             and agents.fill("Morning{n}.", "Sam") == "Morning, Sam.", "the name from me.md isn't filled into the greetings right")
        greets = [set(g for p in agents.PARTS for g in agents.greetings(base[i] | {"greetings": agents._greetings(base[i]["greetings"])}, "Sam", p)) for i in agreed]
        need(not (greets[0] & greets[1] or greets[0] & greets[2] or greets[1] & greets[2]), "two agents share a greeting")
        src = (APP / "agents.py").read_text()
        need(not name or name not in src, "the user's name is written in HQ's agents.py")
        # H131: no "honestly" in any agent's own lines, and the human rules tell every agent not to say it.
        for a in base.values():
            lines = [a["character"], a["pushback"]] + [g for v in agents._greetings(a["greetings"]).values() for g in v] + a["continue_greetings"]
            need(not any(re.search(r"(?i)\bhonestly\b|\bmm\b", x) for x in lines), f"{a['id']} still says honestly or Mm: {lines}")
        need('never "honestly"' in agents.HUMAN, "the human rules don't drop honestly")
        need('never says "honestly"' in base["pepper"]["personality"] and "no one-liners" in base["pepper"]["personality"],
             "Pepper's character still invites honestly or one-liners (H131)")
        # H133: the job list is "the team" in what's said, on calls and in Donna's chat; "give it to the team" is his go.
        import direct_line
        need(config.TEAM_RULE in config.VOICE_RULES and config.TEAM_RULE in direct_line._text_rules()
             and '"Give it to the team"' in config.TEAM_RULE and '"Put it on the roadmap" means only the roadmap' in config.TEAM_RULE
             and "{" not in config.TEAM_RULE and '"the team"' in config.SYSTEM_PROMPT and '"the team"' in agents.HUMAN,
             "the call rules, Donna's chat or the agents still don't say the team (H133)")
        need("Job 29 is next" not in config.VOICE_RULES and "tell him it's queued" not in config.VOICE_RULES,
             "the call rules still have him hear job numbers or the queue (H133)")
        # Her character and the human rules after the call rules; no announcing tools or thinking out loud.
        p_ = every["pepper"]
        per = agents.persona(p_, "Sam")
        need(p_["personality"] in per and p_["pushback"] in per and agents.HUMAN in per and "thinking sound" in per,
             "her character, push-back line or the human rules aren't in what her session is told")
        need("Let me look at your calendar" not in config.VOICE_RULES and "Don't announce a tool" in config.VOICE_RULES
             and '"Good question."' not in config.VOICE_RULES, "the call rules still tell her to talk while she works")
        # A call greets in her words; the call system's own greetings only for an agent without any.
        for aid in ("donna", "pepper"):
            c = Call(model="sonnet", calls_dir=self.tmp / "calls69", wrap_up="dry", test_mode=True, agent=aid)
            want = agents.greetings(every[aid], name, config.day_part())
            need(c.agent["id"] == aid and c.fillers._texts["greeting"] == want and want,
                 f"{aid}'s call doesn't greet in her words: {c.fillers._texts['greeting']}")
            if c.transcript.path:
                c.transcript.path.unlink(missing_ok=True)
        need(config.greetings_now({"id": "x", "greetings": {}}) == config.GREETINGS[config.day_part()],
             "an agent without greetings doesn't get the call system's")
        # H77: a workspace's own character wins, only what it gives; marked as its own.
        ws = self.tmp / "agents69"
        (ws / "HQ" / "agents").mkdir(parents=True)
        (ws / "HQ" / "agents" / "agents.json").write_text(json.dumps([
            {"id": "donna", "character": "Soft and slow", "pushback": "Are you sure?", "greetings": ["Hello{s}."]},
            {"id": "pepper", "greetings": 42, "continue_greetings": [1, ""]},
            {"id": "coach", "name": "Coach", "load": "deep"}]))
        mine = {a["id"]: a for a in agents.load(ws)}
        d = mine["donna"]
        need(d["character"] == "Soft and slow" and d["pushback"] == "Are you sure?" and d["personality"] == base["donna"]["personality"]
             and all(agents.greetings(d, "Sam", p) == ["Hello Sam."] for p in agents.PARTS),
             f"the workspace's own character isn't applied, or not only what it gives: {d}")
        need(not agents.is_default(d), "a changed character still counts as HQ's default")
        need(mine["pepper"]["greetings"] == {} and mine["pepper"]["continue_greetings"] == [] and not agents.is_default(mine["pepper"]),
             "bad greetings in agents.json aren't dropped")
        need(config.greetings_now(mine["coach"]) == config.GREETINGS[config.day_part()] and not agents.is_default(mine["coach"]),
             "a new agent without greetings doesn't get the call system's")
        pub = agents.public(d)
        need(pub["character"] == "Soft and slow" and pub["default"] is False and "personality" not in pub and "pushback" not in pub,
             f"the page gets too much or doesn't know it's her own: {pub}")
        text = agents.describe(ws, "Sam")
        need("Donna (sonnet): Soft and slow. [changed in your workspace" in text and "Pepper (opus)" in text and "Hello Sam." in text,
             f"describe doesn't show the workspace's characters: {text[:300]}")
        r = await asyncio.to_thread(run, [sys.executable, str(APP / "agents.py")], timeout=60)
        need(r.returncode == 0 and "Donna (sonnet)" in r.stdout and "Pepper (opus)" in r.stdout and "Moneypenny (fable, coming soon)" in r.stdout,
             f"python3 app/agents.py doesn't print the agents: {(r.stderr or r.stdout)[-300:]!r}")
        # The page and the docs show the defaults.
        await self.ensure_server()
        code, body, _ = http_get("/api/agents")
        j = json.loads(body or b"{}")
        listed = j.get("agents", []) + j.get("soon", [])
        need(code == 200 and all(a.get("character") and "default" in a and "pushback" not in a for a in listed),
             f"/api/agents doesn't give each agent's character and whether it's the default: {body[:200]!r}")
        page = http_get("/")[1].decode()
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        harness = r"""<script>
setTimeout(() => {
  const out = [...document.querySelectorAll('#voices .row span')].map(s => s.firstChild.textContent + '=' + ((s.querySelector('small.character') || {}).textContent || 'none'));
  const pre = document.createElement('pre'); pre.id = 'h77'; pre.textContent = 'H77RESULT ' + out.join(' | ') + ' END'; document.body.append(pre);
}, 1500);
</script>"""
        f = self.tmp / "h77.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1).replace("<head>", f'<head><base href="{TEST_URL.rstrip("/")}/">', 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []), f"--user-data-dir={self.tmp / 'h77-profile'}",
                                          "--disable-web-security", "--virtual-time-budget=5000", "--dump-dom", f.as_uri()], timeout=60)
        m = re.search(r'<pre id="h77">H77RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the call page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        say(f"   {m.group(1)}")
        rows = dict(x.split("=", 1) for x in m.group(1).split(" | "))
        for a in [x for x in listed if not x.get("coming_soon")]:
            shown = rows.get("Voice " + a["full_name"], "none")
            need(shown.startswith(a["character"]) and (("HQ's default" in shown) == a["default"]),
                 f"Settings doesn't show {a['name']}'s character and whether it's the default: {shown}")
        readme = (ROOT / "README.md").read_text()
        tmpl = (ROOT / "template/HQ/agents/README.md").read_text()
        about = (ROOT / "ABOUT.md").read_text()
        need("python3 app/agents.py" in readme and "pushback" in readme and "agents.json" in readme and "HQ's defaults" in readme,
             "the readme doesn't tell their Claude the characters are defaults they can change")
        need(all(x in tmpl for x in ("Hey you. What do you need?", "Just not tonight.", '"pushback"', '"greetings"')),
             "the template's agents readme doesn't show the defaults and how to change them")
        need("Quick and dry" in about and "HQ's defaults" in about, "ABOUT.md doesn't describe the characters")
        # H132: what she says about herself is kept in her own list in the workspace, and comes with her persona
        import about_self, direct_line
        from policy import Policy
        ws = self.tmp / "h132"
        donna = agents.find(ws, "donna")
        need(donna["about_self"] == [] and "nothing yet" in agents.persona(donna, "Sam"), "an agent without a list isn't told so")
        need(about_self.add(ws, donna, "  I have a nice   chair by the window ") and not about_self.add(ws, donna, "I have a nice chair by the window."),
             "a fact isn't kept, or is kept twice")
        f = about_self.path(ws, "donna")
        need(f == ws / "HQ/agents/donna-about-herself.md" and f.read_text().count("- I have a nice chair by the window\n") == 1,
             f"her list isn't in the workspace's agents folder: {f}")
        donna, pepper = agents.find(ws, "donna"), agents.find(ws, "pepper")
        need("- I have a nice chair by the window" in agents.persona(donna, "Sam") and "chair by the window" not in agents.persona(pepper, "Sam"),
             "her list doesn't come with her own persona only")
        pol = Policy(config.FOLDER, dry_run=True)
        need(pol.decide("Bash", {"command": f'python3 "{ROOT}/app/about_self.py" add Donna "x"'}).verdict == "allow"
             and pol.decide("Bash", {"command": f'python3 "{ROOT}/app/about_self.py" rm Donna'}).verdict == "deny",
             "a call or her chat can't keep a fact (or can do more than list and add)")
        need("about_self.py\" add <her name>" in config.WRAP_UP_PROMPT and "@HQ@" not in config.WRAP_UP_PROMPT,
             "the after-call notes don't keep what an agent said about herself")
        need("about_self.py\" add donna" in direct_line._text_rules(), "her chat doesn't keep what she says about herself")
        need(not name or name not in (APP / "about_self.py").read_text(), "the user's name is written in HQ's about_self.py")
        need("about-herself" in tmpl, "the template's agents readme doesn't mention her own list")
        return ("Donna, Pepper and Moneypenny each with her agreed greeting and push-back, nothing personal; her character and no "
                "talking while she thinks; calls greet in her words; a workspace's own character wins and is marked; "
                "Settings, /api/agents, agents.py and the readme show the defaults; what she says about herself is kept in "
                "her own list and comes with her persona (H132)")


    # 70
    async def flow70(self) -> str:
        """H75: she hangs up herself after his clear goodbye. No Claude turns: the rules are read from
        what each kind of call gets, and the real call service is driven by a stand-in for Claude."""
        from claude_llm import ClaudeSessionLLMService, MarkFilter
        from pipecat.processors.aggregators.llm_context import LLMContext
        from pipeline import make_brain
        from policy import Policy
        mark = config.HANGUP_MARK
        # The mark is taken out of the speech, also when it streams in pieces.
        f = MarkFilter(mark)
        said = "".join(f.feed(x) for x in ["Bye, S", "am. [", "[END", " CALL]", "]"]) + f.flush()
        need(f.found and mark not in said and said.startswith("Bye, Sam."), f"the mark isn't taken out: {said!r}")
        f = MarkFilter(mark)
        said = "".join(f.feed(x) for x in ["Two [", "[notes]] and [x]"]) + f.flush()
        need(not f.found and said == "Two [[notes]] and [x]", f"ordinary brackets are lost or taken for the mark: {said!r}")
        # The rule is in every kind of call: Free (plain Claude) and the full call, with the phrases and the never-on list.
        rules = config.HANGUP_RULES
        for ph in ["that's it, see you later", "okay, that is all", "okay, thanks, appreciate you", "cheers",
                   "you're the best", "you are the best", "perfect, you're the best", "thanks, you are the best"]:
            need(ph in rules and ph in config.GOODBYE_PHRASES, f"the starting phrase {ph!r} is missing")
        need("a passing okay" in rules and "a pause or silence" in rules and "When you are not sure" in rules,
             "the rule doesn't say when not to hang up")
        free = make_brain(config.MODEL, None, cwd=self.tmp / "free70", free=True)
        need(rules in free._options.system_prompt, "a Free call doesn't get the hang-up rule")
        full = make_brain(config.MODEL, Policy(config.FOLDER, dry_run=True), load="deep")
        need(rules in full._options.system_prompt["append"], "a full call doesn't get the hang-up rule")
        need("{user}" not in rules, "the name in the rule isn't filled in from me.md")
        # H129: the goodbye comments on what he's doing right now: the appointment on now or soon in HQ's own saved
        # calendar, else his to-do list; Moneypenny keeps her own goodbye. Read from the saved days, no Claude run.
        need("H129" in rules and "what he's doing right now" in rules and "no tools" in rules,
             "the rule doesn't say to comment on what he's doing right now")
        for w in ["okay, thanks, appreciate you", "Cheers!", "bye", "That's it, see you later",
                  "Perfect, you're the best.", "Thanks, you are the best", "You\u2019re the best"]:
            need(config.sounds_like_goodbye(w), f"{w!r} isn't taken as a possible goodbye")
        for w in ["what's on my calendar today", "put that on the list", "add tea later today"]:
            need(not config.sounds_like_goodbye(w), f"{w!r} is taken as a goodbye")
        import agenda, agents
        from datetime import datetime as _dt, timedelta as _td
        cal_env = os.environ.get("HQ_CALENDAR_FILE")
        os.environ["HQ_CALENDAR_FILE"] = str(self.tmp / "cal129" / "calendar.json")
        try:
            t0 = _dt.now().astimezone().replace(second=0, microsecond=0)
            ev = lambda title, a, b, **k: {"id": title, "title": title, "start": (t0 + _td(minutes=a)).isoformat(),
                                           "end": (t0 + _td(minutes=b)).isoformat(), "all_day": False, **k}
            agenda._write({"events": [{"id": "d", "title": "A whole day", "start": t0.strftime("%Y-%m-%d"),
                                       "end": "", "all_day": True}]})
            n = agenda.goodbye_note("Sam")
            need("nothing in his calendar" in n and "to-do list" in n, f"without an appointment it isn't the to-do list: {n!r}")
            agenda._write({"events": [ev("Gym", 30, 90), ev("Lunch", -20, 20, where="the kitchen")]})
            n = agenda.goodbye_note("Sam")
            need("Lunch" in n and "the kitchen" in n and "on now" in n and "Gym" not in n,
                 f"the appointment on now isn't the one: {n!r}")
            agenda._write({"events": [ev("Gym", 30, 90), ev("Later thing", 200, 260)]})
            n = agenda.goodbye_note("Sam")
            need("Gym" in n and "starting at" in n and "Later" not in n, f"the one starting soon isn't the one: {n!r}")
            # Who gets the note: not Moneypenny (her own goodbye), not on Free, only on a turn that may be a goodbye.
            import call as _call
            mp = next(a for a in agents.load(config.FOLDER) if a["id"] == "moneypenny")
            pp = next(a for a in agents.load(config.FOLDER) if a["id"] == "pepper")
            need(mp.get("own_goodbye") and not pp.get("own_goodbye"), "Moneypenny doesn't keep her own goodbye")
            fake = type("C", (), {"free": False})()
            gb = _call.Call._goodbye_note
            need(gb(fake, pp, "cheers") and "Gym" in gb(fake, pp, "cheers")[0], "Pepper's goodbye turn gets no note")
            need(gb(fake, mp, "cheers") == [], "Moneypenny's goodbye turn gets the note")
            need(gb(fake, pp, "what's next on my list") == [], "an ordinary turn gets the goodbye note")
            fake.free = True
            need(gb(fake, pp, "cheers") == [], "a Free call gets his calendar in the goodbye note")
        finally:
            if cal_env is None:
                os.environ.pop("HQ_CALENDAR_FILE", None)
            else:
                os.environ["HQ_CALENDAR_FILE"] = cal_env

        class Stand:  # stands in for the Claude session: answers with the pieces it's given
            model = "stand-in"
            def __init__(self): self.replies = []
            async def start(self): pass
            async def stop(self): pass
            def cancel_turn(self): pass
            async def ask(self, text):
                for piece in self.replies.pop(0):
                    await asyncio.sleep(0.01)
                    yield piece

        class Script:  # what the transcript is told
            def __init__(self): self.replies = []
            def user(self, *a, **k): pass
            def note(self, *a, **k): pass
            def reply(self, text, cut_off=False): self.replies.append(text)

        brain, script = Stand(), Script()
        llm = ClaudeSessionLLMService(brain, transcript=script)
        spoken: list[str] = []
        async def nothing(*a, **k): pass
        async def speak(text): spoken.append(text)
        llm.push_frame = nothing
        llm._push_llm_text = speak
        llm.start_processing_metrics = llm.stop_processing_metrics = nothing
        llm.start_ttfb_metrics = llm.stop_ttfb_metrics = nothing
        hung: list[float] = []
        async def on_hangup(): hung.append(time.perf_counter())
        llm.on_hangup = on_hangup
        llm.HANGUP_QUIET_SECS, llm.HANGUP_NO_VOICE_SECS, llm.HANGUP_MAX_SECS = 0.3, 1.0, 5.0
        msgs: list[dict] = []
        async def turn(words, reply):
            msgs.append({"role": "user", "content": words})
            brain.replies.append(reply)
            await llm._process_context(LLMContext(messages=list(msgs)))
            msgs.append({"role": "assistant", "content": "".join(reply)})
        # 1. A passing okay: she answers, and stays on.
        await turn("Okay, and what about tomorrow?", ["Tomorrow is ", "free."])
        await asyncio.sleep(1.3)
        need(not hung and llm._hangup_task is None, "she hung up without a goodbye")
        # 2. His goodbye: the goodbye is spoken without the mark, and the call ends once it has been heard.
        spoken.clear()
        await turn("That's it, see you later.", ["See you", " later.", " [[END", " CALL]]"])
        need(mark not in "".join(spoken) and "See you later." in "".join(spoken), f"the mark was spoken: {spoken}")
        need(mark not in script.replies[-1], "the mark went into the transcript")
        llm._bot_speaking, llm._spoke_at = True, time.perf_counter()  # her voice says the goodbye
        await asyncio.sleep(0.6)
        need(not hung, "she hung up while her goodbye was still being spoken")
        llm._bot_speaking, llm._quiet_at = False, time.perf_counter()
        await asyncio.sleep(0.8)
        need(len(hung) == 1 and hung[0] - llm._quiet_at >= 0.25, "the call didn't end after the goodbye was heard")
        # 3. He says more right after her goodbye: the call goes on.
        hung.clear()
        await turn("Bye!", ["Bye.", "[[END CALL]]"])
        need(llm._hangup_task is not None, "no hang-up started after the goodbye")
        await turn("Oh wait, one more thing.", ["Sure, go ahead."])
        await asyncio.sleep(1.5)
        need(not hung, "she hung up although he said more")
        # The server and the page: the same way as his Hang up.
        bot = (APP / "bot.py").read_text()
        hook = bot.split("async def agent_hangs_up():", 1)[1].split("call.llm.on_hangup = agent_hangs_up", 1)[0]
        need('"hq-hangup"' in hook and "await worker.cancel()" in hook and "call.ended_by_agent = True" in hook,
             "the call server doesn't end the call like Hang up does")
        callpy = (APP / "call.py").read_text()
        need("hung up after the goodbye" in callpy, "the transcript doesn't say she hung up")
        page = (APP / "web/index.html").read_text()
        need('m.type === "hq-hangup" && state !== "idle") hangup();' in page,
             "the call page (phone and desktop app) doesn't close the call when she hangs up")
        return ("the mark is never spoken or written; the rule with its phrases is in Free and full calls; "
                "an okay keeps the call; a goodbye ends it once heard; more words after it keep it; H129: the goodbye note says what he's doing now (calendar, else to-do list), not for Moneypenny")

    async def flow85(self) -> str:
        """H79: ask for another agent by name: she hands over (the call ends as a hang-up does and the other one picks
        up a new call that continues it) or brings her in (a three-way call: one conversation, each turn the one who
        fits answers in her own model and voice). No Claude turns: a stand-in drives the real call service."""
        import agents as ag
        from call import Call
        from claude_llm import ClaudeSessionLLMService, Marks
        from pipecat.processors.aggregators.llm_context import LLMContext
        from transcript import CallTranscript, continue_from, read_lines
        every = ag.visible(config.FOLDER)
        need(len(every) >= 2, "fewer than two agents to switch between")
        one, two = every[0], every[1]
        # The rules: every other agent by name, hand over, three-way, and asking when it isn't clear.
        rules = ag.switch_rules(one, [two], "Sam")
        need(ag.SWITCH_MARK.format(name=two["name"]) in rules and ag.THREE_WAY_MARK.format(name=two["name"]) in rules
             and "secretary style" in rules and two["speciality"] in rules, "the rules miss a mark, or asking first")
        need(ag.switch_rules(one, [], "Sam") == "", "rules without anyone to switch to")
        # H122: "bring in" is always a three-way call, "give me" always hands over; asking only for other words.
        hand = next((l for l in rules.splitlines() if ag.SWITCH_MARK.format(name=two["name"]) in l), "")
        three = next((l for l in rules.splitlines() if ag.THREE_WAY_MARK.format(name=two["name"]) in l), "")
        need(f'Give me {two["name"]}' in hand and "connect me through" in hand and "always mean hand over, never ask" in hand
             and f'Bring in {two["name"]}' in three and "always mean a three-way call, never ask" in three
             and "Bring in" not in hand and "Give me" not in three, "H122: bring in and give me aren't fixed")
        marks = ag.switch_marks([two])
        # The marks are never spoken, also in pieces; ordinary brackets stay.
        m = Marks([config.HANGUP_MARK, *marks])
        sw = ag.SWITCH_MARK.format(name=two["name"])
        said = "".join(m.feed(x) for x in ["Putting her on. [", "[SWITCH ", two["name"] + "]", "]"]) + m.flush()
        need(m.found(sw) and not m.found(config.HANGUP_MARK) and said == "Putting her on. ", f"the mark isn't taken out: {said!r}")
        m = Marks([config.HANGUP_MARK, *marks])
        said = "".join(m.feed(x) for x in ["Two [", "[notes]] [x"]) + m.flush()
        need(said == "Two [[notes]] [x" and not any(m.found(k) for k in marks), f"ordinary brackets lost: {said!r}")
        # Who answers on a three-way call: the one named; else the one whose speciality fits; else the last one.
        a, b = dict(one, speciality="Your agenda, your list, mail and quick orders"), dict(two, speciality="Sparring, planning and the bigger picture")
        need(ag.pick([a, b], f"{b['name']}, what do you think?", a["id"]) is b, "the one named doesn't answer")
        need(ag.pick([a, b], f"Thanks {a['name']}. And {b['name']}?", a["id"]) is b, "named both: not the one named last")
        need(ag.pick([a, b], "Any new mail today?", b["id"]) is a, "mail doesn't go to the one for mail")
        need(ag.pick([a, b], "Let's plan the bigger picture for next week", a["id"]) is b, "planning doesn't go to the planner")
        need(ag.pick([a, b], "Hmm, okay.", b["id"]) is b, "nothing fits: not the one who answered last")

        class Stand:
            model = "stand-in"
            def __init__(self): self.replies, self.sent = [], []
            async def start(self): pass
            async def stop(self): pass
            def cancel_turn(self): pass
            async def ask(self, text):
                self.sent.append(text)
                for piece in self.replies.pop(0):
                    await asyncio.sleep(0.01)
                    yield piece

        class Script:
            def __init__(self): self.replies = []
            def user(self, *a, **k): pass
            def note(self, *a, **k): pass
            def reply(self, text, cut_off=False): self.replies.append(text)

        brain, script = Stand(), Script()
        llm = ClaudeSessionLLMService(brain, transcript=script)
        spoken: list[str] = []
        async def nothing(*a, **k): pass
        async def speak(text): spoken.append(text)
        llm.push_frame = nothing
        llm._push_llm_text = speak
        llm.start_processing_metrics = llm.stop_processing_metrics = nothing
        llm.start_ttfb_metrics = llm.stop_ttfb_metrics = nothing
        llm.HANGUP_QUIET_SECS, llm.HANGUP_NO_VOICE_SECS, llm.HANGUP_MAX_SECS = 0.3, 1.0, 5.0
        llm.switch_marks = marks
        switched, joined, hung = [], [], []
        async def on_switch(x): switched.append(x)
        async def on_join(x): joined.append(x)
        async def on_hangup(): hung.append(1)
        llm.on_switch, llm.on_three_way, llm.on_hangup = on_switch, on_join, on_hangup
        msgs: list[dict] = []
        async def turn(words, reply):
            msgs.append({"role": "user", "content": words})
            brain.replies.append(reply)
            await llm._process_context(LLMContext(messages=list(msgs)))
            msgs.append({"role": "assistant", "content": "".join(reply)})
        # Hand over: spoken without the mark, and only once her line has been heard.
        await turn(f"Give me {two['name']}.", ["Sure, putting her on.", " [[SWITCH ", two["name"], "]]"])
        need(sw not in "".join(spoken) + script.replies[-1], "the hand-over mark was spoken or written")
        llm._bot_speaking, llm._spoke_at = True, time.perf_counter()
        await asyncio.sleep(0.5)
        need(not switched, "handed over while her line was still being spoken")
        llm._bot_speaking, llm._quiet_at = False, time.perf_counter()
        await asyncio.sleep(0.7)
        need(switched == [two["id"]] and not hung and not joined, f"no hand-over after her line: {switched}")
        # Three-way: she joins right after the reply, nothing hangs up.
        await turn("Let's make it a three-way call.", ["Bringing her in.", ag.THREE_WAY_MARK.format(name=two["name"])])
        need(joined == [two["id"]] and len(switched) == 1 and llm._hangup_task is None, "the three-way call didn't start")
        # H130: once the line bringing her in has been heard, she says hi in a turn of her own; he speaking first drops it.
        queued, his = [], []
        async def queue(frame, *a, **k): queued.append(frame)
        async def hi(x):
            his.append(x)
            return ["[Call system: you are her. Say hi.]"]
        llm.queue_frame, llm.joined_hi = queue, hi
        joined.clear()
        await turn("Bring her in.", ["Bringing her in.", ag.THREE_WAY_MARK.format(name=two["name"])])
        need(joined == [two["id"]] and llm._hangup_task is not None and not queued, "she says hi before the line was heard")
        llm._bot_speaking, llm._spoke_at = True, time.perf_counter()
        await asyncio.sleep(0.5)
        need(not queued, "she says hi while the line bringing her in is still being spoken")
        llm._bot_speaking, llm._quiet_at = False, time.perf_counter()
        await asyncio.sleep(0.7)
        need(len(queued) == 1 and queued[0].agent == two["id"], f"no hi once the line was heard: {queued}")
        n_said = len(script.replies)
        brain.replies.append(["Hey, I'm here."])
        await llm._say_hi(queued[0].agent)
        need(his == [two["id"]] and brain.sent[-1] == "[Call system: you are her. Say hi.]" and script.replies[n_said:] == ["Hey, I'm here."]
             and llm.turns[-1]["hi"] and llm.turns[-1]["words"] == "", f"her hi isn't a turn of her own: {script.replies[n_said:]}")
        need(llm.late_cancel_target() is not llm.turns[-1], "Cancel would take back her hi instead of his last turn")
        queued.clear()
        await turn("Bring her in.", ["Bringing her in.", ag.THREE_WAY_MARK.format(name=two["name"])])
        await turn("Wait, one thing first.", ["Sure."])
        await asyncio.sleep(1.2)
        need(not queued and llm._hangup_task is None, "she still says hi after he spoke first")
        llm.joined_hi = None
        need("isinstance(frame, JoinedHiFrame)" in (APP / "claude_llm.py").read_text(), "the hi frame isn't run as a turn")
        # On the call: who answers, her voice, her notes, her lines in the transcript.
        calls = self.tmp / "calls85"
        c = Call(calls_dir=calls, test_mode=True, agent=one["id"], voices={one["id"]: "af_bella", two["id"]: "bf_emma"})
        need(c.llm.switch_marks == ag.switch_marks(c.others) and two["id"] in [x["id"] for x in c.others] and one["id"] not in [x["id"] for x in c.others],
             "the call doesn't know the others")
        need(await c._before_turn("hello") == [], "notes on a call with one agent")
        await c.three_way(two["id"])
        need([x["id"] for x in c.panel] == [one["id"], two["id"]], "she isn't on the call")
        notes = await c._before_turn(f"{two['name']}, what do you think?")
        need(c.speaker["id"] == two["id"] and c.tts._settings.voice == "bf_emma" and c.tts._settings.language == "en-gb"
             and c.fillers._voice == "bf_emma", "the voice didn't switch to hers")
        need(any("now on this call too" in n for n in notes) and f"{two['name']} answers this turn" in notes[-1],
             f"no note on who answers: {notes}")
        c.transcript.user("What do you think?")
        c.transcript.reply("I'd plan it first.")
        notes = await c._before_turn(f"And {one['name']}?")
        need(c.speaker["id"] == one["id"] and c.tts._settings.voice == "af_bella" and len(notes) == 1, "the voice didn't switch back")
        c.transcript.reply("Agreed.")
        lines = read_lines(c.transcript.path)
        need([ln.get("agent") for ln in lines if ln["who"] == "hq"] == [two["name"], one["name"]], f"her lines don't say who: {lines}")
        # H130: on the call, her hi: her voice and model from then on, a note to say she's there in her own words, once.
        e = Call(calls_dir=calls, test_mode=True, agent=one["id"], voices={one["id"]: "af_bella", two["id"]: "bf_emma"})
        need(e.llm.joined_hi == e._joined_hi and await e._joined_hi(two["id"]) == [], "a hi with nobody brought in")
        await e.three_way(two["id"])
        hi_notes = await e._joined_hi(two["id"])
        need(e.speaker["id"] == two["id"] and e.tts._settings.voice == "bf_emma" and e.transcript.speaker == two["name"]
             and len(hi_notes) == 2 and "has just been brought in" in hi_notes[0] and "a three-way call" in hi_notes[0]
             and f"you are {two['name']}" in hi_notes[1] and "never a set greeting" in hi_notes[1], f"her hi note: {hi_notes}")
        need(await e._joined_hi(two["id"]) == [] and not any("now on this call too" in x for x in await e._before_turn("Hi both.")),
             "she's told twice that she joined")
        await e.brain.stop()
        # H121: one still coming soon can be brought in too, never handed over to; then it's a four-way call.
        locked = ag.soon(config.FOLDER)
        if locked:
            three_ = locked[0]
            need(three_["id"] in [x["id"] for x in c.others] and ag.THREE_WAY_MARK.format(name=three_["name"]) in c.llm.switch_marks
                 and ag.SWITCH_MARK.format(name=three_["name"]) not in c.llm.switch_marks, "the locked one can't be brought in, or can take over")
            rules = ag.switch_rules(one, c.others, "Sam")
            need(f"{three_['name']} can only be brought in" in rules and "four-way call" in rules, "the rules don't say she only joins")
            await c.three_way(three_["id"])
            need(len(c.panel) == 3 and ag.way(c.panel) == "four-way", "no four-way call")
            notes = await c._before_turn(f"{three_['name']}, your turn.")
            need(c.speaker["id"] == three_["id"] and any("a four-way call" in x for x in notes)
                 and c.tts._settings.voice == c.voice_for(three_), f"she doesn't answer in her voice on the four-way call: {notes}")
            await c._before_turn(f"And {one['name']}?")
        # The hand-over: the other one gets it with the earlier agent's lines by name, and greets as picking up.
        c.transcript.end()
        cont = continue_from(c.transcript.path.stem, calls, me=two["name"])
        need(f"You: I'd plan it first." in cont["text"] and f"{one['name']}: Agreed." in cont["text"], f"continue text: {cont['text']}")
        d = Call(calls_dir=calls, test_mode=True, agent=two["id"], continues=c.transcript.path.stem, handover=True)
        need(f"{one['name']} just put you on the phone" in d._continue_note(), "the new call doesn't know it was handed over")
        need("Continues the call of" in d.transcript.path.read_text(), "the new transcript doesn't say which call it continues")
        c.switched_to, c.ended_by_agent = two, True
        c._finished = False; c.wrap_up_mode = "off"; c.llm.turns.append({"words": "What do you think?"})
        await c.finish()
        need(f"put {two['name']} on" in c.transcript.path.read_text(), "the transcript doesn't say she put the other one on")
        free = Call(calls_dir=calls, test_mode=True, free=True)
        need(free.others == [] and free.llm.switch_marks == {}, "Free calls can switch")
        # The server and the page.
        bot = (APP / "bot.py").read_text()
        need('"hq-switch"' in bot and '"hq-three-way"' in bot and "call.llm.on_switch" in bot and "call.llm.on_three_way" in bot
             and 'body.get("handover")' in bot and 'body.get("voices")' in bot, "the call server doesn't hand over or bring her in")
        page = (APP / "web/index.html").read_text()
        need('m.type === "hq-switch"' in page and "switchTo(m.agent, m.call)" in page and 'm.type === "hq-three-way"' in page
             and "handover: true" in page and "voices: Object.fromEntries" in page and "return panel.length ? panel : [agent]" in page,
             "the call page doesn't call the other one or show the three-way call")
        for x in (c, d, free):
            await x.brain.stop()
        return ("hand-over and three-way marks never spoken; hand-over once heard, the other continues the call as picking "
                "up; three-way keeps one conversation, the one named or fitting answers in her voice; lines say who; "
                "the one brought in says hi in her own turn once the line was heard, not when he spoke first")

    async def flow87(self) -> str:
        """H98, no Claude: the dog's own mood for an update. The Mac app's strip (also the phone's, /hq) in a headless
        browser: with a newer version out (H59) the dog sits by its empty bowl, wags and now and then barks Update!
        in green; a red bark, sleep or turning things on still win; no newer version or updating: its usual mood."""
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the strip in")
        page = (ROOT / "desktop/shell.html").read_text()
        harness = r"""<script>
(() => {
  const out = [], dog = document.getElementById('dog');
  const NEW = { version: '0.2', latest: '0.3', available: true };
  const one = (mood, update, light = 'ok') => { hq.update({ light, mood, headline: 'All working', off: [], routines: [], update }); return hq.state().mood; };
  hq.tab('status');
  out.push('happy:' + one('happy', NEW));
  const seen = (sel) => getComputedStyle(dog.querySelector(sel)).opacity;
  const moving = (sel) => getComputedStyle(dog.querySelector(sel)).animationName;
  out.push('bowl:' + seen('.bowl') + '/' + seen('.sit') + '/' + seen('.leg.rear'));
  const feed = dog.querySelector('.feed');
  out.push('feed:' + feed.textContent.trim() + '/' + getComputedStyle(feed.querySelector('rect')).fill + '/' + moving('.feed'));
  out.push('wag:' + moving('.tail') + '/' + moving('.head-g') + '/' + moving('.mouth-open'));
  out.push('title:' + document.getElementById('dogtitle').textContent);
  out.push('green:' + getComputedStyle(document.documentElement).getPropertyValue('--green').trim());
  out.push('alert:' + one('alert', NEW, 'waiting'));
  out.push('bark:' + one('bark', NEW, 'down'));
  out.push('sleep:' + one('sleep', NEW, 'down'));
  out.push('none:' + one('happy', {}) + '/' + seen('.bowl'));
  out.push('updating:' + one('happy', { ...NEW, updating: true }));
  one('happy', NEW); hq.fixing(true, 'Turning on');
  out.push('fixing:' + hq.state().mood);
  hq.fixing(false, '');
  out.push('back:' + hq.state().mood);
  const pre = document.createElement('pre'); pre.id = 'h98'; pre.textContent = 'H98RESULT ' + out.join(' | ') + ' END'; document.body.append(pre);
})();
</script>"""
        f = self.tmp / "h98-shell.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []),
                                          f"--user-data-dir={self.tmp / 'h98-profile'}",
                                          "--virtual-time-budget=2000", "--dump-dom", f.as_uri()], timeout=60)
        m = re.search(r'<pre id="h98">H98RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the strip test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        res = dict(part.split(":", 1) for part in m.group(1).split(" | "))
        say(f"   {m.group(1)}")
        need(res["happy"] == "hungry" and res["alert"] == "hungry", f"a newer version doesn't make the dog sit by its bowl: {res}")
        need(res["bowl"] == "1/1/0", f"the bowl, the sitting or the rear legs are wrong: {res['bowl']}")
        green = res["green"]
        rgb = tuple(int(green[i:i + 2], 16) for i in (1, 3, 5)) if green.startswith("#") else None
        need(res["feed"].startswith("Update!/") and rgb and res["feed"].split("/")[1] == f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
             and res["feed"].endswith("/now-and-then"), f"Update! isn't in green now and then: {res['feed']} ({green})")
        need(res["wag"] == "wag/look/open-now-and-then", f"the dog doesn't wag, look and bark: {res['wag']}")
        need("new version" in res["title"], f"the dog's title doesn't say why: {res['title']}")
        need(res["bark"] == "bark" and res["sleep"] == "sleep" and res["fixing"] == "run", f"the update covers a problem: {res}")
        need(res["none"] == "happy/0" and res["updating"] == "happy" and res["back"] == "hungry", f"the bowl shows without a newer version: {res}")
        return "a newer version: the dog sits by its empty bowl, wags, looks up and barks Update! in green now and then; a red bark, sleep and turning on still win; no newer version or updating: its usual mood"

    async def flow88(self) -> str:
        """H113: a job stopped by the usage line carries on where it left off. No Claude turns, no window: a
        copy of the roadmap, its own carry-on folder and a stand-in for Claude Code's chats, and the routine's
        start of a job caught before it opens anything."""
        import subprocess as sp, importlib
        jv = ROOT
        sys.path.insert(0, str(jv / "routine"))
        rm = self.tmp / "roadmap-H113.md"
        rm.write_text(ROADMAP.read_text())
        co_dir, chats = self.tmp / "carryon-H113", self.tmp / "claude-projects-H113"
        env = {**os.environ, "HQ_ROADMAP": str(rm), "HQ_CARRYON": str(co_dir)}
        def jobs(*a, ok=True):
            r = sp.run(["python3", str(jv / "routine/jobs.py"), *a], capture_output=True, text=True, env=env)
            need((r.returncode == 0) == ok, f"jobs.py {' '.join(a)}: {r.stdout.strip()} {r.stderr.strip()}")
            return r.stdout + r.stderr
        for j in json.loads(jobs("next"))["waiting"]:
            jobs("stop", str(j["n"]))
        for j in json.loads(jobs("next"))["running"]:
            jobs("mark", str(j["n"]), "stopped 00:00")
        a, b = (int(jobs("add", f"flow 88 job {x}").split()[1]) for x in "ab")
        carryon = importlib.import_module("carryon")
        tick = importlib.import_module("tick")
        saved = (carryon.DIR, tick.RUN, tick.STATE, tick.PIDFILE, tick.hqpaths.ROADMAP, tick.open_window,
                 tick.status, tick.jobs, tick.log, os.environ.get("HQ_CLAUDE_PROJECTS"))
        run = self.tmp / "run-H113"
        run.mkdir(exist_ok=True)
        caught = {"status": [], "jobs": [], "opened": []}
        carryon.DIR, tick.RUN, tick.STATE, tick.PIDFILE = str(co_dir), str(run), str(run / "job.json"), str(run / "job.pid")
        tick.hqpaths.ROADMAP = str(rm)
        tick.open_window = lambda cmd, name="": caught["opened"].append((cmd, name))
        tick.status = lambda *x: caught["status"].append(x)
        tick.jobs = lambda *x: caught["jobs"].append(x) or ""
        tick.log = lambda m: None
        os.environ["HQ_CLAUDE_PROJECTS"] = str(chats)
        def start(n):
            job = next(j for j in json.loads(jobs("next"))["waiting"] if j["n"] == n)
            caught["opened"].clear()
            tick.start(job)
            need(caught["opened"], f"job {n} wasn't started")
            return (run / f"job-{n}.command").read_text(), (run / f"job-{n}.prompt").read_text()
        try:
            # A new job gets its own chat id up front, so it can be found again.
            cmd, prompt = start(a)
            sid = carryon.load(a).get("session")
            need(sid and f"--session-id {sid}" in cmd and "--resume" not in cmd, f"a new job's chat has no id: {cmd}")
            need(prompt.startswith(f"let's go. This is job {a} from the queue") and "H113" not in prompt,
                 f"a new job's prompt changed: {prompt[:200]}")
            # The usage says STOP at a step: the hold notes when and where.
            jobs("mark", str(a), "running since 12:00")
            txt = rm.read_text()
            head, sep, rest = txt.partition("\n---\n")
            head = re.sub(r"^## Now: .*$", f"## Now: Job {a} · building the second half of flow 88", head, count=1, flags=re.M)
            rm.write_text(head + sep + rest)
            jobs("held", str(a))
            rec = carryon.load(a)
            need(rec.get("held") and rec.get("step") == "building the second half of flow 88" and rec.get("session") == sid,
                 f"the hold didn't note the step: {rec}")
            # Started again on the same computer with its chat still there: it picks its own chat up again.
            slug = re.sub(r"[^A-Za-z0-9]", "-", tick.FOLDER)
            (chats / slug).mkdir(parents=True, exist_ok=True)
            (chats / slug / f"{sid}.jsonl").write_text("{}\n")
            cmd, prompt = start(a)
            need(f"--resume {sid}" in cmd and "--session-id" not in cmd, f"a held job didn't pick its own chat up: {cmd}")
            need(prompt.startswith(f"let's go again. This is job {a}") and "your own earlier chat" in prompt
                 and "building the second half of flow 88" in prompt and prompt.rstrip().endswith("flow 88 job a"),
                 f"the carry-on prompt: {prompt}")
            need("carries on in its own chat" in caught["status"][-1][1], f"the status block doesn't say so: {caught['status'][-1]}")
            need(carryon.load(a).get("session") == sid and not carryon.load(a).get("held"), f"the hold wasn't used up: {carryon.load(a)}")
            # Held again, but the old chat is gone: a fresh chat with the note.
            jobs("mark", str(a), "running since 12:30")
            jobs("held", str(a))
            (chats / slug / f"{sid}.jsonl").unlink()
            cmd, prompt = start(a)
            sid2 = carryon.load(a).get("session")
            need(sid2 and sid2 != sid and f"--session-id {sid2}" in cmd and "--resume" not in cmd, f"no fresh chat: {cmd}")
            need(prompt.startswith(f"let's go. This is job {a}") and "stopped by the usage line" in prompt
                 and "building the second half of flow 88" in prompt and "can't be found here" in prompt
                 and "First look at what the first run left" in prompt, f"the fresh chat's note: {prompt}")
            # The other computer picks a held job up (no record here): a fresh chat, the step from the roadmap's log.
            jobs("mark", str(b), "running since 13:00")
            jobs("held", str(b))
            (co_dir / f"job-{b}.json").unlink()
            txt = rm.read_text()
            head, sep, rest = txt.partition("\n---\n")
            head = re.sub(r"^## Now: .*$", f"## Now: Job {b} waits for the usage line", head, count=1, flags=re.M)
            head = head.replace("\n- ", f"\n- 13:05 job {b}: held, usage over the line\n- 13:04 job {b}: running the flows\n- ", 1)
            rm.write_text(head + sep + rest)
            cmd, prompt = start(b)
            need("--session-id" in cmd and "stopped by the usage line" in prompt and "at about this step: running the flows" in prompt
                 and "isn't on this computer" in prompt, f"the other computer's fresh chat: {prompt}")
            need("--session-id" in tick.job_script_tmux(b, "s.json", "p", "--session-id x"), "the tmux script doesn't pass the chat id")
        finally:
            (carryon.DIR, tick.RUN, tick.STATE, tick.PIDFILE, tick.hqpaths.ROADMAP, tick.open_window,
             tick.status, tick.jobs, tick.log, old) = saved
            if old is None:
                os.environ.pop("HQ_CLAUDE_PROJECTS", None)
            else:
                os.environ["HQ_CLAUDE_PROJECTS"] = old
        return "a new job's chat gets an id; held, it picks its own chat up with the step; chat gone or other computer: a fresh chat with the note"

    async def flow94(self) -> str:
        """H135, no Claude, no network: the weather in the app. The view from a made-up forecast, radar and warnings
        feed (sunny or not, degrees, wind in Bft, chance of rain, UV, the next hours, today and tomorrow), the
        warnings that count (his region, yellow and up, not over, not cancelled, English, the English region name
        matched to the local one), a blank place said plainly, the read kept for 15 minutes in a throwaway folder,
        the call server's endpoint (not on Free) and the call page's widget and sheet (the widget out of the page's flow,
        so the call screen keeps its room, flow 64)."""
        import importlib
        from datetime import datetime as dt
        sys.path.insert(0, str(ROOT / "app"))
        import weather as w
        importlib.reload(w)
        hrs = [f"2026-10-14T{h:02d}:00" for h in range(24)] + [f"2026-10-15T{h:02d}:00" for h in range(24)]
        def fc(code=1, prob=10, day=1):
            return {"current": {"temperature_2m": 17.4, "apparent_temperature": 15.1, "weather_code": code, "is_day": day,
                                "precipitation": 0, "wind_speed_10m": 22.0, "wind_gusts_10m": 41.0,
                                "wind_direction_10m": 230, "uv_index": 3.4},
                    "hourly": {"time": hrs, "temperature_2m": [16] * 48, "precipitation": [0] * 48,
                               "precipitation_probability": [prob] * 48, "weather_code": [code] * 48,
                               "uv_index": [2] * 48, "wind_speed_10m": [20] * 48, "is_day": [1] * 48},
                    "daily": {"time": ["2026-10-14", "2026-10-15"], "weather_code": [code, 61],
                              "temperature_2m_max": [18.2, 14], "temperature_2m_min": [10.1, 9],
                              "precipitation_sum": [0, 4.2], "precipitation_probability_max": [10, 80],
                              "uv_index_max": [3.6, 1.2], "sunrise": ["2026-10-14T08:03", "2026-10-15T08:05"],
                              "sunset": ["2026-10-14T18:48", "2026-10-15T18:46"],
                              "wind_speed_10m_max": [25, 30], "wind_gusts_10m_max": [45, 60]}}
        now = dt(2026, 10, 14, 11, 20)
        v = w.build_view(fc(), [("11:20", 0.0)] * 24, [], now, "Town", "KNMI")
        n = v["now"]
        need(n["sunny"] and n["icon"] == "sun" and round(n["temp"]) == 17 and n["bft"] == 4 and n["dir"] == "SW"
             and n["chance"] == 10 and n["uv_word"] == "moderate" and not n["raining"], f"the view now: {n}")
        need(len(v["hours"]) == 12 and v["hours"][0]["at"] == "11:00" and v["radar"] == "Dry for the next two hours",
             f"the next hours or the radar: {v['hours'][:1]} {v['radar']}")
        need(v["today"]["uv_word"] == "moderate" and v["today"]["sunset"] == "18:48" and v["tomorrow"]["chance"] == 80
             and v["tomorrow"]["icon"] == "rain", f"today and tomorrow: {v['today']} {v['tomorrow']}")
        v = w.build_view(fc(code=63, prob=90), [("11:20", 1.2)] * 6 + [("11:50", 0.0)] * 18, [], now, "Town")
        need(not v["now"]["sunny"] and v["now"]["raining"] and v["now"]["icon"] == "rain"
             and v["radar"] == "Raining now, dry from about 11:50", f"rain now: {v['now']} {v['radar']}")
        need(not w.build_view(fc(day=0), [], [], now)["now"]["sunny"] and w.icon(0, False) == "moon", "sunny at night")
        # the warnings: his region (the English name matched to the local one), yellow and up, still on
        def warn(area, level, expires="2026-10-14T23:00:00+02:00", lang="en-GB", kind="2; Wind", msg="Alert"):
            return {"alert": {"msgType": msg, "status": "Actual", "info": [
                {"language": lang, "event": "wind", "headline": f"Code {level} wind {area}", "description": "Gusts up to 75 km/h.",
                 "onset": "2026-10-14T13:00:00+02:00", "expires": expires, "senderName": "KNMI",
                 "area": [{"areaDesc": area}],
                 "parameter": [{"valueName": "awareness_level", "value": f"{level}; x; y"},
                               {"valueName": "awareness_type", "value": kind}]}]}}
        feed = {"warnings": [warn("Noord-Holland", 2), warn("Noord-Holland", 1, kind="3; Thunderstorm"),
                             warn("Zeeland", 3), warn("Noord-Holland", 3, expires="2026-10-14T09:00:00+02:00", kind="4; Fog"),
                             warn("Noord-Holland", 3, msg="Cancel", kind="7; Rain"), warn("Noord-Holland", 2, lang="nl-NL", kind="2; Wind")]}
        place = {"name": "Haarlem", "region": "North Holland", "country": "NL"}
        got = w.parse_warnings(feed, place, now)
        need(len(got) == 1 and got[0]["level"] == "yellow" and got[0]["what"] == "Wind" and got[0]["area"] == "Noord-Holland",
             f"the warnings that count: {got}")
        need(not w.parse_warnings(feed, {"name": "Breda", "region": "North Brabant", "country": "NL"}, now),
             "a warning for another region was shown")
        need(w.parse_warnings({"warnings": [warn("Zeeland", 3)]}, {"name": "Middelburg", "region": "Zeeland"}, now)[0]["level"] == "orange",
             "an orange warning isn't read")
        need(w.METEOALARM.get("NL") == "netherlands" and w.METEOALARM.get("EE") == "estonia", "the warnings feeds by country")
        need(w.warnings({"country": "TH"}, now) == ([], "no warnings feed for this country"), "a country without a feed")
        # view(): a blank place said plainly; the read kept for 15 minutes; a failed read keeps the last one
        folder = self.tmp / "weather-H135"
        keep = {k: os.environ.get(k) for k in ("HQ_DIRECT_DIR", "HQ_WEATHER_PLACE", "HQ_WEATHER")}
        real = (w.app_forecast, w.rain_text, w.warnings, w.place)
        calls = []
        try:
            os.environ.update({"HQ_DIRECT_DIR": str(folder)})
            os.environ.pop("HQ_WEATHER", None)
            os.environ.pop("HQ_WEATHER_PLACE", None)
            w.place = lambda: ""
            need("No place set yet" in (w.view(fresh=True).get("off") or ""), "a blank place isn't said plainly")
            w.place = real[3]
            os.environ["HQ_WEATHER_PLACE"] = "Testtown"
            w._write({"where": {"place": "Testtown", "lat": 52.0, "lon": 5.0, "tz": "Europe/Amsterdam",
                                "country": "NL", "name": "Testtown", "region": "Zeeland"}})
            w.app_forecast = lambda _w: calls.append(1) or fc()
            w.rain_text = lambda _w: []
            w.warnings = lambda _w, _now: (w.parse_warnings({"warnings": [warn("Zeeland", 2)]}, _w, _now.replace(year=2026, month=10, day=14, hour=11)), "KNMI")
            t0 = time.time()
            v1 = w.view(fresh=True, now=t0)
            need(v1.get("place") == "Testtown" and v1["now"]["temp"] == 17.4 and v1.get("warnings") and len(calls) == 1,
                 f"the view wasn't read: {v1.get('error')} {calls}")
            need(w.view(fresh=True, now=t0 + 600)["looked"] == t0 and len(calls) == 1, "read again within 15 minutes")
            need(w.view(now=t0 + 3600)["looked"] == t0 and len(calls) == 1, "read without being asked fresh")
            w.app_forecast = lambda _w: (_ for _ in ()).throw(OSError("offline"))
            v3 = w.view(fresh=True, now=t0 + 3600)
            need(v3.get("error") and v3["looked"] == t0 and v3["now"]["temp"] == 17.4, "a failed read didn't keep the last one")
            os.environ["HQ_WEATHER_PLACE"] = "Othertown"
            need(not w.view().get("now"), "another place's weather was shown")
            os.environ["HQ_WEATHER"] = "0"
            need(w.view().get("off"), "HQ_WEATHER=0 doesn't switch it off")
        finally:
            w.app_forecast, w.rain_text, w.warnings, w.place = real
            for k, v in keep.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        # the call server and the page
        bot = (ROOT / "app/bot.py").read_text()
        ep = bot.split('@app.get("/api/weather"')[1].split("@app.")[0] if '@app.get("/api/weather"' in bot else ""
        need("FREE_ONLY" in ep and "_weather.view" in ep and 'get("fresh") == "1"' in ep, "the call server has no /api/weather, or it's on Free")
        page = (ROOT / "app/web/index.html").read_text()
        for x in ('id="wx"', 'id="wxsheet"', '"api/weather"', "function paintWx", "function showWx", "body.chatting #wx"):
            need(x in page, f"the call page misses {x}")
        need(page.count("closeWx();") >= 6, "opening another sheet doesn't close the weather (one sheet at a time)")
        pw = page.split("function paintWx")[1].split("\nfunction ")[0]
        need('state === "idle"' in pw and "!free" in pw and "warnings" in pw and "d.off" in pw,
             "the pill shows on a call or on Free, or misses the warning or the plain no-place line")
        sb = page.split("function showWxBody")[1].split("\nasync function ")[0]
        need(all(k in sb for k in ("wxLevel(w)", "UV now", "Next hours", "Tomorrow", "Chance of rain", "Wind")),
             "the sheet misses the warnings, UV, the next hours, tomorrow, rain or wind")
        need(re.search(r"#wx \{ position:fixed;", page), "the widget takes room in the page's flow (the call screen moves)")
        need("var wxData" in page, "the pill's data isn't hoisted: showMode() paints it before the line runs")
        return "the view (sun, degrees, Bft, rain, UV, hours, today, tomorrow), the warnings that count, a blank place said, kept 15 minutes, the endpoint off on Free, the pill and the sheet"

    async def flow90(self) -> str:
        """H120, no Claude, no network: the weather every three hours. What's worth a text from a made-up forecast
        and rain radar (sun, rain coming by the minute, a rainy day never saying go outside, quiet at night and
        when nothing changed), when a look is due, the place from me.md (blank in the template), a look that texts
        through the direct line in a throwaway folder, and the routine's wiring."""
        import importlib
        from datetime import datetime as dt
        sys.path.insert(0, str(ROOT / "app"))
        import weather as w
        importlib.reload(w)
        hrs = [f"2026-10-14T{h:02d}:00" for h in range(24)]
        def fc(rain=0.0, prob=5, code=1):
            return {"current": {"temperature_2m": 17.2, "weather_code": code}, "daily": {"sunset": ["2026-10-14T18:50"]},
                    "hourly": {"time": hrs, "temperature_2m": [15] * 24, "precipitation": [rain] * 24,
                               "precipitation_probability": [prob] * 24, "weather_code": [code] * 24}}
        day, night = dt(2026, 10, 14, 11, 5), dt(2026, 10, 14, 22, 0)
        dry = [("11:05", 0.0)] * 24
        got = w.decide(fc(), dry, day, [], "Town")
        need(got and got[0] == "sun" and "sunset at 18:50" in got[1], f"a sunny day: {got}")
        need(w.decide(fc(), dry, day, ["sun"]) is None, "the sun was texted twice in a day")
        got = w.decide(fc(), [("11:05", 0.0)] * 6 + [("11:35", 0.6), ("11:40", 2.0)], day, [])
        need(got and got[0] == "rain" and "11:35" in got[1] and "steady" in got[1], f"rain by the minute: {got}")
        f2 = fc(); f2["hourly"]["precipitation_probability"] = [5] * 12 + [80] * 2 + [5] * 10
        got = w.decide(f2, [], day, [])
        need(got and got[0] == "rain" and "12:00" in got[1], f"rain likely in the next hours: {got}")
        got = w.decide(fc(rain=1.2, code=63), [("11:05", 1.5)] * 24, day, [])
        need(got and got[0] == "cosy" and "cosy inside" in got[1], f"a rainy day: {got}")
        need(w.decide(fc(rain=1.2, code=63), [], day, ["cosy"]) is None, "the rainy day was texted twice")
        need(w.decide(fc(), dry, night, []) is None and w.decide(fc(code=3), dry, day, []) is None,
             "she texts at night, or on a grey dry day")
        need(w.parse_rain("000|11:05\n109|11:10\nxx\n141|11:15") == [("11:05", 0.0), ("11:10", 1.0), ("11:15", 10.0)],
             "Buienradar's rain text is read wrong")
        # The look: a throwaway folder, a made-up place, the network and her text stood in for.
        folder = self.tmp / "weather-H120"
        keep = {k: os.environ.get(k) for k in ("HQ_DIRECT_DIR", "HQ_WEATHER_PLACE", "HQ_WEATHER")}
        import direct_line as dl
        sent, real = [], (w.forecast, w.rain_text, dl.text)
        try:
            os.environ.update({"HQ_DIRECT_DIR": str(folder), "HQ_WEATHER_PLACE": "Testtown"})
            os.environ.pop("HQ_WEATHER", None)
            w._write({"where": {"place": "Testtown", "lat": 52.0, "lon": 5.0, "tz": "Europe/Amsterdam",
                                "country": "NL", "name": "Testtown"}})
            noon = dt(2026, 10, 14, 12, 0).timestamp()
            need(w.due(noon) and not w.due(dt(2026, 10, 14, 23, 30).timestamp()) and
                 not w.due(dt(2026, 10, 14, 6, 0).timestamp()), "a look is due at night, or not in the day")
            w.forecast, w.rain_text = (lambda _w: fc(rain=1.2, code=63)), (lambda _w: [])
            dl.text = lambda why, facts: sent.append((why, facts))
            got = w.look(now=noon)
            need(got and got[0] == "cosy" and sent == [got], f"the look didn't text the rainy day: {got} {sent}")
            need(not w.due(noon + 3600) and w.due(noon + 3 * 3600), "not every three hours after a look")
            need(w.look(now=noon + 3 * 3600) is None and len(sent) == 1, "the rainy day was texted again")
            os.environ["HQ_WEATHER"] = "0"
            need(not w.due(noon + 9 * 3600), "HQ_WEATHER=0 doesn't switch it off")
        finally:
            w.forecast, w.rain_text, dl.text = real
            for k, v in keep.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        # The place from me.md; the template asks for it, blank.
        import me as _me
        need(_me.load(ROOT / "template")["place"] == "", "the template's place isn't blank")
        need("**Where I am:**" in (ROOT / "template/me.md").read_text(), "the template doesn't ask where you are")
        (folder / "me.md").write_text("**Name:** X\n\n**Where I am:** Testtown, NL\n")
        need(_me.load(folder)["place"] == "Testtown, NL", "me.md's place isn't read")
        # The wiring: the routine starts it on the main, her prompts and plain lines know the three kinds.
        tick = (ROOT / "routine/tick.py").read_text().split("def direct_watch")[1].split("\ndef ")[0]
        need("weather.start()" in tick and "if main:" in tick, "the routine doesn't start the look on the main")
        need(all(k in dl.PLAIN for k in ("sun", "rain", "cosy")) and "never suggest going outside" in dl.compose_prompt("cosy", "").lower(),
             "her texts don't know sun, rain and cosy")
        gi = (Path(config.FOLDER) / ".gitignore")
        if gi.exists():
            need("HQ/direct-line/weather.json" in gi.read_text(), "the weather state isn't kept off GitHub")
        return "sun, rain by the minute and by the hour, a rainy day (never outside), quiet at night and on grey days; due every three hours in the day; me.md's place; texted once"

    async def flow93(self) -> str:
        """H125, no Claude, no network: Donna's watch list. routine/pings.py on its own copies: a mail watch and a
        weather watch added (and refused when unclear), the mail check's lines and its match (kept once, texted once,
        every update until its time, ending when one answers it), a weather watch checked against a made-up forecast
        (rain later today, dry, sun, colder than N) and ending at the first match, its time up and his stop each
        texted; the weather look every 30 minutes only while a weather watch is open (her three-hourly texts not more
        often); the mail check's instructions and its one allowed command, the call's and her chat's rules and
        policy, her texts' kinds, and her watches in /api/notes on the test server."""
        import importlib
        import pings
        import direct_line
        sys.path.insert(0, str(ROOT / "app"))
        import weather as w
        importlib.reload(w)
        from policy import Policy, ALLOW, DENY
        d = self.tmp / "h125"
        d.mkdir(parents=True, exist_ok=True)
        keep = {k: os.environ.get(k) for k in ("HQ_DIRECT_DIR", "HQ_CALENDAR_FILE", "HQ_AGENT_NOTES", "HQ_DIRECT_DRY",
                                               "HQ_WEATHER_PLACE", "HQ_WEATHER", "HQ_INITIATIVE")}
        real = Path(os.path.join(pings.hqpaths.DATA, "direct-line", "pings.json"))
        real_before = real.read_bytes() if real.exists() else None
        os.environ.update({"HQ_DIRECT_DIR": str(d / "line"), "HQ_CALENDAR_FILE": str(d / "calendar.json"),
                           "HQ_AGENT_NOTES": str(d / "notes-donna.md"), "HQ_DIRECT_DRY": "1",
                           "HQ_WEATHER_PLACE": "Testtown", "HQ_INITIATIVE": "0"})
        os.environ.pop("HQ_WEATHER", None)
        texts = []
        spawn = lambda why, facts: texts.append((why, facts))
        try:
            now = datetime(2099, 1, 1, 12, 0)
            t = lambda h, m=0, day=1: datetime(2099, 1, day, h, m).timestamp()
            # adding: mail for 7 days by default, weather until the end of today and once; unclear ones refused
            m1 = pings.watch_add("mail", "the package from Nedgame: shipping or delivery", now=now)
            need(m1["until"] == "2099-01-08 12:00" and not m1["once"], f"a mail watch's default isn't 7 days, every update: {m1}")
            w1 = pings.watch_add("weather", "raining", now=now)
            need(w1["what"] == "rain" and w1["until"] == "2099-01-01 23:00" and w1["once"], f"a weather watch's default: {w1}")
            need(pings.watch_add("weather", "below 3°C", until=datetime(2099, 1, 2, 9), now=now)["what"] == "below 3", "below N isn't read")
            for bad in (("weather", "snowstorm"), ("tea", "x"), ("mail", "  ")):
                try:
                    pings.watch_add(*bad, now=now)
                    need(False, f"an unclear watch was taken: {bad}")
                except ValueError:
                    pass
            need(pings.when("in 3 days", now) == datetime(2099, 1, 4, 12) and pings.when("tomorrow", now) == datetime(2099, 1, 2, 23),
                 "a watch's until isn't read")
            # the mail check: its lines and its match
            lines = pings.mail_watch_text(now=t(12))
            need(f"Watch {m1['n']}: the package from Nedgame" in lines and "rain" not in lines, f"the mail check's lines: {lines}")
            need(pings.match(m1["n"], "13 Jan · Nedgame · Order sent · packed and sent", key="L1", now=t(12, 5)) == "new"
                 and pings.match(m1["n"], "again", key="L1", now=t(12, 6)) == "seen", "a mail match isn't kept once")
            got = pings.watch(t(12, 7), spawn=spawn)
            need([x[0] for x in got] == ["watch"] and "packed and sent" in got[0][1] and "keep watching" in got[0][1],
                 f"a mail match wasn't texted, or ended the watch: {got}")
            need(not pings.watch(t(12, 8), spawn=spawn), "a match was texted twice")
            pings.match(m1["n"], "14 Jan · Nedgame · Delivered", key="L2", answers=True, now=t(13))
            got = pings.watch(t(13, 1), spawn=spawn)
            need([x[0] for x in got] == ["watch"] and "stop watching" in got[0][1] and not pings.open_watches("mail", now=t(13, 2)),
                 f"a mail that answers it didn't end the watch: {got}")
            need(pings.match(m1["n"], "late", key="L3", now=t(13, 3)) != "new", "an ended watch still takes matches")
            # the weather: checked against a forecast, the first match ends it
            hrs = [f"2099-01-01T{h:02d}:00" for h in range(24)] + [f"2099-01-02T{h:02d}:00" for h in range(24)]
            def fc(prob=None, code=None, temp=None):
                prob, code, temp = prob or [5] * 48, code or [3] * 48, temp or [10] * 48
                return {"current": {"temperature_2m": temp[12], "weather_code": code[12], "precipitation": 0},
                        "daily": {"sunset": ["2099-01-01T17:00"]},
                        "hourly": {"time": hrs, "precipitation_probability": prob, "weather_code": code,
                                   "temperature_2m": temp, "precipitation": [0] * 48}}
            later = fc(prob=[5] * 16 + [80] * 3 + [5] * 29)
            until = datetime(2099, 1, 1, 23)
            need(w.check_watch("rain", fc(), [], now, until) is None, "rain found in a dry forecast")
            got = w.check_watch("rain", later, [], now, until)
            need(got and "16:00" in got[1], f"rain later today isn't found: {got}")
            need(w.check_watch("rain", later, [], now, datetime(2099, 1, 1, 15)) is None, "rain after the watch's time counted")
            got = w.check_watch("rain", fc(), [("12:05", 0.0), ("12:30", 0.8)], now, until)
            need(got and "12:30" in got[1], f"rain by the minute isn't found: {got}")
            got = w.check_watch("dry", later, [("16:05", 0.9)], now.replace(hour=16), until)
            need(got and "19:00" in got[1], f"dry again isn't found: {got}")
            need("14:00" in (w.check_watch("sun", fc(code=[3] * 14 + [1] * 34), [], now, until) or ("", ""))[1], "sun isn't found")
            need("20:00" in (w.check_watch("below 3", fc(temp=[10] * 20 + [2] * 28), [], now, until) or ("", ""))[1], "colder than N isn't found")
            ws = [x for x in pings.open_watches("weather", now=t(12, 30)) if x["what"] == "rain"]
            new = w.check_watches(later, [], now.replace(minute=30), "Testtown", ws=ws)
            need(len(new) == 1 and not w.check_watches(later, [], now.replace(minute=59), "Testtown", ws=ws), "a weather match was kept twice")
            got = pings.watch(t(12, 31), spawn=spawn)
            need([x[0] for x in got] == ["watch"] and "16:00" in got[0][1] and "stop watching" in got[0][1]
                 and not [x for x in pings.open_watches("weather", now=t(12, 32)) if x["what"] == "rain"],
                 f"the rain watch wasn't texted and ended at its first match: {got}")
            # its time up, and his stop, are texted; once
            got = pings.watch(t(9, day=2), spawn=spawn)
            need([x[0] for x in got] == ["watch-end"] and "Nothing came" in got[0][1], f"a watch whose time is up: {got}")
            w2 = pings.watch_add("weather", "sun", now=datetime(2099, 1, 2, 10))
            w3 = pings.watch_add("weather", "dry", now=datetime(2099, 1, 2, 10))
            pings.unwatch(w2["n"], now=t(10, 1, day=2))
            pings.unwatch(w3["n"], quiet=True, now=t(10, 1, day=2))
            got = pings.watch(t(10, 2, day=2), spawn=spawn)
            need([x[0] for x in got] == ["watch-end"] and "stop watching" in got[0][1] and not pings.watch(t(10, 3, day=2), spawn=spawn),
                 f"his stop isn't texted once, or --quiet still texted: {got}")
            need("Watches" in pings.listing() and pings.unwatch(w2["n"]) is None, "the list doesn't show the watches")
            # the weather look: every 30 minutes only while a weather watch is open; her three-hourly texts stay
            w._write({"where": {"place": "Testtown", "lat": 52.0, "lon": 5.0, "tz": "Europe/Amsterdam", "country": "NL", "name": "Testtown"},
                      "looked": t(11, day=2), "general": t(11, day=2)})
            need(not w.due(t(11, 40, day=2)), "a look every 30 minutes without a weather watch")
            w4 = pings.watch_add("weather", "rain", now=datetime(2099, 1, 2, 11, 30))
            need(w.due(t(11, 40, day=2)) and w.watch_due(t(11, 40, day=2)) and not w.general_due(t(11, 40, day=2)),
                 "no look every 30 minutes while a weather watch is open")
            sent, realfn = [], (w.forecast, w.rain_text, direct_line.text)
            w.forecast, w.rain_text = (lambda _w: fc(code=[1] * 48)), (lambda _w: [])
            direct_line.text = lambda why, facts: sent.append(why)
            try:
                need(w.look(now=t(11, 40, day=2), general=False) is None and not sent, "a watch look sent her three-hourly text")
                need(not w.due(t(12, day=2)) and w.due(t(12, 10, day=2)), "the watch look isn't every 30 minutes")
                need(w.general_due(t(14, day=2)), "the three-hourly look moved with the watch looks")
            finally:
                w.forecast, w.rain_text, direct_line.text = realfn
            pings.unwatch(w4["n"], quiet=True)
            need(not w.due(t(12, 10, day=2)), "still every 30 minutes after the last weather watch ended")
            # her texts know both kinds
            for why, word in (("watch", "keep an eye out"), ("watch-end", "stopped")):
                need(why in direct_line.PLAIN and word in direct_line.compose_prompt(why, "x"), f"her texts don't know {why}")
            # the rules, the policy, the mail check's instructions and its one command
            need("watch mail" in config.VOICE_RULES and "watch weather" in config.VOICE_RULES and "unwatch" in direct_line._text_rules(),
                 "the call's or her chat's rules don't say how to keep watches")
            pol = Policy(config.FOLDER)
            script = str(ROOT / "routine" / "pings.py")
            for cmd in (f'python3 "{script}" watch mail "the package"', f'python3 "{script}" watch weather rain --until "today 18:00"',
                        f'python3 "{script}" unwatch 3'):
                need(pol.decide("Bash", {"command": cmd}).verdict == ALLOW, f"a call may not run {cmd}")
            need(pol.decide("Bash", {"command": f'python3 "{script}" match 1 "x"'}).verdict == DENY, "a call may run the mail check's match")
            mc = (ROOT / "routine" / "mail-check.md").read_text()
            need("{WATCHES}" in mc and "{PINGS} match N" in mc and "--answers" in mc, "the mail check isn't told about the watches")
            tsrc = (ROOT / "routine" / "tick.py").read_text()
            need("pings.py')} match:*)" in tsrc and '.replace("{WATCHES}", mail_watches())' in tsrc,
                 "the mail check doesn't get the watches or the match command")
        finally:
            for k, v in keep.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        need((real.read_bytes() if real.exists() else None) == real_before, "the workspace's own pings were touched")
        # the test server: her watches come with her notes
        await self.ensure_server()
        sdir = Path(self.server.env["HQ_DIRECT_DIR"])
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / "pings.json").write_text(json.dumps({"watches": [
            {"n": 1, "kind": "mail", "what": "the package", "until": "2099-01-08 12:00", "once": False, "matches": []}]}))
        code, body, _ = http_get("/api/notes")
        got = json.loads(body) if code == 200 else {}
        ws = (got.get("hers") or {}).get("watches") or []
        need(code == 200 and [x["text"] for x in ws] == ["Watching for a mail about the package"], f"/api/notes doesn't give her watches: {got}")
        page = (ROOT / "app" / "web" / "index.html").read_text()
        need("hers.watches" in page and "keeps an eye out" in page, "the notes sheet doesn't show her watches")
        return ("mail and weather watches added (unclear ones refused), the mail check's match kept and texted once, every update until "
                "one answers it; rain later today, dry, sun and colder than N from a forecast, ending at the first match; time up and "
                "his stop texted; a look every 30 minutes only while a weather watch is open; rules, policy, mail check, /api/notes")

    async def flow86(self) -> str:
        """H80, no Claude: Donna's direct line. A push message encrypted for a stand-in phone decrypts back (RFC 8291)
        and its VAPID token verifies with the shared key; a gone phone is dropped. The routine's look takes stock
        first, then texts when the job list is finished, for a new very important mail (not for its status changing),
        when something stays down and when it's back. A throwaway status server serves the chat and its service
        worker, refuses a send without the HQ header, signs a phone up, and his text gets her (canned) reply. Off a
        Mac her reply finds Claude on PATH (F27)."""
        import base64
        import urllib.request
        sys.path.insert(0, str(ROOT / "routine"))
        d = self.tmp / "h80"
        d.mkdir()
        saved = {k: os.environ.get(k) for k in ("HQ_DIRECT_DIR", "HQ_DIRECT_LOCAL", "HQ_DIRECT_DRY", "HQ_DIRECT")}
        os.environ.update({"HQ_DIRECT_DIR": str(d / "line"), "HQ_DIRECT_LOCAL": str(d / "local.json"), "HQ_DIRECT_DRY": "1"})
        os.environ.pop("HQ_DIRECT", None)
        try:
            import direct_line as dl
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
            b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
            unb64 = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
            # Push: encrypted for a stand-in phone, decrypted the way the phone does it.
            phone = ec.generate_private_key(ec.SECP256R1())
            p256dh = b64(phone.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
            auth = b64(os.urandom(16))
            body = dl.encrypt(b'{"body":"hi"}', p256dh, auth)
            need(dl.decrypt(body, phone, auth) == b'{"body":"hi"}', "a push message doesn't decrypt back on the phone's side")
            k = dl.keys()
            need(dl.keys() == k and dl.public_key() == k["public"], "the push key isn't made once and kept")
            hv = dl.vapid_header("https://push.example.com/send/abc", k)
            # F27: her reply run finds Claude without HQ_CLAUDE_CLI (the status server starts it without one); off a
            # Mac that's the claude on PATH, not the Mac's place.
            import config as _cfg
            cli_env = os.environ.pop("HQ_CLAUDE_CLI", None)
            try:
                found = _cfg._claude_cli()
                if sys.platform != "darwin" and shutil.which("claude"):
                    need(found == shutil.which("claude"), f"off a Mac her reply looks for Claude at {found}")
            finally:
                if cli_env is not None:
                    os.environ["HQ_CLAUDE_CLI"] = cli_env
            m = re.fullmatch(r"vapid t=([\w-]+)\.([\w-]+)\.([\w-]+), k=([\w-]+)", hv)
            need(m and m.group(4) == k["public"], f"the VAPID header is shaped wrong: {hv[:60]}")
            claims = json.loads(unb64(m.group(2)))
            need(claims["aud"] == "https://push.example.com" and claims["exp"] > time.time(), f"the VAPID claims are wrong: {claims}")
            sig = unb64(m.group(3))
            pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), unb64(k["public"]))
            pub.verify(encode_dss_signature(int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:], "big")),
                       f"{m.group(1)}.{m.group(2)}".encode(), ec.ECDSA(hashes.SHA256()))
            # Two phones; the push services answer 201 for one and 410 (gone) for the other, which is dropped.
            dl.subscribe({"endpoint": "https://push.example.com/a", "keys": {"p256dh": p256dh, "auth": auth}}, "phone a")
            dl.subscribe({"endpoint": "https://push.example.com/b", "keys": {"p256dh": p256dh, "auth": auth}}, "phone b")
            try:
                dl.subscribe({"endpoint": "http://nope", "keys": {}})
                need(False, "a broken subscription was taken")
            except ValueError:
                pass
            sent = []

            class _R:
                status = 201
                def __enter__(self): return self
                def __exit__(self, *a): return False

            def fake(req, timeout=0):
                sent.append(req)
                if req.full_url.endswith("/b"):
                    raise urllib.error.HTTPError(req.full_url, 410, "Gone", {}, None)
                return _R()
            real_open = urllib.request.urlopen
            os.environ["HQ_DIRECT_PUSH_TO"] = "1"
            urllib.request.urlopen = fake
            try:
                said = dl.push("Hey, all done.")
            finally:
                urllib.request.urlopen = real_open
                os.environ.pop("HQ_DIRECT_PUSH_TO", None)
            need(said == ["201", "410"], f"push said {said}")
            need([s["endpoint"] for s in dl.subscriptions()] == ["https://push.example.com/a"], "the gone phone wasn't dropped")
            a = sent[0]
            need(a.get_header("Content-encoding") == "aes128gcm" and a.get_header("Authorization", "").startswith("vapid t="),
                 "the push request lacks its encoding or VAPID header")
            got = json.loads(dl.decrypt(a.data, phone, auth))
            need(got["body"] == "Hey, all done." and got["url"] == "/direct" and got["title"] == dl.agent()["name"],
                 f"the phone would show {got}")
            # The routine's look.
            inbox = d / "inbox.md"
            inbox.write_text("# Mail\n\n## Very important\n\n- 1 Oct · Old · Bill · old one · Status: new · [Gmail](x)\n\n## To check\n")
            roadmap = d / "roadmap.md"
            roadmap.write_text("- Job 7 · done 18:00 · build the thing\n")
            look = lambda q, inc=(): dl.watch(q, inbox=inbox, roadmap=str(roadmap), incidents_data=list(inc), dry=False, spawn=lambda w, f: None)
            busy = {"running": [{"n": 7, "text": "build the thing"}], "ready": [], "held": []}
            need(look(busy) == [], "the first look texted about what was already there")
            need(look(busy) == [], "she texted while the job list is still busy")
            out = look({"running": [], "ready": [], "held": []})
            need([w for w, _ in out] == ["jobs"] and "build the thing" in out[0][1], f"the finished job list gave {out}")
            need(look({}) == [], "she texted twice that the job list is finished")
            inbox.write_text(inbox.read_text().replace("Status: new · [Gmail](x)\n",
                             "Status: new · [Gmail](x)\n- 13 Oct · Employer · Salary · a question · Why: work · Status: new · [Gmail](y)\n"))
            out = look({})
            need([w for w, _ in out] == ["mail"] and "Employer" in out[0][1] and "Gmail" not in out[0][1] and "Why:" not in out[0][1],
                 f"the new very important mail gave {out}")
            inbox.write_text(inbox.read_text().replace("a question · Why: work · Status: new", "a question, and a reminder · Why: work · Status: on the list"))
            need(look({}) == [], "an update to a mail she already texted about was texted again")
            now = time.time()
            inc = [{"id": "i1", "key": "mail", "down": now - 30, "why": "no internet"}]
            need(look({}, inc) == [], "something down for 30 seconds was texted")
            inc[0]["down"] = now - 200
            out = look({}, inc)
            need([w for w, _ in out] == ["down"] and "no internet" in out[0][1], f"something down for a while gave {out}")
            need(look({}, inc) == [], "she texted twice that it's down")
            inc[0]["back"] = now
            out = look({}, inc)
            need([w for w, _ in out] == ["back"], f"back again gave {out}")
            out = look({}, [{"id": "r1", "key": "role", "down": now, "why": "the main doesn't answer"}])
            need([w for w, _ in out] == ["down"], f"a takeover wasn't texted at once: {out}")
            need(dl.watch({}, main=False, inbox=inbox, incidents_data=[], dry=True) == [], "the backup texted about the job list or mail")
            # F28: the incident log as the routine really reads it (a dict holding the list), not only a list
            sys.path.insert(0, str(ROOT / "routine"))
            import incidents as _inc
            real_read = _inc.read
            _inc.read = lambda: {"incidents": [{"id": "x1", "key": "net", "down": now - 999, "why": "no internet"}], "events_seen": 0}
            try:
                dl.watch({}, main=False, inbox=inbox, dry=True)
            except Exception as e:
                need(False, f"the real incident log breaks her look: {e!r}")
            finally:
                _inc.read = real_read
            os.environ["HQ_DIRECT"] = "0"
            need(dl.watch({"running": []}, inbox=inbox, incidents_data=[], dry=True) == [], "switched off, she still texted")
            os.environ.pop("HQ_DIRECT")
            msg = dl.text("jobs", "What ran: the thing")
            need(msg["from"] == "agent" and msg["why"] == "jobs" and dl.thread()[-1]["text"] == msg["text"], "her text isn't in the thread")
            # H127: the team finished up, a short line with no details or status talk, not the same one twice in a row
            nxt = dl.text("jobs", "What ran: the thing")
            for m in (msg, nxt):
                low = m["text"].lower()
                need("the thing" not in low and "nothing running" not in low and "job list" not in low and len(m["text"]) < 80,
                     f"the finished job list text has details or status talk: {m['text']!r}")
            need(nxt["text"] != msg["text"], f"the same finished line twice in a row: {nxt['text']!r}")
            need("no details" in dl.compose_prompt("jobs", "x") and "background" in dl.compose_prompt("jobs", "x")
                 and "short" in dl.TEXT_RULES and "humanised" in dl.TEXT_RULES, "her prompts don't ask for a short, human text")
            dl.add("agent", "Small test line.", "back")
            need("Small test line." in dl.compose_prompt("back", "x"), "her prompt doesn't show her last texts of the kind")
            low = dl.plain("down", "call: no answer on 7860\nmail: ENOTFOUND").lower()
            need("the call line" in low and "mail check" in low and "7860" not in low and "enotfound" not in low,
                 f"the plain down text gives technical details: {low!r}")
            tick = (ROOT / "routine/tick.py").read_text()
            need("def direct_watch" in tick and "hqpaths.under_test()" in tick.split("def direct_watch")[1][:600],
                 "the routine doesn't look every minute, or would text from a test on the real workspace")
            # The status server: the chat, its service worker, the HQ header, a phone signing up, texting her back.
            node = shutil.which("node") or "/opt/homebrew/bin/node"
            port = 4791
            env = dict(os.environ, HQ_STATUS_PORT=str(port), HQ_FIX_DRY="1")
            log = open(self.tmp / "h80-server.log", "w")
            srv = subprocess.Popen([node, str(ROOT / "status/server.mjs"), "--quiet"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            base = f"http://127.0.0.1:{port}"

            def call(path, data=None, header=True):
                req = urllib.request.Request(base + path, data=None if data is None else json.dumps(data).encode(),
                                             headers={"x-hq": "direct", "content-type": "application/json"} if header else {})
                try:
                    with urllib.request.urlopen(req, timeout=60) as r:
                        return r.status, r.read().decode()
                except urllib.error.HTTPError as e:
                    return e.code, e.read().decode()
            try:
                for _ in range(50):
                    try:
                        await asyncio.to_thread(call, "/direct.json")
                        break
                    except Exception:
                        await asyncio.sleep(0.2)
                code, page = await asyncio.to_thread(call, "/direct")
                need(code == 200 and "/direct/send" in page and "pushManager" in page, "the chat page isn't served")
                code, sw = await asyncio.to_thread(call, "/direct-sw.js")
                need(code == 200 and "showNotification" in sw, "the service worker isn't served")
                code, body = await asyncio.to_thread(call, "/direct.json")
                j = json.loads(body)
                need(j["agent"]["name"] == dl.agent()["name"] and j["agent"]["key"] == k["public"] and j["messages"][-1]["text"] == dl.thread()[-1]["text"],
                     f"/direct.json says {body[:200]}")
                code, _ = await asyncio.to_thread(call, "/direct/send", {"text": "hi"}, False)
                need(code == 403, f"a send without the HQ header got {code}")
                code, body = await asyncio.to_thread(call, "/direct/subscribe", {"subscription": {"endpoint": "https://push.example.com/c", "keys": {"p256dh": p256dh, "auth": auth}}, "device": "test"})
                need(code == 200 and json.loads(body)["phones"] == 2, f"signing a phone up gave {code} {body}")
                code, _ = await asyncio.to_thread(call, "/direct/send", {"text": "Is the job list done?"})
                need(code == 200, f"his text got {code}")
                for _ in range(100):
                    th = dl.thread()
                    if th[-1]["from"] == "agent" and "Is the job list done?" in th[-1]["text"]:
                        break
                    await asyncio.sleep(0.2)
                th = dl.thread()
                need(th[-2]["from"] == "me" and th[-2]["text"] == "Is the job list done?" and th[-1]["from"] == "agent",
                     f"texting her back gave {th[-2:]}")
                need(dl.unanswered() == [], "his text is still unanswered")
            finally:
                srv.terminate()
                srv.wait(timeout=10)
            # F25: the bubble is in the call page (shown on 8443, whether the phone's icon opens it or the HQ page
            # around it), no longer over the voice button from phone.js; the call line passes her paths on.
            web = (ROOT / "app/web/index.html").read_text()
            need('id="directbtn"' in web and 'location.port !== "8443"' in web, "the call page has no bubble for her chat on the phone")
            # F29: a tap opens her chat in a sheet over the call page (a frame of /direct?sheet), never leaving the page,
            # which ended a call; one sheet at a time, dragged up by its handle, closed again.
            need('target = "_top"' not in web and 'id="dirsheet"' in web and 'id="dirframe"' in web and "e.preventDefault();" in web
                 and '"/direct?sheet"' in web and web.count("showDirect(false)") >= 6 and "setPointerCapture" in web,
                 "a tap on her bubble still leaves the call page instead of opening her chat in a sheet")
            need("direct-btn" not in (ROOT / "desktop/phone.js").read_text(), "the HQ page still lays its own bubble over the voice button")
            bot = (ROOT / "app/bot.py").read_text()
            need(all(f'"{p}"' in bot.split("_DIRECT = (")[1][:300] for p in ("/direct", "/direct.json", "/direct/key", "/direct/send",
                                                                               "/direct/subscribe", "/direct-sw.js")),
                 "the call line doesn't pass her chat on to the status page")
            dh = (ROOT / "status/direct.html").read_text()
            need("location.port === '8443'" in dh and "'/manifest.webmanifest'" in dh, "the chat doesn't know it's opened through the call line")
            need("has('sheet')" in dh and "if (!SHEET && !APP) bellState();" in dh, "her chat in the sheet still shows its back arrow or signs the phone up")
        finally:
            for key, v in saved.items():
                if v is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = v
        return ("push messages encrypt for the phone and carry a valid VAPID token, a gone phone is dropped; she texts once when the "
                "job list is finished, for a new very important mail, when something stays down (a takeover at once) and when it's back; "
                "the chat, its service worker, a phone signing up and texting her back work through the status server")

    async def flow71(self) -> str:
        """H87, H91, no Claude: the three stop lines (5-hour, weekly all models, weekly Fable) each move every minute,
        the share of their window gone by (never below 10% or 20%), up to 100% in the minute before the reset, or stay
        at a fixed number; each switched from the status page or a call. The lines on made-up readings (each its own
        setting, no reset time keeps the fixed number, past the line still skips only the 5-hour one), the roadmap's
        settings (moving when they aren't named; an old flat weekly limit still fixes both weekly lines), the switch
        script on a copy, the status server's switch on a copy, what a call may run, the call rules, the page and the
        template."""
        import subprocess as sp
        from policy import Policy, ALLOW, DENY
        node = shutil.which("node") or "/opt/homebrew/bin/node"
        js = f"""import {{ stopLine, usageVerdict, movingFiveHour, lineSettings, roomNeeded, START_ROOM }} from {json.dumps((ROOT / 'status/usage.mjs').as_uri())};
import {{ parseRoadmap }} from {json.dumps((ROOT / 'status/parse.mjs').as_uri())};
const R = new Date('2026-10-12T20:00:00Z'), S = R.getTime() - 5 * 36e5, W = R.getTime() + 3 * 864e5, WS = W - 7 * 864e5;
const five = {{ label: '5-hour limit', resetsAt: R.toISOString() }};
const week = {{ label: 'Weekly · all models', resetsAt: new Date(W).toISOString() }};
const fable = {{ label: 'Weekly · Fable', resetsAt: new Date(W).toISOString() }};
const M = {{ five: {{ moving: true, fixed: 70 }}, weekly: {{ moving: true, fixed: 90 }}, fable: {{ moving: true, fixed: 90 }} }};
const F = {{ five: {{ moving: false, fixed: 70 }}, weekly: {{ moving: false, fixed: 95 }}, fable: {{ moving: false, fixed: 85 }} }};
const at = (min, L = M) => stopLine(five, L, new Date(S + min * 6e4 + 1000));
const wk = (min, l = week, L = M) => stopLine(l, L, new Date(WS + min * 6e4 + 1000));
const r = (p, w = 5) => ({{ readable: true, limits: [{{ ...five, percent: p }}, {{ ...week, percent: w }}] }});
const when = new Date(S + 60 * 6e4 + 1000);  // 1 h in, the 61st minute: the line is at 20.3%
const base = '# x\\n\\n- **Usage limit: 70%.** y\\n';
console.log(JSON.stringify({{
  first: at(0).line, half: at(29).line, after: at(30).line, hour: at(60).line, mid: at(150).line, last: at(299).line,
  perMinute: at(61).line > at(60).line && at(62).line > at(61).line, perHour: at(60).perHour,
  firstNext: at(0).next, movingNext: at(100).next,
  wFirst: wk(0).line, wMid: wk(5040).line, wLast: wk(10079).line, wRises: wk(4000).line < wk(4010).line && wk(4010).line < wk(4020).line,
  wPerHour: wk(4000).perHour, fableMoves: wk(5040, fable).line,
  fixed: at(10, F).line, wFixed: wk(5040, week, F).line, fFixed: wk(5040, fable, F).line,
  mixed: [stopLine(week, {{ ...M, weekly: F.weekly }}, new Date(WS + 5040 * 6e4)).line,
          stopLine(fable, {{ ...M, weekly: F.weekly }}, new Date(WS + 5040 * 6e4)).line],
  noReset: stopLine({{ label: '5-hour limit', resetsAt: null }}, M, new Date()).line,
  noResetW: stopLine({{ label: 'Weekly · Fable', resetsAt: null }}, M, new Date()).line,
  stops: usageVerdict(r(25), M, when).stop, under: usageVerdict(r(18), M, when).stop,
  fixedNoStop: usageVerdict(r(25), F, when).stop,
  weekStops: usageVerdict(r(5, 60), M, new Date(WS + 5040 * 6e4)).stop,
  weekFixedNoStop: usageVerdict(r(5, 60), F, new Date(WS + 5040 * 6e4)).stop,
  pastSkips: usageVerdict(r(95), M, when, {{ weeklyOnly: true }}).stop,
  pastWeek: usageVerdict(r(95, 60), M, new Date(WS + 5040 * 6e4), {{ weeklyOnly: true }}).stop,
  reason: usageVerdict(r(25), M, when).reason,
  // H141 (was H114's fixed buffer): a new job needs room for its estimate, 1 point per 2 minutes under the 5-hour line and
  // 0.2 under each weekly one; with no estimate the room of 10 minutes (H114's 5 and 1); a running job goes on to the line.
  rates: START_ROOM, need: [roomNeeded('five', 12), roomNeeded('weekly', 12), roomNeeded('fable', 2), roomNeeded('five'), roomNeeded('weekly', 0)],
  m12: [64, 63].map((p) => usageVerdict(r(p), F, when, {{ start: true, minutes: 12 }}).stop),
  m30: [55, 54].map((p) => usageVerdict(r(p), F, when, {{ start: true, minutes: 30 }}).stop),
  mWeek: [92, 91].map((p) => usageVerdict(r(5, p), F, when, {{ start: true, minutes: 30 }}).stop),
  mWeek12: [94, 93].map((p) => usageVerdict(r(5, p), F, when, {{ start: true, minutes: 12 }}).stop),
  mFable: [82, 81].map((p) => usageVerdict({{ readable: true, limits: [{{ ...fable, percent: p }}] }}, F, when, {{ start: true, minutes: 30 }}).stop),
  mPast: [usageVerdict(r(95, 92), F, when, {{ weeklyOnly: true, start: true, minutes: 30 }}).stop, usageVerdict(r(95, 91), F, when, {{ weeklyOnly: true, start: true, minutes: 30 }}).stop],
  mRun: usageVerdict(r(69), F, when, {{ minutes: 60 }}).stop,
  mReason: usageVerdict(r(66), F, when, {{ start: true, minutes: 12 }}).reason,
  b5: [66, 65, 64].map((p) => usageVerdict(r(p), F, when, {{ start: true }}).stop), b5run: usageVerdict(r(66), F, when).stop,
  b5move: [16, 15].map((p) => usageVerdict(r(p), M, when, {{ start: true }}).stop),
  bWeek: [94, 93].map((p) => usageVerdict(r(5, p), F, when, {{ start: true }}).stop), bWeekRun: usageVerdict(r(5, 94), F, when).stop,
  bFable: [84, 83].map((p) => usageVerdict({{ readable: true, limits: [{{ ...fable, percent: p }}] }}, F, when, {{ start: true }}).stop),
  bPast: [usageVerdict(r(95, 94), F, when, {{ weeklyOnly: true, start: true }}).stop, usageVerdict(r(95, 93), F, when, {{ weeklyOnly: true, start: true }}).stop],
  bReason: usageVerdict(r(66), F, when, {{ start: true }}).reason,
  none: lineSettings('# x'), dflt: parseRoadmap(base).usageLines,
  set: lineSettings(base + '- **5-hour line: fixed.** z\\n- **Weekly line: fixed at 95%.** z\\n- **Fable line: moving; fixed at 80% when switched.** z\\n'),
  flat: lineSettings(base + '- **Weekly limit: 60%.** z\\n'),
  dfltMoving: parseRoadmap(base).usageMoving, offLine: parseRoadmap(base + '- **5-hour line: fixed.** z\\n').usageMoving,
  helper: movingFiveHour(null) }}));"""
        out = await asyncio.to_thread(sp.run, [node, "--input-type=module", "-e", js], capture_output=True, text=True)
        need(out.returncode == 0, f"the line check didn't run: {out.stderr.strip()[-300:]}")
        d = json.loads(out.stdout.strip().splitlines()[-1])
        need((d["first"], d["half"], d["after"], d["hour"], d["mid"], d["last"]) == (10, 10, 10.3, 20.3, 50.3, 100),
             f"the moving 5-hour line isn't the session's share, from 10% up to 100%: {d}")
        need(d["perMinute"] and d["perHour"] == 20, "the 5-hour line doesn't move every minute, 20% an hour")
        need(d["firstNext"] == "2026-10-12T15:30:00.000Z" and d["movingNext"] is None, f"the 5-hour line's start is off: {d['firstNext']}, {d['movingNext']}")
        need(d["wFirst"] == 20 and 49 <= d["wMid"] <= 51 and d["wLast"] == 100 and d["wRises"] and d["wPerHour"] == 0.6,
             f"the weekly line doesn't move every minute from 20% to 100%: {d['wFirst']}, {d['wMid']}, {d['wLast']}, {d['wPerHour']}")
        need(d["fableMoves"] == d["wMid"], "the Fable line doesn't move like the weekly one")
        need((d["fixed"], d["wFixed"], d["fFixed"]) == (70, 95, 85), f"a fixed line isn't its own number: {d['fixed']}, {d['wFixed']}, {d['fFixed']}")
        need(d["mixed"][0] == 95 and d["mixed"][1] == d["wMid"], f"one line's switch changed another: {d['mixed']}")
        need(d["noReset"] == 70 and d["noResetW"] == 90 and d["helper"] is None, "moving without a reset time isn't the fixed number")
        need(d["stops"] and not d["under"] and not d["fixedNoStop"], "the verdict doesn't follow the moving 5-hour line")
        need(d["weekStops"] and not d["weekFixedNoStop"], "the verdict doesn't follow the weekly line's setting")
        need("its stop line is 20.3%" in d["reason"], f"the reason doesn't name the moving line: {d['reason']}")
        need(not d["pastSkips"] and d["pastWeek"], "a job past the line stops at the 5-hour line, or skips the weekly one")
        # H141: the room a new job needs grows with its estimate; the two rates in one place (usage.mjs's START_ROOM).
        need(d["rates"] == {"per": 2, "five": 1, "weekly": 0.2, "fable": 0.2}, f"the rates aren't 1% and 0.2% per 2 minutes: {d['rates']}")
        need(d["need"] == [6, 1.2, 0.2, 5, 1], f"the room a job needs isn't its estimate times the rate: {d['need']}")
        need(d["m12"] == [True, False] and d["m30"] == [True, False], f"the 5-hour room doesn't grow with the estimate: {d['m12']}, {d['m30']}")
        need(d["mWeek"] == [True, False] and d["mWeek12"] == [True, False] and d["mFable"] == [True, False],
             f"the weekly room doesn't grow with the estimate: {d['mWeek']}, {d['mWeek12']}, {d['mFable']}")
        need(d["mPast"] == [True, False], f"a job past the line skips the weekly room: {d['mPast']}")
        need(not d["mRun"], "a running job's own check needs room for an estimate")
        need("about 12 min of work needs 6% of room under its stop line of 70%, there's 4% (at 66%)" in d["mReason"],
             f"the waiting reason doesn't say how much room it needs and has: {d['mReason']}")
        # Without an estimate: the room of 10 minutes, the same as H114's old buffer.
        need(d["b5"] == [True, True, False] and not d["b5run"], f"a new job doesn't keep 5 points under the 5-hour line: {d['b5']}, {d['b5run']}")
        need(d["b5move"] == [True, False], f"the 5-hour buffer doesn't follow the moving line: {d['b5move']}")
        need(d["bWeek"] == [True, False] and not d["bWeekRun"] and d["bFable"] == [True, False],
             f"a new job doesn't keep 1 point under the weekly lines: {d['bWeek']}, {d['bWeekRun']}, {d['bFable']}")
        need(d["bPast"] == [True, False], f"a job past the line skips the weekly buffer: {d['bPast']}")
        need("about 10 min of work needs 5% of room under its stop line of 70%, there's 4% (at 66%)" in d["bReason"]
             and "buffer" not in d["bReason"].lower(), f"the waiting reason is off: {d['bReason']}")
        gate = (ROOT / "status/save-usage.mjs").read_text()
        need("{ weeklyOnly, start: true, minutes }" in gate and "'--minutes'" in gate, "the routine's start check doesn't take the job's estimate")
        need(gate.count("start: true") == 1, "the running job's own check keeps the room too")
        need("START_BUFFER" not in gate + (ROOT / "status/usage.mjs").read_text(), "H114's fixed buffer is still there")
        tick = (ROOT / "routine/tick.py").read_text()
        need('["--minutes", str(m)] if (m := job_minutes(job))' in tick and "def job_minutes(job):" in tick,
             "the routine doesn't give the gate the job's estimate")
        page = (ROOT / "status/index.html").read_text()
        need("waits for the usage line: `" in page and "gate?.state === 'waiting'" in page, "the status page doesn't say why the job waits")
        # jobs.py list says why the job first in line waits, from the routine's last start check (a copy, never the real note).
        rmq = self.tmp / "h141-roadmap.md"
        rmq.write_text((ROOT / "template/HQ/roadmap.md").read_text())
        note = self.tmp / "h141-gate-note"
        envq = {**os.environ, "HQ_ROADMAP": str(rmq), "HQ_GATE_NOTE": str(note)}
        jq = lambda *a: sp.run(["python3", str(ROOT / "routine/jobs.py"), *a], capture_output=True, text=True, env=envq)  # noqa: E731
        for i in (1, 2):
            jq("add", f"build thing {i}")
        note.write_text("2 STOP. 5-hour limit: about 12 min of work needs 6% of room under its stop line of 70%, there's 4% (at 66%).")
        o = jq("list").stdout
        need("Job 2 · ready" in o and "    Waits for the usage line: 5-hour limit: about 12 min of work needs 6% of room" in o
             and o.count("Waits for the usage line") == 1, f"jobs.py list doesn't say why the job waits: {o}")
        jq("off")
        need("Waits for the usage line" not in jq("list").stdout, "jobs.py list says it waits for the usage while the routine is off")
        need(d["none"] is None and all(v["moving"] for v in d["dflt"].values()) and d["dflt"]["weekly"]["fixed"] == 90,
             f"the roadmap's settings aren't read (moving by default): {d['none']}, {d['dflt']}")
        st = d["set"]
        need(st["five"] == {"moving": False, "fixed": 70} and st["weekly"] == {"moving": False, "fixed": 95}
             and st["fable"] == {"moving": True, "fixed": 80}, f"the three settings aren't read: {st}")
        need(d["flat"]["weekly"] == {"moving": False, "fixed": 60} == d["flat"]["fable"], f"an old flat weekly limit isn't read: {d['flat']}")
        need(d["dfltMoving"] is True and d["offLine"] is False, "the old 5-hour setting field isn't kept")

        # The switch script, on a copy of the template's roadmap; the real roadmap is refused under a test.
        copy = self.tmp / "h87-roadmap.md"
        copy.write_text((ROOT / "template/HQ/roadmap.md").read_text())
        tt = copy.read_text()
        need("**5-hour line: moving.**" in tt and "**Weekly line: moving; fixed at 90% when switched.**" in tt
             and "**Fable line: moving; fixed at 90% when switched.**" in tt, "the template doesn't start with all three lines moving (HQ's default)")
        script = str(ROOT / "routine/usageline.py")
        env = {**os.environ, "HQ_ROADMAP": str(copy)}
        ul = lambda *a, e=env: sp.run(["python3", script, *a], capture_output=True, text=True, env=e)  # noqa: E731
        o = ul()
        need(o.returncode == 0 and "moves" in o.stdout, f"reading the setting: {o.stdout}{o.stderr}")
        o = ul("fixed", "60")
        t = copy.read_text()
        need(o.returncode == 0 and "fixed at 60%" in o.stdout and "**Usage limit: 60%" in t and "**5-hour line: fixed.**" in t,
             f"fixing it at 60 didn't: {o.stdout}{o.stderr}")
        o = ul("moving")
        t = copy.read_text()
        need(o.returncode == 0 and "**5-hour line: moving.**" in t and "**Usage limit: 60%" in t and t.count("5-hour line:") == 1,
             f"moving again didn't, or lost the number: {o.stdout}{o.stderr}")
        o = ul("weekly", "fixed", "95")
        t = copy.read_text()
        need(o.returncode == 0 and "fixed at 95%" in o.stdout and "**Weekly line: fixed at 95%.**" in t
             and "**Fable line: moving; fixed at 90% when switched.**" in t and "**5-hour line: moving.**" in t,
             f"fixing the weekly line at 95 didn't, or touched another: {o.stdout}{o.stderr}")
        o = ul("fable", "fixed")
        t = copy.read_text()
        need(o.returncode == 0 and "**Fable line: fixed at 90%.**" in t, f"fixing the Fable line at its number didn't: {o.stdout}{o.stderr}")
        o = ul("weekly", "moving")
        t = copy.read_text()
        need(o.returncode == 0 and "**Weekly line: moving; fixed at 95% when switched.**" in t and t.count("Weekly line:") == 1,
             f"moving the weekly line again didn't, or lost its number: {o.stdout}{o.stderr}")
        o = ul()
        need(o.returncode == 0 and all(w in o.stdout for w in ("5-hour line", "weekly line (all models)", "Fable line is fixed at 90%")),
             f"reading all three: {o.stdout}{o.stderr}")
        need(ul("fixed", "0").returncode == 2 and ul("fixed", "150").returncode == 2 and ul("sideways").returncode == 2
             and ul("weekly", "fixed", "sixty").returncode == 2 and ul("fable", "off").returncode == 2,
             "the script takes a number outside 1 to 100, or an unknown word")
        need(copy.read_text() == t, "a refused switch still changed the roadmap")
        bare = self.tmp / "h87-bare.md"
        bare.write_text("# x\n\n- **Usage limit: 70%.** y\n")
        need(ul("fixed", e={**os.environ, "HQ_ROADMAP": str(bare)}).returncode == 0 and
             bare.read_text().count("**5-hour line: fixed.**") == 1, "a roadmap without the setting doesn't get its line")
        need(ul("fable", "fixed", "80", e={**os.environ, "HQ_ROADMAP": str(bare)}).returncode == 0 and
             ul("weekly", "moving", e={**os.environ, "HQ_ROADMAP": str(bare)}).returncode == 0, "a roadmap without the weekly lines can't switch them")
        bl = bare.read_text().split("\n")
        need([l.split(":")[0] for l in bl if " line:" in l] == ["- **5-hour line", "- **Weekly line", "- **Fable line"],
             f"the lines aren't added in their order under the usage limit: {bl}")
        real = ul("moving", e={**os.environ, "HQ_ROADMAP": os.environ.get("HQ_REAL_ROADMAP", str(ROADMAP))})
        need(real.returncode != 0, "under a test, the switch changed the real roadmap")

        # The status server's switch, on a copy of the status page and the routine.
        site = self.tmp / "h87"
        shutil.copytree(ROOT / "status", site / "status", ignore=shutil.ignore_patterns("icons"))
        shutil.copytree(ROOT / "routine", site / "routine", ignore=shutil.ignore_patterns("__pycache__", "*.o"))
        (site / ".status").mkdir()
        road = site_roadmap(site)
        road.write_text((ROOT / "template/HQ/roadmap.md").read_text())
        port = 4793
        proc = subprocess.Popen([node, str(site / "status/server.mjs"), "--quiet"],
                                env={**os.environ, "HQ_STATUS_PORT": str(port), "HQ_ROADMAP": str(road)},
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                if http_get("/roadmap.md", base)[0] == 200:
                    break
                await asyncio.sleep(0.2)

            def post(body: dict, header: str | None = "usage-line") -> tuple[int, dict]:
                req = urllib.request.Request(f"{base}/api/usage-line", data=json.dumps(body).encode(), method="POST",
                                             headers={"content-type": "application/json", **({"x-hq": header} if header else {})})
                try:
                    with urllib.request.urlopen(req, timeout=20) as r_:
                        return r_.status, json.loads(r_.read() or b"null")
                except urllib.error.HTTPError as e:
                    return e.code, {}
            code, _ = await asyncio.to_thread(post, {"mode": "fixed", "limit": 55}, None)
            need(code == 403 and "**5-hour line: moving.**" in road.read_text(), "the switch works without the page's header")
            code, ans = await asyncio.to_thread(post, {"mode": "fixed", "limit": 55})
            t = road.read_text()
            need(code == 200 and ans.get("ok") and "**5-hour line: fixed.**" in t and "**Usage limit: 55%" in t,
                 f"the page's switch didn't fix the line at 55: {code} {ans}")
            code, ans = await asyncio.to_thread(post, {"mode": "moving"})
            need(code == 200 and "**5-hour line: moving.**" in road.read_text(), f"the page's switch didn't make it move: {code} {ans}")
            code, _ = await asyncio.to_thread(post, {"mode": "fixed", "limit": 0})
            need(code == 400, "the page's switch took 0%")
            code, ans = await asyncio.to_thread(post, {"line": "weekly", "mode": "fixed", "limit": 95})
            t = road.read_text()
            need(code == 200 and "**Weekly line: fixed at 95%.**" in t and "**5-hour line: moving.**" in t,
                 f"the page's weekly switch didn't fix it at 95: {code} {ans}")
            code, ans = await asyncio.to_thread(post, {"line": "fable", "mode": "fixed"})
            need(code == 200 and "**Fable line: fixed at 90%.**" in road.read_text(), f"the page's Fable switch didn't: {code} {ans}")
            code, _ = await asyncio.to_thread(post, {"line": "monthly", "mode": "moving"})
            need(code == 400, "the page's switch took an unknown line")
            _, page, _ = http_get("/", base)
            html = page.decode()
            need("lineSwitch(key, lines[key])" in html and "['five', 'weekly', 'fable']" in html and "s.usageLines" in html
                 and "'x-hq': 'usage-line'" in html and "moving up" in html, "the status page doesn't have the three line switches")
        finally:
            proc.terminate()

        # A call: reads it, makes it move, fixes it at a number; nothing else.
        pol = Policy(config.FOLDER)
        c = f'python3 "{ROOT}/routine/usageline.py"'
        for extra in ("", " moving", " fixed", " fixed 60", " weekly", " weekly moving", " weekly fixed 95", " fable fixed",
                      " fable fixed 80%", " 5-hour moving"):
            need(pol.decide("Bash", {"command": c + extra}).verdict == ALLOW, f"a call can't run the line switch with '{extra.strip()}'")
        for extra in (" fixed sixty", " off", " moving 60", " weekly off", " fable fixed sixty", " monthly moving", " weekly fable moving"):
            need(pol.decide("Bash", {"command": c + extra}).verdict == DENY, f"a call may run the line switch with '{extra.strip()}'")
        need("usageline.py" in config.VOICE_RULES and "every minute" in config.VOICE_RULES and "weekly fixed 95" in config.VOICE_RULES
             and "fable" in config.VOICE_RULES, "the call rules don't say how to switch the three lines")
        save = (ROOT / "status/save-usage.mjs").read_text()
        need(save.count("usageLines") >= 2, "the usage check and the jobs' gate don't use the three lines")
        return ("all three lines move every minute (10% or 20% up to 100%) or stay fixed, each on its own; past the line "
                "still skips only the 5-hour one; moving by default; switched on a copy by the script, the page (its header "
                "only) and a call; the real roadmap refused")


    async def flow72(self) -> str:
        """H83, no Claude: which HQ this is, small under the name. The rule (the label, else Local and this computer's
        system) the same in Python and in the status server; the status page, /where.json (readable from the call
        page's port) and the strip's reading (/hq.json, hq_control.py health) all carry it, with and without a label;
        the strip and the call page show it, the call page out of the flow so nothing on the call screen moves (F16)."""
        import urllib.request
        sys.path.insert(0, str(ROOT / "routine"))
        import hqpaths
        system = {"darwin": "macOS", "linux": "Linux", "win32": "Windows"}.get(sys.platform, sys.platform)
        here = f"Local · {system}"
        old = os.environ.pop("HQ_LABEL", None)
        try:
            need(hqpaths.where() == here, f"without a label, where() says {hqpaths.where()!r}")
            os.environ["HQ_LABEL"] = " VPS "
            need(hqpaths.where() == "VPS", f"with HQ_LABEL=VPS, where() says {hqpaths.where()!r}")
        finally:
            os.environ.pop("HQ_LABEL", None)
            if old is not None:
                os.environ["HQ_LABEL"] = old
        node = shutil.which("node") or "/opt/homebrew/bin/node"
        seen = []
        for label, port in (("", 4793), ("VPS", 4794)):
            env = {k: v for k, v in os.environ.items() if k != "HQ_LABEL"}
            env.update({"HQ_STATUS_PORT": str(port), "HQ_FIX_DRY": "1"})
            if label:
                env["HQ_LABEL"] = label
            want = label or here
            log = open(self.tmp / f"h83-server-{port}.log", "w")
            srv = subprocess.Popen([node, str(ROOT / "status/server.mjs"), "--quiet"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            base = f"http://127.0.0.1:{port}"

            def get(path):
                with urllib.request.urlopen(base + path, timeout=60) as r:
                    return r.headers, r.read().decode()
            try:
                for _ in range(50):
                    try:
                        await asyncio.to_thread(get, "/where.json")
                        break
                    except Exception:
                        await asyncio.sleep(0.2)
                hd, body = await asyncio.to_thread(get, "/where.json")
                need(json.loads(body).get("where") == want, f"/where.json says {body} (want {want!r})")
                need(hd.get("access-control-allow-origin") == "*", "the call page's port can't read /where.json")
                _, page = await asyncio.to_thread(get, "/")
                need(f'<meta name="hq-where" content="{want}" />' in page, f"the status page doesn't carry {want!r}")
                _, body = await asyncio.to_thread(get, "/hq.json")
                need(json.loads(body).get("where") == want, f"the strip's reading says {json.loads(body).get('where')!r} (want {want!r})")
                seen.append(want)
            finally:
                srv.terminate()
                srv.wait(timeout=10)
        status = (ROOT / "status/index.html").read_text()
        need("meta[name=\"hq-where\"]" in status and "el('small', 'where', WHERE)" in status, "the status page doesn't show it under HQ")
        shell = (ROOT / "desktop/shell.html").read_text()
        need('id="where"' in shell and "$('where').textContent = h.where" in shell, "the strip (Mac app and phone) doesn't show it")
        call = (ROOT / "app/web/index.html").read_text()
        need('<h1>HQ<small id="where"></small></h1>' in call and "/where.json" in call
             and re.search(r"h1 #where \{ position:absolute;", call), "the call page doesn't show it, or it takes room (F16)")
        return f"the status page, the strip's reading and /where.json say {seen[0]!r} without a label and {seen[1]!r} with one; shown under HQ on the status page, the strip and the call page, the call screen unmoved"

    async def flow95(self) -> str:
        """H139, no Claude: the laptop's lid closed and opened again never leaves two mains. In throwaway HQ memories
        with role.py's look at the other one stood in: the online check wants a real HTTPS answer (a network that
        only accepts connections, like a café's or a phone hotspot's without internet, isn't online); a backup that
        can't reach the main and isn't really online doesn't take over; when one took over on a broken line while the
        chosen main stayed awake, online and main, the chosen main stays main and the other hands back at its first
        look (or, with a job running, starts nothing new and queues no merge jobs); a chosen main that really was
        away (asleep, or offline itself) or an older HQ that doesn't say when it took over still gives way (F23)."""
        import socket as so, threading
        now = time.time()

        def look(name, cfg, state, peer, online=True, busy="", woke=1.0):
            sup = self.tmp / f"h139-{name}"
            sup.mkdir(exist_ok=True)
            (sup / "role.json").write_text(json.dumps(cfg))
            (sup / "role-state.json").write_text(json.dumps(state))
            env = {k: v for k, v in os.environ.items() if k not in ("HQ_ROADMAP",)}
            env.update(HQ_SUPPORT=str(sup), HQ_ROLE_RETRY="0", HQ_ROLE_ONLINE="1" if online else "0",
                       HQ_ROLE_WAKETIME=str(woke))
            code = ("import sys, json; sys.path.insert(0, sys.argv[1]); import role\n"
                    "peer = json.loads(sys.argv[2]); role.peer_role = lambda c=None: peer\n"
                    "role.busy = lambda: sys.argv[3]\n"
                    "r = role.tick(log=lambda m: None)\n"
                    "print(json.dumps({**r, 'state': json.load(open(role.STATE)), 'mine': role.mine()}))")
            r = subprocess.run([sys.executable, "-c", code, str(ROOT / "routine"), json.dumps(peer), busy],
                               env=env, capture_output=True, text=True, timeout=60)
            need(r.returncode == 0, f"role.tick ({name}) failed: {r.stderr[-600:]}")
            return json.loads(r.stdout.strip().splitlines()[-1])

        # A network that accepts any connection but gives no real answer is not online.
        srv = so.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(8)
        port = srv.getsockname()[1]

        def accept():
            try:
                while True:
                    c, _ = srv.accept()
                    c.sendall(b"HTTP/1.1 302 Found\r\nLocation: http://portal.example/\r\n\r\n")
                    c.close()
            except OSError:
                pass
        threading.Thread(target=accept, daemon=True).start()
        env = {k: v for k, v in os.environ.items() if k != "HQ_ROLE_ONLINE"}
        r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import role; "
                            f"role.ONLINE_URLS = ('https://127.0.0.1:{port}/',); print(role.online())", str(ROOT / "routine")],
                           env=env, capture_output=True, text=True, timeout=60)
        srv.close()
        need(r.stdout.strip() == "False", f"a network that only accepts connections counts as online: {r.stdout}{r.stderr[-300:]}")
        src = (ROOT / "routine/role.py").read_text()
        need("create_connection((host, 443)" not in src, "the online check still only opens a connection")

        lap = {"name": "laptop", "peer": "https://vps.example:8444", "main": "vps", "chosen_at": 1, "peer_name": "vps", "takeover": 300}
        vps = {"name": "vps", "peer": "https://laptop.example:8444", "main": "vps", "chosen_at": 1, "peer_name": "laptop", "takeover": 300}
        # The lid closed at a café: the laptop looks every minute but has no real internet, the server can't be seen.
        lost = {"acting": "backup", "last_look": now - 60, "awake_since": now - 3600, "peer_lost_since": now - 900,
                "lost_looks": 9}
        r = look("cafe", lap, lost, None, online=False)
        need(r["acting"] == "backup", f"the laptop without real internet took over: {r}")
        r = look("cafe-online", lap, lost, None, online=True)
        need(r["acting"] == "main", f"a backup that's really online and can't see the main for long didn't take over: {r}")
        took = r["state"]["took_over"]
        need(r["mine"].get("took_over_at") == took, f"the one that took over doesn't say when: {r['mine']}")
        took = now - 600  # it took over ten minutes ago; the server looked every minute since
        laptop_says = {"name": "laptop", "acting": "main", "busy": "", "main": "vps", "took_over": True,
                       "took_over_at": took, "label": "Laptop"}
        # The lid opens: the server was main, awake and online the whole time: it stays main.
        vstate = {"acting": "main", "last_look": now - 30, "awake_since": now - 7200, "why": "the chosen main"}
        r = look("vps-stayed", vps, vstate, laptop_says)
        need(r["acting"] == "main" and not r["state"].get("gave_way"), f"the server that never left gave way: {r}")
        # The laptop sees the server acting main: it hands back at this first look.
        server_says = {"name": "vps", "acting": "main", "busy": "", "main": "vps", "took_over": False, "label": "VPS"}
        r = look("laptop-back", lap, {"acting": "main", "took_over": took, "last_look": now - 60,
                                      "awake_since": now - 3600, "why": "took over"}, server_says)
        need(r["acting"] == "backup", f"the laptop didn't hand back at its first look at the server as main: {r}")
        # With a job running there, it starts nothing new and lets the main queue the merges.
        r = look("laptop-busy", lap, {"acting": "main", "took_over": took, "last_look": now - 60,
                                      "awake_since": now - 3600, "why": "took over"}, server_says, busy="job 9")
        need(r["acting"] == "main" and r["handing_back"], f"with a job running the laptop isn't handing back: {r}")
        tick_src = (ROOT / "routine/tick.py").read_text()
        need('main=r["acting"] == "main" and not r.get("handing_back")' in tick_src,
             "a main that hands back still queues merge jobs for the sync's conflict copies")
        # F23 kept: a server that really was away (asleep: woke after the takeover) or offline itself gives way.
        r = look("vps-asleep", vps, {**vstate, "awake_since": took + 30}, laptop_says)
        need(r["acting"] == "backup" and r["state"].get("gave_way"), f"a main that was asleep didn't give way: {r}")
        r = look("vps-offline", vps, {**vstate, "offline_seen": took - 60}, laptop_says)
        need(r["acting"] == "backup", f"a main that was offline itself didn't give way: {r}")
        r = look("vps-stopped", vps, {**vstate, "last_look": took - 60}, laptop_says)
        need(r["acting"] == "backup", f"a main whose routine didn't look since the takeover didn't give way: {r}")
        old = {k: v for k, v in laptop_says.items() if k != "took_over_at"}
        r = look("vps-old-peer", vps, vstate, old)
        need(r["acting"] == "backup", f"with an older HQ that doesn't say when it took over, the main didn't give way: {r}")
        return ("no takeover without real internet; after the lid the main that stayed stays, the other hands back at "
                "once and queues no merges; one really away still gives way")

    async def flow96(self) -> str:
        """H137, H140, no Claude: Modern is the only look. No Look row in Settings, no saved choice and no html.modern
        switch: Modern's rules are the page's own (one style block, after the older rules), and the round buttons sit in
        the dock in the page itself, each with its name. A device that saved Classic before H140 still gets Modern:
        the real page in a headless browser, phone and desktop app, with "classic" saved on the device."""
        page = (APP / "web/index.html").read_text()
        for gone, what in (('id="lookrow"', "the Look row in Settings"), ("data-look=", "the Classic and Modern buttons"),
                           ("hq-look", "the saved look"), ("html.modern", "the html.modern switch"), ('classList.toggle("modern"', "the switch in the code"),
                           ("applyLook", "applyLook"), ("look=", "the look passed to the status page or her chat"), ("hqSpot", "Classic's own spots for the buttons")):
            need(gone not in page, f"{what} is still on the call page (H140: Modern only)")
        need(page.count('<style id="look">') == 1, "the look's style block is missing")
        dock = page.split('<nav id="dock" aria-label="HQ">', 1)
        need(len(dock) == 2, "the dock is missing")
        dock = dock[1].split("</nav>", 1)[0]
        order = [("directbtn", "Donna"), ("chatbtn", "Chat"), ("calbtn", "Calendar"), ("devbtn", "Mic"), ("notesbtn", "Notes"),
                 ("histbtn", "Calls"), ("statbtn", "Status"), ("voicebtn", "Voice")]
        at = [dock.find(f'id="{bid}" data-dl="{label}"') for bid, label in order]
        need(all(i >= 0 for i in at) and at == sorted(at), f"the dock doesn't hold the eight buttons with their names, in order: {at}")
        need(all(page.count(f'id="{bid}"') == 1 for bid, _ in order), "a dock button is on the page twice")
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        await self.ensure_server()
        saved = '<script>try { localStorage.setItem("hq-look", "classic"); } catch (e) {}</script>'
        harness = r"""<script>
setTimeout(() => {
  const out = [], dk = document.getElementById("dock").getBoundingClientRect();
  out.push("dock:" + (dk.height > 0 && Math.abs(dk.bottom - innerHeight) < 40 ? "ok" : "off " + Math.round(dk.top) + "/" + Math.round(dk.bottom)));
  const ids = ["chatbtn", "histbtn", "notesbtn", "voicebtn"].concat(document.body.classList.contains("inapp") ? [] : ["statbtn"]);
  const off = ids.filter(id => { const r = document.getElementById(id).getBoundingClientRect();
    return !(r.width > 0 && r.left >= dk.left - 1 && r.right <= dk.right + 1 && r.top >= dk.top - 1 && r.bottom <= dk.bottom + 1); });
  out.push("inside:" + (off.length ? off.join(",") : "ok"));
  out.push("label:" + getComputedStyle(document.getElementById("chatbtn"), "::after").content);
  out.push("lookrow:" + (document.querySelector("#settings [data-look]") ? "there" : "gone"));
  // H144: on a call the dock holds Calendar and Mic as well (and Donna, when her line is on); every name reads whole.
  document.getElementById("directbtn").classList.add("on"); calledHere = true; setState("live", "On the call");
  const dl = document.getElementById("dock").getBoundingClientRect(), cv = document.createElement("canvas").getContext("2d");
  const live = [...document.querySelectorAll("#dock > *")].filter(b => getComputedStyle(b).display !== "none");
  const outside = live.filter(b => { const r = b.getBoundingClientRect(); return !(r.width > 0 && r.left >= dl.left - 1 && r.right <= dl.right + 1); }).map(b => b.id);
  const cut = live.filter(b => { const a = getComputedStyle(b, "::after"); cv.font = a.fontWeight + " " + a.fontSize + " " + a.fontFamily;
    return cv.measureText(b.dataset.dl).width + (b.dataset.dl.length - 1) * (parseFloat(a.letterSpacing) || 0) > b.getBoundingClientRect().width + .5; }).map(b => b.id);
  out.push("oncall:" + (live.some(b => b.id === "calbtn") && live.some(b => b.id === "devbtn") && !outside.length && !cut.length ? "ok" : "WRONG " + live.length + " out " + outside + " cut " + cut));
  cleanup("Call ended");
  const pre = document.createElement("pre"); pre.id = "h140"; pre.textContent = "H140RESULT " + out.join(" | ") + " END"; document.body.append(pre);
}, 1500);
</script>"""
        f = self.tmp / "h140.html"
        f.write_text(page.replace("<head>", f'<head><base href="{TEST_URL.rstrip("/")}/">' + saved, 1).replace("</body>", harness + "</body>", 1))
        fa = self.tmp / "h140app.html"  # the desktop app loads the page with ?app
        fa.write_text(f.read_text().replace('new URLSearchParams(location.search).has("app")', "true", 1))
        seen = []
        for name, size, page_file in (("the phone", "390,844", f), ("the desktop app", "1180,780", fa)):
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []),
                                              f"--user-data-dir={self.tmp / 'h140-profile'}", "--disable-web-security", f"--window-size={size}",
                                              "--virtual-time-budget=6000", "--dump-dom", page_file.as_uri()], timeout=60)
            mm = re.search(r'<pre id="h140">H140RESULT (.*?) END</pre>', r.stdout)
            need(mm, f"{name}: the call page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
            res = dict(part.split(":", 1) for part in mm.group(1).split(" | "))
            say(f"   {name} ({size}): {mm.group(1)}")
            need(res["dock"] == "ok", f"{name}: with Classic saved on the device, the dock isn't at the bottom: {res}")
            need(res["inside"] == "ok", f"{name}: round buttons outside the dock: {res}")
            need(res["label"] == '"Chat"', f"{name}: the dock's buttons have no names under them: {res}")
            need(res["lookrow"] == "gone", f"{name}: the Look row is still in Settings: {res}")
            need(res["oncall"] == "ok", f"{name}: on a call (H144) Calendar or Mic isn't in the dock, a button sits outside it, or a name is cut off: {res}")
            seen.append(name)
        return "Modern only: no Look row, no saved choice, no html.modern; the eight buttons in the dock with their names, on a call too with Calendar next to Mic, every name whole (H144); Classic saved on a device still shows Modern (" + ", ".join(seen) + ")"


    # 98
    async def flow98(self) -> str:
        """F32, no network, no Claude: a friend's fresh install on an old release sees the newer one and installs it
        with one tap. A made-up public repo in a throwaway folder (v0.3, then v0.4, both with today's update code and
        status page) and two fresh installs of v0.3, the ways a friend may get one: a download without git history
        (a ZIP), and a shallow clone of the old tag without its tags. Each gets its own status page on its own port,
        on a computer whose git has no name or email. Checked: the version reads 0.3; the look sees v0.4 (also on
        the download, where fetching what's new can't work, which used to count as offline: no bar, ever); Update
        goes through (the download first becomes a clone in place); after it, 0.4 and the latest; the workspace,
        local/ and the friend's own change are kept. Everything removed after."""
        import socket as _so
        import subprocess as sp
        import urllib.request as ur
        node = shutil.which("node") or "/opt/homebrew/bin/node"
        base = self.tmp / "f32"
        up = base / "upstream"
        if base.exists():
            shutil.rmtree(base)
        genv = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_TERMINAL_PROMPT": "0"}

        def g(where, *a, env=genv):
            r = sp.run(["git", "-C", str(where), *a], capture_output=True, text=True, env=env)
            need(r.returncode == 0, f"git {' '.join(a)}: {r.stderr.strip()}")
            return r.stdout.strip()
        # The made-up public repo: HQ's own update code and status page, as they are now.
        for d in ("routine", "status"):
            shutil.copytree(ROOT / d, up / d, ignore=shutil.ignore_patterns("__pycache__", "icons"))
        (up / "desktop").mkdir()
        shutil.copy(ROOT / "desktop/shell.html", up / "desktop/shell.html")
        shutil.copy(ROOT / ".gitignore", up / ".gitignore")
        (up / "README.md").write_text("A made-up HQ, for flow 98.\n")
        log = lambda body: "# Changelog\n\n" + body + "## 0.3 · 1 January 2026\n\n### New\n- The old version.\n"
        (up / "CHANGELOG.md").write_text(log(""))
        (up / "VERSION").write_text("0.3\n")
        g(up, "init", "-q", "-b", "main"); g(up, "add", "-A"); g(up, "commit", "-qm", "0.3")
        g(up, "tag", "-a", "v0.3", "-m", "HQ 0.3")
        # The two fresh installs of 0.3, before 0.4 is out.
        dl, sh_ = base / "download", base / "shallow"
        dl.mkdir()
        arch = sp.run(["git", "-C", str(up), "archive", "v0.3"], capture_output=True, check=True).stdout
        sp.run(["tar", "-x", "-C", str(dl)], input=arch, check=True)
        g(base, "clone", "-q", "--depth", "1", "--branch", "v0.3", "--no-tags", f"file://{up}", str(sh_))
        g(sh_, "tag", "-d", "v0.3")  # a copy whose tags didn't come along (git describe finds nothing)
        for me in (dl, sh_):
            (me / "workspace").mkdir()
            (me / "workspace/me.md").write_text("# mine, flow 98\n")
            (me / "local").mkdir()
            (me / "local/my-part.sh").write_text("# my own part, flow 98\n")
            with open(me / "README.md", "a") as f:
                f.write("my own line, flow 98\n")
        # Then 0.4 comes out.
        (up / "app").mkdir()
        (up / "app/hello.txt").write_text("new in 0.4\n")
        (up / "CHANGELOG.md").write_text(log("## 0.4 · 2 January 2026\n\n### New\n- Flow ninety-eight's new thing.\n\n"))
        (up / "VERSION").write_text("0.4\n")
        g(up, "add", "-A"); g(up, "commit", "-qm", "0.4"); g(up, "tag", "-a", "v0.4", "-m", "HQ 0.4")

        def free_port() -> int:
            with _so.socket() as s_:
                s_.bind(("127.0.0.1", 0))
                return s_.getsockname()[1]

        def api(port, path, post=False):
            req = ur.Request(f"http://127.0.0.1:{port}{path}", method="POST" if post else "GET",
                             headers={"x-hq": "update"} if post else {})
            with ur.urlopen(req, timeout=150) as r:
                return json.loads(r.read())

        notes = []
        for name, me in (("download", dl), ("shallow clone", sh_)):
            port, dead = free_port(), free_port()
            rm = base / f"roadmap-{me.name}.md"
            rm.write_text("# test\n\n## The queue\n\n**Routine:** on\n")
            home = base / f"home-{me.name}"
            home.mkdir()
            # A computer whose git has no name or email yet: nothing global, and no guessing one from the system.
            env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "HQ_LOCAL"))}
            env.update({"HQ_STATUS_PORT": str(port), "HQ_UPDATE_URL": str(up), "HQ_UPDATE_RESTART": "0",
                        "HQ_PLATFORM": "darwin", "HQ_ROADMAP": str(rm), "HQ_CALL_URL": f"http://127.0.0.1:{dead}",
                        "HQ_WORKSPACE": str(me / "workspace"), "HQ_SUPPORT": str(base / f"support-{me.name}"),
                        "HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
                        "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "user.useConfigOnly", "GIT_CONFIG_VALUE_0": "true"})
            (me / ".status").mkdir(exist_ok=True)
            proc = sp.Popen([node, str(me / "status/server.mjs"), "--quiet"], env=env, cwd=str(me),
                            stdout=sp.DEVNULL, stderr=sp.DEVNULL)
            try:
                for _ in range(50):
                    if http_get("/api/update", f"http://127.0.0.1:{port}")[0] == 200:
                        break
                    await asyncio.sleep(0.2)
                s = await asyncio.to_thread(api, port, "/api/update")
                need(s["version"] == "0.3", f"{name}: it doesn't read its own version: {s}")
                # The page's first look starts the check by itself; give it a moment, then Check now.
                for _ in range(40):
                    s = await asyncio.to_thread(api, port, "/api/update")
                    if s.get("latest"):
                        break
                    await asyncio.sleep(0.5)
                need(s.get("available") and s.get("latest") == "0.4" and not s.get("offline"),
                     f"{name}: the page's own look doesn't see v0.4: {s}")
                s = await asyncio.to_thread(api, port, "/api/update/check", True)
                need(s["available"] and s["new_tag"] == "v0.4" and s["new"], f"{name}: Check now doesn't see v0.4: {s}")
                items = [i for sec in s["new"] for grp in sec["groups"] for i in grp["items"]]
                if me is sh_:
                    need("Flow ninety-eight's new thing." in items, f"{name}: what's new isn't there: {items}")
                need(not (me / "app/hello.txt").exists(), f"{name}: the look changed HQ before Update was tapped")
                # One tap.
                s = await asyncio.to_thread(api, port, "/api/update/start", True)
                for _ in range(120):
                    s = await asyncio.to_thread(api, port, "/api/update")
                    if s["run"].get("state") in ("done", "failed"):
                        break
                    await asyncio.sleep(0.5)
                need(s["run"].get("state") == "done", f"{name}: the update didn't go through: {s['run']}")
                need((me / "app/hello.txt").exists() and (me / "VERSION").read_text().strip() == "0.4",
                     f"{name}: HQ isn't on 0.4 after the update")
                s = await asyncio.to_thread(api, port, "/api/update/check", True)
                need(s["version"] == "0.4" and not s["available"] and s["latest"] == "0.4",
                     f"{name}: after the update it isn't the latest: {s}")
                need((me / "workspace/me.md").read_text() == "# mine, flow 98\n"
                     and (me / "local/my-part.sh").read_text() == "# my own part, flow 98\n",
                     f"{name}: the workspace or local/ didn't survive")
                br = (s["run"].get("saved") or {}).get("changes", {}).get("branch", "")
                need(br.startswith("hq-backup/") and "my own line, flow 98" in g(me, "show", f"{br}:README.md"),
                     f"{name}: the friend's own change isn't on the backup branch: {s['run']}")
                need(g(me, "remote", "get-url", "origin") == str(up) if me is dl else True,
                     f"{name}: the new clone doesn't know where updates come from")
                notes.append(f"{name}: 0.3, sees v0.4, one tap, 0.4 and the latest, own change on {br.split('/')[-1]}")
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except sp.TimeoutExpired:
                    proc.kill()
        shutil.rmtree(base, ignore_errors=True)
        return "; ".join(notes)

    async def flow99(self) -> str:
        """H143, no Claude: the check and the X in the calendar. planning.py on its own copies with a stand-in for the
        connector (HQ_PLANNING_FAKE: every call checked by the same guard the real runs have): marks, an X copied to
        HQ Planning and only then the original removed, undo the other way, what's never moved, a failing copy never
        removing anything, the week's look back, the call's rule and policy; the test server's /api/calendar/mark;
        and the real call page in a headless browser, phone and app: the two buttons, the X greyed, the week's past days."""
        import agenda
        import planning
        from policy import Policy, ALLOW, DENY
        d = self.tmp / "h143"
        d.mkdir(parents=True, exist_ok=True)
        real = agenda.data_file().with_name("calendar-marks.json") if not os.environ.get("HQ_CALENDAR_FILE") else None
        real = real or Path(os.path.join(agenda.hqpaths.DATA, "calendar-marks.json"))
        real_before = real.read_bytes() if real.exists() else None
        keep = {k: os.environ.get(k) for k in ("HQ_CALENDAR_FILE", "HQ_CALENDAR_MARKS", "HQ_PLANNING_FAKE", "HQ_CALENDAR",
                                               "HQ_PLANNING_CALENDAR", "HQ_CALENDAR_FAKE")}
        fake = d / "fake"
        fake.mkdir(exist_ok=True)
        os.environ.update({"HQ_CALENDAR_FILE": str(d / "calendar.json"), "HQ_PLANNING_FAKE": str(fake), "HQ_CALENDAR": "0"})
        for k in ("HQ_CALENDAR_MARKS", "HQ_PLANNING_CALENDAR", "HQ_CALENDAR_FAKE"):
            os.environ.pop(k, None)
        calls, answers = fake / "calls.jsonl", fake / "answers.jsonl"
        def answer(*items):
            answers.write_text("".join(json.dumps({"tool": t, "result": r}) + "\n" for t, r in items))
            calls.write_text("")
        def made():
            return [json.loads(l) for l in calls.read_text().splitlines()] if calls.exists() else []
        try:
            now = datetime.now()
            mon = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            iso = lambda day, h: (mon + timedelta(days=day, hours=h)).astimezone().isoformat()
            ev = lambda i, cal, gid, title, day, h, **kw: {"id": agenda._event_id(cal, gid), "gid": gid, "cal": cal, "title": title,
                                                          "start": iso(day, h), "end": iso(day, h + 1), "all_day": False, "where": "",
                                                          "notes": "", "calendar": "Main", "free": False, "type": "DEFAULT", **kw}
            cals = [{"id": "me@example.com", "name": "Main"}, {"id": "plan-id", "name": "HQ Planning"}]
            a1 = ev(1, "me@example.com", "g1", "Deep work", 0, 9, where="Desk", notes="The big one")
            a2 = ev(2, "me@example.com", "g2", "Lunch with a friend", 0, 12, others=True)
            a3 = {**ev(3, "me@example.com", "g3", "A birthday", 0, 0), "all_day": True, "type": "BIRTHDAY",
                  "start": mon.strftime("%Y-%m-%d"), "end": (mon + timedelta(days=1)).strftime("%Y-%m-%d")}
            a4 = ev(4, "me@example.com", "g4", "Gym", 1, 18)
            a5 = ev(5, "work-id", "g5", "Read", 2, 20)
            a6 = ev(6, "me@example.com", "g6", "Next week", 8, 9)
            evs = [a1, a2, a3, a4, a5, a6]
            (d / "calendar.json").write_text(json.dumps({"looked": time.time(), "calendars": cals, "events": evs}))
            need(planning.marks_file() == d / "calendar-marks.json" and planning.calendar_name() == "HQ Planning",
                 "the marks aren't next to the calendar copy, or the calendar's name isn't HQ Planning by default")
            os.environ["HQ_PLANNING_CALENDAR"] = "Other plans"
            need(planning.calendar_name() == "Other plans", "the calendar's name isn't a setting")
            os.environ.pop("HQ_PLANNING_CALENDAR")
            got = {e["id"]: e for e in agenda.read()["events"]}
            need(a1["id"] in got and a6["id"] in got and all(e["mark"] == "" for e in got.values()),
                 "this week's past days aren't in the calendar, or something is marked before a tap")
            need(agenda.prompt(now).count(mon.strftime("%Y-%m-%dT00:00:00")) == 1, "the calendar isn't read from this week's Monday")
            # done, and undo
            planning.set_mark(a1["id"], "done")
            need(next(e for e in agenda.read()["events"] if e["id"] == a1["id"])["mark"] == "done" and not planning.pending(), "the check didn't mark it, or asked for a move")
            planning.set_mark(a1["id"], "")
            need(not planning._read().get("marks"), "a second tap didn't undo the check")
            # X: the copy in HQ Planning, and only then the original removed
            planning.set_mark(a1["id"], "x")
            e1 = next(e for e in agenda.read()["events"] if e["id"] == a1["id"])
            need(e1["mark"] == "x" and e1["move"] == "to_move" and "Moving to HQ Planning" in e1["move_note"], f"the X isn't waiting to move: {e1}")
            answer(("create_event", {"id": "c1", "summary": "Deep work"}), ("delete_event", {}))
            need(planning.work() == 1, "the waiting move wasn't done")
            c = made()
            need([x["tool_name"] for x in c] == [planning.TOOL + "create_event", planning.TOOL + "delete_event"] and all(x["passed"] for x in c),
                 f"the move wasn't a guarded copy and then a removal: {c}")
            ci, di = c[0]["tool_input"], c[1]["tool_input"]
            need(ci["calendarId"] == "plan-id" and ci["summary"] == "Deep work" and ci["location"] == "Desk" and ci["description"] == "The big one"
                 and ci["notificationLevel"] == "NONE" and ci["startTime"].endswith("T09:00:00") and "+" not in ci["startTime"],
                 f"the copy isn't the same appointment in HQ Planning: {ci}")
            need(di == {"calendarId": "me@example.com", "eventId": "g1", "notificationLevel": "NONE"}, f"something else was removed: {di}")
            m1 = planning._read()["marks"][a1["id"]]
            need(m1["move"]["state"] == "moved" and m1["move"]["copy"] == {"cal": "plan-id", "gid": "c1"}, f"the move isn't saved: {m1}")
            need(next(e for e in agenda.read()["events"] if e["id"] == a1["id"])["move_note"] == "In HQ Planning", "the sheet doesn't say it's in HQ Planning")
            # the next read: the original gone, the copy in HQ Planning carries the X
            cp = {**a1, "id": agenda._event_id("plan-id", "c1"), "gid": "c1", "cal": "plan-id", "calendar": "HQ Planning"}
            (d / "calendar.json").write_text(json.dumps({"looked": time.time(), "calendars": cals, "events": [cp] + evs[1:]}))
            e1 = next(e for e in agenda.read()["events"] if e["title"] == "Deep work")
            need(e1["mark_id"] == a1["id"] and e1["mark"] == "x", f"the copy in HQ Planning doesn't carry the X: {e1}")
            need(planning.why_not(cp).startswith("Already in"), "an appointment already in HQ Planning would be moved again")
            # undo: put back where it came from, then the copy removed
            planning.set_mark(a1["id"], "")
            answer(("create_event", {"id": "b1", "summary": "Deep work"}), ("delete_event", {}))
            planning.work()
            c = made()
            need([x["tool_input"].get("calendarId") for x in c] == ["me@example.com", "plan-id"] and c[1]["tool_input"]["eventId"] == "c1"
                 and all(x["passed"] for x in c), f"undo didn't put it back and then remove the copy: {c}")
            need(not any(e["title"] == "Deep work" for e in agenda.read()["events"]),
                 "the removed copy still shows before the next read")
            need(planning._read()["marks"][a1["id"]].get("mark") == "", "undo left a mark")
            # never moved: other people in it, a birthday
            for e in (a2, a3):
                planning.set_mark(e["id"], "x")
            calls.write_text("")
            planning.work()
            st = {e["id"]: e for e in agenda.read()["events"]}
            need(not made() and st[a2["id"]]["move"] == "kept" and "other people" in st[a2["id"]]["move_note"]
                 and st[a3["id"]]["move"] == "kept" and st[a2["id"]]["mark"] == "x", "an appointment with others in it or a birthday was moved")
            # a copy that fails: tried TRIES times, and nothing is ever removed
            planning.set_mark(a4["id"], "x")
            answer()
            for _ in range(planning.TRIES):
                planning.work()
            c = made()
            m4 = planning._read()["marks"][a4["id"]]["move"]
            need(m4["state"] == "failed" and not any(x["tool_name"].endswith("delete_event") for x in c)
                 and len([x for x in c if x["tool_name"].endswith("create_event")]) == planning.TRIES,
                 f"a failing copy wasn't tried {planning.TRIES} times, stopped, and nothing removed: {m4} {c}")
            need("Couldn't move it" in next(e for e in agenda.read()["events"] if e["id"] == a4["id"])["move_note"], "the sheet doesn't say the move failed")
            planning.set_mark(a4["id"], "")
            need(a4["id"] not in planning._read()["marks"], "undoing a failed X left something")
            # copied, but the original couldn't be removed: undo only removes the copy, nothing put back twice
            planning.set_mark(a5["id"], "x")
            answer(("create_event", {"id": "c5", "summary": "Read"}), ("delete_event", {"error": "forbidden"}))
            planning.work()
            m5 = planning._read()["marks"][a5["id"]]["move"]
            need(m5["state"] == "to_move" and m5["copy"]["gid"] == "c5" and not m5.get("removed"), f"a failed removal isn't kept: {m5}")
            planning.set_mark(a5["id"], "")
            answer(("delete_event", {}))
            planning.work()
            c = made()
            need([x["tool_name"] for x in c] == [planning.TOOL + "delete_event"] and c[0]["tool_input"]["eventId"] == "c5"
                 and c[0]["tool_input"]["calendarId"] == "plan-id", f"undo after a failed removal wasn't only the copy's removal: {c}")
            # no HQ Planning calendar: said, nothing made
            (d / "calendar.json").write_text(json.dumps({"looked": time.time(), "calendars": cals[:1], "events": evs}))
            planning.set_mark(a6["id"], "x")
            calls.write_text("")
            planning.work()
            need(not made() and "no calendar named HQ Planning" in planning._read()["marks"][a6["id"]]["move"].get("error", ""),
                 "a missing HQ Planning calendar isn't said")
            planning.set_mark(a6["id"], "")
            (d / "calendar.json").write_text(json.dumps({"looked": time.time(), "calendars": cals, "events": evs}))
            # the guard: the one call asked for, once; nothing else
            exp = d / "expect.json"
            exp.write_text(json.dumps({"tool": planning.TOOL + "delete_event", "input": {"calendarId": "a", "eventId": "b"}}))
            g = lambda name, inp: planning.guard(json.dumps({"tool_name": planning.TOOL + name, "tool_input": inp}), str(exp))
            need(g("delete_event", {"calendarId": "a", "eventId": "other"}) == 2 and planning.guard(json.dumps({"tool_name": "ToolSearch", "tool_input": {}}), str(exp)) == 0 and g("update_event", {"calendarId": "a", "eventId": "b"}) == 2
                 and g("delete_event", {"calendarId": "a", "eventId": "b"}) == 0 and g("delete_event", {"calendarId": "a", "eventId": "b"}) == 2
                 and planning.guard("{}", str(d / "none.json")) == 2, "the guard lets another call through, or the same one twice")
            src = (APP / "planning.py").read_text()
            need('"--permission-mode", "dontAsk"' in src and '"--allowedTools", TOOL + tool' in src and '"PreToolUse"' in src,
                 "a move run isn't a dontAsk run with only its one tool and the guard")
            # the look back
            planning.set_mark(a2["id"], "done")
            wk = planning.week()
            need("Week of Monday" in wk and "- done: Lunch with a friend" in wk and "- X: A birthday" in wk and "Next week" not in wk
                 and "HQ Planning" in wk, f"the week's look back isn't right: {wk}")
            # the call's rule and policy
            need('planning.py" week' in config.VOICE_RULES and '"HQ Planning"' in config.VOICE_RULES, "the call rules don't say where the marks are")
            pol = Policy(config.FOLDER)
            py = str(ROOT / "app" / "planning.py")
            need(pol.decide("Bash", {"command": f'python3 "{py}" week'}).verdict == ALLOW
                 and pol.decide("Bash", {"command": f'python3 "{py}" work'}).verdict == DENY, "a call can't read the week, or can run the moves")
        finally:
            for k, v in keep.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        need((real.read_bytes() if real.exists() else None) == real_before, "the workspace's own marks were touched")

        await self.ensure_server()
        sfile = Path(self.server.env["HQ_CALENDAR_FILE"])
        sfile.parent.mkdir(parents=True, exist_ok=True)
        now = time.time()
        sfile.write_text(json.dumps({"looked": now, "calendars": [], "events": [
            {"id": "s1", "title": "Soon", "start": datetime.fromtimestamp(now + 3600).astimezone().isoformat(), "end": "", "all_day": False}]}))
        def post(body, hq):
            req = urllib.request.Request(TEST_URL + "/api/calendar/mark", data=json.dumps(body).encode(), method="POST",
                                         headers={"content-type": "application/json", **({"x-hq": hq} if hq else {})})
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.status, json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as e:
                return e.code, {}
        need(post({"id": "s1", "mark": "done"}, "")[0] == 403, "an appointment could be marked without the page's header")
        code, got = post({"id": "s1", "mark": "done"}, "calendar")
        need(code == 200 and [e.get("mark") for e in got.get("events", [])] == ["done"], f"the server didn't mark it ({code} {got})")
        need(post({"id": "nope", "mark": "done"}, "calendar")[0] == 404 and post({"id": "s1", "mark": "maybe"}, "calendar")[0] == 400,
             "an unknown appointment or mark was taken")
        code, got = post({"id": "s1", "mark": ""}, "calendar")
        need(code == 200 and got["events"][0]["mark"] == "", "the server didn't undo the mark")

        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        stub = r"""<script>
var POSTS = [], T = new Date(); T.setHours(0, 0, 0, 0);
function at(days, h, m) { const d = new Date(T); d.setDate(d.getDate() + days); d.setHours(h, m || 0); return d.toISOString(); }
var EVENTS = [
  { id: "e0", mark_id: "e0", title: "Yesterday's block", start: at(-1, 9), end: at(-1, 10), all_day: false, where: "", notes: "", calendar: "Main", free: false, mark: "", move: "", move_note: "" },
  { id: "e1", mark_id: "e1", title: "Gym", start: at(0, 23, 0), end: at(0, 23, 45), all_day: false, where: "", notes: "", calendar: "Main", free: false, mark: "", move: "", move_note: "" }];
window.fetch = async (url, opt) => {
  url = String(url);
  if (url === "api/calendar/mark") {
    const b = JSON.parse(opt.body); POSTS.push(b.id + ":" + (b.mark || "-") + ":" + (opt.headers || {})["x-hq"]);
    EVENTS = EVENTS.map(e => e.mark_id !== b.id ? e : { ...e, mark: b.mark, move: b.mark === "x" ? "moved" : "", move_note: b.mark === "x" ? "In HQ Planning" : "" });
    return { ok: true, json: async () => ({ on: true, looked: Date.now() / 1000 - 60, looking: false, error: "", events: EVENTS }) };
  }
  if (url.startsWith("api/calendar")) return { ok: true, json: async () => ({ on: true, looked: Date.now() / 1000 - 60, looking: false, error: "", events: EVENTS }) };
  return { ok: true, json: async () => ({ lines: [], calls: [], items: [] }) };
};</script>"""
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  await wait(300); calBtn.click(); await wait(400);
  const rows = () => calList.querySelectorAll(".arow"), days = () => [...calList.querySelectorAll(".day")].map(x => x.textContent);
  const mk = (i, k) => rows()[i].querySelector(".mk." + k);
  out.push("rows:" + (rows().length === 2 && calList.querySelectorAll(".appt").length === 2 && mk(0, "done") && mk(0, "x") ? "ok" : "WRONG " + rows().length));
  out.push("pastday:" + (days().length === 2 && !days()[0].startsWith("Today") && days()[1].startsWith("Today") ? "ok" : "WRONG " + days()));
  const size = mk(1, "x").getBoundingClientRect();
  out.push("tappable:" + (size.width >= 30 && size.height >= 30 && rows()[1].getBoundingClientRect().right <= innerWidth + 1 ? "ok" : "WRONG"));
  mk(1, "done").click(); await wait(300);
  out.push("done:" + (POSTS.join() === "e1:done:calendar" && mk(1, "done").getAttribute("aria-pressed") === "true"
    && getComputedStyle(mk(1, "done")).backgroundColor === "rgb(22, 163, 74)" && !rows()[1].classList.contains("x") ? "ok" : "WRONG " + POSTS));
  mk(1, "done").click(); await wait(300);
  out.push("undo:" + (POSTS[1] === "e1:-:calendar" && mk(1, "done").getAttribute("aria-pressed") === "false" ? "ok" : "WRONG " + POSTS));
  mk(0, "x").click(); await wait(300);
  const w = rows()[0].querySelector(".appt .w");
  out.push("x:" + (POSTS[2] === "e0:x:calendar" && rows()[0].classList.contains("x") && parseFloat(getComputedStyle(w).opacity) < 0.6
    && w.textContent.includes("In HQ Planning") && mk(0, "x").getAttribute("aria-pressed") === "true" ? "ok" : "WRONG " + POSTS));
  rows()[0].querySelector(".appt").click(); await wait(200);
  out.push("one:" + (calOne.textContent.includes("didn't happen as planned") && calOne.textContent.includes("In HQ Planning") ? "ok" : "WRONG"));
  document.getElementById("calclose").click();
  const pre = document.createElement("pre"); pre.id = "h143"; pre.textContent = "H143RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f2 = self.tmp / "h143.html"
        f2.write_text(page.replace("<style>", stub + "<style>", 1).replace("</body>", harness + "</body>", 1))
        for where, q in (("phone", ""), ("app", "?app=1")):
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []), "--window-size=390,844",
                                              f"--user-data-dir={self.tmp / ('h143-' + where)}", "--virtual-time-budget=20000", "--dump-dom", f2.as_uri() + q], timeout=120)
            m = re.search(r'<pre id="h143">H143RESULT (.*?) END</pre>', r.stdout)
            need(m, f"the page test didn't finish ({where}): {(r.stderr or r.stdout)[-300:]!r}")
            res = m.group(1)
            say(f"   {where}: {res}")
            need(all(part.endswith(":ok") for part in res.split(" | ")), f"the check or the X isn't right ({where}): {res}")
        return ("marks next to the calendar copy (the name a setting, HQ Planning by default), the week from Monday; a check and "
                "its undo; an X copied to HQ Planning through the guarded stand-in and only then the original removed, nobody "
                "notified; the next read's copy carrying the X; undo putting it back and removing the copy; others in it or a "
                "birthday never moved; a failing copy tried three times and nothing removed; a failed removal undone by removing "
                "only the copy; no HQ Planning said; the guard one call once; the week's look back, the call's rule and policy; "
                "/api/calendar/mark; the page, phone and app: two buttons per row, the green check, the X greyed with where it is, "
                "yesterday under its own day")

    async def flow100(self) -> str:
        """H146, no Claude: a quick note on each appointment. appt_notes.py on its own copies: add and clear per note,
        tied to the appointment's mark id so one X'd to HQ Planning keeps its notes, the listing a call reads with the
        Google ids, the call's and Donna's chat rules and the policy (read only); the test server's /api/calendar/note;
        and the real call page in a headless browser, phone and app: the note button, one tap to type, the note in the
        list and the appointment, Clear."""
        import agenda
        import appt_notes
        import planning
        import direct_line
        from policy import Policy, ALLOW, DENY
        d = self.tmp / "h146"
        d.mkdir(parents=True, exist_ok=True)
        real = Path(os.path.join(agenda.hqpaths.DATA, "calendar-notes.json"))
        real_before = real.read_bytes() if real.exists() else None
        keep = {k: os.environ.get(k) for k in ("HQ_CALENDAR_FILE", "HQ_CALENDAR_MARKS", "HQ_CALENDAR_NOTES", "HQ_PLANNING_FAKE", "HQ_CALENDAR")}
        os.environ.update({"HQ_CALENDAR_FILE": str(d / "calendar.json"), "HQ_PLANNING_FAKE": str(d / "fake"), "HQ_CALENDAR": "0"})
        for k in ("HQ_CALENDAR_MARKS", "HQ_CALENDAR_NOTES"):
            os.environ.pop(k, None)
        try:
            now = datetime.now()
            at = lambda h: now.replace(hour=h, minute=0, second=0, microsecond=0).astimezone().isoformat()
            ev = lambda cal, gid, title, h, **kw: {"id": agenda._event_id(cal, gid), "gid": gid, "cal": cal, "title": title,
                                                   "start": at(h), "end": at(h + 1), "all_day": False, "where": "", "notes": "",
                                                   "calendar": "Main", "free": False, "type": "DEFAULT", **kw}
            cals = [{"id": "me@example.com", "name": "Main"}, {"id": "plan-id", "name": "HQ Planning"}]
            a1, a2 = ev("me@example.com", "g1", "Haircut", 15), ev("me@example.com", "g2", "Dinner with friends", 19, others=True)
            (d / "calendar.json").write_text(json.dumps({"looked": time.time(), "calendars": cals, "events": [a1, a2]}))
            need(appt_notes.notes_file() == d / "calendar-notes.json", "the notes aren't next to the calendar copy")
            need(all(e["appt_notes"] == [] for e in agenda.read()["events"]) and "No notes" in appt_notes.text(),
                 "an appointment has notes before any was written")
            n = appt_notes.add(a1["id"], "  arrived 16:00\r\nleft 17:00  ")
            need(n["title"] == "Haircut" and n["items"][0]["text"] == "arrived 16:00\nleft 17:00", f"the note isn't saved as typed: {n}")
            appt_notes.add(a1["id"], "nice and short")
            got = {e["id"]: e for e in agenda.read()["events"]}
            need([x["text"] for x in got[a1["id"]]["appt_notes"]] == ["arrived 16:00\nleft 17:00", "nice and short"]
                 and got[a2["id"]]["appt_notes"] == [], f"the notes don't show on their own appointment only: {got}")
            for bad, err in (("", ValueError), ("   ", ValueError)):
                try:
                    appt_notes.add(a1["id"], bad); need(False, "an empty note was taken")
                except err:
                    pass
            try:
                appt_notes.add("nope", "x"); need(False, "a note on an unknown appointment was taken")
            except KeyError:
                pass
            txt = appt_notes.text()
            need("Haircut" in txt and "calendarId me@example.com, eventId g1" in txt and "arrived 16:00 / left 17:00" in txt
                 and "Dinner" not in txt, f"the listing a call reads isn't right: {txt}")
            appt_notes.add(a2["id"], "ran late")
            need("has other people in it" in appt_notes.text(), "the listing doesn't say an appointment has others in it")
            # X'd and moved to HQ Planning: the copy carries the notes, and the listing points at the copy
            planning.set_mark(a1["id"], "x")
            s = planning._read(); m = s["marks"][a1["id"]]
            m["also"] = [agenda._event_id("plan-id", "c1")]; m["move"] = {"state": "moved", "copy": {"cal": "plan-id", "gid": "c1"}, "removed": True}
            planning._write(s)
            cp = {**a1, "id": agenda._event_id("plan-id", "c1"), "gid": "c1", "cal": "plan-id", "calendar": "HQ Planning"}
            (d / "calendar.json").write_text(json.dumps({"looked": time.time(), "calendars": cals, "events": [cp, a2]}))
            e1 = next(e for e in agenda.read()["events"] if e["title"] == "Haircut")
            need(len(e1["appt_notes"]) == 2 and "calendarId plan-id, eventId c1" in appt_notes.text(),
                 f"the copy in HQ Planning lost its notes, or the listing points at the old one: {e1}")
            appt_notes.add(cp["id"], "via the copy")
            need(len(appt_notes._read()["notes"][a1["id"]]["items"]) == 3 and cp["id"] not in appt_notes._read()["notes"],
                 "a note on the copy didn't go to the same appointment")
            # gone from the calendar: still listed with its saved title
            (d / "calendar.json").write_text(json.dumps({"looked": time.time(), "calendars": cals, "events": [a2]}))
            need("Haircut" in appt_notes.text() and "not in the last read" in appt_notes.text(), "a note whose appointment is gone isn't listed")
            # clear per note; the last one takes the entry with it
            ids = [i["id"] for i in appt_notes._read()["notes"][a1["id"]]["items"]]
            need(appt_notes.clear(a1["id"], ids[0]) and not appt_notes.clear(a1["id"], ids[0]), "a note wasn't cleared once")
            for i in ids[1:]:
                appt_notes.clear(a1["id"], i)
            need(a1["id"] not in appt_notes._read()["notes"], "the last cleared note left its appointment behind")
            # the rules and the policy
            need('appt_notes.py' in config.VOICE_RULES and "Planned: 15:00 to 16:00" in config.VOICE_RULES
                 and 'appt_notes.py' in direct_line._text_rules(), "the call rules or Donna's chat rules don't say where the notes are")
            pol = Policy(config.FOLDER)
            py = str(ROOT / "app" / "appt_notes.py")
            need(pol.decide("Bash", {"command": f'python3 "{py}"'}).verdict == ALLOW
                 and pol.decide("Bash", {"command": f'python3 "{py}" json'}).verdict == ALLOW
                 and pol.decide("Bash", {"command": f'python3 "{py}" clear x y'}).verdict == DENY, "a call can't read the notes, or can change them")
            src = (APP / "appt_notes.py").read_text()
            need("mcp__" not in src and "claude" not in src.split('"""', 2)[2].lower(), "the notes script writes Google Calendar or runs Claude")
        finally:
            for k, v in keep.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        need((real.read_bytes() if real.exists() else None) == real_before, "the workspace's own notes were touched")

        await self.ensure_server()
        sfile = Path(self.server.env["HQ_CALENDAR_FILE"])
        sfile.parent.mkdir(parents=True, exist_ok=True)
        t = time.time()
        sfile.write_text(json.dumps({"looked": t, "calendars": [], "events": [
            {"id": "s1", "title": "Soon", "start": datetime.fromtimestamp(t + 3600).astimezone().isoformat(), "end": "", "all_day": False}]}))
        def post(body, hq):
            req = urllib.request.Request(TEST_URL + "/api/calendar/note", data=json.dumps(body).encode(), method="POST",
                                         headers={"content-type": "application/json", **({"x-hq": hq} if hq else {})})
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.status, json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as e:
                return e.code, {}
        need(post({"id": "s1", "add": "x"}, "")[0] == 403, "a note could be added without the page's header")
        code, got = post({"id": "s1", "add": "left at 5"}, "calendar")
        notes_ = got.get("events", [{}])[0].get("appt_notes") or []
        need(code == 200 and [x["text"] for x in notes_] == ["left at 5"], f"the server didn't add the note ({code} {got})")
        need(post({"id": "nope", "add": "x"}, "calendar")[0] == 404 and post({"id": "s1", "add": "  "}, "calendar")[0] == 400
             and post({"id": "s1"}, "calendar")[0] == 400 and post({"id": "s1", "clear": "nope"}, "calendar")[0] == 404,
             "an unknown appointment, an empty note or an unknown note was taken")
        code, got = post({"id": "s1", "clear": notes_[0]["id"]}, "calendar")
        need(code == 200 and got["events"][0]["appt_notes"] == [], "the server didn't clear the note")

        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        stub = r"""<script>
var POSTS = [], N = 0, T = new Date(); T.setHours(0, 0, 0, 0);
function at(days, h, m) { const d = new Date(T); d.setDate(d.getDate() + days); d.setHours(h, m || 0); return d.toISOString(); }
var EVENTS = [
  { id: "e1", mark_id: "e1", title: "Haircut", start: at(0, 23, 0), end: at(0, 23, 45), all_day: false, where: "", notes: "", calendar: "Main", free: false, mark: "", move: "", move_note: "", appt_notes: [] },
  { id: "e2", mark_id: "e2", title: "Gym", start: at(1, 9, 0), end: at(1, 10, 0), all_day: false, where: "", notes: "", calendar: "Main", free: false, mark: "", move: "", move_note: "", appt_notes: [] }];
const ANSWER = () => ({ ok: true, json: async () => ({ on: true, looked: Date.now() / 1000 - 60, looking: false, error: "", events: EVENTS }) });
window.fetch = async (url, opt) => {
  url = String(url);
  if (url === "api/calendar/note") {
    const b = JSON.parse(opt.body); POSTS.push(b.id + ":" + (b.add !== undefined ? "add=" + b.add : "clear=" + b.clear) + ":" + (opt.headers || {})["x-hq"]);
    EVENTS = EVENTS.map(e => e.mark_id !== b.id ? e : { ...e, appt_notes: b.add !== undefined ? [...e.appt_notes, { id: "n" + (++N), when: "2026-10-15 16:00", text: b.add }] : e.appt_notes.filter(n => n.id !== b.clear) });
    return ANSWER();
  }
  if (url.startsWith("api/calendar")) return ANSWER();
  return { ok: true, json: async () => ({ lines: [], calls: [], items: [] }) };
};</script>"""
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  await wait(300); calBtn.click(); await wait(400);
  const rows = () => calList.querySelectorAll(".arow"), nb = i => rows()[i].querySelector(".mk.nt");
  out.push("button:" + (rows().length === 2 && nb(0) && nb(1) && rows()[0].querySelectorAll(".mk").length === 3 ? "ok" : "WRONG " + rows().length));
  const r = nb(0).getBoundingClientRect();
  out.push("fits:" + (r.width >= 30 && r.height >= 30 && rows()[0].getBoundingClientRect().right <= innerWidth + 1
    && rows()[0].querySelector(".appt").getBoundingClientRect().width > 120 ? "ok" : "WRONG"));
  nb(0).click(); await wait(300);
  const inp = () => document.getElementById("calnotein");
  out.push("onetap:" + (calEl.classList.contains("reading") && inp() && document.activeElement === inp() ? "ok" : "WRONG"));
  inp().value = "arrived 16:00, left 17:00"; inp().dispatchEvent(new Event("input"));
  document.getElementById("calnoteadd").click(); await wait(300);
  const shown = [...calOne.querySelectorAll("#calnotes .an .txt")].map(x => x.firstChild.textContent);
  out.push("added:" + (POSTS[0] === "e1:add=arrived 16:00, left 17:00:calendar" && shown.join() === "arrived 16:00, left 17:00"
    && inp().value === "" && calOne.querySelector("h3").textContent === "Haircut" ? "ok" : "WRONG " + POSTS + " " + shown));
  calBack(); await wait(300);
  const sub = rows()[0].querySelector(".appt small.an");
  out.push("inlist:" + (sub && sub.textContent === "arrived 16:00, left 17:00" && nb(0).dataset.n === "1" && !rows()[1].querySelector("small.an") ? "ok" : "WRONG"));
  rows()[0].querySelector(".appt").click(); await wait(300);
  out.push("view:" + (calOne.querySelectorAll("#calnotes .an").length === 1 && document.activeElement !== inp() ? "ok" : "WRONG"));
  calOne.querySelector("#calnotes .clr").click(); await wait(300);
  out.push("clear:" + (POSTS[1] === "e1:clear=n1:calendar" && !calOne.querySelector("#calnotes .an") ? "ok" : "WRONG " + POSTS));
  inp().value = "half typed"; inp().dispatchEvent(new Event("input")); calEl.dispatchEvent(new Event("hq-redraw")); await wait(100);
  out.push("redraw:" + (inp().value === "half typed" && !document.getElementById("calnoteadd").disabled ? "ok" : "WRONG"));
  document.getElementById("calclose").click();
  const pre = document.createElement("pre"); pre.id = "h146"; pre.textContent = "H146RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f2 = self.tmp / "h146.html"
        f2.write_text(page.replace("<style>", stub + "<style>", 1).replace("</body>", harness + "</body>", 1))
        for where, q, size in (("phone", "", "390,844"), ("small phone", "", "320,640"), ("app", "?app=1", "390,844")):
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []), f"--window-size={size}",
                                              f"--user-data-dir={self.tmp / ('h146-' + where.replace(' ', '-'))}", "--virtual-time-budget=20000", "--dump-dom", f2.as_uri() + q], timeout=120)
            m = re.search(r'<pre id="h146">H146RESULT (.*?) END</pre>', r.stdout)
            need(m, f"the page test didn't finish ({where}): {(r.stderr or r.stdout)[-300:]!r}")
            res = m.group(1)
            say(f"   {where}: {res}")
            need(all(part.endswith(":ok") for part in res.split(" | ")), f"the appointment notes aren't right ({where}): {res}")
        return ("notes next to the calendar copy; added as typed, on their own appointment only, empty and unknown refused; "
                "the listing a call reads with the Google ids and others-in-it; an X'd appointment's copy in HQ Planning "
                "keeping its notes and taking new ones; a gone appointment still listed; clear per note; the call's and "
                "Donna's chat rules and a read-only policy; /api/calendar/note; the page on a phone, a small phone and the "
                "app: the note button in each row, one tap to type, the note in the list and the appointment, Clear, a "
                "half-typed note kept through a redraw")

    async def flow101(self) -> str:
        """H152, no Claude, no Syncthing, no network: after a crash or a restart the two computers come back in step
        by themselves. Her pings file is only written when something changed (it was written every minute, so it
        was nearly always on its way over, and a crash in between made a conflict copy and a merge job), and taking
        its lock changes nothing; the sync's ignore block leaves lock and .tmp files out and is brought up to date
        on an HQ set up before, the user's own lines kept; a conflict copy that is the same as the file, or of a
        lock, is cleared without a merge job, a real one is left to merge; a call transcript nobody committed is
        committed by the main after half an hour, a fresh one is left alone. All in a throwaway folder."""
        import importlib
        sys.path.insert(0, str(ROOT / "routine"))
        import pings as pg
        import sync as sy
        importlib.reload(sy)
        tmp = Path(tempfile.mkdtemp(prefix="hq-flow101-"))
        keep_env = {k: os.environ.get(k) for k in ("HQ_DIRECT_DIR", "HQ_CALENDAR_FILE", "HQ_AGENT_NOTES")}
        real_cfg = sy.CONFIG
        try:
            # her pings: a minute with nothing to do leaves the file and the lock as they were
            os.environ["HQ_DIRECT_DIR"] = str(tmp / "dl")
            os.environ["HQ_CALENDAR_FILE"] = str(tmp / "calendar.json")
            os.environ["HQ_AGENT_NOTES"] = str(tmp / "notes.md")
            (tmp / "dl").mkdir()
            t = time.time()
            pf, lf = tmp / "dl" / "pings.json", tmp / "dl" / ".pings.lock"
            pf.write_text(json.dumps({"reminders": [{"n": 1, "at": time.strftime(pg.FMT, time.localtime(t + 7200)),
                                                     "text": "flow 101"}]}))
            pg.watch(now=t, spawn=lambda *a: None)
            need(lf.exists(), "her pings lock wasn't taken")
            os.utime(pf, (t - 3600, t - 3600))
            os.utime(lf, (t - 3600, t - 3600))
            before = pf.read_text()
            for k in range(3):
                pg.watch(now=t + 1 + k, spawn=lambda *a: None)
            need(pf.stat().st_mtime < t - 3000, "her pings file was written again on a minute where nothing changed")
            need(lf.stat().st_mtime < t - 3000, "taking her pings lock still changes the lock file (so the sync sends it)")
            need(pf.read_text() == before, "her pings file changed on a minute where nothing happened")
            # the ignore block: lock and .tmp files stay home; an old, shorter block is replaced, his own lines kept
            ws = tmp / "ws"
            (ws / "HQ" / "calls").mkdir(parents=True)
            mem = tmp / "mem"
            mem.mkdir()
            old = [sy.MARK, ".git", ".claude/settings.local.json", "(?i)*.mp4", "(?d).DS_Store", "", "my-own-line", "// mine"]
            (ws / ".stignore").write_text("\n".join(old) + "\n")
            sy.CONFIG = str(tmp / "sync.json")
            (tmp / "sync.json").write_text(json.dumps({"peer": "X", "peer_name": "other", "folders": [
                {"id": "w", "what": "workspace", "path": str(ws)}, {"id": "m", "what": "memory", "path": str(mem)}]}))
            need(sorted(sy.keep_ignores()) == ["memory", "workspace"], "the ignore blocks weren't brought up to date")
            lines = (ws / ".stignore").read_text().splitlines()
            need("(?d).*.lock" in lines and "(?d)*.tmp" in lines, f"lock and .tmp files still go over: {lines}")
            need(lines[-2:] == ["my-own-line", "// mine"] and lines.count(sy.MARK) == 1 and "(?i)*.mp4" not in lines[len(sy.IGNORE_WORKSPACE) + 1:],
                 f"his own .stignore lines weren't kept as they were: {lines}")
            need(sy.keep_ignores() == [], "an up-to-date ignore block was written again")
            # conflict copies: the same as the file, or a lock: cleared; a real one: left for the merge job
            (ws / "HQ" / "pings.json").write_text('{"a": 1}\n')
            same = ws / "HQ" / "pings.sync-conflict-20261016-092834-ABCDEFG.json"
            same.write_text('{"a": 1}\n')
            lock = ws / "HQ" / ".pings.sync-conflict-20261016-092834-ABCDEFG.lock"
            lock.write_text("")
            (ws / "HQ" / ".pings.lock").write_text("")
            (ws / "notes.md").write_text("one\n")
            real = ws / "notes.sync-conflict-20261016-092834-ABCDEFG.md"
            real.write_text("two\n")
            said = []
            left = sy.settle(sy.conflicts(), said.append)
            need(not same.exists() and not lock.exists(), f"a copy that needs no merge is still there: {said}")
            need([c["copy"] for c in left] == [str(real)] and real.exists(), f"a real conflict wasn't left for its merge job: {left}")
            real.unlink()
            # call transcripts nobody committed: the main commits them after half an hour, a fresh one waits
            def g(*a, cwd=ws):
                return subprocess.run(["git", *a], cwd=cwd, text=True, capture_output=True, check=True)
            g("init", "-q", "--bare", "-b", "main", str(tmp / "origin.git"), cwd=tmp)
            g("init", "-q", "-b", "main")
            g("config", "user.name", "hq-test")
            g("config", "user.email", "hq-test@example.invalid")
            (ws / "HQ" / "calls" / "2026-10-15-1200.md").write_text("tracked\n")
            g("add", "HQ/calls/2026-10-15-1200.md")
            g("commit", "-q", "-m", "start")
            g("remote", "add", "origin", str(tmp / "origin.git"))
            g("push", "-q", "-u", "origin", "main")
            lost = ws / "HQ" / "calls" / "2026-10-15-1450.md"
            lost.write_text("a call whose own commit was missed\n")
            os.utime(lost, (t - 7200, t - 7200))
            fresh = ws / "HQ" / "calls" / "2026-10-16-1030.md"
            fresh.write_text("a call just over\n")
            need(sy.left_calls(t) == ["HQ/calls/2026-10-15-1450.md"], f"the transcripts left over aren't the right ones: {sy.left_calls(t)}")
            said = []
            need(sy.commit_calls(said.append, t) == 1, f"the transcript nobody committed wasn't committed: {said}")
            need(g("ls-files", "HQ/calls").stdout.split() == ["HQ/calls/2026-10-15-1200.md", "HQ/calls/2026-10-15-1450.md"],
                 "the wrong transcripts are in git")
            need("2026-10-15-1450.md" in g("ls-tree", "-r", "--name-only", "main", cwd=tmp / "origin.git").stdout,
                 "the committed transcript didn't reach GitHub (the throwaway origin)")
            need(sy.left_calls(t) == [] and sy.commit_calls(said.append, t) == 0, "a committed transcript came up again")
            return "pings written only on a change, lock untouched; lock/.tmp out of the sync, old ignore block updated with his lines kept; same/lock conflict copies cleared, a real one left; a missed transcript committed and pushed, a fresh one left"
        finally:
            sy.CONFIG = real_cfg
            for k, v in keep_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            shutil.rmtree(tmp, ignore_errors=True)

    async def flow97(self) -> str:
        """F31, no Claude, no network: a refused pull or push from a job never passes silently. push.py --pull and a
        plain push against a throwaway HQ copy whose GitHub is a throwaway folder: a pull that works says so; a remote
        that refuses opens the incident github (in a throwaway incident log) with git's own words; Donna's watch texts
        about it at once, not after three minutes; the next pull that goes through closes it, and she says it's back."""
        import importlib
        sys.path.insert(0, str(ROOT / "routine"))
        sys.path.insert(0, str(ROOT / "app"))
        import incidents as inc
        import push as pu
        import direct_line as dl
        importlib.reload(pu)
        tmp = Path(tempfile.mkdtemp(prefix="hq-flow97-"))
        real = (inc.FILE, pu.ROOT)
        try:
            def g(*a, cwd=tmp):
                return subprocess.run(["git", *a], cwd=cwd, text=True, capture_output=True, check=True)
            g("init", "-q", "--bare", "-b", "dev", str(tmp / "hub.git"))
            g("clone", "-q", str(tmp / "hub.git"), str(tmp / "hq"))
            hq = tmp / "hq"
            g("checkout", "-q", "-b", "dev", cwd=hq)
            (hq / "a.txt").write_text("one\n")
            g("add", "a.txt", cwd=hq)
            g("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "one", cwd=hq)
            g("push", "-q", "origin", "dev", cwd=hq)
            inc.FILE = str(tmp / "incidents.json")
            pu.ROOT = hq
            need(pu.pull() == 0, "a pull from a GitHub that answers didn't go through")
            need(not inc.is_down("github"), "a pull that worked opened an incident")
            g("remote", "set-url", "origin", str(tmp / "gone.git"), cwd=hq)
            need(pu.pull() == 2, "a refused pull didn't fail")
            open_ = inc.is_down("github")
            need(open_ and "pulling dev refused" in open_["why"] and open_.get("detail"),
                 f"a refused pull didn't open the github incident with git's words: {open_}")
            r = pu.git("push", "origin", "dev")
            need(r.returncode != 0, "the throwaway remote accepted a push")
            pu.refused("pushing the branch dev", r.stdout + r.stderr)
            need(len([i for i in inc.read()["incidents"] if i["key"] == "github"]) == 1, "a second refusal opened a second incident")
            now = time.time()
            data = inc.read()["incidents"]
            look = lambda d: [w for w, _ in dl.watch({}, main=False, inbox=tmp / "none.md", incidents_data=d, dry=True)]
            os.environ["HQ_DIRECT_STATE"] = str(tmp / "direct-state.json")
            real_state = dl.local_state_file
            dl.local_state_file = lambda: tmp / "direct-state.json"
            try:
                (tmp / "direct-state.json").write_text(json.dumps({"looked": now - 60}))
                if not dl.on():
                    note = "Donna's texts are off here, so her part was checked on the rule only"
                    need('in ("role", "github")' in (ROOT / "app/direct_line.py").read_text(), "Donna doesn't text a refused push at once")
                else:
                    note = ""
                    need(look(data) == ["down"], f"a refused pull wasn't texted at once: {look(data)}")
            finally:
                dl.local_state_file = real_state
                os.environ.pop("HQ_DIRECT_STATE", None)
            g("remote", "set-url", "origin", str(tmp / "hub.git"), cwd=hq)
            need(pu.pull() == 0, "the pull after the fix didn't go through")
            last = [i for i in inc.read()["incidents"] if i["key"] == "github"][-1]
            need(last.get("back") and any("went through" in f["what"] for f in last["fixes"]),
                 f"the next pull that worked didn't close the incident: {last}")
            need("--pull" in (ROOT / "routine/tick.py").read_text(), "a job's start text doesn't pull with push.py --pull")
        finally:
            inc.FILE, pu.ROOT = real
            shutil.rmtree(tmp, ignore_errors=True)
        return ("a pull that works passes quietly; a refused pull or push opens the github incident with git's words, one "
                "incident for several refusals, texted at once; the next one through closes it; jobs pull with push.py --pull"
                + (f" ({note})" if note else ""))

    async def flow89(self) -> str:
        """H118, no Claude: which computer is main, at a glance. role.py's badge in throwaway HQ memories (on its own:
        none; the main: Main; the backup: Backup · <the other> is main, by the other's label, else its name), written
        with the routine's main-or-backup line and dropped once on its own again; /where.json and the strip's reading
        carry it; the status page, the strip and the call page show it as a pill."""
        import urllib.request
        sp = {}

        def badge(name, cfg=None, state=None, label="", drop=False):
            sup = self.tmp / f"h118-{name}"
            sup.mkdir(exist_ok=True)
            if cfg is not None:
                (sup / "role.json").write_text(json.dumps(cfg))
            if state is not None:
                (sup / "role-state.json").write_text(json.dumps(state))
            rfile = self.tmp / f"h118-{name}-routines.json"
            if drop:
                rfile.write_text(json.dumps({"role": {"text": "Main (old)", "badge": {"text": "Main"}}, "mail": {"text": "x"}}))
            env = {k: v for k, v in os.environ.items() if k not in ("HQ_ROADMAP", "HQ_LABEL")}
            env["HQ_SUPPORT"] = str(sup)
            if label:
                env["HQ_LABEL"] = label
            code = ("import sys, json; sys.path.insert(0, sys.argv[1]); import role, routines; routines.FILE = sys.argv[2]\n"
                    "out = role.badge()\n"
                    "if sys.argv[3] == '1': role.tick(routines=routines); out = json.load(open(sys.argv[2]))\n"
                    "print(json.dumps(out))")
            r = subprocess.run([sys.executable, "-c", code, str(ROOT / "routine"), str(rfile), "1" if drop else "0"],
                               env=env, capture_output=True, text=True, timeout=60)
            need(r.returncode == 0, f"role.badge ({name}) failed: {r.stderr[-400:]}")
            return json.loads(r.stdout.strip().splitlines()[-1])

        need(badge("alone") == {}, "an HQ on its own shows a badge")
        left = badge("alone-drop", drop=True)
        need("role" not in left and "mail" in left, f"on its own again, the main-or-backup line stays: {left}")
        pair = {"name": "srv", "peer": "https://other.example:8444", "main": "srv", "chosen_at": 1, "peer_name": "mac"}
        b = badge("main", pair, {"acting": "main", "peer": {"name": "mac", "label": "Laptop"}}, label="VPS")
        need(b == {"acting": "main", "main": "VPS", "text": "Main"}, f"the main's badge says {b}")
        b = badge("backup", {**pair, "name": "mac", "peer_name": "srv"}, {"acting": "backup", "peer": {"name": "srv", "label": "VPS"}}, label="Laptop")
        need(b == {"acting": "backup", "main": "VPS", "text": "Backup · VPS is main"}, f"the backup's badge says {b}")
        b = badge("backup-old", {**pair, "name": "mac", "peer_name": "srv"}, {"acting": "backup", "peer": {"name": "srv"}}, label="Laptop")
        need(b["text"] == "Backup · srv is main", f"without the other's label, the backup's badge says {b}")
        b = badge("undecided", {**pair, "name": "mac"}, {}, label="Laptop")
        need(b["acting"] == "backup" and b["main"] == "mac", f"not decided yet, the badge follows the choice: {b}")
        src = (ROOT / "routine/role.py").read_text()
        need(src.count("badge=badge(c, s)") == 2, "the routine's main-or-backup line doesn't carry the badge")
        need('"label")}' in src, "the other's label isn't kept with what it answered")

        node = shutil.which("node") or "/opt/homebrew/bin/node"
        env = {k: v for k, v in os.environ.items() if k != "HQ_LABEL"}
        env.update({"HQ_STATUS_PORT": "4789", "HQ_FIX_DRY": "1"})
        log = open(self.tmp / "h118-server.log", "w")
        srv = subprocess.Popen([node, str(ROOT / "status/server.mjs"), "--quiet"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)

        def get(path):
            with urllib.request.urlopen("http://127.0.0.1:4789" + path, timeout=60) as r:
                return r.read().decode()
        try:
            for _ in range(50):
                try:
                    await asyncio.to_thread(get, "/where.json")
                    break
                except Exception:
                    await asyncio.sleep(0.2)
            w = json.loads(await asyncio.to_thread(get, "/where.json"))
            try:
                real = json.loads((ROOT / ".status/routines.json").read_text()).get("role", {}).get("badge")
            except Exception:
                real = None
            need("role" in w and w["role"] == real, f"/where.json's role is {w.get('role')} (the routine line says {real})")
            h = json.loads(await asyncio.to_thread(get, "/hq.json"))
            need("role" in h and isinstance(h["role"], dict), f"the strip's reading has no role: {h.get('role')!r}")
        finally:
            srv.terminate()
            srv.wait(timeout=10)
        status = (ROOT / "status/index.html").read_text()
        need("routines?.routines?.role?.badge" in status and "rolepill" in status, "the status page doesn't show the pill")
        shell = (ROOT / "desktop/shell.html").read_text()
        need("h.role && h.role.text" in shell and ".who .where .role.main" in shell, "the strip (Mac app and phone) doesn't show the pill")
        call = (ROOT / "app/web/index.html").read_text()
        need("w.role && w.role.text" in call and "h1 #where .role.main" in call and "setInterval(loadWhere" in call,
             "the call page doesn't show the pill, or doesn't look again")
        return ("the badge: none on its own (and the old line dropped), Main on the main, Backup · VPS is main on the backup "
                f"(by the other's name when it has no label); /where.json and the strip's reading carry it ({real}); a pill on "
                "the status page, the strip and the call page")

    async def flow73(self) -> str:
        """H92, no Claude: on a server there is no laptop to read. The status page in a headless browser, served once as a
        server (HQ_LAPTOP=0) and once as the laptop (HQ_LAPTOP=1), with a hot laptop and a low battery written down."""
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the status page in")
        node = shutil.which("node") or "/opt/homebrew/bin/node"
        site = self.tmp / "h92"
        shutil.copytree(ROOT / "status", site / "status", ignore=shutil.ignore_patterns("icons"))
        (site / ".status").mkdir()
        shutil.copy(ROADMAP, site_roadmap(site))
        now = int(time.time())
        lines = {k: {"state": "ok", "text": "fine", "at": now, "every": 60} for k in ["helper", "watchdog", "mail", "jobs", "usage", "phone", "call"]}
        lines["temp"] = {"state": "down", "text": "Hot: 95°C on the chip", "at": now, "every": 60}
        lines["battery"] = {"state": "down", "text": "Low battery: 12%, on battery", "at": now, "every": 60}
        (site / ".status/routines.json").write_text(json.dumps(lines))
        (site / ".status/battery.json").write_text(json.dumps({"t": now, "pct": 12, "plugged": False, "charging": False, "lvl": "low",
                                                              "ranges": {"low": 20, "getting_low": 40}}))
        (site / ".status/temperature.json").write_text(json.dumps({"t": now, "cpu": 95.0, "avg": 88.0, "lvl": "hot", "slow": False,
                                                                  "ranges": {"warm": 70, "hot": 90}}))
        (site / ".status/routines-history.jsonl").write_text(json.dumps({"t": now - 60, "s": {k: v["state"] for k, v in lines.items()}}) + "\n")
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 40 && !document.querySelector('.routine'); i++) await wait(250);
  await wait(1500);
  out.push('laptop:' + (document.querySelector('section.laptop') ? 'yes' : 'no'));
  out.push('pill:' + (document.querySelector('.batpill') ? 'yes' : 'no'));
  out.push('rows:' + [...document.querySelectorAll('.routine .name')].map(n => n.textContent).filter(t => /Laptop/.test(t)).length);
  out.push('lanes:' + [...document.querySelectorAll('.lane .who')].map(n => n.textContent).filter(t => /Laptop/.test(t)).length);
  out.push('alllanes:' + document.querySelectorAll('.lane .who').length);
  const rl = [...document.querySelectorAll('section')].find(s => /Routines/.test(s.querySelector('summary')?.textContent || ''));
  out.push('light:' + (rl && rl.querySelector('.light').className));
  const pre = document.createElement('pre'); pre.id = 'h92'; pre.textContent = 'H92RESULT ' + out.join(' | ') + ' END';
  document.body.appendChild(pre);
})();
</script>
"""
        idx = site / "status/index.html"
        idx.write_text(idx.read_text().replace("</body>", harness + "</body>", 1))
        seen = {}
        for laptop, port in (("0", 4796), ("1", 4797)):
            env = {**os.environ, "HQ_STATUS_PORT": str(port), "HQ_LAPTOP": laptop, "HQ_FIX_DRY": "1"}
            proc = subprocess.Popen([node, str(site / "status/server.mjs"), "--quiet"], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                base = f"http://127.0.0.1:{port}"
                for _ in range(50):
                    if http_get("/routines.json", base)[0] == 200:
                        break
                    await asyncio.sleep(0.2)
                _, page, _ = http_get("/", base)
                want = "no" if laptop == "0" else "yes"
                need(f'<meta name="hq-laptop" content="{want}" />'.encode() in page, f"the page doesn't say hq-laptop {want}")
                # Off a Mac the browser's own sandbox is refused by the system; only our own page is opened here.
                r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []),
                                                  f"--user-data-dir={self.tmp / ('h92-profile' + laptop)}",
                                                  "--virtual-time-budget=20000", "--dump-dom", base + "/"], timeout=120)
                m = re.search(r'<pre id="h92">H92RESULT (.*?) END</pre>', r.stdout)
                need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
                res = dict(part.split(":", 1) for part in m.group(1).split(" | "))
                say(f"   HQ_LAPTOP={laptop}: {m.group(1)[:300]}")
                seen[laptop] = res
            finally:
                proc.terminate()
                proc.wait(timeout=10)
        srv, lap = seen["0"], seen["1"]
        need(srv["laptop"] == "no" and srv["pill"] == "no", f"a server still shows the laptop: section {srv['laptop']}, battery {srv['pill']}")
        need(srv["rows"] == "0" and srv["lanes"] == "0", f"a server still has laptop lines under Routines: {srv['rows']} lines, {srv['lanes']} bars")
        need(int(srv["alllanes"]) > 0, "a server shows no bars at all under Routines")
        need(srv["light"] == "light", f"on a server a hot laptop and a low battery still colour the Routines light: {srv['light']}")
        need(lap["laptop"] == "yes" and lap["pill"] == "yes", f"the laptop lost its Laptop section or battery: {lap['laptop']}, {lap['pill']}")
        need(lap["rows"] == "2" and lap["lanes"] == "2", f"the laptop lost its temperature and battery lines: {lap['rows']} lines, {lap['lanes']} bars")
        need(lap["light"] == "light down", f"on the laptop a hot laptop doesn't make the Routines light red: {lap['light']}")
        return "on a server no Laptop section, no battery in the top line, no laptop lines or bars under Routines, the light green; on the laptop all of it as before, the light red"

    async def flow82(self) -> str:
        """H104, then H108, no Claude: times as 12-hour digits with a space instead of the colon, then the part
        of the day ("5 30 in the afternoon", "10 in the evening"). Both kinds of call (Quick and Deep) are told
        so; no example in the call rules or in the call system's ask-first note still says a time another way
        (in words, with a colon, half, quarter or o'clock); the speech filter turns a stray 5:30 into "5 30",
        also when it streams in pieces; and Kokoro reads "5 30" as five thirty, with no pause."""
        import brain
        from claude_llm import SpeechFilter
        rules = {"Quick": config.SYSTEM_PROMPT, "Deep": config.VOICE_RULES}
        for kind, text in rules.items():
            need('"5 30 in the afternoon"' in text and '"10 in the evening"' in text and "never a colon" in text.lower(),
                 f"a {kind} call isn't told to write times as 5 30 in the afternoon")
        hours = "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
        tens = "fifteen|thirty|forty|forty five|forty-five"
        old = re.compile(rf"half ({hours}|past)|\b({hours}) o'clock|quarter (past|to)|\b({hours}) ({tens})\b"
                         rf"|\b\d{{1,2}}:\d\d\b(?! today| tomorrow)", re.I)
        ask = brain.refusal_text(type("D", (), {"verdict": "ask", "question": "a test", "retry": False, "why": ""})())
        own = config.ME["on_calls"] or ""  # the user's own notes (me.md) may quote the old style; only HQ's rules count
        tools = config.VOICE_RULES[config.VOICE_RULES.find("When is a day and a time"):][:400]  # the scheduler's syntax
        for name, text in {**rules, "the ask-first note": ask}.items():
            text = text.replace(own, "") if own else text
            text = text.replace(tools, "").replace(config.PINGS_RULE, "")  # H124's command syntax (pings.py), not speech
            hit = old.search(text)
            need(not hit, f"{name} still says a time another way: {hit and hit.group(0)!r}")
        need('Saturday at 6 30 in the evening?' in ask, "the ask-first note's example isn't in the new style")

        def spoken(pieces):
            f = SpeechFilter()
            return "".join(f.feed(p) for p in pieces) + f.flush()
        for pieces in (["The gym at 5:30 in the afternoon."], ["The gym at 5", ":", "30 in the afternoon."],
                       ["The gym at 5:", "30 in the afternoon."]):
            got = spoken(pieces)
            need(got == "The gym at 5 30 in the afternoon.", f"the voice still gets a colon in a time: {got!r} from {pieces}")
        got = spoken(["Two things: one, ", "and 3: two."])
        need(got == "Two things: one, and 3: two.", f"a colon that isn't in a time changed: {got!r}")

        said = "Kokoro not checked (no model here)"
        if config.KOKORO_MODEL.exists():
            from kokoro_onnx import Kokoro
            k = Kokoro(str(config.KOKORO_MODEL), str(config.MODELS / "voices-v1.0.bin"))
            ph = k.tokenizer.phonemize("The gym at 5 30 in the afternoon.", lang="en-us")
            need(":" not in ph and "θˈɜːɾi" in ph and "fˈaɪv" in ph, f"Kokoro doesn't read 5 30 as five thirty: {ph!r}")
            said = "Kokoro reads 5 30 as five thirty, no pause"
        return f"Quick and Deep both write times as 5 30 in the afternoon; no other style left in the call rules or the ask-first note; a stray 5:30 is spoken as 5 30; {said}"

    async def flow81(self) -> str:
        """H81, no Claude: job estimates per computer, and patterns from all the data. The estimator on its own
        files (a throwaway roadmap copy and estimates folder, nothing real read or written), two made-up computers:
        a finished job notes its computer and tags; the other computer's jobs count, scaled by how much slower or
        faster this one turned out to be; a computer with no history starts from the other's; a tag seen often
        moves the estimate; the words say it; share gives only this computer's lines; the status server answers
        /api/estimates and the page and the job list show what was learned."""
        import subprocess as sp
        rm = self.tmp / "roadmap-H81.md"
        rm.write_text(ROADMAP.read_text())
        d = self.tmp / "roadmap-H81-estimates"
        d.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "HQ_ROADMAP": str(rm), "HQ_ESTIMATES": str(d)}
        env.pop("HQ_ROUTINES_HISTORY", None)
        script = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import estimate as E
out = {}
A = {"name": "lap", "label": "Laptop", "type": "laptop"}
B = {"name": "vps", "label": "VPS", "type": "server"}
# The laptop takes twice as long as the VPS for builds; the VPS has the history.
h = [{"n": i, "kind": "build", "actual": a, "done": i, "machine": m, "tags": t}
     for i, (a, m, t) in enumerate([(10, "lap", []), (12, "lap", []), (10, "lap", []), (5, "vps", []), (6, "vps", []),
                                    (5, "vps", []), (6, "vps", []), (5, "vps", []), (5, "vps", [])], 1)]
out["vps"] = E.estimate_detail("Build H1", h, machine="vps")
out["lap"] = E.estimate_detail("Build H1", h, machine="lap")
out["factor"] = E.factor(E._real(h), "lap", "vps", "build")
# A new computer with no history starts from the others', unscaled.
out["new"] = E.estimate_detail("Build H1", [x for x in h if x["machine"] == "vps"], machine="new")
# A tag seen on many jobs that took clearly longer than their kind's usual time moves the estimate.
p = [{"n": 100 + i, "kind": "build", "actual": (20 if i % 2 else 5), "done": 100 + i, "machine": "vps",
      "tags": (["internet"] if i % 2 else [])} for i in range(12)]
out["pat"] = {k: list(v) for k, v in E.patterns(E._real(p)).items()}
out["web"] = E.estimate_detail("Build H2: download the videos from the web", p, machine="vps")
out["plain"] = E.estimate_detail("Build H3", p, machine="vps")
out["tags"] = E.tags_of("let's go. This is job 5. The job, as agreed on the call: Scheduled item 3, planned for Tuesday: "
                        "H9: fetch the page from the web. Planned on the call of 12 October. Pull dev first, push to dev when done.")
# The words, for the status page and the job list.
E.me = lambda: A
E._peer = lambda: {"name": "vps", "label": "VPS", "type": "server", "lines": []}
out["learned"] = E.learned(h + p, A)
# share: only this computer's own lines; on_done notes the computer and the tags.
open(E.HISTORY, "w").write("".join(json.dumps(x) + "\n" for x in h))
out["share"] = E.share()
E.on_add(500, "Build H5: search the web for prices")
out["done"] = E.on_done(500, "Build H5: search the web for prices", "00:01")
out["last"] = json.loads(open(E.HISTORY).read().splitlines()[-1])
# F34: the kinds.
SC = "Sync conflict (H56.4), found by the routine: both HQs changed the same file in the workspace at once"
out["kinds"] = {"merge": E.kind_of(SC), "release": E.kind_of("H93 on the HQ roadmap: release HQ 0.4, on his say-so"),
                "notrelease": E.kind_of("F32 on the roadmap: fix the update button. Fix it so it works. Not a release: main stays."),
                "buildcolon": E.kind_of("H141 on the HQ roadmap: the gap. Build: the gate takes the estimate"),
                "firstversion": E.kind_of("H74 on the HQ roadmap: a tutorial. Build a first version: an animated click-through"),
                "fixso": E.kind_of("F33 on the HQ roadmap: a typed line is sent twice. Fix it so a new line only carries itself"),
                "research": E.kind_of("H68 on the roadmap: research only. Nothing built"),
                "mergehand": E.kind_for(SC, "build"), "callhand": E.kind_for("Build H7", "call")}
# F34: a seeded line doesn't count; only measured times do.
s = [{"n": 1, "kind": "build", "actual": 90, "done": 1, "machine": "vps", "how": "seed"}] + \
    [{"n": i, "kind": "build", "actual": 5, "done": i, "machine": "vps", "how": "seen"} for i in range(2, 6)]
out["seed"] = E.estimate_detail("Build H1", s, machine="vps")
# F34: a job the other HQ added, with its kind there; and a waiting job follows the newest finished jobs.
E._load_state = lambda: {}
cs = [{"n": 10 + i, "kind": "call", "actual": 9, "done": 10 + i, "machine": "vps", "how": "seen"} for i in range(4)]
E._peer = lambda: {"name": "vps", "label": "VPS", "type": "server", "lines": [], "open": {"77": {"kind": "call", "est": 9}}}
d77 = E.job_estimate(77, "Measure the token cost of one run", s + cs, "vps")
out["peer_kind"], out["peer_est"] = d77["kind"], d77["est"]
E._peer = lambda: {"name": "vps", "label": "VPS", "type": "server", "lines": []}
later = s + [{"n": 20 + i, "kind": "build", "actual": 20, "done": 20 + i, "machine": "vps", "how": "seen"} for i in range(12)]
out["follows"] = [E.job_estimate(78, "Build H8", s, "vps")["est"], E.job_estimate(78, "Build H8", later, "vps")["est"]]
# F34: retag: every finished line here gets its kind and tags from its text, the other HQ's lines too (kept apart).
E.me = lambda: B
open(E.HISTORY, "w").write("".join(json.dumps(x) + "\n" for x in [
    {"n": 1, "kind": "other", "actual": 1, "done": 1, "how": "seen"}, {"n": 2, "kind": "other", "actual": 6, "done": 2, "how": "seen"},
    {"n": 3, "kind": "other", "actual": 3, "done": 3, "how": "seen"}, {"n": 4, "kind": "call", "actual": 4, "done": 4, "how": "seen"}]))
E._peer = lambda: {"name": "lap", "label": "Laptop", "type": "laptop", "lines": [{"n": 9, "kind": "other", "actual": 2, "done": 9, "machine": "lap"}]}
E.retag(texts={1: SC, 2: "H74: Build a first version", 3: "H93 on the HQ roadmap: release HQ 0.4", 4: "Build H4", 9: SC}, quiet=True)
lines = E.history()
out["retag"] = {"kinds": [x["kind"] for x in lines], "marked": all(x.get("retag") == E.RETAG for x in lines),
                "peer": json.load(open(E.RETAGS))["lines"].get("lap|9")}
E.me = lambda: A
out["back"] = E.backtest(h)
print("H81OUT " + json.dumps(out))
"""
        r = sp.run([sys.executable, "-c", script, str(ROOT / "routine")], capture_output=True, text=True, env=env, timeout=60)
        m = re.search(r"H81OUT (.*)", r.stdout)
        need(m, f"the estimator didn't run: {r.stdout[-500:]} {r.stderr[-1500:]}")
        o = json.loads(m.group(1))
        need(o["vps"]["est"] == 5 and o["vps"]["own"] == 6, f"on the VPS its own builds don't count first: {o['vps']}")
        f, n = o["factor"]
        need(1.5 < f < 2.1 and n == 3, f"the laptop isn't seen as about twice as slow as the VPS for builds: {o['factor']}")
        need(7 <= o["lap"]["est"] <= 12 and o["lap"]["own"] == 3 and o["lap"]["other"] == 6, f"the laptop's estimate isn't its own builds plus the VPS's scaled: {o['lap']}")
        need(o["new"]["est"] == 5 and o["new"]["own"] == 0 and o["new"]["other"] == 6,
             f"a computer with no history doesn't start from the other's: {o['new']}")
        need("internet" in o["pat"] and o["pat"]["internet"][0] >= 1.5, f"a slow tag isn't found as a pattern: {o['pat']}")
        need(o["web"]["est"] > o["plain"]["est"] and o["web"]["pattern"] > 1 and o["plain"]["pattern"] == 1,
             f"the pattern doesn't move the estimate of a job with that tag (only): {o['web']} {o['plain']}")
        need(o["tags"] == ["internet"], f"the tags read the routine's own wording too: {o['tags']}")
        # F34: the kinds the wording tells for sure, builds worded otherwise, a merge stays a merge whatever a call says.
        k = o["kinds"]
        need(k["merge"] == "merge" and k["release"] == "release" and k["notrelease"] == "build" and k["buildcolon"] == "build"
             and k["firstversion"] == "build" and k["fixso"] == "build" and k["research"] == "other" and k["mergehand"] == "merge"
             and k["callhand"] == "call", f"F34: the kinds are wrong: {k}")
        need(o["seed"]["est"] == 5, f"F34: a seeded line (no measured time) still counts: {o['seed']}")
        # F34: a job added on the other HQ (its kind there) is estimated under that kind here, not guessed again.
        need(o["peer_kind"] == "call" and o["peer_est"] == 9, f"F34: a job from the other HQ loses its kind: {o['peer_kind']} {o['peer_est']}")
        need(o["follows"][0] == 5 and o["follows"][1] == 20, f"F34: a waiting job's estimate doesn't follow the newest jobs: {o['follows']}")
        need(o["retag"]["kinds"] == ["merge", "build", "release", "call"] and o["retag"]["marked"] and o["retag"]["peer"] == {"kind": "merge", "tags": ["files"]},
             f"F34: retag doesn't give every finished job its kind again: {o['retag']}")
        need(o["back"]["count"] == 8 and o["back"]["avg_off"] >= 0, f"F34: estimating the finished jobs back doesn't work: {o['back']}")
        words = " ".join(o["learned"])
        need("Estimates are for the Laptop, from 3 finished jobs there and 18 on the VPS" in words
             and "The Laptop takes about 1." in words and "times as long as the VPS" in words and "need the internet take about" in words,
             f"what was learned isn't said in words: {o['learned']}")
        need(o["share"]["name"] == "lap" and [x["n"] for x in o["share"]["lines"]] == [1, 2, 3], f"share gives other computers' lines as its own: {o['share']}")
        last = o["last"]
        need(last["n"] == 500 and last.get("machine") and last.get("type") in ("laptop", "server") and "internet" in last["tags"],
             f"a finished job doesn't note its computer and tags: {last}")
        srv = (ROOT / "status/server.mjs").read_text()
        need("path0 === '/api/estimates'" in srv and "'share'" in srv, "the status server doesn't answer /api/estimates")
        page = (ROOT / "status/index.html").read_text()
        need("etaLearned(E)" in page, "the status page doesn't show what the estimates learned")
        need("p.get(\"learned\")" in (ROOT / "routine/jobs.py").read_text(), "the job list on calls doesn't say what was learned")
        need("estimate.pull(log=log)" in (ROOT / "routine/tick.py").read_text(), "the routine doesn't pull the other HQ's finished jobs")
        return ("each computer's own jobs first, the other's scaled (laptop about 2 times the VPS), a new computer starts "
                "from the other's, a slow tag moves the estimate, said in words; only its own lines shared; served and shown")

    async def flow80(self) -> str:
        """F9, no Claude: a call left quiet stays connected. Pipecat ends a pipeline after 5 minutes with nothing
        spoken or heard (typed lines and her thinking don't count); the call line turns that off. Two tiny pipelines,
        nothing else: one with a 1 s idle timeout ends by itself (the cause, so a Pipecat update can't hide it), one
        with the call's own setting is still running after 3 s. Then the code: the call server uses that setting, and
        a real hang-up or a lost connection still ends the call."""
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.worker import PipelineParams, PipelineWorker
        from pipecat.processors.filters.identity_filter import IdentityFilter
        from pipecat.workers.runner import WorkerRunner

        need(config.CALL_IDLE_SECS is None, f"the call line has an idle timeout again ({config.CALL_IDLE_SECS} s)")

        async def quiet_for(secs: float, idle) -> bool:
            """True when a pipeline with this idle timeout is still running after secs of nothing."""
            worker = PipelineWorker(Pipeline([IdentityFilter()]), params=PipelineParams(),
                                    idle_timeout_secs=idle, check_dangling_tasks=False)
            idled = []

            @worker.event_handler("on_idle_timeout")
            async def on_idle(w):
                idled.append(True)

            runner = WorkerRunner(handle_sigint=False)
            await runner.add_workers(worker)
            task = asyncio.create_task(runner.run())
            await asyncio.sleep(secs)
            alive = not idled and not task.done()
            if alive:
                await worker.cancel()
            try:
                await asyncio.wait_for(task, 10)
            except Exception:
                pass
            return alive

        need(not await quiet_for(3.0, 1.0), "a 1 s idle timeout didn't end a quiet pipeline: the cause can't be shown")
        need(await quiet_for(3.0, config.CALL_IDLE_SECS), "a quiet pipeline with the call's setting ended by itself")
        bot = (APP / "bot.py").read_text()
        need("idle_timeout_secs=config.CALL_IDLE_SECS" in bot, "the call server doesn't use the call's idle setting")
        gone = bot.split('@transport.event_handler("on_client_disconnected")', 1)[1].split("@", 1)[0]
        need("await worker.cancel()" in gone, "a lost connection no longer ends the call")
        page = (APP / "web/index.html").read_text()
        need('pc.connectionState === "failed" || pc.connectionState === "closed"' in page,
             "the call page no longer closes a call whose connection failed")
        return ("a 1 s idle timeout ends a quiet pipeline; the call's setting (none) keeps it on; "
                "the call server uses it; a lost connection or hang-up still ends the call")

    async def flow79(self) -> str:
        """H88, no Claude: heartbeats for both computers. The routine's part with a throwaway HQ memory (its own
        pairing, a stand-in for the other HQ on a spare port, the lines and incidents caught, nothing real written):
        alone no lines; paired, this computer up and online and the other answering; one missed answer yellow, two
        red with an incident, closed when it answers again; offline, this one red and the other "can't tell"; a
        new name leaves no old line. Then the status page in a headless browser: Laptop and VPS right after Main
        or backup, red when down, with their bars in the graph."""
        import subprocess as sp
        sup = self.tmp / "h88-support"
        sup.mkdir()
        driver = self.tmp / "h88-driver.py"
        driver.write_text(r"""
import http.server, json, os, sys, threading
sys.path.insert(0, sys.argv[1])
import heartbeat, role
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        b = json.dumps({"name": "far-away", "label": "VPS", "main": "far-away", "acting": "main"}).encode()
        self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
srv = http.server.HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
class R:
    lines, dropped = {}, []
    def beat(self, k, **f): self.lines[k] = f
    def drop(self, prefix, keep=()):
        for k in [k for k in self.lines if k.startswith(prefix) and k not in keep]:
            del self.lines[k]; self.dropped.append(k)
class I:
    log, open_ = [], set()
    def is_down(self, k): return k in self.open_
    def down(self, k, why, at=None): self.log.append(("down", k, why)); self.open_.add(k)
    def fix(self, k, what, at=None): self.log.append(("fix", k, what))
    def up(self, k, at=None): self.log.append(("up", k)); self.open_.discard(k)
r, i, out = R(), I(), {}
r.lines["beat-old"] = {"state": "ok"}
out["alone"] = [heartbeat.tick(routines=r, incidents=i), sorted(r.lines)]
json.dump({"name": "here", "peer": f"http://127.0.0.1:{srv.server_port}/", "peer_name": "far-away", "main": "here", "chosen_at": 1},
          open(os.path.join(os.environ["HQ_SUPPORT"], "role.json"), "w"))
out["label"] = role.mine().get("label")
def snap(): return {k: [v["name"], v["state"], v["text"]] for k, v in sorted(r.lines.items())}
heartbeat.tick(routines=r, incidents=i, online=True); out["up"] = snap()
heartbeat.tick(routines=r, incidents=i, online=True, peer={}); out["miss1"] = snap()
heartbeat.tick(routines=r, incidents=i, online=True, peer={}); out["miss2"] = snap(); out["inc2"] = list(i.log)
heartbeat.tick(routines=r, incidents=i, online=True); out["back"] = snap(); out["inc3"] = list(i.log)
heartbeat.tick(routines=r, incidents=i, online=False, peer={}); out["offline"] = snap()
os.environ["HQ_LABEL"] = "Server"
heartbeat.tick(routines=r, incidents=i, online=True); out["renamed"] = snap()
print("H88OUT " + json.dumps(out))
""")
        env = {**os.environ, "HQ_SUPPORT": str(sup), "HQ_LABEL": "Laptop"}
        env.pop("HQ_ROADMAP", None)
        r = sp.run([sys.executable, str(driver), str(ROOT / "routine")], capture_output=True, text=True, env=env, timeout=120)
        m = re.search(r"H88OUT (.*)", r.stdout)
        need(m, f"the heartbeat test didn't finish: {(r.stderr or r.stdout)[-400:]}")
        o = json.loads(m.group(1))
        need(o["alone"][0] is None and o["alone"][1] == [], f"alone, an HQ still writes heartbeat lines or keeps old ones: {o['alone']}")
        need(o["label"] == "Laptop", f"the role answer doesn't carry this computer's short name: {o['label']}")
        need(o["up"] == {"beat-laptop": ["Laptop", "ok", "Up and online"], "beat-vps": ["VPS", "ok", o["up"]["beat-vps"][2]]}
             and o["up"]["beat-vps"][2].startswith("Answers ("), f"paired, the two lines aren't both green: {o['up']}")
        need(o["miss1"]["beat-vps"][1] == "waiting", f"one missed answer isn't yellow: {o['miss1']}")
        need(o["miss2"]["beat-vps"][1] == "down" and "Doesn't answer since" in o["miss2"]["beat-vps"][2], f"two missed answers aren't red: {o['miss2']}")
        need(any(e[0] == "down" and e[1] == "beat-vps" for e in o["inc2"]), f"no incident when the other stopped answering: {o['inc2']}")
        need(o["back"]["beat-vps"][1] == "ok" and o["inc3"][-1] == ["up", "beat-vps"], f"answering again doesn't turn green and close the incident: {o['back']} {o['inc3'][-2:]}")
        need(o["offline"]["beat-laptop"][1] == "down" and o["offline"]["beat-vps"][1] == "waiting" and "Can't tell" in o["offline"]["beat-vps"][2],
             f"offline isn't this one red and the other can't tell: {o['offline']}")
        need(sorted(o["renamed"]) == ["beat-server", "beat-vps"], f"a new name left an old line behind: {sorted(o['renamed'])}")
        # The status page.
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the status page in")
        node = shutil.which("node") or "/opt/homebrew/bin/node"
        site = self.tmp / "h88"
        shutil.copytree(ROOT / "status", site / "status", ignore=shutil.ignore_patterns("icons"))
        (site / ".status").mkdir()
        shutil.copy(ROADMAP, site_roadmap(site))
        now = int(time.time())
        lines = {k: {"state": "ok", "text": "fine", "at": now, "every": 60} for k in ["helper", "watchdog", "mail", "jobs", "usage", "phone", "call"]}
        lines["role"] = {"state": "ok", "text": "Main (here)", "at": now, "every": 60}
        lines["beat-vps"] = {"state": "down", "text": "Doesn't answer since 12:00", "name": "VPS", "at": now, "every": 60}
        lines["beat-laptop"] = {"state": "ok", "text": "Up and online", "name": "Laptop", "at": now, "every": 60}
        (site / ".status/routines.json").write_text(json.dumps(lines))
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 40 && !document.querySelector('.routine'); i++) await wait(250);
  await wait(2500);
  out.push('rows:' + [...document.querySelectorAll('.routine .name')].map(n => n.textContent).join(','));
  out.push('vps:' + ([...document.querySelectorAll('.routine')].find(r => r.querySelector('.name')?.textContent === 'VPS')?.className ?? ''));
  out.push('lanes:' + [...document.querySelectorAll('.lane .who')].map(n => n.textContent).filter(t => t === 'Laptop' || t === 'VPS').join(','));
  const pre = document.createElement('pre'); pre.id = 'h88'; pre.textContent = 'H88RESULT ' + out.join(' | ') + ' END';
  document.body.appendChild(pre);
})();
</script>
"""
        idx = site / "status/index.html"
        idx.write_text(idx.read_text().replace("</body>", harness + "</body>", 1))
        import socket as _socket
        with _socket.socket() as _s:  # a free port: a spare one may be taken by another HQ's test server
            _s.bind(("127.0.0.1", 0))
            port = _s.getsockname()[1]
        env = {**os.environ, "HQ_STATUS_PORT": str(port), "HQ_LAPTOP": "0", "HQ_FIX_DRY": "1"}
        proc = subprocess.Popen([node, str(site / "status/server.mjs"), "--quiet"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                if http_get("/routines.json", base)[0] == 200:
                    break
                await asyncio.sleep(0.2)
            hist = b""
            for _ in range(25):
                _, hist, _ = http_get("/routines-history.json?h=1", base)
                if b"beat-vps" in hist:
                    break
                await asyncio.sleep(0.2)
            need(b'"beat-vps":"down"' in hist and b'"beat-laptop":"ok"' in hist, f"the graph's record has no heartbeat lines: {hist[-300:]!r}")
            r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run", *(["--no-sandbox"] if sys.platform != "darwin" else []),
                                              f"--user-data-dir={self.tmp / 'h88-profile'}", "--virtual-time-budget=20000", "--dump-dom", base + "/"], timeout=120)
        finally:
            proc.terminate()
            proc.wait(timeout=10)
        m = re.search(r'<pre id="h88">H88RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        res = dict(part.split(":", 1) for part in m.group(1).split(" | "))
        say(f"   page: {m.group(1)[:300]}")
        rows = res["rows"].split(",")
        need(rows[:3] == ["Main or backup", "Laptop", "VPS"], f"Laptop and VPS aren't right after Main or backup: {rows[:5]}")
        need("down" in res["vps"], f"the VPS line isn't red when it doesn't answer: {res['vps']}")
        need(res["lanes"] == "Laptop,VPS", f"the graph has no bars for Laptop and VPS: {res['lanes']}")
        return ("alone no lines; paired both green, one miss yellow, two red with an incident, closed when back; offline this "
                "one red and the other can't tell; a new name leaves no old line; on the page Laptop and VPS right after Main "
                "or backup, the VPS red, both with bars in the graph")

    async def flow76(self) -> str:
        """H78, no Claude: the call's policy on calendar changes, with made-up events (nothing reaches the calendar).
        Adding goes without asking; moving or deleting too, once the event was looked at on this call (what it was
        goes into the transcript's line); other people in it, or answering an invitation, asks; a test run stops all."""
        from policy import Policy, ALLOW, ASK, DENY
        import brain as _brain
        from pipeline import make_brain
        C = "mcp__claude_ai_Google_Calendar__"
        pol = Policy(config.FOLDER)
        need(pol.decide(C + "create_event", {"summary": "Gym"}).verdict == ALLOW, "adding his own event still asks")
        need(pol.decide(C + "create_event", {"summary": "Lunch", "attendees": [{"email": "a@example.com"}]}).verdict == ASK,
             "adding an event with someone invited doesn't ask")
        d = pol.decide(C + "delete_event", {"eventId": "own1"})
        need(d.verdict == DENY and d.retry and "Not yet" in _brain.refusal_text(d),
             "deleting an event she hasn't looked at isn't stopped, or not as a 'look first'")
        answer = [{"type": "text", "text": json.dumps({"events": [
            {"id": "own1", "summary": "Gym", "start": {"dateTime": "2026-10-14T10:00:00+02:00"},
             "end": {"dateTime": "2026-10-14T11:00:00+02:00"}, "organizer": {"email": "me@example.com", "self": True}},
            {"id": "with1", "summary": "Lunch", "start": {"dateTime": "2026-10-15T12:00:00+02:00"},
             "end": {"dateTime": "2026-10-15T13:00:00+02:00"}, "organizer": {"email": "me@example.com", "self": True},
             "attendees": [{"email": "me@example.com", "self": True}, {"email": "a@example.com"}]},
            {"id": "inv1", "summary": "Their meeting", "start": {"date": "2026-10-16"},
             "organizer": {"email": "someone@example.com"}}]})}]
        pol.seen(C + "list_events", answer)
        d = pol.decide(C + "delete_event", {"eventId": "own1"})
        need(d.verdict == ALLOW and '"Gym"' in d.why and "2026-10-14T10:00" in d.why,
             f"deleting his own event she looked at doesn't go, or doesn't keep what it was: {d.why}")
        need(pol.decide(C + "update_event", {"eventId": "own1", "start": {}}).verdict == ALLOW, "moving his own event still asks")
        need(pol.decide(C + "update_event", {"eventId": "own1", "attendees": [{"email": "b@example.com"}]}).verdict == ASK,
             "inviting someone to his event doesn't ask")
        need(pol.decide(C + "update_event", {"eventId": "with1", "start": {}}).verdict == ASK, "moving an event with others in it doesn't ask")
        need(pol.decide(C + "delete_event", {"eventId": "inv1"}).verdict == ASK, "deleting someone else's invitation doesn't ask")
        need(pol.decide(C + "respond_to_event", {"eventId": "inv1"}).verdict == ASK, "answering an invitation doesn't ask")
        test = Policy(config.FOLDER, dry_run=True)
        need(test.decide(C + "create_event", {"summary": "Gym"}).verdict == DENY, "a test run can change the calendar")
        need("The calendar (H78)" in config.VOICE_RULES, "the call isn't told it may change the calendar")
        opts = make_brain(config.MODEL_ALIASES["sonnet"], test, load="quick")._options
        need("PostToolUse" in opts.hooks, "the call doesn't tell the policy what a calendar read showed")
        return "adding goes; moving and deleting after a look, with what it was kept; others in it and invitations ask; tests change nothing"

    async def flow75(self) -> str:
        """F18, no Claude: the status page on the phone only scrolls up and down. A copy of the status page in a
        headless browser at phone widths, with a job and a roadmap note that hold a long path and a key (no space
        to break at), every fold opened: no element's right edge is past the screen and the page is no wider than it."""
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the status page in")
        node = shutil.which("node") or "/opt/homebrew/bin/node"
        page = (ROOT / "status/index.html").read_text()
        need("if (window.scrollY !== y || window.scrollX !== 0) window.scrollTo(0, y);" in page,
             "the redraw scrolls the page back every time again (that stops a swipe on the phone halfway)")
        site = self.tmp / "f18"
        shutil.copytree(ROOT / "status", site / "status", ignore=shutil.ignore_patterns("icons"))
        (site / ".status").mkdir()
        long_path = "/home/someone/HQ/workspace/HQ/roadmap.sync-conflict-20261012-223405-5Q2D7XN-and-a-long-tail.md"
        key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAwk8/o+vb4By0L7LRCWdxgnYI7o0qc/Lund+DC/zojPxxxxxxxxxxxxxxxx"
        rm = ROADMAP.read_text()
        need("\n## The queue\n" in rm and "\n## The schedule\n" in rm, "the roadmap has no queue or schedule to add to")
        rm = rm.replace("\n## The schedule\n", f"\n- Job 9001 · waiting · agreed 2026-10-13 12:00 · Merge {long_path} into the roadmap.\n\n## The schedule\n", 1)
        rm = rm.replace("\n## The schedule\n", f"\n## The schedule\n\n- Item 9001 · waiting · at 2026-12-31 23:59 · added 2026-10-13 12:00 · Look at {long_path}.\n", 1)
        rm += f"\n\n## Phase Z · Test\n\n| | Step | What you get | Model |\n|---|---|---|---|\n| ⬜ | Z1 A long word | The key `{key}` and the file `{long_path}` | Sonnet |\n"
        site_roadmap(site).write_text(rm)
        harness = r"""
<script>
(async () => {
  const wait = ms => new Promise(r => setTimeout(r, ms));
  for (let i = 0; i < 40 && !document.querySelector('section'); i++) await wait(250);
  await wait(1500);
  document.querySelectorAll('details').forEach(d => d.open = true);
  await wait(1000);
  const W = document.documentElement.clientWidth, out = [];
  out.push('page:' + document.documentElement.scrollWidth + '/' + W);
  const wide = [];
  for (const el of document.querySelectorAll('main *')) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.right > W + 1) wide.push(el.tagName + '.' + el.className + ' ' + Math.round(r.right) + ' ' + el.textContent.slice(0, 40).replace(/[|:]/g, ' '));
  }
  out.push('wide:' + wide.length + (wide.length ? ' ' + wide.slice(0, 3).join(' ; ') : ''));
  out.push('found:' + (document.body.textContent.includes('sync-conflict-20261012') ? 'yes' : 'no'));
  out.push('key:' + (document.body.textContent.includes('Lund+DC/zojPxxxx') ? 'yes' : 'no'));
  const pre = document.createElement('pre'); pre.id = 'f18'; pre.textContent = 'F18RESULT ' + out.join(' | ') + ' END';
  document.body.appendChild(pre);
})();
</script>
"""
        idx = site / "status/index.html"
        idx.write_text(idx.read_text().replace("</body>", harness + "</body>", 1))
        port = 4798
        env = {**os.environ, "HQ_STATUS_PORT": str(port), "HQ_FIX_DRY": "1"}
        proc = subprocess.Popen([node, str(site / "status/server.mjs"), "--quiet"], env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        seen = []
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                if http_get("/routines.json", base)[0] == 200:
                    break
                await asyncio.sleep(0.2)
            for w in (390, 320):
                # A phone: its own width as the page's width (the viewport meta), touch, three pixels to one.
                r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run",
                                                  *(["--no-sandbox"] if sys.platform != "darwin" else []),
                                                  f"--user-data-dir={self.tmp / ('f18-profile' + str(w))}",
                                                  f"--window-size={w},844", "--force-device-scale-factor=3", "--enable-viewport", "--touch-events=enabled",
                                                  "--virtual-time-budget=20000", "--dump-dom", base + "/"], timeout=120)
                m = re.search(r'<pre id="f18">F18RESULT (.*?) END</pre>', r.stdout)
                need(m, f"the page test didn't finish at {w}: {(r.stderr or r.stdout)[-300:]!r}")
                res = dict(part.split(":", 1) for part in m.group(1).split(" | "))
                say(f"   {w} wide: {m.group(1)[:300]}")
                need(res["found"] == "yes", f"at {w} the job with the long path isn't on the page")
                need(res["key"] == "yes", f"at {w} the roadmap note with the key isn't on the page")
                sw, cw = (int(x) for x in res["page"].split("/"))
                need(sw <= cw, f"at {w} the page is {sw} wide on a {cw} screen: it swipes sideways")
                need(res["wide"] == "0", f"at {w} something sticks out past the screen: {res['wide']}")
                seen.append(f"{w}: {sw}/{cw}")
        finally:
            proc.terminate()
            proc.wait(timeout=10)
        return "with a long path in a job and the schedule and a key in a roadmap note, every fold open: " + ", ".join(seen) + " wide, nothing sticks out; the redraw only scrolls back when it moved"

    async def flow74(self) -> str:
        """H100, no Claude: the coaching log keeps three hours. On a throwaway workspace: entries older than three hours
        move to the archive, newest first, word for word; the head and the open commitments stay whatever their age;
        a Quick call's text has only the last three hours; the routine runs the move on the main, never on the real
        log under a test."""
        import collections
        import datetime as _dt

        sys.path.insert(0, str(ROOT / "routine"))
        import log_cycle
        import quick_context

        ws = self.tmp / "h100" / "coaching"
        ws.mkdir(parents=True)
        now = _dt.datetime(2026, 10, 13, 12, 0)
        e = lambda t, what: f"## {t:%Y-%m-%d %H:%M} · {what}\n\n- note of {what}\n"
        log = ("# Coaching Log\n\nNewest first.\n\n" + e(now - _dt.timedelta(minutes=30), "fresh call") + "\n"
               + e(now - _dt.timedelta(hours=2, minutes=50), "two hours fifty") + "\n"
               + e(now - _dt.timedelta(hours=3, minutes=10), "three hours ten") + "\n"
               + "## Open commitments\n\n- an old promise, still open\n\n"
               + e(now - _dt.timedelta(days=3), "three days ago") + "\n## 2026-10-05 · setup\n\n- an entry with a date only\n")
        arch = log_cycle.ARCHIVE_HEAD + "\n" + e(now - _dt.timedelta(days=2), "already archived")
        (ws / "log.md").write_text(log)
        (ws / "log-archive.md").write_text(arch)
        text = quick_context.trim_log(log, now.date(), now=now)
        n = log_cycle.move(ws.parent, now=now)
        need(n == 3, f"{n} entries moved, not the three older than three hours")
        new_log, new_arch = (ws / "log.md").read_text(), (ws / "log-archive.md").read_text()
        for keep in ("# Coaching Log", "fresh call", "two hours fifty", "## Open commitments", "an old promise"):
            need(keep in new_log, f"the log lost {keep!r}")
        for gone in ("three hours ten", "three days ago", "a date only"):
            need(gone not in new_log and gone in new_arch, f"{gone!r} didn't move to the archive")
        heads = [l for l in new_arch.splitlines() if l.startswith("## ")]
        need(heads == sorted(heads, reverse=True) and len(heads) == 4, f"the archive isn't newest first: {heads}")
        before = collections.Counter(l for l in (log + arch).splitlines() if l.strip())
        after = collections.Counter(l for l in (new_log + new_arch).splitlines() if l.strip())
        need(before == after, "a line was lost, changed or doubled in the move")
        need(log_cycle.move(ws.parent, now=now) == 0, "a second look moved something again")
        if config.LIGHT_NOTES:
            need("fresh call" in text and "two hours fifty" in text and "an old promise" in text,
                 "a Quick call is missing the last three hours or the open commitments")
            need("three hours ten" not in text and "three days ago" not in text, "a Quick call has notes older than three hours")
        tick = (ROOT / "routine" / "tick.py").read_text()
        need("log_move()" in tick and "under_test()" in tick.split("def log_move")[1].split("def tick")[0],
             "the routine doesn't run the move, or would move the real log under a test")
        claude_md = (ROOT / "template" / "CLAUDE.md").read_text() + (ROOT / "template" / "where-things-go.md").read_text()
        need("three hours" in claude_md, "the template still says the log keeps two weeks")
        return (f"3 of 5 entries moved (older than {log_cycle.HOURS} hours), word for word, newest first; head and open "
                "commitments stayed; nothing moved twice; Quick has only the last three hours")

    # 77
    async def flow77(self) -> str:
        """H82, no Claude: her text may have bold and short lists for the chat; the voice never says the marks.
        Checked: both kinds of call are told so; the speech filter takes the marks out, also when they stream in
        pieces, and keeps numbers like 1.5 and 2026; the real call service driven by a stand-in speaks it plain
        while the transcript gets it with its line breaks; the saved call keeps them (<br>) and gives them back
        for the chat, and a continued call gets one line; the real call page in a headless browser shows bold
        and lists for her, and his lines and anything like HTML stay plain text."""
        from claude_llm import ClaudeSessionLLMService, SpeechFilter
        from pipecat.processors.aggregators.llm_context import LLMContext
        import transcript as tr
        rule = config.FORMAT_RULE
        need(rule in config.SYSTEM_PROMPT and rule in config.VOICE_RULES and "{format}" not in config.SYSTEM_PROMPT + config.VOICE_RULES,
             "a kind of call isn't told it may use bold and lists")
        need("No markdown" not in config.SYSTEM_PROMPT and "no markdown" not in config.VOICE_RULES, "a call is still told no markdown at all")

        def spoken(pieces):
            f = SpeechFilter()
            return "".join(f.feed(x) for x in pieces) + f.flush()
        text = "Three things:\n- **Bold** one\n- two\n\n1. three\n## Later\n1.5 hours in 2026, *really*."
        whole = spoken([text])
        need(whole == "Three things: Bold one. two.  three. Later. 1.5 hours in 2026, really.", f"the speech isn't plain: {whole!r}")
        for n in range(1, len(text)):
            need(spoken([text[:n], text[n:]]) == whole, f"cut at {n} the speech differs: {spoken([text[:n], text[n:]])!r}")
        need(spoken(["Fine, ", "done."]) == "Fine, done.", "a plain reply changed")
        # H116: a nested item and a bold lead-in are said plain too
        laid = spoken(["Plan:\n1. **Call** the bank\n   - ", "the bill\n\n2. Book"])
        need(not re.search(r"[*#]|(^|\s)-\s|\d\.\s", laid) and "Call the bank." in laid and "the bill." in laid, f"a laid-out reply isn't said plain: {laid!r}")

        class Stand:
            model = "stand-in"
            def __init__(self): self.replies = []
            async def start(self): pass
            async def stop(self): pass
            def cancel_turn(self): pass
            async def ask(self, text):
                for piece in self.replies.pop(0):
                    await asyncio.sleep(0.005)
                    yield piece

        folder = self.tmp / "h82calls"
        script = tr.CallTranscript(folder, model="stand-in")
        told: list[tuple[str, str]] = []
        script.on_line = lambda who, t: told.append((who, t))
        brain = Stand()
        llm = ClaudeSessionLLMService(brain, transcript=script)
        said: list[str] = []
        async def nothing(*a, **k): pass
        async def speak(t): said.append(t)
        llm.push_frame = nothing
        llm._push_llm_text = speak
        llm.start_processing_metrics = llm.stop_processing_metrics = nothing
        llm.start_ttfb_metrics = llm.stop_ttfb_metrics = nothing
        brain.replies.append(["Two ", "things:\n", "- ", "**Call", " the bank**\n", "- Book ", "the dentist"])
        await llm._process_context(LLMContext(messages=[{"role": "user", "content": "What's left?"}]))
        voice = "".join(said)
        need("*" not in voice and "- " not in voice and "Call the bank." in voice and voice.strip().endswith("Book the dentist"),
             f"the voice got the marks: {voice!r}")
        need(told and told[-1] == ("hq", "Two things:\n- **Call the bank**\n- Book the dentist"), f"the chat didn't get her text with its lines: {told[-1:]}")
        script.reply("Plain answer.")
        script.end()
        raw = script.path.read_text()
        need("**HQ:** Two things:<br>- **Call the bank**<br>- Book the dentist\n" in raw, "the saved call doesn't keep her lines")
        lines = tr.read_lines(script.path)
        hers = [ln["text"] for ln in lines if ln["who"] == "hq"]
        need(hers == ["Two things:\n- **Call the bank**\n- Book the dentist", "Plain answer."], f"the saved call gives back: {hers}")
        cont = tr.continue_from(script.path.stem, folder)
        need(cont and "You: Two things: - **Call the bank** - Book the dentist" in cont["text"] and "\n" not in cont["text"].split("\n")[-1],
             f"a continued call doesn't get her line as one line: {cont and cont['text']!r}")

        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const check = (name, ok, why) => out.push(name + ":" + (ok ? "ok" : "WRONG " + why));
  setState("live", "On the call");
  const send = (who, text) => onServerMessage({ data: JSON.stringify({ type: "hq-chat", who, text }) });
  send("hq", "Two things:\n- **Call the bank** today\n- Book *the dentist*\n\n1. first\n2. second");
  send("user", "Is **this** <b>bold</b>?");
  send("hq", "Plain <img src=x onerror=window.bad=1> line.");
  await wait(100);
  const msgs = [...chatLog.querySelectorAll(".msg")], h = msgs[0], me = msgs[1], plain = msgs[2];
  check("bold", h.querySelector("strong") && h.querySelector("strong").textContent === "Call the bank", h.innerHTML);
  check("italic", h.querySelector("em") && h.querySelector("em").textContent === "the dentist", h.innerHTML);
  check("ul", h.querySelectorAll("ul > li").length === 2, h.innerHTML);
  check("ol", h.querySelectorAll("ol > li").length === 2 && h.querySelector("ol").start === 1, h.innerHTML);
  check("no-marks", !h.textContent.includes("*") && !h.textContent.includes("- "), h.textContent);
  check("his-plain", me.textContent === "Is **this** <b>bold</b>?" && !me.querySelector("b,strong"), me.innerHTML);
  check("no-html", !plain.querySelector("img") && plain.textContent.includes("<img") && !window.bad, plain.innerHTML);
  // H116: laid out like a reply in an AI chat app
  send("hq", "Here's the plan:\n\n1. **The bank** first\n   - the bill\n   - the charger\n\n2. Then the dentist\n   before Friday\n---\n## Later\nThat's it.");
  await wait(100);
  const lay = [...chatLog.querySelectorAll(".msg")].pop();
  const ol = lay.querySelector(":scope > ol");
  check("one-ol", lay.querySelectorAll(":scope > ol").length === 1 && ol && ol.children.length === 2, lay.innerHTML);
  check("nested", ol && ol.children[0].querySelectorAll(":scope > ul > li").length === 2, lay.innerHTML);
  check("goes-on", ol && ol.children[1].textContent.includes("before Friday") && ol.children[1].querySelector("br"), lay.innerHTML);
  check("lead-bold", ol && ol.children[0].firstChild.tagName === "STRONG", lay.innerHTML);
  check("head-bold", [...lay.querySelectorAll(":scope > p > strong")].some(e => e.textContent === "Later") && !lay.textContent.includes("#") && !lay.textContent.includes("---"), lay.innerHTML);
  check("paras", lay.querySelectorAll(":scope > p").length === 3, lay.innerHTML);
  const cs = getComputedStyle(lay), lh = parseFloat(cs.lineHeight) / parseFloat(cs.fontSize);
  check("air", lh >= 1.45 && parseFloat(getComputedStyle(ol).marginTop) > 6, cs.lineHeight + " " + getComputedStyle(ol).marginTop);
  const pre = document.createElement("pre"); pre.id = "h82"; pre.textContent = "H82RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f = self.tmp / "h82.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run",
                                          *(["--no-sandbox"] if sys.platform != "darwin" else []),
                                          f"--user-data-dir={self.tmp / 'h82-profile'}", "--window-size=390,844",
                                          "--virtual-time-budget=20000", "--dump-dom", f.as_uri()], timeout=90)
        m = re.search(r'<pre id="h82">H82RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        say(f"   {m.group(1)}")
        need(all(part.endswith(":ok") for part in m.group(1).split(" | ")), f"the chat isn't formatted right: {m.group(1)}")
        return ("both calls may use bold and short lists; the voice gets them plain (also in pieces, numbers kept); "
                "the chat and the saved call keep her lines; the call page shows bold, italics and lists, his lines and HTML stay text; "
                "H116: laid out like an AI chat app (paragraphs, nested and numbered lists, lead-in bold, more air)")

    async def flow78(self) -> str:
        """H86, no Claude: the real call page in a headless browser. Before a call the screen is plain; on a call
        it takes a soft tint of her colour (Donna's, then Pepper's differs); two on the call (a three-way call,
        H79) cut the screen diagonally in both colours; after the call it's plain again. In the chat his lines
        are green and hers are in her own colour, also in a past call opened from the list (by its agent)."""
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        harness = r"""
<script>
(async () => {
  const out = [], wait = ms => new Promise(r => setTimeout(r, ms));
  const check = (name, ok, why) => out.push(name + ":" + (ok ? "ok" : "WRONG " + why));
  const root = document.documentElement, bodyBg = () => getComputedStyle(document.body).backgroundImage;
  const bg = el => getComputedStyle(el).backgroundColor;
  agent = "donna";
  setState("idle", "");
  check("idle-plain", !root.classList.contains("tinted") && bodyBg() === "none", bodyBg());
  setState("live", "On the call");
  const donna = bodyBg();
  check("live-tinted", root.classList.contains("tinted") && donna.includes("gradient"), donna);
  const parts = donna.match(/(rgb|color)\([^)]*\)/g) || [];
  check("one-colour", parts.length === 2 && parts[0] === parts[1], donna);
  const send = (who, text) => onServerMessage({ data: JSON.stringify({ type: "hq-chat", who, text }) });
  send("hq", "Hi, Donna here.");
  send("user", "Hi.");
  await wait(50);
  const [h, me] = chatLog.querySelectorAll(".msg");
  check("her-colour", h.style.getPropertyValue("--her") === AGENTS.donna.colour, h.style.cssText);
  check("me-green", /rgb\(34, 197, 94\)|rgb\(74, 222, 128\)/.test(bg(me)), bg(me));
  check("differ", bg(h) !== bg(me), bg(h) + " vs " + bg(me));
  setState("idle", "");
  check("after-plain", !root.classList.contains("tinted"), root.className);
  agent = "pepper"; setState("live", "On the call");
  check("pepper-differs", bodyBg() !== donna && bodyBg().includes("gradient"), bodyBg());
  paintTint(["donna", "pepper"]);
  const two = (bodyBg().match(/(rgb|color)\([^)]*\)/g) || []);
  check("two-colours", two.length === 2 && two[0] !== two[1], bodyBg());
  setState("idle", "");
  histEl.classList.add("open");
  const r = { agent: "Pepper", started: "today", lines: [{ who: "hq", text: "Pepper here." }, { who: "user", text: "Hi." }] };
  histGet = async () => r;
  await readCall("2026-10-13-1400");
  const hh = histLog.querySelector(".msg.hq");
  check("past-call", hh && hh.style.getPropertyValue("--her") === AGENTS.pepper.colour, hh ? hh.style.cssText : "none");
  const pre = document.createElement("pre"); pre.id = "h86"; pre.textContent = "H86RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f = self.tmp / "h86.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run",
                                          *(["--no-sandbox"] if sys.platform != "darwin" else []),
                                          f"--user-data-dir={self.tmp / 'h86-profile'}", "--window-size=390,844",
                                          "--virtual-time-budget=20000", "--dump-dom", f.as_uri()], timeout=90)
        m = re.search(r'<pre id="h86">H86RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        say(f"   {m.group(1)}")
        need(all(part.endswith(":ok") for part in m.group(1).split(" | ")), f"the colours aren't right: {m.group(1)}")
        return ("plain before and after a call; on a call a soft tint of her colour, two on the call cut diagonally; "
                "his lines green, hers in her colour, also in a past call")

    async def flow84(self) -> str:
        """H106, H112, no Claude: the mic and sound choice in Settings (and on a call), on the real call page in a headless browser with
        stand-in devices (AirPods, the phone's mic, a podcast mic; two outputs). Every input is listed after Default;
        a choice is remembered on this device and the call's getUserMedia asks for exactly that mic, also when the
        browser gave it a new id (found by its name); a mic that's gone falls back to the default and says so;
        Default asks for no mic in particular. The Sound row shows only where setSinkId exists, and her voice is
        sent to the chosen output. F24: the output the computer already plays on stays on the default path; where
        the page can't choose the sound it says so; in WebKit the old mic is let go before the new one opens; a mic
        the iPhone doesn't switch to is said plainly."""
        cands = sorted(Path.home().glob("Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-arm64/chrome-headless-shell"))
        cands += sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell"))
        chrome = str(cands[-1]) if cands else (shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        need(Path(chrome).exists(), "no headless browser found to run the call page in")
        page = (APP / "web/index.html").read_text()
        harness = r"""
<script>
(async () => {
  const out = [], check = (name, ok, why) => out.push(name + ":" + (ok ? "ok" : "WRONG " + why));
  try {
  localStorage.removeItem("hq-mic"); localStorage.removeItem("hq-out");
  let devs = [
    { kind: "audioinput", deviceId: "default", label: "Default - AirPods" },
    { kind: "audioinput", deviceId: "air", label: "AirPods" },
    { kind: "audioinput", deviceId: "phone", label: "iPhone Microphone" },
    { kind: "audioinput", deviceId: "pod", label: "Podcast Mic USB" },
    { kind: "audiooutput", deviceId: "default", label: "Default - AirPods", groupId: "g-air" },
    { kind: "audiooutput", deviceId: "airout", label: "AirPods", groupId: "g-air" },
    { kind: "audiooutput", deviceId: "spk", label: "Speaker", groupId: "g-spk" },
  ];
  const asked = [], order = [];
  let gone = false, stuck = null;
  Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: {
    enumerateDevices: async () => devs.map(d => ({ ...d })),
    getUserMedia: async c => { asked.push(JSON.stringify(c.audio)); order.push("open");
      if (gone && c.audio.deviceId) { const e = new Error("gone"); e.name = "OverconstrainedError"; throw e; }
      const from = stuck || (c.audio.deviceId ? c.audio.deviceId.exact : ""), dv = devs.find(d => d.deviceId === from && d.kind === "audioinput");
      const tr = { kind: "audio", enabled: true, stopped: false, from, label: dv ? dv.label : "Default - AirPods",
        getSettings() { return { deviceId: from || "default" }; }, stop() { this.stopped = true; order.push("stop " + from); } };
      return { getTracks: () => [tr], getAudioTracks: () => [tr] }; },
    addEventListener: () => {} } });
  const sinks = []; audioEl.setSinkId = async id => { sinks.push(id); };
  showSettings(true); await listDevices();
  const names = [...micSel.options].map(o => o.textContent);
  check("all-inputs", names.join(",") === "Default,AirPods,iPhone Microphone,Podcast Mic USB", names.join(","));
  check("default-first", micSel.value === "", micSel.value);
  let a = JSON.parse(JSON.stringify(micAudio()));
  check("default-no-device", !a.deviceId && a.echoCancellation === true, JSON.stringify(a));
  micSel.value = "phone"; micSel.dispatchEvent(new Event("change"));
  check("remembered", (localStorage.getItem("hq-mic") || "").includes("iPhone Microphone"), localStorage.getItem("hq-mic"));
  await openMic();
  check("call-uses-it", asked.at(-1).includes('"exact":"phone"'), asked.at(-1));
  devs = devs.map(d => d.deviceId === "phone" ? { ...d, deviceId: "phone2" } : d);
  await listDevices();
  check("kept-after-new-id", micSel.value === "phone2", micSel.value);
  await openMic();
  check("found-by-name", asked.at(-1).includes('"exact":"phone2"'), asked.at(-1));
  micSel.value = "pod"; micSel.dispatchEvent(new Event("change"));
  devs = devs.filter(d => d.deviceId !== "pod"); gone = true; await listDevices();
  check("gone-shown", [...micSel.options].some(o => o.textContent === "Podcast Mic USB (not here now)"), [...micSel.options].map(o => o.textContent).join(","));
  errEl.textContent = ""; await openMic();
  check("gone-falls-back", !asked.at(-1).includes("deviceId") && /default one/.test(errEl.textContent), asked.at(-1) + " " + errEl.textContent);
  micSel.value = ""; micSel.dispatchEvent(new Event("change"));
  check("back-to-default", localStorage.getItem("hq-mic") === null && !micAudio().deviceId, localStorage.getItem("hq-mic"));
  check("sound-row", outRow.hidden === !CAN_SINK, "CAN_SINK " + CAN_SINK + " hidden " + outRow.hidden);
  if (CAN_SINK) {
    outSel.value = "spk"; outSel.dispatchEvent(new Event("change"));
    check("sound-sent", sinks.at(-1) === "spk", sinks.join(","));
    outSel.value = ""; outSel.dispatchEvent(new Event("change"));
    check("sound-default", sinks.at(-1) === "", sinks.join(","));
    // F24: the output the computer already plays on (the AirPods) stays on the default path, so it isn't quieter.
    outSel.value = "airout"; outSel.dispatchEvent(new Event("change"));
    check("same-as-default-stays-default", sinks.at(-1) === "", sinks.join(","));
    outSel.value = ""; outSel.dispatchEvent(new Event("change"));
  }
  check("no-sink-row", noSinkRow.hidden === !outRow.hidden, "nosink " + noSinkRow.hidden + " out " + outRow.hidden);
  // H112: on a call the round mic button opens only the mic and sound rows, and a new mic takes over at once.
  gone = false; showSettings(false);
  check("no-devbtn-before", getComputedStyle(devBtn).display === "none", getComputedStyle(devBtn).display);
  const sent = [], sender = { track: null, replaceTrack: async t => { sent.push(t); sender.track = t; } };
  stream = await openMic(); sender.track = stream.getAudioTracks()[0];
  pc = { getSenders: () => [sender], close() {} };
  setState("live", "On the call");
  check("devbtn-on-call", getComputedStyle(devBtn).display !== "none", getComputedStyle(devBtn).display);
  // H144: the calendar stays next to it on a call; the two buttons are apart, and open one sheet at a time.
  const calB = document.getElementById("calbtn"), r1 = calB.getBoundingClientRect(), r2 = devBtn.getBoundingClientRect();
  check("calbtn-beside-mic", getComputedStyle(calB).display !== "none" && (r1.right <= r2.left + 1 || r2.right <= r1.left + 1), getComputedStyle(calB).display);
  devBtn.click();
  check("sheet-open", setEl.classList.contains("open") && setEl.classList.contains("incall"), setEl.className);
  const shown = r => r && getComputedStyle(r).display !== "none";
  check("only-mic-sound", shown(micSel.closest(".row")) && !shown(document.getElementById("free").closest(".row"))
    && !shown(soundBtn.closest(".row")) && !shown(document.getElementById("voices")), "rows shown wrong");
  const first = stream.getAudioTracks()[0];
  first.enabled = false;  // muted on the call
  micSel.value = "air"; micSel.dispatchEvent(new Event("change"));
  for (let i = 0; i < 50 && !sent.length; i++) await new Promise(r => setTimeout(r, 20));
  const now = sent.at(-1);
  check("switched-at-once", !!now && now.from === "air" && stream.getAudioTracks()[0] === now, now ? now.from : "nothing sent");
  check("old-mic-stopped", first.stopped === true, String(first.stopped));
  check("mute-kept", now && now.enabled === false, now ? String(now.enabled) : "-");
  check("same-call", pc && pc.getSenders()[0] === sender, "a new connection");
  // F24: WebKit (the iPhone, Safari, the Mac app) lets the old mic go first, else the new one never comes.
  ONE_MIC = true; IS_IOS = true; order.length = 0; sent.length = 0;
  await new Promise(r => setTimeout(r, 100)); await listDevices();  // the first switch's own look at the devices is done
  micSel.value = "phone2"; micSel.dispatchEvent(new Event("change"));
  for (let i = 0; i < 200 && stream.getAudioTracks()[0].from !== "phone2"; i++) await new Promise(r => setTimeout(r, 20));
  check("webkit-old-first", order[0] === "stop air" && order[1] === "open" && sent.at(-1) && sent.at(-1).from === "phone2", order.join(",") + " sent " + (sent.at(-1) && sent.at(-1).from) + " options " + [...micSel.options].map(o => o.textContent).join(","));
  check("webkit-switched-quietly", errEl.textContent === "", errEl.textContent);
  // The iPhone keeps the AirPods whatever the page asks: the page says so plainly.
  stuck = "air"; sent.length = 0;
  micSel.value = "phone2"; micSel.dispatchEvent(new Event("change"));
  for (let i = 0; i < 50 && !/kept/.test(errEl.textContent); i++) await new Promise(r => setTimeout(r, 20));
  check("iphone-says-kept", /The iPhone kept AirPods/.test(errEl.textContent) && /Control Center/.test(errEl.textContent), errEl.textContent);
  // F26: on the phone one row, Microphone and sound, and no Sound row; a saved output isn't used there.
  stuck = null; IS_PHONE = true; await listDevices();
  check("phone-one-row", micName.textContent === "Microphone and sound" && /follows/.test(micNote.textContent)
    && outRow.hidden && noSinkRow.hidden && micSel.getAttribute("aria-label") === "Microphone and sound",
    micName.textContent + " / " + micNote.textContent + " out " + outRow.hidden + " nosink " + noSinkRow.hidden);
  localStorage.setItem("hq-out", JSON.stringify({ id: "spk", label: "Speaker" }));
  check("phone-sound-follows", sinkFor().id === "", sinkFor().id);
  localStorage.removeItem("hq-out");
  IS_PHONE = false; await listDevices();
  check("computer-two-rows", micName.textContent === "Microphone" && !/follows/.test(micNote.textContent)
    && (outRow.hidden !== noSinkRow.hidden), micName.textContent + " out " + outRow.hidden + " nosink " + noSinkRow.hidden);
  ONE_MIC = false; IS_IOS = false; errEl.textContent = "";
  await listDevices();
  check("iphone-sound-note", noSinkRow.hidden || /computer/.test(noSinkNote.textContent), noSinkNote.textContent);
  calB.click(); await new Promise(r => setTimeout(r, 100));
  check("calendar-then-mic", calOpen() && !setEl.classList.contains("open") && stream && pc, "cal " + calOpen() + " mic sheet " + setEl.className);
  devBtn.click(); await new Promise(r => setTimeout(r, 100));
  check("mic-then-calendar", !calOpen() && setEl.classList.contains("open") && setEl.classList.contains("incall"), "cal " + calOpen() + " " + setEl.className);
  await listDevices(); sent.length = 0; ONE_MIC = false; IS_IOS = false;
  micSel.value = "air"; micSel.dispatchEvent(new Event("change"));
  for (let i = 0; i < 100 && !sent.length; i++) await new Promise(r => setTimeout(r, 20));
  check("switch-after-calendar", sent.length && sent.at(-1).from === "air", sent.length ? sent.at(-1).from : "nothing sent " + micSel.value);
  setState("live", "On the call");
  check("stays-open", setEl.classList.contains("open"), setEl.className);
  setState("idle", "Call ended");
  check("closes-after-call", !setEl.classList.contains("open") && getComputedStyle(devBtn).display === "none", setEl.className);
  pc = null; stream = null;
  devs = devs.map(d => ({ ...d, label: "" })); await listDevices();
  check("ask-names", !micAskRow.hidden, "hidden");
  } catch (e) { out.push("crash:WRONG " + e); }
  const pre = document.createElement("pre"); pre.id = "h106"; pre.textContent = "H106RESULT " + out.join(" | ") + " END";
  document.body.appendChild(pre);
})();
</script>
"""
        f = self.tmp / "h106.html"
        f.write_text(page.replace("</body>", harness + "</body>", 1))
        r = await asyncio.to_thread(run, [chrome, "--headless", "--disable-gpu", "--no-first-run",
                                          *(["--no-sandbox"] if sys.platform != "darwin" else []),
                                          f"--user-data-dir={self.tmp / 'h106-profile'}", "--window-size=390,844",
                                          "--virtual-time-budget=20000", "--dump-dom", f.as_uri()], timeout=90)
        m = re.search(r'<pre id="h106">H106RESULT (.*?) END</pre>', r.stdout)
        need(m, f"the page test didn't finish: {(r.stderr or r.stdout)[-300:]!r}")
        say(f"   {m.group(1)}")
        need(all(part.endswith(":ok") for part in m.group(1).split(" | ")), f"the mic or sound choice isn't right: {m.group(1)}")
        return ("every mic listed after Default, the choice remembered and used by the call, found again by its name, "
                "a gone mic falls back to the default; the sound choice only where the browser can, and used; "
                "on a call the mic button opens only mic and sound, a new mic takes over at once, muted stays muted; "
                "F24: the output already in use stays on the default path, WebKit lets the old mic go first, "
                "and a mic the iPhone won't switch to is said plainly; F26: on the phone one row, Microphone and sound, "
                "and the sound follows the mic, on the computer two rows")

# H56.3: happy flow 65's script, run with bash on this computer (and on a Linux machine with HQ_TEST_LINUX).
FLOW65_SCRIPT = r"""
# H56.3, happy flow 65: two throwaway HQs, A (laptop) and B (vps), on spare ports, nothing of the user's.
T="@BASE@/@TAG@"; PA=4796; PB=4797; SA=; SB=
fail() { echo "FAIL $*"; exit 1; }
cleanup() { [ -n "$SA" ] && kill "$SA" 2>/dev/null; [ -n "$SB" ] && kill "$SB" 2>/dev/null; sleep 0.3; rm -rf "$T"; }
trap cleanup EXIT
NOW=$(date +%s)
for X in A B; do
  mkdir -p "$T/$X/HQ" "$T/$X/state" && tar -xzf "$T/hq.tgz" -C "$T/$X/HQ" 2>/dev/null || fail "couldn't unpack HQ"
  cp -R "$T/$X/HQ/template" "$T/$X/HQ/workspace"
  # The throwaway's own watchdog line and heartbeat, so its routine never reaches for the real watchdog.
  echo "{\"at\": $NOW}" > "$T/$X/state/watchdog.json"; echo "$NOW" > "$T/$X/state/heartbeat"
done
ENVA="HQ_SUPPORT=$T/A/state HQ_STATUS_PORT=$PA HQ_PORT=7894 HQ_UNIT=@TAG@-a HQ_NO_PHONE=1 HQ_CALL_FIX=off HQ_ROLE_ONLINE=1 HQ_ROLE_RETRY=0.2"
ENVB="HQ_SUPPORT=$T/B/state HQ_STATUS_PORT=$PB HQ_PORT=7893 HQ_UNIT=@TAG@-b HQ_NO_PHONE=1 HQ_CALL_FIX=off HQ_ROLE_ONLINE=1 HQ_ROLE_RETRY=0.2"
NODE=$(command -v node || echo /opt/homebrew/bin/node)
ra() { (cd "$T/A/HQ" && env $ENVA python3 "$@"); }
rb() { (cd "$T/B/HQ" && env $ENVB python3 "$@"); }
starta() { (cd "$T/A/HQ" && exec env $ENVA "$NODE" status/server.mjs --quiet >> "$T/A/server.log" 2>&1) & SA=$!; }
startb() { (cd "$T/B/HQ" && exec env $ENVB "$NODE" status/server.mjs --quiet >> "$T/B/server.log" 2>&1) & SB=$!; }
up() { for i in $(seq 1 40); do curl -s -m 2 "http://127.0.0.1:$1/api/role" >/dev/null && return 0; sleep 0.25; done; return 1; }
acting() { python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('acting'))" "$1/state/role-state.json"; }
roadmap() { cat "$T/$1/HQ/workspace/HQ/roadmap.md"; }
lines() { cat "$T/$1/HQ/.status/routines.json" 2>/dev/null; }
starta; startb; up $PA && up $PB || fail "the throwaway status servers didn't start: $(tail -3 "$T/A/server.log")"

# Alone.
for f in ra rb; do $f routine/jobs.py off >/dev/null && $f routine/jobs.py mail-off >/dev/null || fail "couldn't switch the test's routine off"; done
[ "$(ra routine/role.py acting)" = main ] || fail "an HQ on its own isn't main"
ra routine/role.py tick | grep -q '"alone": true' || fail "an HQ on its own looked for another"
ra routine/jobs.py add "alone job" --kind other >/dev/null && roadmap A | grep -q "alone job" || fail "an HQ on its own can't add a job"
ra routine/tick.py || fail "the routine's look failed on an HQ on its own"
lines A | grep -q '"role"' && fail "an HQ on its own shows a main-or-backup line"
curl -s "http://127.0.0.1:$PA/api/role" | grep -q '"paired": *false' || fail "the status server doesn't answer the role"
echo "OK alone: main, looks for nothing, says nothing about it"

# Paired: B is chosen main.
rb routine/role.py setup "http://127.0.0.1:$PA" --name vps --takeover 4 >/dev/null
ra routine/role.py setup "http://127.0.0.1:$PB" --name laptop --takeover 4 >/dev/null
rb routine/role.py setup "http://127.0.0.1:$PA" --main here | grep -q "vps is the main one now" || fail "couldn't make vps main"
ra routine/role.py json | grep -q '"main": "vps"' || fail "the choice of main didn't reach the other HQ"
rb routine/tick.py; ra routine/tick.py
[ "$(acting "$T/B")" = main ] && [ "$(acting "$T/A")" = backup ] || fail "after the choice: B $(acting "$T/B"), A $(acting "$T/A")"
lines A | grep -q 'Backup (laptop); vps is the main one' || fail "the backup's line doesn't say so"
lines A | grep -q '"text": "Runs on the main one, vps; this HQ is the backup"' || fail "the backup's mail, jobs and scheduler lines don't say they run on the main"
lines B | grep -q '"text": "Main (vps)"' || fail "the main's line doesn't say so"
echo "OK the choice of main reaches the other one; the backup's mail check, jobs and scheduler say they run on the main"

# On the backup: a call's job and planned item go to the main; nothing is committed.
OUT=$(ra routine/jobs.py add "from a call on the backup" --kind other)
echo "$OUT" | grep -q "handed to the main one, vps" || fail "a job on the backup wasn't handed to the main: $OUT"
roadmap B | grep -q "from a call on the backup" || fail "the job didn't reach the main's queue"
roadmap A | grep -q "from a call on the backup" && fail "the backup wrote the job in its own queue too"
ra routine/schedule.py add "tomorrow 9:30" "planned on the backup" | grep -q "handed to the main" || fail "a planned item on the backup wasn't handed to the main"
roadmap B | grep -q "planned on the backup" || fail "the planned item didn't reach the main"
ra routine/jobs.py list >/dev/null || fail "the backup can't read its queue"
ra routine/gitlock.py commit "test" x | grep -q "backup now" || fail "the backup would commit"
(cd "$T/A/HQ/app" && env $ENVA python3 -c "import policy; assert policy.is_backup()") || fail "a call on the backup doesn't know it's the backup"
echo "OK on the backup a call's job and planned item go to the main; nothing is committed there"

# The main goes down: the backup keeps a request, takes over after the few minutes, runs it.
kill "$SB"; SB=; sleep 0.5
ra routine/tick.py
[ "$(acting "$T/A")" = backup ] || fail "the backup took over at once, without waiting"
ra routine/jobs.py add "while the main is down" --kind other | grep -q "kept here" || fail "a request on the backup wasn't kept while the main was down"
sleep 5
ra routine/tick.py
[ "$(acting "$T/A")" = main ] || fail "the backup didn't take over: $(ra routine/role.py)"
roadmap A | grep -q "while the main is down" || fail "the kept request didn't run once the backup took over"
grep -q '"key": "role"' "$T/A/HQ/.status/incidents.json" && grep -q "took over as main" "$T/A/HQ/.status/incidents.json" || fail "the takeover isn't in the incidents"
echo "OK with the main down the backup keeps the request, takes over after the few minutes, runs it, and notes it"

# The main is back: it waits as backup until the other has finished its job, then gets the role back.
startb; up $PB || fail "B's status server didn't come back"
rb routine/tick.py
[ "$(acting "$T/B")" = backup ] || fail "the returning main took the role while the other was still main"
ra routine/tick.py
echo '{"n": 9, "pid": null, "started": 0}' > "$T/A/HQ/scratch/routine/job.json"
python3 -c "import json,sys; p=sys.argv[1]; s=json.load(open(p)); s['peer_looks']=1; json.dump(s,open(p,'w'))" "$T/A/state/role-state.json"
(cd "$T/A/HQ" && env $ENVA python3 -c "import sys; sys.path.insert(0,'routine'); import role; r=role.tick(); assert r['acting']=='main' and r['handing_back'], r") \
  || fail "the backup handed back while its job still ran"
rm -f "$T/A/HQ/scratch/routine/job.json"
ra routine/tick.py
[ "$(acting "$T/A")" = backup ] || fail "the backup didn't hand the role back once its job was done"
rb routine/tick.py
[ "$(acting "$T/B")" = main ] || fail "the main didn't get its role back"
grep -q "handed the main role back" "$T/A/HQ/.status/incidents.json" || fail "handing back isn't in the incidents"
echo "OK the main back: it waits until the other has finished its job, then gets the role back"

# From a call to the laptop, with the server down: make the laptop main; the server takes that over when it's back.
kill "$SB"; SB=; sleep 0.5
ra routine/role.py main here | grep -q "can't be reached" || fail "making this one main with the other down didn't say so"
ra routine/tick.py
[ "$(acting "$T/A")" = main ] || fail "the laptop isn't main after being made main"
startb; up $PB || fail "B's status server didn't come back"
for i in 1 2 3; do rb routine/tick.py; ra routine/tick.py; done
rb routine/role.py json | grep -q '"main": "laptop"' || fail "the server didn't take the newer choice over"
[ "$(acting "$T/A")" = main ] && [ "$(acting "$T/B")" = backup ] || fail "after it was back: A $(acting "$T/A"), B $(acting "$T/B")"
echo "OK made main from a call with the other one down; the other takes that over when it's back"

# F19: from a call with both up, the switch is done at once, without waiting for the routines' minutes, and the
# reason never says the other one took over when it was simply main before.
OUT=$(ra routine/role.py main other)
echo "$OUT" | grep -q "the switch is done" || fail "making the other main with both up didn't switch at once: $OUT"
[ "$(acting "$T/B")" = main ] && [ "$(acting "$T/A")" = backup ] || fail "right after making vps main: A $(acting "$T/A"), B $(acting "$T/B")"
OUT=$(ra routine/role.py main here)
echo "$OUT" | grep -q "the switch is done" || fail "making this one main from the backup didn't switch at once: $OUT"
[ "$(acting "$T/A")" = main ] && [ "$(acting "$T/B")" = backup ] || fail "right after making the laptop main: A $(acting "$T/A"), B $(acting "$T/B")"
grep -q "on_main_pending" "$T/A/state/role-state.json" || fail "the new main won't line up its routines at its next look"
ra routine/tick.py; rb routine/tick.py
grep -q "on_main_pending" "$T/A/state/role-state.json" && fail "the new main's next look didn't line up its routines"
rb routine/role.py main here | grep -q "the switch is done" || fail "making vps main from vps didn't switch at once"
[ "$(acting "$T/B")" = main ] && [ "$(acting "$T/A")" = backup ] || fail "after vps made itself main: A $(acting "$T/A"), B $(acting "$T/B")"
# With a job running on the main, it waits for the job; once done, the hand-over is at once again.
echo '{"n": 9, "pid": null, "started": 0}' > "$T/B/HQ/scratch/routine/job.json"
OUT=$(ra routine/role.py main here)
echo "$OUT" | grep -q "as soon as job 9 is done" || fail "making this one main while the other runs a job didn't say it waits: $OUT"
[ "$(acting "$T/A")" = backup ] && [ "$(acting "$T/B")" = main ] || fail "the switch didn't wait for the job: A $(acting "$T/A"), B $(acting "$T/B")"
ra routine/tick.py
grep -q "took over while this one was away" "$T/A/state/role-state.json" && fail "the reason says vps took over, while it was simply main before"
grep -q "handing the main role over once job 9 is done" "$T/A/state/role-state.json" || fail "the reason doesn't say vps is handing over after its job"
rm -f "$T/B/HQ/scratch/routine/job.json"
rb routine/tick.py
[ "$(acting "$T/B")" = backup ] && [ "$(acting "$T/A")" = main ] || fail "once the job was done, the hand-over waited for the next look: A $(acting "$T/A"), B $(acting "$T/B")"
for i in 1 2; do ra routine/tick.py; rb routine/tick.py; done
[ "$(acting "$T/A")" = main ] && [ "$(acting "$T/B")" = backup ] || fail "the looks after the switch changed it: A $(acting "$T/A"), B $(acting "$T/B")"
echo "OK F19: from a call the switch is at once when nothing runs, after the job when one does, with the right reason"

# F23: time asleep never counts as the main being gone; the last check before a takeover; never two mains.
setst() { python3 -c "import json,sys,time; p=sys.argv[1]; s=json.load(open(p)); n=time.time()
for kv in sys.argv[2:]:
    k, v = kv.split('='); s[k] = n - float(v[3:]) if v.startswith('ago') else json.loads(v)
json.dump(s, open(p, 'w'))" "$1/state/role-state.json" "${@:2}"; }
rb routine/role.py main here | grep -q "the switch is done" || fail "couldn't make vps main again for F23"
[ "$(acting "$T/B")" = main ] && [ "$(acting "$T/A")" = backup ] || fail "before F23: A $(acting "$T/A"), B $(acting "$T/B")"
kill "$SB"; SB=; sleep 0.5
ra routine/tick.py
# Asleep for ten minutes: the last look was ten minutes ago, the main unreachable since then.
setst "$T/A" last_look=ago600 peer_lost_since=ago600 awake_since=ago600 lost_looks=9
ra routine/tick.py
[ "$(acting "$T/A")" = backup ] || fail "the backup took over after a ten-minute gap between its looks (asleep): $(ra routine/role.py)"
# Woke up a moment ago (the Mac's wake time), the last look just before the sleep: the minutes before the wake don't count.
setst "$T/A" last_look=ago30 peer_lost_since=ago600 awake_since=ago600 lost_looks=9
(cd "$T/A/HQ" && env $ENVA HQ_ROLE_WAKETIME=$(( $(date +%s) - 1 )) python3 routine/tick.py)
[ "$(acting "$T/A")" = backup ] || fail "the backup counted the time before its wake as the main being gone: $(ra routine/role.py)"
# The main answers again on the last check (busy with a job): no takeover.
setst "$T/A" last_look=ago30 peer_lost_since=ago600 awake_since=ago600 lost_looks=9
(cd "$T/A/HQ" && env $ENVA python3 -c "
import sys; sys.path.insert(0, 'routine'); import role
answers = iter([None, {'name': 'vps', 'acting': 'main', 'busy': 'job 7', 'main': 'vps'}])
role.peer_role = lambda c=None: next(answers, None)
r = role.tick(); assert r['acting'] == 'backup' and 'answered again (job 7)' in r['why'], r") \
  || fail "the backup took over although the main answered on the last check"
# Awake the whole time and still nothing: it does take over.
ra routine/tick.py; sleep 5; ra routine/tick.py
[ "$(acting "$T/A")" = main ] || fail "the backup didn't take over after being awake the whole takeover time: $(ra routine/role.py)"
echo "OK F23: time asleep doesn't count, a main that answers on the last check isn't taken over, a real outage is"
# The main is back and gives way; a shaky line (one look missed) doesn't make it main again next to the other.
startb; up $PB || fail "B's status server didn't come back"
rb routine/tick.py
[ "$(acting "$T/B")" = backup ] || fail "the returning main took the role while the other was main"
kill "$SA"; SA=; sleep 0.5
rb routine/tick.py
[ "$(acting "$T/B")" = backup ] || fail "one missed look made the returning main main again: two mains"
starta; up $PA || fail "A's status server didn't come back"
ra routine/tick.py
[ "$(acting "$T/A")" = main ] && grep -q '"handing_back": true' "$T/A/state/role-state.json" || fail "the one that took over didn't stop starting new things once the main was back"
kill "$SB"; SB=; sleep 0.5
ra routine/tick.py
grep -q '"handing_back": true' "$T/A/state/role-state.json" || fail "one missed look made the one that took over start new things again"
startb; up $PB || fail "B's status server didn't come back"
ra routine/tick.py
[ "$(acting "$T/A")" = backup ] && [ "$(acting "$T/B")" = main ] || fail "the hand-back after a shaky line: A $(acting "$T/A"), B $(acting "$T/B")"
for i in 1 2; do rb routine/tick.py; ra routine/tick.py; done
[ "$(acting "$T/A")" = backup ] && [ "$(acting "$T/B")" = main ] || fail "the looks after the hand-back changed it: A $(acting "$T/A"), B $(acting "$T/B")"
echo "OK F23: never two mains: the returning main stays the backup through a missed look, the other starts nothing new and hands back"

ra routine/role.py alone | grep -q "on its own" && [ "$(ra routine/role.py acting)" = main ] || fail "alone again didn't work"
echo "ALL OK"
"""


# H56.4: happy flow 66's script, run with bash on this computer (and on a Linux machine with HQ_TEST_LINUX).
FLOW66_SCRIPT = r"""
# H56.4, happy flow 66: two private Syncthings and two throwaway HQs, A (laptop) and B (vps), nothing of the user's.
T="@BASE@/@TAG@"; export PATH="$PATH:/opt/homebrew/bin:/usr/local/bin"
GA=8396; GB=8397; LA=22096; LB=22097; PIDS=""
fail() { echo "FAIL $*"; exit 1; }
cleanup() { for p in $PIDS; do kill "$p" 2>/dev/null; done; sleep 1; for p in $PIDS; do kill -9 "$p" 2>/dev/null; done; rm -rf "${T:?}"; }
trap cleanup EXIT
command -v syncthing >/dev/null || fail "Syncthing isn't installed here"
command -v git >/dev/null || fail "git isn't installed here"
NOW=$(date +%s)
git init -q --bare -b main "$T/origin.git" 2>/dev/null || fail "couldn't make the throwaway origin"
for X in A B; do
  mkdir -p "$T/$X/HQ" "$T/$X/state" "$T/$X/mem" && tar -xzf "$T/hq.tgz" -C "$T/$X/HQ" 2>/dev/null || fail "couldn't unpack HQ"
  echo "{\"at\": $NOW}" > "$T/$X/state/watchdog.json"; echo "$NOW" > "$T/$X/state/heartbeat"
done
cp -R "$T/A/HQ/template" "$T/A/HQ/workspace"
G="git -c user.name=hq-test -c user.email=hq-test@example.invalid"
(cd "$T/A/HQ/workspace" && $G init -q -b main && $G add -A && $G commit -q -m start && $G remote add origin "$T/origin.git" && $G push -q -u origin main) || fail "couldn't make A's workspace a repo"
$G clone -q "$T/origin.git" "$T/B/HQ/workspace" || fail "couldn't clone B's workspace"
for X in A B; do (cd "$T/$X/HQ/workspace" && git config user.name hq-test && git config user.email hq-test@example.invalid); done
WA="$T/A/HQ/workspace"; WB="$T/B/HQ/workspace"
ENVA="HQ_SUPPORT=$T/A/state HQ_SYNCTHING_HOME=$T/A/st HQ_STATUS_PORT=4795 HQ_PORT=7892 HQ_UNIT=@TAG@-a HQ_NO_PHONE=1 HQ_CALL_FIX=off"
ENVB="HQ_SUPPORT=$T/B/state HQ_SYNCTHING_HOME=$T/B/st HQ_STATUS_PORT=4794 HQ_PORT=7891 HQ_UNIT=@TAG@-b HQ_NO_PHONE=1 HQ_CALL_FIX=off"
ra() { (cd "$T/A/HQ" && env $ENVA python3 "$@"); }
rb() { (cd "$T/B/HQ" && env $ENVB python3 "$@"); }
st() { X=$1; shift; (cd "$T/$X/HQ" && env HQ_SYNCTHING_HOME="$T/$X/st" python3 -c "
import sys, json; sys.path.insert(0, 'routine'); import sync
a = sys.argv[1:]; r = sync.api(a[1], a[0], json.loads(a[2]) if len(a) > 2 else None); print(json.dumps(r))" "$@"); }
wait_for() { for i in $(seq 1 ${2:-60}); do eval "$1" && return 0; sleep 1; done; return 1; }

# Alone: nothing at all.
for f in ra rb; do $f routine/jobs.py off >/dev/null && $f routine/jobs.py mail-off >/dev/null || fail "couldn't switch the test's routine off"; done
[ "$(ra routine/sync.py tick)" = null ] || fail "an HQ with no sync set up did something"
ra routine/sync.py | grep -q "on its own" || fail "an HQ on its own doesn't say so"
echo "OK alone: no sync, no line"

# Two private Syncthings, only talking to each other on this computer.
for X in A B; do
  syncthing generate --home="$T/$X/st" >/dev/null 2>&1 || fail "couldn't make a throwaway Syncthing"
done
python3 - "$T/A/st/config.xml" $GA $LA "$T/B/st/config.xml" $GB $LB <<'PY'
import sys, xml.etree.ElementTree as ET
a = sys.argv[1:]
for p, gui, listen in (a[0:3], a[3:6]):
    t = ET.parse(p); r = t.getroot()
    r.find("gui").find("address").text = f"127.0.0.1:{gui}"
    o = r.find("options")
    for x in o.findall("listenAddress"):
        o.remove(x)
    ET.SubElement(o, "listenAddress").text = f"tcp://127.0.0.1:{listen}"
    for k, v in (("globalAnnounceEnabled", "false"), ("localAnnounceEnabled", "false"), ("relaysEnabled", "false"),
                 ("natEnabled", "false"), ("urAccepted", "-1"), ("autoUpgradeIntervalH", "0"),
                 ("startBrowser", "false"), ("crashReportingEnabled", "false")):
        x = o.find(k)
        if x is None:
            x = ET.SubElement(o, k)
        x.text = v
    for f in r.findall("folder"):
        r.remove(f)
    t.write(p)
PY
for X in A B; do
  STNODEFAULTFOLDER=1 STNOUPGRADE=1 syncthing serve --home="$T/$X/st" --no-browser > "$T/$X/st.log" 2>&1 &
  PIDS="$PIDS $!"
done
wait_for "st A GET /rest/system/status >/dev/null 2>&1 && st B GET /rest/system/status >/dev/null 2>&1" 40 || fail "the throwaway Syncthings didn't start: $(tail -3 "$T/A/st.log")"
IA=$(st A GET /rest/system/status | python3 -c "import json,sys; print(json.load(sys.stdin)['myID'])")
IB=$(st B GET /rest/system/status | python3 -c "import json,sys; print(json.load(sys.stdin)['myID'])")
st A PUT /rest/config/devices/$IB "{\"deviceID\": \"$IB\", \"name\": \"vps\", \"addresses\": [\"tcp://127.0.0.1:$LB\"]}" >/dev/null || fail "couldn't pair A"
st B PUT /rest/config/devices/$IA "{\"deviceID\": \"$IA\", \"name\": \"laptop\", \"addresses\": [\"tcp://127.0.0.1:$LA\"]}" >/dev/null || fail "couldn't pair B"
wait_for "st A GET /rest/system/connections | grep -q '\"connected\": true'" 60 || fail "the throwaway Syncthings didn't connect"
echo "OK two private Syncthings, paired only with each other"

# Setup on both.
OUT=$(ra routine/sync.py setup vps --memory "$T/A/mem") || fail "setup on A failed: $OUT"
rb routine/sync.py setup laptop --memory "$T/B/mem" >/dev/null || fail "setup on B failed"
grep -q "mp4" "$WA/.stignore" && grep -q "^.git$" "$WA/.stignore" || fail "the workspace's ignore list is missing video or git"
grep -q ".sync-conflict" "$WA/.git/info/exclude" || fail "Syncthing's own files aren't kept out of git"
st A GET /rest/config/folders/hq-workspace | grep -q '"maxConflicts": -1' || fail "conflict copies aren't all kept"
wait_for "ra routine/sync.py | grep -q 'In sync with vps'" 60 || fail "the two didn't get in sync: $(ra routine/sync.py)"
[ -z "$(cd "$WA" && git status --porcelain -- . ':!HQ/roadmap.md')" ] || fail "setting up the sync left changes in git: $(cd "$WA" && git status --porcelain | head -3)"
echo "OK set up on both: the workspace and the memory, video, audio and git left out"

# Both ways, within seconds.
echo "from the laptop" > "$WA/note-a.md"; echo "memory from the laptop" > "$T/A/mem/m.md"
S=$(date +%s)
wait_for "[ -f '$WB/note-a.md' ] && [ -f '$T/B/mem/m.md' ]" 30 || fail "a change on A didn't reach B"
D1=$(( $(date +%s) - S ))
echo "from the server" > "$WB/note-b.md"
S=$(date +%s)
wait_for "[ -f '$WA/note-b.md' ]" 30 || fail "a change on B didn't reach A"
D2=$(( $(date +%s) - S ))
echo "OK both ways: laptop to server in ${D1} s (memory too), server to laptop in ${D2} s"

# What never goes over.
echo video > "$WA/clip.MP4"; echo audio > "$WA/voice.m4a"; mkdir -p "$WA/.claude"; echo '{}' > "$WA/.claude/settings.local.json"
echo marker > "$WA/after.md"
wait_for "[ -f '$WB/after.md' ]" 30 || fail "a change after the video didn't reach B"
sleep 3
{ [ -f "$WB/clip.MP4" ] || [ -f "$WB/voice.m4a" ]; } && fail "video or audio went over"
[ -f "$WB/.claude/settings.local.json" ] && fail "this computer's own Claude settings went over"
[ "$(cd "$WA" && git rev-parse HEAD)" = "$(cd "$WB" && git rev-parse HEAD)" ] || fail "git's folder went over"
echo "OK video, audio, git's folder and this computer's own Claude settings stay where they are"

# The main commits what came over (and pushes it); the backup commits nothing.
BEFORE_B=$(cd "$WB" && git rev-parse HEAD)
rb routine/sync.py tick --backup >/dev/null
[ "$(cd "$WB" && git rev-parse HEAD)" = "$BEFORE_B" ] || fail "the backup committed"
OUT=$(ra routine/sync.py tick)
echo "$OUT" | grep -q '"committed": [1-9]' || fail "the main didn't commit what came over: $OUT"
(cd "$WA" && git log -1 --format=%s | grep -q "Sync: from vps") || fail "the commit doesn't say where it came from"
(cd "$WA" && git show --stat HEAD | grep -q "note-b.md") || fail "the commit doesn't have the file that came over"
(cd "$WA" && git show --stat HEAD | grep -q "note-a.md") && fail "the main committed its own file as if it came over"
[ "$(git --git-dir="$T/origin.git" rev-parse main)" = "$(cd "$WA" && git rev-parse HEAD)" ] || fail "the commit wasn't pushed"
echo "OK the main commits what came over, file by file, and pushes it; the backup commits nothing"

# Both change the same note at once: both kept, said, one merge job.
echo "same start" > "$WA/shared.md"
wait_for "[ -f '$WB/shared.md' ]" 30 || fail "shared.md didn't reach B"
sleep 2
st A PATCH /rest/config/devices/$IB '{"paused": true}' >/dev/null || fail "couldn't pause"
wait_for "! st A GET /rest/system/connections | grep -q '\"connected\": true'" 30 || fail "the pause didn't disconnect"
echo "the laptop's version" > "$WA/shared.md"; sleep 1; echo "the server's version" > "$WB/shared.md"
sleep 4
st A PATCH /rest/config/devices/$IB '{"paused": false}' >/dev/null
wait_for "ls '$WA' '$WB' | grep -q 'shared.sync-conflict-'" 60 || fail "no conflict copy came: $(ls "$WA" "$WB" | grep shared)"
wait_for "[ \$(ls '$WA' | grep -c 'shared') -ge 2 ]" 30 || fail "the conflict copy didn't reach A"
ra routine/sync.py conflicts | grep -q "shared.md" || fail "the conflict isn't listed"
OUT=$(ra routine/sync.py tick); echo "$OUT" | grep -q '"queued": \[[0-9]' || fail "no merge job was queued: $OUT"
grep -q "Sync conflict (H56.4)" "$WA/HQ/roadmap.md" || fail "the merge job isn't on the queue"
ra routine/sync.py tick | grep -q '"queued": \[\]' || fail "a second look queued it again"
[ "$(grep -c "Sync conflict (H56.4)" "$WA/HQ/roadmap.md")" = 1 ] || fail "the merge job was queued more than once"
grep -q 'conflict cop' "$T/A/HQ/.status/routines.json" || fail "the sync line doesn't say there's a conflict"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); i=[x for x in d['incidents'] if x['key']=='sync' and not x.get('back')]; assert i and i[0]['fixes'], d" "$T/A/HQ/.status/incidents.json" || fail "the conflict isn't in the incidents with its merge job"
wait_for "ls '$WB' | grep -q 'shared.sync-conflict-'" 30 || fail "the conflict copy didn't reach B"
rb routine/sync.py tick --backup | grep -q '"queued": \[\]' || fail "the backup queued a merge too"
grep -q 'the main one merges it' "$T/B/HQ/.status/routines.json" || fail "the backup's line doesn't say the main merges it"
echo "OK both changed the same note: both versions kept, the line and the incidents say so, one merge job queued on the main"

# The merge (here by hand, as the job would): one file with both, the copy gone; then green.
C=$(ls "$WA" | grep 'shared.sync-conflict-' | head -1)
{ echo "the laptop's version"; echo "the server's version"; } > "$WA/shared.md"; rm -f "${WA:?}/${C:?}"
wait_for "! ls '$WB' | grep -q 'shared.sync-conflict-' && grep -q \"server's\" '$WB/shared.md' && grep -q \"laptop's\" '$WB/shared.md'" 30 || fail "the merge didn't reach B"
wait_for "ra routine/sync.py tick | grep -q '\"state\": \"ok\"'" 30 || fail "the line didn't go green after the merge: $(ra routine/sync.py tick)"
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert not [x for x in d['incidents'] if x['key']=='sync' and not x.get('back')]" "$T/A/HQ/.status/incidents.json" || fail "the incident didn't close"
echo "OK once merged the copy is gone on both, the line is green and the incident closed"

# An HQ that becomes main lines its git up with GitHub, keeping the files.
cp "$WB/shared.md" "$T/keep.md"
[ "$(cd "$WB" && git rev-parse HEAD)" != "$(git --git-dir="$T/origin.git" rev-parse main)" ] || fail "B wasn't behind for the test"
OUT=$(rb routine/sync.py align 2>&1); [ "$(echo "$OUT" | tail -1)" = True ] || fail "align failed: $OUT"
[ "$(cd "$WB" && git rev-parse HEAD)" = "$(git --git-dir="$T/origin.git" rev-parse main)" ] || fail "align didn't line B up with GitHub"
cmp -s "$WB/shared.md" "$T/keep.md" && [ -f "$WB/note-a.md" ] || fail "align changed the files"
echo "OK an HQ that becomes main lines its git up with GitHub, keeping its files"

# The routine's own minute writes the line.
ra routine/tick.py >/dev/null 2>&1
python3 -c "import json,sys; s=json.load(open(sys.argv[1]))['sync']; assert s['state'] in ('ok','running'), s" "$T/A/HQ/.status/routines.json" || fail "the routine's minute didn't write the sync line"
echo "OK the routine's minute writes the sync line"

# Remove: no more sync, files stay.
ra routine/sync.py remove >/dev/null
st A GET /rest/config/folders | grep -q hq-workspace && fail "the folder is still in Syncthing"
{ [ -f "$WA/note-b.md" ] && [ "$(ra routine/sync.py tick)" = null ]; } || fail "remove lost files or the sync still runs"
echo "OK remove stops it and leaves the files"
echo "ALL OK"
"""

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
    22: ("Typing to HQ on a call: she answers out loud, chat gets both", True, "flow22"),
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
    36: ("Typing to HQ: the text field grows; Enter on phone and computer", False, "flow36"),
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
    51: ("H51: a call saves the usage it gets back, for the status page", False, "flow51"),
    52: ("H49: the space bar in the desktop app: tap mutes, hold talks, letting go sends", False, "flow52"),
    53: ("H57: a button for every past call: the list, one call read only", False, "flow53"),
    54: ("H61: estimated time to completion for each job and the whole list, learning from real times", False, "flow54"),
    55: ("F14: her voice off also silences the thinking tick, the talk sound and the click", False, "flow55"),
    56: ("H59: an update to a fake newer version: backup, local/ kept, note for Claude, waits for a call", False, "flow56"),
    57: ("H59: the version, the new-version bar, the changelog and the warning off a Mac, on every page", False, "flow57"),
    58: ("H60: continue an earlier call: Continue in Past calls, the greeting, the earlier call as context", True, "flow58"),
    59: ("H62: after a crash the job runs again, first in line, picking up where it left off", False, "flow59"),
    60: ("H65: a call reads HQ freely (files, logs, status page data); changes still ask; web lookups never ask (H103)", False, "flow60"),
    61: ("H56.1: the routine and the watchdog on Linux; the Mac as it was", False, "flow61"),
    62: ("H73: Moneypenny, coming soon: a locked card under Donna and Pepper, not on the picker", False, "flow62"),
    63: ("H56.2: job windows and the mail check on Linux, in tmux: a throwaway job and mail check", False, "flow63"),
    64: ("F16: the call page fits the screen before, during and after a call; no scrolling into white space", False, "flow64"),
    65: ("H56.3: main and backup: two throwaway HQs hand the main role back and forth; alone, an HQ is simply main", False, "flow65"),
    66: ("H56.4: the two-way sync: two private Syncthings, both ways, video left out, conflicts kept and merged, only the main commits", False, "flow66"),
    67: ("F17: a test never changes the real job list, schedule or status block, nor uses the real pairing", False, "flow67"),
    68: ("H72: the hidden Yes: hold the greyed-out Send, slide onto Yes, let go sends Yes", False, "flow68"),
    69: ("H76, H77: each agent her own character on calls, HQ's defaults a workspace can change", False, "flow69"),
    70: ("H75: she hangs up herself after his clear goodbye, once it has been heard; never on a passing okay", False, "flow70"),
    71: ("H87, H91: the three stop lines move every minute, or each stays fixed; switched from the page or a call", False, "flow71"),
    72: ("H83: which HQ this is (VPS, or Local · macOS), small under the name on the status page, the strip and the call page", False, "flow72"),
    73: ("H92: on a server the status page shows no Laptop section and no laptop lines under Routines", False, "flow73"),
    74: ("H100: the coaching log keeps three hours; older entries move to its archive, calls load only those", False, "flow74"),
    75: ("F18: the status page on the phone never gets wider than the screen; it only scrolls up and down", False, "flow75"),
    76: ("H78: his own calendar changes go without asking; with other people in it, or not looked at first, they don't", False, "flow76"),
    77: ("H82, H116: her text shows formatted in the call's chat, laid out like an AI chat app, while the voice stays plain", False, "flow77"),
    78: ("H86: the screen in the colour of who I'm calling; my lines green, hers in her colour", False, "flow78"),
    79: ("H88: heartbeats for both computers: this one up and online, the other answering; on both status pages", False, "flow79"),
    80: ("F9: a call left quiet stays connected: no idle timeout; a hang-up or a lost connection still ends it", False, "flow80"),
    81: ("H81: job estimates per computer, the other's scaled, and patterns from all the data", False, "flow81"),
    82: ("H104, H108: times on calls as 5 30 in the afternoon, no colon, no words, never half, quarter or o'clock", False, "flow82"),
    83: ("H105: the notes button: his quick notes kept in the workspace, cleared one by one; just text, the field grows (H117)", False, "flow83"),
    84: ("H106, H112, F26: the mic and sound choice in Settings: every mic listed, the chosen one used by the call, sound where the browser can; changed on a call at once; one row on the phone", False, "flow84"),
    85: ("H79, H121, H130: ask for another agent by name: she hands over, or brings her in on a three-way or four-way call and she says hi", False, "flow85"),
    86: ("H80: Donna's direct line: her texts on the lock screen, when she texts, texting her back", False, "flow86"),
    87: ("H98: the dog sits by its empty bowl and says Update! in green when a newer version is out", False, "flow87"),
    88: ("H113: a job held by the usage line carries on in its own chat, or in a fresh one with a note at which step", False, "flow88"),
    89: ("H118: which computer is main, at a glance: a pill next to the name on the status page, the strip and the call page", False, "flow89"),
    90: ("H120: the weather every three hours: sun, rain coming, a rainy day stays inside; quiet otherwise and at night", False, "flow90"),
    91: ("H101, H144, H153: my calendar inside HQ, read only from Google, read again right after a change, in time order; a tap on an appointment starts a call about it; it opens on a call too", False, "flow91"),
    92: ("H124: Donna texts first: pings for appointments he picked (a bell shows them), reminders, her own notes", False, "flow92"),
    93: ("H125: Donna's watch list: she keeps an eye out for a mail or the weather and texts when it comes", False, "flow93"),
    94: ("H135: the weather in the app: a widget on the main screen, a sheet with warnings (KNMI), UV and the next hours", False, "flow94"),
    95: ("H139: closing and opening the laptop's lid never leaves two mains: a real online check, the main that stayed stays", False, "flow95"),
    96: ("H137, H140: Modern is the only look: no Look switch, no saved choice, the round buttons in one dock", False, "flow96"),
    97: ("F31: a refused pull or push from a job shows up: the github incident, Donna texts at once, closed by the next one through", False, "flow97"),
    98: ("F32: a fresh install on an old release (a download, a shallow clone) sees the newer one and updates with one tap", False, "flow98"),
    99: ("H143: tick off or X the appointments; an X moves it to the Google calendar HQ Planning, undo moves it back; the week's look back", False, "flow99"),
    100: ("H146: a quick note on each appointment, one tap to type; a call and Donna's chat read it to put the calendar right", False, "flow100"),
    101: ("H152: after a crash or restart both computers come back in step: no every-minute pings write, locks stay home, needless conflict copies cleared, missed call transcripts committed", False, "flow101"),
}


async def main(args) -> bool:
    chosen = sorted(int(x) for x in args.only.split(",")) if args.only else sorted(FLOWS)
    bad = [n for n in chosen if n not in FLOWS]
    if bad:
        print(f"No such flow: {bad}. The flows are 1 to {len(FLOWS)}.")
        return False
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"== HQ happy flows · {stamp} · flows {chosen}" + (" · quick (no Claude turns)" if args.quick else ""))
    # F17: everything the flows start knows it's a test, and which roadmap and HQ memory are the real ones,
    # so jobs.py, schedule.py, set-status.py and role.py refuse them (a flow works on its own copies only).
    os.environ["HQ_UNDER_TEST"] = "1"
    os.environ.setdefault("HQ_REAL_ROADMAP", os.path.realpath(ROADMAP))
    sys.path.insert(0, str(ROOT / "routine"))
    import hqpaths as _hqp
    os.environ.setdefault("HQ_REAL_SUPPORT", _hqp.real_support())
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
    p = argparse.ArgumentParser(description="HQ happy flows (phase G)")
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
