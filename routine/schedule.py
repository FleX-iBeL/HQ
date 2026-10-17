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
(the weekly line always counts, F13). ", priority" before it (H99): the item has the priority tag. ", every day"
or ", every saturday" before that (H171): the item repeats.

The job list always goes first: every minute the routine runs "promote", which only does something when the
routine is on and no job runs or waits. Then the item whose time came first becomes a job at the bottom of the
queue (so it starts within the same minute), and the item says which job it became.

Looking back (H111, 13 October 2026; the user's words on the call of 13 October at 17:40: "it needs to look at
right now or previous time, not just right now"): an item is due from its time on, not only in that minute. Every
item whose time has passed while the job list, the usage or the routine being off held it back stays waiting,
and when the scheduler gets its turn they all run, one after another, earliest first. None is skipped or dropped.
Priority doesn't change: the job list still goes first, and only a tagged item (H99) goes ahead of it.

The priority tag (H99, 13 October 2026; the user's words on the call of 12 October at 22:40: "if we have things
in the scheduler we can give it like a priority tag. And then it has priority over the normal job list line. If
not, then the normal job list line has priority."): a tagged item whose time has come doesn't wait for the job
list. Once no job runs, it becomes a job first in line, ahead of the waiting jobs (after any tagged item that
went in before it), and starts within the same minute. A running job is never stopped for it.

Repeating items (H171, 16 October 2026; the user's words on the call of 16 October at 11:56: "Can we also set up
in such a way the scheduler? For example, stuff like this, that it just runs daily. So we don't have to add it every
day and we can maybe do weekly ... Scheduled not just one time, but recurring."): an item planned with --every day
(or --every saturday) plans its next one by itself the moment it becomes a job: a new waiting item with the same
work, the same priority tag, past-the-line and kind, at the next time after now (a day on, or a week on). One that
was held back for days doesn't pile up: only the next time ahead is planned. Cancelling the waiting one stops the
repeating; "every N off" stops it but keeps that one.

usage (from the workspace):
  python3 "routine/schedule.py" add "WHEN" "TEXT" [--past-the-line] [--kind K] [--priority] [--every R] [--guess MINUTES]   plan an item
        --guess MINUTES (H190): the call's own guess, kept apart from the first look's (started in the background)
        --priority: the priority tag (H99): at its time it goes ahead of the waiting jobs
        --every R (H171): it repeats: R is day (daily) or a weekday (saturday), or week (the weekday of WHEN)
        WHEN: 2026-10-13 15:00 · today 15:00 · tomorrow 9:30 · tuesday 15:00 (the next one) · 2:00 (the next
              one, today or tomorrow) · now. With --every a time that has passed today rolls on to the next one.
        K: what kind of work, for its estimate, as for a job (H95): transcribe, big, call, build, other
  python3 "routine/schedule.py" list                                  what's planned, with each item's estimate
                                                                      (H95), and what came of the earlier ones
  python3 "routine/schedule.py" cancel N                              cancel waiting item N
  python3 "routine/schedule.py" move N "WHEN"                         give waiting item N another day or time
  python3 "routine/schedule.py" priority N [off]                      tag waiting item N priority (H99), or take
                                                                      the tag off again
  python3 "routine/schedule.py" every N R|off                         make waiting item N repeat (H171), or stop
                                                                      the repeating and keep this one
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
    "minute. An item whose time passed while it waited is never skipped: they run one after another, earliest "
    "first (H111). Kept by the routine's schedule script; the lines are not edited by hand. A call can add, list, "
    "move and cancel items."
)
LINE = re.compile(r"^- Item (\d+) · (.+?) · at (\d{4}-\d\d-\d\d \d\d:\d\d) · added (\d{4}-\d\d-\d\d \d\d:\d\d) · (.*)$")
FMT = "%Y-%m-%d %H:%M"
KEEP_FINISHED = 20  # enough to look back on a couple of weeks of planned work
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
JOB_FINISHED = jobs.FINISHED
PRIORITY = ", priority"  # H99: the tag, written in the state, before ", past the line"
EVERY = re.compile(r", every (day|" + "|".join(DAYS) + r")$")  # H171: before ", priority"


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
                state = state[: -len(jobs.PAST)] if past else state
                prio = state.endswith(PRIORITY)
                state = state[: -len(PRIORITY)] if prio else state
                ev = EVERY.search(state)
                items.append({"n": int(m.group(1)), "state": state[: ev.start()] if ev else state,
                              "past": past, "priority": prio, "every": ev.group(1) if ev else None,
                              "at": m.group(3), "added": m.group(4), "text": m.group(5)})
    return items


def write(text, items):
    """The schedule section, written back right under the queue (or under the status block)."""
    finished = [i for i in items if i["state"] != "waiting"]
    drop = {i["n"] for i in finished[:-KEEP_FINISHED]} if len(finished) > KEEP_FINISHED else set()
    coming = sorted((i for i in items if i["state"] == "waiting"), key=lambda i: (i["at"], i["n"]))
    order = sorted(finished, key=lambda i: i["n"]) + coming
    lines = [f"- Item {i['n']} · {tags(i)} · at {i['at']} · added {i['added']} · {i['text']}"
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
    m = re.fullmatch(r"(?:at )?(\d{1,2}):(\d\d)", s)  # H171: a time alone: the next one, today or tomorrow
    if m and int(m.group(1)) <= 23 and int(m.group(2)) <= 59:
        base = now.replace(hour=int(m.group(1)), minute=int(m.group(2)))
        return base if base >= now else base + dt.timedelta(days=1)
    m = re.fullmatch(r"(\d{4}-\d\d-\d\d) (\d{1,2}):(\d\d)", s)
    if m:
        return dt.datetime.strptime(f"{m.group(1)} {int(m.group(2)):02d}:{m.group(3)}", FMT)
    m = re.fullmatch(r"(today|tomorrow|(?:next )?(?:" + "|".join(DAYS) + r")) (?:at )?(\d{1,2}):(\d\d)", s)
    if not m:
        sys.exit("When? Give a day and a time: 2026-10-13 15:00, today 15:00, tomorrow 9:30, tuesday 15:00, 2:00, or now.")
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


def tags(i):
    """The state as written: with the repeat (H171), the priority tag (H99) and past the line, when they're there."""
    ev = f", every {i['every']}" if i.get("every") else ""
    return f"{i['state']}{ev}{PRIORITY if i.get('priority') else ''}{jobs.PAST if i['past'] else ''}"


def rule(words, at=None):
    """H171: --every as said to the rule written down: day, or a weekday. week(ly) is the weekday of its time."""
    s = " ".join(words).strip().lower().removeprefix("every ").strip()
    if s in ("day", "daily", "days", "each day", "night", "nightly"):
        return "day"
    if s.rstrip("s") in DAYS:
        return s.rstrip("s")
    if s in ("week", "weekly") and at is not None:
        return DAYS[at.weekday()]
    sys.exit("Every what? day (daily), a weekday (saturday), or week (the weekday of its time).")


def next_at(at, every, now=None):
    """H171: the next time of a repeating item after now: a day or a week on from its time, as many times as it
    takes to be ahead (one that was held back for days plans only the next one, it doesn't pile up). A weekday
    rule first goes to that weekday."""
    now = (now or dt.datetime.now()).replace(second=0, microsecond=0)
    d = dt.datetime.strptime(at, FMT) if isinstance(at, str) else at
    if every != "day":
        d += dt.timedelta(days=(DAYS.index(every) - d.weekday()) % 7)
    step = dt.timedelta(days=1 if every == "day" else 7)
    while d <= now:
        d += step
    return d


def say_every(every):
    return "every day" if every == "day" else f"every {every.capitalize()}"


def repeats(i, now=None):
    """H171: in words, for list and a call: it repeats, and when the one after this one is."""
    if not i.get("every"):
        return ""
    after = next_at(i["at"], i["every"], max(now or dt.datetime.now(), dt.datetime.strptime(i["at"], FMT)))
    return f" · repeats {say_every(i['every'])}, the one after: {say_when(after.strftime(FMT))}"


def due(item, now=None):
    """H111: due from its time on, also long after it (while the job list or the usage held it back), never
    only in that minute."""
    return item["state"] == "waiting" and item["at"] <= (now or dt.datetime.now()).strftime(FMT)


def show(i, now=None):
    state = i["state"]
    if due(i, now):
        state = ("due, goes first in line once no job runs" if i.get("priority")
                 else "due, waits for the job list to be empty")
    return (f"Item {i['n']} · {say_when(i['at'])} · {state}{PRIORITY if i.get('priority') else ''}"
            f"{jobs.PAST if i['past'] else ''}{repeats(i, now)} · {i['text']}")


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


def passed(items, now=None):
    """H111: the waiting items whose time has come, in the order they run: tagged first (H99), then the
    earliest time first."""
    now = now or dt.datetime.now()
    return sorted((i for i in items if due(i, now)), key=lambda i: (not i.get("priority"), i["at"], i["n"]))


def promote():
    """The routine, every minute. A due item with the priority tag (H99): once no job runs, it becomes a job
    first in line, ahead of the waiting jobs (after the tagged ones that went in before it). Any other item:
    only when the routine is on and no job runs or waits, the item whose time came first becomes a job.
    Returns what it did, as one line (empty when nothing)."""
    with jobs.locked():
        text, queue, on = jobs.read()
        items = read(text)
        changed = sync(items, queue)
        # F37: a parked job (paused for its usage) is neither running nor waiting, so nothing waits on it.
        running = any(jobs.open_job(j) and not jobs.waiting(j) for j in queue)
        busy = any(jobs.open_job(j) for j in queue)
        now = dt.datetime.now()
        ready = passed(items, now)  # H111: every item whose time has passed, not only this minute's
        did = ""
        item = ready[0] if ready else None
        if on and item and (not busy or (item.get("priority") and not running)):
            n = max([j["n"] for j in queue] + [0]) + 1
            job = {"n": n, "state": "ready", "past": item["past"], "agreed": time.strftime("%Y-%m-%d %H:%M"),
                   "text": f"Scheduled item {item['n']}, planned for {say_when(item['at'])}: {item['text']}"}
            if item.get("priority"):
                # H99: first in line, after the waiting jobs that came from tagged items before it.
                tagged = {int(m.group(1)) for i in items if i.get("priority")
                          for m in [re.match(r"started as job (\d+)", i["state"])] if m}
                line = jobs.line_up(queue)
                k = 0
                while k < len(line) and line[k]["n"] in tagged:
                    k += 1
                line.insert(k, job)
                queue = [x for x in queue if not jobs.waiting(x)] + line
            else:
                queue.append(job)
            jobs.write(text, queue, on)
            k = max(i["n"] for i in items) + 1  # H171: a repeating item's next one; its estimate first, before
            if item.get("every"):                # item_on_job forgets this one's
                estimate("item_repeat", item["n"], k, item["text"])
            estimate("item_on_job", item["n"], item["text"], n, job["text"])  # H95: its kind goes with it
            text = open(jobs.ROADMAP, encoding="utf8").read()
            item["state"] = f"started as job {n} at {time.strftime('%H:%M')}"
            changed = True
            did = f"item {item['n']} became job {n}" + (", first in line (priority)" if item.get("priority") else "")
            if item.get("every"):  # H171: the next one, planned by itself, with everything it carried
                nxt = {**item, "n": k, "state": "waiting", "at": next_at(item["at"], item["every"], now).strftime(FMT),
                       "added": time.strftime(FMT)}
                item["every"] = None  # the repeat goes on with the new one
                items.append(nxt)
                did += f"; it repeats {say_every(nxt['every'])}: item {k} is the next one, {say_when(nxt['at'])}"
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
    prio = [i for i in coming if i.get("priority") and due(i, now)]
    if prio and on:
        # H99: a tagged item goes ahead of the waiting jobs, but never stops a running one.
        return {"state": "ok", "text": f"Item {prio[0]['n']} is due with priority; goes first once no job runs",
                "next": None}
    rp = f", repeats {say_every(first['every'])}" if first.get("every") else ""  # H171
    if due(first, now):
        why = "the routine is off" if not on else "the job list goes first"
        more = len(passed(items, now)) - 1  # H111: the others whose time passed wait their turn, none skipped
        more = f", {more} more after it, earliest first" if more > 0 else ""
        # Waiting for the job list is how it's meant to work, so it's not shown as a warning.
        return {"state": "ok", "text": f"Item {first['n']} is due{more}; waits: {why}", "next": None}
    at = dt.datetime.strptime(first["at"], FMT)
    more = f", {len(coming) - 1} more after it" if len(coming) > 1 else ""
    return {"state": "ok", "text": f"Next: item {first['n']}, {say_when(first['at'])}{rp}{more}", "next": at.timestamp()}


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
            try:  # H107: the planned items' total, as jobs.py list ends with the job list's
                tw = est.items_total_words(p) if p and coming else ""
            except Exception:
                tw = ""
            if tw:
                print(tw)
            print("Looking back:\n" + ("\n".join(show(i) for i in reversed(done)) or "Nothing yet."))
            return
        if cmd == "add":
            past = "--past-the-line" in args
            rest, kind, every, skip, guess = [], None, None, False, None
            for k, a in enumerate(args):  # H95: --kind for its estimate, as for a job (H70)
                if skip:
                    skip = False
                elif a == "--kind" or a.startswith("--kind="):
                    kind = a.split("=", 1)[1] if "=" in a else (args[k + 1] if k + 1 < len(args) else "")
                    skip = "=" not in a
                elif a == "--guess" or a.startswith("--guess="):  # H190: the call's own guess
                    guess = a.split("=", 1)[1] if "=" in a else (args[k + 1] if k + 1 < len(args) else "")
                    skip = "=" not in a
                elif a == "--every" or a.startswith("--every="):  # H171
                    every = a.split("=", 1)[1] if "=" in a else (args[k + 1] if k + 1 < len(args) else "")
                    skip = "=" not in a
                elif a not in ("--past-the-line", "--priority"):
                    rest.append(a)
            if kind is not None:
                kind = kind.strip().lower()
                import estimate as est_
                if kind not in est_.KINDS:
                    sys.exit(f"--kind is one of: {', '.join(est_.KINDS)}.")
            if guess is not None:
                import estimate as est_
                if not re.fullmatch(r"\d+", guess.strip()) or not 1 <= int(guess) <= est_.GUESS_MAX:
                    sys.exit(f"--guess is whole minutes, between 1 and {est_.GUESS_MAX}.")
                guess = int(guess)
            if len(rest) < 2 or not jobs.one_line(" ".join(rest[1:])):
                sys.exit('Usage: add "WHEN" "TEXT" [--past-the-line] [--kind K] [--priority] [--every R], for example: add "tuesday 15:00" "Build ..." --kind build')
            at = when(rest[0].split())
            if every is not None:  # H171: a repeating item starts at its first time ahead (a weekday: that day)
                every = rule(every.split(), at)
                if every != "day" or at < dt.datetime.now().replace(second=0, microsecond=0) - dt.timedelta(minutes=1):
                    at = next_at(at, every, dt.datetime.now() - dt.timedelta(minutes=1))
            if at < dt.datetime.now().replace(second=0, microsecond=0) - dt.timedelta(minutes=1):
                sys.exit(f"{say_when(at.strftime(FMT))} has already passed. Give a time ahead, or now.")
            n = max([i["n"] for i in items] + [0]) + 1
            prio = "--priority" in args
            item = {"n": n, "state": "waiting", "past": past, "priority": prio, "every": every, "at": at.strftime(FMT),
                    "added": time.strftime(FMT), "text": jobs.one_line(" ".join(rest[1:])).replace("·", "-")}
            items.append(item)
            write(text, items)
            estimate("item_on_add", n, item["text"], kind, guess)
            looks = estimate("look_later", "item", n, item["text"])  # H190: the first look, in the background
            busy = any(jobs.open_job(j) for j in queue)  # F37: a parked job doesn't count
            after = (" Its time has come; it starts once the job list is empty." if due(item)
                     else " It starts then, once the job list is empty.")
            if prio:  # H99
                after = (" It has priority: its time has come, so it goes first in line once no job runs."
                         if due(item) else " It has priority: at its time it goes ahead of the waiting jobs.")
            if not on:
                after += " The routine is off right now."
            elif due(item) and not busy:
                after = " Its time has come; it starts within about a minute."
            try:  # H95: its estimate, as a job gets when it's added
                import estimate as est
                w = est.item_words(n, est.plan())
            except Exception:
                w = ""
            rp = f" It repeats {say_every(every)}: each time it becomes a job, the next one is planned by itself." if every else ""
            lk = " A first look at it is on its way." if looks else ""
            print(f"Item {n} is planned for {say_when(item['at'])}.{after}{rp}{lk}" + (f"\nEstimate: {w}" if w else ""))
            return
        if cmd in ("cancel", "move", "priority", "every"):
            if not args or not args[0].isdigit():
                sys.exit(f"Usage: {cmd} N" + (' "WHEN"' if cmd == "move" else " [off]" if cmd == "priority"
                                              else " day|saturday|off" if cmd == "every" else ""))
            i = find(items, int(args[0]))
            if i["state"] != "waiting":
                verb = {"cancel": "cancelled", "move": "moved", "priority": "tagged", "every": "made to repeat"}[cmd]
                sys.exit(f"Item {i['n']} isn't waiting any more ({i['state']}); only a waiting item can be {verb}.")
            if cmd == "priority":  # H99: the tag, on (default) or off
                on_ = (args[1].lower() if len(args) > 1 else "on") not in ("off", "no", "remove")
                i["priority"] = on_
                write(text, items)
                print(f"Item {i['n']} has priority now: at its time it goes ahead of the waiting jobs." if on_
                      else f"Item {i['n']} has no priority tag now: it waits for the job list, as usual.")
                return
            if cmd == "every":  # H171: make it repeat, or stop the repeating and keep this one
                if len(args) < 2:
                    sys.exit("Every what? day, a weekday (saturday), week, or off.")
                if args[1].lower() in ("off", "no", "stop", "none"):
                    i["every"] = None
                    write(text, items)
                    print(f"Item {i['n']} doesn't repeat any more; this one still runs at {say_when(i['at'])}.")
                    return
                i["every"] = rule(args[1:], dt.datetime.strptime(i["at"], FMT))
                d = dt.datetime.strptime(i["at"], FMT)
                if i["every"] != "day" and DAYS[d.weekday()] != i["every"]:
                    i["at"] = next_at(d, i["every"], dt.datetime.now() - dt.timedelta(minutes=1)).strftime(FMT)
                write(text, items)
                print(f"Item {i['n']} repeats {say_every(i['every'])} now; the first one is {say_when(i['at'])}.")
                return
            if cmd == "cancel":
                rp = " The repeating stops with it." if i.get("every") else ""  # H171
                i["state"] = f"cancelled {time.strftime('%H:%M')}"
                i["every"] = None
                write(text, items)
                estimate("item_forget", i["n"])
                print(f"Item {i['n']} cancelled; it won't start.{rp}")
                return
            if len(args) < 2:
                sys.exit('Move it to when? For example: move 3 "wednesday 10:00"')
            at = when(args[1].split())
            if at < dt.datetime.now().replace(second=0, microsecond=0) - dt.timedelta(minutes=1):
                sys.exit(f"{say_when(at.strftime(FMT))} has already passed. Give a time ahead, or now.")
            i["at"] = at.strftime(FMT)
            rp = ""
            if i.get("every"):  # H171: a weekly one follows its new day; the times after it follow its new time
                if i["every"] != "day":
                    i["every"] = DAYS[at.weekday()]
                rp = f" It repeats {say_every(i['every'])} from there."
            write(text, items)
            print(f"Item {i['n']} is now planned for {say_when(i['at'])}.{rp}")
            return
    sys.exit(f"Unknown command {cmd!r}. See --help.")


if __name__ == "__main__":
    main(sys.argv[1:])
