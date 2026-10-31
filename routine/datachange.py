#!/usr/bin/env python3
"""F104: a version's changes to the user's data, each with its undo.

His words: "yes exactly, i want here we put it on our roadmap and planning, and then we run these first." A bad version must be
undoable in one step, and the code alone doesn't undo what it did to the data. So a change to the data ships as a file in
`routine/datachanges/` (README.md there) with `do`, `undo` and `WHAT`; which ones have run stands in the workspace's
`HQ/data-changes.json`. The main runs a new one, the release tries its undo on a copy before it goes out, `update.py back` undoes.

    python3 routine/datachange.py list            every change, and whether it has run here
    python3 routine/datachange.py apply           what hasn't run yet (the routine's minute, on the main)
    python3 routine/datachange.py try [NAME …]    do and undo on a throwaway copy of the workspace; says what doesn't come back
Standard library only.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
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


def _base(base=None) -> Path:
    return Path(base or hqpaths.FOLDER)


def names(root=None) -> list[str]:
    try:
        return sorted(n[:-3] for n in os.listdir(os.path.join(str(root or hqpaths.HQ), REL)) if n.endswith(".py") and not n.startswith("_"))
    except OSError:
        return []


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


def apply(base=None, root=None, log=None) -> list[str]:
    """Runs what hasn't run. On a first look nothing is taken as having run for code that has no change yet."""
    did = []
    have = applied(base)
    for n in names(root):
        if n not in have:
            load(n, root).do(_base(base))
            have.append(n)
            _save(have, base)
            did.append(n)
            if log:
                log(f"data change: {n}")
    return did


def undo(todo: list[str], base=None, root=None) -> list[str]:
    """The undos of these, newest first; only what has run. A failure puts back what this run undid, and raises."""
    have = applied(base)
    done: list[str] = []
    for n in sorted((x for x in todo if x in have), reverse=True):
        try:
            load(n, root).undo(_base(base))
        except Exception:
            for b in reversed(done):
                load(b, root).do(_base(base))
            raise
        done.append(n)
    if done:
        _save([x for x in have if x not in done], base)
    return done


def between(a: str, b: str, root=None) -> list[str]:
    """The changes added from a to b, in order."""
    r = subprocess.run(["git", "-C", str(root or hqpaths.HQ), "diff", "--name-only", "--diff-filter=A", a, b, "--", REL],
                       capture_output=True, text=True)
    return sorted(Path(f).stem for f in r.stdout.splitlines() if f.endswith(".py") and not Path(f).name.startswith("_"))


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
        have = applied(copy)
        for n in sorted((x for x in todo if x in have), reverse=True):  # what the work line has already run here: back first
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
        print("\n".join(f"{n}: {'run here' if n in have else 'not run'}" for n in names()) or "No data changes.")
        return 0
    if cmd == "apply":
        print("\n".join(apply()) or "Nothing to run.")
        return 0
    if cmd == "try":
        no = try_on_copy(argv[1:] or names())
        print(no or "Every undo comes back clean on a copy.")
        return 1 if no else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
