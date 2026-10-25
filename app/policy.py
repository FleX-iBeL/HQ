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


def _slug(path) -> str:
    """How Claude Code names a working folder's own place under ~/.claude/projects."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def tool_output(path: str, folder: Path) -> bool:
    """H277: a file where a call's Claude session saved a long tool output (…/<session>/tool-results/…), under
    the projects folder of the workspace or HQ. Reading it back is reading what the call already read."""
    try:
        real = Path(os.path.realpath(Path(path).expanduser()))
        base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "projects"
        base = Path(os.path.realpath(base))
        rel = real.relative_to(base).parts
    except (ValueError, OSError):
        return False
    slugs = {_slug(folder), _slug(HQ_ROOT), _slug(HQ_ROOT / "workspace")}
    return len(rel) >= 4 and rel[0] in slugs and rel[2] == "tool-results" and ".." not in rel


def one_writer(rel: str) -> bool:
    """H203: a workspace file only the main writes (role.ONE_WRITER). Never raises."""
    try:
        import sys
        if str(HQ_ROUTINE) not in sys.path:
            sys.path.insert(0, str(HQ_ROUTINE))
        import role
        return role.one_writer(rel)
    except Exception:
        return False


def is_backup() -> bool:
    """H56.3: this HQ is the backup now (routine/role.py; alone it's always main). Never raises."""
    try:
        import sys
        if str(HQ_ROUTINE) not in sys.path:
            sys.path.insert(0, str(HQ_ROUTINE))
        import role
        return role.is_backup()
    except Exception:
        return False
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
    retry: bool = False  # H78: a DENY that's only "not yet": do what `why` says, then make the same call again
    handed: bool = False  # H203: not made here, but done: the backup handed it to the main, which wrote it (or will)


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
# H78 (12 October 2026, in the user's words): "If there are other people included in this appointment, then maybe
# ask for a confirmation. If it's just my account, I just put things in my calendar. ... We can always turn it back."
# So adding, moving and deleting go without asking, on every call; an event with other people in it (attendees, or
# someone else's invitation) and answering an invitation still ask. Before a move or a delete she must have read the
# event on this call, so the policy knows whether others are in it and keeps what it was (see seen()).
CALENDAR_ADD = {"create_event"}
CALENDAR_CHANGE = {"update_event", "delete_event"}
GMAIL_READ = {"search_threads", "get_thread", "get_message", "list_drafts", "get_draft", "list_labels"}
GMAIL_NEVER = {"send_message", "send", "reply", "forward", "send_draft"}
# H213 (19 October 2026, call at 10:57, in the user's words): "I think she should be able to make an email unread,
# read, archived, and put it into certain labels. ... Starring emails, marking them as important or not". All of these
# are labels in Gmail (UNREAD, INBOX, STARRED, IMPORTANT and their own), so on his ask they go without a yes, like
# adding to his own calendar; taking a mail out of the trash or spam is the undo and goes too. Never on her own (the
# rule, config.MAIL_TIDY_RULE). Trash, spam and deleting a label still ask: "She even asked about deleting but I
# don't think deleting is smart."
GMAIL_TIDY = {"label_message", "label_thread", "unlabel_message", "unlabel_thread", "update_message_labels",
              "create_label", "update_label", "untrash_message", "untrash_thread", "unmark_message_spam",
              "unmark_thread_spam"}
GMAIL_CAREFUL = {"trash_message", "trash_thread", "mark_message_spam", "mark_thread_spam", "delete_label"}
GMAIL_BIN = {"TRASH", "SPAM"}  # adding one of these as a label is trashing or spamming it

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
    # H78: calendar events read on this call: event id -> (others in it?, what it was, in one line).
    events: dict[str, tuple[bool, str]] = field(default_factory=dict)
    # H277: where a cd earlier in the same command went, so `cd HQ && python3 routine/sprint.py …` is known.
    _cwd: Path | None = None

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
                if name in GMAIL_TIDY:
                    added = {str(x).upper() for x in (inp.get("labelIds") or []) + (inp.get("addLabelIds") or [])}
                    if name.startswith(("label_", "update_message")) and added & GMAIL_BIN:
                        return _ask("move that mail to the trash or spam", "trash or spam in Gmail")
                    return Decision(ALLOW, "tidying mail on his ask (labels, read, archive, star, important)")
                if name in GMAIL_CAREFUL:
                    what = ("delete that label (the mails keep their other labels)" if name == "delete_label"
                            else "move that mail to the spam" if "spam" in name else "move that mail to the trash")
                    return _ask(what, "trash, spam or deleting a label in Gmail")
                return _ask(f"{_plain(name)} in your Gmail", "a Gmail change")
            if "calendar" in s:
                if name in CALENDAR_READ:
                    return Decision(ALLOW, "reading the calendar")
                return self._calendar(name, inp)
            return _ask(f"use {_plain(name)} in {server.replace('_', ' ')}", "another connector")

        if tool in SESSION_TOOLS:
            return Decision(ALLOW, "session helper")
        if tool in READ_TOOLS:
            path = inp.get("file_path") or inp.get("path") or str(self.folder)
            if self.inside(path):
                return Decision(ALLOW, "reading in the folder")
            if self.in_hq(path):
                return Decision(ALLOW, "reading in HQ")
            if tool_output(path, self.folder):
                return Decision(ALLOW, "reading this call's own saved output")
            return _ask(f"read {Path(path).name} outside your workspace", "reading outside the folder")
        if tool in EDIT_TOOLS:
            return self._edit(inp.get("file_path") or "", tool, inp)
        if tool == "Bash":
            return self._bash(inp.get("command") or "")
        if tool in CALL_UNFRIENDLY:
            return Decision(DENY, "not available on a call")
        if tool in ("WebSearch", "WebFetch"):
            # H103 (13 October 2026), in his words: "donna needs access to internet always (no need to ask for yes)".
            return Decision(ALLOW, "looking it up on the web (no need to ask)")
        if tool in ("Task", "Agent"):
            return _ask("hand this to a helper to work on", "a helper")
        return _ask(f"use {tool}", "anything else")

    def _calendar(self, name: str, inp: dict) -> Decision:
        """H78: his own calendar changes go without asking; with other people in it, ask."""
        if _has_others(inp):
            return _ask(_calendar_question(name, inp), "a calendar change with other people in it")
        if name in CALENDAR_ADD:
            return Decision(ALLOW, "adding to the calendar (no need to ask)")
        if name in CALENDAR_CHANGE:
            ev = self.events.get(str(inp.get("eventId") or ""))
            if ev is None:
                return Decision(DENY, "look at this event first (get_event), so it can be put back, and to see "
                                      "whether other people are in it; then try again", retry=True)
            others, was = ev
            if others:
                return _ask(_calendar_question(name, inp), "a calendar change with other people in it")
            verb = "deleting" if "delete" in name else "moving or changing"
            return Decision(ALLOW, f"{verb} in the calendar (no need to ask); it was: {was}")
        return _ask(_calendar_question(name, inp), "a calendar change")

    def seen(self, tool: str, response) -> None:
        """H78: after a calendar read, remember each event it showed: whether others are in it, and what it was,
        so a move or delete can be put back (the line goes into the transcript with the change). Never raises."""
        server, name = _mcp_parts(tool)
        if "calendar" in server.lower() and name in CALENDAR_ADD | CALENDAR_CHANGE | {"respond_to_event"}:
            # H153: a write in the calendar (a call, Donna's chat, an appointment's note): HQ's calendar reads it again
            if not self.dry_run:
                try:
                    import agenda
                    agenda.changed(name)
                except Exception:
                    pass
            return
        if "calendar" not in server.lower() or name not in CALENDAR_READ:
            return
        try:
            for ev in _event_dicts(response):
                self.events[str(ev["id"])] = (_has_others(ev), _event_line(ev))
        except Exception:
            pass

    def _edit(self, path: str, tool: str = "Edit", inp: dict | None = None) -> Decision:
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
        if is_backup() and one_writer(rel.as_posix()):
            return self._hand_over(tool, rel.as_posix(), inp or {})
        return Decision(ALLOW, "writing in the folder")

    def _hand_over(self, tool: str, rel: str, inp: dict) -> Decision:
        """H203: on the backup, a change to a file only the main writes goes to the main, which makes it on its own
        copy; the sync brings it back here. Nothing is written here, so the two never make conflict copies."""
        if tool == "Write":
            return Decision(DENY, f"this HQ is the backup, and {rel} is written only by the main: make the change as "
                                  "an Edit (only the part that changes), so the main can make it on its own copy",
                            retry=True)
        edits = inp.get("edits") if tool == "MultiEdit" else [inp]
        edits = [{"old": e.get("old_string") or "", "new": e.get("new_string") or "", "all": bool(e.get("replace_all"))}
                 for e in edits or [] if isinstance(e, dict)]
        if len(json.dumps(edits)) > 90_000:  # the main's /api/forward takes up to 100 KB
            return Decision(DENY, f"this HQ is the backup, so this change to {rel} goes to the main, and it's too big "
                                  "to send in one go: make it as a few smaller Edits", retry=True)
        if self.dry_run:
            return Decision(DENY, f"test run: on the backup this change to {rel} would go to the main")
        try:
            import sys
            if str(HQ_ROUTINE) not in sys.path:
                sys.path.insert(0, str(HQ_ROUTINE))
            import role
            code, out, err, how = role.hand("handover", ["edit", rel, json.dumps({"edits": edits}, ensure_ascii=False)])
        except Exception as e:
            code, out, err, how = 3, "", repr(e), "error"
        said = " ".join((out + " " + err).split())[:300]
        if how == "kept":
            return Decision(DENY, f"this HQ is the backup and the main can't be reached right now, so this change to "
                                  f"{rel} is kept here and goes to the main as soon as it answers; it then comes back "
                                  "with the sync. Don't make it again", handed=True)
        if how == "main" and code == 0:
            return Decision(DENY, f"this HQ is the backup, so the main wrote this change to {rel}; it reaches this "
                                  "computer with the sync within a minute (a read right now may not show it yet). "
                                  "Don't make it again", handed=True)
        if how == "main" and code == 1:
            return Decision(DENY, f"this HQ is the backup, and the main's copy of {rel} differs from this one ({said}); "
                                  "read the file again in a moment, when the sync has brought the main's copy, and "
                                  "make the edit on what's there", retry=True)
        return Decision(DENY, f"this HQ is the backup, and the main didn't take this change to {rel} ({said or how})")

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
            if tok in ("&&", "|", ";", "||"):
                segments.append([])
            elif tok and set(tok) <= set("();<>|&\n"):
                return _ask("run a shell command", "a complex shell command")
            else:
                segments[-1].append(tok)
        segments = _loops(segments)
        if segments is None:
            return _ask("run a shell command", "a shell loop it can't follow")
        # H277: several steps chained count as one; a cd carries over to the steps after it.
        results = []
        self._cwd = None
        try:
            for seg in segments:
                if any("$" in w for w in seg):
                    results.append(_ask("run a shell command", "a shell command with a variable"))
                    continue
                d = self._bash_one(seg)
                results.append(d)
                if seg and seg[0] == "cd" and d.verdict == ALLOW:
                    target = Path(seg[1]).expanduser() if len(seg) > 1 else Path.home()
                    if not target.is_absolute():
                        target = (self._cwd or self.folder) / target
                    self._cwd = Path(os.path.realpath(target))
        finally:
            self._cwd = None
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
            if sub in ("add", "add-row", "send-row",  # H277: a row on the roadmap first, or an open row to the team
                       "list", "stop", "overrule", "move", "on", "off", "resume",  # H172: resume a paused job
                       "mail-fast", "mail-hourly"):  # H149: the mail check every 15 minutes for a while he names

                return Decision(ALLOW, "the queue for the computer")
            return Decision(DENY, "that part of the queue is only for the computer itself")
        # H43: the scheduler. Adding, listing, moving and cancelling planned items only writes the schedule on
        # the roadmap, like the queue; promote and status are the routine's own.
        if prog in ("python3", "python") and args and self.hq_script(args[0], "schedule.py"):
            sub = args[1] if len(args) > 1 else ""
            if sub in ("add", "list", "cancel", "move", "priority", "every"):  # H171: every
                return Decision(ALLOW, "the schedule for the computer")
            return Decision(DENY, "that part of the schedule is only for the computer itself")
        # H269: the planning's ranks and estimates: read them, and give a row its place (only HQ's own sprint.json);
        # piece 2: lay a sprint over the nights, and plan it for the team (the schedule, as schedule.py add would).
        if prog in ("python3", "python") and args and self.hq_script(args[0], "sprint.py"):
            sub = args[1] if len(args) > 1 else "list"
            if sub in ("list", "json", "rank", "lay", "plan", "moscow", "ready", "check"):  # H271: moscow; H272: ready, check
                return Decision(ALLOW, "the planning's ranks and estimates, and the sprint")
            return Decision(DENY, "from a call, the sprint script takes list, json, rank, moscow, ready, check, lay or plan")
        # H173: the usage counts, read only: what a job or a call cost on its own tokens, the rate, the room now.
        if prog in ("python3", "python") and args and self.hq_script(args[0], "usagecost.py"):
            sub = args[1] if len(args) > 1 else ""
            if sub in ("now", "cost", "when", "costs", "rate", "tokens", "calls"):
                return Decision(ALLOW, "the usage counts")
            return Decision(DENY, "from a call, the usage script only reads (now, cost, when, costs, rate, tokens, calls)")
        # H124: Donna texts first. Picking appointments to ping, reminders and her own notes only writes HQ's own list
        # in the workspace (direct-line/pings.json, her notes file); Google Calendar is never touched by it.
        if prog in ("python3", "python") and args and self.hq_script(args[0], "pings.py"):
            sub = args[1] if len(args) > 1 else "list"
            if sub in ("list", "appt", "remind", "cancel", "note", "note-clear", "due", "watch", "unwatch",
                       "out", "out-stop",  # H212: his own times out, for the weather
                       "nudge", "nudge-done", "nudge-later",  # H211: nudge until done
                       "call", "call-cancel"):  # H238: an agent calls him at a time they agreed
                return Decision(ALLOW, "her pings, reminders, notes and watches")
            # H125: match is the mail check's own (it found a mail for a watch)
            return Decision(DENY, "the pings script takes list, appt, remind, cancel, note, note-clear, watch, unwatch, out, out-stop, nudge, nudge-done, nudge-later, call or call-cancel")
        # H213: the mail sorting rules he agreed, in the workspace (HQ/mail-sort.json): read, add, stop, start, remove.
        # `sorted` is the mail check's own line per mail.
        if prog in ("python3", "python") and args and self.hq_script(args[0], "mailsort.py"):
            if len(args) == 1 or args[1] in ("list", "add", "stop", "start", "remove"):
                return Decision(ALLOW, "his mail sorting rules")
            return Decision(DENY, "the mail sorting script takes list, add, stop, start or remove")
        # H132: what an agent has said about herself, kept in her own list in the workspace (HQ/agents/).
        if prog in ("python3", "python") and args and self.hq_app_script(args[0], "about_self.py"):
            if len(args) == 1 or args[1] in ("list", "add"):
                return Decision(ALLOW, "her own list of what she has said about herself")
            return Decision(DENY, "the about-herself script takes list or add")
        # H143: the week's ticks and X in his calendar, read only, to look back with him.
        if prog in ("python3", "python") and args and self.hq_app_script(args[0], "planning.py"):
            if len(args) == 1 or (args[1] == "week" and len(args) <= 3):
                return Decision(ALLOW, "the week's ticks and X in his calendar")
            return Decision(DENY, "from a call, the planning script only reads a week (week, or week with a date)")
        # H146: his notes on the appointments, read only (the page adds and clears them).
        if prog in ("python3", "python") and args and self.hq_app_script(args[0], "appt_notes.py"):
            if len(args) == 1 or (len(args) == 2 and args[1] in ("list", "json")):
                return Decision(ALLOW, "his notes on the appointments")
            return Decision(DENY, "from a call, the appointment notes script only reads them")
        # H263: his quick notes: read, clear one (kept, so it can come back), the cleared ones, bring one back. The
        # notes file is in the workspace, which a call may edit anyway; this way a cleared note is never lost.
        if prog in ("python3", "python") and args and self.hq_app_script(args[0], "notes.py"):
            if len(args) == 1 or args[1] in ("clear", "cleared", "restore"):
                return Decision(ALLOW, "his quick notes")
            return Decision(DENY, "the notes script takes clear, cleared or restore")
        # H200: the to-do list, the user's own file in the workspace: read, add, done, let go, move, undo. Each change is
        # one table row and its log line, the same as editing the file by hand, which a call may do anyway.
        if prog in ("python3", "python") and args and self.hq_app_script(args[0], "todo.py"):
            if len(args) == 1 or args[1] in ("summary", "json", "add", "done", "letgo", "move", "tick", "untick",
                                                  "order", "rename", "undo", "blocks", "plan", "unplan",
                                                  "repeat"):
                return Decision(ALLOW, "the to-do list")
            return Decision(DENY, "the to-do script takes summary, json, add, done, letgo, move, tick, untick, order, "
                                  "rename, undo, blocks, plan, unplan or repeat")
        # H222: the six-week games, the workspace's own HQ/games.json: read, tick a day, count, a note, the diary, a
        # week's look back, the debrief, undo. Making a game or changing its design is the team's (new, spec), from
        # the design written in their map.
        if prog in ("python3", "python") and args and self.hq_app_script(args[0], "games.py"):
            if len(args) == 1 or args[1] in ("summary", "json", "show", "kinds", "check", "tick", "count", "note",
                                             "diary", "week", "debrief", "undo"):
                return Decision(ALLOW, "the six-week game")
            return Decision(DENY, "making a six-week game or changing its design is the team's: write the design in "
                                  "their map and hand it to the team; from a call the games script reads, ticks, "
                                  "counts, notes, keeps the diary, the week's look back and the debrief")
        # H225: Life coaching's check-ins: what's due, and marking one done (or not now) once it's through.
        if prog in ("python3", "python") and args and self.hq_app_script(args[0], "coaching.py"):
            if len(args) == 1 or args[1] in ("summary", "json", "due") or (args[1] in ("done", "later") and len(args) == 3):
                return Decision(ALLOW, "Life coaching's check-ins")
            return Decision(DENY, "from a call, the coaching script says what's due and marks a check-in done or not now")
        # H236: their own news: read it, and keep their setup (topics, what to leave out, sources) as they say it; try a
        # feed before adding it, read the sources now. `start` is the routine's.
        if prog in ("python3", "python") and args and self.hq_app_script(args[0], "news.py"):
            if len(args) == 1 or args[1] in ("summary", "json", "setup", "suggest", "try", "topic", "leave-out",
                                             "source", "fetch", "rule"):
                return Decision(ALLOW, "their own news")
            return Decision(DENY, "from a call, the news script reads, keeps their topics, what's left out and the "
                                  "sources, tries a feed or reads the sources now")
        # H235: their own extensions: list them, read their rules and the last clash check, and run one of an
        # extension's own scripts, only one it declares (extensions.py refuses the rest); one that says "ask" waits for
        # a yes. Settling a clash is the page's buttons'.
        if prog in ("python3", "python") and args and self.hq_app_script(args[0], "extensions.py"):
            sub = args[1] if len(args) > 1 else "list"
            if sub in ("list", "summary", "json", "rule", "mail") or (sub == "clash" and len(args) == 2):
                return Decision(ALLOW, "their own extensions")
            if sub == "run" and len(args) >= 4:
                try:
                    import extensions as _ext
                    s = _ext.script(args[2], args[3])
                except Exception:
                    s = None
                if not s:
                    return Decision(DENY, f"there's no script {args[3]} in an extension {args[2]} that's on")
                if s.get("ask"):
                    return _ask(f"run {args[3]} from your extension {args[2]}", "an extension's script that asks first")
                return Decision(ALLOW, "one of their own extension's scripts")
            return Decision(DENY, "from a call, the extensions script lists them, gives their rules, the last check, or runs one of their scripts")
        # H224: the workflows, read only: which are on, the call rule, a blank checklist, and their file's checklist
        # held against the guide before a layer is called done. Turning one on or off is Settings'.
        if prog in ("python3", "python") and args and self.hq_app_script(args[0], "workflows.py"):
            if len(args) == 1 or args[1] == "rule" or (args[1] in ("check", "checklist") and len(args) in (3, 4)):
                return Decision(ALLOW, "the workflows and their checklist")
            return Decision(DENY, "from a call, the workflows script only lists, gives the rule, a checklist or the check")
        # H56.3: main and backup. Asking which one is main, and making one the main on his ask.
        if prog in ("python3", "python") and args and self.hq_script(args[0], "role.py"):
            if len(args) == 1 or (len(args) == 3 and args[1] == "main"):
                return Decision(ALLOW, "which HQ is main")
            return Decision(DENY, "from a call, the role script only says which one is main, or makes one the main")
        # L9/L10: the usage check. Reads the latest saved usage and shows it on the status page, nothing else.
        if prog in ("python3", "python") and args and self.hq_script(args[0], "usage-check.py"):
            if len(args) == 1:
                return Decision(ALLOW, "reading the usage")
            return Decision(DENY, "the usage check from a call takes no options")
        # H87, H91: the three usage stop lines (5-hour, weekly, fable), each moving every minute or fixed at a
        # number. Reads them, or switches one: [5-hour|weekly|fable] moving, or fixed with or without a number.
        if prog in ("python3", "python") and args and self.hq_script(args[0], "usageline.py"):
            rest = args[1:]
            if rest and rest[0].lower() in ("5-hour", "five", "5h", "weekly", "week", "fable"):
                rest = rest[1:]
            if (len(args) == 1 or rest == [] and len(args) == 2 or rest == ["moving"] or rest == ["fixed"]
                    or (len(rest) == 2 and rest[0] == "fixed" and rest[1].rstrip("%").isdigit())):
                return Decision(ALLOW, "the usage stop lines")
            return Decision(DENY, "a usage line takes only moving, or fixed with a number")
        # H214: a 9292 link door to door. Only looks places up (the government's open address service, the open
        # station list) and prints a link; it changes nothing.
        if prog in ("python3", "python") and args and self.hq_app_script(args[0], "travel.py"):
            if len(args) >= 2 and args[1] in ("link", "where"):
                return Decision(ALLOW, "a 9292 travel link")
            return Decision(DENY, "the travel script takes link or where")
        # H229: travel on appointments. Lists and shows the trips, turns travel on or off for one, keeps a place by name;
        # only HQ's own file in the workspace changes. `check` is the routine's, not a call's.
        if prog in ("python3", "python") and args and self.hq_app_script(args[0], "trips.py"):
            if len(args) == 1 or args[1] in ("list", "on", "off", "show", "place", "places", "forget"):
                return Decision(ALLOW, "travel on appointments")
            return Decision(DENY, "the trips script takes list, on, off, show, place, places or forget")
        # H230: driving to appointments: only whether a maps key is here and today's looks. The key itself is set in
        # Settings (never on a call: it would be in the transcript), and a test look costs one of the day's looks.
        if prog in ("python3", "python") and args and self.hq_app_script(args[0], "drive.py"):
            if len(args) == 1 or args[1:] == ["status"]:
                return Decision(ALLOW, "whether driving has a key")
            return Decision(DENY, "the driving script only says whether a key is here; the key goes in Settings")
        # H45: lid-closed sleep. Reads it, or flips it on or off; the script itself only runs the two exact
        # pmset commands the one-time setup allows without a password, nothing else.
        if prog in ("python3", "python") and args and self.hq_script(args[0], "lidsleep.py"):
            if len(args) == 1 or (len(args) == 2 and args[1] in ("on", "off")):
                return Decision(ALLOW, "the lid-closed sleep switch")
            return Decision(DENY, "the lid-closed sleep switch takes only on or off")
        if prog in SAFE_READ_COMMANDS:
            if prog == "find" and any(a in ("-exec", "-execdir", "-delete", "-ok", "-okdir", "-fprint") for a in args):
                return _ask("run a find command that changes files", "find with actions")
            paths = [a for a in args if not a.startswith("-") and ("/" in a or Path(self._base(), a).exists())]
            if all(self.inside(p) for p in paths):
                return Decision(ALLOW, "reading in the folder")
            if all(self.inside(p) or self.in_hq(p) for p in paths):
                return Decision(ALLOW, "reading in HQ")
            if all(self.inside(p) or self.in_hq(p) or tool_output(p, self.folder) for p in paths):
                return Decision(ALLOW, "reading this call's own saved output")
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
        if sub in ("commit", "push") and is_backup():
            # H56.3: only the main one commits; on the backup the notes go over with the sync.
            return Decision(DENY, "this HQ is the backup now: only the main one commits, the files go over with the sync")
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

    def _base(self) -> Path:
        return self._cwd or self.folder

    def inside(self, path: str) -> bool:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self._base() / p
        real = Path(os.path.realpath(p))
        return real == self.folder or self.folder in real.parents

    def in_hq(self, path: str) -> bool:
        """H65: inside HQ itself (the app). The workspace link resolves to the folder, so it isn't counted here."""
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self._base() / p
        real = Path(os.path.realpath(p))
        return real == HQ_ROOT or HQ_ROOT in real.parents

    def hq_script(self, path: str, name: str) -> bool:
        """M1: one of HQ's own routine scripts (HQ is the app, outside the folder the call works in)."""
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self._base() / p
        return Path(os.path.realpath(p)) == HQ_ROUTINE / name

    def hq_app_script(self, path: str, name: str) -> bool:
        """H132: one of HQ's own app scripts, like hq_script for the routine's."""
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self._base() / p
        return Path(os.path.realpath(p)) == HQ_ROUTINE.parent / "app" / name

    def rel(self, path: str) -> Path:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = self._base() / p
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


def _loops(segments: list[list[str]]) -> list[list[str]] | None:
    """H277: `for l in A B C; do …; done` becomes its body once per value, with $l, "$l" filled in, so each step
    is judged as if typed out. Only plain loops over plain words; anything else gives None (asks)."""
    out: list[list[str]] = []
    i = 0
    while i < len(segments):
        seg = segments[i]
        if seg[:1] in (["while"], ["until"], ["if"], ["then"], ["else"], ["fi"], ["do"], ["done"]):
            return None
        if seg[:1] != ["for"]:
            out.append(seg)
            i += 1
            continue
        if len(seg) < 3 or seg[2] != "in" or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", seg[1]):
            return None
        var, values = seg[1], seg[3:]
        if any("$" in v or "*" in v or "?" in v for v in values):
            return None
        body: list[list[str]] = []
        j = i + 1
        while j < len(segments) and segments[j] != ["done"]:
            body.append(segments[j])
            j += 1
        if j >= len(segments) or not body or body[0][:1] != ["do"]:
            return None
        body[0] = body[0][1:]
        if any(b[:1] in (["for"], ["do"], ["while"], ["if"]) for b in body):
            return None
        pat = re.compile(r"\$(?:\{%s\}|%s(?![A-Za-z0-9_]))" % (var, var))
        for v in values or [""]:
            for b in body:
                out.append([pat.sub(v, w) for w in b])
        i = j + 1
    return out


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


def _has_others(ev: dict) -> bool:
    """Other people in an event: an attendee who isn't him, or an organizer who isn't one of his calendars."""
    for a in ev.get("attendees") or []:
        if not (isinstance(a, dict) and a.get("self")):
            return True
    org = ev.get("organizer")
    return isinstance(org, dict) and bool(org.get("email")) and not org.get("self")


def _event_line(ev: dict) -> str:
    def when(k):
        t = ev.get(k) or {}
        return str(t.get("dateTime") or t.get("date") or "?") if isinstance(t, dict) else "?"
    bits = [f"\"{ev.get('summary') or '(no title)'}\"", f"{when('start')} to {when('end')}"]
    if ev.get("location"):
        bits.append(f"at {ev['location']}")
    if ev.get("recurringEventId"):
        bits.append("one of a series")
    return ", ".join(bits)[:300]


def _event_dicts(x, depth: int = 0):
    """Every event in a calendar tool's answer, whatever wraps it (content blocks, JSON in text, a list)."""
    if depth > 8:
        return
    if isinstance(x, str):
        t = x.strip()
        if t[:1] in "[{":
            try:
                yield from _event_dicts(json.loads(t), depth + 1)
            except ValueError:
                pass
    elif isinstance(x, list):
        for y in x:
            yield from _event_dicts(y, depth + 1)
    elif isinstance(x, dict):
        if x.get("id") and isinstance(x.get("start"), dict):
            yield x
        for k, y in x.items():
            if k in ("events", "items", "content", "text", "result", "structuredContent", "event") or isinstance(y, str):
                yield from _event_dicts(y, depth + 1)


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
    server, name = _mcp_parts(tool)
    if "calendar" in server.lower() and name not in CALENDAR_READ:
        return True  # H78: a calendar change goes without asking now, so a test run stops it here
    if "gmail" in server.lower() and name in GMAIL_TIDY:
        return True  # H213: tidying mail goes without asking, so a test run stops it here
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
