#!/usr/bin/env python3
"""The nightly line (H186, 17 October 2026): every night the team decides itself whether the night's work is safe
to release.

The user on the call of 17 October 2026 at 10:42, after a release held back by one test that only broke at night:
"i dont want stupid things like this to block a release", "why cant we have the team be autonomous enough, to find
the bug, clean it, and then decide if this was low risk enough to still release?" and "maybe they can push to another
branch like nightly releases and if they hesitate they still finish and push to there but not to main. if everything
goes well they push always first to nightly and then to main as well".

Three branches: dev (the work), nightly (the night's work, every night), main (a released version, with its tag).
Friends' update bars only look at main's version tags (update.py remote_tags), so nightly never reaches them.
The daily release (H178, a repeating planned item at 2:05) runs after the nightly run or the Sunday sweep:

  python3 "routine/release.py" status          tonight's run, what changed since it started (tests or HQ itself),
                                               dev against nightly and main, and the suggestion: sure, again or hesitate
  python3 "routine/release.py" nightly "WHY"   hesitating: the privacy check, then dev to nightly only; main stays
  python3 "routine/release.py" main            sure: the privacy check, dev to nightly, then the next small version
                                               the H90 way (Coming next becomes it, VERSION, tag, main, back to dev);
                                               only the work whose row says QA passed (F56, qa.py): from the first
                                               commit for a row without it, the rest stays on dev and nightly;
                                               --without-qa only on his explicit say-so on a call
  python3 "routine/release.py" log "LINE"      one line in the H178 row's Releases, newest first

The night works in rounds (H226, 22 October 2026): round 1 is the full run; not green, everything it found is fixed and
the full run goes again (nightly.py again), at most three full runs. Sure: the latest round passed every flow, after
round 1, 2 or 3, also when a fix was in HQ itself (the green full run tested it). Again: not green and a round left.
Hesitating: still not green after the third full run, or no run tonight; the next night tests it again. The privacy check is a hard no for both branches.
A release also sets GitHub's About to the new version (H197, routine/about.py, through push.py).
Only the main computer releases. Exits 0 when done, 1 on a privacy hit (nothing pushed), 2 when git refused or a
check doesn't hold (nothing forced).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import push  # noqa: E402
import qa  # noqa: E402  F56: the release only takes work that passed QA

ROOT = HERE.parent
ROW = "H178"
MARK = "Releases:"
KEEP = 14
# What counts as "only a test": the flows and their sets. Everything else is HQ itself. [Claude's choice.]
# H227: the night's tutorial read comes after the green run; a change to the tutorial's text alone is checked by
# flows 120 and 134 that same night, so it counts like a test change, not as HQ changing after the run. [Claude's choice]
TESTS = ("app/happy_flows.py", "routine/flowsets.py", "app/test_", "app/web/tour.json")


def git(*args: str) -> subprocess.CompletedProcess:
    push.ROOT = ROOT
    return subprocess.run(["git", "-C", str(ROOT), *args], text=True, capture_output=True)


def out(*args: str) -> str:
    return git(*args).stdout.strip()


def is_main() -> bool:
    try:
        import nightly
        return nightly.is_main()
    except Exception:
        return True


def last_run() -> dict | None:
    try:
        return json.load(open(ROOT / "scratch" / "nightly" / "last.json", encoding="utf8"))
    except Exception:
        return None


def ahead(a: str, b: str) -> int:
    """How many commits a has that b hasn't (0 when b doesn't exist here)."""
    if git("rev-parse", "-q", "--verify", b).returncode:
        return int(out("rev-list", "--count", a) or 0)
    return int(out("rev-list", "--count", f"{b}..{a}") or 0)


def changed_since(at: str | None) -> dict:
    """The files dev changed after tonight's run started (the night's fixes), split into tests and HQ itself."""
    if not at:
        return {"tests": [], "hq": []}
    files = out("log", f"--since={at}", "--name-only", "--format=", push.RELEASE_BRANCH + ".." + push.WORK_BRANCH)
    files = sorted({f for f in files.splitlines() if f.strip()})
    tests = [f for f in files if f.startswith(TESTS)]
    return {"tests": tests, "hq": [f for f in files if f not in tests]}


def suggest(run: dict | None, changed: dict, tonight: bool) -> tuple[str, str]:
    """Sure, again or hesitate, with why in everyday words (H226: the night works in rounds of full runs).

    run is last.json: the latest round of tonight (its own ran, passed, failed), with "round" and "rounds_max".
    changed is what dev changed after that round started. Green after any round is sure, also when the round before
    needed a fix in HQ itself: the green full run tested it. Not green with a round left: again (fix everything it
    found, then nightly.py again). Not green after the last round: hesitate (hold on nightly)."""
    if not run or not tonight:
        return "hesitate", "there was no test run tonight"
    n, most = int(run.get("round") or 1), int(run.get("rounds_max") or 3)
    after = f" in round {n}" if n > 1 else ""
    if not run.get("failed") and run.get("passed") == run.get("ran") and run.get("ran"):
        if changed["hq"]:
            return "hesitate", "every test passed, but HQ itself changed after that full run"
        return "sure", f"all {run['ran']} tests passed{after}"
    if n < most:
        return "again", (f"round {n} found {len(run.get('failed') or []) or 'a'} failure(s): fix everything it found, "
                         f"then a full run again (nightly.py again, round {n + 1} of {most})")
    return "hesitate", f"still not green after {n} full runs tonight; the next night tests it again"


def status() -> dict:
    run = last_run()
    today = dt.date.today()
    tonight = bool(run) and run.get("at", "")[:10] == today.isoformat()
    changed = changed_since(run.get("at") if tonight else None)
    verdict, why = suggest(run, changed, tonight)
    return {"main_computer": is_main(), "branch": out("branch", "--show-current"), "version": version(),
            "run": run, "tonight": tonight, "changed": changed,
            "dev_ahead_of_main": ahead(push.WORK_BRANCH, push.RELEASE_BRANCH),
            "dev_ahead_of_nightly": ahead(push.WORK_BRANCH, push.NIGHTLY_BRANCH),
            "coming_next": coming_next(), "suggest": verdict, "why": why, "qa": qa_hold()}


def qa_hold() -> dict:
    """F56: what the release would take and hold, by QA (qa.hold); empty when it can't be read."""
    try:
        return qa.hold(str(ROOT), push.RELEASE_BRANCH, push.WORK_BRANCH)
    except Exception as e:
        return {"to": None, "tip": None, "taken": [], "held": [], "behind": [], "all": False, "error": repr(e)}


def version() -> str:
    try:
        return (ROOT / "VERSION").read_text().strip()
    except Exception:
        return "0.0.0"


def next_version(v: str) -> str:
    parts = [int(x) for x in re.findall(r"\d+", v)] or [0]
    while len(parts) < 3:
        parts.append(0)
    parts[-1] += 1
    return ".".join(str(p) for p in parts)


def coming_next() -> list[str]:
    """The lines under the changelog's Coming next, up to the first version heading."""
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf8")
    m = re.search(r"^## Coming next\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return [ln for ln in (m.group(1) if m else "").splitlines() if ln.strip().startswith("-")]


def _ready(need_clean: tuple[str, ...] = ("CHANGELOG.md", "VERSION", "README.md")) -> str:
    """Why the night's push can't go now, or ''."""
    if not is_main():
        return "this computer isn't the main right now; the main releases"
    branch = out("branch", "--show-current")
    if branch != push.WORK_BRANCH:
        return f"HQ is on {branch or 'no branch'}, not {push.WORK_BRANCH}"
    dirty = out("status", "--porcelain", "--", *need_clean) if need_clean else ""
    if dirty:
        return f"these have changes that aren't committed: {dirty}"
    return ""


def to_nightly() -> int:
    """The privacy check, then dev to GitHub and dev to nightly."""
    if not push.privacy_ok():
        return 1
    r = push.push_branch(push.WORK_BRANCH)
    return r or push.push_nightly(push.WORK_BRANCH, [])


def cmd_nightly(why: str) -> int:
    no = _ready(())
    if no:
        print(f"Nothing pushed: {no}.")
        return 0 if "isn't the main" in no else 2
    r = to_nightly()
    if r:
        return r
    print(f"Held back from main: {why}. The night's work is on {push.NIGHTLY_BRANCH}; main stays at {version()}. "
          f"To put it out anyway: release.py main (his say-so on a call).")
    return 0


def cmd_main(today: dt.date | None = None, without_qa: bool = False) -> int:
    no = _ready()
    if no:
        print(f"No release: {no}.")
        return 0 if "isn't the main" in no else 2
    r = to_nightly()  # always first to nightly
    if r:
        return r
    if not ahead(push.WORK_BRANCH, push.RELEASE_BRANCH):
        print(f"No release: nothing new on {push.WORK_BRANCH} since {version()}.")
        return 0
    if not without_qa:  # F56: only work whose row says QA passed goes out
        h = qa.hold(str(ROOT), push.RELEASE_BRANCH, push.WORK_BRANCH)
        if not h["all"]:
            print(qa.hold_words(h))
            if h["held"]:  # H266: Moneypenny tells him on her own line what's held and why
                qa.tell("release-held", "Held back, not passed my check yet: " + "; ".join(
                    f"{qa.title_of(x['label']) or x['label']} ({x['why']})" for x in h["held"])
                    + (". Goes out now: " + ", ".join(qa.title_of(l) or l for l in h["taken"]) if h["to"] else
                       ". Nothing new goes out this time."))
            if not h["to"]:
                print(f"No release: nothing new has passed QA yet; it stays on {push.NIGHTLY_BRANCH}, main stays at {version()}.")
                return 0
            return cmd_part(h, today)
    if not coming_next():
        print("No release: the changelog's Coming next is empty; write what's new for friends first, commit, then again.")
        return 2
    today = today or dt.date.today()
    old_main = out("rev-parse", push.RELEASE_BRANCH)
    old = version()
    v = next_version(old)
    tag = f"v{v}"
    if not git("rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode:
        print(f"No release: the tag {tag} is already here.")
        return 2
    log = ROOT / "CHANGELOG.md"
    text = log.read_text(encoding="utf8")
    log.write_text(text.replace("## Coming next\n", f"## Coming next\n\n## {v} · {today.day} {today:%B %Y}\n", 1), encoding="utf8")
    (ROOT / "VERSION").write_text(v + "\n")
    files = ["CHANGELOG.md", "VERSION"]
    readme = ROOT / "README.md"  # its "HQ is at version **X**" line moves along (H209)
    if readme.exists():
        files.append("README.md")
        readme.write_text(readme.read_text(encoding="utf8").replace(f"**{old}**", f"**{v}**", 1), encoding="utf8")
    msg = (f"HQ {v}: the changelog's Coming next becomes {v} ({today.day} {today:%B %Y}), VERSION {v}, the README's version "
           f"(H186, the nightly line)\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    steps = [("add", *files), ("commit", "-q", "-m", msg),
             ("checkout", "-q", push.RELEASE_BRANCH), ("merge", "-q", "--ff-only", push.WORK_BRANCH),
             ("tag", "-a", tag, "-m", f"HQ {v}")]
    for s in steps:
        g = git(*s)
        if g.returncode:
            print(f"No release: git {s[0]} failed: {(g.stdout + g.stderr).strip()}")
            return _undo(old_main, tag, committed=s[0] not in ("add", "commit"))
    r = push.push_branch(push.RELEASE_BRANCH, release=True)
    git("checkout", "-q", push.WORK_BRANCH)
    if r:
        print("No release: GitHub refused main or the tags; put back as it was.")
        return _undo(old_main, tag, committed=True) or r
    r = push.push_branch(push.WORK_BRANCH) or push.push_nightly(push.WORK_BRANCH, [])
    print(f"Released {v} ({tag}) on {push.RELEASE_BRANCH}; {push.NIGHTLY_BRANCH} and {push.WORK_BRANCH} have it too.")
    return r


def _coming(text: str) -> list[str]:
    m = re.search(r"^## Coming next\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return [ln for ln in (m.group(1) if m else "").splitlines() if ln.strip().startswith("-")]


def _versioned(text: str, v: str, today: dt.date, lines: list[str]) -> str:
    """The changelog with the given lines out of Coming next and under a new version heading; the rest stays."""
    m = re.search(r"^## Coming next\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    keep = [ln for ln in _coming(text) if ln not in lines]
    body = "".join(f"\n{ln}\n" for ln in keep)
    new = f"## Coming next\n{body}\n## {v} · {today.day} {today:%B %Y}\n\n" + "\n".join(lines) + "\n\n"
    return text[:m.start()] + new + text[m.end():].lstrip("\n")


def cmd_part(h: dict, today: dt.date | None = None) -> int:
    """F56: release only up to the last commit before the first one whose row hasn't passed QA (h["to"]). The version
    commit goes on top of that commit, in a worktree of its own; main and the tag go there; dev gets it merged back
    (its tree kept, the released lines moved under the version), so main stays an ancestor of dev."""
    today = today or dt.date.today()
    to = h["to"]
    at_to = out("show", f"{to}:CHANGELOG.md")
    lines = _coming(at_to)
    if not lines:
        print("No release: the work that passed QA has nothing in the changelog's Coming next; it stays on "
              f"{push.NIGHTLY_BRANCH}, main stays at {version()}.")
        return 0
    old_main, old_dev = out("rev-parse", push.RELEASE_BRANCH), out("rev-parse", push.WORK_BRANCH)
    old = version()
    v = next_version(old)
    tag = f"v{v}"
    if not git("rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode:
        print(f"No release: the tag {tag} is already here.")
        return 2
    import shutil
    import tempfile
    wt = Path(tempfile.mkdtemp(prefix="hq-release-")) / "wt"
    msg = (f"HQ {v}: the changelog's Coming next becomes {v} ({today.day} {today:%B %Y}) for the work that passed QA, "
           f"VERSION {v}, the README's version (H186, F56)\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")

    def back(why: str) -> int:
        print(f"No release: {why}")
        git("merge", "--abort")
        git("checkout", "-q", push.WORK_BRANCH)
        git("reset", "-q", "--keep", old_dev)
        git("tag", "-d", tag)
        git("branch", "-f", push.RELEASE_BRANCH, old_main)
        git("worktree", "remove", "--force", str(wt))
        shutil.rmtree(wt.parent, ignore_errors=True)
        return 2

    if git("worktree", "add", "-q", "--detach", str(wt), to).returncode:
        shutil.rmtree(wt.parent, ignore_errors=True)
        print("No release: git couldn't make a worktree for it.")
        return 2

    def w(*a):
        return subprocess.run(["git", "-C", str(wt), *a], text=True, capture_output=True)
    (wt / "CHANGELOG.md").write_text(_versioned(at_to, v, today, lines), encoding="utf8")
    (wt / "VERSION").write_text(v + "\n")
    files = ["CHANGELOG.md", "VERSION"]
    if (wt / "README.md").exists():
        files.append("README.md")
        (wt / "README.md").write_text((wt / "README.md").read_text(encoding="utf8").replace(f"**{old}**", f"**{v}**", 1), encoding="utf8")
    if w("add", *files).returncode or w("commit", "-q", "-m", msg).returncode:
        return back("git couldn't commit the version.")
    rel = w("rev-parse", "HEAD").stdout.strip()
    for step in (("branch", "-f", push.RELEASE_BRANCH, rel), ("tag", "-a", tag, "-m", f"HQ {v}", rel)):
        if git(*step).returncode:
            return back(f"git {step[0]} failed.")
    # dev: merge the release in, keeping dev's own tree, then the same version change on dev's changelog.
    if git("merge", "-q", "--no-ff", "--no-commit", "-s", "ours", rel).returncode:
        return back("git couldn't merge the release back into dev.")
    log = ROOT / "CHANGELOG.md"
    log.write_text(_versioned(log.read_text(encoding="utf8"), v, today, lines), encoding="utf8")
    (ROOT / "VERSION").write_text(v + "\n")
    readme = ROOT / "README.md"
    if readme.exists():
        readme.write_text(readme.read_text(encoding="utf8").replace(f"**{old}**", f"**{v}**", 1), encoding="utf8")
    if git("add", *files).returncode or git("commit", "-q", "-m", f"HQ {v} back into dev: what's held stays under "
                                             f"Coming next (F56)\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>").returncode:
        return back("git couldn't commit the merge on dev.")
    git("worktree", "remove", "--force", str(wt))
    shutil.rmtree(wt.parent, ignore_errors=True)
    r = push.push_branch(push.RELEASE_BRANCH, release=True)
    if r:
        print("No release: GitHub refused main or the tags; put back as it was.")
        git("reset", "-q", "--keep", old_dev)
        git("tag", "-d", tag)
        git("branch", "-f", push.RELEASE_BRANCH, old_main)
        return 2
    r = push.push_branch(push.WORK_BRANCH) or push.push_nightly(push.WORK_BRANCH, [])
    print(f"Released {v} ({tag}) on {push.RELEASE_BRANCH}, with the work that passed QA; what's held stays on "
          f"{push.WORK_BRANCH} and {push.NIGHTLY_BRANCH}.")
    return r


def _undo(old_main: str, tag: str, committed: bool) -> int:
    git("checkout", "-q", push.WORK_BRANCH)
    git("tag", "-d", tag)
    git("branch", "-f", push.RELEASE_BRANCH, old_main)
    if committed:
        git("reset", "-q", "--keep", "HEAD~1")
    else:
        git("checkout", "-q", "--", *[f for f in ("CHANGELOG.md", "VERSION", "README.md") if (ROOT / f).exists()])
    return 2


def add_line(line: str, roadmap: str | None = None) -> bool:
    """One line in the H178 row's Releases, newest first, the last KEEP kept. False when there's no row."""
    import hqpaths
    import jobs
    path = roadmap or hqpaths.ROADMAP
    line = " ".join(line.replace("|", "/").split())
    with jobs.locked():
        text = open(path, encoding="utf8").read()
        m = re.search(rf"^\| [^|\n]* \| {ROW} [^\n]*\|\s*$", text, re.M)
        if not m:
            return False
        row = m.group(0).rstrip()
        cells = row[1:-1].split(" | ")
        before, _, rel = cells[-1].strip().partition(MARK)
        old = [n.strip() for n in re.split(r"(?<=\.) (?=\d{1,2} \w+ 20\d\d)", rel.strip()) if n.strip()]
        new = " ".join([line if line.endswith(".") else line + "."] + old[:KEEP - 1])
        cells[-1] = f" {(before.strip() + ' ') if before.strip() else ''}{MARK} {new} "
        row2 = "| " + " | ".join(c.strip() for c in cells) + " |"
        hqpaths.guard_roadmap(path)  # F17
        tmp = path + ".tmp"
        open(tmp, "w", encoding="utf8").write(text[:m.start()] + row2 + text[m.start() + len(row):])
        os.replace(tmp, path)
    return True


def words(s: dict) -> str:
    run = s["run"]
    lines = [f"Main computer: {'yes' if s['main_computer'] else 'no'} · on {s['branch']} · version {s['version']}"]
    if run and s["tonight"]:
        lines.append(f"Tonight's run, round {run.get('round') or 1} of at most {run.get('rounds_max') or 3} "
                     f"({run.get('at')}): {run.get('passed')} of {run.get('ran')} passed"
                     + (f"; failed: {'; '.join(run.get('failed') or [])}" if run.get("failed") else ""))
    else:
        lines.append("No test run from tonight" + (f" (the last was {run.get('at')})" if run else ""))
    c = s["changed"]
    lines.append(f"Changed since the run started: tests {', '.join(c['tests']) or 'none'}; HQ itself {', '.join(c['hq']) or 'none'}")
    lines.append(f"dev is {s['dev_ahead_of_main']} ahead of main and {s['dev_ahead_of_nightly']} ahead of nightly; "
                 f"Coming next has {len(s['coming_next'])} lines")
    lines.append(f"Suggestion: {s['suggest']} ({s['why']})")
    h = s.get("qa") or {}
    lines.append(f"QA cannot be read: {h['error']}" if h.get("error") else qa.hold_words(h))
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "status":
        s = status()
        print(json.dumps(s, indent=1) if "--json" in argv else words(s))
        return 0
    if cmd in ("nightly", "main") and push.notes_waiting():  # H283: the running job reads its notes first
        return 3
    if cmd == "nightly" and len(argv) >= 2:
        return cmd_nightly(" ".join(argv[1:]))
    if cmd == "main":
        # F56: --without-qa only on his explicit say-so on a call; it releases everything on dev.
        return cmd_main(without_qa="--without-qa" in argv)
    if cmd == "log" and len(argv) >= 2:
        if not add_line(" ".join(argv[1:])):
            print(f"No {ROW} row on the roadmap.")
            return 1
        print("Written.")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
