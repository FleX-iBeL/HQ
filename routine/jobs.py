#!/usr/bin/env python3
"""The hourly mail check's switch, kept on the roadmap's queue section, and the queue's lock.

HQ has no team: nothing here starts, queues or runs work. What's left of the queue section is its two switch lines,
which both computers read from the same roadmap:

    **Routine:** on                     (read only here)
    **Mail check:** on (every hour, hidden, also while a job runs; commits take turns)

    python3 routine/jobs.py next            the switches as JSON: {"on", "mail", "mail_fast", "running": [], ...}
    python3 routine/jobs.py list            the switches in words
    python3 routine/jobs.py mail-off | mail-on      the hourly mail check off or on
    python3 routine/jobs.py mail-fast "UNTIL"       every 15 minutes until UNTIL (his words: 6 hours, 20:00, tonight, Friday)
    python3 routine/jobs.py mail-hourly             back to every hour now

Only the Mail check line is ever rewritten; every other line of the roadmap stays as it is. On the backup a change goes
to the main HQ as the same command (routine/role.py). HQ_ROADMAP names a test's own copy.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import sys
import time
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths

ROADMAP = hqpaths.ROADMAP
LOCK = os.path.join(HERE, "..", "scratch", "routine", "queue.lock")
HEADING = "## The queue"
MAIL_LINE = "**Mail check:**"
FAST_RE = re.compile(r"every 15 minutes from (\d{4}-\d\d-\d\d \d\d:\d\d(?:[+-]\d\d:\d\d)?) until (\d{4}-\d\d-\d\d \d\d:\d\d(?:[+-]\d\d:\d\d)?)")
MAIL = True
MAIL_FAST = None  # (from, until) epoch seconds while the mail check runs every 15 minutes, else None
WRITES = ("mail-on", "mail-off", "mail-fast", "mail-hourly")


@contextmanager
def locked():
    """The queue's lock: one writer of the roadmap at a time (the status block and this line take it)."""
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    with open(LOCK, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def section(text: str):
    """(start, end) of the queue section, or None."""
    i = text.find("\n" + HEADING + "\n")
    if i < 0:
        return None
    i += 1
    j = text.find("\n# ", i)
    k = text.find("\n## ", i + len(HEADING))
    ends = [x for x in (j, k) if x >= 0]
    return i, (min(ends) + 1 if ends else len(text))


def read():
    """(text, routine_on). Sets MAIL and MAIL_FAST from the Mail check line."""
    global MAIL, MAIL_FAST
    MAIL, MAIL_FAST, on = True, None, True
    try:
        text = open(ROADMAP, encoding="utf8").read()
    except FileNotFoundError:  # no planning here (yet): the mail check is on, as it starts
        return "", on
    sec = section(text)
    if sec:
        for l in text[sec[0]:sec[1]].splitlines():
            if l.startswith("**Routine:**"):
                on = "off" not in l.lower() and "paused" not in l.lower()
            elif l.startswith(MAIL_LINE):
                MAIL = "off" not in l.split("(")[0].lower()
                m = FAST_RE.search(l)
                if m:
                    import mailfast
                    f, u = mailfast.from_stamp(m.group(1)), mailfast.from_stamp(m.group(2))
                    MAIL_FAST = (f, u) if u > time.time() else None
    return text, on


def mail_words() -> str:
    """How often, on the Mail check line."""
    if MAIL_FAST and MAIL_FAST[1] > time.time():
        import mailfast
        return (f"every 15 minutes from {mailfast.stamp(MAIL_FAST[0])} until {mailfast.stamp(MAIL_FAST[1])}, "
                "then every hour by itself")
    return "every hour"


def write_mail_line(text: str) -> None:
    """The Mail check line as MAIL and MAIL_FAST say; nothing else in the file changes."""
    line = f"{MAIL_LINE} {'on' if MAIL else 'off'} ({mail_words()}, hidden, also while a job runs; commits take turns)"
    sec = section(text)
    if not sec:
        sys.exit("The roadmap has no queue section to keep the mail check's switch in.")
    body = text[sec[0]:sec[1]]
    if re.search(r"^\*\*Mail check:\*\*.*$", body, re.M):
        body = re.sub(r"^\*\*Mail check:\*\*.*$", lambda _: line, body, count=1, flags=re.M)
    else:
        body = body.replace(HEADING + "\n", f"{HEADING}\n\n{line}\n", 1)
    text = text[:sec[0]] + body + text[sec[1]:]
    hqpaths.guard_roadmap(ROADMAP)
    tmp = ROADMAP + f".tmp{os.getpid()}"
    open(tmp, "w", encoding="utf8").write(text)
    os.replace(tmp, ROADMAP)


def main(argv):
    global MAIL, MAIL_FAST
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, args = argv[0], argv[1:]
    if cmd not in ("next", "list") + WRITES:
        sys.exit(f"{cmd}: HQ has no team queue; only the mail check's switch is kept here (see --help).")
    import role
    if cmd in WRITES and not os.environ.get("HQ_ROLE_HERE") and role.is_backup():
        sys.exit(role.forward("jobs", list(argv)))
    with locked():
        text, on = read()
        if cmd == "next":
            print(json.dumps({"on": on, "mail": MAIL, "mail_fast": list(MAIL_FAST) if MAIL_FAST else None,
                              "running": [], "ready": [], "held": [], "waiting": [], "all": []}))
            return
        if cmd == "list":
            print(f"Routine: {'on' if on else 'off'}")
            print(f"Mail check: {'on' if MAIL else 'off'} ({mail_words()})")
            return
        if cmd in ("mail-on", "mail-off"):
            MAIL = cmd == "mail-on"
            write_mail_line(text)
            print(f"The hourly mail check is {cmd[5:]}.")
            return
        if cmd == "mail-fast":
            import mailfast
            try:
                until = mailfast.parse(" ".join(args))
            except ValueError as e:
                sys.exit(str(e))
            MAIL_FAST = (MAIL_FAST[0] if MAIL_FAST else int(time.time()), until)
            write_mail_line(text)
            print(f"The mail check runs every 15 minutes until {mailfast.said(until)} ({mailfast.stamp(until)}), "
                  f"then every hour again by itself." + ("" if MAIL else " It's switched off now, though: mail-on starts it."))
            return
        if cmd == "mail-hourly":
            was = MAIL_FAST
            MAIL_FAST = None
            write_mail_line(text)
            print("The mail check runs every hour again." if was else "The mail check already runs every hour.")


if __name__ == "__main__":
    main(sys.argv[1:])
