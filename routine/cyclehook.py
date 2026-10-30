#!/usr/bin/env python3
"""H298, piece 8: the tool hook of an agent's own cycle (a headless run as her, routine/cycles.py).

A shared file (the planning, the to-do list, the log, the mail list, the calendar, the games, the coaching marks)
has one serialized way in: HQ's own scripts (todo.py, sprint.py, jobs.py, pings.py, games.py) and, for the log and
the mail list, handover.py edit, which take the file's lock. A cycle that reaches for the file itself with Edit, Write
or a shell redirect is refused here, before anything is written, with the way in named; her ledger and her line she
writes freely. The run's stream shows the refusal, so after the run it's also a tripwire (cycles.after_run).

The hook reads the PreToolUse JSON on stdin: exit 0 lets the call through, exit 2 refuses it with the reason on
stderr. Nothing else is decided here; the box and the shares are the runner's.

F99 (30 October 2026): the same hook guards every team job against sending: any connector's send, reply or forward is
refused, whatever the connector is called. A team job needs the planning (it writes its results in the row), so only
a cycle gets the shared-file part: `--mail-only` is how a team job's settings call it.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SHARED = ("HQ/roadmap.md", "challenges.md", "coaching/log.md", "inbox.md", "HQ/calendar.json", "HQ/sprint.json",
          "HQ/games.json", "HQ/coaching.json", "HQ/calendar-todo.json", "HQ/calendar-marks.json")
FREE = ("HQ/ledger/", "HQ/direct-line/", "HQ/coaching-line/", "HQ/team-line/", "HQ/notes-")
EDITORS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
# a shell write on the file itself: a redirect into it, sed -i, tee, or a python open(..., "w") on it
_SHELL_WRITE = r"(>>?\s*\S*{name})|(sed\s+-i\S*\s.*{name})|(tee\s+(-a\s+)?\S*{name})|(open\(\s*[\"'][^\"']*{name}[\"']\s*,\s*[\"'][wa])"
WAY = ("the planning through sprint.py, jobs.py or review.py reword, the to-do list through todo.py, the calendar through pings.py, "
       "the games through games.py, the log and the mail list through handover.py edit REL JSON; your ledger and "
       "your line you write freely")


def shared_name(path: str) -> str | None:
    p = (path or "").replace(os.sep, "/")
    if any(x in p for x in FREE):
        return None
    for s in SHARED:
        if p.endswith(s) or p.endswith("/" + s.split("/")[-1]) and s.split("/")[-1] in ("roadmap.md", "sprint.json", "calendar.json", "games.json", "coaching.json"):
            return s
    return None


def never_mail(name: str) -> bool:
    """F99: a connector's send, reply or forward, whatever the connector is called."""
    import hqpaths
    return name.startswith("mcp__") and name.rsplit("__", 1)[-1] in hqpaths.NEVER_MAIL


def decide(ask: dict, mail_only: bool = False) -> tuple[int, str]:
    name, inp = str(ask.get("tool_name", "")), ask.get("tool_input") or {}
    if never_mail(name):
        return 2, f"HQ: refused {name}: nothing is ever sent, replied to or forwarded from a job. A draft at the most."
    if name in EDITORS and ".status/proofs" in str(inp.get("file_path") or "").replace(os.sep, "/"):
        return 2, "HQ: refused: a build's record is written only by routine/proof.py."
    if name == "Bash" and re.search(r"\.status/proofs|\bHQ_(?:UNDER_TEST|PROOF_\w+)\s*=", str(inp.get("command") or "")) and "proof.py" not in str(inp.get("command")):
        return 2, "HQ: refused: a build's record and its gate are the program's: routine/proof.py run N."
    if mail_only:
        return 0, ""
    if name in EDITORS:
        s = shared_name(str(inp.get("file_path") or inp.get("notebook_path") or ""))
        if s:
            return 2, f"HQ: refused {name} on {s}: a shared file is written only through HQ's own scripts ({WAY})."
        return 0, ""
    if name == "Bash":
        cmd = str(inp.get("command") or "")
        for s in SHARED:
            if re.search(_SHELL_WRITE.format(name=re.escape(s.split("/")[-1])), cmd):
                if "handover.py" in cmd or any(x in cmd for x in ("todo.py", "sprint.py", "jobs.py", "pings.py", "games.py", "coaching.py", "review.py")):
                    continue
                return 2, f"HQ: refused a shell write on {s}: a shared file is written only through HQ's own scripts ({WAY})."
    return 0, ""


def main() -> int:
    try:
        ask = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    code, why = decide(ask, "--mail-only" in sys.argv[1:])
    if code:
        print(why, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
