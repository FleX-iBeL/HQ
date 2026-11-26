"""The hand-overs, read only: the notes in HQ/prep/, newest first, each with its title; one read by name; nothing else."""
import os

from _kit import done, need, workspace

tmp = workspace("handovers")
prep = tmp / "HQ" / "prep"
prep.mkdir()
(prep / "2026-11-20-old-one.md").write_text("# The old one\n\ntext\n")
(prep / "2026-11-25-new-one.md").write_text("Some intro\n# The new one\n\nmore\n")
(prep / "notes.txt").write_text("not a hand-over")
(tmp / "HQ" / "secret.md").write_text("# outside prep")
import handovers  # noqa: E402

got = handovers.listing()
need([h["name"] for h in got] == ["2026-11-25-new-one.md", "2026-11-20-old-one.md"], f"newest first, only .md: {[h['name'] for h in got]}")
need(got[0]["title"] == "The new one" and got[0]["date"] == "2026-11-25", "the title is its first heading, the date its name's")
need(handovers.read("2026-11-20-old-one.md")["text"].startswith("# The old one"), "one is read by its name")
need(handovers.read("../secret.md") is None and handovers.read("notes.txt") is None, "nothing outside the folder or not a hand-over")
done()
