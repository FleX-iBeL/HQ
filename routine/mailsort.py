"""H213: the hourly mail check sorting new mail by the rules the user agreed (19 October 2026).

The user's words on the call of 19 October 2026 (10:57): "I know normally you set a filter and then everything goes
into a label automatically. I don't think Donna would be able to do that, right? ... Maybe for every mail check Donna
can just put it in that folder. I know it will cost usage so maybe it can advise, "Hey you can set this up as a
filter," but is it possible?" and, on the answer: "Yeah, I like it. I like that Donna can offer both."

So for "keep putting these in a label" the agent offers both: a real Gmail filter first (she walks them through it,
so it works without HQ), or a sorting rule here. A rule says which mail (who or what, in their own words), which label,
and whether it's archived (out of the inbox). The hourly mail check (mail-check.md) gets the rules that are on in its
instructions and, for each new mail it already reads that fits one, adds the label and archives it if the rule says
so, with only the label tools allowed to it (tick.py), then writes one line for it here (`sorted`). No rules, or all
stopped: the mail check stays read-only, as before. Nothing is ever deleted, trashed or marked as spam by a rule.

Kept in the workspace: HQ/mail-sort.json (the rules, and the last lines of what was sorted). HQ_MAIL_SORT is a test's.

    python3 routine/mailsort.py list                         the rules (on and stopped) and the last mail sorted
    python3 routine/mailsort.py add "WHICH MAIL" --label "LABEL" [--archive] [--words "THEIR WORDS"]
    python3 routine/mailsort.py stop N                       stop rule N (kept, so it can start again)
    python3 routine/mailsort.py start N                      start it again
    python3 routine/mailsort.py remove N                     take it off for good
    python3 routine/mailsort.py sorted N "FACTS" --key K     the mail check: it sorted one mail by rule N
    python3 routine/mailsort.py text                         the rules that are on, for the mail check's instructions
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hqpaths  # noqa: E402

LOG_KEEP = 200  # the last mails sorted, kept for "what did it sort?"


def path() -> Path:
    return Path(os.environ.get("HQ_MAIL_SORT") or os.path.join(hqpaths.DATA, "mail-sort.json"))


def read() -> dict:
    try:
        d = json.loads(path().read_text(encoding="utf8"))
    except (OSError, ValueError):
        d = {}
    d.setdefault("rules", [])
    d.setdefault("sorted", [])
    return d


def _save(d: dict) -> None:
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    os.replace(tmp, p)


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def on_rules(d: dict | None = None) -> list[dict]:
    return [r for r in (d or read())["rules"] if r.get("on")]


def any_on() -> bool:
    """Whether the mail check may sort at all this run (tick.py allows the label tools only then)."""
    return bool(on_rules())


def _find(d: dict, n: str) -> dict:
    try:
        k = int(str(n).lstrip("#"))
    except ValueError:
        raise SystemExit(f"No rule {n}: give its number (list shows them).")
    r = next((r for r in d["rules"] if r["n"] == k), None)
    if not r:
        raise SystemExit(f"No rule {k}.")
    return r


def _says(r: dict) -> str:
    return (f"mail {r['which']} gets the label {r['label']}" + (" and is archived" if r.get("archive") else "")
            + ("" if r.get("on") else " (stopped)"))


def add(which: str, label: str, archive: bool, words: str = "") -> dict:
    which, label = which.strip(), label.strip()
    if not which or not label:
        raise SystemExit("A rule needs which mail and a label.")
    d = read()
    n = max([r["n"] for r in d["rules"]] or [0]) + 1
    r = {"n": n, "which": which, "label": label, "archive": bool(archive), "on": True, "added": _now()}
    if words.strip():
        r["words"] = words.strip()
    d["rules"].append(r)
    _save(d)
    return r


def switch(n: str, on: bool) -> dict:
    d = read()
    r = _find(d, n)
    r["on"] = on
    r["stopped" if not on else "started"] = _now()
    _save(d)
    return r


def remove(n: str) -> dict:
    d = read()
    r = _find(d, n)
    d["rules"] = [x for x in d["rules"] if x is not r]
    _save(d)
    return r


def sorted_one(n: str, facts: str, key: str = "") -> dict:
    """One line per mail sorted. The same mail (key) twice is noted once."""
    d = read()
    r = _find(d, n)
    if key and any(s.get("key") == key for s in d["sorted"]):
        return r
    d["sorted"].append({"at": _now(), "rule": r["n"], "label": r["label"], "archived": bool(r.get("archive")),
                        "facts": " ".join(facts.split()), **({"key": key} if key else {})})
    d["sorted"] = d["sorted"][-LOG_KEEP:]
    r["count"] = r.get("count", 0) + 1
    r["last"] = _now()
    _save(d)
    return r


def text() -> str:
    """For the hourly mail check's instructions: the rules that are on, one line each, or that there are none."""
    rs = on_rules()
    if not rs:
        return "(no sorting rules)"
    return "\n".join(f"- Rule {r['n']}: mail {r['which']} gets the label \"{r['label']}\""
                     + (", and is archived (INBOX removed)" if r.get("archive") else ", and stays in the inbox")
                     for r in rs)


def listing(last: int = 10) -> str:
    d = read()
    if not d["rules"]:
        return "No sorting rules. The mail check only reads mail."
    out = ["Sorting rules (the hourly mail check applies the ones that are on to new mail):"]
    for r in d["rules"]:
        out.append(f"- rule {r['n']}: {_says(r)}" + (f", {r['count']} sorted so far, the last {r['last']}"
                                                    if r.get("count") else ", nothing sorted yet"))
    if d["sorted"]:
        out += ["", "Last sorted:"] + [f"- {s['at']} · rule {s['rule']} · {s['label']}"
                                       + (" · archived" if s.get("archived") else "") + f" · {s['facts']}"
                                       for s in d["sorted"][-last:][::-1]]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mailsort.py")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("list")
    sub.add_parser("text")
    a = sub.add_parser("add")
    a.add_argument("which")
    a.add_argument("--label", required=True)
    a.add_argument("--archive", action="store_true")
    a.add_argument("--words", default="")
    for name in ("stop", "start", "remove"):
        sub.add_parser(name).add_argument("n")
    s = sub.add_parser("sorted")
    s.add_argument("n")
    s.add_argument("facts")
    s.add_argument("--key", default="")
    args = p.parse_args(argv)
    if args.cmd in (None, "list"):
        print(listing())
    elif args.cmd == "text":
        print(text())
    elif args.cmd == "add":
        r = add(args.which, args.label, args.archive, args.words)
        print(f"Rule {r['n']} is on: {_says(r)}. The hourly mail check applies it to new mail from now on.")
    elif args.cmd == "stop":
        print(f"Rule {switch(args.n, False)['n']} is stopped; nothing more gets sorted by it.")
    elif args.cmd == "start":
        print(f"Rule {switch(args.n, True)['n']} is on again.")
    elif args.cmd == "remove":
        print(f"Rule {remove(args.n)['n']} is gone.")
    elif args.cmd == "sorted":
        r = sorted_one(args.n, args.facts, args.key)
        print(f"Noted under rule {r['n']}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
