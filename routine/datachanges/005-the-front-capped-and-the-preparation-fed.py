"""The front capped and the preparation fed (11 November 2026, by hand in the laptop chat, his words: "Ok so cap the front solution and
move weight to the back solution and then instead of 2: we do improve MP solution as you just described"): the two new backend switches,
front_cap and fed_prep, are on by default. A fresh install has them from the template; an HQ that updates gets them once, but only when its
file is exactly one HQ wrote itself (the template's file at the stable version, or the one change 003 made); anything else may hold a
switch turned off by hand, and is left alone. Its undo takes back only what it added, unless a switch was turned since."""
import json
import os

WHAT = "The front capped and the preparation fed are on by default: two review rounds an item, and a prep job that starts with the item, his words and the real case, in one chat."
FILE = "HQ/backend.json"
ADD = ["front_cap", "fed_prep"]
STABLE = ["briefing", "open_line", "headless_jobs", "one_way_sync", "planning_index", "handover"]
MARK_003 = "HQ: on by default at the stable version (H301)"
MARK = "HQ: the front capped and the preparation fed, on by default (11 November 2026)"


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


def _hqs_own(d):
    """The file as HQ itself wrote it: the template's six at the stable version, or change 003's (its five plus what was on before)."""
    on = d.get("on")
    if not isinstance(on, list) or any(k in on for k in ADD):
        return False
    if d == {"on": STABLE}:
        return True
    return d.get("set_by") == MARK_003 and set(d) <= {"on", "set_by", "was"}


def do(folder):
    p = folder / FILE
    d = _read(p)
    if d is None or not _hqs_own(d):
        return  # no file, one that can't be read, or one that may hold her own choices: left alone
    new = dict(d)
    new["on"] = list(d["on"]) + ADD
    new["set_by_005"] = MARK
    new["was_005"] = p.read_text(encoding="utf8")
    _write(p, json.dumps(new, indent=2) + "\n")


def undo(folder):
    p = folder / FILE
    d = _read(p)
    if not d or d.get("set_by_005") != MARK or not isinstance(d.get("was_005"), str):
        return  # not the file this made
    try:
        before = json.loads(d["was_005"]).get("on") or []
    except (ValueError, AttributeError):
        return
    if sorted(d.get("on") or []) != sorted(set(before) | set(ADD)):
        return  # a switch turned since is the person's: left as it is
    _write(p, d["was_005"])
