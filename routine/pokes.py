#!/usr/bin/env python3
"""The weekly score per agent, computed by the routine without Claude (H298, piece 5, 29 October 2026).

The handbook: "HQ computes your score every week from what it already sees, writes it in your ledger, and your bigger
session reads it first. One measure is shared by all three, and it's the one that matters: how often he had to poke,
chase or correct you. Down is good." The point of computing it: the score must not put the user to work telling
each agent whether she helped; it has to come from what HQ already sees.

The pokes, counted from his own lines (the handbook's part four): his texts to an agent on her line that ask after
something she owns (a status question: is it done, did you, where is, what happened to), his corrections (the word
"rule", a "no" or "wrong" right after her message) and calls with her shorter than five minutes that end on such a
question. Rough but free; it only has to move in the right direction. The keyword lists are below (KEYWORDS), tuned
in the monthly review. Then each agent's own measures from what HQ already has: the to-do list, the mail list, the
calendar's ticks and X's, the game, the coaching check-ins, the planning's Ready marks, the finished jobs' estimates,
the QA marks. A measure that can't be read on this HQ says so ("not measured yet") instead of a made-up number.

    python3 routine/pokes.py AGENT [--days 7]      her score for the last week, in plain lines
    python3 routine/pokes.py AGENT --json
Standard library only (the readers it uses are HQ's own, each in its try).
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
SHORT_CALL_MIN = 5
ACTED_HOURS = 24  # a text of hers he answered within this is one he acted on

# Tuned in the monthly review (routine/cycles.py review): what in his own lines counts as a poke.
KEYWORDS = {
    "status": [r"\bis (it|that|this) (done|ready|finished|fixed|in|planned)\b", r"\bdid you (do|send|put|fix|check|plan|run|add|move)\b",
               r"\bwhere('s| is| are) (the|my|it)\b", r"\bwhat happened (to|with)\b", r"\bis (the )?(job|team|it|that) (stuck|done|running|finished)\b",
               r"\bany (news|update)\b", r"\bstill (waiting|running|open|not done)\b", r"\bdid the team\b", r"\bhow far (is|are|did)\b",
               r"\bstatus\b", r"\bdid (it|that) (run|work|go|happen)\b", r"\bhas (it|that) (run|been done|happened)\b",
               r"\bwhen (is|will) (it|that) (be )?(done|ready)\b", r"\bis (it|that) (on|in) (the|my) (list|calendar|planning)\b"],
    "correction": [r"^\W*(no|nope|wrong|not that|that'?s wrong|that'?s not (right|it|what i))\b", r"\brule\b", r"\bwhat is this\b",
                   r"\bnot what i (said|asked|meant)\b", r"\bthis is (wrong|not acceptable)\b", r"\byou (got|read|did) (it|that|this) wrong\b"],
}
_STATUS = re.compile("|".join(KEYWORDS["status"]), re.I)
_CORRECTION = re.compile("|".join(KEYWORDS["correction"]), re.I)


# -- where each agent's line is ------------------------------------------------------------------------------------

def line_dir(agent_id: str, folder: Path | None = None) -> Path:
    """Her line's folder: Moneypenny's team line, Pepper's coaching line, else the direct line (Donna's)."""
    base = folder or FOLDER
    if agent_id == "moneypenny":
        return Path(os.environ.get("HQ_TEAM_LINE_DIR") or base / "HQ" / "team-line")
    if agent_id == "pepper":
        return Path(os.environ.get("HQ_COACHING_LINE") or base / "HQ" / "coaching-line")
    return Path(os.environ.get("HQ_DIRECT_DIR") or base / "HQ" / "direct-line")


def _thread(agent_id: str, folder: Path | None = None) -> list[dict]:
    out = []
    try:
        for l in (line_dir(agent_id, folder) / "thread.jsonl").read_text(encoding="utf8").splitlines():
            try:
                m = json.loads(l)
            except ValueError:
                continue
            if isinstance(m, dict) and m.get("text"):
                out.append(m)
    except OSError:
        pass
    return out


# -- the pokes ------------------------------------------------------------------------------------------------------

def text_pokes(agent_id: str, since: float, until: float, folder: Path | None = None) -> dict:
    """{"status": n, "corrections": n, "texts": his texts counted, "acted": [hers he answered, hers in all]}."""
    msgs = _thread(agent_id, folder)
    status = corrections = his = 0
    hers_all = hers_acted = 0
    prev = None
    for i, m in enumerate(msgs):
        at = float(m.get("at") or 0)
        if since <= at < until:
            if m.get("from") == "me":
                his += 1
                t = m["text"]
                if _STATUS.search(t):
                    status += 1
                if _CORRECTION.search(t) and prev is not None and prev.get("from") == "agent":
                    corrections += 1
            elif m.get("from") == "agent":
                hers_all += 1
                nxt = next((x for x in msgs[i + 1:] if x.get("from") == "me"), None)
                if nxt and float(nxt.get("at") or 0) - at <= ACTED_HOURS * 3600:
                    hers_acted += 1
        prev = m
    return {"status": status, "corrections": corrections, "texts": his, "acted": [hers_acted, hers_all]}


_HEAD = re.compile(r"^Started (\d\d:\d\d:\d\d) · (?:agent ([^·]+?) · )?", re.M)
_LINE = re.compile(r"^- (\d\d:\d\d) \*\*([^*:]+?)(?: \([^)]*\))?:\*\* (.*)$", re.M)


def call_pokes(agent_id: str, agent_name: str, since: float, until: float, folder: Path | None = None) -> dict:
    """Calls with her (her name in the head, or hers on a three-way) shorter than five minutes that end on a status
    question or a correction of his: {"short": n, "calls": n}."""
    calls = (folder or FOLDER) / "HQ" / "calls"
    short = total = 0
    try:
        names = sorted(os.listdir(calls))
    except OSError:
        return {"short": 0, "calls": 0}
    for nm in names:
        m = re.match(r"(\d{4}-\d\d-\d\d)-(\d\d)(\d\d)", nm)
        if not m or not nm.endswith(".md"):
            continue
        try:
            start = dt.datetime.strptime(f"{m.group(1)} {m.group(2)}:{m.group(3)}", "%Y-%m-%d %H:%M").timestamp()
        except ValueError:
            continue
        if not since <= start < until:
            continue
        try:
            text = (calls / nm).read_text(encoding="utf8", errors="replace")
        except OSError:
            continue
        h = _HEAD.search(text)
        who = (h.group(2) or "").strip().lower() if h else ""
        on_it = who == agent_name.lower() or re.search(rf"\b{re.escape(agent_name.lower())} joined\b|\bput {re.escape(agent_name.lower())} on\b", text.lower())
        if not on_it:
            continue
        total += 1
        lines = _LINE.findall(text)
        if not lines:
            continue
        t0 = dt.datetime.strptime(lines[0][0], "%H:%M")
        t1 = dt.datetime.strptime(lines[-1][0], "%H:%M")
        minutes = ((t1 - t0).seconds // 60) if t1 >= t0 else 0
        his = [l for l in lines if l[1].strip().lower() not in ("hq",) and not l[1].strip().startswith("HQ")]
        last = his[-1][2] if his else ""
        if minutes < SHORT_CALL_MIN and (_STATUS.search(last) or _CORRECTION.search(last)):
            short += 1
    return {"short": short, "calls": total}


def pokes(agent: dict, since: float, until: float, folder: Path | None = None) -> dict:
    t = text_pokes(agent["id"], since, until, folder)
    c = call_pokes(agent["id"], agent["name"], since, until, folder)
    return {"status_questions": t["status"], "corrections": t["corrections"], "short_calls": c["short"],
            "total": t["status"] + t["corrections"] + c["short"], "his_texts": t["texts"], "calls": c["calls"],
            "texts_acted_on": t["acted"]}


# -- each agent's own measures -----------------------------------------------------------------------------------------

def _todo(folder: Path):
    try:
        import todo
        return todo.read(folder / "challenges.md")
    except Exception:
        return None


def _parse_at(s: str) -> float | None:
    for f in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s.strip()[:16 if f.endswith("%M") else 10], f).timestamp()
        except (ValueError, TypeError):
            continue
    return None


def _deadline_of(it: dict) -> float | None:
    d = it.get("deadline") or ""
    m = re.search(r"\d{4}-\d\d-\d\d", d) or re.search(r"(?:by|before|deadline:?)\s*(\d{4}-\d\d-\d\d)", it.get("notes") or "", re.I)
    return _parse_at(m.group(1) if m and m.lastindex else m.group(0)) if m else None


def donna_measures(since: float, until: float, folder: Path | None = None) -> dict:
    folder = folder or FOLDER
    out = {}
    d = _todo(folder)
    if d and not d.get("missing"):
        done = [it for l in d["lists"] if l["kind"] == "done" for it in l["items"]]
        dated, before = 0, 0
        for it in done:
            at, dl = _parse_at(it.get("at") or ""), _deadline_of(it)
            if at and dl and since <= at < until:
                dated += 1
                before += at <= dl + 86400
        out["dated_items_done_before_their_date"] = [before, dated]
    else:
        out["dated_items_done_before_their_date"] = None
    try:
        inbox = (folder / "inbox.md").read_text(encoding="utf8")
        closed = re.findall(r"^- (\d{1,2} \w+ \d{4})", _section(inbox, "Closed"), re.M)
        n = 0
        for c in closed:
            try:
                t = dt.datetime.strptime(c, "%d %b %Y").timestamp()
            except ValueError:
                try:
                    t = dt.datetime.strptime(c, "%d %B %Y").timestamp()
                except ValueError:
                    continue
            n += since - 86400 <= t < until
        out["very_important_mail_resolved"] = n
        out["to_check_pile"] = len([l for l in _section(inbox, "To check").splitlines() if l.startswith("- ")])
        out["very_important_open"] = len([l for l in _section(inbox, "Very important").splitlines() if l.startswith("- ")])
    except OSError:
        out["very_important_mail_resolved"] = out["to_check_pile"] = out["very_important_open"] = None
    return out


def _section(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(r"^#{1,2} ", rest, re.M)
    return rest[:n.start()] if n else rest


def pepper_measures(since: float, until: float, folder: Path | None = None, plan: dict | None = None) -> dict:
    folder = folder or FOLDER
    out = {}
    try:  # the calendar's ticks and X's (app/planning.py's marks)
        import planning
        marks = planning._marks(planning._read())
        done = x = 0
        for m in marks.values():
            if isinstance(m, dict) and since <= float(m.get("marked") or 0) < until:
                done += m.get("mark") == "done"
                x += m.get("mark") == "x"
        out["calendar_ticks_vs_x"] = [done, x]
    except Exception:
        out["calendar_ticks_vs_x"] = None
    try:  # the game's ticks against its win line
        import games
        lines = games.score_lines()
        out["game"] = lines[0] if lines else "no game being played"
    except Exception:
        out["game"] = None
    d = _todo(folder)
    if d and not d.get("missing"):
        done = [it for l in d["lists"] if l["kind"] == "done" for it in l["items"]
                if _parse_at(it.get("at") or "") and since <= _parse_at(it.get("at") or "") < until]
        out["items_done"] = len(done)
        nm = None
        picks = (plan or {}).get("picks") or []
        if picks:
            want = picks[0].get("what", "") if isinstance(picks[0], dict) else str(picks[0])
            words = {w for w in re.findall(r"[a-z]{4,}", want.lower())}
            nm = any(len(words & set(re.findall(r"[a-z]{4,}", it["title"].lower()))) >= max(1, len(words) // 2) for it in done) if words else None
        out["needle_mover_done"] = nm
        out["share_important_not_urgent"] = None  # the done list doesn't keep which list an item came from
    else:
        out["items_done"] = out["needle_mover_done"] = out["share_important_not_urgent"] = None
    try:  # the weekly session done this week (the coaching check-ins)
        c = json.loads((folder / "HQ" / "coaching.json").read_text(encoding="utf8"))
        wk = dt.datetime.fromtimestamp(until - 1).strftime("%G-W%V")
        out["weekly_session_done"] = f"week:{wk}" in (c.get("done") or {})
    except (OSError, ValueError):
        out["weekly_session_done"] = None
    return out


def moneypenny_measures(since: float, until: float, folder: Path | None = None) -> dict:
    folder = folder or FOLDER
    out = {}
    try:  # rows marked ready before the sprint planning, against marks set at the sprint itself
        sp = json.loads((folder / "HQ" / "sprint.json").read_text(encoding="utf8"))
        friday = _last_friday(until)
        before = at_sprint = 0
        for v in (sp.get("ready") or {}).values():
            t = float((v or {}).get("at") or 0)
            if since <= t < until:
                if friday and friday + 12.5 * 3600 <= t < friday + 18 * 3600:
                    at_sprint += 1
                else:
                    before += 1
        out["rows_ready_before_friday_vs_at_the_sprint"] = [before, at_sprint]
    except (OSError, ValueError):
        out["rows_ready_before_friday_vs_at_the_sprint"] = None
    try:
        import estimate
        hist = [h for h in estimate.all_history() if since <= (h.get("done") or 0) < until]
        inside = n = 0
        for h in hist:
            if not h.get("est") or estimate.mistake(h):
                continue
            est = h.get("with_guess") or h["est"]
            late = h.get("latest") or estimate.latest_of(est, h.get("kind"))
            n += 1
            inside += (est / 2 <= h["actual"] <= late)
        out["jobs_landed_in_range"] = [inside, n]
        out["fixes_on_fixes"] = sum(1 for h in hist if str(h.get("about", "")).lower().startswith("fix for"))
        out["mistakes"] = sum(1 for h in hist if estimate.mistake(h))
    except Exception:
        out["jobs_landed_in_range"] = out["fixes_on_fixes"] = out["mistakes"] = None
    try:  # QA passed the first time: rows whose first QA mark in the window passed
        import qa
        import jobs as q
        text = q.read()[0]
        first_pass = first_fail = 0
        for label, (line, phase) in qa.rows(text).items():
            ms = qa.marks(line)
            if not ms:
                continue
            t = _mark_time(ms[0][1])
            if t and since <= t < until:
                first_pass += ms[0][0] == "passed"
                first_fail += ms[0][0] == "failed"
        out["qa_passed_first_time"] = [first_pass, first_pass + first_fail]
    except Exception:
        out["qa_passed_first_time"] = None
    return out


def _mark_time(s: str) -> float | None:
    m = re.search(r"(\d{1,2} \w+ \d{4}) ?(\d\d:\d\d)?", s or "")
    if not m:
        return None
    for f in ("%d %B %Y %H:%M", "%d %B %Y"):
        try:
            return dt.datetime.strptime(f"{m.group(1)} {m.group(2)}".strip() if "%H" in f else m.group(1), f).timestamp()
        except ValueError:
            continue
    return None


def _last_friday(until: float) -> float | None:
    d = dt.datetime.fromtimestamp(until - 1)
    d = d - dt.timedelta(days=(d.weekday() - 4) % 7)
    return d.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


# -- the score ---------------------------------------------------------------------------------------------------------

def score(agent: dict, now: dt.datetime | None = None, days: float = 7, folder: Path | None = None,
          plan: dict | None = None) -> dict:
    """Her score for the last `days` days: the pokes (shared by all), and her own measures by her context."""
    now = now or dt.datetime.now()
    until, since = now.timestamp(), (now - dt.timedelta(days=days)).timestamp()
    folder = folder or FOLDER
    p = pokes(agent, since, until, folder)
    ctx = agent.get("context") or ""
    if ctx == "day":
        own = donna_measures(since, until, folder)
    elif ctx == "coach":
        own = pepper_measures(since, until, folder, plan)
    elif ctx == "build":
        own = moneypenny_measures(since, until, folder)
    else:
        own = {}
    week = (now - dt.timedelta(days=1)).strftime("%G-W%V")
    return {"week": week, "from": dt.datetime.fromtimestamp(since).strftime("%Y-%m-%d"), "to": now.strftime("%Y-%m-%d"),
            "pokes": p, "measures": own, "lines": lines_of(agent, p, own)}


def _say(v) -> str:
    if v is None:
        return "not measured yet"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, list) and len(v) == 2:
        return f"{v[0]} of {v[1]}"
    return str(v)


NAMES = {"dated_items_done_before_their_date": "dated items done before their date",
         "very_important_mail_resolved": "very important mail resolved this week", "to_check_pile": "the To check pile now",
         "very_important_open": "very important mail still open", "calendar_ticks_vs_x": "calendar blocks ticked against X",
         "game": "the game", "items_done": "to-do items done", "needle_mover_done": "the week's needle mover done",
         "share_important_not_urgent": "share of done items that were important, not urgent",
         "weekly_session_done": "the weekly session done this week",
         "rows_ready_before_friday_vs_at_the_sprint": "rows ready before Friday against rows marked at the sprint",
         "jobs_landed_in_range": "jobs landed in their range", "qa_passed_first_time": "QA passed the first time",
         "fixes_on_fixes": "fixes on fixes", "mistakes": "jobs tagged as a mistake"}


def lines_of(agent: dict, p: dict, own: dict) -> list[str]:
    out = [f"pokes: {p['total']} (status questions {p['status_questions']}, corrections {p['corrections']}, short calls "
           f"{p['short_calls']}; his texts {p['his_texts']}, calls with her {p['calls']})"]
    if agent.get("context") == "day":
        out.append(f"texts he acted on: {_say(p['texts_acted_on'])}")
    for k, v in own.items():
        out.append(f"{NAMES.get(k, k)}: {_say(v)}")
    return out


def delta(new: dict, old: dict | None) -> list[str]:
    """What moved against the last score, in a few lines (the Friday screen): pokes first."""
    if not old:
        return ["first score, nothing to compare with yet"]
    out = []
    a, b = (new.get("pokes") or {}).get("total"), (old.get("pokes") or {}).get("total")
    if isinstance(a, int) and isinstance(b, int):
        out.append(f"pokes {b} to {a}" + (" (down, good)" if a < b else " (up)" if a > b else " (the same)"))
    for k, v in (new.get("measures") or {}).items():
        o = (old.get("measures") or {}).get(k)
        if v is None or o is None or v == o:
            continue
        out.append(f"{NAMES.get(k, k)}: {_say(o)} to {_say(v)}")
    return out or ["nothing moved"]


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    import agents
    who = argv[0].strip().lower()
    a = next((x for x in agents.load(FOLDER) if who in (x["id"], x["name"].lower())), None)
    if not a:
        print(f"No agent called {argv[0]}.")
        return 2
    days = 7
    if "--days" in argv:
        days = float(argv[argv.index("--days") + 1])
    s = score(a, days=days)
    if "--json" in argv:
        print(json.dumps(s, indent=1, ensure_ascii=False))
    else:
        print(f"{a['name']}'s score, week {s['week']} ({s['from']} to {s['to']}):")
        print("\n".join("- " + l for l in s["lines"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
