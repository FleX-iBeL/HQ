"""H202: workflows a user turns on (17 October 2026).

A workflow is guidance HQ ships for the whole of something bigger, which the user's agent walks them
through on a call, one question at a time, writing their answers into a file in their own workspace.
The first one is the map: from the life they want three to five years out down to next week.

Each lives in HQ's `workflows/<id>/`, the same for everyone and with nothing personal in it:
    workflow.json   id, name, what (one line), agent (who walks them through it), file (theirs, in the
                    workspace), guide (the agent's guide), blank (their file as it starts), start (how they
                    start it on a call), where (its line in where-things-go.md)
    guide.md        the guide the agent follows
    blank.md        their file, as it is before anything is filled in

Which ones are on is the workspace's: `HQ/workflows.json` there, {"on": ["map"]}. Turning one on copies
its blank file into the workspace when there's none yet (an existing one is never touched) and adds its
line to where-things-go.md. The call rules (config.py) name the ones that are on.

    python3 app/workflows.py              the workflows and which are on
    python3 app/workflows.py on map       turn one on
    python3 app/workflows.py off map      turn one off (their file stays)
    python3 app/workflows.py rule         the call rule for the ones that are on
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # HQ
SHIPPED = ROOT / "workflows"
STATE = "HQ/workflows.json"  # in the workspace


def _folder() -> Path:
    return Path(os.environ.get("HQ_FOLDER") or os.path.realpath(os.environ.get("HQ_WORKSPACE", str(ROOT / "workspace"))))


def shipped(base: Path = SHIPPED) -> list[dict]:
    """Every workflow HQ ships, by id."""
    out = []
    for f in sorted(base.glob("*/workflow.json")):
        try:
            w = json.loads(f.read_text(encoding="utf8"))
        except (OSError, ValueError):
            continue
        if w.get("id") == f.parent.name and (f.parent / w.get("guide", "guide.md")).exists():
            w["dir"] = f.parent
            out.append(w)
    return out


def find(wid: str, base: Path = SHIPPED) -> dict | None:
    return next((w for w in shipped(base) if w["id"] == wid), None)


def turned_on(folder: Path) -> list[str]:
    try:
        on = json.loads((folder / STATE).read_text(encoding="utf8")).get("on", [])
    except (OSError, ValueError, AttributeError):
        return []
    return [x for x in on if isinstance(x, str)]


def _save(folder: Path, on: list[str]) -> None:
    p = folder / STATE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"on": on}, indent=2) + "\n", encoding="utf8")


def _add_where(folder: Path, w: dict) -> bool:
    """Its line in where-things-go.md's table, above "Something new"; False when it's there or there's no table."""
    p = folder / "where-things-go.md"
    try:
        text = p.read_text(encoding="utf8")
    except OSError:
        return False
    if f"`{w['file']}`" in text:
        return False
    row = f"| {w['where']} | `{w['file']}` (the guide your agent follows: HQ's `workflows/{w['id']}/{w['guide']}`) | on demand |\n"
    lines = text.splitlines(keepends=True)
    at = next((i for i, l in enumerate(lines) if l.startswith("| Something new")), None)
    if at is None:
        return False
    lines.insert(at, row)
    p.write_text("".join(lines), encoding="utf8")
    return True


def turn_on(folder: Path, wid: str, base: Path = SHIPPED) -> str:
    w = find(wid, base)
    if not w:
        return f"No workflow {wid}. There are: {', '.join(x['id'] for x in shipped(base)) or 'none'}."
    said = []
    mine = folder / w["file"]
    if not mine.exists():
        mine.write_text((w["dir"] / w["blank"]).read_text(encoding="utf8"), encoding="utf8")
        said.append(f"{w['file']} started from the blank one")
    else:
        said.append(f"{w['file']} was already there and stays as it is")
    if _add_where(folder, w):
        said.append("its line is in where-things-go.md")
    on = turned_on(folder)
    if wid not in on:
        _save(folder, on + [wid])
    return f"{w['name']} is on: " + "; ".join(said) + f". Start it on a call with \"{w['start']}\"."


def turn_off(folder: Path, wid: str) -> str:
    on = turned_on(folder)
    if wid not in on:
        return f"{wid} wasn't on."
    _save(folder, [x for x in on if x != wid])
    return f"{wid} is off. Their file stays."


def active(folder: Path, base: Path = SHIPPED) -> list[dict]:
    on = turned_on(folder)
    return [w for w in shipped(base) if w["id"] in on]


def rule(folder: Path, base: Path = SHIPPED) -> str:
    """The call rule for the workflows that are on; empty when none is."""
    ws = active(folder, base)
    if not ws:
        return ""
    parts = []
    for w in ws:
        parts.append(f"{w['name']} ({w['what']} Their file: {w['file']} in the workspace; the guide: "
                     f"{w['dir'] / w['guide']}; started with something like \"{w['start']}\"; best with "
                     f"{w['agent'].capitalize()})")
    return ("- Workflows they turned on (H202): " + "; ".join(parts) + ". When they want to go through one, read "
            "its guide and their file first, say where they are in it, and go through it the guide's way: one "
            "question per turn, sparring, their answers written into their file as you go, in their words. "
            "Never say where the questions come from.")


def main(argv: list[str]) -> int:
    folder = _folder()
    if not argv:
        on = turned_on(folder)
        for w in shipped():
            print(f"{w['id']}: {w['name']}, {'on' if w['id'] in on else 'off'}. {w['what']}")
        return 0
    if argv[0] == "on" and len(argv) == 2:
        print(turn_on(folder, argv[1]))
        return 0
    if argv[0] == "off" and len(argv) == 2:
        print(turn_off(folder, argv[1]))
        return 0
    if argv[0] == "rule":
        print(rule(folder) or "No workflow is on.")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
