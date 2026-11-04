#!/usr/bin/env python3
"""F103, the ledger: one append-only list of mistakes, read for the score with no model.

His words, 30 October 2026: "All calls, all chats, everything needs to be checked and needs to be logged when people make
mistakes. The scoring system needs to be across the whole build otherwise it doesn't make any fucking sense." One JSON line per
mistake in the workspace's `HQ/mistakes.jsonl`, never in HQ; nothing here changes or removes a line. A call or a text can only add
through this script (app/policy.py refuses the file itself).

What goes in, and who writes it:
- correction: his correction on a call or in a text. The after-call wrap-up tags them in the same run (a model reads the call, the
  program checks the quote is his, and takes the agent from the transcript, never from the one tagging), and a text's agent the same.
  The clearest ones the program finds by itself (CLEAR below), so a call whose wrap-up never ran still counts. Any other line a model
  tags gets one short second look (second_look) before it's believed: his words alone don't make it a correction.
- stop-asking, say-yes: his "stop asking" and "you just say yes" lines (C12), found by the program.
- refused: a refused outward action (mail sent, replied, forwarded), from app/policy.py, routine/cyclehook.py and the cycles.
- qa-fail: every QA fail, against the team's build (qa.py fail).
- bug-after-qa: a bug found after a QA pass, against that QA: `jobs.py write-row "…" --bug --after-qa LABEL`, here by hand, or a
  later QA fail on a row that had passed.

    python3 routine/mistakes.py add correction --call HQ/calls/NAME.md --said "HIS WORDS" [--handoff "X to Y"] [--item ID|LABEL]
    python3 routine/mistakes.py add correction --line direct-line|coaching-line|team-line --said "HIS WORDS"
    python3 routine/mistakes.py add bug-after-qa LABEL "WHAT WAS FOUND"
    python3 routine/mistakes.py scan [--call PATH | --all]    the program's own pass; without a target, what's new since the last pass
    python3 routine/mistakes.py list [--days N] [--agent A]
    python3 routine/mistakes.py score [--days N] [--json]     per agent and per hand-off, from the ledger alone; with what the pass read
                                                              and couldn't (F97) and what the second looks cost (.status/mistakes-looks.jsonl)
    python3 routine/mistakes.py put JSON                      the main writes a line the backup handed over (role.WRITES)
Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqlock  # noqa: E402
import hqpaths  # noqa: E402

REL = os.path.join("HQ", "mistakes.jsonl")
# The hand-off each kind belongs to, unless a line names its own ("Pepper to Moneypenny").
HANDOFF = {"correction": "him to the agent", "stop-asking": "him to the agent", "say-yes": "him to the agent",
           "refused": "the agent to the outside", "qa-fail": "the build to QA", "bug-after-qa": "QA to the release"}
KINDS = tuple(HANDOFF)
QUOTE_LEAST = 3  # F103: the shortest quote taken as his words, the same three words as sprint.his_quote
WORDS_KEPT = 600  # F103: how much of a line of his the ledger keeps; the transcript holds the rest
THREADS = {"direct-line": "donna", "coaching-line": "pepper", "team-line": "moneypenny"}
ONE_HANDOFF = re.compile(r"^[\w .'-]{1,40} to [\w .'-]{1,40}$")
MERGED = ("handoff", "item", "label")  # what a later tag may add to a line that's already there
LOOK_MODEL = "haiku"  # F103: the second look, the same small look as about_self's harvest
LOOK_BUDGET = 0.05
LOOK_TIMEOUT = 45
LOOK_SYSTEM = ("You read one thing a man said to his AI assistant on a call or in a text, with what was said just before it. Is he correcting "
               "the assistant here: telling it that it got something wrong, did what he didn't ask, or should have done otherwise? Thanks, "
               "praise, a question, a plain no to a question and a new request are not corrections. Answer with one word: yes or no.")

# What the program reads as a mistake from his own line, no model. Not "no", "wrong" or "what is this" on their own: those counted
# "No problem, thanks!" and "what is this amazing thing". What needs reading between the lines is the wrap-up's.
CLEAR = {
    "say-yes": re.compile(r"\byou (?:just |only |always |keep |keep on |literally )+(?:say|saying|said) yes\b|\byou'?re (?:just |only |always )?saying yes\b"
                          r"|\byou say yes to (?:everything|whatever|anything)\b|\bstop (?:saying yes|agreeing)\b"
                          r"|\byou (?:just |only |always |keep )*agree(?:ing)? with (?:me|everything|whatever)\b", re.I),
    "stop-asking": re.compile(r"\bstop asking\b|\b(?:quit|enough) asking\b|\bdon'?t (?:keep |ever )?ask(?:ing)? me (?:that|this|again|every)\b", re.I),
    "correction": re.compile(r"^\W*rule\b(?!s)|\b(?:new|another|add a|make (?:it|that|this) a|that'?s a|this is a) rule\b"
                             r"|\b(?:that'?s|thats|that is|this is) (?:wrong|not (?:right|correct|acceptable|what i (?:said|asked|meant|wanted)))\b"
                             r"|\bnot what i (?:said|asked|meant|wanted|requested)\b"
                             r"|\byou (?:got|read|did) (?:it|that|this) wrong\b"
                             r"|\b(?:didn'?t|did not|doesn'?t|does not) (?:deliver|do) what i\b", re.I),
}
_HEAD = re.compile(r"^Started \d\d:\d\d:\d\d · (?:agent ([^·\n]+?) · )?", re.M)
_LINE = re.compile(r"^- (\d\d:\d\d)(?::\d\d)? \*\*([^*:(]+?)(?: \(([^)]*)\))?:\*\* (.*)$")
_TAIL = re.compile(r"(?:\s*\*\([^)]*\)\*)+\s*$")  # *(typed)*, *(cancelled)*


def path(base=None) -> str | None:
    """The ledger's file, or None for a test that gave no folder of its own (it never writes in a real one)."""
    if base:
        return os.path.join(str(base), REL)
    if os.environ.get("HQ_MISTAKES"):
        return os.environ["HQ_MISTAKES"]
    if os.environ.get("HQ_ROADMAP"):
        return os.path.join(os.path.dirname(hqpaths.ROADMAP), "mistakes.jsonl")
    if hqpaths.under_test() and not os.environ.get("HQ_WORKSPACE"):
        return None
    return os.path.join(hqpaths.FOLDER, REL)


def read(base=None, since: float | None = None, until: float | None = None) -> list[dict]:
    p = path(base)
    out = []
    if not p:
        return out
    more: dict = {}
    try:
        with open(p, encoding="utf8") as f:
            for l in f:
                try:
                    d = json.loads(l)
                except ValueError:
                    continue
                if isinstance(d, dict) and d.get("more"):  # what a later tag added to a line: the file itself only ever grows
                    more.setdefault(d["more"], {}).update({k: d[k] for k in MERGED if d.get(k)})
                elif isinstance(d, dict) and d.get("kind") and (since is None or d.get("at", 0) >= since) and (until is None or d.get("at", 0) < until):
                    out.append(d)
    except OSError:
        pass
    for d in out:
        d.update(more.get(d.get("key")) or {})
    return out


def _backup() -> bool:
    if os.environ.get("HQ_ROLE_HERE"):
        return False
    try:
        import role
        return role.is_backup()
    except Exception:
        return False


def _workspace(base=None) -> bool:
    """Whether a line goes in the real workspace, the only one with a main to hand it to; a test's own folder stays local."""
    return base is None or os.path.realpath(str(base)) == os.path.realpath(hqpaths.FOLDER)


def _append(line: dict, base=None) -> bool:
    """False when a line with its key is already there: one event, one line. A hand-off or an item it didn't have yet lands on that
    line, as a line of its own that read() folds in."""
    p = path(base)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with hqlock.locked(p):
        have = next((d for d in read(base) if d.get("key") == line["key"]), None)
        if have:
            more = {k: line[k] for k in MERGED if line.get(k) and line[k] != have.get(k) and not (k == "handoff" and line[k] == HANDOFF.get(line["kind"]))}
            if not more:
                return False
            line = {"more": line["key"], "at": line["at"], **more}
        with open(p, "a", encoding="utf8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return True


def add(kind: str, agent: str, words: str, *, where: str = "", handoff: str = "", item: str = "", label: str = "", key: str = "",
        by: str = "the program", at: float | None = None, base=None) -> dict | None:
    """One line, or None when it's already there or nothing can be written. Never raises: a ledger that can't be written is a red
    line on the page, not a stopped call."""
    words = " ".join(str(words).split())[:WORDS_KEPT]
    who = " ".join(str(agent or "").split()).lower() or "unknown"
    line = {"at": round(at or time.time(), 3), "kind": kind, "agent": who, "handoff": handoff or HANDOFF.get(kind, ""), "words": words,
            "where": where, "by": by, "key": key or hashlib.sha256(f"{kind}|{where}|{words}".encode()).hexdigest()[:16],
            **({"item": item} if item else {}), **({"label": label} if label else {})}
    try:
        if not path(base):
            return None
        if hqpaths.under_test() and os.path.realpath(path(base)) == os.path.join(os.path.dirname(hqpaths.real_roadmap()), "mistakes.jsonl"):
            return None  # nowroad: a test, a flow or a probe never writes his real ledger, whatever folder it was given
        if _workspace(base) and _backup():  # one-way sync: what's written here would stay here for good
            import role
            code, _o, _e, how = role.hand("mistakes", ["put", json.dumps(line, ensure_ascii=False)], timeout=15)
            if how == "kept" or (how == "main" and code == 0):
                return line
        return line if _append(line, base) else None
    except Exception as e:
        print(f"(the ledger: {e!r})", file=sys.stderr)
        try:
            import routines
            routines.bad("mistakes", f"the ledger couldn't be written: {e!r}", every=30 * 86400)
        except Exception:
            pass
        return None


# -- his own lines --------------------------------------------------------------------------------------------------

def _bare(t: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", " ".join(str(t).lower().split()), flags=re.UNICODE).split())


def _folder(base=None) -> str:
    return str(base or hqpaths.FOLDER)


def _his_name(base=None) -> str:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "app"))
    import me as _me
    from pathlib import Path
    return _me.load(Path(_folder(base)))["name"] or "Me"


_ENDED = re.compile(r"^Ended \d\d:\d\d(?::\d\d)?", re.M)


def read_call(p: str, base=None) -> tuple[list[dict] | None, str, bool]:
    """F97: (his lines, why it couldn't be read, whether the call has ended). None and a why when the transcript can't be
    opened or isn't a transcript, so the pass counts it as not read and tries it again, never as a call with nothing in it."""
    try:
        text = open(p, encoding="utf8", errors="replace").read()
    except OSError as e:
        return None, f"it can't be opened ({e.strerror or type(e).__name__})", False
    first = next((l for l in text.splitlines() if l.strip()), "")
    if not first.startswith("# "):
        try:
            old = time.time() - os.path.getmtime(p) >= OPEN_DAYS * 86400
        except OSError:
            old = False
        if old and not any(_LINE.match(l) for l in text.splitlines()):
            return [], "", True  # F97: a stub nobody wrote into for a day: read, and nothing in it
        return None, "it isn't in a transcript's shape (no heading)", False
    return _his_lines(p, text, base), "", bool(_ENDED.search(text))


def call_lines(p: str, base=None) -> list[dict]:
    """His lines of a transcript: {"n" (its line number), "words", "agent" (who spoke just before him, else the call's agent)}."""
    try:
        text = open(p, encoding="utf8", errors="replace").read()
    except OSError:
        return []
    return _his_lines(p, text, base)


def _his_lines(p: str, text: str, base=None) -> list[dict]:
    me = _his_name(base).lower()
    h = _HEAD.search(text)
    agent = (h.group(1) or "").strip() if h else ""
    out = []
    day = re.match(r"(\d{4}-\d\d-\d\d)-\d{4}", os.path.basename(p))
    for i, l in enumerate(text.splitlines(), 1):
        m = _LINE.match(l)
        if not m:
            continue
        who = m.group(2).strip()
        if who.lower() == me:
            if "*(cancelled)*" not in m.group(4):
                out.append({"n": i, "words": _TAIL.sub("", m.group(4)).strip(), "agent": agent, "at": _when(day, l)})
        elif m.group(3):  # HQ (Pepper): who took that turn on a three-way
            agent = m.group(3).strip()
    return out


def _when(day, line: str) -> float | None:
    """When a transcript's line was said: the call's day from its name, the time from the line."""
    try:
        return time.mktime(time.strptime(f"{day.group(1)} {line[2:7]}", "%Y-%m-%d %H:%M"))
    except (AttributeError, ValueError):
        return None


def read_thread(line: str, base=None) -> tuple[list[dict], int, str]:
    """F97: (his lines of a text thread, how many of its lines couldn't be read, why the thread itself couldn't be, else '').
    A thread that isn't there is an empty one, not an unread one."""
    p = os.path.join(_folder(base), "HQ", line, "thread.jsonl")
    out, bad = [], 0
    try:
        with open(p, encoding="utf8", errors="replace") as f:
            for l in f:
                if not l.strip():
                    continue
                try:
                    d = json.loads(l)
                except ValueError:
                    bad += 1
                    continue
                if isinstance(d, dict) and d.get("from") == "me" and d.get("text"):
                    out.append({"n": d.get("id") or f"{d.get('at')}", "words": str(d["text"]).strip(), "agent": THREADS[line],
                                "at": d.get("at")})
    except FileNotFoundError:
        pass
    except OSError as e:
        return [], 0, f"it can't be opened ({e.strerror or type(e).__name__})"
    return out, bad, ""


def thread_lines(line: str, base=None) -> list[dict]:
    """His lines of a text thread: {"n" (the line's id), "words", "agent", "at"}."""
    return read_thread(line, base)[0]


def clear_kind(words: str) -> str | None:
    """The kind of mistake a line of his plainly is, or None."""
    for kind in ("say-yes", "stop-asking", "correction"):
        if CLEAR[kind].search(words):
            return kind
    return None


def _where_call(p: str, base=None) -> str:
    return os.path.relpath(os.path.realpath(p), os.path.realpath(_folder(base)))


def _key(where: str, n) -> str:
    """One line of his, one ledger line, whoever tags it and however often."""
    return hashlib.sha256(f"{where}#{n}".encode()).hexdigest()[:16]


def _scan_lines(lines, where, base=None) -> list[dict]:
    got = []
    for l in lines:
        kind = clear_kind(l["words"])
        if kind:
            d = add(kind, l["agent"], l["words"], where=where, key=_key(where, l["n"]), at=l["at"], base=base)
            if d:
                got.append(d)
    return got


def scan_call(p: str, base=None) -> list[dict]:
    return _scan_lines(call_lines(p, base), _where_call(p, base), base)


def scan_thread(line: str, since: float = 0, base=None) -> list[dict]:
    return _scan_lines([l for l in thread_lines(line, base) if float(l["at"] or 0) > since], f"HQ/{line}", base)


def _state_file() -> str:
    return os.environ.get("HQ_MISTAKES_SCAN") or os.path.join(hqpaths.HQ, ".status", "mistakes-scan.json")


def _load_state() -> dict:
    try:
        st = json.load(open(_state_file()))
        return st if isinstance(st, dict) else {}
    except (OSError, ValueError):
        return {}


OPEN_DAYS = 1  # F97: a transcript without its Ended line is read again each pass this long after its last change (a call still going)


def _call_names(base=None) -> tuple[str, list[str]]:
    calls = os.path.join(_folder(base), "HQ", "calls")
    try:
        return calls, sorted(n for n in os.listdir(calls) if n.endswith(".md"))
    except OSError:
        return calls, []


def sweep(all_of_it: bool = False, base=None) -> list[dict]:
    """What's new in the transcripts and the threads since the last pass (on the main, from the routine's minute): the program's
    part for what reached the main without a wrap-up here, a call's from the backup and every text.

    F97: every transcript it hasn't read yet, by name, not only the names after the newest it saw, so one that reaches the main late
    with an older name is read too. One that can't be read is kept as not read, with why, and tried again the next pass; a call
    still going (no Ended line) is read again until it ends. The threads go by the ids of his lines, not their times."""
    st = _load_state()
    now = time.time()
    calls, names = _call_names(base)
    read_ = dict(st.get("read") or {})
    if "read" not in st and st.get("calls"):  # a state from before F97: what the old pass had passed counts as read
        read_ = {n: now for n in names if n <= st["calls"]}
    seen = {k: set(v) for k, v in (st.get("thread_ids") or {}).items()}
    first = not st and not all_of_it
    lines = {line: read_thread(line, base) for line in THREADS}
    if first:  # the first pass starts now; what came before is `scan --all`, once
        read_ = {n: now for n in names}
        seen = {line: {l["n"] for l in got[0]} for line, got in lines.items()}
    elif not st.get("thread_ids") and st.get("threads"):
        seen = {line: {l["n"] for l in got[0] if float(l["at"] or 0) <= float(st["threads"])} for line, got in lines.items()}
    unread = {} if all_of_it else dict(st.get("unread") or {})
    got = []
    for n in names:
        if n in read_ and not all_of_it:
            continue
        p = os.path.join(calls, n)
        his, why, ended = read_call(p, base)
        if his is None:
            was = unread.get(n) or {}
            unread[n] = {"why": why, "tries": int(was.get("tries") or 0) + 1, "first": was.get("first") or round(now), "last": round(now)}
            continue
        unread.pop(n, None)
        got += _scan_lines(his, _where_call(p, base), base)
        try:
            still = not ended and now - os.path.getmtime(p) < OPEN_DAYS * 86400
        except OSError:
            still = False
        if still:
            read_.pop(n, None)
        else:
            read_[n] = round(now)
    for n in list(unread):
        if n not in names:  # gone from the folder: nothing left to read
            unread.pop(n)
    texts = {}
    for line, (his, bad, why) in lines.items():
        new = his if all_of_it else [l for l in his if l["n"] not in seen.get(line, set())]
        got += _scan_lines(new, f"HQ/{line}", base)
        if not why:
            seen[line] = {l["n"] for l in his}  # what's still in the thread; older ids fell off it
        texts[line] = {"bad": bad, "why": why}
    if base is None:
        try:
            os.makedirs(os.path.dirname(_state_file()), exist_ok=True)
            tmp = hqlock.tmp(_state_file())
            with open(tmp, "w") as f:
                json.dump({"calls": max(names) if names else st.get("calls", ""), "threads": now, "read": read_, "unread": unread,
                           "thread_ids": {k: sorted(v) for k, v in seen.items()}, "texts": texts}, f)
            os.replace(tmp, _state_file())
        except OSError:
            pass
    return got


def reading(since: float | None = None, until: float | None = None, base=None) -> dict:
    """F97: what the ledger's pass has read, so a score that couldn't read a call or a text never reads as zero: the calls of the
    period (by the day in their name) read, not read (with why, tried again each pass) and not looked at yet; his texts of the period
    read and not looked at yet, the threads or lines that couldn't be read. From the pass's own state and the folder, no model."""
    st = _load_state()
    read_, unread = st.get("read") or {}, st.get("unread") or {}
    if "read" not in st and st.get("calls"):  # a state from before F97
        read_ = {n: 0 for n in _call_names(base)[1] if n <= st["calls"]}

    def inside(name: str) -> bool:
        m = re.match(r"(\d{4}-\d\d-\d\d)-(\d\d)(\d\d)", name)
        if not m:
            return True
        try:
            t = time.mktime(time.strptime(f"{m.group(1)} {m.group(2)}:{m.group(3)}", "%Y-%m-%d %H:%M"))
        except ValueError:
            return True
        return (since is None or t >= since) and (until is None or t < until)

    names = [n for n in _call_names(base)[1] if inside(n)]
    out = {"calls_read": sum(1 for n in names if n in read_), "calls_not_read": sorted(n for n in names if n in unread),
           "calls_waiting": sum(1 for n in names if n not in read_ and n not in unread), "texts_read": 0, "texts_waiting": 0,
           "texts_not_read": 0, "threads_not_read": [], "passed": bool(st)}
    out["why"] = {n: unread[n].get("why", "") for n in out["calls_not_read"]}
    seen = st.get("thread_ids") or {}
    texts = st.get("texts") or {}
    for line in THREADS:
        his, bad, why = read_thread(line, base)
        if why or (texts.get(line) or {}).get("why"):
            out["threads_not_read"].append(line)
            continue
        out["texts_not_read"] += bad
        for l in his:
            if (since is None or float(l["at"] or 0) >= since) and (until is None or float(l["at"] or 0) < until):
                out["texts_read" if l["n"] in set(seen.get(line) or ()) else "texts_waiting"] += 1
    return out


def reading_words(r: dict) -> str:
    """The pass's reading in one line, for the score."""
    if not r.get("passed"):
        return "The pass over the calls and texts hasn't run here yet, so nothing below is counted from them."
    calls = f"{r['calls_read']} call{'' if r['calls_read'] == 1 else 's'}"
    texts = f"{r['texts_read']} of his text{'' if r['texts_read'] == 1 else 's'}"
    out = f"Read {calls} and {texts}"
    no = len(r["calls_not_read"]) + r["texts_not_read"] + len(r["threads_not_read"])
    if no:
        bits = ([f"{len(r['calls_not_read'])} call{'' if len(r['calls_not_read']) == 1 else 's'} ("
                 + "; ".join(f"{n}: {r['why'].get(n) or 'not read'}" for n in r["calls_not_read"][:5]) + ")"] if r["calls_not_read"] else [])
        bits += [f"{r['texts_not_read']} line{'' if r['texts_not_read'] == 1 else 's'} in the text threads"] if r["texts_not_read"] else []
        bits += [f"the thread {t}" for t in r["threads_not_read"]]
        out += f"; couldn't read {', '.join(bits)}, tried again each pass"
    else:
        out += "; none it couldn't read"
    wait = r["calls_waiting"] + r["texts_waiting"]
    if wait:
        out += f"; {r['calls_waiting']} call{'' if r['calls_waiting'] == 1 else 's'} and {r['texts_waiting']} text{'' if r['texts_waiting'] == 1 else 's'} not looked at yet"
    return out + "."


def looks_file() -> str:
    """F97: what each second look really cost, one line per look, the way routine/review.py keeps .status/reviews.jsonl."""
    return os.environ.get("HQ_MISTAKES_LOOKS") or os.path.join(hqpaths.HQ, ".status", "mistakes-looks.jsonl")


def _keep_look(what: str, t0: float, cost, why: str = "") -> None:
    line = {"at": round(time.time(), 3), "what": what, "model": LOOK_MODEL, "cost": cost, "s": round(time.time() - t0, 1),
            **({"failed": True, "why": why[:200]} if why else {})}
    try:
        os.makedirs(os.path.dirname(looks_file()), exist_ok=True)
        with hqlock.locked(looks_file()):
            with open(looks_file(), "a", encoding="utf8") as f:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"(the looks' cost: {e!r})", file=sys.stderr)


def looks(since: float | None = None, until: float | None = None) -> dict:
    """F97: the second looks of a period: how many, how many failed, what they cost in all (a look with no cost known counted apart)."""
    out = {"looks": 0, "failed": 0, "cost": 0.0, "unknown": 0}
    try:
        with open(looks_file(), encoding="utf8") as f:
            for l in f:
                try:
                    d = json.loads(l)
                except ValueError:
                    continue
                if not isinstance(d, dict) or (since is not None and d.get("at", 0) < since) or (until is not None and d.get("at", 0) >= until):
                    continue
                out["looks"] += 1
                out["failed"] += bool(d.get("failed"))
                if isinstance(d.get("cost"), (int, float)):
                    out["cost"] += d["cost"]
                else:
                    out["unknown"] += 1
    except OSError:
        pass
    out["cost"] = round(out["cost"], 4)
    return out


def looks_words(x: dict) -> str:
    if not x["looks"]:
        return "The second looks: none in this period, so they cost nothing."
    return (f"The second looks: {x['looks']}, ${x['cost']:.4f} in all" + (f" ({x['failed']} failed)" if x["failed"] else "")
            + (f"; {x['unknown']} with no cost known" if x["unknown"] else "") + ".")


def ask(system: str, text: str, what: str = "") -> str:
    """One small look: haiku, no tools, nothing of the folder's. Raises when it fails. what: kept as a line of its own in looks_file(),
    with what it cost (F97), also when it failed."""
    import subprocess
    t0, cost = time.time(), None
    try:
        p = subprocess.run([hqpaths.tool("claude", "/opt/homebrew/bin/claude"), "-p", "--model", LOOK_MODEL, "--output-format", "json", "--tools", "",
                            "--strict-mcp-config", "--setting-sources", "", "--max-budget-usd", str(LOOK_BUDGET), "--no-session-persistence",
                            "--system-prompt", system],
                           input=text, capture_output=True, text=True, timeout=LOOK_TIMEOUT)
        d = json.loads(p.stdout)
        cost = d.get("total_cost_usd") if isinstance(d, dict) else None
        if d.get("is_error"):
            raise RuntimeError(f"the model said no: {str(d.get('result') or d.get('subtype'))[:120]}")
    except Exception as e:
        if what:
            _keep_look(what, t0, cost, str(e) or repr(e))
        raise
    if what:
        _keep_look(what, t0, cost)
    return d.get("result") or ""


def _ask_model(words: str, before: str) -> str:
    return ask(LOOK_SYSTEM, (f"Said just before it:\n{before}\n\n" if before else "") + f"What he said:\n{words}", what="second look")


def second_look(words: str, before: str = "") -> tuple[bool, str]:
    """F103: is he correcting the agent here? (yes, why not). No tools, one word back. HQ_MISTAKES_FAKE stands in for Claude in the flows
    (yes, no, or anything else for a look that failed), and a test never asks the real model. Never raises."""
    fake = os.environ.get("HQ_MISTAKES_FAKE") if hqpaths.under_test() else None
    try:
        if fake is None and hqpaths.under_test():
            raise RuntimeError("a test without a stand-in")
        answer = (fake if fake is not None else _ask_model(words, before)).strip().lower()
    except Exception as e:
        return False, f"the second look failed: {e!r}"
    if answer.startswith("yes"):
        return True, ""
    return False, "the second look says it isn't a correction" if answer.startswith("no") else f"the second look failed: it said {answer[:60]!r}"


def _left_out(words: str, where: str, why: str) -> None:
    """What a model tagged and the second look left out, with why, so it can be read back."""
    try:
        p = os.path.join(hqpaths.HQ, "scratch", "mistakes-left-out.log")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} · {where} · {why} · {' '.join(str(words).split())[:WORDS_KEPT]}\n")
    except OSError as e:
        print(f"(the left-out log: {e!r})", file=sys.stderr)


def _just_before(p: str, n: int) -> str:
    """The lines of a transcript just before line n, for the second look."""
    try:
        lines = open(p, encoding="utf8", errors="replace").read().splitlines()
    except OSError:
        return ""
    return "\n".join(l for l in lines[max(0, n - 4):n - 1] if l.strip())[-1500:]


def tag(said: str, *, call: str = "", line: str = "", handoff: str = "", item: str = "", label: str = "", base=None) -> tuple[dict | None, str]:
    """A correction tagged by a model: (the line, what went wrong). The quote must stand in one of his own lines of that call or
    thread; the agent comes from there. A line the clear phrases don't catch gets the second look first. None and "" means it was
    already on the ledger; a hand-off or an item given for a line that's there lands on that line."""
    quote = _bare(said)
    if len(quote.split()) < QUOTE_LEAST:
        return None, f"Refused: a quote of at least {QUOTE_LEAST} of his own words."
    if handoff and not ONE_HANDOFF.match(handoff):
        return None, "Refused: a hand-off is written like \"Pepper to Moneypenny\"."
    if bool(call) == bool(line):
        return None, "Refused: name the call (--call HQ/calls/NAME.md) or the text line (--line direct-line)."
    if call:
        folder = _folder(base)
        p = call if os.path.isabs(call) else os.path.join(folder, call)
        where = _where_call(p, base)
        if not re.fullmatch(r"HQ/calls/[^/]+\.md", where.replace(os.sep, "/")):
            return None, "Refused: not a call's transcript."
        his = call_lines(p, base)
    else:
        if line not in THREADS:
            return None, "Refused: not one of the text lines."
        where = f"HQ/{line}"
        his = thread_lines(line, base)
    hit = next((l for l in reversed(his) if quote in _bare(l["words"])), None)
    if not hit:
        return None, "Refused: those words aren't his in that call or line. Nothing written."
    kind = clear_kind(hit["words"])
    key = _key(where, hit["n"])
    if not kind and not any(d.get("key") == key for d in read(base)):
        yes, why = second_look(hit["words"], _just_before(p, hit["n"]) if call else "")
        if not yes:
            _left_out(hit["words"], where, why)
            return None, f"Left out: {why}. Nothing written."
    d = add(kind or "correction", hit["agent"], hit["words"], where=where, key=key, handoff=handoff, item=item, label=label,
            by="the wrap-up" if call else "the agent", at=hit["at"], base=base)
    return d, ""


# -- the score ------------------------------------------------------------------------------------------------------

def tally(rows: list[dict]) -> dict:
    agents: dict = {}
    hands: dict = {}
    for d in rows:
        for box, name in ((agents, d.get("agent") or "unknown"), (hands, d.get("handoff") or "not said")):
            e = box.setdefault(name, {"total": 0, "kinds": {}})
            e["total"] += 1
            e["kinds"][d["kind"]] = e["kinds"].get(d["kind"], 0) + 1
    return {"lines": len(rows), "agents": agents, "handoffs": hands}


def counts(names, since: float, until: float, base=None) -> dict:
    """One agent's lines in a period, per kind (routine/pokes.py); names: her id and her name, lower case. QA's and the build's
    lines stand under their own names."""
    out: dict = {}
    for d in read(base, since, until):
        if d.get("agent") in names:
            out[d["kind"]] = out.get(d["kind"], 0) + 1
    return out


def _kinds(e: dict) -> str:
    return ", ".join(f"{k} {n}" for k, n in sorted(e["kinds"].items()))


def score_words(t: dict, days: float) -> str:
    out = [f"The score over the last {days:g} days, from the ledger: {t['lines']} line{'' if t['lines'] == 1 else 's'}."]
    for title, box in (("Per agent:", t["agents"]), ("Per hand-off:", t["handoffs"])):
        out.append(title)
        out += [f"- {name}: {e['total']} ({_kinds(e)})" for name, e in sorted(box.items(), key=lambda x: (-x[1]["total"], x[0]))] or ["- nothing"]
    return "\n".join(out)


def _opt(args: list[str], name: str) -> str:
    if name in args:
        i = args.index(name)
        v = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
        return v
    return ""


def main(argv: list[str]) -> int:
    args = list(argv)
    cmd = args.pop(0) if args else ""
    if cmd == "add" and args:
        kind = args.pop(0)
        if kind == "correction":
            call, line, said, hand_, it = (_opt(args, x) for x in ("--call", "--line", "--said", "--handoff", "--item"))
            item, label = "", ""
            if it:
                import trail
                item, label = trail.resolve(it) or "", (it.upper() if not trail.ID.match(it) else trail.label_of(it) or "")
            d, no = tag(said, call=call, line=line, handoff=hand_, item=item, label=label)
            if no:
                print(no)
                return 2
            print("Already on the ledger." if not d else f"On the ledger: {d['kind']}, {d['agent']}.")
            return 0
        if kind == "bug-after-qa" and len(args) >= 2:
            import qa
            label, what = args[0].upper(), " ".join(args[1:])
            no = qa.bug_after_qa(label, what)
            print(no or f"On the ledger against {label}'s QA.")
            return 2 if no else 0
        print("Only a correction or a bug found after QA goes in by hand; the rest is the program's.")
        return 2
    if cmd == "scan":
        call = _opt(args, "--call")
        got = scan_call(call) if call else sweep("--all" in args)
        print(f"{len(got)} new on the ledger.")
        return 0
    if cmd == "list":
        days, who = _opt(args, "--days"), _opt(args, "--agent").lower()
        since = time.time() - float(days) * 86400 if days else None
        for d in read(None, since):
            if not who or d.get("agent") == who:
                print(f"- {time.strftime('%Y-%m-%d %H:%M', time.localtime(d['at']))} · {d['agent']} · {d['kind']} · {d['handoff']} · {d['words'][:200]}"
                      + (f" · {d['where']}" if d.get("where") else ""))
        return 0
    if cmd == "score":
        days = float(_opt(args, "--days") or 7)
        since = time.time() - days * 86400
        t = tally(read(None, since))
        t["reading"], t["looks"] = reading(since), looks(since)  # F97: what it read and couldn't, and what the second looks cost
        print(json.dumps(t, indent=1, ensure_ascii=False) if "--json" in args else
              score_words(t, days) + "\n" + reading_words(t["reading"]) + "\n" + looks_words(t["looks"]))
        return 0
    if cmd == "put" and args:
        d = json.loads(args[0])
        if not isinstance(d, dict) or d.get("kind") not in KINDS or not d.get("key"):
            print("Refused: not a line of the ledger.", file=sys.stderr)
            return 2
        print("written" if _append(d) else "already there")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
