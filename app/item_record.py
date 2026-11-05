"""F147 (4 November 2026, his words: "why is she lying, it is important he can trust what she says"): an item's facts come from
HQ's record, not from her memory. Every text she answers is a fresh session that only sees the thread, so asked how many review
rounds F146 took she rebuilt it and said one round, while the record had two. Now:

- before she answers, the record of each item his text names (its review rounds with verdicts and times, ready, the job and its
  state) goes in her prompt (`for_prompt`), never to him;
- her draft is checked against it (`misses`): a round count or a ready state the record contradicts, or one she states about an
  item with no record, no rounds yet or no clear item, is a miss;
- a miss holds the draft back, goes on the mistakes ledger, and she writes it again once with the record in front of her
  (`rewrite_note`); still wrong, the record's own words go out instead of those lines (`fallback`), no second rewrite. He only
  ever sees one normal reply.

His yes to this, 5 November 2026 (call, 12:52): "Yes, this is great. You can take it with a team and figure it out."
Prompting is the last line, the program is the guard.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

ROUTINE = Path(__file__).resolve().parent.parent / "routine"
if str(ROUTINE) not in sys.path:
    sys.path.insert(0, str(ROUTINE))

LABEL = re.compile(r"(?<![\w.])([A-Za-z]\d{1,5}(?:\.\d+)?)(?![\w])")
MOST = 5  # items with their record in one prompt
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
         11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen",
         18: "eighteen", 19: "nineteen", 20: "twenty"}
NUMS = {v: k for k, v in WORDS.items()} | {"a single": 1, "just one": 1, "only one": 1}
_COUNT = re.compile(r"\b(\d+|" + "|".join(sorted((re.escape(k) for k in NUMS), key=len, reverse=True)) +
                    r")\s+(?:(?:review|more|separate|full)\s+)?rounds?\b", re.I)
CANT = re.compile(r"couldn.t|can.t|cannot|not able|unable|no record|not sure|whether|don.t know", re.I)
_READY_YES = re.compile(r"\b(?:is|it's|it’s|'s|’s|are|was|been|got)\s+(?:now\s+|already\s+|also\s+|still\s+)?(?:marked\s+|set\s+)?(?:as\s+)?ready\b", re.I)
_READY_NO = re.compile(r"(?:\bnot|n't|n’t|\bnever)\s+(?:yet\s+|been\s+|got\s+)?(?:marked\s+|set\s+)?(?:as\s+)?ready\b|\bnot\s+(?:yet\s+)?ready\b"
                       r"|\b(?:no|without\s+an?|lacks\s+an?)\s+(?:ready\s+mark|mark\s+of\s+ready)\b|\bisn.t\s+(?:yet\s+)?marked\b"
                       r"|\b(?:hasn.t|has\s+not|wasn.t|never)\s+(?:yet\s+)?(?:been\s+)?marked\b", re.I)
_IF = re.compile(r"\b(when|once|if|until|till|as soon as|before|after|so that|whether)\b[^.,;]*$", re.I)  # "once it's ready" says nothing
# A line that says an item isn't there or had no rounds: wrong against a record that has rounds (QA, 5 November 2026 19:18:
# "F146 isn't on the planning, so no review count" went out while her record said two rounds, ready).
_NONE = re.compile(r"\b(?:isn.t|is\s+not|wasn.t|not)\s+(?:on|in)\s+(?:the\s+)?(?:planning|roadmap|plan|list)\b|\bno\s+(?:such\s+)?"
                   r"(?:item|row|record)\b|\b(?:can.t|cannot|couldn.t)\s+(?:find|see|locate)\b|\bnot\s+found\b|\bdoesn.t\s+exist\b"
                   r"|\bno\s+(?:review\s+)?(?:count|rounds?)\b|\bzero\s+(?:review\s+)?rounds?\b|\bany\s+(?:review\s+)?rounds?\b"
                   r"|\bnever\s+(?:been\s+)?reviewed\b|\bnot\s+(?:been\s+)?reviewed\b", re.I)
_ABOUT = re.compile(r"\brounds?\b|\bready\b|\breview|\bplanning\b|\brecord\b|\bcheck", re.I)
# QA, 5 November 2026 21:43: "its job stopped partway and left no record", "I haven't checked whether any of its work made it
# in" talk about the job or the work, not the rounds or the ready mark: not a claim the record can check.
_JOB_TALK = re.compile(r"\bjobs?\b|\bwork\b|\blanded\b|\bmade it in\b|\bcommits?\b|\bbuilds?\b|\bpushed\b", re.I)
_RECORD_TALK = re.compile(r"\brounds?\b|\bready\b|\breview|\bplanning\b|\broadmap\b", re.I)
ASKS = re.compile(r"\brounds?\b|\bready\b|\breview(?:ed|s)?\b|\bstatus\b|\bwhere (?:is|does) it stand\b", re.I)


def labels_in(text: str) -> list[str]:
    """The items a text names, in order, each once: an upper-case label always (F9999 too, so 'no record' can be said), a
    lower-case one (f93) only when the planning has it."""
    out = []
    for m in LABEL.finditer(text or ""):
        w = m.group(1)
        lab = w.upper()
        if lab in out:
            continue
        if w[0].isupper() or _row(lab):
            out.append(lab)
    return out


def _row(label: str):
    try:
        import sprint
        return sprint.row_of(label)
    except Exception:
        return None


def _state() -> dict:
    try:
        import sprint
        with open(sprint.RANKS, encoding="utf8") as f:
            return json.load(f)
    except Exception:
        return {}


def _entry(review: dict, label: str) -> dict | None:
    """The review entry of a row: its own key wins when it's there (the plain layout), else the one under rows."""
    if isinstance(review.get(label), dict):
        return review[label]
    e = (review.get("rows") or {}).get(label)
    return e if isinstance(e, dict) else None


def _job(label: str) -> dict | None:
    """The newest job on the team's list for this item: {"n", "state"}."""
    try:
        import jobs
        _t, js, _on = jobs.read()
    except Exception:
        return None
    pat = re.compile(rf"(?<![\w.]){re.escape(label)} on the (hq )?roadmap\b|\bthe {re.escape(label)} row\b", re.I)
    mine = [j for j in js if (j.get("item") or {}).get("label") == label or pat.search(j.get("text") or "")]
    return max(mine, key=lambda j: j["n"]) if mine else None


def _when(t) -> str:
    try:
        return time.strftime("%d %b %H:%M", time.localtime(float(t)))
    except Exception:
        return ""


def record(label: str, state: dict | None = None) -> dict:
    """What HQ's record says about one item: {"label", "found", "title", "row_state", "rounds": [{"verdict", "at"}], "ready",
    "job"}. found is False when neither the planning nor the review knows it."""
    label = label.upper()
    state = _state() if state is None else state
    row = _row(label)
    e = _entry(state.get("review") or {}, label)
    rounds = [{"verdict": x.get("verdict"), "at": x.get("at")} for x in ((e or {}).get("now_rounds") or []) if isinstance(x, dict)]
    mark = (state.get("ready") or {}).get(label)
    ready, changed = isinstance(mark, dict), False
    if ready and row:
        try:
            import sprint
            changed = not sprint.mark_holds(mark, row["line"])
        except Exception:
            pass
    j = _job(label) if (row or e) else None
    try:
        import sprint
        row_state = sprint.STATES.get(row["state"], "") if row else ""
    except Exception:
        row_state = ""
    return {"label": label, "found": bool(row or e), "title": (row or {}).get("title", "")[:80], "row_state": row_state,
            "rounds": rounds, "verdict": (e or {}).get("verdict") or "", "ready": ready, "marked": ready, "changed": changed,
            "job": {"n": j["n"], "state": j["state"]} if j else None}


def checkable(rec: dict) -> bool:
    return bool(rec.get("found") and rec.get("rounds"))


def _said(v: str) -> str:
    return {"flag": "flagged", "pass": "passed"}.get(v or "", v or "no verdict")


def rounds_words(rec: dict) -> str:
    """The record's own words for the rounds, for him: 'F93 took two review rounds: round 1 flagged, round 2 passed.'"""
    n = len(rec["rounds"])
    each = ", ".join(f"round {k} {_said(x['verdict'])}" for k, x in enumerate(rec["rounds"], 1))
    return f"{rec['label']} took {WORDS.get(n, str(n))} review round{'s' if n != 1 else ''}: {each}."


def ready_words(rec: dict) -> str:
    if rec["ready"] and rec.get("changed"):
        return f"{rec['label']} is marked ready, though its words changed since it was marked."
    if rec["ready"]:
        return f"{rec['label']} is marked ready."
    return f"{rec['label']} isn't marked ready."


def cant_words(rec: dict | None) -> str:
    if rec is None:
        return "I couldn't check that: I'm not sure which item you mean. Which one is it?"
    if not rec.get("found"):
        return f"I couldn't check that: there's no record of {rec['label']} in HQ."
    return (f"I couldn't check that: {rec['label']} has no review rounds on record yet, so I can't say how many it took or "
            "whether it's ready.")


def for_her(rec: dict) -> str:
    """One item's record as it goes in her prompt (never to him as is)."""
    lab = rec["label"]
    if not rec["found"]:
        return f"- {lab}: no record in HQ at all (no such item on the planning). You couldn't check it: say so, give no number or state."
    title = f" ({rec['title']})" if rec["title"] else ""
    if not rec["rounds"]:
        rs = (f"no review rounds on record yet. You couldn't check its rounds or whether it's ready: say so, give no number and "
              "don't call it ready.")
    else:
        n = len(rec["rounds"])
        rs = (f"{n} review round{'s' if n != 1 else ''}: " +
              ", ".join(f"round {k} {_said(x['verdict'])} ({_when(x['at'])})" for k, x in enumerate(rec["rounds"], 1)) +
              f"; its review now: {_said(rec['verdict'])}; " + (("marked ready (its words changed since the mark)" if rec.get("changed")
                                                                 else "marked ready") if rec["ready"] else "not marked ready"))
    j = rec["job"]
    js = f"job {j['n']}, {j['state']}" if j else "no job on the team's list for it"
    st = f"row {rec['row_state']}; " if rec["row_state"] else ""
    return f"- {lab}{title}: on HQ's planning; {st}{rs}. Job: {js}."


def context(words: str, history: str = "") -> dict:
    """What her answer is checked against: {"records": {label: rec}, "default": label | None, "asks": bool}. The items his text
    names; when it names none, those of the chat so far (the newest first)."""
    st = _state()
    named = labels_in(words)
    from_history = False
    if not named and history:
        named = list(reversed(labels_in(history)))[:MOST]
        from_history = True
    recs = {lab: record(lab, st) for lab in named[:MOST]}
    default = None
    if len(named) == 1 and not from_history:
        default = named[0]
    return {"records": recs, "default": default, "asks": bool(ASKS.search(words or "")), "state": st}


def for_prompt(ctx: dict) -> str:
    """The record part of her prompt, or '' when there's nothing to put in."""
    lines = [for_her(r) for r in ctx["records"].values()]
    if not lines and ctx["asks"]:
        return ("(From HQ, not from him: his text names no item, so you can't check which one he means. Don't give a number or a "
                "state from memory: say you couldn't check it and ask which item.)\n\n")
    if not lines:
        return ""
    return ("(HQ's record of the items in his text, from the planning, not from him and never shown to him as it is: answer from "
            "this, not from memory, and over anything else you see or look up: an item listed here is on the planning even when "
            "you don't find it elsewhere (it may be done or off the open list), so never say it isn't. A number or a state you "
            "give must match it; what isn't here you couldn't check, so say so and give no number. Answer in your own normal "
            "words.)\n" + "\n".join(lines) + "\n\n")


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def counts_in(s: str) -> set[int]:
    got = set()
    for m in _COUNT.finditer(s):
        if re.search(r"\b(not|n.t)\s*$", s[max(0, m.start() - 6):m.start()], re.I):
            continue  # "two rounds, not one round": named only to correct it
        v = m.group(1).lower()
        got.add(int(v) if v.isdigit() else NUMS[v])
    return got


def ready_in(s: str, first: bool = False, asks_ready: bool = False):
    """True when the sentence says the item is ready, False when it says it isn't, None when it says neither."""
    if _READY_NO.search(s):
        return False
    m = _READY_YES.search(s)
    if m and not _IF.search(s[max(0, m.start() - 30):m.start()]):
        return True
    if first and asks_ready and re.match(r"\s*(yes|yep|yeah)\b", s, re.I):
        return True
    if first and asks_ready and re.match(r"\s*(no|nope)\b", s, re.I):
        return False
    return None


def misses(draft: str, ctx: dict, words: str = "") -> list[dict]:
    """The lines of her draft the record contradicts or can't back: [{"sentence", "label", "what", "truth"}]. what is count, state
    or unchecked; truth the record's own words for him."""
    out = []
    asks_ready = bool(re.search(r"\bready\b", words or "", re.I))
    for k, s in enumerate(_sentences(draft)):
        named = labels_in(s)
        lab = named[0] if named else ctx["default"]
        if _JOB_TALK.search(s) and not _RECORD_TALK.search(s):
            continue  # about its job or its work, not its rounds or its mark
        none = bool(_NONE.search(s) or (CANT.search(s) and _ABOUT.search(s)))
        if none and lab:  # "isn't on the planning", "no rounds", "couldn't check": wrong when the record has its rounds
            if lab not in ctx["records"]:
                ctx["records"][lab] = record(lab, ctx.get("state"))
            rec = ctx["records"][lab]
            if checkable(rec):
                truth = rounds_words(rec) + (" " + ready_words(rec) if asks_ready else "")
                out.append({"sentence": s, "label": lab, "what": "count", "truth": truth})
                continue
            if rec.get("found") and _NONE.search(s) and not re.search(r"\brounds?\b|\breview", s, re.I):
                out.append({"sentence": s, "label": lab, "what": "unchecked", "truth": cant_words(rec)})
                continue  # "isn't on the planning" about an item that is, though it has no rounds yet
        if CANT.search(s):
            continue  # she says she couldn't check: no claim
        counts = counts_in(s)
        ready = ready_in(s, k == 0, asks_ready)
        if not counts and ready is None:
            continue
        if lab and lab not in ctx["records"]:
            ctx["records"][lab] = record(lab, ctx.get("state"))
        rec = ctx["records"].get(lab) if lab else None
        if rec is None or not checkable(rec):
            out.append({"sentence": s, "label": lab or "", "what": "unchecked", "truth": cant_words(rec)})
            continue
        n = len(rec["rounds"])
        if counts and counts != {n}:
            out.append({"sentence": s, "label": lab, "what": "count", "truth": rounds_words(rec)})
        elif ready is not None and ready != rec["ready"]:
            out.append({"sentence": s, "label": lab, "what": "state", "truth": ready_words(rec)})
    return out


def rewrite_note(ms: list[dict]) -> str:
    """What she gets when her draft is held back: the lines the record contradicts, and the record's true facts."""
    lines = []
    for m in ms:
        if m["what"] == "unchecked":
            lines.append(f"- You wrote \"{m['sentence']}\", but HQ has nothing to check it against: {m['truth']}")
        else:
            lines.append(f"- You wrote \"{m['sentence']}\", but the record contradicts it. HQ's record: {m['truth']}")
    return ("(A note from HQ, not from him: your text was held back and he hasn't seen it. A line in it is wrong against the record:\n"
            + "\n".join(lines) + "\nWrite your text to him again, in your own normal words, with the record's facts, not from memory. "
            "Where there's nothing to check, say you couldn't check it and give no number or state. Don't mention this note, the "
            "record's fields or that a text was held back.)")


def fallback(draft: str, ms: list[dict]) -> str:
    """Her rewrite was still wrong: each line the record contradicts is replaced, where it stood, by the record's own words, and
    only by what the rest of her text doesn't already tell (QA, 5 November 2026 21:43: the record's rounds went out beside her
    own telling of them, so he got the rounds twice)."""
    bad = {}
    for m in ms:
        bad.setdefault(m["sentence"], []).append(m["truth"])
    ss = _sentences(draft)
    kept = [s for s in ss if s not in bad]
    told_count = any(counts_in(s) or re.search(r"\bround\s+\d", s, re.I) for s in kept)
    told_ready = any(ready_in(s) is not None for s in kept)
    out, said = [], set()
    for s in ss:
        if s not in bad:
            out.append(s)
            continue
        for truth in bad[s]:
            for part in _sentences(truth):
                if part in said:
                    continue
                if counts_in(part) and told_count or ready_in(part) is not None and told_ready:
                    continue  # her other lines already tell it, rightly
                said.add(part)
                told_count = told_count or bool(counts_in(part))
                told_ready = told_ready or ready_in(part) is not None
                out.append(part)
    return " ".join(out).strip()


def log(agent: str, where: str, ms: list[dict], rewrite: bool = False) -> None:
    """Each miss on the mistakes ledger, naming the item."""
    try:
        import mistakes
        for m in ms:
            what = {"count": "a round count", "state": "a ready state", "unchecked": "a fact she couldn't check"}[m["what"]]
            lab = m["label"] or "no clear item"
            mistakes.add("from-memory", agent, f"{lab}: her {'rewrite' if rewrite else 'draft'} said \"{m['sentence']}\", "
                         f"{what} from memory; the record: {m['truth']}", where=where, label=m["label"])
    except Exception as e:
        print(f"item_record: the ledger: {e!r}", file=sys.stderr)


def guard(draft: str, ctx: dict, words: str, again, agent: str, where: str) -> str:
    """The text that goes to him. again(note) asks her for one rewrite and gives it back."""
    ms = misses(draft, ctx, words)
    if not ms:
        return draft
    log(agent, where, ms)
    try:
        second = again(rewrite_note(ms)) or ""
    except Exception as e:
        print(f"item_record: the rewrite: {e!r}", file=sys.stderr)
        second = ""
    if second.strip():
        ms2 = misses(second, ctx, words)
        if not ms2:
            return second
        log(agent, where, ms2, rewrite=True)
        return fallback(second, ms2) or fallback(draft, ms)
    return fallback(draft, ms)


if __name__ == "__main__":  # a look by hand: python3 app/item_record.py F93
    for lab in sys.argv[1:]:
        r = record(lab)
        print(for_her(r))
        if checkable(r):
            print("  for him:", rounds_words(r), ready_words(r))
