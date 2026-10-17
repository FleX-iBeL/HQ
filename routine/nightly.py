#!/usr/bin/env python3
"""The nightly run (H169, 16 October 2026): every night, all the happy flows, to find bugs.

The user on the call of 16 October 2026 at 11:56: "I was thinking maybe we can each night, during those usage
hours, just run all the flows or something like that and just find bugs. ... We don't have to plan those
maintenance moments because we just do it daily whenever we have space." and "Maybe we do the nightly check at
2 am". A repeating planned item (H171) carries one job text (in the H169 row); that job runs this script:

  python3 "routine/nightly.py" run          on the main only: the happy flows for this computer, no Claude turns.
                                            All pass: one line in the H169 row's nights, exit 0, nothing else.
                                            One fails: the failed flows and the log, exit 1 (the job fixes them).
                                            Not the main: says so, changes nothing, exit 0.
  python3 "routine/nightly.py" set          which flows this computer runs
  python3 "routine/nightly.py" log "LINE"   one line in the H169 row's nights (the job, after its fix)
  python3 "routine/nightly.py" morning "TEXT"  a short plain line Donna texts him at 08:00 (the next one)

The set: on a Mac every flow without Claude turns (--quick); elsewhere the Linux nightly set (flowsets.LINUX_NIGHTLY: every quick flow that holds on Linux).
The flows with Claude turns stay out: they need a live voice and cost usage, and the daytime builds run them.
[Claude's choice.] Each run's output is kept in scratch/nightly/ (the last 14 nights).
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
MORNING = (8, 0)  # when Donna texts the line for the morning


def flow_args() -> list[str]:
    return ["--quick"] if sys.platform == "darwin" else ["--quick", "--only", flowsets.LINUX_NIGHTLY]


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
    """Donna texts it at the next 08:00, in her own words (pings.py, why nightly)."""
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


def run() -> int:
    stamp = dt.datetime.now()
    if not is_main():
        print("This computer isn't the main right now, so the nightly run is the main's. Nothing done.")
        return 0
    os.makedirs(OUT, exist_ok=True)
    log = os.path.join(OUT, stamp.strftime("%Y-%m-%d-%H%M") + ".log")
    cmd = [_python(), os.path.join(HQ, "app", "happy_flows.py")] + flow_args()
    print(f"Running: {' '.join(cmd[1:])}  (output in {log})", flush=True)
    t = time.time()
    with open(log, "w", encoding="utf8") as f:
        r = subprocess.run(cmd, cwd=HQ, stdout=f, stderr=subprocess.STDOUT)
    out = open(log, encoding="utf8").read()
    mins = round((time.time() - t) / 60)
    passed, ran = summary(out)
    failed = failures(out)
    json.dump({"at": stamp.strftime("%Y-%m-%d %H:%M"), "ran": ran, "passed": passed, "failed": failed,
               "exit": r.returncode, "minutes": mins, "log": log},
              open(os.path.join(OUT, "last.json"), "w"), indent=1)
    _prune()
    when = stamp.strftime("%-d %b %H:%M")
    if r.returncode == 0 and ran and not failed:
        add_night(f"{when} all {ran} flows pass ({mins} min)")
        print(f"All {ran} flows pass ({mins} min). One line in the {ROW} row; nothing else to do.")
        return 0
    print(f"{passed} of {ran} passed ({mins} min). Failed:")
    for ln in failed or [f"(no flow failed, but the run ended with exit {r.returncode}: see the log's end)"]:
        print("  " + ln)
    print(f"The full output: {log}")
    return 1


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "run":
        return run()
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
        print(f"Donna texts it at {r['at']}: {r['text']}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
