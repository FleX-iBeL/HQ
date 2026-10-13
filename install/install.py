#!/usr/bin/env python3
"""HQ's installer (phase M, M4, 10 October 2026).

Two rounds, ticked off live on a checklist page:

  1. Setup: checks what's needed, makes the workspace from the template (only on a fresh install; an
     existing workspace is never touched), the Python environment, the voice, and every password and
     macOS permission once: the helper app's Documents access, Terminal windows, the watchdog, the
     lid-closed sleep switch. Those are the moments macOS or sudo asks; the user is told up front.
  2. Test (the installer's happy flow): the same things again, and nothing may ask any more. A check
     that would need a password or a click fails instead of waiting.

    python3 install/install.py              both rounds (asks Enter once, after the heads-up)
    python3 install/install.py --test-only  only the test round: read only, asks nothing
    python3 install/install.py --skip lidsleep,tailscale,flows   leave optional parts out
    python3 install/install.py --yes        no Enter after the heads-up (the user's Claude runs it)

The checklist: http://localhost:4749 while the installer runs, and afterwards on the status page at
http://localhost:4748/install (and on the phone's status address). Its data: scratch/install/checklist.json;
the whole run's output: scratch/install/install.log. Python's standard library only, so it runs on the
python3 macOS ships, before HQ's own Python environment exists.

On a Linux server (H56.5, 12 October 2026) the same two rounds run, with the Linux parts from H56.1 and
H56.2 instead of the Mac's: systemd user units instead of the helper app and the LaunchAgents
(routine/install-linux.sh), tmux instead of Terminal windows, faster-whisper instead of MLX, and no lid switch
or Mac app. Nothing is installed with sudo: what's missing is named, with the line to install it. Run it
there the same way, usually with --yes --no-page (there's no browser on a server; the checklist is still on the
status page, /install).

For the happy flows (flow 43), in a throwaway copy: HQ_INSTALL_FAKE=1 simulates every step that touches
the computer outside HQ (Homebrew, downloads, launchctl, sudo, Terminal, servers) and runs the rest for
real; HQ_INSTALL_FAIL=<step id> makes that step fail, to see the checklist stop there.
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime

HQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
WORKSPACE = os.environ.get("HQ_WORKSPACE") or os.path.join(HQ, "workspace")
TEMPLATE = os.path.join(HQ, "template")
OUT = os.path.join(HQ, "scratch", "install")
CHECKLIST = os.path.join(OUT, "checklist.json")
LOG = os.path.join(OUT, "install.log")
PAGE = os.path.join(HQ, "install", "checklist.html")
PAGE_PORT = int(os.environ.get("HQ_INSTALL_PORT", "4749"))
FAKE = os.environ.get("HQ_INSTALL_FAKE") == "1"
FORCE_FAIL = os.environ.get("HQ_INSTALL_FAIL", "")
IS_MAC = platform.system() == "Darwin"
sys.path.insert(0, os.path.join(HQ, "routine"))
try:
    import hqpaths  # H56.1: HQ's own memory and the units' names, the same as the routine works them out
    SUPPORT = hqpaths.SUPPORT
except Exception:
    hqpaths = None
    SUPPORT = os.path.expanduser("~/Library/Application Support/HQ")
HEARTBEAT = os.path.join(SUPPORT, "heartbeat")
HELPER_APP = os.path.expanduser("~/Applications/HQ Routine.app")
AGENTS = os.path.expanduser("~/Library/LaunchAgents")


def _label(path: str, pattern: str) -> str:
    """The LaunchAgent ids as the repo ships them (read from the files, so a rename follows by itself)."""
    try:
        return re.search(pattern, open(path).read()).group(1)
    except (OSError, AttributeError):
        return ""


# The helper's plist is app/<its label>.plist; the watchdog's label is in its install script.
_plists = [f for f in (os.listdir(os.path.join(HQ, "app")) if os.path.isdir(os.path.join(HQ, "app")) else [])
           if f.endswith(".plist")]
HELPER_AGENT = _plists[0][:-len(".plist")] if _plists else ""


def _own_part(name):
    """H59: the user's own version of a platform part in local/ (see routine/hqpaths.py), or None."""
    sys.path.insert(0, os.path.join(HQ, "routine"))
    try:
        import hqpaths
        return hqpaths.part_cmd(name)
    except Exception:
        return None

WATCHDOG_AGENT = _label(os.path.join(HQ, "routine", "install-watchdog.sh"), r"<key>Label</key><string>([^<]+)</string>")
# The HQ path the repo's helper files were written with (whatever home folder it was), replaced by
# this HQ's path when installing.
SHIPPED_HQ = re.compile(r'/Users/[^/"<\s]+(?:/[^/"<\s]+)*?/HQ(?=[/"<]|$)')
BREW_PATHS = (["/opt/homebrew/bin", "/usr/local/bin"] if IS_MAC
              else [os.path.expanduser("~/.local/bin"), os.path.expanduser("~/.npm-global/bin"), "/usr/local/bin"])
STATUS_PORT = int(os.environ.get("HQ_STATUS_PORT", "4748"))
CALL_PORT = int(os.environ.get("HQ_PORT", "7860"))
UNIT = os.environ.get("HQ_UNIT", "hq")
# H56.5: on Linux the call listens with faster-whisper; MLX and what only mlx-whisper needs are left out.
MAC_ONLY_PACKAGES = {"mlx", "mlx-metal", "mlx-whisper", "more-itertools", "networkx", "regex", "scipy",
                     "setuptools", "tiktoken", "torch"}
LISTEN_MODULE = "mlx_whisper" if IS_MAC else "faster_whisper"
# H56.5: the quick happy flows that hold on a Linux server today (the rest are written for the Mac and get their
# Linux side when HQ on a server is made the main one, H56.7).
LINUX_FLOWS = "8,15,16,20,23,26,34,41,42,44,45,51,54,56,60,61,63,65,66,67,70,71,72,73,79,84"
VOICE_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
VOICE_FILES = {"kokoro-v1.0.onnx": 300_000_000, "voices-v1.0.bin": 25_000_000}  # minimum sizes

HEADS_UP_LINUX = (
    "Heads-up before we start: on a server nothing is installed with sudo and nothing asks. What's missing is "
    "named with the line to install it. Claude Code must be signed in here once (run claude), and Claude must "
    "trust the workspace once (run claude in it and answer yes), since nobody answers that question for a job."
)

HEADS_UP = (
    "Heads-up before we start: the setup will ask for your password, and macOS will ask a few times "
    "whether something may have access (the Documents folder, Terminal, later the microphone). If you "
    "want those features, allow it. It's asked once; after that HQ runs by itself, and the second round "
    "checks that nothing asks any more."
)


class Fail(Exception):
    def __init__(self, why, fix=""):
        super().__init__(why)
        self.why, self.fix = why, fix


class Warn(Exception):
    """Done, but with something the user should know (an optional part left out, an existing workspace kept)."""


class Skip(Exception):
    pass


# ---------- the checklist ----------

class Checklist:
    def __init__(self, mode: str, steps: list):
        self.lock = threading.Lock()
        self.data = {
            "run": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mode": mode, "fake": FAKE, "hq": HQ, "workspace": WORKSPACE,
            "heads_up": HEADS_UP if IS_MAC else HEADS_UP_LINUX, "machine": f"{platform.system()} {platform.machine()}",
            "phase": "setup" if mode != "test" else "test", "result": "running", "finished": None,
            "steps": [{"id": s.id, "phase": s.phase, "title": s.title, "asks": s.asks, "optional": s.optional,
                       "state": "todo", "detail": "", "fix": "", "started": None, "ended": None} for s in steps],
        }
        self.save()

    def step(self, sid: str, phase: str) -> dict:
        return next(s for s in self.data["steps"] if s["id"] == sid and s["phase"] == phase)

    def set(self, sid: str, phase: str, **kw) -> None:
        with self.lock:
            self.step(sid, phase).update(kw)
            self.save()

    def finish(self, result: str) -> None:
        with self.lock:
            self.data["result"] = result
            self.data["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.save()

    def save(self) -> None:
        os.makedirs(OUT, exist_ok=True)
        tmp = CHECKLIST + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f, indent=1)
        os.replace(tmp, CHECKLIST)


def log(line: str) -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{datetime.now().strftime('%H:%M:%S')} {line}\n")


def say(line: str) -> None:
    print(line, flush=True)
    log(line)


def serve_page() -> http.server.ThreadingHTTPServer | None:
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?")[0]
            src, kind = {"/": (PAGE, "text/html; charset=utf-8"), "/install": (PAGE, "text/html; charset=utf-8"),
                         "/install.json": (CHECKLIST, "application/json; charset=utf-8")}.get(path, (None, None))
            if not src:
                self.send_response(404)
                self.end_headers()
                return
            try:
                body = open(src, "rb").read()
            except OSError:
                body = b"null"
            self.send_response(200)
            self.send_header("content-type", kind)
            self.send_header("cache-control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    try:
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", PAGE_PORT), H)
    except OSError:
        return None  # the port is taken (another installer run); the status page still shows it
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ---------- helpers ----------

def sh(cmd, timeout=600, env=None, cwd=None, check=True) -> subprocess.CompletedProcess:
    log("$ " + (cmd if isinstance(cmd, str) else " ".join(cmd)))
    full_env = dict(os.environ)
    full_env["PATH"] = ":".join(BREW_PATHS + [full_env.get("PATH", "/usr/bin:/bin")])
    if env:
        full_env.update(env)
    try:
        r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True,
                           timeout=timeout, env=full_env, cwd=cwd)
    except subprocess.TimeoutExpired:
        raise Fail(f"took longer than {timeout} seconds: {cmd if isinstance(cmd, str) else ' '.join(cmd)}",
                   "If macOS showed a question, answer it and run the installer again.")
    out = (r.stdout + r.stderr).strip()
    if out:
        log(out[-4000:])
    if check and r.returncode != 0:
        raise Fail(f"{cmd if isinstance(cmd, str) else ' '.join(cmd)} stopped with code {r.returncode}: "
                   + (out.splitlines()[-1] if out else "no output"))
    return r


def which(name: str) -> str | None:
    return shutil.which(name, path=":".join(BREW_PATHS + [os.environ.get("PATH", "")]))


def http_ok(url: str, timeout=5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def wait_for(cond, secs: float, every: float = 1.0) -> bool:
    end = time.time() + secs
    while time.time() < end:
        if cond():
            return True
        time.sleep(every)
    return cond()


def heartbeat_age() -> float | None:
    try:
        return time.time() - float(open(HEARTBEAT).read().strip())
    except Exception:
        return None


def agent_loaded(label: str) -> bool:
    return subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{label}"], capture_output=True).returncode == 0


def with_this_hq(text: str) -> str:
    return SHIPPED_HQ.sub(lambda m: HQ, text)


# ---------- the steps ----------

class Step:
    def __init__(self, id, title, phase, fn, asks=False, optional=False):
        self.id, self.title, self.phase, self.fn, self.asks, self.optional = id, title, phase, fn, asks, optional


class Installer:
    def __init__(self, args):
        self.args = args
        self.skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    # -- setup --

    def heads_up(self):
        say("\n" + (HEADS_UP if IS_MAC else HEADS_UP_LINUX) + "\n")
        say("The checklist, live: http://localhost:%d" % PAGE_PORT)
        if not self.args.yes and sys.stdin.isatty():
            input("Press Enter to start. ")
        return "told: password and Allow a few times, once" if IS_MAC else "told: nothing asks; what's missing is named"

    def mac(self):
        if platform.system() == "Linux":
            return self._linux()
        if platform.system() != "Darwin":
            raise Fail(f"this is {platform.system()}, not a Mac",
                       "HQ 0.1 is built for a Mac; on Windows, Claude builds the Mac-only parts (README, Mac-only parts).")
        if platform.machine() != "arm64":
            raise Fail(f"this Mac has an {platform.machine()} chip, not an Apple chip",
                       "Speech recognition runs on the Apple chip (MLX); see the README's Mac-only parts.")
        return f"macOS {platform.mac_ver()[0]}, Apple chip"

    def _linux(self):
        """H56.5: a Linux server with systemd (the units of H56.1 run as the user, with lingering)."""
        if not which("systemctl") or subprocess.run(["systemctl", "--user", "show-environment"],
                                                    capture_output=True).returncode != 0:
            raise Fail("this Linux has no systemd for the user (systemctl --user)",
                       "HQ on Linux runs its routine and watchdog as systemd user units; on another system, Claude "
                       "builds them in local/ (README, platform parts).")
        name = platform.system()
        try:
            name = dict(l.strip().split("=", 1) for l in open("/etc/os-release") if "=" in l).get("PRETTY_NAME", name).strip('"')
        except OSError:
            pass
        return f"{name}, {platform.machine()}, systemd"

    def tools(self):
        if FAKE:
            return "simulated (test)"
        if not IS_MAC:
            return self._tools_linux()
        have, missing = [], []
        for name in ["brew", "claude", "uv", "node", "git"]:
            (have if which(name) else missing).append(name)
        if "brew" in missing:
            raise Fail("Homebrew isn't installed", "Install it from https://brew.sh, then run the installer again.")
        brew_names = {"uv": "uv", "node": "node", "git": "git"}
        todo = [brew_names[m] for m in missing if m in brew_names]
        if not shutil.which("python3.12", path=":".join(BREW_PATHS)):
            todo.append("python@3.12")
        if todo:
            say("Installing with Homebrew: " + ", ".join(todo))
            sh(["brew", "install"] + todo, timeout=1800)
        if not which("claude"):
            raise Fail("Claude Code isn't installed",
                       "Install it (https://claude.com/claude-code), sign in with your Claude plan, then run the installer again.")
        node_v = sh(["node", "--version"]).stdout.strip()
        if int(node_v.lstrip("v").split(".")[0]) < 20:
            raise Fail(f"Node {node_v} is too old (20 or newer)", "brew upgrade node")
        return "Claude Code, Homebrew, Python 3.12, uv, Node %s, git" % node_v

    def _tools_linux(self):
        missing = [n for n in ["git", "node", "curl", "tmux"] if not which(n)]
        if missing:
            raise Fail("not installed: " + ", ".join(missing),
                       "sudo apt install " + " ".join("nodejs" if m == "node" else m for m in missing)
                       + " (node 20 or newer), then run the installer again.")
        if not which("uv"):
            raise Fail("uv isn't installed", "curl -LsSf https://astral.sh/uv/install.sh | sh, then run the installer again.")
        if not which("claude"):
            raise Fail("Claude Code isn't installed",
                       "npm install -g @anthropic-ai/claude-code (or https://claude.com/claude-code), sign in with your "
                       "Claude plan (run claude once), then run the installer again.")
        node_v = sh(["node", "--version"]).stdout.strip()
        if int(node_v.lstrip("v").split(".")[0]) < 20:
            raise Fail(f"Node {node_v} is too old (20 or newer)", "Install a newer Node (nodejs 20 or newer).")
        return f"Claude Code, git, Node {node_v}, uv, tmux, curl (Python 3.12 comes with uv)"

    def signed_in(self):
        if FAKE:
            return "simulated (test)"
        try:
            acct = json.load(open(os.path.expanduser("~/.claude.json"))).get("oauthAccount") or {}
        except Exception:
            acct = {}
        if not acct:
            raise Fail("Claude Code isn't signed in with a Claude plan",
                       "Run claude in Terminal and sign in with your Pro or Max plan, then run the installer again.")
        return "signed in with a Claude plan"

    def workspace(self):
        if os.path.lexists(WORKSPACE):
            # Never touched: not copied over, not changed, not even a git init.
            kind = "a link to " + os.path.realpath(WORKSPACE) if os.path.islink(WORKSPACE) else "a folder"
            raise Warn(f"kept your existing workspace ({kind}); nothing in it was changed")
        if not os.path.isdir(TEMPLATE):
            raise Fail("the template folder is missing from HQ", "Download HQ again (git pull or a fresh clone).")
        shutil.copytree(TEMPLATE, WORKSPACE, symlinks=True)
        r = subprocess.run(["git", "init", "-q"], cwd=WORKSPACE, capture_output=True, text=True)
        if r.returncode == 0:
            subprocess.run(["git", "add", "-A"], cwd=WORKSPACE, capture_output=True)
            subprocess.run(["git", "-c", "user.name=HQ", "-c", "user.email=hq@localhost", "commit", "-q", "-m",
                            "The workspace, from HQ's template"], cwd=WORKSPACE, capture_output=True)
        return "made from the template, as its own git repo" if r.returncode == 0 else "made from the template"

    def venv(self):
        if FAKE:
            return "simulated (test)"
        py = os.path.join(HQ, ".venv", "bin", "python")
        check = [py, "-c", f"import pipecat, {LISTEN_MODULE}, kokoro_onnx, claude_agent_sdk"]
        if os.path.exists(py) and subprocess.run(check, capture_output=True).returncode == 0:
            return "already there"
        say("Making the Python environment (a few minutes, about 1.6 GB)")
        sh(["uv", "venv", "--python", "3.12", ".venv"], cwd=HQ)
        sh(["uv", "pip", "install", "--python", py, "--only-binary", ":all:", "tokenizers", "faster-whisper==1.2.1"],
           cwd=HQ, timeout=1800)
        reqs = "app/requirements.txt"
        if not IS_MAC:  # H56.5: the same list without MLX and what only mlx-whisper needs
            reqs = os.path.join(OUT, "requirements-linux.txt")
            keep = [l for l in open(os.path.join(HQ, "app", "requirements.txt"))
                    if l.split("==")[0].strip().lower() not in MAC_ONLY_PACKAGES]
            open(reqs, "w").writelines(keep)
        sh(["uv", "pip", "install", "--python", py, "-r", reqs], cwd=HQ, timeout=1800)
        sh(check)
        return "made, and everything imports"

    def voice(self):
        if FAKE:
            return "simulated (test)"
        os.makedirs(os.path.join(HQ, "models"), exist_ok=True)
        got = []
        for name, least in VOICE_FILES.items():
            dest = os.path.join(HQ, "models", name)
            if os.path.exists(dest) and os.path.getsize(dest) >= least:
                continue
            say(f"Downloading {name}")
            sh(["curl", "-fL", "--retry", "3", "-o", dest + ".part", VOICE_BASE + name], timeout=1800)
            os.replace(dest + ".part", dest)
            got.append(name)
        return ("downloaded: " + ", ".join(got)) if got else "already there (all nine voices, Heart the default)"

    def helper(self):
        if "helper" in self.skip:
            raise Skip("left out (--skip helper): no routine, no start at login")
        if FAKE:
            return "simulated (test)"
        own = _own_part("start-at-login")
        if own:  # H59: the user's own start at login, in local/ (for example on Windows)
            sh(own)
            return "your own start at login (local/)"
        if not IS_MAC:  # H56.5: the units of H56.1; the routine, the call line and the watchdog start now
            before = os.path.getmtime(HEARTBEAT) if os.path.exists(HEARTBEAT) else 0
            sh(["/bin/sh", os.path.join(HQ, "routine", "install-linux.sh")], timeout=120)
            if not wait_for(lambda: os.path.exists(HEARTBEAT) and os.path.getmtime(HEARTBEAT) > before, 150, 2):
                raise Fail("the routine's timer is on but it didn't run within 2 minutes",
                           f"systemctl --user status {UNIT}-routine.service; log: scratch/routine/routine.log")
            return f"systemd user units ({UNIT}-routine every minute, {UNIT}-start at the start), lingering on"
        os.makedirs(os.path.join(HQ, "scratch", "routine"), exist_ok=True)
        # The helper and its LaunchAgent with this HQ's path.
        src = with_this_hq(open(os.path.join(HQ, "routine", "routine.applescript")).read())
        gen = os.path.join(OUT, "routine.applescript")
        open(gen, "w").write(src)
        sh(["/bin/zsh", os.path.join(HQ, "routine", "build-app.sh"), gen])
        plist = with_this_hq(open(os.path.join(HQ, "app", HELPER_AGENT + ".plist")).read())
        os.makedirs(AGENTS, exist_ok=True)
        dest = os.path.join(AGENTS, HELPER_AGENT + ".plist")
        # One start at login only: one installed under another id before (an older HQ) is taken out.
        suffix = "." + HELPER_AGENT.split(".")[-1] + ".plist"
        for old in os.listdir(AGENTS):
            # (Also the id from before H54, 11 October 2026: .jarvis-va.)
            if (old.endswith(suffix) or old.endswith(".jarvis-va.plist")) and old != HELPER_AGENT + ".plist":
                subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{old[:-len('.plist')]}"], capture_output=True)
                os.remove(os.path.join(AGENTS, old))
        open(dest, "w").write(plist)
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{HELPER_AGENT}"], capture_output=True)
        sh(["launchctl", "bootstrap", f"gui/{os.getuid()}", dest])
        before = os.path.getmtime(HEARTBEAT) if os.path.exists(HEARTBEAT) else 0
        sh(["/usr/bin/open", "-a", HELPER_APP])
        say("macOS asks whether HQ Routine may reach your files (Documents): click Allow. Waiting up to 3 minutes.")
        if not wait_for(lambda: os.path.exists(HEARTBEAT) and os.path.getmtime(HEARTBEAT) > before, 180, 2):
            raise Fail("the helper started but didn't run its routine within 3 minutes",
                       "Most likely the Documents question wasn't answered: System Settings → Privacy & Security → "
                       "Files and Folders → HQ Routine → Documents on. Log: scratch/routine/routine.log")
        return "built, starts at login, runs every minute (Documents allowed)"

    def terminal(self):
        if "helper" in self.skip:
            raise Skip("left out with the helper")
        return self._terminal_window(asking=True) if IS_MAC else self._tmux_window()

    def _tmux_window(self):
        """H56.5: on Linux jobs and the mail check run in a detached tmux session (H56.2) that ends by itself."""
        if FAKE:
            return "simulated (test)"
        if not which("tmux"):
            raise Fail("tmux isn't installed", "sudo apt install tmux, then run the installer again.")
        mark = os.path.join(OUT, "tmux-ok")
        if os.path.exists(mark):
            os.remove(mark)
        name = f"{UNIT}-install-check"
        sh(["tmux", "new-session", "-d", "-s", name, f"date > '{mark}'"])
        if not wait_for(lambda: os.path.exists(mark), 20, 0.5):
            raise Fail("a tmux session didn't run its script", "tmux new-session -d works for this user?")
        if not wait_for(lambda: subprocess.run(["tmux", "has-session", "-t", name], capture_output=True).returncode != 0, 20, 0.5):
            raise Fail("the tmux session ran but didn't end by itself", f"tmux kill-session -t {name}")
        return "a tmux session opened, ran, and ended by itself, nothing asked"

    def _terminal_window(self, asking: bool):
        """The way jobs and the mail check open and close their windows: open -g -a Terminal with a
        script that closes its own window. The first time, macOS may ask once."""
        if FAKE:
            return "simulated (test)"
        mark = os.path.join(OUT, "terminal-ok")
        closelog = os.path.join(OUT, "close.log")
        for f in (mark, closelog):
            if os.path.exists(f):
                os.remove(f)
        script = os.path.join(OUT, "terminal-check.command")
        close = os.path.join(HQ, "routine", "close-window.applescript")
        # The tty first (a background job has no tty), then the closer in its own session, as tick.py's
        # CLOSE_WINDOW does, so it never counts as a process in the window it closes.
        open(script, "w").write(
            "#!/bin/zsh\n"
            "T=$(tty)\n"
            f"date > '{mark}'\n"
            "/usr/bin/python3 -c 'import os,sys,subprocess; os.setsid(); r=subprocess.run([\"/usr/bin/osascript\"]+sys.argv[1:3], "
            "capture_output=True, text=True); open(sys.argv[3], \"a\").write((r.stdout+r.stderr).strip()+chr(10))' "
            f"'{close}' \"$T\" '{closelog}' </dev/null >/dev/null 2>&1 &!\n"
            "exit 0\n"
        )
        os.chmod(script, 0o755)
        sh(["/usr/bin/open", "-g", "-a", "Terminal", script])
        if asking:
            say("If macOS asks whether Terminal may control Terminal or open the window: click OK. Waiting up to 2 minutes.")
        if not wait_for(lambda: os.path.exists(mark), 120 if asking else 20, 1):
            raise Fail("a Terminal window didn't run its script" + ("" if asking else " without asking"),
                       "System Settings → Privacy & Security → Automation: allow Terminal; then run the installer again.")
        closed = lambda: os.path.exists(closelog) and " closed " in open(closelog).read() and "gave up" not in open(closelog).read()
        if not wait_for(closed, 120 if asking else 30, 1):
            said = open(closelog).read().strip() if os.path.exists(closelog) else "nothing yet"
            raise Fail("the window ran but didn't close itself" + ("" if asking else " without asking") + f" ({said})",
                       "System Settings → Privacy & Security → Automation → Terminal may control Terminal; then run the installer again.")
        return "a window opened, ran, and closed itself" + ("" if asking else ", nothing asked")

    def watchdog(self):
        if "helper" in self.skip:
            raise Skip("left out with the helper")
        if FAKE:
            return "simulated (test)"
        own = _own_part("install-watchdog")
        if own:  # H59: the user's own watchdog, in local/
            sh(own)
            return "your own watchdog (local/)"
        if not IS_MAC:  # H56.5: put in with the routine by install-linux.sh
            return self._linux_timer("watchdog", "every 5 minutes, and a minute after the start")
        sh(["/bin/zsh", os.path.join(HQ, "routine", "install-watchdog.sh")])
        if not agent_loaded(WATCHDOG_AGENT):
            raise Fail("the watchdog didn't load", "Log: ~/Library/Application Support/HQ/watchdog.out")
        return "every 5 minutes and at login"

    def _linux_timer(self, what, says):
        timer = f"{UNIT}-{what}.timer"
        if subprocess.run(["systemctl", "--user", "is-active", "--quiet", timer]).returncode != 0:
            raise Fail(f"{timer} isn't running", f"sh routine/install-linux.sh; then systemctl --user status {timer}")
        return f"{timer}: {says}"

    def desktop(self):
        if not IS_MAC:
            raise Skip("the Mac app: not on Linux (the status page and calls work in the browser)")
        if "desktop" in self.skip:
            raise Skip("left out (--skip desktop): the status page and calls still work in the browser")
        if FAKE:
            return "simulated (test)"
        if not which("swiftc"):
            raise Fail("swiftc isn't there (the Command Line Tools)", "xcode-select --install, then run the installer again.")
        sh(["/bin/zsh", os.path.join(HQ, "desktop", "build.sh"), "--install"], timeout=600)
        return "~/Applications/HQ.app (macOS asks Documents access and the microphone once, the first time)"

    def t_desktop(self):
        if not IS_MAC:
            raise Skip("not on Linux")
        if "desktop" in self.skip:
            raise Skip("left out")
        if FAKE:
            return "simulated (test)"
        app = os.path.expanduser("~/Applications/HQ.app/Contents/MacOS/HQ")
        if not os.path.exists(app) or sh([app, "--check"], check=False).returncode != 0:
            raise Fail("HQ.app isn't there or doesn't find its files", "desktop/build.sh --install")
        return "finds its files"

    def lidsleep(self):
        if not IS_MAC:
            raise Skip("a laptop part: not on a server")
        if "lidsleep" in self.skip:
            raise Skip("left out (--skip lidsleep): a call can't flip the lid-closed sleep")
        if FAKE:
            return "simulated (test)"
        if self._lidsleep_allowed():
            return "already allowed"
        if not sys.stdin.isatty():
            raise Fail("needs your password, typed by you in Terminal",
                       f'Run once in Terminal: sudo sh "{HQ}/routine/install-lidsleep.sh"  (or leave it out: --skip lidsleep)')
        say("Lid closed, keep working: type your Mac password below (nothing shows while you type).")
        r = subprocess.run(["sudo", "sh", os.path.join(HQ, "routine", "install-lidsleep.sh")])
        if r.returncode != 0 or not self._lidsleep_allowed():
            raise Fail("the lid-closed sleep switch wasn't allowed",
                       f'Run once in Terminal: sudo sh "{HQ}/routine/install-lidsleep.sh"')
        return "allowed: a call can switch it on and off"

    def _lidsleep_allowed(self) -> bool:
        return subprocess.run(["sudo", "-n", "-l", "/usr/bin/pmset", "-a", "disablesleep", "0"],
                              capture_output=True).returncode == 0

    def status_page(self):
        if FAKE:
            return "simulated (test)"
        if not http_ok(f"http://127.0.0.1:{STATUS_PORT}/"):
            subprocess.Popen([which("node") or "node", os.path.join(HQ, "status", "server.mjs"), "--quiet"],
                             cwd=HQ, stdout=open(os.path.join(OUT, "status-server.log"), "a"),
                             stderr=subprocess.STDOUT, start_new_session=True)
        if not wait_for(lambda: http_ok(f"http://127.0.0.1:{STATUS_PORT}/"), 15):
            raise Fail(f"the status page didn't answer on port {STATUS_PORT}", "Log: scratch/install/status-server.log")
        return f"http://localhost:{STATUS_PORT} (this checklist too: /install)"

    def call_line(self):
        if FAKE:
            return "simulated (test)"
        if not http_ok(f"http://127.0.0.1:{CALL_PORT}/"):
            env = {} if (which("tailscale") and "tailscale" not in self.skip) else {"HQ_NO_PHONE": "1"}
            start = ["/bin/zsh", os.path.join(HQ, "app", "start.sh")] if IS_MAC else \
                    ["/bin/bash", os.path.join(HQ, "app", "start-linux.sh")]
            sh(start, env=env, timeout=120)
        if not wait_for(lambda: http_ok(f"http://127.0.0.1:{CALL_PORT}/"), 120, 2):
            raise Fail(f"the call line didn't answer on port {CALL_PORT}", "Log: scratch/server.log")
        if not IS_MAC:
            return (f"http://127.0.0.1:{CALL_PORT}, on the phone through Tailscale on port 8443 "
                    "(the browser asks for the microphone on the first call: Allow)")
        return f"http://127.0.0.1:{CALL_PORT} (the browser asks for the microphone on the first call: Allow)"

    def tailscale(self):
        if "tailscale" in self.skip:
            raise Skip("left out (--skip tailscale): calls from this computer only")
        if FAKE:
            return "simulated (test)"
        ts = which("tailscale") or ("/usr/bin/tailscale" if os.path.exists("/usr/bin/tailscale") else None) or ("/Applications/Tailscale.app/Contents/MacOS/Tailscale"
                                    if os.path.exists("/Applications/Tailscale.app") else None)
        if not ts:
            raise Warn("not installed: calls from this computer only (optional; "
                       + ("brew install --cask tailscale)" if IS_MAC else "https://tailscale.com/download/linux)"))
        r = subprocess.run([ts, "status"], capture_output=True, text=True)
        if r.returncode != 0:
            raise Warn("installed but not signed in: open Tailscale and sign in, on the phone too (optional)")
        return "on: the phone can call"

    def trust(self):
        """H56.5: on a server a job's chat opens in the workspace, and Claude Code asks once whether to trust it;
        nobody answers there (H56.2). The same check as the routine's."""
        if IS_MAC:
            raise Skip("on a Mac Claude asks you the first time a job opens")
        if FAKE:
            return "simulated (test)"
        try:
            projects = json.load(open(os.path.expanduser("~/.claude.json"))).get("projects") or {}
        except (OSError, ValueError):
            projects = {}
        p = os.path.realpath(WORKSPACE)
        while True:
            if (projects.get(p) or {}).get("hasTrustDialogAccepted"):
                return "Claude trusts the workspace: jobs can start here"
            up = os.path.dirname(p)
            if up == p:
                break
            p = up
        raise Warn(f"Claude doesn't trust the workspace yet, so jobs wait: run claude once in {os.path.realpath(WORKSPACE)}, "
                   "answer yes, then /exit")

    def connectors(self):
        raise Warn("for you and your Claude: connect Gmail and Google Calendar in claude.ai → Settings → "
                   "Connectors (the installer can't check this without using your plan)")

    # -- test: the installer's happy flow; nothing may ask --

    def t_workspace(self):
        if not os.path.isdir(os.path.realpath(WORKSPACE)):
            raise Fail("there's no workspace", "Run the installer without --test-only.")
        need = ["CLAUDE.md", os.path.join("HQ", "roadmap.md")]
        missing = [n for n in need if not os.path.exists(os.path.join(WORKSPACE, n))]
        if missing:
            raise Fail("the workspace misses " + ", ".join(missing), "Compare it with HQ's template folder.")
        return "there, with its roadmap"

    def t_venv(self):
        if FAKE:
            return "simulated (test)"
        py = os.path.join(HQ, ".venv", "bin", "python")
        if not os.path.exists(py):
            raise Fail("no Python environment", "Run the installer without --test-only.")
        sh([py, "-c", f"import pipecat, {LISTEN_MODULE}, kokoro_onnx, claude_agent_sdk"], timeout=120)
        return "everything imports"

    def t_voice(self):
        if FAKE:
            return "simulated (test)"
        bad = [n for n, least in VOICE_FILES.items()
               if not (os.path.exists(os.path.join(HQ, "models", n)) and os.path.getsize(os.path.join(HQ, "models", n)) >= least)]
        if bad:
            raise Fail("missing or incomplete: " + ", ".join(bad), "Run the installer without --test-only.")
        return "both files there"

    def t_helper(self):
        if "helper" in self.skip:
            raise Skip("left out")
        if FAKE:
            return "simulated (test)"
        if not IS_MAC:
            self._linux_timer("routine", "on")
        elif not agent_loaded(HELPER_AGENT):
            raise Fail("the start at login isn't loaded", "Run the installer without --test-only.")
        if not wait_for(lambda: (heartbeat_age() or 999) < 150, 130, 5):
            raise Fail("the helper hasn't run its routine in the last few minutes",
                       "Privacy & Security → Files and Folders → HQ Routine → Documents on; log: scratch/routine/routine.log")
        return ("loaded at login" if IS_MAC else f"{UNIT}-routine.timer on") + \
            ", ran its routine %d seconds ago" % (heartbeat_age() or 0)

    def t_terminal(self):
        if "helper" in self.skip:
            raise Skip("left out")
        return self._terminal_window(asking=False) if IS_MAC else self._tmux_window()

    def t_watchdog(self):
        if "helper" in self.skip:
            raise Skip("left out")
        if FAKE:
            return "simulated (test)"
        if not IS_MAC:
            return self._linux_timer("watchdog", "on")
        if not agent_loaded(WATCHDOG_AGENT):
            raise Fail("the watchdog isn't loaded", "Run the installer without --test-only.")
        return "loaded"

    def t_lidsleep(self):
        if not IS_MAC:
            raise Skip("not on a server")
        if "lidsleep" in self.skip:
            raise Skip("left out")
        if FAKE:
            return "simulated (test)"
        if not self._lidsleep_allowed():
            raise Fail("switching the lid-closed sleep would ask for the password",
                       f'Run once in Terminal: sudo sh "{HQ}/routine/install-lidsleep.sh"')
        r = subprocess.run(["/usr/bin/python3", os.path.join(HQ, "routine", "lidsleep.py")], capture_output=True, text=True)
        return "allowed without a password" + (f"; now: {r.stdout.strip().splitlines()[-1]}" if r.stdout.strip() else "")

    def t_status(self):
        if FAKE:
            return "simulated (test)"
        if not http_ok(f"http://127.0.0.1:{STATUS_PORT}/roadmap.md"):
            raise Fail("the status page doesn't answer", "node status/server.mjs; log: scratch/install/status-server.log")
        return "answers, and reads the roadmap"

    def t_call(self):
        if FAKE:
            return "simulated (test)"
        if not http_ok(f"http://127.0.0.1:{CALL_PORT}/"):
            raise Fail("the call line doesn't answer", ("app/start.sh" if IS_MAC else "app/start-linux.sh")
                       + "; log: scratch/server.log")
        return f"answers on {CALL_PORT}"

    def t_flows(self):
        if "flows" in self.skip:
            raise Skip("left out (--skip flows)")
        if FAKE:
            return "simulated (test)"
        py = os.path.join(HQ, ".venv", "bin", "python")
        r = sh([py, os.path.join(HQ, "app", "happy_flows.py"), "--quick"] + ([] if IS_MAC else ["--only", LINUX_FLOWS]),
               cwd=HQ, timeout=900, check=False)
        last = [l for l in (r.stdout + r.stderr).splitlines() if " passed " in l]
        if r.returncode != 0:
            failed = [l.strip() for l in r.stdout.splitlines() if "FAILED" in l][:3]
            raise Fail("happy flows: " + (last[-1] if last else "failed") + (" · " + " · ".join(failed) if failed else ""),
                       "Each failed flow says why; the whole output is in scratch/install/install.log.")
        return ("quick happy flows: " if IS_MAC else "the happy flows that hold on Linux: ") + \
            (last[-1].split(" · ")[0] if last else "pass")

    def steps(self) -> list:
        S = Step
        setup = [
            S("heads_up", "Heads-up: your password and Allow, a few times", "setup", self.heads_up),
            S("mac", "A Mac with an Apple chip" if IS_MAC else "A Linux server with systemd", "setup", self.mac),
            S("tools", "Claude Code, Homebrew, Python 3.12, uv, Node, git" if IS_MAC
              else "Claude Code, git, Node, uv, tmux, curl", "setup", self.tools),
            S("signed_in", "Claude Code signed in with a Claude plan", "setup", self.signed_in),
            S("workspace", "Your workspace (from the template; an existing one is never touched)", "setup", self.workspace),
            S("venv", "The call line's Python environment", "setup", self.venv),
            S("voice", "The voice (Kokoro, Heart the default)", "setup", self.voice),
            S("helper", "The helper app: the routine and the start at login" if IS_MAC
              else "The routine and the start at boot: systemd user units", "setup", self.helper, asks=IS_MAC),
            S("terminal", "Terminal windows for jobs and the mail check" if IS_MAC
              else "tmux sessions for jobs and the mail check", "setup", self.terminal, asks=IS_MAC),
            S("watchdog", "The watchdog", "setup", self.watchdog),
            S("lidsleep", "Lid closed, keep working (optional)", "setup", self.lidsleep, asks=True, optional=True),
            S("status_page", "The status page", "setup", self.status_page),
            S("call_line", "The call line", "setup", self.call_line),
            S("desktop", "The Mac app: status, calling and the watchdog dog in one (optional)", "setup", self.desktop, optional=True),
            S("tailscale", "Calling from the phone: Tailscale (optional)", "setup", self.tailscale, optional=True),
            S("connectors", "Mail and calendar: the Gmail and Google Calendar connectors", "setup", self.connectors),
        ]
        if not IS_MAC:  # on a Mac Claude asks the person the first time a job opens
            setup.insert(-1, S("trust", "Claude trusts the workspace, so jobs can start", "setup", self.trust))
        test = [
            S("workspace", "The workspace is there", "test", self.t_workspace),
            S("venv", "The Python environment imports", "test", self.t_venv),
            S("voice", "The voice files", "test", self.t_voice),
            S("helper", "The helper runs every minute, nothing asks", "test", self.t_helper),
            S("terminal", "A Terminal window opens and closes, nothing asks" if IS_MAC
              else "A tmux session opens and ends, nothing asks", "test", self.t_terminal),
            S("watchdog", "The watchdog is loaded", "test", self.t_watchdog),
            S("lidsleep", "The lid switch works without a password", "test", self.t_lidsleep, optional=True),
            S("status_page", "The status page answers", "test", self.t_status),
            S("call_line", "The call line answers", "test", self.t_call),
            S("desktop", "The Mac app finds its files", "test", self.t_desktop, optional=True),
            S("flows", "The quick happy flows pass", "test", self.t_flows),
        ]
        return test if self.args.test_only else setup + test


def run(args) -> bool:
    inst = Installer(args)
    steps = inst.steps()
    os.makedirs(OUT, exist_ok=True)
    open(LOG, "w").write(f"HQ installer · {datetime.now():%Y-%m-%d %H:%M:%S} · {'test only' if args.test_only else 'setup and test'}"
                         + (" · simulated" if FAKE else "") + f"\nHQ: {HQ}\nworkspace: {WORKSPACE}\n")
    cl = Checklist("test" if args.test_only else "full", steps)
    srv = None if args.no_page else serve_page()
    if srv and not args.no_browser and not FAKE and IS_MAC:
        subprocess.run(["/usr/bin/open", f"http://localhost:{PAGE_PORT}"], capture_output=True)
    failed = None
    for s in steps:
        if failed:
            cl.set(s.id, s.phase, state="not run", detail=f"not run: {failed} failed first")
            continue
        if s.phase == "test" and cl.data["phase"] != "test":
            cl.data["phase"] = "test"
            say("\nSecond round: the test. Nothing may ask any more.")
        cl.set(s.id, s.phase, state="running", started=datetime.now().strftime("%H:%M:%S"))
        say(f"[ ] {s.title} …")
        try:
            if FORCE_FAIL and FORCE_FAIL in (s.id, f"{s.phase}:{s.id}"):
                raise Fail(f"made to fail for the test (HQ_INSTALL_FAIL={FORCE_FAIL})", "Nothing to fix: this was a test.")
            detail, state, fix = s.fn(), "ok", ""
        except Warn as w:
            detail, state, fix = str(w), "warn", ""
        except Skip as k:
            detail, state, fix = str(k), "skipped", ""
        except Fail as f:
            detail, state, fix = f.why, "fail", f.fix
        except Exception as e:  # a crash is a failed step, with what it said
            detail, state, fix = f"{type(e).__name__}: {e}", "fail", "The whole output is in scratch/install/install.log."
        if state == "fail" and s.optional:  # an optional part that didn't work doesn't stop the rest
            state, detail = "warn", f"not set up: {detail}"
        cl.set(s.id, s.phase, state=state, detail=detail or "", fix=fix, ended=datetime.now().strftime("%H:%M:%S"))
        mark = {"ok": "[✓]", "warn": "[!]", "skipped": "[-]", "fail": "[✗]"}[state]
        say(f"{mark} {s.title}: {detail}" + (f"\n    To fix: {fix}" if fix else ""))
        if state == "fail":
            failed = f"{s.phase}: {s.title}"
    cl.finish("failed" if failed else "passed")
    say("\n" + (f"Stopped at: {failed}. The checklist shows why and what to do." if failed
                else "All done: set up, and the test passed without asking for anything."))
    if srv and not args.no_wait and sys.stdin.isatty():
        try:
            input(f"The checklist stays on http://localhost:{PAGE_PORT} until you press Enter "
                  "(and afterwards on the status page, /install). ")
        except EOFError:
            pass
    if srv:
        srv.shutdown()
    return not failed


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="HQ's installer: setup, then a test round that asks nothing (M4)")
    p.add_argument("--test-only", action="store_true", help="only the test round: read only, asks nothing")
    p.add_argument("--skip", default="", help="comma-separated: helper, lidsleep, tailscale, flows")
    p.add_argument("--yes", action="store_true", help="no Enter after the heads-up")
    p.add_argument("--no-page", action="store_true", help="don't serve the checklist page on 4749")
    p.add_argument("--no-browser", action="store_true", help="don't open the checklist in the browser")
    p.add_argument("--no-wait", action="store_true", help="don't keep the page up at the end")
    sys.exit(0 if run(p.parse_args()) else 1)
