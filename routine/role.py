#!/usr/bin/env python3
"""Main and backup (H56.3, 12 October 2026): two HQs, one on the laptop and one on a server, that never do the
same work twice.

Each HQ has a role. The main runs the hourly mail check, the jobs and the scheduler, and commits; the backup
takes calls, shows the status page and keeps its own laptop parts. A let's go on a call to the backup (adding,
stopping, moving a job, planning an item) goes to the main as a request, so only one of them ever writes the
job list. From a call the user says which one is main.

Decided on the call of 12 October 2026 at 12:23, in the user's words: "We see the server is not up. So it takes
over. And then, yeah, of course, it needs to start running. All the routines." So the backup takes over by
itself when the main can't be reached for a few minutes, and gives the role back once the main is there again
and the backup has finished the job it's running. [Claude's additions: a few minutes is TAKEOVER, 5; the backup
only takes over when it is online itself, so a laptop without internet never thinks the server is gone; once
the main is back for two looks in a row, the backup starts nothing new and hands back when its job and mail
check are done.] And at 13:21: "if other people don't have a VPS, I want to make sure that if they download on
the repo, Everything works fine." So with no other HQ set up, this one is simply main, never looks for a
server, never waits on one, and says nothing about it.

Kept in HQ's own memory on this computer (hqpaths.SUPPORT), never in the workspace (which syncs):
    role.json        the setup: {"name", "peer" (the other HQ's status page address), "main" (the name of the
                     chosen main), "chosen_at", "takeover" (seconds, optional), "peer_ip" (optional: connect to
                     this address for the peer's name, its certificate still checked against the name; for a
                     computer whose own DNS gives the name's public address, as a Mac without Tailscale DNS)}
    role-state.json  what the routine last decided: {"acting": "main"|"backup", "since", "why", ...}
    role-pending.jsonl  requests made on the backup while the main couldn't be reached; sent on (or run here
                     once this one takes over) by the routine.

The choice of main is the same on both: whichever was chosen last (chosen_at) wins, and each look the other's
choice is taken over when it's newer. So "make the laptop main" from a call to the laptop works with the server
completely down: when the server comes back, it sees the newer choice and is the backup.

usage (from the workspace):
  python3 "routine/role.py"                       which one is main, in plain words (a call may run this)
  python3 "routine/role.py" main here|other|NAME  make this one, the other one, or NAME the main (a call may run this)
  python3 "routine/role.py" setup PEER_URL [--name NAME] [--main here|other|NAME] [--takeover SECONDS] [--peer-ip IP]
                                                  pair this HQ with another (not from a call)
  python3 "routine/role.py" alone                 forget the other HQ: this one is main by itself again
Used by HQ itself: tick (the routine, every minute), acting, json, serve (the status server's /api/role and
/api/forward), forward SCRIPT ARGS... (jobs.py and schedule.py on the backup).
"""
from __future__ import annotations

import http.client, json, os, socket, ssl, subprocess, sys, time
import urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths

SUPPORT = hqpaths.SUPPORT
CONFIG = os.path.join(SUPPORT, "role.json")
STATE = os.path.join(SUPPORT, "role-state.json")
PENDING = os.path.join(SUPPORT, "role-pending.jsonl")
TAKEOVER = 300  # a few minutes without the main before the backup takes over (Claude's choice)
BACK_LOOKS = 2  # looks in a row the main must answer before the backup hands back (no flapping)
TIMEOUT = 8
PY = sys.executable or "/usr/bin/python3"

# What a call may ask of the queue and the schedule, and so what the backup hands to the main.
WRITES = {"jobs": {"add", "stop", "overrule", "move", "on", "off", "mail-on", "mail-off"},
          "schedule": {"add", "cancel", "move"}}


def _load(path, default):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return default


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


def _test_on_real_pairing() -> bool:
    """A test (HQ_UNDER_TEST) whose HQ memory is this computer's real one, so it would read the real role.json:
    only throwaway HQs with their own HQ_SUPPORT may pair under a test (flow 65)."""
    return hqpaths.under_test() and os.path.realpath(SUPPORT) == hqpaths.real_support()


def config() -> dict:
    """The setup, or {} when this HQ is on its own (no other HQ: main, nothing to look for). A test's copy of the
    roadmap (HQ_ROADMAP without its own HQ_SUPPORT) is always on its own: on a paired backup its jobs and planned
    items would otherwise go to the real main's job list (found in H56.7, when the flows ran on the VPS)."""
    if os.environ.get("HQ_ROADMAP") and not os.environ.get("HQ_SUPPORT"):
        return {}
    if _test_on_real_pairing():  # F17: a test never uses this HQ's real pairing
        return {}
    c = _load(CONFIG, {})
    return c if c.get("peer") else {}


def my_name(c=None) -> str:
    c = c if c is not None else config()
    return c.get("name") or socket.gethostname().split(".")[0]


def chosen_main(c=None) -> str:
    c = c if c is not None else config()
    return c.get("main") or my_name(c)


def acting() -> str:
    """'main' or 'backup': what this HQ does now. Cheap (no network); calls and jobs.py read this.
    Alone: always main. Paired but the routine hasn't decided yet: main only when it's the chosen one."""
    c = config()
    if not c:
        return "main"
    s = _load(STATE, {})
    if s.get("acting") in ("main", "backup"):
        return s["acting"]
    return "main" if chosen_main(c) == my_name(c) else "backup"


def is_backup() -> bool:
    return acting() == "backup"


def mine() -> dict:
    """What this HQ tells the other one (GET /api/role)."""
    c = config()
    s = _load(STATE, {})
    return {"name": my_name(c), "main": chosen_main(c), "chosen_at": c.get("chosen_at", 0), "acting": acting(),
            "busy": busy(), "since": s.get("since"), "paired": bool(c), "at": time.time(),
            "label": hqpaths.short_name()}  # H88: the name of its heartbeat line on the other's status page


def busy() -> str:
    """What this HQ is still doing as main: a job or the mail check ('' when nothing). A handing-back main
    waits for this to be empty."""
    run = os.path.join(hqpaths.HQ, "scratch", "routine")
    try:
        n = json.load(open(os.path.join(run, "job.json"))).get("n")
        return f"job {n}"
    except (OSError, ValueError):
        pass
    if os.path.exists(os.path.join(run, "mail.json")):
        return "the mail check"
    return ""


# -- talking to the other HQ ---------------------------------------------------------------------------

def _pinned(ip):
    """A urllib handler that connects to ip whatever the name resolves to, keeping the name for TLS (H56.7)."""
    def _connect(conn):
        sock = socket.create_connection((ip, conn.port), conn.timeout)
        conn.sock = conn._context.wrap_socket(sock, server_hostname=conn.host) if hasattr(conn, "_context") else sock

    class HTTPS(http.client.HTTPSConnection):
        connect = _connect

    class HTTP(http.client.HTTPConnection):
        connect = _connect

    class Handler(urllib.request.HTTPSHandler, urllib.request.HTTPHandler):
        def https_open(self, req):
            return self.do_open(HTTPS, req, context=self._context)

        def http_open(self, req):
            return self.do_open(HTTP, req)
    return Handler


def _request(url, data=None, header="", timeout=TIMEOUT):
    req = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode(),
                                 headers={"content-type": "application/json", **({"x-hq": header} if header else {})},
                                 method="GET" if data is None else "POST")
    ctx = ssl.create_default_context()
    if os.environ.get("HQ_ROLE_INSECURE"):  # a test against a self-made certificate
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
    c = _load(CONFIG, {})
    ip = c.get("peer_ip")
    if ip and c.get("peer") and urllib.parse.urlsplit(url).hostname == urllib.parse.urlsplit(c["peer"]).hostname:
        opener = urllib.request.build_opener(_pinned(ip)(context=ctx))
        with opener.open(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "null")
    with urllib.request.urlopen(req, timeout=timeout, context=ctx if url.startswith("https") else None) as r:
        return r.status, json.loads(r.read().decode() or "null")


def peer_role(c=None):
    """The other HQ's answer to GET /api/role, or None when it can't be reached."""
    c = c if c is not None else config()
    try:
        code, d = _request(c["peer"].rstrip("/") + "/api/role")
        return d if code == 200 and isinstance(d, dict) and d.get("name") else None
    except Exception:
        return None


def online() -> bool:
    """This computer can reach the internet. A backup only takes over when it's online itself: without
    internet it's this one that's cut off, not the main that's gone. HQ_ROLE_ONLINE=0/1 fixes it for a test."""
    if os.environ.get("HQ_ROLE_ONLINE") in ("0", "1"):
        return os.environ["HQ_ROLE_ONLINE"] == "1"
    for host in ("1.1.1.1", "8.8.8.8", "github.com"):
        try:
            socket.create_connection((host, 443), timeout=4).close()
            return True
        except OSError:
            continue
    return False


# -- the choice of main ----------------------------------------------------------------------------------

def choose(who: str) -> str:
    """Make `who` the main (here, other, or a name), now. Tells the other HQ right away when it answers; when
    it doesn't, it learns the newer choice the first time it can see this one again."""
    c = _load(CONFIG, {})
    if not c.get("peer"):
        return "This HQ is on its own, so it's always the main one. There's no other HQ set up."
    me = my_name(c)
    other = c.get("peer_name") or "the other one"
    name = me if who in ("here", "this", me) else (c.get("peer_name") or "") if who in ("other", "there") else who
    if not name:
        p = peer_role(c)
        name = (p or {}).get("name", "")
        if not name:
            return "The other HQ can't be reached and its name isn't known yet, so it can't be made main from here."
    if name not in (me, c.get("peer_name")):
        return f"There's no HQ called {name}: this one is {me}, the other one is {other}."
    c.update({"main": name, "chosen_at": time.time()})
    _save(CONFIG, c)
    told = ""
    try:
        code, _ = _request(c["peer"].rstrip("/") + "/api/role", {"main": name, "chosen_at": c["chosen_at"]}, "role")
        told = " It told the other one right away." if code == 200 else ""
    except Exception:
        told = " The other one can't be reached now; it takes this choice over as soon as it's back."
    turn = (" This one starts running the routines within a minute" if name == me else
            " This one stops starting new work within a minute; a job already running here finishes first")
    return f"{name} is the main one now.{told}{turn}."


def adopt(main: str, chosen_at: float) -> bool:
    """The other HQ's choice, when it's newer than this one's (POST /api/role, or seen on a look)."""
    c = _load(CONFIG, {})
    if not c.get("peer") or not main or float(chosen_at or 0) <= float(c.get("chosen_at") or 0):
        return False
    c.update({"main": main, "chosen_at": float(chosen_at)})
    _save(CONFIG, c)
    return True


# -- the routine's minute ----------------------------------------------------------------------------------

def _set(state, acting_now, why, log=None, **extra):
    was = state.get("acting")
    state.update({"acting": acting_now, "why": why, **extra})
    if was != acting_now:
        state["since"] = time.time()
        if log:
            log(f"role: {was or 'none'} -> {acting_now}: {why}")
    return was != acting_now


def tick(jobs_cmd=None, log=None, incidents=None, routines=None, on_main=None) -> dict:
    """One look (the routine, every minute). Decides whether this HQ acts as main or backup now, writes its routine
    line, and sends on requests made here while the main couldn't be reached. Alone: returns at once, no network,
    no line. on_main() is called once when this HQ becomes the acting main (the routine lines up its timers)."""
    c = config()
    if not c:
        return {"acting": "main", "alone": True}
    now = time.time()
    s = _load(STATE, {})
    me = my_name(c)
    p = peer_role(c)
    if p:
        if p.get("name") and c.get("peer_name") != p["name"]:
            full = _load(CONFIG, {})
            full["peer_name"] = p["name"]
            _save(CONFIG, full)
        if adopt(p.get("main"), p.get("chosen_at")):
            if log:
                log(f"role: took over the other HQ's newer choice: {p.get('main')} is main")
        c = config()
        s["peer_seen"] = now
        s["peer_lost_since"] = None
        s["peer_looks"] = int(s.get("peer_looks") or 0) + 1
        s["peer"] = {k: p.get(k) for k in ("name", "acting", "busy", "main")}
    else:
        s["peer_looks"] = 0
        s["peer_lost_since"] = s.get("peer_lost_since") or now
    peer = c.get("peer_name") or "the other HQ"
    lost = now - s["peer_lost_since"] if s.get("peer_lost_since") else 0
    takeover = float(c.get("takeover") or TAKEOVER)
    chosen = chosen_main(c) == me
    was = s.get("acting")
    took = s.get("took_over")
    if chosen:
        if p and p.get("acting") == "main":
            what = f" ({p['busy']})" if p.get("busy") else ""
            changed = _set(s, "backup", f"{peer} took over while this one was away; it hands the main role back "
                                        f"once it has finished what it's doing{what}", log)
        else:
            changed = _set(s, "main", "the chosen main", log)
    else:
        if was == "main":
            # Took over earlier, or was the main until the other one was chosen. Hand back once the main answers
            # again (two looks in a row) and nothing runs here; until then this one stays main, so nothing is
            # ever left without one.
            if p and s["peer_looks"] >= BACK_LOOKS:
                doing = busy()
                if doing:
                    s["handing_back"] = True
                    changed = _set(s, "main", f"{peer} is back; this one hands the main role back once {doing} is done", log)
                else:
                    changed = _set(s, "backup", f"handed the main role back to {peer}", log, took_over=None, handing_back=None)
            else:
                s["handing_back"] = bool(p)
                changed = _set(s, "main", f"{peer} is back; handing the main role over at the next look" if p
                               else s.get("why") if s.get("took_over") else f"{peer} was made main but can't be "
                               "reached; this one stays main until it answers", log)
        elif not p and lost >= takeover and online():
            changed = _set(s, "main", f"took over: {peer} couldn't be reached for {int(lost // 60)} minutes", log,
                           took_over=now, handing_back=None)
        else:
            changed = _set(s, "backup", f"{peer} is the main one", log, handing_back=None)
    _save(STATE, s)
    # The incident log: a takeover is the main going down, handing back is it being up again.
    if incidents:
        if changed and s["acting"] == "main" and s.get("took_over") == now:
            incidents.down("role", f"{peer}, the main one, couldn't be reached since {_clock(s['peer_lost_since'])}",
                           at=s["peer_lost_since"])
            incidents.fix("role", f"This one took over as main at {_clock(now)} and started the routines")
        elif changed and was == "main" and s["acting"] == "backup" and took and incidents.is_down("role"):
            incidents.fix("role", f"{peer} was back; handed the main role back at {_clock(now)}")
            incidents.up("role")
    if changed and s["acting"] == "main" and on_main:
        try:
            on_main()
        except Exception as e:
            if log:
                log(f"role: on_main: {e!r}")
    _deliver(s["acting"], p, c, jobs_cmd, log)
    if routines:
        routines.beat("role", state=_line_state(s, p, lost, chosen), text=line(s, p, me, peer, lost, takeover, chosen),
                      last=now, next=now + 60, every=60)
    return {"acting": s["acting"], "handing_back": bool(s.get("handing_back")), "peer": peer, "why": s.get("why")}


def _line_state(s, p, lost, chosen):
    if s["acting"] == "main" and not chosen:
        return "waiting"  # running as main for the other one: yellow, on purpose
    if not p and lost >= 120:
        return "waiting"
    return "ok"


def line(s, p, me, peer, lost, takeover, chosen) -> str:
    if s["acting"] == "main" and chosen:
        tail = "" if p else f"; {peer}, the backup, can't be reached" if lost >= 120 else ""
        return f"Main ({me}){tail}"
    if s["acting"] == "main":
        return f"Main for now ({me}): {s.get('why')}"
    if chosen:
        return f"Backup for now ({me}): {s.get('why')}"
    if not p and lost:
        left = max(0, takeover - lost)
        return (f"Backup ({me}); {peer}, the main one, can't be reached since {_clock(s['peer_lost_since'])}"
                + (f": takes over in about {int(left // 60) + 1} minutes" if left else
                   ": doesn't take over while this computer is offline itself"))
    return f"Backup ({me}); {peer} is the main one"


def _clock(t):
    return time.strftime("%H:%M", time.localtime(t or time.time()))


# -- requests from the backup ----------------------------------------------------------------------------------

def _run_here(script, args):
    r = subprocess.run([PY, os.path.join(HERE, f"{script}.py"), *args], capture_output=True, text=True, timeout=120,
                       env={**os.environ, "HQ_ROLE_HERE": "1"})
    return r.returncode, r.stdout, r.stderr


def forward(script: str, args: list[str]) -> int:
    """jobs.py or schedule.py on the backup: a call's write goes to the main as a request. Prints what the main
    said. When the main can't be reached, the request is kept here and goes on by itself (or runs here when this
    one takes over)."""
    if _test_on_real_pairing():
        sys.stderr.write("Refused (F17): a test may not hand anything to the other HQ through the real pairing.\n")
        return 3
    c = config()
    if not c:  # nothing to hand it to
        sys.stderr.write("This HQ isn't paired; nothing to hand it to.\n")
        return 3
    peer = c.get("peer_name") or "the main HQ"
    try:
        code, d = _request(c["peer"].rstrip("/") + "/api/forward", {"script": script, "args": args}, "forward", timeout=90)
        if code == 200 and isinstance(d, dict):
            sys.stdout.write(f"(This HQ is the backup; handed to the main one, {peer}.)\n" + (d.get("out") or ""))
            sys.stderr.write(d.get("err") or "")
            return int(d.get("code") or 0)
    except urllib.error.HTTPError as e:
        if e.code not in (409, 503):
            sys.stderr.write(f"The main one ({peer}) refused it: {e.code}\n")
            return 1
    except Exception:
        pass
    os.makedirs(SUPPORT, exist_ok=True)
    with open(PENDING, "a") as f:
        f.write(json.dumps({"script": script, "args": args, "at": time.time()}) + "\n")
    print(f"This HQ is the backup, and the main one ({peer}) can't be reached right now. The request is kept here: "
          f"it goes to {peer} as soon as it answers, or runs here if this one takes over as main in the next minutes.")
    return 0


def _deliver(acting_now, p, c, jobs_cmd, log):
    """Requests kept on the backup: run here once this one is main, or sent to the main once it answers."""
    try:
        lines = [json.loads(l) for l in open(PENDING) if l.strip()]
    except (OSError, ValueError):
        return
    left = []
    for r in lines:
        try:
            if acting_now == "main":
                code, out, err = _run_here(r["script"], r["args"])
                if log:
                    log(f"role: ran a kept request here: {r['script']} {' '.join(r['args'])[:80]} -> {code}")
                continue
            if p and p.get("acting") == "main":
                code, _ = _request(c["peer"].rstrip("/") + "/api/forward", r, "forward", timeout=90)
                if code == 200:
                    if log:
                        log(f"role: sent a kept request to the main: {r['script']} {' '.join(r['args'])[:80]}")
                    continue
        except Exception:
            pass
        left.append(r)
    if left:
        with open(PENDING + ".tmp", "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in left)
        os.replace(PENDING + ".tmp", PENDING)
    else:
        try:
            os.remove(PENDING)
        except OSError:
            pass


def serve(kind: str) -> int:
    """For the status server: GET /api/role (kind 'get'), POST /api/role (kind 'set', the other's newer choice on
    stdin) and POST /api/forward (kind 'forward', {script, args} on stdin). Prints JSON; exit 3 when a forwarded
    request comes to an HQ that isn't the acting main (the backup keeps it and tries again)."""
    if kind == "get":
        print(json.dumps(mine()))
        return 0
    d = json.loads(sys.stdin.read() or "{}")
    if kind == "set":
        adopt(d.get("main"), d.get("chosen_at"))
        print(json.dumps(mine()))
        return 0
    if kind == "forward":
        script, args = d.get("script"), [str(a) for a in d.get("args") or []]
        if script not in WRITES or not args or args[0] not in WRITES[script]:
            print(json.dumps({"code": 2, "out": "", "err": "Only a call's own queue and schedule commands are taken.\n"}))
            return 2
        if acting() != "main":
            print(json.dumps({"code": 3, "out": "", "err": "This HQ isn't the main one right now.\n"}))
            return 3
        code, out, err = _run_here(script, args)
        print(json.dumps({"code": code, "out": out, "err": err}))
        return 0
    return 2


def describe() -> str:
    c = config()
    if not c:
        return "This HQ is on its own, so it's the main one: it runs the mail check, the jobs and the scheduler."
    s = _load(STATE, {})
    me, peer = my_name(c), c.get("peer_name") or "the other HQ"
    a = acting()
    main = chosen_main(c)
    text = f"This one is {me}, and it's acting as the {a} now. The chosen main is {main if main != me else 'this one'}."
    if s.get("why"):
        text += f" Why: {s['why']}."
    if s.get("peer_seen"):
        text += f" {peer} last answered at {_clock(s['peer_seen'])}."
    if s.get("peer_lost_since"):
        text += f" It hasn't answered since {_clock(s['peer_lost_since'])}."
    try:
        n = sum(1 for l in open(PENDING) if l.strip())
        text += f" {n} request{'s' if n != 1 else ''} made here wait{'s' if n == 1 else ''} to go to the main."
    except OSError:
        pass
    return text


def main(argv):
    if not argv:
        print(describe())
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd in ("-h", "--help"):
        print(__doc__)
        return 0
    if cmd == "main" and args:
        print(choose(args[0]))
        return 0
    if cmd == "acting":
        print(acting())
        return 0
    if cmd == "json":
        print(json.dumps({**mine(), "state": _load(STATE, {})}))
        return 0
    if cmd == "setup" and args:
        c = _load(CONFIG, {})
        c["peer"] = args[0]
        i = 1
        while i < len(args):
            if args[i] == "--name":
                c["name"] = args[i + 1]
            elif args[i] == "--takeover":
                c["takeover"] = float(args[i + 1])
            elif args[i] == "--peer-ip":
                c["peer_ip"] = args[i + 1]
            elif args[i] == "--main":
                c["_main"] = args[i + 1]
            i += 2
        who = c.pop("_main", None)
        c.setdefault("main", my_name(c))
        c.setdefault("chosen_at", 0)
        _save(CONFIG, c)
        p = peer_role(c)
        if p:
            c["peer_name"] = p["name"]
            _save(CONFIG, c)
            adopt(p.get("main"), p.get("chosen_at"))
        if who:
            print(choose(who))
        print(describe() + ("" if p else " The other HQ didn't answer yet."))
        return 0
    if cmd == "alone":
        for f in (CONFIG, STATE, PENDING):
            try:
                os.remove(f)
            except OSError:
                pass
        print("This HQ is on its own again: the main one, and it no longer looks for another.")
        return 0
    if cmd == "tick":
        print(json.dumps(tick(log=lambda m: None)))
        return 0
    if cmd == "serve" and args:
        return serve(args[0])
    if cmd == "forward" and args:
        return forward(args[0], args[1:])
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
