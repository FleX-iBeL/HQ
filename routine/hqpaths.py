"""Where HQ is, and where the user's own files are (phase M, M1, 10 October 2026).

HQ is the app: the same for everyone, its code in this folder. The user's own data lives in one
folder at the top of HQ called workspace, which the HQ repo ignores completely (it may be a link
to a folder elsewhere). Runtime state (scratch/, .status/) stays in HQ, also
ignored by the repo.

    HQ         this app's folder (the parent of routine/)
    WORKSPACE  HQ/workspace, or HQ_WORKSPACE
    FOLDER     the workspace with the link resolved: where Claude works, git runs and jobs start
               (the same path a chat in that folder has, so its settings and memory are found)
    DATA       FOLDER/HQ: the roadmap with its status block and queue, and the call transcripts
    ROADMAP    DATA/roadmap.md, or HQ_ROADMAP
"""
from __future__ import annotations

import os

HQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
WORKSPACE = os.environ.get("HQ_WORKSPACE") or os.path.join(HQ, "workspace")
FOLDER = os.path.realpath(WORKSPACE)
DATA = os.path.join(FOLDER, "HQ")
ROADMAP = os.environ.get("HQ_ROADMAP") or os.path.join(DATA, "roadmap.md")


def agent_label(name: str, default_prefix: str = "com.hq") -> str:
    """The id of an installed LaunchAgent, e.g. agent_label("watchdog"): the one in
    ~/Library/LaunchAgents ending in .<name>.plist (an older install may use another prefix),
    else com.hq.<name>, as this HQ installs it."""
    folder = os.path.expanduser("~/Library/LaunchAgents")
    try:
        found = sorted(f for f in os.listdir(folder) if f.endswith(f".{name}.plist"))
    except OSError:
        found = []
    return found[0][:-len(".plist")] if found else f"{default_prefix}.{name}"


# H59 (11 October 2026): the user's own builds. As asked on the call of 13:14: "if my friends on windows
# have to build their own things, wont it erase what they have built and then need to do it again?" So HQ has one
# place for them, local/ at the top of HQ: ignored by HQ's repo, never touched by an update, never uploaded. Where
# HQ has a part that differs per computer (starting the call line, opening a job's window, the watchdog, starting
# at login...), it looks there first: local/<name> with any of the endings below. [Claude's choice of the name
# local/ and of looking by name.] The names HQ looks for are listed in README.md, "Your own parts".
LOCAL = os.environ.get("HQ_LOCAL") or os.path.join(HQ, "local")
_ENDINGS = ("", ".sh", ".py", ".ps1", ".cmd", ".bat")


def part(name: str) -> str | None:
    """The user's own version of a platform part, local/<name>[.sh|.py|.ps1|.cmd|.bat], or None."""
    for end in _ENDINGS:
        p = os.path.join(LOCAL, name + end)
        if os.path.isfile(p):
            return p
    return None


def part_cmd(name: str, *args: str) -> list[str] | None:
    """The command that runs the user's own part (by its ending), or None when there is none."""
    p = part(name)
    if not p:
        return None
    if p.endswith(".py"):
        import sys
        return [sys.executable or "python3", p, *args]
    if p.endswith(".ps1"):
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", p, *args]
    if p.endswith((".cmd", ".bat")):
        return ["cmd", "/c", p, *args]
    if p.endswith(".sh"):
        return ["/bin/sh", p, *args]
    return [p, *args]
