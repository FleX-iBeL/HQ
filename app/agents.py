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
- A workspace may change or add agents in `HQ/agents/agents.json`: a list of objects with
  the same keys; an entry with a known id changes only the keys it gives, a new id adds an agent
  (it needs at least a name and a load). `"hidden": true` leaves an agent out of the call page.
- The headshot: `HQ/agents/<id>.jpg` (or .jpeg, .png, .webp) in the workspace. Pictures stay in
  the workspace, never in HQ. Without one, the call page shows a drawn placeholder (picture_svg).
- H73: an agent with `"coming_soon": true` is shown on the call page as a small locked card under the
  others, greyed out, and is never picked or called (`find` and `visible` leave it out; `soon` lists it).
  A workspace can unlock one with `"coming_soon": false`.
- H76 (12 October 2026): each agent has her own character on calls: `character` (one line, shown in
  Settings), `personality` (how she is and how she talks), `pushback` (a line that sounds like her when she
  pushes back), `greetings` (per part of the day: morning, afternoon, evening, night; or one list for all)
  and `continue_greetings` (when a call picks up an earlier one). In the greetings `{s}` is " Name", `{n}` is
  ", Name" and `{N}` is "Name. " (each nothing without a name), the name from the user's me.md.
- H77: the three below are HQ's defaults, the same for everyone and nothing personal. A workspace changes any
  of these keys in its agents.json; `is_default` says whether an agent's character is still HQ's own, and
  `python3 app/agents.py` prints each agent's character as it is now, marked default or changed.
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
# H46 (11 October 2026), in the user's words: "i want Donna to be Sonnet and Pepper to be Opus, and have them
# switched so Donna is left and Pepper is right. the colors can stay i like Purple for Donna and the red for
# Pepper." Then: "sonnet is not for sparring planning and the bigger picture, and opus is not for mail and quick
# orders". So the roles went with the models: Donna (Sonnet) the day-to-day on the Quick load, Pepper (Opus) the
# sparring on the Deep load. Each has her own voice in the call page's Settings ("Voice Pepper Potts", "Voice Donna Paulsen").
# H66 (12 October 2026), in the user's words: "can we make the default voice for when you install this? ... For
# Donna is Bella and for Pepper is Heart." A voice already chosen in Settings on a device stays as it is.
# H76 (12 October 2026, call at 13:43), in the user's words: "right now you sound like an AI still ... I just want
# to know your thinking. I don't want to hear you talk. ... maybe we can give Donna a different character than Pepper
# and then Moneypenny. So it sounds more... I like human interaction." Claude's three sketches, in the user's words:
# "Yeah, it's perfect." The agreed greeting and push-back line are each agent's own; the other greeting variants are
# Claude's, in the same character.
# H77, in the user's words: "we can give them our default we're using as well, but we give them the option to change
# it. And we show them what is the default for these agents right now."
DEFAULTS: list[dict] = [
    {
        "id": "donna",
        "name": "Donna",
        "load": "quick",
        "model": "sonnet",
        "full_name": "Donna Paulsen",
        "voice": "af_bella",
        "colour": "#6d28d9",
        "speciality": "Your agenda, your list, mail and quick orders",
        "character": "Quick and dry, a bit cheeky. Knows what you need before you finish",
        "personality": (
            "Quick and dry, a bit cheeky, and she knows what you need before you've finished the sentence. "
            "She runs the day-to-day: the agenda, the to-do list, the inbox and small orders. Short, snappy "
            "sentences, often only a few words; she gets on with it instead of talking about it. Dry humour, "
            "never mean. When something's off she says so with a wink and moves things along. She doesn't "
            "spar or coach; for the big picture she says Pepper is the one to call."
        ),
        "pushback": "You said that yesterday too. Shall I just put it in?",
        "greetings": {
            "morning": ["Hey you. What do you need?", "Morning. What do you need?"],
            "afternoon": ["Hey you. What do you need?", "There you are. What do you need?"],
            "evening": ["Hey you. What do you need?", "Evening. What do you need?"],
            "night": ["Hey you. What do you need?", "Hey you. Still up? What do you need?"],
        },
        "continue_greetings": ["Back again. Where were we?", "Hey you. Picking up where we left off."],
    },
    {
        "id": "pepper",
        "name": "Pepper",
        "load": "deep",
        "model": "opus",
        "full_name": "Pepper Potts",
        "voice": "af_heart",
        "colour": "#c2410c",
        "speciality": "Sparring, planning and the bigger picture",
        "character": "Warm, calm and direct. Takes a beat before she answers",
        "personality": (
            "Warm, calm and direct. She takes a beat before she answers, and then says what she really "
            "thinks, kindly and plainly. She's the one to spar with: plans, decisions, the week and the long "
            "view. She asks the one question that matters and lets it land; she never pushes. When she sees "
            "the fun thing winning over the thing that matters, she names it, gently, once. Unhurried "
            "sentences, a little warmth in them, no fuss."
        ),
        "pushback": "Honestly? That's the third build today. Is this the needle mover, or the fun one?",
        "greetings": {
            "morning": ["Hey{s}. What's on your mind?", "Morning{n}. What's on your mind?"],
            "afternoon": ["Hey{s}. What's on your mind?"],
            "evening": ["Hey{s}. What's on your mind?", "Evening{n}. What's on your mind?"],
            "night": ["Hey{s}. What's on your mind?", "Hey{s}. Late one. What's on your mind?"],
        },
        "continue_greetings": ["Hey{s}. Let's pick up where we left off.", "Hey{s}. Where were we? Let's carry on."],
    },
    # H73 (12 October 2026, call at 12:23), in the user's words: "Moneypenny could be Fable. And that's kind of
    # fitting as well because Moneypenny is famous for running things behind the scenes." "we could just put it
    # sort of like grayed out. And just say something like coming soon" and "I just want the icon to be yellow ...
    # As they show like an M for Moneypenny." Locked: never picked, never called. Her line, picked by the user from
    # Claude's options (cloud session, 12 October 2026): "oehhh clearance pending is nice".
    {
        "id": "moneypenny",
        "name": "Moneypenny",
        "load": "deep",
        "model": "fable",
        "full_name": "Miss Moneypenny",
        "voice": "bf_emma",
        "colour": "#ca8a04",
        "coming_soon": True,
        "speciality": "Clearance pending.",
        "character": "Few words, cool, a little mysterious. All business",
        "personality": (
            "Few words, cool and a little mysterious. All business. She runs the big, heavy jobs behind the "
            "scenes and doesn't explain how; when she says it's handled, it is. No small talk, no warm-up, "
            "no exclamation marks. Now and then a dry half-smile in the voice, never a joke."
        ),
        "pushback": "Noted. It'll be done. Just not tonight.",
        "greetings": ["{N}Go ahead.", "{N}I'm listening."],
        "continue_greetings": ["{N}Where we left off. Go ahead."],
    },
]

PARTS = ("morning", "afternoon", "evening", "night")
# The keys that make up an agent's character (H76); is_default compares these with HQ's own.
CHARACTER_KEYS = ("character", "personality", "pushback", "greetings", "continue_greetings")

_KEYS = ("name", "full_name", "voice", "load", "model", "colour", "speciality", "personality", "hidden", "coming_soon",
         "character", "pushback", "greetings", "continue_greetings")


def _lines(v, most: int = 8) -> list[str]:
    """A list of short spoken lines; anything else is dropped."""
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list):
        return []
    return [x.strip()[:160] for x in v if isinstance(x, str) and x.strip()][:most]


def _greetings(v) -> dict:
    """Greetings per part of the day; one plain list counts for every part."""
    if isinstance(v, dict):
        return {p: g for p in PARTS if (g := _lines(v.get(p)))}
    g = _lines(v)
    return {p: list(g) for p in PARTS} if g else {}


def agents_dir(folder: Path) -> Path:
    return folder / "HQ" / "agents"


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
        "full_name": str(a.get("full_name") or name).strip()[:60],
        "voice": a.get("voice") if re.fullmatch(r"[a-z]{2}_[a-z]{2,20}", str(a.get("voice", ""))) else "af_heart",
        "speciality": str(a.get("speciality", "")).strip()[:120],
        "personality": str(a.get("personality", "")).strip()[:2000],
        "hidden": a.get("hidden") is True,
        "coming_soon": a.get("coming_soon") is True,
        "character": str(a.get("character", "")).strip()[:160],
        "pushback": str(a.get("pushback", "")).strip()[:200],
        "greetings": _greetings(a.get("greetings")),
        "continue_greetings": _lines(a.get("continue_greetings")),
    }


def load(folder: Path) -> list[dict]:
    """The agents for this workspace: HQ's defaults with the workspace's changes on top, in order."""
    agents = {a["id"]: _clean(dict(a, hidden=False)) for a in DEFAULTS}
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
    """The agents a call can be made with (not hidden, not coming soon)."""
    return [a for a in load(folder) if not a["hidden"] and not a["coming_soon"]]


def soon(folder: Path) -> list[dict]:
    """H73: the locked agents, shown greyed out as coming soon; never called."""
    return [a for a in load(folder) if not a["hidden"] and a["coming_soon"]]


def names(folder: Path) -> list[str]:
    return [a["name"] for a in visible(folder)]


def find(folder: Path, agent_id: str | None = None, mode: str | None = None) -> dict:
    """The agent a call asked for. Without a known id, the first visible agent with that load
    (pages from before H29 send only mode quick or deep), else the first one."""
    every = [a for a in load(folder) if not a["coming_soon"]]  # H73: a locked agent is never called
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


def fill(text: str, user: str | None) -> str:
    """A greeting with the user's name from me.md put in ({s} " Name", {n} ", Name", {N} "Name. ")."""
    return (text.replace("{s}", f" {user}" if user else "").replace("{n}", f", {user}" if user else "")
            .replace("{N}", f"{user}. " if user else ""))


def greetings(agent: dict, user: str | None, part: str) -> list[str]:
    """H76: her greetings for this part of the day, with the name filled in; [] when she has none
    (then the call system's own greetings play)."""
    g = agent.get("greetings") or {}
    return [fill(x, user) for x in (g.get(part) or next((v for v in g.values() if v), []))]


def continue_greetings(agent: dict, user: str | None) -> list[str]:
    """H76: her greetings when a call continues an earlier one; [] when she has none."""
    return [fill(x, user) for x in agent.get("continue_greetings") or []]


def is_default(agent: dict) -> bool:
    """H77: is her character still HQ's own default (not changed in the workspace)?"""
    base = next((a for a in DEFAULTS if a["id"] == agent.get("id")), None)
    if not base:
        return False
    base = _clean(dict(base, hidden=False))
    return all(agent.get(k) == base.get(k) for k in CHARACTER_KEYS)


# H76, in the user's words: "right now you sound like an AI still" and "when you're thinking. I just want to know
# your thinking. I don't want to hear you talk." For every agent, after her own character.
HUMAN = (
    "Sound like a person on the phone, not like an AI: contractions, plain words, your own rhythm, and stay in "
    "your character the whole call, also when you push back or say no. No assistant phrases (\"Great question\", "
    "\"I'd be happy to\", \"Certainly\", \"Absolutely\", \"Is there anything else\"), don't repeat back what he "
    "just said, and don't wrap up with a summary. Don't say that you're thinking or what you're about to look up: "
    "while you work the call page plays a soft thinking sound, so stay quiet and answer when you have it."
)


def persona(agent: dict, user: str = "the user") -> str:
    """Added to the call rules: who she is on this call, and how she talks (H76)."""
    out = (
        f"\n# Who you are on this call: {agent['name']}\n\n"
        f"{user} picked {agent['name']} for this call. You are {agent['name']}, one of the agents in "
        f"{user}'s HQ. Where this differs from \"Who you "
        f"are on the call\" above, this wins. If asked your name, it's {agent['name']}.\n"
        f"Your character: {agent['personality']}\n"
        f"What you're for: {agent['speciality']}.\n"
    )
    if agent.get("pushback"):
        out += (f"How you sound when you push back, as an example of your voice (don't repeat it word for word): "
                f"\"{agent['pushback']}\"\n")
    return out + HUMAN + "\nEverything else in the call rules above still holds.\n"


def public(agent: dict) -> dict:
    """What the call page gets: no personality text, just what it shows and sends."""
    return {"id": agent["id"], "name": agent["name"], "full_name": agent.get("full_name") or agent["name"],
            "voice": agent.get("voice", "af_heart"), "load": agent["load"], "model": agent["model"],
            "speciality": agent["speciality"], "colour": agent["colour"],
            "picture": f"/agents/{agent['id']}/picture", "coming_soon": agent.get("coming_soon") is True,
            "character": agent.get("character", ""), "default": is_default(agent)}


def describe(folder: Path, user: str | None = None) -> str:
    """H77: every agent's character as it is now in this workspace, marked HQ's default or changed."""
    out = []
    for a in load(folder):
        if a["hidden"]:
            continue
        mark = "HQ's default" if is_default(a) else "changed in your workspace (HQ/agents/agents.json)"
        soon_ = ", coming soon" if a["coming_soon"] else ""
        g = greetings(a, user, "afternoon")
        out.append(f"{a['name']} ({a['model']}{soon_}): {a['character'] or a['personality'][:80]}. [{mark}]\n"
                   f"  How she is: {a['personality']}\n"
                   + (f"  Pushing back: \"{a['pushback']}\"\n" if a["pushback"] else "")
                   + (f"  Greeting: \"{g[0]}\"\n" if g else ""))
    return "\n".join(out)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import config  # noqa: E402  (the workspace and the name from me.md)
    print(describe(config.FOLDER, config.ME["name"] or None))
