"""nowroad (4 November 2026): a row's ask is written once. Rows written by a call, a text or the status page held the same words twice: in What
you get (after the date) and again in the Model column. The review and the Ready mark only ever read What you get, but an edit of his words met
them twice: reword refused it, or changed one copy and not the other, and Moneypenny told him "both copies" changed when one had. Since then
jobs.py writes the Model column empty. This clears the old copies: only where the Model column is exactly the end of What you get, word for word,
and nothing else stands after it; any other Model column (a model, the team's or QA's notes) is left as it is. Under the queue's lock, not while a
round of the review loop runs, through a temp file. A Ready mark from before F77 (on the old cells) is first given its ask, so no mark is lost.
The undo puts each cleared copy back where it stood, from the file this keeps."""
import json
import os
import sys
from pathlib import Path

WHAT = "A row's words are written once on the planning: the copy in the Model column of rows written by a call, a text or the status page is cleared."
KEPT = "HQ/data-changes-004.json"


def _routine():
    here = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(here))
    import hqpaths  # noqa: F401
    import jobs as q
    import sprint as S
    return hqpaths, q, S


def _rows(text):
    import re
    for i, line in enumerate(text.split("\n")):
        if line.startswith("| ") and re.match(r"^\| [^|]* \| [A-Z]\d+", line):
            yield i, line


def _write(path, text):
    tmp = f"{path}.004.{os.getpid()}"
    with open(tmp, "w", encoding="utf8") as f:
        f.write(text)
    os.replace(tmp, path)


def _no_round(folder):
    import roundlog
    d = roundlog.folder()
    if os.path.isdir(d) and any(n.startswith("job-") and n.endswith(".json") and n.count(".") == 1 for n in os.listdir(d)):
        raise RuntimeError("a round of the review loop is running; tried again next minute")


def do(folder):
    hqpaths, q, S = _routine()
    road = Path(folder) / "HQ" / "roadmap.md"
    if not road.exists():
        return
    _no_round(folder)
    with q.locked():
        text = road.read_text(encoding="utf8")
        lines = text.split("\n")
        kept = {}
        sp = Path(folder) / "HQ" / "sprint.json"  # this folder's own, never another's (datachange.py try runs this on a copy)
        d = json.loads(sp.read_text(encoding="utf8")) if sp.exists() else {}
        marks = json.loads(json.dumps(d.get("ready") or {}))  # a copy: only a mark that really changes rewrites the file
        moved = False
        for i, line in _rows(text):
            cs, spans = hqpaths.cells(line), hqpaths.cell_spans(line)
            if len(cs) < 4 or len(spans) != len(cs) or len(cs[3]) < 20 or not cs[2].endswith(cs[3]):  # the team's notes in a cell after it stay
                continue
            label = cs[1].split(" ", 1)[0]
            m = marks.get(label)
            if isinstance(m, dict) and not m.get("ask") and S.mark_holds(m, line):
                m["ask"] = S.ask_fp(line)
                moved = True
            a, b = spans[3]
            lines[i] = line[:a] + line[b:]
            kept[label] = {"was": line, "row": lines[i]}
        if not kept:
            return
        if moved:
            was = sp.read_text(encoding="utf8")
            d["ready"] = marks
            _write(str(sp), json.dumps(d, ensure_ascii=False, indent=1))
            kept["__sprint__"] = {"was": was, "row": sp.read_text(encoding="utf8")}  # the undo puts the file back as it was, if it's still this
        p = Path(folder) / KEPT
        old = json.loads(p.read_text(encoding="utf8")) if p.exists() else {}
        old.update(kept)
        _write(str(p), json.dumps(old, ensure_ascii=False, indent=1))
        hqpaths.guard_roadmap(str(road))
        _write(str(road), "\n".join(lines))


def undo(folder):
    hqpaths, q, S = _routine()
    road = Path(folder) / "HQ" / "roadmap.md"
    p = Path(folder) / KEPT
    if not road.exists() or not p.exists():
        return
    kept = json.loads(p.read_text(encoding="utf8"))
    with q.locked():
        text = road.read_text(encoding="utf8")
        lines = text.split("\n")
        for i, line in _rows(text):
            label = hqpaths.cells(line)[1].split(" ", 1)[0]
            k = kept.get(label)
            if k and line == k["row"]:  # only a row as this left it: one changed since is his
                lines[i] = k["was"]
        _write(str(road), "\n".join(lines))
        sp, k = Path(folder) / "HQ" / "sprint.json", kept.get("__sprint__")
        if k and sp.exists() and sp.read_text(encoding="utf8") == k["row"]:
            _write(str(sp), k["was"])
    p.unlink()
