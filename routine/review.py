#!/usr/bin/env python3
"""F77: every new or changed row on the planning gets an automatic review by a fresh reviewer, 28 October 2026.
In the user's words (call of 28 October 2026, about 16:50, Moneypenny): "maybe we can have an automated process that
just checks each item [that] gets put or changed on the whole roadmap, planning, backlog, however we're calling it right
now. And it just automatically checks if it passes the checklist. If it doesn't, it flags it with a specific tag. And
then whenever there is that tag, you and I immediately need to talk about it." And at 16:55: "this should be an
automated process in the back. Always continuously looking at the roadmap, see whenever something is added or changed.
Run the low usage Claude prompt check if your checklist passes."

  - What starts a review: only a change to a row's ask (sprint.ask_of: its title and its description, what he and
    Moneypenny write). Never its status mark, the team's built or done notes, QA lines, the rank, the MoSCoW tag, the
    Ready mark, the flag or the status block: none of those uses usage or takes a mark off ("when the team actually
    works on it and just change the status of it, right, that then it doesn't check it again"). One fingerprint per row,
    the ask as last reviewed.
  - When: on the main computer, every minute from tick.py, once a row's ask has been quiet for QUIET seconds (a row
    written in steps on a call is reviewed once), at most AT_ONCE at a time, each wording once.
  - The first start: every open row's ask is taken as already reviewed, without a review ("baseline"), so there's no
    burst; only what's added or changed after that is reviewed. F80 (29 October 2026): the rows taken that way get one
    real review each with `pass` (below), one after another.
  - The reviewer: a small Claude run (MODEL and EFFORT: Sonnet at medium effort since F80, his words: "Use medium
    effort sonnet"; no tools: it reads only the row it's
    given and can't change anything) holds the row against the nine ready points (a bug row with an F label: the three
    points of a small fix) and walks the same five probes every time (PROBES: twice, halfway, where each number comes
    from, the examples, each point), quoting the sentence that covers each; one that applies with none is a hole by
    rule (verdict). It answers pass, or flag with a few plain findings.
  - The flag and its findings are kept in sprint.json ("review"), next to the Ready mark, never in the row (or they'd
    start a review themselves). A flagged row can't be marked ready (sprint.py ready says why); a row that gets the
    flag loses its Ready mark. The flag goes when the row's ask changes and the next review passes, or on his say-so on
    a call (clear LABEL "his words", kept with the row).
  - A row that's new or changed and not reviewed yet can't be marked ready until its review has passed.
  - A review that doesn't run (a time-out, no answer) leaves no flag and no pass: it's tried again RETRY_S later; from
    the second failure the row shows "the review didn't run" on the planning, so it's never skipped in silence.
  - F101: an answer needs all five probes and its "covered" quotes must stand in the item; `golden` runs real past rows the
    reviewer must still flag (review.py golden), on every change to the reviewer.
  - Usage: each review's cost is kept, one line per attempt in COSTS (reviews.jsonl: the row, the verdict or failed,
    the cost, the seconds, the model and the effort), failed attempts with what they cost too. No daily cap and no
    waiting for the night (F80, 29 October 2026; the cap was F77's own addition, never his): a new or changed row is
    reviewed within QUIET plus a few minutes, day or night, one at a time, each within BUDGET.
  - On Moneypenny's calls only (her briefing, quick_context._planning), the flagged rows come first, to raise before
    anything else, like the mail heads-up; Donna's and Pepper's never see them.
  - F86 (30 October 2026): the fix-and-review loop runs by itself. In the user's words (call of 29 October 2026): "i want
    you create the item to the best of your ability Then the stystem tools check it and flag it Then you improve it
    again And the tool check again And this repeats until the tool says it looks good And then and only then can you
    mark it ready", "And the loop part? It should open a prompt with you and it should go automatic". Here is the
    loop's state (in sprint.json, each row's "fix"); routine/cycles.py opens her short sessions: a round rewords the row
    (reword, that one row and nothing else) and the review looks again; once it passes, one short session for her
    mark, the review's pass first, hers second. A finding only he can answer is never filled in: sitdown puts it on
    her sit-down list with one text on her line and the loop stops for that row. A round can only add: what stands in
    the row stays byte for byte, and her words go in one marked place (addition), read by the review as part of the
    ask. And no is an answer too: a row that can't be done as asked, or isn't worth building, she says so (no): the
    row stops, loses any Ready mark, and only his words through clear lift it. After every round the program holds the planning against what stood
    before it (round_before, round_after, outside her session): only her one addition on her one row may differ; anything else is put back. At most ROUNDS rounds an item,
    then the sit-down list, for good: no day starts them again. A stop holds until the row's words change. Rows flagged
    before the loop was switched on wait for her calls, unless they have a rank.

usage:
  python3 routine/review.py list                 the review state of every open row
  python3 routine/review.py tick                 what the routine runs every minute (on the main)
  python3 routine/review.py clear LABEL "WORDS"  take a flag off on his say-so on a call, his words kept with it
  python3 routine/review.py run LABEL            a review now, in the foreground (a test, or by hand)
  python3 routine/review.py pass                 F80's one-time pass: every open row never really reviewed gets one
                                                 review, one after another (resumes; a failure is retried once, then named)
  python3 routine/review.py pass-result          what the pass found: each row's verdict, the failures, the total cost
  python3 routine/review.py reword LABEL 'JSON'  a call's way: {"edits": [{"old": "...", "new": "..."}]} inside that one row
  python3 routine/review.py add LABEL "WORDS"    F86: what a round writes, or the words on stdin: added in one marked place, nothing else changes
  python3 routine/review.py no LABEL "WHY" "WHAT COULD WORK INSTEAD" "If ..., I'll ...; if not, ..."
                                                 F86: this can't be done as asked or isn't worth building: the row stops, one text, he decides
  python3 routine/review.py sitdown LABEL "THE OPEN POINT WITH YOUR FIX" "If ..., I'll ...; if not, ..."
                                                 F86: on her sit-down list, one text on her line, the loop stops for it
  python3 routine/review.py sitdown-list         F86: what waits for him
  python3 routine/review.py keep [N]             F86: his keep it: what the look after round N, or the last one, put back, as it was written
Used by the background review itself: review-run LABEL.
"""
import contextlib
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_FILE = os.path.abspath(__file__)
sys.path.insert(0, HERE)
import estimate as E  # noqa: E402
import hqpaths  # noqa: E402
import jobs as q  # noqa: E402
import roundlog  # noqa: E402
import sprint as S  # noqa: E402

# The lightest model that does it (his "low usage Claude prompt"). Tried on real rows on 28 October 2026 (job 438):
# Haiku flagged H297 as first written but missed its second stop, and flagged its whole version too; Sonnet at low
# effort found both holes and passed the whole one, about a cent a review. QA (job 450) then found that was luck: 3 of
# 5. With the probes (job 455, 29 October 2026): H297 as first written flagged 8 of 8 at low effort and 8 of 8 at
# medium, H297 as it is passed 8 of 8 at both; low named the second stop every time and the cost's source 6 of 8, at about $0.008 a review.
MODEL = os.environ.get("HQ_REVIEW_MODEL") or "sonnet"
EFFORT = os.environ.get("HQ_REVIEW_EFFORT") or "medium"  # F80, his words: "Use medium effort sonnet"
QUIET = int(os.environ.get("HQ_REVIEW_QUIET") or 300)  # seconds a row's ask must stay the same before it's reviewed
AT_ONCE = 1
TIMEOUT = 180  # seconds for one review
PENDING = TIMEOUT + 60  # a started review counts as on its way this long
RETRY_S = int(os.environ.get("HQ_REVIEW_RETRY") or 1800)  # a review that didn't run is tried again after this
SHOW_FAILED = 2  # from this many failures for the same words, the row says the review didn't run
BUDGET = 0.15  # dollars at most for one review (--max-budget-usd)
LOG = os.path.join(E.DIR, "reviews.log")
COSTS = os.path.join(E.DIR, "reviews.jsonl")  # one line per attempt: the row, the verdict or failed, the cost, the seconds, model, effort

# F77's fix (job 455, 29 October 2026, after QA job 450): with "when in doubt, pass" and a free verdict the reviewer
# flagged H297 as first written only 3 of 5 times (0 of 6 at medium effort), and a miss lets the hole through for good,
# since each wording is reviewed once. Now it walks the same five probes every time, says for each whether it applies
# to this item and quotes the sentence that covers it, and an applying probe with no sentence is a hole by rule
# (verdict() below), not by mood.
PROBES = (
    ("again", "The thing the item is about happens more than once: a second stop, a second run, a retry, twice in a "
              "row. Does the item say what then?"),
    ("halfway", "It stops or fails halfway, or meets an empty, missing or not-yet-there input. Does the item say what "
                "then?"),
    ("numbers", "Every number, cost, count or measurement the item asks the team to find or report, above all a part "
                "to be split out of a larger whole (one step's share, one turn's cost, one day's count): does the item "
                "say where it's read from, a source the team can actually read? A figure the project plainly keeps "
                "already (a job's estimate, its total, its time) needs no source named, and turning tokens or dollars "
                "into a percent, or into the unit the item's other figures already use, is settled the obvious way: "
                "never a hole by itself."),
    ("examples", "Each 'done means' example: could someone really try it and tell yes or no?"),
    ("points", "Each point of the checklist: does it say something, not just name the point?"),
)

SYSTEM = (
    "You review one item of a software project's planning before it may be marked ready for the build team. You did "
    "not write it. You read only the item you're given; you have no tools and change nothing. Hold it against the "
    "points of the checklist and hunt for real holes, as a reviewer who wants the team to build or check the right "
    "thing the first time. Do the same walk every time, probe by probe:\n"
    + "".join(f"- {k}: {q}\n" for k, q in PROBES)
    + "For each probe decide whether it applies to this item: it applies when what the item is about can really meet "
    "that case (something that can fail can fail twice; a figure to report has to be read from somewhere). When it "
    "applies, copy the item's own sentence that covers it into \"covered\", word for word; when no sentence covers it, "
    "\"covered\" is null and \"hole\" says in one plain sentence what's missing, naming the point. Don't count a "
    "sentence that only covers the case in general when the item's own question is left open (a figure given without "
    "where to read it; one case handled when it can happen several times). A hole is something that would make a careful "
    "team build, measure or check the wrong thing, or leave them unable to tell whether it's done. Not a hole: a detail "
    "a careful team would settle the obvious way, style, length, wording, something the item rightly puts out of scope, "
    "or a requirement you invent. Answer with JSON only, nothing else: "
    '{"probes": [{"probe": "again", "applies": true, "covered": "the sentence" or null, "hole": null or "the sentence"}, '
    '... one per probe, in order], "pass": true or false, "findings": ["one plain sentence per hole", ...]}. '
    "pass is false exactly when a probe applies with no covering sentence, or you found another real hole; at most "
    "four findings, the most important first.")

NINE = ("1. what's asked; 2. what done means, with examples someone can try; 3. the test (which flow, what it covers); "
        "4. why; 5. out of scope; 6. what it touches; 7. its size; 8. what it waits on; "
        "9. the privacy check")
THREE = "1. what's wrong; 2. what right looks like; 3. how to check it's fixed"


LINE_EVERY = 30 * 86400  # F102: its line isn't overdue in a quiet month: it runs when a row changes


def on():
    """Whether reviews may run here: not with HQ_REVIEW=0, and a test copy (HQ_ROADMAP) only with HQ_REVIEW_FAKE."""
    if os.environ.get("HQ_REVIEW", "1") == "0":
        return False
    if q.is_paused():  # F100: a pause holds the reviewer too
        return False
    return bool(os.environ.get("HQ_REVIEW_FAKE")) or not os.environ.get("HQ_ROADMAP")


def _clock():
    """Now, or HQ_REVIEW_NOW (a test's clock, epoch seconds)."""
    return float(os.environ.get("HQ_REVIEW_NOW") or time.time())


def _log(line):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
    except OSError:
        pass


def _state():
    d = S._load(S.RANKS)
    rv = d.get("review")
    return d, (rv if isinstance(rv, dict) else {})


def _today(now=None):
    return dt.datetime.fromtimestamp(now or time.time()).strftime("%Y-%m-%d")


def points_of(row):
    """The checklist a row is held against: a bug row with an F label the three of a small fix, else the nine."""
    return THREE if S.is_bug(row) and str(row.get("label", "")).startswith("F") else NINE


# ---------- the state of one row ----------

def state_of(row, e, now=None):
    """One open row's review state: {"state": "baseline"|"passed"|"cleared"|"flagged"|"waiting"|"didnt_run",
    "findings", "changed" (its ask changed since the verdict shown)}."""
    fp = S.ask_fp(row["line"])
    e = e or {}
    same = e.get("ask") == fp
    out = {"findings": e.get("findings") or [], "changed": not same and bool(e.get("ask"))}
    if e.get("verdict") == "flag":
        out["state"] = "flagged"  # the flag stays until a review passes the new words, or he clears it
    elif same:
        out["state"] = {"baseline": "baseline", "pass": "passed", "cleared": "cleared"}.get(e.get("verdict"), "waiting")
    elif (e.get("tries") or [None, 0])[0] == fp and e["tries"][1] >= SHOW_FAILED:
        out["state"] = "didnt_run"
    else:
        out["state"] = "waiting"
    if out["state"] == "flagged" and e.get("cleared_words"):
        out["cleared_words"] = e["cleared_words"]
    if e.get("cleared_words") and out["state"] == "cleared":
        out["cleared_words"] = e["cleared_words"]
    if e.get("at"):
        out["at"] = e["at"]
    return out


def states(rows=None):
    """{label: state_of} for the open rows."""
    rows = S.open_rows() if rows is None else rows
    _, rv = _state()
    rs = rv.get("rows") or {}
    return {r["label"]: state_of(r, rs.get(r["label"])) for r in rows}


def why_not_ready(row, st=None):
    """Why the review keeps a row from the Ready mark, in a few plain words, or None (also when reviews don't run
    here, or haven't started yet: then nothing waits on them)."""
    no_ = _said_no(row)
    if no_:
        return f"{row['label']} isn't ready: Moneypenny said no to it, and it's his to decide: {no_.get('why', '')}"
    if not (on() or q.is_paused()) or not _state()[1].get("since"):  # F86: a pause holds the reviewer, it doesn't open this gate
        return None
    st = st or states([row]).get(row["label"]) or {}
    s = st.get("state")
    if s == "flagged":
        f = "; ".join(st.get("findings") or []) or "no findings written"
        more = " (its words changed since; the next review looks again)" if st.get("changed") else ""
        return f"{row['label']} isn't ready: the review flagged it{more}: {f}"
    if s == "waiting":
        return (f"{row['label']} isn't ready: it's new or changed and its review hasn't passed yet (it runs once the "
                f"row has been quiet {QUIET // 60} minutes); it can be marked once it passes")
    if s == "didnt_run":
        return f"{row['label']} isn't ready: its review didn't run (it's tried again); it can be marked once it passes"
    return None


# ---------- the routine's minute ----------

def tick(log=None, now=None, start=True):
    """Every minute on the main: the first start takes every open row as reviewed; then a row whose ask changed is
    noted, and once quiet long enough a review starts (AT_ONCE at a time, each wording once; no daily cap, F80).
    Rows no longer open are let go. Returns the labels a review started for."""
    now = now or _clock()
    started = []
    _rounds_left(log)
    with q.locked():
        rows = S.open_rows()
        d, rv = _state()
        rs = rv.get("rows") or {}
        have = {r["label"] for r in rows}
        for k in [k for k in rs if k not in have]:
            rs.pop(k)
        first = not rv.get("since")
        if first:
            rv["since"] = int(now)
        marks = d.get("ready") or {}
        for r in rows:
            fp = S.ask_fp(r["line"])
            e = rs.setdefault(r["label"], {})
            if first:
                e.update({"ask": fp, "verdict": "baseline", "at": int(now)})
            if e.get("seen") != fp:
                e["seen"], e["seen_at"] = fp, int(now)
            m = marks.get(r["label"])  # a Ready mark from before F77 that still holds now holds the ask
            if isinstance(m, dict) and not m.get("ask") and S.mark_holds(m, r["line"]):
                m["ask"] = fp
        spent = rv.get("spent") or {}
        if spent.get("day") != _today(now):
            spent = {"day": _today(now), "usd": 0.0, "n": 0}
        pending = [k for k, e in rs.items() if now - (e.get("pending") or 0) < PENDING]
        if start and on() and not first:
            for r in rows:
                if len(pending) >= AT_ONCE:
                    break
                e = rs[r["label"]]
                fp = e["seen"]
                if e.get("ask") == fp or r["label"] in pending or now - e["seen_at"] < QUIET:
                    continue
                tries = e.get("tries") or [None, 0]
                if tries[0] == fp and now < (e.get("next_try") or 0):
                    continue
                e["pending"] = int(now)
                try:
                    os.makedirs(E.DIR, exist_ok=True)
                    out = open(LOG, "a")
                    subprocess.Popen([sys.executable, os.path.abspath(__file__), "review-run", r["label"]], cwd=E.ROOT,
                                     stdin=subprocess.DEVNULL, stdout=out, stderr=out, start_new_session=True)
                    pending.append(r["label"])
                    started.append(r["label"])
                except Exception as ex:
                    e.pop("pending", None)
                    print(f"(the review couldn't start: {ex!r})", file=sys.stderr)
        rv.pop("waits_night", None)  # F80: no more waiting for the night
        rv["rows"], rv["spent"] = rs, spent
        d["review"] = rv
        if marks:
            d["ready"] = marks
        S._save(S.RANKS, d)
    if first and log:
        log(f"review: first start, {len(rows)} open rows taken as reviewed (F77)")
    if started and log:
        log(f"review: a review for {', '.join(started)} on the planning (F77)")
    return started


# ---------- the review itself ----------

def _input(row):
    return ("The checklist (" + ("a small bug fix" if points_of(row) == THREE else "a feature or bigger change") + "): "
            + points_of(row) + "\n\nThe item, as written on the planning:\n\n" + S.ask_of(row["line"])[:24000])


def _fake(row):
    """HQ_REVIEW_FAKE (tests): "auto" flags a row whose ask holds "HOLE:" (the words after it the finding, unless "FILLED:" and the same words stand in it) and passes
    the rest, and a row holding "FAILREVIEW" never answers; "fail" never answers for any row (a failed attempt, at HQ_REVIEW_FAKE_COST like the rest)."""
    how = os.environ.get("HQ_REVIEW_FAKE")
    cost = float(os.environ.get("HQ_REVIEW_FAKE_COST") or 0)
    if how == "fail" or "FAILREVIEW" in S.ask_of(row["line"]):  # "FAILREVIEW" in a row: only that one fails
        return {"failed": True, "why": "the stand-in never answers", "cost": cost, "s": 0.0, "model": "fake", "effort": EFFORT}
    ask = S.ask_of(row["line"])
    m = re.search(r"HOLE:\s*([^.|]+)", ask)
    if m and f"FILLED: {m.group(1).strip()}" not in ask:  # a round adds, it takes nothing away: an addition fills the hole
        return {"pass": False, "findings": [m.group(1).strip()], "cost": cost, "s": 0.0, "model": "fake", "effort": EFFORT}
    return {"pass": True, "findings": [], "cost": cost, "s": 0.0, "model": "fake", "effort": EFFORT}


def _one(f):
    return re.sub(r"\s+", " ", str(f)).strip()[:400]


def in_item(quote, ask):
    """F101: whether the reviewer's "covered" sentence really stands in the item, punctuation aside. Its parts around a
    "…" each."""
    parts = [S._bare(x) for x in re.split(r"\s*(?:…|\.\.\.)\s*", quote)]
    have = S._bare(ask)
    return any(parts) and all(x in have for x in parts if x)


def verdict(a, ask=None):
    """The reviewer's JSON to (pass, findings), or None when it's not an answer. A probe that applies with no covering
    sentence is a hole whatever its own pass says (F77's fix); its own findings come first. F101: an answer without all
    five probes is no answer, and a "covered" sentence that isn't in the item (ask) covers nothing."""
    if not isinstance(a, dict) or not isinstance(a.get("pass"), bool):
        return None
    answered = {p.get("probe") for p in a.get("probes") or [] if isinstance(p, dict)}
    if any(k not in answered for k, _ in PROBES):
        return None
    fs = [_one(f) for f in (a.get("findings") or []) if str(f).strip()]
    for p in a.get("probes") or []:
        if not isinstance(p, dict) or p.get("applies") is not True:
            continue
        cov = p.get("covered")
        if isinstance(cov, str) and cov.strip():
            if ask is None or in_item(cov, ask):
                continue
            h = _one(f"the {p.get('probe', 'a')} probe quotes something that isn't in the item")
            if h not in fs:
                fs.append(h)
            continue
        h = _one(p.get("hole") or f"the {p.get('probe', 'a')} probe applies and nothing in the item covers it")
        if h and h not in fs:
            fs.append(h)
    ok = a["pass"] and not fs
    if not ok and not fs:
        fs = ["the reviewer flagged it without saying why"]
    return ok, ([] if ok else fs[:5])


# nowroad (4 November 2026): the review settles. His design, 30 October 2026: "It gets reviewed through a tool, the work is correct, and it can bounce
# back and forth up to three times". Until now every change brought a whole new review: the five probes found fresh "what if it happens twice, is
# missing, stops halfway" holes each round, and a row that had passed was flagged again after any change (61 rows flagged against 9 passed on
# 4 November). A row that has had a verdict is now looked at again only for: whether each earlier point is settled by a sentence that stands in
# it now, and whether a sentence that changed brings in a hole of its own. A new point must quote the changed sentence it comes from, or it
# doesn't count; a point about something that didn't change can't come up again.
RESYSTEM = (
    "You check one item of a software project's planning again, after it was changed. You did not write it; you read only what you're given, you "
    "have no tools and change nothing. An earlier review raised the points listed. Do exactly two things. 1. For each earlier point, in order: copy, "
    "word for word, the sentence of the item as it is now that settles it, or null when nothing does. A point is settled when the item now answers "
    "it, puts it out of scope, or says how the team decides it. 2. Look only at the changed sentences listed: does one of them, by itself, bring in "
    "a real hole, something that would make a careful team build or check the wrong thing? Not a hole: anything in a sentence that didn't change, "
    "a detail a careful team settles the obvious way, a new what-if about a case the change didn't raise, style or wording. Answer with JSON only: "
    '{"earlier": [{"point": "...", "settled_by": "the sentence" or null}, ... one per earlier point, in order], '
    '"new": [{"hole": "one plain sentence", "in": "the changed sentence it comes from, word for word"}]}, at most two new.')


def _sentences(t):
    return [x.strip() for x in re.split(r"(?<=[.!?;])\s+", str(t or "")) if x.strip()]


def changed_text(old, new):
    """The sentences of the new ask that weren't in the old one (punctuation and case aside), in order."""
    had = {S._bare(x) for x in _sentences(old)}
    return [x for x in _sentences(new) if S._bare(x) not in had]


def _dedupe(fs):
    out, seen = [], set()
    for f in fs:
        k = S._bare(f)[:120]
        if k and k not in seen:
            seen.add(k)
            out.append(f)
    return out


def again_input(row, prior):
    ask = S.ask_of(row["line"])[:REVIEW_READS]
    ch = prior.get("changed") or []
    pts = prior.get("findings") or []
    return ("The earlier points:\n" + ("".join(f"{i + 1}. {f}\n" for i, f in enumerate(pts)) or "(none)\n")
            + "\nThe changed sentences:\n" + ("".join(f"- {x}\n" for x in ch) or "(none)\n")
            + "\nThe item as it is now:\n\n" + ask)


def again_verdict(a, ask, prior):
    """The re-review's JSON to (pass, findings), or None when it's not an answer: an earlier point stays open unless its sentence stands in the
    item now; a new point counts only when the sentence it quotes is one that changed."""
    if not isinstance(a, dict) or not isinstance(a.get("earlier", []), list) or not isinstance(a.get("new", []), list):
        return None
    pts = prior.get("findings") or []
    got = [x for x in a.get("earlier") or [] if isinstance(x, dict)]
    open_ = []
    for i, f in enumerate(pts):
        q = got[i].get("settled_by") if i < len(got) else None
        if not (isinstance(q, str) and q.strip() and in_item(q, ask)):
            open_.append(f)
    ch = " ".join(prior.get("changed") or [])
    for x in a.get("new") or []:
        if isinstance(x, dict) and str(x.get("hole") or "").strip() and isinstance(x.get("in"), str) and ch and in_item(x["in"], ch):
            open_.append(_one(x["hole"]))
    open_ = _dedupe(open_)
    return (not open_), open_[:5]


def prior_of(e, ask):
    """What a re-review needs from the row's last verdict, or None for a first review: a row with no real verdict yet (new, or taken as it was
    at the first start), or a passed row whose words before aren't kept (verdicts from before 4 November)."""
    e = e or {}
    if e.get("verdict") not in ("pass", "flag"):
        return None
    old = e.get("text")
    if old is None:
        if e.get("verdict") == "pass":
            return None
        m = S.ADDITION.search(ask)  # before the words were kept: what a round added is what changed
        ch = _sentences(ask[m.start():]) if m else []
    else:
        ch = changed_text(old, ask)
    return {"findings": _dedupe(e.get("findings") or []), "changed": ch, "verdict": e.get("verdict")}


def ask_reviewer(row, prior=None):
    """The reviewer's answer: {"pass", "findings", "cost" (dollars), "s", "model", "effort"}; when it didn't run (a
    time-out, over its budget, no answer) {"failed": True, "why", "cost" (what it cost, when the run said), ...} (F80:
    a failed attempt's cost is kept too)."""
    if os.environ.get("HQ_REVIEW_FAKE"):
        return _fake(row)
    if prior is not None and not prior["findings"] and not prior["changed"]:
        return {"pass": True, "findings": [], "cost": 0.0, "s": 0.0, "model": "none", "effort": "", "again": True}  # nothing open, nothing new
    try:
        import hqpaths
        claude = hqpaths.tool("claude", "/opt/homebrew/bin/claude")
    except Exception:
        claude = "claude"
    t0 = time.time()
    base = {"model": MODEL, "effort": EFFORT}
    cost = None
    try:
        p = subprocess.run([claude, "-p", "--model", MODEL, "--output-format", "json", "--tools", "",
                            "--strict-mcp-config", "--setting-sources", "", "--effort", EFFORT,
                            "--max-budget-usd", str(BUDGET), "--no-session-persistence", "--system-prompt", RESYSTEM if prior else SYSTEM],
                           input=again_input(row, prior) if prior else _input(row), capture_output=True, text=True, timeout=TIMEOUT, cwd=E.ROOT)
        d = json.loads(p.stdout)
        cost = d.get("total_cost_usd")
        if d.get("is_error") or d.get("subtype") not in (None, "success"):
            raise ValueError(f"the run ended {d.get('subtype') or 'with an error'}")
        found = re.findall(r"\{.*\}", d.get("result") or "", re.S)
        a = json.loads(found[-1])
        v = again_verdict(a, S.ask_of(row["line"]), prior) if prior else verdict(a, S.ask_of(row["line"]))
        if v is None:
            raise ValueError("the answer wasn't a verdict" + ("" if prior else " with all five probes"))
        ok, fs = v
        return {"pass": ok, "findings": fs, "cost": cost, "s": round(time.time() - t0, 1), **base, **({"again": True} if prior else {})}
    except subprocess.TimeoutExpired:
        return {"failed": True, "why": f"timed out after {TIMEOUT} s", "cost": cost, "s": round(time.time() - t0, 1), **base}
    except Exception as ex:
        return {"failed": True, "why": str(ex)[:200] or repr(ex), "cost": cost, "s": round(time.time() - t0, 1), **base}


def _attempt(label, now_fn=_clock, extra=None):
    """One review of one row, outside the lock; its verdict is written only when the row's ask is still the one it
    read (changed in between: the next minute's tick starts the next one). Every attempt, a failed one too, is a line
    in COSTS with what it cost, the model and the effort (F80). Returns the reviewer's answer, or None when the row
    isn't open (any more)."""
    def now_row():
        return next((r for r in S.open_rows() if r["label"] == label), None)
    with q.locked():
        r = now_row()
        prior = prior_of(((_state()[1].get("rows") or {}).get(label) or {}), S.ask_of(r["line"])) if r else None
    if not r:
        return None
    fp = S.ask_fp(r["line"])
    a = (ask_reviewer(r, prior) if prior is not None else ask_reviewer(r)) or {"failed": True, "why": "no answer", "cost": None}
    failed = bool(a.get("failed"))
    lost = False
    try:  # F102: a reviewer that doesn't run turns its line red and opens an incident; the next good run closes it
        import routines
        (routines.bad("review", f"The review of {label} didn't run: {a.get('why') or 'no answer'}", every=LINE_EVERY) if failed
         else routines.good("review", f"Reviewed {label}", every=LINE_EVERY))
    except Exception:
        pass
    with q.locked():
        d, rv = _state()
        rs = rv.get("rows") or {}
        e = rs.get(label)
        if e is None:
            return None
        e.pop("pending", None)
        now = int(now_fn())
        r2 = now_row()
        if failed:
            tries = e.get("tries") or [None, 0]
            e["tries"] = [fp, (tries[1] if tries[0] == fp else 0) + 1]
            e["next_try"] = now + RETRY_S
        elif r2 and S.ask_fp(r2["line"]) == fp:
            e.update({"ask": fp, "verdict": "pass" if a["pass"] else "flag", "findings": a["findings"], "at": now,
                      "cost": a.get("cost"), "s": a.get("s"), "model": a.get("model"), "effort": a.get("effort"),
                      "text": S.ask_of(r["line"])[:REVIEW_READS], "again": bool(a.get("again"))})  # nowroad: the words this verdict is on
            e.pop("tries", None)
            import trail  # F105: the verdict on the item's record
            trail.step(trail.resolve(label), "review", verdict="pass" if a["pass"] else "flag", findings=len(a["findings"]))
            e.pop("next_try", None)
            e.pop("cleared_words", None)
            if not a["pass"]:
                marks = d.get("ready") or {}
                if label in marks:  # a row that gets the flag loses its Ready mark
                    marks.pop(label)
                    d["ready"] = marks
                    lost = True
        sp = rv.get("spent") or {}
        if sp.get("day") != _today(now):
            sp = {"day": _today(now), "usd": 0.0, "n": 0}
        sp["usd"] = round(sp["usd"] + float(a.get("cost") or 0), 4)  # every attempt counts, day or night (F80)
        sp["n"] = sp.get("n", 0) + 1
        rv["spent"] = sp
        rs[label] = e
        rv["rows"] = rs
        d["review"] = rv
        S._save(S.RANKS, d)
    rec = {"row": label, "at": int(now_fn()), "fp": fp}
    if failed:
        rec.update({"failed": True, "why": a.get("why")})
    else:
        rec.update({"verdict": "pass" if a["pass"] else "flag", "findings": len(a["findings"])})
    rec.update({"cost": a.get("cost"), "s": a.get("s"), "model": a.get("model"), "effort": a.get("effort")})
    rec.update(extra or {})
    try:
        os.makedirs(E.DIR, exist_ok=True)
        with open(COSTS, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        pass
    _log(f"review {label}: " + (f"didn't run ({a.get('why')})" if failed else ("passed" if a["pass"] else "flagged: " + "; ".join(a["findings"])))
         + (" (its Ready mark taken off)" if lost else "") + (f", ${a['cost']:.4f}" if a.get("cost") else "")
         + (" [the one-time pass]" if (extra or {}).get("pass") else ""))
    return a


def review_run(label, now_fn=_clock):
    """In the background, started by tick: one review of one row (a failure is tried again RETRY_S later by tick)."""
    return _attempt(label, now_fn)


# ---------- F80: one real review for every row taken as reviewed at the first start ----------

PASS_WAIT = int(os.environ.get("HQ_REVIEW_PASS_WAIT") or 5)  # seconds between looks while another review runs
PASS_MOST = int(os.environ.get("HQ_REVIEW_PASS_MOST") or 0)  # a test's stop halfway: at most this many rows a run


def _due(rows, rs, now):
    """The first open row tick would review now (new or changed, quiet long enough, not waiting for a retry), or None."""
    for r in rows:
        e = rs.get(r["label"]) or {}
        fp = S.ask_fp(r["line"])
        if e.get("ask") == fp or e.get("seen") != fp or now - (e.get("seen_at") or now) < QUIET:
            continue
        tries = e.get("tries") or [None, 0]
        if tries[0] == fp and now < (e.get("next_try") or 0):
            continue
        return r["label"]
    return None


def _claim(now_fn, log):
    """Under the lock: wait while another review runs (one at a time, as F77), then say which row is next: a row tick
    has due first (a row edited or added during the pass is never held up by it: within QUIET plus a review, F80's 15
    minutes), else the next row of the pass. Marks it pending (tick then waits) and returns (label, kind), or None."""
    while True:
        with q.locked():
            d, rv = _state()
            rs = rv.get("rows") or {}
            now = int(now_fn())
            if any(now - (e.get("pending") or 0) < PENDING for e in rs.values()):
                label = kind = None
            else:
                rows = S.open_rows()
                label, kind = _due(rows, rs, now), "changed"
                if not label:
                    label = next((r["label"] for r in rows if (rs.get(r["label"]) or {}).get("verdict") == "baseline"
                                  and (rs.get(r["label"]) or {}).get("ask") == S.ask_fp(r["line"])), None)
                    kind = "pass"
                if not label:
                    return None
                rs[label]["pending"] = now
                rv["rows"] = rs
                d["review"] = rv
                S._save(S.RANKS, d)
                return label, kind
        time.sleep(PASS_WAIT)


def run_pass(log=print, now_fn=_clock):
    """F80's one-time pass, in the foreground: every open row whose words are still the ones taken as reviewed at
    F77's first start ("baseline") gets one real review, one after another, flags and lost Ready marks as any review.
    Stopped halfway or run twice, it carries on with what's left (a row once reviewed is never baseline again). A
    failed review is tried again once at once; failing again, it's named in the pass's result and not counted as
    reviewed (the row then waits like a changed row: tick tries it again RETRY_S later and the planning shows the
    review didn't run). Rows edited or added during the pass get their review as tick would, first. Every attempt is
    a line in COSTS marked with the pass; the pass's result (each row, its verdict, its cost, its attempts, the total)
    is kept in sprint.json under review.pass. Closed rows are never reviewed."""
    if not on():
        sys.exit("Reviews don't run here (HQ_REVIEW=0, or a test copy without HQ_REVIEW_FAKE).")
    with q.locked():
        d, rv = _state()
        if not rv.get("since"):
            sys.exit("The review hasn't had its first start yet (tick); nothing was taken as reviewed.")
        ps = rv.get("pass") or {}
        if not ps or ps.get("ended"):
            ps = {"started": int(now_fn()), "rows": {}, "usd": 0.0, **({"before": ps} if ps else {})}
        ps["runs"] = ps.get("runs", 0) + 1
        ps.pop("ended", None)
        rv["pass"] = ps
        d["review"] = rv
        S._save(S.RANKS, d)
    pid = ps["started"]
    done_now = 0
    while True:
        if PASS_MOST and done_now >= PASS_MOST:
            log(f"review pass: stopped after {done_now} rows (HQ_REVIEW_PASS_MOST, a test's stop halfway)")
            return ps
        c = _claim(now_fn, log)
        if not c:
            break
        label, kind = c
        if kind == "changed":
            log(f"review: {label} changed, reviewed before the pass goes on")
            _attempt(label, now_fn)
            continue
        done_now += 1
        out = {"attempts": 0, "usd": 0.0}
        a = None
        for n in (1, 2):
            if n == 2:
                with q.locked():  # the retry, at once: still pending, so tick waits
                    d, rv = _state()
                    e = (rv.get("rows") or {}).get(label)
                    if e is None:
                        break
                    e["pending"] = int(now_fn())
                    S._save(S.RANKS, d)
            a = _attempt(label, now_fn, {"pass": pid, "attempt": n})
            if a is None:
                break
            out["attempts"] = n
            out["usd"] = round(out["usd"] + float(a.get("cost") or 0), 6)
            if not a.get("failed"):
                break
        with q.locked():
            d, rv = _state()
            rs = rv.get("rows") or {}
            e = rs.get(label) or {}
            if a is None:
                out["gone"] = True  # closed or changed while it ran: not the pass's any more
            elif a.get("failed"):
                out.update({"failed": True, "why": a.get("why")})
                if e.get("verdict") == "baseline":
                    e.pop("ask", None)  # never counted as reviewed: it waits like a changed row now
                    e.pop("verdict", None)
            else:
                out["verdict"] = "pass" if a["pass"] else "flag"
            if e:
                rs[label] = e
            ps = rv.get("pass") or {}
            if ps.get("started") == pid:
                ps.setdefault("rows", {})[label] = out
                ps["usd"] = round(sum(float(x.get("usd") or 0) for x in ps["rows"].values()), 6)
                rv["pass"] = ps
            rv["rows"] = rs
            d["review"] = rv
            S._save(S.RANKS, d)
        log(f"review pass: {label} " + ("failed twice: " + str(out.get("why")) if out.get("failed") else
                                         out.get("verdict", "let go")) + f", ${out['usd']:.4f}")
    with q.locked():
        d, rv = _state()
        ps = rv.get("pass") or {}
        ps["ended"] = int(now_fn())
        rv["pass"] = ps
        d["review"] = rv
        S._save(S.RANKS, d)
    log(pass_words(ps))
    return ps


def pass_words(ps=None):
    """The pass's result in a few lines."""
    if ps is None:
        ps = _state()[1].get("pass") or {}
    if not ps:
        return "The one-time pass (F80) hasn't run."
    rows = ps.get("rows") or {}
    by = lambda k: sorted(l for l, x in rows.items() if x.get("verdict") == k)  # noqa: E731
    failed = sorted(l for l, x in rows.items() if x.get("failed"))
    head = (f"The one-time pass (F80){' (still running or stopped)' if not ps.get('ended') else ''}: {len(rows)} rows, "
            f"{len(by('pass'))} passed, {len(by('flag'))} flagged, {len(failed)} failed; "
            f"{sum(x.get('attempts', 0) for x in rows.values())} attempts, ${ps.get('usd', 0):.4f} in all.")
    out = [head]
    if by("flag"):
        out.append("Flagged: " + ", ".join(by("flag")))
    if failed:
        out.append("Failed twice, not counted as reviewed: " + "; ".join(f"{l} ({rows[l].get('why')})" for l in failed))
    return "\n".join(out)


def clear(label, words):
    """His say-so on a call: the flag off, his words kept with the row (in sprint.json, outside the ask). F99: the words
    must stand in his own lines (a call, a text, a quick note), so a flag never comes off on an agent's word."""
    label = label.strip().upper()
    words = q.one_line(words or "").strip()
    if not words:
        sys.exit("Clearing a flag needs his words, as he said them on the call.")
    now = next((r for r in S.open_rows() if r["label"] == label), None)
    where, no = S.his_yes(words, f"taking the review's flag off planning row {label}, so it goes on as it is: {(now or {}).get('line', '')[:400]}", names=(label,))
    if not where:
        sys.exit(f"Refused: {no}, so the flag on {label} stays. Quote at least three words he really said or typed in a call, a text or a "
                 "quick note, saying yes to this.")
    with q.locked():
        row = next((r for r in S.open_rows() if r["label"] == label), None)
        if not row:
            sys.exit(f"{label} isn't an open row on the planning.")
        d, rv = _state()
        rs = rv.get("rows") or {}
        e = rs.get(label) or {}
        said_no = _stopped(e, S.ask_fp(row["line"]))
        if said_no and said_no.get("kind") == "no":  # his decision on her no
            e["fix"].pop("stop")
            e["fix"].update({"n": 0, "no_lifted": {"words": words, "where": where, "at": int(_clock())}})
            if e.get("verdict") != "flag":
                S._save(S.RANKS, d)
                return e
        if e.get("verdict") != "flag":
            sys.exit(f"{label} has no flag to take off.")
        e.update({"ask": S.ask_fp(row["line"]), "verdict": "cleared", "at": int(_clock()),
                  "cleared_words": words, "cleared_where": where, "cleared_findings": e.get("findings") or []})
        e["findings"] = []
        rs[label] = e
        rv["rows"] = rs
        d["review"] = rv
        S._save(S.RANKS, d)
    return e


# ---------- F101: the golden set ----------

# F101 (C76): real past rows the reviewer once flagged for a real hole, each of which it must still flag. They're his own
# planning rows, so the file is the workspace's (HQ/review-golden.json), never HQ's: {"rows": [{"label", "line", "must"}],
# "passed_for": fingerprint}. A change to the reviewer (its prompt, probes, model, effort or what it reads) gives a new
# fingerprint, and a flow fails until the real reviewer has flagged them all again; the weekly sweep runs it too.
def golden_file():
    return os.environ.get("HQ_GOLDEN") or os.path.join(S._ws(), "HQ", "review-golden.json")


def fingerprint():
    import hashlib
    import inspect
    parts = [SYSTEM, repr(PROBES), MODEL, str(EFFORT), inspect.getsource(verdict), inspect.getsource(_input),
             inspect.getsource(S.ask_of), inspect.getsource(S.team_note_at), S.TEAM_NOTE.pattern]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


def golden():
    """Every golden row through the real reviewer; passes only when each is flagged. Its usage is logged like any review."""
    try:
        data = json.load(open(golden_file(), encoding="utf8"))
    except (OSError, ValueError) as ex:
        print(f"No golden set here: {ex}")
        return 3
    rows = data.get("rows") or []
    missed, failed, cost = [], [], 0.0
    for r in rows:
        row = {"label": r["label"], "line": r["line"], "phase": r["label"][0], "title": ""}
        got = ask_reviewer(row)
        cost += float(got.get("cost") or 0)
        try:
            with open(COSTS, "a") as f:
                f.write(json.dumps({"row": r["label"], "at": int(_clock()), "golden": True, "verdict": "failed" if got.get("failed") else ("pass" if got.get("pass") else "flag"),
                                    "cost": got.get("cost"), "s": got.get("s"), "model": got.get("model"), "effort": got.get("effort")}) + "\n")
        except OSError:
            pass
        if got.get("failed"):
            failed.append(f"{r['label']} ({got.get('why')})")
        elif got.get("pass"):
            missed.append(r["label"])
        print(f"{r['label']}: {'failed to run' if got.get('failed') else 'passed it, it should have flagged it' if got.get('pass') else 'flagged'}", flush=True)
    good = len(rows) - len(missed) - len(failed)
    print(f"Golden set: {good} of {len(rows)} flagged, ${cost:.3f}.")
    if rows and not missed and not failed:
        data["passed_for"] = fingerprint()
        tmp = golden_file() + ".tmp"
        with open(tmp, "w", encoding="utf8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, golden_file())
        return 0
    return 1


def golden_current():
    """Whether the real reviewer has flagged the golden set since it last changed: True, False, or None with no set here."""
    try:
        data = json.load(open(golden_file(), encoding="utf8"))
    except (OSError, ValueError):
        return None
    return data.get("passed_for") == fingerprint()


# ---------- F86: the fix-and-review loop ----------

ADD_MOST = 4000  # F86: characters in one addition, about two pages; three rounds are 12,000. The review reads 24,000 of a row (_input)
REVIEW_READS = 24000
ROUNDS_DIR = roundlog.folder()
ROUND_QUIET = 300  # F86: seconds no row may have changed before a round starts, his five minutes
ROUNDS = 3  # rounds an item, then the sit-down list and one text to him (F86, his yes 30 October 2026; F101: per item, not per day)
STOP_WORDS = {"his": "needs him", "cap": f"{ROUNDS} rounds and the review still flags it", "mark": "her mark didn't land",
              "no": "she says no, it's his to decide, and only his words lift it, through review.py clear",
              "broke": "its own row changed during a round, outside its one addition, with no door behind it"}


def _stopped(e, fp):
    """The stop that holds on these words, or None: new words (his answer written in) lift it. Her no stands whatever the words: only clear lifts it."""
    st = (e.get("fix") or {}).get("stop")
    return st if st and (st.get("ask") == fp or st.get("kind") == "no") else None


def _said_no(row):
    """Her no on this row as its words stand, or None."""
    st = _stopped((_state()[1].get("rows") or {}).get(row["label"]) or {}, S.ask_fp(row["line"]))
    return st if st and st.get("kind") == "no" else None


def _rounds(e):
    """F101 (C36): the rounds this item has had, whatever the day; two before midnight and three after is five."""
    return int((e.get("fix") or {}).get("n") or 0)


def next_round(now=None):
    """The routine's look, for routine/cycles.py: {"pick": {"label", "mode": "mark"|"fix", "round"} or None, "capped":
    [labels that just went on the sit-down list]}. A mark for a row past the review comes first (since F105 also one that passed the first time), then the
    flagged rows, ranked first (F87's rank 1 goes first). Only a verdict on the row's current words counts: changed
    words wait for their review. Rows flagged before the loop was on (fix_since) are left to her calls, unless ranked."""
    now = now or _clock()
    capped = []
    with q.locked():
        rows = S.open_rows()
        d, rv = _state()
        rs = rv.get("rows") or {}
        since = rv.get("fix_since")
        if not since:
            since = rv["fix_since"] = int(now)
        marks = S.ready_of(rows)
        ranked = S.order(rows)
        place = {l: i for i, l in enumerate(ranked)}
        order = sorted(rows, key=lambda r: place.get(r["label"], len(ranked)))
        pick = None
        for r in order:
            e, label, fp = rs.get(r["label"]) or {}, r["label"], S.ask_fp(r["line"])
            f = e.get("fix") or {}
            if e.get("ask") == fp and e.get("verdict") == "pass" and (f or int(e.get("at") or 0) >= since) and marks.get(label) != "ready" \
                    and f.get("marked") != fp and not _stopped(e, fp):  # F105: a row that passes the first time gets its mark run too
                pick = {"label": label, "mode": "mark", "round": 0}
                break
        for r in ([] if pick else order):
            e, label, fp = rs.get(r["label"]) or {}, r["label"], S.ask_fp(r["line"])
            if e.get("ask") != fp or e.get("verdict") != "flag" or _stopped(e, fp):
                continue
            if label not in place and int(e.get("at") or 0) < since:
                continue
            f = e.setdefault("fix", {})
            if f.get("stop") and f["stop"].get("ask") != fp:  # new words lifted the stop; after the cap, rounds from nothing
                if f.pop("stop").get("kind") == "cap":
                    f["n"] = 0
            n = _rounds(e)
            if n >= ROUNDS:
                f["stop"] = {"ask": fp, "kind": "cap", "why": "; ".join(e.get("findings") or []), "at": int(now)}
                capped.append(label)
                continue
            pick = {"label": label, "mode": "fix", "round": n + 1}
            break
        rv["rows"] = rs
        d["review"] = rv
        S._save(S.RANKS, d)
    return {"pick": None if pick and round_waits() else pick, "capped": capped}


def round_started(pick, now=None):
    """A round is on its way: it counts from here, a cut-off one too."""
    now = now or _clock()
    with q.locked():
        d, rv = _state()
        e = (rv.get("rows") or {}).get(pick["label"])
        if e is None:
            return
        f = e.setdefault("fix", {})
        if pick["mode"] == "mark":
            f["marked"] = e.get("ask")
        else:
            f.update({"day": _today(now), "n": _rounds(e) + 1, "at": int(now)})
            import trail  # F105
            trail.step(trail.resolve(pick["label"]), "round", n=f["n"])
        S._save(S.RANKS, d)


def round_refund(label, mode, now=None):
    """A round that never ran (skipped at the start) doesn't count."""
    now = now or _clock()
    with q.locked():
        d, rv = _state()
        e = (rv.get("rows") or {}).get(label)
        f = (e or {}).get("fix")
        if not f:
            return
        if mode == "mark":
            f.pop("marked", None)
        elif f.get("n"):
            f["n"] -= 1
        S._save(S.RANKS, d)


def mark_ended(label, why, now=None):
    """Her mark's run is over. Marked, or on the sit-down list by her own hand: nothing to do. Else (cut off, or it ended
    with neither) the row would wait unseen, since a mark gets one run: it goes on the list, named, for her next call."""
    now = now or _clock()
    with q.locked():
        rows = S.open_rows()
        row = next((r for r in rows if r["label"] == label), None)
        d, rv = _state()
        e = (rv.get("rows") or {}).get(label)
        if not row or not e:
            return False
        fp = S.ask_fp(row["line"])
        if e.get("ask") != fp or e.get("verdict") != "pass" or _stopped(e, fp) or S.ready_of([row]).get(label) == "ready":
            return False
        e.setdefault("fix", {})["stop"] = {"ask": fp, "kind": "mark", "why": why, "at": int(now)}
        S._save(S.RANKS, d)
    return True


def stop_stays(label):
    """A round over: a sit-down of this round holds on the words it ended with, also when she reworded after it. Else her
    own words would lift it, and the next round would go past the text he already has."""
    with q.locked():
        row = next((r for r in S.open_rows() if r["label"] == label), None)
        d, rv = _state()
        f = ((rv.get("rows") or {}).get(label) or {}).get("fix") or {}
        st = f.get("stop")
        if row and st and st.get("kind") in ("his", "no") and st.get("round") == f.get("n"):
            st["ask"] = S.ask_fp(row["line"])
            S._save(S.RANKS, d)


def round_wanted(label, mode):
    """Whether the round still has work when it starts (a call may have fixed the row meanwhile)."""
    with q.locked():
        r = next((x for x in S.open_rows() if x["label"] == label), None)
        e = (_state()[1].get("rows") or {}).get(label) or {}
    if not r:
        return False
    return e.get("ask") == S.ask_fp(r["line"]) and e.get("verdict") == ("pass" if mode == "mark" else "flag")


def in_round():
    """(label, "fix"|"mark") when this process is a round of the loop, or None. The runner sets HQ_ROUND on her session, so whatever she
    runs has it, a script of hers too; a call and a person don't."""
    label, _, mode = (os.environ.get("HQ_ROUND") or "").partition(":")
    return (label.upper(), mode) if label and mode else None


def _new_quotes(old, new):
    """Every quote in the new ask that wasn't in the old one, wherever it stands: a second His words, "He said:", a yes."""
    pick = lambda line: {m.group(1).strip() for m in S._QUOTES.finditer(S.ask_of(line))}  # noqa: E731
    return pick(new) - pick(old)


_ANY_MARK = re.compile(f"[{S.QUOTE_OPEN}{S.QUOTE_CLOSE}]")


def _addition_why(words, about=""):
    """What's wrong with an addition of hers, or None. A quote in it must be one unbroken piece of one line of his (sprint.his_quote: his own
    lines, never an agent's), and a team's mark can't stand in it: those are put by their own commands, in their own place."""
    if S.TEAM_NOTE.search(words):
        return ("Refused: that has the shape of the team's mark (Built, Done, Fixed, QA passed or failed). A mark is put only by its own "
                "command at its own place. Say it without that shape.")
    rest = words
    for marks in S.QUOTE_MARKS:  # a quote is a quote, in any marks, backticks too
        for m in marks.finditer(rest):
            bit = m.group(1).strip()
            if re.search(r"…|\.\.\.", bit):
                return f"Refused: a quote of his is one unbroken piece of one line of his, with no … in it: {bit[:80]!r}."
            if not S.his_quote(bit):
                return (f"Refused: this between quote marks isn't in his own lines (a call, a text or a quick note of his; three words at least, and an "
                        f"agent's line is never his): {bit[:80]!r}. Copy his words exactly, or take the quote marks off: a name or a label goes without.")
            where, why = S.his_on(bit, about)
            if not where:
                return (f"Refused: {why}: {bit[:80]!r}. His words are never filled from something else: if you'd have to explain that he said it about another thing, "
                        "it doesn't go in. A row he said nothing about says: His words: none, found by job N (or by the review, or a check). If his words are needed, it goes on the list.")
        rest = marks.sub(" ", rest)
    if _ANY_MARK.search(rest):
        return "Refused: a quote mark with no partner. Quote marks stand only around his own words."
    return None


def _note_of(line):
    """The team's part of a row's description (Built, QA, ...), never hers to change."""
    cs = hqpaths.cells(line)
    desc = cs[2] if len(cs) > 2 else ""
    at = S.team_note_at(desc)
    return "" if at is None else desc[at:]


def ask_edit(line, edits):
    """nowroad (4 November 2026): the edits applied inside the row's ask only, its title and its description before the team's notes, each old
    text found there once; every other cell and the notes stay byte for byte. Rows written before 4 November held the same words again in the
    Model column, so an edit of the whole line met them twice and was refused, or changed one copy and not the other."""
    import handover
    cs, spans = hqpaths.cells(line), hqpaths.cell_spans(line)
    if len(cs) < 3 or len(spans) != len(cs):
        raise ValueError("the row has no description to change")
    desc = cs[2]
    at = S.team_note_at(desc)
    ask = desc if at is None else desc[:at].rstrip()
    sep = "\n"
    fixed = []
    for e in edits:
        e = dict(e)
        e["new"] = re.sub(r"(?<!\\)\|", r"\\|", str(e.get("new") or ""))  # a pipe in the new words would split the row
        if "\n" in str(e.get("old") or "") + e["new"]:
            raise ValueError("a row is one line: no line breaks in an edit")
        fixed.append(e)
    try:
        both = handover.apply(cs[1] + sep + ask, fixed)
    except LookupError as ex:
        raise LookupError(str(ex).replace("the main's copy", "the row's title and words")) from None
    title, _, ask2 = both.partition(sep)
    a1, b1 = spans[1]
    a2 = spans[2][0]
    b2 = a2 + len(ask)
    return line[:a1] + title + line[b1:a2] + ask2 + line[b2:]


def reword(label, payload):
    """A call's edits inside this one row's ask, all or nothing, under the queue's lock: its status, its label, its other cells
    and the team's notes stay as they are, and a new quote anywhere in it must be found in a call, the notes or the log. A round
    never comes through here: it can only add (addition)."""
    import handover
    label = label.strip().upper()
    if in_round():
        sys.exit(f"Refused: a round can only add; everything in the row stays exactly as it is. Your words go through: python3 review.py add {label} with the words.")
    try:
        edits = json.loads(payload).get("edits") or []
        assert isinstance(edits, list) and edits and all(isinstance(x, dict) for x in edits)
    except Exception:
        sys.exit('Refused: no edits given ({"edits": [{"old": "...", "new": "..."}]}).')
    with q.locked():
        text = open(q.ROADMAP, encoding="utf8").read()
        row = next((r for r in S.open_rows(text) if r["label"] == label), None)
        if not row:
            sys.exit(f"Refused: {label} isn't an open row on the planning.")
        line = row["line"]
        try:
            new = ask_edit(line, edits)
        except (LookupError, ValueError) as ex:
            sys.exit(f"Not written: {ex}.")
        was, now_ = hqpaths.cells(line), hqpaths.cells(new)
        if "\n" in new or len(now_) != len(was) or now_[1].split()[:1] != was[1].split()[:1] or now_[0] != was[0] or now_[3:] != was[3:]:
            sys.exit("Refused: the row must stay one row with the same status, label and cells; only its title and words change.")
        if _note_of(new) != _note_of(line):
            sys.exit("Refused: the team's notes on a row aren't reworded, and nothing goes after them: the review reads what comes before.")
        texts = S._grep_texts(S._ws())
        bad = [x for x in _new_quotes(line, new) if not S.quote_found(x, texts)]
        if bad:
            sys.exit(f"Refused: a new quote isn't in a call, the notes or the log: {bad[0][:80]!r}. His words are never written for "
                     "him; it goes on the sit-down list. (Not his words at all, a name or a label: write it without the quote marks.)")
        hqpaths.guard_roadmap(q.ROADMAP)
        roundlog.planning(q.ROADMAP, text.replace(line, new, 1))
        tmp = f"{q.ROADMAP}.reword.{os.getpid()}"
        with open(tmp, "w", encoding="utf8") as f:
            f.write(text.replace(line, new, 1))
        os.replace(tmp, q.ROADMAP)
    no_ = _stopped((_state()[1].get("rows") or {}).get(label) or {}, S.ask_fp(new))
    return (f"{label} changed; the review looks again once it's been quiet {QUIET // 60} minutes."
            + (" Her no stands: only clear with his words lifts it." if no_ and no_.get("kind") == "no" else ""))


def addition(label, words, now=None):
    """What a round writes: her words, under her name and the date, in one place: after everything that stands in the row's ask and before
    the team's notes. The rest of the row stays byte for byte, so nothing of his can go, and nothing she writes can read as his."""
    import cycles
    label, words = label.strip().upper(), q.one_line(words or "").strip()
    held = in_round()
    if held and (held[0] != label or held[1] != "fix"):
        sys.exit(f"Refused: this run is on {held[0]} ({held[1]}); only a round adds, and only to its own row.")
    if not words:
        sys.exit("Refused: no words to add.")
    if len(words) > ADD_MOST:
        sys.exit(f"Refused: {len(words)} characters; an addition is at most {ADD_MOST}. Say what the row needs, or it goes on the list.")
    was_row = next((r for r in S.open_rows() if r["label"] == label), None)
    if not was_row:
        sys.exit(f"Refused: {label} isn't an open row on the planning.")
    why = _addition_why(words, S.ask_of(was_row["line"])[:1500])
    if why:
        sys.exit(why)
    day = dt.datetime.fromtimestamp(now or _clock())
    mine = f"{cycles.fix_name()}'s addition ({day.day} {day:%B %Y}): " + re.sub(r"(?<!\\)\|", r"\\|", words)
    with q.locked():
        text = open(q.ROADMAP, encoding="utf8").read()
        row = next((r for r in S.open_rows(text) if r["label"] == label), None)
        if not row:
            sys.exit(f"Refused: {label} isn't an open row on the planning.")
        line = row["line"]
        cs = hqpaths.cells(line)
        if len(cs) < 3:
            sys.exit(f"Refused: {label} has no description to add to.")
        at = S.team_note_at(cs[2])
        ask, notes = (cs[2], "") if at is None else (cs[2][:at], cs[2][at:])
        cs[2] = (ask.rstrip() + " " + mine + (" " + notes if notes else "")).strip()
        new = hqpaths.join_cells(cs)
        if "\n" in new or not S.ask_of(new).startswith(S.ask_of(line)) or _note_of(new) != _note_of(line):  # the promise, held once more on the result
            sys.exit("Refused: the addition would change what stands in the row. Nothing written.")
        if len(S.ask_of(new)) > REVIEW_READS:
            sys.exit(f"Refused: the row would pass the {REVIEW_READS} characters the review reads, so it couldn't see your words. It goes on the list.")
        d, rv = _state()
        f = rv.setdefault("rows", {}).setdefault(label, {}).setdefault("fix", {})
        if held and f.get("added", {}).get("n", -1) == f.get("n"):
            sys.exit("Refused: one addition a round. Nothing written.")
        was, will, held_ = S.field_texts(line), S.field_texts(new), S.ready_fields({"label": label, "line": new})
        for key, name in (("his_words", "His words"), ("sources", "Sources")):  # what she writes she can't take back: a field of hers that won't hold doesn't go in
            if not was[key] and will[key] and not held_[key]["ok"]:
                sys.exit(f"Refused: the {name} in your addition wouldn't hold: {held_[key]['why']}. Nothing written; a round can't change it later, so put it right now.")
        hqpaths.guard_roadmap(q.ROADMAP)
        roundlog.planning(q.ROADMAP, text.replace(line, new, 1))  # a laptop chat's add is a door too
        tmp = f"{q.ROADMAP}.reword.{os.getpid()}"
        with open(tmp, "w", encoding="utf8") as fh:
            fh.write(text.replace(line, new, 1))
        os.replace(tmp, q.ROADMAP)
        if held:
            f["added"] = {"n": f.get("n"), "sha": _sha(new)}  # what the look after the round holds her row to
            d["review"] = rv
            S._save(S.RANKS, d)
    still = S.fields_why({"label": label, "line": new})
    return (f"{label}: your addition is in; the review reads it as part of the row and looks again once it's been quiet {QUIET // 60} minutes."
            + (f" Your mark will need: {still.split(': ', 1)[1]}." if still else " Its ready fields hold."))


def _sha(line):
    import hashlib
    return hashlib.sha256(line.encode()).hexdigest()


def round_waits():
    """Why no round may start now, or "": a call is on, or a row changed in the last five minutes. seen_at comes from the file itself, so that also
    covers the status page, a laptop chat and a call on the other computer."""
    import helper
    if helper.current():
        return "a call is on"
    now = _clock()
    if any(now - (e.get("seen_at") or 0) < ROUND_QUIET for e in (_state()[1].get("rows") or {}).values()):
        return "a row changed in the last five minutes"
    return ""


def _call_since(at):
    """Whether a call was on at any moment since `at`: on now, or a transcript written since."""
    import helper
    if helper.current():
        return True
    calls = os.path.join(S._ws(), "HQ", "calls")
    try:
        return any(os.path.getmtime(os.path.join(calls, x)) > at for x in os.listdir(calls) if x.endswith(".md"))
    except OSError:
        return False


def round_before(n, label, mode):
    """The runner, before her session starts: what stands before the round, kept outside it."""
    os.makedirs(ROUNDS_DIR, exist_ok=True)
    round_after(n)  # a held round that starts again: the last run's look first, if it never came
    with q.locked():
        text = open(q.ROADMAP, encoding="utf8").read()
        d, rv = _state()
    with open(os.path.join(ROUNDS_DIR, f"job-{n}.json"), "w", encoding="utf8") as f:
        json.dump({"n": n, "label": label, "mode": mode, "at": time.time(), "planning": text, "ready": d.get("ready") or {}, "rows": rv.get("rows") or {}}, f)


def _rows_back(text, before, back, gone, wrote=()):
    """The planning with these rows as they were, row by row. A file cut in half, a phase heading gone with it, comes back whole from what stood before, with
    what a door wrote on its rows in those minutes."""
    was, now = roundlog.keyed_rows(before), roundlog.keyed_rows(text)
    if _cut(text, before):
        lines, seen = before.split("\n"), {}
        for line in text.split("\n"):  # by label wherever it stands: its heading may be what went
            m = re.match(r"\| [^|]* \| ([A-Z]\d+(?:\.\d+)*)\b", line)
            if m:
                k = (m.group(1), seen.get(m.group(1), 0))
                seen[m.group(1)] = k[1] + 1
                if f"row {k[0]}" in wrote and k in was:
                    lines[lines.index(was[k])] = line
        return "\n".join(lines)
    lines = text.split("\n")
    for key in back:
        lines[lines.index(now[key])] = was[key]
    order = list(was)
    for key in gone:
        i = order.index(key)
        after = next((was[k] for k in reversed(order[:i]) if was[k] in lines), None)
        lines.insert(lines.index(after) + 1 if after else len(lines), was[key])
    return "\n".join(lines)


def _cut(text, before):
    return not roundlog.keyed_rows(text) or any(x.startswith("## Phase") and x not in text for x in before.split("\n"))  # the status headings move by themselves


def _the_change(old, new):
    """What differs between two versions of a row, in a few words each."""
    a, b = S.ask_of(old), S.ask_of(new)
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    j = 0
    while j < min(len(a), len(b)) - i and a[-1 - j] == b[-1 - j]:
        j += 1
    bit = lambda t: q.one_line(t[max(0, i - 30):len(t) - j + 10])[:160].strip() or "(nothing there)"  # noqa: E731
    return (bit(a), bit(b)) if a != b else (q.one_line(old)[:60], q.one_line(new)[:60])


def round_after(n):
    """The runner, after her session, or the routine's minute when the runner never got there: what stood before the round against what stands now, row by row
    by label, the queue, the sprint file. What's in the journal (roundlog) was written through a door by someone else: it stays, and nobody is told. Only her one
    addition on her row is hers. What's left, a change no door wrote, goes back as a last net: with a call on it can't be told apart and it's kept and named,
    with none it goes back, a job or item is cancelled, and he's told right away, what it said, what it says now, and that "keep it" brings it back (keep).
    A new row stays and is named. The planning is copied first, and what went back is kept in job-N.put-back.json."""
    p = os.path.join(ROUNDS_DIR, f"job-{n}.json")
    try:
        s = json.load(open(p, encoding="utf8"))
    except (OSError, ValueError):
        return ""
    label, mode, before = s["label"], s["mode"], s["planning"]
    call = _call_since(s.get("at") or 0)
    wrote = roundlog.read(f"job-{n}")
    with q.locked():
        try:
            text = open(q.ROADMAP, encoding="utf8").read()
        except OSError:
            text = ""
        d, rv = _state()
        rs = rv.setdefault("rows", {})
        f = (rs.get(label) or {}).get("fix") or {}
        was, now_ = roundlog.keyed_rows(before), roundlog.keyed_rows(text)
        cut = _cut(text, before)
        anywhere = {m.group(1) for m in re.finditer(r"^\| [^|]* \| ([A-Z]\d+(?:\.\d+)*)\b", text, re.M)}  # a row moved out of the phases isn't gone
        changed = [k for k in was if k in now_ and was[k] != now_[k] and f"row {k[0]}" not in wrote
                   and not (k[0] == label and mode == "fix" and S.ask_of(now_[k]).startswith(S.ask_of(was[k])) and (f.get("added") or {}).get("sha") == _sha(now_[k]))]
        lost_rows = [k for k in was if k not in now_ and f"row {k[0]}" not in wrote and (cut or k[0] not in anywhere)]
        fresh = [k for k in now_ if k not in was and f"row {k[0]}" not in wrote]
        q0, q1 = roundlog.queue(before), roundlog.queue(text)
        jobs_new = {j: x for j, x in q1["jobs"].items() if j not in q0["jobs"] and f"job {j}" not in wrote}
        items_new = {i: x for i, x in q1["items"].items() if i not in q0["items"] and f"item {i}" not in wrote}
        ready, was_ready = d.get("ready") or {}, s.get("ready") or {}
        gained = [k for k, v in ready.items() if v != was_ready.get(k) and f"ready {k}" not in wrote and not (k == label and mode == "mark")]
        lost = [k for k in was_ready if k not in ready and f"ready {k}" not in wrote]
        passed = [k for k, e in rs.items() if e.get("verdict") != ((s.get("rows") or {}).get(k) or {}).get("verdict") and f"verdict {k}" not in wrote and e.get("verdict") in ("pass", "cleared")]
        anything = bool(changed or lost_rows or fresh or jobs_new or items_new or gained or lost or passed)
        said, told, back, gone, kept = [], False, [], [], []
        if anything:
            net = not call  # no door wrote it and no call was on: the last net
            back, gone, kept = (changed if net or cut else []), (lost_rows if net or cut else []), ([] if net or cut else changed + lost_rows)
            copy = os.path.join(ROUNDS_DIR, f"job-{n}.planning.md")
            if back or gone:
                with open(copy, "w", encoding="utf8") as fh:
                    fh.write(text)
                os.makedirs(os.path.dirname(q.ROADMAP), exist_ok=True)
                tmp = f"{q.ROADMAP}.back.{os.getpid()}"
                with open(tmp, "w", encoding="utf8") as fh:
                    fh.write(_rows_back(text, before, back, gone, wrote))
                os.replace(tmp, q.ROADMAP)
            with open(os.path.join(ROUNDS_DIR, f"job-{n}.put-back.json"), "w", encoding="utf8") as fh:
                json.dump({"n": n, "label": label, "call": call, "back": [[was[k], now_[k]] for k in back], "gone": [was[k] for k in gone], "kept": [[was[k], now_.get(k, "")] for k in kept],
                           "new_rows": [now_[k] for k in fresh], "jobs": jobs_new, "items": items_new, "gained": {k: ready[k] for k in gained}, "lost": {k: was_ready[k] for k in lost},
                           "passed": {k: rs[k] for k in passed}, "copy": copy if back or gone else ""}, fh)
            for k in back[:3]:
                old, new_ = _the_change(was[k], now_[k])
                said.append(f"{k[0]} said \"{new_}\" and I put it back to \"{old}\"")
            if gone:
                said.append("these rows were gone and came back: " + ", ".join(sorted({k[0] for k in gone})))
            if kept:
                said.append("changed and kept: " + ", ".join(sorted({k[0] for k in kept})))
            if fresh:
                said.append("new, kept: " + ", ".join(sorted({k[0] for k in fresh})))
            for x, what in ((jobs_new, "job"), (items_new, "item")):
                for i, line in x.items():
                    said.append(f"{what} {i} appeared, \"{q.one_line(line.split(' · ')[-1])[:80]}\"" + (", kept" if call else ", and I cancelled it"))
            if gained or lost or passed:
                said.append(("Ready marks or passes changed and kept: " if call else "Ready marks or passes I put back: ") + ", ".join(sorted(set(gained + lost + passed))))
            if net:
                for k in gained:
                    ready.pop(k)
                for k in lost:
                    ready[k] = was_ready[k]
                for k in passed:
                    if k in (s.get("rows") or {}):
                        rs[k] = s["rows"][k]
                    else:
                        rs.pop(k)
                d["ready"] = ready
            own = net and (any(k[0] == label for k in back + gone) or label in gained + lost + passed)  # only the one place the round itself writes stops its row
            if own:
                row = next((r for r in S.open_rows() if r["label"] == label), None)
                e = rs.setdefault(label, {})
                g = e.setdefault("fix", {})
                st = _stopped(e, S.ask_fp(row["line"])) if row else None
                told = bool(st and st.get("kind") in ("his", "no") and st.get("round") == g.get("n"))
                if row and not told:
                    g["stop"] = {"ask": S.ask_fp(row["line"]), "kind": "broke", "at": int(_clock()), "round": g.get("n"), "why": "; ".join(said)[:400]}
            rv["round_said"] = (rv.get("round_said") or [])[-19:] + [{"at": int(_clock()), "label": label, "call": call, "n": n, "words": "; ".join(said)[:600]}]
            d["review"] = rv
            S._save(S.RANKS, d)
    os.remove(p)
    for x in (f"job-{n}.journal.jsonl",):
        with contextlib.suppress(OSError):
            os.remove(os.path.join(ROUNDS_DIR, x))
    if not anything:
        return ""
    import cycles
    import ledger
    words = "; ".join(said)
    if not call:
        here = os.path.dirname(os.path.abspath(__file__))
        for j in jobs_new:
            subprocess.run([sys.executable, os.path.join(here, "jobs.py"), "stop", str(j)], capture_output=True, timeout=60)
        for i in items_new:
            subprocess.run([sys.executable, os.path.join(here, "schedule.py"), "cancel", str(i)], capture_output=True, timeout=60)
    ledger.note(cycles.FIX_AGENT, f"after job {n}, the round on {label}" + (", a call on in those minutes" if call else "") + f": {words[:300]}. Kept in .status/rounds/job-{n}.put-back.json")
    if call:
        text_ = f"While my round on {label} ran the planning changed, with a call on, so I can't say who did what: {words}. If any of that isn't what you want, tell me which and I'll set it right; if not, it stays."
    else:
        text_ = f"While my round on {label} ran something changed that I can't place: {words}. If that was you, say keep it and it comes back as you wrote it; if not, there's nothing to do."
    if not told:
        cycles.say(cycles.FIX_AGENT, text_[:1500], "round-put-back", dt.datetime.now())  # H298: every text of hers waits for his sleep
    return f"after the round on {label}: {words[:300]}"


def keep(n=None):
    """His "keep it": what the last net put back (or job N's) as it was written. The kept words are in .status/rounds/job-N.put-back.json."""
    if in_round():
        sys.exit("Refused: this run is a round; his keep it is for a call or a chat.")
    names = sorted((x for x in os.listdir(ROUNDS_DIR) if re.fullmatch(r"job-\d+\.put-back\.json", x)), key=lambda x: int(x[4:-14])) if os.path.isdir(ROUNDS_DIR) else []
    name = f"job-{n}.put-back.json" if n else (names[-1] if names else "")
    p = os.path.join(ROUNDS_DIR, name)
    if not name or not os.path.exists(p):
        sys.exit("Nothing kept to bring back.")
    s = json.load(open(p, encoding="utf8"))
    done, missed = [], []
    with q.locked():
        text = open(q.ROADMAP, encoding="utf8").read()
        for old, new in s.get("back") or []:
            if old in text:
                text = text.replace(old, new, 1)
                done.append(new.split(" | ")[1].split(" ")[0])
            else:
                missed.append(old.split(" | ")[1].split(" ")[0])
        for line in s.get("gone") or []:
            text = text.replace(line + "\n", "", 1)
        for what, x in (("Job", s.get("jobs") or {}), ("Item", s.get("items") or {})):
            for i, line in x.items():
                text = re.sub(rf"^- {what} {i} · .*$", lambda _m, ln=line: ln, text, count=1, flags=re.M)
                done.append(f"{what.lower()} {i}")
        tmp = f"{q.ROADMAP}.keep.{os.getpid()}"
        with open(tmp, "w", encoding="utf8") as fh:
            fh.write(text)
        os.replace(tmp, q.ROADMAP)
        d, rv = _state()
        ready = d.setdefault("ready", {})
        ready.update(s.get("gained") or {})
        for k in s.get("lost") or {}:
            ready.pop(k, None)
        rv.setdefault("rows", {}).update(s.get("passed") or {})
        done += sorted(set(s.get("gained") or {}) | set(s.get("lost") or {}) | set(s.get("passed") or {}))
        d["review"] = rv
        S._save(S.RANKS, d)
    os.replace(p, p.replace(".put-back.json", ".kept.json"))
    return "Back as written: " + (", ".join(done) or "nothing") + "." + (f" Changed since, so not touched: {', '.join(missed)}; the words are in {name}." if missed else "")


def _rounds_left(log=None):
    """A look that never came, the runner killed with its round: the routine's minute does it."""
    try:
        names = [x for x in os.listdir(ROUNDS_DIR) if re.fullmatch(r"job-\d+\.json", x)]
    except OSError:
        return
    jobs_ = {j["n"]: j["state"] for j in q.read()[1]} if names else {}
    for x in names:
        n = int(x[4:-5])
        if not jobs_.get(n, "").startswith("running"):
            said = round_after(n)
            if said and log:
                log(f"review: {said} (F86)")


def sitdown(label, what, ifthen, now=None, kind="his", instead=""):
    """A finding only he can answer: on her sit-down list, the loop stops for this row, one text in if-then shape. Her no goes the same way (no)."""
    import cycles
    import ledger
    label, what, ifthen = label.strip().upper(), q.one_line(what or "").strip(), q.one_line(ifthen or "").strip()
    if not what or not re.match(r"if\b", ifthen, re.I) or "if not" not in ifthen.lower():
        sys.exit('Refused: it needs the open point and a text in if-then shape: "If ..., I\'ll ...; if not, ...".')
    now = now or _clock()
    with q.locked():
        row = next((r for r in S.open_rows() if r["label"] == label), None)
        if not row:
            sys.exit(f"{label} isn't an open row on the planning.")
        d, rv = _state()
        rs = rv.get("rows") or {}
        e = rs.setdefault(label, {})
        fp = S.ask_fp(row["line"])
        had = _stopped(e, fp)
        f = e.setdefault("fix", {})
        if not (had and had.get("kind") == "no"):  # her no stands: a sit-down after it in the same round doesn't replace it
            f["stop"] = {"ask": fp, "kind": kind, "why": what, "at": int(now), "round": f.get("n")}
            if instead:
                f["stop"]["instead"] = instead
        if kind == "no":
            (d.get("ready") or {}).pop(label, None)  # a row she said no to is no Ready row: jobs.py add goes by the mark
        rv["rows"] = rs
        d["review"] = rv
        S._save(S.RANKS, d)
    if had and had.get("kind") in ("his", "no"):
        return f"{label} was on the sit-down list already; no second text."
    ledger.note(cycles.FIX_AGENT, f"{label} on the sit-down list: " + (f"she says no: {what} Instead: {instead}" if kind == "no" else what))
    return f"{label} is on the sit-down list. " + cycles.ask(cycles.FIX_AGENT, ifthen)


def no(label, why, instead, ifthen, now=None):
    """The third way out of a round, beside improving a row and handing it to him: this can't be done as asked, or isn't worth building. The row
    stops, gets no Ready mark, and nothing else on it changes; he decides. An ending, not a failed round."""
    why, instead = q.one_line(why or "").strip(), q.one_line(instead or "").strip()
    if not why or not instead:
        sys.exit("Refused: a no says why, in one or two plain sentences, and what could work instead.")
    return sitdown(label, why, ifthen, now, kind="no", instead=instead)


def sitdown_rows(rows=None):
    """[(row, stop)] for the rows on her sit-down list, in the planning's order."""
    rows = S.open_rows() if rows is None else rows
    rs = _state()[1].get("rows") or {}
    ready = S.ready_of(rows)
    out = []
    for r in rows:
        st = _stopped(rs.get(r["label"]) or {}, S.ask_fp(r["line"]))
        if st and not (st.get("kind") == "mark" and ready.get(r["label"]) == "ready"):  # she marked it since
            out.append((r, st))
    return out


def sitdown_words(rows=None):
    sd = sitdown_rows(rows)
    since = _clock() - 7 * 86400
    after = [x for x in _state()[1].get("round_said") or [] if x.get("at", 0) > since]
    if not sd and not after:
        return ""
    return "\n".join((["ON YOUR SIT-DOWN LIST (F86): the loop stopped for these rows; each waits for his answer."] if sd else [])
                     + [f"- {r['label']} {q.one_line(r['title'])[:120]} ({STOP_WORDS.get(s.get('kind'), 'stopped')}): {s.get('why', '')}"
                        + (f" What could work instead: {s['instead']}" if s.get("instead") else "") for r, s in sd]
                     + (["WHILE A ROUND RAN, this week (F86): raise these with him. On his keep it: python3 routine/review.py keep N brings back what round N put back; the words are in .status/rounds/job-N.put-back.json."] if after else [])
                     + [f"- job {x.get('n', '?')}, around {x['label']}: {x['words']}" for x in after])


def role_writes():
    try:
        import role
        return role.WRITES.get("review", set())
    except Exception:
        return set()


# ---------- in words ----------

STATE_WORDS = {"baseline": "reviewed (taken as it was at the first start)", "passed": "the review passed it",
               "cleared": "flag taken off on his say-so", "flagged": "FLAGGED by the review",
               "waiting": "new or changed, its review is waiting", "didnt_run": "the review didn't run (tried again)"}


def flagged(rows=None):
    """[(row, state)] for the flagged open rows, in the planning's order."""
    rows = S.open_rows() if rows is None else rows
    st = states(rows)
    return [(r, st[r["label"]]) for r in rows if st[r["label"]]["state"] == "flagged"]


def flag_words(rows=None):
    """For Moneypenny's briefing (F77): the flagged rows, with the findings, to raise first; "" when none."""
    fl = flagged(rows)
    sd = sitdown_words(rows)
    if not fl:
        return sd
    out = ["FLAGGED ON THE PLANNING (F77): the automatic review found holes in these rows. Raise them first on this "
           "call, before anything else, like the mail heads-up: a sentence each, with your proposed fix; fix the row "
           "with him (its next review takes the flag off), or, on his say-so, python3 \"" + os.path.abspath(__file__)
           + "\" clear LABEL \"his words\". A flagged row can't be marked ready."]
    for r, s in fl:
        more = " (changed since; the next review looks again)" if s.get("changed") else ""
        out.append(f"- {r['label']} {q.one_line(r['title'])[:120]}{more}: " + "; ".join(s["findings"]))
    return "\n".join(out + ([sd] if sd else []))


def list_words():
    rows = S.open_rows()
    st = states(rows)
    _, rv = _state()
    sp = rv.get("spent") or {}
    head = (f"The review of the planning (F77): {sum(1 for s in st.values() if s['state'] == 'flagged')} flagged, "
            f"{sum(1 for s in st.values() if s['state'] in ('waiting', 'didnt_run'))} waiting; today's reviews "
            f"{sp.get('n', 0)}, ${sp.get('usd', 0):.2f} (no daily cap, F80).")
    lines = [head]
    for r in rows:
        s = st[r["label"]]
        line = f"- {r['label']}: {STATE_WORDS[s['state']]}"
        if s.get("findings"):
            line += ": " + "; ".join(s["findings"])
        if s.get("cleared_words"):
            line += f' (his words: "{s["cleared_words"]}")'
        lines.append(line)
    sd = sitdown_words(rows)
    return "\n".join(lines + ([sd] if sd else []))


def main(argv):
    if argv[:1] == ["add"] and len(argv) == 2:  # the words on stdin, also for a hand-over to the main
        argv = [*argv, sys.stdin.read()]
    if argv and argv[0] in role_writes():
        import role
        if not os.environ.get("HQ_ROLE_HERE") and role.is_backup():
            sys.exit(role.forward("review", list(argv)))
    if not argv or argv[0] == "list":
        print(list_words())
    elif argv[0] == "tick":
        print(", ".join(tick(log=print)) or "no review started")
    elif argv[0] == "review-run" and len(argv) == 2:
        review_run(argv[1].upper())
    elif argv[0] == "run" and len(argv) == 2:
        row = next((r for r in S.open_rows() if r["label"] == argv[1].upper()), None)
        if not row:
            sys.exit(f"{argv[1]} isn't an open row on the planning.")
        print(json.dumps(ask_reviewer(row), indent=1))
    elif argv[0] == "clear" and len(argv) == 3:
        clear(argv[1], argv[2])
        print(f"{argv[1].upper()}: the flag and any no of hers are off, his words kept with it.")
    elif argv[0] == "pass" and len(argv) == 1:
        run_pass()
    elif argv[0] == "pass-result":
        print(pass_words())
    elif argv[0] == "golden":  # F101: every golden row through the real reviewer
        sys.exit(golden())
    elif argv[0] == "fingerprint":
        print(fingerprint(), golden_current())
    elif argv[0] == "flags":
        print(flag_words() or "No flagged rows on the planning.")
    elif argv[0] == "reword" and len(argv) == 3:
        print(reword(argv[1], argv[2]))
    elif argv[0] == "add" and len(argv) == 3:
        print(addition(argv[1], argv[2]))
    elif argv[0] == "sitdown" and len(argv) == 4:
        print(sitdown(argv[1], argv[2], argv[3]))
    elif argv[0] == "keep" and len(argv) in (1, 2):
        print(keep(int(argv[1]) if len(argv) == 2 else None))
    elif argv[0] == "round-before" and len(argv) == 4:
        round_before(int(argv[1]), argv[2], argv[3])
    elif argv[0] == "round-after" and len(argv) == 2:
        print(round_after(int(argv[1])))
    elif argv[0] == "no" and len(argv) == 5:
        print(no(argv[1], argv[2], argv[3], argv[4]))
    elif argv[0] == "sitdown-list":
        print(sitdown_words() or "Nothing on the sit-down list.")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
