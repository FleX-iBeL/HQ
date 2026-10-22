"""H120: the weather every three hours, and a nudge to go outside.

13 October 2026, the user's quick note: "I also want you to check the weather every 3 hours just to have a general
overview. If it's a sunny day, maybe prompt me if I'm going to do something nice in the sun, or tell me to go outside
when it's not too busy, or enjoy the sun, stuff like that. If it's possible that it's going to rain, let me know so I
can take that into account. Don't prompt me on rainy days to go outside because it doesn't make any sense. Say maybe
I can do something cosy inside, read a book, or do some other things." And on rain by the minute (Buienalarm): "I'm
not sure how specific you can check when it's going to rain and where but let's start here at least."

Every three hours in the day (08:00 to 21:00 where the user is, never at night), on the main only, the routine
(tick.py, through start()) looks at the weather for the place in me.md (**Where I am:**). The forecast comes from
Open-Meteo (free, no key); rain by the five minutes for the next two hours from Buienradar's rain text (the
Netherlands and Belgium only; elsewhere the hourly forecast stands in). When there's something worth saying, the
direct line's agent (H80) texts it in her own words, else nothing:

  cosy   most of the rest of the day is wet: something cosy inside, never "go outside" (once a day)
  rain   dry now, rain coming in the next hours: a heads-up with when it starts (by the minute where it can)
  sun    sunny and dry for the next hours: something nice outside, or a walk when it's quiet (once a day)

H125: her watch list ("let me know if it rains later today", routine/pings.py). While a weather watch is open
the look comes every 30 minutes (WATCH_EVERY, 07:00 to 23:00), checks each open watch against the forecast up to
its time, and keeps a match for her to text (pings.match); the texts above still come only every three hours.

H135: the weather in the app. view() is what the call page shows (GET /api/weather): now (sunny or not, degrees,
wind, chance of rain), today and the next hours, UV, the rain radar's two hours, and the official weather warnings
for his area (code yellow and up; MeteoAlarm's feed, which carries KNMI's for the Netherlands). Read when the page
asks and the last read is over 15 minutes old (APP_EVERY), kept in weather.json under "app".

H161 (15 October 2026, his quick note: "is it possible to have it check with gps for more accuracy? and if possible,
a button to toggle to get alerts if rain is coming up?"). Where: the phone's location when he allows it (the page
sends it rounded to two decimals, about a kilometre; view(gps=…)), named once per spot through OpenStreetMap's
reverse geocoding (here_place); without it, the place in me.md as before. The last spot is kept (`here`) and the
looks above use it while it's under HERE_FRESH old, so her texts and watches follow him too. The rain alert: a
switch in the weather sheet (rain_alert) that opens or ends a lasting weather watch for rain on her list
(pings.watch_add(..., alert=True)): every look checks only the next ALERT_AHEAD hours, never while it's raining
already.

H196 (17 October 2026, on the call: "ok so lets have her check every 5 minutes", and about the three quiet hours
after a text: "sometimes the rain moves faster or slower or dissapears"). While the rain alert is on the look comes
every five minutes (ALERT_EVERY). Instead of three quiet hours after a text she follows that one shower (`follow`
in weather.json, by watch): she texts again only when it comes SHIFT minutes or more earlier or later than she said,
when it's gone (two looks in a row without it, GONE_LOOKS), or when it stops (dry by the radar for the next
quarter of an hour). Otherwise she stays quiet. A shower not looked at for FOLLOW_STALE (the night) is let go
without a text.

H212 (19 October 2026, call at 10:57, Pepper): weather texts that fit his day. In his words: "it rains all night and
I wake up and HQ has like 45 notifications", "If I'm asleep, then I don't care about that, right? ... All I need to
know is... When I wake up, is it gonna rain or not? And if I need to go out", "Another way is to tell her, hey, from
this time to this time, let me know", and "We can make it more humanizing." So:
  asleep    nothing: no looks, no rain alerts, no summary of the night (his calendar's Sleep block, else NIGHT)
  morning   on waking, one text only: will it rain when he's out today, yes or no (morning)
  out       before he goes out (LEAVE ahead: his calendar's appointments away from home, and the hours he gave her,
            pings.py out "14:00-18:00" [--every-day]) she looks once, and texts only when it rains then (out)
  the rain alert still looks in the background, but only texts about rain while he's out (MATTERS); the three-
  hourly "rain coming" text is gone, the sun and cosy nudges stay.

Kept in the direct line's folder (synced, off GitHub): weather.json, the last look, the place's coordinates and
what she already said today. Off: HQ_WEATHER=0. HQ_WEATHER_PLACE overrides the place (tests).

  python3 app/weather.py status            the place, the last look, whether a look is due
  .venv/bin/python app/weather.py look     look now and text if there's something worth saying
  python3 app/weather.py look --dry        what she would text now, without texting
  python3 app/weather.py view [--fresh]    what the app shows (H135)
  python3 app/weather.py alert [on|off]    the rain alert switch (H161)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "routine"))
import hqpaths  # noqa: E402

EVERY = 3 * 3600  # a look every three hours
DAY = (8, 21)  # she looks (and texts) from 08:00, the last look before 21:00, local time where the user is
WET_MM, WET_PROB = 0.3, 60  # an hour counts as wet with this much rain (mm) or this chance (%)
SUN_CODES = {0, 1, 2}  # WMO: clear, mainly clear, partly cloudy
WATCH_EVERY = 30 * 60  # H125: a look every 30 minutes while a weather watch is open
WATCH_DAY = (7, 23)  # and watches are looked at a little longer into the evening
UA = {"User-Agent": "HQ (https://github.com/FleX-iBeL/HQ)"}
HERE_FRESH = 6 * 3600  # H161: the phone's last spot stands in for me.md's place in the looks while it's this new
HERE_KEEP = 20  # named spots kept
ALERT_AHEAD = 3  # H161: the rain alert looks this many hours ahead
ALERT_YEARS = 100  # H188: the rain alert stays on until he switches it off, so it never shows an end
ALERT_EVERY = 5 * 60  # H196: a look every five minutes while the rain alert is on
SHIFT = 15 * 60  # H196: she texts again when the shower comes this much earlier or later than she said
GONE_LOOKS = 2  # H196: looks in a row without the shower before she says it's gone
FOLLOW_STALE = 3600  # H196: a shower not looked at for this long (the night) is let go quietly


def on() -> bool:
    return os.environ.get("HQ_WEATHER", "1") != "0" and os.environ.get("HQ_DIRECT", "1") != "0" and _feature("weather")


def _feature(fid: str) -> bool:
    """H205: the user's own switch in Settings, What HQ helps you with (app/features.py); on when it can't be read."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import features
        return features.is_on(fid)
    except Exception:
        return True


def state_file() -> Path:
    return Path(os.environ.get("HQ_DIRECT_DIR") or os.path.join(hqpaths.DATA, "direct-line")) / "weather.json"


def _read() -> dict:
    try:
        s = json.loads(state_file().read_text(encoding="utf8"))
        return s if isinstance(s, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(s: dict) -> None:
    p = state_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    os.replace(tmp, p)


def place() -> str:
    if os.environ.get("HQ_WEATHER_PLACE"):
        return os.environ["HQ_WEATHER_PLACE"].strip()
    try:
        import me as _me
        return _me.load(Path(hqpaths.FOLDER)).get("place", "")
    except Exception:
        return ""


def _get(url: str, timeout: int = 15) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf8", "replace")


def where(s: dict | None = None, region: bool = False) -> dict | None:
    """The place's coordinates, its time zone and country, looked up once (Open-Meteo's geocoding) and kept.
    REGION (H135, for the warnings): looked up again when it was kept from before without its region."""
    name = place()
    if not name:
        return None
    s = _read() if s is None else s
    got = s.get("where") or {}
    if got.get("place") == name and "lat" in got and (not region or "region" in got):
        return got
    q = urllib.parse.urlencode({"name": name.split(",")[0].strip(), "count": 1, "language": "en"})
    res = (json.loads(_get(f"https://geocoding-api.open-meteo.com/v1/search?{q}")).get("results") or [None])[0]
    if not res:
        return None
    got = {"place": name, "lat": res["latitude"], "lon": res["longitude"], "tz": res.get("timezone") or "UTC",
           "country": res.get("country_code") or "", "name": res.get("name") or name,
           "region": res.get("admin1") or ""}
    s["where"] = got
    return got


def _gps(gps) -> tuple[float, float] | None:
    """(lat, lon) rounded to two decimals (about a kilometre), or None when it isn't a real spot."""
    try:
        lat, lon = float(gps[0]), float(gps[1])
    except (TypeError, ValueError, IndexError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or lat != lat or lon != lon:
        return None
    return round(lat, 2), round(lon, 2)


def gps_key(g: tuple[float, float]) -> str:
    return f"gps:{g[0]:.2f},{g[1]:.2f}"


def reverse(lat: float, lon: float) -> dict:
    """H161: the spot's town, region and country, from OpenStreetMap's reverse geocoding (no key), in the local
    language, so the region matches the warnings' own names."""
    q = urllib.parse.urlencode({"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 10})
    a = json.loads(_get(f"https://nominatim.openstreetmap.org/reverse?{q}", timeout=10)).get("address") or {}
    return {"name": a.get("city") or a.get("town") or a.get("village") or a.get("municipality") or a.get("county") or "",
            "region": a.get("state") or a.get("province") or "", "country": (a.get("country_code") or "").upper()}


def here_place(g: tuple[float, float], s: dict, now: float, name=None) -> dict:
    """H161: the where-dict for the phone's spot G, named once (kept under `spots`), and marked as his last spot
    (`here`). The time zone is filled in from the forecast (Open-Meteo's own). NAME stands in for reverse (tests)."""
    key = gps_key(g)
    spots = s.get("spots") if isinstance(s.get("spots"), dict) else {}
    got = spots.pop(key, None) or {"place": key, "lat": g[0], "lon": g[1], "tz": "", "gps": True}
    if not got.get("named"):
        try:
            got |= (name or reverse)(g[0], g[1]) | {"named": True}
        except Exception:  # unnamed for now; the warnings fall back on me.md's region and country
            home = s.get("where") or {}
            got |= {"name": got.get("name") or "", "region": home.get("region", ""), "country": home.get("country", "")}
    spots[key] = got
    s["spots"] = dict(list(spots.items())[-HERE_KEEP:])
    s["here"] = {"key": key, "at": now}
    return got


def here(s: dict, now: float | None = None) -> dict | None:
    """H161: his last spot from the phone, while it's under HERE_FRESH old and its time zone is known; else None
    (the looks use me.md's place)."""
    h = s.get("here") or {}
    got = (s.get("spots") or {}).get(h.get("key")) if isinstance(s.get("spots"), dict) else None
    if not got or not got.get("tz") or (now or time.time()) - float(h.get("at") or 0) > HERE_FRESH:
        return None
    return got


def local_now(tz: str, now: float | None = None) -> datetime:
    from zoneinfo import ZoneInfo
    try:
        return datetime.fromtimestamp(now or time.time(), ZoneInfo(tz))
    except Exception:
        return datetime.fromtimestamp(now or time.time())


def _hour(now: float, s: dict) -> int:
    w = here(s, now) or s.get("where") or {}
    return local_now(w.get("tz") or "", now).hour if w.get("gps") or w.get("place") == place() \
        else datetime.fromtimestamp(now).hour


def _somewhere(s: dict, now: float) -> bool:
    """A place to look at: me.md's, or the phone's last spot (H161)."""
    return bool(place() or here(s, now))


def general_due(now: float | None = None, s: dict | None = None) -> bool:
    """The three-hourly look (its sun, rain and cosy texts): in the day where the user is, three hours since the
    last one. Cheap and offline (the time zone comes from the kept coordinates; before the first look, this
    computer's)."""
    if not on():
        return False
    now = now or time.time()
    s = _read() if s is None else s
    if not _somewhere(s, now) or not (DAY[0] <= _hour(now, s) < DAY[1]) or asleep_at(now, s):
        return False
    return now - float(s.get("general", s.get("looked")) or 0) >= EVERY - 60


def watches(now: float | None = None) -> list[dict]:
    """H125: the open weather watches on her list."""
    try:
        import pings
        return pings.open_watches("weather", now=now)
    except Exception:
        return []


def watch_due(now: float | None = None, s: dict | None = None) -> bool:
    """H125: a weather watch is open and 30 minutes have passed since the last look (07:00 to 23:00); five minutes
    while the rain alert is on (H196)."""
    if not on():
        return False
    now = now or time.time()
    s = _read() if s is None else s
    ws = watches(now)
    if not _somewhere(s, now) or not (WATCH_DAY[0] <= _hour(now, s) < WATCH_DAY[1]) or not ws or asleep_at(now, s):
        return False  # H212: asleep she says nothing
    every = ALERT_EVERY - 30 if any(w.get("alert") for w in ws) else WATCH_EVERY - 60
    return now - float(s.get("looked") or 0) >= every


def due(now: float | None = None, s: dict | None = None) -> bool:
    """A look is due: the three-hourly one, or the 30-minute one while a weather watch is open (five minutes while
    the rain alert is on)."""
    s = _read() if s is None else s
    return general_due(now, s) or watch_due(now, s) or morning_due(now, s) or out_due(now, s)  # H212


# -- the data -----------------------------------------------------------------------------------------

def forecast(w: dict) -> dict:
    q = urllib.parse.urlencode({
        "latitude": w["lat"], "longitude": w["lon"], "timezone": w.get("tz") or "auto", "forecast_days": 2,
        "current": "temperature_2m,precipitation,weather_code,cloud_cover",
        "hourly": "temperature_2m,precipitation,precipitation_probability,weather_code,cloud_cover",
        "daily": "sunset,temperature_2m_max"})
    return json.loads(_get(f"https://api.open-meteo.com/v1/forecast?{q}"))


def rain_text(w: dict) -> list[tuple[str, float]]:
    """Buienradar's rain for the next two hours, by five minutes: [(HH:MM, mm per hour)]. Only NL and BE."""
    if w.get("country") not in ("NL", "BE"):
        return []
    q = urllib.parse.urlencode({"lat": round(w["lat"], 2), "lon": round(w["lon"], 2)})
    return parse_rain(_get(f"https://gpsgadget.buienradar.nl/data/raintext?{q}", timeout=10))


def parse_rain(text: str) -> list[tuple[str, float]]:
    out = []
    for line in (text or "").splitlines():
        v, _, hm = line.strip().partition("|")
        try:
            v = int(v)
        except ValueError:
            continue
        out.append((hm.strip(), round(10 ** ((v - 109) / 32), 2) if v > 0 else 0.0))
    return out


# -- what's worth saying (no network: the happy flow feeds it) -------------------------------------------

WMO = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "foggy", 48: "foggy",
       51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
       66: "freezing rain", 67: "freezing rain", 71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
       80: "showers", 81: "showers", 82: "heavy showers", 85: "snow showers", 86: "snow showers",
       95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail"}


def _hours(fc: dict, now: datetime) -> list[dict]:
    """The forecast's hours from this hour to the end of the day window, as dicts."""
    h = fc.get("hourly") or {}
    out = []
    for i, t in enumerate(h.get("time") or []):
        at = datetime.fromisoformat(t)
        if at.date() == now.date() and now.hour <= at.hour < DAY[1]:
            out.append({k: (h.get(k) or [None] * (i + 1))[i] for k in h} | {"hour": at.hour})
    return out


def _wet(x: dict) -> bool:
    return (x.get("precipitation") or 0) >= WET_MM or (x.get("precipitation_probability") or 0) >= WET_PROB


def decide(fc: dict, minutes: list[tuple[str, float]], now: datetime, told: list[str], name: str = "") -> tuple[str, str] | None:
    """(why, facts) for one text, or None when there's nothing worth saying. told: what she said today already."""
    hours = _hours(fc, now)
    if not hours:
        return None
    cur = fc.get("current") or {}
    temp = cur.get("temperature_2m")
    code = cur.get("weather_code")
    daily = fc.get("daily") or {}
    sunset = ((daily.get("sunset") or [""])[0] or "")[11:16]
    tmax = max([(x.get("temperature_2m") or -99) for x in hours] + ([temp] if temp is not None else []))
    raining_now = (minutes[0][1] >= 0.1) if minutes else _wet(hours[0]) or (cur.get("precipitation") or 0) >= WET_MM
    wet = [x for x in hours if _wet(x)]
    base = (f"Where: {name}. " if name else "") + (f"Now {round(temp)} °C" if temp is not None else "Now") + \
        (f", {WMO.get(code, 'mixed')}" if code is not None else "") + "."
    # A rainy day: most of what's left of it is wet (and at least three hours of it left).
    if len(hours) >= 3 and len(wet) * 2 >= len(hours):
        if "cosy" in told:
            return None
        return "cosy", f"{base} Rain most of the rest of the day ({len(wet)} of the {len(hours)} hours left), " \
                       f"up to {round(tmax)} °C. A day for something cosy inside."
    # Rain coming: dry now, rain in the next two hours by the minute, or likely in the next three hours.
    if not raining_now:
        start = next((hm for hm, mm in minutes if mm >= 0.1), "")
        if start:
            peak = max(mm for _, mm in minutes)
            how = "light" if peak < 1 else "steady" if peak < 4 else "heavy"
            return "rain", f"{base} Rain from about {start} ({how}, by the minute from the rain radar)."
        soon = [x for x in hours[1:4] if (x.get("precipitation_probability") or 0) >= WET_PROB]
        if soon:
            x = soon[0]
            return "rain", f"{base} Rain likely from around {x['hour']:02d}:00 " \
                           f"({x.get('precipitation_probability')}% chance)."
    # Sun: dry and mostly sunny for the next hours.
    nxt = hours[:3]
    if not raining_now and not any(_wet(x) for x in nxt) and \
            sum(1 for x in nxt if x.get("weather_code") in SUN_CODES) * 2 > len(nxt) and "sun" not in told:
        return "sun", f"{base} Sunny and dry for the next hours, up to {round(tmax)} °C" + \
                      (f", sunset at {sunset}." if sunset else ".")
    return None


# -- H125: a watch against the forecast (no network: the happy flow feeds it) ------------------------------

def _window(fc: dict, now: datetime, until: datetime) -> list[dict]:
    """The forecast's hours from this hour up to UNTIL, as dicts."""
    h = fc.get("hourly") or {}
    out = []
    for i, t in enumerate(h.get("time") or []):
        at = datetime.fromisoformat(t)
        if now.replace(minute=0, second=0, microsecond=0) <= at <= until:
            out.append({k: (h.get(k) or [None] * (i + 1))[i] for k in h} | {"at": at})
    return out


def _radar_at(hm: str, now: datetime) -> datetime:
    try:
        at = datetime.combine(now.date(), datetime.strptime(hm, "%H:%M").time())
    except ValueError:
        return now
    return at + timedelta(days=1) if at < now - timedelta(hours=1) else at


def check_watch(look_for: str, fc: dict, minutes: list[tuple[str, float]], now: datetime,
                until: datetime) -> tuple[str, str] | None:
    """(key, facts) when the forecast shows LOOK_FOR (rain, dry, sun, below N, above N) between now and UNTIL;
    None otherwise. The key is what was found (so the same finding isn't kept twice)."""
    hours = _window(fc, now, until)
    if not hours:
        return None
    cur = fc.get("current") or {}
    day = lambda at: "" if at.date() == now.date() else " tomorrow"
    def hhmm(x):
        return f"{x['at']:%H}:00{day(x['at'])}"
    raining_now = (minutes[0][1] >= 0.1) if minutes else _wet(hours[0]) or (cur.get("precipitation") or 0) >= WET_MM
    if look_for == "rain":
        if raining_now:
            return "rain-now", "It's raining now."
        start = next((hm for hm, mm in minutes if mm >= 0.1), "")
        if start and _radar_at(start, now) <= until:
            return f"rain-{start}", f"Rain from about {start} (by the minute from the rain radar)."
        x = next((x for x in hours[1:] if _wet(x)), None)
        if x:
            return f"rain-{x['at']:%d%H}", f"Rain likely from around {hhmm(x)} " \
                                            f"({x.get('precipitation_probability') or 0}% chance)."
        return None
    if look_for == "dry":
        if not raining_now:
            return "dry-now", "It's dry now."
        stop = next((hm for hm, mm in minutes if mm < 0.1), "")
        if stop:
            return f"dry-{stop}", f"Dry from about {stop} (by the minute from the rain radar)."
        x = next((x for x in hours[1:] if not _wet(x)), None)
        return (f"dry-{x['at']:%d%H}", f"Dry from around {hhmm(x)}.") if x else None
    if look_for == "sun":
        x = next((x for x in hours if x.get("weather_code") in SUN_CODES and not _wet(x)), None)
        if not x:
            return None
        return (f"sun-{x['at']:%d%H}", "Sunny now." if x is hours[0] and cur.get("weather_code") in SUN_CODES
                else f"Sun from around {hhmm(x)} ({WMO.get(x.get('weather_code'), 'clear')}).")
    m = re.fullmatch(r"(below|above) (-?\d+)", look_for or "")
    if m:
        n = int(m.group(2))
        hit = (lambda v: v <= n) if m.group(1) == "below" else (lambda v: v >= n)
        x = next((x for x in hours if x.get("temperature_2m") is not None and hit(x["temperature_2m"])), None)
        return (f"{look_for}-{x['at']:%d%H}", f"{round(x['temperature_2m'])} °C around {hhmm(x)} "
                f"({m.group(1)} {n} °C).") if x else None
    return None


def _hm(at: datetime, now: datetime) -> str:
    return f"{at:%H:%M}" + ("" if at.date() == now.date() else " tomorrow")


def _shower(fc: dict, minutes: list[tuple[str, float]], now: datetime,
            until: datetime) -> tuple[str, datetime | None, str]:
    """H196: where the rain stands up to UNTIL: ("now", None, ""), ("coming", when, how it's known) or
    ("dry", None, "")."""
    hours = _window(fc, now, until)
    cur = fc.get("current") or {}
    if minutes:
        if minutes[0][1] >= 0.1:
            return "now", None, ""
    elif hours and (_wet(hours[0]) or (cur.get("precipitation") or 0) >= WET_MM):
        return "now", None, ""
    start = next((hm for hm, mm in minutes if mm >= 0.1), "")
    if start and _radar_at(start, now) <= until:
        return "coming", _radar_at(start, now), "by the minute from the rain radar"
    x = next((x for x in hours[1:] if _wet(x)), None)
    if x:
        return "coming", x["at"], f"{x.get('precipitation_probability') or 0}% chance"
    return "dry", None, ""


def _stopped(fc: dict, minutes: list[tuple[str, float]], now: datetime) -> bool:
    """H196: dry now and for the next quarter of an hour by the radar (by the hour without it)."""
    if minutes:
        return all(mm < 0.1 for _, mm in minutes[:3])
    hours = _window(fc, now, now)
    return bool(hours) and not _wet(hours[0]) and ((fc.get("current") or {}).get("precipitation") or 0) < WET_MM


def follow_shower(f: dict | None, fc: dict, minutes: list[tuple[str, float]], now: datetime, first: datetime,
                  until: datetime, matters=None) -> tuple[dict | None, tuple[str, str] | None]:
    """H196: the rain alert follows one shower. F is what she said about it (None before she said anything);
    FIRST is how far ahead a new shower counts, UNTIL how far a followed one may move. Returns the new F and
    (key, facts) when there's something to text: the shower coming, coming SHIFT or more earlier or later than
    she said, gone, started well before she said, or stopped. MATTERS (H212): whether rain at a time changes
    something for him (he's out then); without it, every shower counts as before."""
    hit = matters or (lambda at: True)
    stamp = now.isoformat(timespec="minutes")
    if f and (now - datetime.fromisoformat(f.get("seen") or f["at"])).total_seconds() > FOLLOW_STALE:
        f = None  # the night in between: let it go quietly
    if not f:
        kind, at, how = _shower(fc, minutes, now, first)
        if kind != "coming" or not hit(at):
            return None, None  # nothing coming, raining already, or not while he's out: never set it off then
        return ({"phase": "coming", "at": at.isoformat(timespec="minutes"), "seen": stamp, "miss": 0},
                (f"rain-{at:%d%H%M}", f"Rain from about {_hm(at, now)} ({how})."))
    f = dict(f, seen=stamp)
    said = datetime.fromisoformat(f["at"])
    if f.get("phase") == "raining":
        if _stopped(fc, minutes, now):
            if not hit(now):
                return None, None  # stopped while he's in: nothing changes for him
            return None, (f"stop-{now:%d%H%M}", "Update on the rain you texted about: it's stopped, dry now"
                          + (" (by the minute from the rain radar)." if minutes else "."))
        return f, None
    upd = f"Update on the rain you said would come from about {_hm(said, now)}:"
    kind, at, how = _shower(fc, minutes, now, until)
    if kind == "now":
        f.update(phase="raining", miss=0)
        if (said - now).total_seconds() >= SHIFT and hit(now):
            return f, (f"early-{now:%d%H%M}", f"{upd} it's raining already, earlier than you said.")
        return f, None
    if kind == "coming":
        f["miss"] = 0
        if abs((at - said).total_seconds()) >= SHIFT:
            f["at"] = at.isoformat(timespec="minutes")
            if not (hit(said) or hit(at)):
                return f, None
            return f, (f"shift-{now:%d%H%M}", f"{upd} it now comes from about {_hm(at, now)} ({how}), "
                       f"{'earlier' if at < said else 'later'} than you said.")
        return f, None
    f["miss"] = int(f.get("miss") or 0) + 1
    if f["miss"] >= GONE_LOOKS:
        if not hit(said):
            return None, None
        return None, (f"gone-{now:%d%H%M}", f"{upd} it's gone, no rain coming in the next hours after all.")
    return f, None


def check_watches(fc: dict, minutes: list[tuple[str, float]], loc: datetime, name: str = "",
                  ws: list[dict] | None = None, keep=None, follow: dict | None = None,
                  matters=None) -> list[tuple[int, str]]:
    """Each open weather watch against this look; a match is kept for her to text (pings.match). Returns
    [(watch n, facts)] of the new ones. The rain alert (H161, `alert`): a new shower only in the next ALERT_AHEAD
    hours and not while it's raining already; then she follows it (H196, follow_shower; FOLLOW is weather.json's
    `follow`, by watch, changed in place)."""
    import pings
    ws = watches() if ws is None else ws
    follow = {} if follow is None else follow
    out = []
    for w in ws:
        try:
            until = datetime.strptime(w["until"], pings.FMT)
        except (KeyError, ValueError):
            continue
        if w.get("alert"):
            f, got = follow_shower(follow.get(str(w["n"])), fc, minutes, loc,
                                   min(until, loc + timedelta(hours=ALERT_AHEAD)),
                                   min(until, loc + timedelta(hours=2 * ALERT_AHEAD)), matters)
            if f:
                follow[str(w["n"])] = f
            else:
                follow.pop(str(w["n"]), None)
        else:
            got = check_watch(w.get("what", ""), fc, minutes, loc, until)
        if not got:
            continue
        facts = (f"Where: {name}. " if name else "") + got[1]
        if (keep or pings.match)(int(w["n"]), facts, key=got[0], answers=bool(w.get("once"))) == "new":
            out.append((int(w["n"]), facts))
    return out


# -- H212: weather texts that fit his day (no network: the happy flow feeds it) --------------------------------

SLEEP_WORDS = ("sleep", "slapen", "asleep", "bed", "bedtime", "night")  # a calendar block with this title is his night
NIGHT = (23, 8)  # without a Sleep block around: asleep from 23:00 to 08:00 (Claude's choice)
LEAVE = 60 * 60  # she looks this long before he goes out
TRAVEL = 20 * 60  # rain this long before an outing still counts: he's on his way
MORNING_LATE = 3 * 3600  # the morning text only this long after he wakes up; later the day has started without it
OUT_LOOK_EVERY = 5 * 60  # a going-out look that failed is tried again after this
DONE_KEEP = 2 * 86400  # outings she looked at, kept this long
# An appointment takes him out of the house when it has a place that isn't a link, or a title with one of these
# words (Claude's choice); not when it says it's by phone or online.
OUT_WORDS = ("outside", "walk", "gym", "haircut", "kapper", "barber", "dentist", "tandarts", "doctor", "dokter",
             "huisarts", "afspraak", "library", "bibliotheek", "station", "shop", "shopping", "groceries",
             "boodschappen", "market", "markt", "pick up", "ophalen", "visit", "bij", "run", "running", "bike",
             "fietsen", "park", "cafe", "café", "restaurant", "swim", "zwemmen", "train", "trip", "airport", "return")
HOME_WORDS = ("telefonisch", "phone", "call", "online", "zoom", "bellen", "video", "teams")


def _cal(evs: list[dict] | None = None) -> list[dict]:
    """His calendar as HQ last read it (calendar.json, through pings), no network."""
    if evs is not None:
        return evs
    try:
        import pings
        return pings.events()
    except Exception:
        return []


def _own_outs() -> list[dict]:
    """His own times out from her list (pings.py out)."""
    try:
        import pings
        return pings.read().get("outs") or []
    except Exception:
        return []


def _naive(iso: str, tz: str) -> datetime | None:
    """A calendar time as a plain local time where he is."""
    try:
        d = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None
    if d.tzinfo:
        from zoneinfo import ZoneInfo
        try:
            d = d.astimezone(ZoneInfo(tz))
        except Exception:
            d = d.astimezone()
        d = d.replace(tzinfo=None)
    return d


def _is_sleep(e: dict) -> bool:
    t = (e.get("title") or "").strip().lower()
    return not e.get("all_day") and (t in SLEEP_WORDS or t.split(" ")[0] in ("sleep", "slapen"))


def sleeps(evs: list[dict], tz: str) -> list[tuple[datetime, datetime]]:
    out = []
    for e in evs:
        if _is_sleep(e):
            a, b = _naive(e.get("start", ""), tz), _naive(e.get("end", ""), tz)
            if a and b and b > a:
                out.append((a, b))
    return out


def asleep(loc: datetime, evs: list[dict], tz: str) -> bool:
    """H212: inside a Sleep block of his calendar; when the calendar has none around this night, the NIGHT hours."""
    near = [x for x in sleeps(evs, tz) if x[0] - timedelta(hours=18) <= loc <= x[1] + timedelta(hours=18)]
    if near:
        return any(a <= loc < b for a, b in near)
    return loc.hour >= NIGHT[0] or loc.hour < NIGHT[1]


def woke(loc: datetime, evs: list[dict], tz: str) -> datetime:
    """When he wakes up today: the end of the Sleep block that ends today, else NIGHT's end."""
    ends = [b for a, b in sleeps(evs, tz) if b.date() == loc.date()]
    return min(ends) if ends else loc.replace(hour=NIGHT[1], minute=0, second=0, microsecond=0)


def _out_event(e: dict) -> bool:
    if e.get("all_day") or e.get("free") or _is_sleep(e):
        return False
    title = (e.get("title") or "").lower()
    if any(re.search(rf"\b{re.escape(w)}\b", title) for w in HOME_WORDS):
        return False
    where = (e.get("where") or "").strip().lower()
    if where and not re.match(r"(https?://|www\.)", where) and not any(w in where for w in ("zoom", "meet.google", "teams")):
        return True
    return any(re.search(rf"\b{re.escape(w)}\b", title) for w in OUT_WORDS)


def _at(day: datetime, hm: str) -> datetime:
    h, m = (int(x) for x in hm.split(":"))
    return day + timedelta(hours=h, minutes=m)


def outings(day, evs: list[dict], outs: list[dict], tz: str) -> list[dict]:
    """H212: his times out on DAY: his calendar's appointments away from home (_out_event) and his own times (her
    list, pings.py out), each {key, what, start, end, own}, by start."""
    d0 = datetime.combine(day, datetime.min.time())
    d1 = d0 + timedelta(days=1)
    out = []
    for e in evs:
        if not _out_event(e):
            continue
        a, b = _naive(e.get("start", ""), tz), _naive(e.get("end", ""), tz)
        if a and b and b > d0 and a < d1:
            out.append({"key": f"cal-{e.get('id')}-{day:%m%d}", "what": e.get("title") or "an appointment",
                        "start": max(a, d0), "end": min(b, d1), "own": False})
    for o in outs:
        if o.get("daily") or o.get("on") == day.isoformat():
            try:
                out.append({"key": f"own-{o['n']}-{day:%m%d}", "what": "the hours he said he's out",
                            "start": _at(d0, o["from"]), "end": _at(d0, o["to"]), "own": True})
            except (KeyError, ValueError):
                continue
    return sorted(out, key=lambda x: x["start"])


def rain_between(fc: dict, minutes: list[tuple[str, float]], now: datetime, a: datetime,
                 b: datetime) -> tuple[datetime, str] | None:
    """H212: the first rain between A and B (from now on): by the radar's five minutes as far as it reaches, by the
    hour after that. (when, how it's known), or None when it stays dry."""
    a = max(a, now)
    if b <= a:
        return None
    reach = None
    for hm, mm in minutes:
        at = _radar_at(hm, now)
        reach = at
        if mm >= 0.1 and a - timedelta(minutes=5) < at <= b:
            return max(at, a), "by the minute from the rain radar"
    for x in _window(fc, now, b):
        end = x["at"] + timedelta(hours=1)
        if reach and end <= reach + timedelta(minutes=5):
            continue  # the radar already said
        if end > a and _wet(x):
            return max(x["at"], a), f"{x.get('precipitation_probability') or 0}% chance"
    return None


def _span(o: dict) -> str:
    return f"{o['what']} ({o['start']:%H:%M} to {o['end']:%H:%M})"


def morning(fc: dict, minutes: list[tuple[str, float]], loc: datetime, outs: list[dict],
            name: str = "") -> tuple[str, str]:
    """H212: on waking, one thing only: will it rain when he's out today, yes or no. Without times out, whether it
    rains in the rest of his day."""
    head = (f"Where: {name}. " if name else "") + "He just woke up; this is his only weather text this morning. "
    ahead = [o for o in outs if o["end"] > loc]
    if ahead:
        hit = next(((o, r) for o in ahead
                    if (r := rain_between(fc, minutes, loc, o["start"] - timedelta(seconds=TRAVEL), o["end"]))), None)
        plan = "; ".join(_span(o) for o in ahead)
        if hit:
            o, (at, how) = hit
            return "morning", f"{head}He's out today: {plan}. Rain while he's out: yes, from about {at:%H:%M} " \
                              f"({how}), around {o['what']}."
        return "morning", f"{head}He's out today: {plan}. Rain while he's out: no, it stays dry then."
    r = rain_between(fc, minutes, loc, loc, loc.replace(hour=DAY[1], minute=0, second=0, microsecond=0))
    return "morning", f"{head}Nothing in his day takes him out yet. Rain today: " + \
        (f"yes, from about {r[0]:%H:%M} ({r[1]})." if r else "no, it stays dry.")


def going_out(fc: dict, minutes: list[tuple[str, float]], loc: datetime, outs: list[dict],
              done: dict) -> list[tuple[dict, str | None, tuple[datetime, str] | None]]:
    """H212: each outing starting within LEAVE (or under way) that she hasn't looked at yet: (outing, facts or None
    when it stays dry then, the rain). She texts only the ones with facts."""
    out = []
    for o in outs:
        if o["key"] in done or not (o["start"] - timedelta(seconds=LEAVE) <= loc < o["end"]):
            continue
        r = rain_between(fc, minutes, loc, o["start"] - timedelta(seconds=TRAVEL), o["end"])
        facts = None
        if r:
            at, how = r
            now_wet = at <= loc + timedelta(minutes=5)
            facts = (f"He's {'out now' if o['start'] <= loc else 'going out soon'}: {_span(o)}"
                     + (" (the hours he gave you)" if o["own"] else " (his calendar)") + ". "
                     + ("It's raining now." if now_wet else f"Rain from about {at:%H:%M} ({how}), while he's out."))
        out.append((o, facts, r))
    return out


def _loc(now: float, s: dict) -> tuple[datetime, str]:
    """Now where he is, as a plain local time, and its time zone."""
    w = here(s, now) or s.get("where") or {}
    tz = (w.get("tz") or "") if (w.get("gps") or w.get("place") == place()) else ""
    return local_now(tz, now).replace(tzinfo=None), tz


def outings_now(now: float | None = None, evs: list[dict] | None = None) -> tuple[datetime, list[dict]]:
    """H239: now where he is (a plain local time) and today's times away from home, for the six-week game's texts."""
    now = now or time.time()
    loc, tz = _loc(now, _read())
    return loc, outings(loc.date(), _cal(evs), _own_outs(), tz)


def asleep_at(now: float | None = None, s: dict | None = None, evs: list[dict] | None = None) -> bool:
    """H212: he's asleep now (for pings: a weather watch ending at night ends quietly)."""
    now = now or time.time()
    s = _read() if s is None else s
    loc, tz = _loc(now, s)
    return asleep(loc, _cal(evs), tz)


def morning_due(now: float | None = None, s: dict | None = None, evs: list[dict] | None = None) -> bool:
    """H212: he's up, the morning text hasn't gone yet today, and he woke up under MORNING_LATE ago."""
    if not on():
        return False
    now = now or time.time()
    s = _read() if s is None else s
    if not _somewhere(s, now):
        return False
    loc, tz = _loc(now, s)
    evs = _cal(evs)
    w0 = woke(loc, evs, tz)
    return (not asleep(loc, evs, tz) and w0 <= loc < w0 + timedelta(seconds=MORNING_LATE)
            and now - float(s.get("general") or 0) >= OUT_LOOK_EVERY - 30  # a failed look isn't retried every minute
            and "morning" not in ((s.get("told") or {}).get(f"{loc:%Y-%m-%d}") or []))


def out_due(now: float | None = None, s: dict | None = None, evs: list[dict] | None = None) -> bool:
    """H212: he's about to go out (or is out) and she hasn't looked at that outing yet."""
    if not on():
        return False
    now = now or time.time()
    s = _read() if s is None else s
    if not _somewhere(s, now) or now - float(s.get("looked") or 0) < OUT_LOOK_EVERY - 30:
        return False
    loc, tz = _loc(now, s)
    evs = _cal(evs)
    if asleep(loc, evs, tz):
        return False
    done = s.get("outs_done") or {}
    return any(o["key"] not in done and o["start"] - timedelta(seconds=LEAVE) <= loc < o["end"]
               for o in outings(loc.date(), evs, _own_outs(), tz))


# -- the look ----------------------------------------------------------------------------------------

def look(dry: bool = False, now: float | None = None, general: bool | None = None) -> tuple[str, str] | None:
    """The look: her three-hourly text when GENERAL (default: when that one is due, or always on a dry run), and
    the open weather watches (H125) each time."""
    s = _read()
    now = now or time.time()
    general = (dry or general_due(now, s) or not watches(now)) if general is None else general
    if not dry:
        s["looked"] = now
        if general:
            s["general"] = now
    w = here(s, now) or where(s)  # H161: the phone's last spot while it's fresh
    if not w:
        if not dry:
            _write(s)
        return None
    loc = local_now(w["tz"], now)
    today = loc.strftime("%Y-%m-%d")
    told = (s.get("told") or {}).get(today) or []
    fc, minutes = forecast(w), rain_text(w)
    name = w.get("name") or ("" if w.get("gps") else w["place"])
    # H212: his day: asleep, waking up, and his times out (his calendar and the times he gave her)
    ln = loc.replace(tzinfo=None)
    evs = _cal()
    outs = outings(ln.date(), evs, _own_outs(), w["tz"])
    ahead = [o for o in outs if o["end"] > ln]
    matters = lambda at: any(o["start"] - timedelta(seconds=TRAVEL) <= at <= o["end"] for o in ahead)
    wake = woke(ln, evs, w["tz"])
    first = general and "morning" not in told and wake <= ln < wake + timedelta(seconds=MORNING_LATE) \
        and not asleep(ln, evs, w["tz"])
    if first:
        got = morning(fc, minutes, ln, outs, name)
    else:
        got = decide(fc, minutes, ln, told, name) if general else None
        if got and got[0] == "rain":
            got = None  # H212: rain is said only when it changes something for him: going out, or his own times
    if dry:
        return got
    texts = [got] if got else []
    ws = watches(now)
    alerts = {str(x["n"]) for x in ws if x.get("alert")}
    follow = {k: v for k, v in (s.get("follow") or {}).items() if k in alerts}
    done = {k: v for k, v in (s.get("outs_done") or {}).items() if now - float(v) < DONE_KEEP}
    stamp = ln.isoformat(timespec="minutes")
    for o, facts, r in going_out(fc, minutes, ln, outs, done):
        done[o["key"]] = now
        if facts and not first:  # on waking, the morning text already said it
            texts.append(("out", (f"Where: {name}. " if name else "") + facts))
        if r and alerts and not any(follow.get(k) for k in alerts):  # the rain alert follows that shower from here
            raining = r[0] <= ln + timedelta(minutes=5)
            follow[sorted(alerts)[0]] = {"phase": "raining" if raining else "coming", "at": r[0].isoformat(timespec="minutes"),
                                        "seen": stamp, "miss": 0}
    for n, facts in check_watches(fc, minutes, ln, name, ws=ws, follow=follow, matters=matters):
        print(time.strftime("%Y-%m-%d %H:%M:%S"), f"weather: a match for watch {n}: {facts}")
    if got:
        s["told"] = {today: told + [got[0]]}
    s["follow"] = follow
    s["outs_done"] = done
    _write(s)
    if texts:
        import direct_line
        for why, facts in texts:
            direct_line.text(why, facts)
    return got


def start(now: float | None = None) -> bool:
    """From tick.py, every minute on the main: when a look is due, note it and run it detached (the network and
    her text can take a while). True when one was started."""
    s = _read()
    if not due(now, s):
        return False
    general = general_due(now, s) or morning_due(now, s)
    s["looked"] = now or time.time()
    if general:
        s["general"] = s["looked"]
    _write(s)
    py = ROOT / ".venv" / "bin" / "python"
    log = ROOT / "scratch" / "direct-line.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([str(py) if py.exists() else sys.executable, str(Path(__file__).resolve()), "look"]
                     + (["--general"] if general else ["--watches"]),
                     cwd=str(ROOT), stdout=open(log, "a"), stderr=subprocess.STDOUT, start_new_session=True)
    return True


# -- H135: the weather in the app ------------------------------------------------------------------------

APP_EVERY = 15 * 60  # the app's weather is read again when it's older than this
WARN_FROM = 2  # MeteoAlarm's awareness levels: 1 green, 2 yellow, 3 orange, 4 red; shown from yellow
LEVELS = {1: "green", 2: "yellow", 3: "orange", 4: "red"}
# MeteoAlarm's feeds by country (the feed's name); elsewhere the app says there's no warnings feed for the place.
METEOALARM = {"NL": "netherlands", "BE": "belgium", "DE": "germany", "FR": "france", "LU": "luxembourg",
              "GB": "united-kingdom", "IE": "ireland", "ES": "spain", "PT": "portugal", "IT": "italy",
              "AT": "austria", "CH": "switzerland", "DK": "denmark", "NO": "norway", "SE": "sweden",
              "FI": "finland", "EE": "estonia", "LV": "latvia", "LT": "lithuania", "PL": "poland",
              "CZ": "czechia", "SK": "slovakia", "HU": "hungary", "SI": "slovenia", "HR": "croatia",
              "GR": "greece", "CY": "cyprus", "MT": "malta", "RO": "romania", "BG": "bulgaria", "RS": "serbia",
              "IS": "iceland", "ME": "montenegro", "MK": "republic-of-north-macedonia", "BA": "bosnia-herzegovina",
              "IL": "israel", "MD": "moldova", "UA": "ukraine"}
# The names geocoding gives a region in English where the warnings use the local one.
REGION_WORDS = {"north": "noord", "south": "zuid", "frisia": "friesland", "fryslan": "friesland"}
WIND_DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def app_forecast(w: dict) -> dict:
    q = urllib.parse.urlencode({
        "latitude": w["lat"], "longitude": w["lon"], "timezone": w.get("tz") or "auto", "forecast_days": 2,
        "current": "temperature_2m,apparent_temperature,precipitation,weather_code,is_day,wind_speed_10m,"
                   "wind_gusts_10m,wind_direction_10m,uv_index",
        "hourly": "temperature_2m,precipitation,precipitation_probability,weather_code,uv_index,wind_speed_10m,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
                 "precipitation_probability_max,uv_index_max,sunrise,sunset,wind_speed_10m_max,wind_gusts_10m_max"})
    return json.loads(_get(f"https://api.open-meteo.com/v1/forecast?{q}"))


def _norm(t: str) -> str:
    words = re.findall(r"[a-z]+", (t or "").lower().replace("â", "a"))
    return "".join(REGION_WORDS.get(x, x) for x in words)


def _level(info: dict) -> int:
    for p in info.get("parameter") or []:
        if p.get("valueName") == "awareness_level":
            try:
                return int(str(p.get("value")).split(";")[0])
            except ValueError:
                return 0
    return 0


def parse_warnings(feed: dict, w: dict, now: datetime) -> list[dict]:
    """The warnings from a MeteoAlarm feed that cover the place's region (or the place itself), yellow and up, not
    over yet; English where the feed has it. One per kind of weather, the highest level first. No network."""
    areas = {_norm(w.get("region") or ""), _norm(w.get("name") or "")} - {""}
    out = {}
    for x in (feed or {}).get("warnings") or []:
        alert = x.get("alert") or {}
        if alert.get("msgType") == "Cancel" or alert.get("status") not in (None, "Actual"):
            continue
        infos = alert.get("info") or []
        info = next((i for i in infos if str(i.get("language", "")).startswith("en")), infos[0] if infos else None)
        if not info or _level(info) < WARN_FROM:
            continue
        hit = [a.get("areaDesc", "") for a in info.get("area") or [] if _norm(a.get("areaDesc", "")) in areas]
        if not hit:
            continue
        try:
            ends = datetime.fromisoformat(info["expires"])
            if ends.tzinfo:
                ends = ends.astimezone(now.tzinfo).replace(tzinfo=None) if now.tzinfo else ends.replace(tzinfo=None)
            if ends <= now.replace(tzinfo=None):
                continue
        except (KeyError, ValueError):
            pass
        lvl = _level(info)
        kind = next((p.get("value", "") for p in info.get("parameter") or [] if p.get("valueName") == "awareness_type"), "")
        kind = kind.split(";")[-1].strip() or info.get("event", "")
        one = {"level": LEVELS.get(lvl, str(lvl)), "n": lvl, "what": kind, "event": info.get("event", ""),
               "headline": info.get("headline", ""), "text": (info.get("description") or "").strip(),
               "from": info.get("onset") or info.get("effective") or "", "until": info.get("expires", ""),
               "area": hit[0], "by": info.get("senderName", ""), "web": info.get("web", "")}
        k = (kind.lower(), one["from"][:13])
        if k not in out or out[k]["n"] < lvl:
            out[k] = one
    return sorted(out.values(), key=lambda o: (-o["n"], o["from"]))


def warnings(w: dict, now: datetime) -> tuple[list[dict], str]:
    """(warnings, the source's name or why there are none to read)."""
    slug = METEOALARM.get(w.get("country") or "")
    if not slug:
        return [], "no warnings feed for this country"
    feed = json.loads(_get(f"https://feeds.meteoalarm.org/api/v1/warnings/feeds-{slug}", timeout=20))
    return parse_warnings(feed, w, now), "KNMI" if w.get("country") == "NL" else "MeteoAlarm"


def uv_word(uv) -> str:
    if uv is None:
        return ""
    uv = float(uv)
    return "low" if uv < 3 else "moderate" if uv < 6 else "high" if uv < 8 else "very high" if uv < 11 else "extreme"


def beaufort(kmh) -> int:
    if kmh is None:
        return 0
    for b, top in enumerate([1, 6, 12, 20, 29, 39, 50, 62, 75, 89, 103, 118]):
        if kmh < top:
            return b
    return 12


def icon(code, day: bool = True) -> str:
    """One word for the page's picture: sun, moon, partly, cloud, fog, drizzle, rain, snow, storm."""
    if code in (0, 1):
        return "sun" if day else "moon"
    if code == 2:
        return "partly" if day else "cloud"
    return {3: "cloud", 45: "fog", 48: "fog"}.get(code) or ("drizzle" if code in (51, 53, 55, 56, 57) else
            "snow" if code in (71, 73, 75, 77, 85, 86) else "storm" if code in (95, 96, 99) else
            "rain" if code is not None else "cloud")


def build_view(fc: dict, minutes: list[tuple[str, float]], warns: list[dict], now: datetime, name: str = "",
               warn_source: str = "") -> dict:
    """What the app shows, from the forecast, the radar and the warnings. No network: the happy flow feeds it."""
    cur = fc.get("current") or {}
    h = fc.get("hourly") or {}
    hours = []
    for i, t in enumerate(h.get("time") or []):
        at = datetime.fromisoformat(t)
        if at < now.replace(minute=0, second=0, microsecond=0) or len(hours) >= 12:
            continue
        x = {k: (h.get(k) or [None] * (i + 1))[i] for k in h}
        hours.append({"at": at.strftime("%H:%M"), "temp": x.get("temperature_2m"),
                      "chance": x.get("precipitation_probability"), "mm": x.get("precipitation"),
                      "uv": x.get("uv_index"), "icon": icon(x.get("weather_code"), bool(x.get("is_day", 1))),
                      "text": WMO.get(x.get("weather_code"), "")})
    code, day_now = cur.get("weather_code"), bool(cur.get("is_day", 1))
    nxt = hours[:3]
    chance = max([x["chance"] or 0 for x in nxt] or [0])
    raining = (minutes[0][1] >= 0.1) if minutes else (cur.get("precipitation") or 0) >= 0.1
    wind = cur.get("wind_speed_10m")
    d = fc.get("daily") or {}
    def daily(i):
        g = lambda k: ((d.get(k) or []) + [None, None])[i]
        if not (d.get("time") or [])[i:i + 1]:
            return None
        return {"date": d["time"][i], "text": WMO.get(g("weather_code"), ""), "icon": icon(g("weather_code")),
                "max": g("temperature_2m_max"), "min": g("temperature_2m_min"), "mm": g("precipitation_sum"),
                "chance": g("precipitation_probability_max"), "uv": g("uv_index_max"), "uv_word": uv_word(g("uv_index_max")),
                "sunrise": (g("sunrise") or "")[11:16], "sunset": (g("sunset") or "")[11:16],
                "wind": g("wind_speed_10m_max"), "gusts": g("wind_gusts_10m_max")}
    if minutes:
        wet = [hm for hm, mm in minutes if mm >= 0.1]
        if raining:
            stop = next((hm for hm, mm in minutes if mm < 0.1), "")
            radar = f"Raining now, dry from about {stop}" if stop else "Raining for the next two hours"
        else:
            radar = f"Rain from about {wet[0]}" if wet else "Dry for the next two hours"
    else:
        radar = ""
    sunny = code in SUN_CODES and day_now and not raining
    return {"place": name, "now": {
        "temp": cur.get("temperature_2m"), "feels": cur.get("apparent_temperature"), "code": code,
        "text": WMO.get(code, ""), "icon": icon(code, day_now), "sunny": sunny, "day": day_now, "raining": raining,
        "chance": chance, "wind": wind, "gusts": cur.get("wind_gusts_10m"), "bft": beaufort(wind),
        "dir": WIND_DIRS[round((cur.get("wind_direction_10m") or 0) / 45) % 8] if wind is not None else "",
        "uv": cur.get("uv_index"), "uv_word": uv_word(cur.get("uv_index"))},
        "today": daily(0), "tomorrow": daily(1), "hours": hours, "radar": radar,
        "minutes": [{"at": hm, "mm": mm} for hm, mm in minutes], "warnings": warns, "warn_source": warn_source}


def view(fresh: bool = False, now: float | None = None, gps=None) -> dict:
    """What the app shows (H135): the last read, read again first when FRESH and it's over 15 minutes old. Says so
    plainly when HQ has no place for him, or the weather is off. GPS (H161): the phone's (lat, lon) when he allows
    it; then that spot, else me.md's place. `alert` says whether the rain alert is on, `home` is me.md's place."""
    if not on():
        return {"off": "The weather is off on this HQ."}
    name, g = place(), _gps(gps) if gps else None
    if not name and not g:
        return {"off": "No place set yet. Tell me where you are (Where I am, in me.md), or allow your location, "
                       "and the weather shows here.", "alert": alert_state()}
    key = gps_key(g) if g else name
    s = _read()
    got = s.get("app") or {}
    now = now or time.time()
    if got.get("for") != key:
        got = {}
    if fresh and (not got or now - float(got.get("looked") or 0) >= APP_EVERY - 30):
        try:
            w = here_place(g, s, now) if g else where(s, region=True)
            if not w:
                raise ValueError(f"couldn't find {name}")
            fc = app_forecast(w)
            if g:
                w["tz"] = fc.get("timezone") or w.get("tz") or "UTC"
            loc = local_now(w["tz"], now).replace(tzinfo=None)
            try:
                minutes = rain_text(w)
            except Exception:
                minutes = []
            try:
                warns, source = warnings(w, loc)
            except Exception:
                warns, source = [], "the warnings couldn't be read just now"
            got = build_view(fc, minutes, warns, loc, w.get("name") or ("Your location" if g else name), source) \
                | {"looked": now, "for": key, "gps": bool(g)}
            # the look may have written meanwhile
            s = _read() | {k: s.get(k) for k in ("where", "spots", "here") if s.get(k)} | {"app": got}
            _write(s)
        except Exception as e:
            got = dict(got) | {"error": str(e)[:200]}
    elif g and got:  # the same spot read a moment ago: it's still where he is
        s["here"] = {"key": key, "at": now}
        _write(_read() | {"here": s["here"]})
    out = got | {"for": key} if got else {"for": key, "looked": None, "gps": bool(g)}
    return out | {"home": name, "alert": alert_state()}


# -- H161: the rain alert switch -------------------------------------------------------------------------------

def alert_state() -> dict:
    """Whether the rain alert is on: an open weather watch for rain marked `alert` on her list."""
    try:
        import pings
        w = next((w for w in pings.open_watches("weather") if w.get("alert")), None)
    except Exception:
        return {"on": False}
    return {"on": bool(w), "n": int(w["n"]) if w else None}


def rain_alert(want: bool) -> dict:
    """The switch in the weather sheet: on opens a lasting rain watch (ALERT_YEARS, so it's simply on, H188; every
    match texted as she follows the shower, H196), off ends it without a text (he switched it himself)."""
    import pings
    cur = [w for w in pings.open_watches("weather") if w.get("alert")]
    if want and not cur:
        pings.watch_add("weather", "rain", until=datetime.now().replace(second=0, microsecond=0) + timedelta(days=round(365.25 * ALERT_YEARS)),
                        once=False, by="the rain alert in the app", alert=True)
    elif not want:
        for w in cur:
            pings.unwatch(int(w["n"]), quiet=True)
    return alert_state()


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    if cmd == "status":
        s = _read()
        print(json.dumps({"on": on(), "place": place(), "where": s.get("where"), "looked": s.get("looked"),
                          "due": due(s=s), "watches": [w["what"] for w in watches()], "told": s.get("told")},
                         ensure_ascii=False))
    elif cmd == "look":
        try:
            print(json.dumps(look(dry="--dry" in args, general=True if "--general" in args else False if "--watches" in args else None),
                             ensure_ascii=False))
        except (OSError, ValueError) as e:  # H162: the weather service busy (a 503) is one line, not a traceback
            print(time.strftime("%Y-%m-%d %H:%M:%S"), f"weather: the look couldn't read the weather ({e}); the next one as planned")
            sys.exit(1)
    elif cmd == "view":
        print(json.dumps(view(fresh="--fresh" in args), ensure_ascii=False, indent=1))
    elif cmd == "alert":
        print(json.dumps(rain_alert(args[1] == "on") if args[1:2] in (["on"], ["off"]) else alert_state()))
    else:
        print(__doc__)
        sys.exit(2)
