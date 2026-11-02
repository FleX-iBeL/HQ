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
    if not _quiet("remote").stdout.strip():  # a workspace with no GitHub: nothing to push to, nothing wrong
        return 0
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
    if m.returncode and not main_wins(branch):
        _quiet("merge", "--abort")
        _tell(True, f"GitHub has work that doesn't merge with this: {(m.stdout + m.stderr).strip()[:200]}")
        return m.returncode
    r = _quiet("push", "-q")
    if r.returncode:
        _tell(True, f"GitHub refused the workspace's push again: {(r.stderr or r.stdout).strip()[:200]}")
        return r.returncode
    _tell(False)
    return 0


def main_wins(branch):
    """F115: a repo conflict settles itself, main wins with the other side kept. Only the main commits, so this
    computer's side of each clashing file stays; GitHub's own lines of it go into the list he sees (settle.py), and the
    merge is finished and pushed. A file one side removed keeps the side that has it. False (nothing changed) when it
    can't: then the merge is taken back and the incident says so, as before."""
    try:
        import settle
    except ImportError:
        return False
    names = [n for n in _quiet("diff", "--name-only", "--diff-filter=U").stdout.splitlines() if n]
    if not names:
        return False
    kept = []
    for rel in names:
        ours = subprocess.run(["git", "show", f":2:{rel}"], cwd=FOLDER, capture_output=True)
        theirs = subprocess.run(["git", "show", f":3:{rel}"], cwd=FOLDER, capture_output=True)
        if ours.returncode and theirs.returncode:
            return False
        if ours.returncode:  # removed here, changed there: the one that has it stays
            open(os.path.join(FOLDER, rel), "wb").write(theirs.stdout)
        else:
            open(os.path.join(FOLDER, rel), "wb").write(ours.stdout)
            if theirs.returncode == 0:
                try:
                    a, b = ours.stdout.decode("utf8"), theirs.stdout.decode("utf8")
                except UnicodeDecodeError:
                    a = b = None
                if a is not None:
                    new, extra, _ = settle.decide(rel, a, b)
                    if new is not None and rel.endswith(".jsonl"):
                        open(os.path.join(FOLDER, rel), "w", encoding="utf8").write(new)  # a log of lines: every line of both
                    elif extra:
                        settle.keep(rel, extra, "GitHub", "A repo conflict: both sides changed this file. This computer's "
                                    "version stayed (main wins); these lines were only on GitHub's side.", folder=FOLDER)
                        kept.append(rel)
                else:
                    stem, ext = os.path.splitext(rel)
                    side = f"{stem} (from GitHub){ext}"
                    open(os.path.join(FOLDER, side), "wb").write(theirs.stdout)
                    _quiet("add", "--", side)
                    settle.keep(rel, [], "GitHub", f"A repo conflict on a file that isn't text: this computer's stayed, "
                                f"GitHub's is next to it as {os.path.basename(side)}.", folder=FOLDER)
                    kept.append(rel)
        if _quiet("add", "--", rel).returncode:
            return False
    if kept:
        _quiet("add", "--", settle.KEPT)
    c = _quiet("commit", "-q", "--no-edit", "-m", f"Merge GitHub: main wins on {', '.join(names)[:200]}", "-m",
               "The other side's own lines are kept in " + settle.KEPT + " (F115).", "-m", COAUTHOR)
    if c.returncode:
        return False
    print(f"gitlock: a repo conflict in {', '.join(names)[:200]} settled itself: this computer's version stayed"
          + (f", GitHub's own lines kept for him to look at" if kept else ""), file=sys.stderr)
    return True


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


def hand_over(files, role):
    """F115: a chat's commit on the backup with one-way sync: the files don't go over with the sync, so each goes to
    the main through the door (settle.py), which writes and commits it. Says plainly what happened."""
    import base64, hashlib, json
    if not files:
        sys.exit("gitlock: name the files to commit")
    me, sent, waiting, refused = role.my_name(), [], [], []
    for rel in files:
        p = os.path.join(FOLDER, rel)
        payload = {"from": me}
        if not os.path.exists(p):
            payload["deleted"] = True
            key = "deleted"
        else:
            raw = open(p, "rb").read()
            try:
                payload["text"] = raw.decode("utf8")
            except UnicodeDecodeError:
                payload["b64"] = base64.b64encode(raw).decode()
            key = hashlib.sha1(raw).hexdigest()
        hid = "settle-" + hashlib.sha1(f"workspace|{rel}|{key}".encode()).hexdigest()[:24]
        import settle
        code, out, err, how = settle.send(role, ["file", "workspace", rel], payload, hid)
        (sent if how == "main" and not code else waiting if how != "main" else refused).append(rel)
    if sent:
        print(f"This HQ is the backup: handed {len(sent)} file{'s' * (len(sent) != 1)} to the main one, which writes and "
              "commits {}.".format("it" if len(sent) == 1 else "them"))
    if waiting:
        print(f"The main one can't be reached right now: {', '.join(waiting)[:200]} stay{'s' * (len(waiting) == 1)} on "
              "this computer and go to the main by themselves at the next look once it answers.")
    if refused:
        print(f"The main one didn't take {', '.join(refused)[:200]}; they stay on this computer.", file=sys.stderr)
        return 1
    return 0


def main(argv):
    if not argv or argv[0] not in ("commit", "run", "push"):
        sys.exit(__doc__)
    if argv[0] == "commit" and not os.environ.get("HQ_ROLE_HERE"):
        try:
            import role  # H56.3: only the main one commits; on the backup the files go over with the sync
        except ImportError:
            role = None
        if role and role.is_backup():
            if role.one_way():
                return hand_over(argv[2:], role)
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
