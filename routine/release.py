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
                                               dev against nightly and main, and the suggestion: sure or hesitate
  python3 "routine/release.py" nightly "WHY"   hesitating: the privacy check, then dev to nightly only; main stays
  python3 "routine/release.py" main            sure: the privacy check, dev to nightly, then the next small version
                                               the H90 way (Coming next becomes it, VERSION, tag, main, back to dev)
  python3 "routine/release.py" log "LINE"      one line in the H178 row's Releases, newest first

Sure and low risk: tonight's run passed every flow, or what failed was only a test (the fix touched only the flows)
and the rerun is green. Hesitating: a fix in HQ itself, or anything not green after the fix; the next night's run
then tests the fix in full, and a green night releases it. The privacy check is a hard no for both branches.
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

ROOT = HERE.parent
ROW = "H178"
MARK = "Releases:"
KEEP = 14
# What counts as "only a test": the flows and their sets. Everything else is HQ itself. [Claude's choice.]
TESTS = ("app/happy_flows.py", "routine/flowsets.py", "app/test_")


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
    """Sure or hesitate, with why in everyday words. The team still reruns the failed flows before going on."""
    if not run or not tonight:
        return "hesitate", "there was no test run tonight"
    if not run.get("failed") and run.get("passed") == run.get("ran") and run.get("ran"):
        if changed["hq"]:
            return "hesitate", "every test passed, but HQ itself changed after the run started"
        return "sure", f"all {run['ran']} tests passed"
    if changed["hq"]:
        return "hesitate", "a fix in how HQ itself works; the next night's run tests it in full"
    if changed["tests"]:
        return "sure", "only a test was wrong and it's fixed (sure once the rerun is green)"
    return "hesitate", "a test failed and nothing was fixed yet"


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
            "coming_next": coming_next(), "suggest": verdict, "why": why}


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


def _ready(need_clean: tuple[str, ...] = ("CHANGELOG.md", "VERSION")) -> str:
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


def cmd_main(today: dt.date | None = None) -> int:
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
    if not coming_next():
        print("No release: the changelog's Coming next is empty; write what's new for friends first, commit, then again.")
        return 2
    today = today or dt.date.today()
    old_main = out("rev-parse", push.RELEASE_BRANCH)
    v = next_version(version())
    tag = f"v{v}"
    if not git("rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode:
        print(f"No release: the tag {tag} is already here.")
        return 2
    log = ROOT / "CHANGELOG.md"
    text = log.read_text(encoding="utf8")
    log.write_text(text.replace("## Coming next\n", f"## Coming next\n\n## {v} · {today.day} {today:%B %Y}\n", 1), encoding="utf8")
    (ROOT / "VERSION").write_text(v + "\n")
    msg = (f"HQ {v}: the changelog's Coming next becomes {v} ({today.day} {today:%B %Y}), VERSION {v} "
           f"(H186, the nightly line)\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    steps = [("add", "CHANGELOG.md", "VERSION"), ("commit", "-q", "-m", msg),
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


def _undo(old_main: str, tag: str, committed: bool) -> int:
    git("checkout", "-q", push.WORK_BRANCH)
    git("tag", "-d", tag)
    git("branch", "-f", push.RELEASE_BRANCH, old_main)
    if committed:
        git("reset", "-q", "--keep", "HEAD~1")
    else:
        git("checkout", "-q", "--", "CHANGELOG.md", "VERSION")
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
        lines.append(f"Tonight's run ({run.get('at')}): {run.get('passed')} of {run.get('ran')} passed"
                     + (f"; failed: {'; '.join(run.get('failed') or [])}" if run.get("failed") else ""))
    else:
        lines.append("No test run from tonight" + (f" (the last was {run.get('at')})" if run else ""))
    c = s["changed"]
    lines.append(f"Changed since the run started: tests {', '.join(c['tests']) or 'none'}; HQ itself {', '.join(c['hq']) or 'none'}")
    lines.append(f"dev is {s['dev_ahead_of_main']} ahead of main and {s['dev_ahead_of_nightly']} ahead of nightly; "
                 f"Coming next has {len(s['coming_next'])} lines")
    lines.append(f"Suggestion: {s['suggest']} ({s['why']})")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "status":
        s = status()
        print(json.dumps(s, indent=1) if "--json" in argv else words(s))
        return 0
    if cmd == "nightly" and len(argv) >= 2:
        return cmd_nightly(" ".join(argv[1:]))
    if cmd == "main":
        return cmd_main()
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
