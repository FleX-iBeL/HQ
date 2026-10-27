#!/usr/bin/env python3
"""The two-way sync (H56.4, 12 October 2026): the workspace and Claude's memory of the user, kept the same on
two HQs (a laptop and a server) through Syncthing, both ways, within seconds.

Only with a second HQ. With no sync set up (no sync.json in HQ's own memory) every command here returns at once
and the status page says nothing about it, so an HQ on its own works exactly as before.

What goes over: the whole workspace except git's own folder, video and audio (mp4, mov, mkv, webm, m4a, mp3,
wav and the like) and this computer's own Claude Code settings (.claude/settings.local.json); and, as a second
small folder, Claude's memory of the user (~/.claude/projects/<the workspace's path>/memory). Course material
that never goes in a repo (PDFs, transcripts) goes over this way, computer to computer, never through GitHub.

Nothing is ever overwritten: when both sides change the same file at once, Syncthing keeps both, the other one
as `<name>.sync-conflict-<date>-<time>-<device>.<ext>`. Every minute the routine looks for those (`tick`): the
status page's Two-way sync line and the incidents say so, and on the main one a small job is queued that merges
both versions into the file without dropping anything, then removes the copy. Only the main one commits (H56.3):
what came over from the other side is committed by the main one, through the shared lock (gitlock.py), named
file by file, only files git doesn't ignore. When an HQ becomes the main one (`align`, from tick.became_main),
it first lines its git up with GitHub, keeping the files as they are.

H152 (16 October 2026, after the laptop came back from a crash with a conflict copy): lock and .tmp files never
go over, and every minute both HQs bring their .stignore block up to date (`keep_ignores`); on the main a conflict
copy that is the same as its file, or of a lock or .tmp, is removed without a merge job (`settle`), and a call
transcript git doesn't have that hasn't changed for half an hour is committed (`commit_calls`).

Kept in HQ's own memory on this computer (hqpaths.SUPPORT), never in the workspace:
    sync.json        the setup: {"peer", "peer_name", "folders": [{"id", "what", "path"}], "set_at"}
    sync-state.json  what the routine last saw: {"since" (Syncthing's last event read), "seen_peer", "merges"}

usage (from the workspace):
  python3 "routine/sync.py"                     how the sync is doing, in plain words
  python3 "routine/sync.py" conflicts           the conflict copies there are now
  python3 "routine/sync.py" setup PEER [--workspace PATH] [--memory PATH|none] [--prefix hq] [--dry]
                                                share the workspace and the memory with PEER (its Syncthing
                                                device ID, or its name in this Syncthing); run on both computers
  python3 "routine/sync.py" remove              stop syncing (the folders leave Syncthing; the files stay)
  python3 "routine/sync.py" direction main|backup|two-way   the folders' direction on this computer (one-way sync)
Used by HQ itself: tick [--main|--backup] (the routine, every minute), align (an HQ that just became main), json.
For tests: HQ_SYNCTHING_HOME (Syncthing's config folder), HQ_SYNC_GIT=0 (no commits, no align).
"""
from __future__ import annotations

import json, os, re, ssl, subprocess, sys, time
import urllib.error, urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths

SUPPORT = hqpaths.SUPPORT
CONFIG = os.path.join(SUPPORT, "sync.json")
STATE = os.path.join(SUPPORT, "sync-state.json")
PY = sys.executable or "/usr/bin/python3"
GITLOCK = os.path.join(HERE, "gitlock.py")
JOBS = os.path.join(HERE, "jobs.py")
TIMEOUT = 8
GONE_AFTER = 600  # the other side unreachable this long before the line turns yellow (Claude's choice)
MARK = "// HQ two-way sync (H56.4): written by routine/sync.py; lines below this block are your own"
MEDIA = ("mp4", "mov", "m4v", "mkv", "webm", "avi", "m4a", "mp3", "wav", "aac", "flac", "ogg", "opus", "aiff")
# H152: a lock file belongs to the computer that holds it (a pid in it means nothing on the other one), and a
# .tmp is a write half done; both went over and made conflict copies.
IGNORE_WORKSPACE = [".git", ".claude/settings.local.json", *[f"(?i)*.{x}" for x in MEDIA], "(?d).DS_Store",
                    "(?d)Thumbs.db", "(?d).*.lock", "(?d)*.tmp"]
IGNORE_MEMORY = ["(?d).DS_Store"]
GIT_EXCLUDE = [".stfolder", ".stignore", "*.sync-conflict-*"]  # Syncthing's own files stay out of git
CONFLICT = re.compile(r"\.sync-conflict-\d{8}-\d{6}-[A-Z0-9]{7}")
CALLS_AFTER = 1800  # H152: a call transcript nobody committed, this long after its last change, is committed by the main


# --- small helpers -----------------------------------------------------------------------------------------

def _load(path, default):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


def config():
    return _load(CONFIG, {})


def is_set():
    return bool(config().get("folders"))


def hhmm(t):
    return time.strftime("%H:%M", time.localtime(t))


def memory_path(workspace):
    """Where Claude Code keeps its memory for a folder: every character that isn't a letter or digit becomes -."""
    return os.path.join(os.path.expanduser("~/.claude/projects"), re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(workspace)),
                        "memory")


# --- Syncthing's own API -----------------------------------------------------------------------------------

def syncthing_home():
    if os.environ.get("HQ_SYNCTHING_HOME"):
        return os.path.expanduser(os.environ["HQ_SYNCTHING_HOME"])
    for p in ("~/Library/Application Support/Syncthing", "~/.local/state/syncthing", "~/.config/syncthing"):
        if os.path.exists(os.path.join(os.path.expanduser(p), "config.xml")):
            return os.path.expanduser(p)
    return None


def _gui():
    home = syncthing_home()
    if not home:
        raise RuntimeError("Syncthing isn't set up on this computer")
    gui = ET.parse(os.path.join(home, "config.xml")).getroot().find("gui")
    addr = (gui.findtext("address") or "127.0.0.1:8384").strip()
    tls = gui.get("tls") == "true" or addr.startswith("https")
    addr = re.sub(r"^https?://", "", addr)
    if addr.startswith("0.0.0.0") or addr.startswith("[::]"):
        addr = "127.0.0.1:" + addr.rsplit(":", 1)[1]
    return ("https://" if tls else "http://") + addr, (gui.findtext("apikey") or "").strip()


def api(path, method="GET", body=None, timeout=TIMEOUT):
    base, key = _gui()
    req = urllib.request.Request(base + path, method=method, headers={"X-API-Key": key},
                                 data=None if body is None else json.dumps(body).encode())
    if body is not None:
        req.add_header("Content-Type", "application/json")
    ctx = ssl._create_unverified_context() if base.startswith("https") else None  # its own certificate, on localhost
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        raw = r.read()
    try:
        return json.loads(raw) if raw else None
    except ValueError:
        return raw.decode(errors="replace")


def my_id():
    return api("/rest/system/status")["myID"]


def find_device(peer):
    for d in api("/rest/config/devices"):
        if peer in (d["deviceID"], d.get("name")) or d["deviceID"].startswith(peer.upper()):
            return d
    return None


# --- setup and remove ----------------------------------------------------------------------------------------

def write_ignores(path, patterns):
    """Our patterns at the top of .stignore; whatever the user had below them is kept."""
    f = os.path.join(path, ".stignore")
    own, old = [], None
    try:
        old = open(f).read()
        lines = old.splitlines()
        if MARK in lines:
            # H152: our block runs from the mark to its blank line, whatever its length was when it was written
            i = lines.index(MARK)
            end = lines.index("", i) if "" in lines[i:] else len(lines)
            own = lines[:i] + lines[end + 1:]
        else:
            own = lines
    except OSError:
        pass
    new = "\n".join([MARK, *patterns, "", *own]).rstrip("\n") + "\n"
    if new != old:
        open(f, "w").write(new)
        return True
    return False


def keep_ignores():
    """H152: both HQs keep their .stignore block as this version of HQ writes it, so a pattern added later (the
    lock files) reaches an HQ set up before it. Returns the folders whose block changed."""
    out = []
    for f in config().get("folders", []):
        if os.path.isdir(f["path"]):
            if write_ignores(f["path"], IGNORE_WORKSPACE if f["what"] == "workspace" else IGNORE_MEMORY):
                out.append(f["what"])
    return out


def git_exclude(path):
    """Syncthing's own files out of git, locally (.git/info/exclude is never committed and never synced)."""
    info = os.path.join(path, ".git", "info")
    if not os.path.isdir(os.path.join(path, ".git")):
        return False
    os.makedirs(info, exist_ok=True)
    f = os.path.join(info, "exclude")
    have = open(f).read().splitlines() if os.path.exists(f) else []
    add = [p for p in GIT_EXCLUDE if p not in have]
    if add:
        open(f, "a").write(("\n" if have and have[-1] else "") + "# HQ two-way sync (H56.4)\n" + "\n".join(add) + "\n")
    return True


def folder_config(fid, label, path, peer):
    f = api("/rest/config/defaults/folder")
    me = my_id()
    f.update({"id": fid, "label": label, "path": path, "type": "sendreceive", "paused": False,
              "devices": [{"deviceID": me, "introducedBy": "", "encryptionPassword": ""},
                          {"deviceID": peer, "introducedBy": "", "encryptionPassword": ""}],
              "fsWatcherEnabled": True, "fsWatcherDelayS": 2,  # within seconds (Syncthing's default waits 10)
              "rescanIntervalS": 3600, "ignorePerms": False, "autoNormalize": True,
              "maxConflicts": -1})  # never drop a conflict copy (Syncthing's default keeps only 10)
    return f


def setup(args):
    peer, workspace, memory, prefix, dry = None, hqpaths.FOLDER, "", "hq", False
    it = iter(args)
    for a in it:
        if a == "--workspace":
            workspace = os.path.realpath(os.path.expanduser(next(it)))
        elif a == "--memory":
            memory = next(it)
        elif a == "--prefix":
            prefix = next(it)
        elif a == "--dry":
            dry = True
        elif peer is None:
            peer = a
        else:
            sys.exit(f"sync: don't know {a!r}\n\n{__doc__}")
    if not peer:
        sys.exit(__doc__)
    dev = find_device(peer)
    if not dev:
        sys.exit(f"sync: this Syncthing doesn't know {peer!r} yet. Pair the two computers in Syncthing first "
                 "(each adds the other's device ID), then run this again.")
    if not os.path.isdir(workspace):
        sys.exit(f"sync: no workspace at {workspace}")
    folders = [{"id": f"{prefix}-workspace", "what": "workspace", "path": workspace, "ignore": IGNORE_WORKSPACE}]
    if memory != "none":
        folders.append({"id": f"{prefix}-memory", "what": "memory",
                        "path": os.path.expanduser(memory) if memory else memory_path(workspace), "ignore": IGNORE_MEMORY})
    for f in folders:
        print(f"{'Would share' if dry else 'Sharing'} {f['what']}: {f['path']} as {f['id']} with {dev.get('name') or dev['deviceID'][:7]}")
    if dry:
        print("Skipped: " + ", ".join(IGNORE_WORKSPACE))
        return 0
    for f in folders:
        os.makedirs(f["path"], exist_ok=True)
        write_ignores(f["path"], f["ignore"])  # before Syncthing scans it, so nothing ignored ever goes over
        if f["what"] == "workspace" and git_exclude(f["path"]):
            print("Syncthing's own files are kept out of git (in .git/info/exclude, this computer only).")
        api(f"/rest/config/folders/{f['id']}", "PUT", folder_config(f["id"], f"HQ {f['what']}", f["path"], dev["deviceID"]))
    _save(CONFIG, {"peer": dev["deviceID"], "peer_name": dev.get("name") or dev["deviceID"][:7],
                   "folders": [{k: f[k] for k in ("id", "what", "path")} for f in folders], "set_at": time.time()})
    try:
        latest = api("/rest/events?since=0&limit=1&timeout=1&events=ItemFinished", timeout=TIMEOUT + 2) or []
        since = latest[-1]["id"] if latest else 0
    except Exception:
        since = 0
    _save(STATE, {"since": since, "seen_peer": time.time(), "merges": {}})
    print("Done. Run the same on the other computer (with this one as PEER); the folders connect once both have them.")
    return 0


def remove():
    cfg = config()
    for f in cfg.get("folders", []):
        try:
            api(f"/rest/config/folders/{f['id']}", "DELETE")
            print(f"Stopped syncing {f['what']} ({f['id']}); its files stay where they are.")
        except Exception as e:
            print(f"Couldn't remove {f['id']} from Syncthing: {e}")
    for p in (CONFIG, STATE):
        try:
            os.remove(p)
        except OSError:
            pass
    return 0


# --- one-way sync (Fable, 27 October 2026; the backend switch one_way_sync) ------------------------------------------

DIRECTIONS = {"main": "sendonly", "backup": "receiveonly", "two-way": "sendreceive"}


def direction(mode: str, log=print) -> list[str]:
    """Set every synced folder's type on this computer: the main sends only, the backup only receives (so the two
    never make a conflict copy: by construction), or two-way as before. Idempotent: a folder already set is left.
    Returns the folders changed. His F58 (26 October 2026): "we keep getting conflicts. I also want this logged as a
    bug with must as rank, im sick of these merges while i do nothing"."""
    want = DIRECTIONS[mode]
    changed = []
    for f in config().get("folders", []):
        try:
            cur = api(f"/rest/config/folders/{f['id']}")
        except Exception as e:
            log(f"sync: direction: couldn't read {f['id']}: {e}")
            continue
        if not isinstance(cur, dict) or cur.get("type") == want:
            continue
        cur["type"] = want
        try:
            api(f"/rest/config/folders/{f['id']}", "PUT", cur)
            changed.append(f["what"])
            log(f"sync: {f['what']} is now {want}")
        except Exception as e:
            log(f"sync: direction: couldn't set {f['id']}: {e}")
    return changed


def revert_local(log=print) -> list[str]:
    """On a receive-only folder, drop what was changed locally and take the main's copy (Syncthing's revert): the
    backup never keeps its own version of a synced file; a change it makes goes to the main by hand-over first."""
    out = []
    for f in config().get("folders", []):
        try:
            st = api(f"/rest/db/status?folder={f['id']}")
            if isinstance(st, dict) and st.get("receiveOnlyTotalItems"):
                api(f"/rest/db/revert?folder={f['id']}", "POST", {})
                out.append(f["what"])
                log(f"sync: reverted {st['receiveOnlyTotalItems']} local change(s) on {f['what']} to the main's copy")
        except Exception as e:
            log(f"sync: revert: {e}")
    return out


def one_way_on() -> bool:
    try:
        sys.path.insert(0, os.path.join(hqpaths.HQ, "app"))
        import backend
        return backend.on("one_way_sync")
    except Exception:
        return False


def tick_direction(acting: str, log=print) -> None:
    """Every minute: with the switch on, this computer's folders point the way its role says; switched off again,
    back to two-way (once, remembered in the state)."""
    if not config().get("folders"):
        return
    try:
        st = json.load(open(STATE))
    except (OSError, ValueError):
        st = {}
    if one_way_on():
        mode = "main" if acting == "main" else "backup"
        if st.get("direction") != mode:
            direction(mode, log)
            st["direction"] = mode
            _save(STATE, st)
        # No automatic revert on the backup: a local addition (a transcript of a call taken here, a note from the page)
        # stays until it's handed over; `sync.py revert` does it by hand when the main has everything.
    elif st.get("direction") in ("main", "backup"):
        direction("two-way", log)
        st["direction"] = "two-way"
        _save(STATE, st)


# --- what the routine does every minute ----------------------------------------------------------------------

def conflicts():
    """Every conflict copy in the synced folders: [{"copy", "file", "folder", "what"}]."""
    out = []
    for f in config().get("folders", []):
        for root, dirs, files in os.walk(f["path"]):
            dirs[:] = [d for d in dirs if d not in (".git", ".stfolder", ".stversions")]
            for name in files:
                if CONFLICT.search(name):
                    out.append({"copy": os.path.join(root, name), "file": os.path.join(root, CONFLICT.sub("", name)),
                                "folder": f["id"], "what": f["what"]})
    return sorted(out, key=lambda c: c["copy"])


def merge_text(c):
    rel = lambda p: os.path.relpath(p, next(f["path"] for f in config()["folders"] if f["id"] == c["folder"]))
    where = "the workspace" if c["what"] == "workspace" else "Claude's memory of the user"
    return (f"Sync conflict (H56.4), found by the routine: both HQs changed the same file in {where} at once, and "
            f"Syncthing kept both. The file: {c['file']}. The other version: {c['copy']}. Merge both into "
            f"{rel(c['file'])} without dropping anything from either: keep every line, entry and change that is in "
            f"one and not the other (for a log, both entries in time order; where they really differ and you can't "
            f"tell which is right, keep both, marked). If it isn't a text file, keep the newer one as the file and "
            f"leave the other next to it, renamed to end in '(other version)'. Then delete the conflict copy, commit "
            f"the file through the lock, and say in the log what was merged. Nothing else.")


def settle(found, log):
    """H152: conflict copies that need no merge are cleared here, without a job: one that is the same as the file
    (byte for byte), and one of a lock or a half-written .tmp (this computer's own, never worth keeping). Returns
    the ones still to merge."""
    left = []
    for c in found:
        name = os.path.basename(c["file"])
        same = False
        try:
            with open(c["copy"], "rb") as a, open(c["file"], "rb") as b:
                same = a.read() == b.read()
        except OSError:
            pass
        if same or name.endswith((".lock", ".tmp")):
            try:
                os.remove(c["copy"])
                log(f"sync: conflict copy {c['copy']} removed: " + ("the same as the file" if same else "a lock or .tmp file"))
                continue
            except OSError as e:
                log(f"sync: couldn't remove {c['copy']}: {e}")
        left.append(c)
    return left


def left_calls(now=None):
    """H152: call transcripts (HQ/calls/*.md) that git doesn't have yet and that haven't changed for CALLS_AFTER
    seconds: the call's own commit missed them (its wrap-up ran on the other computer, was cut off, or forgot).
    Relative paths, oldest first."""
    folder = next((f["path"] for f in config().get("folders", []) if f["what"] == "workspace"), None) or hqpaths.FOLDER
    calls = os.path.join(folder, "HQ", "calls")
    if not os.path.isdir(os.path.join(folder, ".git")) or not os.path.isdir(calls):
        return []
    r = subprocess.run(["git", "-C", folder, "ls-files", "--others", "--exclude-standard", "--", "HQ/calls"],
                       capture_output=True, text=True, timeout=60)
    now = now or time.time()
    out = []
    for p in r.stdout.splitlines():
        full = os.path.join(folder, p)
        if p.endswith(".md") and not CONFLICT.search(p) and os.path.isfile(full) and now - os.path.getmtime(full) >= CALLS_AFTER:
            out.append(p)
    return sorted(out)


def commit_calls(log, now=None):
    """H152: on the main, the transcripts left_calls finds are committed through the lock."""
    if os.environ.get("HQ_SYNC_GIT") == "0":
        return 0
    left = left_calls(now)
    if not left:
        return 0
    folder = next((f["path"] for f in config().get("folders", []) if f["what"] == "workspace"), None) or hqpaths.FOLDER
    env = {**os.environ, "HQ_WORKSPACE": folder}
    r = subprocess.run([PY, GITLOCK, "commit", f"Calls: {len(left)} transcript{'s' * (len(left) != 1)} the call's own commit missed",
                        *left], capture_output=True, text=True, timeout=400, env=env)
    log(f"sync: committed call transcripts nobody had: {', '.join(left)[:300]}" if r.returncode == 0
        else f"sync: committing call transcripts failed ({r.returncode}): {(r.stderr or r.stdout).strip()[:200]}")
    return len(left) if r.returncode == 0 else 0


def queue_merges(found, state, log):
    merges = state.setdefault("merges", {})
    for gone in [k for k in merges if not os.path.exists(k)]:
        merges.pop(gone)
    out = []
    for c in found:
        if c["copy"] in merges:
            continue
        r = subprocess.run([PY, JOBS, "add", merge_text(c), "--kind", "merge"], capture_output=True, text=True, timeout=60)
        m = re.search(r"[Jj]ob (\d+)", r.stdout)
        merges[c["copy"]] = int(m.group(1)) if m else None
        out.append((c, merges[c["copy"]]))
        log(f"sync: conflict copy {c['copy']}; " + (f"merge job {m.group(1)} queued" if m else f"couldn't queue a merge: {(r.stderr or r.stdout).strip()[:200]}"))
    return out


def came_over(state, main):
    """Files Syncthing brought in from the other side since the last look (its ItemFinished events). Only the
    main commits them; the backup only keeps up with the events, so nothing old is committed after a takeover."""
    ws = next((f for f in config().get("folders", []) if f["what"] == "workspace"), None)
    since = state.get("since") or 0
    try:
        ev = api(f"/rest/events?since={since}&timeout=1&events=ItemFinished", timeout=TIMEOUT + 3) or []
    except Exception:
        return []
    newest = max([e["id"] for e in ev] or [since])
    if not ev and since:
        try:  # after a Syncthing restart its event ids start again from 1; go on from its newest then
            last = api("/rest/events?since=0&limit=1&timeout=1&events=ItemFinished", timeout=TIMEOUT + 2) or []
            if not last or last[-1]["id"] < since:
                newest = last[-1]["id"] if last else 0
        except Exception:
            pass
    state["since"] = newest
    if not main or not ws:
        return []
    paths = []
    for e in ev:
        d = e.get("data") or {}
        if d.get("folder") != ws["id"] or d.get("error") or d.get("type") not in ("file", "symlink", None):
            continue
        p = d.get("item") or ""
        if not p or CONFLICT.search(p) or p.split("/")[0] == ".git" or p == ".stignore":
            continue
        if p not in paths:
            paths.append(p)
    return paths


def commit(paths, peer, log):
    if not paths or os.environ.get("HQ_SYNC_GIT") == "0":
        return 0
    folder = config()["folders"][0]["path"]
    if not os.path.isdir(os.path.join(folder, ".git")):
        return 0
    keep = []
    for p in paths:
        ignored = subprocess.run(["git", "-C", folder, "check-ignore", "-q", "--", p]).returncode == 0
        tracked = subprocess.run(["git", "-C", folder, "ls-files", "--error-unmatch", "--", p],
                                 capture_output=True).returncode == 0
        if not ignored and (tracked or os.path.exists(os.path.join(folder, p))):
            keep.append(p)
    if not keep:
        return 0
    env = {**os.environ, "HQ_WORKSPACE": folder}
    r = subprocess.run([PY, GITLOCK, "commit", f"Sync: from {peer} ({len(keep)} file{'s' * (len(keep) != 1)})", *keep],
                       capture_output=True, text=True, timeout=400, env=env)
    log(f"sync: committed what came over from {peer}: {', '.join(keep)[:300]}" if r.returncode == 0
        else f"sync: commit failed ({r.returncode}): {(r.stderr or r.stdout).strip()[:200]}")
    return len(keep) if r.returncode == 0 else 0


def look():
    """What Syncthing says now: {"peer_up", "folders": [{id, what, state, need, errors}], "error"}."""
    cfg = config()
    try:
        conns = api("/rest/system/connections")["connections"]
    except Exception as e:
        return {"error": f"Syncthing doesn't answer on this computer ({type(e).__name__})"}
    out = {"peer_up": bool((conns.get(cfg["peer"]) or {}).get("connected")), "folders": []}
    for f in cfg["folders"]:
        try:
            st = api(f"/rest/db/status?folder={f['id']}")
            errs = (api(f"/rest/folder/errors?folder={f['id']}") or {}).get("errors") or []
            out["folders"].append({"id": f["id"], "what": f["what"], "state": st.get("state", ""),
                                   "error": st.get("error") or "", "need": st.get("needFiles", 0) + st.get("needDeletes", 0),
                                   "errors": [e.get("path", "") + ": " + e.get("error", "") for e in errs][:5]})
        except urllib.error.HTTPError as e:
            out["folders"].append({"id": f["id"], "what": f["what"], "state": "missing", "need": 0, "errors": [],
                                   "error": f"Syncthing doesn't have this folder ({e.code})"})
        except Exception as e:
            out["folders"].append({"id": f["id"], "what": f["what"], "state": "", "need": 0, "errors": [],
                                   "error": type(e).__name__})
    return out


def judge(seen, found, state, main, peer, now=None):
    """The line: (state, text, why-for-an-incident or "")."""
    now = now or time.time()
    if seen.get("error"):
        return "down", seen["error"], seen["error"]
    bad = [f for f in seen["folders"] if f["error"] or f["state"] == "error" or f["errors"]]
    if bad:
        f = bad[0]
        why = f"{f['what']}: " + (f["error"] or "; ".join(f["errors"]) or "error")
        return "down", why[:200], why[:300]
    if found:
        n = len(found)
        jobs = sorted({state.get("merges", {}).get(c["copy"]) for c in found} - {None})
        what = (f"merge job{'s' * (len(jobs) > 1)} {', '.join(map(str, jobs))} queued" if jobs and main
                else "the main one merges it" if not main else "merge job not queued yet")
        names = ", ".join(os.path.basename(c["file"]) for c in found[:3])
        return "waiting", f"{n} conflict cop{'ies' if n > 1 else 'y'} ({names}): {what}", f"Both sides changed {names} at once; both versions kept"
    if not seen["peer_up"]:
        gone = now - (state.get("seen_peer") or now)
        if gone >= GONE_AFTER:
            return "waiting", f"Can't reach {peer} since {hhmm(state['seen_peer'])}; changes wait here and go over when it's back", ""
        return "ok", f"Reconnecting to {peer}", ""
    need = sum(f["need"] for f in seen["folders"])
    busy = [f for f in seen["folders"] if f["state"] in ("syncing", "sync-preparing", "scanning", "sync-waiting")]
    if need or busy:
        return "running", f"Syncing with {peer}" + (f": {need} file{'s' * (need != 1)} to go" if need else ""), ""
    return "ok", f"In sync with {peer}: the workspace" + (" and Claude's memory" if len(seen["folders"]) > 1 else ""), ""


def tick(main=True, log=print, routines=None, incidents=None):
    """Every minute, from the routine, on both HQs. Returns the line it wrote (or None when no sync is set up)."""
    if not is_set():
        return None
    cfg = config()
    peer = cfg.get("peer_name") or "the other HQ"
    try:  # Fable, 27 October 2026: one-way sync, when its switch is on
        tick_direction("main" if main else "backup", log)
    except Exception as e:
        log(f"sync: direction: {e!r}")
    state = _load(STATE, {})
    seen = look()
    if seen.get("peer_up"):
        state["seen_peer"] = time.time()
    try:
        for what in keep_ignores():
            log(f"sync: the {what}'s .stignore block brought up to date")
    except OSError as e:
        log(f"sync: .stignore: {e}")
    found = conflicts()
    if main and found:
        found = settle(found, log)
    queued = queue_merges(found, state, log) if main and found else []
    paths = came_over(state, main) if not seen.get("error") else []
    _save(STATE, state)
    committed = commit(paths, peer, log) if main else 0
    if main:
        try:
            committed += commit_calls(log)
        except Exception as e:
            log(f"sync: call transcripts: {e!r}")
    st, text, why = judge(seen, found, state, main, peer)
    if routines:
        routines.beat("sync", state=st, text=text, last=time.time(), next=time.time() + 60, every=60)
    if incidents:
        if why:
            incidents.down("sync", why)
            for c, n in queued:
                incidents.fix("sync", f"Merge job {n} queued for {os.path.basename(c['file'])}" if n else
                              f"Couldn't queue a merge job for {os.path.basename(c['file'])}")
        elif incidents.is_down("sync"):
            incidents.up("sync")
    return {"state": st, "text": text, "conflicts": len(found), "queued": [n for _, n in queued], "committed": committed}


def align(log=print):
    """An HQ that just became the main one lines its git up with GitHub first, keeping the files as they are (the
    sync already brought them): fetch, then move the branch to GitHub's without touching the working tree. Then
    its own commits go on from where the other one left off."""
    if not is_set() or os.environ.get("HQ_SYNC_GIT") == "0":
        return None
    folder = next((f["path"] for f in config()["folders"] if f["what"] == "workspace"), None)
    if not folder or not os.path.isdir(os.path.join(folder, ".git")):
        return None
    g = lambda *a: subprocess.run(["git", "-C", folder, *a], capture_output=True, text=True, timeout=120)
    branch = g("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if g("fetch", "-q", "origin").returncode:
        log("sync: align: couldn't reach GitHub; git stays as it is for now")
        return False
    up = g("rev-parse", f"origin/{branch}").stdout.strip()
    if not up or up == g("rev-parse", "HEAD").stdout.strip():
        return True
    env = {**os.environ, "HQ_WORKSPACE": folder}
    r = subprocess.run([PY, GITLOCK, "run", "git", "-C", folder, "reset", "-q", "--mixed", f"origin/{branch}"],
                       capture_output=True, text=True, timeout=400, env=env)
    log(f"sync: align: git lined up with GitHub ({up[:8]}), files kept" if r.returncode == 0
        else f"sync: align failed: {(r.stderr or r.stdout).strip()[:200]}")
    return r.returncode == 0


def say():
    if not is_set():
        return "No two-way sync here: this HQ is on its own."
    cfg = config()
    seen = look()
    found = conflicts()
    st, text, _ = judge(seen, found, _load(STATE, {}), True, cfg.get("peer_name") or "the other HQ")
    lines = [text]
    for f in seen.get("folders", []):
        lines.append(f"  {f['what']}: {f['state'] or '?'}" + (f", {f['need']} to go" if f["need"] else "")
                     + (f" ({f['error']})" if f["error"] else ""))
    return "\n".join(lines)


def main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "":
        print(say())
    elif cmd == "conflicts":
        found = conflicts()
        print("\n".join(f"{c['copy']}  (of {os.path.basename(c['file'])})" for c in found) or "No conflict copies.")
    elif cmd == "setup":
        return setup(argv[1:])
    elif cmd == "remove":
        return remove()
    elif cmd == "direction" and len(argv) == 2 and argv[1] in DIRECTIONS:
        changed = direction(argv[1])
        print("Changed: " + (", ".join(changed) if changed else "nothing (already so)"))
    elif cmd == "revert":
        print("Reverted: " + (", ".join(revert_local()) or "nothing"))
    elif cmd == "tick":
        import incidents, routines
        r = tick(main="--backup" not in argv, routines=routines, incidents=incidents)
        print(json.dumps(r))
    elif cmd == "align":
        print(align())
    elif cmd == "json":
        print(json.dumps({"set": is_set(), **({"look": look(), "conflicts": conflicts()} if is_set() else {})}))
    else:
        sys.exit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
