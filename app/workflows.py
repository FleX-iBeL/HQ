"""H202: workflows a user turns on (17 October 2026).

A workflow is guidance HQ ships for the whole of something bigger, which the user's agent walks them
through on a call, one question at a time, writing their answers into a file in their own workspace.
The first one is the map: from the life they want three to five years out down to next week. In HQ it's the
Life coaching switch (job 257, the user's words on the call of 17 October 2026: "Maybe we could call it like if
someone wants a life coaching module turned on", "If not, they will only do the short-term things, but if you want
it integrated and embedded, then... You can have a couple of life coaching sessions", "And then in there, people can
name it themselves"): on, a few sessions (the layers) build their long-term vision into HQ; off, only the short-term
things. During the sessions they name their own vision; the name sits on the vision's `Name:` line in their file
and the call rule uses it from then on.

Each lives in HQ's `workflows/<id>/`, the same for everyone and with nothing personal in it:
    workflow.json   id, name, what (one line), agent (who walks them through it), file (theirs, in the
                    workspace), guide (the agent's guide), blank (their file as it starts), start (how they
                    start it on a call), where (its line in where-things-go.md), on and off (what the switch
                    does each way, for Settings)
    guide.md        the guide the agent follows
    blank.md        their file, as it is before anything is filled in

Which ones are on is the workspace's: `HQ/workflows.json` there, {"on": ["map"]}. Turning one on copies
its blank file into the workspace when there's none yet (an existing one is never touched) and adds its
line to where-things-go.md. The call rules (config.py) name the ones that are on.

    python3 app/workflows.py              the workflows and which are on
    python3 app/workflows.py on map       turn one on
    python3 app/workflows.py off map      turn one off (their file stays)
    python3 app/workflows.py rule         the call rule for the ones that are on
    python3 app/workflows.py checklist map [N]   the blank checklist of every layer (or layer N), all open
    python3 app/workflows.py check map [N]       their file's checklist held against the guide, line by line

The checklist (H224, 21 October 2026, the user's words on the call after questions had been skipped in every
layer: "Does this mean you also screw up like this for other people that use HQ?" and "do give it to the team so
they need to make this more of a checklist thing and have it checked out"): every question of every layer of the
guide has its own line in their file, under its layer, marked answered, parked (why, and when it comes back),
later (on purpose, and when) or open:
    - open · 5 · <the question, short>
    - parked · 23 · <the question> · why: <why> · back: <when it comes back>
    - later · 14 · <the question> · when: <when>
    - answered · 1 · <the question>
The keys are the guide's own numbers, per group: the questions as 1, 2, …; the vision's checks as check 1, …;
looking back's as day 1, week 1, game 1 and check-in 1. `check` says per layer what's missing, still open or
without its why or when, and whether the Status line says done while it can't be yet.
"""
from __future__ import annotations

import json
import os
import re
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


NOT_NAMED = ("not named yet", "not yet", "")


def own_name(folder: Path, w: dict) -> str:
    """What they call their vision: the first `Name:` line in their file, empty while it isn't named yet."""
    try:
        text = (folder / w["file"]).read_text(encoding="utf8")
    except OSError:
        return ""
    for line in text.splitlines():
        if line.startswith("Name:"):
            name = line[5:].split("(", 1)[0].split("[", 1)[0].strip().strip('"\u201c\u201d').strip()
            return "" if name.lower().rstrip(".") in NOT_NAMED else name[:80]
    return ""


def listing(folder: Path, base: Path = SHIPPED) -> list[dict]:
    """For Settings: each workflow, whether it's on, and what on and off do."""
    on = turned_on(folder)
    return [{"id": w["id"], "name": w["name"], "on": w["id"] in on, "what": w["what"],
             "when_on": w.get("on", ""), "when_off": w.get("off", ""), "start": w["start"]} for w in shipped(base)]


# H224: the checklist. The guide's layers are its "## N. Name" headings; within one, a bold lead starts a group.
GROUPS = {"**The questions,**": "", "**Check it with them,**": "check", "**Each day,**": "day", "**Each week,**": "week",
          "**After every game,**": "game", "**Every three to six months,**": "check-in"}
MARKS = ("answered", "parked", "later", "open")
LINE = re.compile(r"^- (answered|parked|later|open) · ((?:check-in|check|day|week|game) )?(\d+) · (.*)$")


def _layers(text: str) -> list[tuple[int, str, str]]:
    """(number, heading, body) for each "## N. Name" in a guide or a map."""
    heads = [(m.start(), int(m.group(1)), m.group(2).strip()) for m in re.finditer(r"^## (\d+)\. (.+)$", text, re.M)]
    out = []
    for i, (at, n, name) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        body = text[at:end]
        cut = re.search(r"^## (?!\d+\.)", body[3:], re.M)  # a later "## In short" ends the last layer
        out.append((n, name, body[:cut.start() + 3] if cut else body))
    return out


def _short(q: str) -> str:
    """The question, short: up to its first question mark (or its first sentence), at most about ninety letters."""
    q = re.sub(r"\s+", " ", re.sub(r"\*\*|\(.*?\)", "", q)).replace(" ?", "?").replace(" ,", ",").replace(" .", ".").strip()
    m = re.search(r"\?|\.(\s|$)", q)
    first = q[:m.start() + 1] if m else q
    return first if len(first) <= 90 else first[:87].rsplit(" ", 1)[0].rstrip(",:;") + "…"


def questions(w: dict) -> dict[int, list[tuple[str, str]]]:
    """Every question of every layer in the guide, as (key, short text): the checklist's lines."""
    text = (w["dir"] / w["guide"]).read_text(encoding="utf8")
    out = {}
    for n, _name, body in _layers(text):
        group, items = None, []
        for line in body.splitlines():
            lead = next((g for g in GROUPS if line.startswith(g)), None)
            if lead:
                group = GROUPS[lead]
                continue
            if line.startswith("**"):
                group = None
                continue
            if group is None:
                continue
            m = re.match(r"^(\d+)\. (.+)", line)
            if m and group != "check":
                items.append(((group + " " if group else "") + m.group(1), _short(m.group(2))))
            elif group == "check" and line.startswith("- "):
                items.append((f"check {sum(1 for k, _ in items if k.startswith('check ')) + 1}", _short(line[2:])))
        out[n] = items
    return out


def checklist_lines(w: dict, layer: int) -> list[str]:
    return [f"- open · {k} · {q}" for k, q in questions(w).get(layer, [])]


CHECKLIST_HEAD = "Checklist (every question of this layer: answered, parked with why and when it comes back, later with when, or open):"


def check(folder: Path, w: dict, only: int | None = None) -> list[dict]:
    """Their file's checklist held against the guide, layer by layer."""
    try:
        text = (folder / w["file"]).read_text(encoding="utf8")
    except OSError:
        text = ""
    mine = {n: body for n, _name, body in _layers(text)}
    out = []
    for n, items in questions(w).items():
        if only is not None and n != only:
            continue
        body = mine.get(n, "")
        marks = {}
        for line in body.splitlines():
            m = LINE.match(line.strip())
            if m:
                marks[(m.group(2) or "") + m.group(3)] = (m.group(1), m.group(4))
        keys = [k for k, _ in items]
        status = next((l[7:].strip() for l in body.splitlines() if l.startswith("Status:")), "")
        r = {"layer": n, "name": next((nm for x, nm, _b in _layers(text) if x == n), ""), "status": status,
             "total": len(keys), "missing": [k for k in keys if k not in marks],
             "unknown": [k for k in marks if k not in keys],
             "counts": {mk: sum(1 for k in keys if marks.get(k, ("",))[0] == mk) for mk in MARKS},
             "open": [k for k in keys if marks.get(k, ("",))[0] == "open"],
             "no_why": [k for k in keys if marks.get(k, ("",))[0] == "parked"
                        and not ("why:" in marks[k][1] and "back:" in marks[k][1])],
             "no_when": [k for k in keys if marks.get(k, ("",))[0] == "later" and "when:" not in marks[k][1]]}
        r["can_close"] = not (r["missing"] or r["open"] or r["no_why"] or r["no_when"])
        r["says_done"] = status.lower().startswith("done")
        r["ok"] = r["can_close"] or not r["says_done"]
        out.append(r)
    return out


def check_words(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        c = r["counts"]
        head = (f"{r['layer']}. {r['name'] or '(not in their file)'}: {c['answered']} answered, {c['parked']} parked, "
                f"{c['later']} later, {c['open']} open, of {r['total']}. Status: {(r['status'] or 'none').rstrip('.')}.")
        bits = []
        if r["missing"]:
            bits.append("not in their checklist: " + ", ".join(r["missing"]))
        if r["open"]:
            bits.append("still open: " + ", ".join(r["open"]))
        if r["no_why"]:
            bits.append("parked without why or back: " + ", ".join(r["no_why"]))
        if r["no_when"]:
            bits.append("later without when: " + ", ".join(r["no_when"]))
        if r["unknown"]:
            bits.append("not in the guide: " + ", ".join(r["unknown"]))
        if r["says_done"] and not r["can_close"]:
            bits.append("its Status says done, but it can't be yet")
        elif r["can_close"] and not r["says_done"]:
            bits.append("every line is through: it can be closed once its result is read back and they say yes")
        lines.append(head + (" " + "; ".join(bits) + "." if bits else ""))
    return "\n".join(lines)


def rule(folder: Path, base: Path = SHIPPED) -> str:
    """The call rule for the workflows that are on; empty when none is."""
    ws = active(folder, base)
    if not ws:
        return ""
    parts = []
    for w in ws:
        named = own_name(folder, w)
        parts.append(f"{w['name']} ({w['what']} Their file: {w['file']} in the workspace; the guide: "
                     f"{w['dir'] / w['guide']}; started with something like \"{w['start']}\"; best with "
                     f"{w['agent'].capitalize()}"
                     + (f". They call their vision \"{named}\": use that name for it, not \"the vision\""
                        if named else ". They haven't named their vision yet; the guide says when to ask") + ")")
    return ("- Workflows they turned on (H202): " + "; ".join(parts) + ". When they want to go through one, read "
            "its guide and their file first, say where they are in it, and go through it the guide's way: one "
            "question per turn, sparring, their answers written into their file as you go, in their words. "
            "Never say where the questions come from. The checklist (H224): every question of every layer has its own "
            "line in their file's checklist under that layer, marked answered, parked (with why and when it comes back), "
            "later (on purpose, with when) or open; tick each line as you go, never skip one silently (one answered "
            "earlier is ticked answered, not asked again), and never call a layer done before holding it against the "
            f"guide line by line (python3 {ROOT / 'app' / 'workflows.py'} check <id> <layer>) and saying plainly what's "
            "still open.")


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
    if argv[0] in ("checklist", "check") and len(argv) in (2, 3):
        w = find(argv[1])
        if not w:
            print(f"No workflow {argv[1]}.")
            return 2
        only = int(argv[2]) if len(argv) == 3 and argv[2].isdigit() else None
        if argv[0] == "checklist":
            for n in questions(w):
                if only is None or n == only:
                    print(f"Layer {n}:\n{CHECKLIST_HEAD}\n" + "\n".join(checklist_lines(w, n)) + "\n")
            return 0
        print(check_words(check(folder, w, only)))
        return 0
    if argv[0] == "rule":
        print(rule(folder) or "No workflow is on.")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
