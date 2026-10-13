#!/usr/bin/env python3
"""The scheduler (H43, 10 October 2026): work planned ahead for a day and a time, next to the queue.

In the user's words (call of 10 October 2026, 19:13): "A scheduler that we can schedule things out ahead
into the future of the week. And then we know, for example, on Tuesday, we want to have something done at
3 p.m. It goes there and then we also have a routine that checks that besides the job list, the job list
will have priority. But then if there's no jobs on the job list, then the scheduler will also. If there is
something, it will run that."

It lives in roadmap.md, in the section "## The schedule" right under the queue. One line per item:

    - Item 3 · waiting · at 2026-10-13 15:00 · added 2026-10-10 22:40 · <what to do, self-contained>

States: waiting (its time hasn't come, or it has and it waits for the job list) · started as job 41 at
15:02 · job 41 done 15:40 (or stopped, ended, cancelled: how its job finished, for looking back) ·
cancelled 22:50. ", past the line" after the state: the job it becomes may go past the 5-hour usage line
(the weekly line always counts, F13).

The job list always goes first: every minute the routine runs "promote", which only does something when the
routine is on and no job runs or waits. Then the item whose time came first becomes a job at the bottom of the
queue (so it starts within the same minute), and the item says which job it became.

usage (from the workspace):
  python3 "routine/schedule.py" add "WHEN" "TEXT" [--past-the-line] [--kind K]   plan an item
        WHEN: 2026-10-13 15:00 · today 15:00 · tomorrow 9:30 · tuesday 15:00 (the next one) · now
        K: what kind of work, for its estimate, as for a job (H95): transcribe, big, call, build, other
  python3 "routine/schedule.py" list                                  what's planned, with each item's estimate
                                                                      (H95), and what came of the earlier ones
  python3 "routine/schedule.py" cancel N                              cancel waiting item N
  python3 "routine/schedule.py" move N "WHEN"                         give waiting item N another day or time
Used by the routine itself: promote (and status, for its routine line).
"""
import datetime as dt
import json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jobs  # the same roadmap, the same lock: promoting an item and the queue never cross

HEADING = "## The schedule"
INTRO = (
    "Work planned ahead for a day and a time (H43). The job list always goes first: when an item's time has "
    "come and no job runs or waits, the routine puts it in the queue as a job, and it starts within about a "
    "minute. Kept by the routine's schedule script; the lines are not edited by hand. A call can add, list, "
    "move and cancel items."
)
LINE = re.compile(r"^- Item (\d+) · (.+?) · at (\d{4}-\d\d-\d\d \d\d:\d\d) · added (\d{4}-\d\d-\d\d \d\d:\d\d) · (.*)$")
FMT = "%Y-%m-%d %H:%M"
KEEP_FINISHED = 20  # enough to look back on a couple of weeks of planned work
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
JOB_FINISHED = jobs.FINISHED


def section(text):
    """(start, end) of the schedule section, or None."""
    i = text.find("\n" + HEADING + "\n")
    if i < 0:
        return None
    i += 1
    j = text.find("\n# ", i)
    k = text.find("\n## ", i + len(HEADING))
    ends = [x for x in (j, k) if x >= 0]
    return i, (min(ends) + 1 if ends else len(text))


def read(text):
    items = []
    sec = section(text)
    if sec:
        for l in text[sec[0]:sec[1]].splitlines():
            m = LINE.match(l)
            if m:
                state = m.group(2)
                past = state.endswith(jobs.PAST)
                items.append({"n": int(m.group(1)), "state": state[: -len(jobs.PAST)] if past else state,
                              "past": past, "at": m.group(3), "added": m.group(4), "text": m.group(5)})
    return items


def write(text, items):
    """The schedule section, written back right under the queue (or under the status block)."""
    finished = [i for i in items if i["state"] != "waiting"]
    drop = {i["n"] for i in finished[:-KEEP_FINISHED]} if len(finished) > KEEP_FINISHED else set()
    coming = sorted((i for i in items if i["state"] == "waiting"), key=lambda i: (i["at"], i["n"]))
    order = sorted(finished, key=lambda i: i["n"]) + coming
    lines = [f"- Item {i['n']} · {i['state']}{jobs.PAST if i['past'] else ''} · at {i['at']} · added {i['added']} · {i['text']}"
             for i in order if i["n"] not in drop]
    body = f"{HEADING}\n\n{INTRO}\n\n" + ("\n".join(lines) if lines else "Nothing planned yet.") + "\n\n"
    sec = section(text)
    if sec:
        text = text[:sec[0]] + body + text[sec[1]:]
    else:
        q = jobs.section(text)
        if q:
            text = text[:q[1]] + body + text[q[1]:]
        else:
            head, sep, rest = text.partition("\n---\n")
            text = head + sep + "\n" + body + rest.lstrip("\n")
    jobs.hqpaths.guard_roadmap(jobs.ROADMAP)  # F17
    tmp = jobs.ROADMAP + ".tmp"
    open(tmp, "w", encoding="utf8").write(text)
    os.replace(tmp, jobs.ROADMAP)
    return text


def when(words, now=None):
    """A day and a time, as a call would give it, to a datetime (minutes, local time)."""
    now = (now or dt.datetime.now()).replace(second=0, microsecond=0)
    s = " ".join(words).strip().lower()
    if s == "now":
        return now
    m = re.fullmatch(r"(\d{4}-\d\d-\d\d) (\d{1,2}):(\d\d)", s)
    if m:
        return dt.datetime.strptime(f"{m.group(1)} {int(m.group(2)):02d}:{m.group(3)}", FMT)
    m = re.fullmatch(r"(today|tomorrow|(?:next )?(?:" + "|".join(DAYS) + r")) (?:at )?(\d{1,2}):(\d\d)", s)
    if not m:
        sys.exit("When? Give a day and a time: 2026-10-13 15:00, today 15:00, tomorrow 9:30, tuesday 15:00, or now.")
    day, h, mi = m.group(1), int(m.group(2)), int(m.group(3))
    if h > 23 or mi > 59:
        sys.exit(f"{h}:{mi:02d} isn't a time of day.")
    base = now.replace(hour=h, minute=mi)
    if day == "today":
        return base
    if day == "tomorrow":
        return base + dt.timedelta(days=1)
    want = DAYS.index(day.replace("next ", ""))
    ahead = (want - now.weekday()) % 7
    if ahead == 0 and (base <= now or day.startswith("next ")):
        ahead = 7  # the same weekday, but its time has passed today (or "next" was said): a week on
    return base + dt.timedelta(days=ahead)


def say_when(at):
    """2026-10-13 15:00 -> Tuesday 13 October, 15:00."""
    d = dt.datetime.strptime(at, FMT)
    return f"{d.strftime('%A')} {d.day} {d.strftime('%B')}, {d.strftime('%H:%M')}"


def due(item, now=None):
    return item["state"] == "waiting" and item["at"] <= (now or dt.datetime.now()).strftime(FMT)


def show(i, now=None):
    state = i["state"]
    if due(i, now):
        state = "due, waits for the job list to be empty"
    return f"Item {i['n']} · {say_when(i['at'])} · {state}{jobs.PAST if i['past'] else ''} · {i['text']}"


def estimate(fn, *a):
    """H95: the planned items' estimates (routine/estimate.py), the same way the queue does it: never in
    the way of the schedule itself; a failure is only said."""
    return jobs.estimate(fn, *a)


def with_estimate(i, p):
    """A planned item with its estimate under it (H95), as jobs.py list does for jobs."""
    try:
        import estimate as est
        w = est.item_words(i["n"], p) if p else ""
    except Exception:
        w = ""
    return show(i) + (f"\n    Estimate: {w}" if w else "")


def find(items, n):
    for i in items:
        if i["n"] == n:
            return i
    sys.exit(f"There is no item {n}.")


def sync(items, queue):
    """An item that became a job takes over how its job finished, so it can be looked back on."""
    by_n = {j["n"]: j for j in queue}
    changed = False
    for i in items:
        m = re.match(r"started as job (\d+)", i["state"])
        if m and int(m.group(1)) in by_n:
            st = by_n[int(m.group(1))]["state"]
            if st.startswith(JOB_FINISHED):
                i["state"] = f"job {m.group(1)} {st}"
                changed = True
    return changed


def promote():
    """The routine, every minute: only when the routine is on and no job runs or waits, the item whose
    time came first becomes a job. Returns what it did, as one line (empty when nothing)."""
    with jobs.locked():
        text, queue, on = jobs.read()
        items = read(text)
        changed = sync(items, queue)
        busy = any(not j["state"].startswith(JOB_FINISHED) for j in queue)
        now = dt.datetime.now()
        ready = sorted((i for i in items if due(i, now)), key=lambda i: (i["at"], i["n"]))
        did = ""
        if on and not busy and ready:
            item = ready[0]
            n = max([j["n"] for j in queue] + [0]) + 1
            queue.append({"n": n, "state": "ready", "past": item["past"], "agreed": time.strftime("%Y-%m-%d %H:%M"),
                          "text": f"Scheduled item {item['n']}, planned for {say_when(item['at'])}: {item['text']}"})
            jobs.write(text, queue, on)
            estimate("item_on_job", item["n"], item["text"], n, queue[-1]["text"])  # H95: its kind goes with it
            text = open(jobs.ROADMAP, encoding="utf8").read()
            item["state"] = f"started as job {n} at {time.strftime('%H:%M')}"
            changed = True
            did = f"item {item['n']} became job {n}"
        if changed:
            write(text, items)
        return did


def status():
    """For the routine line: what's next, or what's due and waiting."""
    text, queue, on = jobs.read()
    items = read(text)
    now = dt.datetime.now()
    coming = sorted((i for i in items if i["state"] == "waiting"), key=lambda i: (i["at"], i["n"]))
    if not coming:
        return {"state": "ok", "text": "Nothing planned; looks every minute", "next": None}
    first = coming[0]
    if due(first, now):
        why = "the routine is off" if not on else "the job list goes first"
        # Waiting for the job list is how it's meant to work, so it's not shown as a warning.
        return {"state": "ok", "text": f"Item {first['n']} is due; waits: {why}", "next": None}
    at = dt.datetime.strptime(first["at"], FMT)
    more = f", {len(coming) - 1} more after it" if len(coming) > 1 else ""
    return {"state": "ok", "text": f"Next: item {first['n']}, {say_when(first['at'])}{more}", "next": at.timestamp()}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, args = argv[0], argv[1:]
    # H56.3: on the backup HQ, a call's change to the schedule goes to the main one as a request, so only
    # one HQ ever writes it. HQ_ROLE_HERE is set when the main runs such a request itself.
    import role
    if cmd in role.WRITES["schedule"] and not os.environ.get("HQ_ROLE_HERE") and role.is_backup():
        sys.exit(role.forward("schedule", list(argv)))
    if cmd == "promote":
        did = promote()
        print(did or "Nothing to start.")
        return
    if cmd == "status":
        print(json.dumps(status()))
        return
    with jobs.locked():
        text, queue, on = jobs.read()
        items = read(text)
        if cmd == "list":
            coming = sorted((i for i in items if i["state"] == "waiting"), key=lambda i: (i["at"], i["n"]))
            done = [i for i in items if i["state"] != "waiting"]
            try:  # H95: each planned item's estimate
                import estimate as est
                p = est.plan()
            except Exception:
                p = None
            print("Planned:\n" + ("\n".join(with_estimate(i, p) for i in coming) or "Nothing planned."))
            print("Looking back:\n" + ("\n".join(show(i) for i in reversed(done)) or "Nothing yet."))
            return
        if cmd == "add":
            past = "--past-the-line" in args
            rest, kind, skip = [], None, False
            for k, a in enumerate(args):  # H95: --kind for its estimate, as for a job (H70)
                if skip:
                    skip = False
                elif a == "--kind" or a.startswith("--kind="):
                    kind = a.split("=", 1)[1] if "=" in a else (args[k + 1] if k + 1 < len(args) else "")
                    skip = "=" not in a
                elif a != "--past-the-line":
                    rest.append(a)
            if kind is not None:
                kind = kind.strip().lower()
                import estimate as est_
                if kind not in est_.KINDS:
                    sys.exit(f"--kind is one of: {', '.join(est_.KINDS)}.")
            if len(rest) < 2 or not jobs.one_line(" ".join(rest[1:])):
                sys.exit('Usage: add "WHEN" "TEXT" [--past-the-line] [--kind K], for example: add "tuesday 15:00" "Build ..." --kind build')
            at = when(rest[0].split())
            if at < dt.datetime.now().replace(second=0, microsecond=0) - dt.timedelta(minutes=1):
                sys.exit(f"{say_when(at.strftime(FMT))} has already passed. Give a time ahead, or now.")
            n = max([i["n"] for i in items] + [0]) + 1
            item = {"n": n, "state": "waiting", "past": past, "at": at.strftime(FMT),
                    "added": time.strftime(FMT), "text": jobs.one_line(" ".join(rest[1:])).replace("·", "-")}
            items.append(item)
            write(text, items)
            estimate("item_on_add", n, item["text"], kind)
            busy = any(not j["state"].startswith(JOB_FINISHED) for j in queue)
            after = (" Its time has come; it starts once the job list is empty." if due(item)
                     else " It starts then, once the job list is empty.")
            if not on:
                after += " The routine is off right now."
            elif due(item) and not busy:
                after = " Its time has come; it starts within about a minute."
            try:  # H95: its estimate, as a job gets when it's added
                import estimate as est
                w = est.item_words(n, est.plan())
            except Exception:
                w = ""
            print(f"Item {n} is planned for {say_when(item['at'])}.{after}" + (f"\nEstimate: {w}" if w else ""))
            return
        if cmd in ("cancel", "move"):
            if not args or not args[0].isdigit():
                sys.exit(f"Usage: {cmd} N" + (' "WHEN"' if cmd == "move" else ""))
            i = find(items, int(args[0]))
            if i["state"] != "waiting":
                sys.exit(f"Item {i['n']} isn't waiting any more ({i['state']}); only a waiting item can be {'cancelled' if cmd == 'cancel' else 'moved'}.")
            if cmd == "cancel":
                i["state"] = f"cancelled {time.strftime('%H:%M')}"
                write(text, items)
                estimate("item_forget", i["n"])
                print(f"Item {i['n']} cancelled; it won't start.")
                return
            if len(args) < 2:
                sys.exit('Move it to when? For example: move 3 "wednesday 10:00"')
            at = when(args[1].split())
            if at < dt.datetime.now().replace(second=0, microsecond=0) - dt.timedelta(minutes=1):
                sys.exit(f"{say_when(at.strftime(FMT))} has already passed. Give a time ahead, or now.")
            i["at"] = at.strftime(FMT)
            write(text, items)
            print(f"Item {i['n']} is now planned for {say_when(i['at'])}.")
            return
    sys.exit(f"Unknown command {cmd!r}. See --help.")


if __name__ == "__main__":
    main(sys.argv[1:])
