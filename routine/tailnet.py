#!/usr/bin/env python3
"""Is Tailscale on here (H234, 22 October 2026)?

In the user's words (quick note, 21 October 2026): "ok my tailscale was turned off somehow, i turned it back on
and suddenly 'the vps is back' thats not what happened ofcourse. i want in the routines a check for tailscale and
if it is not on, then it can conclude that might be the reason there is no 'connection' with the vps".

Two HQs reach each other over Tailscale (the other's status page is a tailnet name). When Tailscale is off on
this computer, the other one can't be reached from here, but it hasn't gone down. So the heartbeat, Main or
backup, the incidents and Donna's texts ask this first: with Tailscale off here they say that, and the backup
doesn't take over (the same as when this computer is offline itself).

state()   "on", "off", or None when this computer has no Tailscale (then nothing is said about it)
matters() the other HQ is reached over the tailnet (a .ts.net name or a 100.64/10 address)
off_here() both: Tailscale is the reason the other can't be reached from here

[Claude's choices: Stopped, NeedsLogin and NeedsMachineAuth are off; Starting and anything else not known count as
on, so a computer that is just connecting isn't called off; a Tailscale installed but not running (its app or
daemon stopped) is off. HQ_TAILSCALE=on|off fixes it for a test, and then it always matters.]

usage: python3 routine/tailnet.py     on, off or none, printed
"""
from __future__ import annotations

import ipaddress, json, os, subprocess, sys, time, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths

OFF = ("Stopped", "NeedsLogin", "NeedsMachineAuth")
MAC_APP = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"  # the Mac app's own command line
_cache: dict = {}


def _command() -> str | None:
    for path in (hqpaths.tool("tailscale", "/usr/local/bin/tailscale"), "/opt/homebrew/bin/tailscale", MAC_APP):
        if path and os.path.exists(path):
            return path
    return None


def state() -> str | None:
    """'on', 'off' or None (no Tailscale on this computer). Looked at once per 20 seconds at most."""
    fixed = os.environ.get("HQ_TAILSCALE")
    if fixed in ("on", "off"):
        return fixed
    if fixed == "none":
        return None
    if _cache and time.monotonic() - _cache["t"] < 20:
        return _cache["v"]
    ts = _command()
    if not ts:
        v = None
    else:
        try:  # status needs no sudo, on Linux too
            r = subprocess.run([ts, "status", "--json"], capture_output=True, text=True, timeout=8)
            try:
                v = "off" if json.loads(r.stdout).get("BackendState") in OFF else "on"
            except ValueError:
                v = "off"  # installed, but its daemon or app isn't running: no tailnet
        except (OSError, subprocess.TimeoutExpired):
            v = None  # can't tell: say nothing
    _cache.update(t=time.monotonic(), v=v)
    return v


def matters(c: dict | None) -> bool:
    """The other HQ is reached over the tailnet, so Tailscale being off here cuts it off."""
    if os.environ.get("HQ_TAILSCALE") in ("on", "off"):
        return True
    if not c:
        return False
    hosts = [urllib.parse.urlsplit(c.get("peer") or "").hostname or "", c.get("peer_ip") or ""]
    for h in hosts:
        if h.endswith(".ts.net"):
            return True
        try:
            if ipaddress.ip_address(h) in ipaddress.ip_network("100.64.0.0/10"):
                return True
        except ValueError:
            pass
    return False


def off_here(c: dict | None) -> bool:
    return matters(c) and state() == "off"


if __name__ == "__main__":
    print(state() or "none")
