#!/usr/bin/env python3
"""F104: a version's changes to the user's data, each with its undo.

His words: "yes exactly, i want here we put it on our roadmap and planning, and then we run these first." A bad version must be
undoable in one step, and the code alone doesn't undo what it did to the data. So a change to the data ships as a file in
`routine/datachanges/` (README.md there) with `do`, `undo` and `WHAT`; which ones have run stands in the workspace's
`HQ/data-changes.json`. The main runs a new one, the release tries its undo on a copy before it goes out, `update.py back` undoes.
A file in the folder isn't enough to run on real data, jobs work in the live clone: it has to be committed, unchanged from HEAD, and on
GitHub's dev on the maker's copy, in the release she stands on on a friend's. Anything else is left alone and said once in the routine's log.

    python3 routine/datachange.py list            every change, and whether it has run here
    python3 routine/datachange.py apply           what hasn't run yet and may (the routine's minute, on the main)
    python3 routine/datachange.py try [NAME …]    do and undo on a throwaway copy of the workspace; says what doesn't come back
Standard library only.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqlock  # noqa: E402
import hqpaths  # noqa: E402

REL = "routine/datachanges"
STATE = os.path.join("HQ", "data-changes.json")
LEFT = os.path.join(".status", "data-changes-left.json")  # what's been said about the changes left alone, per computer
WORK_LINE = "refs/remotes/origin/dev"  # F104: GitHub's dev as this copy knows it, never a local branch of that name
TAG = re.compile(r"^v(\d+)\.(\d+)(?:\.(\d+))?$")


def _base(base=None) -> Path:
    return Path(base or hqpaths.FOLDER)


def names(root=None) -> list[str]:
    try:
        return sorted(n[:-3] for n in os.listdir(os.path.join(str(root or hqpaths.HQ), REL)) if n.endswith(".py") and not n.startswith("_"))
    except OSError:
        return []


def number(name: str) -> str:
    """F104: what makes a change that change: the number at the start of its name; a rename doesn't make it a new one. A name with no number is itself."""
    m = re.match(r"\d+", name)
    return str(int(m.group(0))) if m else name


def renamed_from(name: str, root=None) -> str:
    """F104: the change this file was renamed from with another number, by git's own history, or "". Its identity is still that one's."""
    rel = f"{REL}/{name}.py"
    for ln in _git(root, "log", "-M", "--diff-filter=R", "--name-status", "--format=", "HEAD", "--", REL).splitlines():
        cols = ln.split("\t")
        if len(cols) == 3 and cols[2] == rel and number(Path(cols[1]).stem) != number(name):
            return Path(cols[1]).stem
    return ""


def load(name: str, root=None):
    """The change's module. Raises when it can't be loaded or lacks do, undo or WHAT."""
    p = os.path.join(str(root or hqpaths.HQ), REL, name + ".py")
    spec = importlib.util.spec_from_file_location(f"hq_datachange_{name.replace('-', '_')}", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for need in ("do", "undo", "WHAT"):
        if not hasattr(m, need):
            raise ValueError(f"{name} has no {need}")
    return m


def applied(base=None) -> list[str]:
    try:
        return json.loads((_base(base) / STATE).read_text(encoding="utf8")).get("applied") or []
    except (OSError, ValueError):
        return []


def _save(have: list[str], base=None) -> None:
    p = _base(base) / STATE
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = hqlock.tmp(str(p))
    with open(tmp, "w", encoding="utf8") as f:
        json.dump({"applied": have}, f, indent=1)
    os.replace(tmp, p)


def _git(root, *args: str) -> str:
    """What git prints, or "" when it says no or can't be asked: what can't be told isn't run on real data."""
    try:
        r = subprocess.run(["git", "-C", str(root or hqpaths.HQ), *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout.strip() if not r.returncode else ""


def _stands_on(root=None) -> str:
    """The release this copy stands on: the newest version tag in the head's history."""
    tags = [(tuple(int(x or 0) for x in m.groups()), m.group(0)) for m in map(TAG.match, _git(root, "tag", "--merged", "HEAD").split()) if m]
    return max(tags)[1] if tags else ""


def why_left(name: str, root=None) -> str:
    """F104: why this change doesn't run here; "" when it may. Committed, unchanged from HEAD, and on GitHub's dev on the maker's copy, in the
    release she stands on on a friend's, the same file each time."""
    rel = f"{REL}/{name}.py"
    here = _git(root, "rev-parse", "-q", "--verify", f"HEAD:{rel}")
    if not here:
        return "it isn't committed"
    if _git(root, "status", "--porcelain", "--", rel):
        return "it differs from what's committed"
    if hqpaths.is_maker():
        return "" if _git(root, "rev-parse", "-q", "--verify", f"{WORK_LINE}:{rel}") == here else "it isn't on GitHub's dev"
    tag = _stands_on(root)
    if not tag:
        return "this copy stands on no release"
    return "" if _git(root, "rev-parse", "-q", "--verify", f"refs/tags/{tag}:{rel}") == here else f"it isn't in {tag}, the release this copy stands on"


def _say_left(left: dict, root=None, log=None) -> None:
    """F104: what's left alone, said once: a name goes in the log when it's new or its reason changes, not every minute."""
    if not log:
        return
    p = os.path.join(str(root or hqpaths.HQ), LEFT)
    try:
        said = json.load(open(p, encoding="utf8"))
    except (OSError, ValueError):
        said = {}
    if said == left:
        return
    for n, why in left.items():
        if said.get(n) != why:
            log(f"data change left alone: {n}: {why}")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = hqlock.tmp(p)
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(left, f, indent=1)
    os.replace(tmp, p)


def apply(base=None, root=None, log=None) -> list[str]:
    """Runs what hasn't run and may (why_left). On a first look nothing is taken as having run for code that has no change yet."""
    did, left = [], {}
    have = applied(base)
    here = names(root)
    for n in here:
        if n in have:
            continue
        ran_as = [x for x in have if number(x) == number(n)]
        if ran_as:  # renamed after it ran: the same change. Another file with a number that's taken never runs, and that's said
            if ran_as[0] in here:
                left[n] = f"its number is {ran_as[0]}'s"
            continue
        was = renamed_from(n, root)
        if was and any(number(x) == number(was) for x in have):
            left[n] = f"it's {was} under a new number, and that has run: a change keeps its number"
            continue
        why = why_left(n, root)
        if why:
            left[n] = why
            continue
        load(n, root).do(_base(base))
        have.append(n)
        _save(have, base)
        did.append(n)
        if log:
            log(f"data change: {n}")
    _say_left(left, root, log)
    return did


def undo(todo: list[str], base=None, root=None) -> list[str]:
    """The undos of these, newest first; only what has run. A failure puts back what this run undid, and raises."""
    have = applied(base)
    ids = {number(x) for x in have}
    done: list[str] = []
    for n in sorted((x for x in todo if number(x) in ids), reverse=True):
        try:
            load(n, root).undo(_base(base))
        except Exception:
            for b in reversed(done):
                load(b, root).do(_base(base))
            raise
        done.append(n)
    if done:
        gone = {number(x) for x in done}
        _save([x for x in have if number(x) not in gone], base)
    return done


def between(a: str, b: str, root=None) -> list[str]:
    """The changes added from a to b, in order; one with a number that was already there is that change, renamed."""
    r = subprocess.run(["git", "-C", str(root or hqpaths.HQ), "diff", "--name-only", "--diff-filter=A", a, b, "--", REL],
                       capture_output=True, text=True)
    new = sorted(Path(f).stem for f in r.stdout.splitlines() if f.endswith(".py") and not Path(f).name.startswith("_"))
    old = {number(n) for n in _names_at(a, root)}
    return [n for n in new if number(n) not in old]


def _names_at(rev: str, root=None) -> list[str]:
    return [Path(f).stem for f in _git(root, "ls-tree", "-r", "--name-only", rev, "--", REL + "/").splitlines() if f.endswith(".py") and not Path(f).name.startswith("_")]


def number_refuses(a: str, b: str, root=None) -> str | None:
    """F104: the release check: at `b` every change has its own number, and from a to b none got a new one. What's wrong, or None."""
    at_b = _names_at(b, root)
    for n in at_b:
        same = [x for x in at_b if x != n and number(x) == number(n)]
        if same:
            return f"{n} and {same[0]} have the same number, and a change's number is what it is"
    for ln in _git(root, "diff", "-M", "--diff-filter=R", "--name-status", a, b, "--", REL).splitlines():
        cols = ln.split("\t")
        if len(cols) == 3 and number(Path(cols[1]).stem) != number(Path(cols[2]).stem):
            return f"{Path(cols[1]).stem} got a new number ({Path(cols[2]).stem}), and it would run a second time"
    return None


def _skip(base: Path):
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "app"))
        import me as _me
        protected = set(_me.load(base)["protected"])
    except Exception:
        protected = set()

    def ignore(d, files):
        top = Path(d) == base
        return [f for f in files if f in (".git", ".stfolder", ".stversions") or (top and f in protected) or f.endswith((".mp4", ".mov", ".m4a", ".wav", ".mp3"))]
    return ignore


def snapshot(folder: Path) -> dict:
    out = {}
    for p in sorted(folder.rglob("*")):
        if p.is_file() and p.name != Path(STATE).name:
            out[str(p.relative_to(folder))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def try_on_copy(todo: list[str], base=None, root=None) -> str | None:
    """Each change done and undone on a throwaway copy of the workspace, its files compared before and after. None, or what's wrong."""
    src = _base(base)
    tmp = tempfile.mkdtemp(prefix="hq-datachange-")
    copy = Path(tmp) / "ws"
    try:
        shutil.copytree(src, copy, ignore=_skip(src), symlinks=True)
        ids = {number(x) for x in applied(copy)}
        for n in sorted((x for x in todo if number(x) in ids), reverse=True):  # what the work line has already run here: back first
            try:
                load(n, root).undo(copy)
            except Exception as e:
                return f"the undo of {n} failed on a copy: {e!r}"
        for n in sorted(todo):
            before = snapshot(copy)
            try:
                m = load(n, root)
                m.do(copy)
            except Exception as e:
                return f"{n} failed on a copy: {e!r}"
            try:
                m.undo(copy)
            except Exception as e:
                return f"the undo of {n} failed on a copy: {e!r}"
            after = snapshot(copy)
            if after != before:
                off = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
                return f"the undo of {n} doesn't put things back on a copy: {', '.join(off[:5])} differ"
            m.do(copy)  # the next change starts from this one done
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def lines_for(todo: list[str], root=None) -> list[str]:
    """The changelog's lines for these changes."""
    return [f"- Your data: {load(n, root).WHAT.rstrip('.')}. Going back a version undoes it." for n in sorted(todo)]


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "list"
    if cmd == "list":
        have = applied()
        print("\n".join(f"{n}: {'run here' if number(n) in {number(x) for x in have} else 'not run'}" for n in names()) or "No data changes.")
        return 0
    if cmd == "apply":
        print("\n".join(apply(log=print)) or "Nothing to run.")
        return 0
    if cmd == "try":
        no = try_on_copy(argv[1:] or names())
        print(no or "Every undo comes back clean on a copy.")
        return 1 if no else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
