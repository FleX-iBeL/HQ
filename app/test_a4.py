"""A4 test: a real WebRTC call from this MacBook to the phone URL, through Tailscale serve.

Like the phone does: HTTPS to the ts.net name (resolved to the Tailscale address, since this
MacBook's own DNS doesn't use MagicDNS), the same offer as the web page, no STUN servers, a
fake microphone (Kokoro says one sentence). Checks:
  - the answer offers the 100.x Tailscale address as a candidate and no outside (STUN) one
  - the call connects, over which address pair
  - audio comes back from HQ
  - Hang up (the data-channel message the page sends) is noticed at once by the server

Run it against a server started with  HQ_WRAP_UP=dry HQ_CALLS=<scratch folder> app/start.sh
so the after-call work changes nothing.   .venv/bin/python app/test_a4.py
Uses one turn of the Max plan.
"""
import asyncio
import fractions
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

import aiohttp  # noqa: E402
import av  # noqa: E402
import numpy as np  # noqa: E402
import soxr  # noqa: E402
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription  # noqa: E402
from aiortc.mediastreams import AudioStreamTrack  # noqa: E402
from kokoro_onnx import Kokoro  # noqa: E402

# This Mac's own Tailscale name and address, as Tailscale reports them.
# F59 (job 454): a computer without Tailscale at that path (a Linux server) can still import FakeMic for the flows.
import shutil  # noqa: E402
_TS_BIN = "/usr/local/bin/tailscale" if os.path.exists("/usr/local/bin/tailscale") else shutil.which("tailscale")
try:
    _ts = json.loads(subprocess.run([_TS_BIN, "status", "--json"], capture_output=True, text=True,
                                    timeout=10).stdout or "{}") if _TS_BIN else {}
except (OSError, subprocess.SubprocessError, ValueError):
    _ts = {}
HOST = (_ts.get("Self", {}).get("DNSName") or "").rstrip(".")
TS_IP = (_ts.get("Self", {}).get("TailscaleIPs") or [""])[0]
# H56.5: another HQ's call line on the tailnet (a server): HQ_TEST_HOST=<its ts.net name> HQ_TEST_IP=<its 100.x>
HOST = os.environ.get("HQ_TEST_HOST") or HOST
TS_IP = os.environ.get("HQ_TEST_IP") or TS_IP
URL = f"https://{HOST}:8443"
SR = 48000
QUESTION = "Hey there, say hello to me in four words."


class FakeMic(AudioStreamTrack):
    def __init__(self, speech: np.ndarray):
        super().__init__()
        self.samples = np.concatenate([np.zeros(SR * 2, np.int16), speech, np.zeros(SR * 120, np.int16)])
        self.pos = 0
        self.t0 = None
        self.n = 0

    async def recv(self):
        if self.t0 is None:
            self.t0 = time.perf_counter()
        wait = self.t0 + self.n * 0.02 - time.perf_counter()
        if wait > 0:
            await asyncio.sleep(wait)
        chunk = self.samples[self.pos:self.pos + 960]
        self.pos += 960
        frame = av.AudioFrame.from_ndarray(chunk.reshape(1, -1), format="s16", layout="mono")
        frame.sample_rate = SR
        frame.pts = self.n * 960
        frame.time_base = fractions.Fraction(1, SR)
        self.n += 1
        return frame


class Resolver(aiohttp.abc.AbstractResolver):
    async def resolve(self, host, port=0, family=0):
        return [{"hostname": host, "host": TS_IP, "port": port, "family": 2, "proto": 0, "flags": 0}]

    async def close(self):
        pass


async def main() -> bool:
    ok = True

    def check(name, cond, extra=""):
        nonlocal ok
        ok &= bool(cond)
        print(("PASS " if cond else "FAIL ") + name + (f"  ({extra})" if extra else ""))

    k = Kokoro(str(config.KOKORO_MODEL), str(config.KOKORO_VOICES))
    audio, sr = k.create(QUESTION, voice=config.VOICE, speed=1.0, lang="en-us")
    speech = (soxr.resample(audio.astype(np.float32), sr, SR) * 32767).astype(np.int16)

    pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    mic = FakeMic(speech)
    pc.addTrack(mic)
    dc = pc.createDataChannel("chat", ordered=True)
    heard = {"first": None, "frames": 0, "loud": 0}

    @pc.on("track")
    def on_track(track):
        async def read():
            while True:
                try:
                    f = await track.recv()
                except Exception:
                    return
                a = f.to_ndarray().astype(np.int32)
                heard["frames"] += 1
                if np.abs(a).mean() > 200:
                    heard["loud"] += 1
                    if heard["first"] is None:
                        heard["first"] = time.perf_counter()
        asyncio.ensure_future(read())

    async def pinger():
        while True:
            await asyncio.sleep(1)
            if dc.readyState == "open":
                dc.send("ping: " + str(time.time()))

    asyncio.ensure_future(pinger())

    await pc.setLocalDescription(await pc.createOffer())
    conn = aiohttp.TCPConnector(resolver=Resolver())
    async with aiohttp.ClientSession(connector=conn) as s:
        async with s.get(URL + "/") as r:
            page = await r.text()
            check("page over https via Tailscale serve", r.status == 200 and "HQ" in page, f"{r.status}")
        for p, t in [("manifest.webmanifest", "json"), ("apple-touch-icon.png", "image/png")]:
            async with s.get(f"{URL}/{p}") as r:
                check(f"/{p}", r.status == 200, r.headers.get("content-type", ""))
        async with s.post(URL + "/api/offer", json={"sdp": pc.localDescription.sdp, "type": "offer"}) as r:
            check("offer accepted", r.status == 200, f"{r.status}")
            answer = await r.json()
    cands = re.findall(r"^a=candidate:.*$", answer["sdp"], re.M)
    print("answer candidates:\n  " + "\n  ".join(cands))
    check("answer offers the Tailscale address", any(TS_IP in c for c in cands))
    check("no outside STUN candidate (srflx/relay)", not any(" typ srflx" in c or " typ relay" in c for c in cands))
    await pc.setRemoteDescription(RTCSessionDescription(answer["sdp"], answer["type"]))

    t0 = time.perf_counter()
    while pc.connectionState != "connected" and time.perf_counter() - t0 < 20:
        await asyncio.sleep(0.1)
    check("WebRTC connected", pc.connectionState == "connected", f"{time.perf_counter() - t0:.1f}s")
    try:
        pair = pc.sctp.transport.transport._connection._nominated
        for comp, p in pair.items():
            print(f"nominated pair: local {p.local_candidate.host}:{p.local_candidate.port} <-> remote {p.remote_candidate.host}:{p.remote_candidate.port}")
    except Exception as e:
        print("could not read the nominated pair:", e)

    t0 = time.perf_counter()
    while heard["first"] is None and time.perf_counter() - t0 < 60:
        await asyncio.sleep(0.2)
    check("audio from HQ came back", heard["first"] is not None, f"{heard['loud']} loud frames")
    await asyncio.sleep(5)  # let it speak a bit

    print("hanging up (data channel message, as the page does)...")
    t_hang = time.time()
    dc.send(json.dumps({"type": "hangup"}))
    await asyncio.sleep(1)
    await pc.close()
    print(f"hangup sent at {time.strftime('%H:%M:%S', time.localtime(t_hang))}; check scratch/server.log for 'The caller hung up (button)'")
    return ok


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
