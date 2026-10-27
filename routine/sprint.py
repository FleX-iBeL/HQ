#!/usr/bin/env python3
"""H269: sprint planning: the rank and the estimate on every open row of the planning (piece 1), and the sprint view
with Plan the sprint (piece 2), 25 October 2026.
In the user's words (call of 25 October 2026, 02:23): "just like a real scrum sprint, we should rank the planning somehow
and also have the items with estimation on time and usage and then be able to actual plan them and see how much space
we have where ... This is super important or we cant start a sprint".

The planning is the roadmap's open rows (⬜) in its "## Phase" tables, not the parked ones (Phase P) and not the
repeating ones (🔁, Maintenance).

  - The rank: a place in line for each row, 1 the top, kept in the workspace's HQ/sprint.json (next to the roadmap, so
    it syncs with it), never in the row itself. Set on a call or at the sprint (rank LABEL N|top|bottom|off): the row
    goes to that place and the rows from there move down one. A row added to the planning has no rank until it's given
    one, so the others keep theirs; a row that's done, parked or gone drops out and the ones below move up. Unranked
    rows come after the ranked ones, in the roadmap's order. On the backup a rank goes to the main (role.WRITES), so
    only one HQ writes the file (role.ONE_WRITER).
  - The estimate: time and usage (the 5-hour and the weekly), made the same way as for the team's work: the row as the
    job it would become (the words "Send to the team" gives it, jobs.py send-row), its kind (kind_of on the row), its
    size with the material it names (estimate.look), the finished jobs like it, and the first look (Haiku, H190) once
    it's back. Kept in this computer's .status/sprint-estimates.json. refresh(), every minute on the main from tick.py,
    makes the size again and starts a new look when a row's words change (estimate.fingerprint: the job's words and the
    row's, without the result column), never on a move or a rank change. At most LOOKS_AT_ONCE looks run at once, so
    the first time the planning's rows are looked at one after another.

  - The sprint (piece 2): the rows ticked for this sprint fall into the coming nights in rank order (lay). The team's
    room is every night from 22:00 to 8 in the morning (H269 point 8, his "Yes it's good"). The work already with the
    team or planned goes first (its times and usage from estimate.plan); a repeating item takes its minutes off the
    night it falls in. Each row starts once the one before it is done and its usage fits under the 5-hour and weekly
    stop lines (usagecost.Projection, the same as the team's own times); a row that would end after 8 goes to the next
    night, unless the night is still empty (a row longer than a night then has the night to itself). A row the usage
    pushes out of the night it would have fallen in, or that finds no room in the nights looked at, is past the room:
    the line goes before the first one. Plan the sprint (plan) puts the ticked rows on the schedule for the team in
    that order, each at its night's 22:00 (a minute apart, so they keep their order), as a call planning them would;
    a row already with the team or planned is left out and said. On the backup it goes to the main (role.WRITES).

usage:
  python3 routine/sprint.py list                       the planning in rank order, each with its estimate (a call reads this)
  python3 routine/sprint.py json                       the same as JSON (the status server shows it)
  python3 routine/sprint.py rank LABEL N|top|bottom|off  give row LABEL a place (1 the top), or take its rank away
  python3 routine/sprint.py moscow LABEL must|should|could|wont|off  its MoSCoW tag for the sprint (H271), or none
  python3 routine/sprint.py ready LABEL [on|off]          its Ready mark (H272): only rows marked ready go to the team
  python3 routine/sprint.py check LABEL...             why a row isn't ready (the points it seems to miss), or that it is
  python3 routine/sprint.py lay LABEL... [--night D]     the sprint: the rows, in rank order, laid over the nights from
                                                        night D (tonight, tomorrow, a weekday or 2026-10-26; tonight
                                                        when left out); --json for the status page
  python3 routine/sprint.py plan LABEL... [--night D]    Plan the sprint: those rows planned for the team in that order
  python3 routine/sprint.py refresh                    the sizes and the looks for rows whose words changed (the routine does it)
Used by the background look itself: look-run LABEL.

H271 (25 October 2026, call at 11:31), in the user's words: "i want moneypenny to prioritize bugs always over features
... (all of it is to avoid tech debt as a whole ...) then i was thinking maybe we can sort our sprint planning with
moscow method ... and then color code each step, so its a clear overview." Each open row can carry a MoSCoW tag
(Must, Should, Could, Won't this time), kept next to the rank in sprint.json ("moscow"), set on a call or in the sprint
view (moscow LABEL TAG|off), dropped like the rank when the row is no longer open. The planning is shown and laid in
groups: Must, Should, Could, then the rows not sorted yet, then Won't; inside each group the bugs first (a row in the
Bugs phase, F on this roadmap), then the rank, then the roadmap's order. Bugs before features is how HQ keeps its
tech debt down.
"""
import hashlib, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import estimate as E  # noqa: E402
import jobs as q  # noqa: E402

RANKS = os.environ.get("HQ_SPRINT") or os.path.join(os.path.dirname(q.ROADMAP), "sprint.json")
ESTS = os.path.join(E.DIR, "sprint-estimates.json")
LOOKS_AT_ONCE = 1  # Claude's choice: one look at a time, so the first pass over the planning stays light


# ---------- the planning's open rows ----------

def open_rows(text=None):
    """The open rows of the planning, in the roadmap's order: [{"label", "title", "line", "phase"}]."""
    if text is None:  # Fable, 27 October 2026: from the planning index when it's on and as new as the file
        try:
            import planning_index
            got = planning_index.open_rows()
            if got is not None:
                return got
        except Exception:
            pass
    text = q.read()[0] if text is None else text
    out, phase = [], ""
    for line in text.split("\n"):
        if line.startswith("## "):
            phase = line
            continue
        if not phase.startswith("## Phase ") or phase.startswith("## Phase P ") or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 2 or cells[0] != "⬜":
            continue
        head = cells[1].split(" ", 1)
        if not re.fullmatch(r"[A-Z]\d+(\.\d+)*", head[0]):
            continue
        out.append({"label": head[0], "title": head[1].strip() if len(head) > 1 else head[0], "line": line,
                    "phase": phase[9:].split(" ·", 1)[0],
                    "phase_title": phase[9:].strip()})
    return out


STATES = {"⬜": "open", "✅": "done", "🔨": "being built", "🔁": "repeats"}
SHOW_MOST = 12000  # about one of the biggest rows; past that the rest is pointed at, never the whole planning


def row_of(label, text=None):
    """Any row of the roadmap with this label, open or closed, in any phase (Fable clean-up, 27 October 2026):
    {"label", "title", "state", "phase", "cells", "line", "n"} (n: its line number), or None."""
    if text is None:  # Fable, 27 October 2026: by its place in the file, from the planning index, when it can be used
        try:
            import planning_index
            got = planning_index.row(label)
            if got is not None:
                return None if got.get("missing") else got
        except Exception:
            pass
    text = q.read()[0] if text is None else text
    label = label.strip().upper()
    phase = ""
    for n, line in enumerate(text.split("\n"), 1):
        if line.startswith("## "):
            phase = line[3:].strip()
            continue
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 2:
            continue
        head = cells[1].split(" ", 1)
        if head[0] != label:
            continue
        return {"label": label, "title": head[1].strip() if len(head) > 1 else "", "state": cells[0],
                "phase": phase, "cells": cells[2:], "line": line, "n": n}
    return None


def show_words(labels, text=None):
    """`show LABEL …` (Fable clean-up, 27 October 2026): one row's cells, plainly, so a call never reads or greps the
    whole planning (over 1 MB: a whole read killed the call's line, F60) to see one row, open or closed."""
    text = q.read()[0] if text is None else text
    out = []
    for label in labels:
        r = row_of(label, text)
        if r is None:
            out.append(f"{label.strip().upper()} isn't a row on the planning.")
            continue
        s = f"{r['label']} ({STATES.get(r['state'], r['state'] or 'no mark')}; {r['phase']}): {r['title']}"
        for i, c in enumerate(r["cells"], 1):
            if c:
                s += f"\n\n[{i}] {c}"
        if len(s) > SHOW_MOST:
            s = s[:SHOW_MOST] + (f"\n\n[… {len(s) - SHOW_MOST:,} more characters. The whole row is line {r['n']} of "
                                 f"the roadmap: sed -n {r['n']}p HQ/roadmap.md | cut -c{SHOW_MOST}-{SHOW_MOST + 8000}]")
        out.append(s)
    return "\n\n".join(out)


def open_words(text=None):
    """`open` (H288, Fable clean-up): the open items only, one line each, with their tag, mark, rank and whether it's a
    bug; a closed one only when asked for by name (show). Small enough to load at a call's start."""
    rows = open_rows(text)
    tags, readies, ranked = moscow_of(rows), ready_of(rows), order(rows)
    out = [f"{len(rows)} open items on the planning (one row whole: sprint.py show LABEL; closed rows the same way):"]
    for r in rows:
        bits = [MOSCOW_NAMES[tags[r["label"]]]] if r["label"] in tags else []
        bits.append({"ready": "ready", "changed": "changed since ready"}.get(readies.get(r["label"]), "not ready"))
        if r["label"] in ranked:
            bits.append(f"rank {ranked.index(r['label']) + 1}")
        if is_bug(r):
            bits.append("bug")
        out.append(f"- {r['label']} ({', '.join(bits)}): {q.one_line(r['title'])[:160]}")
    return "\n".join(out)


def job_text(label, title):
    """The row as the job it would become, the same words jobs.py send-row gives it."""
    title = q.one_line(title).replace("·", "-").rstrip(".")
    return (f"{label} on the HQ roadmap, sent to the team from the status page: {title}. Read the {label} row "
            f"and do what it says. Pull dev first, privacy check, push to dev with push.py, write the result in the {label} row.")


# ---------- the rank ----------

def _load(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}


def _save(path, d):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=1)
        f.write("\n")
    os.replace(tmp, path)


MOSCOW = ("must", "should", "could", "wont")
MOSCOW_NAMES = {"must": "Must", "should": "Should", "could": "Could", "wont": "Won't this time", None: "Not sorted yet"}
GROUPS = ("must", "should", "could", None, "wont")  # the order the groups are shown and laid in


def is_bug(row):
    """A bug: a row in the roadmap's Bugs phase (Phase F, or a phase called Bugs), or an F row (HQ's letter for a bug,
    jobs.roadmap_row) wherever it stands, or feedback sent as a bug (H247: "| A bug from …" in its row)."""
    ph = (row.get("phase_title") or row.get("phase") or "")
    return (ph.split(" ", 1)[0] == "F" or "bug" in ph.lower() or str(row.get("label", "")).startswith("F")
            or "| A bug from " in (row.get("line") or ""))


def moscow_of(rows=None):
    """{label: tag} for the open rows that have one."""
    rows = open_rows() if rows is None else rows
    have = {r["label"] for r in rows}
    m = _load(RANKS).get("moscow") or {}
    return {l: t for l, t in m.items() if l in have and t in MOSCOW}


def _tag(word):
    w = re.sub(r"[^a-z]", "", str(word).lower())
    w = {"m": "must", "s": "should", "c": "could", "w": "wont", "wont": "wont", "wonthistime": "wont",
         "none": "off", "clear": "off", "remove": "off"}.get(w, w)
    if w not in MOSCOW + ("off",):
        sys.exit("A MoSCoW tag is must, should, could, wont, or off.")
    return w


def set_moscow(label, word):
    """Row LABEL's MoSCoW tag, or off. Returns the tag (None for off). Exits with why."""
    label = label.strip().upper()
    rows = open_rows()
    if label not in {r["label"] for r in rows}:
        sys.exit(f"{label} isn't an open row on the planning (done, parked, repeating or not there), so it gets no tag.")
    t = _tag(word)
    d = _load(RANKS)
    m = {l: v for l, v in (d.get("moscow") or {}).items() if l in {r["label"] for r in rows}}
    if t == "off":
        m.pop(label, None)
    else:
        m[label] = t
    d["moscow"] = m
    d["set"] = int(time.time())
    _save(RANKS, d)
    return None if t == "off" else t


# ---------- the Ready mark (H272) ----------

# H272 (25 October 2026, call at 12:36), in the user's words: "Btw can items pass through if they are not checked? How do
# we know you and i decided they pass the ready for sprint?" Each open row can carry a Ready mark, kept next to its rank
# and MoSCoW tag in sprint.json ("ready": {label: {"fp", "at"}}), never in the row: set and taken off on a call (once
# the nine points are filled in with him) and with a tick in the sprint view. The mark holds the row's words as they
# were (fp); when they change after, the row says "changed since ready" until it's marked again. Plan the sprint and
# Send to the team refuse a row without a mark that still holds, and say which point seems to be missing; a call can
# still give one to the team on the user's explicit say-so (jobs.py or schedule.py add --not-ready), and the job then
# says it went without the mark. Which points a row seems to miss is only a hint from its words (the full check of the
# nine points is the weekly ready review, H273), never a reason to set or take off the mark.

READY_POINTS = (  # (the words for a missing point, what in a row's words says it's there)
    ("what's asked", r"what'?s asked|what is asked|\b1\. "),
    ("what done means", r"done means|\bdone is\b"),
    ("test", r"\btests?\b|\bflows?\b"),
    ("why", r"\bwhy\b"),
    ("out of scope", r"out of scope"),
    ("what it touches", r"\btouches\b"),
    ("size", r"\bsize\b|small build|big build|one night"),
    ("what it waits on", r"waits on"),
    ("privacy check", r"privacy"),
)
BUG_POINTS = (  # a small bug fix is ready with what's wrong, what right looks like and how to check
    ("what's wrong", r"wrong|broken|breaks|fails|doesn'?t|isn'?t|bug"),
    ("what right looks like", r"right looks like|should|expected|instead"),
    ("how to check", r"how to check|\bcheck\b|\btest"),
)


def row_words_fp(line):
    """The row's words, without its mark and its result column: what the Ready mark holds on to."""
    cells = [c.strip() for c in line.split("|")[1:-1]]
    return _fp(" | ".join(cells[1:4]))


def ready_of(rows=None):
    """{label: "ready" | "changed"} for the open rows with a mark: ready while the words are the ones it was given on,
    changed when they've changed since."""
    rows = open_rows() if rows is None else rows
    marks = _load(RANKS).get("ready") or {}
    out = {}
    for r in rows:
        m = marks.get(r["label"])
        if isinstance(m, dict):
            out[r["label"]] = "ready" if m.get("fp") == row_words_fp(r["line"]) else "changed"
    return out


def missing_points(row):
    """The points the row's words don't seem to have (a hint only, H273 checks them properly)."""
    text = row["line"].lower()
    pts = BUG_POINTS if is_bug(row) and str(row.get("label", "")).startswith("F") else READY_POINTS
    return [name for name, pat in pts if not re.search(pat, text)]


def not_ready_why(row, state=None):
    """Why a row isn't ready, in a few plain words, or None when it is: "H257 isn't ready: no out of scope, no size"."""
    state = ready_of([row]).get(row["label"]) if state is None else state
    if state == "ready":
        return None
    if state == "changed":
        return f"{row['label']} isn't ready: its words changed since it was marked ready, so it needs the mark again"
    miss = missing_points(row)
    if len(miss) == len(BUG_POINTS if row["label"].startswith("F") and is_bug(row) else READY_POINTS):
        return f"{row['label']} isn't ready: none of its ready points are written in it yet"
    if miss:
        return f"{row['label']} isn't ready: no {', no '.join(miss)}"
    return f"{row['label']} isn't ready: it isn't marked ready yet (its points seem to be there, it only needs the mark)"


def set_ready(label, on=True):
    """Row LABEL's Ready mark on (on its words as they are now) or off. Returns True for on. Exits with why."""
    label = label.strip().upper()
    rows = open_rows()
    row = next((r for r in rows if r["label"] == label), None)
    if not row:
        sys.exit(f"{label} isn't an open row on the planning (done, parked, repeating or not there), so it gets no Ready mark.")
    d = _load(RANKS)
    have = {r["label"] for r in rows}
    m = {l: v for l, v in (d.get("ready") or {}).items() if l in have}
    if on:
        m[label] = {"fp": row_words_fp(row["line"]), "at": int(time.time())}
    else:
        m.pop(label, None)
    d["ready"] = m
    d["set"] = int(time.time())
    _save(RANKS, d)
    return bool(on)


def _onoff(word):
    w = re.sub(r"[^a-z]", "", str(word or "on").lower())
    if w in ("on", "yes", "ready", "set", "mark"):
        return True
    if w in ("off", "no", "notready", "unset", "remove", "clear"):
        return False
    sys.exit("The Ready mark is on or off.")


def named_open_rows(text, job_text_):
    """The open planning rows a job's words name the way a job reads its row ("LABEL on the HQ roadmap", "the LABEL
    row"), as jobs.with_team counts them; another label mentioned in passing doesn't count."""
    out = []
    for r in open_rows(text):
        l = re.escape(r["label"])
        if re.search(rf"(?<![\w.]){l} on the (hq )?roadmap\b|\bthe {l} row\b", job_text_, re.I):
            out.append(r)
    return out


def gate(text, job_text_, say_so=False):
    """H272, for a call adding work for the team (jobs.py add, schedule.py add): the open rows it names must be ready.
    Returns the job's words to use (with a line that it went without the mark, on the say-so); exits with why when a
    row isn't ready and there's no say-so."""
    rows = named_open_rows(text, job_text_)
    if not rows:
        return job_text_
    states = ready_of(rows)
    whys = [w for w in (not_ready_why(r, states.get(r["label"])) for r in rows) if w]
    if not whys:
        return job_text_
    if not say_so:
        sys.exit("; ".join(whys) + ". Only rows marked ready go to the team; mark it ready first "
                 "(sprint.py ready LABEL), or, on his explicit say-so, add it with --not-ready.")
    labels = ", ".join(r["label"] for r in rows if states.get(r["label"]) != "ready")
    return (job_text_.rstrip() + f" It went to the team without the Ready mark ({labels}), on the explicit say-so "
            "on the call; check the row's points before building.")


def group_key(x, roadmap_place):
    """How a row sorts in the sprint view: its MoSCoW group, bugs first, its rank, the roadmap's order."""
    return (GROUPS.index(x.get("moscow")), not x.get("bug"), x["rank"] is None, x["rank"] or 0,
            roadmap_place.get(x["label"], 0))


def order(rows=None):
    """The ranked labels, top first, only the rows still open."""
    rows = open_rows() if rows is None else rows
    have = {r["label"] for r in rows}
    return [l for l in (_load(RANKS).get("order") or []) if l in have]


def set_rank(label, place):
    """Row LABEL to place (an int from 1, 'top', 'bottom') or 'off'. Returns the new order. Exits with why."""
    label = label.strip().upper()
    rows = open_rows()
    if label not in {r["label"] for r in rows}:
        sys.exit(f"{label} isn't an open row on the planning (done, parked, repeating or not there), so it gets no rank.")
    ranked = [l for l in order(rows) if l != label]
    p = str(place).strip().lower()
    if p != "off":
        if p == "top":
            i = 0
        elif p == "bottom":
            i = len(ranked)
        elif re.fullmatch(r"\d+", p) and int(p) >= 1:
            i = min(int(p), len(ranked) + 1) - 1
        else:
            sys.exit("A rank is a number from 1 (the top), top, bottom, or off.")
        ranked.insert(i, label)
    d = _load(RANKS)
    d.update({"order": ranked, "set": int(time.time())})  # H271: the MoSCoW tags stay
    _save(RANKS, d)
    return ranked


# ---------- the estimate ----------

def _fp(text):
    return E.fingerprint(text)


def refresh(log=None, start_looks=True):
    """The size made again for a row whose words changed (or that has none yet), and a first look started for it, at
    most LOOKS_AT_ONCE at a time; never for a move or a rank change. Rows no longer open are let go. Returns what it
    started."""
    started = []
    with q.locked():
        rows = open_rows()
        d = _load(ESTS)
        have = {r["label"] for r in rows}
        for k in [k for k in d if k not in have]:
            d.pop(k)
        for r in rows:
            t = job_text(r["label"], r["title"])
            fp = _fp(t)
            e = d.get(r["label"]) or {}
            if e.get("fp") != fp:
                e.update({"fp": fp, "kind": E.kind_of(r["line"]), "size": E.look(E._about(t)), "set": int(time.time())})
                d[r["label"]] = e
        pending = [k for k, e in d.items() if time.time() - (e.get("look_pending") or 0) < E.LOOK_PENDING]
        if start_looks and E.look_on():
            for r in rows:
                if len(pending) >= LOOKS_AT_ONCE:
                    break
                e = d[r["label"]]
                if e.get("look_fp") == e["fp"] or r["label"] in pending:
                    continue
                tried = e.get("look_try") or [None, 0]
                if tried[0] == e["fp"] and tried[1] >= E.LOOK_TRIES:
                    continue
                e["look_try"] = [e["fp"], (tried[1] if tried[0] == e["fp"] else 0) + 1]
                e["look_pending"] = int(time.time())
                try:
                    os.makedirs(E.DIR, exist_ok=True)
                    out = open(E.LOOK_LOG, "a")
                    subprocess.Popen([sys.executable, os.path.abspath(__file__), "look-run", r["label"]], cwd=E.ROOT,
                                     stdin=subprocess.DEVNULL, stdout=out, stderr=out, start_new_session=True)
                    pending.append(r["label"])
                    started.append(r["label"])
                except Exception as ex:
                    e.pop("look_pending", None)
                    print(f"(the look couldn't start: {ex!r})", file=sys.stderr)
        _save(ESTS, d)
    if started and log:
        log(f"sprint: a first look for {', '.join(started)} on the planning (H269)")
    return started


def look_run(label):
    """In the background: the look itself, outside the lock; written only when the row's words are still the ones it read."""
    def now_row():
        return next((r for r in open_rows() if r["label"] == label), None)
    with q.locked():
        r = now_row()
    if not r:
        return None
    t = job_text(r["label"], r["title"])
    fp = _fp(t)
    kind = (_load(ESTS).get(label) or {}).get("kind")
    g = E.look_guess(t, kind)
    with q.locked():
        d = _load(ESTS)
        e = d.get(label)
        if e is None:
            return None
        e.pop("look_pending", None)
        r2 = now_row()
        if g and r2 and _fp(job_text(r2["label"], r2["title"])) == fp:
            e.update({"guess_look": g["min"], "look_at": int(time.time()), "look_fp": fp, "look_cost": g.get("cost"),
                      "look_s": g.get("s"), "look_why": g.get("why")})
            if e.get("kind") in E.BUILDS:  # H215: the first look's minutes say a build's size
                e["kind"] = E.build_size(t, g["min"])
        d[label] = e
        _save(ESTS, d)
    E._append_look({"what": "row", "n": label, "at": int(time.time()), "fp": fp,
                    **({"min": g["min"], "cost": g.get("cost"), "s": g.get("s"), "why": g.get("why")} if g else {"failed": True})})
    print(f"{time.strftime('%Y-%m-%d %H:%M')} look row {label}: " + (f"{g['min']} min" if g else "failed"))
    return g


def plan():
    """The planning in rank order with each row's estimate: {"rows": [...], "ranked": N}."""
    import usagecost as U
    rows = open_rows()
    ranked = order(rows)
    place = {l: i + 1 for i, l in enumerate(ranked)}
    tags = moscow_of(rows)  # H271
    readies = ready_of(rows)  # H272
    roadmap_place = {r["label"]: i for i, r in enumerate(rows)}
    d = _load(ESTS)
    hist = E.all_history()
    fits = E.guess_fits(hist)
    try:
        text, jobs, _ = q.read()
    except Exception:
        text, jobs = "", []
    items = _waiting_items(text)
    out = []
    for r in rows:
        t = job_text(r["label"], r["title"])
        e = d.get(r["label"]) or {}
        fresh = e.get("fp") == _fp(t)
        kind = e.get("kind") if fresh else E.kind_of(r["line"])
        size = e.get("size") if fresh else E.look(E._about(t))
        det = E.estimate_detail(t, hist, kind, size=size)
        computed = det["est"]
        ge = e if fresh and e.get("look_fp") == e.get("fp") else {}
        guess, gkey, gf = E.pick_guess(ge, fits)
        est = E.with_guess(computed, guess, gf)
        x = {"label": r["label"], "title": r["title"], "phase": r["phase"], "rank": place.get(r["label"]),
             "est": est, "kind": det["kind"], "moscow": tags.get(r["label"]), "bug": is_bug(r),
             "ready": readies.get(r["label"])}
        if readies.get(r["label"]) != "ready":
            x["not_ready"] = not_ready_why(r, readies.get(r["label"]))
        if est != computed:
            x.update({"computed": computed, "guess_used": gkey})
        if ge.get("guess_look"):
            x["guess_look"] = ge["guess_look"]
        if e.get("look_pending") and time.time() - e["look_pending"] < E.LOOK_PENDING:
            x["looking"] = True
        try:
            c = U.cost_for(est, t, det["kind"], hist)
            x["cost"] = {k: c[k] for k in U.KEYS}
            x["cost_how"] = c["how"]
        except Exception:
            pass
        j = q.with_team(jobs, r["label"])
        if j:
            x["team"] = j["n"]
        i = planned_item(items, r["label"])  # piece 2: already planned for the team
        if i:
            x["planned"] = {"n": i["n"], "at": i["at"]}
        out.append(x)
    out.sort(key=lambda x: group_key(x, roadmap_place))  # H271: Must first, bugs first in each group, then the rank
    counts = {MOSCOW_NAMES[g]: sum(1 for x in out if x.get("moscow") == g) for g in GROUPS}
    return {"rows": out, "ranked": len(ranked), "tagged": len(tags), "groups": counts,
            "ready": sum(1 for v in readies.values() if v == "ready"), "totals": totals(out)}


TOTAL_PARTS = (("not_ready", "Not ready"), ("ready", "Ready, not planned yet"), ("planned", "Planned"), ("total", "Total"))


def part_of(x):
    """H275: which total a planning row counts in: planned (with the team, or planned for a night), else ready (its
    Ready mark on and its words unchanged since), else not ready. Ready never counts what's planned, so the three add up."""
    if x.get("team") or x.get("planned"):
        return "planned"
    return "ready" if x.get("ready") == "ready" else "not_ready"


def totals(rows):
    """H275: the planning's totals, the way the job list shows its own: per part (not ready, ready and not yet
    planned, planned) and in all, how many rows, the minutes and the share of the 5-hour and the weekly."""
    t = {k: {"count": 0, "minutes": 0, "five": 0.0, "weekly": 0.0} for k, _ in TOTAL_PARTS}
    for x in rows:
        for k in (part_of(x), "total"):
            t[k]["count"] += 1
            t[k]["minutes"] += x.get("est") or 0
            for c in ("five", "weekly"):
                t[k][c] += (x.get("cost") or {}).get(c) or 0
    for v in t.values():
        v["five"], v["weekly"] = round(v["five"], 1), round(v["weekly"], 1)
    return t


def total_words(t):
    """H275: one total in words: "6 rows, about 2 h, 5-hour 40%, weekly 9%"."""
    s = f"{t['count']} {'row' if t['count'] == 1 else 'rows'}"
    if t["count"]:
        s += f", about {E.dur(t['minutes'])}, 5-hour {E._pct(t['five'])}, weekly {E._pct(t['weekly'])}"
    return s


def row_words(x):
    """One row's estimate in words: "about 40 min, 5-hour 12%, weekly 3%"."""
    s = f"about {E.dur(x['est'])}"
    if x.get("guess_look"):
        s += f" (the first look guessed {E.dur(x['guess_look'])})"
    elif x.get("looking"):
        s += " (a first look is on its way)"
    c = x.get("cost")
    if c:
        s += f", 5-hour {E._pct(c.get('five') or 0)}, weekly {E._pct(c.get('weekly') or 0)}"
    return s


def words(p):
    lines, g = [], object()
    for x in p["rows"]:
        if x.get("moscow") != g:
            g = x.get("moscow")
            lines.append(f"{MOSCOW_NAMES[g]}:")
        where = (f"{x['rank']}." if x["rank"] else "unranked:") + (" (bug)" if x.get("bug") else "")
        team = (f" (with the team: job {x['team']})" if x.get("team") else
                f" (planned for the team: item {x['planned']['n']}, {x['planned']['at']})" if x.get("planned") else "")
        mark = {"ready": " [ready]", "changed": " [changed since ready]"}.get(x.get("ready"), " [not ready]")  # H272
        lines.append(f"{where} {x['label']} {q.one_line(x['title'])[:90]}: {row_words(x)}{team}{mark}")
    if not lines:
        return "Nothing open on the planning."
    head = (f"The planning, {len(p['rows'])} open rows, {p['ranked']} ranked, {p.get('tagged', 0)} with a MoSCoW tag, {p.get('ready', 0)} marked ready; "
            "grouped Must, Should, Could, not sorted yet, Won't, bugs first in each (estimate):")
    t = p.get("totals")
    if t:  # H275
        head += "\nTotals: " + "; ".join(f"{name}: {total_words(t[k])}" for k, name in TOTAL_PARTS) + "."
    return "\n".join([head] + lines)


# ---------- the sprint (piece 2) ----------

def _room():
    """The team's room in a sprint: (from hour, to hour), every night from 22:00 to 8 in the morning (H269 point 8).
    HQ_SPRINT_ROOM ("22-23") narrows it for a test."""
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})", (os.environ.get("HQ_SPRINT_ROOM") or "").strip())
    return (int(m.group(1)), int(m.group(2))) if m else (22, 8)


def _now():
    try:
        return float(os.environ["HQ_SPRINT_NOW"])  # a test's own clock
    except (KeyError, ValueError):
        return time.time()


NIGHTS = 14  # how many nights the sprint looks ahead at most (Claude's choice)
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def night_of(word=None, now=None):
    """The day a night starts on, from his words: tonight (also left out), tomorrow, a weekday (the next one, today
    counting), or 2026-10-26. Exits with why for anything else, or a night that has already ended."""
    import datetime as dt
    now = _now() if now is None else now
    today = dt.date.fromtimestamp(now)
    w = (word or "tonight").strip().lower()
    if w in ("tonight", "today"):
        d = today
    elif w == "tomorrow":
        d = today + dt.timedelta(days=1)
    elif w in DAYS:
        d = today + dt.timedelta(days=(DAYS.index(w) - today.weekday()) % 7)
    else:
        try:
            d = dt.date.fromisoformat(w)
        except ValueError:
            sys.exit("A night is tonight, tomorrow, a weekday, or a date like 2026-10-26.")
    a, b = _night(d)
    if b <= now:
        sys.exit(f"The night of {d.isoformat()} has already ended. Pick tonight or a night ahead.")
    return d


def _night(d):
    """The room of the night that starts on day d, as (start, end) epoch seconds."""
    import datetime as dt
    h0, h1 = _room()
    a = dt.datetime.combine(d, dt.time(h0)).timestamp()
    end_day = d + dt.timedelta(days=1) if h1 <= h0 else d
    return a, dt.datetime.combine(end_day, dt.time(h1)).timestamp()


def _waiting_items(text):
    try:
        import schedule as sc
        return [i for i in sc.read(text) if i["state"] == "waiting"]
    except Exception:
        return []


def planned_item(items, label):
    """The waiting planned item that already names roadmap row LABEL, the way a job does (jobs.with_team), or None."""
    l = re.escape(label)
    pat = re.compile(rf"(?<![\w.]){l} on the (hq )?roadmap\b|\bthe {l} row\b", re.I)
    return next((i for i in items if pat.search(i["text"])), None)


def _busy(now, end):
    """What's already with the team or planned, from estimate.plan: (proj, busy, reserved) where proj is the usage
    projection with that work in it, busy the (start, end) of each piece of one-off work (a night it reaches into
    starts after it), and reserved a list of (start, minutes) for the repeating items up to `end` (each night they
    fall in loses those minutes)."""
    import usagecost as U
    p = E.plan(now)
    proj = U.Projection.here(now) if p.get("on", True) else None
    busy, reserved = [], []
    for e in (p.get("jobs") or {}).values():
        if e.get("finished"):
            continue
        cost = {k: max(0.0, (e.get("cost") or {}).get(k, 0) - (e.get("used") or {}).get(k, 0)) for k in U.KEYS}
        start = now if "left" in e else (e.get("start") or ((e.get("eta") or now) - (e.get("est") or 0) * 60))
        if proj:
            proj.add(cost, max(now, start))
        if e.get("eta"):
            busy.append((max(now, start), e["eta"]))
    for e in (p.get("items") or {}).values():
        if not e.get("start"):
            continue
        if e.get("every"):
            step, t = (86400 if e["every"] == "day" else 7 * 86400), e["start"]
            while t < end:
                reserved.append((t, e.get("est") or 0))
                if proj and e.get("cost"):
                    proj.add(e["cost"], t)
                t += step
            continue
        if proj and e.get("cost"):
            proj.add(e["cost"], e["start"])
        busy.append((e["start"], e.get("eta") or e["start"]))
    return proj, busy, reserved


def lay(labels, night=None, now=None):
    """The ticked rows over the nights from `night` (a day, or his word for one), in rank order. Returns
    {"rows": [...], "nights": [...], "line": {...} | None, "night": "YYYY-MM-DD", "room": [22, 8], "left_out": [...]}."""
    import datetime as dt
    now = _now() if now is None else now
    d0 = night if isinstance(night, dt.date) else night_of(night, now)
    p = plan()
    by = {x["label"]: x for x in p["rows"]}
    want = [l.strip().upper() for l in labels if l.strip()]
    left_out, picked = [], []
    for l in dict.fromkeys(want):
        x = by.get(l)
        if not x:
            left_out.append({"label": l, "why": "not an open row on the planning"})
        elif x.get("team"):
            left_out.append({"label": l, "why": f"already with the team (job {x['team']})"})
        elif x.get("planned"):
            left_out.append({"label": l, "why": f"already planned for the team (item {x['planned']['n']}, {x['planned']['at']})"})
        else:
            picked.append(x)
    order_ = [x["label"] for x in p["rows"]]
    picked.sort(key=lambda x: order_.index(x["label"]))  # the planning's order: MoSCoW group, bugs first, the rank (H271)
    a0, _ = _night(d0)
    horizon_end = _night(d0 + dt.timedelta(days=NIGHTS - 1))[1]
    proj, busy, reserved = _busy(now, horizon_end)
    nights = []
    for k in range(NIGHTS):
        a, b = _night(d0 + dt.timedelta(days=k))
        res = sum(m for t, m in reserved if a <= t < b)
        taken = [e for s_, e in busy if s_ < b and e > a]  # the work already there that reaches into this night
        nights.append({"day": (d0 + dt.timedelta(days=k)).isoformat(), "from": int(a), "to": int(b), "reserved": res,
                       "cursor": max([a, now] + taken), "end": b - res * 60, "rows": []})
    out, line = [], None
    k = 0
    for x in picked:
        cost = x.get("cost") or {}
        need = {kk: cost.get(kk, 0) for kk in ("five", "weekly")}
        r = {"label": x["label"], "title": x["title"], "rank": x["rank"], "est": x["est"], "cost": cost, "kind": x.get("kind"),
             "moscow": x.get("moscow"), "bug": x.get("bug"), "ready": x.get("ready"), "not_ready": x.get("not_ready")}
        placed = False
        first_k = k
        while k < len(nights):
            n = nights[k]
            if n["cursor"] >= n["end"]:
                k += 1
                continue
            t = proj.fits_at(need, n["cursor"]) if proj else n["cursor"]
            if t is None:
                r["why"] = "it doesn't fit under the usage lines as they're set (a fixed line)"
                break
            t = max(t, n["cursor"])
            fits = t + x["est"] * 60 <= n["end"]
            if t >= n["end"] or (not fits and n["rows"]):
                if t > n["cursor"] + 59 and k == first_k:
                    r["usage"] = True  # the usage, not the night's length, pushed it on
                k += 1
                continue
            if proj:
                proj.add(need, t)
            r.update({"night": n["day"], "start": int(t), "eta": int(t + x["est"] * 60), "waits": t > n["cursor"] + 59})
            if t > n["cursor"] + 59:
                r["usage"] = True
            n["cursor"] = t + x["est"] * 60
            n["rows"].append(x["label"])
            placed = True
            break
        if not placed and "why" not in r:
            r["why"] = f"no room in the next {NIGHTS} nights"
        if line is None and (not placed or (r.get("usage") and r.get("night") != nights[first_k]["day"])):
            line = {"before": x["label"], "why": r.get("why") or _line_why(r, proj)}
        r["past"] = line is not None
        out.append(r)
    used = []
    for n in nights:
        if not n["rows"]:
            continue
        mine = [r for r in out if r.get("night") == n["day"]]
        used.append({"day": n["day"], "from": n["from"], "to": n["to"], "rows": n["rows"],
                     "minutes": sum(r["est"] for r in mine), "eta": max(r["eta"] for r in mine),
                     "five": round(sum((r["cost"] or {}).get("five", 0) for r in mine), 1),
                     "weekly": round(sum((r["cost"] or {}).get("weekly", 0) for r in mine), 1),
                     "reserved": n["reserved"]})
    return {"rows": out, "nights": used, "line": line, "night": d0.isoformat(), "room": list(_room()),
            "left_out": left_out, "now": int(now)}


def _line_why(r, proj):
    """Why the room runs out at this row, in a few words."""
    try:
        wk = proj.read.get("weekly", {}).get("reset") if proj else None
    except Exception:
        wk = None
    if r.get("start") and wk and r["start"] >= wk:
        return f"the weekly room runs out: from here the work waits for the weekly reset ({_when(wk)})"
    return "the usage room runs out: from here the work waits for the 5-hour or weekly stop line, so it moves on"


def _when(t):
    return time.strftime("%A %H:%M", time.localtime(t))


def _night_name(day, now):
    import datetime as dt
    d = dt.date.fromisoformat(day)
    today = dt.date.fromtimestamp(now)
    return "tonight" if d == today else "tomorrow night" if d == today + dt.timedelta(days=1) else f"{DAYS[d.weekday()].capitalize()} night"


def lay_words(L):
    """The sprint in words, for a call."""
    out = []
    for x in L["left_out"]:
        out.append(f"{x['label']} is left out: {x['why']}.")
    if not L["rows"]:
        return "\n".join(out + ["Nothing ticked for the sprint."])
    nights = {n["day"]: n for n in L["nights"]}
    seen = set()
    for r in L["rows"]:
        if L["line"] and L["line"]["before"] == r["label"]:
            out.append(f"--- the room runs out here: {L['line']['why']} ---")
        if r.get("night") and r["night"] not in seen:
            seen.add(r["night"])
            n = nights[r["night"]]
            out.append(f"{_night_name(r['night'], L['now']).capitalize()} ({r['night']}): {len(n['rows'])} {'row' if len(n['rows']) == 1 else 'rows'}, about "
                       f"{E.dur(n['minutes'])}, done around {E.hhmm(n['eta'])}; 5-hour {E._pct(n['five'])}, weekly {E._pct(n['weekly'])}")
        c = r.get("cost") or {}
        where = (f"starts around {E.hhmm(r['start'])}{' (it waits for the usage)' if r.get('usage') else ''}, done around {E.hhmm(r['eta'])}"
                 if r.get("start") else r.get("why", "no time"))
        out.append(f"  {r['rank'] or '-'}. {r['label']} {q.one_line(r['title'])[:80]}: about {E.dur(r['est'])}, "
                   f"5-hour {E._pct(c.get('five') or 0)}, weekly {E._pct(c.get('weekly') or 0)}; {where}"
                   + (f" ({r['not_ready']}, so Plan the sprint leaves it out)" if r.get("ready") != "ready" else ""))
    if not L["line"]:
        out.append("Everything ticked fits in the room (estimate).")
    return "\n".join(out)


def plan_sprint(labels, night=None, now=None):
    """Plan the sprint: the ticked rows on the schedule for the team, in rank order, each at its night's start (a
    minute apart, so the scheduler keeps their order), the same as a call planning them. Returns (planned, said)."""
    import datetime as dt
    now = _now() if now is None else now
    L = lay(labels, night, now)
    said, planned = [f"{x['label']} is left out: {x['why']}." for x in L["left_out"]], []
    at_of = {}
    for r in L["rows"]:
        day = r.get("night")
        if r.get("ready") != "ready":  # H272: only rows marked ready go to the team
            said.append((r.get("not_ready") or f"{r['label']} isn't ready") + ", so it isn't planned.")
            continue
        if not day:
            said.append(f"{r['label']} isn't planned: {r.get('why', 'no room')}.")
            continue
        a, _ = _night(dt.date.fromisoformat(day))
        a = max(a, now + 60)
        at = max(a, at_of.get(day, a - 60) + 60)
        at_of[day] = at
        text = (f"{r['label']} on the HQ roadmap, planned for the team at the sprint planning: "
                f"{q.one_line(r['title']).replace('·', '-').rstrip('.')}. Read the {r['label']} row and do what it says. "
                f"Pull dev first, privacy check, push to dev with push.py, write the result in the {r['label']} row.")
        args = [sys.executable, os.path.join(HERE, "schedule.py"), "add", time.strftime("%Y-%m-%d %H:%M", time.localtime(at)), text]
        if r.get("kind") and E.kind_word_ok(r["kind"]):
            args += ["--kind", r["kind"]]
        res = subprocess.run(args, capture_output=True, text=True, env={**os.environ, "HQ_ROLE_HERE": "1"}, timeout=120)
        if res.returncode != 0:
            said.append(f"{r['label']} couldn't be planned: {(res.stderr or res.stdout).strip()[:200]}")
            continue
        planned.append(r["label"])
        said.append(f"{r['label']} planned for {_night_name(day, now)}, {time.strftime('%a %d %b %H:%M', time.localtime(at))}"
                    f" (about {E.dur(r['est'])}, done around {E.hhmm(r['eta'])}).")
    if L["line"]:
        said.append(f"The room runs out at {L['line']['before']}: {L['line']['why']}.")
    if not planned:
        said.append("Nothing was planned.")
    return planned, "\n".join(said)


def _args(argv):
    """The labels and --night (with or without =), and --json."""
    labels, night, as_json, skip = [], None, False, False
    for i, a in enumerate(argv):
        if skip:
            skip = False
        elif a == "--night":
            night, skip = (argv[i + 1] if i + 1 < len(argv) else ""), True
        elif a.startswith("--night="):
            night = a.split("=", 1)[1]
        elif a == "--json":
            as_json = True
        else:
            labels += [x for x in re.split(r"[,\s]+", a) if x]
    return labels, night, as_json


def main(argv):
    cmd = argv[0] if argv else "--help"
    if cmd in ("rank", "plan", "moscow", "ready"):
        import role
        if not os.environ.get("HQ_ROLE_HERE") and role.is_backup():
            sys.exit(role.forward("sprint", list(argv)))
    if cmd == "list":
        print(words(plan()))
    elif cmd == "json":
        print(json.dumps(plan()))
    elif cmd == "rank":
        if len(argv) < 3:
            sys.exit("rank LABEL N|top|bottom|off")
        with q.locked():
            ranked = set_rank(argv[1], argv[2])
        label = argv[1].strip().upper()
        print(f"{label} is now rank {ranked.index(label) + 1} of {len(ranked)}." if label in ranked
              else f"{label} has no rank now; {len(ranked)} rows are ranked.")
    elif cmd == "moscow":
        if len(argv) < 3:
            sys.exit("moscow LABEL must|should|could|wont|off")
        with q.locked():
            t = set_moscow(argv[1], argv[2])
        label = argv[1].strip().upper()
        print(f"{label} is now {MOSCOW_NAMES[t]}." if t else f"{label} has no MoSCoW tag now.")
    elif cmd == "ready":  # H272
        if len(argv) < 2:
            sys.exit("ready LABEL [on|off]")
        on = _onoff(argv[2] if len(argv) > 2 else "on")
        with q.locked():
            set_ready(argv[1], on)
        label = argv[1].strip().upper()
        print(f"{label} is marked ready for the sprint." if on else f"{label} has no Ready mark now.")
    elif cmd == "check":  # H272: why a row isn't ready, for a call or the page
        rows = {r["label"]: r for r in open_rows()}
        for l in [a.strip().upper() for a in argv[1:]]:
            print((not_ready_why(rows[l]) or f"{l} is ready.") if l in rows else f"{l} isn't an open row on the planning.")
    elif cmd == "show":  # Fable clean-up: one row, open or closed, never the whole planning
        if len(argv) < 2:
            sys.exit("show LABEL [LABEL …]")
        print(show_words([a.strip().upper() for a in argv[1:]]))
    elif cmd == "open":  # H288: the open items only
        print(open_words())
    elif cmd == "lay":
        labels, night, as_json = _args(argv[1:])
        L = lay(labels, night)
        print(json.dumps(L) if as_json else lay_words(L))
    elif cmd == "plan":
        labels, night, _ = _args(argv[1:])
        if not labels:
            sys.exit("plan LABEL... [--night D]: which rows go in the sprint, in rank order.")
        planned, said = plan_sprint(labels, night)
        print(said)
        if not planned:
            sys.exit(1)
    elif cmd == "refresh":
        print(", ".join(refresh()) or "Nothing to look at again.")
    elif cmd == "look-run":
        look_run(argv[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
