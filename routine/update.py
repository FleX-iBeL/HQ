#!/usr/bin/python3
"""H59: HQ knows its version, sees when there's a newer one, and updates itself with one tap.

11 October 2026 (call at 12:42), typed: "is there some way we can build in that they see when they open the HQ
that there is a new version, with a button to update?" And on the call of 13:14: "if my friends on windows have
to build their own things, wont it erase what they have built and then need to do it again? wouldnt it break
their versions?", "yes skip 3 for now, i dont want them to upload to my github for now. but yes if there is some
way that their versions can be saved this would be essential", "and also a message that if they are up to date
that they are running the latest version, and also that if they click on update, a warning message that if it's
not macos, that explained from above and that claude will get instructions to patch it up locally again" and
"maybe we can put a mini text in more gray with version number, and if you click on it you can see the
changelog what we've added/changed over the versions".

    update.py status            one JSON line: this version, the newest one seen, what's new, the update's state
                                (also starts a check in the background when one is due)
    update.py check [--force]   looks at HQ's public repo for its newest version tag (read only, no login);
                                at most every 6 hours, every 30 minutes after a failed look (offline: quiet)
    update.py changelog         one JSON line: CHANGELOG.md as versions, newest first
    update.py start             starts the update in the background (it ends a call, a job or the mail check that runs)
    update.py restart           H187: restarts what the files on stdin changed (JSON {"changed": [...],
                                "was": {"call": bool, "status": bool}}); one JSON line {"done", "todo"}
    update.py parts             H187: the background parts running now, their exact pids, and what counts as their code
    update.py run               the update itself (what start runs)

The version is the newest version tag HQ's history contains (git describe, v0.2), else the VERSION file (F32: also
when the history has no tags or only older ones). A copy without git history (a download) still sees a newer
version, and its update first makes it a clone in place, every file kept.
A newer version is a tag vX.Y or vX.Y.Z on the public repo with a higher number. The update:
  1. doesn't wait (H187, his change): it ends what runs, by exact pid: the call (hung up, its notes get the minute
     stop.sh gives them), a job's chat (held, so it carries on by itself after the update) and the mail check
     (tried again within a minute); while it installs, the routine starts nothing (tick.updating);
  2. saves anything changed in HQ outside local/ (and the user's own commits) on a backup branch,
     hq-backup/..., never sent anywhere (git stash apply <branch> brings the changes back);
  3. fetches only that tag from the public repo and moves HQ to it; workspace, local/, scratch/ and .status/
     are ignored by the repo, so they are never touched;
  4. restarts every HQ background part, all of them, changed or not (H187), with the new version's own rules (the
     moved HQ's update.py restart, so a fix to these rules counts from the update that brings it): the call line,
     the status page, the watchdog (the Mac's copy reinstalled; on Linux its timer), the routine (the HQ Routine
     helper on a Mac, the units' timers on Linux); the Python packages when the requirements changed, the Mac app
     when it changed. By exact pid, on a Mac and on Linux (there in their own systemd scope, so stopping the status
     server takes nothing else down), and checked: only a part that answers again on a new pid counts as
     restarted, else it's on the note's to-do list. A user's own parts in local/ go first (restart-call-line,
     restart-status-page, install-watchdog). The computer itself is never restarted;
  5. leaves a note for the user's Claude in updates/<version>.md: what changed, what was kept, what to check
     and rebuild in local/.
State: .status/update.json (the last check) and .status/update-run.json (the update), for the pages.
Tests: HQ_UPDATE_URL (another repo, e.g. a folder), HQ_PLATFORM (pretend another computer), HQ_CALL_URL,
HQ_UPDATE_RESTART=0 (restart nothing, end nothing), HQ_UPDATE_ROUTINE=0 (leave the routine and the watchdog alone).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import socket
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402

HQ = hqpaths.HQ
STATUS_DIR = os.path.join(HQ, ".status")
CHECK_FILE = os.path.join(STATUS_DIR, "update.json")
RUN_FILE = os.path.join(STATUS_DIR, "update-run.json")
LOCK = os.path.join(HQ, "scratch", "update.lock")
LOG = os.path.join(HQ, "scratch", "update.log")
NOTES = os.path.join(HQ, "updates")
UPSTREAM = os.environ.get("HQ_UPDATE_URL") or "https://github.com/FleX-iBeL/HQ.git"
CALL_URL = os.environ.get("HQ_CALL_URL") or "http://127.0.0.1:7860"
EVERY = 6 * 3600       # how often to look (Claude's choice: four times a day)
RETRY = 30 * 60        # after a failed look (offline)
PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
# F32: who the update's backup (a stash is a commit) is by, so it works on a computer whose git has no name yet.
IDENTITY = ("-c", "user.name=HQ update", "-c", "user.email=hq-update@localhost")
TAG = re.compile(r"^v(\d+)\.(\d+)(?:\.(\d+))?$")


def platform() -> str:
    return os.environ.get("HQ_PLATFORM") or sys.platform


def log(msg: str) -> None:
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def git(*args: str, timeout: int = 60, check: bool = False) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "PATH": os.environ.get("PATH", "") + ":" + PATH}
    r = subprocess.run(["git", "-C", HQ, *args], capture_output=True, text=True, timeout=timeout, env=env)
    if check and r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout).strip() else f"git {args[0]} failed")
    return r


def vtuple(tag: str) -> tuple[int, int, int] | None:
    m = TAG.match(tag.strip())
    return (int(m[1]), int(m[2]), int(m[3] or 0)) if m else None


def vname(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def read_json(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


# ---- this version -------------------------------------------------------------------------------------------

def has_git() -> bool:
    """F32: HQ is its own git repo (a clone), not a download or a copy without one."""
    return os.path.exists(os.path.join(HQ, ".git"))


def file_version() -> str:
    try:
        v = open(os.path.join(HQ, "VERSION")).read().strip()
        return v if vtuple("v" + v) else ""
    except OSError:
        return ""


def local_version() -> dict:
    """{"tag": "v0.2", "version": "0.2", "ahead": 16}: the newest version tag in HQ's own history, and how many
    changes came after it that aren't in a version yet. Without git, or when the history has no tags (a
    download, a shallow clone), or only older ones than the VERSION file says: the VERSION file (F32)."""
    fv = file_version()
    try:
        if has_git():
            r = git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*", timeout=10)
            tag = r.stdout.strip()
            if r.returncode == 0 and vtuple(tag) and (not fv or vtuple(tag) >= vtuple("v" + fv)):
                ahead = git("rev-list", "--count", f"{tag}..HEAD", timeout=10).stdout.strip()
                return {"tag": tag, "version": vname(tag), "ahead": int(ahead or 0)}
    except Exception:
        pass
    return {"tag": "v" + fv, "version": fv, "ahead": 0} if fv else {"tag": "", "version": "", "ahead": 0}


# ---- the changelog ------------------------------------------------------------------------------------------

def parse_changelog(text: str) -> list[dict]:
    """CHANGELOG.md as [{"title", "version", "coming", "groups": [{"name", "items"}]}], newest first (as written).
    "## 0.2 · 10 October 2026" starts a version, "## Coming next" what isn't in one yet, "### New" a group,
    "- " an item (a line indented under it goes with it)."""
    out: list[dict] = []
    cur = grp = None
    for line in text.splitlines():
        if line.startswith("## "):
            title = line[3:].strip()
            m = re.match(r"v?(\d+\.\d+(?:\.\d+)?)", title)
            cur = {"title": title, "version": m[1] if m else "", "coming": not m, "groups": []}
            grp = None
            out.append(cur)
        elif cur is None:
            continue
        elif line.startswith("### "):
            grp = {"name": line[4:].strip(), "items": []}
            cur["groups"].append(grp)
        elif re.match(r"^\s*[-*] ", line):
            if grp is None:
                grp = {"name": "", "items": []}
                cur["groups"].append(grp)
            grp["items"].append(re.sub(r"^\s*[-*] ", "", line).strip())
        elif line.strip() and grp and grp["items"] and line.startswith("  "):
            grp["items"][-1] += " " + line.strip()
    return out


def changelog() -> dict:
    try:
        text = open(os.path.join(HQ, "CHANGELOG.md")).read()
    except OSError:
        text = ""
    here = local_version()
    versions = parse_changelog(text)
    # "Coming next" only means something on a copy that's ahead of its version (the one it's built on).
    if not here["ahead"]:
        versions = [v for v in versions if not v["coming"]]
    for v in versions:
        v["current"] = bool(v["version"]) and v["version"] == here["version"]
    return {"version": here["version"], "ahead": here["ahead"], "versions": versions}


# ---- looking for a newer one --------------------------------------------------------------------------------

def remote_tags(url: str) -> list[str]:
    """Every version tag on the public repo (read only, no login); raises when it can't be reached."""
    r = subprocess.run(["git", "ls-remote", "--tags", "--refs", url], capture_output=True, text=True, timeout=25,
                       env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "PATH": os.environ.get("PATH", "") + ":" + PATH})
    if r.returncode:
        raise RuntimeError((r.stderr or "").strip().splitlines()[-1] if r.stderr.strip() else "can't reach it")
    tags = [ln.split("refs/tags/", 1)[1] for ln in r.stdout.splitlines() if "refs/tags/" in ln]
    return [t for t in tags if vtuple(t)]


def remote_newest(url: str) -> str | None:
    tags = remote_tags(url)
    return max(tags, key=vtuple) if tags else None


def whats_new(tag: str, since: str) -> list[dict]:
    """The changelog sections after `since` up to `tag`, from the CHANGELOG.md in that version (else its tag's
    message), so the banner can say what's new before anything changes here."""
    r = git("show", f"{tag}:CHANGELOG.md", timeout=10)
    secs = []
    if r.returncode == 0:
        lo, hi = vtuple("v" + since) if since else None, vtuple(tag)
        for s in parse_changelog(r.stdout):
            t = vtuple("v" + s["version"]) if s["version"] else None
            if t and t <= hi and (lo is None or t > lo):
                secs.append(s)
    if not secs:
        msg = git("tag", "-l", "--format=%(contents)", tag, timeout=10).stdout.strip()
        lines = [ln.strip("-* ").strip() for ln in msg.splitlines() if ln.strip() and not ln.startswith("Co-Authored")]
        secs = [{"title": vname(tag), "version": vname(tag), "coming": False,
                 "groups": [{"name": "", "items": lines[:8] or [f"HQ {vname(tag)}"]}]}]
    return secs


def check(force: bool = False) -> dict:
    last = read_json(CHECK_FILE)
    age = time.time() - last.get("checked", 0)
    if not force and age < (RETRY if last.get("offline") else EVERY):
        return last
    here = local_version()
    out = {"checked": time.time(), "version": here["version"], "url": UPSTREAM}
    try:
        newest = remote_newest(UPSTREAM)
        out["offline"] = False
        out["latest"] = vname(newest) if newest else None
        # F32: a copy that doesn't know its own version is older than any release, not the latest.
        mine = vtuple(here["tag"]) if here["tag"] else None
        newer = bool(newest and (mine is None or vtuple(newest) > mine))
        out["available"] = newer
        if newer:
            out["tag"] = newest
            # What's new is a nice-to-have: a failed fetch (no git history here, a folder git can't write in)
            # never hides the newer version, as it did before F32 (the look counted as offline).
            try:
                if not has_git():
                    raise RuntimeError("no git history here")
                git("fetch", "--no-tags", "--quiet", UPSTREAM, f"+refs/tags/{newest}:refs/tags/{newest}", timeout=90, check=True)
                out["new"] = whats_new(newest, here["version"])
            except Exception as e:
                log(f"check: couldn't fetch {newest} for what's new ({str(e)[:120]})")
                out["new"] = [{"title": vname(newest), "version": vname(newest), "coming": False,
                               "groups": [{"name": "", "items": [f"HQ {vname(newest)}: tap Update, and the changelog has the rest."]}]}]
    except Exception as e:  # offline, or the repo can't be reached: quiet, try again later
        out.update(offline=True, available=last.get("available", False) and last.get("version") == here["version"],
                   latest=last.get("latest"), why=str(e)[:200])
        for k in ("tag", "new"):
            if out["available"] and k in last:
                out[k] = last[k]
    write_json(CHECK_FILE, out)
    log(f"check: here {here['version']}, newest {out.get('latest')}, available {out.get('available')}"
        + (f", offline ({out.get('why')})" if out.get("offline") else ""))
    return out


def check_in_background() -> None:
    """Starts `check` detached, unless one started in the last two minutes."""
    try:
        if time.time() - os.path.getmtime(LOCK + ".check") < 120:
            return
    except OSError:
        pass
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    open(LOCK + ".check", "w").write(str(os.getpid()))
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "check"], cwd=HQ, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def status(background: bool = True) -> dict:
    last = read_json(CHECK_FILE)
    here = local_version()
    due = time.time() - last.get("checked", 0) >= (RETRY if last.get("offline") else EVERY)
    if background and (due or last.get("version") not in (None, here["version"]) or last.get("url", UPSTREAM) != UPSTREAM):
        check_in_background()
    # A check from before an update (or of another repo) says nothing about now.
    stale = last.get("version") != here["version"] or last.get("url", UPSTREAM) != UPSTREAM
    available = bool(last.get("available")) and not stale
    run = read_json(RUN_FILE)
    if run.get("state") in ("waiting", "updating") and not alive(run.get("pid")):
        run.update(state="failed", step="", message="The update stopped halfway. Nothing of yours was lost; try it again.")
    return {
        "version": here["version"], "tag": here["tag"], "ahead": here["ahead"],
        "latest": None if stale else last.get("latest"), "available": available,
        "new_tag": last.get("tag") if available else None, "new": last.get("new", []) if available else [],
        "checked": None if stale else last.get("checked"), "offline": bool(last.get("offline")) and not stale,
        "platform": platform(), "mac": platform() == "darwin", "run": run or {"state": "idle"},
    }


# ---- the update ---------------------------------------------------------------------------------------------

def alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def say(state: str, step: str = "", message: str = "", **extra) -> None:
    run = read_json(RUN_FILE)
    run.update(state=state, step=step, message=message, at=time.time(), pid=os.getpid(), **extra)
    write_json(RUN_FILE, run)
    log(f"update: {state} · {step or message}")


def calls_on() -> int | None:
    """How many calls are on (with their after-call work), from the call server; 0 when it doesn't run,
    None when it can't say (a call server from before H59)."""
    try:
        with urllib.request.urlopen(CALL_URL + "/api/busy", timeout=4) as r:
            return int(json.load(r).get("calls", 0))
    except urllib.error.HTTPError:
        return None
    except Exception:
        return 0


def start() -> dict:
    run = read_json(RUN_FILE)
    if run.get("state") in ("waiting", "updating") and alive(run.get("pid")):
        return status(background=False)
    st = status(background=False)
    if not st["available"]:
        return st
    write_json(RUN_FILE, {"state": "waiting", "step": "Starting the update", "message": "", "at": time.time(),
                          "from": st["version"], "to": vname(st["new_tag"])})
    # H187: on Linux in its own scope: started from the status server, it would otherwise go down with it.
    p = subprocess.Popen(scoped([sys.executable, os.path.abspath(__file__), "run"], "update"), cwd=HQ, stdin=subprocess.DEVNULL,
                         stdout=open(LOG, "a"), stderr=subprocess.STDOUT, start_new_session=True)
    run = read_json(RUN_FILE)
    run["pid"] = p.pid
    write_json(RUN_FILE, run)
    return status(background=False)


def changed_outside_local() -> list[str]:
    """What the user changed in HQ's own files (tracked, and new files the repo doesn't ignore)."""
    r = git("status", "--porcelain", "--untracked-files=all", timeout=30)
    return [ln[3:] for ln in r.stdout.splitlines() if ln.strip()]


def backup(target: str) -> dict:
    """Saves the user's changes and own commits on branches, never sent anywhere. Returns what it saved."""
    stamp = time.strftime("%Y%m%d-%H%M")
    saved = {}
    files = changed_outside_local()
    if files:
        name = f"hq-backup/{stamp}-before-{target}-changes"
        # F32: a stash is a commit, and a fresh computer often has no git name and email yet.
        git(*IDENTITY, "stash", "push", "--include-untracked", "-m", f"HQ update backup before {target}", timeout=60, check=True)
        git("branch", name, "stash@{0}", timeout=10, check=True)
        git("stash", "drop", timeout=10)
        saved["changes"] = {"branch": name, "files": files[:200]}
    head = git("rev-parse", "HEAD", timeout=10).stdout.strip()
    own = git("rev-list", "--count", f"{target}..HEAD", timeout=10).stdout.strip()
    if head and own and int(own) > 0:
        name = f"hq-backup/{stamp}-before-{target}-commits"
        git("branch", name, head, timeout=10, check=True)
        saved["commits"] = {"branch": name, "count": int(own)}
    return saved


def listening(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


# ---- H187: the background parts, restarted by exact pid --------------------------------------------------------
# 17 October 2026 (call at 10:42), typed: "now when i update on my macbook, i still need to reboot my whole
# laptop because only restarting the application isnt enough. do my friends will have the same? because if so then i
# want that when a new release is installed then all these backend processes get forced rebooted if thats also needed"
# What keeps running, and so keeps the old code in memory: the call line (app/bot.py, which imports app/ and
# routine/) and the status server (status/server.mjs and its .mjs). The routine (tick.py), the watchdog, the jobs,
# the mail check and the small helpers start fresh each time; the Mac's watchdog runs from its own copy; the HQ app
# and the HQ Routine helper are apps.
# Then, same call: "no if they update they must be forced out of everything and then get the reboot." So an update
# doesn't wait: it ends the call, a job's chat and the mail check (force_out), and restarts every part, all of them,
# changed or not (restart). Never the computer itself.

CALL_MARK, STATUS_MARK = "app/bot.py", "status/server.mjs"
RUN_DIR = os.path.join(HQ, "scratch", "routine")
HELPERS = [os.path.expanduser("~/Applications/HQ Routine.app"), os.path.expanduser("~/Applications/Jarvis Routine.app")]


def cmdline(pid: int) -> str:
    return subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()


def pids_on(port: int) -> list[int]:
    """This user's pids listening on a port: lsof on a Mac, ss elsewhere."""
    if platform() == "darwin" or not shutil.which("ss"):
        r = subprocess.run(["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"], capture_output=True, text=True)
        return sorted({int(p) for p in r.stdout.split() if p.isdigit()})
    r = subprocess.run(["ss", "-Hltnp", f"sport = :{port}"], capture_output=True, text=True)
    return sorted({int(p) for p in re.findall(r"pid=(\d+)", r.stdout)})


def pid_on(port: int, must: str) -> int | None:
    """The exact pid listening on a port, only when its command line has `must` in it."""
    for p in pids_on(port):
        if must in cmdline(p):
            return p
    return None


def scoped(cmd: list[str], name: str) -> list[str]:
    """H187: on Linux, a command in its own systemd user scope when there is one (as tick.open_window), so it never
    belongs to the unit of whoever started it: the status server's, which takes everything in it down when it stops."""
    if platform() == "darwin" or not os.environ.get("XDG_RUNTIME_DIR") or not shutil.which("systemd-run"):
        return cmd
    return ["systemd-run", "--user", "--scope", "--quiet", f"--unit={hqpaths.unit(name)}-{int(time.time())}-{os.getpid()}"] + cmd


def gone(pid: int, secs: float) -> bool:
    end = time.time() + secs
    while time.time() < end:
        if not alive(pid) or "<defunct>" in cmdline(pid) or not cmdline(pid):
            return True
        time.sleep(0.2)
    return not alive(pid)


def stop_pid(pid: int) -> bool:
    """Stops one exact pid: TERM, then KILL when it doesn't go."""
    for sig, secs in ((15, 10), (9, 3)):
        try:
            os.kill(pid, sig)
        except OSError:
            return True
        if gone(pid, secs):
            return True
    return False


def came_back(port: int, must: str, old: int | None, secs: float) -> int | None:
    """The new pid once the part listens again on a pid other than the old one."""
    end = time.time() + secs
    while time.time() < end:
        p = pid_on(port, must)
        if p and p != old:
            return p
        time.sleep(0.5)
    return None


def children(pid: int) -> list[int]:
    r = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True)
    return [int(x) for x in r.stdout.split() if x.isdigit()]


def tree(pid: int) -> list[int]:
    """A pid and everything under it, the deepest first: exact pids, never a name."""
    out = []
    for c in children(pid):
        out += tree(c)
    return out + [pid]


def ancestors() -> set[int]:
    """This process and the ones above it: a job's chat that started this update is never ended by it."""
    out, p = set(), os.getpid()
    while p > 1 and p not in out:
        out.add(p)
        r = subprocess.run(["ps", "-o", "ppid=", "-p", str(p)], capture_output=True, text=True).stdout.strip()
        p = int(r) if r.isdigit() else 0
    return out


def window_pid(state: str, pidfile: str) -> int | None:
    """The pid of a job's or the mail check's window script, from the routine's own files."""
    pid = read_json(os.path.join(RUN_DIR, state)).get("pid")
    if not pid:
        try:
            pid = int(open(os.path.join(RUN_DIR, pidfile)).read().strip())
        except (OSError, ValueError):
            pid = None
    return int(pid) if pid and alive(pid) else None


def end_tree(pid: int) -> None:
    for p in tree(pid):
        stop_pid(p)


def running_job() -> int | None:
    try:
        m = re.search(r"^- Job (\d+) · running", open(hqpaths.ROADMAP).read(), re.M)
    except OSError:
        return None
    return int(m.group(1)) if m else None


def stop_call_line() -> list[str]:
    """Hangs up a call and stops the call line (stop.sh: its notes get a minute), then its exact pid if it stays."""
    port = hqpaths.call_port()
    old = pid_on(port, CALL_MARK)
    if not old:
        return []
    n = calls_on()
    try:
        subprocess.run([os.path.join(HQ, "app", "stop.sh" if platform() == "darwin" else "stop-linux.sh")], cwd=HQ, capture_output=True, timeout=120,
                       env={**os.environ, "PATH": os.environ.get("PATH", "") + ":" + PATH})
    except Exception:
        pass
    if not gone(old, 1):
        stop_pid(old)
    # Its restart says the pids; only a call that was on is worth its own line.
    return [f"ended the call that was on (the call line, pid {old})"] if n else []


def force_out(stop_call: bool = False) -> list[str]:
    """H187: ends what runs, so no old code keeps going: a job's chat (held, it carries on by itself after the
    update), the mail check (tried again within a minute), and with stop_call the call line (a call drops).
    By exact pid only. Returns what it ended."""
    if os.environ.get("HQ_UPDATE_RESTART") == "0":
        return []
    ended, mine = [], ancestors()
    n, pid = running_job(), window_pid("job.json", "job.pid")
    if n and pid and pid in mine:
        ended.append(f"left job {n}'s chat running: it started this update")
    elif n:
        if pid:
            end_tree(pid)
        subprocess.run([sys.executable, os.path.join(HERE, "jobs.py"), "held", str(n),
                        "an update was installed; it carries on by itself"], capture_output=True, text=True)
        for f in ("job.json", "job.pid"):
            try:
                os.remove(os.path.join(RUN_DIR, f))
            except OSError:
                pass
        ended.append(f"ended job {n}'s chat" + (f" (pid {pid})" if pid else "") + "; it carries on by itself after the update")
    pid = window_pid("mail.json", "mail.pid")
    if pid and pid not in mine:
        end_tree(pid)
        for f in ("mail.json", "mail.pid"):
            try:
                os.remove(os.path.join(RUN_DIR, f))
            except OSError:
                pass
        # Not a failed run: it's started again at the routine's next look.
        write_json(os.path.join(RUN_DIR, "mail-retry"), {"at": time.time(), "n": 0})
        ended.append(f"ended the mail check (pid {pid}); it runs again within a minute")
    if stop_call:
        ended += stop_call_line()
    return ended


def helper_pids() -> list[int]:
    """The Mac's HQ Routine helper: the process whose program is the applet itself (as watchdog.pids)."""
    r = subprocess.run(["ps", "-ax", "-o", "pid=,comm="], capture_output=True, text=True)
    ends = tuple(os.path.basename(a) + "/Contents/MacOS/applet" for a in HELPERS)
    return [int(p) for p, _, c in (ln.strip().partition(" ") for ln in r.stdout.splitlines())
            if p.isdigit() and c.strip().endswith(ends)]


def code_of(changed: list[str]) -> dict:
    """Which parts' code the changed files are (H187): what needs more than a restart, and what to say."""
    return {
        "call": [f for f in changed if (f.startswith("app/") and not os.path.basename(f).startswith(("happy_flows", "test_")))
                 or (f.startswith("routine/") and f.endswith(".py"))],
        "status": [f for f in changed if f.startswith("status/") and f.endswith(".mjs")],
        "watchdog": [f for f in changed if f == "routine/watchdog.py"],
        "packages": [f for f in changed if f == "app/requirements.txt"],
        "helper": [f for f in changed if f in ("routine/routine.applescript", "routine/build-app.sh")],
        "units": [f for f in changed if f == "routine/install-linux.sh"],
        "app": [f for f in changed if f.startswith("desktop/") and not f.endswith((".html", ".js", ".css", ".py"))],
        "strip": [f for f in changed if f.startswith("desktop/") and f.endswith((".html", ".js", ".css"))],
    }


def parts() -> dict:
    """The background parts running now, with their exact pids (H187)."""
    cp, sp = hqpaths.call_port(), hqpaths.status_port()
    return {"call": {"port": cp, "pid": pid_on(cp, CALL_MARK), "code": "app/, routine/*.py"},
            "status": {"port": sp, "pid": pid_on(sp, STATUS_MARK), "code": "status/*.mjs"},
            "helper": helper_pids() if platform() == "darwin" else None,
            "job": {"n": running_job(), "pid": window_pid("job.json", "job.pid")},
            "mail": {"pid": window_pid("mail.json", "mail.pid")},
            "fresh": "the routine (tick.py), the watchdog on Linux, jobs, the mail check, the helpers: started anew each time"}


def restart_new(changed: list[str], was_running: dict) -> tuple[list[str], list[str]]:
    """H187: the restart step with the moved HQ's own update.py, so the new version's rules decide what restarts.
    Falls back on this one's rules when the new file can't do it."""
    if os.environ.get("HQ_UPDATE_RESTART") == "0":
        return ["nothing restarted (test)"], []
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "update.py"), "restart"], cwd=HQ, capture_output=True,
                           text=True, timeout=3 * 3600, input=json.dumps({"changed": changed, "was": was_running}))
        out = json.loads(r.stdout.strip().splitlines()[-1])
        return list(out["done"]), list(out["todo"])
    except Exception as e:
        log(f"update: the new version's restart didn't answer ({str(e)[:120]}); restarting with this one's rules")
        return restart(changed, was_running)


def restart(changed: list[str], was_running: dict) -> tuple[list[str], list[str]]:
    """Restarts every HQ background part, changed or not (H187), by exact pid, and checks each came back on a new
    pid. First ends what still runs (a job or mail check started meanwhile, or by an older update that waited).
    Returns (what was done, what the user or their Claude still has to do)."""
    done, todo = [], []
    if os.environ.get("HQ_UPDATE_RESTART") == "0":
        return ["nothing restarted (test)"], []
    env = {**os.environ, "PATH": os.environ.get("PATH", "") + ":" + PATH}
    mac = platform() == "darwin"
    code = code_of(changed)
    done += force_out()

    def ran(cmd, what, detach=False, name="part"):
        try:
            if detach:
                subprocess.Popen(scoped(cmd, name), cwd=HQ, env=env, stdin=subprocess.DEVNULL, stdout=open(LOG, "a"),
                                 stderr=subprocess.STDOUT, start_new_session=True)
                ok = True
            else:
                ok = subprocess.run(scoped(cmd, name), cwd=HQ, env=env, capture_output=True, timeout=900).returncode == 0
        except Exception:
            ok = False
        if not ok:
            todo.append(f"{what}: it didn't work, do it by hand")
        return ok

    if code["packages"]:
        pip = os.path.join(HQ, ".venv", "bin", "pip")
        if os.path.exists(pip):
            ran([pip, "install", "-q", "-r", os.path.join(HQ, "app", "requirements.txt")], "installed the new Python packages") \
                and done.append("installed the new Python packages")
        else:
            todo.append("install the new Python packages (app/requirements.txt)")
    if code["app"]:
        app = os.path.expanduser("~/Applications/HQ.app")
        if mac and os.path.isdir(app):
            if ran(["/bin/zsh", os.path.join(HQ, "desktop", "build.sh"), "--install"], "reinstalled the Mac app"):
                done.append("reinstalled the Mac app")
                todo.append("close the HQ app and open it again, to use the new one")
    elif code["strip"] and mac and os.path.isdir(os.path.expanduser("~/Applications/HQ.app")):
        todo.append("the HQ app's strip changed: close the HQ app and open it again to see it")

    # The call line: app/bot.py holds app/ and routine/ in memory. Always restarted when it ran (a call drops).
    cport = hqpaths.call_port()
    if was_running.get("call") or pid_on(cport, CALL_MARK):
        old = pid_on(cport, CALL_MARK)
        before = old or was_running.get("call_pid")  # the update may have stopped it already (force_out)
        own = hqpaths.part_cmd("restart-call-line")
        if own:
            ran(own, "restarted the call line (your own part)", name="call") and done.append("restarted the call line (your own part)")
        else:
            if old:
                stop_call_line()
            if old and not gone(old, 1):
                todo.append(f"the call line's old process (pid {old}) wouldn't stop: restart the computer once")
            else:
                ran([os.path.join(HQ, "app", "start.sh" if mac else "start-linux.sh")], "restarted the call line", name="call")
                new = came_back(cport, CALL_MARK, before, 90)
                if new:
                    done.append(f"restarted the call line (pid {before} → {new})" if before else f"restarted the call line (pid {new})")
                elif not any(t.startswith("restarted the call line") for t in todo):
                    todo.append("restarted the call line: it didn't come back, start it by hand (app/start.sh) or let the routine do it")

    # The routine and the watchdog: on a Mac the HQ Routine helper and the watchdog's own copy, on Linux their timers.
    # HQ_UPDATE_ROUTINE=0: a test on a computer whose own routine runs leaves them alone.
    own = hqpaths.part_cmd("install-watchdog")
    if os.environ.get("HQ_UPDATE_ROUTINE") == "0":
        pass
    elif own:
        ran(own, "installed the watchdog again (your own part)") and done.append("installed the watchdog again (your own part)")
    elif mac:
        ran(["/bin/zsh", os.path.join(HQ, "routine", "install-watchdog.sh")], "installed the watchdog again") \
            and done.append("installed the watchdog again")
    if os.environ.get("HQ_UPDATE_ROUTINE") == "0":
        pass
    elif mac:
        olds = helper_pids()
        app = next((a for a in HELPERS if os.path.isdir(a)), None)
        if olds or app:
            stuck = [p for p in olds if not stop_pid(p)]
            if stuck:
                todo.append(f"the HQ Routine helper (pid {stuck[0]}) wouldn't stop: restart the computer once")
            elif app and ran(["open", "-g", app], "restarted the HQ Routine helper"):
                end, new = time.time() + 20, []
                while time.time() < end and not new:
                    new = [p for p in helper_pids() if p not in olds]
                    time.sleep(0.5)
                if new:
                    done.append(f"restarted the HQ Routine helper (pid {olds[0]} → {new[0]})" if olds
                                else f"started the HQ Routine helper (pid {new[0]})")
                else:
                    todo.append("restarted the HQ Routine helper: it didn't come back; the watchdog starts it within 5 minutes")
        if code["helper"]:
            todo.append("the routine helper changed: rebuild it with routine/build-app.sh (macOS asks for one Allow)")
    else:
        udir = os.path.expanduser("~/.config/systemd/user")
        timers = [t for t in (hqpaths.unit("routine.timer"), hqpaths.unit("watchdog.timer"))
                  if os.path.exists(os.path.join(udir, t))]
        if timers and shutil.which("systemctl"):
            subprocess.run(["systemctl", "--user", "daemon-reload"], env=env, capture_output=True, timeout=60)
            if ran(["systemctl", "--user", "restart"] + timers, "restarted the routine's and the watchdog's timers"):
                up = subprocess.run(["systemctl", "--user", "is-active"] + timers, env=env, capture_output=True,
                                    text=True, timeout=30).stdout.split()
                if up and all(u == "active" for u in up):
                    done.append("restarted " + " and ".join(timers) + " (the routine and the watchdog run the new code)")
                else:
                    todo.append("the routine's or the watchdog's timer isn't active again: systemctl --user status "
                                + " ".join(timers))
        elif not own:
            todo.append("the routine and the watchdog: restart your own parts in local/ (start at login)")
        if code["units"]:
            todo.append("the Linux units changed: run routine/install-linux.sh again (it keeps the HQ_ settings you give it)")

    # The status page last: the pages watching this update are served by it.
    sport = hqpaths.status_port()
    if was_running.get("status") or pid_on(sport, STATUS_MARK):
        own = hqpaths.part_cmd("restart-status-page")
        if own:
            ran(own, "restarted the status page (your own part)", detach=True, name="status") \
                and done.append("restarted the status page (your own part)")
        else:
            old = pid_on(sport, STATUS_MARK)
            if old and not stop_pid(old):
                todo.append(f"the status page's old process (pid {old}) wouldn't stop: restart the computer once")
            else:
                ran([hqpaths.shell(), os.path.join(HQ, "status", "phone.sh")], "restarted the status page", name="status")
                new = came_back(sport, STATUS_MARK, old, 20)
                if new:
                    done.append(f"restarted the status page (pid {old} → {new})" if old else f"restarted the status page (pid {new})")
                elif not any(t.startswith("restarted the status page") for t in todo):
                    todo.append("restarted the status page: it didn't come back; the routine starts it again within a minute")
    return done, todo


def notes(old: str, new: str, saved: dict, changed: list[str], done: list[str], todo: list[str]) -> str:
    """The note for the user's Claude: updates/<new>.md. Returns its path, relative to HQ."""
    os.makedirs(NOTES, exist_ok=True)
    path = os.path.join(NOTES, f"{new}.md")
    secs = [s for s in parse_changelog(open(os.path.join(HQ, "CHANGELOG.md")).read())
            if s["version"] and vtuple("v" + s["version"]) and vtuple("v" + s["version"]) <= vtuple(new)
            and (not vtuple("v" + old) or vtuple("v" + s["version"]) > vtuple("v" + old))] \
        if os.path.exists(os.path.join(HQ, "CHANGELOG.md")) and vtuple(new) else []
    mine = sorted(os.listdir(hqpaths.LOCAL)) if os.path.isdir(hqpaths.LOCAL) else []
    names = {re.sub(r"\.(sh|py|ps1|cmd|bat)$", "", m) for m in mine}
    hit = sorted({f for f in changed for n in names if n and n.split("-")[-1] in f})
    w = [f"# HQ updated: {old or '?'} → {vname(new)}", "",
         f"Updated on {time.strftime('%d %B %Y at %H:%M')}, on {platform()}. For the Claude that runs this HQ: read this, "
         "do what it says, then tell the user in a sentence or two and move this note into updates/done/.", ""]
    w += ["## What's new", ""]
    for s in secs or [{"title": vname(new), "groups": []}]:
        w.append(f"### {s['title']}")
        for g in s["groups"]:
            for it in g["items"]:
                w.append(f"- {g['name'] + ': ' if g['name'] else ''}{it}")
        w.append("")
    w += ["## What was kept", "",
          "- The workspace (the user's own files), local/ (their own builds), scratch/ and .status/: never touched."]
    if saved.get("changes"):
        b = saved["changes"]["branch"]
        w.append(f"- Changes to HQ's own files, saved on the branch `{b}` (never sent anywhere): "
                 + ", ".join(saved["changes"]["files"][:30]) + ". To bring them back: "
                 f"`git stash apply {b}`; if something clashes with the new version, move it into local/ instead.")
    if saved.get("commits"):
        b = saved["commits"]["branch"]
        w.append(f"- The user's own commits ({saved['commits']['count']}), saved on the branch `{b}`. "
                 f"To bring them back: `git cherry-pick v{old}..{b}`, or move them into local/.")
    w += ["", "## What the update did", ""] + [f"- {d}" for d in done or ["nothing needed a restart"]]
    w += ["", "## What to check, and rebuild locally", ""]
    w += [f"- {t}" for t in todo]
    if platform() != "darwin":
        w.append("- This computer isn't a Mac, so HQ's Mac parts (starting at login, the watchdog, Terminal windows) "
                 "are replaced by the user's own parts in local/. Look at what changed below; where a Mac part "
                 "changed, change the user's own version in local/ the same way. Build only in local/.")
    if hit:
        w.append("- These changed files are what the user's own parts in local/ stand in for: " + ", ".join(hit)
                 + ". Check those parts still do the same.")
    w.append("- Run the happy flows that fit this computer (`python3 app/happy_flows.py --help`), and one short call.")
    w += ["", "## Every file that changed", ""] + [f"- {f}" for f in changed[:300]]
    with open(path, "w") as f:
        f.write("\n".join(w) + "\n")
    return os.path.relpath(path, HQ)


def ensure_repo(old: str, tag: str) -> str:
    """F32: HQ came as a download or a copy, without its git history. Makes it a clone in place without
    touching a single file: the history of the version it says it is (else the new one) is fetched and set as
    where it stands, so what differs from that version counts as the user's own change and is saved first."""
    tags = remote_tags(UPSTREAM)
    base = ("v" + old) if old and ("v" + old) in tags else tag
    git("init", "-q", timeout=30, check=True)
    if git("remote", "get-url", "origin", timeout=10).returncode:
        git("remote", "add", "origin", UPSTREAM, timeout=10, check=True)
    for t in {base, tag}:
        git("fetch", "--no-tags", "--quiet", UPSTREAM, f"+refs/tags/{t}:refs/tags/{t}", timeout=300, check=True)
    commit = git("rev-parse", f"{base}^{{commit}}", timeout=10, check=True).stdout.strip()
    git("update-ref", "refs/heads/main", commit, timeout=10, check=True)
    git("symbolic-ref", "HEAD", "refs/heads/main", timeout=10, check=True)
    git("reset", "-q", timeout=60, check=True)  # the index only; every file stays as it is
    log(f"update: made HQ a git copy at {base}")
    return base


def run() -> int:
    target = read_json(RUN_FILE).get("to")
    st = status(background=False)
    tag = st.get("new_tag") or (("v" + target) if target else None)
    old = st["version"]
    if not tag or not vtuple(tag):
        say("failed", message="There's no newer version to update to.")
        return 1
    say("updating", "Getting ready", **{"from": old, "to": vname(tag)})
    try:
        was = {"call": listening(hqpaths.call_port()), "status": listening(hqpaths.status_port()),
               "call_pid": pid_on(hqpaths.call_port(), CALL_MARK)}
        # H187: no waiting for a call or a job: what runs is ended first, so nothing runs while the files move.
        say("updating", "Ending what runs: the call, the job, the mail check")
        ended = force_out(stop_call=True)
        made = None
        if not has_git():
            say("updating", "Making HQ a git copy, so it can update")
            made = ensure_repo(old, tag)
        say("updating", "Saving anything you changed")
        saved = backup(tag)
        say("updating", f"Getting {vname(tag)}", saved=saved)
        if git("rev-parse", "-q", "--verify", f"refs/tags/{tag}", timeout=10).returncode:
            git("fetch", "--no-tags", "--quiet", UPSTREAM, f"+refs/tags/{tag}:refs/tags/{tag}", timeout=120, check=True)
        before = git("rev-parse", "HEAD", timeout=10).stdout.strip()
        branch = git("symbolic-ref", "-q", "--short", "HEAD", timeout=10).stdout.strip()
        say("updating", f"Moving HQ to {vname(tag)}")
        if branch and git("merge-base", "--is-ancestor", "HEAD", tag, timeout=10).returncode == 0:
            git("merge", "--ff-only", "--quiet", tag, timeout=60, check=True)
        else:
            git("checkout", "--quiet", "--detach", tag, timeout=60, check=True)
        changed = [f for f in git("diff", "--name-only", before, "HEAD", timeout=30).stdout.splitlines() if f]
        if made == tag:  # its own version wasn't on the public repo: everything that differed was set right
            changed = sorted(set(changed) | set(saved.get("changes", {}).get("files", [])))
        say("updating", "Restarting what changed")
        done, todo = restart_new(changed, was)
        done = ended + done
        note = notes(old, tag, saved, changed, done, todo)
        bits = [f"Updated to {vname(tag)}."]
        if saved:
            bits.append("Your own changes are saved on a backup branch.")
        if platform() != "darwin":
            bits.append("Your Claude has instructions to patch things up locally.")
        say("done", "", " ".join(bits), done=done, todo=todo, notes=note, saved=saved, finished=time.time())
        check(force=True)
        return 0
    except Exception as e:
        say("failed", "", f"The update didn't go through: {str(e)[:200]}. HQ stays as it was; nothing of yours was lost.")
        return 1


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "status"
    if cmd == "status":
        print(json.dumps(status()))
    elif cmd == "check":
        print(json.dumps(check(force="--force" in argv)))
        try:
            os.remove(LOCK + ".check")
        except OSError:
            pass
    elif cmd == "changelog":
        print(json.dumps(changelog()))
    elif cmd == "start":
        print(json.dumps(start()))
    elif cmd == "run":
        return run()
    elif cmd == "restart":
        req = json.loads(sys.stdin.read() or "{}")
        done, todo = restart(list(req.get("changed") or []), dict(req.get("was") or {}))
        print(json.dumps({"done": done, "todo": todo}))
    elif cmd == "parts":
        print(json.dumps(parts()))
    elif cmd == "version":
        print(json.dumps(local_version()))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
