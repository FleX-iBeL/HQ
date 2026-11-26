"""J2: the start routine of a call reads the open loops (9 October 2026, call at 18:12:
"Every time we open a new chat, whether it's local or it's quick or it's deep, you will read that."
"One needs to give the input, one needs to read it, the output.").

The hourly mail check writes inbox.md; this reads it. The shape is fixed in inbox.md itself:
a "## Very important" section with one `- ` line per item, and a "## To check" section below it.
Very important items stay until the user says they're resolved or not that important. At call
start, the call system puts them in the warm-up message, so the first reply names them (on Quick
and on Deep alike, whatever else is loaded). The computer chat reads the same file through CLAUDE.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

INBOX = "inbox.md"
VERY_IMPORTANT = "## Very important"
TO_CHECK = "## To check"

_LINK = re.compile(r"\s*·?\s*\[Gmail\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


@dataclass
class OpenLoops:
    very_important: list[str]  # the item lines, without the leading "- " and without links
    to_check: int  # how many items wait under "To check"
    found: bool  # both sections were there


def _section(text: str, heading: str) -> list[str] | None:
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == heading)
    except StopIteration:
        return None
    out = []
    for ln in lines[start + 1:]:
        if ln.startswith("## "):
            break
        out.append(ln)
    return out


def read(folder: Path) -> OpenLoops:
    try:
        text = (folder / INBOX).read_text()
    except OSError:
        return OpenLoops([], 0, False)
    vi, tc = _section(text, VERY_IMPORTANT), _section(text, TO_CHECK)
    items = [_MD_LINK.sub(r"\1", _LINK.sub("", ln[2:])).strip() for ln in (vi or []) if ln.startswith("- ")]
    waiting = sum(1 for ln in (tc or []) if ln.startswith("- "))
    return OpenLoops(items, waiting, vi is not None and tc is not None)


def call_note(loops: OpenLoops) -> str:
    """What the warm-up message tells the call about the open loops ("" when there's nothing)."""
    if not loops.very_important:
        return ""
    items = "\n".join(f"- {it}" for it in loops.very_important)
    rest = (f" There {'is' if loops.to_check == 1 else 'are'} also {loops.to_check} other "
            f"mail{'' if loops.to_check == 1 else 's'} waiting under To check; mention that only in a few words, "
            "and go through them only when he asks." if loops.to_check else "")
    return (
        "Very important open items from his mail list, still open until he says they're resolved or "
        f"not that important:\n{items}\n"
        "In your first reply on this call, after answering what he says, tell him these in a sentence or "
        "two, like an assistant with a heads-up (\"Oh, and one important thing is still open: ...\"). "
        "Every call, also when he heard it before. If he says one is resolved or not that important, "
        f"handle it as the mail list says.{rest}"
    )
