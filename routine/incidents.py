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
FILE = os.path.join(JV, ".status", "incidents.json")
import hqpaths  # noqa: E402  H56.1: HQ's own memory, a folder that fits each computer
EVENTS = os.path.join(hqpaths.SUPPORT, "events.jsonl")
KEEP = 100


def read():
    try:
        data = json.load(open(FILE))
    except (OSError, ValueError):
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


def up(key, at=None):
    """The routine is back: closes its open incident, if any."""
    try:
        data = read()
        inc = _open(data, key)
        if inc:
            inc["back"] = at or time.time()
            _write(data)
    except Exception:
        pass


def past(key, since, until, why, fixes):
    """An outage that is already over when it's noticed (the helper itself was down)."""
    try:
        data = read()
        data["incidents"].append({"id": f"{key}-{int(since)}", "key": key, "down": since, "why": why,
                                  "fixes": [{"at": a, "what": w} for a, w in fixes], "back": until})
        data["incidents"].sort(key=lambda i: i["down"])
        _write(data)
    except Exception:
        pass


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
