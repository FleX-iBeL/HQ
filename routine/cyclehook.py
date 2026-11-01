#!/usr/bin/env python3
"""H298, piece 8: the tool hook of an agent's own cycle (a headless run as her, routine/cycles.py).

A shared file (the planning, the to-do list, the log, the mail list, the calendar, the games, the coaching marks)
has one serialized way in: HQ's own scripts (todo.py, sprint.py, jobs.py, pings.py, games.py) and, for the log and
the mail list, handover.py edit, which take the file's lock. A cycle that reaches for the file itself with Edit, Write
or a shell redirect is refused here, before anything is written, with the way in named; her ledger and her line she
writes freely. The run's stream shows the refusal, so after the run it's also a tripwire (cycles.after_run).

The hook reads the PreToolUse JSON on stdin: exit 0 lets the call through, exit 2 refuses it with the reason on
stderr. Nothing else is decided here; the box and the shares are the runner's.

F99 (30 October 2026): the same hook guards every team job against sending: any connector's send, reply or forward is
refused, whatever the connector is called. A team job needs the planning (it writes its results in the row), so only
a cycle gets the shared-file part: `--mail-only` is how a team job's settings call it.

F86: a round of the fix-and-review loop (`--fix LABEL fix|mark`) touches its one row, through its proper commands: a fix run adds to
it, a mark run marks it (a mark run doesn't add: rounds are counted, marks aren't, and that would be a loop with no cap), either puts it
on the sit-down list or says no; and her ledger. Reading stays free. Like the rest here it's a filter for an honest session: it reads
commands, not what a script does. What keeps the row safe is in the row's own doors: review.py adds and refuses the rest (HQ_ROUND),
sprint.py ready holds the mark.

F104, F103, F106 (fix round of batch 3): every job, whatever its kind, is kept off the work line on a friend's copy (any way of
moving the head onto commits she hasn't got released), off HQ's guard variables, off the switches and the two records, and it
can't write the ledger or start a helper, skip the pre-push hook, go back or forward a version, or run the data changes by hand. The hook reads
commands: what a script a job wrote does when it runs isn't seen here: a word filter for an honest job, not a wall. The words
of a command can't reach "never" for a friend's copy (`git checkout -` is ordinary git), so the plain ways stop here and the guard on the
state is the routine's: update.release_minute, the first thing in every minute.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SHARED = ("HQ/roadmap.md", "challenges.md", "coaching/log.md", "inbox.md", "HQ/calendar.json", "HQ/sprint.json",
          "HQ/games.json", "HQ/coaching.json", "HQ/calendar-todo.json", "HQ/calendar-marks.json", "HQ/mistakes.jsonl", "HQ/trail.jsonl")
FREE = ("HQ/ledger/", "HQ/direct-line/", "HQ/coaching-line/", "HQ/team-line/", "HQ/notes-")
EDITORS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
# F104, F103: the plain in-place writers: perl and ruby -i, gawk -i inplace, ed, ex, vim, sponge. What a script a job wrote does, a $(...) and
# a path in a variable stay outside this on purpose: a job is an honest model doing something by habit, and those aren't habits.
_IN_PLACE = (r"\b(?:perl|ruby)\s+(?:[^|&\n]*\s)?-[a-zA-Z0-9]*i[^\s]*\s[^|&\n]*{name}"
             r"|\bg?awk\s+(?:[^|&\n]*\s)?(?:-i\s*|--include[=\s]\s*)inplace\b[^|&\n]*{name}"
             r"|(?:^|[|;&(\n]\s*)(?:\S*/)?(?:ed|ex|vim?|nvim)\s[^;&\n]*{name}"
             r"|\bsponge\b[^|;&\n]*{name}")
# a shell write on the file itself: a redirect into it, sed -i, tee, a python open(..., "w") on it, or an in-place writer
_SHELL_WRITE = r"(>>?\s*\S*{name})|(sed\s+-i\S*\s.*{name})|(tee\s+(-a\s+)?\S*{name})|(open\(\s*[\"'][^\"']*{name}[\"']\s*,\s*[\"'][wa])|" + _IN_PLACE
# F104, F103: what no job writes, of any kind: the switches (features.py is the way, it keeps who and when) and the two records.
KEPT = ("HQ/features.json", "HQ/mistakes.jsonl", "HQ/trail.jsonl")
_KEPT_NAME = r"(?<![\w-])(?:features\.json|mistakes\.jsonl|trail\.jsonl)"
_KEPT_SHELL = re.compile(
    rf">>?\s*[^\s|;&]*{_KEPT_NAME}"
    rf"|\bsed\s+(?:-[a-zA-Z]*\s+)*-i[^|;&]*{_KEPT_NAME}"
    rf"|\btee\b[^|;&]*{_KEPT_NAME}"
    rf"|\b(?:cp|mv|rm|ln|truncate|dd|rsync|install|touch|chmod|unlink)\b[^|;&]*{_KEPT_NAME}"
    rf"|\b(?:python3?|perl|ruby|node)\b\s+(?:-[cCeE]\b|-\s|<<)[^|&]*{_KEPT_NAME}"
    rf"|\bgit\s+(?:\S+\s+)*(?:checkout|restore|rm|mv|reset|apply|am)\b[^|;&]*{_KEPT_NAME}"
    rf"|{_IN_PLACE.format(name=_KEPT_NAME)}", re.I)
# F104: what opens a gate when it's set by hand. HQ_ROUND (F86: a round only adds), HQ_MAKER (who the maker is), HQ_PRIVACY_PASSED (skips the pre-push hook), HQ_UNDER_TEST
# and HQ_PROOF_* (the gate on done), HQ_NO_WALL (the wall), HQ_ROLE_HERE (past the hand-over to the main), HQ_READY_FIELDS, HQ_REVIEW and
# HQ_REVIEW_FAKE (the ready check and the reviewer). HQ_IN_JOB has its own line below.
_GUARD = r"\bHQ_(?:MAKER|PRIVACY_PASSED|UNDER_TEST|PROOF_\w+|NO_WALL|ROLE_HERE|READY_FIELDS|REVIEW|REVIEW_FAKE|ROUND)\b"
_SETS_GUARD = re.compile(rf"{_GUARD}\s*\]?\s*(?:=(?!=)|:\s)"
                         rf"|\b(?:export|declare|typeset|readonly|local|unset|setenv|read)\b[^|;&\n]*{_GUARD}"
                         rf"|\benv\b[^|;&\n]*\s-u\s*{_GUARD}|\bprintf\s+-v\s*{_GUARD}"
                         rf"|\b(?:setdefault|putenv|setenv|pop|update)\W+{_GUARD}", re.I)
_MAKER_OFF = re.compile(r"\bHQ_MAKER\s*=\s*0(?=\s|$)")  # F104: only ever closes: qa.py's own advice for checking a feature in pieces
_JOB_NO_LEDGER = re.compile(r"(?<![\w-])mistakes\.py\s+(?:add|put)\b|-m\s+mistakes\b|\bpython\S*\s[^|&]*\b(?:import|from)\s+mistakes\b")
_JOB_NO_HELPER = re.compile(r"(?<![\w-])helper\.py\s+(?:start|run)\b|-m\s+helper\b|\bpython\S*\s[^|&]*\b(?:import|from)\s+helper\b")
_JOB_NO_VERSIONS = re.compile(r"(?<![\w-])update\.py\s+(?:back|forward)(?:-run|-here|-first)?\b")  # F104: his, they end what runs and move both computers
_GIT_CONFIG = re.compile(r"(?<![\w$])GIT_CONFIG_(?:COUNT|KEY_\w+|PARAMETERS)\s*=|\bexport\b[^;&|\n]*GIT_CONFIG_(?:COUNT|KEY_|PARAMETERS)")  # F104: config by the environment
_ONLY_SAYS = {"grep", "egrep", "fgrep", "rg", "ag", "cat", "head", "tail", "less", "more", "sed", "awk", "echo", "printf", "git", "ls", "wc", "diff", "sort", "uniq", "cut", "tr", "jq"}  # reads or prints its arguments
_SHELL = r"(?:^|[\s/])(?:ba|z|da|k)?sh"
_RUNS_SHELL = re.compile(rf"{_SHELL}\s+(?:-\S+\s+)*-\w*c\s*$|(?:^|\s)eval\s+$|{_SHELL}(?:\s+-\S+)*\s*<<<\s*$")
_RUNS_CODE = re.compile(r"\bpython[\d.]*\s+(?:-\S+\s+)*-c\s*$")
_FEEDS_SHELL = re.compile(rf"{_SHELL}(?:\s+-\S+)*\s*$")
_FEEDS_CODE = re.compile(r"\bpython[\d.]*(?:\s+-\S+)*\s*$")
_JOB_NO_DATA = re.compile(r"(?<![\w-])datachange\.py\s+apply\b")  # F104: the routine's minute does that, on what's committed and on dev
WAY = ("the planning through sprint.py, jobs.py or review.py reword, the to-do list through todo.py, the calendar through pings.py, "
       "the games through games.py, the log and the mail list through handover.py edit REL JSON; your ledger and "
       "your line you write freely")


def shared_name(path: str) -> str | None:
    p = (path or "").replace(os.sep, "/")
    if any(x in p for x in FREE):
        return None
    for s in SHARED:
        if p.endswith(s) or p.endswith("/" + s.split("/")[-1]) and s.split("/")[-1] in ("roadmap.md", "sprint.json", "calendar.json", "games.json", "coaching.json"):
            return s
    return None


def kept_name(path: str) -> str | None:
    p = (path or "").replace(os.sep, "/")
    return next((k for k in KEPT if (p == k or p.endswith("/" + k)) and "/template/" not in p), None)


def never_mail(name: str) -> bool:
    """F99: a connector's send, reply or forward, whatever the connector is called."""
    import hqpaths
    return name.startswith("mcp__") and name.rsplit("__", 1)[-1] in hqpaths.NEVER_MAIL


_WORK_LINE = re.compile(r"\bgit\b[^|;&]*\b(?:pull|merge|rebase|checkout|switch|reset|fetch)\b[^|;&]*\b(?:origin/)?(?:dev|nightly)\b"
                        r"|\bgit\b[^|;&]*\bpull\b"
                        r"|\bgit\b[^;&]*\b(?:show|diff|archive|format-patch)\b[^;&]*(?:origin/\S*|FETCH_HEAD|\bdev\b|\bnightly\b)[^;&]*(?:(?<!2)>|\|\s*(?:git\s+(?:apply|am)|patch|tar)\b)"
                        r"|\bgit\b[^|;&]*\bclone\b[^|;&]*(?:-b|--branch)[\s=]*(?:dev|nightly)\b"
                        r"|raw\.githubusercontent\.com/\S*/(?:dev|nightly)/|/(?:archive|tarball|zipball)/\S*(?:dev|nightly)")
_MOVES = {"merge", "rebase", "reset", "checkout", "switch", "cherry-pick", "restore", "read-tree", "update-ref", "symbolic-ref", "branch", "tag", "am"}
_GIT_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def plain(cmd: str) -> str:
    """A command as the shell reads it, near enough: d"e"v is dev, a Python list ['git','merge'] is git merge, $(x) stays a $."""
    return re.sub(r"[\[\](),]", " ", re.sub(r"[\"'\\]", "", re.sub(r"[\"']\s*,\s*[\"']", " ", cmd)))


def _git_hq(*args: str) -> subprocess.CompletedProcess:
    import hqpaths
    return subprocess.run(["git", "-C", hqpaths.HQ, *args], capture_output=True, text=True, timeout=20)


def _released(sha: str) -> bool:
    """F104: a commit this copy may stand on: already under its head, on a version tag, or on a branch of its own (not the work line)."""
    if not _git_hq("merge-base", "--is-ancestor", sha, "HEAD").returncode:
        return True
    r = _git_hq("for-each-ref", "--contains", sha, "--format=%(refname)", "refs/heads", "refs/tags/v*")
    return any(n not in ("refs/heads/dev", "refs/heads/nightly") for n in r.stdout.split())


def _unreleased(arg: str) -> bool:
    """F104: whether an argument of a command that moves the head names something off the release, or can't be read: what's only on
    GitHub's work line, FETCH_HEAD, a commit nobody here knows yet, a word the shell fills in later."""
    if "$" in arg or "`" in arg or "FETCH_HEAD" in arg:
        return True
    for part in filter(None, re.split(r"\.{2,3}", arg)):
        sha = _git_hq("rev-parse", "-q", "--verify", part + "^{commit}").stdout.strip()
        if sha and not _released(sha):
            return True
        if not sha and (re.match(r"(?:refs/|remotes/|origin/|upstream/)", part) or re.fullmatch(r"[0-9a-f]{7,40}", part) or "://" in part or part.startswith("git@")):
            return True
    return False


def off_the_release(cmd: str) -> bool:
    """F104: a job on a friend's HQ taking the work line, by hand, past push.py --pull: by its name or by any command that moves the
    head onto commits she hasn't got released. The name isn't enough: a fetch and a merge of FETCH_HEAD never says dev."""
    import hqpaths
    if hqpaths.is_maker():
        return False
    t = plain(cmd)
    if _WORK_LINE.search(t) or re.search(r"\bHQ_WORKSPACE\s*=", t):  # is_maker reads the workspace's features.json
        return True
    for piece in re.split(r"[;&|\n]+", t):
        m = re.search(r"\bgit\s(.*)", piece, re.S)
        if not m:
            continue
        words, i = m.group(1).split(), 0
        while i < len(words) and words[i].startswith("-"):
            i += 2 if words[i] in _GIT_ARG else 1
        sub, args = (words[i], words[i + 1:]) if i < len(words) else ("", [])
        if sub == "fetch" and any(":" in a and "://" not in a for a in args):  # into a branch of its own
            return True
        if sub in _MOVES:
            for a in args:
                if a == "--":
                    break
                a = a.split("=", 1)[1] if a.startswith("--") and "=" in a else a
                if not a.startswith("-") and _unreleased(a):
                    return True
    return False


def ran(cmd: str, depth: int = 0) -> str:
    """F104: a command with what would really run, near enough: a backslash line break is no break, and what only stands in it is out: what's inside
    quotes as an argument with spaces or shell marks in it (a commit message, a grep's pattern, a note), heredocs and comments. A quoted single word stays a word.
    What a shell or Python is handed to run, by -c, eval or a heredoc, stays in, read the same way: there the quotes are the command."""
    cmd = cmd.replace("\\\n", " ")
    out, piece, waiting, i = [], "", [], 0

    def put(s: str) -> None:
        nonlocal piece
        out.append(s)
        piece += s

    def given(body: str, shell: bool, code: bool) -> str:
        return ran(body, depth + 1) if shell and depth < 3 else plain(body) if code else ""

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
            waiting.append((m.group(1), bool(_FEEDS_SHELL.search(piece)), bool(_FEEDS_CODE.search(piece))))
            i += m.end()
        elif c == "\n":
            out.append(c)
            piece = ""
            i += 1
            for end, shell, code in waiting:
                body = []
                while i < len(cmd):
                    nl = cmd.find("\n", i)
                    nl = len(cmd) if nl < 0 else nl
                    line, i = cmd[i:nl], nl + 1
                    if line.strip() == end:
                        break
                    body.append(line)
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


def _says_only(piece: str) -> bool:
    """A command that only reads or prints its arguments, whatever they say."""
    words = [w for w in piece.split() if not re.match(r"[A-Za-z_]\w*=", w)]
    return bool(words) and os.path.basename(words[0]) in _ONLY_SAYS


def skips_hooks(t: str) -> bool:
    """F104: a push past the pre-push hook: --no-verify or its short forms, or git told to look for hooks elsewhere (`t` is what `ran` left). Read as
    git reads it; reading the setting is no such thing."""
    for piece in re.split(r"[;&|\n]+", t):
        m = re.search(r"\bgit\s(.*)", piece, re.S)
        if not m:
            continue
        words, i = m.group(1).split(), 0
        while i < len(words) and words[i].startswith("-"):
            set_by = words[i + 1] if words[i] in ("-c", "--config-env") and i + 1 < len(words) else words[i].split("=", 1)[1] if words[i].startswith("--config-env=") else ""
            if set_by.lower().startswith("core.hookspath"):
                return True
            i += 2 if words[i] in _GIT_ARG or words[i] == "--config-env" else 1
        sub, args = (words[i], words[i + 1:]) if i < len(words) else ("", [])
        if sub == "push" and any(len(a) >= len("--no-v") and "--no-verify".startswith(a) for a in args):
            return True
        low = [a.lower() for a in args]
        if sub == "config" and "core.hookspath" in low:
            at = low.index("core.hookspath")
            reads = {"get", "list", "unset", "--get", "--get-all", "--get-regexp", "--get-urlmatch", "--list", "-l", "--unset", "--unset-all"} & set(low[:at])
            if at + 1 < len(low) and not reads:
                return True
    return False


def job_guard(cmd: str) -> str | None:
    """What no job's shell command does, of any kind, in a refusal's words; None when it's fine."""
    t = plain(cmd)
    if _SETS_GUARD.search(_MAKER_OFF.sub(" ", t)):
        return "HQ: refused: this variable opens a gate, and a job never sets it itself."
    if _KEPT_SHELL.search(t) or "/api/features" in t:
        return "HQ: refused: the switches and the two records are never written by hand: python3 app/features.py on|off NAME, and the program's own lines."
    if _JOB_NO_LEDGER.search(t):
        return "HQ: refused: a job doesn't write the ledger; only the program's pass and the wrap-up do."
    if _JOB_NO_HELPER.search(t):
        return "HQ: refused: a helper is for calls and texts; a job has its own time."
    runs = ran(cmd)
    if skips_hooks(runs) or _GIT_CONFIG.search(runs):
        return "HQ: refused: a push goes through the pre-push hook, the privacy check; a job never skips it."
    pieces = [p for p in re.split(r"[;&|\n]+", runs) if not _says_only(p)]
    if any(_JOB_NO_VERSIONS.search(p) for p in pieces):
        return "HQ: refused: going back or forward a version is his, on a call or on the status page; a job never does it."
    if any(_JOB_NO_DATA.search(p) for p in pieces):
        return "HQ: refused: the routine runs the data changes, once they're committed and on dev; a job never runs them by hand."
    return None


# F86: what writes, besides role.WRITES (what a call may hand to the main); a round's own ways out are named in fix_guard.
_FIX_ALSO = {"cycles": {"ask", "batch", "text", "plan", "order", "set", "done", "failed", "proposal"}, "direct_line": None, "handover": None,
             "review": {"clear", "pass", "run", "golden", "tick"}, "set-status": None, "set_status": None, "notes": None, "gitlock": None, "push": None,
             "qa": {"pass", "fail", "queue"}, "jobs": {"mark", "held"}}
_SCRIPT = re.compile(r"(?<![\w-])([a-z_-]+)\.py\b\s*(\S+)?\s*(\S+)?")
_GIT_WRITES = {"checkout", "restore", "reset", "stash", "commit", "push", "pull", "fetch", "merge", "rebase", "apply", "am", "rm", "mv", "clean", "cherry-pick", "revert", "switch", "add",
               "update-ref", "read-tree", "worktree", "clone"}  # reading stays free
_BY_HAND = re.compile(r"\b(?:cp|mv|rm|ln|truncate|dd|rsync|install|unlink|tee)\b[^|;&\n]*(?:roadmap\.md|sprint\.json)")
_MCP_READS = re.compile(r"(?:get|list|search|read|query|suggest)")


def fix_guard(cmd: str, label: str, mode: str) -> str | None:
    """F86: what a round of the loop may not do with a shell command, in a refusal's words; None when it's fine."""
    import role
    no = (f"HQ: refused: this run is one round on {label}: only " + (f"sprint.py ready {label}" if mode == "mark" else f"review.py add {label}") +
          f", review.py sitdown {label}, review.py no {label}, your ledger, and reading. What's left goes on the sit-down list.")
    named = re.sub(r"[\"']([^\"'\n]*\.py)[\"']", lambda m: m.group(1).replace(" ", "_"), cmd)  # a path with a space in it stays one word
    for piece in re.split(r"[;&|\n]+", ran(named)):
        git = re.search(r"(?:^|\s)git\s+(?:(?:-C|-c|--git-dir|--work-tree)\s+\S+\s+|-\S+\s+)*([a-z-]+)", piece)
        if git and git.group(1) in _GIT_WRITES or _BY_HAND.search(piece):
            return no
        if _says_only(piece):
            continue
        for script, sub, arg in _SCRIPT.findall(piece):
            if script == "review" and sub in ("reword", "add", "sitdown", "no"):
                if arg.upper() != label or sub in ("reword", "add") and mode == "mark":
                    return no
            elif script == "sprint" and sub == "ready":
                if mode != "mark" or arg.upper() != label:
                    return no
            elif sub in role.WRITES.get(script, ()) or script in _FIX_ALSO and (_FIX_ALSO[script] is None or sub in _FIX_ALSO[script]):
                return no
    return None


def decide(ask: dict, mail_only: bool = False, fix: tuple | None = None) -> tuple[int, str]:
    name, inp = str(ask.get("tool_name", "")), ask.get("tool_input") or {}
    if never_mail(name):
        return 2, f"HQ: refused {name}: nothing is ever sent, replied to or forwarded from a job. A draft at the most."
    if name in EDITORS and ".status/proofs" in str(inp.get("file_path") or "").replace(os.sep, "/"):
        return 2, "HQ: refused: a build's record is written only by routine/proof.py."
    if name == "Bash" and off_the_release(str(inp.get("command") or "")):
        return 2, "HQ: refused: this HQ stays on its released version; a job here never takes the work line."
    if name == "Bash" and re.search(r"\.status/proofs", str(inp.get("command") or "")) and "proof.py" not in str(inp.get("command")):
        return 2, "HQ: refused: a build's record and its gate are the program's: routine/proof.py run N."
    if name in EDITORS and kept_name(str(inp.get("file_path") or inp.get("notebook_path") or "")):
        return 2, f"HQ: refused {name}: the switches and the two records are never written by hand; the switches go through python3 app/features.py on|off NAME."
    if name == "Bash":
        why = job_guard(str(inp.get("command") or ""))
        if why:
            return 2, why
    if name == "Bash" and re.search(r"jobs\.py[\"']?\s+(?:now\b|(?:add|add-row|send-row)\b[^\n]*\s--now\b)|/api/team\b|/api/sayso\b|/api/forward\b|\bHQ_IN_JOB\b", str(inp.get("command") or "")):
        return 2, "HQ: refused: a build in his day hours goes only on his own say-so; a job can't give it to itself."
    if mail_only:
        return 0, ""
    if fix and name in EDITORS and "HQ/ledger/" not in os.path.normpath(str(inp.get("file_path") or inp.get("notebook_path") or "")).replace(os.sep, "/"):
        return 2, f"HQ: refused {name}: this run is one round on {fix[0]}; it writes through review.py add and your ledger, nothing by hand."
    if fix and name.startswith("mcp__") and not _MCP_READS.match(name.rsplit("__", 1)[-1]):
        return 2, f"HQ: refused {name}: this run is one round on {fix[0]}; a round reads, it doesn't write to the calendar or the mail."
    if fix and name == "Bash":
        why = fix_guard(str(inp.get("command") or ""), *fix)
        if why:
            return 2, why
    if name in EDITORS:
        s = shared_name(str(inp.get("file_path") or inp.get("notebook_path") or ""))
        if s:
            return 2, f"HQ: refused {name} on {s}: a shared file is written only through HQ's own scripts ({WAY})."
        return 0, ""
    if name == "Bash":
        cmd = str(inp.get("command") or "")
        for s in SHARED:
            if re.search(_SHELL_WRITE.format(name=re.escape(s.split("/")[-1])), cmd):
                if "handover.py" in cmd or any(x in cmd for x in ("todo.py", "sprint.py", "jobs.py", "pings.py", "games.py", "coaching.py", "review.py")):
                    continue
                return 2, f"HQ: refused a shell write on {s}: a shared file is written only through HQ's own scripts ({WAY})."
    return 0, ""


def main() -> int:
    try:
        ask = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    a = sys.argv[1:]
    code, why = decide(ask, "--mail-only" in a, (a[a.index("--fix") + 1].upper(), a[a.index("--fix") + 2]) if "--fix" in a else None)
    if code:
        print(why, file=sys.stderr)
        if never_mail(str(ask.get("tool_name", ""))):  # F103: a refused outward action is a mistake on the ledger
            try:
                import mistakes
                mistakes.add("refused", os.environ.get("HQ_JOB_AGENT") or "team", why, where=f"job {os.environ.get('HQ_IN_JOB', '')}".strip(),
                             key=f"refused|{ask.get('tool_name')}|{json.dumps(ask.get('tool_input') or {}, sort_keys=True)[:200]}")
            except Exception:
                pass
    return code


if __name__ == "__main__":
    sys.exit(main())
