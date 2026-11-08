#!/usr/bin/env python3
"""H342 (8 November 2026): her QA tests replay the real case, on a copy of the real data, where he would see it.

Why: in the week of 2 to 8 November 2026 her check sent work back 14 times against 55 passes, and in 13 of the 14 her own sealed tests
had passed while the row's own example failed on real data: the test checked a stand-in (F197: a state file instead of the status page;
F186: the program's texts, not her replies; H339: made-up nights, while a real night showed raw job texts and numbers). What is asked
(his yes, 8 November 2026): "(1) the row's own done example is the test: its real case replayed (the real row, the real text, the real
job) on a throwaway copy of the real workspace, never on made-up data and never on the real one; (2) the test looks where he looks: a
thing on the status page is read from the page as it is served, a text from the line as it lands, never from a file behind it".

This is the supported way for her test.py to do that. Her tests run through qatests.run_on, which already puts a throwaway copy of the
real workspace under HQDIR/workspace and a throwaway copy of HQ's real .status in HQ_QA_STATUS, behind the test wall. A Case is a whole
throwaway HQ made of the code under test (HQDIR) on those two copies, so anything run in it (a routine, the status server, a line's
reply) reads the real data and writes only into the copy:

    import sys; sys.path.insert(0, sys.argv[1] + "/routine"); import realcase
    case = realcase.Case(sys.argv[1])            # the code under test, on a copy of the real workspace and of HQ's real .status
    row = case.row("F197")                      # the row as it really stands
    case.py("routine/sprint.py", "go", "H299", "build", "on", "--by", "moneypenny")   # a real command, in the copy
    case.py("routine/line.py", "tick")
    with case.serve() as page:                  # HQ's own status server, on the copy
        code, html = page.get("/")              # as served
        seen = page.rendered()                  # as he sees it: drawn by a headless browser, the page's text
    texts = case.thread("team")                 # the team line as the texts landed in the copy

Never on the real files: a Case refuses to start outside her test run (no wall), or when HQDIR's workspace is the live one.
"""
from __future__ import annotations

import atexit
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LEFT_OUT = {"workspace", "scratch", ".status", ".venv", "models", "HQ", ".git", "__pycache__", "node_modules"}
LINES = {"team": "HQ/team-line", "direct": "HQ/direct-line", "donna": "HQ/direct-line", "coaching": "HQ/coaching-line"}
CHROME = ("google-chrome", "chromium", "chromium-browser", "google-chrome-stable")


class Refused(RuntimeError):
    """A real-case run that would reach the live files, or can't be made."""


def live_paths() -> set[str]:
    """The live places, as the test wall knows them (its real.json): never written, never served from."""
    try:
        return {os.path.realpath(p) for p in json.load(open(os.path.join(os.environ["HQ_WALL"], "real.json"), encoding="utf8"))["paths"]}
    except (KeyError, OSError, ValueError, TypeError):
        return set()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _copy_code(src: str, dest: str) -> None:
    os.makedirs(dest)
    junk = shutil.ignore_patterns("__pycache__", "*.pyc")
    for nm in os.listdir(src):
        if nm in LEFT_OUT:
            continue
        s = os.path.join(src, nm)
        if os.path.isdir(s) and not os.path.islink(s):
            shutil.copytree(s, os.path.join(dest, nm), symlinks=True, ignore=junk, ignore_dangling_symlinks=True)
        elif os.path.isfile(s):
            shutil.copy2(s, os.path.join(dest, nm), follow_symlinks=False)


class Case:
    """A throwaway HQ: the code under test (HQDIR) on a copy of the real workspace and of HQ's real .status. Gone when the test ends."""

    def __init__(self, hqdir: str | None = None, status: bool = True):
        hqdir = os.path.realpath(hqdir or sys.argv[1])
        if not os.environ.get("HQ_WALL") or not os.environ.get("HQ_QA_TEST_RUN") or not os.environ.get("HQ_QA_BOX"):
            raise Refused("realcase runs only inside her test run (python3 routine/qatests.py), on its throwaway copy behind the wall")
        ws = os.path.realpath(os.path.join(hqdir, "workspace"))
        if not os.path.isdir(os.path.join(ws, "HQ")):
            raise Refused(f"the code at {hqdir} has no workspace copy with an HQ folder")
        box = os.path.realpath(os.environ.get("HQ_QA_BOX") or "/nonexistent")
        if ws in live_paths() or not (ws + os.sep).startswith(box + os.sep):
            raise Refused("the workspace under the code given isn't this test run's throwaway copy (it may be the live one)")
        self.code, self.workspace = hqdir, ws
        self.root = tempfile.mkdtemp(prefix="realcase-")
        atexit.register(self.close)
        self.hq = os.path.join(self.root, "hq")
        _copy_code(hqdir, self.hq)
        for nm in (".venv", "models"):
            s = os.path.join(hqdir, nm)
            if os.path.lexists(s):
                os.symlink(os.path.realpath(s), os.path.join(self.hq, nm))
        os.symlink(ws, os.path.join(self.hq, "workspace"))
        os.symlink(".", os.path.join(self.hq, "HQ"))  # the workspace's ../HQ paths, as in a test wall's copy
        os.makedirs(os.path.join(self.hq, "scratch"))
        st = os.path.join(self.hq, ".status")
        src = os.environ.get("HQ_QA_STATUS") or ""
        if status and src and os.path.isdir(src) and os.path.realpath(src) not in live_paths():
            shutil.copytree(src, st, symlinks=True, ignore=shutil.ignore_patterns("qa-sealed"), ignore_dangling_symlinks=True)
        else:
            os.makedirs(st)
        self.support = os.path.join(self.root, "support")
        os.makedirs(self.support)
        self._servers: list = []

    # ---- what's there ----

    def path(self, *parts: str) -> str:
        """A path inside the copy: case.path("workspace", "HQ", "roadmap.md")."""
        return os.path.join(self.hq, *parts)

    def roadmap(self) -> str:
        return open(self.path("workspace", "HQ", "roadmap.md"), encoding="utf8").read()

    def row(self, label: str) -> str | None:
        """The row as it really stands in the copy of the planning, or None."""
        m = re.search(rf"^\|[^|\n]*\|\s*\**{re.escape(label.strip().upper())}\b[^\n]*$", self.roadmap(), re.M)
        return m.group(0) if m else None

    def thread(self, line: str = "team") -> list[dict]:
        """The texts of a line as they landed in the copy (team, direct or donna, coaching), oldest first."""
        p = self.path("workspace", LINES.get(line, line), "thread.jsonl")
        out = []
        try:
            for ln in open(p, encoding="utf8"):
                try:
                    out.append(json.loads(ln))
                except ValueError:
                    pass
        except OSError:
            pass
        return out

    def env(self, **extra) -> dict:
        """What a command in the copy runs with: this test's own environment (the wall's hook in it), its own support folder."""
        e = {**os.environ, "HQ_SUPPORT": self.support}
        e.pop("HQ_WORKSPACE", None)
        e.pop("HQ_ROADMAP", None)
        # F17's guard keeps a test off the real planning; here the real one is the live planning (the wall knows it), so the copy's own
        # planning and sprint file can be changed by HQ's real commands, and the live one never
        live = next((p for p in sorted(live_paths()) if p.endswith(os.path.join("HQ", "roadmap.md"))), "")
        e["HQ_REAL_ROADMAP"] = live or os.path.join(self.root, "no-live-planning", "HQ", "roadmap.md")
        e.update({k: str(v) for k, v in extra.items()})
        return e

    def python(self) -> str:
        py = os.path.join(self.hq, ".venv", "bin", "python")
        return py if os.path.exists(py) else sys.executable

    def py(self, *args: str, timeout: int = 300, **env) -> subprocess.CompletedProcess:
        """A Python command of HQ's run in the copy: case.py("routine/line.py", "tick"). Output in .stdout, .stderr, .out (both)."""
        r = subprocess.run([self.python(), *args], cwd=self.hq, env=self.env(**env), text=True, capture_output=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
        r.out = (r.stdout or "") + (r.stderr or "")
        return r

    # ---- where he looks ----

    def serve(self, **env) -> "Page":
        """HQ's own status server on the copy, on a free port. Use as `with case.serve() as page:`."""
        p = Page(self, env)
        self._servers.append(p)
        return p

    def close(self) -> None:
        for p in self._servers:
            p.stop()
        self._servers = []
        shutil.rmtree(self.root, ignore_errors=True)


class Page:
    """The status page as HQ's own server serves it from the copy."""

    def __init__(self, case: Case, env: dict):
        self.case, self.port = case, _free_port()
        self.log = os.path.join(case.root, f"server-{self.port}.log")
        node = shutil.which("node") or "/usr/bin/node"
        with open(self.log, "w") as lf:
            self.proc = subprocess.Popen([node, "status/server.mjs", "--quiet"], cwd=case.hq, stdout=lf, stderr=lf,
                                         env=case.env(HQ_STATUS_PORT=self.port, **env), stdin=subprocess.DEVNULL)
        for _ in range(300):
            if self.proc.poll() is not None:
                break
            if self.get("/roadmap.md", timeout=2)[0]:
                return
            time.sleep(0.1)
        self.stop()
        raise Refused("the status server on the copy didn't start: " + open(self.log, encoding="utf8", errors="replace").read()[-400:])

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stop()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def get(self, path: str = "/", timeout: int = 20) -> tuple[int, str]:
        """(status, body) of a route as served; 0 and the reason when it didn't answer."""
        try:
            with urllib.request.urlopen(self.url + path, timeout=timeout) as r:
                return r.status, r.read().decode("utf8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf8", "replace")
        except Exception as e:  # noqa: BLE001
            return 0, str(e)

    def json(self, path: str):
        code, body = self.get(path)
        return json.loads(body) if code == 200 else None

    def text(self, path: str = "/") -> str:
        """A served route's words: tags, scripts and styles out, spaces folded. What the HTML says before any script draws."""
        return words(self.get(path)[1])

    def rendered(self, path: str = "/", wait_ms: int = 15000, width: int = 1280) -> str:
        """The page as he sees it: opened in a headless browser, its scripts run (wait_ms of page time), then its text. Raises Refused
        without a browser: a test that needs the drawn page doesn't pass on a stand-in."""
        chrome = next((c for c in map(shutil.which, CHROME) if c), None)
        if not chrome:
            raise Refused("no headless browser here to draw the status page with")
        prof = tempfile.mkdtemp(prefix="realcase-chrome-", dir=self.case.root)
        try:
            r = subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-first-run", "--user-data-dir=" + prof,
                                f"--window-size={width},900", f"--virtual-time-budget={wait_ms}", "--dump-dom", self.url + path],
                               capture_output=True, text=True, timeout=120 + wait_ms // 1000)
            return words(r.stdout)
        finally:
            shutil.rmtree(prof, ignore_errors=True)

    def stop(self) -> None:
        p = getattr(self, "proc", None)
        if p and p.poll() is None:
            p.terminate()
            try:
                p.wait(10)
            except subprocess.TimeoutExpired:
                p.kill()


def words(html: str) -> str:
    """An HTML page's text as read: scripts and styles out, tags out, entities for the common marks, spaces folded."""
    t = re.sub(r"(?is)<(script|style|template)\b[^>]*>.*?</\1>", " ", html or "")
    t = re.sub(r"<[^>]+>", " ", t)
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " "), ("&#x27;", "'")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip()


# ---------- for the review of her tests (qatests.py): a test that reads behind where he looks ----------

PAGE_WORDS = re.compile(r"\bstatus page\b|\bnight'?s road\b", re.I)
SERVED = re.compile(r"realcase|\.serve\(|urlopen|127\.0\.0\.1|localhost:|server\.mjs|--dump-dom|requests\.get|http\.client", re.I)
BEHIND = re.compile(r"\.status[/\\'\"]|line\.json|HQ_LINE_STATE|usage\.json|routines\.json|night-road/[^'\"]*\.json|\bnight[\w-]*\.json", re.I)


def stand_in_holes(ask: str, test_py: str) -> list[str]:
    """The hole a program can see without a model: the row is about what the status page shows, and the test reads a file behind the
    page (a state file in .status, the night's kept file) and never serves the page. F197's test of 7 November did exactly that: it read
    .status/line.json, passed, and the page never showed the hold. Anything subtler is the reviewer's real-case probe."""
    t = test_py or ""
    behind = sorted({m.group(0).strip("'\" /\\") for m in BEHIND.finditer(t)})
    if PAGE_WORDS.search(ask or "") and behind and not SERVED.search(t):
        return ["the row is about what the status page shows, and her test reads a file behind the page ("
                + ", ".join(behind)[:160] + ") and never the page as it is served (HQ's own status server on a real-data copy: "
                "realcase.Case(sys.argv[1]).serve(), then page.rendered() or page.get(...)); a stand-in passes while the page is wrong"]
    return []
