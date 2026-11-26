"""The walkthrough on keeping HQ running (MAINTAINING.md at HQ's top), read in sections.

The owner's plan: "the walkthrough on maintaining HQ, placed where Moneypenny loads it, written last". The file is
long, so her start (quick_context.build and the build briefing) carries only its index: the sections by number and
title, and the command that prints one. `app/rules.py maintain [N]` prints them. Standard library only.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = "MAINTAINING.md"
_HEAD = re.compile(r"^## (\d+)\. (.+)$", re.M)


def text(root: Path | None = None) -> str:
    try:
        return ((root or ROOT) / FILE).read_text(encoding="utf8")
    except OSError:
        return ""


def sections(root: Path | None = None) -> list[tuple[int, str, str]]:
    """(number, title, the section's text with its heading) of each numbered section, in order."""
    t = text(root)
    heads = list(_HEAD.finditer(t))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(t)
        out.append((int(m.group(1)), m.group(2).strip(), t[m.start():end].rstrip() + "\n"))
    return out


def section(which: str, root: Path | None = None) -> str:
    """One section, by its number or a word of its title; '' when there's none."""
    for n, title, body in sections(root):
        if which.strip() == str(n) or (not which.strip().isdigit() and which.strip().lower() in title.lower()):
            return body
    return ""


def index(root: Path | None = None) -> str:
    """What an agent's start carries of the walkthrough: what it is, when to read it, how, and its sections."""
    secs = sections(root)
    if not secs:
        return ""
    rules = (root or ROOT) / "app" / "rules.py"
    return ("Keeping HQ running: the walkthrough is " + str((root or ROOT) / FILE) + ". Before you act on one of these, "
            "or give the team an item about one, read its section (a quick look, no yes needed): python3 \""
            + str(rules) + "\" maintain N. The sections: " + "; ".join(f"{n} {t}" for n, t, _ in secs) + ".")
