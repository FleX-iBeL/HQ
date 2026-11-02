#!/usr/bin/env python3
"""F103, the record: one id per request, from his words to live.

His words: "yes exactly, i want here we put it on our roadmap and planning, and then we run these first." Work used to be joined
by finding a label in a sentence. Now an item gets an id when it's written, and the id is carried as an argument: a job holds it
in its own line (⟪item …⟫), and QA, the release, the texts and the incidents are given it. Nothing is found by reading sentences.

The record is one append-only file in the workspace, `HQ/trail.jsonl`, never in HQ: one JSON line per step of an item.

    {"at": epoch, "id": "r-1a2b3c4d", "step": "written", "label": "F200", "words": "…"}
    {"at": epoch, "id": "r-1a2b3c4d", "step": "job", "job": 12, "commit": "abc1234", "state": "done"}

    python3 routine/trail.py follow ID|LABEL     everything that happened to an item, oldest first, with what comes next missing
    python3 routine/trail.py id LABEL            an item's id (given now if the row is older than the record)
    python3 routine/trail.py put JSON            the main writes a line the backup handed over (role.WRITES)

A test's own copy (HQ_TRAIL, or a roadmap copy with its HQ_ROADMAP) keeps its own record next to it. Standard library only. Writing
the record never stops the work: a failure turns the record's own line on the page red.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqlock  # noqa: E402
import hqpaths  # noqa: E402

REL = os.path.join("HQ", "trail.jsonl")
ID = re.compile(r"^r-[0-9a-f]{8}$")
LABEL = re.compile(r"^[A-Z]\d+(\.\d+)*$")
WORDS_KEPT = 400  # F103: how much of an item's first words the record keeps; the row itself holds them whole
STEPS = ("written", "job", "qa", "release", "text", "incident")


def path() -> str | None:
    """The record's file, or None for a test that gave no folder of its own (it never writes in a real one)."""
    if os.environ.get("HQ_TRAIL"):
        return os.environ["HQ_TRAIL"]
    if os.environ.get("HQ_ROADMAP"):
        # F111: a test on the real roadmap is refused further on, by then it had left its line here: 6 of the first 9 in his record
        if hqpaths.under_test() and os.path.realpath(hqpaths.ROADMAP) == hqpaths.real_roadmap():
            return None
        return os.path.join(os.path.dirname(hqpaths.ROADMAP), "trail.jsonl")
    if hqpaths.under_test() and not os.environ.get("HQ_WORKSPACE"):
        return None
    return os.path.join(hqpaths.FOLDER, REL)


def lines() -> list[dict]:
    p = path()
    if not p:
        return []
    out = []
    try:
        with open(p, encoding="utf8") as f:
            for l in f:
                try:
                    d = json.loads(l)
                except ValueError:
                    continue
                if isinstance(d, dict) and d.get("id"):
                    out.append(d)
    except OSError:
        pass
    return out


def _backup() -> bool:
    if os.environ.get("HQ_ROLE_HERE"):
        return False
    try:
        import role
        return role.is_backup()
    except Exception:
        return False


def _append(line: dict) -> None:
    p = path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with hqlock.locked(p):
        with open(p, "a", encoding="utf8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")


def _put(line: dict) -> None:
    if not path():
        return
    if _backup():
        import role
        code, _o, _e, how = role.hand("trail", ["put", json.dumps(line, ensure_ascii=False)], timeout=15)
        if how == "kept" or (how == "main" and code == 0):
            return
    _append(line)


def _bad(e: Exception) -> None:
    print(f"(the record: {e!r})", file=sys.stderr)
    try:
        import routines
        routines.bad("record", f"the record couldn't be written: {e!r}", every=30 * 86400)
    except Exception:
        pass


def of(label: str) -> str | None:
    """The id of a label, or None."""
    for d in lines():
        if d.get("step") == "written" and d.get("label") == label:
            return d["id"]
    return None


def label_of(item: str) -> str | None:
    for d in lines():
        if d.get("id") == item and d.get("label"):
            return d["label"]
    return None


def written(label: str, words: str = "", by: str = "") -> str:
    """An item is written: its id, a new one unless the label has one. The id comes back whatever happens to the file."""
    have = of(label)
    if have:
        return have
    item = "r-" + secrets.token_hex(4)
    try:
        _put({"at": round(time.time(), 3), "id": item, "step": "written", "label": label,
              "words": " ".join(str(words).split())[:WORDS_KEPT], **({"by": by} if by else {})})
    except Exception as e:
        _bad(e)
    return item


def resolve(x: str | None) -> str | None:
    """An id from an id or a label; a label without one (a row older than the record) gets it now."""
    x = (x or "").strip()
    if not x:
        return None
    if ID.match(x):
        return x
    if LABEL.match(x.upper()):
        return written(x.upper(), by="older than the record")
    return None


def step(item: str | None, what: str, **facts) -> None:
    """One step of an item. Without an id there's nothing to write; a failure never stops the work."""
    if not item:
        return
    try:
        _put({"at": round(time.time(), 3), "id": item, "step": what, **{k: v for k, v in facts.items() if v not in (None, "", [])}})
    except Exception as e:
        _bad(e)


def follow(x: str) -> list[dict]:
    """Every line of an item, oldest first."""
    item = x if ID.match(x or "") else of((x or "").upper())
    if not item:
        return []
    return sorted((d for d in lines() if d["id"] == item), key=lambda d: d.get("at") or 0)


def _when(d: dict) -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(d.get("at") or 0))


def say(d: dict) -> str:
    s = d.get("step")
    bits = [f"{k} {d[k]}" for k in ("label", "job", "state", "commit", "version", "tag", "why", "key", "line") if d.get(k) not in (None, "")]
    tail = f": {d['words']}" if d.get("words") else ""
    return f"{_when(d)} · {s} · " + ", ".join(bits) + tail


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "follow" and len(argv) > 1:
        got = follow(argv[1])
        if not got:
            print(f"Nothing on the record for {argv[1]}.")
            return 1
        print(f"{got[0]['id']}" + (f" ({got[0].get('label')})" if got[0].get("label") else "") + ":")
        for d in got:
            print("- " + say(d))
        have = {d.get("step") for d in got}
        left = [s for s in STEPS[:4] if s not in have]
        if left:
            print("Not yet: " + ", ".join(left) + ".")
        return 0
    if cmd == "id" and len(argv) > 1:
        got = resolve(argv[1])
        if not got:
            print("Which item? Give its label or id.")
            return 2
        print(got)
        return 0
    if cmd == "put" and len(argv) > 1:
        d = json.loads(argv[1])
        if not isinstance(d, dict) or not ID.match(str(d.get("id"))) or d.get("step") not in STEPS:
            print("Refused: not a line of the record.", file=sys.stderr)
            return 2
        _append(d)
        print("written")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
