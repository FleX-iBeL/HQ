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
                   continues: str | None = None, handover: bool = False, voices: dict | None = None,
                   about: dict | None = None, demo: bool = False, demo_topic: str = "", callback: bool = False) -> None:
    global _free_calls, _calls_on
    free = free or demo  # H74: a demo call is a Free call
    _filter_the_log()
    if free:
        _free_calls += 1
    _calls_on += 1
    try:
        await _run_call(transport, handle_sigint, connection, model=model, voice=voice,
                        waiting_lines=waiting_lines, free=free, load=load, agent=agent, continues=continues,
                        handover=handover, voices=voices, about=about, demo=demo, demo_topic=demo_topic,
                        callback=callback)
    finally:
        _calls_on -= 1
        if free:
            _free_calls -= 1


async def _run_call(transport: SmallWebRTCTransport, handle_sigint: bool, connection=None,
                    model: str | None = None, voice: str | None = None, waiting_lines: bool = False,
                    free: bool = False, load: str | None = None, agent: str | None = None,
                    continues: str | None = None, handover: bool = False, voices: dict | None = None,
                    about: dict | None = None, demo: bool = False, demo_topic: str = "", callback: bool = False) -> None:
    call = Call(model=model, voice=voice, waiting_lines=waiting_lines, free=free, load=load, agent=agent,
                continues=continues, handover=handover, voices=voices, about=about, demo=demo, demo_topic=demo_topic,
                callback=callback)
    logger.info(f"Call started on {call.model} with {call.agent['name']}, voice {call.voice}, {'free' if free else call.load + ' load'}; "
                + ("demo call from the tutorial, nothing kept" if demo else "free mode, nothing kept" if free else f"transcript: {call.transcript.path.name}")
                + (f"; continues {call.continued['name']}" if call.continued else "")
                + (f"; about {'a to-do item' if call.about.get('kind') == 'todo' else 'an appointment'} ({call.about['title']})" if call.about else ""))

    # Warm everything up in the background while the browser finishes connecting: open and
    # prime the Claude session, load Whisper, run Kokoro once. The pipeline starts right away.
    warming = asyncio.create_task(call.warm())

    # H3: tell the call page what HQ is doing (listening, thinking, speaking).
    call_state = CallState(connection.send_app_message if connection is not None else None)
    # H6: every spoken line also goes to the call page, for the chat log.
    if connection is not None:
        def to_page(who: str, text: str) -> None:
            # H79: on a three-way call her lines say who said them (her colour in the chat)
            her = {"agent": call.transcript.speaker} if who == "hq" and call.transcript.speaker else {}
            connection.send_app_message({"type": "hq-chat", "who": who, "text": text, **her})
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

    # H238: he asked her to hang up and call him right back. The call ends as a hang-up does (notes and all); the
    # page loads itself again (fresh page code) and calls the same agent, continuing this call.
    async def agent_calls_back():
        if call.ended_by_agent:
            return
        call.ended_by_agent = True
        logger.info(f"H238: {call.speaker['name']} calls him right back")
        if connection is not None:
            try:
                connection.send_app_message({"type": "hq-callback", "agent": call.speaker["id"],
                                             "call": call.transcript.path.stem if call.transcript.path else None})
            except Exception:
                pass
        await asyncio.sleep(1.0)
        await worker.cancel()
    call.llm.on_callback = agent_calls_back

    # H79: he asked for another agent. Hand over: the call ends as a hang-up does (notes and all) and the page
    # calls her at once, continuing this call. Three-way: she joins this same conversation.
    async def agent_switches(other_id: str):
        if call.ended_by_agent:
            return
        other = next((a for a in call.others if a["id"] == other_id), None)
        if other is None:
            return
        call.ended_by_agent = True
        call.switched_to = other
        logger.info(f"H79: {call.speaker['name']} puts {other['name']} on")
        if connection is not None:
            try:
                connection.send_app_message({"type": "hq-switch", "agent": other["id"],
                                             "call": call.transcript.path.stem if call.transcript.path else None})
            except Exception:
                pass
        await asyncio.sleep(1.0)
        await worker.cancel()
    call.llm.on_switch = agent_switches

    async def agent_joins(other_id: str):
        other = await call.three_way(other_id)
        if other is not None and connection is not None:
            try:
                connection.send_app_message({"type": "hq-three-way", "agents": [a["id"] for a in call.panel]})
            except Exception:
                pass
    call.llm.on_three_way = agent_joins

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
    # H74: a demo call from the get-started tutorial: Free (nothing of his, nothing saved), Opus, no tools (tour.py)
    demo = body.get("demo") is True
    demo_topic = str(body.get("demo_topic") or "")[:40] if demo else ""
    free = free or demo
    # H29: the page sends the agent (Pepper, Donna, ...); her model and load win over the mode.
    # A page from before H29 sends only the mode: the agent with that load.
    agent = agents.find(config.FOLDER, str(body.get("agent", "")) or None, mode if mode in ("quick", "deep") else None)
    model = config.MODEL_ALIASES.get(agents.runs_on(agent["model"]), agent["model"])
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
    # H79: a hand-over from another agent (the page calls her right after), and every agent's voice from Settings
    handover = body.get("handover") is True
    callback = body.get("callback") is True  # H238: she's calling him right back after his "hang up and call me back"
    voices = body.get("voices") if isinstance(body.get("voices"), dict) else {}
    # H101: a call started from an appointment in the calendar sends its id; the saved appointment goes in. Never on Free.
    import agenda as _agenda
    about = None if free else _agenda.about(str(body.get("about") or ""))
    if about is None and not free and body.get("about_todo"):  # H200: a call started from an item on the to-do list
        import todo as _todo_call
        about = _todo_call.about(str(body.get("about_todo") or ""))
    if about is None and not free and body.get("about_coaching"):  # H225: a layer or a check-in from the Coaching place
        import coaching as _coaching_call
        about = _coaching_call.about(str(body.get("about_coaching") or ""))
    if about is None and not free and body.get("about_news"):  # H236: the short session that sets up their news
        import news as _news_call
        about = _news_call.about(str(body.get("about_news") or "setup"))
    if about is None and not free and body.get("ring"):  # H238: he picked up the agent's call from the notification
        import ringing as _ringing
        about = _ringing.about(str(body.get("ring") or ""))
        if about is not None:
            agent = agents.find(config.FOLDER, about["agent"]) or agent  # the agent who's calling, whatever the page had
            model = config.MODEL_ALIASES.get(agents.runs_on(agent["model"]), agent["model"])
            mode = agent["load"]
            load = mode if mode in ("quick", "deep") else "quick"
            voice = str(voices.get(agent["id"]) or agent.get("voice", ""))
    await run_call(transport, runner_args.handle_sigint, runner_args.webrtc_connection,
                   model=model, voice=voice, waiting_lines=waiting_lines, free=free, load=load, agent=agent["id"],
                   continues=None if free else continues, handover=handover and not free, voices=voices, about=about,
                   demo=demo, demo_topic=demo_topic, callback=callback and not free)


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
    # H194 (17 October 2026): on a laptop the call page has HQ's own house too (status/icons/hq-*.png, the same as
    # the HQ page), under every name iOS and Safari's Add to Dock may look for, so a friend's fresh install saved to
    # the home screen or the Dock shows HQ's icon, never a screenshot or the old rings.
    HOUSE = Path(__file__).resolve().parent.parent / "status" / "icons"
    ICONS = {"apple-touch-icon.png": HOUSE / "hq-180.png", "icon-192.png": HOUSE / "hq-192.png",
             "icon-512.png": HOUSE / "hq-512.png",
             "apple-touch-icon-precomposed.png": HOUSE / "hq-180.png",
             "apple-touch-icon-180x180.png": HOUSE / "hq-180.png",
             "apple-touch-icon-180x180-precomposed.png": HOUSE / "hq-180.png",
             "favicon.png": HOUSE / "hq-192.png"}
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

    # H74: the get-started tutorial's pieces (the question mark on the page; tour.py makes the demo call from the same)
    @app.get("/games.js", include_in_schema=False)
    async def games_js():  # H222: the six-week game's sheet and its kinds of tracks
        return FileResponse(WEB / "games.js", media_type="text/javascript", headers=_NO_CACHE)

    @app.get("/coach.js", include_in_schema=False)
    async def coach_js():  # H225: the Coaching place
        return FileResponse(WEB / "coach.js", media_type="text/javascript", headers=_NO_CACHE)

    @app.get("/news.js", include_in_schema=False)
    async def news_js():  # H236: the News sheet, their own newspaper
        return FileResponse(WEB / "news.js", media_type="text/javascript", headers=_NO_CACHE)

    @app.get("/tour.json", include_in_schema=False)
    async def tour_json():
        return FileResponse(WEB / "tour.json", media_type="application/json", headers=_NO_CACHE)

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse(ICONS["favicon.png"], media_type="image/png", headers=_NO_CACHE)

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

    # H105: the quick notes behind the round notes button (just text since H117). Kept in the workspace (notes.py);
    # changed only from the call page itself (the header x-hq: notes), like the update's buttons.
    import notes as _notes

    def _notes_both():
        # H124: Donna's own notes come along, shown under his (read here, cleared with clear_hers).
        out = _notes.read()
        try:
            import pings as _pings
            out["hers"] = {"name": _pings.agent_name(), "items": _pings.her_notes(),
                           "watches": _pings.watch_items(),  # H125: what she keeps an eye out for
                           "nudges": _pings.nudge_items()}  # H211: what she nudges him about until it's done
        except Exception:
            pass
        return out

    @app.get("/api/notes", include_in_schema=False)
    async def notes_read():
        return JSONResponse(_notes_both(), headers=_NO_CACHE)

    @app.post("/api/notes", include_in_schema=False)
    async def notes_change(request: Request):
        if request.headers.get("x-hq") != "notes":
            return JSONResponse({"error": "Only the HQ page can change the notes"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict):
            return JSONResponse({"error": "no change asked"}, status_code=400)
        if isinstance(ask.get("add"), str):
            if not _notes.add(ask["add"]):
                return JSONResponse({"error": "nothing to add"}, status_code=400)
        elif isinstance(ask.get("clear"), str):
            if not _notes.clear(ask["clear"]):
                return JSONResponse({"error": "no such note"}, status_code=404)
        elif ask.get("clear_all") is True:
            _notes.clear_all()
        elif isinstance(ask.get("clear_hers"), str):
            import pings as _pings
            if not _notes.clear(ask["clear_hers"], _pings.notes_file()):
                return JSONResponse({"error": "no such note"}, status_code=404)
        elif isinstance(ask.get("nudge_done"), int):  # H211: Done in the app stops her nudges
            import pings as _pings
            if not _pings.nudge_done(str(ask["nudge_done"])):
                return JSONResponse({"error": "no such nudge"}, status_code=404)
        else:
            return JSONResponse({"error": "no change asked"}, status_code=400)
        return JSONResponse(_notes_both(), headers=_NO_CACHE)

    # H247: the Feedback button, next to the quick notes. What's sent lands on the planning under Feedback
    # (feedback.py, jobs.py feedback); the sender's own list with each one's status comes back.
    import feedback as _feedback

    @app.get("/api/feedback", include_in_schema=False)
    async def feedback_read():
        return JSONResponse(await asyncio.to_thread(_feedback.read), headers=_NO_CACHE)

    @app.post("/api/feedback", include_in_schema=False)
    async def feedback_send(request: Request):
        if request.headers.get("x-hq") != "feedback":
            return JSONResponse({"error": "Only the HQ page can send feedback"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict) or not isinstance(ask.get("text"), str):
            return JSONResponse({"error": "nothing to send"}, status_code=400)
        res = await asyncio.to_thread(_feedback.send, ask["text"], ask.get("bug") is True)
        if "error" in res:
            return JSONResponse(res, status_code=400)
        return JSONResponse({"sent": res, **(await asyncio.to_thread(_feedback.read))}, headers=_NO_CACHE)

    # H101: his calendar, read only (agenda.py). ?fresh=1 (the page opening it) reads Google again when the last read
    # is older than a quarter of an hour; the answer says it's reading, and the page asks again a bit later.
    import agenda as _agenda_api

    @app.get("/api/calendar", include_in_schema=False)
    async def calendar_read(request: Request):
        if request.query_params.get("fresh") == "1" and not config.FREE_ONLY:
            await asyncio.to_thread(_agenda_api.refresh)
        return JSONResponse(_agenda_api.read(), headers=_NO_CACHE)

    # H135: the weather in the app (weather.py view): ?fresh=1 reads it again when the last read is over 15 minutes
    # old. Not on a Free-only line: the place comes from his own files.
    @app.get("/api/weather", include_in_schema=False)
    async def weather_read(request: Request):
        if config.FREE_ONLY:
            return JSONResponse({"off": "Free"}, headers=_NO_CACHE)
        import weather as _weather
        q = request.query_params  # H161: the phone's spot when he allows it (lat, lon), else me.md's place
        gps = (q.get("lat"), q.get("lon")) if q.get("lat") and q.get("lon") else None
        return JSONResponse(await asyncio.to_thread(_weather.view, q.get("fresh") == "1", None, gps),
                            headers=_NO_CACHE)

    # H161: the rain alert switch in the weather sheet: on opens a lasting rain watch on Donna's list, off ends it
    # (pings.py, through weather.rain_alert). Only from the page itself (x-hq: weather), not on a Free-only line.
    @app.post("/api/weather/alert", include_in_schema=False)
    async def weather_alert(request: Request):
        if request.headers.get("x-hq") != "weather":
            return JSONResponse({"error": "Only the HQ page can switch the rain alert"}, status_code=403)
        if config.FREE_ONLY:
            return JSONResponse({"error": "Not on Free"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict) or not isinstance(ask.get("on"), bool):
            return JSONResponse({"error": "on or off?"}, status_code=400)
        import weather as _weather
        return JSONResponse(await asyncio.to_thread(_weather.rain_alert, ask["on"]), headers=_NO_CACHE)

    # H217: where the phone is, for travel advice (app/travel.py's here.json). The page sends it only when he allows
    # his location in the app; only from the page itself (x-hq: here), not on a Free-only line.
    @app.post("/api/here", include_in_schema=False)
    async def here_post(request: Request):
        if request.headers.get("x-hq") != "here":
            return JSONResponse({"error": "Only the HQ page can say where the phone is"}, status_code=403)
        if config.FREE_ONLY:
            return JSONResponse({"error": "Not on Free"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        import travel as _travel
        out = _travel.set_here(ask.get("lat"), ask.get("lon")) if isinstance(ask, dict) else {"ok": False}
        return JSONResponse(out, status_code=200 if out["ok"] else 400, headers=_NO_CACHE)

    # H124: the bell. A tap in the appointment asks Donna to ping him when it starts (or not any more). Only HQ's own
    # list changes (routine/pings.py); Google Calendar is never written. Only from the page itself (x-hq: calendar).
    @app.post("/api/calendar/ping", include_in_schema=False)
    async def calendar_ping(request: Request):
        if request.headers.get("x-hq") != "calendar":
            return JSONResponse({"error": "Only the HQ page can change the pings"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict) or not isinstance(ask.get("id"), str):
            return JSONResponse({"error": "which appointment?"}, status_code=400)
        import pings as _pings
        if ask.get("on"):
            e = _agenda_api.about(ask["id"])
            if not e:
                return JSONResponse({"error": "no such appointment"}, status_code=404)
            _pings.appt_on(e, int(ask.get("before") or 0), by="the calendar in the app")
        else:
            _pings.appt_off(ask["id"])
        return JSONResponse(_agenda_api.read(), headers=_NO_CACHE)

    # H229: travel on an appointment, by hand: {id, on}. Only HQ's own file in the workspace changes (trips.py); on looks
    # the trip up in the background. Google Calendar is never written. Only from the page itself (x-hq: calendar).
    @app.post("/api/calendar/travel", include_in_schema=False)
    async def calendar_travel(request: Request):
        if request.headers.get("x-hq") != "calendar":
            return JSONResponse({"error": "Only the HQ page can change travel"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict) or not isinstance(ask.get("id"), str):
            return JSONResponse({"error": "which appointment?"}, status_code=400)
        import trips as _trips
        try:
            await asyncio.to_thread(_trips.page_switch, ask["id"], bool(ask.get("on")),
                                    ask["mode"] if ask.get("mode") in ("car", "transit") else "")
        except KeyError:
            return JSONResponse({"error": "no such appointment"}, status_code=404)
        return JSONResponse(_agenda_api.read(), headers=_NO_CACHE)

    # H143: the check and the X on an appointment. A tap marks it (done or x), a second tap undoes it ("");
    # since H241 both are kept in HQ only (planning.py); what an old X moved to HQ Planning goes back, after the
    # answer, on the main HQ. Only from the page itself (x-hq: calendar).
    @app.post("/api/calendar/mark", include_in_schema=False)
    async def calendar_mark(request: Request):
        if request.headers.get("x-hq") != "calendar":
            return JSONResponse({"error": "Only the HQ page can mark appointments"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict) or not isinstance(ask.get("id"), str) or ask.get("mark") not in ("done", "x", ""):
            return JSONResponse({"error": "which appointment, and which mark?"}, status_code=400)
        import planning as _planning
        try:
            await asyncio.to_thread(_planning.set_mark, ask["id"], ask["mark"])
        except KeyError:
            return JSONResponse({"error": "no such appointment"}, status_code=404)
        await asyncio.to_thread(_planning.start)
        return JSONResponse(_agenda_api.read(), headers=_NO_CACHE)

    # H244: a kind of the week renamed or given another of Google's colours (kinds.py): {id, name} or {id, colour} or
    # {id, reset: true}. Only HQ's own file in the workspace changes; Google Calendar never does. Only from the page
    # itself (x-hq: calendar).
    @app.post("/api/calendar/kind", include_in_schema=False)
    async def calendar_kind(request: Request):
        if request.headers.get("x-hq") != "calendar":
            return JSONResponse({"error": "Only the HQ page can change the kinds"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict) or not isinstance(ask.get("id"), str):
            return JSONResponse({"error": "which kind?"}, status_code=400)
        import kinds as _kinds
        try:
            if ask.get("reset") is True:
                await asyncio.to_thread(_kinds.reset, ask["id"])
            else:
                if isinstance(ask.get("name"), str):
                    await asyncio.to_thread(_kinds.rename, ask["id"], ask["name"])
                if isinstance(ask.get("colour"), str):
                    await asyncio.to_thread(_kinds.recolour, ask["id"], ask["colour"])
        except KeyError:
            return JSONResponse({"error": "no such kind"}, status_code=404)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        return JSONResponse(_agenda_api.read(), headers=_NO_CACHE)

    # H146: a quick note on an appointment (appt_notes.py): {id, add: text} or {id, clear: note id}. Only HQ's own file in
    # the workspace changes; Google Calendar never does. Only from the page itself (x-hq: calendar).
    @app.post("/api/calendar/note", include_in_schema=False)
    async def calendar_note(request: Request):
        if request.headers.get("x-hq") != "calendar":
            return JSONResponse({"error": "Only the HQ page can change the notes"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict) or not isinstance(ask.get("id"), str) or not (
                isinstance(ask.get("add"), str) or isinstance(ask.get("clear"), str)):
            return JSONResponse({"error": "which appointment, and which note?"}, status_code=400)
        import appt_notes as _appt_notes
        if isinstance(ask.get("add"), str):
            try:
                await asyncio.to_thread(_appt_notes.add, ask["id"], ask["add"])
            except KeyError:
                return JSONResponse({"error": "no such appointment"}, status_code=404)
            except ValueError:
                return JSONResponse({"error": "nothing to add"}, status_code=400)
        elif not await asyncio.to_thread(_appt_notes.clear, ask["id"], ask["clear"]):
            return JSONResponse({"error": "no such note"}, status_code=404)
        return JSONResponse(_agenda_api.read(), headers=_NO_CACHE)

    # H200: the to-do list, the Eisenhower way (todo.py), from the workspace's own file. The page reads it and can tick
    # one off, let it go, move it, add one (several at once, F40), tick a grocery off and back on (F40), put one at
    # another place in its list and rename it (H231), plan it in a calendar block by hand (H243), and undo its last change; calls and Donna keep it the same way. Only from the page itself (x-hq: todo), never on a Free-only
    # line.
    import todo as _todo

    @app.get("/api/todo", include_in_schema=False)
    async def todo_read():
        if config.FREE_ONLY:
            return JSONResponse({"off": "Free"}, headers=_NO_CACHE)
        return JSONResponse(await asyncio.to_thread(_todo.read), headers=_NO_CACHE)

    @app.post("/api/todo", include_in_schema=False)
    async def todo_change(request: Request):
        if request.headers.get("x-hq") != "todo":
            return JSONResponse({"error": "Only the HQ page can change the to-do list"}, status_code=403)
        if config.FREE_ONLY:
            return JSONResponse({"error": "Not on Free"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict):
            return JSONResponse({"error": "no change asked"}, status_code=400)
        by = "in the app"
        from policy import is_backup as _is_backup
        if await asyncio.to_thread(_is_backup):
            # H203: on the backup the main writes the list; the change comes back here with the sync.
            if isinstance(ask.get("done"), str):
                args = ["done", ask["done"], ""]
            elif isinstance(ask.get("letgo"), str):
                args = ["letgo", ask["letgo"], str(ask.get("why") or "")[:500]]
            elif isinstance(ask.get("move"), str) and isinstance(ask.get("to"), str):
                args = ["move", ask["move"], ask["to"]]
            elif isinstance(ask.get("tick"), str):
                args = ["tick", ask["tick"]]
            elif isinstance(ask.get("untick"), str):
                args = ["untick", ask["untick"]]
            elif isinstance(ask.get("order"), str) and isinstance(ask.get("place"), int) and ask["place"] > 0:
                args = ["order", ask["order"], str(ask["place"])]
            elif isinstance(ask.get("rename"), str) and isinstance(ask.get("title"), str):
                args = ["rename", ask["rename"], ask["title"][:300]]
            elif isinstance(ask.get("add"), str) and isinstance(ask.get("list"), str):
                args = ["add", ask["list"], ask["add"][:2000]]
            elif isinstance(ask.get("plan"), str) and isinstance(ask.get("block"), str):
                args = ["plan", ask["plan"], ask["block"][:200]]
            elif isinstance(ask.get("unplan"), str):
                args = ["unplan", ask["unplan"]]
            elif isinstance(ask.get("repeat"), str) and isinstance(ask.get("rule"), str):  # H245
                args = ["repeat", ask["repeat"], ask["rule"][:200] or "off"]
            elif ask.get("undo") is True:
                args = ["undo"]
            else:
                return JSONResponse({"error": "no change asked"}, status_code=400)
            import role as _role
            code, out_, err_, how = await asyncio.to_thread(_role.hand, "todo", args + ([] if args[0] == "undo" else
                                                                                         ["--by", by]))
            if code:
                return JSONResponse({"error": " ".join((out_ + " " + err_).split())[:300] or "the main didn't take it"},
                                    status_code=409)
            out = await asyncio.to_thread(_todo.read)
            out["said"] = " ".join(out_.split())[:300] + (" It comes back here with the sync in a moment."
                                                         if how == "main" else "")
            out["undo"] = args[0] != "undo"
            out["handed"] = how
            return JSONResponse(out, headers=_NO_CACHE)
        try:
            if isinstance(ask.get("done"), str):
                said = await asyncio.to_thread(_todo.done, ask["done"], "", by)
            elif isinstance(ask.get("letgo"), str):
                said = await asyncio.to_thread(_todo.letgo, ask["letgo"], str(ask.get("why") or "")[:500], by)
            elif isinstance(ask.get("move"), str) and isinstance(ask.get("to"), str):
                said = await asyncio.to_thread(_todo.move, ask["move"], ask["to"], by)
            elif isinstance(ask.get("tick"), str):
                said = await asyncio.to_thread(_todo.tick, ask["tick"], by)
            elif isinstance(ask.get("untick"), str):
                said = await asyncio.to_thread(_todo.untick, ask["untick"], by)
            elif isinstance(ask.get("order"), str) and isinstance(ask.get("place"), int) and ask["place"] > 0:
                said = await asyncio.to_thread(_todo.order, ask["order"], ask["place"], by)
            elif isinstance(ask.get("rename"), str) and isinstance(ask.get("title"), str):
                said = await asyncio.to_thread(_todo.rename, ask["rename"], ask["title"][:300], by)
            elif isinstance(ask.get("add"), str) and isinstance(ask.get("list"), str):
                said = await asyncio.to_thread(_todo.add, ask["list"], ask["add"][:2000], "", "", "", "", by)
            elif isinstance(ask.get("plan"), str) and isinstance(ask.get("block"), str):  # H243: by hand
                said = await asyncio.to_thread(_todo.plan, ask["plan"], ask["block"][:200], by)
            elif isinstance(ask.get("unplan"), str):
                said = await asyncio.to_thread(_todo.unplan, ask["unplan"], by)
            elif isinstance(ask.get("repeat"), str) and isinstance(ask.get("rule"), str):  # H245
                said = await asyncio.to_thread(_todo.repeat, ask["repeat"], ask["rule"][:200] or "off", by)
            elif ask.get("undo") is True:
                said = await asyncio.to_thread(_todo.undo)
            else:
                return JSONResponse({"error": "no change asked"}, status_code=400)
        except KeyError as e:
            return JSONResponse({"error": str(e).strip("'\"")}, status_code=404)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        except OSError:
            return JSONResponse({"error": "Couldn't read or write the list"}, status_code=500)
        out = await asyncio.to_thread(_todo.read)
        out["said"] = said.get("said", "")
        out["undo"] = bool(said.get("ok")) and ask.get("undo") is not True
        if said.get("id"):
            out["id"] = said["id"]  # H231: a renamed item has a new id
        return JSONResponse(out, headers=_NO_CACHE)

    # H222: the six-week games (games.py), the workspace's own HQ/games.json; a fresh install has none. The page reads
    # them and can tick a day, add to a count, write a note, a diary entry, a week's look back or the debrief, and undo
    # its last change; calls and Donna's chat do the same with the script. Making a game is the team's. Only from the
    # page itself (x-hq: games), never on a Free-only line; on the backup the main writes it (H203).
    import games as _games

    @app.get("/api/games", include_in_schema=False)
    async def games_read():
        if config.FREE_ONLY:
            return JSONResponse({"off": "Free", "games": []}, headers=_NO_CACHE)
        return JSONResponse(await asyncio.to_thread(_games.read), headers=_NO_CACHE)

    @app.post("/api/games", include_in_schema=False)
    async def games_change(request: Request):
        if request.headers.get("x-hq") != "games":
            return JSONResponse({"error": "Only the HQ page can change the games"}, status_code=403)
        if config.FREE_ONLY:
            return JSONResponse({"error": "Not on Free"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict):
            return JSONResponse({"error": "no change asked"}, status_code=400)
        g, day, by = str(ask.get("game") or ""), str(ask.get("day") or ""), "in the app"
        s = lambda k, n=4000: str(ask.get(k) or "")[:n]
        if ask.get("undo") is True:
            args = ["undo"]
        elif "tick" in ask:
            args = ["tick", s("tick", 10) or "done", "--track", s("track", 40)]
        elif "count" in ask:
            args = ["count", s("track", 40), s("count", 20)] + (["--set"] if ask.get("set") else [])
        elif "note" in ask:
            args = ["note", s("note", 2000)]
        elif "diary" in ask:
            args = ["diary", s("diary", 2000), "--feel", s("feel", 40), "--track", s("track", 40)]
        elif "week" in ask:
            args = ["week", s("week", 4), s("text")]
        elif "debrief" in ask:
            args = ["debrief", s("debrief", 6000)]
        else:
            return JSONResponse({"error": "no change asked"}, status_code=400)
        if args[0] != "undo":
            args += ["--game", g] + (["--day", day] if day and args[0] in ("tick", "count", "note") else []) + ["--by", by]
        from policy import is_backup as _is_backup
        if await asyncio.to_thread(_is_backup):
            import role as _role
            code, out_, err_, how = await asyncio.to_thread(_role.hand, "games", args)
            if code:
                return JSONResponse({"error": " ".join((out_ + " " + err_).split())[:300] or "the main didn't take it"},
                                    status_code=409)
            out = await asyncio.to_thread(_games.read)
            out["said"] = " ".join(out_.split())[:300] + (" It comes back here with the sync in a moment."
                                                         if how == "main" else "")
            out["undo"] = args[0] != "undo"
            out["handed"] = how
            return JSONResponse(out, headers=_NO_CACHE)
        code, said = await asyncio.to_thread(_games.run, args)
        said = " ".join(said.split())[:400]
        if code:
            return JSONResponse({"error": said or "Couldn't change the game"}, status_code=400)
        out = await asyncio.to_thread(_games.read)
        out["said"] = said
        out["undo"] = args[0] != "undo"
        return JSONResponse(out, headers=_NO_CACHE)

    # H225: Life coaching's own place (coaching.py): the layers with their checklist, the check-ins and which are due,
    # and the coaching line, a thread with the workflow's agent. Reading it also takes the background look (a due
    # check-in lands in the thread). Changed only from the page (x-hq: coaching): a check-in done or not now (on the
    # backup handed to the main, H203), and a text on the coaching line (what's read is kept on the device). Never on a Free-only line.
    import coaching as _coaching

    @app.get("/api/coaching", include_in_schema=False)
    async def coaching_read():
        if config.FREE_ONLY:
            return JSONResponse({"off": "Free", "on": False}, headers=_NO_CACHE)
        from policy import is_backup as _is_backup
        if not await asyncio.to_thread(_is_backup):
            try:
                await asyncio.to_thread(_coaching.refresh)
            except Exception:
                pass
        return JSONResponse(await asyncio.to_thread(_coaching.read), headers=_NO_CACHE)

    @app.post("/api/coaching", include_in_schema=False)
    async def coaching_change(request: Request):
        if request.headers.get("x-hq") != "coaching":
            return JSONResponse({"error": "Only the HQ page can change Life coaching"}, status_code=403)
        if config.FREE_ONLY:
            return JSONResponse({"error": "Not on Free"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict):
            return JSONResponse({"error": "nothing asked"}, status_code=400)
        said = ""
        if ask.get("send"):
            text = str(ask.get("send") or "").strip()[:4000]
            if not text:
                return JSONResponse({"error": "nothing to send"}, status_code=400)
            await asyncio.to_thread(_coaching.send, text)
        elif ask.get("done") or ask.get("later"):
            how = "done" if ask.get("done") else "later"
            key = str(ask.get(how) or "")[:60]
            from policy import is_backup as _is_backup
            if await asyncio.to_thread(_is_backup):
                import role as _role
                code, out_, err_, hand_how = await asyncio.to_thread(_role.hand, "coaching", [how, key])
                if code:
                    return JSONResponse({"error": " ".join((out_ + " " + err_).split())[:300] or "the main didn't take it"},
                                        status_code=409)
                said = " ".join(out_.split())[:300] + (" It comes back here with the sync in a moment."
                                                      if hand_how == "main" else "")
            else:
                said = await asyncio.to_thread(_coaching.done if how == "done" else _coaching.later, key)
        else:
            return JSONResponse({"error": "nothing asked"}, status_code=400)
        out = await asyncio.to_thread(_coaching.read)
        out["said"] = said
        return JSONResponse(out, headers=_NO_CACHE)

    # H236: their own newspaper (news.py): the items the routine on the main kept from their sources, and their setup.
    # ?id= reads one item inside HQ (its article's own text, fetched now; kept only on the main, the newspaper's one
    # writer). Changed only from the page (x-hq: news): read the sources now, on the main. Never on a Free-only line.
    import news as _news

    @app.get("/api/news", include_in_schema=False)
    async def news_read(id: str = ""):
        if config.FREE_ONLY:
            return JSONResponse({"off": "Free", "on": False}, headers=_NO_CACHE)
        if id:
            from policy import is_backup as _is_backup
            backup = await asyncio.to_thread(_is_backup)
            return JSONResponse(await asyncio.to_thread(_news.article, id[:40], None, not backup), headers=_NO_CACHE)
        return JSONResponse(await asyncio.to_thread(_news.read), headers=_NO_CACHE)

    @app.post("/api/news", include_in_schema=False)
    async def news_change(request: Request):
        if request.headers.get("x-hq") != "news":
            return JSONResponse({"error": "Only the HQ page can change the news"}, status_code=403)
        if config.FREE_ONLY:
            return JSONResponse({"error": "Not on Free"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict) or not ask.get("fetch"):
            return JSONResponse({"error": "nothing asked"}, status_code=400)
        from policy import is_backup as _is_backup
        if await asyncio.to_thread(_is_backup):
            out = await asyncio.to_thread(_news.read)
            out["said"] = "Your news is read on the main HQ; it comes over here with the sync."
            return JSONResponse(out, headers=_NO_CACHE)
        if not _news.on():
            return JSONResponse({"error": "News is off"}, status_code=409)
        r = await asyncio.to_thread(_news.fetch)
        out = await asyncio.to_thread(_news.read)
        bad = [n for n, x in r["sources"].items() if not x.get("ok")]
        out["said"] = (f"{r['new']} new." if r["new"] else "Nothing new.") + (f" Didn't answer: {', '.join(bad)}." if bad else "")
        return JSONResponse(out, headers=_NO_CACHE)

    # Job 257 (H202): the workflows the user can switch on in Settings, Life coaching first. On starts their map from
    # the blank one (never over theirs), off keeps it; the next call follows it (config.voice_rules). Only from the
    # page itself (x-hq: workflows), never on a Free-only line.
    import workflows as _wf

    def _wf_folder() -> Path:
        return Path(os.environ.get("HQ_WORKFLOWS_FOLDER") or config.FOLDER)  # the happy flows' own copy

    @app.get("/api/workflows", include_in_schema=False)
    async def workflows_read():
        if config.FREE_ONLY:
            return JSONResponse({"off": "Free", "items": []}, headers=_NO_CACHE)
        return JSONResponse({"items": _wf.listing(_wf_folder())}, headers=_NO_CACHE)

    @app.post("/api/workflows", include_in_schema=False)
    async def workflows_change(request: Request):
        if request.headers.get("x-hq") != "workflows":
            return JSONResponse({"error": "Only the HQ page can switch these"}, status_code=403)
        if config.FREE_ONLY:
            return JSONResponse({"error": "Not on Free"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict) or not isinstance(ask.get("id"), str) or not isinstance(ask.get("on"), bool):
            return JSONResponse({"error": "no change asked"}, status_code=400)
        if not _wf.find(ask["id"]):
            return JSONResponse({"error": "no such switch"}, status_code=404)
        try:
            said = await asyncio.to_thread(_wf.turn_on if ask["on"] else _wf.turn_off, _wf_folder(), ask["id"])
        except OSError:
            return JSONResponse({"error": "Couldn't write it"}, status_code=500)
        return JSONResponse({"items": _wf.listing(_wf_folder()), "said": said}, headers=_NO_CACHE)

    # H205: What HQ helps you with, every feature a switch (app/features.py). Everything on until they turn something
    # off; off takes its button away on the page. Only from the page itself (x-hq: features), never on Free-only.
    import features as _feat

    def _feat_folder() -> Path:
        return Path(os.environ.get("HQ_FEATURES_FOLDER") or config.FOLDER)  # the happy flows' own copy

    @app.get("/api/features", include_in_schema=False)
    async def features_read():
        if config.FREE_ONLY:
            return JSONResponse({"off": "Free", "items": []}, headers=_NO_CACHE)
        return JSONResponse({"items": await asyncio.to_thread(_feat.listing, _feat_folder())}, headers=_NO_CACHE)

    @app.post("/api/features", include_in_schema=False)
    async def features_change(request: Request):
        if request.headers.get("x-hq") != "features":
            return JSONResponse({"error": "Only the HQ page can switch these"}, status_code=403)
        if config.FREE_ONLY:
            return JSONResponse({"error": "Not on Free"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict) or not isinstance(ask.get("id"), str) or not isinstance(ask.get("on"), bool):
            return JSONResponse({"error": "no change asked"}, status_code=400)
        if ask["id"] not in _feat.IDS:
            return JSONResponse({"error": "no such switch"}, status_code=404)
        try:
            said = await asyncio.to_thread(_feat.switch, ask["id"], ask["on"], _feat_folder())
        except Exception:  # a file that can't be written, the mail check's jobs.py timing out
            return JSONResponse({"error": "Couldn't write it"}, status_code=500)
        return JSONResponse({"items": await asyncio.to_thread(_feat.listing, _feat_folder()), "said": said}, headers=_NO_CACHE)

    # H230: their own maps key for Driving to appointments, pasted in Settings: kept on this computer only
    # (drive.py, ~/.config/hq/maps-key), never in the workspace, never sent back. {key} keeps it, {key: ""} forgets it.
    @app.post("/api/drive/key", include_in_schema=False)
    async def drive_key(request: Request):
        if request.headers.get("x-hq") != "features":
            return JSONResponse({"error": "Only the HQ page can set the key"}, status_code=403)
        if config.FREE_ONLY:
            return JSONResponse({"error": "Not on Free"}, status_code=403)
        try:
            ask = await request.json()
        except Exception:
            ask = None
        if not isinstance(ask, dict) or not isinstance(ask.get("key"), str):
            return JSONResponse({"error": "no key"}, status_code=400)
        import drive as _drive
        try:
            if ask["key"].strip():
                await asyncio.to_thread(_drive.set_key, ask["key"], "")
                import trips as _trips
                await asyncio.to_thread(_trips.key_changed)
            else:
                await asyncio.to_thread(_drive.forget_key)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)
        return JSONResponse({"items": await asyncio.to_thread(_feat.listing, _feat_folder())}, headers=_NO_CACHE)

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
        if what not in ("start", "check", "clash-chat", "clash-team", "clash-ok") or request.headers.get("x-hq") != "update":
            return JSONResponse({"error": "Only the HQ page can start an update"}, status_code=403)
        if what.startswith("clash-"):  # H235: after an update, talk a possible clash through, send it to the team, or it's fine
            out = await asyncio.to_thread(_update, "clash", what[6:])
            return JSONResponse(out, status_code=200 if out else 500, headers=_NO_CACHE)
        if what == "check":
            await asyncio.to_thread(_update, "check", "--force")
        out = await asyncio.to_thread(_update, "start" if what == "start" else "status")
        return JSONResponse(out, status_code=200 if out else 500, headers=_NO_CACHE)

    # F25: Donna's direct line (H80) through the call line too. The phone's home-screen icon can be this
    # call page itself (8443) rather than the HQ page (8444), so its bubble, its chat and its notifications
    # have to work on this address: these few paths are passed on to the status server on this computer,
    # unchanged, the x-hq header included (only the HQ page can text her).
    import httpx as _httpx

    _STATUS = f"http://127.0.0.1:{os.environ.get('HQ_STATUS_PORT', '4748')}"
    _DIRECT = ("/direct", "/direct.json", "/direct/key", "/direct/send", "/direct/subscribe", "/direct-sw.js",
               "/hq-icon-180.png", "/hq-icon-192.png")

    async def _direct(request: Request):
        head = {k: v for k, v in request.headers.items() if k.lower() in ("x-hq", "content-type")}
        try:
            async with _httpx.AsyncClient(timeout=90) as cl:
                r = await cl.request(request.method, _STATUS + request.url.path, headers=head,
                                     content=await request.body())
        except _httpx.HTTPError:
            return Response("The direct line can't be reached right now", status_code=502, media_type="text/plain")
        keep = {k: v for k, v in r.headers.items() if k.lower() in ("content-type", "cache-control")}
        return Response(r.content, status_code=r.status_code, headers=keep)

    for _path in _DIRECT:
        app.add_api_route(_path, _direct, methods=["GET", "POST"] if _path.startswith("/direct/") else ["GET"],
                          include_in_schema=False)

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
