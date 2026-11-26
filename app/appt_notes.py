"""H146: a quick note on each appointment in HQ's calendar.

15 October 2026 (call at 09:34, Pepper), typed by the user: "maybe we can have a feature i can add a note to the
calendar appointments in HQ, so we can also pick up on those (just like the quick notes feature but then linked to
each appointment and with one click i can add a quick note typing) then maybe for example if haircut was scheduled
for 3pm to 4pm, and i arrived at 4pm and left 5pm, then i could just write that in the quick note, then later tell
donna on the chat line to look at the haircut and update my calendar and then it can be checked off at the end of
the day. this way we keep the speed up while keeping administration in order"

In the calendar sheet of the call page every appointment has a note button; a tap opens it with the note field
ready to type. Its notes show under its title in the list and in the appointment, each with its own Clear. Kept in
the workspace next to calendar.json, as HQ/calendar-notes.json (HQ_CALENDAR_NOTES; synced to the other computer, off
GitHub: titles and notes are private). A note belongs to the appointment's mark id (planning.py), so an appointment
X'd (and, before H241, moved to HQ Planning and back) keeps its notes; with each one the appointment's title and time are saved, so a note
still reads right after the appointment has changed or gone.

A call and Donna's direct line read them (`python3 app/appt_notes.py`): every appointment with notes, with where it
is in Google Calendar now (calendar id and event id), so "look at the haircut and update my calendar" can change its
times from the note. Only the page adds and clears notes; Google Calendar is never written here.

    python3 app/appt_notes.py          every appointment with notes, in plain lines (what a call reads)
    python3 app/appt_notes.py json     the same as JSON
    python3 app/appt_notes.py add ID TEXT | clear ID NOTE   (F115: what the backup's page hands to the main)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agenda  # noqa: E402

MAX_TEXT = 1000
MAX_NOTES = 20  # per appointment
_lock = threading.Lock()


def notes_file() -> Path:
    return Path(os.environ.get("HQ_CALENDAR_NOTES") or agenda.data_file().with_name("calendar-notes.json"))


def _read() -> dict:
    try:
        s = json.loads(notes_file().read_text(encoding="utf8"))
        return s if isinstance(s, dict) and isinstance(s.get("notes"), dict) else {"notes": {}}
    except (OSError, ValueError):
        return {"notes": {}}


def _write(s: dict) -> None:
    p = notes_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f"{p.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    os.replace(tmp, p)


def _index() -> dict:
    """Every appointment id that stands for a mark id (its copies in HQ Planning and back, planning.py)."""
    try:
        import planning
        return planning._index(planning._marks(planning._read()))[0]
    except Exception:
        return {}


def _key(eid: str, by: dict | None = None) -> str:
    return (by if by is not None else _index()).get(eid, eid)


def _current(key: str, events: list[dict], by: dict) -> dict | None:
    """The appointment as the last read of the calendar has it now: its own id, or a copy that carries its mark."""
    return next((e for e in events if e.get("id") == key), None) or next((e for e in events if by.get(e.get("id")) == key), None)


def attach(events: list[dict]) -> list[dict]:
    """The page's appointments with their notes: appt_notes, a list of {id, when, text}, oldest first."""
    notes = _read()["notes"]
    if not notes:
        return [{**e, "appt_notes": []} for e in events]
    by = _index()
    return [{**e, "appt_notes": list((notes.get(e.get("mark_id") or _key(e.get("id", ""), by)) or {}).get("items") or [])}
            for e in events]


def _handed(args: list[str]):
    """F115: on the backup the main writes the notes (role.door): None when this computer writes them, else the main's
    answer (code, out, err, how)."""
    sys.path.insert(0, str(HERE.parent / "routine"))
    import role
    return role.door(notes_file(), "appt_notes", args)


def _locked():
    sys.path.insert(0, str(HERE.parent / "routine"))
    import hqlock  # F115: across processes too (the page, the main running a handed note)
    return hqlock.locked(notes_file())


def add(eid: str, text: str, now: float | None = None) -> dict:
    """A note on the appointment eid (its id or mark id). KeyError when there's no such appointment, ValueError when
    the text is empty."""
    text = "\n".join(l.rstrip() for l in str(text).replace("\r", "").strip().splitlines())[:MAX_TEXT].strip()
    if not text:
        raise ValueError("nothing to add")
    h = _handed(["add", eid, text])
    if h is not None:
        if h[0] == 1 and "no such" in (h[1] + h[2]):
            raise KeyError("no such appointment")
        if h[0]:
            raise ValueError(" ".join((h[1] + h[2]).split()) or "the main didn't take it")
        return {"items": [], "handed": h[3]}
    t = now or time.time()
    with _lock, _locked():
        s = _read()
        by = _index()
        key = _key(eid, by)
        events = agenda._read().get("events") or []
        e = _current(key, events, by) or (_current(eid, events, by) if eid != key else None)
        n = s["notes"].get(key)
        if not e and not n:
            raise KeyError("no such appointment")
        n = n or {"items": []}
        if e:
            n.update({k: e.get(k) for k in ("title", "start", "end", "all_day", "calendar")})
        when = datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")
        nid = hashlib.sha1(f"{key}|{t}|{text}".encode()).hexdigest()[:10]
        n["items"] = (list(n.get("items") or []) + [{"id": nid, "when": when, "text": text}])[-MAX_NOTES:]
        n["changed"] = t
        s["notes"][key] = n
        _write(s)
        return n


def clear(eid: str, note_id: str) -> bool:
    """Clears one note; the appointment's entry goes when its last note does."""
    h = _handed(["clear", eid, note_id])
    if h is not None:
        return h[0] == 0
    with _lock, _locked():
        s = _read()
        key = _key(eid)
        n = s["notes"].get(key) or s["notes"].get(eid)
        if not n:
            return False
        key = key if key in s["notes"] else eid
        items = [i for i in n.get("items") or [] if i.get("id") != note_id]
        if len(items) == len(n.get("items") or []):
            return False
        if items:
            n["items"] = items
        else:
            s["notes"].pop(key, None)
        _write(s)
        return True


def listing() -> list[dict]:
    """Every appointment with notes, oldest appointment first, with where it is in Google Calendar now."""
    notes = _read()["notes"]
    cal = agenda._read()
    events, by = cal.get("events") or [], _index()
    out = []
    for key, n in notes.items():
        if not isinstance(n, dict) or not n.get("items"):
            continue
        e = _current(key, events, by)
        row = {"id": key, "title": (e or n).get("title", ""), "start": (e or n).get("start", ""), "end": (e or n).get("end", ""),
               "all_day": bool((e or n).get("all_day")), "calendar": (e or n).get("calendar", ""), "notes": n["items"],
               "in_google": bool(e)}
        if e:
            row.update({"calendar_id": e.get("cal", ""), "event_id": e.get("gid", ""), "others": bool(e.get("others"))})
        out.append(row)
    out.sort(key=lambda r: agenda._sort_key(r["start"]))
    return out


def text() -> str:
    rows = listing()
    if not rows:
        return "No notes on any appointment."
    lines = ["Notes on appointments, written in the calendar in the app (oldest appointment first):"]
    for r in rows:
        where = (f"calendarId {r['calendar_id']}, eventId {r['event_id']}" if r.get("event_id")
                 else "not in the last read of the calendar (moved or removed since)")
        lines.append(f"- {r['title']} ({agenda.when_words(r)}; {r['calendar'] or 'Main'} calendar; {where}"
                     + ("; has other people in it" if r.get("others") else "") + ")")
        for i in r["notes"]:
            lines.append(f"    note ({i['when']}): " + i["text"].replace("\n", " / "))
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "list":
        print(text())
    elif args[0] == "json":
        print(json.dumps(listing(), ensure_ascii=False, indent=1))
    elif args[0] == "add" and len(args) >= 3:  # F115: what the backup hands to the main (the page's tap there)
        try:
            add(args[1], " ".join(args[2:]))
            print("Note added.")
        except KeyError:
            print("no such appointment")
            sys.exit(1)
        except ValueError as e:
            print(str(e))
            sys.exit(1)
    elif args[0] == "clear" and len(args) == 3:
        if not clear(args[1], args[2]):
            print("no such note")
            sys.exit(1)
        print("Note cleared.")
    else:
        print(__doc__)
        sys.exit(2)
