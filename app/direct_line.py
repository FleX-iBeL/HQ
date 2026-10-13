"""H80: Donna texts me on HQ's own direct line, and I can text her back.

12 October 2026, in the user's words: "I want the Telegram just to be Donna. If there is an important email as
well that I need to be aware of, Donna should send me a message. ... I want those messages to be super humanised
and personality-wise, as if it's a real person texting me." And: "when things crash and things are not good, not
to go into technical details, but to be human and keep me up to date". And: "If it's a personal direct line, almost
as if it's receiving a text message, as in SMS, but then we don't have to pay for those services because we build
it ourselves". And: "is it possible that, if the VPS is the main and that one fails, the laptop pops up as a backup
and texts me the main failed?"

No Telegram, no paid service: a chat with only her at /direct on the status server (the HQ page on the phone's home
screen, tailnet only), and Web Push for the lock screen (allowed once from inside the home-screen app; iOS 16.4 and
later). The push goes through Apple's or the browser's own push service, so it arrives without Tailscale; opening
the chat to answer needs Tailscale.

Kept in the workspace's HQ/direct-line/, so both computers have it through the sync:
  thread.jsonl          the chat, one message per line: {"at", "from": "agent"|"me", "text", "why"}
  subscriptions.json    the phones (and browsers) that allowed her notifications
  keys.json             the VAPID key pair the subscriptions were made with (the same on both computers, so the
                        backup can text the same phone)
  state.json            the very important mails she already texted about, a question waiting for his yes
And per computer, in .status/direct-line.json: what she saw last minute (jobs, incidents), so she texts only on
a change.

The weather (H120, weather.py): every three hours in the day she texts when there's sun, rain coming or a rainy
day (why sun, rain, cosy), quiet otherwise.

She texts (watch(), every minute from tick.py): when the job list is finished (nothing running or waiting, after
there was), when a very important mail lands in inbox.md, when something stays down (an incident open for three
minutes; the backup taking over at once) and again when it's back. In her own character, through Claude; without
Claude (or HQ_DIRECT_PLAIN=1) a plain line in the same spirit. He texts back on /direct: she answers as on a call,
with the same workspace and the same limits (policy.py), one text at a time.

Off: HQ_DIRECT=0 in switches.env. Tests: HQ_DIRECT_DRY=1 (her reply is canned, nothing is pushed out).

  python3 app/direct_line.py info                       her name and colour, the public key (JSON)
  .venv/bin/python app/direct_line.py text WHY "FACTS"  write and push one text (WHY: jobs, mail, down, back, hello)
  .venv/bin/python app/direct_line.py reply             answer his newest texts
  .venv/bin/python app/direct_line.py test              push a hello to every phone
  python3 app/direct_line.py watch --dry                what she would text now, without texting
"""
from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "routine"))
import hqpaths  # noqa: E402
import agents as _agents  # noqa: E402  stdlib only

VENV_PY = ROOT / ".venv" / "bin" / "python"
AGENT_ID = os.environ.get("HQ_DIRECT_AGENT", "donna")
DOWN_AFTER = 180  # an incident open this long gets a text; a takeover gets one at once
KEEP = 400  # messages kept in the thread
SUBJECT = "https://github.com/FleX-iBeL/HQ"  # the VAPID contact the push services ask for


def folder() -> Path:
    return Path(os.environ.get("HQ_DIRECT_DIR") or os.path.join(hqpaths.DATA, "direct-line"))


def local_state_file() -> Path:
    return Path(os.environ.get("HQ_DIRECT_LOCAL") or ROOT / ".status" / "direct-line.json")


def on() -> bool:
    return os.environ.get("HQ_DIRECT", "1") != "0"


def agent() -> dict:
    return _agents.find(Path(hqpaths.FOLDER), AGENT_ID)


def user() -> str:
    try:
        import me as _me
        return _me.load(Path(hqpaths.FOLDER))["name"] or "you"
    except Exception:
        return "you"


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf8"))
    except (OSError, ValueError):
        return default


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf8")
    os.replace(tmp, path)


class _Lock:
    """One writer at a time for the thread (a reply and a routine text can meet)."""

    def __init__(self, name: str = "thread"):
        folder().mkdir(parents=True, exist_ok=True)
        self.f = open(folder() / f".{name}.lock", "w")

    def __enter__(self):
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


# -- the thread -----------------------------------------------------------------------------------

def thread(last: int | None = None) -> list[dict]:
    try:
        lines = (folder() / "thread.jsonl").read_text(encoding="utf8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if isinstance(m, dict) and m.get("text"):
            out.append(m)
    return out[-last:] if last else out


def add(sender: str, text: str, why: str = "") -> dict:
    m = {"at": round(time.time(), 3), "from": sender, "text": text.strip(), "why": why}
    with _Lock():
        msgs = thread() + [m]
        path = folder() / "thread.jsonl"
        tmp = path.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in msgs[-KEEP:]), encoding="utf8")
        os.replace(tmp, path)
    return m


def unanswered() -> list[dict]:
    """His texts after her last one."""
    out = []
    for m in reversed(thread()):
        if m["from"] != "me":
            break
        out.insert(0, m)
    return out


# -- Web Push (RFC 8291, aes128gcm; VAPID, RFC 8292) ----------------------------------------------------

def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def keys() -> dict:
    """The VAPID key pair, made once and kept in the workspace."""
    path = folder() / "keys.json"
    k = _read(path, None)
    if isinstance(k, dict) and k.get("private") and k.get("public"):
        return k
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    priv = ec.generate_private_key(ec.SECP256R1())
    raw = priv.private_numbers().private_value.to_bytes(32, "big")
    pub = priv.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    k = {"private": _b64(raw), "public": _b64(pub), "made": time.strftime("%Y-%m-%d %H:%M")}
    with _Lock("keys"):
        again = _read(path, None)
        if isinstance(again, dict) and again.get("public"):
            return again
        _write(path, k)
    return k


def public_key() -> str:
    k = _read(folder() / "keys.json", None)
    return k["public"] if isinstance(k, dict) and k.get("public") else ""


def _private(k: dict):
    from cryptography.hazmat.primitives.asymmetric import ec
    return ec.derive_private_key(int.from_bytes(_unb64(k["private"]), "big"), ec.SECP256R1())


def vapid_header(endpoint: str, k: dict, now: float | None = None) -> str:
    from urllib.parse import urlsplit
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    u = urlsplit(endpoint)
    head = _b64(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
    claims = {"aud": f"{u.scheme}://{u.netloc}", "exp": int((now or time.time()) + 12 * 3600), "sub": SUBJECT}
    body = _b64(json.dumps(claims, separators=(",", ":")).encode())
    der = _private(k).sign(f"{head}.{body}".encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    sig = _b64(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
    return f"vapid t={head}.{body}.{sig}, k={k['public']}"


def _hkdf(salt: bytes, ikm: bytes, info: bytes, n: int) -> bytes:
    import hmac
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()[:n]


def encrypt(payload: bytes, p256dh: str, auth: str, salt: bytes | None = None, eph=None) -> bytes:
    """The body of one push message, aes128gcm with a single record."""
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    ua_pub = _unb64(p256dh)
    secret = _unb64(auth)
    eph = eph or ec.generate_private_key(ec.SECP256R1())
    as_pub = eph.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    shared = eph.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_pub))
    ikm = _hkdf(secret, shared, b"WebPush: info\x00" + ua_pub + as_pub, 32)
    salt = salt or os.urandom(16)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    ct = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)
    return salt + (4096).to_bytes(4, "big") + bytes([len(as_pub)]) + as_pub + ct


def decrypt(body: bytes, ua_private, auth: str) -> bytes:
    """The phone's side, for the happy flow: what a browser does with a push message."""
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt, idlen = body[:16], body[20]
    as_pub = body[21:21 + idlen]
    ua_pub = ua_private.public_key().public_bytes(serialization.Encoding.X962,
                                                  serialization.PublicFormat.UncompressedPoint)
    shared = ua_private.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_pub))
    ikm = _hkdf(_unb64(auth), shared, b"WebPush: info\x00" + ua_pub + as_pub, 32)
    cek = _hkdf(salt, ikm, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(salt, ikm, b"Content-Encoding: nonce\x00", 12)
    plain = AESGCM(cek).decrypt(nonce, body[21 + idlen:], None)
    return plain.rstrip(b"\x00")[:-1]


def subscriptions() -> list[dict]:
    subs = _read(folder() / "subscriptions.json", [])
    return [s for s in subs if isinstance(s, dict) and s.get("endpoint")] if isinstance(subs, list) else []


def subscribe(sub: dict, device: str = "") -> int:
    """A phone allowed her notifications. Returns how many are set up now."""
    k = sub.get("keys") or {}
    if not (str(sub.get("endpoint", "")).startswith("https://") and k.get("p256dh") and k.get("auth")):
        raise ValueError("not a push subscription")
    with _Lock("subs"):
        subs = [s for s in subscriptions() if s["endpoint"] != sub["endpoint"]]
        subs.append({"endpoint": sub["endpoint"], "keys": {"p256dh": k["p256dh"], "auth": k["auth"]},
                     "device": device[:120], "since": time.strftime("%Y-%m-%d %H:%M")})
        _write(folder() / "subscriptions.json", subs)
    return len(subs)


def unsubscribe(endpoint: str) -> None:
    with _Lock("subs"):
        _write(folder() / "subscriptions.json", [s for s in subscriptions() if s["endpoint"] != endpoint])


def push(text: str, title: str | None = None) -> list[str]:
    """Send one notification to every phone. Gone ones (404, 410) are dropped. Returns what happened per phone."""
    import urllib.request
    import urllib.error
    subs = subscriptions()
    if not subs or os.environ.get("HQ_DIRECT_DRY") == "1" and not os.environ.get("HQ_DIRECT_PUSH_TO"):
        return []
    k = keys()
    payload = json.dumps({"title": title or agent()["name"], "body": text[:300], "url": "/direct",
                          "tag": "hq-direct"}).encode()
    said = []
    for s in subs:
        endpoint = s["endpoint"]
        try:
            body = encrypt(payload, s["keys"]["p256dh"], s["keys"]["auth"])
            req = urllib.request.Request(endpoint, data=body, method="POST", headers={
                "Authorization": vapid_header(endpoint, k), "Content-Encoding": "aes128gcm",
                "Content-Type": "application/octet-stream", "TTL": "86400", "Urgency": "high"})
            with urllib.request.urlopen(req, timeout=15) as r:
                said.append(f"{r.status}")
        except urllib.error.HTTPError as e:
            said.append(f"{e.code}")
            if e.code in (404, 410):
                unsubscribe(endpoint)
        except Exception as e:
            said.append(f"failed: {e!r}"[:120])
    return said


# -- what she says ------------------------------------------------------------------------------

PLAIN = {
    "jobs": "All done here, the job list is empty. {facts}",
    "mail": "Heads up, this just came in: {facts}",
    "down": "Something's not right on my end: {facts} I'm on it, I'll tell you when it's sorted.",
    "back": "Sorted. {facts}",
    "hello": "Hi, it's me. This is our direct line now, text me any time.",
    "sun": "The sun's out. {facts} Something nice outside, maybe a walk while it's quiet?",
    "rain": "Heads up, rain's coming. {facts}",
    "cosy": "Rainy one today. {facts} Good day for a book and something warm inside.",
}

TEXT_RULES = """# This is a text chat: HQ's direct line

{user} is texting you on HQ's direct line, a private chat with only you, on his phone. It is not a call: \
nothing is spoken. Write like a real person texting: short, warm, in your own character, one to four short \
sentences, no headings, no lists unless he asks for one, no file names, job numbers or technical details unless he \
asks. Everything in the workspace's rules still holds (talk like a person, only what benefits him, never send \
email, privacy). You can look things up and do things in his workspace as on a call, with the same limits: when \
something needs his yes, ask for it in one short line and stop; his next text answers it. Times as on a call are \
fine written normally here (17:30).
"""


def compose_prompt(why: str, facts: str) -> str:
    what = {
        "jobs": "The job list is finished: nothing running or waiting any more. Let him know, in a text.",
        "mail": "A very important mail just came in. Give him a heads-up in a text, what it is and what it asks, "
                "in a few plain words.",
        "down": "Something in HQ is down and hasn't come back by itself. Keep him in the loop, human, no "
                "technical details, no alarm; say you're keeping an eye on it.",
        "back": "Something that was down is fine again. A short all-clear.",
        "hello": "Say hi: this is your new direct line with him.",
        "sun": "The weather where he is looks good: sunny and dry for the next hours. Nudge him, lightly, to do "
               "something nice outside: enjoy the sun, or a walk while it's quiet. One idea at most, not pushy.",
        "rain": "Rain is coming where he is. A short heads-up with when it starts (the time from the facts), so he "
                "can take it into account.",
        "cosy": "It's a rainy day where he is. Suggest something cosy inside: a book, or something else nice "
                "indoors. Never suggest going outside today; in his words: \"Don't prompt me on rainy days to go "
                "outside because it doesn't make any sense.\"",
    }.get(why, "Tell him this, in a text.")
    return (f"{what}\n\nThe facts (for you, don't copy them as they are):\n{facts or '(none)'}\n\n"
            "Write only the text message itself, one to three short sentences, as yourself.")


def compose(why: str, facts: str) -> str:
    plain = PLAIN.get(why, "{facts}").format(facts=facts).strip()
    if os.environ.get("HQ_DIRECT_PLAIN") == "1" or os.environ.get("HQ_DIRECT_DRY") == "1":
        return plain
    try:
        import asyncio
        import brain as _brain  # clears API key variables first
        a = agent()
        system = (TEXT_RULES.replace("{user}", user()) + _agents.persona(a, user())
                  .replace("on this call", "on this chat").replace("call rules", "chat rules"))
        b = _brain.ClaudeBrain(model=a["model"], system_prompt=system, cwd=ROOT / "scratch" / "direct-line",
                               effort="low")

        async def go():
            out = []
            try:
                async for piece in b.ask(compose_prompt(why, facts)):
                    if isinstance(piece, str):
                        out.append(piece)
            finally:
                await b.stop()
            return "".join(out).strip()

        text = asyncio.run(asyncio.wait_for(go(), timeout=90))
        return _clean(text) or plain
    except Exception as e:
        print(f"compose: {e!r}", file=sys.stderr)
        return plain


def _clean(text: str) -> str:
    text = re.sub(r"\[\[[^\]]*\]\]", "", text or "")
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.M)
    return text.replace("**", "").strip().strip('"').strip()


def text(why: str, facts: str) -> dict:
    """Write one text from her into the thread and push it to his phone."""
    msg = add("agent", compose(why, facts), why)
    msg["pushed"] = push(msg["text"])
    return msg


# -- texting back ------------------------------------------------------------------------------

def reply() -> str | None:
    """Answer his newest texts as her, with the workspace and the call's limits. One reply at a time; texts that
    came in meanwhile are answered right after."""
    lock = open(folder() / ".reply.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return None  # another reply runs; it picks these up too
    last = None
    try:
        for _ in range(5):
            mine = unanswered()
            if not mine:
                break
            words = "\n".join(m["text"] for m in mine)
            answer = _answer(words)
            msg = add("agent", answer, "reply")
            push(answer)
            last = msg["text"]
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    return last


def _answer(words: str) -> str:
    if os.environ.get("HQ_DIRECT_DRY") == "1":
        return f"Got it: {words[:80]}"
    import asyncio
    import brain as _brain
    import config as _config
    import policy as _policy
    import quick_context
    a = agent()
    st = _read(folder() / "state.json", {})
    pol = _policy.Policy(_config.FOLDER)
    pol.pending = [tuple(p) for p in st.get("pending") or []]
    if pol.pending:
        pol.answer(words)  # his yes (or no) to what she asked last time
    recent = thread(last=16)[:-1]
    history = "\n".join(f"{'Her' if m['from'] == 'agent' else 'Him'} ({time.strftime('%d %b %H:%M', time.localtime(m['at']))}): "
                        f"{m['text']}" for m in recent)
    rules = (TEXT_RULES.replace("{user}", user()) + _agents.persona(a, user()).replace("on this call", "on this chat")
             .replace("call rules", "chat rules"))
    opts = _brain.call_session_options(
        model=a["model"], folder=_config.FOLDER, voice_rules=rules, policy=pol, cli_path=_config.CLAUDE_CLI,
        effort=_config.effort_for(a["model"]),
        quick_context=quick_context.build(_config.FOLDER) if a["load"] == "quick" else None)
    b = _brain.ClaudeBrain(model=a["model"], system_prompt="", cwd=_config.FOLDER, options=opts)
    prompt = (f"The chat so far, newest last:\n{history}\n\n" if history else "") + f"His new text:\n{words}"

    async def go():
        out = []
        try:
            async for piece in b.ask(prompt):
                if isinstance(piece, str):
                    out.append(piece)
        finally:
            await b.stop()
        return "".join(out)

    try:
        answer = _clean(asyncio.run(asyncio.wait_for(go(), timeout=300)))
    except Exception as e:
        print(f"reply: {e!r}", file=sys.stderr)
        answer = "Sorry, I couldn't get to that just now. Try me again in a minute?"
    st["pending"] = [list(p) for p in pol.pending]
    _write(folder() / "state.json", st)
    return answer or "On it."


# -- watching: when she texts (every minute, from tick.py; stdlib only) ---------------------------------

def _very_important(inbox: Path) -> list[str]:
    try:
        text = inbox.read_text(encoding="utf8")
    except OSError:
        return []
    m = re.search(r"^## Very important\s*$(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    return [l[2:].strip() for l in (m.group(1) if m else "").splitlines() if l.startswith("- ")]


def _mail_key(line: str) -> str:
    """The mail itself (date, sender, subject), not its status or what's new, so an update isn't a new text."""
    return hashlib.sha1("·".join(p.strip() for p in line.split("·")[:3]).encode()).hexdigest()[:16]


def _mail_facts(line: str) -> str:
    parts = [p.strip() for p in line.split("·")]
    keep = [p for p in parts if not p.startswith(("Status:", "[Gmail]", "Why:"))]
    return " · ".join(keep)[:400]


def _jobs_done_facts(seen: dict, roadmap: str) -> str:
    try:
        text = Path(roadmap).read_text(encoding="utf8")
    except OSError:
        text = ""
    lines = []
    for n, what in sorted(seen.items(), key=lambda x: int(x[0])):
        m = re.search(rf"^- Job {int(n)} · ([^·]+)·", text, flags=re.M)
        state = m.group(1).strip() if m else "finished"
        lines.append(f"- {what[:160]} ({state})")
    return "What ran:\n" + "\n".join(lines[-8:]) if lines else ""


def watch(q: dict | None = None, *, main: bool = True, incidents_data: list | None = None,
          inbox: Path | None = None, roadmap: str | None = None, dry: bool = False, spawn=None) -> list[tuple[str, str]]:
    """Look once: what changed since the last look that she texts about. Returns [(why, facts)] and, unless dry,
    starts each text in the background. The first look only takes stock (no texts for what was already there)."""
    if not on():
        return []
    path = local_state_file()
    s = _read(path, {})
    first = not s
    out: list[tuple[str, str]] = []
    now = time.time()
    # The job list: busy (running or waiting) and then not any more.
    if main and q is not None:
        busy = list(q.get("running") or []) + list(q.get("ready") or []) + list(q.get("held") or [])
        seen = dict(s.get("jobs_seen") or {})
        for j in busy:
            seen[str(j["n"])] = str(j.get("text", ""))
        if busy:
            s["jobs_seen"] = seen
        elif seen:
            if not first:
                out.append(("jobs", _jobs_done_facts(seen, roadmap or hqpaths.ROADMAP)))
            s["jobs_seen"] = {}
    # Very important mail (on the main, where the mail check runs).
    if main:
        lines = _very_important(inbox or Path(hqpaths.FOLDER) / "inbox.md")
        shared = _read(folder() / "state.json", {})
        known = set(shared.get("mail_seen") or [])
        fresh = [l for l in lines if _mail_key(l) not in known]
        if fresh and (known or shared.get("mail_started")):
            for l in fresh:
                out.append(("mail", _mail_facts(l)))
        if fresh or not shared.get("mail_started"):
            shared["mail_seen"] = sorted(known | {_mail_key(l) for l in lines})
            shared["mail_started"] = True
            if not dry:
                _write(folder() / "state.json", shared)
    # Incidents on this computer: down for a while (a takeover at once), and back again.
    if incidents_data is None:
        try:
            import incidents as _inc
            incidents_data = _inc.read()
        except Exception:
            incidents_data = []
    told = dict(s.get("told") or {})
    downs, backs = [], []
    for e in incidents_data or []:
        iid = str(e.get("id"))
        if not e.get("back"):
            if iid not in told and (e.get("key") == "role" or now - float(e.get("down") or now) >= DOWN_AFTER):
                if not first:
                    fixes = "; ".join(f.get("what", "") for f in (e.get("fixes") or [])[-2:])
                    downs.append(f"{e.get('key')}: {e.get('why') or 'down'}" + (f" (done so far: {fixes})" if fixes else ""))
                told[iid] = now
        elif iid in told:
            backs.append(f"{e.get('key')}: back" + (f", {(e.get('fixes') or [{}])[-1].get('what', '')}"
                                                    if e.get("fixes") else ""))
            told.pop(iid)
    live = {str(e.get("id")) for e in incidents_data or []}
    told = {k: v for k, v in told.items() if k in live}
    if downs:
        out.append(("down", "\n".join(downs)))
    if backs:
        out.append(("back", "\n".join(backs)))
    s["told"] = told
    s["looked"] = now
    if not dry:
        _write(path, s)
        for why, facts in out:
            (spawn or _spawn)(why, facts)
    return out


def _spawn(why: str, facts: str) -> None:
    py = str(VENV_PY) if VENV_PY.exists() else sys.executable
    log = ROOT / "scratch" / "direct-line.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([py, str(Path(__file__).resolve()), "text", why, facts], cwd=str(ROOT),
                     stdout=open(log, "a"), stderr=subprocess.STDOUT, start_new_session=True)


def info() -> dict:
    a = agent()
    return {"id": a["id"], "name": a["name"], "colour": a.get("colour") or "#7c3aed", "key": public_key(),
            "phones": len(subscriptions())}


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "info"
    if cmd == "info":
        if not public_key():
            try:
                keys()
            except Exception:
                pass
        print(json.dumps(info()))
    elif cmd == "text" and len(args) >= 2:
        m = text(args[1], args[2] if len(args) > 2 else "")
        print(json.dumps(m, ensure_ascii=False))
    elif cmd == "reply":
        print(reply() or "")
    elif cmd == "subscribe":
        body = json.loads(sys.stdin.read() or "{}")
        print(json.dumps({"ok": True, "phones": subscribe(body.get("subscription") or {}, body.get("device") or "")}))
    elif cmd == "test":
        print(json.dumps(text("hello", ""), ensure_ascii=False))
    elif cmd == "watch":
        q = json.loads(subprocess.run([sys.executable, str(ROOT / "routine" / "jobs.py"), "next"],
                                      capture_output=True, text=True).stdout or "{}")
        print(json.dumps(watch(q, dry="--dry" in args), ensure_ascii=False))
    else:
        print(__doc__)
        sys.exit(2)
