"""The privacy check (M5, 10 October 2026): nothing of the user's own may end up in HQ itself.

HQ is public; the user's own things live in workspace, which the repo ignores. This looks through
HQ's files (and, with --history, every version in its git history) for:

- the user's private words: the name and "Private words" from workspace/me.md (case ignored);
- things that are personal for anyone: a home folder path (/Users/<someone>, except the
  placeholder /Users/you), a Tailscale machine name (<mac>.tail<id>.ts.net), a Tailscale address
  (100.64.x.x to 100.127.x.x), a mail address (except example and noreply ones), and keys or
  tokens (Anthropic, GitHub, Slack, AWS, private key blocks).

    python3 app/privacy.py            HQ's files as they are now (tracked, and new ones not ignored)
    python3 app/privacy.py --history  also every version in git's history

Prints each hit and exits 1 when there is one; the hit's word is shown, never more of the line
than needed to find it.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BINARY = re.compile(r"\.(png|jpe?g|gif|ico|m4a|wav|mp3|onnx|bin|npz|zip|gz)$", re.I)

GENERIC = [
    r"/Users/(?!you/|you\b|<)[A-Za-z0-9._-]+",
    r"\b[A-Za-z0-9-]+\.tail[0-9a-f]{4,}\.ts\.net\b",
    r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b(?!/)",
    r"\b[A-Za-z0-9._%+-]+@(?!example\.|users\.noreply\.github\.com|anthropic\.com)[A-Za-z0-9-]+\.[A-Za-z.]{2,}\b",
    r"sk-ant-[A-Za-z0-9_-]{10,}",
    r"\bgh[pousr]_[A-Za-z0-9]{20,}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"\bxox[abpr]-[A-Za-z0-9-]{10,}",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
]


def words(folder: Path | None = None) -> list[str]:
    """The user's private words, from me.md in their workspace."""
    sys.path.insert(0, str(ROOT / "app"))
    import me  # noqa: E402
    if folder is None:
        folder = Path(os.path.realpath(os.environ.get("HQ_WORKSPACE") or ROOT / "workspace"))
    m = me.load(folder)
    return [w for w in [m["name"], *m["private"]] if w]


def pattern(private: list[str]) -> re.Pattern:
    parts = list(GENERIC)
    for w in private:
        e = re.escape(w)
        parts.append((r"\b" if w[:1].isalnum() else "") + e + (r"\b" if w[-1:].isalnum() else ""))
    return re.compile("|".join(f"(?:{p})" for p in parts), re.I)


def scan_text(text: str, pat: re.Pattern) -> list[str]:
    return [m.group(0) for m in pat.finditer(text)]


def files(root: Path = ROOT) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                         capture_output=True, text=True).stdout
    return [f for f in out.split("\0") if f and (root / f).is_file()]


def scan_tree(pat: re.Pattern, root: Path = ROOT) -> list[str]:
    hits = []
    for f in files(root):
        for w in scan_text(f, pat):
            hits.append(f"{f} (its name): {w}")
        if BINARY.search(f):
            continue
        for i, line in enumerate((root / f).read_text(encoding="utf8", errors="replace").splitlines(), 1):
            for w in scan_text(line, pat):
                hits.append(f"{f}:{i}: {w}")
    return hits


def scan_history(pat: re.Pattern, root: Path = ROOT) -> list[str]:
    """Every commit's message, author, and every version of every file in git's history."""
    hits = []
    log = subprocess.run(["git", "-C", str(root), "log", "--all", "--format=%H%x00%an%x00%ae%x00%cn%x00%ce%x00%B%x01"],
                         capture_output=True, text=True).stdout
    for entry in filter(str.strip, log.split("\x01")):
        sha, *rest = entry.strip().split("\x00")
        for w in scan_text("\n".join(rest), pat):
            hits.append(f"commit {sha[:8]} (author, committer or message): {w}")
    blobs = subprocess.run(["git", "-C", str(root), "rev-list", "--all", "--objects"],
                           capture_output=True, text=True).stdout.splitlines()
    seen = set()
    for line in blobs:
        sha, _, path = line.partition(" ")
        if not path or sha in seen:
            continue
        seen.add(sha)
        for w in scan_text(path, pat):
            hits.append(f"history {path} (its name): {w}")
        if BINARY.search(path):
            continue
        kind = subprocess.run(["git", "-C", str(root), "cat-file", "-t", sha], capture_output=True, text=True).stdout.strip()
        if kind != "blob":
            continue
        body = subprocess.run(["git", "-C", str(root), "cat-file", "-p", sha], capture_output=True).stdout
        for w in scan_text(body.decode("utf8", "replace"), pat):
            hits.append(f"history {path} ({sha[:8]}): {w}")
    return hits


def main() -> int:
    private = words()
    if not private:
        print("No private words in workspace/me.md (Name, Private words): only the general checks run.")
    pat = pattern(private)
    hits = scan_tree(pat)
    if "--history" in sys.argv:
        hits += scan_history(pat)
    for h in hits:
        print(h)
    print(f"{len(hits)} hit(s)" if hits else "Nothing personal found.")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
