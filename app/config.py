"""HQ settings, in one place. Override any of them with an environment variable."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # HQ: the app, the same for everyone (M1)
MODELS = ROOT / "models"
SCRATCH = ROOT / "scratch"  # empty working folder for the plain Claude (git-ignored)
# M1 (10 October 2026): the user's own files are in HQ/workspace, which the HQ repo ignores (it can
# be a link to a folder elsewhere). The call's Claude works there, like a chat in that folder, on
# the resolved path, so the folder's settings and Claude's memory for it are the same as in a chat.
WORKSPACE = Path(os.environ.get("HQ_WORKSPACE", str(ROOT / "workspace")))
FOLDER = Path(os.environ.get("HQ_FOLDER", os.path.realpath(WORKSPACE)))
DATA = FOLDER / "HQ"  # the roadmap and the call transcripts
CALLS = Path(os.environ.get("HQ_CALLS", str(DATA / "calls")))  # one transcript per call
# M5: who the user is comes from their workspace (me.md), never from this code.
import me as _me
ME = _me.load(FOLDER)
USER = ME["name"] or "the user"  # in the call rules and the call system's notes
USER_LABEL = ME["name"] or "Me"  # their lines in a transcript
def _local_timezone() -> str:
    """This Mac's own time zone (the user's clock), e.g. Europe/Amsterdam; HQ_TIMEZONE overrides it."""
    try:
        return os.environ.get("HQ_TIMEZONE") or os.path.realpath("/etc/localtime").split("/zoneinfo/", 1)[1]
    except IndexError:
        return "UTC"


TIMEZONE = _local_timezone()
# HQ_PLAIN=1 goes back to the A2 plain Claude (no files, tools or connectors).
PLAIN = os.environ.get("HQ_PLAIN", "") == "1"
# H55 (12 October 2026): HQ_FREE_ONLY=1 makes every call a Free call, whatever the page sends:
# for a test line on a server with nothing of the user's on it (the VPS).
FREE_ONLY = os.environ.get("HQ_FREE_ONLY", "") == "1"
# After hang-up Claude writes down what matters, commits and pushes. HQ_WRAP_UP=dry
# makes it only say what it would do (tests); HQ_WRAP_UP=off skips it.
WRAP_UP = os.environ.get("HQ_WRAP_UP", "on")
WRAP_UP_TIMEOUT_SECS = float(os.environ.get("HQ_WRAP_UP_TIMEOUT_SECS", "600"))

# The brain. Sonnet is the talker; HQ_MODEL=haiku tries Haiku 4.5 instead.
MODEL_ALIASES = {
    "sonnet": "claude-sonnet-5-5",
    "haiku": "claude-haiku-4-5-20251001",
    "opus": "claude-opus-5-5",
}
_model = os.environ.get("HQ_MODEL", "sonnet")
MODEL = MODEL_ALIASES.get(_model, _model)
# Effort for the talker: low keeps the first words quick. (Thinking can't be switched
# off with "disabled" on Sonnet 5.5; low effort is the supported way to keep it short.)
EFFORT = os.environ.get("HQ_EFFORT", "low")
# The call page has two buttons: Quick (Sonnet, the default) and Deep (Opus, for sparring and
# bigger planning; 9 October 2026). Deep thinks a little longer before it speaks.
CALL_MODES = {"quick": "sonnet", "deep": "opus", "free": "sonnet"}  # "free": old pages (before H8)
# H7, free mode (9 October 2026: "I want to show this to other people"): a plain
# Claude on Sonnet. None of the user's files, no connectors, no tools, no transcript, no log, no
# commit, and their words are not written to the server log. Its working folder is an empty one
# outside the workspace, so no CLAUDE.md or memory of theirs can be found from it.
FREE_DIR = Path(os.environ.get("HQ_FREE_DIR", str(Path.home() / ".hq" / "free")))
# H8 (9 October 2026): Free is a switch on top of Quick and Deep, so it runs on Sonnet or
# Opus; and "I do want it to be able to access the internet". Its only tools: searching the web and
# reading a web page. Still none of the user's files, connectors, calendar or mail.
FREE_TOOLS = ["WebSearch", "WebFetch"]
DEEP_EFFORT = os.environ.get("HQ_DEEP_EFFORT", "medium")


def effort_for(model: str) -> str:
    return DEEP_EFFORT if model == MODEL_ALIASES["opus"] else EFFORT
CLAUDE_CLI = os.environ.get("HQ_CLAUDE_CLI", "/opt/homebrew/bin/claude")

# Phase K, lighter calls (9 October 2026: "ok can we put this on roadmap, with a backup
# kind of thing that if we dont like it, we can revert it?"). One switch per step, on by default;
# set one to 0 to go back to how it was (or check out the git tag before-phase-K for all of them).
# The switches live in switches.env next to the roadmap (start.sh starts the server with a clean
# environment, so a file is what survives a restart and a reboot); an environment variable wins.
_SWITCHES = {}
for _line in (ROOT / "switches.env").read_text().splitlines() if (ROOT / "switches.env").exists() else []:
    if "=" in _line and not _line.lstrip().startswith("#"):
        _k, _v = _line.split("=", 1)
        _SWITCHES[_k.strip()] = _v.split("#")[0].strip()


def _switch(name: str) -> bool:
    return os.environ.get(name, _SWITCHES.get(name, "1")) != "0"
LIGHT_NOTES = _switch("HQ_LIGHT_NOTES")  # K1: Quick has the log's open commitments, not two days of entries
NO_DOCS = _switch("HQ_NO_DOCS")  # K2: no Claude Docs tools on Quick or Deep
TOOLS_ON_DEMAND = _switch("HQ_TOOLS_ON_DEMAND")  # K3: connector tools loaded when needed (tool search on)
CHEAP_AFTER_CALL = _switch("HQ_CHEAP_AFTER_CALL")  # K4: the after-call work runs on AFTER_CALL_MODEL
AFTER_CALL_MODEL = os.environ.get("HQ_AFTER_CALL_MODEL", "haiku")  # the CLI on this laptop (2.1.286) maps this to Haiku 4.5; it doesn't know Haiku 5.5 yet
DOCS_SERVER = "mcp__claude_ai_Claude_Docs"


def light_switches() -> str:
    return ", ".join(f"{k} {'on' if v else 'off'}" for k, v in (
        ("K1 notes", LIGHT_NOTES), ("K2 no Docs", NO_DOCS), ("K3 tools on demand", TOOLS_ON_DEMAND),
        ("K4 cheap after-call", CHEAP_AFTER_CALL)))

SYSTEM_PROMPT = """You are {user}'s assistant in HQ, on a live voice call with them. \
Everything you write is turned into speech the moment you write it, and {user} hears it through their earphones.

How to talk:
- Short spoken sentences, like a person on the phone. Usually one to three sentences per reply.
- Keep your first sentence especially short, a few words, so he hears you right away.
- Plain words only. No markdown, no lists, no headings, no emojis, no URLs, no code.
- Say numbers, dates and times the way you would say them out loud.
- If you didn't catch something, say so briefly and ask him to repeat it.
- Their words come to you through speech recognition, so names and words in other \
languages can be misheard; go with the most likely meaning.
- If a message starts with a note in square brackets, it is from the call system, not from {user}."""

# H8: added to SYSTEM_PROMPT in free mode. Claude's wording.
FREE_RULES = """
- You can search the web and read web pages. Use them when a question needs current or exact \
facts; before you do, say one very short sentence like "Let me look that up." Never read out links.
- {user} may be showing this call to other people. You know nothing about their private life here, \
so don't make anything up about it."""

# A3: added to the folder's own instructions (CLAUDE.md, rules.md), not instead of them.
VOICE_RULES = """# This chat is a live voice call

{user} is talking to you on a live voice call (HQ), through their earphones. Everything \
you write as text is turned into speech the moment you write it. His words reach you \
through speech recognition.

Who you are on the call: his full-time personal assistant, sitting at your desk, picking up \
when he calls. Warm, calm, on top of things, with a normal human phone manner: "Sure.", "Got it.", \
"Okay, done.", "Good question." Talk about his things the way an assistant would: his \
agenda, his list, your notes, his inbox. Never mention being an AI, models, tools, files, \
sessions, prompts or "the system". Don't over-apologise, don't recap what he just said, and \
don't end every reply with a question; on the phone a plain "Done." is fine.

How to talk on the call:
- Follow rules.md as a person on the phone would: short spoken sentences, usually one to \
three per reply. Keep the first sentence especially short, so he hears you right away.
- Never write anything that can't be said out loud: no markdown, lists, headings, links, \
file names, paths, code, commands or emojis. Say dates, times and numbers the way you'd say them.
- Before you use a tool you may say one very short sentence first, like "Let me look at your calendar." \
Never say you're doing or have done something that may still need his yes. When you're \
done, say the result plainly. Don't narrate each step.
- When he calls, the call system greets them for you (like "Hey there, what can I do for \
you?"). Don't greet him again; just answer what he says.
- The call system may play a short filler for you while you work ("One sec."). It is not \
in your text; don't repeat it, just go on.
- Messages that start with a note in square brackets come from the call system, not from \
{user}. Names and words in other languages can be misheard (see any dictation slips in CLAUDE.md); \
go with the most likely meaning, and ask when it matters.

What is different from a normal chat:
- Don't run the start-of-session routine (the calendar overview and the mail check) on \
your own. Do it only when he asks. Answer what he says first. The one thing you do bring up \
yourself: the very important open items from his mail list, which the call system gives you when \
he calls. Name them in your first reply, after answering him, every call, until he says they're \
resolved or not that important.
- Some actions need his okay. If a tool call is refused with "needs {user}'s yes", check it \
with him like a real assistant would, in one natural sentence with the details ("Shall I put \
that in for Saturday at half six?"), never "say yes or no", and stop; the call system tells \
you his answer. If he answers with a change ("yes, but make it seven"), make the change and \
check again. Never ask by any other means, and never try a way around a refusal.
- When something is done, confirm it the way a person would: "Done, it's in for Saturday at \
half six, until half eight." If you filled something in yourself, like an end time, just say \
it in passing ("I've blocked it until half eight"), not as an explanation.
- Say times the way a person would say them out loud: "ten o'clock", "quarter past two".
- Writing things down during the call works as usual (where-things-go.md). Only the quiet notes, \
the commit and the push happen after he hangs up.
- Work for the computer (building, a bigger job, anything agreed for "let's go") goes in the queue \
on the HQ roadmap; the computer starts it by itself within about a minute, one job at a time, \
in a window he can watch. Agree it first: what exactly, and write it on the roadmap and in the \
status block's Next line as usual. Only on his clear go ("let's go", "do it", "start it"), add it: \
python3 "{HQ}/routine/jobs.py" add "<the job in one self-contained line, with everything the \
computer needs: the steps, and his words where they matter>". Don't write "the Next line": copy what \
it says, so a later change can't change this job. Add --past-the-line only when he says it may go \
past the usage line; it only goes past the 5-hour line, the weekly line always counts (F13). \
Always add --kind with what the job is, for its estimate (H70): transcribe (transcribing recordings), \
big (runs the whole set of happy flows), call (restarts the call line as its last step), build \
(building or changing HQ otherwise, a roadmap step like H56.2 too), other (research, moving or \
checking things). Then tell him it's queued, and whether something runs before it. If the job \
restarts the call line, tell him the call will drop and to call back when it's done.
- The queue on a call: "list" says what runs and waits, with each waiting job's place in line \
and its estimate (H61: how long, and when it should be done; the last line the whole list), learned \
from how long earlier jobs took; say them as estimates ("around ten past two, if it goes like the \
last ones"), and that a held job waits on the usage; \
"stop" ends the running job, "stop N" cancels waiting job N; "overrule N" lets job N past the 5-hour usage \
line (never the weekly line); "off" and "on" switch the whole routine. Use them when he asks.
- The waiting jobs run in the order they stand on the list, top first, not by number. When he wants \
a job sooner or later, move it: "move N top", "move N up", "move N down", "move N bottom", or \
"move N before M" / "move N after M". The job numbers stay the same; tell him its new place in line \
in a sentence ("Job 29 is next now, then 27 and 28"). The status page and the roadmap's status block show how a job is going.
- The scheduler (H43): work planned ahead for a day and a time, next to the queue. When he wants \
something done later ("on Tuesday at three"), agree it like a job, and on his clear go plan it: \
python3 "{HQ}/routine/schedule.py" add "<when>" "<the work in one self-contained line, as for a job>". \
When is a day and a time: 2026-10-13 15:00, today 15:00, tomorrow 9:30, tuesday 15:00 (the next one), \
or now; work out the date yourself when he says something else. Add --past-the-line only on his say-so, \
as for a job. The job list always goes first: an item whose time has come starts only when no job \
runs or waits, then it becomes a job and starts within about a minute. "list" says what's planned \
and what came of the earlier ones (looking back); "cancel N" cancels item N; "move N \"<when>\"" gives \
it another day or time. Tell him in a sentence when it is planned ("Planned for Tuesday at three").
- When he asks what the usage is, run python3 "{HQ}/routine/usage-check.py" and tell him the \
5-hour and the weekly numbers in a sentence, with how old they are: they are the latest saved \
numbers (from a running job or the hourly mail check), not read live, and it costs nothing. Weekly \
Fable is the last one from a normal chat, so say it's the last known one.
- HQ itself, the app at {HQ}, you may read freely, the same as the workspace (H65): its files, \
its logs in {HQ}/scratch (the hourly mail check's own log is {HQ}/scratch/routine/mail.log, its last start \
in {HQ}/scratch/routine/mail-last), and the status page's data with curl on this computer only: \
curl -s http://localhost:4748/routines.json (every routine, when it last ran and runs next), /usage.json, \
/roadmap.md, /jobs-history.json. Changing anything in HQ (editing, git changes, running its scripts \
other than the ones above) still asks him first; building HQ is work for the queue.
- Keep working with the lid closed (lid-closed sleep): when he asks which it is, run python3 \
"{HQ}/routine/lidsleep.py"; to turn it on ("keep working with the lid closed") add on, to turn \
it off ("back to normal", sleeps when the lid closes) add off. Flip it on his ask, then tell him in a \
sentence which it is now. On drains the battery in a bag, so when he turns it on, say that once. If \
it says the one-time setup isn't done, tell him he types one line once in Terminal with his laptop \
password; it's on the HQ roadmap under H45, and he can do it next time he's at the laptop.
"""
# M1: the routine's scripts are in HQ, outside the folder the call works in.
VOICE_RULES = VOICE_RULES.replace("{HQ}", str(ROOT))
# M5: the user's own additions for calls (me.md, "On calls"), and their name.
if ME["on_calls"]:
    VOICE_RULES += "\nFrom the user's own notes for calls:\n" + ME["on_calls"] + "\n"
SYSTEM_PROMPT = SYSTEM_PROMPT.replace("{user}", USER)
FREE_RULES = FREE_RULES.replace("{user}", USER)
VOICE_RULES = VOICE_RULES.replace("{user}", USER)

WRAP_UP_PROMPT = """[Call system: @USER@ has hung up. The call is over, and nothing you write now is spoken.
Do the after-call work, quietly and fully, as in a normal chat:
1. Write what matters from this call into the right places, as where-things-go.md says, in his words. \
At least one entry in coaching/log.md, newest first, headed with today's date, the time the call \
started ({start}) and the type "call", with his own words from the call and any commitments or follow-ups.
2. The full transcript of the call is in {transcript}. Read it if you need to; don't change it.
3. Then commit and push, as CLAUDE.md says: git add every file you changed plus the transcript, \
each by name (never -A or a dot), then one plain command: git commit -q -m "Call {start_short}: <a short description>", then git push. \
One line per command, no here-documents.
Nobody can answer questions now: if something needs his yes, leave it, and note it in the log as a follow-up. \
Don't start new work here, because nobody can be asked.
When you're done, reply with one line saying what you wrote and committed.]"""

WRAP_UP_DRY_PROMPT = """[Call system: TEST RUN. @USER@ has hung up. Don't change any file and don't run git. \
Reply with one short line saying which files you would update and what you would commit. The transcript is in {transcript}.]"""
WRAP_UP_PROMPT = WRAP_UP_PROMPT.replace("@USER@", USER)
WRAP_UP_DRY_PROMPT = WRAP_UP_DRY_PROMPT.replace("@USER@", USER)

# Fillers: when Claude hasn't said anything this long after the user's turn ends, HQ
# says one of these right away (pre-recorded at call start). And when Claude starts a tool
# mid-reply after this long a silence, a tool filler.
FILLER_AFTER_SECS = float(os.environ.get("HQ_FILLER_AFTER_SECS", "1.2"))
TOOL_FILLER_SILENCE_SECS = float(os.environ.get("HQ_TOOL_FILLER_SILENCE_SECS", "2.0"))
# 9 October 2026: "i want the conversation to sound like real human" and "as if i call
# it up and the person is sitting behind a desk and is fulltime my assistant." So the lines
# fit what she's doing: the calendar, the mail, writing something down, looking something up.
# Later the same night: the lines right after he stops talking confirm that she heard him,
# instead of "let me check that": "Just like a confirmation, in a humanized way" and "Like
# that makes sense, stuff like that. Gotcha."
# "How many variations did you build? Because if it's only three, I want you to build way,
# way, way more." Only this moment; the calendar, mail and writing lines stay as they were.
# No "Mm" lines: the voice says them oddly ("What does this MM lemme think mean?").
FILLERS = [
    "Gotcha.", "Got it.", "That makes sense.", "Okay, I hear you.", "Right, understood.",
    "Sure thing.", "I see what you're saying.", "Yeah, makes sense.", "Okay, gotcha.", "Got you.",
    "Okay.", "Right, okay.", "Yep, I'm with you.", "Okay, fair enough.", "Ah, I see.",
    "I hear you.", "Okay, sure.", "Right, I follow.", "Yeah, I get it.", "Okay, noted.",
    "Sure, that's clear.", "Yeah, I hear you.", "Alright, got it.", "Okay, understood.",
    "Yeah, totally.", "Right, of course.", "Okay, that's clear.", "Good point.",
    "Yeah, I see what you mean.", "Alright.", "Okay, I'm with you.", "Sure, makes sense.",
    "Right, gotcha.", "Yep, understood.", "Okay, yeah.", "Ah, okay.", "Yep, got it.",
    "Okay, that makes sense.", "Right, I hear you.", "Sure, I get that.",
]
TOOL_FILLERS = {
    "calendar": ["Let me pull up your calendar.", "One sec, let me open your agenda.",
                 "Let me grab your calendar real quick."],
    "mail": ["Let me log in and check your mail.", "Hang on, let me open your inbox.",
             "Let me have a look in your mail."],
    "write": ["Let me grab a pen and write that down for you.", "Okay, writing that down.",
              "One sec, let me note that."],
    "read": ["Let me gather my things and take a look for you.", "Let me look that up in my notes.",
             "Let me dig that up for you."],
    "tool": ["Let me take a look.", "Bear with me, I'm on it.", "Let me check that for you."],
}


# HQ opens the call (9 October 2026: "i want that [it] starts the conversation, not me.
# something like \"Hey there, what can i do for you\""). Picked by time of day. {n} is ", Name"
# (or nothing), {s} is " Name" (or nothing), from me.md.
_GREETINGS = {
    "morning": ["Good morning{n}. What can I do for you?", "Morning{n}! What's up?",
                "Hey there{s}, good morning. How can I help?"],
    "afternoon": ["Hey there{s}, what can I do for you?", "Hi{s}! What's up?",
                  "Hey{s}, good to hear from you. What can I do for you?"],
    "evening": ["Good evening{n}. What can I do for you?", "Hey there{s}, what can I do for you?",
                "Evening{n}! What's up?"],
    "night": ["Hey{s}, you're up late. What can I do for you?", "Hi{s}. What can I do for you?"],
}
_N = ME["name"]
GREETINGS = {k: [g.replace("{n}", f", {_N}" if _N else "").replace("{s}", f" {_N}" if _N else "") for g in v]
             for k, v in _GREETINGS.items()}


# H60 (11 October 2026), in the user's words: "instead of saying something like 'hey <name> what's up' you say
# something like 'Hey <name>, let's continue from where we left off'". The greeting when a call continues an earlier one.
_CONTINUE_GREETINGS = ["Hey{s}, let's continue from where we left off.", "Hey{s}, let's pick up where we left off.",
                       "Hi{s}, let's continue where we left off."]
CONTINUE_GREETINGS = [g.replace("{s}", f" {_N}" if _N else "") for g in _CONTINUE_GREETINGS]
# H60: how much of the earlier call goes in, at most (characters, the newest kept; Claude's choice).
CONTINUE_MAX_CHARS = 12000


def greetings_now() -> list[str]:
    import datetime
    h = datetime.datetime.now().hour
    part = ("night" if h < 5 or h >= 23 else "morning" if h < 12 else "afternoon" if h < 18
            else "evening")
    return GREETINGS[part]


def tool_kind(name: str) -> str:
    """Which kind of tool line fits this tool."""
    n = name.lower()
    if "calendar" in n:
        return "calendar"
    if "gmail" in n or "mail" in n:
        return "mail"
    if n in ("edit", "write", "multiedit", "notebookedit"):
        return "write"
    if n in ("read", "grep", "glob", "bash", "skill") or "docs" in n:
        return "read"
    return "tool"

# Hearing. A short word list helps Whisper with names: HQ, the agents (H29), the user's name,
# and their own "Names to hear" from me.md (M5).
import agents as _agents  # noqa: E402
# H55 (12 October 2026): off a Mac there is no MLX, so Whisper runs on the CPU with faster-whisper.
# On the VPS (4 cores) large was 7 s a sentence, small about 2 s, base about 1 s; small hears
# a real voice outside better, so it's the default there. HQ_STT and HQ_WHISPER override both.
import sys as _sys  # noqa: E402
STT_ENGINE = os.environ.get("HQ_STT", "mlx" if _sys.platform == "darwin" else "faster")
WHISPER_MODEL = os.environ.get(
    "HQ_WHISPER", "mlx-community/whisper-large-v3-turbo" if STT_ENGINE == "mlx" else "small")
WHISPER_PROMPT = os.environ.get(
    "HQ_WHISPER_PROMPT",
    ", ".join(w for w in ["HQ", *_agents.names(FOLDER), ME["name"], ME["hear"].rstrip(".")] if w) + ".",
)

# Ears. How long a silence must be before the turn may end. Pipecat's default is 0.2 s,
# but Whisper needs about a second, and in that second the user often goes on talking,
# which split one question into several Claude turns. 0.5 s kept every test question whole.
VAD_STOP_SECS = float(os.environ.get("HQ_VAD_STOP_SECS", "0.5"))
# Whisper large-v3-turbo on the M2: about 1.0 to 1.2 s from the end of speech to the text.
WHISPER_P99_SECS = float(os.environ.get("HQ_WHISPER_P99_SECS", "1.5"))
# H12: in free talking, once the turn looks finished, wait this much longer before HQ
# takes it; if he goes on talking in that time, the turn stays his. The call page shows the
# wait in yellow. 9 October 2026: "just keep it yellow for a little longer while we wait."
TURN_GRACE_SECS = float(os.environ.get("HQ_TURN_GRACE_SECS", "1.0"))
# H11: a turn never ends while Whisper is still turning a piece of speech into text. If that
# takes longer than this (it shouldn't), the turn may end anyway, so a call can't hang.
TRANSCRIBING_MAX_SECS = float(os.environ.get("HQ_TRANSCRIBING_MAX_SECS", "6"))

# Voice.
VOICE = os.environ.get("HQ_VOICE", "af_heart")
# A long first sentence may be cut once at a comma after this many words; later ones never.
FIRST_CLAUSE_MIN_WORDS = int(os.environ.get("HQ_FIRST_CLAUSE_MIN_WORDS", "10"))
# H18 (10 October 2026): Pipecat gives up on a reply's audio when the voice sends nothing for 3 s,
# and drops the sentence. On a busy MacBook Kokoro sometimes needs longer for one sentence, so
# the reply ended without sound (likely bug F4 too). The reply's end is marked explicitly, so this
# only matters while Kokoro is still working.
TTS_STALL_SECS = float(os.environ.get("HQ_TTS_STALL_SECS", "12"))
# Voices the user can pick on the call page (9 October 2026). Heart is the default.
VOICES = {
    "af_heart": "Heart", "af_bella": "Bella", "am_michael": "Michael", "bf_isabella": "Isabella",
    "bf_emma": "Emma", "am_adam": "Adam", "am_eric": "Eric", "bm_george": "George", "bm_fable": "Fable",
}


def voice_lang(voice: str) -> str:
    """Kokoro's accent: British voices start with b (bf_, bm_), the rest are American."""
    return "en-gb" if voice.startswith("b") else "en-us"
KOKORO_MODEL = MODELS / "kokoro-v1.0.onnx"
KOKORO_VOICES = MODELS / "voices-v1.0.bin"

# Serving. Only this MacBook for now; A4 opens it to the phone over Tailscale.
HOST = os.environ.get("HQ_HOST", "127.0.0.1")
PORT = int(os.environ.get("HQ_PORT", "7860"))
