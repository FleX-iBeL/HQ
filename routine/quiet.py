"""H36: wake up a job that has gone quiet. Run by the HQ Routine helper (tick.py) every minute while a
job runs; no Claude, no usage.

10 October 2026 (call at 16:08): he went to the supermarket with the laptop and lost internet; job 15
stopped at about 15:55 and sat waiting in its window, while the status page still said BUILDING. In his
words: "Okay, but then can't we send a message in the terminal and try to... Can we configure it this way?"
On that call, typing continue into job 15's window woke it up. This does that by itself.

- A sign of life is: the job's status line ran (statusline.py writes job-activity.json after every reply and
  tool step), its transcript changed, or a tool is running under its chat (a test run, a background
  command). The job's start counts too.
- F57 (27 October 2026): the nudge names the job and the done mark ("You haven't marked job N done ..."), since a
  job that finished and said so in chat never ran `jobs.py done` (job 393, job 377, QA job 389). A shell under the
  chat (a tool "running") counts for 15 minutes after the chat's last step, then only while a background command
  keeps writing output; a wait loop that can never end no longer hides a finished job.
- Quiet: no sign of life for 10 minutes (Claude's choice: the longest normal gap seen between two steps is a
  few minutes, and a running tool always counts as alive).
- Quiet and no internet: wait, and say so (yellow). Typing continue only helps once the connection is back.
- Quiet and online: type continue into that job's own window, at most 3 times, 4 minutes apart.
- Still quiet after that: the status page shows the job as stuck (STOPPED), not BUILDING.
- Every nudge and its result go in the incident log under Routines (key "jobs").

The typing is done from inside the job's own window by routine/nudge.py, which the window starts next to
the chat (like closing the window, L7): a request from inside Terminal needs no macOS permission, and it
can only ever reach its own window (found by its tty). Nothing is stopped here, and no other window is
touched. Jobs started before H36 have no nudge.py in their window; then the request goes unanswered and
that is written down too.
"""
import json, os, subprocess, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
JV = os.path.normpath(os.path.join(HERE, ".."))
RUN = os.environ.get("HQ_NUDGE_DIR") or os.path.join(JV, "scratch", "routine")  # the env: for the happy flow
ACTIVITY = os.path.join(RUN, "job-activity.json")  # written by statusline.py: {"at", "session", "transcript"}
REQUEST = os.path.join(RUN, "nudge-request.json")  # {"n", "at", "text"}: read by nudge.py in job n's window
RESULT = os.path.join(RUN, "nudge-result.json")  # {"n", "at", "ok", "said"}: written by nudge.py

QUIET = 10 * 60
NUDGE_EVERY = 4 * 60
NUDGES = 3
NO_ANSWER = 2 * 60  # a request nudge.py hasn't picked up after this: the window has no nudge.py
TEXT = "continue"  # nudge.py's fallback when a request carries no text
BUSY_GRACE = 15 * 60  # F57: a shell under the chat counts as work this long after the chat's last step, then only with output


def nudge_text(n):
    """F57: the nudge names the job and the done mark. A bare "continue" only made job 393 say it was finished (it
    never ran the done mark) and go idle again, every eleven minutes, for over an hour."""
    jobs = os.path.join(HERE, "jobs.py")
    return (f"You haven't marked job {n} done. If its work is finished and checked, run python3 {json.dumps(jobs)} done {n} "
            "now: the status block first, the done mark as the very last step, nothing after it. If it isn't finished, "
            "carry on from where you were.")


def clock(t):
    return time.strftime("%H:%M", time.localtime(t))


def _mtime(p):
    try:
        return os.path.getmtime(p)
    except (OSError, TypeError):
        return 0


def activity():
    try:
        return json.load(open(ACTIVITY))
    except (OSError, ValueError):
        return {}


def is_claude_comm(comm):
    """The chat's process name: claude, or claude.exe for the native build on Linux (H56.2)."""
    return os.path.basename(comm.strip()) in ("claude", "claude.exe") or comm.strip().endswith("claude")


def claude_of(pid):
    """The chat (claude) in the job's window: the window's script itself (jobs before L7), or its child."""
    if not pid:
        return None
    r = subprocess.run(["/bin/ps", "-o", "comm=", "-p", str(pid)], capture_output=True, text=True)
    if is_claude_comm(r.stdout):
        return pid
    kids = subprocess.run(["/usr/bin/pgrep", "-P", str(pid)], capture_output=True, text=True).stdout.split()
    for k in kids:
        r = subprocess.run(["/bin/ps", "-o", "comm=", "-p", k], capture_output=True, text=True)
        if is_claude_comm(r.stdout):
            return int(k)
    return None


def busy(claude):
    """A tool is running under the chat: any child but caffeinate (Claude Code keeps that one all the time)
    and the MCP servers it starts at launch (those are older than a minute after the chat began)."""
    if not claude:
        return False
    r = subprocess.run(["/bin/ps", "-A", "-o", "pid=,ppid=,comm="], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[1] == str(claude) and not parts[2].strip().endswith("caffeinate"):
            if _tool_like(parts[2].strip()):
                return True
    return False


def _tool_like(comm):
    # The Bash tool runs commands through a shell; MCP servers are node or python processes started at
    # launch. A shell under the chat means a tool is running.
    return os.path.basename(comm).lstrip("-") in ("zsh", "bash", "sh")


def output_recent(session, now):
    """F57: a background command of the chat wrote output lately (Claude Code keeps each one's output in a file under
    /tmp/claude-<uid>/.../<session>/tasks)."""
    if not session:
        return False
    import glob
    for f in glob.glob(f"/tmp/claude-*/*/{session}/tasks/*.output"):
        if now - _mtime(f) < BUSY_GRACE:
            return True
    return False


def base_sign(s):
    """The job's last step of its own, in epoch seconds: its start, the status line, its transcript."""
    a = activity()
    at = a.get("at", 0) if a.get("at", 0) >= s.get("started", 0) else 0
    return max(s.get("started", 0), at, _mtime(a.get("transcript")) if at else 0)


def last_sign(s, claude, now=None):
    """The last sign of life of the running job, in epoch seconds. A shell under the chat counts as work (F57) only
    for 15 minutes after the chat's last step, or while its output keeps coming: a wait loop that never ends (a
    pgrep -f that finds itself) is no sign of life."""
    now = now or time.time()
    t = base_sign(s)
    if busy(claude) and (now - t < BUSY_GRACE or output_recent(activity().get("session"), now)):
        t = now
    return t


def online():
    """The internet is there: Anthropic's API answers anything at all (an error page counts)."""
    try:
        urllib.request.urlopen("https://api.anthropic.com/", timeout=6)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def decide(now, last, nudges, last_nudge, is_online):
    """What to do: "ok" (alive), "offline" (quiet, no internet: wait), "nudge", "wait" (between two
    nudges), or "stuck" (quiet after every nudge)."""
    if now - last < QUIET:
        return "ok"
    if not is_online:
        return "offline"
    if now - (last_nudge or 0) < NUDGE_EVERY:
        return "wait"
    return "nudge" if nudges < NUDGES else "stuck"


def request(n):
    tmp = REQUEST + ".tmp"
    json.dump({"n": n, "at": time.time(), "text": nudge_text(n)}, open(tmp, "w"))
    os.replace(tmp, REQUEST)


def result(n, since):
    """nudge.py's answer to the last request for job n, if it came after `since`."""
    try:
        r = json.load(open(RESULT))
    except (OSError, ValueError):
        return None
    return r if r.get("n") == n and r.get("at", 0) >= since else None


def pending(n):
    try:
        r = json.load(open(REQUEST))
    except (OSError, ValueError):
        return None
    return r if r.get("n") == n else None


def clear_request():
    try:
        os.remove(REQUEST)
    except OSError:
        pass


def check(n, s, save, status, beat, incidents, log, now=None, is_online=None):
    """One look at running job n. `s` is the routine's job state (job.json), changed here and saved with
    save(s). status(state, step, logline) writes the status block; beat(**fields) the jobs routine line."""
    now = now or time.time()
    claude = claude_of(s.get("pid"))
    last = last_sign(s, claude, now)
    nudges, last_nudge = s.get("nudges", 0), s.get("last_nudge", 0)

    # The answer to the last nudge, from the window itself.
    if last_nudge and not s.get("answered"):
        r = result(n, last_nudge - 1)
        if r:
            s["answered"] = True
            incidents.fix("jobs", f"Nudged job {n} in its window (try {nudges} of {NUDGES})" if r.get("ok")
                          else f"Couldn't type into job {n}'s window: {r.get('said', '')[:100]}", at=r["at"])
        elif pending(n) and now - last_nudge > NO_ANSWER:
            s["answered"] = True
            clear_request()
            incidents.fix("jobs", f"Job {n}'s window didn't pick up the nudge (it was started before H36); "
                          "type a nudge in it by hand")

    what = decide(now, last, nudges, last_nudge, online() if is_online is None and now - last >= QUIET else is_online)

    if what == "ok":
        if nudges or s.get("stuck") or s.get("offline"):
            how = (f"after try {nudges}" if nudges else "on its own, once the internet was back")
            incidents.fix("jobs", f"Job {n} is working again, {how}")
            incidents.up("jobs")
            if s.get("stuck"):
                status("BUILDING", f"Job {n} · working again after it was stuck", f"job {n} is working again ({how})")
            log(f"job {n} is working again ({how})")
            for k in ("nudges", "last_nudge", "answered", "stuck", "offline"):
                s.pop(k, None)
            clear_request()
        save(s)
        return what

    quiet_since = clock(last)
    if what == "offline":
        if not s.get("offline"):
            s["offline"] = True
            incidents.down("jobs", f"Job {n} has been quiet since {quiet_since}, and there's no internet", at=last)
            incidents.fix("jobs", "Waiting for the internet; then it types a nudge into the job's window")
            log(f"job {n} quiet since {quiet_since}, no internet: waiting")
        beat(state="waiting", text=f"Job {n} quiet since {quiet_since}: no internet, waiting for it to come back")
    elif what == "nudge":
        incidents.down("jobs", f"Job {n} has been quiet since {quiet_since}", at=last)
        request(n)
        s.update(nudges=nudges + 1, last_nudge=now, answered=False)
        log(f"job {n} quiet since {quiet_since}: typing a nudge that names the done mark (try {nudges + 1} of {NUDGES})")
        beat(state="waiting", text=f"Job {n} quiet since {quiet_since}: nudged, try {nudges + 1} of {NUDGES}")
    elif what == "wait":
        beat(state="waiting", text=f"Job {n} quiet since {quiet_since}: nudged, try {nudges} of {NUDGES}; "
                                   f"looking again at {clock(last_nudge + NUDGE_EVERY)}")
    elif what == "stuck":
        if not s.get("stuck"):
            s["stuck"] = True
            incidents.fix("jobs", f"Still quiet after {NUDGES} tries; shown as stuck on the status page")
            status("STOPPED", f"Job {n} looks stuck: nothing since {quiet_since}, nudged {NUDGES} times",
                   f"job {n} looks stuck since {quiet_since}; check its Terminal window")
            log(f"job {n} looks stuck since {quiet_since}")
        beat(state="down", text=f"Job {n} looks stuck: nothing since {quiet_since}, nudged {NUDGES} times")
    save(s)
    return what
