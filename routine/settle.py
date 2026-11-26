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
    place) goes to the main through the door (`file`): a file the main doesn't have is written whole, a log of lines
    (.jsonl) gets every line of both, and any other difference leaves the main's file as it is, with the other's
    differing blocks kept word for word in the list (his decision after the check: nothing the main cleaned up comes
    back by itself).
  - Repeats: settling the same file twice is safe by itself (the main runs it again, never answers from memory); a
    part of a big file has an id and a second one does nothing; a settled conflict that comes back is told once (an
    entry in the list has an id; the same difference again adds nothing).

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


def _guard(path: str) -> None:
    """A test never writes his real workspace (F17's rule, for this file too)."""
    if not hqpaths.under_test():
        return
    real = os.path.dirname(os.path.dirname(hqpaths.real_roadmap()))
    p = os.path.realpath(path)
    if real and (p == real or p.startswith(real.rstrip(os.sep) + os.sep)):
        raise PermissionError(f"Refused (F17): a test may not write the real workspace ({path})")


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
    _guard(p)
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


def _heading(lines: list[str], i: int) -> str:
    """The nearest heading above line i ("# …" to "###### …"), or ""."""
    for k in range(min(i, len(lines)) - 1, -1, -1):
        if re.match(r"^#{1,6}\s", lines[k]):
            return lines[k]
    return ""


def _json_blocks(a, b, path: str, who: str) -> list[str]:
    """F115 (the check's finding 3): a JSON file's differences as whole records, word for word (pretty-printed):
    what only the other has, what the other changed, and what isn't in the other's version (named as removed there)."""
    dump = lambda v: json.dumps(v, indent=1, ensure_ascii=False).splitlines()
    name = path or "the whole file"
    if a == b:
        return []
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in list(a) + [k for k in b if k not in a]:
            sub = f"{path}.{k}" if path else str(k)
            if k not in b:
                out += [f"[{sub}: not in {who}'s version, removed there:]", *dump(a[k])]
            elif k not in a:
                out += [f"[{sub}: only on {who}:]", *dump(b[k])]
            elif a[k] != b[k]:
                if isinstance(a[k], (dict, list)) and isinstance(b[k], type(a[k])):
                    out += _json_blocks(a[k], b[k], sub, who)
                else:
                    out += [f"[{sub} as {who} has it:]", *dump(b[k])]
        return out
    if isinstance(a, list) and isinstance(b, list):
        out = []
        for x in b:
            if x not in a:
                out += [f"[a record in {name}, only on {who}:]", *dump(x)]
        for x in a:
            if x not in b:
                out += [f"[a record in {name}, not in {who}'s version, removed there:]", *dump(x)]
        return out
    return [f"[{name} as {who} has it:]", *dump(b)]


def blocks(rel: str, main_text: str, other_text: str, who: str = "the other computer") -> list[str]:
    """F115 (the check's finding 3): every difference of the other's version against the main's, word for word, as
    whole blocks: what's only in the other's under the heading it stands under (the heading copied as it is), and
    what isn't in the other's version named as removed there. A JSON file by its whole records."""
    try:
        a, b = json.loads(main_text), json.loads(other_text)
        if isinstance(a, (dict, list)) and isinstance(b, (dict, list)):
            return _json_blocks(a, b, "", who)
    except ValueError:
        pass
    import difflib
    m, o = main_text.splitlines(), other_text.splitlines()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, m, o, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        added, removed = o[j1:j2], m[i1:i2]
        if not any(l.strip() for l in added + removed):
            continue  # blank lines only
        if [l for l in added if l.strip()]:
            head = _heading(o, j1)
            out.append(f"[only on {who}" + (", under its heading:]" if head and head not in added else ":]"))
            if head and head not in added:
                out.append(head)
            out += added
        if [l for l in removed if l.strip()]:
            head = _heading(m, i1)
            out.append(f"[not in {who}'s version, removed there" + (", under:]" if head and head not in removed else ":]"))
            if head and head not in removed:
                out.append(head)
            out += removed
    return out


def decide(rel: str, main_text: str | None, other_text: str, who: str = "the other computer") -> tuple[str | None, list[str], str]:
    """(what the file becomes, or None to leave it; the other's differences to keep in the list, word for word; how).
    F115, his decision after the check (2 November 2026): the main's file is only written when the main doesn't have
    it at all, or when a log of lines (.jsonl) gets lines the main's doesn't have. Any other difference leaves the
    main's file as it is, so nothing the main cleaned up comes back by itself, and the other's whole differing blocks
    go into the list."""
    if main_text is None:
        return other_text, [], "new here, written whole"
    if main_text == other_text:
        return None, [], "the same"
    if rel.endswith(".jsonl"):
        merged = merge_jsonl(main_text, other_text)
        if merged is not None:
            return (None if merged == main_text else merged), [], "every line of both"
    kept = blocks(rel, main_text, other_text, who)
    if not kept:
        return None, [], "nothing in it the main doesn't have"
    return None, kept, "they differ: the main's stays, the other's differences are kept word for word"


# ---- F195: when the two last agreed ----------------------------------------------------------------------------------
# F195 (7 November 2026): a change made only on the laptop was put aside as a clash and undone, though the main never
# touched the file. The main now remembers, per file, the version both ended with at its last settle (and the versions
# of the other's it put aside); the other sends the version it last had from the main ("base", sync.py). A file only one
# of them changed since they last agreed goes over as it is; only a file both changed is a clash, F115's rule. No
# agreement on record (a file from before this): F115 as before.

AGREED = os.path.join(hqpaths.SUPPORT, "settle-agreed.json")  # on the main: {"WHAT|REL": {"agreed", "aside", "at"}}
ASIDE_MOST = 20


def sha(text: str) -> str:
    return hashlib.sha1(text.encode("utf8")).hexdigest()


def _agreed_all() -> dict:
    try:
        d = json.load(open(AGREED, encoding="utf8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def agreed(what: str, rel: str) -> dict:
    r = _agreed_all().get(f"{what}|{rel}")
    return r if isinstance(r, dict) else {}


def agree(what: str, rel: str, text: str, aside: str | None = None) -> None:
    """Both end with TEXT (the main's file as it is now; the other takes it at its revert); ASIDE: the other's version
    this settle put aside, so the same one sent again never goes over."""
    import hqlock
    os.makedirs(os.path.dirname(AGREED), exist_ok=True)
    with hqlock.locked(AGREED):
        d = _agreed_all()
        k = f"{what}|{rel}"
        was = d.get(k) if isinstance(d.get(k), dict) else {}
        put = [x for x in was.get("aside") or [] if isinstance(x, str)]
        if aside and aside not in put:
            put = (put + [aside])[-ASIDE_MOST:]
        d[k] = {"agreed": sha(text), "aside": put, "at": time.time()}
        tmp = f"{AGREED}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf8") as f:
            json.dump(d, f)
        os.replace(tmp, AGREED)


def since_agreed(rec: dict, base: str | None, main_text: str, other_text: str) -> str | None:
    """F195: who changed the file since the two last agreed: "other" (only the other: its version goes over as it is),
    "main" (only the main: the main's stays, nothing to keep), "aside" (the other's is one the main put aside before),
    or None (no agreement on record, or both changed: F115's rule)."""
    o = sha(other_text)
    if o in (rec.get("aside") or []):
        return "aside"
    bases = {b for b in (rec.get("agreed"), base) if isinstance(b, str) and b}
    if not bases:
        return None
    if sha(main_text) in bases:
        return "other"
    if o in bases:
        return "main"
    return None


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
    try:
        _guard(path)
    except PermissionError as e:
        return 2, str(e)
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
        rec = agreed(what, rel)
        theirs = payload.get("base") if isinstance(payload.get("base"), str) else None  # what the other last had from here
        way = since_agreed(rec, theirs, mine, other) if mine is not None and mine != other else None
        if way == "other":
            new, extra, said = other, [], "only changed there since the two last agreed: it goes over as it is"
        elif way == "main":
            new, extra, said = None, [], "only the main changed it since the two last agreed: the main's stays"
        elif way == "aside":
            new, extra, said = None, [], "settled before: the main's stays, the other's differences are in the list already"
        else:
            new, extra, said = decide(rel, mine, other, who)
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
        # F195: what both end with (the other takes the main's copy at its revert), and the other's put aside
        agree(what, rel, mine if new is None else new, aside=sha(other) if extra or way == "aside" else None)
    if extra:
        keep(rel if ws else f"Claude's memory: {rel}", extra, who,
             f"The two computers had this file differently. The main's version stayed as it is; here is every difference "
             f"of {who}'s, word for word.",
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
    base = os.path.dirname(c["file"])
    for f in _folders():
        if c["file"].startswith(f["path"].rstrip("/") + "/"):
            base = f["path"]
            break
    rel = os.path.relpath(c["file"], base)
    # Which of the two is the main's: Syncthing says who last changed the file as it is now (its short device id);
    # when that's the other computer, the file is the other's version and the copy the main's. (The id in a copy's
    # name isn't a safe guide: on this Syncthing it names the version that won, not the one in the copy.)
    # With one-way sync the main's folder only sends: nothing from the other side ever changes its files, so the file
    # is always the main's. Two-way, the one who changed the file last is the side that won.
    copy_is_main = False
    try:
        import sync
        import urllib.parse
        if sync.one_way_on():
            raise StopIteration
        d = sync.api(f"/rest/db/file?folder={c['folder']}&file={urllib.parse.quote(rel)}")
        by = str(((d or {}).get("local") or {}).get("modifiedBy") or "")
        copy_is_main = bool(by and main_device and file_raw is not None and not main_device.upper().startswith(by.upper()))
    except (Exception, StopIteration):
        pass
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


PART = 45_000  # the status server takes a request of at most 100,000 characters: a bigger file goes in parts


def send(role, args: list[str], payload: dict, hid: str, timeout: float = 120):
    """F115: hand a file's settling to the main (role.hand, never kept here: the next look tries again), in parts when
    it's big, each part with its own id; the last call names how many parts and the hash of the whole, and the main
    writes nothing unless every part is there and the whole matches (the check's finding 5). Returns hand()'s
    (code, out, err, how)."""
    data = json.dumps(payload)
    if len(data) <= 60_000:
        return role.hand("settle", args, keep=False, hid=hid, stdin=data, timeout=timeout)
    b = base64.b64encode(data.encode("utf8")).decode()
    parts = [b[i:i + PART] for i in range(0, len(b), PART)]
    whole = hashlib.sha256(b.encode()).hexdigest()
    r = None
    for again in ("", f"-r{int(time.time())}"):  # parts gone on the main (an old hand-over's): once more, fresh ids
        for i, part in enumerate(parts):
            r = role.hand("settle", ["part", hid, str(i), str(len(parts))], keep=False, hid=f"{hid}{again}-p{i}",
                          stdin=part, timeout=timeout)
            if r[3] != "main" or r[0]:
                return r
        r = role.hand("settle", args + ["--parts", hid, str(len(parts)), whole], keep=False, hid=hid, stdin="",
                      timeout=timeout)
        if r[0] != PARTS_MISSING:
            return r
    return r


PARTS_MISSING = 4


def _parts_dir(hid: str) -> str:
    return os.path.join(hqpaths.SUPPORT, "settle-parts", re.sub(r"[^A-Za-z0-9_-]", "", hid)[:80])


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
    if argv[0] == "override" and len(argv) == 2:
        # F115: the backup has handed over what the main still needed from it; the main's own versions go out as
        # everyone's (Syncthing's override on its send-only folder). Only on the main, only a send-only folder.
        sys.path.insert(0, HERE)
        import role, sync
        if role.is_backup():
            print("Refused: only the main does this.")
            return 3
        f = next((x for x in sync.config().get("folders", []) if x["what"] == argv[1]), None)
        if not f:
            print(f"There's no {argv[1]} folder here.")
            return 1
        try:
            if (sync.api(f"/rest/config/folders/{f['id']}") or {}).get("type") != "sendonly":
                print("Not a send-only folder here; nothing to do.")
                return 0
            sync.api(f"/rest/db/override?folder={f['id']}", "POST", {})
        except Exception as e:
            print(f"Couldn't: {e}")
            return 1
        print(f"The main's {argv[1]} goes out as everyone's.")
        return 0
    if argv[0] == "part" and len(argv) == 4 and argv[2].isdigit() and argv[3].isdigit():
        d = _parts_dir(argv[1])  # a part of a big file, kept until the file itself comes, and two days after
        os.makedirs(d, exist_ok=True)
        top = os.path.dirname(d)
        for n in os.listdir(top):  # the parts of hand-overs that never finished, or finished long ago
            with contextlib.suppress(OSError):
                if time.time() - os.path.getmtime(os.path.join(top, n)) > 2 * 86400:
                    import shutil
                    shutil.rmtree(os.path.join(top, n), ignore_errors=True)
        tmp = os.path.join(d, f"{argv[2]}.{os.getpid()}.tmp")
        with open(tmp, "w") as f:
            f.write(sys.stdin.read())
        os.replace(tmp, os.path.join(d, argv[2]))
        print(f"Part {int(argv[2]) + 1} of {argv[3]} kept.")
        return 0
    if argv[0] == "file" and len(argv) in (3, 7):
        if os.environ.get("HQ_ROLE_HERE") is None:
            sys.path.insert(0, HERE)
            import role
            if role.is_backup():
                print("Refused: only the main settles; this one is the backup.")
                return 3
        parts = argv[4] if len(argv) == 7 and argv[3] == "--parts" and argv[5].isdigit() else None
        try:
            if parts:
                d, n = _parts_dir(parts), int(argv[5])
                if not all(os.path.isfile(os.path.join(d, str(i))) for i in range(n)):
                    print(f"Not whole: some of the {n} parts aren't here.")
                    return PARTS_MISSING
                raw = "".join(open(os.path.join(d, str(i))).read() for i in range(n))
                if hashlib.sha256(raw.encode()).hexdigest() != argv[6]:
                    print("Not whole: the parts don't add up to the file that was sent.")
                    return PARTS_MISSING
                payload = json.loads(base64.b64decode(raw).decode("utf8"))
            else:
                payload = json.loads(sys.stdin.read() or "{}")
            assert isinstance(payload, dict)
        except (OSError, ValueError, AssertionError):
            print("Refused: the file didn't come over whole.")
            return 2
        code, said = settle_file(argv[1], argv[2], payload)
        print(said)
        return code
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
