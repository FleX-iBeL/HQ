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
  - Planned items (H95, 13 October 2026): an item on the schedule gets a kind when it's planned
    (schedule.py add --kind, from a call, else the guess from its text), kept in schedule-kinds.json, and
    the same estimate as a job of that kind would get. plan() gives each waiting item how long, and when
    it should start and be done: at its time, or later when the job list or the items before it are
    still running. When it becomes a job, its kind goes with it.

  - Per machine (H81, 13 October 2026): every finished job notes the computer that ran it (its name, its
    short name, laptop or server). With a second HQ the two share their history: the routine pulls the other
    one's lines (GET /api/estimates, at most every ten minutes, kept in job-estimates-peer.json). An estimate is
    for the computer that runs the jobs (the main); its own jobs count double, the other computer's count too,
    scaled by how much faster or slower this one has turned out to be for that kind (or, with too few of the
    kind, over all kinds), pulled towards "the same" while there are few to compare. A computer with no
    history yet starts from the other one's, unscaled.
  - Patterns (H81): each finished job also keeps a few tags from the words in its text (internet, files,
    happy flows, finding a cause, research, both computers, the status page, the call). A tag seen on at
    least PATTERN_MIN finished jobs that took clearly longer or shorter than their kind's usual time moves
    the estimate of a new job with that tag, pulled towards nothing while there are few, at most twice or
    half. [The tags and the thresholds are Claude's choice.]

Files, in HQ's .status (never in the repo): job-estimates.json (each job's estimate, set when added,
and when it started) and job-estimates-history.jsonl (one line per finished job: estimate and real).
A test's copy of the roadmap (HQ_ROADMAP) gets its own files next to it, so tests never touch the real ones.

usage:
  python3 routine/estimate.py plan      the estimates as JSON (the status server shows them)
  python3 routine/estimate.py list      the estimates in words (jobs.py list and schedule.py list add them too)
  python3 routine/estimate.py seed      fill the history once from the jobs history (H33) and the job prompts
  python3 routine/estimate.py kind TEXT        the kind kind_of guesses for a text
  python3 routine/estimate.py check-kinds      every finished job: the kind it learned under, next to today's guess (H70)
  python3 routine/estimate.py learned          what the estimates have learned, in words: the computers and the patterns (H81)
  python3 routine/estimate.py pull [--force]   fetch the other HQ's history (the routine does this every minute, at most every ten)
  python3 routine/estimate.py share            this computer's own history as JSON (the status server's GET /api/estimates)
  python3 routine/estimate.py tag              fill in the tags (and this computer) on finished jobs from before H81, from their prompts
"""
import json, math, os, re, statistics, sys, time

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
ITEMS = os.path.join(DIR, "schedule-kinds.json")  # H95: each planned item's kind, set when it's planned
HISTORY = os.path.join(DIR, "job-estimates-history.jsonl")
PEER = os.path.join(DIR, "job-estimates-peer.json")  # H81: the other HQ's history, as it last answered
# The minute-by-minute record of the status server (H33). A test's roadmap copy doesn't read the real one.
SAMPLES = os.environ.get("HQ_ROUTINES_HISTORY") or ("" if _TEST else os.path.join(ROOT, ".status", "routines-history.jsonl"))
BACKFILL = os.path.join(ROOT, ".status", "jobs-backfill.json")
PROMPTS = os.path.join(ROOT, "scratch", "routine")

DEFAULT = 15      # minutes, when nothing has been measured yet
GAP = 1           # minutes between two jobs: the routine looks every minute
RECENT = 8        # how many of the last jobs of a kind count
MIN_KIND = 3      # fewer than this of a kind: the last jobs of any kind count too
OWN = 2           # H81: a job run on the computer the estimate is for counts this many times one from the other
SHRINK = 2        # H81: n compared jobs give a machine factor n/(n+SHRINK) of the way from 1 to what they say
PATTERN_MIN = 4   # H81: finished jobs with a tag before it moves an estimate
PATTERN_SHRINK = 4
PATTERN_CLEAR = 1.2  # H81: a tag moves an estimate only when its jobs took at least this much longer (or shorter)
PULL_EVERY = 600  # H81: seconds between two pulls of the other HQ's history

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
    # H95: the way planned items are worded, "Read the F18 row first and fix it as it says", counts too.
    if re.search(r"^build\b|\bbuild [a-z]\d|\bbuild exactly what\b|\bbuild the\b|^[a-z]\d+\.\d+ on the (hq )?roadmap"
                 r"|\b(build|fix) it as it says\b|\bthen fix it\b", tb):
        return "build"
    return "other"


def kind_given(kind):
    """A kind set by hand (jobs.py add --kind), or None. Unknown words are refused by jobs.py."""
    k = (kind or "").strip().lower()
    return k if k in KINDS else None


# H81: tags from the words in a job's text, for the patterns. The routine's own wording ("Planned on the call of
# ...", "Pull dev first ...", "Only the affected happy flows", "Restart what changed as the last step") is the same
# in every planned item, so it's cut off first; what's left is what the job is about.
TAGS = {
    "internet": (r"\b(download\w*|fetch\w*|web|online|internet|youtube|yt-dlp|search\w*|browser|website|api)\b", "need the internet"),
    "files": (r"\b(transcri\w*|files?|folders?|copy|copies|backup|archive|move them)\b", "work through files"),
    "flows": (r"\bwhole (happy flow )?set\b|\ball (the )?happy flows\b|\bflow \d+", "run happy flows"),
    "cause": (r"\bfind the cause\b|\bwhy\b|\bbug\b|\bbroken\b|\bdoesn'?t work\b|\bfix (it|the)\b", "look for a cause"),
    "research": (r"\bresearch\w*|\blook into\b|\binvestigat\w*|\bcompare\b", "are research"),
    "machines": (r"\b(vps|servers?|laptops?|machines?|computers?|both computers|two computers|sync\w*|main and backup)\b", "touch both computers"),
    "status": (r"\bstatus page\b|\bthe page\b", "change the status page"),
    "call": (r"\b(on a call|call line|voice|calls?)\b", "change the call"),
}


def _about(text):
    """The part of a job's text that says what it's about (H81): without the routine's own wording."""
    t = " ".join((text or "").lower().split())
    t = t.split("follow the hq build notes")[0]
    t = re.sub(r"^.*?the job, as agreed on the call: ", "", t)
    t = re.sub(r"^scheduled item \d+, planned for [^:]*: ", "", t)
    for cut in ("planned on the call of", "pull dev first", "only the affected happy flows", "restart what changed",
                "write the result in its row"):
        t = t.split(cut)[0]
    return t


def tags_of(text):
    t = _about(text)
    return sorted(k for k, (rx, _) in TAGS.items() if re.search(rx, t))


# ---------- the computers (H81) ----------

def me():
    """This computer: {"name", "label", "type"}. name as main and backup know it, label its short name."""
    try:
        import role
        name = role.my_name(role.config())
    except Exception:
        import socket
        name = socket.gethostname().split(".")[0]
    return {"name": name, "label": hqpaths.short_name(), "type": "laptop" if hqpaths.IS_MAC else "server"}


def _peer():
    try:
        return json.load(open(PEER))
    except Exception:
        return {}


def runner():
    """The computer the jobs run on, so the one an estimate is for: this one, or the main when this is the backup."""
    m = me()
    try:
        import role
        if role.acting() == "backup":
            c, p = role.config(), _peer()
            name = c.get("peer_name") or p.get("name")
            if name:
                return {"name": name, "label": p.get("label") or name, "type": p.get("type") or "other"}
    except Exception:
        pass
    return m


def label(name, mine=None, peer=None):
    mine = mine or me()
    peer = _peer() if peer is None else peer
    if name == mine["name"]:
        return mine["label"]
    if name == peer.get("name"):
        return peer.get("label") or name
    return name


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


def all_history():
    """H81: this computer's finished jobs and the other HQ's (as it last answered), each with its machine, oldest
    first. A line from before H81 has no machine: it's the computer whose file it's in."""
    mine, peer = me()["name"], _peer()
    out, seen = [], set()
    for h in history():
        h = {**h, "machine": h.get("machine") or mine}
        out.append(h)
        seen.add((h["machine"], h.get("n")))
    for h in peer.get("lines") or []:
        if not isinstance(h, dict):
            continue
        h = {**h, "machine": h.get("machine") or peer.get("name") or "other"}
        if (h["machine"], h.get("n")) not in seen and h["machine"] != mine:
            out.append(h)
    out.sort(key=lambda h: h.get("done") or 0)  # stable: lines with the same time keep their order
    return out


def share():
    """What GET /api/estimates answers: this computer's own finished jobs, each with its machine."""
    m = me()
    lines = [{**h, "machine": h.get("machine") or m["name"]} for h in history()]
    return {**m, "lines": [h for h in lines if h["machine"] == m["name"]], "at": int(time.time())}


def pull(force=False, log=None):
    """H81: fetch the other HQ's history, at most every PULL_EVERY seconds. Alone (no other HQ): nothing. When
    it can't be reached (or doesn't know /api/estimates yet), what it said last stays."""
    try:
        import role
        c = role.config()
    except Exception:
        return None
    if not c:
        return None
    p = _peer()
    if not force and time.time() - max(p.get("at", 0), p.get("tried", 0)) < PULL_EVERY:
        return None
    try:
        code, d = role._request(c["peer"].rstrip("/") + "/api/estimates")
        ok = code == 200 and isinstance(d, dict) and isinstance(d.get("lines"), list) and d.get("name")
    except Exception as e:
        ok, d = False, str(e)
    if ok:
        p = {"name": d["name"], "label": d.get("label") or d["name"], "type": d.get("type") or "other",
             "lines": d["lines"], "at": int(time.time())}
    else:
        p = {**p, "tried": int(time.time()), "error": str(d)[:200]}
    os.makedirs(DIR, exist_ok=True)
    tmp = PEER + ".tmp"
    json.dump(p, open(tmp, "w"))
    os.replace(tmp, PEER)
    if log and ok:
        log(f"estimates: {len(p['lines'])} finished jobs from {p['label']}")
    return ok


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


def _wmedian(pairs):
    """Weighted median of (value, weight) pairs."""
    pairs = sorted(pairs)
    half = sum(w for _, w in pairs) / 2
    acc = 0
    for v, w in pairs:
        acc += w
        if acc >= half:
            return v
    return pairs[-1][0]


def _real(hist):
    return [h for h in hist if isinstance(h.get("actual"), (int, float)) and h["actual"] > 0]


def _ratios(real, a, b, kind=None):
    """H81: log(how long a job on a took / the usual time of its kind on b), one per job of a whose kind b has
    at least two of."""
    usual = {}
    for h in real:
        if h["machine"] == b:
            usual.setdefault(h.get("kind"), []).append(h["actual"])
    return [math.log(h["actual"] / statistics.median(usual[h.get("kind")])) for h in real
            if h["machine"] == a and (kind is None or h.get("kind") == kind) and len(usual.get(h.get("kind"), [])) >= 2]


def factor(real, a, b, kind=None):
    """H81: (how many times as long a takes as b, how many jobs it's based on), for kind: its own kind's jobs
    when there are MIN_KIND of them, else all kinds; pulled towards 1 while there are few. 1 with nothing to
    compare (a computer with no history yet starts from the other one's, unscaled)."""
    if a == b:
        return 1.0, 0
    rs = _ratios(real, a, b, kind) if kind else []
    if len(rs) < MIN_KIND:
        rs = _ratios(real, a, b)
    if not rs:
        # Nothing of a to compare: the other way round, if b has jobs of kinds a has two of.
        back = _ratios(real, b, a)
        if not back:
            return 1.0, 0
        n = len(back)
        return math.exp(-statistics.mean(back) * n / (n + SHRINK)), n
    n = len(rs)
    return math.exp(statistics.mean(rs) * n / (n + SHRINK)), n


def patterns(real):
    """H81: {tag: (how many times as long its jobs took as their kind's usual time, how many)}, for the tags
    seen on at least PATTERN_MIN finished jobs, pulled towards 1 while there are few, at most twice or half.
    The usual time is the median of that kind on that computer, so the computers don't count as a pattern."""
    usual = {}
    for h in real:
        usual.setdefault((h["machine"], h.get("kind")), []).append(h["actual"])
    res = {}
    for h in real:
        if not isinstance(h.get("tags"), list):
            continue
        u = usual[(h["machine"], h.get("kind"))]
        if len(u) < 2:
            continue
        r = math.log(h["actual"] / statistics.median(u))
        res.setdefault("", []).append(r)
        for t in h["tags"]:
            res.setdefault(t, []).append(r)
    base = statistics.mean(res.pop("", [0])) if res else 0
    out = {}
    for t, rs in res.items():
        n = len(rs)
        if n < PATTERN_MIN:
            continue
        x = (statistics.mean(rs) - base) * n / (n + PATTERN_SHRINK)
        x = max(-math.log(2), min(math.log(2), x))
        out[t] = (math.exp(x), n)
    return out


def estimate_detail(text, hist=None, kind=None, machine=None):
    """H81: the estimate with how it came about: {"est", "kind", "based", "machine", "own", "other", "scaled",
    "tags", "pattern"}. hist: all finished jobs (all_history()); machine: the computer it's for (runner())."""
    hist = all_history() if hist is None else hist
    kind = kind_given(kind) or kind_of(text)
    machine = machine or runner()["name"]
    real = [{**h, "machine": h.get("machine") or machine} for h in _real(hist)]
    scale = {}

    def scaled(h, k):
        if h["machine"] == machine:
            return h["actual"]
        key = (h["machine"], k)
        if key not in scale:
            scale[key] = factor(real, machine, h["machine"], k)[0]
        return h["actual"] * scale[key]

    own = [h for h in real if h.get("kind") == kind and h["machine"] == machine][-RECENT:]
    other = [h for h in real if h.get("kind") == kind and h["machine"] != machine][-RECENT:]
    if len(own) >= RECENT:
        other = []
    same = sorted(own + other, key=lambda h: h.get("done") or 0)
    if len(same) >= MIN_KIND:
        # The newest counts most; a job on this computer counts OWN times one from the other.
        est = _wmedian([(scaled(h, kind), (i + 1) * (OWN if h["machine"] == machine else 1)) for i, h in enumerate(same)])
        based = len(same)
    elif not real:
        est, based = DEFAULT, 0
    else:
        # Few of its own kind: they count double next to the last jobs of any kind (the others scaled over all kinds).
        values = [scaled(h, None) for h in real[-RECENT:]] + [scaled(h, None) for h in same] * 2
        est = _weighted_median(values)
        based = len(same) + len(real[-RECENT:])
    tags = tags_of(text)
    pat = patterns(real)
    hit = [pat[t][0] for t in tags if t in pat and (pat[t][0] >= PATTERN_CLEAR or pat[t][0] <= 1 / PATTERN_CLEAR)]
    mult = math.exp(statistics.mean(math.log(x) for x in hit)) if hit else 1.0
    return {"est": max(1, round(est * mult)), "kind": kind, "based": based, "machine": machine,
            "own": len(own), "other": len(other), "tags": tags, "pattern": round(mult, 2)}


def estimate_for(text, hist=None, kind=None, machine=None):
    """(minutes, kind, how many past jobs it's based on). A kind given by hand wins over the guess (H70)."""
    d = estimate_detail(text, hist, kind, machine)
    return d["est"], d["kind"], d["based"]


# ---------- called by jobs.py (inside its lock) ----------

def on_add(n, text, kind=None, by_hand=None):
    """kind: set by hand (jobs.py add --kind); it's stored here and goes into the history when the job
    finishes, so a hand-set kind learns in the right pile (H70). by_hand: False for a kind that was a
    guess made earlier (a planned item's, H95), so it isn't marked as set by hand."""
    st = _load_state()
    d = estimate_detail(text, kind=kind)
    st[str(n)] = {"est": d["est"], "kind": d["kind"], "based": d["based"], "set": int(time.time()), "machine": d["machine"]}
    if kind_given(kind) and by_hand is not False:
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
        e = {"est": None, "kind": kind_of(text)}
    now = time.time()
    seen = _minutes_seen(n)
    started = e.get("started") or _from_hhmm(started_hhmm, now)
    wall = round((now - started) / 60) if started else None
    actual = seen if seen else wall
    if actual is None:
        return None
    m = me()  # H81: the computer that ran it, and the tags from its words for the patterns
    rec = {"n": n, "kind": e.get("kind") or kind_of(text), "est": e.get("est"), "actual": max(1, actual),
           "done": int(now), "how": "seen" if seen else "clock", "machine": m["name"], "label": m["label"],
           "type": m["type"], "tags": tags_of(text)}
    _append(rec)
    st.pop(str(n), None)
    _save_state(st)
    return rec


# ---------- planned items (H95), called by schedule.py (inside the queue's lock) ----------

def _load_items():
    try:
        return json.load(open(ITEMS))
    except Exception:
        return {}


def _save_items(d):
    os.makedirs(DIR, exist_ok=True)
    tmp = ITEMS + ".tmp"
    json.dump(d, open(tmp, "w"), indent=1)
    os.replace(tmp, ITEMS)


def item_kind(n, text=""):
    """(kind, set by hand) of planned item n: the kind given when it was planned, else the guess."""
    e = _load_items().get(str(n)) or {}
    k = kind_given(e.get("kind"))
    return (k, bool(e.get("by_hand"))) if k else (kind_of(text), False)


def item_on_add(n, text, kind=None):
    """A planned item's kind, set when it's planned: given by the call (schedule.py add --kind), else guessed."""
    d = _load_items()
    d[str(n)] = {"kind": kind_given(kind) or kind_of(text), "set": int(time.time())}
    if kind_given(kind):
        d[str(n)]["by_hand"] = True
    _save_items(d)
    return d[str(n)]


def item_on_job(n, text, job_n, job_text):
    """The item became job job_n: its kind goes with it (the job's own text starts with "Scheduled item ...",
    which would spoil the guess), and the item's line here is no longer needed."""
    kind, by_hand = item_kind(n, text)
    e = on_add(job_n, job_text, kind, by_hand)
    item_forget(n)
    return e


def item_forget(n):
    d = _load_items()
    if d.pop(str(n), None) is not None:
        _save_items(d)


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
    hist = all_history()
    run = runner()
    out = {"now": int(now), "on": on, "jobs": {}, "total": None, "accuracy": accuracy(history()), "kinds": KINDS,
           "machine": run["label"], "learned": learned(hist, run)}
    for h in hist[-30:]:
        out["jobs"][str(h["n"])] = {"finished": True, "est": h.get("est"), "actual": h["actual"], "kind": h.get("kind")}
    samples = None
    cursor, left_total, waits = now, 0, not on
    running = [j for j in js if j["state"].startswith(("running", "stop asked"))]
    for j in running:
        e = st.get(str(j["n"])) or {}
        est = e.get("est") or estimate_for(j["text"], hist, machine=run["name"])[0]
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
    run_end = cursor  # H99: when the running job should be done; a priority item can start from there
    line = [j for j in js if j["state"] == "ready" or j["state"].startswith("held")]
    for j in line:
        e = st.get(str(j["n"])) or {}
        est = e.get("est")
        kind = e.get("kind")
        if not est:
            est, kind, _ = estimate_for(j["text"], hist, machine=run["name"])
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
    out["items"] = _plan_items(cursor, waits, on, hist, run, run_end)
    out["items_total"] = _items_total(out["items"], waits, on)
    return out


def _items_total(items, waits, on):
    """H107: all planned items together, like the job list's total: how long they take together, and when
    the last one should be done (the job list goes first, so its time is already in each item's)."""
    if not items:
        return None
    t = {"items": len(items), "minutes": round(sum(e["est"] for e in items.values())), "eta": None, "waits": None}
    if waits or not on:
        t["waits"] = "off" if not on else "usage"
    elif all(e.get("eta") for e in items.values()):
        t["eta"] = max(e["eta"] for e in items.values())
    return t


def _schedule():
    try:
        import schedule as sc
        import jobs as q
        return sc.read(open(q.ROADMAP, encoding="utf8").read())
    except Exception:
        return []


def _plan_items(cursor, waits, on, hist, run, run_end=None):
    """H95: each waiting planned item, soonest first: how long, and when it should start and be done. It
    starts at its time, or once the job list and the items before it are done (the job list goes first);
    the routine looks every minute. Waiting on the usage or the routine off: no times, only how long.
    H99: an item with the priority tag starts at its time, or once the running job and the tagged items
    before it are done, ahead of the waiting jobs; a tagged item that cuts in makes the job list (and so
    the other items) end that much later."""
    import datetime as dt
    items = sorted((i for i in _schedule() if i["state"] == "waiting"),
                   key=lambda i: (not i.get("priority"), i["at"], i["n"]))
    out = {}
    pcursor = cursor if run_end is None else run_end
    for i in items:
        kind, by_hand = item_kind(i["n"], i["text"])
        est, kind, _ = estimate_for(i["text"], hist, kind, run["name"])
        e = {"est": est, "kind": kind, "start": None, "eta": None, "waits": None}
        if by_hand:
            e["by_hand"] = True
        if i.get("priority"):
            e["priority"] = True
        if waits or not on:
            e["waits"] = "off" if not on else "usage"
        else:
            at = dt.datetime.strptime(i["at"], "%Y-%m-%d %H:%M").timestamp()
            if i.get("priority"):  # H99: from when the running job is done, not the whole job list
                start = max(at, pcursor) + GAP * 60
                pcursor = start + est * 60
                if start < cursor:  # it cuts in ahead of the waiting jobs
                    cursor += (est + GAP) * 60
                e["start"], e["eta"] = int(start), int(pcursor)
            else:
                start = max(at, cursor) + GAP * 60  # cursor: now, or when the job list should be done
                cursor = start + est * 60
                e["start"], e["eta"] = int(start), int(cursor)
            e["later"] = start - at > 5 * 60  # starts later than planned: the job list or earlier items first
        out[str(i["n"])] = e
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


def item_words(n, p):
    """H95: a planned item's estimate in words, for schedule.py list and a call."""
    e = (p.get("items") or {}).get(str(n))
    if not e:
        return ""
    s = f"about {dur(e['est'])}"
    if e.get("eta"):
        day = lambda t: "" if time.strftime("%Y-%m-%d", time.localtime(t)) == time.strftime("%Y-%m-%d", time.localtime(p["now"])) \
            else time.strftime("%A ", time.localtime(t))
        if e.get("later"):
            s += f", starts around {day(e['start'])}{hhmm(e['start'])} (after the work before it)"
        s += f", done around {day(e['eta'])}{hhmm(e['eta'])}"
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


def items_total_words(p):
    """H107: the planned items' total in words, for schedule.py list and a call."""
    t = p.get("items_total")
    if not t:
        return ""
    s = f"All {t['items']} planned item{'s' if t['items'] != 1 else ''}: about {dur(t['minutes'])}"
    if t.get("eta"):
        day = "" if time.strftime("%Y-%m-%d", time.localtime(t["eta"])) == time.strftime("%Y-%m-%d", time.localtime(p["now"])) \
            else time.strftime("%A ", time.localtime(t["eta"]))
        s += f", all done around {day}{hhmm(t['eta'])}, after the job list"
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


def times(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")


def learned(hist=None, run=None):
    """H81: what the estimates have learned, in plain sentences: which computer they're for, how many finished
    jobs each computer gave, how much faster or slower one is than the other, and the patterns."""
    hist = all_history() if hist is None else hist
    run = run or runner()
    real = _real(hist)
    if not real:
        return []
    mine, peer = me(), _peer()
    count = {}
    for h in real:
        count[h["machine"]] = count.get(h["machine"], 0) + 1
    others = [m for m in count if m != run["name"]]
    here = count.get(run["name"], 0)
    s = f"Estimates are for the {run['label']}, from {here} finished job{'s' if here != 1 else ''} there"
    if others:
        s += "".join(f" and {count[o]} on the {label(o, mine, peer)}" for o in others)
    out = [s + "."]
    for o in others:
        f, n = factor(real, run["name"], o)
        if n and abs(math.log(f)) >= math.log(1.1):
            out.append(f"The {run['label']} takes about {times(f)} times as long as the {label(o, mine, peer)} "
                       f"(from {n} job{'s' if n != 1 else ''} of the same kinds); the {label(o, mine, peer)}'s jobs count scaled.")
        elif n:
            out.append(f"The {run['label']} and the {label(o, mine, peer)} take about as long (from {n} job{'s' if n != 1 else ''}).")
        else:
            out.append(f"Nothing to compare the {run['label']} with the {label(o, mine, peer)} yet; "
                       f"the {label(o, mine, peer)}'s jobs count as they are.")
    for t, (f, n) in sorted(patterns(real).items(), key=lambda x: -abs(math.log(x[1][0]))):
        if f >= PATTERN_CLEAR:
            out.append(f"Jobs that {TAGS[t][1]} take about {times(f)} times as long as usual for their kind ({n} jobs).")
        elif f <= 1 / PATTERN_CLEAR:
            out.append(f"Jobs that {TAGS[t][1]} take about {times(f)} times as long as usual for their kind ({n} jobs).")
    return out


def tag():
    """H81: this computer's finished jobs from before H81 get their machine and their tags, from the job
    prompts the routine saved. Nothing else in a line changes."""
    js, _ = _queue()
    texts = {j["n"]: j["text"] for j in js}
    m = me()
    lines, changed = history(), 0
    for h in lines:
        if "machine" not in h:
            h.update(machine=m["name"], label=m["label"], type=m["type"])
            changed += 1
        text = texts.get(h["n"], "")
        pf = os.path.join(PROMPTS, f"job-{h['n']}.prompt")
        if not text and os.path.exists(pf):
            text = open(pf, encoding="utf8").read()
            i = text.find("The job, as agreed on the call:")
            text = text[i:] if i >= 0 else text
        if text and h.get("tags") != tags_of(text):  # the tags follow from the text, so they're always made again
            h["tags"] = tags_of(text)
            changed += 1
    if changed:
        os.makedirs(DIR, exist_ok=True)
        tmp = HISTORY + ".tmp"
        with open(tmp, "w", encoding="utf8") as f:
            f.writelines(json.dumps(h) + "\n" for h in lines)
        os.replace(tmp, HISTORY)
    print(f"{sum(1 for h in lines if 'tags' in h)} of {len(lines)} finished jobs have tags; all have their computer.")


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
        for l in p.get("learned") or []:
            print(l)
    elif cmd == "seed":
        seed()
    elif cmd == "kind":
        print(kind_of(" ".join(argv[1:])))
    elif cmd == "check-kinds":
        check_kinds()
    elif cmd == "learned":
        print("\n".join(learned()) or "No finished jobs yet.")
    elif cmd == "share":
        print(json.dumps(share()))
    elif cmd == "pull":
        r = pull(force="--force" in argv)
        print({None: "Not pulled: no other HQ, or pulled less than ten minutes ago.", True: "Pulled the other HQ's finished jobs.",
               False: "The other HQ couldn't be asked; what it said last stays."}[r])
    elif cmd == "tag":
        tag()
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
