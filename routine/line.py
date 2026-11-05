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
  - It's with the team (a build, its QA, a fix): nothing, the queue has it. A build that ended red without a record gets its proof run
    once more (red twice: one text to him, and the line leaves it).
  - Ready: with build on, the program sends it to the team itself (by day only on his own switch, at night also on hers). Build off:
    nothing more; prepared.
  - Only the Ready mark is missing: the program sets it.
  - The review is still to run on its new words: nothing, the routine reviews it after five quiet minutes.
  - Anything else (the review flagged it, her tests are missing, not sealed, not reviewed, a finding from QA, missing ready points): with
    prepare on, a prep job for Moneypenny in the team's line, for that one item, with the next step as the record says it. She does the
    work, never the send. When she ends, the line reads the record again. The same step three times without the record moving: one text
    to him with what's stuck, and the line leaves the item until its words or its switches change.

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
    """The waiting or running prep job for LABEL, or None."""
    for j in jobs:
        if prep_label(j["text"]) == label and not j["state"].startswith(q.FINISHED):
            return j
    return None


def _night(now=None):
    import wall
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
    j = q.with_team(jobs, label)
    if j:
        if j["state"].startswith("paused: ended, no record"):
            return "rerun", f"job {j['n']} ended without a green record"
        return "wait", f"with the team: job {j['n']} ({j['state']})"
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
    if not g.get("prep"):
        return "none", f"not ready and prepare is off: {why}"
    return "prep", why


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
            f"item's own words (review.py add or reword), write or fix your QA tests (qatests.py new, check, review), fill what's "
            f"missing. Never send it to the team, never jobs.py send-row or now: the program sends it once it's ready and its build "
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
    if what == "rerun":
        j = q.with_team(jobs, label)
        if not j:
            return None
        if e.get("rerun") == j["n"]:
            if not e.get("told_red") == j["n"]:
                e["told_red"] = j["n"]
                _tell(label, f"red-{j['n']}", f"{label}: the team's build (job {j['n']}) is still red after its check ran twice, so it's stuck there. "
                      f"The line leaves it until a fix goes in.")
            return None
        e["rerun"] = j["n"]
        lock = os.path.expanduser("~/hq-fullrun.lock")
        cmd = f'python3 routine/proof.py run {j["n"]} && python3 routine/jobs.py done {j["n"]}'
        if shutil.which("flock"):
            cmd = f'flock {lock} sh -c "{cmd}"'
        subprocess.Popen(["sh", "-c", cmd], cwd=os.path.dirname(HERE), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL, start_new_session=True, env={**os.environ, "HQ_ROLE_HERE": "1"})
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
    for l in [x for x in st if x not in go]:
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
        if what in ("send", "mark", "rerun", "prep"):
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
