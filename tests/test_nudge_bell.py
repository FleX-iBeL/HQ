"""A nudge's bell and Undo from the app, checked on a throwaway folder: python3 tests/test_nudge_bell.py (no Claude, no network).

The bell makes a nudge quiet until the next morning she may nudge (nudge_later), a second tap wakes it at its usual gap
from now (nudge_wake, only a paused one), and Undo after Done opens it again as it was (nudge_reopen)."""
import datetime as dt
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
tmp = Path(tempfile.mkdtemp(prefix="hq-nudge-test-"))
(tmp / "HQ" / "direct-line").mkdir(parents=True)
os.environ.update(HQ_FOLDER=str(tmp), HQ_WORKSPACE=str(tmp), HQ_ROLE_HERE="1", HQ_UNDER_TEST="1",
                  HQ_DIRECT_DIR=str(tmp / "HQ" / "direct-line"))
sys.path[:0] = [str(ROOT / "app"), str(ROOT / "routine")]
import pings  # noqa: E402

fails = []


def need(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def state():
    return json.loads(pings.data_file().read_text(encoding="utf8"))


noon = dt.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
x = pings.nudge_add(noon, "Water the plants", now=noon)
n = x["n"]
other = pings.nudge_add(noon, "Fix the bike", now=noon)

need(not pings.nudge_wake(str(n)), "waking a nudge that isn't paused changes nothing")
hit = pings.nudge_later(str(n), now=noon.timestamp())
y = next(z for z in state()["nudges"] if z["n"] == n)
morning = (noon + dt.timedelta(days=1)).replace(hour=pings.NUDGE_DAY[0])
need(len(hit) == 1 and y.get("paused") and y["next"].startswith(morning.strftime("%Y-%m-%d %H")),
     "the bell: quiet until tomorrow morning (" + y["next"] + ")")
need(not next(z for z in state()["nudges"] if z["n"] == other["n"]).get("paused"), "the other nudge stays as it was")

hit = pings.nudge_wake(str(n), now=noon.timestamp())
y = next(z for z in state()["nudges"] if z["n"] == n)
need(len(hit) == 1 and not y.get("paused") and pings._local_ts(y["next"]) >= noon.timestamp() + 3600 - 60
     and pings._local_ts(y["next"]) < morning.timestamp(),
     "the bell again: it goes on, the next one at its usual gap (" + y["next"] + ")")
late = noon.replace(hour=20, minute=50)
pings.nudge_later(str(n), now=late.timestamp())
pings.nudge_wake(str(n), now=late.timestamp())
y = next(z for z in state()["nudges"] if z["n"] == n)
need(pings._local_ts(y["next"]) <= morning.timestamp(), "woken late in the evening: never later than the quiet time (" + y["next"] + ")")

before = next(z for z in state()["nudges"] if z["n"] == n)
pings.nudge_done(str(n))
need(next(z for z in state()["nudges"] if z["n"] == n).get("done"), "Done marks it done")
need(not pings.nudge_reopen(other["n"]), "Undo can't open a nudge that isn't done")
back = pings.nudge_reopen(n)
y = next(z for z in state()["nudges"] if z["n"] == n)
need(back is not None and not y.get("done") and y["next"] == before["next"] and y["text"] == before["text"],
     "Undo after Done: open again, as it was")
need(not pings.nudge_reopen(9999), "no such nudge: nothing happens")
need(any(z["n"] == n for z in pings.nudge_items()), "the app lists it again")

print("All passed." if not fails else "FAILED: " + "; ".join(fails))
sys.exit(1 if fails else 0)
