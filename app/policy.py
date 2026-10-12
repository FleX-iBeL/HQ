"""What HQ may do on a call without asking, what it must ask for, and what never.

One place, readable top to bottom. Every tool call of the call's Claude session goes
through decide(); the brain wires it in twice:

- a PreToolUse hook, which sees every call, also ones that a settings "allow" rule would
  let through without asking (the folder's settings.local.json allows `Bash(git add *)`,
  which would also allow `git add -A`);
- can_use_tool, the SDK's permission prompt, for whatever still reaches a prompt.

The three answers:
  ALLOW  go ahead.
  ASK    HQ asks the user out loud ("Can I …? Say yes or no."). The call is refused
         for now; the next thing they say decides. A clear yes approves exactly that
         call once (same tool, same input), and Claude makes it again.
  DENY   never, not even with a yes.

Two switches: unattended (after hang-up: nobody to ask, so ASK means no) and dry_run
(tests: no file changes, no git, and even a yes doesn't let a change through).
"""
from __future__ import annotations

import json
import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

# M1: the routine's scripts a call may run (the queue, the usage, lid-closed sleep) are HQ's own.
HQ_ROUTINE = Path(os.path.realpath(Path(__file__).resolve().parent.parent / "routine"))
# H65: HQ itself (the app: its code, logs and the status page's data). A call reads it freely, like the
# workspace; changing anything in it still asks.
HQ_ROOT = Path(os.path.realpath(Path(__file__).resolve().parent.parent))
# H65: the status page's server, on this computer only. A call may read its pages (GET), nothing else.
STATUS_HOSTS = ("localhost", "127.0.0.1")
STATUS_PORT = os.environ.get("HQ_STATUS_PORT", "4748")
CURL_SAFE_FLAGS = {"-s", "-S", "-sS", "-Ss", "-f", "-fs", "-sf", "-fsS", "-sSf", "-L", "-m", "--max-time",
                   "--silent", "--show-error", "--fail", "--compressed", "-g", "--globoff"}

ALLOW, ASK, DENY = "allow", "ask", "deny"


@dataclass
class Decision:
    verdict: str  # ALLOW, ASK or DENY
    why: str  # one short line, for the log and the transcript
    question: str = ""  # for ASK: what HQ asks, in plain words


# -- the lists -------------------------------------------------------------------

# Harmless helpers of the session itself (loading tools, its own to-do list, skills).
SESSION_TOOLS = {
    "ToolSearch", "Skill", "TaskCreate", "TaskGet", "TaskList", "TaskUpdate", "TaskOutput",
}
READ_TOOLS = {"Read", "Glob", "Grep", "LS"}
EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}

# Connectors are matched by server name, so they work whatever prefix the CLI gives them
# (mcp__claude_ai_Google_Calendar__list_events in the CLI).
CALENDAR_READ = {"list_calendars", "list_events", "get_event", "search_events", "suggest_time"}
GMAIL_READ = {"search_threads", "get_thread", "get_message", "list_drafts", "get_draft", "list_labels"}
GMAIL_NEVER = {"send_message", "send", "reply", "forward", "send_draft"}

# Tools that make no sense on a call; they are also removed from the session.
CALL_UNFRIENDLY = [
    "AskUserQuestion", "EnterPlanMode", "ExitPlanMode", "EnterWorktree", "ExitWorktree",
    "NotebookEdit", "Workflow", "CronCreate", "CronDelete", "ScheduleWakeup", "RemoteTrigger",
    "DesignSync",
]

# Read-only shell commands that may run without asking, as long as every path they touch
# is inside the folder.
SAFE_READ_COMMANDS = {"ls", "grep", "rg", "find", "wc", "head", "tail", "cat", "pwd", "date", "stat", "file",
                      "ps", "pgrep", "which", "echo", "sort", "uniq", "du"}
SAFE_GIT_READ = {"status", "log", "diff", "show", "rev-parse", "branch", "ls-files"}


def gmail_never_tool_names(prefixes: tuple[str, ...] = ("mcp__claude_ai_Gmail__",)) -> list[str]:
    return [p + name for p in prefixes for name in sorted(GMAIL_NEVER)]


@dataclass
class Policy:
    folder: Path
    dry_run: bool = False  # tests: nothing may change, not even with a yes
    unattended: bool = False  # after hang-up: nobody can answer a question
    # Calls the user was asked about, waiting for his answer, and the ones he said yes to.
    pending: list[tuple[str, str, str]] = field(default_factory=list)  # (tool, key, question)
    approved: set[tuple[str, str]] = field(default_factory=set)
    log: list[tuple[str, str, Decision]] = field(default_factory=list)  # (tool, summary, decision)
    listener: object = None  # called as listener(tool, summary, decision), e.g. the transcript

    def __post_init__(self):
        self.folder = Path(os.path.realpath(self.folder))
        # M5: folders in the workspace that are never changed and never go to git, from me.md.
        import me as _me
        self.protected = set(_me.load(self.folder)["protected"])

    # -- the decision -----------------------------------------------------------

    def decide(self, tool: str, inp: dict) -> Decision:
        d = self._decide(tool, inp or {})
        if self.dry_run and d.verdict == ALLOW and _writes(tool, inp or {}):
            d = Decision(DENY, "test run: no changes allowed")
        if d.verdict == ASK:
            key = _key(inp)
            if (tool, key) in self.approved:
                self.approved.discard((tool, key))
                if self.dry_run:
                    d = Decision(DENY, f"test run: the yes is noted, but nothing changes ({d.why})")
                else:
                    d = Decision(ALLOW, f"they said yes ({d.why})")
            elif self.unattended:
                d = Decision(DENY, f"nobody to ask after the call ({d.why})")
            else:
                if not any(p[0] == tool and p[1] == key for p in self.pending):
                    self.pending.append((tool, key, d.question))
        summary = summarize(tool, inp or {})
        self.log.append((tool, summary, d))
        if callable(self.listener):
            try:
                self.listener(tool, summary, d)
            except Exception:
                pass
        return d

    def _decide(self, tool: str, inp: dict) -> Decision:
        server, name = _mcp_parts(tool)
        if server:
            s = server.lower()
            if "gmail" in s:
                if name in GMAIL_NEVER or "send" in name:
                    return Decision(DENY, "sending, replying and forwarding email is never allowed")
                if name in GMAIL_READ:
                    return Decision(ALLOW, "reading mail")
                return _ask(f"{_plain(name)} in your Gmail", "a Gmail change")
            if "calendar" in s:
                if name in CALENDAR_READ:
                    return Decision(ALLOW, "reading the calendar")
                return _ask(_calendar_question(name, inp), "a calendar change")
            return _ask(f"use {_plain(name)} in {server.replace('_', ' ')}", "another connector")

        if tool in SESSION_TOOLS:
            return Decision(ALLOW, "session helper")
        if tool in READ_TOOLS:
            path = inp.get("file_path") or inp.get("path") or str(self.folder)
            if self.inside(path):
                return Decision(ALLOW, "reading in the folder")
            if self.in_hq(path):
                return Decision(ALLOW, "reading in HQ")
            return _ask(f"read {Path(path).name} outside your workspace", "reading outside the folder")
        if tool in EDIT_TOOLS:
            return self._edit(inp.get("file_path") or "")
        if tool == "Bash":
            return self._bash(inp.get("command") or "")
        if tool in CALL_UNFRIENDLY:
            return Decision(DENY, "not available on a call")
        if tool in ("WebSearch", "WebFetch"):
            return _ask("look this up on the web", "the web")
        if tool in ("Task", "Agent"):
            return _ask("hand this to a helper to work on", "a helper")
        return _ask(f"use {tool}", "anything else")

    def _edit(self, path: str) -> Decision:
        if not path:
            return Decision(DENY, "no file named")
        if not self.inside(path):
            if self.in_hq(path):
                return _ask(f"change {Path(path).name} in HQ", "a change in HQ")
            return _ask(f"change {Path(path).name}, outside your workspace", "a file outside the folder")
        rel = self.rel(path)
        top = rel.parts[0] if rel.parts else ""
        if top in self.protected:
            return Decision(DENY, f"the {top} folder is never changed")
        if re.match(r"^my notes .*\.md$", rel.name, re.I):
            return Decision(DENY, "your own notes are never edited")
        if top in (".git",):
            return Decision(DENY, "git's own files are not edited")
        if top == ".claude":
            return _ask(f"change the project setup file {rel.name}", "the project setup")
        return Decision(ALLOW, "writing in the folder")

    def _bash(self, command: str) -> Decision:
        cmd = command.strip()
        if not cmd:
            return Decision(DENY, "empty command")
        # Only plain commands, joined by && or |. No redirection into files, no
        # subshells, variables or here-documents (quoted text may contain anything).
        if re.search(r"`|\$\(|\$\{|<<", cmd):
            return _ask("run a shell command", "a complex shell command")
        cmd = re.sub(r"\s2>\s*/dev/null|\s2>&1", " ", cmd)
        lex = shlex.shlex(cmd, posix=True, punctuation_chars="();<>|&\n")
        lex.whitespace = " \t\r"
        lex.whitespace_split = True
        try:
            tokens = list(lex)
        except ValueError:
            return _ask("run a shell command", "a shell command that doesn't parse")
        segments: list[list[str]] = [[]]
        for tok in tokens:
            if tok in ("&&", "|", ";"):
                segments.append([])
            elif tok and set(tok) <= set("();<>|&\n"):
                return _ask("run a shell command", "a complex shell command")
            else:
                segments[-1].append(tok)
        results = [self._bash_one(s) for s in segments]
        for verdict in (DENY, ASK):
            for d in results:
                if d.verdict == verdict:
                    return d
        return Decision(ALLOW, "; ".join(dict.fromkeys(d.why for d in results)))

    def _bash_one(self, words: list[str]) -> Decision:
        if not words:
            return Decision(DENY, "empty command")
        prog, args = words[0], words[1:]
        if prog == "cd":
            target = args[0] if args else str(Path.home())
            if self.inside(target):
                return Decision(ALLOW, "moving within the folder")
            if self.in_hq(target):
                return Decision(ALLOW, "moving within HQ")
            return _ask("go outside your workspace", "a folder outside")
        if prog == "date":
            return Decision(ALLOW, "the date")
        if prog == "git":
            return self._git(args)
        if prog == "curl":
            return self._curl(args)
        # Phase L: the queue of jobs for the computer. Adding, stopping, overruling, moving (H39) and switching
        # the routine only writes the queue on the roadmap, like writing in the folder; the call
        # uses them on his clear go. The job's own steps (done, held, mark, next) are not for calls.
        if prog in ("python3", "python") and args and self.hq_script(args[0], "jobs.py"):
            sub = args[1] if len(args) > 1 else ""
            if sub in ("add", "list", "stop", "overrule", "move", "on", "off"):
                return Decision(ALLOW, "the queue for the computer")
            return Decision(DENY, "that part of the queue is only for the computer itself")
        # H43: the scheduler. Adding, listing, moving and cancelling planned items only writes the schedule on
        # the roadmap, like the queue; promote and status are the routine's own.
        if prog in ("python3", "python") and args and self.hq_script(args[0], "schedule.py"):
            sub = args[1] if len(args) > 1 else ""
            if sub in ("add", "list", "cancel", "move"):
                return Decision(ALLOW, "the schedule for the computer")
            return Decision(DENY, "that part of the schedule is only for the computer itself")
        # L9/L10: the usage check. Reads the latest saved usage and shows it on the status page, nothing else.
        if prog in ("python3", "python") and args and self.hq_script(args[0], "usage-check.py"):
            if len(args) == 1:
                return Decision(ALLOW, "reading the usage")
            return Decision(DENY, "the usage check from a call takes no options")
        # H45: lid-closed sleep. Reads it, or flips it on or off; the script itself only runs the two exact
        # pmset commands the one-time setup allows without a password, nothing else.
        if prog in ("python3", "python") and args and self.hq_script(args[0], "lidsleep.py"):
            if len(args) == 1 or (len(args) == 2 and args[1] in ("on", "off")):
                return Decision(ALLOW, "the lid-closed sleep switch")
            return Decision(DENY, "the lid-closed sleep switch takes only on or off")
        if prog in SAFE_READ_COMMANDS:
            if prog == "find" and any(a in ("-exec", "-execdir", "-delete", "-ok", "-okdir", "-fprint") for a in args):
                return _ask("run a find command that changes files", "find with actions")
            paths = [a for a in args if not a.startswith("-") and ("/" in a or Path(self.folder, a).exists())]
            if all(self.inside(p) for p in paths):
                return Decision(ALLOW, "reading in the folder")
            if all(self.inside(p) or self.in_hq(p) for p in paths):
                return Decision(ALLOW, "reading in HQ")
            return _ask("look at something outside your workspace", "reading outside the folder")
        return _ask(f"run the command {prog}", "a shell command")

    def _curl(self, args: list[str]) -> Decision:
        """H65: reading the status page's data (GET on this computer's status server); anything else asks."""
        urls, i = [], 0
        while i < len(args):
            a = args[i]
            if a in ("-m", "--max-time"):
                i += 2
                continue
            if a.startswith("-"):
                if a not in CURL_SAFE_FLAGS:
                    return _ask("run curl that way", "curl with options")
            else:
                urls.append(a)
            i += 1
        if not urls:
            return _ask("run curl", "curl")
        for u in urls:
            m = re.match(r"^(?:https?://)?([^/:?#]+):(\d+)(/[^\s]*)?$", u)
            if not m or m.group(1) not in STATUS_HOSTS or m.group(2) != STATUS_PORT:
                return _ask("fetch something from the internet", "curl elsewhere")
        return Decision(ALLOW, "reading the status page")

    def _git(self, args: list[str]) -> Decision:
        # "git -C <dir> …" must point inside the folder; in HQ (H65) only to look.
        in_hq = False
        while args and args[0] in ("-C", "-c"):
            if args[0] == "-C" and len(args) > 1 and not self.inside(args[1]):
                if not self.in_hq(args[1]):
                    return _ask("run git outside your workspace", "git elsewhere")
                in_hq = True
            args = args[2:]
        if not args:
            return Decision(ALLOW, "git")
        sub, rest = args[0], args[1:]
        if sub in SAFE_GIT_READ:
            return Decision(ALLOW, "looking at git")
        if in_hq:
            return _ask(f"run git {sub} in HQ", "a git change in HQ")
        if sub == "add":
            files = [a for a in rest if a != "--"]
            bad = [a for a in files if a.startswith("-") or a in (".", "*", ":/", "./") or any(c in a for c in "*?[")]
            dirs = [a for a in files if not a.startswith("-") and Path(self.folder, a).is_dir()]
            if not files or bad or dirs:
                return _ask("add everything to git at once", "git add without named files")
            if not all(self.inside(a) for a in files):
                return _ask("add files from outside the folder to git", "git add outside")
            if any(self.rel(a).parts[:1] and self.rel(a).parts[0] in self.protected for a in files):
                return Decision(DENY, "that folder never goes to GitHub")
            return Decision(ALLOW, "git add, files by name")
        if sub == "commit":
            if any(a in ("-a", "--all", "--amend", "--no-verify", "-n") or a.startswith("--amend") for a in rest):
                return _ask("commit in a special way", "a special commit")
            return Decision(ALLOW, "git commit")
        if sub == "push":
            if any(a in ("-f", "--force", "--force-with-lease", "--delete", "-d", "--mirror", "--all", "--tags") or a.startswith("--force") or a.startswith("+") for a in rest):
                return _ask("force-push to GitHub", "a special push")
            return Decision(ALLOW, "git push")
        return _ask(f"run git {sub}", "another git command")

    # -- the user's answer -------------------------------------------------------

    def has_pending(self) -> bool:
        return bool(self.pending)

    def answer(self, words: str) -> tuple[bool, list[str]]:
        """The user's next words after a question. Returns (approved, questions)."""
        questions = [q for _, _, q in self.pending]
        yes = is_clear_yes(words)
        if yes:
            self.approved |= {(t, k) for t, k, _ in self.pending}
        self.pending.clear()
        return yes, questions

    def end_of_turn(self) -> None:
        """A yes counts for the turn right after it, not for later."""
        self.approved.clear()

    # -- paths ------------------------------------------------------------------

    def inside(self, path: str) -> bool:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self.folder / p
        real = Path(os.path.realpath(p))
        return real == self.folder or self.folder in real.parents

    def in_hq(self, path: str) -> bool:
        """H65: inside HQ itself (the app). The workspace link resolves to the folder, so it isn't counted here."""
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self.folder / p
        real = Path(os.path.realpath(p))
        return real == HQ_ROOT or HQ_ROOT in real.parents

    def hq_script(self, path: str, name: str) -> bool:
        """M1: one of HQ's own routine scripts (HQ is the app, outside the folder the call works in)."""
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self.folder / p
        return Path(os.path.realpath(p)) == HQ_ROUTINE / name

    def rel(self, path: str) -> Path:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self.folder / p
        return Path(os.path.realpath(p)).relative_to(self.folder)


# -- helpers ------------------------------------------------------------------------

# 9 October 2026: "i dont mind the confirmation, but lets make it like real". So a
# natural answer counts ("yeah, perfect", "sounds good", "mm-hm, put it in"), and a yes with a
# change ("yes, but make it seven") does not approve the old version: Claude makes the change.
_YES = re.compile(
    r"^(yes|yeah|yea|yep|yup|ya|ja|jazeker|sure|ok|okay|k|alright|all right|go ahead|go for it|go on|"
    r"do it|please do|please|absolutely|of course|correct|that's right|right|exactly|that's fine|"
    r"that is fine|fine|perfect|great|good|lovely|nice|cool|awesome|sounds good|sounds great|"
    r"sounds perfect|definitely|mhm|mm hmm|mm hm|uh huh|why not|put it in|add it|book it|let's do it)\b"
)
_NOT = re.compile(
    r"\b(no|not|don't|dont|do not|nope|wait|stop|hold on|cancel|never|nee|but|instead|actually|"
    r"rather|change|make it|move it)\b"
)
_HARMLESS = re.compile(r"\b(no problem|no worries|why not|not a problem)\b")


def is_clear_yes(words: str) -> bool:
    w = re.sub(r"[^a-z' ]", " ", words.lower())
    w = re.sub(r"^\s*(hq|um+|uh+|hmm+|well)\s+", "", " ".join(w.split()))
    return bool(_YES.match(w)) and not _NOT.search(_HARMLESS.sub(" ", w))


def _ask(question: str, why: str) -> Decision:
    return Decision(ASK, why, question=f"Can I {question}?")


def _calendar_question(name: str, inp: dict) -> str:
    what = inp.get("summary") or inp.get("title") or ""
    what = f" \"{what}\"" if what else ""
    if "create" in name:
        return f"add{what} to your calendar"
    if "delete" in name:
        return f"delete{what or ' an event'} from your calendar"
    if "respond" in name:
        return "answer that invitation in your calendar"
    return f"change{what or ' an event'} in your calendar"


def _mcp_parts(tool: str) -> tuple[str, str]:
    if not tool.startswith("mcp__"):
        return "", ""
    parts = tool.split("__")
    if len(parts) < 3:
        return parts[-1], ""
    return parts[1].removeprefix("claude_ai_"), "__".join(parts[2:])


def _plain(name: str) -> str:
    return name.replace("_", " ")


def _key(inp: dict) -> str:
    return json.dumps(inp or {}, sort_keys=True, ensure_ascii=False)


def _writes(tool: str, inp: dict) -> bool:
    if tool in EDIT_TOOLS:
        return True
    if tool == "Bash":
        c = inp.get("command") or ""
        return bool(re.search(r"\bgit\s+(add|commit|push)\b", c))
    return False


def summarize(tool: str, inp: dict) -> str:
    """A short line for the transcript: what the tool call was about."""
    server, name = _mcp_parts(tool)
    if server:
        bits = [inp.get(k) for k in ("summary", "query", "q", "calendarId", "timeMin", "timeMax") if inp.get(k)]
        return f"{server.replace('_', ' ')}: {_plain(name)}" + (f" ({', '.join(str(b) for b in bits)[:120]})" if bits else "")
    if tool in READ_TOOLS | EDIT_TOOLS:
        p = inp.get("file_path") or inp.get("path") or inp.get("pattern") or ""
        return f"{tool} {Path(p).name if '/' in str(p) else p}"
    if tool == "Bash":
        return f"Bash: {(inp.get('command') or '')[:140]}"
    if tool == "Skill":
        return f"Skill {inp.get('skill') or inp.get('name') or ''}"
    return tool
