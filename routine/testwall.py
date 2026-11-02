#!/usr/bin/env python3
"""F111 (2 November 2026): the wall between a test run and what's real.

The checklist re-run of that night found full runs reaching real things: a made-up crash in the real incident log that Donna
texted him about at 03:22, test lines in the real trail and the real proofs, a test bug posted to the real maker from a
connected HQ, a real mail check with his Gmail read tools inside the quick set. 'All green' is what he relies on instead of
testing himself, and a test that texts him at night breaks that. So a run can't reach what's real, whoever starts it: by
hand, the routine, a proof, a friend's HQ.

How. app/happy_flows.py starts here, and this runs the flows from a copy:

  * Before the first flow the real records (REAL_RECORDS, the one list) are hashed into a file outside the throwaway folder.
  * The run gets a new empty throwaway folder, scratch/test-wall-<pid>, and a copy of HQ in it: the code, its .git, .status
    and the workspace, so every path HQ works out by itself is inside. HQ's memory, tmux, temporary files and Syncthing's
    place go there too. What ties HQ to the outside isn't copied (NOT_COPIED) and the copy's workspace has a git of its own
    with no remote, so a test has no phone to push to, no maker to post to, no remote to push to.
  * `claude` is a stand-in first on the path, and in every setting that names it. A flow marked as using Claude goes through
    it to the real one; any other flow is stopped there, and every call is a line, so the run prints true counts.
  * Every Python a test starts carries a hook that refuses a write to a real record and notes it (the run goes red).
  * After the last flow the records are compared byte for byte. What differs turns the run red and is named. A path missing
    at both ends counts as the same.
  * The throwaway folder goes at the end. One left by a run that died is removed first (a run still alive keeps its own). A run
    that died used nothing real, so nothing needs restoring: the next run compares against the stored hashes, and a real change
    is told apart by its time: after the dead run's last sign of life plus a flow's limit it was his own work, not the run.

What a live HQ writes meanwhile. The routine writes the sprint file and the incident log about every minute, a job its row, his
own chat his to-do list; no time can tell those from a test while both go on. So: a change while this HQ's routine is ticking is
named and doesn't turn the run red; there the refused writes are what's exact, for every Python a test starts. On an HQ with no
routine running, every change is red.

    python3 routine/testwall.py records    what counts as real here, and whether it's there

Standard library only. A test of this very wall: flows 300 and 301 (HQ_REAL_HQ, the real HQ a copy of a copy answers for).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402

# What counts as real, the one list: (what it's called, in HQ's own folder or in the workspace, where). A folder counts as every file in it.
REAL_RECORDS = (
    ("the incident log", "hq", ".status/incidents.json"),
    ("the trail", "ws", "HQ/trail.jsonl"),
    ("the proofs", "hq", ".status/proofs"),
    ("the mistake ledger", "ws", "HQ/mistakes.jsonl"),
    ("the agents' ledgers", "ws", "HQ/ledger"),
    ("the planning", "ws", "HQ/roadmap.md"),
    ("the sprint file", "ws", "HQ/sprint.json"),
    ("the to-do list", "ws", "challenges.md"),
    ("the text thread", "ws", "HQ/direct-line/thread.jsonl"),
    ("the coaching thread", "ws", "HQ/coaching-line/thread.jsonl"),
    ("the team thread", "ws", "HQ/team-line/thread.jsonl"),
)
# What ties an HQ to the outside: the phones, a maker, the mailbox of a maker. Never in a copy.
NOT_COPIED = ("HQ/direct-line/subscriptions.json", "HQ/feedback-maker.json", "HQ/feedback-box.json", "HQ/feedback-keys.json")
HQ_LEFT_OUT = {"workspace", "scratch", ".status", ".venv", "models", "HQ", ".git", "__pycache__"}
BIG = 50 * 1024 * 1024  # a folder of the workspace bigger than this stays out of the copy (course videos): no flow reads them [Claude's choice]
LIVE_FILE = ".status/routines.json"  # the routine's own minute: its time says whether this HQ was running
LIVE_WITHIN = 90
DIED_MARGIN = 420  # past a dead run's last sign of life: a flow's limit and a little
PREFIX = "test-wall-"
STATE = "test-wall.json"


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def real_places(real_hq: str, real_ws: str) -> list[tuple[str, str, str]]:
    """(what it's called, its name for the run's lines, the real path)."""
    return [(name, rel, os.path.join(real_hq if where == "hq" else real_ws, rel)) for name, where, rel in REAL_RECORDS]


def _files(places) -> list[tuple[str, str, str]]:
    """Every real file: (what it's called, its short name, its path)."""
    out = []
    for name, rel, p in places:
        if os.path.isdir(p):
            for d, _, fs in os.walk(p):
                out += [(name, os.path.relpath(os.path.join(d, f), os.path.dirname(os.path.dirname(p))), os.path.join(d, f)) for f in sorted(fs)]
        elif os.path.exists(p):
            out.append((name, rel, p))
    return out


def snapshot(places) -> dict:
    """The records as they are: {short name: {name, path, sha, mtime}}; a path that isn't there isn't in it."""
    snap = {}
    for name, rel, p in _files(places):
        try:
            snap[rel] = {"name": name, "path": p, "mtime": os.path.getmtime(p), "sha": _sha(p)}
        except OSError:
            pass
    return snap


def stamps(places) -> dict:
    """A quick look, after every flow: {path: (mtime in ns, size)}."""
    out = {}
    for _, _, p in _files(places):
        try:
            s = os.stat(p)
            out[p] = (s.st_mtime_ns, s.st_size)
        except OSError:
            pass
    return out


def differs(a: dict, b: dict) -> list[str]:
    return sorted(k for k in set(a) | set(b) if (a.get(k) or {}).get("sha") != (b.get(k) or {}).get("sha"))


def alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except PermissionError:
        return True
    except (OSError, ValueError, OverflowError):
        return False


def inside(root) -> bool:
    """Is this run the one inside the wall?"""
    w = os.environ.get("HQ_WALL")
    return bool(w) and str(os.getppid()) == os.environ.get("HQ_WALL_OUTER") and os.path.realpath(str(root)) == os.path.realpath(os.path.join(w, "hq"))


def _refused(wall: str) -> list[dict]:
    try:
        return [json.loads(l) for l in open(os.path.join(wall, "refused.jsonl"), encoding="utf8") if l.strip()]
    except (OSError, ValueError):
        return []


def _live_since(real_hq: str, since: float) -> bool:
    """Was this HQ's routine ticking from `since` on?"""
    try:
        return os.path.getmtime(os.path.join(real_hq, LIVE_FILE)) >= since - LIVE_WITHIN
    except OSError:
        return False


def _load(path: str) -> dict | None:
    try:
        return json.load(open(path, encoding="utf8"))
    except (OSError, ValueError):
        return None


def _save(path: str, state: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, path)


def clear_leftovers(scratch: str) -> list[dict]:
    """What runs that died left: their folders go (a run still alive keeps its own); what they tried on real records stays said."""
    tried = []
    try:
        names = os.listdir(scratch)
    except OSError:
        return tried
    for nm in names:
        m = re.fullmatch(PREFIX + r"(\d+)", nm)
        if m and not alive(m.group(1)):
            tried += _refused(os.path.join(scratch, nm))
            stop_tmux(os.path.join(scratch, nm))
            shutil.rmtree(os.path.join(scratch, nm), ignore_errors=True)
    return tried


def died(prior: dict, real_hq: str, now: dict, places) -> tuple[list[str], list[str]]:
    """The last run never finished: what differs from its stored hashes. Back to (red lines, notes)."""
    reds, notes = [], []
    base = prior.get("hashes") or {}
    until = float(prior.get("alive") or prior.get("start") or 0) + DIED_MARGIN
    live = _live_since(real_hq, float(prior.get("start") or 0))
    for k in differs(base, now):
        rec = now.get(k) or base.get(k) or {}
        name = rec.get("name") or k
        if k in now and now[k]["mtime"] > until:
            notes.append(f"{name} ({k}) changed after the run before this one stopped: his own work, not the run")
        elif live:
            notes.append(f"{name} ({k}) changed around the run that died, while this HQ's routine ran: told apart as its own")
        else:
            reds.append(f"the run that died changed a real record: {name} ({k})")
    return reds, notes


# -- the copy ------------------------------------------------------------------------------

def _big(path: str) -> bool:
    total = 0
    for d, _, fs in os.walk(path):
        for f in fs:
            try:
                total += os.lstat(os.path.join(d, f)).st_size
            except OSError:
                pass
        if total > BIG:
            return True
    return False


def _tree(src: str, dest: str, ignore=None) -> None:
    """A copy; a file that goes while it's copied (a live HQ writes on) doesn't stop it."""
    try:
        shutil.copytree(src, dest, symlinks=True, ignore=ignore, ignore_dangling_symlinks=True)
    except shutil.Error:
        pass


def _git(*a, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)


def copy_hq(root: str, real_hq: str, real_ws: str, dest: str) -> None:
    """HQ, its .git, .status and the workspace, with nothing that reaches the outside."""
    os.makedirs(dest)
    junk = shutil.ignore_patterns("__pycache__")
    for nm in os.listdir(root):
        src = os.path.join(root, nm)
        if nm in HQ_LEFT_OUT:
            continue
        if os.path.isdir(src) and not os.path.islink(src):
            _tree(src, os.path.join(dest, nm), junk)
        else:
            shutil.copy2(src, os.path.join(dest, nm), follow_symlinks=False)
    for nm in (".venv", "models"):
        if os.path.lexists(os.path.join(root, nm)):
            os.symlink(os.path.realpath(os.path.join(root, nm)), os.path.join(dest, nm))
    os.symlink(".", os.path.join(dest, "HQ"))  # the workspace's ../HQ paths
    _copy_git(root, dest)
    os.makedirs(os.path.join(dest, "scratch"))
    if os.path.isdir(os.path.join(real_hq, ".status")):
        _tree(os.path.join(real_hq, ".status"), os.path.join(dest, ".status"))
    _copy_workspace(real_ws, os.path.join(dest, "workspace"))


def _copy_git(root: str, dest: str) -> None:
    common = _git("rev-parse", "--git-common-dir", cwd=root).stdout.strip()
    head = _git("rev-parse", "HEAD", cwd=root).stdout.strip()
    common = os.path.join(root, common) if common else ""
    if not head or not os.path.isdir(common):
        return
    _tree(common, os.path.join(dest, ".git"), shutil.ignore_patterns("worktrees"))
    if os.path.isfile(os.path.join(root, ".git")):  # a proof's worktree: this copy stands on that worktree's commit
        with open(os.path.join(dest, ".git", "HEAD"), "w") as f:
            f.write(head + "\n")
        _git("reset", "-q", cwd=dest)
    _git("config", "remote.origin.pushurl", "/nonexistent/test-wall", cwd=dest)  # nothing a test does goes up


def _copy_workspace(real_ws: str, dest: str) -> None:
    os.makedirs(dest)
    try:
        names = os.listdir(real_ws)
    except OSError:
        names = []
    for nm in names:
        src = os.path.join(real_ws, nm)
        if nm in (".git", ".stfolder"):
            continue
        if os.path.isdir(src) and not os.path.islink(src):
            if not _big(src):
                _tree(src, os.path.join(dest, nm))
        elif not os.path.islink(src):
            shutil.copy2(src, os.path.join(dest, nm))
    for rel in NOT_COPIED:
        try:
            os.remove(os.path.join(dest, rel))
        except OSError:
            pass
    me = ("-c", "user.name=test", "-c", "user.email=t@example.invalid")
    _git("init", "-q", cwd=dest)
    _git("add", "-A", cwd=dest)
    _git(*me, "commit", "-q", "--allow-empty", "-m", "The workspace of a test run", cwd=dest)


# -- the wall's own parts ------------------------------------------------------------------

STANDIN = r'''#!/bin/sh
# F111: the model for a test run. A flow marked as using Claude goes on to the real one; any other flow stops here. Each call is a line.
w="@WALL@"
flow=$(cat "$w/flow" 2>/dev/null)
how=$(cat "$w/flow-model" 2>/dev/null)
case "$1" in --version|-v) ;; *) printf '%s\t%s\t%s\n' "${how:-stopped}" "$flow" "$(printf '%s ' "$1" "$2" "$3" | tr '\t\n' '  ' | cut -c1-120)" >> "$w/model-calls.log";; esac
if [ "$how" = real ] && [ -x "@REAL@" ]; then
  [ "$CLAUDE_CONFIG_DIR" = "$w/claude-config" ] && unset CLAUDE_CONFIG_DIR
  exec "@REAL@" "$@"
fi
case "$1" in --version|-v) echo "2.0.0 (the test wall's stand-in)"; exit 0;; esac
echo "The test wall's stand-in: no real model in a flow that isn't marked as using Claude." >&2
exit 1
'''

SITECUSTOMIZE = r'''# F111: every Python a test starts. A write to a real record is refused and noted, and the run goes red.
import os, sys


def _wall():
    import json
    wall = os.environ.get("HQ_WALL")
    try:
        paths = json.load(open(os.path.join(wall, "real.json"), encoding="utf8"))["paths"]
    except Exception:
        return
    writing = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND

    def real(p):
        try:
            p = os.path.realpath(os.fsdecode(p))
        except (TypeError, ValueError):
            return None
        return p if any(p == r or p.startswith(r + os.sep) for r in paths) else None

    def stop(p, what):
        try:
            flow = open(os.path.join(wall, "flow"), encoding="utf8").read().strip()
        except OSError:
            flow = ""
        with open(os.path.join(wall, "refused.jsonl"), "a", encoding="utf8") as f:
            f.write(json.dumps({"path": p, "what": what, "flow": flow}) + "\n")
        raise PermissionError(13, "the test wall: a test run may not write a real record", p)

    def hook(event, args):
        if event == "open":
            p, mode, flags = args
            if isinstance(p, int) or p is None:
                return
            if isinstance(mode, str):
                write = bool(set(mode) & set("wax+"))
            else:
                write = isinstance(flags, int) and bool(flags & writing)
            hit = real(p) if write else None
            if hit:
                stop(hit, "open")
        elif event == "os.rename":
            for p in args[:2]:
                hit = real(p) if not isinstance(p, int) else None
                if hit:
                    stop(hit, "rename")
        elif event in ("os.remove", "os.truncate", "os.rmdir", "shutil.rmtree"):
            hit = real(args[0]) if not isinstance(args[0], int) else None
            if hit:
                stop(hit, event)

    sys.addaudithook(hook)


if os.environ.get("HQ_WALL"):
    _wall()
'''


def _real_claude() -> str:
    for c in (os.environ.get("HQ_WALL_REAL_CLAUDE"), hqpaths.tool("claude", "/opt/homebrew/bin/claude")):
        if c and os.path.exists(c):
            return c
    return ""


def build(wall: str, places, parent_paths: list[str]) -> None:
    for d in ("bin", "py", "tmp", "state/hq", "claude-config", "gh", "syncthing"):
        os.makedirs(os.path.join(wall, d))
    os.makedirs(tmux_dir(wall), exist_ok=True)
    claude = os.path.join(wall, "bin", "claude")
    with open(claude, "w", encoding="utf8") as f:
        f.write(STANDIN.replace("@WALL@", wall).replace("@REAL@", _real_claude()))
    os.chmod(claude, 0o755)
    with open(os.path.join(wall, "py", "sitecustomize.py"), "w", encoding="utf8") as f:
        f.write(SITECUSTOMIZE)
    paths = sorted({os.path.realpath(p) for _, _, p in places} | set(parent_paths))
    with open(os.path.join(wall, "real.json"), "w", encoding="utf8") as f:
        json.dump({"paths": paths, "places": [list(x) for x in places]}, f, indent=1)


def wall_env(wall: str, roots: list[str]) -> dict:
    env = dict(os.environ)
    for k, v in list(env.items()):  # nothing that names a real place goes in
        if k.startswith("HQ_") and os.path.isabs(v) and any(_under(v, r) for r in roots):
            del env[k]
    support = os.path.join(wall, "state", "hq")
    claude = os.path.join(wall, "bin", "claude")
    env.update({
        "HQ_WALL": wall, "HQ_WALL_OUTER": str(os.getpid()), "HQ_UNDER_TEST": "1", "HQ_SUPPORT": support, "HQ_REAL_SUPPORT": support,
        "XDG_STATE_HOME": os.path.join(wall, "state"), "TMUX_TMPDIR": tmux_dir(wall), "TMPDIR": os.path.join(wall, "tmp"),
        "HQ_SYNCTHING_HOME": os.path.join(wall, "syncthing"), "GH_CONFIG_DIR": os.path.join(wall, "gh"), "GIT_SSH_COMMAND": "false",
        "CLAUDE_CONFIG_DIR": os.path.join(wall, "claude-config"), "PATH": os.path.join(wall, "bin") + os.pathsep + env.get("PATH", ""),
        "HQ_CLAUDE": claude, "HQ_CLAUDE_CLI": claude, "HQ_HELPER_CLAUDE": claude, "PYTHONPATH": os.path.join(wall, "py"),
    })
    for k in ("HQ_REAL_ROADMAP", "GH_TOKEN", "GITHUB_TOKEN", "ANTHROPIC_API_KEY"):
        env.pop(k, None)
    return env


def _under(p: str, root: str) -> bool:
    p, root = os.path.realpath(p), os.path.realpath(root)
    return p == root or p.startswith(root + os.sep)


def tmux_dir(wall: str) -> str:
    """The run's own tmux socket: a short path, a socket's name has a limit a nested copy's folder goes past."""
    return os.path.join("/tmp", "hq-" + os.path.basename(wall))


def stop_left(wall: str) -> list[int]:
    """What a run left running in its throwaway folder (a flow's status server outliving it), by exact pid: on Linux the
    processes whose working folder is in it. Two of those held fixed ports for hours on 2 November."""
    out = []
    if not os.path.isdir("/proc"):
        return out
    for nm in os.listdir("/proc"):
        if not nm.isdigit() or int(nm) == os.getpid():
            continue
        try:
            cwd = os.readlink(f"/proc/{nm}/cwd")
        except OSError:
            continue
        if cwd.endswith(" (deleted)"):
            cwd = cwd[:-10]
        if cwd == wall or cwd.startswith(wall + os.sep):
            try:
                os.kill(int(nm), signal.SIGTERM)
                out.append(int(nm))
            except OSError:
                pass
    return out


def stop_tmux(wall: str) -> None:
    stop_left(wall)
    folder = tmux_dir(wall)
    if os.path.isdir(folder):
        if shutil.which("tmux"):
            subprocess.run(["tmux", "kill-server"], env={**os.environ, "TMUX_TMPDIR": folder}, capture_output=True)
        shutil.rmtree(folder, ignore_errors=True)


# -- inside the wall: what the run's own loop asks ----------------------------------------------

def mark(n, uses_claude: bool) -> None:
    """Which flow runs now, for the stand-in and the hook."""
    w = os.environ["HQ_WALL"]
    with open(os.path.join(w, "flow-model"), "w") as f:
        f.write("real" if uses_claude else "stopped")
    with open(os.path.join(w, "flow"), "w") as f:
        f.write(str(n))


def finished() -> None:
    """The run got to its result."""
    with open(os.path.join(os.environ["HQ_WALL"], "finished"), "w") as f:
        f.write("yes")


def outer_gone() -> bool:
    return str(os.getppid()) != os.environ.get("HQ_WALL_OUTER")


class Watch:
    """After each flow: which flow was running when a record moved, the real ones, and the same ones in the copy."""

    def __init__(self):
        self.wall = os.environ["HQ_WALL"]
        info = json.load(open(os.path.join(self.wall, "real.json"), encoding="utf8"))
        self.real = [tuple(x) for x in info["places"]]
        hq = os.path.join(self.wall, "hq")
        self.copy = [(name, rel, os.path.join(hq if where == "hq" else os.path.join(hq, "workspace"), rel)) for name, where, rel in REAL_RECORDS]
        self.was = (stamps(self.real), stamps(self.copy))

    def after(self, n) -> None:
        now = (stamps(self.real), stamps(self.copy))
        for kind, a, b in (("real", self.was[0], now[0]), ("copy", self.was[1], now[1])):
            moved = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
            if moved:
                with open(os.path.join(self.wall, "seen.jsonl"), "a", encoding="utf8") as f:
                    f.write(json.dumps({"flow": n, "kind": kind, "paths": moved}) + "\n")
        self.was = now


def model_calls() -> tuple[int, int]:
    """(real model runs, calls stopped) so far."""
    try:
        lines = open(os.path.join(os.environ["HQ_WALL"], "model-calls.log"), encoding="utf8").read().splitlines()
    except (OSError, KeyError):
        return 0, 0
    real = sum(l.startswith("real\t") for l in lines)
    return real, len(lines) - real


# -- the run ----------------------------------------------------------------------------------

def _seen(wall: str) -> list[dict]:
    try:
        return [json.loads(l) for l in open(os.path.join(wall, "seen.jsonl"), encoding="utf8") if l.strip()]
    except (OSError, ValueError):
        return []


def _during(path: str, seen: list[dict]) -> str:
    flows = [str(s["flow"]) for s in seen if s["kind"] == "real" and path in s["paths"]]
    return f", during flow {', '.join(flows[:5])}" if flows else ""


def _stopped(wall: str) -> list[str]:
    try:
        lines = open(os.path.join(wall, "model-calls.log"), encoding="utf8").read().splitlines()
    except OSError:
        return []
    return sorted({l.split("\t")[1] for l in lines if l.startswith("stopped\t")})


def _projects_gone(wall: str) -> None:
    """A flow marked as using Claude leaves its session under Claude Code's projects, named after the copy's folder: those go with the copy."""
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    mark = re.sub(r"[^A-Za-z0-9]", "-", wall)
    try:
        names = os.listdir(os.path.join(base, "projects"))
    except OSError:
        return
    for nm in names:
        if nm.startswith(mark):
            shutil.rmtree(os.path.join(base, "projects", nm), ignore_errors=True)


def run(argv: list[str], root, keep: bool = False) -> int:
    """The whole run: hash, copy, the flows inside, compare, clean up. Back to the exit code."""
    root = os.path.realpath(str(root))
    real_hq = os.path.realpath(os.environ.get("HQ_REAL_HQ") or root)
    real_ws = os.path.realpath(os.environ.get("HQ_WORKSPACE") or os.path.join(root, "workspace"))
    scratch = os.path.join(root, "scratch")
    state_file = os.path.join(hqpaths.SUPPORT, STATE)
    places = real_places(real_hq, real_ws)
    own = {os.path.realpath(p) for p in os.environ.get("HQ_WALL_OWN", "").split(os.pathsep) if p}  # a proof's own log, written while it runs
    parent = []
    if os.environ.get("HQ_WALL"):
        try:
            parent = json.load(open(os.path.join(os.environ["HQ_WALL"], "real.json"), encoding="utf8"))["paths"]
        except (OSError, ValueError, KeyError):
            parent = []
    reds, notes = [], []
    tried = clear_leftovers(scratch)
    reds += [f"a run that died tried to write a real record: {t.get('path')}" + (f", in flow {t['flow']}" if t.get("flow") else "") for t in tried]
    before = snapshot(places)
    prior = _load(state_file)
    if prior and not prior.get("done"):
        r, n = died(prior, real_hq, before, places)
        reds, notes = reds + r, notes + n
    t0 = time.time()
    state = {"real_hq": real_hq, "start": t0, "alive": t0, "pid": os.getpid(), "done": False, "hashes": before}
    _save(state_file, state)
    wall = os.path.join(scratch, f"{PREFIX}{os.getpid()}")
    code, seen = 1, []
    try:
        os.makedirs(wall)
        build(wall, places, parent)
        copy_hq(root, real_hq, real_ws, os.path.join(wall, "hq"))
        env = wall_env(wall, [real_hq, real_ws, hqpaths.SUPPORT])
        inner = os.path.join(wall, "hq", "app", "happy_flows.py")
        p = subprocess.Popen([sys.executable, inner, *argv], cwd=os.path.join(wall, "hq"), env=env)

        def told(sig, _):
            try:
                p.send_signal(sig)
            except OSError:
                pass
        signal.signal(signal.SIGTERM, told)
        next_beat = time.time() + 30
        while True:
            try:
                code = p.wait(timeout=5)
                break
            except subprocess.TimeoutExpired:
                pass
            if time.time() > next_beat:
                state["alive"], next_beat = time.time(), time.time() + 30
                _save(state_file, state)
        seen = _seen(wall)
        tried = _refused(wall)
        if not os.path.exists(os.path.join(wall, "finished")):  # F111: a run that stops halfway says so, it doesn't look like nothing failed
            try:
                last = open(os.path.join(wall, "flow"), encoding="utf8").read().strip()
            except OSError:
                last = ""
            reds.append(f"the run stopped before its result (exit {code})" + (f", in flow {last}" if last else ""))
    finally:
        stop_tmux(wall)
    reds += [f"a flow tried to write a real record: {t.get('path')}" + (f", in flow {t['flow']}" if t.get("flow") else "") for t in tried]
    after = snapshot(places)
    live = _live_since(real_hq, t0)
    for k in differs(before, after):
        rec = after.get(k) or before.get(k)
        if os.path.realpath(rec["path"]) in own:
            continue
        what = f"{rec['name']} ({k}){_during(rec['path'], seen)}"
        if live:
            notes.append(f"{what} changed while this HQ's routine ran: told apart as its own")
        else:
            reds.append(f"the run changed a real record: {what}")
    state.update({"alive": time.time(), "done": True, "hashes": after})
    _save(state_file, state)
    wrote = {}
    for s in seen:
        if s["kind"] == "copy":
            wrote.setdefault(str(s["flow"]), []).extend(os.path.basename(x) for x in s["paths"])
    print("\n== The wall")
    print(f"{len(after)} real files compared before and after, {len(differs(before, after))} differ; {len(tried)} writes refused.")
    stopped = _stopped(wall)
    if stopped:
        print(f"Stopped at the model's stand-in: flow {', '.join(stopped[:30])}.")
    for n in notes[:12]:
        print(f"  {n}")
    if wrote:
        print("Flows that wrote a record of the copy (no harm, it's thrown away): "
              + "; ".join(f"{f}: {', '.join(sorted(set(v))[:4])}" for f, v in list(wrote.items())[:40]))
    for r in reds:
        print(f"      0: FAILED - {r}")
    if keep:
        print(f"The throwaway folder stays: {wall}")
    else:
        shutil.rmtree(wall, ignore_errors=True)
        _projects_gone(wall)
    return 1 if reds or code else 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["records"]:
        for name, rel, p in real_places(hqpaths.HQ, hqpaths.FOLDER):
            print(f"{'there  ' if os.path.exists(p) else 'missing'}  {name}: {rel}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
