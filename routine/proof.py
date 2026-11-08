#!/usr/bin/env python3
"""F101, piece 3 of the foundation (30 October 2026): a program, not an agent, passes a build.

His words: "yes exactly, i want here we put it on our roadmap and planning, and then we run these first." The chain he asked
for only works when each step is proven by a program. A build's done used to be a clean exit, and QA's pass a typed form.
Here a program runs the tests on a copy and keeps a record; `jobs.py done` and `qa.py pass` read the record and nothing else.

    python3 routine/proof.py run N       job N's record: the commits, the flows its row names plus the 17 happy flows, on a copy
    python3 routine/proof.py show N      the record, as it stands
    python3 routine/proof.py latest ROW  the newest record for a row (F99, H283)
    python3 routine/proof.py run-rows ROW [ROW ...]  F121: the 17 happy flows once, each row's own flows, a record per row

H342 (8 November 2026): her sealed tests' run (qatests.end_run) also runs the sealed tests of the items this build touches, each on its
own copy; a red one is in "qa_tests" (its "neighbours", "neighbours_red") and makes the record red, and their rows' flows ("around")
run with the row's own named flows.

H313 (4 November 2026): the gate is the 17 happy flows he asked for (routine/happy.py), run for real with the real model, plus the
row's own flows, also for real (no --quick: a pass with stand-ins isn't a pass). The detailed flows (the quick set) run at night, in
routine/nightly.py, no longer here. A happy flow that can't be driven yet is a "not tried" line in the record (rec["not_tried"]), and
a record with one isn't green: it holds QA and the release until it's run for real.

A record says what was run and how it came out: {"n", "label", "head", "commits", "named", "ran", "passed", "failed", "green",
"at"}. It stands for the commit it ran on: new commits after it mean a new run. HQ_PROOF_RUNNER is a test's stand-in for the
flows (same arguments, same output); HQ_PROOF_ROOT a test's own HQ repository; HQ_PROOF_DIR its own records folder. While a
test runs (HQ_UNDER_TEST) the gate is off unless HQ_PROOF_ON says it's the gate being tested.

F165 (7 November 2026): HQ_PROOF_EXCUSED, flow numbers with commas, set only by the line (routine/line.py) when it runs a parked
build's record step again, names flows already on the planning as their own items, checks unrelated to the build's row: such a
flow's failure, when the row doesn't name it, doesn't hold the record ("excused" in the record, next to "failed"). His row: "a
real-model check that fails for a reason outside the item doesn't hold that item's build but becomes its own item."

F121 (3 November 2026): items built and checked in a supervised chat, not as jobs, have no record. `run-rows` runs the quick set
once on the commit HQ is on, then each row's own named flows (one group per row), and writes `rows-<run id>-<ROW>.json` for every
row with commits in that commit (`commits_of`, or listed in qa.COMMITS_FOR); a row without any gets no record and is named. Each
is a record as above plus "shared" (the run's id) and "rows" (every row of that run): green only when the shared happy flows (H313; the quick set before) and that
row's own flows all passed. `latest()` reads it by its "t" like a job's; `jobs.py done` still needs a job's own record. It takes
~/hq-fullrun.lock (HQ_FULLRUN_LOCK for a test's own), the lock the whole quick sets by hand take turns on, so two full runs never
run at once. Exit 0 when every record is green, 1 when one is red, 2 when there was nothing to run.

How it's started: alone (`.venv/bin/python routine/proof.py run-rows F120 F97`), or the house way, wrapped in that lock and a time
limit: `flock ~/hq-fullrun.lock timeout 60m .venv/bin/python routine/proof.py run-rows F120 F97`. Wrapped, it sees the lock its
wrapper holds (the open file flock hands down) and goes on; with `flock -o`, which hands nothing down, the wrapper sets
HQ_FULLRUN_HELD=1. Either way it never waits on a lock its own parent holds.

F121, second round: a record names the commit it tested. The commit is read first, the copy made of exactly that commit and the
row's commits read up to it. A stop (the time limit's SIGTERM, a hang-up, Ctrl-C) is a normal end: the flows' own process group
is stopped, the copy removed from git and from scratch, the clock's "since" cleared, no record written (exit 143). What a kill
can't clean is cleaned by the next run, at its start: copies whose run is gone (their owner.json names a dead pid) are removed,
their flows stopped if still running there, `git worktree prune` run, and a rows run's clock file of a dead pid removed. A named
flow the quick set skips (a Claude flow) is kept under "skipped", not counted as ran.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402
import jobs as q  # noqa: E402
import nightly  # noqa: E402
import happy  # noqa: E402  (H313: the 17 happy flows are the gate)

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
    """Only a build needs a record; a QA, a release, a prep (H342: getting an item ready, her tests rewritten and sealed among it; its
    words read like a build's, its kind may say build) or an agent's own run doesn't."""
    import qa
    if qa.is_prep(j.get("text") or ""):
        return False
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


def _base() -> str:
    return "origin/main" if _git("rev-parse", "-q", "--verify", "origin/main") else "main"


def commits_of(label: str | None, head: str = "HEAD") -> list[str]:
    """The commits on this branch up to head that name the row, newest first."""
    if not label:
        return []
    lines = _git("log", "--format=%h %s", f"{_base()}..{head}").splitlines()
    return [ln for ln in lines if re.match(rf"^\w+ [^:]*\b{re.escape(label)}\b", ln)][:40]


class Stopped(Exception):
    """F121: a stop (SIGTERM, SIGHUP) turned into a normal end, so every finally runs."""


def _stop(signum, _frame):
    for sig in (signal.SIGTERM, signal.SIGHUP):  # one stop is enough: a second must not cut the cleanup short
        signal.signal(sig, signal.SIG_IGN)
    raise Stopped(signal.Signals(signum).name)


def _on_stop() -> dict:
    """The stop signals turned into Stopped for this run; the old handlers back with _off_stop."""
    was = {}
    for sig in (signal.SIGTERM, signal.SIGHUP):
        try:
            was[sig] = signal.signal(sig, _stop)
        except (ValueError, OSError):  # not the main thread: leave it
            pass
    return was


def _off_stop(was: dict) -> None:
    for sig, h in was.items():
        try:
            signal.signal(sig, h)
        except (ValueError, OSError):
            pass


def _alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


STALE_NO_OWNER = 6 * 3600  # a copy from before owner.json counts as left behind after this long


def clean_stale() -> list[str]:
    """F121: what a killed run left: its copy (in git and in scratch), its flows still running there, its clock's since."""
    gone = []
    scratch = os.path.join(hqpaths.HQ, "scratch")
    try:
        names = [n for n in os.listdir(scratch) if n.startswith("proof-")]
    except OSError:
        names = []
    for nm in names:
        base = os.path.join(scratch, nm)
        try:
            own = json.load(open(os.path.join(base, "owner.json"), encoding="utf8"))
        except (OSError, ValueError):
            own = None
        if own is not None:
            if _alive(own.get("pid")):
                continue
        else:
            try:
                if time.time() - os.path.getmtime(base) < STALE_NO_OWNER:
                    continue
            except OSError:
                continue
        wt = os.path.join(base, "hq")
        grp = (own or {}).get("group")
        if grp and _alive(grp):
            try:  # only a group whose leader still works in that copy: never a pid that came back as something else
                if os.path.realpath(os.readlink(f"/proc/{int(grp)}/cwd")).startswith(os.path.realpath(base)):
                    os.killpg(int(grp), signal.SIGKILL)
            except (OSError, ValueError):
                pass
        subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", wt], capture_output=True)
        shutil.rmtree(base, ignore_errors=True)
        gone.append(nm)
    subprocess.run(["git", "-C", str(ROOT), "worktree", "prune"], capture_output=True)
    try:
        import wall
        d = wall._dir()
        for nm in os.listdir(d):
            m = re.fullmatch(r"job-rows-.*-(\d+)-proof-time\.json", nm)
            if m and not _alive(m.group(1)):
                os.remove(os.path.join(d, nm))
    except Exception:
        pass
    return gone


def _owner(wt: str, **kv) -> None:
    p = os.path.join(os.path.dirname(wt), "owner.json")
    try:
        d = json.load(open(p, encoding="utf8"))
    except (OSError, ValueError):
        d = {}
    d.update(kv)
    with open(p + ".tmp", "w", encoding="utf8") as f:
        json.dump(d, f)
    os.replace(p + ".tmp", p)


def _copy(head: str = "HEAD") -> str:
    """A throwaway worktree of exactly this commit, with what git doesn't hold linked in. Never his live files' place to write.
    Its owner.json names the run (and, while they run, the flows' process group) so a later run knows it's left behind."""
    base = tempfile.mkdtemp(prefix="proof-", dir=os.path.join(hqpaths.HQ, "scratch"))
    wt = os.path.join(base, "hq")
    _owner(wt, pid=os.getpid(), head=head)
    r = subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "-q", "--detach", wt, head], capture_output=True, text=True)
    if r.returncode:
        shutil.rmtree(base, ignore_errors=True)
        raise RuntimeError(f"no copy: {r.stderr.strip()[:200]}")
    for name in ("workspace", "models", ".venv"):
        src = os.path.join(hqpaths.HQ, name)
        if os.path.lexists(src) and not os.path.lexists(os.path.join(wt, name)):
            os.symlink(os.path.realpath(src), os.path.join(wt, name))
    os.makedirs(os.path.join(wt, "scratch"), exist_ok=True)
    _job_logs(wt)
    return wt


def _job_logs(wt: str) -> None:
    """F173: the finished jobs' logs, copied (not linked: the copy never writes his live files) from the working HQ, the one the
    workspace is in. A research answer gives a job's log as its source, and her tests look it up there, as the team's run does."""
    live = os.path.join(os.path.dirname(os.path.realpath(os.path.join(hqpaths.HQ, "workspace"))), "scratch", "routine")
    dst = os.path.join(wt, "scratch", "routine")
    try:
        names = [n for n in os.listdir(live) if re.fullmatch(r"job-\d+\.stream\.log", n)]
    except OSError:
        return
    os.makedirs(dst, exist_ok=True)
    for n in names:
        try:
            shutil.copy2(os.path.join(live, n), os.path.join(dst, n))
        except OSError:
            pass


def _uncopy(wt: str) -> None:
    subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", wt], capture_output=True)
    shutil.rmtree(os.path.dirname(wt), ignore_errors=True)
    subprocess.run(["git", "-C", str(ROOT), "worktree", "prune"], capture_output=True)


def _killgroup(p) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(p.pid, sig)
        except OSError:
            return
        try:
            p.wait(timeout=5)
            if sig == signal.SIGTERM:
                time.sleep(0.2)  # the group's others, a moment to go
        except subprocess.TimeoutExpired:
            pass


def _known_flows(wt: str) -> set[int]:
    """F188: the flow numbers the copy's happy_flows.py has (its FLOWS entries); empty when it can't be read."""
    try:
        with open(os.path.join(wt, "app", "happy_flows.py"), encoding="utf8") as f:
            return {int(x) for x in re.findall(r"(?m)^    (\d+): \(", f.read())}
    except OSError:
        return set()


def _flows(wt: str, args: list[str], log) -> tuple[int, str]:
    runner = os.environ.get("HQ_PROOF_RUNNER")
    cmd = [runner] if runner else [nightly._python(), os.path.join(wt, "app", "happy_flows.py")]
    # F111: the flows run behind the wall from the copy, and answer for the real HQ; this record's own log is written meanwhile
    env = {**os.environ, "HQ_REAL_HQ": hqpaths.HQ, "HQ_WALL_OWN": os.path.realpath(getattr(log, "name", "") or os.devnull)}
    # F121: in a process group of their own, so a stop ends them all, and the copy's owner.json names it for a later run
    p = subprocess.Popen(cmd + args, cwd=wt, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, start_new_session=True)
    _owner(wt, group=p.pid)
    try:
        so, se = p.communicate()
    except BaseException:
        _killgroup(p)
        raise
    _killgroup(p)  # what the flows left running in their group
    _owner(wt, group=None)
    out = so + se
    log.write(out)
    return p.returncode, out


def _excused(failed: list[str], named) -> list[str]:
    """F165: the failing flow lines ("605: FAILED - ...") of flows HQ_PROOF_EXCUSED names and the row doesn't."""
    ok = {x.strip() for x in (os.environ.get("HQ_PROOF_EXCUSED") or "").split(",") if x.strip()} - {str(x) for x in named}
    return [f for f in failed if (m := re.match(r"\s*(\d+): FAILED - ", f)) and m.group(1) in ok]


def _not_tried() -> list[str]:
    """H313: the happy flows not run for real here, each one holding the record. A test's stand-in for the flows (HQ_PROOF_RUNNER) tests
    the proof's own workings, not the app, so it has none."""
    if os.environ.get("HQ_PROOF_RUNNER"):
        return []
    return [w for w in happy.not_tried() if not re.match(rf"happy flow (?:{'|'.join(map(str, LATER))}) not tried", w)]


# 4 November 2026, his words: "we can do the 3 untried flows later once we have actually built those parts. keep them as an
# item for the planning for now" (H316). Until H316 makes them runnable they don't hold a build; everything else still does.
LATER = (9, 12, 14)


def skipped_flows(out: str) -> list[int]:
    """F121: the flows the run's result says were skipped under --quick (a Claude flow): named, not ran."""
    tail = out.rpartition("\n== Result")[2]
    return sorted({int(x) for x in re.findall(r"^\s*(\d+): skipped \(--quick\)", tail, re.M)})


def _last_words(out: str) -> str:
    """F155: a run that broke without a failing flow says why in its last line; kept on the record, so the job's line can say it."""
    last = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return f": {last[-1][:200]}" if last else ""


def run(n: int) -> int:
    was = _on_stop()
    try:
        return _run(n)
    except Stopped as e:
        print(f"Job {n}: stopped ({e}); the copy is cleaned up, no record written.")
        return 143
    finally:
        _off_stop(was)


def _run(n: int) -> int:
    text, jobs, _ = q.read()
    j = next((x for x in jobs if x["n"] == n), None)
    if not j:
        print(f"No job {n}.")
        return 2
    if subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet", "HEAD"]).returncode:
        print("HQ has changes that aren't committed: commit them first; a record stands for a commit.")
        return 2
    clean_stale()
    head = _git("rev-parse", "HEAD")  # F121: read first; the copy and the commits are of exactly this one
    label = label_of(j)
    rowtext = (j["text"] + " " + row_of(text, label))
    named = named_flows(rowtext)
    rec = {"n": n, "label": label, "item": (j.get("item") or {}).get("id"), "head": head, "commits": commits_of(label, head), "named": named,
           "skipped": [], "ran": 0, "passed": 0, "failed": [], "not_tried": _not_tried(), "green": False,
           "at": time.strftime("%Y-%m-%d %H:%M"), "t": time.time()}
    logpath = path(n)[:-5] + ".log"
    os.makedirs(folder(), exist_ok=True)
    import wall
    wt = None
    wall.proof_start(n)  # F100: the box counts the job's own work, not the test run that proves it
    try:
        wt = _copy(head)
        with open(logpath, "w", encoding="utf8") as log:
            import qatests  # real QA: her sealed tests on the built copy, first; red, and the rest isn't run
            if qatests.gate_on() and label:
                rec["qa_tests"] = qatests.end_run(label, wt)
                log.write(f"== her QA tests for {label}: {json.dumps(rec['qa_tests'], ensure_ascii=False)}\n")
                if not rec["qa_tests"].get("green"):
                    rec["failed"].append(f"her QA tests: {rec['qa_tests'].get('why') or 'not green'}")
                for nb in rec["qa_tests"].get("neighbours") or []:  # H342: the items it touches, each named in the job's log
                    log.write(f"== a neighbour, {nb['label']}: {nb['ran'] - len(nb['failed'])} of {nb['ran']} of its sealed tests pass\n")
            # H342: the flows around the items this build touches (their rows' own flows) run with the row's, on the same copy
            around = [x for x in (rec.get("qa_tests") or {}).get("neighbour_flows") or [] if x not in named]
            known = _known_flows(wt)  # F188: a neighbour's row can mention a made-up flow (F155's 9102); one unknown stops the run
            if known:
                around = [x for x in around if x in known]
            if around:
                rec["around"] = around
            if (named or around) and not rec["failed"]:
                # F105: a flow with Claude turns needs a live voice and usage; a row that only mentions one doesn't turn the record red
                both = sorted(set(named) | set(around))
                code, out = _flows(wt, ["--only", ",".join(map(str, both))], log)  # H313: for real, no --quick
                p, r_ = nightly.summary(out)
                rec["ran"], rec["passed"] = r_, p
                rec["skipped"] = [x for x in skipped_flows(out) if x in both]
                rec["failed"] = nightly.failures(out) or ([] if code == 0 else [f"the named flows {both} ended with exit {code}, {p} of {r_}{_last_words(out)}"])
            if not rec["failed"]:
                code, out = _flows(wt, happy.gate_args(), log)  # H313: the 17 happy flows, for real; the quick set is the night's
                p, r_ = nightly.summary(out)
                rec["ran"] += r_
                rec["passed"] += p
                rec["failed"] = nightly.failures(out) or ([] if code == 0 and r_ else [f"the happy flows ended with exit {code}, {p} of {r_}{_last_words(out)}"])
        excused = _excused(rec["failed"], named)
        if excused:  # F165: a check already split off as its own item doesn't hold this build
            rec["excused"] = excused
            rec["failed"] = [f for f in rec["failed"] if f not in excused]
        rec["green"] = (not rec["failed"] and not rec["not_tried"] and rec["ran"] > 0
                        and rec["passed"] + len(rec.get("excused") or []) == rec["ran"]
                        and ("qa_tests" not in rec or bool(rec["qa_tests"].get("green"))))
    finally:
        wall.proof_end(n)
        if wt:
            _uncopy(wt)
    _save(rec)
    qt = rec.get("qa_tests")
    print(f"Job {n}: {rec['passed']} of {rec['ran']} passed on a copy of {head[:7]}"
          + (f", her QA tests {qt.get('passed', 0)} of {qt.get('ran', 0)}" if qt else "")
          + (f", named flows {named}" if named else "") + (f", skipped {rec['skipped']}" if rec["skipped"] else "")
          + (": green." if rec["green"] else f". Failed: {'; '.join(rec['failed'] + rec['not_tried'])[:900]}"))
    return 0 if rec["green"] else 1


def lock_path() -> str:
    """The lock the full runs take turns on. A test never waits on the real one: a quick set held by hand runs this too."""
    if os.environ.get("HQ_FULLRUN_LOCK"):
        return os.environ["HQ_FULLRUN_LOCK"]
    if hqpaths.under_test():
        os.makedirs(folder(), exist_ok=True)
        return os.path.join(folder(), ".fullrun.lock")
    return os.path.expanduser("~/hq-fullrun.lock")


def listed_commits(label: str, head: str = "HEAD") -> list[str]:
    """F121: the commits qa.COMMITS_FOR gives this row that are on this branch up to head, written as commits_of writes them. Only
    where the gate counts it for this row alone (qa.commit_labels): a listed commit whose own subject names a row is that row's."""
    import qa
    base = _base()
    out = []
    for sha, entry in qa.COMMITS_FOR.items():
        if entry.get("row") != label:
            continue
        if subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", sha, head], capture_output=True).returncode:
            continue
        if not subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", sha, base], capture_output=True).returncode:
            continue  # already on the release line, which commits_of leaves out too
        if qa.commit_labels(str(ROOT), sha, _git("log", "-1", "--format=%s", sha)) == [label]:
            out.append(_git("log", "-1", "--format=%h %s", sha))
    return out


def all_commits(label: str, head: str = "HEAD") -> list[str]:
    """F121: every commit of the row up to head: named in its subject, or listed for it."""
    commits = commits_of(label, head)
    return commits + [c for c in listed_commits(label, head) if c not in commits]


def _held_by_parent(path_: str) -> int | None:
    """F121: an open file on the lock handed down by a wrapper (flock FILE command ...), whose lock is this run's already. The fd, or None."""
    import fcntl
    try:
        st = os.stat(path_)
    except OSError:
        return None
    try:
        fds = [int(x) for x in os.listdir("/proc/self/fd")]
    except OSError:
        fds = list(range(3, 256))
    for fd in fds:
        try:
            f = os.fstat(fd)
        except OSError:
            continue
        if (f.st_dev, f.st_ino) == (st.st_dev, st.st_ino):
            try:  # the same open file as the wrapper's: locking it again is a no-op when it's held there, refused when it isn't ours
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fd
            except OSError:
                continue
    return None


def run_rows(labels: list[str]) -> int:
    was = _on_stop()
    try:
        return _run_rows(labels)
    except Stopped as e:
        print(f"Stopped ({e}): the copy is cleaned up, no record written.", flush=True)
        return 143
    finally:
        _off_stop(was)


def _run_rows(labels: list[str]) -> int:
    """F121: one run on the commit HQ is on stands as the proof for every row it holds."""
    import fcntl
    import qa
    labels = list(dict.fromkeys(x.upper() for x in labels))
    bad = [x for x in labels if not qa.LABEL.fullmatch(x)]
    if not labels or bad:
        print("Which rows? Give their labels, like F121" + (f": not {', '.join(bad)}." if bad else "."))
        return 2
    lock = None
    if os.environ.get("HQ_FULLRUN_HELD") == "1" or _held_by_parent(lock_path()) is not None:
        print(f"The lock {lock_path()} is held by the run that started this one: going on.", flush=True)
    else:
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
        clean_stale()
        head = _git("rev-parse", "HEAD")  # read first: the copy, the commits and the record are all of exactly this one
        text = q.read()[0]
        rows, none = {}, []
        for label in labels:
            commits = all_commits(label, head)
            if commits:
                rows[label] = {"commits": commits, "named": named_flows(row_of(text, label))}
            else:
                none.append(label)
        if none:
            print(f"No commits in this commit for {', '.join(none)}: no record for {'it' if len(none) == 1 else 'them'}.")
        if not rows:
            print("Nothing to run.")
            return 2
        runid = time.strftime("%Y%m%d-%H%M%S") + "-" + head[:7]
        at, t = time.strftime("%Y-%m-%d %H:%M"), time.time()
        own_job = os.environ.get("HQ_JOB") or ""
        key = own_job or f"rows-{runid}-{os.getpid()}"  # a job that runs it keeps its box still; else the pid says when it's left behind
        shared = {"ran": 0, "passed": 0, "failed": []}
        os.makedirs(folder(), exist_ok=True)
        import wall
        wt = None
        wall.proof_start(key)
        try:
            wt = _copy(head)
            with open(os.path.join(folder(), f"rows-{runid}.log"), "w", encoding="utf8") as log:
                code, out = _flows(wt, happy.gate_args(), log)  # H313: the 17 happy flows, for real
                p, r_ = nightly.summary(out)
                shared.update(ran=r_, passed=p, not_tried=_not_tried(), failed=nightly.failures(out)
                              or ([] if code == 0 and r_ else [f"the happy flows ended with exit {code}, {p} of {r_}{_last_words(out)}"]))
                import qatests  # H342: an item built outside a job is proven like one: her sealed tests on the same copy
                for label, row in rows.items():
                    row.update(ran=0, passed=0, failed=[], skipped=[])
                    if qatests.gate_on():
                        row["qa_tests"] = qatests.end_run(label, wt)
                        log.write(f"== her QA tests for {label}: {json.dumps(row['qa_tests'], ensure_ascii=False)}\n")
                        if not row["qa_tests"].get("green"):
                            row["failed"].append(f"her QA tests: {row['qa_tests'].get('why') or 'not green'}")
                    if row["named"] and not row["failed"]:
                        code, out = _flows(wt, ["--only", ",".join(map(str, row["named"]))], log)  # H313: for real
                        p, r_ = nightly.summary(out)
                        row.update(ran=r_, passed=p, skipped=[x for x in skipped_flows(out) if x in row["named"]], failed=nightly.failures(out)
                                   or ([] if code == 0 else [f"the named flows {row['named']} ended with exit {code}, {p} of {r_}"]))
        finally:
            wall.proof_end(key)
            if not own_job:
                wall.forget(key)
            if wt:
                _uncopy(wt)
        sgreen = not shared["failed"] and not shared.get("not_tried") and shared["ran"] > 0 and shared["passed"] == shared["ran"]
        red = 0
        for label, row in rows.items():
            ran, passed = shared["ran"] + row["ran"], shared["passed"] + row["passed"]
            failed = shared["failed"] + row["failed"]
            green = (sgreen and not row["failed"] and row["passed"] == row["ran"]
                     and ("qa_tests" not in row or bool(row["qa_tests"].get("green"))))
            rec = {"n": None, "label": label, "item": None, "head": head, "commits": row["commits"][:40], "named": row["named"],
                   "skipped": row["skipped"], "ran": ran, "passed": passed, "failed": failed, "not_tried": shared.get("not_tried") or [],
                   "green": green, "at": at, "t": t,
                   "shared": runid, "rows": list(rows)}
            if "qa_tests" in row:
                rec["qa_tests"] = row["qa_tests"]
            _save(rec, os.path.join(folder(), f"rows-{runid}-{label}.json"))
            red += not green
            qt = row.get("qa_tests")
            print(f"{label}: {passed} of {ran} passed on a copy of {head[:7]}"
                  + (f", her QA tests {qt.get('passed', 0)} of {qt.get('ran', 0)}" if qt else "")
                  + (f", named flows {row['named']}" if row["named"] else "")
                  + (f", skipped {row['skipped']}" if row["skipped"] else "")
                  + (": green." if green else f". Failed: {'; '.join(failed + (shared.get('not_tried') or []))[:900]}"))
        print(f"One run ({runid}): the happy flows {shared['passed']} of {shared['ran']}, {len(rows)} record{'' if len(rows) == 1 else 's'}"
              + (f", {red} red." if red else ", all green."))
        return 1 if red else 0
    finally:
        if lock:
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
