"""The planning board, read only: open rows of the phase tables, ranked and tagged from sprint.json, Phase P left out."""
import json
import os

from _kit import done, need, workspace

tmp = workspace("board")
(tmp / "HQ" / "roadmap.md").write_text("""# 🔨 BUILDING
## Now: something
*Updated 2026-11-26 10:00*

---

## Phase F · Bugs

| | Step | Result |
|---|---|---|
| ⬜ | F1 The page is blank | |
| ✅ | F2 Fixed already | done |

## Phase H · Features

| | Step | Result |
|---|---|---|
| ⬜ | H1 A dark mode | |
| ⬜ | H2 A wishlist | |
| 🔁 | H3 Every night | |

## Phase P · Parked

| | Step | Result |
|---|---|---|
| ⬜ | H9 Parked one | |
""", encoding="utf8")
(tmp / "HQ" / "sprint.json").write_text(json.dumps({"order": ["H2", "H1", "F2"], "moscow": {"H2": "must", "H1": "could", "F1": "wont"}}))
before = (tmp / "HQ" / "sprint.json").read_text(), (tmp / "HQ" / "roadmap.md").read_text()
import planning_board  # noqa: E402

b = planning_board.board()
labels = [r["label"] for r in b["rows"]]
need(labels == ["H2", "H1", "F1"], f"Must, Could, then Won't, each with its rank: {labels}")
need("H3" not in labels and "H9" not in labels and "F2" not in labels, "no repeating, parked or done rows")
by = {r["label"]: r for r in b["rows"]}
need(by["H2"]["rank"] == 1 and by["H1"]["rank"] == 2 and by["F1"]["rank"] is None, "ranks among the open rows")
need(by["F1"]["bug"] and not by["H1"]["bug"], "a row in the Bugs phase is a bug")
need([g["tag"] for g in b["groups"]] == ["must", "could", "wont"], "the groups in order")
need("Must:" in planning_board.words(b), "in words too")
need(before == ((tmp / "HQ" / "sprint.json").read_text(), (tmp / "HQ" / "roadmap.md").read_text()), "nothing was written")
done()
