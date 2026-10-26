"""H225: Life coaching as its own place in the app, with check-ins (21 October 2026).

The user's words on the call (21 October 2026, at 12:29): "Maybe there should be a separate place where we can get a
notification. Not a notification but I don't know, it changes colour or whatever, or you get the red dot ... You can
click on there and then we go back into this [life] coaching thing. ... in the background it gets tracked when those
moments should be. ... It guarantees that we have those points of contact. Otherwise it might just drift away." And,
the same call: "maybe we can just make it sort of like a [life] coaching module where you can click on the button.
You can see this checklist as well ... which layers you've checked off with the sessions ... We can actually make it
separate sessions so also it won't drift off ... a speed dial line to you where we just talk about life coaching,
where the weekly checkups come there".

For everyone with Life coaching on (the map workflow, workflows.py). Nothing of theirs is in HQ: it all comes from
their workspace.
    - The layers, read from their map.md with their checklist (workflows.check, H224): done, in progress, not started.
    - The check-ins, the moments read from their map and kept here in the background:
        week     the weekly look back, on the day and part of the day their map's `Check-ins:` line says (written in
                 the looking-back layer; without it, a line of their map that puts the look back on a weekday)
        game     each six-week game's debrief, from its look-back week on (games.py)
        checkin  the bigger check-in, every eight weeks in step with the games (H251): in each game's look-back week,
                 next to its debrief but its own session; without a game, every eight weeks (or the `Check-ins:`
                 line's "every N weeks" or "every N months") from the last one, or from when HQ first kept them
      One that's due shows a red dot on the Coaching button, until it's done (a call does it at the end, or Done in the
      app) or put off until tomorrow (Not now). No push notification.
    - The coaching line: a thread with the agent the workflow is best with (Pepper by default), like the direct line,
      in the workspace's HQ/coaching-line/. A check-in that comes due lands there as a line from her, without Claude.
      His texts are answered by direct_line.py with this folder and her (no phone notifications: nothing subscribes).

Kept in the workspace's HQ/coaching.json ({"first", "done": {key: when}, "later": {key: until}, "landed": [keys]}).
A fresh install has none, and nothing is due until their map has its moments.

    python3 app/coaching.py                 what's due, in a few lines (and the layers)
    python3 app/coaching.py json            everything the app shows
    python3 app/coaching.py due             only what's due
    python3 app/coaching.py done KEY        a check-in is through (KEY from the list: week:2026-W43, game:ID,
                                            checkin:2026-10-21; or just week, game, checkin for the one due now)
    python3 app/coaching.py later KEY       not now: until tomorrow morning
    python3 app/coaching.py refresh         look now: land what came due in the coaching line (tick.py, every minute)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # HQ
sys.path.insert(0, str(HERE))
import workflows  # noqa: E402

FILE = "HQ/coaching.json"  # in the workspace
LINE_DIR = "HQ/coaching-line"  # the coaching line's thread, in the workspace
WID = "map"
EVERY_WEEKS = 8  # the bigger check-in (H251): the games' rhythm, a setup week, six weeks and a look-back week
PARTS = {"morning": 9, "afternoon": 14, "evening": 19, "night": 21}  # a part of the day starts at
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_lock = threading.Lock()


def folder() -> Path:
    return Path(os.environ.get("HQ_WORKFLOWS_FOLDER") or os.environ.get("HQ_FOLDER") or os.path.realpath(os.environ.get("HQ_WORKSPACE", str(ROOT / "workspace"))))


def path() -> Path:
    return Path(os.environ.get("HQ_COACHING") or folder() / FILE)


def line_dir() -> Path:
    return Path(os.environ.get("HQ_COACHING_LINE") or folder() / LINE_DIR)


def _now() -> datetime:
    t = os.environ.get("HQ_COACHING_NOW")  # the happy flows' own now
    return datetime.fromisoformat(t) if t else datetime.now()


def workflow() -> dict | None:
    return workflows.find(WID)


def on(f: Path | None = None) -> bool:
    return WID in workflows.turned_on(f or folder())


def _load() -> dict:
    try:
        d = json.loads(path().read_text(encoding="utf8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(d: dict) -> None:
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    os.replace(tmp, p)


def _map_text(f: Path, w: dict) -> str:
    try:
        return (f / w["file"]).read_text(encoding="utf8")
    except OSError:
        return ""


# ---- the moments, from their map ----------------------------------------------------------------------------------

def _part_of(text: str) -> str:
    """The part of the day a line means: the last one it names ("after lunch" is the afternoon)."""
    t = text.lower().replace("after lunch", "afternoon")
    best, at = "", -1
    for p in PARTS:
        i = t.rfind(p)
        if i > at:
            best, at = p, i
    return best


def _time_of(text: str) -> tuple[int, int] | None:
    m = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def moments(text: str) -> dict:
    """The check-ins their map sets: {"week": {"day", "part", "at", "said", "from"} | None, "every": (n, "weeks"|"months"), "said"}.

    First the `Check-ins:` line (the guide's looking-back layer, In HQ); without one, a line elsewhere in the map
    that puts the weekly look back on a weekday. Nothing found: no weekly moment yet."""
    out = {"week": None, "every": (EVERY_WEEKS, "weeks"), "every_from": "default", "said": ""}
    line = next((l for l in text.splitlines() if l.strip().lower().startswith("check-ins:")), "")
    cands = []
    if line:
        out["said"] = line.split(":", 1)[1].strip()
        body = re.sub(r"\[.*?\]", "", out["said"])
        m = re.search(r"every\s+(\w+)\s+(weeks?|months?)", body, re.I)
        if m:
            word = m.group(1).lower()
            n = int(word) if word.isdigit() else {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                                                  "eight": 8, "nine": 9, "ten": 10, "twelve": 12}.get(word)
            unit = "weeks" if m.group(2).lower().startswith("week") else "months"
            if n and 1 <= n <= (52 if unit == "weeks" else 12):
                out["every"], out["every_from"] = (n, unit), "map"
        for part in re.split(r";|\.\s", body):
            if re.search(r"week|look ?back", part, re.I):
                cands.append((part, "line"))
    if not cands:
        for l in text.splitlines():
            ll = l.lower()
            if re.search(r"week(ly)?'?s? (look ?back|review)", ll) and any(d in ll for d in DAYS):
                cands.append((l, "map"))
                break
    for part, src in cands:
        ll = part.lower()
        day = next((i for i, d in enumerate(DAYS) if re.search(r"\b" + d + r"s?\b", ll)), None)
        if day is None:
            continue
        p, at = _part_of(part), _time_of(part)
        hour, minute = at if at else (PARTS.get(p, PARTS["morning"]), 0)
        out["week"] = {"day": day, "part": p or ("" if at else "morning"), "at": f"{hour:02d}:{minute:02d}",
                       "said": re.sub(r"\s+", " ", part).strip()[:200], "from": src}
        break
    return out


def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, m, day)
        except ValueError:
            continue
    return date(y, m, 28)


def _week_key(t: datetime) -> str:
    y, w, _ = t.isocalendar()
    return f"week:{y}-W{w:02d}"


def _week_moment(now: datetime, wk: dict) -> datetime:
    """The latest weekly moment at or before now."""
    h, m = (int(x) for x in wk["at"].split(":"))
    monday = (now - timedelta(days=now.weekday())).replace(hour=h, minute=m, second=0, microsecond=0)
    at = monday + timedelta(days=wk["day"])
    return at if at <= now else at - timedelta(days=7)


def _day_words(d: datetime | date, now: datetime) -> str:
    dd = d.date() if isinstance(d, datetime) else d
    if dd == now.date():
        return "today"
    if dd == now.date() - timedelta(days=1):
        return "yesterday"
    if dd == now.date() + timedelta(days=1):
        return "tomorrow"
    return f"{dd:%A} {dd.day} {dd:%B}"


def _at_words(at: datetime, now: datetime, part: str) -> str:
    """"this morning", "Friday 23 October morning", "today at 18:30"."""
    day = _day_words(at, now)
    if part in PARTS:
        return f"this {part}" if day == "today" else f"{day} {part}"
    return f"{day} at {part}"


def _num(n: int) -> str:
    return {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
            10: "ten", 12: "twelve"}.get(n, str(n))


def _games() -> list[dict]:
    try:
        import games as _g
        return _g.read().get("games", [])
    except Exception:
        return []


def checkins(d: dict, text: str, now: datetime | None = None, games: list | None = None) -> list[dict]:
    """Every check-in the app shows: the weekly look back, each game's debrief, the bigger check-in; each with its
    key, whether it's due, and when the next one is."""
    now = now or _now()
    mo = moments(text)
    first = datetime.fromisoformat(d["first"]) if d.get("first") else now
    done, later = d.get("done") or {}, d.get("later") or {}
    out = []

    def state(key: str, from_: datetime | None) -> dict:
        if key in done:
            return {"due": False, "done": done[key]}
        until = later.get(key)
        if until and now < datetime.fromisoformat(until):
            return {"due": False, "later": until}
        return {"due": from_ is not None and from_ <= now}

    wk = mo["week"]
    if wk:
        last = _week_moment(now, wk)
        part = wk["part"] or wk["at"]
        # The latest moment is due until it's done; one before HQ first kept their check-ins doesn't count.
        st = state(_week_key(last), last) if last >= first else {"due": False}
        at = last if (st["due"] or st.get("later")) else last + timedelta(days=7)
        if not (st["due"] or st.get("later")):
            st = state(_week_key(at), None)
        out.append({"key": _week_key(at), "kind": "week", "title": "The weekly look back", **st,
                    "from": at.isoformat(timespec="minutes"), "next": (last + timedelta(days=7)).isoformat(timespec="minutes"),
                    "when": f"{DAYS[wk['day']].capitalize()}s, {part}",
                    "line": ("Since " + _at_words(at, now, part) if st["due"] else
                             "Not now: back tomorrow morning" if st.get("later") else
                             "Next: " + _at_words(at, now, part)),
                    "layer": 6, "group": "week", "said": wk["said"],
                    "score": _score(games) if st["due"] else []})
    for g in (games if games is not None else _games()):
        if g.get("phase") not in ("looking back", "past") or (g.get("debrief") or "").strip():
            continue
        end = date.fromisoformat(g["end"])
        if g.get("phase") == "past" and now.date() > date.fromisoformat(g["look_end"]) + timedelta(days=14):
            continue  # long gone without a debrief: no dot for ever
        key = f"game:{g['id']}"
        start = datetime.combine(end + timedelta(days=1), datetime.min.time()).replace(hour=PARTS["morning"])
        st = state(key, start)
        out.append({"key": key, "kind": "game", "title": f"The debrief of {g.get('name') or 'the game'}", **st,
                    "from": start.isoformat(timespec="minutes"), "game": g["id"],
                    "line": "The game's six weeks are through" if st["due"] else "After the game",
                    "layer": 6, "group": "game"})
    if not re.search(r"^Status: done", text, re.M):
        return out  # the bigger check-in counts from the first layer that's done: a fresh map has none
    base = datetime.fromisoformat(max([v for k, v in done.items() if k.startswith("checkin:")] or [first.isoformat()]))
    n, unit = mo["every"]
    every = f"{_num(n)} {unit if n != 1 else unit[:-1]}"
    # H251: in step with the games: the start of each game's look-back week, after the last one and after HQ first
    # kept their check-ins; its own key, apart from the game's debrief. No game ahead: every eight weeks.
    lbs = sorted({datetime.combine(date.fromisoformat(g["end"]) + timedelta(days=1), datetime.min.time())
                  .replace(hour=PARTS["morning"]) for g in (games if games is not None else _games()) if g.get("end")})
    lbs = [t for t in lbs if t.date() >= first.date() and t.date() > base.date() and f"checkin:{t.date().isoformat()}" not in done]
    if lbs:
        due_at, game = lbs[0], True
    else:
        nxt = _add_months(base.date(), n) if unit == "months" else base.date() + timedelta(weeks=n)
        due_at, game = datetime.combine(nxt, datetime.min.time()).replace(hour=PARTS["morning"]), False
    key = f"checkin:{due_at.date().isoformat()}"
    st = state(key, due_at)
    out.append({"key": key, "kind": "checkin", "title": "The bigger check-in", **st,
                "from": due_at.isoformat(timespec="minutes"), "every": n, "unit": unit, "with_game": game,
                "when": "Every eight weeks, in each game's look-back week" if game else f"Every {every}",
                "line": (("A game's six weeks are through" if game else f"It's been {every}") if st["due"] else
                         "Not now: back tomorrow morning" if st.get("later") else
                         f"Next: {_day_words(due_at, now)}" + (", in the game's look-back week" if game else "")),
                "layer": 6, "group": "check-in"})
    return out


# ---- the layers ----------------------------------------------------------------------------------------------------

def layers(f: Path, w: dict, text: str) -> list[dict]:
    rows = workflows.check(f, w)
    qs = workflows.questions(w)
    mine = {n: body for n, _name, body in workflows._layers(text)}
    out = []
    for r in rows:
        n = r["layer"]
        marks = {}
        for line in mine.get(n, "").splitlines():
            m = workflows.LINE.match(line.strip())
            if m:
                marks[(m.group(2) or "") + m.group(3)] = (m.group(1), m.group(4))
        items = []
        for k, q in qs.get(n, []):
            mk, rest = marks.get(k, ("open", q))
            note = rest.split(" · ", 1)[1] if " · " in rest else ""
            items.append({"key": k, "q": q, "mark": mk, "note": note})
        st = r["status"].lower()
        word = ("done" if st.startswith("done") else "not started" if (not st or st.startswith("not started"))
                else "in progress")
        out.append({"n": n, "name": r["name"] or "", "status": r["status"], "word": word, "counts": r["counts"],
                    "total": r["total"], "can_close": r["can_close"], "items": items})
    return out


# ---- what the app gets ---------------------------------------------------------------------------------------------

def read(f: Path | None = None, now: datetime | None = None, games: list | None = None) -> dict:
    f = f or folder()
    w = workflow()
    if not w or not on(f):
        return {"on": False, "layers": [], "checkins": [], "due": 0, "thread": []}
    text = _map_text(f, w)
    d = _load()
    import agents as _agents
    a = _agents.find(f, w.get("agent"))
    out = {"on": True, "agent": {"id": a["id"], "name": a["name"]}, "named": workflows.own_name(f, w),
           "map": bool(text), "start": w.get("start", ""), "kept": bool(d.get("first"))}
    out["layers"] = layers(f, w, text) if text else []
    out["checkins"] = checkins(d, text, now, games) if (text and d.get("first")) else []
    out["due"] = sum(1 for c in out["checkins"] if c["due"])
    out["thread"] = thread(last=200)
    out["waiting"] = bool(out["thread"]) and out["thread"][-1]["from"] == "me"
    return out


def refresh(f: Path | None = None, now: datetime | None = None, games: list | None = None) -> list[str]:
    """The background look: start keeping their check-ins once their map exists, and land each one that comes due in
    the coaching line, once. Returns the keys landed."""
    f = f or folder()
    w = workflow()
    if not w or not on(f):
        return []
    text = _map_text(f, w)
    if not text:
        return []
    with _lock:
        d = _load()
        if not d.get("first"):
            d["first"] = (now or _now()).isoformat(timespec="minutes")
            _save(d)
        landed = []
        seen = set(d.get("landed") or [])
        for c in checkins(d, text, now, games):
            if c["due"] and c["key"] not in seen:
                _land(c)
                seen.add(c["key"])
                landed.append(c["key"])
        if landed:
            d["landed"] = sorted(seen)[-60:]
            _save(d)
    return landed


LAND = {"week": ["Time for our weekly look back. Tap Start when you're ready, and we'll go through the week together.",
                 "It's that moment again: the weekly look back. Start it here whenever you're ready."],
        "game": ["{title}: the six weeks are through. Shall we look back on it? Tap Start when you're ready."],
        "checkin": ["Eight weeks are through: time for the bigger check-in on the whole picture. It's its own session, apart "
                    "from the game's debrief. Tap Start when you're ready."]}


def _score(games: list | None = None) -> list[str]:
    """H239: the score of the game being played (or looked back on), for the weekly look back."""
    try:
        import games as _g
        return _g.score_lines(games)
    except Exception:
        return []


def _land(c: dict) -> None:
    opts = LAND.get(c["kind"]) or ["{title} is due."]
    text = opts[int(time.time() // 86400) % len(opts)].replace("{title}", c["title"])
    if c["kind"] == "week":
        score = _score()
        if score:  # H239: the game's score comes with the weekly look back
            text += " Your game so far: " + " ".join(score)
    add("agent", text, "checkin:" + c["key"])


def done(key: str, f: Path | None = None, now: datetime | None = None) -> str:
    return _mark(key, "done", f, now)


def later(key: str, f: Path | None = None, now: datetime | None = None) -> str:
    return _mark(key, "later", f, now)


def _mark(key: str, how: str, f: Path | None, now: datetime | None) -> str:
    f = f or folder()
    w = workflow()
    if not w or not on(f):
        return "Life coaching is off."
    now = now or _now()
    text = _map_text(f, w)
    with _lock:
        d = _load()
        d.setdefault("first", now.isoformat(timespec="minutes"))
        cs = checkins(d, text, now)
        if ":" in key:  # its own key; just the kind means the one of that kind that's due now, else the next one
            c = next((x for x in cs if x["key"] == key), None)
        else:
            c = next((x for x in cs if x["kind"] == key and (x["due"] or x.get("later"))), None) or next(
                (x for x in cs if x["kind"] == key), None)
        if not c:
            return f"There's no check-in {key} now."
        if how == "done":
            d.setdefault("done", {})[c["key"]] = now.isoformat(timespec="minutes")
            (d.get("later") or {}).pop(c["key"], None)
            said = f"{c['title']}: done."
        else:
            until = (now + timedelta(days=1)).replace(hour=PARTS["morning"], minute=0, second=0, microsecond=0)
            d.setdefault("later", {})[c["key"]] = until.isoformat(timespec="minutes")
            said = f"{c['title']}: not now, back {_day_words(until, now)} morning."
        _save(d)
    return said


# ---- the coaching line: the thread, through the direct line's own code --------------------------------------------

def _env(f: Path | None = None) -> dict:
    w = workflow() or {}
    return {**os.environ, "HQ_DIRECT_DIR": str(line_dir()), "HQ_DIRECT_AGENT": w.get("agent") or "pepper",
            "HQ_DIRECT_COACHING": "1", **({"HQ_DIRECT_DRY": "1"} if os.environ.get("HQ_COACHING_DRY") == "1" else {})}


def thread(last: int | None = None) -> list[dict]:
    p = line_dir() / "thread.jsonl"
    out = []
    try:
        for line in p.read_text(encoding="utf8").splitlines():
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if isinstance(m, dict) and m.get("text"):
                out.append(m)
    except OSError:
        return []
    return out[-last:] if last else out


def add(sender: str, text: str, why: str = "") -> dict:
    old = {k: os.environ.get(k) for k in ("HQ_DIRECT_DIR",)}
    os.environ["HQ_DIRECT_DIR"] = str(line_dir())
    try:
        import direct_line
        return direct_line.add(sender, text, why)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def send(text: str) -> dict:
    """His text on the coaching line; her answer comes from direct_line.py reply, detached."""
    m = add("me", text[:4000], "")
    py = ROOT / ".venv" / "bin" / "python"
    log = ROOT / "scratch" / "coaching-line.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([str(py) if py.exists() else sys.executable, str(HERE / "direct_line.py"), "reply"],
                     cwd=str(ROOT), env=_env(), stdout=open(log, "a"), stderr=subprocess.STDOUT, start_new_session=True)
    return m


def rule(f: Path | None = None) -> str:
    """What her chat on the coaching line adds to the direct line's rules (direct_line, HQ_DIRECT_COACHING)."""
    f = f or folder()
    r = read(f)
    lines = ["# This chat is the coaching line (H225)",
             "", "This is not the everyday direct line: it's the life coaching line, a thread only for life coaching, "
             "in the Coaching place of the app. Talk about their map, the check-ins, how the week went, what's next; "
             "one thing at a time, a sparring partner, short texts. Everyday things (reminders, the to-do list) you "
             "can still do. A whole layer or a check-in goes best on a call: offer the Start button for it in the app "
             "when they want to go through one, and do a quick look here when they'd rather text.",
             "", workflows.rule(f)]
    due = [c for c in r.get("checkins", []) if c["due"]]
    if due:
        lines.append("Due now: " + "; ".join(f"{c['title']} ({c['key']})" for c in due) + ". When one is through "
                     f"here, mark it: python3 \"{HERE / 'coaching.py'}\" done KEY.")
    return "\n".join(lines)


# ---- a call about a layer or a check-in (call.py's _about, kind "coaching") -------------------------------------------

def about(ref: str, f: Path | None = None) -> dict | None:
    """One layer ("layer:N") or check-in (its key) for a call started from it in the app."""
    f = f or folder()
    r = read(f)
    if not r.get("on") or not ref:
        return None
    if ref.startswith("layer:"):
        try:
            n = int(ref[6:])
        except ValueError:
            return None
        lay = next((x for x in r["layers"] if x["n"] == n), None)
        w = workflow()
        if not lay:
            name = next((nm for x, nm, _b in workflows._layers((w["dir"] / w["guide"]).read_text(encoding="utf8"))
                         if x == n), "") if w else ""
            if not name:
                return None
            lay = {"n": n, "name": name, "word": "not started", "status": "", "items": [], "counts": {}, "total": 0}
        return {"kind": "coaching", "what": "layer", "ref": ref, "title": f"{lay['n']}. {lay['name']}", "layer": lay,
                "named": r.get("named", "")}
    c = next((x for x in r["checkins"] if x["key"] == ref), None)
    if not c:
        return None
    return {"kind": "coaching", "what": "checkin", "ref": ref, "title": c["title"], "checkin": c,
            "layer": next((x for x in r["layers"] if x["n"] == 6), None), "named": r.get("named", "")}


def when_line(e: dict) -> str:
    return f"{e.get('title', '')} (life coaching)"


def greetings(e: dict, name: str = "") -> list[str]:
    """The call system's greeting on a coaching call (spoken, so plain words only). Wording Claude's choice."""
    n = f", {name}" if name else ""
    if e.get("what") == "checkin":
        k = (e.get("checkin") or {}).get("kind")
        what = {"week": "our weekly look back", "game": "the game's debrief", "checkin": "the bigger check-in"}.get(k, "our check-in")
        return [f"Hi{n}. Time for {what}. Ready when you are.", f"Hey{n}. Let's do {what}. How are you doing?"]
    lay = e.get("layer") or {}
    title = re.sub(r"\(.*?\)", "", lay.get("name", "")).strip() or "this layer"
    # H237: "Let's work on the year", not "on The year", mid-sentence.
    mid = re.sub(r"^(The|A|An) ", lambda m: m.group(1).lower() + " ", title)
    return [f"Hi{n}. Let's work on {mid}. Ready?", f"Hey{n}. {title} today. How are you doing?"]


def call_note(e: dict, user: str = "the user") -> str:
    w = workflow() or {}
    guide = (w.get("dir") or ROOT / "workflows" / WID) / w.get("guide", "guide.md")
    mapf = w.get("file", "map.md")
    script = HERE / "coaching.py"
    lay = e.get("layer") or {}
    open_ = [f"{i['key']}: {i['q']}" for i in lay.get("items", []) if i["mark"] == "open"]
    if e.get("what") == "checkin":
        c = e["checkin"]
        part = {"week": "Each week", "game": "After every game", "checkin": "Every eight weeks"}[c["kind"]]
        extra = ""
        if c["kind"] == "game":
            extra = (f" The game: python3 \"{HERE / 'games.py'}\" show --game {c.get('game', '')} (its score, notes "
                     f"and weeks); its debrief goes in with games.py debrief \"TEXT\" --game {c.get('game', '')}.")
        elif c["kind"] == "week":
            extra = (" Look at what the week held first: their calendar for the last seven days, the six-week game's "
                     "score if one is on (games.py), and the last weekly note under the looking-back layer.")
            score = _score()
            if score:  # H239: the game's score is part of every weekly look back
                extra += (" The six-week game is part of this look back: go through its score with them (what they "
                          "did, how it felt, what came out of it), then put their look back on the week in with "
                          f"games.py week \"TEXT\". The score now: {' '.join(score)}")
        return (
            f"{user} started this call from the Coaching place in HQ: it's a check-in, {c['title'].lower()}. This call "
            f"is only that check-in. Read their {mapf} first (the looking-back layer and the layers it adjusts) and "
            f"the guide's looking-back layer, the part \"{part}\" ({guide}), then go through it the guide's way, one "
            f"question at a time, writing what comes out under the looking-back layer as you go, and ticking its "
            f"checklist lines.{extra} When it's through, mark it done: python3 \"{script}\" done {c['key']}; if they "
            "stop halfway, leave it and say it stays open. Anything bigger that comes up gets its own call.\n"
        )
    return (
        f"{user} started this call from the Coaching place in HQ, about one layer of their map: {lay.get('n')}. "
        f"{lay.get('name', '')} (now: {lay.get('word', '')}). This call is that one layer only, its own session, so it "
        f"doesn't drift: read their {mapf} and the guide's layer {lay.get('n')} first ({guide}), say in a sentence "
        "where they are in it, and go through it the guide's way, one question at a time, writing their answers and "
        "ticking the checklist as you go. When the layer is through or the time is up, say what's next and that the "
        "next layer is its own call, from the same place.\n"
        + ("Still open in this layer: " + "; ".join(open_[:40]) + ".\n" if open_ else "")
    )


def summary(f: Path | None = None) -> str:
    r = read(f)
    if not r["on"]:
        return "Life coaching is off."
    if not r["map"]:
        return "Life coaching is on, but their map isn't started yet."
    out = []
    for c in r["checkins"]:
        out.append(f"{c['title']} ({c['key']}): " + ("due. " if c["due"] else "") + c["line"])
    if not r.get("kept"):
        out.append("Check-ins: not kept yet (the first look starts them).")
    for lay in r["layers"]:
        cn = lay["counts"]
        out.append(f"{lay['n']}. {lay['name']}: {lay['word']}, {cn.get('answered', 0)} answered, "
                   f"{cn.get('open', 0)} open of {lay['total']}")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "summary"
    # H203: on the backup HQ a done or a not now goes to the main one, which writes it (role.WRITES).
    if cmd in ("done", "later") and not os.environ.get("HQ_ROLE_HERE") and not os.environ.get("HQ_COACHING"):
        sys.path.insert(0, str(ROOT / "routine"))
        import role
        if role.is_backup():
            return role.forward("coaching", list(argv))
    if cmd == "summary":
        print(summary())
    elif cmd == "json":
        print(json.dumps(read(), ensure_ascii=False, indent=1))
    elif cmd == "due":
        due = [c for c in read()["checkins"] if c["due"]]
        print("\n".join(f"{c['title']} ({c['key']}): {c['line']}" for c in due) or "Nothing due.")
    elif cmd in ("done", "later") and len(argv) == 2:
        print((done if cmd == "done" else later)(argv[1]))
    elif cmd == "refresh":
        print(" ".join(refresh()) or "nothing new")
    elif cmd == "rule":
        print(rule())
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
