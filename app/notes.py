"""H105: the user's quick notes, from the round notes button on the call page.

One file in the workspace (never in HQ's code): HQ/notes.md, or HQ_NOTES. Each note is one line under
"## Notes", "- YYYY-MM-DD HH:MM:SS · text" (line breaks kept as <br>), newest at the bottom, so a call
reads it like any other file and goes through it with the user; a note is cleared by removing its line
(the page's Clear does the same). Since H117 just text: the doodle space is gone, and a notes-doodle.png
saved before is left where it is, unread.
A line a call wrote by hand ("- something") counts as a note too; its id is a hash of the line.
Since H263 nothing is ever lost: there's no Clear all, and a cleared note is kept, its line moved to
notes-cleared.md next to the notes ("- cleared YYYY-MM-DD HH:MM:SS · " and the note's own line), newest at the
bottom. The page shows Undo for a moment after a Clear; a call can bring any cleared note back.

    python3 app/notes.py                 the notes, as the page gets them (JSON)
    python3 app/notes.py add TEXT        add one note (F99: the way in for a call or a text; the file itself is refused)
    python3 app/notes.py clear WORDS     clear the one note with these words in it (kept, so it can come back)
    python3 app/notes.py cleared         the cleared notes, newest first, in plain lines
    python3 app/notes.py restore WORDS   bring back the newest cleared note with these words in it
    python3 app/notes.py new             H338: only the notes added since the last look, then all marked as looked at

F102 (31 October 2026): only the main writes the notes, like the text lines (F58). His quick note of 30 October never reached
the server: on the backup a note goes to the main as a hand-over (`put`), kept in notes.here.md next to the notes (which never
syncs) until the main's list brings it back, so his page shows it at once; the main can't be reached: it goes on by itself.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "routine"))
import hqlock  # noqa: E402  F102: one lock across processes, unique temp files

NOTES = Path(os.environ.get("HQ_NOTES", str(config.DATA / "notes.md")))
MAX_TEXT = 2000
HEAD = ("# Quick notes\n\n"
        "> **Private.** Written on the call page's notes button (H105). Go through them together whenever "
        "asked; once a topic is gone through, clear it (the page's Clear, or app/notes.py clear WORDS): cleared notes "
        "are kept in notes-cleared.md, so any can come back.\n\n"
        "## Notes\n\n")
_CLEARED = re.compile(r"^- cleared (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) · (.*?)(?: <!-- before (\w+) -->)?$")
_STAMP = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) · (.*)$")
_lock = hqlock.For(lambda: NOTES)


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


def _here(notes: Path) -> Path:
    return notes.with_name(notes.stem + ".here" + notes.suffix)


def _backup() -> bool:
    if os.environ.get("HQ_ROLE_HERE"):
        return False
    try:
        import role
        return role.is_backup()
    except Exception:
        return False


def _hand(*args) -> str:
    """The backup hands a change to the main; how it went: main, kept, or '' (not done, write it here as before)."""
    import role
    try:
        code, _o, _e, how = role.hand("notes", list(args), timeout=15)
    except Exception:
        return ""
    return how if how == "kept" or (how == "main" and code == 0) else ""


def _here_lines(notes: Path) -> list[str]:
    try:
        return [l for l in _here(notes).read_text().splitlines() if l.startswith("- ")]
    except OSError:
        return []


def _keep_here(notes: Path, lines: list[str]) -> None:
    """On the backup: its own notes the main's list hasn't brought back yet (those it has are dropped)."""
    have = set(_read(notes)[1])
    left = [l for l in dict.fromkeys(lines) if l not in have]
    f = _here(notes)
    if left:
        tmp = hqlock.tmp(f)
        tmp.write_text("\n".join(left) + "\n")
        os.replace(tmp, f)
    else:
        f.unlink(missing_ok=True)


def _write(notes: Path, head: list[str], body: list[str]) -> None:
    notes.parent.mkdir(parents=True, exist_ok=True)
    tmp = hqlock.tmp(notes)
    tmp.write_text("\n".join(head).rstrip("\n") + "\n\n" + ("\n".join(body) + "\n" if body else ""))
    os.replace(tmp, notes)


def items(notes: Path | None = None) -> list[dict]:
    notes = notes or NOTES
    out = []
    body = _read(notes)[1]
    for line in body + [l for l in _here_lines(notes) if l not in body]:
        if not line.startswith("- "):
            continue
        out.append(_item(line))
    return out


def read(notes: Path | None = None) -> dict:
    return {"items": items(notes)}


def add(text: str, notes: Path | None = None) -> dict | None:
    text = "\n".join(l.rstrip() for l in str(text).replace("\r", "").strip().splitlines())[:MAX_TEXT].strip()
    if not text:
        return None
    notes = notes or NOTES
    line = f"- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · " + text.replace("\n", "<br>")
    if notes == NOTES and _backup() and _hand("put", line):
        with _lock:
            _keep_here(notes, _here_lines(notes) + [line])
        return _item(line)
    with _lock:
        head, body = _read(notes)
        notes_end = next((i for i, l in enumerate(body) if not l.startswith("- ")), len(body))
        body.insert(notes_end, line)
        _write(notes, head, body)
    return _item(line)


def cleared_file(notes: Path | None = None) -> Path:
    """H263: where cleared notes are kept, next to the notes file (notes.md → notes-cleared.md)."""
    notes = notes or NOTES
    return notes.with_name(notes.stem + "-cleared" + notes.suffix)


def _item(line: str) -> dict:
    m = _STAMP.match(line[2:])
    when, text = (m.group(1), m.group(2)) if m else ("", line[2:])
    return {"id": _id(line), "when": when, "text": text.replace("<br>", "\n").strip()}


def _cleared_lines(notes: Path) -> list[str]:
    try:
        return [l for l in cleared_file(notes).read_text().splitlines() if _CLEARED.match(l)]
    except OSError:
        return []


def _keep(line: str, notes: Path, before: str = "") -> None:
    """Moves a cleared note's line to the cleared file, so it can always come back (before: the note that came
    right after it, so Undo puts it back in its place)."""
    f = cleared_file(notes)
    try:
        text = f.read_text()
    except OSError:
        text = ("# Cleared quick notes\n\n> **Private.** Every note cleared from the quick notes (H263), newest at the "
                "bottom, so it can always be brought back.\n\n")
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = hqlock.tmp(f)
    tmp.write_text(text.rstrip("\n") + "\n" + f"- cleared {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · {line[2:]}"
                   + (f" <!-- before {before} -->" if before else "") + "\n")
    os.replace(tmp, f)


def cleared(notes: Path | None = None) -> list[dict]:
    """The cleared notes, newest first: each with its own id (the same as before it was cleared) and when it went."""
    out = []
    for l in reversed(_cleared_lines(notes or NOTES)):
        m = _CLEARED.match(l)
        out.append({**_item("- " + m.group(2)), "cleared": m.group(1)})
    return out


def put(line: str, notes: Path | None = None) -> bool:
    """F102: the main's way in for a note the backup handed over: the line as it is, in its place by its time, once."""
    notes = notes or NOTES
    if not line.startswith("- "):
        return False
    with _lock:
        head, body = _read(notes)
        if line in body:
            return False
        end = next((i for i, l in enumerate(body) if not l.startswith("- ")), len(body))
        when = _item(line)["when"]
        later = [i for i in range(end) if when and (_item(body[i])["when"] or "") > when]
        body.insert(later[0] if later else end, line)
        _write(notes, head, body)
    return True


def clear(note_id: str, notes: Path | None = None) -> bool:
    notes = notes or NOTES
    if notes == NOTES and _backup():
        mine = [l for l in _here_lines(notes) if _id(l) == note_id]
        if mine:  # not on the main's list yet: it's cleared there the moment it lands
            with _lock:
                _keep_here(notes, [l for l in _here_lines(notes) if l not in mine])
        if _hand("clear-id", note_id):
            return True
    with _lock:
        head, body = _read(notes)
        for i, line in enumerate(body):
            if line.startswith("- ") and _id(line) == note_id:
                nxt = body[i + 1] if i + 1 < len(body) and body[i + 1].startswith("- ") else ""
                _keep(line, notes, _id(nxt) if nxt else "")
                del body[i]
                _write(notes, head, body)
                return True
    return False


def restore(note_id: str, notes: Path | None = None) -> dict | None:
    """Brings a cleared note back to the notes, in its place by its time (a note without a time at the end)."""
    notes = notes or NOTES
    if notes == NOTES and _backup() and _hand("restore-id", note_id):
        return {"id": note_id}
    with _lock:
        lines = _cleared_lines(notes)
        for k in range(len(lines) - 1, -1, -1):
            m = _CLEARED.match(lines[k])
            line = "- " + m.group(2)
            if _id(line) != note_id:
                continue
            head, body = _read(notes)
            end = next((i for i, l in enumerate(body) if not l.startswith("- ")), len(body))
            when = _item(line)["when"]
            at = end
            ids = [_id(l) for l in body[:end]]
            if m.group(3) and m.group(3) in ids:  # back in front of the note it was in front of
                at = ids.index(m.group(3))
            elif when:
                later = [i for i in range(end) if (_item(body[i])["when"] or "") > when]
                at = later[0] if later else end
            body.insert(at, line)
            _write(notes, head, body)
            f = cleared_file(notes)
            text = f.read_text().splitlines()
            gone = len(text) - 1 - text[::-1].index(lines[k])
            del text[gone]
            tmp = hqlock.tmp(f)
            tmp.write_text("\n".join(text) + "\n")
            os.replace(tmp, f)
            return _item(line)
    return None


def seen_file(notes: Path | None = None) -> Path:
    """H338: the notes a look has had already, next to the notes (notes.md → notes-seen.json)."""
    notes = notes or NOTES
    return notes.with_name(notes.stem + "-seen.json")


def new(notes: Path | None = None) -> list[dict]:
    """H338 (Part C 9): his notes marked as handled by the program, so a look gets only the ones added since the last look
    (Pepper re-read all 26 on 6 November). The ones it gives are marked as looked at."""
    notes = notes or NOTES
    with _lock:
        try:
            seen = set(json.loads(seen_file(notes).read_text(encoding="utf8")))
        except (OSError, ValueError, TypeError):
            seen = set()
        now = items(notes)
        out = [i for i in now if i["id"] not in seen]
        if out:
            f = seen_file(notes)
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps(sorted(seen | {i["id"] for i in now})), encoding="utf8")
            os.replace(tmp, f)
    return out


def _match(words: str, found: list[dict]) -> list[dict]:
    w = words.strip().lower()
    return [i for i in found if w and w in i["text"].lower()] if w else []


def _cli(args: list[str]) -> int:
    if not args:
        print(json.dumps(read(), ensure_ascii=False, indent=1))
        return 0
    what, words = args[0], " ".join(args[1:])
    if what == "put" and words:  # F102: the main writes a note the backup handed over (role.WRITES)
        print("In the notes." if put(words) else "Already there.")
        return 0
    if what in ("clear-id", "restore-id") and words:
        done = clear(words) if what == "clear-id" else restore(words)
        print("Done." if done else "It isn't here.")
        return 0 if done else 1
    if what == "add":
        got = add(words)
        print(f"In the notes: {got['text']}" if got else "Nothing to add.")
        return 0 if got else 1
    if what == "new":
        got = new()
        print("\n".join(f"- {i['when'][:16]} {i['text']}" for i in got) if got else "No new notes since the last look.")
        return 0
    if what == "cleared":
        got = cleared()
        print("\n".join(f"- cleared {i['cleared'][:16]}: {i['text']}" for i in got) if got else "No cleared notes.")
        return 0
    if what in ("clear", "restore"):
        pool = items() if what == "clear" else cleared()
        hit = _match(words, pool)
        if what == "restore":
            hit = hit[:1]  # the newest one cleared with these words
        if len(hit) != 1:
            print(f"{'No' if not hit else len(hit)} {'note' if what == 'clear' else 'cleared note'}"
                  f"{'s' if len(hit) > 1 else ''} with \"{words}\" in it" + (": say more of its words." if hit else "."))
            return 1
        if what == "clear":
            clear(hit[0]["id"])
            print(f"Cleared (kept, so it can come back): {hit[0]['text']}")
        else:
            restore(hit[0]["id"])
            print(f"Back in the notes: {hit[0]['text']}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
