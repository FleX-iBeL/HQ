"""The call transcript: one Markdown file per call, written line by line as the call goes.

Each line is appended and flushed straight away, so a crash loses at most the reply that
was still being spoken. File name: Jarvis VA/calls/YYYY-MM-DD-HHMM.md, in this Mac's time zone, at the
time of the call start (a second call in the same minute gets -2, -3, ...).

What goes in:
  **<Name>** what they said (the name from me.md, else Me) (as Whisper heard it)        · (cut in) when he talked over Jarvis
                                                         · (typed) when he typed it on the call page (H18)
                                                         · (cancelled) when he tapped Cancel before she answered (H31)
  **Jarvis** what Claude said                            · (cut off) when he stopped it
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
                 keep: bool = True, agent: str = ""):
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
            "> **Private.** Only for this workspace. A Jarvis VA call, "
            "written down as it happened.\n\n"
            f"Started {self.started.strftime('%H:%M:%S')} · " + (f"agent {agent} · " if agent else "")
            + f"brain {model or config.MODEL}\n\n"
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

    def jarvis(self, words: str, *, cut_off: bool = False) -> None:
        words = _one_line(words)
        if not words and not cut_off:
            return
        self._tell("jarvis", (words or "…") + (" (cut off)" if cut_off else ""))
        if cut_off:
            self._line(f"**Jarvis:** {words or '…'} *(cut off)*")
        else:
            self._line(f"**Jarvis:** {words}")

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


_LINE = re.compile(r"^- (\d\d:\d\d):\d\d (.*)$")
_MARK = re.compile(r"\s*\*\((typed|cut in|cut off|cancelled|Cancel button)\)\*\s*$")


def _sort_key(path: Path) -> tuple[str, int]:
    """2026-10-10-1727.md, then 2026-10-10-1727-2.md: a second call in the same minute is later."""
    m = re.match(r"^(\d{4}-\d\d-\d\d-\d{4})(?:-(\d+))?$", path.stem)
    return (m.group(1), int(m.group(2) or 1)) if m else ("", 0)


def read_lines(path: Path) -> list[dict]:
    """H34: what was said on a saved call, the way the chat on the call page shows it:
    his lines, Jarvis's lines and her waiting lines. Tool lines and call notes are left out."""
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
        elif rest.startswith("**Jarvis:** "):
            text = rest[12:].strip() + (" (cut off)" if "cut off" in marks else "")
            out.append({"who": "jarvis", "text": text, "at": hhmm})
        elif rest.startswith("*filler: ") and rest.endswith("*"):
            out.append({"who": "filler", "text": rest[9:-1].strip(), "at": hhmm})
    return [line for line in out if line["text"]]


def last_call(folder: Path | None = None) -> dict | None:
    """H34: the most recent saved call where something was said, read only. None if there is none."""
    folder = folder or config.CALLS
    try:
        paths = sorted((p for p in folder.glob("*.md") if _sort_key(p)[0]), key=_sort_key, reverse=True)
    except OSError:
        return None
    for path in paths:
        try:
            lines = read_lines(path)
        except OSError:
            continue
        if any(line["who"] != "filler" for line in lines):
            day, hhmm = _sort_key(path)[0].rsplit("-", 1)
            started = datetime.strptime(day + hhmm, "%Y-%m-%d%H%M")
            return {"name": path.stem, "started": started.strftime("%-d %B, %H:%M"),
                    "date": started.strftime("%Y-%m-%d"), "lines": lines}
    return None


def _one_line(text: str) -> str:
    return " ".join((text or "").split()).replace("`", "'")
