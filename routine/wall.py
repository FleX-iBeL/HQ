#!/usr/bin/env python3
"""F100, piece 2 of the foundation (31 October 2026): the usage wall. His rule: he never wakes up to burned usage, and he
comes first when it's tight. His words: "yes exactly, i want here we put it on our roadmap and planning, and then we run these
first." and "daytime building is only allowed if i manually say it is."

What's here, read by the routine's minute (tick.py), the runner (runjob.py) and the queue (jobs.py):
  - the box: every job a limit in minutes and turns from its estimate's latest end; a job with no estimate 60 minutes (his
    words, 31 October 2026: "up to you, if you think 60 is good"). It counts the job's own work, not the test run that proves
    it (proof.py marks that time), so a build is never stopped by its own tests. Past it: `boxed`, parked for a call.
  - a resume gives a job stopped by its box more time and turns, RAISE times; it never takes the limit away. At most two resumes,
    then the job stops for good and the item gets split, and in all its time never goes past four times its first estimate. His
    words, 31 October 2026: "yes stop after 2 resumes sound good, if that means in total it could get 4x it's initial estimate." The
    first box stands when four times the estimate is smaller than it; a job with no estimate gets 240 minutes in all. Turns follow
    the same limit. The usage pause is another stop and doesn't rise: four times the top of the estimate (H220, H221), and a job
    paused for its usage can't be resumed: it stops for good and the item gets split. Held at a usage stop line (H113) is
    a third thing: that job carries on by itself when there's room.
  - his day: between 8:00 and 22:00 no build starts without his stored say-so, with who and when (jobs.py now N).
  - a held job doesn't restart at night unless it was planned for the night, or he resumed it himself.
  - at most WIP items in progress: the next build waits until one is through QA.
  - the order when it's tight: him live, the small routines (neither ever pass a gate), then the agents' cycles, then the
    team. The reserve, taken off the stop lines for the last two, is on the roadmap (**Usage reserve: 15 points.**, usageline.py).
  - pause (jobs.py pause): the running job held, nothing new starts, and no reviewer or first look starts.

The gate itself is status/save-usage.mjs: a reading older than 30 minutes stops it, and --reserve takes the reserve off.
Off only for a test: HQ_NO_WALL under HQ_UNDER_TEST (the happy flows set it, so the flows from before keep to one thing; a
wall flow takes it out again). HQ_WALL_HOUR pins the hour for a test.

[The numbers that aren't his: BOX_OVER 1.5 (the review's example: 2 jobs in 10 run past their latest end), BOX_MIN 20, RAISE 2,
TURNS_A_MINUTE 15 (on the server's headless runs the middle is 6 a minute, the most 16), BOX_LEFT 5. His: 60, two resumes, four times,
240, 8:00 to 22:00, 30 minutes. WIP 3 is the design's. The reserve's 15 is Fable's, his to turn.]
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402

DAY = (8, 22)         # his words, 30 October 2026: "Daytime is 8:00 to 22:00"
BOX_NONE = 60         # minutes, a job with no estimate
BOX_OVER = 1.5        # the box is the estimate's latest end times this
BOX_MIN = 20          # never a smaller box than this
BOX_LEFT = 5          # minutes a job carrying on always gets
TURNS_A_MINUTE = 15
RAISE = 2             # a resume multiplies the limits by this
MOST_RESUMES = 2      # his words: "stop after 2 resumes"
MOST_TIMES = 4        # his words: "in total it could get 4x it's initial estimate"
NO_ESTIMATE_ALL = 240  # minutes in all for a job with no estimate: four times its 60
WIP = 3
PROOF_MAX = 3600      # a test run that says it's still on after this long has died
BUILDS = ("build", "bigbuild")
_PLANNED = re.compile(r"^scheduled item \d+, planned for [^:]*?(\d\d):\d\d:", re.I)


def off() -> bool:
    return hqpaths.under_test() and bool(os.environ.get("HQ_NO_WALL"))


def _dir() -> str:
    import usagecost
    return usagecost.DIR


def hour(now=None) -> int:
    pin = os.environ.get("HQ_WALL_HOUR") if hqpaths.under_test() else None
    if pin:
        return int(pin)
    return time.localtime(now).tm_hour if now else time.localtime().tm_hour


def daytime(now=None) -> bool:
    return DAY[0] <= hour(now) < DAY[1]


def _is_cycle(job) -> bool:
    import cycles
    return bool(cycles.is_cycle_job(job))


def kind_of(job) -> str:
    import estimate as E
    return E.kind_for(job.get("text", ""), (E._load_state().get(str(job["n"])) or {}).get("kind"))


def is_build(job) -> bool:
    return not _is_cycle(job) and kind_of(job) in BUILDS


def planned_night(job) -> bool:
    """A job from a planned item whose time is in the night."""
    m = _PLANNED.match(job.get("text", ""))
    return bool(m) and not DAY[0] <= int(m.group(1)) < DAY[1]


def in_progress(jobs, leave_out=None) -> set:
    """The items in progress: a QA or a fix waiting or running, and a build that started and isn't through (running,
    held, paused or boxed). A build still waiting for its first start isn't in progress."""
    import jobs as q
    import qa
    out = set()
    for j in jobs:
        if j["state"].startswith(q.FINISHED) or (leave_out and j["n"] == leave_out):
            continue
        t = j.get("text", "")
        started = not j["state"].startswith("ready")
        if t.startswith(("QA of ", "Fix for ")) or (started and is_build(j)):
            out.add(qa.job_label(t) or f"job {j['n']}")
    return out


def why_not(job, jobs, now=None) -> str | None:
    """Why this waiting job doesn't start now, whatever the usage says, or None."""
    if off() or _is_cycle(job):
        return None
    day = daytime(now)
    if job["state"].startswith("held") and not day and not job["state"].startswith(("held: resumed", "held: paused")) and not planned_night(job):
        return "held, and a held job doesn't restart at night unless it was planned for the night; it can go on in the morning"
    if not is_build(job):
        return None
    if day and not job.get("sayso"):
        return f"no build starts between {DAY[0]}:00 and {DAY[1]}:00 without his say-so; it waits for the night, or jobs.py now {job['n']}"
    import qa
    busy = in_progress(jobs, leave_out=job["n"])
    label = qa.job_label(job.get("text", ""))
    if len(busy) >= WIP and label not in busy:
        return f"{len(busy)} items are in progress ({', '.join(sorted(busy))}), the most at once; it waits until one is through QA"
    return None


def order(line) -> list:
    """Who goes first when it's tight: the agents' cycles, then the team, each in its place in line."""
    if off():
        return list(line)
    return [j for j in line if _is_cycle(j)] + [j for j in line if not _is_cycle(j)]


# ---------- the box ----------

def _boxes_path() -> str:
    return os.path.join(_dir(), "job-box.json")


def _boxes() -> dict:
    try:
        return json.load(open(_boxes_path()))
    except (OSError, ValueError):
        return {}


def _save_boxes(d) -> None:
    os.makedirs(_dir(), exist_ok=True)
    tmp = f"{_boxes_path()}.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=1)
    os.replace(tmp, _boxes_path())


def estimate_of(job):
    """(the likely minutes, the latest end), with the guesses taken in; (None, None) when the job has no estimate."""
    import estimate as E
    n, text = job["n"], job.get("text", "")
    e = E.known(n)
    if not e.get("est"):
        return None, None
    hist = E.all_history()
    d = E.job_estimate(n, text, hist)
    guess, _, fit = E.pick_guess(e, E.guess_fits(hist))
    est = E.with_guess(d["est"], guess, fit)
    return est, max(d["latest"], E.latest_of(est, d["kind"], hist))


def latest_minutes(job):
    return estimate_of(job)[1]


def box_for(job) -> dict | None:
    """{"minutes", "turns", "total", "raised", "cap", "resumes"}: what's left of job's box. The first estimate and the first box are
    kept the first time they're asked, so a later estimate never moves the limit. None under a test without the wall."""
    if off():
        return None
    d = _boxes()
    rec = d.get(str(job["n"])) or {}
    if "first_box" not in rec:
        try:
            est, lat = estimate_of(job)
        except Exception:
            est, lat = None, None
        rec.update(first_est=est, first_box=BOX_NONE if lat is None else max(BOX_MIN, math.ceil(lat * BOX_OVER)))
        d[str(job["n"])] = rec
        _save_boxes(d)
    first, raised, used = rec["first_box"], rec.get("raised") or 1, rec.get("minutes") or 0
    cap = _cap(rec)
    total = min(cap, first * raised)
    left = total - used
    if left < BOX_LEFT:  # a job carrying on always gets a little, but never past the most it can have
        left = min(BOX_LEFT, cap - used)
    left = max(0.1, left)
    turns = min(math.ceil(left * TURNS_A_MINUTE), math.ceil(total * TURNS_A_MINUTE) - (rec.get("turns") or 0))
    return {"minutes": round(left, 1), "turns": max(1, turns), "total": total, "raised": raised, "cap": cap, "resumes": rec.get("resumes") or 0}


def _cap(rec) -> float:
    """The most a job gets in all: four times its first estimate, the first box when that's smaller."""
    est = rec.get("first_est")
    return NO_ESTIMATE_ALL if est is None else max(rec.get("first_box") or 0, MOST_TIMES * est)


def no_resume(n) -> str | None:
    """Why job n can't be resumed, in words a job, an agent and he can read; None when it can."""
    rec = _boxes().get(str(n)) or {}
    if (rec.get("resumes") or 0) >= MOST_RESUMES:
        return (f"Job {n} has had its {MOST_RESUMES} resumes, the most a job gets, so it stops here for good. What it wrote stays. "
                "The item gets split into smaller pieces on the planning.")
    if "first_box" in rec and (rec.get("minutes") or 0) >= _cap(rec):
        return (f"Job {n} has used all its time, {MOST_TIMES} times its first estimate at the most, so it stops here for good. What it "
                "wrote stays. The item gets split into smaller pieces on the planning.")
    return None


def used_too_much(n) -> str:
    """What jobs.py resume N says for a job paused for its usage."""
    return (f"Job {n} used too much of the usage, about four times the most it was expected to take, so it can't be resumed. It stops "
            f"here for good. What it wrote stays. The item gets split into smaller pieces on the planning; stop {n} takes it off the list.")


def what_next(n) -> str:
    """The sentence for his text about a paused or boxed job."""
    if no_resume(n):
        return "It has had all the room it gets, so it stops here for good; what it wrote stays and the item needs splitting."
    return "It won't start again by itself; tell me on a call if it should carry on or be dropped."


def add_used(n, minutes, turns=0) -> None:
    """What a run of the job used of its box: its own minutes, the test runs left out."""
    d = _boxes()
    rec = d.setdefault(str(n), {})
    rec["minutes"] = round((rec.get("minutes") or 0) + max(0, minutes), 2)
    rec["turns"] = (rec.get("turns") or 0) + max(0, turns)
    _save_boxes(d)


def raise_box(n) -> int:
    """jobs.py resume N: its box grows RAISE times, on top of what it had, up to the most it can have (box_for)."""
    d = _boxes()
    rec = d.setdefault(str(n), {})
    rec["raised"] = (rec.get("raised") or 1) * RAISE
    rec["resumes"] = (rec.get("resumes") or 0) + 1
    _save_boxes(d)
    return rec["raised"]


def carry_over(n, to) -> None:
    """A crash's rerun goes on with the job's box: what it used, its resumes and its first estimate."""
    d = _boxes()
    if str(n) in d:
        d[str(to)] = dict(d[str(n)])
        _save_boxes(d)


def forget(n) -> None:
    d = _boxes()
    if d.pop(str(n), None) is not None:
        _save_boxes(d)
    try:
        os.remove(_proof_path(n))
    except OSError:
        pass


# ---------- the test run isn't part of the box ----------

def _proof_path(n) -> str:
    return os.path.join(_dir(), f"job-{n}-proof-time.json")


def _proof(n) -> dict:
    try:
        return json.load(open(_proof_path(n)))
    except (OSError, ValueError):
        return {}


def proof_start(n) -> None:
    os.makedirs(_dir(), exist_ok=True)
    json.dump({**_proof(n), "since": time.time()}, open(_proof_path(n), "w"))


def proof_end(n) -> None:
    d = _proof(n)
    if d.get("since"):
        d["spent"] = (d.get("spent") or 0) + max(0, time.time() - d["since"])
        d["since"] = None
        json.dump(d, open(_proof_path(n), "w"))


def proof_seconds(n, now=None) -> float:
    """The seconds job n spent in its own test run so far, the one on now included."""
    d, now = _proof(n), now or time.time()
    return (d.get("spent") or 0) + (min(now - d["since"], PROOF_MAX) if d.get("since") else 0)
