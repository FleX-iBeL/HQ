#!/usr/bin/env python3
"""F102 (31 October 2026): a program holds the mail check to its own rules, and says when it stopped.

His words of 30 October 2026: "The mail list counts as stale when it hasn't been checked for 2 hours between 8:00 and midnight. Then
it turns red." The mail check is a model; the marker moving forward and the very important lines staying were only sentences in
its instructions. So the routine keeps the list as it stood at the run's start (`before`), and after the run (`after_run`) checks:
the marker didn't go backwards, every very important line is still there with its first three parts (date, sender, subject), and no
two lines share a key. Anything else: the old file back and an incident. A call or a text taking a line out during the run
(handover.py, loose_ends.py) calls `touched`, so that isn't counted against the run. `minute` keeps the line on the status page:
red when the last good run is over 2 hours ago between 8:00 and midnight.

F109 (1 November 2026): the Gmail connector began answering nothing to `after:<epoch seconds>`, so every run said nothing was new
and the marker stood still for days, with no failure anywhere. So the run gets its searches by date from here (`searches`),
one a day, because an answer stops at 50 threads without saying more are left. A date counts from midnight, so `newer` sorts out
what can't be new. And a good run that leaves the marker over 24 hours old opens an incident of its own, which Donna texts about.

F110 (3 November 2026): a day with more than 50 threads still lost mail: 120 in one day gave 79 found, and only the run's last
line said so. His words (1 November 2026): "i do want a fix that if we hit above the 50 emails we can still get alerts for
everything", and on the row (2 November): "yes rereading mail but also escalate to me and moneypenny through donna". So the run
hands every search it makes and its number of threads to `reach`; a search that answers 50 is capped (the connector gives no page
token and no total), and `reach` gives it two searches that split it (`X` and `-X`: every mail fits one of the two), deeper each
time, until each answers under 50. After the run the program reads what was really reached, not the model's last line: a day
with a search still at 50, or one not reported, isn't reached. Then the marker stays before that day, so the next run reads it
again (what's already written down isn't written twice: the check's own rules, and the guard above), and a good run opens the
incident `mailreach`, one per stretch, which Donna texts him about and hands to Moneypenny (`to`, app/direct_line.py watch);
the stuck-marker incident stays quiet about the same cause. The first good run that reaches all of it closes it.

    python3 routine/mailguard.py check BEFORE AFTER    what's wrong between two versions, one line each (none: it's fine)
    python3 routine/mailguard.py newer ID ID ...       which of these Gmail ids may be newer than the marker
    python3 routine/mailguard.py reach N "QUERY"       a search this run made and its number of threads: reached, or the
                                                       searches that split it (F110)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqlock  # noqa: E402
import hqpaths  # noqa: E402

RUN = os.environ.get("HQ_JOB_RUN") or os.path.join(hqpaths.HQ, "scratch", "routine")
STALE_S = 2 * 3600
HOURS = (8, 24)  # his words: between 8:00 and midnight
KEY = "maillist"
STUCK_KEY = "mailmarker"  # F109: its own incident: the two lines' rules for closing differ
STUCK_S = 24 * 3600  # his item: real mail never stops that long
EARLIEST_CLOCK = 12 * 3600  # the westernmost clock on earth: whichever zone a date counts from midnight in, this day starts in time
MOST_SEARCHES = 31
MARGIN_S = 600  # an id's time and the mail's own time differ by seconds
FIRST_MAIL = 1072915200  # 2004: an id that reads as earlier isn't a time
REACH_KEY = "mailreach"  # F110: its own incident, next to mailmarker
REACH_TO = "moneypenny"  # F110, his words: "escalate to me and moneypenny through donna"
CAP = 50  # an answer holds 50 threads at most and says nothing of the rest: 50 is capped
EASTMOST_CLOCK = 14 * 3600  # a date's midnight is at the earliest 14 hours before UTC's (Kiribati)
# F110: how a capped search is split, in this order, each as `X` and `-X`, so every mail fits one of the two halves. [Claude's
# pick: these are Gmail's own search words; whether the connector takes each of them couldn't be tried without reading his mail.]
SPLITS_FIRST = ("in:inbox", "is:unread", "has:attachment")
SPLITS_LAST = ("category:promotions", "category:updates", "category:social", "category:forums")
SIZE_START, SIZE_STEPS = 32, 5  # then by size, halving the range in K each step (larger:32K, then 8K or 128K, ...)
MOST_SPLITS = 80  # searches a run may add by splitting; past it, what's still capped waits for the next run [Claude's number]


def path() -> str:
    return os.path.join(hqpaths.FOLDER, "inbox.md")


def _before() -> str:
    return os.path.join(RUN, "inbox-before.md")


def _ok_file() -> str:
    return os.path.join(RUN, "mail-good")


def marker(text: str):
    m = re.search(r"^Marker:\s*(\d+)", text or "", re.M)
    return int(m.group(1)) if m else None


def very_important(text: str) -> list[str]:
    """The lines under "## Very important"."""
    m = re.search(r"^## Very important\s*$(.*?)(?=^## |\Z)", text or "", re.M | re.S)
    return [ln for ln in (m.group(1).splitlines() if m else []) if ln.startswith("- ")]


def key(line: str) -> str:
    """A line's first three parts: its date, sender and subject."""
    return " · ".join(p.strip() for p in line[2:].split(" · ")[:3])


def problems(old: str, new: str) -> list[str]:
    out = []
    a, b = marker(old), marker(new)
    if a is not None and (b is None or b < a):
        out.append(f"the marker went backwards ({a} to {b})")
    was, now = [key(x) for x in very_important(old)], [key(x) for x in very_important(new)]
    gone = [k for k in was if k not in now]
    if gone:
        out.append(f"{len(gone)} very important line(s) gone or changed: {gone[0][:120]}")
    twice = sorted({k for k in now if now.count(k) > 1})
    if twice:
        out.append(f"two lines share one key: {twice[0][:120]}")
    return out


def before() -> None:
    """The mail check starts: the list as it stands."""
    os.makedirs(RUN, exist_ok=True)
    try:
        shutil.copyfile(path(), _before())
    except OSError:
        pass


def touched(p=None) -> None:
    """Someone else changed the list during a run: what they left is what the run is held against."""
    if p is not None and os.path.realpath(os.fspath(p)) != os.path.realpath(path()):
        return
    if os.path.exists(_before()):
        before()


def after_run(ok: bool, incidents, routines, log=print) -> list[str]:
    """The run ended. Its result is checked against the list at its start; a bad one puts the old file back and opens an
    incident. Returns what was wrong."""
    b = _before()
    if not os.path.exists(b):
        if ok:
            open(_ok_file(), "w").write(str(int(time.time())))
        return []
    with hqlock.locked(path()):
        try:
            old, new = open(b, encoding="utf8").read(), open(path(), encoding="utf8").read()
        except OSError:
            return []
        bad = problems(old, new)
        if bad:
            tmp = hqlock.tmp(path())
            with open(tmp, "w", encoding="utf8") as f:
                f.write(old)
            os.replace(tmp, path())
            for p in (_plan_file(), _reach_file()):  # F110: its searches went with what it wrote
                try:
                    os.remove(p)
                except OSError:
                    pass
        else:
            _reach_after(ok, marker(old), incidents, routines, log=log)  # F110
        os.remove(b)
    if bad:
        why = "; ".join(bad)
        incidents.down(KEY, f"The mail check broke the list: {why}")
        incidents.fix(KEY, "Put the list back as it was before the run; the next run reads that mail again")
        routines.beat(KEY, state="down", text=f"The list was put back: {why}"[:200], every=60)
        log(f"mail list put back: {why}")
    elif ok:
        open(_ok_file(), "w").write(str(int(time.time())))
    return bad


def _read() -> str:
    try:
        return open(path(), encoding="utf8").read()
    except OSError:
        return ""


def _day(t: float) -> int:
    return int((t - EARLIEST_CLOCK) // 86400)


def _date(day: int) -> str:
    return time.strftime("%Y/%m/%d", time.gmtime(day * 86400))


def searches(text=None, now=None) -> list[str]:
    """F109: what this run searches: a day at a time from the marker's day, the last one open. With a marker very far back the days
    get wider, so a run never gets more than about a month of searches and no stretch of time is skipped. No marker: 7 days."""
    now = time.time() if now is None else now
    m = marker(_read() if text is None else text)
    first, last = _day(now - 7 * 86400 if m is None else min(m, now)), _day(now)
    step = (last - first) // MOST_SEARCHES + 1
    return [f"after:{_date(d)} before:{_date(min(d + step, last))}" for d in range(first, last, step)] + [f"after:{_date(last)}"]


def search_text() -> str:
    """The searches, for the run's instructions. F110: they're this run's plan too, what `reach` and the end of the run read."""
    text = _read()
    qs = searches(text)
    os.makedirs(RUN, exist_ok=True)
    _put(_plan_file(), {"searches": qs, "at": time.time(), "marker": marker(text)})  # the marker at the start: a hand change
    # during the run (touched) moves what the list is held against, not this
    _put(_reach_file(), {})
    _put(_open_file(), {})
    return "\n".join(f"   - `{q}`" for q in qs)


# -- F110: what the run really reached -------------------------------------------------------------------------------------

def _plan_file() -> str:
    return os.path.join(RUN, "mail-plan.json")


def _reach_file() -> str:
    return os.path.join(RUN, "mail-reach.json")


def _open_file() -> str:
    """When the open search (today's, no end) was first made: its halves come minutes later, so mail between isn't in either."""
    return os.path.join(RUN, "mail-reach-open.json")


def _misses_file() -> str:
    """How many good runs in a row didn't reach everything (kept across runs): the incident opens on the second."""
    return os.path.join(RUN, "mail-reach-misses.json")


def _put(p: str, data) -> None:
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(data, f)
    os.replace(tmp, p)


def _get(p: str):
    try:
        return json.load(open(p, encoding="utf8"))
    except (OSError, ValueError):
        return None


def _norm(q: str) -> str:
    return " ".join(str(q).replace("`", " ").split())


def _root(q: str, plan: list[str]):
    """The planned search a reported one belongs to: itself, or itself with the split words added."""
    for r in plan:
        if q == r or q.startswith(r + " "):
            return r
    return None


def _size_split(path: list[str]):
    """The next size word for this branch: the range in K halved on a log scale, or None when it's done."""
    lo = [int(t[7:-1]) for t in path if re.fullmatch(r"larger:\d+K", t)]
    hi = [int(t[8:-1]) for t in path if re.fullmatch(r"-larger:\d+K", t)]
    if len(lo) + len(hi) >= SIZE_STEPS:
        return None
    a, b = max(lo, default=None), min(hi, default=None)
    if a is None and b is None:
        k = SIZE_START
    elif b is None:
        k = a * 4
    elif a is None:
        k = max(1, b // 4)
    else:
        k = int(round((a * b) ** 0.5))
    if (a is not None and k <= a) or (b is not None and k >= b):
        return None
    return f"larger:{k}K"


def split_word(root: str, q: str):
    """The word that splits search q next (q is root with the words already added), or None when there's none left."""
    path = q[len(root):].split()
    used = {t.lstrip("-") for t in path}
    for w in SPLITS_FIRST:
        if w not in used:
            return w
    size = _size_split(path)
    if size:
        return size
    for w in SPLITS_LAST:
        if w not in used:
            return w
    return None


def children(root: str, q: str):
    w = split_word(root, q)
    return None if w is None else (f"{q} {w}", f"{q} -{w}")


def reach(n: int, query: str) -> str:
    """A search the run made and its number of threads (`reach N "QUERY"`): what the run does next, in a line or two."""
    q = _norm(query)
    plan = (_get(_plan_file()) or {}).get("searches") or []
    root = _root(q, plan)
    if root is None:
        return ("That isn't one of this run's searches. Search exactly as you were given them, and report each with the "
                "words it was searched with.")
    with hqlock.locked(_reach_file()):
        got = _get(_reach_file()) or {}
        got[q] = int(n)
        _put(_reach_file(), got)
        if q == root and "before:" not in root:
            first = _get(_open_file()) or {}
            if root not in first:
                first[root] = time.time()
                _put(_open_file(), first)
    if n < CAP:
        return "Reached: everything this search finds is in its answer."
    kids = children(root, q)
    if kids is None:
        return ("Not reached, and it can't be split any further: HQ says so after the run. Go on with the other searches.")
    asked = sum(1 for k in got if k not in plan)
    if asked + 2 > MOST_SPLITS:
        return ("Not reached, and this run has made all the extra searches it may; the next run reads this day again. "
                "Go on with the other searches.")
    return ("It holds 50 threads, so not all of it fits in one answer. Search these two too, each the same way (pageSize 50, "
            "the words exactly as here), and report each with this same command:\n" + "\n".join(f"- `{k}`" for k in kids))


def _node(root: str, q: str, got: dict) -> str | None:
    """Why search q isn't reached (None: it is)."""
    if q not in got:
        return f"the search {q} wasn't reported"
    n = got[q]
    if n < CAP:
        return None
    kids = children(root, q)
    if kids is None:
        return f"the search {q} still answers {CAP} threads and can't be split further"
    if not all(k in got for k in kids):
        return f"the search {q} answered {CAP} threads and wasn't split to the end"
    if sum(got[k] for k in kids) < n:
        return f"the two searches splitting {q} answered fewer threads than it did, so a split word didn't work"
    for k in kids:
        why = _node(root, k, got)
        if why:
            return why
    return None


def _first_day(root: str):
    m = re.match(r"after:(\d{4})/(\d\d)/(\d\d)", root)
    if not m:
        return None
    import calendar
    return calendar.timegm((int(m.group(1)), int(m.group(2)), int(m.group(3)), 0, 0, 0)) // 86400


def reached(plan: list[str] | None = None, got: dict | None = None) -> list[tuple[str, str]]:
    """F110: the planned searches the run didn't reach to the end, with why: [(search, why)]; [] when it reached all."""
    plan = (_get(_plan_file()) or {}).get("searches") or [] if plan is None else plan
    got = (_get(_reach_file()) or {}) if got is None else got
    out = []
    for r in plan:
        why = _node(r, r, got)
        if why:
            out.append((r, why))
    return out


def _day_words(root: str) -> str:
    d = _first_day(root)
    if d is None:
        return root
    m = re.search(r"before:(\S+)", root)
    first = time.strftime("%A %-d %B", time.gmtime(d * 86400))
    if m and _first_day("after:" + m.group(1)) not in (None, d + 1):
        return f"{first} to {time.strftime('%-d %B', time.gmtime((_first_day('after:' + m.group(1)) - 1) * 86400))}"
    return first if m else f"{first} up to now"


def _hold_marker(missed: list[tuple[str, str]], old_m) -> None:
    """The marker stays before the first day not reached, so the next run reads it again; never backwards."""
    days = [d for d in (_first_day(r) for r, _ in missed) if d is not None]
    if not days:
        return
    _hold_at(min(days) * 86400 - EASTMOST_CLOCK - MARGIN_S, old_m, f"{_day_words(missed[0][0])}, which isn't all read yet")


def _hold_open(plan: list[str], got: dict, old_m) -> None:
    """F110, the check's point 5: today's search was split, and its halves came minutes after it, so a mail that came in between
    is in neither. The marker goes no further than when that search was first made."""
    first = _get(_open_file()) or {}
    for r in plan:
        if "before:" not in r and r in first and any(k.startswith(r + " ") for k in got):
            _hold_at(int(first[r]) - MARGIN_S, old_m, "the moment today's search was split")


def _hold_at(upto, old_m, words: str) -> None:
    text = _read()
    m = marker(text)
    if m is None or m <= upto:
        return
    hold = max(upto, old_m) if old_m is not None else upto
    if hold >= m:
        return
    new = re.sub(r"^Marker:.*$", f"Marker: {hold} ({time.strftime('%-d %B %Y %H:%M', time.localtime(hold))}; held before "
                 f"{words})", text, count=1, flags=re.M)
    tmp = hqlock.tmp(path())
    with open(tmp, "w", encoding="utf8") as f:
        f.write(new)
    os.replace(tmp, path())


def _reach_after(ok: bool, old_m, incidents, routines, log=print) -> list[tuple[str, str]]:
    """The end of a run: what it didn't reach holds the marker; a good run opens or closes the incident from that. A failed run
    only holds the marker: its own incident says it failed."""
    started = _get(_plan_file()) or {}
    plan = started.get("searches")
    if not plan:
        return []  # a run started before F110, or a test of the list alone: nothing known about its searches
    if started.get("marker") is not None:
        old_m = started["marker"]
    got = _get(_reach_file()) or {}
    missed = reached(plan, got)
    if missed:
        _hold_marker(missed, old_m)
    _hold_open(plan, got, old_m)
    for p in (_plan_file(), _reach_file(), _open_file()):
        try:
            os.remove(p)
        except OSError:
            pass
    if not ok:
        return missed
    misses = ((_get(_misses_file()) or {}).get("n", 0) + 1) if missed else 0
    _put(_misses_file(), {"n": misses})
    if missed and misses < 2 and not incidents.is_down(REACH_KEY):
        # F110, the check's point 4: one miss alone (often a search the model didn't report) only holds the marker; the next run
        # reads that day again. The incident opens on the second good run in a row that misses, so he isn't texted down and back.
        day = _day_words(missed[0][0])
        routines.beat(REACH_KEY, state="ok", text=f"Not all of {day} read yet; the next run reads it again"[:200], every=60)
        log(f"mail check didn't reach {day} (first miss): {missed[0][1]}")
    elif missed:
        day = _day_words(missed[0][0])
        why = (f"The mail check couldn't read all the mail of {day}: {missed[0][1]}. So some mail of that day may not be read "
               "yet. The newest mail seen stays before that day, so every run reads it again until it gets all of it")
        was = incidents.is_down(REACH_KEY)
        incidents.down(REACH_KEY, why, to=REACH_TO)
        if not was:
            incidents.fix(REACH_KEY, "Held the newest mail seen before that day; every hourly run reads it again")
        routines.beat(REACH_KEY, state="down", text=f"Not all of {day} read yet: {missed[0][1]}"[:200], every=60)
        log(f"mail check didn't reach {day}: {missed[0][1]}")
    else:
        if incidents.is_down(REACH_KEY):
            incidents.up(REACH_KEY, what="A mail check read all of that day's mail, and the newest mail seen moved on")
        routines.beat(REACH_KEY, state="ok", text="Every search of the last run reached all its mail", every=60)
    return missed


def mail_time(mail_id: str):
    """When a mail came in by its Gmail id (the top of the number is milliseconds, seconds off the mail's own time), or None. Gmail
    doesn't promise this, so it only ever saves a read: what doesn't read as a time gets read."""
    try:
        t = (int(str(mail_id), 16) >> 20) / 1000
    except ValueError:
        return None
    return t if FIRST_MAIL <= t <= time.time() + 86400 else None


def maybe_newer(ids, text=None) -> list[str]:
    """F109: the ids a run has to read: the rest are clearly older than the marker. The mail's own time then decides."""
    m = marker(_read() if text is None else text)
    out = []
    for i in ids:
        t = mail_time(i)
        if (m is None or t is None or t >= m - MARGIN_S) and i not in out:
            out.append(i)
    return out


def _marker_minute(last, incidents, routines) -> None:
    """F109: the last good run left the marker over 24 hours old: no run failed, so nothing else says so. It counts from a good run,
    so a check that was off or down doesn't read as this; those have their own line."""
    m = marker(_read())
    if m is None or last - m < STUCK_S:
        incidents.up(STUCK_KEY, what="A good mail check moved the newest mail seen again")
        text = "No mail seen yet" if m is None else "Newest mail seen " + time.strftime("%d %B %H:%M", time.localtime(m))
        routines.beat(STUCK_KEY, state="ok", text=text, every=60)
        return
    if incidents.is_down(REACH_KEY) and not incidents.is_down(STUCK_KEY):
        # F110: the marker is held on purpose before a day not all read; that incident says so, and Donna texts once for it
        routines.beat(STUCK_KEY, state="ok", text="Held before a day not all read yet (the line Mail read in full)", every=60)
        return
    why = (f"The mail check has found no new mail since {time.strftime('%d %B %H:%M', time.localtime(m))}, "
           "and real mail never stops that long: the check itself may be blind")
    incidents.down(STUCK_KEY, why)
    routines.beat(STUCK_KEY, state="down", text=why[:200], every=60)


def last_good():
    try:
        return float(open(_ok_file()).read().strip())
    except (OSError, ValueError):
        return None


def in_hours(now=None) -> bool:
    pin = os.environ.get("HQ_WALL_HOUR") if hqpaths.under_test() else None
    h = int(pin) if pin else time.localtime(now).tm_hour
    return HOURS[0] <= h < HOURS[1]


def minute(on, incidents, routines, now=None) -> str:
    """Every minute on the main: the line on the status page. Off from a call: off. Nothing good yet: it starts counting."""
    now = now or time.time()
    if not on:
        routines.beat(KEY, state="off", text="The mail check is off", every=60)
        routines.beat(STUCK_KEY, state="off", text="The mail check is off", every=60)
        incidents.up(KEY, what="The mail check was turned off, so the list isn't watched")
        incidents.up(STUCK_KEY, what="The mail check was turned off, so the newest mail isn't watched")
        routines.beat(REACH_KEY, state="off", text="The mail check is off", every=60)
        incidents.up(REACH_KEY, what="The mail check was turned off, so no day is read again")
        return "off"
    last = last_good()
    if last is None:
        open(_ok_file(), "w").write(str(int(now)))
        last = now
    _marker_minute(last, incidents, routines)
    old = now - last
    if old > STALE_S and in_hours(now):
        why = f"Not checked for {int(old // 3600)} h {int(old % 3600 // 60)} min"
        incidents.down(KEY, why)
        routines.beat(KEY, state="down", text=why + ": the mail list is stale", every=60)
        return "stale"
    was = incidents.is_down(KEY)
    if was and not str(was.get("why", "")).startswith("The mail check broke") or (was and old < 3600):
        incidents.up(KEY, what="The mail list was checked again")
    routines.beat(KEY, state="ok", text="Checked " + time.strftime("%H:%M", time.localtime(last)), every=60)
    return "ok"


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[0] == "check":
        for p in problems(open(argv[1], encoding="utf8").read(), open(argv[2], encoding="utf8").read()):
            print(p)
        return 0
    if len(argv) >= 3 and argv[0] == "reach" and re.fullmatch(r"\d+", argv[1]):
        print(reach(int(argv[1]), " ".join(argv[2:])))
        return 0
    if argv[:1] == ["newer"]:
        print("\n".join(maybe_newer(argv[1:])) or "None of these can be newer than the marker")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
