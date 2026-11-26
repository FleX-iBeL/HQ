"""His own lines: only what he himself said or typed, never an agent's line, a summary or the log.

    hislines.his_lines(ws)  [(where, the line without punctuation)]: his lines in the newest call transcripts, his side of the text
                            threads, his quick notes

app/about_self.py reads these so an agent never keeps one of his lines as a fact about herself. Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

def _bare(t):
    """A line or a quote without punctuation or case, so a dictated comma doesn't decide what he said."""
    return " ".join(re.sub(r"[^\w\s]", " ", _norm(t), flags=re.UNICODE).split())


HIS_CALLS = 120  # the newest transcripts looked through for his own words; Claude's choice, about a month of calls
HIS_THREADS = ("direct-line", "coaching-line", "team-line")
MARKS = re.compile(r"(?:\s*\*\([^)]*\)\*)+\s*$")  # a transcript's *(typed)* and *(cut in)*: HQ's, not his words

def _ws():
    """The workspace (the roadmap sits in its HQ folder)."""
    import hqpaths
    return os.environ.get("HQ_SPRINT_FOLDER") or os.path.dirname(os.path.dirname(os.path.realpath(hqpaths.ROADMAP)))

def _norm(t):
    t = t.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    return " ".join(t.lower().split())

def his_lines(ws=None):
    """Only what he himself said or typed, as (where, the line without punctuation): his lines in the call
    transcripts, his side of the text threads, his quick notes. Never an agent's line, a summary or the log."""
    ws = ws or _ws()
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "app"))
    import me as _me
    from pathlib import Path as _P
    name = _me.load(_P(ws))["name"] or "Me"
    mark = re.compile(rf"^- [0-9:]+ \*\*{re.escape(name)}:\*\*\s*(.*)$")
    out = []
    calls = os.path.join(ws, "HQ", "calls")
    try:
        names = sorted(n for n in os.listdir(calls) if n.endswith(".md"))[-HIS_CALLS:]
    except OSError:
        names = []
    for nm in names:
        try:
            for line in open(os.path.join(calls, nm), encoding="utf8", errors="replace"):
                m = mark.match(line)
                if m:
                    out.append((f"HQ/calls/{nm}", _bare(MARKS.sub("", m.group(1)))))
        except OSError:
            pass
    for line_name in HIS_THREADS:
        try:
            for line in open(os.path.join(ws, "HQ", line_name, "thread.jsonl"), encoding="utf8", errors="replace"):
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if isinstance(d, dict) and d.get("from") == "me" and d.get("text"):
                    out.append((f"HQ/{line_name}", _bare(str(d["text"]))))
        except OSError:
            pass
    for rel in ("HQ/notes.md", "HQ/notes-cleared.md"):
        try:
            for line in open(os.path.join(ws, rel), encoding="utf8", errors="replace"):
                if line.startswith("- "):
                    out.append((rel, _bare(line)))
        except OSError:
            pass
    return out
