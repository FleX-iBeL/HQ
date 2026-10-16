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
    (usage line), and everything after it, waits on the usage. H109 (13 October 2026): it still gets its
    "done around" time as if the usage allowed it, with waits "usage", so the page and a call say it will
    be later because of the usage limit. Only with the routine off there are no times.
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

  - F34 (14 October 2026), after every waiting job showed about a minute. The cause: a computer that didn't hold a
    job's kind (the backup, or one that took over as main) guessed it from the words, builds worded "Build: ..." or
    "build a first version" fell into other, and other had become mostly one-minute merge jobs. Now: merges and
    releases are kinds of their own (the wording says them for sure, also over a kind given by hand), builds are read
    from more wording (a happy flow to add or run, a push to dev, "fix it so"), the open jobs' kinds go to the other
    HQ with its finished jobs (share "open", known()), and a waiting job is estimated again every time from the newest
    finished jobs (job_estimate; the estimate it starts with is the one checked). Only jobs whose time was measured
    when they finished count (not the seeded ones). Every finished job from job 1 was retagged from its text (the
    queue, the prompts, the roadmap's saved versions in git; retag), and estimated back from the jobs before it
    (backtest). What really tells the time is the kind and the computer; the tags move it little.

  - H166 (16 October 2026), after F34 showed builds vary from 2 to 23 minutes, all estimated alike. In the user's words:
    "Okay, so is there a better way to make these estimations?" A job is now also estimated from the finished jobs
    most like it in what the work is: its words (without the routine's own wording and the quotes), the H/F row it
    builds, and the parts of HQ it names (PARTS: the calendar, the call page, the status page, the weather, the sync,
    Donna's line ...). Each finished line keeps its words ("about"); TF-IDF over the measured finished jobs, cosine
    alike, the SIMILAR most alike above SIM_MIN, same kind counting SIM_KIND times, the other computer's scaled as
    before. Their weighted median (by alike^SIM_POW, in log minutes) pulls the kind's estimate towards it, as far as
    their weight lets it (SIM_TRUST); fewer than two similar jobs, or no words: the kind's estimate as before. Only jobs
    with a measured time count. Checked with backtest against the kind's estimate alone. [The numbers are Claude's
    choice, from estimating the finished jobs back.]

  - H167 (16 October 2026), same call: "put all three of them on the roadmap and give it to the team". A quick look at
    the work when it's added or planned gives it a size (look): how many parts of HQ it and its roadmap row name, how
    many happy flows it names or adds, whether it restarts the call line, research or a clear fix, and how many words.
    Each finished job is estimated back once from the jobs before it (kept in job-estimates-backs.json); how far each
    was off, against its size, gives weights (ridge regression, SIZE_RIDGE), and a new job's estimate moves by what
    its size says, at most twice or half, once SIZE_MIN finished jobs have a back estimate. The look reads the words
    only, no Claude: Haiku (claude -p, no tools) was tried on all 141 finished jobs and wasn't closer (about $0.0004 and
    4 seconds a job); look --haiku keeps that comparison at hand. [The features and numbers are Claude's choice.]

  - H168 (16 October 2026), same call: "put all three of them on the roadmap and give it to the team". At its start, after
    reading its row, each job writes down its own guess of how many minutes it will take (jobs.py guess N MINUTES; the
    job prompt and the build notes say to). It's kept with the job (job-estimates.json: guess, guess_at) and, at done,
    next to the computed estimate and the real time on its finished line. The page and jobs.py list show the team's
    guess next to the computed estimate. Once GUESS_MIN finished jobs have a guess (guess_fit), how far the guesses and
    the computed estimates were off decides how much a running job's estimate takes the guess in: the guess corrected
    by how long or short the guesses run (their median ratio, at most three times), weighed against the computed one
    by how close each was (in log minutes), pulled towards the computed one while there are few. The computed estimate
    on the finished line stays what it was, so the backtest compares like with like; with_guess is kept next to it.

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
  python3 routine/estimate.py retag            every finished job's kind and tags again, from its text (F34; the routine does it once per RETAG)
  python3 routine/estimate.py backtest         every measured finished job estimated back from the jobs before it: how close (F34),
                                               from the most similar jobs (H166) next to the kind alone (before H166)
  python3 routine/estimate.py reestimate       every waiting job's stored estimate made again now (H166)
  python3 routine/estimate.py similar TEXT     the finished jobs most like a text, and the estimate they give (H166)
  python3 routine/estimate.py guesses          the team's own guesses (H168): how far off they were, next to the computed
                                               estimates, and how much a running job's estimate takes the guess in
  python3 routine/estimate.py look TEXT [--haiku]  the quick look at a job's size (H167); --haiku asks Haiku as well, with
                                               what that costs (only to compare: the estimates use the look without Claude)
"""
import functools, json, math, os, re, statistics, sys, time

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
RETAGS = os.path.join(DIR, "job-estimates-retag.json")  # F34: kinds and tags for the other HQ's lines, until it retags

DEFAULT = 15      # minutes, when nothing has been measured yet
GAP = 1           # minutes between two jobs: the routine looks every minute
RECENT = 12       # how many of the last jobs of a kind count (F34: 12, from estimating the finished jobs back)
MIN_KIND = 3      # fewer than this of a kind: the last jobs of any kind count too
OWN = 2           # H81: a job run on the computer the estimate is for counts this many times one from the other
SHRINK = 2        # H81: n compared jobs give a machine factor n/(n+SHRINK) of the way from 1 to what they say
PATTERN_MIN = 4   # H81: finished jobs with a tag before it moves an estimate
PATTERN_SHRINK = 4
PATTERN_CLEAR = 1.2  # H81: a tag moves an estimate only when its jobs took at least this much longer (or shorter)
PULL_EVERY = 120  # H81: seconds between two pulls of the other HQ's history (F34: 2 minutes, for the open jobs' kinds)
RETAG = 2         # F34: the version of the kinds and tags; a finished line with an older one is retagged (2: H166's words)
SIMILAR = 8       # H166: how many of the most similar finished jobs count
SIM_MIN = 0.1     # H166: less alike than this (0 to 1) doesn't count as similar
SIM_POW = 2       # H166: a job twice as alike counts four times as much
SIM_KIND = 2      # H166: a similar job of the same kind counts this many times as alike
SIM_TRUST = 0.5   # H166: how far the similar jobs pull away from the kind's estimate: their weight / (weight + this)
ABOUT_MAX = 1500  # H166: characters of a job's words kept with its finished line
SIZE_MIN = 20     # H167: finished jobs (with an estimate from the jobs before them) before the size moves an estimate
SIZE_RIDGE = 2    # H167: how hard the size's weights are pulled towards nothing (ridge), from estimating the jobs back
BACKS = os.path.join(DIR, "job-estimates-backs.json")  # H167: each finished job's estimate from the jobs before it
GUESS_MIN = 5     # H168: finished jobs with the team's own guess before the guesses move a running job's estimate
GUESS_SHRINK = 5  # H168: n guessed jobs trust the guess n/(n+GUESS_SHRINK) of the way its record says
GUESS_MAX = 600   # H168: minutes; a guess above this is a slip

KINDS = {
    "transcribe": "transcribing",
    "big": "a big change (whole set of happy flows)",
    "call": "a change to the call (line restarts)",
    "build": "a build",
    "release": "a release",            # F34: a few minutes, nothing built
    "merge": "merging a sync conflict",  # F34: a minute or two; kept apart so they don't pull other kinds down
    "other": "other",
}
# F34: a kind set by hand (a call's --kind) wins over the guess, except over these two: the routine's own
# wording says them for sure, and a call has no word for a merge.
SURE = ("merge", "release")


def _sure(t):
    """F34: the kinds the wording tells for sure: the routine's merge jobs and a release of HQ."""
    if re.search(r"^sync conflict|\bsync conflict \(h56\.4\), found by the routine\b", t):
        return "merge"
    if re.search(r"(^|: )(do |build )?release hq \d|^h\d+ on the (hq )?roadmap: release hq \d", t):
        return "release"
    return None


def kind_of(text):
    """The kind of job, from the words the call wrote in it (Claude's choice, H61)."""
    t = " ".join(text.lower().split())
    t = t.split("follow the hq build notes")[0].split("follow the jarvis va build notes")[0]
    t = re.sub(r"^.*?the job, as agreed on the call: ", "", t)
    t = re.sub(r"^scheduled item \d+, planned for [^:]*: ", "", t)
    sure = _sure(t)
    if sure:
        return sure
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
    # F34: a job that changes HQ's code says so in how it ends: "Build: ...", "build a first version", "fix it
    # so ...", a happy flow to add or run, a push to dev. Before, these fell into other, next to the merges.
    if re.search(r"\bbuild(:| a | it\b| this\b| them\b)|\bfix (it|this|that|them) so\b|\badd (a|one|the) (new )?happy flow"
                 r"|\bhappy flows? for it\b|\brun (happy flow|the affected|flows? \d)|\bpush (to dev|with push\.py)", tb):
        return "build"
    return "other"


def kind_given(kind):
    """A kind set by hand (jobs.py add --kind), or None. Unknown words are refused by jobs.py."""
    k = (kind or "").strip().lower()
    return k if k in KINDS else None


def kind_for(text, kind=None):
    """F34: the kind a job learns and is estimated under: one set by hand wins over the guess, except when the
    wording says a merge or a release for sure."""
    guess = kind_of(text)
    if guess in SURE:
        return guess
    return kind_given(kind) or guess


# H81: tags from the words in a job's text, for the patterns. The routine's own wording ("Planned on the call of
# ...", "Pull dev first ...", "Only the affected happy flows", "Restart what changed as the last step") is the same
# in every planned item, so it's cut off first; what's left is what the job is about.
TAGS = {
    # F34 (14 October 2026): made again from every finished job since job 1. The broad "machines" and "call" tags
    # were on nearly every job (the VPS and calls are named everywhere), so they told nothing; these are narrower.
    "internet": (r"\b(download\w*|fetch\w*|web|online|internet|youtube|yt-dlp|website|api|github)\b", "need the internet"),
    "files": (r"\b(transcri\w*|files?|folders?|copy|copies|archive|move them)\b", "work through files"),
    "flows": (r"\bwhole (happy flow )?set\b|\ball (the )?happy flows\b", "run the whole set of happy flows"),
    "newflow": (r"\badd (a|one|the) (new )?happy flow|\bhappy flows? for it\b|\bnew happy flow\b", "add a happy flow"),
    "cause": (r"\bfind (the cause|why|where|out why)\b|\binvestigat\w*|\bwhy\b|\bbug\b|\bdoesn'?t work\b|\bbroken\b",
              "look for a cause"),
    "research": (r"\bresearch\w*|\blook into\b|\bcompare\b", "are research"),
    "computers": (r"\b(both computers|two computers|main and backup|takes? over|takeover|pairing|heartbeats?|hand(s|ing)? back)\b"
                  r"|\bthe laptop and the vps\b|\bon the laptop\b", "touch both computers"),
    "status": (r"\bstatus page\b", "change the status page"),
    "callpage": (r"\bcall page\b|\bphone version\b|\b(mac|desktop) app\b|\bin settings\b|\bbutton\b|\bsheet\b|\bwidget\b",
                 "change the call page"),
    "agents": (r"\b(pepper|donna|moneypenny|agents?)\b", "change what the agents say or do"),
    "texts": (r"\bdirect line\b|\btexts?\b", "touch Donna's texts"),
    "calendar": (r"\bcalendar\b", "touch the calendar"),
    "usage": (r"\busage\b", "touch the usage lines"),
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


# ---------- similar jobs (H166) ----------

# The parts of HQ a job can name, for finding the jobs most like it (only for that: the patterns keep TAGS).
PARTS = {
    **{k: rx for k, (rx, _) in TAGS.items()},
    "weather": r"\bweather\b|\bforecast\b|\brain\b",
    "sync": r"\bsync\w*\b|\bmain and backup\b|\bthe other hq\b",
    "queue": r"\bqueue\b|\bthe team\b|\bjobs?\.py\b|\bscheduler?\b|\bplanned items?\b|\bestimat\w*",
    "mail": r"\bmail\b|\bgmail\b|\binbox\b",
    "listen": r"\blisten\w*|\bwhisper\b|\btranscription\b|\bvoice\b|\bkokoro\b|\bspeech\b",
    "install": r"\binstall\w*|\brelease\b|\bupdate button\b",
}
_STOP = set("""a an the and or of to in on at for with from by as is are be it its this that these those not no do does did
done so then than when what which who how if else but into out up down over about after before only also just all any each
every one two three first last new more most other same such very can could would should will may might must he she they we
you i me my our his her them their there here was were has have had been being yes call october read row rows pepper hq
roadmap job words quote said asked typed""".split())


@functools.lru_cache(maxsize=4096)
def _words_cached(about):
    return tuple(_count(about).items())


def _words(about):
    return dict(_words_cached(about or ""))


def _count(about):
    """H166: what a job is about, as counts: its words (cut to six letters, so builds and building meet), the rows it
    names (#h154), and the parts of HQ it names (@calendar). Quotes are left out: they say the same thing loosely."""
    about = (about or "").lower()
    t = re.sub(r"'[^']*'|\"[^\"]*\"", " ", about)
    out = {}
    for w in re.findall(r"[a-z][a-z0-9]+", t):
        if len(w) > 2 and w not in _STOP and not re.match(r"[hfmlj]\d+$", w):
            out[w[:6]] = out.get(w[:6], 0) + 1
    for r in set(re.findall(r"\b([hfmlj]\d+)(?:\.\d+)?\b", t)):
        out["#" + r] = out.get("#" + r, 0) + 2
    for k, rx in PARTS.items():
        if re.search(rx, about):
            out["@" + k] = out.get("@" + k, 0) + 2
    return out


def _vector(counts, df, n):
    v = {w: (1 + math.log(c)) * math.log((n + 1) / (df.get(w, 0) + 1)) for w, c in counts.items()}
    size = math.sqrt(sum(x * x for x in v.values())) or 1
    return {w: x / size for w, x in v.items()}


def similar(about, kind, real, scaled=None):
    """H166: the finished jobs most like a job's words: [(alike 0..1, line)], most alike first, at most SIMILAR, only
    from SIM_MIN; a line of the same kind counts SIM_KIND times as alike. real: measured finished lines (with "about")."""
    q = _words(about)
    docs = [(h, _words(h.get("about"))) for h in real if h.get("about")]
    if not q or not docs:
        return []
    df = {}
    for _, d in docs + [(None, q)]:
        for w in d:
            df[w] = df.get(w, 0) + 1
    n = len(docs) + 1
    qv = _vector(q, df, n)
    out = []
    for h, d in docs:
        dv = _vector(d, df, n)
        a = sum(x * dv.get(w, 0) for w, x in qv.items())
        if h.get("kind") == kind:
            a *= SIM_KIND
        out.append((a, h))
    out.sort(key=lambda x: -x[0])
    return [(a, h) for a, h in out[:SIMILAR] if a >= SIM_MIN]


# ---------- the size of the work: a quick look before it starts (H167) ----------

_ROW = re.compile(r"^\| [^|]* \| ([HFMLJ]\d+(?:\.\d+)?) ([^|]*)\|([^|]*)\|([^|]*)\|")
_ROWS = {}


def _rows():
    """{"h167": its title, his words and the goal, lowercased}: the roadmap's rows, without what came of them (the
    last column, written once it's done, would tell the look what it can't know beforehand)."""
    try:
        import jobs as q
        path = q.ROADMAP
        key = (path, os.path.getmtime(path))
    except Exception:
        return {}
    if _ROWS.get("key") != key:
        rows = {}
        try:
            for l in open(path, encoding="utf8"):
                m = _ROW.match(l)
                if m:
                    rows[m.group(1).lower()] = " ".join((m.group(2) + " " + m.group(3) + " " + m.group(4)).lower().split())
        except Exception:
            pass
        _ROWS.clear()
        _ROWS.update(key=key, rows=rows)
    return _ROWS["rows"]


_FLOWS = re.compile(r"happy flows? ((?:\d+(?:,? (?:and )?|\s*))+)|\bflows? ((?:\d+(?:,? (?:and )?|\s*))+)")


def look(about):
    return dict(_look(about or "", _rows_key()))


def _rows_key():
    _rows()
    return _ROWS.get("key")


@functools.lru_cache(maxsize=4096)
def _look(about, _key):
    return tuple(_look_now(about).items())


def _look_now(about):
    """H167: a job's size from its words and its roadmap row, no Claude: {"parts", "flows", "restart", "research", "fix",
    "words"}. parts: the parts of HQ named (PARTS) in either; flows: the happy flows it names, plus one it adds."""
    t = about or ""
    r = re.search(r"\b([hfmlj]\d+(?:\.\d+)?) on the (?:hq )?roadmap|\bread the ([hfmlj]\d+(?:\.\d+)?) row", t)
    row = _rows().get(r.group(1) or r.group(2), "") if r else ""
    both = t + " " + row
    asks = re.sub(r"\b(whether|if) it restarts the call line", " ", both)  # a question about it isn't a restart
    flows = set()
    for m in _FLOWS.finditer(t):
        flows |= set(re.findall(r"\d+", m.group(1) or m.group(2) or ""))
    research = bool(re.search(r"\bresearch|\bmeasure|\bcompare|\btest\b|backtest|\bfind (out|the cause|why)|\binvestigat", t))
    return {"parts": sum(1 for rx in PARTS.values() if re.search(rx, both)),
            "flows": len(flows) + bool(re.search(r"\badd (a|one|the) (new )?happy flow|new happy flow|happy flows? for it", t)),
            "restart": bool(re.search(r"restart\w* (the )?call line", asks)), "research": research,
            "fix": bool(re.search(r"\bfix\b|\bbug\b", t)) and not research, "words": len(t.split())}


def _features(size):
    return [math.log(1 + size.get("parts", 0)), math.log(1 + size.get("flows", 0)), float(bool(size.get("restart"))),
            float(bool(size.get("research"))), float(bool(size.get("fix"))), math.log(1 + size.get("words", 0))]


def _ridge(X, y, lam):
    """Weights w with X·w close to y, pulled towards 0 by lam (X and y centred)."""
    k = len(X[0])
    m = [[sum(x[a] * x[b] for x in X) + (lam if a == b else 0) for b in range(k)] + [sum(x[a] * v for x, v in zip(X, y))]
         for a in range(k)]
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        for r in range(k):
            if r != c and m[c][c]:
                f = m[r][c] / m[c][c]
                m[r] = [a - f * b for a, b in zip(m[r], m[c])]
    return [m[i][k] / m[i][i] if m[i][i] else 0.0 for i in range(k)]


def _size_fit(pairs):
    """H167: from (size, how far off its estimate from the jobs before it was, as log(real/estimate)) of finished jobs,
    what a size says: (weights, mean features, mean off), or None with fewer than SIZE_MIN."""
    if len(pairs) < SIZE_MIN:
        return None
    X = [_features(s) for s, _ in pairs]
    mu = [statistics.mean(c) for c in zip(*X)]
    ym = statistics.mean(r for _, r in pairs)
    w = _ridge([[a - b for a, b in zip(x, mu)] for x in X], [r - ym for _, r in pairs], SIZE_RIDGE)
    return w, mu, ym


def _size_mult(fit, size):
    """How many times the estimate a job of this size takes, by the fit: at most twice or half."""
    if not fit:
        return 1.0
    w, mu = fit[0], fit[1]
    x = sum(a * (b - m) for a, b, m in zip(w, _features(size), mu))
    return math.exp(max(-math.log(2), min(math.log(2), x)))


def _size_of(h):
    return h["size"] if isinstance(h.get("size"), dict) else look(h.get("about") or "")


_FIT = {}


def _size_pairs(hist):
    """H167: (size, log(real / its estimate from the jobs before it)) for every measured finished job. The estimate from
    the jobs before it is made once per job and kept in BACKS (made again when the jobs before it changed: the other
    HQ's lines came in, or a retag)."""
    try:
        backs = json.load(open(BACKS))
    except Exception:
        backs = {}
    changed, out, before = False, [], 0
    for i, h in enumerate(hist):
        if not _real([h]):
            continue
        before += 1
        if before == 1:
            continue
        key = f"{h['machine']}|{h.get('n')}|{h.get('done')}"
        b = backs.get(key)
        if not b or b.get("before") != before - 1 or b.get("retag") != RETAG or "size" not in b:
            d = estimate_detail("", hist[:i], h.get("kind"), h["machine"], h.get("tags") or [], h.get("about") or "",
                                sized=False)
            b = backs[key] = {"est": d["est"], "before": before - 1, "retag": RETAG, "size": _size_of(h)}
            changed = True
        out.append((b["size"], math.log(h["actual"] / b["est"])))
    if changed:
        try:
            os.makedirs(DIR, exist_ok=True)
            json.dump(backs, open(BACKS + ".tmp", "w"))
            os.replace(BACKS + ".tmp", BACKS)
        except Exception:
            pass
    return out


def size_fit(hist):
    """The fit for these finished jobs, made once per set of them."""
    key = (len(hist), hist[-1].get("done") if hist else None, hist[-1].get("machine") if hist else None)
    if _FIT.get("key") != key:
        _FIT.clear()
        _FIT.update(key=key, fit=_size_fit(_size_pairs(hist)))
    return _FIT["fit"]


def look_haiku(about):
    """H167, only to compare: Haiku's look at the same job (claude -p, no tools, no settings): (size or None, cost in
    dollars, seconds)."""
    import subprocess
    t = about or ""
    r = re.search(r"\b([hfmlj]\d+(?:\.\d+)?) on the (?:hq )?roadmap|\bread the ([hfmlj]\d+(?:\.\d+)?) row", t)
    row = _rows().get(r.group(1) or r.group(2), "") if r else ""
    system = ("You size software jobs for an app (a voice call line, a job queue, a status page, a calendar, sync between "
              "two computers). Read the job and its roadmap row. Answer only one line of JSON: {\"parts\": <how many "
              "separate parts of the app it touches>, \"flows\": <how many happy flows (tests) it names, runs or adds>, "
              "\"restart\": <true if it restarts the call line>, \"work\": \"research\"|\"fix\"|\"build\"}")
    t0 = time.time()
    try:
        p = subprocess.run(["claude", "-p", "--model", "haiku", "--output-format", "json", "--tools", "", "--strict-mcp-config",
                            "--setting-sources", "", "--effort", "low", "--system-prompt", system],
                           input="Job: " + t + ("\n\nRoadmap row: " + row[:1500] if row else ""), capture_output=True,
                           text=True, timeout=120, cwd=DIR if os.path.isdir(DIR) else "/")
        d = json.loads(p.stdout)
        a = json.loads(re.search(r"\{.*\}", d.get("result") or "", re.S).group(0))
        size = {"parts": int(a.get("parts") or 0), "flows": int(a.get("flows") or 0), "restart": bool(a.get("restart")),
                "research": a.get("work") == "research", "fix": a.get("work") == "fix", "words": len(t.split())}
        return size, d.get("total_cost_usd"), round(time.time() - t0, 1)
    except Exception:
        return None, None, round(time.time() - t0, 1)


def size_words(size):
    bits = [f"{size['parts']} part{'s' if size['parts'] != 1 else ''} of HQ",
            f"{size['flows']} happy flow{'s' if size['flows'] != 1 else ''}"]
    if size.get("restart"):
        bits.append("restarts the call line")
    bits.append("research" if size.get("research") else "a clear fix" if size.get("fix") else "a build or other")
    return ", ".join(bits) + f", {size['words']} words"


# ---------- the computers (H81) ----------

def me():
    """This computer: {"name", "label", "type"}. name as main and backup know it, label its short name."""
    try:
        import role
        name = role.my_name(role.config())
    except Exception:
        name = hqpaths.host_name()
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
    fix = _retag_map()
    for h in peer.get("lines") or []:
        if not isinstance(h, dict):
            continue
        h = {**h, "machine": h.get("machine") or peer.get("name") or "other"}
        if h.get("retag") != RETAG and f"{h['machine']}|{h.get('n')}" in fix:  # F34: not retagged there yet
            h.update(fix[f"{h['machine']}|{h.get('n')}"])
        if (h["machine"], h.get("n")) not in seen and h["machine"] != mine:
            out.append(h)
    out.sort(key=lambda h: h.get("done") or 0)  # stable: lines with the same time keep their order
    return out


def share():
    """What GET /api/estimates answers: this computer's own finished jobs, each with its machine."""
    m = me()
    lines = [{**h, "machine": h.get("machine") or m["name"]} for h in history()]
    # F34: the open jobs' kinds too (no text), so the other computer estimates a job by the kind it was given
    # here, also when it takes over as main, instead of guessing it again from the words.
    opened = {n: {k: e[k] for k in ("kind", "est", "by_hand", "set", "guess") if k in e} for n, e in _load_state().items()}
    return {**m, "lines": [h for h in lines if h["machine"] == m["name"]], "open": opened, "at": int(time.time())}


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
             "lines": d["lines"], "open": d.get("open") if isinstance(d.get("open"), dict) else {}, "at": int(time.time())}
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
    """The finished jobs the estimates learn from: only the ones whose time to complete was measured when they
    finished (F34: the jobs seeded once from before H61 have their tags and kind, but don't count)."""
    return [h for h in hist if isinstance(h.get("actual"), (int, float)) and h["actual"] > 0 and h.get("how") != "seed"]


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


def estimate_detail(text, hist=None, kind=None, machine=None, tags=None, about=None, alike=True, sized=True, size=None):
    """H81: the estimate with how it came about: {"est", "kind", "based", "machine", "own", "other", "scaled",
    "tags", "pattern", "by_kind", "similar"}. hist: all finished jobs (all_history()); machine: the computer it's for
    (runner()). tags, about: given instead of read from the text (F34, H166: estimating finished jobs back from their
    lines). alike: False gives the kind's estimate alone, as before H166 (backtest). sized: False leaves out the size
    (H167); size: the look given (stored when it was added) instead of made now."""
    hist = all_history() if hist is None else hist
    kind = kind_for(text, kind)
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
    tags = tags_of(text) if tags is None else tags
    pat = patterns(real)
    hit = [pat[t][0] for t in tags if t in pat and (pat[t][0] >= PATTERN_CLEAR or pat[t][0] <= 1 / PATTERN_CLEAR)]
    mult = math.exp(statistics.mean(math.log(x) for x in hit)) if hit else 1.0
    by_kind = max(1, round(est * mult))
    out = {"est": by_kind, "kind": kind, "based": based, "machine": machine, "own": len(own), "other": len(other),
           "tags": tags, "pattern": round(mult, 2), "by_kind": by_kind, "similar": []}
    # H166: the finished jobs most like this one pull the kind's estimate towards how long they took.
    near = similar(_about(text) if about is None else about, kind, real) if alike else []
    if len(near) >= 2:
        pairs = [(math.log(scaled(h, h.get("kind"))), a ** SIM_POW) for a, h in near]
        weight = sum(w for _, w in pairs)
        trust = weight / (weight + SIM_TRUST)
        out["est"] = max(1, round(math.exp(trust * _wmedian(pairs) + (1 - trust) * math.log(by_kind))))
        out["similar"] = [{"n": h.get("n"), "alike": round(a, 2), "actual": h["actual"]} for a, h in near]
    # H167: the size of the work moves it by how far jobs of a size like it were off before.
    if sized and alike:
        size = size if isinstance(size, dict) else look(_about(text) if about is None else about)
        mult = _size_mult(size_fit(hist), size)
        out["by_similar"] = out["est"]
        out["est"] = max(1, round(out["est"] * mult))
        out["size"], out["size_mult"] = size, round(mult, 2)
    return out


def estimate_for(text, hist=None, kind=None, machine=None, size=None):
    """(minutes, kind, how many past jobs it's based on). A kind given by hand wins over the guess (H70)."""
    d = estimate_detail(text, hist, kind, machine, size=size)
    return d["est"], d["kind"], d["based"]


def known(n):
    """F34: what's known of open job n: its line in this computer's job-estimates.json, else the other HQ's (as it
    last answered), where it was added when that one was main. {} when neither has it."""
    e = _load_state().get(str(n))
    if e:
        return e
    return dict((_peer().get("open") or {}).get(str(n)) or {})


def job_estimate(n, text, hist=None, machine=None):
    """F34: a waiting job's estimate now, under the kind it was given (set by hand, or guessed when it was added)
    and from the newest finished jobs, so it follows what the estimates learn while it waits."""
    k = known(n)
    return estimate_detail(text, hist, k.get("kind"), machine, size=k.get("size"))


# ---------- called by jobs.py (inside its lock) ----------

def on_add(n, text, kind=None, by_hand=None):
    """kind: set by hand (jobs.py add --kind); it's stored here and goes into the history when the job
    finishes, so a hand-set kind learns in the right pile (H70). by_hand: False for a kind that was a
    guess made earlier (a planned item's, H95), so it isn't marked as set by hand."""
    st = _load_state()
    t0 = time.time()
    size = look(_about(text))  # H167: the quick look at the work, kept with it (and how long it took, in ms)
    look_ms = round((time.time() - t0) * 1000)
    d = estimate_detail(text, kind=kind, size=size)
    st[str(n)] = {"est": d["est"], "kind": d["kind"], "based": d["based"], "set": int(time.time()), "machine": d["machine"],
                  "size": size, "look_ms": look_ms}
    if kind_given(kind) and by_hand is not False:
        st[str(n)]["by_hand"] = True
    _save_state(st)
    return st[str(n)]


def on_start(n, text=""):
    if str(n) not in _load_state():
        # A job from before H61, added by hand, or added on the other HQ when that one was main: its estimate now,
        # under the kind the other one gave it (F34).
        k = known(n)
        on_add(n, text, k.get("kind"), True if k.get("by_hand") else False)
    st = _load_state()
    e = st[str(n)]
    # F34: the estimate it starts with is made now, from the newest finished jobs; that's the one that's checked
    # against how long it really takes.
    try:
        e["est"] = estimate_detail(text, kind=e.get("kind"), size=e.get("size"))["est"] if text else e.get("est")
    except Exception:
        pass
    e["started"] = int(time.time())
    st[str(n)] = e
    _save_state(st)
    try:  # H172: its usage counted from now, next to its time
        import usagecost
        usagecost.start(n, text)
    except Exception as ex:
        print(f"(the usage count couldn't start: {ex!r})", file=sys.stderr)


def on_guess(n, minutes, text=""):
    """H168: the team's own guess of how many minutes job n takes, written by the job itself at its start. Kept with
    the job's estimate; a second guess replaces the first. Returns the job's line, with the computed estimate now."""
    st = _load_state()
    if str(n) not in st:
        k = known(n)
        on_add(n, text, k.get("kind"), True if k.get("by_hand") else False)
        st = _load_state()
    e = st[str(n)]
    e["guess"], e["guess_at"] = int(minutes), int(time.time())
    st[str(n)] = e
    _save_state(st)
    return e


def guess_fit(hist=None):
    """H168: how far the team's own guesses were off, next to the computed estimates, on the finished jobs that had
    both. {"count", "need", "ready", "guess_off", "est_off", "bias", "weight"}: bias, how many times as long the jobs
    took as guessed (median, at most three times or a third); weight, how much a running job's estimate takes the
    corrected guess in (0 to 1), from how close each was, pulled towards none while there are few."""
    hist = all_history() if hist is None else hist
    pairs = [h for h in _real(hist) if isinstance(h.get("guess"), (int, float)) and h["guess"] > 0
             and isinstance(h.get("est"), (int, float)) and h["est"] > 0]
    out = {"count": len(pairs), "need": GUESS_MIN, "ready": len(pairs) >= GUESS_MIN}
    if not pairs:
        return out
    out["guess_off"] = round(statistics.mean(abs(h["actual"] - h["guess"]) for h in pairs), 1)
    out["est_off"] = round(statistics.mean(abs(h["actual"] - h["est"]) for h in pairs), 1)
    out["longer"] = sum(1 for h in pairs if h["actual"] > h["guess"])
    out["recent"] = [{"n": h.get("n"), "guess": h["guess"], "est": h["est"], "actual": h["actual"]} for h in pairs[-10:]]
    if not out["ready"]:
        return out
    bias = statistics.median(math.log(h["actual"] / h["guess"]) for h in pairs)
    bias = max(-math.log(3), min(math.log(3), bias))
    eg = statistics.mean((math.log(h["actual"]) - math.log(h["guess"]) - bias) ** 2 for h in pairs)
    ec = statistics.mean((math.log(h["actual"]) - math.log(h["est"])) ** 2 for h in pairs)
    w = ec / (ec + eg) if ec + eg > 0 else 0.5
    out["bias"] = round(math.exp(bias), 2)
    out["weight"] = round(w * len(pairs) / (len(pairs) + GUESS_SHRINK), 2)
    return out


def with_guess(est, guess, fit):
    """H168: a running job's estimate with the team's guess taken in, as far as the guesses' record lets it; the
    computed one as it is while there are fewer than GUESS_MIN guessed jobs, or no guess."""
    if not guess or not est or not (fit or {}).get("ready"):
        return est
    w = fit["weight"]
    return max(1, round(math.exp(w * (math.log(guess) + math.log(fit["bias"])) + (1 - w) * math.log(est))))


def guess_words(fit):
    """H168: the team's own guesses in a sentence, for the status page, jobs.py list and a call."""
    if not fit.get("count"):
        return "The team's own guesses: none checked against a finished job yet."
    s = (f"The team's own guesses (last {fit['count']} job{'s' if fit['count'] != 1 else ''} with one) were off by "
         f"{fit['guess_off']:g} min on average; the computed estimates by {fit['est_off']:g}.")
    if not fit["ready"]:
        return s + f" From {fit['need']} guessed jobs on, a running job's estimate takes the guess in."
    pct = round(fit["weight"] * 100)
    corr = "" if abs(fit["bias"] - 1) < 0.05 else f", the guess times {times(fit['bias'])} (the jobs take that much {'longer' if fit['bias'] > 1 else 'less'} than guessed)"
    return s + f" A running job's estimate takes the guess in for {pct}%{corr}."


def on_done(n, text="", started_hhmm=None):
    """Write the job's estimate next to how long it really took. Returns the record."""
    st = _load_state()
    e = st.get(str(n)) or known(n)
    if not e.get("kind"):
        e = {**e, "kind": kind_of(text)}
    now = time.time()
    seen = _minutes_seen(n)
    started = e.get("started") or _from_hhmm(started_hhmm, now)
    wall = round((now - started) / 60) if started else None
    actual = seen if seen else wall
    if actual is None:
        return None
    m = me()  # H81: the computer that ran it, and the tags from its words for the patterns
    rec = {"n": n, "kind": kind_for(text, e.get("kind")), "est": e.get("est"),
           "actual": max(1, actual), "done": int(now), "how": "seen" if seen else "clock", "machine": m["name"],
           "label": m["label"], "type": m["type"], "tags": tags_of(text), "retag": RETAG,
           "size": e.get("size") if isinstance(e.get("size"), dict) else look(_about(text))}  # H167
    if isinstance(e.get("guess"), (int, float)):  # H168: the team's own guess, next to the computed estimate
        rec["guess"] = e["guess"]
        try:
            w = with_guess(rec["est"], e["guess"], guess_fit())
            if w != rec["est"]:
                rec["with_guess"] = w
        except Exception:
            pass
    if _about(text):
        rec["about"] = _about(text)[:ABOUT_MAX]  # H166: its words, so later jobs can find it as similar
    try:  # H172: its real usage next to its time, and the usage it was estimated to take
        import usagecost
        u = usagecost.finish(n, now)
        read = u.get("cost_read") if u and not u["late"] else None
        if not read:  # its start wasn't counted (it ran before this was built): from the saved readings, as a past job
            c = usagecost.cost_between(usagecost.log_readings(), now - rec["actual"] * 60, now)
            read = c if c and all(k in c for k in usagecost.KEYS) else None
        if read:
            rec["cost"], rec["cost_how"] = read, ("read" if u and not u["late"] and u.get("cost_read") else "log")
        if u and u.get("tokens"):  # H173: its own tokens; its cost is those over the rate, the readings kept next to it
            rec["tokens"] = u["tokens"]
            if read:
                rec["cost_read"] = read
            if u.get("how") == "tokens":
                rec["cost"], rec["cost_how"] = u["cost"], "tokens"
        if u and u.get("est_cost"):
            rec["est_cost"] = u["est_cost"]
    except Exception as ex:
        print(f"(the usage count couldn't be read: {ex!r})", file=sys.stderr)
    _append(rec)
    st.pop(str(n), None)
    _save_state(st)
    if rec.get("tokens"):  # H173: the rate learns from every finished job with its own tokens
        try:
            import usagecost
            usagecost.learn()
        except Exception as ex:
            print(f"(the usage rate couldn't be learned: {ex!r})", file=sys.stderr)
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
    d[str(n)] = {"kind": kind_given(kind) or kind_of(text), "set": int(time.time()), "size": look(_about(text))}  # H167
    if kind_given(kind):
        d[str(n)]["by_hand"] = True
    _save_items(d)
    return d[str(n)]


def item_on_job(n, text, job_n, job_text):
    """The item became job job_n: its kind goes with it (the job's own text starts with "Scheduled item ...",
    which would spoil the guess), and the item's line here is no longer needed."""
    kind, by_hand = item_kind(n, text)
    e = on_add(job_n, job_text, kind, by_hand)
    size = (_load_items().get(str(n)) or {}).get("size") or look(_about(text))  # H167: the item's own words, not "Scheduled item ..."
    st = _load_state()
    if str(job_n) in st:
        st[str(job_n)]["size"] = size
        _save_state(st)
        e = st[str(job_n)]
    item_forget(n)
    return e


def item_repeat(n, k, text):
    """H171: repeating item n became a job and planned its next one, item k: the same kind (also set by hand)
    and size go with it, so the next one's estimate is the same work's."""
    d = _load_items()
    e = dict(d.get(str(n)) or {})
    if not e:
        return item_on_add(k, text)
    e["set"] = int(time.time())
    d[str(k)] = e
    _save_items(d)
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
    gfit = guess_fit(hist)  # H168
    out = {"now": int(now), "on": on, "jobs": {}, "total": None, "accuracy": accuracy(history()), "kinds": KINDS,
           "machine": run["label"], "learned": learned(hist, run), "guesses": {**gfit, "words": guess_words(gfit)}}
    for h in hist[-30:]:
        out["jobs"][str(h["n"])] = {"finished": True, "est": h.get("est"), "actual": h["actual"], "kind": h.get("kind"),
                                    **({"cost": h["cost"]} if isinstance(h.get("cost"), dict) else {}),  # H172
                                    **({"guess": h["guess"]} if isinstance(h.get("guess"), (int, float)) else {})}  # H168
    samples = None
    cursor, left_total, waits = now, 0, not on
    # H172: the usage each piece of work should take, and when it fits under the stop lines (the reading now, the
    # moving lines, the resets and the work before it). No reading or no stop lines: the times as before.
    proj, U = None, None
    try:
        import usagecost as U
        proj = U.Projection.here(now) if on else None
        counts = U._load()
    except Exception:
        counts = {}
    held_wait = False
    # H174: what the total counts, part by part, so it adds up with the per-job lines.
    parts = {"running_min": 0, "waiting_min": 0, "gaps": 0, "held": 0, "guess_in": False, "five": 0.0, "weekly": 0.0}
    running = [j for j in js if j["state"].startswith(("running", "stop asked"))]
    for j in running:
        e = st.get(str(j["n"])) or known(j["n"])
        est = e.get("est") or job_estimate(j["n"], j["text"], hist, run["name"])["est"]
        computed, guess = est, e.get("guess")
        est = with_guess(est, guess, gfit)  # H168: the team's own guess taken in, once the guesses have a record
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
        parts["running_min"] += nxt
        parts["guess_in"] |= bool(guess) and est != computed
        out["jobs"][str(j["n"])] = {"est": est, "kind": kind_for(j["text"], e.get("kind")), "so_far": done_min,
                                    "left": left, "over": over, "eta": None if waits else int(cursor)}
        if guess:  # H168
            out["jobs"][str(j["n"])].update({"guess": guess, "computed": computed})
        if U:  # H172: its estimated usage, what it has used so far, and what's left of it before the next can start
            rec = counts.get(str(j["n"])) or {}
            c = rec.get("est") or U.cost_for(est, j["text"], e.get("kind"), hist)
            used = U._so_far(rec) if rec.get("seg") else {}
            out["jobs"][str(j["n"])]["cost"] = {k: c.get(k, 0) for k in U.KEYS}
            if used:
                out["jobs"][str(j["n"])]["used"] = used
            for k, w in (("five", "five"), ("weekly", "weekly")):  # H174: what's still to come of it, as the lines show it
                parts[w] += max(0.0, round(c.get(k, 0), 1) - round(used.get(k, 0), 1))
            if proj:
                proj.add({k: max(0.0, c.get(k, 0) - used.get(k, 0)) for k in U.KEYS}, now)
    run_end = cursor  # H99: when the running job should be done; a priority item can start from there
    line = [j for j in js if j["state"] == "ready" or j["state"].startswith("held")]
    for j in line:
        # F34: a waiting job is estimated again every time, under the kind it was given, so it follows the
        # newest finished jobs (and the right computer) instead of the number it got when it was added.
        d = job_estimate(j["n"], j["text"], hist, run["name"])
        est, kind = d["est"], d["kind"]
        if j["state"].startswith("held") and not proj:
            waits = True
        if running or j is not line[0] or cursor > now:
            cursor += GAP * 60
            left_total += GAP
            parts["gaps"] += GAP
        parts["waiting_min"] += est
        parts["held"] += j["state"].startswith("held")
        cost = U.cost_for(est, j["text"], kind, hist) if U else None
        if cost:
            parts["five"] += round(cost.get("five", 0), 1)
            parts["weekly"] += round(cost.get("weekly", 0), 1)
        fits = proj.fits_at(cost, cursor, weekly_only=j.get("past")) if proj else None
        start = None
        if proj and fits is None:
            waits = True  # it never fits as the lines stand (a fixed line without a reset time): no time from here on
        elif proj and fits > cursor + 59:
            start = cursor = fits  # H172: it waits until the usage leaves room for it
            held_wait = True
        if proj and fits is not None:
            proj.add(cost, cursor)
        cursor += est * 60
        left_total += est
        out["jobs"][str(j["n"])] = {"est": est, "kind": kind, "eta": int(cursor) if on and not (proj and waits) else None,
                                    "waits": "usage" if (waits or start) and on else ("off" if not on else None)}
        if cost:
            out["jobs"][str(j["n"])]["cost"] = {k: cost[k] for k in U.KEYS}
            out["jobs"][str(j["n"])]["cost_how"] = cost["how"]
        if start:
            out["jobs"][str(j["n"])]["start"] = int(start)
        if proj and waits:
            out["jobs"][str(j["n"])]["never"] = True
    if running or line:
        out["total"] = {"jobs": len(running) + len(line), "minutes": round(left_total),
                        "eta": int(cursor) if on and not (proj and waits) else None,
                        "waits": ("usage" if on else "off") if waits or held_wait else None,
                        "running": len(running), "waiting": len(line), **parts,
                        "five": round(parts["five"], 1), "weekly": round(parts["weekly"], 1),
                        "usage_wait": held_wait,
                        "paused": sum(1 for j in js if j["state"].startswith("paused"))}
        out["total"]["counts"] = total_counts(out["total"], bool(U))
    out["items"] = _plan_items(cursor, waits, on, hist, run, run_end, proj, U)
    out["items_total"] = _items_total(out["items"], waits, on)
    return out


def _items_total(items, waits, on):
    """H107: all planned items together, like the job list's total: how long they take together, and when
    the last one should be done (the job list goes first, so its time is already in each item's)."""
    if not items:
        return None
    t = {"items": len(items), "minutes": round(sum(e["est"] for e in items.values())), "eta": None, "waits": None,
         # H174: their usage together (each as its line shows it), and the repeating ones, counted once: their next time.
         "five": round(sum(round((e.get("cost") or {}).get("five", 0), 1) for e in items.values()), 1),
         "weekly": round(sum(round((e.get("cost") or {}).get("weekly", 0), 1) for e in items.values()), 1),
         "repeating": sum(1 for e in items.values() if e.get("every")),
         "has_cost": any(e.get("cost") for e in items.values())}
    if waits or not on or any(e.get("usage_wait") for e in items.values()):
        t["waits"] = "off" if not on else "usage"
    if on and all(e.get("eta") for e in items.values()):  # H109: held by the usage, still a time, later
        t["eta"] = max(e["eta"] for e in items.values())
    t["counts"] = items_counts(t)
    return t


def _pct(x):
    x = round(float(x), 1)
    return f"{x:g}%"


def total_counts(t, with_cost=True):
    """H174: what the job list's total counts, in plain words, part by part, so it adds up with the lines under it.
    The same sentence on the status page (under the Jobs from calls heading), in jobs.py list and on a call."""
    bits = []
    if t.get("running"):
        bits.append(f"the running job's time left ({dur(t['running_min'])})" if t["running"] == 1
                    else f"the {t['running']} running jobs' time left ({dur(t['running_min'])})")
    if t.get("waiting"):
        held = f", {t['held']} of them held by the usage" if t.get("held") and t["waiting"] > 1 else (" (held by the usage)" if t.get("held") else "")
        bits.append(f"{'the waiting job' if t['waiting'] == 1 else 'the ' + str(t['waiting']) + ' waiting jobs'} ({dur(t['waiting_min'])}{held})")
    if t.get("gaps"):
        bits.append(f"{dur(t['gaps'])} between jobs")
    s = "The total counts " + (", ".join(bits[:-1]) + " and " + bits[-1] if len(bits) > 1 else bits[0]) + f": {dur(t['minutes'])} in all"
    if with_cost:
        s += f", using about {_pct(t.get('five', 0))} of the 5-hour and {_pct(t.get('weekly', 0))} of the week"
        if t.get("running"):
            s += " (of the running job, only what's still to come)"
    s += "."
    if t.get("usage_wait"):
        s += " The time a job waits for the usage is in the done-around time, not in the minutes."
    if t.get("paused"):
        s += f" {'A paused job is' if t['paused'] == 1 else str(t['paused']) + ' paused jobs are'} parked for a call, {'isn' if t['paused'] == 1 else 'aren'}'t counted and hold nothing up."  # F37
    s += (" It's the computed estimate, from how long jobs like these took, with the team's own guess taken in for the running job"
          " as far as its guesses have been right." if t.get("guess_in") else
          " It's the computed estimate, from how long jobs like these took; the team's own guesses aren't in it.")
    return s


def items_counts(t):
    """H174: what the planned items' total counts, in plain words."""
    n = t["items"]
    s = f"The total counts {'the planned item' if n == 1 else 'each of the ' + str(n) + ' planned items'} once"
    if t.get("repeating"):
        s += (", the repeating one only its next time" if t["repeating"] == 1 else ", a repeating one only its next time")
    s += f": {dur(t['minutes'])} of work in all"
    if t.get("has_cost"):
        s += f", using about {_pct(t.get('weekly', 0))} of the week"
    s += (". The job list goes first and the items wait for their own time, so that's in the done-around time, not in the minutes."
          " It's the computed estimate, from how long work like this took.")
    return s


def _schedule():
    try:
        import schedule as sc
        import jobs as q
        return sc.read(open(q.ROADMAP, encoding="utf8").read())
    except Exception:
        return []


def _plan_items(cursor, waits, on, hist, run, run_end=None, proj=None, U=None):
    """H95: each waiting planned item, soonest first: how long, and when it should start and be done. It
    starts at its time, or once the job list and the items before it are done (the job list goes first);
    the routine looks every minute. The routine off: no times, only how long. Waiting on the usage (H109):
    the times as if the usage allowed it, with waits "usage", said as later because of the usage limit.
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
        est, kind, _ = estimate_for(i["text"], hist, kind, run["name"], (_load_items().get(str(i["n"])) or {}).get("size"))
        e = {"est": est, "kind": kind, "start": None, "eta": None, "waits": None}
        if by_hand:
            e["by_hand"] = True
        if i.get("priority"):
            e["priority"] = True
        if i.get("every"):  # H171: it repeats; the next one is planned when this one becomes a job
            e["every"] = i["every"]
        if waits or not on:
            e["waits"] = "off" if not on else "usage"
        cost = U.cost_for(est, i["text"], kind, hist) if U else None
        if cost:
            e["cost"], e["cost_how"] = {k: cost[k] for k in U.KEYS}, cost["how"]

        def fit(start):
            """H172: the first minute from start when its usage fits; it counts for the work after it."""
            if not proj:
                return start
            t = proj.fits_at(cost, start)
            if t is None:
                e["never"] = True
                return None
            if t > start + 59:
                e["usage_wait"] = True
                e["waits"] = "usage"
            proj.add(cost, max(start, t))
            return max(start, t)
        if on:
            at = dt.datetime.strptime(i["at"], "%Y-%m-%d %H:%M").timestamp()
            if i.get("priority"):  # H99: from when the running job is done, not the whole job list
                start = fit(max(at, pcursor) + GAP * 60)
                if start is None:
                    out[str(i["n"])] = e
                    continue
                pcursor = start + est * 60
                if start < cursor:  # it cuts in ahead of the waiting jobs
                    cursor += (est + GAP) * 60
                e["start"], e["eta"] = int(start), int(pcursor)
            else:
                start = fit(max(at, cursor) + GAP * 60)  # cursor: now, or when the job list should be done
                if start is None:
                    out[str(i["n"])] = e
                    continue
                cursor = start + est * 60
                e["start"], e["eta"] = int(start), int(cursor)
            e["later"] = start - at > 5 * 60  # starts later than planned: the job list or earlier items first
        out[str(i["n"])] = e
    return out


USAGE_LATE = "later, because the usage limit holds the jobs"  # H109: said next to a time the usage holds back


def dur(m):
    m = int(round(m))
    if m < 60:
        return f"{m} min"
    return f"{m // 60} h {m % 60:02d}" if m % 60 else f"{m // 60} h"


def _cost_words(e):
    """H172: a job's estimated usage next to its time, and what it used so far or in all."""
    try:
        import usagecost as U
    except Exception:
        return ""
    if e.get("finished"):
        return f"; {U.used_words(e['cost'])}" if e.get("cost") else ""
    s = f"; {U.cost_words(e['cost'])}" if e.get("cost") else ""
    if e.get("used"):
        s += f" ({U.used_words(e['used'])} so far)"
    return s


def _day(t, now):
    return "" if time.strftime("%Y-%m-%d", time.localtime(t)) == time.strftime("%Y-%m-%d", time.localtime(now)) \
        else time.strftime("%A ", time.localtime(t))


USAGE_START = "when the usage leaves room for it"  # H172: said next to a start the usage holds back


def words(n, p):
    """One job's estimate in words, for jobs.py list and a call."""
    e = p["jobs"].get(str(n))
    if not e:
        return ""
    g = f", the team guessed {dur(e['guess'])}" if e.get("guess") else ""  # H168
    if e.get("finished"):
        return (f"estimated {dur(e['est'])}{g}, took {dur(e['actual'])}" if e.get("est") else f"took {dur(e['actual'])}{g}") \
            + _cost_words(e)
    if e.get("guess") and e.get("computed") != e["est"]:
        g = f" (computed {dur(e['computed'])}, the team guessed {dur(e['guess'])})"
    if "left" in e:
        if e.get("over"):
            s = f"estimated {dur(e['est'])}{g}, running {dur(e['so_far'])}: taking longer than estimated"
        else:
            s = f"about {dur(e['left'])} left of {dur(e['est'])}{g}"
    else:
        s = f"about {dur(e['est'])}"
    s += _cost_words(e)
    if e.get("start"):  # H172: when the usage should leave room for it
        s += f", starts around {_day(e['start'], p['now'])}{hhmm(e['start'])} {USAGE_START}"
    if e.get("never"):
        s += ", it doesn't fit under the usage lines as they're set (a fixed line), so no time"
    elif e.get("eta"):
        s += f", done around {_day(e['eta'], p['now'])}{hhmm(e['eta'])}"
        if e.get("waits") == "usage" and not e.get("start"):
            s += f", but {USAGE_LATE}"
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
    s = f"about {dur(e['est'])}" + _cost_words(e)
    if e.get("never"):
        s += ", it doesn't fit under the usage lines as they're set (a fixed line), so no time"
    elif e.get("eta"):
        day = lambda t: _day(t, p["now"])  # noqa: E731
        if e.get("usage_wait"):  # H172
            s += f", starts around {day(e['start'])}{hhmm(e['start'])} {USAGE_START}"
        elif e.get("later"):
            s += f", starts around {day(e['start'])}{hhmm(e['start'])} (after the work before it)"
        s += f", done around {day(e['eta'])}{hhmm(e['eta'])}"
        if e.get("waits") == "usage" and not e.get("usage_wait"):
            s += f", but {USAGE_LATE}"
    elif e.get("waits") == "usage":
        s += ", when it's done waits on the usage"
    elif e.get("waits") == "off":
        s += ", the routine is off"
    if e.get("every"):  # H171
        s += f", each time again, {'every day' if e['every'] == 'day' else 'every ' + e['every'].capitalize()}"
    return s + " (estimate)"


def total_words(p):
    t = p.get("total")
    if not t:
        return "Nothing waiting."
    s = f"All {t['jobs']} job{'s' if t['jobs'] != 1 else ''}: about {dur(t['minutes'])}"
    if t.get("eta"):
        s += f", all done around {hhmm(t['eta'])}"
        if t.get("waits") == "usage" and not t.get("usage_wait"):
            s += f", but {USAGE_LATE}"
    elif t.get("waits") == "usage":
        s += "; when it's done waits on the usage"
    elif t.get("waits") == "off":
        s += "; the routine is off"
    return s + " (estimate)." + (f" {t['counts']}" if t.get("counts") else "")


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
        if t.get("waits") == "usage":
            s += f", but {USAGE_LATE}"
    elif t.get("waits") == "usage":
        s += "; when it's done waits on the usage"
    elif t.get("waits") == "off":
        s += "; the routine is off"
    return s + " (estimate)." + (f" {t['counts']}" if t.get("counts") else "")


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


# ---------- retag (F34) ----------

_QUEUE_LINE = re.compile(r"^- Job (\d+) · [^·]*? · (?:agreed [^·]*? · )?(.*)$")


def _roadmap_texts():
    """F34: every job's text as the roadmap's saved versions (its git history, every roadmap.md it was ever
    called) wrote it: {n: text}, the longest one for each number. {} when the roadmap isn't in git."""
    import subprocess
    try:
        import jobs as q
        repo = os.path.dirname(os.path.realpath(q.ROADMAP))
        top = subprocess.run(["git", "-C", repo, "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                             timeout=20).stdout.strip()
        if not top:
            return {}
        log = subprocess.run(["git", "-C", top, "log", "--all", "--format=@%H", "--name-only", "--", "*roadmap.md"],
                             capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return {}
    pairs, commit = [], None
    for l in log.splitlines():
        if l.startswith("@"):
            commit = l[1:]
        elif l.strip() and commit:
            pairs.append((commit, l.strip()))
    out = {}
    for c, f in pairs:
        try:
            t = subprocess.run(["git", "-C", top, "show", f"{c}:{f}"], capture_output=True, text=True, timeout=20).stdout
        except Exception:
            continue
        for l in t.splitlines():
            m = _QUEUE_LINE.match(l)
            if m and len(m.group(2)) > len(out.get(int(m.group(1)), "")):
                out[int(m.group(1))] = m.group(2)
    return out


def job_texts(from_git=True):
    """F34: every job's text that can be found: the queue now, the prompts the routine saved, and the roadmap's
    saved versions in git (jobs from day 1, also the ones the queue has long dropped)."""
    out = _roadmap_texts() if from_git else {}
    try:
        js, _ = _queue()
        out.update({j["n"]: j["text"] for j in js})
    except Exception:
        pass
    try:
        for f in os.listdir(PROMPTS):
            m = re.match(r"job-(\d+)\.prompt$", f)
            if m:
                text = open(os.path.join(PROMPTS, f), encoding="utf8").read()
                i = text.find("The job, as agreed on the call:")
                out[int(m.group(1))] = text[i:] if i >= 0 else text
    except OSError:
        pass
    return out


def _retag_map():
    try:
        return json.load(open(RETAGS)).get("lines") or {}
    except Exception:
        return {}


def new_kind(text, old):
    """F34: a finished job's kind with today's rules: what the wording says for sure (a merge, a release) wins; a
    kind it learned under that says more than the guess (build, call, big, transcribe, often set by hand on a
    call) stays; other is guessed again (merges and builds were hiding there)."""
    return kind_for(text, None if old in (None, "other") else old)


def retag(texts=None, quiet=False):
    """F34: every finished job gets its kind and tags again, from its text (job_texts): this computer's lines in
    the history file (marked with RETAG), and the other HQ's lines in job-estimates-retag.json, used until that
    one has retagged its own. Only kind, tags and its words (H166) change; how long it took and its estimate stay."""
    texts = job_texts() if texts is None else texts
    lines, changed, kinds = history(), 0, {}
    for h in lines:
        t = texts.get(h.get("n"))
        if t:
            k, tg, ab = new_kind(t, h.get("kind")), tags_of(t), _about(t)[:ABOUT_MAX]
            if k != h.get("kind"):
                kinds[(h.get("kind"), k)] = kinds.get((h.get("kind"), k), 0) + 1
            if (k, tg, ab) != (h.get("kind"), h.get("tags"), h.get("about")):
                changed += 1
            h.update(kind=k, tags=tg, about=ab)  # H166: its words too
        h["retag"] = RETAG
    if lines:
        os.makedirs(DIR, exist_ok=True)
        tmp = HISTORY + ".tmp"
        with open(tmp, "w", encoding="utf8") as f:
            f.writelines(json.dumps(h) + "\n" for h in lines)
        os.replace(tmp, HISTORY)
    peer, fix = _peer(), {}
    for h in peer.get("lines") or []:
        t = texts.get(h.get("n")) if isinstance(h, dict) else None
        if t:
            fix[f"{h.get('machine') or peer.get('name')}|{h['n']}"] = {"kind": new_kind(t, h.get("kind")), "tags": tags_of(t),
                                                                     "about": _about(t)[:ABOUT_MAX]}
    tmp = RETAGS + ".tmp"
    json.dump({"retag": RETAG, "at": int(time.time()), "lines": fix}, open(tmp, "w"))
    os.replace(tmp, RETAGS)
    if not quiet:
        print(f"Retagged {len(lines)} finished jobs here ({changed} changed"
              + "".join(f"; {n} {a} -> {b}" for (a, b), n in sorted(kinds.items(), key=str)) + f"), "
              f"and {len(fix)} of the other HQ's.")
    return changed


def retag_if_needed(log=None):
    """F34: once per version of the kinds and tags, by itself (tick.py): a computer that pulls this code retags
    its own finished jobs, so the other one learns from the new kinds too."""
    lines = history()
    if not lines or all(h.get("retag") == RETAG for h in lines):
        return None
    c = retag(quiet=True)
    if log:
        log(f"estimates: retagged {len(lines)} finished jobs ({c} changed), kinds and tags version {RETAG}")
    return c


def backtest(hist=None, last=None, alike=True, sized=False):
    """F34: every measured finished job estimated back from only the jobs finished before it, on its own computer,
    with its kind, tags and words: how close the estimates come. {"count", "avg_off", "median_off", "within"}.
    alike=False: the kind's estimate alone, as before H166, to compare. sized: with the size of the work (H167), its
    weights made only from the jobs before it, each of those estimated back the same way."""
    hist = all_history() if hist is None else hist
    offs, within, pairs = [], 0, []
    for i, h in enumerate(hist):
        if h not in _real([h]) or not _real(hist[:i]):
            continue
        d = estimate_detail("", hist[:i], h.get("kind"), h["machine"], h.get("tags") or [], h.get("about") or "", alike,
                            sized=False)
        est = d["est"]
        if sized:
            est = max(1, round(est * _size_mult(_size_fit(pairs), _size_of(h))))
            pairs.append((_size_of(h), math.log(h["actual"] / d["est"])))
        off = abs(est - h["actual"])
        offs.append(off)
        within += off <= max(3, 0.25 * est)
    if last:
        offs = offs[-last:]
    if not offs:
        return {"count": 0}
    return {"count": len(offs), "avg_off": round(statistics.mean(offs), 1), "median_off": statistics.median(offs),
            "within": within}


def reestimate():
    """H166: every waiting job's stored estimate made again now, under its kind, from the newest finished jobs and the
    ones most like it (a waiting job and a planned item are estimated again on every plan() anyway; this keeps the
    stored number, said when it was added, the same)."""
    st, hist = _load_state(), all_history()
    try:
        js, _ = _queue()
    except Exception:
        js = []
    texts = {str(j["n"]): j["text"] for j in js}
    changed = []
    for n, e in st.items():
        if e.get("started") or n not in texts:
            continue
        new = estimate_detail(texts[n], hist, e.get("kind"))["est"]
        if new != e.get("est"):
            changed.append(f"job {n}: {e.get('est')} -> {new} min")
            e["est"] = new
    if changed:
        _save_state(st)
    return "Estimated again: " + ("; ".join(changed) if changed else "nothing changed") + "."


def check_kinds():
    """H70: today's kind_of on every finished job's text next to the kind it learned under, so a change
    to the guess can be checked against the earlier jobs. Hand-set kinds say so."""
    texts = job_texts()
    for h in history():
        n = h["n"]
        text = texts.get(n, "")
        if not text:
            continue
        now = new_kind(text, h.get("kind"))  # F34: the kind a retag gives it
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
        print(p["guesses"]["words"])  # H168
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
    elif cmd == "retag":
        retag()
    elif cmd == "backtest":
        hist = all_history()
        for how, alike, sized in (("With the size of the work (H167)", True, True), ("From the most similar jobs (H166)", True, False),
                                  ("From the kind alone (before H166)", False, False)):
            print(how + ":")
            for name, n in (("All", None), ("Last 30", 30)):
                b = backtest(hist, last=n, alike=alike, sized=sized)
                if b.get("count"):
                    print(f"  {name}: {b['count']} measured jobs estimated back from the jobs before them: off by {b['avg_off']:g} min "
                          f"on average (median {b['median_off']:g})" + (f"; {b['within']} close." if not n else "."))
    elif cmd == "reestimate":
        print(reestimate())
    elif cmd == "guesses":
        f = guess_fit()
        print(guess_words(f))
        for x in f.get("recent") or []:
            print(f"  job {x['n']}: the team guessed {dur(x['guess'])}, computed {dur(x['est'])}, took {dur(x['actual'])}")
    elif cmd == "look":
        text = " ".join(a for a in argv[1:] if a != "--haiku")
        t0 = time.time()
        size = look(_about(text))
        ms = (time.time() - t0) * 1000
        d = estimate_detail(text, size=size)
        print(f"The look (no Claude, {ms:.0f} ms): {size_words(size)}.")
        print(f"About {dur(d['est'])}: the similar jobs say {dur(d.get('by_similar', d['est']))}, the size moves it x{d.get('size_mult', 1):g}.")
        if "--haiku" in argv:
            hs, cost, secs = look_haiku(_about(text))
            print(f"Haiku's look ({secs:g} s, ${cost or 0:.5f}): " + (size_words(hs) if hs else "no answer") + ".")
    elif cmd == "similar":
        text = " ".join(argv[1:])
        d = estimate_detail(text)
        print(f"About {dur(d['est'])} ({d['kind']}; the kind alone: {dur(d['by_kind'])}).")
        for x in d["similar"]:
            print(f"  job {x['n']}: {x['alike']:g} alike, took {dur(x['actual'])}")
        if not d["similar"]:
            print("  No finished job is enough like it; the kind's estimate stands.")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
