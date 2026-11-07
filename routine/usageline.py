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
    python3 routine/usageline.py reserve [N]           F100: the points kept for his calls and the small routines (0 to 50)
    python3 routine/usageline.py least [N]             F113: the reserve never takes the team's line under N points (0 to 50)
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
USAGE = os.environ.get("HQ_USAGE") or os.path.join(hqpaths.HQ, ".status", "usage.json")
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
    import usagecost
    if usagecost.five_on():
        return " ".join(describe_one(k, s[k]) for k in LINES)
    return "This plan has no 5-hour limit, so only the week counts. " + " ".join(describe_one(k, s[k]) for k in LINES if k != "five")


def line_text(key: str, moving: bool, number: int) -> str:
    if key == "five":
        return f"**5-hour line: {'moving' if moving else 'fixed'}.**"
    name = LINES[key][0]
    return f"**{name} line: moving; fixed at {number}% when switched.**" if moving else f"**{name} line: fixed at {number}%.**"


def write(key: str, moving: bool, number: int | None) -> None:
    import jobs  # F115: the planning file's one lock, the queue's: a switch here never undoes a planned line there
    with jobs.locked():
        _write(key, moving, number)


def _replace(text: str) -> None:
    hqpaths.guard_roadmap(ROADMAP)  # F17: a test never changes the real roadmap
    tmp = f"{ROADMAP}.{os.getpid()}.tmp"
    open(tmp, "w", encoding="utf8").write(text)
    os.replace(tmp, ROADMAP)


def _write(key: str, moving: bool, number: int | None) -> None:
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
    _replace(text)


RESERVE = re.compile(r"\*\*Usage reserve:\s*([0-9]{1,2})\b[^*]*\*\*")
# F113: where the usage settings stand on the roadmap: a line of its own (a list item or a paragraph), never a table's row
SETTING = re.compile(r"^(?:- )?\*\*(?:Usage limit|Usage reserve|Team line at least|Weekly limit|5-hour line|Weekly line|Fable line):")


def reserve_of(text: str) -> int:
    m = RESERVE.search(text)
    if m:
        return min(50, int(m.group(1)))  # F113: 0 to 50, as the command
    import usagecost  # F149: without his own number, the agents' weekly shares; F168: what's left of them this week
    return min(50, usagecost.agents_room())


def points(word: str) -> int | None:
    """F113: a whole number of points from 0 to 50 typed on the command line, or None (a "²" is no number)."""
    return int(word) if re.fullmatch(r"[0-9]{1,2}", word or "") and int(word) <= 50 else None


def insert_setting(text: str, new: str, words: str) -> str:
    """F113: a new usage setting goes right after the last of the usage settings, in their own list or paragraphs; never into a
    phase table or after a heading further down, where an older row may quote a setting."""
    lines = text.split("\n")
    first = next((j for j, l in enumerate(lines) if SETTING.match(l)), None)
    if first is None:
        first = next(j for j, l in enumerate(lines) if LIMIT.search(l) and not l.lstrip().startswith("|"))
    last = first
    for j in range(first + 1, len(lines)):
        l = lines[j]
        if l.startswith("#") or l.lstrip().startswith("|") or l.strip() == "---":
            break
        if SETTING.match(l):
            last = j
    if lines[last].startswith("- "):
        lines.insert(last + 1, f"- {new} {words}")
    else:
        lines[last + 1:last + 1] = ["", f"{new} {words}"]
    return "\n".join(lines)


def write_reserve(n: int) -> None:
    """F100: taken off each stop line for the agents' cycles and the team; on the roadmap, so both HQs read the same one."""
    import jobs  # F115: under the planning file's lock
    with jobs.locked():
        _write_reserve(n)


def _write_reserve(n: int) -> None:
    text, s = read()
    if s is None:
        sys.exit("The roadmap names no usage limit (**Usage limit: N%**), so there are no stop lines to keep a reserve under.")
    new = f"**Usage reserve: {n} points.**"
    if RESERVE.search(text):
        text = RESERVE.sub(lambda _: new, text, count=1)
    else:
        text = insert_setting(text, new, "Taken off each stop line for the agents' cycles and the team, so his calls and the "
                                         "small routines always have room (F100). Switched from a call.")
    _replace(text)


LEAST = re.compile(r"\*\*Team line at least:\s*([0-9]{1,2})\b[^*]*\*\*")


def least_of(text: str) -> int:
    m = LEAST.search(text)
    return min(50, int(m.group(1))) if m else 15  # 0 to 50, as the command


def write_least(n: int) -> None:
    """F113: the reserve never takes the team's line under this; on the roadmap, next to the reserve."""
    import jobs  # F115: under the planning file's lock
    with jobs.locked():
        _write_least(n)


def _write_least(n: int) -> None:
    text, s = read()
    if s is None:
        sys.exit("The roadmap names no usage limit (**Usage limit: N%**), so there are no stop lines to keep a reserve under.")
    new = f"**Team line at least: {n} points.**"
    if LEAST.search(text):
        text = LEAST.sub(lambda _: new, text, count=1)
    else:
        text = insert_setting(text, new, "The reserve never takes the team's stop line under this (or under the stop line itself), so "
                                         "the first hours after a reset still have room for the team and the agents; from a line of this plus "
                                         "the reserve on, the whole reserve is kept (F113). 0 keeps the whole reserve always. Switched from a call.")
    _replace(text)


def _writes(argv: list[str]) -> bool:
    rest = argv[1:] if argv and argv[0].lower() in ALIASES else argv
    return bool(rest) and (rest[0] in ("moving", "fixed") or (argv[0] in ("reserve", "least") and len(argv) == 2))


# F114 (the check's fix round): what names each line in his words. "The weekly Fable line" is the Fable one.
LINE_WORDS = {"five": re.compile(r"\b(?:5|five)[- ]?h(?:ou)?rs?\b|\b5h\b"), "weekly": re.compile(r"\bweek(?:ly)?\b"),
              "fable": re.compile(r"\bfable\b")}


def _norm(text: str) -> str:
    return " ".join(str(text).lower().replace("’", "'").split())


def lines_named(text: str) -> set:
    """F114: which stop lines these words name ("the weekly Fable line" is the Fable one)."""
    named = {k for k, rx in LINE_WORDS.items() if rx.search(_norm(text))}
    return named - {"weekly"} if "fable" in named else named


def numbers_in(text: str) -> set:
    """F114: the numbers in these words, the 5 of "5-hour" left out."""
    return {n for _, n in _numbers_at(_norm(text))}


def _numbers_at(low: str) -> list:
    blank = LINE_WORDS["five"].sub(lambda m: " " * len(m.group(0)), low)
    return [(m.start(), int(m.group(1))) for m in re.finditer(r"(?<![\d.:])(\d{1,3})(?![\d.:])", blank)]


_FIX = re.compile(r"\bfix(?:es|ed|ing)?\b")
_MOVE = re.compile(r"\bmov(?:e|es|ed|ing)\b")
# F114, the third check: what isn't an instruction (a question, a doubt, a wish), and a way said only to be denied ("it shouldn't keep moving").
_NOT_AN_ORDER = re.compile(r"\?|^(?:why|what|what's|how|when|where|who|which|is|are|was|were|do|does|did|should|shall|could|would|can|will|has|have)\b"
                           r"|\b(?:maybe|perhaps|should|shouldn't|might|i think|i guess|probably|wonder|not sure|right now|at the moment)\b")
_ORDER = re.compile(r"\b(?:fix|set|put|move|make|change|turn|switch|pin|lock|bring|keep|let)\b")
_DENIED = re.compile(r"\b(?:shouldn't|should not|mustn't|must not|don't|do not|doesn't|does not|not|never|no longer|stop(?:s|ped)?)\s+(?:\w+\s+){0,3}?"
                     r"(?:mov(?:e|es|ed|ing)|fix(?:es|ed|ing)?)\b")


_LEAD_YES = re.compile(r"(?:(?:yes|ok|okay|yeah)[\s,!.]+)?(?:nice|lovely|cool|fine|good|alright|great|perfect|awesome|excellent|yes|ok|okay|yeah|sure)\b[\s,!.]")


def _mentions(low: str) -> list:
    """F114: where each line is named in these words, in order, as (start, key); "the weekly Fable line" is one mention, of Fable."""
    found = sorted((m.start(), m.end(), k) for k, rx in LINE_WORDS.items() for m in rx.finditer(low))
    out = []
    for i, (a, b, k) in enumerate(found):
        if k == "weekly" and any(k2 == "fable" and 0 <= a2 - b <= 12 for a2, _, k2 in found[i + 1:]):
            continue
        out.append((a, k))
    return out


def _paired(low: str) -> dict:
    """F114, the third check: per line named, its numbers and the way asked for, from the part of the words that belongs to it: a number
    goes to the line named last before it (else the first one after it); a way said only to be denied doesn't count."""
    marks = _mentions(low)
    if not marks:
        return {}
    clean = _DENIED.sub(" ", low)
    out = {k: {"numbers": set(), "moving": False, "fixed": False} for _, k in marks}
    for at, n in _numbers_at(low):
        owner = next((k for a, k in reversed(marks) if a <= at), marks[0][1])
        out[owner]["numbers"].add(n)
    for i, (a, k) in enumerate(marks):
        part = clean[(0 if i == 0 else a):(marks[i + 1][0] if i + 1 < len(marks) else len(clean))]
        moving, fixed = bool(_MOVE.search(part)), bool(_FIX.search(part)) or bool(out[k]["numbers"])
        if not moving and not fixed:  # the way said once for the whole line ("fix the weekly at 95 and the fable at 80")
            moving, fixed = bool(_MOVE.search(clean)), bool(_FIX.search(clean))
        out[k]["moving"] |= moving and not fixed
        out[k]["fixed"] |= fixed
    return out


def opens(key: str, number: int | None, moving: bool, line: str, turn: str = "") -> bool:
    """F114: whether his line, or his yes to her question just before it, opens exactly this: the line, the way (moving or fixed) and the
    number. Third check: his own line must be an instruction or a yes, never a question, a maybe or a should; a number belongs to the line
    it's paired with in the words; moving or fixed is what he asked for, not a word in a "shouldn't". When his line names no line, his yes
    to her question that names exactly one opens it, at his number or else hers; a number in passing opens nothing."""
    low, hers_low = _norm(line), _norm(turn)
    mine = _paired(low)
    if mine:
        asked = _DENIED.sub(" ", low)  # "it shouldn't keep moving" is a way denied, not a doubt
        answers = bool(_LEAD_YES.match(asked)) and set(_paired(hers_low)) == {key} and not _held(line)  # "great, the weekly one at 95"
        if _NOT_AN_ORDER.search(asked) or not (_ORDER.search(asked) or sprint_yes(line, turn) or answers):
            return False
        if key not in mine:
            return False
        got = mine[key]
        if moving:
            return got["moving"]
        if got["moving"]:
            return False
        if number is None:
            return True
        if got["numbers"]:
            return number in got["numbers"]
        hers = _paired(hers_low)
        return set(hers) == {key} and number in hers[key]["numbers"]
    hers = _paired(hers_low)
    if set(hers) != {key} or not sprint_yes(line, turn):
        return False  # neither names one line: ask him which one
    clean = _DENIED.sub(" ", low)
    asked_move, asked_fix = bool(_MOVE.search(clean)), bool(_FIX.search(clean))
    if moving:
        return (asked_move or hers[key]["moving"]) and not asked_fix
    if asked_move and not asked_fix or (hers[key]["moving"] and not asked_fix and not numbers_in(low)):
        return False
    if number is None:
        return True
    his = numbers_in(low)
    return number in his if his else number in hers[key]["numbers"]


def _held(line: str) -> bool:
    import sprint
    return sprint.held_back(line)


def sprint_yes(line: str, turn: str) -> bool:
    import sprint
    return sprint.a_yes(line, turn)


def names_line(key: str, line: str, number: int | None = None) -> bool:
    """F114 (first round, kept for its callers): his line alone opens this line, fixed at this number."""
    return opens(key, number, False, line)


def his_say_so(words: str | None, key: str, number: int | None = None, places: list | None | str = "env", ws: str | None = None,
               moving: bool = False) -> str:
    """F114: why his words don't stand for switching this line, or "" when they do: a line he said or typed himself, today, on this call or
    in this chat (HQ_WORDS_FROM, which the session sets for its tools; by hand, any of today's), the program's own lines only (a transcript
    or a thread), not a no, and naming this line or its number. Never a job's own process; inside a call or a chat, never without words."""
    if os.environ.get("HQ_IN_JOB"):
        return "a job can't give itself his say-so"
    import sprint
    places = sprint.words_from_env() if places == "env" else places
    if words is None:
        return "this runs on a call or in a chat, so it needs his words with --said" if places is not None else ""
    if hqpaths.under_test() and not os.environ.get("HQ_PROOF_ON"):  # a test copy without lines of his, as sprint.his_quote
        return ""
    hits = sprint.his_said_now(words, ws, places=places)
    if not hits:
        return "those aren't his words from this call or this chat, today"
    ok = [h for h in hits if sprint.yes_reading(h["line"], h["turn"], ()) != "no"]
    if not ok:
        return "those are his words, but they say no"
    if not any(opens(key, number, moving, h["line"], h["turn"]) for h in ok):
        return (f"his words, or your question just before his yes, don't name this line ({LINES[key][0]}) and what to do with it"
                + (f" at {number}" if number is not None else "") + "; when neither names a line, ask him which one")
    return ""


def sprint_places():
    import sprint
    return sprint.words_from_env()


def main(argv: list[str]) -> int:
    if not argv:
        print(describe())
        return 0
    said = None
    orig = [a for a in argv]
    if "--said" in argv:  # F114: from a call or a chat, a switch stands on his own words; the status page is his own hand
        i = argv.index("--said")
        said, argv = (argv[i + 1] if i + 1 < len(argv) else ""), argv[:i] + argv[i + 2:]
        orig = list(argv)
        if not argv:
            print(describe())
            return 0
    import role
    handed = role.handed_words() if _writes(argv) else None
    if _writes(argv) and role.is_handed() and not handed:
        # F115 with F114 (the combined check): a handed switch stands only on words the backup checked at its own door
        print("Refused: a switch handed over from the other computer carries no words it checked there.", file=sys.stderr)
        return 2

    def refused(key, number=None, moving=False):
        if handed:  # checked on the backup, against the call or chat it came from: trusted here, and where it came from noted
            role.note_handed(f"usageline {' '.join(orig)}", handed)
            return False
        why = his_say_so(said, key, number, moving=moving)
        if why:
            print(f"Refused: {why}. A usage stop line changes only on his own words: --said \"HIS WORDS\", a line he said or typed, "
                  "naming the line (weekly, 5-hour or Fable) or its number.", file=sys.stderr)
        return bool(why)

    def to_main():
        """F115: on the backup a switch that passed its checks here goes to the main, which writes the planning file, with the
        words checked here. None when this computer writes it itself."""
        if os.environ.get("HQ_ROLE_HERE") or not role.is_backup():
            return None
        hits = []
        if said is not None and sprint_places() is not None:
            import sprint
            hits = sprint.his_said_now(said, None, sprint_places())
        return role.forward("usageline", list(orig) + (["--said", said] if said is not None else []),
                            env=role.checked_env(said, hits))
    if argv[0] == "least":
        if len(argv) == 2:
            if os.environ.get("HQ_IN_JOB") or sprint_places() is not None:  # F114: not from a job, a call or a chat, as the reserve
                print("Refused: the least line is set on the status page or by his own hand.", file=sys.stderr)
                return 2
            if points(argv[1]) is None:
                print("The least line is a whole number of points from 0 to 50.", file=sys.stderr)
                return 2
            if handed:
                role.note_handed(f"usageline {' '.join(orig)}", handed)
            r = to_main()
            if r is not None:
                return r
            write_least(points(argv[1]))
        print(f"The team's line stays at {least_of(read()[0])} points at the least when the reserve comes off "
              f"(the reserve is {reserve_of(read()[0])} points).")
        return 0
    if argv[0] == "reserve":
        if len(argv) == 2:
            if os.environ.get("HQ_IN_JOB") or sprint_places() is not None:  # F114: not from a job, a call or a chat
                print("Refused: the reserve is set on the status page or by his own hand.", file=sys.stderr)
                return 2
            if points(argv[1]) is None:
                print("The reserve is a whole number of points from 0 to 50.", file=sys.stderr)
                return 2
            if handed:
                role.note_handed(f"usageline {' '.join(orig)}", handed)
            r = to_main()
            if r is not None:
                return r
            write_reserve(points(argv[1]))
        print(f"The reserve is {reserve_of(read()[0])} points: taken off each stop line for the agents' cycles and the team.")
        return 0
    key = "five"
    if argv[0].lower() in ALIASES:
        key, argv = ALIASES[argv[0].lower()], argv[1:]
        if not argv:
            _, s = read()
            print(describe_one(key, s[key]) if s else describe())
            return 0
    if argv[0] == "moving" and len(argv) == 1:
        if refused(key, moving=True):
            return 2
        r = to_main()
        if r is not None:
            return r
        write(key, True, None)
    elif argv[0] == "fixed" and len(argv) in (1, 2):
        number = None
        if len(argv) == 2:
            n = argv[1].rstrip("%")
            if not n.isdigit() or not 1 <= int(n) <= 100:
                print("The fixed number is a whole percentage from 1 to 100.", file=sys.stderr)
                return 2
            number = int(n)
        if refused(key, number):
            return 2
        r = to_main()
        if r is not None:
            return r
        write(key, False, number)
    else:
        print(__doc__.strip().split("\n\n")[-1], file=sys.stderr)
        return 2
    _, s = read()
    print(describe_one(key, s[key]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
