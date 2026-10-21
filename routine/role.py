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

F23 (13 October 2026): the laptop slept seven minutes, woke up, counted its own sleep as the server being gone and
took over, while the server carried on as main: two mains for twenty minutes. In the user's words: "is this going
correct? my laptop was turned off and i worked on the vps, but now the macbook wants to take over main". So the
minutes without the main only count while this computer has been awake the whole time (a gap between its looks,
or a wake or restart since the last one, starts the count again); before taking over it asks the main once more,
directly and through the sync (Syncthing still connected means its computer is up), and doesn't take over when it
answers either way; once a backup that took over has seen the main again, it starts nothing new until it has
handed back, even when a later look fails; and a chosen main that gave way to one that took over stays the backup
until that one hands back or has itself been gone for the full takeover time, so there are never two mains.

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
/api/forward), forward SCRIPT ARGS... (jobs.py, schedule.py, todo.py and pings.py on the backup; H203: a call's
edits to the files only the main writes go the same way, through hand()).
"""
from __future__ import annotations

import contextlib, fcntl, http.client, json, os, socket, ssl, subprocess, sys, time
import urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hqpaths

SUPPORT = hqpaths.SUPPORT
CONFIG = os.path.join(SUPPORT, "role.json")
STATE = os.path.join(SUPPORT, "role-state.json")
PENDING = os.path.join(SUPPORT, "role-pending.jsonl")
TAKEOVER = 300  # a few minutes without the main before the backup takes over (Claude's choice)
BACK_LOOKS = 2  # looks the main must answer before the backup hands back (no flapping)
LOST_LOOKS = 2  # F23: looks in a row without the main before a takeover, whatever the minutes say
AWAY_GAP = 180  # F23: a gap this long between two looks means this computer was asleep or stopped (looks are every 60)
TIMEOUT = 8
TELL_TIMEOUT = 30  # telling the other one a choice: it may wait for its own minute's look to finish first (F19)
PY = sys.executable or "/usr/bin/python3"

# What a call may ask of the queue and the schedule, and so what the backup hands to the main.
# H203 (17 October 2026): also the to-do list (todo.py), the agent's reminders and notes (pings.py), and a call's or
# chat's own edits to the files only the main writes (handover.py edit, see ONE_WRITER).
WRITES = {"jobs": {"add", "add-row", "send-row", "stop", "overrule", "move", "on", "off", "mail-on", "mail-off", "mail-fast", "mail-hourly", "resume"},
          "schedule": {"add", "cancel", "move", "priority", "every"},
          "todo": {"add", "done", "letgo", "move", "tick", "untick", "undo"},
          "pings": {"appt", "remind", "cancel", "note", "note-clear", "watch", "unwatch", "out", "out-stop", "nudge", "nudge-done", "nudge-later"},
          "games": {"new", "spec", "tick", "count", "note", "diary", "week", "debrief", "undo"},
          "handover": {"edit"}}
SCRIPTS = {"todo": os.path.join(os.path.dirname(HERE), "app", "todo.py"),
           "games": os.path.join(os.path.dirname(HERE), "app", "games.py")}  # H222; the rest are routine/<script>.py
PASS_ENV = ("HQ_PINGS_BY",)  # what a handed request may carry over to the main (who asked, for her notes)

# H203, in the user's words (call of 17 October 2026, 14:45): "i am even more confused, you give it to the server but
# then also do it yourself? why?", then "ok, is there also other things you'd be better to hand over while that one
# is main?" The files the main writes by itself (the team, the mail check, the log's three-hour cycle, the routine's
# reminders), and so the only one that writes them: on the backup a call or chat hands its change to these to the
# main, which writes it; the sync brings it back. Paths are relative to the workspace.
ONE_WRITER = ("HQ/roadmap.md", "coaching/log.md", "inbox.md", "challenges.md", "HQ/games.json")


def one_writer(rel: str) -> bool:
    """H203: a workspace file only the main writes (the three, the to-do list, and an agent's own notes)."""
    rel = rel.replace(os.sep, "/").lstrip("./")
    if rel in ONE_WRITER:
        return True
    return rel.startswith("HQ/notes-") and rel.endswith(".md") and "/" not in rel[len("HQ/"):]


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


@contextlib.contextmanager
def _locked(wait=20.0):
    """F19: one decision about this HQ's role at a time: the routine's minute, a choice made from a call here, and
    the other HQ telling this one its choice. Raises TimeoutError when it can't get its turn within `wait`."""
    os.makedirs(SUPPORT, exist_ok=True)
    f = open(os.path.join(SUPPORT, "role.lock"), "a")
    try:
        end = time.time() + wait
        while True:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.time() >= end:
                    raise TimeoutError("role.lock")
                time.sleep(0.2)
        yield
    finally:
        f.close()


def _log(msg):
    """The routine's log, for what happens outside its minute (a choice from a call, the other one telling this one)."""
    try:
        run = os.path.join(hqpaths.HQ, "scratch", "routine")
        os.makedirs(run, exist_ok=True)
        with open(os.path.join(run, "routine.log"), "a") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


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
    return c.get("name") or hqpaths.host_name()  # H162: not the network's name (a hotspot renames it)


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
            "took_over": bool(s.get("took_over")),  # F19: took over (main gone) or just handing over a choice
            "took_over_at": s.get("took_over") or None,  # H139: when, so a main that never left can tell
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


ONLINE_URLS = ("https://api.anthropic.com/", "https://github.com/")


def online() -> bool:
    """This computer can reach the internet. A backup only takes over when it's online itself: without
    internet it's this one that's cut off, not the main that's gone. HQ_ROLE_ONLINE=0/1 fixes it for a test.
    H139: a real HTTPS answer with a checked certificate (any status counts, an error page too), not just a
    connection: a café's or a phone hotspot's network without real internet accepts any connection, so the
    laptop thought it was online, took over while the server carried on as main, and both were main."""
    if os.environ.get("HQ_ROLE_ONLINE") in ("0", "1"):
        return os.environ["HQ_ROLE_ONLINE"] == "1"
    ctx = ssl.create_default_context()
    for url in ONLINE_URLS:
        try:
            urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=6, context=ctx).close()
            return True
        except urllib.error.HTTPError:
            return True
        except Exception:
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
    # F19: the hand-over happens now, not at the next minute's looks. The one stepping down tells the other it's the
    # backup, and the other starts as main on that answer; nothing waits for both routines' minutes to line up.
    d = None
    try:
        with _locked():
            s = _load(STATE, {})
            step_down = name != me and acting() == "main" and not busy() and not s.get("took_over")
            if step_down:
                _set(s, "backup", f"{name} was made main; handed the role over", _log, handing_back=None)
                _save(STATE, s)
            d = _tell(c, name)
            s = _load(STATE, {})
            if step_down and not (d and d.get("acting") == "main"):
                # The other one didn't start as main: this one stays main until its minute's look sees it has.
                _set(s, "main", f"{name} was made main; this one stays main until it has taken over", _log)
            elif name == me and d and d.get("acting") == "backup" and acting() != "main":
                _set(s, "main", "the chosen main", _log, on_main_pending=True, took_over=None, handing_back=None,
                     gave_way=None)
            _save(STATE, s)
    except TimeoutError:  # this HQ's minute is busy deciding: still tell the other one; the next look does the rest
        d = _tell(c, name)
    _beat()
    if not d:
        turn = (" This one starts running the routines within a minute." if name == me else
                " This one stays main until the other one is back and has taken over.")
        return f"{name} is the main one now. The other one can't be reached now; it takes this choice over as soon as it's back.{turn}"
    if acting() == ("main" if name == me else "backup"):
        return f"{name} is the main one now. It told the other one, and the switch is done."
    doing = busy() if name != me else d.get("busy")
    return (f"{name} is the main one now. It told the other one right away. The switch happens as soon as "
            f"{doing or 'what runs there now'} is done, so nothing runs twice.")


def _tell(c, main):
    """Tell the other HQ the choice of main and what this one is doing now; its answer (its own role), or None."""
    try:
        code, d = _request(c["peer"].rstrip("/") + "/api/role", {"main": main, "chosen_at": c.get("chosen_at"),
                           "acting": acting(), "busy": busy()}, "role", timeout=TELL_TIMEOUT)
        return d if code == 200 and isinstance(d, dict) else None
    except Exception:
        return None


def settle(sender: dict) -> None:
    """F19: the other HQ has just told this one its choice (POST /api/role), so it's up. Hand over now instead of
    at the next minute's look: step down when the other is chosen and nothing runs here, or start as main when this
    one is chosen and the other says it's the backup. A main that took over (the other was gone) is left to the
    minute's look, which also writes the incident."""
    try:
        with _locked():
            c = config()
            if not c:
                return
            me, s = my_name(c), _load(STATE, {})
            peer = c.get("peer_name") or "the other HQ"
            if chosen_main(c) == me:
                if sender.get("acting") == "backup" and acting() != "main":
                    _set(s, "main", "the chosen main", _log, on_main_pending=True, took_over=None, handing_back=None,
                         gave_way=None)
            elif acting() == "main" and not s.get("took_over"):
                doing = busy()
                if doing:
                    s["handing_back"] = True
                    _set(s, "main", f"{peer} was made main; this one hands the role over once {doing} is done", _log)
                else:
                    _set(s, "backup", f"{peer} was made main; handed the role over", _log, handing_back=None)
            _save(STATE, s)
    except TimeoutError:
        return  # this HQ's minute is deciding right now; its next look does it
    _beat()


def _beat():
    """The status page's main-or-backup line, right after a hand-over outside the routine's minute."""
    try:
        import routines
        c = config()
        if not c:
            return
        s, me = _load(STATE, {}), my_name(c)
        chosen = chosen_main(c) == me
        p = s.get("peer") or {}
        routines.beat("role", state="waiting" if s.get("acting") == "main" and not chosen else "ok",
                      text=line(s, p or True, me, c.get("peer_name") or "the other HQ", 0, TAKEOVER, chosen),
                      badge=badge(c, s))
    except Exception:
        pass


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


def _woke() -> float:
    """When this computer last woke or started (a Mac's kern.waketime, the boot time). HQ_ROLE_WAKETIME sets it for
    a test."""
    if os.environ.get("HQ_ROLE_WAKETIME"):
        return float(os.environ["HQ_ROLE_WAKETIME"])
    try:
        return float(max(hqpaths.waketime(), hqpaths.boottime()))
    except Exception:
        return 0.0


def _awake_since(s, now) -> float:
    """F23: since when this computer has been awake and looking without a break. A gap between two looks, or a
    wake or restart since the last look, starts it again: time asleep never counts as the main being gone."""
    last = s.get("last_look")
    since = s.get("awake_since") or now
    if not last or now - float(last) > AWAY_GAP:
        since = now
    woke = _woke()
    if since < woke <= now:
        since = woke
    return since


def _stayed(s, p, was, takeover, prev_look=None) -> bool:
    """H139: the chosen main sees the other one acting main after a takeover. True when this one was the acting
    main, awake and looking since before the takeover (its last look came after it), and online at every look the
    other one didn't answer: then
    the other took over on a broken line (a café's network, the laptop's lid) and this one never left. An older
    HQ that doesn't say when it took over: False, the F23 way (give way until it hands back)."""
    at = p.get("took_over_at")
    if was != "main" or not p.get("took_over", True) or not at:
        return False
    at = float(at)
    if float(s.get("awake_since") or 0) > at or float(prev_look or 0) < at:
        return False
    return not (s.get("offline_seen") and float(s["offline_seen"]) >= at - takeover - 120)


def _main_still_there(c):
    """F23: the last check before taking over. Asks the main once more, a few seconds apart, and asks Syncthing
    whether the main's computer is still connected. Returns why not to take over ('' when it's really gone).
    When it answers it's up, busy or not, so this one doesn't take over."""
    for _ in range(2):
        time.sleep(float(os.environ.get("HQ_ROLE_RETRY", "3")))
        p = peer_role(c)
        if p:
            return f"it answered again ({p['busy']})" if p.get("busy") else "it answered again"
    try:
        import sync
        if sync.is_set() and sync.look().get("peer_up"):
            return "its computer is still connected through the sync"
    except Exception:
        pass
    return ""


def tick(jobs_cmd=None, log=None, incidents=None, routines=None, on_main=None) -> dict:
    """One look (the routine, every minute). Decides whether this HQ acts as main or backup now, writes its routine
    line, and sends on requests made here while the main couldn't be reached. Alone: returns at once, no network,
    no line. on_main() is called once when this HQ becomes the acting main (the routine lines up its timers)."""
    c = config()
    if not c:
        if routines:
            routines.drop("role")  # H118: an HQ on its own again shows no main-or-backup line or badge
        return {"acting": "main", "alone": True}
    p = peer_role(c)
    lock = contextlib.ExitStack()
    try:  # F19: a hand-over from a call, or told by the other one, may be deciding right now; this look waits its turn
        lock.enter_context(_locked(30))
    except TimeoutError:
        return {"acting": acting(), "handing_back": bool(_load(STATE, {}).get("handing_back")), "busy_deciding": True}
    now = time.time()
    s = _load(STATE, {})
    me = my_name(c)
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
        s["peer"] = {k: p.get(k) for k in ("name", "acting", "busy", "main", "label")}
    else:
        s["peer_looks"] = 0
        s["lost_looks"] = int(s.get("lost_looks") or 0) + 1
        s["peer_lost_since"] = s.get("peer_lost_since") or now
        if not online():  # H139: a look this one was cut off itself; the main that stayed checks it on return
            s["offline_seen"] = now
    if p:
        s["lost_looks"] = 0
    # F23: only minutes this computer was awake and looking count; a sleep, a restart or a stopped routine
    # starts the count again from when it was back.
    s["awake_since"] = _awake_since(s, now)
    prev_look = s.get("last_look")
    s["last_look"] = now
    peer = c.get("peer_name") or "the other HQ"
    lost = now - max(s["peer_lost_since"], s["awake_since"]) if s.get("peer_lost_since") else 0
    takeover = float(c.get("takeover") or TAKEOVER)
    gone = not p and lost >= takeover and int(s.get("lost_looks") or 0) >= LOST_LOOKS
    chosen = chosen_main(c) == me
    was = s.get("acting")
    took = s.get("took_over")
    if chosen:
        if p and p.get("acting") == "main" and _stayed(s, p, was, takeover, prev_look):
            # H139: this one was main, awake and online the whole time the other one couldn't see it: the other
            # took over on a broken line, not because this one was gone. It stays main; the other hands back.
            changed = _set(s, "main", "the chosen main", log, gave_way=None)
            if log:
                log(f"role: {peer} took over while this one was main and online the whole time; this one stays "
                    "main and it hands back")
        elif p and p.get("acting") == "main":
            what = f" ({p['busy']})" if p.get("busy") else ""
            # F19: only a main that took over took over; one that was simply main before is handing a choice over.
            took_over = p.get("took_over", True)
            changed = _set(s, "backup", f"{peer} took over while this one was away; it hands the main role back "
                                        f"once it has finished what it's doing{what}" if took_over else
                           f"{peer} is handing the main role over" + (f" once {p['busy']} is done" if p.get("busy")
                                                                      else " now"), log)
            s["gave_way"] = now if took_over else None
        elif not p and was == "backup" and s.get("gave_way") and not (gone and online() and not _main_still_there(c)):
            # F23: gave way to the other one, which took over; one look that doesn't reach it isn't the role back,
            # or both would be main. It stays the backup until the other hands back (it tells this one, or a look
            # sees it as the backup) or has been gone for the full takeover time.
            changed = _set(s, "backup", s.get("why") or f"{peer} took over while this one was away", log)
        else:
            changed = _set(s, "main", "the chosen main" if p or not s.get("gave_way") else
                           f"took the main role back: {peer} couldn't be reached for {int(lost // 60)} minutes",
                           log, gave_way=None)
    else:
        if was == "main":
            # Took over earlier, or was the main until the other one was chosen. Hand back once the main has
            # answered again (two looks) and nothing runs here; until then this one stays main, so nothing is
            # ever left without one. F23: from the first answer on, it starts nothing new, also when a later look
            # misses (a shaky line), until it has handed back or the main has been gone for the full time again.
            if p:
                s["main_back"] = True
                s["back_looks"] = int(s.get("back_looks") or 0) + 1
                if p.get("acting") == "main" or not s.get("took_over"):
                    # H139: the chosen main says it's main itself (it never left), or this one didn't take over but
                    # is handing a choice over (F19): hand back now, not a look later. The looks are for a return.
                    s["back_looks"] = max(s["back_looks"], BACK_LOOKS)
            elif s.get("main_back") and gone:
                s["main_back"], s["back_looks"] = None, 0
            if p and s["back_looks"] >= BACK_LOOKS:
                doing = busy()
                if doing:
                    s["handing_back"] = True
                    changed = _set(s, "main", f"{peer} is back; this one hands the main role back once {doing} is done", log)
                else:
                    changed = _set(s, "backup", f"handed the main role back to {peer}", log, took_over=None,
                                   handing_back=None, main_back=None, back_looks=0)
            else:
                s["handing_back"] = bool(s.get("main_back"))
                changed = _set(s, "main", f"{peer} is back; handing the main role over at the next look" if p
                               else f"{peer} answered again but not now; this one starts nothing new and hands the "
                                    "main role back when it answers" if s.get("main_back")
                               else s.get("why") if s.get("took_over") else f"{peer} was made main but can't be "
                               "reached; this one stays main until it answers", log)
        elif gone and online():
            why_not = _main_still_there(c)
            if why_not:
                s["peer_lost_since"], s["lost_looks"] = now, 0
                changed = _set(s, "backup", f"{peer} is the main one; it didn't answer for a few minutes, but "
                                            f"{why_not}, so this one didn't take over", log, handing_back=None)
                if log:
                    log(f"role: didn't take over: {why_not}")
            else:
                changed = _set(s, "main", f"took over: {peer} couldn't be reached for {int(lost // 60)} minutes "
                                          "while this computer was awake", log,
                               took_over=now, handing_back=None, main_back=None, back_looks=0)
        else:
            changed = _set(s, "backup", f"{peer} is the main one", log, handing_back=None)
    pending = s.pop("on_main_pending", None)
    _save(STATE, s)
    lock.close()
    # F19: stepped down while the other one answers: tell it now, so it starts as main without waiting a minute.
    if changed and was == "main" and s["acting"] == "backup" and p:
        _tell(c, chosen_main(c))
    # The incident log: a takeover is the main going down, handing back is it being up again.
    if incidents:
        if changed and s["acting"] == "main" and s.get("took_over") == now:
            since = max(s["peer_lost_since"], s.get("awake_since") or 0)
            incidents.down("role", f"{peer}, the main one, couldn't be reached since {_clock(since)}", at=since)
            incidents.fix("role", f"This one took over as main at {_clock(now)} and started the routines")
        elif changed and was == "main" and s["acting"] == "backup" and took and incidents.is_down("role"):
            incidents.fix("role", f"{peer} was back; handed the main role back at {_clock(now)}")
            incidents.up("role")
    if (changed or pending) and s["acting"] == "main" and on_main:
        try:
            on_main()
        except Exception as e:
            if log:
                log(f"role: on_main: {e!r}")
    _deliver(s["acting"], p, c, jobs_cmd, log)
    if routines:
        routines.beat("role", state=_line_state(s, p, lost, chosen), text=line(s, p, me, peer, lost, takeover, chosen),
                      last=now, next=now + 60, every=60, badge=badge(c, s))
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

def _script_path(script):
    return SCRIPTS.get(script) or os.path.join(HERE, f"{script}.py")


def _env(env):
    return {k: str(v) for k, v in (env or {}).items() if k in PASS_ENV}


def _run_here(script, args, env=None):
    r = subprocess.run([PY, _script_path(script), *args], capture_output=True, text=True, timeout=120,
                       env={**os.environ, **_env(env), "HQ_ROLE_HERE": "1"})
    return r.returncode, r.stdout, r.stderr


def hand(script: str, args: list[str], env: dict | None = None) -> tuple[int, str, str, str]:
    """H203: hand a write to the main. Returns (code, out, err, how): how is 'main' (the main ran it; code, out and
    err are its own), 'kept' (the main can't be reached: kept here, it goes on by itself, or runs here when this one
    takes over), 'refused' (the main said no) or 'alone' (no other HQ, or a test on the real pairing)."""
    if _test_on_real_pairing():
        return 3, "", "Refused (F17): a test may not hand anything to the other HQ through the real pairing.\n", "alone"
    c = config()
    if not c:  # nothing to hand it to
        return 3, "", "This HQ isn't paired; nothing to hand it to.\n", "alone"
    peer = c.get("peer_name") or "the main HQ"
    req = {"script": script, "args": args, **({"env": _env(env)} if _env(env) else {})}
    try:
        code, d = _request(c["peer"].rstrip("/") + "/api/forward", req, "forward", timeout=90)
        if code == 200 and isinstance(d, dict):
            return int(d.get("code") or 0), d.get("out") or "", d.get("err") or "", "main"
    except urllib.error.HTTPError as e:
        if e.code not in (409, 503):
            return 1, "", f"The main one ({peer}) refused it: {e.code}\n", "refused"
    except Exception:
        pass
    os.makedirs(SUPPORT, exist_ok=True)
    with open(PENDING, "a") as f:
        f.write(json.dumps({**req, "at": time.time()}) + "\n")
    return 0, (f"This HQ is the backup, and the main one ({peer}) can't be reached right now. The request is kept "
               f"here: it goes to {peer} as soon as it answers, or runs here if this one takes over as main in the "
               "next minutes.\n"), "", "kept"


def forward(script: str, args: list[str], env: dict | None = None) -> int:
    """jobs.py, schedule.py, todo.py or pings.py on the backup: a call's write goes to the main as a request. Prints
    what the main said. When the main can't be reached, the request is kept here and goes on by itself (or runs here
    when this one takes over)."""
    code, out, err, how = hand(script, args, env)
    if how == "main":
        peer = config().get("peer_name") or "the main HQ"
        out = f"(This HQ is the backup; handed to the main one, {peer}.)\n" + out
    sys.stdout.write(out)
    sys.stderr.write(err)
    return code


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
                code, out, err = _run_here(r["script"], r["args"], r.get("env"))
                if log:
                    log(f"role: ran a kept request here: {r['script']} {' '.join(r['args'])[:80]} -> {code}")
                continue
            if p and p.get("acting") == "main":
                code, d = _request(c["peer"].rstrip("/") + "/api/forward", r, "forward", timeout=90)
                if code == 200:
                    if log:
                        said = "" if not isinstance(d, dict) or not d.get("code") else \
                            f" -> {d['code']}: {' '.join(((d.get('out') or '') + (d.get('err') or '')).split())[:120]}"
                        log(f"role: sent a kept request to the main: {r['script']} {' '.join(r['args'])[:80]}{said}")
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
    if kind == "badge":  # H118
        print(json.dumps(badge()))
        return 0
    d = json.loads(sys.stdin.read() or "{}")
    if kind == "set":
        adopt(d.get("main"), d.get("chosen_at"))
        settle(d)  # F19: hand over now, not at the next minute's look
        print(json.dumps(mine()))
        return 0
    if kind == "forward":
        script, args = d.get("script"), [str(a) for a in d.get("args") or []]
        if script not in WRITES or not args or args[0] not in WRITES[script]:
            print(json.dumps({"code": 2, "out": "", "err": "Only a call's own queue, schedule, to-do, game, "
                                                             "reminder and hand-over commands are taken.\n"}))
            return 2
        if acting() != "main":
            print(json.dumps({"code": 3, "out": "", "err": "This HQ isn't the main one right now.\n"}))
            return 3
        code, out, err = _run_here(script, args, d.get("env"))
        print(json.dumps({"code": code, "out": out, "err": err}))
        return 0
    return 2


def badge(c=None, s=None) -> dict:
    """H118 (13 October 2026, in the user's words: "i would love to have a more UX friendly way to seeing which is
    the main; local or vps"): which computer is main, plainly, for the badge under the name on the status page, the
    call page and the strip (the Mac app and the phone version). {} when this HQ is on its own: nothing to show.
    "acting" is this one's role now; "main" the short name of the computer that is main (this one's, or the
    other's: VPS, Laptop); "text" what the badge says (the wording is Claude's choice)."""
    c = c if c is not None else config()
    if not c:
        return {}
    s = s if s is not None else _load(STATE, {})
    a = s.get("acting") if s.get("acting") in ("main", "backup") else acting()
    here = hqpaths.short_name()
    there = (s.get("peer") or {}).get("label") or c.get("peer_name") or "the other HQ"
    main = here if a == "main" else there
    return {"acting": a, "main": main, "text": "Main" if a == "main" else f"Backup · {main} is main"}


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
