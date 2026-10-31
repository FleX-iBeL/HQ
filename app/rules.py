#!/usr/bin/env python3
"""F106: the call rules that aren't in a call's start, looked up when a turn needs them.

His words: "lighter starts". A call starts with a small core (config.start_rules); how the team, the to-do list, the reminders and the
rest work stands here, and the agent reads a topic before she acts on it.

    python3 app/rules.py                  the topics
    python3 app/rules.py TOPIC            the rule of one topic
    python3 app/rules.py craft AGENT      how she works (her craft)
    python3 app/rules.py handbook AGENT   the handbook's part one and her own section
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("HQ_RULES_LOOKUP", "1")
import agents  # noqa: E402
import config  # noqa: E402
import handbook  # noqa: E402


def main(argv: list[str]) -> int:
    if not argv:
        print("\n".join(f"{k}: {v}" for k, v in config.topics().items()))
        return 0
    if argv[0] in ("craft", "handbook") and len(argv) > 1:
        a = next((x for x in agents.load(config.FOLDER) if argv[1].lower() in (x["id"], x["name"].lower())), None)
        if not a:
            print(f"No agent called {argv[1]}.")
            return 2
        print(handbook.trim_craft(a.get("craft") or "") if argv[0] == "craft" else handbook.block(a, config.USER) or "No handbook here.")
        return 0
    text = config.rule_topic(argv[0])
    if not text:
        print(f"No topic {argv[0]}. There are: {', '.join(config.topics())}.")
        return 2
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
