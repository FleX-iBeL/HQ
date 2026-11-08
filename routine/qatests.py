#!/usr/bin/env python3
"""Real QA (4 November 2026): Moneypenny's own QA tests for an item, written before the build, held by the program.

His words, laptop chat of 4 November 2026: "i want her to seperate from the checklist, also write QA tests, and then test it at the end",
"based on the context, of what we want to have achieved as the end user. thats why its important she understands what i want.", "then
these tests are dynamic, they are built, and then we have tooling/system that tests robust if what is built actually is what was being
asked", "the point is she cant blindly make these QA tests without anyone checking her work either". His principle: "the team (the
tooling/system) is there to keep her in check, prompting is last line of defense not first."

Her tests for row LABEL live in the workspace, HQ/qa-tests/LABEL/:
    test.py      run as `python3 test.py HQDIR` against a copy of HQ's code (its working folder HQDIR too); one line per test,
                 "PASS name" or "FAIL name: why"
    tests.json   {"sentences": [{"his": "one sentence of his words, as it stands in the row", "tests": ["name", ...]}, ...],
                  "tests": {"name": "what it checks, as he'd see it", ...}}

The program, not a prompt, holds them:
  - the coverage: every sentence of his words in the row (the quotes in its "His words:") has at least one test that the script runs;
  - before the build: on a throwaway copy of HQ's code as it is, every test must FAIL (a test that passes already tests nothing new);
    then they're sealed: their fingerprint, the run before, and a copy of the files outside the workspace (HQ's own .status);
  - their own review, apart from the item's: its own prompt and verdict, at most ROUNDS rounds per road, and after the last
    flagged one a single message to him with all the open points;
  - the Ready mark (sprint.set_ready), the way to the team (sprint.gate: jobs.py add and send-row, his now too) and the end
    (proof.py runs the sealed tests on the built copy; jobs.py done and qa.py pass read that, his words on done don't skip it).
F151: flagged tests never go to the team, his now neither; after the 20th flagged round they're his decision, in one text. A QA
failure opens a fix road (fix_why): a new test of hers that fails on the build, sealed, and that version's own 20 fresh rounds. The team sees her tests as the target and can't change them: the fingerprint is checked at the end.

    python3 routine/qatests.py new LABEL       start her folder: his sentences in tests.json, a test.py to fill in
    python3 routine/qatests.py check LABEL     the two hard checks; seals them when they hold
    python3 routine/qatests.py check LABEL --before COMMIT
                                               F157: for an item already built before its tests were sealed: the same checks, run
                                               on a throwaway copy of COMMIT (HQ's code from before the build, in its history before
                                               the code as it is) instead; every test must fail there, and the seal names it
    python3 routine/qatests.py review LABEL    one round of their own review (the real reviewer), ROUNDS at most
    python3 routine/qatests.py show LABEL      where they stand
    python3 routine/qatests.py run LABEL HQDIR the sealed tests on HQDIR (what proof.py does at the end)
    python3 routine/qatests.py neighbours LABEL [HQDIR]
                                               H342: the items whose sealed tests a build for LABEL also runs, and why

H342 (8 November 2026, his yes): her tests replay the real case, on a copy of the real data, where he would see it, and fail first;
every build also checks what it touches. Why: that week her check sent work back 14 times against 55 passes, and in 13 of the 14 her
own sealed tests had passed while the row's own example failed on real data (a state file instead of the status page, the program's
texts instead of her replies, made-up nights). So, held by the program:
  - the real case: run_on gives her test a throwaway copy of the real workspace (HQDIR/workspace) and of HQ's real .status
    (HQ_QA_STATUS); routine/realcase.py makes a whole throwaway HQ of them, with HQ's own status server, a headless browser's view of
    the page and the lines' threads as the texts land (realcase.Case);
  - fail first, for a reason: on the code from before the build every test must print its FAIL line and the run must end by itself:
    a test that passes there, or only crashes there (a traceback, an exit that isn't 0), or fails without saying what he'd see
    instead, is refused and named; the seal keeps each FAIL line, and the review reads them;
  - the review asks the real-case probe: does this test replay the row's own example on real data, where he would see it; a stand-in
    the program can see itself (a file behind the status page read instead of the page as served, realcase.stand_in_holes) is a hole
    whatever the model says;
  - seals and reviews carry RULES: tests sealed or reviewed before these rules hold the Ready mark until they're checked and reviewed
    again under them (the rest of the sprint goes through this);
  - neighbours: a build's sealed-test run (end_run) also runs the sealed tests of the items whose own commits touched the files this
    build changed (NEIGHBOURS_MOST, the most overlap first), each on its own copy; a red there makes the record red and names the
    item and its flows, which proof.py runs with the build's. A fix road's new tests (red by design until that fix lands) don't count.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import estimate as E  # noqa: E402
import hqpaths  # noqa: E402
import jobs as q  # noqa: E402
import sprint as S  # noqa: E402

ROUNDS = 20  # F151: 20 at most, counted per version: each QA failure starts them again, as for a new item
RUN_TIMEOUT = 1200  # seconds for one run of her tests; F175: room for F165's ten real runs of flow 605 (about 460 s), a hanging test still stopped
REVIEW_TIMEOUT = 240
BUDGET = 0.25
MODEL = os.environ.get("HQ_QA_REVIEW_MODEL") or os.environ.get("HQ_REVIEW_MODEL") or "sonnet"
EFFORT = os.environ.get("HQ_QA_REVIEW_EFFORT") or "medium"
READS = 20000
_LINE = re.compile(r"^\s*(PASS|FAIL)\s+([A-Za-z0-9_.-]+)\s*(?::\s*(.*))?$")
PARKED_DONE = "paused: ended, no record"  # runjob.PARKED: a build whose work is done and only its record is missing
RULES = "H342"  # the rules a seal and a review were made under; older ones hold the Ready mark until checked and reviewed again
NEIGHBOURS_MOST = int(os.environ.get("HQ_QA_NEIGHBOURS_MOST") or 4)  # [Claude's choice] each neighbour's run can take minutes
_CRASH = re.compile(r"Traceback \(most recent call last\)")
_BARE_ERROR = re.compile(r"^\W*(?:\w+\.)*\w*(?:Error|Exception|Exit)\b(?:\(.*\))?\W*$")

SYSTEM = (
    "You review the QA tests written for one item of a software project, before the build team starts on it. You did not write them. "
    "You read only what you're given: the item, the sentences of the user's own words in it, the tests' list and the test script. You "
    "have no tools and change nothing. The tests are the only check the build will get: after the build a program runs them on the "
    "built code, and only a pass lets it through. So hunt for tests that would let the wrong build through or hold the right one back. "
    "For each of the user's sentences, in order, decide whether its tests check what that sentence asks, as the end user would see it "
    "(the page he reads, the text he gets, the file he opens, what the program does when he uses it), not a stand-in for it (a file that "
    "exists, a word anywhere in the code, a function's name, a comment). A sentence that only gives context or a reason, and asks for "
    "nothing to change, is checked when its tests check the change it gives the reason for. Then look for: a test that would pass "
    "although the sentence isn't met; a test that would fail although it is met (brittle on wording, layout or order the user didn't "
    "ask for); something the item's done means that no test checks. Not a hole: style, naming, the script's length, a case the item "
    "puts out of scope, a requirement you invent. "
    "Then the real-case probe (H342; in one week 13 of 14 send-backs were tests that passed on a stand-in while the row's own example "
    "failed on real data): does at least one test replay the row's own done example, its real case (the real row, the real text, the "
    "real job or night it names), on the real data as the test's throwaway copy holds it (HQDIR/workspace is a copy of the real "
    "workspace; routine/realcase.py gives a whole HQ on it), and read the result where he would see it: a thing on the status page "
    "from the page as HQ's own server serves it (realcase's serve(), rendered() or get()), never a state file behind it; a text from "
    "the line's thread as it lands, never the program's own wording of it; a command's result from its real output? Made-up items, "
    "made-up nights or rows planted only for the test, where the row names a real one, are a stand-in. You also get how each test "
    "failed on the code from before the build: it should fail there for the reason the row gives (the example not met), not because "
    "a helper, a file or a module is missing. Answer with JSON only, nothing else: "
    '{"sentences": [{"his": "the sentence", "checked": true or false, "why": "one plain sentence"}, ... one per sentence, in order], '
    '"real_case": {"replays": true or false, "test": "the test that replays it, or empty", "where": "where it reads the result", '
    '"hole": "one plain sentence when it doesn\'t, else empty"}, '
    '"pass": true or false, "findings": ["one plain sentence per hole, naming the test", ...]}. pass is false exactly when a sentence '
    "isn't checked, the real-case probe finds no replay, or you found another real hole; at most four findings, the most important first.")


# ---------- F151: a fix found by QA goes the same road as a new item ----------
# His words, 5 November 2026: "when you find something in QA that was not of expected quality, and you propose a fix, that fix needs to be
# checked if it still make sense in the total picture of things. so it needs to be reviewed again, and also checked against the intial
# request", "as if it was a new item", "no put it back, this is mandatory". A QA failure queues nothing: the finding goes back into the row
# as an open point (qa.fail) and opens a fix road here, held by the program until, in this order: a new test of hers for the finding fails
# on the build as it stands and is sealed (check), that version of her tests passes its own review (rounds 1 to 20 of this road), and the
# item passes its review again against his words and the whole picture (review.py now, rounds 1 to 20 of this road). Each QA failure opens
# a new road; a QA pass closes it. Always on, a test copy too: a road only exists where a QA failure opened it.

def roads(label: str) -> list[dict]:
    return [x for x in state(label).get("qa_fails") or [] if isinstance(x, dict)]


def cycle(label: str) -> int:
    """Which road the rounds are counted in: 0 before any QA failure, then 1, 2, … one per QA failure."""
    return len(roads(label))


def fix_road(label: str) -> dict | None:
    """The open road of this row (a QA failure without a QA pass since), or None."""
    rs = roads(label)
    return rs[-1] if rs and not rs[-1].get("passed") else None


def qa_failed(label: str, finding: str, job: int | None = None) -> dict:
    """qa.fail: a new road, with her tests as they were sealed before it (the new test is the one they don't have)."""
    before = list((state(label).get("sealed") or {}).get("tests") or [])
    e = _put(label, lambda x: x.update({"qa_fails": [y for y in x.get("qa_fails") or [] if isinstance(y, dict)] + [
        {"at": int(time.time()), "finding": finding, "job": job, "tests_before": before}]}))
    return {**e["qa_fails"][-1], "n": len(e["qa_fails"])}


def qa_passed(label: str) -> None:
    if fix_road(label):
        _put(label, lambda x: x["qa_fails"][-1].update({"passed": int(time.time())}))


def in_road(rounds: list, label: str) -> list:
    """The rounds of the road the row is on now (a round from before F151 counts as road 0)."""
    k = cycle(label)
    return [x for x in rounds if isinstance(x, dict) and int(x.get("cycle") or 0) == k]


def fix_why(row) -> str | None:
    """Why the fix of a row QA failed can't go to the team yet, or None (no open road, or every step of it done)."""
    label = row["label"]
    road = fix_road(label)
    if not road:
        return None
    k, fp = cycle(label), fingerprint(label)
    finding = road.get("finding") or ""
    sealed = state(label).get("sealed") or {}
    if not fp or sealed.get("fp") != fp or int(sealed.get("cycle") or 0) != k or sealed.get("rules") != RULES:
        return (f"{label} isn't ready: QA failed it, and the finding is an open point in the row: {finding}. As for a new item, a new test of "
                f"hers for it goes first: it must fail on the build as it stands and be sealed by the hard checks (python3 routine/qatests.py "
                f"check {label}); the fix is held until then")
    rv = in_road(state(label).get("reviews") or [], label)
    last = rv[-1] if rv else {}
    if not (last.get("fp") == fp and last.get("verdict") == "pass" and last.get("rules") == RULES):
        flagged = last.get("fp") == fp and last.get("verdict") == "flag"
        return (f"{label} isn't ready: the new version of her QA tests, with the test for the QA finding, needs its own review first"
                + (f"; it flagged them (round {len(rv)} of {ROUNDS}): " + "; ".join(last.get("findings") or []) if flagged else
                   f" (round {len(rv) + 1} of {ROUNDS}): python3 routine/qatests.py review {label}"))
    import review
    e = ((review._state()[1].get("rows") or {}).get(label)) or {}
    nr = in_road(review.now_rounds(e), label)
    if not (nr and nr[-1].get("fp") == S.ask_fp(row["line"]) and nr[-1].get("verdict") == "pass"):
        return (f"{label} isn't ready: after the QA failure the item itself goes through its review again, the fix against his words, the "
                f"first request and the whole picture, before it goes to the team: python3 routine/review.py now {label} "
                f"(round {len(nr) + 1} of {review.NOW_ROUNDS})")
    return None


def flagged_why(label: str) -> str | None:
    """F151: tests their review flagged never go to the team, his now neither: why, or None."""
    rv = in_road(state(label).get("reviews") or [], label)
    if rv and rv[-1].get("verdict") == "flag":
        return (f"Refused: the review of {label}'s QA tests flagged them (round {len(rv)} of {ROUNDS}): " + "; ".join(rv[-1].get("findings") or [])
                + ". Flagged tests never go to the team, on his now neither; after the 20th round they're his decision. Nothing added.")
    return None


def gate_on() -> bool:
    """On everywhere, a copy too; a test (HQ_UNDER_TEST) only with HQ_QA_ON, like the proof's gate."""
    return not hqpaths.under_test() or bool(os.environ.get("HQ_QA_ON"))


def data_dir() -> str:
    return os.path.dirname(os.path.realpath(q.ROADMAP))


def folder(label: str) -> str:
    return os.path.join(data_dir(), "qa-tests", label.strip().upper())


def seal_root() -> str:
    """The program's own copy of sealed tests: HQ's .status on this computer, never the workspace the team can write."""
    return os.environ.get("HQ_QA_SEALS") or os.path.join(hqpaths.HQ, ".status", "qa-sealed")


def _files(d: str) -> dict:
    out = {}
    for f in ("test.py", "tests.json"):
        try:
            out[f] = open(os.path.join(d, f), encoding="utf8").read()
        except OSError:
            out[f] = None
    return out


def fingerprint_of(d: str) -> str | None:
    fs = _files(d)
    if any(v is None for v in fs.values()):
        return None
    h = hashlib.sha256()
    for k in sorted(fs):
        h.update(k.encode() + b"\0" + fs[k].encode("utf8") + b"\0")
    return h.hexdigest()


def fingerprint(label: str) -> str | None:
    return fingerprint_of(folder(label))


# ---------- the state, in sprint.json under "qa_tests", apart from the item review's ----------

def _all() -> dict:
    return S._load(S.RANKS).get("qa_tests") or {}


def state(label: str) -> dict:
    return _all().get(label.strip().upper()) or {}


def _put(label: str, change) -> dict:
    label = label.strip().upper()
    with q.locked():
        d = S._load(S.RANKS)
        allq = d.get("qa_tests") or {}
        e = allq.get(label) or {}
        change(e)
        allq[label] = e
        d["qa_tests"] = allq
        S._save(S.RANKS, d)
    return e


# ---------- his sentences and her list ----------

def _row(label: str):
    label = label.strip().upper()
    return next((r for r in S.open_rows() if r["label"] == label), None)


def his_sentences(row) -> list[str]:
    """Every sentence of his words in the row: the quotes in its "His words:" field, each cut into sentences. With no quote of his (a row
    found by QA or a check), the row's title stands for what's asked."""
    hw = S.field_texts(row["line"]).get("his_words") or ""
    out = []
    for qt in S._QUOTES.findall(hw):
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"“'‘])", qt.strip()):
            s = s.strip().strip("…").strip()
            if len(S._bare(s)) >= 3 and S._bare(s) not in {S._bare(x) for x in out}:
                out.append(s)
    if not out:
        cells = hqpaths.cells(row["line"])
        title = re.sub(r"^\s*\**[FH]\d+(?:\.\d+)*\**\s*[:.-]?\s*", "", cells[1] if len(cells) > 1 else "").strip()
        out = [title] if title else []
    return out


def read_list(d: str) -> tuple[dict | None, str]:
    try:
        t = json.load(open(os.path.join(d, "tests.json"), encoding="utf8"))
    except OSError:
        return None, "there's no tests.json"
    except ValueError as e:
        return None, f"tests.json isn't JSON ({e})"
    if not isinstance(t, dict) or not isinstance(t.get("sentences"), list) or not isinstance(t.get("tests"), dict):
        return None, 'tests.json needs {"sentences": [{"his": "...", "tests": ["name"]}], "tests": {"name": "what it checks"}}'
    return t, ""


def coverage(row, t: dict) -> list[str]:
    """What's missing in her list for his words, in plain words; [] when every sentence of his has a named, described test."""
    have = {}
    for x in t.get("sentences") or []:
        if isinstance(x, dict) and isinstance(x.get("his"), str):
            have.setdefault(S._bare(x["his"]), []).extend([n for n in (x.get("tests") or []) if isinstance(n, str) and n.strip()])
    miss = []
    for s in his_sentences(row):
        names = have.get(S._bare(s)) or []
        if not names:
            miss.append(f"no test for his sentence \"{s}\"")
            continue
        undescribed = [n for n in names if not str((t.get("tests") or {}).get(n) or "").strip()]
        if undescribed:
            miss.append(f"the test(s) {', '.join(undescribed)} for \"{s[:60]}\" aren't described in tests.json's \"tests\"")
    return miss


def named_tests(t: dict) -> list[str]:
    out = []
    for x in t.get("sentences") or []:
        for n in (x.get("tests") or []) if isinstance(x, dict) else []:
            if isinstance(n, str) and n.strip() and n not in out:
                out.append(n)
    return out


# ---------- running them ----------

def status_source() -> str:
    """H342: where HQ's real .status is read from for a test's copy: an outer test run's own copy (HQ_QA_STATUS), else this HQ's."""
    return os.environ.get("HQ_QA_STATUS") or os.path.join(hqpaths.HQ, ".status")


def _status_copy(box: str) -> str:
    """H342: a throwaway copy of HQ's real .status in the box (without the sealed tests, the proofs' logs or the locks), for a test that
    needs what HQ keeps there (the line's state, the usage, the routines): realcase.Case puts it under its own HQ. "" when there's none."""
    src, dest = status_source(), os.path.join(box, "status")
    if not os.path.isdir(src):
        return ""
    try:
        shutil.copytree(src, dest, symlinks=True, ignore_dangling_symlinks=True,
                        ignore=shutil.ignore_patterns("qa-sealed", "*.log", "*.lock", "*.pid", "__pycache__"))
    except shutil.Error:
        pass  # a file that went while it was copied (the live HQ writes on)
    except OSError:
        return ""
    return dest


def crashed(out: str, code: int | None) -> str:
    """H342: why a run of her test.py counts as a crash, or "": a traceback in its output, or an exit that isn't 0."""
    if _CRASH.search(out or ""):
        tail = [ln for ln in (out or "").splitlines() if ln.strip()]
        return "a traceback: " + (tail[-1].strip()[:200] if tail else "")
    if code not in (0, None):
        return f"it ended with exit {code}"
    return ""


def run_on(d: str, hqdir: str, info: dict | None = None) -> tuple[dict, str]:
    """Her test.py in folder d on the code at hqdir: ({name: passed}, its output). F9176: only ever on a throwaway copy of the
    workspace (the planning with its jobs, the sprint file), never his live one: hqdir/workspace points to the copy while her test
    runs, and every Python it starts carries the test wall's hook, which refuses a write to the live files by their own path.
    H342: the box also holds a copy of HQ's real .status (HQ_QA_STATUS), for realcase.Case; info, when given, gets the run's exit
    code and whether it crashed."""
    box, why = _qa_box(hqdir)
    if not box:
        return {}, f"Refused: her tests didn't run: {why}. They only ever run on a throwaway copy, never on the live files."
    link, wall = os.path.join(hqdir, "workspace"), os.path.join(box, "wall")
    was = os.readlink(link)
    _relink(link, os.path.join(box, "workspace"))
    try:
        env = {k: v for k, v in os.environ.items() if not k.startswith("HQ_")}
        os.makedirs(os.path.join(box, "tmp"), exist_ok=True)  # F175: her test's own temp files go in the box, gone with it
        env["TMPDIR"] = os.path.join(box, "tmp")
        env.update({"HQ_UNDER_TEST": "1", "HQ_QA_TEST_RUN": "1", "PYTHONDONTWRITEBYTECODE": "1", "HQ_WALL": wall,
                    "PYTHONPATH": os.pathsep.join(x for x in (os.path.join(wall, "py"), env.get("PYTHONPATH", "")) if x)})
        env["HQ_QA_BOX"] = box  # H342: realcase.Case only works on this box's own copies
        # H342: the program's own realcase, for a test run on code from before it existed (fail first on the old code); a test that puts
        # HQDIR/routine first on its path gets the code under test's own one when it has it
        lib = os.path.join(box, "lib")
        os.makedirs(lib, exist_ok=True)
        if os.path.exists(os.path.join(HERE, "realcase.py")):
            shutil.copyfile(os.path.join(HERE, "realcase.py"), os.path.join(lib, "realcase.py"))
        env["PYTHONPATH"] = os.pathsep.join(x for x in (os.path.join(wall, "py"), lib, os.environ.get("PYTHONPATH", "")) if x)
        st = _status_copy(box)
        if st:
            env["HQ_QA_STATUS"] = st
        py = os.path.join(hqpaths.HQ, ".venv", "bin", "python")  # HQ's own Python, as in tell(): her tests import the app (loguru), the system one can't
        # H339 (job 9333): her test is written to sit in HQ/qa-tests/LABEL of the workspace, and may read the planning next to it
        # (its __file__'s parents[2]/roadmap.md). Sealed it sits in .status/qa-sealed/LABEL/SEAL, where that read finds nothing and the
        # test stops before its first line. So the sealed files run from their own place in the throwaway copy, byte for byte.
        run_d = d
        if os.path.isdir(os.path.join(box, "workspace", "HQ")):
            up = os.path.dirname(os.path.realpath(d))
            name = os.path.basename(up) if os.path.dirname(up) == os.path.realpath(seal_root()) else os.path.basename(os.path.realpath(d))
            run_d = os.path.join(box, "workspace", "HQ", "qa-tests", name or "test")
            os.makedirs(run_d, exist_ok=True)
            for f in ("test.py", "tests.json"):
                if os.path.exists(os.path.join(d, f)):
                    shutil.copyfile(os.path.join(d, f), os.path.join(run_d, f))
        # F193: her test runs in a session of its own, and whatever ends this run (its end, a timeout, a stop) stops it and every
        # process it started, wherever they went, before the box is removed: nothing writes into a box half removed
        p = subprocess.Popen([py if os.path.exists(py) else sys.executable, os.path.join(run_d, "test.py"), hqdir], cwd=hqdir, env=env,
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            so, se = p.communicate(timeout=RUN_TIMEOUT)
            out = so + se
            if info is not None:
                info.update({"code": p.returncode, "crashed": crashed(out, p.returncode)})
        except subprocess.TimeoutExpired:
            if info is not None:
                info.update({"code": None, "crashed": f"it didn't finish in {RUN_TIMEOUT} s"})
            return {}, f"her tests didn't finish in {RUN_TIMEOUT} s"
        finally:
            _stop_all(p.pid if p.returncode is None else None, box)
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        got = {}
        for ln in out.splitlines():
            m = _LINE.match(ln)
            if m:
                got[m.group(2)] = got.get(m.group(2), True) and m.group(1) == "PASS"
        try:
            refused = [json.loads(x).get("path", "") for x in open(os.path.join(wall, "refused.jsonl"), encoding="utf8") if x.strip()]
        except (OSError, ValueError):
            refused = []
        if refused:  # a test that reached for the live files doesn't pass, whatever it printed
            got = {n: False for n in got}
            out += "\nRefused: her test tried to write the live files: " + ", ".join(sorted(set(refused)))[:400] + "\n"
        return got, out[-3000:]
    finally:
        _relink(link, was)
        _stop_all(None, box)
        for _ in range(3):  # F193: a box removed in full, never a stub left (a file still being let go of on the first try)
            shutil.rmtree(box, ignore_errors=True)
            if not os.path.exists(box):
                break
            time.sleep(0.2)


def _procs() -> dict:
    """F193: every process here, {pid: parent pid}."""
    out = {}
    for d in os.listdir("/proc"):
        if d.isdigit():
            try:
                with open(f"/proc/{d}/stat", encoding="utf8", errors="replace") as f:
                    out[int(d)] = int(f.read().rsplit(")", 1)[1].split()[1])
            except (OSError, IndexError, ValueError):
                pass
    return out


def _in_box(pid: int, box: str) -> bool:
    """F193: a process working in the box: its folder, its command line or its HQ_QA_BOX is the box (a test's orphan under init too)."""
    try:
        if os.readlink(f"/proc/{pid}/cwd").startswith(box):
            return True
    except OSError:
        pass
    for part, mark in (("cmdline", box.encode()), ("environ", b"HQ_QA_BOX=" + box.encode() + b"\0")):
        try:
            with open(f"/proc/{pid}/{part}", "rb") as f:
                if mark in f.read():
                    return True
        except OSError:
            pass
    return False


def _stop_all(root: int | None, box: str) -> None:
    """F193: the test run at root and every process it started, followed by parent wherever its process group went, and any process
    still working in the box, held still (so none starts another) and then killed. Never this run itself or what it runs under."""
    import signal
    mine, ps = set(), _procs()
    p = os.getpid()
    while p > 1 and p not in mine:
        mine.add(p)
        p = ps.get(p, 0)
    seen: set = set()
    for _ in range(20):
        ps = _procs()
        got = {root} if root and root in ps else set()
        todo = list(got | seen)
        while todo:
            x = todo.pop()
            for c, pp in ps.items():
                if pp == x and c not in got:
                    got.add(c)
                    todo.append(c)
        if box:
            got |= {c for c in ps if c not in got and _in_box(c, box)}
        got = {c for c in got if c in ps} - mine
        if not got - seen:
            break
        for c in got - seen:
            try:
                os.kill(c, signal.SIGSTOP)
            except OSError:
                pass
        seen |= got
    for c in seen:
        try:
            os.kill(c, signal.SIGKILL)
        except OSError:
            pass
    end = time.time() + 5
    while time.time() < end and any(_state(c) not in ("", "Z") for c in seen - {root}):
        time.sleep(0.05)


def _state(pid: int) -> str:
    try:
        with open(f"/proc/{pid}/stat", encoding="utf8", errors="replace") as f:
            return f.read().rsplit(")", 1)[1].split()[0]
    except (OSError, IndexError):
        return ""


def _relink(link: str, to: str) -> None:
    """The link pointed somewhere else in one step: never a moment with no workspace, never a write through it."""
    tmp = f"{link}.qa-{os.getpid()}"
    try:
        os.remove(tmp)
    except OSError:
        pass
    os.symlink(to, tmp)
    os.replace(tmp, link)


def _qa_box(hqdir: str) -> tuple[str | None, str]:
    """F9176: a throwaway folder (in the temp folder) with a copy of hqdir's workspace and the wall's hook: (its path, ""), or
    (None, why). No copy means no run, never a fall back to the live files."""
    import tempfile
    import testwall
    link = os.path.join(hqdir, "workspace")
    if not os.path.islink(link):
        return None, "the code given holds the live workspace itself, not a copy's link to it"
    live = os.path.realpath(link)
    try:
        # F175: on the main disk, like proof's own copies; the temp folder (/tmp) filled up with other runs' copies and her tests
        # then never started ("Disk quota exceeded", job 9264)
        base = os.path.join(hqpaths.HQ, "scratch")
        os.makedirs(base, exist_ok=True)
        box = tempfile.mkdtemp(prefix="hq-qa-", dir=base)
    except OSError as ex:
        return None, f"no throwaway copy could be made ({ex.strerror or ex})"
    try:
        import proof
        proof.mark_owner(box)  # F193: names this run, so a later one sweeps the box if this one is killed before it tidies up
        testwall._copy_workspace(live, os.path.join(box, "workspace"))
        paths = {live} | {os.path.realpath(p) for _, _, p in testwall.real_places(os.path.dirname(live), live)}
        try:  # a run already behind a wall keeps that wall's real places too
            paths |= set(json.load(open(os.path.join(os.environ["HQ_WALL"], "real.json"), encoding="utf8"))["paths"])
        except (KeyError, OSError, ValueError):
            pass
        py = os.path.join(box, "wall", "py")
        os.makedirs(py)
        with open(os.path.join(py, "hqwallhook.py"), "w", encoding="utf8") as f:
            f.write(testwall.HOOK)
        with open(os.path.join(py, "sitecustomize.py"), "w", encoding="utf8") as f:
            f.write(testwall.SITECUSTOMIZE)
        with open(os.path.join(box, "wall", "real.json"), "w", encoding="utf8") as f:
            json.dump({"paths": sorted(paths), "claudes": []}, f)
        return box, ""
    except Exception as ex:
        shutil.rmtree(box, ignore_errors=True)
        return None, f"no throwaway copy could be made ({ex})"[:300]


def _head() -> str:
    import proof
    return subprocess.run(["git", "-C", str(proof.ROOT), "rev-parse", "HEAD"], text=True, capture_output=True).stdout.strip()


def _before_commit(before: str) -> tuple[str | None, str]:
    """F157: the named commit as a full hash, when it's in HQ's history before the code as it is; else (None, why)."""
    import proof
    full = subprocess.run(["git", "-C", str(proof.ROOT), "rev-parse", "--verify", "--quiet", f"{before}^{{commit}}"], text=True,
                          capture_output=True).stdout.strip()
    if not full:
        return None, f"the commit {before} isn't in HQ's history"
    head = _head()
    if full == head or subprocess.run(["git", "-C", str(proof.ROOT), "merge-base", "--is-ancestor", full, head],
                                      capture_output=True).returncode:
        return None, f"the commit {before} ({full[:7]}) isn't before HQ's code as it is ({head[:7]})"
    return full, ""


def check(label: str, before: str | None = None) -> tuple[bool, str]:
    """The two hard checks on her tests as they stand; sealed when both hold. (ok, what to say). before (F157): a commit from before the
    item's build, for an item built before its tests were sealed: the tests then run on a copy of that commit, not the code as it is."""
    label = label.strip().upper()
    row = _row(label)
    if not row:
        return False, f"Refused: {label} isn't an open row on the planning."
    d = folder(label)
    fp = fingerprint_of(d)
    if not fp:
        return False, (f"Refused: {label} has no QA tests of hers: HQ/qa-tests/{label}/test.py and tests.json "
                       f"(python3 routine/qatests.py new {label} starts them).")
    _, js, _ = q.read()
    # H342: a build parked with its work done and only its record missing ("paused: ended, no record") builds nothing more: it doesn't
    # hold her tests, so a rewrite can replace them (and the record step then runs on the new ones); a prep builds nothing either
    busy = [x for x in js if not x["state"].startswith(PARKED_DONE) and not _is_prep(x["text"])]
    j = q.with_team(busy, label) if gate_on() else None  # F157: part of her gate, so off in a test copy as the rest (its queue is a copy of the live one)
    if j and (state(label).get("sealed") or {}).get("fp"):  # the team builds to them: no new seal while it does, by anyone
        return False, (f"Refused: {label} is with the team (job {j['n']}, {j['state']}): its QA tests stay as they were sealed while it builds. "
                       "A change to them waits until the job is done or stopped.")
    named = None
    if before is not None:
        named, why = _before_commit(before)
        if not named:
            return False, f"Refused: {why}. Nothing sealed."
    t, why = read_list(d)
    if t is None:
        return False, f"Refused: {label}'s QA tests: {why}."
    miss = coverage(row, t)
    if miss:
        return False, f"Refused: {label}'s QA tests don't cover his words: " + "; ".join(miss) + ". Nothing sealed."
    names = named_tests(t)
    import proof
    proof.clean_stale()  # F193: what earlier runs left (a killed check's box and copy, old QA leftovers) goes before a new copy is made
    head = named or _head()
    where = f"the commit {head[:7]} from before the build" if named else f"HQ's code as it is ({head[:7]})"
    wt = proof._copy(head)
    info: dict = {}
    try:
        got, out = run_on(d, wt, info)
    finally:
        proof._uncopy(wt)
    unrun = [n for n in names if n not in got]
    if unrun:
        return False, (f"Refused: {label}'s test.py never reports {', '.join(unrun)} (a line \"PASS name\" or \"FAIL name: why\" for each), "
                       f"so those tests don't exist. Its output: {out[-400:]!r}. Nothing sealed.")
    # H342, fail first for a reason: on the code from before the build the run ends by itself, every FAIL line says what he'd see
    # instead; a test that only crashes there (a traceback, an exit that isn't 0) doesn't show it fails for the row's reason
    if info.get("crashed"):
        return False, (f"Refused: {label}'s test.py crashed on {where} ({info['crashed']}). A test that only crashes on the code from "
                       "before the build doesn't show it fails for the reason the row gives: catch what you need, and end every test with "
                       "its own line, FAIL saying what he'd see instead of the row's example. Nothing sealed.")
    whys = {n: _why(out, n) for n in names if not got.get(n)}
    bare = [n for n, w in whys.items() if w in ("no why given", "it gave no line (it didn't run to it)") or _BARE_ERROR.match(w)]
    if bare:
        return False, (f"Refused: {label}'s test(s) {', '.join(bare)} fail on {where} without saying what he'd see instead "
                       f"({'; '.join(f'{n}: {whys[n]}' for n in bare)[:300]}). Each FAIL line says, in his terms, how the row's own example "
                       "isn't met yet there. Nothing sealed.")
    road, k = fix_road(label), cycle(label)
    if road:  # F151: after a QA failure her earlier tests stay as they were; what's new is the test for the finding, and it must fail now
        names = names + [n for n in got if n not in names]
        fresh = [n for n in names if n not in (road.get("tests_before") or [])]
        passing = [n for n in fresh if got.get(n)]
        if not fresh or passing:
            why = (f"no new test for the QA finding (her tests are the ones sealed before it)" if not fresh else
                   f"the new test(s) {', '.join(passing)} already pass on {where}, so they don't catch the fault QA found")
            tell(label, f"fix-test-{k}", f"QA failed {label}: {road.get('finding') or 'no finding written'}. Her new test for it doesn't hold: {why}. "
                 "The fix doesn't go to the team; it's an open point for you.")
            return False, (f"Refused: {label}'s QA tests: {why}: {road.get('finding')}. Nothing sealed, the fix doesn't go, and the finding goes to "
                           "him on Moneypenny's line as an open point.")
    else:
        passing = [n for n in names if got.get(n)]
    if passing:
        said = "; ".join(f"PASS {n}" for n in passing)[:300]
        if named:
            return False, (f"Refused: {label}'s test(s) {', '.join(passing)} already pass on {where} ({said}), so they don't test what was "
                           "built. Each test must fail there and pass on the build: rewrite it to replay the row's own example. Nothing sealed.")
        return False, (f"Refused: {label}'s test(s) {', '.join(passing)} already pass on {where} ({said}), before any "
                       "build, so they don't test what he asked for. Each test must fail now and pass once it's built: rewrite it to replay "
                       "the row's own example. Nothing sealed.")
    keep = os.path.join(seal_root(), label, fp[:16])
    shutil.rmtree(keep, ignore_errors=True)
    os.makedirs(keep, exist_ok=True)
    for f in ("test.py", "tests.json"):
        shutil.copy2(os.path.join(d, f), os.path.join(keep, f))
    sealed = {"fp": fp, "at": int(time.time()), "copy": keep, "his": len(his_sentences(row)), "tests": names, "cycle": k, "rules": RULES,
              "before": {"head": head, "results": {n: got[n] for n in names}, "whys": {n: whys[n] for n in names if n in whys},
                         **({"named": True} if named else {})}}
    def _seal(e):  # H342: a rewrite replaces the sealed set; the one it replaces stays in the history
        if (e.get("sealed") or {}).get("fp") and e["sealed"]["fp"] != fp:
            e["sealed_before"] = ([x for x in e.get("sealed_before") or [] if isinstance(x, dict)] + [{**e["sealed"], "replaced": int(time.time())}])[-20:]
        e["sealed"] = sealed
    _put(label, _seal)
    try:
        import trail
        trail.step(trail.resolve(label), "qa_tests", fp=fp[:16], tests=len(names), before=head[:12])
    except Exception:
        pass
    if road:
        return True, (f"{label}'s QA tests are sealed: {len(names)} test(s), the new one(s) for the QA finding failing on {where} as they "
                      f"should. Next, this version's own review: python3 routine/qatests.py review {label} (round 1 of {ROUNDS}).")
    return True, (f"{label}'s QA tests are sealed: {len(names)} test(s) for his {sealed['his']} sentence(s), every one failing on "
                  f"{where} as it should. Next, their own review: python3 routine/qatests.py review {label}.")


def _is_prep(text: str) -> bool:
    import qa
    return qa.is_prep(text)


def why_not(row, now: bool = False) -> str | None:
    """Why her QA tests keep this row from the Ready mark (now=False) or from the team on his now (now=True), or None. The hard checks
    always; the review must have passed them as they stand (F151: flagged tests never go, his now neither), and a fix QA found goes its road."""
    fw = fix_why(row)
    if fw:
        return fw
    old = (state(row["label"]).get("sealed") or {})
    if old.get("fp") and old.get("rules") != RULES and old.get("fp") == fingerprint(row["label"]):
        # H342: a seal from before the real-case rules is stale wherever it's read, a test copy of the real data too
        return _rules_why(row["label"])
    if not gate_on():
        return None
    label = row["label"]
    d = folder(label)
    fp = fingerprint_of(d)
    if not fp:
        return (f"{label} isn't ready: it has no QA tests of hers (HQ/qa-tests/{label}/test.py and tests.json; "
                f"python3 routine/qatests.py new {label} starts them, then check and review)")
    t, why = read_list(d)
    if t is None:
        return f"{label} isn't ready: its QA tests: {why}"
    miss = coverage(row, t)
    if miss:
        return f"{label} isn't ready: its QA tests don't cover his words: " + "; ".join(miss)
    e = state(label)
    if (e.get("sealed") or {}).get("fp") != fp:
        return (f"{label} isn't ready: its QA tests as they stand haven't passed the hard checks (every sentence of his covered, every test "
                f"failing on the code as it is): python3 routine/qatests.py check {label}")
    if (e.get("sealed") or {}).get("rules") != RULES:
        return _rules_why(label)
    rv = in_road(e.get("reviews") or [], label)
    last = rv[-1] if rv else {}
    if last.get("fp") == fp and last.get("verdict") == "pass" and last.get("rules") == RULES:
        return None
    if last.get("fp") == fp and last.get("verdict") == "pass":
        return (f"{label} isn't ready: its QA tests' review passed them before the real-case probe ({RULES}): python3 routine/qatests.py "
                f"review {label} asks it again")
    if last.get("fp") == fp and last.get("verdict") == "flag":
        return (f"{label} isn't ready: the review of its QA tests flagged them (round {len(rv)} of {ROUNDS}): " + "; ".join(last.get("findings") or [])
                + f". Answer it in the tests, check them again, then python3 routine/qatests.py review {label}")
    return f"{label} isn't ready: its QA tests haven't had their own review as they stand: python3 routine/qatests.py review {label}"


def _rules_why(label: str) -> str:
    return (f"{label} isn't ready: its QA tests as they stand haven't passed the hard checks of the real-case rules ({RULES}, 8 November "
            f"2026: the row's own example replayed on a copy of the real data, where he would see it, failing first for the row's reason): "
            f"python3 routine/qatests.py check {label}, then their review again")


def open_points(label: str) -> list[str]:
    rv = [x for x in state(label).get("reviews") or [] if isinstance(x, dict)]
    return list((rv[-1].get("findings") or []) if rv and rv[-1].get("verdict") == "flag" else [])


def job_words(labels) -> str:
    """What a team job is told about her tests: its target, not its to change."""
    bits = []
    for lab in labels:
        e = state(lab).get("sealed") or {}
        if e.get("fp"):
            pts = open_points(lab)
            bits.append(f"{lab}: HQ/qa-tests/{lab}/ (sealed {e['fp'][:12]}, {len(e.get('tests') or [])} test(s))"
                        + (f", their review's open points: {' / '.join(pts)}" if pts else ""))
    if not bits:
        return ""
    return (" Her QA tests are the target: " + "; ".join(bits) + ". Read them, build until they pass, and don't change them: at the end the "
            "program runs them as sealed, with the 17 happy flows, and a changed test file is red.")


# ---------- their own review ----------

def _before_lines(row) -> str:
    """H342: how each sealed test failed on the code from before the build, as the seal kept it, for the reviewer."""
    b = ((state(row["label"]).get("sealed") or {}).get("before") or {})
    whys = b.get("whys") or {}
    if not whys:
        return ""
    return ("\n\nHow each test failed on the code from before the build (" + str(b.get("head") or "")[:7] + "), its own FAIL line:\n"
            + "".join(f"- {n}: {w}\n" for n, w in list(whys.items())[:40]))[:4000]


def _input(row, d) -> str:
    fs = _files(d)
    sents = his_sentences(row)
    return ("The item, as written on the planning:\n\n" + S.ask_of(row["line"])[:8000]
            + "\n\nThe user's own words in it, sentence by sentence:\n" + "".join(f"{i + 1}. {s}\n" for i, s in enumerate(sents))
            + "\nThe tests' list (tests.json):\n" + (fs["tests.json"] or "")[:4000]
            + "\n\nThe test script (test.py), run as `python3 test.py HQDIR` on the built code:\n" + (fs["test.py"] or "")[:READS]
            + _before_lines(row))


def verdict(a, sents) -> tuple[bool, list[str]] | None:
    if not isinstance(a, dict) or not isinstance(a.get("pass"), bool) or not isinstance(a.get("sentences"), list):
        return None
    got = [x for x in a["sentences"] if isinstance(x, dict)]
    if len(got) < len(sents):
        return None
    rc = a.get("real_case")  # H342: the real-case probe is part of every verdict; without it there's no verdict
    if not isinstance(rc, dict) or not isinstance(rc.get("replays"), bool):
        return None
    fs = [re.sub(r"\s+", " ", str(f)).strip()[:400] for f in a.get("findings") or [] if str(f).strip()]
    if rc["replays"] is not True:
        why = re.sub(r"\s+", " ", str(rc.get("hole") or "no test replays the row's own example on real data where he would see it"))[:300]
        if not any("real case" in f.lower() or "real data" in f.lower() or "stand-in" in f.lower() for f in fs):
            fs.insert(0, "the real-case probe: " + why)
    for s, x in zip(sents, got):
        if x.get("checked") is not True:
            why = re.sub(r"\s+", " ", str(x.get("why") or "no reason given"))[:240]  # no backslash inside an f-string: 3.9 reads these too
            h = f"his sentence \"{s[:80]}\" isn't checked by its tests: {why}"
            if not any(S._bare(s)[:30] in S._bare(f) for f in fs):
                fs.append(h)
    ok = a["pass"] and not fs
    if not ok and not fs:
        fs = ["the reviewer flagged the tests without saying why"]
    return ok, ([] if ok else fs[:5])


def _last_object(text: str) -> dict:
    """The last JSON object in the reviewer's answer that holds a verdict: the answer may carry text or a second block
    around it, which a greedy match from the first { to the last } turns into "Extra data"."""
    dec, best = json.JSONDecoder(), None
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = dec.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(obj, dict) and "pass" in obj:
            best = obj
    if best is None:
        raise ValueError("no verdict in the answer")
    return best


def _fake(d) -> dict | None:
    """HQ_REVIEW_FAKE (tests), as the item review's: "auto" flags tests whose files hold "HOLE:" and passes the rest; "fail" never answers."""
    how = os.environ.get("HQ_REVIEW_FAKE")
    if not how:
        return None
    if how == "fail":
        return {"failed": True, "why": "the fake reviewer never answers", "cost": 0}
    fs = _files(d)
    holes = [ln.split("HOLE:", 1)[1].strip()[:200] for v in fs.values() for ln in (v or "").splitlines() if "HOLE:" in ln]
    return {"pass": not holes, "findings": holes, "cost": 0, "s": 0}


def program_holes(row, d) -> list[str]:
    """H342: the stand-ins the program sees itself, whatever the reviewer says (realcase.stand_in_holes)."""
    try:
        import realcase
        return realcase.stand_in_holes(S.ask_of(row["line"]), _files(d).get("test.py") or "")
    except Exception:
        return []


def ask_reviewer(row, d) -> dict:
    a = _ask_reviewer(row, d)
    holes = [] if a.get("failed") else program_holes(row, d)
    if holes:
        a = {**a, "pass": False, "findings": (holes + [f for f in a.get("findings") or [] if f not in holes])[:5],
             "real_case": {"replays": False, "hole": holes[0], "by": "the program"}}
    return a


def _ask_reviewer(row, d) -> dict:
    fake = _fake(d)
    if fake:
        return fake
    sents = his_sentences(row)
    claude = hqpaths.tool("claude", "/opt/homebrew/bin/claude")
    t0 = time.time()
    cost = None
    try:
        p = subprocess.run([claude, "-p", "--model", MODEL, "--output-format", "json", "--tools", "", "--strict-mcp-config",
                            "--setting-sources", "", "--effort", EFFORT, "--max-budget-usd", str(BUDGET), "--no-session-persistence",
                            "--system-prompt", SYSTEM], input=_input(row, d), capture_output=True, text=True, timeout=REVIEW_TIMEOUT, cwd=E.ROOT)
        dd = json.loads(p.stdout)
        cost = dd.get("total_cost_usd")
        if dd.get("is_error") or dd.get("subtype") not in (None, "success"):
            raise ValueError(f"the run ended {dd.get('subtype') or 'with an error'}")
        obj = _last_object(dd.get("result") or "")
        v = verdict(obj, sents)
        if v is None:
            raise ValueError("the answer wasn't a verdict on every sentence with the real-case probe")
        return {"pass": v[0], "findings": v[1], "cost": cost, "s": round(time.time() - t0, 1), "real_case": obj.get("real_case")}
    except subprocess.TimeoutExpired:
        return {"failed": True, "why": f"timed out after {REVIEW_TIMEOUT} s", "cost": cost}
    except Exception as ex:
        return {"failed": True, "why": str(ex)[:200] or repr(ex), "cost": cost}


def review(label: str) -> tuple[int, str]:
    """One round of their own review. (exit code, what to say): 0 passed, 1 flagged, 2 refused or didn't run."""
    label = label.strip().upper()
    row = _row(label)
    if not row:
        return 2, f"Refused: {label} isn't an open row on the planning."
    d = folder(label)
    fp = fingerprint_of(d)
    e = state(label)
    if not fp or (e.get("sealed") or {}).get("fp") != fp:
        return 2, f"Refused: {label}'s QA tests as they stand aren't sealed: python3 routine/qatests.py check {label} first."
    if (e.get("sealed") or {}).get("rules") != RULES:
        return 2, (f"Refused: {label}'s QA tests were sealed before the real-case rules ({RULES}): python3 routine/qatests.py check {label} "
                   "first, so they're held to fail first for the row's reason; then their review.")
    rv, k_ = in_road(e.get("reviews") or [], label), cycle(label)
    if len(rv) >= ROUNDS:
        return 2, (f"Refused: {ROUNDS} rounds have run on {label}'s QA tests; no round {ROUNDS + 1}. They're his decision now, with the "
                   "open points he has; flagged tests never go to the team, his now neither.")
    if rv and rv[-1].get("fp") == fp and rv[-1].get("rules") == RULES:  # the same version again: the verdict stands, no new look, and it counts as a round
        a = {"pass": rv[-1].get("verdict") == "pass", "findings": list(rv[-1].get("findings") or []), "cost": 0, "same": True}
    else:
        a = ask_reviewer(row, d)
    rec = {"row": label, "at": int(time.time()), "fp": fp[:16], "kind": "qa-tests", "model": MODEL, "effort": EFFORT, "cost": a.get("cost")}
    if a.get("failed"):
        _cost_line({**rec, "failed": True, "why": a.get("why")})
        return 2, f"The review of {label}'s QA tests didn't run ({a.get('why')}); nothing counted. Try again."
    if fingerprint_of(d) != fp:
        return 2, f"{label}'s QA tests changed while they were reviewed; nothing counted."
    entry = {"fp": fp, "at": int(time.time()), "verdict": "pass" if a["pass"] else "flag", "findings": a["findings"], "cost": a.get("cost"),
             "cycle": k_, "rules": RULES, **({"real_case": a["real_case"]} if a.get("real_case") else {})}
    e = _put(label, lambda x: x.update({"reviews": [y for y in x.get("reviews") or [] if isinstance(y, dict)] + [entry]}))
    _cost_line({**rec, "verdict": entry["verdict"], "findings": len(a["findings"])})
    try:
        import trail
        trail.step(trail.resolve(label), "qa_tests_review", verdict=entry["verdict"], findings=len(a["findings"]))
    except Exception:
        pass
    k = len(in_road(e["reviews"], label))
    same = " (unchanged since the round before, so its verdict stands)" if a.get("same") else ""
    if a["pass"]:
        return 0, f"Round {k} of {ROUNDS}: the review passed {label}'s QA tests{same}."
    fs = "".join(f"\n{i + 1}. {f}" for i, f in enumerate(a["findings"]))
    if k >= ROUNDS:
        tell(label, "qa-tests" + (f"-{k_}" if k_ else ""), f"Her QA tests for {label} were flagged {ROUNDS} times by their review; it's your "
             "decision now. The open points: " + " ".join(f"({i + 1}) {f}" for i, f in enumerate(a["findings"]))
             + f" Flagged tests never go to the team, your now neither.")
        return 1, (f"Round {k} of {ROUNDS}: the review flagged {label}'s QA tests{same}:{fs}\nThat was the last round: it comes to him as his "
                   "decision, the open points in one text; flagged, it never goes to the team.")
    return 1, (f"Round {k} of {ROUNDS}: the review flagged {label}'s QA tests{same}:{fs}\nAnswer each in the tests, python3 routine/qatests.py "
               f"check {label}, then review {label} for round {k + 1}.")


def _cost_line(rec: dict) -> None:
    try:
        os.makedirs(E.DIR, exist_ok=True)
        with open(os.path.join(E.DIR, "reviews.jsonl"), "a") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        pass


def tell(label: str, kind: str, words: str) -> bool:
    """One message to him on her line, once per item and kind (its id), the open points as they are (no rewording)."""
    if hqpaths.under_test() and not os.environ.get("HQ_DIRECT_DIR"):
        return False
    mid = f"qa-{kind}-{label}"
    if mid in (state(label).get("told") or []):
        return False
    hq = hqpaths.HQ
    py = os.path.join(hq, ".venv", "bin", "python")
    try:
        r = subprocess.run([py if os.path.exists(py) else sys.executable, os.path.join(hq, "app", "direct_line.py"), "text", "team", words,
                            "--item", label, "--once", mid], cwd=hq, env={**os.environ, "HQ_DIRECT_PLAIN": "1"}, text=True,
                           capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as ex:
        print(f"(the message to him didn't go: {ex!r})", file=sys.stderr)
        return False
    if r.returncode:
        print(f"(the message to him didn't go: {(r.stdout + r.stderr)[-300:]})", file=sys.stderr)
        return False
    _put(label, lambda e: e.update({"told": (e.get("told") or []) + [mid]}))
    return True


# ---------- the end: the sealed tests on the built copy ----------

def end_run(label: str | None, wt: str) -> dict:
    """For proof.py: the sealed tests on the built copy. {"ran", "passed", "failed", "green", "why"}. A build for a row with no sealed
    tests, or whose tests changed since they were sealed (in the workspace or in the program's copy), is red."""
    out = {"ran": 0, "passed": 0, "failed": [], "green": False}
    if not label:
        out["why"] = "the job names no row, so there are no QA tests of hers to run"
        return out
    e = state(label).get("sealed") or {}
    if not e.get("fp"):
        out["why"] = f"{label} has no sealed QA tests of hers: it went to the team without them"
        return out
    now_fp = fingerprint(label)
    kept = e.get("copy") or ""
    kept_fp = fingerprint_of(kept) if kept else None
    if kept_fp != e["fp"]:
        out["why"] = f"the program's sealed copy of {label}'s QA tests is gone or changed"
        return out
    if now_fp != e["fp"]:
        out["why"] = (f"{label}'s QA tests changed in the workspace since they were sealed ({e['fp'][:12]}, now {(now_fp or 'gone')[:12]}): "
                      "the team can't change them")
        out["changed"] = True
        return out
    got, log = run_on(kept, wt)
    names = e.get("tests") or []
    out["ran"] = len(names)
    out["passed"] = sum(1 for n in names if got.get(n))
    out["failed"] = [n for n in names if not got.get(n)]
    out["green"] = bool(names) and not out["failed"]
    if out["failed"]:
        team = _team_run(kept, wt, out["failed"])
        parts = []
        for n in out["failed"]:
            why = _why(log, n)
            if team.get(n):  # F173: the team's run on the working HQ passed it; only the proof's copy fails it, named so
                parts.append(f"{n} passes in the team's run, fails in the proof's copy: {why}")
            else:
                parts.append(f"{n}: {why}")
        out["split"] = [n for n in out["failed"] if team.get(n)]
        out["why"] = "her QA tests fail on the built code: " + "; ".join(parts)
        out["log"] = log[-800:]
    elif out["green"] and os.environ.get("HQ_QA_NEIGHBOURS", "1") != "0":
        _neighbours_run(label, wt, out)
    return out


# ---------- H342: the neighbours, so a fix doesn't break the item next to it ----------
# His row: "a build also runs the sealed tests of the items it touches and the flows around them on the same copy, and a test can only
# write into its own copy". Twice on 7 November 2026 a fix broke the item next to it (F192's hold made F197; H339's tests wrote made-up
# usage into HQ's real file, F198). An item touches this build when its own commits (named at the start of their subject) changed a file
# this build's commits changed, the shared test and version files left out (qa.FREE_FILES), or its sealed test imports one of the
# Python files this build changed. Each runs through run_on: its own throwaway copy, behind the wall.

def _git_lines(root: str, *a) -> str:
    return subprocess.run(["git", "-C", str(root), *a], text=True, capture_output=True).stdout


def _commits_files(root: str, rng: str) -> list[tuple[list[str], set[str]]]:
    """(the rows a commit is for, the files it changed) for each commit in rng, merges left out."""
    import qa
    out = []
    for rec in _git_lines(root, "log", "--no-merges", "--format=%x00%s", "--name-only", rng).split("\x00")[1:]:
        lines = rec.split("\n")
        labs = qa.subject_labels(lines[0])
        files = {f.strip() for f in lines[1:] if f.strip()}
        if labs and files:
            out.append((labs, files))
    return out


def _build_range(label: str, wt: str) -> str:
    """The commits this build is made of: since its tests were sealed when that commit is in its history, else all of it."""
    head = ((state(label).get("sealed") or {}).get("before") or {}).get("head") or ""
    if head and not subprocess.run(["git", "-C", wt, "merge-base", "--is-ancestor", head, "HEAD"], capture_output=True).returncode:
        return f"{head}..HEAD"
    return "HEAD"


def base_commit(label: str, wt: str) -> str | None:
    """The code from just before this build: the parent of the oldest commit naming the row in its range, or None."""
    import qa
    first = None
    for ln in _git_lines(wt, "log", "--reverse", "--no-merges", "--format=%H%x09%s", _build_range(label, wt)).splitlines():
        sha, _, subj = ln.partition("\t")
        if label in qa.subject_labels(subj):
            first = sha
            break
    if not first:
        return None
    return _git_lines(wt, "rev-parse", "--verify", "--quiet", f"{first}^").strip() or None


def build_files(label: str, wt: str) -> set[str]:
    """The files this build changed: the commits naming the row since its tests were sealed (else in all of history), the free files out."""
    import qa
    rng = _build_range(label, wt)
    files = set()
    for labs, fs in _commits_files(wt, rng):
        if label in labs:
            files |= fs
    return {f for f in files if not f.startswith(qa.FREE_FILES)}


def neighbours(label: str, wt: str, most: int | None = None, skipped: list | None = None) -> list[dict]:
    """The items whose sealed tests a build for label runs too: [{"label", "files", "imports", "tests"}], the most touched first.
    skipped, when given, gets the touched items that aren't run, each with why (a fix road open: its tests are red by design)."""
    import qa
    label = label.strip().upper()
    mine = build_files(label, wt)
    if not mine:
        return []
    by = {}
    for labs, fs in _commits_files(wt, "HEAD"):
        for l in labs:
            by.setdefault(l, set()).update(fs)
    mods = {os.path.splitext(os.path.basename(f))[0] for f in mine if f.endswith(".py")}
    found = []
    for lab, e in _all().items():
        s = e.get("sealed") or {}
        if lab == label or not s.get("fp") or not s.get("copy") or fingerprint_of(s["copy"]) != s["fp"]:
            continue
        files = sorted(f for f in (by.get(lab) or set()) & mine if not f.startswith(qa.FREE_FILES))
        body = _files(s["copy"]).get("test.py") or ""
        imports = sorted(m for m in mods if re.search(rf"^\s*(?:import\s+[\w, ]*\b{re.escape(m)}\b|from\s+{re.escape(m)}\s+import)", body, re.M))
        if not files and not imports:
            continue
        tests = list(s.get("tests") or [])
        road = None
        for r in reversed([x for x in e.get("qa_fails") or [] if isinstance(x, dict)]):
            road = r if not r.get("passed") else None
            break
        if road:  # a fix road's new tests are red by design until that fix lands: only the ones from before it are guarded
            before = set(road.get("tests_before") or [])
            tests = [n for n in tests if n in before]
            if not tests and skipped is not None:
                skipped.append({"label": lab, "files": files, "imports": imports,
                                "why": f"its fix road is open (QA failed it): its {len(s.get('tests') or [])} sealed test(s) are new on that road, "
                                       "red by design until its fix lands, so none is known green to guard"})
        if tests:
            found.append({"label": lab, "files": files, "imports": imports, "tests": tests, "copy": s["copy"], "at": s.get("at") or 0})
    found.sort(key=lambda x: (-(2 * len(x["files"]) + len(x["imports"])), -x["at"]))
    return found[: NEIGHBOURS_MOST if most is None else most]


def _neighbours_run(label: str, wt: str, out: dict) -> None:
    """The neighbours' sealed tests on the built copy, each on its own throwaway copy; a red one makes this build's run red, named."""
    import proof
    skipped: list = []
    try:
        near = neighbours(label, wt, skipped=skipped)
    except Exception as ex:  # a neighbour that can't be found is said, never a silent green
        out.update(green=False, why=f"the items this build touches couldn't be found: {ex!r}"[:300])
        return
    try:
        text = q.read()[0]
    except Exception:
        text = ""
    done = []
    for nb in near:
        got, log = run_on(nb["copy"], wt)
        failed = [n for n in nb["tests"] if not got.get(n)]
        flows = proof.named_flows(proof.row_of(text, nb["label"]))
        done.append({"label": nb["label"], "files": nb["files"], "imports": nb["imports"], "ran": len(nb["tests"]),
                     "failed": failed, "flows": flows, **({"why": "; ".join(f"{n}: {_why(log, n)}" for n in failed)[:600]} if failed else {})})
    # a neighbour's red counts against this build only when its test passed on the code from just before it: one already red there
    # (its own open fault, or a test that can't pass on this computer) is named, not this build's
    reds = [d for d in done if d["failed"]]
    if reds:
        base = base_commit(label, wt)
        bwt = None
        try:
            bwt = proof._copy(base) if base else None
        except Exception:
            bwt = None
        try:
            for d in reds:
                if not bwt:
                    d["broken"] = list(d["failed"])
                    d["before"] = "the code from before this build couldn't be copied, so every red counts"
                    continue
                got_b, _ = run_on(next(nb["copy"] for nb in near if nb["label"] == d["label"]), bwt)
                d["already_red"] = [n for n in d["failed"] if not got_b.get(n)]
                d["broken"] = [n for n in d["failed"] if got_b.get(n)]
                d["before"] = base[:7]
        finally:
            if bwt:
                proof._uncopy(bwt)
    red = [d for d in done if d.get("broken")]
    out["neighbours"] = done
    if skipped:
        out["neighbours_skipped"] = skipped
    out["neighbour_flows"] = sorted({f for d in done for f in d["flows"]})
    if red:
        out["green"] = False
        out["why"] = "this build breaks the sealed QA tests of an item it touches: " + "; ".join(
            f"{d['label']} (touched through {', '.join(d['files'] + d['imports'])[:120]}; "
            + (f"{', '.join(d['broken'])} passed on the code from before it ({d['before']}) and fail now" if "already_red" in d else d["before"])
            + f": {d['why']}; "
            + (f"its flows {', '.join(map(str, d['flows']))} run with the build's" if d["flows"] else "its row names no flows of its own") + ")"
            for d in red)
        out["neighbours_red"] = [d["label"] for d in red]


def neighbours_words(label: str, wt: str) -> str:
    skipped: list = []
    near = neighbours(label, wt, skipped=skipped)
    out = ([f"A build for {label} also runs the sealed QA tests of {len(near)} item(s) it touches:"] if near else
           [f"A build for {label} runs no neighbour's sealed QA tests."])
    out += [f"- {n['label']}: {len(n['tests'])} test(s), through " + ", ".join(n["files"] + [f"import {m}" for m in n["imports"]]) for n in near]
    out += [f"- {n['label']}: touched through " + ", ".join(n["files"] + [f"import {m}" for m in n["imports"]]) + f", not run: {n['why']}" for n in skipped]
    return "\n".join(out)


def _why(log: str, name: str) -> str:
    """Her test's own why for a failed test, from its FAIL line."""
    for ln in log.splitlines():
        m = _LINE.match(ln)
        if m and m.group(2) == name and m.group(1) == "FAIL":
            return (m.group(3) or "no why given").strip()[:300]
    return "it gave no line (it didn't run to it)"


def _team_run(d: str, wt: str, failed: list) -> dict:
    """F173: the same tests on the working HQ (the one the workspace is in), the team's own run, to tell a test that only fails in
    the proof's copy from a real red. {} when the copy is the working HQ itself."""
    live = os.path.dirname(os.path.realpath(os.path.join(hqpaths.HQ, "workspace")))
    if not failed or os.path.realpath(wt) == live:
        return {}
    got, _ = run_on(d, live)
    return got


def done_refuses(j: dict) -> str | None:
    """For jobs.py done: why a build job can't be done on her QA tests, or None. His words on done never skip this."""
    if not gate_on():
        return None
    import proof
    if not proof.needs(j):
        return None
    label = proof.label_of(j)
    if not label:
        return None
    rec = proof.load(j["n"]) or {}
    qa = rec.get("qa_tests")
    if not qa:
        return f"job {j['n']} has no run of {label}'s QA tests at the end: python3 routine/proof.py run {j['n']} runs them with the 17."
    if not qa.get("green"):
        return f"job {j['n']}'s QA tests aren't green: {qa.get('why') or ', '.join(qa.get('failed') or [])}."
    e = state(label).get("sealed") or {}
    if fingerprint(label) != e.get("fp"):
        return f"{label}'s QA tests changed since they were sealed: the team can't change them."
    return None


def new(label: str) -> str:
    label = label.strip().upper()
    row = _row(label)
    if not row:
        return f"Refused: {label} isn't an open row on the planning."
    d = folder(label)
    os.makedirs(d, exist_ok=True)
    if not os.path.exists(os.path.join(d, "tests.json")):
        json.dump({"sentences": [{"his": s, "tests": []} for s in his_sentences(row)], "tests": {}}, open(os.path.join(d, "tests.json"), "w", encoding="utf8"),
                  ensure_ascii=False, indent=1)
    if not os.path.exists(os.path.join(d, "test.py")):
        open(os.path.join(d, "test.py"), "w", encoding="utf8").write(
            "#!/usr/bin/env python3\n# Her QA tests for " + label + ": run as `python3 test.py HQDIR` on the built code; one line per test.\n"
            "# H342: the row's own done example is the test, replayed on real data (the real row, the real text, the real job), read where\n"
            "# he would see it: realcase.Case(HQDIR) is a throwaway HQ of this code on a copy of the real workspace and of HQ's .status;\n"
            "# with case.serve() as page: page.rendered() is the status page as he sees it; case.thread(\"team\") the texts as they landed.\n"
            "# It must fail on the code from before the build, for the row's reason, with a FAIL line saying what he'd see instead.\n"
            "import sys, pathlib\nhq = pathlib.Path(sys.argv[1])\nsys.path.insert(0, str(hq / \"routine\"))\nimport realcase\n\n\n"
            "def t(name, ok, why):\n"
            "    print((\"PASS \" if ok else \"FAIL \") + name + (\"\" if ok else \": \" + why), flush=True)\n\n\n"
            "# case = realcase.Case(sys.argv[1])\n"
            "# t(\"name\", what he'd see is right, \"what he'd see instead\")\n")
    return (f"HQ/qa-tests/{label}/ started: his {len(his_sentences(row))} sentence(s) in tests.json, each needing at least one test; write "
            f"the tests in test.py as he'd see the result: the row's own example replayed on the real data of the copy, read where he "
            f"looks (routine/realcase.py), then python3 routine/qatests.py check {label}.")


def show(label: str) -> str:
    label = label.strip().upper()
    row = _row(label)
    e = state(label)
    fp = fingerprint(label)
    s = e.get("sealed") or {}
    rv = e.get("reviews") or []
    lines = [f"{label}: QA tests " + ("there" if fp else "not written") + (", sealed as they stand" if fp and s.get("fp") == fp else
                                                                             (", changed since sealed" if s.get("fp") else ", not sealed"))]
    if s.get("fp"):
        b = s.get("before") or {}
        lines.append(f"- sealed on {(b.get('head') or '?')[:7]}" + (", the commit named as from before the build" if b.get("named") else
                                                                    ", HQ's code as it was"))
    if rv:
        lines.append(f"- their review: round {len(in_road(rv, label))} of {ROUNDS}, {rv[-1].get('verdict')}" + ("" if rv[-1].get("fp") == fp else " (on an earlier wording)")
                     + "".join(f"\n  - {f}" for f in rv[-1].get("findings") or []))
    if row:
        w = why_not(row)
        lines.append("- " + (w or "nothing of hers holds the Ready mark"))
    return "\n".join(lines)


def main(argv) -> int:
    if len(argv) >= 2 and argv[0] in ("check", "review", "new", "show"):
        lab = argv[1]
        if argv[0] == "check":
            if "--before" in argv and (argv.index("--before") + 1 >= len(argv) or not argv[argv.index("--before") + 1].strip()):
                print("Refused: --before needs a commit. Nothing sealed.")
                return 1
            import proof
            was = proof._on_stop()  # F193: a stop (a timeout's SIGTERM, the runner's stop) is a normal end: its copies are removed
            try:
                ok, words = check(lab, before=argv[argv.index("--before") + 1] if "--before" in argv else None)
            except proof.Stopped as e:
                print(f"Stopped ({e}): its throwaway copies are removed. Nothing sealed.")
                return 143
            finally:
                proof._off_stop(was)
            print(words)
            return 0 if ok else 1
        if argv[0] == "review":
            code, words = review(lab)
            print(words)
            return code
        print(new(lab) if argv[0] == "new" else show(lab))
        return 0
    if len(argv) >= 3 and argv[0] == "run":
        import proof
        was = proof._on_stop()  # F193: a run stopped like a timeout ends like a stopped check: its tests stopped, its copies removed
        try:
            res = end_run(argv[1].upper(), os.path.realpath(argv[2]))
        except proof.Stopped as e:
            print(json.dumps({"ran": 0, "passed": 0, "failed": [], "green": False, "stopped": True,
                              "why": f"the run of her tests was stopped ({e}): its tests are stopped, its throwaway copies removed"}))
            return 143
        finally:
            proof._off_stop(was)
        print(json.dumps(res, ensure_ascii=False))
        return 0
    if len(argv) >= 2 and argv[0] == "neighbours":
        import proof
        print(neighbours_words(argv[1].upper(), os.path.realpath(argv[2]) if len(argv) >= 3 else str(proof.ROOT)))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
