"""The small list: a workspace from before the template had HQ/backend.json has every backend switch off, so its calls start with the files
whole, over the size a call's start is held to (F106). It gets the briefing switch, the one a fresh install starts with that keeps the start
small. Nothing else is turned on, and a workspace that has the file is left as it is."""
import json
import os

WHAT = "A workspace without backend switches gets the briefing on, so a call starts small, as on a fresh install."
FILE = "HQ/backend.json"
MADE = {"on": ["briefing"], "set_by": "HQ: this workspace had no switches yet"}  # the note tells this file from one of hers


def do(folder):
    p = folder / FILE
    if p.exists():
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(MADE, indent=2) + "\n", encoding="utf8")
    os.replace(tmp, p)


def undo(folder):
    p = folder / FILE
    try:
        if json.loads(p.read_text(encoding="utf8")) == MADE:  # only the file this made, untouched since; a switch turned since is hers
            p.unlink()
    except (OSError, ValueError):
        pass
