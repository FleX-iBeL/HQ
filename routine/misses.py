#!/usr/bin/env python3
"""F79's miss goes to Moneypenny (3 November 2026).

His words of 1 November 2026, on F79: "i dont want to hear it when it slips, moneypenny needs to know, be autonomous, make
decisions, and escalate if things repeat and she can't fix it herself". The pick he accepted in batch 5: "keep it as the aim,
widen the latest, a miss goes to Moneypenny, at most 1 miss in 20".

A miss: a finished job that ran past the latest end it was given when it started (the `latest` of its finished line, F79's
measured one; a line without F79's measured estimate, `m_est`, is from before the fix and isn't counted). It's told to her once
per job, as a note on her own line that isn't pushed to his phone (direct_line.py note estimate-miss): which job, the kind of
work, its range (likely to latest), its real time, how sure the estimate was.

A repeat goes to him through her, as a text on her line (estimate-misses), at most once a day (REPEAT_GAP), when either:
  * the bar is broken: more than MOST of the last WINDOW counted jobs ran past their latest end (2 or more in 20), or
  * the same kind of work missed twice in a row: the last two counted jobs of one kind (measured.group) both ran past it.
[Both rules are the builder's reading of "escalate if things repeat" next to "at most 1 miss in 20".]

Never from a test, unless it says so (HQ_MISSES=1) and gave its own line (HQ_DIRECT_DIR); HQ_MISSES_SYNC=1 waits for the text.

    python3 routine/misses.py            the misses so far, the last 20 counted jobs, and whether it repeats now
Standard library only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hqlock  # noqa: E402
import hqpaths  # noqa: E402
import estimate as E  # noqa: E402

WINDOW = 20  # his bar: at most 1 miss in 20
MOST = 1
REPEAT_GAP = 86400  # an escalation at most once a day; a miss after that, while it still repeats, raises it again [the builder's]
STATE = os.path.join(E.DIR, "estimate-misses.json")


def counted(h: dict) -> bool:
    """A finished job held to F79's latest end: its line carries the measured estimate it started with."""
    return isinstance(h, dict) and isinstance(h.get("m_est"), (int, float)) and isinstance(h.get("latest"), (int, float)) \
        and isinstance(h.get("actual"), (int, float))


def is_miss(h: dict) -> bool:
    return counted(h) and h["actual"] > h["latest"]


def kind_of(h: dict) -> str:
    import measured
    return measured.group(h.get("kind"), h.get("about") or "")


def key(h: dict) -> str:
    return f"{h.get('machine') or ''}|{h.get('n')}|{h.get('done')}"


def _sure(h: dict) -> str:
    s = h.get("sure") or {}
    if s.get("ok"):
        return f"from {s.get('jobs') or 'enough'} finished jobs like it"
    return "a rough estimate, too few finished jobs like it"


def facts(h: dict) -> str:
    """The note, in her words: which job, the kind, its range, its real time."""
    over = h["actual"] - h["latest"]
    own = f" It's tagged as its own mistake: {(h.get('mistake') or {}).get('what') or 'no reason written'}." if h.get("mistake") else ""
    return (f"Noted for myself: job {h.get('n')} ({kind_of(h)}) took {h['actual']} minutes. It was given about {h['m_est']}, "
            f"at the latest {h['latest']} ({_sure(h)}), so it ran {over} minute{'' if over == 1 else 's'} past its latest end.{own} "
            "Mine to look at; nothing for him unless it repeats.")


def last(hist: list[dict]) -> list[dict]:
    """The counted finished jobs, oldest first, by when they finished."""
    return sorted((h for h in hist if counted(h)), key=lambda h: h.get("done") or 0)


def repeats(hist: list[dict]) -> list[str]:
    """Which rule a repeat breaks now, in plain words; [] when it doesn't."""
    jobs = last(hist)
    out = []
    window = jobs[-WINDOW:]
    missed = [h for h in window if is_miss(h)]
    if len(missed) > MOST:
        out.append(f"{len(missed)} of the last {len(window)} finished jobs ran past their latest end, against at most {MOST} in {WINDOW}: "
                   + "; ".join(f"job {h.get('n')} ({kind_of(h)}, about {h['m_est']}, at the latest {h['latest']}, took {h['actual']})"
                               for h in missed[-5:]))
    if jobs and is_miss(jobs[-1]):
        k = kind_of(jobs[-1])
        same = [h for h in jobs if kind_of(h) == k][-2:]
        if len(same) == 2 and all(is_miss(h) for h in same):
            out.append(f"two {k} jobs in a row ran past their latest end: "
                       + " and ".join(f"job {h.get('n')} (at the latest {h['latest']}, took {h['actual']})" for h in same))
    return out


def _load() -> dict:
    try:
        d = json.load(open(STATE))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(d: dict) -> None:
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = hqlock.tmp(STATE)
    with open(tmp, "w") as f:
        json.dump(d, f)
    os.replace(tmp, STATE)


def _allowed() -> bool:
    if not hqpaths.under_test():
        return True
    return os.environ.get("HQ_MISSES") == "1" and bool(os.environ.get("HQ_DIRECT_DIR"))


def _send(args: list[str]) -> list[str] | None:
    """direct_line.py with these arguments, detached (the queue's lock is held while a job is closed), or waited for in a test."""
    py = os.path.join(ROOT, ".venv", "bin", "python")
    cmd = [py if os.path.exists(py) else sys.executable, os.path.join(ROOT, "app", "direct_line.py"), *args]
    try:
        if os.environ.get("HQ_MISSES_SYNC") == "1":
            subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
        else:
            os.makedirs(os.path.join(ROOT, "scratch"), exist_ok=True)
            log = open(os.path.join(ROOT, "scratch", "direct-line.log"), "a")
            subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"(the estimate's miss couldn't be told: {e!r})", file=sys.stderr)
        return None
    return cmd


def check(rec: dict, hist: list[dict] | None = None, now: float | None = None) -> dict | None:
    """A job just finished (estimate.on_done): a miss is told to her once, and a repeat raised with him through her, at most once a
    day. {"miss", "repeat"} of what was told, or None."""
    if not is_miss(rec) or not _allowed():
        return None
    now = time.time() if now is None else now
    with hqlock.locked(STATE):
        st = _load()
        told = list(st.get("told") or [])
        k = key(rec)
        if k in told:
            return None
        hist = E.all_history() if hist is None else hist
        if not any(key(h) == k for h in hist):
            hist = hist + [rec]
        out = {"miss": facts(rec), "repeat": None}
        _send(["note", "estimate-miss", out["miss"], "--once", "miss-" + k.replace("|", "-")])
        told.append(k)
        st["told"] = told[-500:]
        why = repeats(hist)
        if why and now - float(st.get("raised") or 0) >= REPEAT_GAP:
            out["repeat"] = " ".join(why)
            _send(["text", "estimate-misses", out["repeat"]])
            st["raised"], st["raised_why"] = now, out["repeat"]
        _save(st)
    return out


def main(argv: list[str]) -> int:
    hist = E.all_history()
    jobs = last(hist)
    window = jobs[-WINDOW:]
    miss = [h for h in jobs if is_miss(h)]
    print(f"Counted since F79: {len(jobs)} finished jobs, {len(miss)} past their latest end.")
    print(f"The last {len(window)}: {sum(is_miss(h) for h in window)} past it (the bar: at most {MOST} in {WINDOW}).")
    for h in miss[-10:]:
        print(f"- job {h.get('n')} · {kind_of(h)} · about {h['m_est']}, at the latest {h['latest']} · took {h['actual']}")
    why = repeats(hist)
    print("It repeats now: " + " ".join(why) if why else "It doesn't repeat now.")
    st = _load()
    if st.get("raised"):
        print(f"Last raised with him: {time.strftime('%Y-%m-%d %H:%M', time.localtime(st['raised']))}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
