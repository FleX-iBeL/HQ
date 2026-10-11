"""K0 and K5: what a short call costs, step by step (9 October 2026: "im surprised because
calling costs 2% of usage").

Opens a call in test mode (nothing can change, no after-call work), lets it warm up, asks one
question that needs the calendar, closes it, and reads the session's own record of every step:
how many tokens were read from the cache, written to it, and written out. Also lists what the
session had loaded (tools per connector). Run from the HQ folder:

    .venv/bin/python app/measure_call.py                 # Quick, as the switches are now
    .venv/bin/python app/measure_call.py --load deep
    HQ_LIGHT_NOTES=0 .venv/bin/python app/measure_call.py   # with a switch off (see config.py)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402

QUESTION = "What's on my calendar this Saturday? Just tell me briefly."


def steps(session_id: str) -> list[dict]:
    """Every model call of the session, from the CLI's own record (one line per message)."""
    proj = Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(config.FOLDER))
    f = proj / f"{session_id}.jsonl"
    seen, out = set(), []
    for line in f.read_text().splitlines():
        d = json.loads(line)
        if d.get("type") != "assistant":
            continue
        m = d["message"]
        if m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        u = m.get("usage") or {}
        out.append({
            "model": m.get("model", ""),
            "read": u.get("cache_read_input_tokens", 0), "write": u.get("cache_creation_input_tokens", 0),
            "in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0),
            "tools": [c.get("name") for c in m.get("content", []) if c.get("type") == "tool_use"],
        })
    return out


async def main(load: str, model: str) -> None:
    import brain  # noqa: F401  (clears the API key variables first)
    from call import Call

    call = Call(model=model, load=load, wrap_up="dry", test_mode=True, calls_dir=config.SCRATCH / "measure")
    try:
        await call.warm()
        reply = ""
        async for piece in call.brain.ask(QUESTION):
            if isinstance(piece, str):
                reply += piece
        info = call.brain.init_info or {}
        sid = call.brain.session_id
    finally:
        call._finished = True
        call.transcript.path.unlink(missing_ok=True)
        await call.brain.stop()

    tools = info.get("tools", [])
    per = Counter(t.split("__")[1] if t.startswith("mcp__") else "built in" for t in tools)
    print(f"== {load.capitalize()} call on {call.model} · switches: {config.light_switches()}")
    print(f"tools loaded: {len(tools)} ({', '.join(f'{k} {v}' for k, v in per.most_common())})")
    print(f"reply: {reply.strip()[:160]!r}")
    rows = steps(sid)
    for i, r in enumerate(rows, 1):
        print(f" {i:>2}  start {r['read'] + r['write'] + r['in']:>7,}  cache read {r['read']:>7,}  written {r['write']:>6,}  "
              f"out {r['out']:>4}  {' '.join(r['tools'])}")
    tot = {k: sum(r[k] for r in rows) for k in ("read", "write", "in", "out")}
    first = rows[0]["read"] + rows[0]["write"] + rows[0]["in"] if rows else 0
    print(f"steps {len(rows)} · the first step starts at {first:,} tokens · in all: cache read {tot['read']:,}, "
          f"written {tot['write']:,}, out {tot['out']:,}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--load", default="quick", choices=["quick", "deep"])
    p.add_argument("--model", default=None)
    a = p.parse_args()
    from loguru import logger
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    asyncio.run(main(a.load, a.model or ("opus" if a.load == "deep" else "sonnet")))
