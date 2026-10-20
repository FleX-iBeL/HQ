"""Public transport advice door to door, as a 9292 link (H214, 19 October 2026).

The user, on the call: "if you develop an app, you can connect to it. ... No hidden browser nonsense unless this is
actually the way to do it. ... I think the government needs to give this information. Publicly, you can just draw that
information." So no browser and no scraping of 9292's own data service (that one wants a signed header from its web
page). 9292's planner takes the start and the end in its link itself, `?van=…&naar=…` (where its old /reisadvies links
go too), and a place on the map is `@latitude,longitude`, the same as its own "current location". So:

- an address, street, postcode or town: the government's open address service (PDOK Locatieserver, BAG; free, no key)
  gives its point, and the link gets `@lat,lon` with the address as its label;
- a train station: the open station list (Rijden de Treinen, CC0) gives 9292's own station id, `station-<slug>`;
- home: the **Home:** line in the workspace's me.md.

9292 opens on that link with both filled in and plans right away (from now). `--train` limits it to trains and
walking. Nothing about the user is in here; their home address only comes from their own me.md.

H216 (20 October 2026, call at 14:03), the user: "I want never that vervoer met toeslag, by default". Every link says
`withSurcharge=false`, 9292's own switch for "Vervoer met toeslag" (the planner's search parameter, read from its
page's code and checked on a real link: the advice it plans carries it); `--surcharge` puts it back on, only when asked.

H218 (20 October 2026, call at 14:24), the user: "apparently there is also another one about reservation. I also, by
default, don't want that one turned on." Every link also says `onDemand=false`, 9292's own switch for "Vervoer met
reservering" (buses, boats and taxis booked ahead; the planner's search parameter next to the surcharge one, read from
its page's code); `--reservation` puts it back on, only when asked.

H217 (same call): "Also is it possible it picks my gps?" Without a start named, the link starts where the phone is:
the spot the call page or Donna's chat sent (`here`, only when he has allowed his location in the app, as the weather
does: H161), or else the weather's last spot from the phone, while either is under HERE_FRESH old; else home, as
before. A start he names wins, and "home" is home. The output says which start it used. The spot is kept in the direct
line's folder (here.json, off GitHub, like weather.json).

    python3 app/travel.py link "TO" [--from "FROM"] [--train] [--surcharge] [--reservation]   the link, and what it understood
    python3 app/travel.py link "TO" --json                                     the same as JSON
    python3 app/travel.py where "PLACE"                                        what a place resolves to (a check)
    python3 app/travel.py here LAT LON                                         keep where the phone is now (the pages)

FROM is where the phone is, else home, when left out; "home" (or thuis) works for TO too.
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "routine"))
import hqpaths  # noqa: E402

PLANNER = "https://9292.nl/reisplanner"
PDOK = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
STATIONS_URL = "https://opendata.rijdendetreinen.nl/public/stations/stations-2023-09.csv"
STATIONS_CACHE = Path(os.environ.get("HQ_TRAVEL_STATIONS", str(ROOT / "scratch" / "stations.csv")))
STATIONS_DAYS = 60  # the list is read again after this; an older copy still works when the download fails
HOME_WORDS = {"home", "thuis", "my home", "huis", "naar huis", "my place", "my house"}
HERE_FRESH = 30 * 60  # H217: the phone's spot stands in for home this long
PDOK_REVERSE = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/reverse"
UA = "HQ travel link (open source; https://github.com/FleX-iBeL/HQ)"


KINDS = {"adres": "address", "weg": "street", "postcode": "postcode", "woonplaats": "town", "gemeente": "town"}


class NotFound(Exception):
    pass


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def home() -> str:
    """The user's home address, from the **Home:** line in their me.md (empty when not set)."""
    try:
        text = Path(os.environ.get("HQ_TRAVEL_ME") or Path(hqpaths.FOLDER) / "me.md").read_text(encoding="utf8")
    except OSError:
        return ""
    m = re.search(r"^\*\*Home:\*\*[ \t]*(.*)$", text, re.M | re.I)
    value = m.group(1).strip() if m else ""
    return "" if value.startswith("[") else value


def _get(url: str, timeout: float = 10) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def stations() -> list[dict]:
    """The Dutch train stations: names and 9292's slug. Kept in scratch, read again every two months."""
    fresh = STATIONS_CACHE.exists() and time.time() - STATIONS_CACHE.stat().st_mtime < STATIONS_DAYS * 86400
    if not fresh and not os.environ.get("HQ_TRAVEL_OFFLINE"):
        try:
            data = _get(STATIONS_URL, 20)
            if b"name_long" in data[:500]:
                STATIONS_CACHE.parent.mkdir(parents=True, exist_ok=True)
                STATIONS_CACHE.write_bytes(data)
        except Exception:
            pass  # an older copy, or none: then places go through the address service
    try:
        rows = list(csv.DictReader(io.StringIO(STATIONS_CACHE.read_text(encoding="utf8"))))
    except OSError:
        return []
    return [r for r in rows if r.get("country") == "NL" and r.get("slug")]


def station(text: str) -> dict | None:
    """A train station by its name ("Rotterdam Centraal", "station Zwolle", "Amsterdam CS"), or None."""
    q = _norm(text)
    q = re.sub(r"^(trein)?station(s)? ", "", q)
    q = re.sub(r" (trein)?station$", "", q)
    q = re.sub(r"\bcs\b", "centraal", q)
    if not q:
        return None
    for r in stations():
        names = {_norm(r.get(k, "")) for k in ("name_long", "name_medium", "name_short", "slug")}
        names |= {re.sub(r"\bc\b", "centraal", n) for n in names}
        if q in names:
            return {"id": f"station-{r['slug']}", "label": r["name_long"], "kind": "station"}
    return None


def address(text: str) -> dict:
    """An address, street, postcode or town, through the government's open address service (PDOK)."""
    fake = os.environ.get("HQ_TRAVEL_PLACES")  # tests: a JSON file of made-up places, {text: [lat, lon, label]}
    if fake:
        places = {_norm(k): v for k, v in json.loads(Path(fake).read_text()).items()}
        hit = places.get(_norm(text))
        if not hit:
            raise NotFound(text)
        return {"id": f"@{hit[0]},{hit[1]}", "label": hit[2], "kind": "address"}
    # With a house number it's an address first (else the street alone scores higher); then anything that's a place.
    kinds = (["adres"] if re.search(r"\d", text) else []) + ["adres OR postcode OR weg OR woonplaats"]
    d = None
    for k in kinds:
        params = {"q": text, "rows": "1", "fl": "weergavenaam,centroide_ll,type", "fq": f"type:({k})"}
        try:
            data = json.loads(_get(PDOK + "?" + urllib.parse.urlencode(params)))
        except Exception as e:
            raise NotFound(f"{text} (the address service didn't answer: {e})")
        docs = data.get("response", {}).get("docs", [])
        if docs:
            d = docs[0]
            break
    if not d:
        raise NotFound(text)
    # The service always guesses something; the longest word asked for has to be in what it found, or it's not it.
    words = [w for w in _norm(text).split() if w.isalpha() and len(w) >= 3]
    if words and max(words, key=len) not in _norm(d.get("weergavenaam", "")):
        raise NotFound(text)
    m = re.match(r"POINT\(([-0-9.]+) ([-0-9.]+)\)", d.get("centroide_ll", ""))
    if not m:
        raise NotFound(text)
    lon, lat = float(m.group(1)), float(m.group(2))
    return {"id": f"@{lat:.6f},{lon:.6f}", "label": d.get("weergavenaam") or text, "kind": KINDS.get(d.get("type", ""), "address")}


def where(text: str) -> dict:
    """Any place he names: home, a station, or an address, street, postcode or town."""
    text = (text or "").strip()
    if not text or _norm(text) in {_norm(w) for w in HOME_WORDS}:
        h = home()
        if not h:
            raise NotFound("home (there's no Home line in me.md yet)")
        out = address(h)
        out["home"] = True
        return out
    return station(text) or address(text)


def _direct_dir() -> Path:
    return Path(os.environ.get("HQ_DIRECT_DIR") or os.path.join(hqpaths.DATA, "direct-line"))


def _spot(lat, lon) -> tuple[float, float] | None:
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if lat != lat or lon != lon or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return round(lat, 4), round(lon, 4)  # about ten metres: enough for the door, no more


def set_here(lat, lon, now: float | None = None) -> dict:
    """H217: keep where the phone is now (the call page or Donna's chat sends it, only when he allows his location)."""
    g = _spot(lat, lon)
    if not g:
        return {"ok": False}
    f = _direct_dir() / "here.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f".here.{os.getpid()}.tmp")
    tmp.write_text(json.dumps({"lat": g[0], "lon": g[1], "at": now or time.time()}))
    os.replace(tmp, f)
    return {"ok": True}


def _read_json(f: Path) -> dict:
    try:
        d = json.loads(f.read_text(encoding="utf8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def phone_spot(now: float | None = None) -> tuple[float, float] | None:
    """H217: where the phone is, while it's fresh: the pages' own spot first, else the weather's (H161, rounded to
    about a kilometre there); None when neither is under HERE_FRESH old."""
    now = now or time.time()
    h = _read_json(_direct_dir() / "here.json")
    if now - float(h.get("at") or 0) <= HERE_FRESH and _spot(h.get("lat"), h.get("lon")):
        return _spot(h["lat"], h["lon"])
    w = _read_json(_direct_dir() / "weather.json")
    last = w.get("here") if isinstance(w.get("here"), dict) else {}
    got = (w.get("spots") or {}).get(last.get("key")) if isinstance(w.get("spots"), dict) else None
    if isinstance(got, dict) and now - float(last.get("at") or 0) <= HERE_FRESH:
        return _spot(got.get("lat"), got.get("lon"))
    return None


def near(g: tuple[float, float]) -> str:
    """The nearest address to a spot, from the government's address service, for 9292's label ("" when unknown)."""
    if os.environ.get("HQ_TRAVEL_OFFLINE") or os.environ.get("HQ_TRAVEL_PLACES"):
        return ""
    q = {"lat": g[0], "lon": g[1], "rows": "1", "type": "adres", "fl": "weergavenaam"}
    try:
        docs = json.loads(_get(PDOK_REVERSE + "?" + urllib.parse.urlencode(q), 6)).get("response", {}).get("docs", [])
        return docs[0].get("weergavenaam", "") if docs else ""
    except Exception:
        return ""


def start(frm: str = "", now: float | None = None) -> dict:
    """Where the trip starts (H217): the place he names; "home" is home; nothing named is where the phone is, while
    that's fresh, else home. `start` says which: named, home or phone."""
    if (frm or "").strip() and _norm(frm) not in {_norm(w) for w in HOME_WORDS}:
        return where(frm) | {"start": "named"}
    g = None if (frm or "").strip() else phone_spot(now)
    if g:
        n = near(g)
        return {"id": f"@{g[0]},{g[1]}", "label": n or "My location", "near": n, "kind": "location", "start": "phone"}
    return where("") | {"start": "home"}


def link(to: str, frm: str = "", train: bool = False, surcharge: bool = False, reservation: bool = False) -> dict:
    a, b = start(frm), where(to)
    q = {"van": a["id"], "vanLabel": a["label"], "naar": b["id"], "naarLabel": b["label"]}
    if train:
        q["modalities"] = "Train"  # walking to and from the train stays, as on 9292 itself
    q["withSurcharge"] = "true" if surcharge else "false"  # H216: never "Vervoer met toeslag" unless asked
    q["onDemand"] = "true" if reservation else "false"  # H218: never "Vervoer met reservering" unless asked
    url = PLANNER + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote, safe="@,")
    return {"url": url, "from": a, "to": b, "train": train, "surcharge": surcharge, "reservation": reservation}


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="A 9292 link door to door (H214)")
    sub = p.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("link")
    l.add_argument("to")
    l.add_argument("--from", dest="frm", default="")
    l.add_argument("--train", action="store_true", help="trains and walking only")
    l.add_argument("--surcharge", action="store_true", help="also transport with a surcharge (off unless asked)")
    l.add_argument("--reservation", action="store_true", help="also transport that needs a reservation (off unless asked)")
    l.add_argument("--json", action="store_true")
    w = sub.add_parser("where")
    w.add_argument("place")
    h = sub.add_parser("here")
    h.add_argument("lat")
    h.add_argument("lon")
    a = p.parse_args(argv)
    try:
        if a.cmd == "here":
            out = set_here(a.lat, a.lon)
            print(json.dumps(out))
            return 0 if out["ok"] else 2
        if a.cmd == "where":
            print(json.dumps(where(a.place), ensure_ascii=False))
            return 0
        r = link(a.to, a.frm, a.train, a.surcharge, a.reservation)
    except NotFound as e:
        print(f"Couldn't find {e}. Ask for the address, a station or a town.")
        return 1
    if a.json:
        print(json.dumps(r, ensure_ascii=False))
        return 0
    side = lambda x: x["label"] + (" (home)" if x.get("home") else f" ({x['kind']})")
    f = r["from"]
    frm = ("where the phone is" + (f", near {f['near']}" if f.get("near") else "") if f.get("start") == "phone"
           else side(f) + (", as there's no fresh location from the phone" if f.get("start") == "home" else ""))
    print(r["url"])
    print(f"From {frm} to {side(r['to'])}" + (", trains and walking only" if r["train"] else "")
          + (", with transport with a surcharge" if r["surcharge"] else ", without transport with a surcharge")
          + (" and with transport that needs a reservation." if r["reservation"]
             else " and without transport that needs a reservation."))
    print("9 2 9 2 opens with both filled in and plans from now; a time or date is changed there.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
