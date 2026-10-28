#!/usr/bin/env python3
"""H113: a job stopped by the usage line carries on where it left off (13 October 2026, call at 19:53).
His quick note: "When i job is halted bu usage line limit atatuspage, can it continue where it left off or do
we restart it each time now that this usage limiter is so dynamically moving?" On the call, in his words:
"I like that and I think we should do that".

Every job's chat gets its own id when the routine starts it (`claude --session-id`), kept here per job. When
the job's chat says `jobs.py held N` (the usage said STOP), `on_held` notes when and at about which step (the
status block's Now line while it still names the job, else the job's newest line in the status block's log).
When the routine starts that job again (`plan`):

- on the same computer, with its earlier chat still there (Claude Code's own transcript in ~/.claude/projects):
  the chat is picked up again (`claude --resume <id>`), with its memory, and told to carry on;
- when it can't (the other computer picks it up, or the old chat isn't found): a fresh chat, whose prompt
  gets a note: stopped by the usage line at about this step, first look at what the first run left, then
  carry on. On the other computer the step comes from the status block's log in the roadmap, which syncs.

The records are this computer's own (HQ's scratch/routine/carryon, never in the repo or the workspace); a
test's roadmap copy (HQ_ROADMAP) gets its own folder next to it, and HQ_CLAUDE_PROJECTS points the transcript
look-up elsewhere for a test.

F72 (28 October 2026, call at 14:20, Moneypenny): a big job is cut into steps at its start, saved (committed to
dev) after each step, and writes down which are done, so a stop or a crash picks up at the next step, not the
top. His words: "I like the idea that the saved pieces can have their own row. ... You just need to fix it."
`jobs.py steps N "A" "B" …` sets the steps (`set_steps`; done ones are kept), `jobs.py step N K` marks step K
done with HQ's commit (`step_done`; refused while HQ has uncommitted changes, as the step isn't saved yet). The
record is `job-N-steps.json` next to the carry-on record; a held job's step is its next one (`on_held`), the
resume prompt, the fresh note and a crash rerun's first prompt name the saved steps and where to carry on
(`steps_words`, `steps_note`), and a crash rerun takes its first run's steps (`copy_steps`). The commits of the
steps say "(job N, step K of M)" in their subject, so a fresh chat on the other computer finds them in git log.
"""
import glob, json, os, re, subprocess, sys, time, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
_TEST = os.environ.get("HQ_ROADMAP")
DIR = (os.environ.get("HQ_CARRYON") or (os.path.splitext(_TEST)[0] + "-carryon" if _TEST
                                         else os.path.join(ROOT, "scratch", "routine", "carryon")))


def projects():
    """Where Claude Code keeps its chats on this computer."""
    if os.environ.get("HQ_CLAUDE_PROJECTS"):
        return os.environ["HQ_CLAUDE_PROJECTS"]
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    return os.path.join(base, "projects")


def _file(n):
    return os.path.join(DIR, f"job-{int(n)}.json")


def load(n):
    try:
        return json.load(open(_file(n)))
    except (OSError, ValueError):
        return {}


def save(n, rec):
    os.makedirs(DIR, exist_ok=True)
    tmp = _file(n) + ".tmp"
    json.dump(rec, open(tmp, "w"), indent=1)
    os.replace(tmp, _file(n))


def chat_there(sid, folder=None):
    """True when Claude Code still has the chat sid on this computer (in the folder's project, when given)."""
    if not sid:
        return False
    if folder:
        slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(folder))
        if os.path.exists(os.path.join(projects(), slug, f"{sid}.jsonl")):
            return True
    return bool(glob.glob(os.path.join(projects(), "*", f"{sid}.jsonl")))


def _clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("·", "-")).strip()


def step_from_roadmap(n, text):
    """At about which step job n is, from the roadmap's status block: its Now line while that still names
    the job (and isn't the routine's own waiting line), else the job's newest line in the status block's log."""
    head = (text or "").split("\n---\n", 1)[0]
    m = re.search(rf"^## Now: Job {int(n)} · (.+)$", head, re.M)
    if m and not _not_a_step(m.group(1)):
        return _clean(re.sub(r";? *watch it:.*$", "", m.group(1)))
    for line in re.findall(r"^- \d\d:\d\d (.+)$", head, re.M):
        m = re.match(rf"job {int(n)}(?::| ·) (.+)", line)
        if m and not _not_a_step(m.group(1)):
            return _clean(m.group(1))
    return ""


def _not_a_step(s):
    """The routine's own lines and the hold itself say nothing about where the job got to."""
    return bool(re.match(r"(started by the routine|started again|carries on|waits\b|held\b|ended\b|stopped\b|done\b)", s)
                or re.search(r"\bSTOP(PED)?\b|usage over the line|waits for the usage|held (by|at) the usage", s))


def on_held(n, text, now=None):
    """jobs.py held N: note when, and at about which step, so the next start can say so. F72: a job with its
    steps written down was held before its next step; that's the step."""
    rec = load(n)
    rec["held"] = time.strftime("%H:%M", time.localtime(now or time.time()))
    nxt = next_step(n)
    rec["step"] = ((f"before step {nxt['k']} of {len(load_steps(n))}: {nxt['name']} (steps 1 to {nxt['k'] - 1} saved)"
                    if nxt["k"] > 1 else f"before step 1 of {len(load_steps(n))}: {nxt['name']}") if nxt
                   else step_from_roadmap(n, text) or rec.get("step", ""))
    save(n, rec)
    return rec


def plan(job, text, folder=None):
    """How the routine starts job: {"mode": "new" | "resume" | "fresh", "session", "step", "held", "why"}.
    "resume": its own earlier chat, with its memory. "fresh": a new chat with the note (it was held, but the
    old chat isn't here). "new": a job that wasn't held. Every mode gets the session id to start with."""
    n = job["n"]
    rec = load(n)
    held = job["state"].startswith("held") or bool(rec.get("held"))
    if not held:
        return {"mode": "new", "session": str(uuid.uuid4())}
    step = rec.get("step") or step_from_roadmap(n, text)
    out = {"step": step, "held": rec.get("held", "")}
    if rec.get("session") and chat_there(rec["session"], folder):
        return dict(out, mode="resume", session=rec["session"])
    why = ("its earlier chat isn't on this computer (it ran on the other one, or before this was built)"
           if not rec.get("session") else "its earlier chat can't be found here any more")
    return dict(out, mode="fresh", session=str(uuid.uuid4()), why=why)


# ---------- F72: big work in steps, saved as they go ----------

STEPS_MAX = 20  # more than this isn't steps any more, it's a to-do list


def _steps_file(n):
    return os.path.join(DIR, f"job-{int(n)}-steps.json")


def load_steps(n):
    """Job n's steps, oldest first: [{"k", "name", "done": "HH:MM" | None, "commit": sha | None}]."""
    try:
        return json.load(open(_steps_file(n))).get("steps") or []
    except (OSError, ValueError, AttributeError):
        return []


def _save_steps(n, steps):
    os.makedirs(DIR, exist_ok=True)
    tmp = _steps_file(n) + ".tmp"
    json.dump({"n": int(n), "steps": steps, "saved": int(time.time())}, open(tmp, "w"), indent=1)
    os.replace(tmp, _steps_file(n))


def set_steps(n, names):
    """The job's steps. Steps already done stay as they are, first; the names given replace the rest (a name
    list that starts with the done ones' names skips them). Returns the steps, or raises ValueError."""
    names = [_clean(x) for x in names if _clean(x)]
    old = load_steps(n)
    done = [x for x in old if x.get("done")]
    if done and [x["name"] for x in done] == names[:len(done)]:
        names = names[len(done):]
    if not names and not done:
        raise ValueError("no steps given")
    if len(done) + len(names) > STEPS_MAX:
        raise ValueError(f"at most {STEPS_MAX} steps")
    steps = done + [{"k": len(done) + i + 1, "name": x, "done": None, "commit": None} for i, x in enumerate(names)]
    _save_steps(n, steps)
    return steps


def _hq_git(*args):
    r = subprocess.run(["git", "-C", os.environ.get("HQ_STEPS_GIT") or ROOT, *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def step_done(n, k, anyway=False, now=None):
    """Step k of job n is done and saved: its time and HQ's commit. Refused (ValueError) while HQ has changes
    that aren't committed (the step isn't saved yet), unless anyway; and for a step that isn't there."""
    steps = load_steps(n)
    if not steps:
        raise ValueError(f"job {n} has no steps written down; first: jobs.py steps {n} \"STEP 1\" \"STEP 2\" …")
    hit = [x for x in steps if x["k"] == int(k)]
    if not hit:
        raise ValueError(f"job {n} has steps 1 to {len(steps)}")
    code, dirty = _hq_git("status", "--porcelain", "--untracked-files=no")
    if code == 0 and dirty and not anyway:
        raise ValueError("HQ has changes that aren't committed, so this step isn't saved yet: commit them first "
                         f"(the subject \"ROW: … (job {n}, step {k} of {len(steps)})\"), then mark it again")
    code, sha = _hq_git("rev-parse", "--short", "HEAD")
    hit[0]["done"] = time.strftime("%H:%M", time.localtime(now or time.time()))
    hit[0]["commit"] = sha if code == 0 else None
    _save_steps(n, steps)
    return hit[0], steps


def next_step(n):
    """The first step not done yet, or None (no steps, or all done)."""
    return next((x for x in load_steps(n) if not x.get("done")), None)


def copy_steps(old, new):
    """A crash rerun (H62) takes its first run's steps, so it carries on at the next one."""
    steps = load_steps(old)
    if steps:
        _save_steps(new, steps)
    return steps


def steps_words(n):
    """One line per step, for the job's own prompt and for a look by hand."""
    steps = load_steps(n)
    return "\n".join(f"- step {x['k']} of {len(steps)}: {x['name']}: "
                      + (f"done {x['done']}, saved in {x['commit'] or 'HQ'}" if x.get("done") else "not done yet")
                      for x in steps)


def steps_note(n, first=None):
    """F72: what a carried-on run is told about the steps. `first`: the job whose steps these were (a rerun)."""
    steps = load_steps(n)
    if not steps:
        return ""
    nxt = next_step(n)
    who = f"job {first}'s" if first else "this job's"
    head = (f"\n\nThe steps of {who} first run, as written down (F72):\n{steps_words(n)}\n")
    if not nxt:
        return head + ("Every step is done and saved: check the work is whole (the flows, the row's write-up, the "
                       "push), then finish.")
    return head + (f"Carry on at step {nxt['k']}: {nxt['name']}. "
                   + (f"Steps 1 to {nxt['k'] - 1} are saved in HQ's commits: don't redo them. " if nxt["k"] > 1 else "")
                   + f"Mark each step done as before (jobs.py step {n} K, after its commit).")


def steps_rule(n):
    """F72: the rule a big job gets in its first prompt."""
    jp = json.dumps(os.path.join(HERE, "jobs.py"))
    return (f"\n\nThis is big work, so it's done in steps that are saved as they go (F72): a stop by the usage line "
            "or a crash then picks up at the next step, not the top. Before building, cut it into steps (two to "
            f"eight, each one leaving HQ whole) and write them down: python3 {jp} steps {n} \"STEP 1\" \"STEP 2\" …. "
            f"After each step, commit it in HQ (the subject \"ROW: … (job {n}, step K of M)\") and mark it: "
            f"python3 {jp} step {n} K. The steps can be changed later with the same steps command; the done ones stay.")


def needs_steps(text, kind=None, est=None):
    """F72: big work gets the steps rule: a big build, an estimate of 40 minutes or more, or words that ask
    for it. A QA, a release, a merge or a transcription isn't cut into steps."""
    t = text or ""
    if kind in ("qa", "release", "merge", "transcribe") or t.startswith("QA of"):
        return False
    return (kind == "bigbuild" or (isinstance(est, (int, float)) and est >= BIG_MINUTES)
            or bool(re.search(r"\b(cut into steps|in steps that are saved|big build|big work)\b", t, re.I)))


BIG_MINUTES = 40


def started(n, p):
    """The routine started job n as planned: keep its chat's id; the hold is used up."""
    save(n, {"session": p["session"], "started": time.time(), "mode": p["mode"],
             **({"step": p["step"]} if p.get("step") else {})})


def resume_prompt(n, where, p, text_of_job, past_note=""):
    at = f" at about this step: {p['step']}" if p.get("step") else ""
    when = f" at {p['held']}" if p.get("held") else ""
    return (f"let's go again. This is job {n} from the queue on the HQ roadmap, started again by the routine "
            f"(phase L) in {where}. The usage line held it{when}{at} (H113). This is your own earlier chat for "
            "this job, so you know what you already did. First check where things stand (git status and git log "
            "in HQ and the workspace, the status block) against where you were, then carry on from there to the "
            "end; don't redo what's done. Same as before: read the usage before the first step and at every "
            "status block rewrite, hold again on STOP, and finish with the done mark as the very last step. "
            f"Read your notes first, then after each step and always before any push or release: python3 "
            f"{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jobs.py')} notes {n} (H283). "
            f"The job, as agreed on the call: {text_of_job}" + (f"\n\n{past_note}" if past_note else "")
            + steps_note(n))


def fresh_note(n, p):
    at = f", at about this step: {p['step']}" if p.get("step") else " (the step it was at isn't known here)"
    when = f" at {p['held']}" if p.get("held") else ""
    return (f"\n\nThis job was stopped by the usage line{when}{at} (H113). It is started again in a fresh chat "
            f"because {p.get('why') or 'its earlier chat can not be picked up'}. First look at what the first run "
            "left (git status and git log in HQ and the workspace, its lines in the status block's log, its row "
            "on the roadmap; on another computer its saved steps are the HQ commits that say \"(job "
            f"{n}, step\"), then carry on from there; don't redo what's already done." + steps_note(n))


if __name__ == "__main__":
    # For a look by hand: python3 routine/carryon.py N
    if len(sys.argv) == 2 and sys.argv[1].isdigit():
        print(json.dumps(load(int(sys.argv[1])), indent=1))
        if load_steps(int(sys.argv[1])):
            print(steps_words(int(sys.argv[1])))
    else:
        print(__doc__)
