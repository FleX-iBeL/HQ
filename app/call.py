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

H60: continues=<a saved call's name> starts the call where that one left off: the warm-up message
carries what was said on it (transcript.continue_from), the greeting says so, and the new transcript
notes which call it continues. Never on Free (nothing of his goes in), and Free calls are never saved.

J2: the warm-up message carries the very important open items from his mail list
(open_loops.py), so the first reply names them, on Quick and on Deep. Tests pass their own.
"""
from __future__ import annotations

import asyncio
import re
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
import agenda
import transcript
from transcript import CallTranscript, now


class Call:
    def __init__(self, *, model: str | None = None, voice: str | None = None, calls_dir: Path | None = None,
                 wrap_up: str = config.WRAP_UP, test_mode: bool = False, waiting_lines: bool = True,
                 free: bool = False, load: str | None = None, loops: "open_loops.OpenLoops | None" = None,
                 agent: str | None = None, continues: str | None = None, handover: bool = False,
                 voices: dict | None = None, about: dict | None = None):
        self._loops = loops
        # H101: the appointment in his calendar this call was started from (agenda.about); never on Free
        self.about = None if free or not isinstance(about, dict) else about
        self.model = config.MODEL_ALIASES.get(agents.runs_on(model), model) if model else config.MODEL
        self.free = free
        # B1: Quick loads only part of his folder, Deep everything. Without a mode from the page,
        # the model decides: Opus is Deep, the rest Quick.
        self.load = load if load in ("quick", "deep") else ("deep" if self.model == config.MODEL_ALIASES["opus"] else "quick")
        # H29: the agent on this call (Pepper for Quick, Donna for Deep by default); her personality
        # goes after the call rules. Without one asked for, the agent with this call's load.
        self.agent = agents.find(config.FOLDER, agent, self.load)
        persona = agents.persona(self.agent, config.USER)
        # H79: the other agents she can hand over to or bring in (never on Free: one plain Claude);
        # H121: one still coming soon too, to bring in only (agents.switch_marks)
        self.others = [] if free else [a for a in agents.visible(config.FOLDER) + agents.soon(config.FOLDER)
                                       if a["id"] != self.agent["id"]]
        persona += agents.switch_rules(self.agent, self.others, config.USER)
        self.panel: list[dict] = [self.agent]  # H79: who's on the call; two on a three-way call, three on a four-way (H121)
        self.speaker = self.agent  # H79: who answers now
        self.voices: dict[str, str] = {k: str(v) for k, v in (voices or {}).items()}  # H79: each agent's voice from the page
        self.switched_to: dict | None = None  # H79: she handed the call over to this one
        self.wrap_up_mode = "off" if free else wrap_up  # "on", "dry" or "off"
        # H60: the earlier call this one continues (read before this call's own transcript exists)
        # H79: handover: the earlier call's agent just put her on (he asked for her); she picks up the phone
        self.handover = bool(handover)
        self.continued = None if free or not continues else transcript.continue_from(continues, calls_dir,
                                                                                     me=self.agent["name"])
        self.transcript = CallTranscript(calls_dir, model=self.model, keep=not free, agent=self.agent["name"],
                                         continues=self.continued,
                                         about=agenda.when_line(self.about) if self.about else "")
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
        self.voices.setdefault(self.agent["id"], self.voice)
        self.tts = make_tts(self.voice)
        self.fillers = FillerPlayer(self.tts._kokoro, voice=self.voice, on_play=self.transcript.filler,
                                    waiting_lines=waiting_lines,
                                    # H76: her own greetings, in her character
                                    greetings=agenda.greetings(self.about, config.ME["name"]) if self.about
                                    else config.continue_greetings(self.agent)
                                    if self.continued and not self.handover else config.greetings_now(self.agent))
        self.llm = ClaudeSessionLLMService(
            self.brain, stop_brain_on_end=False, fillers=self.fillers,
            policy=self.policy, transcript=self.transcript,
        )
        self.llm.switch_marks = agents.switch_marks(self.others)
        self.llm.before_turn = self._before_turn
        self.prime_s: float | None = None
        self.open_loops_note = ""
        self.wrap_up_reply: str | None = None
        self._finished = False
        self.ended_by_agent = False  # H75: she hung up after his goodbye

    def _continue_note(self) -> str:
        """H60: what the new call's Claude gets about the call it continues."""
        c = self.continued
        who = f" with {c['agent']}" if c.get("agent") else ""
        if self.handover and c.get("agent") and c["agent"] != self.agent["name"]:
            return (
                f"{c['agent']} just put you on the phone: {config.USER} asked for you on the call of {c['started']}, "
                "so the call system greets him as you picking up. Carry on right where it was, like taking over the "
                "phone, knowing what was said, without reading it back. What was said on that call, oldest first "
                f"(\"You\" is you; {c['agent']}'s lines carry her name):\n"
                f"<earlier-call>\n{c['text']}\n</earlier-call>\n"
            )
        return (
            f"This call continues the earlier call of {c['started']}{who}. The call system greets "
            f"{config.USER} by saying you're picking up where you left off, so pick up from there: "
            "know what was said and where it ended, without reading it back unless asked. "
            "What was said on that call, oldest first (\"You\" is you; another agent's lines carry her name):\n"
            f"<earlier-call>\n{c['text']}\n</earlier-call>\n"
        )

    # -- H79: another agent on the call -----------------------------------------

    def voice_for(self, agent: dict) -> str:
        v = self.voices.get(agent["id"]) or agent.get("voice") or config.VOICE
        return v if v in config.VOICES else config.VOICE

    async def three_way(self, other_id: str) -> dict | None:
        """She brought another agent in: from the next turn both are on the call, in the same conversation."""
        other = next((a for a in self.others if a["id"] == other_id), None)
        if other is None or other in self.panel:
            return None
        self.panel.append(other)
        self._joined = other
        self.transcript.note(f"{other['name']} joined: a {agents.way(self.panel)} call with {', '.join(a['name'] for a in self.panel)}")
        return other

    def _speak_as(self, agent: dict) -> None:
        """Her voice from now on (the fillers too)."""
        v = self.voice_for(agent)
        from pipecat.transcriptions.language import Language
        self.tts._settings.voice = v
        self.tts._settings.language = self.tts.language_to_service_language(
            Language.EN_GB if config.voice_lang(v) == "en-gb" else Language.EN)
        self.fillers._voice = v

    async def _before_turn(self, words: str) -> list[str]:
        """On a three-way call: who answers this turn, her model and voice, and a note saying so."""
        if len(self.panel) < 2:
            return self._goodbye_note(self.speaker, words)
        who = agents.pick(self.panel, words, self.speaker["id"])
        notes = []
        joined, self._joined = getattr(self, "_joined", None), None
        if joined is not None:
            notes.append(f"[Call system: {joined['name']} is now on this call too, a {agents.way(self.panel)} call. Who she is:"
                         f"{agents.persona(joined, config.USER)}]")
        if who is not self.speaker:
            model = config.MODEL_ALIASES.get(agents.runs_on(who["model"]), who["model"])
            if self.brain._client and model != self.brain.model:
                try:
                    await self.brain._client.set_model(model)
                    self.brain.model = model
                except Exception as e:
                    logger.warning(f"H79: model switch to {model} failed: {e!r}")
            self._speak_as(who)
            self.speaker = who
        self.transcript.speaker = who["name"]
        rest = ", ".join(a["name"] for a in self.panel if a is not who)
        notes.append(f"[Call system: {agents.way(self.panel)} call with {rest}. {who['name']} answers this turn: answer as "
                     f"{who['name']}, in her character, and only as her.]")
        return notes + self._goodbye_note(who, words)

    def _goodbye_note(self, who: dict, words: str) -> list[str]:
        """H129: on a turn that may be his goodbye, what he's doing right now (his calendar, else his to-do list), so
        her goodbye comments on it. Not on Free (nothing of his here), not for an agent with her own goodbye."""
        if self.free or who.get("own_goodbye") or not config.sounds_like_goodbye(words):
            return []
        try:
            return [agenda.goodbye_note(config.USER)]
        except Exception as e:
            logger.warning(f"H129: what he's doing now couldn't be read: {e!r}")
            return []

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
                f"[Call system: {config.USER} is calling you now on HQ, the voice call. It is {stamp}. "
                + (f"{note}\n" if note else "")
                + (self._continue_note() if self.continued else "")
                + (agenda.call_note(self.about, config.USER) if self.about else "")
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
            self.transcript.note(f"{self.speaker['name']} put {self.switched_to['name']} on: the call goes on with her"
                                 if self.switched_to else
                                 f"{self.speaker['name']} hung up after the goodbye" if self.ended_by_agent
                                 else f"{config.USER_LABEL} hung up")
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
                logger.info("After-call work is off (HQ_WRAP_UP=off)")
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
            if template is config.WRAP_UP_PROMPT:
                from policy import is_backup  # H56.3: the backup never commits
                if is_backup():
                    prompt = re.sub(r"^3\. Then commit and push.*?no here-documents\.$", lambda m: config.WRAP_UP_BACKUP_STEP,
                                    prompt, count=1, flags=re.S | re.M)
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
