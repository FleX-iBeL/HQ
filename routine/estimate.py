#!/usr/bin/env python3
"""H61: how long the jobs in the queue should take, learned from how long earlier jobs really took
(11 October 2026). In the user's words: "estimate time to completion (per job and total from waiting
list still waiting)" and "that it improves it at the end so we can collect real data".

How it works:
  - Every job gets a kind from the words in its text (kind_of): transcribing, a big change (the whole
    set of happy flows), a change to the call (the call line restarts at the end), a build, or other.
    A call can give the kind itself (jobs.py add --kind); that wins over the guess, is stored with the
    job's estimate, and is the kind it learns under when it finishes (H70).
  - A job's estimate is set when it's added (jobs.py add): the median of how long the last jobs of
    its kind really took, the newest counting most; with too few of its kind, the last jobs of any kind
    count too; with no history at all, 15 minutes.
  - When a job finishes (jobs.py done), its estimate and how long it really took go into the history
    file, so the next estimates learn from it. "How long it really took" is the minutes the status
    server saw it running (.status/routines-history.jsonl, not counting time held by the usage line),
    else the time since it started.
  - plan(): for the running job the time left and when it should be done; for each waiting job, in
    its place in line, how long and when it should be done; the total for the whole list. A held job
    (usage line), and everything after it, waits on the usage, so it gets no "done around" time.

Files, in HQ's .status (never in the repo): job-estimates.json (each job's estimate, set when added,
and when it started) and job-estimates-history.jsonl (one line per finished job: estimate and real).
A test's copy of the roadmap (HQ_ROADMAP) gets its own files next to it, so tests never touch the real ones.

usage:
  python3 routine/estimate.py plan      the estimates as JSON (the status server shows them)
  python3 routine/estimate.py list      the estimates in words (jobs.py list adds them too)
  python3 routine/estimate.py seed      fill the history once from the jobs history (H33) and the job prompts
  python3 routine/estimate.py kind TEXT        the kind kind_of guesses for a text
  python3 routine/estimate.py check-kinds      every finished job: the kind it learned under, next to today's guess (H70)
"""
import json, os, re, statistics, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, ".."))
_TEST = os.environ.get("HQ_ROADMAP")
if os.environ.get("HQ_ESTIMATES"):
    DIR = os.environ["HQ_ESTIMATES"]
elif _TEST:
    DIR = os.path.splitext(_TEST)[0] + "-estimates"
else:
    DIR = os.path.join(ROOT, ".status")
STATE = os.path.join(DIR, "job-estimates.json")
HISTORY = os.path.join(DIR, "job-estimates-history.jsonl")
# The minute-by-minute record of the status server (H33). A test's roadmap copy doesn't read the real one.
SAMPLES = os.environ.get("HQ_ROUTINES_HISTORY") or ("" if _TEST else os.path.join(ROOT, ".status", "routines-history.jsonl"))
BACKFILL = os.path.join(ROOT, ".status", "jobs-backfill.json")
PROMPTS = os.path.join(ROOT, "scratch", "routine")

DEFAULT = 15      # minutes, when nothing has been measured yet
GAP = 1           # minutes between two jobs: the routine looks every minute
RECENT = 8        # how many of the last jobs of a kind count
MIN_KIND = 3      # fewer than this of a kind: the last jobs of any kind count too

KINDS = {
    "transcribe": "transcribing",
    "big": "a big change (whole set of happy flows)",
    "call": "a change to the call (line restarts)",
    "build": "a build",
    "other": "other",
}


def kind_of(text):
    """The kind of job, from the words the call wrote in it (Claude's choice, H61)."""
    t = " ".join(text.lower().split())
    t = t.split("follow the hq build notes")[0].split("follow the jarvis va build notes")[0]
    t = re.sub(r"^.*?the job, as agreed on the call: ", "", t)
    if re.search(r"^transcrib|\btranscribe (the|four|all|his|\d)", t):
        return "transcribe"
    if re.search(r"(run|runs|running) the whole (happy flow )?set|whole happy flow set|all (the )?\d* ?happy flows (have )?pass", t) \
            and not re.search(r"not the whole (happy flow )?set", t):
        return "big"
    if re.search(r"restart(s)? the call line (as|at) the (very )?last step", t) and not re.search(r"don'?t restart the call line", t):
        return "call"
    # Build work by its wording anywhere (H70): "Build exactly what the H56.2 row says", "build the ...",
    # or a roadmap sub-step like "H56.1 on the HQ roadmap". A plain "H68 on the roadmap: research only"
    # stays other, as before.
    # "Don't build the backup" or "nothing built" says what not to do, so negated wording doesn't count.
    tb = re.sub(r"\b(don'?t|do not|never|not|nothing|no need to) (build|built)\b[^.;:]*", " ", t)
    if re.search(r"^build\b|\bbuild [a-z]\d|\bbuild exactly what\b|\bbuild the\b|^[a-z]\d+\.\d+ on the (hq )?roadmap", tb):
        return "build"
    return "other"


def kind_given(kind):
    """A kind set by hand (jobs.py add --kind), or None. Unknown words are refused by jobs.py."""
    k = (kind or "").strip().lower()
    return k if k in KINDS else None


# ---------- files ----------

def _load_state():
    try:
        return json.load(open(STATE))
    except Exception:
        return {}


def _save_state(d):
    os.makedirs(DIR, exist_ok=True)
    tmp = STATE + ".tmp"
    json.dump(d, open(tmp, "w"), indent=1)
    os.replace(tmp, STATE)


def history():
    out = []
    try:
        for l in open(HISTORY, encoding="utf8"):
            try:
                out.append(json.loads(l))
            except Exception:
                pass
    except FileNotFoundError:
        pass
    return out


def _append(rec):
    os.makedirs(DIR, exist_ok=True)
    with open(HISTORY, "a", encoding="utf8") as f:
        f.write(json.dumps(rec) + "\n")


def _samples():
    if not SAMPLES:
        return []
    out = []
    try:
        for l in open(SAMPLES, encoding="utf8"):
            try:
                x = json.loads(l)
            except Exception:
                continue
            if isinstance(x.get("j"), list):
                out.append(x)
    except FileNotFoundError:
        pass
    return out


def _minutes_seen(n, samples=None):
    """Minutes the status server saw job n running (not held, not the one minute of DONE)."""
    samples = _samples() if samples is None else samples
    return sum(1 for s in samples for x in s["j"] if x.get("n") == n and x.get("st") not in ("STOPPED", "DONE"))


# ---------- estimating ----------

def _weighted_median(values):
    """The newest counts most: value i (oldest first) gets weight i+1."""
    pairs = sorted((v, i + 1) for i, v in enumerate(values))
    half = sum(w for _, w in pairs) / 2
    acc = 0
    for v, w in pairs:
        acc += w
        if acc >= half:
            return v
    return pairs[-1][0]


def estimate_for(text, hist=None, kind=None):
    """(minutes, kind, how many past jobs it's based on). A kind given by hand wins over the guess (H70)."""
    hist = history() if hist is None else hist
    kind = kind_given(kind) or kind_of(text)
    real = [h for h in hist if isinstance(h.get("actual"), (int, float)) and h["actual"] > 0]
    same = [h["actual"] for h in real if h.get("kind") == kind][-RECENT:]
    if len(same) >= MIN_KIND:
        return max(1, round(_weighted_median(same))), kind, len(same)
    pool = same + [h["actual"] for h in real if h.get("kind") != kind][-RECENT:]
    if not pool:
        return DEFAULT, kind, 0
    # Few of its own kind: they count double next to the last jobs of any kind.
    return max(1, round(_weighted_median([h["actual"] for h in real][-RECENT:] + same * 2))), kind, len(pool)


# ---------- called by jobs.py (inside its lock) ----------

def on_add(n, text, kind=None):
    """kind: set by hand (jobs.py add --kind); it's stored here and goes into the history when the job
    finishes, so a hand-set kind learns in the right pile (H70)."""
    st = _load_state()
    est, kind_, based = estimate_for(text, kind=kind)
    st[str(n)] = {"est": est, "kind": kind_, "based": based, "set": int(time.time())}
    if kind_given(kind):
        st[str(n)]["by_hand"] = True
    _save_state(st)
    return st[str(n)]


def on_start(n, text=""):
    if str(n) not in _load_state():
        on_add(n, text)  # a job from before H61, or added by hand: its estimate now
    st = _load_state()
    e = st[str(n)]
    e["started"] = int(time.time())
    st[str(n)] = e
    _save_state(st)


def on_done(n, text="", started_hhmm=None):
    """Write the job's estimate next to how long it really took. Returns the record."""
    st = _load_state()
    e = st.get(str(n))
    if not e:
        est, kind, based = estimate_for(text)
        e = {"est": None, "kind": kind}
    now = time.time()
    seen = _minutes_seen(n)
    started = e.get("started") or _from_hhmm(started_hhmm, now)
    wall = round((now - started) / 60) if started else None
    actual = seen if seen else wall
    if actual is None:
        return None
    rec = {"n": n, "kind": e.get("kind") or kind_of(text), "est": e.get("est"), "actual": max(1, actual),
           "done": int(now), "how": "seen" if seen else "clock"}
    _append(rec)
    st.pop(str(n), None)
    _save_state(st)
    return rec


def _from_hhmm(hhmm, now):
    if not hhmm:
        return None
    m = re.match(r"(\d\d):(\d\d)", hhmm)
    if not m:
        return None
    t = time.localtime(now)
    s = time.mktime((t.tm_year, t.tm_mon, t.tm_mday, int(m.group(1)), int(m.group(2)), 0, 0, 0, -1))
    return s - 86400 if s > now + 60 else s


# ---------- the plan ----------

def _queue():
    import jobs as q
    _, js, on = q.read()
    return js, on


def hhmm(t):
    return time.strftime("%H:%M", time.localtime(t))


def accuracy(hist=None, last=10):
    """How close the estimates have been lately: only jobs that had an estimate when they started."""
    hist = history() if hist is None else hist
    pairs = [h for h in hist if isinstance(h.get("est"), (int, float)) and isinstance(h.get("actual"), (int, float))][-last:]
    if not pairs:
        return {"count": 0}
    off = [abs(h["actual"] - h["est"]) for h in pairs]
    within = sum(1 for h in pairs if abs(h["actual"] - h["est"]) <= max(3, 0.25 * h["est"]))
    over = sum(1 for h in pairs if h["actual"] > h["est"])
    return {"count": len(pairs), "avg_off": round(statistics.mean(off), 1), "within": within, "longer": over,
            "recent": [{"n": h["n"], "est": h["est"], "actual": h["actual"]} for h in pairs]}


def plan(now=None):
    now = time.time() if now is None else now
    js, on = _queue()
    st = _load_state()
    hist = history()
    out = {"now": int(now), "on": on, "jobs": {}, "total": None, "accuracy": accuracy(hist), "kinds": KINDS}
    for h in hist[-30:]:
        out["jobs"][str(h["n"])] = {"finished": True, "est": h.get("est"), "actual": h["actual"], "kind": h.get("kind")}
    samples = None
    cursor, left_total, waits = now, 0, not on
    running = [j for j in js if j["state"].startswith(("running", "stop asked"))]
    for j in running:
        e = st.get(str(j["n"])) or {}
        est = e.get("est") or estimate_for(j["text"], hist)[0]
        samples = _samples() if samples is None else samples
        seen = _minutes_seen(j["n"], samples)
        m = re.match(r"running since (\d\d:\d\d)", j["state"])
        started = e.get("started") or _from_hhmm(m.group(1) if m else None, now)
        done_min = seen or (round((now - started) / 60) if started else 0)
        left = max(est - done_min, 0)
        over = done_min > est
        if j["state"].startswith("stop asked"):
            left, over = 1, False
        nxt = left if left > 0 else 2  # running longer than estimated: a couple of minutes more, at least
        cursor += nxt * 60
        left_total += nxt
        out["jobs"][str(j["n"])] = {"est": est, "kind": e.get("kind") or kind_of(j["text"]), "so_far": done_min,
                                    "left": left, "over": over, "eta": None if waits else int(cursor)}
    line = [j for j in js if j["state"] == "ready" or j["state"].startswith("held")]
    for j in line:
        e = st.get(str(j["n"])) or {}
        est = e.get("est")
        kind = e.get("kind")
        if not est:
            est, kind, _ = estimate_for(j["text"], hist)
        if j["state"].startswith("held"):
            waits = True
        if running or j is not line[0] or cursor > now:
            cursor += GAP * 60
            left_total += GAP
        cursor += est * 60
        left_total += est
        out["jobs"][str(j["n"])] = {"est": est, "kind": kind, "eta": None if waits else int(cursor),
                                    "waits": "usage" if waits and on else ("off" if not on else None)}
    if running or line:
        out["total"] = {"jobs": len(running) + len(line), "minutes": round(left_total),
                        "eta": None if waits else int(cursor), "waits": ("usage" if on else "off") if waits else None}
    return out


def dur(m):
    m = int(round(m))
    if m < 60:
        return f"{m} min"
    return f"{m // 60} h {m % 60:02d}" if m % 60 else f"{m // 60} h"


def words(n, p):
    """One job's estimate in words, for jobs.py list and a call."""
    e = p["jobs"].get(str(n))
    if not e:
        return ""
    if e.get("finished"):
        return f"estimated {dur(e['est'])}, took {dur(e['actual'])}" if e.get("est") else f"took {dur(e['actual'])}"
    if "left" in e:
        if e.get("over"):
            s = f"estimated {dur(e['est'])}, running {dur(e['so_far'])}: taking longer than estimated"
        else:
            s = f"about {dur(e['left'])} left of {dur(e['est'])}"
    else:
        s = f"about {dur(e['est'])}"
    if e.get("eta"):
        s += f", done around {hhmm(e['eta'])}"
    elif e.get("waits") == "usage":
        s += ", when it's done waits on the usage"
    elif e.get("waits") == "off":
        s += ", the routine is off"
    return s + " (estimate)"


def total_words(p):
    t = p.get("total")
    if not t:
        return "Nothing waiting."
    s = f"All {t['jobs']} job{'s' if t['jobs'] != 1 else ''}: about {dur(t['minutes'])}"
    if t.get("eta"):
        s += f", all done around {hhmm(t['eta'])}"
    elif t.get("waits") == "usage":
        s += "; when it's done waits on the usage"
    elif t.get("waits") == "off":
        s += "; the routine is off"
    return s + " (estimate)."


def accuracy_words(a):
    if not a.get("count"):
        return "No estimate has been checked against a finished job yet."
    return (f"Lately (last {a['count']} job{'s' if a['count'] != 1 else ''}) the estimates were off by "
            f"{a['avg_off']:g} min on average; {a['within']} of {a['count']} close, {a['longer']} took longer.")


# ---------- seed, once ----------

def seed():
    """Fill the history from what's already known: the jobs history (H33) and its backfill, the job
    prompts for their text. No estimates existed then, so these lines have est null: they teach the
    estimates, and don't count in how close the estimates have been."""
    if history():
        print("The history already has lines; nothing seeded.")
        return
    samples = _samples()
    since = samples[0]["t"] if samples else time.time()
    act = {}
    try:
        for s in json.load(open(BACKFILL)).get("segments", []):
            if s["start"] < since and s["st"] not in ("STOPPED", "DONE"):
                act[s["n"]] = act.get(s["n"], 0) + max(0, min(s["end"], since) - s["start"]) / 60
    except Exception:
        pass
    ends = {}
    for s in samples:
        for x in s["j"]:
            ends[x["n"]] = s["t"]
            if x["st"] not in ("STOPPED", "DONE"):
                act[x["n"]] = act.get(x["n"], 0) + 1
    js, _ = _queue()
    running = {j["n"] for j in js if not re.match(r"(done|stopped|ended|cancelled)", j["state"])}
    texts = {j["n"]: j["text"] for j in js}
    n_ = 0
    for n in sorted(act):
        if n in running or act[n] < 1:
            continue
        p = os.path.join(PROMPTS, f"job-{n}.prompt")
        text = texts.get(n, "")
        if not text and os.path.exists(p):
            text = open(p, encoding="utf8").read()
            i = text.find("The job, as agreed on the call:")
            text = text[i:] if i >= 0 else text
        _append({"n": n, "kind": kind_of(text), "est": None, "actual": max(1, round(act[n])),
                 "done": int(ends.get(n, since)), "how": "seed"})
        n_ += 1
    print(f"Seeded {n_} finished jobs.")


def check_kinds():
    """H70: today's kind_of on every finished job's text next to the kind it learned under, so a change
    to the guess can be checked against the earlier jobs. Hand-set kinds say so."""
    js, _ = _queue()
    texts = {j["n"]: j["text"] for j in js}
    for h in history():
        n = h["n"]
        text = texts.get(n, "")
        p = os.path.join(PROMPTS, f"job-{n}.prompt")
        if not text and os.path.exists(p):
            text = open(p, encoding="utf8").read()
            i = text.find("The job, as agreed on the call:")
            text = text[i:] if i >= 0 else text
        if not text:
            continue
        now = kind_of(text)
        print(f"job {n}: learned {h.get('kind')}, guessed now {now}" + ("" if now == h.get("kind") else "  <- differs"))


def main(argv):
    cmd = argv[0] if argv else "--help"
    if cmd == "plan":
        print(json.dumps(plan()))
    elif cmd == "list":
        p = plan()
        js, _ = _queue()
        for j in js:
            w = words(j["n"], p)
            if w:
                print(f"Job {j['n']} · {w}")
        print(total_words(p))
        print(accuracy_words(p["accuracy"]))
    elif cmd == "seed":
        seed()
    elif cmd == "kind":
        print(kind_of(" ".join(argv[1:])))
    elif cmd == "check-kinds":
        check_kinds()
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
