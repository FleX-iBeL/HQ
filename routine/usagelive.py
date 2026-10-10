"""The plan limits a Claude run brings back with it, saved for the usage check (L10, H51).

A Claude run on the plan login gets its usage back for free: the 5-hour and weekly windows in its
rate limit event (`unifiedWindows`). The hourly mail check reads them from its stream
(stream-usage.py) and a call reads them from its own session (app/brain.py, H51); both save them
here, to usage-live.json, in the status line's shape, so the usage check puts them on the status
page within a minute. Only the numbers: nothing else of the run.
"""
import json, os
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


def limits(windows):
    """The 5-hour and weekly numbers from a rate limit event's unifiedWindows, in the status line's shape."""
    out = {}
    for key in ("five_hour", "seven_day"):
        w = (windows or {}).get(key) or {}
        if isinstance(w.get("utilization"), (int, float)):
            out[key] = {"used_percentage": round(w["utilization"] * 100, 1), "resets_at": epoch(w.get("resetsAt"))}
    return out


def save(windows, by):
    """Save the numbers for the usage check; `by` names the source ("mail check", "call").
    Returns what was saved, or {} when the windows had no numbers (then nothing is written)."""
    out = limits(windows)
    if out:
        os.makedirs(os.path.dirname(LIVE), exist_ok=True)
        tmp = f"{LIVE}.{os.getpid()}.tmp"
        with open(tmp, "w") as f:
            json.dump({"savedAt": datetime.now().astimezone().isoformat(timespec="seconds"), "rate_limits": out,
                       "by": by}, f)
        os.replace(tmp, LIVE)
    return out


def summary(out):
    return ", ".join(f"{k} {v['used_percentage']:.0f}%" for k, v in out.items())
