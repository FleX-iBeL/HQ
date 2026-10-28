#!/usr/bin/env python3
"""H172: usage that keeps itself in check (16 October 2026, call at 11:56, Pepper). In the user's words: "I don't have
to worry about how much usage we're running. I want it to be dynamically spread out evenly. I want that when a job
wants to run, it knows (at least as a best effort) how much usage it thinks it's going to cost and how much time it
thinks it's going to cost. Then we look at what we have ... if it has to wait, it will wait. Then we need to understand
how long it should wait." and "it just looks at the numbers, does the calculation, and takes the risk of running it.
Even if it passes a couple percentage points over, we course-correct for the future and the next one will
automatically have to wait a little longer". Replaces H159 (estimated usage per job) and H141's fixed rates.

What it does:
  - The real cost of every job: the saved usage (.status/usage.json: the 5-hour and the weekly all-models percent,
    with their reset times) when it starts, every minute while it runs (tick.py), and when it's done. A reset in
    between is counted (what was used before it, plus what came after). Time held by the usage line doesn't count:
    the count stops at the hold and starts again from the reading when it carries on. Kept per running job in
    job-usage.json; at done the cost goes into the job's line in the estimates history ("cost": {"five", "weekly"},
    next to "actual"), with the estimate it started with ("est_cost"). Whatever else used the plan at the same time
    (a call, the mail check) counts with it: that's the usage the work really had room for.
  - Past jobs (backfill): their cost from the saved readings in scratch/routine/usage.log (every minute a new reading
    came in), from shortly before they started to shortly after they were done; where no reading is close enough to
    either end, the cost stays empty ("cost_how": "log").
  - The estimate (cost_for): how much usage a job or planned item takes per minute, from the finished jobs most like
    it (H166's similar jobs, by how alike), else the last jobs of its kind, else the last jobs of any kind, each only
    with COST_MIN or more jobs that have a cost; times its estimated minutes. With too little history: START_ROOM's
    rates (1% per 2 minutes on the 5-hour line, 0.2% per 2 minutes on the weekly ones), the fallback only.
  - The gate (tick.py, save-usage.mjs --gate --need): a job starts when its estimated cost fits under each stop line
    (the 5-hour line skipped only for a job let past it; the weekly lines always count, F13), else it waits.
  - When it will fit (Projection.fits_at): from the reading now, how the moving lines rise every minute, the resets
    (after one, the use is 0 and the line starts at its floor again), and the cost of the work before it in line.
    estimate.plan() gives each waiting job and planned item that start ("starts around" on the status page, in
    jobs.py list and schedule.py list).
  - The stop at the line for a running job stays as it is (H113). New: a job whose real cost reaches about four times
    the top of its estimate (OVER times; twice the estimate itself until H221, four times until H220; and at least
    OVER_MIN points more than the estimate, so a rounding of the readings doesn't do it) is paused for good: its chat
    ends, it isn't started again by itself, and Donna texts him in plain words. A call lets it carry on (jobs.py resume
    N, in its own chat, H113) or cancels it (jobs.py stop N).
  - H220 (21 October 2026): how sure the estimate is counts. Every pause so far (jobs 211, 248, 266, 281, 292) was a
    job whose usage was estimated from its computed minutes alone, while the first look, the call and the team itself
    had guessed it two to ten times longer, and they were right. The top of an estimate (top_factor) is the estimate
    times how unsure it is: the high end of the jobs like it (the middle half's top), and the longest guess (the look's,
    the call's, the team's) over the computed minutes, at most TOP_MAX times. A sure job is paused at four times its
    estimate, as H221 said; an unsure one at most at eight. Backtest: pause_backtest.

[The numbers are Claude's choice: COST_MIN 3 jobs, OVER 4 (2 until H221) with OVER_MIN 3 points on the 5-hour line and 1 on the
weekly, TOP_MAX 2 (H220); the readings are whole percents, so a short job's cost is rough, and it evens out over many jobs.]

Files, in HQ's .status (never in the repo), next to the estimates: job-usage.json (the running and held jobs' count).
A test's copy of the roadmap (HQ_ROADMAP) gets its own files next to it and reads no real usage unless HQ_USAGE names
a reading (and HQ_USAGE_LOG a log), so tests never touch or depend on the real ones.

usage:
  python3 routine/usagecost.py now                 the reading the gate uses, each line's stop line and room
  python3 routine/usagecost.py cost "TEXT" [MIN]   a job's estimated usage, and what it's based on
  python3 routine/usagecost.py when "TEXT" [MIN]   when a job like that would fit, with nothing else running
  python3 routine/usagecost.py backfill            fill the finished jobs' cost from the saved readings (once is enough)
  python3 routine/usagecost.py costs [N]           the last N finished jobs with their time and cost
  python3 routine/usagecost.py rate                H173: learn the rate (weighted tokens a point) and show it
  python3 routine/usagecost.py tokens N            H173: job N's own tokens and cost, from its own chats
  python3 routine/usagecost.py calls [N]           H173: what the last N calls cost on their own
  python3 routine/usagecost.py fill                H173: the finished jobs' own tokens from their chats (by itself once)
  python3 routine/usagecost.py pauses              H220: every finished job against the pause: twice, four times, and
                                                   four times the top of its estimate (which ones would have paused)
"""
import json, math, os, re, sys, time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.normpath(os.path.join(HERE, ".."))
_TEST = os.environ.get("HQ_ROADMAP")
if os.environ.get("HQ_ESTIMATES"):
    DIR = os.environ["HQ_ESTIMATES"]
elif _TEST:
    DIR = os.path.splitext(_TEST)[0] + "-estimates"
else:
    DIR = os.path.join(ROOT, ".status")
TRACK = os.path.join(DIR, "job-usage.json")
USAGE = os.environ.get("HQ_USAGE") or ("" if _TEST else os.path.join(ROOT, ".status", "usage.json"))
USAGE_LOG = os.environ.get("HQ_USAGE_LOG") or ("" if _TEST else os.path.join(ROOT, "scratch", "routine", "usage.log"))

KEYS = ("five", "weekly")  # the lines a job's cost is counted on (Weekly Fable takes the weekly cost)
# H141's rates, only the fallback now: percent per minute (START_ROOM in status/usage.mjs: 1 and 0.2 per 2 minutes).
FALLBACK = {"five": 0.5, "weekly": 0.1}
COST_MIN = 3        # finished jobs with a cost before they decide the rate
RECENT = 12         # the last jobs of a kind (or of any kind) that count
OVER = 4            # a running job at this many times the top of its estimated cost pauses for good (H221: was 2)
TOP_MAX = 2         # H220: the top of an estimate is at most this many times the estimate (how unsure it can count)
GUESS_KEYS = ("guess", "guess_call", "guess_look")  # H220: the guesses that say an estimate may be short
OVER_MIN = {"five": 3, "weekly": 1}  # ... and at least this many points over it (the readings are whole percents)
SAME_RESET = 5 * 60  # two reset times this close are the same window
NEAR = {"before": 15 * 60, "after": 10 * 60}  # backfill: a reading this close to a job's start or end counts
HORIZON = 15 * 86400  # when_fits looks this far ahead at most
LINES = {"five": {"window": 5 * 3600, "floor": 10}, "weekly": {"window": 7 * 86400, "floor": 20},
         "fable": {"window": 7 * 86400, "floor": 20}}
WEEKLY_FIXED = 90


def _now():
    return time.time()


def _iso(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def line_key(label):
    """Which of the three lines a plan limit's label belongs to (lineKey in usage.mjs)."""
    label = label or ""
    if re.search(r"5-hour", label, re.I):
        return "five"
    if re.match(r"weekly", label, re.I):
        return "fable" if re.search(r"fable", label, re.I) else "weekly"
    return None


# ---------- the stop lines, as status/usage.mjs has them (lineSettings, movingLine, stopLine) ----------

def line_settings(markdown):
    """The three lines' settings from the roadmap, or None when it names no usage limit (lineSettings in usage.mjs)."""
    limit = re.search(r"\*\*Usage limit:\s*(\d{1,3})\s*%", markdown or "")
    if not limit:
        return None
    flat = re.search(r"\*\*Weekly limit:\s*(\d{1,3})\s*%", markdown)

    def read(name):
        m = re.search(r"\*\*" + re.escape(name) + r" line:\s*(moving|fixed)\b([^*]*)\*\*", markdown, re.I)
        if not m:
            return None
        n = re.search(r"(\d{1,3})\s*%", m.group(2))
        return {"moving": m.group(1).lower() == "moving", "fixed": int(n.group(1)) if n else None}

    five, week, fable = read("5-hour"), read("Weekly"), read("Fable")
    old = {"moving": not flat, "fixed": int(flat.group(1)) if flat else WEEKLY_FIXED}
    pick = lambda r: {"moving": r["moving"], "fixed": r["fixed"] if r["fixed"] is not None else old["fixed"]} if r else dict(old)  # noqa: E731
    return {"five": {"moving": five["moving"] if five else True, "fixed": int(limit.group(1))},
            "weekly": pick(week), "fable": pick(fable)}


def roadmap_lines():
    try:
        import hqpaths
        return line_settings(open(hqpaths.ROADMAP, encoding="utf8").read())
    except Exception:
        return None


def moving_line(key, reset, t):
    """The moving line at time t from its window's reset time (movingLine in usage.mjs), or None without a reset."""
    if reset is None or key not in LINES:
        return None
    w, floor = LINES[key]["window"], LINES[key]["floor"]
    minutes = w // 60
    start = round(reset / 60) * 60 - w
    begun = min(minutes, max(1, math.floor((t - start) / 60) + 1))
    # Math.round in JS rounds .5 up; Python's round() would round it to even.
    return max(floor, math.floor(1000 * begun / minutes + 0.5) / 10)


def stop_line(key, reset, lines, t):
    s = lines.get(key) if lines and key else None
    if not s:
        return lines["five"]["fixed"] if lines else None
    if s["moving"]:
        m = moving_line(key, reset, t)
        if m is not None:
            return m
    return s["fixed"]


# ---------- the reading ----------

def reading(path=None, now=None):
    """The saved usage the gate uses: {key: {"pct", "reset"}} for the lines read in this reading (not the kept ones),
    with a window whose reset has passed counted as empty (and its next reset one window on); {} when there's none."""
    path = USAGE if path is None else path
    now = _now() if now is None else now
    try:
        r = json.load(open(path))
    except (OSError, ValueError, TypeError):
        return {}
    if not r.get("readable"):
        return {}
    out = {}
    for l in r.get("limits") or []:
        k = line_key(l.get("label"))
        if not k or l.get("kept") or not isinstance(l.get("percent"), (int, float)):
            continue
        pct, reset = float(l["percent"]), _iso(l.get("resetsAt"))
        if reset is not None and reset <= now:
            w = LINES[k]["window"]
            while reset <= now:
                reset += w
            pct = 0.0
        out[k] = {"pct": pct, "reset": reset}
    return out


# ---------- when a job fits ----------

class Projection:
    """The use on each line from now on: the reading now, plus the cost of the work planned before (added at its
    start), with each reset bringing the use back to 0 and the moving line back to its floor."""

    def __init__(self, read, lines, now=None):
        self.read, self.lines, self.now = read, lines, (_now() if now is None else now)
        self.adds = []  # (t, {key: points})

    @classmethod
    def here(cls, now=None):
        r, lines = reading(now=now), roadmap_lines()
        return cls(r, lines, now) if r and lines else None

    def _window(self, key, t):
        reset = self.read[key]["reset"]
        if reset is None or t < reset:
            return 0
        return 1 + int((t - reset) // LINES[key]["window"])

    def _reset_of(self, key, k):
        reset = self.read[key]["reset"]
        return None if reset is None else reset + k * LINES[key]["window"]

    def pct(self, key, t):
        k = self._window(key, t)
        base = self.read[key]["pct"] if k == 0 else 0.0
        return base + sum(c.get(key if key in c else "weekly", 0) for at, c in self.adds
                          if at <= t and self._window(key, at) == k)

    def line(self, key, t):
        return stop_line(key, self._reset_of(key, self._window(key, t)), self.lines, t)

    def add(self, cost, at):
        if cost:
            self.adds.append((at, dict(cost)))

    def counted(self, weekly_only=False):
        return [k for k in self.read if not (weekly_only and k == "five")]

    def room(self, key, t):
        return round(self.line(key, t) - self.pct(key, t), 1)

    def fits(self, need, t, weekly_only=False):
        return all(self.room(k, t) > _need(need, k) for k in self.counted(weekly_only))

    def fits_at(self, need, t0, weekly_only=False):
        """The first minute from t0 on when the work fits under every counted line; None when it never does (a
        fixed line without a reset time, or a cost bigger than a fresh window has room for)."""
        t = t0
        for _ in range(200):
            if t - t0 > HORIZON:
                return None
            nxt = []
            for k in self.counted(weekly_only):
                need_k = _need(need, k)
                if self.room(k, t) > need_k:
                    continue
                w = self._window(k, t)
                reset = self._reset_of(k, w)
                s = self.lines.get(k) if self.lines else None
                c = None
                if s and s["moving"] and reset is not None:
                    # The minute the moving line passes the use plus the need, in this window.
                    target = self.pct(k, t) + need_k + 0.05
                    win = LINES[k]["window"]
                    start = round(reset / 60) * 60 - win
                    begun = math.ceil((target - 0.05) * (win // 60) / 100)
                    c = max(t, start + (begun - 1) * 60)
                    for _ in range(3):
                        if c >= reset or self.room(k, c) > need_k:
                            break
                        c += 60
                    if c >= reset:
                        c = None
                if c is None:
                    if reset is None:
                        return None
                    c = reset
                nxt.append(c)
            if not nxt:
                return int(t)
            t2 = max(nxt)
            t = t2 if t2 > t else t + 60
        return None


def _need(need, key):
    if not need:
        return 0
    return float(need.get(key, need.get("weekly", 0)) or 0)


# ---------- the estimate ----------

def _est():
    import estimate
    return estimate


def _pick(pool, about, kind):
    """The finished jobs an estimate learns from, each with its weight: the most alike (H166), else the last of its
    kind, else the last of any kind; ([], "fallback", 0) with too few."""
    E = _est()
    near = E.similar(about, kind, pool) if about and pool else []
    if len(near) >= COST_MIN:
        return [(a ** E.SIM_POW, h) for a, h in near], "similar", len(near)
    same = [h for h in pool if h.get("kind") == kind][-RECENT:]
    if len(same) >= COST_MIN:
        return [(1, h) for h in same], "kind", len(same)
    anyk = pool[-RECENT:]
    if len(anyk) >= COST_MIN:
        return [(1, h) for h in anyk], "all", len(anyk)
    return [], "fallback", 0


def _quantile(pairs, q):
    """The weighted q-quantile of [(value, weight)]."""
    pairs = sorted(pairs)
    tot = sum(w for _, w in pairs) or 1
    acc = 0
    for v, w in pairs:
        acc += w
        if acc >= q * tot:
            return v
    return pairs[-1][0] if pairs else 0


def rates(text="", kind=None, hist=None, about=None):
    """Percent per minute on each line for work like this: {"five", "weekly", "how", "based"}. H173: from the finished
    jobs' own tokens once there's a rate ("tokens": weighted tokens per minute, "lo" and "hi" the range: the middle
    half of the jobs it's based on); else from the rise in the readings (H172); else START_ROOM's rates."""
    E = _est()
    hist = E.all_history() if hist is None else hist
    kind = E.kind_for(text, kind) if text or kind else kind
    about = E._about(text) if about is None else about
    real = [h for h in E._real(hist) if not E.mistake(h)]  # H286: a job's own mistake doesn't teach the rate
    model = load_rate()
    if model:
        tok = [h for h in real if isinstance(h.get("tokens"), dict) and h["tokens"] and h.get("actual")]
        pairs, how, based = _pick(tok, about, kind)
        if pairs:
            per = [(weighted(h["tokens"], model) / h["actual"], w) for w, h in pairs]
            mins = sum(w * h["actual"] for w, h in pairs)
            wpm = sum(w * weighted(h["tokens"], model) for w, h in pairs) / mins
            r = {k: wpm / model["rate"][k] if model["rate"].get(k) else FALLBACK[k] for k in KEYS}
            return {**r, "how": how, "based": based, "tokens": wpm, "lo": _quantile(per, 0.25), "hi": _quantile(per, 0.75)}
    withc = [h for h in real if isinstance(h.get("cost"), dict) and h.get("actual")]
    pairs, how, based = _pick(withc, about, kind)
    if not pairs:
        return {**FALLBACK, "how": "fallback", "based": 0}
    mins = sum(w * h["actual"] for w, h in pairs)
    return {**{k: (sum(w * float(h["cost"].get(k) or 0) for w, h in pairs) / mins) if mins else FALLBACK[k] for k in KEYS},
            "how": how, "based": based}


def cost_for(minutes, text="", kind=None, hist=None, about=None):
    """The estimated usage of work of so many minutes: {"five", "weekly", "how", "based"} (points of each line).
    H173: with a rate, also "tokens" (weighted) with its range "range" [low, high], and each line's "range" in points
    ("five_range", "weekly_range")."""
    r = rates(text, kind, hist, about)
    m = max(1, minutes or 1)
    out = {**{k: round(r[k] * m, 1) for k in KEYS}, "how": r["how"], "based": r["based"]}
    if r.get("tokens"):
        model = load_rate() or {}
        lo, hi = min(r["lo"], r["tokens"]) * m, max(r["hi"], r["tokens"]) * m
        out["tokens"], out["range"] = round(r["tokens"] * m), [round(lo), round(hi)]
        for k in KEYS:
            if (model.get("rate") or {}).get(k):
                out[k + "_range"] = [round(lo / model["rate"][k], 1), round(hi / model["rate"][k], 1)]
    return out


def at_latest(cost, minutes, latest):
    """F66: the usage of work at its latest end: each line's estimate times latest over likely minutes."""
    f = (latest / minutes) if minutes else 1
    return {k: round(float((cost or {}).get(k, 0)) * f, 1) for k in KEYS}


def job_cost(n, text, hist=None, latest=False):
    """A waiting job's estimated minutes and usage, from its estimate now (F34, H166)."""
    E = _est()
    d = E.job_estimate(n, text, hist)
    c = cost_for(d["est"], text, d.get("kind"), hist)
    if latest:  # F66: the gate lets a job start only when its latest end fits under the stop lines
        return d["latest"], {**c, **at_latest(c, d["est"], d["latest"])}
    return d["est"], c


# ---------- the real cost of a running job ----------

def _load():
    try:
        return json.load(open(TRACK))
    except (OSError, ValueError):
        return {}


def _save(d):
    os.makedirs(DIR, exist_ok=True)
    tmp = TRACK + ".tmp"
    json.dump(d, open(tmp, "w"), indent=1)
    os.replace(tmp, TRACK)


def _snap(now=None):
    r = reading(now=now)
    return {k: [r[k]["pct"], r[k]["reset"]] for k in KEYS if k in r}


def _so_far(rec):
    """What a job has used so far: its own tokens over the rate (H173), else the rise in the readings (H172)."""
    if isinstance(rec.get("own"), dict) and rec["own"]:
        return rec["own"]
    return _read_so_far(rec)


def _read_so_far(rec):
    return {k: round(rec["spent"].get(k, 0) + max(0.0, rec["last"][k][0] - rec["seg"][k][0]), 1)
            for k in KEYS if k in rec.get("seg", {}) and k in rec.get("last", {})}


def _step(rec, snap):
    """One new reading for a counting job: a reset since the last one adds what was used before it."""
    for k, (v, reset) in snap.items():
        if k not in rec["seg"]:
            rec["seg"][k] = rec["last"][k] = [v, reset]
            rec["spent"].setdefault(k, 0)
            continue
        lv, lreset = rec["last"][k]
        new_window = (reset is not None and lreset is not None and abs(reset - lreset) > SAME_RESET) or v < lv - 0.5
        if new_window:
            rec["spent"][k] = round(rec["spent"].get(k, 0) + max(0.0, lv - rec["seg"][k][0]), 1)
            rec["seg"][k] = [0.0, reset]
        rec["last"][k] = [v, reset]


def start(n, text="", now=None):
    """The job starts (jobs.py mark running): its count starts from the reading now. A held job that carries on keeps
    what it used before the hold and counts on from now. Its estimated cost is kept, to check it against."""
    now = _now() if now is None else now
    d = _load()
    rec = d.get(str(n))
    snap = _snap(now)
    if rec:
        rec.update(running=True, seg={k: list(v) for k, v in snap.items()}, last={k: list(v) for k, v in snap.items()})
    else:
        try:
            minutes, cost = job_cost(n, text)
        except Exception:
            minutes, cost = None, None
        rec = {"n": n, "started": int(now), "running": True, "spent": {k: 0 for k in KEYS},
               "seg": {k: list(v) for k, v in snap.items()}, "last": {k: list(v) for k, v in snap.items()},
               "est": ({**{k: cost[k] for k in KEYS}, "minutes": minutes, "how": cost["how"],
                        **{k: cost[k] for k in ("tokens", "range") if k in cost}} if cost else None)}
    d[str(n)] = rec
    _save(d)
    return rec


def track(n, text="", now=None):
    """Every minute while job n runs (tick.py): the newest reading. A job already running before this was built (or
    whose start wasn't seen) starts counting now and is marked late: it's never paused for an overrun."""
    d = _load()
    rec = d.get(str(n))
    if not rec:
        rec = start(n, text, now)
        rec["late"] = True
        d = _load()
    elif rec.get("running", True):
        _step(rec, _snap(now))
    if rec.get("running", True):  # H173: its own tokens, from its own chats
        _own(rec, n)
    if isinstance(rec.get("est"), dict):  # H220: the top of its estimate, with the guesses known by now
        rec["est"]["top"] = top_factor(rec["est"], job_guesses(n))
    d[str(n)] = rec
    _save(d)
    return {**rec, "so_far": _so_far(rec)}


def _own(rec, n):
    try:
        t = job_tokens(n, rec.get("started"))
    except Exception:
        t = None
    if t:
        rec["tokens"] = t
        c = own_cost(t)
        if c:
            rec["own"] = c


def hold(n, now=None):
    """The usage line held the job (jobs.py held N): the count stops here until it carries on."""
    d = _load()
    rec = d.get(str(n))
    if rec:
        if rec.get("running", True):
            _step(rec, _snap(now))
        rec["spent"] = _read_so_far(rec) or rec["spent"]
        rec["seg"] = {k: list(v) for k, v in rec["last"].items()}
        rec["running"] = False
        _save(d)
    return rec


def finish(n, now=None):
    """The job is done: its real cost ({"five", "weekly"}) and the estimate it started with; None when nothing was
    counted. Its count is removed."""
    d = _load()
    rec = d.pop(str(n), None)
    if not rec:
        return None
    if rec.get("running", True):
        _step(rec, _snap(now))
    _save(d)
    read = _read_so_far(rec) if rec.get("running", True) else {k: rec["spent"].get(k, 0) for k in KEYS if k in rec["spent"]}
    # H173: its own tokens, all of its chats from its start to now; the cost is those over the rate.
    try:
        t = job_tokens(n, rec.get("started"), now)
    except Exception:
        t = None
    own = own_cost(t) if t else None
    if not read and not t:
        return None
    return {"cost": own or read, "how": "tokens" if own else "read", "cost_read": read or None, "tokens": t,
            "est_cost": rec.get("est"), "late": bool(rec.get("late"))}


def top_factor(est, guesses=None):
    """H220: how unsure an estimate is, as a factor from 1 to TOP_MAX: the high end of the jobs it's based on (its
    tokens' range, the middle half's top, over its middle) and the longest guess of its minutes (the first look's, the
    call's, the team's own; {key: minutes}) over the computed minutes. The top of the estimate is the estimate times
    this."""
    est = est or {}
    f = 1.0
    if est.get("range") and est.get("tokens"):
        f = max(f, float(est["range"][1]) / float(est["tokens"]))
    m = est.get("minutes")
    if m:
        for g in (guesses or {}).values():
            if isinstance(g, (int, float)) and 0 < g <= 600:
                f = max(f, g / float(m))
    return round(min(TOP_MAX, f), 2)


def job_guesses(n):
    """H220: the guesses kept for job n ({key: minutes}), from the estimates."""
    try:
        e = _est()._load_state().get(str(n)) or {}
    except Exception:
        return {}
    return {k: e[k] for k in GUESS_KEYS if e.get(k)}


def overrun(rec):
    """None, or {"line", "used", "est", "top"} when the running job has used about four times the top of its estimated
    cost on a line (H220: the top is the estimate times top_factor, kept in its est as "top" by track)."""
    if not rec or (rec.get("late") and not rec.get("own")) or rec.get("allowed") or not rec.get("est"):
        return None
    so_far = rec.get("so_far") or _so_far(rec)
    f = float(rec["est"].get("top") or 1)
    for k in KEYS:
        est, used = float(rec["est"].get(k) or 0), so_far.get(k)
        if used is None:
            continue
        top = round(est * f, 1)
        if used >= OVER * top and used - est >= OVER_MIN[k]:
            return {"line": k, "used": used, "est": est, "top": top}
    return None


def usage_backtest(hist=None, last=None):
    """H220: every finished job with its own tokens, its usage estimated back from only the jobs finished before it
    (minutes from estimate_detail under its kind, usage from cost_for): {"jobs", "median", "within", "twice", "four",
    "top", "at"}: the median of real over estimated usage on the 5-hour line, how many within a factor 1.5, and the jobs
    the pause would have stopped at twice, four times, and four times the top (with the guesses kept on its line)."""
    E = _est()
    hist = sorted(E.all_history() if hist is None else hist, key=lambda h: h.get("done") or 0)
    rows = []
    for i, h in enumerate(hist):
        c = h.get("cost")
        if not (isinstance(c, dict) and c.get("five") and h.get("tokens") and h.get("actual")):
            continue
        prior = hist[:i]
        if len(E._real(prior)) < COST_MIN:
            continue
        d = E.estimate_detail("", prior, h.get("kind"), h.get("machine"), h.get("tags") or [], h.get("about") or "")
        e = cost_for(d["est"], "", h.get("kind"), prior, h.get("about") or "")
        e["minutes"] = d["est"]
        rows.append((h.get("n"), float(c["five"]), float(e["five"] or 0.1),
                     top_factor(e, {k: h[k] for k in GUESS_KEYS if h.get(k)})))
    if last:
        rows = rows[-last:]
    out = {"jobs": len(rows), "twice": [], "four": [], "top": [], "at": {}}
    if not rows:
        return out
    ratios = sorted(u / e for _, u, e, _ in rows)
    out["median"] = round(ratios[len(ratios) // 2], 2)
    out["within"] = sum(1 for r in ratios if 1 / 1.5 <= r <= 1.5)
    for name, mult in (("twice", lambda f: 2), ("four", lambda f: 4), ("top", lambda f: OVER * f)):
        pts = sorted(mult(f) * e for _, _, e, f in rows)
        out["at"][name] = round(pts[len(pts) // 2], 1)
        out[name] = [n for n, u, e, f in rows if u >= mult(f) * e and u - e >= OVER_MIN["five"]]
    return out


def pause_backtest(hist=None):
    """H220: every finished job with an estimated and a real cost, against the pause: {"jobs", "twice", "four", "top"}
    with the jobs each rule would have paused (twice its estimate until H221, four times until H220, four times the top
    of its estimate now), and the median pause point in points of the 5-hour line for each."""
    E = _est()
    hist = E.all_history() if hist is None else hist
    out = {"jobs": 0, "twice": [], "four": [], "top": [], "at": {"twice": [], "four": [], "top": []}}
    for h in hist:
        e, c = h.get("est_cost"), h.get("cost")
        if not (isinstance(e, dict) and isinstance(c, dict) and e.get("five")):
            continue
        out["jobs"] += 1
        est, used = float(e["five"]), float(c.get("five") or 0)
        f = top_factor(e, {k: h[k] for k in GUESS_KEYS if h.get(k)})
        for name, line in (("twice", 2 * est), ("four", 4 * est), ("top", OVER * est * f)):
            out["at"][name].append(line)
            if used >= line and used - est >= OVER_MIN["five"]:
                out[name].append(h.get("n"))
    for name in ("twice", "four", "top"):
        v = sorted(out["at"][name])
        out["at"][name] = round(v[len(v) // 2], 1) if v else None
    return out


def allow(n):
    """jobs.py resume N: he let the paused job carry on; it isn't paused for an overrun again."""
    d = _load()
    rec = d.get(str(n)) or {"n": n, "spent": {k: 0 for k in KEYS}, "seg": {}, "last": {}, "running": False}
    rec["allowed"] = True
    rec["running"] = False
    d[str(n)] = rec
    _save(d)
    return rec


def forget(n):
    d = _load()
    if d.pop(str(n), None) is not None:
        _save(d)


def short_what(text):
    """What a job is about, in a few words: "H172 on the HQ roadmap: usage that keeps itself in check. ..." gives
    "usage that keeps itself in check"."""
    t = re.sub(r"^(?:Scheduled item \d+[^:]*:\s*)?", "", text or "")
    m = re.match(r"^[HFMLJ]\d+(?:\.\d+)? on the (?:HQ )?roadmap:\s*([^.]+)", t)
    s = m.group(1) if m else re.split(r"(?<=[a-z])\.\s", t, 1)[0]
    return s.strip()[:120]


def paused_words(n, text, o):
    """Donna's facts for a paused job: plain, everyday words (the text is sent as it is when she can't compose)."""
    line = "the five-hour usage" if o["line"] == "five" else "the weekly usage"
    return (f"Heads up: I paused one of the team's jobs, {short_what(text)}. It had used about {o['used']:g}% of "
            f"{line}, roughly four times the most it was expected to take, so I stopped it before it burns more. It won't start "
            f"again by itself; tell me on a call if it should carry on or be dropped.")


# ---------- past jobs: from the saved readings ----------

_LOG = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) usage check · [^,]*, read ([^:]+): (.*)$")


def log_readings(path=None):
    """[(t, {"five": pct, "weekly": pct})] from usage.log, oldest first: when each reading was really read."""
    path = USAGE_LOG if path is None else path
    out = []
    try:
        lines = open(path, encoding="utf8").read().splitlines()
    except (OSError, TypeError):
        return out
    for l in lines:
        m = _LOG.match(l)
        if not m:
            continue
        t = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
        ago = m.group(2).strip()
        a = re.match(r"(?:(\d+) h )?(\d+) min ago", ago)
        if a:
            t -= (int(a.group(1) or 0) * 60 + int(a.group(2))) * 60
        elif ago != "just now":
            continue
        v = {}
        for part in m.group(3).split(" / "):
            p = re.match(r"\s*(\d+)%\s+(.+?)\s{2}", part + "  ")
            if not p or "last known" in part or "reset since" in part:
                continue
            k = line_key(p.group(2))
            if k in KEYS:
                v[k] = float(p.group(1))
        if v:
            out.append((t, v))
    out.sort(key=lambda x: x[0])
    return out


def cost_between(readings, a, b):
    """The use on each line from a to b from the readings, a drop counted as a reset; None when no reading is close
    enough to either end."""
    out = {}
    for k in KEYS:
        rs = [(t, v[k]) for t, v in readings if k in v]
        before = [x for x in rs if a - NEAR["before"] <= x[0] <= a]
        first = before[-1] if before else next((x for x in rs if a < x[0] <= a + 5 * 60), None)
        after = [x for x in rs if b <= x[0] <= b + NEAR["after"]]
        last = after[0] if after else next((x for x in reversed(rs) if b - 5 * 60 <= x[0] < b), None)
        if not first or not last or last[0] <= first[0]:
            continue
        span = [x for x in rs if first[0] <= x[0] <= last[0]]
        used, prev = 0.0, span[0][1]
        for _, v in span[1:]:
            used += v - prev if v >= prev else v  # a drop: the window reset, what's there now came after it
            prev = v
        out[k] = round(used, 1)
    return out or None


def backfill(readings=None, write=True):
    """The finished jobs' cost from the saved readings, for this computer's lines without one. Returns (filled, left)."""
    E = _est()
    readings = log_readings() if readings is None else readings
    lines = E.history()
    filled = left = 0
    for h in lines:
        if isinstance(h.get("cost"), dict) or h.get("cost_how") == "none":
            continue
        if not h.get("done") or not h.get("actual") or h.get("how") == "seed":
            continue
        c = cost_between(readings, h["done"] - h["actual"] * 60, h["done"]) if readings else None
        if c and all(k in c for k in KEYS):
            h["cost"], h["cost_how"] = c, "log"
            filled += 1
        else:
            left += 1
    if write and filled:
        os.makedirs(DIR, exist_ok=True)
        tmp = E.HISTORY + ".tmp"
        with open(tmp, "w", encoding="utf8") as f:
            f.writelines(json.dumps(h) + "\n" for h in lines)
        os.replace(tmp, E.HISTORY)
    return filled, left


BACKFILLED = os.path.join(DIR, "job-usage-backfill")


def backfill_once(log=None):
    """By itself, once on each computer (tick.py): the computer that pulls this code fills its own past jobs."""
    if os.path.exists(BACKFILLED):
        return None
    filled, left = backfill()
    os.makedirs(DIR, exist_ok=True)
    open(BACKFILLED, "w").write(f"{int(_now())} {filled} {left}\n")
    if log:
        log(f"usage: the cost of {filled} finished jobs filled from the saved readings ({left} couldn't be matched)")
    return filled, left


# ---------- H173: a job's own tokens, and how many make a point ----------
#
# The user, 16 October 2026 (call at 13:37): "Isn't it possible that right now they would run it in isolation? They
# track how many tokens are used and what percentage is used. They can therefore conclude over time how many tokens
# correspond to what percentage." and "when we run the nightly checks nobody is using it so we know those numbers are
# more accurate as well."
#
# Every job runs as its own Claude Code chat, and Claude Code writes each chat to a session file (one JSON line per
# message, the assistant's with its usage: input, output, cache read, cache write, and the model). The chat of job N
# is the one whose first prompt says "This is job N from the queue" (a crash rerun or a carry-on is another chat with
# the same first words: they all count); the helpers it starts write theirs under <session>/subagents/. A message
# split over several lines carries the same usage on each: counted once, by its id.
#
# The rate: weighted tokens = for each model, its weight times (input, output, cache read and cache write tokens, each
# with its weight). How many weighted tokens make one point of the 5-hour and of the weekly is learned from the
# finished jobs: their own tokens against the rise in the saved readings while they ran (H172's count, now kept as
# "cost_read"). The weights start from the API's price ratios (PRIOR, MODEL_PRIOR) and move with the data, a ridge
# fit that counts the prior as PRIOR_N jobs. A reading that rose far more than the job's tokens explain (OUT_RATIO
# times and OUT_MIN points more: a call, the mail check or someone else on the plan at the same time) is left out;
# the nightly run counts NIGHTLY times, nobody else is on the plan at 2 at night. Kept in usage-rate.json, learned
# again when a job is done.
#
# A job's real cost is then its own tokens divided by the rate: what others use at the same time no longer counts
# against it, nor towards the pause at four times its estimate. The gate before a start still reads the real total.
# [The priors, PRIOR_N 10, OUT_RATIO 2.5 with OUT_MIN 2, NIGHTLY 3 and RATE_MIN 5 are Claude's choice.]

TOKEN_KINDS = ("in", "out", "cr", "cw")  # input, output, cache read, cache write
PRIOR = {"in": 1.0, "out": 5.0, "cr": 0.1, "cw": 1.6}  # the API's price ratios (cache write between 5 min and 1 h)
MODEL_PRIOR = {"opus": 1.0, "fable": 1.0, "sonnet": 0.6, "haiku": 0.2, "other": 1.0}
PRIOR_N = 10      # the prior counts as this many jobs
OUT_RATIO = 2.5   # a reading that rose this many times more than the tokens explain ...
OUT_MIN = 2.0     # ... and at least this many points more is someone else on the plan: left out
NIGHTLY = 3       # the nightly run's weight as a sample
RATE_MIN = 5      # finished jobs with tokens and a reading before there's a rate
RATE_FILE = os.path.join(DIR, "usage-rate.json")
SESSIONS = os.path.join(DIR, "job-sessions.json")
if os.environ.get("HQ_CLAUDE_PROJECTS") is not None:
    PROJECTS = os.environ["HQ_CLAUDE_PROJECTS"]
elif _TEST:
    PROJECTS = ""
else:
    PROJECTS = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"), "projects")
_JOB = re.compile(r"\bThis is job (\d+) from the queue")


def family(model):
    m = (model or "").lower()
    for f in ("opus", "fable", "sonnet", "haiku"):
        if f in m:
            return f
    return "other"


def _first_prompt(path):
    """(text, time) of a session's first prompt, or (None, None) when it has none yet."""
    try:
        with open(path, encoding="utf8", errors="replace") as f:
            for i, l in enumerate(f):
                if i > 400:
                    break
                if '"type":"user"' not in l.replace(" ", ""):
                    continue
                try:
                    d = json.loads(l)
                except ValueError:
                    continue
                if d.get("type") != "user" or d.get("isMeta"):
                    continue
                c = (d.get("message") or {}).get("content")
                if not isinstance(c, str):
                    c = " ".join(x.get("text", "") for x in c or [] if isinstance(x, dict))
                if c.strip():
                    return c, _iso(d.get("timestamp"))
    except OSError:
        pass
    return None, None


def sessions(projects=None):
    """Every Claude Code session on this computer with what it was: {path: {"job": N | None, "call": bool, "at": t}}.
    A session's first prompt never changes, so each one is read once (job-sessions.json)."""
    projects = PROJECTS if projects is None else projects
    if not projects or not os.path.isdir(projects):
        return {}
    try:
        idx = json.load(open(SESSIONS))
    except (OSError, ValueError):
        idx = {}
    changed = False
    for d in os.listdir(projects):
        full = os.path.join(projects, d)
        if not os.path.isdir(full):
            continue
        for name in os.listdir(full):
            p = os.path.join(full, name)
            if not name.endswith(".jsonl") or p in idx:
                continue
            text, at = _first_prompt(p)
            if text is None:
                continue
            m = _JOB.search(text[:400])
            idx[p] = {"job": int(m.group(1)) if m else None, "call": text.startswith("[Call system:"), "at": at}
            changed = True
    if changed:
        os.makedirs(DIR, exist_ok=True)
        tmp = SESSIONS + ".tmp"
        json.dump(idx, open(tmp, "w"))
        os.replace(tmp, SESSIONS)
    return {p: v for p, v in idx.items() if os.path.exists(p)}


def _with_helpers(path):
    """A session and the sessions of the helpers it started (the Agent tool's, under <session>/subagents/)."""
    sub = os.path.join(os.path.splitext(path)[0], "subagents")
    try:
        return [path] + sorted(os.path.join(sub, n) for n in os.listdir(sub) if n.endswith(".jsonl"))
    except OSError:
        return [path]


def job_sessions(n, since=None, until=None, idx=None):
    """The session files of job n's chats (with their helpers), first prompt from since on (an hour of slack: the
    clock of a carry-on) and before until."""
    idx = sessions() if idx is None else idx
    out = []
    for p, v in sorted(idx.items(), key=lambda x: x[1].get("at") or 0):
        if v.get("job") != n:
            continue
        at = v.get("at") or 0
        if (since and at < since - 3600) or (until and at > until + 300):
            continue
        out += _with_helpers(p)
    return out


def tokens_of(paths, since=None, until=None):
    """The tokens in these session files: {family: [input, output, cache read, cache write]}, each message once."""
    seen, out = set(), {}
    for p in paths:
        try:
            f = open(p, encoding="utf8", errors="replace")
        except OSError:
            continue
        with f:
            for l in f:
                if '"usage"' not in l or '"assistant"' not in l:
                    continue
                try:
                    d = json.loads(l)
                except ValueError:
                    continue
                msg = d.get("message") or {}
                u = msg.get("usage")
                if d.get("type") != "assistant" or not isinstance(u, dict):
                    continue
                key = msg.get("id") or d.get("requestId") or d.get("uuid")
                if key in seen or msg.get("model") == "<synthetic>":
                    continue
                t = _iso(d.get("timestamp"))
                if t is not None and ((since and t < since) or (until and t > until)):
                    continue
                seen.add(key)
                v = out.setdefault(family(msg.get("model")), [0, 0, 0, 0])
                v[0] += int(u.get("input_tokens") or 0)
                v[1] += int(u.get("output_tokens") or 0)
                v[2] += int(u.get("cache_read_input_tokens") or 0)
                v[3] += int(u.get("cache_creation_input_tokens") or 0)
    return out


def job_tokens(n, since=None, until=None):
    """Job n's own tokens, from its chats; None when none of its chats is on this computer."""
    paths = job_sessions(n, since, until)
    if not paths:
        return None
    t = tokens_of(paths, (since - 120) if since else None, until)
    return t or None


def weighted(tokens, model=None):
    """Weighted tokens: each model's weight times its tokens, each kind with its weight."""
    model = model or load_rate() or {}
    kw, mw = model.get("weights") or PRIOR, model.get("models") or MODEL_PRIOR
    return sum(mw.get(f, mw.get("other", 1.0)) * sum(kw[k] * v[i] for i, k in enumerate(TOKEN_KINDS))
               for f, v in (tokens or {}).items())


def own_cost(tokens, model=None):
    """A job's own cost, {"five", "weekly"}: its weighted tokens over the learned rate; None without a rate."""
    model = model or load_rate()
    if not tokens or not model or not model.get("rate"):
        return None
    w = weighted(tokens, model)
    return {k: round(w / model["rate"][k], 2) for k in KEYS if model["rate"].get(k)}


def load_rate():
    try:
        r = json.load(open(RATE_FILE))
        return r if r.get("rate") else None
    except (OSError, ValueError):
        return None


def _solve(A, b):
    """A small linear system by Gaussian elimination with pivoting; None when it's singular."""
    n = len(b)
    M = [list(A[i]) + [b[i]] for i in range(n)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-12:
            return None
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                M[r] = [x - f * y for x, y in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def _ridge(rows, ys, wts):
    """Multipliers g (prior 1) with y ~ sum(g_j * row_j): the prior counts as PRIOR_N jobs."""
    m = len(rows[0])
    sw = sum(wts) or 1
    lam = PRIOR_N * sum(w * sum(r) ** 2 for r, w in zip(rows, wts)) / sw / max(m, 1)
    A = [[sum(w * r[i] * r[j] for r, w in zip(rows, wts)) + (lam if i == j else 0) for j in range(m)] for i in range(m)]
    b = [sum(w * r[i] * y for r, y, w in zip(rows, ys, wts)) + lam for i in range(m)]
    g = _solve(A, b) or [1.0] * m
    return [min(20.0, max(0.05, x)) for x in g]


def read_cost(h):
    """The rise in the saved readings while a finished job ran (H172), or None."""
    c = h.get("cost_read")
    if isinstance(c, dict):
        return c
    if isinstance(h.get("cost"), dict) and h.get("cost_how") in ("read", "log"):
        return h["cost"]
    return None


def is_nightly(h):
    """The nightly run (H169): its planned item's words, as the job's text carries them."""
    return "h169, the nightly run" in (h.get("about") or "").lower()


def learn(hist=None, write=True):
    """The rate from the finished jobs with their own tokens and a reading: the weights per kind of token and per
    model, how many weighted tokens make one point of each line, and which jobs were left out as outliers."""
    E = _est()
    hist = E.all_history() if hist is None else hist
    samples = [h for h in hist if isinstance(h.get("tokens"), dict) and h["tokens"] and read_cost(h)
               and all(k in read_cost(h) for k in KEYS)]
    if len(samples) < RATE_MIN:
        return None
    wt = [NIGHTLY if is_nightly(h) else 1 for h in samples]
    ys = [float(read_cost(h)["five"]) for h in samples]
    kw, mw = dict(PRIOR), dict(MODEL_PRIOR)
    fams = sorted({f for h in samples for f in h["tokens"]})
    keep = [True] * len(samples)
    for _ in range(3):
        idx = [i for i in range(len(samples)) if keep[i]]
        if len(idx) < RATE_MIN:
            break
        # The kinds of token: each kind's share at the prior weights, a multiplier per kind.
        rows = [[sum(mw.get(f, 1.0) * PRIOR[k] * samples[i]["tokens"][f][j] for f in samples[i]["tokens"]) / 1e6
                 for j, k in enumerate(TOKEN_KINDS)] for i in idx]
        r0 = sum(ys[i] * wt[i] for i in idx) / (sum(sum(r) * wt[i] for r, i in zip(rows, idx)) or 1)
        g = _ridge([[x * r0 for x in r] for r in rows], [ys[i] for i in idx], [wt[i] for i in idx])
        tot = [sum(r[j] for r in rows) for j in range(len(TOKEN_KINDS))]
        G = sum(gj * t for gj, t in zip(g, tot)) / (sum(tot) or 1)
        kw = {k: PRIOR[k] * g[j] / (G or 1) for j, k in enumerate(TOKEN_KINDS)}
        # The models: a multiplier per model, the main one (the most tokens) staying at its prior.
        rows = [[MODEL_PRIOR.get(f, 1.0) * sum(kw[k] * samples[i]["tokens"].get(f, [0] * 4)[j]
                                                for j, k in enumerate(TOKEN_KINDS)) / 1e6 for f in fams] for i in idx]
        r0 = sum(ys[i] * wt[i] for i in idx) / (sum(sum(r) * wt[i] for r, i in zip(rows, idx)) or 1)
        g = _ridge([[x * r0 for x in r] for r in rows], [ys[i] for i in idx], [wt[i] for i in idx])
        main = max(range(len(fams)), key=lambda j: sum(r[j] for r in rows))
        mw = {**MODEL_PRIOR, **{f: MODEL_PRIOR.get(f, 1.0) * g[j] / g[main] for j, f in enumerate(fams)}}
        # The outliers: the reading rose far more than the tokens explain.
        W = [weighted(h["tokens"], {"weights": kw, "models": mw}) for h in samples]
        rate5 = sum(W[i] * wt[i] for i in idx) / (sum(ys[i] * wt[i] for i in idx) or 1)
        new = [not (ys[i] > OUT_RATIO * W[i] / rate5 and ys[i] - W[i] / rate5 >= OUT_MIN) for i in range(len(samples))]
        if new == keep:
            break
        keep = new
    idx = [i for i in range(len(samples)) if keep[i]]
    W = [weighted(h["tokens"], {"weights": kw, "models": mw}) for h in samples]
    rate = {}
    for k in KEYS:
        pts = sum(float(read_cost(samples[i])[k]) * wt[i] for i in idx)
        rate[k] = round(sum(W[i] * wt[i] for i in idx) / pts) if pts > 0 else None
    model = {"weights": {k: round(v, 4) for k, v in kw.items()}, "models": {k: round(v, 4) for k, v in mw.items()},
             "rate": rate, "based": len(idx), "nightly": sum(1 for i in idx if is_nightly(samples[i])),
             "left_out": [samples[i].get("n") for i in range(len(samples)) if not keep[i]], "at": int(_now())}
    if write:
        os.makedirs(DIR, exist_ok=True)
        tmp = RATE_FILE + ".tmp"
        json.dump(model, open(tmp, "w"), indent=1)
        os.replace(tmp, RATE_FILE)
    return model


def backfill_tokens(write=True):
    """The finished jobs' own tokens from their session files, where those are still on this computer, and their
    cost from them once there's a rate. Returns (filled, left)."""
    E = _est()
    lines = E.history()
    idx = sessions()
    filled = left = 0
    for h in lines:
        if isinstance(h.get("tokens"), dict) or not h.get("done") or not h.get("actual") or h.get("how") == "seed":
            continue
        start = h["done"] - h["actual"] * 60
        paths = job_sessions(h.get("n"), start - 1800, h["done"], idx)
        t = tokens_of(paths, start - 1800, h["done"] + 300) if paths else None
        if t:
            h["tokens"] = t
            filled += 1
        else:
            left += 1
    model = learn(lines + [h for h in E.all_history() if h.get("machine") != E.me()["name"]], write=write)
    for h in lines:
        if isinstance(h.get("tokens"), dict) and read_cost(h) and "cost_read" not in h:
            h["cost_read"] = read_cost(h)
        c = own_cost(h.get("tokens"), model)
        if c:
            h["cost"], h["cost_how"] = c, "tokens"
    if write:
        os.makedirs(DIR, exist_ok=True)
        tmp = E.HISTORY + ".tmp"
        with open(tmp, "w", encoding="utf8") as f:
            f.writelines(json.dumps(h) + "\n" for h in lines)
        os.replace(tmp, E.HISTORY)
    return filled, left


TOKENS_FILLED = os.path.join(DIR, "job-usage-tokens")


def tokens_once(log=None):
    """By itself, once on each computer (tick.py): its past jobs get their own tokens and the rate is learned."""
    if os.path.exists(TOKENS_FILLED) or not PROJECTS:
        return None
    filled, left = backfill_tokens()
    open(TOKENS_FILLED, "w").write(f"{int(_now())} {filled} {left}\n")
    if log:
        log(f"usage: the own tokens of {filled} finished jobs read from their chats ({left} not on this computer); "
            f"rate: {rate_words(load_rate())}")
    return filled, left


def calls(n=10):
    """H173: what the last n calls cost on their own: [{"at", "tokens", "cost"}], newest first."""
    idx = sessions()
    out = []
    for p, v in sorted(idx.items(), key=lambda x: -(x[1].get("at") or 0)):
        if not v.get("call"):
            continue
        t = tokens_of(_with_helpers(p))
        if t:
            out.append({"at": v.get("at"), "tokens": t, "weighted": round(weighted(t)), "cost": own_cost(t)})
        if len(out) >= n:
            break
    return out


def mtok(w):
    w = float(w or 0)
    return f"{w / 1e6:.1f}M" if w >= 1e6 else f"{w / 1e3:.0f}k"


def rate_words(model):
    if not model:
        return "no rate yet (too few finished jobs with their own tokens and a reading)"
    r = model["rate"]
    return (f"{mtok(r.get('five'))} weighted tokens a point of the 5-hour, {mtok(r.get('weekly'))} a point of the week, "
            f"from {model['based']} jobs ({model.get('nightly', 0)} nightly), {len(model.get('left_out') or [])} left out")


# ---------- in words ----------

def pct(x):
    x = round(float(x), 1)
    return f"{x:g}%"


def cost_words(c):
    """"about 4% of the 5-hour and 0.8% of the week"."""
    if not c:
        return ""
    return f"about {pct(c.get('five', 0))} of the 5-hour and {pct(c.get('weekly', 0))} of the week"


def used_words(c):
    if not c:
        return ""
    return f"used {pct(c.get('five', 0))} of the 5-hour and {pct(c.get('weekly', 0))} of the week"


def main(argv):
    cmd = argv[0] if argv else "--help"
    if cmd == "now":
        r, lines, now = reading(), roadmap_lines(), _now()
        if not r:
            print("No usage reading.")
            return 0
        p = Projection(r, lines, now)
        for k, v in r.items():
            print(f"{k}: at {pct(v['pct'])}, stop line {p.line(k, now) if lines else '-'}%, room "
                  f"{p.room(k, now) if lines else '-'}%" + (f", resets {time.strftime('%a %H:%M', time.localtime(v['reset']))}"
                                                           if v["reset"] else ""))
        return 0
    if cmd in ("cost", "when") and len(argv) > 1:
        text = argv[1]
        E = _est()
        minutes = int(argv[2]) if len(argv) > 2 else E.estimate_detail(text)["est"]
        c = cost_for(minutes, text)
        print(f"About {minutes} min, {cost_words(c)} (from {c['how']}, {c['based']} jobs).")
        if c.get("tokens"):
            print(f"In tokens: about {mtok(c['tokens'])} weighted ({mtok(c['range'][0])} to {mtok(c['range'][1])}), "
                  f"{pct(c['five_range'][0])} to {pct(c['five_range'][1])} of the 5-hour.")
        if cmd == "when":
            p = Projection.here()
            t = p.fits_at(c, _now()) if p else None
            print("Fits now." if t and t - _now() < 60 else f"Fits around {time.strftime('%a %H:%M', time.localtime(t))}."
                  if t else "No time: no reading, no stop lines, or it never fits.")
        return 0
    if cmd == "rate":  # H173
        m = learn()
        print("Rate: " + rate_words(m) + ".")
        if m:
            print("Weights per kind of token (input 1 at the API's prices): " + ", ".join(f"{k} {v:g}" for k, v in m["weights"].items())
                  + "; per model: " + ", ".join(f"{k} {v:g}" for k, v in m["models"].items()) + ".")
            if m["left_out"]:
                print("Left out (the readings rose far more than their own tokens explain): jobs " + ", ".join(map(str, m["left_out"])) + ".")
        return 0
    if cmd == "tokens" and len(argv) > 1:  # H173: a job's own tokens and cost, running or finished
        n = int(argv[1])
        rec = _load().get(str(n)) or {}
        h = next((h for h in reversed(_est().history()) if h.get("n") == n), {})
        t = job_tokens(n, rec.get("started") or ((h["done"] - h["actual"] * 60) if h.get("done") else None), h.get("done"))
        if not t:
            print(f"Job {n}: no chat of it on this computer.")
            return 1
        print(f"Job {n}: " + "; ".join(f"{f}: {v[0]} in, {v[1]} out, {v[2]} cache read, {v[3]} cache write" for f, v in t.items())
              + f"; {mtok(weighted(t))} weighted" + (f", {used_words(own_cost(t))}" if own_cost(t) else "") + ".")
        return 0
    if cmd == "calls":  # H173: what the calls cost on their own
        for c in calls(int(argv[1]) if len(argv) > 1 else 10):
            when = time.strftime("%a %d %b %H:%M", time.localtime(c["at"])) if c["at"] else "?"
            print(f"call {when}: {mtok(c['weighted'])} weighted tokens" + (f", {used_words(c['cost'])}" if c["cost"] else ""))
        return 0
    if cmd == "fill":  # H173
        filled, left = backfill_tokens()
        print(f"Read the own tokens of {filled} finished jobs from their chats; {left} aren't on this computer. Rate: {rate_words(load_rate())}.")
        return 0
    if cmd == "backfill":
        filled, left = backfill()
        print(f"Filled the cost of {filled} finished jobs from the saved readings; {left} couldn't be matched.")
        return 0
    if cmd == "pauses":  # H220
        b = pause_backtest()
        for name, words in (("twice", "twice the estimate (until H221)"), ("four", "four times the estimate (H221)"),
                            ("top", "four times the top of the estimate (H220)")):
            jobs_ = b[name]
            print(f"At {words}: {len(jobs_)} of {b['jobs']} finished jobs would have paused"
                  + (f" (jobs {', '.join(map(str, jobs_))})" if jobs_ else "") + f"; the pause point is {b['at'][name]}% "
                  "of the 5-hour line for the middle job.")
        return 0
    if cmd == "costs":
        n = int(argv[1]) if len(argv) > 1 else 20
        for h in _est().history()[-n:]:
            c = h.get("cost")
            print(f"job {h.get('n')}: {h.get('actual')} min" + (f", {used_words(c)} ({h.get('cost_how', 'read')})" if c else ", no cost"))
        return 0
    print(__doc__)
    return 0 if cmd in ("-h", "--help") else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
