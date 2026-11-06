"""The outbox (H338): every text of hers ends in direct_line.add(), so what was only written down in her rules is done here,
before a line is written: the style filter, the claim check, no question already answered, one text per topic, her batches
(the low-information diet). His words of 6 November 2026: "if we want them to do things, we had to do it through tooling right?"
"""
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# -- the style filter: a job number or a file path never reaches him (the call's SpeechFilter does the same on a call) ---------
_JOBNO = re.compile(r"\b(?:the )?job (?:no\.? ?|number )?#?\d{2,}\b", re.I)
_PATH = re.compile(r"(?<![:/\w.])(?:~|\.{1,2})?/(?:[\w.@-]+/)+[\w@-]+(?:\.\w+)?|(?<![/\w.])[\w-]+\.(?:py|mjs|js|jsonl|json|sh)\b")  # never a web link


def style(text: str) -> str:
    """A job number becomes "the job", a path or a file name "the code"; the rest as she said it."""
    out = _JOBNO.sub(lambda m: "The job" if m.group(0)[:1].isupper() else "the job", text or "")
    out = _PATH.sub("the code", out)
    out = re.sub(r"\bthe code(?:,? the code)+\b", "the code", out)
    return re.sub(r"[ \t]{2,}", " ", out)


# -- the claim check: "it's in your calendar" with no calendar write behind it is held, rewritten and logged ------------------
_CLAIM = re.compile(r"\b(?:(?:is|are|they're|it's|now|both \w+)\s+(?:now\s+)?in your calendar|(?:added|put|booked|written)\b[^.\n]{0,40}"
                    r"\b(?:to|in|into) your calendar)\b", re.I)
_NOT = re.compile(r"\b(?:not|isn't|aren't|yet|couldn't|didn't|I'll|I will|shall I|should I|want me to|can I)\b|n't\b|\?", re.I)
CLAIM_MINUTES = 30


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def claims_calendar(text: str) -> bool:
    return any(_CLAIM.search(s) and not _NOT.search(s) for s in _sentences(text))


def _jsonl(f: Path) -> list[dict]:
    try:
        rows = f.read_text(encoding="utf8").splitlines()
    except OSError:
        return []
    out = []
    for r in rows:
        try:
            out.append(json.loads(r))
        except ValueError:
            pass
    return [x for x in out if isinstance(x, dict)]


def wrote_calendar(where: Path, what: str = "") -> None:
    """A calendar write that really happened, kept next to the line: her "it's in your calendar" then goes through."""
    where.mkdir(parents=True, exist_ok=True)
    with open(where / "calendar-writes.jsonl", "a", encoding="utf8") as f:
        f.write(json.dumps({"at": round(time.time(), 3), "what": what}, ensure_ascii=False) + "\n")


def _hqpaths():
    sys.path.insert(0, str(ROOT / "routine"))
    import hqpaths
    return hqpaths


def writes_file() -> Path:
    """Every calendar write that came back, from a call, a text or a cycle (policy.seen, cycles), in HQ's data folder."""
    return Path(_hqpaths().DATA) / "direct-line" / "calendar-writes.jsonl"  # the line's folder: never synced or committed


def calendar_written(what: str = "") -> None:
    try:
        f = writes_file()
        f.parent.mkdir(parents=True, exist_ok=True)
        rows = [x for x in _jsonl(f) if time.time() - float(x.get("at") or 0) < 86400][-200:]
        rows.append({"at": round(time.time(), 3), "what": what})
        tmp = f.with_name(f.name + ".tmp")
        tmp.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf8")
        tmp.replace(f)
    except Exception as e:
        print(f"outbox: {e!r}", file=sys.stderr)


def _wrote_lately(where: Path) -> bool:
    rows = _jsonl(where / "calendar-writes.jsonl")
    if not _hqpaths().under_test():  # a test's throwaway line has only its own writes
        rows += _jsonl(writes_file())
    return any(time.time() - float(x.get("at") or 0) < CLAIM_MINUTES * 60 for x in rows)


def _rewrite_claim(text: str) -> str:
    keep = " ".join(s for s in _sentences(text) if not claims_calendar(s)).strip()
    return ("Correction: that isn't in your calendar yet, nothing was written to it; I'll tell you once it really is."
            + (" " + keep if keep else ""))


# -- one text per topic: the same topic from two senders on one day reaches him once -------------------------------------------
_STOP = set("the and but for with your you his her its this that these those today tonight are was were been still just now "
            "than then from into onto about not yet reminder says say said has have had what when will can".split())
# Only reminders and nudges count: an answer to him, an ask, an incident's down and back are never taken for a repeat.
REMINDING = ("game", "game-away", "cycle", "cycle-batch", "nudge", "nudge-later", "remind", "appt", "initiative", "loose-end", "checkin")


def _reminding(why: str) -> bool:
    return (why or "").split(":", 1)[0] in REMINDING


def _words(text: str) -> set:
    out = set()
    for w in re.findall(r"[a-z][a-z']+", (text or "").lower()):
        w = w[:-2] if w.endswith("'s") else w.rstrip("'")
        if len(w) > 2 and w not in _STOP and "'" not in w:
            out.add(w)
    return out


def same_topic(a: str, b: str) -> bool:
    wa, wb = _words(a), _words(b)
    both = wa & wb
    return len(both) >= 3 and len(both) / max(1, min(len(wa), len(wb))) >= 0.5


def _day(t: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(t))


def _repeat(m: dict, msgs: list[dict]) -> dict | None:
    if not _reminding(m.get("why")):
        return None
    for x in reversed(msgs):
        if _day(float(x.get("at") or 0)) != _day(m["at"]):
            break
        if (x.get("from") == "agent" and not x.get("quiet") and _reminding(x.get("why"))
                and x.get("why") != m.get("why") and same_topic(x.get("text", ""), m["text"])):
            return x
    return None


# -- no question already answered: his answer on an item is on the line with its date; asked again, the ask is refused ----------
def _answered(m: dict, msgs: list[dict]) -> dict | None:
    if m.get("why") not in ("ask", "cycle-ask") or not m.get("item") or "?" not in m["text"]:
        return None
    for k, x in enumerate(msgs):
        if x.get("from") != "me" or x.get("quiet"):
            continue
        before = msgs[k - 1] if k else {}
        if x.get("item") == m["item"] or (before.get("from") == "agent" and before.get("item") == m["item"]
                                          and "?" in before.get("text", "")):
            return x
    return None


# -- the low-information diet: with her batch times set, what can wait goes into her next batch; the rest breaks through ---------
# Breaks through at once: an appointment ping he asked for, a travel delay, a very important mail, a game reminder, a tripwire,
# her answers to him, an incident. Waits for the batch: these kinds.
BATCHED = ("nudge", "nudge-later", "loose-end")  # a cycle queues its own with cycles.py batch


def _batched(m: dict, aid: str) -> str:
    if (m.get("why") or "") not in BATCHED:
        return ""
    try:
        sys.path.insert(0, str(ROOT / "routine"))
        import cycles as _cy
        times = _cy.agent_settings(aid).get("batches")
        if not times:
            return ""
        import datetime as dt
        now = dt.datetime.now()
        nxt = min(now.replace(hour=int(t[:2]), minute=int(t[3:5]), second=0, microsecond=0)
                  + dt.timedelta(days=0 if t > now.strftime("%H:%M") else 1) for t in times)
        out = _cy.batch(aid, m["text"], until=(nxt + dt.timedelta(minutes=15)).strftime(_cy.FMT))  # good until her next batch
        return out if out.startswith("Queued") else ""
    except Exception as e:
        print(f"outbox batch: {e!r}", file=sys.stderr)
        return ""


def check(m: dict, where: Path, msgs: list[dict], aid: str) -> dict:
    """The text to write (maybe changed), or {"refused"|"same"|"queued": why, ...} with nothing to write."""
    if m.get("from") != "agent" or m.get("quiet"):
        return m
    m["text"] = style(m["text"]).strip()
    if claims_calendar(m["text"]) and not _wrote_lately(where):
        where.mkdir(parents=True, exist_ok=True)
        with open(where / "held-claims.jsonl", "a", encoding="utf8") as f:
            f.write(json.dumps({"at": m["at"], "said": m["text"], "why": m.get("why", ""),
                                "held": "a calendar claim with no calendar write behind it"}, ensure_ascii=False) + "\n")
        m = {**m, "text": _rewrite_claim(m["text"]), "held": "claim"}
    ans = _answered(m, msgs)
    if ans:
        when = _day(float(ans.get("at") or 0))
        return {"refused": f"already answered: on {when} he said \"{ans['text']}\" about {m['item']}; not asked again",
                "answer": ans["text"], "date": when, "item": m["item"]}
    same = _repeat(m, msgs)
    if same:
        return {"same": f"the same topic went to him today already ({same.get('why')}): not sent twice", "text": m["text"],
                "why": m.get("why", ""), "id": same.get("id", ""), "at": m["at"]}
    q = _batched(m, aid)
    if q:
        return {"queued": q, "text": m["text"], "why": m.get("why", ""), "id": m["id"], "at": m["at"]}
    return m


# -- promises carried on (H338, Part C 2): a reply that says she'll take a step herself, and ends on no question for him ----------
_PROMISE = re.compile(r"\b(I'll|I will|I'm going to|next I|then I|I can now|so I'll|let me)\b", re.I)
_WAITS = re.compile(r"\b(once you|until you|your call|waiting on you|when you answer|if you|no change|nothing'?s moved)\b", re.I)


def promises(text: str) -> bool:
    """Her text ends on a step she says she'll take herself, not on a question for him."""
    tail = (text or "").strip().split("\n\n")[-1]
    return bool(_PROMISE.search(text or "")) and "?" not in tail and not _WAITS.search(text or "")


def promised(text: str) -> str:
    """The sentence of hers that promises the step."""
    return next((s.strip() for s in _sentences(text) if _PROMISE.search(s)), (text or "").strip())[:200]
