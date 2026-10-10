"""H29: agents with names, personalities and their own specialities (10 October 2026, call at 15:09).

In the user's words: "what if we have, Let's call them agents for lack of better word. that we have
in this app so we have a Moneypenny, a Donna. A pepper? ... They have different personalities as
well and we can use them and they have different specialities as well." "for now just put one,
which is like the quick and the deep. I'll put two. We already have two, but later I want to
replace those."

So for now two agents replace Quick and Deep. Each has a name, a personality, a speciality, a model
and how much of the workspace it loads (B1: "quick" is the lighter part, "deep" everything). Later
agents (creative strategy, life coach) are one more entry each, with their own load.

Where they come from:
- HQ ships the defaults below, the same for everyone.
- A workspace may change or add agents in `Jarvis VA/agents/agents.json`: a list of objects with
  the same keys; an entry with a known id changes only the keys it gives, a new id adds an agent
  (it needs at least a name and a load). `"hidden": true` leaves an agent out of the call page.
- The headshot: `Jarvis VA/agents/<id>.jpg` (or .jpeg, .png, .webp) in the workspace. Pictures stay in
  the workspace, never in HQ. Without one, the call page shows a drawn placeholder (picture_svg).
"""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

LOADS = ("quick", "deep")
PICTURE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

# [Claude's choice, 10 October 2026: Pepper takes Quick and Donna takes Deep; Moneypenny waits for a
# later agent. The personalities and colours are Claude's too, the user's to change.]
DEFAULTS: list[dict] = [
    {
        "id": "pepper",
        "name": "Pepper",
        "load": "quick",
        "model": "sonnet",
        "colour": "#c2410c",
        "speciality": "Your agenda, your list, mail and quick orders",
        "personality": (
            "Calm, quick and organised, with a dry sense of humour. She runs the day-to-day: the "
            "agenda, the to-do list, the inbox and small orders. Short answers, straight to the "
            "point, and she gets it done before you've finished asking. She doesn't spar or coach; "
            "for the big picture she says Donna is the one to call."
        ),
    },
    {
        "id": "donna",
        "name": "Donna",
        "load": "deep",
        "model": "opus",
        "colour": "#6d28d9",
        "speciality": "Sparring, planning and the bigger picture",
        "personality": (
            "Warm, sharp and confident; she reads people and already knows the whole picture. She's "
            "the one to spar with: plans, decisions, the week and the long view. She says what she "
            "thinks, kindly and plainly, asks the one question that matters, and never pushes. She "
            "takes a moment longer to think, and it shows."
        ),
    },
]

_KEYS = ("name", "load", "model", "colour", "speciality", "personality", "hidden")


def agents_dir(folder: Path) -> Path:
    return folder / "Jarvis VA" / "agents"


def _clean(a: dict) -> dict | None:
    aid = str(a.get("id", "")).strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,30}", aid):
        return None
    name = str(a.get("name", "")).strip()
    load = a.get("load") if a.get("load") in LOADS else None
    if not name or not load:
        return None
    return {
        "id": aid,
        "name": name[:40],
        "load": load,
        "model": str(a.get("model") or ("opus" if load == "deep" else "sonnet")),
        "colour": a.get("colour") if re.fullmatch(r"#[0-9a-fA-F]{6}", str(a.get("colour", ""))) else "#475569",
        "speciality": str(a.get("speciality", "")).strip()[:120],
        "personality": str(a.get("personality", "")).strip()[:2000],
        "hidden": a.get("hidden") is True,
    }


def load(folder: Path) -> list[dict]:
    """The agents for this workspace: HQ's defaults with the workspace's changes on top, in order."""
    agents = {a["id"]: dict(a, hidden=False) for a in DEFAULTS}
    order = [a["id"] for a in DEFAULTS]
    try:
        extra = json.loads((agents_dir(folder) / "agents.json").read_text(encoding="utf8"))
    except (OSError, ValueError):
        extra = []
    for e in extra if isinstance(extra, list) else []:
        if not isinstance(e, dict):
            continue
        aid = str(e.get("id", "")).strip().lower()
        if aid in agents:
            merged = _clean({**agents[aid], **{k: e[k] for k in _KEYS if k in e}, "id": aid})
            if merged:
                agents[aid] = merged
        elif (new := _clean(e)):
            agents[new["id"]] = new
            order.append(new["id"])
    return [agents[i] for i in order]


def visible(folder: Path) -> list[dict]:
    return [a for a in load(folder) if not a["hidden"]]


def names(folder: Path) -> list[str]:
    return [a["name"] for a in visible(folder)]


def find(folder: Path, agent_id: str | None = None, mode: str | None = None) -> dict:
    """The agent a call asked for. Without a known id, the first visible agent with that load
    (pages from before H29 send only mode quick or deep), else the first one."""
    every = load(folder)
    by_id = {a["id"]: a for a in every}
    if agent_id and str(agent_id).lower() in by_id:
        return by_id[str(agent_id).lower()]
    shown = [a for a in every if not a["hidden"]] or every
    if mode in LOADS:
        for a in shown:
            if a["load"] == mode:
                return a
    return shown[0]


def picture(folder: Path, agent_id: str) -> Path | None:
    """The workspace's headshot for this agent, if there is one."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,30}", agent_id or ""):
        return None
    for ext in PICTURE_TYPES:
        p = agents_dir(folder) / f"{agent_id}{ext}"
        if p.is_file():
            return p
    return None


def picture_svg(agent: dict) -> str:
    """The placeholder headshot: the agent's initial on their colour, until a picture is added."""
    initial = escape(agent["name"][:1].upper())
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" '
        f'aria-label="{escape(agent["name"])}"><circle cx="48" cy="48" r="48" fill="{agent["colour"]}"/>'
        '<circle cx="48" cy="38" r="17" fill="#ffffff" fill-opacity=".22"/>'
        '<path d="M16 84c5-17 18-25 32-25s27 8 32 25" fill="#ffffff" fill-opacity=".22"/>'
        f'<text x="48" y="58" text-anchor="middle" font-family="-apple-system,Helvetica,Arial,sans-serif" '
        f'font-size="40" font-weight="700" fill="#ffffff">{initial}</text></svg>'
    )


def persona(agent: dict, user: str = "the user") -> str:
    """Added to the call rules: who she is on this call. The line is still called Jarvis."""
    return (
        f"\n# Who you are on this call: {agent['name']}\n\n"
        f"{user} picked {agent['name']} for this call. You are {agent['name']}, one of the agents in "
        f"{user}'s HQ (the call line itself is still called Jarvis). Where this differs from \"Who you "
        f"are on the call\" above, this wins. If asked your name, it's {agent['name']}.\n"
        f"Your personality: {agent['personality']}\n"
        f"What you're for: {agent['speciality']}.\n"
        "Everything else in the call rules above still holds.\n"
    )


def public(agent: dict) -> dict:
    """What the call page gets: no personality text, just what it shows and sends."""
    return {"id": agent["id"], "name": agent["name"], "load": agent["load"], "model": agent["model"],
            "speciality": agent["speciality"], "colour": agent["colour"],
            "picture": f"/agents/{agent['id']}/picture"}
