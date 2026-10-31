#!/usr/bin/env python3
"""F106: what each agent starts a call with, in bytes, against the cap. Only sizes, nothing of what's in it.

    python3 app/startsize.py           every agent's start
    python3 app/startsize.py --check   exit 1 when one is over config.START_CAP
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agents  # noqa: E402
import config  # noqa: E402
import quick_context  # noqa: E402


def start_of(a: dict, folder: Path | None = None) -> dict:
    """The text HQ adds at a call's start, the way Call and pipeline.make_brain put it together."""
    folder = folder or config.FOLDER
    context = agents.context_of(a)
    context = "day" if context == "all" else context
    everyone = agents.visible(folder) + agents.soon(folder)
    others = [x for x in everyone if x["id"] != a["id"]]
    persona = agents.persona(a, config.USER, light=True) + agents.switch_rules(a, others, config.USER)
    rules = config.start_rules(context, a["name"]) + config.HANGUP_RULES + persona
    ctx = quick_context.build(folder, context=context)
    return {"agent": a["id"], "context": context, "rules": len(rules.encode()), "start": len(ctx.encode()),
            "total": len((ctx + rules).encode()), "cap": config.START_CAP}


def main(argv: list[str]) -> int:
    over = 0
    for a in agents.visible(config.FOLDER):
        d = start_of(a)
        over += d["total"] > d["cap"]
        print(f"{d['agent']}: {d['total']} bytes of {d['cap']} (the rules and who she is {d['rules']}, what she starts with {d['start']})")
    return 1 if over and "--check" in argv else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
