"""The brain: one Claude session for the whole call, through the Claude Agent SDK.

Nothing here knows about Pipecat. The call layer (claude_llm.py) asks a question and
streams the answer; when the user cuts in it calls cancel_turn(), which interrupts Claude
and throws away the rest of that reply.

The SDK drives the `claude` CLI, which is logged in to the user's Claude plan. The API key
variables are removed from this process's environment on import, so the CLI can't fall
back to API billing.

A3: call_session_options() makes it the full Claude of the user's workspace,
with every tool call checked by policy.py. ask() also yields ToolStarted when Claude
starts a tool call, so the call layer can say a filler.

Design:
- One ClaudeSDKClient per call, connected when the call starts, kept open for the call.
- One reader task pulls every message from the SDK into an asyncio.Queue. A turn reads
  from that queue until its ResultMessage. Nothing else reads the SDK stream.
- A turn has three states: idle, answering, draining. cancel_turn() sends the CLI an
  interrupt and moves to draining: the reader keeps going, and the rest of that turn is
  dropped up to its ResultMessage. The next ask() waits for that before sending.
"""
from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    RateLimitEvent,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    UserMessage,
)

import config as _config
import policy as _policy

import sys as _sys

_sys.path.insert(0, str(_config.ROOT / "routine"))
import usagelive  # H51: the usage a call gets back is saved the same way as the mail check's

# Never let the CLI bill an API key: the call runs on the Max login. And never let it
# talk to a Claude desktop host it happens to be started from (its variables point the
# CLI somewhere else): the call is a plain, logged-in CLI.
for _var in list(os.environ):
    if _var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDECODE") or (
        _var.startswith("CLAUDE_CODE_")
    ):
        os.environ.pop(_var, None)


# F38 (17 October 2026): the text a session adds to Claude's own goes to the CLI as a file, never as one
# command-line argument: Linux caps a single argument at 128 KB, and a Quick call's text grew past it
# ("Argument list too long", so Donna never answered). Named by its contents, so a restarted session finds it.
PROMPT_DIR = _config.SCRATCH / "prompts"
PROMPT_KEEP_S = 2 * 86400


def append_file(text: str) -> Path:
    """TEXT in a file the CLI reads with --append-system-prompt-file; old ones are cleared."""
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    path = PROMPT_DIR / f"append-{hashlib.sha256(text.encode('utf8')).hexdigest()[:24]}.md"
    if not path.exists() or path.read_text(encoding="utf8") != text:
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(text, encoding="utf8")
        tmp.replace(path)
    now = time.time()
    for old in PROMPT_DIR.glob("append-*"):
        try:
            if old != path and now - old.stat().st_mtime > PROMPT_KEEP_S:
                old.unlink()
        except OSError:
            pass
    os.utime(path)
    return path


def prompt_text(options: ClaudeAgentOptions) -> str:
    """The text a session adds (or its whole system prompt, for a plain one), read back from its file."""
    extra = (options.extra_args or {}).get("append-system-prompt-file")
    sp = options.system_prompt
    path = extra or (sp.get("path") if isinstance(sp, dict) and sp.get("type") == "file" else None)
    return Path(path).read_text(encoding="utf8") if path else (sp if isinstance(sp, str) else "")


# F60: the Claude SDK kills the session when one message from the CLI is over its buffer (1 MB by default),
# and it did so silently when a call read a very big file. Well above what a call can read (policy.BIG_FILE_BYTES).
MAX_BUFFER = 64 * 1024 * 1024
LOST_LINE = "Lost my line, one moment. "


@dataclass
class ToolStarted:
    """Yielded by ask() when Claude starts a tool call mid-reply (for a filler)."""

    name: str


def call_session_options(
    *,
    model: str,
    folder: Path,
    voice_rules: str,
    policy: "_policy.Policy",
    cli_path: str | None = None,
    effort: str | None = "low",
    quick_context: str | None = None,
) -> ClaudeAgentOptions:
    """A3: the same Claude as the user's chats in their workspace.

    The folder's CLAUDE.md (with its @-imports), rules.md and its hook, the deny list, the
    life-coach skill, their claude.ai connectors (Calendar, Gmail): all load, as in a chat.
    On top: the voice rules, and every tool call goes through policy.py.

    B1: with quick_context (a Quick call), no CLAUDE.md is loaded by the CLI; that text, the
    lighter version built by quick_context.py, goes in front of the voice rules instead.
    F38: both go to the CLI in a file (append_file), however long they get.
    Settings, hooks, the deny list and the connectors load the same.
    """

    async def pre_tool_use(hook_input, tool_use_id, context):
        d = policy.decide(hook_input.get("tool_name", ""), hook_input.get("tool_input") or {})
        out = {"hookEventName": "PreToolUse", "permissionDecision": "allow" if d.verdict == "allow" else "deny"}
        if d.verdict != "allow":
            out["permissionDecisionReason"] = refusal_text(d)
        return {"hookSpecificOutput": out}

    async def post_tool_use(hook_input, tool_use_id, context):
        # H78: what a calendar read showed, so a move or delete knows who's in the event and what it was.
        policy.seen(hook_input.get("tool_name", ""), hook_input.get("tool_response"))
        return {}

    async def can_use_tool(tool_name, tool_input, ctx):
        # Normally not reached: the hook above already decided. Kept as the fallback.
        d = policy.decide(tool_name, tool_input or {})
        if d.verdict == "allow":
            return PermissionResultAllow()
        return PermissionResultDeny(message=refusal_text(d))

    return ClaudeAgentOptions(
        model=model,
        cwd=str(folder),
        cli_path=cli_path,
        system_prompt={"type": "preset", "preset": "claude_code"},
        # F38: the quick context and the voice rules through a file, not the command line.
        extra_args={"append-system-prompt-file": str(append_file(
            f"{quick_context}\n\n{voice_rules}" if quick_context else voice_rules))},
        setting_sources=["user", "project", "local"],
        # K2: no Claude Docs on calls (the whole server, so its tools aren't loaded at all).
        disallowed_tools=_policy.CALL_UNFRIENDLY + _policy.gmail_never_tool_names()
        + ([_config.DOCS_SERVER] if _config.NO_DOCS else []),
        hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[pre_tool_use])],
               "PostToolUse": [HookMatcher(matcher=None, hooks=[post_tool_use])]},
        can_use_tool=can_use_tool,
        include_partial_messages=True,
        effort=effort,
        max_buffer_size=MAX_BUFFER,  # F60
        # No CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC here: it also switches off the
        # claude.ai connectors (Calendar, Gmail), checked 8 October 2026.
        # Tool search off: the connector tools are loaded up front instead of through a
        # ToolSearch step first. Measured 8 October: first words 1.2 s instead of 3.5 s.
        # K3 (9 October 2026): tool search back on, so the connector tools are loaded when she needs
        # them instead of read on every step; the waiting line covers the extra seconds.
        env={"ENABLE_TOOL_SEARCH": "true" if _config.TOOLS_ON_DEMAND else "false",
             **({"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1"} if quick_context else {})},
        stderr=lambda line: logger.debug(f"claude cli: {line}"),
    )


def refusal_text(d: "_policy.Decision") -> str:
    if d.verdict == "ask":
        return (
            f"Not done: this needs {_config.USER}'s yes first. Check it with him the way an assistant on "
            "the phone would, in one short natural sentence with the details that matter, e.g. "
            '"Shall I put dinner with a friend in your agenda, Saturday at 6 30 in the evening?" or '
            '"So that\'s breakfast tomorrow at 10 in the morning, until 11. Want me to put it in?" '
            f"(What needs his okay: {d.question}) Never say \"say yes or no\". Then stop and wait for "
            "his answer. If the call system then tells you he said yes, make exactly the same call again."
        )
    if d.handed:  # H203: the backup handed it to the main; it's done, not refused
        return f"Done, though not on this computer: {d.why}. No need to tell {_config.USER} how."
    if d.retry:
        return f"Not yet: {d.why}. No need to ask {_config.USER} for this."
    return f"Not allowed on this call: {d.why}. Don't try another way; tell {_config.USER} briefly if it matters."


@dataclass
class TurnStats:
    """Timings of one turn, in seconds from the moment the question was sent."""

    text: str = ""
    first_text_s: float | None = None
    total_s: float | None = None
    interrupted: bool = False
    is_error: bool = False
    terminal_reason: str | None = None
    model_usage: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    events: list[tuple[float, str]] = field(default_factory=list)  # (seconds, what) for timing


class ClaudeBrain:
    def __init__(
        self,
        *,
        model: str,
        system_prompt: str,
        cwd: Path,
        cli_path: str | None = None,
        effort: str | None = "low",
        options: ClaudeAgentOptions | None = None,
        tools: list[str] | None = None,
    ):
        if options is None:
            cwd.mkdir(parents=True, exist_ok=True)
        # A2: a plain Claude. No tools, no MCP servers, no settings or CLAUDE.md files,
        # an empty working folder. A3 replaces these options with the full session.
        # H8: free mode passes tools=config.FREE_TOOLS (web search and fetching pages only).
        self._options = options or ClaudeAgentOptions(
            model=model,
            # F38: through a file too, so its length never matters.
            system_prompt={"type": "file", "path": str(append_file(system_prompt))} if system_prompt else system_prompt,
            cwd=str(cwd),
            cli_path=cli_path,
            tools=list(tools or []),
            allowed_tools=list(tools or []),
            setting_sources=[],
            strict_mcp_config=True,
            include_partial_messages=True,
            effort=effort,
            max_buffer_size=MAX_BUFFER,  # F60
            # No side calls (the CLI otherwise runs small Haiku jobs next to each turn).
            env={"CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"},
            stderr=lambda line: logger.debug(f"claude cli: {line}"),
        )
        self.model = model
        self._client: ClaudeSDKClient | None = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._reader: asyncio.Task | None = None
        self._drainer: asyncio.Task | None = None
        self._idle = asyncio.Event()
        self._idle.set()
        self._lock = asyncio.Lock()
        self._start_lock = asyncio.Lock()
        self._answering = False
        self._dead = False
        self.interrupts_sent = 0
        self.last_turn: TurnStats | None = None
        self.session_id: str | None = None
        self.init_info: dict | None = None  # the session's init message: tools, connectors, skills
        self.rate_limit_events = 0  # H51: how many usage readings this call's session brought back

    # -- lifecycle -----------------------------------------------------------

    async def start(self) -> None:
        async with self._start_lock:  # warm-up and the first turn may both call this
            if self._client:
                return
            t = time.perf_counter()
            client = ClaudeSDKClient(self._options)
            await client.connect()
            self._client = client
            self._reader = asyncio.create_task(self._read_forever(), name="claude-reader")
            logger.info(f"Claude session open ({self.model}) in {time.perf_counter() - t:.2f}s")

    async def connectors(self) -> list[dict]:
        """The session's MCP servers (their claude.ai connectors) and their state, asked live:
        the init message can come before they have connected."""
        if not self._client:
            return []
        try:
            return list((await self._client.get_mcp_status()).get("mcpServers", []))
        except Exception as e:
            logger.warning(f"Connector status: {e!r}")
            return []

    async def stop(self) -> None:
        client, self._client = self._client, None
        for task in (self._drainer, self._reader):
            if task and not task.done():
                task.cancel()
        if client:
            try:
                await client.disconnect()
            except Exception as e:  # closing is best effort
                logger.warning(f"Claude session close: {e}")
        logger.info("Claude session closed")

    async def _read_forever(self) -> None:
        assert self._client
        try:
            async for msg in self._client.receive_messages():
                if isinstance(msg, RateLimitEvent):
                    self._save_usage(msg)  # only the numbers; it's not part of any turn
                    continue
                await self._queue.put(msg)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Claude stream ended: {e}")
            await self._queue.put(e)

    def _save_usage(self, msg: RateLimitEvent) -> None:
        """H51: the plan usage that comes back with the call's own session, saved for the usage
        check (usage-live.json), so the status page gets fresh numbers from every call, for free.
        Also on a Free call: the same login, so the same numbers, and nothing else of the call."""
        self.rate_limit_events += 1
        try:
            out = usagelive.save((msg.rate_limit_info.raw or {}).get("unifiedWindows"), "call")
            if out:
                logger.info(f"Usage saved from the call's session: {usagelive.summary(out)}")
        except Exception as e:  # never let the usage get in the way of the call
            logger.warning(f"Usage from the call's session not saved: {e!r}")

    # -- turns ---------------------------------------------------------------

    async def ask(self, text: str, _retry: bool = False) -> AsyncIterator["str | ToolStarted"]:
        """Send one user turn and yield the reply as text pieces, as they arrive.

        If the caller is cancelled mid-reply (the user cut in) or closes the generator
        early, the rest of the reply is interrupted in the CLI and dropped. Callers should
        close the generator explicitly (aclose) so that happens right away.
        """
        if not self._client:
            await self.start()
        elif self._dead:
            await self._reconnect()
        # Wait for an interrupted turn to finish draining before the next one.
        try:
            await asyncio.wait_for(self._idle.wait(), timeout=15)
        except asyncio.TimeoutError:
            logger.warning("Previous Claude turn never finished; reconnecting")
            await self._reconnect()

        async with self._lock:
            stats = TurnStats()
            self.last_turn = stats
            self._idle.clear()
            self._answering = True
            t0 = time.perf_counter()
            streamed = False
            got_result = False
            died = False
            try:
                await self._client.query(text)
                while True:
                    msg = await self._queue.get()
                    if isinstance(msg, Exception):
                        # F60: the session died mid-turn. Not raised: he hears it at once, the session
                        # reopens and this same turn is answered (below, outside the lock).
                        self._dead = True
                        died = True
                        logger.error(f"F60: Claude's session died mid-turn: {msg!r}")
                        break
                    if isinstance(msg, StreamEvent):
                        ev = msg.event
                        if ev.get("type") == "content_block_start":
                            stats.events.append((time.perf_counter() - t0, (ev.get("content_block") or {}).get("type", "?")))
                        elif ev.get("type") == "message_start":
                            stats.events.append((time.perf_counter() - t0, "message_start"))
                        if msg.parent_tool_use_id is None:
                            tool = _tool_start(msg.event)
                            if tool:
                                stats.tools.append(tool)
                                yield ToolStarted(tool)
                                continue
                            piece = _text_delta(msg.event)
                            if piece:
                                if stats.first_text_s is None:
                                    stats.first_text_s = time.perf_counter() - t0
                                streamed = True
                                stats.text += piece
                                yield piece
                    elif isinstance(msg, AssistantMessage):
                        # Only used when nothing was streamed (e.g. an API error text).
                        if not streamed and msg.parent_tool_use_id is None:
                            full = "".join(b.text for b in msg.content if isinstance(b, TextBlock))
                            if msg.error:
                                logger.error(f"Claude error: {msg.error}: {full}")
                            elif full:
                                stats.first_text_s = time.perf_counter() - t0
                                stats.text += full
                                streamed = True
                                yield full
                    elif isinstance(msg, SystemMessage):
                        if msg.subtype == "init":
                            self.session_id = msg.data.get("session_id")
                            self.init_info = msg.data
                    elif isinstance(msg, UserMessage):
                        stats.events.append((time.perf_counter() - t0, "tool_result"))
                    elif isinstance(msg, ResultMessage):
                        got_result = True
                        stats.total_s = time.perf_counter() - t0
                        stats.is_error = msg.is_error
                        stats.terminal_reason = msg.terminal_reason
                        stats.model_usage = list((msg.model_usage or {}).keys())
                        if msg.is_error and not streamed:
                            logger.error(f"Claude turn failed: {msg.result}")
                            yield "Sorry, something went wrong on my side. Can you say that again?"
                        break
            finally:
                # Reached on a normal end, on cancellation (the user cut in) and when the
                # caller closes the generator early. Without a ResultMessage the reply is
                # still running in the CLI: interrupt it and drop the rest, in the background.
                self._answering = False
                if got_result or died:
                    self._idle.set()
                else:
                    stats.interrupted = True
                    self._start_drain()

        if died:
            if _retry:
                yield "Sorry, I lost my line again. Can you say that again?"
                return
            yield LOST_LINE
            async for piece in self.ask(text, _retry=True):  # reopens the session (resumed) and answers
                yield piece

    def cancel_turn(self) -> None:
        """Interrupt the running reply, if there is one, and drop what's left of it.

        Normally not needed: closing or cancelling ask() does this by itself. While an
        ask() is still reading its reply, this does nothing: that reader owns the turn (a
        second reader on the queue would leave it waiting forever), and closing it is what
        stops the turn. This matters for the warm-up turn at call start, which the user's
        first words must not cut off.
        """
        if not self._idle.is_set() and not self._answering:
            self._start_drain()

    def _start_drain(self) -> None:
        if self._drainer and not self._drainer.done():
            return
        self._drainer = asyncio.create_task(self._interrupt_and_drain(), name="claude-drain")

    async def _interrupt_and_drain(self) -> None:
        t = time.perf_counter()
        try:
            if self._client:
                await self._client.interrupt()
                self.interrupts_sent += 1
            dropped = 0
            while True:
                msg = await asyncio.wait_for(self._queue.get(), timeout=15)
                if isinstance(msg, Exception):
                    break
                if isinstance(msg, ResultMessage):
                    if self.last_turn:
                        self.last_turn.terminal_reason = msg.terminal_reason
                    break
                dropped += 1
            logger.info(
                f"Claude interrupted: dropped {dropped} messages, settled in "
                f"{time.perf_counter() - t:.2f}s"
            )
        except Exception as e:
            logger.warning(f"Claude interrupt didn't settle cleanly: {e!r}")
        finally:
            self._idle.set()

    async def _reconnect(self) -> None:
        sid = self.session_id
        await self.stop()
        if sid and self._dead:
            # F60: reopen with the call so far, not an empty start
            self._options = dataclasses.replace(self._options, resume=sid)
        self._queue = asyncio.Queue()
        self._dead = False
        self._idle.set()
        await self.start()


def _tool_start(event: dict) -> str | None:
    if event.get("type") == "content_block_start":
        block = event.get("content_block") or {}
        if block.get("type") in ("tool_use", "server_tool_use", "mcp_tool_use"):
            return block.get("name") or "tool"
    return None


def _text_delta(event: dict) -> str | None:
    if event.get("type") == "content_block_delta":
        delta = event.get("delta") or {}
        if delta.get("type") == "text_delta":
            return delta.get("text")
    return None
