#!/usr/bin/env python3
"""H100: the coaching log keeps only the last three hours of notes (13 October 2026, call at 00:00, in the
user's words: "Yeah, I'm even thinking maybe three hours", "No, I like this because we make a lot of calls and
every time... Um... You have to load everything", and "Now the computer can also do the 3 hours.").

Every normal chat, job and Deep call loads coaching/log.md in full (an @ import in the workspace's CLAUDE.md),
so the file itself stays small: every entry older than HOURS moves to coaching/log-archive.md, newest first.
Moving only: an entry goes over word for word, never shortened. What always stays in the log: its head (the
title and the lines before the first entry) and every section that isn't a dated entry (Open commitments),
whatever its age. A Quick call cuts the same way in its own text (app/quick_context.py, `recent`).

An entry is a `## YYYY-MM-DD HH:MM …` heading and the lines under it; a heading with only a date counts as
the start of that day. The routine runs `move` every minute on the main HQ (tick.py) and commits both files
through the lock when something moved; the backup gets them through the sync.

    python3 routine/log_cycle.py          # move what's older than three hours, print what moved
    python3 routine/log_cycle.py --dry    # only say what would move
"""
from __future__ import annotations

import datetime as dt
import os
import re
import sys
from pathlib import Path

HOURS = 3
LOG = "coaching/log.md"
ARCHIVE = "coaching/log-archive.md"
ARCHIVE_HEAD = (
    "# Coaching Log: archive\n\n"
    "> **Private and sensitive.** Only for this project (this folder). Never copy elsewhere unless explicitly asked.\n\n"
    "Log entries older than three hours, moved here from the coaching log by the routine (H100). Newest first. "
    "Nothing here is ever deleted.\n"
)

_ENTRY = re.compile(r"^## (\d{4}-\d{2}-\d{2})(?:\s+(\d{1,2}):(\d{2}))?\b")


def when(heading: str) -> dt.datetime | None:
    """The time of a dated entry's heading, or None for any other section."""
    m = _ENTRY.match(heading)
    if not m:
        return None
    t = dt.datetime.fromisoformat(m.group(1))
    if m.group(2):
        t = t.replace(hour=int(m.group(2)), minute=int(m.group(3)))
    return t


def split(text: str) -> tuple[list[str], list[tuple[dt.datetime | None, list[str]]]]:
    """The head (lines before the first `## `) and the sections in order, each with its time (None if undated)."""
    head: list[str] = []
    sections: list[tuple[dt.datetime | None, list[str]]] = []
    for line in text.splitlines():
        if line.startswith("## "):
            sections.append((when(line), [line]))
        elif sections:
            sections[-1][1].append(line)
        else:
            head.append(line)
    return head, sections


def _join(lines: list[str]) -> str:
    return "\n".join(lines).rstrip("\n")


def recent(text: str, now: dt.datetime, hours: float = HOURS) -> str:
    """The log as a call should see it: the head, the undated sections, and the entries of the last `hours`."""
    first = now - dt.timedelta(hours=hours)
    head, sections = split(text)
    keep = [_join(head)] + [_join(lines) for t, lines in sections if t is None or t >= first]
    return "\n\n".join(k for k in keep if k) + "\n"


def plan(log_text: str, archive_text: str, now: dt.datetime, hours: float = HOURS) -> tuple[str, str, int]:
    """The new log and archive, and how many entries moved. Nothing moves: the texts come back unchanged."""
    first = now - dt.timedelta(hours=hours)
    head, sections = split(log_text)
    old = [(t, lines) for t, lines in sections if t is not None and t < first]
    if not old:
        return log_text, archive_text, 0
    stay = [lines for t, lines in sections if not (t is not None and t < first)]
    new_log = "\n\n".join(x for x in [_join(head)] + [_join(l) for l in stay] if x) + "\n"
    a_head, a_sections = split(archive_text or ARCHIVE_HEAD)
    # Newest first; equal times keep their order from the log (which is newest first already).
    merged = sorted(old + a_sections, key=lambda s: s[0] or dt.datetime.min, reverse=True)
    new_archive = "\n\n".join(x for x in [_join(a_head)] + [_join(l) for _, l in merged] if x) + "\n"
    return new_log, new_archive, len(old)


def _write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".h100-tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def move(folder: Path | str, now: dt.datetime | None = None, hours: float = HOURS, dry: bool = False) -> int:
    """Move the old entries from the log to the archive. Returns how many moved (0: nothing written)."""
    now, folder = now or dt.datetime.now(), Path(folder)
    log_p, arch_p = folder / LOG, folder / ARCHIVE
    if not log_p.exists():
        return 0
    before = log_p.read_text()
    arch = arch_p.read_text() if arch_p.exists() else ""
    new_log, new_arch, n = plan(before, arch, now, hours)
    if not n or dry:
        return n
    # Words go into the archive first, so an entry is never in neither file; and the log is only replaced if
    # nobody wrote to it in the meantime (a call's notes), else this waits for the next minute.
    _write(arch_p, new_arch)
    if log_p.read_text() != before:
        _write(arch_p, arch) if arch else arch_p.unlink()
        return 0
    _write(log_p, new_log)
    return n


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import hqpaths
    dry = "--dry" in sys.argv
    n = move(Path(hqpaths.FOLDER), dry=dry)
    print(f"{n} log entr{'y' if n == 1 else 'ies'} older than {HOURS} hours "
          f"{'would move' if dry else 'moved'} to the archive" if n else f"Nothing older than {HOURS} hours in the log")
