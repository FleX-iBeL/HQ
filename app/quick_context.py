"""B1: what a Quick call loads (9 October 2026, call at 14:05: "Okay, it's perfect. Let's split it up.").

Quick is for the calendar, mail and small orders. It knows the rules, where everything gets
written down, the to-do list, new mail and the last couple of days of notes. It leaves out the
rest of the workspace (the vision, the current situation and the coaching skill). Deep keeps everything, as in a normal chat.

How: a Quick session starts with CLAUDE_CODE_DISABLE_CLAUDE_MDS=1, so the CLI loads no CLAUDE.md
at all, and gets this text in its system prompt instead. The text is built from the folder's own
CLAUDE.md at call start, so there is still one source: each `@file` there is pulled in only when
it's on the Quick list below; the others are named as "not loaded, read it when needed". The
folder's settings (the deny list on sending email, the rules hook) still load, as in a chat.
The switch also stops the CLI loading Claude's memory for this folder (which calendar account,
how to handle calendar events), so those notes are added here too.
"""
from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

import config

sys.path.insert(0, str(config.ROOT / "routine"))
import log_cycle  # H100: the same three-hour cut as the routine's move to the archive

# The files a Quick call has in full, relative to the folder. coaching/log.md is trimmed (below).
QUICK_FILES = ["rules.md", "where-things-go.md", "challenges.md", "inbox.md", "coaching/log.md"]
# "The last couple of days of notes": with K1 switched off, the log's entries from today and the day before,
# plus its open commitments (whatever their age). K1 on (H100): the last three hours and the open commitments.
LOG_DAYS = 2
LOG_HOURS = log_cycle.HOURS

_IMPORT = re.compile(r"@([\w./-]+\.md)")
_ENTRY = re.compile(r"^## (\d{4}-\d{2}-\d{2})\b")


def trim_log(text: str, today: datetime.date, days: int = LOG_DAYS, now: datetime.datetime | None = None) -> str:
    """The log's head and open commitments, and only the recent entries: with K1 on the last three hours
    (H100, 13 October 2026: "Yeah, I'm even thinking maybe three hours"), else the last `days` days."""
    if config.LIGHT_NOTES:
        now = now or datetime.datetime.now()
        out = log_cycle.recent(text, now, LOG_HOURS)
        return out.rstrip() + (f"\n\n[On a call only the notes of the last {LOG_HOURS} hours and the open commitments "
                               "are here. Older notes are in coaching/log-archive.md, newest first: read them only "
                               "when he asks about something earlier.]\n")
    first = today - datetime.timedelta(days=days - 1)
    out, keep = [], True
    for line in text.splitlines():
        m = _ENTRY.match(line)
        if m:
            keep = datetime.date.fromisoformat(m.group(1)) >= first
        elif line.startswith("## "):  # a section that isn't a dated entry (Open commitments), wherever it stands
            keep = True
        if keep:
            out.append(line)
    out.append(f"\n[On a Quick call only the entries from {first:%-d %B} on are here; older ones are in the file.]")
    return "\n".join(out).rstrip() + "\n"


def memory_dir(folder: Path) -> Path:
    """Where Claude Code keeps its memory for this folder (its path with every other character as -)."""
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(folder)) / "memory"


def build(folder: Path, today: datetime.date | None = None) -> str:
    """The Quick call's instructions: CLAUDE.md with only the Quick files pulled in."""
    today = today or datetime.date.today()
    claude_md = (folder / "CLAUDE.md").read_text()
    pulled: list[str] = []

    def file_text(rel: str) -> str:
        text = (folder / rel).read_text()
        return trim_log(text, today) if rel == "coaching/log.md" else text

    def swap(m: re.Match) -> str:
        rel = m.group(1)
        if rel in QUICK_FILES and (folder / rel).exists():
            if rel not in pulled:
                pulled.append(rel)
            return f"`{rel}` (loaded, below)"
        return f"`{rel}` (not loaded on a Quick call; read it with the Read tool when it's needed)"

    body = _IMPORT.sub(swap, claude_md)
    parts = [
        "# This is a Quick call",
        f"{config.USER} picked Quick: calendar, mail and small orders. Only part of the folder is loaded: "
        + (f"the rules, where things go, the to-do list, the mail list, the last {LOG_HOURS} hours of notes and "
           "the open commitments (older notes are in the log archive). " if config.LIGHT_NOTES else
           "the rules, where things go, the to-do list, the mail list and the last two days of notes. ")
        + "The rest of the folder (the vision, the current situation and the coaching skill) is "
        "not loaded. Read a file when a question needs it; for sparring, planning "
        "or coaching, a Deep call has everything.",
        f"Contents of {folder / 'CLAUDE.md'} (project instructions):\n\n{body}",
    ]
    for rel in pulled:
        parts.append(f"Contents of {folder / rel}:\n\n{file_text(rel)}")
    mem = memory_dir(folder)
    if (mem / "MEMORY.md").exists():
        notes = [mem / "MEMORY.md"] + sorted(p for p in mem.glob("*.md") if p.name != "MEMORY.md")
        parts.append("Claude's memory for this folder (notes from earlier chats):\n\n"
                     + "\n\n".join(f"{p.name}:\n{p.read_text().strip()}" for p in notes))
    return "\n\n".join(parts)
