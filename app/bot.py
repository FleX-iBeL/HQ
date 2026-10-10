"""Jarvis VA: a live voice call with Claude, at the desk.

Start it with app/start.sh, open http://127.0.0.1:7860 and press Connect.
Each browser connection is one call (call.py) with its own Claude session: since A3 the
full Claude of the user's workspace. After hang-up, also when the tab is just
closed, the same session writes things down, commits and pushes.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import brain  # noqa: F401  (clears the API key variables before anything else runs)
import agents
import config
from loguru import logger

from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.runner.types import RunnerArguments, SmallWebRTCRunnerArguments
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.workers.runner import WorkerRunner

from call import Call
from call_state import CallState
from pipeline import PushToTalk, build_pipeline, cancel_turn, late_cancel, type_to_jarvis


def keep_audio_in_the_tailnet() -> None:
    """The MacBook only offers its Tailscale addresses (100.x and fd7a:...) as places to send
    the call's audio to, not its Wi-Fi or public IPv6 addresses. With no outside STUN/TURN
    servers either, the audio can only travel through Tailscale. If the MacBook has no
    Tailscale address (Tailscale off), all addresses are offered, so the call still works
    at the desk. JARVIS_TAILNET_ONLY=0 turns this off."""
    import ipaddress

    import aioice.ice as ice

    if os.environ.get("JARVIS_TAILNET_ONLY", "1") == "0":
        return
    original = ice.get_host_addresses
    cgnat = ipaddress.ip_network("100.64.0.0/10")
    ula = ipaddress.ip_network("fd7a:115c:a1e0::/48")

    def tailnet_only(use_ipv4: bool, use_ipv6: bool) -> list[str]:
        everything = original(use_ipv4, use_ipv6)
        tail = [a for a in everything if (ipaddress.ip_address(a) in cgnat or ipaddress.ip_address(a) in ula)]
        return tail or everything

    ice.get_host_addresses = tailnet_only


# H7: while a free call is on, what was said stays out of the server log. Pipecat's voice
# writes every sentence it speaks to the log ("Generating TTS [...]"), and Whisper's text
# ("Transcription: [...]"); those lines are dropped as long as a free call runs. Pipecat sets
# up the log itself when the server starts, so the filter goes in at the first call.
_free_calls = 0
_log_filter_on = False
_SAID = ("Generating TTS [", "Transcription: [")


def _keep_log_line(record) -> bool:
    return not (_free_calls and any(m in record["message"] for m in _SAID))


def _filter_the_log() -> None:
    global _log_filter_on
    if not _log_filter_on:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG", filter=_keep_log_line)
        _log_filter_on = True


async def run_call(transport: SmallWebRTCTransport, handle_sigint: bool, connection=None,
                   model: str | None = None, voice: str | None = None, waiting_lines: bool = False,
                   free: bool = False, load: str | None = None, agent: str | None = None) -> None:
    global _free_calls
    _filter_the_log()
    if free:
        _free_calls += 1
    try:
        await _run_call(transport, handle_sigint, connection, model=model, voice=voice,
                        waiting_lines=waiting_lines, free=free, load=load, agent=agent)
    finally:
        if free:
            _free_calls -= 1


async def _run_call(transport: SmallWebRTCTransport, handle_sigint: bool, connection=None,
                    model: str | None = None, voice: str | None = None, waiting_lines: bool = False,
                    free: bool = False, load: str | None = None, agent: str | None = None) -> None:
    call = Call(model=model, voice=voice, waiting_lines=waiting_lines, free=free, load=load, agent=agent)
    logger.info(f"Call started on {call.model} with {call.agent['name']}, voice {call.voice}, {'free' if free else call.load + ' load'}; "
                + ("free mode, nothing kept" if free else f"transcript: {call.transcript.path.name}"))

    # Warm everything up in the background while the browser finishes connecting: open and
    # prime the Claude session, load Whisper, run Kokoro once. The pipeline starts right away.
    warming = asyncio.create_task(call.warm())

    # H3: tell the call page what Jarvis is doing (listening, thinking, speaking).
    call_state = CallState(connection.send_app_message if connection is not None else None)
    # H6: every spoken line also goes to the call page, for the chat log.
    if connection is not None:
        def to_page(who: str, text: str) -> None:
            connection.send_app_message({"type": "jarvis-chat", "who": who, "text": text})
        call.transcript.on_line = to_page

        # H31: the Cancel button shows while what he said can still be taken back.
        def cancellable(on: bool) -> None:
            connection.send_app_message({"type": "jarvis-cancellable", "on": on})
        call.llm.on_cancellable = cancellable
    # H9: while the talk button is held, the turn stays his.
    ptt = PushToTalk()
    pipeline, _ = build_pipeline(
        source=transport.input(), sink=transport.output(), stt=call.stt, llm=call.llm,
        tts=call.tts, fillers=call.fillers, call_state=call_state, ptt=ptt,
    )
    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("The caller connected")
        # Jarvis opens the call, like an assistant picking up the phone.
        asyncio.create_task(call.fillers.greet())

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("The caller hung up")
        await worker.cancel()

    # The phone page's Hang up button sends {"type": "hangup"} over the data channel before
    # it closes the connection, so the after-call work starts at once instead of after the
    # ~35 s it takes to notice a connection that just went quiet.
    if connection is not None:
        @connection.event_handler("app-message")
        async def on_app_message(conn, message):
            if isinstance(message, dict) and message.get("type") == "hangup":
                logger.info("The caller hung up (button)")
                await worker.cancel()
            elif isinstance(message, dict) and message.get("type") == "ptt":
                await ptt.set_held(bool(message.get("held")))
            elif isinstance(message, dict) and message.get("type") == "typed":
                # H18: he typed in the chat instead of talking; she answers out loud as usual.
                await type_to_jarvis(worker, call.llm, call_state, str(message.get("text") or ""))
            elif isinstance(message, dict) and message.get("type") == "cancel":
                # H31: he takes back what he just said, before she answers.
                if await cancel_turn(ptt.user_aggregator, call.llm, call_state):
                    connection.send_app_message({"type": "jarvis-cancelled"})
                else:
                    # H38: too late for that: she stops, and "Cancel last message" goes in as his turn.
                    await late_cancel(worker, call.llm, call_state,
                                      lambda: connection.send_app_message({"type": "jarvis-cancelled"}))

    runner = WorkerRunner(handle_sigint=handle_sigint)
    await runner.add_workers(worker)
    try:
        await runner.run()
    finally:
        ptt.stop()
        if not warming.done():
            warming.cancel()
        # The after-call work runs on its own task, shielded: if this coroutine is
        # cancelled (the server is shutting down), it still gets as far as it can.
        await asyncio.shield(asyncio.create_task(call.finish(), name="after-call"))


async def bot(runner_args: RunnerArguments):
    """Entry point for Pipecat's runner: one call per browser connection."""
    if not isinstance(runner_args, SmallWebRTCRunnerArguments):
        raise RuntimeError("Jarvis VA only runs over the small WebRTC transport (-t webrtc)")
    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    )
    # Quick (Sonnet) or Deep (Opus), chosen on the call page; Free (H7, H8) is a switch on top of
    # either: a plain Claude with the internet, nothing of his. mode "free" is from an old page.
    body = runner_args.body if isinstance(runner_args.body, dict) else {}
    mode = str(body.get("mode", "quick"))
    free = body.get("free") is True or mode == "free"
    # H29: the page sends the agent (Pepper, Donna, ...); her model and load win over the mode.
    # A page from before H29 sends only the mode: the agent with that load.
    agent = agents.find(config.FOLDER, str(body.get("agent", "")) or None, mode if mode in ("quick", "deep") else None)
    model = config.MODEL_ALIASES.get(agent["model"], agent["model"])
    mode = agent["load"]
    voice = str(body.get("voice", ""))  # one of config.VOICES, else the default (Call checks)
    waiting_lines = body.get("waiting_lines") is True  # H1: off unless the page switch is on
    # B1: Quick loads only part of his folder, Deep everything.
    load = mode if mode in ("quick", "deep") else "quick"
    await run_call(transport, runner_args.handle_sigint, runner_args.webrtc_connection,
                   model=model, voice=voice, waiting_lines=waiting_lines, free=free, load=load, agent=agent["id"])


if __name__ == "__main__":
    from pipecat.runner.run import app, main

    # The phone page (A4): our own page at / and /call instead of Pipecat's prebuilt client
    # (which stays at /client/). Registered before main() adds the runner's own routes, so
    # these win. Static files are read from app/web.
    from fastapi.responses import FileResponse, Response

    keep_audio_in_the_tailnet()

    WEB = Path(__file__).resolve().parent / "web"
    _NO_CACHE = {"Cache-Control": "no-cache"}

    @app.get("/", include_in_schema=False)
    @app.get("/call", include_in_schema=False)
    async def phone_page():
        return FileResponse(WEB / "index.html", media_type="text/html", headers=_NO_CACHE)

    @app.get("/manifest.webmanifest", include_in_schema=False)
    async def phone_manifest():
        return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json", headers=_NO_CACHE)

    # H34: the last call's conversation, for the chat before a call. Read only, from the saved
    # transcripts in calls/; nothing is written. Free calls are never saved, so never shown.
    from fastapi.responses import JSONResponse
    import transcript as _transcript

    # H29: the agents for the call page (no personality text), and each one's headshot: the
    # workspace's picture when there is one, else a drawn placeholder.
    import agents as _agents

    @app.get("/api/agents", include_in_schema=False)
    async def agent_list():
        return JSONResponse({"agents": [_agents.public(a) for a in _agents.visible(config.FOLDER)]}, headers=_NO_CACHE)

    @app.get("/agents/{agent_id}/picture", include_in_schema=False)
    async def agent_picture(agent_id: str):
        every = {a["id"]: a for a in _agents.load(config.FOLDER)}
        if agent_id not in every:
            return Response(status_code=404)
        pic = _agents.picture(config.FOLDER, agent_id)
        if pic:
            return FileResponse(pic, media_type=_agents.PICTURE_TYPES[pic.suffix.lower()], headers=_NO_CACHE)
        return Response(_agents.picture_svg(every[agent_id]), media_type="image/svg+xml", headers=_NO_CACHE)

    @app.get("/api/last-call", include_in_schema=False)
    async def last_call():
        return JSONResponse(_transcript.last_call() or {"lines": []}, headers=_NO_CACHE)

    for _icon in ("apple-touch-icon.png", "icon-192.png", "icon-512.png"):
        def _make(name):
            async def icon():
                return FileResponse(WEB / name, media_type="image/png")
            return icon
        app.add_api_route("/" + _icon, _make(_icon), methods=["GET"], include_in_schema=False)

    # Only this MacBook, on 7860 (the status page uses 4747/4748). Tailscale serve (start.sh)
    # puts HTTPS in front of it for the phone; nothing else can reach it.
    if "--host" not in sys.argv:
        sys.argv += ["--host", config.HOST]
    if "--port" not in sys.argv:
        sys.argv += ["--port", str(config.PORT)]
    if "-t" not in sys.argv and "--transport" not in sys.argv:
        sys.argv += ["-t", "webrtc"]
    main()
