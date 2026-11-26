"""The six-week games on a throwaway workspace: a game made from a spec, a day ticked, a count added."""
import json
import os

from _kit import done, need, workspace

tmp = workspace("games")
os.environ["HQ_GAMES_TODAY"] = "2026-11-03"
import games  # noqa: E402

spec = {"name": "Walk every day", "start": "2026-11-02", "weeks": 6,
        "tracks": [{"id": "walk", "kind": "tick", "name": "A walk"}, {"id": "steps", "kind": "count", "name": "Steps", "target": 100}],
        "win": {"track": "walk", "share": 0.9}}
need(games.check_spec(spec) == [], f"the spec is one HQ can keep: {games.check_spec(spec)}")
code, said = games.run(["new", json.dumps(spec), "--by", "a test"])
need(code == 0, f"new: {said.strip()[:120]}")
code, said = games.run(["tick", "done", "--track", "walk", "--by", "a test"])
need(code == 0, f"tick today: {said.strip()[:120]}")
code, said = games.run(["count", "steps", "30", "--by", "a test"])
code2, said2 = games.run(["count", "steps", "12", "--by", "a test"])
need(code == 0 and code2 == 0, f"count twice: {said2.strip()[:120]}")
g = json.loads((tmp / "HQ" / "games.json").read_text())
g = g["games"][0] if isinstance(g, dict) and "games" in g else g[0]
blob = json.dumps(g)
need("2026-11-03" in blob, "today's tick is kept on today")
need("42" in blob, "the count adds up to 42")
code, said = games.run(["tick", "done", "--track", "walk", "--day", "2026-11-09", "--by", "a test"])
need(code != 0, "a day that hasn't come can't be ticked")
done()
