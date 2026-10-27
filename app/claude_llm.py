"""Pipecat's view of the brain: an LLM service that answers with the Claude session.

It behaves like Pipecat's own LLM services (see pipecat/services/anthropic/llm.py in
1.12.0): on each LLMContextFrame from the user aggregator it pushes
LLMFullResponseStartFrame, then LLMTextFrames as the reply streams in, then
LLMFullResponseEndFrame. The TTS service turns the text into speech sentence by sentence,
so the voice starts at the first full sentence.

Interruptions: when the user starts talking, the user aggregator sends an InterruptionFrame.
Pipecat cancels this service's running task (the one in _process_context); the brain's
ask() generator is closed in the `finally`, which interrupts the reply in the CLI and drops
the rest of it (a running tool call too). The TTS and the output drop the audio they
still had, fillers included.

Memory lives in the Claude session, not in Pipecat's context: each turn sends only the
new words from the user, with short notes from the call system in square brackets when
needed (he cut in; he answered a yes/no question).

A3 adds, all optional (the A2 test runs without them):
- fillers (fillers.py): one per wait, when Claude is quiet for a while;
- the yes/no answer to a permission question (policy.py);
- the transcript (transcript.py).
"""
from __future__ import annotations

import asyncio
import re
import time

from loguru import logger

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    CancelFrame,
    EndFrame,
    DataFrame,
    Frame,
    InterruptionFrame,
    LLMContextFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    StartFrame,
)
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.llm_service import LLMService
from pipecat.services.settings import LLMSettings

import config
from brain import ClaudeBrain, ToolStarted


class JoinedHiFrame(DataFrame):
    """H130: the one just brought in says hi. Queued to the service itself, so it runs like a turn: in order, and a
    cut-in stops it the same way."""

    def __init__(self, agent: str):
        super().__init__()
        self.agent = agent


class ClaudeSessionLLMService(LLMService):
    def __init__(
        self,
        brain: ClaudeBrain,
        *,
        stop_brain_on_end: bool = True,
        fillers=None,  # fillers.FillerPlayer
        policy=None,  # policy.Policy
        transcript=None,  # transcript.CallTranscript
        **kwargs,
    ):
        super().__init__(
            settings=LLMSettings(
                model=brain.model,
                system_instruction=None,  # lives in the Claude session
                temperature=None,
                max_tokens=None,
                top_p=None,
                top_k=None,
                frequency_penalty=None,
                presence_penalty=None,
                seed=None,
                filter_incomplete_user_turns=False,
                user_turn_completion_config=None,
            ),
            **kwargs,
        )
        self.brain = brain
        self.fillers = fillers
        self.policy = policy
        self.transcript = transcript
        self._stop_brain_on_end = stop_brain_on_end
        self._bot_speaking = False
        self._replying = False
        self._cut_off = False
        self._cut_reply = ""  # the reply text that was running when he cut in
        self._worked_on = False  # he cut in while Claude was still working (a tool, thinking)
        # F33: how far into the call's context his words have already gone to Claude (the number of
        # messages, and the last one's text to be sure it's the same context), so a new line carries
        # only itself; reset only when a turn really got no answer (an error)
        self._sent_upto = 0
        self._sent_last = ""
        self._typed: list[str] = []  # H18: messages he typed on the call page, not yet answered
        self._cancel_asked = False  # H31: he tapped Cancel; the interruption that follows isn't a cut-in
        self._cancel_note = ""  # H31: told to Claude with the next turn
        self.on_cancellable = None  # H31: told True/False when Cancel may be tapped (the call page)
        self._cancellable = False
        self._late_cancel: str | None = None  # H38: the Cancel button's line, waiting to go in as his turn
        self.on_hangup = None  # H75: async, called once her goodbye has been heard (bot.py ends the call)
        self.on_callback = None  # H238: async, called once her "calling you right back" has been heard
        # H79: the marks that bring in another agent (agents.switch_marks: mark -> ("switch"|"three-way", id)),
        # async on_switch(id) once her hand-over line has been heard, async on_three_way(id) right after the reply,
        # and async before_turn(words) -> notes for this turn (a three-way call picks who answers; Call sets it).
        self.switch_marks: dict[str, tuple[str, str]] = {}
        self.on_switch = None
        self.on_three_way = None
        self.before_turn = None
        # H130: async joined_hi(id) -> notes for her own first line once she's on the call ([] = she says nothing;
        # Call sets it), asked once the line bringing her in has been heard
        self.joined_hi = None
        self.hear_whole = None  # H165: async (use) -> the whole turn heard again, or None (pipeline sets it)
        self._hangup_task = None
        self._spoke_at = 0.0  # H75: when her voice last started, and stopped
        self._quiet_at = 0.0
        # For tests and logs: what happened in each turn.
        self.turns: list[dict] = []

    def mark_typed(self, text: str) -> None:
        """H18: the next turn that holds this text was typed, not spoken."""
        self._typed.append(text)

    # -- H31: cancel what he just said, before she answers ------------------

    @property
    def cancellable(self) -> bool:
        """A turn is running and Claude hasn't said a word of the reply yet."""
        return bool(self._replying and self.turns and not self.turns[-1]["reply"].strip()
                    and not self.turns[-1].get("cancelled") and not self.turns[-1].get("hi"))

    def _tell_cancellable(self, on: bool) -> None:
        if on == self._cancellable:
            return
        self._cancellable = on
        if self.on_cancellable:
            try:
                self.on_cancellable(on)
            except Exception:
                pass

    def request_cancel(self) -> bool:
        """H31: drop the running turn before she answers. The caller then sends an interruption,
        which stops the reply in the CLI; she says nothing. The transcript marks his line as
        cancelled, and Claude is told with the next turn (the CLI already has the words)."""
        if not self.cancellable:
            return False
        turn = self.turns[-1]
        turn["cancelled"] = True
        self._cancel_asked = True
        self._tell_cancellable(False)
        words = " ".join(turn["words"].split())
        self._cancel_note = (
            f'[Call system: {config.USER} cancelled what he said ("{words[:300]}") before you answered. '
            "Don't answer it or act on it. Anything you had started for it was stopped.]"
        )
        if self.transcript:
            self.transcript.cancel_last()
        logger.info("The user cancelled their turn before HQ answered")
        return True

    # -- H38: Cancel tapped after she started answering ----------------------

    CANCEL_LINE = "Cancel last message"

    def late_cancel_target(self) -> dict | None:
        """The turn a late Cancel takes back: his last turn, if it wasn't cancelled already and
        wasn't itself a Cancel-button line. None when there is nothing to take back."""
        his = [t for t in self.turns if not t.get("hi")]  # H130: her hi when she joined isn't his turn
        if not his:
            return None
        turn = his[-1]
        if turn.get("cancelled") or turn.get("button"):
            return None
        return turn

    def request_late_cancel(self) -> str | None:
        """H38: mark his last turn as taken back. Returns the line to send as his next turn (the
        caller sends it, typed, which also stops her if she's still talking), or None."""
        turn = self.late_cancel_target()
        if turn is None:
            return None
        turn["cancelled"] = True
        words = " ".join(turn["words"].split())
        self._late_cancel = self.CANCEL_LINE
        self._cancel_note = (
            f'[Call system: {config.USER} tapped the Cancel button on the call page after you had started answering. '
            f'He takes back what he said before ("{words[:300]}"). Stop: don\'t answer it any further and '
            "don't act on it. Anything you had started for it was stopped. Reply with only a very short okay, "
            "a few words at the most.]"
        )
        if self.transcript:
            self.transcript.cancel_last()
        logger.info("The user cancelled their last turn after HQ had started answering (Cancel button)")
        return self.CANCEL_LINE

    # -- lifecycle -----------------------------------------------------------

    async def start(self, frame: StartFrame):
        await super().start(frame)
        await self.brain.start()  # usually already open (bot.py starts it early)

    async def stop(self, frame: EndFrame):
        await super().stop(frame)
        if self._stop_brain_on_end:
            await self.brain.stop()

    async def cancel(self, frame: CancelFrame):
        await super().cancel(frame)
        if self._stop_brain_on_end:
            await self.brain.stop()

    # -- frames --------------------------------------------------------------

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        if isinstance(frame, InterruptionFrame):
            logger.debug(f"Interruption reached the Claude service (replying={self._replying}, cancel_asked={self._cancel_asked})")
        if isinstance(frame, InterruptionFrame):
            self._drop_hangup("he cut in")  # H75: he said more, so the call goes on
        if isinstance(frame, InterruptionFrame) and self._cancel_asked:
            pass  # H31: his Cancel, not a cut-in: nothing to tell Claude about what he heard
        elif isinstance(frame, InterruptionFrame) and self._replying and self.turns:
            # Checked before super(), which cancels the running reply.
            self._cut_off = True
            self._cut_reply = self.turns[-1]["reply"]
            self._worked_on = bool(self.turns[-1]["tools"]) or not self._cut_reply
        elif isinstance(frame, InterruptionFrame) and self._bot_speaking:
            self._cut_off = True  # the reply was written, but he talked over its audio
            self._cut_reply = self.turns[-1]["reply"] if self.turns else ""
            self._worked_on = False
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMContextFrame):
            await self._process_context(frame.context)
            return
        if isinstance(frame, JoinedHiFrame):
            await self._say_hi(frame.agent)
            return

        if isinstance(frame, InterruptionFrame):
            # In case a reply is still being drained or was mid-flight outside our task.
            self.brain.cancel_turn()
        elif isinstance(frame, BotStartedSpeakingFrame):
            self._bot_speaking = True
            self._spoke_at = time.perf_counter()
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._bot_speaking = False
            self._quiet_at = time.perf_counter()

        await self.push_frame(frame, direction)

    async def _process_context(self, context: LLMContext):
        words, notes, cut_in = self._new_user_text(context)
        if not words:
            if self.hear_whole is not None:
                await self.hear_whole(use=False)  # nothing to answer: the kept pieces go
            logger.debug("No new words from the user in this turn; not answering")
            return
        self._drop_hangup("he said more")
        button = bool(self._late_cancel) and self._late_cancel in words
        if button:
            self._late_cancel = None
        typed = any(t in words for t in self._typed)
        if typed:
            self._typed.clear()
        if self.hear_whole is not None:  # H165: his whole turn heard again; typed lines stay as typed
            whole = await self.hear_whole(use=not (typed or button))
            if whole:
                words = whole
        if button:
            typed = False  # the Cancel button's own line, marked as such instead
        elif typed:
            notes.append(f"[{config.USER} typed this in the chat on the call page instead of saying it. "
                         "Answer out loud as usual.]")
        if self._cancel_note:
            notes.insert(0, self._cancel_note)
            self._cancel_note = ""
        if self.transcript:
            self.transcript.user(words, cut_in=cut_in, typed=typed, button=button)
        if self.policy and self.policy.has_pending():
            yes, questions = self.policy.answer(words)
            asked = " ".join(questions)
            if yes:
                notes.append(
                    f"[Call system: {config.USER} said yes to your question ({asked}). Approved once: "
                    "make exactly the same call again now.]"
                )
            elif yes is None:
                # Fable clean-up (27 October 2026): his words were neither a yes nor a no (a question back, a condition,
                # another subject), so the question stays open instead of being dropped as a no.
                notes.append(
                    f"[Call system: {config.USER} hasn't answered your question yet ({asked}): what he just said is "
                    "neither a yes nor a no to it. Answer what he said. If the question still matters, ask it again in "
                    "one short sentence; it stays open, and his next clear yes approves it.]"
                )
            else:
                notes.append(
                    f"[Call system: {config.USER} did not give a clear yes to your question ({asked}), "
                    "so it is not approved and must not be done. Don't retry it unless he asks again; "
                    "just respond to what he said.]"
                )
            if self.transcript:
                self.transcript.note((f"{config.USER} said yes to: " if yes else "not answered yet: " if yes is None
                                      else "not approved: ") + asked)
        if self.before_turn is not None:
            try:
                notes = list(await self.before_turn(words)) + notes
            except Exception as e:
                logger.error(f"H79: picking who answers failed: {e!r}")
        await self._answer("\n".join(notes + [words]), words, button=button)

    # -- H130: whoever is brought in says hi -------------------------------------

    async def _say_hi(self, other: str) -> None:
        """Her own first line once she's on the call, before he says anything more: a turn without his words."""
        if self.joined_hi is None:
            return
        try:
            notes = list(await self.joined_hi(other))
        except Exception as e:
            logger.error(f"H130: getting her ready to say hi failed: {e!r}")
            return
        if notes:
            logger.info(f"H130: {other} says hi now she's on the call")
            await self._answer("\n".join(notes), "", hi=True)

    async def _queue_hi(self, other: str) -> None:
        await self.queue_frame(JoinedHiFrame(other))

    async def _answer(self, text: str, words: str, *, button: bool = False, hi: bool = False) -> None:
        """One reply from the Claude session to text, spoken and written as it streams in."""
        turn = {
            "sent": text, "words": words, "reply": "", "first_text_s": None, "interrupted": False,
            "tools": [], "fillers": [], "t0": time.perf_counter(), "button": button, "hi": hi,
        }
        self.turns.append(turn)
        t0 = turn["t0"]
        self._replying = True
        self._cancel_asked = False
        if not button and not hi:
            self._tell_cancellable(True)  # H38: the Cancel button's own line isn't offered for cancelling
        reply = self.brain.ask(text)
        watch = self.create_task(self._watch_for_fillers(turn), "filler-watch") if self.fillers else None
        # H75: her hang-up mark is never spoken; H79: nor the marks that bring in another agent
        mark = Marks([config.HANGUP_MARK, config.CALLBACK_MARK, *self.switch_marks])  # H238: nor the call-back one
        speech = SpeechFilter()  # H82: bold and list marks are for the chat, never spoken
        try:
            await self.push_frame(LLMFullResponseStartFrame())
            await self.start_processing_metrics()
            await self.start_ttfb_metrics()
            await self._stream(reply, turn, t0, mark, speech)
            if self._ended_silent(turn):
                # Fable clean-up (27 October 2026): a turn that ends without a word to him (every tool done, nothing said;
                # a step refused or asking for his yes and no question put to him) is asked once more, in the same
                # turn, so he never sits in silence with the thinking sound gone. His words, 16:11: "I had to ask you
                # two three times, 'What is your response?' because there is no response."
                logger.warning("The turn ended without a word to him; asking once more")
                if self.transcript:
                    self.transcript.note("her turn ended without a word to him; asked once more")
                turn["nudged"] = True
                await reply.aclose()
                pending = " ".join(q for _, _, q in self.policy.pending) if self.policy else ""
                reply = self.brain.ask(self.SILENT_NUDGE.format(
                    user=config.USER,
                    asked=f" You still have a question for him that needs his yes ({pending}): ask it now, in words."
                    if pending else ""))
                mark, speech = Marks([config.HANGUP_MARK, config.CALLBACK_MARK, *self.switch_marks]), SpeechFilter()
                await self._stream(reply, turn, t0, mark, speech)
            asked = [self.switch_marks[m] for m in self.switch_marks if mark.found(m)]
            if mark.found(config.CALLBACK_MARK) and not mark.found(config.HANGUP_MARK):
                # H238: he asked her to hang up and call him right back
                turn["callback"] = True
                if self.on_callback is not None and not turn.get("cancelled"):
                    logger.info("H238: she calls him right back once her line has been heard")
                    self._hangup_task = asyncio.create_task(
                        self._hang_up_after_goodbye(t0, then=self.on_callback), name="callback")
            elif mark.found(config.HANGUP_MARK):
                turn["hangup"] = True
                if self.on_hangup is not None and not turn.get("cancelled"):
                    logger.info("H75: she said goodbye and hangs up once it has been heard")
                    self._hangup_task = asyncio.create_task(self._hang_up_after_goodbye(t0), name="hangup")
            elif asked and not turn.get("cancelled"):
                kind, other = asked[-1]
                turn[kind.replace("-", "_")] = other
                if kind == "switch" and self.on_switch is not None:
                    logger.info(f"H79: she hands over to {other} once her line has been heard")
                    self._hangup_task = asyncio.create_task(
                        self._hang_up_after_goodbye(t0, then=lambda: self.on_switch(other)), name="switch")
                elif kind == "three-way" and self.on_three_way is not None:
                    logger.info(f"H79: {other} joins, a three-way call")
                    await self.on_three_way(other)
                    if self.joined_hi is not None:
                        # H130: once the line bringing her in has been heard, she says hi; he speaking first drops it
                        self._hangup_task = asyncio.create_task(
                            self._hang_up_after_goodbye(t0, then=lambda: self._queue_hi(other)), name="hi")
        except asyncio.CancelledError:
            turn["interrupted"] = True
            if not turn.get("cancelled"):
                logger.info("The user cut in: stopping Claude's reply")
            raise
        except Exception as e:
            self._sent_upto, self._sent_last = 0, ""  # F33: never answered, so his words go again
            await self.push_error(error_msg=f"Claude session error: {e}", exception=e)
        finally:
            self._replying = False
            self._tell_cancellable(False)
            if turn.get("cancelled"):
                self._cancel_asked = False
            if watch:
                await self.cancel_task(watch)
            # Closing the generator interrupts the CLI if the reply wasn't finished.
            await reply.aclose()
            if self.policy:
                self.policy.end_of_turn()
            if self.transcript and not (turn.get("cancelled") and not turn["reply"].strip()):
                self.transcript.reply(turn["reply"], cut_off=turn["interrupted"])
            await self.stop_processing_metrics()
            await self.push_frame(LLMFullResponseEndFrame())

    SILENT_NUDGE = ("[Call system: your turn ended without a single word to {user}. He heard nothing, and the thinking "
                    "sound stopped. Say now, in one or two short spoken sentences, what you did or found and what comes "
                    "next; if a step was refused, say so plainly.{asked} Never end a turn without a word to him.]")

    async def _stream(self, reply, turn: dict, t0: float, mark: "Marks", speech: "SpeechFilter") -> None:
        """One reply from the brain into the turn: spoken as it streams in, written for the chat, the marks taken out."""
        open_text = False  # text pushed since the last response start (for flushing at a tool)
        async for piece in reply:
            if isinstance(piece, ToolStarted):
                turn["tools"].append((time.perf_counter() - t0, piece.name))
                turn["tool_pending"] = True
                turn["tool_kind"] = config.tool_kind(piece.name)
                if open_text:
                    # Say what came before the tool now, instead of holding the last
                    # sentence until the tool is done (the voice waits for more text
                    # to be sure a sentence ended).
                    await self.push_frame(LLMFullResponseEndFrame())
                    await self.push_frame(LLMFullResponseStartFrame())
                    open_text = False
                continue
            piece = mark.feed(piece)
            if not piece:
                continue
            if turn["first_text_s"] is None:
                turn["first_text_s"] = time.perf_counter() - t0
                await self.stop_ttfb_metrics()
            if piece.strip():
                self._tell_cancellable(False)  # H31: she has started answering
            if turn["reply"] and not turn["reply"][-1].isspace() and piece and not piece[0].isspace() and turn.get("tool_pending") is not None:
                piece = " " + piece  # a new message after a tool: keep the words apart
            turn["reply"] += piece
            turn["tool_pending"] = None
            turn["last_text"] = time.perf_counter()
            if piece.strip():
                open_text = True
            said = speech.feed(piece)
            if said:
                await self._push_llm_text(said)
        tail = mark.flush()
        if tail:
            turn["reply"] += tail
        said = speech.feed(tail) + speech.flush()
        if said:
            await self._push_llm_text(said)

    def _ended_silent(self, turn: dict) -> bool:
        """The reply came to its end (a result, not a cut-in, not a dead line) and she said nothing at all."""
        if turn["reply"].strip() or turn.get("cancelled") or turn.get("hi") or turn.get("nudged"):
            return False
        last = self.brain.last_turn
        if last is None or last.total_s is None or last.interrupted or last.is_error:
            return False
        return True

    # -- H75: she hangs up after his goodbye -------------------------------------

    HANGUP_QUIET_SECS = 1.0  # her voice quiet this long after the goodbye: it has been heard
    HANGUP_NO_VOICE_SECS = 4.0  # no voice at all after the reply (voice off, nothing said): hang up anyway
    HANGUP_MAX_SECS = 25.0  # never wait longer than this

    def _drop_hangup(self, why: str) -> None:
        task, self._hangup_task = self._hangup_task, None
        if task is not None and not task.done():
            task.cancel()
            logger.info(f"H75: not {'saying hi' if task.get_name() == 'hi' else 'hanging up'} after all: {why}")

    async def _hang_up_after_goodbye(self, t0: float, then=None) -> None:
        """Waits until her goodbye has been spoken (her voice started after his turn and has been
        quiet for a moment), then calls on_hangup. Cancelled when he says anything more."""
        try:
            done_at = time.perf_counter()
            while True:
                await asyncio.sleep(0.1)
                now = time.perf_counter()
                if now - done_at > self.HANGUP_MAX_SECS:
                    break
                spoke = self._spoke_at > t0
                if not spoke and now - done_at > self.HANGUP_NO_VOICE_SECS:
                    break
                if spoke and not self._bot_speaking and self._quiet_at > self._spoke_at \
                        and now - self._quiet_at >= self.HANGUP_QUIET_SECS:
                    break
            self._hangup_task = None
            await (then() if then else self.on_hangup())
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"H75: hanging up failed: {e!r}")

    async def _watch_for_fillers(self, turn: dict):
        """At most one filler per wait: while Claude is quiet after the user's turn, and
        while a tool runs after HQ went quiet. Ends with the reply."""
        armed = True
        t0 = turn["t0"]
        last_text_seen = None
        while True:
            await asyncio.sleep(0.05)
            now = time.perf_counter()
            if turn.get("last_text") != last_text_seen:
                last_text_seen = turn.get("last_text")
                armed = True  # HQ said something: the next wait may get a filler
            if not armed:
                continue
            kind = None
            if turn["first_text_s"] is None and not turn["tools"]:
                if now - t0 >= config.FILLER_AFTER_SECS:
                    kind = "wait"
            elif turn.get("tool_pending"):
                since = turn.get("last_text") or t0
                if self.fillers.silent_for(since) >= config.TOOL_FILLER_SILENCE_SECS:
                    kind = turn.get("tool_kind") or "tool"
                elif turn["first_text_s"] is None and now - t0 >= config.FILLER_AFTER_SECS:
                    kind = turn.get("tool_kind") or "wait"  # straight to a tool, nothing said yet
            if kind:
                said = await self.fillers.say(kind)
                if said:
                    turn["fillers"].append((time.perf_counter() - t0, said))
                    armed = False

    def _new_user_text(self, context: LLMContext) -> tuple[str, list[str], bool]:
        """The user's words since the last reply; call-system notes if he cut that reply
        off; and whether he did."""
        messages = context.get_messages()
        start = len(messages)
        last_assistant = None
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if not isinstance(msg, dict):
                break
            role = msg.get("role")
            if role == "user":
                start = i
            else:
                if role == "assistant":
                    last_assistant = _content_text(msg.get("content"))
                break
        # F33: if her reply was stopped before he heard any of it (or was written but not yet spoken),
        # the context keeps his earlier line next to the new one; Claude already has the earlier one,
        # so only what came after it goes (counted by message, so a line he sends twice still goes).
        upto = self._sent_upto
        if (start < upto <= len(messages) and isinstance(messages[upto - 1], dict)
                and _content_text(messages[upto - 1].get("content")) == self._sent_last):
            start = upto
        user_parts = [_content_text(m.get("content")) for m in messages[start:]]
        text = " ".join(p.strip() for p in user_parts if p and p.strip())
        if messages and isinstance(messages[-1], dict):
            self._sent_upto, self._sent_last = len(messages), _content_text(messages[-1].get("content"))
        notes: list[str] = []
        cut_in = False
        if text and self._cut_off:
            cut_in = True
            heard = (last_assistant or "").strip()
            # Pipecat's context only has what was spoken; make sure it's from this reply.
            if heard and self._cut_reply and _norm(heard)[:40] not in _norm(self._cut_reply):
                heard = ""
            if heard:
                notes.append(f'[{config.USER} cut in while you were talking. He heard you say: "{heard}"]')
            elif self._worked_on:
                notes.append(
                    f"[{config.USER} spoke while you were still working on your last reply, so it was stopped. "
                    "Anything you had started may not have finished.]"
                )
            else:
                notes.append(f"[{config.USER} cut in before he heard any of your reply.]")
        if text:
            self._cut_off = False
            self._cut_reply = ""
            self._worked_on = False
        return text, notes, cut_in


class MarkFilter:
    """H75: takes a marker out of streamed text, also when it comes in pieces. feed() returns what
    may be spoken now (a possible start of the marker is held back); flush() what was held at the
    end; found says whether the marker came (its case doesn't matter)."""

    def __init__(self, marker: str):
        self.m = marker.lower()
        self.buf = ""
        self.found = False

    def feed(self, piece: str) -> str:
        s, self.buf = self.buf + piece, ""
        out = ""
        while True:
            i = s.lower().find(self.m)
            if i < 0:
                break
            out += s[:i]
            s = s[i + len(self.m):]
            self.found = True
        low = s.lower()
        for k in range(min(len(s), len(self.m) - 1), 0, -1):
            if self.m.startswith(low[-k:]):
                self.buf, s = s[-k:], s[:-k]
                break
        return out + s

    def flush(self) -> str:
        b, self.buf = self.buf, ""
        return b



class Marks:
    """H79: several markers taken out of the same streamed text (a MarkFilter for each, one after the other);
    found(marker) says whether that one came."""

    def __init__(self, markers):
        self.filters = [MarkFilter(m) for m in markers]

    def feed(self, piece: str) -> str:
        for f in self.filters:
            piece = f.feed(piece)
        return piece

    def flush(self) -> str:
        out = ""
        for f in self.filters:
            out = f.feed(out) + f.flush()
        return out

    def found(self, marker: str) -> bool:
        return any(f.found for f in self.filters if f.m == marker.lower())


class SpeechFilter:
    """H82: her text may have bold and short lists, for the chat on the call page; the voice gets it
    without the marks. Asterisks and backticks are dropped; a list or heading mark at the start of a
    line ("- ", "* ", "1. ", "## ") is dropped, also when it streams in pieces (a possible start of one
    is held back); a line break becomes a sentence end when the line didn't end in one, so each list
    item is said as its own phrase. H108: a colon between digits (5:30) becomes a space, so the voice
    doesn't pause in a time. H170: a web address is never said ("https://…", "www.…"), and of a link
    written [words](https://…) only the words are; a word that could still become one is held back until
    it ends. feed() returns what may be spoken now; flush() what was held."""

    _MARK = re.compile(r"[ \t]*(?:[-*+\u2022]|\d{1,3}[.)]|#{1,6})[ \t]+")
    _MAYBE = re.compile(r"[ \t]*(?:[-*+\u2022]|\d{1,3}[.)]?|#{1,6})?")
    _ENDS = ".!?:;,"

    _URL = r"(?:https?://|\bwww\.)[^\s<>\"]*[^\s<>\".,;:!?)\]'*]"
    _LINK = re.compile(r"\]\((?:https?://)[^\s)]*\)|\(?" + _URL + r"\)?", re.I)
    _OPEN = ("https://", "http://", "www.")

    def __init__(self):
        self.buf = ""
        self.word = ""  # H170: the end of the text so far, held while it could still be a link
        self.line_start = True
        self.last = ""  # the last character spoken that wasn't a space

    def _unlinked(self, piece: str, end: bool = False) -> str:
        """H170: the text without its web addresses. The last word is held back while it could still
        become one (or the end of a [words](…) link), and let go at the next space or at the end."""
        s, self.word = self.word + piece, ""
        if not end:
            cut = max(s.rfind(c) for c in " \t\n")
            tail = s[cut + 1:]
            bare = tail.lstrip("([<*\"'").lower()
            if tail and ("[" in tail or "]" in tail or bare.startswith(self._OPEN)
                         or any(o.startswith(bare) for o in self._OPEN)):
                s, self.word = s[:cut + 1], tail
        s = self._LINK.sub("", s)
        return s.replace("[", "").replace("]", "")

    def feed(self, piece: str) -> str:
        return self._marks(self._unlinked(piece))

    def _marks(self, piece: str) -> str:
        s, self.buf = self.buf + piece, ""
        out = []
        i = 0
        while i < len(s):
            if self.line_start:
                rest = s[i:]
                m = self._MARK.match(rest)
                if m:
                    i += m.end()
                    self.line_start = False
                    continue
                if self._MAYBE.fullmatch(rest):
                    self.buf = rest  # could still become a mark: wait for the next piece
                    break
                self.line_start = False
            ch = s[i]
            i += 1
            if ch == "\n":
                if self.last and self.last not in self._ENDS:
                    out.append(".")
                    self.last = "."
                out.append(" ")
                self.line_start = True
            elif ch in "*`":
                continue
            elif ch == ":" and self.last.isdigit():
                # H108: a time's colon (5:30) makes Kokoro pause; said as "5 30". At a piece's end it
                # waits for the next piece to see whether a digit follows.
                if i == len(s):
                    self.buf = ":"
                    break
                out.append(" " if s[i].isdigit() else ":")
                if not s[i].isdigit():
                    self.last = ":"
            else:
                out.append(ch)
                if not ch.isspace():
                    self.last = ch
        return "".join(out)

    def flush(self) -> str:
        rest = self._unlinked("", end=True)
        b = (self._marks(rest) if rest else "") + self.buf
        self.buf = ""
        self.line_start = True
        self.last = ""
        return b.replace("*", "").replace("`", "")


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", "", s.lower()).split())


def _content_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""
