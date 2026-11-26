#!/usr/bin/env python3
"""F106: a helper beside a call. His words: "and that whole part where on the call she can say let me figure that out (or something
like that) and then run a job on the background and either let me know on the call or if i hung up it gets texted".

On a call, for anything bigger than a quick look, the agent says she'll take it away and starts a helper: a headless Claude that
only reads, boxed in minutes and turns, writing only its own record here. The call goes on. The answer comes back into the same
call (app/call.py watches for it and she says it at the next quiet moment), or as a text on her line if he hung up. It's not the
team: nothing is built, nothing is queued, and it runs on the live slice: the order is him live first, so the team's stop lines
don't hold it, only a used-up limit does.

    python3 routine/helper.py start "THE QUESTION"       from a call: who's asking comes from the call that's on
    python3 routine/helper.py list                       the helpers that run now, in a line each
    python3 routine/helper.py run ID                     the run itself, in the background

A record is `.status/helpers/ID.json`: {"id", "question", "agent", "call", "state" (running, done, boxed, stopped, failed), "started", "ended",
"minutes", "turns", "box", "answer", "told" (call or text)}. HQ_HELPERS a test's own folder, HQ_HELPER_CLAUDE a stand-in for the model
(same arguments, same stream). Standard library only.

Whatever way a run fails, she said she'd come back, so it ends as `failed` and is told as a finished one is: a run that can't start or falls over
says so itself, and one that died without a word is found by the call's watcher and the routine's minute (`minute`, on both computers), which also
texts an answer whose call is gone. A run that hit its turns gives what it had.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import signal
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqlock  # noqa: E402
import hqpaths  # noqa: E402

MINUTES = 5       # F106: a helper's box in minutes: long enough for a long read, short enough to land while he's still on the call
TURNS = 40        # F106: its box in turns, about TURNS_A_MINUTE (wall.py) times the minutes, a little under
AT_ONCE = 2       # F106: how many run beside calls at once; a third is told to wait
LIMIT_FULL = 98   # F106: at this percent of the 5-hour or the weekly limit no helper starts: the live slice ends where the limit does
LIVE_S = 15       # F106: a call that hasn't said it's on for this long counts as hung up
WATCH_S = 3       # F106: how often a call looks for an answer
GRACE_S = 5       # F106: how long a helper past its box gets to end by itself before it's killed (then it's "stopped")
PIPE_S = 1        # F106: how long the model's stdout gets once the model itself is gone; a child in a session of its own can hold it open for good
LATE_S = 120      # F106: a run this far past its box isn't running, whatever its pid says (a pid can be taken by something else)
TEXT_TRIES = 10   # F106: how many minutes the routine tries a text that wouldn't go; past that the line on the status page is what's left
MODEL = "sonnet"  # F106: reading and finding, the reviewer's model
ANSWER_MOST = 2000  # F106: the characters of an answer that go into a call or a text; the record keeps it whole
TOOLS = "Read,Glob,Grep,WebSearch"


def folder() -> str:
    return os.environ.get("HQ_HELPERS") or os.path.join(hqpaths.HQ, ".status", "helpers")


def path(hid: str) -> str:
    return os.path.join(folder(), f"{hid}.json")


def load(hid: str) -> dict:
    try:
        return json.load(open(path(hid)))
    except (OSError, ValueError):
        return {}


def save(rec: dict) -> None:
    os.makedirs(folder(), exist_ok=True)
    p = path(rec["id"])
    tmp = hqlock.tmp(p)
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def everyone() -> list[dict]:
    out = []
    try:
        names = os.listdir(folder())
    except OSError:
        return out
    for n in names:
        if n.endswith(".json") and not n.startswith("live-"):
            d = load(n[:-5])
            if d.get("id"):
                out.append(d)
    return sorted(out, key=lambda d: d.get("started") or 0)


def alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def running() -> list[dict]:
    return [d for d in everyone() if d.get("state") == "running" and (alive(d.get("pid")) or time.time() - (d.get("started") or 0) < 5)]


def _finish(hid: str, **fields) -> dict | None:
    """A run's end on its record, once, and a text when nobody's on its call. None when it had ended already."""
    with hqlock.locked(path(hid)):
        rec = load(hid)
        if rec.get("state") != "running":
            return None
        rec.update({"ended": time.time(), **fields})
        save(rec)
    if not call_on(rec.get("call") or ""):
        by_text(hid)
    return rec


def _gone(d: dict) -> bool:
    """A record that says running with nothing running: its run died without a word."""
    if d.get("state") != "running":
        return False
    age = time.time() - (d.get("started") or 0)
    return age > (d.get("box") or {}).get("minutes", MINUTES) * 60 + LATE_S or (age >= 5 and not alive(d.get("pid")))


def reap() -> list[str]:
    """What died without a word ends as failed, here, as a run that fell over ends itself."""
    done = []
    for d in everyone():
        if _gone(d) and _finish(d["id"], state="failed", answer=d.get("answer") or "", why="the run died"):
            done.append(d["id"])
    return done


def minute() -> list[str]:
    """F106: the routine's minute, on both computers: what died goes as failed, and an answer whose call is gone and that was never told goes
    as a text (a call line that fell over never says it's over). What it sent."""
    reap()
    return [d["id"] for d in everyone() if d.get("state") != "running" and not d.get("told") and not call_on(d.get("call") or "")
            and (d.get("tries") or 0) < TEXT_TRIES and by_text(d["id"])]


# -- which call ----------------------------------------------------------------------------------------------------------

def _live_path(call: str) -> str:
    return os.path.join(folder(), f"live-{call}.json")


def live(call: str, agent: str) -> None:
    """A call says it's on, every WATCH_S."""
    os.makedirs(folder(), exist_ok=True)
    p = _live_path(call)
    tmp = hqlock.tmp(p)
    with open(tmp, "w") as f:
        json.dump({"call": call, "agent": agent, "at": time.time()}, f)
    os.replace(tmp, p)


def call_on(call: str) -> bool:
    try:
        return time.time() - json.load(open(_live_path(call))).get("at", 0) < LIVE_S
    except (OSError, ValueError):
        return False


def current() -> dict:
    """The call that's on now, the newest: {"call", "agent"}, or {}."""
    best: dict = {}
    try:
        for n in os.listdir(folder()):
            if n.startswith("live-") and n.endswith(".json"):
                try:
                    d = json.load(open(os.path.join(folder(), n)))
                except (OSError, ValueError):
                    continue
                if time.time() - d.get("at", 0) < LIVE_S and d.get("at", 0) > best.get("at", 0):
                    best = d
    except OSError:
        pass
    return best


# -- starting --------------------------------------------------------------------------------------------------------

def why_not() -> str | None:
    """Why a helper can't start now, in plain words, or None."""
    if len(running()) >= AT_ONCE:
        return f"{AT_ONCE} are already running; say you'll look at it when one is back."
    try:
        d = json.load(open(os.environ.get("HQ_USAGE") or os.path.join(hqpaths.HQ, ".status", "usage.json")))
        for lim in d.get("limits") or []:
            over = isinstance(lim.get("percent"), (int, float)) and lim["percent"] >= LIMIT_FULL
            if over and str(lim.get("resetsAt") or "9") > time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()):
                return "the usage limit is used up; it can't run now."
    except (OSError, ValueError, AttributeError):
        pass
    return None


def start(question: str, agent: str = "", call: str = "") -> dict:
    question = " ".join(str(question).split())
    if len(question) < 8:
        return {"ok": False, "said": "What should it find out? Say it in a line."}
    os.makedirs(folder(), exist_ok=True)
    with hqlock.locked(os.path.join(folder(), "start")):  # the limit holds: the record is there before the next one counts
        no = why_not()
        if no:
            return {"ok": False, "said": f"No helper now: {no}"}
        on = current()
        rec = {"id": secrets.token_hex(4), "question": question[:600], "agent": agent or on.get("agent") or "donna", "call": call or on.get("call") or "",
               "state": "running", "started": time.time(), "box": {"minutes": MINUTES, "turns": int(os.environ.get("HQ_HELPER_TURNS") or TURNS)}}
        save(rec)
    log = os.path.join(hqpaths.HQ, "scratch", "helper.log")
    try:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "run", rec["id"]], cwd=hqpaths.HQ, stdin=subprocess.DEVNULL,
                             stdout=open(log, "a"), stderr=subprocess.STDOUT, start_new_session=True)
    except OSError as e:  # she hears it here, so nothing else tells it
        with hqlock.locked(path(rec["id"])):
            save({**load(rec["id"]), "state": "failed", "ended": time.time(), "answer": "", "why": repr(e)[:200], "told": "start"})
        return {"ok": False, "said": "No helper now: it couldn't start. Say so, and look at it yourself if it's a quick one."}
    with hqlock.locked(path(rec["id"])):  # a run that's over already keeps its end
        save({**load(rec["id"]), "pid": p.pid})
    return {"ok": True, "id": rec["id"], "said": f"A helper is on it, boxed at {MINUTES} minutes. Say you'll come back with it, and go on with him."}


# -- the run ---------------------------------------------------------------------------------------------------------

PROMPT = ("You're a helper beside a live call at HQ. The agent on the call asked you one question. Look it up in this folder and in HQ's "
          "own files, read as much as it takes, and change nothing: you can only read. Answer in a few plain sentences, with what you "
          "found, where it stands and what you couldn't check. No headings, no lists, no file names unless the question asks for one. "
          "The question: ")


def _command(question: str) -> list[str]:
    claude = os.environ.get("HQ_HELPER_CLAUDE") or hqpaths.tool("claude", "/opt/homebrew/bin/claude")
    return [claude, "-p", PROMPT + question, "--model", MODEL, "--output-format", "stream-json", "--verbose",
            "--tools", TOOLS, "--allowedTools", TOOLS, "--strict-mcp-config", "--add-dir", hqpaths.HQ,
            "--no-session-persistence", "--max-turns", str(TURNS), *hqpaths.job_flags()]


def run(hid: str) -> int:
    """The run, and whatever way it falls over: the model that won't start, this process told to stop, anything else. It ends as failed, with
    what it had."""
    rec = load(hid)
    if not rec:
        return 2
    got = {"proc": None, "said": [], "turns": 0}

    def stop(*_a) -> None:
        raise SystemExit(1)

    signal.signal(signal.SIGTERM, stop)
    try:
        return _run(hid, rec, got)
    except BaseException as e:
        if got["proc"]:
            try:
                os.killpg(got["proc"].pid, signal.SIGKILL)
            except OSError:
                pass
        print(f"helper {hid}: the run fell over: {e!r}", flush=True)
        _finish(hid, state="failed", answer=got["said"][-1] if got["said"] else "", turns=got["turns"], why=repr(e)[:200],
                minutes=round((time.time() - rec.get("started", time.time())) / 60, 2))
        if got["proc"]:  # the reader may sit in a read that never ends: nothing here waits for it, not even the way out
            sys.stdout.flush()
            os._exit(1)
        return 1


def _run(hid: str, rec: dict, got: dict) -> int:
    box_s = float(os.environ.get("HQ_HELPER_BOX_S") or rec["box"]["minutes"] * 60)
    p = got["proc"] = subprocess.Popen(_command(rec["question"]), cwd=hqpaths.FOLDER, env={**os.environ, **hqpaths.JOB_ENV}, stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, start_new_session=True)
    t0 = time.time()
    boxed = {"why": None, "killed": False}

    def kill() -> None:
        boxed["killed"] = True
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            pass

    grace = threading.Timer(GRACE_S, kill)
    grace.daemon = True

    def end(why: str) -> None:
        try:
            grace.start()
        except RuntimeError:  # a second reason to end: the first one's grace is running
            pass
        boxed["why"] = boxed["why"] or why
        try:
            os.killpg(p.pid, signal.SIGTERM)
        except OSError:
            pass

    timer = threading.Timer(box_s, end, args=("minutes",))
    timer.daemon = True
    timer.start()
    turns, said, result, broke = 0, got["said"], "", ""

    def read() -> None:
        nonlocal turns, result, broke
        for line in p.stdout:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            if d.get("type") == "assistant":
                turns = got["turns"] = turns + 1
                for b in (d.get("message") or {}).get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip():
                        said.append(b["text"].strip())
                if turns > rec["box"]["turns"]:
                    end("turns")
            elif d.get("type") == "result":
                if d.get("subtype") == "error_max_turns":  # claude's own count of the box: what it had still counts
                    boxed["why"] = boxed["why"] or "turns"
                elif d.get("is_error"):
                    broke = str(d.get("result") or d.get("subtype") or "an error")[:200]
                else:
                    result = (d.get("result") or "").strip()

    # The pipe is read beside this: once the model is gone, what's left on the pipe gets PIPE_S and no more. A grandchild in its own
    # session outlives the kill and keeps the pipe open, and a run waiting on that would hold its record "running", and its slot, for good.
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    gone_at = None
    while reader.is_alive():
        reader.join(0.2)
        if p.poll() is not None:
            gone_at = gone_at or time.time()
            if time.time() - gone_at > PIPE_S:
                break
    timer.cancel()
    grace.cancel()
    try:
        code = p.wait(timeout=10)
    except subprocess.TimeoutExpired:
        p.kill()
        code = -1
    held = reader.is_alive()
    answer = result or (said[-1] if said else "")
    state = "stopped" if boxed["killed"] or (held and boxed["why"]) else "boxed" if boxed["why"] else ("done" if code == 0 and answer and not broke else "failed")
    _finish(hid, state=state, minutes=round((time.time() - t0) / 60, 2), turns=turns, answer=answer, why=boxed["why"] or broke)
    if held:  # the reader sits in a read that never ends: nothing here waits for it, not even the way out
        sys.stdout.flush()
        os._exit(0)
    return 0


def words(rec: dict) -> str:
    """What comes back: the answer, or what's known when it didn't finish."""
    a = (rec.get("answer") or "").strip()[:ANSWER_MOST]
    if rec.get("state") in ("boxed", "stopped"):
        return (f"It ran out of its time before it finished. What it had: {a}" if a else "It ran out of its time before it found anything.")
    if rec.get("state") == "failed" and a:
        return f"The run fell over before it finished. What it had: {a}"
    if rec.get("state") == "failed" or not a:
        return "It didn't get an answer: the run failed."
    return a


def _claim(hid: str, how: str) -> dict | None:
    """One way out for each answer: the call or the text, never both."""
    p = path(hid)
    with hqlock.locked(p):
        rec = load(hid)
        if not rec or rec.get("told") or rec.get("state") == "running":
            return None
        rec["told"] = how
        rec["told_at"] = time.time()
        save(rec)
    return rec


def take(call: str) -> list[dict]:
    """The finished answers for a call that's on; each comes out once. A run that died comes out as a failed one."""
    reap()
    out = []
    for d in everyone():
        if d.get("call") == call and d.get("state") != "running" and not d.get("told"):
            got = _claim(d["id"], "call")
            if got:
                out.append(got)
    return out


def by_text(hid: str) -> bool:
    rec = _claim(hid, "text")
    if not rec:
        return False
    py = os.path.join(hqpaths.HQ, ".venv", "bin", "python")
    env = {**os.environ}
    who = rec.get("agent") or ""
    if who == "pepper":  # her line is the coaching line, as app/coaching.py sets it
        env.update({"HQ_DIRECT_DIR": os.environ.get("HQ_COACHING_LINE") or os.path.join(hqpaths.FOLDER, "HQ", "coaching-line"),
                    "HQ_DIRECT_AGENT": "pepper", "HQ_DIRECT_COACHING": "1"})
    cmd = [py if os.path.exists(py) else sys.executable, os.path.join(hqpaths.HQ, "app", "direct_line.py"), *(["--team"] if who == "moneypenny" else []),
           "text", "helper", f"He asked on the call: {rec['question'][:200]}\nWhat came back: {words(rec)}", "--once", f"helper-{hid}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=hqpaths.HQ, timeout=120)
        code, err = r.returncode, r.stderr
    except (OSError, subprocess.SubprocessError) as e:
        code, err = 1, repr(e)
    if code:
        print(f"the helper's text: {err[-300:]}", file=sys.stderr)
        with hqlock.locked(path(hid)):  # not told after all: the routine's minute tries again
            save({**load(hid), "told": None, "tries": (rec.get("tries") or 0) + 1})
        import routines
        routines.bad("helper", f"A helper's answer couldn't be texted: {err[-160:]}", every=3600)
        return False
    return True


def call_over(call: str) -> list[str]:
    """The call hung up: what's finished and not said goes by text; a helper still running texts by itself when it ends."""
    try:
        os.remove(_live_path(call))
    except OSError:
        pass
    reap()
    done = []
    for d in everyone():
        if d.get("call") == call and d.get("state") != "running" and not d.get("told") and by_text(d["id"]):
            done.append(d["id"])
    return done


def line_words(rec: dict, now: float | None = None) -> str:
    """The status page's line."""
    mins = int(((now or time.time()) - rec.get("started", 0)) / 60)
    return f"{(rec.get('agent') or 'an agent').capitalize()}'s helper: {rec['question'][:120]} ({mins} of {rec['box']['minutes']} minutes)"


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "start" and len(argv) > 1:
        r = start(" ".join(argv[1:]))
        print(r["said"])
        return 0 if r["ok"] else 2
    if cmd == "run" and len(argv) > 1:
        return run(argv[1])
    if cmd == "list":
        print("\n".join(line_words(d) for d in running()) or "No helper is running.")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
