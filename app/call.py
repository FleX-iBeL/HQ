"""One call: everything that lives as long as a call does, shared by the live call
(bot.py) and the headless tests.

- the permission policy (policy.py), in "call" mode while he's on the line;
- the transcript (transcript.py), started when the call connects;
- the Claude session (brain.py), opened and primed at connect so the first answer is quick;
- hearing, voice and the fillers;
- after hang-up: one last instruction to the same session (write things down, commit,
  push), then the session closes. finish() runs from bot.py's `finally`, so it also runs
  when he just closes the browser tab.

H7, free mode (free=True): the plain Claude of A2 in an empty folder outside his files, no
policy, no transcript file, no after-call work. H8: on Quick's or Deep's model, with web search
and fetching pages as its only tools. The chat log on the page (H6) still works.

B1: a Quick call loads only part of his folder (quick_context.py); Deep loads it all.

J2: the warm-up message carries the very important open items from his mail list
(open_loops.py), so the first reply names them, on Quick and on Deep. Tests pass their own.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

from loguru import logger

import config
import agents
import open_loops
from claude_llm import ClaudeSessionLLMService
from fillers import FillerPlayer
from pipeline import make_brain, make_stt, make_tts, warm_up_tts
from policy import SESSION_TOOLS, Policy
from transcript import CallTranscript, now


class Call:
    def __init__(self, *, model: str | None = None, voice: str | None = None, calls_dir: Path | None = None,
                 wrap_up: str = config.WRAP_UP, test_mode: bool = False, waiting_lines: bool = True,
                 free: bool = False, load: str | None = None, loops: "open_loops.OpenLoops | None" = None,
                 agent: str | None = None):
        self._loops = loops
        self.model = config.MODEL_ALIASES.get(model or "", model or config.MODEL)
        self.free = free
        # B1: Quick loads only part of his folder, Deep everything. Without a mode from the page,
        # the model decides: Opus is Deep, the rest Quick.
        self.load = load if load in ("quick", "deep") else ("deep" if self.model == config.MODEL_ALIASES["opus"] else "quick")
        # H29: the agent on this call (Pepper for Quick, Donna for Deep by default); her personality
        # goes after the call rules. Without one asked for, the agent with this call's load.
        self.agent = agents.find(config.FOLDER, agent, self.load)
        persona = agents.persona(self.agent, config.USER)
        self.wrap_up_mode = "off" if free else wrap_up  # "on", "dry" or "off"
        self.transcript = CallTranscript(calls_dir, model=self.model, keep=not free, agent=self.agent["name"])
        if free:
            config.FREE_DIR.mkdir(parents=True, exist_ok=True)
            self.policy = None
            self.brain = make_brain(self.model, None, cwd=config.FREE_DIR, free=True, persona=persona)
        else:
            # In tests, nothing may change: no file edits, no git, even during the call.
            self.policy = Policy(config.FOLDER, dry_run=test_mode, listener=self._on_decision)
            self.brain = make_brain(self.model, self.policy, load=self.load, persona=persona)
        self.stt = make_stt(quiet=free)
        self.voice = voice if voice in config.VOICES else config.VOICE
        self.tts = make_tts(self.voice)
        self.fillers = FillerPlayer(self.tts._kokoro, voice=self.voice, on_play=self.transcript.filler,
                                    waiting_lines=waiting_lines)
        self.llm = ClaudeSessionLLMService(
            self.brain, stop_brain_on_end=False, fillers=self.fillers,
            policy=self.policy, transcript=self.transcript,
        )
        self.prime_s: float | None = None
        self.open_loops_note = ""
        self.wrap_up_reply: str | None = None
        self._finished = False

    def _on_decision(self, tool, summary, decision):
        if tool in SESSION_TOOLS and tool != "Skill":
            return  # loading tools and the session's own to-do list: noise in a transcript
        self.transcript.tool(summary, decision.verdict, decision.why)

    async def warm(self) -> None:
        """Open the Claude session and prime it (the folder's files are read into its
        cache), load Whisper and run Kokoro once. The call starts right away; if the user
        talks before this is done, his first turn just waits for it."""
        t = time.perf_counter()

        async def prime():
            await self.brain.start()
            stamp = now().strftime("%A %-d %B %Y, %H:%M")
            note = "" if self.free else open_loops.call_note(self._loops or open_loops.read(config.FOLDER))
            self.open_loops_note = note
            text = (
                f"[Call system: {config.USER} is calling you now on Jarvis VA, the voice call. It is {stamp}. "
                + (f"{note}\n" if note else "")
                + "Don't do anything yet and use no tools. Reply with only the word: ready]"
            )
            async for _ in self.brain.ask(text):
                pass
            self.prime_s = time.perf_counter() - t

        results = await asyncio.gather(prime(), asyncio.to_thread(self.stt.warm_up), return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Warm-up: {r!r}")
        k = await asyncio.to_thread(warm_up_tts, self.tts)
        servers = [f"{s.get('name')} ({s.get('status')})" for s in await self.brain.connectors()]
        logger.info(
            f"Warm in {time.perf_counter() - t:.1f}s (Claude primed {self.prime_s or 0:.1f}s, Kokoro {k:.2f}s); "
            f"connectors: {', '.join(servers) or 'none'}"
        )
        self.transcript.note("connected; connectors: " + (", ".join(servers) or "none"))

    async def finish(self) -> None:
        """After hang-up: close the transcript, let Claude do the after-call work, close
        the session. Safe to call twice."""
        if self._finished:
            return
        self._finished = True
        try:
            self.transcript.note(f"{config.USER_LABEL} hung up")
            self.transcript.end()
            if self.free:
                logger.info("Free mode: nothing kept, no after-call work")
                return
            spoke = any(t.get("words") for t in self.llm.turns)
            if not spoke:
                logger.info("Nobody said anything on this call: no after-call work, transcript removed")
                self.transcript.path.unlink(missing_ok=True)
                return
            if self.wrap_up_mode == "off":
                logger.info("After-call work is off (JARVIS_WRAP_UP=off)")
                return
            # Nobody can answer questions now, and the transcript is closed.
            self.policy.listener = None
            self.policy.pending.clear()
            self.policy.unattended = True
            if self.wrap_up_mode == "dry":
                self.policy.dry_run = True
                template = config.WRAP_UP_DRY_PROMPT
            else:
                template = config.WRAP_UP_PROMPT
            rel = self.transcript.path.relative_to(config.FOLDER) if config.FOLDER in self.transcript.path.parents else self.transcript.path
            prompt = template.format(
                start=self.transcript.start_hhmm,
                start_short=self.transcript.started.strftime("%Y-%m-%d %H:%M"),
                transcript=rel,
            )
            t = time.perf_counter()
            if config.CHEAP_AFTER_CALL and self.brain._client:  # K4: the quiet work on a cheaper model
                try:
                    await self.brain._client.set_model(config.AFTER_CALL_MODEL)
                    logger.info(f"After-call work on {config.AFTER_CALL_MODEL}")
                except Exception as e:
                    logger.warning(f"After-call model switch failed, staying on {self.model}: {e!r}")
            logger.info("After-call work: started")

            async def run():
                reply = ""
                async for piece in self.brain.ask(prompt):
                    if isinstance(piece, str):
                        reply += piece
                return reply

            try:
                self.wrap_up_reply = await asyncio.wait_for(run(), timeout=config.WRAP_UP_TIMEOUT_SECS)
                logger.info(f"After-call work done in {time.perf_counter() - t:.0f}s: {self.wrap_up_reply.strip()}")
            except asyncio.TimeoutError:
                logger.error("After-call work took too long and was stopped")
        except Exception as e:
            logger.error(f"After-call work failed: {e!r}")
        finally:
            await self.brain.stop()
