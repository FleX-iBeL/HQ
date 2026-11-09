#!/usr/bin/env python3
"""F215 (8 November 2026): his clear go for the sprint is his day yes for the sprint's ready builds that day.

Found by the laptop chat: after his "FIX THIS MESS SO I CAN HAVE MY WEEKEND" (12:0x) six ready sprint builds were refused for the day
from 14:2x and waited until 22:00. His words on the call that evening: "yes put them also on this list."

The wall (wall.py) lets no build start between 8:00 and 22:00 without his stored say-so. Here, read by the routine's minute: his own
lines of today (what he typed in a laptop chat, his side of the text threads, his lines on a call), the newest that tells the team to
work now (fix it, go, build it, get it done) counts as his day yes for every build the line sent from the sprint, kept on the job with
his words and where they stand. A line that isn't about building doesn't, and a newer line of his that holds the work back (stop, wait,
not now) takes it back. When nothing counts, the refusal names the line of his it read and why it didn't count.

    python3 routine/daygo.py      what the minute would read now: his go for the day, or the line it read and why not
"""
from __future__ import annotations

import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# A line telling the team to work: a word to fix, build, start or finish it, or a go. Whole words, so "goal" or "building's plan" isn't one.
_GO = re.compile(r"(?<![\w'])(?:"
                 r"fix(?:es)?\s+(?:this|it|that|them|these|those|the|everything|all|my|our)|"
                 r"build\s+(?:it|them|this|that|these|those|the|everything|all)|get\s+(?:it|them|this|that|these|those|everything)\s+"
                 r"(?:done|built|fixed|going|running)|get\s+(?:to\s+)?work|"
                 r"go\s+ahead|go\s+for\s+it|let'?s\s+go|let'?s\s+(?:build|fix|run|do)\s+|just\s+go|go\s+go|"
                 r"start\s+(?:it|them|building|the\s+builds?|working|the\s+sprint)|run\s+(?:it|them|the\s+builds?|the\s+sprint)|"
                 r"work\s+(?:the|on\s+the)\s+sprint|do\s+(?:it|them|the\s+sprint)|ship\s+it|make\s+it\s+work"
                 r")(?![\w'])", re.I)
_GO_ALONE = re.compile(r"\s*(?:go|go!+|build|fix it|do it)\s*[.!]*\s*", re.I)
# Words that take the work back: a newer line like this undoes the go.
_STOP = re.compile(r"(?<![\w'])(?:stop|hold (?:on|off|it)|wait|pause|not now|don'?t (?:build|start|fix|run)|leave it|later)(?![\w'])", re.I)

WHERE_CHAT = "his laptop chat"


def _ws():
    import sprint
    return sprint._ws()


def _day_start(now=None):
    t = time.localtime(now)
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1))


def his_lines_today(ws=None, now=None) -> list:
    """His own lines of today, oldest first: {"where" (in his words: his laptop chat, his text on the team line, the call of HH:MM),
    "at" (seconds), "line"}. Never an agent's line, a job's prompt or a quick note."""
    import sprint
    ws = ws or _ws()
    start = _day_start(now)
    out = []
    try:
        for text, at in sprint.laptop_chat_turns(ws, since=start):
            if at >= start:
                out.append({"where": WHERE_CHAT, "at": at, "line": " ".join(text.split())})
    except Exception:
        pass
    try:
        for where, rows in sprint._spoken(ws):
            if where.startswith("HQ/notes"):
                continue  # a quick note can be added from a call: not his own line
            name = (f"his text on the {where[3:].replace('-', ' ')}" if not where.startswith("HQ/calls/")
                    else "his words on the call " + os.path.basename(where)[:-3])
            for r in rows:
                if r["who"] == "he" and (r.get("at") or 0) >= start:
                    out.append({"where": name, "at": float(r["at"]), "line": " ".join(str(r["text"]).split())})
    except Exception:
        pass
    return sorted(out, key=lambda x: x["at"])


def reading(line) -> str:
    """"" when the line is his go for the sprint, else why not, in plain words."""
    low = " ".join(str(line).lower().replace("’", "'").split())
    if _STOP.search(low):
        return "it holds the work back"
    go = bool(_GO.search(low) or _GO_ALONE.fullmatch(low))
    if not go:
        if low.rstrip().endswith("?") or re.match(r"(?:which|what|why|how|when|where|who|is|are|can|could|do|does|did)\b", low):
            return "it's a question, not a word to the team to fix, build or go"
        return "it isn't about building: no word in it tells the team to fix, build or go"
    if "?" in low:
        return "it asks, it doesn't tell the team to go"
    return ""


def day_go(ws=None, now=None) -> dict:
    """{"go": {"where", "at", "line"} or None, "read": the line of his it read (the go, or the newest of today), "why": why it didn't count}."""
    lines = his_lines_today(ws, now)
    if not lines:
        return {"go": None, "read": None, "why": "there is no line of his from today"}
    newest = lines[-1]
    for i in range(len(lines) - 1, -1, -1):
        why = reading(lines[i]["line"])
        if why == "it holds the work back":
            return {"go": None, "read": lines[i], "why": why}
        if not why:
            return {"go": lines[i], "read": lines[i], "why": ""}
    return {"go": None, "read": newest, "why": reading(newest["line"])}


def sprint_build(job) -> bool:
    """A build the line sent from the sprint (line.SENT in its text): the ones his sprint go is for."""
    import line as L
    return bool(L.sent_label(job.get("text") or ""))


def sayso_of(g) -> dict:
    """The day yes kept on the job, as jobs.sayso keeps one: who (where his words stand), when, his words."""
    import jobs as q
    at = time.strftime("%H:%M", time.localtime(g["at"])) if g.get("at") else ""
    return {"at": time.strftime("%Y-%m-%d %H:%M"), "who": q.clean_mark(f"his go for the sprint in {g['where']}" + (f" at {at}" if at else "")).replace("·", "-"),
            "words": q.clean_mark(g["line"][:300])}


def refused_words(d) -> str:
    """Why his lines of today don't open the day for the sprint, naming the line it read."""
    r = d.get("read")
    if not r:
        return f"{d.get('why') or 'there is no line of his from today'} that tells the team to work the sprint"
    at = time.strftime("%H:%M", time.localtime(r["at"])) if r.get("at") else ""
    line = r["line"] if len(r["line"]) <= 160 else r["line"][:157] + "..."
    return f"his line \"{line}\" ({r['where']}{', ' + at if at else ''}) doesn't count as his go for the sprint: {d['why']}"


_CACHE = {}


def cached(now=None) -> dict:
    """day_go once a minute: the minute asks it for each waiting build."""
    key = int((now or time.time()) // 60)
    if _CACHE.get("key") != key:
        _CACHE.update(key=key, d=day_go(now=now))
    return _CACHE["d"]


if __name__ == "__main__":
    d = day_go()
    print(f"His go for the sprint today: {d['go']['line']!r} ({d['go']['where']})" if d["go"] else "No go for the sprint today: " + refused_words(d))
