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
     (the run is skipped, written as skipped), read from the measured cost of her finished runs;
  4. nothing of theirs runs outside her hours (8:00 to 22:00 by default) and nothing restarts itself: a boxed, stale or
     skipped step is never retried by the runner; what waits at the hours' end is dropped to the morning.

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
in her ledger (`cycles.py order`) and picked up here. Every week the routine computes her score (routine/pokes.py)
into her ledger. The settings are the workspace's HQ/agents/cycles.json (numbers; the template ships the defaults).

    python3 routine/cycles.py                         what runs, each agent's share used this week, what's planned
    python3 routine/cycles.py settings                the settings, per agent
    python3 routine/cycles.py set AGENT KEY VALUE     on|off, fix (F86's loop, on|off), weekly, daily, hours (08:00-22:00), batches (12:00,17:00),
                                                      texts (tripwire texts a day), session_at, session_every,
                                                      session_minutes, session_turns, step_minutes, step_turns, steps_a_day
    python3 routine/cycles.py order AGENT start|stop|standing "HIS WORDS" [--now]   an order from a call or a text
    python3 routine/cycles.py plan AGENT 'JSON'       the bigger session's cycle plan (her own run writes it)
    python3 routine/cycles.py done AGENT K "WHAT"     a small step says what came of it; failed AGENT K "WHY"
    python3 routine/cycles.py ask AGENT "IF-THEN"     one question for him on her line, in if-then shape (once a day)
    python3 routine/cycles.py batch AGENT "TEXT"      a text for her next batch (the low-information diet)
    python3 routine/cycles.py text AGENT "TEXT"       a text on her line now (a run's own, inside the day's cap)
    python3 routine/cycles.py ledger AGENT            her ledger
    python3 routine/cycles.py score [AGENT]           the weekly score now (written to her ledger with --write)
    python3 routine/cycles.py friday [--json]         the Friday screen: three lines per agent, her share
    python3 routine/cycles.py tick                    the routine's minute (tick.py runs it on the main)
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "app"))
import hqpaths  # noqa: E402
import ledger  # noqa: E402

FOLDER = Path(hqpaths.FOLDER)
SETTINGS_REL = "HQ/agents/cycles.json"
STATE = Path(os.environ.get("HQ_CYCLES_STATE") or (ROOT / ".status" / "cycles-state.json"))
PY = sys.executable
FMT = "%Y-%m-%d %H:%M"
MARK_CYCLE = "Agent cycle: "
MARK_STEP = "Agent step: "
MARK_FIX = "Agent fix: "
FIX_AGENT = "moneypenny"  # F86: the loop is hers; the rows are hers to write
PICKS_MOST = 3
QUESTIONS_MOST = 3
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
SHARED = ("HQ/roadmap.md", "challenges.md", "coaching/log.md", "inbox.md", "HQ/calendar.json", "HQ/sprint.json",
          "HQ/games.json", "HQ/coaching.json", "HQ/calendar-todo.json", "HQ/calendar-marks.json")
# H298: an action outside every agent's limits, by the tool it would take (the handbook's "what she asks").
OUTSIDE = (r"mcp__\w*gmail\w*__(send_message|reply|forward)", r"mcp__\w*calendar\w*__(create_event|update_event|delete_event)",
           r"\bpush\.py\b", r"\brelease\.py\b", r"\bfeatures\.py (on|off)\b", r"\bbackend\.py (on|off)\b", r"\bjobs\.py (add|send-row|add-row|stop|on|off)\b",
           r"\bgit (push|commit|reset|checkout)\b", r"\bcycles\.py set\b", r"handbook\.md", r"agents\.json")
_OUTSIDE = re.compile("|".join(OUTSIDE), re.I)
_EDIT = re.compile(r"^(Edit|Write|MultiEdit|NotebookEdit) (.+)$")


# -- settings ---------------------------------------------------------------------------------------------------------

def folder() -> Path:
    return Path(os.environ.get("HQ_CYCLES_FOLDER") or FOLDER)


def on(base: Path | None = None) -> bool:
    try:
        import features
        return features.is_on("agents_run", base or folder())
    except Exception:
        return False


DEFAULT_AGENT = {"on": True, "fix": False, "weekly_share": 2, "daily_share": 1, "hours": ["08:00", "22:00"], "batches": [], "tripwire_texts": 2,
                 "session": {"at": "09:00", "every": "day", "minutes": 10, "turns": 30, "useful_until": "12:00"},
                 "step": {"minutes": 3, "turns": 10, "most_a_day": 3}, "looks": []}


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


SET_KEYS = ("on", "fix", "weekly", "daily", "hours", "batches", "texts", "session_at", "session_every", "session_minutes",
            "session_turns", "session_until", "step_minutes", "step_turns", "steps_a_day")


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
    elif key == "hours":
        m = re.fullmatch(r"(\d{1,2}:\d\d)\s*(?:-|to)\s*(\d{1,2}:\d\d)", v)
        if not m:
            return "hours are from-to, like 08:00-22:00."
        a["hours"] = [_hhmm(m.group(1)), _hhmm(m.group(2))]
    elif key == "batches":
        ts = [x.strip() for x in re.split(r"[,; ]+", v) if x.strip()]
        if not all(re.fullmatch(r"\d{1,2}:\d\d", x) for x in ts):
            return "batches are times, like 12:00,17:00 (or none)."
        a["batches"] = [_hhmm(x) for x in ts if x.lower() != "none"]
    elif key in ("session_at",):
        if not re.fullmatch(r"\d{1,2}:\d\d", v):
            return "session_at is a time, like 08:30."
        a["session"]["at"] = _hhmm(v)
    elif key == "session_every":
        w = v.lower().rstrip("s")
        if w not in ("day",) + tuple(DAYS):
            return "session_every is day or a weekday."
        a["session"]["every"] = w
    elif key == "session_until":
        a["session"]["useful_until"] = v
    else:
        return f"No setting called {key}. The settings: {', '.join(SET_KEYS)}."
    _save_settings(d, base)
    return f"{aid}: {key} is now {v}."


def _hhmm(s: str) -> str:
    h, m = s.split(":")
    return f"{int(h):02d}:{int(m):02d}"


# -- the state (this computer's) --------------------------------------------------------------------------------------

def _state() -> dict:
    try:
        d = json.loads(STATE.read_text(encoding="utf8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(d: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_name(STATE.name + ".tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    os.replace(tmp, STATE)


def _agent_state(d: dict, aid: str) -> dict:
    return d.setdefault("agents", {}).setdefault(aid, {"goals": {}, "boxed_streak": 0, "texts": {}, "batch": [],
                                                       "asked": {}, "processed": [], "steps": {}, "skipped": {}})


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
            "try:\n    m['pushed'] = D.push(m['text']) if D.on() else []\nexcept Exception as e:\n    m['pushed'] = [repr(e)]\n"
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
    have = {i["text"] for i in waiting}
    for w in want:
        if w["text"] in have:
            continue
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


def in_hours(a: dict, now: dt.datetime) -> bool:
    lo, hi = a.get("hours") or ["08:00", "22:00"]
    return _t(lo) <= now.time() < _t(hi)


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
    hi = _t((a.get("hours") or ["08:00", "22:00"])[1])
    return job_at.replace(hour=hi.hour, minute=hi.minute, second=0, microsecond=0)


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


def gatekeep(job: dict, now: dt.datetime | None = None, base: Path | None = None, log=None) -> str:
    """Before the routine starts a cycle job (tick.py, with the jobs' gate after it): "go", "wait" (before her hours;
    nothing else starts meanwhile, the queue is the lane) or "skipped" (cancelled on the queue, written in her ledger:
    outside her hours at the day's end, past its useful-until, over her share, a step past the day's count, or the
    feature off)."""
    now = now or dt.datetime.now()
    p = parse(job.get("text", ""))
    if not p:
        return "go"
    aid = p["agent"]
    a = agent_settings(aid, base)
    d = _state()
    st = _agent_state(d, aid)
    job_at = _job_at(job, now)

    def skip(why: str, morning: bool = False) -> str:
        _jobs("stop", str(job["n"]))
        if p["kind"] == "fix":  # F86: a round that never ran doesn't count
            import review
            review.round_refund(p["label"], p["mode"])
        ledger.entry(aid, f"{p['name']} skipped (job {job['n']})", [f"skipped: {why}"], now)
        st["skipped"][str(job["n"])] = why
        if morning and p["kind"] == "session":
            lo = (a.get("hours") or ["08:00", "22:00"])[0]
            nxt = (now + dt.timedelta(days=1)).replace(hour=_t(lo).hour, minute=_t(lo).minute, second=0, microsecond=0)
            u = useful_until(p, a, job_at, now)
            if u and u > nxt:
                _schedule("add", nxt.strftime(FMT), cycle_text(aid, p["name"]), "--priority", "--kind", f"cycle-{aid}")
                ledger.note(aid, f"planned again for {nxt:%A %H:%M}, inside its useful-until")
        _save_state(d)
        if log:
            log(f"cycles: job {job['n']} ({aid}, {p['name']}) skipped: {why}")
        return "skipped"

    if not on(base) or not a.get("on"):
        return skip("the agents running themselves is off" if not on(base) else "she's switched off")
    if not in_hours(a, now):
        lo, hi = a.get("hours") or ["08:00", "22:00"]
        if now.time() >= _t(hi):
            return skip(f"the day's hours end at {hi}; nothing of hers runs at night", morning=True)
        return "wait"
    u = useful_until(p, a, job_at, now)
    if u and now > u:
        return skip(f"too late to be useful (until {u:%A %H:%M})")
    sh = shares(aid, now, base)
    est = _est_weekly(job)
    # A share of 0 is a wall with no room in it: nothing of hers starts (found on the server, 29 October 2026, where
    # `set donna weekly 0` let every start through).
    if sh["weekly_share"] <= 0 or sh["weekly_used"] + est > sh["weekly_share"]:
        return skip(f"over her weekly share ({sh['weekly_used']:g} of {sh['weekly_share']:g} points used, this run about {est:g})")
    if sh["daily_share"] <= 0 or sh["daily_used"] + est > sh["daily_share"]:
        return skip(f"over her daily share ({sh['daily_used']:g} of {sh['daily_share']:g} points used today, this run about {est:g})")
    if p["kind"] == "fix":
        import review
        if not review.round_wanted(p["label"], p["mode"]):
            return skip("the row no longer needs it (changed or settled since)")
    if p["kind"] == "step":
        today = now.strftime("%Y-%m-%d")
        n = sum(1 for k, v in st["steps"].items() if v.get("day") == today and v.get("started"))
        if n >= int(a["step"].get("most_a_day") or 3):
            return skip(f"the day's steps are used up ({n})")
        why = stale(aid, p, d)
        if why:
            _jobs("stop", str(job["n"]))
            ledger.entry(aid, f"step {p['k']} stale (job {job['n']})", [f"stale: {why}; not run"], now)
            rec = st["steps"].get(_step_key(p)) or {}
            rec["state"] = "stale"
            st["steps"][_step_key(p)] = rec
            _save_state(d)
            if log:
                log(f"cycles: job {job['n']} ({aid}, step {p['k']}) stale: {why}")
            return "skipped"
    return "go"


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
    return {"minutes": a["step"]["minutes"], "turns": a["step"]["turns"]}


def box_args(job: dict, parsed: dict, run_dir: str, base: Path | None = None) -> list[str]:
    b = box(parsed, base)
    return ["--max-minutes", str(b["minutes"]), "--max-turns", str(b["turns"]), "--box-note",
            os.path.join(run_dir, f"job-{job['n']}.box.json")]


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
             "- Writes to a shared file (the planning, the to-do list, the log, the mail list, the calendar) only through HQ's own scripts "
             f"(todo.py, sprint.py, jobs.py, pings.py, python3 \"{ROOT / 'routine' / 'handover.py'}\" edit REL JSON for the log and the mail list), never with an Edit or Write on the file itself: "
             "that's the one place that serializes them (each takes the file's lock); a direct write is refused by this run's hook before it lands, and is a tripwire. Your ledger and your line you write freely.",
             "- Never send mail, never a calendar change with another person in it, never anything he must say yes to first, never a change to the handbook, "
             "your section or the settings: those are his (an if-then question instead). Never start another run or plan more than this run's plan.",
             "- Nothing in what you write goes outside this workspace."]
    if a.get("batches") and aid == "donna":
        lines.append(f"- His low-information diet: your texts come in batches at {' and '.join(a['batches'])}: python3 \"{cy}\" batch {aid} \"…\" queues one for the next batch. "
                     "Only an appointment ping he asked for, a travel delay, a very important mail with a date inside 48 hours, the game reminder and a tripwire break through on their own.")
    return "\n".join(lines)


def _plan_shape(aid: str, a: dict, now: dt.datetime) -> str:
    cy = ROOT / "routine" / "cycles.py"
    lo, hi = a.get("hours") or ["08:00", "22:00"]
    return (f"Your cycle plan, the last thing this session does, in one command (JSON in single quotes):\n"
            f"python3 \"{cy}\" plan {aid} '{{\"picks\": [{{\"what\": \"…\", \"source\": \"his words of <date>, a rule, a row, the calendar\"}}], "
            f"\"let_go\": [\"…\"], \"steps\": [{{\"goal\": \"one look or one action\", \"done_means\": \"…\", \"inputs\": [{{\"kind\": \"todo\", \"words\": \"…\"}}, "
            f"{{\"kind\": \"row\", \"label\": \"H123\"}}, {{\"kind\": \"mail\", \"words\": \"…\"}}, {{\"kind\": \"calendar\", \"words\": \"…\"}}, {{\"kind\": \"file\", \"path\": \"…\"}}], "
            f"\"may\": \"what the step may do\", \"at\": \"HH:MM\", \"escalate_when\": \"…\"}}], \"questions\": [\"If …, …; if not, …\"], \"orders_done\": [1]}}'\n"
            f"At most {PICKS_MOST} picks, at most {a['step'].get('most_a_day', 3)} steps, each at a time today between {lo} and {hi} and after now ({now:%H:%M}), "
            "each with only the inputs it needs by name (the runner checks they still hold before the step runs; changed, the step is stale and doesn't run); "
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
        parts.append("Your ledger (the last cycles first thing: what was boxed, stale, skipped, escalated or corrected, and your score):\n\n" + ledger.words(aid, 10))
        orders = ledger.orders(aid, ("open", "now"))
        if orders:
            parts.append("His orders waiting for you (take each up in this plan, or say in your ledger why not):\n" +
                         "\n".join(f"{o['n']}. {o['kind']}: \"{o['words']}\" ({o['at']})" for o in orders))
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
            if ".." in p.split("/") or not path.exists():
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
    for inp, fp in zip(rec.get("spec", {}).get("inputs") or [], rec.get("fps") or []):
        now_fp = _fp(resolve(inp, base))
        if now_fp != fp:
            return f"its input changed since the plan ({inp.get('kind')} {inp.get('label') or inp.get('words') or inp.get('path') or ''})".strip()
    return None


def _step_words(aid: str, parsed: dict, spec: dict, base: Path) -> str:
    cy = ROOT / "routine" / "cycles.py"
    out = [f"This step, from your cycle plan of {parsed['stamp']} (step {parsed['k']}):",
           f"- goal: {spec.get('goal', parsed.get('goal', ''))}",
           f"- done means: {spec.get('done_means', '')}",
           f"- what you may do: {spec.get('may', 'one look or one action inside your limits')}",
           f"- escalate when: {spec.get('escalate_when', 'anything outside your limits comes up')}",
           "Its inputs, as they are now (checked against the plan before this run started; nothing else is loaded):"]
    for inp in spec.get("inputs") or []:
        out.append(f"\n[{inp.get('kind')} {inp.get('label') or inp.get('words') or inp.get('path') or ''}]\n{resolve(inp, base)}")
    out.append(f"\nA small step makes no new steps and plans nothing. End with python3 \"{cy}\" done {aid} {parsed['k']} \"what came of it\" "
               f"(or python3 \"{cy}\" failed {aid} {parsed['k']} \"why\" when the check failed, or an ask when it's outside your limits).")
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
    end = f"End with one line in your ledger: python3 \"{ROOT / 'routine' / 'ledger.py'}\" {aid} note \"{parsed['name']}: what you did\"."
    if parsed["mode"] == "mark":
        return (f"This run: one row, {label}. The review passed it, so your mark comes second. Nothing else is loaded.\n\nThe row:\n{ask}\n\n"
                f"Hold it against your ready check yourself. It holds: python3 \"{ROOT / 'routine' / 'sprint.py'}\" ready {label}. "
                f"It doesn't, or the mark is refused: nothing is forced, it goes to him: {sit}\n{end}")
    finds = "\n".join(f"- {f}" for f in st.get("findings") or []) or "- (no findings written)"
    return (f"This run: round {parsed['round']} of at most {review.ROUNDS} today on one row of the planning, {label}. The review flagged it. "
            f"Nothing else is loaded; look up only what a finding needs.\n\nThe row:\n{ask}\n\nThe review's findings:\n{finds}\n\n"
            "For each finding, one of two:\n"
            f"- You can ground it (his words with a date, a rule, a planning row, the code): improve the row, naming the source: "
            f"python3 \"{rv}\" reword {label} '{{\"edits\": [{{\"old\": \"the exact words\", \"new\": \"the new words\"}}]}}' (this one row only; a shared file is "
            "written no other way). The review looks again by itself.\n"
            f"- Only he can answer it (his words are missing, a choice that's his, a number you'd pick): you never fill it in, not even marked as yours. {sit} "
            "That's his one text, and the loop stops for this row. All the open points of the row in that one command.\n"
            f"Never mark it ready in this round: the review's pass comes first, and your mark gets its own run after it.\n{end}")


def _norm_goal(g: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", " ".join(str(g).lower().split()))[:120]


def plan(aid: str, raw: str, now: dt.datetime | None = None, base: Path | None = None, job: int | None = None) -> str:
    """The bigger session's plan: checked, written in her ledger, its steps planned as one-off priority items with
    their inputs fingerprinted. Refuses (ValueError) a plan with too many picks or steps, or a step without its goal,
    done_means or time."""
    now = now or dt.datetime.now()
    base = base or folder()
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
    if len(steps) > most:
        raise ValueError(f"at most {most} steps a day for you")
    lo, hi = a.get("hours") or ["08:00", "22:00"]
    for i, st in enumerate(steps, 1):
        if not isinstance(st, dict) or not str(st.get("goal", "")).strip() or not str(st.get("done_means", "")).strip():
            raise ValueError(f"step {i} needs its goal and what done means")
        at = str(st.get("at", "")).strip()
        if not re.fullmatch(r"\d{1,2}:\d\d", at):
            raise ValueError(f"step {i} needs a time today, HH:MM")
        st["at"] = _hhmm(at)
        if not (_t(lo) <= _t(st["at"]) < _t(hi)):
            raise ValueError(f"step {i}'s time {st['at']} is outside your hours {lo} to {hi}")
        st["inputs"] = [x for x in (st.get("inputs") or []) if isinstance(x, dict) and x.get("kind")]
    # the share: a session that would push her over it plans fewer steps
    sh = shares(aid, now, base)
    d = _state()
    st_ = _agent_state(d, aid)
    stamp = now.strftime("%Y-%m-%d %H:%M")
    kept, trip = [], []
    for i, st in enumerate(steps, 1):
        g = _norm_goal(st["goal"])
        before = st_["goals"].get(g) or {}
        if before.get("tries", 0) >= 1 and not before.get("done"):
            trip.append(st["goal"])
            tripwire(aid, "same goal twice", f"\"{st['goal']}\" was tried before without getting done; the step waits for his word", now, base, d)
            continue
        kept.append((i, st))
    stamp_items = []
    for i, st in kept:
        fps = [_fp(resolve(x, base)) for x in st["inputs"]]
        text = step_text(aid, stamp, i, st["goal"])
        when = f"today {st['at']}" if _t(st["at"]) > now.time() else "now"
        code, out = _schedule("add", when, text, "--priority", "--kind", f"step-{aid}")
        m = re.search(r"Item (\d+) is planned", out)
        st_["steps"][f"{aid}|{stamp}|{i}"] = {"spec": st, "fps": fps, "day": now.strftime("%Y-%m-%d"), "item": int(m.group(1)) if m else None,
                                             "state": "planned" if code == 0 else "not planned", "stamp": stamp}
        g = _norm_goal(st["goal"])
        st_["goals"][g] = {"tries": (st_["goals"].get(g) or {}).get("tries", 0) + 1, "done": False, "at": stamp}
        stamp_items.append(f"step {i} planned at {st['at']}" + ("" if code == 0 else f" (not planned: {out[:80]})"))
    for n in p.get("orders_done") or []:
        try:
            ledger.set_order(aid, int(n), "planned", f"in the plan of {stamp}")
        except Exception:
            pass
    _save_state(d)
    p["stamp"] = stamp
    p["steps"] = [st for _, st in kept]
    title = ledger.write_plan(aid, p, job, now)
    for q_ in (p.get("questions") or [])[:QUESTIONS_MOST]:
        ask(aid, str(q_), now, base)
    return (f"Plan written in {aid}'s ledger ({title}): {len(picks)} picks, {len(kept)} steps" + (f" ({', '.join(stamp_items)})" if stamp_items else "")
            + (f"; {len(trip)} step(s) held: the same goal was tried before without done" if trip else "") + ".")


def step_done(aid: str, k: int, what: str, failed: bool = False, now: dt.datetime | None = None, base: Path | None = None) -> str:
    """A small step says what came of it (her own run writes it): the ledger, the goal's record, a check failing
    twice as a tripwire."""
    now = now or dt.datetime.now()
    d = _state()
    st_ = _agent_state(d, aid)
    cands = [(key, v) for key, v in st_["steps"].items() if key.endswith(f"|{k}") and v.get("state") not in ("stale",)]
    cands.sort(key=lambda kv: kv[1].get("stamp", ""))
    key, rec = (cands[-1] if cands else (None, None))
    goal = (rec or {}).get("spec", {}).get("goal", f"step {k}")
    g = _norm_goal(goal)
    gr = st_["goals"].setdefault(g, {"tries": 1, "done": False})
    if failed:
        gr["failed"] = gr.get("failed", 0) + 1
        if rec is not None:
            rec["state"] = "failed"
        ledger.note(aid, f"step {k} failed: {what}")
        if gr["failed"] >= 2:
            tripwire(aid, "a check failing twice", f"the check of \"{goal}\" failed twice ({what[:120]}); the step waits for his word", now, base, d)
    else:
        gr["done"] = True
        if rec is not None:
            rec["state"] = "done"
        ledger.note(aid, f"step {k} done: {what}")
    _save_state(d)
    return f"Step {k} {'failed' if failed else 'done'}, written in {aid}'s ledger."


# -- texts: asks, batches, tripwires ------------------------------------------------------------------------------------------

def _today(now: dt.datetime) -> str:
    return now.strftime("%Y-%m-%d")


def ask(aid: str, text: str, now: dt.datetime | None = None, base: Path | None = None) -> str:
    """One question for him on her line, in if-then shape, never the same one twice in a day. Donna's goes into her
    next batch (unless she has no batches); the others' go now."""
    now = now or dt.datetime.now()
    text = " ".join(str(text).split())
    if not text:
        return "An ask needs words."
    d = _state()
    st_ = _agent_state(d, aid)
    key = _norm_goal(text)
    asked = st_["asked"]
    if asked.get(key) == _today(now):
        _save_state(d)
        return "Already asked today; not asked again."
    asked[key] = _today(now)
    a = agent_settings(aid, base)
    ledger.note(aid, f"escalated: {text}")
    if a.get("batches"):
        st_["batch"].append({"text": text, "at": now.strftime(FMT)})
        _save_state(d)
        return f"Queued for {aid}'s next batch ({', '.join(a['batches'])})."
    _save_state(d)
    send(aid, text, "cycle-ask", base)
    return f"Asked on {aid}'s line."


def batch(aid: str, text: str, now: dt.datetime | None = None, base: Path | None = None) -> str:
    now = now or dt.datetime.now()
    text = " ".join(str(text).split())
    if not text:
        return "A batch text needs words."
    a = agent_settings(aid, base)
    d = _state()
    st_ = _agent_state(d, aid)
    if not a.get("batches"):
        _save_state(d)
        send(aid, text, "cycle", base)
        return f"{aid} has no batches: sent on her line now."
    st_["batch"].append({"text": text, "at": now.strftime(FMT)})
    _save_state(d)
    return f"Queued for {aid}'s next batch ({', '.join(a['batches'])})."


def send_batches(now: dt.datetime | None = None, base: Path | None = None, log=None) -> list[str]:
    """At each batch time (within the quarter after it), what's queued goes out as one text."""
    now = now or dt.datetime.now()
    d = _state()
    did = []
    for aid, a in settings(base)["agents"].items():
        st_ = _agent_state(d, aid)
        for t in a.get("batches") or []:
            bt = now.replace(hour=_t(t).hour, minute=_t(t).minute, second=0, microsecond=0)
            key = f"{_today(now)} {t}"
            if bt <= now < bt + dt.timedelta(minutes=15) and st_.get("batch_sent") != key:
                st_["batch_sent"] = key
                if st_["batch"]:
                    texts = [x["text"] for x in st_["batch"]]
                    st_["batch"] = []
                    send(aid, " ".join(texts) if len(texts) == 1 else "\n".join(f"- {x}" for x in texts), "cycle-batch", base)
                    ledger.note(aid, f"batch at {t}: {len(texts)} text(s) sent")
                    did.append(f"{aid}'s {t} batch: {len(texts)} text(s)")
    _save_state(d)
    if log:
        for x in did:
            log(f"cycles: {x}")
    return did


TRIPWIRE_WORDS = {
    "same goal twice": "If you want me to keep at it, say go and I'll try once more in my next session; if not, I let it go until you bring it back.",
    "boxed twice in a row": "If this is worth more time, say so and I'll give it a bigger box next time; if not, I drop it and plan smaller steps.",
    "a refused command or push": "If that's something you want done, say go and I'll put it to you as a question first; if not, I leave it.",
    "a check failing twice": "If you want me to try another way, say so; if not, I let it go until Friday.",
    "an action outside my limits": "If you want it done, say yes and I'll do exactly that; if not, I leave it as it is.",
    "a write to a shared file outside the serialized place": "If you want that change, say go and I'll make it through HQ's own scripts; if not, nothing changed.",
    "a Ready mark refused on its fields": "If you give me the quote and the sources I'll mark it ready; if not, it stays on the sit-down list for Friday.",
}


def tripwire(aid: str, kind: str, detail: str, now: dt.datetime | None = None, base: Path | None = None, d: dict | None = None) -> str:
    """Counted by the runner: a line in her ledger, and one message on her line in if-then shape, at most her texts
    a day; past that, the ledger only. A caller holding the state passes it (d) and saves it itself."""
    now = now or dt.datetime.now()
    own = d is None
    d = _state() if own else d
    st_ = _agent_state(d, aid)
    ledger.note(aid, f"tripwire ({kind}): {detail}")
    today = _today(now)
    sent = st_["texts"].get(today, 0)
    most = int(agent_settings(aid, base).get("tripwire_texts", 2))
    if sent >= most:
        if own:
            _save_state(d)
        return "ledger only (the day's texts are used up)"
    st_["texts"][today] = sent + 1
    if own:
        _save_state(d)
    msg = f"A tripwire on my side: {kind}: {detail}. {TRIPWIRE_WORDS.get(kind, 'Say what you want me to do, and I do that.')}"
    send(aid, msg, "tripwire", base)
    return "texted"


# -- after a run: the ledger, the tripwires, the streaks ---------------------------------------------------------------------

def after_run(job: dict, parsed: dict, now: dt.datetime | None = None, base: Path | None = None, run_dir: str | None = None, log=None) -> dict:
    """A finished cycle job, once: its box note into her ledger (minutes, turns, boxed), the tripwires the stream
    shows (refused, outside her limits, a shared file written directly, a Ready mark refused), boxed twice in a row."""
    now = now or dt.datetime.now()
    aid = parsed["agent"]
    d = _state()
    st_ = _agent_state(d, aid)
    if job["n"] in st_["processed"]:
        return {}
    st_["processed"] = (st_["processed"] + [job["n"]])[-200:]
    if str(job["n"]) in st_["skipped"]:  # gatekeep stopped it before it ran and already wrote why
        _save_state(d)
        return {}
    run_dir = run_dir or os.environ.get("HQ_JOB_RUN") or os.path.join(hqpaths.HQ, "scratch", "routine")
    note = {}
    try:
        note = json.loads(Path(run_dir, f"job-{job['n']}.box.json").read_text(encoding="utf8"))
    except (OSError, ValueError):
        pass
    cost = ""
    try:
        import estimate
        h = next((h for h in estimate.history() if h.get("n") == job["n"]), None)
        if h and h.get("cost"):
            cost = f", cost {h['cost'].get('weekly', 0):g}% of the week"
    except Exception:
        pass
    state = job.get("state", "")
    how = ("boxed at its " + note["boxed"]) if note.get("boxed") else ("done" if state.startswith("done") else state.split(" ")[0] or "ended")
    line = f"run: {how} · {note.get('minutes', '?')} min, {note.get('turns', '?')} turns, {note.get('steps', '?')} tool steps{cost} (job {job['n']})"
    ledger.entry(aid, f"{parsed['name']} ran (job {job['n']})", [line], now)
    if parsed["kind"] == "step":
        rec = st_["steps"].get(_step_key(parsed))
        if rec is not None and rec.get("state") in ("planned", "started"):
            rec["state"] = "boxed" if note.get("boxed") else "ended without saying what came of it"
            ledger.note(aid, f"step {parsed['k']}: {rec['state']}")
    # boxed twice in a row
    if note.get("boxed"):
        st_["boxed_streak"] = st_.get("boxed_streak", 0) + 1
        if st_["boxed_streak"] >= 2:
            tripwire(aid, "boxed twice in a row", f"two runs in a row ended at their box ({parsed['name']} at its {note['boxed']})", now, base, d)
            st_["boxed_streak"] = 0
    else:
        st_["boxed_streak"] = 0
    if parsed["kind"] == "fix":  # F86: what the row's own words say (a "refused", a push.py) is no refusal or action of hers
        ledger.note(aid, f"{parsed['name']}: " + (f"cut off ({note.get('boxed') or state}); the row stays flagged and not ready, the round counts"
                                                  if note.get("boxed") or state.startswith("ended") else "ended; the review looks again if the words changed"))
        said = ("reword", "sitdown", "sprint.py show", "sprint.py fields")
        note = {**note, "refused": [r for r in note.get("refused") or [] if not any(w in r.get("tool", "") for w in said)],
                "tools": [t for t in note.get("tools") or [] if not any(w in t for w in said)]}
    # refused, outside her limits, a shared file written directly, a Ready mark refused
    for r in note.get("refused") or []:
        if "sprint.py ready" in r.get("tool", "") and aid == "moneypenny":
            tripwire(aid, "a Ready mark refused on its fields", r.get("said", "")[:160], now, base, d)
        else:
            tripwire(aid, "a refused command or push", f"{r.get('tool', '')[:80]}: {r.get('said', '')[:120]}", now, base, d)
        break
    for t in note.get("tools") or []:
        m = _EDIT.match(t)
        if m and any(m.group(2).replace(os.sep, "/").endswith(x) for x in SHARED):
            tripwire(aid, "a write to a shared file outside the serialized place", f"{m.group(1)} on {m.group(2)[-80:]}", now, base, d)
            break
    for t in note.get("tools") or []:
        if _OUTSIDE.search(t):
            tripwire(aid, "an action outside my limits", t[:160], now, base, d)
            break
    _save_state(d)
    if log:
        log(f"cycles: job {job['n']} ({aid}, {parsed['name']}) {how}")
    return note


# -- orders from a call or a text --------------------------------------------------------------------------------------------

def order(aid: str, kind: str, words: str, now_: bool = False, now: dt.datetime | None = None, base: Path | None = None) -> str:
    now = now or dt.datetime.now()
    base = base or folder()
    o = ledger.add_order(aid, kind, words, now_, now)
    if kind == "stop":
        # her matching waiting steps are cancelled at once, and it goes on her let-go
        items, jobs_ = _items()
        want = set(_norm_goal(words).split())
        n = 0
        for i in items:
            p = parse(i["text"])
            if i["state"] == "waiting" and p["agent"] == aid and p["kind"] == "step" and want & set(_norm_goal(p["goal"]).split()):
                _schedule("cancel", str(i["n"]))
                n += 1
        for j in jobs_:
            p = parse(j["text"])
            if (j["state"] == "ready" or j["state"].startswith("held")) and p["agent"] == aid and p["kind"] == "step" and want & set(_norm_goal(p["goal"]).split()):
                _jobs("stop", str(j["n"]))
                n += 1
        ledger.note(aid, f"let go, on his order: \"{words}\" ({n} step(s) cancelled)")
        return f"Stopped: {n} of {aid}'s steps cancelled; \"{words}\" is on her let-go list until she brings it back to him."
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
    if now_:
        a = agent_settings(aid, base)
        d = _state()
        st_ = _agent_state(d, aid)
        stamp = now.strftime("%Y-%m-%d %H:%M")
        k = 0
        spec = {"goal": words, "done_means": "what he asked for is done, or put to him as a question", "inputs": [], "may": "one look or one action inside your limits", "at": now.strftime("%H:%M")}
        st_["steps"][f"{aid}|{stamp}|{k}"] = {"spec": spec, "fps": [], "day": now.strftime("%Y-%m-%d"), "state": "planned", "stamp": stamp, "order": o["n"]}
        _save_state(d)
        code, out = _schedule("add", "now", step_text(aid, stamp, k, words), "--priority", "--kind", f"step-{aid}")
        ledger.set_order(aid, o["n"], "planned", "a step at once")
        return f"Now: a step for {aid} planned at once ({out.splitlines()[0][:100] if out else code})."
    return f"Noted for {aid}'s next bigger session: \"{words}\"."


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
        if any(i["state"] == "waiting" and i["text"] == text for i in items):
            continue
        ff = first_friday(now)
        at = ff.replace(hour=_t(r.get("at", "09:00")).hour, minute=_t(r.get("at", "09:00")).minute, second=0, microsecond=0)
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
    send(aid, "My monthly review, for your yes or no (nothing changed by itself): " + text, "cycle-review", base)
    return f"Proposal written in {aid}'s ledger and sent on her line; nothing changed."


def write_scores(now: dt.datetime | None = None, base: Path | None = None, force: bool = False, log=None) -> list[str]:
    """Every week (Friday from 7 in the morning, once), each agent's score into her ledger."""
    now = now or dt.datetime.now()
    import pokes
    d = _state()
    week = (now - dt.timedelta(days=1)).strftime("%G-W%V")
    did = []
    if not force and not (now.weekday() == 4 and now.hour >= 7):
        return did
    for ag in _agents(base):
        aid = ag["id"]
        if not agent_settings(aid, base).get("on") and not force:
            continue
        st_ = _agent_state(d, aid)
        if st_.get("scored") == week and not force:
            continue
        sc = pokes.score(ag, now, folder=base or folder(), plan=ledger.plan(aid)[1])
        ledger.write_score(aid, week, {"pokes": sc["pokes"], "measures": sc["measures"]}, sc["lines"], now)
        st_["scored"] = week
        did.append(f"{aid}'s score for {week} written")
    _save_state(d)
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
        if p and j["state"].startswith(q.FINISHED):
            out.append((j, p))
    return out


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
            if not in_hours(a, now) and now.time() >= _t((a.get("hours") or ["08:00", "22:00"])[1]):
                gatekeep(j, now, base, log)
                did.append(f"job {j['n']} dropped at the hours' end")
    return did


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
    if not a.get("on") or not a.get("fix") or not in_hours(a, now) or not _agent(aid, base):
        return []
    import jobs as q
    import review
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
    if sh["daily_used"] + est > sh["daily_share"] or sh["weekly_used"] + est > sh["weekly_share"]:
        d = _state()
        st_ = _agent_state(d, aid)
        if st_.get("fix_waits") != _today(now):
            st_["fix_waits"] = _today(now)
            ledger.note(aid, f"{pick['label']} waits for the next day's share ({sh['daily_used']:g} of {sh['daily_share']:g} points today, "
                             f"{sh['weekly_used']:g} of {sh['weekly_share']:g} this week, a round about {est:g})")
        _save_state(d)
        return did + [f"{pick['label']} waits for the next day's share"]
    code, out = _schedule("add", "now", fix_text(aid, pick["label"], pick["mode"], pick["round"]), "--priority", "--kind", f"step-{aid}")
    if code:
        return did + [f"{pick['label']}: not planned ({out[:80]})"]
    review.round_started(pick, now.timestamp())
    did.append(f"{pick['label']} {'mark' if pick['mode'] == 'mark' else 'round ' + str(pick['round'])} planned")
    if log:
        log(f"cycles: {did[-1]} (F86)")
    return did


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
        done = []
        for j, p in finished_cycle_jobs():
            if after_run(j, p, now, base, log=log):
                done.append(j["n"])
        out["processed"] = done
    except Exception as e:
        out["processed"] = [f"error: {e!r}"]
    for name, fn in (("batches", send_batches), ("dropped", drop_waiting), ("reviews", plan_reviews), ("scores", write_scores), ("fixes", fix_rounds)):
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
                   + "".join(f"; {lk['name']} {lk.get('every', 'day')} at {lk['at']}" for lk in a.get("looks") or []))
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
    try:
        if cmd == "settings":
            print(settings_words())
        elif cmd == "set" and len(rest) == 3:
            print(set_setting(rest[0], rest[1], rest[2]))
        elif cmd == "order" and len(rest) >= 3:
            print(order(rest[0].lower(), rest[1].lower(), rest[2], now_="--now" in rest))
        elif cmd == "plan" and len(rest) == 2:
            print(plan(rest[0].lower(), rest[1], job=int(os.environ.get("HQ_JOB") or 0) or None))
        elif cmd in ("done", "failed") and len(rest) == 3 and rest[1].isdigit():
            print(step_done(rest[0].lower(), int(rest[1]), rest[2], failed=cmd == "failed"))
        elif cmd == "ask" and len(rest) == 2:
            print(ask(rest[0].lower(), rest[1]))
        elif cmd == "batch" and len(rest) == 2:
            print(batch(rest[0].lower(), rest[1]))
        elif cmd == "text" and len(rest) == 2:
            print(tripwire_free_text(rest[0].lower(), rest[1]))
        elif cmd == "proposal" and len(rest) == 2:
            print(proposal(rest[0].lower(), rest[1]))
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
        else:
            print(__doc__)
            return 2
    except ValueError as e:
        print(f"Refused: {e}")
        return 2
    return 0


def tripwire_free_text(aid: str, text: str, now: dt.datetime | None = None, base: Path | None = None) -> str:
    """A run's own text on her line now (for what breaks through), inside the day's cap of texts."""
    now = now or dt.datetime.now()
    d = _state()
    st_ = _agent_state(d, aid)
    today = _today(now)
    most = int(agent_settings(aid, base).get("tripwire_texts", 2))
    if st_["texts"].get(today, 0) >= most:
        _save_state(d)
        return "Not sent: the day's texts are used up; it goes in the ledger only."
    st_["texts"][today] = st_["texts"].get(today, 0) + 1
    _save_state(d)
    ledger.note(aid, f"texted: {text}")
    send(aid, text, "cycle", base)
    return f"Sent on {aid}'s line."


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
