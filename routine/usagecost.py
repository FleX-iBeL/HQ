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
  - The stop at the line for a running job stays as it is (H113). New: a job whose real cost reaches about twice its
    estimate (OVER times, and at least OVER_MIN points more than the estimate, so a rounding of the readings doesn't do
    it) is paused for good: its chat ends, it isn't started again by itself, and Donna texts him in plain words. A
    call lets it carry on (jobs.py resume N, in its own chat, H113) or cancels it (jobs.py stop N).

[The numbers are Claude's choice: COST_MIN 3 jobs, OVER 2 with OVER_MIN 3 points on the 5-hour line and 1 on the
weekly; the readings are whole percents, so a short job's cost is rough, and it evens out over many jobs.]

Files, in HQ's .status (never in the repo), next to the estimates: job-usage.json (the running and held jobs' count).
A test's copy of the roadmap (HQ_ROADMAP) gets its own files next to it and reads no real usage unless HQ_USAGE names
a reading (and HQ_USAGE_LOG a log), so tests never touch or depend on the real ones.

usage:
  python3 routine/usagecost.py now                 the reading the gate uses, each line's stop line and room
  python3 routine/usagecost.py cost "TEXT" [MIN]   a job's estimated usage, and what it's based on
  python3 routine/usagecost.py when "TEXT" [MIN]   when a job like that would fit, with nothing else running
  python3 routine/usagecost.py backfill            fill the finished jobs' cost from the saved readings (once is enough)
  python3 routine/usagecost.py costs [N]           the last N finished jobs with their time and cost
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
OVER = 2            # a running job at this many times its estimated cost pauses for good
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


def rates(text="", kind=None, hist=None, about=None):
    """Percent per minute on each line for work like this: {"five", "weekly", "how", "based"}."""
    E = _est()
    hist = E.all_history() if hist is None else hist
    kind = E.kind_for(text, kind) if text or kind else kind
    withc = [h for h in E._real(hist) if isinstance(h.get("cost"), dict) and h.get("actual")]
    about = E._about(text) if about is None else about

    def ratio(pairs):
        mins = sum(w * h["actual"] for w, h in pairs)
        return {k: (sum(w * float(h["cost"].get(k) or 0) for w, h in pairs) / mins) if mins else FALLBACK[k] for k in KEYS}

    near = E.similar(about, kind, withc) if about and withc else []
    if len(near) >= COST_MIN:
        r, how, based = ratio([(a ** E.SIM_POW, h) for a, h in near]), "similar", len(near)
    else:
        same = [h for h in withc if h.get("kind") == kind][-RECENT:]
        anyk = withc[-RECENT:]
        if len(same) >= COST_MIN:
            r, how, based = ratio([(1, h) for h in same]), "kind", len(same)
        elif len(anyk) >= COST_MIN:
            r, how, based = ratio([(1, h) for h in anyk]), "all", len(anyk)
        else:
            r, how, based = dict(FALLBACK), "fallback", 0
    return {**{k: r[k] for k in KEYS}, "how": how, "based": based}


def cost_for(minutes, text="", kind=None, hist=None, about=None):
    """The estimated usage of work of so many minutes: {"five", "weekly", "how", "based"} (points of each line)."""
    r = rates(text, kind, hist, about)
    m = max(1, minutes or 1)
    return {**{k: round(r[k] * m, 1) for k in KEYS}, "how": r["how"], "based": r["based"]}


def job_cost(n, text, hist=None):
    """A waiting job's estimated minutes and usage, from its estimate now (F34, H166)."""
    E = _est()
    d = E.job_estimate(n, text, hist)
    return d["est"], cost_for(d["est"], text, d.get("kind"), hist)


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
               "est": ({**{k: cost[k] for k in KEYS}, "minutes": minutes, "how": cost["how"]} if cost else None)}
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
    d[str(n)] = rec
    _save(d)
    return {**rec, "so_far": _so_far(rec)}


def hold(n, now=None):
    """The usage line held the job (jobs.py held N): the count stops here until it carries on."""
    d = _load()
    rec = d.get(str(n))
    if rec:
        if rec.get("running", True):
            _step(rec, _snap(now))
        rec["spent"] = _so_far(rec) or rec["spent"]
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
    cost = _so_far(rec) if rec.get("running", True) else {k: rec["spent"].get(k, 0) for k in KEYS if k in rec["spent"]}
    if not cost:
        return None
    return {"cost": cost, "est_cost": rec.get("est"), "late": bool(rec.get("late"))}


def overrun(rec):
    """None, or {"line", "used", "est"} when the running job has used about twice its estimated cost on a line."""
    if not rec or rec.get("late") or rec.get("allowed") or not rec.get("est"):
        return None
    so_far = rec.get("so_far") or _so_far(rec)
    for k in KEYS:
        est, used = float(rec["est"].get(k) or 0), so_far.get(k)
        if used is None:
            continue
        if used >= OVER * est and used - est >= OVER_MIN[k]:
            return {"line": k, "used": used, "est": est}
    return None


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
            f"{line}, roughly twice what it was expected to take, so I stopped it before it burns more. It won't start "
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
        if cmd == "when":
            p = Projection.here()
            t = p.fits_at(c, _now()) if p else None
            print("Fits now." if t and t - _now() < 60 else f"Fits around {time.strftime('%a %H:%M', time.localtime(t))}."
                  if t else "No time: no reading, no stop lines, or it never fits.")
        return 0
    if cmd == "backfill":
        filled, left = backfill()
        print(f"Filled the cost of {filled} finished jobs from the saved readings; {left} couldn't be matched.")
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
