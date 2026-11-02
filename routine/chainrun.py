#!/usr/bin/env python3
"""F105: the whole chain on a copy, from his words to live, every hand-off read back from its record.

His words: "how do we make sure that i can just discuss something with pepper, then say yea let MP know, and then she
will pick it up, write it as an item, review might flag and they go back and forth together and its complete, then it is
planned, then it is built, then it's tested, then it is QA checked and then its live".

A copy: HQ's files in a git repo of their own, a workspace, a status folder and ports of its own, bare repos on disk
standing in for GitHub, the phones, the mail and the calendar left out, only Moneypenny's cycle on. On it the routine's
real tick runs by itself. Two ways to run it:

    python3 routine/chainrun.py standin ROOT                  stand-ins for the model; flow 294, every night
    python3 routine/chainrun.py real ROOT --workspace PATH    the real model and a copy of the workspace; flow 295, by hand
    python3 routine/chainrun.py check ROOT LABEL              the hand-offs of one item, read from the record and what it points at
    python3 routine/chainrun.py clean ROOT                    the copy's processes by their pids, then its folder

What the chain can't do by itself stands in the run's own lines and in HOLD_UPS: the clock (her Thursday session, the
night's 22:00 and 2:00 are brought to now) and his two yeses (at the sprint planning, and the night's release going out);
those are the driver's, in plain words he'd use. Everything else is the routine's. Nothing of his is in here.
Standard library only.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent
PY = sys.executable

WORDS = ("On the status page, when nothing is on the schedule, it just says Nothing planned. "
         "I'd like it to say Nothing planned yet, so it doesn't feel so final.")
OLD, NEW = "Nothing planned.", "Nothing planned yet."
PAGE = "status/index.html"
HOLD_UPS = ("her Thursday session brought to now", "the night's 22:00 brought to now", "the night's 2:00 brought to now",
            "his yes at the sprint planning", "his hours for her set to the whole day")
OFF = ("HQ_UNDER_TEST", "HQ_ROADMAP", "HQ_SPRINT", "HQ_ROLE_HERE", "HQ_WORKSPACE", "HQ_TEST_PORT", "HQ_PORT", "HQ_STATUS_PORT", "HQ_UNIT", "HQ_SUPPORT",
       "HQ_NO_WALL", "HQ_DIRECT_DIR", "HQ_DIRECT_AGENT", "HQ_DIRECT_TEAM", "HQ_DIRECT_PUSH_DIR", "HQ_CLAUDE_CLI", "HQ_CLAUDE")


def _env(root: Path, ports=(7841, 4741), test_port: int = 7881) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in OFF}
    env.update({"HQ_UNIT": f"hqchain{ports[0]}", "HQ_SUPPORT": str(root / "state"), "HQ_NO_PHONE": "1", "HQ_CALL_FIX": "off",
                "HQ_PORT": str(ports[0]), "HQ_STATUS_PORT": str(ports[1]), "HQ_TEST_PORT": str(test_port), "HQ_LABEL": "chain copy",
                "HQ_GITHUB_API": "http://127.0.0.1:9", "HQ_GITHUB_TOKEN_FILE": str(root / "no-token"),
                "HQ_UPDATE_URL": str(root / "remote-hq.git"), "HQ_CLAUDE_JSON": str(root / "claude.json")})
    env.pop("HQ_GITHUB_TOKEN", None)
    return env


def _git(cwd, *a, check=True, env=None) -> str:
    r = subprocess.run(["git", *a], cwd=str(cwd), text=True, capture_output=True, env=env)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(a)}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def _run(env, root, *a, stdin=None, timeout=300) -> subprocess.CompletedProcess:
    """A script of the copy's, from the copy."""
    return subprocess.run([PY, *map(str, a)], cwd=str(root / "HQ"), env=env, text=True, capture_output=True, input=stdin, timeout=timeout)


def _hq_files(src: Path) -> bytes:
    names = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=str(src), text=True, capture_output=True).stdout.splitlines()
    names = [n for n in names if n and not n.startswith("workspace") and (src / n).is_file() and not (src / n).is_symlink()]
    return "\n".join(names).encode()


def build(root: Path, workspace: str | None = None, standin: bool = True, ports=(7841, 4741), test_port=7881) -> dict:
    """The copy: returns its environment. `workspace` is the folder to copy (the real run), else the template."""
    env = _env(root, ports, test_port)
    hq, ws = root / "HQ", root / "workspace"
    hq.mkdir(parents=True)
    (root / "state").mkdir()
    tar = subprocess.run(["tar", "-czf", "-", "-T", "-"], input=_hq_files(SRC), capture_output=True, cwd=str(SRC), env={**os.environ, "COPYFILE_DISABLE": "1"})
    if tar.returncode:
        raise RuntimeError(tar.stderr.decode()[:300])
    subprocess.run(["tar", "-xzf", "-", "-C", str(hq)], input=tar.stdout, check=True)
    if standin:  # the privacy check over a whole history takes ten minutes; the night's own flows hold it
        (hq / "app" / "privacy.py").write_text("print('Nothing personal found.')\n")
    _git(hq, "init", "-q", "-b", "dev")
    _git(hq, "config", "user.name", os.environ.get("HQ_CHAIN_NAME") or "HQ chain")
    _git(hq, "config", "user.email", os.environ.get("HQ_CHAIN_MAIL") or "chain@example.com")
    _git(hq, "add", "-A")
    _git(hq, "commit", "-q", "-m", "The copy's start", env={**env, "HQ_PRIVACY_PASSED": "1"})
    version = (hq / "VERSION").read_text().strip()
    _git(hq, "tag", "-a", f"v{version}", "-m", f"HQ {version}")
    _git(hq, "branch", "main")
    _git(hq, "branch", "nightly")
    _git(root, "clone", "-q", "--bare", str(hq), str(root / "remote-hq.git"))
    _git(hq, "remote", "add", "origin", str(root / "remote-hq.git"))
    _git(hq, "fetch", "-q", "origin")
    _git(hq, "branch", "-q", "--set-upstream-to=origin/dev", "dev")
    if workspace:
        ign = Path(workspace) / ".gitignore"  # what the workspace keeps out of git stays out of the copy too (big local-only folders)
        subprocess.run(["rsync", "-a", *(["--exclude-from", str(ign)] if ign.exists() else []), "--exclude", "*.mp4", "--exclude", "*.mp3",
                        workspace.rstrip("/") + "/", str(ws) + "/"], check=True)
        (hq / "workspace").symlink_to(ws)
    else:
        shutil.copytree(hq / "template", ws)
        (hq / "workspace").symlink_to(ws)
        (ws / "me.md").write_text("# About me\n\nName: Sam\n") if not (ws / "me.md").exists() else None
        _git(ws, "init", "-q", "-b", "main")
        _git(ws, "config", "user.name", "HQ chain")
        _git(ws, "config", "user.email", "chain@example.com")
        _git(ws, "add", "-A")
        _git(ws, "commit", "-q", "-m", "The copy's start")
    _git(root, "clone", "-q", "--bare", str(ws), str(root / "remote-ws.git"))
    if workspace:
        _git(ws, "remote", "set-url", "origin", str(root / "remote-ws.git"))
    else:
        _git(ws, "remote", "add", "origin", str(root / "remote-ws.git"))
    venv = SRC / ".venv"
    if venv.exists():
        (hq / ".venv").symlink_to(venv.resolve())
    (root / "claude.json").write_text(json.dumps({"projects": {str(ws.resolve()): {"hasTrustDialogAccepted": True}}}))
    data = ws / "HQ"
    for line in ("direct-line", "team-line", "coaching-line"):  # no phone anywhere: a text stays on the copy's thread
        (data / line).mkdir(parents=True, exist_ok=True)
        (data / line / "subscriptions.json").unlink(missing_ok=True)
    for name, change in (("feedback-box.json", lambda d: {**d, "on": False}),
                         ("backend.json", lambda d: {**d, "on": [x for x in d.get("on", []) if x != "one_way_sync"]}),
                         ("sprint.json", lambda d: {**d, "order": []})):
        p = data / name
        if p.exists():
            p.write_text(json.dumps(change(json.loads(p.read_text())), ensure_ascii=False, indent=1))
    (data / "features.json").write_text(json.dumps({**(json.loads((data / "features.json").read_text()) if (data / "features.json").exists() else {}), "on": ["agents_run"], "maker": True}))
    for a in ("jobs.py mail-off", "jobs.py on", "cycles.py set donna on off", "cycles.py set pepper on off",
              "cycles.py set moneypenny on on", "cycles.py set moneypenny hours 00:00-23:59", "cycles.py set moneypenny fix on"):
        r = _run(env, root, f"routine/{a.split()[0]}", *a.split()[1:])
        if r.returncode:
            raise RuntimeError(f"{a}: {(r.stdout + r.stderr)[-300:]}")
    return env


def set_old_aside(env, root) -> None:
    """The real run: her older orders and the repeating work aren't this run's."""
    code = ("import sys; sys.path.insert(0, 'routine')\nimport ledger\n"
            "for o in ledger.orders('moneypenny', ('open', 'now')):\n    ledger.set_order('moneypenny', o['n'], 'done', 'set aside on the copy')\n")
    subprocess.run([PY, "-c", code], cwd=str(root / "HQ"), env=env, check=True)
    t = (root / "workspace/HQ/roadmap.md")
    for n, text in re.findall(r"^- Item (\d+) · waiting[^\n]*? · added \S+ \S+ · (.*)$", t.read_text(encoding="utf8"), re.M):
        if not text.startswith("Agent cycle: moneypenny"):
            _run(env, root, "routine/schedule.py", "cancel", n)
    (root / "HQ/scratch/routine").mkdir(parents=True, exist_ok=True)
    (root / "HQ/scratch/routine/nightly-started").write_text(dt.date.today().isoformat())


# -- the stand-in for the model -----------------------------------------------------------------------------------

STANDIN = r'''#!/usr/bin/env python3
import json, os, re, subprocess, sys
prompt = sys.stdin.read()
HQ, PY = os.environ["HQ_CHAIN_HQ"], sys.executable
def out(d): print(json.dumps(d), flush=True)
def run(name, *a, stdin=None):
    r = subprocess.run([PY, f"{HQ}/routine/{name}", *a], capture_output=True, text=True, input=stdin, cwd=HQ)
    open(os.environ["HQ_CHAIN_LOG"], "a").write(f"{name} {' '.join(a)[:120]}: {r.returncode} {(r.stdout + r.stderr)[-200:]}\n")
    return r
out({"type": "system", "subtype": "init", "session_id": "s-chain"})
n = (re.search(r"This is job (\d+)", prompt) or [0, "0"])[1]
words = os.environ["HQ_CHAIN_WORDS"]
if "bigger session" in prompt.split("\n", 1)[0]:
    done = []
    for k, said in re.findall(r"^(\d+)\. start: \"(.*)\" \(", prompt, re.M):
        row = (f"The page says it better. His words: \"{said}\" What's asked: the wording. Done means: the page says it, example: empty schedule. "
               "Test: the flow. Why: his words. Out of scope: the rest. Touches: status/index.html, no call line restart. Size: small. Waits on: nothing. "
               "Privacy: code only. My own additions: none. Sources: status/index.html. HOLE: which card. Nothing else.")
        run("jobs.py", "write-row", "--order", k, row)
        done.append(int(k))
    run("cycles.py", "plan", "moneypenny", json.dumps({"picks": [], "let_go": [], "steps": [], "questions": [], "orders_done": done}))
elif re.search(r"This run: round \d+ of at most", prompt):
    label = re.search(r"on one row of the planning, (\S+?)\.", prompt)[1]
    run("review.py", "add", label, stdin="FILLED: which card.\n")
elif "your mark comes second" in prompt:
    label = re.search(r"This run: one row, (\S+?)\.", prompt)[1]
    run("sprint.py", "ready", label)
elif "planned for the team at the sprint planning" in prompt:
    label = re.search(r"(?:^|\s)([FH]\d+) on the HQ roadmap", prompt)[1]
    p = f"{HQ}/{os.environ['HQ_CHAIN_PAGE']}"
    s = open(p, encoding="utf8").read()
    open(p, "w", encoding="utf8").write(s.replace(os.environ["HQ_CHAIN_OLD"], os.environ["HQ_CHAIN_NEW"], 1))
    log = f"{HQ}/CHANGELOG.md"
    t = open(log, encoding="utf8").read()
    open(log, "w", encoding="utf8").write(t.replace("## Coming next\n", f"## Coming next\n\n- The page says it better ({label}).\n", 1))
    subprocess.run(["git", "add", "-A", "status", "CHANGELOG.md"], cwd=HQ)
    subprocess.run(["git", "commit", "-q", "-m", f"{label}: the page says it better"], cwd=HQ)
    run("proof.py", "run", n)
    subprocess.run(["git", "push", "-q", "origin", "dev"], cwd=HQ, env={**os.environ, "HQ_PRIVACY_PASSED": "1"})
    run("jobs.py", "done", n)
elif prompt.lstrip().startswith("let's go") and re.search(r"QA of (\S+) \(F56\)", prompt):
    label = re.search(r"QA of (\S+) \(F56\)", prompt)[1]
    run("qa.py", "pass", label, "the page's wording, tried for real", "--example", "empty schedule", "--ran", "the page", "--got", os.environ["HQ_CHAIN_NEW"], "--job", n, "--compared", "the empty card, 1 of 1 right")
out({"type": "result", "subtype": "success", "is_error": False, "result": "Done."})
'''

RUNNER = r'''#!/usr/bin/env python3
import sys
args = sys.argv[1:]
print("== Result")
print("1 of 1 passed")
'''


def standin_files(root: Path, env: dict) -> dict:
    """The stand-ins' files and environment."""
    b = root / "bin"
    b.mkdir(exist_ok=True)
    (b / "claude").write_text(STANDIN)
    (b / "runner").write_text(RUNNER)
    (b / "open-window").write_text("#!/bin/bash\nnohup /bin/bash \"$1\" >/dev/null 2>&1 &\n")
    for f in ("claude", "runner", "open-window"):
        (b / f).chmod(0o755)
    local = root / "HQ" / "local"
    local.mkdir(exist_ok=True)
    shutil.copy(b / "open-window", local / "open-window")
    env.update({"HQ_CLAUDE": str(b / "claude"), "HQ_PROOF_RUNNER": str(b / "runner"), "HQ_CHAIN_HQ": str(root / "HQ"), "HQ_CHAIN_LOG": str(root / "standin.log"),
                "HQ_CHAIN_WORDS": WORDS, "HQ_CHAIN_OLD": OLD, "HQ_CHAIN_NEW": NEW, "HQ_CHAIN_PAGE": PAGE,
                "HQ_REVIEW_FAKE": "auto", "HQ_REVIEW_QUIET": "0", "HQ_LOOK": "0", "HQ_PROOF_ON": "1", "HQ_PROOF_ROOT": str(root / "HQ"),
                "HQ_PRIVACY_PASSED": "1"})
    # a saved usage reading under the lines, so the routine may start a job
    (root / "HQ/scratch/routine").mkdir(parents=True, exist_ok=True)
    (root / "HQ/.status").mkdir(exist_ok=True)
    (root / "HQ/.status/usage.json").write_text(json.dumps({
        "checkedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"), "by": "the chain's stand-in", "readable": True, "plan": "Max",
        "limits": [{"label": "Weekly · all models", "percent": 5, "resetsAt": (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=3)).isoformat(timespec="seconds").replace("+00:00", "Z")}]}))
    (root / "HQ/scratch/routine/nightly-started").write_text(dt.date.today().isoformat())
    for key, v in (("daily", "20"), ("weekly", "50")):  # a fresh copy has no history, so its first estimate is over her share
        _run(env, root, "routine/cycles.py", "set", "moneypenny", key, v)
    return env


# -- the driver --------------------------------------------------------------------------------------------------

def his_text(env, root, words: str, real: bool) -> None:
    """His text on Pepper's line. With the model she decides by herself; the stand-in writes what she writes."""
    code = ("import sys; sys.path.insert(0, 'app')\nimport coaching\n" + ("coaching.send(sys.argv[1])\n" if real else "coaching.add('me', sys.argv[1], '')\n"))
    subprocess.run([PY, "-c", code, words], cwd=str(root / "HQ"), env=env, check=True, capture_output=True)
    if not real:
        r = _run({**env, "HQ_DIRECT_AGENT": "pepper"}, root, "routine/cycles.py", "order", "moneypenny", "start", words)
        if r.returncode:
            raise RuntimeError(r.stderr[-300:])


def tick(env, root) -> None:
    subprocess.run([PY, "routine/tick.py"], cwd=str(root / "HQ"), env=env, capture_output=True, timeout=240)


def follow(env, root, what: str) -> list[dict]:
    code = "import sys, json; sys.path.insert(0, 'routine')\nimport trail\nprint(json.dumps(trail.follow(sys.argv[1])))"
    r = subprocess.run([PY, "-c", code, what], cwd=str(root / "HQ"), env=env, text=True, capture_output=True)
    return json.loads(r.stdout or "[]")


def items(root) -> list[tuple[str, str, str]]:
    t = (root / "workspace/HQ/roadmap.md").read_text(encoding="utf8")
    return re.findall(r"^- Item (\d+) · waiting[^\n]*? · at (\S+ \S+) · added \S+ \S+ · (.*)$", t, re.M)


def soon(minutes: int = 1) -> str:
    return (dt.datetime.now() + dt.timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")


def bring(env, root, marker: str) -> bool:
    """The clock: a planned item whose words hold `marker` is brought to now."""
    for n, at, text in items(root):
        if marker in text and dt.datetime.strptime(at, "%Y-%m-%d %H:%M") > dt.datetime.now():
            _run(env, root, "routine/schedule.py", "move", n, soon())
            return True
    return False


def her_session(env, root) -> None:
    """Her Thursday comes now: the session's time moves, through her own setting."""
    _run(env, root, "routine/cycles.py", "set", "moneypenny", "session_every", "day")
    _run(env, root, "routine/cycles.py", "set", "moneypenny", "session_at", (dt.datetime.now() + dt.timedelta(minutes=1)).strftime("%H:%M"))


def night(env, root, real: bool) -> None:
    """The night's check on the copy: the real flows on the real run, a green record for the stand-in."""
    if real:
        subprocess.run([PY, "routine/nightly.py", "run", "--routine"], cwd=str(root / "HQ"), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=7200)
        return
    d = root / "HQ/scratch/nightly"
    d.mkdir(parents=True, exist_ok=True)
    (d / "last.json").write_text(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M"), "ran": 1, "passed": 1, "failed": [], "exit": 0, "round": 1, "rounds_max": 3}))


STEPS = ("order", "written", "review", "ready", "planned", "job added", "job done", "qa", "release")


def hand_offs(env, root, label: str, want_round: bool = False) -> list[str]:
    """What's missing, each hand-off read from its record under the one id and from what the record points at. Empty: the chain held."""
    lines = follow(env, root, label)
    if not lines:
        return [f"nothing on the record for {label}"]
    no = []
    ids = {d["id"] for d in lines}
    if len(ids) != 1:
        no.append(f"more than one id: {sorted(ids)}")
    first = lines[0]
    if first.get("step") != "order" or not first.get("words"):
        no.append("his words aren't the record's first line")
    get = lambda s, **kw: next((d for d in lines if d.get("step") == s and all(d.get(k) == v for k, v in kw.items())), None)  # noqa: E731
    for s in ("written", "ready", "planned"):
        if not get(s):
            no.append(f"no {s} on the record")
    if not get("review", verdict="pass"):
        no.append("no review pass on the record")
    if want_round and not (get("review", verdict="flag") and get("round")):
        no.append("no flag and round on the record")
    done = get("job", state="done")
    if not done or not done.get("commit"):
        no.append("no job done with a commit on the record")
    else:
        rec = root / "HQ/.status/proofs" / f"job-{done['job']}.json"
        try:
            green = json.loads(rec.read_text())
            if not str(green.get("head", "")).startswith(done["commit"]) or not green.get("green", green.get("ok")):
                no.append(f"job {done['job']}'s record isn't green for {done['commit']}")
        except (OSError, ValueError):
            no.append(f"job {done['job']} has no proof record")
    qa = get("qa", state="passed")
    if not qa:
        no.append("no QA pass on the record")
    elif done and qa.get("job") == done.get("job"):
        no.append("QA was the builder's own job")
    rel = get("release")
    if not rel or not rel.get("tag"):
        no.append("no release with a tag on the record")
    else:
        got = subprocess.run(["git", "-C", str(root / "remote-hq.git"), "rev-parse", "-q", "--verify", f"refs/tags/{rel['tag']}"], text=True, capture_output=True).stdout.strip()
        if not got:
            no.append(f"the tag {rel['tag']} isn't on the stand-in remote")
        else:
            page = subprocess.run(["git", "-C", str(root / "remote-hq.git"), "show", f"{rel['tag']}:{PAGE}"], text=True, capture_output=True).stdout
            if NEW not in page:
                no.append(f"{rel['tag']} doesn't hold the change")
    return no


def where_it_stands(env, root, label: str | None) -> str:
    out = []
    if label:
        out += [f"{d.get('step')}:{d.get('state') or d.get('verdict') or ''}" for d in follow(env, root, label)]
    return " ".join(out)


def order_item(env, root) -> tuple[str | None, str | None]:
    """The order's id and the row written for it, read from the record."""
    code = ("import sys, json; sys.path.insert(0, 'routine')\nimport trail\n"
            "L = trail.lines()\no = [d for d in L if d.get('step') == 'order' and d.get('agent') == 'moneypenny']\n"
            "i = o[-1]['id'] if o else None\nw = [d for d in L if d.get('id') == i and d.get('step') == 'written']\n"
            "print(json.dumps([i, w[0]['label'] if w else None]))")
    r = subprocess.run([PY, "-c", code], cwd=str(root / "HQ"), env=env, text=True, capture_output=True)
    return tuple(json.loads(r.stdout or "[null, null]"))


def standin_run(root: Path, deadline_s: int = 280) -> dict:
    """The chain with stand-ins, the routine's real tick by hand once it's quiet. Returns {"label", "missing", "stopped"}."""
    env = build(root, ports=(7843, 4743), test_port=7883)
    env = standin_files(root, env)
    env["HQ_RELEASE_MINUTE"] = "0"
    his_text(env, root, WORDS, real=False)
    her_session(env, root)
    t0, label, said, night_done, released = time.time(), None, False, False, False
    clock = time.time()
    while time.time() - t0 < deadline_s:
        clock += 301  # the review's own clock: a round waits for five quiet minutes
        env["HQ_REVIEW_NOW"] = str(int(clock))
        tick(env, root)
        _, label = order_item(env, root)
        if not label:
            time.sleep(1)
            continue
        have = {d.get("step") for d in follow(env, root, label)}
        if "ready" in have and "planned" not in have:  # his yes at the sprint planning
            r = _run(env, root, "routine/sprint.py", "plan", label)
            if r.returncode:
                return {"label": label, "missing": [f"the plan refused: {(r.stdout + r.stderr)[-200:]}"], "stopped": "planned"}
        if "planned" in have and "job" not in have:
            bring(env, root, f"{label} on the HQ roadmap")
        if "qa" in have and any(d.get("state") == "passed" for d in follow(env, root, label)) and not released:
            night(env, root, real=False)
            r = _run(env, root, "routine/release.py", "main")
            released = True
            (root / "release.out").write_text(r.stdout + r.stderr)
        if released:
            break
        time.sleep(1)
    missing = hand_offs(env, root, label, want_round=True) if label else ["no row was written"]
    return {"label": label, "missing": missing, "stopped": where_it_stands(env, root, label)}


def real_run(root: Path, workspace: str, deadline_s: int = 14400) -> dict:
    """The real model, the real tick every minute, nobody helping but the clock and his two yeses. Printed as it goes."""
    env = build(root, workspace=workspace, standin=False)
    set_old_aside(env, root)
    for src in ("job-usage.json", "job-estimates.json", "usage.json", "usage-rate.json"):
        p = Path(workspace).resolve().parent / ".status" / src
        p = p if p.exists() else (SRC / ".status" / src)
        if p.exists():
            (root / "HQ/.status").mkdir(exist_ok=True)
            shutil.copy(p, root / "HQ/.status" / src)
    loop = root / "tick-loop.sh"
    loop.write_text("#!/bin/bash\ncd \"$1\"\nwhile true; do\n  " + PY + " routine/tick.py >> ../tick.log 2>&1\n  sleep 60\ndone\n")
    p = subprocess.Popen(["bash", str(loop), str(root / "HQ")], env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    (root / "pids").write_text(f"{p.pid}\n")
    say = lambda s: print(time.strftime("%H:%M"), s, flush=True)  # noqa: E731
    his_text(env, root, WORDS + " Can we change that?", real=True)
    say("his text is on Pepper's line")
    t0, label, planned, nighted, released = time.time(), None, False, False, False
    while time.time() - t0 < deadline_s:
        time.sleep(30)
        item, lab = order_item(env, root)
        if item and not label and not lab and not (root / "session-moved").exists():
            her_session(env, root)
            (root / "session-moved").touch()
            say("the clock: her Thursday session brought to now")
        if not lab:
            continue
        label = lab
        lines = follow(env, root, label)
        have = {d.get("step") for d in lines}
        if "ready" in have and not planned:
            subprocess.run([PY, "app/direct_line.py", "--team", "me"], cwd=str(root / "HQ"), env=env, text=True, capture_output=True,
                           input=json.dumps({"text": f"Morning. {label} is such a small one, yes plan it for tonight please, just that one."}))
            subprocess.run([str(root / "HQ/.venv/bin/python"), "app/direct_line.py", "--team", "reply"], cwd=str(root / "HQ"), env=env, capture_output=True, timeout=300)
            planned = True
            say(f"his yes at the sprint planning for {label}, typed by the driver")
        if "planned" in have and "job" not in have and bring(env, root, f"{label} on the HQ roadmap"):
            say("the clock: the night's 22:00 brought to now")
        if any(d.get("step") == "qa" and d.get("state") == "passed" for d in lines) and not nighted:
            nighted = True
            say("the night's check starts on the copy")
            night(env, root, real=True)
            say("the night's check ended; the release item brought to now")
            bring(env, root, "the daily release on the nightly line")
        if "release" in have:
            released = True
            break
    missing = hand_offs(env, root, label) if label else ["no row was written"]
    say(f"{label}: " + ("every hand-off holds" if not missing else "; ".join(missing)))
    return {"label": label, "missing": missing, "released": released}


def clean(root: Path, ports=(7841, 4741)) -> None:
    p = root / "pids"
    if p.exists():
        for line in p.read_text().split():
            try:
                os.kill(int(line), signal.SIGTERM)
            except (OSError, ValueError):
                pass
    env = _env(root, ports)
    port = env["HQ_STATUS_PORT"]
    r = subprocess.run(["ss", "-Hltnp", f"sport = :{port}"], text=True, capture_output=True)
    for pid in re.findall(r"pid=(\d+)", r.stdout):
        try:
            os.kill(int(pid), signal.SIGTERM)
        except OSError:
            pass
    shutil.rmtree(root, ignore_errors=True)


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "standin" and len(argv) > 1:
        got = standin_run(Path(argv[1]))
        print(json.dumps(got, ensure_ascii=False))
        return 1 if got["missing"] else 0
    if cmd == "real" and len(argv) > 3 and argv[2] == "--workspace":
        got = real_run(Path(argv[1]), argv[3])
        print(json.dumps(got, ensure_ascii=False))
        return 1 if got["missing"] else 0
    if cmd == "check" and len(argv) > 2:
        root = Path(argv[1])
        no = hand_offs(_env(root), root, argv[2])
        print("\n".join(no) or "Every hand-off holds.")
        return 1 if no else 0
    if cmd == "clean" and len(argv) > 1:
        clean(Path(argv[1]), (int(argv[2]), int(argv[3])) if len(argv) > 3 else (7841, 4741))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
