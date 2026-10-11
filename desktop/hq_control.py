#!/usr/bin/python3
"""H27: the Mac desktop app's watchdog part. 10 October 2026 (call at 14:33): "So instead of now running all
these routines on the background, we can open this one up, and we know everything is running or not. And
this app can also reboot that, right? So the main watchdog thing in here. That helps turn everything on,
can then be in that app."

The app (desktop/HQ.swift) runs this every few seconds and shows what it says; the routines themselves keep
running in the background as before, also when the app is closed (Claude's choice: closing a window must
never stop the mail check or a job).

    hq_control.py health          one JSON line: the overall light, the dog's mood, each routine, what's off
    hq_control.py fix             turns on what's off (status page, helper, watchdog, call line); JSON line
    hq_control.py fix --dry       says what it would turn on, does nothing
    --from FILE                   read the routine lines from FILE instead of the status server (tests)

The light follows the status page's Routines light (H21): red when something has stopped (or the laptop is
hot, or the battery low on battery), yellow when a routine waits on purpose or the laptop is warm, green
otherwise (a routine running now is green too, as since H33). The dog (Claude's choice): happy and wagging on green, alert and sniffing on yellow, barking on
red, running while it turns things on, asleep when the status page itself doesn't answer and nothing has
been tried yet.
"""
import json, os, socket, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HQ = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HQ, "routine"))
try:
    import hqpaths, incidents
except Exception:  # the app must still show something
    hqpaths = incidents = None

STATUS = "http://127.0.0.1:4748"
CALL_PORT = 7860
# The helper app; until it is rebuilt under its new name (H54, 11 October 2026), the old one still runs.
HELPER_APPS = [os.path.expanduser("~/Applications/HQ Routine.app"), os.path.expanduser("~/Applications/Jarvis Routine.app")]
HELPER_APP = next((a for a in HELPER_APPS if os.path.isdir(a)), HELPER_APPS[0])
SUPPORT = os.path.expanduser("~/Library/Application Support/HQ")
PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

# The same names and order as the status page's Routines section.
ROUTINES = [
    ("helper", "Routine helper"), ("watchdog", "Watchdog"), ("mail", "Mail check"), ("jobs", "Jobs from calls"),
    ("schedule", "Scheduler"), ("usage", "Usage check"), ("phone", "Status page"), ("call", "Call line"),
    ("temp", "Laptop temperature"), ("battery", "Laptop battery"),
]


def fetch(src=None):
    """The status server's /routines.json, or None when it doesn't answer."""
    if src:
        return json.load(open(src))
    try:
        with urllib.request.urlopen(STATUS + "/routines.json", timeout=3) as r:
            return json.load(r)
    except Exception:
        return None


def judge(data):
    """The overall light and each routine's state, as the status page draws them (index.html, drawRoutines)."""
    if data is None:
        return {"light": "down", "mood": "sleep", "headline": "The status page doesn't answer",
                "routines": [], "off": ["status"], "counts": "Status page down"}
    now = data.get("now") or time.time()
    allr = data.get("routines") or {}
    helper = allr.get("helper")
    helper_late = not helper or now - helper.get("at", 0) > 180
    rows, off = [], []
    bad = busy = waiting = warm = 0
    hot = low_bat = False
    for key, name in ROUTINES:
        x = allr.get(key)
        state = (x or {}).get("state", "off")
        text = (x or {}).get("text", "No line yet")
        late = bool(x) and now - x.get("at", 0) > (x.get("every") or 60) * 2 + 60
        if not x and key == "watchdog":
            state, text = "down", "Not installed or not running"
        elif late:
            state = "down"
            mins = int((now - x.get("at", 0)) // 60)
            text = f"Stopped: last seen {mins} min ago" if key in ("helper", "watchdog") else (
                f"Not checked since the helper stopped ({mins} min)" if helper_late else f"Overdue: last seen {mins} min ago")
        if state == "fixed":
            state = "ok"
        if state == "down":
            bad += 1
        if state == "running":
            busy += 1
        if state == "waiting":
            waiting += 1
        if key == "temp" and state == "warm":
            warm += 1
        if key == "temp" and state == "down" and x and not late and text.startswith("Hot"):
            hot, bad = True, bad - 1
        if key == "battery" and state == "low":
            warm += 1
        if key == "battery" and state == "down" and x and not late and text.startswith("Low battery"):
            low_bat, bad = True, bad - 1
        if state == "down" and key in ("helper", "watchdog", "call", "phone"):
            off.append(key)
        rows.append({"key": key, "name": name, "state": state, "text": text})
    if bad or hot or low_bat:
        light, mood = "down", "bark"
    elif waiting or warm:
        light, mood = ("waiting" if waiting else "warm"), "alert"
    elif busy:
        light, mood = "running", "happy"  # a running routine is good news (H33: green with stripes)
    else:
        light, mood = "ok", "happy"
    if hot:
        headline = "The laptop is hot"
    elif low_bat:
        headline = "The battery is low"
    elif bad:
        names = [r["name"] for r in rows if r["state"] == "down"]
        headline = ("Not working: " + ", ".join(names[:3]) + (" …" if len(names) > 3 else ""))
    elif busy:
        headline = f"All working · {busy} running now"
    elif waiting:
        headline = f"All working · {waiting} waiting on purpose"
    elif warm:
        headline = "All working · the laptop is warm"
    else:
        headline = "All working"
    return {"light": light, "mood": mood, "headline": headline, "routines": rows, "off": off,
            "counts": f"{bad} not working" if bad else "All working"}


# ---------- turning things on ----------

def listening(port):
    s = socket.socket()
    s.settimeout(1)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def helper_pids():
    """The helper is the process whose program is the applet itself (as the watchdog finds it)."""
    r = subprocess.run(["/bin/ps", "-ax", "-o", "pid=,comm="], capture_output=True, text=True)
    out = []
    for line in r.stdout.splitlines():
        pid, _, comm = line.strip().partition(" ")
        if comm.strip().endswith(tuple(os.path.basename(a) + "/Contents/MacOS/applet" for a in HELPER_APPS)):
            out.append(int(pid))
    return out


def watchdog_label():
    return hqpaths.agent_label("watchdog") if hqpaths else "com.hq.watchdog"


def watchdog_loaded(label):
    r = subprocess.run(["/bin/launchctl", "print", f"gui/{os.getuid()}/{label}"], capture_output=True, text=True)
    return r.returncode == 0


def plan(data):
    """What's off and how it would be turned on: [(key, what, command)]. Only things that are really off:
    a routine that runs is never stopped or restarted from here."""
    todo = []
    if data is None and not listening(4748):
        todo.append(("phone", "Started the status page",
                     ["node", os.path.join(HQ, "status", "server.mjs"), "--quiet"]))
    if not helper_pids() and os.path.isdir(HELPER_APP):
        todo.append(("helper", "Started the routine helper", ["/usr/bin/open", "-g", HELPER_APP]))
    label = watchdog_label()
    plist = os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")
    wd = ((data or {}).get("routines") or {}).get("watchdog")
    now = (data or {}).get("now") or time.time()
    wd_late = not wd or now - wd.get("at", 0) > (wd.get("every") or 300) * 2 + 60
    if os.path.exists(plist) and not watchdog_loaded(label):
        todo.append(("watchdog", "Loaded the watchdog", ["/bin/launchctl", "load", plist]))
    elif wd_late and watchdog_loaded(label):
        todo.append(("watchdog", "Woke the watchdog up", ["/bin/launchctl", "kickstart", f"gui/{os.getuid()}/{label}"]))
    if not listening(CALL_PORT):
        todo.append(("call", "Started the call line", [os.path.join(HQ, "app", "start.sh")]))
    # H59: a user's own part in local/ goes first (start-status-page, start-helper, start-watchdog, start-call-line).
    own = {"phone": "start-status-page", "helper": "start-helper", "watchdog": "start-watchdog", "call": "start-call-line"}
    if hqpaths:
        todo = [(k, w, hqpaths.part_cmd(own[k]) or c) for k, w, c in todo]
    return todo


def fix(data, dry=False):
    done = []
    for key, what, cmd in plan(data):
        if dry:
            done.append({"key": key, "what": what, "ok": None})
            continue
        try:
            if cmd[0] == "node" or cmd[0].endswith("start.sh") or (hqpaths and hqpaths.LOCAL in " ".join(cmd)):
                # Detached, so it keeps running when the app quits.
                subprocess.Popen(cmd, cwd=HQ, env={**os.environ, "PATH": PATH}, stdin=subprocess.DEVNULL,
                                 stdout=open(os.path.join(HQ, "scratch", f"desktop-{key}.log"), "a"),
                                 stderr=subprocess.STDOUT, start_new_session=True)
                ok = True
            else:
                ok = subprocess.run(cmd, capture_output=True, timeout=30).returncode == 0
        except Exception:
            ok = False
        done.append({"key": key, "what": what, "ok": ok})
        if ok and incidents:
            incidents.fix(key, what + " (from the Mac app)")
    return done


def main(argv):
    src = argv[argv.index("--from") + 1] if "--from" in argv else None
    data = fetch(src)
    if argv and argv[0] == "fix":
        os.makedirs(os.path.join(HQ, "scratch"), exist_ok=True)
        done = fix(data, dry="--dry" in argv)
        print(json.dumps({"fixed": done, "nothing": not done}))
        return 0
    out = judge(data)
    out["at"] = time.time()
    # H59: the version and a newer one, for the strip (a look on GitHub is started in the background when due).
    try:
        import update
        u = update.status()
        out["update"] = {"version": u["version"], "latest": u["latest"], "available": u["available"],
                         "offline": u["offline"], "updating": u["run"].get("state") in ("waiting", "updating")}
    except Exception:
        out["update"] = {}
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
