"""H301: at the stable version the five backend switches (the briefing, the open line, headless jobs, one-way sync, the planning index) are on
by default. A fresh install has them from the template; an HQ that updates gets the ones it doesn't have yet once, when its file is still
one HQ wrote: one of the template's files from before (headless jobs; the briefing and headless jobs; those and the hand-over) or the file
change 002 makes (the briefing). Any other file holds the person's own choices (a switch turned on or off by hand) and is left exactly as it
is; one set by hand to exactly one of HQ's old files can't be told apart, and gets the five too. With two HQs this runs on the main, and the
file reaches the backup the way every synced file does. Its undo puts back the file as it was, unless a switch was turned since."""
import json
import os

WHAT = "The five backend switches are on by default: an HQ that never set its own gets the open line, one-way sync and the planning index too."
FILE = "HQ/backend.json"
ADD = ["briefing", "open_line", "headless_jobs", "one_way_sync", "planning_index"]  # the five
ORDER = ["briefing", "open_line", "headless_jobs", "one_way_sync", "planning_index", "handover"]
# What HQ itself wrote before, untouched: the template's file until the stable version, and the file change 002 makes.
HQS_OWN = [["headless_jobs"], ["briefing", "headless_jobs"], ["briefing", "headless_jobs", "handover"], ["briefing"]]
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
    now = d.get("on")
    if not isinstance(now, list) or sorted(now) not in [sorted(x) for x in HQS_OWN]:
        return  # the person's own choices
    if d.get("set_by") not in (None, "HQ: this workspace had no switches yet") or set(d) - {"on", "set_by"}:
        return  # something else in the file that HQ didn't write
    new = {"on": [k for k in ORDER if k in set(now) | set(ADD)], "set_by": MARK, "was": p.read_text(encoding="utf8")}
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
