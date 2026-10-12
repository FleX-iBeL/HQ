#!/usr/bin/env python3
"""H91: the three usage stop lines (the 5-hour line, the weekly all-models line and the weekly Fable line),
each moving every minute or fixed at a number, switched from a call or the status page. 12 October 2026 (call
at 21:00): "why don't we just skip the whole per hour and we just do it per minute? We do checks per minute
anyway." and "So all three of them move each minute and then all three have a fixed possibility." It grew out
of H87 (the 5-hour line only, 10% every half hour).

Moving (HQ's default): the line is the share of the limit's window that has gone by, recalculated every minute,
up to 100% in the minute before the reset; never below 10% for the 5-hour line or 20% for the weekly lines
(status/usage.mjs, movingLine, which the gate and the page use; this file says the same in words). Fixed: it
stays at a number. The settings are lines in the roadmap, so both HQs (laptop and server) read the same ones:
  - **Usage limit: 70%.**   the 5-hour line's fixed number
  - **5-hour line: moving.** or fixed.
  - **Weekly line: moving; fixed at 90% when switched.** or **Weekly line: fixed at 90%.**
  - **Fable line: …**       the same, for the weekly Fable limit
A job let past the line still only skips the 5-hour line; the weekly lines always count.

    python3 routine/usageline.py                       all three: which they are, and where they stand
    python3 routine/usageline.py moving                the 5-hour line moves (also: 5-hour moving)
    python3 routine/usageline.py fixed 60              the 5-hour line fixed at 60% (1 to 100; without a number, the one it has)
    python3 routine/usageline.py weekly moving         the weekly all-models line moves
    python3 routine/usageline.py weekly fixed 95       the weekly all-models line fixed at 95%
    python3 routine/usageline.py fable moving|fixed [N]   the same for the weekly Fable line
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
FLAT = re.compile(r"\*\*Weekly limit:\s*(\d{1,3})\s*%")
WEEKLY_FIXED = 90  # a weekly line fixed with no number of its own (Claude's choice), as in usage.mjs

# key: (roadmap name, spoken name, window in seconds, floor %, plan limit label test)
LINES = {
    "five": ("5-hour", "The 5-hour line", 5 * 3600, 10, re.compile(r"5-hour", re.I)),
    "weekly": ("Weekly", "The weekly line (all models)", 7 * 86400, 20, re.compile(r"^weekly(?!.*fable)", re.I)),
    "fable": ("Fable", "The weekly Fable line", 7 * 86400, 20, re.compile(r"^weekly.*fable", re.I)),
}
ALIASES = {"five": "five", "5-hour": "five", "5h": "five", "weekly": "weekly", "week": "weekly", "fable": "fable"}
WHAT = {
    "five": ("Moving: the 5-hour usage line grows every minute through the session, from 10% after a reset up to "
             "100% at the next (H87, H91). Fixed: it stays at the usage limit above. Switched from a call or the "
             "status page."),
    "weekly": ("Moving: the weekly all-models line grows every minute through the week, from 20% up to 100% at "
               "its reset (H91). Fixed: it stays at the number in it. Switched from a call or the status page."),
    "fable": ("Moving: the weekly Fable line grows every minute through its week, from 20% up to 100% at its "
              "reset (H91). Fixed: it stays at the number in it. Switched from a call or the status page."),
}


def mode_re(key: str) -> re.Pattern:
    return re.compile(r"\*\*" + re.escape(LINES[key][0]) + r" line:\s*(moving|fixed)\b([^*]*)\*\*", re.I)


def settings(text: str) -> dict | None:
    """The same reading as lineSettings in status/usage.mjs. None: the roadmap names no usage limit."""
    lim = LIMIT.search(text)
    if not lim:
        return None
    flat = FLAT.search(text)
    old = {"moving": not flat, "fixed": int(flat.group(1)) if flat else WEEKLY_FIXED}
    out = {}
    for key in LINES:
        m = mode_re(key).search(text)
        n = re.search(r"(\d{1,3})\s*%", m.group(2)) if m else None
        if key == "five":
            out[key] = {"moving": m.group(1).lower() == "moving" if m else True, "fixed": int(lim.group(1))}
        elif m:
            out[key] = {"moving": m.group(1).lower() == "moving", "fixed": int(n.group(1)) if n else old["fixed"]}
        else:
            out[key] = dict(old)
    return out


def read() -> tuple[str, dict | None]:
    text = open(ROADMAP, encoding="utf8").read()
    return text, settings(text)


def moving_now(key: str, now: float | None = None) -> tuple[float, float] | None:
    """Where the moving line stands now, and how much it climbs an hour, from the last saved reset time."""
    _, _, window, floor, test = LINES[key]
    try:
        u = json.load(open(USAGE, encoding="utf8"))
        reset = next(l["resetsAt"] for l in u.get("limits", []) if test.search(l.get("label", "")))
        reset_t = round(datetime.fromisoformat(reset.replace("Z", "+00:00")).timestamp() / 60) * 60
    except Exception:
        return None
    now = time.time() if now is None else now
    minutes = window // 60
    start = reset_t - window
    if now >= reset_t:  # a new window since the last reading
        start += window
    begun = min(minutes, max(1, int((now - start) // 60) + 1))
    return max(floor, round(1000 * begun / minutes) / 10), round(100 * 3600 * 10 / window) / 10


def pct(x: float) -> str:
    return f"{x:g}%"


def describe_one(key: str, s: dict) -> str:
    name = LINES[key][1]
    if not s["moving"]:
        return f"{name} is fixed at {s['fixed']}%."
    at = moving_now(key)
    how = "every minute through the session" if key == "five" else "every minute through the week"
    if at is None:
        return f"{name} moves, {how}; no reset time is saved yet, so for now it stands at {s['fixed']}%."
    line, per_hour = at
    rate = f"{pct(per_hour)} an hour" if per_hour >= 1 else f"about {pct(round(per_hour * 24))} a day"
    if line <= LINES[key][3]:
        return f"{name} moves, {how}; it's at its starting {pct(line)} now, then climbs {rate}."
    if line >= 100:
        return f"{name} moves, {how}; it's at 100% now, until the reset."
    return f"{name} moves, {how}; it's at {pct(line)} now, climbing {rate}."


def describe() -> str:
    _, s = read()
    if s is None:
        return "The roadmap names no usage limit, so there are no stop lines."
    return " ".join(describe_one(k, s[k]) for k in LINES)


def line_text(key: str, moving: bool, number: int) -> str:
    if key == "five":
        return f"**5-hour line: {'moving' if moving else 'fixed'}.**"
    name = LINES[key][0]
    return f"**{name} line: moving; fixed at {number}% when switched.**" if moving else f"**{name} line: fixed at {number}%.**"


def write(key: str, moving: bool, number: int | None) -> None:
    text, s = read()
    if s is None:
        sys.exit("The roadmap names no usage limit (**Usage limit: N%**), so there are no stop lines to switch.")
    if key == "five" and number is not None:
        text = LIMIT.sub(f"**Usage limit: {number}%", text, count=1)
    new = line_text(key, moving, number if number is not None else s[key]["fixed"])
    if mode_re(key).search(text):
        text = mode_re(key).sub(lambda _: new, text, count=1)
    else:
        lines = text.split("\n")
        # Under the usage limit, after whichever of the three lines before it are there already.
        i = next(i for i, l in enumerate(lines) if LIMIT.search(l))
        for k in LINES:
            if k == key:
                break
            j = next((j for j, l in enumerate(lines) if mode_re(k).search(l)), None)
            if j is not None and j > i:
                i = j
        lines.insert(i + 1, f"- {new} {WHAT[key]}")
        text = "\n".join(lines)
    hqpaths.guard_roadmap(ROADMAP)  # F17: a test never changes the real roadmap
    tmp = ROADMAP + ".tmp"
    open(tmp, "w", encoding="utf8").write(text)
    os.replace(tmp, ROADMAP)


def main(argv: list[str]) -> int:
    if not argv:
        print(describe())
        return 0
    key = "five"
    if argv[0].lower() in ALIASES:
        key, argv = ALIASES[argv[0].lower()], argv[1:]
        if not argv:
            _, s = read()
            print(describe_one(key, s[key]) if s else describe())
            return 0
    if argv[0] == "moving" and len(argv) == 1:
        write(key, True, None)
    elif argv[0] == "fixed" and len(argv) in (1, 2):
        number = None
        if len(argv) == 2:
            n = argv[1].rstrip("%")
            if not n.isdigit() or not 1 <= int(n) <= 100:
                print("The fixed number is a whole percentage from 1 to 100.", file=sys.stderr)
                return 2
            number = int(n)
        write(key, False, number)
    else:
        print(__doc__.strip().split("\n\n")[-1], file=sys.stderr)
        return 2
    _, s = read()
    print(describe_one(key, s[key]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
