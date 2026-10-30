#!/usr/bin/env python3
"""Rewrite the status block at the top of HQ/roadmap.md. Copied from an earlier project's status page (8 October 2026).
usage: set-status.py STATE "STEP" "JUST" "NEXT" "TABLE_ROW" "LOGLINE" ["UPDATED_NOTE"]
STATE: BUILDING|TESTING|RELEASING|WAITING|DONE|STOPPED. TABLE_ROW like "Phase A|A1 ✅|A2 🔨|A3 ⬜".
Keeps the newest eight log lines. An empty TABLE_ROW keeps the phase row that was there; a row that
doesn't start with "Phase " is refused, and so is an empty one when there's no row to keep (F35).

F101: written under the queue's lock through a temporary file, so two writers can't lose each other's work and a crash can't
leave half a planning; a file without the block's separator is refused, nothing written. Run from a call on the backup, it goes
to the main, like every other write to the planning."""
import os, re, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "routine"))
import hqpaths  # M1: the roadmap is in the workspace
import jobs as q
import role
path = hqpaths.ROADMAP
if len(sys.argv) < 7:
    sys.exit(__doc__)
if role.is_backup() and not os.environ.get("HQ_ROLE_HERE"):
    sys.exit(role.forward("set_status", ["set", *sys.argv[1:]]))
states = {"BUILDING": "🔨 BUILDING", "TESTING": "🧪 TESTING", "RELEASING": "🚀 RELEASING",
          "WAITING": "⏸ WAITING FOR YOU", "DONE": "✅ DONE", "STOPPED": "⚠️ STOPPED"}
args = sys.argv[1:]
if args and args[0] == "set":  # the hand-over from the backup
    args = args[1:]
state, step, just, nxt, row, logline = args[:6]
note = args[6] if len(args) > 6 else None
if state not in states:
    sys.exit(f"set-status.py: no state {state!r}; nothing written")
lock = q.locked()
lock.__enter__()
text = open(path, encoding="utf8").read()
head, sep, rest = text.partition("\n---\n")
if not sep:
    sys.exit("set-status.py: the roadmap has no --- under its status block; nothing written")
old_log = [l for l in head.splitlines() if re.match(r"^- \d\d:\d\d ", l)]
if note is None:
    m = re.search(r"^\*Updated [^·]*· (.+)\*$", head, re.M)
    note = m.group(1) if m else ""
log = ([f"- {time.strftime('%H:%M')} {logline}"] if logline else []) + old_log
# F35: the block always keeps its one-row phase table (the status page shows a red box without it).
old_row = re.search(r"^\|\s*Phase .*\|\n\|(?:-+\|)+$", head, re.M)
if not row.strip():
    if not old_row:
        sys.exit("set-status.py: the phase row is empty and the status block has none to keep; nothing written")
    table = old_row.group(0)
elif not row.strip().startswith("Phase "):
    sys.exit(f"set-status.py: the phase row must start with \"Phase \" (like \"Phase A|A1 ✅\"), not {row!r}; nothing written")
else:
    cells = [c.strip() for c in row.strip().strip("|").split("|")]
    table = "| " + " | ".join(cells) + " |\n|" + "---|" * len(cells)
block = f"""# {states[state]}

## Now: {step}

**Just finished:** {just}
**Next:** {nxt}

{table}

""" + "\n".join(log[:8]) + f"""

*Updated {time.strftime('%Y-%m-%d')}{' · ' + note if note else ''}*
"""
hqpaths.guard_roadmap(path)  # F17
tmp = f"{path}.status.{os.getpid()}"
with open(tmp, "w", encoding="utf8") as f:
    f.write(block + sep + rest)
try:
    os.chmod(tmp, os.stat(path).st_mode & 0o777)
except OSError:
    pass
os.replace(tmp, path)
lock.__exit__(None, None, None)
print(block)
