#!/usr/bin/env python3
"""The usage check (phase L: L9, without paid runs since L10). Shows the latest saved 5-hour and weekly
all-models usage on the status page, with how old it is. It never starts Claude, so it costs nothing.
9 October 2026: "how about if we only just... Run a routine that checks that. And... Just
showcase the latest data that it has."

Where the numbers come from, both free, both written to usage-live.json:
- A job's Terminal window: its status line (statusline.py) after every reply.
- The hourly mail check: its own run brings the plan limits back with it (stream-usage.py).
- A call: its Claude session brings them back too (app/brain.py, H51), the same way (usagelive.py).

What it does: when usage-live.json is newer than what the status page shows, it saves it there
(through save-usage.mjs --statusline --any, so Weekly Fable stays from a normal chat, greyed, as in
F7, and the reading keeps the time it was really read). A newer full reading from a normal chat is
never overwritten. Then it prints the numbers and how old they are.

The HQ Routine helper (tick.py) runs it every minute. A call runs it with no options when he
asks what the usage is:
    python3 "routine/usage-check.py"
"""
import json, os, subprocess, sys, time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
JV = os.path.normpath(os.path.join(HERE, ".."))
RUN = os.path.join(JV, "scratch", "routine")
LIVE = os.path.join(RUN, "usage-live.json")
SAVED = os.path.join(JV, ".status", "usage.json")
NODE = "/opt/homebrew/bin/node"
SOURCES = {"mail check": "the hourly mail check", "call": "a call", "": "a job's status line"}


def log(msg):
    os.makedirs(RUN, exist_ok=True)
    with open(os.path.join(RUN, "usage.log"), "a") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def when(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError):
        return None


def ago(t):
    m = int(max(0, time.time() - t) // 60)
    if m < 1:
        return "just now"
    if m < 60:
        return f"{m} min ago"
    return f"{m // 60} h {m % 60} min ago" if m < 24 * 60 else f"{m // 1440} days ago"


def load(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return None


def save_latest():
    """Saves usage-live.json for the status page when it's newer than what's there. True if it did."""
    live, saved = load(LIVE), load(SAVED)
    if not live or not (live.get("rate_limits") or {}):
        return False
    live_t = when(live.get("savedAt"))
    if live_t is None:
        return False
    if saved and saved.get("readable") and (when(saved.get("checkedAt")) or 0) >= live_t - 1:
        return False
    by = "usage check · from " + SOURCES.get(live.get("by", ""), SOURCES[""])
    r = subprocess.run([NODE, os.path.join(JV, "status", "save-usage.mjs"), "--statusline", "--any", "--by", by],
                       capture_output=True, text=True)
    log(f"{by}, read {ago(live_t)}: " + " / ".join(l.strip() for l in r.stdout.strip().splitlines()[:2]))
    return True


def report():
    saved = load(SAVED)
    if not saved or not saved.get("limits"):
        return "No usage has been saved yet."
    t = when(saved.get("checkedAt"))
    lines = []
    for l in saved["limits"]:
        reset = l.get("resetsAt") and (when(l["resetsAt"]) or 0) <= time.time()
        pct = 0 if reset else l.get("percent")
        if l.get("kept") or not saved.get("readable"):
            kt = when(l.get("keptAt") or saved.get("checkedAt"))
            age = f"reset since, no fresh reading" if reset else f"last known, read {ago(kt) if kt else 'some time ago'}"
        else:
            age = f"read {ago(t)}" if t else "time of reading unknown"
        lines.append(f"{pct}%  {l['label']}  ({age})")
    stale = t is not None and time.time() - t > 20 * 60
    lines.append("These numbers are old: nothing has read the usage since; they're greyed out on the status page."
                 if stale else "These are the latest numbers.")
    return "\n".join(lines)


def main():
    try:
        save_latest()
    except Exception as e:
        log(f"failed: {e!r}")
    print(report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
