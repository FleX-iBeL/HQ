"""H230: driving to appointments, with traffic, on each person's own maps key (22 October 2026).

The user's words on the call of 22 October 2026 (Pepper): "the Google one was for driving for [a friend], not for me.
I'm surprised I thought we could just do that over API for free." and "Yes, so they are separate. And... As long as it
explained well in the tutorial, then it should work right. We can still build the Google Maps one." And on the night's
plan: "They can set it up with their own card but make them two separate features."

So: its own switch (Driving to appointments, features.py, off until turned on), on the same trips as public transport
(trips.py, H229): an appointment's trip is by public transport or by car. HQ ships no key. Each person makes their own,
step by step in the tutorial, and pastes it in Settings, What HQ helps you with, under Driving; it's kept on that
computer only (~/.config/hq/maps-key, or HQ_MAPS_KEY_FILE; never in the workspace, never on GitHub). Two kinds work:

  - Google Maps (the Routes API, computeRoutes, traffic aware): a key from Google Cloud, which needs a card on file;
    its free monthly use covers one person's trips by far.
  - TomTom (the Routing API, traffic=true): a free key from TomTom's developer portal, no card (2,500 a day).

Which one is told by the key itself (Google's start with "AIza"), or --provider.

What a look gives: how long the drive takes now (with traffic), how long without traffic, and the distance. trips.py
asks once when it plans the trip (for the time he'd leave), then every DRIVE_EVERY from DRIVE_BEFORE before the
appointment, and works out when to leave. Never more than DAILY_MAX looks a day on a computer, so a mistake can't run
up anyone's bill. The link to open is Google Maps' own directions link, which needs no key.

    python3 app/drive.py                      whether driving can work here: the key's kind, today's looks
    python3 app/drive.py key "KEY" [--provider google|tomtom]   keep the key on this computer (by hand or the page)
    python3 app/drive.py forget-key           take it off this computer
    python3 app/drive.py test "TO" [--from "FROM"]   one look, to see the key works (counts as a look)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import travel  # noqa: E402

KEY_FILE = Path(os.environ.get("HQ_MAPS_KEY_FILE") or Path.home() / ".config" / "hq" / "maps-key")
COUNT_FILE = Path(os.environ.get("HQ_DRIVE_COUNT") or ROOT / "scratch" / "trips" / "drive-count.json")
GOOGLE = os.environ.get("HQ_DRIVE_GOOGLE", "https://routes.googleapis.com/directions/v2:computeRoutes")
TOMTOM = os.environ.get("HQ_DRIVE_TOMTOM", "https://api.tomtom.com/routing/1/calculateRoute/")
DAILY_MAX = 150  # looks a day on this computer, at most
PROVIDERS = {"google": "Google Maps", "tomtom": "TomTom"}


class NoKey(Exception):
    pass


class Refused(Exception):
    pass


# -- the key ------------------------------------------------------------------------------------------------------

def guess_provider(key: str) -> str:
    return "google" if key.startswith("AIza") else "tomtom"


def key() -> dict | None:
    """{provider, key} from this computer, or None. HQ_MAPS_KEY (with HQ_MAPS_PROVIDER) wins, for a test or a server."""
    k = os.environ.get("HQ_MAPS_KEY", "").strip()
    if k:
        return {"provider": os.environ.get("HQ_MAPS_PROVIDER") or guess_provider(k), "key": k}
    try:
        d = json.loads(KEY_FILE.read_text(encoding="utf8"))
    except (OSError, ValueError):
        return None
    if isinstance(d, dict) and d.get("key") and d.get("provider") in PROVIDERS:
        return d
    return None


def set_key(k: str, provider: str = "") -> dict:
    k = (k or "").strip().strip('"').strip("'")
    if len(k) < 20 or len(k) > 200 or any(c.isspace() for c in k):
        raise ValueError("that doesn't look like a key: paste it whole, without spaces")
    provider = provider or guess_provider(k)
    if provider not in PROVIDERS:
        raise ValueError(f"a key is for {' or '.join(PROVIDERS)}")
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = KEY_FILE.with_name(f".{KEY_FILE.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf8") as fh:
        json.dump({"provider": provider, "key": k, "set": time.time()}, fh)
    os.replace(tmp, KEY_FILE)
    return {"provider": provider}


def forget_key() -> bool:
    try:
        KEY_FILE.unlink()
        return True
    except OSError:
        return False


def status() -> dict:
    """For the page and a call: which kind of key is here (never the key itself) and today's looks."""
    k = key()
    return {"key": bool(k), "provider": (k or {}).get("provider", ""),
            "provider_name": PROVIDERS.get((k or {}).get("provider", ""), ""), "today": _count()[1], "max": DAILY_MAX}


# -- the daily count ------------------------------------------------------------------------------------------------

def _count() -> tuple[str, int]:
    day = datetime.now().strftime("%Y-%m-%d")
    try:
        d = json.loads(COUNT_FILE.read_text(encoding="utf8"))
    except (OSError, ValueError):
        d = {}
    return day, int(d.get(day) or 0) if isinstance(d, dict) else 0


def _bump() -> None:
    day, n = _count()
    if n >= DAILY_MAX:
        raise Refused(f"today's {DAILY_MAX} looks are used up on this computer; tomorrow again")
    COUNT_FILE.parent.mkdir(parents=True, exist_ok=True)
    COUNT_FILE.write_text(json.dumps({day: n + 1}))


# -- a look ---------------------------------------------------------------------------------------------------------

def point(place: dict) -> tuple[float, float] | None:
    """A place's spot: an address's @lat,lon, or a train station's from the open station list."""
    import re
    m = re.match(r"@([-0-9.]+),([-0-9.]+)$", place.get("id") or "")
    if m:
        return float(m.group(1)), float(m.group(2))
    if place.get("lat") is not None:
        return float(place["lat"]), float(place["lon"])
    if (place.get("id") or "").startswith("station-"):
        slug = place["id"].removeprefix("station-")
        r = next((r for r in travel.stations() if r.get("slug") == slug), None)
        if r:
            return float(r["geo_lat"]), float(r["geo_lng"])
    return None


def maps_link(a: tuple[float, float], b: tuple[float, float]) -> str:
    """Google Maps' own directions link, by car; it needs no key."""
    return "https://www.google.com/maps/dir/?" + urllib.parse.urlencode(
        {"api": 1, "origin": f"{a[0]:.5f},{a[1]:.5f}", "destination": f"{b[0]:.5f},{b[1]:.5f}", "travelmode": "driving"})


def _post(url: str, body: dict, headers: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": travel.UA, **headers})
    return _open(req)


def _open(req) -> dict:
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            why = json.loads(e.read() or b"{}")
            why = (why.get("error") or {}).get("message") or why.get("detailedError", {}).get("message") or str(why)
        except Exception:
            why = ""
        raise Refused(f"the maps service said no ({e.code}){': ' + str(why)[:200] if why else ''}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Refused(f"the maps service didn't answer ({e})")


def _secs(s) -> int:
    return int(float(str(s).rstrip("s") or 0))


def look(a: tuple[float, float], b: tuple[float, float], depart: float | None = None) -> dict:
    """One drive: {minutes, free_minutes, traffic, km, provider}. depart None is now; a later time uses the traffic
    that's expected then. Counts against DAILY_MAX."""
    k = key()
    if not k:
        raise NoKey("no maps key on this computer: paste yours in Settings, What HQ helps you with, Driving")
    fake = os.environ.get("HQ_DRIVE_FAKE")  # tests: a file with the answer, {minutes, free_minutes, km}
    _bump()
    if fake:
        d = json.loads(Path(fake).read_text(encoding="utf8"))
        mins, free, km = float(d["minutes"]), float(d.get("free_minutes", d["minutes"])), float(d.get("km", 0))
    elif k["provider"] == "google":
        body = {"origin": {"location": {"latLng": {"latitude": a[0], "longitude": a[1]}}},
                "destination": {"location": {"latLng": {"latitude": b[0], "longitude": b[1]}}},
                "travelMode": "DRIVE", "routingPreference": "TRAFFIC_AWARE"}
        if depart and depart > time.time() + 60:
            body["departureTime"] = datetime.fromtimestamp(depart, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        d = _post(GOOGLE, body, {"X-Goog-Api-Key": k["key"],
                                 "X-Goog-FieldMask": "routes.duration,routes.staticDuration,routes.distanceMeters"})
        r = (d.get("routes") or [None])[0]
        if not r:
            raise Refused("Google found no route by car between these two places")
        mins, free, km = _secs(r.get("duration")) / 60, _secs(r.get("staticDuration") or r.get("duration")) / 60, \
            (r.get("distanceMeters") or 0) / 1000
    else:
        q = {"key": k["key"], "traffic": "true", "travelMode": "car", "routeType": "fastest"}
        if depart and depart > time.time() + 60:
            q["departAt"] = datetime.fromtimestamp(depart, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        url = f"{TOMTOM}{a[0]:.6f},{a[1]:.6f}:{b[0]:.6f},{b[1]:.6f}/json?" + urllib.parse.urlencode(q)
        d = _open(urllib.request.Request(url, headers={"User-Agent": travel.UA}))
        r = (d.get("routes") or [None])[0]
        if not r:
            raise Refused("TomTom found no route by car between these two places")
        sm = r.get("summary") or {}
        mins = sm.get("travelTimeInSeconds", 0) / 60
        free = sm.get("noTrafficTravelTimeInSeconds", sm.get("travelTimeInSeconds", 0) - sm.get("trafficDelayInSeconds", 0)) / 60
        km = sm.get("lengthInMeters", 0) / 1000
    return {"minutes": round(mins), "free_minutes": round(free), "traffic": max(0, round(mins - free)),
            "km": round(km, 1), "provider": k["provider"], "asked": time.time()}


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Driving to appointments (H230)")
    sub = p.add_subparsers(dest="cmd")
    kk = sub.add_parser("key")
    kk.add_argument("key")
    kk.add_argument("--provider", choices=list(PROVIDERS), default="")
    sub.add_parser("forget-key")
    t = sub.add_parser("test")
    t.add_argument("to")
    t.add_argument("--from", dest="frm", default="")
    sub.add_parser("status")
    a = p.parse_args(argv)
    try:
        if a.cmd in (None, "status"):
            s = status()
            print(f"Driving: a {s['provider_name']} key is on this computer; {s['today']} of {s['max']} looks today."
                  if s["key"] else "Driving: no maps key on this computer yet (Settings, What HQ helps you with, Driving).")
        elif a.cmd == "key":
            r = set_key(a.key, a.provider)
            try:  # car trips that waited for a key are looked up again
                import trips
                trips.key_changed()
            except Exception:
                pass
            print(f"Kept: a {PROVIDERS[r['provider']]} key, on this computer only.")
        elif a.cmd == "forget-key":
            print("The key is gone from this computer." if forget_key() else "There was no key here.")
        elif a.cmd == "test":
            fa = travel.where(a.frm) if a.frm else travel.where("")
            fb = travel.where(a.to)
            pa, pb_ = point(fa), point(fb)
            if not pa or not pb_:
                raise ValueError("couldn't put one of the two places on the map")
            r = look(pa, pb_)
            print(f"From {fa.get('label')} to {fb.get('label')} by car: {r['minutes']} minutes now "
                  f"({r['traffic']} of it traffic), {r['km']} km. {maps_link(pa, pb_)}")
    except (NoKey, Refused, ValueError, travel.NotFound) as e:
        print(f"Couldn't: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
