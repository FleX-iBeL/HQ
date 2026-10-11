"""The call transcript: one Markdown file per call, written line by line as the call goes.

Each line is appended and flushed straight away, so a crash loses at most the reply that
was still being spoken. File name: HQ/calls/YYYY-MM-DD-HHMM.md, in this Mac's time zone, at the
time of the call start (a second call in the same minute gets -2, -3, ...).

What goes in:
  **<Name>** what they said (the name from me.md, else Me) (as Whisper heard it)        · (cut in) when he talked over HQ
                                                         · (typed) when he typed it on the call page (H18)
                                                         · (cancelled) when he tapped Cancel before she answered (H31)
  **HQ** what Claude said (before H54: **Jarvis**)          · (cut off) when he stopped it
  *filler* what the call system said while Claude worked (not Claude's words; Claude never sees them)
  `tool` one short line per tool call, with the decision (done / asked / refused)
  *call* call system notes (permission answers, connect, hang-up, after-call work)

H6: on_line, when set, is told every spoken line as it is written (who, text), so the call
page can show the chat log. H7 (free mode): keep=False writes no file at all; on_line still works.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import config

TZ = ZoneInfo(config.TIMEZONE)


def now() -> datetime:
    return datetime.now(TZ)


class CallTranscript:
    def __init__(self, folder: Path | None = None, *, model: str = "", started: datetime | None = None,
                 keep: bool = True, agent: str = "", continues: dict | None = None):
        self.started = started or now()
        self.on_line: Callable[[str, str], None] | None = None  # H6: (who, text) for the call page
        self.path: Path | None = None
        self._last_user = ""  # H31: the last line he said, so Cancel can mark it
        if not keep:
            return  # H7: free mode, nothing written to disk
        folder = folder or config.CALLS
        folder.mkdir(parents=True, exist_ok=True)
        base = self.started.strftime("%Y-%m-%d-%H%M")
        path = folder / f"{base}.md"
        n = 2
        while path.exists():
            path = folder / f"{base}-{n}.md"
            n += 1
        self.path = path
        self._write(
            f"# Call {self.started.strftime('%-d %B %Y, %H:%M')}\n\n"
            "> **Private.** Only for this workspace. A HQ call, "
            "written down as it happened.\n\n"
            f"Started {self.started.strftime('%H:%M:%S')} · " + (f"agent {agent} · " if agent else "")
            + f"brain {model or config.MODEL}\n\n"
            # H60: a call that continues an earlier one says which, so it can be found back
            + (f"Continues the call of {continues['started']} ({continues['name']})\n\n" if continues else "")
        )

    @property
    def start_hhmm(self) -> str:
        return self.started.strftime("%H:%M")

    def _write(self, text: str) -> None:
        if self.path is None:
            return
        with open(self.path, "a", encoding="utf8") as f:
            f.write(text)
            f.flush()

    def _line(self, text: str) -> None:
        self._write(f"- {now().strftime('%H:%M:%S')} {text}\n")

    def _tell(self, who: str, text: str) -> None:
        if self.on_line and text:
            try:
                self.on_line(who, text)
            except Exception:
                pass

    def user(self, words: str, *, cut_in: bool = False, typed: bool = False, button: bool = False) -> None:
        """button (H38): the line came from the Cancel button, tapped after she had started answering."""
        self._tell("user", _one_line(words) + (" (Cancel button)" if button else ""))
        line = (f"- {now().strftime('%H:%M:%S')} **{config.USER_LABEL}:** {_one_line(words)}" + (" *(typed)*" if typed else "")
                + (" *(Cancel button)*" if button else "") + (" *(cut in)*" if cut_in else ""))
        self._last_user = line
        self._write(line + "\n")

    def cancel_last(self) -> None:
        """H31: he tapped Cancel before she answered: his last line gets *(cancelled)*."""
        line, self._last_user = self._last_user, ""
        if not line or self.path is None:
            return
        try:
            text = self.path.read_text(encoding="utf8")
            i = text.rfind(line + "\n")
            if i >= 0:
                text = text[:i] + line + " *(cancelled)*" + text[i + len(line):]
                self.path.write_text(text, encoding="utf8")
        except OSError:
            pass

    def reply(self, words: str, *, cut_off: bool = False) -> None:
        words = _one_line(words)
        if not words and not cut_off:
            return
        self._tell("hq", (words or "…") + (" (cut off)" if cut_off else ""))
        if cut_off:
            self._line(f"**HQ:** {words or '…'} *(cut off)*")
        else:
            self._line(f"**HQ:** {words}")

    def filler(self, words: str) -> None:
        self._tell("filler", _one_line(words))
        self._line(f"*filler: {words}*")

    def tool(self, summary: str, verdict: str, why: str) -> None:
        label = {"allow": "done", "ask": f"asked {config.USER_LABEL}", "deny": "refused"}.get(verdict, verdict)
        self._line(f"`{_one_line(summary)}` · {label} ({why})")

    def note(self, text: str) -> None:
        self._line(f"*call: {_one_line(text)}*")

    def end(self) -> None:
        self._write(f"\nEnded {now().strftime('%H:%M:%S')}\n")


# Her lines: **HQ:** since H54 (11 October 2026); saved calls from before still say the old name.
_HERS = ("**HQ:** ", "**Jarvis:** ")
_LINE = re.compile(r"^- (\d\d:\d\d):\d\d (.*)$")
_MARK = re.compile(r"\s*\*\((typed|cut in|cut off|cancelled|Cancel button)\)\*\s*$")


def _sort_key(path: Path) -> tuple[str, int]:
    """2026-10-10-1727.md, then 2026-10-10-1727-2.md: a second call in the same minute is later."""
    m = re.match(r"^(\d{4}-\d\d-\d\d-\d{4})(?:-(\d+))?$", path.stem)
    return (m.group(1), int(m.group(2) or 1)) if m else ("", 0)


def read_lines(path: Path) -> list[dict]:
    """H34: what was said on a saved call, the way the chat on the call page shows it:
    his lines, her lines and her waiting lines. Tool lines and call notes are left out."""
    out = []
    for raw in path.read_text(encoding="utf8").splitlines():
        m = _LINE.match(raw)
        if not m:
            continue
        hhmm, rest = m.groups()
        marks = []
        while (mm := _MARK.search(rest)):
            marks.insert(0, mm.group(1))
            rest = rest[:mm.start()]
        if rest.startswith(f"**{config.USER_LABEL}:** "):
            text = rest[len(config.USER_LABEL) + 5:].strip() + (" (Cancel button)" if "Cancel button" in marks else "")
            out.append({"who": "user", "text": text, "at": hhmm, "cancelled": "cancelled" in marks})
        elif rest.startswith(_HERS):
            text = rest.split(":** ", 1)[1].strip() + (" (cut off)" if "cut off" in marks else "")
            out.append({"who": "hq", "text": text, "at": hhmm})
        elif rest.startswith("*filler: ") and rest.endswith("*"):
            out.append({"who": "filler", "text": rest[9:-1].strip(), "at": hhmm})
    return [line for line in out if line["text"]]


_NAME = re.compile(r"^\d{4}-\d\d-\d\d-\d{4}(?:-\d+)?$")
_AGENT = re.compile(r"^Started [\d:]+ · agent ([^·]+?) · ", re.M)
_CONTINUES = re.compile(r"^Continues the call of .+ \((\d{4}-\d\d-\d\d-\d{4}(?:-\d+)?)\)$", re.M)


def _calls(folder: Path) -> list[Path]:
    """The saved calls, newest first."""
    try:
        return sorted((p for p in folder.glob("*.md") if _sort_key(p)[0]), key=_sort_key, reverse=True)
    except OSError:
        return []


def _said(lines: list[dict]) -> bool:
    return any(line["who"] != "filler" for line in lines)


def _about(path: Path, lines: list[dict]) -> dict:
    day, hhmm = _sort_key(path)[0].rsplit("-", 1)
    started = datetime.strptime(day + hhmm, "%Y-%m-%d%H%M")
    try:
        head = path.read_text(encoding="utf8")[:800]
    except OSError:
        head = ""
    m, c = _AGENT.search(head), _CONTINUES.search(head)
    return {"name": path.stem, "started": started.strftime("%-d %B, %H:%M"), "date": started.strftime("%Y-%m-%d"),
            "time": started.strftime("%H:%M"), "agent": m.group(1).strip() if m else "",
            "continues": c.group(1) if c else ""}


def last_call(folder: Path | None = None) -> dict | None:
    """H34: the most recent saved call where something was said, read only. None if there is none."""
    for path in _calls(folder or config.CALLS):
        try:
            lines = read_lines(path)
        except OSError:
            continue
        if _said(lines):
            return {**_about(path, lines), "lines": lines}
    return None


def list_calls(folder: Path | None = None) -> list[dict]:
    """H57: every saved call where something was said, newest first, read only: when, which agent
    (older calls had none), and how many lines he and she said. Free calls are never saved, so never here."""
    out = []
    for path in _calls(folder or config.CALLS):
        try:
            lines = read_lines(path)
        except OSError:
            continue
        if _said(lines):
            out.append({**_about(path, lines), "said": sum(1 for line in lines if line["who"] != "filler")})
    return out


def read_call(name: str, folder: Path | None = None) -> dict | None:
    """H57: one saved call by its name (as list_calls gives it), read only, the way the chat shows it.
    None for a name that isn't a saved call's, so nothing outside the calls folder can be asked for."""
    if not _NAME.match(name or ""):
        return None
    path = (folder or config.CALLS) / f"{name}.md"
    try:
        lines = read_lines(path)
    except OSError:
        return None
    return {**_about(path, lines), "lines": lines}


def continue_from(name: str, folder: Path | None = None, max_chars: int | None = None) -> dict | None:
    """H60: an earlier saved call, to continue on a new call: when it was, its agent, and what was said
    as a block of text for the new call's Claude (his lines and hers as read_lines gives them, her waiting
    lines and cancelled lines left out). A long call is trimmed from the start, so the newest is kept.
    None when it isn't a saved call or nothing was said on it."""
    data = read_call(name, folder)
    if not data:
        return None
    limit = config.CONTINUE_MAX_CHARS if max_chars is None else max_chars
    said = [ln for ln in data["lines"] if ln["who"] != "filler" and not ln.get("cancelled")]
    if not said:
        return None
    rows = [f"{ln['at']} {config.USER_LABEL if ln['who'] == 'user' else 'You'}: {ln['text']}" for ln in said]
    kept, size = [], 0
    for row in reversed(rows):
        if kept and size + len(row) + 1 > limit:
            break
        kept.insert(0, row)
        size += len(row) + 1
    text = "\n".join(kept)
    if len(kept) < len(rows):
        text = f"(the first {len(rows) - len(kept)} lines left out, the call was long)\n" + text
    return {**{k: data[k] for k in ("name", "started", "date", "time", "agent")}, "text": text,
            "lines": len(said), "trimmed": len(rows) - len(kept)}


def _one_line(text: str) -> str:
    return " ".join((text or "").split()).replace("`", "'")
