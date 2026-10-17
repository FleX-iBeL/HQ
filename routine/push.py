"""Push HQ to its public repo, only after the privacy check (H58, 11 October 2026).

HQ pushes with its own key (a deploy key with write access on the public repo), through the SSH
alias github.com-hq in ~/.ssh/config, so a job can push without anyone at the Terminal. Before
anything goes up, `app/privacy.py --history` must say nothing personal; one hit and nothing is pushed.

    python3 routine/push.py            privacy check, then push the current branch (the working branch, dev)
    python3 routine/push.py --release  privacy check, then push main and the version tags (only on a release,
                                       on the user's say-so; H90)
    python3 routine/push.py --nightly  privacy check, then dev to the branch nightly (H186: the night's work, every night;
                                       no tags, so friends' update bars never see it)
    python3 routine/push.py --dry-run  the same, but git only shows what it would push
    python3 routine/push.py --check    only checks that GitHub accepts HQ's key; pushes nothing
    python3 routine/push.py --pull     brings HQ up to date with dev from GitHub (fast-forward only), at a job's start

Exits 0 when pushed (or pulled, or the check passed), 1 when the privacy check found something, 2 when git failed.

F31 (14 October 2026): a refused pull or push never passes silently. It opens the incident "github" (the status
page's Incidents, and Donna texts at once); the next pull or push that goes through closes it again.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
REMOTE = "origin"
WORK_BRANCH = "dev"      # H90: every job's commits go here
RELEASE_BRANCH = "main"  # H90: only on a release, with the version tags
NIGHTLY_BRANCH = "nightly"  # H186: the night's work, always; main only when the team is sure


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], text=True, capture_output=True)


def refused(what: str, out: str) -> None:
    """F31: a refused pull or push shows up: an incident (Donna texts about it at once), and a line saying so."""
    last = next((l for l in reversed(out.strip().splitlines()) if l.strip()), "no answer")
    try:
        import incidents
        incidents.down("github", f"{what} refused: {last[:200]}", detail=out.strip()[-1500:].splitlines())  # a list of lines, like every other incident (H42)
    except Exception:
        pass
    print("Logged as an incident (github): it shows on the status page and Donna texts about it.")


def went_through(what: str) -> None:
    """F31: a pull or push that worked closes an open github incident."""
    try:
        import incidents
        if incidents.is_down("github"):
            incidents.fix("github", f"{what} went through again")
            incidents.up("github")
    except Exception:
        pass


def pull() -> int:
    """F31: a job's start: dev from GitHub, fast-forward only. Uncommitted changes are left alone (git refuses
    only when they'd be overwritten, and then says which)."""
    branch = git("branch", "--show-current").stdout.strip()
    if branch != WORK_BRANCH:
        print(f"Not pulled: HQ is on {branch or 'no branch'}, not {WORK_BRANCH}. Switch first: git -C <HQ> checkout {WORK_BRANCH}")
        return 2
    r = git("pull", "--ff-only", REMOTE, WORK_BRANCH)
    out = (r.stdout + r.stderr).strip()
    if r.returncode != 0:
        print(f"Pulling {WORK_BRANCH} failed:\n{out}")
        refused(f"pulling {WORK_BRANCH}", out)
        return 2
    went_through(f"pulling {WORK_BRANCH}")
    print(f"Pulled {WORK_BRANCH}." + (f"\n{out}" if out else ""))
    if git("status", "--porcelain").stdout.strip():
        print("Note: HQ has changes that aren't committed:\n" + git("status", "--short").stdout.rstrip())
    return 0


def ssh_host() -> str:
    url = git("remote", "get-url", REMOTE).stdout.strip()
    # git@<host>:owner/repo.git
    return url.split("@", 1)[-1].split(":", 1)[0] if "@" in url and ":" in url else ""


def check_key() -> int:
    host = ssh_host()
    if not host:
        print(f"HQ's remote isn't an SSH address ({git('remote', 'get-url', REMOTE).stdout.strip()}).")
        return 2
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-T", host],
                       text=True, capture_output=True)
    out = (r.stdout + r.stderr).strip()
    # GitHub answers "Hi <repo>! You've successfully authenticated" (exit 1) when the key is known.
    if "successfully authenticated" in out:
        print(f"GitHub accepts HQ's key ({host}).")
        return 0
    print(f"GitHub doesn't accept HQ's key yet ({host}): {out.splitlines()[-1] if out else 'no answer'}")
    return 2


def privacy_ok(dry: bool = False) -> bool:
    """The privacy check over HQ and its whole history; a hit means nothing goes up, to any branch (H58, H186)."""
    print("Privacy check of HQ and its whole history…")
    p = subprocess.run([sys.executable, str(ROOT / "app" / "privacy.py"), "--history"],
                       text=True, capture_output=True)
    print(p.stdout.strip())
    if p.returncode != 0:
        print("Not pushed: the privacy check found something personal. Take it out first.")
        if not dry:
            refused("pushing (the privacy check found something personal)", p.stdout)
        return False
    return True


def push_nightly(branch: str, dry: list[str]) -> int:
    """H186: the working branch as it is now goes to nightly, on GitHub and here. Fast-forward only, never tags."""
    if branch != WORK_BRANCH:
        print(f"Not pushed: {NIGHTLY_BRANCH} only takes {WORK_BRANCH}, and HQ is on {branch}.")
        return 2
    r = git("push", *dry, REMOTE, f"refs/heads/{WORK_BRANCH}:refs/heads/{NIGHTLY_BRANCH}")
    out = (r.stdout + r.stderr).strip()
    if r.returncode != 0:
        print(f"Pushing {WORK_BRANCH} to {NIGHTLY_BRANCH} failed:\n{out}")
        if not dry:
            refused(f"pushing {WORK_BRANCH} to {NIGHTLY_BRANCH}", out)
        return 2
    if not dry:
        git("branch", "-f", NIGHTLY_BRANCH, WORK_BRANCH)
        went_through(f"pushing {WORK_BRANCH} to {NIGHTLY_BRANCH}")
    print(f"Pushed {WORK_BRANCH} to {NIGHTLY_BRANCH}{' (dry run)' if dry else ''}." + (f"\n{out}" if out else ""))
    return 0


def main() -> int:
    if "--check" in sys.argv:
        return check_key()
    if "--pull" in sys.argv:
        return pull()
    dry = ["--dry-run"] if "--dry-run" in sys.argv else []

    if not privacy_ok(bool(dry)):
        return 1

    branch = git("branch", "--show-current").stdout.strip()
    if not branch:
        print("Not pushed: HQ isn't on a branch.")
        return 2
    if "--nightly" in sys.argv:
        return push_nightly(branch, dry)
    # H90: day-to-day work goes to the working branch; main and the tags only move on a release.
    release = "--release" in sys.argv
    if branch == RELEASE_BRANCH and not release:
        print(f"Not pushed: {RELEASE_BRANCH} only goes up on a release (add --release, on the user's say-so). "
              f"Work goes to {WORK_BRANCH}.")
        return 2
    if git("status", "--porcelain").stdout.strip():
        print("Note: HQ has changes that aren't committed; only what's committed goes up.")
    return push_branch(branch, release, dry)


def push_branch(branch: str, release: bool = False, dry: list[str] | None = None) -> int:
    """The branch to GitHub, and on a release the version tags too. Only after privacy_ok()."""
    dry = dry or []
    steps = [(f"branch {branch}", ["push", *dry, REMOTE, branch])]
    if release:
        steps.append(("tags", ["push", *dry, REMOTE, "--tags"]))
    for what, args in steps:
        r = git(*args)
        out = (r.stdout + r.stderr).strip()
        if r.returncode != 0:
            print(f"Pushing the {what} failed:\n{out}")
            if not dry:
                refused(f"pushing the {what}", out)
            return 2
        print(f"Pushed the {what}{' (dry run)' if dry else ''}." + (f"\n{out}" if out else ""))
        if not dry:
            went_through(f"pushing the {what}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
