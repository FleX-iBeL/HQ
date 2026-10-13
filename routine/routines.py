"""H19: every routine writes its own line for the status page, each time it runs.

The lines live in .status/routines.json (local only, like the usage reading), one entry per
routine: {"at": epoch seconds of this write, "state": ok|running|waiting|off|down, "text": what it
did or found, "last": epoch of its last real run, "next": epoch of its next run, "every": how often
it is expected to write, in seconds}. The status server serves it with the watchdog's own line (H20),
and the page turns a line red when it is overdue: that routine has stopped.

The helper also leaves a heartbeat outside the Documents folder, which the watchdog (H20) can read
without any macOS permission: ~/Library/Application Support/HQ/heartbeat (on Linux ~/.local/state/hq; H56.1).
"""
import json, os, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
JV = os.path.normpath(os.path.join(HERE, ".."))
FILE = os.path.join(JV, ".status", "routines.json")
import hqpaths  # noqa: E402  H56.1: HQ's own memory, a folder that fits each computer
SUPPORT = hqpaths.SUPPORT
HEARTBEAT = os.path.join(SUPPORT, "heartbeat")


def read():
    try:
        return json.load(open(FILE))
    except (OSError, ValueError):
        return {}


def beat(key, **fields):
    """Write (merge) one routine's line. Never raises: a status line must not stop a routine."""
    try:
        data = read()
        entry = dict(data.get(key) or {})
        entry.update(fields)
        entry["at"] = time.time()
        data[key] = entry
        os.makedirs(os.path.dirname(FILE), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(FILE), prefix=".routines")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, FILE)
    except Exception:
        pass


def drop(prefix, keep=()):
    """H88: remove the lines whose key starts with prefix, except those in keep (a heartbeat line whose
    computer got another name, or an HQ that is on its own again). Never raises."""
    try:
        data = read()
        gone = [k for k in data if k.startswith(prefix) and k not in keep]
        if not gone:
            return
        for k in gone:
            del data[k]
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(FILE), prefix=".routines")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=1)
        os.replace(tmp, FILE)
    except Exception:
        pass


def heartbeat():
    try:
        os.makedirs(SUPPORT, exist_ok=True)
        with open(HEARTBEAT, "w") as f:
            f.write(str(int(time.time())))
    except OSError:
        pass
