#!/usr/bin/env python3
"""The queue of jobs agreed on a call (phase L, 9 October 2026). It lives in roadmap.md, in the
section "## The queue" right under the status block, so the call, the routine and the status page
all read the same place. One line per job:

    - Job 3 · ready · agreed 2026-10-09 21:30 · <what to do, self-contained>

States: ready · running since 21:31 · stop asked · stopped 21:40 · done 21:45 ·
held: usage over the line · ended 21:45 without a done mark · cancelled 21:33 ·
paused: used about twice its estimated usage (H172: not started again by itself; resume N or stop N from a call).
", past the line" after the state: the user's say-so on a call to go past the 5-hour usage line, for that job only.
The weekly line always counts, also for such a job (F13, 10 October 2026).
The waiting jobs (ready or held) run in the order they stand on the list, top first (H39, 10 October 2026):
a new job goes at the bottom, and "move" changes its place. The job numbers never change.

usage (from the workspace):
  python3 "routine/jobs.py" add "TEXT" [--past-the-line] [--kind K]   a call's let's go: the job is ready;
                                                           K (transcribe, big, call, build, other) sets the
                                                           kind for its estimate instead of the guess (H70)
  python3 "routine/jobs.py" list                           the queue, as on the roadmap, with each job's estimate (H61)
  python3 "routine/jobs.py" stop [N]                       stop the running job (or cancel ready job N)
  python3 "routine/jobs.py" overrule N                     job N may go past the 5-hour line (the weekly line still counts)
  python3 "routine/jobs.py" move N top|up|down|bottom      move waiting job N in the line (H39)
  python3 "routine/jobs.py" move N before|after M          put waiting job N just before or after job M
  python3 "routine/jobs.py" done N                         the job's own chat, when it's finished
  python3 "routine/jobs.py" held N                         the job's own chat, when the usage says STOP; the
                                                           next start carries on from there (H113)
  python3 "routine/jobs.py" resume N                       a job paused for using about twice its estimated usage
                                                           carries on, in its own chat (H172); stop N drops it
  python3 "routine/jobs.py" off | on                       jobs from calls off or on
  python3 "routine/jobs.py" mail-off | mail-on             the hourly mail check off or on (L8)
Used by the routine itself: next, mark N STATE, crashed N "HOW" (H62: job N ended by a crash; its rerun
goes to the top of the line, once only).
"""
import fcntl, json, os, re, sys, time
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # M1: the roadmap is in the workspace
ROADMAP = hqpaths.ROADMAP
LOCK = os.path.join(HERE, "..", "scratch", "routine", "queue.lock")
# H141: why the job first in line waits, as the routine's start check last said it (tick.py writes it).
# A test's roadmap copy (HQ_ROADMAP) never reads the real one.
GATE_NOTE = os.environ.get("HQ_GATE_NOTE") or (
    "" if os.environ.get("HQ_ROADMAP") else os.path.join(HERE, "..", "scratch", "routine", "gate-note"))
HEADING = "## The queue"
INTRO = (
    "Jobs agreed on a call, run one at a time on the MacBook by the routine (phase L). A call's let's go "
    "adds a job here as ready; within about a minute the routine starts the waiting job highest on this list in a Terminal "
    "window, as a normal chat with let's go, and starts the next one only when that one is done. Kept by "
    "the routine's queue script; the lines are not edited by hand. A call can move a waiting job up or down."
)
LINE = re.compile(r"^- Job (\d+) · (.+?) · agreed (\d{4}-\d\d-\d\d \d\d:\d\d) · (.*)$")
FINISHED = ("done", "stopped", "ended", "cancelled")
KEEP_FINISHED = 5
PAST = ", past the line"
MAIL = True  # the hourly mail check through the routine (L8); its own switch, so jobs off leaves it running


@contextmanager
def locked():
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    with open(LOCK, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def read():
    """(text, jobs, routine_on). jobs: list of dicts n, state, past, agreed, text."""
    global MAIL
    text = open(ROADMAP, encoding="utf8").read()
    jobs, on = [], True
    sec = section(text)
    if sec:
        for l in text[sec[0]:sec[1]].splitlines():
            m = LINE.match(l)
            if m:
                state = m.group(2)
                past = state.endswith(PAST)
                jobs.append({"n": int(m.group(1)), "state": state[: -len(PAST)] if past else state,
                             "past": past, "agreed": m.group(3), "text": m.group(4)})
            elif l.startswith("**Routine:**"):
                on = "off" not in l.lower()
            elif l.startswith("**Mail check:**"):
                MAIL = "off" not in l.lower()
    return text, jobs, on


def section(text):
    """(start, end) of the queue section, or None."""
    i = text.find("\n" + HEADING + "\n")
    if i < 0:
        return None
    i += 1
    j = text.find("\n# ", i)
    k = text.find("\n## ", i + len(HEADING))
    ends = [x for x in (j, k) if x >= 0]
    return i, (min(ends) + 1 if ends else len(text))


def write(text, jobs, on):
    finished = [j for j in jobs if j["state"].startswith(FINISHED)]
    drop = {j["n"] for j in finished[:-KEEP_FINISHED]} if len(finished) > KEEP_FINISHED else set()
    # H39: finished jobs by number, then running, then the waiting ones in their place in line.
    rest = [j for j in jobs if not j["state"].startswith(FINISHED)]
    order = sorted(finished, key=lambda j: j["n"]) + [j for j in rest if not waiting(j)] + [j for j in rest if waiting(j)]
    lines = [f"- Job {j['n']} · {j['state']}{PAST if j['past'] else ''} · agreed {j['agreed']} · {j['text']}"
             for j in order if j["n"] not in drop]
    body = (f"{HEADING}\n\n{INTRO}\n\n**Routine:** {'on' if on else 'off'}\n\n"
            f"**Mail check:** {'on' if MAIL else 'off'} (every hour, hidden, also while a job runs; commits take turns)\n\n"
            + ("\n".join(lines) if lines else "No jobs yet.") + "\n\n")
    sec = section(text)
    if sec:
        text = text[:sec[0]] + body + text[sec[1]:]
    else:
        # Right under the status block.
        head, sep, rest = text.partition("\n---\n")
        text = head + sep + "\n" + body + rest.lstrip("\n")
    hqpaths.guard_roadmap(ROADMAP)  # F17
    tmp = ROADMAP + ".tmp"
    open(tmp, "w", encoding="utf8").write(text)
    os.replace(tmp, ROADMAP)


def waiting(j):
    return j["state"] == "ready" or j["state"].startswith("held")


def line_up(jobs):
    """H39: the waiting jobs, in the order they will run (top of the list first)."""
    return [j for j in jobs if waiting(j)]


def one_line(s):
    return " ".join(s.split())


def find(jobs, n):
    for j in jobs:
        if j["n"] == n:
            return j
    sys.exit(f"There is no job {n}.")


def show(j, place=None):
    at = f" · number {place} in line" if place else ""
    return f"Job {j['n']} · {j['state']}{PAST if j['past'] else ''}{at} · {j['text']}"


def show_all(jobs):
    places = {j["n"]: i + 1 for i, j in enumerate(line_up(jobs))}
    return "\n".join(show(j, places.get(j["n"])) for j in jobs) or "No jobs yet."


def estimate(fn, *a):
    """H61: the estimates (routine/estimate.py). Never in the way of the queue itself: a failure is only said."""
    try:
        import estimate as est
        return getattr(est, fn)(*a)
    except Exception as e:
        print(f"(The estimate couldn't be written: {e})", file=sys.stderr)
        return None


def gate_words():
    """H141: (job number, why it waits) from the routine's last start check, in plain words; (None, "") if none."""
    try:
        n, _, why = open(GATE_NOTE).read().strip().partition(" ")
    except OSError:
        return None, ""
    why = why.strip()
    why = why[4:].strip(" .:") + "." if why.upper().startswith("STOP") else why
    return (int(n), why) if n.isdigit() and why else (None, "")


def with_estimates(jobs):
    """H61: the list as on the roadmap, each job with its estimate, then the total and how close they've been."""
    places = {j["n"]: i + 1 for i, j in enumerate(line_up(jobs))}
    try:
        import estimate as est
        p = est.plan()
    except Exception:
        return show_all(jobs)
    lines = []
    gn, why = gate_words()
    for j in jobs:
        w = est.words(j["n"], p)
        lines.append(show(j, places.get(j["n"])) + (f"\n    Estimate: {w}" if w else "")
                     + (f"\n    Waits for the usage line: {why}" if j["n"] == gn and waiting(j) and p.get("on") else ""))
    lines.append(est.total_words(p))
    lines.append(est.accuracy_words(p["accuracy"]))
    lines.extend(p.get("learned") or [])  # H81: which computer, how the two compare, the patterns
    return "\n".join(lines) if jobs else "No jobs yet."


def move(jobs, n, where, other=None):
    """H39: move waiting job n within the line; the rest of the list keeps its order."""
    line = line_up(jobs)
    j = find(jobs, n)
    if j not in line:
        sys.exit(f"Job {n} is {j['state']}; only a waiting job can be moved.")
    i = line.index(j)
    line.remove(j)
    if where == "top":
        k = 0
    elif where == "bottom":
        k = len(line)
    elif where == "up":
        k = max(i - 1, 0)
    elif where == "down":
        k = min(i + 1, len(line))
    elif where in ("before", "after"):
        if other is None:
            sys.exit(f"Move job {n} {where} which job? For example: move {n} {where} 27")
        if other == n:
            sys.exit("A job can't move before or after itself.")
        o = find(jobs, other)
        if o not in line:
            sys.exit(f"Job {other} is {o['state']}; it isn't waiting, so there's no place next to it.")
        k = line.index(o) + (where == "after")
    else:
        sys.exit("Move it where? top, up, down, bottom, before M or after M.")
    line.insert(k, j)
    return [x for x in jobs if not waiting(x)] + line


def main(argv):
    global MAIL
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, args = argv[0], argv[1:]
    # H56.3: on the backup HQ, a call's change to the queue goes to the main one as a request, so only
    # one HQ ever writes it. HQ_ROLE_HERE is set when the main runs such a request itself.
    import role
    if cmd in role.WRITES["jobs"] and not os.environ.get("HQ_ROLE_HERE") and role.is_backup():
        sys.exit(role.forward("jobs", list(argv)))
    now = time.strftime("%H:%M")
    with locked():
        text, jobs, on = read()
        if cmd == "list":
            print(f"Routine: {'on' if on else 'off'}")
            print(with_estimates(jobs))
            return
        if cmd == "next":
            ready = [j for j in jobs if j["state"] == "ready"]
            running = [j for j in jobs if j["state"].startswith(("running", "stop asked"))]
            # H39: "waiting" is the line itself, ready and held together, top first; the routine takes its first.
            print(json.dumps({"on": on, "mail": MAIL, "running": running, "ready": ready,
                              "held": [j for j in jobs if j["state"].startswith("held")], "waiting": line_up(jobs)}))
            return
        if cmd == "add":
            past = "--past-the-line" in args
            words = [a for a in args if a != "--past-the-line"]
            kind = None  # H70: the kind for its estimate, given by the call; wins over the guess
            for i, a in enumerate(words):
                if a == "--kind" or a.startswith("--kind="):
                    kind = a.split("=", 1)[1] if "=" in a else (words[i + 1] if i + 1 < len(words) else "")
                    words = words[:i] + words[i + (1 if "=" in a else 2):]
                    break
            if kind is not None:
                kind = kind.strip().lower()
                import estimate as est_
                if kind not in est_.KINDS:
                    sys.exit(f"--kind is one of: {', '.join(est_.KINDS)}.")
            if not words or not one_line(" ".join(words)):
                sys.exit("What should the job do? Give it as one self-contained line.")
            n = max([j["n"] for j in jobs] + [0]) + 1
            j = {"n": n, "state": "ready", "past": past, "agreed": time.strftime("%Y-%m-%d %H:%M"),
                 "text": one_line(" ".join(words)).replace("·", "-")}
            jobs.append(j)
            write(text, jobs, on)
            e = estimate("on_add", n, j["text"], kind)
            waiting = [x for x in line_up(jobs) if x["n"] != n]
            busy = any(x["state"].startswith(("running", "stop asked")) for x in jobs)
            if not on:
                after = " The routine is off, so it waits until it's on."
            elif busy or waiting:
                after = f" It waits its turn: {int(busy)} running, {len(waiting)} waiting before it."
            else:
                after = " The routine starts it within about a minute."
            if e:
                after += f" Estimate: about {e['est']} min."
            print(f"Job {n} is ready.{after}")
            return
        if cmd in ("mail-on", "mail-off"):
            MAIL = cmd == "mail-on"
            write(text, jobs, on)
            print(f"The hourly mail check is {cmd[5:]}.")
            return
        if cmd in ("on", "off"):
            write(text, jobs, cmd == "on")
            print(f"The routine is {cmd}.")
            return
        if cmd == "stop":
            if args:
                j = find(jobs, int(args[0]))
            else:
                running = [x for x in jobs if x["state"].startswith("running")]
                if not running:
                    sys.exit("No job is running.")
                j = running[0]
            if j["state"].startswith("running"):
                j["state"] = "stop asked"
                msg = f"Job {j['n']}: stop asked; the routine ends it within about a minute."
            elif j["state"] in ("ready",) or j["state"].startswith(("held", "paused")):
                j["state"] = f"cancelled {now}"
                msg = f"Job {j['n']} cancelled; it won't start."
                try:  # H172: a held or paused job's usage count goes with it
                    import usagecost
                    usagecost.forget(j["n"])
                except Exception:
                    pass
            else:
                sys.exit(f"Job {j['n']} is {j['state']}; nothing to stop.")
            write(text, jobs, on)
            print(msg)
            return
        if cmd == "move":
            if len(args) < 2 or not args[0].isdigit() or (len(args) > 2 and not args[2].isdigit()):
                sys.exit("Usage: move N top|up|down|bottom, or move N before|after M")
            n = int(args[0])
            jobs = move(jobs, n, args[1], int(args[2]) if len(args) > 2 else None)
            write(text, jobs, on)
            place = [x["n"] for x in line_up(jobs)].index(n) + 1
            print(f"Job {n} is now number {place} in line. The line: "
                  + ", ".join(f"{i + 1}. job {x['n']}" for i, x in enumerate(line_up(jobs))))
            return
        if cmd == "overrule":
            j = find(jobs, int(args[0]))
            j["past"] = True
            if j["state"].startswith("held"):
                j["state"] = "ready"
            write(text, jobs, on)
            print(f"Job {j['n']} may go past the 5-hour usage line; the weekly line still counts.")
            return
        if cmd == "resume":
            # H172: he lets a job paused for its usage carry on: it waits in line again like a held job (its own
            # chat, H113) and isn't paused for its usage again.
            if not args or not args[0].isdigit():
                sys.exit("Usage: resume N")
            j = find(jobs, int(args[0]))
            if not j["state"].startswith("paused"):
                sys.exit(f"Job {j['n']} is {j['state']}; only a paused job can be resumed.")
            j["state"] = "held: usage over the line"
            write(text, jobs, on)
            try:
                import usagecost
                usagecost.allow(j["n"])
            except Exception as e:
                print(f"(couldn't note it may go on: {e!r})", file=sys.stderr)
            place = [x["n"] for x in line_up(jobs)].index(j["n"]) + 1
            print(f"Job {j['n']} carries on: number {place} in line, in its own chat, when the usage leaves room.")
            return
        if cmd in ("done", "held"):
            j = find(jobs, int(args[0]))
            was = j["state"]
            j["state"] = f"done {now}" if cmd == "done" else "held: usage over the line"
            write(text, jobs, on)
            print(show(j))
            if cmd == "held":
                # H113: when and at about which step, so the next start carries on from there.
                try:
                    import carryon
                    carryon.on_held(j["n"], text)
                except Exception as e:
                    print(f"(couldn't note the step for the carry-on: {e!r})", file=sys.stderr)
                try:  # H172: the usage the hold doesn't count
                    import usagecost
                    usagecost.hold(j["n"])
                except Exception as e:
                    print(f"(couldn't stop its usage count: {e!r})", file=sys.stderr)
            if cmd == "done" and not was.startswith("done"):
                # H61: its estimate next to how long it really took, so the next estimates learn.
                m = re.match(r"running since (\d\d:\d\d)", was)
                r = estimate("on_done", j["n"], j["text"], m.group(1) if m else None)
                if r:
                    print(f"Took {r['actual']} min" + (f"; the estimate was {r['est']} min." if r.get("est") else "."))
            return
        if cmd == "crashed":
            # H62: the Mac went down while job N ran. It ends by a crash and runs again from the top of the
            # line, with a note to pick up from what it left; once only (a rerun that crashes isn't queued again).
            j = find(jobs, int(args[0]))
            how = one_line(" ".join(args[1:])).replace("·", "-") or "the Mac went down"
            import crash
            if crash.is_rerun(j["text"]):
                j["state"] = f"ended {now} by a crash, again; not run again by itself"
                write(text, jobs, on)
                print(f"Job {j['n']} ended by a crash again ({how}); it was already a rerun, so it isn't queued again.")
                return
            n = max(x["n"] for x in jobs) + 1
            j["state"] = f"ended {now} by a crash; requeued as job {n}"
            new = {"n": n, "state": "ready", "past": j["past"], "agreed": time.strftime("%Y-%m-%d %H:%M"),
                   "text": (f"Rerun of job {j['n']}, which ended at {now} without a done mark because {how} (H62, "
                            "queued again by the routine). First look at what the first run left in HQ (git status, "
                            "the roadmap's row for it, the status page) and pick up from there instead of starting "
                            "over; nothing of it was committed unless git says so. Then the job as it was: "
                            + j["text"])}
            jobs.append(new)
            jobs = move(jobs, n, "top")
            write(text, jobs, on)
            try:  # H70: the rerun keeps the kind the first run had (a hand-set one too)
                import estimate as est_
                first_kind = (est_._load_state().get(str(j["n"])) or {}).get("kind")
            except Exception:
                first_kind = None
            estimate("on_add", n, new["text"], first_kind)
            print(f"Job {j['n']} ended by a crash; requeued as job {n}, number 1 in line.")
            return
        if cmd == "mark":
            j = find(jobs, int(args[0]))
            j["state"] = " ".join(args[1:]).replace("·", "-")
            write(text, jobs, on)
            print(show(j))
            if j["state"].startswith("running since"):
                estimate("on_start", j["n"], j["text"])  # H61: when it started
            return
    sys.exit(f"Unknown command {cmd!r}. See --help.")


if __name__ == "__main__":
    main(sys.argv[1:])
