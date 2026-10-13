"""Who the user is, read from their own workspace (M5, 10 October 2026).

HQ is the same for everyone, so nothing about one user is in its code. What the call needs to know
about them comes from workspace/me.md (the template ships it blank):

    **Name:** the name HQ calls them by (greetings, the call rules, the transcripts)
    **Names to hear:** words that help speech recognition (names, places, brands), comma separated
    **Never change:** folders in the workspace a call never changes or commits, comma separated
    **Private words:** words that must never end up in HQ itself (the privacy check), comma separated
    **Where I am:** the town (or town, country) for the weather every three hours (H120)
    ## On calls      anything extra for the call rules (their language, how they say times, ...)

Every part is optional. Without a name, HQ greets without one and the rules say "the user".
HQ_USER_NAME overrides the name (tests).
"""
import os
import re
from pathlib import Path


def _read(folder: Path) -> str:
    try:
        return (folder / "me.md").read_text(encoding="utf8")
    except OSError:
        return ""


def _field(text: str, label: str) -> str:
    m = re.search(rf"^\*\*{re.escape(label)}:\*\*[ \t]*(.*)$", text, re.M | re.I)
    value = (m.group(1).strip() if m else "")
    return "" if value.startswith("[") else value


def _section(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S | re.I)
    body = (m.group(1).strip() if m else "")
    return "" if not body or body.startswith("[") else body


def _list(value: str) -> list[str]:
    return [w.strip().strip("/") for w in value.rstrip(".").split(",") if w.strip()]


def load(folder: Path) -> dict:
    text = _read(folder)
    return {
        "name": os.environ.get("HQ_USER_NAME", _field(text, "Name")),
        "hear": _field(text, "Names to hear"),
        "on_calls": _section(text, "On calls"),
        "protected": _list(_field(text, "Never change")),
        "private": _list(_field(text, "Private words")),
        "place": _field(text, "Where I am"),
    }
