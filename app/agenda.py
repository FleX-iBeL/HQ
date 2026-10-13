"""H101: the user's calendar inside HQ, and an appointment as a call's context.

13 October 2026 (call at 19:53, Pepper), in the user's words: "Should be in good calendar. We just need to have
that. We just have... The information in the app as well." and "Maybe through API or something, I don't know."

The appointments stay in Google Calendar, the one place. HQ only reads them: never writes, moves or deletes.
The read goes through the Google Calendar connector of the user's own Claude (claude.ai), the same way the
hourly mail check reads Gmail, so no Google key or sign-in is needed in HQ: a short `claude -p` run (Haiku)
that may only call list_calendars and list_events (everything that writes is refused), streamed, and the tool
results are read straight from the stream, word for word as Google gave them, so Claude retypes nothing.

What it reads: every calendar the connector lists, from today 00:00 for DAYS days. Kept in the workspace as
HQ/calendar.json (HQ_CALENDAR_FILE; synced to the other computer, off GitHub). The look runs on the main, from
tick.py (start()): every hour from 07:00 to 23:00, and when the call page opens the calendar and the last look
is older than FRESH seconds (refresh()). The call page shows the days; a tap on an appointment shows it with
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
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=DAYS)
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
    return str(t.get("date", "")), True


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
            })
    events.sort(key=lambda x: (_sort_key(x["start"]), x["title"]))
    return [{"id": k, "name": v} for k, v in cals.items()], events


def _event_id(cal: str, eid: str) -> str:
    import hashlib
    return hashlib.sha1(f"{cal}\n{eid}".encode()).hexdigest()[:16]


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


def running(s: dict | None = None, now: float | None = None) -> bool:
    s = _read() if s is None else s
    return bool(s.get("running")) and (now or time.time()) - s["running"] < RUN_MAX


def due(now: float | None = None, s: dict | None = None) -> bool:
    """An hourly look: on, from 07:00 to 23:00, an hour since the last one (or its last try)."""
    if not on():
        return False
    s = _read() if s is None else s
    t = now or time.time()
    if running(s, t):
        return False
    if not DAY[0] <= datetime.fromtimestamp(t).hour < DAY[1]:
        return False
    last = max(s.get("looked") or 0, s.get("failed") or 0, s.get("asked") or 0)
    return t - last >= EVERY


def _start(s: dict, t: float) -> None:
    s["asked"] = t
    _write(s)
    py = ROOT / ".venv" / "bin" / "python"
    log = ROOT / "scratch" / "calendar.log"
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
    """What the call page shows: the appointments from today on, the time of the last look, any error."""
    s = _read()
    t = now or time.time()
    today = datetime.fromtimestamp(t).strftime("%Y-%m-%d")
    events = [e for e in s.get("events") or [] if not _over(e, today, t)]
    return {"on": on(), "looked": s.get("looked"), "looking": running(s, t), "error": s.get("error", ""),
            "events": events}


def _over(e: dict, today: str, t: float) -> bool:
    """Over: a whole day before today (Google's end date is the day after), or a timed one that ended over an hour ago."""
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
