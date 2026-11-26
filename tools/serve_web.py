#!/usr/bin/env python3
"""Serve HQ2/web for building and testing, with the backend behind the same origin.

    python3 tools/serve_web.py [port]      (default 7871, on 127.0.0.1 only)

Standard library only.
- A file under web/ is served from there, never cached (Cache-Control: no-store), so a
  changed template, stylesheet or module is what the next reload gets.
- Any other GET (or HEAD) is passed through to a backend, so the page has one origin:
  HQ_DEV_BACKENDS, a comma list of http://host:port, default
  http://127.0.0.1:7870,http://127.0.0.1:7860,http://127.0.0.1:4748; on a refused connection
  or a 404 the next one is tried.
- Any other method (POST, PUT, PATCH, DELETE) goes only to HQ_DEV_WRITE_BACKENDS (same form,
  default empty). Empty: the answer is 403, writes are off, so nothing changes live data
  by accident.
- WebSocket and WebRTC signalling can't pass through this server; the call is tried on the
  real HQ2 server. Streaming answers are passed on only once they end.
"""
import functools
import http.client
import http.server
import os
import sys
import urllib.parse

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
DEFAULT_BACKENDS = "http://127.0.0.1:7870,http://127.0.0.1:7860,http://127.0.0.1:4748"
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
       "transfer-encoding", "upgrade", "host", "content-length", "accept-encoding"}


def backends(var, default):
    return [b.strip().rstrip("/") for b in os.environ.get(var, default).split(",") if b.strip()]


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass

    def is_file(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return os.path.isfile(os.path.join(path, "index.html"))
        return os.path.isfile(path)

    def do_GET(self):
        if self.is_file():
            return super().do_GET()
        self.pass_on(backends("HQ_DEV_BACKENDS", DEFAULT_BACKENDS), try_next_on_404=True)

    def do_HEAD(self):
        if self.is_file():
            return super().do_HEAD()
        self.pass_on(backends("HQ_DEV_BACKENDS", DEFAULT_BACKENDS), try_next_on_404=True)

    def write(self):
        targets = backends("HQ_DEV_WRITE_BACKENDS", "")
        if not targets:
            self.send_plain(403, "Writes are off on this dev server (set HQ_DEV_WRITE_BACKENDS to allow them).\n")
            return
        self.pass_on(targets, try_next_on_404=False)

    do_POST = do_PUT = do_PATCH = do_DELETE = write

    def send_plain(self, code, text):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def pass_on(self, targets, try_next_on_404):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        last = None
        for i, base in enumerate(targets):
            u = urllib.parse.urlsplit(base)
            conn = http.client.HTTPConnection(u.hostname, u.port or 80, timeout=30)
            try:
                conn.request(self.command, self.path, body=body, headers=dict(headers, Host=u.netloc))
                r = conn.getresponse()
                data = r.read()
            except OSError as err:  # refused, reset, timed out: try the next one
                last = "%s: %s" % (base, err)
                conn.close()
                continue
            if r.status == 404 and try_next_on_404 and i < len(targets) - 1:
                last = "%s: 404" % base
                conn.close()
                continue
            self.send_response(r.status, r.reason)
            for k, v in r.getheaders():
                if k.lower() not in HOP and k.lower() != "cache-control":
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
            conn.close()
            return
        self.send_plain(502, "No backend answered (%s).\n" % (last or "none set"))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7871
    handler = functools.partial(Handler, directory=WEB)
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print("Serving %s on http://127.0.0.1:%d/ ; GET to %s ; writes to %s" % (
            WEB, port, ",".join(backends("HQ_DEV_BACKENDS", DEFAULT_BACKENDS)),
            ",".join(backends("HQ_DEV_WRITE_BACKENDS", "")) or "nobody (off)"), flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
