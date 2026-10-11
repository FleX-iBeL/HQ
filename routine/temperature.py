#!/usr/bin/env python3
"""H35: the laptop's temperature, every minute, run by the HQ Routine helper (tick.py). No Claude,
no usage, no password. 10 October 2026, with the lid closed and the MacBook in his bag while
jobs build: "I was thinking maybe we can build a routine and it also checks it continuously and it shows
a little graph. Or... In the status bars, we put ranges and colors on it."

- The degrees come from the Apple Silicon sensors through IOKit (routine/thermal.m, built here with
  clang into scratch/routine/thermal the first time and whenever the source changes). No admin rights.
- The heat warning comes from macOS itself: its heat state (nominal, fair, serious, critical) and
  `pmset -g therm` (a thermal or performance warning level, or a CPU speed limit under 100%).
- The ranges, for this MacBook Air M2 (no fan; it starts slowing itself down around 100 degrees on the
  chip): normal under 70, warm 70 to 89, hot from 90. Slowing down (macOS heat state serious or
  critical, a warning level, a speed limit) counts as hot whatever the degrees.

Writes .status/temperature.json (the latest reading), appends one line a minute to
.status/temperature-history.jsonl (a day kept), writes its routine line ("temp": ok, warm, or down when
hot) and opens an incident while it's hot.

    python3 "routine/temperature.py"          one reading, written and printed
    python3 "routine/temperature.py" --dry    one reading, printed only
"""
import json, os, re, subprocess, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routines
import incidents

HERE = os.path.dirname(os.path.abspath(__file__))
JV = os.path.normpath(os.path.join(HERE, ".."))
SRC = os.path.join(HERE, "thermal.m")
BIN = os.path.join(JV, "scratch", "routine", "thermal")
NOW_FILE = os.path.join(JV, ".status", "temperature.json")
HISTORY = os.path.join(JV, ".status", "temperature-history.jsonl")
WARM, HOT = 70, 90  # degrees on the hottest chip die
STATE_WORD = {0: "normal", 1: "fair", 2: "serious", 3: "critical"}


def build():
    if os.path.exists(BIN) and os.path.getmtime(BIN) >= os.path.getmtime(SRC):
        return
    os.makedirs(os.path.dirname(BIN), exist_ok=True)
    r = subprocess.run(["/usr/bin/clang", "-O2", "-fobjc-arc", "-o", BIN, SRC, "-framework", "Foundation",
                        "-framework", "IOKit"], capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise RuntimeError(f"building the sensor reader failed: {(r.stderr or r.stdout).strip()[:200]}")


def pmset():
    """macOS's own heat warning: (thermal warning level, performance warning level, CPU speed limit %)."""
    out = subprocess.run(["/usr/bin/pmset", "-g", "therm"], capture_output=True, text=True, timeout=20).stdout
    def level(kind):
        m = re.search(rf"{kind} warning level.*?(\d+)", out, re.I)
        return int(m.group(1)) if m else 0
    m = re.search(r"CPU_Speed_Limit\s*=\s*(\d+)", out)
    return level("thermal"), level("performance"), int(m.group(1)) if m else 100


def judge(cpu, state, therm, perf, speed):
    """normal, warm or hot, and whether macOS is slowing the laptop down."""
    slow = state >= 2 or therm > 0 or perf > 0 or speed < 100
    if slow or cpu >= HOT:
        return "hot", slow
    if cpu >= WARM:  # macOS says "fair" already at ~60 degrees, so that alone isn't warm
        return "warm", slow
    return "normal", slow


def read():
    build()
    r = subprocess.run([BIN], capture_output=True, text=True, timeout=20)
    data = json.loads(r.stdout.strip() or "{}")
    if r.returncode or data.get("cpu", -1) < 0:
        raise RuntimeError("no chip temperature sensors answered")
    therm, perf, speed = pmset()
    level, slow = judge(data["cpu"], data.get("state", 0), therm, perf, speed)
    return {"t": int(time.time()), "cpu": data["cpu"], "avg": data.get("cpu_avg"),
            "bat": data["battery"] if data.get("battery", -1) >= 0 else None,
            "st": data.get("state", 0), "therm": therm, "perf": perf, "speed": speed,
            "lvl": level, "slow": slow}


def heat_words(x):
    """macOS's heat warning in plain words."""
    if x["slow"]:
        parts = []
        if x["st"] >= 2:
            parts.append(f"macOS heat state {STATE_WORD.get(x['st'], x['st'])}")
        if x["speed"] < 100:
            parts.append(f"CPU held to {x['speed']}%")
        if x["therm"] or x["perf"]:
            parts.append(f"warning level {max(x['therm'], x['perf'])}")
        return "Slowing itself down: " + ", ".join(parts)
    return "No heat warning, not slowing down" if x["st"] == 0 else f"No heat warning; macOS heat state {STATE_WORD.get(x['st'], x['st'])}"


def write(x):
    os.makedirs(os.path.dirname(NOW_FILE), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(NOW_FILE), prefix=".temperature")
    with os.fdopen(fd, "w") as f:
        json.dump({**x, "heat": heat_words(x), "ranges": {"warm": WARM, "hot": HOT}}, f)
    os.replace(tmp, NOW_FILE)
    with open(HISTORY, "a") as f:
        f.write(json.dumps({k: x[k] for k in ("t", "cpu", "avg", "bat", "st", "lvl", "slow")}) + "\n")
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
            routines.beat("temp", state="down", text=f"Can't read the temperature: {str(e)[:120]}", last=now,
                          next=now + 60, every=60)
        print(f"Can't read the temperature: {e}")
        return 1
    word = {"normal": "Normal", "warm": "Warm", "hot": "Hot"}[x["lvl"]]
    text = f"{word}: {x['cpu']:.0f}°C on the chip · {heat_words(x)}"
    print(text)
    if dry:
        print(json.dumps(x))
        return 0
    write(x)
    state = {"normal": "ok", "warm": "warm", "hot": "down"}[x["lvl"]]
    routines.beat("temp", state=state, text=text, last=now, next=now + 60, every=60)
    if x["lvl"] == "hot":
        incidents.down("temp", f"{x['cpu']:.0f}°C on the chip; {heat_words(x)}")
    else:
        incidents.up("temp")
    return 0


if __name__ == "__main__":
    sys.exit(main(dry="--dry" in sys.argv[1:]))
