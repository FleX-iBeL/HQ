"""F102 (31 October 2026): one lock across processes for a shared file, with unique temp files.

His words: "yes exactly, i want here we put it on our roadmap and planning, and then we run these first." On a copy 300 notes added
by two processes left 18: the to-do list, the notes, the games and the coaching file each held a lock that only works inside one
process, and wrote through one fixed temp name. The web page, a forwarded command and a call are separate processes.

    _lock = hqlock.For(path)        # path: a function that says which file, read at each use
    with _lock:                       # read, change and write under it; works across processes and threads
        tmp = hqlock.tmp(p)         # a temp name no other writer has

The lock is flock on a file named after the shared file in HQ's own scratch/routine/locks (never in the user's folder), the same
one handover.py takes, so a hand-over and a command take turns on the same file. Standard library only.
"""
from __future__ import annotations

import contextlib
import fcntl
import os
import sys
import threading
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hqpaths  # noqa: E402

FOLDER = os.path.join(hqpaths.HQ, "scratch", "routine", "locks")


def lock_path(path) -> str:
    os.makedirs(FOLDER, exist_ok=True)
    name = os.path.relpath(os.fspath(path), hqpaths.FOLDER).replace(os.sep, "__").replace("..", "_")
    return os.path.join(FOLDER, name + ".lock")


@contextlib.contextmanager
def locked(path):
    with open(lock_path(path), "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


class For:
    """`with lock:` for the file a function names. Each use opens its own descriptor, so threads wait for each other too."""

    def __init__(self, path_of):
        self.path_of = path_of
        self.held = threading.local()

    def __enter__(self):
        f = open(lock_path(self.path_of()), "w")
        fcntl.flock(f, fcntl.LOCK_EX)
        self.held.f = f
        return self

    def __exit__(self, *a):
        f = self.held.f
        fcntl.flock(f, fcntl.LOCK_UN)
        f.close()


def tmp(path) -> Path:
    """A temp name next to the file that no other writer has."""
    p = Path(path)
    return p.with_name(f"{p.name}.{os.getpid()}.{threading.get_ident()}.tmp")
