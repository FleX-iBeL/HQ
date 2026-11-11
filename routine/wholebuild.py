#!/usr/bin/env python3
"""The weight at the back: one builder holds an item, one review over the whole build, one fix round (11 November 2026).

His words (laptop chat, 11 November 2026): "i do want them to stop have diferent jobs that dont remember each other. so back to
basic, what if we make it that multiple items can run at same time, and they do get the whole context from begin to end 1 agent,
and then a second one to review it but the review is over the whole night s build, and then to fix it, and just to make sure its
not broken." The measure (8 to 10 November): QA per item, a cold job each, passed about half the builds the first time, and about
30% of what passed was named again in a newer bug. The run by hand that night (HQ/by-hand/three-items-side-by-side.md): one builder
per item, one reviewer over the whole merged build trying things for real and proving which checks were red before, the findings back
to the same builders, one recheck: three items closed in one fix round.

Behind the backend switch `whole_build_review` (app/backend.py, on by default; a test only with HQ_BACKEND_WHOLE_BUILD_REVIEW=1).
Off, everything is as before: a QA job per built item (qa.on_done), a fail opening the road of a new item (F151).

On:
  1. A build for a row in Bugs or Features that's done (jobs.py done -> qa.on_done -> on_built) queues no "QA of LABEL". The item is
     "built": the build's job, its chat's session (carryon), its record's commits and head are kept here. The line (line.next_step ->
     line_step) waits on it: it isn't sent again while it waits for the review, its fix or its recheck.
  2. The routine's minute (minute): when no build of the team's waits or runs, the line sends none right now, the last build ended a
     few minutes ago (SETTLE) and at least one built item isn't reviewed, ONE review job is queued: "QA of the whole build (review R)",
     kind qa, run as Moneypenny with her QA character (qa.prompt_extra), on the strong model like any team job. Its first prompt is put
     together here (prompt): for each item its full text (sprint.py show), his words, the open points the front left (the heading
     "Open points from the front (not settled):" when it's there), the build's commits, its record and her sealed tests' result; and
     the base, the commit before the first of these builds, so a red check is proved red-before or not. It ends with a verdict per
     item through qa.py pass / qa.py fail (the same marks, so the release gate, the status page and the trail read them as before).
  3. A fail (qa.fail -> on_fail) on an item in this road goes back to the chat that built it: a new job "Fix for LABEL after the
     whole-build review", held as resumed, whose carry-on record (carryon) holds the builder's session, so the routine resumes that
     chat (claude --resume) with the findings as its message. Only when that chat can't be continued (not on this computer, older than
     CHAT_HOURS, its context past CONTEXT_MOST tokens) does it start fresh, and then its first prompt carries the whole item, the
     build's commits and every finding (fresh_note). Once the fixes have landed, ONE recheck (the same review job, the item marked as
     a recheck) runs over only the items that failed, with the files the fixes touched and the other items those files belong to.
     Failing again: held, no third round by itself, one short text to him (qatests.tell), the old road of a new item opened for when
     the hold is lifted (the row's words change, or wholebuild.py lift LABEL). The items that passed go on.
  4. A review job that ends without a verdict for an item (refused pass, nothing written) leaves it for the next review once; twice:
     held, with the text. A check only the laptop can run keeps its road (machalf): the item waits for the laptop's verdict.

The state is HQ's own .status/whole-build.json (HQ_WHOLE_BUILD_STATE; a test's roadmap copy, HQ_ROADMAP, gets one next to it).

    python3 routine/wholebuild.py show                  what's in the road, per item
    python3 routine/wholebuild.py tick                  the routine's minute once (it runs every minute on the main)
    python3 routine/wholebuild.py prompt R              review R's first prompt, as the program puts it together
    python3 routine/wholebuild.py lift LABEL            a held item out of the road: the line takes it as before
    python3 routine/wholebuild.py on SHA -- COMMAND     COMMAND in a throwaway copy of exactly SHA (proof.py's copy), then gone

[Not his: SETTLE 3 minutes, CHAT_HOURS 48, CONTEXT_MOST 150,000 tokens, MOST_MISSED 2, the review's guessed minutes. Claude's choices.]
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402
import jobs as q  # noqa: E402

SWITCH = "whole_build_review"
REVIEW_START = "QA of the whole build"
REVIEW_RE = re.compile(r"^QA of the whole build \(review (\d+)\)")
FIX_MARK = " after the whole-build review"
FIX_RE = re.compile(r"^Fix for ([A-Z]\d+(?:\.\d+)*) after the whole-build review\b")
FIX_STATE = "held: resumed by the whole-build review"
SETTLE = 3 * 60          # seconds after the last build ended before the review is queued
CHAT_HOURS = 48          # a builder's chat older than this isn't continued: a fresh job, fully fed
CONTEXT_MOST = 150_000   # tokens in the builder chat's last turn past which it isn't continued
MOST_MISSED = 2          # reviews that ended without a verdict for an item before it's held
OPEN = ("built", "review", "recheck", "fixing", "fixed", "mac")   # the item is in the road: the line waits
IN_ROAD = OPEN + ("passed",)
FRONT_HEAD = "Open points from the front (not settled):"


def on() -> bool:
    """The switch. A test (HQ_UNDER_TEST) only with HQ_BACKEND_WHOLE_BUILD_REVIEW=1, so the flows from before keep today's road."""
    if hqpaths.under_test():
        return os.environ.get("HQ_BACKEND_WHOLE_BUILD_REVIEW") == "1"
    try:
        sys.path.insert(0, os.path.join(hqpaths.HQ, "app"))
        import backend
        return backend.on(SWITCH)
    except Exception:
        return True


def path() -> str:
    if os.environ.get("HQ_WHOLE_BUILD_STATE"):
        return os.environ["HQ_WHOLE_BUILD_STATE"]
    t = os.environ.get("HQ_ROADMAP")
    if t:
        return os.path.splitext(t)[0] + "-whole-build.json"
    return os.path.join(hqpaths.HQ, ".status", "whole-build.json")


def load() -> dict:
    try:
        with open(path(), encoding="utf8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    d.setdefault("items", {})
    d.setdefault("reviews", {})
    d.setdefault("next", 1)
    return d


def _save(d: dict) -> None:
    p = path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = f"{p}.{os.getpid()}"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)


@contextmanager
def changing():
    """The state, read under its own lock and written back. Always taken after the queue's lock (jobs.locked), never before it."""
    p = path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        d = load()
        yield d
        _save(d)


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def is_review(text: str) -> bool:
    return " ".join((text or "").split()).startswith(REVIEW_START)


def review_id(text: str) -> str | None:
    m = REVIEW_RE.match(" ".join((text or "").split()))
    return m.group(1) if m else None


def fix_label(text: str) -> str | None:
    m = FIX_RE.match(" ".join((text or "").split()))
    return m.group(1) if m else None


# ---------- git, for the base and what the fixes touched ----------

def _root() -> str:
    import proof
    return str(proof.ROOT)


def _git(*a) -> str:
    r = subprocess.run(["git", "-C", _root(), *a], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def _shas(commits) -> list[str]:
    return [c.split()[0] for c in commits or [] if c and c.split()]


def base_of(shas: list[str]) -> str | None:
    """The commit before the oldest of these: the code before the first of these builds. The oldest is one no other of them comes
    before (by ancestry; side by side, branches, by commit time among those)."""
    shas = [s for s in dict.fromkeys(shas) if s and _git("rev-parse", "-q", "--verify", f"{s}^{{commit}}")]
    if not shas:
        return None
    def before(a, b):
        return subprocess.run(["git", "-C", _root(), "merge-base", "--is-ancestor", a, b], capture_output=True).returncode == 0
    first = [s for s in shas if not any(o != s and before(o, s) for o in shas)]
    if len(first) > 1:
        out = _git("log", "--no-walk=unsorted", "--format=%ct %H", *first)
        first = [ln.split()[1] for ln in sorted(out.splitlines()) if len(ln.split()) == 2] or first
    return _git("rev-parse", "--short=12", f"{first[0]}^1") or None


def files_of(shas: list[str]) -> set[str]:
    files = set()
    for s in shas:
        files |= {f for f in _git("show", "--format=", "--name-only", s).splitlines() if f.strip()}
    return files


# ---------- 1. a build done: the item waits for the review ----------

def _build_rec(j: dict) -> dict:
    import carryon
    import proof
    rec = proof.load(j["n"]) or {}
    return {"job": j["n"], "session": (carryon.load(j["n"]) or {}).get("session"), "head": rec.get("head"),
            "commits": rec.get("commits") or [], "at": time.time(), "sayso": j.get("sayso")}


def on_built(j: dict, label: str) -> str:
    """qa.on_done with the switch on (inside jobs.py done, the queue's lock held): no QA job; the item waits for the whole-build review.
    The fix of a failed item (its continuation) makes it "fixed": it waits for its one recheck."""
    b = _build_rec(j)
    with changing() as d:
        e = d["items"].get(label)
        if e and e.get("stage") == "fixing" and e.get("fix_job") == j["n"]:
            e["fixes"].append(b)
            e.update(stage="fixed", at=time.time())
            return f"{label}'s fix is in (job {j['n']}); one recheck of it follows with the next whole-build review."
        keep = e.get("builds") if e and e.get("stage") == "built" else []  # a second build before its review: one road
        d["items"][label] = {"stage": "built", "round": 1, "builds": (keep or []) + [b], "fixes": [], "findings": [], "verdicts": [],
                             "missed": 0, "at": time.time(), "since": _now()}
    return f"{label} waits for the whole-build review (no QA job of its own): one review runs over everything built once the builds are through."


def said_for(n: int) -> str:
    d = load()
    for label, e in d["items"].items():
        if any(b.get("job") == n for b in (e.get("builds") or []) + (e.get("fixes") or [])):
            return f"{label}: {e.get('stage')}"
    return ""


def line_step(row: dict) -> tuple[str, str] | None:
    """line.next_step: what the line does with an item in this road, or None (the line's own steps). Held: until its words change, or lift."""
    if not on():
        return None
    label = row["label"]
    e = load()["items"].get(label)
    if not e:
        return None
    st = e.get("stage")
    if st == "held":
        import sprint as S
        if (e.get("held") or {}).get("fp") and (e["held"]["fp"] != S.ask_fp(row.get("line") or "")):
            lift(label, "its words changed")
            return None
        return "hold", f"held after the whole-build review's one fix round: {q.one_line((e.get('held') or {}).get('what') or '')[:200]}"
    words = {"built": "built; waits for the whole-build review", "review": "built; in the whole-build review",
             "recheck": "fixed; in the whole-build review's recheck", "fixing": "back with its builder after the whole-build review",
             "fixed": "fixed; waits for the whole-build review's recheck", "mac": "waits for the laptop's half of its review"}
    if st in words:
        return "wait", words[st]
    return None


def lift(label: str, why: str = "lifted by hand") -> str:
    with changing() as d:
        e = d["items"].get(label)
        if not e:
            return f"{label} isn't in the whole-build road."
        e.update(stage="out", out=f"{_now()}: {why}")
    return f"{label} is out of the whole-build road ({why}): the line takes it as before (its fix goes the road of a new item)."


# ---------- 3. a verdict ----------

def takes(label: str) -> bool:
    """qa.fail asks: does this item's fail go the whole-build way (back to its builder's chat)?"""
    return on() and (load()["items"].get(label) or {}).get("stage") in IN_ROAD


def on_pass(label: str, job: int | None) -> None:
    """qa.py pass (and the laptop's PASS, machalf): the item is through."""
    if not on():
        return
    with changing() as d:
        e = d["items"].get(label)
        if not e or e.get("stage") not in IN_ROAD:
            return
        e["verdicts"].append({"review": e.get("review"), "state": "passed", "job": job, "at": _now()})
        e["stage"] = "passed"


def _rounds_failed(e: dict) -> int:
    return len({f.get("review") or f"by hand {f.get('at')}" for f in e.get("findings") or []})


def on_fail(label: str, what: str, job: int | None) -> str:
    """qa.fail with the switch on, after its mark, the trail and the open point: back to the builder's chat (round 1), or held (after the recheck)."""
    with q.locked():
        text, jobs, onq = q.read()
        with changing() as d:
            e = d["items"][label]
            rid = e.get("review")
            same = [f for f in e["findings"] if rid and f.get("review") == rid]
            e["findings"].append({"review": rid, "job": job, "at": _now(), "what": " ".join(what.split())})
            e["verdicts"].append({"review": rid, "state": "failed", "job": job, "at": _now()})
            fj = next((x for x in jobs if x["n"] == e.get("fix_job")), None) if same else None
            if fj and not fj["state"].startswith(q.FINISHED):  # a second finding of the same review: to the same fix, as a note
                fj.setdefault("notes", []).append({"at": _now(), "text": q.clean_mark(f"One more finding of the whole-build review: {what}")[:2000]})
                q.write(text, jobs, onq)
                return f"QA failed for {label}: one more finding of the same review, sent to its fix (job {fj['n']}) as a note."
            if _rounds_failed(e) >= 2:
                said = _hold(label, e, what, job)
            else:
                said = None
    if said:
        flush()
        return said
    with q.locked():
        text, jobs, onq = q.read()
        with changing() as d:
            e = d["items"][label]
            rid = e.get("review")
            b = (e.get("fixes") or e.get("builds") or [{}])[-1]
            n = max([x["n"] for x in jobs] + [0]) + 1
            words = q.one_line(what)[:1500]
            jt = (f"Fix for {label}{FIX_MARK} (round 1): {label} on the HQ roadmap, back in the chat of job {b.get('job')} that built it. "
                  f"What the review found: {words}").replace("·", "-").replace("⟪", "(").replace("⟫", ")")
            nj = {"n": n, "state": FIX_STATE, "past": False, "agreed": _now(), "text": jt, "notes": []}
            if b.get("sayso"):  # the same work on the same say-so: by day it starts as its build did
                nj["sayso"] = dict(b["sayso"])
            q.carry(nj, label)
            import qa
            jobs.insert(qa._place(jobs, label), nj)
            q.write(text, jobs, onq)
            e.update(stage="fixing", fix_job=n, round=2, fix_review=rid)
            import carryon
            carryon.save(n, {"session": b.get("session"), "held": time.strftime("%H:%M"), "continues": b.get("job"), "label": label,
                             "step": "the whole-build review's findings"})
    q.estimate("on_add", n, jt, "build")
    return (f"QA failed for {label}: the finding is back in its row as an open point and goes to the chat that built it (job {b.get('job')}), "
            f"as job {n}, a continuation with the findings as its message; then one recheck. No separate fix road.")


def _hold(label: str, e: dict, what: str, job) -> str:
    """Inside changing(): the recheck failed too. Held, no third round, one short text; the old road of a new item opens for after the hold."""
    import sprint as S
    row = S.row_of(label) or {}
    e.update(stage="held", held={"at": _now(), "what": " ".join(what.split()), "fp": S.ask_fp(row.get("line") or "")})
    _later(lambda: __import__("qatests").qa_failed(label, what.rstrip("."), job))  # it takes the queue's lock: after ours are let go
    _tell(e, label, f"{label} still fails after its one fix round in the whole-build review: {q.one_line(what)[:300]}. It's held, no third "
                    "round by itself; the items that passed go on. Changing its words, or wholebuild.py lift, lets it go on the old road.")
    return (f"QA failed for {label} again after its one fix round: held, no third round by itself, one text to him. "
            "The items that passed go on.")


def _tell(e: dict, label: str, words: str) -> None:
    """One text per hold, kept in the state too (a test reads it there)."""
    e.setdefault("told", []).append({"at": _now(), "words": words})
    k = len(e["told"])
    _later(lambda: __import__("qatests").tell(label, f"whole-build-held-{k}", words))


_AFTER: list = []


def _later(fn) -> None:
    """What takes the queue's lock (her road, a text) runs once the locks held here are let go: flush(), or at the process's end
    (jobs.py done holds the queue's lock while it settles a review's end)."""
    if not _AFTER:
        import atexit
        atexit.register(flush)
    _AFTER.append(fn)


def flush() -> None:
    while _AFTER:
        fn = _AFTER.pop(0)
        try:
            fn()
        except Exception as e:
            print(f"(whole build: {e!r})", file=sys.stderr)


# ---------- 2. the review, queued once the builds are through ----------

def _busy_builds(jobs: list) -> list:
    import qa
    import wall
    out = []
    for j in jobs:
        s = j["state"]
        if s.startswith(q.FINISHED) or q.parked(j):
            continue
        t = j.get("text") or ""
        if qa.is_prep(t) or qa.is_qa(t):
            continue
        try:
            if fix_label(t) or wall.is_build(j):
                out.append(j)
        except Exception:
            pass
    return out


def _line_would_send(jobs: list) -> list[str]:
    try:
        import line as L
        import sprint as S
        rows = {r["label"]: r for r in S.open_rows()}
        out = []
        for label, g in S.go_all().items():
            if not g.get("build") or label not in rows:
                continue
            what, _ = L.next_step(rows[label], g, jobs)
            if what in ("send", "resume", "rerun"):
                out.append(label)
        return out
    except Exception:
        return []


def _job(jobs, n):
    return next((x for x in jobs if x["n"] == n), None)


def _settle(d: dict, jobs: list) -> list[str]:
    """Inside changing(): a review job gone without its done mark (stopped, cancelled, dropped) and a fix gone the same way."""
    out = []
    for rid, r in d["reviews"].items():
        if r.get("done"):
            continue
        j = _job(jobs, r.get("job"))
        if j and not j["state"].startswith(q.FINISHED):
            continue
        if j and j["state"].startswith("done"):
            continue  # jobs.py done settles it (review_done)
        out += _review_over(d, rid, why="ended without its done mark")
    for label, e in d["items"].items():
        if e.get("stage") != "fixing":
            continue
        j = _job(jobs, e.get("fix_job"))
        if j and (not j["state"].startswith(q.FINISHED) or j["state"].startswith("done")):
            continue
        if j is None and any(f.get("job") == e.get("fix_job") for f in e.get("fixes") or []):
            continue
        out.append(_hold(label, e, f"its fix (job {e.get('fix_job')}) ended without being done", None))
    return out


def minute(now: float | None = None) -> list[str]:
    """The routine's minute on the main: one review over everything built once the builds are through. Returns what it did."""
    if not on():
        return []
    try:
        import role
        if role.is_backup():
            return []
    except Exception:
        pass
    now = now or time.time()
    with q.locked():
        text, jobs, onq = q.read()
        if not onq or q.PAUSED:
            return []
        with changing() as d:
            said = _settle(d, jobs)
            go = _due(d, jobs, now)
    flush()
    if not go or _line_would_send(jobs):
        return said
    return said + [queue_review()]


def _due(d: dict, jobs: list, now: float) -> bool:
    if any(is_review(j["text"]) and not j["state"].startswith(q.FINISHED) for j in jobs):
        return False
    due = {l: e for l, e in d["items"].items() if e.get("stage") in ("built", "fixed")}
    if not due or _busy_builds(jobs):
        return False
    try:
        import sidebyside
        if sidebyside.waiting_to_merge():  # point 6: the branches come together into dev first
            return False
    except ImportError:
        pass
    return now - max(float(e.get("at") or 0) for e in due.values()) >= SETTLE


def queue_review() -> str:
    import qa
    import sprint as S
    with q.locked():
        text, jobs, onq = q.read()
        with changing() as d:
            due = {l: e for l, e in d["items"].items() if e.get("stage") in ("built", "fixed")}
            if not due:
                return "nothing built to review"
            try:
                order = {l: i for i, l in enumerate(S.order())}
            except Exception:
                order = {}
            labels = sorted(due, key=lambda l: (order.get(l, 10 ** 6), l))
            rid = str(d["next"])
            d["next"] += 1
            first = [l for l in labels if due[l]["stage"] == "built"]
            again = [l for l in labels if due[l]["stage"] == "fixed"]
            base = base_of([s for l in labels for b in due[l]["builds"] for s in _shas(b.get("commits"))])
            jt = (f"{REVIEW_START} (review {rid}): one review over everything built since the last one, each item tried for real on the "
                  f"built code, one verdict per item. " + (f"First looks: {' / '.join(first)}. " if first else "")
                  + (f"Rechecks after the one fix round: {' / '.join(again)}. " if again else "")
                  + "The items, his words, the commits and the records are in the first prompt, put together by the program.")
            n = max([x["n"] for x in jobs] + [0]) + 1
            jobs.append({"n": n, "state": "ready", "past": False, "agreed": _now(), "text": q.one_line(jt).replace("·", "-"), "notes": []})
            q.write(text, jobs, onq)
            d["reviews"][rid] = {"job": n, "items": {l: (2 if l in again else 1) for l in labels}, "at": _now(), "base": base}
            for l in labels:
                due[l].update(stage="recheck" if l in again else "review", review=rid)
                due[l].setdefault("reviews", []).append(rid)
    guess = min(240, 20 + 12 * len(labels) + 35)  # the items, the quick set once
    q.estimate("on_add", n, jt, "qa", None, guess)
    return f"queued the whole-build review {rid} as job {n}: " + ", ".join(labels)


def review_done(j: dict) -> str:
    """jobs.py done of a review job (its lock held): an item it left without a verdict waits for the next one, once; twice, held."""
    rid = review_id(j.get("text") or "")
    if not rid:
        return ""
    with changing() as d:
        out = _review_over(d, rid)
    return "; ".join(out)


def _review_over(d: dict, rid: str, why: str = "") -> list[str]:
    r = d["reviews"].get(rid) or {}
    r["done"] = _now() + (f" ({why})" if why else "")
    out = []
    for label in r.get("items") or {}:
        e = d["items"].get(label) or {}
        if e.get("review") != rid or e.get("stage") not in ("review", "recheck"):
            continue
        if _mac_pending(label):
            e["stage"] = "mac"
            out.append(f"{label} waits for the laptop's half")
            continue
        e["missed"] = int(e.get("missed") or 0) + 1
        if e["missed"] >= MOST_MISSED:
            out.append(_hold(label, e, f"the whole-build review ended {e['missed']} times without a verdict for it", None))
        else:
            e["stage"] = "fixed" if e["stage"] == "recheck" else "built"
            out.append(f"{label}: no verdict in review {rid}; it goes into the next one")
    return out


def _mac_pending(label: str) -> bool:
    try:
        import machalf
        return any(x.get("label") == label and x.get("state") in ("new", "laptop-off", "handed", "writing") for x in machalf._read())
    except Exception:
        return False


# ---------- the review's first prompt ----------

def _front_points(show: str) -> str:
    i = show.find(FRONT_HEAD)
    if i < 0:
        return ""
    rest = show[i + len(FRONT_HEAD):]
    end = re.search(r"\n\n\[\d+\] |\n\n[A-Z]\d+ \(", rest)
    return rest[: end.start() if end else len(rest)].strip()[:4000]


def _record_words(n) -> str:
    import proof
    rec = proof.load(n) or {}
    if not rec:
        return f"job {n}: no record kept"
    qt = rec.get("qa_tests") or {}
    return (f"job {n}: {'green' if rec.get('green') else 'not green'} on {str(rec.get('head') or '?')[:10]}, {rec.get('passed', 0)} of "
            f"{rec.get('ran', 0)} flows passed" + (f", named flows {rec['named']}" if rec.get("named") else "")
            + (f", failed: {'; '.join(rec['failed'])[:400]}" if rec.get("failed") else "")
            + (f"; her sealed tests {'green' if qt.get('green') else 'NOT green'} ({qt.get('passed', 0)} of {qt.get('ran', 0)})"
               + (f": {qt['why']}" if qt.get("why") else "") if qt else "; her sealed tests: none ran"))


def _item_words(label: str, e: dict, rnd: int, d: dict, rid: str) -> str:
    import sprint as S
    show = S.show_words([label])
    row = S.row_of(label) or {}
    his = S.field_texts(row.get("line") or "").get("his_words") if row.get("line") else ""
    commits = list(dict.fromkeys(c for b in (e.get("builds") or []) + (e.get("fixes") or []) for c in b.get("commits") or []))
    parts = [f"=== {label} ({'RECHECK after its one fix round' if rnd == 2 else 'first look'}) ===",
             f"Built by job(s) {', '.join(str(b['job']) for b in e.get('builds') or [])}"
             + (f"; fixed by job(s) {', '.join(str(b['job']) for b in e.get('fixes') or [])}" if e.get("fixes") else "") + ".",
             "The item, whole (sprint.py show):\n" + show,
             "His own words in it: " + (his or "(no His words field in the row)")]
    front = _front_points(show)
    parts.append("Open points from the front (not settled): " + (front if front else "none"))
    parts.append("The build's commits (newest first):\n" + ("\n".join(commits[:40]) if commits else "(none recorded)"))
    parts.append("The build's record and her sealed tests:\n" + "\n".join(_record_words(b["job"]) for b in (e.get("builds") or []) + (e.get("fixes") or [])))
    if rnd == 2:
        parts.append("What the review found before (round 1), now fixed by its builder:\n" + "\n".join(
            f"- {f['at']}: {f['what']}" for f in e.get("findings") or []))
        fix_shas = [s for b in e.get("fixes") or [] for s in _shas(b.get("commits"))]
        built_shas = {s for b in e.get("builds") or [] for s in _shas(b.get("commits"))}
        touched = files_of([s for s in fix_shas if s not in built_shas])
        others = sorted(l for l, x in d["items"].items() if l != label and x.get("stage") in IN_ROAD
                        and touched & files_of([s for b in x.get("builds") or [] for s in _shas(b.get("commits"))]))
        parts.append("Files the fix touched: " + (", ".join(sorted(touched)) if touched else "none found")
                     + (f". Other items of this build in those files, try their done examples again too, and fail one that broke: "
                        f"{', '.join(others)}" if others else "."))
    return "\n\n".join(parts)


def prompt(text: str, n: int | None = None) -> str:
    """The review job's first prompt (after her QA character, qa.prompt_extra): every item and how to end."""
    rid = review_id(text)
    d = load()
    r = d["reviews"].get(rid or "") if rid else None
    if not r:
        return "\n\n(The whole-build review's items couldn't be found in the program's record; read HQ's whole-build.json by hand.)\n"
    items = r.get("items") or {}
    me = "python3"
    wb = os.path.join(HERE, "wholebuild.py")
    jp = f"--job {n}" if n else "--job N"
    head = (
        f"\n\nThis is the whole-build review {rid} (his design, 11 November 2026): one review over everything built since the last one, "
        "in place of a QA job per item. You hold the whole build: the items below were built (and, for a recheck, fixed) one after "
        "another on dev, each by its own builder, and each builder still has its chat; your verdicts go back to them.\n\n"
        "How you work:\n"
        "- Pull dev first (routine/push.py --pull). Build nothing, except a one-line fix in a test when the test itself is wrong (say so).\n"
        "- Try every \"done means\" example of every item for real, the way he would see it, on a copy of the built code: "
        f"{me} {wb} on HEAD -- 'COMMAND' runs COMMAND in a throwaway copy of exactly that commit (the workspace linked, as proof.py's "
        "copy) and removes it after. A second HQ, a phone-sized page, a real command, as QA does.\n"
        "- Run the flows the items name, and the quick set ONCE for the whole build, not once per item: "
        f"{me} {wb} on HEAD -- 'flock ~/hq-fullrun.lock timeout 60m .venv/bin/python app/happy_flows.py --quick' in the background "
        "(run_in_background; a tool call ends at ten minutes), and wait for it.\n"
        f"- For every red check, prove whether it was already red before these builds: run it again on the base, {r.get('base') or '(unknown: the parent of the oldest commit below)'}, "
        f"with {me} {wb} on BASE -- 'COMMAND'. Red there too: not the item's fault; say so in its verdict, by flow and commit. Red only on the "
        "build: name the item whose change made it red.\n"
        "- Look at how the items touch each other: the same files, the same behaviour; one item's change breaking another's example is a "
        "fail of the item that broke it.\n"
        "- End with one verdict PER ITEM, as QA does, the same marks: "
        f"python3 routine/qa.py pass LABEL \"a line on the whole\" {jp} --example \"the row's example\" --ran \"what you ran\" --got \"what came out\" "
        "(every done example, three flags each) --compared \"what you compared on real data, how many of how many\" (F71, F101: refused without them, "
        "or without the green record holding all its commits), or "
        f"python3 routine/qa.py fail LABEL \"what's off, plainly, and how to see it\" {jp}. A fail goes straight back to that item's builder, in "
        "its own chat; it gets one fix round, then one recheck. A check only the Mac can run: say so in qa.py fail (--mac-only --flow N), "
        "the laptop's answer becomes the verdict (F216). An item you can't give a verdict is reviewed once more, then held.\n"
        "- A recheck: only the items marked RECHECK, plus the other items the fix's files belong to (named under it). Rerun your whole set "
        "of checks for them; a still-failing item is held after this, no third round.\n\n"
        f"The items ({len(items)}):\n\n")
    blocks = [_item_words(l, d["items"].get(l) or {}, rnd, d, rid) for l, rnd in items.items()]
    return head + "\n\n".join(blocks) + "\n"


# ---------- 1. the builder's chat continued ----------

def chat_problem(sid: str | None, folder: str | None = None) -> str | None:
    """Why the builder's chat can't be continued, or None: not here, too old, its context too full."""
    import carryon
    if not sid or not carryon.chat_there(sid, folder):
        return "its chat isn't on this computer (it ran on the other one, or is gone)"
    import glob
    files = glob.glob(os.path.join(carryon.projects(), "*", f"{sid}.jsonl"))
    if not files:
        return "its chat isn't on this computer"
    f = max(files, key=os.path.getmtime)
    if time.time() - os.path.getmtime(f) > CHAT_HOURS * 3600:
        return f"its chat is older than {CHAT_HOURS} hours"
    last = 0
    try:
        with open(f, encoding="utf8", errors="replace") as fh:
            for ln in fh:
                if '"usage"' not in ln:
                    continue
                try:
                    u = (json.loads(ln).get("message") or {}).get("usage") or {}
                except ValueError:
                    continue
                last = sum(int(u.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")) or last
    except OSError:
        return "its chat can't be read"
    if last > CONTEXT_MOST:
        return f"its context is full ({last:,} tokens in its last turn, past {CONTEXT_MOST:,})"
    return None


def _findings(label: str) -> list[dict]:
    return (load()["items"].get(label) or {}).get("findings") or []


def resume_prompt(n: int, where: str, plan: dict, job: dict) -> str:
    import carryon
    msg = carryon.load(n).get("message")
    jp = os.path.join(HERE, "jobs.py")
    if msg:  # side by side: bringing it together (sidebyside._send_back), in its own chat
        return (f"let's go again. This is your own chat from job {plan.get('continues')}; the routine picks it up again in {where} as job "
                f"{n}. {msg} From now on this run is job {n}: use {n}, not {plan.get('continues')}, in every command. Read your notes first: "
                f"python3 {jp} notes {n}. As the very last step: python3 {jp} done {n}, nothing after it.")
    label = fix_label(job["text"]) or "the item"
    fs = _findings(label)
    return (f"let's go again. This is your own chat from job {plan.get('continues')}, where you built {label}; the routine (phase L) "
            f"picks it up again in {where} as job {n}. The whole-build review tried {label} for real on the whole build and failed it. "
            "Its findings:\n" + "\n".join(f"- {f['what']}" for f in fs[-3:]) + "\n\n"
            f"Fix what's off so every done example of {label} holds, on the build as it stands now (other items were built after yours: "
            "git pull and git log first, and keep their work whole). This is the one fix round: after it, one recheck, and an item still "
            f"failing is held. From now on this run is job {n}: use {n}, not {plan.get('continues')}, in every command (notes, guess, done). "
            f"Read your notes first and after each step, always before a push: python3 {jp} notes {n} (H283). Same as before: commit, "
            + ("in your own worktree (named below), no push: the program brings it together into dev" if _side(label) else
               "push to dev with push.py after the privacy check") +
            f", write under the {label} row what was fixed, and end; the runner runs the "
            f"record and marks the job done. As the very last step: python3 {jp} done {n}, nothing after it.")


def _side(label: str) -> bool:
    try:
        import sidebyside
        return sidebyside.on() and bool(sidebyside._item_worktree(sidebyside.load(), label))
    except Exception:
        return False


def fresh_note(n: int, plan: dict, job: dict) -> str:
    """A fix whose builder chat can't be continued: everything it needs, in its first prompt."""
    import sprint as S
    label = fix_label(job["text"]) or ""
    e = load()["items"].get(label) or {}
    commits = list(dict.fromkeys(c for b in (e.get("builds") or []) + (e.get("fixes") or []) for c in b.get("commits") or []))
    return (f"\n\nThis is the one fix round of {label} after the whole-build review. Its builder's chat (job {plan.get('continues')}) can't "
            f"be continued, because {plan.get('why') or 'it is gone'}, so you start fresh with everything here.\n\nThe item, whole:\n"
            + S.show_words([label]) + "\n\nThe build's commits (newest first):\n" + ("\n".join(commits[:40]) or "(none recorded)")
            + "\n\nWhat the review found:\n" + "\n".join(f"- {f['at']}: {f['what']}" for f in e.get("findings") or [])
            + "\n\nRead the commits (git show) before you change anything; fix so every done example holds and the other items built "
            "after it stay whole. After this, one recheck; an item still failing is held.")


# ---------- the copy, for the review ----------

def on_copy(sha: str, command: str) -> int:
    import proof
    head = _git("rev-parse", sha) or sha
    wt = proof._copy(head)
    try:
        return subprocess.run(["sh", "-c", command], cwd=wt, env={**os.environ, "HQ_REAL_HQ": hqpaths.HQ}).returncode
    finally:
        proof._uncopy(wt)


def show_words() -> str:
    d = load()
    if not d["items"]:
        return "Nothing in the whole-build road." + ("" if on() else " (The switch is off.)")
    out = [] if on() else ["The switch whole_build_review is off: QA runs per item, as before."]
    for label, e in d["items"].items():
        out.append(f"{label}: {e.get('stage')}, builds {[b.get('job') for b in e.get('builds') or []]}"
                   + (f", fix job {e['fix_job']}" if e.get("fix_job") else "")
                   + (f", reviews {e.get('reviews')}" if e.get("reviews") else "")
                   + (f", held: {e['held']['what'][:120]}" if e.get("stage") == "held" else ""))
    return "\n".join(out)


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "show"
    if cmd == "show":
        print(show_words())
    elif cmd == "tick":
        for x in minute():
            print(x)
    elif cmd == "prompt" and len(argv) > 1:
        r = load()["reviews"].get(argv[1]) or {}
        print(prompt(f"{REVIEW_START} (review {argv[1]})", r.get("job")))
    elif cmd == "lift" and len(argv) > 1:
        print(lift(argv[1].upper()))
    elif cmd == "on" and len(argv) > 3 and argv[2] == "--":
        return on_copy(argv[1], " ".join(argv[3:]))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
