"""H279: ask Donna or Pepper about an old text, and they find it.

The user's words (26 October 2026, after H255): "Okay, so the 400 is fine. If we have a backup, that's fine. I don't
care if I can't scroll back. If I can just ask her about it and she can search it, then that is great. I assume the
same is for Pepper and her text channel."

A reply on a chat line (direct_line.py: Donna's, the coaching line, the team line) sees only the last 15 texts. The
thread file keeps the newest 400 (KEEP); older ones are only in the workspace's git, where every version of the file
was committed. This searches both, read only: the thread as it is, then every text that was ever added to it in git
(`git log -p` on the file: each "+" line is one text as it was written), so a text past the 400 is still found.
Each text is counted once (by its time and sender). The line is the one the reply runs on (HQ_DIRECT_DIR, as
direct_line.folder()); --dir gives another (a test's).

  python3 app/thread_search.py WORDS...                  texts with all these words, newest first (at most 10)
  python3 app/thread_search.py --on 2026-10-15           every text of that day (words optional)
  python3 app/thread_search.py --from 2026-10-10 --to 2026-10-16 parcel
  ... --who me|her   only his or only hers      ... --most N   at most N (up to 50)      ... --json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "routine"))

MOST = 10
MOST_MAX = 50
TEXT_MAX = 600  # characters of each text shown; a long one is cut, its start is what helps find it


def folder(given: str | None = None) -> Path:
    if given:
        return Path(given)
    if os.environ.get("HQ_DIRECT_DIR"):
        return Path(os.environ["HQ_DIRECT_DIR"])
    import hqpaths
    return Path(hqpaths.DATA) / "direct-line"


def _parse(line: str) -> dict | None:
    try:
        m = json.loads(line)
    except ValueError:
        return None
    if isinstance(m, dict) and m.get("text") and isinstance(m.get("at"), (int, float)):
        return m
    return None


def current(where: Path) -> list[dict]:
    try:
        lines = (where / "thread.jsonl").read_text(encoding="utf8").splitlines()
    except OSError:
        return []
    return [m for m in map(_parse, lines) if m]


def from_git(where: Path) -> list[dict]:
    """Every text ever added to the thread file in git, older ones past the 400 too. Empty when it isn't in git."""
    path = where / "thread.jsonl"
    try:
        top = subprocess.run(["git", "-C", str(where), "rev-parse", "--show-toplevel"], capture_output=True,
                             text=True, timeout=20)
        if top.returncode != 0:
            return []
        rel = os.path.relpath(os.path.realpath(path), os.path.realpath(top.stdout.strip()))
        log = subprocess.run(["git", "-C", top.stdout.strip(), "log", "-p", "--no-color", "--no-ext-diff",
                              "--format=", "--", rel], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return []
    out = []
    for line in log.stdout.splitlines():
        if line.startswith("+{"):
            m = _parse(line[1:])
            if m:
                out.append(m)
    return out


def _day(s: str, end: bool = False) -> float:
    t = time.mktime(time.strptime(s, "%Y-%m-%d"))
    return t + 86400 if end else t


def search(words: list[str], where: Path, *, since: float | None = None, until: float | None = None,
           who: str | None = None, most: int = MOST) -> list[dict]:
    """Texts with every word (any case), in the time window, newest first. Each with "older": True when it's no
    longer in the thread file (found in git)."""
    now = current(where)
    seen, found = set(), []
    keys_now = {(round(m["at"], 3), m.get("from")) for m in now}
    for m in now + from_git(where):
        key = (round(m["at"], 3), m.get("from"))
        if key in seen:
            continue
        seen.add(key)
        if since is not None and m["at"] < since or until is not None and m["at"] >= until:
            continue
        if who == "me" and m.get("from") != "me" or who == "her" and m.get("from") == "me":
            continue
        low = m["text"].lower()
        if all(w.lower() in low for w in words):
            found.append({**m, "older": key not in keys_now})
    found.sort(key=lambda m: m["at"], reverse=True)
    return found[:max(1, min(most, MOST_MAX))]


def show(found: list[dict]) -> str:
    if not found:
        return "Nothing found."
    lines = []
    for m in found:
        when = time.strftime("%a %d %b %Y %H:%M", time.localtime(m["at"]))
        who = "Him" if m.get("from") == "me" else "Her"
        text = m["text"] if len(m["text"]) <= TEXT_MAX else m["text"][:TEXT_MAX] + " …"
        lines.append(f"{when} · {who}{' · (older, from the backup)' if m['older'] else ''}: {text}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Search a chat line's texts, older ones too (H279).")
    ap.add_argument("words", nargs="*")
    ap.add_argument("--on")
    ap.add_argument("--from", dest="since")
    ap.add_argument("--to", dest="until")
    ap.add_argument("--who", choices=("me", "her"))
    ap.add_argument("--most", type=int, default=MOST)
    ap.add_argument("--dir")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        since = _day(a.on) if a.on else (_day(a.since) if a.since else None)
        until = _day(a.on, end=True) if a.on else (_day(a.until, end=True) if a.until else None)
    except ValueError:
        print("Dates are YYYY-MM-DD.", file=sys.stderr)
        return 2
    if not a.words and since is None and until is None:
        print("Give some words to look for, or a day (--on YYYY-MM-DD).", file=sys.stderr)
        return 2
    found = search(a.words, folder(a.dir), since=since, until=until, who=a.who, most=a.most)
    print(json.dumps(found, ensure_ascii=False, indent=1) if a.json else show(found))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
