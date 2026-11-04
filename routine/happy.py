#!/usr/bin/env python3
"""H313 (4 November 2026): the happy flows, the 17 he asked for, run for real.

His words of 9 October 2026 asked for a handful of happy flows: the minimum that makes the app usable, run before every update.
Over a month every feature added its own test under that name, until there were 384, all with stand-ins, and the ones that needed
a real Claude reply were kept out of the night. So the ones he asked for didn't run, and 1.0 shipped with his "now" to Moneypenny
broken. His decisions of 4 November 2026: only these 17 are the happy flows. They run for real, with the real model, after every
bug fix and every feature, as the build's gate (routine/proof.py). The others are the detailed flows (app/happy_flows.py keeps its
file name for now) and run at night (routine/nightly.py). A pass with stand-ins isn't a pass, and a line "not tried" holds QA and
the release until it's run for real.

    python3 routine/happy.py list               the 17, which flows drive each, and what can't be driven yet
    python3 routine/happy.py run [--only 1,5]   run them (behind the test wall, on a copy, with the real model); exit 0 only when
                                                every one asked for is green, nothing "not tried"
    python3 routine/happy.py flows              the flow numbers the gate runs here (for proof.py)
    python3 routine/happy.py phone [URL]        the phone's road with the laptop closed: the server's call page over the tailnet,
                                                read only (GET), nothing written

Each happy flow is driven by one or more flows of app/happy_flows.py. The steps no detailed flow drove for real are flows 601 to 608
there (a block of their own). A happy flow that can't be driven yet says why, plainly, and counts as not green. Where it runs:
"any" here, "linux" only on the Linux server (a fresh install), "after" a flow another branch brings (named by number: it joins
by itself once that flow is in app/happy_flows.py). Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
HQ = os.path.dirname(HERE)
sys.path.insert(0, HERE)

# (number, what he approved, the flows that drive it, what's still not driven or None). His wording, 4 November 2026.
HAPPY = (
    (1, "A call from the phone: the greeting, a spoken answer, the notes saved after hanging up", [1, 2, 3, 601], None),
    (2, "Typing on a call gets an answer", [22], None),
    (3, "Something that needs his yes asks first; a no does nothing", [5], None),
    (4, "A dropped call still leaves its notes", [602], None),
    (5, "A text to Donna is answered within a minute", [603], None),
    (6, "A reminder arrives on time, with its text", [606], None),
    (7, "\"Put this on my to-do list\" lands on the right list, in his words", [604], None),
    (8, "\"What's on my calendar today\" is right, from Google Calendar", [605], None),
    (9, "A new very important mail is on the list within the hour", [],
     "the mail check reads his real Gmail through the connector; a run for real needs a made-up mailbox of HQ's own to read"),
    (10, "An idea to Moneypenny is on the planning, in his words", [481], None),
    (11, "His \"now\": the team starts it today", [481], None),
    (12, "The team builds a small change: tested, checked, live, and she texts him", [],
     "the whole chain for real (flow 295) is one small job built, checked and released on a copy with the real model: "
     "hours of the team's usage, so it isn't a gate step yet; it runs by hand"),
    (13, "He closes a job in his own words", [481], None),
    (14, "The agents' check-ins happen at their times and do something", [],
     "the agents running themselves are switched off (H298), and a real check-in is a bigger session of up to 10 minutes "
     "and 30 turns; flow 191 drives it only with a stand-in"),
    (15, "At night, work waits at the usage line", [218, 382], None),
    (16, "The Ring Fit reminder at 8 when there's no tick, and the tick works", [607], None),
    (17, "A fresh install from GitHub starts, and a first call works", [608, 3], None),
)
# Where a flow holds: 608 clones and starts a fresh HQ, the install he cares about is the server's (Linux); the rest run anywhere.
LINUX_ONLY: set[int] = set()  # 608 holds on a Mac and on Linux; on the server it is the fresh install he means
# Flows another branch brings: until they're in app/happy_flows.py the happy flows that need them are "not tried".
AFTER = {481: "nowroad (flow 481 drives his idea, his now and his close on real rows)"}
# What a flow can't prove even when green: said with its result, so a green line isn't read as more than it is.
LIMITS = {
    1: "the call runs in-process with Kokoro speaking his words, not from a phone's browser",
    8: "HQ's own calendar copy, seeded with a made-up appointment; Google itself isn't read (his real calendar)",
    10: "flow 481 stands in for Moneypenny's look (no model turn)",
    11: "flow 481 stands in for the look; the job is started, not built",
    13: "flow 481 stands in for the look",
    15: "no model on this road: the usage numbers are made up",
    17: "the clone borrows this copy's Python and models: the installer's own steps run in flow 43 with its steps simulated; "
        "the first call (flow 3) is on this commit, not the clone's",
}


def _flows_table() -> set[int]:
    """The flow numbers app/happy_flows.py has, read from its text (no import: it's heavy)."""
    text = open(os.path.join(HQ, "app", "happy_flows.py"), encoding="utf8").read()
    return {int(n) for n in re.findall(r"^    (\d+): \(", text, re.M)}


def plan(only: list[int] | None = None, linux: bool | None = None) -> list[dict]:
    """Each happy flow asked for: its flows to run here, or why it's not tried."""
    linux = sys.platform.startswith("linux") if linux is None else linux
    have = _flows_table()
    out = []
    for n, name, flows, why in HAPPY:
        if only and n not in only:
            continue
        p = {"n": n, "name": name, "flows": list(flows), "not_tried": why, "limit": LIMITS.get(n)}
        missing = [f for f in flows if f not in have]
        if not why and missing:
            p["not_tried"] = "waits for " + "; ".join(AFTER.get(f, f"flow {f}") for f in missing)
        elif not why and not linux and any(f in LINUX_ONLY for f in flows):
            p["not_tried"] = "runs on the Linux server (the fresh install there): python3 routine/happy.py run --only 17"
        if p["not_tried"]:
            p["flows"] = []
        out.append(p)
    return out


def gate_flows(linux: bool | None = None) -> list[int]:
    """The flow numbers the build's gate runs here: every happy flow that can be driven."""
    return sorted({f for p in plan(linux=linux) for f in p["flows"]})


def gate_args(linux: bool | None = None) -> list[str]:
    """For proof.py: the happy flows' own flows, for real (no --quick)."""
    return ["--only", ",".join(map(str, gate_flows(linux)))]


def not_tried(linux: bool | None = None) -> list[str]:
    """For proof.py and qa: every happy flow that isn't run for real here, with why. Each one holds QA and the release."""
    return [f"happy flow {p['n']} not tried: {p['not_tried']}" for p in plan(linux=linux) if p["not_tried"]]


def results(out: str) -> dict[int, tuple[str, float, str]]:
    """From a run's output: {flow: (PASS or FAIL, seconds, its note)}."""
    tail = out.rpartition("\n== Result")[2]
    got: dict[int, list] = {}
    for m in re.finditer(r"^\s*(\d+)\s+.*?\s(PASS|FAIL)\s+(\d+) s", tail, re.M):
        got[int(m.group(1))] = [m.group(2), float(m.group(3)), ""]
    for m in re.finditer(r"^\s{6}\s*(\d+): (.*)$", tail, re.M):
        if int(m.group(1)) in got:
            got[int(m.group(1))][2] = m.group(2)
    return {k: tuple(v) for k, v in got.items()}


def judge(p: list[dict], res: dict) -> list[dict]:
    """Each happy flow's verdict: green only when every one of its flows passed for real."""
    out = []
    for h in p:
        if h["not_tried"]:
            out.append({**h, "status": "NOT TRIED", "secs": 0.0, "why": h["not_tried"]})
            continue
        rows = [(f, *res.get(f, ("NOT RUN", 0.0, "the run didn't reach it"))) for f in h["flows"]]
        bad = [f"{f}: {s} {note}" for f, s, _, note in rows if s != "PASS"]
        out.append({**h, "status": "FAIL" if bad else "PASS", "secs": sum(r[2] for r in rows),
                    "why": "; ".join(bad) or "; ".join(f"{f}: {note}" for f, _, _, note in rows)})
    return out


def _python() -> str:
    venv = os.path.join(HQ, ".venv", "bin", "python")
    return venv if os.path.exists(venv) else sys.executable


def made_up_workspace() -> str | None:
    """An HQ with no workspace (a fresh checkout, a worktree): a made-up one from the template, so the run never needs his."""
    ws = os.path.join(HQ, "workspace")
    if os.environ.get("HQ_WORKSPACE") or os.path.exists(ws):
        return None
    import shutil
    shutil.copytree(os.path.join(HQ, "template"), ws)
    subprocess.run(["git", "init", "-q"], cwd=ws)
    return ws


def run(only: list[int] | None = None, keep: bool = False) -> int:
    made = made_up_workspace()
    if made:
        print(f"No workspace here: a made-up one from the template, {made}")
    p = plan(only)
    flows = sorted({f for h in p for f in h["flows"]})
    out, t = "", time.time()
    if flows:
        cmd = [_python(), os.path.join(HQ, "app", "happy_flows.py"), "--only", ",".join(map(str, flows))] + (["--keep"] if keep else [])
        print(f"== The happy flows, for real: flows {flows}", flush=True)
        proc = subprocess.Popen(cmd, cwd=HQ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            out += line
            sys.stdout.write(line)
        proc.wait()
    verdicts = judge(p, results(out))
    real = re.findall(r"(\d+) real model runs, (\d+) stopped at the stand-in", out)
    print("\n== The happy flows")
    for v in verdicts:
        print(f" {v['n']:>2}  {v['status']:<9} {v['secs'] / 60:5.1f} min  {v['name']}")
        print(f"      {v['why']}")
        if v["status"] == "PASS" and v["limit"]:
            print(f"      what this doesn't prove: {v['limit']}")
    green = [v for v in verdicts if v["status"] == "PASS"]
    print(f"\n{len(green)} of {len(verdicts)} green · {sum(v['status'] == 'NOT TRIED' for v in verdicts)} not tried"
          + (f" · {real[-1][0]} real model runs, {real[-1][1]} stopped at the stand-in" if real else "")
          + f" · {(time.time() - t) / 60:.1f} min")
    return 0 if len(green) == len(verdicts) else 1


def phone(url: str = "") -> int:
    """The phone's road with the laptop closed: the server's call page over the tailnet, read only. Never a call (that would be
    a real call on his live line), never a write."""
    url = (url or os.environ.get("HQ_PHONE_URL") or "").rstrip("/")
    if not url:
        try:
            st = subprocess.run(["ssh", os.environ.get("HQ_SERVER", "openclaw-vps"), "tailscale serve status"],
                                capture_output=True, text=True, timeout=30).stdout
            m = re.search(r"(https://\S+:8443)\s+\(tailnet only\)\s*\n\|-- / proxy http://127\.0\.0\.1:7860", st)
            url = m.group(1) if m else ""
        except Exception as e:
            print(f"The server's address: {e!r}")
    if not url:
        print("The phone's road: no address for the server's call line (set HQ_PHONE_URL).")
        return 1
    try:
        with urllib.request.urlopen(url + "/", timeout=20) as r:
            body = r.read().decode("utf8", "replace")
            ok = r.status == 200 and "<title>HQ</title>" in body
    except Exception as e:
        print(f"The phone's road: {url} didn't answer: {e!r}")
        return 1
    print(f"The phone's road: {url} answers over the tailnet with the call page" if ok else f"The phone's road: {url} isn't HQ's call page")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "list"
    only = None
    if "--only" in argv:
        only = [int(x) for x in argv[argv.index("--only") + 1].split(",") if x.strip()]
    if cmd == "list":
        for h in plan(only):
            print(f" {h['n']:>2}  {h['name']}")
            print(f"      {'not tried: ' + h['not_tried'] if h['not_tried'] else 'flows ' + ', '.join(map(str, h['flows']))}")
        return 0
    if cmd == "flows":
        print(",".join(map(str, gate_flows())))
        return 0
    if cmd == "run":
        return run(only, keep="--keep" in argv)
    if cmd == "phone":
        return phone(argv[1] if len(argv) > 1 else "")
    if cmd == "json":
        print(json.dumps(plan(only), indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
