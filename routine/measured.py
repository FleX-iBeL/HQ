#!/usr/bin/env python3
"""F79 (3 November 2026): an estimate built from measured parts, with its range and how sure it is.

The end goal, from F66: when HQ says work is done by a time, it's done by then. In his words: "If those estimates are not
correct, We are on calls and we're saying, oh yeah, it's done in 30 minutes. And five hours later, I'm still talking with
agents". The bar, his words on 2 November 2026: "estimates part is fine", on the builder's pick of 1 November: 9 in 10 by
their latest end, and half to double as today or better, in the replay (each finished job estimated only from the jobs
before it). The 20 live jobs come after 1.0.

What it's built from: the record of every finished job (job-estimates-history.jsonl, F103's minutes, turns and plan on each
line), never a sentence. The measuring of 1 November (HQ/handoff-foundation-built-f79.md) showed what holds:

  * Time. Jobs are grouped by what they really are (group): a build of any size is one group (the guess sorts small from big
    better than the two kinds did), each maintenance run by its own wording, a daily release apart from a release by hand,
    the agents' runs together, else the kind. The likely time is the group's median over its last LAST jobs; a guess (the
    team's at the start, else the call's, else the first look's; at add time only the call's or the look's) moves it by
    where it sits among the group's own guesses (PULL), never by its size, since the guesses run 2 to 4 times long. The
    latest end is the likely time times where 9 in 10 of the group's last jobs landed against what this gave them (Q_TOP),
    between WIDE times.
  * Usage. Per job, not per minute: the median of the kind's last LAST jobs' own tokens (weighted, at the plan's own rate,
    F107), its range the tenth to ninetieth of them, the latest the ninetieth. Builds stay two kinds here: for tokens the
    split holds.
  * How sure. A group with at least SURE_MIN measured jobs gives a measured estimate, saying how many it rests on. Under it
    the estimate says so: too few jobs like it. It still gets a number and a latest end, never none (Moneypenny's addition
    of 1 November): today's estimate (estimate.py: under 3 of a kind the last jobs of any kind, nothing at all 15 minutes),
    marked as rough.

It gets better as jobs finish: every finished job is in its group's last LAST at once.

The numbers here are the builder's (F79, 3 November 2026), from the replay on the 451 finished jobs up to 31 October, and
named in the CHANGELOG: LAST 30, SURE_MIN 5, GUESS_MIN 4, PULL 0.85 at the start and 0.7 at add, ANY_LAST 60, Q_TOP 0.9,
WIDE 1.3 to 6, the usage range from the tenth to the ninetieth.

    python3 routine/measured.py replay [--today]   every finished job estimated back: how close, by its latest, per group
    python3 routine/measured.py show TEXT [--kind K]  what an item with these words would get now
"""
import math
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import estimate as E  # noqa: E402

LAST = 30          # the group's last finished jobs an estimate is built from
SURE_MIN = 5       # measured jobs like it before an estimate counts as measured; under it: too few, said
GUESS_MIN = 4      # guessed jobs in a group before a guess is placed among them
PULL = {"start": 0.85, "add": 0.7}  # how far a guess's place among its group's guesses moves the likely time (in log)
ANY_LAST = 60      # with too few guesses in its group: a guess corrected by how the last this many of any kind ran
Q_TOP = 0.9        # the latest end: where this share of the group's last jobs landed against their estimate
WIDE = (1.3, 6.0)  # the latest end is at least and at most this many times the likely time
Q_LOW = 0.1        # the usage range: from this share to Q_TOP of the kind's last jobs
USE_MAX = 4        # a job's usage grows with its own likely time over its group's middle one, at most this many times
KEYS = {"start": ("guess", "guess_call", "guess_look"), "add": ("guess_call", "guess_look")}


def group(kind, about=""):
    """What a job really is, for its time: a build of any size, each maintenance run, a daily release or one by hand,
    the agents' runs, else its kind."""
    k = kind or "other"
    a = about or ""
    if k in E.BUILDS:
        return "build"
    if k.startswith(("cycle-", "step-")):
        return "agents"
    if k == "maintenance":
        m = E._MAINT.search(a)
        return "maintenance: " + ((m.group(1) or "full test run") if m else "other")
    if k == "release":
        return "release: daily" if re.search(r"\bthe daily release\b", a) else "release: by hand"
    return k


def use_group(kind):
    """What a job is, for its usage: its kind (builds stay two), the agents' runs together."""
    k = kind or "other"
    return "agents" if k.startswith(("cycle-", "step-")) else k


def _ok(g):
    return isinstance(g, (int, float)) and 0 < g <= E.GUESS_MAX


class _Book:
    """The measured finished jobs of one history, grouped, with what's been worked out from them."""

    def __init__(self, hist):
        self.all = [h for h in E._real(hist) if not E.mistake(h)]
        self.groups = {}
        self.where = []
        for h in self.all:
            g = self.groups.setdefault(group(h.get("kind"), h.get("about")), [])
            self.where.append((g, len(g)))
            g.append(h)
        self.pos = {id(h): p for p, h in enumerate(self.all)}
        self.tops = {}


_BOOKS = {}


def _book(hist):
    key = (id(hist), len(hist), (hist[-1].get("done"), hist[-1].get("n")) if hist else None)
    b = _BOOKS.get(key)
    if b is None:
        _BOOKS.clear() if len(_BOOKS) > 8 else None
        b = _BOOKS[key] = _Book(hist)
    return b


def _likely(before, anyp, e, moment):
    """The likely minutes from the group's jobs before (oldest first) and the guesses e carries: (minutes, the group's
    alone, the guess used)."""
    alone = statistics.median(h["actual"] for h in before)
    lm = math.log(alone)
    used = None
    for k in KEYS[moment]:
        g = (e or {}).get(k)
        if not _ok(g):
            continue
        gs = [math.log(h[k]) for h in before if _ok(h.get(k))]
        if len(gs) >= GUESS_MIN:
            lm += PULL[moment] * (math.log(g) - statistics.median(gs))
            used = k
        else:
            anyg = [h for h in anyp if _ok(h.get(k))][-ANY_LAST:]
            if len(anyg) >= GUESS_MIN:
                lm = (lm + math.log(g) + statistics.median(math.log(h["actual"] / h[k]) for h in anyg)) / 2
                used = k
        break
    return max(1, round(math.exp(lm))), max(1, round(alone)), used


def _ratios(b, jobs, moment):
    out = []
    for h in jobs:
        p = b.pos.get(id(h))
        if p is None:
            continue
        g, i = b.where[p]
        before = g[max(0, i - LAST):i]
        if len(before) < 2:
            continue
        out.append(h["actual"] / _likely(before, b.all, h, moment)[0])
    return out


def _quant(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def _top(b, name, moment):
    """How much later than its likely time a job of this group lands at the latest: the Q_TOP share of real over what
    this gave the group's last LAST jobs (each from the jobs before it); with under SURE_MIN of those, the last LAST of
    every group; between WIDE."""
    key = (name, moment)
    if key not in b.tops:
        rs = _ratios(b, b.groups.get(name, [])[-LAST:], moment)
        if len(rs) < SURE_MIN:
            if ("*", moment) not in b.tops:
                every = _ratios(b, b.all[-LAST:], moment)
                b.tops[("*", moment)] = _quant(every, Q_TOP) if every else 2.0
            f = b.tops[("*", moment)]
        else:
            f = _quant(rs, Q_TOP)
        b.tops[key] = round(min(WIDE[1], max(WIDE[0], f)), 2)
    return b.tops[key]


def time_of(kind, about, e, hist, moment="add"):
    """{"est", "latest", "alone", "guess_used", "sure": {"ok", "jobs", "group"}}; under SURE_MIN jobs like it
    {"sure": {"ok": False, ...}, "top"}: the caller keeps today's number, marked as rough, its latest end at least
    "top" times it (where 9 in 10 of the last jobs of every group landed)."""
    b = _book(hist)
    name = group(kind, about)
    grp = b.groups.get(name, [])
    if len(grp) < SURE_MIN:  # too few like it: today's number stays, its latest end at least as wide as unsure work lands
        return {"sure": {"ok": False, "jobs": len(grp), "group": name}, "top": _top(b, name, moment)}
    est, alone, used = _likely(grp[-LAST:], b.all, e, moment)
    return {"est": est, "latest": max(est + 1, math.ceil(est * _top(b, name, moment))), "alone": alone,
            "guess_used": used, "sure": {"ok": True, "jobs": min(len(grp), LAST), "group": name}}


def cost_of(kind, hist, plan=None, keep=None, scale=1.0):
    """The usage of one job like it, at the plan's own rate (F107): {"five", "weekly", "how": "measured", "based",
    "plan", "tokens", "range", "five_range", "weekly_range"} and, apart, its latest {"five", "weekly"}; (None, None)
    under SURE_MIN of its kind with tokens, or with no rate. keep: today's cost, for a line the plan has no rate for.
    scale: how much bigger than its group's middle job this one is (scale_of); the middle and the top grow with it."""
    import usagecost as U
    plan = plan or U.current_plan()
    model = U.load_rate(plan)
    if not model or not model.get("rate"):
        return None, None
    name = use_group(kind)
    toks = [U.weighted(h["tokens"], model) for h in _book(hist).all
            if use_group(h.get("kind")) == name and isinstance(h.get("tokens"), dict) and h["tokens"]][-LAST:]
    if len(toks) < SURE_MIN:
        return None, None
    mid, lo, hi = statistics.median(toks), _quant(toks, Q_LOW), _quant(toks, Q_TOP)
    scale = min(USE_MAX, max(1.0, scale or 1.0))
    mid, hi = mid * scale, hi * scale
    out = {"how": "measured", "based": len(toks), "plan": plan, "tokens": round(mid), "range": [round(lo), round(hi)]}
    if scale > 1:
        out["scale"] = round(scale, 2)
    late = {}
    for k in U.KEYS:
        r = model["rate"].get(k)
        if r:
            out[k], late[k] = round(mid / r, 1), round(hi / r, 1)
            out[k + "_range"] = [round(lo / r, 1), round(hi / r, 1)]
        else:
            out[k] = late[k] = float((keep or {}).get(k, 0))
    return out, late


def apply(x, kind, about, e, hist, moment="add"):
    """Puts the measured estimate on x (a planning row, a waiting job, a planned item: its "est" and "latest" made the
    way they were before F79) and says how sure it is. Returns x."""
    m = time_of(kind, about, e, hist, moment)
    x["sure"] = m["sure"]
    if m["sure"]["ok"]:
        x["est"], x["latest"] = m["est"], m["latest"]
        x["based"], x["group_mid"] = m["sure"]["jobs"], m["alone"]
        x.pop("computed", None)
        x.pop("guess_used", None)
        if m["guess_used"] and m["alone"] != m["est"]:
            x["computed"], x["guess_used"] = m["alone"], m["guess_used"]
    else:
        x["based"] = m["sure"]["jobs"]
        if x.get("est"):
            x["latest"] = max(x.get("latest") or 0, x["est"] + 1, math.ceil(x["est"] * m["top"]))
    return x


def put(x, kind, about, e, hist, moment="add", text=""):
    """F79: the measured time (apply) and usage on x, next to each other: "cost", "cost_how", "cost_latest" and, when
    measured, "cost_range" and the whole "cost_detail". Under SURE_MIN of its kind with tokens: today's usage, made
    again from the time when that changed, its latest at the latest end. Returns x."""
    before = x.get("est")
    apply(x, kind, about, e, hist, moment)
    return cost_put(x, kind, hist, text, before)


def scale_of(x):
    """F79: a job bigger than its group's middle one uses more: its likely time over the group's middle likely time,
    never under 1, at most USE_MAX. 1 when its time isn't measured (today's usage is per minute, so it follows already)."""
    mid = x.get("group_mid")
    return min(USE_MAX, max(1.0, x["est"] / mid)) if mid and x.get("est") else 1.0


def cost_put(x, kind, hist, text="", before=None):
    """F79: the usage half of put, on x that already has its time. before: its minutes before the time was made, so
    today's per-minute usage is made again when they changed."""
    import usagecost as U
    c, late = cost_of(kind, hist, keep=x.get("cost"), scale=scale_of(x))
    if c:
        x["cost"], x["cost_how"], x["cost_latest"], x["cost_detail"] = {k: c[k] for k in U.KEYS}, "measured", late, c
        x["cost_range"] = {k: c[k + "_range"] for k in U.KEYS if c.get(k + "_range")}
    elif x.get("est"):
        if x.get("cost") is None or (before is not None and x["est"] != before):
            t = U.cost_for(x["est"], text, kind, hist)
            x["cost"], x["cost_how"] = {k: t[k] for k in U.KEYS}, t["how"]
        if x.get("latest"):
            x["cost_latest"] = U.at_latest(x["cost"], x["est"], x["latest"])
    return x


def words(x):
    """How sure an estimate is, in a few words, for a call and the lists."""
    s = x.get("sure") or {}
    if not s:
        return ""
    n = s.get("jobs", 0)
    if s.get("ok"):
        return f"from {n} finished jobs like it"
    return (f"too few finished jobs like it ({n}), so a rough number" if n else
            "no finished jobs like it yet, so a rough number")


# ---------- the replay ----------

def replay(hist=None, today=False):
    """Every measured finished job estimated from only the jobs before it, at the start (with the guesses it had) and
    at add time (the call's and the look's only): between half and double, by its latest end, the width, per group;
    the usage the same way. today: next to estimate.py's own numbers as they'd have been (slower)."""
    import usagecost as U
    hist = E.all_history() if hist is None else hist
    model = U.load_rate()
    out = {m: {"count": 0, "within": 0, "by_latest": 0, "widths": [], "rough": 0, "groups": {}} for m in ("start", "add")}
    if today:
        out["today"] = {"count": 0, "within": 0, "by_latest": 0, "widths": []}
        out["today_add"] = {"count": 0, "within": 0, "by_latest": 0, "widths": []}
    use = {"count": 0, "within": 0, "under_top": 0}
    was = {"count": 0, "within": 0, "under_top": 0}  # the usage estimate each line was given, as it was recorded
    for i, h in enumerate(hist):
        if h not in E._real([h]) or E.mistake(h):
            continue
        prior = hist[:i]
        if not E._real(prior):
            continue
        a = h["actual"]
        for moment in ("start", "add"):
            m = time_of(h.get("kind"), h.get("about"), h, prior, moment)
            r = out[moment]
            if not m["sure"]["ok"]:  # too few like it: today's number, as the live code gives it
                r["rough"] += 1
                d = E.estimate_detail("", prior, h.get("kind"), h["machine"], h.get("tags") or [], h.get("about") or "",
                                      True, sized=False)
                g, _, gf = E.pick_guess(h if moment == "start" else {k: h.get(k) for k in KEYS["add"]}, E.guess_fits(prior))
                est = E.with_guess(d["est"], g, gf)
                m = apply({"est": est, "latest": E.latest_of(est, h.get("kind"), prior)}, h.get("kind"), h.get("about"),
                          h, prior, moment)
            ok, by = m["est"] / 2 <= a <= m["est"] * 2, a <= m["latest"]
            gr = r["groups"].setdefault(group(h.get("kind"), h.get("about")), {"count": 0, "within": 0, "by_latest": 0})
            for t in (r, gr):
                t["count"] += 1
                t["within"] += ok
                t["by_latest"] += by
            r["widths"].append(m["latest"] / m["est"])
        if today:
            d = E.estimate_detail("", prior, h.get("kind"), h["machine"], h.get("tags") or [], h.get("about") or "",
                                  True, sized=False)
            fits = E.guess_fits(prior)
            for key, src in (("today", h), ("today_add", {k: h.get(k) for k in KEYS["add"]})):
                g, _, gf = E.pick_guess(src, fits)
                est = E.with_guess(d["est"], g, gf)
                lat = E.latest_of(est, h.get("kind"), prior)
                t = out[key]
                t["count"] += 1
                t["within"] += est / 2 <= a <= est * 2
                t["by_latest"] += a <= lat
                t["widths"].append(lat / est)
        if model and isinstance(h.get("tokens"), dict) and h["tokens"]:
            c, late = cost_of(h.get("kind"), prior)
            if c:
                real = U.weighted(h["tokens"], model)
                use["count"] += 1
                use["within"] += c["tokens"] / 2 <= real <= c["tokens"] * 2
                use["under_top"] += real <= c["range"][1]
                rec = h.get("est_cost") or {}
                if rec.get("tokens") and rec.get("range"):
                    was["count"] += 1
                    was["within"] += rec["tokens"] / 2 <= real <= rec["tokens"] * 2
                    was["under_top"] += real <= rec["range"][1]
    for k, r in out.items():
        r["width"] = round(statistics.median(r.pop("widths")), 2) if r.get("widths") else None
    out["usage"], out["usage_was"] = use, was
    return out


def _pct(a, b):
    return f"{round(100 * a / b)}%" if b else "none"


def replay_words(r):
    lines = []
    for moment, title in (("start", "At the start"), ("add", "When added or on the planning")):
        x = r[moment]
        lines.append(f"{title}: {x['within']} of {x['count']} ({_pct(x['within'], x['count'])}) between half and double, "
                     f"{x['by_latest']} ({_pct(x['by_latest'], x['count'])}) by their latest end, the latest {x['width']} "
                     f"times the likely in the middle; {x['rough']} with too few jobs like them.")
        lines.append("  " + "; ".join(f"{g} {v['within']} and {v['by_latest']} of {v['count']}"
                                      for g, v in sorted(x["groups"].items(), key=lambda kv: -kv[1]["count"])))
    for key, title in (("today", "at the start"), ("today_add", "when added")):
        t = r.get(key)
        if t:
            lines.append(f"The code before F79 {title}: {t['within']} of {t['count']} ({_pct(t['within'], t['count'])}) between "
                         f"half and double, {t['by_latest']} ({_pct(t['by_latest'], t['count'])}) by the latest, width {t['width']}.")
    u = r["usage"]
    lines.append(f"Usage: {u['within']} of {u['count']} ({_pct(u['within'], u['count'])}) between half and double, "
                 f"{u['under_top']} ({_pct(u['under_top'], u['count'])}) under the top of the range.")
    w = r.get("usage_was") or {}
    if w.get("count"):
        lines.append(f"Usage as each line was given it before F79, on the same jobs: {w['within']} of {w['count']} "
                     f"({_pct(w['within'], w['count'])}) between half and double, {w['under_top']} "
                     f"({_pct(w['under_top'], w['count'])}) under its top.")
    return "\n".join(lines)


def main(argv):
    if len(argv) > 1 and argv[1] == "replay":
        print(replay_words(replay(today="--today" in argv)))
        return 0
    if len(argv) > 2 and argv[1] == "show":
        a = [x for x in argv[2:] if not x.startswith("--")]
        kind = argv[argv.index("--kind") + 1] if "--kind" in argv else None
        text = " ".join(t for t in a if t != kind)
        hist = E.all_history()
        k = E.kind_for(text, kind)
        d = E.estimate_detail(text, hist, k)
        x = put({"est": d["est"], "latest": d["latest"]}, k, E._about(text), {}, hist, text=text)
        print(f"{k}: about {x['est']} minutes, at the latest {x['latest']}, {words(x)}; usage {x.get('cost')} "
              f"({'measured' if x.get('cost_how') == 'measured' else 'too few like it with tokens: the way before F79'})")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
