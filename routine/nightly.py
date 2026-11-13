#!/usr/bin/env python3
"""The nightly run (H169, 16 October 2026): every night, all the detailed flows, to find bugs.

The user on the call of 16 October 2026 at 11:56: "I was thinking maybe we can each night, during those usage
hours, just run all the flows or something like that and just find bugs. ... We don't have to plan those
maintenance moments because we just do it daily whenever we have space." and "Maybe we do the nightly check at
2 am". A repeating planned item (H171) carries one job text (in the H169 row); that job runs this script:

  python3 "routine/nightly.py" run          on the main only: round 1, the detailed flows for this computer, no Claude
                                            turns. All pass: one line in the H169 row's nights, exit 0, nothing else.
                                            One fails: the failed flows and the log, exit 1 (the job fixes them all).
                                            Not the main: says so, changes nothing, exit 0.
  python3 "routine/nightly.py" again        the next full run of tonight (round 2, then 3), only after every flow the
                                            round before found is fixed. All pass: exit 0. Still failing with a round
                                            left: exit 1 (fix all again). Still failing after round 3: exit 3 (hold).
  python3 "routine/nightly.py" set          which flows this computer runs
  python3 "routine/nightly.py" log "LINE"   one line in the H169 row's nights (the job, after its fix)
  python3 "routine/nightly.py" morning "TEXT"  a short plain line Moneypenny texts him at 08:00 (H266; Donna without her) (the next one)
  python3 "routine/nightly.py" tutorial     after the flows, every night (H227): what changed in HQ since the last
                                            tutorial read (commits and the files they touched), and where the
                                            tutorial is, to read it against what HQ does now
  python3 "routine/nightly.py" tutorial done  the read is done: the next one starts from here

The set: on a Mac every flow without Claude turns (--quick); elsewhere the Linux nightly set (flowsets.LINUX_NIGHTLY: every quick flow that holds on Linux).
11 November 2026, his words: "No the 17 happy flows should only run once at night in the nightly run". With whole_build_review on
(routine/wholebuild.py), after the detailed set the 17 happy flows (happy.gate_args, for real, with the model) run here, on dev as it stands,
their own log next to the night's (happy_at_night, _happy_run); a red or untried one is one of the night's failures, so the night is red,
the release holds, and it becomes the night's own repair item like any failure. A build's record and the whole-build review run none of them.
The flows with Claude turns stay out: they need a live voice and cost usage, and the daytime builds run them.
[Claude's choice.] Each run's output is kept in scratch/nightly/ (the last 14 nights).

Rounds (H226, 22 October 2026). The user on the call at 11:37: "they fix the 3 bugs, and then at the end they run it
again, they might find another thing. They fix all those bugs again and then they run another time. If that time it
still finds bugs, then we don't release." and "Of course if there is nothing found, we don't need to run it three
times." So: round 1 is the full run; green ends the night's testing. Not green: the job fixes everything it found
(each fix checked on the flows it touches, never a full run per fix), then `again`, a full run again; at most
ROUNDS full runs. last.json holds the latest round and every round of tonight, so the release (release.py) reads
whether the night ended green, and after which round.

F112 (2 November 2026): the routine starts the night itself, once, with the team off too (tick.nightly_minute); a run writes the commit it ran on and
any change that wasn't committed, whole_set says how many flows a whole night is at that commit, and the release counts a green night only for that
commit and its free files (release.night_tied). One run at a time (running): a second start is left out, and no job starts beside it.

The tutorial stays right (H227, 22 October 2026). The user on the call at 12:13: "If we keep adding features and
changing things, then the tutorial still needs to work the same." and "Yeah, every night is fine. It doesn't need to
skip it. ... Just included. Every night is good." Two parts, every night, no skipping: detailed flow 134 (in both sets)
fails when a button or screen on the call page has no tutorial piece; and after the flows the job reads the tutorial
(app/web/tour.json) against what HQ does now and `tutorial`'s changes, and fixes what's outdated or missing the same
night, in everyday words, demo content only, then `tutorial done`.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HQ = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import flowsets  # noqa: E402
import hqpaths  # noqa: E402
import jobs  # noqa: E402  (the roadmap's lock)

ROW = "H169"
MARK = "Nights:"
KEEP_NIGHTS = 7
KEEP_LOGS = 14
OUT = os.environ.get("HQ_NIGHT_OUT") or os.path.join(HQ, "scratch", "nightly")  # H324: a test's own place for the record
MORNING = (8, 0)  # when Moneypenny (H266) texts the line for the morning
ROUNDS = 3  # H226: at most three full runs a night
NIGHT_HOURS = 20  # H324: the rotation between rounds can run into the morning; was 12. a round belongs to tonight when tonight's round 1 started less than this long ago [Claude's choice]


def flow_args() -> list[str]:
    """F101 (C73): every quick flow, a new one by itself; on Linux all but those marked Mac-only."""
    return ["--quick"] if sys.platform == "darwin" else ["--quick", "--skip", flowsets.MAC_ONLY]


def is_main() -> bool:
    try:
        import role
        return role.acting() == "main"
    except Exception:
        return True  # no pairing (or role can't be read): this HQ is the only one, so it's main


def _python() -> str:
    venv = os.path.join(HQ, ".venv", "bin", "python")
    return venv if os.path.exists(venv) else sys.executable


def failures(out: str) -> list[str]:
    """The flows the run's result says failed: ["45: FAILED - ..."]."""
    tail = out.rpartition("\n== Result")[2]
    return [ln.strip() for ln in tail.splitlines() if re.match(r"\s*\d+: FAILED - ", ln)]


def summary(out: str) -> tuple[int, int]:
    # The last one: a flow's own output can have such a line too (a stand-in run inside flow 103).
    m = re.findall(r"^(\d+) of (\d+) passed", out, re.M)
    return (int(m[-1][0]), int(m[-1][1])) if m else (0, 0)


def add_night(line: str, roadmap: str | None = None) -> bool:
    """One line in the H169 row's nights, newest first, the last KEEP_NIGHTS kept. False when there's no row."""
    path = roadmap or hqpaths.ROADMAP
    line = " ".join(line.replace("|", "/").split())
    with jobs.locked():
        text = open(path, encoding="utf8").read()
        m = re.search(rf"^\| [^|\n]* \| {ROW} [^\n]*\|\s*$", text, re.M)
        if not m:
            return False
        row = m.group(0).rstrip()
        cells = row[1:-1].split(" | ")
        last = cells[-1].strip()
        before, _, nights = last.partition(MARK)
        old = [n.strip() for n in nights.split(";") if n.strip()]
        new = "; ".join([line] + old[:KEEP_NIGHTS - 1])
        cells[-1] = f" {(before.strip() + ' ') if before.strip() else ''}{MARK} {new} "
        row2 ="| " + " | ".join(c.strip() for c in cells) + " |"
        hqpaths.guard_roadmap(path)  # F17
        tmp = path + ".tmp"
        open(tmp, "w", encoding="utf8").write(text[:m.start()] + row2 + text[m.start() + len(row):])
        os.replace(tmp, path)
    return True


def morning(text: str, now: dt.datetime | None = None) -> dict:
    """Moneypenny texts it on her own line at the next 08:00 (H266), in her own words (pings.py, why nightly)."""
    import pings
    now = now or dt.datetime.now()
    at = now.replace(hour=MORNING[0], minute=MORNING[1], second=0, microsecond=0)
    if at <= now:
        at += dt.timedelta(days=1)
    return pings.remind(at, text, by="nightly", why="nightly")


def _prune():
    logs = sorted(f for f in os.listdir(OUT) if f.endswith(".log"))
    for f in logs[:-KEEP_LOGS]:
        os.remove(os.path.join(OUT, f))


def last() -> dict | None:
    try:
        return json.load(open(os.path.join(OUT, "last.json"), encoding="utf8"))
    except Exception:
        return None


def _git(*a: str, root: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", root or HQ, *a], capture_output=True, text=True)


def here() -> tuple[str, list[str]]:
    """F112: the commit HQ stands on, and the tracked files that differ from it: that's what a run really runs."""
    dirty = [ln[3:] for ln in _git("status", "--porcelain").stdout.splitlines() if ln.strip() and not ln.startswith("??")]
    return _git("rev-parse", "HEAD").stdout.strip(), dirty


def whole_set(commit: str = "HEAD", root: str | None = None) -> int:
    """F112: how many flows a whole night is at that commit, read from git: every quick flow, on Linux all but the Mac-only ones. A number of
    its own, so a record with one flow in it isn't a night. 0 when it can't be read."""
    flows = _git("show", f"{commit}:app/happy_flows.py", root=root).stdout
    sets = _git("show", f"{commit}:routine/flowsets.py", root=root).stdout
    block = flows.partition("\nFLOWS = {")[2].partition("\n}\n")[0]
    quick = re.findall(r"^\s+(\d+): \(.*, False, \"\w+\"\),?\s*$", block, re.M)
    out = re.search(r'^MAC_ONLY = "([\d,]*)"', sets, re.M)
    left = set((out.group(1) if out else "").split(",")) if sys.platform != "darwin" else set()
    return len([n for n in quick if n not in left])


RUNNING = None  # F112: a test's own file; otherwise running.json in OUT


def _running_file() -> str:
    return RUNNING or os.path.join(OUT, "running.json")


def running() -> dict | None:
    """F112: the night's run that's going right now, on this HQ: {"pid", "at"}, or None. A run inside a test isn't one: it's the night's own flows."""
    if hqpaths.under_test() and not os.environ.get("HQ_NIGHT_MINUTE"):
        return None
    try:
        d = json.load(open(_running_file(), encoding="utf8"))
        os.kill(int(d["pid"]), 0)
        return d
    except PermissionError:
        return d
    except (OSError, ValueError, KeyError, TypeError):
        return None


def tonight(prev: dict | None, now: dt.datetime | None = None) -> dict | None:
    """The night prev belongs to, when it's still tonight's: {"night", "round", "rounds", "green"}; else None."""
    if not prev or not prev.get("at"):
        return None
    now = now or dt.datetime.now()
    night = prev.get("night") or prev["at"]
    try:
        start = dt.datetime.strptime(night, "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    if not dt.timedelta(0) <= now - start < dt.timedelta(hours=NIGHT_HOURS):
        return None
    green = prev.get("exit") == 0 and bool(prev.get("ran")) and not prev.get("failed")
    rounds = prev.get("rounds") or [{k: prev.get(k) for k in ("at", "commit", "dirty", "ran", "passed", "failed", "exit", "minutes", "log")}]
    return {"night": night, "round": int(prev.get("round") or 1), "rounds": rounds, "green": green}


def team_job(failed: list[str]) -> None:
    """F101: a red night started by the routine is the team's to fix, as the H169 job did."""
    what = "; ".join(failed)[:900] or "the run ended with an error"
    subprocess.run([sys.executable, os.path.join(HQ, "routine", "jobs.py"), "add",
                    f"H169, the nightly run, was red: {what}. Read scratch/nightly/last.json and its log, fix everything it "
                    "found, then nightly.py again, up to three rounds a night; python3 routine/nightly.py morning \"TEXT\" for the "
                    "morning's text.", "--kind", "small"], capture_output=True, text=True)


# H324, his words (the laptop chat, 6 November 2026, 00:20): "i want that during a nightly run, they FINISH the whole run, and if there are
# multiple that broke, then they get all fixed through the whole rotation that we built the last two days (MP makes the row, the review checks
# it, MP makes the test case, the review checks it, MP ready marks it and puts it on the planning), and then if after 3 full cycles of testing
# they couldnt have everything fixed, it is paused." And: "it must be held against the initial item as well to make sure it still fits the
# bigger picture". So a red round no longer goes to a team job that patches it: each failure becomes a row on the planning with both switches
# on as the night's own (built at night, like Moneypenny's pick), the line carries each through the whole rotation, and the routine starts
# the next full run only once every failure of the round passed her check. After the third red run the night is paused: nothing goes out.
H324 = "H324"


def _flow_item(num: str) -> tuple[str, str]:
    """The flow's own line in FLOWS and the item it belongs to (the F or H label it starts with), or ("", "")."""
    try:
        src = open(os.path.join(HQ, "app", "happy_flows.py"), encoding="utf8").read()
    except OSError:
        return "", ""
    m = re.search(rf'^\s+{num}: \(\s*"((?:[^"\\]|\\.)*)"', src, re.M)
    desc = m.group(1) if m else ""
    lab = re.search(r"\b([FH]\d{1,4})\b", desc)  # the first item it names: most flows start with it
    return desc, (lab.group(1) if lab else "")


def rotate(failed: list[str], n: int, night: str) -> dict:
    """H324: each failure of a red round a row on the planning (one per failing flow; the same flow's open row from tonight is used again),
    held against the item its flow belongs to, both switches on as the night's own, so the line carries it through the whole rotation.
    Returns {failure line: label} (or "not written: why")."""
    import sprint as S
    items = {}
    for ln in failed or ["the run ended without a flow failing: see the log's end"]:
        m = re.match(r"\s*(\d+): FAILED - (.*)", ln)
        num, why = (m.group(1), m.group(2).strip()) if m else ("", ln.strip())
        desc, item = _flow_item(num) if num else ("", "")
        what = (f"flow {num}" + (f" ({desc[:160]})" if desc else "")) if num else "the run itself"
        mark = f"(night run, flow {num or 'run'})"
        said = (f"{what[0].upper() + what[1:]} failed in the night run {mark}: {why[:600]}. Found on {night[:10]}, round {n} of {ROUNDS} ({H324}): "
                "fixed through the whole rotation, never a quick patch: the row, the review, her test, the review, the Ready mark, the team, "
                "her check. " + (f"Held against {item}'s row as well, so the fix still fits what {item} is for and the bigger picture. " if item
                                 else "Held against the item this flow belongs to as well, and the bigger picture. ")
                + "The night's next full run starts once every failure of this round passed her check. "
                # F163: where it came from, so the row's fields hold once she adds His words: none, found by a check
                + "Sources: " + "; ".join(x for x in ("app/happy_flows.py" if num else "", H324, item) if x) + ".").replace("|", "/")
        try:
            with jobs.locked():
                text, queue, on = jobs.read()
                same = next((r["label"] for r in S.open_rows(text) if mark in r["line"]), None)
                if same:
                    label = same
                else:
                    text, label = jobs.roadmap_row(text, said, True, by="the night run")
                    jobs.write(text, queue, on)
            S.set_go(label, "both", True, by="night")
            items[ln] = label
        except (Exception, SystemExit) as e:  # one failure not written never stops the others
            items[ln] = f"not written: {e!r}"[:200]
    return items


def _tell_paused(night: str, n: int, failed: list[str]) -> None:
    """H324: after the last full run still red: the night is paused, one text to him on her line, and the morning's line."""
    what = "; ".join(failed)[:400] or "the run ended with an error"
    words = (f"The night run of {night[:10]} is paused: after {n} full runs it still isn't green ({what}). Nothing goes out; "
             "the night's work holds on nightly. The failures are on the planning.")
    try:
        import qatests
        qatests.tell(H324, f"night-paused-{night[:10]}", words)
    except Exception:
        pass
    try:
        morning(words)
    except Exception:
        pass


def night_open(now: dt.datetime | None = None) -> bool:
    """H324: tonight isn't settled yet: its run is going, or a red round's failures are in the rotation with a full run left. A release waits
    for it (schedule.py). A copy under test reads only its own record (HQ_NIGHT_OUT)."""
    if hqpaths.under_test() and not os.environ.get("HQ_NIGHT_OUT"):
        return False
    if running():
        return True
    rec = last() or {}
    t = tonight(rec, now)
    return bool(t and not t["green"] and rec.get("routine") and not rec.get("held") and rec.get("items"))


def rotation_minute(now: dt.datetime | None = None, busy: bool = False):
    """H324: the routine, every minute on the main: tonight's red round, every one of its failures through her check (or no longer an
    open row), gets the next full run, once. Returns the run's pid when it started one, else None."""
    if running() or busy:
        return None
    rec = last() or {}
    t = tonight(rec, now)
    if not t or t["green"] or not rec.get("routine") or rec.get("held") or t["round"] >= ROUNDS:
        return None
    items = sorted({v for v in (rec.get("items") or {}).values() if re.fullmatch(r"[FH]\d+", str(v))})
    if not items:
        return None
    import qa
    import sprint as S
    open_ = {r["label"] for r in S.open_rows()}
    if [x for x in items if x in open_ and qa.state(x) != "passed"]:
        return None
    os.makedirs(OUT, exist_ok=True)
    out = open(os.path.join(OUT, "rotation.log"), "a")
    p = subprocess.Popen([_python(), os.path.abspath(__file__), "again", "--routine"], cwd=HQ, stdin=subprocess.DEVNULL, stdout=out,
                         stderr=subprocess.STDOUT, start_new_session=True)
    json.dump({"pid": p.pid, "at": (now or dt.datetime.now()).strftime("%Y-%m-%d %H:%M")}, open(_running_file(), "w"))
    return p.pid


def run(again: bool = False, routine: bool = False) -> int:
    stamp = dt.datetime.now()
    if not is_main():
        print("This computer isn't the main right now, so the nightly run is the main's. Nothing done.")
        return 0
    os.makedirs(OUT, exist_ok=True)
    going = running()
    if going and int(going.get("pid") or 0) != os.getpid():  # F112: two runs at once go red by themselves; the routine marks this one before it starts
        print(f"A full run is already going (pid {going['pid']}, since {going.get('at')}): it's left alone, nothing more started.")
        return 0
    if not again and not routine:  # F101: the routine already ran it: the H169 item has nothing left to run
        t = tonight(last(), stamp)
        if t and t["green"] and (last() or {}).get("routine"):
            print(f"Tonight's run already passed every flow (round {t['round']}): nothing to run.")
            return 0
    rec_ = last() or {}
    if not routine and rec_.get("routine") and tonight(rec_, stamp) and (rec_.get("items") or rec_.get("held")):
        # H324: the routine's night is in the rotation (or paused): no job patches it or runs it again by hand
        labels = sorted({v for v in (rec_.get("items") or {}).values() if re.fullmatch(r"[FH]\d+", str(v))})
        print("Tonight's night is " + ("paused after its last full run" if rec_.get("held") else
              f"in the rotation ({H324}): its failures are on the planning as {', '.join(labels) or 'rows'}, each through the whole rotation; "
              "the routine starts the next full run itself once each passed her check") + ". Nothing for this job to run or fix.")
        return 0
    night, n, rounds = stamp.strftime("%Y-%m-%d %H:%M"), 1, []
    if again:
        t = tonight(last(), stamp)
        if not t:
            print("No run from tonight to go on from: start with run (round 1).")
            return 2
        if t["green"]:
            print(f"Round {t['round']} already passed every flow: no more runs tonight.")
            return 0
        if t["round"] >= ROUNDS:
            print(f"Tonight already had {ROUNDS} full runs; still failing, so the night's work holds on nightly.")
            return 3
        night, n, rounds = t["night"], t["round"] + 1, t["rounds"]
    log = os.path.join(OUT, stamp.strftime("%Y-%m-%d-%H%M%S") + ".log")
    cmd = [_python(), os.path.join(HQ, "app", "happy_flows.py")] + flow_args()
    print(f"Round {n} of at most {ROUNDS}. Running: {' '.join(cmd[1:])}  (output in {log})", flush=True)
    t0 = time.time()
    commit, dirty = here()  # F112: what this run tests; a release reads it
    json.dump({"pid": os.getpid(), "at": stamp.strftime("%Y-%m-%d %H:%M")}, open(_running_file(), "w"))
    hp = None
    try:
        with open(log, "w", encoding="utf8") as f:
            r = subprocess.run(cmd, cwd=HQ, stdout=f, stderr=subprocess.STDOUT)
        red_happy = any((x.get("happy") or {}).get("green") is False for x in rounds)  # a red night's next round checks their fix too
        if happy_at_night() and (happy_due(stamp) or red_happy):
            hp = _happy_run(log, commit)
    finally:
        try:
            os.remove(_running_file())
        except OSError:
            pass
    out = open(log, encoding="utf8").read()
    mins = round((time.time() - t0) / 60)
    passed, ran = summary(out)
    failed = failures(out)
    if hp:  # a red or untried happy flow makes the night red, as a red detailed flow does; each its own repair item (rotate)
        failed = failed + hp["failed"] + hp["not_tried"]
    entry = {"at": stamp.strftime("%Y-%m-%d %H:%M"), "commit": commit, "dirty": dirty, "ran": ran, "passed": passed, "failed": failed,
             "exit": r.returncode, "minutes": mins, "log": log, **({"happy": hp} if hp else {})}
    if happy_at_night() and not hp:  # not their night: nothing missing, the last run of them stands (release.night_refuses reads it)
        entry["happy_not_tonight"] = f"the 17 run {happy_every()[0]}ly; the last run: {(last_happy() or {}).get('at') or 'none yet'}"
    green_ = r.returncode == 0 and bool(ran) and not failed and (not hp or hp["green"])
    items = rotate(failed, n, night) if routine and not green_ and n < ROUNDS else {}  # H324
    entry["items"] = items
    held = bool(routine and not green_ and n >= ROUNDS)
    json.dump({**entry, "round": n, "rounds_max": ROUNDS, "night": night, "rounds": rounds + [entry], "routine": routine, "held": held},
              open(os.path.join(OUT, "last.json"), "w"), indent=1)
    _prune()
    when = stamp.strftime("%-d %b %H:%M")
    import routines  # F102: the night's own line, with a day's interval, so a night that didn't run shows
    if green_:
        routines.good("nightly", f"{when}: all {ran} flows pass" + (f", and the {hp['ran']} of the happy flows" if hp else ""), every=86400)
    else:
        routines.bad("nightly", f"{when}: {passed} of {ran} passed", every=86400)
    if green_:
        hold_privacy()
        if n == 1:
            add_night(f"{when} all {ran} flows pass ({mins} min)")
            print(f"All {ran} flows pass ({mins} min). One line in the {ROW} row. Then the tutorial read: nightly.py tutorial.")
        else:
            print(f"Round {n}: all {ran} flows pass ({mins} min). Tonight ends green: the release can go out. "
                  f"Write one line for the night with nightly.py log (what each round found and what was fixed). "
                  f"Then the tutorial read: nightly.py tutorial.")
        return 0
    print(f"Round {n}: {passed} of {ran} passed ({mins} min). Failed:")
    for ln in failed or [f"(no flow failed, but the run ended with exit {r.returncode}: see the log's end)"]:
        print("  " + ln)
    print(f"The full output: {log}")
    if routine:  # H324: the whole rotation, not a team job that patches it
        if n < ROUNDS:
            print(f"Each failure is on the planning for the whole rotation ({H324}): " + ", ".join(f"{v}" for v in items.values())
                  + f". The routine starts round {n + 1} of {ROUNDS} once every one passed her check.")
            return 1
        _tell_paused(night, n, failed)
        print(f"That was the last of {ROUNDS} full runs: the night is paused, its work holds on nightly, not released. Told him once.")
        return 3
    if n < ROUNDS:
        print(f"Fix everything this round found (check each fix on the flows it touches; no full run per fix), "
              f"then: nightly.py again (round {n + 1} of {ROUNDS}).")
        return 1
    print(f"That was the last of {ROUNDS} full runs: the night's work holds on nightly, not released.")
    return 3


def happy_at_night() -> bool:
    """11 November 2026, his words: "No the 17 happy flows should only run once at night in the nightly run". With whole_build_review on
    they run here, once a night (each round of a red night too), not after a build and not in the whole-build step."""
    try:
        import wholebuild
        return wholebuild.on()
    except Exception:
        return False


WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def happy_every() -> tuple[str, int]:
    """(night or week, the weekday for week) from the workspace's HQ/backend.json: "happy_flows_every" ("night", the default, or "week")
    and "happy_flows_day" (a weekday's name; by default the weekly sweep's day, tick.SWEEP_DAY). He hasn't decided yet (11 November 2026)."""
    try:
        sys.path.insert(0, os.path.join(HQ, "app"))
        import backend
        d = backend._read()
    except Exception:
        d = {}
    every = str(d.get("happy_flows_every") or os.environ.get("HQ_HAPPY_EVERY") or "night").lower()
    day = str(d.get("happy_flows_day") or os.environ.get("HQ_HAPPY_DAY") or "").lower()
    sweep = 0  # tick.SWEEP_DAY: Monday, the weekly sweep's morning
    return ("week" if every.startswith("week") else "night"), (WEEKDAYS.index(day) if day in WEEKDAYS else sweep)


def _happy_file() -> str:
    return os.path.join(OUT, "happy-last.json")


def last_happy() -> dict | None:
    try:
        return json.load(open(_happy_file(), encoding="utf8"))
    except (OSError, ValueError):
        return None


def happy_due(now: dt.datetime | None = None) -> bool:
    """Every night; or once a week: the first night on or after the set weekday since their last run (the sweep's Monday has no
    nightly, so by default they run the Tuesday morning)."""
    every, day = happy_every()
    if every == "night":
        return True
    now = now or dt.datetime.now()
    since = (now - dt.timedelta(days=(now.weekday() - day) % 7)).date()
    last = (last_happy() or {}).get("at") or ""
    return last[:10] < since.isoformat()


def _happy_run(log: str, commit: str = "") -> dict:
    """The 17 happy flows (happy.gate_args), for real, on dev as it stands, with their own log next to the night's."""
    import happy
    import proof
    hlog = log[:-4] + "-happy.log"
    t0 = time.time()
    with open(hlog, "w", encoding="utf8") as f:
        r = subprocess.run([_python(), os.path.join(HQ, "app", "happy_flows.py")] + happy.gate_args(), cwd=HQ, stdout=f, stderr=subprocess.STDOUT)
    out = open(hlog, encoding="utf8").read()
    passed, ran = summary(out)
    failed = failures(out) or ([] if r.returncode == 0 and ran else [f"the run itself: the happy flows ended with exit {r.returncode}"])
    not_tried = proof._not_tried()
    rec = {"ran": ran, "passed": passed, "failed": failed, "not_tried": not_tried, "log": hlog, "minutes": round((time.time() - t0) / 60),
           "green": not failed and not not_tried and bool(ran) and passed == ran, "at": time.strftime("%Y-%m-%d %H:%M"), "commit": commit}
    json.dump(rec, open(_happy_file(), "w"), indent=1)
    return rec


def hold_privacy() -> None:
    """F112: a green night reads the history once, so what the release reads after it is only what's new (privacy.py holds what read clean).
    What it finds isn't the night's to judge: the release refuses it."""
    if hqpaths.under_test():
        return
    try:
        p = subprocess.run([_python(), os.path.join(HQ, "app", "privacy.py"), "--history"], cwd=HQ, capture_output=True, text=True, timeout=3600)
        print("Privacy check, for the release: " + ((p.stdout.strip().splitlines() or ["no answer"])[-1]))
    except subprocess.SubprocessError as e:
        print(f"Privacy check, for the release: not finished: {e!r}")


TOUR = os.path.join(HQ, "app", "web", "tour.json")


def tutorial(done: bool = False) -> int:
    """H227: what changed in HQ since the last tutorial read, for the night's read; `done` sets the mark at HEAD."""
    git = lambda *a: subprocess.run(["git", "-C", HQ, *a], capture_output=True, text=True).stdout.strip()
    head = git("rev-parse", "HEAD")
    mark_file = os.path.join(OUT, "tutorial.json")  # where the last read ended (commit, time)
    if done:
        os.makedirs(OUT, exist_ok=True)
        json.dump({"commit": head, "at": dt.datetime.now().strftime("%Y-%m-%d %H:%M")}, open(mark_file, "w"), indent=1)
        print(f"Tutorial read marked at {head[:7]}; the next read starts from here.")
        return 0
    try:
        mark = json.load(open(mark_file))
    except (OSError, ValueError):
        mark = {}
    since = mark.get("commit")
    if since and git("cat-file", "-t", since) == "commit":
        rng, start = [f"{since}..HEAD"], f"the last read ({mark.get('at')}, {since[:7]})"
    else:
        rng, start = ["--since=26 hours ago"], "the last 26 hours (no earlier read marked)"
    commits = git("log", "--no-merges", "--format=%h %s", *rng)
    files = sorted({f for f in git("log", "--no-merges", "--format=", "--name-only", *rng).splitlines() if f})
    print(f"Read the tutorial ({TOUR}) against what HQ does now; changes since {start}:")
    print(commits or "  (no commits: still read it once against the call page and the build notes)")
    if files:
        print("Files touched: " + ", ".join(files))
    print("Fix what's outdated or missing tonight: everyday words, demo content only (never anyone's real life); "
          "a new button or screen needs its piece (flow 134). Check with flows 120 and 134, then: nightly.py tutorial done.")
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "run" and "--routine" in argv:  # F101: started by the routine's own minute
        return run(routine=True)
    if cmd == "run":
        return run()
    if cmd == "again":
        return run(again=True, routine="--routine" in argv)  # H324: the routine's next round after the rotation
    if cmd == "tutorial":
        return tutorial(done=argv[1:2] == ["done"])
    if cmd == "set":
        print(" ".join(flow_args()))
        return 0
    if cmd == "log" and len(argv) >= 2:
        if not add_night(" ".join(argv[1:])):
            print(f"No {ROW} row on the roadmap.")
            return 1
        print("Written.")
        return 0
    if cmd == "morning" and len(argv) >= 2:
        r = morning(" ".join(argv[1:]))
        print(f"Moneypenny texts it at {r['at']}: {r['text']}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
