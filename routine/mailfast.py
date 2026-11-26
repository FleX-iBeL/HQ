#!/usr/bin/env python3
"""H149 (16 October 2026): the mail check every 15 minutes for a while he names, then hourly again by itself.

In his words (call at 09:10): "Six hours or something or whatever hours we declare. ... Or it can even be like
days, right, until the end of the week or whatever. We need to keep it humanized. ... and have the routine as well
that after a certain period of time it jumps back to once an hour."

Built on H148's switch in routine/tick.py. The window is kept on the roadmap's queue section, on the
**Mail check:** line (jobs.py mail-fast / mail-hourly), so both HQs, the routine and the status page read the
same place. This file only turns his words into an end time, and says it back in plain words.

Words it takes (the call or Donna turns his own words into one of these and says the time back):
  6 hours · 90 minutes · 2 days · an hour · half an hour       from now
  20:00 · 8pm · 8:30 pm                                           the next time the clock says that
  tonight · this evening                                          22:00 today
  tomorrow · tomorrow 18:00                                       22:00 (or the time) tomorrow
  friday · friday 18:00 · until friday                            22:00 (or the time) on the next Friday (today counts)
  end of the week · weekend                                       22:00 on Sunday
  2026-10-18 · 2026-10-18 14:00                                   that day (22:00) or that time
A day without a time ends at DAY_END, the evening, as H148's test did (Claude's choice). At most MAX_DAYS ahead
(a week every 15 minutes is about 12 to 15 points of the weekly limit, H148's result), at least one quarter.
"""
import re, sys, time
from datetime import datetime, timedelta

FAST = 900
DAY_END = 22  # a day named without a time ends at 22:00
MAX_DAYS = 7
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
UNITS = {"m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60, "h": 3600, "hr": 3600, "hrs": 3600,
         "hour": 3600, "hours": 3600, "d": 86400, "day": 86400, "days": 86400,
         "w": 604800, "week": 604800, "weeks": 604800}


def _clock(s):
    """(hour, minute) from '20:00', '20.00', '8pm', '8:30 pm', '20' with am/pm, or None."""
    m = re.fullmatch(r"(\d{1,2})(?:[:.](\d\d))?\s*(am|pm|a\.m\.|p\.m\.)?", s.strip())
    if not m or (m.group(2) is None and m.group(3) is None):
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").replace(".", "")
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    return (h, mi) if h < 24 and mi < 60 else None


def parse(words, now=None):
    """The end of the quick window as epoch seconds, from his words; ValueError (in plain words) when it can't."""
    now = time.time() if now is None else now
    base = datetime.fromtimestamp(now)
    s = re.sub(r"\s+", " ", words.strip().lower()).strip(" .!")
    s = re.sub(r"^(for the next|for the|for|until|till|til|up to|to|through)\s+", "", s)
    s = re.sub(r"^(the )?next\s+(?=\d|an? |half)", "", s)
    s = re.sub(r"^(this|next|coming|on)\s+(?=" + "|".join(DAYS) + ")", "", s)
    s = s.replace(" o'clock", "").replace(" at ", " ")
    end = None
    if s in ("an hour", "one hour", "a hour"):
        end = now + 3600
    elif s in ("half an hour", "half hour", "30 minutes"):
        end = now + 1800
    elif m := re.fullmatch(r"(\d+(?:\.\d+)?|a|an|one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s*([a-z]+)", s):
        n = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
             "nine": 9, "ten": 10, "twelve": 12}.get(m.group(1))
        unit = UNITS.get(m.group(2))
        if unit:
            end = now + (n if n is not None else float(m.group(1))) * unit
    if end is None and s in ("tonight", "this evening", "the evening", "this afternoon and evening", "today"):
        end = base.replace(hour=DAY_END, minute=0, second=0, microsecond=0).timestamp()
    if end is None and s in ("end of the week", "the end of the week", "end of week", "weekend", "the weekend",
                             "the end of this week", "end of this week", "sunday night"):
        d = base + timedelta(days=(6 - base.weekday()))
        end = d.replace(hour=DAY_END, minute=0, second=0, microsecond=0).timestamp()
    if end is None:
        day, rest = None, s
        m = re.match(r"(tomorrow|today|tonight|" + "|".join(DAYS) + r"|\d{4}-\d\d-\d\d)\b\s*(.*)$", s)
        if m:
            w, rest = m.group(1), m.group(2).strip()
            if w in ("today", "tonight"):
                day = base
            elif w == "tomorrow":
                day = base + timedelta(days=1)
            elif w in DAYS:
                day = base + timedelta(days=(DAYS.index(w) - base.weekday()) % 7)
            else:
                day = datetime.strptime(w, "%Y-%m-%d")
        hm = _clock(rest) if rest else None
        if rest and hm is None:
            raise ValueError(f"I can't read a time in '{words}'. Say it like 6 hours, 20:00, tonight, Friday or end of the week.")
        if day is None and hm is None:
            raise ValueError(f"I can't read a time in '{words}'. Say it like 6 hours, 20:00, tonight, Friday or end of the week.")
        if day is None:  # only a clock time: the next time it says that
            t = base.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
            if t.timestamp() <= now:
                t += timedelta(days=1)
            end = t.timestamp()
        else:
            h, mi = hm or (DAY_END, 0)
            end = day.replace(hour=h, minute=mi, second=0, microsecond=0).timestamp()
            if m.group(1) in DAYS and end <= now:  # "Friday" said late on a Friday: the next one
                end += 7 * 86400
    end = int(end)
    if end < now + FAST:
        raise ValueError(f"That's {said(end, now)}, too soon for a quicker mail check; it runs every quarter hour.")
    if end > now + MAX_DAYS * 86400:
        raise ValueError(f"That's {said(end, now)}, more than {MAX_DAYS} days away; the most is a week.")
    return end


def said(end, now=None):
    """The end time in plain words: 'today at 22:00', 'tomorrow at 9:00', 'Friday 23 October at 22:00'."""
    now = time.time() if now is None else now
    e, n = datetime.fromtimestamp(end), datetime.fromtimestamp(now)
    hm = f"{e.hour}:{e.minute:02d}"
    days = (e.date() - n.date()).days
    if days == 0:
        return f"today at {hm}"
    if days == 1:
        return f"tomorrow at {hm}"
    return f"{DAYS[e.weekday()].capitalize()} {e.day} {e.strftime('%B')} at {hm}"


def _ambiguous(wall):
    """H162 (sweep of 25 October): the hour the clocks go back happens twice, so its clock time alone can't say which."""
    t = time.strptime(wall, "%Y-%m-%d %H:%M")
    a, b = (int(time.mktime((*t[:8], dst))) for dst in (0, 1))
    return a != b and all(time.strftime("%Y-%m-%d %H:%M", time.localtime(x)) == wall for x in (a, b))


def stamp(end):
    """How the end stands on the roadmap's Mail check line: 2026-10-16 22:00. In the hour that happens twice
    when the clocks go back, with its offset: 2026-10-25 02:10+02:00."""
    wall = time.strftime("%Y-%m-%d %H:%M", time.localtime(end))
    if _ambiguous(wall):
        z = time.strftime("%z", time.localtime(end))
        wall += f"{z[:3]}:{z[3:]}"
    return wall


def from_stamp(s):
    if len(s) > 16:  # with its offset (above)
        return int(datetime.strptime(s[:16] + s[16:].replace(":", ""), "%Y-%m-%d %H:%M%z").timestamp())
    return int(time.mktime(time.strptime(s, "%Y-%m-%d %H:%M")))


if __name__ == "__main__":
    try:
        e = parse(" ".join(sys.argv[1:]))
        print(f"{stamp(e)} ({said(e)})")
    except ValueError as x:
        sys.exit(str(x))
