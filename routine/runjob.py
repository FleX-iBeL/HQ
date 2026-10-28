#!/usr/bin/env python3
"""A team job run headless (Fable, 27 October 2026; the backend switch `headless_jobs`).

Before this a job was an interactive chat in a Terminal or tmux window: the routine typed "continue" when it went
quiet, a shell under the chat counted as work, the done mark was a command the agent had to remember, and three
jobs sat idle for an hour this week because of exactly that (377, 393, 399). Here the job is a process: `claude -p`
with a streamed output, the prompt the routine wrote (`scratch/routine/job-N.prompt`), the same session id or
resume as before (so a held job carries on). The job's end is the process's end: when the roadmap still says the
job is running and the run ended well, the done mark is run for it. Its steps are read from the stream: each tool
call is a line in `scratch/routine/job-N.stream.log` (what to watch in the window) and a sign of life in
job-activity.json (the status page's Jobs line and the quiet watcher read it); the plan limits that come back with
the stream are saved for the usage check, as the mail check's are (L10). A SIGTERM (the usage pause, a stop from
a call) ends the claude process too, and nothing is marked done.

    python3 routine/runjob.py N [--session-id UUID | --resume UUID]
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402
import usagelive  # noqa: E402

FOLDER = hqpaths.FOLDER
# F65: HQ_JOB_RUN gives a test its own run folder (the prompt, the stream log, the activity), as tick.py does.
RUN = os.environ.get("HQ_JOB_RUN") or os.path.join(hqpaths.HQ, "scratch", "routine")
CLAUDE = hqpaths.tool("claude", "/opt/homebrew/bin/claude")
PY = sys.executable
ACTIVITY = os.environ.get("HQ_ACTIVITY") or os.path.join(RUN, "job-activity.json")
LINE_MOST = 160


def _log(f, line: str) -> None:
    stamp = time.strftime("%H:%M:%S")
    f.write(f"{stamp} {line}\n")
    f.flush()
    print(f"{stamp} {line}", flush=True)


def _activity(session: str | None, step: str) -> None:
    try:
        os.makedirs(os.path.dirname(ACTIVITY), exist_ok=True)
        tmp = ACTIVITY + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"at": time.time(), "session": session, "transcript": None, "step": step[:LINE_MOST]}, f)
        os.replace(tmp, ACTIVITY)
    except OSError:
        pass


def _step_of(block: dict) -> str:
    name = block.get("name") or "tool"
    inp = block.get("input") or {}
    what = ""
    if isinstance(inp, dict):
        for k in ("command", "file_path", "path", "pattern", "query", "url", "description"):
            if inp.get(k):
                what = str(inp[k])
                break
    what = " ".join(what.split())
    return f"{name} {what[:LINE_MOST]}".strip()


def _state(n: int) -> str:
    """The job's state on the roadmap (running since …, done …, held: …), or ''."""
    try:
        text = open(hqpaths.ROADMAP, encoding="utf8").read()
    except OSError:
        return ""
    import re
    m = re.search(rf"^- Job {n} · ([a-z][^·\n]*?)\s*(?:·|$)", text, re.M)
    return (m.group(1).strip() if m else "")


def _jobs(*args: str) -> str:
    r = subprocess.run([PY, os.path.join(HERE, "jobs.py"), *args], capture_output=True, text=True, timeout=120,
                       env={**os.environ, "HQ_ROLE_HERE": "1"})
    return (r.stdout + r.stderr).strip()


def main(argv: list[str]) -> int:
    if not argv or not argv[0].isdigit():
        print(__doc__)
        return 2
    n = int(argv[0])
    chat = argv[1:]
    pfile = os.path.join(RUN, f"job-{n}.prompt")
    stream_log = os.path.join(RUN, f"job-{n}.stream.log")
    os.makedirs(RUN, exist_ok=True)
    cmd = [CLAUDE, "-p", "--no-chrome", "--permission-mode", "auto", "--output-format", "stream-json", "--verbose",
           *chat]
    env = dict(os.environ)
    env.setdefault("HQ_JOB", str(n))
    with open(stream_log, "a") as lg, open(pfile, encoding="utf8") as prompt:
        _log(lg, f"job {n}: headless run started ({' '.join(chat) or 'a new session'})")
        proc = subprocess.Popen(cmd, stdin=prompt, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                cwd=FOLDER, env=env, bufsize=1)
        ended_by_signal = {"sig": None}

        def _end(sig, frame):
            ended_by_signal["sig"] = sig
            try:
                proc.terminate()
            except OSError:
                pass

        signal.signal(signal.SIGTERM, _end)
        signal.signal(signal.SIGINT, _end)
        session, windows, result, is_error, subtype, steps = None, None, None, False, None, 0
        _activity(None, "started")
        for line in proc.stdout:
            try:
                d = json.loads(line)
            except ValueError:
                s = line.rstrip()
                if s:
                    _log(lg, "claude: " + s[:LINE_MOST])
                continue
            t = d.get("type")
            if t == "system" and d.get("subtype") == "init":
                session = d.get("session_id") or session
                _activity(session, "session open")
            elif t == "rate_limit_event":
                windows = (d.get("rate_limit_info") or {}).get("unifiedWindows") or windows
            elif t == "assistant":
                for block in (d.get("message") or {}).get("content") or []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use":
                        steps += 1
                        step = _step_of(block)
                        _log(lg, step)
                        _activity(session, step)
                    elif block.get("type") == "text" and block.get("text", "").strip():
                        txt = " ".join(block["text"].split())
                        _log(lg, "says: " + txt[:LINE_MOST * 2])
                        _activity(session, "writing")
            elif t == "user":
                _activity(session, "tool result")
            elif t == "result":
                result = d.get("result") or ""
                is_error = bool(d.get("is_error"))
                subtype = d.get("subtype")
        code = proc.wait()
        if windows:
            try:
                usagelive.save(windows, f"job {n}")
            except Exception as e:
                _log(lg, f"usage not saved: {e!r}")
        sig = ended_by_signal["sig"]
        if sig:
            _log(lg, f"job {n}: ended by the routine (signal {sig}); nothing marked")
            return 0
        _log(lg, f"job {n}: claude ended (exit {code}, {steps} tool steps, result {subtype or '?'}"
                 f"{', error' if is_error else ''})")
        if result:
            _log(lg, "last words: " + " ".join(result.split())[:LINE_MOST * 3])
        state = _state(n)
        if state.startswith("running") or state.startswith("stop asked"):
            if code == 0 and not is_error:
                _log(lg, f"job {n}: still marked running on the roadmap; the done mark is run for it (headless)")
                _log(lg, _jobs("done", str(n)))
            else:
                _log(lg, f"job {n}: ended without finishing (exit {code}{', error' if is_error else ''}); left as it is "
                         "for the routine (it notes a chat that closed without a done mark)")
        else:
            _log(lg, f"job {n}: the roadmap says '{state or 'unknown'}', nothing to mark")
        return 0 if code == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
