#!/usr/bin/env python3
"""Rewrite the status block at the top of HQ/roadmap.md. Copied from an earlier project's status page (8 October 2026).
usage: set-status.py STATE "STEP" "JUST" "NEXT" "TABLE_ROW" "LOGLINE" ["UPDATED_NOTE"]
STATE: BUILDING|TESTING|RELEASING|WAITING|DONE|STOPPED. TABLE_ROW like "Phase A|A1 ✅|A2 🔨|A3 ⬜".
Keeps the newest eight log lines. An empty TABLE_ROW keeps the phase row that was there; a row that
doesn't start with "Phase " is refused, and so is an empty one when there's no row to keep (F35)."""
import os, re, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "routine"))
import hqpaths  # M1: the roadmap is in the workspace
path = hqpaths.ROADMAP
states = {"BUILDING": "🔨 BUILDING", "TESTING": "🧪 TESTING", "RELEASING": "🚀 RELEASING",
          "WAITING": "⏸ WAITING FOR YOU", "DONE": "✅ DONE", "STOPPED": "⚠️ STOPPED"}
state, step, just, nxt, row, logline = sys.argv[1:7]
note = sys.argv[7] if len(sys.argv) > 7 else None

text = open(path, encoding="utf8").read()
head, sep, rest = text.partition("\n---\n")
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
open(path, "w", encoding="utf8").write(block + sep + rest)
print(block)
