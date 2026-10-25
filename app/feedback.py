"""H247: feedback from the people using HQ, straight onto the planning in its own phase.

Piece (a): the Feedback button and the phase. Someone types a bug, a wish or an idea in the Feedback sheet (next to
the quick notes); it lands as one row under "Phase U · Feedback" on the planning (`jobs.py feedback`, so on the backup
the main writes it), with who sent it and when, in their own words, never as a job for the team: the sprint planning
decides on it. What they sent is kept in the workspace's HQ/feedback.json (or HQ_FEEDBACK), each with its row, and its
status is read back from the planning: received, looked at, planned, being built, done, or not doing.
For now it lands on this HQ's own planning; sending from someone else's HQ to the maker's (piece b) and from a call
with the texts (piece c) come after.

    python3 app/feedback.py                     what was sent, with each one's status (JSON)
    python3 app/feedback.py send "TEXT" [--bug]  send one
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
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


def read() -> dict:
    data = _load()
    rows, text = _rows()
    sprint = _sprint()
    items = []
    for it in reversed(data["items"]):  # newest first
        s = status_of(it.get("row", ""), rows, text, sprint)
        items.append({**it, "status": s, "status_words": STATUS[s]})
    return {"items": items}


def send(text: str, bug: bool = False) -> dict:
    """Puts it on the planning under Feedback and keeps it in the sender's own list. Returns the item, or an error."""
    said = " ".join((text or "").split())[:MAX_TEXT]
    if not said:
        return {"error": "Write what you'd like to send first."}
    cmd = [sys.executable, str(JOBS), "feedback", said, "--from", _sender()] + (["--bug"] if bug else [])
    try:
        env = {**os.environ}
        if os.environ.get("HQ_FEEDBACK_ROADMAP"):
            env["HQ_ROADMAP"] = os.environ["HQ_FEEDBACK_ROADMAP"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"error": f"It couldn't be sent: {e}"}
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"\b(U\d+) is on the planning", out)
    handed = r.returncode == 0 and not m  # on the backup the main writes it; the row's number comes with the sync
    if r.returncode != 0 or not (m or handed):
        return {"error": (out.strip().splitlines() or ["It couldn't be sent."])[-1]}
    when = datetime.now().strftime("%Y-%m-%d %H:%M")
    item = {"id": hashlib.sha1(f"{when}{said}".encode()).hexdigest()[:12], "when": when, "text": said,
            "bug": bug, "row": m.group(1) if m else ""}
    with _lock:
        data = _load()
        data["items"].append(item)
        _save(data)
    return {**item, "status": "received", "status_words": STATUS["received"]}


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "send":
        res = send(" ".join(x for x in a[1:] if x != "--bug"), "--bug" in a)
        print(json.dumps(res, ensure_ascii=False))
        sys.exit(1 if "error" in res else 0)
    print(json.dumps(read(), indent=1, ensure_ascii=False))
