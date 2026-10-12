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
import re
import shutil
import socket
import subprocess
import sys

HQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
WORKSPACE = os.environ.get("HQ_WORKSPACE") or os.path.join(HQ, "workspace")
FOLDER = os.path.realpath(WORKSPACE)
DATA = os.path.join(FOLDER, "HQ")
ROADMAP = os.environ.get("HQ_ROADMAP") or os.path.join(DATA, "roadmap.md")

# H56.1 (12 October 2026): HQ also runs on a Linux server, as the routine and the watchdog (systemd there).
# The Mac stays exactly as it was; on Linux the same parts find their own places and programs.
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def support_dir() -> str:
    """HQ's own memory outside the workspace (the heartbeat, the watchdog's line and log, failures in a row):
    ~/Library/Application Support/HQ on a Mac (where macOS lets the watchdog read without asking), else
    $XDG_STATE_HOME/hq (~/.local/state/hq). HQ_SUPPORT puts it elsewhere, e.g. for a second HQ on one
    computer. watchdog.py runs on its own and works this out the same way."""
    if os.environ.get("HQ_SUPPORT"):
        return os.path.expanduser(os.environ["HQ_SUPPORT"])
    if IS_MAC:
        return os.path.expanduser("~/Library/Application Support/HQ")
    return os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state"), "hq")


SUPPORT = support_dir()

# Where a program may be when the helper runs it with a bare PATH (the Mac's helper app has only /usr/bin:/bin).
_EXTRA_PATH = ["/opt/homebrew/bin", "/usr/local/bin", os.path.expanduser("~/.npm-global/bin"),
               os.path.expanduser("~/.local/bin"), "/usr/bin", "/bin", "/usr/sbin", "/sbin"]


def tool(name: str, default: str) -> str:
    """A program's full path: HQ_<NAME> if set (e.g. HQ_NODE), else on a Mac `default` as before, else the
    first one found on PATH or in the usual places, else `default`."""
    env = os.environ.get("HQ_" + name.upper().replace("-", "_"))
    if env:
        return env
    if IS_MAC:
        return default
    path = os.pathsep.join([os.environ.get("PATH", ""), *_EXTRA_PATH])
    return shutil.which(name, path=path) or default


def tailscale(*args: str) -> list[str]:
    """The command for `tailscale <args>`. On Linux, Tailscale's serve settings belong to root unless the
    user was made its operator, so it runs through `sudo -n` there (never asks for a password; fails
    instead). HQ_TS_SUDO=0 leaves sudo out."""
    ts = tool("tailscale", "/usr/local/bin/tailscale")
    if IS_LINUX and os.geteuid() != 0 and os.environ.get("HQ_TS_SUDO", "1") != "0":
        return ["sudo", "-n", ts, *args]
    return [ts, *args]


def listening(port: int) -> bool:
    """Something listens on this computer's port: lsof on a Mac as before, a plain connect elsewhere."""
    if IS_MAC:
        r = subprocess.run(["/usr/sbin/lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"], capture_output=True, text=True)
        return bool(r.stdout.strip())
    try:
        socket.create_connection(("127.0.0.1", int(port)), timeout=2).close()
        return True
    except OSError:
        return False


def boottime() -> int:
    """When this computer last started (epoch seconds): kern.boottime on a Mac, btime in /proc/stat on Linux."""
    if IS_LINUX:
        try:
            for line in open("/proc/stat"):
                if line.startswith("btime "):
                    return int(line.split()[1])
        except OSError:
            pass
        return 0
    r = subprocess.run(["/usr/sbin/sysctl", "-n", "kern.boottime"], capture_output=True, text=True)
    m = re.search(r"sec = (\d+)", r.stdout)
    return int(m.group(1)) if m else 0


def waketime() -> int:
    """When a Mac last woke from sleep (kern.waketime); 0 elsewhere (a server doesn't sleep)."""
    if not IS_MAC:
        return 0
    r = subprocess.run(["/usr/sbin/sysctl", "-n", "kern.waketime"], capture_output=True, text=True)
    m = re.search(r"sec = (\d+)", r.stdout)
    return int(m.group(1)) if m else 0


def unit(name: str) -> str:
    """A systemd user unit of this HQ on Linux, e.g. unit("routine.timer") → hq-routine.timer. HQ_UNIT
    changes the prefix, so a second HQ on one server has its own units."""
    return f"{os.environ.get('HQ_UNIT') or 'hq'}-{name}"


def call_port() -> int:
    return int(os.environ.get("HQ_PORT") or 7860)


def status_port() -> int:
    return int(os.environ.get("HQ_STATUS_PORT") or 4748)


def shell() -> str:
    """The shell for HQ's own scripts (start.sh, phone.sh): zsh on a Mac as before, sh elsewhere."""
    return "/bin/zsh" if IS_MAC else "/bin/sh"


def start_script() -> str:
    """What starts the call line: app/start.sh on a Mac, app/start-linux.sh on Linux."""
    return os.path.join(HQ, "app", "start.sh" if IS_MAC else "start-linux.sh")


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
