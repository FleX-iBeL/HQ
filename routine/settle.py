#!/usr/bin/env python3
"""F115 (2 November 2026): two computers don't lose or hide what he did. When both have a version of the same file,
the main's version stays in the file and the other's own words go into one list he sees, so nothing is lost and
nothing waits on him or on a merge job.

His words (the item, 2 November 2026): "sometimes my laptop crashes". Why: the server is main, the laptop is backup,
and he shouldn't have to know which one he's on. The rules (Claude's proposal on the item, his to change):
  - A conflict copy: the same line in both keeps the main's, and the other's words go in one list he sees; a copy
    that differs in nothing is removed. Settled means no copies left on the laptop and every kept difference in
    that list.
  - What the backup has that the main doesn't (written there while the main was away, or before a door was in
    place) goes to the main through the door (`file`): a file the main doesn't have is written whole, a version
    that only adds to the main's is taken as it is, a log of lines (.jsonl) gets every line of both, and anything
    else is a clash: the main's stays and the other's own lines are kept in the list, named.
  - Repeats: a hand-over has an id and a second one does nothing; a settled conflict that comes back is told once
    (an entry in the list has an id; the same difference again adds nothing).

The list is the workspace's HQ/kept-from-both.md, written only by the main (role.ONE_WRITER), newest first.

    python3 routine/settle.py                    how many differences are kept, the newest first
    python3 routine/settle.py file WHAT REL      the main settles the other computer's version of REL (WHAT is
                                                 workspace or memory); the payload on stdin as JSON: {"text"} or
                                                 {"b64"} or {"deleted": true}, and "from" (the other computer's name)
Used by HQ itself: role.py (the door), sync.py (conflict copies on the main, the hand-over from the backup),
gitlock.py (a repo conflict, and a commit on the backup).
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402

KEPT = "HQ/kept-from-both.md"
PY = sys.executable or "/usr/bin/python3"
INTRO = ("# Kept from both computers\n\n"
         "> **Private.** Only for this workspace and its private repo.\n\n"
         "When both computers had their own version of the same thing, the main's version stayed where it was and the "
         "other's own words are kept here, so nothing is lost. Look through them when you like: take back what you "
         "want into its place, then delete the entry. Written by HQ (F115), newest first.\n")
FENCE = "~~~~"


def kept_path(folder: str | None = None) -> str:
    return os.environ.get("HQ_KEPT_FILE") or os.path.join(folder or hqpaths.FOLDER, KEPT)


@contextlib.contextmanager
def file_lock(path: str):
    """The one lock of a shared file: the roadmap takes the queue's, every other file its own (hqlock)."""
    if os.path.realpath(path) == os.path.realpath(hqpaths.ROADMAP):
        import jobs
        with jobs.locked():
            yield
        return
    import hqlock
    with hqlock.locked(path):
        yield


# ---- the list ------------------------------------------------------------------------------------------------------

def entry_id(rel: str, lines: list[str], why: str = "") -> str:
    return hashlib.sha1(("\n".join([rel, why] + lines)).encode("utf8")).hexdigest()[:12]


def has(eid: str, folder: str | None = None) -> bool:
    try:
        return f"<!-- id: {eid} -->" in open(kept_path(folder), encoding="utf8").read()
    except OSError:
        return False


def keep(rel: str, lines: list[str], who: str, why: str, folder: str | None = None, eid: str = "",
         now: float | None = None) -> str:
    """One entry in the list (newest first). Returns its id; nothing is added when that id is there already."""
    eid = eid or entry_id(rel, lines, why)
    p = kept_path(folder)
    with file_lock(p):
        try:
            text = open(p, encoding="utf8").read()
        except OSError:
            text = INTRO
        if f"<!-- id: {eid} -->" in text:
            return eid
        stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(now or time.time()))
        body = [f"## {stamp} · {rel} · from {who}", f"<!-- id: {eid} -->", "", why]
        if lines:
            body += ["", FENCE + "text", *[l.replace(FENCE, "~ ~ ~ ~") for l in lines], FENCE]
        block = "\n".join(body) + "\n"
        at = text.find("\n## ")
        text = (text.rstrip("\n") + "\n\n" + block) if at < 0 else (text[:at + 1] + block + "\n" + text[at + 1:])
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = f"{p}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf8") as f:
            f.write(text)
        os.replace(tmp, p)
    return eid


def entries(folder: str | None = None) -> list[dict]:
    try:
        text = open(kept_path(folder), encoding="utf8").read()
    except OSError:
        return []
    out = []
    for m in re.finditer(r"^## (\d{4}-\d\d-\d\d \d\d:\d\d) · (.+?) · from (.+)$\n<!-- id: (\w+) -->", text, re.M):
        out.append({"at": m.group(1), "file": m.group(2), "from": m.group(3), "id": m.group(4)})
    return out


def recent(hours: float = 24, folder: str | None = None, now: float | None = None) -> int:
    """How many entries came in the last `hours` (the sync line says so for a day, then stays quiet)."""
    now = now or time.time()
    n = 0
    for e in entries(folder):
        try:
            t = time.mktime(time.strptime(e["at"], "%Y-%m-%d %H:%M"))
        except ValueError:
            continue
        n += now - t < hours * 3600
    return n


# ---- the rule --------------------------------------------------------------------------------------------------------

def _subseq(small: list[str], big: list[str]) -> bool:
    it = iter(big)
    return all(any(x == y for y in it) for x in small)


def merge_jsonl(a: str, b: str) -> str | None:
    """Every line of both, each once, in time order when every line has its "at" (sync.merge_lines' rule)."""
    try:
        rows = [(l, json.loads(l)) for l in a.splitlines() + b.splitlines() if l.strip()]
    except ValueError:
        return None
    seen, out = set(), []
    for l, d in rows:
        if l not in seen:
            seen.add(l)
            out.append((l, d))

    def at(d):
        try:
            return float(d.get("at"))
        except (AttributeError, TypeError, ValueError):
            return None
    if out and all(at(d) is not None for _, d in out):
        out.sort(key=lambda x: at(x[1]))
    return "".join(l + "\n" for l, _ in out)


def decide(rel: str, main_text: str | None, other_text: str) -> tuple[str | None, list[str], str]:
    """(what the file becomes, or None to leave it; the other's own lines to keep in the list; how, in words)."""
    if main_text is None:
        return other_text, [], "new here, written whole"
    if main_text == other_text:
        return None, [], "the same"
    if rel.endswith(".jsonl"):
        merged = merge_jsonl(main_text, other_text)
        if merged is not None:
            return (None if merged == main_text else merged), [], "every line of both"
    m, o = main_text.splitlines(), other_text.splitlines()
    if _subseq(m, o):
        return other_text, [], "it only added to the main's, taken as it is"
    if _subseq(o, m):
        return None, [], "the main had all of it already"
    have = set(m)
    extra = [l for l in o if l.strip() and l not in have]
    if not extra:
        return None, [], "nothing in it the main doesn't have"
    return None, extra, "both changed it: the main's stays, the other's own lines are kept"


# ---- on the main -----------------------------------------------------------------------------------------------------

def folder_of(what: str) -> str | None:
    """The synced folder `what` names on this computer (workspace or memory); the workspace without a sync."""
    try:
        import sync
        for f in sync.config().get("folders", []):
            if f["what"] == what:
                return f["path"]
    except Exception:
        pass
    return hqpaths.FOLDER if what == "workspace" else None


def _commit_later(folder: str, msg: str, rels: list[str]) -> None:
    """The main commits what it settled through the shared lock, in the background (the hand-over answers at once)."""
    if os.environ.get("HQ_SYNC_GIT") == "0" or not os.path.isdir(os.path.join(folder, ".git")):
        return
    rels = [r for r in rels if subprocess.run(["git", "-C", folder, "check-ignore", "-q", "--", r]).returncode != 0]
    if not rels:
        return
    log = os.path.join(hqpaths.HQ, "scratch", "routine", "settle.log")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    subprocess.Popen([PY, os.path.join(HERE, "gitlock.py"), "commit", msg, *rels], cwd=folder,
                     env={**os.environ, "HQ_WORKSPACE": folder, "HQ_ROLE_HERE": "1"}, stdout=open(log, "a"),
                     stderr=subprocess.STDOUT, start_new_session=True)


def settle_file(what: str, rel: str, payload: dict, log=None) -> tuple[int, str]:
    """The main settles the other computer's version of rel. (exit code, what happened in words)."""
    rel = rel.replace(os.sep, "/").lstrip("/")
    if not rel or ".." in rel.split("/") or rel.split("/")[0] in (".git", ".stfolder") or re.search(r"[\x00]", rel):
        return 2, f"Refused: {rel} can't be settled."
    base = folder_of(what)
    if not base:
        return 2, f"Refused: there's no {what} folder here."
    who = str(payload.get("from") or "the other computer")[:60]
    path = os.path.join(base, rel)
    ws = what == "workspace"
    label = rel if ws else f"Claude's memory: {rel}"
    if payload.get("deleted"):
        if not os.path.exists(path):
            return 0, f"{label}: gone on both."
        if ws:
            keep(rel, [], who, f"Removed on {who}; the main's copy stays.", folder=base)
        return 0, f"{label}: removed on {who}; the main's copy stays" + (", named in the list." if ws else ".")
    raw = None
    if "b64" in payload:
        try:
            raw = base64.b64decode(payload["b64"])
        except ValueError:
            return 2, "Refused: the file didn't come over whole."
        try:
            other = raw.decode("utf8")
            raw = None
        except UnicodeDecodeError:
            other = None
    else:
        other = payload.get("text")
        if not isinstance(other, str):
            return 2, "Refused: no text given."
    changed = []
    with file_lock(path):
        if raw is not None:  # not text: the main's stays; a different one is kept next to it, named in the list
            try:
                mine = open(path, "rb").read()
            except OSError:
                mine = None
            if mine == raw:
                return 0, f"{label}: the same."
            if mine is None:
                target, said = path, "new here, written whole"
            else:
                stem, ext = os.path.splitext(path)
                target = f"{stem} (from {who}){ext}"
                said = f"both had their own; the other's is next to it as {os.path.basename(target)}"
            os.makedirs(os.path.dirname(target), exist_ok=True)
            tmp = f"{target}.{os.getpid()}.tmp"
            open(tmp, "wb").write(raw)
            os.replace(tmp, target)
            changed.append(os.path.relpath(target, base))
            if mine is not None and ws:
                keep(rel, [], who, f"Both had their own; the other's is kept next to it as {os.path.basename(target)}.",
                     folder=base)
                changed.append(KEPT)
            if ws:
                _commit_later(base, f"Settled from {who}: {rel}", changed)
            return 0, f"{label}: {said}."
        try:
            mine = open(path, encoding="utf8").read()
        except FileNotFoundError:
            mine = None
        except (OSError, UnicodeDecodeError) as e:
            return 1, f"{label}: the main couldn't read its own: {e}"
        new, extra, said = decide(rel, mine, other)
        if new is not None:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = f"{path}.{os.getpid()}.settle.tmp"
            with open(tmp, "w", encoding="utf8") as f:
                f.write(new)
            with contextlib.suppress(OSError):
                if mine is not None:
                    os.chmod(tmp, os.stat(path).st_mode & 0o777)
            os.replace(tmp, path)
            changed.append(rel)
    if extra:
        keep(rel if ws else f"Claude's memory: {rel}", extra, who,
             f"Both computers changed this file. The main's version stayed; these lines were only in {who}'s.",
             folder=folder_of("workspace"))
        changed.append(KEPT)
    if log:
        log(f"settle: {label} from {who}: {said}")
    if changed and ws:
        _commit_later(base, f"Settled from {who}: {rel}", changed)
    return 0, f"{label}: {said}" + (f"; {len(extra)} line{'s' * (len(extra) != 1)} kept in the list." if extra else ".")


def settle_copy(c: dict, main_device: str | None, other_name: str, log=None) -> bool:
    """A conflict copy on the main (sync.conflicts' {copy, file, folder, what}). The main's version is the file,
    unless the copy was made by the main's own computer (its short device id in the copy's name): then the copy is the
    main's. The main's version ends in the file, the other's own lines in the list, the copy goes. True when settled."""
    try:
        copy_raw = open(c["copy"], "rb").read()
        try:
            file_raw = open(c["file"], "rb").read()
        except FileNotFoundError:
            file_raw = None
    except OSError as e:
        if log:
            log(f"settle: couldn't read {c['copy']}: {e}")
        return False
    m = re.search(r"\.sync-conflict-\d{8}-\d{6}-([A-Z0-9]{7})", os.path.basename(c["copy"]))
    copy_is_main = bool(m and main_device and main_device.upper().startswith(m.group(1)))
    base = os.path.dirname(c["file"])
    for f in _folders():
        if c["file"].startswith(f["path"].rstrip("/") + "/"):
            base = f["path"]
            break
    rel = os.path.relpath(c["file"], base)
    main_raw, other_raw = (copy_raw, file_raw) if copy_is_main else (file_raw, copy_raw)
    path = c["file"]
    with file_lock(path):
        if copy_is_main:  # the main's own version goes back into the file first
            tmp = f"{path}.{os.getpid()}.settle.tmp"
            open(tmp, "wb").write(main_raw)
            os.replace(tmp, path)
    if other_raw is None:
        os.remove(c["copy"])
        return True
    payload = {"from": other_name}
    try:
        payload["text"] = other_raw.decode("utf8")
    except UnicodeDecodeError:
        payload["b64"] = base64.b64encode(other_raw).decode()
    code, said = settle_file(c.get("what") or "workspace", rel, payload, log)
    if code:
        return False
    with contextlib.suppress(OSError):
        os.remove(c["copy"])
    if log:
        log(f"sync: conflict copy {os.path.basename(c['copy'])} settled, main wins: {said}")
    return True


def _folders() -> list[dict]:
    try:
        import sync
        return sync.config().get("folders", [])
    except Exception:
        return []


def main(argv: list[str]) -> int:
    if not argv:
        es = entries()
        print(f"{len(es)} difference{'s' * (len(es) != 1)} kept from both computers" + (":" if es else "."))
        for e in es[:20]:
            print(f"- {e['at']} · {e['file']} · from {e['from']}")
        return 0
    if argv[0] == "file" and len(argv) == 3:
        if os.environ.get("HQ_ROLE_HERE") is None:
            sys.path.insert(0, HERE)
            import role
            if role.is_backup():
                print("Refused: only the main settles; this one is the backup.")
                return 3
        try:
            payload = json.loads(sys.stdin.read() or "{}")
            assert isinstance(payload, dict)
        except (ValueError, AssertionError):
            print("Refused: no payload given.")
            return 2
        code, said = settle_file(argv[1], argv[2], payload)
        print(said)
        return code
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
