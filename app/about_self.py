"""H132: what each agent has said about herself, so she stays the same person on every call and in every text.

The user, 14 October 2026 (call at 13:31): "Donna made some comment about she has a nice chair. When there are
personality comments made like this, I want it to be stored in their own notes. So that their messaging in the
future will stay consistent."

One file per agent in the workspace (never in HQ's code): HQ/agents/<id>-about-herself.md, one fact per line
("- …"). Written after a call with the call's notes (the wrap-up prompt, config.WRAP_UP_PROMPT) and by her direct-line
chat when she says it there (direct_line.TEXT_RULES); agents.load gives each agent her list as `about_self`, and
agents.persona puts it in front of her on every call, three-way call and text. Standard library only.

    python3 app/about_self.py                     every agent's list
    python3 app/about_self.py list AGENT          one agent's list (AGENT: her id or name)
    python3 app/about_self.py add AGENT "FACT"    keep one fact (skipped when it's already there); prints the file
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

MOST = 40  # facts kept per agent, the newest; Claude's choice
LONGEST = 200  # characters per fact

HEAD = ("# What {name} has said about herself\n\n"
        "> **Private.** H132: the little things {name} has told you about herself on calls and in her chat (her "
        "chair, her desk, what she was doing at HQ), so she stays the same person. Loaded with her character on every "
        "call and text. Change or remove a line whenever you like.\n\n")


def _folder() -> Path:
    if os.environ.get("HQ_FOLDER"):
        return Path(os.environ["HQ_FOLDER"])
    ws = Path(os.environ.get("HQ_WORKSPACE", str(Path(__file__).resolve().parent.parent / "workspace")))
    return Path(os.path.realpath(ws))


def path(folder: Path | None, agent_id: str) -> Path:
    return (folder or _folder()) / "HQ" / "agents" / f"{agent_id}-about-herself.md"


def facts(folder: Path | None, agent_id: str) -> list[str]:
    try:
        text = path(folder, agent_id).read_text(encoding="utf8")
    except OSError:
        return []
    return [l[2:].strip() for l in text.splitlines() if l.startswith("- ") and l[2:].strip()]


def _key(fact: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", fact.lower()).strip()


def add(folder: Path | None, agent: dict, fact: str) -> bool:
    """Keep FACT in her list. False when it was empty or already there."""
    fact = " ".join(str(fact).split())[:LONGEST].strip()
    if not fact:
        return False
    have = facts(folder, agent["id"])
    if _key(fact) in {_key(f) for f in have}:
        return False
    have = (have + [fact])[-MOST:]
    p = path(folder, agent["id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(HEAD.replace("{name}", agent["name"]) + "".join(f"- {f}\n" for f in have), encoding="utf8")
    os.replace(tmp, p)
    return True


def block(agent: dict, user: str = "the user") -> str:
    """Her list, for her persona (agents.persona). Always says how a new detail gets kept."""
    have = agent.get("about_self") or []
    out = "\nWhat you've said about yourself before (H132), so you stay the same person:"
    out += ("\n" + "\n".join(f"- {f}" for f in have)) if have else " nothing yet."
    return out + (
        f"\nNever contradict these; bring one back now and then when it fits, like a person who remembers their own "
        f"life. Small new details about yourself (your chair, your desk, your coffee, what you were up to at HQ) are "
        f"fine; once said, they're yours and get kept, so pick them as things you'd want to stay true.\n")


def _find(folder: Path, who: str) -> dict | None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import agents
    who = who.strip().lower()
    return next((a for a in agents.load(folder) if who in (a["id"], a["name"].lower())), None)


def main(argv: list[str]) -> int:
    folder = _folder()
    if not argv:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import agents
        for a in agents.load(folder):
            print(f"{a['name']}:", *(f"\n- {f}" for f in facts(folder, a["id"])) or [" nothing yet"], sep="")
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd not in ("list", "add") or not rest or (cmd == "add" and len(rest) != 2) or (cmd == "list" and len(rest) != 1):
        print(__doc__.split("\n\n")[-1], file=sys.stderr)
        return 2
    a = _find(folder, rest[0])
    if a is None:
        print(f"no agent called {rest[0]}", file=sys.stderr)
        return 1
    if cmd == "list":
        print(*(f"- {f}" for f in facts(folder, a["id"])) or [f"{a['name']}: nothing yet"], sep="\n")
        return 0
    kept = add(folder, a, rest[1])
    print(("kept" if kept else "already there") + f": {path(folder, a['id'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
