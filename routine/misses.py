#!/usr/bin/env python3
"""F79's miss goes to Moneypenny (3 November 2026).

His words of 1 November 2026, on F79: "i dont want to hear it when it slips, moneypenny needs to know, be autonomous, make
decisions, and escalate if things repeat and she can't fix it herself". The pick he accepted in batch 5: "keep it as the aim,
widen the latest, a miss goes to Moneypenny, at most 1 miss in 20".

A miss: a finished job that ran past the latest end it was given when it started (the `latest` of its finished line, F79's
measured one; a line without F79's measured estimate, `m_est`, is from before the fix and isn't counted). A job is its number
on the shared queue, whichever computer closed it and however often: counted once, by its latest close (last()).

Only the main does this, every minute from the routine (tick.py, sweep()), over both computers' finished jobs, so one job is
told once and one repeat raised once, whatever closed it where:

  * a miss is told to her once per job, as a note on her own line that isn't pushed to his phone (direct_line.py note
    estimate-miss): which job, the kind of work, its range (likely to latest), its real time, how sure the estimate was; its
    row's id when it's on the record (F103). Without her line (no Moneypenny, or HQ_TEAM_LINE=0, as on a friend's HQ) no note
    is written anywhere he reads: it's kept in this file only (misses.py shows it). It counts as told only once it's written.
  * a repeat goes to him through her, as a text on her line (estimate-misses), at most once a day (REPEAT_GAP), when either:
      - the bar is broken: more than MOST of the last WINDOW counted jobs ran past their latest end (2 or more in 20), or
      - the same kind of work missed twice in a row: the last two counted jobs of one kind (measured.group) both ran past it.
    [Both rules are the builder's reading of "escalate if things repeat" next to "at most 1 miss in 20".]
    It's sent by a run of its own (her words go through Claude), and counts as raised only once the text stands in her thread;
    until then it waits as pending and is tried again every RETRY_S, at most TRIES times. The text's line id is the day's, so
    even two computers on one line give one text.

Never from a test, unless it says so (HQ_MISSES=1) and gave its own line (HQ_DIRECT_DIR); HQ_MISSES_SYNC=1 waits for the text.

    python3 routine/misses.py            the misses so far, the last 20 counted jobs, whether it repeats now, what's kept
    python3 routine/misses.py raise      send the pending repeat (the routine starts it; it marks it raised once it went)
Standard library only.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
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
REPEAT_GAP = 86400  # a repeat raised at most once a day; a miss after that, while it still repeats, raises it again [the builder's]
RETRY_S = int(os.environ.get("HQ_MISSES_RETRY") or 600)  # a repeat that didn't go is tried again after this
TRIES = 6
KEPT_MOST = 50
STATE = os.path.join(E.DIR, "estimate-misses.json")


def counted(h: dict) -> bool:
    """A finished job held to F79's latest end: its line carries the measured estimate it started with."""
    return isinstance(h, dict) and isinstance(h.get("m_est"), (int, float)) and isinstance(h.get("latest"), (int, float)) \
        and isinstance(h.get("actual"), (int, float)) and h["actual"] > 0 and h.get("n") is not None


def is_miss(h: dict) -> bool:
    return counted(h) and h["actual"] > h["latest"]


def kind_of(h: dict) -> str:
    import measured
    return measured.group(h.get("kind"), h.get("about") or "")


def job_key(h: dict) -> str:
    """The job itself: its number on the shared queue, the same on both computers and on a second close."""
    return f"job {h.get('n')}"


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
    """The counted finished jobs, each once (its latest close, whichever computer), oldest first by when they finished."""
    by: dict = {}
    for h in hist:
        if counted(h):
            k = job_key(h)
            if k not in by or (h.get("done") or 0) >= (by[k].get("done") or 0):
                by[k] = h
    return sorted(by.values(), key=lambda h: h.get("done") or 0)


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


def _main() -> bool:
    """Only the main tells and raises: one place decides, whichever computer closed the job."""
    try:
        import role
        return role.acting() == "main"
    except Exception:
        return True


def _dl():
    sys.path.insert(0, os.path.join(ROOT, "app"))
    import direct_line
    return direct_line


def _item_of(h: dict) -> str:
    """The id of the row a job was for, when the row is on the record already (never a new id made here)."""
    m = re.match(r"\s*(?:qa of\s+)?([fh]\d+)\b", (h.get("about") or "").lower())
    if not m:
        return ""
    try:
        import trail
        return trail.of(m.group(1).upper()) or ""
    except Exception:
        return ""


def raise_id(now: float) -> str:
    return "misses-" + time.strftime("%Y-%m-%d", time.localtime(now))


def _start_raise() -> None:
    py = os.path.join(ROOT, ".venv", "bin", "python")
    cmd = [py if os.path.exists(py) else sys.executable, os.path.abspath(__file__), "raise"]
    try:
        if os.environ.get("HQ_MISSES_SYNC") == "1":
            subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180)
        else:
            os.makedirs(os.path.join(ROOT, "scratch"), exist_ok=True)
            log = open(os.path.join(ROOT, "scratch", "direct-line.log"), "a")
            subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"(the repeat couldn't be started: {e!r})", file=sys.stderr)


def sweep(hist: list[dict] | None = None, now: float | None = None) -> dict:
    """The routine's minute on the main: every counted miss not told yet gets its note; a repeat waits as pending until its
    text went. {"told": [job keys], "kept": [...], "pending": ..., "started": bool}."""
    out = {"told": [], "kept": [], "pending": None, "started": False}
    if not _allowed() or not _main():
        return out
    now = time.time() if now is None else now
    hist = E.all_history() if hist is None else hist
    jobs = last(hist)
    with hqlock.locked(STATE):
        st = _load()
        if not st:  # the first look here (a new main, a takeover): what's already past counts as told, nothing old is sent
            st = {"told": [job_key(h) for h in jobs if is_miss(h)], "since": now}
            _save(st)
            return out
        told = list(st.get("told") or [])
        new = [h for h in jobs if is_miss(h) and job_key(h) not in told]
        dl = _dl() if new else None
        for h in new:
            words = facts(h)
            if dl.line_for("estimate-miss") != "team":  # no line of hers: nowhere he reads, only here
                st.setdefault("kept", []).append({"at": round(now), "job": job_key(h), "facts": words})
                st["kept"] = st["kept"][-KEPT_MOST:]
                out["kept"].append(job_key(h))
            else:
                try:
                    m = dl.note("estimate-miss", words, _item_of(h), "miss-" + str(h.get("n")))
                except Exception as e:
                    print(f"(the note on job {h.get('n')} couldn't be written: {e!r})", file=sys.stderr)
                    continue  # not told: tried again the next minute
                if not m.get("id"):
                    continue
                out["told"].append(job_key(h))
            told.append(job_key(h))
        st["told"] = told[-500:]
        why = repeats(hist) if new else []
        if why and now - float(st.get("raised") or 0) >= REPEAT_GAP:
            p = st.get("pending") or {}
            st["pending"] = {"why": " ".join(why), "id": raise_id(now), "tries": int(p.get("tries") or 0), "last": float(p.get("last") or 0)}
        p = st.get("pending")
        if p and now - float(st.get("raised") or 0) < REPEAT_GAP:
            st["pending"] = p = None  # it went meanwhile
        start = bool(p) and now - float(p.get("last") or 0) >= RETRY_S and int(p.get("tries") or 0) < TRIES
        if start:
            p["tries"], p["last"] = int(p.get("tries") or 0) + 1, now
        out["pending"] = p
        _save(st)
    if start:
        _start_raise()
        out["started"] = True
    return out


def raise_pending() -> str:
    """The run of its own: the pending repeat as her text on her line; raised only when it stands there."""
    lock = open(STATE + ".raise", "a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return "another run is sending it"
    try:
        with hqlock.locked(STATE):
            p = (_load().get("pending") or {})
        if not p.get("why"):
            return "nothing pending"
        m = _dl().text("estimate-misses", p["why"], "", p.get("id") or "")
        if not (m.get("id") or m.get("held")):
            return f"it didn't go: {m}"
        with hqlock.locked(STATE):
            st = _load()
            st["raised"], st["raised_why"], st["pending"] = time.time(), p["why"], None
            _save(st)
        return "raised"
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def main(argv: list[str]) -> int:
    if argv[:1] == ["raise"]:
        print(raise_pending())
        return 0
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
    if st.get("pending"):
        print(f"Waiting to go to him (tried {st['pending'].get('tries')} times): {st['pending'].get('why')}")
    for k in (st.get("kept") or [])[-10:]:
        print(f"Kept here, with no line of hers: {k['facts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
