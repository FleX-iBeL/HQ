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


# H246: what each role loads. "day" (Donna) is Quick plus where he stands now; "coach" (Pepper) every file the folder's
# CLAUDE.md loads, but the notes without the team's work and only the very important mail; "build" (Moneypenny) none of
# the life files: the planning, the team's notes, the build notes in full and Claude's memory index (H280).
# 26 October 2026 (his call with Pepper, moneypenny-fix): "build" is Pepper's old load again, the whole folder and
# Claude's memory like a chat, minus the vision (VISION_FILES), which is Pepper's.
DAY_FILES = QUICK_FILES + ["current-situation.md"]
VISION_FILES = ["my-answers.md", "day-in-the-life.md", "lifestyle-design.md", "map.md"]
# 27 October 2026 (Pepper's green light on the fix): Moneypenny talks about building only, never his life: no mail list,
# no to-do list, no current situation either.
LIFE_FILES = ["inbox.md", "challenges.md", "current-situation.md"]
NOT_FOR_BUILD = VISION_FILES + LIFE_FILES
# A note in the log about the team's work: "- 25 October 2026, 20:15, job 345 (H244): ...".
# A call with Moneypenny is about building too.
_TEAM_NOTE = re.compile(r"^- \d{1,2} \w+ \d{4}, [\d:]+, (job \d+|call \(Moneypenny\b)")
TEAM_NOTES_MOST = 30  # H280: was 12


def _notes(text: str) -> list[tuple[str, list[str]]]:
    """The log split into its parts: (the section it's in, the note's lines); a note is a top-level bullet."""
    parts, section, cur = [], "", None
    for line in text.splitlines():
        if line.startswith("## ") or line.startswith("# "):
            section, cur = line, None
            parts.append((section, [line]))
        elif line.startswith("- "):
            cur = (section, [line])
            parts.append(cur)
        elif cur is not None:
            cur[1].append(line)
        else:
            parts.append((section, [line]))
    return parts


def is_team_note(lines: list[str]) -> bool:
    return bool(lines) and bool(_TEAM_NOTE.match(lines[0]))


def life_notes(text: str) -> str:
    """The log without the notes about the team's work (H246: Pepper gets nothing from the building)."""
    return "\n".join("\n".join(ls) for _, ls in _notes(text) if not is_team_note(ls)).rstrip() + "\n"


def team_notes(text: str, most: int = TEAM_NOTES_MOST) -> str:
    """Only the newest notes about the team's work (H246: what Moneypenny needs of the log)."""
    got = [ls for _, ls in _notes(text) if is_team_note(ls)][:most]
    return "\n\n".join("\n".join(ls).rstrip() for ls in got) + "\n" if got else "(none yet)\n"


def very_important(text: str) -> str:
    """Only the mail list's Very important section (H246: what a coaching call needs of the mail)."""
    out, keep = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            keep = line.strip() == "## Very important"
        if keep:
            out.append(line)
    return ("\n".join(out).rstrip() + "\n\n[The rest of the mail list is under To check in inbox.md; read it when "
            "he asks.]\n") if out else "(No very important mail.)\n"


def build(folder: Path, today: datetime.date | None = None, context: str = "day") -> str:
    """A call's instructions: CLAUDE.md with only the files its role loads pulled in (B1, H246).
    context "day" (Quick, Donna), "coach" (Pepper) or "build" (Moneypenny); see agents.CONTEXTS."""
    today = today or datetime.date.today()
    claude_md = (folder / "CLAUDE.md").read_text()
    pulled: list[str] = []
    wanted = DAY_FILES if context == "day" else None

    def file_text(rel: str) -> str:
        text = (folder / rel).read_text()
        if rel == "coaching/log.md":
            text = trim_log(text, today)
            return text if context == "build" else life_notes(text)  # H246: the team's work is Moneypenny's
        if rel == "inbox.md" and context == "coach":
            return very_important(text)
        return text

    def swap(m: re.Match) -> str:
        rel = m.group(1)
        if (wanted is None or rel in wanted) and not (context == "build" and rel in NOT_FOR_BUILD) \
                and (folder / rel).exists():
            if rel not in pulled:
                pulled.append(rel)
            return f"`{rel}` (loaded, below)"
        if context == "build" and rel in NOT_FOR_BUILD:
            return f"`{rel}` (not loaded for you: {config.USER}'s life is not your business, only building HQ; Donna or Pepper have it)"
        where = "a Quick call" if context == "day" else "this call"
        return f"`{rel}` (not loaded on {where}; read it with the Read tool when it's needed)"

    body = _IMPORT.sub(swap, claude_md)
    if context == "coach":
        head = ["# This is a coaching call",
                f"{config.USER}'s vision, the map, where he stands, the to-do list and the very important mail are "
                "loaded, and the notes of the last hours without the team's work. Nothing from building HQ is "
                "here (the planning, the team, the build notes): that's Moneypenny's. When he wants something built "
                "or put on the planning, put her on or bring her in."]
    elif context == "build":
        head = ["# This is a call about building HQ",
                f"The folder is loaded like a chat, with Claude's memory, except {config.USER}'s vision (the vision "
                "files and the map), his mail list, his to-do list and where he stands now: you talk about building "
                "HQ only, never his life. For his life, put Donna or Pepper on. The roadmap's rows, the planning, the queue and the build notes are not loaded in full: "
                "read the section or the row you need with grep or sed -n, never the whole file."]
    else:
        head = ["# This is a Quick call",
                f"{config.USER} picked Quick: calendar, mail and small orders. Only part of the folder is loaded: "
                + (f"the rules, where things go, the to-do list, the mail list, where they stand now, the last "
                   f"{LOG_HOURS} hours of notes and the open commitments (older notes are in the log archive). "
                   if config.LIGHT_NOTES else
                   "the rules, where things go, the to-do list, the mail list, where they stand now and the last two "
                   "days of notes. ")
                + "The rest of the folder (the vision, the map and the coaching skill) is "
                "not loaded. Read a file when a question needs it; for sparring, planning "
                "or coaching, Pepper has everything."]
    parts = head + [f"Contents of {folder / 'CLAUDE.md'} (project instructions):\n\n{body}"]
    for rel in pulled:
        parts.append(f"Contents of {folder / rel}:\n\n{file_text(rel)}")
    mem = memory_dir(folder)
    if (mem / "MEMORY.md").exists():
        notes = [mem / "MEMORY.md"] + sorted(p for p in mem.glob("*.md") if p.name != "MEMORY.md")
        parts.append("Claude's memory for this folder (notes from earlier chats):\n\n"
                     + "\n\n".join(f"{p.name}:\n{p.read_text().strip()}" for p in notes))
    return "\n\n".join(parts)
