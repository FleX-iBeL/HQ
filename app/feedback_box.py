"""H247, piece (b): the maker's small mailbox, so feedback from someone else's HQ reaches the planning of the person who
makes HQ.

It runs on the maker's main computer, listens on this computer only (127.0.0.1), and is reached from outside through
one HTTPS path that Tailscale Funnel passes on (`setup`); nothing else on the computer is opened. It only takes short
text, only with a key the maker made for that one person ("Invite someone to send feedback" on the status page), at
most MAX_TEXT characters a message and PER_DAY messages a day per key. A key can be taken back. What's sent becomes a
row under Phase U · Feedback (`jobs.py feedback`, with the name the maker gave the key, never the name the sender
claims), as words only: nothing in a message is ever run, and nothing is put in a page as code.

Where it keeps things, in the maker's workspace (never in HQ's public code):
  HQ/feedback-box.json   the mailbox's settings: on, its public address, its port (HQ_FEEDBACK_BOX)
  HQ/feedback-keys.json  the keys, only their hashes, each with its name and what came in with it (HQ_FEEDBACK_KEYS)

    python3 app/feedback_box.py serve [--port N]     run the mailbox (the routine keeps it running when it's on)
    python3 app/feedback_box.py setup                turn it on: its address, and the one HTTPS path through Tailscale
    python3 app/feedback_box.py off                  turn it off, and close the path again
    python3 app/feedback_box.py invite NAME          a key for one person; prints the link to send them (JSON)
    python3 app/feedback_box.py revoke KEY-ID|NAME   take a key back: nothing more gets in with it
    python3 app/feedback_box.py list                 the keys (names, made, taken back, how much came in), JSON
    python3 app/feedback_box.py check                is it up, and is its path open (JSON)

The sender's side is app/feedback.py.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

HERE = Path(__file__).resolve().parent
JOBS = HERE.parent / "routine" / "jobs.py"
MOUNT = "/hq/feedback"       # the one path Tailscale passes on
PORT = 4791                  # on this computer only
FUNNEL_PORT = 10000          # one of the three ports Tailscale Funnel allows (443 and 8443 serve other things)
MAX_TEXT = 2000              # characters in one message
MAX_BODY = 8192              # bytes in one request
PER_DAY = 20                 # messages a day per key
BAD_PER_10_MIN = 10          # wrong keys from one place before it's told to wait
_ID = re.compile(r"^[a-f0-9]{6,32}$")
_KEY = re.compile(r"^[A-Za-z0-9_-]{20,64}$")
_lock = threading.Lock()
_bad = {}  # where from -> times a wrong key came in


def box_file() -> Path:
    return Path(os.environ.get("HQ_FEEDBACK_BOX", str(config.DATA / "feedback-box.json")))


def keys_file() -> Path:
    return Path(os.environ.get("HQ_FEEDBACK_KEYS", str(config.DATA / "feedback-keys.json")))


def _read(p: Path, empty):
    try:
        d = json.loads(p.read_text())
        return d if isinstance(d, type(empty)) else empty
    except (OSError, ValueError):
        return empty


def _write(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def box() -> dict:
    return _read(box_file(), {})


def is_on() -> bool:
    return bool(box().get("on"))


def _keys() -> dict:
    d = _read(keys_file(), {})
    d.setdefault("keys", [])
    return d


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _maker() -> str:
    try:
        import me
        return me.load(config.FOLDER).get("name") or ""
    except Exception:
        return ""


def _token(url: str, key: str, maker: str) -> str:
    raw = json.dumps({"v": 1, "u": url, "k": key, "n": maker}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def invite(name: str) -> dict:
    name = " ".join((name or "").split())[:60]
    if not name:
        return {"error": "Who is it for? Give a name."}
    url = box().get("url")
    if not url:
        return {"error": "The mailbox isn't set up on this HQ yet (python3 app/feedback_box.py setup)."}
    key = secrets.token_urlsafe(24)
    with _lock:
        d = _keys()
        kid = "k" + secrets.token_hex(4)
        d["keys"].append({"id": kid, "name": name, "hash": _hash(key), "made": datetime.now().strftime("%Y-%m-%d %H:%M"),
                          "revoked": "", "days": {}, "items": {}})
        _write(keys_file(), d)
    link = f"{url}/join#t={_token(url, key, _maker())}"
    return {"id": kid, "name": name, "link": link}


def revoke(which: str) -> dict:
    which = (which or "").strip()
    with _lock:
        d = _keys()
        hit = [k for k in d["keys"] if not k.get("revoked") and (k["id"] == which or k["name"].lower() == which.lower())]
        if not hit:
            return {"error": f"No key in use for {which!r}."}
        for k in hit:
            k["revoked"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        _write(keys_file(), d)
    return {"revoked": [k["id"] for k in hit], "names": [k["name"] for k in hit]}


def listing() -> dict:
    out = []
    for k in _keys()["keys"]:
        out.append({"id": k["id"], "name": k["name"], "made": k.get("made", ""), "revoked": k.get("revoked", ""),
                    "sent": len(k.get("items") or {}), "last": max((v.get("at", "") for v in (k.get("items") or {}).values()),
                                                                   default="")})
    return {"on": is_on(), "url": box().get("url", ""), "keys": out}


def _find(key: str):
    """The key's entry, or None. Compared by hash in constant time; a taken-back key is no key."""
    if not _KEY.match(key or ""):
        return None
    h = _hash(key)
    for k in _keys()["keys"]:
        if hmac.compare_digest(k.get("hash", ""), h) and not k.get("revoked"):
            return k
    return None


def _clean(text: str) -> str:
    # Words only: no control characters, one line (a table row), a | can't break the row.
    t = "".join(ch if ch.isprintable() or ch in "\n\t" else " " for ch in (text or ""))
    return " ".join(t.split()).replace("|", "/")


def take(key: str, ask: dict) -> tuple:
    """One message in. Returns (http status, answer)."""
    k = _find(key)
    if not k:
        return 401, {"error": "This key isn't known, or it was taken back."}
    sid = str(ask.get("id") or "")
    if not _ID.match(sid):
        return 400, {"error": "Each message needs its own id."}
    text = _clean(str(ask.get("text") or ""))
    if not text:
        return 400, {"error": "The message is empty."}
    if len(text) > MAX_TEXT:
        return 413, {"error": f"At most {MAX_TEXT} characters in one message."}
    when = str(ask.get("when") or "")
    if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", when):
        when = ""
    via = "agent" if ask.get("via") == "agent" else ""
    with _lock:
        d = _keys()
        k = next((x for x in d["keys"] if x["id"] == k["id"]), None)
        if not k or k.get("revoked"):
            return 401, {"error": "This key isn't known, or it was taken back."}
        got = (k.get("items") or {}).get(sid)
        if got:  # sent before (a retry): the same row, nothing new
            return 200, {"row": got.get("row", ""), "again": True}
        today = time.strftime("%Y-%m-%d")
        if (k.get("days") or {}).get(today, 0) >= PER_DAY:
            return 429, {"error": f"That's {PER_DAY} for today. The rest can go tomorrow."}
        cmd = [sys.executable, str(JOBS), "feedback", text, "--from", k["name"]]
        cmd += (["--bug"] if ask.get("bug") is True else []) + (["--when", when] if when else [])
        cmd += (["--via", "agent"] if via else [])
        env = {**os.environ}
        if os.environ.get("HQ_FEEDBACK_ROADMAP"):
            env["HQ_ROADMAP"] = os.environ["HQ_FEEDBACK_ROADMAP"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
        except (OSError, subprocess.TimeoutExpired):
            return 503, {"error": "It couldn't be put on the planning just now. It will be tried again."}
        m = re.search(r"\b(U\d+) is on the planning", r.stdout or "")
        if r.returncode != 0 or not m:
            return 503, {"error": "It couldn't be put on the planning just now. It will be tried again."}
        k.setdefault("items", {})[sid] = {"row": m.group(1), "at": datetime.now().strftime("%Y-%m-%d %H:%M")}
        k.setdefault("days", {})[today] = k["days"].get(today, 0) + 1
        k["days"] = {dd: n for dd, n in k["days"].items() if dd >= time.strftime("%Y-%m-%d", time.localtime(time.time() - 8 * 86400))}
        _write(keys_file(), d)
    return 200, {"row": m.group(1)}


def statuses(key: str) -> tuple:
    """What came in with this key, each with its status on the planning now."""
    k = _find(key)
    if not k:
        return 401, {"error": "This key isn't known, or it was taken back."}
    import feedback as fb
    rows, text = fb._rows()
    sprint = fb._sprint()
    out = {}
    for sid, v in (k.get("items") or {}).items():
        s = fb.status_of(v.get("row", ""), rows, text, sprint)
        out[sid] = {"row": v.get("row", ""), "status": s, "status_words": fb.STATUS[s]}
    return 200, {"items": out}


def _too_many_bad(where: str) -> bool:
    now = time.time()
    seen = [t for t in _bad.get(where, []) if now - t < 600]
    _bad[where] = seen
    return len(seen) >= BAD_PER_10_MIN


JOIN_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="referrer" content="no-referrer">
<title>Connect your HQ</title>
<style>
:root{color-scheme:light dark;--bg:#fafaf7;--fg:#1c1c1a;--muted:#6b6b66;--line:#e2e1db;--accent:#2f6f5e}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe6;--muted:#9a9993;--line:#2e2d2a;--accent:#7cc4ad}}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 -apple-system,system-ui,sans-serif}
main{max-width:30rem;margin:0 auto;padding:32px 16px}
h1{font-size:22px;margin:0 0 8px}p{color:var(--muted);margin:0 0 16px}
a.btn,button{display:block;width:100%;box-sizing:border-box;text-align:center;border:0;border-radius:12px;padding:14px;
font:600 16px/1.2 inherit;margin:0 0 10px;cursor:pointer;text-decoration:none}
a.btn{background:var(--accent);color:var(--bg)}button{background:transparent;color:var(--fg);border:1px solid var(--line)}
label{display:block;font-size:14px;color:var(--muted);margin:16px 0 4px}
input{width:100%;box-sizing:border-box;padding:10px;border-radius:10px;border:1px solid var(--line);background:transparent;color:var(--fg);font:15px inherit}
small{color:var(--muted)}
</style></head><body><main>
<h1 id="h">Connect your HQ</h1>
<p id="p">This link lets your HQ send feedback to the person who makes it. Open it in your HQ and it sets itself up: nothing to type.</p>
<a class="btn" id="open" href="#">Open in my HQ</a>
<button id="copy" type="button">Copy the link</button>
<small id="note">Not on the computer that runs HQ? Copy the link and paste it in HQ, Settings, Feedback.</small>
<label for="addr">Your HQ's address</label><input id="addr" inputmode="url" autocomplete="off" spellcheck="false">
</main><script>
(function(){
  var t = (location.hash.match(/[#&]t=([A-Za-z0-9_-]+)/) || [])[1] || "";
  var who = "";
  try { var j = JSON.parse(atob(t.replace(/-/g,"+").replace(/_/g,"/"))); who = String(j.n || "").slice(0, 60); } catch (e) {}
  if (!t) { document.getElementById("h").textContent = "This link is incomplete"; document.getElementById("p").textContent = "Ask for the link again."; return; }
  if (who) document.getElementById("h").textContent = "Send feedback to " + who;
  var addr = document.getElementById("addr"), open = document.getElementById("open");
  var saved = ""; try { saved = localStorage.getItem("hq-address") || ""; } catch (e) {}
  addr.value = saved || "http://localhost:7860";
  function href() { var a = addr.value.trim().replace(/\\/+$/, ""); if (!/^https?:\\/\\//.test(a)) a = "http://" + a; return a + "/?feedback-join=" + t; }
  function set() { open.href = href(); }
  addr.addEventListener("input", function(){ set(); try { localStorage.setItem("hq-address", addr.value.trim()); } catch (e) {} });
  set();
  document.getElementById("copy").addEventListener("click", function(){
    var s = location.href; var b = this;
    (navigator.clipboard ? navigator.clipboard.writeText(s) : Promise.reject()).then(function(){ b.textContent = "Copied"; }, function(){ b.textContent = "Copy it from the address bar"; });
  });
})();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "HQ"
    sys_version = ""

    def log_message(self, fmt, *args):  # never the keys or the words in a log
        pass

    def _path(self) -> str:
        p = self.path.split("?", 1)[0].split("#", 1)[0]
        if p.startswith(MOUNT):  # whether or not Tailscale took the mount path off
            p = p[len(MOUNT):]
        return p or "/"

    def _where(self) -> str:
        return (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()[:64]

    def _answer(self, code: int, body, kind="application/json; charset=utf-8", extra=None):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self._path() == "/join":
            csp = ("default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; "
                   "form-action 'none'; frame-ancestors 'none'")
            return self._answer(200, JOIN_PAGE.encode(), "text/html; charset=utf-8", {"Content-Security-Policy": csp})
        return self._answer(404, {"error": "Not here."})

    def do_POST(self):
        path = self._path()
        if path not in ("/send", "/status", "/hello"):
            return self._answer(404, {"error": "Not here."})
        where = self._where()
        try:
            n = int(self.headers.get("Content-Length") or "-1")
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            return self._answer(413, {"error": "Too long."})
        raw = self.rfile.read(n)
        key = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
        if not _find(key):
            # A right key always gets in; wrong ones from one place (behind Funnel that may be every stranger at
            # once) are told to wait, so guessing gets slow.
            if _too_many_bad(where):
                return self._answer(429, {"error": "Too many wrong keys. Try again later."})
            _bad.setdefault(where, []).append(time.time())
            return self._answer(401, {"error": "This key isn't known, or it was taken back."})
        try:
            ask = json.loads(raw or b"{}")
            if not isinstance(ask, dict):
                raise ValueError
        except ValueError:
            return self._answer(400, {"error": "That isn't a message."})
        if path == "/hello":
            return self._answer(200, {"ok": True, "maker": _maker()})
        if path == "/status":
            return self._answer(*statuses(key))
        return self._answer(*take(key, ask))


def serve(port: int) -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    srv.serve_forever()


def _tailscale(*args) -> list:
    """The tailscale command; on a Linux server its serve settings belong to root (as status/phone.sh does)."""
    sys.path.insert(0, str(HERE.parent / "routine"))
    import hqpaths
    cmd = hqpaths.tailscale(*args)
    if sys.platform != "darwin" and os.geteuid() != 0 and os.environ.get("HQ_TS_SUDO", "1") != "0":
        cmd = ["sudo", "-n"] + cmd
    return cmd


def _public_host() -> str:
    r = subprocess.run(_tailscale("status", "--self", "--json"), capture_output=True, text=True, timeout=30)
    try:
        return json.loads(r.stdout)["Self"]["DNSName"].rstrip(".")
    except (ValueError, KeyError):
        return ""


def path_open() -> bool:
    """Is the one path passed on to the mailbox, and public (Funnel)?"""
    r = subprocess.run(_tailscale("serve", "status", "--json"), capture_output=True, text=True, timeout=30)
    try:
        d = json.loads(r.stdout or "{}")
    except ValueError:
        return False
    port = int(box().get("funnel_port") or FUNNEL_PORT)
    web = [v for k, v in (d.get("Web") or {}).items() if k.endswith(f":{port}")]
    funnel = any(k.endswith(f":{port}") and v for k, v in (d.get("AllowFunnel") or {}).items())
    return funnel and bool(web) and set(web[0].get("Handlers", {})) == {MOUNT}


def open_path() -> str:
    """Only MOUNT on FUNNEL_PORT goes to the mailbox, public; whatever else that port served (inside the tailnet) is
    taken off first, so nothing else becomes public with it."""
    b = box()
    port, local = int(b.get("funnel_port") or FUNNEL_PORT), int(b.get("port") or PORT)
    subprocess.run(_tailscale("serve", f"--https={port}", "off"), capture_output=True, text=True, timeout=60)
    r = subprocess.run(_tailscale("funnel", "--bg", f"--https={port}", f"--set-path={MOUNT}", f"http://127.0.0.1:{local}"),
                       capture_output=True, text=True, timeout=60)
    return (r.stdout + r.stderr).strip()


def setup() -> dict:
    host = _public_host()
    if not host:
        return {"error": "Tailscale doesn't say this computer's name; is Tailscale on?"}
    b = box()
    b.update({"on": True, "url": f"https://{host}:{int(b.get('funnel_port') or FUNNEL_PORT)}{MOUNT}",
              "port": int(b.get("port") or PORT), "funnel_port": int(b.get("funnel_port") or FUNNEL_PORT)})
    _write(box_file(), b)
    said = open_path()
    return {"on": True, "url": b["url"], "open": path_open(), "tailscale": said[-300:]}


def off() -> dict:
    b = box()
    b["on"] = False
    _write(box_file(), b)
    subprocess.run(_tailscale("funnel", f"--https={int(b.get('funnel_port') or FUNNEL_PORT)}", "off"), capture_output=True,
                   text=True, timeout=60)
    return {"on": False, "open": path_open()}


def check() -> dict:
    sys.path.insert(0, str(HERE.parent / "routine"))
    import hqpaths
    b = box()
    return {"on": bool(b.get("on")), "url": b.get("url", ""), "up": hqpaths.listening(int(b.get("port") or PORT)),
            "open": path_open() if b.get("on") else False}


if __name__ == "__main__":
    a = sys.argv[1:]
    cmd = a[0] if a else "list"
    if cmd == "serve":
        p = int(a[a.index("--port") + 1]) if "--port" in a else int(box().get("port") or PORT)
        serve(p)
    elif cmd == "invite":
        res = invite(" ".join(a[1:]))
    elif cmd == "revoke":
        res = revoke(" ".join(a[1:]))
    elif cmd == "setup":
        res = setup()
    elif cmd == "off":
        res = off()
    elif cmd == "check":
        res = check()
    else:
        res = listing()
    if cmd != "serve":
        print(json.dumps(res, ensure_ascii=False, indent=1))
        sys.exit(1 if isinstance(res, dict) and res.get("error") else 0)
