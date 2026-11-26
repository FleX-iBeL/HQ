"""What every test here shares: a throwaway workspace, the paths to HQ's modules, and a check that prints ok or FAIL.

Every test writes only to a temp folder, needs no Claude and no network, and ends with "All passed." or "FAILED: …"."""
import os
import sys
import tempfile
from pathlib import Path

HQ = Path(__file__).resolve().parent.parent
APP, ROUTINE = HQ / "app", HQ / "routine"
sys.path[:0] = [str(APP), str(ROUTINE)]

CHALLENGES = """# Challenges

## 0. Commitments towards other people

| Challenge | Type | For | Deadline | Status | In calendar | Added | Notes |
|---|---|---|---|---|---|---|---|

## 1. Important, not urgent

| Challenge | Type | Deadline | Status | In calendar | Added | Notes |
|---|---|---|---|---|---|---|
| Read a book | active | | open | | 2026-10-05 | |

## 2. Important and urgent

| Challenge | Type | Deadline | Status | In calendar | Added | Notes |
|---|---|---|---|---|---|---|

## 3. Urgent, not important

| Challenge | Type | Deadline | Status | In calendar | Added | Notes |
|---|---|---|---|---|---|---|

## 4. Not urgent, not important

| Challenge | Type | Deadline | Status | In calendar | Added | Notes |
|---|---|---|---|---|---|---|

## 5. Consciously decided not to pursue

| Challenge | Decided (date, time) | Why |
|---|---|---|

## 7. Done

| Challenge | Done (date, time) | Notes |
|---|---|---|

## Groceries

| Item | How often | Last bought | Notes |
|---|---|---|---|

## Log

Newest first.

- 2026-10-05 10:00: started.
"""


def workspace(prefix: str) -> Path:
    """A throwaway workspace with an HQ folder and a to-do file, set as THE workspace for everything this test imports."""
    tmp = Path(tempfile.mkdtemp(prefix=f"hq2-{prefix}-"))
    (tmp / "HQ").mkdir()
    (tmp / "challenges.md").write_text(CHALLENGES, encoding="utf8")
    os.environ.update(HQ_FOLDER=str(tmp), HQ_WORKSPACE=str(tmp), HQ_ROLE_HERE="1", HQ_UNDER_TEST="1",
                      HQ_SUPPORT=str(tmp / "support"), HQ_TODO_UNDO=str(tmp / "todo-undo.json"),
                      HQ_GAMES_UNDO=str(tmp / "games-undo.json"), HQ_LISTS_UNDO=str(tmp / "lists-undo.json"),
                      HQ_ROADMAP=str(tmp / "HQ" / "roadmap.md"))
    for k in ("HQ_TODO", "HQ_GAMES", "HQ_LISTS", "HQ_SPRINT", "HQ_PREP", "HQ_ROLE_READ"):
        os.environ.pop(k, None)
    return tmp


fails = []


def need(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        fails.append(what)


def done():
    print()
    print("FAILED: " + "; ".join(fails) if fails else "All passed.")
    sys.exit(1 if fails else 0)
