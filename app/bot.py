"""HQ: a live voice call with Claude, at the desk.

Start it with app/start.sh, open http://127.0.0.1:7860 and press Connect.
Each browser connection is one call (call.py) with its own Claude session: since A3 the
full Claude of the user's workspace. After hang-up, also when the tab is just
closed, the same session writes things down, commits and pushes.
"""
from __future__ import annotations

import asyncio
import contextvars
import json
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
from pipeline import PushToTalk, build_pipeline, cancel_turn, late_cancel, type_to_agent


# H46: True while the call line answers an offer from a page on this MacBook itself (see CallerHere).
_caller_here = contextvars.ContextVar("caller_here", default=False)
_all_addresses = None  # aioice's own list of this MacBook's addresses, before the tailnet filter


def keep_audio_in_the_tailnet() -> None:
    """The MacBook only offers its Tailscale addresses (100.x and fd7a:...) as places to send
    the call's audio to, not its Wi-Fi or public IPv6 addresses. With no outside STUN/TURN
    servers either, the audio can only travel through Tailscale. If the MacBook has no
    Tailscale address (Tailscale off), all addresses are offered, so the call still works
    at the desk. HQ_TAILNET_ONLY=0 turns this off.

    H46 (11 October 2026): the HQ app on this MacBook (WebKit) never offers a Tailscale address,
    only Wi-Fi, so its calls timed out. When the caller offers one of this MacBook's own addresses,
    the caller is this MacBook, and the audio never leaves it: then all addresses are offered.
    A phone can't offer the MacBook's own address, so its calls stay Tailscale only."""
    import ipaddress

    import aioice.ice as ice

    if os.environ.get("HQ_TAILNET_ONLY", "1") == "0":
        return
    global _all_addresses
    original = _all_addresses = ice.get_host_addresses
    cgnat = ipaddress.ip_network("100.64.0.0/10")
    ula = ipaddress.ip_network("fd7a:115c:a1e0::/48")

    def tailnet_only(use_ipv4: bool, use_ipv6: bool) -> list[str]:
        everything = original(use_ipv4, use_ipv6)
        if _caller_here.get():
            return everything
        tail = [a for a in everything if (ipaddress.ip_address(a) in cgnat or ipaddress.ip_address(a) in ula)]
        return tail or everything

    ice.get_host_addresses = tailnet_only


def own_addresses() -> set[str]:
    import aioice.ice as ice
    return set((_all_addresses or ice.get_host_addresses)(True, True))


def offer_from_this_mac(body: bytes) -> bool:
    """H46: does this offer (the call page's JSON with its SDP) come from a page on this MacBook?
    Yes when one of its candidates is one of this MacBook's own addresses."""
    try:
        sdp = json.loads(body or b"{}").get("sdp", "")
    except (ValueError, AttributeError):
        return False
    theirs = {ln.split()[4] for ln in str(sdp).splitlines() if ln.startswith("a=candidate") and len(ln.split()) > 4}
    return bool(theirs & own_addresses())


class CallerHere:
    """H46: reads a call's offer before the call line answers it, and marks it when it comes from this
    MacBook (offer_from_this_mac), so keep_audio_in_the_tailnet offers this MacBook's own addresses too."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method") != "POST" or scope.get("path") != "/api/offer":
            return await self.app(scope, receive, send)
        chunks, more = [], True
        while more:
            m = await receive()
            chunks.append(m.get("body", b""))
            more = m.get("more_body", False)
        body = b"".join(chunks)
        given = False

        async def replay():
            nonlocal given
            if not given:
                given = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        token = _caller_here.set(offer_from_this_mac(body))
        try:
            await self.app(scope, replay, send)
        finally:
            _caller_here.reset(token)


# H7: while a free call is on, what was said stays out of the server log. Pipecat's voice
# writes every sentence it speaks to the log ("Generating TTS [...]"), and Whisper's text
# ("Transcription: [...]"); those lines are dropped as long as a free call runs. Pipecat sets
# up the log itself when the server starts, so the filter goes in at the first call.
_free_calls = 0
# H59: how many calls are on, their after-call work included, so an update never starts during one (/api/busy).
_calls_on = 0
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
                   free: bool = False, load: str | None = None, agent: str | None = None,
                   continues: str | None = None) -> None:
    global _free_calls, _calls_on
    _filter_the_log()
    if free:
        _free_calls += 1
    _calls_on += 1
    try:
        await _run_call(transport, handle_sigint, connection, model=model, voice=voice,
                        waiting_lines=waiting_lines, free=free, load=load, agent=agent, continues=continues)
    finally:
        _calls_on -= 1
        if free:
            _free_calls -= 1


async def _run_call(transport: SmallWebRTCTransport, handle_sigint: bool, connection=None,
                    model: str | None = None, voice: str | None = None, waiting_lines: bool = False,
                    free: bool = False, load: str | None = None, agent: str | None = None,
                    continues: str | None = None) -> None:
    call = Call(model=model, voice=voice, waiting_lines=waiting_lines, free=free, load=load, agent=agent,
                continues=continues)
    logger.info(f"Call started on {call.model} with {call.agent['name']}, voice {call.voice}, {'free' if free else call.load + ' load'}; "
                + ("free mode, nothing kept" if free else f"transcript: {call.transcript.path.name}")
                + (f"; continues {call.continued['name']}" if call.continued else ""))

    # Warm everything up in the background while the browser finishes connecting: open and
    # prime the Claude session, load Whisper, run Kokoro once. The pipeline starts right away.
    warming = asyncio.create_task(call.warm())

    # H3: tell the call page what HQ is doing (listening, thinking, speaking).
    call_state = CallState(connection.send_app_message if connection is not None else None)
    # H6: every spoken line also goes to the call page, for the chat log.
    if connection is not None:
        def to_page(who: str, text: str) -> None:
            connection.send_app_message({"type": "hq-chat", "who": who, "text": text})
        call.transcript.on_line = to_page

        # H31: the Cancel button shows while what he said can still be taken back.
        def cancellable(on: bool) -> None:
            connection.send_app_message({"type": "hq-cancellable", "on": on})
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
        idle_timeout_secs=config.CALL_IDLE_SECS,  # F9: a quiet call stays on
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("The caller connected")
        # HQ opens the call, like an assistant picking up the phone.
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
                await type_to_agent(worker, call.llm, call_state, str(message.get("text") or ""))
            elif isinstance(message, dict) and message.get("type") == "cancel":
                # H31: he takes back what he just said, before she answers.
                if await cancel_turn(ptt.user_aggregator, call.llm, call_state):
                    connection.send_app_message({"type": "hq-cancelled"})
                else:
                    # H38: too late for that: she stops, and "Cancel last message" goes in as his turn.
                    await late_cancel(worker, call.llm, call_state,
                                      lambda: connection.send_app_message({"type": "hq-cancelled"}))

    # H75: she said goodbye after his clear goodbye and it has been heard: the call ends as if he
    # tapped Hang up. The page is told first (it closes the same way); the server doesn't wait on it.
    async def agent_hangs_up():
        if call.ended_by_agent:
            return
        call.ended_by_agent = True
        logger.info(f"{call.agent['name']} hung up after the goodbye")
        if connection is not None:
            try:
                connection.send_app_message({"type": "hq-hangup"})
            except Exception:
                pass
        await asyncio.sleep(1.0)
        await worker.cancel()
    call.llm.on_hangup = agent_hangs_up

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
        raise RuntimeError("HQ only runs over the small WebRTC transport (-t webrtc)")
    transport = SmallWebRTCTransport(
        webrtc_connection=runner_args.webrtc_connection,
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    )
    # Quick (Sonnet) or Deep (Opus), chosen on the call page; Free (H7, H8) is a switch on top of
    # either: a plain Claude with the internet, nothing of his. mode "free" is from an old page.
    body = runner_args.body if isinstance(runner_args.body, dict) else {}
    mode = str(body.get("mode", "quick"))
    free = body.get("free") is True or mode == "free" or config.FREE_ONLY
    # H29: the page sends the agent (Pepper, Donna, ...); her model and load win over the mode.
    # A page from before H29 sends only the mode: the agent with that load.
    agent = agents.find(config.FOLDER, str(body.get("agent", "")) or None, mode if mode in ("quick", "deep") else None)
    model = config.MODEL_ALIASES.get(agent["model"], agent["model"])
    mode = agent["load"]
    # H46: each agent has her own voice (Settings on the call page); the page sends hers, else her default.
    voice = str(body.get("voice", "")) or agent.get("voice", "")  # one of config.VOICES, else the default (Call checks)
    # H46 (11 October 2026), in the user's words: "i want the waiting lines to be gone from the settings as we
    # dont want to use these lines anymore." So they're always off, whatever an older page sends.
    waiting_lines = False
    # B1: Quick loads only part of his folder, Deep everything.
    load = mode if mode in ("quick", "deep") else "quick"
    # H60: Continue in Past calls sends the earlier call's name; never on Free (Call checks it's a saved call).
    continues = str(body.get("continue") or "") or None
    await run_call(transport, runner_args.handle_sigint, runner_args.webrtc_connection,
                   model=model, voice=voice, waiting_lines=waiting_lines, free=free, load=load, agent=agent["id"],
                   continues=None if free else continues)


if __name__ == "__main__":
    from pipecat.runner.run import app, main

    # The phone page (A4): our own page at / and /call instead of Pipecat's prebuilt client
    # (which stays at /client/). Registered before main() adds the runner's own routes, so
    # these win. Static files are read from app/web.
    from fastapi.responses import FileResponse, Response

    keep_audio_in_the_tailnet()
    app.add_middleware(CallerHere)  # H46

    WEB = Path(__file__).resolve().parent / "web"
    _NO_CACHE = {"Cache-Control": "no-cache"}

    # H96 (12 October 2026): on a second HQ (a server, HQ_LABEL set, e.g. VPS) the call page gets the same night
    # icon as its status page (H84, status/icons/hq-night-*.png), and its own name in the manifest, so it sits next
    # to the laptop's on the home screen. Without HQ_LABEL nothing changes: the laptop keeps the daytime icon.
    # F21 (12 October 2026): the iPhone kept the old icon under the old addresses, so on a server the page and the
    # manifest point at new names (NIGHT_LINKS, NIGHT_NAMES), every apple-touch-icon iOS may look for at the root
    # (with and without -precomposed, and the 180x180 sizes) and a favicon are the night icon too, and the icons
    # are served with no-cache. The night PNGs are opaque squares to the edges (RGB, no alpha): no border.
    LABEL = os.environ.get("HQ_LABEL", "").strip().replace("<", "").replace(">", "").replace("&", "").replace('"', "")
    NIGHT = Path(__file__).resolve().parent.parent / "status" / "icons"
    ICONS = {"apple-touch-icon.png": WEB / "apple-touch-icon.png", "icon-192.png": WEB / "icon-192.png",
             "icon-512.png": WEB / "icon-512.png"}
    NIGHT_NAMES = {"hq-call-night-180.png": NIGHT / "hq-night-180.png",
                   "hq-call-night-192.png": NIGHT / "hq-night-192.png",
                   "hq-call-night-512.png": NIGHT / "hq-night-512.png"}
    NIGHT_LINKS = ('<link rel="apple-touch-icon" sizes="180x180" href="hq-call-night-180.png">\n'
                   '<link rel="apple-touch-icon" href="hq-call-night-180.png">\n'
                   '<link rel="apple-touch-icon-precomposed" href="hq-call-night-180.png">\n'
                   '<link rel="icon" type="image/png" sizes="192x192" href="hq-call-night-192.png">')
    if LABEL:
        ICONS = {"apple-touch-icon.png": NIGHT / "hq-night-180.png", "icon-192.png": NIGHT / "hq-night-192.png",
                 "icon-512.png": NIGHT / "hq-night-512.png",
                 "apple-touch-icon-precomposed.png": NIGHT / "hq-night-180.png",
                 "apple-touch-icon-180x180.png": NIGHT / "hq-night-180.png",
                 "apple-touch-icon-180x180-precomposed.png": NIGHT / "hq-night-180.png",
                 "favicon.png": NIGHT / "hq-night-192.png", **NIGHT_NAMES}

    @app.get("/", include_in_schema=False)
    @app.get("/call", include_in_schema=False)
    async def phone_page():
        if not LABEL:
            return FileResponse(WEB / "index.html", media_type="text/html", headers=_NO_CACHE)
        html = (WEB / "index.html").read_text().replace(
            '<link rel="apple-touch-icon" href="apple-touch-icon.png">', NIGHT_LINKS)
        return Response(html, media_type="text/html; charset=utf-8", headers=_NO_CACHE)

    if LABEL:
        @app.get("/favicon.ico", include_in_schema=False)
        async def favicon():
            return FileResponse(NIGHT / "hq-night-192.png", media_type="image/png", headers=_NO_CACHE)

    @app.get("/manifest.webmanifest", include_in_schema=False)
    async def phone_manifest():
        if not LABEL:
            return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json", headers=_NO_CACHE)
        from fastapi.responses import JSONResponse as _JSON
        m = json.loads((WEB / "manifest.webmanifest").read_text())
        m["name"], m["short_name"] = f"{m['name']} ({LABEL})", f"{m['short_name']} {LABEL}"
        m["icons"] = [{"src": "/hq-call-night-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                      {"src": "/hq-call-night-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"}]
        return _JSON(m, media_type="application/manifest+json", headers=_NO_CACHE)

    # H34: the last call's conversation, for the chat before a call. Read only, from the saved
    # transcripts in calls/; nothing is written. Free calls are never saved, so never shown.
    from fastapi.responses import JSONResponse
    import transcript as _transcript

    # H29: the agents for the call page (no personality text), and each one's headshot: the
    # workspace's picture when there is one, else a drawn placeholder.
    import agents as _agents

    @app.get("/api/agents", include_in_schema=False)
    async def agent_list():
        return JSONResponse({"agents": [_agents.public(a) for a in _agents.visible(config.FOLDER)],
                             "soon": [_agents.public(a) for a in _agents.soon(config.FOLDER)],  # H73
                             "free_only": config.FREE_ONLY}, headers=_NO_CACHE)

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

    # H57: every saved call, newest first, and one call by its name; read only, nothing is written.
    @app.get("/api/calls", include_in_schema=False)
    async def call_list():
        return JSONResponse({"calls": _transcript.list_calls()}, headers=_NO_CACHE)

    @app.get("/api/calls/{name}", include_in_schema=False)
    async def call_one(name: str):
        data = _transcript.read_call(name)
        return JSONResponse(data, headers=_NO_CACHE) if data else JSONResponse({"error": "no such call"}, status_code=404, headers=_NO_CACHE)

    # H59: is a call on (for the update, which waits until it ends); the version, a newer one, the update and
    # the changelog, from routine/update.py, at the same addresses as the status page; and the shared page part.
    import subprocess as _sp
    from fastapi import Request

    _UPDATE = Path(__file__).resolve().parent.parent / "routine" / "update.py"
    _STATUS_JS = Path(__file__).resolve().parent.parent / "status" / "update-ui.js"

    def _update(*args: str):
        r = _sp.run([sys.executable, str(_UPDATE), *args], capture_output=True, text=True, timeout=120)
        try:
            return json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            return None

    @app.get("/api/busy", include_in_schema=False)
    async def busy():
        return JSONResponse({"calls": _calls_on}, headers=_NO_CACHE)

    @app.get("/update-ui.js", include_in_schema=False)
    async def update_ui():
        return FileResponse(_STATUS_JS, media_type="text/javascript", headers=_NO_CACHE)

    @app.get("/api/update", include_in_schema=False)
    async def update_status():
        out = await asyncio.to_thread(_update, "status")
        return JSONResponse(out, status_code=200 if out else 500, headers=_NO_CACHE)

    @app.get("/api/changelog", include_in_schema=False)
    async def update_changelog():
        out = await asyncio.to_thread(_update, "changelog")
        return JSONResponse(out, status_code=200 if out else 500, headers=_NO_CACHE)

    @app.post("/api/update/{what}", include_in_schema=False)
    async def update_do(what: str, request: Request):
        if what not in ("start", "check") or request.headers.get("x-hq") != "update":
            return JSONResponse({"error": "Only the HQ page can start an update"}, status_code=403)
        if what == "check":
            await asyncio.to_thread(_update, "check", "--force")
        out = await asyncio.to_thread(_update, "start" if what == "start" else "status")
        return JSONResponse(out, status_code=200 if out else 500, headers=_NO_CACHE)

    for _icon in ICONS:
        def _make(name):
            async def icon():
                return FileResponse(ICONS[name], media_type="image/png", headers=_NO_CACHE if LABEL else None)
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
