"""H247: feedback from the people using HQ, straight onto the planning in its own phase.

Piece (a): the Feedback button and the phase. Someone types a bug, a wish or an idea in the Feedback sheet (next to
the quick notes); it lands as one row under "Phase U · Feedback" on the planning (`jobs.py feedback`, so on the backup
the main writes it), with who sent it and when, in their own words, never as a job for the team: the sprint planning
decides on it. What they sent is kept in the workspace's HQ/feedback.json (or HQ_FEEDBACK), each with its row, and its
status is read back from the planning: received, looked at, planned, being built, done, or not doing.
Piece (b): an HQ connected to a maker (the link the maker sends, "Invite someone to send feedback" on their status
page) sends to the maker's mailbox instead (app/feedback_box.py, HTTPS, with its own key), and what was sent before on its
own planning goes across too. Until it's taken, a message waits here and is tried again every minute (the routine's
`poll`); the status comes back from the maker's planning. The maker's address and the key are kept in the workspace's
HQ/feedback-maker.json (HQ_FEEDBACK_MAKER), never in the code. Until an HQ is connected to a maker (or is a maker
itself, its mailbox on) the Feedback tab doesn't show. Piece (c): sent from a call or a text after the person's yes
(--via agent), and a text from their agent when a status changes, with its switch.

    python3 app/feedback.py                     what was sent, with each one's status (JSON)
    python3 app/feedback.py send "TEXT" [--bug] [--via agent]   send one
    python3 app/feedback.py connect LINK        connect to a maker with the link they sent
    python3 app/feedback.py disconnect          stop sending to that maker
    python3 app/feedback.py texts on|off        a text when a status changes
    python3 app/feedback.py poll                send what waits, read the statuses back (the routine, every minute)
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

HERE = Path(__file__).resolve().parent
JOBS = HERE.parent / "routine" / "jobs.py"


def _file() -> Path:
    return Path(os.environ.get("HQ_FEEDBACK", str(config.DATA / "feedback.json")))

MAX_TEXT = 2000
# In the order things go; the words the sender sees.
STATUS = {"received": "Received", "looked": "Looked at", "planned": "Planned", "building": "Being built",
          "done": "Done", "wont": "Not doing it"}
_LABEL = re.compile(r"^U\d+$")
_lock = threading.Lock()


def _load() -> dict:
    try:
        data = json.loads(_file().read_text())
        return data if isinstance(data.get("items"), list) else {"items": []}
    except (OSError, ValueError, AttributeError):
        return {"items": []}


def _save(data: dict) -> None:
    f = _file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    os.replace(tmp, f)


def _sender() -> str:
    try:
        import me
        return me.load(config.FOLDER).get("name") or ""
    except Exception:
        return ""


def _roadmap() -> Path:
    # HQ_FEEDBACK_ROADMAP: a test server's own roadmap, without moving everything else it reads (HQ_ROADMAP)
    return Path(os.environ.get("HQ_FEEDBACK_ROADMAP") or os.environ.get("HQ_ROADMAP") or str(config.DATA / "roadmap.md"))


def _rows() -> dict:
    """Each U row on the planning: its mark and whether it's parked (in Phase P)."""
    out, phase = {}, ""
    try:
        text = _roadmap().read_text(encoding="utf8")
    except OSError:
        return out, ""
    for line in text.split("\n"):
        if line.startswith("## "):
            phase = line
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]] if line.startswith("|") else []
        if len(cells) >= 2:
            label = cells[1].split(" ", 1)[0]
            if _LABEL.match(label):
                out[label] = {"mark": cells[0], "parked": phase.startswith("## Phase P ")}
    return out, text


def _sprint() -> dict:
    p = Path(os.environ.get("HQ_SPRINT", str(_roadmap().parent / "sprint.json")))
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def status_of(label: str, rows: dict, text: str, sprint: dict) -> str:
    row = rows.get(label)
    if not row:
        return "received"  # not on the planning (yet): it was sent, nothing more is known
    if row["mark"] == "✅":
        return "done"
    if row["parked"] or (sprint.get("moscow") or {}).get(label) == "wont":
        return "wont"
    l = re.escape(label)
    queue = re.compile(rf"^- Job \d+ · (ready|running|held|stop asked|parked)[^\n]*(?<![\w.]){l} on the (hq )?roadmap\b",
                       re.M | re.I)
    if queue.search(text):
        return "building"
    if label in (sprint.get("ready") or {}):
        return "planned"
    if label in (sprint.get("moscow") or {}) or label in (sprint.get("order") or []):
        return "looked"
    return "received"


STATUS_WAIT = "Waiting to send"


def _maker_file() -> Path:
    return Path(os.environ.get("HQ_FEEDBACK_MAKER", str(config.DATA / "feedback-maker.json")))


def maker() -> dict:
    """The maker this HQ sends to: {"name", "url", "key", "texts", "since"}, or {} when it isn't connected."""
    try:
        d = json.loads(_maker_file().read_text())
        return d if isinstance(d, dict) and d.get("url") and d.get("key") else {}
    except (OSError, ValueError):
        return {}


def _save_maker(d: dict) -> None:
    f = _maker_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, f)


def _is_maker() -> bool:
    try:
        import feedback_box as _mb
        return _mb.is_on()
    except Exception:
        return False


def _ok_url(u: str) -> bool:
    if re.match(r"^https://[A-Za-z0-9.-]+(:\d{1,5})?/[A-Za-z0-9/_-]*$", u or ""):
        return True
    # a test's own mailbox on this computer
    return os.environ.get("HQ_FEEDBACK_INSECURE") == "1" and bool(re.match(r"^http://127\.0\.0\.1:\d{1,5}/[A-Za-z0-9/_-]*$", u or ""))


def _call(url: str, key: str, path: str, body: dict, timeout=15) -> tuple:
    """POST to the maker's mailbox. Returns (status, answer); status 0 when it couldn't be reached."""
    req = urllib.request.Request(url.rstrip("/") + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json", "authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}
    except (OSError, ValueError):
        return 0, {}


def _read_link(link: str) -> dict:
    m = re.search(r"(?:[#&?]t=|feedback-join=)([A-Za-z0-9_-]+)", link or "") or re.match(r"^\s*([A-Za-z0-9_-]{40,})\s*$", link or "")
    if not m:
        return {}
    t = m.group(1)
    try:
        d = json.loads(base64.urlsafe_b64decode(t + "=" * (-len(t) % 4)))
    except (ValueError, TypeError):
        return {}
    return d if isinstance(d, dict) else {}


def connect(link: str) -> dict:
    """The link from the maker: its address and this HQ's key. Checked with the maker's mailbox before it's kept; what
    was sent before on this HQ's own planning goes across with the next poll."""
    d = _read_link(link)
    url, key = str(d.get("u") or ""), str(d.get("k") or "")
    if not (_ok_url(url) and re.match(r"^[A-Za-z0-9_-]{20,64}$", key)):
        return {"error": "That link isn't a feedback link from an HQ. Ask for it again."}
    code, ans = _call(url, key, "/hello", {})
    if code == 401:
        return {"error": "That link was taken back, or it's not right. Ask for a new one."}
    if code != 200:
        return {"error": "The other HQ couldn't be reached just now. Try the link again in a bit."}
    name = " ".join(str(ans.get("maker") or d.get("n") or "the maker").split())[:60]
    old = maker()
    _save_maker({"name": name, "url": url, "key": key, "texts": old.get("texts", True),
                 "since": datetime.now().strftime("%Y-%m-%d %H:%M")})
    with _lock:
        data = _load()
        for it in data["items"]:
            if not it.get("to"):  # sent on this HQ's own planning before: across too
                it.update({"to": name, "pending": True})
        _save(data)
    threading.Thread(target=poll, daemon=True).start()
    return {"connected": True, "maker": name}


def disconnect() -> dict:
    try:
        _maker_file().unlink()
    except OSError:
        pass
    return {"connected": False}


def set_texts(on: bool) -> dict:
    m = maker()
    if not m:
        return {"error": "Not connected to anyone yet."}
    m["texts"] = bool(on)
    _save_maker(m)
    return {"texts": m["texts"]}


def deliver() -> int:
    """What waits goes to the maker's mailbox; taken, it gets its row there. Returns how many went."""
    m = maker()
    if not m:
        return 0
    sent = 0
    with _lock:
        waiting = [dict(it) for it in _load()["items"] if it.get("pending")]
    for it in waiting:
        code, ans = _call(m["url"], m["key"], "/send", {"id": it["id"], "text": it["text"], "bug": bool(it.get("bug")),
                                                        "when": it.get("when", ""), "via": it.get("via", "")})
        if code == 200 and ans.get("row"):
            upd = {"pending": False, "remote": ans["row"], "status": it.get("status") or "received", "error": ""}
            sent += 1
        elif code in (400, 413):  # never taken as it is: say why, stop trying
            upd = {"pending": False, "error": ans.get("error") or "The other HQ didn't take it."}
        elif code == 401:
            upd = {"error": "Your link was taken back. Ask for a new one."}
        elif code == 429:
            upd = {"error": ans.get("error") or "That's enough for today; it goes tomorrow."}
        else:
            upd = {"error": ""}  # offline or busy: tried again in a minute
        with _lock:
            data = _load()
            for x in data["items"]:
                if x.get("id") == it["id"]:
                    x.update(upd)
            _save(data)
        if code in (0, 401):
            break
    return sent


def poll(texts=None) -> dict:
    """The routine, every minute: send what waits, then read the statuses back from the maker; a change texts the
    person (their agent, kind feedback-status) when the switch is on."""
    m = maker()
    if not m:
        return {"connected": False}
    went = deliver()
    code, ans = _call(m["url"], m["key"], "/status", {})
    changed = []
    if code == 200 and isinstance(ans.get("items"), dict):
        with _lock:
            data = _load()
            for it in data["items"]:
                got = ans["items"].get(it.get("id"))
                if not got or got.get("status") not in STATUS:
                    continue
                if it.get("status") and got["status"] != it.get("status"):
                    changed.append({"text": it["text"], "status": got["status"]})
                it["status"], it["remote"] = got["status"], got.get("row") or it.get("remote", "")
            _save(data)
    texted = 0
    if changed and m.get("texts", True):
        say = texts or _text_them
        for c in changed:
            try:
                say("feedback-status", f'What they sent: "{c["text"][:200]}". It is now: {STATUS[c["status"]].lower()}.')
                texted += 1
            except Exception:
                pass
    return {"connected": True, "sent": went, "changed": len(changed), "texted": texted, "reached": code == 200}


def _text_them(why: str, facts: str) -> None:
    if os.environ.get("HQ_UNDER_TEST") and not os.environ.get("HQ_DIRECT_DIR"):
        return  # a test never texts the real thread
    import direct_line
    if direct_line.on():
        direct_line.text(why, facts)


def read() -> dict:
    data = _load()
    rows, text = _rows()
    sprint = _sprint()
    m = maker()
    items = []
    for it in reversed(data["items"]):  # newest first
        if it.get("to"):
            if it.get("pending"):
                s, words = "waiting", STATUS_WAIT
            else:
                s = it.get("status") or "received"
                words = STATUS.get(s, STATUS["received"])
        else:
            s = status_of(it.get("row", ""), rows, text, sprint)
            words = STATUS[s]
        items.append({**it, "status": s, "status_words": words})
    return {"items": items, "connected": bool(m), "maker": m.get("name", ""), "texts": bool(m.get("texts", True)) if m else False,
            "is_maker": _is_maker(), "shown": bool(m) or _is_maker()}


def send(text: str, bug: bool = False, via: str = "") -> dict:
    """Connected to a maker: kept here as waiting and sent to the maker's mailbox (now, else with the next poll).
    Otherwise (the maker's own HQ) it goes on this HQ's own planning under Feedback. Returns the item, or an error."""
    said = " ".join((text or "").split())
    if not said:
        return {"error": "Write what you'd like to send first."}
    if len(said) > MAX_TEXT:
        return {"error": f"That's more than {MAX_TEXT} characters. Send it in two parts."}
    via = "agent" if via == "agent" else ""
    when = datetime.now().strftime("%Y-%m-%d %H:%M")
    m = maker()
    if m:
        item = {"id": hashlib.sha1(f"{when}{said}{os.urandom(4).hex()}".encode()).hexdigest()[:12], "when": when,
                "text": said, "bug": bug, "via": via, "to": m["name"], "pending": True, "row": ""}
        with _lock:
            data = _load()
            data["items"].append(item)
            _save(data)
        deliver()
        got = next((x for x in read()["items"] if x["id"] == item["id"]), item)
        return got
    cmd = [sys.executable, str(JOBS), "feedback", said, "--from", _sender()] + (["--bug"] if bug else [])
    cmd += ["--via", "agent"] if via else []
    try:
        env = {**os.environ}
        if os.environ.get("HQ_FEEDBACK_ROADMAP"):
            env["HQ_ROADMAP"] = os.environ["HQ_FEEDBACK_ROADMAP"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"error": f"It couldn't be sent: {e}"}
    out = (r.stdout or "") + (r.stderr or "")
    m2 = re.search(r"\b(U\d+) is on the planning", out)
    handed = r.returncode == 0 and not m2  # on the backup the main writes it; the row's number comes with the sync
    if r.returncode != 0 or not (m2 or handed):
        return {"error": (out.strip().splitlines() or ["It couldn't be sent."])[-1]}
    item = {"id": hashlib.sha1(f"{when}{said}".encode()).hexdigest()[:12], "when": when, "text": said,
            "bug": bug, "via": via, "row": m2.group(1) if m2 else ""}
    with _lock:
        data = _load()
        data["items"].append(item)
        _save(data)
    return {**item, "status": "received", "status_words": STATUS["received"]}


if __name__ == "__main__":
    a = sys.argv[1:]
    cmd = a[0] if a else ""
    if cmd == "send":
        via = a[a.index("--via") + 1] if "--via" in a and a.index("--via") + 1 < len(a) else ""
        words = [x for i, x in enumerate(a[1:], 1) if x not in ("--bug", "--via") and not (i > 1 and a[i - 1] == "--via")]
        res = send(" ".join(words), "--bug" in a, via)
    elif cmd == "connect":
        res = connect(" ".join(a[1:]))
    elif cmd == "disconnect":
        res = disconnect()
    elif cmd == "texts":
        res = set_texts((a[1:] or ["on"])[0] == "on")
    elif cmd == "poll":
        res = poll()
    else:
        res = read()
    print(json.dumps(res, ensure_ascii=False, indent=None if cmd else 1))
    sys.exit(1 if isinstance(res, dict) and res.get("error") else 0)
