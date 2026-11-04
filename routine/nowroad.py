#!/usr/bin/env python3
"""nowroad (4 November 2026): the road from his "now" to the team, driven on a throwaway copy of the workspace, with the real reviewer and the
real looks at his words. His design: he says it to Moneypenny ("give it to the team and let's run it immediately"), the item goes on the
planning, she gets it ready herself right away, and the team starts building it today: no sit-down, no string of questions, no wait for Friday.

Each of her steps is the command she runs from a text, judged first by the copy's own app/policy.py as Moneypenny on a text (a refusal there
is a break in the road), then run in the copy with her text's environment. The reviewer, the look at his quotes and the look at his yes are the
real model. Only the team job's own model is a stand-in (it would build for real): once the routine starts it, that's step 6, and it's stopped.

    python3 routine/nowroad.py run ROOT [--workspace PATH] [--label F146] [--rounds 3]    the road; ROOT is a new folder, cleaned after
    python3 routine/nowroad.py clean ROOT

Prints one line per step with the time, and ends with PASS or where it stopped. Nothing here touches the real workspace: it's copied.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chainrun  # noqa: E402

PY = sys.executable
PORTS, TEST_PORT = (7861, 4761), 7901
T0 = time.time()


def _noq(f):
    """A finding without its quote marks: in her words a quote is only ever his."""
    return re.sub(r"[\"“”‘’`']", "", f).rstrip(".")


def say(step, what):
    print(f"{time.strftime('%H:%M:%S')} +{int(time.time() - T0):4d}s  {step}: {what}", flush=True)


def stop(step, why):
    say(step, "STOPPED: " + why)
    print("RESULT: STOPPED at " + step)
    sys.exit(1)


STANDIN_CLAUDE = r'''#!/usr/bin/env python3
# The copy's claude: a run with a system prompt (the reviewer, a look at his words) is the real model; anything else is the team's job,
# which would build for real, so it's a stand-in that says it started and waits.
import os, re, select, sys, time
if "--system-prompt" in sys.argv:
    os.execv(os.environ["NOWROAD_REAL_CLAUDE"], ["claude", *sys.argv[1:]])
got = sys.stdin.read() if select.select([sys.stdin], [], [], 3)[0] else ""
words = " ".join(sys.argv[1:]) + " " + got
m = re.search(r"This is job (\d+)", words)
open(os.environ["NOWROAD_JOBLOG"], "a").write(f"{time.strftime('%H:%M:%S')} " + (f"job {m.group(1)}'s chat started: {words[words.find('This is job'):][:200]!r}" if m else
                                               f"another run of the routine's (not the job): {' '.join(sys.argv[1:])[:120]}") + "\n")
print('{"type": "system", "subtype": "init", "session_id": "nowroad"}', flush=True)
time.sleep(int(os.environ.get("NOWROAD_JOB_SLEEP") or 900))
'''


def copy(root: Path, workspace: str) -> dict:
    env = chainrun.build(root, workspace, standin=True, ports=PORTS, test_port=TEST_PORT)
    real = subprocess.run(["bash", "-lc", "command -v claude"], text=True, capture_output=True).stdout.strip() or "claude"
    b = root / "bin"
    b.mkdir(exist_ok=True)
    (b / "claude").write_text(STANDIN_CLAUDE)
    (b / "claude").chmod(0o755)
    (b / "open-window").write_text("#!/bin/bash\nnohup /bin/bash \"$1\" >/dev/null 2>&1 &\n")
    (b / "open-window").chmod(0o755)
    (root / "HQ" / "local").mkdir(exist_ok=True)
    (root / "HQ" / "local" / "open-window").write_text((b / "open-window").read_text())
    (root / "HQ" / "local" / "open-window").chmod(0o755)
    env.update({"HQ_CLAUDE": str(b / "claude"), "NOWROAD_REAL_CLAUDE": real, "NOWROAD_JOBLOG": str(root / "team-job.log"),
                "HQ_PRIVACY_PASSED": "1", "HQ_LOOK": "0"})  # no first looks for the copy's hundred other rows
    for a in ("cycles.py set moneypenny on off", "cycles.py set moneypenny fix off"):  # her own cycles aren't this run's: her text is
        r = chainrun._run(env, root, f"routine/{a.split()[0]}", *a.split()[1:])
        if r.returncode:
            raise RuntimeError(f"{a}: {(r.stdout + r.stderr)[-300:]}")
    # the real usage reading, so the copy's routine decides on today's real room
    src = Path(os.environ.get("NOWROAD_USAGE") or Path.home() / "HQ" / ".status" / "usage.json")  # the main's own reading, read only
    (root / "HQ" / ".status").mkdir(exist_ok=True)
    if src.exists():
        (root / "HQ" / ".status" / "usage.json").write_text(src.read_text())
    # the copy's queue: the real jobs aren't this run's (one running would hold the line)
    code = ("import sys; sys.path.insert(0, 'routine')\nimport jobs, time\n"
            "with jobs.locked():\n t, js, on = jobs.read()\n"
            " for j in js:\n  if not j['state'].startswith(jobs.FINISHED):\n   j['state'] = 'cancelled ' + time.strftime('%Y-%m-%d %H:%M')\n"
            " jobs.write(t, js, True)\n")
    r = subprocess.run([PY, "-c", code], cwd=str(root / "HQ"), env=env, text=True, capture_output=True)
    if r.returncode:
        raise RuntimeError("the copy's queue: " + r.stderr[-300:])
    return env


def her_env(env, root):
    """Her text's environment: the line she answers on, where his words count (F114)."""
    return {**env, "HQ_DIRECT_AGENT": "moneypenny", "HQ_WORDS_FROM": str(root / "workspace" / "HQ" / "team-line" / "thread.jsonl")}


def policy(root, env, cmd) -> tuple[str, str]:
    code = ("import sys, json; sys.path.insert(0, 'app'); sys.path.insert(0, 'routine')\nimport policy\n"
            "p = policy.Policy(sys.argv[1]); p.agent = 'moneypenny'; p.unattended = True; p.team_texts = True\n"
            "p.words_from = [sys.argv[3]]\n"
            "d = p.decide('Bash', {'command': sys.argv[2]}); print(json.dumps([d.verdict, d.why]))")
    r = subprocess.run([PY, "-c", code, str(root / "workspace"), cmd, str(root / "workspace/HQ/team-line")], cwd=str(root / "HQ"),
                       env=env, text=True, capture_output=True)
    try:
        v, why = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return "error", (r.stdout + r.stderr)[-400:]
    return v, why


def her(step, root, env, *argv, timeout=600) -> str:
    """One command of hers from a text: the policy first, then the command in the copy."""
    cmd = "python3 " + shlex.join([str(root / "HQ" / argv[0]), *argv[1:]])
    v, why = policy(root, env, cmd)
    if v != "allow":
        stop(step, f"the policy refuses her command on a text ({v}): {why}\n    {cmd[:300]}")
    r = subprocess.run([PY, str(root / "HQ" / argv[0]), *argv[1:]], cwd=str(root / "workspace"), env=her_env(env, root), text=True,
                       capture_output=True, timeout=timeout)
    out = (r.stdout + r.stderr).strip()
    if r.returncode:
        stop(step, f"refused ({r.returncode}): {out[-700:]}")
    return out


def his_text(root, words):
    """His text on Moneypenny's line, as the text server writes it: the driver's one stand-in for him (his real words, today's time)."""
    p = root / "workspace" / "HQ" / "team-line" / "thread.jsonl"
    with open(p, "a", encoding="utf8") as f:
        f.write(json.dumps({"at": round(time.time(), 3), "from": "me", "text": words}, ensure_ascii=False) + "\n")


def py(root, env, code, *args) -> str:
    r = subprocess.run([PY, "-c", "import sys, json; sys.path.insert(0, 'routine')\n" + code, *args], cwd=str(root / "HQ"), env=env,
                       text=True, capture_output=True, timeout=900)
    if r.returncode:
        raise RuntimeError(r.stderr[-600:])
    return r.stdout.strip()


def row_of(root, env, label):
    return json.loads(py(root, env, "import sprint\nr = next((x for x in sprint.open_rows() if x['label'] == sys.argv[1]), None)\n"
                                    "print(json.dumps(r and {'line': r['line'], 'ask': sprint.ask_of(r['line'])}))", label))


def review_state(root, env, label):
    return json.loads(py(root, env, "import review\ns = review.states().get(sys.argv[1]) or {}\n"
                                    "e = (review._state()[1].get('rows') or {}).get(sys.argv[1]) or {}\n"
                                    "print(json.dumps({**s, 'again': e.get('again'), 'cost': e.get('cost')}))", label))


def review_now(root, env, label):
    """The review the routine starts once the row has been quiet: here at once, in the foreground, the real reviewer."""
    py(root, env, "import review\nreview.tick(start=False)\nreview.review_run(sys.argv[1])", label)
    return review_state(root, env, label)


def tick(root, env):
    subprocess.run([PY, "routine/tick.py"], cwd=str(root / "HQ"), env=env, capture_output=True, timeout=300)


def run(root: Path, workspace: str, label: str, rounds: int) -> int:
    say("0 copy", f"a copy of {workspace} in {root}")
    env = copy(root, workspace)
    road = (root / "workspace/HQ/roadmap.md").read_text(encoding="utf8")
    src = next((l for l in road.split("\n") if re.match(rf"^\| [^|]* \| {label} ", l)), None)
    if not src:
        stop("0 copy", f"{label} isn't on the copy's planning")
    import hqpaths
    cs = hqpaths.cells(src)
    words = re.sub(r"^\d{1,2} \w+ \d{4} \([^)]*\):\s*", "", cs[2])  # what she wrote, without the date the program puts in front
    his = next((json.loads(l)["text"] for l in reversed((root / "workspace/HQ/team-line/thread.jsonl").read_text(encoding="utf8").splitlines())
                if '"from": "me"' in l and "team" in l and "immediately" in l), None)
    if not his:
        stop("0 copy", "his text with the now isn't on the copy's team line")
    say("0 copy", f"the row to write again: {label} ({len(words)} characters); his words: {his[:120]!r}")

    at = next((json.loads(l)["at"] for l in reversed((root / "workspace/HQ/team-line/thread.jsonl").read_text(encoding="utf8").splitlines())
               if '"from": "me"' in l and json.loads(l).get("text") == his), 0)
    if time.strftime("%Y-%m-%d", time.localtime(at)) == time.strftime("%Y-%m-%d"):
        say("1 his text", f"his own text on Moneypenny's line, as he typed it at {time.strftime('%H:%M', time.localtime(at))} today")
    else:
        his_text(root, his)
        say("1 his text", "his own words on Moneypenny's line again, with today's time (the driver's one stand-in: his text was from another day)")

    out = her("1 row", root, env, "routine/jobs.py", "write-row", words, "--bug")
    new = re.search(r"\b([FH]\d+) is on the planning", out)
    if not new:
        stop("1 row", out)
    new = new.group(1)
    row = row_of(root, env, new)
    c = hqpaths.cells(row["line"])
    say("1 row", f"{new} written; its words stand once: {c[2].count(words) == 1 and words not in ''.join(c[3:])}")
    if words in "".join(c[3:]):
        stop("1 row", "the row holds its words twice")

    quote = re.split(r"(?<=[.!?])\s+", his)[-1].strip()  # his now, word for word
    add = f'His words: "{his}" Sources: HQ/team-line/thread.jsonl (his text of {time.strftime("%-d %B %Y")}); {label}.'
    out = her("2 his words", root, env, "routine/review.py", "add", new, add)
    say("2 his words", out.splitlines()[-1][:300])
    fields = py(root, env, "import sprint\nr = next(x for x in sprint.open_rows() if x['label'] == sys.argv[1])\nprint(sprint.fields_words(r))", new)
    say("2 fields", fields.replace("\n", " / ")[:400])

    probe = her("2 reword", root, env, "routine/review.py", "reword", new,
                json.dumps({"edits": [{"old": "Out of scope: what the messages say.", "new": "Out of scope: what the messages say, and their wording."}]}))
    row2 = row_of(root, env, new)
    c2 = hqpaths.cells(row2["line"])
    say("2 reword", f"{probe.splitlines()[-1][:160]}; changed in the words: {'and their wording' in c2[2]}; other cells as they were: {c2[3:] == c[3:]}")

    st = {}
    for n in range(1, rounds + 1):
        st = review_now(root, env, new)
        say(f"3 review {n}", f"{st.get('state')} ({'again: the earlier points and the changed words' if st.get('again') else 'a first review, the five probes'}, "
                             f"${st.get('cost') or 0:.4f}): " + ("; ".join(st.get("findings") or []))[:600])
        if st.get("state") != "flagged":
            break
        if n == rounds:
            break
        answer = ("For each point, how the team settles it: " + " ".join(
            f"({i + 1}) {_noq(f)}: the team decides it the plain way while building and writes what it chose in the row's result." for i, f in enumerate(st["findings"][:3]))
            + " On an HQ where Moneypenny is off, her messages still come on her line, never Donna's.")
        out = her(f"3 answer {n}", root, env, "routine/review.py", "add", new, answer[:3800])
        say(f"3 answer {n}", out.splitlines()[-1][:200])

    if st.get("state") == "passed":
        out = her("4 ready", root, env, "routine/sprint.py", "ready", new)
        say("4 ready", out.splitlines()[-1][:200] if out else "marked")
        send = ["routine/jobs.py", "send-row", new, "--now", "--said", quote]
    else:
        say("4 ready", f"not marked: {st.get('state')} after {rounds} rounds; his now sends it with the open points on the job")
        send = ["routine/jobs.py", "send-row", new, "--not-ready", "--now", "--said", quote]
    out = her("5 his now", root, env, *send)
    job = re.search(r"Job (\d+) is ready", out)
    say("5 his now", out.splitlines()[-1][:400])
    if not job:
        stop("5 his now", out)
    job = int(job.group(1))
    text = json.loads(py(root, env, "import jobs\nprint(json.dumps(next(j for j in jobs.read()[1] if j['n'] == int(sys.argv[1]))))", str(job)))
    say("5 his now", f"job {job}: say-so for today {'yes' if text.get('sayso') else 'NO'}; the review's points on it: "
                     f"{'yes' if 'open points' in text['text'] or st.get('state') == 'passed' else 'NO'}")

    for k in range(12):
        tick(root, env)
        js = json.loads(py(root, env, "import jobs, wall\njs = jobs.read()[1]\nj = next(x for x in js if x['n'] == int(sys.argv[1]))\n"
                                      "print(json.dumps({'state': j['state'], 'why': wall.why_not(j, js)}))", str(job)))
        if js["state"].startswith(("running", "done")):
            say("6 team job", f"job {job} {js['state']}")
            log = root / "team-job.log"
            mine = [x for x in (log.read_text().splitlines() if log.exists() else []) if f"job {job}'s chat started" in x]
            say("6 team job", mine[0][:300] if mine else "the queue says running, but no chat of the job's started (yet)")
            if not mine:
                time.sleep(10)
                mine = [x for x in (log.read_text().splitlines() if log.exists() else []) if f"job {job}'s chat started" in x]
                if not mine:
                    stop("6 team job", "the queue says running, but the job's own chat never started")
            chainrun._run(env, root, "routine/jobs.py", "stop", str(job))
            tick(root, env)
            print("RESULT: PASS")
            return 0
        say("6 team job", f"tick {k + 1}: job {job} {js['state']}" + (f"; waits: {js['why']}" if js.get("why") else ""))
        time.sleep(20)
    stop("6 team job", f"job {job} didn't start")
    return 1


def main(argv):
    if len(argv) >= 2 and argv[0] == "clean":
        chainrun.clean(Path(argv[1]), PORTS)
        return 0
    if len(argv) < 2 or argv[0] != "run":
        print(__doc__)
        return 2
    root = Path(argv[1]).resolve()
    if root.exists():
        sys.exit(f"{root} is there already: give a new folder")
    opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d  # noqa: E731
    ws = opt("--workspace", str(Path.home() / "HQ" / "workspace"))
    try:
        return run(root, os.path.realpath(ws), opt("--label", "F146").upper(), int(opt("--rounds", "3")))
    finally:
        if "--keep" not in argv:
            chainrun.clean(root, PORTS)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
