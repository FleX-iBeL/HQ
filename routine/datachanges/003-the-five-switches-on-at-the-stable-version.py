"""H301: at the stable version the five backend switches (the briefing, the open line, headless jobs, one-way sync, the planning index) are on
by default. A fresh install has them from the template; an HQ that updates gets them once, but only when its file is exactly one HQ wrote
itself and nobody could have changed by hand: the template's file just before the stable version (the briefing, headless jobs and the
hand-over), or the file change 002 makes (the briefing, with its set_by). When in doubt, the file is left alone: anything else could be a
switch turned off by hand (the earlier templates' files are also what a later one looks like with a switch turned off), and keeps its
switches. With two HQs this runs on the main, and the file reaches the backup the way every synced file does. Its undo puts back the file
as it was, unless a switch was turned since."""
import json
import os

WHAT = "The five backend switches are on by default: an HQ whose switches are still the ones HQ gave it gets the open line, one-way sync and the planning index too."
FILE = "HQ/backend.json"
ADD = ["briefing", "open_line", "headless_jobs", "one_way_sync", "planning_index"]  # the five
ORDER = ["briefing", "open_line", "headless_jobs", "one_way_sync", "planning_index", "handover"]
# The files HQ itself wrote that no hand change can give: the template's from F115 until the stable version, and change 002's.
HQS_OWN = [{"on": ["briefing", "headless_jobs", "handover"]},
           {"on": ["briefing"], "set_by": "HQ: this workspace had no switches yet"}]
MARK = "HQ: on by default at the stable version (H301)"  # tells this file from one of hers, so the undo takes back only its own


def _read(p):
    try:
        d = json.loads(p.read_text(encoding="utf8"))
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def _write(p, text):
    tmp = p.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf8")
    os.replace(tmp, p)


def do(folder):
    p = folder / FILE
    d = _read(p)
    if d is None:
        return  # no file, or one that can't be read: not HQ's to guess at
    if d not in HQS_OWN:
        return  # could be the person's own choices: left alone
    new = {"on": [k for k in ORDER if k in set(d["on"]) | set(ADD)], "set_by": MARK, "was": p.read_text(encoding="utf8")}
    _write(p, json.dumps(new, indent=2) + "\n")


def undo(folder):
    p = folder / FILE
    d = _read(p)
    if not d or d.get("set_by") != MARK or not isinstance(d.get("was"), str):
        return  # not the file this made
    try:
        before = json.loads(d["was"]).get("on") or []
    except (ValueError, AttributeError):
        return
    if sorted(d.get("on") or []) != sorted(set(before) | set(ADD)):
        return  # a switch turned since is the person's: left as it is
    _write(p, d["was"])
