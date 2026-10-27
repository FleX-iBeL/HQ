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
import json
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
import coaching
import news
import ringing
import todo
import tour
import transcript
from transcript import CallTranscript, now


def _about(e: dict, what: str):
    """H101, H200, H225: what a call started from something in the app gets: an appointment (agenda), a to-do item
    (todo), or a layer or check-in of their Life coaching (coaching). H236: or setting up their news (news)."""
    if e.get("kind") == "news":
        mod = news
    elif e.get("kind") == "ring":  # H238: the agent called him and he picked up
        mod = ringing
    else:
        mod = todo if e.get("kind") == "todo" else coaching if e.get("kind") == "coaching" else agenda
    if what == "line":
        return mod.when_line(e)
    if what == "greetings":
        return mod.greetings(e, config.ME["name"])
    return mod.call_note(e, config.USER)


class Call:
    def __init__(self, *, model: str | None = None, voice: str | None = None, calls_dir: Path | None = None,
                 wrap_up: str = config.WRAP_UP, test_mode: bool = False, waiting_lines: bool = True,
                 free: bool = False, load: str | None = None, loops: "open_loops.OpenLoops | None" = None,
                 agent: str | None = None, continues: str | None = None, handover: bool = False,
                 voices: dict | None = None, about: dict | None = None, demo: bool = False, demo_topic: str = "",
                 callback: bool = False):
        self._loops = loops
        # H74: a demo call from the tutorial is a Free call (nothing of his, nothing saved) on Opus, with no tools
        self.demo = bool(demo)
        if self.demo:
            free, model = True, tour.MODEL
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
        if self.demo:
            persona += tour.rules(demo_topic, self.agent["name"], {a["id"]: a["name"] for a in agents.visible(config.FOLDER)})
        self.panel: list[dict] = [self.agent]  # H79: who's on the call; two on a three-way call, three on a four-way (H121)
        self.speaker = self.agent  # H79: who answers now
        # Fable clean-up (27 October 2026): on a three-way call each agent has her own Claude session (_brain_for), with
        # only her own context, persona and model. Before, both shared the caller's session, so whoever was brought in
        # sat on the caller's whole context (Moneypenny on Pepper's, his vision included; his words: "How the fuck
        # would money penny know my vision?!"). The one who takes a turn is told what the others said since her last.
        self.brains: dict = {}
        self._seen: dict[str, int] = {}  # per agent: how many lines of the transcript she has had
        self._calls_dir = calls_dir
        self.voices: dict[str, str] = {k: str(v) for k, v in (voices or {}).items()}  # H79: each agent's voice from the page
        self.switched_to: dict | None = None  # H79: she handed the call over to this one
        self.wrap_up_mode = "off" if free else wrap_up  # "on", "dry" or "off"
        # H60: the earlier call this one continues (read before this call's own transcript exists)
        # H79: handover: the earlier call's agent just put her on (he asked for her); she picks up the phone
        self.handover = bool(handover)
        self.callback = bool(callback) and not free  # H238: she calls him right back, continuing the call
        # H164: the first call of the day (any agent, from the saved calls) gets a first-of-the-day hello; read
        # before this call's own transcript exists. A free call isn't saved, so it doesn't count.
        self.first_today = transcript.first_call_today(calls_dir, agent=self.agent["name"])
        self.continued = None if free or not continues else transcript.continue_from(continues, calls_dir,
                                                                                     me=self.agent["name"])
        self.transcript = CallTranscript(calls_dir, model=self.model, keep=not free, agent=self.agent["name"],
                                         continues=self.continued,
                                         about=_about(self.about, "line") if self.about else "")
        if free:
            config.FREE_DIR.mkdir(parents=True, exist_ok=True)
            self.policy = None
            self.brain = make_brain(self.model, None, cwd=config.FREE_DIR, free=True, persona=persona, demo=self.demo)
        else:
            # In tests, nothing may change: no file edits, no git, even during the call.
            self.policy = Policy(config.FOLDER, dry_run=test_mode, listener=self._on_decision)
            # H246: she loads what fits her role; a Deep call with the day's agent keeps the whole folder, as before
            context = agents.context_of(self.agent)
            self.context = "all" if context == "day" and self.load == "deep" else context
            self.policy.memory_writes = self.context == "build"  # H280: her lessons stay
            # H282: her own thinking time (Moneypenny high), the rest as before; a three-way keeps the first one's
            self.brain = make_brain(self.model, self.policy, load=self.load, persona=persona, context=self.context,
                                    effort=agents.effort_of(self.agent, self.model),
                                    resume=self._line_for(self.agent))
        self.brains[self.agent["id"]] = self.brain
        self.stt = make_stt(quiet=free)
        self.voice = voice if voice in config.VOICES else config.VOICE
        self.voices.setdefault(self.agent["id"], self.voice)
        self.tts = make_tts(self.voice)
        self.fillers = FillerPlayer(self.tts._kokoro, voice=self.voice, on_play=self.transcript.filler,
                                    waiting_lines=waiting_lines,
                                    # H76: her own greetings, in her character
                                    greetings=tour.greetings(self.agent["name"]) if self.demo
                                    else _about(self.about, "greetings") if self.about
                                    else config.handover_greetings(self.agent, self.continued["agent"])
                                    if self.continued and self.handover and self.continued.get("agent")
                                    and self.continued["agent"] != self.agent["name"]
                                    else config.callback_greetings(self.agent)
                                    if self.continued and self.callback
                                    else config.continue_greetings(self.agent)
                                    if self.continued and not self.handover
                                    else config.greetings_now(self.agent, first=self.first_today))
        self.llm = ClaudeSessionLLMService(
            self.brain, stop_brain_on_end=False, fillers=self.fillers,
            policy=self.policy, transcript=self.transcript,
        )
        self.llm.switch_marks = agents.switch_marks(self.others)
        self.llm.before_turn = self._before_turn
        self.llm.joined_hi = self._joined_hi
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
        if self.callback:
            return (
                f"{config.USER} asked you to hang up and call him right back, and this is that call: it continues "
                f"the call of {c['started']} a moment ago, on a freshly loaded app. The call system greets him as you "
                "being back on the line, so carry straight on from where it was, without reading it back or asking "
                "where you were. What was said on that call, oldest first (\"You\" is you; another agent's lines "
                f"carry her name):\n<earlier-call>\n{c['text']}\n</earlier-call>\n"
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
        """On a three-way call: who answers this turn, her own session, model and voice, and a note saying so."""
        if len(self.panel) < 2:
            return self._goodbye_note(self.speaker, words)
        who = agents.pick(self.panel, words, self.speaker["id"])
        notes = []
        joined, self._joined = getattr(self, "_joined", None), None
        if joined is not None and joined is not who:
            notes.append(f"[Call system: {joined['name']} ({joined['speciality']}) is on this call too now, a "
                         f"{agents.way(self.panel)} call. She has her own line and answers when he speaks to her; you "
                         f"only answer the turns the call system gives you.]")
        was = self.speaker
        await self._switch_to(who)
        notes += self._catch_up(who, words, tell=who is not was)
        rest = ", ".join(a["name"] for a in self.panel if a is not who)
        notes.append(f"[Call system: {agents.way(self.panel)} call with {rest} and {config.USER}. This turn is yours, "
                     f"{who['name']}: answer as yourself, in your own character.]")
        return notes + self._goodbye_note(who, words)

    async def _joined_hi(self, other_id: str) -> list[str]:
        """H130: once the line bringing her in has been heard, the one who joined says hi: her own session, model and
        voice from now on, and the note for her own first line. [] when she isn't the one who just joined (he spoke first)."""
        joined = getattr(self, "_joined", None)
        if joined is None or joined["id"] != other_id or len(self.panel) < 2:
            return []
        self._joined = None
        await self._switch_to(joined)
        self._catch_up(joined, "", tell=False)
        rest = ", ".join(a["name"] for a in self.panel if a is not joined)
        return [f"[Call system: you, {joined['name']}, have just been brought in: a {agents.way(self.panel)} call with "
                f"{rest} and {config.USER}. Nobody has asked you anything yet: say one short line of your own that "
                f"you're there now, the way a person joining a call says hi, in your character, picking up on what was "
                f"said so far if it fits. Your own words, never a set greeting, never the same line as before. Just that "
                f"line, no question to answer, no marks; then he goes on.]"]

    def _line_for(self, who: dict) -> str | None:
        """The open line (app/lines.py): her last session on this computer, resumed when the switch is on and the
        line is fresh enough; a free or demo call never resumes."""
        if self.free or self.demo:
            return None
        try:
            import lines
            sid = lines.session_for(who["id"])
            if sid:
                logger.info(f"{who['name']}'s line is open: resuming session {sid[:8]}")
            return sid
        except Exception as e:
            logger.warning(f"The open line: {e!r}")
            return None

    def _hand_transcript(self) -> None:
        """One-way sync (Fable, 27 October 2026): a call taken on the backup leaves its transcript here, which a
        receive-only folder never sends; so at the end it goes to the main whole, by hand-over."""
        try:
            import sys as _s
            if str(config.ROOT / "routine") not in _s.path:
                _s.path.insert(0, str(config.ROOT / "routine"))
            import role
            p = self.transcript.path
            if p is None or not p.exists() or not role.is_backup() or not role.one_way():
                return
            rel = p.relative_to(config.FOLDER).as_posix() if config.FOLDER in p.parents else None
            if not rel:
                return
            text = p.read_text(encoding="utf8")
            if len(text.encode("utf8")) > 100_000:
                logger.warning("The transcript is too big to hand over whole; the main gets it when this HQ is main")
                return
            code, out, err, how = role.hand("handover", ["put", rel, json.dumps({"text": text}, ensure_ascii=False)])
            logger.info(f"Transcript handed to the main ({how}): {(out or err).strip()[:120]}")
        except Exception as e:
            logger.warning(f"Handing the transcript to the main: {e!r}")

    def _note_lines(self) -> None:
        """After the call: every agent's session on it, and how big its context got, for the next start."""
        try:
            import lines
            for aid, b in self.brains.items():
                if b is not None and getattr(b, "session_id", None):
                    lt = getattr(b, "last_turn", None)
                    lines.note(aid, b.session_id, getattr(lt, "context_tokens", None), "call")
        except Exception as e:
            logger.warning(f"The open line: noting the sessions: {e!r}")

    async def _brain_for(self, who: dict):
        """Her own Claude session on this call (Fable clean-up): made the first time she answers, with her own context
        (H246), persona and model, and primed with what was said on the call so far, the way Continue does (H60)."""
        b = self.brains.get(who["id"])
        if b is not None:
            return b
        on_call = {a["id"] for a in self.panel}
        others = [a for a in agents.visible(config.FOLDER) + agents.soon(config.FOLDER)
                  if a["id"] != who["id"] and a["id"] not in on_call]
        persona = agents.persona(who, config.USER) + agents.switch_rules(who, others, config.USER)
        context = agents.context_of(who)
        context = "all" if context == "day" and who["load"] == "deep" else context
        model = config.MODEL_ALIASES.get(agents.runs_on(who["model"]), who["model"])
        b = make_brain(model, self.policy, load=who["load"], persona=persona, context=context,
                       effort=agents.effort_of(who, model), resume=self._line_for(who))
        self.brains[who["id"]] = b
        t = time.perf_counter()
        await b.start()
        so_far = ""
        if self.transcript.path is not None:
            c = transcript.continue_from(self.transcript.path.stem, self._calls_dir, me=who["name"])
            if c:
                so_far = (" What was said on this call so far, oldest first (\"You\" is you; the other lines carry "
                          f"their names):\n<call-so-far>\n{c['text']}\n</call-so-far>")
        stamp = now().strftime("%A %-d %B %Y, %H:%M")
        with_ = ", ".join(a["name"] for a in self.panel if a is not who) or "nobody else"
        text = (f"[Call system: {config.USER} is on a live call on HQ with {with_}, and you, {who['name']}, have just "
                f"been brought in: a {agents.way(self.panel)} call. It is {stamp}.{so_far}\n"
                "Don't do anything yet and use no tools. Reply with only the word: ready]")
        async for _ in b.ask(text):
            pass
        logger.info(f"{who['name']}'s own session is open and primed in {time.perf_counter() - t:.1f}s")
        self._seen[who["id"]] = len(self._lines())
        return b

    def _lines(self) -> list[dict]:
        if self.transcript.path is None:
            return []
        try:
            return transcript.read_lines(self.transcript.path)
        except OSError:
            return []

    def _catch_up(self, who: dict, words: str, tell: bool) -> list[str]:
        """What the others and he said since her last turn (her own session didn't hear it), as a note for this turn;
        [] when nothing, or when she answered the turn before. Always moves her mark to now."""
        lines = self._lines()
        seen, self._seen[who["id"]] = self._seen.get(who["id"], 0), len(lines)
        if not tell:
            return []
        new = [ln for ln in lines[seen:] if ln["who"] != "filler" and not ln.get("cancelled")
               and not (ln["who"] == "hq" and ln.get("agent", self.agent["name"]) == who["name"])]
        if new and new[-1]["who"] == "user" and words and transcript._one_line(words) == new[-1]["text"]:
            new = new[:-1]  # the words of this turn come with it, not here
        if not new:
            return []
        rows = [f"{config.USER_LABEL if ln['who'] == 'user' else ln.get('agent') or self.agent['name']}: "
                f"{transcript._one_line(ln['text'])}" for ln in new]
        return [f"[Call system: since your last turn on this call, oldest first:\n" + "\n".join(rows) + "]"]

    async def _switch_to(self, who: dict) -> None:
        """H79: from now on she answers: her own session (her model with it) and her voice."""
        if who is not self.speaker:
            self.llm.brain = await self._brain_for(who)
            self.policy.memory_writes = agents.context_of(who) == "build"  # H280: her lessons, on her turns
            self._speak_as(who)
            self.speaker = who
        self.transcript.speaker = who["name"]

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
            # 27 October 2026: Moneypenny (context "build") talks about building only, so no mail heads-up for her
            note = "" if self.free or getattr(self, "context", "") == "build" else open_loops.call_note(
                self._loops or open_loops.read(config.FOLDER))
            self.open_loops_note = note
            text = (
                f"[Call system: {config.USER} is calling you now on HQ, the voice call. It is {stamp}. "
                + (f"{note}\n" if note else "")
                + (self._continue_note() if self.continued else "")
                + (_about(self.about, "note") if self.about else "")
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
                day=self.transcript.started.strftime("%Y-%m-%d"),
                start_short=self.transcript.started.strftime("%Y-%m-%d %H:%M"),
                transcript=rel,
            )
            if template is config.WRAP_UP_PROMPT:
                from policy import is_backup  # H56.3: the backup never commits
                if is_backup():
                    prompt = re.sub(r"^3\. Then commit and push.*?no here-documents\.$", lambda m: config.WRAP_UP_BACKUP_STEP,
                                    prompt, count=1, flags=re.S | re.M)
            if template is config.WRAP_UP_PROMPT:  # H232: HQ itself keeps what the agents said about themselves
                try:
                    import about_self
                    words = self.transcript.path.read_text(encoding="utf8")
                    who, said = about_self.call_lines(words, agents.load(config.FOLDER))
                    kept = await asyncio.wait_for(asyncio.to_thread(about_self.harvest, config.FOLDER, who, said),
                                                  timeout=about_self.HARVEST_TIMEOUT + 10)
                    logger.info(f"About themselves: {len(kept)} new kept" + "".join(f"; {n}: {f}" for n, f in kept))
                except Exception as e:
                    logger.warning(f"About themselves: the harvest failed: {e!r}")
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
            if not self.free:
                self._note_lines()
                self._hand_transcript()
            for b in self.brains.values() or [self.brain]:
                await b.stop()
