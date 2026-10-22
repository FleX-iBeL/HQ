"""H229: travel on appointments, by public transport, with Donna's texts when something changes (22 October 2026).

The user's quick note, 20 October 2026: "for all the calendar appointments it can automatically link those so each
appointment can have travel turned on and automatically donna can keep you uptodate. So for example if in 2 weeks i
visit [a friend] again, i will leave from home (you can conclude that based on my calendar), and you will know [their]
adress (as he is a friend) ... and then Donna can have alert me if i need to know unexpected changes". On the call of
22 October 2026 (Pepper): "As long as it explained well in the tutorial, then it should work right." Driving is its
own feature (H230).

An appointment away from home gets travel by itself when HQ knows where it is: its place in the calendar, or a name in
its title that's in the places book (a friend's address, kept once). It can be turned on or off by hand: the Travel
button in the appointment in the app, or a call or Donna's chat (this script). Off by hand stays off.

Each trip keeps: where it goes, where it starts (named by hand, else the place of the appointment just before it that
day, else home: the Home line in me.md), its 9 2 9 2 link (travel.py, H214), the train stations nearest both ends, and
the bus, tram and metro stops near them. Kept in the workspace next to the calendar, HQ/calendar-travel.json (synced to
the other computer, off GitHub: places and titles are private). Nothing about anyone is in this file.

Live changes come from open data, free and without a key (9292's own data is a paid product, NS's own API needs a
key per person): OVapi's GTFS feeds (gtfs.ovapi.nl, Stichting OpenGeo, made from the NDOV open data the transport
companies publish):
  - trainUpdates.pb: every NS (and other) train today and tomorrow, live, per station: delays, cancelled trains,
    stations skipped, platform changes. Strikes and works show here as cancelled trains.
  - alerts.pb: the companies' messages for buses, trams and metros (KV15, GVB): a stop moved or skipped, a line
    diverted, works.
  - the stops of the GTFS timetable (stops.txt, read out of the big zip by its range, once a month): where each stop is.
Their rules (the feed's README): say who you are in the User-Agent, ask only when it changed (If-Modified-Since), gzip.

From LIVE_BEFORE before an appointment until it starts, every CHECK_EVERY on the main (tick.py, detached), HQ looks:
  - his train: the latest direct train from the station near the start that gets him to the station near the
    appointment in time (WALK_SPEED, BUFFER), picked once and then followed by its number. Cancelled, a station
    skipped, late by LATE_MIN or more (and again when it changes by that much), or another platform: Donna texts.
  - no direct train (a change on the way): the stations at both ends; when CROWD of the trains there in the window are
    cancelled, Donna texts that there's trouble on the rails there (a strike or works).
  - buses, trams and metros: a message for a stop within STOP_M of either end, active around the trip: Donna texts.
Each change is texted once (direct_line.text("travel", facts)); never at night (pings._asleep), never when texts are
off. Nothing is written to Google Calendar.

    python3 app/trips.py                          the trips coming up, in plain lines (what a call reads)
    python3 app/trips.py on "ID or words" [--to PLACE] [--from PLACE]   travel on for that appointment
    python3 app/trips.py off "ID or words"        travel off for that appointment (stays off)
    python3 app/trips.py show "ID or words"       one trip, with what the open data says now
    python3 app/trips.py place "NAME" "ADDRESS"   keep a place (a friend's address) once, by name
    python3 app/trips.py places                   the places book
    python3 app/trips.py forget "NAME"            take a place out of the book
    python3 app/trips.py check [--dry]            the routine's look (from tick.py); --dry texts nothing
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "routine"))
import agenda  # noqa: E402
import travel  # noqa: E402

FEEDS = os.environ.get("HQ_TRIPS_FEEDS", "https://gtfs.ovapi.nl/nl/")
UA = travel.UA
CACHE = Path(os.environ.get("HQ_TRIPS_CACHE") or ROOT / "scratch" / "trips")
STOPS_DAYS = 30  # the stops are read out of the timetable again after this
FEED_FRESH = 60  # a feed is asked again after this many seconds at most (their README: not more than once a minute)
LIVE_BEFORE = 3 * 3600  # live watching starts this long before an appointment
CHECK_EVERY = 5 * 60  # while a trip is live
PLAN_EVERY = 3600  # otherwise: places found for new appointments, once an hour in the day
DAYS_AHEAD = 14
PREV_GAP = 3 * 3600  # the appointment before it counts as the start when it ends this long before, or less
STATION_KM = 5.0  # a station farther than this from an end isn't its station
STOP_M = 500  # bus, tram and metro stops this near an end are its stops
WALK_SPEED = 80  # metres a minute, from the station to the place
BUFFER = 5  # minutes to spare at the end
LATE_MIN = 5  # a delay this many minutes or more is worth a text, and a change of this much again
CROWD = 0.3  # this share of the trains at a station cancelled (at least CROWD_MIN) is trouble on the rails
CROWD_MIN = 3
KEEP_DONE = 2 * 86400  # trips of appointments over this long ago go
_lock = threading.Lock()


class NotFound(Exception):
    pass


def on() -> bool:
    if os.environ.get("HQ_TRIPS", "1") == "0" or not agenda.on():
        return False
    try:
        import features
        return features.is_on("travel")
    except Exception:
        return True


# -- the file ---------------------------------------------------------------------------------------------------

def data_file() -> Path:
    return Path(os.environ.get("HQ_TRIPS_FILE") or agenda.data_file().with_name("calendar-travel.json"))


def _read() -> dict:
    try:
        s = json.loads(data_file().read_text(encoding="utf8"))
    except (OSError, ValueError):
        s = {}
    if not isinstance(s, dict):
        s = {}
    for k in ("trips", "places"):
        if not isinstance(s.get(k), dict):
            s[k] = {}
    return s


def _write(s: dict) -> None:
    p = data_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    os.replace(tmp, p)


def _key(eid: str) -> str:
    """The appointment's mark id, so a trip stays with an appointment moved to HQ Planning and back (H143)."""
    try:
        import appt_notes
        return appt_notes._key(eid)
    except Exception:
        return eid


def _events() -> list[dict]:
    return [e for e in agenda._read().get("events") or [] if isinstance(e, dict)]


def find(words: str, evs: list[dict] | None = None) -> dict:
    """One appointment by its id or the words of its title (with a date or a time to narrow it)."""
    import pings
    evs = _events() if evs is None else evs
    hit = pings.find_events(words, evs)
    if not hit:
        raise NotFound(f"no appointment to come matches {words!r}")
    if len(hit) > 1:
        raise NotFound("more than one appointment matches: " + "; ".join(
            f"{e.get('title')} ({agenda.when_words(e)}, id {e.get('id')})" for e in hit[:5]))
    return hit[0]


# -- places ------------------------------------------------------------------------------------------------------

def _norm(s: str) -> str:
    return travel._norm(s or "")


def place_add(name: str, address: str) -> dict:
    name, address = (name or "").strip(), (address or "").strip()
    if not name or not address:
        raise ValueError("a place needs a name and an address")
    got = travel.where(address)  # it has to be findable, or it's no use
    with _lock:
        s = _read()
        s["places"][_norm(name)] = {"name": name, "address": address, "label": got["label"]}
        _write(s)
    return s["places"][_norm(name)]


def place_forget(name: str) -> bool:
    with _lock:
        s = _read()
        if s["places"].pop(_norm(name), None) is None:
            return False
        _write(s)
        return True


def place_in(title: str, places: dict) -> dict | None:
    """A place from the book whose name is a word in the title ("Sam" in "Visit Sam", "at Sam's")."""
    t = " " + _norm(re.sub(r"'s\b", "", title or "")) + " "
    for k, p in sorted(places.items(), key=lambda kv: -len(kv[0])):
        if k and f" {k} " in t:
            return p
    return None


# -- distances, stations, stops ------------------------------------------------------------------------------------

def _latlon(place: dict) -> tuple[float, float] | None:
    m = re.match(r"@([-0-9.]+),([-0-9.]+)$", place.get("id") or "")
    if m:
        return float(m.group(1)), float(m.group(2))
    if place.get("lat") is not None:
        return float(place["lat"]), float(place["lon"])
    return None


def metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def nearest_station(place: dict) -> dict | None:
    """The train station nearest a place (a station is its own), within STATION_KM: {code, name, metres}."""
    rows = travel.stations()
    if place.get("kind") == "station":
        slug = (place.get("id") or "").removeprefix("station-")
        r = next((r for r in rows if r.get("slug") == slug), None)
        return {"code": r["code"].lower(), "name": r["name_long"], "metres": 0} if r else None
    g = _latlon(place)
    if not g:
        return None
    best = None
    for r in rows:
        try:
            d = metres(g, (float(r["geo_lat"]), float(r["geo_lng"])))
        except (KeyError, ValueError):
            continue
        if best is None or d < best[0]:
            best = (d, r)
    if not best or best[0] > STATION_KM * 1000:
        return None
    return {"code": best[1]["code"].lower(), "name": best[1]["name_long"], "metres": round(best[0])}


def _get(url: str, timeout: float = 30, headers: dict | None = None) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                import gzip
                body = gzip.decompress(body)
            return r.status, body, dict(r.headers)
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return 304, b"", dict(e.headers)
        raise


class _Ranged(io.RawIOBase):
    """A file over HTTP, read by byte ranges: zipfile reads only the parts it needs (the big timetable is 200 MB,
    its stops 2 MB)."""

    def __init__(self, url: str):
        self.url, self.pos = url, 0
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            self.size = int(r.headers["Content-Length"])

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def readinto(self, b):
        if self.pos >= self.size:
            return 0
        end = min(self.size, self.pos + len(b)) - 1
        req = urllib.request.Request(self.url, headers={"User-Agent": UA, "Range": f"bytes={self.pos}-{end}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        b[:len(data)] = data
        self.pos += len(data)
        return len(data)


def stops() -> list[list]:
    """Every bus, tram, metro and ferry stop in the Netherlands, [id, name, lat, lon], from the open timetable's
    stops.txt, read again once a month; an older copy keeps working when that fails."""
    f = CACHE / "stops.json"
    fresh = f.exists() and time.time() - f.stat().st_mtime < STOPS_DAYS * 86400
    if not fresh and not os.environ.get("HQ_TRAVEL_OFFLINE"):
        try:
            z = zipfile.ZipFile(io.BufferedReader(_Ranged(FEEDS + "gtfs-nl.zip"), buffer_size=1 << 20))
            out = []
            with z.open("stops.txt") as fh:
                for r in csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig")):
                    if r.get("location_type", "0") in ("", "0") and r.get("stop_lat"):
                        out.append([r["stop_id"], r.get("stop_name", ""), round(float(r["stop_lat"]), 5),
                                    round(float(r["stop_lon"]), 5)])
            if out:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(json.dumps(out, ensure_ascii=False))
        except Exception as e:
            print(f"trips: couldn't read the stops: {e!r}", file=sys.stderr)
    try:
        return json.loads(f.read_text(encoding="utf8"))
    except (OSError, ValueError):
        return []


def stops_near(place: dict, all_stops: list[list] | None = None) -> list[str]:
    g = _latlon(place)
    if not g:
        return []
    all_stops = stops() if all_stops is None else all_stops
    dlat = STOP_M / 111000
    return [s[0] for s in all_stops if abs(s[2] - g[0]) < dlat * 1.5 and metres(g, (s[2], s[3])) <= STOP_M]


# -- the live feeds (GTFS-realtime, read with the standard library) --------------------------------------------------

def _varint(b: bytes, i: int) -> tuple[int, int]:
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        s += 7
        if x < 0x80:
            return r, i


def pb(b: bytes) -> dict[int, list]:
    """One protobuf message: its fields by number, each a list of ints (varints) or bytes (everything else)."""
    out: dict[int, list] = {}
    i = 0
    while i < len(b):
        k, i = _varint(b, i)
        f, w = k >> 3, k & 7
        if w == 0:
            v, i = _varint(b, i)
        elif w == 2:
            n, i = _varint(b, i)
            v, i = b[i:i + n], i + n
        elif w == 1:
            v, i = b[i:i + 8], i + 8
        elif w == 5:
            v, i = b[i:i + 4], i + 4
        else:
            raise ValueError(f"protobuf wire type {w}")
        out.setdefault(f, []).append(v)
    return out


def _s(m: dict, f: int) -> str:
    v = m.get(f)
    return v[0].decode("utf8", "replace") if v and isinstance(v[0], bytes) else ""


def _n(m: dict, f: int, default: int = 0) -> int:
    v = m.get(f)
    if not v or isinstance(v[0], bytes):
        return default
    x = v[0]
    return x - (1 << 64) if x >= 1 << 63 else x  # int32/int64 delays can be negative


def feed(name: str) -> bytes:
    """One of the live feeds, asked at most once a FEED_FRESH and only when it changed; b"" when there's none."""
    f = CACHE / name
    fake = os.environ.get("HQ_TRIPS_FAKE_DIR")  # tests: the feeds as files
    if fake:
        p = Path(fake) / name
        return p.read_bytes() if p.exists() else b""
    meta = CACHE / (name + ".json")
    m = travel._read_json(meta)
    if not f.exists() or time.time() - float(m.get("asked") or 0) >= FEED_FRESH:
        hdr = {"If-Modified-Since": m["modified"]} if m.get("modified") and f.exists() else {}
        try:
            code, body, h = _get(FEEDS + name, 30, hdr)
            if code == 200 and body[:1] == b"\x0a":
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(body)
                m["modified"] = h.get("Last-Modified", "")
            m["asked"] = time.time()
            meta.write_text(json.dumps(m))
        except Exception as e:
            print(f"trips: {name}: {e!r}", file=sys.stderr)
    return f.read_bytes() if f.exists() else b""


def trains(data: bytes) -> list[dict]:
    """The trains in trainUpdates: {number, kind, cancelled, stops: [{code, arr, arr_delay, dep, dep_delay, skipped,
    track, track_now}]}, times in seconds since 1970 as live (the planned time is the live one minus the delay)."""
    out = []
    for ent in pb(data).get(2, []) if data else []:
        e = pb(ent)
        if 3 not in e:
            continue
        tu = pb(e[3][0])
        td = pb(tu[1][0]) if 1 in tu else {}
        ext = pb(td[1003][0]) if 1003 in td else {}
        rid = _s(ext, 1)  # "IFF:IC:2168"
        number = _s(ext, 2) or rid.rsplit(":", 1)[-1]
        kind = rid.split(":")[1] if rid.count(":") >= 2 else ""
        st = []
        for raw in tu.get(2, []):
            u = pb(raw)
            ux = pb(u[1003][0]) if 1003 in u else {}
            arr = pb(u[2][0]) if 2 in u else {}
            dep = pb(u[3][0]) if 3 in u else {}
            st.append({"code": _s(ux, 4).lower(), "arr": _n(arr, 2), "arr_delay": _n(arr, 1), "dep": _n(dep, 2),
                       "dep_delay": _n(dep, 1), "skipped": _n(u, 5) == 1, "track": _s(ux, 2), "track_now": _s(ux, 3)})
        out.append({"number": number, "kind": kind, "cancelled": _n(td, 4) == 3, "date": _s(td, 3), "stops": st})
    return out


def alerts(data: bytes) -> list[dict]:
    """The bus, tram and metro messages in alerts.pb: {id, text, stops, routes, periods: [(from, to)]}."""
    out = []
    for ent in pb(data).get(2, []) if data else []:
        e = pb(ent)
        if 5 not in e:
            continue
        a = pb(e[5][0])

        def words(f):
            if f not in a:
                return ""
            ts = [pb(x) for x in pb(a[f][0]).get(1, [])]
            nl = next((t for t in ts if _s(t, 2) in ("nl", "")), ts[0] if ts else {})
            return _s(nl, 1) if nl else ""
        ie = [pb(x) for x in a.get(5, [])]
        periods = [(_n(p, 1), _n(p, 2)) for p in (pb(x) for x in a.get(1, []))]
        text = words(10)
        more = words(11)
        out.append({"id": _s(e, 1), "text": text if not more or more.strip() == text.strip() else f"{text} {more}".strip(),
                    "stops": [_s(x, 5) for x in ie if _s(x, 5)], "routes": [_s(x, 2) for x in ie if _s(x, 2)],
                    "periods": periods})
    return out


# -- a trip -------------------------------------------------------------------------------------------------------

def _ts(iso: str) -> float:
    return agenda._sort_key(iso or "")


def _hm(t: float) -> str:
    return datetime.fromtimestamp(t).strftime("%H:%M")


def _prev(e: dict, evs: list[dict], s: dict) -> dict | None:
    """The appointment just before it that day with a place: where this trip starts."""
    import weather
    t0 = _ts(e.get("start", ""))
    best = None
    for o in evs:
        if o is e or o.get("id") == e.get("id") or o.get("all_day") or o.get("free"):
            continue
        end = _ts(o.get("end") or o.get("start", ""))
        if not (t0 - PREV_GAP <= end <= t0) or (o.get("start", "")[:10] != e.get("start", "")[:10]):
            continue
        rec = s["trips"].get(_key(o.get("id", "")))
        if rec and rec.get("to_place"):
            cand = rec["to_place"]
        elif weather._out_event(o) and (o.get("where") or "").strip():
            cand = {"text": o["where"].strip()}
        else:
            continue
        if best is None or end > best[0]:
            best = (end, cand, o)
    return best and {**best[1], "after": best[2].get("title", "")}


def destination(e: dict, places: dict, hand: str = "") -> str:
    """Where the appointment is, as words travel.where() takes: by hand, else its place, else a name in the book."""
    if hand:
        p = places.get(_norm(hand))
        return p["address"] if p else hand
    where_ = (e.get("where") or "").strip()
    if where_ and not re.match(r"(https?://|www\.)", where_.lower()):
        p = places.get(_norm(where_))
        return p["address"] if p else where_
    p = place_in(e.get("title", ""), places)
    return p["address"] if p else ""


def wanted(e: dict) -> bool:
    """An appointment that gets travel by itself: away from home (as the weather sees it), with a time."""
    import weather
    return not e.get("all_day") and not e.get("free") and weather._out_event(e)


def plan(e: dict, s: dict, evs: list[dict]) -> dict:
    """Works out a trip for the appointment: its ends, the 9292 link, the stations and the stops. Looks places up."""
    key = _key(e.get("id", ""))
    rec = dict(s["trips"].get(key) or {})
    to_text = destination(e, s["places"], rec.get("to_hand", ""))
    if not to_text:
        raise NotFound(f"where {e.get('title')!r} is: give the place, or keep it in the places book")
    b = travel.where(to_text)
    if rec.get("from_hand"):
        frm = rec["from_hand"]
        p = s["places"].get(_norm(frm))
        a = travel.where(p["address"] if p else frm) | {"start": "named"}
    else:
        pv = _prev(e, evs, s)
        if pv and pv.get("id"):
            a = {k: v for k, v in pv.items() if k != "after"} | {"start": "before", "after": pv.get("after", "")}
        elif pv and pv.get("text"):
            a = travel.where(pv["text"]) | {"start": "before", "after": pv.get("after", "")}
        else:
            a = travel.where("") | {"start": "home"}
    lk = travel.link_for(a, b)
    all_stops = stops()
    st_a, st_b = nearest_station(a), nearest_station(b)
    if st_a and st_b and st_a["code"] == st_b["code"]:
        st_a = st_b = None  # close by: no train
    rec.update({
        "on": rec.get("on", True), "title": e.get("title", ""), "start": e.get("start", ""),
        "to_text": to_text, "to_place": {k: b.get(k) for k in ("id", "label", "kind")},
        "from_place": {k: a.get(k) for k in ("id", "label", "kind", "start", "after") if a.get(k) is not None},
        "link": lk["url"], "stations": {"from": st_a, "to": st_b},
        "stops": {"from": stops_near(a, all_stops), "to": stops_near(b, all_stops)},
        "planned": time.time(),
    })
    if rec.get("train") and rec.get("train_for") != [e.get("start"), (st_a or {}).get("code"), (st_b or {}).get("code")]:
        rec.pop("train", None)  # moved, or other ends: the train is picked again
    rec.pop("why_not", None)
    return rec


def _set(e: dict, change: dict) -> dict:
    with _lock:
        s = _read()
        key = _key(e.get("id", ""))
        rec = {**(s["trips"].get(key) or {}), **change, "title": e.get("title", ""), "start": e.get("start", "")}
        s["trips"][key] = rec
        _write(s)
        return rec


def turn_on(words: str, to: str = "", frm: str = "") -> dict:
    e = find(words)
    change = {"on": True, "by": "hand"}
    if to:
        change["to_hand"] = to
    if frm:
        change["from_hand"] = "" if _norm(frm) in {_norm(w) for w in travel.HOME_WORDS} else frm
        if not change["from_hand"]:
            change["from_hand"] = "home"
    _set(e, change)
    with _lock:  # look it up now, so the answer can say where from and to
        s = _read()
        key = _key(e.get("id", ""))
        try:
            s["trips"][key] = plan(e, s, _events())
        except (NotFound, travel.NotFound) as x:
            s["trips"][key]["why_not"] = str(x)
        _write(s)
        return s["trips"][key]


def turn_off(words: str) -> dict:
    e = find(words)
    return _set(e, {"on": False, "by": "hand"})


def page_switch(eid: str, want: bool) -> dict:
    """The app's Travel button: on or off by hand. On looks the trip up in the background."""
    e = next((x for x in _events() if x.get("id") == eid), None)
    if not e:
        raise KeyError("no such appointment")
    rec = _set(e, {"on": bool(want), "by": "hand"})
    if want:
        _spawn("check")
    return rec


def attach(events: list[dict]) -> list[dict]:
    """The page's appointments with their trip: travel {on, from, to, link, train, news, why_not}, or nothing."""
    if not on():
        return events
    s = _read()
    out = []
    for e in events:
        rec = s["trips"].get(_key(e.get("id", ""))) or s["trips"].get(e.get("mark_id") or "")
        if rec:
            e = {**e, "travel": _view(rec)}
        elif not e.get("all_day") and not e.get("free"):
            e = {**e, "travel": {"on": False, "can": True}}
        out.append(e)
    return out


def _view(rec: dict) -> dict:
    f = rec.get("from_place") or {}
    st = rec.get("stations") or {}
    v = {"on": bool(rec.get("on")), "by": rec.get("by", "auto"), "link": rec.get("link", ""),
         "to": (rec.get("to_place") or {}).get("label", ""),
         "from": ("home" if f.get("start") == "home" else f.get("label", "")) if f else "",
         "after": f.get("after", "") if f.get("start") == "before" else "",
         "stations": [x["name"] for x in (st.get("from"), st.get("to")) if x],
         "news": list(rec.get("news") or [])[-3:], "why_not": rec.get("why_not", "")}
    tr = rec.get("train")
    if tr:
        v["train"] = f"{tr.get('kind') or 'train'} {tr['number']}, {_hm(tr['dep'])} from {tr['from']} to {tr['to']}, there {_hm(tr['arr'])}"
    return v


# -- the live look ---------------------------------------------------------------------------------------------------

def pick_train(rec: dict, at: float, all_trains: list[dict]) -> dict | None:
    """The latest direct train from the start's station that reaches the appointment's station in time."""
    st = rec.get("stations") or {}
    a, b = (st.get("from") or {}).get("code"), (st.get("to") or {}).get("code")
    if not a or not b:
        return None
    walk = (st.get("to") or {}).get("metres", 0) / WALK_SPEED + BUFFER
    latest = at - walk * 60
    best = None
    for t in all_trains:
        if t["cancelled"]:
            continue
        codes = [x["code"] for x in t["stops"]]
        if a not in codes or b not in codes or codes.index(a) >= codes.index(b):
            continue
        sa, sb = t["stops"][codes.index(a)], t["stops"][codes.index(b)]
        dep = (sa["dep"] or sa["arr"]) - (sa["dep_delay"] if sa["dep"] else sa["arr_delay"])
        arr = (sb["arr"] or sb["dep"]) - (sb["arr_delay"] if sb["arr"] else sb["dep_delay"])
        if not dep or not arr or arr > latest or dep < at - LIVE_BEFORE - 3600:
            continue
        if best is None or arr > best["arr"]:
            best = {"number": t["number"], "kind": t["kind"], "dep": dep, "arr": arr, "from": st["from"]["name"],
                    "to": st["to"]["name"], "track": sa["track"]}
    return best


def train_news(rec: dict, all_trains: list[dict]) -> list[tuple[str, str]]:
    """What changed for his train since the last look: [(key, words)]. Updates rec's last seen state."""
    tr = rec.get("train")
    if not tr:
        return []
    st = rec["stations"]
    a, b = st["from"]["code"], st["to"]["code"]
    same = [t for t in all_trains if t["number"] == tr["number"]]
    t = next((x for x in same if not x["cancelled"]), None) or (same[0] if same else None)
    seen = rec.setdefault("seen", {})
    out = []
    name = f"the {_hm(tr['dep'])} {tr.get('kind') or 'train'} from {tr['from']} to {tr['to']} (train {tr['number']})"
    if t is None:
        return out  # not in the feed (yet, or any more): nothing to say
    if t["cancelled"]:
        if not seen.get("cancelled"):
            seen["cancelled"] = True
            out.append((f"cancel-{tr['number']}", f"{name} is cancelled."))
        return out
    codes = [x["code"] for x in t["stops"]]
    for code, which in ((a, "from"), (b, "to")):
        if code in codes and t["stops"][codes.index(code)]["skipped"] and not seen.get(f"skip-{code}"):
            seen[f"skip-{code}"] = True
            out.append((f"skip-{tr['number']}-{code}", f"{name} doesn't stop at {st[which]['name']} now."))
    if a in codes:
        sa = t["stops"][codes.index(a)]
        delay = round((sa["dep_delay"] if sa["dep"] else sa["arr_delay"]) / 60)
        told = int(seen.get("delay", 0))
        if abs(delay - told) >= LATE_MIN and (delay >= LATE_MIN or told >= LATE_MIN):
            seen["delay"] = delay
            out.append((f"delay-{tr['number']}-{delay}", f"{name} is now {delay} minutes late, leaving around "
                        f"{_hm(tr['dep'] + delay * 60)}." if delay > 0 else f"{name} is on time again."))
        if sa["track_now"] and sa["track_now"] != sa["track"] and seen.get("track") != sa["track_now"]:
            seen["track"] = sa["track_now"]
            out.append((f"track-{tr['number']}-{sa['track_now']}", f"{name} leaves from platform {sa['track_now']}, "
                        f"not {sa['track'] or 'the usual one'}."))
    return out


def station_news(rec: dict, at: float, all_trains: list[dict]) -> list[tuple[str, str]]:
    """No direct train: trouble at either end's station (many trains cancelled around the trip: a strike or works)."""
    out = []
    for which in ("from", "to"):
        st = (rec.get("stations") or {}).get(which)
        if not st:
            continue
        lo, hi = at - LIVE_BEFORE, at + 3600
        there, gone = 0, 0
        for t in all_trains:
            x = next((x for x in t["stops"] if x["code"] == st["code"]), None)
            if t["cancelled"]:
                continue  # a cancelled trip has no stops in the feed; its stops are what's skipped below
            if not x:
                continue
            when = (x["dep"] or x["arr"])
            if lo <= when <= hi:
                there += 1
                gone += x["skipped"]
        if there and gone >= CROWD_MIN and gone / there >= CROWD:
            out.append((f"crowd-{st['code']}-{datetime.fromtimestamp(at):%Y%m%d}",
                        f"{gone} of the {there} trains at {st['name']} around then don't stop there now: "
                        "there's trouble on the rails (works or a strike). Check the trip again."))
    return out


def stop_news(rec: dict, at: float, all_alerts: list[dict]) -> list[tuple[str, str]]:
    """A bus, tram or metro message for a stop near either end, active around the trip."""
    near = set((rec.get("stops") or {}).get("from") or []) | set((rec.get("stops") or {}).get("to") or [])
    out = []
    for al in all_alerts:
        if not near.intersection(al["stops"]) or not al["text"]:
            continue
        if al["periods"] and not any((p0 or 0) <= at and (p1 or at + 1) >= at - LIVE_BEFORE for p0, p1 in al["periods"]):
            continue
        start_side = set((rec.get("stops") or {}).get("from") or []).intersection(al["stops"])
        out.append((f"stop-{al['id']}", f"A message for a stop near {'the start' if start_side else 'the appointment'}: "
                    f"{al['text']}"))
    return out


def check(now: float | None = None, dry: bool = False) -> list[tuple[str, str]]:
    """The routine's look: trips for new appointments, then the live ones. Texts each change once. [(key, facts)]."""
    if not on():
        return []
    t = now or time.time()
    evs = _events()
    texts: list[tuple[str, str]] = []
    with _lock:
        s = _read()
        by = {_key(e.get("id", "")): e for e in evs}
        # new appointments away from home get travel by themselves; hand-off stays off; moved ones are looked up again
        for key, e in by.items():
            at = _ts(e.get("start", ""))
            if not at or at < t or at > t + DAYS_AHEAD * 86400:
                continue
            rec = s["trips"].get(key)
            if rec is None and not wanted(e):
                continue
            if rec is not None and not rec.get("on"):
                continue
            if rec and rec.get("planned") and rec.get("start") == e.get("start") and rec.get("title") == e.get("title") \
                    and t - float(rec["planned"]) < 86400:
                continue
            try:
                s["trips"][key] = plan(e, s, evs) | ({} if rec else {"on": True, "by": "auto"})
            except (NotFound, travel.NotFound) as x:
                if rec is None:
                    continue  # nothing known about where it is: no trip
                s["trips"][key] = {**rec, "why_not": str(x), "planned": t, "start": e.get("start", ""), "title": e.get("title", "")}
        live = [(k, r) for k, r in s["trips"].items() if r.get("on") and r.get("link")
                and 0 <= _ts((by.get(k) or r).get("start", "")) - t <= LIVE_BEFORE]
        if live:
            all_trains = trains(feed("trainUpdates.pb"))
            all_alerts = alerts(feed("alerts.pb"))
            for key, rec in live:
                at = _ts((by.get(key) or rec).get("start", ""))
                if not rec.get("train") and all_trains:
                    tr = pick_train(rec, at, all_trains)
                    if tr:
                        st = rec.get("stations") or {}
                        rec["train"] = tr
                        rec["train_for"] = [rec.get("start"), (st.get("from") or {}).get("code"), (st.get("to") or {}).get("code")]
                news = train_news(rec, all_trains) if rec.get("train") else station_news(rec, at, all_trains)
                news += stop_news(rec, at, all_alerts)
                sent = rec.setdefault("sent", [])
                fresh = [(k, w) for k, w in news if k not in sent]
                if not fresh:
                    continue
                sent.extend(k for k, _ in fresh)
                rec["news"] = (list(rec.get("news") or []) + [f"{_hm(t)} {w}" for _, w in fresh])[-10:]
                texts.append((key, _facts(rec, [w for _, w in fresh])))
        for k, r in list(s["trips"].items()):  # trips of appointments well over go
            at = _ts(r.get("start", ""))
            if at and at < t - KEEP_DONE:
                s["trips"].pop(k)
        s["checked"] = t
        if not dry:
            _write(s)
    if texts and not dry:
        try:
            import pings
            asleep = pings._asleep(t)
        except Exception:
            asleep = False
        try:
            import direct_line
            if direct_line.on() and not asleep:
                for _, facts in texts:
                    direct_line.text("travel", facts)
        except Exception as e:
            print(f"trips: texting: {e!r}", file=sys.stderr)
    return texts


def _facts(rec: dict, news: list[str]) -> str:
    f = rec.get("from_place") or {}
    lines = [f"Trip to: {rec.get('title', '')} at {_hm(_ts(rec.get('start', '')))}",
             f"From: {'home' if f.get('start') == 'home' else f.get('label', '')}",
             f"To: {(rec.get('to_place') or {}).get('label', '')}"]
    lines += [f"Changed: {w}" for w in news]
    lines.append(f"9292 link for the trip: {rec.get('link', '')}")
    return "\n".join(lines)


def due(now: float | None = None) -> bool:
    if not on():
        return False
    t = now or time.time()
    s = _read()
    last = float(s.get("checked") or 0)
    hour = datetime.fromtimestamp(t).hour
    live = any(r.get("on") and 0 <= _ts(r.get("start", "")) - t <= LIVE_BEFORE for r in s["trips"].values())
    if live:
        return t - last >= CHECK_EVERY
    return 7 <= hour < 23 and t - last >= PLAN_EVERY


def _spawn(*args: str) -> None:
    py = ROOT / ".venv" / "bin" / "python"
    log = ROOT / "scratch" / "trips.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([str(py) if py.exists() else sys.executable, str(Path(__file__).resolve()), *args],
                     cwd=str(ROOT), stdout=open(log, "a"), stderr=subprocess.STDOUT, start_new_session=True)


def start(now: float | None = None) -> bool:
    """From tick.py, every minute on the main: a look when one is due, detached (the network can take a while)."""
    if not due(now):
        return False
    with _lock:
        s = _read()
        s["checked"] = now or time.time()
        _write(s)
    _spawn("check")
    return True


# -- what a call reads ---------------------------------------------------------------------------------------------

def text(now: float | None = None) -> str:
    t = now or time.time()
    s = _read()
    rows = sorted(((k, r) for k, r in s["trips"].items() if _ts(r.get("start", "")) >= t - 3600),
                  key=lambda kr: _ts(kr[1].get("start", "")))
    if not on():
        return "Travel on appointments is off (Settings, What HQ helps you with)."
    if not rows:
        return "No trips on appointments coming up."
    lines = ["Trips on appointments (travel on appointments, H229):"]
    for k, r in rows:
        v = _view(r)
        if not v["on"]:
            lines.append(f"- {r.get('title')} ({agenda.when_words(r)}): travel off{' (by hand)' if v['by'] == 'hand' else ''}")
            continue
        lines.append(f"- {r.get('title')} ({agenda.when_words(r)}): from {v['from'] or '?'}"
                     + (f" (after {v['after']})" if v["after"] else "") + f" to {v['to'] or '?'}"
                     + (f"; stations {' and '.join(v['stations'])}" if v["stations"] else "")
                     + (f"; {v['train']}" if v.get("train") else "") + (f"; not found: {v['why_not']}" if v["why_not"] else "")
                     + (f"; link {v['link']}" if v["link"] else ""))
        for n in v["news"]:
            lines.append(f"    told: {n}")
    if s["places"]:
        lines.append("Places book: " + "; ".join(f"{p['name']}: {p['label']}" for p in s["places"].values()))
    return "\n".join(lines)


def show(words: str) -> str:
    e = find(words)
    s = _read()
    rec = s["trips"].get(_key(e.get("id", "")))
    if not rec or not rec.get("on"):
        return f"Travel is off for {e.get('title')}."
    out = [text_one(rec)]
    at = _ts(e.get("start", ""))
    if 0 <= at - time.time() <= LIVE_BEFORE + 6 * 3600:
        tr = trains(feed("trainUpdates.pb"))
        pick = rec.get("train") or pick_train(rec, at, tr)
        if pick:
            out.append(f"Train: {pick.get('kind') or 'train'} {pick['number']}, {_hm(pick['dep'])} from {pick['from']}, "
                       f"there {_hm(pick['arr'])}" + (f", platform {pick['track']}" if pick.get("track") else ""))
        elif rec.get("stations", {}).get("from") and rec.get("stations", {}).get("to"):
            out.append("No direct train in the open data for then: it's a trip with a change, or too far ahead.")
    else:
        out.append("The live data covers the hours before; HQ starts watching " + f"{LIVE_BEFORE // 3600} hours before it.")
    return "\n".join(out)


def text_one(rec: dict) -> str:
    v = _view(rec)
    return (f"{rec.get('title')} ({agenda.when_words(rec)}): from {v['from'] or '?'} to {v['to'] or '?'}"
            + (f"; stations {' and '.join(v['stations'])}" if v["stations"] else "; no train stations near both ends")
            + (f"; not found: {v['why_not']}" if v["why_not"] else "") + (f"\n{v['link']}" if v["link"] else ""))


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Travel on appointments (H229)")
    sub = p.add_subparsers(dest="cmd")
    o = sub.add_parser("on")
    o.add_argument("words")
    o.add_argument("--to", default="")
    o.add_argument("--from", dest="frm", default="")
    sub.add_parser("off").add_argument("words")
    sub.add_parser("show").add_argument("words")
    pl = sub.add_parser("place")
    pl.add_argument("name")
    pl.add_argument("address")
    sub.add_parser("places")
    sub.add_parser("forget").add_argument("name")
    c = sub.add_parser("check")
    c.add_argument("--dry", action="store_true")
    sub.add_parser("list")
    a = p.parse_args(argv)
    try:
        if a.cmd in (None, "list"):
            print(text())
        elif a.cmd == "on":
            r = turn_on(a.words, a.to, a.frm)
            print("Travel is on. " + text_one(r))
        elif a.cmd == "off":
            r = turn_off(a.words)
            print(f"Travel is off for {r.get('title')}; it stays off.")
        elif a.cmd == "show":
            print(show(a.words))
        elif a.cmd == "place":
            r = place_add(a.name, a.address)
            print(f"Kept: {r['name']} is {r['label']}.")
        elif a.cmd == "places":
            ps = _read()["places"]
            print("\n".join(f"{x['name']}: {x['label']}" for x in ps.values()) or "No places kept yet.")
        elif a.cmd == "forget":
            print("Forgotten." if place_forget(a.name) else "There's no place by that name.")
        elif a.cmd == "check":
            for _, facts in check(dry=a.dry):
                print(facts + "\n")
    except (NotFound, travel.NotFound, ValueError) as e:
        print(f"Couldn't: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
