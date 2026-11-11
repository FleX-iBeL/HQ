#!/usr/bin/env python3
"""Builds side by side, each on its own branch, brought together into dev, then the one review (11 November 2026).

His words (10 November 2026): "for the ones that dont impact each other, they can run side by side. we can do as if we have multiple
people in our team, and each can pick up one item MP delegates." and "i like the idea everyone works on it's own branch and merges later
together, maybe we have everyone their own branch, and then merge all together into dev, and then we do the testing and fixing, and then
we push to main once it's all green. if we do the testing and we find bugs, MP needs to hold it against all the items that were built and
merged into that dev, to make sure the final fix is congruent to the total picture." And 11 November: "I do want them simultaneously
running side by side, because I also want to test how it is when they all bring it together, and then there is one test at the end."

Behind the backend switch `side_by_side` (on by default; a test only with HQ_BACKEND_SIDE_BY_SIDE=1), and only with headless jobs
(`headless_jobs`) on the maker's HQ. Off: builds one after another, in HQ's own folder, each pushing to dev, as before.

On:
  - Who runs together (may_go_beside): up to MOST builds at once (3, a setting: "side_by_side_most" in the workspace's HQ/backend.json),
    only builds (a build, a fix or a merge of one), never two of the same item, never an item whose Waits on names a running one (or
    the other way round). Anything else (QA, a prep, an agent's run, research) starts only when nothing runs, as before. The usage gate
    still decides each start, with what the running ones still need added to the new one's need (tick.job_need). No model call judges
    overlap.
  - Each build gets its own worktree (scratch/side/job-N) on its own branch side/job-N cut from dev (prepare), what git doesn't hold
    linked in as proof.py's copies; the builder works and commits there, never in HQ's own folder, pushes nothing; its record
    (proof.py) runs on its branch (HQ_PROOF_ROOT in its runner). Its fix after the whole-build review goes back to the same worktree,
    dev merged into it first.
  - New flows of an item go in their own file, app/flows_items/LABEL.py, which happy_flows.py reads in (one place per item): last night
    every builder added its flow at the same spot of the one big test file and the merge collided twice. A file of its own never collides.
  - Brought together (merge_minute): once no build waits or runs, each built branch is merged into dev in HQ's own folder (git merge
    --no-ff, "LABEL: brought together ..."), in rank order. A collision is aborted (git resolves nothing by hand here; only its own
    automatic merge counts) and goes back to the builder of the item merged later, in its own chat, with both sides named: a merge job
    in its worktree. Once everything is in, dev goes up with push.py (its privacy check, as today) and only then does the one whole-build
    review run (wholebuild._due waits on waiting_to_merge), on the merged code.
  - A worktree goes once its item is through the review (passed, held or out of the road) and its branch is in dev.

State: HQ's .status/side-by-side.json (HQ_SIDE_BY_SIDE_STATE; a test's roadmap copy gets one next to it). Worktrees in HQ_SIDE_DIR
(scratch/side), the repository HQ_SIDE_ROOT (HQ itself).

    python3 routine/sidebyside.py show          the side builds and their branches
    python3 routine/sidebyside.py merge         the bringing together once (the routine's minute does it every minute)

[Not his: MOST 3 is the brief's default; the per-item flow file, the order of merging (the planning's rank) and "the later one
resolves" are Claude's choices.]
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402
import jobs as q  # noqa: E402

SWITCH = "side_by_side"
MOST = 3
MERGE_RE = re.compile(r"^Merge ([A-Z]\d+(?:\.\d+)*) into dev after the side-by-side builds\b")
MERGE_STATE = "held: resumed to bring it together"
WAITING = ("building", "built", "collided", "merging")


def on() -> bool:
    if hqpaths.under_test():
        return os.environ.get("HQ_BACKEND_SIDE_BY_SIDE") == "1"
    try:
        sys.path.insert(0, os.path.join(hqpaths.HQ, "app"))
        import backend
        return backend.on(SWITCH) and backend.on("headless_jobs") and hqpaths.is_maker()
    except Exception:
        return False


def most() -> int:
    v = os.environ.get("HQ_SIDE_BY_SIDE_MOST")
    if not v:
        try:
            sys.path.insert(0, os.path.join(hqpaths.HQ, "app"))
            import backend
            v = backend._read().get("side_by_side_most")
        except Exception:
            v = None
    try:
        return max(1, int(v)) if v else MOST
    except (TypeError, ValueError):
        return MOST


def root() -> str:
    return os.environ.get("HQ_SIDE_ROOT") or hqpaths.HQ


def side_dir() -> str:
    return os.environ.get("HQ_SIDE_DIR") or os.path.join(hqpaths.HQ, "scratch", "side")


def path() -> str:
    if os.environ.get("HQ_SIDE_BY_SIDE_STATE"):
        return os.environ["HQ_SIDE_BY_SIDE_STATE"]
    t = os.environ.get("HQ_ROADMAP")
    if t:
        return os.path.splitext(t)[0] + "-side-by-side.json"
    return os.path.join(hqpaths.HQ, ".status", "side-by-side.json")


def load() -> dict:
    try:
        d = json.load(open(path(), encoding="utf8"))
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    d.setdefault("jobs", {})
    return d


@contextmanager
def changing():
    p = path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        d = load()
        yield d
        tmp = f"{p}.{os.getpid()}"
        json.dump(d, open(tmp, "w", encoding="utf8"), indent=1, ensure_ascii=False)
        os.replace(tmp, p)


def _git(*a, cwd=None, check=False):
    r = subprocess.run(["git", "-C", cwd or root(), *a], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(a)}: {(r.stderr or r.stdout).strip()[:300]}")
    return r


def label_of(job: dict) -> str | None:
    import qa
    return (job.get("item") or {}).get("label") or qa.job_label(job.get("text") or "")


def is_build(job: dict) -> bool:
    """A build, the fix of one after the whole-build review, or bringing one together: what may run beside another."""
    import qa
    import wall
    import wholebuild
    t = job.get("text") or ""
    if qa.is_prep(t) or qa.is_qa(t):
        return False
    try:
        import cycles
        if cycles.is_cycle_job(job):
            return False
    except Exception:
        pass
    return bool(wholebuild.fix_label(t) or MERGE_RE.match(" ".join(t.split())) or wall.is_build(job))


def may_go_beside(cand: dict, running: list) -> str | None:
    """Why CAND doesn't start beside the running jobs, or None. Nothing running: None (the line as before)."""
    if not running:
        return None
    if not on():
        return "one job at a time (side_by_side is off)"
    if len(running) >= most():
        return f"{len(running)} builds run side by side, the most at once ({most()})"
    if not all(is_build(j) for j in running):
        return "a job that isn't a build is running; builds go side by side only with builds"
    if not is_build(cand):
        return "only builds go side by side; it waits until nothing runs"
    label = label_of(cand)
    busy = {label_of(j) for j in running}
    if label and label in busy:
        return f"{label} is being built already"
    try:
        import line as L
        import sprint as S
        row = S.row_of(label) if label else None
        mine = {w for w, _ in L.waits_of(row)} if row else set()
        if mine & busy:
            return f"{label} waits on {', '.join(sorted(mine & busy))}, which is being built: never beside it"
        for b in busy:
            r = S.row_of(b) if b else None
            if r and label in {w for w, _ in L.waits_of(r)}:
                return f"{b}, being built, waits on {label}: never beside it"
    except Exception:
        pass
    return None


# ---------- a build's own branch ----------

def _link(wt: str) -> None:
    for name in ("workspace", "models", ".venv"):
        src = os.path.join(hqpaths.HQ, name)
        if os.path.lexists(src) and not os.path.lexists(os.path.join(wt, name)):
            os.symlink(os.path.realpath(src), os.path.join(wt, name))
    os.makedirs(os.path.join(wt, "scratch"), exist_ok=True)


def _item_worktree(d: dict, label: str) -> dict | None:
    """The newest side worktree of an item that's still there (its fix and its merge go back to it)."""
    got = [e for e in d["jobs"].values() if e.get("label") == label and e.get("state") != "gone" and os.path.isdir(e.get("worktree") or "")]
    return max(got, key=lambda e: e.get("at") or 0) if got else None


def prepare(job: dict) -> dict | None:
    """tick.start of a build with side by side on: its worktree and branch, {"worktree", "branch", "base"}; None when off."""
    if not on() or not is_build(job):
        return None
    n, label = job["n"], label_of(job)
    with changing() as d:
        if str(n) in d["jobs"] and os.path.isdir(d["jobs"][str(n)]["worktree"]):
            e = d["jobs"][str(n)]
            e["state"] = "building"
            return e
        again = _item_worktree(d, label) if label else None
        if again:  # its fix or its merge: the same worktree, with dev merged in first (the others' work, as it now stands)
            r = _git("merge", "--no-edit", "dev", cwd=again["worktree"])
            if r.returncode:
                _git("merge", "--abort", cwd=again["worktree"])
            for x in d["jobs"].values():  # its earlier collided or built run: this one carries it now
                if x.get("worktree") == again["worktree"] and x.get("state") in ("collided", "built"):
                    x["state"] = "superseded"
            e = {**{k: v for k, v in again.items() if k not in ("files", "merge_job", "tip", "merged")}, "job": n, "state": "building",
                 "at": time.time(), "of": again.get("job"), "dev_merged": r.returncode == 0}
            d["jobs"][str(n)] = e
            return e
        wt = os.path.join(side_dir(), f"job-{n}")
        branch = f"side/job-{n}"
        base = _git("rev-parse", "dev", check=True).stdout.strip()
        os.makedirs(side_dir(), exist_ok=True)
        if os.path.isdir(wt):
            shutil.rmtree(wt, ignore_errors=True)
            _git("worktree", "prune")
        _git("worktree", "add", "-q", "-B", branch, wt, base, check=True)
        _link(wt)
        e = {"job": n, "label": label, "worktree": wt, "branch": branch, "base": base, "state": "building", "at": time.time()}
        d["jobs"][str(n)] = e
        return e


def prompt_note(info: dict, job: dict) -> str:
    """What the builder is told about its own copy of HQ."""
    wt, br, label = info["worktree"], info["branch"], info.get("label") or "the item"
    again = info.get("of")
    return (f"\n\nYou build side by side with other builders (his design, 11 November 2026). Your own copy of HQ for this job is "
            f"{wt}, on the branch {br}, cut from dev" + (f" (job {again}'s worktree, with dev merged in)" if again else "") + ". "
            f"Read, edit, run and commit ONLY there (git -C {wt} ...), never in HQ's own folder ({hqpaths.HQ}), and don't pull or push: "
            "the program brings every branch together into dev once the builds are through, and pushes after its privacy check. "
            f"A new flow of {label} goes in its own file, {wt}/app/flows_items/{label}.py (happy_flows.py reads every file there; one "
            "place per item, so the branches don't collide in the big test file); edit happy_flows.py itself only to change an existing flow. "
            "Run flows only under the full-run lock (flock ~/hq-fullrun.lock ...), other builders run theirs on this computer too. "
            "Your record (proof.py) runs on your branch by itself."
            + ("" if info.get("dev_merged", True) else
               f" Dev couldn't be merged into your branch by itself (a collision): first git -C {wt} merge dev, resolve it so both "
               "sides keep working, commit."))


def runner_env(info: dict | None) -> str:
    """The runner's environment for a side build: its record and its done check on its own branch."""
    if not info:
        return ""
    import shlex
    return f"HQ_PROOF_ROOT={shlex.quote(info['worktree'])} HQ_SIDE_WORKTREE={shlex.quote(info['worktree'])} "


# ---------- brought together ----------

def waiting_to_merge() -> bool:
    if not on():
        return False
    return any(e.get("state") in WAITING for e in load()["jobs"].values())


def _jobs_state(jobs: list, n) -> str | None:
    j = next((x for x in jobs if x["n"] == int(n)), None)
    return j["state"] if j else None


def merge_minute(push: bool = True) -> list[str]:
    """Every minute on the main: the side builds' end seen, and once no build waits or runs, each built branch merged into dev."""
    if not on():
        return []
    try:
        import role
        if role.is_backup():
            return []
    except Exception:
        pass
    import wholebuild
    out = []
    with q.locked():
        text, jobs, onq = q.read()
    with changing() as d:
        for n, e in d["jobs"].items():
            if e.get("state") != "building":
                continue
            st = _jobs_state(jobs, n)
            if st and st.startswith("done"):
                e.update(state="built", tip=_git("rev-parse", e["branch"]).stdout.strip())
            elif st is None or st.startswith(("stopped", "cancelled", "ended")):
                e.update(state="dropped", why=st or "gone from the queue")
                out.append(f"job {n} ({e.get('label')}) ended without being done: its branch isn't brought together")
        if wholebuild._busy_builds(jobs):
            _cleanup(d, out)
            return out
        todo = [(n, e) for n, e in d["jobs"].items() if e.get("state") == "built"]
        if not todo:
            _cleanup(d, out)
            return out
        r = _git("status", "--porcelain", "--untracked-files=no")
        here = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        if r.stdout.strip() or here != "dev":
            out.append(f"waits to bring the builds together: HQ's own folder is {'on ' + here if here != 'dev' else 'not clean'}")
            return out
        try:
            import sprint as S
            rank = {l: i for i, l in enumerate(S.order())}
        except Exception:
            rank = {}
        todo.sort(key=lambda x: (rank.get(x[1].get("label"), 10 ** 6), int(x[0])))
        merged = []
        for n, e in todo:
            label = e.get("label") or f"job {n}"
            r = _git("merge", "--no-ff", "--no-edit", "-m", f"{label}: brought together from {e['branch']} (side by side, job {n})", e["branch"])
            if r.returncode == 0:
                e.update(state="merged", merged=_git("rev-parse", "HEAD").stdout.strip(), at_merge=time.time())
                merged.append(label)
                continue
            files = [f for f in _git("diff", "--name-only", "--diff-filter=U").stdout.splitlines() if f.strip()]
            _git("merge", "--abort")
            e.update(state="collided", files=files)
            out.append(_send_back(n, e, files, merged))
        if merged:
            out.append(f"brought together into dev: {', '.join(merged)}")
    if merged and push and not hqpaths.under_test():
        r = subprocess.run([sys.executable, os.path.join(HERE, "push.py")], cwd=root(), capture_output=True, text=True)
        out.append("pushed dev after its privacy check" if r.returncode == 0 else f"dev not pushed: {(r.stdout + r.stderr).strip()[-200:]}")
    return out


def _send_back(n, e: dict, files: list, merged: list) -> str:
    """A collision: the builder of the item merged later resolves it in its own chat (a merge job in its worktree), with both sides."""
    label = e.get("label") or ""
    with q.locked():
        text, jobs, onq = q.read()
        m = max([x["n"] for x in jobs] + [0]) + 1
        both = ", ".join(merged) or "the items merged before it"
        jt = (f"Merge {label} into dev after the side-by-side builds: {label} on the HQ roadmap, back in the chat of job {n} that built it. "
              f"Its branch {e['branch']} collides with dev in {', '.join(files) or 'files git named'} (dev now holds {both}). In its "
              f"worktree {e['worktree']}: git merge dev, resolve so both sides keep working ({label}'s and theirs), run the flows of both, "
              "commit, and end; the program brings it together again.").replace("·", "-")
        nj = {"n": m, "state": MERGE_STATE, "past": False, "agreed": time.strftime("%Y-%m-%d %H:%M"), "text": jt, "notes": []}
        q.carry(nj, label)
        jobs.append(nj)
        q.write(text, jobs, onq)
    import carryon
    rec = carryon.load(int(n))
    carryon.save(m, {"session": rec.get("session"), "held": time.strftime("%H:%M"), "continues": int(n), "label": label,
                     "message": jt, "step": "bringing the builds together"})
    q.estimate("on_add", m, jt, "build")
    e["merge_job"] = m
    return f"{label}'s branch collides with dev in {', '.join(files)}: back to job {n}'s chat as job {m}"


def _cleanup(d: dict, out: list) -> None:
    """A worktree goes once its item is through the review and its branch is in dev."""
    import wholebuild
    wb = wholebuild.load()["items"]
    for n, e in d["jobs"].items():
        if e.get("state") not in ("merged", "dropped"):
            continue
        st = (wb.get(e.get("label") or "") or {}).get("stage")
        if e["state"] == "merged" and st not in ("passed", "held", "out"):
            continue
        if any(x is not e and x.get("worktree") == e.get("worktree") and x.get("state") in WAITING for x in d["jobs"].values()):
            continue
        if os.path.isdir(e.get("worktree") or ""):
            _git("worktree", "remove", "--force", e["worktree"])
            _git("worktree", "prune")
        if e["state"] == "merged":
            _git("branch", "-D", e["branch"])
        e["state"] = "gone"
        out.append(f"job {n}'s worktree is gone ({e.get('label')} {st or 'dropped'})")


def show_words() -> str:
    d = load()
    if not d["jobs"]:
        return "No side builds." + ("" if on() else " (side_by_side is off.)")
    return "\n".join(f"job {n}: {e.get('label')} on {e.get('branch')} ({e.get('state')})" + (f", collided in {e['files']}" if e.get("files") else "")
                     for n, e in d["jobs"].items())


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "show"
    if cmd == "show":
        print(show_words())
    elif cmd == "merge":
        for x in merge_minute():
            print(x)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
