#!/usr/bin/env python3
"""The nightly run (H169, 16 October 2026): every night, all the happy flows, to find bugs.

The user on the call of 16 October 2026 at 11:56: "I was thinking maybe we can each night, during those usage
hours, just run all the flows or something like that and just find bugs. ... We don't have to plan those
maintenance moments because we just do it daily whenever we have space." and "Maybe we do the nightly check at
2 am". A repeating planned item (H171) carries one job text (in the H169 row); that job runs this script:

  python3 "routine/nightly.py" run          on the main only: round 1, the happy flows for this computer, no Claude
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
The flows with Claude turns stay out: they need a live voice and cost usage, and the daytime builds run them.
[Claude's choice.] Each run's output is kept in scratch/nightly/ (the last 14 nights).

Rounds (H226, 22 October 2026). The user on the call at 11:37: "they fix the 3 bugs, and then at the end they run it
again, they might find another thing. They fix all those bugs again and then they run another time. If that time it
still finds bugs, then we don't release." and "Of course if there is nothing found, we don't need to run it three
times." So: round 1 is the full run; green ends the night's testing. Not green: the job fixes everything it found
(each fix checked on the flows it touches, never a full run per fix), then `again`, a full run again; at most
ROUNDS full runs. last.json holds the latest round and every round of tonight, so the release (release.py) reads
whether the night ended green, and after which round.

The tutorial stays right (H227, 22 October 2026). The user on the call at 12:13: "If we keep adding features and
changing things, then the tutorial still needs to work the same." and "Yeah, every night is fine. It doesn't need to
skip it. ... Just included. Every night is good." Two parts, every night, no skipping: happy flow 134 (in both sets)
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
OUT = os.path.join(HQ, "scratch", "nightly")
MORNING = (8, 0)  # when Moneypenny (H266) texts the line for the morning
ROUNDS = 3  # H226: at most three full runs a night
NIGHT_HOURS = 12  # a round belongs to tonight when tonight's round 1 started less than this long ago [Claude's choice]


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
    rounds = prev.get("rounds") or [{k: prev.get(k) for k in ("at", "ran", "passed", "failed", "exit", "minutes", "log")}]
    return {"night": night, "round": int(prev.get("round") or 1), "rounds": rounds, "green": green}


def team_job(failed: list[str]) -> None:
    """F101: a red night started by the routine is the team's to fix, as the H169 job did."""
    what = "; ".join(failed)[:900] or "the run ended with an error"
    subprocess.run([sys.executable, os.path.join(HQ, "routine", "jobs.py"), "add",
                    f"H169, the nightly run, was red: {what}. Read scratch/nightly/last.json and its log, fix everything it "
                    "found, then nightly.py again, up to three rounds a night; python3 routine/nightly.py morning \"TEXT\" for the "
                    "morning's text.", "--kind", "small"], capture_output=True, text=True)


def run(again: bool = False, routine: bool = False) -> int:
    stamp = dt.datetime.now()
    if not is_main():
        print("This computer isn't the main right now, so the nightly run is the main's. Nothing done.")
        return 0
    os.makedirs(OUT, exist_ok=True)
    if not again and not routine:  # F101: the routine already ran it: the H169 item has nothing left to run
        t = tonight(last(), stamp)
        if t and t["green"] and (last() or {}).get("routine"):
            print(f"Tonight's run already passed every flow (round {t['round']}): nothing to run.")
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
    with open(log, "w", encoding="utf8") as f:
        r = subprocess.run(cmd, cwd=HQ, stdout=f, stderr=subprocess.STDOUT)
    out = open(log, encoding="utf8").read()
    mins = round((time.time() - t0) / 60)
    passed, ran = summary(out)
    failed = failures(out)
    entry = {"at": stamp.strftime("%Y-%m-%d %H:%M"), "ran": ran, "passed": passed, "failed": failed,
             "exit": r.returncode, "minutes": mins, "log": log}
    json.dump({**entry, "round": n, "rounds_max": ROUNDS, "night": night, "rounds": rounds + [entry], "routine": routine},
              open(os.path.join(OUT, "last.json"), "w"), indent=1)
    _prune()
    when = stamp.strftime("%-d %b %H:%M")
    if r.returncode == 0 and ran and not failed:
        if n == 1:
            add_night(f"{when} all {ran} flows pass ({mins} min)")
            print(f"All {ran} flows pass ({mins} min). One line in the {ROW} row. Then the tutorial read: nightly.py tutorial.")
        else:
            print(f"Round {n}: all {ran} flows pass ({mins} min). Tonight ends green: the release can go out. "
                  f"Write one line for the night with nightly.py log (what each round found and what was fixed). "
                  f"Then the tutorial read: nightly.py tutorial.")
        return 0
    if routine:
        team_job(failed)
    print(f"Round {n}: {passed} of {ran} passed ({mins} min). Failed:")
    for ln in failed or [f"(no flow failed, but the run ended with exit {r.returncode}: see the log's end)"]:
        print("  " + ln)
    print(f"The full output: {log}")
    if n < ROUNDS:
        print(f"Fix everything this round found (check each fix on the flows it touches; no full run per fix), "
              f"then: nightly.py again (round {n + 1} of {ROUNDS}).")
        return 1
    print(f"That was the last of {ROUNDS} full runs: the night's work holds on nightly, not released.")
    return 3


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
        return run(again=True)
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
