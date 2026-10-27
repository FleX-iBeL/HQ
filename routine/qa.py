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
  before it, the rest stays on dev and nightly, and the morning text names what was held and why (hold()).
  A commit without a row (a version, a nightly test fix, a merge) or for a row elsewhere (maintenance) goes along.

usage:
  python3 routine/qa.py pass LABEL "WHAT WAS TRIED" [--job N]   QA passed, in the row
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
    """The QA marks in a row, oldest first: (passed|failed, when, what)."""
    return [(m.group(1), m.group(2), m.group(3).strip()) for m in MARK.finditer(line or "")]


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
        cells = [c.strip() for c in line.rstrip().split("|")[1:-1]]
        at = len(cells) - 2 if len(cells) >= 6 else len(cells) - 1
        word = "passed" if passed else "failed"
        new = f"QA {word} ({f'job {job}' if job else 'by hand'}, {_when(now)}): {what}."
        cells[at] = (cells[at].strip() + " " + new).strip()
        row2 = ("| " + " | ".join(cells) + " |").replace("|  |", "| |").replace("|  |", "| |")
        text = text.replace(line, row2, 1)
        q.write(text, jobs, on)
        return row2


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
            f"result: python3 routine/qa.py pass {label} \"what was tried\" --job N, or python3 routine/qa.py fail {label} "
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
        if is_qa(j["text"]) == qa and job_label(j["text"]) == label:
            return j
    return None


def _append(jobs: list, text: str) -> dict:
    n = max([j["n"] for j in jobs] + [0]) + 1
    j = {"n": n, "state": "ready", "past": False, "agreed": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
         "text": q.one_line(text).replace("·", "-")}
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
    label = job_label(j["text"])
    if not label or not gated(label, text) or _waiting_for(jobs, label, qa=True):
        return None
    return _append(jobs, qa_text(label, f"the team finished job {j['n']} for it."))


def queue(label: str, after: str = "") -> str:
    with q.locked():
        text, jobs, on = q.read()
        if label not in rows(text):
            sys.exit(f"No {label} row on the roadmap.")
        w = _waiting_for(jobs, label, qa=True)
        if w:
            return f"{label} already has a QA job: job {w['n']} ({w['state']})."
        j = _append(jobs, qa_text(label, after or "asked for on a call."))
        q.write(text, jobs, on)
    _estimate(j, "qa")
    return f"Job {j['n']} is ready: QA of {label}."


def fail(label: str, what: str, job: int | None = None) -> str:
    row = mark(label, False, what, job)
    if fails_in_a_row(row) >= MAX_FAILS:
        return (f"QA failed for {label}, {MAX_FAILS} times in a row now: no fix job by itself; it waits for a call, "
                "and the release holds it.")
    with q.locked():
        text, jobs, on = q.read()
        w = _waiting_for(jobs, label, qa=False)
        if w and w["text"].startswith("Fix for "):
            return f"QA failed for {label}; a fix job is already waiting: job {w['n']}."
        j = _append(jobs, fix_text(label, " ".join(what.split()).rstrip("."), job))
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
    return [m.group(0) for m in re.finditer(r"(?<![\w.])[HF]\d+(?:\.\d+)*\b", head)]


def commits(root: str, base: str, tip: str) -> list[tuple[str, str]]:
    """(sha, subject) of the commits in tip not in base, oldest first, first parent only."""
    r = subprocess.run(["git", "-C", str(root), "log", "--reverse", "--first-parent", "--format=%H%x09%s", f"{base}..{tip}"],
                       text=True, capture_output=True)
    return [tuple(ln.split("\t", 1)) for ln in r.stdout.splitlines() if "\t" in ln]


def hold(root: str | None = None, base: str = "main", tip: str = "dev", text: str | None = None) -> dict:
    """What the release can take: {"to": sha or None (the last commit it takes; None: nothing new it may take),
    "tip": dev's sha or None, "taken": [labels], "held": [{"label", "why"}], "behind": [labels that passed but come
    after a held one], "all": bool}."""
    root = root or ROOT
    text = q.read()[0] if text is None else text
    all_rows = rows(text)
    cs = commits(root, base, tip)
    to, taken, held, behind, stop = None, [], [], [], False
    for sha, subject in cs:
        need = [l for l in subject_labels(subject) if l in all_rows and all_rows[l][1] in GATED]
        bad = [l for l in need if state(l, text) != "passed"]
        if bad and not stop:
            stop = True
        if stop:
            for l in bad:
                if l not in [h["label"] for h in held]:
                    s = state(l, text)
                    ms = marks(all_rows[l][0])
                    why = (f"QA failed: {ms[-1][2].rstrip('.')}" if s == "failed" else "no QA yet")
                    if s == "failed" and fails_in_a_row(all_rows[l][0]) >= MAX_FAILS:
                        why += f" ({MAX_FAILS} times; it waits for a call)"
                    held.append({"label": l, "why": why})
            for l in need:
                if l not in bad and l not in behind and l not in taken:
                    behind.append(l)
            continue
        to = sha
        for l in need:
            if l not in taken:
                taken.append(l)
    tipsha = cs[-1][0] if cs else None
    return {"to": to, "tip": tipsha, "taken": taken, "held": held, "behind": [l for l in behind if l not in taken],
            "all": bool(cs) and to == tipsha}


def hold_words(h: dict) -> str:
    if not h["tip"]:
        return "QA: nothing new since the last release, so nothing to hold."
    if h["all"]:
        return "QA: everything new has passed QA (or needs none)" + (f": {', '.join(h['taken'])}." if h["taken"] else ".")
    parts = []
    if h["taken"]:
        parts.append(f"QA passed and goes out: {', '.join(h['taken'])}")
    parts.append("held on nightly: " + "; ".join(f"{x['label']} ({x['why']})" for x in h["held"]))
    if h["behind"]:
        parts.append(f"passed QA but built after it, so it waits too: {', '.join(h['behind'])}")
    return "QA: " + ". ".join(parts) + "."


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
    if cmd == "pass":
        row = mark(label, True, " ".join(args[1:]), job)
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
    sys.exit(main(sys.argv[1:]))
