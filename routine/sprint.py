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
  python3 routine/sprint.py lay LABEL... [--night D]     the sprint: the rows, in rank order, laid over the nights from
                                                        night D (tonight, tomorrow, a weekday or 2026-10-26; tonight
                                                        when left out); --json for the status page
  python3 routine/sprint.py plan LABEL... [--night D]    Plan the sprint: those rows planned for the team in that order
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
        i = planned_item(items, r["label"])  # piece 2: already planned for the team
        if i:
            x["planned"] = {"n": i["n"], "at": i["at"]}
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
        team = (f" (with the team: job {x['team']})" if x.get("team") else
                f" (planned for the team: item {x['planned']['n']}, {x['planned']['at']})" if x.get("planned") else "")
        lines.append(f"{where} {x['label']} {q.one_line(x['title'])[:90]}: {row_words(x)}{team}")
    if not lines:
        return "Nothing open on the planning."
    head = f"The planning, {len(p['rows'])} open rows, {p['ranked']} ranked (estimate):"
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
    picked.sort(key=lambda x: order_.index(x["label"]))  # rank order: the ranked first, then the roadmap's order
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
        r = {"label": x["label"], "title": x["title"], "rank": x["rank"], "est": x["est"], "cost": cost, "kind": x.get("kind")}
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
                   f"5-hour {E._pct(c.get('five') or 0)}, weekly {E._pct(c.get('weekly') or 0)}; {where}")
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
    if cmd in ("rank", "plan"):
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
