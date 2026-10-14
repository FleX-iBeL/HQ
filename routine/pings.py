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
        self.f = open(folder() / ".pings.lock", "w")
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


def remind(at: dt.datetime, text: str, by: str = "") -> dict:
    text = " ".join(str(text).split())[:500]
    if not text:
        raise ValueError("What should she remind him of?")
    with _Lock():
        s = read()
        n = max([int(r.get("n") or 0) for r in s["reminders"]] + [int(s.get("last_n") or 0)]) + 1
        r = {"n": n, "at": at.strftime(FMT), "text": text, "added": time.strftime(FMT), "by": by}
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
        sent = [r for r in s["reminders"] if r.get("sent")]
        s["reminders"] = [r for r in s["reminders"] if not r.get("sent")] + sent[-KEEP_SENT:]
        if initiative_due(t, s):
            s["initiative"] = {**(s.get("initiative") or {}), "looked": t}
            out.append(("initiative", ""))
        if not dry:
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
    out += ["", f"{agent_name()}'s own notes ({notes_file().relative_to(hqpaths.FOLDER) if str(notes_file()).startswith(hqpaths.FOLDER) else notes_file()}):"]
    out += [f"- {i['when'][:16]} · {i['text']} · id {i['id']}" for i in her_notes()] or ["- none"]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    by = os.environ.get("HQ_PINGS_BY", "")
    cmd = argv[0] if argv else "list"
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
    elif cmd == "due":
        print(json.dumps(due(), ensure_ascii=False, indent=1))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
