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

Kept in the direct line's folder (synced, off GitHub): weather.json, the last look, the place's coordinates and
what she already said today. Off: HQ_WEATHER=0. HQ_WEATHER_PLACE overrides the place (tests).

  python3 app/weather.py status            the place, the last look, whether a look is due
  .venv/bin/python app/weather.py look     look now and text if there's something worth saying
  python3 app/weather.py look --dry        what she would text now, without texting
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


def on() -> bool:
    return os.environ.get("HQ_WEATHER", "1") != "0" and os.environ.get("HQ_DIRECT", "1") != "0"


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


def where(s: dict | None = None) -> dict | None:
    """The place's coordinates, its time zone and country, looked up once (Open-Meteo's geocoding) and kept."""
    name = place()
    if not name:
        return None
    s = _read() if s is None else s
    got = s.get("where") or {}
    if got.get("place") == name and "lat" in got:
        return got
    q = urllib.parse.urlencode({"name": name.split(",")[0].strip(), "count": 1, "language": "en"})
    res = (json.loads(_get(f"https://geocoding-api.open-meteo.com/v1/search?{q}")).get("results") or [None])[0]
    if not res:
        return None
    got = {"place": name, "lat": res["latitude"], "lon": res["longitude"], "tz": res.get("timezone") or "UTC",
           "country": res.get("country_code") or "", "name": res.get("name") or name}
    s["where"] = got
    return got


def local_now(tz: str, now: float | None = None) -> datetime:
    from zoneinfo import ZoneInfo
    try:
        return datetime.fromtimestamp(now or time.time(), ZoneInfo(tz))
    except Exception:
        return datetime.fromtimestamp(now or time.time())


def _hour(now: float, s: dict) -> int:
    w = s.get("where") or {}
    return local_now(w.get("tz") or "", now).hour if w.get("place") == place() else datetime.fromtimestamp(now).hour


def general_due(now: float | None = None, s: dict | None = None) -> bool:
    """The three-hourly look (its sun, rain and cosy texts): in the day where the user is, three hours since the
    last one. Cheap and offline (the time zone comes from the kept coordinates; before the first look, this
    computer's)."""
    if not on() or not place():
        return False
    now = now or time.time()
    s = _read() if s is None else s
    if not (DAY[0] <= _hour(now, s) < DAY[1]):
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
    """H125: a weather watch is open and 30 minutes have passed since the last look (07:00 to 23:00)."""
    if not on() or not place():
        return False
    now = now or time.time()
    s = _read() if s is None else s
    if not (WATCH_DAY[0] <= _hour(now, s) < WATCH_DAY[1]) or not watches(now):
        return False
    return now - float(s.get("looked") or 0) >= WATCH_EVERY - 60


def due(now: float | None = None, s: dict | None = None) -> bool:
    """A look is due: the three-hourly one, or the 30-minute one while a weather watch is open."""
    s = _read() if s is None else s
    return general_due(now, s) or watch_due(now, s)


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


def check_watches(fc: dict, minutes: list[tuple[str, float]], loc: datetime, name: str = "",
                  ws: list[dict] | None = None, keep=None) -> list[tuple[int, str]]:
    """Each open weather watch against this look; a match is kept for her to text (pings.match). Returns
    [(watch n, facts)] of the new ones."""
    import pings
    ws = watches() if ws is None else ws
    out = []
    for w in ws:
        try:
            until = datetime.strptime(w["until"], pings.FMT)
        except (KeyError, ValueError):
            continue
        got = check_watch(w.get("what", ""), fc, minutes, loc, until)
        if not got:
            continue
        facts = (f"Where: {name}. " if name else "") + got[1]
        if (keep or pings.match)(int(w["n"]), facts, key=got[0], answers=bool(w.get("once"))) == "new":
            out.append((int(w["n"]), facts))
    return out


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
    w = where(s)
    if not w:
        if not dry:
            _write(s)
        return None
    loc = local_now(w["tz"], now)
    today = loc.strftime("%Y-%m-%d")
    told = (s.get("told") or {}).get(today) or []
    fc, minutes = forecast(w), rain_text(w)
    name = w.get("name") or w["place"]
    if not dry:
        for n, facts in check_watches(fc, minutes, loc.replace(tzinfo=None), name):
            print(time.strftime("%Y-%m-%d %H:%M:%S"), f"weather: a match for watch {n}: {facts}")
    got = decide(fc, minutes, loc.replace(tzinfo=None), told, name) if general else None
    if dry:
        return got
    if got:
        s["told"] = {today: told + [got[0]]}
    _write(s)
    if got:
        import direct_line
        direct_line.text(got[0], got[1])
    return got


def start(now: float | None = None) -> bool:
    """From tick.py, every minute on the main: when a look is due, note it and run it detached (the network and
    her text can take a while). True when one was started."""
    s = _read()
    if not due(now, s):
        return False
    general = general_due(now, s)
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


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    if cmd == "status":
        s = _read()
        print(json.dumps({"on": on(), "place": place(), "where": s.get("where"), "looked": s.get("looked"),
                          "due": due(s=s), "watches": [w["what"] for w in watches()], "told": s.get("told")},
                         ensure_ascii=False))
    elif cmd == "look":
        print(json.dumps(look(dry="--dry" in args, general=True if "--general" in args else False if "--watches" in args else None),
                         ensure_ascii=False))
    else:
        print(__doc__)
        sys.exit(2)
