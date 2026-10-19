"""F43: when a to-do item is done or let go, what still hangs on to it elsewhere goes with it (19 October 2026).

In the user's words, on the call at 10:57: "Didn't we fix the flex one yesterday? Why do you keep bringing it up?
Donna also kept bringing it up and I already told her as well." and "Because the structure should have been set up
in such a way that this would not be brought up." His condition: "If you think this doesn't break other things. That
is very important."

An item lives in more places than the list: the direct-line agent's own notes, her reminders, watches and nudges
(routine/pings.py), and lines on the mail list (inbox.md). todo.done and todo.letgo call sweep(), which looks at all
of them and sorts each into:

  clear   it clearly belongs to that item: tagged with it (pings.py --item, the "(to-do: NAME)" a note carries), or
          the mail check named it ('about the open item "NAME"'), or it says the item's whole name (a name of at least
          three real words, so a short name never takes a note with it on a guess). Cleared: the note removed, the
          reminder taken off, the watch ended quietly, the nudge done, the To check line removed.
  unsure  it shares words with the item but doesn't name it: left as it is, and named once in the answer, so the
          agent asks ("she still has a note about X, clear it too?"); never cleared on a guess.

A Very important mail line is never cleared here, only named: it goes when the user says so, as before. Every thing
cleared gets its own line in the list's log, and todo.undo puts all of it back (the records ride in the list's undo).

With HQ_TODO set (a test's own list) the agent's pings are only touched when HQ_DIRECT_DIR is set too, so a test
never clears the real ones. The mail list is the one next to the list (HQ_INBOX for a test).
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # HQ
STOP = set("""about after again also before being from have here into just like make more need needs only over some
than that their them then there these they this those very want what when where which while with without would your
open item done list mail check still back keep sure""".split())
MIN_NAME_WORDS = 3  # a name this long, said whole, is clearly that item


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", str(s).lower()).split())


def _words(s: str) -> set[str]:
    return {w for w in _norm(s).split() if len(w) >= 4 and w not in STOP and not w.isdigit()}


def judge(title: str, text: str, tagged: str = "") -> str:
    """'clear', 'unsure' or '' for one thing that may belong to the item TITLE."""
    t, x = _norm(title), _norm(text)
    if not t:
        return ""
    if tagged and _norm(tagged) == t:
        return "clear"
    low, tl = " ".join(str(text).lower().split()), " ".join(str(title).lower().split())
    if f'item "{tl}"' in low or f"(to-do: {tl})" in low:
        return "clear"
    if len(_words(title)) >= MIN_NAME_WORDS and f" {t} " in f" {x} ":
        return "clear"
    need = _words(title)
    common = need & _words(text)
    subject = _words(title.split(":", 1)[0]) if ":" in title else set()
    if common and len(common) >= min(2, len(need)) and (not subject or subject & common):
        return "unsure"  # "Subject: what to do": a maybe needs the subject too, not just two everyday words
    return ""


# ---- where else it lives --------------------------------------------------------------------------------------

def _pings():
    sys.path.insert(0, str(ROOT / "routine"))
    import pings  # noqa: E402
    return pings


def _pings_ok() -> bool:
    return bool(os.environ.get("HQ_DIRECT_DIR")) or not os.environ.get("HQ_TODO")


def inbox_path(todo_file: Path) -> Path:
    return Path(os.environ.get("HQ_INBOX") or todo_file.parent / "inbox.md")


def _short(s: str, n: int = 90) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def _inbox_lines(p: Path) -> list[tuple[str, str, str]]:
    """(section, heading, line) for every mail line: section 'vi' or 'check'."""
    try:
        lines = p.read_text(encoding="utf8").splitlines()
    except OSError:
        return []
    out, sec, head = [], "", ""
    for l in lines:
        if l.startswith("## "):
            sec = {"## very important": "vi", "## to check": "check"}.get(l.strip().lower(), "")
            head = ""
        elif l.startswith("### "):
            head = l
        elif sec and l.startswith("- "):
            out.append((sec, head, l))
    return out


def look(title: str, todo_file: Path) -> list[dict]:
    """Everything that may belong to the item, each {'where', 'say', 'verdict', …} with what clearing needs."""
    found = []
    if _pings_ok():
        try:
            pg = _pings()
            who = pg.agent_name()
            s = pg.read()
            now = time.time()
            for it in pg.her_notes():
                v = judge(title, it["text"])
                if v:
                    found.append({"where": "note", "id": it["id"], "text": it["text"], "verdict": v,
                                  "say": f"{who}'s note \"{_short(it['text'])}\""})
            for r in s["reminders"]:
                if r.get("sent"):
                    continue
                v = judge(title, r.get("text", ""), r.get("item", ""))
                if v:
                    found.append({"where": "reminder", "n": r.get("n"), "verdict": v,
                                  "say": f"{who}'s reminder for {r.get('at', '')}, \"{_short(r.get('text', ''))}\""})
            for w in pg.open_watches(s=s, now=now):
                if w.get("alert"):
                    continue
                v = judge(title, w.get("what", ""), w.get("item", ""))
                if v:
                    found.append({"where": "watch", "n": w.get("n"), "verdict": v,
                                  "say": f"{who}'s watch on the {w.get('kind', '')} for \"{_short(w.get('what', ''))}\""})
            for x in pg.open_nudges(s):
                v = judge(title, x.get("text", "") + " " + x.get("reason", ""), x.get("item", ""))
                if v:
                    found.append({"where": "nudge", "n": x.get("n"), "verdict": v,
                                  "say": f"{who}'s nudge \"{_short(x.get('text', ''))}\""})
        except Exception:
            pass  # her things can't be read: the list's change still counts
    for sec, head, line in _inbox_lines(inbox_path(todo_file)):
        parts = [x.strip() for x in line[2:].split(" · ")]
        v = judge(title, line)
        if not v:
            continue
        say = "the mail " + (f"\"{_short(parts[2], 60)}\"" if len(parts) > 2 else f"\"{_short(line[2:], 60)}\"")
        if sec == "vi":
            found.append({"where": "vi", "verdict": "unsure", "say": say + " (very important; it stays until you say so)"})
        else:
            found.append({"where": "mail", "line": line, "heading": head, "verdict": v, "say": say + " under To check"})
    return found


# ---- clearing, and putting back -------------------------------------------------------------------------------

def _edit_pings(change) -> None:
    pg = _pings()
    with pg._Lock():
        s = pg.read()
        change(s)
        pg._write(s)


def _clear_one(f: dict, todo_file: Path) -> dict | None:
    """Clears F; returns the record undo needs, or None when it was gone already."""
    where = f["where"]
    if where == "note":
        pg = _pings()
        if pg._notes().clear(f["id"], pg.notes_file()):
            return {"where": "note", "text": f["text"]}
        return None
    if where in ("reminder", "watch", "nudge"):
        got = {}
        stamp = time.strftime("%Y-%m-%d %H:%M")

        def change(s):
            if where == "reminder":
                keep = []
                for r in s["reminders"]:
                    if int(r.get("n") or 0) == int(f["n"]) and not r.get("sent") and not got:
                        got["was"] = r
                    else:
                        keep.append(r)
                s["reminders"] = keep
            elif where == "watch":
                w = next((w for w in s["watches"] if int(w.get("n") or 0) == int(f["n"]) and not w.get("ended")), None)
                if w:
                    w["ended"] = {"at": stamp, "why": "its to-do item is done", "texted": "quiet"}
                    got["n"] = w["n"]
            else:
                x = next((x for x in s.get("nudges") or [] if int(x.get("n") or 0) == int(f["n"]) and not x.get("done")),
                         None)
                if x:
                    x["done"] = stamp
                    x["done_with_item"] = True
                    got["n"] = x["n"]
        _edit_pings(change)
        return {"where": where} | got if got else None
    if where == "mail":
        p = inbox_path(todo_file)
        text = p.read_text(encoding="utf8")
        lines = text.splitlines()
        if f["line"] not in lines:
            return None
        lines.remove(f["line"])
        _write_text(p, "\n".join(lines) + ("\n" if text.endswith("\n") else ""))
        return {"where": "mail", "line": f["line"], "heading": f.get("heading", "")}
    return None


def _write_text(p: Path, text: str) -> None:
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(text, encoding="utf8")
    os.replace(tmp, p)


def sweep(title: str, todo_file: Path) -> tuple[list[str], list[dict], list[str]]:
    """Clears what clearly belongs to TITLE. Returns (what was cleared, to say and log; the undo records; what was
    left because it only might belong to it, to name once)."""
    cleared, records, unsure = [], [], []
    for f in look(title, todo_file):
        if f["verdict"] != "clear":
            unsure.append(f["say"])
            continue
        try:
            rec = _clear_one(f, todo_file)
        except Exception:
            rec = None
            unsure.append(f["say"])
        if rec:
            cleared.append(f["say"])
            records.append(rec)
    return cleared, records, unsure


def put_back(records: list[dict], todo_file: Path) -> int:
    """Undo: every record put back where it was. Returns how many."""
    n = 0
    for rec in records:
        try:
            where = rec["where"]
            if where == "note":
                if _pings().note_add(rec["text"]):
                    n += 1
            elif where == "reminder":
                was = rec["was"]

                def change(s, was=was):
                    if not any(int(r.get("n") or 0) == int(was.get("n") or 0) for r in s["reminders"]):
                        s["reminders"].append(was)
                _edit_pings(change)
                n += 1
            elif where == "watch":
                def change(s, k=rec["n"]):
                    w = next((w for w in s["watches"] if int(w.get("n") or 0) == int(k)), None)
                    if w and (w.get("ended") or {}).get("why") == "its to-do item is done":
                        w.pop("ended", None)
                _edit_pings(change)
                n += 1
            elif where == "nudge":
                def change(s, k=rec["n"]):
                    x = next((x for x in s.get("nudges") or [] if int(x.get("n") or 0) == int(k)), None)
                    if x and x.get("done_with_item"):
                        x.pop("done", None)
                        x.pop("done_with_item", None)
                _edit_pings(change)
                n += 1
            elif where == "mail":
                p = inbox_path(todo_file)
                text = p.read_text(encoding="utf8")
                lines = text.splitlines()
                if rec["line"] in lines:
                    continue
                head = rec.get("heading") or ""
                at = next((i for i, l in enumerate(lines) if head and l == head), None)
                if at is not None:
                    at += 2 if at + 1 < len(lines) and not lines[at + 1].strip() else 1
                    lines.insert(at, rec["line"])
                else:
                    sec = next((i for i, l in enumerate(lines) if l.strip().lower() == "## to check"), None)
                    if sec is None:
                        lines += ["", "## To check"]
                        sec = len(lines) - 1
                    lines[sec + 1:sec + 1] = [""] + ([head, ""] if head else []) + [rec["line"]]
                _write_text(p, "\n".join(lines) + ("\n" if text.endswith("\n") else ""))
                n += 1
        except Exception:
            continue
    return n


def said(cleared: list[str], unsure: list[str]) -> str:
    out = []
    if cleared:
        out.append("Cleared with it: " + "; ".join(cleared) + ".")
    if unsure:
        out.append("Left, since it may be about it: " + "; ".join(unsure) + ". Clear it too?")
    return " ".join(out)
