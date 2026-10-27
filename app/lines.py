"""The open line: one Claude session per agent that lives on between calls and texts (Fable, 27 October 2026; the
backend switch `open_line`).

His words (27 October 2026, 16:11): "every time I call you guys, it opens a new chat. Maybe that is not necessary at
all. Maybe we can just keep the line open and I reconnect to it ... all three of you will have your own channel line
open until we reset it, just like we have with the text version." Before this, every call and every text opened a
fresh session and paid her whole start again. Now the session id of her last session on this computer is kept here
(`.status/lines.json`, per computer: the CLI's sessions live on the computer that ran them), and the next call or text
resumes it with a fresh system prompt (her identity and the briefing), so she remembers the morning in the afternoon
and the turn costs the turn. A line is rolled over (a fresh session) when it's been quiet for `QUIET_HOURS`, older
than `MOST_HOURS`, or its context has grown past `BUDGET_TOKENS` (read from the last result's usage); `lines.py reset
[AGENT]` rolls it over by hand, which is what "until we reset it" means.

    python3 app/lines.py            the lines and their state
    python3 app/lines.py reset      every line starts fresh at the next call or text
    python3 app/lines.py reset ID   one agent's
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS = Path(os.environ.get("HQ_STATUS_DIR") or (ROOT / ".status"))
FILE = Path(os.environ.get("HQ_LINES") or (STATUS / "lines.json"))
QUIET_HOURS = 8      # quiet this long: a fresh session (a new day, in effect)
MOST_HOURS = 36      # however busy, a line this old starts fresh
BUDGET_TOKENS = 110_000  # the context the last turn carried; past it the next start is fresh


def _read() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(d: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_name(FILE.name + ".tmp")
    tmp.write_text(json.dumps(d, indent=1) + "\n", encoding="utf8")
    os.replace(tmp, FILE)


def _on() -> bool:
    try:
        sys.path.insert(0, str(ROOT / "app"))
        import backend
        return backend.on("open_line")
    except Exception:
        return False


def why_fresh(rec: dict | None, now: float | None = None) -> str | None:
    """None when the line can be resumed, else why it starts fresh."""
    now = now or time.time()
    if not rec or not rec.get("session"):
        return "no line yet"
    if rec.get("reset"):
        return "reset by hand"
    if now - (rec.get("last") or 0) > QUIET_HOURS * 3600:
        return f"quiet for over {QUIET_HOURS} hours"
    if now - (rec.get("since") or 0) > MOST_HOURS * 3600:
        return f"older than {MOST_HOURS} hours"
    if (rec.get("context_tokens") or 0) > BUDGET_TOKENS:
        return f"its context grew past {BUDGET_TOKENS // 1000}k tokens"
    return None


def session_for(agent_id: str, now: float | None = None) -> str | None:
    """The session to resume for this agent, or None for a fresh one (also when the switch is off)."""
    if not _on():
        return None
    rec = _read().get(agent_id)
    return None if why_fresh(rec, now) else rec["session"]


def note(agent_id: str, session: str | None, context_tokens: int | None = None, how: str = "call") -> None:
    """After a turn: the session this agent is on now and how big its context is. Kept also with the switch off,
    so turning it on resumes the newest session."""
    if not session:
        return
    d = _read()
    rec = d.get(agent_id) or {}
    now = time.time()
    if rec.get("session") != session:
        rec = {"session": session, "since": now, "turns": 0}
    rec["last"] = now
    rec["turns"] = int(rec.get("turns") or 0) + 1
    rec["how"] = how
    if context_tokens is not None:
        rec["context_tokens"] = int(context_tokens)
    rec.pop("reset", None)
    d[agent_id] = rec
    _write(d)


def reset(agent_id: str | None = None) -> list[str]:
    d = _read()
    done = []
    for k, rec in d.items():
        if agent_id in (None, k):
            rec["reset"] = True
            done.append(k)
    _write(d)
    return done


def context_tokens_of(usage: dict | None) -> int | None:
    """What the last turn carried as context, from a result's usage: the input plus what came from the cache."""
    if not isinstance(usage, dict):
        return None
    n = 0
    for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
        v = usage.get(k)
        if isinstance(v, (int, float)):
            n += int(v)
    return n or None


def words() -> str:
    d = _read()
    if not d:
        return "No lines kept yet." + ("" if _on() else " (The open line is switched off.)")
    now = time.time()
    out = []
    for k, rec in d.items():
        why = why_fresh(rec, now)
        age = int((now - (rec.get("last") or now)) // 60)
        out.append(f"{k}: {'fresh at the next start (' + why + ')' if why else 'open, resumed at the next start'}; "
                   f"{rec.get('turns', 0)} turns, last {age} min ago, "
                   f"context about {(rec.get('context_tokens') or 0) // 1000}k tokens, session {str(rec.get('session', ''))[:8]}")
    if not _on():
        out.append("(The open line is switched off: every start is fresh.)")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("list", "show"):
        print(words())
        return 0
    if argv[0] == "reset":
        done = reset(argv[1] if len(argv) > 1 else None)
        print("Fresh at the next start: " + (", ".join(done) if done else "nothing to reset"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
