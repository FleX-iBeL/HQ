"""The planning index (Fable, 27 October 2026; the backend switch `planning_index`).

The planning file (`HQ/roadmap.md`) is over a megabyte, most of it the done rows, and everything read it whole: the
status page every three seconds, every script, the calls and the team; a whole read on a call is what killed the
line (F60). He denied moving the done rows elsewhere (27 October, 17:50), so the file stays one file. What changes
is that nothing has to open it whole: the routine keeps this index, `.status/planning-index.json`, one entry a row
(label, title, state, phase, bug, where the row's line starts and ends in the file), refreshed every minute and
whenever the file is newer than the index, and a row is fetched by its place (`row(label)`), the open rows from
the index (`open_rows()`). The index is only trusted while it's at least as new as the file; else the file is parsed
as before, so a stale index never shows a stale row.

    python3 routine/planning_index.py            write the index (the routine, every minute)
    python3 routine/planning_index.py show       the index's counts
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402

FILE = os.environ.get("HQ_PLANNING_INDEX") or os.path.join(hqpaths.HQ, ".status", "planning-index.json")
_LABEL = re.compile(r"[A-Z]\d+(\.\d+)*")


def _on() -> bool:
    try:
        sys.path.insert(0, os.path.join(hqpaths.HQ, "app"))
        import backend
        return backend.on("planning_index")
    except Exception:
        return False


def build(text: str | None = None) -> dict:
    """The index from the roadmap's text: every table row with a label in a `## Phase` section, with its byte
    offsets (so a row is read back with one seek), plus the status block's end and the queue's place."""
    path = hqpaths.ROADMAP
    if text is None:
        with open(path, encoding="utf8") as f:
            text = f.read()
    data = text.encode("utf8")
    rows, phase, phase_title = [], "", ""
    pos = 0
    for line in text.split("\n"):
        start = pos
        pos += len(line.encode("utf8")) + 1
        if line.startswith("## "):
            phase_title = line[3:].strip()
            phase = phase_title[6:].split(" ·", 1)[0] if phase_title.startswith("Phase ") else ""
            continue
        if not phase or not line.startswith("|"):
            continue
        cells = hqpaths.cells(line)
        if len(cells) < 2:
            continue
        head = cells[1].split(" ", 1)
        if not _LABEL.fullmatch(head[0]):
            continue
        rows.append({"label": head[0], "title": head[1].strip() if len(head) > 1 else "", "state": cells[0],
                     "phase": phase_title, "phase_id": phase, "parked": phase.startswith("P"),
                     "bug": phase.startswith("F") or head[0].startswith("F") or "Bugs" in phase_title,
                     "start": start, "end": start + len(line.encode("utf8")), "n": text[:start].count("\n") + 1})
    queue = text.find("\n## The queue")
    return {"made": time.time(), "file": path, "size": len(data), "mtime": os.path.getmtime(path) if os.path.exists(path) else 0,
            "queue_at": queue if queue >= 0 else None, "rows": rows,
            "counts": {"rows": len(rows), "open": sum(1 for r in rows if r["state"] == "⬜" and not r["parked"]),
                       "done": sum(1 for r in rows if r["state"] == "✅")}}


def write() -> dict | None:
    """Write the index when the file is newer than it (or there is none). Returns the index written, else None."""
    try:
        mtime = os.path.getmtime(hqpaths.ROADMAP)
    except OSError:
        return None
    try:
        with open(FILE, encoding="utf8") as f:
            have = json.load(f)
        if have.get("mtime") == mtime and have.get("file") == hqpaths.ROADMAP:
            return None
    except (OSError, ValueError):
        pass
    idx = build()
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    tmp = FILE + ".tmp"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(idx, f)
    os.replace(tmp, FILE)
    return idx


def read() -> dict | None:
    """The index, only when the switch is on and it's as new as the file; else None (parse the file)."""
    if not _on():
        return None
    try:
        with open(FILE, encoding="utf8") as f:
            idx = json.load(f)
        if idx.get("file") != hqpaths.ROADMAP or idx.get("mtime") != os.path.getmtime(hqpaths.ROADMAP):
            return None
        return idx
    except (OSError, ValueError):
        return None


def line_at(start: int, end: int) -> str:
    with open(hqpaths.ROADMAP, "rb") as f:
        f.seek(start)
        return f.read(end - start).decode("utf8", errors="replace")


def row(label: str) -> dict | None:
    """One row by its label from the index: the same shape as sprint.row_of, or None when the index can't be used
    (then the caller parses the file)."""
    idx = read()
    if idx is None:
        return None
    label = label.strip().upper()
    for r in idx["rows"]:
        if r["label"] == label:
            line = line_at(r["start"], r["end"])
            cells = hqpaths.cells(line)
            return {"label": label, "title": r["title"], "state": r["state"], "phase": r["phase"],
                    "cells": cells[2:], "line": line, "n": r["n"]}
    return {"missing": True}


def open_rows() -> list[dict] | None:
    """The open rows the way sprint.open_rows gives them, from the index; None when it can't be used."""
    idx = read()
    if idx is None:
        return None
    out = []
    for r in idx["rows"]:
        if r["state"] != "⬜" or r["parked"] or not r["phase_id"]:
            continue
        out.append({"label": r["label"], "title": r["title"] or r["label"], "line": line_at(r["start"], r["end"]),
                    "phase": r["phase_id"], "phase_title": r["phase"]})
    return out


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "write":
        idx = write()
        print("Index written: " + json.dumps(idx["counts"]) if idx else "The index is up to date.")
        return 0
    if argv[0] == "show":
        try:
            with open(FILE, encoding="utf8") as f:
                idx = json.load(f)
            print(json.dumps({"made": time.strftime("%H:%M:%S", time.localtime(idx["made"])), **idx["counts"],
                              "size_kb": idx["size"] // 1000, "switch": "on" if _on() else "off"}))
        except (OSError, ValueError):
            print("No index yet.")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
