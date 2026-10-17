#!/usr/bin/env python3
"""GitHub's About says the version that's out (H197, 17 October 2026).

The user's quick note: "If the team releases, then it needs to also update the About on github, it still says 0.3,
this is second time i caught it. Also the description can be better". So every release (release.py main, and
push.py --release by hand) sets the public repo's About to the new version, with the description below.

    python3 routine/about.py           sets the About now, to the version in VERSION
    python3 routine/about.py --show    only prints what the About would say

The deploy key that pushes HQ can't change the About; that takes a GitHub token with "Administration: read and
write" on the repo. Looked for in this order: HQ_GITHUB_TOKEN, GH_TOKEN or GITHUB_TOKEN in the environment, the file
~/.config/hq/github-token (or HQ_GITHUB_TOKEN_FILE), then `gh auth token` when the gh command is signed in.
Without one, or when GitHub says no, the release still counts (the code is out), but it opens the incident "about"
(the status page's Incidents, and Donna texts), so a stale About never goes unseen again. The next About that goes
through closes it. Exits 0 when set, 2 when not.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
API = os.environ.get("HQ_GITHUB_API", "https://api.github.com")
TOKEN_FILE = Path(os.environ.get("HQ_GITHUB_TOKEN_FILE", Path.home() / ".config" / "hq" / "github-token"))
# In everyday words, rewritten once (H197). GitHub keeps it under 350 characters. [Claude's wording.]
DESCRIPTION = ("HQ {v}: your own headquarters with Claude. Call it from your phone and just talk; it gets things done "
               "with your notes, to-do list, mail and calendar. A team keeps working while you're away, and a status "
               "page shows what's going on. Runs on your own computer. Still in development.")


def version(root: Path | None = None) -> str:
    return ((root or ROOT) / "VERSION").read_text().strip()


def text(v: str) -> str:
    return DESCRIPTION.format(v=v)


def slug(root: Path | None = None) -> str | None:
    """owner/repo from origin's address, ssh alias or https."""
    url = subprocess.run(["git", "-C", str(root or ROOT), "remote", "get-url", "origin"],
                         text=True, capture_output=True).stdout.strip()
    m = re.search(r"github\.com[^:/]*[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else None


def token() -> str | None:
    for k in ("HQ_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(k, "").strip():
            return os.environ[k].strip()
    try:
        t = TOKEN_FILE.read_text().strip()
        if t:
            return t
    except OSError:
        pass
    if shutil.which("gh"):
        r = subprocess.run(["gh", "auth", "token"], text=True, capture_output=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return None


def _incident(ok: bool, why: str) -> None:
    try:
        import incidents
        if ok:
            if incidents.is_down("about"):
                incidents.fix("about", why)
                incidents.up("about")
        else:
            incidents.down("about", why[:200])
    except Exception:
        pass


def set_about(v: str | None = None, root: Path | None = None) -> tuple[bool, str]:
    """Sets the About to the description with version v. Never raises; says what happened."""
    v = v or version(root)
    repo, tok = slug(root), token()
    if not repo:
        why = "GitHub's About not set: HQ's origin isn't a GitHub repo."
    elif not tok:
        why = (f"GitHub's About not set to {v}: no GitHub token here (one with Administration: read and write on "
               f"{repo}, in {TOKEN_FILE}).")
    else:
        req = urllib.request.Request(f"{API}/repos/{repo}", method="PATCH",
                                     data=json.dumps({"description": text(v)}).encode(),
                                     headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
                                              "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                got = json.loads(r.read() or b"{}").get("description")
            if got == text(v):
                _incident(True, f"GitHub's About set to {v}")
                return True, f"GitHub's About now says {v}."
            why = f"GitHub's About not set to {v}: GitHub answered with another description."
        except urllib.error.HTTPError as e:
            why = f"GitHub's About not set to {v}: GitHub said {e.code} {e.reason}."
        except (urllib.error.URLError, OSError, ValueError) as e:
            why = f"GitHub's About not set to {v}: {e}."
    _incident(False, why)
    return False, why


def main(argv: list[str]) -> int:
    if "--show" in argv:
        print(text(version()))
        return 0
    ok, why = set_about()
    print(why)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
