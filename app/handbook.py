"""The handbook: how the agents run themselves (H298, piece 1, 29 October 2026).

The user's words (29 October 2026): "the whole point is i dont want to shadow, or tell them. its okay if they make
mistakes, but if they iterate on it, we will get there." The handbook is the workspace's `HQ/agents/handbook.md`:
part one is the shared core every agent reads (what HQ is for, the north star, Pareto and Parkinson the agent way,
the house rules, how she knows what worked); part two is each agent's own section (her job in one sentence, her ten
percent, what she lets go, her cycle, what she decides and what she asks, her score). HQ ships a blank, generic one in
the template; everything personal lives in the user's own copy, never in HQ.

Loaded only while the feature "The agents run themselves" is on (app/features.py, id agents_run): under her
character on calls (agents.persona), in texts (direct_line) and in her own cycles (routine/cycles.py). Off means today's
HQ exactly: nothing of this is loaded.

    python3 app/handbook.py            whether it's on, and what each agent gets
    python3 app/handbook.py core       part one, as loaded
    python3 app/handbook.py AGENT      her part two section
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEATURE = "agents_run"
REL = "HQ/agents/handbook.md"
CORE_MOST = 20_000      # characters of part one loaded (the whole of a normal handbook is well under it)
SECTION_MOST = 12_000   # characters of her own section


def folder() -> Path:
    if os.environ.get("HQ_HANDBOOK_FOLDER"):
        return Path(os.environ["HQ_HANDBOOK_FOLDER"])
    if os.environ.get("HQ_FOLDER"):
        return Path(os.environ["HQ_FOLDER"])
    return Path(os.path.realpath(os.environ.get("HQ_WORKSPACE", str(ROOT / "workspace"))))


def path(base: Path | None = None) -> Path:
    return (base or folder()) / REL


def on(base: Path | None = None) -> bool:
    """The feature's switch (features.py): in pieces and only on the maker's HQ until it ships, then off by default."""
    try:
        sys.path.insert(0, str(ROOT / "app"))
        import features
        return features.is_on(FEATURE, base)
    except Exception:
        return False


def text(base: Path | None = None) -> str:
    try:
        return path(base).read_text(encoding="utf8")
    except OSError:
        return ""


def _parts(t: str) -> tuple[str, str]:
    """(part one, part two): the text between "## Part one" and "## Part two", and from "## Part two" on (up to the
    next "## Part" or the end)."""
    one = re.search(r"^## Part one\b.*$", t, re.M)
    two = re.search(r"^## Part two\b.*$", t, re.M)
    if not one:
        return "", ""
    end1 = two.start() if two else len(t)
    p1 = t[one.start():end1]
    if not two:
        return p1, ""
    nxt = re.search(r"^## Part (three|four|five)\b", t[two.end():], re.M)
    p2 = t[two.start():two.end() + nxt.start()] if nxt else t[two.start():]
    return p1, p2


def core(base: Path | None = None) -> str:
    """Part one, the shared core, as every agent gets it (without the file's own head)."""
    one, _ = _parts(text(base))
    one = re.sub(r"^---\s*$", "", one, flags=re.M).strip()
    return one[:CORE_MOST]


def section(agent: dict | str, base: Path | None = None) -> str:
    """Her own section of part two: the "### <Name>" heading up to the next "###" (or the end of part two)."""
    name = agent["name"] if isinstance(agent, dict) else str(agent)
    _, two = _parts(text(base))
    if not two:
        return ""
    heads = list(re.finditer(r"^### (.+)$", two, re.M))
    for i, h in enumerate(heads):
        title = h.group(1).strip()
        if re.match(rf"{re.escape(name)}\b", title, re.I):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(two)
            return two[h.start():end].rstrip()[:SECTION_MOST]
    return ""


def block(agent: dict, user: str = "the user", base: Path | None = None) -> str:
    """What goes under her character when the feature is on: part one and her section; "" otherwise."""
    if not on(base):
        return ""
    c, s = core(base), section(agent, base)
    if not c and not s:
        return ""
    out = ("\n# The handbook: how you run yourself (H298)\n\n"
           f"This is the handbook of {user}'s HQ, read by every agent. Part one is the shared core; after it comes "
           "your own section. Where it says what you decide and what you ask, that's your limit on calls, in texts "
           "and in your own cycles. Your ledger (HQ/ledger/<your id>.md in the workspace) is where your cycles write "
           "what they did; an order he gives you on a call (\"start x\", \"stop y\", \"from now on\") goes there too, "
           "with the cycles script.\n\n")
    if c:
        out += c + "\n\n"
    if s:
        out += "## Your own section\n\n" + s + "\n"
    return out


# H298, piece 1: Moneypenny's craft says she fills in the nine points herself and marks ready once they pass; with the
# handbook on, "ground every decision" and the ready check's mechanical fields replace that: only what she grounded
# in his quoted words, with her additions named and the sources real, gets the mark (sprint.py check holds it).
_CRAFT_OLD = re.compile(r"You execute towards the team planning yourself: write the items, fill in the nine points, "
                        r"mark them ready\s+once they pass all nine, rank them, put them in the sprint,")
_CRAFT_NEW = ("You execute towards the team planning yourself: write the items with his words quoted (His words:), "
              "your own additions named (My own additions:, or none) and the sources real (Sources:), and mark ready "
              "only what you grounded that way (the ready check reads those fields and refuses the mark when one is "
              "empty or false; that refusal is a tripwire), rank them, put them in the sprint,")


def trim_craft(craft: str, base: Path | None = None) -> str:
    """Her craft with the line that says the opposite of the handbook changed, only while the feature is on."""
    if not craft or not on(base):
        return craft
    return _CRAFT_OLD.sub(_CRAFT_NEW, craft)


def words(base: Path | None = None) -> str:
    sys.path.insert(0, str(ROOT / "app"))
    import agents
    b = base or folder()
    out = [f"The agents run themselves: {'on' if on(b) else 'off'} here. Handbook: {path(b)}"
           + ("" if path(b).exists() else " (missing; the template ships a blank one)")]
    c = core(b)
    out.append(f"Part one: {len(c)} characters" if c else "Part one: not found (no '## Part one' heading)")
    for a in agents.load(b):
        if a.get("hidden"):
            continue
        s = section(a, b)
        out.append(f"{a['name']}: her section {len(s)} characters" if s else f"{a['name']}: no section of her own")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("list", "show"):
        print(words())
        return 0
    if argv[0] == "core":
        print(core())
        return 0
    sys.path.insert(0, str(ROOT / "app"))
    import agents
    who = argv[0].strip().lower()
    a = next((x for x in agents.load(folder()) if who in (x["id"], x["name"].lower())), None)
    if not a:
        print(f"No agent called {argv[0]}.")
        return 2
    print(section(a) or f"{a['name']} has no section of her own in the handbook.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
