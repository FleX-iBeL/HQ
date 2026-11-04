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
  - their own review, apart from the item's: its own prompt and verdict, at most ROUNDS rounds (one per wording), and after the last
    flagged one a single message to him with all the open points;
  - the Ready mark (sprint.set_ready), the way to the team (sprint.gate: jobs.py add and send-row, his now too) and the end
    (proof.py runs the sealed tests on the built copy; jobs.py done and qa.py pass read that, his words on done don't skip it).
His now may send an item whose tests' review flagged them three times, with the open points, but never past the coverage, the run
before, or the run at the end. The team sees her tests as the target and can't change them: the fingerprint is checked at the end.

    python3 routine/qatests.py new LABEL       start her folder: his sentences in tests.json, a test.py to fill in
    python3 routine/qatests.py check LABEL     the two hard checks; seals them when they hold
    python3 routine/qatests.py review LABEL    one round of their own review (the real reviewer), ROUNDS at most
    python3 routine/qatests.py show LABEL      where they stand
    python3 routine/qatests.py run LABEL HQDIR the sealed tests on HQDIR (what proof.py does at the end)
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

ROUNDS = 3
RUN_TIMEOUT = 300  # seconds for one run of her tests
REVIEW_TIMEOUT = 240
BUDGET = 0.25
MODEL = os.environ.get("HQ_QA_REVIEW_MODEL") or os.environ.get("HQ_REVIEW_MODEL") or "sonnet"
EFFORT = os.environ.get("HQ_QA_REVIEW_EFFORT") or "medium"
READS = 20000
_LINE = re.compile(r"^\s*(PASS|FAIL)\s+([A-Za-z0-9_.-]+)\s*(?::\s*(.*))?$")

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
    "puts out of scope, a requirement you invent. Answer with JSON only, nothing else: "
    '{"sentences": [{"his": "the sentence", "checked": true or false, "why": "one plain sentence"}, ... one per sentence, in order], '
    '"pass": true or false, "findings": ["one plain sentence per hole, naming the test", ...]}. pass is false exactly when a sentence '
    "isn't checked or you found another real hole; at most four findings, the most important first.")


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

def run_on(d: str, hqdir: str) -> tuple[dict, str]:
    """Her test.py in folder d on the code at hqdir: ({name: passed}, its output)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("HQ_")}
    env.update({"HQ_UNDER_TEST": "1", "HQ_QA_TEST_RUN": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    try:
        r = subprocess.run([sys.executable, os.path.join(d, "test.py"), hqdir], cwd=hqdir, env=env, text=True, capture_output=True,
                           timeout=RUN_TIMEOUT, stdin=subprocess.DEVNULL)
        out = (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        return {}, f"her tests didn't finish in {RUN_TIMEOUT} s"
    got = {}
    for ln in out.splitlines():
        m = _LINE.match(ln)
        if m:
            got[m.group(2)] = got.get(m.group(2), True) and m.group(1) == "PASS"
    return got, out[-3000:]


def _head() -> str:
    import proof
    return subprocess.run(["git", "-C", str(proof.ROOT), "rev-parse", "HEAD"], text=True, capture_output=True).stdout.strip()


def check(label: str) -> tuple[bool, str]:
    """The two hard checks on her tests as they stand; sealed when both hold. (ok, what to say)."""
    label = label.strip().upper()
    row = _row(label)
    if not row:
        return False, f"Refused: {label} isn't an open row on the planning."
    d = folder(label)
    fp = fingerprint_of(d)
    if not fp:
        return False, (f"Refused: {label} has no QA tests of hers: HQ/qa-tests/{label}/test.py and tests.json "
                       f"(python3 routine/qatests.py new {label} starts them).")
    t, why = read_list(d)
    if t is None:
        return False, f"Refused: {label}'s QA tests: {why}."
    miss = coverage(row, t)
    if miss:
        return False, f"Refused: {label}'s QA tests don't cover his words: " + "; ".join(miss) + ". Nothing sealed."
    names = named_tests(t)
    import proof
    head = _head()
    wt = proof._copy(head)
    try:
        got, out = run_on(d, wt)
    finally:
        proof._uncopy(wt)
    unrun = [n for n in names if n not in got]
    if unrun:
        return False, (f"Refused: {label}'s test.py never reports {', '.join(unrun)} (a line \"PASS name\" or \"FAIL name: why\" for each), "
                       f"so those tests don't exist. Its output: {out[-400:]!r}. Nothing sealed.")
    passing = [n for n in names if got.get(n)]
    if passing:
        return False, (f"Refused: {label}'s test(s) {', '.join(passing)} already pass on HQ's code as it is ({head[:7]}), before any "
                       "build, so they don't test what he asked for. Each test must fail now and pass once it's built. Nothing sealed.")
    keep = os.path.join(seal_root(), label, fp[:16])
    shutil.rmtree(keep, ignore_errors=True)
    os.makedirs(keep, exist_ok=True)
    for f in ("test.py", "tests.json"):
        shutil.copy2(os.path.join(d, f), os.path.join(keep, f))
    sealed = {"fp": fp, "at": int(time.time()), "copy": keep, "his": len(his_sentences(row)), "tests": names,
              "before": {"head": head, "results": {n: got[n] for n in names}}}
    _put(label, lambda e: e.update({"sealed": sealed}))
    try:
        import trail
        trail.step(trail.resolve(label), "qa_tests", fp=fp[:16], tests=len(names), before=head[:12])
    except Exception:
        pass
    return True, (f"{label}'s QA tests are sealed: {len(names)} test(s) for his {sealed['his']} sentence(s), every one failing on "
                  f"{head[:7]} as it should. Next, their own review: python3 routine/qatests.py review {label}.")


def why_not(row, now: bool = False) -> str | None:
    """Why her QA tests keep this row from the Ready mark (now=False) or from the team on his now (now=True), or None. The hard checks
    always; the review must have passed them as they stand, or, on his now only, have run its ROUNDS rounds."""
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
    rv = [x for x in e.get("reviews") or [] if isinstance(x, dict)]
    last = rv[-1] if rv else {}
    if last.get("fp") == fp and last.get("verdict") == "pass":
        return None
    if now and len(rv) >= ROUNDS:
        return None
    if last.get("fp") == fp and last.get("verdict") == "flag":
        return (f"{label} isn't ready: the review of its QA tests flagged them (round {len(rv)} of {ROUNDS}): " + "; ".join(last.get("findings") or [])
                + f". Answer it in the tests, check them again, then python3 routine/qatests.py review {label}")
    return f"{label} isn't ready: its QA tests haven't had their own review as they stand: python3 routine/qatests.py review {label}"


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

def _input(row, d) -> str:
    fs = _files(d)
    sents = his_sentences(row)
    return ("The item, as written on the planning:\n\n" + S.ask_of(row["line"])[:8000]
            + "\n\nThe user's own words in it, sentence by sentence:\n" + "".join(f"{i + 1}. {s}\n" for i, s in enumerate(sents))
            + "\nThe tests' list (tests.json):\n" + (fs["tests.json"] or "")[:4000]
            + "\n\nThe test script (test.py), run as `python3 test.py HQDIR` on the built code:\n" + (fs["test.py"] or "")[:READS])


def verdict(a, sents) -> tuple[bool, list[str]] | None:
    if not isinstance(a, dict) or not isinstance(a.get("pass"), bool) or not isinstance(a.get("sentences"), list):
        return None
    got = [x for x in a["sentences"] if isinstance(x, dict)]
    if len(got) < len(sents):
        return None
    fs = [re.sub(r"\s+", " ", str(f)).strip()[:400] for f in a.get("findings") or [] if str(f).strip()]
    for s, x in zip(sents, got):
        if x.get("checked") is not True:
            h = f"his sentence \"{s[:80]}\" isn't checked by its tests: {re.sub(r'\s+', ' ', str(x.get('why') or 'no reason given'))[:240]}"
            if not any(S._bare(s)[:30] in S._bare(f) for f in fs):
                fs.append(h)
    ok = a["pass"] and not fs
    if not ok and not fs:
        fs = ["the reviewer flagged the tests without saying why"]
    return ok, ([] if ok else fs[:5])


def ask_reviewer(row, d) -> dict:
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
        found = re.findall(r"\{.*\}", dd.get("result") or "", re.S)
        v = verdict(json.loads(found[-1]), sents)
        if v is None:
            raise ValueError("the answer wasn't a verdict on every sentence")
        return {"pass": v[0], "findings": v[1], "cost": cost, "s": round(time.time() - t0, 1)}
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
    rv = [x for x in e.get("reviews") or [] if isinstance(x, dict)]
    if rv and rv[-1].get("fp") == fp:
        return 2, (f"Refused: {label}'s QA tests haven't changed since round {len(rv)} ({rv[-1].get('verdict')}). Answer its points in the "
                   f"tests, check them again, then review again.")
    if len(rv) >= ROUNDS:
        return 2, (f"Refused: {ROUNDS} rounds have run on {label}'s QA tests; he has their open points. His now may send it with them, never "
                   "past the hard checks.")
    a = ask_reviewer(row, d)
    rec = {"row": label, "at": int(time.time()), "fp": fp[:16], "kind": "qa-tests", "model": MODEL, "effort": EFFORT, "cost": a.get("cost")}
    if a.get("failed"):
        _cost_line({**rec, "failed": True, "why": a.get("why")})
        return 2, f"The review of {label}'s QA tests didn't run ({a.get('why')}); nothing counted. Try again."
    if fingerprint_of(d) != fp:
        return 2, f"{label}'s QA tests changed while they were reviewed; nothing counted."
    entry = {"fp": fp, "at": int(time.time()), "verdict": "pass" if a["pass"] else "flag", "findings": a["findings"], "cost": a.get("cost")}
    e = _put(label, lambda x: x.update({"reviews": [y for y in x.get("reviews") or [] if isinstance(y, dict)] + [entry]}))
    _cost_line({**rec, "verdict": entry["verdict"], "findings": len(a["findings"])})
    try:
        import trail
        trail.step(trail.resolve(label), "qa_tests_review", verdict=entry["verdict"], findings=len(a["findings"]))
    except Exception:
        pass
    k = len(e["reviews"])
    if a["pass"]:
        return 0, f"Round {k} of {ROUNDS}: the review passed {label}'s QA tests."
    fs = "".join(f"\n{i + 1}. {f}" for i, f in enumerate(a["findings"]))
    if k >= ROUNDS:
        tell(label, "qa-tests", f"Her QA tests for {label} were flagged {ROUNDS} times by their review; the open points: "
             + " ".join(f"({i + 1}) {f}" for i, f in enumerate(a["findings"])) + f" His now may still send {label} with these points; "
             "the hard checks hold either way.")
        return 1, f"Round {k} of {ROUNDS}: the review flagged {label}'s QA tests:{fs}\nThat was the last round: he has the open points now."
    return 1, (f"Round {k} of {ROUNDS}: the review flagged {label}'s QA tests:{fs}\nAnswer each in the tests, python3 routine/qatests.py "
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
        out["why"] = f"her QA tests {', '.join(out['failed'])} fail on the built code"
        out["log"] = log[-800:]
    return out


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
            "import sys, pathlib\nhq = pathlib.Path(sys.argv[1])\n\n\ndef t(name, ok, why):\n"
            "    print((\"PASS \" if ok else \"FAIL \") + name + (\"\" if ok else \": \" + why), flush=True)\n\n\n"
            "# t(\"name\", what he'd see is right, \"what he'd see instead\")\n")
    return (f"HQ/qa-tests/{label}/ started: his {len(his_sentences(row))} sentence(s) in tests.json, each needing at least one test; write "
            f"the tests in test.py as he'd see the result, then python3 routine/qatests.py check {label}.")


def show(label: str) -> str:
    label = label.strip().upper()
    row = _row(label)
    e = state(label)
    fp = fingerprint(label)
    s = e.get("sealed") or {}
    rv = e.get("reviews") or []
    lines = [f"{label}: QA tests " + ("there" if fp else "not written") + (", sealed as they stand" if fp and s.get("fp") == fp else
                                                                             (", changed since sealed" if s.get("fp") else ", not sealed"))]
    if rv:
        lines.append(f"- their review: round {len(rv)} of {ROUNDS}, {rv[-1].get('verdict')}" + ("" if rv[-1].get("fp") == fp else " (on an earlier wording)")
                     + "".join(f"\n  - {f}" for f in rv[-1].get("findings") or []))
    if row:
        w = why_not(row)
        lines.append("- " + (w or "nothing of hers holds the Ready mark"))
    return "\n".join(lines)


def main(argv) -> int:
    if len(argv) >= 2 and argv[0] in ("check", "review", "new", "show"):
        lab = argv[1]
        if argv[0] == "check":
            ok, words = check(lab)
            print(words)
            return 0 if ok else 1
        if argv[0] == "review":
            code, words = review(lab)
            print(words)
            return code
        print(new(lab) if argv[0] == "new" else show(lab))
        return 0
    if len(argv) >= 3 and argv[0] == "run":
        print(json.dumps(end_run(argv[1].upper(), os.path.realpath(argv[2])), ensure_ascii=False))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
