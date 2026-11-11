#!/usr/bin/env python3
"""The preparation fed (11 November 2026, by hand in the laptop chat, behind the backend switch fed_prep).

What the laptop chat told him, and he agreed to: "Hand her the substance at the start. The item's full text, your own words from the call
or note it came from, and the one or two real cases. The program can collect those." "Give her the task as understand and prepare this
ask. Today it reads as make the gate say ready." "Keep one preparation in one chat. A flag comes back to the same chat that wrote the item,
so nothing is re-read from zero." Measured before (47 first preparations): a prep job started with about 17,000 characters, its item's title
cut off, the gate's next step and her character; not the item, not his words, not a real case, not the earlier rounds. She then spent about
25 of her 35 commands reading HQ's code and 0.4 looking at his words, and every follow-up for a flag was a new chat that started cold.

So, held by the program (tick.start reads this for every prep job, "Prep of LABEL ...", while the switch is on):

  - start_text: the substance in the prep's own start text, bounded (FEED_MOST in all, each part its own ceiling, a cut always said):
    1. the item's full text as it stands on the planning (its ask: title and description, without the team's notes);
    2. his own words it came from: every quote the item holds that is one of his lines (a call, a text thread, a quick note, a laptop chat
       of his), each with where and when it was said and the lines around it in that same place; quotes not found are named; when none
       of his words can be found, that is said first, as the first thing to settle;
    3. the real cases it names: the jobs (their queue line and the end of their run's log), the files and transcripts (their path and
       size, the lines themselves when small), the calls of a named day, his texts at a named minute, the other items it names;
    4. every finding so far on this item, with its round and what was changed after it: the item's review (each verdict, review.py's
       history), her QA tests' review (each round, and whether the tests changed after), QA's failures, her sit-down stop, the line's
       last step and its earlier prep jobs, and the front's open points when it was capped.
  - continue: when an earlier prep of the same item ran in a chat that can still be picked up (on this computer, its transcript there,
    started under PREP_CHAT_HOURS ago, its context under PREP_CHAT_TOKENS), the next prep step resumes that chat (claude --resume) with
    the new findings as its message (continue_prompt). A continuation is a new job number that resumes the old session: the queue, the
    box, the estimates and the job history stay one record per run, and the line's tries count each prep step as before. When it can't
    be picked up, a fresh chat gets the whole fed start, and the reason is said in it.

The record of an item's prep chat is this computer's own, next to the carry-on records: carryon.DIR/prep-LABEL.json {session, n, at,
host, mode}. With the switch off nothing here runs: the prep starts as before.
"""
import glob
import json
import os
import re
import socket
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import carryon  # noqa: E402
import hqpaths  # noqa: E402
import jobs as q  # noqa: E402
import sprint as S  # noqa: E402

FEED_MOST = 40000  # characters in all the program adds to a prep's start (the laptop chat's choice: about the size of her start today, twice)
ITEM_MOST = 14000
WORDS_MOST = 12000
CASES_MOST = 7000
FINDINGS_MOST = 12000
QUOTES_MOST = 12  # quotes looked up per item
AROUND = 3  # lines before and after each line of his, in the same place
LINE_MOST = 600  # characters of each line around
PREP_CHAT_HOURS = 36  # an older prep chat isn't picked up again: the code and the planning have moved on (the laptop chat's choice)
PREP_CHAT_TOKENS = 140000  # a chat whose context is past this is too full to carry on in (the laptop chat's choice, a 200k context)
PREP_CHAT_BYTES = 8_000_000  # a transcript this big is too full whatever its last turn says


def fed_on() -> bool:
    """The backend switch fed_prep (app/backend.py)."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "app"))
        import backend
        return backend.on("fed_prep")
    except Exception:
        return False


def label_of(job) -> str | None:
    """The item a prep job prepares ("Prep of LABEL ..."), when the switch is on; else None."""
    try:
        import line
        lab = line.prep_label(" ".join((job.get("text") or "").split()))
    except Exception:
        return None
    return lab if lab and fed_on() else None


def _cut(text: str, most: int, what: str) -> str:
    if len(text) <= most:
        return text
    return text[:most] + f"\n[… cut here: {len(text) - most:,} more characters of {what} left out, to keep this start bounded]"


def _when(at) -> str:
    try:
        return time.strftime("%-d %B %Y %H:%M", time.localtime(float(at))) if at else "time not known"
    except (TypeError, ValueError, OverflowError):
        return "time not known"


def _ws() -> str:
    return S._ws()


def _row(label):
    return next((r for r in S.open_rows() if r["label"] == label), None) or S.row_of(label)


# ---------- 1. the item ----------

def item_text(row) -> str:
    ask = S.ask_of(row["line"])
    full = S.row_of(row["label"]) or row
    return (f"{row['label']} ({S.STATES.get(full.get('state'), full.get('state') or 'no mark')}; {full.get('phase') or 'no phase'}), its ask as it stands "
            f"(title and description, without the team's notes; the whole row: sprint.py show {row['label']}):\n\n"
            + _cut(ask, ITEM_MOST, "the item"))


# ---------- 2. his own words ----------

def _quotes(row) -> list[str]:
    out = []
    for qt in S._QUOTES.findall(S.ask_of(row["line"])):
        qt = qt.strip()
        if qt and S._bare(qt) not in {S._bare(x) for x in out}:
            out.append(qt)
    return out[:QUOTES_MOST]


def _parts(qt):
    return [p for p in (S._bare(x) for x in re.split(r"\s*(?:…|\.\.\.)\s*", qt)) if p]


def _places(ws):
    """Every place with his lines, as (where, [{"who", "text", "at"}]): the transcripts, the threads, the quick notes, his laptop chats."""
    places = [(w, rows) for w, rows in S._spoken(ws)]
    try:
        turns = S.laptop_chat_turns(ws)
    except Exception:
        turns = []
    if turns:
        places.append(("his laptop chats", [{"who": "he", "text": t, "at": at} for t, at in turns]))
    return places


def his_words(row, ws=None) -> tuple[str, bool]:
    """(the text of part 2, whether any of his words were found)."""
    ws = ws or _ws()
    quotes = _quotes(row)
    if not quotes:
        return ("The item quotes none of his words (no quote of eight characters or more in it).", False)
    try:
        places = _places(ws)
    except Exception as ex:
        return (f"His lines couldn't be read here ({ex!r}).", False)
    found, missing, out = 0, [], []
    for qt in quotes:
        parts = _parts(qt)
        if sum(len(p.split()) for p in parts) < S.HIS_QUOTE_WORDS:
            continue
        hits = []
        for where, rows in places:
            for i, r in enumerate(rows):
                if r.get("who") == "he" and all(p in S._bare(r.get("text") or "") for p in parts):
                    hits.append((r.get("at") or 0, where, rows, i))
        if not hits:
            missing.append(qt)
            continue
        found += 1
        hits.sort(key=lambda h: h[0])
        at, where, rows, i = hits[0]
        block = [f'"{qt[:300]}"' + (f" (said {len(hits)} times; the first shown)" if len(hits) > 1 else "")
                 + f"\n  where: {where}, {_when(at)}"]
        for j in range(max(0, i - AROUND), min(len(rows), i + AROUND + 1)):
            x = rows[j]
            who = "He" if x.get("who") == "he" else "The agent"
            mark = "→ " if j == i else "  "
            block.append(f"  {mark}{who} ({_when(x.get('at'))}): {' '.join(str(x.get('text') or '').split())[:LINE_MOST]}")
        out.append("\n".join(block))
    text = "\n\n".join(out)
    if missing:
        text += ("\n\n" if text else "") + "Not found in his own lines (a call, a text, a quick note, a laptop chat of his): " + "; ".join(
            f'"{m[:200]}"' for m in missing)
    return (_cut(text, WORDS_MOST, "his words"), found > 0)


# ---------- 3. the real cases ----------

_JOBS = re.compile(r"\bjobs?\s+(\d{3,5}(?:\s*(?:,|and|&)\s*\d{3,5})*)", re.I)
_PATH = re.compile(r"(?<![\w/.-])((?:HQ|coaching|routine|app|status|template|workflows)/[\w./-]*[\w-]\.(?:md|json|jsonl|py|txt|mjs|js|html))\b")
_CALL_DAY = re.compile(r"\bcall of (\d{1,2} [A-Z][a-z]+ \d{4})(?:,? (?:at |about )?(\d{1,2})[:.](\d{2}))?")
_LABELS = re.compile(r"(?<![\w-])([FH]\d{2,4})(?![\w-])")
JOBS_MOST, FILES_MOST, SMALL = 4, 6, 3000


def _run_dir():
    return os.environ.get("HQ_JOB_RUN") or os.path.join(hqpaths.HQ, "scratch", "routine")


def _tail(path, lines=12, most=1500):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 60000))
            got = f.read().decode("utf8", "replace").splitlines()[-lines:]
        return "\n".join("    " + x[:300] for x in got)[-most:]
    except OSError:
        return ""


def real_cases(row, ws=None) -> str:
    ws = ws or _ws()
    ask = S.ask_of(row["line"])
    out = []
    try:
        _, js, _ = q.read()
    except Exception:
        js = []
    byn = {j["n"]: j for j in js}
    nums = []
    for m in _JOBS.finditer(ask):
        for x in re.findall(r"\d{3,5}", m.group(1)):
            if int(x) not in nums:
                nums.append(int(x))
    for n in nums[:JOBS_MOST]:
        j = byn.get(n)
        bits = [f"- job {n}: " + (f"{j['state']}: {q.one_line(j['text'])[:300]}" if j else "no longer on the queue (finished jobs leave it)")]
        log = os.path.join(_run_dir(), f"job-{n}.stream.log")
        t = _tail(log)
        if t:
            bits.append(f"  the end of its run's log ({log}):\n{t}")
        elif os.path.exists(os.path.join(_run_dir(), f"job-{n}.prompt")):
            bits.append(f"  its start prompt: {os.path.join(_run_dir(), f'job-{n}.prompt')}")
        out.append("\n".join(bits))
    seen = []
    for m in _PATH.finditer(ask):
        p = m.group(1)
        if p in seen:
            continue
        seen.append(p)
        if len(seen) > FILES_MOST:
            break
        full = os.path.join(ws if p.startswith(("HQ/", "coaching/")) else hqpaths.HQ, p)
        if not os.path.exists(full):
            out.append(f"- {p}: not there")
            continue
        size = os.path.getsize(full) if os.path.isfile(full) else 0
        line = f"- {p} ({full}, {size:,} bytes)"
        if os.path.isfile(full) and 0 < size <= SMALL and not p.startswith("HQ/calls/"):
            try:
                line += ":\n" + "\n".join("    " + x for x in open(full, encoding="utf8", errors="replace").read().splitlines())
            except OSError:
                pass
        elif p.endswith(".jsonl") and size:
            line += ", its last lines:\n" + _tail(full, 5)
        out.append(line)
    calls = os.path.join(ws, "HQ", "calls")
    for m in list(_CALL_DAY.finditer(ask))[:3]:
        try:
            day = time.strftime("%Y-%m-%d", time.strptime(m.group(1), "%d %B %Y"))
        except ValueError:
            continue
        names = sorted(x for x in (os.listdir(calls) if os.path.isdir(calls) else []) if x.startswith(day))
        out.append(f"- the call of {m.group(1)}" + (f" at {m.group(2)}:{m.group(3)}" if m.group(2) else "") + ": "
                   + (", ".join(f"HQ/calls/{x}" for x in names[:6]) if names else "no transcript of that day here"))
    for m in list(S.THREAD_SOURCE.finditer(ask))[:3]:
        name = S._THREAD_OF.get(re.sub(r"'s?$", "", m.group(1).lower()).replace("'", ""), "team-line")
        try:
            t = time.mktime(time.strptime(f"{m.group(2)} {m.group(3)}:{m.group(4)}", "%d %B %Y %H:%M"))
        except ValueError:
            continue
        rows = next((r for w, r in S._spoken(ws) if w == f"HQ/{name}"), [])
        near = [i for i, r in enumerate(rows) if abs(float(r.get("at") or 0) - t) < 120]
        if near:
            i = near[0]
            out.append(f"- his text on the {name} at {m.group(2)} {m.group(3)}:{m.group(4)}:\n" + "\n".join(
                f"    {'He' if r['who'] == 'he' else 'The agent'} ({_when(r.get('at'))}): {r['text'][:LINE_MOST]}"
                for r in rows[max(0, i - 2):i + 3]))
    others = [x for x in dict.fromkeys(_LABELS.findall(ask)) if x != row["label"]][:5]
    for lab in others:
        r = S.row_of(lab)
        if r:
            out.append(f"- the item it names, {lab} ({S.STATES.get(r['state'], r['state'] or '')}): {q.one_line(r['title'])[:200]}")
    if not out:
        return "It names no job, file, transcript, call, text or other item the program could find."
    return _cut("\n".join(out), CASES_MOST, "the real cases")


# ---------- 4. every finding so far ----------

ROUNDS_SHOWN = 6  # the newest rounds of each review shown; the older ones counted
FINDING_MOST = 300  # characters of each finding


def _fs(fs):
    return " / ".join((f if len(f) <= FINDING_MOST else f[:FINDING_MOST] + "…") for f in fs or [])


def _newest(lines, what):
    if len(lines) <= ROUNDS_SHOWN:
        return lines
    return [f"- ({len(lines) - ROUNDS_SHOWN} earlier round(s) of {what} left out; the newest {ROUNDS_SHOWN} below)"] + lines[-ROUNDS_SHOWN:]


def findings(label, since=None) -> str:
    """Every finding so far on LABEL, with its round and what was changed after it; with SINCE (seconds) only what came after it."""
    out = []
    late = (lambda at: since is None or float(at or 0) > since)
    try:
        import review
        e = ((review._state()[1].get("rows") or {}).get(label)) or {}
    except Exception:
        e = {}
    hist = [h for h in e.get("history") or [] if isinstance(h, dict)]
    lines = []
    for k, h in enumerate(hist):
        nxt = hist[k + 1] if k + 1 < len(hist) else None
        if not late(h.get("at")):
            continue
        s = (f"- round {k + 1} ({_when(h.get('at'))}, road {h.get('cycle') or 0}): {'passed' if h.get('verdict') == 'pass' else 'flagged'}"
             + (": " + _fs(h.get("findings")) if h.get("findings") else ""))
        if nxt is not None:
            s += ("\n  changed after it (the sentences new in the next round's words): " + " / ".join(nxt.get("changed") or [])
                  if nxt.get("changed") else "\n  then the words changed (the next round read them)")
        lines.append(s)
    if not hist and e.get("verdict") in ("pass", "flag") and late(e.get("at")):
        lines.append(f"- its last verdict ({_when(e.get('at'))}): {'passed' if e['verdict'] == 'pass' else 'flagged'}"
                     + (": " + _fs(e.get("findings")) if e.get("findings") else "") + " (the rounds before weren't kept)")
    if lines:
        out.append("The item's review (on its wording):\n" + "\n".join(_newest(lines, "the item's review")))
    st = (e.get("fix") or {}).get("stop")
    if st and late(st.get("at")):
        out.append(f"Her stop on it ({st.get('kind')}, {_when(st.get('at'))}): {st.get('why', '')}"
                   + (" (his answer landed: " + "; ".join(st.get("landed") or []) + ")" if st.get("answered") else ""))
    try:
        import qatests
        t = qatests.state(label)
    except Exception:
        t = {}
    rvs = [x for x in t.get("reviews") or [] if isinstance(x, dict)]
    lines = []
    for k, x in enumerate(rvs):
        if not late(x.get("at")):
            continue
        s = (f"- round {k + 1} ({_when(x.get('at'))}, road {x.get('cycle') or 0}, tests {str(x.get('fp') or '')[:8]}): "
             + ("passed" if x.get("verdict") == "pass" else "flagged") + (": " + _fs(x.get("findings")) if x.get("findings") else ""))
        nxt = rvs[k + 1] if k + 1 < len(rvs) else None
        if nxt is not None:
            s += ("\n  her tests changed after it (version " + str(nxt.get("fp") or "")[:8] + ")" if nxt.get("fp") != x.get("fp")
                  else "\n  reviewed again unchanged")
        lines.append(s)
    seal = t.get("sealed") or {}
    if lines or (seal.get("fp") and late(seal.get("at"))):
        out.append("Her QA tests (HQ/qa-tests/" + label + "/): " + (f"sealed {str(seal.get('fp'))[:8]}, {len(seal.get('tests') or [])} test(s)"
                   if seal.get("fp") else "not sealed") + ("\n" + "\n".join(_newest(lines, "her tests' review")) if lines else ""))
    fails = [x for x in t.get("qa_fails") or [] if isinstance(x, dict) and late(x.get("at"))]
    if fails:
        out.append("QA's findings:\n" + "\n".join(f"- {_when(x.get('at'))}" + (f", job {x['job']}" if x.get("job") else "") + f": {x.get('finding', '')}"
                                                 + (" (passed since)" if x.get("passed") else "") for x in fails))
    try:
        import front
        ow = front.open_words(label)
        if ow:
            out.append("Past its review rounds it goes on as it is (the front capped). " + ow)
    except Exception:
        pass
    try:
        import line as L
        le = L._load().get(label) or {}
        if le.get("seen"):
            out.append(f"The line's last look: {le['seen']}" + (f" (the same step {le.get('tries')} time(s))" if le.get("tries") else ""))
        _, js, _ = q.read()
        preps = [j for j in js if L.prep_label(j.get("text")) == label]
        if preps and since is None:
            out.append("Earlier prep jobs of it still on the queue: " + ", ".join(f"job {j['n']} ({j['state']})" for j in preps))
    except Exception:
        pass
    if not out:
        return "Nothing written on it yet: no review, no QA tests, no QA finding." if since is None else \
            "Nothing new written on it since your last run."
    return _cut("\n\n".join(out), FINDINGS_MOST, "the findings")


# ---------- the whole start ----------

def start_text(label, fresh_why=None) -> str:
    """What the program adds to a prep job's first prompt: the item, his words, the real cases, every finding; bounded by FEED_MOST."""
    row = _row(label)
    if not row:
        return f"\n\n(The preparation fed: {label} isn't a row on the planning, so nothing was gathered for it.)"
    ws = _ws()
    words, found = his_words(row, ws)
    head = ("\n\nWHAT THE PROGRAM GATHERED FOR THIS ITEM (the preparation fed, 11 November 2026). Read it first: it is what you would "
            "otherwise go and look for. Open HQ's code only for what this doesn't tell you.\n")
    if fresh_why:
        head += f"(A fresh chat: {fresh_why}.)\n"
    if not found:
        head += ("\nFIRST TO SETTLE: none of his own words for " + label + " could be found in his lines (his calls, his texts, his quick "
                 "notes, his laptop chats). Before you prepare anything, settle where this ask came from and what he said: find his words "
                 "and quote them as they stand, or, when it was found by QA, a check or the review, say so in the item (His words: none, "
                 "found by ...). Never write words for him.\n")
    body = ("\n1. THE ITEM AS IT STANDS ON THE PLANNING\n" + item_text(row)
            + "\n\n2. HIS OWN WORDS IT CAME FROM (each with where and when, and his lines around it there)\n" + words
            + "\n\n3. THE REAL CASES IT NAMES\n" + real_cases(row, ws)
            + "\n\n4. EVERY FINDING SO FAR ON IT, WITH ITS ROUND AND WHAT WAS CHANGED AFTER IT\n" + findings(label))
    return _cut(head + body, FEED_MOST, "this gathered start")


# ---------- one preparation in one chat ----------

def _file(label):
    return os.path.join(carryon.DIR, f"prep-{label.strip().upper()}.json")


def record(label) -> dict:
    try:
        d = json.load(open(_file(label)))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def started(label, n, session, mode) -> None:
    """The routine started prep job N of LABEL in SESSION: the item's prep chat from now on."""
    os.makedirs(carryon.DIR, exist_ok=True)
    old = record(label)
    rec = {"session": session, "n": int(n), "at": time.time(), "host": socket.gethostname(), "mode": mode,
           "first": (old.get("first") or int(n)) if mode in ("continue", "resume") and old.get("session") == session else int(n)}
    tmp = _file(label) + ".tmp"
    json.dump(rec, open(tmp, "w"), indent=1)
    os.replace(tmp, _file(label))


def transcript(sid, folder=None) -> str | None:
    """The chat's transcript on this computer (Claude Code's own), or None."""
    if not sid:
        return None
    if folder:
        p = os.path.join(carryon.projects(), re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(folder)), f"{sid}.jsonl")
        if os.path.exists(p):
            return p
    got = glob.glob(os.path.join(carryon.projects(), "*", f"{sid}.jsonl"))
    return got[0] if got else None


def chat_tokens(path) -> int:
    """How full the chat's context was at its last turn: the last assistant turn's input, cache and output tokens; 0 when not said."""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 400000))
            lines = f.read().decode("utf8", "replace").splitlines()
    except OSError:
        return 0
    for raw in reversed(lines):
        if '"usage"' not in raw:
            continue
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        u = ((d.get("message") or {}).get("usage") if isinstance(d, dict) else None) or {}
        if u:
            return int(sum(int(u.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens")))
    return 0


def chat_to_continue(label, folder=None, now=None) -> dict:
    """{"session", "rec"} when LABEL's earlier prep chat can be picked up; else {"session": None, "why": why not, in a few words}."""
    now = now or time.time()
    rec = record(label)
    sid = rec.get("session")
    if not sid:
        return {"session": None, "why": f"no earlier prep chat of {label} is known on this computer"}
    if rec.get("host") and rec["host"] != socket.gethostname():
        return {"session": None, "why": f"its earlier prep chat (job {rec.get('n')}) ran on another computer"}
    try:
        _, js, _ = q.read()
        j = next((x for x in js if x["n"] == rec.get("n")), None)
        if j and j["state"].startswith("running"):
            return {"session": None, "why": f"its earlier prep chat (job {rec.get('n')}) is still running"}
    except Exception:
        pass
    path = transcript(sid, folder)
    if not path:
        return {"session": None, "why": f"its earlier prep chat (job {rec.get('n')}) isn't on this computer any more"}
    if now - float(rec.get("at") or 0) > PREP_CHAT_HOURS * 3600:
        return {"session": None, "why": f"its earlier prep chat (job {rec.get('n')}) is more than {PREP_CHAT_HOURS} hours old"}
    if os.path.getsize(path) > PREP_CHAT_BYTES:
        return {"session": None, "why": f"its earlier prep chat (job {rec.get('n')}) is too big to carry on in"}
    tok = chat_tokens(path)
    if tok > PREP_CHAT_TOKENS:
        return {"session": None, "why": f"its earlier prep chat (job {rec.get('n')}) is too full ({tok:,} tokens in its context)"}
    return {"session": sid, "rec": rec}


def continue_prompt(job, label, where, plan) -> str:
    """The message a prep step gets in the item's own prep chat: what came back since its last run, the next step, the rules again."""
    n, rec = job["n"], plan.get("prev") or record(label)
    jp = json.dumps(os.path.join(HERE, "jobs.py"))
    return (f"let's go again. This is job {n} from the queue on the HQ roadmap, started by the routine (phase L) in {where}. It is the next "
            f"step of your own preparation of {label}: this is the same chat you prepared it in (job {rec.get('n')}), so you already know "
            "the item, his words, the real case and the code you read; don't read them again from zero, only what the new findings need "
            "(the preparation fed: one preparation in one chat).\n\n"
            f"What came back since your last run, from the record:\n{findings(label, since=float(rec.get('at') or 0))}\n\n"
            f"The job, as the line queued it: {job['text']}\n\n"
            "Same as before: settle what came back in the item itself and in your tests, so a builder who has never seen it can build it; "
            f"run python3 {json.dumps(os.path.join(HERE, 'qatests.py'))} check {label} once yourself before you end. Never send it to the "
            "team, never jobs.py send-row or now: the program sends it once it's ready and its build switch is on. Text him only for a real "
            "decision, never for a step you can take yourself. You never build HQ. "
            f"Read your notes first, then after each step: python3 {jp} notes {n} (H283). " + q.notes_for_prompt(job))


def main(argv):
    if len(argv) == 2 and argv[0] == "show":
        print(start_text(argv[1].strip().upper()))
    elif len(argv) == 2 and argv[0] == "chat":
        print(json.dumps(chat_to_continue(argv[1].strip().upper(), hqpaths.FOLDER), indent=1))
    else:
        print(__doc__ + "\n    python3 routine/prepfeed.py show LABEL   what a prep of LABEL would start with\n"
              "    python3 routine/prepfeed.py chat LABEL   whether its prep chat can be picked up, or why not")


if __name__ == "__main__":
    main(sys.argv[1:])
