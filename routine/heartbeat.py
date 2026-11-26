#!/usr/bin/env python3
"""Heartbeats for both computers, as their own routines (H88, 13 October 2026).

In the user's words (call of 12 October 2026 at 18:40): "I also want separate routines that just does...
Connectivity checks, so just heartbeats for both the laptop and the VPS. This way we can always see from both.
I think it's a little bit more about the main or backup. I think this makes it more complete."

So with a second HQ set up, each HQ writes two routine lines every minute, apart from the Main or backup line:
one for this computer (it's up, and it reaches the internet) and one for the other (it answers). Both status
pages then show both computers, each under its short name (hqpaths.short_name: the VPS, the Laptop). Alone (no
other HQ) there are no heartbeat lines at all, the same as Main or backup.

H234 (22 October 2026): when the other is reached over Tailscale, a third line says whether Tailscale is on here.
Off, the other's line says it can't be reached from here because of that (yellow, no missed answers, no incident:
it hasn't gone down), the Tailscale line is red with its own incident (Donna texts it as Tailscale being off, not
as something down), and when the other answers again after its Tailscale was off, the fix says so.

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
import tailnet  # H234: Tailscale off here is why the other can't be reached, not the other going down

STATE = os.path.join(hqpaths.SUPPORT, "heartbeat-state.json")
PREFIX = "beat-"
EVERY = 60
RED_AFTER = 2  # missed answers in a row before the other computer's line is red (Claude's choice)


def key(name: str) -> str:
    return PREFIX + (re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "other")


def _clock(t):
    return time.strftime("%H:%M", time.localtime(t or time.time()))


def look(c, s, now, online=None, peer=None, tailscale=None) -> tuple[dict, dict]:
    """One look: (this computer's line, the other's line), each {name, state, text}. Updates s. H234: also keeps
    in s whether Tailscale is off here ("ts": on, off or None, "ts_off_since"), which the tick turns into its own
    line; while it's off, the other's line says so and counts no missed answers."""
    me = hqpaths.short_name()
    ts = (tailscale or None) if tailscale is not None else tailnet.state() if tailnet.matters(c) else None
    s["ts"] = ts
    if ts == "off":
        s["ts_off_since"] = s.get("ts_off_since") or now
    elif s.get("ts_off_since") and ts == "on":
        s["ts_last_off"] = [s["ts_off_since"], now]  # told to the other one on its next look (role.mine)
        s["ts_off_since"] = None
    elif ts is None:
        s["ts_off_since"] = None
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
        s["peer_ts_off"] = p.get("tailscale_off")  # H234: when Tailscale was off over there, last
    name = s.get("peer_label") or c.get("peer_name") or "The other HQ"
    if key(name) == key(me):
        name = f"{name} (the other one)"
    if p:
        s.update(peer_ok=now, misses=0, lost_since=None)
        other = {"name": name, "state": "ok", "text": f"Answers ({ms} ms)"}
    elif ts == "off":  # H234: not the other going down; nothing counts as missed until Tailscale is on again
        s.update(misses=0, lost_since=None)
        other = {"name": name, "state": "waiting",
                 "text": f"Can't be reached from here: Tailscale is off on this computer since {_clock(s['ts_off_since'])}"}
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


def ts_line(s, me, other) -> dict | None:
    """H234: this computer's Tailscale line, only when the other HQ is reached over it and Tailscale is here."""
    if not s.get("ts"):
        return None
    name = f"{me} · Tailscale"
    about = "Only with a second HQ reached over Tailscale: every minute, whether Tailscale is on on this computer"
    if s["ts"] == "on":
        return {"name": name, "state": "ok", "text": f"On: {other} is reached over it", "about": about}
    return {"name": name, "state": "down", "about": about,
            "text": f"Off since {_clock(s.get('ts_off_since'))}: {other} can't be reached from here until it's on again"}


def _back_text(name, s, now, lost):
    """The other one answers again: and if Tailscale was off over there in that time, say so (H234)."""
    off = s.get("peer_ts_off") or []
    lost = lost or now
    if len(off) == 2 and off[1] >= lost - 60:
        return (f"{name} answered again at {_clock(now)}; it hadn't gone down: Tailscale was off there from "
                f"{_clock(off[0])} to {_clock(off[1])}")
    return f"{name} answered again at {_clock(now)}"


def tick(routines=None, incidents=None, log=None, now=None, online=None, peer=None, tailscale=None) -> dict | None:
    """The routine's minute, on both HQs (main and backup). Writes the two lines (H234: three, with this computer's
    Tailscale), opens and closes their incidents. Alone: removes any heartbeat lines left from a pairing and returns None, with no network."""
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
    was_lost = s.get("lost_since")
    mine, other = look(c, s, now, online=online, peer=peer, tailscale=tailscale)
    ts = ts_line(s, mine["name"], other["name"])
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE + ".tmp", "w") as f:
        json.dump(s, f)
    os.replace(STATE + ".tmp", STATE)
    keys = []
    for line in (mine, other, *([ts] if ts else [])):
        k = key(line["name"])
        keys.append(k)
        if routines:
            routines.beat(k, state=line["state"], text=line["text"], name=line["name"], last=now, next=now + EVERY,
                          every=EVERY, **({"about": line["about"]} if line.get("about") else {}))
        if incidents:
            if line is other and s.get("ts") == "off" and incidents.is_down(k):
                # H234: it was never the other one going down: Tailscale is off here.
                incidents.fix(k, f"It hadn't gone down: Tailscale is off on {mine['name']}, so it can't be reached "
                                 "from here", at=now)
                incidents.up(k, at=now)
            elif line["state"] == "down" and not incidents.is_down(k):
                why = (f"{line['name']} couldn't reach the internet" if line is mine else
                       f"Tailscale is off on {mine['name']}, so {other['name']} can't be reached from here; it hasn't "
                       "gone down" if line is ts else f"{line['name']} stopped answering")
                incidents.down(k, why, at=s.get("offline_since") if line is mine else
                               s.get("ts_off_since") if line is ts else s.get("lost_since"))
                if log:
                    log(f"heartbeat: {line['name']} down: {line['text']}")
            elif line["state"] == "ok" and incidents.is_down(k):
                incidents.fix(k, f"Tailscale is on again at {_clock(now)}; {other['name']} can be reached" if line is ts
                              else _back_text(line["name"], s, now, was_lost) if line is other
                              else f"{line['name']} answered again at {_clock(now)}", at=now)
                incidents.up(k, at=now)
                if log:
                    log(f"heartbeat: {line['name']} back")
    if routines:
        routines.drop(PREFIX, keep=keys)  # a computer that got another name leaves no old line behind
    if incidents:  # nor an open incident under its old name (H162, 18 October 2026)
        for k in {i["key"] for i in incidents.read()["incidents"]
                  if i["key"].startswith(PREFIX) and i["key"] not in keys and not i.get("back")}:
            incidents.fix(k, "Tailscale isn't looked at here any more; its line is gone" if k.endswith("-tailscale")
                          else "It goes by another name now; its old line is gone", at=now)
            incidents.up(k, at=now)
    return {"here": mine, "other": other}


if __name__ == "__main__":
    c = role.config()
    if not c:
        print("This HQ is on its own: no heartbeat lines.")
    else:
        s = {}
        mine, other = look(c, s, time.time())
        for line in (mine, other, *([ts_line(s, mine["name"], other["name"])] if s.get("ts") else [])):
            print(f"{line['name']}: {line['state']}: {line['text']}")
