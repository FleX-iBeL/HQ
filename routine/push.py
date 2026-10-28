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
                                       (F67: a computer still on the 8 old commits is moved onto the rewritten ones, every ref)
    F67: on a computer with HQ's key, every pull and push first sets HQ's repo to commit as the public identity (own_identity).
    Every push (and release.py) waits while the running job has a note it hasn't read (H283, jobs.py notes N).

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
# F67 (28 October 2026): the public identity HQ's own commits carry. A computer with HQ's key (the remote is the
# SSH alias below) commits as this in HQ's repo, never as the global git identity (the laptop's real name went up).
KEY_HOST = "github.com-hq"
PUBLIC_NAME = "FleX-iBeL"
PUBLIC_EMAIL = "5278158+FleX-iBeL@users.noreply.github.com"
# F67: the 8 commits of 27 October rewritten to the public identity on 28 October (old: new, same tree each). A
# computer still holding the old ones (the laptop) can't fast-forward; pull() moves what it has onto the new ones.
REWRITTEN = {
    "db56d12490dded11f8fc074a0378a66e20fa0dc3": "365d76bd61cf12a2514fe12eb6e7538ec3326014",
    "1c082c5b0a2aeceacfd86ea1da83c494a4e58310": "053cd302af62fa6fa6bd92e4f20ad61c9d3ee586",
    "2856f05d39ec0349f815d64dfc58a6ddcbbb1a68": "6a1b5615bc00c00eb877cebd25cd20a5b77c7907",
    "66821c5e11a4f198c7357b6be63001fcc1d72cbd": "55f6e750df50d36efc5edc0fa2744b7ce26d518c",
    "c9d480fc105051adf190c9705895a0fbdf42f84a": "db7b603f8d58a821702536bce118c2d084eab87f",
    "53306bf9bb6d43494acca30e63041b3088a8aa23": "1c510a9cfdd63cb37a51ed8e96e584f9de763916",
    "177f6420381cb773252c5818ecd52c3f00369f49": "e9dee995e82ce60b17d9c15c619c5e93a8466cf1",
    "45c9ccafa7dd0ad555e869380e5f816e1563757a": "9bdbf133a16c3b5101133c7d4c11952f29280f17",
}
# F67 (job 435): the laptop's one-time start, from the workspace folder next to HQ. Its own push.py is the
# one from before, which only fast-forwards, so its pull is refused and the new one never arrives that way; this takes
# the new push.py from GitHub's dev next to the old one and runs its pull. Written the same in the build notes ("The
# laptop's one-time start after the rewrite (F67)"); happy flow 183 runs it on a stand-in that starts from the old one.
BOOTSTRAP = ("git -C ../HQ checkout dev && git -C ../HQ fetch origin dev && "
             "git -C ../HQ show origin/dev:routine/push.py > ../HQ/routine/push_f67.py && "
             "python3 ../HQ/routine/push_f67.py --pull; rm -f ../HQ/routine/push_f67.py")


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


def own_identity() -> str:
    """F67: on a computer that pushes with HQ's key, HQ's repo commits as the public identity; set it in the repo's own
    config when it's missing or different (a missing one falls back to the global name and mail). Says what it did, or ""."""
    if ssh_host() != KEY_HOST:
        return ""
    name = git("config", "--local", "user.name").stdout.strip()
    mail = git("config", "--local", "user.email").stdout.strip()
    if (name, mail) == (PUBLIC_NAME, PUBLIC_EMAIL):
        return ""
    git("config", "--local", "user.name", PUBLIC_NAME)
    git("config", "--local", "user.email", PUBLIC_EMAIL)
    msg = f"HQ's repo now commits as {PUBLIC_NAME} with the GitHub noreply address (F67; it was {name or 'unset'})."
    print(msg)
    return msg


def across_rewrite() -> str:
    """F67: when HQ still holds rewritten commits, its own commits after the newest of them are moved onto that one's
    new version (the trees are the same), with the public identity; uncommitted changes are kept (autostash). Says
    what it did, or "" when there was nothing to do or it couldn't (then nothing is changed)."""
    old = next((o for o in reversed(list(REWRITTEN)) if git("merge-base", "--is-ancestor", o, "HEAD").returncode == 0), "")
    new = REWRITTEN.get(old, "")
    if not old or git("cat-file", "-e", f"{new}^{{commit}}").returncode != 0:
        return ""
    own = int(git("rev-list", "--count", f"{old}..HEAD").stdout.strip() or 0)
    fix = (f'test "$(git log -1 --format=%an%ae)" = "{PUBLIC_NAME}{PUBLIC_EMAIL}" || '
           f'git -c user.name={PUBLIC_NAME} -c user.email={PUBLIC_EMAIL} commit -q --amend --no-edit --reset-author')
    r = git("-c", f"user.name={PUBLIC_NAME}", "-c", f"user.email={PUBLIC_EMAIL}", "rebase", "-q", "--autostash",
            "--exec", fix, "--onto", new, old)
    if r.returncode != 0:
        git("rebase", "--abort")
        print(f"Couldn't move HQ's own commits across the F67 rewrite:\n{(r.stdout + r.stderr).strip()}")
        return ""
    msg = f"Moved HQ onto the rewritten history (F67): {own} commit(s) of its own carried over."
    print(msg)
    return msg


def _carry(old: str, new: str, ref: str) -> str:
    """F67: ref's own commits after old, re-made on new with the public identity, in a worktree of its own (the
    working tree is never touched). Gives the new tip, or "" when it couldn't (then nothing is changed)."""
    import tempfile
    tmp = tempfile.mkdtemp(prefix="hq-f67-")
    try:
        if git("worktree", "add", "-q", "--detach", tmp, ref).returncode != 0:
            return ""
        fix = (f'test "$(git log -1 --format=%an%ae)" = "{PUBLIC_NAME}{PUBLIC_EMAIL}" || '
               f'git -c user.name={PUBLIC_NAME} -c user.email={PUBLIC_EMAIL} commit -q --amend --no-edit --reset-author')
        r = subprocess.run(["git", "-C", tmp, "-c", f"user.name={PUBLIC_NAME}", "-c", f"user.email={PUBLIC_EMAIL}",
                            "rebase", "-q", "--exec", fix, "--onto", new, old], text=True, capture_output=True)
        if r.returncode != 0:
            subprocess.run(["git", "-C", tmp, "rebase", "--abort"], capture_output=True)
            return ""
        return subprocess.run(["git", "-C", tmp, "rev-parse", "HEAD"], text=True, capture_output=True).stdout.strip()
    finally:
        git("worktree", "remove", "--force", tmp)
        git("worktree", "prune")


def clear_old() -> list[str]:
    """F67 (job 435): after the move, no other ref here may still hold the old 8 commits, or this computer's own
    privacy check (it reads every ref) refuses every push. Remote-tracking branches and tags come fresh from GitHub
    (forced, pruned: the re-made v0.4.18 too); another local branch is moved onto the rewritten commits, its own
    commits after them carried over with the public identity. Only on a computer with HQ's key: a friend's backup
    branches stay hers. What it did, line by line."""
    if ssh_host() != KEY_HOST:
        return []
    have = [o for o in REWRITTEN if git("cat-file", "-e", f"{o}^{{commit}}").returncode == 0]
    if not have or not any(git("for-each-ref", "--contains", o).stdout.strip() for o in have):
        return []
    said = []
    if git("fetch", "-q", "--prune", "--force", "--tags", REMOTE,
           f"+refs/heads/*:refs/remotes/{REMOTE}/*").returncode == 0:
        said.append("GitHub's branches and tags fetched fresh (the old ones replaced).")
    current = git("branch", "--show-current").stdout.strip()
    for ref in git("for-each-ref", "--format=%(refname)", "refs/heads", "refs/tags").stdout.split():
        old = next((o for o in reversed(have) if git("merge-base", "--is-ancestor", o, ref).returncode == 0), "")
        if not old:
            continue
        short, new = ref.split("/", 2)[-1], REWRITTEN[old]
        if ref == f"refs/heads/{current}" or ref.startswith("refs/tags/") \
                or git("cat-file", "-e", f"{new}^{{commit}}").returncode != 0:
            said.append(f"Still on the old commits, left as it is: {short}.")
            continue
        own = int(git("rev-list", "--count", f"{old}..{ref}").stdout.strip() or 0)
        tip = new if own == 0 else _carry(old, new, ref)
        if not tip:
            said.append(f"Couldn't move {short} onto the rewritten commits; left as it is.")
            continue
        git("update-ref", ref, tip)
        said.append(f"Moved {short} onto the rewritten commits" + (f", {own} commit(s) of its own carried over." if own else "."))
    for s in said:
        print(s)
    return said


def pull() -> int:
    """F31: a job's start: dev from GitHub, fast-forward only. Uncommitted changes are left alone (git refuses
    only when they'd be overwritten, and then says which)."""
    branch = git("branch", "--show-current").stdout.strip()
    if branch != WORK_BRANCH:
        print(f"Not pulled: HQ is on {branch or 'no branch'}, not {WORK_BRANCH}. Switch first: git -C <HQ> checkout {WORK_BRANCH}")
        return 2
    own_identity()
    r = git("pull", "--ff-only", REMOTE, WORK_BRANCH)
    if r.returncode != 0 and across_rewrite():  # F67: the laptop still on the old 8 commits
        r = git("pull", "--ff-only", REMOTE, WORK_BRANCH)
    out = (r.stdout + r.stderr).strip()
    if r.returncode != 0:
        print(f"Pulling {WORK_BRANCH} failed:\n{out}")
        refused(f"pulling {WORK_BRANCH}", out)
        return 2
    clear_old()  # F67 (job 435): the other branches and tags too, so its own privacy check passes
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


def notes_waiting() -> bool:
    """H283: True (and says so) while the running job has a note it hasn't read: a push or release waits until the
    job has read its notes with jobs.py notes N, so a "don't release, QA first" is never passed by."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import jobs
        hit = jobs.unread_running()
    except Exception:
        return False
    if not hit:
        return False
    n, new = hit
    print(f"Not pushed: job {n} has {len(new)} note(s) it hasn't read (H283). Read them first with "
          f"python3 routine/jobs.py notes {n}, follow them, then push again:")
    for x in new:
        print(f"- {x['at']}: {x['text']}")
    return True


def main() -> int:
    if "--check" in sys.argv:
        return check_key()
    if "--pull" in sys.argv:
        return pull()
    if notes_waiting():
        return 3
    own_identity()
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
    if release and not dry:
        about_after_release()
    return 0


def about_after_release() -> None:
    """H197: a release also sets GitHub's About to the new version. A refusal doesn't undo the release; about.py
    opens its own incident, so it's seen."""
    try:
        import about
        print(about.set_about(root=ROOT)[1])
    except Exception as e:
        print(f"GitHub's About not set: {e}")

if __name__ == "__main__":
    sys.exit(main())
