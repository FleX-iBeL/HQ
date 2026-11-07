#!/usr/bin/env python3
"""The agents run themselves: the cycle runner (H298, piece 6, 29 October 2026).

What it's for: the agents run the show and escalate to the user when they need him; and no morning may start with the
usage burned by their running. The handbook in the user's folder says it in his own words; nothing of it is in HQ.

A cycle is a repeating planned item on the schedule (routine/schedule.py), tagged priority, that becomes a job of its
own kind (cycle-<agent>, step-<agent>; routine/estimate.py) and runs headless as the agent (her character, the
handbook's part one and her own section, her ledger, her briefing), in its own lane: the queue runs one thing at a
time, so a cycle never runs beside a team job; when they meet, the running job finishes first and the cycle goes
before the next waiting job (H99's priority tag). The wall, four layers, each enough on its own:

  1. before a run starts, the jobs' gate (the usage under each stop line, routine/tick.py) holds it like any job;
  2. during a run, a deterministic box in minutes and turns from the run's own stream (routine/runjob.py, piece 3);
  3. per agent per week, a share of the weekly limit (and a daily share, a third of it): a start past it is refused
     (the run is skipped, written as skipped), read from the measured cost of every run of hers, whichever way it ended;
  4. nothing of theirs runs outside her hours (8:00 to 22:00 by default) and nothing restarts itself: a boxed, held, stale
     or skipped step is never retried by the runner; a run that wouldn't fit its box before the hours end doesn't start;
     what waits at the hours' end is dropped to the morning. A restart or a takeover brings a session, a look or a
     review back once, as itself, through this same wall, and a step never.

The agents are the first to stop near the limit: their line is wall.AGENTS_UNDER points under the team's (tick.py).
The hook (routine/cyclehook.py) stops what does real damage, and lets her do her job: Donna's calendar writes go through
and are logged in her ledger. A mistake gets logged; repeating one is what reaches him. A text respects his Sleep block,
has a date, and goes out only while it's true (say, batch, later). The state of the runner (the steps, what's queued,
the caps) lives next to the ledgers in the workspace, so a takeover keeps it; it's read and written under one lock.

The bigger session writes a cycle plan into her ledger (`cycles.py plan AGENT JSON`): the few things, the let-go,
and the small steps, each with its goal, what done means, its named inputs, what it may do, when it runs, and what
makes it escalate. F86: a flagged planning row gets a short run of hers by itself (fix_rounds; the loop's state is in
routine/review.py): her step's box, her share, her hours, with its own kind "fix" so her planned steps keep their count. The runner schedules those steps as one-off priority items; a small step starts with only the core,
her section, the step and its inputs, and first the runner checks its inputs still hold (a to-do item, a planning
row, a mail line, a calendar block, a file) against what the plan saw: changed, the step is stale and never runs. The
tripwires are counted here, never judged by the agent (the same goal twice without done, a step boxed twice in a row,
a refused command or push, a check failing twice, an action outside her limits, a write to a shared file outside the
serialized place, for Moneypenny a Ready mark refused on its fields); each becomes one message on her own line, in
if-then shape, at most her texts a day, and the step waits. Orders he gives her on a call or in a text are written
in her ledger (`cycles.py order`) and picked up here. H308: she looks at her own list a few times a day inside her hours (looks_a_day,
three by default: morning, midday, evening); each look turns a new order into its step, inside her share, and the order
carries its item's label; one that doesn't fit waits for her next look and her ledger says so. Every week the routine computes her score (routine/pokes.py)
into her ledger. The settings are the workspace's HQ/agents/cycles.json (numbers; the template ships the defaults).

    python3 routine/cycles.py                         what runs, each agent's share used this week, what's planned
    python3 routine/cycles.py settings                the settings, per agent
    python3 routine/cycles.py set AGENT KEY VALUE     on|off, fix (F86's loop, on|off), weekly, daily, hours (08:00-17:00, or 18:00-08:00 through the night),
                                                      days (monday-friday), batches (12:00,16:30),
                                                      texts (tripwire texts a day), session_at, session_every,
                                                      session_minutes, session_turns, step_minutes, step_turns, steps_a_day, looks_a_day
    python3 routine/cycles.py order AGENT start|stop|standing "HIS WORDS" [--now]   an order from a call or a text
    python3 routine/cycles.py plan AGENT 'JSON'       the bigger session's cycle plan (her own run writes it)
    python3 routine/cycles.py done AGENT K "WHAT"     a small step says what came of it; failed AGENT K "WHY"; stale AGENT K "WHY"
    python3 routine/cycles.py ask AGENT "IF-THEN"     one question for him on her line, in if-then shape (once a day)
    python3 routine/cycles.py yes AGENT "HIS WORDS" [N]  his yes to a held calendar change, question N when he named it; several waiting and no N: his words go to her
    python3 routine/cycles.py no AGENT "HIS WORDS" [N]   his no: the held change is closed, a later yes can't open it; several waiting and no N: his words go to her
    python3 routine/cycles.py open AGENT N, close AGENT N, go AGENT N   a run reading his words opens question N, closes it on his no, or says go on held goal N
    python3 routine/cycles.py stopstep AGENT K "WHY"  a stop order's run stops her step K; droptext AGENT N drops a queued text; stopped AGENT "WHAT"
    python3 routine/cycles.py batch AGENT "TEXT" [--until WHEN]   a text for her next batch (the low-information diet); it has a date
    python3 routine/cycles.py text AGENT "TEXT"       a text on her line now (a run's own, inside the day's cap)
    python3 routine/cycles.py ledger AGENT            her ledger
    python3 routine/cycles.py score [AGENT]           the weekly score now (written to her ledger with --write)
    python3 routine/cycles.py waiting                 F194: the Must rows whose prepare is still off past their hour, as JSON lines
    python3 routine/cycles.py friday [--json]         the Friday screen: three lines per agent, her share
    python3 routine/cycles.py tick                    the routine's minute (tick.py runs it on the main)
"""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "app"))
import hqlock  # noqa: E402
import hqpaths  # noqa: E402
import ledger  # noqa: E402

FOLDER = Path(hqpaths.FOLDER)
SETTINGS_REL = "HQ/agents/cycles.json"
STATE_REL = "HQ/agents/cycles-state.json"  # harm 13: next to the ledgers, so a takeover has the steps, the caps and what's queued
OLD_STATE = Path(os.environ.get("HQ_CYCLES_OLD_STATE") or (ROOT / ".status" / "cycles-state.json"))  # where it was before: read until the new one is written, then moved aside
PY = sys.executable
FMT = "%Y-%m-%d %H:%M"
MARK_CYCLE = "Agent cycle: "
MARK_STEP = "Agent step: "
MARK_FIX = "Agent fix: "
FIX_AGENT = "moneypenny"  # F86: the loop is hers; the rows are hers to write
FIX_TURNS = 60  # F86: a round's turns, in her step's minutes, its price: at 20, 5 of 11 real rounds ran out, 3 with nothing written; 15 real ones at 40 took 8 to 35 but for two a hook fault held up, all under 3 minutes
PICKS_MOST = 3
QUESTIONS_MOST = 3
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
SHARED = ("HQ/roadmap.md", "challenges.md", "coaching/log.md", "inbox.md", "HQ/calendar.json", "HQ/sprint.json",
          "HQ/games.json", "HQ/coaching.json", "HQ/calendar-todo.json", "HQ/calendar-marks.json")
_REALLY_REFUSED = re.compile(r"^(?:HQ: refused|refused\b)|\bhook error\b|isn't ready", re.I)  # F86: a round's own reading is full of the word: a grep of the code, a row
STEP_GRACE = 60  # minutes a step may start late when no next step or his own "until" says otherwise [the fix round's pick]
ASKS_A_DAY = 3  # questions a day, like the plan's; past it the ledger keeps them for Friday [the fix round's pick]
LEAST_CHARGE = 0.1  # points a run nothing measured counts at the least: what a real session costs, 0.03 to 0.21 so far [the fix round's pick]
LOOKS_MOST = 12  # H308: looks at her own list a day, at the most
REPEAT_DAYS = 7  # a refusal, a goal or a failing run counts as a repeat within this many days
_STOP_WORDS = {"a", "an", "and", "any", "at", "be", "do", "dont", "for", "from", "her", "him", "his", "i", "in", "is", "it", "its", "me", "my", "no", "not", "of", "off", "on",
               "or", "our", "please", "so", "that", "the", "them", "then", "this", "to", "up", "us", "we", "with", "you", "your", "stop", "drop", "leave", "cancel", "quit", "go", "ahead", "yes", "ok", "okay", "try", "again", "once", "more"}
_tls = threading.local()


# -- settings ---------------------------------------------------------------------------------------------------------

def folder() -> Path:
    return Path(os.environ.get("HQ_CYCLES_FOLDER") or FOLDER)


def on(base: Path | None = None) -> bool:
    try:
        import features
        return features.is_on("agents_run", base or folder())
    except Exception:
        return False


DEFAULT_AGENT = {"on": True, "fix": False, "weekly_share": 2, "daily_share": 1, "hours": ["08:00", "22:00"], "days": list(DAYS), "batches": [], "tripwire_texts": 2,
                 "session": {"at": "09:00", "every": "day", "minutes": 10, "turns": 30, "useful_until": "12:00"},
                 "step": {"minutes": 3, "turns": 10, "most_a_day": 3}, "looks": [], "looks_a_day": 3}


def _template_settings() -> dict:
    try:
        return json.loads((ROOT / "template" / SETTINGS_REL).read_text(encoding="utf8"))
    except (OSError, ValueError):
        return {"agents": {}, "review": {"every": "first friday", "at": "09:00", "minutes": 20, "turns": 60}}


def settings(base: Path | None = None) -> dict:
    """The workspace's settings, with the template's defaults under them (an agent not named gets DEFAULT_AGENT)."""
    tpl = _template_settings()
    try:
        own = json.loads(((base or folder()) / SETTINGS_REL).read_text(encoding="utf8"))
    except (OSError, ValueError):
        own = {}
    out = {"agents": {}, "review": {**(tpl.get("review") or {}), **(own.get("review") or {})}}
    ids = list((tpl.get("agents") or {}).keys()) + [k for k in (own.get("agents") or {}) if k not in (tpl.get("agents") or {})]
    for aid in ids:
        a = {**DEFAULT_AGENT, **((tpl.get("agents") or {}).get(aid) or {})}
        o = (own.get("agents") or {}).get(aid) or {}
        a = {**a, **{k: v for k, v in o.items() if k not in ("session", "step")},
             "session": {**a["session"], **(o.get("session") or {})}, "step": {**a["step"], **(o.get("step") or {})}}
        out["agents"][aid] = a
    return out


def agent_settings(aid: str, base: Path | None = None) -> dict:
    s = settings(base)
    return s["agents"].get(aid) or {**DEFAULT_AGENT, "on": False}


def _save_settings(d: dict, base: Path | None = None) -> None:
    p = (base or folder()) / SETTINGS_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    os.replace(tmp, p)


SET_KEYS = ("on", "fix", "weekly", "daily", "hours", "days", "batches", "texts", "session_at", "session_every", "session_minutes",
            "session_turns", "session_until", "step_minutes", "step_turns", "steps_a_day", "looks_a_day", "own_calendars")


def set_setting(aid: str, key: str, value: str, base: Path | None = None) -> str:
    """One setting changed, from Settings or a call: the whole file written back with the defaults filled in."""
    aid = aid.strip().lower()
    d = settings(base)
    if aid not in d["agents"]:
        d["agents"][aid] = dict(DEFAULT_AGENT)
    a = d["agents"][aid]
    v = str(value).strip()
    key = key.strip().lower().replace("-", "_")
    if key in ("on", "fix"):
        a[key] = v.lower() in ("on", "true", "yes", "1")
    elif key in ("weekly", "weekly_share", "daily", "daily_share", "texts", "tripwire_texts", "steps_a_day",
                 "session_minutes", "session_turns", "step_minutes", "step_turns"):
        try:
            n = float(v)
        except ValueError:
            return f"{key} is a number."
        if n < 0 or (key.endswith("turns") and n < 1):
            return f"{key} can't be {v}."
        n = int(n) if n == int(n) else round(n, 2)
        if key in ("weekly", "weekly_share"):
            a["weekly_share"] = n
        elif key in ("daily", "daily_share"):
            a["daily_share"] = n
        elif key in ("texts", "tripwire_texts"):
            a["tripwire_texts"] = int(n)
        elif key == "steps_a_day":
            a["step"]["most_a_day"] = int(n)
        else:
            which, what = key.split("_")
            a[which][what] = n if what == "minutes" else int(n)
    elif key == "looks_a_day":  # H308: how often a day she looks at her own list; today's looks stay as they were, the new number counts from tomorrow
        if not re.fullmatch(r"\d{1,2}", v) or not 0 <= int(v) <= LOOKS_MOST:
            return f"looks_a_day is a whole number from 0 to {LOOKS_MOST}."
        a["looks_a_day"] = int(v)
    elif key == "hours":
        m = re.fullmatch(r"(\d{1,2}:\d\d)\s*(?:-|to)\s*(\d{1,2}:\d\d)", v)
        if not m:
            return "hours are from-to, like 08:00-22:00."
        lo, hi = m.group(1), m.group(2)
        if not (_is_time(lo) and _is_time(hi)) or _hhmm(lo) == _hhmm(hi):
            return "hours are from-to, like 08:00-22:00 (or 18:00-08:00, through the night)."
        if not _at_hour({"hours": [_hhmm(lo), _hhmm(hi)]}, a["session"]["at"]):
            return f"her session is at {a['session']['at']}, outside {_hhmm(lo)} to {_hhmm(hi)}: it would never run. Move it first."
        a["hours"] = [_hhmm(lo), _hhmm(hi)]
        if a["hours"] == ["00:00", "23:59"]:  # H340: round the clock is every day too
            a["days"] = list(DAYS)
    elif key == "days":  # H340: her working days, like monday-friday or monday,wednesday
        w = [x.strip().lower() for x in re.split(r"[,; ]+", v) if x.strip()]
        if len(w) == 1 and re.fullmatch(r"\w+-\w+", w[0]) and all(x in DAYS for x in w[0].split("-")):
            f_, t_ = (DAYS.index(x) for x in w[0].split("-"))
            w = DAYS[f_:t_ + 1] if f_ <= t_ else DAYS[f_:] + DAYS[:t_ + 1]
        if not w or not all(x in DAYS for x in w):
            return "days are weekdays, like monday-friday or monday,wednesday,friday."
        a["days"] = [x for x in DAYS if x in w]
    elif key == "batches":
        ts = [x.strip() for x in re.split(r"[,; ]+", v) if x.strip() and x.strip().lower() != "none"]
        if not all(_is_time(x) for x in ts):
            return "batches are times, like 12:00,17:00 (or none)."
        a["batches"] = [_hhmm(x) for x in ts]
    elif key in ("session_at",):
        if not _is_time(v):
            return "session_at is a time, like 08:30."
        lo, hi = a.get("hours") or ["08:00", "22:00"]
        if not _at_hour(a, _hhmm(v)):
            return f"session_at {_hhmm(v)} is outside her hours, {lo} to {hi}: it would never run. Change her hours first."
        a["session"]["at"] = _hhmm(v)
    elif key == "session_every":
        w = v.lower().rstrip("s")
        if w not in ("day",) + tuple(DAYS):
            return "session_every is day or a weekday."
        a["session"]["every"] = w
    elif key == "session_until":
        a["session"]["useful_until"] = v
    elif key == "own_calendars":  # besides his main calendar, the ones that are his (names or ids); on any other a change is a question first
        a["own_calendars"] = [x.strip() for x in v.split(",") if x.strip() and x.strip().lower() != "none"]
    else:
        return f"No setting called {key}. The settings: {', '.join(SET_KEYS)}."
    _save_settings(d, base)
    return f"{aid}: {key} is now {v}." + (" It counts from tomorrow; today's looks stay as they were." if key == "looks_a_day" else "")


def _hhmm(s: str) -> str:
    h, m = s.split(":")
    return f"{int(h):02d}:{int(m):02d}"


def _is_time(s: str) -> bool:
    m = re.fullmatch(r"(\d{1,2}):(\d\d)", s.strip())
    return bool(m) and int(m.group(1)) < 24 and int(m.group(2)) < 60


# -- the state (this computer's) --------------------------------------------------------------------------------------

def state_path() -> Path:
    return Path(os.environ.get("HQ_CYCLES_STATE") or (folder() / STATE_REL))


_lock = hqlock.For(lambda: state_path())


def _state() -> dict:
    p = state_path()
    for f in (p,) if os.environ.get("HQ_CYCLES_STATE") or p.exists() else (p, OLD_STATE):
        try:
            d = json.loads(f.read_text(encoding="utf8"))
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            pass
    return {}


def _save_state(d: dict) -> None:
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = hqlock.tmp(p)
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    os.replace(tmp, p)
    if not os.environ.get("HQ_CYCLES_STATE") and OLD_STATE.exists():  # the move is done: the old file is never read again
        os.replace(OLD_STATE, OLD_STATE.with_name(OLD_STATE.name + ".moved"))


@contextlib.contextmanager
def held():
    """The state, read, changed and written under one lock across processes (a run's text and the routine's minute both
    write it); nested, the same dict. Written only when it changed, and on the main only, by who calls this. What's to
    be texted goes out after the lock is let go (_say_now), since a push can take a while."""
    if getattr(_tls, "d", None) is not None:
        yield _tls.d
        return
    _tls.out = []
    try:
        with _lock:
            d = _tls.d = _state()
            was = json.dumps(d, sort_keys=True)
            try:
                yield d
            finally:
                _tls.d = None
                if json.dumps(d, sort_keys=True) != was:
                    _save_state(d)
    finally:
        out, _tls.out = _tls.out, []
        for a in out:
            send(*a)


def _agent_state(d: dict, aid: str) -> dict:
    st = d.setdefault("agents", {}).setdefault(aid, {})
    for k, v in (("goals", {}), ("boxed_streak", 0), ("texts", {}), ("own_texts", {}), ("batch", []), ("later", []), ("asked", {}), ("asks", {}), ("processed", []),
                 ("steps", {}), ("skipped", {}), ("held_out", {}), ("started", {}), ("run_start", {}), ("refusals", {}), ("back", {}), ("failing", {}),
                 ("holds", []), ("allowed", {}), ("stopping", {}), ("mine", {}), ("order_steps", {}), ("closed", {})):
        st.setdefault(k, v)
    return st


# -- the agents and their lines -----------------------------------------------------------------------------------------

def _agents(base: Path | None = None) -> list[dict]:
    import agents
    return [a for a in agents.load(base or folder()) if not a.get("hidden")]


def _agent(aid: str, base: Path | None = None) -> dict | None:
    return next((a for a in _agents(base) if a["id"] == aid), None)


def _line_env(aid: str, base: Path | None = None) -> dict:
    """The environment that puts direct_line on her line: Moneypenny's team line (pushed to the same phones as
    Donna's), Pepper's coaching line (no push), else Donna's direct line."""
    import pokes
    env = dict(os.environ)
    d = pokes.line_dir(aid, base)
    donna = os.environ.get("HQ_DIRECT_PUSH_DIR") or os.environ.get("HQ_DIRECT_DIR") or str((base or folder()) / "HQ" / "direct-line")
    env["HQ_DIRECT_DIR"] = str(d)
    env["HQ_DIRECT_AGENT"] = aid
    if aid == "moneypenny":
        env["HQ_DIRECT_TEAM"] = "1"
        env["HQ_DIRECT_PUSH_DIR"] = donna
    elif aid != "donna":
        env.pop("HQ_DIRECT_PUSH_DIR", None)
    return env


def send(aid: str, text: str, why: str = "cycle", base: Path | None = None) -> dict:
    """One text from her on her own line, as written (no Claude), pushed where her line pushes."""
    text = " ".join(str(text).split())
    if not text:
        return {}
    env = _line_env(aid, base)
    code = ("import sys, json; sys.path.insert(0, %r); import direct_line as D\n"
            "m = D.add('agent', sys.argv[1], sys.argv[2])\n"
            "try:\n    m['pushed'] = D.push(m['text']) if D.on() and D.written(m) else []\nexcept Exception as e:\n    m['pushed'] = [repr(e)]\n"
            "print(json.dumps(m))") % str(ROOT / "app")
    r = subprocess.run([PY, "-c", code, text, why], capture_output=True, text=True, env=env, timeout=120)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"error": (r.stderr or r.stdout)[-300:]}


# -- the planned items -------------------------------------------------------------------------------------------------

def cycle_text(aid: str, name: str) -> str:
    return f"{MARK_CYCLE}{aid}, {name}"


def fix_text(aid: str, label: str, mode: str, n: int) -> str:
    return f"{MARK_FIX}{aid}, {label} " + (f"round {n}" if mode == "fix" else "mark")


def step_text(aid: str, stamp: str, k: int, goal: str) -> str:
    return f"{MARK_STEP}{aid} #{k} ({stamp}): {' '.join(goal.split())[:90]}"


_JOB_HEAD = re.compile(r"^scheduled item (\d+), planned for [^:]*?(?:\d{1,2}:\d\d)?: ", re.I)
_CYCLE_RE = re.compile(r"^Agent cycle: ([a-z0-9][a-z0-9-]{0,30}), (.+?)\s*$")
_FIX_RE = re.compile(r"^Agent fix: ([a-z0-9][a-z0-9-]{0,30}), (\S+) (?:round (\d+)|mark)\s*$")
_STEP_RE = re.compile(r"^Agent step: ([a-z0-9][a-z0-9-]{0,30}) #(\d+) \(([^)]+)\): (.*)$")


def parse(text: str) -> dict | None:
    """What a job or item is, when it's an agent's: {"agent", "kind" (session, look, review, step), "name", "k",
    "stamp", "goal", "item"} or None."""
    t = " ".join((text or "").split())
    if t.startswith("Rerun of job") and "Then the job as it was: " in t:  # harm 1: whatever wrapped it, it's still hers
        t = t.split("Then the job as it was: ", 1)[1]
    m = _JOB_HEAD.match(t)
    item = int(m.group(1)) if m else None
    if m:
        t = t[m.end():]
    c = _CYCLE_RE.match(t)
    if c:
        name = c.group(2).strip()
        kind = "session" if name == "bigger session" else "review" if name == "monthly review" else "look"
        return {"agent": c.group(1), "kind": kind, "name": name, "item": item}
    f = _FIX_RE.match(t)
    if f:
        n = int(f.group(3) or 0)
        return {"agent": f.group(1), "kind": "fix", "label": f.group(2), "mode": "fix" if n else "mark", "round": n, "item": item,
                "name": f"{f.group(2)} round {n}" if n else f"{f.group(2)} mark"}
    s = _STEP_RE.match(t)
    if s:
        return {"agent": s.group(1), "kind": "step", "k": int(s.group(2)), "stamp": s.group(3), "goal": s.group(4), "item": item,
                "name": f"step {s.group(2)}"}
    return None


def is_cycle_job(job: dict) -> dict | None:
    return parse(job.get("text", "")) if isinstance(job, dict) else None


def _schedule(*args: str) -> tuple[int, str]:
    r = subprocess.run([PY, str(HERE / "schedule.py"), *args], capture_output=True, text=True, timeout=120,
                       env={**os.environ, "HQ_ROLE_HERE": "1"})
    return r.returncode, (r.stdout + r.stderr).strip()


def _jobs(*args: str) -> tuple[int, str]:
    r = subprocess.run([PY, str(HERE / "jobs.py"), *args], capture_output=True, text=True, timeout=120,
                       env={**os.environ, "HQ_ROLE_HERE": "1"})
    return r.returncode, (r.stdout + r.stderr).strip()


def _items() -> list[dict]:
    import jobs as q
    import schedule
    text, jobs_, _ = q.read()
    return [i for i in schedule.read(text) if parse(i["text"])] , [j for j in jobs_ if parse(j["text"])]


def wanted(now: dt.datetime | None = None, base: Path | None = None) -> list[dict]:
    """The repeating cycles every agent that's on should have planned: {"agent", "name", "at", "every", "text"}."""
    s = settings(base)
    ids = {a["id"] for a in _agents(base)}
    out = []
    for aid, a in s["agents"].items():
        if not a.get("on") or aid not in ids:
            continue
        se = a["session"]
        out.append({"agent": aid, "name": "bigger session", "at": se["at"], "every": se.get("every", "day"), "text": cycle_text(aid, "bigger session")})
        for lk in a.get("looks") or []:
            if lk.get("name") and lk.get("at"):
                out.append({"agent": aid, "name": lk["name"], "at": lk["at"], "every": lk.get("every", "day"), "text": cycle_text(aid, lk["name"])})
    return out


def _item_fits(item: dict, w: dict) -> bool:
    """The repeating item is where the settings say: its day and its time."""
    try:
        at = dt.datetime.strptime(item["at"], FMT)
    except ValueError:
        return False
    return item.get("every") == w["every"] and at.strftime("%H:%M") == w["at"] and (w["every"] == "day" or DAYS[at.weekday()] == w["every"])


def reconcile(now: dt.datetime | None = None, base: Path | None = None, log=None) -> list[str]:
    """The planned items follow the settings: with the feature off (or an agent off) her cycles are cancelled; on,
    every cycle she should have is planned as a repeating priority item, once."""
    now = now or dt.datetime.now()
    did = []
    items, jobs_ = _items()
    waiting = [i for i in items if i["state"] == "waiting"]
    want = wanted(now, base) if on(base) else []
    want_texts = {w["text"] for w in want}
    for i in waiting:
        p = parse(i["text"])
        if p["kind"] in ("session", "look") and i["text"] not in want_texts:
            code, out = _schedule("cancel", str(i["n"]))
            did.append(f"cancelled item {i['n']} ({p['agent']}, {p['name']}): {'no longer wanted' if on(base) else 'the feature is off'}")
        elif not on(base) or not agent_settings(p["agent"], base).get("on"):
            _schedule("cancel", str(i["n"]))
            did.append(f"cancelled item {i['n']} ({p['agent']}, {p['name']})")
    if not on(base):
        for j in jobs_:
            if j["state"] == "ready" or j["state"].startswith("held"):
                _jobs("stop", str(j["n"]))
                did.append(f"cancelled job {j['n']}: the feature is off")
    for w in want:
        mine = [i for i in waiting if i["text"] == w["text"]]
        rep = next((i for i in mine if i.get("every")), None)
        if mine and not rep:  # a one-off (planned again for the morning) stands in for it until it has gone
            continue
        if rep and _item_fits(rep, w):
            continue
        if rep:  # harm 11: a new time or day: the planned item follows the settings, within the minute
            _schedule("cancel", str(rep["n"]))
        when = f"{w['every']} {w['at']}" if w["every"] != "day" else w["at"]
        code, out = _schedule("add", when, w["text"], "--priority", "--every", w["every"], "--kind", f"cycle-{w['agent']}")
        did.append(f"planned {w['agent']}'s {w['name']}: {out.splitlines()[0][:120] if out else code}")
    if log:
        for x in did:
            log(f"cycles: {x}")
    return did


# -- hours, usefulness, shares ---------------------------------------------------------------------------------------------

def _t(hhmm: str) -> dt.time:
    h, m = hhmm.split(":")
    return dt.time(int(h), int(m))


def _hours(a: dict) -> tuple[dt.time, dt.time]:
    lo, hi = a.get("hours") or ["08:00", "22:00"]
    return _t(lo), _t(hi)


def _wraps(a: dict) -> bool:
    """H340: hours past midnight, like Moneypenny's 18:00 to 08:00: the night after a day is that day's."""
    lo, hi = _hours(a)
    return hi <= lo


def _at_hour(a: dict, hhmm: str) -> bool:
    """A time of day inside her hours, whatever the day."""
    lo, hi = _hours(a)
    t = _t(hhmm)
    return (t >= lo or t < hi) if _wraps(a) else lo <= t < hi


def _shift_day(a: dict, now: dt.datetime) -> dt.date:
    """The day the hours around now belong to: before 08:00 in hours that run from the evening, the day before."""
    return now.date() - dt.timedelta(days=1) if _wraps(a) and now.time() < _hours(a)[1] else now.date()


def _working_day(a: dict, day: dt.date) -> bool:
    return DAYS[day.weekday()] in (a.get("days") or DAYS)


def in_hours(a: dict, now: dt.datetime) -> bool:
    """H340: her hours on her working days (days, Monday to Friday by the template; nobody works at the weekend)."""
    return _at_hour(a, now.strftime("%H:%M")) and _working_day(a, _shift_day(a, now))


def _shift_end(a: dict, now: dt.datetime) -> dt.datetime:
    """When the hours that now is in (or the day's, outside them) end: the next morning for hours past midnight."""
    d = _shift_day(a, now)
    end = dt.datetime.combine(d, _hours(a)[1])
    return end + dt.timedelta(days=1) if _wraps(a) else end


def next_start(a: dict, now: dt.datetime) -> dt.datetime:
    """The start of her next hours from now (now itself inside them), on a working day."""
    if in_hours(a, now):
        return now
    lo = _hours(a)[0]
    for k in range(8):
        d = now.date() + dt.timedelta(days=k)
        at = dt.datetime.combine(d, lo)
        if at >= now.replace(second=0, microsecond=0) and _working_day(a, d):
            return at
    return dt.datetime.combine(now.date() + dt.timedelta(days=1), lo)


def useful_until(parsed: dict, a: dict, job_at: dt.datetime, now: dt.datetime) -> dt.datetime | None:
    """When a run is no longer worth running: the session's "still useful until" (a time today, or "friday 09:30"),
    a look's until its next one (its every), a step's until the day's hours end."""
    if parsed["kind"] == "session":
        u = str(a["session"].get("useful_until") or "")
        m = re.fullmatch(r"(?:(\w+) )?(\d{1,2}:\d\d)", u.strip().lower())
        if not m:
            return None
        day, t = m.group(1), _t(m.group(2))
        base = job_at.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        if day in DAYS:
            ahead = (DAYS.index(day) - job_at.weekday()) % 7
            base = base + dt.timedelta(days=ahead)
        elif base < job_at:
            base += dt.timedelta(days=1)
        return base
    if parsed["kind"] == "look":
        return job_at + dt.timedelta(hours=23) if any(lk.get("every", "day") == "day" for lk in a.get("looks") or [] if lk.get("name") == parsed["name"]) else job_at + dt.timedelta(days=6)
    if parsed["kind"] == "review":
        return job_at + dt.timedelta(days=1)
    # a step: what the plan says (until the next one, her own until); one from before that: a while after its time
    end = _shift_end(a, job_at)
    return end if parsed["kind"] == "fix" else min(end, job_at + dt.timedelta(minutes=STEP_GRACE))  # a round isn't tied to a time of day


def used(aid: str, since: float, kinds: tuple = ("cycle", "step")) -> float:
    """Points of the weekly limit her runs cost since `since`, from the measured cost of the finished jobs of her kinds."""
    try:
        import estimate
        hist = estimate.all_history()
    except Exception:
        return 0.0
    total = 0.0
    for h in hist:
        if (h.get("done") or 0) < since:
            continue
        if h.get("kind") not in {f"{k}-{aid}" for k in kinds}:
            continue
        c = h.get("cost") or {}
        total += float(c.get("weekly") or 0)
    return round(total, 2)


def shares(aid: str, now: dt.datetime | None = None, base: Path | None = None) -> dict:
    now = now or dt.datetime.now()
    a = agent_settings(aid, base)
    week = now - dt.timedelta(days=7)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return {"weekly_used": used(aid, week.timestamp()), "weekly_share": a.get("weekly_share", 0),
            "daily_used": used(aid, day.timestamp()), "daily_share": a.get("daily_share", 0)}


def _est_weekly(job: dict) -> float:
    try:
        import usagecost
        m, c = usagecost.job_cost(job["n"], job.get("text", ""), latest=True)
        return float(c.get("weekly") or 0)
    except Exception:
        return 0.0


def over_share(sh: dict, est: float) -> str | None:
    """Why a run of about est points doesn't fit her shares, in words, or None. One wall for the start and for a fix round's
    plan. A share of 0 is a wall with no room in it: nothing of hers starts (found on the server, 29 October 2026, where
    `set donna weekly 0` let every start through)."""
    if sh["weekly_share"] <= 0 or sh["weekly_used"] + est > sh["weekly_share"]:
        return f"over her weekly share ({sh['weekly_used']:g} of {sh['weekly_share']:g} points used, this run about {est:g})"
    if sh["daily_share"] <= 0 or sh["daily_used"] + est > sh["daily_share"]:
        return f"over her daily share ({sh['daily_used']:g} of {sh['daily_share']:g} points used today, this run about {est:g})"
    return None


def _minutes_left(a: dict, now: dt.datetime) -> float:
    return (_shift_end(a, now) - now.replace(second=0, microsecond=0)).total_seconds() / 60


def gatekeep(job: dict, now: dt.datetime | None = None, base: Path | None = None, log=None) -> str:
    """Before the routine starts a cycle job (tick.py, with the jobs' gate after it): "go", "wait" (before her hours;
    nothing else starts meanwhile, the queue is the lane) or "skipped" (cancelled on the queue, written in her ledger:
    held while it ran, outside her hours at the day's end, a box that doesn't fit before they end, past its useful-until,
    over her share, a step past the day's count, or the feature off)."""
    now = now or dt.datetime.now()
    p = parse(job.get("text", ""))
    if not p:
        return "go"
    settle(now, base, log)  # a run that just ended counts before the next one starts, whichever way it ended
    aid = p["agent"]
    a = agent_settings(aid, base)
    with held() as d:
        st = _agent_state(d, aid)
        job_at = _job_at(job, now)
        rec = st["steps"].get(_step_key(p)) if p["kind"] == "step" else None

        def skip(why: str, morning: bool = False, ran: bool = False, tomorrow: bool = False) -> str:
            if ran:  # it ran, and was held: what it used is hers, and the minute's ledger line says how it went
                _charge(job, now)
                st["held_out"][str(job["n"])] = why
            _jobs("stop", str(job["n"]))
            if p["kind"] == "fix":
                import review
                if not job.get("state", "").startswith("held"):  # F86: a round that never ran doesn't count; a held one ran
                    review.round_refund(p["label"], p["mode"])
                elif p["mode"] == "mark" and review.mark_ended(p["label"], f"her mark's run was held and then dropped: {why}"):  # a mark gets one run: never lost in silence
                    ledger.note(aid, f"{p['label']} on the sit-down list: passed by the review, not marked")
            ledger.entry(aid, f"{p['name']} skipped (job {job['n']})", [f"skipped: {why}"], now)
            if not ran:
                st["skipped"][str(job["n"])] = why
            if rec is not None and rec.get("stop") and not ran:  # his stop isn't lost and isn't silent: he's told, it runs when it can
                rec["state"] = "skipped"
                ledger.set_order(aid, rec["order"], "now", f"waits: {why}")
                say(aid, f"Your stop, \"{rec['spec'].get('words', '')}\", has to wait: {why}. It runs as soon as it can.", "cycle", now, base)
            elif rec is not None:
                rec["state"] = "skipped"
                _order_back(aid, rec, why, base)
                if rec.get("stop"):
                    st["stopping"].pop(str(rec.get("order")), None)
            if morning and p["kind"] in ("session", "review"):
                _again(aid, p, a, job_at, now, base, tomorrow)
            if log:
                log(f"cycles: job {job['n']} ({aid}, {p['name']}) skipped: {why}")
            return "skipped"

        stop_here = bool(rec and rec.get("stop"))
        if job.get("state", "").startswith("held"):  # harm 2: the handbook: a boxed or held step is never retried by the runner
            return skip("it was held while it ran, and a held run is never started again; the next bigger session decides", ran=True)
        if not on(base) or not a.get("on"):
            return skip("the agents running themselves is off" if not on(base) else "she's switched off")
        any_hour = bool((rec or {}).get("any_hour"))  # F174: a look at new work runs day or night; her share is the wall
        if not in_hours(a, now) and not any_hour:
            lo, hi = a.get("hours") or ["08:00", "22:00"]
            if next_start(a, now).date() != now.date():  # H340: her hours are over for today, or it's a day nobody works
                return skip(f"the day's hours end at {hi}; nothing of hers runs outside her hours", morning=True)
            return "wait"
        if st["stopping"] and not stop_here and p["kind"] != "fix":  # his stop comes first: it may be about this very run
            return "wait"
        u = _until(rec) if rec and rec.get("until") else useful_until(p, a, job_at, now)
        if u and now > u:
            return skip(f"too late to be useful (until {u:%A %H:%M})")
        bx = box(p, base)["minutes"]
        if a.get("hours", ["", "22:00"])[1] != "23:59" and _minutes_left(a, now) < bx and not any_hour:  # harm: the night: nothing of hers reaches past the hours' end
            return skip(f"its box of {bx:g} minutes doesn't fit before the day's hours end; nothing of hers runs at night", morning=True, tomorrow=True)
        why = over_share(shares(aid, now, base), _round_points(base) if p["kind"] == "fix" else _est_weekly(job))  # F86: a round's one price
        if why:
            return skip(why)
        if p["kind"] == "fix":
            import review
            if review.round_waits():  # F86: no round on a call or within five minutes of a change; it stays on the queue
                return "wait"
            if not review.round_wanted(p["label"], p["mode"]):
                return skip("the row no longer needs it (changed or settled since)")
        if p["kind"] == "step":
            today = now.strftime("%Y-%m-%d")
            n = st["started"].get(today, 0)
            if n >= int(a["step"].get("most_a_day") or 3) and not (rec or {}).get("order") and not (rec or {}).get("new_work"):  # his own "now" is his to give; it still counts
                return skip(f"the day's steps are used up ({n})")
            if rec is None:  # harm 16: no record of its plan here: nothing to check its inputs against, so it doesn't run
                return skip("its plan isn't on record on this computer, so its inputs can't be checked")
            why = stale(aid, p, d, base)
            if why:
                _jobs("stop", str(job["n"]))
                st["skipped"][str(job["n"])] = why
                ledger.entry(aid, f"step {p['k']} stale (job {job['n']})", [f"stale: {why}; not run"], now)
                rec["state"] = "stale"  # quiet: he may well have done the thing; the goal stays free for her next plan
                if log:
                    log(f"cycles: job {job['n']} ({aid}, step {p['k']}) stale: {why}")
                return "skipped"
    if p["kind"] == "look":  # H308: every look reads her own list first; a named look takes what's on it up to now
        _take_orders(aid, a, p["name"], now.strftime(FMT), now, base)
    return "go"


def started(job: dict, parsed: dict, now: dt.datetime | None = None) -> None:
    """The routine really started this run (tick.start): the day's step count, and when it began."""
    now = now or dt.datetime.now()
    with held() as d:
        st = _agent_state(d, parsed["agent"])
        st["run_start"] = {k: v for k, v in list(st["run_start"].items())[-20:]}
        st["run_start"][str(job["n"])] = now.strftime(FMT)
        if parsed["kind"] == "step":
            today = now.strftime("%Y-%m-%d")
            st["started"] = {today: st["started"].get(today, 0) + 1}
            rec = st["steps"].get(_step_key(parsed))
            if rec is not None:
                rec["state"], rec["started"] = "started", now.strftime(FMT)


def out_of_hours(job: dict, now: dt.datetime | None = None, base: Path | None = None) -> bool:
    """A running cycle past the hours' end (her hours changed, or a box's last moments): the routine ends it."""
    p = parse(job.get("text", ""))
    if not p:
        return False
    if p["kind"] == "step" and ((_state().get("agents") or {}).get(p["agent"], {}).get("steps") or {}).get(_step_key(p), {}).get("any_hour"):
        return False  # F174: a look at new work runs day or night
    return not in_hours(agent_settings(p["agent"], base), now or dt.datetime.now())


def _again(aid: str, p: dict, a: dict, job_at: dt.datetime, now: dt.datetime, base: Path | None, tomorrow: bool = False) -> bool:
    """A session, a look or a review comes back at her next hours, as itself, once it's still useful then. Tomorrow: not again
    today, where the same check would only send it round."""
    nxt = next_start(a, _shift_end(a, now) if tomorrow else now)
    u = useful_until(p, a, job_at, now)
    if not u or u <= nxt:
        return False
    _schedule("add", "now" if nxt == now else nxt.strftime(FMT), cycle_text(aid, p["name"]), "--priority", "--kind", f"cycle-{aid}")
    ledger.note(aid, f"planned again for {nxt:%A %H:%M}, inside its useful-until")
    return True


def _order_back(aid: str, rec: dict, why: str, base: Path | None = None) -> None:
    """His "now" that didn't get done is never lost: it's open again for her next session, and the ledger says why."""
    n = rec.get("order")
    if n:
        ledger.set_order(aid, n, "open", f"back for her next session: {why}")


def _charge(job: dict, now: dt.datetime) -> None:
    """Harm 3: every run counts against her share, whichever way it ended: done writes its own line; paused, killed, crashed
    and held get theirs here, from the same count (its own tokens, the readings), else at its estimate, never at nothing."""
    import estimate
    import jobs as q
    n, text = job["n"], job.get("text", "")
    measured = lambda h: float((h.get("cost") or {}).get("weekly") or 0) > 0  # noqa: E731  # a count of 0 is nothing measured
    if any(h.get("n") == n and measured(h) for h in estimate.history()):
        return
    rec = None
    try:
        with q.locked():
            if not any(h.get("n") == n for h in estimate.history()):
                rec = estimate.on_done(n, text)
    except Exception as e:
        print(f"(a run's cost couldn't be counted: {e!r})", file=sys.stderr)
    if rec and measured(rec):
        return
    est = max(_est_weekly(job), LEAST_CHARGE)
    with q.locked():
        estimate.fill_cost(n, text, {"five": est, "weekly": est}, now.timestamp())


def _job_at(job: dict, now: dt.datetime) -> dt.datetime:
    m = re.match(r"^Scheduled item \d+, planned for (\w+ \d{1,2} \w+), (\d{1,2}:\d\d): ", job.get("text", ""))
    if m:
        try:
            d = dt.datetime.strptime(f"{m.group(1)} {now.year}, {m.group(2)}", "%A %d %B %Y, %H:%M")
            if d > now + dt.timedelta(days=200):
                d = d.replace(year=now.year - 1)
            return d
        except ValueError:
            pass
    try:
        return dt.datetime.strptime(job.get("agreed", ""), FMT)
    except ValueError:
        return now


# -- the box ----------------------------------------------------------------------------------------------------------

def box(parsed: dict, base: Path | None = None) -> dict:
    a = agent_settings(parsed["agent"], base)
    if parsed["kind"] == "session":
        return {"minutes": a["session"]["minutes"], "turns": a["session"]["turns"]}
    if parsed["kind"] == "review":
        r = settings(base).get("review") or {}
        return {"minutes": r.get("minutes", 20), "turns": r.get("turns", 60)}
    if parsed["kind"] == "look":
        lk = next((x for x in a.get("looks") or [] if x.get("name") == parsed["name"]), {})
        return {"minutes": lk.get("minutes", a["step"]["minutes"]), "turns": lk.get("turns", a["step"]["turns"])}
    if parsed["kind"] == "fix":  # its price is her step's minutes (_round_points); turns cost nothing past those minutes
        return {"minutes": a["step"]["minutes"], "turns": max(FIX_TURNS, a["step"]["turns"])}
    return {"minutes": a["step"]["minutes"], "turns": a["step"]["turns"]}


def box_args(job: dict, parsed: dict, run_dir: str, base: Path | None = None) -> list[str]:
    b = box(parsed, base)
    return ["--max-minutes", str(b["minutes"]), "--max-turns", str(b["turns"]), "--agent", parsed["agent"], "--box-note",
            os.path.join(run_dir, f"job-{job['n']}.box.json")] + (["--round", f"{parsed['label']}:{parsed['mode']}"] if parsed["kind"] == "fix" else []) + _allow(parsed)


def _allow(parsed: dict) -> list:
    """His yes runs with exactly the one tool it opened, by permission flag, not past auto mode's own judgment: Claude Code refused a yes on a guest event as an unrequested commit."""
    if parsed["kind"] != "step":
        return []
    y = (_step_spec(parsed["agent"], parsed) or {}).get("yes")
    return ["--allow-tool", y["tool"]] if y else []


# -- the prompts -----------------------------------------------------------------------------------------------------------

def _library(aid: str, ctx: str) -> str:
    sp = ROOT / "routine" / "sprint.py"
    out = ["Read just in time: your ledger is below, your briefing one command away; open only what a step needs:",
           f"- one to-do item with its details: python3 \"{ROOT / 'app' / 'todo.py'}\" show \"a few words of it\" (the list one line each is in the briefing)",
           f"- one planning row, open or closed: python3 \"{sp}\" show LABEL; the open items: python3 \"{sp}\" open; the three mechanical fields of a row: python3 \"{sp}\" fields LABEL",
           f"- one layer of the map: python3 \"{ROOT / 'routine' / 'briefing.py'}\" layer N",
           "- never the planning file whole, never the map whole, never a call transcript whole (grep -n a word, sed -n a few lines)."]
    return "\n".join(out)


def _rules(aid: str, parsed: dict, a: dict, b: dict) -> str:
    cy = ROOT / "routine" / "cycles.py"
    kind = parsed["kind"]
    lines = [f"# This run is your own cycle: {parsed['name']} (H298)",
             f"Nobody is on the line. You run headless by yourself; what you write in your ledger and on your line is what reaches anyone. "
             f"Your box: {b['minutes']} minutes and {b['turns']} turns; past either the run is ended and what you wrote stays, so write as you go and "
             "never go round in circles. Decide inside your limits (your section: what you decide, what you ask) and write the decision with its source; "
             "what's outside them is one question for him in if-then shape, never an action.",
             f"- Your ledger: a line for a decision or what happened: python3 \"{cy}\" done {aid} K \"what came of it\" for a step K, or "
             f"python3 \"{ROOT / 'routine' / 'ledger.py'}\" {aid} note \"decision: …, source: …\" for anything else.",
             f"- One question for him, once, in if-then shape (your pick first, both branches): python3 \"{cy}\" ask {aid} \"If …, I'll …; if not, …\". "
             "The same question is never asked twice in a day.",
             f"- Went stale (what it was for has already happened, or its input no longer holds): python3 \"{cy}\" stale {aid} K \"why\", and end. That's no failure; the goal goes on.",
             "- Writes to a shared file (the planning, the to-do list, the log, the mail list, the calendar) only through HQ's own scripts "
             f"(todo.py, sprint.py, jobs.py, pings.py, python3 \"{ROOT / 'routine' / 'handover.py'}\" edit REL JSON for the log and the mail list), (each takes the file's lock). Your ledger and your line you write freely.",
             "- Never send mail (a draft at the most), never a calendar change with another person in it, never anything he must say yes to first, never a change to the handbook, "
             "your section, his vision, his rules or the settings: those are his (an if-then question instead). Never start another run, plan team work, or plan more than this run's plan.",
             "- A text reaches him only through cycles.py batch, ask or text: they wait for his sleep. Other files of the workspace aren't yours to write: your ledger, your notes and your line are."]
    if aid == "donna":
        lines.append("- His calendar is yours to keep: add, move and remove his own events in Google Calendar by yourself; HQ logs each one in your ledger with what and when, so write nothing extra. "
                     "An event you made yourself is yours at once. An event with guests, on someone else's calendar, or a whole series, HQ holds and asks him first: when a change comes back as held, that's done, leave it and go on.")
    if a.get("batches") and aid == "donna":
        lines.append(f"- A text that can wait: python3 \"{cy}\" batch {aid} \"…\" (it goes out at {' or '.join(a['batches'])}). "
                     "A queued text has a date: it goes out today or not at all, unless you add --until \"friday 12:15\", the moment it stops being true. What can't wait, the line lets through by itself.")
    return "\n".join(lines)


def _plan_shape(aid: str, a: dict, now: dt.datetime) -> str:
    cy = ROOT / "routine" / "cycles.py"
    lo, hi = a.get("hours") or ["08:00", "22:00"]
    return (f"Your cycle plan, the last thing this session does, in one command (JSON in single quotes):\n"
            f"python3 \"{cy}\" plan {aid} '{{\"picks\": [{{\"what\": \"…\", \"source\": \"his words of <date>, a rule, a row, the calendar\"}}], "
            f"\"let_go\": [\"…\"], \"steps\": [{{\"goal\": \"one look or one action\", \"done_means\": \"…\", \"inputs\": [{{\"kind\": \"todo\", \"words\": \"…\"}}, "
            f"{{\"kind\": \"row\", \"label\": \"H123\"}}, {{\"kind\": \"mail\", \"words\": \"…\"}}, {{\"kind\": \"calendar\", \"words\": \"…\"}}, {{\"kind\": \"file\", \"path\": \"…\"}}], "
            f"\"may\": \"what the step may do\", \"at\": \"HH:MM\", \"until\": \"HH:MM, when it's too late to be of use (leave it out: until your next step, an hour at the most)\", \"escalate_when\": \"…\"}}], \"questions\": [\"If …, …; if not, …\"], \"orders_done\": [1]}}'\n"
            f"At most {PICKS_MOST} picks, at most {a['step'].get('most_a_day', 3)} steps a day, a plan written earlier today included, each at a time today between {lo} and {hi} and after now ({now:%H:%M}), "
            "each with only the inputs it needs by name, and each input there now (the runner checks they still hold before the step runs; changed, the step is stale and doesn't run); "
            f"a step is one look or one action inside its box ({a['step']['minutes']} minutes, {a['step']['turns']} turns). What you let go you name, so it's a decision. "
            "orders_done lists the numbers of his orders this plan takes up. The command refuses a plan with more, or a step without its goal, done_means or time; then fix it and run it again.")


def prompt(job: dict, parsed: dict, base: Path | None = None, now: dt.datetime | None = None) -> str:
    """The run's prompt: her persona (character, the handbook, her section), the rules of a cycle, her ledger, her
    briefing, the open orders and what this run is for."""
    import agents
    import me as _me
    now = now or dt.datetime.now()
    aid = parsed["agent"]
    base = base or folder()
    ag = _agent(aid, base) or {"id": aid, "name": aid.capitalize(), "personality": "", "speciality": "", "context": "day"}
    user = _me.load(base)["name"] or "the user"
    a = agent_settings(aid, base)
    b = box(parsed, base)
    ctx = agents.context_of(ag)
    head = f"let's go. This is job {job['n']} from the queue: {ag['name']}'s own cycle, {parsed['name']} (H298), run headless as her.\n\n"
    parts = [head + agents.persona(ag, user).replace("on this call", "in this run").replace("call rules", "rules"),
             _rules(aid, parsed, a, b), _library(aid, ctx)]
    if parsed["kind"] in ("session", "review"):
        parts.append("Your ledger, a digest HQ computed (what was boxed, stale, skipped, escalated or corrected; your score is below):\n\n" + ledger.digest(aid, 10))
        orders = ledger.orders(aid, ("open", "now"))
        if orders:
            parts.append("His orders waiting for you (take each up in this plan, or say in your ledger why not):\n" +
                         "\n".join(f"{o['n']}. {o['kind']}: \"{o['words']}\" ({o['at']})" + (f" [{o['note']}]" if o.get("note") else "") for o in orders))
            if aid == FIX_AGENT:  # F105: the order's id goes on with the row
                parts.append(f"A row you write for one of them: python3 \"{ROOT / 'routine' / 'jobs.py'}\" write-row --order N \"THE ROW\", N its number: his request's record goes on under the row.")
        sc = ledger.scores(aid)
        if sc:
            parts.append("Your newest score (computed by HQ, not by you):\n" + "\n".join(f"- {k}: {v}" for k, v in sc[-1][1].items() if k != "week"))
        parts.append(_briefing(ctx, base))
        if parsed["kind"] == "session":
            parts.append(_plan_shape(aid, a, now))
        else:
            parts.append("Your whole month (every dated section of your ledger of the last 31 days, oldest first; the scores HQ computed are the "
                         "'score, week' ones):\n\n" + _month_words(aid, now))
            parts.append(_review_shape(aid))
    elif parsed["kind"] == "look":
        lk = next((x for x in a.get("looks") or [] if x.get("name") == parsed["name"]), {})
        parts.append(f"This look: {lk.get('what', parsed['name'])}\nThe newest cycle plan in your ledger, for what the week's or day's focus is:\n"
                     + (json.dumps(ledger.plan(aid)[1], ensure_ascii=False)[:4000] if ledger.plan(aid)[1] else "(no plan yet)"))
        parts.append(_briefing(ctx, base))
        parts.append(f"End with one line in your ledger: python3 \"{ROOT / 'routine' / 'ledger.py'}\" {aid} note \"{parsed['name']}: what you saw and did\".")
    elif parsed["kind"] == "fix":
        parts.append(_fix_words(aid, parsed))
    else:
        spec = _step_spec(aid, parsed)
        parts.append(_step_words(aid, parsed, spec, base))
    return "\n\n".join(p for p in parts if p) + "\n"


MONTH_MOST = 60_000  # characters of the month's ledger in a review's prompt


def _month_words(aid: str, now: dt.datetime) -> str:
    secs = ledger.recent(aid, 31, now)
    if not secs:
        return "(nothing in the last 31 days)"
    t = "\n\n".join(f"## {s['title']}\n{s['body']}" for s in secs).strip()
    return t if len(t) <= MONTH_MOST else "(the oldest part left out for room)\n\n" + t[-MONTH_MOST:]


def _briefing(ctx: str, base: Path) -> str:
    """F99: a run starts without his life in its first prompt: the briefing is one command away, by path."""
    which = ctx if ctx in ("day", "coach", "build") else "day"
    return (f"Your briefing isn't in this prompt on purpose (F99). Read it first, once: HQ_WORKSPACE={json.dumps(str(base))} "
            f"python3 \"{HERE / 'briefing.py'}\" fresh {which}")


def _review_shape(aid: str) -> str:
    cy = ROOT / "routine" / "cycles.py"
    return ("This is your monthly review (the book's questions on your own ledger, the whole month of it below the last cycles): which 20% of "
            "what you did moved your score; which 20% caused the pokes and the corrections; what you do by hand every cycle that should be a "
            "routine (a row for the planning, never something you build); which boxes were too loose or too tight; what in your own section should "
            "change. Bring it as one short proposal, three parts: drop these, automate these, change these lines in my section. It changes nothing by "
            f"itself: he says yes or no. Write it with python3 \"{cy}\" proposal {aid} \"…\" (one command, plain words, no headings), which puts it in your "
            "ledger and on your line. Nothing else is written or changed in this run.")


# -- the plan, the steps, their inputs --------------------------------------------------------------------------------------

def _step_key(parsed: dict) -> str:
    return f"{parsed['agent']}|{parsed['stamp']}|{parsed['k']}"


def _step_spec(aid: str, parsed: dict) -> dict:
    d = _state()
    return (_agent_state(d, aid)["steps"].get(_step_key(parsed)) or {}).get("spec") or {"goal": parsed.get("goal", ""), "inputs": []}


def resolve(inp: dict, base: Path | None = None) -> str:
    """What a named input is right now, as text (its fingerprint is what the staleness check compares)."""
    base = base or folder()
    kind = str(inp.get("kind", "")).lower()
    words = " ".join(str(inp.get("words", "")).split()).lower()
    try:
        if kind == "todo":
            import todo
            d = todo.read(base / "challenges.md")
            hits = [it for l in d.get("lists", []) for it in l["items"] if words and words in it["title"].lower()]
            return "\n".join(f"{it['title']} | {it.get('status', '')} | {it.get('deadline', '')} | {it.get('notes', '')[:200]}" for it in hits[:5]) or "(no such item)"
        if kind == "row":
            import sprint
            r = sprint.row_of(str(inp.get("label", "")).upper())
            return r["line"] if r else "(no such row)"
        if kind == "mail":
            text = (base / "inbox.md").read_text(encoding="utf8")
            hits = [l for l in text.splitlines() if l.startswith("- ") and words and words in l.lower()]
            return "\n".join(hits[:5]) or "(no such mail line)"
        if kind == "calendar":
            s = json.loads((base / "HQ" / "calendar.json").read_text(encoding="utf8"))
            hits = [e for e in s.get("events") or [] if words and words in str(e.get("title", "")).lower()]
            return "\n".join(f"{e.get('start')} {e.get('end', '')} {e.get('title')} {e.get('where', '')}" for e in hits[:5]) or "(no such block)"
        if kind == "file":
            p = str(inp.get("path", ""))
            path = (base / p) if not os.path.isabs(p) else Path(p)
            if ".." in p.split("/") or not path.exists() or not str(path.resolve()).startswith(str(Path(base).resolve()) + os.sep):
                return "(no such file)"
            t = path.read_text(encoding="utf8", errors="replace")
            m = re.fullmatch(r"(\d+)-(\d+)", str(inp.get("lines", "")))
            if m:
                ls = t.splitlines()
                t = "\n".join(ls[int(m.group(1)) - 1:int(m.group(2))])
            return t[:20000]
    except Exception as e:
        return f"(couldn't read: {e!r})"
    return "(an input of a kind the runner doesn't know)"


def _fp(text: str) -> str:
    return hashlib.sha1(" ".join(text.split()).encode("utf8", "replace")).hexdigest()[:16]


def stale(aid: str, parsed: dict, d: dict | None = None, base: Path | None = None) -> str | None:
    """Why the step is stale (an input changed since the plan saw it, or one it had is gone), or None."""
    d = d or _state()
    rec = _agent_state(d, aid)["steps"].get(_step_key(parsed))
    if not rec:
        return None
    return _changed(rec.get("spec", {}).get("inputs") or [], rec.get("fps") or [], base)


def _changed(inputs: list, fps: list, base: Path | None = None) -> str | None:
    for inp, fp in zip(inputs, fps):
        if _fp(resolve(inp, base)) != fp:
            return f"its input changed since the plan ({inp.get('kind')} {inp.get('label') or inp.get('words') or inp.get('path') or ''})".strip()
    return None


def _until(rec: dict) -> dt.datetime | None:
    try:
        return dt.datetime.strptime(rec["until"], FMT)
    except (KeyError, ValueError):
        return None


def _stop_words(aid: str, parsed: dict, spec: dict) -> str:
    """His stop order, in his words, with all she has planned."""
    cy = ROOT / "routine" / "cycles.py"
    steps = planned_steps(aid)
    st_ = _agent_state(_state(), aid)
    texts = st_["batch"] + st_["later"]
    out = [f"This step is one order of his, in his own words: \"{spec.get('words', '')}\"", "What you have planned, all of it:"]
    out += [f"- step {s['k']} ({s['at']}): {s['goal']}" for s in steps] or ["- no steps planned"]
    out += [f"- queued text {i}: {e['text'][:200]}" for i, e in enumerate(texts, 1)]
    out += ["Work out what he means, and stop that. A step: python3 \"{c}\" stopstep {a} K \"why\". A queued text: python3 \"{c}\" droptext {a} N.".format(c=cy, a=aid),
            "Then tell him, one short plain line, what you stopped: python3 \"{c}\" stopped {a} \"I stopped ...\". That's your last act.".format(c=cy, a=aid),
            "If nothing here is what he means, or you're not sure which: never say nothing was cancelled. Ask, and that's your last act: python3 \"{c}\" ask {a} \"If you mean ..., I'll stop that; if not, ...\".".format(c=cy, a=aid),
            "Your next plans leave it out by themselves. If it was a reminder of his, pings.py is its way out. This run does nothing else."]
    return "\n".join(out)


def _answer_words(aid: str, parsed: dict, spec: dict) -> str:
    """His words, and what waits for his word."""
    cy = ROOT / "routine" / "cycles.py"
    st_ = _agent_state(_state(), aid)
    out = [f"This step is one thing he said, in his own words: \"{spec.get('words', '')}\"", "What's waiting for his word, all of it:"]
    out += [f"- question {h['n']}: {h['what']} ({h['why']})" for h in st_["holds"]]
    out += [f"- goal {i}: {g} (tried before without getting done; you told him you'd try once more if he said go)" for i, g in enumerate(spec.get("goals") or [], 1)]
    out += [f"Work out which one his words are for. He talks loosely: yeah, sure, go for it, sounds good, try it again all mean yes to something; nah, forget it, leave it, not that one mean no. A yes to a question: python3 \"{cy}\" open {aid} N. A no to a question: python3 \"{cy}\" close {aid} N, nothing goes out and it's closed, also when the question was to remove something and he says forget it: words that open with no are a no. A go on a goal: python3 \"{cy}\" go {aid} N.",
            f"If they could be for more than one and it isn't clear which: open nothing, ask, with the numbers and titles: python3 \"{cy}\" ask {aid} \"Which one do you mean: ...? If you tell me the number, I do that one; if not, I leave them.\"",
            ("If his words aren't about any of these, do what he asked as one look or one action: he said now." if spec.get("now") else
             "If his words aren't about any of these, end: your next session has them. This run does nothing else.")]
    return "\n".join(out)


def _yes_words(aid: str, parsed: dict, spec: dict) -> str:
    """His yes, what it opened, and the one call."""
    y = spec["yes"]
    return (f"He said yes, in his own words: \"{y['words']}\". That opened exactly this: {y['what']} ({y['why']}: he knows, and he said yes).\n"
            f"Make this one call now, once, with exactly this input and nothing added: tool {y['tool']}, input {json.dumps(y['input'], ensure_ascii=False)}.\n"
            "That's all this run has and all it does: no commands, no other tool. HQ reads the result and writes your ledger.")


def _step_words(aid: str, parsed: dict, spec: dict, base: Path) -> str:
    if spec.get("yes"):
        return _yes_words(aid, parsed, spec)
    if spec.get("answer"):
        return _answer_words(aid, parsed, spec)
    if spec.get("words"):
        return _stop_words(aid, parsed, spec)
    cy = ROOT / "routine" / "cycles.py"
    out = [f"This step, from your cycle plan of {parsed['stamp']} (step {parsed['k']}):",
           f"- goal: {spec.get('goal', parsed.get('goal', ''))}",
           f"- done means: {spec.get('done_means', '')}",
           f"- what you may do: {spec.get('may', 'one look or one action inside your limits')}",
           f"- escalate when: {spec.get('escalate_when', 'anything outside your limits comes up')}",
           "Its inputs, as they are now (checked against the plan before this run started; nothing else is loaded):"]
    for inp in spec.get("inputs") or []:
        out.append(f"\n[{inp.get('kind')} {inp.get('label') or inp.get('words') or inp.get('path') or ''}]\n{resolve(inp, base)}")
    if spec.get("order") and aid == FIX_AGENT:  # F105
        out.append(f"\nA row you write for this: python3 \"{ROOT / 'routine' / 'jobs.py'}\" write-row --order {spec['order']} \"THE ROW\": his request's record goes on under the row.")
    out.append(f"\nA small step makes no new steps and plans nothing. End with python3 \"{cy}\" done {aid} {parsed['k']} \"what came of it\" "
               f"(or python3 \"{cy}\" stale {aid} {parsed['k']} \"why\" when there's nothing left to do, python3 \"{cy}\" failed {aid} {parsed['k']} \"why\" when the check failed, or an ask when it's outside your limits).")
    return "\n".join(out)


def _fix_words(aid: str, parsed: dict) -> str:
    """F86: the one row and its findings, and the ways out of this round."""
    import review
    import sprint
    rv = review.ROOT_FILE
    label = parsed["label"]
    row = sprint.row_of(label) or {"line": ""}
    ask = sprint.ask_of(row["line"])
    st = review.states([row]).get(label, {}) if row.get("label") else {}
    sit = (f"python3 \"{rv}\" sitdown {label} \"the open point with your proposed solution\" \"If ..., I'll ...; if not, ...\"")
    no_ = (f"python3 \"{rv}\" no {label} \"why, in one or two plain sentences\" \"what could work instead\" \"If ..., I'll ...; if not, ...\"")
    end = f"End with one line in your ledger: python3 \"{ROOT / 'routine' / 'ledger.py'}\" {aid} note \"{parsed['name']}: what you did\"."
    if parsed["mode"] == "mark":
        return (f"This run: one row, {label}. The review passed it, so your mark comes second. Nothing else is loaded.\n\nThe row:\n{ask}\n\n"
                f"Hold it against your ready check yourself. It holds: python3 \"{ROOT / 'routine' / 'sprint.py'}\" ready {label}. "
                f"It doesn't, or the mark is refused: nothing is forced, it goes to him: {sit} And if you now see it can't be done as asked or isn't worth building, "
                f"say no, a good ending: {no_}\n{end}")
    finds = "\n".join(f"- {f}" for f in st.get("findings") or []) or "- (no findings written)"
    fields = sprint.fields_words(row) if row.get("label") and sprint.fields_why(row) else ""
    return (f"This run: round {parsed['round']} of at most {review.ROUNDS} on one row of the planning, {label}. The review flagged it. "
            "Nothing else is loaded. Every command you need is in this prompt, so don't read HQ's code to learn how the loop works; look up only what a "
            f"finding needs.\n\nThe row:\n{ask}\n\nThe review's findings:\n{finds}\n\n"
            + (f"What your mark will need, the row's ready fields:\n{fields}\n\n" if fields else "") +
            "A round can only add. Everything that stands in the row stays exactly as it is, every quote and every sentence; you can't change or take out a word. "
            f"What you add goes in one place, and the program puts {fix_name()}'s addition with the date in front of it, so nothing you write can read as his:\n"
            f"python3 \"{rv}\" add {label} <<'EOF'\nyour words, one go for all you add\nEOF\n"
            "Quote marks only around his own words, copied from one line of his (his lines in the calls in HQ/calls, his texts, his quick notes) in one unbroken piece, "
            "no … in it; an agent's line is never his. A name, a label or a command goes without quote marks or backticks.\n"
            "A ready field you can ground goes in the same addition. His words: only what he said about this very row. A row found by QA, the team, the review or a check, where he said nothing, "
            "says so, and that holds: His words: none, found by job N (a job the row names or that names the row), or by the review, or a check; never on a row with a quotation in it. A quote he said about something else never goes in: if you'd have to explain that he said it about "
            "another thing, leave it out. If he asked for this and his words are needed and missing, that's the list. Sources: each item on its own between semicolons, and each one a planning row (F86), "
            "a rule (rule 13), a dated call (call of 20 October 2026) or a file path; no line numbers, jobs or commits in that field, they read as a source that isn't there. "
            "The command tells you if a field won't hold, and nothing is written then. A field that's there and wrong you can't change: that one is his.\n\n"
            "Three ways out of this round, for the row as a whole:\n"
            f"- You can ground it (his words with a date, a rule, a planning row, the code): add it, naming the source. The review reads your addition as part of the row and looks again by itself.\n"
            f"- Only he can answer it (his words are missing, a choice that's his, a number you'd pick): you never fill it in, not even marked as yours. {sit} "
            "That's his one text, and the loop stops for this row. All the open points of the row in that one command.\n"
            f"- It can't be done as asked, or it isn't worth building: say no. {no_} "
            "The row stops, gets no Ready mark, nothing else on it changes, and he decides. That's a good ending of a round, not a failed one. Getting a row through is not "
            "the goal; a row that's right, or an honest no, is.\n"
            f"Never mark it ready in this round: the review's pass comes first, and your mark gets its own run after it.\n{end}")


def _norm_goal(g: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", " ".join(str(g).lower().split()))[:120]


def _stem(w: str) -> str:
    for end in ("ing", "ers", "er", "ed", "es", "s", "e"):
        if w.endswith(end) and len(w) - len(end) >= 3:
            return w[:-len(end)]
    return w


def _meant(words: str) -> set:
    """What an order or a goal is about: its own words, without the small ones and the stop verbs."""
    return {_stem(w) for w in _norm_goal(words).split() if w not in _STOP_WORDS and not w.isdigit()}


def _about(order_words: str, goal: str) -> bool:
    """A stop order is about this goal: all it names (of three or more words, two thirds), never a shared small word."""
    want, have = _meant(order_words), _meant(goal)
    hit = len(want & have)
    return bool(want) and (hit == len(want) if len(want) <= 2 else hit >= max(2, (2 * len(want) + 2) // 3))


TRIED = ("started", "failed", "boxed", "ended without saying what came of it")


def _goal_open(st_: dict, g: str, now: dt.datetime) -> bool:
    """Harm 7: the same goal tried without getting done: its last real try, in the last week, ended without done. A step that
    never ran (stale because he did the thing, skipped, past its time) is no try, and neither is one of long ago."""
    since = (now - dt.timedelta(days=REPEAT_DAYS)).strftime("%Y-%m-%d")
    tried = False
    for r in sorted((r for r in st_["steps"].values() if _norm_goal((r.get("spec") or {}).get("goal", "")) == g and r.get("day", "") >= since), key=lambda r: r.get("stamp", "")):
        if r.get("state") == "done":
            tried = False
        elif r.get("state") in TRIED:
            tried = True
    return tried


def plan(aid: str, raw: str, now: dt.datetime | None = None, base: Path | None = None, job: int | None = None) -> str:
    """The bigger session's plan: checked, written in her ledger, its steps planned as one-off priority items with
    their inputs fingerprinted. Refuses (ValueError) a plan with too many picks or steps, the day's count included, a step
    without its goal, done_means or time, an input that isn't there, and a plan from any run but a bigger session."""
    now = now or dt.datetime.now()
    base = base or folder()
    run = _this_run()
    if run and run["kind"] != "session":
        raise ValueError("a small step makes no new steps; only the bigger session plans")
    a = agent_settings(aid, base)
    try:
        p = json.loads(raw)
        assert isinstance(p, dict)
    except Exception:
        raise ValueError("the plan is JSON: {\"picks\": [...], \"let_go\": [...], \"steps\": [...], \"questions\": [...]}")
    picks = p.get("picks") or []
    steps = p.get("steps") or []
    most = int(a["step"].get("most_a_day") or 3)
    if len(picks) > PICKS_MOST:
        raise ValueError(f"at most {PICKS_MOST} picks: the few things, the rest stays in chaos")
    lo, hi = a.get("hours") or ["08:00", "22:00"]
    for i, st in enumerate(steps, 1):
        if not isinstance(st, dict) or not str(st.get("goal", "")).strip() or not str(st.get("done_means", "")).strip():
            raise ValueError(f"step {i} needs its goal and what done means")
        at = str(st.get("at", "")).strip()
        if not _is_time(at):
            raise ValueError(f"step {i} needs a time today, HH:MM")
        st["at"] = _hhmm(at)
        if not _at_hour(a, st["at"]):
            raise ValueError(f"step {i}'s time {st['at']} is outside your hours {lo} to {hi}")
        if str(st.get("until", "")).strip() and not (_is_time(str(st["until"])) and _hhmm(str(st["until"])) > st["at"]):
            raise ValueError(f"step {i}'s until is a time after its own, HH:MM")
        st["inputs"] = [x for x in (st.get("inputs") or []) if isinstance(x, dict) and x.get("kind")]
        for x in st["inputs"]:
            if resolve(x, base).startswith("(no such"):  # harm 16: an input that isn't there now could never go stale
                raise ValueError(f"step {i}'s input isn't there ({ledger._input_words(x)}): name one that is, or none")
    stops = [o["words"] for o in ledger.orders(aid, ("open", "planned", "done")) if o["kind"] == "stop"]
    today = now.strftime("%Y-%m-%d")
    cut7 = (now - dt.timedelta(days=REPEAT_DAYS)).strftime("%Y-%m-%d")
    stamp = now.strftime("%Y-%m-%d %H:%M")
    with held() as d:
        st_ = _agent_state(d, aid)
        already = sum(1 for r in st_["steps"].values() if r.get("day") == today and not r.get("order") and r.get("state") != "not planned")
        if already + len(steps) > most:
            raise ValueError(f"at most {most} steps a day for you: {already} planned today already, this plan has {len(steps)}")
        kept, trip = [], []
        for i, st in enumerate(steps, 1):
            g = _norm_goal(st["goal"])
            if any(_about(w, st["goal"]) for w in stops):  # on her let-go until she brings it back to him
                ledger.note(aid, f"left out of the plan, he said to stop it: {st['goal']}")
                continue
            if any(r.get("state") == "stopped" and _norm_goal((r.get("spec") or {}).get("goal", "")) == g and r.get("day", "") >= cut7 for r in st_["steps"].values()):
                ledger.note(aid, f"left out of the plan, he said to stop it: {st['goal']}")
                continue
            gr = st_["goals"].setdefault(g, {})
            if gr.pop("go", None):  # his go: once more
                gr.pop("tripped", None)
            elif _goal_open(st_, g, now):
                trip.append(st["goal"])
                if (gr.get("tripped") or "") < (now - dt.timedelta(days=REPEAT_DAYS)).strftime("%Y-%m-%d"):  # once; after that it's in the ledger until he answers
                    gr["tripped"] = today
                    tripwire(aid, "same goal twice", f"I tried \"{st['goal']}\" before and it didn't get done, so it waits for your word", now, base)
                else:
                    ledger.note(aid, f"held again, tried before without done: {st['goal']}")
                continue
            kept.append((i, st))
        times = sorted(st["at"] for _, st in kept)
        stamp_items = []
        for i, st in kept:
            fps = [_fp(resolve(x, base)) for x in st["inputs"]]
            text = step_text(aid, stamp, i, st["goal"])
            when = f"today {st['at']}" if _t(st["at"]) > now.time() else "now"
            code, out = _schedule("add", when, text, "--priority", "--kind", f"step-{aid}")
            m = re.search(r"Item (\d+) is planned", out)
            st_["steps"][f"{aid}|{stamp}|{i}"] = {"spec": st, "fps": fps, "day": today, "item": int(m.group(1)) if m else None,
                                                 "state": "planned" if code == 0 else "not planned", "stamp": stamp,
                                                 "until": _step_until(st, times, now, a).strftime(FMT)}
            stamp_items.append(f"step {i} planned at {st['at']}" + ("" if code == 0 else f" (not planned: {out[:80]})"))
        cut = (now - dt.timedelta(days=30)).strftime("%Y-%m-%d")
        st_["steps"] = {k: v for k, v in st_["steps"].items() if v.get("day", "") >= cut}
        for n in p.get("orders_done") or []:
            try:
                ledger.set_order(aid, int(n), "planned", f"in the plan of {stamp}")
            except Exception:
                pass
        p["stamp"] = stamp
        p["steps"] = [st for _, st in kept]
        title = ledger.write_plan(aid, p, job, now)
        for q_ in (p.get("questions") or [])[:QUESTIONS_MOST]:
            ask(aid, str(q_), now, base)
    return (f"Plan written in {aid}'s ledger ({title}): {len(picks)} picks, {len(kept)} steps" + (f" ({', '.join(stamp_items)})" if stamp_items else "")
            + (f"; {len(trip)} step(s) held: the same goal was tried before without done" if trip else "") + ".")


def _step_until(st: dict, times: list, now: dt.datetime, a: dict) -> dt.datetime:
    """Harm 16: when a step stops being of use: her own until, else the next step's time, at the most STEP_GRACE after its own."""
    day = now.replace(second=0, microsecond=0)
    at = day.replace(hour=_t(st["at"]).hour, minute=_t(st["at"]).minute)
    at = max(at, day)
    end = _shift_end(a, day)
    if str(st.get("until", "")).strip():
        u = _t(_hhmm(str(st["until"])))
        return min(end, day.replace(hour=u.hour, minute=u.minute))
    nxt = [n for n in (day.replace(hour=_t(x).hour, minute=_t(x).minute) for x in times) if n > at]
    return min(end, nxt[0] if nxt else end, at + dt.timedelta(minutes=STEP_GRACE))


def _this_run() -> dict | None:
    """The cycle job this process is part of (the runner sets HQ_JOB on her run), or None: a call, a person, the routine."""
    n = os.environ.get("HQ_JOB") or ""
    if not n.isdigit():
        return None
    try:
        import jobs as q
        j = next((x for x in q.read()[1] if x["n"] == int(n)), None)
    except Exception:
        return None
    return parse(j["text"]) if j else None


def step_done(aid: str, k: int, what: str, failed: bool = False, now: dt.datetime | None = None, base: Path | None = None, gone_stale: bool = False) -> str:
    """A small step says what came of it (her own run writes it): the ledger, the goal's record, a check failing
    twice as a tripwire. Stale: nothing was left to do; it ends quietly and the goal goes on."""
    now = now or dt.datetime.now()
    with held() as d:
        st_ = _agent_state(d, aid)
        run = _this_run()
        if run and run["kind"] == "step" and run["agent"] == aid and run["k"] == k and _step_key(run) in st_["steps"]:  # this run's own step, whatever came after it
            key, rec = _step_key(run), st_["steps"][_step_key(run)]
        else:
            cands = [(key, v) for key, v in st_["steps"].items() if key.endswith(f"|{k}") and v.get("state") not in ("stale",)]
            cands.sort(key=lambda kv: kv[1].get("stamp", ""))
            key, rec = (cands[-1] if cands else (None, None))
        goal = (rec or {}).get("spec", {}).get("goal", f"step {k}")
        g = _norm_goal(goal)
        gr = st_["goals"].setdefault(g, {})
        if gone_stale:
            if rec is not None:
                rec["state"] = "stale"
            ledger.note(aid, f"step {k} stale: {what}")
            return f"Step {k} is stale, written in {aid}'s ledger; the goal stays open for a next plan."
        if failed:
            gr["failed"] = gr.get("failed", 0) + 1
            if rec is not None:
                rec["state"] = "failed"
            ledger.note(aid, f"step {k} failed: {what}")
            if gr["failed"] >= 2:
                tripwire(aid, "a check failing twice", f"the check of \"{goal}\" failed twice ({what[:120]}), so it waits for your word", now, base)
        else:
            gr["done"], gr["failed"] = True, 0
            if rec is not None:
                rec["state"] = "done"
            ledger.note(aid, f"step {k} done: {what}")
    return f"Step {k} {'failed' if failed else 'done'}, written in {aid}'s ledger."


# -- texts: asks, batches, tripwires ------------------------------------------------------------------------------------------

def _today(now: dt.datetime) -> str:
    return now.strftime("%Y-%m-%d")


def asleep(now: dt.datetime) -> bool:
    """He's asleep (H212: his calendar's Sleep block, else the night hours). A test says so itself with HQ_ASLEEP."""
    if os.environ.get("HQ_ASLEEP") in ("0", "1"):
        return os.environ["HQ_ASLEEP"] == "1"
    try:
        import pings
        return pings._asleep(now.timestamp())
    except Exception:
        return False


def _day_end(a: dict, now: dt.datetime) -> dt.datetime:
    return _shift_end(a, now)


def _true(e: dict, now: dt.datetime, base: Path | None = None) -> str | None:
    """Why a queued text isn't true any more, or None. It has a date, and what it stood on is still there."""
    try:
        if now > dt.datetime.strptime(e["until"], FMT):
            return f"past its time ({e['until']})"
    except (KeyError, ValueError):
        return "it has no date"
    return _changed(e.get("inputs") or [], e.get("fps") or [], base)


def say(aid: str, text: str, why: str, now: dt.datetime, base: Path | None = None, until: dt.datetime | None = None) -> str:
    """Her text now, or when he's up: due during his Sleep it waits until the block ends, and goes only if it's still true
    then (the same way HQ's other texts do, H212). Goes out after the state's lock is let go."""
    a = agent_settings(aid, base)
    with held() as d:
        if asleep(now):
            end = until or (_day_end(a, now) if _day_end(a, now) > now else _day_end(a, now) + dt.timedelta(days=1))
            _agent_state(d, aid)["later"].append({"text": text, "why": why, "at": now.strftime(FMT), "until": end.strftime(FMT), **_stands_on(aid, base)})
            return "later"
        _tls.out.append((aid, text, why, base))
    return "sent"


def _stands_on(aid: str, base: Path | None = None) -> dict:
    """What a text from this run stands on: the step's inputs as they are now. Changed by the time it goes, it isn't true."""
    run = _this_run()
    if not run or run["kind"] != "step" or run["agent"] != aid:
        return {}
    rec = _agent_state(_state(), aid)["steps"].get(_step_key(run)) or {}
    inputs = (rec.get("spec") or {}).get("inputs") or []
    return {"inputs": inputs, "fps": [_fp(resolve(x, base)) for x in inputs]} if inputs else {}


def later(now: dt.datetime | None = None, base: Path | None = None, log=None) -> list[str]:
    """What waited for him to wake up goes now, each only while it's true."""
    now = now or dt.datetime.now()
    did = []
    if asleep(now):
        return did
    with held() as d:
        for aid in list((d.get("agents") or {})):
            st_ = _agent_state(d, aid)
            for e in st_["later"]:
                no = _true(e, now, base)
                if no:
                    ledger.note(aid, f"not sent, {no}: {e['text'][:160]}")
                else:
                    _tls.out.append((aid, e["text"], e.get("why", "cycle"), base))
                    did.append(f"{aid}: a text that waited for him to wake up")
            st_["later"] = []
    if log:
        for x in did:
            log(f"cycles: {x}")
    return did


def _batch_times(a: dict, now: dt.datetime, sent: str | None) -> list[dt.datetime]:
    """The batch times still to come today (one in its quarter of an hour counts, if it hasn't gone)."""
    out = []
    for t in a.get("batches") or []:
        bt = now.replace(hour=_t(t).hour, minute=_t(t).minute, second=0, microsecond=0)
        if (bt > now or bt <= now < bt + dt.timedelta(minutes=15)) and sent != f"{_today(now)} {t}":
            out.append(bt)
    return sorted(out)


def _when(words: str, now: dt.datetime) -> dt.datetime | None:
    """A moment in plain words: HH:MM, tomorrow HH:MM, friday HH:MM or YYYY-MM-DD HH:MM; the next one."""
    w = " ".join(str(words).lower().split())
    try:
        return dt.datetime.strptime(w, FMT)
    except ValueError:
        pass
    m = re.fullmatch(r"(?:(today|tomorrow|\w+day) )?(\d{1,2}:\d\d)", w)
    if not m or not _is_time(m.group(2)):
        return None
    t = _t(m.group(2))
    at = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
    if m.group(1) == "tomorrow":
        return at + dt.timedelta(days=1)
    if m.group(1) in DAYS:
        return at + dt.timedelta(days=(DAYS.index(m.group(1)) - now.weekday()) % 7 or (7 if at <= now else 0))
    if m.group(1) in (None, "today"):
        return at if at > now or m.group(1) else at + dt.timedelta(days=1)
    return None


def ask(aid: str, text: str, now: dt.datetime | None = None, base: Path | None = None, must: bool = False) -> str:
    """One question for him on her line, in if-then shape, never the same one twice in a day, at most ASKS_A_DAY a day. With
    batches it goes into her next one, however far that is; without, now (or when he's up)."""
    now = now or dt.datetime.now()
    text = " ".join(str(text).split())
    if not text:
        return "An ask needs words."
    a = agent_settings(aid, base)
    with held() as d:
        st_ = _agent_state(d, aid)
        key = _norm_goal(text)
        asked = st_["asked"]
        today = _today(now)
        if asked.get(key) == today:
            return "Already asked today; not asked again."
        run = _this_run()
        rec = st_["steps"].get(_step_key(run)) if run and run["kind"] == "step" else None
        his_words = bool(rec and (rec.get("stop") or (rec.get("spec") or {}).get("answer")))  # she's asking about something he just said: it can't wait for Friday
        if his_words and rec.get("asked"):
            return "You've asked him in this run already; once is enough."
        if st_["asks"].get(today, 0) >= ASKS_A_DAY and not must and not his_words:
            ledger.note(aid, f"kept for Friday, the day's questions are used up: {text}")
            return f"The day's {ASKS_A_DAY} questions are used up; it's in the ledger for Friday."
        asked[key] = today
        st_["asks"] = {today: st_["asks"].get(today, 0) + 1}
        if rec is not None:
            rec["asked"] = True  # a stop or a yes she asked about is answered, not lost
        ledger.note(aid, f"escalated: {text}")
        if a.get("batches"):
            nxt = _batch_times(a, now, st_.get("batch_sent")) or [(now + dt.timedelta(days=1)).replace(hour=_t(a["batches"][0]).hour, minute=_t(a["batches"][0]).minute, second=0, microsecond=0)]
            st_["batch"].append({"text": text, "at": now.strftime(FMT), "until": (nxt[0] + dt.timedelta(minutes=15)).strftime(FMT), **({"which": True} if his_words else {})})
            return f"Queued for {aid}'s next batch ({', '.join(a['batches'])})."
        say(aid, text, "cycle-ask", now, base)
    return f"Asked on {aid}'s line."


def batch(aid: str, text: str, now: dt.datetime | None = None, base: Path | None = None, until: str | None = None) -> str:
    """A text for her next batch. It has a date: today's, or the moment she names; it goes out only while it's true, so a
    Friday text never lands on a Saturday. With no batch left before its date it isn't queued, and she's told."""
    now = now or dt.datetime.now()
    text = " ".join(str(text).split())
    if not text:
        return "A batch text needs words."
    a = agent_settings(aid, base)
    end = None
    if until:
        end = _when(until, now)
        if end is None or end <= now:
            return f"Not queued: --until is a moment still to come, like 17:30, tomorrow 12:15 or friday 12:15 (\"{until}\")."
    with held() as d:
        st_ = _agent_state(d, aid)
        if not a.get("batches"):
            say(aid, text, "cycle", now, base, end)
            return f"{aid} has no batches: on her line now."
        sent = st_.get("batch_sent")
        times = _batch_times(a, now, sent)
        for i in range(1, 8):  # the batches of the coming days, for a later date
            day = now + dt.timedelta(days=i)
            times += [day.replace(hour=_t(x).hour, minute=_t(x).minute, second=0, microsecond=0) for x in a["batches"]]
        last = end or (_day_end(a, now) if _day_end(a, now) > now else now)
        if not [x for x in sorted(times) if x <= last]:
            return (f"Not queued: today's last batch has gone, and a queued text has a date. If it's still true later, say until when with --until; "
                    "if not, it stays in your ledger.")
        st_["batch"].append({"text": text, "at": now.strftime(FMT), "until": last.strftime(FMT), **_stands_on(aid, base)})
    return f"Queued for {aid}'s next batch ({', '.join(a['batches'])}), good until {last:%A %H:%M}."


def send_batches(now: dt.datetime | None = None, base: Path | None = None, log=None) -> list[str]:
    """At each batch time (within the quarter after it), what's queued and still true goes out as one text. What's past
    its date or stands on something that changed is dropped, with a line in her ledger, at any minute."""
    now = now or dt.datetime.now()
    did = []
    with held() as d:
        for aid, a in settings(base)["agents"].items():
            st_ = _agent_state(d, aid)
            keep = []
            for e in st_["batch"]:
                e.setdefault("until", (dt.datetime.strptime(e.get("at", now.strftime(FMT)), FMT).replace(hour=23, minute=59)).strftime(FMT))  # queued before they had a date: that day
                no = _true(e, now, base)
                if no:
                    ledger.note(aid, f"not sent, {no}: {e['text'][:160]}")
                else:
                    keep.append(e)
            st_["batch"] = keep
            for t in a.get("batches") or []:
                bt = now.replace(hour=_t(t).hour, minute=_t(t).minute, second=0, microsecond=0)
                key = f"{_today(now)} {t}"
                if bt <= now < bt + dt.timedelta(minutes=15) and st_.get("batch_sent") != key:
                    st_["batch_sent"] = key
                    if st_["batch"]:
                        texts = [x["text"] for x in st_["batch"]]
                        until = min(dt.datetime.strptime(x["until"], FMT) for x in st_["batch"])
                        st_["batch"] = []
                        say(aid, " ".join(texts) if len(texts) == 1 else "\n".join(f"- {x}" for x in texts), "cycle-batch", now, base, until)
                        ledger.note(aid, f"batch at {t}: {len(texts)} text(s) sent")
                        did.append(f"{aid}'s {t} batch: {len(texts)} text(s)")
    if log:
        for x in did:
            log(f"cycles: {x}")
    return did


TRIPWIRE_WORDS = {
    "same goal twice": "If you want me to keep at it, say go and I'll try once more in my next session; if not, I let it go until you bring it back.",
    "boxed twice in a row": "If this is worth more time, say so and I'll give it a bigger box next time; if not, I drop it and plan smaller steps.",
    "a refused command or push": "If you want that done, tell me how; if not, I leave it.",
    "a check failing twice": "If you want me to try another way, say so; if not, I let it go until Friday.",
    "an action outside my limits": "If that was all right, say so; if not, tell me what to undo.",
    "a write to a shared file outside the serialized place": "If you want that change kept, say so; if not, tell me and I'll put it back through HQ's own scripts.",
    "a Ready mark refused on its fields": "If you give me the quote and the sources I'll mark it ready; if not, it stays on the sit-down list for Friday.",
    "a run of mine failed": "If you want me to look at it now, say so; if not, I try again at its next time.",
}


NOT_REPEATS = ("an action outside my limits", "a write to a shared file outside the serialized place")  # those are one thing that went wrong; the rest are a mistake made twice


def tripwire(aid: str, kind: str, detail: str, now: dt.datetime | None = None, base: Path | None = None, d: dict | None = None,
             text: bool = True) -> str:
    """Counted by the runner: a line in her ledger, and one message on her line in if-then shape, in plain words, at most her
    texts a day; past that, the ledger only. text=False: the ledger only, for a run that already put the same thing to him (F86:
    one text). Her own daily texts have a count of their own, so a tripwire never uses up her real reminder."""
    now = now or dt.datetime.now()
    with held() as d:
        st_ = _agent_state(d, aid)
        ledger.note(aid, f"tripwire ({kind}): {detail}" + (" [repeat]" if kind not in NOT_REPEATS else ""))
        if "refus" in kind:  # F103: a refused try is also on the one ledger the score reads
            import mistakes
            mistakes.add("refused", aid, f"{kind}: {detail}", where="her own cycle", base=base)
        today = _today(now)
        sent = st_["texts"].get(today, 0)
        most = int(agent_settings(aid, base).get("tripwire_texts", 2))
        if sent >= most or not text:
            return "ledger only (the day's texts are used up)" if text else "ledger only (she put it to him herself)"
        st_["texts"] = {today: sent + 1}
        d_ = detail.rstrip(" .")
        msg = f"{d_[:1].upper() + d_[1:]}. {TRIPWIRE_WORDS.get(kind, 'Say what you want me to do, and I do that.')}"
        say(aid, msg, "tripwire", now, base)
    return "texted"


# -- after a run: the ledger, the tripwires, the streaks ---------------------------------------------------------------------

def _how_ended(job: dict, note: dict, st_: dict) -> str:
    state = job.get("state", "")
    if str(job["n"]) in st_["held_out"]:
        return "held while it ran, not started again"
    if note.get("boxed"):
        return "boxed at its " + note["boxed"]
    if "by a crash" in state:
        return "ended by a crash"
    if state.startswith("paused"):
        return "paused, it used far more than it should"
    return "done" if state.startswith("done") else state.split(" ")[0] or "ended"


def _failed(job: dict, parsed: dict, note: dict, st_: dict, aid: str) -> str | None:
    """Why this run failed, in plain words, or None: it stopped by itself without getting through. His stop, a hold, the
    box and a crash of the computer are something else; a session that ended without a plan is a failure too."""
    state = job.get("state", "")
    n = str(job["n"])
    if n in st_["held_out"] or "by a crash" in state or "hours ended" in state or state.startswith(("stopped", "cancelled")) or note.get("ended_by") == "signal":
        return None
    if state.startswith("paused"):
        return "it used about four times what it should, so HQ stopped it"
    if state.startswith("ended") or (note and not note.get("boxed") and (note.get("exit") not in (0, None) or note.get("error"))):
        return "it stopped before it got anywhere" if not note or not note.get("steps") else "it stopped halfway with an error"
    if parsed["kind"] == "session" and st_["run_start"].get(n):
        sec, _ = ledger.plan(aid)
        if not sec or sec["at"] < dt.datetime.strptime(st_["run_start"][n], FMT):
            return "it ended without writing a plan"
    return None


def after_run(job: dict, parsed: dict, now: dt.datetime | None = None, base: Path | None = None, run_dir: str | None = None, log=None) -> dict:
    """A run that's over, once, whichever way it ended: what it cost into her share, its box note into her ledger (minutes,
    turns, how it ended), a run that failed said once, a crashed session back as itself, what the stream shows really
    happened: a real refusal is logged, a repeat of it or a run that went past the hook is a tripwire, boxed twice in a row."""
    now = now or dt.datetime.now()
    aid = parsed["agent"]
    with held() as d:
        st_ = _agent_state(d, aid)
        if job["n"] in st_["processed"]:
            return {}
        st_["processed"] = (st_["processed"] + [job["n"]])[-200:]
        if str(job["n"]) in st_["skipped"]:  # gatekeep stopped it before it ran and already wrote why
            return {}
        if job.get("state", "").startswith("cancelled") and str(job["n"]) not in st_["run_start"] and str(job["n"]) not in st_["held_out"]:  # it never ran: nothing to write, nothing to count
            return {}
        run_dir = run_dir or os.environ.get("HQ_JOB_RUN") or os.path.join(hqpaths.HQ, "scratch", "routine")
        note = {}
        try:
            note = json.loads(Path(run_dir, f"job-{job['n']}.box.json").read_text(encoding="utf8"))
        except (OSError, ValueError):
            pass
        _charge(job, now)
        state = job.get("state", "")
        how = _how_ended(job, note, st_)
        cost, took = "", {}
        try:
            import estimate
            took = next((h for h in reversed(estimate.history()) if h.get("n") == job["n"]), {})
            if took.get("cost"):
                cost = f", cost {took['cost'].get('weekly', 0):g}% of the week" + (" (its estimate, nothing was measured)" if took.get("cost_how") == "estimate" else "")
        except Exception:
            pass
        line = f"run: {how} · {note.get('minutes', took.get('actual', '?'))} min, {note.get('turns', '?')} turns, {note.get('steps', '?')} tool steps{cost} (job {job['n']})"
        ledger.entry(aid, f"{parsed['name']} ran (job {job['n']})", [line], now)
        if state.startswith("paused"):
            _jobs("mark", str(job["n"]), f"ended {now:%H:%M}, paused for its usage; an agent's run isn't resumed")
        rec = st_["steps"].get(_step_key(parsed)) if parsed["kind"] == "step" else None
        if rec is not None and (rec.get("stop") or (rec.get("spec") or {}).get("answer")):  # his words' run is over, whatever came of it
            st_["stopping"].pop(str(rec.get("order")), None)
            if rec.get("asked"):
                rec["state"] = "done"
                ledger.set_order(aid, rec["order"], "done", "she asked him which")
            elif rec.get("state") in ("planned", "started"):
                rec["state"] = "ended without saying what came of it"
                _order_back(aid, rec, f"its run ended ({how}) with nothing done and nothing asked", base)
                if rec.get("stop"):
                    ledger.note(aid, f"his stop order's run ended without an answer: {rec['spec'].get('words', '')}")
                    say(aid, f"I didn't get to your stop, \"{rec['spec'].get('words', '')}\". If it still stands, say it again; if not, I leave it.", "cycle", now, base)
        elif rec is not None and (rec.get("spec") or {}).get("yes"):  # his yes: it worked, or it comes back to him, once
            if rec.get("state") != "done":
                y = rec["spec"]["yes"]
                rec["state"] = "failed"
                st_["holds"].append({k: y[k] for k in ("key", "what", "why", "tool", "input")} | {"n": y["n"], "at": now.strftime(FMT)})
                ledger.set_order(aid, rec["order"], "open", "it didn't go through; the question stands again")
                say(aid, f"Your yes on {y['what']} didn't go through{': ' + rec['why'] if rec.get('why') else ''}. If you want it, say yes again; if not, I leave it.", "cycle", now, base)
        elif rec is not None and rec.get("state") in ("planned", "started"):
            clean = state.startswith("done") and not note.get("boxed") and note.get("exit") in (0, None)
            rec["state"] = "boxed" if note.get("boxed") else "finished without a line of what came of it" if clean else "ended without saying what came of it"
            ledger.note(aid, f"step {parsed['k']}: {rec['state']}")
            if clean and rec.get("order"):  # it ran to its end: his order isn't open again for want of a line
                ledger.set_order(aid, rec["order"], "done", "ran to its end")
            else:
                _order_back(aid, rec, f"its run ended ({how}) before it was done", base)
        if parsed["kind"] == "fix":  # F86: a round's texts are her sit-down, her no and the cap; what it tried or ran into stays in her ledger
            import review
            cut = bool(note.get("boxed") or state.startswith("ended") or str(job["n"]) in st_["held_out"])
            ledger.note(aid, f"{parsed['name']}: " + (f"cut off ({note.get('boxed') or state}); " + ("not marked, it stays on her list" if parsed["mode"] == "mark" else
                                                      "the row stays flagged and not ready, the round counts")
                                                      if cut else "ended; the review looks again if the words changed"))
            if parsed["mode"] == "mark":
                if review.mark_ended(parsed["label"], "her mark's run was cut off" if cut else "her mark's run ended with no mark and nothing for the sit-down list"):
                    ledger.note(aid, f"{parsed['label']} on the sit-down list: passed by the review, not marked")
            else:
                review.stop_stays(parsed["label"])
            for r in [x for x in note.get("refused") or [] if _REALLY_REFUSED.search(x.get("said", ""))][:1]:
                what = "a Ready mark refused" if "sprint.py ready" in r.get("tool", "") else "refused"
                ledger.note(aid, f"{parsed['name']}: {what}: {_plain(r.get('said', ''))}")
            if log:
                log(f"cycles: job {job['n']} ({aid}, {parsed['name']}) {how}")
            return note
        if "by a crash" in state and parsed["kind"] in ("session", "look", "review"):  # harm 1: back as itself, once; a step never
            last = st_["back"].get(parsed["name"])  # once: a day's worth, whatever time the one that came back was planned for
            if (not last or dt.datetime.strptime(last, FMT) < now - dt.timedelta(hours=24)) and _again(aid, parsed, agent_settings(aid, base), _job_at(job, now), now, base):
                st_["back"][parsed["name"]] = now.strftime(FMT)
        # a run that failed says so, once, until one gets through
        why = _failed(job, parsed, note, st_, aid)
        if why:
            ledger.note(aid, f"{parsed['name']} failed: {why}")
            if not st_["failing"].get("told"):  # once, whatever the day's cap of tripwires says: this one can't wait for the ledger
                st_["failing"] = {"told": now.strftime(FMT)}
                say(aid, f"My {parsed['name']} didn't get through: {why}. {TRIPWIRE_WORDS['a run of mine failed']}", "tripwire", now, base)
        elif state.startswith("done") and not note.get("boxed"):
            st_["failing"] = {}
        # boxed twice in a row
        if note.get("boxed"):
            st_["boxed_streak"] = st_.get("boxed_streak", 0) + 1
            if st_["boxed_streak"] >= 2:
                tripwire(aid, "boxed twice in a row", f"two of my runs in a row ran out of their box ({parsed['name']})", now, base)
                st_["boxed_streak"] = 0
        else:
            st_["boxed_streak"] = 0
        _what_really_happened(aid, parsed, note, now, base)
    if log:
        log(f"cycles: job {job['n']} ({aid}, {parsed['name']}) {how}")
    return note


def _short_why(said: str) -> str:
    s = _plain(said)
    s = re.sub(r"^(?:Error:?\s*|MCP error[^:]*:\s*)", "", s)
    return (s[:117] + "...") if len(s) > 120 else s


def calendar_result(aid: str, name: str, inp: dict, txt: str, ok: bool, job: int | None = None, now: dt.datetime | None = None, base: Path | None = None) -> None:
    """What really came of a calendar call, read by the runner from the call's own result: her ledger says it was done only once it was, a failed one says which.
    What she made goes on her own list at once: it's hers, she can move or remove it a minute later, HQ's copy of the calendar reads hourly."""
    import cyclehook
    now = now or dt.datetime.now()
    last = name.rsplit("__", 1)[-1]
    with held() as d:
        st_ = _agent_state(d, aid)
        rec = None
        if job:
            try:
                import jobs as q
                j = next((x for x in q.read()[1] if x["n"] == job), None)
                p = parse(j["text"]) if j else None
                rec = st_["steps"].get(_step_key(p)) if p and p["kind"] == "step" else None
            except Exception:
                rec = None
        what = cyclehook.calendar_what(last, inp, st_["mine"], str(base) if base else None)
        if not ok:
            ledger.note(aid, f"{now:%Y-%m-%d %H:%M} calendar: this one didn't go through: {what}: {_short_why(txt)}")
            if rec is not None:
                rec["why"] = _short_why(txt)
            return
        ledger.note(aid, f"{now:%Y-%m-%d %H:%M} {cyclehook.calendar_line(name, inp, str(base) if base else None, st_['mine'])}")
        try:  # H338: a write behind her "it's in your calendar", for the outbox's claim check
            sys.path.insert(0, str(ROOT / "app"))
            import outbox
            outbox.calendar_written(last)
        except Exception:
            pass
        eid = str(inp.get("eventId") or "")
        if last == "create_event":
            m = re.search(r"\"(?:id|eventId|event_id)\"\s*:\s*\"([^\"]+)\"", txt) or re.search(r"\b(?:id|eventId)\W{1,3}([\w-]{6,})", txt)
            st_["mine"][m.group(1) if m else f"new-{now:%H%M%S}"] = {"title": inp.get("summary"), "start": inp.get("startTime"), "end": inp.get("endTime"), "cal": inp.get("calendarId") or "",
                                                                 "others": any(inp.get(k) for k in cyclehook.OTHERS), "at": now.strftime(FMT)}
        elif eid in st_["mine"] and last == "delete_event":
            st_["mine"].pop(eid)
        elif eid in st_["mine"]:
            e = st_["mine"][eid]
            e.update({k2: inp[k1] for k1, k2 in (("summary", "title"), ("startTime", "start"), ("endTime", "end")) if inp.get(k1)})
        cut = (now - dt.timedelta(days=30)).strftime(FMT)
        st_["mine"] = {k: v for k, v in st_["mine"].items() if v.get("at", "") >= cut}
        st_["allowed"].pop(cyclehook._key(last, inp), None)
        if rec is not None and (rec.get("spec") or {}).get("yes"):
            rec["state"] = "done"
            ledger.set_order(aid, rec["order"], "done", "it went through")


def _plain(said: str) -> str:
    """What a refusal said, as a sentence for her ledger: HQ's own words, never the tool line."""
    s = re.sub(r"^(?:Exit code \d+\s*)?(?:PreToolUse:\S+ hook error:?\s*)?(?:\[[^\]]*\]:?\s*)?(?:HQ: refused:?\s*|Refused:?\s*)?", "", " ".join(str(said).split()))
    return (s[:157] + "...") if len(s) > 160 else s


_TO_HIM = ((r"reaching outside|nothing goes out", "I tried to reach outside HQ, and HQ stopped me"),
           (r"pushing code|git \w+ writes", "I tried to change the code's history, and HQ stopped me"),
           (r"his vision|is his|agents' own setup|agents' settings", "I tried to change something of yours, and HQ stopped me"),
           (r"built by the team|isn't a cycle's to run", "I tried to touch HQ itself, and HQ stopped me"),
           (r"deleting|trashing", "I tried to delete something, and HQ stopped me"),
           (r"run starts no other run", "I tried to start another run, and HQ stopped me"),
           (r"small step makes no new steps", "a step of mine tried to plan more, and HQ stopped it"),
           (r"shared file", "I tried to write a shared file by hand, and HQ stopped me"))


def _to_him(said: str) -> str:
    """The same, told to him: what I tried, in his terms, no tool names."""
    s = _plain(said)
    return next((w for pat, w in _TO_HIM if re.search(pat, s, re.I)), "I tried something that isn't mine to do, and HQ stopped me")


def _what_really_happened(aid: str, parsed: dict, note: dict, now: dt.datetime, base: Path | None) -> None:
    """Harm 6: from what really happened in the run, never from words in what it read. note["refused"] holds the calls that were
    really refused (the hook, a refused script, a rejected push), note["uses"] the outward ones that went through."""
    with held() as d:
        st_ = _agent_state(d, aid)
        since = (now - dt.timedelta(days=REPEAT_DAYS)).strftime(FMT)
        st_["refusals"] = {k: v for k, v in st_["refusals"].items() if v >= since}
        for r in (note.get("refused") or [])[:3]:
            plain = _plain(r.get("said", ""))
            mark = "sprint.py ready" in r.get("tool", "") and aid == "moneypenny"
            key = hashlib.sha1(_norm_goal(plain).encode()).hexdigest()[:12]
            if key in st_["refusals"]:  # the mistake made twice: that's what reaches him
                tripwire(aid, "a Ready mark refused on its fields" if mark else "a refused command or push", "that's twice now: a row wasn't ready when I marked it" if mark else "that's twice now: " + _to_him(r.get("said", "")), now, base)
            else:
                st_["refusals"][key] = now.strftime(FMT)
                ledger.note(aid, f"refused, logged: {plain}")
                import mistakes
                mistakes.add("refused", aid, f"a refused try: {plain}", where="her own cycle", base=base)
    import cyclehook
    for u in note.get("uses") or []:  # past the hook: it wasn't loaded, or something it should have stopped went through
        code, why = cyclehook.decide({"tool_name": u.get("name", ""), "tool_input": u.get("input") or {}}, False, None, (aid, parsed["kind"]))
        if code and not why.startswith("HQ: held"):  # a calendar answer can change once his yes is used
            shared = "shared file" in why
            tripwire(aid, "a write to a shared file outside the serialized place" if shared else "an action outside my limits",
                     f"something went through that should have been stopped: {_to_him(why)}", now, base)
            break


# -- orders from a call or a text --------------------------------------------------------------------------------------------

def order(aid: str, kind: str, words: str, now_: bool = False, now: dt.datetime | None = None, base: Path | None = None) -> str:
    now = now or dt.datetime.now()
    base = base or folder()
    if _this_run():
        raise ValueError("orders are his, from a call or a text; a run of hers doesn't give itself one")
    o = ledger.add_order(aid, kind, words, now_, now)
    if kind == "start":  # F105: a request gets its one id at the hand-off, so everything after it is on one record
        import trail
        trail.order(aid, o["n"], words, by=os.environ.get("HQ_DIRECT_AGENT") or "")
    if kind == "stop":
        return _stop_order(aid, o, now, base)
    if kind == "standing":
        import handbook
        p = handbook.path(base)
        try:
            t = p.read_text(encoding="utf8")
        except OSError:
            t = ""
        ag = _agent(aid, base)
        name = ag["name"] if ag else aid.capitalize()
        heads = list(re.finditer(r"^### (.+)$", t, re.M))
        line = f"\n**From now on** ({now:%-d %B %Y}, his words): \"{words}\"\n"
        at = None
        for i, h in enumerate(heads):
            if re.match(rf"{re.escape(name)}\b", h.group(1).strip(), re.I):
                at = heads[i + 1].start() if i + 1 < len(heads) else len(t)
                break
        if at is None:
            return f"Written in her ledger, but {name} has no section of her own in the handbook to put it in."
        t = t[:at].rstrip("\n") + "\n" + line + "\n" + t[at:]
        p.write_text(t, encoding="utf8")
        ledger.set_order(aid, o["n"], "done", "written into her own section")
        return f"Standing: written into {name}'s own section of the handbook."
    if _waiting_for_word(aid, now):  # his words go to her, with what's waiting: she knows what he means, a list of phrases doesn't
        return _answer_order(aid, o, now, base, now_)
    if now_:
        a = agent_settings(aid, base)
        if not in_hours(a, now):  # harm 9: said out loud, kept, and the first thing she does at her hours
            lo, hi = a.get("hours") or ["08:00", "22:00"]
            ledger.set_order(aid, o["n"], "now", f"said outside her hours, waits for {lo}")
            return f"Not now: nothing of {aid}'s runs between {hi} and {lo}. It's kept, and it's the first thing she does at {lo}. Tell him so."
        return _order_step(aid, o, now, base)
    if not on(base):
        return f"Noted for {aid}'s next bigger session: \"{words}\". Her looks at her list are off while the agents' switch is off."
    nx = next_look(aid, now, base) if agent_settings(aid, base).get("on") else None  # H308: her next look picks it up, not her bigger session
    if nx:
        return f"Noted for {aid}: her {nx[0]} ({nx[1]:%A %H:%M}) turns it into a step, so it doesn't wait for her next bigger session: \"{words}\"."
    return f"Noted for {aid}'s next bigger session: \"{words}\"."


def waiting_words(aid: str) -> str:
    """What waits for his word, for whoever talks to him: a text or a call can answer it. The questions may not have gone out yet."""
    holds = _agent_state(_state(), aid)["holds"]
    return ("Waiting for his word, with their numbers: " + "; ".join(f"({h['n']}) {h['what']}, {h['why']}" for h in holds) + ".") if holds else ""


def _held_goals(st_: dict, now: dt.datetime) -> list:
    """The goals held as tried without done, that wait for his go: newest first."""
    since = (now - dt.timedelta(days=REPEAT_DAYS)).strftime("%Y-%m-%d")
    out = sorted(((r["tripped"], g) for g, r in st_["goals"].items() if (r.get("tripped") or "") >= since and not r.get("go")), reverse=True)
    return [g for _, g in out]


def _goal_words(st_: dict, g: str) -> str:
    return next((r["spec"]["goal"] for r in st_["steps"].values() if _norm_goal((r.get("spec") or {}).get("goal", "")) == g), g)


def _waiting_for_word(aid: str, now: dt.datetime) -> bool:
    st_ = _agent_state(_state(), aid)
    return bool(st_["holds"] or _held_goals(st_, now))


def _cant_run(aid: str, now: dt.datetime, base: Path | None) -> str | None:
    """Why a small step of hers can't run now, in plain words, or None."""
    a = agent_settings(aid, base)
    lo, hi = a.get("hours") or ["08:00", "22:00"]
    if not in_hours(a, now):
        return f"nothing of {aid}'s runs until {lo}"
    if hi != "23:59" and _minutes_left(a, now) < a["step"]["minutes"]:
        return f"the day's hours are nearly over, so it's the first thing at {lo}"
    try:
        import usagecost
        price = float(usagecost.cost_for(a["step"]["minutes"], "", f"step-{aid}").get("weekly") or 0)
    except Exception:
        price = 0.0
    sh = shares(aid, now, base)
    if over_share(sh, price):
        return f"her share of the usage is used up for now ({sh['daily_used']:g} of {sh['daily_share']:g} today, {sh['weekly_used']:g} of {sh['weekly_share']:g} this week)"
    return None


def _answer_order(aid: str, o: dict, now: dt.datetime, base: Path | None, now_: bool = False) -> str:
    """His words about what waits for his word: a small step of hers reads them."""
    why = _cant_run(aid, now, base)
    with held() as d:
        _agent_state(d, aid)["order_steps"][str(o["n"])] = {"kind": "answer", "now": now_}
    if why:
        ledger.set_order(aid, o["n"], "now", f"waits: {why}")
        return f"Kept: {why}. She reads it as soon as she can. Tell him so."
    _order_step(aid, o, now, base, answer=True, now_flag=now_)
    return f"She has it, in his words: \"{o['words']}\". She looks at what's waiting for his word and does what he means, or asks."


def _rec_of_run(st_: dict, aid: str) -> dict | None:
    run = _this_run()
    return st_["steps"].get(_step_key(run)) if run and run["kind"] == "step" and run["agent"] == aid else None


def open_hold(aid: str, n: int, now: dt.datetime | None = None, base: Path | None = None) -> str:
    """A run reading his words says which question his yes is for. Only a run that was given his words can."""
    now = now or dt.datetime.now()
    with held() as d:
        st_ = _agent_state(d, aid)
        rec = _rec_of_run(st_, aid)
        if not rec or not (rec.get("spec") or {}).get("answer"):
            return "Refused: only a run reading his own words can open a question."
        h = next((x for x in st_["holds"] if x["n"] == n), None)
        if not h:
            return f"No question {n} is waiting."
        if _SAYS_NO.match(re.sub(r"^He said (?:yes|no) \(", "", rec["spec"].get("words", ""))):
            return f"Refused: his words open with no, so nothing opens: python3 cycles.py close {aid} {n} if they're about this one, or ask."
        rec["state"] = "done"
        ledger.set_order(aid, rec["order"], "planned", f"question {n}")
        return _opened(aid, st_, h, rec["spec"].get("words", ""), rec["order"], now, base) + " A step of yours makes the call, not this run: end here."


def go_on(aid: str, n: int, now: dt.datetime | None = None, base: Path | None = None) -> str:
    """A run reading his words says go on held goal n: it may be planned once more; with his now, at once."""
    now = now or dt.datetime.now()
    with held() as d:
        st_ = _agent_state(d, aid)
        rec = _rec_of_run(st_, aid)
        if not rec or not (rec.get("spec") or {}).get("answer"):
            return "Refused: only a run reading his own words can say go."
        goals = rec["spec"].get("goals") or []
        if not 1 <= n <= len(goals):
            return f"No goal {n} is waiting."
        g = _norm_goal(goals[n - 1])
        st_["goals"].setdefault(g, {})["go"] = True
        for q_ in ("batch", "later"):
            st_[q_] = [e for e in st_[q_] if goals[n - 1] not in e["text"] and not e.get("which")]
        rec["state"] = "done"
        ledger.note(aid, f"he says go on, once more: {goals[n - 1]}")
        if rec["spec"].get("now"):
            ledger.set_order(aid, rec["order"], "planned", f"he says go on: {goals[n - 1]}")
            return _order_step(aid, {"n": rec["order"], "words": goals[n - 1]}, now, base, goal=goals[n - 1])
        ledger.set_order(aid, rec["order"], "open", f"he says go on: {goals[n - 1]}")
    return f"Go: \"{goals[n - 1]}\" goes in your next plan, once more. That's all this run does: end here."


def _stop_order(aid: str, o: dict, now: dt.datetime, base: Path | None) -> str:
    """His stop, in his words, goes to her in a small step: she knows what he means, a word match doesn't (5 of 9 natural orders matched nothing). Till that step
    has run nothing else of hers starts; one step that's running ends now: a step is small, and a stop must stop. It can't run now: he's told, and it runs when it can."""
    _, jobs_ = _items()
    n = 0
    for j in jobs_:
        p = parse(j["text"])
        if j["state"].startswith("running") and p["agent"] == aid and p["kind"] == "step":
            _jobs("stop", str(j["n"]))
            n += 1
    with held() as d:
        st_ = _agent_state(d, aid)
        st_["stopping"][str(o["n"])] = now.strftime(FMT)
        st_["order_steps"][str(o["n"])] = {"kind": "stop"}
    ledger.note(aid, f"stop order: \"{o['words']}\"" + (f"; the step that was running ended ({n})" if n else ""))
    why = _cant_run(aid, now, base)
    if why:
        ledger.set_order(aid, o["n"], "now", f"waits: {why}")
        return f"Kept, not done yet: {why}. It's the first thing she does when she can, and nothing else of hers starts before it. Tell him so."
    _order_step(aid, o, now, base, stop=True)
    return f"She has it, in his words: \"{o['words']}\". She stops what he means and tells him what she stopped; nothing else of hers starts first."


def stops_alive(now: dt.datetime, base: Path | None = None) -> None:
    """A stop that lost its step (she was switched off, it was cancelled) doesn't block her for good: it runs again; a day old, he's told and it's dropped."""
    items, jobs_ = _items()
    live = {(p["agent"], p["stamp"], p["k"]) for p in (parse(x["text"]) for x in [i for i in items if i["state"] == "waiting"] + [j for j in jobs_ if not j["state"].startswith(("done", "stopped", "ended", "cancelled"))]) if p and p["kind"] == "step"}
    with held() as d:
        for aid, a in settings(base)["agents"].items():
            if not a.get("on"):
                continue
            st_ = _agent_state(d, aid)
            for n, ts in list(st_["stopping"].items()):
                orders_ = {str(o["n"]): o for o in ledger.orders(aid)}
                o = orders_.get(n)
                has_step = any(k[0] == aid and (st_["steps"].get(f"{aid}|{k[1]}|{k[2]}") or {}).get("order") == int(n) for k in live)
                old = dt.datetime.strptime(ts, FMT) < now - dt.timedelta(hours=24)
                if o is None or (old and not has_step):
                    st_["stopping"].pop(n)
                    if o is not None:
                        ledger.set_order(aid, int(n), "dropped", "a day old and never run")
                        say(aid, f"I couldn't act on your stop, \"{o['words']}\". If it still stands, say it again.", "cycle", now, base)
                elif not has_step and o["state"] != "now":
                    ledger.set_order(aid, int(n), "now", "back: her step for it was gone")


def planned_steps(aid: str) -> list[dict]:
    """Her steps still to come: [{"k", "goal", "at"}], the running one left out."""
    items, jobs_ = _items()
    st_ = _agent_state(_state(), aid)
    out = []
    for x in [i for i in items if i["state"] == "waiting"] + [j for j in jobs_ if j["state"] == "ready" or j["state"].startswith("held")]:
        p = parse(x["text"])
        if p["agent"] == aid and p["kind"] == "step":
            rec = st_["steps"].get(_step_key(p)) or {}
            if not rec.get("stop"):
                out.append({"k": p["k"], "goal": (rec.get("spec") or {}).get("goal") or p.get("goal", ""), "at": x.get("at") or "on the queue"})
    return out


def stop_step(aid: str, k: int, why: str, now: dt.datetime | None = None, base: Path | None = None) -> str:
    """Her stop run stops her step k: off the schedule or the queue, marked stopped, so a next plan leaves it out too."""
    now = now or dt.datetime.now()
    items, jobs_ = _items()
    n = 0
    with held() as d:
        st_ = _agent_state(d, aid)
        for x, cancel in [(i, lambda i_: _schedule("cancel", str(i_["n"]))) for i in items if i["state"] == "waiting"] + [(j, lambda j_: _jobs("stop", str(j_["n"]))) for j in jobs_ if j["state"] == "ready" or j["state"].startswith(("held", "running"))]:
            p = parse(x["text"])
            if p["agent"] == aid and p["kind"] == "step" and p["k"] == k and not (st_["steps"].get(_step_key(p)) or {}).get("stop"):
                cancel(x)
                rec = st_["steps"].get(_step_key(p))
                if rec is not None:
                    rec["state"] = "stopped"
                n += 1
        if n:
            ledger.note(aid, f"let go, on his order: step {k} stopped: {why}")
    return f"Step {k} is stopped." if n else f"No step {k} is planned; nothing stopped."


def drop_text(aid: str, n: int, base: Path | None = None) -> str:
    """Her stop run drops a queued text: number n of her queue as the prompt showed it."""
    with held() as d:
        st_ = _agent_state(d, aid)
        q_ = st_["batch"] + st_["later"]
        if not 1 <= n <= len(q_):
            return f"No queued text {n}."
        e = q_[n - 1]
        (st_["batch"] if n <= len(st_["batch"]) else st_["later"]).remove(e)
        rec = _rec_of_run(st_, aid)
        ledger.note(aid, f"queued text dropped{', on his order' if rec and rec.get('stop') else ''}: {e['text'][:120]}")
    return f"Queued text {n} is dropped."


def stopped(aid: str, what: str, now: dt.datetime | None = None, base: Path | None = None) -> str:
    """She says what she stopped: the order is done, one short text, whatever the day's count says: he's waiting for it."""
    now = now or dt.datetime.now()
    what = " ".join(str(what).split())
    if not what:
        return "Say what you stopped."
    run = _this_run()
    with held() as d:
        st_ = _agent_state(d, aid)
        rec = st_["steps"].get(_step_key(run)) if run and run["kind"] == "step" else None
        n = (rec or {}).get("order")
        if rec is not None:
            rec["state"] = "done"
            st_["stopping"].pop(str(n), None)
        if n:
            ledger.set_order(aid, n, "done", what)
        ledger.note(aid, f"stopped, on his order: {what}")
        say(aid, what, "cycle", now, base)
    return "Said, and written in your ledger."


def hold(aid: str, key: str, what: str, why: str, tool: str = "", inp: dict | None = None, now: dt.datetime | None = None, base: Path | None = None) -> str:
    """A calendar change the hook held: all of it kept, with a short number and its title, and the question goes to him however many she asked today. One change, one question."""
    now = now or dt.datetime.now()
    with held() as d:
        st_ = _agent_state(d, aid)
        if any(h["key"] == key for h in st_["holds"]) or st_["closed"].get(key, "") >= (now - dt.timedelta(days=REPEAT_DAYS)).strftime(FMT):
            return "already"
        used_ = {h["n"] for h in st_["holds"]}
        n = next(i for i in range(1, len(used_) + 2) if i not in used_)
        st_["holds"].append({"n": n, "key": key, "what": what, "why": why, "tool": tool, "input": inp or {}, "at": now.strftime(FMT)})
        ledger.note(aid, f"held, asked him first ({n}): {what} ({why})")
        ask(aid, f"({n}) If you want me to {what}, say yes and I'll do it; if not, I leave it. {why[0].upper() + why[1:]}.", now, base, must=True)
    return "asked"


def _answered(st_: dict, h: dict) -> None:
    """He answered: the question is off the list, and neither it nor her "which one do you mean" goes out at the next batch."""
    st_["holds"].remove(h)
    for q_ in ("batch", "later"):
        st_[q_] = [e for e in st_[q_] if h["what"] not in e["text"] and not e.get("which")]


_JUST_AN_ANSWER = {_stem(w) for w in ("yep", "yeah", "yea", "sure", "fine", "good", "great", "right", "correct", "thanks", "sounds", "nah", "nope", "forget", "never", "mind", "one", "do", "did")}


def _names_else(words: str, h: dict) -> bool:
    """Even with one waiting: his words name something, and not this: "yes the call" with only a lunch left isn't a yes to the lunch."""
    named = _meant(words) - _JUST_AN_ANSWER
    return bool(named) and not named & _meant(h["what"])


def _closed(aid: str, st_: dict, h: dict, words: str, now: dt.datetime) -> str:
    """His no: the question is closed: a later yes can't open it, and the same change isn't asked again for a week."""
    _answered(st_, h)
    st_["closed"] = {k: v for k, v in st_["closed"].items() if v >= (now - dt.timedelta(days=REPEAT_DAYS)).strftime(FMT)}
    st_["closed"][h["key"]] = now.strftime(FMT)
    ledger.note(aid, f"closed on his no ({words}): {h['what']}")
    return f"No: closed: {h['what']}. Nothing goes out, and a later yes can't open it."


def no(aid: str, words: str, n: int | None = None, now: dt.datetime | None = None, base: Path | None = None) -> str:
    """His no to a held change, from a text, a call or his words to her. His number, or the only one waiting, closes it. Several and no number: his words go to her, the same way a yes does."""
    now = now or dt.datetime.now()
    st0 = _agent_state(_state(), aid)
    if not st0["holds"]:
        return f"{aid} has no change waiting for an answer."
    if n is None and (len(st0["holds"]) > 1 or _names_else(words, st0["holds"][0])):
        o = ledger.add_order(aid, "start", f"He said no ({words})", True, now)
        return _answer_order(aid, o, now, base)
    with held() as d:
        st_ = _agent_state(d, aid)
        h = next((x for x in st_["holds"] if n is None or x["n"] == n), None)
        if not h:
            return f"No question {n} is waiting. Waiting: " + "; ".join(f"{x['n']}: {x['what']}" for x in st_["holds"])
        return _closed(aid, st_, h, words, now)


def close_hold(aid: str, n: int, now: dt.datetime | None = None, base: Path | None = None) -> str:
    """A run reading his words closes the question they say no to. Only a run that was given his words can."""
    now = now or dt.datetime.now()
    with held() as d:
        st_ = _agent_state(d, aid)
        rec = _rec_of_run(st_, aid)
        if not rec or not (rec.get("spec") or {}).get("answer"):
            return "Refused: only a run reading his own words can close a question."
        h = next((x for x in st_["holds"] if x["n"] == n), None)
        if not h:
            return f"No question {n} is waiting."
        rec["state"] = "done"
        ledger.set_order(aid, rec["order"], "done", f"question {n} closed on his no")
        return _closed(aid, st_, h, rec["spec"].get("words", ""), now) + " That's all this run does: end here."


def _opened(aid: str, st_: dict, h: dict, words: str, order_n: int, now: dt.datetime, base: Path | None) -> str:
    """His yes on one held change: it may go through, exactly as it was held, once, for two days. A step does it, with its one tool."""
    _answered(st_, h)
    st_["allowed"][h["key"]] = (now + dt.timedelta(days=2)).strftime(FMT)
    st_["order_steps"][str(order_n)] = {"kind": "yes", "hold": h, "words": words}
    why = _cant_run(aid, now, base)
    if why:
        ledger.set_order(aid, order_n, "now", f"his yes waits: {why}")
        return f"Yes, on {h['what']}. {why[0].upper() + why[1:]}, and then she does it."
    _order_step(aid, {"n": order_n, "words": words}, now, base, yes=h, words=words)
    return f"Yes: she does it now: {h['what']}."


def his_yes_refused(aid: str, words: str, n: int | None = None, places: list | None = None, base: Path | None = None) -> str:
    """F114: why WORDS don't stand as his yes to her held change, or "". They must be a line he said or typed himself, today, in this
    call or this chat (PLACES, else HQ_WORDS_FROM, which the session sets for its tools; by hand, any of today's), the program's own lines
    (a transcript or a thread, never an agent's line or a quick note), read as a yes, and fit the change: his line, or her question just
    before it, names it (its title's words), as the yes step does when several wait. Words that open with no aren't a yes at all: they go
    to no() as before. Never from a run of hers or a job."""
    if _SAYS_NO.match(words or ""):
        return ""
    if os.environ.get("HQ_IN_JOB"):
        return "a run can't give a yes"
    waiting = _agent_state(_state(), aid)["holds"]
    holds = [h for h in waiting if n is None or h["n"] == n]
    if not holds and places is None:
        return ""  # run by itself with nothing waiting: yes() says so itself
    import sprint
    import hqpaths as _hp
    if _hp.under_test() and not os.environ.get("HQ_PROOF_ON"):  # a test copy without lines of his, as sprint.his_quote
        return ""
    hits = sprint.his_said_now(words, str(base or folder()), places if places is not None else sprint.words_from_env())
    if not hits:
        return "those aren't his words from this call or this chat, today"
    if not any(sprint.a_yes(h["line"], h["turn"]) for h in hits):
        return "those are his words, but they aren't a clear yes"
    if not holds:
        return ""  # his words, and nothing waits: yes() says so
    for h in hits:  # F114, the second check: only by its own words, and only when that's the one change his line and her question name
        if sprint.a_yes(h["line"], h["turn"]):
            named = [x for x in waiting if yes_fits(h["line"] + " " + h["turn"], x)]
            if len(named) == 1 and named[0] in holds:
                return ""
    return ("those are his words, but they don't name this one change by its own words (or name more than one), and neither does her "
            "question before them: ask him again by its name")


def his_yes_line(words: str, base: Path | None = None) -> tuple[str, dict | None]:
    """F115 with F114: on the backup, the first checks of his yes, whatever its own copy of the holds says: his own line, today, in this
    call or this chat (or by hand, any of today's), read as a yes. (why, his line) — why is "" when it stands; the line is None when there's
    none to carry (a test copy without lines of his). The fit to a change is the main's to check, against its own holds."""
    if _SAYS_NO.match(words or ""):
        return "", None
    if os.environ.get("HQ_IN_JOB"):
        return "a run can't give a yes", None
    import sprint
    import hqpaths as _hp
    if _hp.under_test() and not os.environ.get("HQ_PROOF_ON"):
        return "", None
    hits = sprint.his_said_now(words, str(base or folder()), sprint.words_from_env())
    if not hits:
        return "those aren't his words from this call or this chat, today", None
    yes_ = [h for h in hits if sprint.a_yes(h["line"], h["turn"])]
    if not yes_:
        return "those are his words, but they aren't a clear yes", None
    return "", yes_[0]


def handed_yes_refused(aid: str, d: dict, n: int | None = None) -> str:
    """F115 with F114: on the main, a yes the backup checked: does his line (or her question just before it) name exactly one of the
    main's own holds by its own words? "" when it does, or when nothing waits (yes() says so), or for a test copy without lines of his."""
    waiting = _agent_state(_state(), aid)["holds"]
    holds = [h for h in waiting if n is None or h["n"] == n]
    if not waiting:
        return ""
    if not d.get("line"):
        import hqpaths as _hp
        if _hp.under_test() and not os.environ.get("HQ_PROOF_ON"):
            return ""
        return "the other computer sent no line of his to fit to a change"
    named = [x for x in waiting if yes_fits(d["line"] + " " + (d.get("turn") or ""), x)]
    if len(named) == 1 and named[0] in holds:
        return ""
    return ("those are his words, but they don't name this one change by its own words (or name more than one), and neither does her "
            "question before them: ask him again by its name")


# F114, the second check: words a title shares with any ordinary sentence ("I'll sort it on this call"), which never name a change alone.
_COMMON = {_stem(w) for w in ("call", "calls", "lunch", "dinner", "breakfast", "drinks", "coffee", "meeting", "meet", "appointment", "event",
                               "today", "tonight", "tomorrow", "this", "that", "next", "week", "weekend", "morning", "afternoon", "evening",
                               "night", "noon", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "with",
                               "time", "hour", "block", "slot", "add", "put", "move", "change", "remove", "plan", "book", "chat", "talk",
                               "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")}


def title_words(h: dict) -> set:
    """F114: a held change's own words: its title's (what's in quotes in its line, else the line), not the common ones."""
    title = " ".join(re.findall(r"\"([^\"]+)\"", h.get("what") or "")) or (h.get("what") or "")
    return _meant(title) - _COMMON


def yes_fits(said: str, h: dict) -> bool:
    """F114: these words name this held change by one of its own words (title_words), never by a common word like call or lunch."""
    return bool(_meant(said) & title_words(h))


_SAYS_NO = re.compile(r"\s*(?:no|nope|nah|nee|don'?t|do not|never mind|nevermind|cancel that|not that)\b", re.I)


def yes(aid: str, words: str, n: int | None = None, now: dt.datetime | None = None, base: Path | None = None) -> str:
    """His yes to a held calendar change. His number, or the only one waiting, opens it. Several and no number: his words go to her, and if it isn't clear which she asks. Never the newest by default."""
    now = now or dt.datetime.now()
    if _SAYS_NO.match(words):  # words that open with no never open anything: "no, forget the call" isn't a yes to removing it
        return no(aid, words, n, now, base)
    st0 = _agent_state(_state(), aid)
    if not st0["holds"]:
        return f"{aid} has no change waiting for a yes."
    o = ledger.add_order(aid, "start", f"He said yes ({words})", True, now)
    if n is None and (len(st0["holds"]) > 1 or _names_else(words, st0["holds"][0])):
        return _answer_order(aid, o, now, base)
    with held() as d:
        st_ = _agent_state(d, aid)
        h = next((x for x in st_["holds"] if n is None or x["n"] == n), None)
        if not h:
            ledger.set_order(aid, o["n"], "dropped", f"no question {n}")
            return f"No question {n} is waiting. Waiting: " + "; ".join(f"{x['n']}: {x['what']}" for x in st_["holds"])
        return _opened(aid, st_, h, words, o["n"], now, base)


def _order_step(aid: str, o: dict, now: dt.datetime, base: Path | None, goal: str | None = None, stop: bool = False, answer: bool = False, yes: dict | None = None,
                words: str = "", now_flag: bool = False, look: str = "") -> str:
    """His "now": a small step at once, inside her box. goal: what it says go on. stop: his stop order, to act on. answer: his words about what waits for his word. yes: the one held change he said yes to."""
    label = f"his stop order: {o['words']}" if stop else f"his words: {o['words']}" if answer else f"he said yes: {yes['what']}" if yes else (goal or o["words"])
    stamp = now.strftime("%Y-%m-%d %H:%M")
    hi = agent_settings(aid, base)["hours"][1]
    with held() as d:
        st_ = _agent_state(d, aid)
        k = 0
        while f"{aid}|{stamp}|{k}" in st_["steps"]:
            k = max(k, 99) + 1
        spec = {"goal": label, "done_means": "what he asked for is done, or put to him as a question", "inputs": [], "may": "one look or one action inside your limits", "at": now.strftime("%H:%M")}
        if not (stop or answer or yes):
            spec["order"] = o["n"]  # F105
        if stop:
            spec["words"] = o["words"]
        if answer:
            spec.update(answer=True, words=o["words"], now=now_flag, goals=[_goal_words(st_, g) for g in _held_goals(st_, now)])
        if yes:
            spec["yes"] = {**{k_: yes[k_] for k_ in ("n", "key", "what", "why", "tool", "input")}, "words": words}
        st_["steps"][f"{aid}|{stamp}|{k}"] = {"spec": spec, "fps": [], "day": now.strftime("%Y-%m-%d"), "state": "planned", "stamp": stamp, "order": o["n"], **({"stop": True} if stop else {}),
                                             "until": _shift_end(agent_settings(aid, base), now).strftime(FMT)}
        code, out = _schedule("add", "now", step_text(aid, stamp, k, label), "--priority", "--kind", f"step-{aid}")
        item = re.match(r"Item (\d+)\b", out or "")
        if look:  # H308: the order carries its item's label, so a later or a doubled look makes no second one
            st_["steps"][f"{aid}|{stamp}|{k}"]["look"] = look
        ledger.set_order(aid, o["n"], "planned", (f"item {item.group(1)}, step #{k}, from her {look}" if item else f"step #{k}, from her {look}") if look else "a step at once")
    return f"Now: a step for {aid} planned at once ({out.splitlines()[0][:100] if out else code})."


# -- her looks at her own list (H308) -----------------------------------------------------------------------------------------

def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def look_times(a: dict) -> list[list]:
    """Her looks at her own list in a day, [[name, "HH:MM"], ...]: looks_a_day of them inside her hours, the first an hour
    after they start, the last three hours before they end, the rest evenly between (hours 8:00 to 22:00 and three looks:
    9:00, 14:00 and 19:00). Hours too short for that: evenly inside them. [The times are the builder's pick.]"""
    n = max(0, min(int(a.get("looks_a_day", 3) or 0), LOOKS_MOST))
    if not n:
        return []
    lo, hi = a.get("hours") or ["08:00", "22:00"]
    lo_m, hi_m = _mins(lo), _mins(hi)
    if hi_m <= lo_m:  # H340: hours past midnight count on into the next morning
        hi_m += 24 * 60
    first, last = lo_m + 60, hi_m - 180
    if last <= first:
        ts = [lo_m + (hi_m - lo_m) * (2 * i + 1) // (2 * n) for i in range(n)]
    elif n == 1:
        ts = [(first + last) // 2]
    else:
        ts = [first + (last - first) * i // (n - 1) for i in range(n)]
    ts = sorted({max(lo_m, t - t % 5) for t in ts})
    names = {1: ["midday look"], 2: ["morning look", "evening look"], 3: ["morning look", "midday look", "evening look"]}.get(len(ts)) \
        or [f"look {i + 1} of {len(ts)}" for i in range(len(ts))]
    return [[names[i], f"{t // 60 % 24:02d}:{t % 60:02d}"] for i, t in enumerate(ts)]


def _day_looks(st_: dict, a: dict, now: dt.datetime) -> dict:
    """Today's looks, fixed at the day's first minute: a change to looks_a_day or her hours counts from the next day."""
    today = now.strftime("%Y-%m-%d")
    ld = st_.get("looks_day") or {}
    if ld.get("day") != today:
        ld = st_["looks_day"] = {"day": today, "times": look_times(a), "done": []}
    return ld


def next_look(aid: str, now: dt.datetime | None = None, base: Path | None = None) -> tuple[str, dt.datetime] | None:
    """Her next look at her own list: (its name, when), today's if one is still to come, else tomorrow's first."""
    now = now or dt.datetime.now()
    a = agent_settings(aid, base)
    hm = now.strftime("%H:%M")
    d = getattr(_tls, "d", None) or _state()  # a read: nothing written (inside the lock, what's held)
    ld = ((d.get("agents") or {}).get(aid) or {}).get("looks_day") or {}
    if ld.get("day") != now.strftime("%Y-%m-%d"):
        ld = {"times": look_times(a), "done": []}
    for name, t in ld["times"]:
        if t >= hm and t not in ld["done"]:
            return name, now.replace(hour=_t(t).hour, minute=_t(t).minute, second=0, microsecond=0)
    tm = look_times(a)
    if not tm:
        return None
    return tm[0][0], (now + dt.timedelta(days=1)).replace(hour=_t(tm[0][1]).hour, minute=_t(tm[0][1]).minute, second=0, microsecond=0)


def _step_price(aid: str, a: dict) -> float:
    try:
        import usagecost
        return float(usagecost.cost_for(a["step"]["minutes"], "", f"step-{aid}").get("weekly") or 0)
    except Exception:
        return 0.0


def _take_orders(aid: str, a: dict, look: str, upto: str, now: dt.datetime, base: Path | None) -> list[str]:
    """A look reads her own list first: every new order on it up to `upto` ("YYYY-MM-DD HH:MM") becomes its step, at once,
    as many as fit her share; the order then carries its item's label. An order that has had a step is never made one again
    here (a held or skipped one is her next bigger session's). What doesn't fit waits for her next look, and her ledger says
    so, with the room it needed."""
    did = []
    with held() as d:
        st_ = _agent_state(d, aid)
        had = {str(r.get("order")) for r in st_["steps"].values() if r.get("order")}
        live = d.get("looks_live")  # an order from before the looks went live stays for her bigger session
        if not live:
            return did
        todo = [o for o in ledger.orders(aid, ("open",)) if o["kind"] == "start" and live < o["at"] <= upto and str(o["n"]) not in had
                and not ledger.LOOK_LABEL.match(o.get("note") or "")]
        if not todo:
            return did
        price = _step_price(aid, a)
        sh = shares(aid, now, base)
        lo, hi = a.get("hours") or ["08:00", "22:00"]
        why = None
        if not in_hours(a, now) or (hi != "23:59" and _minutes_left(a, now) < a["step"]["minutes"]):
            why = f"the day's hours end at {hi}; nothing of hers runs at night"
        took = 0
        for o in todo:
            why = why or over_share(sh, price * (took + 1))
            if why:
                break
            _order_step(aid, o, now, base, look=look)
            took += 1
            did.append(f"{aid}'s {look}: her order {o['n']} is a step")
        left = len(todo) - took
        if left:
            nx = next_look(aid, now + dt.timedelta(minutes=1), base)
            ledger.entry(aid, f"{look} waits", [f"waits: {why}",
                                               f"the room it needed: about {price * left:g} points, for {left} order{'s' if left > 1 else ''} on her list",
                                               f"her {nx[0]} ({nx[1]:%A %H:%M}) looks again" if nx else "her next bigger session reads them"], now)
            did.append(f"{aid}'s {look} waits: {why}")
    return did


def list_looks(now: dt.datetime | None = None, base: Path | None = None, log=None) -> list[str]:
    """H308: every agent looks at her own list a few times a day (looks_a_day, three by default: morning, midday, evening),
    so what he hands over is picked up the same day and not at her bigger session. A look is the routine's, no run of a model:
    it turns the new orders into their steps, and each step runs through her wall like any other."""
    now = now or dt.datetime.now()
    did = []
    hm = now.strftime("%H:%M")
    if not on(base):
        return did
    with held() as d:
        d.setdefault("looks_live", now.strftime(FMT))  # the first minute the looks run with the switch on
    for aid, a in settings(base)["agents"].items():
        if not a.get("on") or not _agent(aid, base):
            continue
        with held() as d:
            ld = _day_looks(_agent_state(d, aid), a, now)
            due = [x for x in ld["times"] if x[1] <= hm and x[1] not in ld["done"]]
            if not due:
                continue
            ld["done"] = ld["done"] + [x[1] for x in due]  # marked first: a doubled minute finds it done
            name, t = due[-1]
            did += _take_orders(aid, a, f"{name} at {t}", f"{ld['day']} {t}", now, base)
    if log:
        for x in did:
            log(f"cycles: {x}")
    return did


def waiting_orders(now: dt.datetime | None = None, base: Path | None = None, log=None) -> list[str]:
    """What he said that couldn't run when he said it runs as soon as it can: outside her hours, near their end, over her share. A stop that lost its step comes back here too."""
    now = now or dt.datetime.now()
    stops_alive(now, base)
    did = []
    for aid, a in settings(base)["agents"].items():
        if not a.get("on") or not _agent(aid, base):
            continue
        for o in ledger.orders(aid, ("now",)):
            if _cant_run(aid, now, base):
                break
            with held() as d:
                os_ = _agent_state(d, aid)["order_steps"].get(str(o["n"])) or {}
            kind = "stop" if o["kind"] == "stop" else os_.get("kind")
            if kind == "yes":
                _order_step(aid, {"n": o["n"], "words": os_.get("words", "")}, now, base, yes=os_["hold"], words=os_.get("words", ""))
            else:
                _order_step(aid, o, now, base, stop=kind == "stop", answer=kind == "answer", now_flag=os_.get("now", False))
            did.append(f"{aid}'s order of {o['at']} planned")
    if log:
        for x in did:
            log(f"cycles: {x}")
    return did


# -- the monthly review (piece 9) and the weekly score ------------------------------------------------------------------------------

def first_friday(after: dt.datetime) -> dt.datetime:
    d = (after.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    while d.weekday() != 4:
        d += dt.timedelta(days=1)
    this = after.replace(day=1)
    while this.weekday() != 4:
        this += dt.timedelta(days=1)
    return this if this.date() > after.date() else d


def plan_reviews(now: dt.datetime | None = None, base: Path | None = None, log=None) -> list[str]:
    """Each agent that's on gets her monthly review planned once for the coming first Friday (a one-off priority
    item), when none is waiting."""
    now = now or dt.datetime.now()
    s = settings(base)
    r = s.get("review") or {}
    items, _ = _items()
    did = []
    for aid, a in s["agents"].items():
        if not a.get("on") or not _agent(aid, base):
            continue
        text = cycle_text(aid, "monthly review")
        mine = [i for i in items if i["state"] == "waiting" and i["text"] == text]
        for i in mine:  # H340: one planned outside her hours (they changed) moves into them
            if not in_hours(a, dt.datetime.strptime(i["at"], FMT)):
                _schedule("cancel", str(i["n"]))
                did.append(f"{aid}'s monthly review (item {i['n']}) was outside her hours")
        if any(in_hours(a, dt.datetime.strptime(i["at"], FMT)) for i in mine):
            continue
        ff = first_friday(now)
        rt = r.get("at", "09:00") if _at_hour(a, r.get("at", "09:00")) else a["hours"][0]  # H340: the review's time, else her hours' start
        at = ff.replace(hour=_t(rt).hour, minute=_t(rt).minute, second=0, microsecond=0)
        code, out = _schedule("add", at.strftime(FMT), text, "--priority", "--kind", f"cycle-{aid}")
        did.append(f"{aid}'s monthly review planned for {at:%A %-d %B %H:%M}")
    if log:
        for x in did:
            log(f"cycles: {x}")
    return did


def proposal(aid: str, text: str, now: dt.datetime | None = None, base: Path | None = None) -> str:
    now = now or dt.datetime.now()
    text = " ".join(str(text).split())
    if not text:
        return "A proposal needs words."
    ledger.entry(aid, "monthly review: proposal", [text], now)
    how = say(aid, "My monthly review, for your yes or no (nothing changed by itself): " + text, "cycle-review", now, base)
    return f"Proposal written in {aid}'s ledger and {'sent on her line' if how == 'sent' else 'waiting for him to wake up'}; nothing changed."


def write_scores(now: dt.datetime | None = None, base: Path | None = None, force: bool = False, log=None) -> list[str]:
    """Every week (Friday from 7 in the morning, once), each agent's score into her ledger. F103: on the maker's HQ whatever the
    agents' switch says. Harm 14: a friend who never turned it on gets nothing written: no ledger, no state."""
    now = now or dt.datetime.now()
    import pokes
    week = (now - dt.timedelta(days=1)).strftime("%G-W%V")
    did = []
    if not force and not (now.weekday() == 4 and now.hour >= 7):
        return did
    if not on(base) and not hqpaths.is_maker():
        return did
    with held() as d:
        for ag in _agents(base):
            aid = ag["id"]
            st_ = _agent_state(d, aid)  # F103: whatever the agents' switch says, the score is written (C69)
            if st_.get("scored") == week and not force:
                continue
            sc = pokes.score(ag, now, folder=base or folder(), plan=ledger.plan(aid)[1])
            ledger.write_score(aid, week, {"pokes": sc["pokes"], "measures": sc["measures"]}, sc["lines"], now)
            st_["scored"] = week
            did.append(f"{aid}'s score for {week} written")
    if log:
        for x in did:
            log(f"cycles: {x}")
    return did


# -- the routine's minute --------------------------------------------------------------------------------------------------------

def finished_cycle_jobs() -> list[tuple[dict, dict]]:
    import jobs as q
    _, jobs_, _ = q.read()
    out = []
    for j in jobs_:
        p = parse(j["text"])
        if p and j["state"].startswith(q.FINISHED + ("paused",)):  # a paused run of hers is over: it isn't resumed
            out.append((j, p))
    return out


def settle(now: dt.datetime | None = None, base: Path | None = None, log=None) -> list[int]:
    done = []
    for j, p in finished_cycle_jobs():
        if after_run(j, p, now, base, log=log):
            done.append(j["n"])
    return done


def drop_waiting(now: dt.datetime | None = None, base: Path | None = None, log=None) -> list[str]:
    """At the hours' end, a cycle job still waiting on the queue is dropped to the morning (gatekeep says how)."""
    now = now or dt.datetime.now()
    import jobs as q
    _, jobs_, _ = q.read()
    did = []
    for j in jobs_:
        p = parse(j["text"])
        if p and (j["state"] == "ready" or j["state"].startswith("held")):
            a = agent_settings(p["agent"], base)
            if not in_hours(a, now) and next_start(a, now).date() != now.date():
                gatekeep(j, now, base, log)
                did.append(f"job {j['n']} dropped at the hours' end")
    return did


def fix_name(base: Path | None = None) -> str:
    """Her name as his HQ has it, for the mark on what she adds."""
    return (_agent(FIX_AGENT, base) or {}).get("name") or FIX_AGENT.capitalize()


def _round_points(base: Path | None = None) -> float:
    """What a round may cost in points of the weekly limit: her step's box at the rate of her own steps."""
    try:
        import usagecost
        c = usagecost.cost_for(agent_settings(FIX_AGENT, base)["step"]["minutes"], "", f"step-{FIX_AGENT}")
        return float(c.get("weekly") or 0)
    except Exception:
        return 0.0


def fix_rounds(now: dt.datetime | None = None, base: Path | None = None, log=None) -> list[str]:
    """F86: the next round of the fix-and-review loop: one at a time, in her hours, and only when it fits under her
    share of the day and the week; else it waits for the next day's share, named once a day in her ledger. Skipped
    while the loop's switch (`set moneypenny fix on`) is off."""
    now = now or dt.datetime.now()
    aid = FIX_AGENT
    a = agent_settings(aid, base)
    if not a.get("on") or not a.get("fix") or not in_hours(a, now) or _minutes_left(a, now) < a["step"]["minutes"] or not _agent(aid, base):
        return []
    import jobs as q
    import review
    if not review.on():  # the review isn't looking (switched off, or everything is paused): a round's words would wait for nobody
        return []
    items, jobs_ = _items()
    is_fix = lambda x: (parse(x["text"]) or {}).get("kind") == "fix"  # noqa: E731
    if any(is_fix(i) and i["state"] == "waiting" for i in items) or any(is_fix(j) and not j["state"].startswith(q.FINISHED) for j in jobs_):
        return []
    got = review.next_round(now.timestamp())
    did = []
    for label in got["capped"]:
        ledger.note(aid, f"{label} on the sit-down list: {review.ROUNDS} rounds and the review still flags it")
        ask(aid, f"If you tell me what {label} should say, I'll write it in and the review looks again; if not, it stays on my list for Friday.")  # F101 (C36)
        did.append(f"{label} went on the sit-down list")
    pick = got["pick"]
    if not pick:
        return did
    sh, est = shares(aid, now, base), _round_points(base)
    if over_share(sh, est):
        with held() as d:
            st_ = _agent_state(d, aid)
            if st_.get("fix_waits") != _today(now):
                st_["fix_waits"] = _today(now)
                ledger.note(aid, f"{pick['label']} waits for the next day's share ({sh['daily_used']:g} of {sh['daily_share']:g} points today, "
                                 f"{sh['weekly_used']:g} of {sh['weekly_share']:g} this week, a round about {est:g})")
            never = 0 < min(sh["daily_share"], sh["weekly_share"]) < est  # no day's share ever holds a round (a smaller plan)
            if never and not st_.get("fix_never"):
                st_["fix_never"] = est
                ask(aid, f"If you raise my daily share to at least {est:g} points, I'll fix flagged rows by myself; if not, they wait for our calls.")
        return did + [f"{pick['label']} waits for the next day's share"]
    code, out = _schedule("add", "now", fix_text(aid, pick["label"], pick["mode"], pick["round"]), "--priority", "--kind", f"step-{aid}")
    if code:
        return did + [f"{pick['label']}: not planned ({out[:80]})"]
    review.round_started(pick, now.timestamp())
    did.append(f"{pick['label']} {'mark' if pick['mode'] == 'mark' else 'round ' + str(pick['round'])} planned")
    if log:
        log(f"cycles: {did[-1]} (F86)")
    return did


# -- new work, looked at when it lands (F174) -----------------------------------------------------------------------------------
# His words, 7 November 2026: "F174: I want you to pick up new work whenever it lands, not once a day." Every minute the routine
# reads the record for what's new for her: a Must row on the planning that's new or whose words changed, a night run whose record
# turned red, a build that stopped with no record. Each gets a small look of hers (one step naming that one thing, not her bigger
# session), one at a time, bugs first, then by the planning's order; each wording, red record and stuck build once. A look waits,
# with a ledger line, while her share has no room, while her start is refused (tried again after NEW_RETRY minutes), or while
# another look of hers is open; what lands while her night shift (her bigger session) runs is that night shift's. A look that
# finds nothing new is nothing: no run, no text. Day or night: the look carries any_hour, her share is the wall.

NEW_RETRY = 5  # minutes between tries of a refused start [the builder's pick]
NEW_UNTIL = 60  # minutes a look stays useful once planned [the builder's pick]
OPEN_HOURS = 3  # a run or step of hers older than this isn't open any more: stuck, it holds no look [the builder's pick]
_OPEN_ROW = re.compile(r"^\| (?:⬜|🔁|🔨|⏸) \| ([FHB]\d+(?:\.\d+)*) ")
_LABEL = re.compile(r"\b([FHB]\d+(?:\.\d+)*)\b")


def _must_rows(base: Path | None = None) -> list[dict]:
    """The open Must rows on the planning: {"label", "fp" (of its words), "bug", "rank"}, bugs first, then the planning's order."""
    ws = base or folder()
    try:
        text = (ws / "HQ" / "roadmap.md").read_text(encoding="utf8")
        sp = json.loads((ws / "HQ" / "sprint.json").read_text(encoding="utf8"))
    except (OSError, ValueError):
        return []
    musts = {k for k, v in (sp.get("moscow") or {}).items() if str(v).lower() == "must"}
    order = [str(x) for x in sp.get("order") or []] if isinstance(sp.get("order"), list) else []
    out, heading = [], ""
    for i, ln in enumerate(text.splitlines()):
        if ln.startswith("## "):
            heading = ln
            continue
        m = _OPEN_ROW.match(ln)
        if not m or m.group(1) not in musts:
            continue
        cells = ln.split(" | ")
        out.append({"label": m.group(1), "fp": _fp(cells[2] if len(cells) > 2 else ln), "bug": "Bugs" in heading,
                    "rank": order.index(m.group(1)) if m.group(1) in order else len(order) + i})
    return sorted(out, key=lambda r: (not r["bug"], r["rank"]))


def _night_red() -> dict | None:
    """The night run's record when it's red: {"key", "words"}, else None."""
    try:
        r = json.loads((ROOT / "scratch" / "nightly" / "last.json").read_text(encoding="utf8"))
    except (OSError, ValueError):
        return None
    if not isinstance(r, dict) or not (r.get("failed") or r.get("exit")):
        return None
    failed = r.get("failed") or []
    n = len(failed) if isinstance(failed, list) else failed
    return {"key": f"night|{r.get('at', '')}", "words": f"a look at the night run of {r.get('at', '?')}, red: {n} of {r.get('ran', '?')} flows failed; "
            "read its record and log, find why, and put the fix in your prep"}


def _proving(n: int) -> bool:
    """The build's proof is running: it's waiting on its record, not stuck."""
    try:
        import wall
        return bool(wall._proof(n).get("since"))
    except Exception:
        return False


def _stuck_builds(jobs_: list) -> list[dict]:
    """Builds that stopped with no record: {"key", "words"}."""
    out = []
    for j in jobs_:
        st = j.get("state", "")
        if not (st.startswith("paused") and "no record" in st) or parse(j.get("text", "")) or _proving(j["n"]):
            continue
        m = _LABEL.search(j.get("text", ""))
        what = f"the build for {m.group(1)}" if m else "a build"
        out.append({"key": f"stuck|{j['n']}|{st.split(':')[0]}", "words": f"a look at job {j['n']}, {what} that stopped with no record: "
                    "read its record and log, find why, and put what it needs in your prep"})
    return out


def _her_open(aid: str, text: str, jobs_: list, now: dt.datetime) -> str | None:
    """"night" while her night shift (a bigger session) runs, "look" while another look of hers is open, else None."""
    import jobs as q
    import schedule
    seen = None
    since = (now - dt.timedelta(hours=OPEN_HOURS)).strftime(FMT)
    hm = now.strftime(FMT)
    for j in jobs_:
        p = parse(j.get("text", ""))
        if not p or p["agent"] != aid or j.get("state", "").startswith(tuple(q.FINISHED) + ("paused", "skipped")):
            continue
        if not since <= (j.get("agreed") or "") <= hm:  # a run of hers "running" for hours is stuck, not open: it holds nothing
            continue
        if p["kind"] == "session" or "night shift" in p.get("name", ""):
            return "night"
        seen = "look"
    for it in schedule.read(text):
        p = parse(it["text"])
        if p and p["kind"] in ("session", "look", "review"):
            continue  # a cycle that hasn't started yet isn't running; it reads the planning itself when it does
        if it["state"].startswith("waiting") and since <= it["at"] <= hm and ((p and p["agent"] == aid) or (not p and aid in it["text"].lower())):
            seen = seen or "look"
    return seen


def new_work(now: dt.datetime | None = None, base: Path | None = None, log=None) -> list[str]:
    """F174: what's new for her gets her look within minutes (see above). One start a minute at the most."""
    now = (now or dt.datetime.now()).replace(second=0, microsecond=0)
    aid = FIX_AGENT
    did = []
    if not on(base):
        return did
    a = agent_settings(aid, base)
    if not a.get("on") or not _agent(aid, base):
        return did
    import jobs as q
    text, jobs_, _ = q.read()
    found = [{"key": f"row|{r['label']}", "fp": r["fp"], "label": r["label"], "bug": r["bug"]} for r in _must_rows(base)]
    nr = _night_red()
    found += [{"key": x["key"], "fp": x["key"], "label": "", "bug": True, "words": x["words"]} for x in ([nr] if nr else []) + _stuck_builds(jobs_)]
    with held() as d:
        nw = d.get("new_work")
        if nw is None:  # the first minute: what's there already is the night shift's, as before
            d["new_work"] = {"seen": {f["key"]: f["fp"] for f in found}, "waiting": []}
            return did
        seen, waiting = nw.setdefault("seen", {}), nw.setdefault("waiting", [])
        here = {f["key"] for f in found}  # what's gone (a row done or no Must any more, last night's record) drops out
        for k_ in [k_ for k_ in seen if k_ not in here]:
            del seen[k_]
        waiting[:] = [x for x in waiting if x["key"] in here]
        busy = _her_open(aid, text, jobs_, now)
        for f in found:
            if seen.get(f["key"]) == f["fp"]:
                continue
            w = next((x for x in waiting if x["key"] == f["key"]), None)
            if w:
                w.update(f)
            else:
                waiting.append({**f, "since": now.strftime(FMT)})
        if busy == "night":  # her running night shift takes what lands meanwhile
            for w in waiting:
                seen[w["key"]] = w["fp"]
                ledger.entry(aid, f"{w['label'] or w['key']} taken by her night shift", ["it landed while her night shift ran, so that night shift has it"], now)
                did.append(f"{aid}: {w['label'] or w['key']} taken by her night shift")
            nw["waiting"] = []
            return did
        if not waiting:
            return did
        waiting.sort(key=lambda w: not w["bug"])  # stable: bugs first, then the order found (the planning's)
        w = waiting[0]
        name = w["label"] or w["key"]

        def wait(kind: str, why: str) -> None:
            if w.get("why") != kind:
                w["why"] = kind
                ledger.entry(aid, f"her look at {name} waits", [f"waits: {why}", "its row stays as it was; it gets its look within minutes of that clearing"], now)
            did.append(f"{aid}'s look at {name} waits: {why}")

        if busy == "look":
            return did  # one at a time: it starts once the open one ends; nothing to write
        if w.get("retry") and now.strftime(FMT) < w["retry"]:
            return did
        why = over_share(shares(aid, now, base), max(_step_price(aid, a), LEAST_CHARGE))
        if why:
            wait("share", why)
            return did
        goal = w.get("words") or (f"a look at {w['label']}, {'changed' if w['key'] in seen else 'new'} on the planning as a Must {'bug' if w['bug'] else 'feature'}: "
                                  "read its row; put it in your prep, or write in your ledger what it waits on")
        stamp = now.strftime(FMT)
        st_ = _agent_state(d, aid)
        k = 0
        while f"{aid}|{stamp}|{k}" in st_["steps"]:
            k = max(k, 99) + 1
        code, out = _schedule("add", "now", step_text(aid, stamp, k, goal), "--priority", "--kind", f"step-{aid}")
        if code:
            w["retry"] = (now + dt.timedelta(minutes=NEW_RETRY)).strftime(FMT)
            wait("refused", f"her start was refused ({(out or '').splitlines()[0][:120] if out else code}); tried again in {NEW_RETRY} minutes")
            return did
        st_["steps"][f"{aid}|{stamp}|{k}"] = {"spec": {"goal": goal, "done_means": "it's in your prep, or your ledger says what it waits on", "inputs": [],
                                                      "may": "one look inside your limits", "at": now.strftime("%H:%M")},
                                             "fps": [], "day": now.strftime("%Y-%m-%d"), "state": "planned", "stamp": stamp, "new_work": w["key"], "any_hour": True,
                                             "until": (now + dt.timedelta(minutes=NEW_UNTIL)).strftime(FMT)}
        seen[w["key"]] = w["fp"]
        nw["waiting"] = waiting[1:]
        did.append(f"{aid}: a look at {name} planned")
    if log:
        for x in did:
            log(f"cycles: {x}")
    return did


# -- a Must's prepare, switched on by itself (F194) ---------------------------------------------------------------------------
# His words, 7 November 2026: "The bugs from today: F194, F192, F186, F187, F189, F190." Six Must bugs sat untouched: F174's look
# only asked her to put a row in her prep, and rows there before its first minute never got one. Every minute the routine switches
# prepare on, by Moneypenny, for each open Must row that is new or whose words changed, also the ones there before, so the line
# takes it into her prep even while her look waits. A prepare already on (his or hers) is left as it is; one he switched off stays
# off for the same wording. A switch that can't be written leaves the row as it was, her ledger says so, and it's tried the next
# minute. A Must whose prepare is still off an hour after the row's first dated line shows on the status page (must_waiting).

MUST_WAIT = 60  # minutes from the row's first dated line before the status page names it (his yes, 7 November 2026)
_FIRST_DATED = re.compile(r"\b(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})"
                          r" \([^)]*?(\d{1,2}):(\d{2})\)")


def _sprint_here(base: Path | None):
    """routine/sprint.py, when its planning is this workspace's (a test's folder elsewhere gets no switch), else None."""
    import sprint
    try:
        same = Path(sprint.RANKS).resolve() == ((base or folder()) / "HQ" / "sprint.json").resolve()
    except OSError:
        same = False
    return sprint if same else None


def must_go(now: dt.datetime | None = None, base: Path | None = None, log=None) -> list[str]:
    """F194: each open Must row that's new or changed gets its prepare on, by Moneypenny (see above)."""
    now = (now or dt.datetime.now()).replace(second=0, microsecond=0)
    aid = FIX_AGENT
    did = []
    sp = _sprint_here(base)
    if not sp or not on(base) or not agent_settings(aid, base).get("on"):
        return did
    rows = _must_rows(base)
    with held() as d:
        mg = d.setdefault("must_go", {})
        done, refused = mg.setdefault("done", {}), mg.setdefault("refused", {})
        here = {r["label"] for r in rows}
        for k_ in [k_ for k_ in done if k_ not in here]:
            del done[k_]
        for k_ in [k_ for k_ in refused if k_ not in here]:
            del refused[k_]
        for r in rows:
            label = r["label"]
            if done.get(label) == r["fp"]:
                continue  # this wording had its switch (or his): one he switched off stays off
            if sp.go_of(label).get("prep"):
                done[label] = r["fp"]  # already on, his or hers: left as it is
                refused.pop(label, None)
                continue
            try:
                sp.set_go(label, "prep", True, by="moneypenny")
                ok = bool(sp.go_of(label).get("prep"))
                why = "" if ok else "the switch didn't stay on"
            except (SystemExit, Exception) as e:
                ok, why = False, " ".join(str(e).split())[:160] or type(e).__name__
            if not ok:
                if label not in refused:
                    refused[label] = now.strftime(FMT)
                    try:
                        ledger.entry(aid, f"{label}: its prepare couldn't be switched on", [f"refused: {why}",
                                     "its row stays as it was; the switch is tried again every minute"], now)
                    except OSError:
                        pass
                did.append(f"{aid}: {label} prepare refused ({why[:80]})")
                continue
            done[label] = r["fp"]
            if refused.pop(label, None):
                try:
                    ledger.entry(aid, f"{label}: its prepare is on now", ["the switch could be written again"], now)
                except OSError:
                    pass
            did.append(f"{aid}: {label} prepare on")
    if log:
        for x in did:
            log(f"cycles: {x} (F194)")
    return did


def must_waiting(now: dt.datetime | None = None, base: Path | None = None) -> list[str]:
    """F194: one line per open Must row whose prepare is still off past MUST_WAIT minutes from its first dated line."""
    now = (now or dt.datetime.now()).replace(second=0, microsecond=0)
    ws = base or folder()
    try:
        text = (ws / "HQ" / "roadmap.md").read_text(encoding="utf8")
        go = json.loads((ws / "HQ" / "sprint.json").read_text(encoding="utf8")).get("go") or {}
    except (OSError, ValueError):
        return []
    musts = {r["label"] for r in _must_rows(base)}
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    out = []
    for ln in text.splitlines():
        m = _OPEN_ROW.match(ln)
        if not m or m.group(1) not in musts or (go.get(m.group(1)) or {}).get("prep"):
            continue
        cells = ln.split(" | ")
        f = _FIRST_DATED.search(cells[2] if len(cells) > 2 else ln)
        if not f:
            continue
        try:
            since = dt.datetime(int(f.group(3)), months.index(f.group(2)) + 1, int(f.group(1)), int(f.group(4)), int(f.group(5)))
        except ValueError:
            continue
        mins = int((now - since).total_seconds() // 60)
        if mins < MUST_WAIT:
            continue
        h, mm = divmod(mins, 60)
        out.append(f"{m.group(1)} is a Must whose prepare is still off: it has waited {h} h {mm:02d} min since {since:%d %b %H:%M}")
    return out


def tick(now: dt.datetime | None = None, base: Path | None = None, log=None) -> dict:
    """The routine's minute on the main: the items follow the settings, finished runs go into the ledgers, the
    batches go out, waiting runs are dropped at the hours' end, the reviews are planned, the weekly score written."""
    now = now or dt.datetime.now()
    out = {"on": on(base)}
    try:
        out["reconciled"] = reconcile(now, base, log)
    except Exception as e:
        out["reconciled"] = [f"error: {e!r}"]
    if not out["on"]:
        return out
    try:
        out["processed"] = settle(now, base, log)
    except Exception as e:
        out["processed"] = [f"error: {e!r}"]
    for name, fn in (("batches", send_batches), ("later", later), ("looks", list_looks), ("orders", waiting_orders), ("dropped", drop_waiting), ("reviews", plan_reviews), ("scores", write_scores), ("fixes", fix_rounds), ("must", must_go), ("new", new_work)):
        try:
            out[name] = fn(now, base, log=log)
        except Exception as e:
            out[name] = [f"error: {e!r}"]
    return out


# -- words --------------------------------------------------------------------------------------------------------------------

def words(base: Path | None = None, now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now()
    out = [f"The agents run themselves: {'on' if on(base) else 'off'}."]
    s = settings(base)
    for ag in _agents(base):
        a = s["agents"].get(ag["id"])
        if not a:
            continue
        sh = shares(ag["id"], now, base)
        out.append(f"{ag['name']}: {'on' if a.get('on') else 'off'}; share this week {sh['weekly_used']:g} of {sh['weekly_share']:g} points "
                   f"(today {sh['daily_used']:g} of {sh['daily_share']:g}); bigger session {a['session'].get('every', 'day')} at {a['session']['at']} "
                   f"({a['session']['minutes']} min, {a['session']['turns']} turns, useful until {a['session'].get('useful_until', '?')}); "
                   f"steps {a['step']['minutes']} min, {a['step']['turns']} turns, at most {a['step'].get('most_a_day', 3)} a day; hours {a['hours'][0]} to {a['hours'][1]}"
                   + (f"; batches {', '.join(a['batches'])}" if a.get("batches") else "") + f"; {a.get('tripwire_texts', 2)} tripwire texts a day"
                   + ("; the fix loop on" if a.get("fix") else "")
                   + "".join(f"; {lk['name']} {lk.get('every', 'day')} at {lk['at']}" for lk in a.get("looks") or [])
                   + (f"; her list looked at {len(look_times(a))} times a day ({', '.join(x[1] for x in look_times(a))})" if look_times(a) else "; her list only at her bigger session"))
    for ag in _agents(base):
        w = waiting_words(ag["id"])
        if w:
            out.append(f"{ag['name']}: {w}")
    try:
        items, jobs_ = _items()
        waiting = [i for i in items if i["state"] == "waiting"]
        if waiting:
            out.append("Planned: " + "; ".join(f"item {i['n']} {i['text'][len(MARK_CYCLE):] if i['text'].startswith(MARK_CYCLE) else i['text'][:60]} at {i['at']}" for i in waiting))
        open_jobs = [j for j in jobs_ if not j["state"].startswith(("done", "stopped", "ended", "cancelled"))]
        if open_jobs:
            out.append("On the queue: " + "; ".join(f"job {j['n']} ({j['state']})" for j in open_jobs))
    except Exception:
        pass
    return "\n".join(out)


def settings_words(base: Path | None = None) -> str:
    s = settings(base)
    return json.dumps(s, indent=1, ensure_ascii=False)


def friday(now: dt.datetime | None = None, base: Path | None = None) -> dict:
    """The Friday screen (piece 7): three lines per agent (what she picked, what moved on her score, what she
    escalated or let go), and her share used this week against her line."""
    now = now or dt.datetime.now()
    out = {"on": on(base), "at": now.strftime(FMT), "agents": []}
    if not out["on"]:
        return out
    for ag in _agents(base):
        aid = ag["id"]
        a = agent_settings(aid, base)
        if not a.get("on"):
            continue
        sec, p = ledger.plan(aid)
        picks = [(x.get("what") if isinstance(x, dict) else str(x)) for x in (p or {}).get("picks") or []]
        picked = (", ".join(picks) if picks else "nothing picked yet") + (f" (plan of {sec['at']:%A %H:%M})" if sec else "")
        sc = ledger.scores(aid)
        import pokes
        moved = pokes.delta(sc[-1][1], sc[-2][1] if len(sc) > 1 else None) if sc else ["no score yet"]
        esc, let = [], []
        for s_ in ledger.recent(aid, 7, now):
            for l in s_["body"].splitlines():
                if l.startswith("- escalated:") or l.startswith("- tripwire"):
                    esc.append(l[2:])
                elif l.startswith("- let go"):
                    let.append(l[2:])
        sh = shares(aid, now, base)
        out["agents"].append({"id": aid, "name": ag["name"], "picked": picked, "moved": "; ".join(moved),
                              "escalated": "; ".join(esc[-5:]) or "nothing escalated", "let_go": "; ".join(let[-5:]) or "nothing let go",
                              "share": sh})
    return out


def friday_words(now: dt.datetime | None = None, base: Path | None = None) -> str:
    f = friday(now, base)
    if not f["on"]:
        return "The agents run themselves is off."
    out = []
    for a in f["agents"]:
        out.append(f"{a['name']}:\n- picked: {a['picked']}\n- moved: {a['moved']}\n- escalated: {a['escalated']}; {a['let_go']}\n"
                   f"- share: {a['share']['weekly_used']:g} of {a['share']['weekly_share']:g} points this week")
    return "\n".join(out) or "No agent is on."


# -- main ---------------------------------------------------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("list", "show", "status"):
        print(words())
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd in ("set", "order", "yes", "no") and _this_run():
        print("Refused: the settings and the orders are his; a run of hers doesn't change them.")
        return 2
    if cmd == "set" and len(rest) == 3 and rest[1].strip().lower() == "mail":  # F114
        import hqpaths as _hp
        print(f"Refused: {_hp.MAIL_SWITCH_WORDS}.")
        return 2
    import role
    yes_n = int(rest[2]) if cmd == "yes" and len(rest) > 2 and rest[2].isdigit() else None
    if cmd == "yes" and len(rest) >= 2 and os.environ.get("HQ_ROLE_HERE") and not role.is_handed():
        pass  # the routine's own run, or a flow's "write here": as before F115's doors, no check of words here
    elif cmd == "yes" and len(rest) >= 2 and role.is_handed() and not _SAYS_NO.match(rest[1]):
        # F115 with F114 (the combined check): a handed yes stands on the words the backup checked, and fits a change by the main's own
        # holds, never by the backup's copy of them, which can be behind
        d = role.handed_words()
        why = "a yes handed over from the other computer carries no words it checked there" if not d else \
            handed_yes_refused(rest[0].lower(), d, yes_n)
        if why:
            print(f"Refused: {why}. A yes to a held change is his own words: cycles.py yes AGENT \"HIS WORDS\" [N], a line he said or typed "
                  "on a call or in a chat; an agent's words never stand for it.")
            return 2
        role.note_handed(f"cycles yes {rest[0]}", d)
    elif cmd == "yes" and len(rest) >= 2:  # F114: his yes is his own words in a real line
        backup = role.is_backup()
        why, hit = his_yes_line(rest[1]) if backup else ("", None)
        why = why or ("" if backup else his_yes_refused(rest[0].lower(), rest[1], yes_n))
        if why:
            print(f"Refused: {why}. A yes to a held change is his own words: cycles.py yes AGENT \"HIS WORDS\" [N], a line he said or typed "
                  "on a call or in a chat; an agent's words never stand for it.")
            return 2
        if backup:  # checked here: his line goes to the main, which fits it to its own holds
            return role.forward("cycles", list(argv), env=role.checked_env(rest[1], [hit] if hit else []))
    # harm 9: on the backup a call's change goes to the main, as schedule.py's does: only the main writes these
    if cmd in ("set", "order", "yes", "no") and not os.environ.get("HQ_ROLE_HERE"):
        if role.is_backup():
            return role.forward("cycles", list(argv))
    try:
        if cmd == "settings":
            print(settings_words())
        elif cmd == "set" and len(rest) == 3:
            print(set_setting(rest[0], rest[1], rest[2]))
        elif cmd == "order" and len(rest) >= 3:
            print(order(rest[0].lower(), rest[1].lower(), rest[2], now_="--now" in rest))
        elif cmd == "plan" and len(rest) == 2:
            print(plan(rest[0].lower(), rest[1], job=int(os.environ.get("HQ_JOB") or 0) or None))
        elif cmd in ("done", "failed", "stale") and len(rest) == 3 and rest[1].isdigit():
            print(step_done(rest[0].lower(), int(rest[1]), rest[2], failed=cmd == "failed", gone_stale=cmd == "stale"))
        elif cmd == "ask" and len(rest) == 2:
            print(ask(rest[0].lower(), rest[1]))
        elif cmd == "batch" and len(rest) in (2, 4) and (len(rest) == 2 or rest[2] == "--until"):
            print(batch(rest[0].lower(), rest[1], until=rest[3] if len(rest) == 4 else None))
        elif cmd == "text" and len(rest) == 2:
            print(tripwire_free_text(rest[0].lower(), rest[1]))
        elif cmd == "proposal" and len(rest) == 2:
            print(proposal(rest[0].lower(), rest[1]))
        elif cmd == "yes" and len(rest) >= 2:
            print(yes(rest[0].lower(), rest[1], int(rest[2]) if len(rest) > 2 and rest[2].isdigit() else None))
        elif cmd == "no" and len(rest) >= 2:
            print(no(rest[0].lower(), rest[1], int(rest[2]) if len(rest) > 2 and rest[2].isdigit() else None))
        elif cmd == "close" and len(rest) == 2 and rest[1].isdigit():
            print(close_hold(rest[0].lower(), int(rest[1])))
        elif cmd == "open" and len(rest) == 2 and rest[1].isdigit():
            print(open_hold(rest[0].lower(), int(rest[1])))
        elif cmd == "go" and len(rest) == 2 and rest[1].isdigit():
            print(go_on(rest[0].lower(), int(rest[1])))
        elif cmd == "stopstep" and len(rest) == 3 and rest[1].isdigit():
            print(stop_step(rest[0].lower(), int(rest[1]), rest[2]))
        elif cmd == "droptext" and len(rest) == 2 and rest[1].isdigit():
            print(drop_text(rest[0].lower(), int(rest[1])))
        elif cmd == "stopped" and len(rest) == 2:
            print(stopped(rest[0].lower(), rest[1]))
        elif cmd == "ledger" and len(rest) == 1:
            print(ledger.words(rest[0].lower()))
        elif cmd == "score":
            if "--write" in rest:
                print("\n".join(write_scores(force=True)) or "Nothing written.")
            else:
                import pokes
                for ag in _agents():
                    if rest and rest[0] not in ("--write",) and ag["id"] != rest[0].lower():
                        continue
                    sc = pokes.score(ag, plan=ledger.plan(ag["id"])[1])
                    print(f"{ag['name']}, week {sc['week']}:\n" + "\n".join("- " + l for l in sc["lines"]))
        elif cmd == "friday":
            print(json.dumps(friday(), indent=1, ensure_ascii=False) if "--json" in rest else friday_words())
        elif cmd == "tick":
            print(json.dumps(tick(), ensure_ascii=False))
        elif cmd == "waiting":
            print(json.dumps(must_waiting(), ensure_ascii=False))
        else:
            print(__doc__)
            return 2
    except ValueError as e:
        print(f"Refused: {e}")
        return 2
    return 0


def tripwire_free_text(aid: str, text: str, now: dt.datetime | None = None, base: Path | None = None) -> str:
    """A run's own text on her line now (for what breaks through), inside a day's cap of its own: a tripwire never uses it up."""
    now = now or dt.datetime.now()
    today = _today(now)
    most = int(agent_settings(aid, base).get("tripwire_texts", 2))
    with held() as d:
        st_ = _agent_state(d, aid)
        if st_["own_texts"].get(today, 0) >= most:
            return "Not sent: the day's texts are used up; it goes in the ledger only."
        st_["own_texts"] = {today: st_["own_texts"].get(today, 0) + 1}
        ledger.note(aid, f"texted: {text}")
        how = say(aid, text, "cycle", now, base)
    return f"Sent on {aid}'s line." if how == "sent" else f"He's asleep: it goes on {aid}'s line when he's up, if it's still true then."


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
