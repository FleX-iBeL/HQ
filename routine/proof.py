#!/usr/bin/env python3
"""F101, piece 3 of the foundation (30 October 2026): a program, not an agent, passes a build.

His words: "yes exactly, i want here we put it on our roadmap and planning, and then we run these first." The chain he asked
for only works when each step is proven by a program. A build's done used to be a clean exit, and QA's pass a typed form.
Here a program runs the tests on a copy and keeps a record; `jobs.py done` and `qa.py pass` read the record and nothing else.

    python3 routine/proof.py run N       job N's record: the commits, the flows its row names plus the quick set, on a copy
    python3 routine/proof.py show N      the record, as it stands
    python3 routine/proof.py latest ROW  the newest record for a row (F99, H283)
    python3 routine/proof.py run-rows ROW [ROW ...]  F121: the quick set once, each row's own flows, a record per row

A record says what was run and how it came out: {"n", "label", "head", "commits", "named", "ran", "passed", "failed", "green",
"at"}. It stands for the commit it ran on: new commits after it mean a new run. HQ_PROOF_RUNNER is a test's stand-in for the
flows (same arguments, same output); HQ_PROOF_ROOT a test's own HQ repository; HQ_PROOF_DIR its own records folder. While a
test runs (HQ_UNDER_TEST) the gate is off unless HQ_PROOF_ON says it's the gate being tested.

F121 (3 November 2026): items built and checked in a supervised chat, not as jobs, have no record. `run-rows` runs the quick set
once on the commit HQ is on, then each row's own named flows (one group per row), and writes `rows-<run id>-<ROW>.json` for every
row with commits in that commit (`commits_of`, or listed in qa.COMMITS_FOR); a row without any gets no record and is named. Each
is a record as above plus "shared" (the run's id) and "rows" (every row of that run): green only when the shared quick set and that
row's own flows all passed. `latest()` reads it by its "t" like a job's; `jobs.py done` still needs a job's own record. It takes
~/hq-fullrun.lock (HQ_FULLRUN_LOCK for a test's own), the lock the whole quick sets by hand take turns on, so two full runs never
run at once. Exit 0 when every record is green, 1 when one is red, 2 when there was nothing to run.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402
import jobs as q  # noqa: E402
import nightly  # noqa: E402

ROOT = os.environ.get("HQ_PROOF_ROOT") or hqpaths.HQ
BUILDS = ("build", "bigbuild")
_NAMED = re.compile(r"\bflows?\s+((?:\d{1,4}(?:\s*,\s*|\s+and\s+|,\s*and\s+)?)+)", re.I)


def folder() -> str:
    return os.environ.get("HQ_PROOF_DIR") or os.path.join(hqpaths.HQ, ".status", "proofs")


def path(n) -> str:
    return os.path.join(folder(), f"job-{n}.json")


def _git(*a, root=None) -> str:
    return subprocess.run(["git", "-C", str(root or ROOT), *a], capture_output=True, text=True).stdout.strip()


def named_flows(text: str) -> list[int]:
    """The flows a row names: "flow 182", "happy flow 199", "flows 41, 182 and 193"."""
    out: list[int] = []
    for m in _NAMED.finditer(text or ""):
        out += [int(x) for x in re.findall(r"\d+", m.group(1))]
    return sorted(set(out))


def row_of(text: str, label: str | None) -> str:
    if not label:
        return ""
    m = re.search(rf"^\|[^|\n]*\|\s*{re.escape(label)}\b[^\n]*$", text, re.M)
    return m.group(0) if m else ""


def label_of(j: dict) -> str | None:
    if (j.get("item") or {}).get("label"):  # F103: the carried id's row
        return j["item"]["label"]
    import qa
    return qa.job_label(j["text"])


def needs(j: dict) -> bool:
    """Only a build needs a record; a QA, a release or an agent's own run doesn't."""
    import estimate as E
    kind = (E._load_state().get(str(j["n"])) or {}).get("kind") or E.kind_of(j["text"])
    return kind in BUILDS


def gate_on() -> bool:
    return not hqpaths.under_test() or bool(os.environ.get("HQ_PROOF_ON"))


def load(n) -> dict | None:
    try:
        return json.load(open(path(n), encoding="utf8"))
    except (OSError, ValueError):
        return None


def refuses(j: dict, text: str) -> str | None:
    """Why job j can't be marked done, or None. The record must be green and stand for the commit HQ is on."""
    if not gate_on() or not needs(j):
        return None
    rec = load(j["n"])
    if not rec:
        return f"job {j['n']} is a build and has no record: python3 routine/proof.py run {j['n']} runs its tests on a copy."
    if not rec.get("green"):
        return f"job {j['n']}'s tests failed: {'; '.join(rec.get('failed') or [])[:300]}."
    if rec.get("head") != _git("rev-parse", "HEAD"):
        return f"job {j['n']}'s record stands for {str(rec.get('head'))[:7]}, not for the commit HQ is on now: run it again."
    return None


def latest(label: str) -> dict | None:
    """The newest record for a row."""
    best = None
    try:
        names = os.listdir(folder())
    except OSError:
        return None
    for nm in names:
        if not nm.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(folder(), nm), encoding="utf8"))
        except (OSError, ValueError):
            continue
        if d.get("label") == label and (best is None or d.get("t", 0) > best.get("t", 0)):
            best = d
    return best


def keep_say_so(j: dict, said: str) -> None:
    """done without a record, on his own words: the record says so, it stays not green for QA."""
    rec = load(j["n"]) or {"n": j["n"], "label": label_of(j)}
    rec.update({"say_so": " ".join(said.split()), "say_so_at": time.strftime("%Y-%m-%d %H:%M")})
    _save(rec)


def _save(rec: dict, where: str | None = None) -> None:
    os.makedirs(folder(), exist_ok=True)
    where = where or path(rec["n"])
    tmp = where + f".{os.getpid()}"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
    os.replace(tmp, where)


def commits_of(label: str | None) -> list[str]:
    """The commits on this branch that name the row, newest first."""
    if not label:
        return []
    base = "origin/main" if _git("rev-parse", "-q", "--verify", "origin/main") else "main"
    lines = _git("log", "--format=%h %s", f"{base}..HEAD").splitlines()
    return [ln for ln in lines if re.match(rf"^\w+ [^:]*\b{re.escape(label)}\b", ln)][:40]


def _copy() -> str:
    """A throwaway worktree of this commit, with what git doesn't hold linked in. Never his live files' place to write."""
    base = tempfile.mkdtemp(prefix="proof-", dir=os.path.join(hqpaths.HQ, "scratch"))
    wt = os.path.join(base, "hq")
    r = subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "-q", "--detach", wt, "HEAD"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"no copy: {r.stderr.strip()[:200]}")
    for name in ("workspace", "models", ".venv"):
        src = os.path.join(hqpaths.HQ, name)
        if os.path.lexists(src) and not os.path.lexists(os.path.join(wt, name)):
            os.symlink(os.path.realpath(src), os.path.join(wt, name))
    os.makedirs(os.path.join(wt, "scratch"), exist_ok=True)
    return wt


def _flows(wt: str, args: list[str], log) -> tuple[int, str]:
    runner = os.environ.get("HQ_PROOF_RUNNER")
    cmd = [runner] if runner else [nightly._python(), os.path.join(wt, "app", "happy_flows.py")]
    # F111: the flows run behind the wall from the copy, and answer for the real HQ; this record's own log is written meanwhile
    env = {**os.environ, "HQ_REAL_HQ": hqpaths.HQ, "HQ_WALL_OWN": os.path.realpath(getattr(log, "name", "") or os.devnull)}
    r = subprocess.run(cmd + args, cwd=wt, capture_output=True, text=True, env=env)
    out = r.stdout + r.stderr
    log.write(out)
    return r.returncode, out


def run(n: int) -> int:
    text, jobs, _ = q.read()
    j = next((x for x in jobs if x["n"] == n), None)
    if not j:
        print(f"No job {n}.")
        return 2
    if subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet", "HEAD"]).returncode:
        print("HQ has changes that aren't committed: commit them first; a record stands for a commit.")
        return 2
    label = label_of(j)
    rowtext = (j["text"] + " " + row_of(text, label))
    named = named_flows(rowtext)
    head = _git("rev-parse", "HEAD")
    rec = {"n": n, "label": label, "item": (j.get("item") or {}).get("id"), "head": head, "commits": commits_of(label), "named": named, "ran": 0, "passed": 0,
           "failed": [], "green": False, "at": time.strftime("%Y-%m-%d %H:%M"), "t": time.time()}
    wt = _copy()
    logpath = path(n)[:-5] + ".log"
    os.makedirs(folder(), exist_ok=True)
    import wall
    wall.proof_start(n)  # F100: the box counts the job's own work, not the test run that proves it
    try:
        with open(logpath, "w", encoding="utf8") as log:
            if named:
                # F105: a flow with Claude turns needs a live voice and usage; a row that only mentions one doesn't turn the record red
                code, out = _flows(wt, ["--quick", "--only", ",".join(map(str, named))], log)
                p, r_ = nightly.summary(out)
                rec["ran"], rec["passed"] = r_, p
                rec["failed"] = nightly.failures(out) or ([] if code == 0 else [f"the named flows {named} ended with exit {code}, {p} of {r_}"])
            if not rec["failed"]:
                code, out = _flows(wt, nightly.flow_args(), log)
                p, r_ = nightly.summary(out)
                rec["ran"] += r_
                rec["passed"] += p
                rec["failed"] = nightly.failures(out) or ([] if code == 0 and r_ else [f"the quick set ended with exit {code}, {p} of {r_}"])
        rec["green"] = not rec["failed"] and rec["ran"] > 0 and rec["passed"] == rec["ran"]
    finally:
        wall.proof_end(n)
        subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", wt], capture_output=True)
        shutil.rmtree(os.path.dirname(wt), ignore_errors=True)
    _save(rec)
    print(f"Job {n}: {rec['passed']} of {rec['ran']} passed on a copy of {head[:7]}"
          + (f", named flows {named}" if named else "") + (": green." if rec["green"] else f". Failed: {'; '.join(rec['failed'])[:600]}"))
    return 0 if rec["green"] else 1


def lock_path() -> str:
    """The lock the full runs take turns on. A test never waits on the real one: a quick set held by hand runs this too."""
    if os.environ.get("HQ_FULLRUN_LOCK"):
        return os.environ["HQ_FULLRUN_LOCK"]
    if hqpaths.under_test():
        os.makedirs(folder(), exist_ok=True)
        return os.path.join(folder(), ".fullrun.lock")
    return os.path.expanduser("~/hq-fullrun.lock")


def listed_commits(label: str) -> list[str]:
    """F121: the commits qa.COMMITS_FOR gives this row that are on this branch, written as commits_of writes them."""
    import qa
    base = "origin/main" if _git("rev-parse", "-q", "--verify", "origin/main") else "main"
    out = []
    for sha, entry in qa.COMMITS_FOR.items():
        if entry.get("row") != label:
            continue
        if subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", sha, "HEAD"], capture_output=True).returncode:
            continue
        if not subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", sha, base], capture_output=True).returncode:
            continue  # already on the release line, which commits_of leaves out too
        if qa.listed_row(str(ROOT), sha)[0] == label:
            out.append(_git("log", "-1", "--format=%h %s", sha))
    return out


def run_rows(labels: list[str]) -> int:
    """F121: one run on the commit HQ is on stands as the proof for every row it holds."""
    import fcntl
    import qa
    labels = list(dict.fromkeys(x.upper() for x in labels))
    bad = [x for x in labels if not qa.LABEL.fullmatch(x)]
    if not labels or bad:
        print("Which rows? Give their labels, like F121" + (f": not {', '.join(bad)}." if bad else "."))
        return 2
    lock = open(lock_path(), "a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(f"Another full run holds {lock_path()}: waiting for it.", flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
    try:  # what's in the commit is read once it's this run's turn: HQ may have moved on while it waited
        if subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet", "HEAD"]).returncode:
            print("HQ has changes that aren't committed: commit them first; a record stands for a commit.")
            return 2
        text = q.read()[0]
        rows, none = {}, []
        for label in labels:
            commits = commits_of(label)
            commits += [c for c in listed_commits(label) if c not in commits]
            if commits:
                rows[label] = {"commits": commits, "named": named_flows(row_of(text, label))}
            else:
                none.append(label)
        if none:
            print(f"No commits in this commit for {', '.join(none)}: no record for {'it' if len(none) == 1 else 'them'}.")
        if not rows:
            print("Nothing to run.")
            return 2
        head = _git("rev-parse", "HEAD")
        runid = time.strftime("%Y%m%d-%H%M%S") + "-" + head[:7]
        at, t = time.strftime("%Y-%m-%d %H:%M"), time.time()
        own_job = os.environ.get("HQ_JOB") or ""
        key = own_job or f"rows-{runid}"  # a job that runs it keeps its box still, as with its own run
        shared = {"ran": 0, "passed": 0, "failed": []}
        wt = _copy()
        os.makedirs(folder(), exist_ok=True)
        import wall
        wall.proof_start(key)
        try:
            with open(os.path.join(folder(), f"rows-{runid}.log"), "w", encoding="utf8") as log:
                code, out = _flows(wt, nightly.flow_args(), log)
                p, r_ = nightly.summary(out)
                shared.update(ran=r_, passed=p, failed=nightly.failures(out)
                              or ([] if code == 0 and r_ else [f"the quick set ended with exit {code}, {p} of {r_}"]))
                for label, row in rows.items():
                    row.update(ran=0, passed=0, failed=[])
                    if row["named"]:
                        code, out = _flows(wt, ["--quick", "--only", ",".join(map(str, row["named"]))], log)
                        p, r_ = nightly.summary(out)
                        row.update(ran=r_, passed=p, failed=nightly.failures(out)
                                   or ([] if code == 0 else [f"the named flows {row['named']} ended with exit {code}, {p} of {r_}"]))
        finally:
            wall.proof_end(key)
            if not own_job:
                wall.forget(key)
            subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", wt], capture_output=True)
            shutil.rmtree(os.path.dirname(wt), ignore_errors=True)
        sgreen = not shared["failed"] and shared["ran"] > 0 and shared["passed"] == shared["ran"]
        red = 0
        for label, row in rows.items():
            ran, passed = shared["ran"] + row["ran"], shared["passed"] + row["passed"]
            failed = shared["failed"] + row["failed"]
            green = sgreen and not row["failed"] and row["passed"] == row["ran"]
            rec = {"n": None, "label": label, "item": None, "head": head, "commits": row["commits"][:40], "named": row["named"],
                   "ran": ran, "passed": passed, "failed": failed, "green": green, "at": at, "t": t, "shared": runid, "rows": list(rows)}
            _save(rec, os.path.join(folder(), f"rows-{runid}-{label}.json"))
            red += not green
            print(f"{label}: {passed} of {ran} passed on a copy of {head[:7]}" + (f", named flows {row['named']}" if row["named"] else "")
                  + (": green." if green else f". Failed: {'; '.join(failed)[:600]}"))
        print(f"One run ({runid}): the quick set {shared['passed']} of {shared['ran']}, {len(rows)} record{'' if len(rows) == 1 else 's'}"
              + (f", {red} red." if red else ", all green."))
        return 1 if red else 0
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "run" and argv[1].isdigit():
        return run(int(argv[1]))
    if len(argv) >= 2 and argv[0] == "run-rows":
        return run_rows(argv[1:])
    if len(argv) == 2 and argv[0] == "show" and argv[1].isdigit():
        print(json.dumps(load(argv[1]) or {}, indent=1, ensure_ascii=False))
        return 0
    if len(argv) == 2 and argv[0] == "latest":
        print(json.dumps(latest(argv[1].upper()) or {}, indent=1, ensure_ascii=False))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
