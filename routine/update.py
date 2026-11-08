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
    update.py here              one JSON line: this code's version (its tag, how far ahead), for a copy without git (H340)
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
F104: `back [--tag vX.Y.Z]` one version back (on the work line past a version: that version; on a friend's copy with commits of her own past a
tag: the one below it; never to a version with no `forward` of its own, unless the release after it wrote that down, routine/way-back.json:
F112, then the update bar is the way forward from there), in the background, here and on the other
computer through the forward; the main runs the undos of the data changes it leaves behind (routine/datachange.py) first and tells the
other computer only once that held, so a failing undo leaves both where they were (started on the backup, the main goes first); the
backup gets them by the sync; while back on the maker's HQ the team waits. `forward` the other way. Tests: HQ_UPDATE_WAIT in the foreground.
F104, the guard on the state: `release_minute`, the routine's first thing every minute on a copy that isn't the maker's. Words can't keep a job
off the work line (`git checkout -` is ordinary git), so it looks at what's checked out: commits no version tag reaches that are on GitHub's
dev. Then it goes back on the newest release as `back` does, stops a job that runs, and starts nothing on top of it.
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
PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
# F32: who the update's backup (a stash is a commit) is by, so it works on a computer whose git has no name yet.
IDENTITY = ("-c", "user.name=HQ update", "-c", "user.email=hq-update@localhost")
TAG = re.compile(r"^v(\d+)\.(\d+)(?:\.(\d+))?$")
WAY_BACK = os.path.join(HQ, "routine", "way-back.json")  # F112: versions with no forward of their own, written by the release after them
BACK_FILE = os.path.join(STATUS_DIR, "back.json")      # F104: this HQ went back: from where, to which version
OTHER_FILE = os.path.join(STATUS_DIR, "back-other.json")  # F104: the other computer still has to hear it
GUARD_FILE = os.path.join(STATUS_DIR, "off-release.json")  # F104: the guard's last look, and what it holds
GUARD_KEY = "off-release"
GUARD_LOOK = 3600      # F104: a head that's been looked at goes to GitHub again this often (a friend's own commits don't change by waiting)
GUARD_OFFLINE = 300    # F104: after a look that didn't reach GitHub
GUARD_RETRY = 900      # F104: a going back that didn't go through is tried again this often, and held until then
WORK_LINE = ("dev", "nightly")


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
    try:  # H340: a throwaway copy without git (routine/realcase.py) carries the version state of the code it was made of
        with open(os.path.join(HQ, ".version-here.json")) as f:
            d = json.load(f)
        if vtuple(d.get("tag", "")):
            return {"tag": d["tag"], "version": d.get("version") or vname(d["tag"]), "ahead": int(d.get("ahead") or 0)}
    except (OSError, ValueError, TypeError, AttributeError):
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
        "clash": clash_status(),
    }


def _extensions():
    """H235: app/extensions.py of the HQ as it stands now (after an update: the new version's)."""
    app = os.path.join(HQ, "app")
    if app not in sys.path:
        sys.path.insert(0, app)
    import extensions
    return extensions


def clash_status() -> dict | None:
    """H235: after an update, whether something they added might clash with it, for the version bar: shown while it's
    new; a day after a button, what was done."""
    try:
        ex = _extensions()
        c = ex.clash()
    except Exception:
        return None
    if not c.get("clashes") or c.get("state") not in ("new", "chat", "team"):
        return None
    if c["state"] != "new" and time.time() - float(c.get("settled") or 0) > 86400:
        return None
    return {"state": c["state"], "to": c.get("to"), "words": ex.clash_words(c),
            "items": [{"name": x["name"], "why": x["why"]} for x in c["clashes"]]}


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
    if read_json(GUARD_FILE).get("held"):  # F104: no update on top of work that isn't released; the guard goes back first
        return {**st, "said": "HQ is going back on its released version first; the update can start after that."}
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


def _free_branch(name: str) -> str:
    """F104: a branch name nothing has yet: going back twice within a minute saves twice."""
    return next(n for n in (name, *(f"{name}-{i}" for i in range(2, 1000))) if git("rev-parse", "-q", "--verify", f"refs/heads/{n}", timeout=10).returncode)


def _saved_already(head: str) -> str:
    """F104: the backup branch that already holds exactly these commits: a try after one that failed saved nothing new."""
    names = git("for-each-ref", f"--points-at={head}", "--format=%(refname:short)", "refs/heads/hq-backup/", timeout=20).stdout.split()
    return next((n for n in names if re.search(r"-commits(-\d+)?$", n)), "")


def backup(target: str) -> dict:
    """Saves the user's changes and own commits on branches, never sent anywhere. Returns what it saved."""
    stamp = time.strftime("%Y%m%d-%H%M")
    saved = {}
    files = changed_outside_local()
    if files:
        name = _free_branch(f"hq-backup/{stamp}-before-{target}-changes")
        # F32: a stash is a commit, and a fresh computer often has no git name and email yet.
        git(*IDENTITY, "stash", "push", "--include-untracked", "-m", f"HQ update backup before {target}", timeout=60, check=True)
        git("branch", name, "stash@{0}", timeout=10, check=True)
        git("stash", "drop", timeout=10)
        saved["changes"] = {"branch": name, "files": files[:200]}
    head = git("rev-parse", "HEAD", timeout=10).stdout.strip()
    own = git("rev-list", "--count", f"{target}..HEAD", timeout=10).stdout.strip()
    if head and own and int(own) > 0:
        name = _saved_already(head)
        if not name:
            name = _free_branch(f"hq-backup/{stamp}-before-{target}-commits")
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
HELPERS = [os.path.expanduser("~/Applications/HQ Routine.app")]


def cmdline(pid: int) -> str:
    return subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()


def pids_on(port: int) -> list[int]:
    """This user's pids listening on a port: lsof on a Mac, ss elsewhere."""
    if platform() == "darwin" or not shutil.which("ss"):
        # F44: lsof lives in /usr/sbin on a Mac, which the helper app's bare PATH leaves out.
        lsof = shutil.which("lsof", path=os.environ.get("PATH", "") + ":" + PATH) or "/usr/sbin/lsof"
        r = subprocess.run([lsof, "-ti", f"tcp:{port}", "-sTCP:LISTEN"], capture_output=True, text=True)
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


# F68, his quick note of 25 October 2026: "there's still a bug on the laptop if you update then the gui doesnt
# restart, i need a full reboot of everything, backend and front end processes including the app itself". The HQ app
# keeps its strip (shell.html, read once), the status page and the call page loaded from the old call line and status
# server, with the old code in them, and the update only said "close the HQ app and open it again". Now restart()
# ends it last, by its exact pid, and opens it again, so it loads everything from the new version.
# HQ_APP_BUNDLE: a test's stand-in bundle (its Contents/MacOS/HQ), also off a Mac.
def app_bundles() -> list[str]:
    own = os.environ.get("HQ_APP_BUNDLE")
    return [own] if own else [os.path.expanduser("~/Applications/HQ.app"), os.path.join(HQ, "scratch", "desktop", "HQ.app")]


def app_pids() -> list[tuple[int, str]]:
    """The HQ app running now: (exact pid, its bundle), the process whose program is the bundle's own HQ."""
    if platform() != "darwin" and not os.environ.get("HQ_APP_BUNDLE"):
        return []
    exes = {os.path.join(b, "Contents", "MacOS", "HQ"): b for b in app_bundles()}
    r = subprocess.run(["ps", "-ax", "-o", "pid=,command="], capture_output=True, text=True)
    out = []
    for ln in r.stdout.splitlines():
        p, _, c = ln.strip().partition(" ")
        c = c.strip()
        for exe, b in exes.items():
            if p.isdigit() and (c == exe or c.startswith(exe + " ")):
                out.append((int(p), b))
    return out


def open_app(bundle: str) -> bool:
    if platform() == "darwin" and not os.environ.get("HQ_APP_BUNDLE"):
        cmd = ["open", "-g", bundle]
    else:  # a test's stand-in: its program, on its own
        cmd = [os.path.join(bundle, "Contents", "MacOS", "HQ"), "600"]
    try:
        subprocess.Popen(cmd, cwd=HQ, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True
    except OSError:
        return False


def restart_app() -> tuple[list[str], list[str]]:
    """F68: the HQ app, when it runs, closed by its exact pid and opened again; counted only on a new pid."""
    done, todo = [], []
    if os.environ.get("HQ_UPDATE_ROUTINE") == "0" and not os.environ.get("HQ_APP_BUNDLE"):
        return done, todo  # a test on a Mac: never the real app of the computer running it
    olds = app_pids()
    if not olds:
        return done, todo
    stuck = [p for p, _ in olds if not stop_pid(p)]
    if stuck:
        return done, [f"the HQ app (pid {stuck[0]}) wouldn't close: close it and open it again"]
    if not open_app(olds[0][1]):
        return done, ["the HQ app was closed but didn't open again: open it by hand"]
    end, new = time.time() + 30, []
    while time.time() < end and not new:
        new = [p for p, _ in app_pids() if p not in {o for o, _ in olds}]
        time.sleep(0.5)
    if new:
        done.append(f"restarted the HQ app (pid {olds[0][0]} → {new[0]}): its strip, status page and call page are the new version")
    else:
        todo.append("the HQ app was closed but didn't open again: open it by hand")
    return done, todo


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
            "app": app_pids(),
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
    if not was_running.get("guard"):  # F104: the guard stops a job by exact pid and nothing else, and it did that already
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
    # F68: the app itself (a new build, a changed strip, the pages) is opened again at the end, restart_app.

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
    # F68: the HQ app last, so it opens on the new call line and status page; never the computer.
    d, t = restart_app()
    return done + d, todo + t


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
                 f"`git stash apply {b}`; if something clashes with the new version, move it into local/ instead. "
                 "What they built on top of HQ (a connector, a routine, their own kind of text) belongs in an extension "
                 "in the workspace's HQ/extensions, which updates never touch: EXTENSIONS.md says how to move it there (H235).")
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
    w.append("- Run the detailed flows that fit this computer (`python3 app/happy_flows.py --help`), and one short call.")
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
        if os.path.exists(BACK_FILE):  # F104: on a version again by its own update: nothing to go forward to, and the data changes run again
            os.remove(BACK_FILE)
        if made == tag:  # its own version wasn't on the public repo: everything that differed was set right
            changed = sorted(set(changed) | set(saved.get("changes", {}).get("files", [])))
        say("updating", "Restarting what changed")
        done, todo = restart_new(changed, was)
        done = ended + done
        note = notes(old, tag, saved, changed, done, todo)
        # H235: the local check against their own extensions, with the new version's own code, right away (the routine
        # also runs it within a minute, for an update made by an older version of this file).
        say("updating", "Checking your own extensions against the new version", notes=note, finished=time.time(),
            changed=changed[:500])
        try:
            subprocess.run([sys.executable, os.path.join(HQ, "app", "extensions.py"), "after-update"], cwd=HQ,
                           capture_output=True, text=True, timeout=120,
                           env={**os.environ, "HQ_EXTENSIONS_RUN": json.dumps({**read_json(RUN_FILE), "state": "done", "to": vname(tag), "from": old})})
        except Exception as e:
            log(f"update: the extensions check: {e!r}")
        bits = [f"Updated to {vname(tag)}."]
        if saved:
            bits.append("Your own changes are saved on a backup branch.")
        if platform() != "darwin":
            bits.append("Your Claude has instructions to patch things up locally.")
        fin = read_json(RUN_FILE).get("finished") or time.time()
        say("done", "", " ".join(bits), done=done, todo=todo, notes=note, saved=saved, finished=fin)
        check(force=True)
        return 0
    except Exception as e:
        say("failed", "", f"The update didn't go through: {str(e)[:200]}. HQ stays as it was; nothing of yours was lost.")
        return 1


def previous() -> str | None:
    """F104: one version back: the newest version tag under where HQ stands; on the work line past a version, that version. On a friend's
    copy her own commits past a tag count as standing on that tag: one version back is the one below it, or she'd stay on the same version.
    Commits of dev's past it aren't hers: that's the work line, on her copy too. The small list: a copy that came as a download got only
    the tags its update needed, so with none found here the version tags are fetched from GitHub first and it looks again."""
    if not has_git():
        return None
    tag = _previous()
    if tag is None:
        fetch_tags()
        tag = _previous()
    return tag


def _previous() -> str | None:
    at = set(git("tag", "--points-at", "HEAD", timeout=10).stdout.split())
    older = [t for t in git("tag", "--merged", "HEAD", timeout=10).stdout.split() if vtuple(t) and t not in at]
    if not older:
        return None
    newest = max(older, key=vtuple)
    if at or not hqpaths.is_friend() or off_release():
        return newest
    below = [t for t in older if vtuple(t) < vtuple(newest)]
    return max(below, key=vtuple) if below else None


def has_forward(tag: str) -> bool:
    """F104: whether that version's own update.py knows `forward`. One that doesn't is a way back with no way out again, and no team wait."""
    want = f"refs/tags/{tag}:routine/update.py"
    try:
        r = git("show", want, timeout=20)
        if r.returncode:
            git("fetch", "--no-tags", "--quiet", UPSTREAM, f"+refs/tags/{tag}:refs/tags/{tag}", timeout=120)
            r = git("show", want, timeout=20)
    except subprocess.SubprocessError:
        return False
    return not r.returncode and bool(re.search(r"^def forward\(", r.stdout, re.M))


def way_forward(tag: str) -> str | None:
    """F112 (C52): how HQ gets forward again from that version: "own" (its own `forward`); "update bar" for one the release after it wrote down
    (routine/way-back.json), the way it came forward the first time; None: there's no way, so no going back to it."""
    if has_forward(tag):
        return "own"
    return "update bar" if tag in read_json(WAY_BACK) else None


def no_forward_words(tag: str) -> str:
    return f"HQ can't go back to {vname(tag)}: that version has no way forward again, so it would be stuck there. Nothing moved."


def gone_back() -> dict:
    """F104: {"to", "from", "branch", "at"} while this HQ stands on an older version it went back to. F112: an old version knows nothing of this
    file, so once its own update has brought HQ forward the file is simply old."""
    d = read_json(BACK_FILE)
    if d.get("no_forward") and d.get("to") != file_version():
        try:
            os.remove(BACK_FILE)
        except OSError:
            pass
        return {}
    return d


def _peer(cmd: list[str]) -> bool:
    """F104: the other computer is told through the forward. True when it took it, or there's no other computer."""
    import role
    return role.tell_other("update", cmd) in ("told", "alone")


def tell_later(cmd: list[str]) -> None:
    write_json(OTHER_FILE, {"cmd": cmd, "at": time.time()})


def tell_now(cmd: list[str]) -> bool:
    """F104: told, the pending line goes. Not told, whatever the reason, it stays, and the routine tries every minute (other_minute)."""
    try:
        told = _peer(cmd)
    except Exception as e:
        log(f"back: the other computer: {e!r}")
        told = False
    if told:
        try:
            os.remove(OTHER_FILE)
        except OSError:
            pass
    return told


def other_minute() -> str | None:
    """F104: from the routine's minute: the other computer was off when this one went back; try again."""
    d = read_json(OTHER_FILE)
    if not d.get("cmd"):
        return None
    if _peer(d["cmd"]):
        os.remove(OTHER_FILE)
        return f"told the other computer: {' '.join(d['cmd'])}"
    return None


def _spawn(*args: str) -> None:
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    subprocess.Popen(scoped([sys.executable, os.path.abspath(__file__), *args], "update"), cwd=HQ, stdin=subprocess.DEVNULL,
                     stdout=open(LOG, "a"), stderr=subprocess.STDOUT, start_new_session=True)


def back(tag: str | None = None, tell: bool = True, first: bool = False) -> dict:
    """F104: one version back, here and on the other computer, in one step. The work happens in the background (it ends what runs,
    so also the shell a call started this from). Returns what was started. The main goes first, whichever computer it's started on:
    only the main's undo can fail, and the other computer hears only once it held. `first`: the backup asked for this."""
    if not has_git():  # the small list: a download has versions before it, but no git to go back with
        return {"ok": False, "said": "This HQ came as a download, without its git history, so it can't go back a version yet. "
                                     "Its first update makes it a git copy; from then on going back works. Nothing moved."}
    tag = tag or previous()
    if not tag or not vtuple(tag):
        return {"ok": False, "said": "There's no version before this one."}
    if not way_forward(tag):
        return {"ok": False, "said": no_forward_words(tag)}
    import role
    if tell and not first and role.is_backup():
        if role.tell_other("update", ["back-first", tag]) == "told":
            return {"ok": True, "said": f"Going back to {vname(tag)}: the main computer goes first, then this one.", "to": vname(tag)}
        return {"ok": False, "said": "The main computer doesn't answer, and it has to go first. Nothing moved."}
    write_json(RUN_FILE, {"state": "waiting", "step": "Going back", "message": "", "at": time.time(), "from": local_version().get("version"), "to": vname(tag)})
    if os.environ.get("HQ_UPDATE_WAIT"):  # a test: in the foreground
        code = back_run(tag, tell)
        return {"ok": code == 0, "said": read_json(RUN_FILE).get("message") or "", "to": vname(tag)}
    _spawn("back-run", tag, "tell" if tell else "quiet")
    return {"ok": True, "said": f"Going back to {vname(tag)}, on this computer and the other one.", "to": vname(tag)}


def own_work(saved: dict, head: str, old: str | None) -> list[str]:
    """F112: the backup branches with her own work on them, for the words after going back: what she hadn't committed, her own commits when
    there are any past the versions (a version's own commits saved on the way back aren't hers), and what her update onto the version she's
    leaving saved before it moved."""
    kept = [saved["changes"]["branch"]] if saved.get("changes") else []
    mine = git("rev-list", "--count", head, "--not", "--tags=v*", timeout=10).stdout.strip() if head else ""
    if saved.get("commits") and mine.isdigit() and int(mine) > 0:
        kept.append(saved["commits"]["branch"])
    if old:
        kept += [b for b in git("for-each-ref", "--sort=-committerdate", "--format=%(refname:short)", "refs/heads/hq-backup/", timeout=10).stdout.split()
                 if f"-before-v{old}-" in b and b not in kept]
    return kept


def back_run(tag: str, tell: bool, guard: bool = False) -> int:
    """`guard`: the guard on the release, not a person: it stops a job by exact pid and nothing else (the job for good: held, it would carry
    on by itself and do the same again), keeps no way forward (back.json is what `forward` goes by), and writes down what happened. Only on
    a friend's copy, however this was started: it never moves the maker's."""
    why = hqpaths.not_friend() if guard else ""
    if why:
        log(f"release guard: left alone: {why}")
        print(f"The guard leaves this HQ alone: {why}.")
        return 1
    way = "guard" if guard else way_forward(tag)  # the guard goes where she stood, it isn't a going back she can undo
    if not way:
        say("failed", "", no_forward_words(tag))
        return 1
    old_way = way == "update bar"
    say("updating", "Going back", **{"to": vname(tag)})
    told, undone, saved, moved = None, [], {}, False
    try:
        import datachange
        import role
        old = local_version().get("version")
        was = {"call": listening(hqpaths.call_port()), "status": listening(hqpaths.status_port()),
               "call_pid": pid_on(hqpaths.call_port(), CALL_MARK)}
        say("updating", "Ending what runs: the job" if guard else "Ending what runs: the call, the job, the mail check")
        ended = stop_job() if guard else force_out(stop_call=True)
        if git("rev-parse", "-q", "--verify", f"refs/tags/{tag}", timeout=10).returncode:
            git("fetch", "--no-tags", "--quiet", UPSTREAM, f"+refs/tags/{tag}:refs/tags/{tag}", timeout=120, check=True)
        say("updating", "Saving anything you changed")
        saved = backup(tag)
        before = git("rev-parse", "HEAD", timeout=10).stdout.strip()
        branch = git("symbolic-ref", "-q", "--short", "HEAD", timeout=10).stdout.strip()
        if not role.is_backup():  # the workspace is the main's: the backup gets it back by the sync
            say("updating", "Undoing what the newer version changed in your data")
            undone = datachange.undo(datachange.between(tag, "HEAD"))
        if old_way and not hqpaths.is_friend():  # F112: that version's routine doesn't know the team has to wait: the switch says so instead
            subprocess.run([sys.executable, os.path.join(HQ, "routine", "jobs.py"), "off"], capture_output=True, text=True, timeout=60)
        say("updating", f"Moving HQ to {vname(tag)}")
        git("checkout", "--quiet", "--detach", tag, timeout=60, check=True)
        moved = True
        changed = [f for f in git("diff", "--name-only", before, "HEAD", timeout=30).stdout.splitlines() if f]
        prior = gone_back()
        if not guard:
            # the small list: what she hadn't committed where she went back from, so forward brings it back there
            changes = prior.get("changes") or (saved.get("changes") or {}).get("branch")
            write_json(BACK_FILE, {"to": vname(tag), "from": prior.get("from") or old, "branch": prior.get("branch") or branch,
                                   "head": prior.get("head") or before, "at": time.time(), **({"no_forward": True} if old_way else {}),
                                   **({"changes": changes} if changes else {})})
        if tell:  # only now: what failed above left this computer where it was, and the other one with it
            tell_later(["back-here", tag])  # kept first: whatever happens to this run, the routine's minute tells it until it's told
            told = tell_now(["back-here", tag])
        say("updating", "Restarting what changed")
        done, todo = guard_restart(was) if guard else restart_new(changed, was)
        msg = f"Back on {vname(tag)}." + (f" Undone in your data: {', '.join(undone)}." if undone else "") + (
            " The other computer hears it as soon as it answers." if told is False else "")
        kept = own_work(saved, before, old) if not guard else []
        if kept:
            msg += f" Your own work is kept, nothing of it is lost: on {', '.join(kept)} (git checkout one of them to see it)."
        if old_way and hqpaths.is_friend():
            msg += f" {vname(tag)} has no Forward button of its own: the update bar brings you back to {old}, and what was undone runs again then."
        elif old_way:
            msg += f" The team is off, because {vname(tag)} doesn't wait by itself. It has no forward of its own: git checkout {branch or before}, then the team on."
        if guard:
            msg = guard_done(tag, old, before, saved, undone, ended)
            st = read_json(GUARD_FILE)
            st.pop("held", None)  # back on a release: nothing is held, and the same head coming back is sent back at once, not after GUARD_RETRY
            write_json(GUARD_FILE, st)
        say("done", "", msg, done=ended + done, todo=todo, saved=saved, undone=undone, finished=time.time())
        check(force=True)
        return 0
    except Exception as e:
        say("failed", "", _not_through(e, tag, moved, undone, saved, guard))
        if guard:
            guard_failed(e)
        return 1


def _not_through(e: Exception, tag: str, moved: bool, undone: list[str], saved: dict, guard: bool) -> str:
    """What's true after a going back that stopped halfway: which of the code, the data and the user's changes moved."""
    why = str(e)[:200].rstrip(". ")
    if moved:
        return f"Back on {vname(tag)}, but what came after it didn't finish: {why}."
    bits = [f"Going back didn't go through: {why}."]
    if undone:
        bits.append(f"HQ's code stays where it was, but in your data this is already undone: {', '.join(undone)}.")
        bits.append("It stays undone until HQ stands on a released version." if guard else "The routine runs it again within a minute.")
    else:
        bits.append("HQ stays where it was.")
    keep = [x["branch"] for x in (saved.get("changes"), saved.get("commits")) if x]
    if keep:
        bits.append(f"Your own changes are saved on {' and '.join(keep)}.")
    return " ".join(bits)


def forward(tell: bool = True) -> dict:
    """F104: the way forward again: this HQ back where it went back from, and the other computer too. The routine runs the data
    changes again by itself. Never onto unreleased work on a copy that isn't the maker's: the guard would only send it back again."""
    d = gone_back()
    if not d:
        return {"ok": False, "said": "This HQ hasn't gone back."}
    if hqpaths.is_friend() and off_release(d.get("branch") or d.get("head") or "HEAD"):
        return {"ok": False, "said": "Forward from here is work that isn't released yet, and this HQ stays on released versions. It stays where it is."}
    if tell and not _peer(["forward-here"]):
        tell_later(["forward-here"])
    if d.get("branch"):
        git("checkout", "--quiet", d["branch"], timeout=60, check=True)
    else:
        git("checkout", "--quiet", "--detach", d.get("head") or "HEAD", timeout=60, check=True)
    kept = _changes_back(d.get("changes") or "")
    os.remove(BACK_FILE)
    if not os.environ.get("HQ_UPDATE_WAIT"):
        _spawn("restart-all")
    return {"ok": True, "said": f"Forward again, on {git('describe', '--tags', '--always', timeout=10).stdout.strip()}.{kept}"}


def _changes_back(branch: str) -> str:
    """The small list: forward puts back what going back saved of hers that wasn't committed, only where it came from and onto a clean
    folder, so it lands as it was. Otherwise it stays on its branch and the words say so. The branch is kept either way."""
    if not branch or git("rev-parse", "-q", "--verify", f"refs/heads/{branch}", timeout=10).returncode:
        return ""
    base = git("rev-parse", f"{branch}^1", timeout=10).stdout.strip()
    if base == git("rev-parse", "HEAD", timeout=10).stdout.strip() and not changed_outside_local():
        r = git(*IDENTITY, "stash", "apply", branch, timeout=60)
        if not r.returncode:
            return f" Your changes that weren't committed are back (still saved on {branch} too)."
        git("reset", "-q", "--hard", "HEAD", timeout=60)  # the folder was clean a moment ago: nothing of hers is lost, it's on the branch
        log(f"forward: {branch} didn't apply: {(r.stderr or r.stdout).strip()[-300:]}")
    return f" Your changes that weren't committed are saved on {branch}: git stash apply {branch} brings them back."


# ---- F104: the guard on the release -----------------------------------------------------------------------------
# A job on a friend's copy is an honest model doing something by habit, not an attacker. The job hook stops the plain ways by their words;
# what it can't see, this sees by what's checked out, every minute, before anything else in the routine runs. What counts is "on GitHub's
# dev and not in a release", never "the head isn't a tag": a friend's own commits are hers. Files of dev's in the folder with the head
# where it was (a `git show` into a file, a raw download) aren't this guard's: nothing in the head says so.

def version_tags() -> list[str]:
    return [t for t in git("tag", "-l", timeout=20).stdout.split() if vtuple(t)]


def past_release(head: str = "HEAD") -> tuple[list[str], list[str]]:
    """(the commits under `head` that no version tag reaches, the version tags). Local, no network."""
    tags = version_tags()
    if not tags:
        return [], []
    return git("rev-list", head, *[f"^{t}" for t in tags], timeout=30).stdout.split(), tags


def _repo_of(url: str) -> str:
    """owner/name of a repo's address, whichever way it's written, or a folder's last two parts: the same for ssh, https and with .git."""
    tail = re.sub(r"\.git/?$|/$", "", url.strip()).replace(":", "/").split("/")
    return "/".join(tail[-2:]).lower()


def work_line() -> list[str]:
    """The tips of GitHub's work line this copy knows from its own refs: what a remote of HQ's own repo says, what the guard fetched, what
    FETCH_HEAD says of it. Never a local branch called dev: that may be hers, with her own commits on it."""
    want = _repo_of(UPSTREAM)
    remotes = [r for r in git("remote", timeout=10).stdout.split() if _repo_of(git("remote", "get-url", r, timeout=10).stdout) == want]
    refs = [f"refs/remotes/{r}/{b}" for r in remotes for b in WORK_LINE] + ["refs/hq/work-line/"]
    tips = set(git("for-each-ref", "--format=%(objectname)", *refs, timeout=20).stdout.split())
    try:
        with open(os.path.join(HQ, git("rev-parse", "--git-path", "FETCH_HEAD", timeout=10).stdout.strip())) as f:  # join: an absolute path stays as it is
            for ln in f:
                m = re.match(r"([0-9a-f]{40})\t[^\t]*\tbranch '(?:dev|nightly)' of (.+)$", ln.rstrip("\n"))
                if m and _repo_of(m[2]) == want and not git("cat-file", "-e", m[1], timeout=10).returncode:
                    tips.add(m[1])
    except OSError:
        pass
    return sorted(tips)


def look_at_github() -> bool:
    """GitHub's dev and nightly into refs/hq/work-line/, a place no checkout goes by itself. False when it can't be reached: what the
    local refs know then stands, and a commit they don't know isn't called dev's on a guess."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "PATH": os.environ.get("PATH", "") + ":" + PATH}
    try:
        r = subprocess.run(["git", "ls-remote", "--heads", UPSTREAM, *WORK_LINE], capture_output=True, text=True, timeout=20, env=env)
        if r.returncode:
            return False
        names = [ln.split("refs/heads/", 1)[1] for ln in r.stdout.splitlines() if "refs/heads/" in ln]
        names = [n for n in names if n in WORK_LINE]
        if names:
            return not git("fetch", "--no-tags", "--quiet", "--no-write-fetch-head", UPSTREAM,
                           *[f"+refs/heads/{n}:refs/hq/work-line/{n}" for n in names], timeout=60).returncode
        return True
    except Exception:
        return False


def _log(revs: list[str], *how: str) -> bytes:
    env = {**os.environ, "PATH": os.environ.get("PATH", "") + ":" + PATH}
    return subprocess.run(["git", "-C", HQ, "log", "--no-walk", *how, "--stdin"], input="\n".join(revs).encode(), capture_output=True, timeout=60, env=env).stdout


def _patches(revs: list[str]) -> dict[str, str]:
    """{patch id: commit}: the same change has the same id, whatever commit it's in."""
    r = subprocess.run(["git", "-C", HQ, "patch-id", "--stable"], input=_log(revs, "-p", "--no-merges"), capture_output=True, timeout=60,
                       env={**os.environ, "PATH": os.environ.get("PATH", "") + ":" + PATH})
    return {ln.split()[0]: ln.split()[1] for ln in r.stdout.decode().splitlines() if len(ln.split()) == 2}


def _trees(revs: list[str]) -> dict[str, str]:
    """{tree: commit}: the same files have the same tree."""
    return dict(ln.split() for ln in _log(revs, "--format=%T %H").decode().splitlines() if len(ln.split()) == 2)


def _not_own(revs: list[str]) -> list[str]:
    """The commits that weren't written by this copy's own git identity (its name or its address): `git am` and a cherry-pick keep the author
    of dev's commit. Her own work is hers, also when the team took her patch as it is and dev now holds the same change."""
    r = git("var", "GIT_AUTHOR_IDENT", timeout=10)
    m = re.match(r"(.*) <(.*)> \d+ [-+]\d+$", r.stdout.strip())
    who = {x for x in (m[1], m[2]) if x} if m and not r.returncode else set()
    rows = [ln.split("\0") for ln in _log(revs, "--format=%H%x00%an%x00%ae").decode(errors="replace").split("\n") if ln]
    return [c for c, *author in rows if not who & set(author)]


def unreleased(mine: list[str], tags: list[str], tips: list[str]) -> list[str]:
    """Of the commits past a release, the ones that are GitHub's unreleased work: the very commit, the same change made again (`git am`, a
    cherry-pick), or the same files as one of them (a squash). Not a commit that repeats something that was released: that's hers. And a
    commit of this copy's own identity counts only as the very commit: the same change or the same files in her own commit are hers."""
    if not mine or not tips:
        return []
    theirs = git("rev-list", *tips, *[f"^{t}" for t in tags], timeout=30).stdout.split()
    if not theirs:
        return []
    same = set(theirs)
    hit = [c for c in mine if c in same]
    if hit:
        return hit
    rest = _not_own(mine)
    if not rest:
        return []
    ids = _patches(theirs)
    hit = [c for i, c in _patches(rest).items() if i in ids]
    of_theirs = _trees(theirs)
    of_tags = set(git("rev-parse", *[f"{t}^{{tree}}" for t in tags], timeout=20).stdout.split())
    return hit + [c for t, c in _trees(rest).items() if t in of_theirs and t not in of_tags and c not in hit]


def off_release(head: str = "HEAD") -> list[str]:
    """The unreleased commits under `head`, by what this copy knows now (no network)."""
    mine, tags = past_release(head)
    return unreleased(mine, tags, work_line())


def _subject(sha: str) -> str:
    return git("log", "-1", "--format=%s", sha, timeout=10).stdout.strip()[:120]


def fetch_tags() -> None:
    """Every version tag GitHub has, when it's reached; offline nothing changes, and a tag that's here is never moved."""
    try:
        git("fetch", "--no-tags", "--quiet", "--no-write-fetch-head", UPSTREAM, "refs/tags/v*:refs/tags/v*", timeout=60)
    except subprocess.SubprocessError:
        pass


def _stood_on(tags: list[str]) -> list[str]:
    """The version tags whose very commit the head has stood on, by its reflog: what the head's history alone can't say."""
    if not tags:
        return []
    seen = set(git("log", "-g", "--format=%H", "HEAD", timeout=20).stdout.split())
    return [t for t, c in zip(tags, git("rev-parse", *[f"{t}^{{commit}}" for t in tags], timeout=20).stdout.split()) if c in seen]


def newest_release() -> str | None:
    """Where the guard goes: the version this HQ went back to, if it did that on purpose; else the newest release it really stood on: a newer one
    that was only fetched, or that dev's history holds (every real release is on dev's line), isn't hers, an update brings that with what it
    does around it, and it never goes below where it stood either. With none known, the newest tag in the head's own history, tags at the head
    included; only then the newest one it has. Data only ever moves forward from there, by the routine's own minute. older_than_stood says
    when that won't do."""
    tags = version_tags()
    to = "v" + str(gone_back().get("to") or "")
    if to in tags:
        return to
    own = _stood_on(tags) or [t for t in git("tag", "--merged", "HEAD", timeout=20).stdout.split() if vtuple(t)] or tags
    return max(own, key=vtuple) if own else None


def older_than_stood(tag: str | None) -> str:
    """Why `tag` won't do: it's older than the version this copy stands on (a tag it lost, and GitHub out of reach), or it can't tell what it
    stands on. "" when it's fine. A version she went back to on purpose is hers, so then only the newest tag there is counts. And a release she
    really stood on is fine below the head's version when that version has a tag of its own she never stood on: dev took her past it, she
    wasn't there. Without that tag it can't be told from one she lost. Going to an older one would undo the data to a shape it never had on a guess."""
    tags = version_tags()
    if not tags or not tag:
        return ""
    v = local_version().get("version") or ""
    top = max(tags, key=vtuple) if tag == "v" + str(gone_back().get("to") or "") else tag
    if not vtuple("v" + v):
        return "it can't tell which version it stands on, and it doesn't go to one on a guess"
    if vtuple("v" + v) > vtuple(top) and not (tag in _stood_on(tags) and any(vtuple(t) == vtuple("v" + v) for t in tags)):
        return f"it stands on {v} and the newest release it can find is {vname(top)}, and it never goes to an older version than it stood on"
    return ""


def release_minute(log=None) -> str | None:
    """F104: the routine's first thing every minute. None: nothing's the matter, carry on. Words: this copy holds unreleased work (or is
    going back from it): start nothing on top of it this minute. Never on the maker's copy, and never on a guess: what can't be read or
    can't be told counts as nothing found. The look at GitHub only happens past a release, for a head it hasn't seen, or once an hour."""
    if not has_git():
        return None
    why = hqpaths.not_friend()
    if why:
        return _guard_doubt(why, log)
    st, now = read_json(GUARD_FILE), time.time()
    st.pop("doubt", None)
    mine, tags = past_release()
    if not mine:
        return _guard_clear(st)
    head = git("rev-parse", "HEAD", timeout=10).stdout.strip()
    if head and (st.get("head") != head or now >= st.get("next", 0)):
        st["next"] = now + (GUARD_LOOK if look_at_github() else GUARD_OFFLINE)
    tips = work_line()
    if st.get("head") == head and st.get("tips") == tips and not st.get("held"):
        write_json(GUARD_FILE, st)
        return None
    st["head"] = head
    hit = unreleased(mine, tags, tips)
    if hit and _guard_due(st, now):  # before it chooses where to go: a tag it lost may be all that's the matter
        fetch_tags()
        mine, tags = past_release()
        hit = unreleased(mine, tags, tips)
    if not hit:  # only a head found fine is kept as looked at: one sent back is judged again if it comes back, also with GitHub's dev the same
        st["tips"] = tips
        st.pop("held", None)
        write_json(GUARD_FILE, st)
        return _guard_clear(st)
    st.pop("tips", None)
    return _guard_hold(st, hit, now, log)


def _guard_doubt(why: str, say_it) -> None:
    """Not surely a friend's: the guard does nothing, on anything. Past a release it says so, once for each reason, in the log and in its file;
    on the maker's own copy there's nothing to say."""
    if why == hqpaths.THE_MAKER or not past_release()[0]:
        return None
    st = read_json(GUARD_FILE)
    if st.get("doubt") != why:
        st["doubt"] = why
        write_json(GUARD_FILE, st)
        (say_it or log)(f"release guard: this HQ stands past a release, and it's left alone: {why}")
    return None


def _guard_clear(st: dict) -> None:
    """Nothing held: the incident closes, and parts the guard couldn't restart during a call get their turn."""
    if st.get("held"):
        st.pop("held")
        write_json(GUARD_FILE, st)
    try:
        import incidents
        if incidents.is_down(GUARD_KEY):
            incidents.up(GUARD_KEY, what="Nothing is held any more: the parts it held may run again")
    except Exception:
        pass
    if st.get("restart") and calls_on() == 0:
        st.pop("restart")
        write_json(GUARD_FILE, st)
        if os.environ.get("HQ_UPDATE_RESTART") != "0":
            _spawn("restart-all", "guard")
    return None


def _guard_due(st: dict, now: float) -> bool:
    """A going back can start now: none is under way, and the last try is long enough ago."""
    run = read_json(RUN_FILE)
    return not (run.get("state") == "updating" and alive(run.get("pid"))) and now >= (st.get("held") or {}).get("again", 0)


def _guard_hold(st: dict, hit: list[str], now: float, log) -> str:
    """Unreleased work under the head: held from here on, and going back, once now and again every GUARD_RETRY if that didn't go through.
    With nothing to go back on that isn't older than where it stood, it stays held and says so."""
    held = st.get("held") or {"since": now, "commits": len(hit), "first": _subject(hit[-1]), "item": _job_item()}
    tag = newest_release()
    why = older_than_stood(tag)
    words = f"HQ stands on work that isn't released ({len(hit)} change{'s' if len(hit) != 1 else ''}): nothing starts until it's back on {vname(tag) if tag and not why else 'a released version'}"
    st["held"] = held
    if not _guard_due(st, now):
        write_json(GUARD_FILE, st)
        return words
    held.update(again=now + GUARD_RETRY, tries=held.get("tries", 0) + 1, to=tag)
    write_json(GUARD_FILE, st)
    import incidents
    incidents.down(GUARD_KEY, words + f". The first: {held['first']}", at=held["since"], item=held.get("item"))
    if why or not tag:  # nothing to go back on: it stays held, and the incident says so
        guard_failed(why or "this HQ has no released version it could go back on")
        return words
    if log:
        log(f"release guard: {len(hit)} unreleased change(s) under the head, going back on {tag}")
    if os.environ.get("HQ_UPDATE_WAIT"):  # a test: in the foreground
        back_run(tag, False, guard=True)
    else:
        _spawn("back-run", tag, "guard")
    return words


def _job_item() -> str | None:
    """The id of the work the running job holds, so the incident is a step of its record (F103)."""
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "jobs.py"), "next"], capture_output=True, text=True, timeout=30)
        running = json.loads(r.stdout).get("running") or []
        return (running[0].get("item") or {}).get("id") if running else None
    except (OSError, ValueError, subprocess.SubprocessError, AttributeError):
        return None


def stop_job() -> list[str]:
    """F104: a job that runs, stopped by exact pid, for good, and nothing else."""
    n, pid = running_job(), window_pid("job.json", "job.pid")
    if pid:
        end_tree(pid)
    if n:
        subprocess.run([sys.executable, os.path.join(HERE, "jobs.py"), "mark", str(n), "stopped " + time.strftime("%H:%M")], capture_output=True, text=True)
    for f in ("job.json", "job.pid"):
        try:
            os.remove(os.path.join(RUN_DIR, f))
        except OSError:
            pass
    return [f"job {n}" + (f" (pid {pid})" if pid else "")] if n or pid else []


def guard_restart(was: dict) -> tuple[list[str], list[str]]:
    """What runs goes back on the released code as after `back`, only never through a call: then it waits until the call has ended."""
    if calls_on() == 0:
        return restart_new(["app/bot.py", "status/server.mjs"], {**was, "guard": True})
    st = read_json(GUARD_FILE)
    st["restart"] = True
    write_json(GUARD_FILE, st)
    return [], ["a call is on: what runs goes on the released code once it has ended"]


def guard_done(tag: str, old: str, head: str, saved: dict, undone: list[str], ended: list[str]) -> str:
    """Said and written down: the incident's line, a note beside the update notes for the Claude that runs this HQ, and a text."""
    held = read_json(GUARD_FILE).get("held") or {}
    kept = [x["branch"] for x in (saved.get("changes"), saved.get("commits")) if x]
    said = (f"HQ had moved onto work that isn't released yet ({held.get('commits', 'some')} change{'' if held.get('commits') == 1 else 's'}, the first: {held.get('first', '?')}). "
            f"It's back on {vname(tag)}." + (f" Stopped: {'; '.join(ended)}; it doesn't carry on by itself." if ended else "")
            + (f" Undone in your data: {', '.join(undone)}." if undone else "")
            + (f" Anything of your own is saved on {' and '.join(kept)}." if kept else ""))
    os.makedirs(NOTES, exist_ok=True)
    path = os.path.join(NOTES, f"went-back-{time.strftime('%Y%m%d-%H%M%S')}.md")
    with open(path, "w") as f:
        f.write("\n".join([f"# HQ went back on {vname(tag)} by itself", "",
                           f"{time.strftime('%d %B %Y at %H:%M')}. For the Claude that runs this HQ: tell the user, in a sentence or two, then move this note into updates/done/.", "",
                           said, "", f"It stood on {head} (from {old or '?'}), past every version, with work from GitHub's work line under it. A friend's HQ only stands on released versions,",
                           "so the routine put it back; nothing of the work line was kept running. A job on this copy doesn't take the work line, by any command.", "",
                           *([f"- Changes to HQ's own files, on `{saved['changes']['branch']}`, never sent anywhere: `git stash apply {saved['changes']['branch']}` brings them back."] if saved.get("changes") else []),
                           *([f"- Commits, on `{saved['commits']['branch']}`, never sent anywhere. Those of the work line are on it too: take over only the user's own (`git log {tag}..{saved['commits']['branch']}`)."] if saved.get("commits") else []),
                           ""]))
    try:
        import incidents
        incidents.fix(GUARD_KEY, said)
    except Exception:
        pass
    log(f"release guard: {said}")
    _guard_text(said)
    return said


def guard_failed(why) -> None:
    """It stays held and the guard tries again. The incident stays open, and the owner hears it now, once: while it's held the routine's
    minute ends here, before the direct line's own look at what's down."""
    words = f"HQ stands on work that isn't released and going back didn't go through: {str(why)[:200]}. Nothing starts until it's back; it's tried again"
    try:
        import incidents
        incidents.fix(GUARD_KEY, words)
    except Exception:
        pass
    log(f"release guard: {words}")
    st = read_json(GUARD_FILE)
    if st.get("held") and not st["held"].get("texted"):
        st["held"]["texted"] = True
        write_json(GUARD_FILE, st)
        _guard_text(words)


def _guard_text(said: str) -> None:
    """The owner's texts, in the background: composing one can take a minute, and nothing here waits for it."""
    py = os.path.join(HQ, ".venv", "bin", "python")
    try:
        subprocess.Popen([py if os.path.exists(py) else sys.executable, os.path.join(HQ, "app", "direct_line.py"), "text", "off-release", said], cwd=HQ, stdin=subprocess.DEVNULL,
                         stdout=open(LOG, "a"), stderr=subprocess.STDOUT, start_new_session=True)
    except Exception as e:
        log(f"release guard: the text: {e!r}")


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "status"
    if cmd == "back":  # F104: python3 routine/update.py back [--tag vX.Y.Z]
        tag = argv[argv.index("--tag") + 1] if "--tag" in argv else None
        print(json.dumps(back(tag)))
        return 0
    if cmd == "back-here" and len(argv) == 2:  # F104: the other computer said so, through the forward
        print(json.dumps(back(argv[1], tell=False)))
        return 0
    if cmd == "back-first" and len(argv) == 2:  # F104: started on the backup: this one goes first and tells it
        print(json.dumps(back(argv[1], first=True)))
        return 0
    if cmd == "back-run" and len(argv) >= 2:
        return back_run(argv[1], argv[2:] not in (["quiet"], ["guard"]), guard=argv[2:] == ["guard"])
    if cmd in ("forward", "forward-here"):
        print(json.dumps(forward(tell=cmd == "forward")))
        return 0
    if cmd == "restart-all":
        was = {"call": listening(hqpaths.call_port()), "status": listening(hqpaths.status_port()), "call_pid": pid_on(hqpaths.call_port(), CALL_MARK)}
        restart_new(["app/bot.py", "status/server.mjs"], {**was, "guard": argv[1:] == ["guard"]})
        return 0
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
    elif cmd == "here":  # H340: this code's version state, for a throwaway copy without git (routine/realcase.py)
        print(json.dumps(local_version()))
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
    elif cmd == "clash" and len(argv) == 2 and argv[1] in ("chat", "team", "ok"):  # H235: the bar's buttons
        out = _extensions().settle(argv[1])
        print(json.dumps({**status(background=False), "said": out.get("said"), "settled": out.get("ok"),
                          "open": out.get("open")}))
    elif cmd == "version":
        print(json.dumps(local_version()))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
