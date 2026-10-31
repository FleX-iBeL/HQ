#!/usr/bin/env python3
"""H30: one commit and push at a time. The hourly mail check may now run while a job runs (10
October 2026: "Yeah, exactly. Because I just want to have those run. I think it's important."), so their
commits and pushes take turns through this lock.

    python3 "routine/gitlock.py" commit "message" file1 file2 ...
        adds the named files, commits only those (other staged files are left alone), and pushes.
    python3 "routine/gitlock.py" run CMD ...
        runs any command while holding the lock.
    python3 "routine/gitlock.py" push
        pushes what's committed (F102: what a refused push left behind).

F102 (31 October 2026): a refused push fetches, merges and tries again, also for saves from chats outside HQ; when that doesn't
work the merge is taken back and an incident opens, closed by the next good push. A file with a key in it isn't committed: it
stays out, and an incident says which.

Waits up to five minutes for the lock. git itself also refuses two changes at once (index.lock), so a
failed step is tried again a few times. Exit code: that of the last git step.
"""
import fcntl, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
JV = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import hqpaths  # M1: git runs in the workspace (his own repo), never in HQ
FOLDER = hqpaths.FOLDER
LOCK = os.path.join(JV, "scratch", "routine", "git.lock")
WAIT = 300
PUSH_KEY = "workspace-push"
COAUTHOR = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"


def hold():
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    f = open(LOCK, "a+")
    end = time.time() + WAIT
    while True:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            f.seek(0)
            f.truncate()
            f.write(f"{os.getpid()} {time.strftime('%H:%M:%S')} {' '.join(sys.argv[1:3])}\n")
            f.flush()
            return f
        except BlockingIOError:
            if time.time() > end:
                sys.exit("gitlock: waited five minutes for another commit; gave up")
            time.sleep(0.5)


def git(*args, tries=5):
    r = None
    for i in range(tries):
        r = subprocess.run(["git", *args], cwd=FOLDER)
        if r.returncode == 0:
            return 0
        time.sleep(1 + i)
    return r.returncode


def _quiet(*args):
    return subprocess.run(["git", *args], cwd=FOLDER, capture_output=True, text=True)


def _tell(down, why=""):
    """The incident of a push that doesn't get through. A test writes it only into its own file."""
    if hqpaths.under_test() and not os.environ.get("HQ_INCIDENTS_FILE"):
        return
    import incidents
    if down:
        incidents.down(PUSH_KEY, why)
    else:
        incidents.up(PUSH_KEY)


def push():
    r = _quiet("push", "-q")
    if r.returncode == 0:
        _tell(False)
        return 0
    first = (r.stderr or r.stdout).strip()
    branch = _quiet("rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or "main"
    f = _quiet("fetch", "-q", "origin", branch)
    if f.returncode:
        _tell(True, f"The workspace can't reach GitHub: {(f.stderr or first).strip()[:200]}")
        return f.returncode
    m = _quiet("merge", "-q", "--no-edit", f"origin/{branch}")
    if m.returncode:
        _quiet("merge", "--abort")
        _tell(True, f"GitHub has work that doesn't merge with this: {(m.stdout + m.stderr).strip()[:200]}")
        return m.returncode
    r = _quiet("push", "-q")
    if r.returncode:
        _tell(True, f"GitHub refused the workspace's push again: {(r.stderr or r.stdout).strip()[:200]}")
        return r.returncode
    _tell(False)
    return 0


def _with_keys(files):
    """F102: the files with a key in them, which stay out of a commit."""
    out = {}
    for rel in files:
        p = os.path.join(FOLDER, rel)
        try:
            if os.path.isfile(p) and os.path.getsize(p) < 20_000_000:
                hit = hqpaths.key_hits(open(p, encoding="utf8", errors="ignore").read())
                if hit:
                    out[rel] = hit[0]
        except OSError:
            pass
    return out


def main(argv):
    if not argv or argv[0] not in ("commit", "run", "push"):
        sys.exit(__doc__)
    if argv[0] == "commit" and not os.environ.get("HQ_ROLE_HERE"):
        try:
            import role  # H56.3: only the main one commits; on the backup the files go over with the sync
        except ImportError:
            role = None
        if role and role.is_backup():
            print("This HQ is the backup now: only the main one commits. Nothing was committed; the files go over with the sync.")
            return 0
    lock = hold()
    try:
        if argv[0] == "run":
            return subprocess.run(argv[1:]).returncode
        if argv[0] == "push":
            return push()
        msg, files = argv[1], argv[2:]
        if not files:
            sys.exit("gitlock: name the files to commit")
        keyed = _with_keys(files)
        if keyed:
            names = ", ".join(sorted(keyed))[:200]
            print(f"gitlock: left out, a key is in it: {names}", file=sys.stderr)
            if not hqpaths.under_test() or os.environ.get("HQ_INCIDENTS_FILE"):
                import incidents
                incidents.down("secrets", f"A key is in {names}: it stays out of git until it's gone")
            files = [f for f in files if f not in keyed]
            if not files:
                return 0
        if subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *files], cwd=FOLDER).returncode == 0 and \
                not subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "--", *files], cwd=FOLDER,
                                   capture_output=True, text=True).stdout.strip():
            return 0  # nothing changed in these files
        code = git("add", "--", *files)
        if code:
            return code
        code = git("commit", "-q", "-m", msg, "-m", COAUTHOR, "--only", "--", *files)
        if code:
            return code
        return push()
    finally:
        lock.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
