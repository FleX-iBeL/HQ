"""The briefing an agent starts with (Fable, 27 October 2026; the backend switch `briefing`).

An agent should start the way a good colleague starts the day: what's in her head is small and current, the files
are on her desk and she opens the one she needs. Before this, a call or a text started with her files whole
(Pepper about 367 KB, some 90,000 tokens, before her first word; every text the same again). The briefing is made
here, every minute, without Claude, from the files; it's 15 to 30 KB: today and tomorrow in the calendar, the
very important mail, the open commitments and the last hours' notes, the open to-do items one line each, the open
nudges, the game's score, the map's status lines; for a build call the planning's status block, the open jobs and
the open items. Written to HQ's `.status/briefing-<context>.md` (day, coach, build), one per role, never by hand,
never committed. The rest of the files is the library: `briefing.py layer N` prints one layer of the map,
`todo.py show WORDS` one item with its details, `sprint.py show LABEL` one planning row.

    python3 routine/briefing.py [day|coach|build]    print that briefing (day without an argument)
    python3 routine/briefing.py write                write all three to .status (the routine, every minute)
    python3 routine/briefing.py fresh CONTEXT        the written one when it's recent, else made now (the call)
    python3 routine/briefing.py layer N              one layer of the map, whole (the library)
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "app"))
import hqpaths  # noqa: E402

FOLDER = Path(hqpaths.FOLDER)
STATUS = Path(os.environ.get("HQ_STATUS_DIR") or (HERE.parent / ".status"))
CONTEXTS = ("day", "coach", "build")
RECENT_HOURS = 3
LINE_MOST = 300  # a note's first line, cut
ITEMS_MOST = 120
EVENTS_MOST = 40


def _read(rel: str, folder: Path | None = None) -> str:
    try:
        return ((folder or FOLDER) / rel).read_text(encoding="utf8")
    except OSError:
        return ""


def _section(text: str, heading: str) -> str:
    """The lines of a `## heading` section (without the heading), up to the next `## ` or `# `."""
    m = re.search(rf"^## {re.escape(heading)}\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^#{1,2} ", rest, re.M)
    return rest[:n.start()] if n else rest


def _cut(s: str, most: int = LINE_MOST) -> str:
    s = " ".join(s.split())
    return s if len(s) <= most else s[:most - 1].rsplit(" ", 1)[0] + "…"


# -- the parts -------------------------------------------------------------------------------------------------------

def calendar_part(now: dt.datetime, folder: Path | None = None) -> str:
    """Today and tomorrow from HQ's copy of the calendar (agenda.py's file), one line an appointment."""
    p = Path(os.environ.get("HQ_CALENDAR_FILE") or ((folder or FOLDER) / "HQ" / "calendar.json"))
    try:
        s = json.loads(p.read_text(encoding="utf8"))
    except (OSError, ValueError):
        return ""
    events = s.get("events") or []
    out = []
    for d, name in ((now.date(), "Today"), (now.date() + dt.timedelta(days=1), "Tomorrow")):
        lines = []
        for e in events:
            st = str(e.get("start") or "")
            if not st.startswith(d.isoformat()):
                continue
            if e.get("all_day"):
                when = "all day"
            else:
                en = str(e.get("end") or "")
                when = st[11:16] + ("–" + en[11:16] if len(en) >= 16 else "")
            where = f" at {e['where']}" if e.get("where") else ""
            free = " (free)" if e.get("free") else ""
            cal = f" [{e['calendar']}]" if e.get("calendar") and e["calendar"] not in ("Mine", "Main") else ""
            lines.append(f"- {when}: {e.get('title', '')}{where}{free}{cal}")
            if len(lines) >= EVENTS_MOST:
                break
        out.append(f"{name}, {d:%A %-d %B}:\n" + ("\n".join(lines) if lines else "- nothing in the calendar"))
    looked = s.get("looked")
    age = f" (the calendar as read {int((now.timestamp() - looked) // 60)} minutes ago)" if looked else ""
    return "The calendar" + age + ":\n" + "\n\n".join(out)


def mail_part(folder: Path | None = None) -> str:
    text = _read("inbox.md", folder)
    vi = [l for l in _section(text, "Very important").splitlines() if l.startswith("- ")]
    check = len([l for l in _section(text, "To check").splitlines() if l.startswith("- ")])
    out = "Very important mail, waiting for his answer (name it at the start, every time):\n" + \
          ("\n".join(_cut(l, 600) for l in vi) if vi else "- none")
    out += f"\n\nUnder To check on the mail list: {check} smaller mails (inbox.md, read when he asks)."
    return out


def commitments_part(now: dt.datetime, folder: Path | None = None) -> str:
    text = _read("coaching/log.md", folder)
    open_ = [l for l in _section(text, "Open commitments").splitlines() if l.startswith("- ")]
    older = [l for l in _section(text, "Open commitments (older)").splitlines() if l.startswith("- ")]
    out = ["Open commitments (the coaching log; the full note is there):\n" +
           ("\n".join(_cut(l, 400) for l in open_) if open_ else "- none")]
    if older:
        out.append(f"Older open commitments: {len(older)} more under 'Open commitments (older)' in coaching/log.md.")
    # the last hours' notes: their heading and first line
    recent = []
    first = now - dt.timedelta(hours=RECENT_HOURS)
    for m in re.finditer(r"^## (\d{4}-\d{2}-\d{2})(?: (\d{1,2}):(\d{2}))?(?: · (.*))?$", text, re.M):
        try:
            t = dt.datetime.fromisoformat(m.group(1))
            if m.group(2):
                t = t.replace(hour=int(m.group(2)), minute=int(m.group(3)))
        except ValueError:
            continue
        if t < first:
            continue
        body = text[m.end():]
        n = re.search(r"^## ", body, re.M)
        body = body[:n.start()] if n else body
        line = next((l for l in body.splitlines() if l.strip()), "")
        recent.append(f"- {t:%H:%M} {m.group(4) or ''}: {_cut(line.lstrip('- '), 500)}")
    if recent:
        out.append(f"The last {RECENT_HOURS} hours' notes (the whole note is in coaching/log.md; older ones in "
                   f"coaching/log-archive.md):\n" + "\n".join(recent[:20]))
    return "\n\n".join(out)


def todo_part(folder: Path | None = None) -> str:
    try:
        import todo
        d = todo.read((folder or FOLDER) / "challenges.md")
    except Exception as e:
        return f"The to-do list couldn't be read: {e!r}"
    names = {"commit": "promised to others", "q1": "important and urgent", "q2": "important, not urgent",
             "q3": "urgent, not important", "q4": "not urgent, not important", "wish": "the shopping wishlist",
             "groceries": "the groceries"}
    out, n = [], 0
    for lst in d.get("lists", []):
        if lst["kind"] not in names:
            continue
        items = lst.get("items") or []
        if not items:
            continue
        lines = []
        for it in items:
            bits = []
            if it.get("deadline"):
                bits.append(f"by {it['deadline']}")
            if it.get("status") and it["status"] not in ("open", ""):
                bits.append(it["status"])
            if it.get("planned") and it["planned"].get("short"):
                bits.append("planned " + it["planned"]["short"])
            if it.get("for"):
                bits.append("for " + it["for"])
            lines.append(f"- {it['title']}" + (f" ({'; '.join(bits)})" if bits else ""))
            n += 1
        out.append(f"{names[lst['kind']]} ({len(items)}):\n" + "\n".join(lines[:ITEMS_MOST]))
    head = (f"The to-do list, {n} open items, one line each (an item's own words and details: python3 "
            f"\"{HERE.parent / 'app' / 'todo.py'}\" show \"a few words of its name\"; the done and let-go items are in "
            f"challenges.md and challenges-archive.md):")
    return head + "\n\n" + "\n\n".join(out)


def nudges_part() -> str:
    try:
        import pings
        s = pings.read()
        ns = pings.open_nudges(s)
        rem = [r for r in s.get("reminders") or [] if not r.get("sent")]
    except Exception:
        return ""
    if not ns and not rem:
        return ""
    out = []
    if ns:
        out.append("Open nudges (she keeps nudging until he says done):\n" +
                   "\n".join(f"- {x.get('text', '')} ({x.get('reason', '')})" for x in ns[:12]))
    if rem:
        out.append("Reminders still to send:\n" +
                   "\n".join(f"- {r.get('when', r.get('at', ''))}: {_cut(str(r.get('text', '')), 160)}" for r in rem[:12]))
    return "\n\n".join(out)


def games_part() -> str:
    try:
        import games
        lines = games.score_lines()
    except Exception:
        return ""
    return "The six-week game:\n" + "\n".join("- " + l for l in lines) if lines else ""


def map_part(folder: Path | None = None) -> str:
    text = _read("map.md", folder)
    if not text:
        return ""
    out = []
    m = re.search(r"^Name: (.*)$", text, re.M)
    if m:
        out.append("The vision's name: " + _cut(m.group(1), 200))
    for mm in re.finditer(r"^Theme: (.*)$|^The year runs (.*?)\(", text, re.M):
        out.append(("Theme: " + mm.group(1)) if mm.group(1) else ("The year runs " + mm.group(2).strip()))
    layers = [(int(h.group(1)), h.group(2), h.start()) for h in re.finditer(r"^## (\d+)\. (.+)$", text, re.M)]
    for i, (n, name, at) in enumerate(layers):
        end = layers[i + 1][2] if i + 1 < len(layers) else len(text)
        st = re.search(r"^Status: (.*)$", text[at:end], re.M)
        out.append(f"- {n}. {name}: {_cut(st.group(1), 240) if st else 'no status line'}")
    return ("The map (map.md): its six layers and where each stands; a whole layer is python3 \""
            f"{HERE / 'briefing.py'}\" layer N:\n" + "\n".join(out))


def planning_part(folder: Path | None = None) -> str:
    """The status block, the team's open jobs and the open planning items (the clean-up's `_planning`)."""
    try:
        import quick_context
        return quick_context._planning(folder or FOLDER)
    except Exception as e:
        return f"The planning couldn't be read: {e!r}"


def situation_part(folder: Path | None = None) -> str:
    text = _read("current-situation.md", folder)
    return ("Where he stands now (current-situation.md, whole):\n\n" + text.strip()) if text else ""


# -- the briefing ---------------------------------------------------------------------------------------------------

def build(context: str = "day", now: dt.datetime | None = None, folder: Path | None = None) -> str:
    now = now or dt.datetime.now()
    head = (f"The briefing, written by HQ's routine at {now:%A %-d %B %Y, %H:%M} from the files (never by hand; it's "
            f"what's current, not everything: the files are the library, open one when the turn needs it).")
    parts = [head]
    if context == "build":
        parts.append(planning_part(folder))
    else:
        parts += [calendar_part(now, folder), mail_part(folder), commitments_part(now, folder), todo_part(folder),
                  nudges_part(), games_part()]
        if context == "coach":
            parts.append(map_part(folder))
        parts.append(situation_part(folder))
    return "\n\n".join(p for p in parts if p).rstrip() + "\n"


def path(context: str) -> Path:
    return STATUS / f"briefing-{context}.md"


def write(now: dt.datetime | None = None, folder: Path | None = None) -> list[str]:
    STATUS.mkdir(parents=True, exist_ok=True)
    done = []
    for c in CONTEXTS:
        text = build(c, now, folder)
        p = path(c)
        try:
            if p.exists() and p.read_text(encoding="utf8") == text:
                continue
        except OSError:
            pass
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(text, encoding="utf8")
        os.replace(tmp, p)
        done.append(c)
    return done


def fresh(context: str, most_age_s: int = 300, folder: Path | None = None) -> str:
    """The written briefing when it's recent, else one made now (a fresh install, a test, a routine that stopped)."""
    p = path(context)
    try:
        if dt.datetime.now().timestamp() - p.stat().st_mtime <= most_age_s:
            return p.read_text(encoding="utf8")
    except OSError:
        pass
    return build(context, folder=folder)


def layer(n: int, folder: Path | None = None) -> str:
    text = _read("map.md", folder)
    heads = [(int(h.group(1)), h.start()) for h in re.finditer(r"^## (\d+)\. (.+)$", text, re.M)]
    for i, (k, at) in enumerate(heads):
        if k == n:
            end = heads[i + 1][1] if i + 1 < len(heads) else len(text)
            return text[at:end].rstrip() + "\n"
    return f"No layer {n} in map.md (the layers: {', '.join(str(k) for k, _ in heads)})."


def main(argv: list[str]) -> int:
    if not argv or argv[0] in CONTEXTS:
        sys.stdout.write(build(argv[0] if argv else "day"))
        return 0
    if argv[0] == "fresh" and len(argv) == 2 and argv[1] in CONTEXTS:
        sys.stdout.write(fresh(argv[1]))
        return 0
    if argv[0] == "write":
        w = write()
        print("Written: " + (", ".join(w) if w else "nothing changed"))
        return 0
    if argv[0] == "layer" and len(argv) == 2 and argv[1].isdigit():
        sys.stdout.write(layer(int(argv[1])))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
