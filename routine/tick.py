#!/usr/bin/env python3
"""One look at the queue (phase L, L2). Run every minute by the Jarvis Routine helper app; no Claude,
so waiting costs no usage. What it does, in order:

- The hourly mail check (L8) runs on its own, also while a job runs (H30, 10 October 2026); their commits
  and pushes take turns through routine/gitlock.py. A run that was missed (a reboot, a stopped helper, a
  sleeping MacBook) is started as soon as the helper looks again, and a failed run is tried again.
- A job is running: if a call asked to stop it, end it (L4); if its chat has gone, note that. Otherwise wait (L6);
  and if it has gone quiet, type continue into its own window, and show it as stuck if it stays quiet (H36).
- A job has just been marked done (or held): end its chat, so its window closes by itself (L7).
- The hourly mail check is due (L8, its own on/off switch): start it, hidden, in a Terminal window that
  closes itself when it's done. Its own run brings the usage back, which is saved (L10).
- The routine is off: nothing more.
- No job running and one is waiting: take the one highest on the list (H39), check the last saved usage against the stop lines (L4; skipped
  for a job marked past the line: only the weekly line then, F13), then start it in a Terminal window as a normal chat with let's go (L5).
- Nothing running and nothing waiting: the scheduler (H43) may turn an item whose time has come into a job,
  which then starts the same way. The job list always goes first.

Before all that, every minute: the status page on the phone (H13) is kept up, on its own address and
independent of the call line (status/phone.sh does nothing when it already runs). So it starts at login too.
And the usage check (L10, routine/usage-check.py, no Claude): the latest saved usage goes on the status page.
And the laptop's temperature (H35, routine/temperature.py, no Claude, no password), and its battery
(H37, routine/battery.py, no Claude), and the totals Activity Monitor shows (H44, routine/stats.py),
and whether the lid-closed sleep is on (H45, routine/lidsleep.py, read only).

Everything it does is written on the status page (the roadmap's status block) and in scratch/routine/routine.log.
H19: every minute each routine also writes its own line (state, last run, what came out, next run) for
the status page's Routines section, and the helper leaves a heartbeat for the watchdog (H20).
H30: whatever goes down, why, what was done about it and when it was back goes in the incident log
(routine/incidents.py), shown under Routines. The helper also checks the watchdog, and starts it again
when it has stopped: the watchdog checks the helper, the helper checks the watchdog.
"""
import json, os, re, signal, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routines  # H19: every routine writes its own line for the status page
import incidents  # H30: what went down, why, what was done, when it was back
import quiet  # H36: a job that has gone quiet gets continue typed into its own window
import failures  # H42: why a run failed, in plain words, and how many times in a row (the watchdog reads it)

HERE = os.path.dirname(os.path.abspath(__file__))
JV = os.path.normpath(os.path.join(HERE, ".."))
import hqpaths  # M1: HQ is the app; the user's files are in workspace
FOLDER = hqpaths.FOLDER
RUN = os.path.join(JV, "scratch", "routine")
STATE = os.path.join(RUN, "job.json")  # the running job: {"n", "pid", "started"}
PIDFILE = os.path.join(RUN, "job.pid")  # written by the job's Terminal window
GATE_NOTE = os.path.join(RUN, "gate-note")
MAIL_STATE = os.path.join(RUN, "mail.json")  # the running mail check: {"pid", "started"}
MAIL_PID = os.path.join(RUN, "mail.pid")  # written by the mail check's Terminal window
MAIL_LAST = os.path.join(RUN, "mail-last")  # epoch seconds of the last mail check start
MAIL_RETRY = os.path.join(RUN, "mail-retry")  # H30: {"at", "n"}: a failed mail check is tried again
MAIL_RUNS = os.path.join(RUN, "mail-runs")  # H42: each mail check's own output, one file per run
MAIL_RUNS_KEEP = 72
MAIL_EVERY = 3600
MAIL_LATE = 300  # H30: a mail check that started over 5 minutes after its hour was missed
MAIL_RETRIES = 2
MAIL_RETRY_AFTER = 600
MAIL_TIMEOUT = 20 * 60
USAGE = os.path.join(HERE, "usage-check.py")  # L10: no Claude, every minute
TEMPERATURE = os.path.join(HERE, "temperature.py")  # H35: no Claude, no password, every minute
BATTERY = os.path.join(HERE, "battery.py")  # H37: no Claude, every minute
STATS = os.path.join(HERE, "stats.py")  # H44: CPU, GPU, memory, disk, network; no Claude, no password
LIDSLEEP = os.path.join(HERE, "lidsleep.py")  # H45: lid-closed sleep on or off, read only; no Claude
STREAM = os.path.join(HERE, "stream-usage.py")  # L10: the mail check's own run brings the usage back
DONE_GRACE = 20  # seconds between a job's done mark and closing its chat, so its last reply lands
NODE = "/opt/homebrew/bin/node"
CLAUDE = "/opt/homebrew/bin/claude"
PY = sys.executable or "/usr/bin/python3"


def log(msg):
    os.makedirs(RUN, exist_ok=True)
    with open(os.path.join(RUN, "routine.log"), "a") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def jobs(*args):
    r = subprocess.run([PY, os.path.join(HERE, "jobs.py"), *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout


def status(state, step, logline):
    """Rewrite the status block's state, step and log line; keep Just finished, Next and the table."""
    head = open(hqpaths.ROADMAP, encoding="utf8").read().partition("\n---\n")[0]
    just = re.search(r"^\*\*Just finished:\*\* (.*)$", head, re.M)
    nxt = re.search(r"^\*\*Next:\*\* (.*)$", head, re.M)
    row = re.search(r"^\|\s*(Phase .*?)\s*\|\s*$", head, re.M)
    subprocess.run([PY, os.path.join(JV, "status", "set-status.py"), state, step,
                    just.group(1) if just else "", nxt.group(1) if nxt else "",
                    re.sub(r"\s*\|\s*", "|", row.group(1)) if row else "Phase L|L2 ✅",
                    logline], capture_output=True)


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


def load_state():
    try:
        s = json.load(open(STATE))
    except (OSError, ValueError):
        return None
    if not s.get("pid"):
        try:
            s["pid"] = int(open(PIDFILE).read().strip())
            json.dump(s, open(STATE, "w"))
        except (OSError, ValueError):
            pass
    return s


def clear(*paths):
    for p in paths or (STATE, PIDFILE):
        try:
            os.remove(p)
        except OSError:
            pass


# L7: a Terminal window closes itself once its chat has ended. The window's own script runs the chat
# (not exec), then asks Terminal to close the window on its tty. That request comes from inside
# Terminal, so macOS asks no permission. Shared by the jobs and the mail check.
# L11: it waits until nothing runs in the window any more before closing.
# F8 (10 October 2026): L11 still left windows open that asked "Do you want to terminate running
# processes in this window?". Now: (1) whatever the run left behind on this window is ended first,
# as Terminate would; (2) the closer is detached from the window (its own session, no tty), so it
# never counts as a process in it; (3) it closes every finished window on this tty, since Terminal
# reuses tty names and L11 sometimes closed an old leftover window instead and stopped; (4) it keeps
# trying for five minutes and writes what it did to scratch/routine/close.log.
CLOSE_WINDOW = """T=$(tty)
SH=$PPID; LG=$(/bin/ps -o ppid= -p $PPID | tr -d ' ')
for p in $(/bin/ps -t ${T#/dev/} -o pid=); do
  [ $p = $$ ] || [ $p = $SH ] || [ $p = $LG ] || kill $p 2>/dev/null
done
/usr/bin/python3 -c 'import os,sys,subprocess,time; os.setsid(); r=subprocess.run(["/usr/bin/osascript"]+sys.argv[1:3], capture_output=True, text=True); open(sys.argv[3], "a").write(time.strftime("%Y-%m-%d %H:%M:%S ")+(r.stdout+r.stderr).strip()+chr(10))' \\
  """ + json.dumps(os.path.join(HERE, "close-window.applescript")) + """ "$T" """ + json.dumps(os.path.join(RUN, "close.log")) + """ </dev/null >/dev/null 2>&1 &!
exit 0
"""


def children(pid):
    r = subprocess.run(["/usr/bin/pgrep", "-P", str(pid)], capture_output=True, text=True)
    return [int(x) for x in r.stdout.split()]


def is_claude(pid):
    r = subprocess.run(["/bin/ps", "-o", "comm=", "-p", str(pid)], capture_output=True, text=True)
    return r.stdout.strip().endswith("claude")


def end_chat(pid):
    """End the chat in a window the routine opened, so the window closes itself (L7). pid is the window's
    script; the chat is its child. Jobs from before L7 exec'd the chat, so there pid is the chat itself."""
    if not alive(pid):
        return
    targets = [pid] if is_claude(pid) else [c for c in children(pid) if is_claude(c)] or children(pid)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        for t in targets:
            try:
                os.kill(t, sig)
            except OSError:
                pass
        for _ in range(10):
            if not any(alive(t) for t in targets):
                return
            time.sleep(1)


def start(job):
    n = job["n"]
    os.makedirs(RUN, exist_ok=True)
    prompt = (
        f"let's go. This is job {n} from the queue on the Jarvis VA roadmap, started by the routine "
        f"(phase L) in a Terminal window. The job, as agreed on the call: {job['text']}\n\n"
        "Follow the Jarvis VA build notes, the section \"Jobs started by the routine\". "
        + ("The user said on the call that this job may go past the 5-hour usage line; the weekly line still "
           "counts (F13): read the usage with --weekly-only, and on STOP hold as usual." if job["past"] else "")
    )
    # The job's settings (its status line) with this HQ's path, written fresh each time.
    settings = os.path.join(RUN, "job-settings.json")
    json.dump({"statusLine": {"type": "command",
                              "command": f"/usr/bin/python3 {json.dumps(os.path.join(HERE, 'statusline.py'))}"}},
              open(settings, "w"), indent=2)
    pfile = os.path.join(RUN, f"job-{n}.prompt")
    open(pfile, "w").write(prompt)
    cmd = os.path.join(RUN, f"job-{n}.command")
    open(cmd, "w").write(f"""#!/bin/zsh
# Job {n}, started by the Jarvis VA routine (phase L).
cd {json.dumps(FOLDER)} || exit 1
# 9 October 2026: the windows shouldn't take over the screen. Opened in the background,
# and the window minimizes itself to the Dock right away (it may show for a moment first).
printf '\\e[2t'
printf '\\e]0;Jarvis job {n}\\a'
echo "Jarvis VA · job {n}, started by the routine at $(date +%H:%M)."
echo "This is a normal chat: watch it, and type in between whenever you like. The window closes by itself once the job is done."
echo
echo $$ > {json.dumps(PIDFILE)}
# H36: wakes the chat up when it has gone quiet (types continue into this window only).
JT=$(tty)
/usr/bin/python3 {json.dumps(os.path.join(HERE, 'nudge.py'))} {n} "$JT" $$ </dev/null >/dev/null 2>&1 &!
{CLAUDE} --no-chrome --permission-mode auto --settings {json.dumps(settings)} \\
  -n "Jarvis job {n}" "$(cat {json.dumps(pfile)})"
""" + CLOSE_WINDOW)
    os.chmod(cmd, 0o755)
    try:
        os.remove(PIDFILE)
    except OSError:
        pass
    jobs("mark", str(n), "running since " + time.strftime("%H:%M"))
    json.dump({"n": n, "pid": None, "started": time.time()}, open(STATE, "w"))
    subprocess.run(["/usr/bin/open", "-g", "-a", "Terminal", cmd], check=True)
    status("BUILDING", f"Job {n} · started by the routine in a Terminal window",
           f"job {n} started by the routine: {job['text'][:90]}")
    log(f"started job {n}")


# The hourly mail check (L8). Only the Gmail reading tools, editing the mail list and its one commit
# script are allowed; everything else is refused without asking (dontAsk), so it never waits on anyone.
MAIL_ALLOW = ",".join([
    "Read", "Grep", "Glob", "Edit(/inbox.md)", "Bash(sh .claude/mail-commit.sh)",
    "mcp__claude_ai_Gmail__search_threads", "mcp__claude_ai_Gmail__get_thread", "mcp__claude_ai_Gmail__get_message",
])
MAIL_DENY = ",".join("mcp__claude_ai_Gmail__" + t for t in (
    "send_message", "reply", "forward", "create_draft", "update_draft", "delete_draft", "label_message",
    "label_thread", "unlabel_message", "unlabel_thread", "update_message_labels", "trash_message", "trash_thread",
    "mark_message_spam", "mark_thread_spam", "apply_sensitive_message_label", "apply_sensitive_thread_label",
    "create_label", "delete_label", "update_label")) + ",Write,NotebookEdit,WebFetch,WebSearch"


def mail_running():
    """True while the mail check's window still runs (one at a time). Clears it once it's finished."""
    try:
        m = json.load(open(MAIL_STATE))
    except (OSError, ValueError):
        return False
    try:
        pid = int(open(MAIL_PID).read().strip())
    except (OSError, ValueError):
        pid = None
    started = m.get("started", 0)
    if pid and alive(pid):
        if time.time() - started > MAIL_TIMEOUT:
            end_chat(pid)
            log("mail check ran over 20 minutes; ended it")
            incidents.down("mail", "Ran over 20 minutes", at=started)
            incidents.fix("mail", "Ended it; the next one starts on the hour")
            clear(MAIL_RETRY)
            clear(MAIL_STATE, MAIL_PID)
            routines.beat("mail", state="down", text="Ran over 20 minutes; it was ended. The next one starts on time.",
                          next=mail_next(started), every=60)
            return False
        routines.beat("mail", state="running", text="Checking the mail now", every=60)
        return True
    if not pid and time.time() - started < 90:
        routines.beat("mail", state="running", text="Starting", every=60)
        return True  # the window is still opening
    clear(MAIL_STATE, MAIL_PID)
    log("mail check finished")
    res = mail_result()
    ok, text = res["ok"], res["text"]
    routines.beat("mail", state="ok" if ok else "down", text=text, last=started, next=mail_next(started), every=60,
                  why=res.get("why", ""), detail=res.get("detail", []), run=res.get("run", ""))
    if ok:
        clear(MAIL_RETRY)
        failures.record("mail", True)
        incidents.up("mail")
    else:
        # H30: a failed run didn't really run; try it again in ten minutes, twice at the most.
        # H42: with the reason from its own output, its last lines, and where its whole output is kept.
        n = _retry().get("n", 0) + 1
        why = res["why"]
        was = incidents.is_down("mail")
        incidents.down("mail", f"The run failed: {why}", detail=res["detail"], run=res.get("run", ""))
        if was:
            incidents.fix("mail", f"{'Failed again' if was.get('why', '').startswith('The run failed') else 'The run failed'}: {why}")
        failures.record("mail", False, why=why, detail=res["detail"], gave_up=n > MAIL_RETRIES)
        if n <= MAIL_RETRIES:
            json.dump({"at": time.time() + MAIL_RETRY_AFTER, "n": n}, open(MAIL_RETRY, "w"))
            incidents.fix("mail", f"Will try it again at {clock(time.time() + MAIL_RETRY_AFTER)} (try {n} of {MAIL_RETRIES})")
            routines.beat("mail", next=time.time() + MAIL_RETRY_AFTER)
        else:
            clear(MAIL_RETRY)
            incidents.fix("mail", f"Failed again after {MAIL_RETRIES} tries; the next one starts on the hour")
        log(f"mail check failed ({why}); retry {n}")
    return False


def _retry():
    try:
        return json.load(open(MAIL_RETRY))
    except (OSError, ValueError):
        return {}


def clock(t):
    return time.strftime("%H:%M", time.localtime(t))


def mail_result():
    """H19: how the last mail check ended, from its log: {"ok", "text"}, and when it failed (H42) also
    "why" (the plain reason from its own output), "detail" (its last lines) and "run" (its own output file).
    Only the lines before its exit line are its own; the usage lines after it are the usage check's."""
    try:
        lines = open(os.path.join(RUN, "mail.log"), encoding="utf8", errors="replace").read().splitlines()
    except OSError:
        return {"ok": False, "text": "Failed: no log of the last run", "why": "No log of the last run", "detail": []}
    start = max((i for i, l in enumerate(lines) if re.match(r"^--- \d{4}-", l)), default=None)
    if start is None:
        return {"ok": False, "text": "Failed: no log of the last run", "why": "No log of the last run", "detail": []}
    block = lines[start + 1:]
    end = next((i for i, l in enumerate(block) if l.startswith("--- exit")), None)
    code = block[end].split()[-1] if end is not None else None
    own = block[:end] if end is not None else block
    said = [l.strip() for l in own if l.strip() and not l.startswith("(usage saved") and not l.startswith("(the mail check's run")]
    run = _last_run_file()
    if code is None:
        return {"ok": False, "text": "Failed: it ended before it could say how", "run": run,
                "why": "It ended before it could say how (the window was closed, or the MacBook slept)", "detail": said[-6:]}
    if code != "0" or any(l.startswith("(the run ended with an error") for l in said):
        why, detail = failures.reason(own, code)
        return {"ok": False, "text": f"Failed: {why} (exit {code})", "why": why, "detail": detail, "run": run}
    return {"ok": True, "text": (said[-1] if said else "")[:140] or "Ran fine", "run": run}


def _last_run_file():
    try:
        names = sorted(f for f in os.listdir(MAIL_RUNS) if f.endswith(".log"))
    except OSError:
        return ""
    return os.path.join("scratch", "routine", "mail-runs", names[-1]) if names else ""


def mail_next(last):
    """H22: the mail check runs on the full hour (14:00, 15:00, …): the first full hour after its last start."""
    return (int(last) // MAIL_EVERY + 1) * MAIL_EVERY


def mail_last():
    try:
        return float(open(MAIL_LAST).read().strip())
    except (OSError, ValueError):
        return None


def mail_due():
    last = mail_last()
    if last is None:
        return True
    r = _retry()
    if r and not r.get("started") and time.time() >= r.get("at", 0):
        return True
    return time.time() >= mail_next(last)


def mail_missed():
    """H30: the hour this run was due, when it is over five minutes late (else None)."""
    last = mail_last()
    if last is None or _retry():
        return None
    due = mail_next(last)
    return due if time.time() - due > MAIL_LATE else None


def why_missed(due):
    """H30: why a routine didn't run at `due`: the helper was down then (and why), or not known."""
    for i in reversed(incidents.read()["incidents"]):
        if i["key"] == "helper" and i["down"] - 120 <= due <= (i.get("back") or time.time()):
            return f"The helper wasn't running at {clock(due)}: {i.get('why') or 'reason not known'}"
    return "Not known: the helper was running"


def mail(q):
    """L8, H30: the hourly mail check, on its own, also while a job runs."""
    if mail_running():
        return
    if not q.get("mail", True):
        routines.beat("mail", state="off", text="Switched off from a call", every=60)
        return
    if failures.retry_asked("mail"):
        # H42: the watchdog saw it keep failing after the helper had given up, and the internet is back.
        incidents.fix("mail", f"The watchdog asked for another try: started it at {clock(time.time())}")
        log("mail check: another try, asked by the watchdog")
        start_mail()
        return
    if mail_due():
        due = mail_missed()
        if due:
            incidents.down("mail", f"Missed its {clock(due)} run. {why_missed(due)}", at=due)
            incidents.fix("mail", f"Started the missed run at {clock(time.time())}")
        start_mail()
        return
    last = mail_last() or time.time()
    r = _retry()
    nxt = r["at"] if r and not r.get("started") else mail_next(last)
    routines.beat("mail", last=last, next=nxt, every=60, **({} if routines.read().get("mail", {}).get("state") in ("ok", "down")
                                                          else {"state": "ok", "text": "Waiting for its next hour"}))


def start_mail():
    os.makedirs(RUN, exist_ok=True)
    cmd = os.path.join(RUN, "mail-check.command")
    # H42: the run's own output also goes to its own file, so why it failed can be read afterwards.
    os.makedirs(MAIL_RUNS, exist_ok=True)
    run_file = os.path.join(MAIL_RUNS, time.strftime("%Y-%m-%d-%H%M%S") + ".log")
    for old in sorted(f for f in os.listdir(MAIL_RUNS) if f.endswith(".log"))[:-MAIL_RUNS_KEEP]:
        clear(os.path.join(MAIL_RUNS, old))
    # The instructions with this workspace's own path in them.
    instructions = os.path.join(RUN, "mail-check.md")
    open(instructions, "w").write(open(os.path.join(HERE, "mail-check.md")).read().replace("{WORKSPACE}", FOLDER))
    open(cmd, "w").write(f"""#!/bin/zsh
# The hourly mail check, started by the Jarvis VA routine (phase L, L8). Hidden: opened in the
# background, minimized to the Dock, and the window closes itself when it's done (L7).
cd {json.dumps(FOLDER)} || exit 1
printf '\\e[2t'
printf '\\e]0;Jarvis mail check\\a'
echo "Jarvis VA · the hourly mail check, started by the routine at $(date +%H:%M). It closes by itself."
echo
echo $$ > {json.dumps(MAIL_PID)}
{{ echo "--- $(date '+%Y-%m-%d %H:%M:%S')"
  # L10: streamed, so the plan limits that come back with the run are saved, for free.
  {CLAUDE} -p --no-chrome --model sonnet --permission-mode dontAsk --no-session-persistence \\
    --output-format stream-json --verbose \\
    --allowedTools {json.dumps(MAIL_ALLOW)} --disallowedTools {json.dumps(MAIL_DENY)} \\
    < {json.dumps(instructions)} 2>&1 | /usr/bin/python3 {json.dumps(STREAM)}
  echo "--- exit ${{pipestatus[1]}}"
  /usr/bin/python3 {json.dumps(USAGE)}; }} 2>&1 | tee -a {json.dumps(os.path.join(RUN, 'mail.log'))} {json.dumps(run_file)}
""" + CLOSE_WINDOW)
    os.chmod(cmd, 0o755)
    clear(MAIL_PID)
    r = _retry()
    if r:
        json.dump({**r, "started": time.time()}, open(MAIL_RETRY, "w"))
    open(MAIL_LAST, "w").write(str(int(time.time())))
    json.dump({"pid": None, "started": time.time()}, open(MAIL_STATE, "w"))
    subprocess.run(["/usr/bin/open", "-g", "-a", "Terminal", cmd], check=True)
    log("started the mail check")
    routines.beat("mail", state="running", text="Started", last=time.time(), next=mail_next(time.time()), every=60)


# The usage check (L10). Every minute, no Claude: the latest saved usage (a job's status line, or the
# mail check's own run) goes on the status page with how old it is.
def usage():
    r = subprocess.run([PY, USAGE], capture_output=True, text=True, timeout=60)
    first = next((l.strip() for l in r.stdout.splitlines() if l.strip()), "")
    routines.beat("usage", state="ok" if r.returncode == 0 else "down", last=time.time(), next=time.time() + 60,
                  every=60, text=(first or "Ran") if r.returncode == 0 else f"Failed: {(r.stderr or r.stdout).strip()[:120]}")
    if r.returncode == 0:
        incidents.up("usage")
    else:
        incidents.down("usage", f"Failed: {(r.stderr or r.stdout).strip()[:120]}")


def status_page():
    # H13: the status server and its Tailscale address; a line in the log only when something was started.
    r = subprocess.run(["/bin/zsh", os.path.join(JV, "status", "phone.sh")], capture_output=True, text=True)
    for line in (r.stdout + r.stderr).strip().splitlines():
        log(line)
    up = listening(4748)
    ts = subprocess.run(["/usr/local/bin/tailscale", "serve", "status"], capture_output=True, text=True).stdout
    on_phone = ":8444" in ts
    text = ("Status page up, also on the phone" if up and on_phone
            else "Status page up, but not on the phone (Tailscale)" if up else "Status server is not running")
    routines.beat("phone", state="ok" if up and on_phone else "down", last=time.time(), next=time.time() + 60, every=60,
                  text=text)
    # H30: phone.sh starts whatever was missing; that's the fix, and the next look shows if it worked.
    started = (r.stdout + r.stderr).strip()
    fixed = f"Started again: {started.splitlines()[-1][:120]}" if started else ""
    if up and on_phone:
        if fixed and not incidents.is_down("phone"):
            # Found down and started again within this same look.
            incidents.past("phone", time.time() - 60, time.time(), "The status server or its phone address wasn't running",
                           [(time.time(), fixed)])
        else:
            if fixed:
                incidents.fix("phone", fixed)
            incidents.up("phone")
    else:
        incidents.down("phone", text)
        if fixed:
            incidents.fix("phone", fixed)


def listening(port):
    r = subprocess.run(["/usr/sbin/lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"], capture_output=True, text=True)
    return bool(r.stdout.strip())


def call_line():
    # H19: the call line isn't a routine the helper runs, but it is what the calls need, so its state shows too.
    # H22: a real check every minute: the call page answers on this MacBook, and the phone address is on.
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:7860/", timeout=5) as r:
            answers = r.status == 200
    except Exception:
        answers = False
    ts = subprocess.run(["/usr/local/bin/tailscale", "serve", "status"], capture_output=True, text=True).stdout
    phone = ":8443" in ts
    now = time.time()
    if answers and phone:
        state, text = "ok", "Up: the call page answers, and the phone address is on"
    elif answers:
        state, text = "down", "The call page answers, but the phone address is off: calls from the phone won't connect"
    elif listening(7860):
        state, text = "down", "Running, but the call page doesn't answer"
    else:
        state, text = "down", "Down: calls won't connect"
    routines.beat("call", state=state, text=text, last=now, next=now + 60, every=60)
    # H30: respond, not only report. Nothing listening for 3 minutes in a row (a job's own restart takes
    # seconds): start it the way login does (app/start.sh, which does nothing if it already runs). The page
    # answering without the phone address: turn the address on again. A server that runs but doesn't
    # answer is only reported: stopping it could drop a call.
    if state == "ok":
        incidents.up("call")
        return
    inc = incidents.down("call", text)
    if not inc:
        return
    tried = [f["at"] for f in inc.get("fixes", [])]
    quiet = not tried or now - max(tried) > 600
    if answers and not phone and now - inc["down"] >= 120 and quiet:
        subprocess.run(["/usr/local/bin/tailscale", "serve", "--bg", "--https=8443", "http://127.0.0.1:7860"],
                       capture_output=True, timeout=30)
        incidents.fix("call", "Turned the phone address on again")
        log("call line: phone address turned on again")
    elif not listening(7860) and now - inc["down"] >= 180 and quiet:
        out = open(os.path.join(JV, "scratch", "launchagent.log"), "a")
        subprocess.Popen(["/bin/zsh", os.path.join(JV, "app", "start.sh")], stdout=out, stderr=out,
                         stdin=subprocess.DEVNULL, start_new_session=True)
        incidents.fix("call", "Nothing was listening for 3 minutes: started it again (app/start.sh)")
        log("call line: started it again")


def boottime():
    r = subprocess.run(["/usr/sbin/sysctl", "-n", "kern.boottime"], capture_output=True, text=True)
    m = re.search(r"sec = (\d+)", r.stdout)
    return int(m.group(1)) if m else 0


def waketime():
    r = subprocess.run(["/usr/sbin/sysctl", "-n", "kern.waketime"], capture_output=True, text=True)
    m = re.search(r"sec = (\d+)", r.stdout)
    return int(m.group(1)) if m else 0


def helper_gap():
    """H30: before the heartbeat is written: was the helper itself away? Then every routine missed its
    looks meanwhile. Written as one incident, with why (a restart, sleep, or it stopped or got stuck)
    and what brought it back (the watchdog, or macOS at login)."""
    try:
        old = float(open(routines.HEARTBEAT).read().strip())
    except (OSError, ValueError):
        return
    now = time.time()
    events = incidents.watchdog_events()
    if now - old < 180:
        return
    boot, wake = boottime(), waketime()
    if boot > old:
        why = f"The MacBook restarted at {clock(boot)}"
    elif wake > old:
        why = f"The MacBook was asleep until {clock(wake)}"
    elif any("stuck" in w for _, w in events):
        why = "It got stuck"
    else:
        why = "It stopped; the reason isn't known"
    fixes = [(a, f"Watchdog: {w}") for a, w in events if old - 60 <= a <= now]
    if not fixes:
        fixes = [(boot, "macOS started it at login")] if boot > old else [(now, "It came back on its own")]
    incidents.past("helper", old + 60, now, why, fixes)
    log(f"helper was away {int((now - old) // 60)} min: {why}")


def watchdog_check():
    """H30: the watchdog checks the helper; the helper checks the watchdog. Its line is over 12 minutes
    old (it runs every 5): ask macOS to run it again."""
    try:
        at = json.load(open(os.path.join(routines.SUPPORT, "watchdog.json"))).get("at", 0)
    except (OSError, ValueError):
        at = 0
    now = time.time()
    if now - at <= 720:
        incidents.up("watchdog")
        return
    inc = incidents.down("watchdog", f"No check from the watchdog since {clock(at)}" if at else "The watchdog has never checked in")
    tried = [f["at"] for f in (inc or {}).get("fixes", [])]
    if not tried or now - max(tried) > 600:
        r = subprocess.run(["/bin/launchctl", "kickstart", f"gui/{os.getuid()}/{hqpaths.agent_label('jarvis-watchdog')}"],
                           capture_output=True, text=True)
        incidents.fix("watchdog", "Asked macOS to run it again" if r.returncode == 0
                      else f"Couldn't start it ({(r.stderr or r.stdout).strip()[:80]}); run routine/install-watchdog.sh")
        log("watchdog: asked macOS to run it again")


def jobs_line(q):
    running = q.get("running") or []
    waiting = len(q.get("ready") or []) + len(q.get("held") or [])
    if running:
        text = f"Job {running[0]['n']} running" + (f", {waiting} waiting" if waiting else "")
        state = "running"
    elif not q.get("on", True):
        text, state = "Switched off from a call", "off"
    elif waiting and os.path.exists(GATE_NOTE):
        # H30: waiting on purpose shows as waiting (yellow), with why, not as broken.
        n, _, why = open(GATE_NOTE).read().partition(" ")
        why = why.strip()
        why = why[4:].strip(" :") if why.upper().startswith("STOP") else why
        text, state = f"Job {n} waits for the usage line: {why[:110]}", "waiting"
    else:
        text = f"{waiting} waiting" if waiting else "Nothing waiting; looks every minute"
        state = "ok"
    routines.beat("jobs", state=state, text=text, every=60)


def schedule_promote():
    """H43: the scheduler. Turns a due item into a job when the queue is empty; returns what it did."""
    r = subprocess.run([PY, os.path.join(HERE, "schedule.py"), "promote"], capture_output=True, text=True)
    out = r.stdout.strip()
    if r.returncode:
        log(f"schedule: {(r.stderr or out).strip()[:200]}")
        return ""
    if out.startswith("item "):
        log(f"schedule: {out}")
        status("BUILDING", f"Scheduled {out.split(' became ')[0]} starts as {out.split(' became ')[1]}",
               f"scheduled {out}, now that the job list is empty")
        return out
    return ""


def schedule_line():
    """H43: the scheduler's own routine line: what's next, or what's due and why it waits."""
    r = subprocess.run([PY, os.path.join(HERE, "schedule.py"), "status"], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout)
    except ValueError:
        routines.beat("schedule", state="down", text=(r.stderr or r.stdout).strip()[:120] or "Couldn't read the schedule",
                      last=time.time(), every=60)
        return
    routines.beat("schedule", state=d["state"], text=d["text"], last=time.time(), next=d.get("next"), every=60)


def tick():
    q = json.loads(jobs("next"))
    jobs_line(q)
    try:
        schedule_line()
    except Exception as e:
        log(f"schedule line: {e!r}")
    try:
        mail(q)  # H30: on its own, also while a job runs
    except Exception as e:
        log(f"mail: {e!r}")
    running = q["running"]
    s = load_state()
    if running:
        job = running[0]
        n = job["n"]
        if s is None or s.get("n") != n:
            # Marked running, but this routine didn't start it (or lost track): treat as ended.
            s = {"n": n, "pid": None, "started": 0}
        pid = s.get("pid")
        if job["state"] == "stop asked":
            end_chat(pid)
            jobs("mark", str(n), "stopped " + time.strftime("%H:%M"))
            clear()
            status("STOPPED", f"Job {n} stopped from a call", f"job {n} stopped, as asked on a call")
            log(f"stopped job {n}")
            return
        if not alive(pid) and time.time() - s.get("started", 0) > 90:
            jobs("mark", str(n), "ended " + time.strftime("%H:%M") + " without a done mark")
            clear()
            incidents.past("jobs", time.time(), time.time(), f"Job {n}'s chat closed before it said it was done",
                           [(time.time(), "Marked it as ended, so the next job can start")])
            status("STOPPED", f"Job {n} ended without saying it was done",
                   f"job {n}: its chat closed before it said done; check the Terminal window or the log")
            log(f"job {n} ended without a done mark")
            return
        try:
            # H36: gone quiet? Then continue is typed into its own window, and a stuck job shows as stuck.
            quiet.check(n, s, lambda x: json.dump(x, open(STATE, "w")), status,
                        lambda **f: routines.beat("jobs", every=60, **f), incidents, log)
        except Exception as e:
            log(f"quiet check: {e!r}")
        return
    if s:
        # The last job is done (or held): end its chat, so its window closes by itself (L7).
        pid = s.get("pid")
        if alive(pid):
            if not s.get("done_seen"):
                s["done_seen"] = time.time()
                json.dump(s, open(STATE, "w"))
            wait = DONE_GRACE - (time.time() - s["done_seen"])
            if wait > 0:
                time.sleep(wait)
            end_chat(pid)
            log(f"job {s.get('n')} finished; closed its window")
        clear()
        quiet.clear_request()  # H36: a nudge that wasn't picked up is for nobody now
    if not q["on"]:
        return
    # H39: the waiting job highest on the list goes first (ready, or held for the usage and now
    # given another go), not the oldest; a call can move them with jobs.py move.
    line = q.get("waiting")
    if line is None:
        line = (q["ready"] or []) + (q["held"] or [])
    if not line:
        # H43: the job list goes first; only now, with nothing running or waiting, may a scheduled item
        # whose time has come become a job (at the bottom of the queue), and it starts right away.
        did = schedule_promote()
        if not did:
            return
        q = json.loads(jobs("next"))
        line = q.get("waiting") or []
        if not line:
            return
    job = line[0]
    # F13: a job let past the line only skips the 5-hour line; the weekly line always counts, so a
    # past-the-line job held at the weekly line waits here quietly instead of being started every minute.
    g = subprocess.run([NODE, os.path.join(JV, "status", "save-usage.mjs"), "--gate"]
                       + (["--weekly-only"] if job["past"] else []),
                       capture_output=True, text=True)
    if g.returncode:
        note = f"{job['n']} {g.stdout.strip()}"
        if not os.path.exists(GATE_NOTE) or open(GATE_NOTE).read() != note:
            open(GATE_NOTE, "w").write(note)
            status("STOPPED", f"Job {job['n']} waits for the usage line",
                   f"job {job['n']} waits: {g.stdout.strip()[6:].strip()[:120]}")
            log(f"job {job['n']} waits for the usage: {g.stdout.strip()}")
        return
    try:
        os.remove(GATE_NOTE)
    except OSError:
        pass
    start(job)


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--mail-now"]:  # a test: start the mail check right away, whatever else runs
            start_mail()
            sys.exit(0)
        if sys.argv[1:] == ["--usage-now"]:  # a test: the usage check, right away
            usage()
            sys.exit(0)
        try:
            helper_gap()
        except Exception as e:
            log(f"helper gap: {e!r}")
        routines.heartbeat()
        routines.beat("helper", state="ok", text="Looks every minute", last=time.time(), next=time.time() + 60, every=60)
        try:
            status_page()
        except Exception as e:
            log(f"status page: {e!r}")
        try:
            call_line()
        except Exception as e:
            log(f"call line: {e!r}")
        try:
            usage()
        except Exception as e:
            log(f"usage: {e!r}")
        try:
            # H35: the laptop's temperature and macOS's heat warning (writes its own routine line).
            subprocess.run([PY, TEMPERATURE], capture_output=True, text=True, timeout=150)
        except Exception as e:
            log(f"temperature: {e!r}")
        try:
            # H37: the laptop's battery, charging or not (writes its own routine line).
            subprocess.run([PY, BATTERY], capture_output=True, text=True, timeout=60)
        except Exception as e:
            log(f"battery: {e!r}")
        try:
            # H44: the totals Activity Monitor shows (no routine line, no alarms: just to look at).
            subprocess.run([PY, STATS], capture_output=True, text=True, timeout=150)
        except Exception as e:
            log(f"stats: {e!r}")
        try:
            # H45: whether the laptop keeps working with the lid closed (only read here, never changed).
            subprocess.run([PY, LIDSLEEP], capture_output=True, text=True, timeout=30)
        except Exception as e:
            log(f"lid sleep: {e!r}")
        try:
            watchdog_check()
        except Exception as e:
            log(f"watchdog check: {e!r}")
        tick()
    except Exception as e:  # never let one bad minute stop the next
        log(f"error: {e!r}")
        sys.exit(1)
