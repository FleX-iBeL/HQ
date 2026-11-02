"""H30: the incident log. When a routine went down, why (if known), what was done to fix it, and when it
was back. 10 October 2026: "preferably, it should also log somewhere in monitoring when services
went disconnected and what it did to fix it."

Kept in .status/incidents.json (local only, like the routine lines), the newest 100. One entry:
{"id", "key" (the routine), "down" (epoch), "why", "fixes": [{"at", "what"}], "back" (epoch, or None while
still down)}. Written by the HQ Routine helper (tick.py). The watchdog can't write in the Documents
folder, so it leaves what it did in ~/Library/Application Support/HQ/events.jsonl, and the helper
picks that up here. The status server serves the log at /incidents.json for the Routines section.
"""
import json, os, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
JV = os.path.normpath(os.path.join(HERE, ".."))
FILE = os.environ.get("HQ_INCIDENTS_FILE") or os.path.join(JV, ".status", "incidents.json")
import hqpaths  # noqa: E402  H56.1: HQ's own memory, a folder that fits each computer
EVENTS = os.path.join(hqpaths.SUPPORT, "events.jsonl")
KEEP = 100


def _real() -> bool:
    """F116: a test leaves the real log as it is unless it named its own."""
    return not hqpaths.under_test() or bool(os.environ.get("HQ_INCIDENTS_FILE"))


def _aside():
    """F116: where an unreadable log is kept: FILE.bad, then FILE.bad.2, .bad.3: one kept never goes under the next."""
    if not os.path.exists(FILE + ".bad"):
        return FILE + ".bad"
    n = 2
    while os.path.exists(f"{FILE}.bad.{n}"):
        n += 1
    return f"{FILE}.bad.{n}"


def read():
    try:
        data = json.load(open(FILE))
    except OSError:
        data = {}
    except ValueError:
        # F116: an unreadable log was read as empty, and the next write put a new one over the history. Now it's kept aside, its
        # own routine line goes red, and new incidents are written from here.
        data = {}
        if _real():
            try:
                aside = _aside()
                os.replace(FILE, aside)
                import routines
                routines.beat("incidents-file", state="down", every=365 * 86400, last=time.time(), aside=os.path.basename(aside),
                              text=f"The incident log was unreadable; kept as {os.path.basename(aside)}, new incidents are written from here")
            except Exception:
                pass
    if not isinstance(data, dict):
        data = {}
    data.setdefault("incidents", [])
    data.setdefault("events_seen", 0)
    return data


def _write(data):
    data["incidents"] = data["incidents"][-KEEP:]
    os.makedirs(os.path.dirname(FILE), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(FILE), prefix=".incidents")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, FILE)
    if _real():  # F116: a good log written again: its red line goes green, saying where the unreadable one is kept
        try:
            import routines
            line = routines.read().get("incidents-file") or {}
            if line.get("state") == "down":
                routines.beat("incidents-file", state="ok", every=365 * 86400, last=time.time(),
                              text=f"The incident log is written again; the unreadable one is kept as {line.get('aside') or os.path.basename(FILE) + '.bad'}")
        except Exception:
            pass


def _open(data, key):
    return next((i for i in reversed(data["incidents"]) if i["key"] == key and not i.get("back")), None)


def is_down(key):
    return _open(read(), key)


def down(key, why, at=None, **extra):
    """A routine went down. Opens an incident, or adds the reason to the one already open. Never raises.
    H42: extra fields, such as "detail" (the run's own last lines) and "run" (where its whole output is
    kept), are kept with it; on an incident already open they are replaced by the newest."""
    try:
        data = read()
        inc = _open(data, key)
        if inc:
            if (why and not inc.get("why")) or extra:
                if why and not inc.get("why"):
                    inc["why"] = why
                inc.update({k: v for k, v in extra.items() if v})
                _write(data)
            return inc
        inc = {"id": f"{key}-{int(at or time.time())}", "key": key, "down": at or time.time(), "why": why or "",
               "fixes": [], "back": None, **{k: v for k, v in extra.items() if v}}
        data["incidents"].append(inc)
        _write(data)
        _on_record(inc)
        return inc
    except Exception:
        return None


def fix(key, what, at=None):
    """What was done about an open incident (opened first if needed)."""
    try:
        if not is_down(key):
            down(key, "")
        data = read()
        inc = _open(data, key)
        inc["fixes"].append({"at": at or time.time(), "what": what})
        _write(data)
    except Exception:
        pass


def up(key, at=None, what=None):
    """The routine is back: closes its open incident, if any. F116: never without what fixed it: `what` is that, kept as the
    incident's last fix when it has none yet (a fix written before it says it already). With no fix and no `what` the close
    is refused: it stays open, and False comes back. True when it closed, None when nothing was open."""
    try:
        data = read()
        inc = _open(data, key)
        if not inc:
            return None
        when = at or time.time()
        if not inc.get("fixes"):
            if not str(what or "").strip():
                return False
            inc["fixes"] = [{"at": when, "what": str(what).strip()}]
        inc["back"] = when
        _write(data)
        return True
    except Exception:
        return None


def past(key, since, until, why, fixes, item=None):
    """An outage that is already over when it's noticed (the helper itself was down). F103: item, the id of the work it hit.
    F116: closed from the start, so never without what fixed it: no fixes, and it's refused (False)."""
    if not [w for _, w in fixes or [] if str(w).strip()]:
        return False
    try:
        data = read()
        inc = {"id": f"{key}-{int(since)}", "key": key, "down": since, "why": why,
               "fixes": [{"at": a, "what": w} for a, w in fixes], "back": until, **({"item": item} if item else {})}
        data["incidents"].append(inc)
        data["incidents"].sort(key=lambda i: i["down"])
        _write(data)
        _on_record(inc)
    except Exception:
        pass


def _on_record(inc):
    """F103: an incident about an item is a step of its record."""
    if inc.get("item"):
        import trail
        trail.step(inc["item"], "incident", key=inc["key"], why=str(inc.get("why") or "")[:200], line=inc["id"])


def watchdog_events():
    """The watchdog's lines (outside the Documents folder) not picked up yet: [(at, what)]."""
    try:
        lines = open(EVENTS).read().splitlines()
    except OSError:
        return []
    data = read()
    seen = data["events_seen"]
    out, keyed = [], []
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("at", 0) > seen:
            (keyed if e.get("key") else out).append(e)
    if out or keyed:
        data["events_seen"] = max(e["at"] for e in out + keyed)
        try:
            _write(data)
        except Exception:
            pass
    # H42: what the watchdog saw about one routine (it keeps failing; it asked for another try) goes
    # with that routine's open incident; seen after it was back, with its last one.
    for e in keyed:
        try:
            data = read()
            inc = _open(data, e["key"]) or next((i for i in reversed(data["incidents"]) if i["key"] == e["key"]), None)
            if inc:
                inc["fixes"].append({"at": e["at"], "what": f"Watchdog: {e.get('what', '')}"})
                _write(data)
        except Exception:
            pass
    return [(e["at"], e.get("what", "")) for e in out]
