#!/usr/bin/env python3
"""F106: what each agent starts a call with, in bytes, against the cap. Only sizes, nothing of what's in it.

    python3 app/startsize.py           every agent's start, and a day agent's on a Deep call
    python3 app/startsize.py --check   exit 1 when one is over config.START_CAP, or its rules over config.START_RULES_MOST

The small list: what a call really starts with. A Deep call with the day's agent, or an agent whose context is "all", loads the folder like a
chat (the CLI reads CLAUDE.md with its @-imports, nothing trimmed): that's measured as it is and named Deep. It isn't held to the cap, a
Deep call keeps the whole folder on purpose (H246), but it's never counted as a Quick one any more.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agents  # noqa: E402
import config  # noqa: E402
import quick_context  # noqa: E402


def whole_folder(folder: Path) -> str:
    """A Deep call's start as the CLI loads it: CLAUDE.md with every @-import that's there, whole."""
    def swap(m):
        p = folder / m.group(1)
        return p.read_text(encoding="utf8", errors="replace") if p.is_file() else m.group(0)
    return quick_context._IMPORT.sub(swap, (folder / "CLAUDE.md").read_text(encoding="utf8", errors="replace"))


def start_of(a: dict, folder: Path | None = None, load: str | None = None) -> dict:
    """The text HQ adds at a call's start, the way Call and pipeline.make_brain put it together. `load`: the call's, else hers."""
    folder = folder or config.FOLDER
    context = agents.context_of(a)
    context = "all" if context == "day" and (load or a.get("load")) == "deep" else context  # as Call does
    everyone = agents.visible(folder) + agents.soon(folder)
    others = [x for x in everyone if x["id"] != a["id"]]
    persona = agents.persona(a, config.USER, light=True) + agents.switch_rules(a, others, config.USER)
    rules = config.start_rules(context, a["name"]) + config.HANGUP_RULES + persona
    ctx = whole_folder(folder) if context == "all" else quick_context.build(folder, context=context)
    return {"agent": a["id"], "context": context, "rules": len(rules.encode()), "start": len(ctx.encode()),
            "total": len((ctx + rules).encode()), "cap": config.START_CAP, "deep": context == "all"}


def main(argv: list[str]) -> int:
    over = 0
    for a in agents.visible(config.FOLDER):
        d = start_of(a)
        if d["deep"]:
            print(f"{d['agent']}: Deep, the whole folder as a chat loads it: {d['total']} bytes, not held to {d['cap']}")
            continue
        over += d["total"] > d["cap"] or d["rules"] > config.START_RULES_MOST  # H338: the rules part has its own share of the cap
        print(f"{d['agent']}: {d['total']} bytes of {d['cap']} (the rules and who she is {d['rules']}, what she starts with {d['start']})")
        if d["rules"] > config.START_RULES_MOST:
            print(f"{d['agent']}: the rules and who she is are {d['rules']} bytes, over their share of {config.START_RULES_MOST}")
        if d["context"] == "day":
            deep = start_of(a, load="deep")
            print(f"{d['agent']} on a Deep call: the whole folder as a chat loads it: {deep['total']} bytes, not held to {d['cap']}")
    return 1 if over and "--check" in argv else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
