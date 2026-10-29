#!/usr/bin/env python3
"""One writer (H203, 17 October 2026): the main writes a change the backup handed it.

On the backup, a call or chat never writes the files only the main writes (role.ONE_WRITER: the roadmap, the coaching
log, the mail list, the to-do list, and an agent's own notes). Its edit goes to the main through role.hand(), the
same way the team's list and the schedule already do; the main makes it here, on its own copy, and the sync brings
it back. In the user's words (call of 17 October 2026, 14:45): "i am even more confused, you give it to the server
but then also do it yourself? why?"

usage (run by the main, through /api/forward; never from a call. H298, piece 8: also by an agent's own cycle on the
main, where it is the one serialized way into the log, the mail list and the to-do list; the roadmap takes the
queue's lock, every other shared file its own lock next to it):
  python3 "routine/handover.py" edit REL JSON   make the edits in the workspace file REL; JSON is
                                                {"edits": [{"old": "...", "new": "...", "all": false}, ...]},
                                                the call's own Edit (or MultiEdit), all or nothing
Exit 0 when written, 1 when the main's copy doesn't have the text (nothing written), 2 when it's refused.
"""
from __future__ import annotations

import contextlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths
import role


def apply(text: str, edits: list[dict]) -> str:
    """The edits in order, like the Edit tool: each old text once (or every time with all), all or nothing."""
    for i, e in enumerate(edits, 1):
        old, new = str(e.get("old") or ""), str(e.get("new") or "")
        n = f" (edit {i})" if len(edits) > 1 else ""
        if not old:
            raise ValueError(f"an empty text to replace{n}")
        count = text.count(old)
        if not count:
            raise LookupError(f"the main's copy doesn't have the text to replace{n}")
        if count > 1 and not e.get("all"):
            raise LookupError(f"the text to replace is there {count} times in the main's copy{n}")
        text = text.replace(old, new) if e.get("all") else text.replace(old, new, 1)
    return text


@contextlib.contextmanager
def _file_lock(path: str):
    """H298, piece 8: one writer at a time on a shared file. The call line, a text, the routine and an agent's own
    cycle (a headless run as her) can all reach the log, the mail list or the to-do list in the same minute; each
    takes this lock (flock on a file named after it in HQ's own scratch/routine/locks, next to the queue's lock,
    never in the user's folder) around its read, edit and replace, so no edit is lost under another's. The roadmap
    keeps the queue's own lock."""
    import fcntl
    import jobs
    folder = os.path.join(os.path.dirname(jobs.LOCK), "locks")
    os.makedirs(folder, exist_ok=True)
    name = os.path.relpath(path, hqpaths.FOLDER).replace(os.sep, "__").replace("..", "_")
    with open(os.path.join(folder, name + ".lock"), "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _lock(rel):
    """The roadmap is also written by the queue and the schedule: take their turn. The rest takes the file's own
    lock (H298, piece 8), so two writers in the same minute land one after the other."""
    if rel == "HQ/roadmap.md":
        import jobs
        return jobs.locked()
    return _file_lock(os.path.join(hqpaths.FOLDER, rel))


def edit(rel: str, payload: str) -> int:
    rel = rel.replace(os.sep, "/").lstrip("./")
    if not role.one_writer(rel) or ".." in rel.split("/"):
        print(f"Refused: {rel} isn't one of the files only the main writes.")
        return 2
    try:
        edits = json.loads(payload).get("edits") or []
        assert isinstance(edits, list) and edits and all(isinstance(e, dict) for e in edits)
    except Exception:
        print("Refused: no edits given.")
        return 2
    path = hqpaths.ROADMAP if rel == "HQ/roadmap.md" else os.path.join(hqpaths.FOLDER, rel)
    with _lock(rel):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"The main couldn't read {rel}: {e.strerror}")
            return 1
        try:
            new = apply(text, edits)
        except (LookupError, ValueError) as e:
            print(f"Not written: {e}.")
            return 1
        tmp = f"{path}.handover.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(new)
        with contextlib.suppress(OSError):
            os.chmod(tmp, os.stat(path).st_mode & 0o777)
        os.replace(tmp, path)
    print(f"Written by the main: {rel}.")
    return 0


PUT_MOST = 100_000


def put(rel: str, payload: str) -> int:
    """Fable, 27 October 2026 (one-way sync): a whole small file from the backup, written by the main as it is: a
    new file, or one the backup made whole (a call's transcript at its end, a note). The payload is {"text": …}."""
    rel = rel.replace(os.sep, "/").lstrip("./")
    if ".." in rel.split("/") or rel.startswith(".git") or not rel:
        print(f"Refused: {rel} can't be written.")
        return 2
    try:
        text = json.loads(payload).get("text")
        assert isinstance(text, str)
    except Exception:
        print("Refused: no text given.")
        return 2
    if len(text.encode("utf8")) > PUT_MOST:
        print(f"Refused: {rel} is over {PUT_MOST // 1000} KB; make it as Edits.")
        return 2
    path = hqpaths.ROADMAP if rel == "HQ/roadmap.md" else os.path.join(hqpaths.FOLDER, rel)
    with _lock(rel):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.handover.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    print(f"Written by the main: {rel} (whole).")
    return 0


def main(argv):
    if len(argv) == 3 and argv[0] == "edit":
        return edit(argv[1], argv[2])
    if len(argv) == 3 and argv[0] == "put":
        return put(argv[1], argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
