#!/usr/bin/python3
"""H20: the watchdog. Runs every 5 minutes, on the five-minute marks (H22), started by macOS itself (a LaunchAgent), apart from the
Jarvis Routine helper, so it keeps going when the helper stops. 10 October 2026: "and maybe a
watchdog that pings every 5 minutes".

- The helper isn't running: start it (it then also starts the call line if that's down).
- The helper runs but its heartbeat is over 6 minutes old (it's stuck): quit it and start it again.
- What it fixed also goes to events.jsonl, for the incident log on the status page (H30).
- Every run writes its own line for the status page (H19), so the page shows the watchdog is alive too.
- H42: a routine that keeps failing, not only one that's missed or stopped. 10 October 2026:
  "i also want to know why the watchdog didnt fix it" (the helper was alive, so it had nothing to do).
  The helper keeps each routine's failures in a row, with why, in failures.json next to this file. Two or
  more in a row: the watchdog notes it once (its log, events.jsonl, its own line). When the helper has given
  up on it (its retries used) and the internet is there, it asks the helper for one more try (retry-<key>).
  When it works again, that's noted too.

It runs from ~/Library/Application Support/JarvisVA (installed there by install-watchdog.sh) and never
touches the Documents folder, so macOS asks no permission. Its log: watchdog.log next to it.
"""
import json, os, socket, subprocess, time

SUPPORT = os.path.expanduser("~/Library/Application Support/JarvisVA")
APP = os.path.expanduser("~/Applications/Jarvis Routine.app")
EVERY = 300
STUCK = 360
KEEPS_FAILING = 2  # H42: failures in a row before the watchdog calls it "keeps failing"
NAMES = {"mail": "the mail check"}


def pids():
    # Not pgrep: started by launchd, pgrep -f found a match while the helper was gone (10 October 2026).
    # The helper is the process whose program is the applet itself.
    r = subprocess.run(["/bin/ps", "-ax", "-o", "pid=,comm="], capture_output=True, text=True)
    out = []
    for line in r.stdout.splitlines():
        pid, _, comm = line.strip().partition(" ")
        if comm.strip().endswith("Jarvis Routine.app/Contents/MacOS/applet"):
            out.append(int(pid))
    return out


def running_for(pid):
    r = subprocess.run(["/bin/ps", "-o", "etime=", "-p", str(pid)], capture_output=True, text=True)
    t = r.stdout.strip()
    if not t:
        return 0
    days = 0
    if "-" in t:
        d, t = t.split("-", 1)
        days = int(d)
    parts = [int(x) for x in t.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return days * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


def log(msg):
    with open(os.path.join(SUPPORT, "watchdog.log"), "a") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def event(what, key=None):
    # H30: the helper writes the incident log in the Documents folder, which the watchdog can't touch,
    # so what it did goes here, and the helper picks it up. H42: with a key, it goes with that routine's incident.
    with open(os.path.join(SUPPORT, "events.jsonl"), "a") as f:
        f.write(json.dumps({"at": time.time(), "what": what, **({"key": key} if key else {})}) + "\n")


def online():
    try:
        socket.create_connection(("api.anthropic.com", 443), timeout=5).close()
        return True
    except OSError:
        return False


def clock(t):
    return time.strftime("%H:%M", time.localtime(t))


def failing():
    """H42: routines that keep failing. Notes each streak once, asks for one more try when the helper has
    given up and the internet is there, and notes when it works again. Returns lines for its own status."""
    try:
        fails = json.load(open(os.path.join(SUPPORT, "failures.json")))
    except (OSError, ValueError):
        return []
    path = os.path.join(SUPPORT, "watchdog-state.json")
    try:
        seen = json.load(open(path))
    except (OSError, ValueError):
        seen = {}
    noticed, asked = seen.setdefault("noticed", {}), seen.setdefault("asked", {})
    out = []
    for key, e in fails.items():
        name = NAMES.get(key, key)
        n, first = e.get("n", 0), str(e.get("first"))
        if n >= KEEPS_FAILING:
            out.append(f"{name} failed {n} times in a row ({e.get('why') or 'reason not known'})")
            if noticed.get(key) != first:
                noticed[key] = first
                text = (f"Noticed: {name} has failed {n} times in a row since {clock(e['first'])}. "
                        f"Last reason: {e.get('why') or 'not known'}")
                log(text)
                event(text, key)
            if e.get("gave_up") and asked.get(key) != first:
                if online():
                    asked[key] = first
                    open(os.path.join(SUPPORT, f"retry-{key}"), "w").write(str(int(time.time())))
                    text = f"The helper had given up on {name}, and the internet is there: asked it for one more try"
                    log(text)
                    event(text, key)
                else:
                    out[-1] += "; waiting for the internet to ask for another try"
        elif key in noticed:
            text = f"{name[0].upper() + name[1:]} works again" + (f" (since {clock(e['ok'])})" if e.get("ok") else "")
            log(text)
            event(text, key)
            noticed.pop(key, None)
            asked.pop(key, None)
    with open(path, "w") as f:
        json.dump(seen, f)
    return out


def main():
    os.makedirs(SUPPORT, exist_ok=True)
    now = time.time()
    try:
        beat = float(open(os.path.join(SUPPORT, "heartbeat")).read().strip())
    except (OSError, ValueError):
        beat = 0
    age = now - beat
    ps = pids()
    if not ps:
        subprocess.run(["/usr/bin/open", "-g", APP])
        state, text = "fixed", "The helper wasn't running: started it again"
        log(text)
        event(text)
    elif age > STUCK and min(running_for(p) for p in ps) > STUCK:
        for p in ps:
            try:
                os.kill(p, 15)
            except OSError:
                pass
        time.sleep(3)
        subprocess.run(["/usr/bin/open", "-g", APP])
        state, text = "fixed", f"The helper was stuck (no heartbeat for {int(age // 60)} min): restarted it"
        log(text)
        event(text)
    else:
        state, text = "ok", "The helper is alive"
    try:
        seen = failing()
    except Exception as e:  # never let this stop the watchdog's own check
        log(f"failing check: {e!r}")
        seen = []
    if seen:
        text += ". Noticed: " + "; ".join(seen)
    # H22: it runs on the five minutes (13:35, 13:40, …), so its next run is the next five-minute mark.
    line = {"at": now, "state": state, "text": text, "last": now, "next": (int(now) // EVERY + 1) * EVERY, "every": EVERY}
    tmp = os.path.join(SUPPORT, ".watchdog.json")
    with open(tmp, "w") as f:
        json.dump(line, f)
    os.replace(tmp, os.path.join(SUPPORT, "watchdog.json"))


if __name__ == "__main__":
    main()
