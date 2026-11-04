#!/usr/bin/env python3
"""H62: after a crash, the job carries on (11 October 2026, call at 13:56). In the user's words: "when The HQ
starts, it checks first if it was because of a crash ... Doesn't run a new job, reorders the queue. It
communicates that it was a crash and see if it can pick up from where it left off. And it just continues."

Called by the routine (tick.py) when the running job's chat is gone without a done mark. It was a crash
when the Mac started again after the job had started (kern.boottime later than the job's start): a chat
can't outlive a restart, and a closed window or a chat that ended on its own leaves the boot time alone
(Claude's choice: the boot time is certain, a long heartbeat gap alone is sleep or a locked screen as
often as a crash). A panic report in /Library/Logs/DiagnosticReports written after the job's start says
it was a crash rather than a restart. Then:

- the job is marked "ended HH:MM by a crash" and a rerun is added, with the same text and a note to pick up
  from what the first run left (jobs.py crashed), at the top of the line, so no other job starts first;
- an incident says it was a crash, which job, and that it was queued again;
- the status block and the routine's log say so.

Never more than one automatic rerun: a job whose text already starts with "Rerun of job" (an automatic
rerun, or one queued by hand after a crash) that crashes too is not queued again; it says so, and the rest
of the line goes on (Claude's choice, so a job that brings the Mac down can't loop). The rerun goes through
the usage gate like any job.
"""
import glob, json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hqpaths  # noqa: E402

# H56.1: on Linux the boot time is btime in /proc/stat, and a kernel crash leaves its record in pstore
# (systemd-pstore moves it to /var/lib/systemd/pstore after the next start). No record there means
# "went down" (a restart or power loss), as on a Mac without a panic report.
PANIC_DIR = "/Library/Logs/DiagnosticReports" if hqpaths.IS_MAC else "/var/lib/systemd/pstore"
PANIC_GLOB = "*.panic" if hqpaths.IS_MAC else os.path.join("**", "*")
RERUN = re.compile(r"^Rerun of job \d+")


def boottime():
    return hqpaths.boottime()


def panic_after(since, folder=PANIC_DIR):
    """When macOS wrote a panic report (Linux: a crash record in pstore) after `since` (epoch), or None."""
    times = []
    for p in glob.glob(os.path.join(folder, PANIC_GLOB), recursive=True):
        if not os.path.isfile(p):
            continue
        try:
            t = os.path.getmtime(p)
        except OSError:
            continue
        if t >= since:
            times.append(t)
    return min(times) if times else None


def started_of(job, s, now=None):
    """When the job started: the routine's own note (job.json), else its "running since HH:MM" (today, or
    yesterday when that time is still to come)."""
    if s and s.get("n") == job["n"] and s.get("started"):
        return float(s["started"])
    m = re.match(r"running since (\d\d):(\d\d)", job.get("state", ""))
    if not m:
        return None
    now = now or time.time()
    lt = time.localtime(now)
    t = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, int(m.group(1)), int(m.group(2)), 0, 0, 0, -1))
    return t - 86400 if t > now + 60 else t


def went_down(job, s, boot=None, now=None):
    """The boot time when the Mac started again after this job had started, else None."""
    started = started_of(job, s, now)
    boot = boottime() if boot is None else boot
    return boot if started and boot > started else None


def is_rerun(text):
    return bool(RERUN.match(text or ""))


def clock(t):
    return time.strftime("%H:%M", time.localtime(t))


def recover(job, s, jobs, incidents, status, log, boot=None, panic_dir=PANIC_DIR, now=None):
    """The running job's chat is gone. Returns True when it was a crash and was dealt with here; False
    leaves it to the routine's usual "ended without a done mark"."""
    n = job["n"]
    now = now or time.time()
    boot = went_down(job, s, boot, now)
    if not boot:
        return False
    started = started_of(job, s, now)
    panic = panic_after(started, panic_dir)
    what = "the Mac" if hqpaths.IS_MAC else "the server"
    record = "macOS wrote a panic report" if hqpaths.IS_MAC else "the kernel left a crash record"
    how = (f"{what} crashed ({record}) and started again at {clock(boot)}" if panic
           else f"{what} went down and started again at {clock(boot)}")
    _requeue(job, how, boot, now, jobs, incidents, status, log)
    return True


def _requeue(job, how, since, now, jobs, incidents, status, log):
    """The crash's way back (jobs.py crashed): once, at the top of the line; an agent's own run only through her runner."""
    n = job["n"]
    out = jobs("crashed", str(n), how).strip()
    m = re.search(r"requeued as job (\d+)", out)
    if "only her runner" in out:  # H298
        what = "An agent's own run: her runner brings it back through her wall, or not at all"
        step = f"Job {n} stopped by a crash; an agent's run, it doesn't come back as a team job"
        line = f"job {n}: {how}; an agent's run, left to her runner"
    elif m:
        again = int(m.group(1))
        what = f"Queued it again as job {again}, at the top of the line, to pick up from where it left off"
        step = f"Job {n} stopped by a crash; it runs again as job {again}, first in line"
        line = f"job {n}: {how}; queued again as job {again}, at the top of the line, picks up where it left off"
    else:
        what = "It had already crashed once, so it isn't queued again by itself: queue it again from a call if you want"
        step = f"Job {n} crashed again; not run again by itself"
        line = f"job {n}: {how}; it was already a rerun, so it isn't queued again; the rest of the line goes on"
    item = (job.get("item") or {}).get("id")  # F103: on the item's record too, when the job has one
    incidents.past("jobs", since, now, f"Job {n} ended by a crash: {how}", [(now, what)], **({"item": item} if item else {}))
    status("STOPPED", step, line)
    log(line)


def hup_note(run_dir, n):
    """F138: the note runjob.py leaves when its window closed under it (SIGHUP) while the roadmap still said running."""
    return os.path.join(run_dir, f"job-{n}.hup")


def window_closed(job, s, jobs, incidents, status, log, run_dir, now=None):
    """F138: the running job's chat is gone because its window closed under it (the runner heard SIGHUP, nothing of the
    routine's asked it to stop): something outside the job ended it, as a crash would. Then the crash's way: run once again
    from the top of the line, picking up from what it left (Claude's pick for F138: the real HQ's way back for a run ended
    from outside, rather than leaving it). Returns True when dealt with here; False leaves it to the
    routine's usual "ended without a done mark"."""
    p = hup_note(run_dir, job["n"])
    try:
        note = json.load(open(p))
    except (OSError, ValueError):
        return False
    try:
        os.remove(p)
    except OSError:
        pass
    now = now or time.time()
    started = started_of(job, s, now) or 0
    at = float(note.get("at") or 0)
    if at < started - 60:  # an old note, from an earlier run of the same number
        return False
    _requeue(job, f"its window closed under it at {clock(at)} (signal {note.get('signal', 1)})", at, now, jobs, incidents, status, log)
    return True
