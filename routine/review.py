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
    burst; only what's added or changed after that is reviewed.
  - The reviewer: a small Claude run (MODEL, the lightest that does it well: Sonnet, low effort, no tools: it reads only the row it's
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
  - Usage: each review's cost is kept; when a day's reviews have cost DAY_USD (about 3% of the 5-hour, Claude's
    estimate of what that is in the dollars the run reports), the rest waits for the night (22:00 to 8).
  - On Moneypenny's calls only (her briefing, quick_context._planning), the flagged rows come first, to raise before
    anything else, like the mail heads-up; Donna's and Pepper's never see them.

usage:
  python3 routine/review.py list                 the review state of every open row
  python3 routine/review.py tick                 what the routine runs every minute (on the main)
  python3 routine/review.py clear LABEL "WORDS"  take a flag off on his say-so on a call, his words kept with it
  python3 routine/review.py run LABEL            a review now, in the foreground (a test, or by hand)
Used by the background review itself: review-run LABEL.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import estimate as E  # noqa: E402
import jobs as q  # noqa: E402
import sprint as S  # noqa: E402

# The lightest model that does it (his "low usage Claude prompt"). Tried on real rows on 28 October 2026 (job 438):
# Haiku flagged H297 as first written but missed its second stop, and flagged its whole version too; Sonnet at low
# effort found both holes and passed the whole one, about a cent a review. QA (job 450) then found that was luck: 3 of
# 5. With the probes (job 455, 29 October 2026): H297 as first written flagged 8 of 8 at low effort and 8 of 8 at
# medium, H297 as it is passed 8 of 8 at both; low named both holes every time, at about $0.008 a review.
MODEL = os.environ.get("HQ_REVIEW_MODEL") or "sonnet"
EFFORT = os.environ.get("HQ_REVIEW_EFFORT") or "low"
QUIET = int(os.environ.get("HQ_REVIEW_QUIET") or 300)  # seconds a row's ask must stay the same before it's reviewed
AT_ONCE = 1
TIMEOUT = 180  # seconds for one review
PENDING = TIMEOUT + 60  # a started review counts as on its way this long
RETRY_S = int(os.environ.get("HQ_REVIEW_RETRY") or 1800)  # a review that didn't run is tried again after this
SHOW_FAILED = 2  # from this many failures for the same words, the row says the review didn't run
BUDGET = 0.15  # dollars at most for one review (--max-budget-usd)
DAY_USD = float(os.environ.get("HQ_REVIEW_DAY_USD") or 1.2)  # about 3% of the 5-hour (Claude's estimate), then the night
NIGHT = (22, 8)
LOG = os.path.join(E.DIR, "reviews.log")
COSTS = os.path.join(E.DIR, "reviews.jsonl")  # one line per review: the row, the verdict, the cost, the seconds

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


def on():
    """Whether reviews may run here: not with HQ_REVIEW=0, and a test copy (HQ_ROADMAP) only with HQ_REVIEW_FAKE."""
    if os.environ.get("HQ_REVIEW", "1") == "0":
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


def _is_night(now=None):
    h = dt.datetime.fromtimestamp(now or time.time()).hour
    a, b = NIGHT
    return h >= a or h < b


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
    if not on() or not _state()[1].get("since"):
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
    noted, and once quiet long enough a review starts (AT_ONCE at a time, each wording once, within the day's budget).
    Rows no longer open are let go. Returns the labels a review started for."""
    now = now or _clock()
    started = []
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
                if not _is_night(now) and spent["usd"] >= DAY_USD:
                    if not rv.get("waits_night"):
                        rv["waits_night"] = int(now)
                        (log or _log)(f"review: the day's reviews cost ${spent['usd']:.2f}, the rest waits for the night (F77)")
                    break
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
        if _is_night(now) or spent["usd"] < DAY_USD:
            rv.pop("waits_night", None)
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
    """HQ_REVIEW_FAKE (tests): "auto" flags a row whose ask holds "HOLE:" (the words after it the finding) and passes
    the rest; "fail" never answers."""
    how = os.environ.get("HQ_REVIEW_FAKE")
    if how == "fail":
        return None
    ask = S.ask_of(row["line"])
    cost = float(os.environ.get("HQ_REVIEW_FAKE_COST") or 0)
    m = re.search(r"HOLE:\s*([^.|]+)", ask)
    if m:
        return {"pass": False, "findings": [m.group(1).strip()], "cost": cost, "s": 0.0, "model": "fake"}
    return {"pass": True, "findings": [], "cost": cost, "s": 0.0, "model": "fake"}


def _one(f):
    return re.sub(r"\s+", " ", str(f)).strip()[:400]


def verdict(a):
    """The reviewer's JSON to (pass, findings), or None when it's not an answer. A probe that applies with no covering
    sentence is a hole whatever its own pass says (F77's fix); its own findings come first."""
    if not isinstance(a, dict) or not isinstance(a.get("pass"), bool):
        return None
    fs = [_one(f) for f in (a.get("findings") or []) if str(f).strip()]
    for p in a.get("probes") or []:
        if not isinstance(p, dict) or p.get("applies") is not True:
            continue
        cov = p.get("covered")
        if isinstance(cov, str) and cov.strip():
            continue
        h = _one(p.get("hole") or f"the {p.get('probe', 'a')} probe applies and nothing in the item covers it")
        if h and h not in fs:
            fs.append(h)
    ok = a["pass"] and not fs
    if not ok and not fs:
        fs = ["the reviewer flagged it without saying why"]
    return ok, ([] if ok else fs[:5])


def ask_reviewer(row):
    """The reviewer's answer: {"pass", "findings", "cost" (dollars), "s", "model"}, or None when it didn't run."""
    if os.environ.get("HQ_REVIEW_FAKE"):
        return _fake(row)
    try:
        import hqpaths
        claude = hqpaths.tool("claude", "/opt/homebrew/bin/claude")
    except Exception:
        claude = "claude"
    t0 = time.time()
    try:
        p = subprocess.run([claude, "-p", "--model", MODEL, "--output-format", "json", "--tools", "",
                            "--strict-mcp-config", "--setting-sources", "", "--effort", EFFORT,
                            "--max-budget-usd", str(BUDGET), "--no-session-persistence", "--system-prompt", SYSTEM],
                           input=_input(row), capture_output=True, text=True, timeout=TIMEOUT, cwd=E.ROOT)
        d = json.loads(p.stdout)
        found = re.findall(r"\{.*\}", d.get("result") or "", re.S)
        a = json.loads(found[-1])
        v = verdict(a)
        if v is None:
            return None
        ok, fs = v
        return {"pass": ok, "findings": fs, "cost": d.get("total_cost_usd"),
                "s": round(time.time() - t0, 1), "model": MODEL + " " + EFFORT}
    except Exception:
        return None


def review_run(label, now_fn=_clock):
    """In the background: the review itself, outside the lock; its verdict is written only when the row's ask is still
    the one it read (changed in between: the next minute's tick starts the next one)."""
    def now_row():
        return next((r for r in S.open_rows() if r["label"] == label), None)
    with q.locked():
        r = now_row()
    if not r:
        return None
    fp = S.ask_fp(r["line"])
    a = ask_reviewer(r)
    lost = False
    with q.locked():
        d, rv = _state()
        rs = rv.get("rows") or {}
        e = rs.get(label)
        if e is None:
            return None
        e.pop("pending", None)
        now = int(now_fn())
        r2 = now_row()
        if a is None:
            tries = e.get("tries") or [None, 0]
            e["tries"] = [fp, (tries[1] if tries[0] == fp else 0) + 1]
            e["next_try"] = now + RETRY_S
        elif r2 and S.ask_fp(r2["line"]) == fp:
            e.update({"ask": fp, "verdict": "pass" if a["pass"] else "flag", "findings": a["findings"], "at": now,
                      "cost": a.get("cost"), "s": a.get("s"), "model": a.get("model")})
            e.pop("tries", None)
            e.pop("next_try", None)
            e.pop("cleared_words", None)
            if not a["pass"]:
                marks = d.get("ready") or {}
                if label in marks:  # a row that gets the flag loses its Ready mark
                    marks.pop(label)
                    d["ready"] = marks
                    lost = True
        if a is not None:
            sp = rv.get("spent") or {}
            if sp.get("day") != _today(now):
                sp = {"day": _today(now), "usd": 0.0, "n": 0}
            if not _is_night(now):
                sp["usd"] = round(sp["usd"] + float(a.get("cost") or 0), 4)
            sp["n"] = sp.get("n", 0) + 1
            rv["spent"] = sp
        rs[label] = e
        rv["rows"] = rs
        d["review"] = rv
        S._save(S.RANKS, d)
    rec = {"row": label, "at": int(now_fn()), "fp": fp}
    rec.update({"verdict": "pass" if a["pass"] else "flag", "findings": len(a["findings"]), "cost": a.get("cost"),
                "s": a.get("s"), "model": a.get("model")} if a else {"failed": True})
    try:
        os.makedirs(E.DIR, exist_ok=True)
        with open(COSTS, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        pass
    _log(f"review {label}: " + ("didn't run" if a is None else ("passed" if a["pass"] else "flagged: " + "; ".join(a["findings"])))
         + (" (its Ready mark taken off)" if lost else "") + (f", ${a['cost']:.4f}" if a and a.get("cost") else ""))
    return a


def clear(label, words):
    """His say-so on a call: the flag off, his words kept with the row (in sprint.json, outside the ask)."""
    label = label.strip().upper()
    words = q.one_line(words or "").strip()
    if not words:
        sys.exit("Clearing a flag needs his words, as he said them on the call.")
    with q.locked():
        row = next((r for r in S.open_rows() if r["label"] == label), None)
        if not row:
            sys.exit(f"{label} isn't an open row on the planning.")
        d, rv = _state()
        rs = rv.get("rows") or {}
        e = rs.get(label) or {}
        if e.get("verdict") != "flag":
            sys.exit(f"{label} has no flag to take off.")
        e.update({"ask": S.ask_fp(row["line"]), "verdict": "cleared", "at": int(_clock()),
                  "cleared_words": words, "cleared_findings": e.get("findings") or []})
        e["findings"] = []
        rs[label] = e
        rv["rows"] = rs
        d["review"] = rv
        S._save(S.RANKS, d)
    return e


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
    if not fl:
        return ""
    out = ["FLAGGED ON THE PLANNING (F77): the automatic review found holes in these rows. Raise them first on this "
           "call, before anything else, like the mail heads-up: a sentence each, with your proposed fix; fix the row "
           "with him (its next review takes the flag off), or, on his say-so, python3 \"" + os.path.abspath(__file__)
           + "\" clear LABEL \"his words\". A flagged row can't be marked ready."]
    for r, s in fl:
        more = " (changed since; the next review looks again)" if s.get("changed") else ""
        out.append(f"- {r['label']} {q.one_line(r['title'])[:120]}{more}: " + "; ".join(s["findings"]))
    return "\n".join(out)


def list_words():
    rows = S.open_rows()
    st = states(rows)
    _, rv = _state()
    sp = rv.get("spent") or {}
    head = (f"The review of the planning (F77): {sum(1 for s in st.values() if s['state'] == 'flagged')} flagged, "
            f"{sum(1 for s in st.values() if s['state'] in ('waiting', 'didnt_run'))} waiting; today's reviews "
            f"{sp.get('n', 0)}, ${sp.get('usd', 0):.2f} of ${DAY_USD:.2f} by day.")
    lines = [head]
    for r in rows:
        s = st[r["label"]]
        line = f"- {r['label']}: {STATE_WORDS[s['state']]}"
        if s.get("findings"):
            line += ": " + "; ".join(s["findings"])
        if s.get("cleared_words"):
            line += f' (his words: "{s["cleared_words"]}")'
        lines.append(line)
    return "\n".join(lines)


def main(argv):
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
        print(f"{argv[1].upper()}: the flag is off, his words kept with it.")
    elif argv[0] == "flags":
        print(flag_words() or "No flagged rows on the planning.")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
