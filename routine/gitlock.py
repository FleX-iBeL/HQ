#!/usr/bin/env python3
"""H30: one commit and push at a time. The hourly mail check may now run while a job runs (10
October 2026: "Yeah, exactly. Because I just want to have those run. I think it's important."), so their
commits and pushes take turns through this lock.

    python3 "routine/gitlock.py" commit "message" file1 file2 ...
        adds the named files, commits only those (other staged files are left alone), and pushes.
    python3 "routine/gitlock.py" run CMD ...
        runs any command while holding the lock.

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


def main(argv):
    if not argv or argv[0] not in ("commit", "run"):
        sys.exit(__doc__)
    lock = hold()
    try:
        if argv[0] == "run":
            return subprocess.run(argv[1:]).returncode
        msg, files = argv[1], argv[2:]
        if not files:
            sys.exit("gitlock: name the files to commit")
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
        return git("push", "-q")
    finally:
        lock.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
