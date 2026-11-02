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
- A fail queues a fix job (a small build) that reads the row and its QA failed line; when that's done, QA again. After
  MAX_FAILS failed QAs in a row no fix job is queued by itself: it waits for a call, and the morning text says so.
- The release (release.py) walks dev's commits since main, oldest first; each names its rows at the start of its
  subject ("H283: ..."). A commit for a row in Phase F or H without "QA passed" stops the walk: main gets the work
  before it, the rest stays on dev and nightly, and the morning text names what was held and why (hold()). F112: a merge
  commit is what it brings, and BEFORE_GATE is the one list of rows from before the gate, each said or named held.
  A commit without a row (a version, a nightly test fix, a merge) or for a row elsewhere (maintenance) goes along.

F71 (28 October 2026): QA jobs since 27 October mostly took one or two minutes, and their write-ups said what was
tried as a whole, not each done example with what was run and what came out; one passed on its flows alone. A pass
now names every done example of the row with its evidence, three flags each, in order: --example (the row's own
example), --ran (the command, page or step really run for it) and --got (what came out). A pass without them, or
with an example missing its ran or got, is refused and nothing is written. The mark keeps them: "Tried: (1) ...".

usage:
  python3 routine/qa.py pass LABEL "SUMMARY" --example E --ran R --got G [--example ... ] [--job N]
                                                                QA passed, in the row, each example with its evidence
  python3 routine/qa.py fail LABEL "WHAT'S OFF" [--job N]       QA failed, in the row; a fix job for the team
  python3 routine/qa.py state LABEL                             passed, failed or none, with the newest mark
  python3 routine/qa.py queue LABEL                             a QA job for the row now (a call, or by hand)
  python3 routine/qa.py hold                                    what the release would take and what it would hold
"""
from __future__ import annotations

import datetime as dt
import os
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


PASS_REFUSED = ("Refused: a pass names every done example of the row with its evidence (F71). For each one: "
                "--example \"the row's example\" --ran \"what was really run for it\" --got \"what came out\". "
                "An example that couldn't be tried is a fail, or said in the summary as not tried, with why. Nothing written.")


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
            "\"what's off, plainly\" --job N (a fail queues a fix job by itself). No helpers fanned out (F55). Nothing to push "
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
    jobs.append(j)
    return j


def _estimate(j: dict, kind: str) -> None:
    try:
        q.estimate("on_add", j["n"], j["text"], kind)
    except Exception:
        pass


def on_done(jobs: list, j: dict, text: str, kind: str | None) -> dict | None:
    """Inside jobs.py done (its lock held): a finished build for a row in Bugs or Features gets a QA job, at the end
    of the line. Returns the new job (not written yet), or None."""
    if kind not in ("build", "bigbuild") or is_qa(j["text"]):
        return None
    label = (j.get("item") or {}).get("label") or job_label(j["text"])  # F103: the carried id's row, never a sentence again
    if not label or not gated(label, text) or _waiting_for(jobs, label, qa=True):
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


def fail(label: str, what: str, job: int | None = None) -> str:
    item = item_id(label)
    bug_after_qa(label, what)  # a pass that didn't hold: against that QA; nothing when the row had no pass
    row = mark(label, False, what, job)
    import mistakes, trail
    mistakes.add("qa-fail", "team", what, where=f"QA job {job}" if job else "QA by hand", label=label, item=item or "")
    trail.step(item, "qa", state="failed", job=job, words=what[:300])
    name = title_of(label)
    if fails_in_a_row(row) >= MAX_FAILS:
        tell("qa-failed", f"What: {name}\nWhat's off: {what}\nIt didn't pass {MAX_FAILS} times in a row, so no fix "
                          "goes to the team by itself: it waits for him, on a call or here.", item)
        return (f"QA failed for {label}, {MAX_FAILS} times in a row now: no fix job by itself; it waits for a call, "
                "and the release holds it.")
    tell("qa-failed", f"What: {name}\nWhat's off: {what}\nIt went back to the team for a fix; your check follows by itself.", item)
    with q.locked():
        text, jobs, on = q.read()
        w = _waiting_for(jobs, label, qa=False)
        if w and w["text"].startswith("Fix for "):
            return f"QA failed for {label}; a fix job is already waiting: job {w['n']}."
        j = _append(jobs, fix_text(label, " ".join(what.split()).rstrip("."), job), label)
        q.write(text, jobs, on)
    _estimate(j, "build")
    return f"QA failed for {label}; job {j['n']} is the fix, and QA follows by itself."


# The release gate.

def subject_labels(subject: str) -> list[str]:
    """The rows a commit is for, named at the start of its subject, before the first colon: "H283: ...",
    "H250, H256: ...", "H269, piece 2: ...", "F56 piece 1 of 2: ..."."""
    head, sep, _ = subject.partition(":")
    if not sep or len(head) > 60:
        return []
    return [m.group(0) for m in re.finditer(r"(?<![\w.])[A-Z]\d+(?:\.\d+)*\b", head)]


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
    after a held one], "before_gate": [what BEFORE_GATE let through, each with "goes": in what would go out], "all": bool}.
    F112: it looks at what each commit brings: a merge passes when what it brought passed, and is held by the first thing it brought that
    isn't; it names nothing itself for that."""
    root = root or ROOT
    text = q.read()[0] if text is None else text
    all_rows = rows(text)
    cs = commits(root, base, tip)
    to, taken, held, behind, stop, past = None, [], [], [], False, {}
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
            named = [l for l in subject_labels(subj) if l in all_rows]
            for l in named:
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
                nameless.append((s, f"this commit names no item: {subj[:70]}"))
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
                    if fails_in_a_row(all_rows[l][0]) >= MAX_FAILS:
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
            "before_gate": [{**x, "goes": bool(x.get("goes"))} for x in past.values()], "all": bool(cs) and to == tipsha}


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


def prompt_extra(text: str) -> str:
    """The QA job's first prompt gets Moneypenny's character and craft (F56). A build of a piece of a feature gets
    the in-pieces rule (F56, piece 2)."""
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
    return ("\n\nThis is a QA job (F56). You are Moneypenny, head of development, checking the team's work before it "
            "reaches anyone; not done is not done.\n" + body
            + "A feature built in pieces (F56, piece 2): from its first piece it's in app/features-in-pieces.json, so "
            "only the maker's HQ shows it. Check that it is, while pieces are left (HQ_MAKER=0 hides it); when the "
            "row's last piece passes, qa.py pass takes it off that list: commit that file too.\n")


_PIECE = re.compile(r"\bpiece \d+ of (\d+)\b", re.I)
_COMPARED = re.compile(r"\d+\s*(?:of|/|out of)\s*\d+", re.I)


def proof_refuses(label: str, compared: str) -> str | None:
    """F101: QA's pass stands on what a program saw, never on what's typed: the build's green record, a comparison on
    real data that says what, how many and how many right, and for a piece, its switch on the hidden list."""
    import proof
    if not proof.gate_on():
        return None
    rec = proof.latest(label)
    if not rec:
        return f"{label} has no record of a green run (routine/proof.py run), so there's nothing to pass."
    if not rec.get("green"):
        return f"the last run for {label} wasn't green: {'; '.join(rec.get('failed') or [])[:300]}."
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
        no = proof_refuses(label, compared)
        if no:
            print(f"Refused: {no} Nothing written.")
            return 2
        args = args[:1] + [" ".join(args[1:]).rstrip(". ") + f". Compared: {compared}"]
        row = mark(label, True, " ".join(args[1:]), job)
        import trail
        trail.step(item_id(label), "qa", state="passed", job=job)
        print(f"QA passed for {label}, in its row; the release may take it.")
        for said in ship_whole(label, row):
            print(said)
        return 0
    if cmd == "fail":
        print(fail(label, " ".join(args[1:]), job))
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
