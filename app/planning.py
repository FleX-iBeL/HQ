"""H143: tick off or X the appointments in HQ's calendar, and look back at the end of the week.

15 October 2026 (call at 09:34, Pepper), typed by the user: "the planning in the calendar already is deviating so
much, and i want that we can checkmark done (checkmark icon) or X and if i press X it goes to hq planning, and so at
the end of the week we can discuss items not checked off yet and items with an X, and perhaps we can see patterns
and improve the general structure of things", then "yes i meant the actual calendar in google".

In the calendar sheet of the call page every appointment gets a check (done) and an X (didn't happen as planned); a
tap marks it, a second tap undoes it. The marks are kept in the workspace next to calendar.json, as
HQ/calendar-marks.json (HQ_CALENDAR_MARKS; synced to the other computer, off GitHub: titles are private).

An X also moves that appointment in Google Calendar to the user's calendar named PLANNING ("HQ Planning", the
setting HQ_PLANNING_CALENDAR in switches.env), and undo moves it back. The only write to Google Calendar HQ itself
does. The connector has no move, so it's a copy and a removal, each a short `claude -p` run (Haiku) like agenda.py's
read: first the copy is created in HQ Planning (only create_event allowed), and only when Google has answered with
the new appointment is the original removed (only delete_event allowed). A hook (`guard`) lets each run make exactly
the one call it was given, with exactly those values, and refuses everything else, so nothing else is ever created,
changed or removed. Undo is the same the other way: the saved details go back into the calendar it came from, then
the copy in HQ Planning is removed. An appointment with other people in it, a birthday or anything that isn't a plain appointment is never moved (one day of a repeating appointment is: that day leaves the series,
and undo puts it back as a single appointment): its X is kept in HQ only, and the sheet says so.

The work runs on the main HQ only (`start()`: from the page's tap, and every minute from tick.py while something
waits), one at a time (a lock).

    python3 app/planning.py               this week's appointments with their marks (what a call reads)
    python3 app/planning.py week [DATE]   the same, for the week of DATE (2026-10-12)
    python3 app/planning.py work          do the waiting moves now
Tests: HQ_PLANNING_FAKE=<a folder> stands in for Claude (see run_claude).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "routine"))
import agenda  # noqa: E402
import hqpaths  # noqa: E402

TOOL = agenda.TOOL
RUN_MAX = 4 * 60
TRIES = 3  # a move that keeps failing stops after this many tries, and says why
MOVABLE = {"DEFAULT", ""}


def _setting(name: str, default: str) -> str:
    """An environment variable wins, then switches.env, then the default."""
    if os.environ.get(name):
        return os.environ[name]
    try:
        for line in (ROOT / "switches.env").read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() == name and v.split("#")[0].strip():
                    return v.split("#")[0].strip().strip('"')
    except OSError:
        pass
    return default


def calendar_name() -> str:
    return _setting("HQ_PLANNING_CALENDAR", "HQ Planning")


def marks_file() -> Path:
    return Path(os.environ.get("HQ_CALENDAR_MARKS") or agenda.data_file().with_name("calendar-marks.json"))


def _read() -> dict:
    try:
        s = json.loads(marks_file().read_text(encoding="utf8"))
        return s if isinstance(s, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(s: dict) -> None:
    p = marks_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    os.replace(tmp, p)


def _marks(s: dict) -> dict:
    m = s.get("marks")
    if not isinstance(m, dict):
        m = s["marks"] = {}
    return m


# -- the marks, for the page ------------------------------------------------------------------------------

def _index(marks: dict) -> tuple[dict, set]:
    """Every appointment id a mark stands for (its own, its copy in HQ Planning, its copy back), and the ids
    HQ removed from Google (hidden until the next read of the calendar shows they're gone)."""
    by, gone = {}, set()
    for key, m in marks.items():
        if not isinstance(m, dict):
            continue
        by[key] = key
        for i in m.get("also") or []:
            by[i] = key
        gone.update(m.get("gone") or [])
    return by, gone


def attach(events: list[dict]) -> list[dict]:
    """The page's appointments with their marks: mark (done, x or ""), mark_id (what a tap sends), and for an X
    where it is in Google (move: moving, moved, back, kept, failed) with a plain line (move_note)."""
    marks = _marks(_read())
    by, gone = _index(marks)
    out = []
    for e in events:
        if e.get("id") in gone and e.get("id") not in marks:  # the original stays in view until the next read
            continue
        key = by.get(e.get("id"), e.get("id"))
        m = marks.get(key) or {}
        mv = m.get("move") or {}
        out.append({**e, "mark_id": key, "mark": m.get("mark", ""), "move": mv.get("state", ""),
                    "move_note": _move_note(mv)})
    return out


def _move_note(mv: dict) -> str:
    st, name = mv.get("state", ""), calendar_name()
    if st == "to_move":
        return f"Moving to {name}…"
    if st == "moved":
        return f"In {name}"
    if st == "to_back":
        return "Moving back…"
    if st == "kept":
        return mv.get("why") or f"Kept where it is, not moved to {name}"
    if st == "failed":
        return f"Couldn't move it: {mv.get('error') or 'try again'}"
    return ""


def _event(key: str) -> dict | None:
    """The saved appointment a mark is about: by its own id, or one of the ids it had since."""
    events = agenda._read().get("events") or []
    marks = _marks(_read())
    ids = {key, *((marks.get(key) or {}).get("also") or [])}
    return next((e for e in events if e.get("id") == key), None) or next((e for e in events if e.get("id") in ids), None)


def _planning_id(cal: dict | None = None) -> str:
    """HQ Planning's calendar id, by its name, from the calendars the last read listed (list_calendars)."""
    name = calendar_name().strip().lower()
    for c in (cal or agenda._read()).get("calendars") or []:
        if str(c.get("name", "")).strip().lower() == name:
            return str(c.get("id", ""))
    return ""


def why_not(e: dict) -> str:
    """Why an appointment can't be moved to HQ Planning; empty when it can."""
    if e.get("others"):
        return "Has other people in it, so it stays where it is"
    if str(e.get("type") or "DEFAULT") not in MOVABLE:
        return "Not a plain appointment, so it stays where it is"
    if not e.get("gid") or not e.get("cal"):
        return ""  # an appointment read before H143: the next read of the calendar brings what's needed
    if e.get("cal") == _planning_id():
        return f"Already in {calendar_name()}"
    return ""


def set_mark(key: str, mark: str, now: float | None = None) -> dict:
    """A tap: mark is "done", "x" or "" (undo). An X asks for the move to HQ Planning, undoing an X asks for the
    move back; the work itself runs after (start())."""
    if mark not in ("done", "x", ""):
        raise ValueError("a mark is done, x or nothing")
    t = now or time.time()
    s = _read()
    marks = _marks(s)
    m = marks.get(key) or {}
    e = _event(key)
    if not e and not m:
        raise KeyError("no such appointment")
    mv = m.get("move") or {}
    if mv.get("state") in ("to_move", "to_back") and m.get("mark") == "x" and mark == "x":
        return s  # already on its way
    if e:
        m.update({k: e.get(k) for k in ("title", "start", "end", "all_day", "calendar")})
    m["mark"], m["marked"] = mark, t
    if mark == "x":
        if mv.get("state") == "failed" and mv.get("was"):
            mv = {**mv, "state": mv["was"], "tries": 0}
            mv.pop("was", None)
            if mv["state"] == "to_back":
                mv["state"] = "moved" if mv.get("removed") else "to_move"
        elif mv.get("state") == "to_back":
            mv["state"] = "moved"  # undo of the undo before it ran: it's still in HQ Planning
        elif mv.get("state") != "moved":
            why = why_not(e or {})
            if why:
                mv = {"state": "kept", "why": why}
            else:
                mv = {"state": "to_move", "tries": 0, "asked": t}
                if e:
                    mv["from"] = {k: e.get(k) for k in ("cal", "gid", "title", "start", "end", "all_day", "where", "notes", "free", "calendar")}
    elif mv.get("state") == "moved":
        mv = {**mv, "state": "to_back", "tries": 0, "asked": t}
    elif mv.get("state") in ("to_move", "kept", "failed"):
        mv = {} if not mv.get("copy") else {**mv, "state": "to_back", "tries": 0, "asked": t}
    m["move"] = mv
    if not mark and not mv and not m.get("gone"):
        marks.pop(key, None)
    else:
        marks[key] = m
    _write(s)
    return s


# -- the move, through the user's own Claude and its Google Calendar connector ------------------------------

def _local(iso: str, all_day: bool) -> str:
    if all_day:
        return iso[:10] + "T00:00:00"
    try:
        d = datetime.fromisoformat(iso)
        return (d.astimezone() if d.tzinfo else d).strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return iso


def create_input(e: dict, calendar_id: str) -> dict:
    """create_event's input for a copy of the saved appointment e in calendar_id: the same title, time, place
    and notes, nobody notified."""
    end = e.get("end") or e.get("start", "")
    inp = {"calendarId": calendar_id, "summary": e.get("title") or "(no title)",
           "startTime": _local(e.get("start", ""), bool(e.get("all_day"))), "endTime": _local(end, bool(e.get("all_day"))),
           "notificationLevel": "NONE"}
    if e.get("all_day"):
        inp["allDay"] = True
    if e.get("where"):
        inp["location"] = e["where"]
    if e.get("notes"):
        inp["description"] = e["notes"]
    if e.get("free"):
        inp["availability"] = "AVAILABILITY_FREE"
    tz = agenda.timezone()
    if tz and not e.get("all_day"):
        inp["timeZone"] = tz
    return inp


def delete_input(calendar_id: str, event_id: str) -> dict:
    return {"calendarId": calendar_id, "eventId": event_id, "notificationLevel": "NONE"}


def prompt(tool: str, inp: dict) -> str:
    return ("You make one change in a calendar for a program; the program reads your tool result itself.\n"
            f"Call {tool} exactly once, with exactly this input, nothing added or changed:\n{json.dumps(inp, ensure_ascii=False)}\n"
            "Call no other tool and don't call it again. Then reply with only the word: done")


def guard(stdin: str, expect_file: str) -> int:
    """The PreToolUse hook of a move run: only the one call the run was given, with exactly its values, passes
    (exit 0); anything else is refused (exit 2, the reason on stderr)."""
    try:
        ask = json.loads(stdin)
        want = json.loads(Path(expect_file).read_text(encoding="utf8"))
    except (OSError, ValueError):
        print("HQ planning: refused (no expected call)", file=sys.stderr)
        return 2
    name, inp = str(ask.get("tool_name", "")), ask.get("tool_input") or {}
    if name == "ToolSearch":  # loading the calendar tool's description first (the connector's tools are deferred)
        return 0
    if name == want.get("tool") and inp == want.get("input") and not want.get("used"):
        want["used"] = True
        Path(expect_file).write_text(json.dumps(want), encoding="utf8")
        return 0
    print(f"HQ planning: refused {name}: only the one {want.get('tool', '')} call asked for may run", file=sys.stderr)
    return 2


def run_claude(tool: str, inp: dict) -> list[str]:
    """One Claude run that may make exactly this one calendar call; its stream lines. In a test, HQ_PLANNING_FAKE
    is a folder: the stand-in checks the call against the same guard, appends it to calls.jsonl and answers with
    what answers.jsonl holds for that tool (its first line for that tool, used once), else an error."""
    fake = os.environ.get("HQ_PLANNING_FAKE")
    work = Path(fake) if fake else ROOT / "scratch" / "planning"
    work.mkdir(parents=True, exist_ok=True)
    expect = work / f"expect-{os.getpid()}.json"
    expect.write_text(json.dumps({"tool": TOOL + tool, "input": inp}), encoding="utf8")
    try:
        if fake:
            return _fake(work, tool, inp, expect)
        hook = f'{sys.executable} {json.dumps(str(Path(__file__).resolve()))} guard {json.dumps(str(expect))}'
        settings = {"hooks": {"PreToolUse": [{"matcher": ".*", "hooks": [{"type": "command", "command": hook}]}]}}
        deny = [TOOL + t for t in ("create_event", "update_event", "delete_event", "respond_to_event", "suggest_time",
                                   "list_calendars", "list_events", "get_event", "search_events") if t != tool]
        cmd = [agenda._claude(), "-p", "--no-chrome", "--model", "haiku", "--permission-mode", "dontAsk",
               "--no-session-persistence", "--output-format", "stream-json", "--verbose",
               "--settings", json.dumps(settings),
               "--allowedTools", TOOL + tool,
               "--disallowedTools", ",".join(deny + ["Bash", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch",
                                                     "Read", "Grep", "Glob", "Task", "Agent"])]
        r = subprocess.run(cmd, input=prompt(tool, inp), capture_output=True, text=True, timeout=RUN_MAX,
                           cwd=str(hqpaths.FOLDER))
        if r.returncode != 0 and not r.stdout.strip():
            raise RuntimeError((r.stderr or "the run failed").strip()[-300:])
        return r.stdout.splitlines()
    finally:
        expect.unlink(missing_ok=True)


def _fake(work: Path, tool: str, inp: dict, expect: Path) -> list[str]:
    calls = work / "calls.jsonl"
    asked = {"tool_name": TOOL + tool, "tool_input": inp}
    with open(calls, "a", encoding="utf8") as f:
        f.write(json.dumps({**asked, "passed": guard(json.dumps(asked), str(expect)) == 0}) + "\n")
    answers = work / "answers.jsonl"
    lines = answers.read_text(encoding="utf8").splitlines() if answers.exists() else []
    body, rest = None, []
    for line in lines:
        a = json.loads(line)
        if body is None and a.get("tool") == tool:
            body = a.get("result")
        else:
            rest.append(line)
    answers.write_text("".join(x + "\n" for x in rest), encoding="utf8")
    use = {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "p1", "name": TOOL + tool, "input": inp}]}}
    res = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "p1",
                                                    "content": json.dumps(body) if body is not None else "Error: no answer"}]}}
    return [json.dumps(use), json.dumps(res), json.dumps({"type": "result", "result": "done"})]


def _answer(lines: list[str], tool: str, inp: dict):
    """Google's answer to exactly this call in a run's stream, or None (an error, or no such call)."""
    for name, got, res in agenda.tool_results(lines):
        if name == TOOL + tool and got == inp:
            return res
    return None


def _created_id(res, inp: dict) -> str:
    """The new appointment's id, when Google's answer shows the copy with the title asked for."""
    if isinstance(res, dict) and isinstance(res.get("event"), dict):
        res = res["event"]
    if not isinstance(res, dict) or not res.get("id"):
        return ""
    if res.get("summary") not in (None, inp.get("summary")):
        return ""
    return str(res["id"])


def _deleted(res) -> bool:
    """A delete's answer: Google answers with nothing much; an error isn't JSON (tool_results leaves it out)."""
    return res is not None and not (isinstance(res, dict) and (res.get("error") or res.get("errors")))


def _copy(e: dict, to_cal: str) -> str:
    inp = create_input(e, to_cal)
    return _created_id(_answer(run_claude("create_event", inp), "create_event", inp), inp)


def _remove(cal: str, gid: str) -> bool:
    inp = delete_input(cal, gid)
    return _deleted(_answer(run_claude("delete_event", inp), "delete_event", inp))


def _step(key: str, m: dict) -> bool:
    """One waiting move or move back. True when something changed."""
    mv = m.get("move") or {}
    st = mv.get("state")
    if st == "to_move":
        src = mv.get("from") or {}
        if not src.get("gid") or not src.get("cal"):
            e = _event(key) or {}
            if not e.get("gid"):
                agenda.refresh()  # read before H143: the next read brings its Google id
                return False
            src = mv["from"] = {k: e.get(k) for k in ("cal", "gid", "title", "start", "end", "all_day", "where", "notes", "free", "calendar")}
            why = why_not(e)
            if why:
                m["move"] = {"state": "kept", "why": why}
                return True
        to = _planning_id()
        if not to:
            mv.update(state="failed", error=f"there's no calendar named {calendar_name()} in your Google Calendar")
            return True
        if not mv.get("copy"):
            new = _copy(src, to)
            if not new:
                return _failed(mv, f"Google didn't make the copy in {calendar_name()}")
            mv["copy"] = {"cal": to, "gid": new}
            m.setdefault("also", []).append(agenda._event_id(to, new))
            _save_one(key, m)
        if not _remove(src["cal"], src["gid"]):
            return _failed(mv, "the copy is in place, but the original couldn't be removed")
        m.setdefault("gone", []).append(agenda._event_id(src["cal"], src["gid"]))
        mv["removed"] = True
        mv.update(state="moved", moved=time.time(), tries=0, error="")
        return True
    if st == "to_back":
        src, cp = mv.get("from") or {}, mv.get("copy") or {}
        if not cp.get("gid"):
            m["move"] = {}
            return True
        if mv.get("removed") and not mv.get("back"):  # the original is gone from Google: put it back first
            new = _copy(src, src.get("cal", ""))
            if not new:
                return _failed(mv, "Google didn't put it back")
            mv["back"] = {"cal": src.get("cal"), "gid": new}
            m.setdefault("also", []).append(agenda._event_id(src.get("cal", ""), new))
            _save_one(key, m)
        if not _remove(cp["cal"], cp["gid"]):
            return _failed(mv, f"it's back, but the copy in {calendar_name()} couldn't be removed")
        m.setdefault("gone", []).append(agenda._event_id(cp["cal"], cp["gid"]))
        # back where it was (the original, or the one put back in its place)
        b = mv.get("back") or {}
        m["move"] = {} if m.get("mark") != "x" else {"state": "to_move", "tries": 0, "from": {**src, **b}}
        return True
    return False


def _failed(mv: dict, why: str) -> bool:
    mv["tries"] = int(mv.get("tries") or 0) + 1
    mv["error"] = why
    if mv["tries"] >= TRIES:
        mv["was"] = mv.get("state")
        mv["state"] = "failed"
    return True


def _save_one(key: str, m: dict) -> None:
    """Saves one mark's progress at once, so a copy made is never forgotten (the page may have marked meanwhile)."""
    s = _read()
    cur = _marks(s).get(key) or {}
    cur["move"], cur["also"], cur["gone"] = m.get("move"), m.get("also", []), m.get("gone", [])
    _marks(s)[key] = cur
    _write(s)


def pending(s: dict | None = None) -> list[str]:
    s = _read() if s is None else s
    return [k for k, m in _marks(s).items() if isinstance(m, dict) and (m.get("move") or {}).get("state") in ("to_move", "to_back")]


def _lock() -> Path:
    return marks_file().with_name(".calendar-marks.lock")


def working() -> bool:
    try:
        pid = int(_lock().read_text().split()[0])
        os.kill(pid, 0)
        return True
    except (OSError, ValueError, IndexError):
        return False


def work() -> int:
    """Does the waiting moves, one at a time. Returns how many changed."""
    if working():
        return 0
    _lock().write_text(str(os.getpid()))
    done = 0
    try:
        for _ in range(20):
            keys = pending()
            if not keys:
                break
            progressed = False
            for key in keys:
                s = _read()
                m = _marks(s).get(key)
                if not isinstance(m, dict):
                    continue
                state_before = (m.get("move") or {}).get("state")
                try:
                    changed = _step(key, m)
                except Exception as e:  # a run that fails is tried again, TRIES times at most
                    changed = _failed(m.setdefault("move", {}), str(e)[:200])
                if changed:
                    s = _read()
                    cur = _marks(s).get(key) or {}
                    # the user may have tapped meanwhile: keep the tap, keep what the work did
                    cur["move"], cur["also"], cur["gone"] = m.get("move"), m.get("also", []), m.get("gone", [])
                    if cur.get("mark") != "x" and (cur["move"] or {}).get("state") == "moved":
                        cur["move"]["state"] = "to_back"
                    if not cur.get("mark") and not cur["move"] and not cur["gone"]:
                        _marks(s).pop(key, None)
                    else:
                        _marks(s)[key] = cur
                    _write(s)
                    done += 1
                    progressed = progressed or (m.get("move") or {}).get("state") != state_before
            if not progressed:
                break
        if done:
            agenda.changed("planning")  # H153: right away, not only when the last read is a quarter of an hour old
    finally:
        _lock().unlink(missing_ok=True)
    return done


def start() -> bool:
    """Starts the work detached when something waits, on the main HQ only, one at a time. True when started."""
    if not pending() or working():
        return False
    try:
        import role
        if role.is_backup():
            return False
    except Exception:
        pass
    py = ROOT / ".venv" / "bin" / "python"
    log = ROOT / "scratch" / "planning.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([str(py) if py.exists() else sys.executable, str(Path(__file__).resolve()), "work"],
                     cwd=str(ROOT), stdout=open(log, "a"), stderr=subprocess.STDOUT, start_new_session=True)
    return True


# -- the look back -----------------------------------------------------------------------------------------

def week_start(d: datetime) -> datetime:
    return (d - timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def week(day: datetime | None = None) -> str:
    """The week's appointments (Monday to Sunday) with their marks, in plain lines: what a call reads to look back."""
    a = week_start(day or datetime.now())
    b = a + timedelta(days=7)
    s, marks = agenda._read(), _marks(_read())
    events = attach(s.get("events") or [])
    seen, rows = set(), []
    for e in events:
        t = agenda._sort_key(e.get("start", ""))
        if not a.timestamp() <= t < b.timestamp() or e["mark_id"] in seen:
            continue
        seen.add(e["mark_id"])
        rows.append((t, e.get("mark", ""), e.get("title", ""), agenda.when_words(e), e.get("move_note", "")))
    for key, m in marks.items():  # X'd ones the last read doesn't show (yet)
        t = agenda._sort_key(m.get("start", "")) if isinstance(m, dict) else 0
        if key not in seen and a.timestamp() <= t < b.timestamp():
            rows.append((t, m.get("mark", ""), m.get("title", ""), agenda.when_words(m), _move_note(m.get("move") or {})))
    rows.sort()
    now = time.time()
    word = {"done": "done", "x": "X"}
    lines = [f"Week of {a:%A} {a.day} {a:%B} {a:%Y}; X means it didn't happen as planned "
             f"(moved to the calendar {calendar_name()})."]
    for t, mk, title, when, note in rows:
        state = word.get(mk) or ("not ticked" if t < now else "coming")
        lines.append(f"- {state}: {title} ({when})" + (f" [{note}]" if note and mk == "x" else ""))
    if len(lines) == 1:
        lines.append("- nothing in the calendar this week (as last read)")
    n = {k: sum(1 for r in rows if (r[1] or ("open" if r[0] < now else "")) == k) for k in ("done", "x", "open")}
    lines.append(f"Done {n['done']}, X {n['x']}, not ticked yet {n['open']}.")
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "week"
    if cmd == "guard":
        sys.exit(guard(sys.stdin.read(), args[1] if len(args) > 1 else ""))
    elif cmd == "week":
        print(week(datetime.fromisoformat(args[1]) if len(args) > 1 else None))
    elif cmd == "work":
        print(time.strftime("%Y-%m-%d %H:%M:%S"), "planning:", work(), "changed")
    elif cmd == "mark" and len(args) >= 2:
        set_mark(args[1], args[2] if len(args) > 2 else "")
        start()
        print("marked")
    else:
        print(__doc__)
        sys.exit(2)
