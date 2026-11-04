"""nowroad: Moneypenny's own model on his real 17:42 text, on a throwaway copy, as in production (direct_line.py --team reply). The copy is put back
to the moment he sent it: his line the newest on her line, the row she wrote from it taken off. Then the copy's routine minute, to see the job start."""
import json, os, re, subprocess, sys, time
from pathlib import Path
HQ = Path.home() / "hq-nowroad"
sys.path.insert(0, str(HQ / "routine"))
import nowroad, hqpaths

root = Path(sys.argv[1]).resolve()
T0 = time.time()
def say(w):
    print(f"{time.strftime('%H:%M:%S')} +{int(time.time() - T0):4d}s  {w}", flush=True)

env = nowroad.copy(root, os.path.realpath(str(Path.home() / "HQ" / "workspace")))
ws = root / "workspace"
th = ws / "HQ/team-line/thread.jsonl"
lines = th.read_text(encoding="utf8").splitlines()
i = max(k for k, l in enumerate(lines) if '"from": "me"' in l and "lets run it immediately" in l)
th.write_text("\n".join(lines[:i + 1]) + "\n", encoding="utf8")
his = json.loads(lines[i])
say(f"the copy as at {time.strftime('%H:%M', time.localtime(his['at']))}: his text the newest on her line: {his['text'][:90]!r}…")
road = ws / "HQ/roadmap.md"
if "--fresh" in sys.argv:
    t = road.read_text(encoding="utf8")
    f146 = next(l for l in t.split("\n") if re.match(r"^\| [^|]* \| F146 ", l))
    road.write_text(t.replace(f146 + "\n", "", 1), encoding="utf8")
    say("F146 taken off the copy's planning, as before she wrote it")
else:
    st = json.loads(subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'routine')\nimport review\nprint(json.dumps(review.states()['F146']))"],
                                   cwd=str(root / "HQ"), env=env, text=True, capture_output=True).stdout)
    say(f"F146 as on the live planning: {st['state']}, {len(st['findings'])} findings")
    cmd = [str(root / "HQ/routine/jobs.py"), "send-row", "F146", "--not-ready", "--now", "--said", "Please give it to the team and lets run it immediately once it’s ready."]
    v, why = nowroad.policy(root, env, "python3 " + " ".join(cmd))
    r0 = subprocess.run([sys.executable, *cmd], cwd=str(ws), env=nowroad.her_env(env, root), text=True, capture_output=True)
    say(f"(a) a send without rounds, as her text would run it: policy {v}; exit {r0.returncode}: {(r0.stdout + r0.stderr).strip()[:500]}")
real = env["NOWROAD_REAL_CLAUDE"]
renv = {**env, "HQ_CLAUDE": real}
t1 = time.time()
r = subprocess.run([str(HQ / ".venv/bin/python"), "app/direct_line.py", "--team", "reply"], cwd=str(root / "HQ"), env=renv, text=True,
                   capture_output=True, timeout=1800)
say(f"her reply took {int(time.time() - t1)} s, exit {r.returncode}")
(root / "reply.out").write_text(r.stdout + "\n----\n" + r.stderr)
ans = [json.loads(l) for l in th.read_text(encoding="utf8").splitlines() if l.strip()]
mine = [m for m in ans if m.get("from") == "agent" and m.get("at", 0) > his["at"]]
for m in mine:
    say("SHE TEXTS BACK: " + m["text"].replace("\n", " / ")[:1500])
proj = Path.home() / ".claude/projects" / ("-" + str(ws).strip("/").replace("/", "-"))
for f in sorted(proj.glob("*.jsonl"), key=lambda x: x.stat().st_mtime)[-1:]:
    for l in f.read_text().splitlines():
        d = json.loads(l)
        for x in ((d.get("message") or {}).get("content") or []) if isinstance((d.get("message") or {}).get("content"), list) else []:
            if x.get("type") == "tool_use":
                say("HER COMMAND: " + str((x.get("input") or {}).get("command") or x.get("input"))[:600])
            elif x.get("type") == "tool_result":
                say("  -> " + str(x.get("content"))[:500].replace("\n", " / "))
t = road.read_text(encoding="utf8")
rows = [l for l in t.split("\n") if re.match(r"^\| ⬜ \| F14[6-9] ", l)]
for l in rows:
    c = hqpaths.cells(l)
    say(f"row {c[1][:60]}…: {c[2][:200]!r}… | model cell {c[3][:40]!r}")
jobs = re.findall(r"^- Job (\d+) · ([^·]*) · agreed [^·]* · (.*)$", t, re.M)
new = [j for j in jobs if not j[1].startswith("cancelled")]
for j in new:
    say(f"job {j[0]} {j[1].strip()}: {j[2][:400]}")
log = [l for l in (r.stdout + r.stderr).splitlines() if "policy" in l.lower() or "refused" in l.lower()][:20]
for l in log:
    say("log: " + l[:300])
if new:
    n = new[-1][0]
    for k in range(8):
        subprocess.run([sys.executable, "routine/tick.py"], cwd=str(root / "HQ"), env=env, capture_output=True, timeout=300)
        st = re.search(rf"^- Job {n} · ([^·]*)", road.read_text(encoding="utf8"), re.M).group(1).strip()
        if st.startswith("running"):
            jl = (root / "team-job.log").read_text() if (root / "team-job.log").exists() else ""
            say(f"job {n} {st}; its chat: {'started' if f'job {n}' in jl else 'NOT started'}")
            subprocess.run([sys.executable, "routine/jobs.py", "stop", n], cwd=str(root / "HQ"), env=env, capture_output=True)
            print("RESULT: PASS")
            break
        say(f"tick {k + 1}: job {n} {st}")
        time.sleep(20)
    else:
        print("RESULT: the job didn't start")
else:
    print("RESULT: no job")
