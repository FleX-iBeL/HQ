#!/usr/bin/env python3
"""The ledger per agent (H298, piece 5, 29 October 2026): `HQ/ledger/<agent>.md` in the workspace, one per agent.

The handbook: "each cycle's plan, each step (what, from which source, what happened, its measured minutes, turns and
cost, done, boxed or stale), each tripwire, each decision taken alone, each escalation, and her weekly score." Written
by the routine (the runner, routine/cycles.py) and by her own runs through this script; read first by her next bigger
session, and by the Friday screen. Plain Markdown, dated sections newest last, so a person can read it; the cycle
plan sits in a JSON block inside its section, so the runner can read it back. Orders he gives her on a call or in a
text ("start x", "stop y", "from now on") stand under "## Orders" at the top, each with its state.

    python3 routine/ledger.py AGENT                      her ledger (the last sections)
    python3 routine/ledger.py AGENT note "TEXT"           a line under the newest section (a decision, what happened)
    python3 routine/ledger.py AGENT entry "TITLE" ["LINE" …]   a dated section with its lines
    python3 routine/ledger.py AGENT orders               the open orders
    python3 routine/ledger.py AGENT plan                 the newest cycle plan (JSON)
    python3 routine/ledger.py AGENT scores               the weekly scores written so far
Standard library only.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hqpaths  # noqa: E402

REL = "HQ/ledger"
FMT = "%Y-%m-%d %H:%M"
ORDERS_HEAD = "## Orders"
ORDER_KINDS = ("start", "stop", "standing")
ORDER_STATES = ("open", "now", "planned", "done", "dropped")
KEEP_SECTIONS = 400  # dated sections kept in the file; older ones go to <agent>-archive.md
_ORDER = re.compile(r"^- (\d{4}-\d\d-\d\d \d\d:\d\d) · (start|stop|standing) · \"(.*)\" · (open|now|planned|done|dropped)(?: · (.*))?$")
_SECTION = re.compile(r"^## (.+)$", re.M)
_DATED = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d) · (.*)$")


def folder() -> Path:
    return Path(os.environ.get("HQ_LEDGER_FOLDER") or os.path.join(hqpaths.FOLDER, REL))


def path(agent_id: str) -> Path:
    return folder() / f"{agent_id}.md"


def _name(agent_id: str) -> str:
    try:
        sys.path.insert(0, str(HERE.parent / "app"))
        import agents
        a = next((x for x in agents.load(Path(hqpaths.FOLDER)) if x["id"] == agent_id), None)
        return a["name"] if a else agent_id.capitalize()
    except Exception:
        return agent_id.capitalize()


def head(agent_id: str) -> str:
    name = _name(agent_id)
    return (f"# {name}'s ledger\n\n> **Private.** Only for this workspace. What {name}'s own cycles did (H298): each "
            "cycle's plan, each step and what came of it, each tripwire, each decision taken alone, each escalation, "
            "and her weekly score; written by HQ's routine and by her own runs, read first by her next bigger session. "
            "Orders given to her on a call or in a text stand on top with their state.\n\n"
            f"{ORDERS_HEAD}\n\n")


def ensure(agent_id: str) -> Path:
    p = path(agent_id)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(head(agent_id), encoding="utf8")
    return p


def text(agent_id: str) -> str:
    try:
        return path(agent_id).read_text(encoding="utf8")
    except OSError:
        return ""


def _write(agent_id: str, t: str) -> None:
    p = ensure(agent_id)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(t, encoding="utf8")
    os.replace(tmp, p)


def sections(agent_id: str) -> list[dict]:
    """[{"title", "at" (datetime or None), "what", "body", "start", "end"}] in file order, the Orders section first."""
    t = text(agent_id)
    heads = list(_SECTION.finditer(t))
    out = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(t)
        title = h.group(1).strip()
        m = _DATED.match(title)
        at = None
        if m:
            try:
                at = dt.datetime.strptime(m.group(1), FMT)
            except ValueError:
                at = None
        out.append({"title": title, "at": at, "what": m.group(2) if m else title, "body": t[h.end():end].strip("\n"),
                    "start": h.start(), "end": end})
    return out


def _tidy(agent_id: str) -> None:
    """Older dated sections past KEEP_SECTIONS move to the archive next to the ledger, oldest first."""
    secs = [s for s in sections(agent_id) if s["at"]]
    if len(secs) <= KEEP_SECTIONS:
        return
    t = text(agent_id)
    old = secs[:len(secs) - KEEP_SECTIONS]
    moved = "".join(f"## {s['title']}\n{s['body']}\n\n" for s in old)
    arch = path(agent_id).with_name(f"{agent_id}-archive.md")
    with open(arch, "a", encoding="utf8") as f:
        f.write(moved)
    for s in reversed(old):
        t = t[:s["start"]] + t[s["end"]:]
    _write(agent_id, t)


def entry(agent_id: str, what: str, lines: list[str] | None = None, now: dt.datetime | None = None,
          block: dict | None = None) -> str:
    """A dated section at the end: "## 2026-10-29 08:30 · what", its lines, and a JSON block when given."""
    now = now or dt.datetime.now()
    title = f"{now:%Y-%m-%d %H:%M} · {' '.join(str(what).split())}"
    body = "".join(f"- {' '.join(str(l).split())}\n" for l in (lines or []) if str(l).strip())
    if block is not None:
        body += "\n```json\n" + json.dumps(block, indent=1, ensure_ascii=False) + "\n```\n"
    t = (text(agent_id) or head(agent_id)).rstrip("\n") + "\n\n"
    t += f"## {title}\n\n{body}" if body else f"## {title}\n"
    _write(agent_id, t)
    _tidy(agent_id)
    return title


def note(agent_id: str, line: str) -> None:
    """One line under the newest dated section (a decision, what happened, a let-go)."""
    t = text(agent_id) or head(agent_id)
    secs = [s for s in sections(agent_id) if s["at"]]
    line = "- " + " ".join(str(line).split())
    if not secs:
        entry(agent_id, "notes", [line[2:]])
        return
    last = secs[-1]
    body = t[last["start"]:last["end"]].rstrip("\n")
    t = t[:last["start"]] + body + "\n" + line + "\n" + t[last["end"]:].lstrip("\n").join(["", ""]) \
        if False else t[:last["start"]] + body + "\n" + line + "\n\n" + t[last["end"]:].lstrip("\n")
    _write(agent_id, t)


# -- orders --------------------------------------------------------------------------------------------------------

def orders(agent_id: str, states: tuple = ORDER_STATES) -> list[dict]:
    """The orders under "## Orders": [{"n", "at", "kind", "words", "state", "note"}], in file order (n is 1-based)."""
    secs = sections(agent_id)
    sec = next((s for s in secs if s["title"] == ORDERS_HEAD[3:]), None)
    if not sec:
        return []
    out, n = [], 0
    for l in sec["body"].splitlines():
        m = _ORDER.match(l)
        if m:
            n += 1
            if m.group(4) in states:
                out.append({"n": n, "at": m.group(1), "kind": m.group(2), "words": m.group(3), "state": m.group(4),
                            "note": m.group(5) or ""})
    return out


def _order_line(o: dict) -> str:
    return f"- {o['at']} · {o['kind']} · \"{o['words']}\" · {o['state']}" + (f" · {o['note']}" if o.get("note") else "")


def add_order(agent_id: str, kind: str, words: str, now_: bool = False, when: dt.datetime | None = None) -> dict:
    """An order from a call or a text, in his words. start: for her next bigger session (or now: a small step at
    once); stop: her matching steps cancelled, on her let-go list; standing: into her own section of the handbook."""
    if kind not in ORDER_KINDS:
        raise ValueError(f"an order is one of {', '.join(ORDER_KINDS)}")
    words = " ".join(str(words).replace('"', "'").split())
    if not words:
        raise ValueError("an order needs his words")
    when = when or dt.datetime.now()
    o = {"at": when.strftime(FMT), "kind": kind, "words": words, "state": "now" if (now_ and kind == "start") else "open", "note": ""}
    t = text(agent_id) or head(agent_id)
    i = t.find(ORDERS_HEAD + "\n")
    if i < 0:
        t = t.rstrip("\n") + f"\n\n{ORDERS_HEAD}\n\n"
        i = t.find(ORDERS_HEAD + "\n")
    j = t.find("\n## ", i + len(ORDERS_HEAD))
    j = len(t) if j < 0 else j
    block = t[i:j].rstrip("\n") + "\n" + _order_line(o) + "\n\n"
    t = t[:i] + block + t[j:].lstrip("\n")
    _write(agent_id, t)
    o["n"] = len(orders(agent_id))
    return o


def set_order(agent_id: str, n: int, state: str, note_: str = "") -> bool:
    if state not in ORDER_STATES:
        raise ValueError(f"a state is one of {', '.join(ORDER_STATES)}")
    t = text(agent_id)
    sec = next((s for s in sections(agent_id) if s["title"] == ORDERS_HEAD[3:]), None)
    if not sec:
        return False
    lines = t[sec["start"]:sec["end"]].split("\n")
    k = 0
    for i, l in enumerate(lines):
        m = _ORDER.match(l)
        if m:
            k += 1
            if k == n:
                o = {"at": m.group(1), "kind": m.group(2), "words": m.group(3), "state": state,
                     "note": " ".join(str(note_).split()) or (m.group(5) or "")}
                lines[i] = _order_line(o)
                _write(agent_id, t[:sec["start"]] + "\n".join(lines) + t[sec["end"]:])
                return True
    return False


# -- the plan, the runs, the score -----------------------------------------------------------------------------

def blocks(agent_id: str, what: str | None = None) -> list[tuple[dict, dict]]:
    """[(section, block)] for every dated section with a JSON block (the newest last); `what` keeps only the
    sections whose heading says it (cycle plan, score)."""
    out = []
    for s in sections(agent_id):
        if not s["at"] or (what and what not in s["what"]):
            continue
        m = re.search(r"```json\n(.*?)\n```", s["body"], re.S)
        if not m:
            continue
        try:
            out.append((s, json.loads(m.group(1))))
        except ValueError:
            continue
    return out


def plan(agent_id: str) -> tuple[dict | None, dict | None]:
    """The newest cycle plan: (section, plan), or (None, None)."""
    got = blocks(agent_id, "cycle plan")
    return got[-1] if got else (None, None)


def write_plan(agent_id: str, p: dict, job: int | None = None, now: dt.datetime | None = None) -> str:
    """The bigger session's plan: the few things, the let-go, the steps, each in a line, and the plan as JSON."""
    lines = []
    for x in p.get("picks") or []:
        lines.append(f"pick: {x.get('what', x) if isinstance(x, dict) else x}" + (f" · source: {x['source']}" if isinstance(x, dict) and x.get("source") else ""))
    for x in p.get("let_go") or []:
        lines.append(f"let go: {x}")
    for i, st in enumerate(p.get("steps") or [], 1):
        lines.append(f"step {i}: {st.get('goal', '')} · at {st.get('at', '?')} · done means: {st.get('done_means', '')}"
                     + (f" · inputs: {', '.join(_input_words(x) for x in st.get('inputs') or [])}" if st.get("inputs") else ""))
    for x in p.get("questions") or []:
        lines.append(f"question for him: {x}")
    return entry(agent_id, f"cycle plan{f' (job {job})' if job else ''}", lines, now, block=p)


def _input_words(x) -> str:
    if isinstance(x, dict):
        return f"{x.get('kind', '?')} {x.get('label') or x.get('words') or x.get('path') or ''}".strip()
    return str(x)


def scores(agent_id: str) -> list[tuple[dict, dict]]:
    return blocks(agent_id, "score")


def write_score(agent_id: str, week: str, items: dict, lines: list[str], now: dt.datetime | None = None) -> str:
    return entry(agent_id, f"score, week {week}", lines, now, block={"week": week, **items})


def recent(agent_id: str, days: float = 7, now: dt.datetime | None = None) -> list[dict]:
    """The dated sections of the last `days` days, oldest first."""
    now = now or dt.datetime.now()
    since = now - dt.timedelta(days=days)
    return [s for s in sections(agent_id) if s["at"] and s["at"] >= since]


def words(agent_id: str, last: int = 12) -> str:
    secs = sections(agent_id)
    if not secs:
        return f"{_name(agent_id)} has no ledger yet (it starts with her first cycle)."
    keep = [secs[0]] + [s for s in secs if s["at"]][-last:]
    return "\n\n".join(f"## {s['title']}\n{s['body']}" for s in keep).strip()


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    aid, rest = argv[0].strip().lower(), argv[1:]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,30}", aid):
        print("Which agent? Her id (donna, pepper, moneypenny).")
        return 2
    if not rest or rest[0] in ("show", "list"):
        print(words(aid))
        return 0
    cmd = rest[0]
    if cmd == "note" and len(rest) == 2:
        note(aid, rest[1])
        print(f"Noted in {_name(aid)}'s ledger.")
        return 0
    if cmd == "entry" and len(rest) >= 2:
        t = entry(aid, rest[1], rest[2:])
        print(f"Written: {t}")
        return 0
    if cmd == "orders":
        os_ = orders(aid, ("open", "now", "planned"))
        print("\n".join(f"{o['n']}. {o['kind']} · \"{o['words']}\" · {o['state']} ({o['at']})" for o in os_) or "No open orders.")
        return 0
    if cmd == "plan":
        s, p = plan(aid)
        print(json.dumps(p, indent=1, ensure_ascii=False) if p else "No cycle plan yet.")
        return 0
    if cmd == "scores":
        got = scores(aid)
        print("\n".join(f"{s['title']}: {json.dumps(b, ensure_ascii=False)}" for s, b in got) or "No score yet.")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
