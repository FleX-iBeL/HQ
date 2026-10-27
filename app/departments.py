"""Departments and projects (Fable, 27 October 2026): the shape that lets the next head plug in.

His words (27 October 2026): "I have this whole AI company that can do things for me. Whether that's a secretary where
I can delegate to, a life coach ... And then also to have a head of development ... in the future, I want to build
other applications through this as well ... When I'm gonna automate marketing work and other things and client
delivery work." The three agents are already departments; what makes them one kind of thing is the record below:
her name and character (agents.json), her context (what her start loads: day, coach, build), the briefing recipe
(which parts the routine puts in her briefing), the lookups she may run, the planning phases she owns, and the
routines that are hers. `record(agent)` gives it; `departments.py` prints them. A workspace adds its own under
"department" in its agents.json entry (any of recipe, phases, lookups, routines) and the rest comes from her
context's defaults.

A project (`projects.json` in the workspace's HQ folder) is a folder with its own planning and team line: this app is
one; a marketing automation or a client's delivery is another later, the same code with a project picked. Nothing
reads projects.json yet beyond this listing: the team's line, the sprint and the status page run on the one project
until the second one exists (what each needs is the `project` line in the record).

    python3 app/departments.py              every department
    python3 app/departments.py show ID      one, in full
    python3 app/departments.py projects     the projects
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agents  # noqa: E402
import config  # noqa: E402

RECIPES = {
    "day": ["calendar", "mail", "commitments", "todo", "nudges", "games", "situation"],
    "coach": ["calendar", "mail", "commitments", "todo", "nudges", "games", "map", "situation"],
    "build": ["planning"],
    "all": ["calendar", "mail", "commitments", "todo", "nudges", "games", "map", "situation", "planning"],
}
LOOKUPS = {
    "day": ["todo.py show", "briefing.py day", "pings.py list", "travel.py link", "the calendar's own commands"],
    "coach": ["briefing.py layer N", "todo.py show", "games.py show", "coaching.py summary", "workflows.py check"],
    "build": ["sprint.py show LABEL", "sprint.py open", "jobs.py list", "jobs.py notes N", "qa.py state LABEL",
              "release.py status", "a section of the build notes with grep -n and sed -n"],
}
PHASES = {"build": ["F", "H", "R", "U"], "coach": ["I"], "day": []}
ROUTINES = {
    "day": ["the hourly mail check", "the reminders and nudges", "the rain and travel texts", "the briefing"],
    "coach": ["the Friday look back", "the check-ins every eight weeks", "the six-week game's texts"],
    "build": ["the nightly run", "the daily release", "the weekly sweep", "the weekly rules check", "the QA step",
              "the ready review on Fridays"],
}
KINDS = {"day": "the secretary", "coach": "the coach", "build": "development", "all": "everything"}


def record(agent: dict) -> dict:
    ctx = agents.context_of(agent)
    own = agent.get("department") if isinstance(agent.get("department"), dict) else {}
    return {
        "id": agent["id"], "name": agent["name"], "kind": own.get("kind") or KINDS.get(ctx, ctx),
        "speciality": agent.get("speciality", ""), "context": ctx,
        "model": agent.get("model", ""), "effort": agent.get("effort") or "",
        "recipe": own.get("recipe") or RECIPES.get(ctx, RECIPES["day"]),
        "lookups": own.get("lookups") or LOOKUPS.get(ctx, []),
        "phases": own.get("phases") or PHASES.get(ctx, []),
        "routines": own.get("routines") or ROUTINES.get(ctx, []),
        "project": own.get("project") or "hq",
    }


def all_records(folder: Path | None = None) -> list[dict]:
    return [record(a) for a in agents.load(folder or config.FOLDER) if not a.get("hidden")]


def projects(folder: Path | None = None) -> list[dict]:
    p = (folder or config.FOLDER) / "HQ" / "projects.json"
    try:
        d = json.loads(p.read_text(encoding="utf8"))
        ps = d.get("projects") if isinstance(d, dict) else d
        ps = [x for x in ps if isinstance(x, dict) and x.get("id")] if isinstance(ps, list) else []
    except (OSError, ValueError):
        ps = []
    if not any(x["id"] == "hq" for x in ps):
        ps.insert(0, {"id": "hq", "name": "HQ", "what": "this app: its planning, team line and maintenance",
                      "planning": "HQ/roadmap.md", "head": "the development department"})
    return ps


def words(folder: Path | None = None) -> str:
    out = []
    for r in all_records(folder):
        out.append(f"{r['name']} ({r['kind']}; context {r['context']}; project {r['project']}): {r['speciality']}\n"
                   f"  briefing: {', '.join(r['recipe'])}\n"
                   f"  lookups: {', '.join(r['lookups']) or 'none'}\n"
                   f"  phases: {', '.join(r['phases']) or 'none'}\n"
                   f"  routines: {', '.join(r['routines']) or 'none'}")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "list":
        print(words())
        return 0
    if argv[0] == "show" and len(argv) == 2:
        for r in all_records():
            if r["id"] == argv[1].lower():
                print(json.dumps(r, indent=1, ensure_ascii=False))
                return 0
        print(f"No department {argv[1]!r}.")
        return 2
    if argv[0] == "projects":
        for p in projects():
            print(f"{p['id']}: {p.get('name', p['id'])}: {p.get('what', '')} (planning {p.get('planning', '?')}; "
                  f"head {p.get('head', '?')})")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
