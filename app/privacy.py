"""The privacy check (M5, 10 October 2026): nothing of the user's own may end up in HQ itself.

HQ is public; the user's own things live in workspace, which the repo ignores. This looks through
HQ's files (and, with --history, every version in its git history) for:

- the user's private words: the name and "Private words" from workspace/me.md (case ignored);
- things that are personal for anyone: a home folder path (/Users/<someone>, except the
  placeholder /Users/you), a Tailscale machine name (<mac>.tail<id>.ts.net), a Tailscale address
  (100.64.x.x to 100.127.x.x), a mail address (except example and noreply ones), and keys or
  tokens (Anthropic, GitHub, Slack, AWS, private key blocks);
- F104: a computer named after someone (<name>s-MacBook-Air) and HQ's old project name, in the files as they are now. Old commits
  still hold them: taking them out of the history means rewriting the public repo, so `--history` doesn't count those two.

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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "routine"))
import hqpaths  # noqa: E402  F102: what a key looks like, one list

ROOT = Path(__file__).resolve().parent.parent
BINARY = re.compile(r"\.(png|jpe?g|gif|ico|m4a|wav|mp3|onnx|bin|npz|zip|gz)$", re.I)

GENERIC = [
    r"/Users/(?!you/|you\b|<)[A-Za-z0-9._-]+",
    r"\b[A-Za-z0-9-]+\.tail[0-9a-f]{4,}\.ts\.net\b",
    r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b(?!/)",
    r"\b[A-Za-z0-9._%+-]+@(?!example\.|users\.noreply\.github\.com|anthropic\.com)[A-Za-z0-9-]+\.[A-Za-z.]{2,}\b",
    *hqpaths.KEY_PATTERNS,
]


# F104: only in the files as they are now. Old commits hold both; taking them out means rewriting the public repo.
TODAY = [hqpaths.OLD_NAME, r"\b[A-Z][a-z]+s-(?:MacBook|iMac|Mac-mini)(?:-[A-Za-z0-9]+)*\b"]


def words(folder: Path | None = None) -> list[str]:
    """The user's private words, from me.md in their workspace."""
    sys.path.insert(0, str(ROOT / "app"))
    import me  # noqa: E402
    if folder is None:
        folder = Path(os.path.realpath(os.environ.get("HQ_WORKSPACE") or ROOT / "workspace"))
    m = me.load(folder)
    return [w for w in [m["name"], *m["private"]] if w]


def pattern(private: list[str], today: bool = False) -> re.Pattern:
    parts = list(GENERIC) + (TODAY if today else [])
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


HOOK = """#!/bin/sh
# HQ (F104): nothing goes up without the privacy check, whatever pushes it. push.py runs the check itself first.
[ -n "$HQ_PRIVACY_PASSED" ] && exit 0
root="$(git rev-parse --show-toplevel)"
exec python3 "$root/app/privacy.py" --history
"""


def install_hook(root: Path = ROOT) -> str:
    """The check as a pre-push hook in HQ's clone (F104), in the repository's own hooks folder, also from a worktree."""
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "--git-common-dir"], capture_output=True, text=True)
    if r.returncode:
        return "This HQ isn't a git copy: no hook."
    common = Path(r.stdout.strip())
    p = (common if common.is_absolute() else root / common) / "hooks" / "pre-push"
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists() and p.read_text() != HOOK and "HQ (F104)" not in p.read_text():
        return f"There's another pre-push hook here, left as it is: {p}"
    p.write_text(HOOK)
    p.chmod(0o755)
    return f"The privacy check runs before every push here: {p.name}."


def main() -> int:
    private = words()
    if not private:
        print("No private words in workspace/me.md (Name, Private words): only the general checks run.")
    if "--hook" in sys.argv:
        print(install_hook())
        return 0
    pat = pattern(private)
    hits = scan_tree(pattern(private, today=True))
    if "--history" in sys.argv:
        hits += scan_history(pat)
    for h in hits:
        print(h)
    print(f"{len(hits)} hit(s)" if hits else "Nothing personal found.")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
