"""H244: the five kinds of the week, in colour, in the app's calendar.

25 October 2026 (call at 18:11, Moneypenny), in the user's words: "5 kinds of colours (this should be a must btw)" and
"the five kinds of colour we decided that the training's names can go public. so its for everyone". 23 October 2026
(call at 16:11, Pepper): "we can also tap those categories, right? So we could tap CEO time or we could see when it is.
... People can overrule it themselves, of course, but the colors that we chose right now is going to be the same
colors for them."

An appointment's kind is its colour in Google Calendar: each kind owns one of Google's eleven event colours. The
defaults, for every HQ: money makers banana (yellow), client delivery basil (green), admin essentials tomato (red),
CEO time peacock (blue-green), cup fillers grape (purple); graphite (grey) is a template block not set yet. An
appointment without its own colour, or in a colour no kind owns, has no kind. HQ never changes a colour in Google: it
only reads it (agenda.py keeps Google's colorId as `gcolor`).

Each HQ can rename a kind or give it another of Google's colours: the workspace's HQ/calendar-kinds.json
(HQ_CALENDAR_KINDS), only the changes, {"<id>": {"name": "...", "colour": "<google name>"}}. Showing or hiding a kind
is the page's, per device, like the calendars.

    python3 app/kinds.py                    the kinds, their colours and names (JSON)
    python3 app/kinds.py rename ID NAME     give a kind another name
    python3 app/kinds.py colour ID COLOUR   give a kind another of Google's colours (banana, basil, ...)
    python3 app/kinds.py reset ID           back to HQ's own name and colour
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "routine"))
import hqpaths  # noqa: E402

# Google Calendar's colours for one appointment (an event's colorId), by the names its colour picker gives them
EVENT_COLOURS = {
    "1": ("lavender", "#7986cb"), "2": ("sage", "#33b679"), "3": ("grape", "#8e24aa"), "4": ("flamingo", "#e67c73"),
    "5": ("banana", "#f6bf26"), "6": ("tangerine", "#f4511e"), "7": ("peacock", "#039be5"),
    "8": ("graphite", "#616161"), "9": ("blueberry", "#3f51b5"), "10": ("basil", "#0b8043"),
    "11": ("tomato", "#d50000")}
BY_NAME = {name: (cid, hx) for cid, (name, hx) in EVENT_COLOURS.items()}
TEMPLATE = "template"
DEFAULTS = [  # in the order the page shows them
    {"id": "money", "name": "Money makers", "colour": "banana"},
    {"id": "delivery", "name": "Client delivery", "colour": "basil"},
    {"id": "admin", "name": "Admin essentials", "colour": "tomato"},
    {"id": "ceo", "name": "CEO time", "colour": "peacock"},
    {"id": "cup", "name": "Cup fillers", "colour": "grape"},
    {"id": TEMPLATE, "name": "Not set yet", "colour": "graphite"},
]
NAME_MAX = 40


def kinds_file() -> Path:
    """Next to the calendar copy (so a test's own copy has its own kinds), unless HQ_CALENDAR_KINDS says another."""
    cal = os.environ.get("HQ_CALENDAR_FILE") or os.path.join(hqpaths.DATA, "calendar.json")
    return Path(os.environ.get("HQ_CALENDAR_KINDS") or Path(cal).with_name("calendar-kinds.json"))


def _own() -> dict:
    try:
        d = json.loads(kinds_file().read_text(encoding="utf8"))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def _save(d: dict) -> None:
    p = kinds_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    os.replace(tmp, p)


def kinds() -> list[dict]:
    """Every kind with its name, Google colour name, hex and colorId; the template last. A colour two kinds would
    share stays with the first."""
    own, out, taken = _own(), [], set()
    for k in DEFAULTS:
        o = own.get(k["id"]) if isinstance(own.get(k["id"]), dict) else {}
        name = str(o.get("name") or "").strip()[:NAME_MAX] or k["name"]
        colour = str(o.get("colour") or "").strip().lower()
        colour = colour if colour in BY_NAME else k["colour"]
        cid, hx = BY_NAME[colour]
        out.append({"id": k["id"], "name": name, "colour": colour, "color": hx, "gcolor": cid,
                    "template": k["id"] == TEMPLATE, "own": bool(o), "free": cid in taken})
        taken.add(cid)
    for k in out:
        if k.pop("free"):
            k["gcolor"] = ""  # a colour another kind already owns: this one catches nothing until it gets its own
    return out


def kind_of(gcolor: str, ks: list[dict] | None = None) -> str:
    """The kind an appointment with Google colorId `gcolor` belongs to, or "" when none."""
    g = str(gcolor or "")
    if not g:
        return ""
    for k in ks if ks is not None else kinds():
        if k["gcolor"] == g:
            return k["id"]
    return ""


def event_colour(gcolor: str) -> str:
    """The hex of an appointment's own Google colour, or "" when it has none."""
    return EVENT_COLOURS.get(str(gcolor or ""), ("", ""))[1]


def find(word: str) -> str:
    """A kind's id from its id or its name as shown (case and spaces don't matter)."""
    w = " ".join(str(word or "").lower().split())
    for k in kinds():
        if w in (k["id"], k["name"].lower()):
            return k["id"]
    raise KeyError(word)


def rename(kid: str, name: str) -> list[dict]:
    kid = find(kid)
    name = " ".join(str(name or "").split())[:NAME_MAX]
    if not name:
        raise ValueError("a name, please")
    d = _own()
    o = d.get(kid) if isinstance(d.get(kid), dict) else {}
    o["name"] = name
    d[kid] = o
    _save(d)
    return kinds()


def recolour(kid: str, colour: str) -> list[dict]:
    kid = find(kid)
    colour = str(colour or "").strip().lower()
    if colour not in BY_NAME:
        raise ValueError("one of Google's colours: " + ", ".join(BY_NAME))
    d = _own()
    o = d.get(kid) if isinstance(d.get(kid), dict) else {}
    o["colour"] = colour
    d[kid] = o
    _save(d)
    return kinds()


def reset(kid: str) -> list[dict]:
    kid = find(kid)
    d = _own()
    if d.pop(kid, None) is not None:
        _save(d)
    return kinds()


def main(argv: list[str]) -> int:
    try:
        if not argv:
            print(json.dumps(kinds(), indent=1, ensure_ascii=False))
        elif argv[0] == "rename" and len(argv) >= 3:
            rename(argv[1], " ".join(argv[2:]))
            print(f"{argv[1]} is now called {' '.join(argv[2:])}.")
        elif argv[0] == "colour" and len(argv) == 3:
            recolour(argv[1], argv[2])
            print(f"{argv[1]} is now {argv[2].lower()}.")
        elif argv[0] == "reset" and len(argv) == 2:
            reset(argv[1])
            print(f"{argv[1]} is back to HQ's own name and colour.")
        else:
            print(__doc__.strip().split("\n\n")[-1])
            return 2
    except KeyError as e:
        print(f"No kind called {e.args[0]}. The kinds: " + ", ".join(k["name"] for k in kinds()) + ".")
        return 1
    except ValueError as e:
        print(str(e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
