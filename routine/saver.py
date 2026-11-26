#!/usr/bin/env python3
"""F102 (31 October 2026): nothing written on the main stays off GitHub because nobody named it.

His quick note of 30 October and the mail check since 27 October never reached GitHub, and nothing showed it: every commit in HQ
names its files. Here a minute job on the main looks at what git sees changed in the workspace (tracked or not ignored), and every
file left unchanged for ten minutes is committed through the lock (gitlock.py), which pushes, merges a refused push and refuses a
file with a key in it. Commits that didn't get pushed are pushed again. A file still being written waits for its ten minutes.

    python3 routine/saver.py        one look, as the routine's minute does
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402

QUIET = 600        # his ten minutes: "workspace files left unsaved for ten minutes"
MOST = 300         # files in one commit; the rest next minute
SKIP_END = (".tmp", ".lock", ".here.jsonl", ".here.md", ".swp", "~")
SKIP_NAME = (".DS_Store", ".stfolder", ".stignore", "Thumbs.db")
GITLOCK = os.path.join(HERE, "gitlock.py")


def quiet_s() -> float:
    return float(os.environ.get("HQ_SAVE_QUIET") or QUIET) if hqpaths.under_test() else QUIET


def skip(rel: str) -> bool:
    name = os.path.basename(rel)
    return (name in SKIP_NAME or name.endswith(SKIP_END) or ".sync-conflict-" in name or name.startswith(".syncthing.")
            or name.startswith("~syncthing~") or rel.startswith(".git/"))


def changed(folder: str | None = None) -> list[str]:
    """The files git sees changed, deleted or new (not ignored), by name; a rename is its two names."""
    folder = folder or hqpaths.FOLDER
    r = subprocess.run(["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=folder, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:200] or "git status failed")
    out, parts, i = [], r.stdout.split("\0"), 0
    while i < len(parts):
        e = parts[i]
        i += 1
        if len(e) < 4:
            continue
        out.append(e[3:])
        if e[0] in "RC":
            out.append(parts[i])
            i += 1
    return [p for p in dict.fromkeys(out) if not skip(p)]


def ripe(rel: str, folder: str, now: float) -> bool:
    try:
        return now - os.path.getmtime(os.path.join(folder, rel)) >= quiet_s()
    except OSError:
        return True  # deleted


def ahead(folder: str) -> int:
    r = subprocess.run(["git", "rev-list", "--count", "@{u}..HEAD"], cwd=folder, capture_output=True, text=True)
    return int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip().isdigit() else 0


def minute(log=print, now=None) -> list[str]:
    """One look. Returns the files committed; raises when git or the commit failed."""
    folder = hqpaths.FOLDER
    if not os.path.exists(os.path.join(folder, ".git")):
        return []
    now = now or time.time()
    files = [p for p in changed(folder) if ripe(p, folder, now)][:MOST]
    env = {**os.environ, "HQ_ROLE_HERE": "1"}
    if files:
        r = subprocess.run([sys.executable, GITLOCK, "commit", f"Saved: {len(files)} file{'s' * (len(files) != 1)} nobody committed", *files],
                           capture_output=True, text=True, timeout=500, env=env)
        if r.returncode:
            raise RuntimeError((r.stderr or r.stdout).strip()[-300:] or f"gitlock ended with {r.returncode}")
        log(f"saved {len(files)} file(s) nobody committed: {', '.join(files)[:200]}")
        return files
    if ahead(folder):
        r = subprocess.run([sys.executable, GITLOCK, "push"], capture_output=True, text=True, timeout=500, env=env)
        if r.returncode:
            raise RuntimeError((r.stderr or r.stdout).strip()[-300:] or f"the push ended with {r.returncode}")
    return []


if __name__ == "__main__":
    print(minute() or "Nothing to save.")
