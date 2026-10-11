#!/usr/bin/env python3
"""H33: fill in the Jobs row of the routines graph for the time before the status server wrote down
each job's state every minute. Written once (10 October 2026); safe to run again.

Where the data comes from:
  - when a job started: the time its prompt was written (scratch/routine/job-N.prompt);
  - when it finished, and how: its line in the queue ("done 16:19", "stopped 21:40", "ended …");
  - what it was doing in between: every saved version of roadmap.md in git. Each version's status block
    says the state, and its newest log line says from when (set-status.py writes both at once).
So it is as fine-grained as the commits: a state that came and went between two commits is missed.

Writes .status/jobs-backfill.json: {"made": t, "segments": [{"n", "st", "start", "end"}], "texts": {n: the job}}. The status
server only uses it for the time before its own minute-by-minute record starts.
    python3 "status/backfill-jobs.py"
"""
import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(HERE / "routine"))
import hqpaths  # M1: the roadmap and its history are in the workspace (his own repo)
REPO = Path(hqpaths.FOLDER)
OUT = HERE / ".status" / "jobs-backfill.json"
STATES = ["BUILDING", "TESTING", "RELEASING", "WAITING", "DONE", "STOPPED"]
JOB = re.compile(r"^- Job (\d+) · (.+?) · agreed (\S+) (\S+) · (.*)$", re.M)


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True).stdout


def at(day: dt.date, hhmm: str, not_before: float | None = None) -> float:
    h, m = map(int, hhmm.split(":"))
    t = dt.datetime.combine(day, dt.time(h, m)).timestamp()
    while not_before is not None and t < not_before - 120:
        t += 86400
    return t


def main() -> None:
    versions = []  # (commit time, text), oldest first
    # The roadmap's folder had another name before H54 (11 October 2026); its saved versions are there.
    paths = ("HQ/roadmap.md", "Jarvis VA/roadmap.md")
    for line in reversed(git("log", "--format=%H %ct", "--", *paths).split("\n")):
        if not line.strip():
            continue
        h, ct = line.split()
        for path in paths:
            try:
                versions.append((int(ct), git("show", f"{h}:{path}")))
                break
            except subprocess.CalledProcessError:
                pass
    now_text = Path(hqpaths.ROADMAP).read_text()
    versions.append((int(dt.datetime.now().timestamp()), now_text))

    starts, ends, events, texts = {}, {}, {}, {}
    for f in (HERE / "scratch" / "routine").glob("job-*.prompt"):
        starts[int(f.stem.split("-")[1])] = f.stat().st_mtime
    for ct, text in versions:
        head = text.split("\n---\n", 1)[0]
        h1 = next((l for l in head.splitlines() if l.startswith("# ")), "")
        state = next((s for s in STATES if s in h1.upper()), None)
        times = re.findall(r"^- (\d\d:\d\d) ", head, re.M)
        day = dt.date.fromtimestamp(ct)
        for m in JOB.finditer(text):
            n, st = int(m.group(1)), m.group(2)
            texts[n] = m.group(5)[:300]
            fin = re.match(r"(done|stopped|ended|cancelled) (\d\d:\d\d)", st)
            if fin and n in starts:
                ends[n] = (fin.group(1), at(dt.date.fromtimestamp(starts[n]), fin.group(2), starts[n]))
            if st.startswith(("running", "stop asked")) and state and n in starts:
                # The state was set at the newest log line's time (same day as the commit, or the day before).
                t = at(day, times[0]) if times else ct
                if t > ct + 120:
                    t -= 86400
                events.setdefault(n, {})[max(t, starts[n])] = state

    segments = []
    for n, start in sorted(starts.items()):
        how, end = ends.get(n, (None, None))
        if end is None and re.search(rf"^- Job {n} · (running|stop asked)", now_text, re.M):
            how, end = "running", dt.datetime.now().timestamp()  # the server's own record takes over from here
        if how == "cancelled" or end is None:
            continue  # never ran
        pts = sorted([(start, "BUILDING")] + [(t, s) for t, s in events.get(n, {}).items() if start <= t < end])
        for i, (t, s) in enumerate(pts):
            z = pts[i + 1][0] if i + 1 < len(pts) else end
            if z > t:
                if segments and segments[-1]["n"] == n and segments[-1]["st"] == s and segments[-1]["end"] >= t:
                    segments[-1]["end"] = round(z)
                else:
                    segments.append({"n": n, "st": s, "start": round(t), "end": round(z)})
        if how != "running":
            segments.append({"n": n, "st": "DONE" if how == "done" else "STOPPED", "start": round(end), "end": round(end) + 60})

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"made": round(dt.datetime.now().timestamp()), "segments": segments,
                               "texts": {n: texts[n] for n in sorted({s["n"] for s in segments}) if n in texts}}))
    jobs = sorted({s["n"] for s in segments})
    print(f"{len(segments)} pieces for jobs {jobs} from {len(versions)} versions of the roadmap -> {OUT}")


if __name__ == "__main__":
    main()
