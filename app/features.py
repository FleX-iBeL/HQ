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
The rest only had their button: to-do, notes and the team's status. Every call reads what's off at its start
(config.voice_rules), so the agent doesn't bring up what they turned off unless they ask.

Which are off is the workspace's: `HQ/features.json` there, {"off": ["calendar"]}. No file: everything on.

    python3 app/features.py                 every switch, on or off
    python3 app/features.py on calendar     turn one on
    python3 app/features.py off calendar    turn one off
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
    {"id": "mail", "name": "Mail check", "line": "Every hour HQ looks at your new mail and tells you what needs you",
     "buttons": []},
    {"id": "notes", "name": "Quick notes", "line": "Jot something down for later: the Notes button",
     "buttons": ["notesbtn"]},
    {"id": "team", "name": "The team's work", "line": "What the computer builds for you, and how far it is: the Status button",
     "buttons": ["statbtn"]},
    {"id": "coaching", "name": "Life coaching", "line": "", "buttons": ["gamebtn"], "workflow": "map"},
]
IDS = [f["id"] for f in FEATURES]


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


def turned_off(base: Path | None = None) -> list[str]:
    try:
        off = json.loads(((base or folder()) / STATE).read_text(encoding="utf8")).get("off", [])
    except (OSError, ValueError, AttributeError):
        return []
    return [x for x in off if x in IDS]


def _save(base: Path, off: list[str]) -> None:
    p = base / STATE
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps({"off": [x for x in IDS if x in off]}, indent=2) + "\n", encoding="utf8")
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
    f = next((x for x in FEATURES if x["id"] == fid), None)
    if not f:
        return True
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
    off, agent, out = turned_off(base), _agent(), []
    for f in FEATURES:
        item = {"id": f["id"], "name": f["name"].replace("{agent}", agent), "line": f["line"].replace("{agent}", agent),
                "buttons": f["buttons"]}
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
            need = next(x for x in FEATURES if x["id"] == f["needs"])
            item["needs"] = need["id"]
            item["needs_name"] = need["name"].replace("{agent}", agent)
        if _computer_off(f):
            item["on"], item["fixed"] = False, "Off on this computer"
        out.append(item)
    byid = {i["id"]: i for i in out}
    for i in out:  # what leans on a switch that's off is off too, and says why
        if i.get("needs") and not byid.get(i["needs"], {}).get("on", True):
            i["waiting"] = True
            i["on"] = False
    return out


def switch(fid: str, on: bool, base: Path | None = None) -> str:
    base = base or folder()
    f = next((x for x in FEATURES if x["id"] == fid), None)
    if not f:
        return f"No switch {fid}. There are: {', '.join(IDS)}."
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
    names = [i["name"] for i in listing(base) if not i["on"] and i["id"] != "coaching"]
    if not names:
        return ""
    return ("- Turned off in What HQ helps you with (H205): " + ", ".join(names) + ". Don't bring those up or offer "
            "them; if they ask for one, help, and say once that it's off in Settings, under What HQ helps you with.")


def main(argv: list[str]) -> int:
    if not argv:
        for i in listing():
            print(f"{i['id']}: {i['name']}, {'on' if i['on'] else 'off'}"
                  + (f" (needs {i['needs_name']})" if i.get("needs") else "") + (f" ({i['fixed']})" if i.get("fixed") else "")
                  + f". {i['line']}")
        return 0
    if argv[0] in ("on", "off") and len(argv) == 2:
        print(switch(argv[1], argv[0] == "on"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
