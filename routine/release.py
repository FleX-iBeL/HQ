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
The daily release (H178, a repeating planned item at 5:05) runs after the nightly run or the Monday sweep:

  python3 "routine/release.py" status          tonight's run, what changed since it started (tests or HQ itself),
                                               dev against nightly and main, and the suggestion: sure, again or hesitate
  python3 "routine/release.py" nightly "WHY"   hesitating: the privacy check, then dev to nightly only; main stays
  python3 "routine/release.py" main [--without-qa] [--past-the-night] [--said "HIS WORDS"] [--version 1.0.0]
                                               sure: the privacy check, dev to nightly, then the next small version.
                                               F101: refused after a red or missing night and for a commit naming no item;
                                               Moneypenny decides when, inside those gates; past them only on his own words
                                               the H90 way (Coming next becomes it, VERSION, tag, main, back to dev);
                                               only the work whose row says QA passed (F56, qa.py): from the first
                                               commit for a row without it, the rest stays on dev and nightly;
                                               --without-qa only on his explicit say-so on a call. F112: --version names the
                                               version instead of the next small one. A second run on the same commit and the
                                               same QA state does nothing and says so
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
import hqpaths  # noqa: E402
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


def changed_since(at: str | None, commit: str | None = None) -> dict:
    """The files dev changed after tonight's run started (the night's fixes), split into tests and HQ itself. F112: from the commit the night
    ran on when its record names it, with the same free files as the gate; the clock is only for a record that doesn't."""
    if not at:
        return {"tests": [], "hq": []}
    free = TESTS + qa.FREE_FILES  # the same as the gate's
    if commit and not git("cat-file", "-e", f"{commit}^{{commit}}").returncode:
        files = out("diff", "--name-only", commit, push.WORK_BRANCH)
    else:
        files = out("log", f"--since={at}", "--name-only", "--format=", push.RELEASE_BRANCH + ".." + push.WORK_BRANCH)
    files = sorted({f for f in files.splitlines() if f.strip()})
    tests = [f for f in files if f.startswith(free)]
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
        if run.get("items"):  # H324: the failures are in the rotation; the routine starts the next full run itself
            return "again", (f"round {n} found {len(run.get('failed') or []) or 'a'} failure(s), each on the planning for the whole rotation; "
                             f"the routine starts round {n + 1} of {most} once each passed her check, and the release waits for it")
        return "again", (f"round {n} found {len(run.get('failed') or []) or 'a'} failure(s): fix everything it found, "
                         f"then a full run again (nightly.py again, round {n + 1} of {most})")
    return "hesitate", f"still not green after {n} full runs tonight; the next night tests it again"


def status() -> dict:
    run = last_run()
    today = dt.date.today()
    tonight = bool(run) and run.get("at", "")[:10] == today.isoformat()
    changed = changed_since(run.get("at") if tonight else None, run.get("commit") if tonight else None)
    verdict, why = suggest(run, changed, tonight)
    h = qa_hold()
    refused = night_refuses(_target(h))  # F112: the advice can't say sure where the gate says no
    if refused and verdict == "sure":
        verdict, why = "hesitate", refused
    return {"main_computer": is_main(), "branch": out("branch", "--show-current"), "version": version(),
            "run": run, "tonight": tonight, "changed": changed,
            "dev_ahead_of_main": ahead(push.WORK_BRANCH, push.RELEASE_BRANCH),
            "dev_ahead_of_nightly": ahead(push.WORK_BRANCH, push.NIGHTLY_BRANCH),
            "coming_next": coming_next(), "suggest": verdict, "why": why, "qa": h, "night_refuses": refused}


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


def released() -> str:
    """H320: the version main is at. VERSION, unless a build set it ahead for the release it waits on (the newest version tag
    is older and VERSION has no tag of its own): then that tag's version."""
    v = version()
    if not git("rev-parse", "-q", "--verify", f"refs/tags/v{v}").returncode:
        return v
    tag = out("describe", "--tags", "--abbrev=0", "--match", "v[0-9]*", push.WORK_BRANCH)
    nums = lambda x: tuple(int(n) for n in re.findall(r"\d+", x)[:3])
    return tag[1:] if tag and nums(tag) and nums(tag) < nums(v) else v


def release_version(want: str | None) -> tuple[str, str]:
    """(old, new): the version main is at and the one this release makes: the named one, else a VERSION set ahead by a
    build (H320: "1.0.2 tonight"), else the next patch."""
    old = released()
    return old, want or (version() if version() != old else next_version(old))


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
    if not ahead(push.WORK_BRANCH, push.NIGHTLY_BRANCH):  # F112: a second run does nothing, and says so
        print(f"Nothing to do: {push.WORK_BRANCH} is already on {push.NIGHTLY_BRANCH}; main stays at {released()}.")
        return 0
    r = to_nightly()
    if r:
        return r
    print(f"Held back from main: {why}. The night's work is on {push.NIGHTLY_BRANCH}; main stays at {released()}. "
          f"To put it out anyway: release.py main (his say-so on a call).")
    return 0


def night_refuses(target: str | None = None) -> str | None:
    """F101 (C43, C73): what the night says against a release of target (HEAD by default), or None. A program reads it; suggest() is only
    advice. F112: a run still going isn't a night yet, and a green night counts for the commit it ran on (night_tied)."""
    import nightly
    import proof
    if not proof.gate_on():
        return None
    going = nightly.running()
    if going:
        return f"the night's test run is still going, since {going.get('at')}; the release reads what it says"
    run = last_run()
    if not run or run.get("at", "")[:10] != dt.date.today().isoformat():
        at = (run or {}).get("at")
        return "there was no test run tonight" + (f" (the last one was {at})" if at else "")
    if run.get("failed") or not run.get("ran") or run.get("passed") != run.get("ran"):
        return (f"the night of {run.get('at')} was red: {run.get('passed')} of {run.get('ran')} passed"
                + (f"; failed: {'; '.join(run.get('failed') or [])[:300]}" if run.get("failed") else ""))
    try:  # 11 November 2026: the 17 happy flows run only at night (every night, or once a week); the last run of them has to be green
        import wholebuild
        if wholebuild.on() and nightly.happy_at_night():
            lh = nightly.last_happy()
            if not lh:
                return ("the release waits for the first night run of the 17 happy flows: since the whole-build road is on they run only "
                        "at night (routine/nightly.py), and they haven't run yet; the next night runs them")
            if not lh.get("green"):
                return f"the last night run of the 17 happy flows ({lh.get('at')}) was red: {'; '.join((lh.get('failed') or []) + (lh.get('not_tried') or []))[:300]}"
    except ImportError:
        pass
    return night_tied(run, target or "HEAD")


def night_tied(run: dict, target: str) -> str | None:
    """F112 (C73): a green night says something about the commit it ran on and nothing else. The record has to name it, it has to be a whole
    night, and a release of a newer commit is refused unless only the free files changed since."""
    import nightly
    at, commit = run.get("at"), run.get("commit")
    if not commit:
        return f"the night of {at} names no commit, so it doesn't say what it tested"
    if git("cat-file", "-e", f"{commit}^{{commit}}").returncode:
        return f"the night of {at} ran on {commit[:7]}, which isn't in this repo"
    whole = nightly.whole_set(commit, str(ROOT))
    if not whole:
        return f"how many flows a whole night is at {commit[:7]} can't be read"
    if int(run.get("ran") or 0) < whole:
        return f"the night of {at} ran {run.get('ran')} flows and a whole night is {whole}: that isn't a night"
    dirty = [f for f in run.get("dirty") or [] if not f.startswith(TESTS + qa.FREE_FILES)]
    if dirty:
        return f"the night of {at} ran with changes that weren't committed: {', '.join(dirty[:6])}"
    if not git("merge-base", "--is-ancestor", target, commit).returncode:
        return None
    changed = [f for f in out("diff", "--name-only", commit, target).splitlines() if f and not f.startswith(TESTS + qa.FREE_FILES)]
    if changed:
        return (f"the night ran on {commit[:7]} and this is newer: {len(changed)} file(s) of HQ changed since, {', '.join(changed[:6])}"
                f"{' and more' if len(changed) > 6 else ''}")
    return None


def _target(h: dict) -> str | None:
    """What a release would put out: the last commit the hold takes when it doesn't take everything, else dev's tip."""
    return h["to"] if h.get("to") and not h.get("all") else None


LAST = "release-last.json"  # F112: what the release last did, so a second run on the same commit does nothing


def _state() -> dict:
    """What decides what a release does: dev, main and what the hold says."""
    h = qa.hold(str(ROOT), push.RELEASE_BRANCH, push.WORK_BRANCH)
    return {"dev": out("rev-parse", push.WORK_BRANCH), "main": out("rev-parse", push.RELEASE_BRANCH), "to": h.get("to"),
            "held": sorted(x["label"] for x in h["held"])}


def _keep(said: str) -> None:
    folder = ROOT / "scratch" / "nightly"
    folder.mkdir(parents=True, exist_ok=True)
    json.dump({"state": _state(), "said": said, "at": dt.datetime.now().strftime("%Y-%m-%d %H:%M")}, open(folder / LAST, "w"), indent=1)


def _done_before() -> dict | None:
    try:
        d = json.load(open(ROOT / "scratch" / "nightly" / LAST, encoding="utf8"))
    except (OSError, ValueError):
        return None
    return d if d.get("state") == _state() else None


def wanted_refuses(want: str | None, old: str) -> str | None:
    """F112: a named version has to be a version, and newer than this one."""
    if want is None:
        return None
    parts = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", want)
    if not parts:
        return f"{want} isn't a version like 1.0.0"
    if tuple(int(x) for x in parts.groups()) <= tuple((int(x) for x in re.findall(r"\d+", old)[:3])):
        return f"{want} isn't newer than {old}"
    if not git("rev-parse", "-q", "--verify", f"refs/tags/v{want}").returncode:
        return f"the tag v{want} is already here"  # F167: said before anything else, the changelog's Coming next included
    return None


WAY_BACK = "routine/way-back.json"


def way_back_file(folder: Path, old: str, at: str = push.WORK_BRANCH) -> list[str]:
    """F112 (C52): the version before this release may be one whose own update.py has no `forward`. Going back to it still has to work: the
    release writes that down, in the release itself, and update.py reads it: forward from there is the update bar, the way that version
    came forward the first time. The files to commit along."""
    tag = f"v{old}"
    r = git("show", f"refs/tags/{tag}:routine/update.py")
    if r.returncode or re.search(r"^def forward\(", r.stdout, re.M):
        return []
    if "way-back.json" not in git("show", f"{at}:routine/update.py").stdout:
        return []  # the version this goes into can't read it: going back from there stays refused, as that version's own code says
    path = folder / WAY_BACK
    try:
        d = json.load(open(path, encoding="utf8"))
    except (OSError, ValueError):
        d = {}
    if tag not in d:
        d[tag] = "the update bar"
        path.write_text(json.dumps(d, indent=1) + "\n", encoding="utf8")
    return [WAY_BACK]


def tag_words(v: str, h: dict | None) -> str:
    """F112: the version's own words: what went out from before the gate stands on the tag, so a release can't leave it unsaid."""
    before = qa.before_words(h, going=True) if h else ""
    return f"HQ {v}" + (f"\n\n{before}" if before else "")


def plan_not_yet(said: str | None, what: str) -> str | None:
    """F166: his words that plan a release for a later moment are his say-so once that moment has come, never before and never past the
    night: for after the night run, a green night (night_refuses says nothing) that ran after he said it; for tomorrow, a later day. Why not
    yet, or None (also when the words plan nothing)."""
    import sprint as S
    plans = S.planned_lines(said)
    if not plans:
        return None
    if "night" in what:
        return "planned words wait for a green night and never go past it"
    p = plans[-1]
    at = dt.datetime.fromtimestamp(p["at"] or 0)
    if p["moment"] == "night":
        no = night_refuses()
        if no:
            return f"they plan it for after the night run, and {no}"
        run_at = (last_run() or {}).get("at") or ""
        if run_at[:16] <= at.strftime("%Y-%m-%dT%H:%M"):
            return f"they plan it for after the night run, and the last run ({run_at}) was before he said it ({at:%d %B %H:%M})"
        return None
    if dt.date.today() <= at.date():
        return f"they plan it for tomorrow, and he said it today ({at:%d %B %H:%M})"
    return None


# F167: his plain order to release ("Release 1.0.2 now, with everything on dev, past the QA gate.", "Yes, release 1.0.2 now") is his yes, read
# by the program, so one small look's mood can't turn it down: a sentence that starts with release (after a yes word at the most) and names the
# version. Past the QA check only: past a red night it takes his words naming the night, as before. A question or a hold in a sentence about the
# release is a no, read by the program too; anything it can't tell goes on to the reading of his yes and the look, as before.
_VERSION = re.compile(r"(?<![\w.])v?\d+\.\d+(?:\.\d+)?(?![\w.])")
_RELEASE = re.compile(r"(?<![\w'])release(?![\w'])")
_NIGHT_NAMED = re.compile(r"(?<![\w'])(?:past the (?:red )?night|red night)(?![\w'])")
QA_NAMES = ("without qa", "skip qa", "skipping qa", "past qa", "past the qa gate", "past the qa check", "without the qa check",
            "without the qa gate", "without a qa check", "skip the qa check", "with everything on dev")
NIGHT_NAMES = ("past the night", "red night")


def order_reading(line: str, turn: str, what: str) -> str:
    """F167: "yes" for his plain order to release, "no" for a question or a hold about it, "" when it isn't plain (see above)."""
    import sprint as S
    low = " ".join(str(line).lower().replace("\u2019", "'").split())
    if S.planned_release(low):
        return ""  # F166: a planned release is read there, and counts once its moment has come
    sents = [x for x in re.split(r"(?<=[.!?])\s+", low) if x]
    rel = [x for x in sents if _RELEASE.search(x) and _VERSION.search(x)]
    if not rel:
        return ""
    if S._TAKEN_BACK.search(low) or any("?" in x or S._HOLD_WORD.search(x) for x in rel):
        return "no"
    order = re.compile(rf"^(?:(?:{S._YES_FIRM}|please)[,!]?\s+)*release\s+(?:of\s+)?v?\d")
    if not any(order.match(x) for x in rel) or any(S._NOT_SURE.search(x) or S._HOLD_WORD.search(x) for x in sents):
        return ""
    if "night" in what and not _NIGHT_NAMED.search(low):
        return "yes" if S.yes_reading(line, turn, NIGHT_NAMES) == "yes" else "no"  # the plain order is his yes past the QA check only
    return "yes"


def say_so(said: str | None, what: str) -> bool:
    """F101: going past a gate takes his own words, found in his lines and kept; a flag alone is nothing."""
    import sprint as S
    names = QA_NAMES if "QA" in what else NIGHT_NAMES
    no = plan_not_yet(said, what)
    if no:
        print(f"No release: {what} needs his say-so, and his planned words are no say-so yet: {no}.")
        return False
    where, no = S.his_yes(said, f"releasing HQ to everyone: {what}", names=names, reading=lambda line, turn: order_reading(line, turn, what))
    if not where:
        if "night" in what and no == S.NOT_A_YES:
            no += " (his plain order to release is his yes past the QA check only; past the night takes his words naming it, past the night or red night)"
        print(f"No release: {what} needs --said with his own words, as they stand in a call, a text or a quick note, saying yes to it: {no}.")
        return False
    S.keep_say_so([f"release: {what}"], " ".join((said or "").split()), where)
    return True


def cmd_main(today: dt.date | None = None, without_qa: bool = False, red_night: bool = False, said: str | None = None, want: str | None = None) -> int:
    no = _ready()
    if no:
        print(f"No release: {no}.")
        return 0 if "isn't the main" in no else 2
    plain = not without_qa and not red_night
    before = _done_before() if plain else None
    if before:  # F112: nothing changed since the last time: nothing pushed, nothing texted
        print(f"Nothing to do: this commit ({out('rev-parse', '--short', push.WORK_BRANCH)}) went through the release on {before['at']}: "
              f"{before['said']} Nothing has changed since, so nothing was pushed or sent.")
        return 0
    if not ahead(push.WORK_BRANCH, push.RELEASE_BRANCH):
        print(f"Nothing to do: nothing new on {push.WORK_BRANCH} since {released()}.")
        return 0
    no = wanted_refuses(want, released())
    if no:
        print(f"No release: {no}.")
        return 2
    h = qa_hold() if without_qa else qa.hold(str(ROOT), push.RELEASE_BRANCH, push.WORK_BRANCH)
    night = night_refuses(None if without_qa else _target(h))
    if night:
        if not red_night:
            print(f"No release: {night}. It stays on {push.NIGHTLY_BRANCH}; main stays at {released()}.")
            return 2
        if not say_so(said, "a release past the night"):
            return 2
    if without_qa and not say_so(said, "a release without QA"):
        return 2
    r = to_nightly()  # always first to nightly
    if r:
        return r
    if not without_qa:  # F56: only work whose row says QA passed goes out
        if not h["all"] and h.get("to"):
            no = data_refuses(push.RELEASE_BRANCH, h["to"])  # F104: on the part that would go out
            if no:
                print(no)
                return 2
        elif h["all"]:
            no = data_refuses(push.RELEASE_BRANCH, push.WORK_BRANCH)
            if no:
                print(no)
                return 2
        if not h["all"]:
            print(qa.hold_words(h))
            if h["held"]:  # H266: Moneypenny tells him on her own line what's held and why
                qa.tell("release-held", "Held back, not passed my check yet: " + "; ".join(
                    f"{qa.title_of(x['label']) or x['label']} ({x['why']})" for x in h["held"])
                    + (". Goes out now: " + ", ".join(qa.title_of(l) or l for l in h["taken"]) if h["to"] or h["taken"] else
                       ". Nothing new goes out this time."))
            if not h["to"] and not h["taken"]:
                print(f"No release: nothing new has passed QA yet; it stays on {push.NIGHTLY_BRANCH}, main stays at {released()}.")
                _keep("nothing new had passed QA, so it stayed on nightly.")
                return 0
            return cmd_part(h, today, want)
    if not coming_next():
        print("No release: the changelog's Coming next is empty; write what's new for friends first, commit, then again.")
        return 2
    if without_qa:
        no = data_refuses(push.RELEASE_BRANCH, push.WORK_BRANCH)  # F104: no say-so goes past a broken undo
        if no:
            print(no)
            return 2
    today = today or dt.date.today()
    old_main = out("rev-parse", push.RELEASE_BRANCH)
    old, v = release_version(want)
    tag = f"v{v}"
    if not git("rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode:
        print(f"No release: the tag {tag} is already here.")
        return 2
    log = ROOT / "CHANGELOG.md"
    text = log.read_text(encoding="utf8")
    log.write_text(text.replace("## Coming next\n", f"## Coming next\n\n## {v} · {today.day} {today:%B %Y}\n" + data_lines(old_main, push.WORK_BRANCH), 1), encoding="utf8")
    (ROOT / "VERSION").write_text(v + "\n")
    files = ["CHANGELOG.md", "VERSION"]
    readme = ROOT / "README.md"  # its "HQ is at version **X**" line moves along (H209)
    if readme.exists():
        files.append("README.md")
        readme.write_text(readme.read_text(encoding="utf8").replace(f"**{old}**", f"**{v}**", 1), encoding="utf8")
    files += way_back_file(ROOT, old)
    msg = (f"HQ {v}: the changelog's Coming next becomes {v} ({today.day} {today:%B %Y}), VERSION {v}, the README's version "
           f"(H186, the nightly line)\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    steps = [("add", *files), ("commit", "-q", "-m", msg),
             ("checkout", "-q", push.RELEASE_BRANCH), ("merge", "-q", "--ff-only", push.WORK_BRANCH),
             ("tag", "-a", tag, "-m", tag_words(v, h))]
    for s in steps:
        g = git(*s)
        if g.returncode:
            print(f"No release: git {s[0]} failed: {(g.stdout + g.stderr).strip()}")
            return _undo(old_main, tag, committed=s[0] not in ("add", "commit"), files=files)
    r = push.push_branch(push.RELEASE_BRANCH, release=True)
    git("checkout", "-q", push.WORK_BRANCH)
    if r:
        print("No release: GitHub refused main or the tags; put back as it was.")
        return _undo(old_main, tag, committed=True, files=files) or r
    r = push.push_branch(push.WORK_BRANCH) or push.push_nightly(push.WORK_BRANCH, [])
    print(f"Released {v} ({tag}) on {push.RELEASE_BRANCH}; {push.NIGHTLY_BRANCH} and {push.WORK_BRANCH} have it too.")
    if qa.before_words(h, going=True):
        print(qa.before_words(h, going=True))
    on_the_record(old_main, tag, v)
    _keep(f"{v} went out.")
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


RELEASE_FILES = ("CHANGELOG.md", "VERSION", "README.md", WAY_BACK)


def _picks(h: dict, old_main: str, start: str) -> list[tuple[str, str]]:
    """F152: what a partial release brings onto start (main, or h["to"] when main is under it), oldest first: (sha, row) for every
    commit up to h["to"] and every own commit of a row that passed QA (taken), that isn't there yet: not behind it, not brought in
    before (its mark), not the same change. Never a commit a held row names too, never a merge (what it brought is picked on its own).
    A row behind a held one waits, as the hold says."""
    rows = h.get("commits") or {}
    held = {s for x in h["held"] for s in rows.get(x["label"], []) + ([x["sha"]] if x.get("sha") else [])}
    want = {}
    if h.get("to"):
        for sha in out("rev-list", "--no-merges", h["to"], f"^{old_main}").split():
            want[sha] = next((l for l, ss in rows.items() if sha in ss), "")
    for label in h["taken"]:
        for sha in rows.get(label, []):
            want.setdefault(out("rev-parse", sha), label)
    on_main = _on_main(old_main)
    new = set(out("rev-list", "--no-merges", push.WORK_BRANCH, f"^{start}").split())
    order = out("rev-list", "--reverse", "--topo-order", push.WORK_BRANCH, f"^{old_main}").split()
    return [(sha, want[sha]) for sha in order if sha in want and sha in new and sha not in on_main
            and not any(sha.startswith(x) or x.startswith(sha) for x in held)]


def _on_main(old_main: str) -> set[str]:
    """The commits of dev whose change is on main already: brought in before (their mark) or the same change."""
    marked = set(re.findall(r"\(cherry picked from commit ([0-9a-f]{40})\)", out("log", "--format=%B", old_main)))
    return marked | {ln[2:] for ln in out("cherry", old_main, push.WORK_BRANCH).splitlines() if ln.startswith("- ")}


def _settled(sha: str, files: list[str], old_main: str, fine: set[str]) -> str | None:
    """F152 (QA, 5 November): a picked commit that clashes with work already on main, where dev already holds the settled version:
    the first commit on dev after sha whose files have all of main's changes to them and, beyond main, only changes of commits that
    go out (fine: on main already, or picked for a row not held). Its files are then the settled version; None when nothing on dev settles it that way."""
    marks = {}
    for entry in out("log", "--format=%H%x00%B%x01", old_main).split("\x01"):
        c, _, body = entry.strip().partition("\0")
        m = re.search(r"\(cherry picked from commit ([0-9a-f]{40})\)", body)
        if m:
            marks[c] = m.group(1)
    for x in out("rev-list", "--reverse", "--ancestry-path", f"{sha}..{push.WORK_BRANCH}").split():
        main_side = out("rev-list", "--no-merges", old_main, f"^{x}", "--", *files).split()
        if any(git("merge-base", "--is-ancestor", marks.get(c, c), x).returncode for c in main_side):
            continue
        if set(out("rev-list", "--no-merges", x, f"^{old_main}", "--", *files).split()) <= fine:
            return x
    return None


def _clash_why(sha: str, row: str, files: list[str], old_main: str, fine: set[str], rows: dict, held: list[dict]) -> str:
    """F152: why a checked commit doesn't go on main: the held row (or the unchecked work) it needs, or a clash with main itself."""
    name = qa.title_of(row) or row or sha[:7]
    need = [c for c in out("rev-list", "--no-merges", f"{sha}^", f"^{old_main}", "--", *files).split() if c not in fine]
    named = list(dict.fromkeys(x["label"] for c in need for x in held
                               if any(c.startswith(s) or s.startswith(c) for s in rows.get(x["label"], []) + [x.get("sha") or "-"])))
    if named:
        return f"{name} ({sha[:7]} doesn't go on main without {', '.join(named)}, which is held)"
    if need:
        return f"{name} ({sha[:7]} doesn't go on main without work that hasn't passed QA)"
    return f"{name} ({sha[:7]} clashes with what's on main in {', '.join(files)}, and nothing on dev settles it)"


def _added_lines(sha: str) -> list[str]:
    """The changelog lines a commit adds ("- …")."""
    diff = out("show", "--format=", "-U0", sha, "--", "CHANGELOG.md")
    return [ln[1:] for ln in diff.splitlines() if ln.startswith("+-")]


def cmd_part(h: dict, today: dt.date | None = None, want: str | None = None) -> int:
    """F56, F152: release only the work that passed QA. It starts from main (the version out now) in a worktree of its own and brings
    in, one by one, the checked commits that aren't on main yet (_picks), each with its mark, the release's own files (changelog,
    VERSION, README) kept as main has them; a row whose commits don't go on main without held work (a conflict) stays held, with why.
    The version commit goes on top; main moves forward to it and the tag goes there; dev gets it merged back (its tree kept, the
    released lines moved under the version), so main stays an ancestor of dev. nightly is left as it is. Anything failing partway puts
    main, dev and the tag back; nothing is forced."""
    today = today or dt.date.today()
    old_main, old_dev = out("rev-parse", push.RELEASE_BRANCH), out("rev-parse", push.WORK_BRANCH)
    to = h.get("to")
    # main under the last checked commit: the version goes right on it (F56); main beside it (job 517): from main, picked in (F152)
    start = to if to and not git("merge-base", "--is-ancestor", old_main, to).returncode else old_main
    picks = _picks(h, old_main, start)
    if not picks and start == old_main:
        print(f"No release: what passed QA is on {push.RELEASE_BRANCH} already, nothing new to bring in; it stays on "
              f"{push.NIGHTLY_BRANCH}, main stays at {released()}.")
        _keep("what had passed QA was out already, so nothing went out.")
        return 0
    old, v = release_version(want)
    tag = f"v{v}"
    if not git("rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode:
        print(f"No release: the tag {tag} is already here.")
        return 2
    import shutil
    import tempfile
    wt = Path(tempfile.mkdtemp(prefix="hq-release-")) / "wt"
    files = ["CHANGELOG.md", "VERSION"]
    msg = (f"HQ {v}: the changelog's Coming next becomes {v} ({today.day} {today:%B %Y}) for the work that passed QA, "
           f"VERSION {v}, the README's version (H186, F56, F152)\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")

    def gone():
        git("worktree", "remove", "--force", str(wt))
        shutil.rmtree(wt.parent, ignore_errors=True)

    def back(why: str) -> int:
        print(f"No release: {why} main stays at {released()}, {push.WORK_BRANCH} and {push.NIGHTLY_BRANCH} as they were.")
        git("merge", "--abort")
        git("checkout", "-q", push.WORK_BRANCH)
        git("reset", "-q", "--keep", old_dev)
        _restore(files + [WAY_BACK], old_dev)
        git("tag", "-d", tag)
        git("branch", "-f", push.RELEASE_BRANCH, old_main)
        gone()
        _keep(f"no release: {why}")
        return 2

    if git("worktree", "add", "-q", "--detach", str(wt), start).returncode:
        shutil.rmtree(wt.parent, ignore_errors=True)
        print("No release: git couldn't make a worktree for it.")
        return 2

    def w(*a, env=None):
        return subprocess.run(["git", "-C", str(wt), *a], text=True, capture_output=True, env=env)
    mine = [f for f in RELEASE_FILES if (wt / f).exists()]
    brought, stuck, row_at, done = [], {}, {}, _on_main(old_main)
    for sha, row in picks:
        if row in stuck:
            continue
        row_at.setdefault(row, w("rev-parse", "HEAD").stdout.strip())
        w("cherry-pick", "-n", sha)
        if mine:
            w("checkout", "HEAD", "--", *mine)
        for f in RELEASE_FILES:  # one the commit brings that main doesn't have stays out too
            if f not in mine and (wt / f).exists():
                w("rm", "-q", "-f", "--cached", "--", f)
                (wt / f).unlink()
        clash = w("diff", "--name-only", "--diff-filter=U").stdout.split()
        if clash:  # F152: a clash with work on main that dev already settled takes the settled version; else it stays held
            fine = done | {p for p, r in picks if r not in stuck}
            x = _settled(sha, clash, old_main, fine)
            for f in clash if x else []:
                if git("cat-file", "-e", f"{x}:{f}").returncode:
                    w("rm", "-q", "-f", "--", f)
                else:
                    w("checkout", x, "--", f)
                    w("add", "--", f)
            if not x or w("diff", "--name-only", "--diff-filter=U").stdout.strip():
                w("cherry-pick", "--quit")
                w("reset", "-q", "--hard", row_at[row])
                stuck[row] = _clash_why(sha, row, clash, old_main, fine, h.get("commits") or {}, h["held"])
                brought = [b for b in brought if b[1] != row]
                continue
        a = out("log", "-1", "--format=%an%x00%ae%x00%aI", sha).split("\0")
        env = {**os.environ, "GIT_AUTHOR_NAME": a[0], "GIT_AUTHOR_EMAIL": a[1], "GIT_AUTHOR_DATE": a[2]} if len(a) == 3 else None
        body = out("log", "-1", "--format=%B", sha)
        if w("commit", "-q", "--allow-empty", "--no-verify", "-m", f"{body}\n\n(cherry picked from commit {sha})", env=env).returncode:
            return back(f"git couldn't bring in {sha[:7]}.")
        brought.append((sha, row))
    why_stuck = "; ".join(stuck.values())
    if why_stuck:
        print("Held: " + why_stuck + ".")
    if not brought and start == old_main:
        return back(f"nothing that passed QA goes on {push.RELEASE_BRANCH} on its own: {why_stuck or 'nothing to bring in'}.")
    picked = w("rev-parse", "HEAD").stdout.strip()
    on_main = out("show", f"{old_main}:CHANGELOG.md")
    lines = [] if start == old_main else [ln for ln in _coming(out("show", f"{to}:CHANGELOG.md")) if ln not in on_main]
    for sha, row in brought:
        for ln in _added_lines(sha):
            if ln not in lines and ln not in on_main:
                lines.append(ln)
    if not lines:  # F152: checked work that wrote no changelog line still goes out under its row's name
        for sha, row in brought:
            ln = f"- {qa.title_of(row) or out('log', '-1', '--format=%s', sha)}" + (f" ({row})." if row else "")
            if ln not in lines:
                lines.append(ln)
    lines += [x for x in data_lines(old_main, picked).splitlines() if x.strip()]  # F104: its data changes are listed with it
    no = data_refuses(old_main, picked)
    if no:
        return back(no[len("No release: "):] if no.startswith("No release: ") else no)
    (wt / "CHANGELOG.md").write_text(_versioned((wt / "CHANGELOG.md").read_text(encoding="utf8"), v, today, lines), encoding="utf8")
    (wt / "VERSION").write_text(v + "\n")
    if (wt / "README.md").exists():
        files.append("README.md")
        (wt / "README.md").write_text((wt / "README.md").read_text(encoding="utf8").replace(f"**{old}**", f"**{v}**", 1), encoding="utf8")
    files += way_back_file(wt, old, picked)
    if w("add", *files).returncode or w("commit", "-q", "-m", msg).returncode:
        return back("git couldn't commit the version.")
    rel = w("rev-parse", "HEAD").stdout.strip()
    if git("merge-base", "--is-ancestor", old_main, rel).returncode:
        return back(f"the version doesn't come after {old_main[:7]}.")
    for step in (("branch", "-f", push.RELEASE_BRANCH, rel), ("tag", "-a", tag, "-m", tag_words(v, h), rel)):
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
    if WAY_BACK in files:  # dev the same as the release, never more
        way_back_file(ROOT, old)
    if git("add", *files).returncode or git("commit", "-q", "-m", f"HQ {v} back into dev: what's held stays under "
                                             f"Coming next (F56)\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>").returncode:
        return back("git couldn't commit the merge on dev.")
    gone()
    r = push.push_branch(push.RELEASE_BRANCH, release=True)
    if r:
        print(f"No release: GitHub refused main or the tags; put back as it was: main at {old[:20]}, {push.WORK_BRANCH} and "
              f"{push.NIGHTLY_BRANCH} as they were, nothing forced.")
        git("reset", "-q", "--keep", old_dev)
        git("tag", "-d", tag)
        git("branch", "-f", push.RELEASE_BRANCH, old_main)
        _keep("no release: GitHub refused main or the tags; put back as it was.")
        return 2
    r = push.push_branch(push.WORK_BRANCH) or push.push_nightly(push.WORK_BRANCH, [])
    went = ", ".join(dict.fromkeys(r_ or s[:7] for s, r_ in brought))
    print(f"Released {v} ({tag}) on {push.RELEASE_BRANCH}, forward from {old} with only the work that passed QA"
          f"{f' (brought in: {went})' if went else ''}; what's held stays on {push.WORK_BRANCH} and {push.NIGHTLY_BRANCH}.")
    if qa.before_words(h, going=True):
        print(qa.before_words(h, going=True))
    on_the_record(old_main, tag, v)
    _keep(f"{v} went out, with what's held left on {push.WORK_BRANCH}.")
    return r


def data_refuses(base: str, tip: str) -> str | None:
    """F104: a release that changes data needs an undo that works: tried on a copy of the workspace, from the code at the tip."""
    import datachange
    no = datachange.number_refuses(base, tip, ROOT)
    if no:
        return f"No release: {no}. It stays on {push.NIGHTLY_BRANCH}; main stays at {released()}."
    new = datachange.between(base, tip, ROOT)
    if not new:
        return None
    no = datachange.try_on_copy(new, root=ROOT)
    return f"No release: {no}. It stays on {push.NIGHTLY_BRANCH}; main stays at {released()}." if no else None


def data_lines(base: str, tip: str) -> str:
    """F104: the changelog's lines for a release's data changes, under its heading."""
    import datachange
    new = datachange.between(base, tip, ROOT)
    return ("\n" + "\n\n".join(datachange.lines_for(new, ROOT)) + "\n") if new else ""


def on_the_record(old_main: str, tag: str, v: str) -> list[str]:
    """F103: which items this version took: the builds whose proof record stands on a commit in it (the id they carried), and the
    rows named at the start of a commit's subject for work done by hand. Never a search through sentences."""
    import proof
    import trail
    shas = out("log", "--format=%H", f"{old_main}..{tag}").split()
    ids = {}
    for sha in shas:
        for label in qa.commit_labels(str(ROOT), sha, out("log", "-1", "--format=%s", sha)):  # F120: a listed commit counts for its row
            ids.setdefault(trail.resolve(label), sha)
    try:
        for name in os.listdir(proof.folder()):
            rec = json.load(open(os.path.join(proof.folder(), name))) if name.endswith(".json") else {}
            if rec.get("item") and rec.get("head") in shas:
                ids.setdefault(rec["item"], rec["head"])
    except (OSError, ValueError):
        pass
    for item, sha in ids.items():
        trail.step(item, "release", version=v, tag=tag, commit=sha[:12])
    return [i for i in ids if i]


def _restore(files: list[str], at: str = "HEAD") -> None:
    """F112: the release's own files as they stand in the commit before, index and folder both; one that wasn't there goes."""
    for f in files:
        if git("cat-file", "-e", f"{at}:{f}").returncode:
            git("rm", "-q", "--cached", "--ignore-unmatch", "--", f)
            try:
                (ROOT / f).unlink()
            except OSError:
                pass
        else:
            git("checkout", "-q", at, "--", f)


def _undo(old_main: str, tag: str, committed: bool, files: list[str] | None = None) -> int:
    git("checkout", "-q", push.WORK_BRANCH)
    git("tag", "-d", tag)
    git("branch", "-f", push.RELEASE_BRANCH, old_main)
    if committed:
        git("reset", "-q", "--keep", "HEAD~1")
    _restore(files or [f for f in ("CHANGELOG.md", "VERSION", "README.md", WAY_BACK) if (ROOT / f).exists()])
    _restore([WAY_BACK])
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
        cells = hqpaths.cells(row)  # F101: the one reader; an escaped pipe isn't a cell
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
    if s.get("night_refuses"):
        lines.append(f"The release would refuse: {s['night_refuses']}")
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
        # F56: --without-qa only on his explicit say-so on a call; it releases everything on dev. F101: that say-so, and
        # going past a red night, is a quote found in his own lines (--said), kept with the time.
        said = argv[argv.index("--said") + 1] if "--said" in argv and argv.index("--said") + 1 < len(argv) else None
        want = None
        if "--version" in argv:  # F112: a version named is a number, never the next word or nothing
            i = argv.index("--version") + 1
            want = argv[i] if i < len(argv) and not argv[i].startswith("--") else ""
            if not want:
                print("No release: --version needs the version, like --version 1.0.0.")
                return 2
        return cmd_main(without_qa="--without-qa" in argv, red_night="--past-the-night" in argv, said=said, want=want)
    if cmd == "log" and len(argv) >= 2:
        if not add_line(" ".join(argv[1:])):
            print(f"No {ROW} row on the roadmap.")
            return 1
        print("Written.")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    import routines
    try:
        code = main(sys.argv[1:])
    except Exception as e:  # F102: a release that fails is red, with an incident; its line has a day's interval
        routines.bad("release", f"release.py failed: {e!r}", every=86400)
        raise
    if sys.argv[1:2] in (["main"], ["nightly"]):
        if code == 0:
            routines.good("release", "Ran fine", every=86400)
        elif code == 2:
            routines.beat("release", state="waiting", text="Held back: see the night and QA", last=__import__("time").time(), every=86400)
        else:
            routines.bad("release", f"release.py {sys.argv[1]} ended with {code}", every=86400)
    sys.exit(code)
