"""H238: an agent calls him, and he picks up from the notification.

22 October 2026, call at 13:03 (Pepper), in the user's words: "let's say we had an appointment or something you can
call me. Is that possible with the limitations that we run this as a headless browser?" A call or Donna's chat sets
it with routine/pings.py call (a time, or an appointment); at that time the main pushes "<agent> is calling" on the
direct line's push (direct_line.ring). One tap opens HQ with ?ring=N; the call page starts the call with that agent
and sends ring=N, and bot.py gets the call here: picked up (pings.py answered, so no missed call), and what the
call is about, the same way as a call started from an appointment (call._about: when_line, greetings, call_note).
No phone number, no paid service, no native app: iOS doesn't let a web app ring like a phone call.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "routine"))


def about(ref: str) -> dict | None:
    """The call with this number, marked picked up; None when there's no such call."""
    if not str(ref).isdigit():
        return None
    import pings
    c = pings.call_get(int(ref))
    if c is None:
        return None
    try:  # picked up; on the backup the main writes it (role.WRITES), so through the script
        subprocess.run([sys.executable, str(ROOT / "routine" / "pings.py"), "answered", str(c["n"])],
                       capture_output=True, text=True, timeout=30, cwd=str(ROOT),
                       env={**os.environ, "HQ_PINGS_BY": "the call page"})
    except Exception:
        pass
    try:
        who = pings.call_agent(c.get("agent", ""))
    except ValueError:
        return None
    return {"kind": "ring", "n": c["n"], "agent": who["id"], "agent_name": who["name"], "what": c.get("what", ""),
            "title": c.get("title", "") or c.get("what", ""), "at": c.get("at", ""), "appt": c.get("appt", ""),
            "start": c.get("start", "")}


def when_line(e: dict) -> str:
    return f"{e.get('what', '')} ({e.get('agent_name', '')} called at {e.get('at', '')[11:16]})"


def greetings(e: dict, name: str = "") -> list[str]:
    """Her opening when he picks up: she's the one calling (wording Claude's choice)."""
    n = f" {name}" if name else ""
    return [f"Hey{n}, it's {e.get('agent_name', 'me')}, calling like we said.",
            f"Hi{n}, {e.get('agent_name', 'me')} here, ringing you as promised."]


def call_note(e: dict, user: str = "the user") -> str:
    appt = f" It's for the appointment {e['title']} ({e.get('start', '')[:16].replace('T', ' ')})." if e.get("appt") else ""
    return (
        f"You called {user}: this is the call you agreed to make at {e.get('at', '')[11:16]}, about: "
        f"{e.get('what', '')}.{appt} The call system rang his phone with a notification, \"{e.get('agent_name', '')} "
        "is calling\", and he just picked up; it greets him as you calling like you said. Then bring up why you're "
        "calling yourself, in a sentence, the way a person who rings someone does, and go from there."
    )
