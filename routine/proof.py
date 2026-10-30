#!/usr/bin/env python3
"""F101, piece 3 of the foundation (30 October 2026): a program, not an agent, passes a build.

His words: "yes exactly, i want here we put it on our roadmap and planning, and then we run these first." The chain he asked
for only works when each step is proven by a program. A build's done used to be a clean exit, and QA's pass a typed form.
Here a program runs the tests on a copy and keeps a record; `jobs.py done` and `qa.py pass` read the record and nothing else.

    python3 routine/proof.py run N       job N's record: the commits, the flows its row names plus the quick set, on a copy
    python3 routine/proof.py show N      the record, as it stands
    python3 routine/proof.py latest ROW  the newest record for a row (F99, H283)

A record says what was run and how it came out: {"n", "label", "head", "commits", "named", "ran", "passed", "failed", "green",
"at"}. It stands for the commit it ran on: new commits after it mean a new run. HQ_PROOF_RUNNER is a test's stand-in for the
flows (same arguments, same output); HQ_PROOF_ROOT a test's own HQ repository; HQ_PROOF_DIR its own records folder. While a
test runs (HQ_UNDER_TEST) the gate is off unless HQ_PROOF_ON says it's the gate being tested.
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


def _save(rec: dict) -> None:
    os.makedirs(folder(), exist_ok=True)
    tmp = path(rec["n"]) + f".{os.getpid()}"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(rec, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path(rec["n"]))


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
    r = subprocess.run(cmd + args, cwd=wt, capture_output=True, text=True)
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
    rec = {"n": n, "label": label, "head": head, "commits": commits_of(label), "named": named, "ran": 0, "passed": 0,
           "failed": [], "green": False, "at": time.strftime("%Y-%m-%d %H:%M"), "t": time.time()}
    wt = _copy()
    logpath = path(n)[:-5] + ".log"
    os.makedirs(folder(), exist_ok=True)
    try:
        with open(logpath, "w", encoding="utf8") as log:
            if named:
                code, out = _flows(wt, ["--only", ",".join(map(str, named))], log)
                p, r_ = nightly.summary(out)
                rec["ran"], rec["passed"] = r_, p
                rec["failed"] = nightly.failures(out) or ([] if code == 0 and r_ else [f"the named flows {named} ended with exit {code}, {p} of {r_}"])
            if not rec["failed"]:
                code, out = _flows(wt, nightly.flow_args(), log)
                p, r_ = nightly.summary(out)
                rec["ran"] += r_
                rec["passed"] += p
                rec["failed"] = nightly.failures(out) or ([] if code == 0 and r_ else [f"the quick set ended with exit {code}, {p} of {r_}"])
        rec["green"] = not rec["failed"] and rec["ran"] > 0 and rec["passed"] == rec["ran"]
    finally:
        subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", wt], capture_output=True)
        shutil.rmtree(os.path.dirname(wt), ignore_errors=True)
    _save(rec)
    print(f"Job {n}: {rec['passed']} of {rec['ran']} passed on a copy of {head[:7]}"
          + (f", named flows {named}" if named else "") + (": green." if rec["green"] else f". Failed: {'; '.join(rec['failed'])[:600]}"))
    return 0 if rec["green"] else 1


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[0] == "run" and argv[1].isdigit():
        return run(int(argv[1]))
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
