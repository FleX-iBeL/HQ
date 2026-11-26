"""The backend switches: a part of how HQ runs that can be turned off in one step.

The file is the workspace's `HQ/backend.json`: {"on": ["briefing", …]}. A computer can override one with
HQ_BACKEND_<NAME>=1 or 0 (a test, or one computer only), and HQ_BACKEND names another file. Names in the file that this
HQ doesn't know (written by another version) are kept as they are.

    python3 app/backend.py                  the switches and what each does
    python3 app/backend.py on NAME          turn one on (from the next call or text)
    python3 app/backend.py off NAME
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SWITCHES = {
    "briefing": "An agent starts with a small briefing the routine writes every minute (the day, the open things, "
                "the planning), plus her identity; the rest of the files she opens when a turn needs them. "
                "Off: she starts with the files whole.",
    "open_line": "Each agent keeps one Claude session between calls and texts (resumed, rolled over when it grows "
                 "too big), so a call doesn't start from zero. Off: a fresh session per call and per text.",
    "one_way_sync": "The main HQ sends and the backup only receives (Syncthing folder types), and the backup hands "
                    "every write to the main. Off: both send and receive, with conflict copies merged after.",
    "handover": "With one-way sync, the backup hands what it holds that the main doesn't (its own changes, its "
                "conflict copies) to the main every minute, and takes the main's copy back once all of it is there. "
                "Off: it waits, said on the sync line; `sync.py handover` does it once by hand.",
}


def _folder() -> Path:
    ws = os.environ.get("HQ_WORKSPACE")
    return Path(ws).expanduser().resolve() if ws else (Path(__file__).resolve().parent.parent / "workspace").resolve()


def file(folder: Path | None = None) -> Path:
    if folder is not None:
        return Path(folder) / "HQ" / "backend.json"
    env = os.environ.get("HQ_BACKEND")
    return Path(env).expanduser() if env else _folder() / "HQ" / "backend.json"


def _read(folder: Path | None = None) -> dict:
    try:
        d = json.loads(file(folder).read_text(encoding="utf8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def on(name: str, folder: Path | None = None) -> bool:
    """Whether the switch is on: the computer's own setting first, then the workspace's file (that of `folder` when
    one is given: a flow's own workspace has its own switches, all off unless it writes them)."""
    if name not in SWITCHES:
        raise KeyError(name)
    env = os.environ.get(f"HQ_BACKEND_{name.upper()}")
    if env in ("0", "1"):
        return env == "1"
    return name in (_read(folder).get("on") or [])


def listing() -> list[dict]:
    d = _read()
    return [{"id": k, "on": on(k), "set": k in (d.get("on") or []), "what": v} for k, v in SWITCHES.items()]


def switch(name: str, want: bool) -> dict:
    if name not in SWITCHES:
        raise KeyError(name)
    d = _read()
    now = [k for k in (d.get("on") or []) if k != name]  # a name this HQ doesn't know stays in the list
    if want:
        now.append(name)
    d["on"] = now
    p = file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(d, indent=2) + "\n", encoding="utf8")
    os.replace(tmp, p)
    return d


def switch_said(name: str, want: bool) -> str:
    """F115: a switch flipped from wherever: on the backup the main writes the file (role.door), as every synced file."""
    if name not in SWITCHES:
        return f"No switch called {name!r}. The switches: {', '.join(SWITCHES)}."
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "routine"))
    import role
    h = role.door(file(), "backend", ["on" if want else "off", name])
    if h is not None:
        return role.door_said(h, "The switch")
    switch(name, want)
    return f"{name} is {'on' if want else 'off'}."


def words() -> str:
    out = []
    for s in listing():
        state = "on" if s["on"] else "off"
        if os.environ.get(f"HQ_BACKEND_{s['id'].upper()}") in ("0", "1"):
            state += " (set on this computer)"
        out.append(f"{s['id']}: {state}. {s['what']}")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("list", "show"):
        print(words())
        return 0
    if argv[0] in ("on", "off") and len(argv) == 2:
        if argv[1] not in SWITCHES:
            print(f"No switch called {argv[1]!r}. The switches: {', '.join(SWITCHES)}.")
            return 2
        said = switch_said(argv[1], argv[0] == "on")
        print(said if not said.endswith(f"{argv[0]}.") else f"{argv[1]} is {argv[0]} from the next call or text.")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
