#!/usr/bin/env python3
"""F102 (31 October 2026): a program holds the mail check to its own rules, and says when it stopped.

His words of 30 October 2026: "The mail list counts as stale when it hasn't been checked for 2 hours between 8:00 and midnight. Then
it turns red." The mail check is a model; the marker moving forward and the very important lines staying were only sentences in
its instructions. So the routine keeps the list as it stood at the run's start (`before`), and after the run (`after_run`) checks:
the marker didn't go backwards, every very important line is still there with its first three parts (date, sender, subject), and no
two lines share a key. Anything else: the old file back and an incident. A call or a text taking a line out during the run
(handover.py, loose_ends.py) calls `touched`, so that isn't counted against the run. `minute` keeps the line on the status page:
red when the last good run is over 2 hours ago between 8:00 and midnight.

    python3 routine/mailguard.py check BEFORE AFTER    what's wrong between two versions, one line each (none: it's fine)
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqlock  # noqa: E402
import hqpaths  # noqa: E402

RUN = os.environ.get("HQ_JOB_RUN") or os.path.join(hqpaths.HQ, "scratch", "routine")
STALE_S = 2 * 3600
HOURS = (8, 24)  # his words: between 8:00 and midnight
KEY = "maillist"


def path() -> str:
    return os.path.join(hqpaths.FOLDER, "inbox.md")


def _before() -> str:
    return os.path.join(RUN, "inbox-before.md")


def _ok_file() -> str:
    return os.path.join(RUN, "mail-good")


def marker(text: str):
    m = re.search(r"^Marker:\s*(\d+)", text or "", re.M)
    return int(m.group(1)) if m else None


def very_important(text: str) -> list[str]:
    """The lines under "## Very important"."""
    m = re.search(r"^## Very important\s*$(.*?)(?=^## |\Z)", text or "", re.M | re.S)
    return [ln for ln in (m.group(1).splitlines() if m else []) if ln.startswith("- ")]


def key(line: str) -> str:
    """A line's first three parts: its date, sender and subject."""
    return " · ".join(p.strip() for p in line[2:].split(" · ")[:3])


def problems(old: str, new: str) -> list[str]:
    out = []
    a, b = marker(old), marker(new)
    if a is not None and (b is None or b < a):
        out.append(f"the marker went backwards ({a} to {b})")
    was, now = [key(x) for x in very_important(old)], [key(x) for x in very_important(new)]
    gone = [k for k in was if k not in now]
    if gone:
        out.append(f"{len(gone)} very important line(s) gone or changed: {gone[0][:120]}")
    twice = sorted({k for k in now if now.count(k) > 1})
    if twice:
        out.append(f"two lines share one key: {twice[0][:120]}")
    return out


def before() -> None:
    """The mail check starts: the list as it stands."""
    os.makedirs(RUN, exist_ok=True)
    try:
        shutil.copyfile(path(), _before())
    except OSError:
        pass


def touched(p=None) -> None:
    """Someone else changed the list during a run: what they left is what the run is held against."""
    if p is not None and os.path.realpath(os.fspath(p)) != os.path.realpath(path()):
        return
    if os.path.exists(_before()):
        before()


def after_run(ok: bool, incidents, routines, log=print) -> list[str]:
    """The run ended. Its result is checked against the list at its start; a bad one puts the old file back and opens an
    incident. Returns what was wrong."""
    b = _before()
    if not os.path.exists(b):
        return []
    with hqlock.locked(path()):
        try:
            old, new = open(b, encoding="utf8").read(), open(path(), encoding="utf8").read()
        except OSError:
            return []
        bad = problems(old, new)
        if bad:
            tmp = hqlock.tmp(path())
            with open(tmp, "w", encoding="utf8") as f:
                f.write(old)
            os.replace(tmp, path())
        os.remove(b)
    if bad:
        why = "; ".join(bad)
        incidents.down(KEY, f"The mail check broke the list: {why}")
        incidents.fix(KEY, "Put the list back as it was before the run; the next run reads that mail again")
        routines.beat(KEY, state="down", text=f"The list was put back: {why}"[:200], every=60)
        log(f"mail list put back: {why}")
    elif ok:
        open(_ok_file(), "w").write(str(int(time.time())))
    return bad


def last_good():
    try:
        return float(open(_ok_file()).read().strip())
    except (OSError, ValueError):
        return None


def in_hours(now=None) -> bool:
    pin = os.environ.get("HQ_WALL_HOUR") if hqpaths.under_test() else None
    h = int(pin) if pin else time.localtime(now).tm_hour
    return HOURS[0] <= h < HOURS[1]


def minute(on, incidents, routines, now=None) -> str:
    """Every minute on the main: the line on the status page. Off from a call: off. Nothing good yet: it starts counting."""
    now = now or time.time()
    if not on:
        routines.beat(KEY, state="off", text="The mail check is off", every=60)
        incidents.up(KEY)
        return "off"
    last = last_good()
    if last is None:
        open(_ok_file(), "w").write(str(int(now)))
        last = now
    old = now - last
    if old > STALE_S and in_hours(now):
        why = f"Not checked for {int(old // 3600)} h {int(old % 3600 // 60)} min"
        incidents.down(KEY, why)
        routines.beat(KEY, state="down", text=why + ": the mail list is stale", every=60)
        return "stale"
    was = incidents.is_down(KEY)
    if was and not str(was.get("why", "")).startswith("The mail check broke") or (was and old < 3600):
        incidents.up(KEY)
    routines.beat(KEY, state="ok", text="Checked " + time.strftime("%H:%M", time.localtime(last)), every=60)
    return "ok"


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[0] == "check":
        for p in problems(open(argv[1], encoding="utf8").read(), open(argv[2], encoding="utf8").read()):
            print(p)
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
