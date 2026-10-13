"""H105: the user's quick notes, from the round notes button on the call page.

One file in the workspace (never in HQ's code): HQ/notes.md, or HQ_NOTES. Each note is one line under
"## Notes", "- YYYY-MM-DD HH:MM:SS · text" (line breaks kept as <br>), newest at the bottom, so a call
reads it like any other file and goes through it with the user; a note is cleared by removing its line
(the page's Clear does the same). Since H117 just text: the doodle space is gone, and a notes-doodle.png
saved before is left where it is, unread.
A line a call wrote by hand ("- something") counts as a note too; its id is a hash of the line.

    python3 app/notes.py            the notes, as the page gets them (JSON)
"""
import hashlib
import json
import os
import re
import sys
import threading
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

NOTES = Path(os.environ.get("HQ_NOTES", str(config.DATA / "notes.md")))
MAX_TEXT = 2000
HEAD = ("# Quick notes\n\n"
        "> **Private.** Written on the call page's notes button (H105). Go through them together whenever "
        "asked; once a topic is gone through, remove its line (the page's Clear does the same).\n\n"
        "## Notes\n\n")
_STAMP = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) · (.*)$")
_lock = threading.Lock()


def _id(line: str) -> str:
    return hashlib.sha1(line.encode()).hexdigest()[:12]


def _split(text: str) -> tuple[list[str], list[str]]:
    """The file's lines before the notes (with the heading), and the note lines."""
    lines = text.splitlines()
    try:
        at = next(i for i, l in enumerate(lines) if l.strip().lower() == "## notes")
    except StopIteration:  # written by hand without the heading: keep what's there, the notes go under one
        other = [l for l in lines if not l.startswith("- ")]
        head = (other + ["", "## Notes"]) if any(l.strip() for l in other) else HEAD.rstrip("\n").splitlines()
        return head, [l for l in lines if l.startswith("- ")]
    after = lines[at + 1:]
    end = next((i for i, l in enumerate(after) if l.startswith("## ")), len(after))
    return lines[:at + 1], [l for l in after[:end] if l.startswith("- ")] + after[end:]


def _read(notes: Path) -> tuple[list[str], list[str]]:
    try:
        return _split(notes.read_text())
    except OSError:
        return HEAD.rstrip("\n").splitlines(), []


def _write(notes: Path, head: list[str], body: list[str]) -> None:
    notes.parent.mkdir(parents=True, exist_ok=True)
    tmp = notes.with_name(notes.name + ".tmp")
    tmp.write_text("\n".join(head).rstrip("\n") + "\n\n" + ("\n".join(body) + "\n" if body else ""))
    os.replace(tmp, notes)


def items(notes: Path | None = None) -> list[dict]:
    out = []
    for line in _read(notes or NOTES)[1]:
        if not line.startswith("- "):
            continue
        m = _STAMP.match(line[2:])
        when, text = (m.group(1), m.group(2)) if m else ("", line[2:])
        out.append({"id": _id(line), "when": when, "text": text.replace("<br>", "\n").strip()})
    return out


def read(notes: Path | None = None) -> dict:
    return {"items": items(notes)}


def add(text: str, notes: Path | None = None) -> dict | None:
    text = "\n".join(l.rstrip() for l in str(text).replace("\r", "").strip().splitlines())[:MAX_TEXT].strip()
    if not text:
        return None
    notes = notes or NOTES
    line = f"- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · " + text.replace("\n", "<br>")
    with _lock:
        head, body = _read(notes)
        notes_end = next((i for i, l in enumerate(body) if not l.startswith("- ")), len(body))
        body.insert(notes_end, line)
        _write(notes, head, body)
    return items(notes)[notes_end]


def clear(note_id: str, notes: Path | None = None) -> bool:
    notes = notes or NOTES
    with _lock:
        head, body = _read(notes)
        for i, line in enumerate(body):
            if line.startswith("- ") and _id(line) == note_id:
                del body[i]
                _write(notes, head, body)
                return True
    return False


def clear_all(notes: Path | None = None) -> int:
    notes = notes or NOTES
    with _lock:
        head, body = _read(notes)
        kept = [l for l in body if not l.startswith("- ")]
        gone = len(body) - len(kept)
        if gone:
            _write(notes, head, kept)
    return gone


if __name__ == "__main__":
    print(json.dumps(read(), ensure_ascii=False, indent=1))
