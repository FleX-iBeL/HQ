"""On the backup a write goes to the main as the same command: a to-do item and a bucketlist item from this HQ are handed
over to a stand-in main (a small server on this computer) as {script, args}, the shape the main's /api/forward takes."""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from _kit import APP, HQ, done, need, workspace

tmp = workspace("role")
os.environ.pop("HQ_ROLE_HERE", None)
os.environ.pop("HQ_UNDER_TEST", None)  # a stand-in pairing in its own HQ memory, never the real one
got = []


class Main(BaseHTTPRequestHandler):
    def do_POST(self):
        got.append((self.path, self.headers.get("x-hq"), json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
        body = json.dumps({"code": 0, "out": "Done on the main.", "err": ""}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), Main)
threading.Thread(target=srv.serve_forever, daemon=True).start()
sup = tmp / "support"
sup.mkdir()
(sup / "role.json").write_text(json.dumps({"peer": f"http://127.0.0.1:{srv.server_port}", "name": "laptop", "main": "server",
                                           "peer_name": "server"}))
(sup / "role-state.json").write_text(json.dumps({"acting": "backup"}))
env = {**os.environ, "HQ_SUPPORT": str(sup)}
before = (tmp / "challenges.md").read_text()
r1 = subprocess.run([sys.executable, str(APP / "todo.py"), "add", "2", "Buy milk", "--by", "in the app"], env=env,
                    capture_output=True, text=True, timeout=60)
r2 = subprocess.run([sys.executable, str(APP / "lists.py"), "add", "A trip", "--list", "bucket", "--by", "in the app"], env=env,
                    capture_output=True, text=True, timeout=60)
srv.shutdown()
need(len(got) == 2, f"two hand-overs reached the main: {len(got)} ({r1.stdout.strip()[:80]} {r1.stderr.strip()[:80]} {r2.stderr.strip()[:80]})")
if len(got) == 2:
    (p1, h1, b1), (p2, h2, b2) = got
    need(p1 == "/api/forward" and h1 == "forward", "to the main's /api/forward, with its header")
    need(b1["script"] == "todo" and b1["args"] == ["add", "2", "Buy milk", "--by", "in the app"], f"the to-do command as it was given: {b1['args']}")
    need(b2["script"] == "lists" and b2["args"] == ["add", "A trip", "--list", "bucket", "--by", "in the app"], f"the lists command: {b2['args']}")
    need(all(isinstance(b.get("id"), str) and b["id"] for b in (b1, b2)), "each with an id, so the main runs it once")
need((tmp / "challenges.md").read_text() == before and not (tmp / "HQ" / "lists.json").exists(), "nothing was written here")
done()
