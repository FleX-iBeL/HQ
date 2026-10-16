"""H101: the user's calendar inside HQ, and an appointment as a call's context.

13 October 2026 (call at 19:53, Pepper), in the user's words: "Should be in good calendar. We just need to have
that. We just have... The information in the app as well." and "Maybe through API or something, I don't know."

The appointments stay in Google Calendar, the one place. HQ only reads them here: never writes, moves or deletes.
(H143: the one write is planning.py's, moving an appointment the user X'd to the calendar HQ Planning and back.)
The read goes through the Google Calendar connector of the user's own Claude (claude.ai), the same way the
hourly mail check reads Gmail, so no Google key or sign-in is needed in HQ: a short `claude -p` run (Haiku)
that may only call list_calendars and list_events (everything that writes is refused), streamed, and the tool
results are read straight from the stream, word for word as Google gave them, so Claude retypes nothing.

What it reads: every calendar the connector lists, from this week's Monday 00:00 (H143: the past days of the week stay,
so they can still be ticked off) to DAYS days from today. Kept in the workspace as
HQ/calendar.json (HQ_CALENDAR_FILE; synced to the other computer, off GitHub). The look runs on the main, from
tick.py (start()): every hour from 07:00 to 23:00, and when the call page opens the calendar and the last look
is older than FRESH seconds (refresh()). H153: and within the minute after anything wrote in the calendar (a call,
Donna's chat, planning.py's moves): changed() leaves a mark in calendar-changed.json (synced, so a write on the backup
reaches the main), and the main reads again when the mark is newer than its last look (due()). The call page shows the days; a tap on an appointment shows it with
"Call about this", and the call's Claude gets the appointment (about()) in its warm-up note.

Off: HQ_CALENDAR=0. Tests: HQ_CALENDAR_FAKE=<a file with the stream lines a run would give> stands in for Claude.

    python3 app/agenda.py               the saved days, as the page gets them (JSON)
    python3 app/agenda.py look          read the calendar now (a Claude run, a few cents of usage)
    python3 app/agenda.py status        when it last looked, whether a look is due
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "routine"))
import hqpaths  # noqa: E402

DAYS = 14  # today and the next 13 days
EVERY = 3600  # a look every hour in the day
DAY = (7, 23)  # from 07:00, the last hourly look before 23:00, local time
FRESH = 15 * 60  # opening the calendar reads it again when the last look is older than this
RUN_MAX = 6 * 60  # a look that runs longer is taken as gone
NOTES_MAX = 1500
PAGE = 25  # appointments per page of list_events: small enough that Claude Code hands the page back whole  # an appointment's own notes, at most this many characters

TOOL = "mcp__claude_ai_Google_Calendar__"
ALLOW = [TOOL + "list_calendars", TOOL + "list_events"]
DENY = [TOOL + t for t in ("create_event", "update_event", "delete_event", "respond_to_event", "suggest_time")] + [
    "Bash", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch", "Read", "Grep", "Glob"]
EVENT_TYPES = ["DEFAULT", "OUT_OF_OFFICE", "FOCUS_TIME", "BIRTHDAY", "FROM_GMAIL"]


def on() -> bool:
    return os.environ.get("HQ_CALENDAR", "1") != "0"


def data_file() -> Path:
    return Path(os.environ.get("HQ_CALENDAR_FILE") or os.path.join(hqpaths.DATA, "calendar.json"))


def _read() -> dict:
    try:
        s = json.loads(data_file().read_text(encoding="utf8"))
        return s if isinstance(s, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(s: dict) -> None:
    p = data_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    os.replace(tmp, p)


def timezone() -> str:
    try:
        return os.environ.get("HQ_TIMEZONE") or os.path.realpath("/etc/localtime").split("/zoneinfo/", 1)[1]
    except IndexError:
        return ""


# -- the look ----------------------------------------------------------------------------------

def prompt(now: datetime) -> str:
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=today.weekday())  # H143: from Monday
    end = today + timedelta(days=DAYS)
    tz = timezone()
    extra = f', "timeZone": "{tz}"' if tz else ""
    return (
        "You read a calendar for a program; the program reads your tool results itself, so write nothing else.\n"
        "1. Call list_calendars once.\n"
        "2. Then, for every calendar it lists, call list_events once with exactly: "
        f'{{"calendarId": "<that calendar\'s id>", "startTime": "{start:%Y-%m-%dT%H:%M:%S}", '
        f'"endTime": "{end:%Y-%m-%dT%H:%M:%S}", "pageSize": {PAGE}, "orderBy": "startTime", '
        f'"eventType": {json.dumps(EVENT_TYPES)}{extra}}}. '
        "If a result has a nextPageToken, call it again with that pageToken.\n"
        "Never change anything in the calendar. When all are read, reply with only the word: done"
    )


def _claude() -> str:
    return os.environ.get("HQ_CLAUDE_CLI") or hqpaths.tool("claude", "/opt/homebrew/bin/claude")


def run_claude(text: str) -> list[str]:
    """The stream lines of one read-only Claude run (or the stand-in's, in a test)."""
    fake = os.environ.get("HQ_CALENDAR_FAKE")
    if fake:
        return Path(fake).read_text(encoding="utf8").splitlines()
    cmd = [_claude(), "-p", "--no-chrome", "--model", "haiku", "--permission-mode", "dontAsk",
           "--no-session-persistence", "--output-format", "stream-json", "--verbose",
           "--allowedTools", ",".join(ALLOW), "--disallowedTools", ",".join(DENY)]
    r = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=RUN_MAX, cwd=str(hqpaths.FOLDER))
    if r.returncode != 0 and not r.stdout.strip():
        raise RuntimeError((r.stderr or "the run failed").strip()[-300:])
    return r.stdout.splitlines()


def tool_results(lines: list[str]) -> list[tuple[str, dict, object]]:
    """(tool name, its input, its result as JSON) for every calendar tool call in a run's stream."""
    calls: dict[str, tuple[str, dict]] = {}
    out = []
    for line in lines:
        try:
            m = json.loads(line)
        except ValueError:
            continue
        msg = m.get("message") if isinstance(m, dict) else None
        if not isinstance(msg, dict) or not isinstance(msg.get("content"), list):
            continue
        for c in msg["content"]:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                calls[c.get("id", "")] = (str(c.get("name", "")), c.get("input") or {})
            elif c.get("type") == "tool_result" and c.get("tool_use_id") in calls:
                name, inp = calls[c["tool_use_id"]]
                body = c.get("content")
                if isinstance(body, list):
                    body = "".join(b.get("text", "") for b in body if isinstance(b, dict))
                body = _persisted(body)
                try:
                    out.append((name, inp, json.loads(body)))
                except (TypeError, ValueError):
                    pass  # an error message, not a result
    return out


_SAVED = re.compile(r"Full output saved to: (\S+?\.(?:txt|json))")


def _persisted(body):
    """An answer too big for the chat is saved to a file by Claude Code, with only a preview in the stream:
    read the whole answer from that file (only from Claude Code's own folder), then remove it."""
    if not isinstance(body, str) or "<persisted-output>" not in body[:40]:
        return body
    m = _SAVED.search(body)
    if not m:
        return body
    p = Path(m.group(1))
    try:
        if not p.resolve().is_relative_to((Path.home() / ".claude").resolve()):
            return body
        full = p.read_text(encoding="utf8")
        p.unlink()
        return full
    except (OSError, ValueError):
        return body


def _when(t: dict) -> tuple[str, bool]:
    """An event's start or end as ISO text, and whether it's a whole day."""
    if not isinstance(t, dict):
        return "", False
    if t.get("dateTime"):
        return str(t["dateTime"]), False
    # H153: the connector gives a whole day's date as midnight UTC ("2026-10-19T00:00:00Z"), which is 02:00 here and
    # the day before west of Greenwich: a whole day is its date only
    return str(t.get("date", ""))[:10], True


def events_from(results: list[tuple[str, dict, object]]) -> tuple[list[dict], list[dict]]:
    """The calendars and the appointments in them, from a run's tool results."""
    cals: dict[str, str] = {}
    for name, _, res in results:
        if name.endswith("list_calendars") and isinstance(res, dict):
            for c in res.get("calendars") or []:
                if isinstance(c, dict) and c.get("id"):
                    name = str(c.get("summary") or c["id"])
                    # the main calendar is named after the account's address: "Main" reads better
                    cals[c["id"]] = "Main" if "@" in name and "calendar.google.com" not in name else name
    seen, events = set(), []
    for name, inp, res in results:
        if not name.endswith("list_events") or not isinstance(res, dict):
            continue
        cal = str(inp.get("calendarId") or "primary")
        for e in res.get("events") or []:
            if not isinstance(e, dict) or e.get("status") == "cancelled" or not e.get("id"):
                continue
            key = (cal, e["id"])
            if key in seen:
                continue
            seen.add(key)
            start, all_day = _when(e.get("start"))
            end, _ = _when(e.get("end"))
            if not start:
                continue
            events.append({
                "id": _event_id(cal, e["id"]),
                "title": str(e.get("summary") or "(no title)"),
                "start": start, "end": end, "all_day": all_day,
                "where": str(e.get("location") or ""),
                "notes": str(e.get("description") or "")[:NOTES_MAX],
                "calendar": cals.get(cal, "Mine" if cal == "primary" else cal),
                "free": e.get("transparency") == "transparent",
                "type": str(e.get("eventType") or "DEFAULT"),
                "link": str(e.get("htmlLink") or ""),
                # H143: where it is in Google, for planning.py's move to HQ Planning; with others in it, never moved
                "gid": str(e["id"]), "cal": cal,
                "others": any(isinstance(a, dict) and not a.get("self") for a in e.get("attendees") or []),
            })
    events.sort(key=_order)
    return [{"id": k, "name": v} for k, v in cals.items()], events


def _event_id(cal: str, eid: str) -> str:
    import hashlib
    return hashlib.sha1(f"{cal}\n{eid}".encode()).hexdigest()[:16]


def _order(e: dict) -> tuple:
    """H153: in time order; a whole day first on its day, then the timed ones, then by title."""
    return (_sort_key(e.get("start") or ""), 0 if e.get("all_day") else 1, e.get("title") or "")


def _day_only(e: dict) -> dict:
    """H153: a whole day saved before the fix (midnight UTC) as its date only."""
    if not e.get("all_day"):
        return e
    return {**e, "start": (e.get("start") or "")[:10], "end": (e.get("end") or "")[:10]}


def _sort_key(start: str) -> float:
    try:
        d = datetime.fromisoformat(start)
        return (d if d.tzinfo else d.astimezone()).timestamp()
    except ValueError:
        return 0.0


def look(now: float | None = None) -> dict:
    """Read the calendar now and save it. On a failure the last good days stay, with the error."""
    s = _read()
    t = now or time.time()
    s["running"] = t
    _write(s)
    try:
        cals, events = events_from(tool_results(run_claude(prompt(datetime.fromtimestamp(t)))))
        if not cals:
            raise RuntimeError("the calendar connector gave no calendars (is Google Calendar connected in Claude?)")
        s = {**_read(), "looked": t, "calendars": cals, "events": events, "error": "", "from": DAYS}
        s.pop("running", None)
    except Exception as e:
        s = {**_read(), "error": str(e)[:300], "failed": t}
        s.pop("running", None)
    _write(s)
    return s


def changed_file() -> Path:
    return data_file().with_name(data_file().stem + "-changed.json")


def changed_at() -> float:
    try:
        return float(json.loads(changed_file().read_text(encoding="utf8")).get("at") or 0)
    except (OSError, ValueError, TypeError, AttributeError):
        return 0.0


def changed(why: str = "", now: float | None = None) -> bool:
    """H153: something just wrote in the calendar (a call, Donna, planning.py): read it again within the minute, so
    the page shows the change and not the last hourly read. The mark is a file of its own (only a writer writes it,
    the main only reads it), synced, so a write on the backup reaches the main; on the main the read starts right
    away. True when a read was started here. Never raises."""
    if not on():
        return False
    t = now or time.time()
    try:
        p = changed_file()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"at": t, "why": str(why)[:80]}) + "\n", encoding="utf8")
    except OSError:
        return False
    try:
        import role
        if role.acting() != "main":
            return False  # the main's tick picks the mark up
    except Exception:
        pass
    try:
        return start(t)
    except Exception:
        return False


def running(s: dict | None = None, now: float | None = None) -> bool:
    s = _read() if s is None else s
    return bool(s.get("running")) and (now or time.time()) - s["running"] < RUN_MAX


def due(now: float | None = None, s: dict | None = None) -> bool:
    """An hourly look: on, from 07:00 to 23:00, an hour since the last one (or its last try). H153: or, at any hour,
    a write in the calendar since the last look started."""
    if not on():
        return False
    s = _read() if s is None else s
    t = now or time.time()
    if running(s, t):
        return False
    if changed_at() > max(s.get("asked") or 0, s.get("looked") or 0, s.get("failed") or 0):
        return True
    if not DAY[0] <= datetime.fromtimestamp(t).hour < DAY[1]:
        return False
    last = max(s.get("looked") or 0, s.get("failed") or 0, s.get("asked") or 0)
    return t - last >= EVERY


def _start(s: dict, t: float) -> None:
    s["asked"] = t
    _write(s)
    py = ROOT / ".venv" / "bin" / "python"
    # H162: a test's look logs next to its own calendar file, not in the real scratch/calendar.log
    log = data_file().parent / "calendar.log" if os.environ.get("HQ_CALENDAR_FILE") else ROOT / "scratch" / "calendar.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([str(py) if py.exists() else sys.executable, str(Path(__file__).resolve()), "look"],
                     cwd=str(ROOT), stdout=open(log, "a"), stderr=subprocess.STDOUT, start_new_session=True)


def start(now: float | None = None) -> bool:
    """From tick.py, every minute on the main: when an hourly look is due, run it detached. True when started."""
    s = _read()
    t = now or time.time()
    if not due(t, s):
        return False
    _start(s, t)
    return True


def refresh(now: float | None = None) -> bool:
    """From the call page opening the calendar: read it again when the last look is older than FRESH."""
    if not on():
        return False
    s = _read()
    t = now or time.time()
    if running(s, t) or t - max(s.get("looked") or 0, s.get("asked") or 0) < FRESH:
        return False
    _start(s, t)
    return True


# -- for the page and the call -------------------------------------------------------------------

def read(now: float | None = None) -> dict:
    """What the call page shows: the appointments from this week's Monday on (H143: the past days stay for the
    ticks), each with its mark, the time of the last look, any error."""
    s = _read()
    t = now or time.time()
    d = datetime.fromtimestamp(t)
    monday = (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")
    events = [_day_only(e) for e in s.get("events") or [] if not _over(e, monday, t, week=True)]
    try:  # H143: done, or X (moved to HQ Planning); H154: a moved one the last read doesn't show yet stays in view
        import planning
        events += [_day_only(e) for e in planning.standins(s.get("events") or [], s.get("looked"))
                   if not _over(e, monday, t, week=True)]
        events = planning.attach(sorted(events, key=_order))
    except Exception:
        events = sorted(events, key=_order)
    try:  # H146: his quick notes on each appointment
        import appt_notes
        events = appt_notes.attach(events)
    except Exception:
        pass
    try:  # H124: the bell, on the appointments Donna will ping him for
        import pings
        bell = pings.pinged()
        events = [{**e, "ping": e.get("id") in bell} for e in events]
    except Exception:
        pass
    return {"on": on(), "looked": s.get("looked"), "looking": running(s, t), "error": s.get("error", ""),
            "events": events}


def _over(e: dict, today: str, t: float, week: bool = False) -> bool:
    """Over: a whole day before today (Google's end date is the day after), or a timed one that ended over an hour ago.
    With week (H143), today is this week's Monday and anything from Monday on stays."""
    if week:
        return (e.get("start") or "")[:10] < today and not (e.get("all_day") and (e.get("end") or "")[:10] > today)
    if e.get("all_day"):
        return (e.get("end") or "")[:10] <= today if e.get("end") else e.get("start", "")[:10] < today
    end = e.get("end") or e.get("start", "")
    return _sort_key(end) < t - 3600


def about(event_id: str) -> dict | None:
    """One saved appointment by its id (the page sends it when a call starts from it)."""
    if not event_id:
        return None
    return next((e for e in _read().get("events") or [] if e.get("id") == event_id), None)


def when_words(e: dict) -> str:
    """'Wednesday 14 October, 10:00 to 11:30' or 'Wednesday 14 October, all day'."""
    try:
        a = datetime.fromisoformat(e["start"])
    except (KeyError, ValueError):
        return e.get("start", "")
    day = f"{a:%A} {a.day} {a:%B}"
    if e.get("all_day"):
        return f"{day}, all day"
    try:
        b = datetime.fromisoformat(e["end"])
        return f"{day}, {a:%H:%M} to {b:%H:%M}" if b.date() == a.date() else f"{day}, {a:%H:%M} to {b:%A} {b:%H:%M}"
    except (KeyError, ValueError):
        return f"{day}, {a:%H:%M}"


def when_line(e: dict) -> str:
    """One line for the transcript's head: the title and when."""
    return f"{e.get('title', '')} ({when_words(e)})".replace("\n", " ")


def greetings(e: dict, name: str = "") -> list[str]:
    """The call system's greeting on a call about an appointment: it names it (spoken, so plain words only).
    Wording Claude's choice."""
    title = re.sub(r"[^\w\s,.'&:/-]", "", e.get("title", "")).strip() or "this appointment"
    n = f", {name}" if name else ""
    return [f"Hi{n}. About {title}. What do you need?", f"Hey{n}. Let's talk about {title}. What's up?"]


# H129 (14 October 2026, call at 13:02, Pepper): when he closes a call, the goodbye comments on what he's doing right
# now. In the user's words: "I want you to check what is on my to-do list right now, or on my calendar, I mean, what
# I'm doing right now. And then you can give me a comment on that one as you say goodbye instead of a generic goodbye."
# Read from the saved days only (no Claude run), so the goodbye isn't slow.
SOON = 90 * 60  # an appointment starting within this counts as what he's doing next


def right_now(now: float | None = None, soon: int = SOON) -> dict | None:
    """The timed appointment happening now, else the first one starting within `soon` seconds; None without one.
    Whole days don't count: they say little about what he's doing this moment."""
    t = now or time.time()
    events = [e for e in _read().get("events") or [] if not e.get("all_day") and e.get("start")]
    on, next_ = [], []
    for e in events:
        a = _sort_key(e["start"])
        b = _sort_key(e.get("end") or e["start"])
        if a <= t < max(b, a + 60):
            on.append(e)
        elif t < a <= t + soon:
            next_.append(e)
    if on:  # the one that started last is the most precise "right now"
        return max(on, key=lambda e: _sort_key(e["start"]))
    return min(next_, key=lambda e: _sort_key(e["start"])) if next_ else None


def goodbye_note(user: str = "the user", now: float | None = None) -> str:
    """What the call's Claude gets on a turn that sounds like a goodbye: what he's doing right now, to comment on."""
    t = now or time.time()
    e = right_now(t) if on() else None
    if e:
        a = _sort_key(e["start"])
        hhmm = datetime.fromtimestamp(a).strftime("%H:%M")
        what = re.sub(r"\s+", " ", e.get("title", "")).strip()
        where = f", at {e['where']}" if e.get("where") else ""
        when = f"on now (started {hhmm})" if a <= t else f"starting at {hhmm}"
        return (f"[Call system, only if {user} is closing the call now: right now in his calendar: {what}{where}, "
                f"{when}. Comment on that in your goodbye.]")
    return (f"[Call system, only if {user} is closing the call now: nothing in his calendar right now or soon. Comment "
            "in your goodbye on something that's up on his to-do list now, from what you already know of it.]")


def call_note(e: dict, user: str = "the user") -> str:
    """What a call's Claude gets when the call was started from this appointment."""
    lines = [f"Title: {e.get('title', '')}", f"When: {when_words(e)}", f"Calendar: {e.get('calendar', '')}"]
    if e.get("where"):
        lines.append(f"Where: {e['where']}")
    if e.get("free"):
        lines.append("Shown as free (it doesn't block the time)")
    if e.get("notes"):
        lines.append(f"Its notes:\n{e['notes']}")
    return (
        f"{user} started this call by tapping an appointment in his calendar in HQ, so this call is about it. "
        "The call system greets him by naming it; pick it up from his answer, without reading it all back, and help "
        "with whatever it needs "
        "(what it's for, what to prepare, how it fits his day); what his files say about it counts too. "
        "The calendar is read only from here: change it only when he asks, as always.\n"
        "<appointment>\n" + "\n".join(lines) + "\n</appointment>\n"
    )


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "read"
    if cmd == "read":
        print(json.dumps(read(), ensure_ascii=False, indent=1))
    elif cmd == "look":
        s = look()
        print(time.strftime("%Y-%m-%d %H:%M:%S"), "calendar:",
              f"failed: {s['error']}" if s.get("error") else f"{len(s.get('events') or [])} appointments")
    elif cmd == "status":
        s = _read()
        print(json.dumps({"on": on(), "looked": s.get("looked"), "running": running(s), "due": due(s=s),
                          "error": s.get("error", ""), "appointments": len(s.get("events") or [])}))
    else:
        print(__doc__)
        sys.exit(2)
