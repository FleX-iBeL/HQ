"""H205: what HQ helps you with, every feature a switch (17 October 2026).

The user's words on the call of 17 October 2026: "so they can turn on and off what they want to use, and including
where they want HQ to suppor them in and where they want more freeroam freeflow", and "how do we make sure that this
doesnt create bugs or not user friendly GUI?". So: everything starts on, as before; one plain page in Settings ("What
HQ helps you with"), one line per switch; what leans on another says so ("Needs Texts with Donna") and can't be on
without it; off takes its button away cleanly and the rest of the dock moves up, on the phone and the Mac.

Where HQ already had an off switch, this is that switch, not a second one:
    calendar   agenda.on()      (and HQ_CALENDAR=0 on this computer still wins)
    texts      direct_line.on() (Donna's texts and check-ins; HQ_DIRECT=0 still wins)
    weather    weather.on()     (its rain alert comes as her text, so it needs texts; HQ_WEATHER=0 still wins)
    mail       the queue's "Mail check:" line on the roadmap (jobs.py mail-on / mail-off)
    coaching   the Life coaching workflow (workflows.py, the map)
The rest only had their button: to-do, notes and the team's status; News (H236) is new, its button and its hourly read. Every call reads what's off at its start
(config.voice_rules), so the agent doesn't bring up what they turned off unless they ask.

Which are off is the workspace's: `HQ/features.json` there, {"off": ["calendar"]}. No file: everything on, except
what starts off ("default": "off": Driving, H230, which needs their own key); turned on, it's in the file's "on" list.

    python3 app/features.py                 every switch, on or off
    python3 app/features.py on calendar     turn one on
    python3 app/features.py off calendar    turn one off
    python3 app/features.py pieces          the features still being built in pieces (F56, piece 2)
    python3 app/features.py ship ID         a feature in pieces goes on for everyone (by hand; qa.py does it itself)

F56, piece 2 (26 October 2026). His words on the call at 13:32 (Moneypenny), after 0.4.14 shipped a third of the
feedback feature to a friend: "Now we shipped out something that is a feature that I did not want to have at all and
now [a friend] has it in her updated version." A feature built in pieces is listed in `app/features-in-pieces.json`
(HQ_FEATURES_PIECES is a test's copy) from its first piece: {"id", "name", "line", "buttons", "row", "pieces"}. While
it's there it is off and invisible on every HQ (no row in Settings, its buttons gone, is_on False), except the maker's:
the workspace's features.json says "maker": true (or HQ_MAKER=1 on that computer), and there it shows in Settings as
still being built, on until switched off, to try it. When the row's last piece passes QA (the row is done and qa.py
pass marks it), qa.py takes it off the list (`ship`), so the next release turns it on for everyone.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # HQ
STATE = "HQ/features.json"  # in the workspace

# In the order Settings shows them. `buttons` are the call page's ids that go when it's off; `needs` another switch;
# `env` the computer's own off switch, which wins. {agent} is whoever answers the texts (Donna by default).
FEATURES = [
    {"id": "calendar", "name": "Calendar", "line": "Your Google Calendar in HQ: the Calendar button, and calls read and plan your days",
     "buttons": ["calbtn"], "env": "HQ_CALENDAR"},
    {"id": "todo", "name": "To-do list", "line": "Your priority lists: the To-do button, and calls keep it up to date",
     "buttons": ["todobtn"]},
    {"id": "texts", "name": "Texts with {agent}", "line": "{agent} texts you reminders and check-ins, and you can text her",
     "buttons": ["directbtn"], "env": "HQ_DIRECT"},
    {"id": "weather", "name": "Weather", "line": "The weather at a glance, and a text when rain is coming",
     "buttons": ["wx"], "needs": "texts", "env": "HQ_WEATHER"},
    {"id": "travel", "name": "Travel on appointments", "line": "Each appointment away from home gets its trip by public "
     "transport, and {agent} texts you when a train or bus on it changes", "buttons": [], "needs": "calendar"},
    {"id": "driving", "name": "Driving to appointments", "line": "Trips by car, with the traffic: {agent} texts you when to "
     "leave, and when the traffic changes. Needs your own maps key (the tutorial shows how)", "buttons": [],
     "needs": "calendar", "default": "off", "key": True},
    {"id": "mail", "name": "Mail check", "line": "Every hour HQ looks at your new mail and tells you what needs you",
     "buttons": []},
    {"id": "news", "name": "News", "line": "Your own newspaper: only the topics and sources you pick, read inside HQ, "
     "apart from your mail. The News button", "buttons": ["newsbtn"]},
    {"id": "notes", "name": "Quick notes", "line": "Jot something down for later: the Notes button",
     "buttons": ["notesbtn"]},
    {"id": "team", "name": "The team's work", "line": "What the computer builds for you, and how far it is: the Status button",
     "buttons": ["statbtn"]},
    {"id": "coaching", "name": "Life coaching", "line": "", "buttons": ["gamebtn", "coachbtn"], "workflow": "map"},
    # H298 (29 October 2026): the agents run their own cycles inside a hard wall on usage. Off by default for everyone,
    # since it spends usage on its own; while it's built in pieces it's also on the in-pieces list (hidden off the maker's).
    {"id": "agents_run", "name": "The agents run themselves", "line": "Each agent runs her own cycle without being poked "
     "(a bigger session and small steps, inside a wall on usage and hours), reads the handbook under her character, and "
     "escalates to you on her own line; the Friday screen on the status page shows what they did", "buttons": [],
     "default": "off", "cycles": True},
]
IDS = [f["id"] for f in FEATURES]
PIECES_FILE = ROOT / "app" / "features-in-pieces.json"


def _pieces_path() -> Path:
    return Path(os.environ.get("HQ_FEATURES_PIECES") or PIECES_FILE)


def _pieces() -> list[dict]:
    try:
        d = json.loads(_pieces_path().read_text(encoding="utf8"))
    except (OSError, ValueError):
        return []
    return [f for f in ((d.get("features") if isinstance(d, dict) else None) or [])
            if isinstance(f, dict) and isinstance(f.get("id"), str)]


def in_pieces() -> list[dict]:
    """F56: the features still being built in pieces, each with its row; hidden from everyone but the maker. H298: one
    that HQ already lists in FEATURES (a switch that will stay, off by default once shipped) is that entry, marked."""
    out = []
    byid = {f["id"]: f for f in FEATURES}
    for f in _pieces():
        if f["id"] in byid:
            out.append({**byid[f["id"]], **{k: v for k, v in f.items() if k in ("row", "pieces")}, "in_pieces": True})
        else:
            out.append({"buttons": [], "line": "", **f, "name": f.get("name") or f["id"], "in_pieces": True})
    return out


def everything() -> list[dict]:
    """Every switch: HQ's own, with the ones in pieces marked (or added, when HQ doesn't list them yet)."""
    pieces = {f["id"]: f for f in in_pieces()}
    return [pieces.get(f["id"], f) for f in FEATURES] + [f for i, f in pieces.items() if i not in IDS]


def ids() -> list[str]:
    return [f["id"] for f in everything()]


def maker(base: Path | None = None) -> bool:
    """The maker's own HQ (F56): the one that builds HQ, where a feature in pieces can be tried before it's whole."""
    if os.environ.get("HQ_MAKER") in ("0", "1"):
        return os.environ["HQ_MAKER"] == "1"
    return _state(base).get("maker") is True


def ship(fid: str) -> str:
    """Takes a feature off the in-pieces list: from the next release it's a normal switch, on for everyone."""
    p = _pieces_path()
    try:
        d = json.loads(p.read_text(encoding="utf8"))
    except (OSError, ValueError):
        return f"{fid} isn't being built in pieces."
    left = [f for f in d.get("features") or [] if not (isinstance(f, dict) and f.get("id") == fid)]
    if len(left) == len(d.get("features") or []):
        return f"{fid} isn't being built in pieces."
    d["features"] = left
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=2) + "\n", encoding="utf8")
    os.replace(tmp, p)
    return f"{fid} is whole: from the next release it's on for everyone."


def for_row(label: str) -> list[str]:
    """The features in pieces that a roadmap row builds."""
    return [f["id"] for f in in_pieces() if str(f.get("row", "")).upper() == label.upper()]


def folder() -> Path:
    return Path(os.environ.get("HQ_FEATURES_FOLDER") or os.environ.get("HQ_FOLDER")
                or os.path.realpath(os.environ.get("HQ_WORKSPACE", str(ROOT / "workspace"))))


def _agent() -> str:
    try:
        sys.path.insert(0, str(ROOT / "app"))
        import direct_line
        return direct_line.agent().get("name") or "Donna"
    except Exception:
        return "Donna"


def _state(base: Path | None = None) -> dict:
    try:
        d = json.loads(((base or folder()) / STATE).read_text(encoding="utf8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def turned_off(base: Path | None = None) -> list[str]:
    """The switches that are off: turned off, or starting off and never turned on (H230)."""
    d = _state(base)
    off, on = d.get("off") or [], d.get("on") or []
    mk = maker(base)
    return [x["id"] for x in everything() if x["id"] in off or (x.get("default") == "off" and x["id"] not in on)
            or (x.get("in_pieces") and not mk)]


def _save(base: Path, off: list[str]) -> None:
    p = base / STATE
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    old = _state(base)
    d = {"off": [x["id"] for x in everything() if x["id"] in off and x.get("default") != "off"
                 and not (x.get("in_pieces") and not maker(base))]}
    on = [x["id"] for x in FEATURES if x.get("default") == "off" and x["id"] not in off]
    if on:
        d["on"] = on
    if old.get("maker") is True:  # F56: kept, never set here
        d["maker"] = True
    tmp.write_text(json.dumps(d, indent=2) + "\n", encoding="utf8")
    os.replace(tmp, p)


def _computer_off(f: dict) -> bool:
    return bool(f.get("env")) and os.environ.get(f["env"], "1") == "0"


# The mail check's switch is the queue's own line on the roadmap (L8); HQ_FEATURES_ROADMAP is a test's copy.
def _roadmap() -> str:
    if os.environ.get("HQ_FEATURES_ROADMAP"):
        return os.environ["HQ_FEATURES_ROADMAP"]
    sys.path.insert(0, str(ROOT / "routine"))
    import hqpaths
    return hqpaths.ROADMAP


def mail_on() -> bool | None:
    """The hourly mail check, as the roadmap says; None when there's no roadmap to say it (then the row isn't shown)."""
    try:
        text = Path(_roadmap()).read_text(encoding="utf8")
    except OSError:
        return None
    m = re.search(r"^\*\*Mail check:\*\*([^(\n]*)", text, re.M)
    return None if not m else "off" not in m.group(1).lower()


def _mail(on: bool) -> bool:
    env = {**os.environ}
    if os.environ.get("HQ_FEATURES_ROADMAP"):
        env["HQ_ROADMAP"] = os.environ["HQ_FEATURES_ROADMAP"]
    r = subprocess.run([sys.executable, str(ROOT / "routine" / "jobs.py"), "mail-on" if on else "mail-off"],
                       env=env, capture_output=True, text=True, timeout=60)
    return r.returncode == 0


def _workflows():
    sys.path.insert(0, str(ROOT / "app"))
    import workflows
    return workflows


def _wf_folder() -> Path:
    return Path(os.environ.get("HQ_WORKFLOWS_FOLDER") or folder())


def is_on(fid: str, base: Path | None = None) -> bool:
    """Whether a switch is on, with what it needs. The cheap ones (no roadmap, no workflow) are read on every look."""
    f = next((x for x in everything() if x["id"] == fid), None)
    if not f:
        return True
    if f.get("in_pieces") and not maker(base):  # F56: not whole yet, hidden here
        return False
    if _computer_off(f):
        return False
    if f.get("workflow"):
        return f["workflow"] in _workflows().turned_on(_wf_folder())
    if fid == "mail":
        return mail_on() is not False
    if fid in turned_off(base):
        return False
    return not f.get("needs") or is_on(f["needs"], base)


def listing(base: Path | None = None) -> list[dict]:
    """For Settings: each switch, on or off, its line, what it needs, and which buttons go when it's off."""
    base = base or folder()
    off, agent, out, mk = turned_off(base), _agent(), [], maker(base)
    for f in everything():
        item = {"id": f["id"], "name": f["name"].replace("{agent}", agent), "line": f["line"].replace("{agent}", agent),
                "buttons": f["buttons"]}
        if f.get("in_pieces"):  # F56: still being built; only the maker sees it, everyone else only loses its buttons
            item["on"] = mk and f["id"] not in off
            if mk:
                item["pieces"] = f"Still being built ({f.get('row') or 'no row'}"
                item["pieces"] += f", {f['pieces']})" if f.get("pieces") else ")"
                item["pieces"] += ": only on your HQ until its last piece passes QA"
            else:
                item["hidden"] = True
            out.append(item)
            continue
        if f.get("workflow"):
            w = _workflows().find(f["workflow"])
            if not w:
                continue
            item["name"] = w["name"]
            item["line"] = f"On: {w['on']}. Off: {w['off']}." if w.get("on") and w.get("off") else w["what"]
            item["on"] = w["id"] in _workflows().turned_on(_wf_folder())
        elif f["id"] == "mail":
            m = mail_on()
            if m is None:
                continue
            item["on"] = m
        else:
            item["on"] = f["id"] not in off
        if f.get("needs"):
            need = next(x for x in everything() if x["id"] == f["needs"])
            item["needs"] = need["id"]
            item["needs_name"] = need["name"].replace("{agent}", agent)
        if _computer_off(f):
            item["on"], item["fixed"] = False, "Off on this computer"
        if f.get("cycles"):  # H298: the agents' cycle settings, a line per agent under this row when it's on
            item["cycles"] = True
        if f.get("key"):  # H230: their own maps key, kept on this computer (drive.py); never the key itself
            try:
                sys.path.insert(0, str(ROOT / "app"))
                import drive
                item["key"] = drive.status()
            except Exception:
                item["key"] = {"key": False}
        out.append(item)
    byid = {i["id"]: i for i in out}
    for i in out:  # what leans on a switch that's off is off too, and says why
        if i.get("needs") and not byid.get(i["needs"], {}).get("on", True):
            i["waiting"] = True
            i["on"] = False
    return out


def switch(fid: str, on: bool, base: Path | None = None) -> str:
    base = base or folder()
    f = next((x for x in everything() if x["id"] == fid and not (x.get("in_pieces") and not maker(base))), None)
    if not f:
        return f"No switch {fid}. There are: {', '.join(i for i in ids() if is_on(i, base) or i in IDS)}."
    if f.get("workflow"):
        wf = _workflows()
        return wf.turn_on(_wf_folder(), f["workflow"]) if on else wf.turn_off(_wf_folder(), f["workflow"])
    if fid == "mail":
        if mail_on() is None:
            return "There's no mail check on this HQ."
        return f"The mail check is {'on' if on else 'off'}." if _mail(on) else "Couldn't switch the mail check."
    off = turned_off(base)
    if on and fid in off:
        off.remove(fid)
    elif not on and fid not in off:
        off.append(fid)
    _save(base, off)
    name = f["name"].replace("{agent}", _agent())
    return f"{name} is {'on' if on else 'off'}."


def rule(base: Path | None = None) -> str:
    """The call rule for what they turned off; empty when everything's on."""
    quiet = {f["id"] for f in FEATURES if f.get("default") == "off"}  # starts off: not something they turned off
    names = [i["name"] for i in listing(base) if not i["on"] and i["id"] != "coaching" and i["id"] not in quiet
             and not i.get("hidden") and not i.get("pieces")]
    if not names:
        return ""
    return ("- Turned off in What HQ helps you with (H205): " + ", ".join(names) + ". Don't bring those up or offer "
            "them; if they ask for one, help, and say once that it's off in Settings, under What HQ helps you with.")


def main(argv: list[str]) -> int:
    if not argv:
        for i in listing():
            if i.get("hidden"):
                continue
            print(f"{i['id']}: {i['name']}, {'on' if i['on'] else 'off'}"
                  + (f" (needs {i['needs_name']})" if i.get("needs") else "") + (f" ({i['fixed']})" if i.get("fixed") else "")
                  + f". {i['line']}")
        return 0
    if argv[0] == "pieces":
        fs = in_pieces()
        print("\n".join(f"{f['id']}: {f['name']} ({f.get('row') or 'no row'}"
                        + (f", {f['pieces']}" if f.get("pieces") else "") + ")" for f in fs)
              or "Nothing is being built in pieces.")
        print(f"This HQ is {'the maker' if maker() else 'not the maker'}: "
              + ("it sees them." if maker() else "they're hidden here."))
        return 0
    if argv[0] == "ship" and len(argv) == 2:
        print(ship(argv[1]))
        return 0
    if argv[0] in ("on", "off") and len(argv) == 2:
        print(switch(argv[1], argv[0] == "on"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
