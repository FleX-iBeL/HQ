#!/usr/bin/env python3
"""F86: who wrote while a round ran. Comparing afterwards can't tell a person from a session, so the doors say so themselves.

While a round of the fix-and-review loop runs, every write to the planning and to the sprint file through HQ's own doors (jobs.py, schedule.py, handover.py,
review.py reword, sprint.py, and so the status page and the calls, which go through those scripts) leaves one short line in the round's journal:
.status/rounds/job-N.journal.jsonl: what (a row, a job, an item, a Ready mark, a verdict), which door, when. It's written where the file is written, from what
really changes, so no door can be left out by forgetting a word. The round's own session carries HQ_ROUND, so its own writes leave no line. review.round_after
reads the journal: what stands in it stays as it is.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_ROW = re.compile(r"^\| [^|]* \| ([A-Z]\d+(?:\.\d+)*)\b")


def folder() -> str:
    """Where a round's files are: beside the estimates, the same place estimate.DIR works out."""
    if os.environ.get("HQ_ESTIMATES"):
        base = os.environ["HQ_ESTIMATES"]
    elif os.environ.get("HQ_ROADMAP"):
        base = os.path.splitext(os.environ["HQ_ROADMAP"])[0] + "-estimates"
    else:
        base = os.path.join(os.path.dirname(HERE), ".status")
    return os.path.join(base, "rounds")


def running() -> list[str]:
    """The rounds whose look hasn't come yet."""
    try:
        return [x[:-5] for x in os.listdir(folder()) if re.fullmatch(r"job-\d+\.json", x)]
    except OSError:
        return []


def keyed_rows(text: str) -> dict:
    """The labelled rows of the planning's phases, in order: {(label, which): line}. A label can stand in two tables."""
    out, seen, phase = {}, {}, False
    for line in text.split("\n"):
        if line.startswith("## "):
            phase = line.startswith("## Phase")
        elif phase:
            m = _ROW.match(line)
            if m:
                k = seen.get(m.group(1), 0)
                seen[m.group(1)] = k + 1
                out[(m.group(1), k)] = line
    return out


def queue(text: str) -> dict:
    """{"jobs": {n: line}, "items": {n: line}} as a planning's text has them."""
    return {"jobs": {int(m.group(1)): m.group(0) for m in re.finditer(r"^- Job (\d+) · .*$", text, re.M)},
            "items": {int(m.group(1)): m.group(0) for m in re.finditer(r"^- Item (\d+) · .*$", text, re.M)}}


def note(whats) -> None:
    """Lines in the journal of every round running. Never in a round's own session, and it never stops a write."""
    names = running() if not os.environ.get("HQ_ROUND") else []
    whats = sorted(set(whats))
    if not names or not whats:
        return
    door = " ".join([os.path.basename(sys.argv[0] or "")] + sys.argv[1:2]).strip()
    for name in names:
        try:
            with open(os.path.join(folder(), f"{name}.journal.jsonl"), "a", encoding="utf8") as f:
                for w in whats:
                    f.write(json.dumps({"at": round(time.time(), 1), "what": w, "door": door}) + "\n")
        except OSError:
            pass


def planning(path: str, new: str) -> None:
    """A door is about to write the planning: what changes, in the journal."""
    if os.environ.get("HQ_ROUND") or not running():
        return
    try:
        old = open(path, encoding="utf8").read()
    except OSError:
        old = ""
    a, b = keyed_rows(old), keyed_rows(new)
    what = [f"row {k[0]}" for k in set(a) | set(b) if a.get(k) != b.get(k)]
    qa, qb = queue(old), queue(new)
    for kind, name in (("jobs", "job"), ("items", "item")):
        what += [f"{name} {n}" for n in set(qa[kind]) | set(qb[kind]) if qa[kind].get(n) != qb[kind].get(n)]
    note(what)


def sprint(path: str, new: dict) -> None:
    """A door is about to write the sprint file: Ready marks and verdicts that change, in the journal."""
    if os.environ.get("HQ_ROUND") or not running():
        return
    try:
        old = json.load(open(path, encoding="utf8"))
    except (OSError, ValueError):
        old = {}
    ra, rb = old.get("ready") or {}, new.get("ready") or {}
    va, vb = (old.get("review") or {}).get("rows") or {}, (new.get("review") or {}).get("rows") or {}
    note([f"ready {k}" for k in set(ra) | set(rb) if ra.get(k) != rb.get(k)]
         + [f"verdict {k}" for k in set(va) | set(vb) if (va.get(k) or {}).get("verdict") != (vb.get(k) or {}).get("verdict")])


def read(name: str) -> dict:
    """{what: door} for one round."""
    out = {}
    try:
        for line in open(os.path.join(folder(), f"{name}.journal.jsonl"), encoding="utf8"):
            r = json.loads(line)
            out[r["what"]] = r["door"]
    except (OSError, ValueError):
        pass
    return out
