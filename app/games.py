"""H222: the six-week game, as HQ keeps and shows it (21 October 2026, part 1: the template and the system).

The user's words on the call of 21 October 2026: "We could also build a 6-week game dashboard in HQ where we can track
things. ... We should make it more templated so that other people that download this can also use it. ... I can just
check whether I did it or I didn't do it, or write a note. Then we know at the end of the week we need to discuss it."
Then: "I think it should build a template so that their HQ, whenever they want to do a 6-week challenge, can build upon
that template. ... maybe there are different ways you want to tick things off. Maybe you want graphs in certain
challenges." And: "the moment they want to do a 6-week challenge, they need to have a session with you ... You just
need to design it and then hand it off to the team so they can tailor it, custom-made for this type of challenge ...
They can always open their past history one."

So every game gets the same frame (the template): what it's for, the dates (a setup week, six weeks of playing, a week
to look back), the win line, a look back at the end of each week and a debrief at the end, a note per day, and every
past game kept to open again. On top of that a game says what it keeps track of, as tracks of a kind:

    tick    a day done or not: done, x (didn't), or nothing yet. Win: a share of the days, {"track": T, "share": .9}
    count   a number a day, added to as often as you like ("several counts a day" are several count tracks), with an
            optional target for the whole game and per day; "graph": true shows it day by day and adding up.
            Win: {"track": T, "total": 60} or {"track": T, "per_day": 5, "share": .8}
    diary   entries with the time, what happened and how it felt ("feel": the words to pick from), to trace back

A game is designed with the user on a call (the deep agent, from the Life coaching guide's six-week game layer),
written into their map.md under that layer, and handed to their team, who make it here with `new` from a spec and,
when it needs something these kinds don't have, add a kind: a function in KINDS below (how a value is taken, and how
a track adds up) and a drawer of the same name in web/games.js (GAME_KINDS). Nothing of anyone's own games is ever in
HQ: they're the workspace's HQ/games.json (or HQ_GAMES), and a fresh install has none.

A spec (JSON), the team's to write from the map:
    {"name": "…", "for": "the year's goal it serves", "game": "For six weeks I…", "rules": "…",
     "start": "YYYY-MM-DD" (the first of the six weeks; the setup week is the week before),
     "weeks": 6, "win": {"track": "…", "share": 0.9} or {"text": "…"}, "win_text": "how they said it",
     "tracks": [{"id": "done", "kind": "tick", "label": "…"}, {"id": "sent", "kind": "count", "label": "…",
                 "target": 60, "graph": true}, {"id": "food", "kind": "diary", "label": "…", "feel": ["good", "bad"]}],
     "graphs": [{"label": "…", "tracks": ["sent", "replies"]}] (optional: several counts in one graph)}

    python3 app/games.py                        the games in a few lines, to say out loud
    python3 app/games.py json                   everything the app gets (JSON)
    python3 app/games.py show GAME              one game, every day
    python3 app/games.py kinds                  the kinds of tracks there are
    python3 app/games.py check SPEC             is this spec a game HQ can keep? (a file or the JSON itself)
    python3 app/games.py new SPEC               make the game (the team, from the map)
    python3 app/games.py spec GAME SPEC         change a game's design, keeping everything played
    python3 app/games.py tick [done|x|clear] [--track T] [--day D] [--game G]
    python3 app/games.py count TRACK N [--set] [--day D] [--game G]
    python3 app/games.py note "TEXT" [--day D] [--game G]
    python3 app/games.py diary "TEXT" [--feel F] [--track T] [--at "YYYY-MM-DD HH:MM"] [--game G]
    python3 app/games.py week [N] "TEXT" [--game G]     the look back on week N (default the last week that ended)
    python3 app/games.py debrief "TEXT" [--game G]      the look back at the end: fun, useful, learned
    python3 app/games.py undo                   puts back the last change made here, if nothing changed since

GAME is a game's id or a few words of its name; without --game it's the one game being played (or set up, or looked
back on) right now. D is a date (YYYY-MM-DD), today or yesterday. Every change takes --by "<who>".
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # HQ
FILE = "HQ/games.json"  # in the workspace
WRITES = ("new", "spec", "tick", "count", "note", "diary", "week", "debrief", "undo")
_lock = threading.Lock()
KEEP_LOG = 300  # the last changes a game keeps, newest first


def folder() -> Path:
    return Path(os.environ.get("HQ_FOLDER") or os.path.realpath(os.environ.get("HQ_WORKSPACE", str(ROOT / "workspace"))))


def path() -> Path:
    return Path(os.environ.get("HQ_GAMES") or folder() / FILE)


def _undo_file() -> Path:
    return Path(os.environ.get("HQ_GAMES_UNDO") or ROOT / "scratch" / "games-undo.json")


def _today() -> date:
    t = os.environ.get("HQ_GAMES_TODAY")  # the happy flows' own today
    return date.fromisoformat(t) if t else date.today()


def _now() -> str:
    return _today().isoformat() + datetime.now().strftime(" %H:%M")


# ---- the kinds of tracks -------------------------------------------------------------------------------------
# Each kind: `take(track, old, value, add)` gives the day's new value (or raises ValueError in plain words), and
# `sum(track, days, played)` what the track comes to over the days played so far. A new kind is a new entry here and a
# drawer of the same name in web/games.js.

def _tick_take(t, old, value, add):
    v = str(value or "done").strip().lower()
    v = {"yes": "done", "did": "done", "tick": "done", "✓": "done", "no": "x", "didn't": "x", "missed": "x",
         "none": "clear", "": "done"}.get(v, v)
    if v not in ("done", "x", "clear"):
        raise ValueError(f"A tick is done, x or clear, not {value!r}.")
    return None if v == "clear" else v


def _tick_sum(t, days, played):
    done = sum(1 for d in played if days.get(d, {}).get(t["id"]) == "done")
    x = sum(1 for d in played if days.get(d, {}).get(t["id"]) == "x")
    return {"done": done, "x": x, "open": len(played) - done - x, "played": len(played),
            "share": round(done / len(played), 3) if played else None}


def _count_take(t, old, value, add):
    try:
        n = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError(f"A count is a number, not {value!r}.")
    n = (old or 0) + n if add else n
    if n < 0:
        raise ValueError("A count can't go below nothing.")
    return int(n) if float(n).is_integer() else round(n, 2)


def _count_sum(t, days, played):
    per = [days.get(d, {}).get(t["id"]) or 0 for d in played]
    total = sum(per)
    out = {"total": int(total) if float(total).is_integer() else round(total, 2), "days": len(played)}
    if t.get("target"):
        out["target"] = t["target"]
        out["share"] = round(total / t["target"], 3)
    if t.get("per_day"):
        hit = sum(1 for v in per if v >= t["per_day"])
        out["per_day"] = t["per_day"]
        out["days_hit"] = hit
        out["share_days"] = round(hit / len(played), 3) if played else None
    return out


def _diary_take(t, old, value, add):  # diary entries go to the game's own list, not a day's value
    raise ValueError("A diary takes entries: games.py diary \"what happened\" --feel …")


def _diary_sum(t, days, played, entries=()):
    return {"entries": len(entries)}


KINDS = {
    "tick": {"take": _tick_take, "sum": _tick_sum, "line": "a day done or not: done, x (didn't), or nothing yet"},
    "count": {"take": _count_take, "sum": _count_sum,
              "line": "a number a day, added to as often as you like, with a target if you want and a graph"},
    "diary": {"take": _diary_take, "sum": _diary_sum,
              "line": "entries with the time, what happened and how it felt, to trace back later"},
}


# ---- the file ------------------------------------------------------------------------------------------------

def _load() -> dict:
    try:
        d = json.loads(path().read_text(encoding="utf8"))
    except FileNotFoundError:
        return {"games": []}
    except ValueError:
        raise ValueError(f"{FILE} isn't readable JSON; fix it by hand first.")
    if not isinstance(d, dict) or not isinstance(d.get("games"), list):
        raise ValueError(f"{FILE} has no list of games; fix it by hand first.")
    return d


def _raw() -> str:
    try:
        return path().read_text(encoding="utf8")
    except FileNotFoundError:
        return ""


def _save(d: dict, before: str) -> None:
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(d, ensure_ascii=False, indent=1) + "\n"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf8")
    os.replace(tmp, p)
    try:
        u = _undo_file()
        u.parent.mkdir(parents=True, exist_ok=True)
        u.write_text(json.dumps({"before": before, "after": hashlib.sha1(text.encode()).hexdigest()}), encoding="utf8")
    except OSError:
        pass


# ---- a game's shape ------------------------------------------------------------------------------------------

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "game"


def check_spec(spec) -> list[str]:
    """What's wrong with a spec, in plain words; empty when it's a game HQ can keep."""
    if not isinstance(spec, dict):
        return ["A spec is a JSON object."]
    bad = []
    if not str(spec.get("name") or "").strip():
        bad.append("It needs a name.")
    try:
        date.fromisoformat(str(spec.get("start")))
    except ValueError:
        bad.append("It needs a start: the first day of the six weeks, YYYY-MM-DD.")
    w = spec.get("weeks", 6)
    if not isinstance(w, int) or not 1 <= w <= 26:
        bad.append("weeks is a whole number from 1 to 26 (six by default).")
    tracks = spec.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        bad.append("It needs at least one track (what it keeps track of).")
        tracks = []
    ids = []
    for t in tracks:
        if not isinstance(t, dict) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,30}", str(t.get("id") or "")):
            bad.append(f"Every track has an id of small letters, digits, - or _: {t!r}.")
            continue
        if t["id"] in ids:
            bad.append(f"Two tracks have the id {t['id']}.")
        ids.append(t["id"])
        if t.get("kind") not in KINDS:
            bad.append(f"Track {t['id']}: the kind is one of {', '.join(KINDS)} (or a new one added to KINDS), "
                       f"not {t.get('kind')!r}.")
        for k in ("target", "per_day"):
            if k in t and not (isinstance(t[k], (int, float)) and t[k] > 0):
                bad.append(f"Track {t['id']}: {k} is a number above nothing.")
        if "feel" in t and not (isinstance(t["feel"], list) and all(isinstance(x, str) for x in t["feel"])):
            bad.append(f"Track {t['id']}: feel is a list of words.")
    win = spec.get("win")
    if win is not None:
        if not isinstance(win, dict):
            bad.append("win is an object: {\"track\": …, \"share\": …} or {\"total\": …} or {\"text\": …}.")
        elif win.get("track") is not None:
            if win["track"] not in ids:
                bad.append(f"The win line's track {win['track']!r} isn't one of the tracks.")
            if not any(k in win for k in ("share", "total")):
                bad.append("A win line on a track says a share (0.9) or a total (60).")
            if "share" in win and not (isinstance(win["share"], (int, float)) and 0 < win["share"] <= 1):
                bad.append("A win share is between 0 and 1, like 0.9.")
        elif not win.get("text"):
            bad.append("A win line names a track, or says it in words (text).")
    for g in spec.get("graphs") or []:
        if not isinstance(g, dict) or not g.get("tracks") or any(x not in ids for x in g.get("tracks", [])):
            bad.append(f"A graph names tracks of this game: {g!r}.")
    return bad


def _dates(g: dict) -> dict:
    start = date.fromisoformat(g["start"])
    n = int(g.get("weeks", 6)) * 7
    return {"setup": start - timedelta(days=7), "start": start, "end": start + timedelta(days=n - 1),
            "look_end": start + timedelta(days=n + 6), "days": n}


def _phase(g: dict, today: date | None = None) -> str:
    t, d = today or _today(), _dates(g)
    if g.get("closed"):
        return "past"
    if t < d["setup"]:
        return "coming"
    if t < d["start"]:
        return "setup"
    if t <= d["end"]:
        return "playing"
    if t <= d["look_end"]:
        return "looking back"
    return "past"


def _played(g: dict, today: date | None = None) -> list[str]:
    """The days played so far (today counts once it's started; up to the last day)."""
    t, d = today or _today(), _dates(g)
    last = min(t, d["end"])
    n = (last - d["start"]).days + 1
    return [(d["start"] + timedelta(days=i)).isoformat() for i in range(max(0, n))]


def _sum(g: dict, t: dict, played: list[str]) -> dict:
    k = KINDS[t["kind"]]
    if t["kind"] == "diary":
        return k["sum"](t, g.get("days", {}), played, [e for e in g.get("diary", []) if e.get("track") == t["id"]])
    return k["sum"](t, g.get("days", {}), played)


def _win(g: dict, sums: dict, played: list[str]) -> dict:
    w = g.get("win") or {}
    out = {"text": g.get("win_text") or w.get("text") or ""}
    tr = next((t for t in g["tracks"] if t["id"] == w.get("track")), None)
    if not tr:
        return out
    s, total_days = sums[tr["id"]], _dates(g)["days"]
    if "share" in w and tr["kind"] == "tick":
        need = int(-(-w["share"] * total_days // 1))
        out.update(share=w["share"], now=s["share"], need=need, have=s["done"], left=total_days - len(played),
                   on_track=s["share"] is None or s["share"] >= w["share"],
                   reachable=s["done"] + total_days - len(played) >= need)
        if not out["text"]:
            out["text"] = f"{round(w['share'] * 100)}% of the days"
    elif "total" in w:
        have = s.get("total", 0)
        out.update(total=w["total"], have=have, on_track=have >= w["total"] * len(played) / total_days if played else True)
        if not out["text"]:
            out["text"] = f"{w['total']} {tr.get('label') or tr['id']}"
    elif "share" in w and tr.get("per_day"):
        out.update(share=w["share"], now=s.get("share_days"), have=s.get("days_hit", 0),
                   on_track=s.get("share_days") is None or s["share_days"] >= w["share"],
                   reachable=(s.get("days_hit", 0) + total_days - len(played)) >= w["share"] * total_days)
        if not out["text"]:
            out["text"] = f"{tr['per_day']} a day on {round(w['share'] * 100)}% of the days"
    out["won"] = (out.get("have", 0) >= out.get("need", out.get("total", float("inf"))) if "need" in out or "total" in out
                  else None)
    return out


def view(g: dict, today: date | None = None) -> dict:
    """One game with everything the app shows: its phase, the day, every track added up, the win line, the weeks."""
    t = today or _today()
    d, played = _dates(g), _played(g, t)
    sums = {tr["id"]: _sum(g, tr, played) for tr in g["tracks"]}
    weeks = []
    for i in range(int(g.get("weeks", 6))):
        ws = d["start"] + timedelta(days=7 * i)
        weeks.append({"n": i + 1, "from": ws.isoformat(), "to": (ws + timedelta(days=6)).isoformat(),
                      "ended": t > ws + timedelta(days=6), "look": (g.get("looks") or {}).get(str(i + 1), "")})
    ph = _phase(g, t)
    return {**{k: g.get(k) for k in ("id", "name", "for", "game", "rules", "win_text", "tracks", "graphs", "weeks",
                                      "made", "by", "debrief", "closed")},
            "phase": ph, "setup": d["setup"].isoformat(), "start": d["start"].isoformat(), "end": d["end"].isoformat(),
            "look_end": d["look_end"].isoformat(), "length": d["days"],
            "day": len(played) if ph == "playing" else None, "today": t.isoformat(),
            "days": g.get("days", {}), "diary": sorted(g.get("diary", []), key=lambda e: e.get("at", ""), reverse=True),
            "sums": sums, "win": _win(g, sums, played), "looks": weeks, "log": (g.get("log") or [])[:20]}


def read() -> dict:
    """Everything the app gets: the games being played or coming first, then the past ones, newest first."""
    try:
        d = _load()
    except ValueError as e:
        return {"games": [], "error": str(e)}
    games = [view(g) for g in d["games"]]
    order = {"playing": 0, "setup": 1, "looking back": 2, "coming": 3, "past": 4}
    games.sort(key=lambda v: (order[v["phase"]], v["start"] if v["phase"] != "past" else "", v["start"]), reverse=False)
    past = sorted([g for g in games if g["phase"] == "past"], key=lambda v: v["start"], reverse=True)
    return {"games": [g for g in games if g["phase"] != "past"] + past,
            "kinds": {k: v["line"] for k, v in KINDS.items()}}


# ---- finding a game, a day, a track --------------------------------------------------------------------------

def _find(d: dict, ref: str | None) -> dict:
    games = d["games"]
    if not games:
        raise KeyError("There's no six-week game yet. One is designed on a call first, then the team makes it.")
    if not ref:
        live = [g for g in games if _phase(g) in ("playing", "setup", "looking back")]
        playing = [g for g in live if _phase(g) == "playing"]
        if len(playing) == 1:  # the one being played wins over one being set up or looked back on
            return playing[0]
        if len(live) == 1:
            return live[0]
        if not live:
            raise KeyError("No game is being played right now; say which one: " + ", ".join(g["name"] for g in games))
        raise KeyError("More than one game is on; say which one: " + ", ".join(g["name"] for g in live))
    r = ref.strip().lower()
    hit = [g for g in games if g["id"] == r] or [g for g in games if g["name"].lower() == r]
    if not hit:
        words = r.split()
        hit = [g for g in games if all(w in (g["name"] + " " + g["id"]).lower() for w in words)]
    if len(hit) == 1:
        return hit[0]
    if not hit:
        raise KeyError(f"No game called {ref!r}. There are: " + ", ".join(g["name"] for g in games))
    raise KeyError(f"{ref!r} fits more than one game: " + ", ".join(g["name"] for g in hit))


def _day(s: str | None) -> str:
    s = (s or "today").strip().lower()
    if s == "today":
        return _today().isoformat()
    if s == "yesterday":
        return (_today() - timedelta(days=1)).isoformat()
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError:
        raise ValueError(f"A day is YYYY-MM-DD, today or yesterday, not {s!r}.")


def _track(g: dict, ref: str | None, kinds: tuple) -> dict:
    ts = [t for t in g["tracks"] if t["kind"] in kinds]
    if ref:
        hit = [t for t in ts if t["id"] == ref.lower()] or [t for t in ts if ref.lower() in (t.get("label") or "").lower()]
        if len(hit) == 1:
            return hit[0]
        raise KeyError(f"{g['name']} has no {'/'.join(kinds)} track {ref!r}"
                       + (f"; it has: {', '.join(t['id'] for t in ts)}" if ts else "") + ".")
    if len(ts) == 1:
        return ts[0]
    if not ts:
        raise KeyError(f"{g['name']} doesn't keep a {'/'.join(kinds)}.")
    raise KeyError(f"{g['name']} has more than one; say which: {', '.join(t['id'] for t in ts)}.")


def _playing_day(g: dict, day: str) -> None:
    d = _dates(g)
    if not d["start"].isoformat() <= day <= d["end"].isoformat():
        raise ValueError(f"{g['name']} is played from {d['start'].isoformat()} to {d['end'].isoformat()}; "
                         f"{day} isn't one of its days.")
    if day > _today().isoformat():
        raise ValueError(f"{day} hasn't come yet.")


def _log(g: dict, what: str, by: str) -> None:
    g.setdefault("log", []).insert(0, {"at": _now(), "by": by or "", "what": what})
    del g["log"][KEEP_LOG:]


# ---- changes -------------------------------------------------------------------------------------------------

def _change(fn):
    def run(*a, **k):
        with _lock:
            before = _raw()
            d = _load()
            said = fn(d, *a, **k)
            _save(d, before)
            return {"ok": True, "said": said}
    run.__name__ = fn.__name__
    run.__doc__ = fn.__doc__
    return run


def _spec_of(spec) -> dict:
    if isinstance(spec, dict):
        return spec
    s = str(spec).strip()
    if not s.startswith("{"):
        s = Path(s).read_text(encoding="utf8")
    try:
        return json.loads(s)
    except ValueError as e:
        raise ValueError(f"The spec isn't JSON: {e}")


_SPEC_KEYS = ("name", "for", "game", "rules", "start", "weeks", "win", "win_text", "tracks", "graphs")


@_change
def new(d, spec, by: str = "") -> str:
    """Make a game from its spec (the team, from the user's map)."""
    spec = _spec_of(spec)
    bad = check_spec(spec)
    if bad:
        raise ValueError(" ".join(bad))
    gid = spec.get("id") or _slug(spec["name"] + "-" + spec["start"][:7])
    if any(g["id"] == gid for g in d["games"]):
        raise ValueError(f"There's already a game {gid}; change it with spec, or give the new one its own id.")
    g = {"id": gid, **{k: spec[k] for k in _SPEC_KEYS if k in spec}, "made": _now(), "by": by,
         "days": {}, "diary": [], "looks": {}, "log": []}
    g.setdefault("weeks", 6)
    _log(g, "made", by)
    d["games"].append(g)
    v = _dates(g)
    return (f"{g['name']} is made: set up from {v['setup'].isoformat()}, played {v['start'].isoformat()} to "
            f"{v['end'].isoformat()}, looked back on until {v['look_end'].isoformat()}.")


@_change
def respec(d, ref: str, spec, by: str = "") -> str:
    """Change a game's design, keeping every day played, the diary and the looks back."""
    g = _find(d, ref)
    spec = _spec_of(spec)
    merged = {**{k: g[k] for k in _SPEC_KEYS if k in g}, **{k: spec[k] for k in _SPEC_KEYS if k in spec}}
    bad = check_spec(merged)
    if bad:
        raise ValueError(" ".join(bad))
    for k in _SPEC_KEYS:
        if k in merged:
            g[k] = merged[k]
    _log(g, "design changed: " + ", ".join(k for k in _SPEC_KEYS if k in spec), by)
    return f"{g['name']}'s design is changed; everything played is kept."


@_change
def tick(d, value: str = "done", track: str = "", day: str = "", game: str = "", by: str = "") -> str:
    g = _find(d, game)
    t = _track(g, track, ("tick",))
    day = _day(day)
    _playing_day(g, day)
    row = g.setdefault("days", {}).setdefault(day, {})
    v = KINDS["tick"]["take"](t, row.get(t["id"]), value, False)
    if v is None:
        row.pop(t["id"], None)
    else:
        row[t["id"]] = v
    if not row:
        g["days"].pop(day, None)
    word = {"done": "done", "x": "an X", None: "cleared"}[v]
    _log(g, f"{day} {t['id']}: {word}", by)
    s = _tick_sum(t, g["days"], _played(g))
    return (f"{g['name']}, {day}: {word}. So far {s['done']} of {s['played']} days done"
            + (f" ({round(s['share'] * 100)}%)." if s["share"] is not None else "."))


@_change
def count(d, track: str, n, set_: bool = False, day: str = "", game: str = "", by: str = "") -> str:
    g = _find(d, game)
    t = _track(g, track, ("count",))
    day = _day(day)
    _playing_day(g, day)
    row = g.setdefault("days", {}).setdefault(day, {})
    row[t["id"]] = KINDS["count"]["take"](t, row.get(t["id"]), n, not set_)
    _log(g, f"{day} {t['id']}: {'set to' if set_ else 'plus'} {n}", by)
    s = _count_sum(t, g["days"], _played(g))
    label = t.get("label") or t["id"]
    return (f"{g['name']}, {day}: {label} {row[t['id']]} today, {s['total']} so far"
            + (f" of {t['target']}." if t.get("target") else "."))


@_change
def note(d, text: str, day: str = "", game: str = "", by: str = "") -> str:
    g = _find(d, game)
    text = " ".join(str(text).split())[:2000]
    if not text:
        raise ValueError("Nothing to note.")
    day = _day(day)
    row = g.setdefault("days", {}).setdefault(day, {})
    row["note"] = (row.get("note", "") + " · " if row.get("note") else "") + text
    _log(g, f"{day} note", by)
    return f"{g['name']}, {day}: noted."


@_change
def diary(d, text: str, feel: str = "", track: str = "", at: str = "", game: str = "", by: str = "") -> str:
    g = _find(d, game)
    t = _track(g, track, ("diary",))
    text = " ".join(str(text).split())[:2000]
    if not text:
        raise ValueError("Nothing to write in the diary.")
    feel = feel.strip().lower()
    if feel and t.get("feel") and feel not in [f.lower() for f in t["feel"]]:
        raise ValueError(f"How it felt is one of: {', '.join(t['feel'])}.")
    when = at.strip() or _now()
    if not re.fullmatch(r"\d{4}-\d\d-\d\d( \d\d:\d\d)?", when):
        raise ValueError("--at is YYYY-MM-DD HH:MM.")
    g.setdefault("diary", []).append({"at": when, "track": t["id"], "text": text, "feel": feel, "by": by})
    _log(g, f"diary {when[:10]}", by)
    return f"{g['name']}: in the {t.get('label') or 'diary'}, {when}" + (f", {feel}." if feel else ".")


@_change
def week(d, n, text: str, game: str = "", by: str = "") -> str:
    g = _find(d, game)
    text = " ".join(str(text).split())[:4000]
    if not text:
        raise ValueError("Nothing to write for the week.")
    weeks = int(g.get("weeks", 6))
    if n in (None, ""):
        done = (min(_today(), _dates(g)["end"] + timedelta(days=1)) - _dates(g)["start"]).days // 7
        if done < 1:
            raise ValueError(f"{g['name']}'s first week hasn't ended yet.")
        n = min(done, weeks)
    n = int(n)
    if not 1 <= n <= weeks:
        raise ValueError(f"{g['name']} has weeks 1 to {weeks}.")
    g.setdefault("looks", {})[str(n)] = text
    _log(g, f"week {n} looked back on", by)
    return f"{g['name']}: the look back on week {n} is kept."


@_change
def debrief(d, text: str, game: str = "", by: str = "") -> str:
    g = _find(d, game)
    text = " ".join(str(text).split())[:6000]
    if not text:
        raise ValueError("Nothing to write for the debrief.")
    g["debrief"] = text
    _log(g, "debrief", by)
    return f"{g['name']}: the debrief is kept."


def undo() -> dict:
    with _lock:
        try:
            u = json.loads(_undo_file().read_text(encoding="utf8"))
        except (OSError, ValueError):
            return {"ok": False, "said": "Nothing to undo."}
        now = _raw()
        if hashlib.sha1(now.encode()).hexdigest() != u.get("after"):
            return {"ok": False, "said": "The games changed since, so the last change can't be undone from here."}
        p = path()
        if u.get("before"):
            p.write_text(u["before"], encoding="utf8")
        else:
            p.unlink(missing_ok=True)
        _undo_file().unlink(missing_ok=True)
        return {"ok": True, "said": "Undone."}


# ---- to say out loud -----------------------------------------------------------------------------------------

def _pct(x) -> str:
    return "" if x is None else f"{round(x * 100)}%"


def line(v: dict) -> str:
    head = f"{v['name']} ({v['phase']}"
    if v["phase"] == "playing":
        head += f", day {v['day']} of {v['length']}"
    elif v["phase"] in ("coming", "setup"):
        head += f", starts {v['start']}"
    elif v["phase"] == "looking back":
        head += f", look back until {v['look_end']}"
    head += ")"
    bits = []
    for t in v["tracks"]:
        s = v["sums"][t["id"]]
        label = t.get("label") or t["id"]
        if t["kind"] == "tick":
            today = v["days"].get(v["today"], {}).get(t["id"])
            bits.append(f"{label}: {s['done']} of {s['played']} days done" + (f" ({_pct(s['share'])})" if s["share"] is not None else "")
                        + ("" if v["phase"] != "playing" else ", today " + ({"done": "done", "x": "an X"}.get(today, "not ticked yet"))))
        elif t["kind"] == "count":
            bits.append(f"{label}: {s['total']}" + (f" of {t['target']}" if t.get("target") else ""))
        elif t["kind"] == "diary":
            bits.append(f"{label}: {s['entries']} {'entry' if s['entries'] == 1 else 'entries'}")
        else:
            bits.append(f"{label}: {json.dumps(s, ensure_ascii=False)}")
    w = v["win"]
    if w.get("text"):
        how = ""
        if v["phase"] == "past" and w.get("won") is not None:
            how = ", won" if w["won"] else ", not won"
        elif v["phase"] == "playing" and w.get("on_track") is not None:
            how = (", on track" if w["on_track"] else ", behind, still within reach" if w.get("reachable", True)
                   else ", out of reach now")
        bits.append("win line: " + w["text"] + how)
    open_weeks = [x["n"] for x in v["looks"] if x["ended"] and not x["look"]]
    if open_weeks and v["phase"] != "past":
        bits.append("weeks not looked back on yet: " + ", ".join(map(str, open_weeks)))
    if v["phase"] in ("looking back", "past") and not v.get("debrief"):
        bits.append("no debrief yet")
    return head + ": " + "; ".join(bits) + "."


def summary() -> str:
    d = read()
    if d.get("error"):
        return d["error"]
    if not d["games"]:
        return "No six-week game yet."
    now = [g for g in d["games"] if g["phase"] != "past"]
    past = [g for g in d["games"] if g["phase"] == "past"]
    out = [line(v) for v in now]
    if past:
        out.append("Past games, to look back at: " + ", ".join(f"{g['name']} ({g['start'][:7]})" for g in past) + ".")
    return "\n".join(out)


def show(ref: str) -> str:
    d = _load()
    v = view(_find(d, ref))
    out = [line(v)]
    for k in ("for", "game", "rules"):
        if v.get(k):
            out.append(f"{k.capitalize()}: {v[k]}")
    out.append(f"Setup {v['setup']}, played {v['start']} to {v['end']}, look back until {v['look_end']}.")
    for day in sorted(v["days"]):
        row = v["days"][day]
        out.append(f"  {day}: " + ", ".join(f"{k} {row[k]}" for k in row))
    for e in v["diary"]:
        out.append(f"  diary {e['at']}{' (' + e['feel'] + ')' if e.get('feel') else ''}: {e['text']}")
    for w in v["looks"]:
        if w["look"]:
            out.append(f"  week {w['n']}: {w['look']}")
    if v.get("debrief"):
        out.append(f"  debrief: {v['debrief']}")
    return "\n".join(out)


# ---- the command line ----------------------------------------------------------------------------------------

def _opt(args: list[str], name: str, flag: bool = False):
    if name in args:
        i = args.index(name)
        if flag:
            del args[i]
            return True
        v = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
        return v
    return False if flag else ""


def run(argv: list[str]) -> tuple[int, str]:
    """One command, here (never handed over): its exit code and what it says."""
    args = list(argv)
    by, game, day, track = _opt(args, "--by"), _opt(args, "--game"), _opt(args, "--day"), _opt(args, "--track")
    set_ = _opt(args, "--set", True)
    cmd = args[0] if args else "summary"
    try:
        if cmd == "summary":
            return 0, summary()
        if cmd == "json":
            return 0, json.dumps(read(), ensure_ascii=False, indent=1)
        if cmd == "show" and len(args) == 2:
            return 0, show(args[1])
        if cmd == "kinds":
            return 0, "\n".join(f"{k}: {v['line']}" for k, v in KINDS.items())
        if cmd == "check" and len(args) == 2:
            bad = check_spec(_spec_of(args[1]))
            return (1, " ".join(bad)) if bad else (0, "It's a game HQ can keep.")
        if cmd == "new" and len(args) == 2:
            return 0, new(args[1], by=by)["said"]
        if cmd == "spec" and len(args) == 3:
            return 0, respec(args[1], args[2], by=by)["said"]
        if cmd == "tick" and len(args) <= 2:
            return 0, tick(args[1] if len(args) > 1 else "done", track=track, day=day, game=game, by=by)["said"]
        if cmd == "count" and len(args) == 3:
            return 0, count(args[1], args[2], set_=set_, day=day, game=game, by=by)["said"]
        if cmd == "note" and len(args) == 2:
            return 0, note(args[1], day=day, game=game, by=by)["said"]
        if cmd == "diary" and len(args) >= 2:
            feel, at = _opt(args, "--feel"), _opt(args, "--at")
            return 0, diary(args[1], feel=feel, track=track, at=at, game=game, by=by)["said"]
        if cmd == "week" and len(args) in (2, 3):
            n, text = (args[1], args[2]) if len(args) == 3 else (None, args[1])
            return 0, week(n, text, game=game, by=by)["said"]
        if cmd == "debrief" and len(args) == 2:
            return 0, debrief(args[1], game=game, by=by)["said"]
        if cmd == "undo":
            r = undo()
            return (0 if r["ok"] else 1), r["said"]
        return 2, __doc__.strip()
    except (KeyError, ValueError) as e:
        return 1, str(e).strip("'\"")
    except OSError as e:
        return 1, f"Couldn't read or write the games: {e}"


def main(argv: list[str]) -> int:
    # H203: on the backup HQ a change goes to the main one, which writes it (role.WRITES), like the to-do list.
    if argv and argv[0] in WRITES and not os.environ.get("HQ_ROLE_HERE"):
        sys.path.insert(0, str(ROOT / "routine"))
        import role
        if role.is_backup():
            return role.forward("games", list(argv))
    code, text = run(argv)
    print(text)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
