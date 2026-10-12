#!/usr/bin/env python3
"""H87: the 5-hour stop line, moving through the session or at a fixed number, switched from a call or the
status page. 12 October 2026 (call at 19:43): "10% for every 30 minutes. And I want to have a toggle. Where we
can toggle it into... A static specific number. We can also talk about it, turning it on or off and giving it
a number."

Moving (HQ's default): the line follows the 5-hour limit's reset time and grows 10% every half hour, 10% in
the session's first half hour up to 100% in its last (status/usage.mjs, movingFiveHour). Fixed: it stays at
the roadmap's "**Usage limit: N%**". The setting is the roadmap's "**5-hour line: moving**" or "fixed" line,
next to the usage limit, so both HQs (laptop and server) read the same one: the roadmap is synced. A job let
past the line still skips the 5-hour line; the weekly line always counts.

    python3 routine/usageline.py              which it is now, and where the line stands
    python3 routine/usageline.py moving       the line moves through the session
    python3 routine/usageline.py fixed        a fixed line, at the number it has
    python3 routine/usageline.py fixed 60     a fixed line at 60% (1 to 100)
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hqpaths  # noqa: E402

ROADMAP = hqpaths.ROADMAP
USAGE = os.path.join(hqpaths.HQ, ".status", "usage.json")
LIMIT = re.compile(r"\*\*Usage limit:\s*(\d{1,3})\s*%")
MODE = re.compile(r"\*\*5-hour line:\s*(moving|fixed)\b[^*]*\*\*", re.I)
MODE_LINE = ("- **5-hour line: {mode}.** Moving: the 5-hour usage line grows 10% every half hour of the session, "
             "10% right after a reset up to 100% in its last half hour (H87). Fixed: it stays at the usage limit "
             "above. Switched from a call or the status page.")


def read() -> tuple[str, int | None, bool]:
    text = open(ROADMAP, encoding="utf8").read()
    lim = LIMIT.search(text)
    mode = MODE.search(text)
    return text, int(lim.group(1)) if lim else None, (mode.group(1).lower() == "moving") if mode else True


def moving_now(now: float | None = None) -> tuple[int, float | None] | None:
    """Where the moving line stands now and when it next goes up, from the last saved 5-hour reset time."""
    try:
        u = json.load(open(USAGE, encoding="utf8"))
        reset = next(l["resetsAt"] for l in u.get("limits", []) if re.search(r"5-hour", l.get("label", ""), re.I))
        reset_t = round(datetime.fromisoformat(reset.replace("Z", "+00:00")).timestamp() / 60) * 60
    except Exception:
        return None
    now = time.time() if now is None else now
    start = reset_t - 5 * 3600
    if now >= reset_t:
        return 10, start + 5 * 3600 + 1800  # a new session: its first half hour
    begun = min(10, max(1, int((now - start) // 1800) + 1))
    return begun * 10, (start + begun * 1800) if begun < 10 else None


def describe() -> str:
    _, limit, moving = read()
    if limit is None:
        return "The roadmap names no usage limit, so there is no 5-hour line."
    if not moving:
        return f"The 5-hour line is fixed at {limit}%."
    at = moving_now()
    if at is None:
        return (f"The 5-hour line moves: 10% for every half hour of the session. No reset time is saved yet, "
                f"so for now it stands at the fixed {limit}%.")
    line, nxt = at
    up = f", up to {line + 10}% at {time.strftime('%H:%M', time.localtime(nxt))}" if nxt and line < 100 else ""
    return f"The 5-hour line moves: 10% for every half hour of the session; it's at {line}% now{up}."


def write(moving: bool, number: int | None) -> None:
    text, limit, _ = read()
    if limit is None:
        sys.exit("The roadmap names no usage limit (**Usage limit: N%**), so there is no 5-hour line to switch.")
    if number is not None:
        text = LIMIT.sub(f"**Usage limit: {number}%", text, count=1)
    mode = "moving" if moving else "fixed"
    if MODE.search(text):
        text = MODE.sub(f"**5-hour line: {mode}.**", text, count=1)
    else:
        lines = text.split("\n")
        i = next(i for i, l in enumerate(lines) if LIMIT.search(l))
        lines.insert(i + 1, MODE_LINE.format(mode=mode))
        text = "\n".join(lines)
    hqpaths.guard_roadmap(ROADMAP)  # F17: a test never changes the real roadmap
    tmp = ROADMAP + ".tmp"
    open(tmp, "w", encoding="utf8").write(text)
    os.replace(tmp, ROADMAP)


def main(argv: list[str]) -> int:
    if not argv:
        print(describe())
        return 0
    if argv[0] == "moving" and len(argv) == 1:
        write(True, None)
    elif argv[0] == "fixed" and len(argv) in (1, 2):
        number = None
        if len(argv) == 2:
            n = argv[1].rstrip("%")
            if not n.isdigit() or not 1 <= int(n) <= 100:
                print("The fixed number is a whole percentage from 1 to 100.", file=sys.stderr)
                return 2
            number = int(n)
        write(False, number)
    else:
        print(__doc__.strip().split("\n\n")[-1], file=sys.stderr)
        return 2
    print(describe())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
