"""H42: when a routine run fails, why, in plain words, and how many times in a row.

10 October 2026 (call at 17:27), typed: "Why is the email routine down?" and "i also want to
know why the watchdog didnt fix it". The 17:00 mail check had failed with only "Failed (exit 1)" on the
page, while its own output said why (no internet: the API server couldn't be reached).

- reason(lines, code): the plain reason from a run's own output, plus its last lines as they were.
- record(key, ok, …): the failures in a row per routine, kept outside the Documents folder
  (~/Library/Application Support/JarvisVA/failures.json), so the watchdog (H20) can read them without
  any macOS permission and notice a routine that keeps failing, not only one that's missed or stopped.
- retry_asked(key): the watchdog asked for one more try (the helper had given up, the internet is back).
"""
import json, os, re, tempfile, time

SUPPORT = os.path.expanduser("~/Library/Application Support/JarvisVA")
FILE = os.path.join(SUPPORT, "failures.json")

# Known reasons, first match wins: (pattern in the output, plain words).
KNOWN = [
    (r"ENOTFOUND|EAI_AGAIN|ECONNREFUSED|ECONNRESET|ETIMEDOUT|ENETUNREACH|Can't reach the API|Unable to connect|fetch failed|network error",
     "No internet: Claude's server couldn't be reached"),
    (r"usage limit|rate.?limit|limit reached|\b429\b|hit your limit", "The usage limit was reached"),
    (r"overloaded|\b529\b|\b50[0234]\b|Internal server error", "Claude's server was busy or had an error"),
    (r"/login|not logged in|Invalid API key|authentication|OAuth|\b401\b|\b403\b", "Claude wasn't logged in"),
    (r"error_max_turns|max turns", "It ran out of turns before it finished"),
    (r"command not found|No such file", "A program or file it needs wasn't found"),
]
SIGNALS = {"130": "It was stopped (interrupted)", "137": "It was stopped (killed)", "143": "It was stopped (ended)"}


def reason(lines, code=None):
    """(plain reason, last lines): from a run's own output (the lines before its exit line) and its exit code."""
    said = [l.rstrip() for l in lines if l.strip()]
    text = "\n".join(said)
    plain = next((words for pat, words in KNOWN if re.search(pat, text, re.I)), None)
    if not plain and code in SIGNALS:
        plain = SIGNALS[code]
    if not plain:
        last = next((l.strip() for l in reversed(said) if not l.startswith("(")), "")
        plain = f"It said: {last[:140]}" if last else f"It ended with exit {code} and said nothing"
    return plain, [l[:200] for l in said[-6:]]


def read():
    try:
        return json.load(open(FILE))
    except (OSError, ValueError):
        return {}


def _write(data):
    os.makedirs(SUPPORT, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=SUPPORT, prefix=".failures")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, FILE)


def record(key, ok, why="", detail=None, gave_up=False, at=None):
    """One run of a routine ended. A failure adds to its streak; a good run ends it. Never raises."""
    try:
        data = read()
        e = dict(data.get(key) or {})
        now = at or time.time()
        if ok:
            if e.get("n"):
                e["ended"] = now
            e.update({"n": 0, "ok": now, "gave_up": False})
        else:
            if not e.get("n"):
                e["first"] = now
                e.pop("ended", None)
            e.update({"n": e.get("n", 0) + 1, "last": now, "why": why, "detail": detail or [], "gave_up": gave_up})
        data[key] = e
        _write(data)
        return e
    except Exception:
        return None


def retry_asked(key):
    """True once when the watchdog asked for another try of this routine (and clears the ask)."""
    path = os.path.join(SUPPORT, f"retry-{key}")
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
        return True
    return False
