#!/usr/bin/env python3
"""One look at the queue (phase L, L2). Run every minute by the HQ Routine helper app; no Claude,
so waiting costs no usage. What it does, in order:

- The hourly mail check (L8) runs on its own, also while a job runs (H30, 10 October 2026); their commits
  and pushes take turns through routine/gitlock.py. A run that was missed (a reboot, a stopped helper, a
  sleeping MacBook) is started as soon as the helper looks again, and a failed run is tried again.
- A job is running: if a call asked to stop it, end it (L4); if its chat has gone, note that. Otherwise wait (L6);
  and if it has gone quiet, type continue into its own window, and show it as stuck if it stays quiet (H36).
- A job's chat is gone without a done mark and the Mac started again after the job had started: it was a crash
  (H62, routine/crash.py). The job runs again, with a note to pick up where it left off, first in line, so no
  other job starts before it; once only.
- A job has just been marked done (or held): end its chat, so its window closes by itself (L7).
- The hourly mail check is due (L8, its own on/off switch): start it, hidden, in a Terminal window that
  closes itself when it's done. Its own run brings the usage back, which is saved (L10).
- The routine is off: nothing more.
- No job running and one is waiting: take the one highest on the list (H39), check the last saved usage against the stop lines (L4; skipped
  for a job marked past the line: only the weekly line then, F13), then start it in a Terminal window as a normal chat with let's go (L5).
- Nothing running and nothing waiting: the scheduler (H43) may turn an item whose time has come into a job,
  which then starts the same way. The job list always goes first, except for an item with the priority tag
  (H99): with nothing running, it becomes a job first in line, ahead of the waiting jobs.

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
import crash  # H62: a job stopped by a crash runs again from the top of the line
import role  # H56.3: main and backup; only the main runs the mail check, the jobs and the scheduler
import heartbeat  # H88: a heartbeat line for each of the two computers
import estimate  # H81: the estimates learn from both computers
import carryon  # H113: a job held by the usage line carries on in its own chat, or with a note
import sync  # H56.4: the two-way sync of the workspace and Claude's memory with the other HQ
import log_cycle  # H100: the coaching log keeps three hours; older entries move to its archive

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
# H148: a usage test, every 15 minutes from 15:00 to 22:00 Europe/Amsterdam on 15 October 2026, then hourly again
# by itself. To remove: these lines, mail_every() (MAIL_EVERY back where it is used) and the label in status/index.html.
MAIL_FAST, MAIL_FAST_FROM, MAIL_FAST_UNTIL = 900, 1792069200, 1792094400
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
NODE = hqpaths.tool("node", "/opt/homebrew/bin/node")  # H56.1: found where it is on Linux
CLAUDE = hqpaths.tool("claude", "/opt/homebrew/bin/claude")
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


TMUX = hqpaths.tool("tmux", "/usr/bin/tmux")  # H56.2: the job windows off a Mac
LINUX_WINDOWS = hqpaths.window_kind() == "tmux"


def open_window(cmd: str, name: str = "") -> None:
    """Opens a job's or the mail check's window to run the script `cmd`: on a Mac a Terminal window, in the
    background; a user's own part local/open-window (H59) gets the script's path instead, on any computer.
    H56.2: off a Mac, a detached tmux session called hqpaths.session(name) (hq-job-63, hq-mail): hidden, to be
    watched with `tmux attach -t <session>`, and gone by itself once the script ends. It gets PATH and every
    HQ_* setting (a tmux server that already runs would otherwise give its own), and runs in its own systemd
    scope when there is one, so it never belongs to the routine's one-minute run."""
    own = hqpaths.part_cmd("open-window", cmd)
    if own or hqpaths.IS_MAC:
        subprocess.run(own or ["/usr/bin/open", "-g", "-a", "Terminal", cmd], check=True)
        return
    sess = hqpaths.session(name)
    subprocess.run([TMUX, "kill-session", "-t", "=" + sess], capture_output=True)  # an old one by that name
    envs = [x for k, v in os.environ.items() if k == "PATH" or k.startswith("HQ_") for x in ("-e", f"{k}={v}")]
    tm = [TMUX, "new-session", "-d", "-s", sess, "-x", "200", "-y", "50", *envs, "/bin/bash", cmd]
    scope = ["systemd-run", "--user", "--scope", "--quiet", f"--unit={sess}-{int(time.time())}-{os.getpid()}"]
    r = subprocess.run(scope + tm, capture_output=True, text=True) if os.environ.get("XDG_RUNTIME_DIR") else None
    if r is None or (r.returncode and not subprocess.run([TMUX, "has-session", "-t", "=" + sess], capture_output=True).returncode == 0):
        r = subprocess.run(tm, capture_output=True, text=True)  # no systemd scope here: tmux on its own
    if r.returncode:
        raise RuntimeError(f"tmux couldn't open {sess}: {(r.stderr or r.stdout).strip()[:200]}")


TRUST_NOTE = os.path.join(RUN, "trust-note")


def workspace_trusted() -> bool:
    """H56.2: a job's chat opens in the workspace, and the first time Claude Code opens a folder it asks whether
    to trust it; on a server nobody answers, so the job would sit there. Claude Code keeps the answer in
    ~/.claude.json (projects[<folder>].hasTrustDialogAccepted); the workspace or a folder above it counts.
    When that file can't be read, it counts as trusted (as before). HQ_CLAUDE_JSON reads another file (a test)."""
    try:
        projects = json.load(open(os.environ.get("HQ_CLAUDE_JSON") or os.path.expanduser("~/.claude.json"))).get("projects") or {}
    except (OSError, ValueError):
        return True
    p = FOLDER
    while True:
        if (projects.get(p) or {}).get("hasTrustDialogAccepted"):
            return True
        up = os.path.dirname(p)
        if up == p:
            return False
        p = up


def watch_line(n) -> str:
    """H56.2: on the status page, how to watch job n from the laptop (only off a Mac)."""
    return f"; watch it: {hqpaths.watch_cmd(f'job-{n}')}" if LINUX_WINDOWS else ""


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
# H56.2: in tmux the session closes by itself once its script ends, and nudge.py ends with it; nothing to close.
CLOSE_WINDOW_TMUX = "exit 0\n"


def children(pid):
    r = subprocess.run(["/usr/bin/pgrep", "-P", str(pid)], capture_output=True, text=True)
    return [int(x) for x in r.stdout.split()]


def is_claude(pid):
    r = subprocess.run(["/bin/ps", "-o", "comm=", "-p", str(pid)], capture_output=True, text=True)
    return quiet.is_claude_comm(r.stdout)


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
    where = "a tmux session" if LINUX_WINDOWS else "a Terminal window"
    past_note = ("The user said on the call that this job may go past the 5-hour usage line; the weekly line still "
                 "counts (F13): read the usage with --weekly-only, and on STOP hold as usual." if job["past"] else "")
    # H113: a job the usage line held picks its own chat up again when it's still here; else a fresh chat
    # with a note at about which step it stopped. Every chat gets its id up front, so it can be found again.
    try:
        roadmap = open(hqpaths.ROADMAP, encoding="utf8").read()
    except OSError:
        roadmap = ""
    plan = carryon.plan(job, roadmap, FOLDER)
    if plan["mode"] == "resume":
        prompt = carryon.resume_prompt(n, where, plan, job["text"], past_note)
    else:
        prompt = (
            f"let's go. This is job {n} from the queue on the HQ roadmap, started by the routine "
            f"(phase L) in {where}. The job, as agreed on the call: {job['text']}"
            + (carryon.fresh_note(n, plan) if plan["mode"] == "fresh" else "") + "\n\n"
            "Follow the HQ build notes, the section \"Jobs started by the routine\". "
            # H90: one HQ code on every computer: the working branch on GitHub is where every job starts and ends.
            "Before the first step, bring HQ up to date with its working branch (dev) from GitHub with "
            "routine/push.py --pull; when done, push HQ's commits to dev with routine/push.py, after its privacy check. "
            "A refused pull or push is never passed over: say so in the status block's log and the coaching log (F31). "
            "Never main, never the version tags. "
            # H168: the team estimates itself: its own guess at the start, kept next to the computed one and the real time.
            f"After reading the job's row, before building, write down your own guess of how many minutes this job will "
            f"take: python3 {json.dumps(os.path.join(HERE, 'jobs.py'))} guess {n} MINUTES (H168). "
            + past_note
        )
    chat = (f"--resume {plan['session']}" if plan["mode"] == "resume" else f"--session-id {plan['session']}")
    # The job's settings (its status line) with this HQ's path, written fresh each time.
    settings = os.path.join(RUN, "job-settings.json")
    json.dump({"statusLine": {"type": "command",
                              "command": f"/usr/bin/python3 {json.dumps(os.path.join(HERE, 'statusline.py'))}"}},
              open(settings, "w"), indent=2)
    pfile = os.path.join(RUN, f"job-{n}.prompt")
    open(pfile, "w").write(prompt)
    cmd = os.path.join(RUN, f"job-{n}.command")
    open(cmd, "w").write(job_script_tmux(n, settings, pfile, chat) if LINUX_WINDOWS else f"""#!/bin/zsh
# Job {n}, started by the HQ routine (phase L).
cd {json.dumps(FOLDER)} || exit 1
# 9 October 2026: the windows shouldn't take over the screen. Opened in the background,
# and the window minimizes itself to the Dock right away (it may show for a moment first).
printf '\\e[2t'
printf '\\e]0;HQ job {n}\\a'
echo "HQ · job {n}, started by the routine at $(date +%H:%M)."
echo "This is a normal chat: watch it, and type in between whenever you like. The window closes by itself once the job is done."
echo
echo $$ > {json.dumps(PIDFILE)}
# H36: wakes the chat up when it has gone quiet (types continue into this window only).
JT=$(tty)
/usr/bin/python3 {json.dumps(os.path.join(HERE, 'nudge.py'))} {n} "$JT" $$ </dev/null >/dev/null 2>&1 &!
{CLAUDE} --no-chrome --permission-mode auto --settings {json.dumps(settings)} {chat} \\
  -n "HQ job {n}" "$(cat {json.dumps(pfile)})"
""" + CLOSE_WINDOW)
    os.chmod(cmd, 0o755)
    try:
        os.remove(PIDFILE)
    except OSError:
        pass
    jobs("mark", str(n), "running since " + time.strftime("%H:%M"))
    json.dump({"n": n, "pid": None, "started": time.time()}, open(STATE, "w"))
    open_window(cmd, f"job-{n}")
    carryon.started(n, plan)
    how = {"resume": "carries on in its own chat after the usage hold",
           "fresh": "started again after the usage hold, in a fresh chat with a note"}.get(plan["mode"])
    status("BUILDING", f"Job {n} · " + (how or "started by the routine") + f" in {where}{watch_line(n)}",
           f"job {n} {how or 'started by the routine'}: {job['text'][:90]}")
    log(f"started job {n}" + (f" ({plan['mode']}, chat {plan['session']})" if how else ""))


def job_script_tmux(n, settings, pfile, chat=""):
    """H56.2: job n's script in a tmux session (bash): the same chat, its status line and nudge.py, which
    types into this session's own pane ($TMUX_PANE) instead of a Terminal tab."""
    return f"""#!/bin/bash
# Job {n}, started by the HQ routine (phase L) in the tmux session {hqpaths.session(f'job-{n}')} (H56.2).
cd {json.dumps(FOLDER)} || exit 1
echo "HQ · job {n}, started by the routine at $(date +%H:%M)."
echo "This is a normal chat: watch it, and type in between whenever you like. Leave it with Ctrl-b d; it closes by itself once the job is done."
echo
echo $$ > {json.dumps(PIDFILE)}
# H36: wakes the chat up when it has gone quiet (types continue into this pane only).
{json.dumps(PY)} {json.dumps(os.path.join(HERE, 'nudge.py'))} {n} "tmux:$TMUX_PANE" $$ </dev/null >/dev/null 2>&1 & disown
{CLAUDE} --no-chrome --permission-mode auto --settings {json.dumps(settings)} {chat} \\
  -n "HQ job {n}" "$(cat {json.dumps(pfile)})"
""" + CLOSE_WINDOW_TMUX


# The hourly mail check (L8). Only the Gmail reading tools, editing the mail list and its one commit
# script are allowed; everything else is refused without asking (dontAsk), so it never waits on anyone.
MAIL_ALLOW = ",".join([
    "Read", "Grep", "Glob", "Edit(/inbox.md)", "Bash(sh .claude/mail-commit.sh)",
    # H125: a mail that fits one of Donna's open mail watches is kept for her to text (only that command).
    f"Bash(python3 {os.path.join(JV, 'routine', 'pings.py')} match:*)",
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


def mail_every(at=None):
    """H148: seconds between mail checks at `at` (default now): 15 minutes during the test, else an hour."""
    at = time.time() if at is None else at
    return MAIL_FAST if MAIL_FAST_FROM <= at < MAIL_FAST_UNTIL else MAIL_EVERY


def mail_next(last):
    """H22: the mail check runs on the full hour (14:00, 15:00, …): the first full hour after its last start.
    H148: during the test, the first quarter (:00, :15, :30, :45) after it."""
    every = mail_every(last)
    return (int(last) // every + 1) * every


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


def mail(q, start_new=True):
    """L8, H30: the hourly mail check, on its own, also while a job runs. H56.3: a main that is handing its
    role back lets a running check finish but starts no new one (start_new False)."""
    if mail_running():
        return
    if not start_new:
        routines.beat("mail", state="ok", text="Handing over to the main one; it runs the next check", every=60)
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
                                                          else {"state": "ok", "text": "Waiting for its next hour" if mail_every() == MAIL_EVERY
                                                                    else "Waiting for its next quarter hour (H148 test)"}))


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
    # H125: with Donna's open mail watches in it, and the one command that keeps a match for her to text.
    open(instructions, "w").write(open(os.path.join(HERE, "mail-check.md")).read().replace("{WORKSPACE}", FOLDER)
                                  .replace("{WATCHES}", mail_watches()).replace("{PINGS}", os.path.join(JV, "routine", "pings.py")))
    open(cmd, "w").write(mail_script_tmux(instructions, run_file) if LINUX_WINDOWS else f"""#!/bin/zsh
# The hourly mail check, started by the HQ routine (phase L, L8). Hidden: opened in the
# background, minimized to the Dock, and the window closes itself when it's done (L7).
cd {json.dumps(FOLDER)} || exit 1
printf '\\e[2t'
printf '\\e]0;HQ mail check\\a'
echo "HQ · the hourly mail check, started by the routine at $(date +%H:%M). It closes by itself."
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
    open_window(cmd, "mail")
    log("started the mail check")
    routines.beat("mail", state="running", text="Started", last=time.time(), next=mail_next(time.time()), every=60)


def mail_watches():
    """H125: Donna's open mail watches, one line each, for the mail check's instructions."""
    try:
        import pings
        return pings.mail_watch_text()
    except Exception as e:
        log(f"mail watches: {e!r}")
        return "(no open mail watches)"


def mail_script_tmux(instructions, run_file):
    """H56.2: the mail check's script in its own hidden tmux session (bash), otherwise the same as on the Mac."""
    return f"""#!/bin/bash
# The hourly mail check, started by the HQ routine (L8) in the tmux session {hqpaths.session('mail')} (H56.2).
# Hidden; the session ends by itself when it's done.
cd {json.dumps(FOLDER)} || exit 1
echo "HQ · the hourly mail check, started by the routine at $(date +%H:%M). It closes by itself."
echo
echo $$ > {json.dumps(MAIL_PID)}
{{ echo "--- $(date '+%Y-%m-%d %H:%M:%S')"
  # L10: streamed, so the plan limits that come back with the run are saved, for free.
  {CLAUDE} -p --no-chrome --model sonnet --permission-mode dontAsk --no-session-persistence \\
    --output-format stream-json --verbose \\
    --allowedTools {json.dumps(MAIL_ALLOW)} --disallowedTools {json.dumps(MAIL_DENY)} \\
    < {json.dumps(instructions)} 2>&1 | {json.dumps(PY)} {json.dumps(STREAM)}
  echo "--- exit ${{PIPESTATUS[0]}}"
  {json.dumps(PY)} {json.dumps(USAGE)}; }} 2>&1 | tee -a {json.dumps(os.path.join(RUN, 'mail.log'))} {json.dumps(run_file)}
""" + CLOSE_WINDOW_TMUX


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
    r = subprocess.run([hqpaths.shell(), os.path.join(JV, "status", "phone.sh")], capture_output=True, text=True)
    for line in (r.stdout + r.stderr).strip().splitlines():
        log(line)
    up = listening(hqpaths.status_port())
    # H56.1: HQ_NO_PHONE=1 (a second HQ on one computer, or a test) leaves Tailscale alone; then the page alone counts.
    on_phone = NO_PHONE or ":8444" in tailscale_status()
    text = ("Status page up" if up and NO_PHONE else "Status page up, also on the phone" if up and on_phone
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
    return hqpaths.listening(port)


NO_PHONE = bool(os.environ.get("HQ_NO_PHONE"))
# H56.1: HQ_CALL_FIX=off: the call line is only reported, never started or changed (a second HQ on one
# computer that shares another's call line, or a test).
CALL_FIX = os.environ.get("HQ_CALL_FIX", "on") != "off"


def tailscale_status():
    return subprocess.run(hqpaths.tailscale("serve", "status"), capture_output=True, text=True).stdout


def call_line():
    # H19: the call line isn't a routine the helper runs, but it is what the calls need, so its state shows too.
    # H22: a real check every minute: the call page answers on this MacBook, and the phone address is on.
    import urllib.request
    port = hqpaths.call_port()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as r:
            answers = r.status == 200
    except Exception:
        answers = False
    phone = NO_PHONE or ":8443" in tailscale_status()
    now = time.time()
    if answers and phone:
        state, text = "ok", ("Up: the call page answers" if NO_PHONE
                             else "Up: the call page answers, and the phone address is on")
    elif answers:
        state, text = "down", "The call page answers, but the phone address is off: calls from the phone won't connect"
    elif listening(port):
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
    if not inc or not CALL_FIX:
        return
    tried = [f["at"] for f in inc.get("fixes", [])]
    quiet = not tried or now - max(tried) > 600
    if answers and not phone and now - inc["down"] >= 120 and quiet:
        subprocess.run(hqpaths.tailscale("serve", "--bg", "--https=8443", f"http://127.0.0.1:{port}"),
                       capture_output=True, timeout=30)
        incidents.fix("call", "Turned the phone address on again")
        log("call line: phone address turned on again")
    elif not listening(port) and now - inc["down"] >= 180 and quiet:
        out = open(os.path.join(JV, "scratch", "launchagent.log"), "a")
        start_sh = hqpaths.start_script()
        subprocess.Popen(["/bin/zsh" if hqpaths.IS_MAC else "/bin/bash", start_sh], stdout=out, stderr=out,
                         stdin=subprocess.DEVNULL, start_new_session=True)
        incidents.fix("call", f"Nothing was listening for 3 minutes: started it again (app/{os.path.basename(start_sh)})")
        log("call line: started it again")


def boottime():
    return hqpaths.boottime()


def waketime():
    return hqpaths.waketime()


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
        why = f"The {'MacBook' if hqpaths.IS_MAC else 'server'} restarted at {clock(boot)}"
    elif wake > old:
        why = f"The MacBook was asleep until {clock(wake)}"
    elif any("stuck" in w for _, w in events):
        why = "It got stuck"
    else:
        why = "It stopped; the reason isn't known"
    fixes = [(a, f"Watchdog: {w}") for a, w in events if old - 60 <= a <= now]
    if not fixes:
        fixes = ([(boot, "macOS started it at login" if hqpaths.IS_MAC else "systemd started it after the restart")]
                 if boot > old else [(now, "It came back on its own")])
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
        if hqpaths.IS_MAC:
            r = subprocess.run(["/bin/launchctl", "kickstart", f"gui/{os.getuid()}/{hqpaths.agent_label('watchdog')}"],
                               capture_output=True, text=True)
            who, fix = "macOS", "routine/install-watchdog.sh"
        else:
            # H56.1: on Linux the watchdog is a systemd timer; starting its service runs one check now,
            # and starting the timer puts it back on its five minutes.
            r = subprocess.run(["systemctl", "--user", "start", hqpaths.unit("watchdog.timer"), hqpaths.unit("watchdog.service")],
                               capture_output=True, text=True)
            who, fix = "systemd", "routine/install-linux.sh"
        incidents.fix("watchdog", f"Asked {who} to run it again" if r.returncode == 0
                      else f"Couldn't start it ({(r.stderr or r.stdout).strip()[:80]}); run {fix}")
        log(f"watchdog: asked {who} to run it again")


def jobs_line(q):
    running = q.get("running") or []
    waiting = len(q.get("ready") or []) + len(q.get("held") or [])
    if running:
        text = (f"Job {running[0]['n']} running" + (f", {waiting} waiting" if waiting else "")
                + watch_line(running[0]["n"]))
        state = "running"
    elif not q.get("on", True):
        text, state = "Switched off from a call", "off"
    elif waiting and os.path.exists(GATE_NOTE):
        # H30: waiting on purpose shows as waiting (yellow), with why, not as broken.
        n, _, why = open(GATE_NOTE).read().partition(" ")
        why = why.strip()
        why = why[4:].strip(" .:") if why.upper().startswith("STOP") else why
        text, state = f"Job {n} waits for the usage line: {why[:240]}", "waiting"
    else:
        text = f"{waiting} waiting" if waiting else "Nothing waiting; looks every minute"
        state = "ok"
    routines.beat("jobs", state=state, text=text, every=60)


def job_need(job):
    """H172: the job's estimated minutes and usage (made now, F34, from the finished jobs like it), as the gate's
    arguments: it starts only when that usage fits under each stop line. [] when it can't be had (the gate then uses
    H141's room for 10 minutes)."""
    try:
        import usagecost
        m, c = usagecost.job_cost(job["n"], job.get("text", ""))
        return ["--minutes", str(max(1, int(round(m)))), "--need", f"five={c['five']},weekly={c['weekly']}"]
    except Exception as e:
        log(f"estimate for the usage gate: {e!r}")
        return []


def usage_overrun(job, s):
    """H172: every minute while a job runs, its usage so far from the newest reading. At about twice its estimate it's
    paused for good: its chat ends, it isn't started again by itself (a call resumes or drops it), and Donna texts him.
    True when it paused it. The stop at the line itself stays the job's own (H113)."""
    import usagecost
    n = job["n"]
    rec = usagecost.track(n, job.get("text", ""))
    o = usagecost.overrun(rec)
    if not o:
        return False
    end_chat(s.get("pid"))
    jobs("mark", str(n), "paused: used about twice its estimated usage")
    try:
        import carryon
        carryon.on_held(n, open(hqpaths.ROADMAP, encoding="utf8").read())  # a resume carries on in its own chat
    except Exception as e:
        log(f"carry-on note for the paused job: {e!r}")
    usagecost.hold(n)
    clear()
    quiet.clear_request()
    line = "5-hour" if o["line"] == "five" else "weekly"
    why = (f"used {o['used']:g}% of the {line} usage, about twice its estimate of {o['est']:g}%; paused for good: "
           f"a call resumes it (jobs.py resume {n}) or drops it (jobs.py stop {n})")
    status("STOPPED", f"Job {n} paused: it used about twice its estimated usage", f"job {n} {why}")
    incidents.past("jobs", time.time(), time.time(), f"Job {n} {why}",
                   [(time.time(), "Ended its chat; it waits for a call, and Donna told him")])
    log(f"job {n} paused: {why}")
    try:
        import pings
        pings._spawn("paused", usagecost.paused_words(n, job.get("text", ""), o))
    except Exception as e:
        log(f"the text about the paused job: {e!r}")
    return True


def schedule_promote():
    """H43: the scheduler. Turns a due item into a job when the queue is empty; returns what it did."""
    r = subprocess.run([PY, os.path.join(HERE, "schedule.py"), "promote"], capture_output=True, text=True)
    out = r.stdout.strip()
    if r.returncode:
        log(f"schedule: {(r.stderr or out).strip()[:200]}")
        return ""
    if out.startswith("item "):
        log(f"schedule: {out}")
        what, job = out.split(" became ")
        prio = job.endswith("(priority)")  # H99: it went ahead of the waiting jobs
        job = job.split(",")[0]
        status("BUILDING", f"Scheduled {what} starts as {job}" + (", ahead of the waiting jobs" if prio else ""),
               f"scheduled {what} became {job}, " + ("first in line: it has priority" if prio
                                                     else "now that the job list is empty"))
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


def on_backup():
    """H56.3: this HQ is the backup. The other one runs the mail check, the jobs and the scheduler; their lines say so."""
    peer = role.config().get("peer_name") or "the other HQ"
    text = f"Runs on the main one, {peer}; this HQ is the backup"
    for key in ("mail", "jobs", "schedule"):
        routines.beat(key, state="ok", text=text, last=None, next=None, every=60, why="", detail=[], run="")
    clear(GATE_NOTE, TRUST_NOTE)


def stale_job_here():
    """H56.7: this HQ is the backup but a job it started still runs here: the lid was closed mid-job, the other
    one took over and ran it again (became_main), and now this one woke up. When the job list no longer shows
    that job running, its chat here is ended, so the same job never runs twice. Only that job's own chat."""
    s = load_state()
    if not s or not alive(s.get("pid")):
        return
    try:
        running = [j["n"] for j in json.loads(jobs("next")).get("running") or []]
    except Exception:
        return
    if s.get("n") in running:
        return
    end_chat(s.get("pid"))
    clear()
    quiet.clear_request()
    peer = role.config().get("peer_name") or "the other HQ"
    incidents.past("role", time.time(), time.time(), f"Job {s.get('n')} was still running here after {peer} took over",
                   [(time.time(), f"Ended its chat here: the job list says {peer} took it over")])
    log(f"role: ended job {s.get('n')}'s chat here; {peer} took it over while this one was away")


def became_main():
    """H56.3: this HQ has just become the acting main (it took over, or got the role back). The mail check waits
    for its next full hour instead of counting the hours the other one checked as missed, and a job the queue
    still shows running on the other one runs again here from the top of the line (H62's rerun)."""
    try:
        sync.align(log=log)  # H56.4: git lined up with GitHub first, keeping the files the sync brought
    except Exception as e:
        log(f"sync align: {e!r}")
    last = mail_last() or 0
    hour = int(time.time()) // mail_every() * mail_every()
    if last < hour:
        os.makedirs(RUN, exist_ok=True)
        open(MAIL_LAST, "w").write(str(hour))
        clear(MAIL_RETRY)
    q = json.loads(jobs("next"))
    s = load_state()
    for job in q.get("running") or []:
        if s is None or s.get("n") != job["n"]:
            peer = role.config().get("peer_name") or "the other HQ"
            out = jobs("crashed", str(job["n"]), f"the main one ({peer}) couldn't be reached while it ran, and this HQ took over")
            incidents.fix("role", out.strip()[:200])
            log(f"role: {out.strip()}")


def log_move():
    """H100: on the main, move the log's entries older than three hours to its archive, and commit both through
    the lock. A test never moves the real workspace's log."""
    if hqpaths.under_test() and FOLDER == os.path.realpath(os.path.join(JV, "workspace")):
        return
    n = log_cycle.move(FOLDER)
    if not n:
        return
    r = subprocess.run([PY, os.path.join(HERE, "gitlock.py"), "commit",
                        f"Log: {n} entr{'y' if n == 1 else 'ies'} older than {log_cycle.HOURS} hours moved to the archive",
                        log_cycle.LOG, log_cycle.ARCHIVE], capture_output=True, text=True, timeout=400)
    log(f"log cycle: moved {n} to the archive" + ("" if r.returncode == 0 else
        f"; commit failed ({r.returncode}): {(r.stderr or r.stdout).strip()[:200]}"))


def direct_watch():
    """H80: Donna texts on HQ's own direct line when the job list is finished, a very important mail comes in, or
    something stays down (and again when it's back). On the backup only this computer's own incidents (a takeover
    is texted by the one that took over). Never in a test on the real workspace."""
    if hqpaths.under_test() and FOLDER == os.path.realpath(os.path.join(JV, "workspace")):
        return
    sys.path.insert(0, os.path.join(JV, "app"))
    import direct_line
    main = role.acting() == "main"
    q = json.loads(jobs("next")) if main else None
    # F28: each look on its own, so one that fails doesn't stop the others (the incidents' one did, from H80 on).
    try:
        for why, facts in direct_line.watch(q, main=main):
            log(f"direct line: texting ({why})")
    except Exception as e:
        log(f"direct line: {e!r}")
    # H120: the weather every three hours in the day, on the main; she texts only when there's something to say.
    if main:
        try:
            import weather
            if weather.start():
                log("direct line: looking at the weather")
        except Exception as e:
            log(f"weather: {e!r}")
        # H101: his calendar, read only, every hour in the day, for the call page's calendar.
        try:
            import agenda
            if agenda.start():
                log("calendar: reading it (read only)")
        except Exception as e:
            log(f"calendar: {e!r}")
        # H143: an appointment X'd (or un-X'd) in the calendar sheet that still waits for its move to HQ Planning.
        try:
            import planning
            if planning.start():
                log("calendar: moving X'd appointments (HQ Planning)")
        except Exception as e:
            log(f"planning: {e!r}")
        # H124: Donna texts first: a ping when an appointment he picked starts, a reminder he asked for, and now and
        # then on her own about something on her own notes. H125: her watches' matches and ends too.
        try:
            import pings
            for why, _ in pings.watch():
                log(f"direct line: texting ({why})" if why != "initiative" else "direct line: her own look at her notes")
        except Exception as e:
            log(f"pings: {e!r}")


def tick():
    # H56.3: main or backup first. Alone (no other HQ set up) this is main at once, with no network and no line.
    try:
        r = role.tick(jobs_cmd=jobs, log=log, incidents=incidents, routines=routines, on_main=became_main)
    except Exception as e:
        log(f"role: {e!r}")
        r = {"acting": role.acting()}
    # H56.4: the two-way sync, on both: its line, conflict copies (the main queues a merge job), and on the main
    # a commit of what came over from the other side. Not set up (no second HQ): nothing at all.
    try:
        # H139: a main that is handing back (the chosen main answers again) queues no merge jobs and commits
        # nothing: the chosen main does, or both queue the same conflict copies.
        sync.tick(main=r["acting"] == "main" and not r.get("handing_back"), log=log, routines=routines,
                  incidents=incidents)
    except Exception as e:
        log(f"sync: {e!r}")
    # H88: the heartbeats, on both: this computer is up and online, the other one answers. Alone: nothing.
    try:
        heartbeat.tick(routines=routines, incidents=incidents, log=log)
    except Exception as e:
        log(f"heartbeat: {e!r}")
    # H81: the other HQ's finished jobs, for estimates on both computers (at most every two minutes, F34). Alone: nothing.
    try:
        estimate.pull(log=log)
    except Exception as e:
        log(f"estimates: {e!r}")
    # F34: once per version of the kinds and tags, this computer's finished jobs get them again (after a pull of dev).
    try:
        estimate.retag_if_needed(log=log)
    except Exception as e:
        log(f"estimates: retag: {e!r}")
    # H172: once on each computer, its past jobs' usage from the saved readings.
    try:
        import usagecost
        usagecost.backfill_once(log=log)
    except Exception as e:
        log(f"usage: backfill: {e!r}")
    if r["acting"] == "backup":
        stale_job_here()
        on_backup()
        return
    try:
        log_move()
    except Exception as e:
        log(f"log cycle: {e!r}")
    handing_back = r.get("handing_back")
    q = json.loads(jobs("next"))
    jobs_line(q)
    try:
        schedule_line()
    except Exception as e:
        log(f"schedule line: {e!r}")
    if not hqpaths.window_kind():
        # H56.1: off a Mac without tmux (H56.2) or the user's own local/open-window, there's no window for a
        # job or the mail check; both wait here, shown as off, and nothing is started.
        why = "Not on this computer yet: HQ has no window here to run it in (install tmux)"
        routines.beat("mail", state="off", text=why, every=60)
        routines.beat("jobs", state="off", text=why, every=60)
        return
    try:
        mail(q, start_new=not handing_back)  # H30: on its own, also while a job runs
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
        # H62: a pid from before a restart may belong to something else now, so after a restart the
        # chat counts as gone whatever that pid is.
        down = crash.went_down(job, s)
        if (down or not alive(pid)) and time.time() - s.get("started", 0) > 90:
            # H62: the Mac went down while it ran: the job runs again from the top of the line.
            if down and crash.recover(job, s, jobs, incidents, status, log, boot=down):
                clear()
                quiet.clear_request()
                return
            jobs("mark", str(n), "ended " + time.strftime("%H:%M") + " without a done mark")
            clear()
            incidents.past("jobs", time.time(), time.time(), f"Job {n}'s chat closed before it said it was done",
                           [(time.time(), "Marked it as ended, so the next job can start")])
            status("STOPPED", f"Job {n} ended without saying it was done",
                   f"job {n}: its chat closed before it said done; check the Terminal window or the log")
            log(f"job {n} ended without a done mark")
            return
        try:
            # H172: about twice its estimated usage: paused for good.
            if usage_overrun(job, s):
                return
        except Exception as e:
            log(f"usage count: {e!r}")
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
    if handing_back:
        # H56.3: the main one is back; this HQ starts nothing new and hands the role back at its next look.
        routines.beat("jobs", state="ok", text="Handing over to the main one; it starts the next job", every=60)
        routines.beat("schedule", state="ok", text="Handing over to the main one", every=60)
        return
    if not q["on"]:
        return
    # H39: the waiting job highest on the list goes first (ready, or held for the usage and now
    # given another go), not the oldest; a call can move them with jobs.py move.
    line = q.get("waiting")
    if line is None:
        line = (q["ready"] or []) + (q["held"] or [])
    # H43: the job list goes first; only with nothing running or waiting may a scheduled item whose time
    # has come become a job (at the bottom of the queue), and it starts right away. H99: an item with the
    # priority tag doesn't wait for the waiting jobs: with nothing running it goes first in line.
    did = schedule_promote()
    if did:
        q = json.loads(jobs("next"))
        line = q.get("waiting") or []
    if not line:
        return
    job = line[0]
    if LINUX_WINDOWS and not workspace_trusted():
        # H56.2: wait, and say what to do, instead of starting a chat into a question nobody answers.
        why = (f"Claude on this server hasn't been told to trust the workspace yet: run claude once in "
               f"{FOLDER} and answer yes")
        routines.beat("jobs", state="waiting", text=f"Job {job['n']} waits: {why}", every=60)
        if not os.path.exists(TRUST_NOTE):
            open(TRUST_NOTE, "w").write(str(job["n"]))
            status("STOPPED", f"Job {job['n']} waits: Claude doesn't trust the workspace on this server yet",
                   f"job {job['n']} waits: {why}")
            log(f"job {job['n']} waits: the workspace isn't trusted by Claude here")
        return
    clear(TRUST_NOTE)
    # F13: a job let past the line only skips the 5-hour line; the weekly line always counts, so a
    # past-the-line job held at the weekly line waits here quietly instead of being started every minute.
    # H172: it starts when its estimated usage (from the finished jobs like it) fits under each stop line; H141's
    # rates only for work with too little history (routine/usagecost.py).
    g = subprocess.run([NODE, os.path.join(JV, "status", "save-usage.mjs"), "--gate"]
                       + (["--weekly-only"] if job["past"] else []) + job_need(job),
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
        # H35 the laptop's temperature and macOS's heat warning, H37 its battery, H44 the totals Activity Monitor
        # shows (no line, no alarms), H45 whether it keeps working with the lid closed (only read here). Each
        # writes its own routine line. H56.1: these are the laptop's own, so Mac only.
        for name, script, timeout in (("temperature", TEMPERATURE, 150), ("battery", BATTERY, 60),
                                      ("stats", STATS, 150), ("lid sleep", LIDSLEEP, 30)) if hqpaths.IS_MAC else ():
            try:
                subprocess.run([PY, script], capture_output=True, text=True, timeout=timeout)
            except Exception as e:
                log(f"{name}: {e!r}")
        try:
            watchdog_check()
        except Exception as e:
            log(f"watchdog check: {e!r}")
        tick()
        try:
            direct_watch()
        except Exception as e:
            log(f"direct line: {e!r}")
    except Exception as e:  # never let one bad minute stop the next
        log(f"error: {e!r}")
        sys.exit(1)
