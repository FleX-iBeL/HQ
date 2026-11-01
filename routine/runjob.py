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

    python3 routine/runjob.py N [--session-id UUID | --resume UUID] [--max-minutes M] [--max-turns T] [--box-note FILE]
                                [--box-state]

H298, piece 3 (29 October 2026): a deterministic box on the run, read from the run's own stream and a wall clock, no
estimate involved: `--max-minutes M` and `--max-turns T` (a turn is one assistant message; claude's own --max-turns is
set too). Past either, the run is ended (SIGTERM to claude), what it wrote stays, the done mark is run as for a run
that ended well (a boxed run is a finished run), and `--box-note FILE` gets a JSON note of what happened: minutes,
turns, steps, boxed (minutes, turns or null), the tools used with their paths, and the tool results that read as a
refusal, so the agents' runner (routine/cycles.py) can mark the run boxed in her ledger and count its tripwires.

F100, the usage wall (31 October 2026): every team job gets the same box (tick.py, from wall.py) with `--box-state`: past it
the job is `boxed`, not done, parked for a call. The minutes count its own work: the time its own test run took
(proof.py) is left out, so a build is never stopped by its tests. The stream's limits are saved as they arrive, so a headless
job never reads the status line (HQ_HEADLESS tells save-usage.mjs so); the routine holds it at the line.
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
import wall  # noqa: E402

FOLDER = hqpaths.FOLDER
# F65: HQ_JOB_RUN gives a test its own run folder (the prompt, the stream log, the activity), as tick.py does.
RUN = os.environ.get("HQ_JOB_RUN") or os.path.join(hqpaths.HQ, "scratch", "routine")
CLAUDE = hqpaths.tool("claude", "/opt/homebrew/bin/claude")
PY = sys.executable
ACTIVITY = os.environ.get("HQ_ACTIVITY") or os.path.join(RUN, "job-activity.json")
LINE_MOST = 160
# H298: what in a tool's result reads as a refusal (a refused command or push, a refused Ready mark), for the tripwires.
import re as _re
REFUSED = _re.compile(r"\b(refused|permission denied|not allowed|isn'?t ready|rejected|denied)\b", _re.I)
NOTE_MOST = 400  # tool lines kept in the box note


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


def _box_args(argv: list[str]) -> tuple[list[str], dict]:
    """H298: the box's options taken out of the chat arguments: {"minutes", "turns", "note"}."""
    box, rest, i = {"minutes": None, "turns": None, "note": None, "state": False, "round": None}, [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--box-state":
            box["state"] = True
            i += 1
            continue
        if a == "--round" and i + 1 < len(argv):  # F86: this run is a round of the loop: LABEL:fix or LABEL:mark, for what she runs
            box["round"] = argv[i + 1]
            i += 2
            continue
        if a in ("--max-minutes", "--max-turns", "--box-note") and i + 1 < len(argv):
            v = argv[i + 1]
            if a == "--box-note":
                box["note"] = v
            else:
                try:  # minutes may be a fraction (a test's short box); turns are whole
                    box["minutes" if a == "--max-minutes" else "turns"] = (max(0.05, float(v)) if a == "--max-minutes"
                                                                             else max(1, int(float(v))))
                except ValueError:
                    pass
            i += 2
            continue
        rest.append(a)
        i += 1
    return rest, box


def _write_note(path: str | None, note: dict) -> None:
    if not path:
        return
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(note, f, indent=1)
        os.replace(tmp, path)
    except OSError:
        pass


def _tell_boxed(n: int, why: str, box: dict) -> None:
    """Moneypenny's facts (H266) for a boxed job, in everyday words. Never from a test without its own line."""
    if hqpaths.under_test() and not os.environ.get("HQ_DIRECT_DIR"):
        return
    try:
        import pings
        import usagecost
        pings._spawn("paused", f"Heads up: one of the team's jobs, {usagecost.short_what(_text(n))}, ran past the time it was given "
                               f"({box['minutes']:g} minutes), so it was stopped before it burns more. It isn't finished. {wall.what_next(n)}")
    except Exception:
        pass


def _text(n: int) -> str:
    import jobs as q
    return next((j["text"] for j in q.read()[1] if j["n"] == n), "")


def _result_text(block: dict) -> str:
    c = block.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(str(x.get("text", "")) for x in c if isinstance(x, dict))
    return ""


def _keep_run(n: int, box: dict, minutes: float, turns: int, lg) -> None:
    """F103: what the runs took, into the job's history line: from the box when it keeps them, else this run's own. The job's own `jobs.py done`
    ran inside the run, before anyone knew, so this is what puts it there."""
    try:
        import estimate
        import jobs as q
        got = wall.used(n) if box["state"] else {}
        with q.locked():
            estimate.run_used(n, got.get("minutes", round(minutes, 2)), got.get("turns", turns))
    except Exception as e:
        _log(lg, f"turns and minutes not kept: {e!r}")


def main(argv: list[str]) -> int:
    if not argv or not argv[0].isdigit():
        print(__doc__)
        return 2
    n = int(argv[0])
    chat, box = _box_args(argv[1:])
    pfile = os.path.join(RUN, f"job-{n}.prompt")
    stream_log = os.path.join(RUN, f"job-{n}.stream.log")
    os.makedirs(RUN, exist_ok=True)
    cmd = [CLAUDE, "-p", "--no-chrome", "--permission-mode", "auto", "--output-format", "stream-json", "--verbose",
           *hqpaths.job_flags(), *chat]  # F99: no project settings, the never-send list; tick gives --settings in `chat`
    if box["turns"]:
        cmd += ["--max-turns", str(box["turns"])]
    env = {**os.environ, **hqpaths.JOB_ENV, "HQ_HEADLESS": "1"}  # F99: none of his folder's files at the start
    env.setdefault("HQ_JOB", str(n))
    if box["round"]:
        env["HQ_ROUND"] = box["round"]
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
        # H298: the box. A wall clock in a thread ends the run at its minutes (the stream may be quiet while
        # claude thinks); the turns are counted from the stream. Past either: boxed, and ended.
        started_at = time.time()
        boxed = {"why": None}
        turns, tools, refused, last_tool = 0, [], [], None

        def _box(why):
            if boxed["why"] is None:
                boxed["why"] = why
                _log(lg, f"job {n}: boxed ({why}: {box['minutes']} min / {box['turns']} turns); the run is ended, what it wrote stays")
                try:
                    proc.terminate()
                except OSError:
                    pass

        proof_before = wall.proof_seconds(n)

        def _own_seconds():  # F100: the job's own work, without the test run that proves it
            return time.time() - started_at - max(0.0, wall.proof_seconds(n) - proof_before)

        if box["minutes"]:
            import threading

            def _clock():
                while proc.poll() is None:
                    if _own_seconds() >= box["minutes"] * 60:
                        _box("minutes")
                        return
                    time.sleep(1)
            threading.Thread(target=_clock, daemon=True).start()
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
                try:  # F100: as they arrive, so the routine reads them every minute and no job reads the status line
                    usagelive.save(windows, f"job {n}")
                except Exception as e:
                    _log(lg, f"usage not saved: {e!r}")
            elif t == "assistant":
                turns += 1
                if box["turns"] and turns > box["turns"]:
                    _box("turns")
                for block in (d.get("message") or {}).get("content") or []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use":
                        steps += 1
                        step = _step_of(block)
                        _log(lg, step)
                        _activity(session, step)
                        last_tool = step
                        if len(tools) < NOTE_MOST:  # H298: for the tripwires (a write to a shared file, an action outside her limits)
                            tools.append(step[:LINE_MOST])
                    elif block.get("type") == "text" and block.get("text", "").strip():
                        txt = " ".join(block["text"].split())
                        _log(lg, "says: " + txt[:LINE_MOST * 2])
                        _activity(session, "writing")
            elif t == "user":
                _activity(session, "tool result")
                for block in (d.get("message") or {}).get("content") or []:  # H298: a refusal in a tool's result
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        txt = " ".join(_result_text(block).split())
                        if REFUSED.search(txt[:2000]) and len(refused) < 50:
                            refused.append({"tool": (last_tool or "")[:LINE_MOST], "said": txt[:LINE_MOST]})
            elif t == "result":
                result = d.get("result") or ""
                is_error = bool(d.get("is_error"))
                subtype = d.get("subtype")
                if subtype == "error_max_turns" and box["turns"]:  # claude's own count of the same box
                    boxed["why"] = boxed["why"] or "turns"
        code = proc.wait()
        if windows:
            try:
                usagelive.save(windows, f"job {n}")
            except Exception as e:
                _log(lg, f"usage not saved: {e!r}")
        minutes = round((time.time() - started_at) / 60, 2)
        if box["state"]:  # F100: what this run used of its box, for a resume
            try:
                wall.add_used(n, _own_seconds() / 60, turns)
            except Exception as e:
                _log(lg, f"box not kept: {e!r}")
        _keep_run(n, box, _own_seconds() / 60, turns, lg)
        _write_note(box["note"], {"n": n, "minutes": minutes, "turns": turns, "steps": steps, "boxed": boxed["why"],
                                  "box": {"minutes": box["minutes"], "turns": box["turns"]}, "exit": code,
                                  "error": bool(is_error), "subtype": subtype, "result": (result or "")[:2000],
                                  "tools": tools, "refused": refused, "session": session,
                                  "ended_by": "signal" if ended_by_signal["sig"] else ("box" if boxed["why"] else "itself")})
        sig = ended_by_signal["sig"]
        if sig:
            _log(lg, f"job {n}: ended by the routine (signal {sig}); nothing marked")
            return 0
        _log(lg, f"job {n}: claude ended (exit {code}, {steps} tool steps, {turns} turns, {minutes:g} min, result {subtype or '?'}"
                 f"{', error' if is_error else ''}{', boxed: ' + boxed['why'] if boxed['why'] else ''})")
        if result:
            _log(lg, "last words: " + " ".join(result.split())[:LINE_MOST * 3])
        state = _state(n)
        if state.startswith("running") or state.startswith("stop asked"):
            if boxed["why"] and box["state"]:  # F100: not done: parked for a call, what it wrote stays
                _log(lg, f"job {n}: boxed: ended at its box, not done; it waits for a call")
                _log(lg, _jobs("boxed", str(n), f"it ran past its box ({boxed['why']}: {box['minutes']:g} min, {box['turns']} turns); a call resumes it or drops it"))
                _tell_boxed(n, boxed["why"], box)
            elif boxed["why"]:  # H298: a boxed run is a finished run: done on the queue, boxed in her ledger
                _log(lg, f"job {n}: boxed, so the done mark is run for it (what it wrote stays)")
                _log(lg, _jobs("done", str(n)))
            elif code == 0 and not is_error:
                _log(lg, f"job {n}: still marked running on the roadmap; the done mark is run for it (headless)")
                said = _jobs("done", str(n))
                _log(lg, said)
                if said.startswith("Refused"):  # F101: a clean exit isn't done: a program runs its tests, then done again
                    _log(lg, f"job {n}: no green record yet; the program runs its tests on a copy")
                    subprocess.run([PY, os.path.join(HERE, "proof.py"), "run", str(n)], stdout=lg, stderr=subprocess.STDOUT)
                    said = _jobs("done", str(n))
                    _log(lg, said)
                    if said.startswith("Refused"):
                        _log(lg, _jobs("mark", str(n), "paused: ended, no record"))
            else:
                _log(lg, f"job {n}: ended without finishing (exit {code}{', error' if is_error else ''}); left as it is "
                         "for the routine (it notes a chat that closed without a done mark)")
        else:
            _log(lg, f"job {n}: the roadmap says '{state or 'unknown'}', nothing to mark")
        _keep_run(n, box, _own_seconds() / 60, turns, lg)  # marked done just now, with no box to read it from
        return 0 if code == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
