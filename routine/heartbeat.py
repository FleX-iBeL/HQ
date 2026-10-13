#!/usr/bin/env python3
"""Heartbeats for both computers, as their own routines (H88, 13 October 2026).

In the user's words (call of 12 October 2026 at 18:40): "I also want separate routines that just does...
Connectivity checks, so just heartbeats for both the laptop and the VPS. This way we can always see from both.
I think it's a little bit more about the main or backup. I think this makes it more complete."

So with a second HQ set up, each HQ writes two routine lines every minute, apart from the Main or backup line:
one for this computer (it's up, and it reaches the internet) and one for the other (it answers). Both status
pages then show both computers, each under its short name (hqpaths.short_name: the VPS, the Laptop). Alone (no
other HQ) there are no heartbeat lines at all, the same as Main or backup.

[Claude's choices: one missed answer is yellow (one look can time out), two in a row are red and an incident;
when this computer can't reach the internet itself, the other one's line says it can't tell, not that it's
down.]

Kept in HQ's own memory (hqpaths.SUPPORT): heartbeat-state.json, {"peer_label", "peer_ok", "misses",
"lost_since", "offline_since"}.

usage: python3 routine/heartbeat.py      one look, printed (doesn't write the lines)
"""
from __future__ import annotations

import json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths
import role

STATE = os.path.join(hqpaths.SUPPORT, "heartbeat-state.json")
PREFIX = "beat-"
EVERY = 60
RED_AFTER = 2  # missed answers in a row before the other computer's line is red (Claude's choice)


def key(name: str) -> str:
    return PREFIX + (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "other")


def _clock(t):
    return time.strftime("%H:%M", time.localtime(t or time.time()))


def look(c, s, now, online=None, peer=None) -> tuple[dict, dict]:
    """One look: (this computer's line, the other's line), each {name, state, text}. Updates s."""
    me = hqpaths.short_name()
    up = role.online() if online is None else online
    if up:
        s["offline_since"] = None
        mine = {"name": me, "state": "ok", "text": "Up and online"}
    else:
        s["offline_since"] = s.get("offline_since") or now
        mine = {"name": me, "state": "down",
                "text": f"Up, but can't reach the internet since {_clock(s['offline_since'])}"}
    t0 = time.monotonic()
    p = role.peer_role(c) if peer is None else (peer or None)
    ms = int((time.monotonic() - t0) * 1000)
    if p:
        s["peer_label"] = p.get("label") or s.get("peer_label") or p.get("name")
    name = s.get("peer_label") or c.get("peer_name") or "The other HQ"
    if key(name) == key(me):
        name = f"{name} (the other one)"
    if p:
        s.update(peer_ok=now, misses=0, lost_since=None)
        other = {"name": name, "state": "ok", "text": f"Answers ({ms} ms)"}
    else:
        s["misses"] = int(s.get("misses") or 0) + 1
        s["lost_since"] = s.get("lost_since") or now
        seen = f"; last answer {_clock(s['peer_ok'])}" if s.get("peer_ok") else ""
        if not up:
            other = {"name": name, "state": "waiting", "text": "Can't tell: this computer can't reach the internet"}
        elif s["misses"] < RED_AFTER:
            other = {"name": name, "state": "waiting", "text": f"Missed one answer; looking again in a minute{seen}"}
        else:
            other = {"name": name, "state": "down", "text": f"Doesn't answer since {_clock(s['lost_since'])}{seen}"}
    return mine, other


def tick(routines=None, incidents=None, log=None, now=None, online=None, peer=None) -> dict | None:
    """The routine's minute, on both HQs (main and backup). Writes the two lines, opens and closes their
    incidents. Alone: removes any heartbeat lines left from a pairing and returns None, with no network."""
    c = role.config()
    if not c:
        if routines:
            routines.drop(PREFIX)
        return None
    now = now or time.time()
    try:
        s = json.load(open(STATE))
    except (OSError, ValueError):
        s = {}
    mine, other = look(c, s, now, online=online, peer=peer)
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE + ".tmp", "w") as f:
        json.dump(s, f)
    os.replace(STATE + ".tmp", STATE)
    keys = []
    for line in (mine, other):
        k = key(line["name"])
        keys.append(k)
        if routines:
            routines.beat(k, state=line["state"], text=line["text"], name=line["name"], last=now, next=now + EVERY,
                          every=EVERY)
        if incidents:
            if line["state"] == "down" and not incidents.is_down(k):
                why = (f"{line['name']} couldn't reach the internet" if line is mine else
                       f"{line['name']} stopped answering")
                incidents.down(k, why, at=s.get("offline_since") if line is mine else s.get("lost_since"))
                if log:
                    log(f"heartbeat: {line['name']} down: {line['text']}")
            elif line["state"] == "ok" and incidents.is_down(k):
                incidents.fix(k, f"{line['name']} answered again at {_clock(now)}", at=now)
                incidents.up(k, at=now)
                if log:
                    log(f"heartbeat: {line['name']} back")
    if routines:
        routines.drop(PREFIX, keep=keys)  # a computer that got another name leaves no old line behind
    return {"here": mine, "other": other}


if __name__ == "__main__":
    c = role.config()
    if not c:
        print("This HQ is on its own: no heartbeat lines.")
    else:
        mine, other = look(c, {}, time.time())
        for line in (mine, other):
            print(f"{line['name']}: {line['state']}: {line['text']}")
