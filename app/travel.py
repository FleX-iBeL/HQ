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

    python3 app/travel.py link "TO" [--from "FROM"] [--train]   the link, and what it understood
    python3 app/travel.py link "TO" --json                       the same as JSON
    python3 app/travel.py where "PLACE"                          what a place resolves to (a check)

FROM is home when left out; "home" (or thuis) works for TO too.
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


def link(to: str, frm: str = "", train: bool = False) -> dict:
    a, b = where(frm), where(to)
    q = {"van": a["id"], "vanLabel": a["label"], "naar": b["id"], "naarLabel": b["label"]}
    if train:
        q["modalities"] = "Train"  # walking to and from the train stays, as on 9292 itself
    url = PLANNER + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote, safe="@,")
    return {"url": url, "from": a, "to": b, "train": train}


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="A 9292 link door to door (H214)")
    sub = p.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("link")
    l.add_argument("to")
    l.add_argument("--from", dest="frm", default="")
    l.add_argument("--train", action="store_true", help="trains and walking only")
    l.add_argument("--json", action="store_true")
    w = sub.add_parser("where")
    w.add_argument("place")
    a = p.parse_args(argv)
    try:
        if a.cmd == "where":
            print(json.dumps(where(a.place), ensure_ascii=False))
            return 0
        r = link(a.to, a.frm, a.train)
    except NotFound as e:
        print(f"Couldn't find {e}. Ask for the address, a station or a town.")
        return 1
    if a.json:
        print(json.dumps(r, ensure_ascii=False))
        return 0
    side = lambda x: x["label"] + (" (home)" if x.get("home") else f" ({x['kind']})")
    print(r["url"])
    print(f"From {side(r['from'])} to {side(r['to'])}" + (", trains and walking only." if r["train"] else "."))
    print("9 2 9 2 opens with both filled in and plans from now; a time or date is changed there.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
