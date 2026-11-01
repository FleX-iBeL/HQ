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

F104, F103, F106 (fix round of batch 3): every job, whatever its kind, is kept off the work line on a friend's copy (any way of
moving the head onto commits she hasn't got released), off HQ's guard variables, off the switches and the two records, and it
can't write the ledger or start a helper. The hook reads commands: what a script a job wrote does when it runs isn't seen here. The words
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
# F104: what opens a gate when it's set by hand. HQ_MAKER (who the maker is), HQ_PRIVACY_PASSED (skips the pre-push hook), HQ_UNDER_TEST
# and HQ_PROOF_* (the gate on done), HQ_NO_WALL (the wall), HQ_ROLE_HERE (past the hand-over to the main), HQ_READY_FIELDS, HQ_REVIEW and
# HQ_REVIEW_FAKE (the ready check and the reviewer). HQ_IN_JOB has its own line below.
_GUARD = r"\bHQ_(?:MAKER|PRIVACY_PASSED|UNDER_TEST|PROOF_\w+|NO_WALL|ROLE_HERE|READY_FIELDS|REVIEW|REVIEW_FAKE)\b"
_SETS_GUARD = re.compile(rf"{_GUARD}\s*\]?\s*(?:=(?!=)|:\s)"
                         rf"|\b(?:export|declare|typeset|readonly|local|unset|setenv|read)\b[^|;&\n]*{_GUARD}"
                         rf"|\benv\b[^|;&\n]*\s-u\s*{_GUARD}|\bprintf\s+-v\s*{_GUARD}"
                         rf"|\b(?:setdefault|putenv|setenv|pop|update)\W+{_GUARD}", re.I)
_MAKER_OFF = re.compile(r"\bHQ_MAKER\s*=\s*0(?=\s|$)")  # F104: only ever closes: qa.py's own advice for checking a feature in pieces
_JOB_NO_LEDGER = re.compile(r"(?<![\w-])mistakes\.py\s+(?:add|put)\b|-m\s+mistakes\b|\bpython\S*\s[^|&]*\b(?:import|from)\s+mistakes\b")
_JOB_NO_HELPER = re.compile(r"(?<![\w-])helper\.py\s+(?:start|run)\b|-m\s+helper\b|\bpython\S*\s[^|&]*\b(?:import|from)\s+helper\b")
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
    return None


def decide(ask: dict, mail_only: bool = False) -> tuple[int, str]:
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
    code, why = decide(ask, "--mail-only" in sys.argv[1:])
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
