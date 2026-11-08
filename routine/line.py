#!/usr/bin/env python3
"""The line: the routine carries every item with a switch on along its road, so nobody has to remember the next step (5 November 2026).

His words (laptop chat, 5 November 2026), after a day of his "now" lost between a call and the team: "it should just be a switch that
the whole process goes on. it either gets flipped during her cycle, when she sees there is usage space left and we have some items on
the planning?" and "another switch that also says it can be built right now (considering the previous flow has accepted it fully and
it's on ready status), which she can either also activate in her cycle so then that night things will get built, or during daytime if i
tell her to flip it." And: "then MP's hours can be in the night with the team, and her triggers work there, and then i can always call
her during daytime and she can still pick things up on request". The report of that evening (HQ/report-what-is-broken.md): nobody owned
moving an item from one step to the next; the program checked, Moneypenny moved, and she's a conversation that ends when he hangs up.

The switches are on the item (sprint.py go): prepare and build. Every minute on the main, for each item with a switch on, the line reads
the record, never anyone's word, and does the next step:

  - The row isn't open any more (done, parked, gone): its switches go.
  - It's with the team (a build, its QA, a fix): nothing, the queue has it. A build that ended red without a green record (F164, 7 November
    2026): the line reads its failing lines. A real failure (her tests, a flow the row names) goes back to the team by itself as a resume
    of its own job, the failing lines in a note it reads first (at night; by day only on his switch), up to its two resumes (past them:
    one text to him, and the line leaves it). A check unrelated to the item becomes its own row, both switches on as the night's own,
    like the night run's failures, never resumed for; once each is on the planning, the build's record step runs again by itself, those
    checks excused (F165, 7 November 2026: before, such a build stayed held until someone looked; tonight F155, job 623 and H338), so a
    build whose own tests pass closes. Nothing to read: its proof runs once more (red twice: one text, the line leaves it).
  - Held (F192, 7 November 2026): its Waits on names an item still open that hasn't passed her check: nothing, no build, prep or
    resume, by day or at night, and show names what it waits on; she lifts it with "Waits on: nothing". "Waits on: nothing" (or none,
    no) holds nothing, whatever follows it (F197); a wait on a Won't or parked item says so and is texted to her once.
  - Ready: with build on, the program sends it to the team itself (by day only on his own switch, at night also on hers). Build off:
    nothing more; prepared.
  - Only the Ready mark is missing: the program sets it.
  - The review is still to run on its new words: nothing, the routine reviews it after five quiet minutes.
  - Anything else (the review flagged it, her tests are missing, not sealed, not reviewed, a finding from QA, missing ready points): with
    prepare on, a prep job for Moneypenny in the team's line, for that one item, with the next step as the record says it. She does the
    work, never the send. When she ends, the line reads the record again. The same step three times without the record moving: one text
    to him with what's stuck, and the line leaves the item until its words or its switches change. A prep boxed (ran past its box)
    no longer holds the item: the line starts a fresh one with the record's next step, each one a try (F178, 7 November 2026). Before
    it gives up on her tests not through the hard checks, it runs qatests.py check itself once: sealed, it moves on with no text.

His pause of the team (jobs.py off) holds the line too.

    python3 routine/line.py tick         one pass (the routine runs it every minute on the main)
    python3 routine/line.py show [LABEL]  what the line sees and would do, nothing done
"""
import json, os, re, shutil, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hqpaths  # noqa: E402
import jobs as q  # noqa: E402
import sprint as S  # noqa: E402

STATE = os.environ.get("HQ_LINE_STATE") or os.path.join(hqpaths.HQ, ".status", "line.json")
TRIES = 3  # the same step this many prep jobs without the record moving: stuck, one text to him
PREP = "Prep of "  # a prep job's text starts so (qa.prompt_extra gives it her character); it never names "the X row" or "X on the HQ roadmap"
HERE = os.path.dirname(os.path.abspath(__file__))


def _load():
    try:
        with open(STATE, encoding="utf8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(d):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(tmp, STATE)


def is_prep(text):
    return (text or "").startswith(PREP)


def prep_label(text):
    m = re.match(rf"{re.escape(PREP)}([A-Z]\d+(?:\.\d+)*)\b", text or "")
    return m.group(1) if m else None


def prep_of(jobs, label):
    """The waiting, running or held prep job for LABEL, or None. F178: a boxed prep (ran past its box) is over for the line: it
    no longer holds the item, the line starts a fresh one; the boxed job stays as it is, with what it wrote."""
    for j in jobs:
        if prep_label(j["text"]) == label and not j["state"].startswith(q.FINISHED + ("boxed",)):
            return j
    return None


def _night(now=None):
    import wall
    if hasattr(now, "timestamp"):  # a datetime as well as a timestamp
        now = now.timestamp()
    return not wall.daytime(now)


def _review_waiting(row):
    try:
        import review
        st = review.states([row]).get(row["label"]) or {}
        return st.get("state") == "waiting"
    except Exception:
        return False


def next_step(row, g, jobs, now=None):
    """(what, detail) the line does for ROW with switches G: wait, send, mark, prep, rerun, hold, or none."""
    label = row["label"]
    try:  # passed her check: the line is through with it, the release takes it (a second send built it twice, 5 November 22:54)
        import qa
        if qa.state(label) == "passed":
            return "passed", "passed her check; the release takes it from here"
    except Exception:
        pass
    held = held_by(row)
    j = q.with_team(jobs, label)
    if j:
        if held and j["state"].startswith("paused: "):  # F192: a parked build of a held item isn't resumed or rerun either
            return "hold", held
        if j["state"].startswith("paused: ended, no record"):
            real, other = red_lines(j["state"], row)
            if real:  # F164: a real failure goes back to the team as a resume of its own job, at night on the night's own switches
                if (g.get("build") or {}).get("by") != "him" and not _night(now):
                    return "hold", f"job {j['n']} is red on {len(real)} real failure(s); by her pick it goes back to the team at night"
                return "resume", f"job {j['n']} is red on {len(real)} real failure(s)" + (f" and {len(other)} unrelated check(s)" if other else "")
            if other:  # F164: red only on checks unrelated to the item: each its own item, the build not resumed for them
                return "split", f"job {j['n']} is red only on {len(other)} check(s) unrelated to {label}"
            return "rerun", f"job {j['n']} ended without a green record"
        return "wait", f"with the team: job {j['n']} ({j['state']})"
    if held:  # F192: her hold is on the item (its Waits on), and no job of it starts, by day or at night, until it's lifted;
        return "hold", held  # a prep of it queued before the hold doesn't hide it: wall.why_not keeps that one back
    p = prep_of(jobs, label)
    if p:
        return "wait", f"her prep job {p['n']} ({p['state']})"
    why = S.not_ready_why(row)
    if why is None:
        b = g.get("build")
        if not b:
            return "none", "ready; build is off"
        if b.get("by") != "him" and not _night(now):
            return "hold", "ready; build is on by her pick, so it goes at night"
        return "send", "ready, build on"
    if "it only needs the mark" in why:
        return "mark", why
    if _review_waiting(row) and "review" in why and "QA tests" not in why:
        return "wait", "the review hasn't run on its new words yet"
    if WAITS_ON_HIM.search(why):  # H338 (Part C 4): only his answer moves it; prepared again it changed nothing (H324, three times on 6 November)
        return "wait", f"waits on his answer: {why}"
    if not g.get("prep"):
        return "none", f"not ready and prepare is off: {why}"
    return "prep", why


# F192 (7 November 2026): a hold she gives is the item's own Waits on (point 8 of ready); she lifts it with "Waits on: nothing".
# Its last Waits on counts; an item it names holds it while that item's row is open and hasn't passed her check.
# Rows write it three ways (QA, 7 November 2026 17:22): "Waits on: F175.", "Waits on F175: why ..." (F165's own row) and
# "Waits on nothing."; one in quotes is only words about a hold (as in this row's own QA note), not a hold.
_L = r"[A-Z]\d+(?:\.\d+)*"
_WAITS = re.compile(rf"(?<!['\"‘“])Waits on(?:: ([^.|]*)| nothing\b()| ({_L}(?:(?:, | and | & ){_L})*):)")
_LABEL = re.compile(r"(?<![\w-])([A-Z]\d+(?:\.\d+)*)(?![\w-])")


# F197 (7 November 2026): "Waits on: nothing" (or none, no) holds nothing, whatever the sentence says after it (H339: "Waits on:
# nothing; until H257 gives it its place, ..." was held on H257, a Won't item, for good). A wait on an item tagged Won't this time
# or parked would never end: it still holds, but says so, on the line, its state the status page reads, and one text to her.
_NONE = re.compile(r"\s*(?:nothing|none|no)\b", re.I)


def _stuck_why(r):
    """F197: "Won't this time" or "parked" for an item a wait on would never end, else None."""
    if re.match(r"(?:## )?Phase P\b", str(r.get("phase_title") or r.get("phase") or "")) or r.get("parked"):
        return "parked"
    try:
        if S.moscow_of().get(r["label"]) == "wont":
            return "Won't this time"
    except Exception:
        pass
    return None


def waits_of(row):
    """F192/F197: [(label, None or why it would never end)] the items ROW's last Waits on holds it behind."""
    said = ["".join(m) for m in _WAITS.findall(row.get("line") or "")]
    if not said or _NONE.match(said[-1]) or not said[-1].strip():
        return []
    try:
        import qa
    except Exception:
        qa = None
    waits = []
    for other in dict.fromkeys(_LABEL.findall(said[-1])):
        if other == row.get("label"):
            continue
        r = S.row_of(other)
        if not r or r.get("state") not in ("⬜", "🔨"):
            continue  # done or gone: nothing to wait for
        try:
            if qa and qa.state(other) == "passed":
                continue
        except Exception:
            pass
        waits.append((other, _stuck_why(r)))
    return waits


def held_by(row):
    """F192: why ROW is held behind another item (its Waits on names an open item that hasn't passed her check), or None."""
    waits = waits_of(row)
    if not waits:
        return None
    stuck = [f"{l} is {w}" for l, w in waits if w]
    labels = [l for l, _ in waits]
    out = f"held: waits on {', '.join(labels)} until {'they have' if len(labels) > 1 else 'it has'} passed her check (its Waits on)"
    if stuck:
        out += f"; it would wait forever: {', '.join(stuck)}"
    return out


# F164: the failing lines a red record gives (runjob._no_record_why): her QA tests ("FAIL name: ...", "her QA tests: ..."), flows
# ("FAIL flow name: ...", "45: FAILED - ..."). A flow the row names is its own; any other flow is a check unrelated to the item.
_RED = re.compile(r"(?:(?<=\s)|(?<=;)|^)(?=FAIL |her QA tests: |\d+: FAILED - )")
_FLOW = re.compile(r"FAIL flow (\S+?):|(\d+): FAILED - ")


def red_lines(state, row):
    """([real failing lines], [(check, line) unrelated to the item]) from a parked job's state; both empty: nothing to read."""
    why = state.split(":", 2)[2] if state.count(":") >= 2 else ""
    real, other = [], []
    try:
        import proof
        named = {str(x) for x in proof.named_flows(row.get("line") or "")}
    except Exception:
        named = set()
    for part in _RED.split(why):
        part = part.strip(" ;")
        if not re.match(r"FAIL |her QA tests: |\d+: FAILED - ", part):
            continue
        m = _FLOW.match(part)
        if m:
            name = m.group(1) or m.group(2)
            own = name in named or re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", row.get("line") or "")
            if not own:
                other.append(("flow " + name, part))
                continue
        real.append(part)
    return real, other


_WHY = re.compile(r"test(?:'s| is) wrong|\btest [\w.-]+ is wrong|can'?t be done|cannot be done|can not be done|isn'?t possible|"
                  r"not possible", re.I)
_HERS = re.compile(r"(?:fail on the built code: |; )([\w.-]+)(?=: | passes in the team's run)")


def red_names(real):
    """F187: the still-red tests' names in the failing lines: 'FAIL NAME', and her sealed tests' line (qatests.py: 'her QA tests fail
    on the built code: NAME: ...; NAME: ...')."""
    names = set()
    for part in real:
        m = re.match(r"FAIL ([\w.-]+)", part)
        if m:
            names.add(m.group(1))
        if "fail on the built code: " in part:
            names |= set(_HERS.findall(part[part.index("fail on the built code: "):]))
    return names


def stated_reason(real, row):
    """F187: a sentence in the build's row that names a still-red test and why (the test is wrong, her test NAME is wrong, or it can't
    be done), whatever its lead word ('Built (job N): NAME stays red, the test is wrong.'): that sentence, or ''. A resumed build ends
    only on a green record or such a reason; any other stop is silent and resumed again."""
    names = red_names(real)
    for s in re.split(r"(?<=[.!?])\s+|\s\|\s", row.get("line") or ""):
        if _WHY.search(s) and any(re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", s) for n in names):
            return s.strip()
    return ""


def _to_sitdown(label, j, real, reason):
    """F187: the red build on her sit-down list (review.py sitdown, quiet) and one if-then text to him naming the three ways, sent by
    the line; False when the list refused it, so the caller texts as before."""
    what = (f"The team's build (job {j['n']}) is still red on {real[0][:160] if real else 'its own test'}"
            + (f", and it says why: {reason[:240]}" if reason else ", after both its times back with the team, the most a job gets") + ".")
    ifthen = (f"If the test is wrong, I'll fix the test and send {label} back to the team; if not, either split {label} into "
              f"smaller items, or say no to it.")
    code, _ = _run([os.path.join(HERE, "review.py"), "sitdown", label, what, ifthen, "--quiet"])
    if code:
        return False
    _tell(label, f"red-{j['n']}", f"{label}: {what} {ifthen}")
    return True


def _split(label, j, other, st):
    """F164: each unrelated check of a red build on the planning as its own item, like the night run's failures (nightly.rotate):
    both switches on as the night's own. The same check's open row is used again, so a second red never makes a second one."""
    import jobs
    done = st.setdefault("_reruns", {}).setdefault(str(j["n"]), {}).setdefault("split", [])
    out = []
    for check, ln in other:
        if check in done:
            continue
        mark = f"(the line, {check})"
        said = (f"{check[0].upper() + check[1:]} failed in the build of {label} (job {j['n']}), a check unrelated to {label}: {ln[:500]}. "
                f"Split out by the line (F164) as its own item, like the night run's failures: fixed through the whole rotation, the row, "
                f"the review, her test, the Ready mark, the team, her check. {mark}").replace("|", "/")
        try:
            with jobs.locked():
                with open(jobs.ROADMAP, encoding="utf8") as f:
                    text = f.read()
                new = next((r["label"] for r in S.open_rows(text) if mark in r["line"]), None)
                if not new:
                    text, new = jobs.roadmap_row(text, said, True, by="the line")
                    tmp = jobs.ROADMAP + ".tmp"
                    with open(tmp, "w", encoding="utf8") as f:
                        f.write(text)
                    os.replace(tmp, jobs.ROADMAP)
            S.set_go(new, "both", True, by="night")
            done.append(check)
            out.append(f"{check} is {new}")
        except (Exception, SystemExit) as e:  # one check not written never stops the others
            out.append(f"{check} not written: {e!r}"[:160])
    return out


def _record_again(j, excused=()):
    """F155: the job's record step once more in the background (its tests on a copy, the done mark, else parked with why), on the
    lock the full runs take turns on. F165: EXCUSED, flows already on the planning as their own items, don't hold its record."""
    lock = os.path.expanduser("~/hq-fullrun.lock")
    cmd = f'python3 routine/runjob.py {j["n"]}'
    if shutil.which("flock"):
        cmd = f'flock {lock} sh -c "{cmd}"'
    env = {**os.environ, "HQ_ROLE_HERE": "1"}
    if excused:
        env["HQ_PROOF_EXCUSED"] = ",".join(excused)
    subprocess.Popen(["sh", "-c", cmd], cwd=os.path.dirname(HERE), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     stdin=subprocess.DEVNULL, start_new_session=True, env=env)


WAITS_ON_HIM = re.compile(r"waits? on his (?:answer|decision|yes)|it's his decision now|on her sit-down list", re.I)


HARD_CHECKS = re.compile(r"QA tests.{0,40}haven't passed the hard checks")


def _fp(why):
    return re.sub(r"\(round \d+ of \d+\)", "", why or "")[:300]


def _run(args, env=None):
    r = subprocess.run([sys.executable, *args], cwd=os.path.dirname(HERE), capture_output=True, text=True,
                       env={**os.environ, **(env or {}), "HQ_ROLE_HERE": "1"}, timeout=120)
    return r.returncode, (r.stdout + r.stderr).strip()


def _tell(label, key, words):
    try:
        import qatests
        return qatests.tell(label, f"line-{key}", words)
    except Exception:
        return False


def prep_text(label, why, row):
    title = (row.get("title") or "").strip()
    return (f"{PREP}{label} (the line): get item {label} ready for the team. {title[:160]} The next step, from the record: {why}. "
            f"Do that step and every one after it you can, until sprint.py check {label} says it's ready: answer the review in the "
            f"item's own words (review.py add or reword), write or fix your QA tests (qatests.py new, check, review: H342, the row's own "
            f"done example replayed on the real data of the copy they run on, read where he looks, the status page as served and a text "
            f"as it lands, with routine/realcase.py, failing first on the code from before the build for the row's reason), fill what's "
            f"missing. Before you end, run python3 routine/qatests.py check {label} once yourself, so tests that pass the hard checks "
            f"are sealed and the line moves on. Never send it to the team, never jobs.py send-row or now: the program sends it once it's ready and its build "
            f"switch is on. Text him only for a real decision, never for a step you can take yourself.")


def act(label, what, detail, row, st, jobs):
    """Does the step. Returns a short line for the routine's log, or None."""
    e = st.setdefault(label, {})
    if what == "send":
        code, out = _run([os.path.join(HERE, "jobs.py"), "send-row", label, "--line"])
        e.update(last="send", at=time.strftime("%Y-%m-%d %H:%M"), out=out[-300:])
        return f"{label}: sent to the team by the line ({out.splitlines()[-1][:120] if out else code})"
    if what == "mark":
        code, out = _run([os.path.join(HERE, "sprint.py"), "ready", label, "on"])
        return f"{label}: marked ready by the line ({out[:120]})"
    if what in ("resume", "split"):
        j = q.with_team(jobs, label)
        if not j:
            return None
        real, other = red_lines(j["state"], row)
        said = _split(label, j, other, st)
        run = st.setdefault("_reruns", {}).setdefault(str(j["n"]), {})
        if what == "split":
            # F165: once each unrelated check is on the planning as its own item, the build's record step runs again by itself,
            # those checks excused, so a build whose own tests pass closes (before, it stayed held until someone looked)
            written = set(run.get("split") or []) | {s.split(" is ", 1)[0] for s in said if " is " in s and "not written" not in s}
            checks = [c for c, _ in other]
            again = None
            if checks and all(c in written for c in checks) and not set(checks) <= set(run.get("excused") or []):
                run["excused"] = sorted(set(run.get("excused") or []) | set(checks))
                _record_again(j, [c.split(" ", 1)[1] for c in run["excused"] if c.startswith("flow ")])
                again = f"its record step runs again with {', '.join(run['excused'])} excused"
            out = "; ".join(said + ([again] if again else []))
            return f"{label}: job {j['n']} red only on checks unrelated to it, each its own item ({out})" if out else None
        import wall
        no = None if wall.off() else wall.no_resume(j["n"])
        reason = stated_reason(real, row)
        if reason or no:  # F187: a stated reason, or past its two resumes: on her sit-down list with one text, the line leaves it
            if run.get("told"):
                return None
            run["told"] = True
            if _to_sitdown(label, j, real, reason):
                return (f"{label}: job {j['n']} red " + ("with its reason written" if reason else "past its resumes")
                        + "; on her sit-down list, one text to him, the line leaves it")
            _tell(label, f"red-{j['n']}", f"{label}: the team's build (job {j['n']}) is still red on a real failure ({real[0][:160]}), and "
                  f"it has had its {wall.MOST_RESUMES} resumes. {wall.what_next(j['n'])} The line leaves it.")
            return f"{label}: job {j['n']} red past its resumes; told him, the line leaves it"
        note = ("Your build came back red on what your item owns, so the line (F164) sent it back to you as a resume: make these "
                "green, then commit, push, write the result and end the run as before. If one can't go green, write why in the row "
                "in one sentence naming the test, like 'Built (job N): NAME stays red, the test is wrong.' or '... NAME stays red, it "
                "can't be done ...': then it goes to Moneypenny as a decision, not back to you. The failing lines: " + " / ".join(real)
                ).replace("⟪", "(").replace("⟫", ")")
        with q.locked():
            text, js, on = q.read()
            jj = next((x for x in js if x["n"] == j["n"]), None)
            if not jj or not jj["state"].startswith("paused: ended, no record"):
                return None
            jj["state"] = "held: resumed by the line"
            jj.setdefault("notes", []).append({"at": time.strftime("%Y-%m-%d %H:%M"), "text": " ".join(note.split())[:2000]})
            q.write(text, js, on)
        try:
            wall.raise_box(j["n"])
        except Exception:
            pass
        run["resumed"] = run.get("resumed", 0) + 1
        return (f"{label}: job {j['n']} red on {len(real)} real failure(s), back to the team as a resume with them"
                + (f"; {'; '.join(said)}" if said else ""))
    if what == "rerun":
        j = q.with_team(jobs, label)
        if not j:
            return None
        runs = st.setdefault("_reruns", {})  # by job, kept apart from the item's own state: a result written in the row doesn't reset it
        if str(j["n"]) in runs:
            if not runs[str(j["n"])].get("told"):
                runs[str(j["n"])]["told"] = True
                _tell(label, f"red-{j['n']}", f"{label}: the team's build (job {j['n']}) is still red after its check ran twice, so it's stuck there. "
                      f"The line leaves it until a fix goes in.")
            return None
        runs[str(j["n"])] = {"at": time.strftime("%Y-%m-%d %H:%M")}
        _record_again(j)
        return f"{label}: job {j['n']}'s check run once more by the line"
    if what == "prep":
        fp = _fp(detail)
        if e.get("fp") == fp:
            e["tries"] = e.get("tries", 0) + 1
        else:
            e.update(fp=fp, tries=1, told=False)
        if e["tries"] > TRIES:
            if not e.get("told"):
                e["told"] = True
                if HARD_CHECKS.search(detail):  # F178: her tests may pass the hard checks by now (F165's night): the check once, before giving up
                    code, out = _run([os.path.join(HERE, "qatests.py"), "check", label])
                    if code == 0 and "tests are sealed" in out:
                        return f"{label}: her QA tests sealed by the line's own check; it moves on"
                _tell(label, "stuck", f"{label} is stuck on the same step after {TRIES} tries of mine: {detail}. "
                      f"The line leaves it until its words or its switches change.")
            return None
        code, out = _run([os.path.join(HERE, "jobs.py"), "add", prep_text(label, detail, row), "--prep", "--item", label, "--kind", "research"])
        e["last"] = "prep"
        return f"{label}: a prep job for Moneypenny ({out.splitlines()[-1][:120] if out else code})"
    return None


def tick(now=None):
    """One pass over the items with a switch on. Returns the lines it did."""
    import role
    if role.is_backup():
        return []
    _, jobs, on = q.read()
    if not on:  # his pause of the team holds the line too
        return []
    rows = {r["label"]: r for r in S.open_rows()}
    S.go_clear_closed(list(rows.values()))
    go = S.go_all()
    st = _load()
    for l in [x for x in st if x not in go and not x.startswith("_")]:
        st.pop(l, None)
    done = []
    for label, g in go.items():
        row = rows.get(label)
        if not row:
            continue
        fp_row = S.ask_fp(row["line"])
        e = st.setdefault(label, {})
        if e.get("row") != fp_row or e.get("go") != json.dumps(g, sort_keys=True):  # his words or the switches changed: start fresh
            st[label] = e = {"row": fp_row, "go": json.dumps(g, sort_keys=True)}
        what, detail = next_step(row, g, jobs, now)
        e["seen"] = f"{what}: {detail}"[:300]
        if what == "hold" and "it would wait forever: " in detail:  # F197: once per hold, not every minute
            stuck = detail.split("it would wait forever: ", 1)[1]
            if e.get("told_stuck") != stuck:
                e["told_stuck"] = stuck
                _tell(label, "wait-stuck", f"{label} is held on its Waits on, and that wait would never end: {stuck}. "
                      f"Lift it (Waits on: nothing) or change what it waits on.")
                done.append(f"{label}: held on a wait that never ends ({stuck}); told her")
        if what == "passed":  # its switches go: nothing more for the line to do
            with q.locked():
                S.set_go(label, "both", False)
            done.append(f"{label}: passed her check, its switches off")
            continue
        if what in ("send", "mark", "rerun", "resume", "split", "prep"):
            line = act(label, what, detail, row, st, jobs)
            if line:
                done.append(line)
                _, jobs, on = q.read()
    _save(st)
    return done


def show(labels=None):
    _, jobs, on = q.read()
    rows = {r["label"]: r for r in S.open_rows()}
    go = S.go_all()
    out = [] if on else ["The team is paused, so the line waits too."]
    for label in labels or sorted(go):
        row = rows.get(label)
        if not row:
            out.append(f"{label}: not an open row.")
            continue
        g = go.get(label) or S.go_of(label)
        what, detail = next_step(row, g, jobs)
        out.append(f"{label}: {S.go_words(label, g)}. Next: {what}, {detail}")
    return "\n".join(out) or "No item has a switch on."


def main(argv):
    cmd = argv[0] if argv else "show"
    if cmd == "tick":
        for l in tick():
            print(l)
    elif cmd == "show":
        print(show([a.strip().upper() for a in argv[1:]] or None))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
