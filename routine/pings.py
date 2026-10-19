"""H124: Donna texts first: a ping when an appointment he picked starts, reminders he asks for, and her own notes.

14 October 2026, in Donna's chat at 10:34: "can you also notify me in this chat when that appointment starts?", and
on the call at 11:59 (Pepper), typed: "Yes or at least give her the option, doesn't have to be default for everything
Just being able to, and have a notification bell symbol next to the appointment in the calendar list inside the app
for items that will get pinged And also i want she can send reminders outside calendar appointments Maybe she can also
have her own notes list just like you, and the ability to text me related to it on her initiative".

Four things, all texted on the direct line (H80, direct_line.py), never written to Google Calendar:
  1. Appointment pings: only the appointments he picks (none by default). Picked from a call or her chat (this
     script), or with the bell in the calendar inside the app (H101). When one starts (or BEFORE minutes earlier,
     when he asked for that), she texts him once.
  2. The bell: agenda.read() marks those appointments with "ping", and the call page draws a bell next to them.
  3. Reminders outside the calendar: "remind me at 3 to …": she texts him at that time, once.
  4. Her own notes, like his quick notes (H105): HQ/notes-donna.md in the workspace (the agent's id in the name),
     one line per note. A few times a day, in the day, while she has notes, she looks at them with the day ahead
     and texts him only when one is worth bringing up now (initiative; at most INITIATIVE_MAX a day).

Kept in the workspace's HQ/direct-line/pings.json (synced to the other computer; off GitHub, since it holds his
appointment titles). Every minute, on the main, tick.py's direct_watch() calls watch(): what's due is marked sent
first, then each text starts detached (direct_line.py text appt|remind FACTS, or direct_line.py initiative).

    python3 routine/pings.py list                        the picked appointments, the reminders, her notes
    python3 routine/pings.py appt on  "ID or words" [--before N]   ping him when it starts (N minutes before)
    python3 routine/pings.py appt off "ID or words"      stop pinging that one
    python3 routine/pings.py remind "WHEN" "TEXT"        WHEN: in 20 minutes, today 15:00, tomorrow 9:30,
                                                         friday 15:00, 2026-10-14 15:00
    python3 routine/pings.py cancel N                    cancel reminder N
    python3 routine/pings.py note "TEXT"                 add a note to her own list
    python3 routine/pings.py note-clear "ID or words"    remove one of her notes
    python3 routine/pings.py due                         what would be texted now (nothing is sent)

H125 (14 October 2026, call at 11:59, Pepper): her watch list, "let me know when …". In his words: "So hypothetically
if i say hey i expect a package, can you keep an eye out on my email and let me know if i get some update on it" and
"if in the future i also want to ask her for example to let me know if it will rain later today (just example) then
the second solution would be better fitted". One list in pings.json (`watches`): each watch says where to look
(KINDS: mail, weather; a new kind is a new name here plus the check that reads it), what to look for, until when.
No routine of its own: the checks that already run read the list. The hourly mail check gets the open mail watches
in its instructions and runs `match N` on a mail that fits; the weather look (H120, weather.py) checks the open
weather watches, every 30 minutes while one is open (five while the rain alert is on, H196). A match is texted by the next minute's watch(). A watch ends
when it's answered (weather: the first match; mail: a match that answers it, like "delivered"), when its time is
up, or when he says so (unwatch); she texts each end.

    python3 routine/pings.py watch mail "WHAT" [--until WHEN] [--once]
                                            a mail about WHAT; every one until WHEN (default 7 days), --once: the first
    python3 routine/pings.py watch weather "rain|dry|sun|below N|above N" [--until WHEN] [--every]
                                            when the forecast shows it before WHEN (default the end of today);
                                            ends at the first match, --every: each new time it shows
    python3 routine/pings.py unwatch N [--quiet]     he says so; she texts that it stopped (--quiet: not, when she's
                                                     already answering him in her chat)
    python3 routine/pings.py match N "FACTS" [--key K] [--answers]   the mail check: a mail fits watch N

H212 (19 October 2026, call at 10:57, Pepper): his own times out, for the weather. In his words: "Another way is to
tell her, hey, from this time to this time, let me know. Whether that's a one-time thing or every day. Until it
changes, of course." Kept in pings.json (`outs`); weather.py reads them next to his calendar.

    python3 routine/pings.py out "14:00-18:00" [--every-day] [--on WHEN]   he's out then (once: today, or WHEN:
                                            tomorrow, friday, 2026-10-20; --every-day: until he changes it)
    python3 routine/pings.py out-stop N|all          he changes it

H211 (19 October 2026, call at 10:57, Pepper): nudge until done. In his words: "I only like actually the nudge me
until I say done." and "I want it to feel humanized. I want the connection to be there. I don't want this to be a
robot telling me its estimates. ... Just have her guess it and that's it." Kept in pings.json (`nudges`). From its
start she texts him about it now and then, how often from how much it matters (MATTERS: little about once a day,
normal about twice, much about every three hours) and stepping up close to the deadline; never at night (his
Sleep block, and only between NUDGE_DAY's hours). Her texts never say how often or when the next one comes. It
stops when he says it's done (a call, her chat, or Done in the app); later pauses it.

    python3 routine/pings.py nudge "WHEN" "TEXT" [--why "his reason"] [--matters little|normal|much] [--deadline WHEN]
                                            WHEN: the first nudge (now, tomorrow 9:00, wednesday 9:00, …)
    python3 routine/pings.py nudge-done N|"words"    he says it's done
    python3 routine/pings.py nudge-later N|"words" [WHEN]   quiet until WHEN (default: tomorrow morning)
"""
from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import hqpaths  # noqa: E402

FMT = "%Y-%m-%d %H:%M"
LATE = 15 * 60  # a ping whose start passed longer ago than this (HQ was off) is dropped, not sent late
REMIND_LATE = 6 * 3600  # a reminder this late is still sent, saying so; later than this it's dropped
KEEP_SENT = 30  # sent reminders kept, for looking back
INITIATIVE_DAY = (9, 21)  # her own look at her notes: only in the day
INITIATIVE_EVERY = 3 * 3600
INITIATIVE_MAX = 2  # texts a day from her own initiative, at most
KINDS = ("mail", "weather")  # H125: where a watch can look; more can follow
WATCH_DAYS = {"mail": 7}  # a watch without --until: mail for 7 days, weather until the end of today
KEEP_ENDED = 30  # ended watches kept, for looking back
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def agent_id() -> str:
    return os.environ.get("HQ_DIRECT_AGENT", "donna")


def folder() -> Path:
    return Path(os.environ.get("HQ_DIRECT_DIR") or os.path.join(hqpaths.DATA, "direct-line"))


def data_file() -> Path:
    return folder() / "pings.json"


def notes_file() -> Path:
    return Path(os.environ.get("HQ_AGENT_NOTES") or os.path.join(hqpaths.DATA, f"notes-{agent_id()}.md"))


def calendar_file() -> Path:
    return Path(os.environ.get("HQ_CALENDAR_FILE") or os.path.join(hqpaths.DATA, "calendar.json"))


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf8"))
    except (OSError, ValueError):
        return default


class _Lock:
    def __enter__(self):
        folder().mkdir(parents=True, exist_ok=True)
        # H152: "a", not "w": opening with "w" empties the file, which counts as a change, so the sync sent the
        # lock over every minute. The lock file is also left out of the sync (sync.IGNORE_WORKSPACE).
        self.f = open(folder() / ".pings.lock", "a")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def read() -> dict:
    s = _read_json(data_file(), {})
    if not isinstance(s, dict):
        s = {}
    s.setdefault("appointments", {})
    s.setdefault("reminders", [])
    s.setdefault("initiative", {})
    s.setdefault("watches", [])
    return s


def _write(s: dict) -> None:
    path = data_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    os.replace(tmp, path)


def _ts(iso: str) -> float:
    try:
        d = dt.datetime.fromisoformat(iso)
        return (d if d.tzinfo else d.astimezone()).timestamp()
    except (TypeError, ValueError):
        return 0.0


# -- 1 and 2: appointments ----------------------------------------------------------------------

def events() -> list[dict]:
    return [e for e in _read_json(calendar_file(), {}).get("events") or [] if isinstance(e, dict)]


def find_events(words: str, evs: list[dict] | None = None, now: float | None = None) -> list[dict]:
    """By its id, else every appointment still to come whose title has all the words (a date like 2026-10-14 or a
    time like 15:00 among the words narrows it to that start)."""
    evs = events() if evs is None else evs
    words = (words or "").strip()
    hit = [e for e in evs if e.get("id") == words]
    if hit:
        return hit
    t = now or time.time()
    parts = words.lower().split()
    date = next((p for p in parts if re.fullmatch(r"\d{4}-\d\d-\d\d", p)), "")
    hm = next((p for p in parts if re.fullmatch(r"\d{1,2}:\d\d", p)), "")
    rest = [p for p in parts if p not in (date, hm)]
    out = []
    for e in evs:
        if e.get("all_day") or _ts(e.get("start", "")) < t - LATE:
            continue
        if date and not e.get("start", "").startswith(date):
            continue
        if hm and e.get("start", "")[11:16] != hm.zfill(5):
            continue
        if rest and not all(p in e.get("title", "").lower() for p in rest):
            continue
        out.append(e)
    return out


def appt_on(e: dict, before: int = 0, by: str = "") -> dict:
    with _Lock():
        s = read()
        s["appointments"][e["id"]] = {"title": e.get("title", ""), "start": e.get("start", ""),
                                      "before": max(0, int(before)), "added": time.strftime(FMT), "by": by}
        _write(s)
    return s["appointments"][e["id"]]


def appt_off(event_id: str) -> bool:
    with _Lock():
        s = read()
        gone = s["appointments"].pop(event_id, None)
        if gone is not None:
            _write(s)
    return gone is not None


def pinged() -> set[str]:
    """The appointments that will get a ping (for the bell)."""
    return {k for k, v in read()["appointments"].items() if not v.get("sent")}


# -- 3: reminders --------------------------------------------------------------------------------

def when(words: str, now: dt.datetime | None = None) -> dt.datetime:
    """'in 20 minutes', 'in 2 hours', 'today 15:00', 'at 15:00', '15:00', 'tomorrow 9:30', 'friday 15:00',
    '2026-10-14 15:00' to a local time (minutes). ValueError when it can't be read."""
    now = (now or dt.datetime.now()).replace(second=0, microsecond=0)
    s = " ".join(str(words).lower().split()).replace(".", ":")
    m = re.fullmatch(r"in (\d+) ?(d|day|days)", s)
    if m:
        return now + dt.timedelta(days=int(m.group(1)))
    if s in ("today", "tonight", "end of today", "end of the day"):
        return now.replace(hour=23, minute=0) if now.hour < 23 else now.replace(hour=23, minute=59)
    if s == "tomorrow":
        return (now + dt.timedelta(days=1)).replace(hour=23, minute=0)
    m = re.fullmatch(r"in (\d+) ?(m|min|mins|minute|minutes|h|hr|hrs|hour|hours)", s)
    if m:
        n = int(m.group(1))
        return now + (dt.timedelta(hours=n) if m.group(2).startswith("h") else dt.timedelta(minutes=n))
    m = re.fullmatch(r"(\d{4}-\d\d-\d\d) (\d{1,2}):(\d\d)", s)
    if m:
        return dt.datetime.strptime(f"{m.group(1)} {int(m.group(2)):02d}:{m.group(3)}", FMT)
    m = re.fullmatch(r"(?:(today|tomorrow|(?:next )?(?:" + "|".join(DAYS) + r")) )?(?:at )?(\d{1,2}):(\d\d)", s)
    if not m:
        raise ValueError("When? in 20 minutes, today 15:00, tomorrow 9:30, friday 15:00 or 2026-10-14 15:00.")
    day, h, mi = m.group(1), int(m.group(2)), int(m.group(3))
    if h > 23 or mi > 59:
        raise ValueError(f"{h}:{mi:02d} isn't a time of day.")
    base = now.replace(hour=h, minute=mi)
    if not day:
        return base if base > now else base + dt.timedelta(days=1)  # a bare time that passed today: tomorrow
    if day == "today":
        return base
    if day == "tomorrow":
        return base + dt.timedelta(days=1)
    ahead = (DAYS.index(day.replace("next ", "")) - now.weekday()) % 7
    if ahead == 0 and (base <= now or day.startswith("next ")):
        ahead = 7
    return base + dt.timedelta(days=ahead)


def remind(at: dt.datetime, text: str, by: str = "", why: str = "remind") -> dict:
    """why: remind (he asked for it), or nightly (H169: the nightly run's line for the morning)."""
    text = " ".join(str(text).split())[:500]
    if not text:
        raise ValueError("What should she remind him of?")
    with _Lock():
        s = read()
        n = max([int(r.get("n") or 0) for r in s["reminders"]] + [int(s.get("last_n") or 0)]) + 1
        r = {"n": n, "at": at.strftime(FMT), "text": text, "added": time.strftime(FMT), "by": by}
        if why != "remind":
            r["why"] = why
        s["reminders"].append(r)
        s["last_n"] = n
        _write(s)
    return r


def cancel(n: int) -> bool:
    with _Lock():
        s = read()
        keep = [r for r in s["reminders"] if not (int(r.get("n") or 0) == n and not r.get("sent"))]
        if len(keep) == len(s["reminders"]):
            return False
        s["reminders"] = keep
        _write(s)
    return True


# -- 4: her own notes ----------------------------------------------------------------------------

def _notes():
    sys.path.insert(0, str(ROOT / "app"))
    import notes as _n  # the same file shape as his quick notes (H105)
    return _n


NOTES_HEAD = ("# {name}'s notes\n\n"
              "> **Private.** Her own list (H124), like the quick notes: what she keeps an eye on for him. She may "
              "text him about one on her own initiative; once it's done or gone through, its line is removed.\n\n"
              "## Notes\n\n")


def agent_name() -> str:
    sys.path.insert(0, str(ROOT / "app"))
    try:
        import agents as _a  # app/agents.py, stdlib only
        return _a.find(Path(hqpaths.FOLDER), agent_id())["name"]
    except Exception:
        return agent_id().capitalize()


def her_notes() -> list[dict]:
    if not notes_file().exists():
        return []
    return _notes().items(notes_file())


def note_add(text: str) -> dict | None:
    n = _notes()
    path = notes_file()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(NOTES_HEAD.replace("{name}", agent_name()))
    return n.add(text, path)


def note_clear(words: str) -> list[dict]:
    """By its id, else the notes that have all the words. Clears only when exactly one matches."""
    items = her_notes()
    hit = [i for i in items if i["id"] == words.strip()]
    if not hit:
        parts = words.lower().split()
        hit = [i for i in items if parts and all(p in i["text"].lower() for p in parts)]
    if len(hit) == 1:
        _notes().clear(hit[0]["id"], notes_file())
    return hit


# -- H125: her watch list ("let me know when …") ---------------------------------------------------------------

WEATHER_LOOKS = ("rain", "dry", "sun", "below", "above")


def weather_look(words: str) -> str:
    """'rain', 'dry', 'sun', 'below 5', 'above 20' (°C); ValueError otherwise."""
    w = " ".join(str(words).lower().replace("°c", "").replace("degrees", "").split())
    m = re.fullmatch(r"(below|above) (-?\d+)", w)
    if m:
        return f"{m.group(1)} {int(m.group(2))}"
    w = {"rains": "rain", "raining": "rain", "showers": "rain", "sunny": "sun", "sunshine": "sun", "dries up": "dry",
         "stops raining": "dry"}.get(w, w)
    if w in ("rain", "dry", "sun"):
        return w
    raise ValueError("A weather watch looks for rain, dry, sun, below N or above N (°C).")


def watch_add(kind: str, what: str, until: dt.datetime | None = None, once: bool | None = None, by: str = "",
              now: dt.datetime | None = None, alert: bool = False) -> dict:
    """ALERT (H161): the rain alert switch in the app's weather (weather.rain_alert); the weather look checks it only
    a few hours ahead, every five minutes, and follows that one shower (H196)."""
    if kind not in KINDS:
        raise ValueError(f"A watch looks in {' or '.join(KINDS)}.")
    now = (now or dt.datetime.now()).replace(second=0, microsecond=0)
    what = weather_look(what) if kind == "weather" else " ".join(str(what).split())[:300]
    if not what:
        raise ValueError("What should she look out for?")
    if until is None:
        until = now + dt.timedelta(days=WATCH_DAYS[kind]) if kind in WATCH_DAYS else when("today", now)
    if until <= now:
        raise ValueError(f"{until.strftime(FMT)} has passed already.")
    with _Lock():
        s = read()
        n = max([int(w.get("n") or 0) for w in s["watches"]] + [int(s.get("last_watch") or 0)]) + 1
        w = {"n": n, "kind": kind, "what": what, "until": until.strftime(FMT),
             "once": (kind == "weather") if once is None else bool(once), "added": now.strftime(FMT), "by": by,
             "matches": []} | ({"alert": True} if alert else {})
        s["watches"].append(w)
        s["last_watch"] = n
        _write(s)
    return w


def open_watches(kind: str | None = None, s: dict | None = None, now: float | None = None) -> list[dict]:
    """The watches still open (not ended, time not up), of KIND or all."""
    t = now or time.time()
    s = read() if s is None else s
    return [w for w in s["watches"] if not w.get("ended") and (kind is None or w.get("kind") == kind)
            and _local_ts(w.get("until", "")) > t]


def _local_ts(at: str) -> float:
    try:
        return time.mktime(time.strptime(at, FMT))
    except (TypeError, ValueError):
        return 0.0


def _find_watch(s: dict, n: int) -> dict | None:
    return next((w for w in s["watches"] if int(w.get("n") or 0) == n), None)


def match(n: int, facts: str, key: str = "", answers: bool = False, now: float | None = None) -> str:
    """A check found something for watch N: kept as a match to text (by the next minute's watch()). The same KEY
    (a mail's link, a weather look's finding) is kept once. Returns 'new', 'seen' or why it can't."""
    t = now or time.time()
    facts = str(facts).strip()[:1200]
    if not facts:
        return "no facts"
    with _Lock():
        s = read()
        w = _find_watch(s, n)
        if not w:
            return f"no watch {n}"
        if w.get("ended") or _local_ts(w.get("until", "")) <= t:
            return f"watch {n} has ended"
        key = key or facts
        if any(m.get("key") == key for m in w["matches"]):
            return "seen"
        w["matches"].append({"key": key, "at": time.strftime(FMT, time.localtime(t)), "facts": facts,
                             "answers": bool(answers or w.get("once")), "texted": ""})
        _write(s)
    return "new"


def unwatch(n: int, quiet: bool = False, now: float | None = None) -> dict | None:
    """He says so: the watch ends; she texts that it stopped unless QUIET."""
    t = now or time.time()
    with _Lock():
        s = read()
        w = _find_watch(s, n)
        if not w or w.get("ended"):
            return None
        w["ended"] = {"at": time.strftime(FMT, time.localtime(t)), "why": "he said so", "texted": "" if not quiet else "quiet"}
        _write(s)
    return w


# -- H212: his own times out, for the weather --------------------------------------------------------

def out_range(words: str) -> tuple[str, str]:
    """'14:00-18:00', '14 to 18', '9:30 until 12' to ('14:00', '18:00'); 24-hour times. ValueError otherwise."""
    s = " ".join(str(words).lower().replace(".", ":").split())
    m = re.fullmatch(r"(?:from |between )?(\d{1,2})(?::(\d\d))? ?(?:-|to|until|till|and|tot) ?(\d{1,2})(?::(\d\d))?", s)
    if not m:
        raise ValueError("Which times? Like 14:00-18:00 (24-hour).")
    a, b = (int(m.group(1)), int(m.group(2) or 0)), (int(m.group(3)), int(m.group(4) or 0))
    if a[0] > 23 or b[0] > 24 or a[1] > 59 or b[1] > 59 or b <= a or b > (24, 0):
        raise ValueError("The times don't make a span in one day; give them as 24-hour times, like 14:00-18:00.")
    return f"{a[0]:02d}:{a[1]:02d}", f"{b[0]:02d}:{b[1]:02d}"


def out_add(span: str, daily: bool = False, on: str = "", by: str = "", now: dt.datetime | None = None) -> dict:
    """He tells her when he's out ("let me know between 2 and 6"): the weather texts him for those hours (H212).
    DAILY: every day until he changes it; else once, ON (a day: today, tomorrow, friday, 2026-10-20; default today,
    or tomorrow when today's span has passed already)."""
    now = (now or dt.datetime.now()).replace(second=0, microsecond=0)
    a, b = out_range(span)
    day = None
    if not daily:
        if on:
            o = " ".join(str(on).lower().split())
            day = (dt.datetime.strptime(o, "%Y-%m-%d") if re.fullmatch(r"\d{4}-\d\d-\d\d", o)
                   else when(f"{o} 00:00", now)).date()
        else:
            day = now.date() if f"{now:%H:%M}" < b else now.date() + dt.timedelta(days=1)
        if day < now.date():
            raise ValueError(f"{day} has passed already.")
    with _Lock():
        s = read()
        outs = s.setdefault("outs", [])
        n = max([int(o.get("n") or 0) for o in outs] + [int(s.get("last_out") or 0)]) + 1
        o = {"n": n, "from": a, "to": b, "daily": bool(daily), "on": "" if daily else day.isoformat(),
             "added": now.strftime(FMT), "by": by}
        outs.append(o)
        s["last_out"] = n
        _write(s)
    return o


def out_stop(which: str) -> list[dict]:
    """He changes it: N, or all. Returns what was stopped."""
    with _Lock():
        s = read()
        outs = s.get("outs") or []
        gone = [o for o in outs if which == "all" or str(o.get("n")) == str(which)]
        if gone:
            s["outs"] = [o for o in outs if o not in gone]
            _write(s)
    return gone


def outs_on(day: dt.date, s: dict | None = None) -> list[dict]:
    """His own times out on DAY (every-day ones and that day's once ones)."""
    s = read() if s is None else s
    return [o for o in s.get("outs") or [] if o.get("daily") or o.get("on") == day.isoformat()]


def _out_says(o: dict) -> str:
    return f"{o['from']} to {o['to']}, " + ("every day" if o.get("daily") else f"on {o['on']}")


def _watch_says(w: dict) -> str:
    if w.get("alert"):
        return "rain coming up (the rain alert he switched on in the app)"
    return (f"a mail about {w['what']}" if w["kind"] == "mail" else
            {"rain": "rain", "dry": "dry weather", "sun": "sun"}.get(w["what"], f"the temperature {w['what']} °C")
            if w["kind"] == "weather" else w["what"])


def _watch_due(s: dict, t: float) -> list[tuple[str, str]]:
    """Marks in S what's to text now about the watches and returns [(why, facts)]: matches not texted yet (why
    watch), and ends not texted yet (why watch-end: time up, or he said so)."""
    out = []
    stamp = time.strftime(FMT, time.localtime(t))
    for w in s["watches"]:
        if w.get("ended") and w["ended"].get("texted"):
            continue
        asked = (f"He asked you to let him know about {_watch_says(w)} (watch {w['n']}, "
                 + ("on until he switches it off)." if w.get("alert") else f"open until {w['until']})."))
        for m in w["matches"]:
            if m.get("texted") or w.get("ended"):
                continue
            m["texted"] = stamp
            facts = f"{asked}\nWhat came: {m['facts']}"
            if m.get("answers"):
                w["ended"] = {"at": stamp, "why": "answered", "texted": stamp}
                facts += "\nThis answers it: you stop watching for it now; say so in passing."
            elif w.get("alert"):
                facts += "\nThe rain alert stays on until he switches it off; don't mention the switch."
            else:
                facts += "\nYou keep watching until then."
            out.append(("watch", facts))
        if w.get("ended") and not w["ended"].get("texted"):
            w["ended"]["texted"] = stamp
            out.append(("watch-end", f"{asked}\nHe asked you to stop watching for it: say it's stopped."))
        elif not w.get("ended") and _local_ts(w.get("until", "")) <= t:
            got = len(w["matches"])
            w["ended"] = {"at": stamp, "why": "time up", "texted": stamp}
            if w.get("kind") == "weather" and _asleep(t):
                continue  # H212: asleep she says nothing; a weather watch whose time is up at night ends quietly
            out.append(("watch-end", f"{asked}\nIts time is up. "
                        + (f"Nothing came for it." if not got else f"{got} update(s) came, all texted already.")
                        + " Say you've stopped watching for it."))
    ended = [w for w in s["watches"] if w.get("ended")]
    s["watches"] = [w for w in s["watches"] if not w.get("ended")] + ended[-KEEP_ENDED:]
    return out


def _asleep(t: float) -> bool:
    """H212: he's asleep (weather.asleep: his calendar's Sleep block, else the night hours)."""
    try:
        sys.path.insert(0, str(ROOT / "app"))
        import weather as _w
        return _w.asleep_at(t)
    except Exception:
        return False


def mail_watch_text(now: float | None = None) -> str:
    """For the hourly mail check's instructions: the open mail watches, one line each, or that there are none."""
    ws = open_watches("mail", now=now)
    if not ws:
        return "(no open mail watches)"
    return "\n".join(f"- Watch {w['n']}: {w['what']} (open until {w['until']}"
                     + (", the first matching mail answers it" if w.get("once") else "") + ")" for w in ws)


def _watch_line(w: dict) -> str:
    return (f"- watch {w['n']} · {w['kind']} · {w['what']} · "
            + ("on until he switches it off" if w.get("alert") else f"until {w['until']}")
            + (" · ends at the first match" if w.get("once") else "")
            + (" · the rain alert from the app" if w.get("alert") else "")
            + (f" · {len(w['matches'])} match(es)" if w.get("matches") else "")
            + (f" · ended {w['ended']['at']} ({w['ended']['why']})" if w.get("ended") else ""))


def watch_items() -> list[dict]:
    """For the notes sheet in the app: the open watches in plain words. The rain alert has no until (H188): it's on.
    H212: his own times out come after them, as the rain for when he's out."""
    return [{"n": w["n"], "kind": w["kind"], "text": "Rain alerts on" if w.get("alert") else f"Watching for {_watch_says(w)}",
             "until": "" if w.get("alert") else w["until"],
             "matches": len(w.get("matches") or [])} for w in open_watches()] + \
        [{"n": o["n"], "kind": "out", "text": f"The rain for when you're out, {_out_says(o)}", "until": "", "matches": 0}
         for o in read().get("outs") or []]


# -- H211: nudge until done -------------------------------------------------------------------------

# How often she nudges, by how much it matters: little about once a day, normal about twice, much about every three
# hours. Close to the deadline it steps up one; past it, much. Never at night, never by the clock: a little give.
NUDGE_GAP = {"little": 24 * 3600, "normal": 6 * 3600, "much": 3 * 3600}
NUDGE_LEVELS = ("little", "normal", "much")
NUDGE_DAY = (9, 21)  # only in the day, also when he has no Sleep block
NUDGE_CLOSE = 24 * 3600  # a deadline this close steps up one
KEEP_DONE_NUDGES = 30


def nudge_level(words: str) -> str:
    w = " ".join(str(words or "normal").lower().split())
    w = {"low": "little", "small": "little", "a little": "little", "medium": "normal", "high": "much", "often": "much",
         "a lot": "much", "important": "much"}.get(w, w)
    if w not in NUDGE_LEVELS:
        raise ValueError("How much it matters: little, normal or much.")
    return w


def nudge_ok(t: float) -> bool:
    """A moment she may nudge: in the day, and not while he's asleep."""
    return NUDGE_DAY[0] <= time.localtime(t).tm_hour < NUDGE_DAY[1] and not _asleep(t)


def _next_ok(t: float) -> float:
    """T, or the first moment after it she may nudge (stepping a quarter of an hour, at most two days on)."""
    for _ in range(2 * 96):
        if nudge_ok(t):
            return t
        t += 900
    return t


def nudge_gap(n: dict, t: float) -> float:
    lv = NUDGE_LEVELS.index(n.get("matters") or "normal")
    dl = _local_ts(n.get("deadline") or "")
    if dl and t >= dl:
        lv = 2
    elif dl and dl - t <= NUDGE_CLOSE:
        lv = min(2, lv + 1)
    gap = NUDGE_GAP[NUDGE_LEVELS[lv]]
    give = ((int(n.get("n") or 0) * 7 + int(n.get("count") or 0) * 13) % 41 - 20) * 60  # -20 to +20 minutes
    return max(3600, gap + give)


def nudge_add(start: dt.datetime, text: str, reason: str = "", matters: str = "normal", deadline: dt.datetime | None = None,
              by: str = "", now: dt.datetime | None = None) -> dict:
    """START: the first nudge (or the first moment after it she may). REASON: why it matters, in his words."""
    text = " ".join(str(text).split())[:500]
    if not text:
        raise ValueError("What should she nudge him about?")
    matters = nudge_level(matters)
    now = (now or dt.datetime.now()).replace(second=0, microsecond=0)
    if deadline is not None and deadline <= now:
        raise ValueError(f"{deadline.strftime(FMT)} has passed already.")
    first = _next_ok(max(start, now).timestamp())
    with _Lock():
        s = read()
        ns = s.setdefault("nudges", [])
        n = max([int(x.get("n") or 0) for x in ns] + [int(s.get("last_nudge") or 0)]) + 1
        x = {"n": n, "text": text, "reason": " ".join(str(reason).split())[:600], "matters": matters,
             "start": start.strftime(FMT), "deadline": deadline.strftime(FMT) if deadline else "",
             "next": time.strftime(FMT, time.localtime(first)), "count": 0, "added": now.strftime(FMT), "by": by}
        ns.append(x)
        s["last_nudge"] = n
        _write(s)
    return x


def open_nudges(s: dict | None = None) -> list[dict]:
    s = read() if s is None else s
    return [x for x in s.get("nudges") or [] if not x.get("done")]


def find_nudges(words: str, s: dict | None = None) -> list[dict]:
    """By its number, else the open nudges that have all the words."""
    ns = open_nudges(s)
    w = str(words or "").strip()
    if w.isdigit():
        return [x for x in ns if int(x.get("n") or 0) == int(w)]
    parts = w.lower().split()
    return [x for x in ns if parts and all(p in (x["text"] + " " + x.get("reason", "")).lower() for p in parts)]


def _change_nudge(words: str, change) -> list[dict]:
    with _Lock():
        s = read()
        hit = find_nudges(words, s)
        if len(hit) == 1:
            change(hit[0])
            s["nudges"] = [x for x in s["nudges"] if not x.get("done")] + \
                [x for x in s["nudges"] if x.get("done")][-KEEP_DONE_NUDGES:]
            _write(s)
    return hit


def nudge_done(words: str, now: float | None = None) -> list[dict]:
    """He says it's done (by text, on any call, or in the app): no more nudges. Changes only when exactly one fits."""
    stamp = time.strftime(FMT, time.localtime(now or time.time()))
    return _change_nudge(words, lambda x: x.update(done=stamp))


def nudge_later(words: str, until: dt.datetime | None = None, now: float | None = None) -> list[dict]:
    """'Later' or 'tomorrow': quiet until UNTIL (default: the next morning she may nudge)."""
    t = now or time.time()
    if until is None:
        d = dt.datetime.fromtimestamp(t) + dt.timedelta(days=1)
        at = _next_ok(d.replace(hour=NUDGE_DAY[0], minute=0, second=0, microsecond=0).timestamp())
    else:
        at = _next_ok(until.timestamp())
    return _change_nudge(words, lambda x: x.update(next=time.strftime(FMT, time.localtime(at)), paused=True))


def _nudge_due(s: dict, t: float) -> list[tuple[str, str]]:
    """Marks in S the nudges to text now and returns [(why, facts)]. One at night is moved to the morning, quietly."""
    out = []
    stamp = time.strftime(FMT, time.localtime(t))
    for x in open_nudges(s):
        at = _local_ts(x.get("next") or "")
        if not at or at > t:
            continue
        if not nudge_ok(t):
            x["next"] = time.strftime(FMT, time.localtime(_next_ok(t)))
            continue
        x["count"] = int(x.get("count") or 0) + 1
        x["last"] = stamp
        x.pop("paused", None)
        x["next"] = time.strftime(FMT, time.localtime(_next_ok(t + nudge_gap(x, t))))
        days = int((t - _local_ts(x.get("start") or stamp)) // 86400)
        facts = [f"Nudge him, until he says it's done: {x['text']}"]
        if x.get("reason"):
            facts.append(f"Why it matters, in his words: {x['reason']}")
        dl = _local_ts(x.get("deadline") or "")
        if dl:
            facts.append("The deadline has passed." if dl <= t else
                         f"It has a deadline: {dt.datetime.fromtimestamp(dl):%A %H:%M}" + (" (close now)" if dl - t <= NUDGE_CLOSE else ""))
        facts.append("This is your first nudge about it." if x["count"] == 1 else
                     f"You've nudged him about it before; it's still open" + (f", {days} days now." if days >= 2 else "."))
        out.append(("nudge", "\n".join(facts)))
    return out


def nudge_items() -> list[dict]:
    """For the app: the open nudges, each with its bell (no numbers of how often: that's hers)."""
    return [{"n": x["n"], "text": x["text"], "paused": bool(x.get("paused"))} for x in open_nudges()]


def _nudge_line(x: dict) -> str:
    return (f"- nudge {x['n']} · {x['text']} · matters {x.get('matters', 'normal')}"
            + (f" · deadline {x['deadline']}" if x.get("deadline") else "")
            + (f" · why: {x['reason']}" if x.get("reason") else "")
            + (f" · done {x['done']}" if x.get("done") else
               (" · paused" if x.get("paused") else "") + f" · next {x.get('next', '')}")
            + (f" · nudged {x['count']}x" if x.get("count") else ""))


# -- every minute: what's due ---------------------------------------------------------------------

def _say_at(start: str) -> str:
    try:
        d = dt.datetime.fromisoformat(start)
        return d.strftime("%H:%M")
    except ValueError:
        return start


def due(now: float | None = None, s: dict | None = None, evs: list[dict] | None = None) -> list[tuple[str, str, str]]:
    """[(why, key, facts)] that are due now; why is appt or remind. Nothing is changed."""
    t = now or time.time()
    s = read() if s is None else s
    evs = events() if evs is None else evs
    by_id = {e.get("id"): e for e in evs}
    out = []
    for k, p in s["appointments"].items():
        if p.get("sent"):
            continue
        e = by_id.get(k) or {}
        start = e.get("start") or p.get("start", "")  # the calendar's latest read wins: a moved appointment moves
        at = _ts(start)
        if not at:
            continue
        before = int(p.get("before") or 0)
        if at - before * 60 <= t <= at + LATE:
            title = e.get("title") or p.get("title", "")
            left = round((at - t) / 60)
            facts = [f"Appointment: {title}", f"Starts: {_say_at(start)}" + (f" (in {left} minutes)" if left > 0 else " (now)")]
            if e.get("where"):
                facts.append(f"Where: {e['where']}")
            if e.get("notes"):
                facts.append(f"Its notes: {e['notes'][:300]}")
            out.append(("appt", k, "\n".join(facts)))
    for r in s["reminders"]:
        if r.get("sent"):
            continue
        try:
            at = time.mktime(time.strptime(r["at"], FMT))
        except (KeyError, ValueError):
            continue
        if at <= t:
            late = t - at
            why = r.get("why") or "remind"
            if why == "nightly":  # H169: not a reminder he asked for; late doesn't matter
                out.append((why, str(r.get("n")), f"From last night's check: {r.get('text', '')}"))
                continue
            facts = f"Reminder he asked for: {r.get('text', '')}\nAsked for: {r['at'][11:]}"
            if late > 10 * 60:
                facts += f" (it's {int(late // 60)} minutes late: HQ couldn't send it on time; say so)"
            out.append(("remind", str(r.get("n")), facts))
    return out


def initiative_due(now: float | None = None, s: dict | None = None) -> bool:
    """Her own look at her notes: in the day, every INITIATIVE_EVERY, while she has notes, under INITIATIVE_MAX
    texts today."""
    if os.environ.get("HQ_INITIATIVE", "1") == "0":
        return False
    t = now or time.time()
    s = read() if s is None else s
    d = dt.datetime.fromtimestamp(t)
    if not INITIATIVE_DAY[0] <= d.hour < INITIATIVE_DAY[1]:
        return False
    i = s.get("initiative") or {}
    if i.get("day") == d.strftime("%Y-%m-%d") and int(i.get("texts") or 0) >= INITIATIVE_MAX:
        return False
    if t - float(i.get("looked") or 0) < INITIATIVE_EVERY:
        return False
    return bool(her_notes())


def watch(now: float | None = None, spawn=None, dry: bool = False) -> list[tuple[str, str]]:
    """From tick.py on the main, every minute: mark what's due as sent, then start each text. Also prunes pings
    for appointments well over, and old sent reminders. Returns [(why, facts)]."""
    t = now or time.time()
    out: list[tuple[str, str]] = []
    with _Lock():
        s = read()
        before = json.dumps(s, sort_keys=True)
        evs = events()
        for why, key, facts in due(t, s, evs):
            if why == "appt":
                s["appointments"][key]["sent"] = time.strftime(FMT, time.localtime(t))
            else:
                for r in s["reminders"]:
                    if str(r.get("n")) == key:
                        r["sent"] = time.strftime(FMT, time.localtime(t))
                        late = t - time.mktime(time.strptime(r["at"], FMT))
                        if late > REMIND_LATE:
                            r["dropped"] = True
                            facts = ""
            if facts:
                out.append((why, facts))
        # an appointment over a day ago (sent or missed) goes; so does a ping on one that's no longer anywhere
        for k, p in list(s["appointments"].items()):
            at = _ts(p.get("start", ""))
            if at and at < t - 86400:
                s["appointments"].pop(k)
        out += _watch_due(s, t)  # H125
        out += _nudge_due(s, t)  # H211
        today = time.strftime("%Y-%m-%d", time.localtime(t))
        if any(not o.get("daily") and o.get("on", "") < today for o in s.get("outs") or []):  # H212: a day gone by
            s["outs"] = [o for o in s["outs"] if o.get("daily") or o.get("on", "") >= today]
        sent = [r for r in s["reminders"] if r.get("sent")]
        s["reminders"] = [r for r in s["reminders"] if not r.get("sent")] + sent[-KEEP_SENT:]
        if initiative_due(t, s):
            s["initiative"] = {**(s.get("initiative") or {}), "looked": t}
            out.append(("initiative", ""))
        # H152: written only when something changed. It was written every minute, so the file was nearly always
        # on its way to the other computer, and a crash or a write there in between made a conflict copy.
        if not dry and json.dumps(s, sort_keys=True) != before:
            _write(s)
    if not dry:
        for why, facts in out:
            (spawn or _spawn)(why, facts)
    return out


def initiative_sent(now: float | None = None) -> None:
    """direct_line.py initiative calls this when she did text (not when she stayed quiet)."""
    t = now or time.time()
    day = time.strftime("%Y-%m-%d", time.localtime(t))
    with _Lock():
        s = read()
        i = s.get("initiative") or {}
        i["texts"] = (int(i.get("texts") or 0) if i.get("day") == day else 0) + 1
        i["day"] = day
        i["last_text"] = t
        s["initiative"] = i
        _write(s)


def initiative_facts(now: float | None = None) -> str:
    """What she looks at when she decides on her own: her notes, the time, the rest of today and tomorrow."""
    t = now or time.time()
    d = dt.datetime.fromtimestamp(t)
    lines = [f"Now: {d:%A %d %B %Y, %H:%M}", "", "Your own notes (oldest first):"]
    lines += [f"- {i['when'][:16]} · {i['text']}" for i in her_notes()] or ["(none)"]
    soon = [e for e in events() if not e.get("all_day") and t - 1800 <= _ts(e.get("start", "")) <= t + 36 * 3600]
    lines += ["", "His calendar, the next day and a half:"]
    lines += [f"- {e['start'][:16].replace('T', ' ')} {e.get('title', '')}" for e in soon[:20]] or ["(nothing)"]
    i = read().get("initiative") or {}
    if i.get("last_text"):
        lines += ["", f"You last texted him on your own at {time.strftime('%H:%M', time.localtime(i['last_text']))}"
                  + (" today." if i.get("day") == d.strftime("%Y-%m-%d") else ".")]
    return "\n".join(lines)


def _spawn(why: str, facts: str) -> None:
    py = ROOT / ".venv" / "bin" / "python"
    log = ROOT / "scratch" / "direct-line.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [str(py) if py.exists() else sys.executable, str(ROOT / "app" / "direct_line.py")]
    cmd += ["initiative"] if why == "initiative" else ["text", why, facts]
    subprocess.Popen(cmd, cwd=str(ROOT), stdout=open(log, "a"), stderr=subprocess.STDOUT, start_new_session=True)


# -- the command line, for a call and her chat --------------------------------------------------------

def _appt_line(k: str, p: dict) -> str:
    return (f"- {p.get('title', '')} · {p.get('start', '')[:16].replace('T', ' ')}"
            + (f" · {p['before']} minutes before" if p.get("before") else " · when it starts")
            + (f" · sent {p['sent']}" if p.get("sent") else "") + f" · id {k}")


def listing() -> str:
    s = read()
    out = ["Appointment pings (only the ones he picked):"]
    out += [_appt_line(k, p) for k, p in s["appointments"].items()] or ["- none"]
    out += ["", "Reminders:"]
    out += [f"- {r['n']} · {r['at']} · {r['text']}" + (f" · sent {r['sent']}" if r.get("sent") else "")
            for r in s["reminders"] if not r.get("dropped")] or ["- none"]
    out += ["", "Watches (\"let me know when …\"):"]
    out += [_watch_line(w) for w in s["watches"]] or ["- none"]
    out += ["", "His own times out, for the weather (H212):"]
    out += [f"- out {o['n']} · {_out_says(o)}" for o in s.get("outs") or []] or ["- none"]
    out += ["", "Nudges until he says it's done (H211):"]
    out += [_nudge_line(x) for x in s.get("nudges") or [] if not x.get("done")] or ["- none"]
    out += ["", f"{agent_name()}'s own notes ({notes_file().relative_to(hqpaths.FOLDER) if str(notes_file()).startswith(hqpaths.FOLDER) else notes_file()}):"]
    out += [f"- {i['when'][:16]} · {i['text']} · id {i['id']}" for i in her_notes()] or ["- none"]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    by = os.environ.get("HQ_PINGS_BY", "")
    cmd = argv[0] if argv else "list"
    # H203: on the backup HQ, her reminders and notes are written by the main one (role.WRITES), like the queue.
    import role
    if cmd in role.WRITES["pings"] and not os.environ.get("HQ_ROLE_HERE") and role.is_backup():
        return role.forward("pings", list(argv), {"HQ_PINGS_BY": by} if by else None)
    if cmd == "list":
        print(listing())
    elif cmd == "appt" and len(argv) >= 3 and argv[1] in ("on", "off"):
        words = argv[2]
        before = 0
        if "--before" in argv:
            try:
                before = int(argv[argv.index("--before") + 1])
            except (IndexError, ValueError):
                print("--before takes a number of minutes.")
                return 2
        if argv[1] == "off":
            s = read()
            keys = [k for k in s["appointments"] if k == words] or [
                k for k, p in s["appointments"].items()
                if all(w in p.get("title", "").lower() for w in words.lower().split())]
            if len(keys) != 1:
                print("No ping like that." if not keys else "More than one; give the id:\n"
                      + "\n".join(_appt_line(k, s["appointments"][k]) for k in keys))
                return 1
            appt_off(keys[0])
            print(f"Off: no ping for {s['appointments'][keys[0]].get('title', '')}.")
            return 0
        hit = find_events(words)
        if len(hit) != 1:
            print("No appointment like that in the calendar's next two weeks." if not hit else
                  "More than one; give the id (or add the date or the time):\n" +
                  "\n".join(f"- {e['title']} · {e['start'][:16].replace('T', ' ')} · id {e['id']}" for e in hit[:12]))
            return 1
        e = hit[0]
        appt_on(e, before, by)
        print(f"On: she texts him {'%d minutes before' % before if before else 'when it starts'}: "
              f"{e['title']}, {e['start'][:16].replace('T', ' ')}.")
    elif cmd == "remind" and len(argv) >= 3:
        try:
            at = when(argv[1])
            if at < dt.datetime.now().replace(second=0, microsecond=0):
                raise ValueError(f"{at.strftime(FMT)} has passed already.")
            r = remind(at, " ".join(argv[2:]), by)
        except ValueError as e:
            print(e)
            return 2
        print(f"Reminder {r['n']}: {r['at']} · {r['text']}")
    elif cmd == "cancel" and len(argv) == 2 and argv[1].isdigit():
        if not cancel(int(argv[1])):
            print(f"No reminder {argv[1]} waiting.")
            return 1
        print(f"Reminder {argv[1]} cancelled.")
    elif cmd == "note" and len(argv) >= 2:
        it = note_add(" ".join(argv[1:]))
        if not it:
            print("Nothing to add.")
            return 2
        print(f"Noted: {it['text']}")
    elif cmd == "note-clear" and len(argv) >= 2:
        hit = note_clear(" ".join(argv[1:]))
        if len(hit) != 1:
            print("No note like that." if not hit else "More than one; give the id:\n"
                  + "\n".join(f"- {i['text']} · id {i['id']}" for i in hit))
            return 1
        print(f"Cleared: {hit[0]['text']}")
    elif cmd == "watch" and len(argv) >= 3:
        rest = argv[3:]
        until = None
        try:
            if "--until" in rest:
                i = rest.index("--until")
                if i + 1 >= len(rest):
                    raise ValueError("--until takes a time: today 18:00, tomorrow, in 3 days, friday 15:00.")
                until = when(rest[i + 1])
            once = True if "--once" in rest else False if "--every" in rest else None
            w = watch_add(argv[1], argv[2], until, once, by)
        except ValueError as e:
            print(e)
            return 2
        if w["kind"] == "weather":
            sys.path.insert(0, str(ROOT / "app"))
            try:
                import weather as _w
                if not _w.place():
                    print("Note: no place in me.md under **Where I am:**, so the weather can't be looked at yet.")
            except Exception:
                pass
        print(f"Watch {w['n']}: {_watch_says(w)}, until {w['until']}"
              + (" (ends at the first match)." if w["once"] else " (every match until then)."))
    elif cmd == "unwatch" and len(argv) >= 2 and argv[1].isdigit():
        w = unwatch(int(argv[1]), quiet="--quiet" in argv)
        if not w:
            print(f"No open watch {argv[1]}.")
            return 1
        print(f"Watch {w['n']} stopped: {_watch_says(w)}.")
    elif cmd == "out" and len(argv) >= 2:
        rest = argv[2:]
        try:
            on = rest[rest.index("--on") + 1] if "--on" in rest and rest.index("--on") + 1 < len(rest) else ""
            o = out_add(argv[1], daily="--every-day" in rest, on=on, by=by)
        except ValueError as e:
            print(e)
            return 2
        print(f"Out {o['n']}: {_out_says(o)}. She checks the rain for then and texts only when it rains.")
    elif cmd == "out-stop" and len(argv) == 2 and (argv[1].isdigit() or argv[1] == "all"):
        gone = out_stop(argv[1])
        if not gone:
            print(f"No times out {argv[1]}.")
            return 1
        print("Stopped: " + "; ".join(_out_says(o) for o in gone) + ".")
    elif cmd == "nudge" and len(argv) >= 3:
        rest = argv[3:]

        def opt(name: str) -> str:
            return rest[rest.index(name) + 1] if name in rest and rest.index(name) + 1 < len(rest) else ""
        words = [a for i, a in enumerate(rest) if not a.startswith("--") and not (i and rest[i - 1].startswith("--"))]
        try:
            start = dt.datetime.now() if argv[1].strip().lower() in ("now", "") else when(argv[1])
            dl = opt("--deadline")
            x = nudge_add(start, " ".join([argv[2]] + words), opt("--why"), opt("--matters") or "normal",
                          when(dl) if dl else None, by)
        except ValueError as e:
            print(e)
            return 2
        print(f"Nudge {x['n']}: {x['text']}; from {x['next']} she nudges him until he says it's done.")
    elif cmd in ("nudge-done", "nudge-later") and len(argv) >= 2:
        if cmd == "nudge-done":
            hit = nudge_done(" ".join(argv[1:]))
        else:
            try:
                hit = nudge_later(argv[1], when(" ".join(argv[2:])) if len(argv) > 2 else None)
            except ValueError as e:
                print(e)
                return 2
        if len(hit) != 1:
            print("No open nudge like that." if not hit else "More than one; give the number:\n"
                  + "\n".join(_nudge_line(x) for x in hit))
            return 1
        x = hit[0]
        print(f"Nudge {x['n']} done: no more nudges about {x['text']}." if cmd == "nudge-done" else
              f"Nudge {x['n']} paused until {x['next']}.")
    elif cmd == "match" and len(argv) >= 3 and argv[1].isdigit():
        key = argv[argv.index("--key") + 1] if "--key" in argv and argv.index("--key") + 1 < len(argv) else ""
        facts = " ".join(a for i, a in enumerate(argv[2:], 2)
                         if a != "--answers" and a != "--key" and not (i > 0 and argv[i - 1] == "--key"))
        got = match(int(argv[1]), facts, key, "--answers" in argv)
        print({"new": f"Kept for watch {argv[1]}; she texts him within a minute.",
               "seen": f"Already kept for watch {argv[1]}."}.get(got, got))
        return 0 if got in ("new", "seen") else 1
    elif cmd == "due":
        print(json.dumps(due(), ensure_ascii=False, indent=1))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
