#!/usr/bin/env python3
"""H269, piece 1: sprint planning, the rank and the estimate on every open row of the planning (25 October 2026).
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

usage:
  python3 routine/sprint.py list                       the planning in rank order, each with its estimate (a call reads this)
  python3 routine/sprint.py json                       the same as JSON (the status server shows it)
  python3 routine/sprint.py rank LABEL N|top|bottom|off  give row LABEL a place (1 the top), or take its rank away
  python3 routine/sprint.py refresh                    the sizes and the looks for rows whose words changed (the routine does it)
Used by the background look itself: look-run LABEL.
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
                    "phase": phase[9:].split(" ·", 1)[0]})
    return out


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
    _save(RANKS, {"order": ranked, "set": int(time.time())})
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
    d = _load(ESTS)
    hist = E.all_history()
    fits = E.guess_fits(hist)
    try:
        jobs = q.read()[1]
    except Exception:
        jobs = []
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
             "est": est, "kind": det["kind"]}
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
        out.append(x)
    out.sort(key=lambda x: (x["rank"] is None, x["rank"] or 0))
    return {"rows": out, "ranked": len(ranked)}


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
    lines = []
    for x in p["rows"]:
        where = f"{x['rank']}." if x["rank"] else "unranked:"
        team = f" (with the team: job {x['team']})" if x.get("team") else ""
        lines.append(f"{where} {x['label']} {q.one_line(x['title'])[:90]}: {row_words(x)}{team}")
    if not lines:
        return "Nothing open on the planning."
    head = f"The planning, {len(p['rows'])} open rows, {p['ranked']} ranked (estimate):"
    return "\n".join([head] + lines)


def main(argv):
    cmd = argv[0] if argv else "--help"
    if cmd in ("rank",):
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
    elif cmd == "refresh":
        print(", ".join(refresh()) or "Nothing to look at again.")
    elif cmd == "look-run":
        look_run(argv[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
