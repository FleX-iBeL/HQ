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
"""
import glob, json, os, re, sys, time, uuid

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
    """jobs.py held N: note when, and at about which step, so the next start can say so."""
    rec = load(n)
    rec["held"] = time.strftime("%H:%M", time.localtime(now or time.time()))
    rec["step"] = step_from_roadmap(n, text) or rec.get("step", "")
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
            f"The job, as agreed on the call: {text_of_job}" + (f"\n\n{past_note}" if past_note else ""))


def fresh_note(n, p):
    at = f", at about this step: {p['step']}" if p.get("step") else " (the step it was at isn't known here)"
    when = f" at {p['held']}" if p.get("held") else ""
    return (f"\n\nThis job was stopped by the usage line{when}{at} (H113). It is started again in a fresh chat "
            f"because {p.get('why') or 'its earlier chat can not be picked up'}. First look at what the first run "
            "left (git status and git log in HQ and the workspace, its lines in the status block's log, its row "
            "on the roadmap), then carry on from there; don't redo what's already done.")


if __name__ == "__main__":
    # For a look by hand: python3 routine/carryon.py N
    if len(sys.argv) == 2 and sys.argv[1].isdigit():
        print(json.dumps(load(int(sys.argv[1])), indent=1))
    else:
        print(__doc__)
