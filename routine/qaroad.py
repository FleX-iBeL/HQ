#!/usr/bin/env python3
"""qaroad (4 November 2026): the acceptance test for real QA, written before it was built. His design, laptop chat of 4 November 2026:
"i want her to seperate from the checklist, also write QA tests, and then test it at the end", "based on the context, of what we want to
have achieved as the end user", "the point is she cant blindly make these QA tests without anyone checking her work either", and his
principle: "the team (the tooling/system) is there to keep her in check, prompting is last line of defense not first."

On a throwaway copy of the workspace (routine/nowroad.py's copy: the real reviewer, the real looks at his words), each of her steps run as
she runs it from a text (the copy's own app/policy.py first, then the command with her text's environment). It checks:

  1  an item without her QA tests gets no Ready mark and doesn't go to the team, not with --not-ready --now either
  2  her tests get a second review of their own: its own prompt and verdict, kept apart from the item's review
  3  each review: at most 3 rounds, then one message to him with all the open points
  4  every sentence of his words has a test of hers, or the program refuses them
  5  her tests must fail on the code as it is (the program runs them before the build), or they're refused
  6  a team job can't change her tests: their fingerprint is checked at the end, and a changed one is red
  7  at the end the program runs her tests plus the 17: only green passes, and his now (his words on done) never skips 4, 5 or 7
  H  (with --her) Moneypenny's own model on his real text with his now (direct_line.py --team reply): no job leaves without her sealed tests

The 17 happy flows are a stand-in here (HQ_PROOF_RUNNER, the proof's own test hook): they run for real on their own (routine/happy.py run).
Her tests and both reviews are real.

    python3 routine/qaroad.py run ROOT [--workspace PATH] [--her] [--keep]    ROOT a new folder, cleaned after; exit 0 only when all pass
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chainrun  # noqa: E402
import nowroad  # noqa: E402

nowroad.PORTS, nowroad.TEST_PORT = (7863, 4763), 7903  # its own ports: nowroad may run next to it

PY = sys.executable
T0 = time.time()
RESULTS: dict[str, list] = {}
WITH_HER = False

WORDS_A = chainrun.WORDS  # "On the status page, when nothing is on the schedule, it just says Nothing planned. I'd like it to say Nothing planned yet, ..."
WORDS_B = "The other cards on the status page say Nothing yet. when they are empty. I'd like them to say Nothing here yet, it reads friendlier."
NOW = "Give it to the team and let's run it immediately."
NOW_B = "Give that one to the team as well, run it right away."  # his now for B in words of its own, so the look reads each text on its own row
ROW = ("{title}. What's asked: on the status page, {what}. Done means: open the status page with {empty} and read {new} there; the words {old} "
       "no longer stand on that card; the other empty words stay as they are. Test: her QA tests for this row, and the 17 happy flows. "
       "Why: {why}. Out of scope: every other text on the page. Touches: status/index.html only, one string. Size: a few minutes. "
       "Waits on: nothing. Privacy check: nothing personal, it's a word on a page.")

GOOD_TESTS = r'''#!/usr/bin/env python3
# Her QA tests for the empty schedule's words, as he reads them on the status page.
import re, sys, pathlib
hq = pathlib.Path(sys.argv[1])
page = (hq / "status" / "index.html").read_text(encoding="utf8")
coming = re.search(r"if \(!list\.length\) card\.append\(el\('div', 'row soft', key === 'coming' \? (['\"`])(.*?)\1", page)
said = coming.group(2) if coming else None
def t(name, ok, why):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else ": " + why), flush=True)
t("says_yet", said == "Nothing planned yet.", f"the empty schedule says {said!r}, not 'Nothing planned yet.'")
t("old_gone", "'Nothing planned.'" not in page, "the old 'Nothing planned.' still stands on the page")
'''
PASSES_BEFORE = GOOD_TESTS.replace('t("old_gone"', 't("page_there", True, "")\nt("old_gone"')
RUBBISH = '''#!/usr/bin/env python3
import sys, pathlib
hq = pathlib.Path(sys.argv[1])
ok = (hq / "DONE{v}").exists()
print(("PASS " if ok else "FAIL ") + "done_file" + ("" if ok else ": no DONE{v} file"))
'''


def say(step, what):
    print(f"{time.strftime('%H:%M:%S')} +{int(time.time() - T0):4d}s  {step}: {what}", flush=True)


def check(n, ok, what):
    RESULTS.setdefault(n, []).append((bool(ok), what))
    say(f"check {n}", ("ok: " if ok else "FAIL: ") + what)
    return bool(ok)


def her(root, env, *argv, timeout=900):
    """One command of hers from a text: (allowed by the policy, exit code, output). A refusal is an answer here, not a stop."""
    cmd = "python3 " + shlex.join([str(root / "HQ" / argv[0]), *argv[1:]])
    v, why = nowroad.policy(root, env, cmd)
    if v != "allow":
        return False, 99, f"the policy refuses it on a text ({v}): {why}"
    if not (root / "HQ" / argv[0]).exists():
        return True, 98, f"{argv[0]} isn't there"
    r = subprocess.run([PY, str(root / "HQ" / argv[0]), *argv[1:]], cwd=str(root / "workspace"), env=nowroad.her_env(env, root), text=True,
                       capture_output=True, timeout=timeout)
    return True, r.returncode, (r.stdout + r.stderr).strip()


def py(root, env, code, *args, check_=True):
    r = subprocess.run([PY, "-c", "import sys, json; sys.path.insert(0, 'routine')\n" + code, *args], cwd=str(root / "HQ"), env=env,
                       text=True, capture_output=True, timeout=900)
    if check_ and r.returncode:
        raise RuntimeError(r.stderr[-600:])
    return r.stdout.strip()


def tests_dir(root, label):
    return root / "workspace" / "HQ" / "qa-tests" / label


def put_tests(root, label, script, sentences):
    d = tests_dir(root, label)
    d.mkdir(parents=True, exist_ok=True)
    (d / "test.py").write_text(script, encoding="utf8")
    names = sorted({t for s in sentences for t in s[1]})
    (d / "tests.json").write_text(json.dumps({"sentences": [{"his": s[0], "tests": s[1]} for s in sentences],
                                              "tests": {n: f"what {n} checks, as he'd see it on the status page" for n in names}},
                                             ensure_ascii=False, indent=1), encoding="utf8")


def sentences_of(words):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z])", words) if x.strip()]


def team_texts(root):
    p = root / "workspace" / "HQ" / "team-line" / "thread.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf8").splitlines() if l.strip()] if p.exists() else []


def write_row(root, env, title, what, empty, new, old, why, words):
    ok, code, out = her(root, env, "routine/jobs.py", "write-row", ROW.format(title=title, what=what, empty=empty, new=new, old=old, why=why), "--bug")
    m = re.search(r"\b([FH]\d+) is on the planning", out)
    if not m:
        raise RuntimeError(f"write-row: {out[-500:]}")
    label = m.group(1)
    add = f'His words: "{words}" My own additions: none. Sources: HQ/team-line/thread.jsonl (his text of {time.strftime("%-d %B %Y")}).'
    ok, code, out = her(root, env, "routine/review.py", "add", label, add)
    if code:
        raise RuntimeError(f"review.py add: {out[-500:]}")
    return label


def item_rounds(root, env, label):
    """The item's own review, review.py now, up to its three rounds, answering each flag the plain way (as nowroad does)."""
    st = {}
    for n in range(1, 4):
        ok, code, out = her(root, env, "routine/review.py", "now", label)
        st = nowroad.review_state(root, env, label)
        say(f"item review {n}", f"{st.get('state')}: " + ("; ".join(st.get("findings") or []))[:300])
        if st.get("state") != "flagged" or n == 3:
            return st, n
        ans = ("For each point, how the team settles it: " + " ".join(f"({i + 1}) {nowroad._noq(f)}: the team decides it the plain way "
               "while building and writes what it chose in the row's result." for i, f in enumerate(st["findings"][:3])))
        her(root, env, "routine/review.py", "add", label, ans[:3800])
    return st, 3


def stand_in_17(root):
    p = root / "bin" / "seventeen"
    p.write_text("#!/bin/bash\necho 'the 17 happy flows (stand-in: they run for real on their own, routine/happy.py run)'\n"
                 "printf '\\n== Result\\n17 of 17 passed\\n'\n")
    p.chmod(0o755)
    return str(p)


def build_change(root, env, on=True):
    page = root / "HQ" / "status" / "index.html"
    t = page.read_text(encoding="utf8")
    a, b = ("'Nothing planned.'", "'Nothing planned yet.'") if on else ("'Nothing planned yet.'", "'Nothing planned.'")
    page.write_text(t.replace(a, b, 1), encoding="utf8")
    chainrun._git(root / "HQ", "commit", "-q", "-am", "the team's build (the qaroad driver's stand-in)" if on else "the build taken back",
                  env={**env, "HQ_PRIVACY_PASSED": "1"})


def done_by_hand(root, env, job):
    """jobs.py done N --said "his words", by hand on the copy: before real QA his words closed a build without its green record."""
    r = subprocess.run([PY, "routine/jobs.py", "done", str(job), "--said", WORDS_A], cwd=str(root / "HQ"), env=env, text=True,
                       capture_output=True, timeout=600)
    return r.returncode, (r.stdout + r.stderr).strip()


def proof(root, env, job, runner):
    r = subprocess.run([PY, "routine/proof.py", "run", str(job)], cwd=str(root / "HQ"), env={**env, "HQ_PROOF_RUNNER": runner},
                       text=True, capture_output=True, timeout=1800)
    rec = json.loads(py(root, env, "import proof\nprint(json.dumps(proof.load(int(sys.argv[1])) or {}))", str(job)))
    return r.returncode, (r.stdout + r.stderr).strip(), rec


def run(root: Path, workspace: str, with_her: bool) -> int:
    say("0 copy", f"a copy of {workspace} in {root}")
    env = nowroad.copy(root, workspace)
    nowroad.his_text(root, WORDS_B + " " + NOW_B)
    nowroad.his_text(root, WORDS_A + " " + NOW)
    has_qa = (root / "HQ" / "routine" / "qatests.py").exists()
    say("0 copy", f"routine/qatests.py in this HQ: {has_qa}")

    A = write_row(root, env, "The empty schedule says Nothing planned yet", "the coming card with nothing on the schedule says Nothing planned yet.",
                  "an empty schedule", "Nothing planned yet.", "Nothing planned.", "so it doesn't feel so final", WORDS_A)
    B = write_row(root, env, "The other empty cards say Nothing here yet", "every other card that's empty says Nothing here yet.",
                  "empty cards", "Nothing here yet.", "Nothing yet.", "it reads friendlier", WORDS_B)
    say("0 rows", f"{A} (the empty schedule) and {B} (the other empty cards) on the copy's planning, his words in both")
    sa, sb = sentences_of(WORDS_A), sentences_of(WORDS_B)

    # ---- 1: no tests, no mark, no team ----
    ok, code, out = her(root, env, "routine/sprint.py", "ready", A)
    check(1, code != 0 and re.search(r"QA test", out), f"Ready mark without her tests: exit {code}: {out[-220:]!r}")
    ok, code, out = her(root, env, "routine/jobs.py", "send-row", A, "--not-ready", "--now", "--said", NOW)
    check(1, code != 0 and re.search(r"QA test", out), f"send-row --not-ready --now without her tests: exit {code}: {out[-220:]!r}")
    jobs_for = lambda lab: json.loads(py(root, env, "import jobs\nprint(json.dumps([j['n'] for j in jobs.read()[1] if j.get('item') and "  # noqa: E731
                                                    "(j['item'].get('label') == sys.argv[1]) or sys.argv[1] + ' on the HQ roadmap' in j['text']]))", lab))
    check(1, not jobs_for(A), f"no job for {A} on the queue: {jobs_for(A)}")
    if jobs_for(A):
        py(root, env, "import jobs, time\nwith jobs.locked():\n t, js, on = jobs.read()\n for j in js:\n  if sys.argv[1] + ' on the HQ roadmap' in j['text']:\n"
                      "   j['state'] = 'cancelled ' + time.strftime('%Y-%m-%d %H:%M')\n jobs.write(t, js, on)", A)

    # ---- 4: every sentence of his words has a test ----
    put_tests(root, A, GOOD_TESTS, [(sa[-1], ["says_yet"])])
    ok, code, out = her(root, env, "routine/qatests.py", "check", A)
    check(4, code != 0 and sa[0][:30].lower() in out.lower(), f"tests for one of his {len(sa)} sentences: exit {code}: {out[-260:]!r}")
    put_tests(root, A, GOOD_TESTS, [(sa[0], ["old_gone"]), (sa[-1], ["says_yet", "not_written"])])
    ok, code, out = her(root, env, "routine/qatests.py", "check", A)
    check(4, code != 0 and "not_written" in out, f"a test named for a sentence that the script never runs: exit {code}: {out[-200:]!r}")

    # ---- 5: they fail on the code as it is ----
    put_tests(root, A, PASSES_BEFORE, [(sa[0], ["old_gone", "page_there"]), (sa[-1], ["says_yet"])])
    ok, code, out = her(root, env, "routine/qatests.py", "check", A)
    check(5, code != 0 and "page_there" in out, f"a test that passes before the build: exit {code}: {out[-220:]!r}")
    put_tests(root, A, GOOD_TESTS, [(sa[0], ["old_gone"]), (sa[-1], ["says_yet"])])
    ok, code, out = her(root, env, "routine/qatests.py", "check", A)
    check(5, code == 0, f"good tests, all failing on today's code, are sealed: exit {code}: {out[-220:]!r}")
    st = json.loads(py(root, env, "import qatests\nprint(json.dumps(qatests.state(sys.argv[1])))", A, check_=False) or "{}")
    before = (st.get("sealed") or {}).get("before") or {}
    check(5, before.get("results") and all(not v for v in before["results"].values()) and before.get("head"),
          f"the seal keeps the run before the build: {json.dumps(before)[:200]}")

    # ---- 2: a second review of her tests, apart from the item's ----
    item_before = nowroad.review_state(root, env, A)
    ok, code, out = her(root, env, "routine/qatests.py", "review", A, timeout=600)
    say("tests review A 1", out[-300:])
    st = json.loads(py(root, env, "import qatests\nprint(json.dumps(qatests.state(sys.argv[1])))", A, check_=False) or "{}")
    rv = st.get("reviews") or []
    check(2, code in (0, 1) and rv and rv[-1].get("verdict") in ("pass", "flag"), f"her tests' review ran and kept its verdict: {json.dumps(rv[-1:])[:260]}")
    check(2, nowroad.review_state(root, env, A).get("state") == item_before.get("state"), "the item's own review state is untouched by it")
    sysprompts = py(root, env, "import qatests, review\nprint(json.dumps([qatests.SYSTEM != review.SYSTEM and qatests.SYSTEM != review.RESYSTEM, "
                               "'test' in qatests.SYSTEM.lower()]))", check_=False)
    check(2, sysprompts == "[true, true]", f"its own prompt, about tests, not the item's: {sysprompts!r}")
    for k in range(2, 4):  # up to three rounds for A's tests, answering in the tests themselves
        if (rv[-1:] or [{}])[0].get("verdict") != "flag":
            break
        (tests_dir(root, A) / "test.py").write_text(GOOD_TESTS + f"# round {k}: the reviewer's points, answered in the tests\n", encoding="utf8")
        her(root, env, "routine/qatests.py", "check", A)
        ok, code, out = her(root, env, "routine/qatests.py", "review", A, timeout=600)
        say(f"tests review A {k}", out[-300:])
        rv = (json.loads(py(root, env, "import qatests\nprint(json.dumps(qatests.state(sys.argv[1])))", A, check_=False) or "{}").get("reviews") or [])

    # ---- 3: at most three rounds, then one message to him with the open points ----
    put_tests(root, B, RUBBISH.format(v=""), [(s, ["done_file"]) for s in sb])
    ok, code, out = her(root, env, "routine/qatests.py", "check", B)
    check(3, code == 0, f"rubbish tests that still pass the hard checks are sealed (the review is what catches them): exit {code}: {out[-160:]!r}")
    told0 = len(team_texts(root))
    verdicts = []
    for k in range(1, 4):
        if k > 1:
            put_tests(root, B, RUBBISH.format(v=str(k)), [(s, ["done_file"]) for s in sb])
            her(root, env, "routine/qatests.py", "check", B)
        ok, code, out = her(root, env, "routine/qatests.py", "review", B, timeout=600)
        st = json.loads(py(root, env, "import qatests\nprint(json.dumps(qatests.state(sys.argv[1])))", B, check_=False) or "{}")
        verdicts.append(((st.get("reviews") or [{}])[-1]).get("verdict"))
        say(f"tests review B {k}", f"{verdicts[-1]}: {out[-200:]}")
    check(3, verdicts == ["flag"] * 3, f"three rounds on tests that check a DONE file: {verdicts}")
    put_tests(root, B, RUBBISH.format(v="4"), [(s, ["done_file"]) for s in sb])
    her(root, env, "routine/qatests.py", "check", B)
    ok, code, out = her(root, env, "routine/qatests.py", "review", B)
    check(3, code != 0 and re.search(r"3 rounds|three rounds", out), f"a fourth round is refused: exit {code}: {out[-200:]!r}")
    new = [m for m in team_texts(root)[told0:] if m.get("from") == "agent" and B in (m.get("text", "") + m.get("item", "") + m.get("why", ""))]
    pts = (st.get("reviews") or [{}])[-1].get("findings") or []
    check(3, len(new) == 1, f"one message to him about {B}'s tests after the third round: {len(new)} ({[m.get('text', '')[:120] for m in new]})")
    check(3, new and pts and all(nowroad._noq(p)[:40].lower() in nowroad._noq(new[0]["text"]).lower() for p in pts),
          f"it holds every open point ({len(pts)})")

    # ---- 4, 5 and his now: never past the hard checks ----
    put_tests(root, B, RUBBISH.format(v="4"), [(sb[0], ["done_file"])])  # a sentence of his loses its test after the rounds
    ok, code, out = her(root, env, "routine/jobs.py", "send-row", B, "--not-ready", "--now", "--said", NOW_B)
    check(4, code != 0 and re.search(r"QA test", out), f"his now with a sentence of his left without a test: exit {code}: {out[-220:]!r}")

    # ---- A to the team: the item's rounds, his now ----
    ist, n = item_rounds(root, env, A)
    trv = (rv[-1:] or [{}])[0].get("verdict")
    if ist.get("state") == "passed" and trv == "pass":
        ok, code, out = her(root, env, "routine/sprint.py", "ready", A)
        check(1, code == 0, f"with sealed, reviewed tests and a passed item review the Ready mark lands: exit {code}: {out[-200:]!r}")
        send = ["routine/jobs.py", "send-row", A, "--now", "--said", NOW]
    else:
        send = ["routine/jobs.py", "send-row", A, "--not-ready", "--now", "--said", NOW]
    if ist.get("state") == "flagged" and n == 3:
        about = [m for m in team_texts(root) if m.get("from") == "agent" and A in (m.get("text", "") + m.get("item", "")) and "review" in m.get("text", "").lower()]
        check(3, len(about) >= 1, f"the item review's third flag sent him its open points too: {len(about)}")
    ok, code, out = her(root, env, *send)
    job = re.search(r"Job (\d+) is ready", out)
    check(1, job, f"with her sealed tests his now sends {A}: exit {code}: {out[-260:]!r}")
    if not job:
        return finish()
    job = int(job.group(1))
    jt = json.loads(py(root, env, "import jobs\nprint(json.dumps(next(j for j in jobs.read()[1] if j['n'] == int(sys.argv[1]))['text']))", str(job)))
    check(6, "qa-tests" in jt and "don't change" in jt.lower(), f"the job names her tests as its target, not its to change: {jt[-260:]!r}")
    py(root, env, "import jobs, time\nwith jobs.locked():\n t, js, on = jobs.read()\n j = next(x for x in js if x['n'] == int(sys.argv[1]))\n"
                  " j['state'] = 'running since ' + time.strftime('%H:%M')\n jobs.write(t, js, on)", str(job))
    runner = stand_in_17(root)

    # ---- 7: the end, for real: not built is red, and his words on done don't skip it ----
    code, out, rec = proof(root, env, job, runner)
    q = rec.get("qa_tests") or {}
    check(7, not rec.get("green") and q and not q.get("green"), f"not built yet: her tests fail, the record is red: {out[-220:]!r}")
    code, out = done_by_hand(root, env, job)
    check(7, code != 0 and re.search(r"QA test", out), f"done by hand with his words on a red record of her tests: exit {code}: {out[-220:]!r}")

    # ---- 6: the team changes her tests ----
    build_change(root, env)
    (tests_dir(root, A) / "test.py").write_text(GOOD_TESTS.replace('said == "Nothing planned yet."', "True"), encoding="utf8")
    code, out, rec = proof(root, env, job, runner)
    q = rec.get("qa_tests") or {}
    check(6, not rec.get("green") and re.search(r"changed", json.dumps(q)), f"built, but her tests changed in the workspace: red: {json.dumps(q)[:260]}")
    code, out = done_by_hand(root, env, job)
    check(6, code != 0 and re.search(r"QA test", out), f"done by hand with his words refused on changed tests: exit {code}: {out[-200:]!r}")
    put_tests(root, A, GOOD_TESTS, [(sa[0], ["old_gone"]), (sa[-1], ["says_yet"])])  # her tests back
    sealed = json.loads(py(root, env, "import qatests\nprint(json.dumps(qatests.state(sys.argv[1])))", A, check_=False) or "{}").get("sealed") or {}
    cur = py(root, env, "import qatests\nprint(qatests.fingerprint(sys.argv[1]))", A, check_=False)
    if sealed.get("fp") != cur:  # the tests as sealed (a round may have added a line)
        src = Path(sealed["copy"]) if sealed.get("copy") else None
        if src and src.is_dir():
            for f in ("test.py", "tests.json"):
                (tests_dir(root, A) / f).write_text((src / f).read_text(encoding="utf8"), encoding="utf8")

    # ---- 7: built, her tests as sealed: green, and only then done ----
    code, out, rec = proof(root, env, job, runner)
    q = rec.get("qa_tests") or {}
    check(7, rec.get("green") and q.get("green") and q.get("passed") == q.get("ran") == 2, f"built and her tests as sealed: green: {out[-220:]!r}")
    pref = py(root, env, "import qa\nprint(qa.proof_refuses(sys.argv[1], 'her tests on the built copy, 2 of 2') or '')", A, check_=False)
    say("qa pass", f"QA's own gate on the record: {pref[:200] or 'passes'}")
    r = chainrun._run(env, root, "routine/jobs.py", "done", str(job))
    check(7, r.returncode == 0, f"done on the green record, without any say-so: exit {r.returncode}: {(r.stdout + r.stderr).strip()[-200:]!r}")

    if with_her:
        her_turn(root, env)
    return finish()


def her_turn(root, env):
    """H: her own model on his real text with his now, as in production; the job, if any, must carry her sealed tests."""
    th = root / "workspace" / "HQ" / "team-line" / "thread.jsonl"
    before_jobs = set(json.loads(py(root, env, "import jobs\nprint(json.dumps([j['n'] for j in jobs.read()[1]]))")))
    words = ("On the status page, the done card says Nothing yet. when nothing's done today. I'd like it to say Nothing done yet today. "
             "Please give it to the team and let's run it immediately once it's ready.")
    nowroad.his_text(root, words)
    at = json.loads(th.read_text(encoding="utf8").splitlines()[-1])["at"]
    real = env["NOWROAD_REAL_CLAUDE"]
    t1 = time.time()
    vpy = next((str(p) for p in (root / "HQ" / ".venv/bin/python", HERE.parent / ".venv/bin/python", Path.home() / "HQ" / ".venv/bin/python")
                if p.exists()), PY)  # the call line's Python (the Agent SDK), as the text server runs it
    r = subprocess.run([vpy, "app/direct_line.py", "--team", "reply"], cwd=str(root / "HQ"),
                       env={**env, "HQ_CLAUDE": real}, text=True, capture_output=True, timeout=2400)
    (root / "her-reply.out").write_text(r.stdout + "\n----\n" + r.stderr)
    back = [m["text"] for m in (json.loads(l) for l in th.read_text(encoding="utf8").splitlines() if l.strip()) if m.get("from") == "agent" and m.get("at", 0) > at]
    say("H her reply", f"{int(time.time() - t1)} s, exit {r.returncode}: " + " / ".join(back)[:600])
    new = [j for j in json.loads(py(root, env, "import jobs\nprint(json.dumps(jobs.read()[1]))")) if j["n"] not in before_jobs and not j["state"].startswith("cancelled")]
    for j in new:
        lab = (j.get("item") or {}).get("label") or (re.search(r"\b([FH]\d+) on the HQ roadmap", j["text"]) or [None, None])[1]
        st = json.loads(py(root, env, "import qatests\nprint(json.dumps(qatests.state(sys.argv[1])))", lab or "", check_=False) or "{}")
        check("H", (st.get("sealed") or {}).get("fp") and "qa-tests" in j["text"], f"job {j['n']} for {lab} left with her sealed tests: {bool((st.get('sealed') or {}).get('fp'))}")
    if not new:
        check("H", any(re.search(r"\btests?\b|QA", t) for t in back), "no job left; her reply says it's her tests that hold it")


def finish():
    print("\n== qaroad")
    bad = 0
    for n in sorted(RESULTS, key=str):
        ok = all(o for o, _ in RESULTS[n])
        bad += not ok
        print(f"  check {n}: {'PASS' if ok else 'FAIL'} ({sum(o for o, _ in RESULTS[n])} of {len(RESULTS[n])})")
    for n in ("1", "2", "3", "4", "5", "6", "7") + (("H",) if WITH_HER else ()):
        if n not in {str(k) for k in RESULTS}:
            bad += 1
            print(f"  check {n}: FAIL (never reached)")
    print("RESULT: " + ("PASS" if not bad else f"FAIL ({bad} checks)"))
    return 0 if not bad else 1


def main(argv):
    if len(argv) >= 2 and argv[0] == "clean":
        chainrun.clean(Path(argv[1]), nowroad.PORTS)
        return 0
    if len(argv) < 2 or argv[0] != "run":
        print(__doc__)
        return 2
    root = Path(argv[1]).resolve()
    if root.exists():
        sys.exit(f"{root} is there already: give a new folder")
    ws = argv[argv.index("--workspace") + 1] if "--workspace" in argv else str(Path.home() / "HQ" / "workspace")
    global WITH_HER
    WITH_HER = "--her" in argv
    try:
        return run(root, os.path.realpath(ws), WITH_HER)
    except Exception as e:
        import traceback
        traceback.print_exc()
        say("stopped", repr(e)[:400])
        return finish() or 1
    finally:
        if "--keep" not in argv:
            chainrun.clean(root, nowroad.PORTS)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
