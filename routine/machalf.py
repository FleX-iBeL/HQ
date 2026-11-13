#!/usr/bin/env python3
"""F216 (8 November 2026): a check whose example only runs on a Mac goes to the laptop by itself, never a fail on the server.

Found 8 November 2026: F203's QA (job 9485) failed only because flow 61's Mac half can't run on the server; the laptop chat ran
it by hand on the MacBook (PASS) and a second QA wrote the pass. His words (laptop chat, 8 November 2026, about 23:00): "yes put
them also on this list." What right looks like (the row): when a check needs the Mac, the QA job hands that part to the laptop (the
backup) on its own, runs it there on a throwaway worktree of the same commit, and takes the result into the same verdict; when the
laptop is off, it waits for it and says so, never a fail.

How it goes:
- The QA side (qa.py fail, on a computer that isn't a Mac and is paired with another HQ, routine/role.py): a fail whose only open
  part is a Mac example not run (the words of job 9485: "One example not run, nothing broken ... Not run: the Mac example"), or
  one given with --mac-only, isn't written as a fail. The flow is the one the text names (its `--only N`, else its first "flow N"),
  the commit the row's build ("on HQ's dev as SHA"). It goes to the paired laptop: POST PEER/api/mac-half (x-hq: mac-half).
  - The laptop answers: a watcher (machalf.py watch ID, on its own) asks it for the result every few seconds; the routine's
    minute (tick) asks too, should the watcher be gone. The laptop's PASS writes "QA passed (job N, ...)" with the QA job's own
    words and the laptop's run; its FAIL goes the normal fail road (qa.fail), with the laptop's words.
  - The laptop can't be reached: the row gets "QA waits for the laptop (job N, ...)", the status page says so in the item's own
    entry, nothing lands as a fail, and the routine's minute hands it over as soon as the laptop answers.
- The laptop side (its status server's /api/mac-half, routine/machalf.py serve): a throwaway worktree of exactly that commit
  (fetched from origin when it doesn't have it yet), what git doesn't hold linked in as proof.py does, then
  `app/happy_flows.py --only N` in it; the worktree goes again after the run. An HQ folder without git history (a copy) runs a
  throwaway copy of its own code instead, and says so in its answer.
- Kept on the QA side in .status/mac-half.json (HQ_MAC_HALF_FILE), the laptop's runs in .status/mac-half-runs/ (HQ_MAC_HALF_RUNS).
  The status page shows each check from the last three days and every one still waiting (status/server.mjs, "Checks on the laptop").

usage:
  python3 routine/machalf.py                    the checks handed to the laptop, as the status page says them
  python3 routine/machalf.py tick               hand over what waits for the laptop, ask for what it runs (the routine's minute)
  python3 routine/machalf.py watch ID           ask the laptop for one check's result until it has one (started by qa.py)
  python3 routine/machalf.py serve start|get    the laptop's side, for its status server (JSON on stdin / the id as an argument)
  python3 routine/machalf.py run ID             the laptop's side: one check run on a throwaway worktree (started by serve start)
"""
from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, ".."))
STORE = os.environ.get("HQ_MAC_HALF_FILE") or os.path.join(hqpaths.HQ, ".status", "mac-half.json")
RUNS = os.environ.get("HQ_MAC_HALF_RUNS") or os.path.join(hqpaths.HQ, ".status", "mac-half-runs")
HEADER = "mac-half"
WATCH_FOR = 3 * 3600      # seconds a watcher asks the laptop before it leaves it to the routine's minute [Claude's choice]
RUN_FOR = 45 * 60         # seconds one flow may run on the laptop [Claude's choice: flow 61 takes under a minute]
SHOW_DAYS = 3             # a finished check stays on the status page this many days [Claude's choice]
RETRY_EVERY = int(os.environ.get("HQ_MAC_HALF_RETRY") or 60)  # seconds between two hand-overs to a laptop that was off (the routine's minute)

# A QA's words that its only open part is a Mac example it couldn't run (job 9485's, and plainer ones)
MAC = r"(?:Mac(?:Book)?|macOS)"
NOT_RUN = r"(?:not (?:yet )?(?:run|tried)|can(?:no|')t (?:be )?run|couldn't (?:be )?run|wasn't run|isn't run)"
MAC_NOT_RUN = re.compile(rf"\b{NOT_RUN}\b[^.]{{0,80}}\b{MAC}\b|\b{MAC}\b[^.]{{0,80}}\b{NOT_RUN}\b", re.I)
NOTHING_ELSE = re.compile(rf"\bnothing (?:else )?(?:is )?broken\b|\bonly\b[^.]{{0,60}}\b{MAC}\b|\b{MAC}\b[^.]{{0,40}}\balone\b", re.I)
BUILT_AS = re.compile(r"on HQ's dev as ([0-9a-f]{7,40})\b")
ON_DEV = re.compile(r"\bdev (?:as |at )?([0-9a-f]{7,40})\b")
ONLY = re.compile(r"--only (\d{1,4})\b")
FLOW = re.compile(r"\bflow (\d{1,4})\b", re.I)


# ---------------------------------------------------------------- the store (the QA side)

@contextlib.contextmanager
def _locked():
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    with open(STORE + ".lock", "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        yield


def _read() -> list[dict]:
    try:
        d = json.load(open(STORE, encoding="utf8"))
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _write(items: list[dict]) -> None:
    tmp = f"{STORE}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STORE)


def _update(cid: str, **kv) -> dict | None:
    with _locked():
        items = _read()
        for it in items:
            if it.get("id") == cid:
                it.update(kv)
                _write(items)
                return dict(it)
    return None


def _when(t: float | None = None) -> str:
    d = dt.datetime.fromtimestamp(t or time.time())
    return f"{d.day} {d:%B %Y %H:%M}"


def _clock(t: float) -> str:
    return dt.datetime.fromtimestamp(t).strftime("%H:%M")


# ---------------------------------------------------------------- what's a Mac half

def mac_only(what: str) -> bool:
    """The QA's words say its only open part is a Mac example it couldn't run, and nothing else is off."""
    w = " ".join((what or "").split())
    return bool(MAC_NOT_RUN.search(w) and NOTHING_ELSE.search(w))


def flow_of(what: str, row: str = "") -> int | None:
    m = ONLY.search(what or "") or FLOW.search(what or "") or FLOW.search(row or "")
    return int(m.group(1)) if m else None


def commit_of(row: str, what: str = "") -> str | None:
    m = BUILT_AS.search(row or "") or ON_DEV.search(what or "")
    if m:
        return m.group(1)[:12]
    r = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True)
    top = subprocess.run(["git", "-C", ROOT, "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    ok = r.returncode == 0 and top and os.path.realpath(top) == os.path.realpath(ROOT)
    return r.stdout.strip() if ok else None


def _row(label: str) -> str:
    import qa
    r = qa.rows(qa.q.read()[0]).get(label)
    return r[0] if r else ""


# ---------------------------------------------------------------- the QA side

def _peer() -> dict:
    import role
    return role.config()


def takes(label: str, what: str, job: int | None, force: bool = False, flow: int | None = None) -> str | None:
    """qa.py fail: when the only open part is a Mac half and there's a laptop to run it, it goes there and nothing is failed.
    Returns what to say, or None when it's an ordinary fail (no pairing, this is the Mac, or more than the Mac is off)."""
    if hqpaths.IS_MAC or not (force or mac_only(what)):
        return None
    c = _peer()
    if not c.get("peer"):
        return None
    row = _row(label)
    flow = flow or flow_of(what, row)
    commit = commit_of(row, what)
    if not row or not flow or not commit:
        return None
    it = {"id": uuid.uuid4().hex[:12], "label": label, "job": job, "flow": flow, "commit": commit,
          "what": " ".join(what.split()).rstrip("."), "at": time.time(), "state": "new", "laptop": c.get("peer_name") or "the laptop"}
    with _locked():
        items = _read()
        items = [x for x in items if not (x.get("label") == label and x.get("state") in ("new", "laptop-off", "handed"))]
        items.append(it)
        _write(items)
    it = hand(it["id"]) or it
    if it.get("state") == "handed":
        _watch(it["id"])
        return (f"QA of {label} (job {job}): its only open part, flow {flow}'s Mac half, went to the laptop to run on a throwaway worktree "
                f"of {commit} (F216); its answer goes into this verdict by itself. Nothing is written as a fail.")
    return (f"QA of {label} (job {job}) waits for the laptop: only flow {flow}'s Mac half is left, and the laptop is off or can't be "
            f"reached ({it.get('why') or 'no answer'}). The routine hands it over by itself as soon as the laptop answers; never a fail.")


def hand(cid: str) -> dict | None:
    """One try to hand a check to the laptop. The row says it waits while the laptop is off (once, not every minute)."""
    import role
    it = next((x for x in _read() if x.get("id") == cid), None)
    if not it:
        return None
    c = _peer()
    body = {"id": cid, "label": it["label"], "job": it.get("job"), "flow": it["flow"], "commit": it["commit"],
            "what": f"flow {it['flow']}'s Mac half at {it['commit']}", "from": hqpaths.short_name()}
    try:
        if not c.get("peer"):
            raise RuntimeError("this HQ isn't paired with a laptop any more")
        code, d = role._request(c["peer"].rstrip("/") + "/api/mac-half", body, HEADER, timeout=role.TIMEOUT)
        if code != 200 or not isinstance(d, dict) or not d.get("id"):
            raise RuntimeError(f"it answered {code} without taking it")
    except Exception as e:  # noqa: BLE001 - every way of not reaching it is the laptop being off or unreachable
        why = _why(e)
        first = it.get("state") == "new"
        it = _update(cid, state="laptop-off", why=why, tried=time.time(), line=_wait_line(it, why))
        if first:
            _note_row(it["label"], f"QA waits for the laptop (job {it.get('job') or 'by hand'}, {_when(it['at'])}): only flow "
                                   f"{it['flow']}'s Mac half is left, and the laptop is off or can't be reached; it runs there by itself "
                                   f"on a throwaway worktree of {it['commit']} as soon as the laptop answers (F216), never a fail.")
        return it
    return _update(cid, state="handed", handed=time.time(), why="", line=_handed_line(it, d))


def _why(e: Exception) -> str:
    s = str(getattr(e, "reason", "") or e)
    if "refused" in s.lower():
        return "the connection was refused"
    if "timed out" in s.lower():
        return "it didn't answer in time"
    if "name or service" in s.lower() or "nodename" in s.lower() or "resolve" in s.lower():
        return "its name isn't found on the network"
    return s[:120] or "no answer"


def _wait_line(it: dict, why: str) -> str:
    return (f"{it['label']} · QA (job {it.get('job') or 'by hand'}) waits for the laptop: only flow {it['flow']}'s Mac half is left, and "
            f"the laptop is off or can't be reached ({why}, last tried {_clock(time.time())}). It runs there by itself as soon as the "
            f"laptop answers; nothing is written against the item.")


def _handed_line(it: dict, d: dict) -> str:
    return (f"{it['label']} · QA (job {it.get('job') or 'by hand'}): flow {it['flow']}'s Mac half is on the laptop now, on a throwaway "
            f"worktree of {it['commit']} (since {_clock(time.time())}); its answer goes into the verdict by itself.")


def _watch(cid: str) -> None:
    """The watcher, on its own: asks the laptop until the result is in (its output in scratch/mac-half.log)."""
    os.makedirs(os.path.join(ROOT, "scratch"), exist_ok=True)
    with open(os.path.join(ROOT, "scratch", "mac-half.log"), "a") as log:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "watch", cid], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)


def ask(cid: str) -> dict | None:
    """One question to the laptop about a handed check; writes the verdict when its answer is in. Returns the check as it is now."""
    import role
    it = next((x for x in _read() if x.get("id") == cid), None)
    if not it or it.get("state") != "handed":
        return it
    c = _peer()
    try:
        code, d = role._request(c["peer"].rstrip("/") + "/api/mac-half?id=" + cid, None, HEADER, timeout=role.TIMEOUT)
    except Exception as e:  # noqa: BLE001 - the laptop went off while it ran: asked again later
        return _update(cid, asked=time.time(), why=_why(e))
    if code != 200 or not isinstance(d, dict):
        return _update(cid, asked=time.time())
    if d.get("state") == "gone":  # the laptop doesn't know it (it restarted): handed over again
        _update(cid, state="laptop-off", why="the laptop no longer had it")
        return hand(cid)
    if d.get("state") != "done" or d.get("result") not in ("PASS", "FAIL"):
        return _update(cid, asked=time.time())
    return finish(cid, d)


def finish(cid: str, d: dict) -> dict | None:
    """The laptop's answer into the same verdict: its PASS is the QA's pass, its FAIL the QA's fail with the laptop's words."""
    with _locked():
        items = _read()
        it = next((x for x in items if x.get("id") == cid), None)
        if not it or it.get("state") != "handed":
            return it
        it.update(state="writing")
        _write(items)
    ran = (f"flow {it['flow']} on the laptop {d.get('where') or it.get('laptop')} ({d.get('platform') or 'its system'}): {d['result']} "
           f"in {d.get('seconds', '?')} s, on {d.get('how') or 'a throwaway worktree of ' + it['commit']}")
    if d.get("platform") and d["platform"] != "macOS":
        ran += f"; the laptop isn't a Mac ({d['platform']}), so it ran the flow as it runs there"
    job = it.get("job")
    import qa
    if ran in _row(it["label"]):  # written already by a watcher that stopped before it said so: not twice
        return _update(cid, state="done", result=d["result"], done=time.time(), ran=ran,
                       line=f"{it['label']} · QA (job {job or 'by hand'}): {ran}. In the verdict.")
    if d["result"] == "PASS":
        what = f"{it['what']}. The Mac half, handed to the laptop by itself (F216): {ran}"
        qa.mark(it["label"], True, what, job)
        _passed(it["label"], job)
        line = f"{it['label']} · QA (job {job or 'by hand'}): {ran}. QA passed with it, in the same verdict."
    else:
        tail = " ".join(str(d.get("tail") or "").split())[-300:]
        what = f"{it['what']}. The Mac half, handed to the laptop by itself (F216): {ran}" + (f": {tail}" if tail else "")
        qa.fail(it["label"], what, job)
        line = f"{it['label']} · QA (job {job or 'by hand'}): {ran}. QA failed with it, in the same verdict."
    return _update(cid, state="done", result=d["result"], done=time.time(), line=line, ran=ran)


def _passed(label: str, job: int | None) -> None:
    """What qa.py pass does after its mark (the trail, her road, the replaced rows, the tick on the planning)."""
    import qa
    for step in (lambda: __import__("trail").step(qa.item_id(label), "qa", state="passed", job=job),
                 lambda: __import__("qatests").qa_passed(label), lambda: qa.close_replaced(label), lambda: qa.tick_done(label),
                 lambda: __import__("wholebuild").on_pass(label, job)):
        try:
            step()
        except Exception as e:  # noqa: BLE001 - the verdict stands; the rest is said in the watcher's log
            print(f"after the pass of {label}: {e!r}", file=sys.stderr)


def _note_row(label: str, words: str) -> None:
    """A line at the end of the row's result cell, as qa.mark writes its marks (no pass or fail in it)."""
    import qa
    words = " ".join(words.split()).replace("|", "/")
    with qa.q.locked():
        text, jobs, on = qa.q.read()
        r = qa.rows(text).get(label)
        if not r:
            return
        cells = hqpaths.cells(r[0])
        at = len(cells) - 2 if len(cells) >= 6 else len(cells) - 1
        cells[at] = (cells[at].strip() + " " + words).strip()
        new = hqpaths.join_cells(cells)
        if len(hqpaths.cells(new)) == len(hqpaths.cells(r[0])):
            qa.q.write(text.replace(r[0], new, 1), jobs, on)


def watch(cid: str) -> int:
    end = time.time() + WATCH_FOR
    while time.time() < end and os.path.isdir(os.path.dirname(STORE)):
        it = ask(cid)
        if not it or it.get("state") not in ("handed",):
            return 0
        time.sleep(5)
    return 0


def tick() -> list[str]:
    """The routine's minute: what waits for the laptop is handed over again, what it runs is asked after (the watcher may be gone)."""
    said, now = [], time.time()
    for it in _read():
        st = it.get("state")
        if st == "laptop-off" and now - float(it.get("tried") or 0) >= max(0, RETRY_EVERY - 5):
            it2 = hand(it["id"]) or {}
            if it2.get("state") == "handed":
                _watch(it["id"])
                said.append(f"{it['label']}: flow {it['flow']}'s Mac half went to the laptop")
        elif st == "writing" and now - float(it.get("asked") or it.get("handed") or 0) >= 15 * 60:
            _update(it["id"], state="handed")  # a watcher that stopped while it wrote the verdict: asked again (the row says if it's there)
        elif st == "handed" and now - float(it.get("asked") or it.get("handed") or 0) >= 50:
            it2 = ask(it["id"]) or {}
            if it2.get("state") == "done":
                said.append(f"{it['label']}: the laptop's {it2.get('result')} is in the verdict")
    return said


def page_lines(now: float | None = None) -> list[str]:
    """What the status page says: each check still waiting or running, and the finished ones of the last few days, newest first."""
    now = now or time.time()
    out = []
    for it in sorted(_read(), key=lambda x: -float(x.get("at") or 0)):
        if it.get("state") == "done" and now - float(it.get("done") or 0) > SHOW_DAYS * 86400:
            continue
        if it.get("line"):
            out.append(it["line"])
    return out


# ---------------------------------------------------------------- the laptop side

def _run_file(cid: str) -> str:
    return os.path.join(RUNS, re.sub(r"[^0-9a-f]", "", cid)[:32] + ".json")


def _run_read(cid: str) -> dict | None:
    try:
        return json.load(open(_run_file(cid), encoding="utf8"))
    except (OSError, ValueError):
        return None


def _run_write(cid: str, d: dict) -> None:
    if not os.path.isdir(os.path.dirname(RUNS)):  # its HQ (a throwaway copy) is gone: nothing is made again where it was
        return
    os.makedirs(RUNS, exist_ok=True)
    p = _run_file(cid)
    with open(p + ".tmp", "w", encoding="utf8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(p + ".tmp", p)


def _platform() -> str:
    return {"darwin": "macOS", "linux": "Linux", "win32": "Windows"}.get(sys.platform, sys.platform)


def answer(d: dict) -> dict:
    """The laptop's answer, its result first (what the QA side reads)."""
    out = {}
    if d.get("state") == "done":
        out["said"] = f"flow {d['flow']} on {d.get('where')} ({d.get('platform')}): {d.get('result')} in {d.get('seconds')} s, on {d.get('how')}"
    else:
        out["said"] = f"flow {d.get('flow')} at {d.get('commit')} is under way on {d.get('where')} since {_clock(float(d.get('at') or time.time()))}"
    out.update({k: d.get(k) for k in ("id", "state", "result", "flow", "commit", "where", "platform", "seconds", "how", "tail") if k in d})
    return out


def serve_start(body: dict) -> tuple[int, dict]:
    cid = re.sub(r"[^0-9a-f]", "", str(body.get("id") or ""))[:32]
    flow, commit = body.get("flow"), str(body.get("commit") or "")
    if not cid or not isinstance(flow, int) or not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        return 400, {"error": "a check names its id, its flow (a number) and its commit"}
    was = _run_read(cid)
    if was:  # the same hand-over twice (its answer lost on the way): the first one's run
        return 200, answer(was)
    d = {"id": cid, "state": "started", "flow": flow, "commit": commit, "label": str(body.get("label") or "")[:12],
         "from": str(body.get("from") or "")[:40], "at": time.time(), "where": hqpaths.short_name(), "platform": _platform()}
    _run_write(cid, d)
    os.makedirs(os.path.join(ROOT, "scratch"), exist_ok=True)
    with open(os.path.join(ROOT, "scratch", "mac-half.log"), "a") as log:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "run", cid], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    return 200, answer(d)


def serve_get(cid: str) -> tuple[int, dict]:
    d = _run_read(cid)
    return (200, answer(d)) if d else (200, {"id": cid, "state": "gone"})


def _git_here() -> bool:
    top = subprocess.run(["git", "-C", ROOT, "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    return bool(top) and os.path.realpath(top) == os.path.realpath(ROOT)


LEFT_OUT = {"workspace", "scratch", ".status", ".venv", "models", "HQ", ".git", "__pycache__", "node_modules"}


def _throwaway(commit: str) -> tuple[str, str, str]:
    """(the copy's folder, its HQ, how it was made): a worktree of exactly the commit, or a copy of this HQ's own code without git."""
    base = tempfile.mkdtemp(prefix="mac-half-", dir=os.path.join(ROOT, "scratch"))
    wt = os.path.join(base, "hq")
    if _git_here():
        have = subprocess.run(["git", "-C", ROOT, "cat-file", "-e", commit + "^{commit}"], capture_output=True).returncode == 0
        if not have:
            subprocess.run(["git", "-C", ROOT, "fetch", "-q", "origin", "dev"], capture_output=True, timeout=120)
        r = subprocess.run(["git", "-C", ROOT, "worktree", "add", "-q", "--detach", wt, commit], capture_output=True, text=True)
        if r.returncode:
            shutil.rmtree(base, ignore_errors=True)
            raise RuntimeError(f"no worktree of {commit}: {r.stderr.strip()[:200]}")
        how = f"a throwaway worktree of {commit}"
    else:
        os.makedirs(wt)
        for nm in os.listdir(ROOT):
            if nm in LEFT_OUT:
                continue
            s = os.path.join(ROOT, nm)
            if os.path.isdir(s) and not os.path.islink(s):
                shutil.copytree(s, os.path.join(wt, nm), symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                                ignore_dangling_symlinks=True)
            elif os.path.isfile(s):
                shutil.copy2(s, os.path.join(wt, nm), follow_symlinks=False)
        how = f"a throwaway copy of its own code for {commit} (this HQ folder holds no git history to check the commit out)"
    for nm in ("workspace", "models", ".venv"):
        s = os.path.join(ROOT, nm)
        if os.path.lexists(s) and not os.path.lexists(os.path.join(wt, nm)):
            os.symlink(os.path.realpath(s), os.path.join(wt, nm))
    os.makedirs(os.path.join(wt, "scratch"), exist_ok=True)
    return base, wt, how


def _gone(base: str, wt: str) -> None:
    if _git_here():
        subprocess.run(["git", "-C", ROOT, "worktree", "remove", "--force", wt], capture_output=True)
    shutil.rmtree(base, ignore_errors=True)
    if _git_here():
        subprocess.run(["git", "-C", ROOT, "worktree", "prune"], capture_output=True)


def run(cid: str) -> int:
    d = _run_read(cid)
    if not d or d.get("state") != "started":
        return 0
    t0, base, out, code = time.time(), None, "", 1
    try:
        base, wt, how = _throwaway(d["commit"])
        d["how"] = how
        py = os.path.join(wt, ".venv", "bin", "python")
        r = subprocess.run([py if os.path.exists(py) else sys.executable, "app/happy_flows.py", "--only", str(d["flow"])], cwd=wt,
                           capture_output=True, text=True, timeout=RUN_FOR, stdin=subprocess.DEVNULL)
        out, code = (r.stdout or "") + (r.stderr or ""), r.returncode
    except subprocess.TimeoutExpired:
        out = f"the flow didn't finish in {RUN_FOR // 60} minutes"
    except Exception as e:  # noqa: BLE001
        out, d["how"] = f"couldn't run it: {e}", d.get("how") or "nothing (no throwaway copy could be made)"
    finally:
        if base:
            _gone(base, os.path.join(base, "hq"))
    line = next((ln.strip() for ln in out.splitlines() if re.match(rf"\s*{d['flow']}\s", ln)), "")
    passed = code == 0 and " PASS " in f" {line} "
    d.update(state="done", result="PASS" if passed else "FAIL", seconds=round(time.time() - t0),
             tail=(line if passed else "\n".join(out.strip().splitlines()[-12:]))[-1500:], done=time.time())
    _run_write(cid, d)
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "show"
    if cmd in ("-h", "--help"):
        print(__doc__)
        return 0
    if cmd == "show":
        print("\n".join(page_lines()) or "No check waits for the laptop or ran there lately.")
        return 0
    if cmd == "json":
        print(json.dumps({"lines": page_lines()}, ensure_ascii=False))
        return 0
    if cmd == "tick":
        for s in tick():
            print(s)
        return 0
    if cmd == "watch" and len(argv) > 1:
        return watch(argv[1])
    if cmd == "run" and len(argv) > 1:
        return run(argv[1])
    if cmd == "serve" and len(argv) > 1:
        if argv[1] == "start":
            try:
                body = json.loads(sys.stdin.read() or "{}")
            except ValueError:
                body = {}
            code, d = serve_start(body if isinstance(body, dict) else {})
        else:
            code, d = serve_get(argv[2] if len(argv) > 2 else "")
        print(json.dumps({"code": code, "data": d}, ensure_ascii=False))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
