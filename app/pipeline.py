"""The call pipeline, shared by the live call (bot.py) and the headless test (test_turn.py).

    mic in → Silero VAD + smart-turn (in the user aggregator) → Whisper (MLX)
           → user aggregator → Claude session → Kokoro → fillers → audio out
           → assistant aggregator
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any, cast

import numpy as np
from loguru import logger

from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    DataFrame,
    ErrorFrame,
    Frame,
    TranscriptionFrame,
    UninterruptibleFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.services.whisper.stt import WhisperSTTService, WhisperSTTServiceMLX
from pipecat.transcriptions.language import Language
from pipecat.turns.user_stop.turn_analyzer_user_turn_stop_strategy import (
    TurnAnalyzerUserTurnStopStrategy,
)
from pipecat.turns.user_turn_strategies import UserTurnStrategies
from pipecat.utils.text.base_text_aggregator import Aggregation, AggregationType
from pipecat.utils.text.simple_text_aggregator import SimpleTextAggregator
from pipecat.utils.time import time_now_iso8601

import config
import quick_context
from brain import ClaudeBrain, call_session_options
from call_state import StateTap
from claude_llm import ClaudeSessionLLMService
from policy import Policy


class SegmentDoneFrame(DataFrame, UninterruptibleFrame):
    """H11: Whisper has finished one piece of speech (with or without words). It follows that
    piece's TranscriptionFrame down the pipeline, so when the turn logic sees it, the words
    are already in the turn."""


class DropSegmentDone(FrameProcessor):
    """Right after the turn logic: SegmentDoneFrame has done its job there, so it doesn't
    travel on to Claude and the voice."""

    async def process_frame(self, frame: Frame, direction):
        await super().process_frame(frame, direction)
        if not isinstance(frame, SegmentDoneFrame):
            await self.push_frame(frame, direction)


class HQWhisperSTT(WhisperSTTServiceMLX):
    """Pipecat's MLX Whisper, plus a word list (initial prompt) and a warm-up.

    The run_stt body follows WhisperSTTServiceMLX.run_stt in pipecat 1.12.0; the changes are
    the initial_prompt, so names come out right, and a SegmentDoneFrame after
    every piece (H11).
    """

    def __init__(self, *, initial_prompt: str | None = None, quiet: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._initial_prompt = initial_prompt or None
        self._quiet = quiet  # H7, free mode: what was said stays out of the server log

    def warm_up(self) -> float:
        """Load the model and run it once (blocking), so the first turn isn't slow."""
        import mlx_whisper

        t = time.perf_counter()
        silence = np.zeros(16000, dtype=np.float32)
        mlx_whisper.transcribe(silence, path_or_hf_repo=self._settings.model, language="en")
        return time.perf_counter() - t

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        try:
            import mlx_whisper

            await self.start_processing_metrics()
            audio_float = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            language = cast("Language | None", self._settings.language)
            chunk = await asyncio.to_thread(
                mlx_whisper.transcribe,
                audio_float,
                path_or_hf_repo=self._settings.model,
                temperature=self._settings.temperature,
                language=language,
                initial_prompt=self._initial_prompt,
            )
            text = ""
            threshold = self._settings.no_speech_prob
            for segment in cast("list[dict[str, Any]]", chunk.get("segments", [])):
                if segment.get("compression_ratio", None) == 0.5555555555555556:
                    continue  # likely hallucination
                if threshold is not None and segment.get("no_speech_prob", 0.0) < threshold:
                    text += f"{segment.get('text', '')} "
            await self.stop_processing_metrics()
            text = text.strip()
            if text:
                if not self._quiet:
                    logger.debug(f"Transcription: [{text}]")
                yield TranscriptionFrame(text, self._user_id, time_now_iso8601(), language)
        except Exception as e:
            yield ErrorFrame(error=f"Whisper error: {e}")
        yield SegmentDoneFrame()

    async def _handle_user_stopped_speaking(self, frame):
        await super()._handle_user_stopped_speaking(frame)
        if not self.is_usable:  # no piece was queued, so none will be finished: say so now
            await self.push_frame(SegmentDoneFrame())


class HQFasterWhisperSTT(WhisperSTTService):
    """H55 (12 October 2026): the same as HQWhisperSTT, off a Mac (no MLX): faster-whisper on the
    CPU, int8, one beam, as timed on the VPS. The run_stt body follows WhisperSTTService.run_stt
    in pipecat 1.12.0; the changes are the beam, the initial prompt and the SegmentDoneFrame."""

    # One model for every call, and one transcription at a time: a model per call, loaded again
    # at every call, left the second call on the VPS stuck in its first transcription.
    _MODELS: dict[str, Any] = {}
    _LOCK = __import__("threading").Lock()

    def __init__(self, *, initial_prompt: str | None = None, quiet: bool = False, **kwargs):
        super().__init__(device="cpu", compute_type="int8", **kwargs)
        self._initial_prompt = initial_prompt or None
        self._quiet = quiet

    def _load(self):
        from faster_whisper import WhisperModel

        name = str(self._settings.model)
        with self._LOCK:
            if name not in self._MODELS:
                self._MODELS[name] = WhisperModel(name, device="cpu", compute_type="int8",
                                                  cpu_threads=__import__("os").cpu_count() or 4)
            self._model = self._MODELS[name]

    def warm_up(self) -> float:
        t = time.perf_counter()
        if self._model is not None:
            with self._LOCK:
                list(self._model.transcribe(np.zeros(16000, dtype=np.float32), language="en", beam_size=1)[0])
        return time.perf_counter() - t

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        try:
            if not self._model:
                raise RuntimeError("Whisper model not available")
            await self.start_processing_metrics()
            audio_float = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            language = cast("Language | None", self._settings.language)

            def transcribe():
                with self._LOCK:
                    segments, _ = self._model.transcribe(audio_float, language=language, beam_size=1,
                                                         initial_prompt=self._initial_prompt)
                    return list(segments)

            segments = await asyncio.to_thread(transcribe)
            text = ""
            threshold = self._settings.no_speech_prob
            for segment in segments:
                if threshold is None or segment.no_speech_prob < threshold:
                    text += f"{segment.text} "
            await self.stop_processing_metrics()
            text = text.strip()
            if text:
                if not self._quiet:
                    logger.debug(f"Transcription: [{text}]")
                yield TranscriptionFrame(text, self._user_id, time_now_iso8601(), language)
        except Exception as e:
            yield ErrorFrame(error=f"Whisper error: {e}")
        yield SegmentDoneFrame()

    async def _handle_user_stopped_speaking(self, frame):
        await super()._handle_user_stopped_speaking(frame)
        if not self.is_usable:
            await self.push_frame(SegmentDoneFrame())


def make_stt(quiet: bool = False) -> HQWhisperSTT | HQFasterWhisperSTT:
    if config.STT_ENGINE == "faster":  # H55: off a Mac
        return HQFasterWhisperSTT(
            initial_prompt=config.WHISPER_PROMPT,
            quiet=quiet,
            ttfs_p99_latency=config.WHISPER_P99_SECS,
            settings=WhisperSTTService.Settings(model=config.WHISPER_MODEL, language=Language.EN),
        )
    return HQWhisperSTT(
        initial_prompt=config.WHISPER_PROMPT,
        quiet=quiet,
        ttfs_p99_latency=config.WHISPER_P99_SECS,
        settings=WhisperSTTServiceMLX.Settings(model=config.WHISPER_MODEL, language=Language.EN),
    )


def make_tts(voice: str | None = None) -> KokoroTTSService:
    voice = voice or config.VOICE
    british = config.voice_lang(voice) == "en-gb"
    tts = KokoroTTSService(
        model_path=str(config.KOKORO_MODEL),
        voices_path=str(config.KOKORO_VOICES),
        settings=KokoroTTSService.Settings(voice=voice, language=Language.EN_GB if british else Language.EN),
        stop_frame_timeout_s=config.TTS_STALL_SECS,
    )
    # TTSService has no argument for its text aggregator in 1.12.0; swap it in place.
    old = tts._text_aggregator
    # Whole sentences sound right; cutting at every comma made Kokoro speak each piece as if
    # it were a sentence of its own, so the tone dropped mid-sentence (9 October 2026:
    # "the intonation ... they are very wrong in all sentences"). Only a long first sentence
    # is still cut once at a comma, so the first words don't wait too long.
    tts._text_aggregator = ClauseTextAggregator(
        aggregation_type=old._aggregation_type, language=old.language,
        min_words=10**6, min_words_first=config.FIRST_CLAUSE_MIN_WORDS,
    )
    return tts


def warm_up_tts(tts: KokoroTTSService) -> float:
    """Run Kokoro once (blocking) so its first sentence in the call is quick."""
    t = time.perf_counter()
    voice = tts._settings.voice or config.VOICE
    tts._kokoro.create("Hello.", voice=voice, speed=1.0, lang=config.voice_lang(voice))
    return time.perf_counter() - t


def make_brain(model: str | None = None, policy: Policy | None = None, cwd=None,
               free: bool = False, load: str = "deep", persona: str = "") -> ClaudeBrain:
    """With a policy: the full Claude of the user's workspace (A3). Without one, or
    with HQ_PLAIN=1: the plain Claude of A2, working in cwd (default: scratch).
    free=True (H7, H8): the plain Claude plus web search and fetching pages, nothing else.
    load (B1): "deep" loads the folder like a chat; "quick" only the lighter part (quick_context.py).
    persona (H29): the agent's own text (agents.persona), added after the call rules."""
    model = model or config.MODEL
    options = None
    if policy is not None and not config.PLAIN:
        options = call_session_options(
            model=model,
            folder=config.FOLDER,
            voice_rules=config.VOICE_RULES + persona,
            policy=policy,
            cli_path=config.CLAUDE_CLI,
            effort=config.effort_for(model),
            quick_context=quick_context.build(config.FOLDER) if load == "quick" else None,
        )
    return ClaudeBrain(
        model=model,
        system_prompt=config.SYSTEM_PROMPT + (config.FREE_RULES if free else "") + persona,
        cwd=cwd or config.SCRATCH,
        cli_path=config.CLAUDE_CLI,
        effort=config.effort_for(model),
        options=options,
        tools=config.FREE_TOOLS if free else None,
    )


class PushToTalk:
    """H9: while the talk button is held on the call page, the turn stays his, however long
    he pauses. The page sends {"type": "ptt", "held": true/false}; bot.py calls set_held.

    Holding: the stop strategy below never ends the turn, and the aggregator's 5-second
    stop watchdog is kept from firing. Letting go: the turn ends as soon as there are words
    and the voice has stopped (the page mutes the mic on letting go), without waiting for
    smart-turn to agree the sentence sounds finished."""

    KEEPALIVE_SECS = 2.0

    def __init__(self) -> None:
        self.held = False
        self.strategy: HoldableTurnStopStrategy | None = None
        self.user_aggregator: Any = None
        self.call_state: Any = None  # H11/H12: the page is told about transcribing and waiting
        self._keepalive: asyncio.Task | None = None

    def show(self, kind: str | None) -> None:
        """H11/H12: "transcribing" (let go, the last words are still being turned into text),
        "waiting" (a pause in free talking, she may still take the turn) or None (he talks)."""
        if self.call_state is not None:
            try:
                self.call_state.turn_wait(kind)
            except Exception:
                pass

    def _poke_watchdog(self) -> None:
        # The watchdog ends a turn after 5 s with no voice events. Private in pipecat 1.12.0.
        controller = getattr(self.user_aggregator, "_user_turn_controller", None)
        event = getattr(controller, "_user_turn_stop_timeout_event", None)
        if event is not None:
            event.set()

    async def _keep_alive(self) -> None:
        while self.held:
            self._poke_watchdog()
            await asyncio.sleep(self.KEEPALIVE_SECS)

    async def set_held(self, held: bool) -> None:
        held = bool(held)
        if held == self.held:
            return
        self.held = held
        logger.info("Push to talk: held" if held else "Push to talk: let go")
        if held:
            if self.strategy:
                self.strategy.released = False
            self._poke_watchdog()
            if self._keepalive is None or self._keepalive.done():
                self._keepalive = asyncio.create_task(self._keep_alive())
        else:
            self._poke_watchdog()
            if self.strategy:
                await self.strategy.on_released()

    def stop(self) -> None:
        self.held = False
        if self._keepalive and not self._keepalive.done():
            self._keepalive.cancel()


class HoldableTurnStopStrategy(TurnAnalyzerUserTurnStopStrategy):
    """Smart-turn as before, with three changes. Leans on the private
    _maybe_trigger_user_turn_stopped, _text, _vad_user_speaking and _timeout_task of
    pipecat 1.12.0.

    H9: while the talk button is held, the turn never ends.
    H11: a turn never ends while Whisper is still on a piece of speech. Every pause the VAD
    hears sends one piece to Whisper, and Whisper answers each piece with a SegmentDoneFrame
    that arrives here after its words; until the count matches, the last words aren't in the
    turn yet. (Before, letting go ended the turn on the words from before the last pause.)
    H12: in free talking, once the turn looks finished, she waits TURN_GRACE_SECS more; if
    he goes on talking, the turn stays his."""

    def __init__(self, ptt: PushToTalk, grace_secs: float | None = None, **kwargs):
        super().__init__(**kwargs)
        self._ptt = ptt
        ptt.strategy = self
        self.released = False  # let go during a turn: end it at the first chance
        self._in_turn = False
        self._grace = config.TURN_GRACE_SECS if grace_secs is None else grace_secs
        self._grace_task: asyncio.Task | None = None
        self._safety_task: asyncio.Task | None = None
        self._pieces_sent = 0  # pauses the VAD heard: each sends one piece to Whisper
        self._pieces_done = 0  # SegmentDoneFrames back from Whisper
        self._piece_sent_at = 0.0

    # -- H11: is Whisper still on a piece? --

    def transcribing(self) -> bool:
        if self._pieces_done >= self._pieces_sent:
            return False
        if time.monotonic() - self._piece_sent_at > config.TRANSCRIBING_MAX_SECS:
            logger.warning("Turn: Whisper's answer for a piece never came; going on without it")
            self._pieces_done = self._pieces_sent
            return False
        return True

    async def process_frame(self, frame: Frame):
        if isinstance(frame, SegmentDoneFrame):
            self._pieces_done += 1
            if not self.transcribing():
                await self._maybe_trigger_user_turn_stopped()
        return await super().process_frame(frame)

    async def _handle_vad_user_stopped_speaking(self, frame):
        # Counted before smart-turn looks at it, so nothing can end the turn in between.
        self._pieces_sent += 1
        self._piece_sent_at = time.monotonic()
        if self._in_turn and not self._ptt.held:
            self._ptt.show("transcribing" if self.released else "waiting")
        await super()._handle_vad_user_stopped_speaking(frame)

    async def _handle_vad_user_started_speaking(self, frame):
        await self._cancel_grace()  # H12: he goes on talking, so the turn stays his
        if self._in_turn:
            self._ptt.show(None)
        await super()._handle_vad_user_started_speaking(frame)

    # -- turn boundaries --

    async def handle_user_turn_started(self):
        await super().handle_user_turn_started()
        self._in_turn = True

    async def handle_user_turn_stopped(self):
        await super().handle_user_turn_stopped()
        self._in_turn = False
        self.released = False
        await self._cancel_grace()
        await self._cancel_safety()

    async def on_released(self):
        self.released = self._in_turn
        if not self._in_turn:
            self._ptt.show(None)  # nothing was said: tell the page, so it doesn't stay yellow
            return
        await self._cancel_grace()
        self._ptt.show("transcribing")
        # If Whisper's answer never comes, look again once transcribing() gives up on it.
        await self._cancel_safety()
        self._safety_task = self.task_manager.create_task(
            self._look_again(config.TRANSCRIBING_MAX_SECS + 0.2), f"{self}::release_safety"
        )
        await self._maybe_trigger_user_turn_stopped()

    async def _look_again(self, secs: float):
        try:
            await asyncio.sleep(secs)
        except asyncio.CancelledError:
            return
        self._safety_task = None
        await self._maybe_trigger_user_turn_stopped()

    # -- ending the turn --

    async def trigger_user_turn_stopped(self, **kwargs):
        if self._ptt.held:
            return  # his turn while he holds the button
        if self.transcribing():
            return  # the SegmentDoneFrame brings us back here
        if not self.released and self._grace > 0:
            if self._grace_task is None:
                self._grace_task = self.task_manager.create_task(
                    self._end_after_grace(kwargs), f"{self}::grace"
                )
            return
        await self._cancel_grace()
        await super().trigger_user_turn_stopped(**kwargs)

    async def _end_after_grace(self, kwargs: dict):
        try:
            await asyncio.sleep(self._grace)
        except asyncio.CancelledError:
            return
        self._grace_task = None
        if self._ptt.held or self._vad_user_speaking or self.transcribing():
            return  # he started again (or is holding): not her turn yet
        await super().trigger_user_turn_stopped(**kwargs)

    async def _cancel_grace(self):
        if self._grace_task:
            task, self._grace_task = self._grace_task, None
            await self.task_manager.cancel_task(task)

    async def _cancel_safety(self):
        if self._safety_task:
            task, self._safety_task = self._safety_task, None
            await self.task_manager.cancel_task(task)

    async def _maybe_trigger_user_turn_stopped(self):
        if self._ptt.held:
            return
        if self.released and self._text and not self._vad_user_speaking:
            if self.transcribing():
                return  # the last words are still on their way
            if self._timeout_task:
                await self.task_manager.cancel_task(self._timeout_task)
                self._timeout_task = None
            await self.trigger_user_turn_stopped()
            return
        await super()._maybe_trigger_user_turn_stopped()


TYPED_MAX_CHARS = 2000  # H18: a typed message longer than this is cut


async def type_to_agent(worker, llm: ClaudeSessionLLMService, call_state, text: str) -> bool:
    """H18: The user typed a message in the chat on the call page instead of saying it. It goes
    into the turn like spoken words (an LLMMessagesAppendFrame through the user aggregator), so
    HQ answers it out loud as usual and both lines reach the chat log. If she was thinking
    or speaking, she is cut off first, as if he had talked over her. Returns False for an
    empty message."""
    from pipecat.frames.frames import InterruptionWorkerFrame, LLMMessagesAppendFrame
    from pipecat.processors.frame_processor import FrameDirection

    text = " ".join((text or "").split())[:TYPED_MAX_CHARS]
    if not text:
        return False
    busy = call_state is not None and call_state.state in ("thinking", "speaking")
    logger.info("The user typed a message" + (" (cutting in)" if busy else ""))
    if busy:
        await worker.queue_frame(InterruptionWorkerFrame(), FrameDirection.UPSTREAM)
        await asyncio.sleep(0.3)  # let the interruption go through before the new words
    llm.mark_typed(text)
    await worker.queue_frame(LLMMessagesAppendFrame(messages=[{"role": "user", "content": text}], run_llm=True))
    return True


async def cancel_turn(user_aggregator, llm: ClaudeSessionLLMService, call_state) -> bool:
    """H31: he tapped Cancel on the call page while she was thinking. What he just said (spoken
    or typed) is dropped: the reply is stopped before she says a word, the thinking circle and
    sound stop, the transcript marks his line as cancelled, and Claude is told with the next
    turn not to answer it. Returns False when there is nothing to cancel (she already started).

    The interruption goes out from the user aggregator, the same way as when he talks over her."""
    if not llm.request_cancel():
        logger.info("Cancel tapped, but there was nothing left to cancel")
        return False
    await user_aggregator.broadcast_interruption()
    if call_state is not None:
        call_state.cancelled()
    return True


async def late_cancel(worker, llm: ClaudeSessionLLMService, call_state, on_cancelled=None) -> bool:
    """H38: he tapped Cancel after she had started answering (or after she finished). His last
    turn is taken back: she stops talking, his line is marked cancelled, and a typed line "Cancel
    last message" goes in as his turn, marked as from the button; Claude is told with it to drop
    what he said before and not answer it. on_cancelled() runs before that line goes in, so the
    call page strikes through the right line. Returns False when there is nothing to take back."""
    line = llm.request_late_cancel()
    if line is None:
        logger.info("Cancel tapped late, but there was nothing left to take back")
        return False
    if on_cancelled is not None:
        on_cancelled()
    return await type_to_agent(worker, llm, call_state, line)


def build_pipeline(
    *,
    source: FrameProcessor,
    sink: FrameProcessor,
    stt: FrameProcessor,
    llm: ClaudeSessionLLMService,
    tts: FrameProcessor,
    fillers: FrameProcessor | None = None,
    taps: dict[str, FrameProcessor] | None = None,
    call_state=None,
    ptt: PushToTalk | None = None,
) -> tuple[Pipeline, LLMContextAggregatorPair]:
    """taps: optional pass-through processors for tests, at "after_stt", "after_llm",
    "after_tts". ptt: the push-to-talk state (H9); one is made when none is given."""
    taps = taps or {}
    ptt = ptt or PushToTalk()

    def tap(name: str) -> list[FrameProcessor]:
        return [taps[name]] if name in taps else []

    context = LLMContext()
    aggregators = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=config.VAD_STOP_SECS)),
            user_turn_strategies=UserTurnStrategies(
                stop=[HoldableTurnStopStrategy(ptt, turn_analyzer=LocalSmartTurnAnalyzerV3())]
            ),
            # A turn with no words (a cough while HQ talks) gets no reply.
            empty_user_turn=None,
        ),
    )
    ptt.user_aggregator = aggregators.user()
    ptt.call_state = call_state
    pipeline = Pipeline(
        [
            source,
            stt,
            *tap("after_stt"),
            aggregators.user(),
            DropSegmentDone(),
            *([StateTap(call_state)] if call_state else []),
            llm,
            *tap("after_llm"),
            tts,
            *tap("after_tts"),
            *([fillers] if fillers else []),
            *([StateTap(call_state)] if call_state else []),
            sink,
            aggregators.assistant(),
        ]
    )
    return pipeline, aggregators


class ClauseTextAggregator(SimpleTextAggregator):
    """Pipecat's sentence aggregator, plus an earlier cut at a comma, semicolon or colon
    once a sentence has a few words. Kokoro needs about a third of a second per second
    of speech, so a long first sentence held the voice back; a clause starts it sooner."""

    def __init__(self, *, min_words: int = 6, min_words_first: int = 3, **kwargs):
        super().__init__(**kwargs)
        self._min_words = min_words
        self._min_words_first = min_words_first  # the first piece of a reply: start sooner
        self._first = True

    async def reset(self):
        await super().reset()
        self._first = True

    async def flush(self):
        result = await super().flush()
        self._first = True  # the reply is over; the next text starts a new one
        return result

    async def handle_interruption(self):
        await super().handle_interruption()
        self._first = True

    async def aggregate(self, text: str):
        if self._aggregation_type == AggregationType.TOKEN:
            async for a in super().aggregate(text):
                yield a
            return
        for char in text:
            self._text += char
            result = await self._check_sentence_with_lookahead(char)
            if result:
                self._first = False
                yield result
                continue
            need = self._min_words_first if self._first else self._min_words
            if (
                char == " "
                and len(self._text) >= 2
                and self._text[-2] in ",;:"
                and len(self._text.split()) >= need
            ):
                self._first = False
                clause = self._text.strip(" ")
                self._text = ""
                self._lookahead_state = type(self._lookahead_state).IDLE
                yield Aggregation(text=clause, type=AggregationType.SENTENCE)
