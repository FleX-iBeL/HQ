#!/usr/bin/env python3
"""Hand-overs, read only: the notes prepared for building HQ by hand, in the workspace's HQ/prep/ folder.

Each hand-over is one Markdown file there. Its title is its first `# ` heading (else the file's name), its date the
YYYY-MM-DD the name starts with (else the file's own time). Nothing is written.

    python3 routine/handovers.py           the list as JSON, newest first
    python3 routine/handovers.py NAME      one file's text

HQ_PREP names a test's own folder. Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hqpaths

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,160}\.md$")
DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})")
MOST_BYTES = 2_000_000


def folder() -> str:
    return os.environ.get("HQ_PREP") or os.path.join(hqpaths.DATA, "prep")


def _title(path: str, name: str) -> str:
    try:
        with open(path, encoding="utf8", errors="replace") as f:
            for _ in range(40):
                line = f.readline()
                if not line:
                    break
                if line.startswith("# "):
                    return line[2:].strip()
    except OSError:
        pass
    return name[:-3]


def listing() -> list[dict]:
    """[{"name", "title", "date", "modified", "bytes"}], newest first (by date, then by the file's time)."""
    try:
        names = os.listdir(folder())
    except OSError:
        return []
    out = []
    for n in names:
        p = os.path.join(folder(), n)
        if not NAME.match(n) or not os.path.isfile(p):
            continue
        st = os.stat(p)
        m = DATED.match(n)
        out.append({"name": n, "title": _title(p, n), "date": m.group(1) if m else time.strftime("%Y-%m-%d", time.localtime(st.st_mtime)),
                     "modified": st.st_mtime, "bytes": st.st_size})
    return sorted(out, key=lambda x: (x["date"], x["modified"]), reverse=True)


def read(name: str) -> dict | None:
    """{"name", "title", "date", "text"} of one hand-over, or None when there's no such file."""
    if not NAME.match(name or ""):
        return None
    hit = next((x for x in listing() if x["name"] == name), None)
    if not hit:
        return None
    with open(os.path.join(folder(), name), encoding="utf8", errors="replace") as f:
        text = f.read(MOST_BYTES)
    return {**hit, "text": text}


if __name__ == "__main__":
    if sys.argv[1:]:
        got = read(sys.argv[1])
        if got is None:
            sys.exit("No such hand-over.")
        print(got["text"])
    else:
        print(json.dumps(listing(), ensure_ascii=False))
