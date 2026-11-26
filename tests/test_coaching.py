"""Life coaching's place on a throwaway workspace: a check-in marked done without a call, each check-in's last done,
and a game designed in the map that HQ doesn't keep yet."""
import json

from _kit import done, need, workspace

tmp = workspace("coaching")
(tmp / "HQ" / "workflows.json").write_text(json.dumps({"on": ["map"]}))
(tmp / "map.md").write_text("""# The map

## 1. The vision

Status: done

## 3. The six-week game

In HQ:
- Name: Walk more   Start: 2026-12-01   Weeks: 6
- Track: a tick a day, "a walk"

In HQ:
- Name: …   Start: YYYY-MM-DD

## 6. Looking back

Check-ins: the weekly look back on Friday morning.
""")
(tmp / "HQ" / "coaching.json").write_text(json.dumps({"first": "2026-10-01T09:00", "done": {"week:2026-W40": "2026-10-02T10:00"}}))
from datetime import datetime  # noqa: E402

import coaching  # noqa: E402

now = datetime(2026, 11, 27, 12, 0)  # a Friday, after the morning
r = coaching.read(now=now, games=[])
week = next((c for c in r["checkins"] if c["kind"] == "week"), None)
need(week is not None and week["due"], f"the weekly look back is due: {week}")
need(week and week["last_done"] == "2026-10-02T10:00", f"it says when one was last done: {week and week['last_done']}")
said = coaching.done(week["key"], now=now)
need(said.endswith("done."), f"done without a call: {said}")
r = coaching.read(now=now, games=[])
week = next(c for c in r["checkins"] if c["kind"] == "week")
need(not week["due"] and week["last_done"] == "2026-11-27T12:00", f"no longer due, last done now: {week}")
need(r["games_designed"] == ["Walk more"], f"the designed game waits to be set up, the placeholder doesn't count: {r['games_designed']}")
r = coaching.read(now=now, games=[{"name": "Walk more"}])
need(r["games_designed"] == [], "once HQ keeps it, it no longer waits")
done()
