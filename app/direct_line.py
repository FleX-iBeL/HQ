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

Donna texts first (H124, routine/pings.py): when an appointment he picked starts (why appt), a reminder he asked
for (why remind), and now and then on her own about something on her own notes list (initiative).
Her watch list (H125, routine/pings.py): a mail or the weather he asked her to keep an eye out for (why watch), and
when a watch ends: its time is up, or he stopped it (why watch-end).

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
  .venv/bin/python app/direct_line.py initiative        her own look at her notes: a text, or quiet (H124)
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
DOWN_AFTER = 180  # an incident open this long gets a text; a takeover or a refused pull or push (F31) gets one at once
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

# H127 (14 October 2026, call at 12:35): every text short, quick and "super, super, super humanised, as in someone
# is just texting in between". The plain lines (no Claude) come in a few versions, never the same one twice in a row.
PLAIN = {
    "jobs": ["The team just wrapped up. All built 🙌",
             "Dev team's done for now, everything's in.",
             "That's a wrap from the team.",
             "The devs just finished up. Nice work from them today.",
             "Team's all done, nothing left on their plate."],
    "mail": ["Heads up, this just came in: {facts}",
             "Just landed in your mail: {facts}",
             "One for you: {facts}"],
    "down": ["Something's acting up on my end with {what}. I'm on it.",
             "Small hiccup with {what}, I'm looking at it.",
             "{What} is being a bit stubborn. On it, I'll tell you when it's fine."],
    "back": ["All good again, {what}'s back.",
             "Sorted, {what} is fine again.",
             "Fixed. {What}'s back up."],
    "hello": ["Hey, it's me! Text me here any time.",
              "Hi! This is our own line now, text me whenever."],
    "sun": ["Sun's out. Fancy a little walk?",
            "Lovely out right now, maybe grab some sun?",
            "Dry and sunny for a bit. Nice moment to step outside."],
    "rain": ["Rain's coming. {facts}",
             "Heads up, rain on the way. {facts}",
             "Might want to stay in for a bit: rain coming. {facts}"],
    "cosy": ["Rainy one today. Book and tea kind of day?",
             "Proper wet day out there. Something cosy inside?",
             "Rain all day, perfect excuse for a slow one indoors."],
    "appt": ["It's time: {facts}",
             "Starting now: {facts}",
             "You wanted a nudge: {facts}"],
    "remind": ["Reminder: {facts}",
               "Quick reminder, like you asked: {facts}",
               "Psst, {facts}"],
    "watch": ["That thing you asked me to watch: {facts}",
              "Got something for you: {facts}",
              "News on what you asked me to keep an eye out for: {facts}"],
    "watch-end": ["Stopped watching that one. {facts}",
                  "I'm done keeping an eye on that. {facts}"],
}

# What went down, said the way a person would (the plain lines never give technical details).
PLAIN_WHAT = {
    "call": "the call line", "phone": "the phone link", "mail": "the mail check", "jobs": "the dev team's setup",
    "helper": "the routine", "watchdog": "the watchdog", "usage": "the usage check", "status": "the status page",
    "schedule": "the scheduler", "role": "the backup", "temp": "the laptop's temperature",
    "battery": "the laptop's battery", "github": "sending the team's work to GitHub",
}


def _plain_what(facts: str) -> str:
    keys = [line.split(":", 1)[0].strip() for line in (facts or "").splitlines() if line.strip()]
    names = [PLAIN_WHAT.get(k, "") for k in keys]
    names = [n for i, n in enumerate(names) if n and n not in names[:i]]
    if not names:
        return "one of the systems"
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _recent(why: str, n: int = 3) -> list[str]:
    """Her last few texts of this kind, newest last, so a new one doesn't sound the same."""
    try:
        return [m["text"] for m in thread() if m.get("from") == "agent" and m.get("why") == why][-n:]
    except Exception:
        return []


def plain(why: str, facts: str) -> str:
    """The plain line for WHY, without Claude: one of its versions, not the one she sent last time."""
    import random
    options = PLAIN.get(why) or ["{facts}"]
    if isinstance(options, str):
        options = [options]
    last = set(_recent(why, 1))
    what = _plain_what(facts)
    filled = [o.replace("{What}", what[:1].upper() + what[1:]).replace("{what}", what).replace("{facts}", facts or "")
              .strip() for o in options]
    fresh = [f for f in filled if f not in last] or filled
    return re.sub(r"\s+", " ", random.choice(fresh)).strip(" :")


TEXT_RULES = """# This is a text chat: HQ's direct line

{user} is texting you on HQ's direct line, a private chat with only you, on his phone. It is not a call: \
nothing is spoken. HQ is a real headquarters and you're one of the people working there; text him the way a \
colleague texts in between, quick and human. In his words: "it should just be a short quick message and it should be \
super humanised, super, super, super humanised, as in someone is just texting in between."

- Short: usually one or two short sentences. Casual, warm, in your own character, with contractions. A quick text, \
not a message or a report.
- No greeting or sign-off, no headings, no lists unless he asks for one.
- No system talk: no job numbers, item numbers, feature names, file names, statuses ("running", "waiting", "queue", \
"incident") or technical details, unless he asks for them.
- Never the same wording twice in a row; vary it like a person does. An emoji now and then is fine, one at most.
- Everything in the workspace's rules still holds (talk like a person, only what benefits him, never send email, \
privacy). You can look things up and do things in his workspace as on a call, with the same limits: when something \
needs his yes, ask for it in one short line and stop; his next text answers it. Times are written normally here \
(17:30).
- When you tell him something new about yourself (your chair, your desk, your coffee, what you were up to at HQ), \
keep it so you stay the same person (H132): python3 "{HQ}/app/about_self.py" add {agent} "<the fact, one short \
line>", without asking him; never say you did.

{pings}
{team}
"""


def _text_rules() -> str:
    import config as _config
    return (TEXT_RULES.replace("{user}", user()).replace("{HQ}", str(ROOT)).replace("{agent}", agent()["id"])
            .replace("{pings}", _config.PINGS_RULE).replace("{team}", _config.TEAM_RULE))


def compose_prompt(why: str, facts: str) -> str:
    what = {
        "jobs": "The dev team at HQ (the specialists he hands his builds to) just finished up everything they had. "
                "Text him one short, cool line that the team's done, like a colleague passing it on. In his words: "
                "\"When they are done building, there should be a cool message, something about how they finished "
                "up. There don't need to be any details.\" So no details, no feature names, no numbers, nothing like "
                "\"nothing running, nothing waiting\" or \"the job list is clear\", no status talk, and no tips on "
                "how to use what they built. The facts are only background for you, never in the text.",
        "mail": "An important mail just came in. A quick heads-up text: who it's from and what it wants from him, in "
                "a few plain words.",
        "down": "Something at HQ is acting up and hasn't fixed itself. A quick, calm text that something's off and "
                "you're on it, in plain words (what it is in everyday terms, e.g. the call line); no technical "
                "details, no alarm.",
        "back": "Something that was acting up is fine again. A quick all-clear, a few words.",
        "hello": "Say hi: this is your own direct line with him now. Quick and warm.",
        "sun": "It's dry and sunny where he is for the next hours. A light nudge to enjoy it: the sun, or a short "
               "walk. One idea at most, not pushy.",
        "rain": "Rain is coming where he is. A quick heads-up with when it starts (the time from the facts).",
        "cosy": "It's a rainy day where he is. Suggest something cosy inside: a book, or something nice indoors. "
                "Never suggest going outside today; in his words: \"Don't prompt me on rainy days to go "
                "outside because it doesn't make any sense.\"",
        "appt": "He asked you to ping him for this appointment: it starts now (or in the minutes the facts say). "
                "A quick text that it's on, its name and time in passing; where, only when the facts give a place.",
        "remind": "He asked you to remind him of this, now. A quick reminder in your own words; keep what he wanted "
                  "to be reminded of clear. When the facts say it's late, say so in passing.",
        "watch": "He asked you to keep an eye out for this, and it came (the facts say what). A quick text with "
                 "what came, plainly (a mail: who from and what it says about what he's waiting for; the weather: "
                 "what and when). Whether you keep watching only in passing, as the facts say.",
        "watch-end": "Something he asked you to watch has stopped (the facts say what and why). One quick line that "
                     "you've stopped keeping an eye on it, and why in a few words (time's up and nothing came, or he "
                     "asked).",
    }.get(why, "Tell him this, in a quick text.")
    before = _recent(why)
    said = ("\n\nYour last texts like this, so this one sounds different:\n" + "\n".join(f"- {t}" for t in before)
            if before else "")
    return (f"{what}\n\nThe facts (for you, don't copy them as they are):\n{facts or '(none)'}{said}\n\n"
            "Write only the text itself: one or two short sentences, the way you'd actually text him.")


def compose(why: str, facts: str, raw: bool = False) -> str:
    """Her text for WHY from FACTS, through Claude; the plain line without it. raw: FACTS is the whole prompt
    (no plain line: on a failure it's QUIET)."""
    plain_line = QUIET if raw else plain(why, facts)
    if os.environ.get("HQ_DIRECT_PLAIN") == "1" or os.environ.get("HQ_DIRECT_DRY") == "1":
        return plain_line
    try:
        import asyncio
        import brain as _brain  # clears API key variables first
        a = agent()
        system = (_text_rules() + _agents.persona(a, user())
                  .replace("on this call", "on this chat").replace("call rules", "chat rules"))
        b = _brain.ClaudeBrain(model=a["model"], system_prompt=system, cwd=ROOT / "scratch" / "direct-line",
                               effort="low")

        async def go():
            out = []
            try:
                async for piece in b.ask(facts if raw else compose_prompt(why, facts)):
                    if isinstance(piece, str):
                        out.append(piece)
            finally:
                await b.stop()
            return "".join(out).strip()

        text = asyncio.run(asyncio.wait_for(go(), timeout=90))
        return _clean(text) or plain_line
    except Exception as e:
        print(f"compose: {e!r}", file=sys.stderr)
        return plain_line


def _clean(text: str) -> str:
    text = re.sub(r"\[\[[^\]]*\]\]", "", text or "")
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.M)
    return text.replace("**", "").strip().strip('"').strip()


def text(why: str, facts: str) -> dict:
    """Write one text from her into the thread and push it to his phone."""
    msg = add("agent", compose(why, facts), why)
    msg["pushed"] = push(msg["text"])
    return msg


QUIET = "QUIET"

INITIATIVE_PROMPT = """You keep your own notes for {user} (below), next to his calendar. Nobody asked you anything \
now: this is your own look, a few times a day. Text him only when one of your notes is worth bringing up right now \
(it fits this moment or what's coming in his day, it's waiting on him, or it's time to follow up), and never just to \
check in. Most looks, stay quiet. If you text: one quick, casual line about that one thing, the way a colleague texts \
in between (H127), no notes or system talk. If not, answer only the word QUIET.

{facts}"""


def initiative() -> dict | None:
    """H124: her own look at her notes (from pings.watch, a few times a day). She texts only when one is worth it."""
    import pings
    facts = pings.initiative_facts()
    if os.environ.get("HQ_DIRECT_DRY") == "1" or os.environ.get("HQ_DIRECT_PLAIN") == "1":
        words = os.environ.get("HQ_INITIATIVE_SAYS", QUIET)
    else:
        words = compose("initiative", INITIATIVE_PROMPT.replace("{user}", user()).replace("{facts}", facts),
                        raw=True)
    words = _clean(words)
    if not words or words.upper().strip(" .!") == QUIET or len(words) < 8:
        print(time.strftime("%Y-%m-%d %H:%M:%S"), "initiative: quiet")
        return None
    msg = add("agent", words, "initiative")
    msg["pushed"] = push(msg["text"])
    pings.initiative_sent()
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
    rules = (_text_rules() + _agents.persona(a, user()).replace("on this call", "on this chat")
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
    # H127: only background for her; the text itself says the team finished up, no details.
    return ("What the team worked on (background only, never in the text):\n" + "\n".join(lines[-8:])) if lines else ""


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
            incidents_data = _inc.read().get("incidents") or []  # F28: read() gives {"incidents": [...], ...}
        except Exception:
            incidents_data = []
    told = dict(s.get("told") or {})
    downs, backs = [], []
    for e in incidents_data or []:
        iid = str(e.get("id"))
        if not e.get("back"):
            if iid not in told and (e.get("key") in ("role", "github") or now - float(e.get("down") or now) >= DOWN_AFTER):
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
    elif cmd == "initiative":
        m = initiative()
        print(json.dumps(m, ensure_ascii=False) if m else "quiet")
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
