#!/usr/bin/env python3
"""QA as a real step, and what the release takes (F56, piece 1, 26 October 2026).

The user on the call of 26 October 2026 at 13:32 (Moneypenny), typed, after 0.4.14 shipped a third of a feature:
"you keep telling me that everything is great and you just push and release. This is not acceptable." The F56 row:
"QA as a real step: after the team builds a piece, a QA job (its own kind, qa, run as Moneypenny with her craft)
checks it against its row: every "done means" example tried for real, end to end, the new flows run, and the result
written in the row's result as "QA passed" or "QA failed: what's off"; a failed QA goes back to the team as a fix job.
The release only takes work whose row says QA passed". His own test at the sprint stays, but isn't a gate for the
daily release (his yes on that call).

How it goes:
- A build job (small or big) for a row in the planning's Bugs or Features (Phase F or H) that's marked done queues a
  QA job for that row by itself (jobs.py done calls on_done). The QA job starts with "QA of LABEL" and runs as
  Moneypenny: the routine puts her character and craft in its first prompt (prompt_extra).
- The QA job ends with qa.py pass LABEL "WHAT WAS TRIED" or qa.py fail LABEL "WHAT'S OFF". Each writes a mark in the
  row: "QA passed (job N, 26 October 2026 17:40): ..." or "QA failed (job N, ...): ...". The newest mark counts.
- F151 (5 November 2026): a fail queues nothing. The finding goes back into the row as an open point, and the fix goes the road of a
  new item (qatests.py): a new test of hers for it that fails on the build, sealed, its own review, the item reviewed again against
  his words and the whole picture, each 20 rounds at most and fresh per QA failure; only then send-row. A pass on that road needs her
  tests, new and earlier, and the 17 happy flows; it closes the rows that say they're replaced by this one.
- The release (release.py) walks dev's commits since main, oldest first; each names its rows at the start of its
  subject ("H283: ..."). A commit for a row in Phase F or H without "QA passed" stops the walk: main gets the work
  before it, the rest stays on dev and nightly, and the morning text names what was held and why (hold()). F112: a merge
  commit is what it brings, and BEFORE_GATE is the one list of rows from before the gate, each said or named held.
  F120: COMMITS_FOR names, by hand, a commit whose subject names no row but that belongs to one (by its full id), with
  exactly what it changes; it then counts for that row and waits for that row's QA like any commit naming it.
  A commit without a row (a version, a nightly test fix, a merge) or for a row elsewhere (maintenance) goes along.

F71 (28 October 2026): QA jobs since 27 October mostly took one or two minutes, and their write-ups said what was
tried as a whole, not each done example with what was run and what came out; one passed on its flows alone. A pass
now names every done example of the row with its evidence, three flags each, in order: --example (the row's own
example), --ran (the command, page or step really run for it) and --got (what came out). A pass without them, or
with an example missing its ran or got, is refused and nothing is written. The mark keeps them: "Tried: (1) ...".

usage:
  python3 routine/qa.py pass LABEL "SUMMARY" --example E --ran R --got G [--example ... ] [--job N]
                                                                QA passed, in the row, each example with its evidence
  python3 routine/qa.py fail LABEL "WHAT'S OFF" [--job N]       QA failed, in the row; the finding an open point, the fix on its road
                                         F216: when the only open part is a Mac example (said in its words, or --mac-only [--flow N]),
                                         on a server paired with the laptop, it goes to the laptop instead (routine/machalf.py)
  python3 routine/qa.py state LABEL                             passed, failed or none, with the newest mark
  python3 routine/qa.py queue LABEL                             a QA job for the row now (a call, or by hand)
  python3 routine/qa.py hold                                    what the release would take and what it would hold
  python3 routine/qa.py first-time [--weeks N] [--json]        H342: each week, how many items passed her check the first time
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402
import jobs as q  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, ".."))
GATED = ("F", "H")  # the planning's phases whose work goes through QA: Bugs and Features
MAX_FAILS = 3       # failed QAs in a row before it waits for a call instead of a fix job [Claude's choice]
# The mark, distinct from a row that only talks about QA (the F56 row itself says "QA passed").
MARK = re.compile(r"QA (passed|failed) \((?:job \d+|by hand), (\d{1,2} \w+ 20\d\d \d\d:\d\d)\):? ?([^|]*?)(?= QA (?:passed|failed) \(|\s*\||\s*$)")
LABEL = re.compile(r"[A-Z]\d+(?:\.\d+)*")
QA_START = "QA of "


def rows(text: str) -> dict:
    """{label: (line, phase letter)} for every row in a roadmap phase."""
    out, phase = {}, ""
    for line in text.split("\n"):
        if line.startswith("## "):
            m = re.match(r"## Phase (\w+)", line)
            phase = m.group(1) if m else ""
            continue
        m = re.match(r"^\| [^|]* \| ([A-Z]\d+(?:\.\d+)*)\b", line)
        if m and phase and m.group(1) not in out:
            out[m.group(1)] = (line, phase)
    return out


def gated(label: str, text: str) -> bool:
    """Work for this row goes through QA: it's in the planning's Bugs or Features."""
    r = rows(text).get(label)
    return bool(r) and r[1] in GATED


def marks(line: str) -> list[tuple[str, str, str]]:
    """The QA marks in a row, oldest first: (passed|failed, when, what). F86: only at a mark's place, the row's result cells or the team's notes
    at the end of its description: with the ask going on after it, it's words in the ask, whatever they look like."""
    import sprint
    cs = hqpaths.cells(line or "")
    if len(cs) < 3:
        return []
    at = sprint.team_note_at(cs[2])
    place = " | ".join(([] if at is None else [cs[2][at:]]) + cs[3:])
    return [(m.group(1), m.group(2), m.group(3).strip()) for m in MARK.finditer(place)]


def state(label: str, text: str | None = None) -> str | None:
    """passed, failed, or None when the row has no QA mark yet."""
    text = q.read()[0] if text is None else text
    r = rows(text).get(label)
    ms = marks(r[0]) if r else []
    return ms[-1][0] if ms else None


def fails_in_a_row(line: str) -> int:
    n = 0
    for s, _, _ in reversed(marks(line)):
        if s != "failed":
            break
        n += 1
    return n


def _when(now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now()
    return f"{now.day} {now:%B %Y %H:%M}"


def mark(label: str, passed: bool, what: str, job: int | None = None, now: dt.datetime | None = None) -> str:
    """Writes the mark at the end of the row's result cell; returns the row as it is now. Exits when there's no row."""
    what = " ".join((what or "").split()).replace("|", "/").rstrip(".")
    if not what:
        sys.exit("Say in a line what QA tried, or what's off.")
    with q.locked():
        text, jobs, on = q.read()
        r = rows(text).get(label)
        if not r:
            sys.exit(f"No {label} row on the roadmap.")
        line = r[0]
        cells = hqpaths.cells(line)  # F101: an escaped pipe in a row is not a cell
        at = len(cells) - 2 if len(cells) >= 6 else len(cells) - 1
        word = "passed" if passed else "failed"
        new = f"QA {word} ({f'job {job}' if job else 'by hand'}, {_when(now)}): {what}."
        cells[at] = (cells[at].strip() + " " + new).strip()
        row2 = hqpaths.join_cells(cells)
        if len(hqpaths.cells(row2)) != len(hqpaths.cells(line)):
            sys.exit(f"Nothing written: the mark would change the cells of the {label} row.")
        text = text.replace(line, row2, 1)
        q.write(text, jobs, on)
        return row2


EVIDENCE = ("--example", "--ran", "--got")


def evidence(args: list[str]) -> tuple[list[str], list[tuple[str, str, str]], str | None]:
    """F71: takes the --example, --ran and --got flags out of args. Returns (the rest, [(example, ran, got)], what's
    wrong or None). Each example needs its ran and its got, in that order, none empty."""
    rest, got, cur, err = [], [], None, None
    i = 0
    while i < len(args):
        a = args[i]
        if a in EVIDENCE:
            v = " ".join((args[i + 1] if i + 1 < len(args) else "").split()).replace("|", "/")
            i += 2
            if not v:
                err = err or f"{a} needs a text after it."
                continue
            if a == "--example":
                if cur is not None:
                    err = err or f"The example \"{cur[0]}\" has no --ran and --got."
                cur = [v]
            elif cur is None or len(cur) != EVIDENCE.index(a):
                err = err or f"{a} \"{v}\" comes without its --example first (each example: --example, --ran, --got)."
            else:
                cur.append(v)
                if len(cur) == 3:
                    got.append(tuple(cur))
                    cur = None
            continue
        rest.append(a)
        i += 1
    if cur is not None:
        err = err or f"The example \"{cur[0]}\" has no " + (" and ".join(EVIDENCE[len(cur):])) + "."
    return rest, got, err


def tried_words(ev: list[tuple[str, str, str]]) -> str:
    return "Tried: " + "; ".join(f"({i}) {e.rstrip('.;')}: ran {r.rstrip('.;')}, got {g.rstrip('.;')}"
                                 for i, (e, r, g) in enumerate(ev, 1))


NOT_TRIED = re.compile(r"\bnot (?:yet )?(?:tried|covered)\b", re.I)  # H313: what holds QA and the release
PASS_REFUSED = ("Refused: a pass names every done example of the row with its evidence (F71). For each one: "
                "--example \"the row's example\" --ran \"what was really run for it\" --got \"what came out\". "
                "An example that couldn't be tried is a fail, with why: a pass that says not tried holds (H313). Nothing written.")


def job_label(text: str) -> str | None:
    """The row a job is for: its QA or fix wording, "LABEL on the roadmap", "read the LABEL row", or a label first."""
    import estimate as est_
    t = " ".join((text or "").split())
    m = re.match(rf"^(?:{QA_START}|Fix for )({LABEL.pattern})\b", t)
    if m:
        return m.group(1)
    tl = re.sub(r"^.*?the job, as agreed on the call: ", "", t.lower())
    tl = re.sub(r"^scheduled item \d+, planned for [^:]*?(?:\d{1,2}:\d\d)?: ", "", tl)
    got = est_._first_row(tl)
    if not got:
        m = re.match(r"^([hf]\d+(?:\.\d+)*)\b", tl)
        got = m.group(1) if m else None
    return got.upper() if got else None


def is_qa(text: str) -> bool:
    return " ".join((text or "").split()).startswith(QA_START)


PREP_START = "Prep of "  # the line's prep job (routine/line.py PREP), and one she queues the same way (H342: a rewrite of her tests)


def is_prep(text: str) -> bool:
    """H342 (8 November 2026): a prep job gets an item ready (her tests written, checked, sealed, reviewed); it builds nothing, so it is
    never judged by a build's record or her tests on "the built code", and its done queues no QA."""
    return " ".join((text or "").split()).startswith(PREP_START)


# F57: the end of every job's text; the done mark is the one thing that is always the very last step.
DONE_LAST = ("Then the status block, then python3 routine/jobs.py done N as the very last step, nothing after it, "
             "within a minute of the result.")


def qa_text(label: str, after: str) -> str:
    return (f"{QA_START}{label} (F56): {after} Read the {label} row whole and check the work against it as Moneypenny, "
            "with her craft (her character and definition of done are in this prompt). Pull dev first. Try every "
            "\"done means\" example of the row for real, end to end, the way someone using HQ would (a second HQ, a "
            "phone-sized page, a real command), and run the new flows it names and the old ones around it. Build "
            "nothing, except a one-line fix in a test when the test itself is wrong (then say so). Then write the "
            f"result: python3 routine/qa.py pass {label} \"a line on the whole\" --job N, followed by every done example "
            "of the row with its evidence, three flags each: --example \"the row's example\" --ran \"the command, "
            "page or step you really ran for it\" --got \"what came out\" (F71: a pass without them is refused; "
            "reading the team's notes or the code is not running it, and the flows alone don't stand in for the "
            "examples), plus --compared \"what you compared on real data, how many of how many\" (F101: a pass also needs "
            f"the green run routine/proof.py keeps for this row), or python3 routine/qa.py fail {label} "
            "\"what's off, plainly\" --job N (a fail queues no fix: the finding goes back into the row, and the fix goes the road of a new item, F151). No helpers fanned out (F55). Nothing to push "
            "unless a test was fixed; the call line isn't restarted. " + DONE_LAST)


def fix_text(label: str, what: str, qa_job: int | None) -> str:
    return (f"Fix for {label} (F56): QA failed{f' in job {qa_job}' if qa_job else ''}: {what}. Read the {label} row whole and "
            "its newest QA failed line, fix what's off so every done example holds, run its flows and the ones around it, "
            f"privacy check, tutorial and changelog where they change, push to dev with push.py, write under the {label} row "
            "what was fixed. A QA job follows by itself when this one is done. " + DONE_LAST)


def _waiting_for(jobs: list, label: str, qa: bool) -> dict | None:
    for j in jobs:
        if j["state"].startswith(q.FINISHED):
            continue
        if is_qa(j["text"]) == qa and ((j.get("item") or {}).get("label") or job_label(j["text"])) == label:  # F103
            return j
    return None


def _append(jobs: list, text: str, label: str | None = None) -> dict:
    n = max([j["n"] for j in jobs] + [0]) + 1
    j = {"n": n, "state": "ready", "past": False, "agreed": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
         "text": q.one_line(text).replace("·", "-")}
    q.carry(j, label)  # F103: the same id through the QA and the fix
    jobs.insert(_place(jobs, label), j)
    return j


def _place(jobs: list, label: str | None) -> int:
    """F212: where a new QA job goes in the list: by its item's rank on the planning, the order the line picks by (F176,
    tick.by_rank), so the place the status page numbers is the place it runs. Before the first waiting job whose item ranks
    lower; equals and higher-ranked work stay ahead of it. An unranked item, or no planning: at the end, as before."""
    try:
        import sprint as sp_
        place = {l: i for i, l in enumerate(sp_.order())}
    except Exception:
        return len(jobs)
    if label not in place:
        return len(jobs)

    def rank(w):
        return place.get((w.get("item") or {}).get("label") or job_label(w.get("text") or ""), len(place))
    return next((i for i, w in enumerate(jobs) if q.waiting(w) and rank(w) > place[label]), len(jobs))


def _estimate(j: dict, kind: str) -> None:
    try:
        q.estimate("on_add", j["n"], j["text"], kind)
    except Exception:
        pass


def on_done(jobs: list, j: dict, text: str, kind: str | None) -> dict | None:
    """Inside jobs.py done (its lock held): a finished build for a row in Bugs or Features gets a QA job, at the end
    of the line. Returns the new job (not written yet), or None."""
    if kind not in ("build", "bigbuild") or is_qa(j["text"]) or is_prep(j["text"]):  # H342: a prep builds nothing
        return None
    label = (j.get("item") or {}).get("label") or job_label(j["text"])  # F103: the carried id's row, never a sentence again
    if not label or not gated(label, text):
        return None
    import wholebuild  # 11 November 2026: with whole_build_review on, no QA job per item: one review over the whole build
    if wholebuild.on():
        print(wholebuild.on_built(j, label))
        return None
    if _waiting_for(jobs, label, qa=True):
        return None
    return _append(jobs, qa_text(label, f"the team finished job {j['n']} for it."), label)


def queue(label: str, after: str = "") -> str:
    with q.locked():
        text, jobs, on = q.read()
        if label not in rows(text):
            sys.exit(f"No {label} row on the roadmap.")
        w = _waiting_for(jobs, label, qa=True)
        if w:
            return f"{label} already has a QA job: job {w['n']} ({w['state']})."
        j = _append(jobs, qa_text(label, after or "asked for on a call."), label)
        q.write(text, jobs, on)
    _estimate(j, "qa")
    return f"Job {j['n']} is ready: QA of {label}."


def title_of(label: str, text: str | None = None) -> str:
    """The row's name without its label, for a text in everyday words."""
    try:
        line = rows(q.read()[0] if text is None else text).get(label, ("",))[0]
    except Exception:
        return ""
    cells = hqpaths.cells(line) if line else []
    name = cells[1] if len(cells) > 1 else ""
    return re.sub(rf"^{re.escape(label)}\s*", "", name)[:160]


def tell(why: str, facts: str, item: str | None = None) -> list[str] | None:
    """H266: Moneypenny texts him on her own line (direct_line.py text WHY, detached; the team's kinds go to her).
    Never from a test on the real line: only when the test gave its own (HQ_DIRECT_DIR)."""
    if hqpaths.under_test() and not os.environ.get("HQ_DIRECT_DIR"):
        return None
    py = os.path.join(ROOT, ".venv", "bin", "python")
    cmd = [py if os.path.exists(py) else sys.executable, os.path.join(ROOT, "app", "direct_line.py"), "text", why, facts] + (["--item", item] if item else [])
    try:
        os.makedirs(os.path.join(ROOT, "scratch"), exist_ok=True)
        log = open(os.path.join(ROOT, "scratch", "direct-line.log"), "a")
        subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError as e:
        print(f"the text about it: {e!r}", file=sys.stderr)
        return None
    return cmd


def item_id(label: str) -> str | None:
    """F103: the id of a row."""
    import trail
    return trail.resolve(label)


def last_pass(label: str, text: str | None = None) -> tuple[str | None, str]:
    """F103: (the job of the row's newest mark, when, if that mark is a pass), else (None, ""). By hand it has no job: "by hand"."""
    r = rows(q.read()[0] if text is None else text).get(label)
    ms = list(MARK.finditer(r[0])) if r else []
    if not ms or ms[-1].group(1) != "passed":
        return None, ""
    m = re.search(r"\(job (\d+),", ms[-1].group(0))
    return (m.group(1) if m else "by hand"), ms[-1].group(2)


def why_no_bug_after(label: str, text: str | None = None) -> str | None:
    if not last_pass(label, text)[0]:
        return f"{label} has no QA pass to hold this against."
    return None


def bug_after_qa(label: str, what: str, found_in: str = "", text: str | None = None) -> str | None:
    """F103 (C42): a bug found after a QA pass, on the ledger against that QA. What's wrong, or None."""
    job, _when_ = last_pass(label, text)
    if not job:
        return f"{label} has no QA pass to hold this against."
    import mistakes
    mistakes.add("bug-after-qa", "qa", what, where=f"QA job {job}", label=label, item=item_id(label) or "",
                 key=f"bug-after-qa|{label}|{job}|{found_in or ' '.join(what.split())}", by="the program")
    return None


def open_point(label: str, what: str, now: dt.datetime | None = None) -> None:
    """F151: the QA finding back into the row as an open point, at the end of its ask (before the team's notes), so the item review sees it."""
    words = "Open point from QA (" + _when(now) + "): " + re.sub(r"(?<!\\)\|", r"\\|", " ".join(what.split()).rstrip(".")) + "."
    import sprint
    with q.locked():
        text, jobs, on = q.read()
        r = rows(text).get(label)
        if not r:
            return
        cs = hqpaths.cells(r[0])
        if len(cs) < 3:
            return
        at = sprint.team_note_at(cs[2])
        ask, notes = (cs[2], "") if at is None else (cs[2][:at], cs[2][at:])
        cs[2] = (ask.rstrip() + " " + words + (" " + notes if notes else "")).strip()
        new = hqpaths.join_cells(cs)
        if len(hqpaths.cells(new)) != len(hqpaths.cells(r[0])):
            return
        q.write(text.replace(r[0], new, 1), jobs, on)


def fail(label: str, what: str, job: int | None = None) -> str:
    """F151: a failed QA queues no fix by itself. The finding goes back into the row as an open point and opens its fix road (qatests.py):
    her new test for it first, failing on the build and sealed, its own review, the item reviewed again, and only then send-row."""
    what = " ".join((what or "").split())
    item = item_id(label)
    name = title_of(label)
    if not what.strip(" ."):  # no usable finding: held the same way, and his to see
        tell("qa-failed", f"What: {name}\nQA failed it without saying what's off, so there's nothing to fix yet. Nothing went to the team; "
                          "it's an open point for you.", item)
        return (f"Refused: QA failed for {label} without a finding, so there's nothing to fix: held, nothing goes to the team, and it goes to "
                "him as an open point on Moneypenny's line. Say in a line what's off.")
    bug_after_qa(label, what)  # a pass that didn't hold: against that QA; nothing when the row had no pass
    row = mark(label, False, what, job)
    import mistakes, qatests, trail
    mistakes.add("qa-fail", "team", what, where=f"QA job {job}" if job else "QA by hand", label=label, item=item or "")
    trail.step(item, "qa", state="failed", job=job, words=what[:300])
    open_point(label, what)
    import wholebuild  # 11 November 2026: an item in the whole-build road goes back to its builder's chat, then one recheck, then held
    if wholebuild.takes(label):
        return wholebuild.on_fail(label, what, job)
    road = qatests.qa_failed(label, what.rstrip("."), job)
    n = fails_in_a_row(row)
    tell("qa-failed", f"What: {name}\nWhat's off: {what}\nNo fix went to the team by itself: the finding is back in the item as an open "
                      "point, and the fix goes the road of a new item (a new test of hers that fails on the build, its own review, the item "
                      "reviewed again)." + (f" It failed {n} times in a row." if n >= MAX_FAILS else ""), item)
    return (f"QA failed for {label} (road {road['n']}): the finding is back in its row as an open point, and the fix is held, not sent: it "
            f"waits for a new test of hers that fails on the build as it stands (qatests.py check {label}), that test's own review "
            f"(qatests.py review {label}, round 1 of {qatests.ROUNDS}), and the item reviewed again against his words and the whole picture "
            f"(review.py now {label}, round 1 of {qatests.ROUNDS}). Only then does send-row {label} go.")


def replaced_rows(label: str, text: str) -> list[str]:
    """F151: the rows that say they're replaced by this one ("Replaced by F151", at the start of a cell or a sentence), not closed yet."""
    out = []
    for lab, (line, _) in rows(text).items():
        cs = hqpaths.cells(line)
        if lab != label and cs and cs[0] not in ("✅",) and re.search(rf"(?:\|\s*|\.\s+)Replaced by {re.escape(label)}\b", line):
            out.append(lab)
    return out


def close_replaced(label: str, now: dt.datetime | None = None) -> list[str]:
    """F151, his words: "nope make a new item, and throw away the old one once this one passes": once this row's QA passed, each row it
    replaces is closed, with a note that says so."""
    done = []
    with q.locked():
        text, jobs, on = q.read()
        for lab in replaced_rows(label, text):
            line = rows(text)[lab][0]
            cs = hqpaths.cells(line)
            cs[0] = "✅"
            at = len(cs) - 2 if len(cs) >= 6 else len(cs) - 1
            cs[at] = (cs[at].strip() + f" Closed as replaced by {label} ({_when(now)}): {label}'s QA passed.").strip()
            new = hqpaths.join_cells(cs)
            if len(hqpaths.cells(new)) == len(cs):
                text = text.replace(line, new, 1)
                done.append(lab)
        if done:
            q.write(text, jobs, on)
    return done


def tick_done(label: str, now: dt.datetime | None = None) -> bool:
    """5 November 2026, his yes in the laptop chat: an item that passed her check is ticked off on the planning (✅), so the open list
    is the real one; 15 items had passed and still stood open. Not a piece of a feature built in pieces with pieces left."""
    with q.locked():
        text, jobs, on = q.read()
        r = rows(text).get(label)
        if not r:
            return False
        line = r[0]
        cs = hqpaths.cells(line)
        if cs[0] != "⬜":
            return False
        m = re.search(r"\bpiece (\d+) of (\d+)\b", line, re.I)
        if m and int(m.group(1)) < int(m.group(2)):
            return False
        cs[0] = "✅"
        new = hqpaths.join_cells(cs)
        if len(hqpaths.cells(new)) != len(cs):
            return False
        q.write(text.replace(line, new, 1), jobs, on)
    return True


def fix_refuses(label: str) -> str | None:
    """F151: a fix on its road passes QA only when her tests pass on the build, the new one and the earlier ones, and the 17 happy flows."""
    import qatests
    if not qatests.fix_road(label):
        return None
    no = []
    d = qatests.folder(label)
    if qatests.fingerprint_of(d):
        import proof
        wt = proof._copy(qatests._head())
        try:
            got, out = qatests.run_on(d, wt)
        finally:
            proof._uncopy(wt)
        failing = [n for n, ok in got.items() if not ok]
        if failing:
            no.append(f"her QA tests {', '.join(failing)} fail on the build")
        elif not got:
            no.append(f"her QA tests didn't run: {out[-200:]}")
    else:
        no.append(f"{label} has no QA tests of hers to run")
    if hqpaths.under_test() and os.environ.get("HQ_HAPPY_FAKE_FAIL"):  # a test's stand-in for a red run of the 17
        no.append("the 17 happy flows didn't all pass for it")
    else:
        import proof
        if proof.gate_on():
            rec = proof.latest(label) or {}
            if not rec.get("green"):
                no.append("the 17 happy flows have no green run for it (routine/proof.py)")
    return ("the fix QA failed doesn't pass yet: " + "; ".join(no) + ".") if no else None


# The release gate.

def subject_labels(subject: str) -> list[str]:
    """The rows a commit is for, named at the start of its subject, before the first colon: "H283: ...",
    "H250, H256: ...", "H269, piece 2: ...", "F56 piece 1 of 2: ..."."""
    head, sep, _ = subject.partition(":")
    if not sep or len(head) > 60:
        return []
    out = []
    for m in re.finditer(r"(?<![\w.])[A-Z]\d+(?:\.\d+)*\b", head):
        if (l := renumbered(m.group(0))) not in out:
            out.append(l)
    return out


def renumbered(label: str) -> str:
    """F191: the label a renumbering gave an old one (routine/renumbered.json); a label moved twice reads as its newest, any other stays."""
    moved = {}
    try:
        for batch in json.loads((pathlib.Path(__file__).parent / "renumbered.json").read_text()).values():
            if isinstance(batch, dict):
                moved.update(batch)
    except (OSError, ValueError):
        return label
    seen = {label}
    while label in moved and moved[label] not in seen:
        label = moved[label]
        seen.add(label)
    return label


# F101 (C73): a commit that names no item holds the release, unless it only touches the tests, the version or the changelog.
# F112: the one set of free files, for the hold, the night and the release's status alike: the tests, the tutorial's text (flows 120 and 134 read it
# the same night), the version, the changelog, and the release's own way-back file.
FREE_FILES = ("app/happy_flows.py", "routine/flowsets.py", "app/test_", "app/web/tour.json", "VERSION", "CHANGELOG.md", "README.md", "updates/",
              "routine/way-back.json")


def proof_on() -> bool:
    import proof
    return proof.gate_on()


def only_free_files(root: str, sha: str) -> bool:
    r = subprocess.run(["git", "-C", str(root), "show", "--first-parent", "--format=", "--name-only", sha],
                       text=True, capture_output=True)
    files = [f for f in r.stdout.splitlines() if f.strip()]
    return r.returncode == 0 and all(f.startswith(FREE_FILES) for f in files)  # F112: a commit that changes nothing changes nothing


def commits(root: str, base: str, tip: str) -> list[tuple[str, str]]:
    """(sha, subject) of the commits in tip not in base, oldest first, first parent only."""
    r = subprocess.run(["git", "-C", str(root), "log", "--reverse", "--first-parent", "--format=%H%x09%s", f"{base}..{tip}"],
                       text=True, capture_output=True)
    return [tuple(ln.split("\t", 1)) for ln in r.stdout.splitlines() if "\t" in ln]


def _auto_tree(root: str, parents: list[str]) -> str | None:
    """The tree git writes by itself for a merge of two parents (conflicts left in), or None."""
    if len(parents) != 2:
        return None
    r = subprocess.run(["git", "-C", str(root), "merge-tree", "--write-tree", *parents], text=True, capture_output=True)
    return (r.stdout.split() or [None])[0] if r.returncode in (0, 1) else None


def _parents(root: str, sha: str) -> list[str]:
    return subprocess.run(["git", "-C", str(root), "rev-list", "--parents", "-n", "1", sha], text=True, capture_output=True).stdout.split()[1:]


def own_changes(root: str, sha: str) -> list[str] | None:
    """F112: what a merge commit changes by itself, beyond what git makes of its parents on its own: the files where its tree differs from the
    merge git would write (a conflict settled by hand, a file added or changed in the merge). None for a commit that isn't a merge."""
    parents = _parents(root, sha)
    if len(parents) < 2:
        return None
    auto = _auto_tree(root, parents)
    if auto:
        r = subprocess.run(["git", "-C", str(root), "diff", "--name-only", auto, f"{sha}^{{tree}}"], text=True, capture_output=True)
    else:  # an older git or more than two parents: every file the merge differs in from all of them
        r = subprocess.run(["git", "-C", str(root), "diff-tree", "--cc", "--name-only", "--no-commit-id", "-r", sha], text=True, capture_output=True)
    return [f for f in r.stdout.splitlines() if f.strip()]


def own_diff(root: str, sha: str, files: list[str]) -> str | None:
    """F112: a fingerprint of a merge's own changes in these files, as its QA read them; None when git can't make the merge to compare with."""
    import hashlib
    auto = _auto_tree(root, _parents(root, sha))
    if not auto:
        return None
    r = subprocess.run(["git", "-C", str(root), "diff", auto, f"{sha}^{{tree}}", "--", *sorted(files)], text=True, capture_output=True)
    return hashlib.sha256(r.stdout.encode("utf8")).hexdigest()[:16] if r.returncode == 0 else None


# F112: merges whose own changes had a QA of their own. Written by hand, next to BEFORE_GATE: the merge, the row it's QA'd under, the record that passed
# it (with a fix it goes only together with), and exactly what that QA read: the files and the fingerprint of those changes. A listed merge whose own
# changes are anything else, whose row hasn't passed, or whose fix isn't on the line with it, is held as before.
MERGES_PASSED = {
    "6fff93a": {"row": "H298", "record": "HQ/handoff-foundation-qa-f112.md, \"QA of the merge 6fff93a's own changes\", with the hook's fix b860621",
                "with": "b860621", "files": ["routine/cyclehook.py", "routine/cycles.py", "routine/review.py", "routine/runjob.py"], "diff": "cc97a792ed15d259"},
}


def merge_passed(root: str, sha: str, own: list[str], text: str) -> tuple[str | None, str]:
    """F112: (the commit it goes with, or "" for none; why not, when it's held). A listed merge passes on exactly what its QA read."""
    entry = next((v for k, v in MERGES_PASSED.items() if sha.startswith(k)), None)
    held = f"this merge changes files of its own: {', '.join(own[:5])}" + (" and more" if len(own) > 5 else "")
    if not entry:
        return None, held
    if sorted(own) != sorted(entry["files"]) or own_diff(root, sha, own) != entry["diff"]:
        return None, held + "; they aren't what its QA read"
    if state(entry["row"], text) != "passed":
        return None, held + f"; its row {entry['row']} hasn't passed QA"
    return entry.get("with") or "", ""


# F120: commits that belong to a row their subject doesn't name. Written by hand, next to MERGES_PASSED: the commit by its full 40-character id,
# the row it's for, and exactly what it changes against its first parent: every file and a fingerprint of that change (of git's raw listing with
# full blob ids, which no git setting changes). A listed commit counts for its row and is held until that row's QA passes, like any commit naming
# it; one whose changes are anything else isn't covered, and is held as a commit naming no item.
COMMITS_FOR = {
    "f6de1a4f2fb156bc53775a75fc0007c8f342cdbe": {
        "row": "F119", "files": ["CHANGELOG.md", "app/happy_flows.py", "app/startsize.py", "install/install.py", "routine/datachange.py",
                                 "routine/datachanges/002-briefing-for-a-workspace-without-switches.py", "routine/update.py"],
        "diff": "0ccea431a175d02a"},
}
_RAW = ["-c", "core.quotePath=true", "diff-tree", "-r", "--no-renames", "--full-index", "--no-commit-id", "--no-ext-diff", "--no-textconv"]


def changed_files(root: str, sha: str) -> list[str]:
    """F120: the files a commit changes against its first parent (no renames, whatever git is set to)."""
    r = subprocess.run(["git", "-C", str(root), *_RAW, "--name-only", f"{sha}^1", sha], text=True, capture_output=True)
    return [f for f in r.stdout.splitlines() if f.strip()] if r.returncode == 0 else []


def commit_diff(root: str, sha: str, files: list[str]) -> str | None:
    """F120: a fingerprint of what a commit changes in these files against its first parent: the raw listing, modes and full blob ids, so it
    stays the same with any core.abbrev, diff.noprefix or diff.renames; None when git can't tell."""
    import hashlib
    r = subprocess.run(["git", "-C", str(root), *_RAW, f"{sha}^1", sha, "--", *sorted(files)], text=True, capture_output=True)
    return hashlib.sha256(r.stdout.encode("utf8")).hexdigest()[:16] if r.returncode == 0 and r.stdout.strip() else None


def full_id(root: str, sha: str) -> str | None:
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "-q", "--verify", f"{sha}^{{commit}}"], text=True, capture_output=True)
    return r.stdout.strip() if r.returncode == 0 else None


def listed_row(root: str, sha: str) -> tuple[str | None, str]:
    """F120: (the row COMMITS_FOR gives this commit, or None; why it isn't covered, when it's listed). Only by its full id, and only on exactly
    what the list names."""
    full = sha if len(sha) == 40 else full_id(root, sha)
    entry = COMMITS_FOR.get(full or "")
    if not entry:
        return None, ""
    files = changed_files(root, sha)
    if sorted(files) != sorted(entry["files"]) or commit_diff(root, sha, files) != entry["diff"]:
        return None, f"; it's listed for {entry['row']}, but its changes aren't what the list names"
    return entry["row"], ""


def commit_labels(root: str, sha: str, subject: str) -> list[str]:
    """F120: the rows a commit is for: named at the start of its subject, else the one COMMITS_FOR gives it."""
    named = subject_labels(subject)
    if named:
        return named
    row, _ = listed_row(root, sha)
    return [row] if row else []


def brought(root: str, base: str, sha: str) -> list[tuple[str, str]]:
    """F112: what a merge commit brings: (sha, subject) of the commits behind its other parents that the line didn't have yet, and that
    aren't in the release already. Empty for anything else, and for a merge that brings nothing new (a version merged back)."""
    parents = subprocess.run(["git", "-C", str(root), "rev-list", "--parents", "-n", "1", sha], text=True, capture_output=True).stdout.split()[1:]
    if len(parents) < 2:
        return []
    r = subprocess.run(["git", "-C", str(root), "log", "--reverse", "--no-merges", "--format=%H%x09%s", sha, f"^{parents[0]}", f"^{base}"],
                       text=True, capture_output=True)
    return [tuple(ln.split("\t", 1)) for ln in r.stdout.splitlines() if "\t" in ln]


# F112: the rows from before the gate. Written by hand, here and nowhere else, by commit: each names the tag the row went out in and the commits on the
# line that never had a QA job because the gate didn't exist yet. Those commits go out on this say; a new commit under the same row's name doesn't, it
# needs its QA like any other, and a failed QA mark wins over the list. The gate checks the tag against git, so a line can't wave anything through.
# Without a tag: the row is in no version, its QA is real work, and its commits are held with this why. The list only ever gets shorter.
BEFORE_GATE = {
    "F66": {"tag": None, "commits": ["6435c01"], "why": "built 28 October, in no version yet: its QA is real work"},
    "H227": {"tag": "v0.4.19", "commits": ["f0f6300"], "why": "out since 0.4.19; one later commit reads the tutorial against HQ, the night's own read"},
    "F17": {"tag": "v0.4.19", "commits": ["047e4c7"], "why": "out since 0.4.19; one later commit guards the workspace's folder from a test"},
    "H230": {"tag": "v0.4.19", "commits": ["e69d82e", "b28db02"], "why": "out since 0.4.19; two later fixes to a trip's times and its text"},
}


def in_version(root: str, label: str, tag: str) -> bool:
    """F112: whether a commit naming this row stands in that version tag."""
    r = subprocess.run(["git", "-C", str(root), "log", "--format=%s", tag], text=True, capture_output=True)
    return r.returncode == 0 and any(label in subject_labels(s) for s in r.stdout.splitlines())


def before_gate(root: str, label: str, sha: str | None = None) -> dict | None:
    """F112: what the list says of this row and this commit: {"label", "tag", "why", "shipped", "covers"}; None for a row that isn't on it.
    covers: the commit is one the list names."""
    d = BEFORE_GATE.get(label)
    if not d:
        return None
    tag, why, cs = d.get("tag"), d.get("why") or "", d.get("commits") or []
    return {"label": label, "tag": tag, "why": why, "commits": cs, "shipped": bool(tag) and in_version(root, label, tag),
            "covers": bool(sha) and any(sha.startswith(c) for c in cs)}


def hold(root: str | None = None, base: str = "main", tip: str = "dev", text: str | None = None) -> dict:
    """What the release can take: {"to": sha or None (the last commit it takes; None: nothing new it may take),
    "tip": dev's sha or None, "taken": [labels], "held": [{"label", "why"}], "behind": [labels that passed but come
    after a held one], "commits": {label: [shas of its own commits]}, "before_gate": [what BEFORE_GATE let through, each with "goes": in what would go out], "all": bool}.
    F112: it looks at what each commit brings: a merge passes when what it brought passed, and is held by the first thing it brought that
    isn't; it names nothing itself for that."""
    root = root or ROOT
    text = q.read()[0] if text is None else text
    all_rows = rows(text)
    cs = commits(root, base, tip)
    to, taken, held, behind, stop, past = None, [], [], [], False, {}
    by_row = {}  # F152: each row's own commits, so a release can bring in a checked row on its own
    pending, waiting = None, []  # F112: a passed merge that goes only together with its fix: (merge, fix), and the rows on the way to it
    held_label = lambda l: l in [h["label"] for h in held]

    def wait_held(why):
        held.append({"label": pending[0][:7], "why": f"its own changes passed QA, but it goes only together with {pending[1]}, {why}"})
        for l in waiting:
            if l not in behind and state(l, text) == "passed":
                behind.append(l)
    for sha, subject in cs:
        parts = brought(root, base, sha)
        named_here = [l for l in subject_labels(subject) if l in all_rows]
        parts = parts + ([(sha, subject)] if named_here or not parts else [])
        need, bad, nameless = [], [], []
        mine = own_changes(root, sha)  # F112: a merge's own changes are its own, held like a commit naming no item
        if mine is not None and not named_here and proof_on():
            own = [f for f in mine if not f.startswith(FREE_FILES)]
            if own:
                fix, why = merge_passed(root, sha, own, text)
                if fix is None:
                    nameless.append((sha, why))
                elif fix and not pending:
                    pending = (sha, fix)
        for s, subj in parts:
            named = [l for l in commit_labels(root, s, subj) if l in all_rows]
            for l in named:
                if s not in by_row.setdefault(l, []):
                    by_row[l].append(s)
                if all_rows[l][1] not in GATED:
                    continue
                if l not in need:
                    need.append(l)
                st = state(l, text)
                if st == "passed":
                    continue
                said = before_gate(root, l, s)
                if said and said["shipped"] and said["covers"] and st != "failed":
                    past.setdefault(l, said)
                    continue
                if not any(b[0] == l for b in bad):
                    bad.append((l, said, s))
            if not named and proof_on() and not only_free_files(root, s):  # F101: nothing goes out that no item asked for
                nameless.append((s, f"this commit names no item: {subj[:70]}" + listed_row(root, s)[1]))
        was_stopped = stop
        stop = stop or bool(bad or nameless)
        if stop and pending and not was_stopped:
            wait_held("which is held behind it")
            pending = None
        if stop:
            for s, why in nameless:
                held.append({"label": s[:7], "why": why})
            for l, said, s in bad:
                if held_label(l):
                    continue
                st = state(l, text)
                ms = marks(all_rows[l][0])
                if st == "failed":
                    why = f"QA failed: {ms[-1][2].rstrip('.')}"
                    import wholebuild
                    if (wholebuild.load()["items"].get(l) or {}).get("stage") == "held" and wholebuild.on():
                        why += " (held after the whole-build review's one fix round; it waits for him)"
                    elif fails_in_a_row(all_rows[l][0]) >= MAX_FAILS:
                        why += f" ({MAX_FAILS} times; it waits for a call)"
                elif said and not said["tag"]:
                    why = said["why"]
                elif said and not said["shipped"]:
                    why = f"listed as out in {said['tag']}, but no commit of it stands there"
                elif said:
                    why = f"no QA yet: {s[:7]} came after the list of what went out before the gate"
                else:
                    why = "no QA yet"
                held.append({"label": l, "why": why})
            for l in need:
                if not held_label(l) and l not in behind and l not in taken and state(l, text) == "passed":
                    behind.append(l)
            continue
        if pending:  # the rows on the way to the fix go when the fix does
            waiting += [l for l in need if l not in waiting]
            if not sha.startswith(pending[1]):
                continue
            need, waiting, pending = waiting, [], None
        to = sha
        for l in need:
            if l not in taken and state(l, text) == "passed":
                taken.append(l)
            if l in past:
                past[l]["goes"] = True
    if pending:
        wait_held("which isn't on this line yet")
    tipsha = cs[-1][0] if cs else None
    return {"to": to, "tip": tipsha, "taken": taken, "held": held, "behind": [l for l in behind if l not in taken],
            "before_gate": [{**x, "goes": bool(x.get("goes"))} for x in past.values()], "all": bool(cs) and to == tipsha,
            "commits": by_row}


def before_words(h: dict, going: bool = False) -> str:
    """F112: the rows from before the gate that this release takes without a QA mark, said every time."""
    xs = [x for x in h.get("before_gate") or [] if x["goes"] or not going]
    return "Released before the gate, no QA mark: " + "; ".join(f"{x['label']} ({x['why']})" for x in xs) + "." if xs else ""


def hold_words(h: dict) -> str:
    if not h["tip"]:
        return "QA: nothing new since the last release, so nothing to hold."
    before = before_words(h)
    if h["all"]:
        return "QA: everything new has passed QA (or needs none)" + (f": {', '.join(h['taken'])}." if h["taken"] else ".") + (f" {before}" if before else "")
    parts = [f"QA passed and goes out: {', '.join(h['taken'])}" if h["taken"] else ("What goes out needs no QA" if h["to"] else "Nothing goes out")]
    parts.append("held on nightly: " + "; ".join(f"{x['label']} ({x['why']})" for x in h["held"]))
    if h["behind"]:
        parts.append(f"passed QA but built after it, so it waits too: {', '.join(h['behind'])}")
    return "QA: " + ". ".join(parts) + "." + (f" {before}" if before else "")


def _features():
    sys.path.insert(0, os.path.join(ROOT, "app"))
    import features
    return features


def ship_whole(label: str, row: str) -> list[str]:
    """F56, piece 2: a feature built in pieces stays hidden (app/features-in-pieces.json) until its last piece passes
    QA. The last piece is the one that marks the row done (✅); a pass on a row still open leaves it hidden."""
    try:
        fs = _features()
        fids = fs.for_row(label)
    except Exception:
        return []
    if not fids:
        return []
    if not (row or "").lstrip("| ").startswith("✅"):
        return [f"{', '.join(fids)} stays switched off for everyone but the maker: {label} isn't done yet "
                "(more pieces to come)."]
    out = [fs.ship(f) for f in fids]
    out.append("Commit app/features-in-pieces.json with the row's label first, and push.")
    return out


def prompt_extra(text: str, n: int | None = None) -> str:
    """The QA job's first prompt gets Moneypenny's character and craft (F56). A build of a piece of a feature gets
    the in-pieces rule (F56, piece 2)."""
    if (text or "").startswith("Prep of "):  # the line (5 November 2026): a prep job runs as Moneypenny too
        try:
            from pathlib import Path
            sys.path.insert(0, os.path.join(ROOT, "app"))
            import agents
            a = agents.find(Path(hqpaths.FOLDER), "moneypenny")
            body = f"Your character: {a['personality']}\nHow you work:\n{a.get('craft', '')}\n"
        except Exception as e:
            body = f"(Her character couldn't be loaded here: {e!r}.)\n"
        return ("\n\nThis is a prep job of the line. You are Moneypenny, head of development, getting one item ready for the team, "
                "on his switch or your own. The program sends it to the team once it's ready and its build switch is on; you do the "
                "work, never the send. Every step's result is read from the record, never from what you say.\n" + body)
    if not is_qa(text):
        m = re.search(r"\bpiece (\d+) of (\d+)\b", text or "", re.I)
        if not m or int(m.group(2)) < 2 or not job_label(text):
            return ""
        return ("\n\nThis is a piece of a feature built in pieces (F56, piece 2). A feature people would see or use, "
                "built in pieces, ships switched off until its last piece passes QA: if this piece brings a new switch, "
                "button or screen and it isn't in app/features-in-pieces.json yet, add it there "
                '({"id", "name", "line", "buttons", "row", "pieces"}, the row is its label), and gate it with '
                "features.is_on(id) on the server and its buttons in the list, so only the maker's HQ shows it. "
                "QA takes it off that list when the last piece passes. Not for a piece that only changes the routine or "
                "HQ's own working (no one else sees it).\n")
    try:
        from pathlib import Path
        sys.path.insert(0, os.path.join(ROOT, "app"))
        import agents
        a = agents.find(Path(hqpaths.FOLDER), "moneypenny")
        body = f"Your character: {a['personality']}\nHow you work:\n{a.get('craft', '')}\n"
    except Exception as e:
        body = f"(Her character couldn't be loaded here: {e!r}. Work as head of development: the definition of done is the gate.)\n"
    import wholebuild
    if wholebuild.is_review(text):  # 11 November 2026: the whole-build review, her character, then what the program put together
        return ("\n\nThis is a QA job (F56) over the whole build. You are Moneypenny, head of development, checking the team's work "
                "before it reaches anyone; not done is not done.\n" + body + wholebuild.prompt(text, n))
    return ("\n\nThis is a QA job (F56). You are Moneypenny, head of development, checking the team's work before it "
            "reaches anyone; not done is not done.\n" + body
            + "A feature built in pieces (F56, piece 2): from its first piece it's in app/features-in-pieces.json, so "
            "only the maker's HQ shows it. Check that it is, while pieces are left (HQ_MAKER=0 hides it); when the "
            "row's last piece passes, qa.py pass takes it off that list: commit that file too.\n"
            "A check that only runs on a Mac (F216): on the server, don't fail the row for that alone. When the Mac example is the only "
            "open part, say so in qa.py fail (\"Not run: the Mac example ... nothing broken\", or --mac-only --flow N): the program hands "
            "that flow to the paired laptop at the row's build commit and writes the laptop's result as your verdict, or waits for the "
            "laptop while it's off.\n")


_PIECE = re.compile(r"\bpiece \d+ of (\d+)\b", re.I)
_COMPARED = re.compile(r"\d+\s*(?:of|/|out of)\s*\d+", re.I)


def _in_commit(sha: str, head: str | None) -> bool:
    """F121: whether a commit is in the one a record ran on."""
    import proof
    if not head:
        return False
    return subprocess.run(["git", "-C", str(proof.ROOT), "merge-base", "--is-ancestor", sha, head], capture_output=True).returncode == 0


def proof_refuses(label: str, compared: str) -> str | None:
    """F101: QA's pass stands on what a program saw, never on what's typed: the build's green record, a comparison on
    real data that says what, how many and how many right, and for a piece, its switch on the hidden list."""
    import proof
    if not proof.gate_on():
        return None
    rec = proof.latest(label)
    if not rec:
        return f"{label} has no record of a green run (routine/proof.py run), so there's nothing to pass."
    try:
        import qatests  # real QA: the record must hold her tests' run at the end, green
        if qatests.gate_on() and not (rec.get("qa_tests") or {}).get("green"):
            return f"the last run for {label} has no green run of her QA tests: {(rec.get('qa_tests') or {}).get('why') or 'none ran'}."
    except ImportError:
        return f"{label}'s QA tests couldn't be read, so there's nothing to pass."
    if not rec.get("green"):
        return f"the last run for {label} wasn't green: {'; '.join((rec.get('failed') or []) + (rec.get('not_tried') or []))[:400]}."
    # F121: the record has to hold every commit of the row: one made before a newer commit of it doesn't stand for it
    newer = [c for c in proof.all_commits(label) if not _in_commit(c.split()[0], rec.get("head"))]
    if newer:
        return (f"the last green run for {label} was on {str(rec.get('head') or 'no commit')[:7]}, before {len(newer)} of its commits "
                f"({', '.join(c.split()[0] for c in newer[:5])}): run it again on the commit HQ is on.")
    if not (compared and re.search(r"[A-Za-z]{3}", compared) and _COMPARED.search(compared)):
        return ("a pass names a comparison on real data: --compared \"what, how many, how many right\", like "
                "\"open planning rows read whole, 61 of 61\".")
    text = q.read()[0]
    r = rows(text).get(label)
    m = _PIECE.search(r[0]) if r else None
    if m and int(m.group(1)) >= 2:
        try:
            listed = bool(_features().for_row(label))
        except Exception:
            listed = False
        if not listed:
            return f"{label} is built in pieces and its switch isn't on the hidden list (app/features-in-pieces.json)."
    return None


# ---------- H342: how many items pass her check the first time, each week ----------
# His row (8 November 2026): "each week HQ counts how many items pass her check the first time (now 55 of 69), for the weekly
# retrospective (H341)". Counted from the record QA writes, the marks in the rows (the newest counts for the row, the first says how its
# first check went): an item belongs to the week its first mark fell in, Monday to Sunday, and passed the first time when that mark is
# "QA passed". The week's checks in all (every mark, first or not) are counted next to it: the 55 of 69 of his row is that number.

def _mark_day(when: str) -> dt.date | None:
    try:
        return dt.datetime.strptime(" ".join(when.split()[:3]), "%d %B %Y").date()
    except ValueError:
        return None


def first_time(text: str | None = None, weeks: int = 8, today: dt.date | None = None) -> list[dict]:
    """The last `weeks` weeks, newest first: {"from", "to", "words_week", "items", "first_time", "sent_back", "back", "checks", "passed"}."""
    text = q.read()[0] if text is None else text
    today = today or dt.date.today()
    monday = today - dt.timedelta(days=today.weekday())
    out = []
    for k in range(weeks):
        lo = monday - dt.timedelta(days=7 * k)
        out.append({"from": lo.isoformat(), "to": (lo + dt.timedelta(days=6)).isoformat(), "items": 0, "first_time": 0, "back": [],
                    "checks": 0, "passed": 0})
    by = {w["from"]: w for w in out}

    def week_of(d):
        return by.get((d - dt.timedelta(days=d.weekday())).isoformat()) if d else None

    for label, (line, _phase) in rows(text).items():
        ms = marks(line)
        if not ms:
            continue
        w = week_of(_mark_day(ms[0][1]))
        if w:
            w["items"] += 1
            if ms[0][0] == "passed":
                w["first_time"] += 1
            else:
                w["back"].append(label)
        for verdict, when, _ in ms:
            w2 = week_of(_mark_day(when))
            if w2:
                w2["checks"] += 1
                w2["passed"] += verdict == "passed"
    for w in out:
        lo, hi = dt.date.fromisoformat(w["from"]), dt.date.fromisoformat(w["to"])
        w["sent_back"] = w["items"] - w["first_time"]
        w["words_week"] = (f"{lo.day} to {hi.day} {hi:%B %Y}" if lo.month == hi.month else f"{lo.day} {lo:%B} to {hi.day} {hi:%B %Y}")
        w["words"] = first_time_words(w)
    return out


def first_time_words(w: dict) -> str:
    if not w["items"] and not w["checks"]:
        return f"Week of {w['words_week']}: no item had her check yet."
    return (f"Week of {w['words_week']}: {w['first_time']} of {w['items']} items passed her check the first time"
            + (f" ({w['sent_back']} sent back: {', '.join(w['back'][:12])}{'…' if len(w['back']) > 12 else ''})" if w["sent_back"] else "")
            + f"; {w['passed']} of {w['checks']} checks passed in all.")


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    job = None
    if "--job" in args:
        i = args.index("--job")
        job = int(args[i + 1]) if i + 1 < len(args) and args[i + 1].isdigit() else None
        args = args[:i] + args[i + 2:]
    label = (args[0] if args else "").upper()
    if cmd in ("pass", "fail", "state", "queue") and not LABEL.fullmatch(label):
        print("Which row? Give its label, like H247.")
        return 2
    mac_only, mac_flow = False, None
    if "--mac-only" in args:  # F216: the QA says its only open part is a Mac example (else it's read from its words)
        args.remove("--mac-only")
        mac_only = True
    if "--flow" in args:
        i = args.index("--flow")
        mac_flow = int(args[i + 1]) if i + 1 < len(args) and args[i + 1].isdigit() else None
        args = args[:i] + args[i + 2:]
    compared = ""
    if "--compared" in args:  # F101: what was compared on real data, how many, how many right
        i = args.index("--compared")
        compared = " ".join((args[i + 1] if i + 1 < len(args) else "").split())
        args = args[:i] + args[i + 2:]
    if cmd in ("pass", "fail"):
        args, ev, err = evidence(args)
        if err or (cmd == "pass" and not ev):
            print(f"{err} " if err else "", end="")
            print(PASS_REFUSED if cmd == "pass" else "Each example needs --example, --ran and --got, in that order. Nothing written.")
            return 2
        if ev:
            summary = " ".join(" ".join(args[1:]).split()).rstrip(".")
            args = args[:1] + [(summary + ". " if summary else "") + tried_words(ev)]
    if cmd == "pass":
        # H313, his words of 4 November 2026: a report line "not tried" or "not covered" holds QA and the release until it's run for real
        held = NOT_TRIED.search(" ".join(args[1:]) + " " + compared)
        if held:
            print(f"Refused: the pass says \"{held.group(0)}\": that holds QA until it's run for real (H313). Run it, or fail it. Nothing written.")
            return 2
        no = fix_refuses(label) or proof_refuses(label, compared)
        if no:
            print(f"Refused: {no} Nothing written.")
            return 2
        args = args[:1] + [" ".join(args[1:]).rstrip(". ") + f". Compared: {compared}"]
        row = mark(label, True, " ".join(args[1:]), job)
        import trail
        trail.step(item_id(label), "qa", state="passed", job=job)
        import qatests
        qatests.qa_passed(label)
        import wholebuild
        wholebuild.on_pass(label, job)
        print(f"QA passed for {label}, in its row; the release may take it.")
        for lab in close_replaced(label):
            print(f"{lab} is closed as replaced by {label}.")
        if tick_done(label):
            print(f"{label} is ticked off on the planning.")
        for said in ship_whole(label, row):
            print(said)
        return 0
    if cmd == "fail":
        # F216: a fail whose only open part is a Mac half goes to the paired laptop (routine/machalf.py), never a fail on the server
        import machalf
        said = machalf.takes(label, " ".join(args[1:]), job, force=mac_only, flow=mac_flow)
        print(said or fail(label, " ".join(args[1:]), job))
        return 0
    if cmd == "state":
        text = q.read()[0]
        r = rows(text).get(label)
        ms = marks(r[0]) if r else []
        print(f"{label}: " + (f"QA {ms[-1][0]} ({ms[-1][1]}): {ms[-1][2]}" if ms else "no QA yet")
              + ("" if r and r[1] in GATED else " (not in Bugs or Features: no QA needed)"))
        return 0
    if cmd == "queue":
        print(queue(label, " ".join(args[1:])))
        return 0
    if cmd == "hold":
        print(hold_words(hold()))
        return 0
    if cmd == "first-time":  # H342: the weekly first-time count, for the retrospective (H341) and the status page
        n = 8
        if "--weeks" in args:
            i = args.index("--weeks")
            n = int(args[i + 1]) if i + 1 < len(args) and args[i + 1].isdigit() else 8
        ws = first_time(weeks=max(1, min(n, 104)))
        print(json.dumps({"weeks": ws}, ensure_ascii=False) if "--json" in args else "\n".join(w["words"] for w in ws))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    import routines
    try:
        code = main(sys.argv[1:])
    except Exception as e:  # F102: a failure of QA itself: red, with an incident
        routines.bad("qa", f"qa.py {' '.join(sys.argv[1:2])} failed: {e!r}", every=30 * 86400)
        raise
    if sys.argv[1:2] in (["pass"], ["fail"]) and not code:
        routines.good("qa", f"QA {sys.argv[1]} written", every=30 * 86400)
    sys.exit(code)
