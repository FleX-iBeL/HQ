#!/usr/bin/env python3
"""The hourly mail check's output, read as it streams (L10). The mail check runs claude -p with
--output-format stream-json; its own run already brings the plan limits back (the stream's
rate_limit_event). This saves them to usage-live.json, in the status line's shape, for the usage
check, so the status page gets fresh numbers every hour for free. It prints the mail check's final
answer, as the log always had it. 9 October 2026: "I think the hourly one on that routine
is also free because it automatically checks. If there's new emails, right? So it should also get
that information back."
"""
import json, os, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.normpath(os.path.join(HERE, "..", "scratch", "routine", "usage-live.json"))


def epoch(v):
    """resetsAt as epoch seconds, as the status line gives it."""
    if isinstance(v, (int, float)):
        return v / 1000 if v > 1e11 else v
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


windows, answer = None, None
for line in sys.stdin:
    try:
        d = json.loads(line)
    except ValueError:
        print(line, end="")  # not the stream (an error message): keep it in the log
        continue
    if d.get("type") == "rate_limit_event":
        windows = (d.get("rate_limit_info") or {}).get("unifiedWindows") or windows
    elif d.get("type") == "result":
        answer = d.get("result") or d.get("subtype")
        if d.get("is_error"):  # H42: say so, so the reason can be read afterwards
            print(f"(the run ended with an error: {d.get('subtype') or 'error'})")

if answer:
    print(answer)
out = {}
for key in ("five_hour", "seven_day"):
    w = (windows or {}).get(key) or {}
    if isinstance(w.get("utilization"), (int, float)):
        out[key] = {"used_percentage": round(w["utilization"] * 100, 1), "resets_at": epoch(w.get("resetsAt"))}
if out:
    os.makedirs(os.path.dirname(LIVE), exist_ok=True)
    with open(LIVE + ".tmp", "w") as f:
        json.dump({"savedAt": datetime.now().astimezone().isoformat(timespec="seconds"), "rate_limits": out,
                   "by": "mail check"}, f)
    os.replace(LIVE + ".tmp", LIVE)
    print("(usage saved from the mail check's own run: "
          + ", ".join(f"{k} {v['used_percentage']:.0f}%" for k, v in out.items()) + ")")
else:
    print("(the mail check's run brought no usage back)")
