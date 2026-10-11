#!/usr/bin/env python3
"""Status line for a job the routine started (phase L). Claude Code gives the status line what it
knows of the plan limits (rate_limits: five_hour, seven_day); this saves it for save-usage.mjs
--statusline, leaves a sign of life for the quiet-job check (H36), and shows one short line at the bottom of the Terminal window."""
import json, os, sys, time
from datetime import datetime

data = json.load(sys.stdin)
run = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scratch", "routine")
out = os.path.join(run, "usage-live.json")
# H36: a sign of life for routine/quiet.py: the status line runs after every reply and tool step.
try:
    act = os.environ.get("HQ_ACTIVITY") or os.path.join(run, "job-activity.json")
    with open(act + ".tmp", "w") as f:
        json.dump({"at": time.time(), "session": data.get("session_id"), "transcript": data.get("transcript_path")}, f)
    os.replace(act + ".tmp", act)
except Exception:
    pass
r = data.get("rate_limits") or {}
if r:
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"savedAt": datetime.now().astimezone().isoformat(timespec="seconds"), "rate_limits": r}, f)
    os.replace(tmp, out)
five = (r.get("five_hour") or {}).get("used_percentage")
week = (r.get("seven_day") or {}).get("used_percentage")
bits = [f"5-hour {five:.0f}%" if five is not None else "", f"week {week:.0f}%" if week is not None else ""]
print("HQ job · " + (" · ".join(b for b in bits if b) or "usage not known yet"))
