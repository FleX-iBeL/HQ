#!/usr/bin/env python3
"""The planning board, read only: the open rows of the roadmap's phase tables, with their rank and MoSCoW tag.

Moneypenny's space shows the planning to look at, not to edit. An open row is a table row marked ⬜ in a
`## Phase …` section, except Phase P (parked) and rows that repeat (🔁). Each row's place and tag come from the
workspace's HQ/sprint.json (`order`: the ranked labels, top first; `moscow`: {label: must|should|could|wont}).
Next to the open rows the board carries the rows that repeat (🔁) and the finished ones (✅), per phase, newest phase
first, to look at too. Nothing is written anywhere.

    python3 routine/planning_board.py           the board as JSON
    python3 routine/planning_board.py --words   one line per row, grouped

HQ_ROADMAP and HQ_SPRINT name a test's own copies. Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hqpaths

MOSCOW = ("must", "should", "could", "wont")
GROUPS = ("must", "should", "could", None, "wont")  # the order the groups are shown in
GROUP_NAMES = {"must": "Must", "should": "Should", "could": "Could", "wont": "Won't this time", None: "Not sorted yet"}
LABEL = re.compile(r"[A-Z]\d+(\.\d+)*")


def roadmap_path() -> str:
    return os.environ.get("HQ_ROADMAP") or hqpaths.ROADMAP


def sprint_path() -> str:
    return os.environ.get("HQ_SPRINT") or os.path.join(os.path.dirname(roadmap_path()), "sprint.json")


def open_rows(text: str) -> list[dict]:
    """The open rows in the roadmap's order: [{"label", "title", "phase", "phase_title"}]."""
    out, phase = [], ""
    for line in text.split("\n"):
        if line.startswith("## "):
            phase = line
            continue
        if not phase.startswith("## Phase ") or phase.startswith("## Phase P ") or not line.startswith("|"):
            continue
        cells = hqpaths.cells(line)
        if len(cells) < 2 or cells[0] != "⬜":
            continue
        head = cells[1].split(" ", 1)
        if not LABEL.fullmatch(head[0]):
            continue
        out.append({"label": head[0], "title": head[1].strip() if len(head) > 1 else head[0],
                    "phase": phase[9:].split(" ·", 1)[0], "phase_title": phase[9:].strip(),
                    "bug": _is_bug(head[0], phase[9:].strip(), line)})
    return out


def other_rows(text: str) -> tuple[list[dict], list[dict]]:
    """The rows that repeat, and the finished ones grouped per phase: ([{"label", "title", "phase_title"}],
    [{"phase", "phase_title", "rows": [{"label", "title"}]}]). Phase P is left out of both."""
    repeat, done, phase, group = [], [], "", None
    for line in text.split("\n"):
        if line.startswith("## "):
            phase, group = line, None
            continue
        if not phase.startswith("## Phase ") or phase.startswith("## Phase P ") or not line.startswith("|"):
            continue
        cells = hqpaths.cells(line)
        if len(cells) < 2 or cells[0] not in ("🔁", "✅"):
            continue
        head = cells[1].split(" ", 1)
        if not LABEL.fullmatch(head[0]):
            continue
        row = {"label": head[0], "title": head[1].strip() if len(head) > 1 else head[0]}
        if cells[0] == "🔁":
            repeat.append(dict(row, phase_title=phase[9:].strip()))
            continue
        if group is None:
            group = {"phase": phase[9:].split(" ·", 1)[0], "phase_title": phase[9:].strip(), "rows": []}
            done.append(group)
        group["rows"].append(row)
    return repeat, list(reversed(done))


def _is_bug(label: str, phase_title: str, line: str) -> bool:
    """A row in the Bugs phase (F, or a phase called Bugs), any F row, or a row sent in as a bug."""
    return (phase_title.split(" ", 1)[0] == "F" or "bug" in phase_title.lower() or label.startswith("F")
            or "| A bug from " in line)


def _sprint() -> dict:
    try:
        d = json.load(open(sprint_path(), encoding="utf8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def board(text: str | None = None) -> dict:
    """{"rows": [...], "groups": [{"tag", "name", "labels"}], "count"}: each row with its rank (1 is first, None when
    it has none) and its MoSCoW tag (None when it has none), sorted the way the planning shows them."""
    if text is None:
        try:
            text = open(roadmap_path(), encoding="utf8").read()
        except OSError:
            return {"rows": [], "groups": [], "count": 0, "error": "The planning can't be read"}
    rows = open_rows(text)
    have = {r["label"] for r in rows}
    s = _sprint()
    order = [l for l in (s.get("order") or []) if l in have]
    rank = {l: i + 1 for i, l in enumerate(order)}
    tags = {l: t for l, t in (s.get("moscow") or {}).items() if l in have and t in MOSCOW}
    place = {r["label"]: i for i, r in enumerate(rows)}
    for r in rows:
        r["rank"] = rank.get(r["label"])
        r["moscow"] = tags.get(r["label"])
    rows.sort(key=lambda x: (GROUPS.index(x["moscow"]), not x["bug"], x["rank"] is None, x["rank"] or 0, place[x["label"]]))
    groups = [{"tag": g, "name": GROUP_NAMES[g], "labels": [r["label"] for r in rows if r["moscow"] == g]} for g in GROUPS]
    repeat, done = other_rows(text)
    return {"rows": rows, "groups": [g for g in groups if g["labels"]], "count": len(rows),
            "repeating": repeat, "finished": done, "finished_count": sum(len(g["rows"]) for g in done)}


def words(b: dict) -> str:
    out = []
    by = {r["label"]: r for r in b["rows"]}
    for g in b["groups"]:
        out.append(f"{g['name']}:")
        for l in g["labels"]:
            r = by[l]
            rank = f" · rank {r['rank']}" if r["rank"] else ""
            out.append(f"  {l}{' (bug)' if r['bug'] else ''}{rank} · {r['title'][:120]}")
    return "\n".join(out) or "Nothing open on the planning."


if __name__ == "__main__":
    b = board()
    print(words(b) if "--words" in sys.argv[1:] else json.dumps(b, ensure_ascii=False))
