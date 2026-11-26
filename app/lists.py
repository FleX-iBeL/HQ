"""The bucketlist and the wishlist: items with a price, links, a time goal, notes and sub-items without end.

The user's words (the laptop chat, 25 November 2026): "i want to build a new feature called bucketlist. this way i can
set sort of mini goals that i want to achieve. can be experiences, products or services to buy (single or recurring),
i want to be able to store links, time goals and costs. also an unlimited amount of subitems should be able to be
added and the total numbers on the main item should also be visible. also notes should be possible." And: "i want to
improve wishlist. i want just like the bucketlist subitems added as an option and add price and link and notes".
From his notes of the day before: "(and scoring based on life vision)" and "Met subtasks, time, goals and money
cost(price) need to spend on it".

One engine, two lists (`bucket` and `wish`), kept in the workspace's HQ/lists.json (or HQ_LISTS); a fresh install has
none. Nothing of anyone's own lists is ever in HQ. An item:

    name     what it is
    kind     experience, product or service (or nothing)
    price    what it costs, with `every`: once, month or year (a recurring one)
    links    as many as wanted
    by       the time goal: a year (2027), a month (2027-06) or a day (2027-06-14)
    hours    the time it takes to do
    score    1 to 5: how much it brings the life they're building closer, with `why`
    notes    free text
    state    open, done, or dropped (let go)
    sub      its sub-items, each one an item like this, as deep as wanted

An item's totals add up itself and everything under it that isn't dropped: money once, per month and per year, what
of the one-off money is still to spend (the open ones), the hours, and how many sub-items are done.

    python3 app/lists.py [bucket|wish]             the lists in a few lines, to say out loud
    python3 app/lists.py json                      everything the app gets (JSON)
    python3 app/lists.py show ITEM                 one item with everything under it
    python3 app/lists.py add "NAME" [--list bucket|wish] [--under ITEM] [--kind K] [--price N] [--every once|month|year]
                                   [--link URL] [--goal WHEN] [--hours N] [--score N] [--why TEXT] [--notes TEXT]
    python3 app/lists.py set ITEM FIELD VALUE      name, kind, price, every, by, hours, score, why, notes ("" clears it)
    python3 app/lists.py link ITEM URL             add a link;  unlink ITEM URL|N  takes one off
    python3 app/lists.py done ITEM | open ITEM | drop ITEM      done, open again, let go
    python3 app/lists.py delete ITEM               gone, with everything under it (undo brings it back)
    python3 app/lists.py move ITEM up|down|top|bottom           its place among its neighbours
    python3 app/lists.py under ITEM PARENT|top     make it a sub-item of PARENT, or a main item again
    python3 app/lists.py import-wish               move an old wishlist table in the to-do file over (HQ does it by itself)
    python3 app/lists.py undo                      puts back the last change made here, if nothing changed since

ITEM is an item's id (L12) or a few words of its name; --list says which list when the words fit both. Every change
takes --by "<who>" (the time goal is --goal on add, and the field `by` or `goal` on set).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # HQ
sys.path.insert(0, str(ROOT / "routine"))
import hqlock  # noqa: E402  one lock across processes, unique temp files

FILE = "HQ/lists.json"  # in the workspace
LISTS = {"bucket": "Bucketlist", "wish": "Wishlist"}
KINDS = ("experience", "product", "service")
EVERY = ("once", "month", "year")
WRITES = ("add", "set", "link", "unlink", "done", "open", "drop", "delete", "move", "under", "import-wish", "undo")
FIELDS = ("name", "kind", "price", "every", "by", "hours", "score", "why", "notes")
KEEP_LOG = 300
_lock = hqlock.For(lambda: path())


def folder() -> Path:
    return Path(os.environ.get("HQ_FOLDER") or os.path.realpath(os.environ.get("HQ_WORKSPACE", str(ROOT / "workspace"))))


def path() -> Path:
    return Path(os.environ.get("HQ_LISTS") or folder() / FILE)


def _undo_file() -> Path:
    return Path(os.environ.get("HQ_LISTS_UNDO") or ROOT / "scratch" / "lists-undo.json")


def _today() -> str:
    return os.environ.get("HQ_LISTS_TODAY") or date.today().isoformat()


def _now() -> str:
    return _today() + datetime.now().strftime(" %H:%M")


# ---- the file ------------------------------------------------------------------------------------------------

def _empty() -> dict:
    return {"lists": {k: [] for k in LISTS}, "seq": 0, "log": []}


def _load() -> dict:
    try:
        d = json.loads(path().read_text(encoding="utf8"))
    except FileNotFoundError:
        return _empty()
    except ValueError:
        raise ValueError(f"{FILE} isn't readable JSON; fix it by hand first.")
    if not isinstance(d, dict) or not isinstance(d.get("lists"), dict):
        raise ValueError(f"{FILE} has no lists; fix it by hand first.")
    for k in LISTS:
        d["lists"].setdefault(k, [])
    d.setdefault("seq", 0)
    d.setdefault("log", [])
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
    tmp = hqlock.tmp(p)
    tmp.write_text(text, encoding="utf8")
    os.replace(tmp, p)
    try:
        u = _undo_file()
        u.parent.mkdir(parents=True, exist_ok=True)
        u.write_text(json.dumps({"before": before, "after": hashlib.sha1(text.encode()).hexdigest()}), encoding="utf8")
    except OSError:
        pass


def _log(d: dict, what: str, by: str) -> None:
    d["log"].insert(0, {"at": _now(), "by": by or "", "what": what})
    del d["log"][KEEP_LOG:]


# ---- an item's values ----------------------------------------------------------------------------------------

def _num(v, what: str):
    s = str(v).strip().replace("€", "").replace("$", "").replace(" ", "")
    if not s:
        return None
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", s):  # 1.250,50
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", s):  # 1,250.50
        s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        n = float(s)
    except ValueError:
        raise ValueError(f"{what} is a number, not {v!r}.")
    if n < 0:
        raise ValueError(f"{what} can't be below nothing.")
    return int(n) if n.is_integer() else round(n, 2)


def _when(v) -> str:
    s = str(v).strip()
    if not s:
        return ""
    if not re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", s):
        raise ValueError(f"A time goal is a year (2027), a month (2027-06) or a day (2027-06-14), not {v!r}.")
    try:
        date.fromisoformat((s + "-01-01")[:10] if len(s) < 10 else s)
    except ValueError:
        raise ValueError(f"{v!r} isn't a real date.")
    return s


def _link(v) -> str:
    s = str(v).strip()
    if not s:
        raise ValueError("A link needs an address.")
    if not re.match(r"https?://", s, re.I):
        s = "https://" + s
    if re.search(r"\s", s) or "." not in s:
        raise ValueError(f"{v!r} isn't a web address.")
    return s[:1000]


def _clean(field: str, value):
    v = "" if value is None else str(value).strip()
    if field == "name":
        v = " ".join(v.split())[:200]
        if not v:
            raise ValueError("An item needs a name.")
        return v
    if field == "kind":
        v = v.lower()
        if v and v not in KINDS:
            raise ValueError(f"A kind is {', '.join(KINDS[:-1])} or {KINDS[-1]}, not {value!r}.")
        return v
    if field == "price":
        return _num(v, "A price")
    if field == "every":
        v = {"": "once", "single": "once", "one-off": "once", "monthly": "month", "a month": "month", "per month": "month",
             "yearly": "year", "a year": "year", "per year": "year", "annual": "year"}.get(v.lower(), v.lower())
        if v not in EVERY:
            raise ValueError(f"A price is once, a month or a year, not {value!r}.")
        return v
    if field == "by":
        return _when(v)
    if field == "hours":
        return _num(v, "The time it takes")
    if field == "score":
        if not v:
            return None
        if v not in "12345" or len(v) != 1:
            raise ValueError(f"A score is 1 to 5, not {value!r}.")
        return int(v)
    if field == "why":
        return v[:500]
    if field == "notes":
        return v[:6000]
    raise ValueError(f"There's no field {field!r}; the fields are {', '.join(FIELDS)}.")


def _new(d: dict, name: str, **vals) -> dict:
    d["seq"] += 1
    it = {"id": f"L{d['seq']}", "name": _clean("name", name), "kind": "", "price": None, "every": "once", "links": [],
          "by": "", "hours": None, "score": None, "why": "", "notes": "", "state": "open", "added": _today(), "sub": []}
    for k, v in vals.items():
        if k == "links":
            it["links"] = [_link(x) for x in v if str(x).strip()]
        elif v not in (None, ""):
            it[k] = _clean(k, v)
    return it


# ---- walking the tree ----------------------------------------------------------------------------------------

def _walk(items: list, parent: dict | None = None, depth: int = 0):
    for it in items:
        yield it, parent, items, depth
        yield from _walk(it.get("sub") or [], it, depth + 1)


def _add_up(n):
    return int(n) if float(n).is_integer() else round(n, 2)


def totals(it: dict) -> dict:
    """The item and everything under it that isn't dropped, added up."""
    t = {"once": 0, "month": 0, "year": 0, "left": 0, "hours": 0, "subs": 0, "subs_done": 0}

    def take(x, top):
        if x.get("state") == "dropped":
            return
        if not top:
            t["subs"] += 1
            t["subs_done"] += x.get("state") == "done"
        p = x.get("price")
        if p:
            t[x.get("every") or "once"] += p
            if (x.get("every") or "once") == "once" and x.get("state") != "done":
                t["left"] += p
        t["hours"] += x.get("hours") or 0
        for s in x.get("sub") or []:
            take(s, False)
    take(it, True)
    return {k: _add_up(v) for k, v in t.items()}


def view(it: dict) -> dict:
    v = {k: it.get(k) for k in ("id", "name", "kind", "price", "every", "links", "by", "hours", "score", "why", "notes",
                                "state", "added", "done")}
    v["links"] = list(it.get("links") or [])
    v["sub"] = [view(s) for s in it.get("sub") or []]
    v["totals"] = totals(it)
    return v


def read() -> dict:
    """Everything the app gets: both lists, every item with its sub-items and totals, and each list's own totals."""
    try:
        d = _load()
    except ValueError as e:
        return {"lists": [], "error": str(e)}
    out = []
    for key, name in LISTS.items():
        items = [view(i) for i in d["lists"][key]]
        whole = totals({"state": "open", "sub": d["lists"][key]})
        out.append({"key": key, "name": name, "items": items, "totals": whole,
                    "open": sum(1 for i in items if i["state"] == "open")})
    return {"lists": out, "kinds": list(KINDS), "every": list(EVERY), "moved": d.get("moved") or {}}


def _find(d: dict, ref: str, lst: str = "") -> tuple[dict, dict | None, list, str]:
    """The item a reference means: (item, its parent, the list it sits in, which list)."""
    ref = str(ref or "").strip()
    if not ref:
        raise KeyError("Which item?")
    keys = [lst] if lst else list(LISTS)
    hits = []
    for key in keys:
        if key not in LISTS:
            raise KeyError(f"There's no list {key!r}; the lists are bucket and wish.")
        for it, parent, sibs, _ in _walk(d["lists"][key]):
            if it["id"].lower() == ref.lower():
                return it, parent, sibs, key
            hits.append((it, parent, sibs, key))
    words = [w for w in re.findall(r"\w+", ref.lower())]
    exact = [h for h in hits if h[0]["name"].lower() == ref.lower()]
    found = exact or [h for h in hits if words and all(w in h[0]["name"].lower() for w in words)]
    live = [h for h in found if h[0].get("state") != "dropped"] or found
    if not live:
        raise KeyError(f"Nothing on the lists fits {ref!r}.")
    if len(live) > 1:
        names = "; ".join(f"{h[0]['id']} {h[0]['name']} ({LISTS[h[3]]})" for h in live[:6])
        raise KeyError(f"More than one item fits {ref!r}: {names}. Say which, by its id.")
    return live[0]


def _money(n, every: str = "once") -> str:
    if not n:
        return ""
    s = f"{n:,.2f}".rstrip("0").rstrip(".") if isinstance(n, float) else f"{n:,}"
    return "€" + s + {"once": "", "month": " a month", "year": " a year"}[every]


def money_line(t: dict) -> str:
    parts = [_money(t["once"]), _money(t["month"], "month"), _money(t["year"], "year")]
    return " + ".join(p for p in parts if p)


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


@_change
def add(d, name: str, lst: str = "", under: str = "", who: str = "", **vals) -> str:
    if under:
        parent, _, _, key = _find(d, under, lst)
        it = _new(d, name, **vals)
        parent.setdefault("sub", []).append(it)
        _log(d, f"added {it['name']} under {parent['name']} ({LISTS[key]})", who)
        return f"Added {it['name']} under {parent['name']}, on the {LISTS[key].lower()}."
    key = lst or "bucket"
    if key not in LISTS:
        raise KeyError(f"There's no list {key!r}; the lists are bucket and wish.")
    it = _new(d, name, **vals)
    d["lists"][key].append(it)
    _log(d, f"added {it['name']} ({LISTS[key]})", who)
    return f"Added {it['name']} to the {LISTS[key].lower()}."


@_change
def set_(d, ref: str, field: str, value, lst: str = "", by: str = "") -> str:
    it, _, _, key = _find(d, ref, lst)
    field = {"link": "links", "time": "hours", "goal": "by", "when": "by", "cost": "price", "title": "name"}.get(field, field)
    if field not in FIELDS:
        raise ValueError(f"There's no field {field!r}; the fields are {', '.join(FIELDS)}.")
    old = it["name"]
    it[field] = _clean(field, value)
    _log(d, f"{old}: {field} is now {it[field]!r}" if field != "notes" else f"{old}: notes changed", by)
    shown = "taken off" if it[field] in ("", None) else f"now {it[field]}"
    return f"{old}: renamed to {it['name']}." if field == "name" else f"{old}: {field} {shown}."


@_change
def link(d, ref: str, url: str, lst: str = "", by: str = "") -> str:
    it, _, _, _ = _find(d, ref, lst)
    u = _link(url)
    if u in it["links"]:
        return f"{it['name']} already has that link."
    it["links"].append(u)
    _log(d, f"{it['name']}: link added", by)
    return f"{it['name']}: link added."


@_change
def unlink(d, ref: str, which: str, lst: str = "", by: str = "") -> str:
    it, _, _, _ = _find(d, ref, lst)
    w = str(which).strip()
    if w.isdigit() and 1 <= int(w) <= len(it["links"]):
        it["links"].pop(int(w) - 1)
    else:
        hit = [u for u in it["links"] if w and w.lower() in u.lower()]
        if len(hit) != 1:
            raise KeyError(f"{it['name']} has {len(it['links'])} links; say which by its number or part of its address.")
        it["links"].remove(hit[0])
    _log(d, f"{it['name']}: link taken off", by)
    return f"{it['name']}: link taken off."


def _state(new: str, word: str):
    @_change
    def go(d, ref: str, lst: str = "", by: str = "") -> str:
        it, _, _, key = _find(d, ref, lst)
        it["state"] = new
        if new == "done":
            it["done"] = _today()
        else:
            it.pop("done", None)
        _log(d, f"{it['name']}: {word}", by)
        if new == "done":
            left = [s for s in it.get("sub") or [] if s.get("state") == "open"]
            return f"{it['name']}: done." + (f" {len(left)} sub-item{'s' if len(left) != 1 else ''} under it still open." if left else "")
        return f"{it['name']}: {word}."
    return go


done = _state("done", "done")
reopen = _state("open", "open again")
drop = _state("dropped", "let go")


@_change
def delete(d, ref: str, lst: str = "", by: str = "") -> str:
    it, _, sibs, _ = _find(d, ref, lst)
    n = sum(1 for _ in _walk(it.get("sub") or []))
    sibs.remove(it)
    _log(d, f"deleted {it['name']}" + (f" with {n} under it" if n else ""), by)
    return f"Deleted {it['name']}" + (f" and the {n} under it." if n else ".")


@_change
def move(d, ref: str, to: str, lst: str = "", by: str = "") -> str:
    it, _, sibs, _ = _find(d, ref, lst)
    i = sibs.index(it)
    to = str(to).strip().lower()
    if to.isdigit():
        j = max(0, min(len(sibs) - 1, int(to) - 1))
    else:
        j = {"up": max(0, i - 1), "down": min(len(sibs) - 1, i + 1), "top": 0, "bottom": len(sibs) - 1}.get(to)
        if j is None:
            raise ValueError("Move it up, down, top, bottom, or to a place (1, 2, …).")
    sibs.insert(j, sibs.pop(i))
    _log(d, f"{it['name']}: moved to place {j + 1}", by)
    return f"{it['name']}: now at place {j + 1} of {len(sibs)}."


@_change
def under(d, ref: str, parent_ref: str, lst: str = "", by: str = "") -> str:
    it, _, sibs, key = _find(d, ref, lst)
    if str(parent_ref).strip().lower() in ("top", "main", "none", ""):
        sibs.remove(it)
        d["lists"][key].append(it)
        _log(d, f"{it['name']}: a main item now", by)
        return f"{it['name']}: a main item on the {LISTS[key].lower()} now."
    parent, _, _, pkey = _find(d, parent_ref, "")
    if parent is it or any(x is parent for x, *_ in _walk(it.get("sub") or [])):
        raise ValueError("An item can't go under itself.")
    sibs.remove(it)
    parent.setdefault("sub", []).append(it)
    _log(d, f"{it['name']}: now under {parent['name']}", by)
    return f"{it['name']}: now under {parent['name']}" + (f", on the {LISTS[pkey].lower()}." if pkey != key else ".")


_URL = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)|(https?://[^\s)|]+)")


def _old_wishes() -> list[dict]:
    import todo
    return todo.wish_rows()


@_change
def _move_wishes(d, by: str = "") -> str:
    rows = _old_wishes()
    made = filled = 0
    for r in rows:
        title = str(r.get("title") or "")
        name = _URL.sub(lambda m: m.group(1) or "", title).strip() or "Wish"
        notes = str(r.get("notes") or "")
        links = [m.group(2) or m.group(3) for m in _URL.finditer(notes + " " + title)]
        notes = _URL.sub(lambda m: "" if (m.group(1) or "").strip().lower() in ("", "link") else m.group(1), notes).strip()
        cells = [(str(k).strip(), str(v or "").strip()) for k, v in (r.get("fields") or [])]
        # everything the old row had comes along: its notes, every other column, and the paragraphs in their own words
        pieces = [notes] + [f"{k.capitalize()}: {v}" for k, v in cells
                            if v and k.lower() not in ("notes", "why", "added") and not (k.lower() == "status" and v.lower() == "open")]
        pieces += [str(x).strip() for x in r.get("details") or []]
        pieces = [x for x in pieces if x]
        added = next((v for k, v in cells if k.lower() == "added"), "") or str(r.get("added") or "")
        it = next((x for x in d["lists"]["wish"] if x["name"].strip().lower() == _clean("name", name).strip().lower()), None)
        if it is None:
            it = _new(d, name, notes="\n".join(pieces), links=links)
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", added):
                it["added"] = added
            d["lists"]["wish"].append(it)
            made += 1
            continue
        have = str(it.get("notes") or "")
        more = [x for x in pieces if x not in have]
        new_links = [u for u in (_link(x) for x in links) if u not in (it.get("links") or [])]
        if more or new_links:
            it["notes"] = _clean("notes", "\n".join([have] + more).strip())
            it["links"] = list(it.get("links") or []) + new_links
            filled += 1
    import todo
    took = todo.take_wishes(by=by)
    d.setdefault("moved", {}).setdefault("wish", _today())
    if not rows and took < 0:
        return "Nothing to move: every wish is already on the wishlist."
    _log(d, f"the wishlist moved over from the to-do list: {made} new, {filled} filled in; the old table is gone", by)
    n = len(rows)
    return (f"Moved {n} wish{'es' if n != 1 else ''} over from the to-do list, with everything each one had"
            + (f" ({made} new, {filled} filled in)" if filled else "") + ". The old list is gone: the wishlist replaces it.")


def import_wish(by: str = "") -> dict:
    """Every wish still in the to-do file's old wishlist table moved to the wishlist, with all it had (its notes, every
    other column, its links, the paragraphs in the user's own words, the day it was added), and the old table taken
    out of the file: the wishlist replaces it. Safe to run again: a wish already here is only filled in, never twice.
    It can't be undone from the lists (an undo would lose the wishes: the old table is gone)."""
    r = _move_wishes(by=by)
    try:
        _undo_file().unlink(missing_ok=True)
    except OSError:
        pass
    return r


_settle_tried = 0.0


def settle(by: str = "HQ") -> None:
    """An old wishlist table still in the to-do file is moved over by itself, the first time anything looks at the
    lists. On the backup the main does it (asked at most once every two minutes)."""
    global _settle_tried
    try:
        import todo
        if not todo.has_wish_table():
            return
        if not os.environ.get("HQ_ROLE_HERE"):
            import role
            if role.is_backup():
                if time.time() - _settle_tried > 120:
                    _settle_tried = time.time()
                    role.hand("lists", ["import-wish", "--by", by], keep=False)
                return
        import_wish(by=by)
    except Exception:
        pass  # a look at the lists never fails on this; the next look tries again


def undo() -> dict:
    with _lock:
        try:
            u = json.loads(_undo_file().read_text(encoding="utf8"))
        except (OSError, ValueError):
            return {"ok": False, "said": "Nothing to undo."}
        if hashlib.sha1(_raw().encode()).hexdigest() != u.get("after"):
            return {"ok": False, "said": "The lists changed since, so the last change can't be undone from here."}
        p = path()
        if u.get("before"):
            p.write_text(u["before"], encoding="utf8")
        else:
            p.unlink(missing_ok=True)
        _undo_file().unlink(missing_ok=True)
        return {"ok": True, "said": "Undone."}


# ---- to say out loud -----------------------------------------------------------------------------------------

def line(v: dict, depth: int = 0) -> str:
    t = v["totals"]
    bits = [money_line(t)]
    if t["hours"]:
        bits.append(f"{t['hours']} h")
    if v.get("by"):
        bits.append(f"by {v['by']}")
    if t["subs"]:
        bits.append(f"{t['subs_done']} of {t['subs']} under it done")
    if v.get("score"):
        bits.append(f"score {v['score']}")
    mark = {"done": "✓ ", "dropped": "✗ "}.get(v["state"], "")
    tail = " (" + ", ".join(b for b in bits if b) + ")" if any(bits) else ""
    return "  " * depth + f"- {mark}{v['name']} [{v['id']}]" + tail


def summary(which: str = "") -> str:
    r = read()
    if r.get("error"):
        return r["error"]
    out = []
    for l in r["lists"]:
        if which and l["key"] != which:
            continue
        live = [i for i in l["items"] if i["state"] == "open"]
        if not l["items"]:
            out.append(f"{l['name']}: nothing on it yet.")
            continue
        m = money_line(l["totals"])
        out.append(f"{l['name']}: {len(live)} open" + (f", {m} in all" if m else "") + ".")
        out += [line(i) for i in live]
        gone = len(l["items"]) - len(live)
        if gone:
            out.append(f"  ({gone} done or let go)")
    return "\n".join(out) if out else "There's no such list; the lists are bucket and wish."


def show(ref: str, lst: str = "") -> str:
    d = _load()
    it, parent, _, key = _find(d, ref, lst)
    v = view(it)
    out = [f"{v['name']} [{v['id']}], on the {LISTS[key].lower()}" + (f", under {parent['name']}" if parent else "") + f": {v['state']}."]
    if v["kind"]:
        out.append(f"Kind: {v['kind']}.")
    if v["price"]:
        out.append(f"Price: {_money(v['price'], v['every'])}.")
    t = v["totals"]
    if v["sub"]:
        m = money_line(t)
        out.append("With everything under it: " + ", ".join(b for b in [m, f"€{t['left']:,} of the one-off still to spend" if t["left"] and t["left"] != t["once"] else "",
                   f"{t['hours']} h" if t["hours"] else "", f"{t['subs_done']} of {t['subs']} done"] if b) + ".")
    if v["by"]:
        out.append(f"Time goal: {v['by']}.")
    if v["hours"]:
        out.append(f"Takes: {v['hours']} h.")
    if v["score"]:
        out.append(f"Score: {v['score']} of 5" + (f" ({v['why']})" if v["why"] else "") + ".")
    out += [f"Link {n}: {u}" for n, u in enumerate(v["links"], 1)]
    if v["notes"]:
        out.append("Notes: " + v["notes"])

    def subs(items, depth):
        for s in items:
            out.append(line(s, depth))
            subs(s["sub"], depth + 1)
    if v["sub"]:
        out.append("Under it:")
        subs(v["sub"], 0)
    return "\n".join(out)


# ---- the command line ----------------------------------------------------------------------------------------

def _opt(args: list[str], name: str, flag: bool = False, many: bool = False):
    got = []
    while name in args:
        i = args.index(name)
        if flag:
            del args[i]
            return True
        got.append(args[i + 1] if i + 1 < len(args) else "")
        del args[i:i + 2]
        if not many:
            break
    if many:
        return got
    return got[0] if got else (False if flag else "")


def run(argv: list[str]) -> tuple[int, str]:
    """One command, here (never handed over): its exit code and what it says."""
    args = list(argv)
    by, lst = _opt(args, "--by"), _opt(args, "--list")
    lst = {"bucketlist": "bucket", "wishlist": "wish"}.get(lst.lower(), lst.lower()) if lst else ""
    cmd = args[0] if args else "summary"
    if cmd not in ("import-wish", "undo"):
        settle()
    try:
        if cmd in ("summary", "bucket", "wish", "bucketlist", "wishlist"):
            return 0, summary("" if cmd == "summary" else cmd[:6] if cmd.startswith("bucket") else "wish")
        if cmd == "json":
            return 0, json.dumps(read(), ensure_ascii=False, indent=1)
        if cmd == "show" and len(args) == 2:
            return 0, show(args[1], lst)
        if cmd == "add" and len(args) >= 2:
            vals = {k: _opt(args, "--" + k) for k in ("kind", "price", "every", "hours", "score", "why", "notes")}
            vals["by"] = _opt(args, "--goal")
            links, parent = _opt(args, "--link", many=True), _opt(args, "--under")
            if len(args) != 2:
                return 2, "add takes one name, in quotes."
            return 0, add(args[1], lst=lst, under=parent, who=by, links=links, **vals)["said"]
        if cmd == "set" and len(args) == 4:
            return 0, set_(args[1], args[2].lower(), args[3], lst=lst, by=by)["said"]
        if cmd == "link" and len(args) == 3:
            return 0, link(args[1], args[2], lst=lst, by=by)["said"]
        if cmd == "unlink" and len(args) == 3:
            return 0, unlink(args[1], args[2], lst=lst, by=by)["said"]
        if cmd in ("done", "open", "drop", "delete") and len(args) == 2:
            fn = {"done": done, "open": reopen, "drop": drop, "delete": delete}[cmd]
            return 0, fn(args[1], lst=lst, by=by)["said"]
        if cmd == "move" and len(args) == 3:
            return 0, move(args[1], args[2], lst=lst, by=by)["said"]
        if cmd == "under" and len(args) == 3:
            return 0, under(args[1], args[2], lst=lst, by=by)["said"]
        if cmd == "import-wish":
            return 0, import_wish(by=by)["said"]
        if cmd == "undo":
            r = undo()
            return (0 if r["ok"] else 1), r["said"]
        return 2, __doc__.strip()
    except (KeyError, ValueError) as e:
        return 1, str(e).strip("'\"")
    except OSError as e:
        return 1, f"Couldn't read or write the lists: {e}"


def main(argv: list[str]) -> int:
    # On the backup HQ a change goes to the main one, which writes it (role.WRITES), like the to-do list and the games.
    if argv and argv[0] in WRITES and not os.environ.get("HQ_ROLE_HERE"):
        import role
        if role.is_backup():
            return role.forward("lists", list(argv))
    code, text = run(argv)
    print(text)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
