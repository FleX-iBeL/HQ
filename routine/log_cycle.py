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


_MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july", "august",
                                          "september", "october", "november", "december"), 1)}
_BULLET = re.compile(r"^- (\d{1,2}) ([A-Za-z]+) (\d{4}), (\d{1,2}):(\d{2})(?:,| ·)\s*(.*)$")
_LABEL_MOST = 70


def _label(rest: str) -> str:
    """The heading's label from what follows the date: up to the first colon or semicolon, at most _LABEL_MOST
    characters cut at a word, an opened bracket closed."""
    label = re.split(r"[:;]", re.sub(r"\*\*", "", rest), 1)[0].strip()
    if len(label) > _LABEL_MOST:
        label = label[:_LABEL_MOST].rsplit(" ", 1)[0].rstrip(" ,(")
    if label.count("(") > label.count(")"):
        label += ")"
    return label


def lift(text: str) -> tuple[str, int]:
    """Fable clean-up, 27 October 2026: a call or job note written as a dated top-level bullet under an undated
    section ("- 27 October 2026, 19:09, call (Pepper): …" under Open commitments) is one the three-hour cycle never
    saw: 292 of them, 280 KB, rode along on every call and text. Each becomes its own dated section
    (`## YYYY-MM-DD HH:MM · call (Pepper)`), the bullet kept whole as its body, so the cycle archives it like any entry.
    A bullet that doesn't start with a date (a real open commitment) stays where it is. Returns the text and how
    many were lifted."""
    head, sections = split(text)
    out, n = [_join(head)], 0
    for t, lines in sections:
        if t is not None:
            out.append(_join(lines)); continue
        keep, lifted, i = [lines[0]], [], 1
        while i < len(lines):
            m = _BULLET.match(lines[i])
            if m and m.group(2).lower() in _MONTHS:
                body = [lines[i]]; i += 1
                while i < len(lines) and not lines[i].startswith("- ") and not lines[i].startswith("## "):
                    body.append(lines[i]); i += 1
                while body and not body[-1].strip():
                    body.pop()
                when = f"{int(m.group(3)):04d}-{_MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d} {int(m.group(4)):02d}:{m.group(5)}"
                lifted.append(f"## {when} · {_label(m.group(6))}")
                lifted.append(_join(body)); n += 1
            else:
                keep.append(lines[i]); i += 1
        out.append(_join(keep))  # the section (Open commitments) keeps its place, with what wasn't a dated note
        out.extend(lifted)
    if not n:
        return text, 0
    return "\n\n".join(x for x in out if x.strip()) + "\n", n


def plan(log_text: str, archive_text: str, now: dt.datetime, hours: float = HOURS) -> tuple[str, str, int]:
    """The new log and archive, and how many entries moved. Nothing moves: the texts come back unchanged.
    Dated bullets under an undated section are lifted into their own sections first (`lift`)."""
    first = now - dt.timedelta(hours=hours)
    log_text, lifted = lift(log_text)
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
    if dry or (not n and new_log == before):
        return n
    if not n:  # only lifted: the log changes, the archive doesn't
        if log_p.read_text() == before:
            _write(log_p, new_log)
        return 0
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
