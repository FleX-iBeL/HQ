"""H235: extensions, everyone can build their own on their HQ, and an update never breaks them (22 October 2026).

The user's quick note of 21 October 2026, after a friend's update clashed with the mail connectors she had built into
HQ's own files: "i want this broader than just email, other people should be able to universally build any extensions
on their own HQ without us breaking that for them." And on the call of 22 October 2026, typed: "theirs become
extensions, like you said, and HQ's version simply is leading. If there are conflicts after an update, we build it in
such a way that with each update it gets checked locally to see if there are possible conflicts between their own
extensions and the main build. If there are, then in nontechnical terms it should give them a message that there might
be possible conflicts. They could click on a button to either have a chat or send it directly to the team to fix and
make sure their HQ runs properly".

So: one folder in the workspace, `HQ/extensions/`, that an update never touches (the workspace isn't in HQ's repo).
One folder per extension, with an `extension.json` (only `name` and `what` are needed):

    {"name": "Apple Mail", "what": "one line on what it does", "on": true,
     "scripts":  {"read": {"run": "read.py", "what": "...", "ask": false}},
     "routines": {"alerts": {"run": "alerts.py", "every": 3600, "what": "..."}},
     "texts":    {"alert": "what the text is for, the way she should write it"},
     "uses":     ["routine/mail-check.md"],
     "keywords": ["Apple Mail"]}

and, when it has them, `call.md` (extra rules for calls), `text.md` (extra rules for the texts) and `mail.md` (extra
steps for the mail check). HQ reads them at its fixed points:
    calls        config.voice_rules(), at every call start      rule("call")
    texts        direct_line._text_rules(), every text          rule("text")
    kinds of texts  direct_line.compose_prompt(), HQ's own first   text_kind(why)
    mail check   tick.start_mail(), its {EXTENSIONS} step       mail_steps()
    scripts      a call, a text or the mail check runs one       run EXT SCRIPT [ARGS]
    routines     tick.py every minute, each at its own `every`  routines()
HQ's version leads: an extension never replaces one of HQ's own text kinds, files or rules; where both say something,
HQ's counts.

After every update (update.py's run, and tick.py as the safety net), `after_update()` checks locally whether anything
might clash: an extension that uses or mentions a part of HQ the update changed, a text kind HQ now has itself, a
script or routine named like a file HQ just added, its name or keywords in what's new. The result is
`.status/extensions-check.json`; the version bar on the call page and the status page says it in plain words, with
two buttons: talk it through (a text to their agent) or send it to the team (a roadmap row and a job). Calls and texts
hear it too until it's settled. How to move what someone already built into HQ's own files into an extension, for
their Claude: EXTENSIONS.md.

    python3 app/extensions.py                     every extension, what it does, on or off, and what's wrong with it
    python3 app/extensions.py rule call|text      the extra rules for a call or a text
    python3 app/extensions.py mail                the extra mail check steps
    python3 app/extensions.py run EXT SCRIPT [ARGS...]   one of an extension's scripts
    python3 app/extensions.py routines            start the routines that are due (tick.py, every minute)
    python3 app/extensions.py check [--from V --to V] [FILE...]   the clash check by hand (FILE: what changed)
    python3 app/extensions.py after-update        the check, once per update (tick.py and update.py)
    python3 app/extensions.py clash [chat|team|ok]  the last check; or talk it through, send it to the team, or it's fine
    python3 app/extensions.py init                the folder with its README, when there's none

Tests: HQ_EXTENSIONS_FOLDER (the extensions folder itself), HQ_EXTENSIONS_STATE (the routines' state file),
HQ_EXTENSIONS_CHECK (the check's file), HQ_EXTENSIONS_DRY=1 (clash chat and team only say what they'd do).
[Claude's choices: the folder's place and the file names; a routine runs at most once a minute and at most ten
minutes; a script at most two minutes; the check reads an extension's own files up to 200 KB each.]
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # HQ
sys.path.insert(0, str(ROOT / "routine"))
import hqpaths  # noqa: E402

RULE_FILES = {"call": "call.md", "text": "text.md", "mail": "mail.md"}
RUNNERS = {".py": [sys.executable], ".sh": ["/bin/sh"]}
ROUTINE_MAX = 600
SCRIPT_MAX = 120
READ_MAX = 200_000
README = """# Your extensions

Everything you add to your HQ goes here, one folder per extension. An update never touches this folder, and after
every update HQ checks whether anything here might clash with the new version, and tells you in plain words.

How to build one, and how to move something you already built into HQ's own files into here: EXTENSIONS.md in HQ.
"""
# The parts of HQ in everyday words, for the message after an update (the longest match wins).
PLAIN = [
    ("routine/mail-check.md", "the mail check"), ("routine/tick.py", "the routine that runs every minute"),
    ("routine/update.py", "the update"), ("routine/pings.py", "Donna's reminders"),
    ("app/direct_line.py", "the texts"), ("app/config.py", "the call rules"), ("app/policy.py", "what calls may do"),
    ("app/bot.py", "the call line"), ("app/brain.py", "the call line"), ("app/agenda.py", "the calendar"),
    ("app/todo.py", "the to-do list"), ("app/weather.py", "the weather"), ("app/web/", "the app's screens"),
    ("status/", "the status page"), ("routine/", "HQ's routines"), ("app/", "HQ's app"),
]


def folder() -> Path:
    return Path(os.environ.get("HQ_EXTENSIONS_FOLDER") or Path(hqpaths.FOLDER) / "HQ" / "extensions")


def state_file() -> Path:
    return Path(os.environ.get("HQ_EXTENSIONS_STATE") or ROOT / "scratch" / "extensions" / "state.json")


def check_file() -> Path:
    return Path(os.environ.get("HQ_EXTENSIONS_CHECK") or ROOT / ".status" / "extensions-check.json")


def _read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf8"))
    except (OSError, ValueError):
        return {}


def _write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf8")
    os.replace(tmp, p)


def init() -> Path:
    f = folder()
    f.mkdir(parents=True, exist_ok=True)
    if not (f / "README.md").exists():
        (f / "README.md").write_text(README, encoding="utf8")
    return f


# ---- reading them -------------------------------------------------------------------------------------------

def _named(d, kind: str, ext: Path, problems: list[str]) -> dict:
    """An extension's scripts or routines: {name: {"run", ...}}, each run file inside its own folder."""
    out = {}
    if not isinstance(d, dict):
        if d:
            problems.append(f"its {kind} aren't a list of names")
        return out
    for name, spec in d.items():
        spec = {"run": spec} if isinstance(spec, str) else dict(spec or {})
        run = str(spec.get("run") or "")
        path = (ext / run).resolve()
        if not run or ext.resolve() not in path.parents or not path.is_file():
            problems.append(f"its {kind[:-1]} {name} has no file to run")
            continue
        spec["path"] = str(path)
        out[str(name)] = spec
    return out


def all_() -> list[dict]:
    """Every extension in the folder, A to Z by folder, each with what's wrong with it (`problems`)."""
    f = folder()
    if not f.is_dir():
        return []
    out = []
    for d in sorted(p for p in f.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
        problems: list[str] = []
        spec = _read_json(d / "extension.json")
        if not (d / "extension.json").exists():
            problems.append("it has no extension.json")
        elif not spec:
            problems.append("its extension.json can't be read")
        e = {"id": d.name, "dir": str(d), "name": str(spec.get("name") or d.name), "what": str(spec.get("what") or ""),
             "on": spec.get("on", True) is not False, "uses": [str(u) for u in spec.get("uses") or []],
             "keywords": [str(k) for k in spec.get("keywords") or []]}
        if spec and not e["what"]:
            problems.append("it doesn't say in a line what it does")
        e["scripts"] = _named(spec.get("scripts"), "scripts", d, problems)
        e["routines"] = _named(spec.get("routines"), "routines", d, problems)
        e["texts"] = {str(k): str(v) for k, v in (spec.get("texts") or {}).items()} if isinstance(spec.get("texts"), dict) else {}
        for kind, name in RULE_FILES.items():
            try:
                e[kind] = (d / name).read_text(encoding="utf8").strip() if (d / name).is_file() else ""
            except OSError:
                e[kind] = ""
        e["problems"] = problems
        out.append(e)
    return out


def on() -> list[dict]:
    return [e for e in all_() if e["on"] and not any("extension.json" in p for p in e["problems"])]


def get(ext_id: str) -> dict | None:
    return next((e for e in on() if e["id"] == ext_id), None)


# ---- HQ's fixed points --------------------------------------------------------------------------------------

def _scripts_line(e: dict, where: str) -> list[str]:
    out = []
    for name, s in e["scripts"].items():
        if where == "mail" and not s.get("mail"):
            continue
        out.append(f"  - `python3 \"{HERE / 'extensions.py'}\" run {e['id']} {name}` ...: {s.get('what') or name}"
                   + (" (asks for a yes first)" if s.get("ask") and where != "mail" else ""))
    return out


def rule(where: str = "call") -> str:
    """The extra rules for a call or a text: each extension that's on, its line, its own rules and its scripts;
    then what might clash after the last update. Empty when there's nothing."""
    exts = [e for e in on() if e.get(where) or e["scripts"] or e["texts"]]
    lines = []
    if exts:
        lines += ["# Their own extensions (H235)", "",
                  "These are what they added to their HQ themselves. HQ's own rules come first: where an extension says "
                  "something different, HQ's rule counts. Only use an extension for what it says it does."]
        for e in exts:
            lines += ["", f"## {e['name']}: {e['what']}"]
            if e.get(where):
                lines.append(e[where])
            sc = _scripts_line(e, where)
            if sc:
                lines += ["Its scripts, each one command on its own:"] + sc
    c = clash()
    if c.get("state") in ("new", "chat") and c.get("clashes"):
        lines += ["", "# After the last update (H235)", "",
                  f"HQ was updated to {c.get('to') or 'a new version'}, and something they added might not work with it. "
                  "If they bring it up, help them look at it in plain words; don't bring it up yourself more than once:"]
        lines += [f"- {x['name']}: {'; '.join(x['why'])}" for x in c["clashes"]]
    return "\n".join(lines).strip()


def mail_steps() -> str:
    """The mail check's extra steps, from each extension's mail.md (H235)."""
    parts = []
    for e in on():
        if e.get("mail"):
            sc = _scripts_line(e, "mail")
            parts.append(f"   From the extension {e['name']} ({e['what']}):\n"
                         + "\n".join("   " + ln for ln in e["mail"].splitlines())
                         + ("\n   Its scripts you may run, each as exactly one Bash command:\n" + "\n".join("   " + s for s in sc)
                            if sc else ""))
    return "\n".join(parts) if parts else "(no extensions add steps)"


def mail_tools() -> list[str]:
    """The Bash permissions the mail check gets for the extensions' mail scripts."""
    return [f"Bash(python3 {HERE / 'extensions.py'} run {e['id']} {n}:*)" for e in on() if e.get("mail")
            for n, s in e["scripts"].items() if s.get("mail")]


def text_kind(why: str) -> str | None:
    """What an extension's own kind of text is for (HQ's own kinds are looked at first, in direct_line)."""
    for e in on():
        if why in e["texts"]:
            return e["texts"][why]
    return None


def script(ext_id: str, name: str) -> dict | None:
    e = get(ext_id)
    return e["scripts"].get(name) if e else None


def _env(e: dict) -> dict:
    return {**os.environ, "HQ_ROOT": str(ROOT), "HQ_WORKSPACE": str(hqpaths.FOLDER), "HQ_EXTENSION": e["dir"],
            "HQ_TEXT": f"{sys.executable} {ROOT / 'app' / 'direct_line.py'} text"}


def _cmd(path: str) -> list[str]:
    return RUNNERS.get(Path(path).suffix, []) + [path]


def run(ext_id: str, name: str, args: list[str]) -> int:
    e = get(ext_id)
    s = e["scripts"].get(name) if e else None
    if not s:
        print(f"There's no script {name} in an extension {ext_id} that's on.", file=sys.stderr)
        return 2
    try:
        r = subprocess.run(_cmd(s["path"]) + list(args), cwd=e["dir"], env=_env(e), timeout=SCRIPT_MAX)
        return r.returncode
    except subprocess.TimeoutExpired:
        print(f"{name} ran over {SCRIPT_MAX} seconds and was stopped.", file=sys.stderr)
        return 124


# ---- the routines -------------------------------------------------------------------------------------------

def _alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def routines(now: float | None = None) -> dict:
    """Start each routine that's due, in the background (one at a time per routine). Returns a summary for the
    routine's line: {"state", "text", "started"}."""
    now = now or time.time()
    st = _read_json(state_file())
    started, failing, count = [], [], 0
    for e in on():
        for name, r in e["routines"].items():
            count += 1
            key = f"{e['id']}/{name}"
            me = st.get(key) or {}
            if me.get("pid") and _alive(me["pid"]):
                continue
            if me.get("exit") not in (None, 0):
                failing.append(f"{e['name']} ({name})")
            every = max(60, int(r.get("every") or 3600))
            if now - float(me.get("last") or 0) < every - 5:
                continue
            log = state_file().parent / f"{e['id']}-{name}.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            p = subprocess.Popen([sys.executable, str(HERE / "extensions.py"), "_routine", e["id"], name],
                                 cwd=e["dir"], stdin=subprocess.DEVNULL, stdout=open(log, "a"), stderr=subprocess.STDOUT,
                                 start_new_session=True)
            st[key] = {**me, "pid": p.pid, "last": now}
            started.append(key)
    if started:
        _write_json(state_file(), st)
    if not count:
        return {"state": "ok", "text": "No routines of your own", "started": []}
    if failing:
        return {"state": "down", "text": "Failed last time: " + ", ".join(failing[:3]), "started": started}
    return {"state": "ok", "text": f"{count} routine{'s' if count != 1 else ''} of your own", "started": started}


def _routine(ext_id: str, name: str) -> int:
    """One routine's run, in the background: its exit and when it ended go into the state file."""
    e = get(ext_id)
    r = e["routines"].get(name) if e else None
    code = 2
    if r:
        print(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} {ext_id}/{name}", flush=True)
        limit = min(ROUTINE_MAX, max(60, int(r.get("every") or 3600)))
        try:
            code = subprocess.run(_cmd(r["path"]), cwd=e["dir"], env=_env(e), timeout=limit).returncode
        except subprocess.TimeoutExpired:
            code = 124
    st = _read_json(state_file())
    key = f"{ext_id}/{name}"
    st[key] = {**(st.get(key) or {}), "pid": None, "exit": code, "ended": time.time()}
    _write_json(state_file(), st)
    return code


# ---- after an update: might something clash? ----------------------------------------------------------------

def plain_part(path: str) -> str:
    for start, words in PLAIN:
        if path == start or path.startswith(start):
            return words
    return "a part of HQ"


def hq_kinds() -> set[str]:
    """HQ's own kinds of texts, read from direct_line.py's KINDS (and PLAIN) as the code stands now."""
    try:
        src = (ROOT / "app" / "direct_line.py").read_text(encoding="utf8")
    except OSError:
        return set()
    kinds = set()
    for block in ("KINDS = {", "PLAIN = {"):
        i = src.find(block)
        if i < 0:
            continue
        j = src.find("\n}\n", i)
        kinds |= set(re.findall(r'^\s{4}"([\w-]+)":', src[i:j], re.M))
    return kinds


def _own_text(e: dict) -> str:
    out = []
    for p in Path(e["dir"]).rglob("*"):
        if p.is_file() and p.suffix in (".py", ".sh", ".md", ".json", ".js", ".mjs", ".txt", ".applescript") \
                and p.stat().st_size <= READ_MAX:
            try:
                out.append(p.read_text(encoding="utf8", errors="ignore"))
            except OSError:
                pass
    return "\n".join(out)


def _mentions(text: str, path: str) -> bool:
    if path in text:
        return True
    if path.startswith(("app/", "routine/")) and path.endswith(".py") and path.count("/") == 1:
        mod = Path(path).stem
        return bool(re.search(rf"^\s*(?:import|from)\s+{re.escape(mod)}\b", text, re.M))
    return False


def _whats_new(old: str, new: str) -> list[str]:
    """The changelog's items between the two versions, as the code stands now (none without the new version)."""
    if not new:
        return []
    try:
        import update as _update
        secs = _update.parse_changelog((ROOT / "CHANGELOG.md").read_text(encoding="utf8"))
        lo, hi = _update.vtuple("v" + old) if old else None, _update.vtuple("v" + new) if new else None
    except Exception:
        return []
    items = []
    for s in secs:
        t = _update.vtuple("v" + s["version"]) if s["version"] else None
        if t and (hi is None or t <= hi) and (lo is None or t > lo):
            items += [it for g in s["groups"] for it in g["items"]]
    return items


def check(changed: list[str], old: str = "", new: str = "", added: list[str] | None = None) -> list[dict]:
    """What might clash, per extension: [{"id", "name", "why": [plain lines]}]. Changed and added are HQ's files
    the update changed or added; old and new its versions (for what's new)."""
    kinds = hq_kinds()
    news = _whats_new(old, new)
    added = added or []
    out = []
    for e in all_():
        if not e["on"]:
            continue
        why: list[str] = []
        if e["problems"]:
            why.append("HQ can't read it properly: " + "; ".join(e["problems"]))
        own = _own_text(e)
        hits = sorted({f for f in changed if f in e["uses"] or _mentions(own, f)})
        for part in sorted({plain_part(f) for f in hits}):
            why.append(f"it works with {part}, which this update changed")
        for k in sorted(set(e["texts"]) & kinds):
            why.append(f"HQ now has its own \"{k}\" texts, so HQ's are used and this one is skipped")
        names = {Path(s["path"]).name for s in list(e["scripts"].values()) + list(e["routines"].values())}
        for f in sorted(added):
            if Path(f).name in names:
                why.append(f"HQ itself now has {plain_part(f)} named like one of its own files, so it may do the same thing")
        for w in [e["name"]] + e["keywords"]:
            if len(w) >= 4 and any(re.search(rf"\b{re.escape(w)}\b", it, re.I) for it in news):
                why.append(f"what's new in this update mentions {w}, so HQ may now do the same thing itself")
                break
        if why:
            out.append({"id": e["id"], "name": e["name"], "why": why})
    return out


def clash() -> dict:
    return _read_json(check_file())


def _git(*args: str) -> list[str]:
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=30)
    return [ln for ln in r.stdout.splitlines() if ln.strip()] if r.returncode == 0 else []


def _changed(old: str, new: str) -> tuple[list[str], list[str]]:
    """What the update changed and added, from git: the two version tags, else HEAD's last move."""
    for a, b in ((f"v{old}", f"v{new}"), (f"v{old}", "HEAD"), ("HEAD@{1}", "HEAD")):
        if not a.strip("v") or not _git("rev-parse", "-q", "--verify", a + "^{commit}"):
            continue
        ch = _git("diff", "--name-only", a, b)
        if ch:
            return ch, _git("diff", "--name-only", "--diff-filter=A", a, b)
    return [], []


def after_update(run: dict | None = None, changed: list[str] | None = None) -> dict | None:
    """Once per finished update: the check, its file, and its lines in the note for their Claude. None when there's
    nothing new to check."""
    if run is None and os.environ.get("HQ_EXTENSIONS_RUN"):
        run = json.loads(os.environ["HQ_EXTENSIONS_RUN"])  # update.py, before its run file says done
    if run is None:
        run = _read_json(ROOT / ".status" / "update-run.json")
    if run.get("state") != "done" or not run.get("to"):
        return None
    last = clash()
    if last.get("to") == run["to"] and last.get("finished") == run.get("finished"):
        return None
    old, new = str(run.get("from") or ""), str(run["to"])
    added: list[str] = []
    if changed is None and run.get("changed"):
        changed = list(run["changed"])
        added = [f for f in changed if (ROOT / f).exists() and subprocess.run(
            ["git", "-C", str(ROOT), "cat-file", "-e", f"v{old}:{f}"], capture_output=True, timeout=10).returncode] if old else []
    if changed is None:
        changed, added = _changed(old, new)
    found = check(changed, old, new, added)
    data = {"at": time.time(), "from": old, "to": new, "finished": run.get("finished"),
            "state": "new" if found else "clear", "clashes": found, "extensions": len(all_())}
    _write_json(check_file(), data)
    if found:
        _to_note(new, found)
    return data


def _to_note(new: str, found: list[dict]) -> None:
    note = ROOT / "updates" / f"{new}.md"
    if not note.parent.is_dir():
        return
    w = ["", "## Their own extensions that might clash (H235)", "",
         "HQ's version leads. For each one: look at what it does and what changed, make it work with the new version "
         "inside its own folder in the workspace's HQ/extensions (never in HQ's own files), then tell the user in a "
         "sentence or two. EXTENSIONS.md in HQ says how extensions work.", ""]
    w += [f"- {x['name']} ({x['id']}): {'; '.join(x['why'])}" for x in found]
    try:
        with note.open("a", encoding="utf8") as f:
            f.write("\n".join(w) + "\n")
    except OSError:
        pass


def clash_words(c: dict | None = None) -> str:
    c = c if c is not None else clash()
    xs = c.get("clashes") or []
    if not xs:
        return ""
    names = [x["name"] for x in xs]
    who = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    return (f"After the update to {c.get('to')}, something you added to your HQ might not work with it: {who}. "
            + " ".join(f"{x['name']}: {x['why'][0]}." for x in xs[:3]))


def settle(how: str) -> dict:
    """The two buttons and the third: chat (a text to their agent, who answers in the texts), team (a roadmap row
    and a job that fixes it), ok (it's fine). Returns {"ok", "said", "open"}."""
    c = clash()
    if not c.get("clashes"):
        return {"ok": False, "said": "Nothing to look at: no clash after the last update."}
    words = clash_words(c)
    dry = os.environ.get("HQ_EXTENSIONS_DRY") == "1"
    if how == "ok":
        c["state"] = "ok"
        said = "Okay, I'll leave it."
        out = {"ok": True, "said": said}
    elif how == "chat":
        sys.path.insert(0, str(HERE))
        import direct_line
        if not direct_line.on():
            return {"ok": False, "said": "Texts are off on this HQ. Start a call and ask about it; the call knows."}
        text = words + " Can we look at it together?"
        if not dry:
            direct_line.add("me", text)
            log = open(ROOT / "scratch" / "direct-line.log", "a")
            subprocess.Popen([sys.executable, str(HERE / "direct_line.py"), "reply"], cwd=str(ROOT),
                             stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        c["state"] = "chat"
        out = {"ok": True, "said": f"Sent to {direct_line.agent().get('name', 'your agent')}; the answer comes in your texts.",
               "open": "texts", "text": text}
    elif how == "team":
        task = (f"After the update to {c.get('to')}, their own extension might clash with HQ. {words} "
                "HQ's version leads: make each extension work with the new version inside its own folder in the "
                "workspace's HQ/extensions (never in HQ's own files), see EXTENSIONS.md and the note in updates/, "
                "then run python3 app/extensions.py check and say in plain words what changed.")
        if dry:
            r = "dry"
        else:
            p = subprocess.run([sys.executable, str(ROOT / "routine" / "jobs.py"), "add-row", task, "--bug", "--kind", "small"],
                               capture_output=True, text=True, timeout=60, cwd=str(hqpaths.FOLDER))
            if p.returncode:
                return {"ok": False, "said": "Couldn't hand it to the team just now: " + (p.stderr or p.stdout).strip()[:160]}
            r = p.stdout.strip()
        c["state"] = "team"
        out = {"ok": True, "said": "Sent to the team; they'll fix it and let you know.", "job": r, "task": task}
    else:
        return {"ok": False, "said": "chat, team or ok"}
    c["settled"] = time.time()
    _write_json(check_file(), c)
    return out


def summary() -> str:
    exts = all_()
    if not exts:
        return f"No extensions yet. They go in {folder()}, one folder each (see EXTENSIONS.md in HQ)."
    lines = []
    for e in exts:
        bits = [f"{e['name']} ({e['id']}, {'on' if e['on'] else 'off'}): {e['what'] or '(no line on what it does)'}"]
        for k, label in (("scripts", "scripts"), ("routines", "routines"), ("texts", "kinds of texts")):
            if e[k]:
                bits.append(f"  {label}: " + ", ".join(e[k]))
        for k in RULE_FILES:
            if e.get(k):
                bits.append(f"  adds to the {'mail check' if k == 'mail' else k + ' rules'}")
        bits += [f"  problem: {p}" for p in e["problems"]]
        lines.append("\n".join(bits))
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "list"
    if cmd in ("list", "summary"):
        print(summary())
    elif cmd == "json":
        print(json.dumps(all_(), ensure_ascii=False))
    elif cmd == "rule":
        print(rule(argv[1] if len(argv) > 1 else "call"))
    elif cmd == "mail":
        print(mail_steps())
    elif cmd == "run" and len(argv) >= 3:
        return run(argv[1], argv[2], argv[3:])
    elif cmd == "_routine" and len(argv) == 3:
        return _routine(argv[1], argv[2])
    elif cmd == "routines":
        print(json.dumps(routines()))
    elif cmd == "check":
        args, old, new = list(argv[1:]), "", ""
        for flag in ("--from", "--to"):
            if flag in args:
                i = args.index(flag)
                val = args[i + 1] if i + 1 < len(args) else ""
                del args[i:i + 2]
                old, new = (val, new) if flag == "--from" else (old, val)
        found = check(args, old, new)
        print(json.dumps(found, ensure_ascii=False, indent=1) if found else "Nothing might clash.")
    elif cmd == "after-update":
        print(json.dumps(after_update(), ensure_ascii=False))
    elif cmd == "clash":
        if len(argv) > 1:
            print(json.dumps(settle(argv[1]), ensure_ascii=False))
        else:
            c = clash()
            print(json.dumps({**c, "words": clash_words(c)}, ensure_ascii=False))
    elif cmd == "init":
        print(init())
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
