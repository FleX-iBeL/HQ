#!/usr/bin/env python3
"""HQ's every-minute routine: one look, no Claude, so it costs no usage. Run every minute by the HQ Routine helper app on
a Mac (or its systemd timer on Linux). Nothing here starts, queues or runs work for a team: HQ only does what he asks.

What it does, every minute:
- Main or backup (routine/role.py), the two-way sync with the other HQ (routine/sync.py) and the heartbeats between the two
  computers (routine/heartbeat.py, with the Tailscale check). Alone (no other HQ set up): main, and none of this.
- The status server and its phone address (status/phone.sh), the call line (it answers; started again when nothing listens
  for three minutes), the usage check (routine/usage-check.py: the latest saved usage on the status page), the laptop's
  temperature, battery, totals and lid-closed sleep (Mac only), and the watchdog (the watchdog checks the helper, the
  helper checks the watchdog).
- On the main: the hourly mail check (routine/mail-check.md, hidden, in a window that closes itself; a missed hour runs
  at once, a failed run is tried again), the mail list's guard (routine/mailguard.py), the coaching log's three hours
  (routine/log_cycle.py), the briefing an agent starts with, the helpers beside a call, a version's data changes, saving
  the workspace's files left unsaved for ten minutes, and the agents' texts: Donna's look (direct_line.watch), the
  weather, travel on appointments, the calendar copy, Life coaching's check-ins, reminders, nudges and the six-week
  game's texts (routine/pings.py); and their own extensions' routines.
- On a friend's copy, first of all: the guard on the release (update.release_minute).

Every routine writes its own line for the status page (routine/routines.py) and the helper leaves a heartbeat for the
watchdog. Whatever goes down, why, what was done about it and when it was back goes in the incident log
(routine/incidents.py). The log: scratch/routine/routine.log.

    python3 routine/tick.py              one look
    python3 routine/tick.py --dry        one look that starts nothing: no window, no mail check, no server, no text sent,
                                         no commit; what it would do goes in the log (try it on a copy: HQ_WORKSPACE, HQ_SUPPORT)
    python3 routine/tick.py --mail-now   a test: the mail check right away
    python3 routine/tick.py --usage-now  a test: the usage check right away
"""
import json, os, re, signal, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routines  # every routine writes its own line for the status page
import incidents  # what went down, why, what was done, when it was back
import failures  # why a run failed, in plain words, and how many times in a row (the watchdog reads it)
import role  # main and backup; only the main runs the mail check
import heartbeat  # a heartbeat line for each of the two computers
import sync  # the two-way sync of the workspace and Claude's memory with the other HQ
import log_cycle  # the coaching log keeps three hours; older entries move to its archive
import mailguard  # a program holds the mail check to its rules, and says when it stopped
import hqpaths

HERE = os.path.dirname(os.path.abspath(__file__))
JV = os.path.normpath(os.path.join(HERE, ".."))
FOLDER = hqpaths.FOLDER
RUN = os.environ.get("HQ_JOB_RUN") or os.path.join(JV, "scratch", "routine")
DRY = "--dry" in sys.argv[1:] or os.environ.get("HQ_ROUTINE_DRY") == "1"  # nothing is started, sent or committed
MAIL_STATE = os.path.join(RUN, "mail.json")  # the running mail check: {"pid", "started"}
MAIL_PID = os.path.join(RUN, "mail.pid")  # written by the mail check's Terminal window
MAIL_LAST = os.path.join(RUN, "mail-last")  # epoch seconds of the last mail check start
MAIL_RETRY = os.path.join(RUN, "mail-retry")  # {"at", "n"}: a failed mail check is tried again
MAIL_RUNS = os.path.join(RUN, "mail-runs")  # each mail check's own output, one file per run
MAIL_RUNS_KEEP = 72
MAIL_EVERY = 3600
MAIL_FAST = 900  # every 15 minutes for a while he named (jobs.py mail-fast)
FAST_WINDOW = None
MAIL_LATE = 300  # a mail check that started over 5 minutes after its hour was missed
MAIL_RETRIES = 2
MAIL_RETRY_AFTER = 600
MAIL_TIMEOUT = 20 * 60
USAGE = os.path.join(HERE, "usage-check.py")  # no Claude, every minute
TEMPERATURE = os.path.join(HERE, "temperature.py")  # no Claude, no password, every minute
BATTERY = os.path.join(HERE, "battery.py")  # no Claude, every minute
STATS = os.path.join(HERE, "stats.py")  # CPU, GPU, memory, disk, network; no Claude, no password
LIDSLEEP = os.path.join(HERE, "lidsleep.py")  # lid-closed sleep on or off, read only; no Claude
STREAM = os.path.join(HERE, "stream-usage.py")  # the mail check's own run brings the usage back
NODE = hqpaths.tool("node", "/opt/homebrew/bin/node")
CLAUDE = hqpaths.tool("claude", "/opt/homebrew/bin/claude")
PY = sys.executable or "/usr/bin/python3"
TS_CALL = os.environ.get("HQ_TS_CALL_PORT") or "8443"  # the call line's phone address
TS_STATUS = os.environ.get("HQ_TS_STATUS_PORT") or "8444"  # the status server's phone address


def log(msg):
    os.makedirs(RUN, exist_ok=True)
    with open(os.path.join(RUN, "routine.log"), "a") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def jobs(*args):
    r = subprocess.run([PY, os.path.join(HERE, "jobs.py"), *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    return r.stdout


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


def clear(*paths):
    for p in paths:
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
    if DRY:
        log(f"dry: would open a window for {name or cmd}")
        return
    own = hqpaths.part_cmd("open-window", cmd)
    if own or hqpaths.IS_MAC:
        subprocess.run(own or ["/usr/bin/open", "-g", "-a", "Terminal", cmd], check=True)
        return
    sess = hqpaths.session(name)
    te = hqpaths.tmux_env()  # F138: the server TMUX_TMPDIR names (a copy's own), never the one of a pane this runs in
    subprocess.run([TMUX, "kill-session", "-t", "=" + sess], capture_output=True, env=te)  # an old one by that name
    envs = [x for k, v in os.environ.items() if k == "PATH" or k.startswith("HQ_") or k == "TMUX_TMPDIR" for x in ("-e", f"{k}={v}")]
    tm = [TMUX, "new-session", "-d", "-s", sess, "-x", "200", "-y", "50", *envs, "/bin/bash", cmd]
    scope = ["systemd-run", "--user", "--scope", "--quiet", f"--unit={sess}-{int(time.time())}-{os.getpid()}"]
    r = subprocess.run(scope + tm, capture_output=True, text=True, env=te) if os.environ.get("XDG_RUNTIME_DIR") else None
    if r is None or (r.returncode and not subprocess.run([TMUX, "has-session", "-t", "=" + sess], capture_output=True, env=te).returncode == 0):
        r = subprocess.run(tm, capture_output=True, text=True, env=te)  # no systemd scope here: tmux on its own
    if r.returncode:
        raise RuntimeError(f"tmux couldn't open {sess}: {(r.stderr or r.stdout).strip()[:200]}")


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
    comm = r.stdout.strip()
    return os.path.basename(comm) in ("claude", "claude.exe") or comm.endswith("claude")  # claude.exe: the native build on Linux


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


# The hourly mail check (L8). Only the Gmail reading tools, editing the mail list and its one commit
# script are allowed; everything else is refused without asking (dontAsk), so it never waits on anyone.
MAIL_ALLOW = ",".join([
    "Read", "Grep", "Glob", "Edit(/inbox.md)", "Bash(sh .claude/mail-commit.sh)",
    # H125: a mail that fits one of Donna's open mail watches is kept for her to text (only that command).
    f"Bash(python3 {os.path.join(JV, 'routine', 'pings.py')} match:*)",
    # F109: which of the mails the date searches found can be new (only reads; only that command).
    f"Bash(python3 {os.path.join(JV, 'routine', 'mailguard.py')} newer:*)",
    # F110: every search and its number of threads, so a program knows what was really reached (only that command).
    f"Bash(python3 {os.path.join(JV, 'routine', 'mailguard.py')} reach:*)",
    "mcp__claude_ai_Gmail__search_threads", "mcp__claude_ai_Gmail__get_thread", "mcp__claude_ai_Gmail__get_message",
])


MAIL_DENY = ",".join("mcp__claude_ai_Gmail__" + t for t in (
    "send_message", "reply", "forward", "create_draft", "update_draft", "delete_draft", "label_message",
    "label_thread", "unlabel_message", "unlabel_thread", "update_message_labels", "trash_message", "trash_thread",
    "mark_message_spam", "mark_thread_spam", "apply_sensitive_message_label", "apply_sensitive_thread_label",
    "create_label", "delete_label", "update_label")) + ",Write,NotebookEdit,WebFetch,WebSearch"


# H213: with sorting rules on, the mail check may also add and remove labels on whole conversations (the label and
# the archive, which is taking INBOX off) and look up the labels' ids, and note each mail sorted. Nothing else changes:
# no sending, drafts, trash, spam, read marks or label changes; without rules it stays read-only.
MAIL_SORT_TOOLS = ("mcp__claude_ai_Gmail__list_labels", "mcp__claude_ai_Gmail__label_thread",
                   "mcp__claude_ai_Gmail__unlabel_thread")


def mail_sorting():
    try:
        import mailsort
        return mailsort.any_on()
    except Exception as e:
        log(f"mail sorting rules: {e!r}")
        return False


def mail_tools(sorting=None):
    """The mail check's allowed and refused tools for this run (H213: the label tools only with sorting rules on;
    H235: their own extensions' mail scripts)."""
    sorting = mail_sorting() if sorting is None else sorting
    ext = ""
    try:
        extensions = _ext()
        ext = "".join("," + t for t in extensions.mail_tools())
    except Exception as e:
        log(f"extensions: {e!r}")
    if not sorting:
        return MAIL_ALLOW + ext, MAIL_DENY
    allow = MAIL_ALLOW + "," + ",".join(MAIL_SORT_TOOLS) + \
        f",Bash(python3 {os.path.join(JV, 'routine', 'mailsort.py')} sorted:*)" + ext
    deny = ",".join(t for t in MAIL_DENY.split(",") if t not in MAIL_SORT_TOOLS)
    return allow, deny


def _ext():
    """H235: app/extensions.py (stdlib only)."""
    app = os.path.join(JV, "app")
    if app not in sys.path:
        sys.path.insert(0, app)
    import extensions
    return extensions


def mail_ext_text():
    """H235: the extra steps their own extensions add to the mail check."""
    try:
        return _ext().mail_steps()
    except Exception as e:
        log(f"extensions: {e!r}")
        return "(no extensions add steps)"


def mail_instructions(text=None):
    """The hourly mail check's instructions as its run gets them: routine/mail-check.md (or the text given, an older version for a
    test) filled in for this workspace. H125: with Donna's open mail watches in it, and the one command that keeps a match for her to text."""
    return ((open(os.path.join(HERE, "mail-check.md")).read() if text is None else text).replace("{WORKSPACE}", FOLDER)
            .replace("{WATCHES}", mail_watches()).replace("{PINGS}", os.path.join(JV, "routine", "pings.py"))
            .replace("{SORTING}", mail_sort_text()).replace("{MAILSORT}", os.path.join(JV, "routine", "mailsort.py"))
            .replace("{QUIET}", mail_quiet_text()).replace("{EXTENSIONS}", mail_ext_text()).replace("{SEARCHES}", mailguard.search_text())
            .replace("{MAILGUARD}", os.path.join(JV, "routine", "mailguard.py")))


def mail_quiet_text():
    """H235, gap 1: what the mail check does on a quiet hour (nothing newer than the marker in Gmail). Without an extension's mail
    step it stops as before; with one, only that step runs."""
    try:
        return _ext().quiet_step()
    except Exception as e:
        log(f"extensions: {e!r}")
        return _QUIET_STOP


_QUIET_STOP = "If nothing is newer than the marker, stop: change nothing, commit nothing."


def extensions_minute():
    """H235: their own extensions' routines that are due, started in the background; and once per finished update,
    the local check whether anything they added might clash with it. On the main HQ only for the routines (the
    backup runs none of the user's work); the check on both, since each has its own update."""
    extensions = _ext()
    try:
        found = extensions.after_update()
        if found:
            log(f"extensions: checked after the update to {found['to']}: {len(found['clashes'])} might clash")
    except Exception as e:
        log(f"extensions check: {e!r}")
    if role.acting() != "main" or updating():
        return
    if DRY:
        log("dry: would start their extensions' routines that are due")
        return
    r = extensions.routines()
    if r["started"]:
        log("extensions: started " + ", ".join(r["started"]))
    if extensions.all_():
        routines.beat("extensions", state=r["state"], text=r["text"], last=time.time(), next=time.time() + 60, every=60)
    else:
        routines.drop("extensions")


def mail_sort_text():
    """H213: the sorting rules that are on, for the mail check's instructions."""
    try:
        import mailsort
        return mailsort.text()
    except Exception as e:
        log(f"mail sorting rules: {e!r}")
        return "(no sorting rules)"


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
            mailguard.after_run(False, incidents, routines, log=log)  # F110: a run cut off still holds the marker; the guard too
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
    if mailguard.after_run(ok, incidents, routines, log=log):  # F102: the list put back, the incident open
        res, ok = {**res, "ok": False}, False
        text = "The list it left broke the rules, so it was put back"
    routines.beat("mail", state="ok" if ok else "down", text=text, last=started, next=mail_next(started), every=60,
                  why=res.get("why", ""), detail=res.get("detail", []), run=res.get("run", ""))
    if ok:
        clear(MAIL_RETRY)
        failures.record("mail", True)
        incidents.up("mail", what="The next mail check ran fine")
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


def fast_window():
    """H149: (from, until) epoch seconds while the mail check runs every 15 minutes for a while he named, else None."""
    if FAST_WINDOW is not None:
        return tuple(FAST_WINDOW) or None
    try:
        import importlib
        q = importlib.import_module("jobs")
        q.read()
        return q.MAIL_FAST
    except Exception:
        return None


def mail_every(at=None):
    """H148, H149: seconds between mail checks at `at` (default now): 15 minutes in his window, else an hour."""
    at = time.time() if at is None else at
    w = fast_window()
    return MAIL_FAST if w and w[0] <= at < w[1] else MAIL_EVERY


def mail_next(last):
    """H22: the mail check runs on the full hour (14:00, 15:00, …): the first full hour after its last start.
    H148, H149: in his window, the first quarter (:00, :15, :30, :45) after the last start, or after the moment he
    asked for it when that's later (so asking never counts as a missed run); past its end, the full hour again."""
    hour = (int(last) // MAIL_EVERY + 1) * MAIL_EVERY
    w = fast_window()
    if w and last < w[1]:
        quarter = (int(max(last, w[0])) // MAIL_FAST + 1) * MAIL_FAST
        if quarter <= w[1]:
            return min(hour, quarter)
    return hour


def mail_words():
    """H149: how often it runs now, for the status page."""
    w = fast_window()
    if w and w[0] <= time.time() < w[1]:
        return f"Every 15 minutes until {clock(w[1])}{'' if time.strftime('%Y%m%d', time.localtime(w[1])) == time.strftime('%Y%m%d') else ' ' + time.strftime('%a %-d %b', time.localtime(w[1]))}, then every hour by itself"
    return "Every hour"


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
    if DRY:
        log(f"dry: the mail check is {'due: it would start now' if mail_due() else 'not due'}")
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
    routines.beat("mail", last=last, next=nxt, every=60, about=mail_words(),
                  **({} if routines.read().get("mail", {}).get("state") in ("ok", "down")
                     else {"state": "ok", "text": "Waiting for its next hour" if mail_every() == MAIL_EVERY
                           else "Waiting for its next quarter hour (asked for, H149)"}))


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
    open(instructions, "w").write(mail_instructions())
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
    --allowedTools {json.dumps(mail_tools()[0])} --disallowedTools {json.dumps(mail_tools()[1])} \\
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
    mailguard.before()  # F102
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
    --allowedTools {json.dumps(mail_tools()[0])} --disallowedTools {json.dumps(mail_tools()[1])} \\
    < {json.dumps(instructions)} 2>&1 | {json.dumps(PY)} {json.dumps(STREAM)}
  echo "--- exit ${{PIPESTATUS[0]}}"
  {json.dumps(PY)} {json.dumps(USAGE)}; }} 2>&1 | tee -a {json.dumps(os.path.join(RUN, 'mail.log'))} {json.dumps(run_file)}
""" + CLOSE_WINDOW_TMUX


# The usage check (L10). Every minute, no Claude: the latest saved usage (a job's status line, or the
# mail check's own run) goes on the status page with how old it is.
def usage():
    if DRY:
        log("dry: the usage check would save the latest reading")
        return
    r = subprocess.run([PY, USAGE], capture_output=True, text=True, timeout=60)
    first = next((l.strip() for l in r.stdout.splitlines() if l.strip()), "")
    routines.beat("usage", state="ok" if r.returncode == 0 else "down", last=time.time(), next=time.time() + 60,
                  every=60, text=(first or "Ran") if r.returncode == 0 else f"Failed: {(r.stderr or r.stdout).strip()[:120]}")
    if r.returncode == 0:
        incidents.up("usage", what="The next usage check ran fine")
    else:
        incidents.down("usage", f"Failed: {(r.stderr or r.stdout).strip()[:120]}")


def status_page():
    # H13: the status server and its Tailscale address; a line in the log only when something was started.
    if DRY:
        log(f"dry: the status server {'answers' if listening(hqpaths.status_port()) else 'is not running; phone.sh would start it'}")
        return
    r = subprocess.run([hqpaths.shell(), os.path.join(JV, "status", "phone.sh")], capture_output=True, text=True)
    for line in (r.stdout + r.stderr).strip().splitlines():
        log(line)
    up = listening(hqpaths.status_port())
    # H56.1: HQ_NO_PHONE=1 (a second HQ on one computer, or a test) leaves Tailscale alone; then the page alone counts.
    on_phone = NO_PHONE or f":{TS_STATUS}" in tailscale_status()
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
            incidents.up("phone", what="The status page and its phone address answer again")
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
    phone = NO_PHONE or f":{TS_CALL}" in tailscale_status()
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
    # answering without the phone address: turn the address on again. F102: a line that listens but doesn't answer
    # for 3 minutes is hung, with or without a call on it: that exact process ends, and it starts again.
    if state == "ok":
        incidents.up("call", what="The call line answers again")
        return
    inc = incidents.down("call", text)
    if not inc or not CALL_FIX or DRY:
        return
    tried = [f["at"] for f in inc.get("fixes", [])]
    quiet = not tried or now - max(tried) > 600
    if answers and not phone and now - inc["down"] >= 120 and quiet:
        subprocess.run(hqpaths.tailscale("serve", "--bg", f"--https={TS_CALL}", f"http://127.0.0.1:{port}"),
                       capture_output=True, timeout=30)
        incidents.fix("call", "Turned the phone address on again")
        log("call line: phone address turned on again")
    elif not answers and now - inc["down"] >= 180 and quiet:
        hung = hqpaths.listener(port) if listening(port) else None
        if hung:
            try:
                os.kill(hung, signal.SIGTERM)
            except OSError as e:
                log(f"call line: couldn't end {hung}: {e!r}")
            time.sleep(3)
            log(f"call line: it listened but didn't answer for 3 minutes; ended pid {hung}")
        out = open(os.path.join(JV, "scratch", "launchagent.log"), "a")
        start_sh = hqpaths.start_script()
        subprocess.Popen(["/bin/zsh" if hqpaths.IS_MAC else "/bin/bash", start_sh], stdout=out, stderr=out,
                         stdin=subprocess.DEVNULL, start_new_session=True)
        incidents.fix("call", f"{'It listened but didn’t answer' if hung else 'Nothing was listening'} for 3 minutes: started it again (app/{os.path.basename(start_sh)})")
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
        incidents.up("watchdog", what="The watchdog wrote its line again")
        return
    inc = incidents.down("watchdog", f"No check from the watchdog since {clock(at)}" if at else "The watchdog has never checked in")
    tried = [f["at"] for f in (inc or {}).get("fixes", [])]
    if DRY:
        log("dry: the watchdog hasn't checked in; it would be asked to run again")
        return
    if not tried or now - max(tried) > 600:
        if hqpaths.IS_MAC:
            r = subprocess.run(["/bin/launchctl", "kickstart", f"gui/{os.getuid()}/{hqpaths.agent_label('watchdog')}"],
                               capture_output=True, text=True)
            who, fix = "macOS", "routine/install-watchdog.sh"
        else:
            # H56.1: on Linux the watchdog is a systemd timer; starting its service runs one check now,
            # and starting the timer puts it back on its five minutes. F138: only this HQ's own units (HQ_UNIT), and only when
            # they're installed: a copy (the chain check) has none, so it asks nothing of systemd and says so.
            timer = hqpaths.unit("watchdog.timer")
            if not os.path.exists(os.path.join(os.path.expanduser("~/.config/systemd/user"), timer)):
                incidents.fix("watchdog", f"No watchdog of its own here ({timer} isn't installed); nothing to start")
                log(f"watchdog: {timer} isn't installed here; nothing asked of systemd")
                return
            r = subprocess.run(["systemctl", "--user", "start", timer, hqpaths.unit("watchdog.service")],
                               capture_output=True, text=True)
            who, fix = "systemd", "routine/install-linux.sh"
        incidents.fix("watchdog", f"Asked {who} to run it again" if r.returncode == 0
                      else f"Couldn't start it ({(r.stderr or r.stdout).strip()[:80]}); run {fix}")
        log(f"watchdog: asked {who} to run it again" if r.returncode == 0 else f"watchdog: {who} couldn't start it")


def on_backup():
    """This HQ is the backup. The other one runs the mail check; its line says so."""
    peer = role.config().get("peer_name") or "the other HQ"
    text = f"Runs on the main one, {peer}; this HQ is the backup"
    for key in ("mail",):
        routines.beat(key, state="ok", text=text, last=None, next=None, every=60, why="", detail=[], run="")
    for key in ("maillist", "mailmarker", "mailreach", "saving") + PART_LINES[1:]:  # F102: these run on the main only; never overdue here (F116: Donna's parts too)
        if key in routines.read():
            routines.beat(key, state="ok", text=text, last=None, next=None, every=60, why="")
    incidents.up("mailmarker", what="This HQ is the backup now; the main keeps that watch")  # F109: the main keeps that watch
    incidents.up("mailreach", what="This HQ is the backup now; the main reads the mail")  # F110


def became_main():
    """This HQ has just become the acting main (it took over, or got the role back). The mail check waits for its next
    full hour instead of counting the hours the other one checked as missed."""
    try:
        sync.align(log=log)  # git lined up with GitHub first, keeping the files the sync brought
    except Exception as e:
        log(f"sync align: {e!r}")
    last = mail_last() or 0
    hour = int(time.time()) // mail_every() * mail_every()
    if last < hour:
        os.makedirs(RUN, exist_ok=True)
        open(MAIL_LAST, "w").write(str(hour))
        clear(MAIL_RETRY)


def helper_minute():
    """F106: on both computers: a helper that died without a word ends as failed and is told, and an answer whose call is gone goes as a text."""
    if DRY:
        return
    import helper
    sent = helper.minute()
    if sent:
        log(f"helpers: told by text: {', '.join(sent)}")


def briefing_minute():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
    import backend
    if not backend.on("briefing"):
        routines.drop("briefing")
        return
    import briefing
    briefing.write()
    routines.good("briefing", "Written")


LOOK_FAILED = "The routine's look failed"


def guarded(key, fn, every=60):
    """F102: a part of the minute: a failure turns its line red and opens an incident, and doesn't stop the next one. A later
    good look closes what a look opened; a reviewer's own runs keep their own line."""
    try:
        r = fn()
    except Exception as e:
        log(f"{key}: {e!r}")
        routines.bad(key, f"{LOOK_FAILED}: {e!r}", every=every)
        return None
    open_ = incidents.is_down(key)
    if open_ and str(open_.get("why", "")).startswith(LOOK_FAILED):
        routines.good(key, "Looks again", every=every)
    return r


def data_minute():
    """F104: on the main, a version's new data changes run (a tag's or the work line's), and the other computer hears what it
    missed. Not while HQ stands on an older version: going back undid them on purpose."""
    try:
        import datachange
        import update
        if not update.gone_back():
            did = datachange.apply(log=log)
            if did:
                log(f"data changes run: {', '.join(did)}")
        said = update.other_minute()
        if said:
            log(said)
        if "data" in routines.read():  # F116: a failure's red line closes once the changes run again
            routines.good("data", "The data changes ran", every=3600)
    except Exception as e:
        log(f"data changes: {e!r}")
        routines.bad("data", f"A data change failed: {e!r}", every=3600)


def save_minute():
    """F102: every workspace file left unsaved for ten minutes committed by the main itself."""
    import saver
    try:
        files = saver.minute(log=log)
    except Exception as e:
        routines.bad("saving", f"Saving the workspace failed: {e}", every=300)
        return
    routines.good("saving", f"Saved {len(files)} file(s) just now" if files else "Everything older than ten minutes is saved", every=300)


def log_move():
    """H100: on the main, move the log's entries older than three hours to its archive, and commit both through
    the lock. A test never moves the real workspace's log."""
    if (hqpaths.under_test() and FOLDER == os.path.realpath(os.path.join(JV, "workspace"))) or DRY:
        return
    n = log_cycle.move(FOLDER)
    if not n:
        return
    r = subprocess.run([PY, os.path.join(HERE, "gitlock.py"), "commit",
                        f"Log: {n} entr{'y' if n == 1 else 'ies'} older than {log_cycle.HOURS} hours moved to the archive",
                        log_cycle.LOG, log_cycle.ARCHIVE], capture_output=True, text=True, timeout=400)
    log(f"log cycle: moved {n} to the archive" + ("" if r.returncode == 0 else
        f"; commit failed ({r.returncode}): {(r.stderr or r.stdout).strip()[:200]}"))


PART_LINES = ("donna", "reminders", "weather", "calendar", "coaching")  # F116: the parts of Donna's minute, a line each


def part_line(key, fn, name=None):
    """F116: one part of Donna's minute: its own line on the status page every minute, red with an incident when it fails, so
    nothing of hers goes quiet; the next good minute closes it. A failure never stops the next part."""
    try:
        said = fn()
    except Exception as e:
        log(f"{name or key}: {e!r}")
        routines.bad(key, f"It failed: {e!r}", every=60)
        return
    routines.good(key, said or "Looked", every=60)


def direct_watch():
    """Donna texts on HQ's own direct line when a very important mail comes in or something stays down (and again when
    it's back); on the main also the weather, travel on appointments, Life coaching's check-ins, the calendar copy and
    the reminders, nudges and the game's texts. On the backup only this computer's own incidents. Never in a test on the
    real workspace. With --dry the looks are made and nothing is sent or started."""
    if hqpaths.under_test() and FOLDER == os.path.realpath(os.path.join(JV, "workspace")):
        return
    sys.path.insert(0, os.path.join(JV, "app"))
    import direct_line
    main = role.acting() == "main"

    def watch():  # each look on its own, with its own line: a failure turns it red, and doesn't stop the others
        n = 0
        for why, facts in direct_line.watch(main=main, dry=DRY):
            log(f"direct line: {'would text' if DRY else 'texting'} ({why})")
            n += 1
        return f"Texted {n} just now" if n else "Looked; nothing to text"
    part_line("donna", watch, "direct line")

    def pings_():  # a ping when an appointment starts, a reminder, a nudge, the game's texts, her watches
        import pings
        n = 0
        for why, _ in pings.watch(dry=DRY):
            log(f"direct line: {'would text' if DRY else 'texting'} ({why})" if why != "initiative" else "direct line: her own look at her notes")
            n += 1
        return f"Texted {n} just now" if n else "Looked; nothing due"
    if DRY:
        if main:
            part_line("reminders", pings_, "pings")
        log("dry: the weather, the trips, the calendar copy and the check-ins would be looked at")
        return
    if main:
        def weather_():  # every three hours in the day; she texts only when there's something to say
            import weather
            if weather.start():
                log("direct line: looking at the weather")
                return "Looking at the weather now"
            return "Looked; not due yet"
        part_line("weather", weather_)
        try:  # travel on appointments: trips for new ones, and the live watch on the open data before each one
            import trips
            if trips.start():
                log("travel: looking at the trips")
        except Exception as e:
            log(f"travel: {e!r}")

        def coaching_():  # Life coaching's check-ins: one that comes due lands in the coaching line
            import coaching
            due = list(coaching.refresh())
            for key in due:
                log(f"coaching: a check-in is due ({key})")
            return f"A check-in is due: {', '.join(due)}" if due else "Looked; none due"
        part_line("coaching", coaching_)

        def calendar_():  # his calendar, read only, every hour in the day, for the app's calendar
            import agenda
            if agenda.start():
                log("calendar: reading it (read only)")
                return "Reading it now (read only)"
            return "Looked; not due yet"
        part_line("calendar", calendar_)
        try:  # an appointment an old X moved to HQ Planning that still waits to go back where it came from
            import planning
            if planning.start():
                log("calendar: moving old X'd appointments back from HQ Planning")
        except Exception as e:
            log(f"planning: {e!r}")
        part_line("reminders", pings_, "pings")


def updating():
    """H187: True while update.py installs an update (its run file says updating, its pid lives, under 30 minutes):
    it ended the job, the mail check and the call, and the routine starts none of them until it's done."""
    try:
        u = json.load(open(os.path.join(JV, ".status", "update-run.json")))
    except (OSError, ValueError):
        return False
    return u.get("state") == "updating" and alive(u.get("pid")) and time.time() - u.get("at", 0) < 1800


def release_minute():
    """F104: first of all, every minute, on a copy that isn't the maker's: does what's checked out hold unreleased work? True: it's going
    back on the newest release and nothing starts on top of it this minute, above all no data change. A flow turns it on by HQ_RELEASE_MINUTE:
    a flow's copy of HQ is often a friend's in name and stands past a version."""
    if (hqpaths.under_test() and not os.environ.get("HQ_RELEASE_MINUTE")) or DRY:
        return False
    try:
        import update
        said = update.release_minute(log=log)
    except Exception as e:  # a look that fails finds nothing: it never stops an HQ, and it's said
        log(f"release guard: {e!r}")
        routines.bad("release", f"The look at what's checked out failed: {e!r}", every=3600)
        return False
    if said:
        routines.beat("release", state="waiting", text=said, every=60)
    return bool(said)


# Lines and incidents of parts HQ no longer has (the team, its queue, the planned items, the nights, the reviews, QA,
# releases by the team, the agents' own cycles, news, feedback): taken off the status page, and an incident of theirs
# that's still open is closed, so nothing waits on a part that's gone.
GONE = ("jobs", "schedule", "cycles", "line", "mistakes", "news", "nightly", "qa", "review", "feedback", "about",
        "side-by-side", "whole-build", "estimates", "night-road", "mac-half", "github")


def gone_lines():
    have = routines.read()
    for key in GONE:
        if key in have:
            routines.drop(key, keep=tuple(k for k in have if k != key))
        try:
            if incidents.is_down(key):
                inc = incidents._open(incidents.read(), key) or {}
                incidents.up(key, what="That part is no longer in HQ")
                quiet_close(str(inc.get("id")))
        except Exception as e:
            log(f"gone lines: {key}: {e!r}")


def quiet_close(iid):
    """A part that left HQ isn't 'back': Donna forgets she told him it was down, so its close sends no all-clear text."""
    sys.path.insert(0, os.path.join(JV, "app"))
    import direct_line
    path = direct_line.local_state_file()
    s = direct_line._read(path, {})
    if iid in (s.get("told") or {}):
        s["told"].pop(iid)
        direct_line._write(path, s)


def tick():
    if release_minute():
        return
    # Main or backup first. Alone (no other HQ set up) this is main at once, with no network and no line.
    try:
        r = role.tick(log=log, incidents=incidents, routines=routines, on_main=became_main)
    except Exception as e:
        log(f"role: {e!r}")
        r = {"acting": role.acting()}
    # The two-way sync, on both. A main that is handing back commits nothing: the chosen main does.
    try:
        sync.tick(main=r["acting"] == "main" and not r.get("handing_back"), log=log, routines=routines,
                  incidents=incidents, acting=r["acting"])
    except Exception as e:
        log(f"sync: {e!r}")
    try:  # the heartbeats, on both: this computer is up and online, the other one answers. Alone: nothing.
        heartbeat.tick(routines=routines, incidents=incidents, log=log)
    except Exception as e:
        log(f"heartbeat: {e!r}")
    guarded("briefing", briefing_minute)  # the briefing an agent starts with, on both computers
    if not hqpaths.under_test() or os.environ.get("HQ_HELPER_MINUTE"):
        guarded("helpers", helper_minute)
    if r["acting"] == "backup":
        on_backup()
        if not hqpaths.under_test() and not DRY:  # the main was off when this one went back a version
            try:
                import update
                update.other_minute()
            except Exception as e:
                log(f"telling the main: {e!r}")
        return
    if (not hqpaths.under_test() or os.environ.get("HQ_SAVE_QUIET")) and not DRY:
        save_minute()
    if release_minute():  # the head can have moved since this minute began; a data change of dev's must never run
        return
    if (not hqpaths.under_test() or os.environ.get("HQ_DATA_MINUTE")) and not DRY:
        data_minute()
    try:
        log_move()
    except Exception as e:
        log(f"log cycle: {e!r}")
    handing_back = r.get("handing_back")
    q = json.loads(jobs("next"))  # the mail check's switch and how often it runs, from the queue section's lines
    if not hqpaths.window_kind():
        # Off a Mac without tmux there's no window for the mail check: it waits here, shown as off.
        routines.beat("mail", state="off", text="Not on this computer yet: HQ has no window here to run it in (install tmux)", every=60)
        return
    if updating():
        return  # an update is being installed; nothing starts until the new code is in
    try:
        mail(q, start_new=not handing_back)  # on its own hour
    except Exception as e:
        log(f"mail: {e!r}")
    try:
        mailguard.minute(q.get("mail", True), incidents, routines)  # red when it hasn't been checked for 2 hours
    except Exception as e:
        log(f"mail list: {e!r}")


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--mail-now"]:  # a test: start the mail check right away
            start_mail()
            sys.exit(0)
        if sys.argv[1:] == ["--usage-now"]:  # a test: the usage check, right away
            usage()
            sys.exit(0)
        if release_minute():  # before anything else runs
            routines.heartbeat()
            sys.exit(0)
        try:
            helper_gap()
        except Exception as e:
            log(f"helper gap: {e!r}")
        routines.heartbeat()
        routines.beat("helper", state="ok", text="Looks every minute", last=time.time(), next=time.time() + 60, every=60)
        gone_lines()
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
        # The laptop's temperature and macOS's heat warning, its battery, the totals Activity Monitor shows (no line, no
        # alarms), and whether it keeps working with the lid closed (only read here). Mac only.
        for name, script, timeout in (("temperature", TEMPERATURE, 150), ("battery", BATTERY, 60),
                                      ("stats", STATS, 150), ("lid sleep", LIDSLEEP, 30)) if hqpaths.IS_MAC and not DRY else ():
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
        try:
            extensions_minute()
        except Exception as e:
            log(f"extensions: {e!r}")
    except Exception as e:  # never let one bad minute stop the next
        log(f"error: {e!r}")
        sys.exit(1)
