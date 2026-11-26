"""F104: a feature in pieces now needs his say-so kept in features.json; what was already on before that stays on."""
import json
import os
import time
from pathlib import Path

WHAT = "A feature in pieces you already had on stays on: it's noted as turned on before HQ kept who turned it on."
HOW = "on before HQ kept who turned it on"
FILE = "HQ/features.json"


def _read(folder):
    try:
        d = json.loads((folder / FILE).read_text(encoding="utf8"))
    except (OSError, ValueError):
        return None
    return d if isinstance(d, dict) else None


def _write(folder, d):
    tmp = (folder / FILE).with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=2) + "\n", encoding="utf8")
    os.replace(tmp, folder / FILE)


def _pieces():
    p = os.environ.get("HQ_FEATURES_PIECES") or Path(__file__).resolve().parents[2] / "app" / "features-in-pieces.json"
    try:
        return {f.get("id") for f in json.loads(Path(p).read_text(encoding="utf8")).get("features") or [] if isinstance(f, dict)}
    except (OSError, ValueError, AttributeError):
        return set()


def do(folder):
    d = _read(folder)
    if not d:
        return
    add = [x for x in d.get("on") or [] if x in _pieces() and x not in (d.get("say_so") or {})]
    if add:
        d["say_so"] = {**(d.get("say_so") or {}), **{x: {"at": time.strftime("%Y-%m-%d %H:%M"), "how": HOW} for x in add}}
        _write(folder, d)


def undo(folder):
    d = _read(folder)
    if not d or not any(v.get("how") == HOW for v in (d.get("say_so") or {}).values()):
        return
    left = {k: v for k, v in d["say_so"].items() if v.get("how") != HOW}
    if left:
        d["say_so"] = left
    else:
        del d["say_so"]
    _write(folder, d)
