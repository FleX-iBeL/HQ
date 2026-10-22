"""H200: the to-do list, the Eisenhower way, as HQ reads and keeps it (17 October 2026).

The list is the user's own file in the workspace, challenges.md (or HQ_TODO), never HQ's: their priority lists as
"## N. Name" headings, each with a table whose first column is the thing to do, then a wishlist and groceries, the
details in their own words and a log. The template ships it blank. Their numbering and list names are theirs: a
list's place in the matrix comes from its name (important or not, urgent or not), and the lists outside the matrix
from their number or name (0 commitments to other people, 5 decided not to pursue, 7 done, a wishlist, groceries).

Calls, Donna's chat and the app keep it the same way: a change moves or adds a table row, keeps every column (a
column the other list doesn't have goes into its Notes), and writes one line in the file's log, newest first.

    python3 app/todo.py                         the list in a few lines, to say out loud
    python3 app/todo.py json                    everything the app gets (JSON)
    python3 app/todo.py add LIST "TEXT" [--notes "…"] [--deadline "…"] [--type active|passive] [--for "…"]
    python3 app/todo.py done "ITEM" ["NOTE"]    to the done list, with the date and time
    python3 app/todo.py letgo "ITEM" "WHY"      to the let-go list
    python3 app/todo.py move "ITEM" LIST        to another list
    python3 app/todo.py tick "ITEM"             groceries: ticked off, onto the ticked-off list (not done)
    python3 app/todo.py untick "ITEM"           groceries: from the ticked-off list back onto the list
    python3 app/todo.py order "ITEM" N          to place N in its own list (1 is the top)
    python3 app/todo.py rename "ITEM" "NEW"     a new name, the rest of its row kept
    python3 app/todo.py undo                    puts back the last change made here, if nothing changed since

LIST is a list's number (0, 1, 2 …), a few words of its name, or matrix words: "important urgent", "important not
urgent", "urgent", "neither", "wishlist", "groceries". ITEM is the item's id or a few words of it; more than one
match is refused with the matches listed. Adding several things at once (one per line, or with commas on the
groceries) adds one item each.

F40 (18 October 2026), in the user's words: "maybe it should get it's own list that's ticked off, so i can also scroll
through it and tick it back on (can put it on alphabetical order), can be inside once you open groceries button". A
ticked grocery goes to its own list, "## Groceries ticked off" (made under the groceries when it's first needed, with
the groceries' own columns), its Last bought set to the day; untick puts it back. The app shows it A to Z.

H231 (22 October 2026), in the user's words: "And i want to be able to move items on my list and rename them", and
"No I just want to change the order". order puts an item at another place in its own list (the row moves in the
table, nothing else changes), rename gives it a new name and keeps the rest of its row. Both get their log line and
undo. A rename whose old name the details in their own words were found by, and the new one isn't, keeps the old name
in its Notes ("Renamed from: …"), so the details stay with it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # HQ
sys.path.insert(0, str(Path(__file__).resolve().parent))  # loose_ends (F43)
FILE = "challenges.md"
_lock = threading.Lock()
_HEAD = re.compile(r"^##\s+(?:(\d+)\.\s*)?(.+?)\s*$")
_DETAIL = re.compile(r"^\*\*(.+?)\*\*\s*(.*)$")


def folder() -> Path:
    return Path(os.environ.get("HQ_FOLDER") or os.path.realpath(os.environ.get("HQ_WORKSPACE", str(ROOT / "workspace"))))


def path() -> Path:
    return Path(os.environ.get("HQ_TODO") or folder() / FILE)


def _undo_file() -> Path:
    return Path(os.environ.get("HQ_TODO_UNDO") or ROOT / "scratch" / "todo-undo.json")


# ---- reading -------------------------------------------------------------------------------------------------

def kind_of(num: str | None, name: str) -> str:
    """Where a list sits: q1 important and urgent, q2 important not urgent, q3 urgent not important, q4 neither,
    commit, letgo, done, wish, groceries, or other. From its name first, the number only for the lists outside."""
    n = name.lower()
    if "grocer" in n:
        return "grocoff" if re.search(r"ticked|\boff\b|\bgot\b|bought", n) else "groceries"
    if "wish" in n or "shopping" in n:
        return "wish"
    if re.search(r"\bdone\b|\bfinished\b|\bcompleted\b", n) or (num == "7" and "urgent" not in n):
        return "done"
    if "not to pursue" in n or "let go" in n or "letting go" in n or (num == "5" and "urgent" not in n):
        return "letgo"
    if "commitment" in n or (num == "0" and "urgent" not in n):
        return "commit"
    imp = "important" in n and not re.search(r"\b(not|un)\s*important", n)
    urg = "urgent" in n and not re.search(r"\b(not|non)[\s-]*urgent", n)
    if "important" not in n and "urgent" not in n:
        return "other"
    return {(True, True): "q1", (True, False): "q2", (False, True): "q3", (False, False): "q4"}[(imp, urg)]


def _cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def _is_sep(line: str) -> bool:
    return bool(re.fullmatch(r"\s*\|?(\s*:?-{3,}:?\s*\|)*\s*:?-{3,}:?\s*\|?\s*", line))


def _row_line(cells: list[str]) -> str:
    return "| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in cells) + " |"


def _item_id(title: str, seen: dict) -> str:
    base = hashlib.sha1(re.sub(r"\s+", " ", title.strip().lower()).encode()).hexdigest()[:10]
    seen[base] = seen.get(base, 0) + 1
    return base if seen[base] == 1 else f"{base}-{seen[base]}"


def parse(text: str) -> dict:
    """The file as lists of items, plus where each table sits in the lines (for changes)."""
    lines = text.splitlines()
    lists, details, log, how = [], [], [], []
    section, cur, seen = None, None, {}
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _HEAD.match(line) if line.startswith("## ") else None
        if m:
            num, name = m.group(1), m.group(2)
            section = name.lower()
            cur = None
            k = kind_of(num, name)
            if not section.startswith(("details", "log", "how i prioritise", "how i prioritize", "patterns")):
                cur = {"key": num if num is not None else re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
                       "num": num, "name": name, "kind": k, "head": i, "columns": [], "items": [],
                       "table": None}
                lists.append(cur)
            i += 1
            continue
        if cur is not None and line.lstrip().startswith("|") and cur["table"] is None:
            if i + 1 < len(lines) and _is_sep(lines[i + 1]):
                cur["columns"] = _cells(line)
                j = i + 2
                while j < len(lines) and lines[j].lstrip().startswith("|"):
                    cells = _cells(lines[j])
                    cells += [""] * (len(cur["columns"]) - len(cells))
                    title = cells[0]
                    if title:
                        row = dict(zip(cur["columns"], cells))
                        cur["items"].append({"id": _item_id(title, seen), "title": title, "line": j,
                                             "cells": cells[:len(cur["columns"])], "row": row})
                    j += 1
                cur["table"] = (i, j)  # the header line, and the line after the last row
                i = j
                continue
        if section and section.startswith("details"):
            d = _DETAIL.match(line.strip())
            if d:
                details.append({"label": d.group(1).strip().rstrip(".").strip(), "text": d.group(2).strip()})
            elif line.strip() and details and not line.startswith("From "):
                details[-1]["text"] += "\n" + line.strip()
        elif section == "log" and line.startswith("- "):
            log.append(line[2:].strip())
        elif section and section.startswith("how i priorit") and line.strip():
            how.append(line)
        i += 1
    return {"lists": [x for x in lists if x["columns"]], "details": details, "log": log, "how": "\n".join(how),
            "lines": lines}


def _words(s: str) -> list[str]:
    return [w for w in re.findall(r"[\w']+", s.lower()) if len(w) >= 4]


def details_for(title: str, details: list[dict]) -> list[str]:
    """The paragraphs in their own words that belong to an item: its label (up to a colon) in the item's name, or
    every longer word of the label in it."""
    t = title.lower()
    out = []
    for d in details:
        key = re.split(r"[:?]", d["label"])[0].strip().lower()
        if not key:
            continue
        hit = re.search(r"(?<!\w)" + re.escape(key) + r"(?!\w)", t) is not None
        if not hit:
            ws = _words(key)
            hit = bool(ws) and all(w in t for w in ws)
        if hit:
            out.append(f"{d['label']}. {d['text']}".strip())
    return out


_RENAMED = re.compile(r"Renamed from: (.+?)\.(?=\s|$)")  # H231

_FIELDS = {"type": ("type",), "for": ("for",), "deadline": ("deadline", "when"), "status": ("status",),
           "calendar": ("in calendar", "calendar"), "added": ("added",), "notes": ("notes", "why"),
           "at": ("done", "decided", "last bought"), "often": ("how often",)}


def _field(row: dict, name: str) -> str:
    for col, val in row.items():
        c = col.lower()
        if any(c == w or c.startswith(w + " ") or c.startswith(w + "(") for w in _FIELDS[name]):
            return val
    return ""


def read(p: Path | None = None) -> dict:
    """What the app shows: the matrix, the lists outside it, every item with its fields and details."""
    p = p or path()
    try:
        text = p.read_text(encoding="utf8")
    except OSError:
        return {"lists": [], "missing": True, "file": p.name}
    doc = parse(text)
    out = []
    for lst in doc["lists"]:
        items = []
        for it in lst["items"]:
            r = it["row"]
            items.append({"id": it["id"], "title": it["title"], "type": _field(r, "type"), "for": _field(r, "for"),
                          "deadline": _field(r, "deadline"), "status": _field(r, "status"),
                          "calendar": _field(r, "calendar"), "added": _field(r, "added"), "notes": _field(r, "notes"),
                          "at": _field(r, "at"), "often": _field(r, "often"),
                          "fields": [[c, v] for c, v in r.items() if v and c != lst["columns"][0]],
                          "details": details_for(it["title"] + " " + " ".join(_RENAMED.findall(_field(r, "notes"))),
                                                 doc["details"])})
        out.append({"key": lst["key"], "num": lst["num"], "name": lst["name"], "kind": lst["kind"], "items": items})
    return {"lists": out, "log": doc["log"][:12], "how": doc["how"], "file": p.name,
            "changed": int(p.stat().st_mtime), "mail": very_important()}


def very_important(folder_: Path | None = None) -> list[dict]:
    """The mail list's very important items (inbox.md), waiting for an answer: things to do too, shown on top."""
    try:
        text = ((folder_ or folder()) / "inbox.md").read_text(encoding="utf8")
    except OSError:
        return []
    m = re.search(r"^## Very important\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    out = []
    for line in (m.group(1) if m else "").splitlines():
        if not line.startswith("- "):
            continue
        parts = [x.strip() for x in line[2:].split(" · ")]
        if len(parts) < 4:
            continue
        status = next((x[len("Status:"):].strip() for x in parts if x.startswith("Status:")), "")
        out.append({"when": parts[0], "from": parts[1], "subject": parts[2], "what": parts[3], "status": status})
    return out


# ---- finding ---------------------------------------------------------------------------------------------------

_MATRIX_WORDS = [("q2", r"important\W+not\W+urgent|not urgent\W+important|schedule"),
                 ("q1", r"important\W+(and\W+)?urgent|urgent\W+(and\W+)?important|^do$|do (it )?now"),
                 ("q3", r"urgent\W+not\W+important|not important\W+urgent|^urgent$|delegate"),
                 ("q4", r"neither|not urgent\W+not important|not important\W+not urgent|drop"),
                 ("done", r"^done$"), ("letgo", r"let ?go|not to pursue"), ("commit", r"commit|other people"),
                 ("wish", r"wish|shopping"), ("groceries", r"grocer")]


def find_list(doc: dict, want: str) -> dict:
    w = want.strip().lower().lstrip("#").strip()
    lists = doc["lists"]
    for lst in lists:
        if lst["num"] is not None and w in (lst["num"], f"list {lst['num']}", f"{lst['num']}."):
            return lst
    for lst in lists:
        if w == lst["name"].lower() or w == lst["key"]:
            return lst
    for kind, rx in _MATRIX_WORDS:
        if re.search(rx, w):
            hit = [x for x in lists if x["kind"] == kind]
            if hit:
                return hit[0]
    hit = [x for x in lists if w and w in x["name"].lower()]
    if len(hit) == 1:
        return hit[0]
    raise KeyError(f"No list called {want!r}. The lists: " + "; ".join(
        (f"{x['num']}. " if x["num"] is not None else "") + x["name"] for x in lists))


def find_item(doc: dict, want: str) -> tuple[dict, dict]:
    w = want.strip()
    for lst in doc["lists"]:
        for it in lst["items"]:
            if it["id"] == w:
                return lst, it
    low = w.lower()
    exact = [(l, it) for l in doc["lists"] for it in l["items"] if it["title"].lower() == low]
    if len(exact) == 1:
        return exact[0]
    ws = [x for x in re.findall(r"[\w']+", low)]
    hits = [(l, it) for l in doc["lists"] for it in l["items"] if ws and all(x in it["title"].lower() for x in ws)]
    open_hits = [h for h in hits if h[0]["kind"] not in ("done", "letgo")]
    if len(open_hits) == 1:
        return open_hits[0]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise KeyError(f"Nothing on the list matches {want!r}.")
    raise KeyError(f"More than one matches {want!r}: " + "; ".join(f"{it['title']} ({it['id']})" for _, it in hits[:8]))


# ---- changing --------------------------------------------------------------------------------------------------

def _now() -> datetime:
    t = os.environ.get("HQ_NOW")
    return datetime.fromisoformat(t) if t else datetime.now()


def _list_label(lst: dict) -> str:
    return f"{lst['num']} ({lst['name'].lower()})" if lst["num"] is not None else lst["name"].lower()


def _row_for(lst: dict, values: dict, extra: list[tuple[str, str]]) -> list[str]:
    """A row for this list's columns from named values; what has no column goes into Notes (or the last column)."""
    cols = lst["columns"]
    cells = [""] * len(cols)
    used = set()
    for i, col in enumerate(cols):
        if i == 0:
            cells[0] = values.get("title", "")
            continue
        c = col.lower()
        for name, words in _FIELDS.items():
            if name in values and values[name] and any(c == w or c.startswith(w + " ") or c.startswith(w + "(") for w in words):
                cells[i] = values[name]
                used.add(name)
                break
    left = [f"{k}: {v}" for k, v in extra if v] + [
        f"{k.capitalize()}: {v}" for k, v in values.items() if k not in used and k not in ("title", "notes") and v]
    note_at = next((i for i, c in enumerate(cols) if i and c.lower().split(" ")[0] in ("notes", "why")), len(cols) - 1)
    if note_at and (values.get("notes") or left):
        base = cells[note_at] or ("" if "notes" in used else values.get("notes", ""))
        cells[note_at] = " ".join(x for x in [base] + [x + "." if not x.endswith(".") else x for x in left] if x).strip()
    return cells


def _insert_log(lines: list[str], line: str) -> list[str]:
    """One line at the top of the log (newest first); a log section is added at the end when there's none."""
    at = next((i for i, l in enumerate(lines) if re.match(r"^##\s+Log\s*$", l)), None)
    if at is None:
        return lines + ["", "## Log", "", "Newest first. One line per change: what happened, and why.", "", line]
    end = next((i for i in range(at + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    first = next((i for i in range(at + 1, end) if lines[i].startswith("- ")), None)
    if first is None:
        k = end
        while k > at + 1 and not lines[k - 1].strip():
            k -= 1
        return lines[:k] + ["", line] + lines[k:]
    return lines[:first] + [line] + lines[first:]


def _write(p: Path, before: str, lines: list[str], what: str, swept: list | None = None) -> None:
    text = "\n".join(lines) + ("\n" if before.endswith("\n") else "")
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(text, encoding="utf8")
    os.replace(tmp, p)
    try:
        u = _undo_file()
        u.parent.mkdir(parents=True, exist_ok=True)
        u.write_text(json.dumps({"file": str(p), "before": before, "after_sha": hashlib.sha1(text.encode()).hexdigest(),
                                 "what": what} | ({"swept": swept} if swept else {})), encoding="utf8")
    except OSError:
        pass


def _by(by: str) -> str:
    return f" ({by})" if by else ""


def _move(p: Path, want_item: str, to: dict | str, at_value: str = "", note: str = "", by: str = "",
          log_what: str = "") -> dict:
    with _lock:
        before = p.read_text(encoding="utf8")
        doc = parse(before)
        src, it = find_item(doc, want_item)
        dst = find_list(doc, to) if isinstance(to, str) else to
        dst = next(x for x in doc["lists"] if x["head"] == dst["head"])
        if dst["head"] == src["head"]:
            return {"ok": True, "said": f"{it['title']} is already on {_list_label(dst)}.", "id": it["id"]}
        r = it["row"]
        vals = {"title": it["title"]}
        for name in _FIELDS:
            v = _field(r, name)
            if v:
                vals[name] = v
        if not (src["kind"] in ("groceries", "grocoff") and dst["kind"] in ("groceries", "grocoff")):
            vals.pop("at", None)
        extra = []
        if dst["kind"] in ("done", "letgo"):
            vals["at"] = at_value or _now().strftime("%Y-%m-%d %H:%M")
            if note:
                vals["notes"] = note if dst["kind"] == "letgo" else " ".join(x for x in (note, vals.get("notes", "")) if x)
            for k in ("type", "for", "deadline", "calendar", "added", "often"):
                vals.pop(k, None)
            vals.pop("status", None)
        elif dst["kind"] == "grocoff":
            vals["at"] = _now().strftime("%Y-%m-%d")
        else:
            if src["kind"] in ("done", "letgo"):
                vals["status"] = "open"
            elif note:
                vals["notes"] = " ".join(x for x in (vals.get("notes", ""), note) if x)
        # what the source row had in a column the target doesn't know goes into its notes, so nothing is lost
        known = {c.lower() for c in dst["columns"]}
        for col, v in r.items():
            if col == src["columns"][0] or not v or col.lower() in known:
                continue
            if any(col.lower() == w or col.lower().startswith(w + " ") for name in _FIELDS for w in _FIELDS[name]
                   if name in vals):
                continue
            if dst["kind"] in ("done", "letgo") and col.lower().split(" ")[0] in ("status", "added", "in", "type", "deadline"):
                continue
            extra.append((col, v))
        cells = _row_for(dst, vals, extra)
        lines = list(doc["lines"])
        del lines[it["line"]]
        end = dst["table"][1] - (1 if dst["table"][1] > it["line"] else 0)
        lines.insert(end, _row_line(cells))
        stamp = _now().strftime("%Y-%m-%d %H:%M")
        what = log_what or f"moved to {_list_label(dst)}"
        lines = _insert_log(lines, f"- {stamp}: {it['title']}: {what}{_by(by)}.")
        # F43: done or let go, so what still hangs on to it elsewhere (her notes, reminders, watches, nudges, the
        # mail list's To check lines) goes with it; what only might belong to it is left and named once.
        cleared, records, unsure = [], [], []
        if dst["kind"] in ("done", "letgo") and src["kind"] not in ("done", "letgo") and os.environ.get(
                "HQ_TODO_SWEEP", "1") != "0":
            try:
                import loose_ends
                cleared, records, unsure = loose_ends.sweep(it["title"], p)
            except Exception:
                cleared, records, unsure = [], [], []
            for c in reversed(cleared):
                lines = _insert_log(lines, f"- {stamp}: {it['title']}: cleared with it: {c}{_by(by)}.")
        _write(p, before, lines, f"{it['title']}: {what}", records)
    out = {"ok": True, "said": f"{it['title']}: {what}.", "id": it["id"], "list": dst["key"]}
    if cleared or unsure:
        import loose_ends
        out["said"] += " " + loose_ends.said(cleared, unsure)
        out["cleared"], out["left"] = cleared, unsure
    return out


def split_items(text: str, kind: str) -> list[str]:
    """F40: several things at once give one item each: one per line on any list, and with commas on the groceries
    (outside brackets, so "beef (150 gram, lean)" stays one). A list marker at the start of a line is dropped."""
    parts = [re.sub(r"^\s*(?:[-*\u2022]|\d+[.)])\s+", "", x) for x in re.split(r"[\r\n]+", text or "")]
    if kind == "groceries":
        out = []
        for x in parts:
            out += re.split(r"[,;](?![^()]*\))", x)
        parts = out
    seen, items = set(), []
    for x in parts:
        x = re.sub(r"\s+", " ", x).strip()
        if x and x.lower() not in seen:
            seen.add(x.lower())
            items.append(x)
    return items


def add(lst_want: str, title: str, notes: str = "", deadline: str = "", type_: str = "", for_: str = "",
        by: str = "", p: Path | None = None) -> dict:
    p = p or path()
    dst = find_list(parse(p.read_text(encoding="utf8")), lst_want)
    many = split_items(title, dst["kind"])
    if len(many) > 1 or (many and dst["kind"] == "groceries"):
        return _add_many(dst, many, notes, deadline, type_, for_, by, p)
    title = re.sub(r"\s+", " ", title).strip()
    if not title:
        raise ValueError("nothing to add")
    with _lock:
        before = p.read_text(encoding="utf8")
        doc = parse(before)
        dst = find_list(doc, lst_want)
        vals = {"title": title, "notes": notes, "deadline": deadline, "type": type_, "for": for_,
                "status": "open" if dst["kind"] not in ("done", "letgo", "groceries") else "",
                "added": _now().strftime("%Y-%m-%d")}
        if dst["kind"] in ("done", "letgo"):
            vals["at"] = _now().strftime("%Y-%m-%d %H:%M")
        # the values HQ fills in itself only where the list has a column for them; what was said always stays
        has = {name for name in _FIELDS for c in dst["columns"][1:]
               if any(c.lower() == w or c.lower().startswith(w + " ") or c.lower().startswith(w + "(") for w in _FIELDS[name])}
        vals = {k: v for k, v in vals.items() if v and (k in ("title", "notes", "deadline", "type", "for") or k in has)}
        cells = _row_for(dst, vals, [])
        lines = list(doc["lines"])
        lines.insert(dst["table"][1], _row_line(cells))
        stamp = _now().strftime("%Y-%m-%d %H:%M")
        lines = _insert_log(lines, f"- {stamp}: added {title} to {_list_label(dst)}{_by(by)}.")
        _write(p, before, lines, f"added {title}")
    return {"ok": True, "said": f"Added {title} to {_list_label(dst)}.", "list": dst["key"]}


def _add_many(dst: dict, titles: list[str], notes: str, deadline: str, type_: str, for_: str, by: str, p: Path) -> dict:
    """Several items in one change (one undo, one log line). On the groceries, one that's already on the list stays
    as it is, and one on the ticked-off list goes back on instead of twice."""
    with _lock:
        before = p.read_text(encoding="utf8")
        doc = parse(before)
        dst = next(x for x in doc["lists"] if x["head"] == dst["head"])
        on = {it["title"].lower() for it in dst["items"]}
        off = next((x for x in doc["lists"] if x["kind"] == "grocoff"), None) if dst["kind"] == "groceries" else None
        back = {it["title"].lower(): it for it in (off["items"] if off else [])}
        lines = list(doc["lines"])
        added, again, had, rows = [], [], [], []
        for title in titles:
            if title.lower() in on:
                had.append(title)
                continue
            if title.lower() in back:
                it = back.pop(title.lower())
                vals = {"title": it["title"]}
                for name in _FIELDS:
                    v = _field(it["row"], name)
                    if v:
                        vals[name] = v
                rows.append(_row_for(dst, vals, []))
                lines[it["line"]] = None
                again.append(it["title"])
                continue
            vals = {"title": title, "notes": notes, "deadline": deadline, "type": type_, "for": for_,
                    "status": "open" if dst["kind"] not in ("done", "letgo", "groceries") else "",
                    "added": _now().strftime("%Y-%m-%d")}
            if dst["kind"] in ("done", "letgo"):
                vals["at"] = _now().strftime("%Y-%m-%d %H:%M")
            has = {name for name in _FIELDS for c in dst["columns"][1:]
                   if any(c.lower() == w or c.lower().startswith(w + " ") or c.lower().startswith(w + "(") for w in _FIELDS[name])}
            vals = {k: v for k, v in vals.items() if v and (k in ("title", "notes", "deadline", "type", "for") or k in has)}
            rows.append(_row_for(dst, vals, []))
            on.add(title.lower())
            added.append(title)
        if not rows:
            return {"ok": True, "said": f"Already on {_list_label(dst)}: {', '.join(had)}.", "list": dst["key"]}
        at = dst["table"][1]
        lines = lines[:at] + [_row_line(c) for c in rows] + lines[at:]
        lines = [l for l in lines if l is not None]
        stamp = _now().strftime("%Y-%m-%d %H:%M")
        bits = ([f"added {', '.join(added)}"] if added else []) + ([f"back on: {', '.join(again)}"] if again else [])
        what = "; ".join(bits)
        lines = _insert_log(lines, f"- {stamp}: {what} ({_list_label(dst)}){_by(by)}.")
        _write(p, before, lines, what)
    said = f"{what[0].upper()}{what[1:]} ({_list_label(dst)})." + (f" Already there: {', '.join(had)}." if had else "")
    return {"ok": True, "said": said, "list": dst["key"], "count": len(rows)}


def _ensure_ticked_list(p: Path) -> dict:
    """The groceries' ticked-off list, made right under the groceries with their columns when there's none yet."""
    with _lock:
        before = p.read_text(encoding="utf8")
        doc = parse(before)
        off = next((x for x in doc["lists"] if x["kind"] == "grocoff"), None)
        if off:
            return off
        gro = next((x for x in doc["lists"] if x["kind"] == "groceries"), None)
        if not gro:
            raise KeyError("There's no groceries list in the file.")
        lines = list(doc["lines"])
        at = gro["table"][1]
        block = ["", "## Groceries ticked off", "",
                 "Ticked off in the app or on a call; tick one back on to put it on the groceries again.", "",
                 _row_line(gro["columns"]), "|" + "|".join("---" for _ in gro["columns"]) + "|"]
        lines = lines[:at] + block + lines[at:]
        text = "\n".join(lines) + ("\n" if before.endswith("\n") else "")
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(text, encoding="utf8")
        os.replace(tmp, p)
        return next(x for x in parse(text)["lists"] if x["kind"] == "grocoff")


def tick(item: str, by: str = "", p: Path | None = None) -> dict:
    """F40: a grocery ticked off goes to the groceries' own ticked-off list, not to done."""
    p = p or path()
    doc = parse(p.read_text(encoding="utf8"))
    gro = [x for x in doc["lists"] if x["kind"] == "groceries"]
    want = item
    try:
        src, it = find_item({"lists": gro}, item)
        want = it["id"]
    except KeyError:
        src, it = find_item(doc, item)
        if src["kind"] == "grocoff":
            return {"ok": True, "said": f"{it['title']} is already ticked off.", "id": it["id"]}
        raise KeyError(f"{it['title']} isn't on the groceries.")
    dst = _ensure_ticked_list(p)
    return _move(p, want, dst, by=by, log_what="ticked off (groceries)")


def untick(item: str, by: str = "", p: Path | None = None) -> dict:
    """F40: back from the ticked-off list onto the groceries."""
    p = p or path()
    doc = parse(p.read_text(encoding="utf8"))
    off = [x for x in doc["lists"] if x["kind"] == "grocoff"]
    gro = next((x for x in doc["lists"] if x["kind"] == "groceries"), None)
    if not off or not gro:
        raise KeyError("Nothing is ticked off on the groceries.")
    src, it = find_item({"lists": off}, item)
    return _move(p, it["id"], gro, by=by, log_what="back on the groceries")


def done(item: str, note: str = "", by: str = "", p: Path | None = None) -> dict:
    p = p or path()
    doc = parse(p.read_text(encoding="utf8"))
    dst = next((x for x in doc["lists"] if x["kind"] == "done"), None)
    if not dst:
        raise KeyError("There's no done list in the file.")
    return _move(p, item, dst, note=note, by=by, log_what=f"done, moved to {_list_label(dst)}")


def letgo(item: str, why: str = "", by: str = "", p: Path | None = None) -> dict:
    p = p or path()
    doc = parse(p.read_text(encoding="utf8"))
    dst = next((x for x in doc["lists"] if x["kind"] == "letgo"), None)
    if not dst:
        raise KeyError("There's no let-go list in the file.")
    return _move(p, item, dst, note=why, by=by, log_what=f"let go, moved to {_list_label(dst)}")


def move(item: str, to: str, by: str = "", p: Path | None = None) -> dict:
    return _move(p or path(), item, to, by=by)


def order(item: str, place: int, by: str = "", p: Path | None = None) -> dict:
    """H231: the item to place N (1 is the top) in its own list; the row moves in the table, nothing else changes."""
    p = p or path()
    with _lock:
        before = p.read_text(encoding="utf8")
        doc = parse(before)
        lst, it = find_item(doc, item)
        items = lst["items"]
        n = max(1, min(int(place), len(items)))
        now = items.index(it) + 1
        if n == now:
            return {"ok": True, "said": f"{it['title']} is already at place {n}.", "id": it["id"], "list": lst["key"]}
        lines = list(doc["lines"])
        row = lines[it["line"]]
        rest = [x for x in items if x is not it]
        # the line it goes before (or after the last one), counted before its own line is taken out
        at = rest[n - 1]["line"] if n - 1 < len(rest) else rest[-1]["line"] + 1
        del lines[it["line"]]
        lines.insert(at - (1 if at > it["line"] else 0), row)
        stamp = _now().strftime("%Y-%m-%d %H:%M")
        what = f"to place {n} of {len(items)} on {_list_label(lst)}"
        lines = _insert_log(lines, f"- {stamp}: {it['title']}: {what}{_by(by)}.")
        _write(p, before, lines, f"{it['title']}: {what}")
    return {"ok": True, "said": f"{it['title']}: {what}.", "id": it["id"], "list": lst["key"]}


def rename(item: str, title: str, by: str = "", p: Path | None = None) -> dict:
    """H231: a new name; the rest of the row stays. Not to a name another item on the same list already has."""
    p = p or path()
    new = re.sub(r"\s+", " ", title or "").strip()
    if not new:
        raise ValueError("a new name is needed")
    with _lock:
        before = p.read_text(encoding="utf8")
        doc = parse(before)
        lst, it = find_item(doc, item)
        old = it["title"]
        if new == old:
            return {"ok": True, "said": f"It's already called {old}.", "id": it["id"], "list": lst["key"]}
        if any(x is not it and x["title"].lower() == new.lower() for x in lst["items"]):
            raise ValueError(f"{new} is already on {_list_label(lst)}.")
        cells = list(it["cells"])
        cells[0] = new
        r = it["row"]
        had = details_for(old + " " + " ".join(_RENAMED.findall(_field(r, "notes"))), doc["details"])
        if had and len(details_for(new, doc["details"])) < len(had):
            note_at = next((i for i, c in enumerate(lst["columns"]) if i and c.lower().split(" ")[0] in ("notes", "why")),
                           len(lst["columns"]) - 1)
            if note_at and "Renamed from: " + old + "." not in cells[note_at]:
                cells[note_at] = " ".join(x for x in (cells[note_at], f"Renamed from: {old}.") if x)
        lines = list(doc["lines"])
        lines[it["line"]] = _row_line(cells)
        stamp = _now().strftime("%Y-%m-%d %H:%M")
        lines = _insert_log(lines, f"- {stamp}: {old}: renamed to {new} ({_list_label(lst)}){_by(by)}.")
        _write(p, before, lines, f"{old}: renamed to {new}")
        nid = next((x["id"] for l in parse("\n".join(lines))["lists"] if l["head"] == lst["head"]
                    for x in l["items"] if x["line"] == it["line"]), "")
    return {"ok": True, "said": f"{old}: renamed to {new}.", "id": nid, "list": lst["key"]}


def undo() -> dict:
    """The last change made through here, put back, only when the file is still as that change left it."""
    with _lock:
        try:
            u = json.loads(_undo_file().read_text(encoding="utf8"))
        except (OSError, ValueError):
            return {"ok": False, "said": "Nothing to undo."}
        p = Path(u["file"])
        try:
            now_text = p.read_text(encoding="utf8")
        except OSError:
            return {"ok": False, "said": "The list isn't there."}
        if hashlib.sha1(now_text.encode()).hexdigest() != u.get("after_sha"):
            return {"ok": False, "said": "The list changed since, so it can't be undone from here."}
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(u["before"], encoding="utf8")
        os.replace(tmp, p)
        _undo_file().unlink(missing_ok=True)
    back = 0
    if u.get("swept"):
        try:
            import loose_ends  # F43: what was cleared with it comes back too
            back = loose_ends.put_back(u["swept"], p)
        except Exception:
            back = 0
    return {"ok": True, "said": f"Undone: {u.get('what', 'the last change')}." + (
        f" Put back what was cleared with it ({back})." if back else "")}


# ---- for a call ------------------------------------------------------------------------------------------------

def about(item_id: str, p: Path | None = None) -> dict | None:
    """One item by its id, for a call started from it in the app."""
    if not item_id:
        return None
    for lst in read(p).get("lists", []):
        for it in lst["items"]:
            if it["id"] == item_id:
                return {**it, "kind": "todo", "list": lst["name"], "list_num": lst["num"]}
    return None


def when_line(it: dict) -> str:
    return f"{it.get('title', '')} (to-do, {it.get('list', '')})".replace("\n", " ")


def greetings(it: dict, name: str = "") -> list[str]:
    """The call system's greeting on a call about a to-do item (spoken, so plain words only). Wording Claude's choice."""
    title = re.sub(r"[^\w\s,.'&:/-]", "", it.get("title", "")).strip() or "this one"
    title = title.split(":")[0].strip() or title
    n = f", {name}" if name else ""
    return [f"Hi{n}. About {title}. Where are you with it?", f"Hey{n}. Let's look at {title}. What's on your mind?"]


def call_note(it: dict, user: str = "the user") -> str:
    lines = [f"Item: {it.get('title', '')}", f"List: {it.get('list', '')}"]
    for c, v in it.get("fields") or []:
        lines.append(f"{c}: {v}")
    for d in it.get("details") or []:
        lines.append(f"In their own words: {d}")
    return (
        f"{user} started this call by tapping an item on the to-do list in HQ, so this call is about it. The call "
        "system greets them by naming it; pick it up from their answer, without reading it all back, and help with "
        "whatever it needs: the next small step, a time for it in the calendar, moving it to another list, letting it "
        "go or ticking it off (the to-do list's own commands, as the call rules say).\n"
        "<todo>\n" + "\n".join(lines) + "\n</todo>\n"
    )


def summary(p: Path | None = None) -> str:
    """The list in a few lines: each list with how many are on it and the first few, the matrix first."""
    d = read(p)
    if d.get("missing"):
        return f"There's no to-do list yet ({d['file']} in the workspace)."
    order = {"commit": 0, "q2": 1, "q1": 2, "q3": 3, "q4": 4, "other": 5, "wish": 6, "groceries": 7, "grocoff": 8, "letgo": 9, "done": 10}
    out = []
    for lst in sorted(d["lists"], key=lambda x: order.get(x["kind"], 5)):
        items = lst["items"]
        label = (f"{lst['num']}. " if lst["num"] is not None else "") + lst["name"]
        if lst["kind"] == "grocoff":
            out.append(f"{label}: {len(items)}" + ("" if not items else ": " + "; ".join(
                f"{it['title']} #{it['id']}" for it in sorted(items, key=lambda x: x["title"].lower()))))
            continue
        if lst["kind"] in ("done", "letgo"):
            out.append(f"{label}: {len(items)}" + (f", latest {items[0]['title']}" if items else ""))
            continue
        out.append(f"{label}: {len(items)}" + ("" if not items else ": " + "; ".join(
            it["title"] + (f" [{it['deadline']}]" if it["deadline"] else "") + (f" ({it['status']})" if it["status"] and it["status"] != "open" else "")
            + f" #{it['id']}" for it in items)))
    if d.get("mail"):
        out.append(f"Very important mail waiting for an answer: {len(d['mail'])}")
    return "\n".join(out)


def _opt(args: list[str], name: str) -> str:
    if name in args:
        i = args.index(name)
        v = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
        return v
    return ""


def main(argv: list[str]) -> int:
    args = list(argv)
    # H203: on the backup HQ, a change to the list goes to the main one, which writes it (role.WRITES), like the queue.
    if args and args[0] in ("add", "done", "letgo", "move", "tick", "untick", "order", "rename", "undo") and not os.environ.get("HQ_ROLE_HERE"):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "routine"))
        import role
        if role.is_backup():
            return role.forward("todo", list(argv))
    by = _opt(args, "--by")
    cmd = args[0] if args else "summary"
    try:
        if cmd == "summary":
            print(summary())
        elif cmd == "json":
            print(json.dumps(read(), ensure_ascii=False, indent=1))
        elif cmd == "add" and len(args) >= 3:
            notes, deadline, type_, for_ = (_opt(args, "--notes"), _opt(args, "--deadline"), _opt(args, "--type"),
                                            _opt(args, "--for"))
            print(add(args[1], args[2], notes=notes, deadline=deadline, type_=type_, for_=for_, by=by)["said"])
        elif cmd == "done" and len(args) >= 2:
            print(done(args[1], args[2] if len(args) > 2 else "", by=by)["said"])
        elif cmd == "letgo" and len(args) >= 2:
            print(letgo(args[1], args[2] if len(args) > 2 else "", by=by)["said"])
        elif cmd == "move" and len(args) >= 3:
            print(move(args[1], args[2], by=by)["said"])
        elif cmd == "tick" and len(args) >= 2:
            print(tick(args[1], by=by)["said"])
        elif cmd == "untick" and len(args) >= 2:
            print(untick(args[1], by=by)["said"])
        elif cmd == "order" and len(args) >= 3 and args[2].strip().isdigit():
            print(order(args[1], int(args[2]), by=by)["said"])
        elif cmd == "rename" and len(args) >= 3:
            print(rename(args[1], args[2], by=by)["said"])
        elif cmd == "undo":
            print(undo()["said"])
        else:
            print(__doc__.strip())
            return 2
    except (KeyError, ValueError) as e:
        print(str(e).strip("'\""))
        return 1
    except OSError as e:
        print(f"Couldn't read or write the list: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
