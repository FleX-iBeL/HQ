#!/usr/bin/env python3
"""H37: the laptop's battery, every minute, run by the HQ Routine helper (tick.py). No Claude, no
usage, no password. 10 October 2026, after the supermarket with the laptop in his bag and no
charger: "I also want a battery percentage on the status page, because I had a feeling maybe my laptop
died. I had no idea how much battery I had." "Same thing, we want to run it with routines on the
background in the terminal."

- Reads `pmset -g batt`: the percentage, and whether it's on the charger (charging, charged, or on
  the charger but not charging) or on battery, with the time left when macOS knows it.
- The ranges (Claude's choice): on battery, low under 20% (red), getting low 20 to 39% (yellow), fine
  from 40%. On the charger it's never an alarm, whatever the percentage: it's filling up.

Writes .status/battery.json (the latest reading), appends one line a minute to
.status/battery-history.jsonl (a day kept), writes its routine line ("battery": ok, low when getting
low, down when low) and opens an incident while it's low on battery.

    python3 "routine/battery.py"          one reading, written and printed
    python3 "routine/battery.py" --dry    one reading, printed only
"""
import json, os, re, subprocess, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routines
import incidents

HERE = os.path.dirname(os.path.abspath(__file__))
JV = os.path.normpath(os.path.join(HERE, ".."))
NOW_FILE = os.path.join(JV, ".status", "battery.json")
HISTORY = os.path.join(JV, ".status", "battery-history.jsonl")
LOW, GETTING_LOW = 20, 40  # percent, only counted on battery


def parse(out):
    """The percentage, on the charger or not, charging or not, and the minutes left (None when unknown)."""
    m = re.search(r"(\d+)%;\s*([^;\n]+)(?:;\s*([^\n]*))?", out)
    if not m:
        raise RuntimeError("no battery in pmset's answer")
    pct = int(m.group(1))
    word = m.group(2).strip().lower()
    rest = (m.group(3) or "").lower()
    plugged = "'ac power'" in out.lower() or word in ("charging", "charged", "finishing charge") or "ac attached" in word
    charging = word in ("charging", "finishing charge")
    t = re.search(r"(\d+):(\d+) remaining", rest)
    left = int(t.group(1)) * 60 + int(t.group(2)) if t and not (t.group(1) == "0" and t.group(2) == "00") else None
    return pct, plugged, charging, word, left


def judge(pct, plugged):
    """fine, getting low or low. On the charger it's always fine."""
    if plugged or pct >= GETTING_LOW:
        return "fine"
    return "low" if pct < LOW else "getting-low"


def read():
    out = subprocess.run(["/usr/bin/pmset", "-g", "batt"], capture_output=True, text=True, timeout=20).stdout
    pct, plugged, charging, word, left = parse(out)
    return {"t": int(time.time()), "pct": pct, "plugged": plugged, "charging": charging,
            "how": word, "left": left, "lvl": judge(pct, plugged)}


def how_words(x):
    """Charging or not, in plain words, with the time left."""
    left = x.get("left")
    hm = f"{left // 60}:{left % 60:02d}" if left is not None else None
    if x["charging"]:
        return f"Charging{f', full in {hm}' if hm else ''}"
    if x["plugged"]:
        return "On the charger, full" if x["how"] == "charged" or x["pct"] >= 99 else "On the charger, not charging"
    return f"On battery{f', {hm} left' if hm else ''}"


def write(x):
    os.makedirs(os.path.dirname(NOW_FILE), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(NOW_FILE), prefix=".battery")
    with os.fdopen(fd, "w") as f:
        json.dump({**x, "words": how_words(x), "ranges": {"low": LOW, "getting_low": GETTING_LOW}}, f)
    os.replace(tmp, NOW_FILE)
    with open(HISTORY, "a") as f:
        f.write(json.dumps({k: x[k] for k in ("t", "pct", "plugged", "charging", "lvl")}) + "\n")
    lines = open(HISTORY).read().splitlines()
    if len(lines) > 1500:
        with open(HISTORY, "w") as f:
            f.write("\n".join(lines[-1440:]) + "\n")


def main(dry=False):
    now = time.time()
    try:
        x = read()
    except Exception as e:
        if not dry:
            routines.beat("battery", state="down", text=f"Can't read the battery: {str(e)[:120]}", last=now,
                          next=now + 60, every=60)
        print(f"Can't read the battery: {e}")
        return 1
    word = {"fine": "Battery", "getting-low": "Battery getting low", "low": "Low battery"}[x["lvl"]]
    text = f"{word}: {x['pct']}% · {how_words(x)}"
    print(text)
    if dry:
        print(json.dumps(x))
        return 0
    write(x)
    state = {"fine": "ok", "getting-low": "low", "low": "down"}[x["lvl"]]
    routines.beat("battery", state=state, text=text, last=now, next=now + 60, every=60)
    if x["lvl"] == "low":
        incidents.down("battery", f"{x['pct']}% and on battery")
    else:
        incidents.up("battery")
    return 0


if __name__ == "__main__":
    sys.exit(main(dry="--dry" in sys.argv[1:]))
