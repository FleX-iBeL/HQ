"""Reading a shell line the way the policy needs it: what would really run, past the wrappers, the quotes, heredocs and comments.

    shellread.ran(cmd)        the command with only what would run in it (quoted arguments with spaces and heredocs are out; what a
                              shell or Python is handed to run by -c, eval or a heredoc stays in, read the same way)
    shellread._program(piece) the words of one piece of a line, starting at what really runs (past VAR=x and the wrappers)

app/policy.py uses these to tell a read from a write and to see a program that starts another model. Standard library only.
"""
from __future__ import annotations

import os
import re

_SHELL = r"(?:^|[\s/])(?:ba|z|da|k)?sh"
_RUNS_SHELL = re.compile(rf"{_SHELL}\s+(?:-\S+\s+)*-\w*c\s*$|(?:^|\s)eval\s+$|{_SHELL}(?:\s+-\S+)*\s*<<<\s*$")
_RUNS_CODE = re.compile(r"\bpython[\d.]*\s+(?:(?:-[XW]\s+\S+|-\S+)\s+)*-c\s*$")  # -X and -W take a value
_FEEDS_SHELL = re.compile(rf"{_SHELL}(?:\s+-\S+)*\s*$")
_FEEDS_CODE = re.compile(r"\bpython[\d.]*(?:\s+-\S+)*\s*$")

RUNS = {"claude", "codex", "openclaw"}
WRAPPERS = {"env", "command", "exec", "time", "nice", "ionice", "timeout", "stdbuf", "xargs", "builtin", "eval", "bash", "sh", "zsh", "dash", "ksh",
            "do", "then", "else", "elif", "if", "while", "until", "{", "!"}

_RUNS_CODE_TEXT = re.compile(r"\b(?:python[\d.]*|node|perl|ruby)\b(?:[^\n|;&]*?\s-[a-zA-Z]*[cCeE]\b|(?:\s+(?:-[XW]\s+\S+|-[a-zA-Z]+))*\s+-?\s*<<)")

_LANGS = {"node": "node", "nodejs": "node", "perl": "perl", "ruby": "ruby"}
_CODE_FLAG = {"node": re.compile(r"-[a-zA-Z]*[ep]|--(?:eval|print)=?|<<<"), "perl": re.compile(r"-[a-zA-Z]*[eE]|<<<"), "ruby": re.compile(r"-[a-zA-Z]*e|<<<")}
_VALUE_FLAG = re.compile(r"-[rIMmxCW]|--(?:require|import|loader|experimental-loader|input-type|title)")
_MODULE_FLAG = {"node": re.compile(r"(?:-r|--require|--import)(?:=|\s+)(\S+)"), "perl": re.compile(r"(?<!\S)-[Mm]-?\s*([\w:]+)"), "ruby": re.compile(r"(?<!\S)-r\s*(\S+)")}
_MODULE_AS = {"node": "require('{}');", "perl": "use {};", "ruby": "require '{}';"}

def _program(piece: str) -> list:
    """The words of a piece of a shell line, starting at what really runs: past VAR=x and the wrappers."""
    words = [w for w in piece.split() if not re.match(r"[A-Za-z_]\w*=", w)]
    while words and os.path.basename(words[0]) in WRAPPERS:
        words = words[1:]
        while words and (words[0].startswith("-") or re.fullmatch(r"[\d.]+[smhd]?", words[0])):
            words = words[1:]
    return words

def plain(cmd: str) -> str:
    """A command as the shell reads it, near enough: d"e"v is dev, a Python list ['git','merge'] is git merge, $(x) stays a $."""
    return re.sub(r"[\[\](),]", " ", re.sub(r"[\"'\\]", "", re.sub(r"[\"']\s*,\s*[\"']", " ", cmd)))

def inline_lang(piece: str, fed: bool = False) -> str | None:
    """F118: the language when this piece of a line is node, perl or ruby about to be handed code: by -e (node also -p, --eval, --print) after
    only its own flags (their values, and perl's earlier -e code), or, `fed`, a heredoc to the runner itself. None for a script run by its name."""
    words = _program(piece)
    lang = _LANGS.get(re.sub(r"[\d.]+$", "", os.path.basename(words[0]))) if words else None
    if not lang:
        return None
    rest = words[1:]
    if fed:
        return lang if all(w.startswith("-") for w in rest) else None
    if not rest or not _CODE_FLAG[lang].fullmatch(rest[-1]):
        return None
    for i, w in enumerate(rest[:-1]):
        if not w.startswith("-") and not (i and (_VALUE_FLAG.fullmatch(rest[i - 1]) or _CODE_FLAG[lang].fullmatch(rest[i - 1]))):
            return None
    return lang

def _with_modules(lang: str, piece: str, code: str) -> str:
    """F118: a module the runner is told to load by a flag (perl -MIO::Socket, ruby -rsocket, node -r https) counts as part of its code."""
    return "".join(_MODULE_AS[lang].format(m) + "\n" for m in _MODULE_FLAG[lang].findall(piece)) + code

def ran(cmd: str, depth: int = 0, found: list | None = None) -> str:
    """F104: a command with what would really run, near enough: a backslash line break is no break, and what only stands in it is out: what's inside
    quotes as an argument with spaces or shell marks in it (a commit message, a grep's pattern, a note), heredocs and comments. A quoted single word stays a word.
    What a shell or Python is handed to run, by -c, eval or a heredoc, stays in, read the same way: there the quotes are the command.
    F118: `found` collects what node, perl or ruby are handed to run, as (language, code), also inside a shell's -c or heredoc."""
    cmd = cmd.replace("\\\n", " ")
    out, piece, waiting, i = [], "", [], 0

    def put(s: str) -> None:
        nonlocal piece
        out.append(s)
        piece += s

    def given(body: str, shell: bool, code: bool) -> str:
        return ran(body, depth + 1, found) if shell and depth < 3 else plain(body) if code else ""

    while i < len(cmd):
        c = cmd[i]
        if c == "\\" and i + 1 < len(cmd):
            put(cmd[i + 1])
            i += 2
        elif c in "'\"":
            j, buf = i + 1, ""
            while j < len(cmd) and cmd[j] != c:
                j += 1 if c == '"' and cmd[j] == "\\" else 0
                buf += cmd[j:j + 1]
                j += 1
            i = j + 1
            lang = inline_lang(piece) if found is not None else None
            if lang:
                found.append((lang, _with_modules(lang, piece, buf)))
            runs = given(buf, bool(_RUNS_SHELL.search(piece)), bool(_RUNS_CODE.search(piece)))
            put(f" {runs} " if runs else buf if not re.search(r"[\s;&|]", buf) else " Q ")  # a grep's 'a|b' is one argument, no pipe
        elif c == "#" and (not piece or piece[-1].isspace()):
            while i < len(cmd) and cmd[i] != "\n":
                i += 1
        elif cmd.startswith("<<<", i):
            put("<<<")
            i += 3
        elif re.match(r"<<-?\s*['\"\\]?[\w.-]+", cmd[i:]):
            m = re.match(r"<<-?\s*['\"\\]?([\w.-]+)['\"]?", cmd[i:])
            waiting.append((m.group(1), bool(_FEEDS_SHELL.search(piece)), bool(_FEEDS_CODE.search(piece)), inline_lang(piece, fed=True) if found is not None else None, piece))
            i += m.end()
        elif c == "\n":
            out.append(c)
            piece = ""
            i += 1
            for end, shell, code, lang, at in waiting:
                body = []
                while i < len(cmd):
                    nl = cmd.find("\n", i)
                    nl = len(cmd) if nl < 0 else nl
                    line, i = cmd[i:nl], nl + 1
                    if line.strip() == end:
                        break
                    body.append(line)
                if lang:
                    found.append((lang, _with_modules(lang, at, "\n".join(body))))
                out.append(given("\n".join(body), shell, code) + "\n")
            waiting = []
        elif c in ";&|":
            out.append(c)
            piece = ""
            i += 1
        else:
            put(c)
            i += 1
    return "".join(out)

