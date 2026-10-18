"""H74: the get-started tutorial's demo call.

The tutorial (the question mark on the call page) shows the pieces in app/web/tour.json on the real screens. From
there a demo call can be started with Donna or Pepper: a safe playground. It runs the Free way (call.py: an empty
folder, nothing of the user's, nothing saved, no after-call work), on Opus for both (his words, 17 October 2026:
"Maybe they need to both have Opus. Not Sonnet. Because people are going to have a lot of questions"), with no tools
at all, so nothing can change. Her rules are made here from the same tour.json, so the call and the screens say the
same; `topic` is the piece they started from.
"""
from __future__ import annotations

import json
from pathlib import Path

TOUR = Path(__file__).resolve().parent / "web" / "tour.json"
MODEL = "opus"


def load() -> dict:
    return json.loads(TOUR.read_text())


def _names(text: str, names: dict) -> str:
    return text.replace("{donna}", names.get("donna", "Donna")).replace("{pepper}", names.get("pepper", "Pepper"))


def piece(topic: str, tour: dict | None = None) -> dict | None:
    return next((p for p in (tour or load())["pieces"] if p["id"] == topic), None)


def guide(names: dict | None = None) -> str:
    """The whole tutorial as plain text, for her to answer from."""
    t, n = load(), names or {}
    out = [_names(t["intro"], n), ""]
    for p in t["pieces"]:
        out.append(f"{_names(p['title'], n)}:")
        for s in p["steps"]:
            out.append(f"- {_names(s['title'], n)}: {_names(s['text'], n)}" + (" (coming soon)" if s.get("soon") else ""))
    out += ["", "More about HQ:"] + [f"- {f}" for f in t["facts"]]
    return "\n".join(out)


def rules(topic: str = "", me: str = "Donna", names: dict | None = None) -> str:
    """Added after her character on a demo call."""
    p = piece(topic) if topic else None
    start = (f"They started it from the part “{_names(p['title'], names or {})}”, so begin there if they "
             "don't say otherwise. ") if p else ""
    return f"""

This is a demo call, started from HQ's get-started tutorial. Whoever is calling may be new to HQ and not technical. \
It's a safe playground: nothing on this call is saved, you have no tools, and nothing in their HQ changes. You are \
{me}, in your own character and voice. {start}Explain HQ plainly and warmly, like a person showing a friend around, \
from the guide below; short spoken answers, one thing at a time, and offer what they might try next. When they ask \
you to do something (put it in the calendar, add it to the list, give the team work), play it out with made-up \
example content and say plainly that on a demo nothing really changed, and that on a real call you would do it. \
Never make anything up about their own life, files or mail: you can't see them here. If you don't know something \
about HQ, say so. When they end the call, say a short goodbye.

<hq-guide>
{guide(names)}
</hq-guide>"""


def greetings(me: str = "Donna") -> list[str]:
    """Her first words on a demo call: who she is, and that it's a demo."""
    return [f"Hi, it's {me}. This is a demo call, so nothing here is saved or changed. Ask me anything about HQ.",
            f"Hey, {me} here, on a demo call. Nothing's saved, so ask me anything about HQ."]
