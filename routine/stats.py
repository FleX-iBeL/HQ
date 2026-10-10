#!/usr/bin/env python3
"""H44: the totals Activity Monitor shows, every minute, run by the Jarvis Routine helper (tick.py). No
Claude, no usage, no password. 10 October 2026 (call at 19:46): "maybe we also want a good CPU.
Or GPU. Or both, and memory there. And maybe read-write. Just the things you see in the activity monitor.
And network too. So CPU, memory. Disk and network and then just the totals of it" and "it's not that
important. But it's just fun to have there."

- The raw counters come from routine/stats.m (built here with clang into scratch/routine/stats the first
  time and whenever the source changes): CPU ticks, the GPU's own use, memory pages, disk bytes read and
  written, network bytes in and out.
- CPU, disk and network are counters that only go up, so a reading is the difference with the last one,
  over the time in between (scratch/routine/stats-last.json): the average of that minute, like Activity
  Monitor's own totals. After a restart (a counter went down) that part is left empty once.
- Memory used is what Activity Monitor calls Memory Used: app memory, wired and compressed. Pressure is
  macOS's own (kern.memorystatus_level: how much is free; the pressure level: normal, warning, critical),
  plus the swap used.
- No alarms and no colours on any light: it's just there to look at. No routine line either.

Writes Jarvis VA/.status/stats.json (the latest reading) and appends one line a minute to
.status/stats-history.jsonl (a day kept).

    python3 "Jarvis VA/routine/stats.py"          one reading, written and printed
    python3 "Jarvis VA/routine/stats.py" --dry    one reading (over about two seconds), printed only
"""
import json, os, re, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
JV = os.path.normpath(os.path.join(HERE, ".."))
SRC = os.path.join(HERE, "stats.m")
BIN = os.path.join(JV, "scratch", "routine", "stats")
LAST = os.path.join(JV, "scratch", "routine", "stats-last.json")
NOW_FILE = os.path.join(JV, ".status", "stats.json")
HISTORY = os.path.join(JV, ".status", "stats-history.jsonl")
PRESSURE_WORD = {1: "normal", 2: "warning", 4: "critical"}


def build():
    if os.path.exists(BIN) and os.path.getmtime(BIN) >= os.path.getmtime(SRC):
        return
    os.makedirs(os.path.dirname(BIN), exist_ok=True)
    r = subprocess.run(["/usr/bin/clang", "-O2", "-fobjc-arc", "-o", BIN, SRC, "-framework", "Foundation",
                        "-framework", "IOKit"], capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise RuntimeError(f"building the stats reader failed: {(r.stderr or r.stdout).strip()[:200]}")


def raw():
    """The counters as they are now, with the time."""
    build()
    r = subprocess.run([BIN], capture_output=True, text=True, timeout=20)
    if r.returncode:
        raise RuntimeError(f"the stats reader failed: {(r.stderr or r.stdout).strip()[:200]}")
    x = json.loads(r.stdout.strip().splitlines()[-1])
    x["t"] = time.time()
    return x


def sysctl(name):
    r = subprocess.run(["/usr/sbin/sysctl", "-n", name], capture_output=True, text=True, timeout=10)
    return r.stdout.strip() if r.returncode == 0 else ""


def swap_used():
    """vm.swapusage: 'total = 2048.00M  used = 1093.50M  free = 954.50M  (encrypted)' -> bytes used."""
    m = re.search(r"used = ([\d.]+)([KMG])", sysctl("vm.swapusage"))
    return int(float(m.group(1)) * {"K": 2**10, "M": 2**20, "G": 2**30}[m.group(2)]) if m else None


def rate(new, old, secs):
    """Per second between two counter values; None after a restart (the counter went down) or no time."""
    if old is None or new is None or secs <= 0 or new < old:
        return None
    return (new - old) / secs


def reading(now, last, pressure_free=None, pressure_level=None, swap=None):
    """One reading from the counters now and the ones a minute ago (last may be None)."""
    x = {"t": int(now["t"])}
    secs = now["t"] - last["t"] if last else 0
    c, lc = now.get("cpu"), (last or {}).get("cpu")
    if c and lc:
        busy = lambda d: d["user"] + d["system"] + d["nice"]
        tot = lambda d: busy(d) + d["idle"]
        dt = tot(c) - tot(lc)
        x["cpu"] = round(100 * (busy(c) - busy(lc)) / dt, 1) if dt > 0 and busy(c) >= busy(lc) else None
        if dt > 0 and x["cpu"] is not None:
            x["cpu_user"] = round(100 * (c["user"] + c["nice"] - lc["user"] - lc["nice"]) / dt, 1)
            x["cpu_system"] = round(100 * (c["system"] - lc["system"]) / dt, 1)
    else:
        x["cpu"] = None
    x["gpu"] = now.get("gpu")
    m = now.get("mem")
    if m:
        pg = m["page"]
        x["mem_total"] = m["total"]
        x["mem_app"] = max(0, m["internal"] - m["purgeable"]) * pg
        x["mem_wired"] = m["wired"] * pg
        x["mem_compressed"] = m["compressed"] * pg
        x["mem_used"] = x["mem_app"] + x["mem_wired"] + x["mem_compressed"]
    x["mem_pressure"] = None if pressure_free is None else max(0, 100 - pressure_free)
    x["mem_level"] = PRESSURE_WORD.get(pressure_level, None)
    x["swap"] = swap
    d, ld = now.get("disk", {}), (last or {}).get("disk", {})
    x["disk_read"] = rate(d.get("read"), ld.get("read"), secs)
    x["disk_write"] = rate(d.get("written"), ld.get("written"), secs)
    n, ln = now.get("net", {}), (last or {}).get("net", {})
    x["net_in"] = rate(n.get("in"), ln.get("in"), secs)
    x["net_out"] = rate(n.get("out"), ln.get("out"), secs)
    for k in ("disk_read", "disk_write", "net_in", "net_out"):
        if x[k] is not None:
            x[k] = round(x[k])
    x["over"] = round(secs) if last else None
    return x


def size(b, per_s=False):
    """Bytes in plain words: 1.2 GB, 340 KB/s. Memory counts in 1024s, as Activity Monitor does (16 GB),
    the speeds in 1000s."""
    if b is None:
        return "–"
    k = 1000 if per_s else 1024
    for unit, f in (("GB", k ** 3), ("MB", k ** 2), ("KB", k)):
        if b >= f:
            v = b / f
            return f"{v:.1f} {unit}{'/s' if per_s else ''}" if v < 100 else f"{v:.0f} {unit}{'/s' if per_s else ''}"
    return f"{b:.0f} B{'/s' if per_s else ''}"


def words(x):
    cpu = "–" if x.get("cpu") is None else f"{x['cpu']:.0f}%"
    gpu = "–" if x.get("gpu") is None else f"{x['gpu']}%"
    return (f"CPU {cpu} · GPU {gpu} · memory {size(x.get('mem_used'))} of {size(x.get('mem_total'))}"
            f" · disk {size(x.get('disk_read'), True)} read, {size(x.get('disk_write'), True)} written"
            f" · network {size(x.get('net_in'), True)} in, {size(x.get('net_out'), True)} out")


def write(x, now_raw):
    os.makedirs(os.path.dirname(NOW_FILE), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(NOW_FILE), prefix=".stats")
    with os.fdopen(fd, "w") as f:
        json.dump({**x, "words": words(x)}, f)
    os.replace(tmp, NOW_FILE)
    with open(HISTORY, "a") as f:
        f.write(json.dumps({k: x.get(k) for k in ("t", "cpu", "gpu", "mem_used", "mem_total", "mem_pressure", "mem_level",
                                                  "disk_read", "disk_write", "net_in", "net_out")}) + "\n")
    lines = open(HISTORY).read().splitlines()
    if len(lines) > 1500:
        with open(HISTORY, "w") as f:
            f.write("\n".join(lines[-1440:]) + "\n")
    os.makedirs(os.path.dirname(LAST), exist_ok=True)
    with open(LAST, "w") as f:
        json.dump(now_raw, f)


def main(dry=False):
    try:
        if dry:
            last = raw()
            time.sleep(2)
        else:
            try:
                last = json.load(open(LAST))
            except Exception:
                last = None
        now = raw()
        if last and now["t"] - last["t"] > 15 * 60:
            last = None  # asleep or off in between: the average of hours means nothing
        free = sysctl("kern.memorystatus_level")
        level = sysctl("kern.memorystatus_vm_pressure_level")
        x = reading(now, last, int(free) if free.isdigit() else None, int(level) if level.isdigit() else None, swap_used())
    except Exception as e:
        print(f"Can't read the laptop stats: {e}")
        return 1
    print(words(x))
    if dry:
        print(json.dumps(x))
        return 0
    write(x, now)
    return 0


if __name__ == "__main__":
    sys.exit(main(dry="--dry" in sys.argv[1:]))
