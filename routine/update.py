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
    update.py start             starts the update in the background (it waits for a call or a job to end)
    update.py run               the update itself (what start runs)

The version is the newest version tag HQ's history contains (git describe, v0.2), else the VERSION file.
A newer version is a tag vX.Y or vX.Y.Z on the public repo with a higher number. The update:
  1. waits while a call is on (the call server's /api/busy) or a job runs (the queue), and says so;
  2. saves anything changed in HQ outside local/ (and the user's own commits) on a backup branch,
     hq-backup/..., never sent anywhere (git stash apply <branch> brings the changes back);
  3. fetches only that tag from the public repo and moves HQ to it; workspace, local/, scratch/ and .status/
     are ignored by the repo, so they are never touched;
  4. restarts what needs it: the call line (when it ran), the status page (when its server changed), the Mac
     app (when it changed and is installed), the watchdog (when it changed); the Python packages when the
     requirements changed; on another computer the user's own parts in local/ do that;
  5. leaves a note for the user's Claude in updates/<version>.md: what changed, what was kept, what to check
     and rebuild in local/.
State: .status/update.json (the last check) and .status/update-run.json (the update), for the pages.
Tests: HQ_UPDATE_URL (another repo, e.g. a folder), HQ_PLATFORM (pretend another computer), HQ_CALL_URL,
HQ_UPDATE_RESTART=0 (restart nothing).
"""
from __future__ import annotations

import json
import os
import re
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

def local_version() -> dict:
    """{"tag": "v0.2", "version": "0.2", "ahead": 16}: the newest version tag in HQ's own history, and how many
    changes came after it that aren't in a version yet. Without git: the VERSION file."""
    try:
        r = git("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*", timeout=10)
        tag = r.stdout.strip()
        if r.returncode == 0 and vtuple(tag):
            ahead = git("rev-list", "--count", f"{tag}..HEAD", timeout=10).stdout.strip()
            return {"tag": tag, "version": vname(tag), "ahead": int(ahead or 0)}
    except Exception:
        pass
    try:
        v = open(os.path.join(HQ, "VERSION")).read().strip()
        return {"tag": "v" + v, "version": v, "ahead": 0}
    except OSError:
        return {"tag": "", "version": "", "ahead": 0}


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

def remote_newest(url: str) -> str | None:
    r = subprocess.run(["git", "ls-remote", "--tags", "--refs", url], capture_output=True, text=True, timeout=25,
                       env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "PATH": os.environ.get("PATH", "") + ":" + PATH})
    if r.returncode:
        raise RuntimeError((r.stderr or "").strip().splitlines()[-1] if r.stderr.strip() else "can't reach it")
    tags = [ln.split("refs/tags/", 1)[1] for ln in r.stdout.splitlines() if "refs/tags/" in ln]
    tags = [t for t in tags if vtuple(t)]
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
        newer = bool(newest and here["tag"] and vtuple(here["tag"]) and vtuple(newest) > vtuple(here["tag"]))
        out["available"] = newer
        if newer:
            git("fetch", "--no-tags", "--quiet", UPSTREAM, f"+refs/tags/{newest}:refs/tags/{newest}", timeout=90, check=True)
            out["tag"] = newest
            out["new"] = whats_new(newest, here["version"])
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
    if background and (due or last.get("version") not in (None, here["version"])):
        check_in_background()
    # A check from before an update says nothing about now.
    stale = last.get("version") != here["version"]
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


def job_running() -> bool:
    try:
        text = open(hqpaths.ROADMAP).read()
    except OSError:
        return False
    return bool(re.search(r"^- Job \d+ · (running|stop asked)", text, re.M))


def start() -> dict:
    run = read_json(RUN_FILE)
    if run.get("state") in ("waiting", "updating") and alive(run.get("pid")):
        return status(background=False)
    st = status(background=False)
    if not st["available"]:
        return st
    write_json(RUN_FILE, {"state": "waiting", "step": "Starting the update", "message": "", "at": time.time(),
                          "from": st["version"], "to": vname(st["new_tag"])})
    p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "run"], cwd=HQ, stdin=subprocess.DEVNULL,
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
        git("stash", "push", "--include-untracked", "-m", f"HQ update backup before {target}", timeout=60, check=True)
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


def pid_on(port: int, must: str) -> int | None:
    """The exact pid listening on a port, only when its command line has `must` in it."""
    r = subprocess.run(["/usr/sbin/lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"], capture_output=True, text=True)
    for p in r.stdout.split():
        cmd = subprocess.run(["/bin/ps", "-o", "command=", "-p", p], capture_output=True, text=True).stdout
        if must in cmd:
            return int(p)
    return None


def restart(changed: list[str], was_running: dict) -> tuple[list[str], list[str]]:
    """Restarts what needs it. Returns (what was done, what the user or their Claude still has to do)."""
    done, todo = [], []
    if os.environ.get("HQ_UPDATE_RESTART") == "0":
        return ["nothing restarted (test)"], []
    env = {**os.environ, "PATH": os.environ.get("PATH", "") + ":" + PATH}
    mac = platform() == "darwin"

    def ran(cmd, what, detach=False):
        try:
            if detach:
                subprocess.Popen(cmd, cwd=HQ, env=env, stdin=subprocess.DEVNULL, stdout=open(LOG, "a"),
                                 stderr=subprocess.STDOUT, start_new_session=True)
                ok = True
            else:
                ok = subprocess.run(cmd, cwd=HQ, env=env, capture_output=True, timeout=900).returncode == 0
        except Exception:
            ok = False
        (done if ok else todo).append(what if ok else f"{what}: it didn't work, do it by hand")
        return ok

    if any(f == "app/requirements.txt" for f in changed):
        pip = os.path.join(HQ, ".venv", "bin", "pip")
        if os.path.exists(pip):
            ran([pip, "install", "-q", "-r", os.path.join(HQ, "app", "requirements.txt")], "installed the new Python packages")
        else:
            todo.append("install the new Python packages (app/requirements.txt)")
    # The call line: always restarted when it ran, since it holds the old code in memory.
    if was_running.get("call"):
        own = hqpaths.part_cmd("restart-call-line")
        if own:
            ran(own, "restarted the call line (your own part)")
        elif mac:
            subprocess.run([os.path.join(HQ, "app", "stop.sh")], cwd=HQ, env=env, capture_output=True, timeout=120)
            ran([os.path.join(HQ, "app", "start.sh")], "restarted the call line")
        else:
            todo.append("restart the call line (build local/restart-call-line for next time)")
    if any(f.startswith("routine/") and ("watchdog" in f) for f in changed):
        own = hqpaths.part_cmd("install-watchdog")
        if own:
            ran(own, "installed the new watchdog (your own part)")
        elif mac:
            ran(["/bin/zsh", os.path.join(HQ, "routine", "install-watchdog.sh")], "installed the new watchdog")
        else:
            todo.append("the watchdog changed: rebuild yours in local/ (install-watchdog)")
    if any(f.startswith("routine/routine.applescript") or f.startswith("routine/build-app.sh") for f in changed):
        todo.append("the routine helper changed: rebuild it with routine/build-app.sh (macOS asks for one Allow)"
                    if mac else "the routine helper changed: check your own start at login in local/")
    if any(f.startswith("desktop/") and not f.endswith((".html", ".js", ".css", ".py")) for f in changed):
        app = os.path.expanduser("~/Applications/HQ.app")
        if mac and os.path.isdir(app):
            if ran(["/bin/zsh", os.path.join(HQ, "desktop", "build.sh"), "--install"], "reinstalled the Mac app"):
                todo.append("close the HQ app and open it again, to use the new one")
    # The status page last: the pages watching this update are served by it.
    if was_running.get("status") and any(f.startswith("status/") and f.endswith(".mjs") for f in changed):
        own = hqpaths.part_cmd("restart-status-page")
        if own:
            ran(own, "restarted the status page (your own part)")
        else:
            pid = pid_on(int(os.environ.get("HQ_STATUS_PORT", 4748)), "status/server.mjs") if mac else None
            if pid:
                os.kill(pid, 15)
                time.sleep(1.5)
            ran(["node", os.path.join(HQ, "status", "server.mjs"), "--quiet"], "restarted the status page", detach=True)
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


def run() -> int:
    target = read_json(RUN_FILE).get("to")
    st = status(background=False)
    tag = st.get("new_tag") or (("v" + target) if target else None)
    old = st["version"]
    if not tag or not vtuple(tag):
        say("failed", message="There's no newer version to update to.")
        return 1
    say("waiting", "Getting ready", **{"from": old, "to": vname(tag)})
    # Never during a call (it would drop), nor while a job is changing things.
    while True:
        n = calls_on()
        if n:
            say("waiting", "Waiting for the call to end", "The update starts by itself when the call ends.")
        elif job_running():
            say("waiting", "Waiting for the running job to finish", "The update starts by itself when the job is done.")
        else:
            break
        time.sleep(15)
    try:
        was = {"call": listening(int(os.environ.get("HQ_PORT", 7860))),
               "status": listening(int(os.environ.get("HQ_STATUS_PORT", 4748)))}
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
        say("updating", "Restarting what needs it")
        done, todo = restart(changed, was)
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
    elif cmd == "version":
        print(json.dumps(local_version()))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
