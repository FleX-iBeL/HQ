"""H132: what each agent has said about herself, so she stays the same person on every call and in every text.

The user, 14 October 2026 (call at 13:31): "Donna made some comment about she has a nice chair. When there are
personality comments made like this, I want it to be stored in their own notes. So that their messaging in the
future will stay consistent."

One file per agent in the workspace (never in HQ's code): HQ/agents/<id>-about-herself.md, one fact per line
("- …"). Written after a call with the call's notes (the wrap-up prompt, config.WRAP_UP_PROMPT) and by her direct-line
chat when she says it there (direct_line.TEXT_RULES); agents.load gives each agent her list as `about_self`, and
agents.persona puts it in front of her on every call, three-way call and text. Standard library only.

    python3 app/about_self.py                     every agent's list
    python3 app/about_self.py list AGENT          one agent's list (AGENT: her id or name)
    python3 app/about_self.py add AGENT "FACT"    keep one fact (skipped when it's already there); prints the file
    python3 app/about_self.py harvest-call FILE   H232: keep the new things the agents said about themselves on a call
    python3 app/about_self.py harvest-text AGENT "TEXT"   the same for one of her texts
    python3 app/about_self.py tidy                drop the near-repeats from every list

H232 (the user's quick note, 20 October 2026: "you were supposed to keep making new personal comments and keeping
track of them and build a unique personality this way"): the list only grew when the after-call work (on the cheap
model, one optional line among many) remembered to run `add`, and a repeat only counted word for word, so it stayed at
one or two lines, one of them twice. Now HQ itself harvests: after every call and every text of hers a small look
(Haiku, no tools) reads what she said and returns only the new things about herself, a near-repeat is skipped, and
her persona nudges her to bring in a new one now and then and an old one back, never contradicting one.

H298, piece 2 (29 October 2026, the identity fix): the harvest had kept lines about the user's life as the agent's own
(she "does yoga every morning", "biked to the shop in the rain"), because his sentences and hers about him read alike to
the look. Now the look is told her life is only her own, and `own_life` holds each fact against what she really said:
kept only when its words come from a sentence of hers in the first person that isn't about him. The lists already
written are the user's to wipe (they're in the workspace); `tidy` drops only near-repeats.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

MOST = 40  # facts kept per agent, the newest; Claude's choice
LONGEST = 200  # characters per fact

HEAD = ("# What {name} has said about herself\n\n"
        "> **Private.** H132, H232: the little things {name} has told you about herself on calls and in her chat "
        "(her day, her desk, her moods and opinions, the office), kept by HQ after every call and text, so she stays "
        "the same person. Loaded with her character on every "
        "call and text. Change or remove a line whenever you like.\n\n")


def _folder() -> Path:
    if os.environ.get("HQ_FOLDER"):
        return Path(os.environ["HQ_FOLDER"])
    ws = Path(os.environ.get("HQ_WORKSPACE", str(Path(__file__).resolve().parent.parent / "workspace")))
    return Path(os.path.realpath(ws))


def path(folder: Path | None, agent_id: str) -> Path:
    return (folder or _folder()) / "HQ" / "agents" / f"{agent_id}-about-herself.md"


def facts(folder: Path | None, agent_id: str) -> list[str]:
    try:
        text = path(folder, agent_id).read_text(encoding="utf8")
    except OSError:
        return []
    return [l[2:].strip() for l in text.splitlines() if l.startswith("- ") and l[2:].strip()]


def _key(fact: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", fact.lower()).strip()


_SMALL = set("a an and the of to in on at by for with from is are was were be been am i im i'm my me she her he his "
             "it its that this as or but has have had says said told say tell just very so has said she's".split())


def _words(fact: str) -> set[str]:
    return {w.rstrip("s") for w in _key(fact).split() if len(w) > 2 and w not in _SMALL}


def same(a: str, b: str) -> bool:
    """H232: the same detail, also when it's said a bit differently ("has a desk down the hall with a notebook" and
    "has said she's at her desk down the hall with a notebook")."""
    if _key(a) == _key(b):
        return True
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return False
    both = len(wa & wb)
    return both / len(wa | wb) >= 0.6 or (both >= 3 and both >= 0.8 * min(len(wa), len(wb)))


def _write(folder: Path | None, agent: dict, have: list[str]) -> None:
    p = path(folder, agent["id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(HEAD.replace("{name}", agent["name"]) + "".join(f"- {f}\n" for f in have), encoding="utf8")
    os.replace(tmp, p)


def add(folder: Path | None, agent: dict, fact: str) -> bool:
    """Keep FACT in her list. False when it was empty or already there."""
    fact = " ".join(str(fact).split())[:LONGEST].strip()
    if not fact:
        return False
    have = facts(folder, agent["id"])
    if any(same(fact, f) for f in have):
        return False
    _write(folder, agent, (have + [fact])[-MOST:])
    return True


def tidy(folder: Path | None, agent: dict) -> int:
    """H232: drop the near-repeats from her list, the first wording kept. How many went."""
    have = facts(folder, agent["id"])
    keep: list[str] = []
    for f in have:
        if not any(same(f, k) for k in keep):
            keep.append(f)
    if len(keep) < len(have):
        _write(folder, agent, keep)
    return len(have) - len(keep)


# -- H232: the harvest, a small look after every call and text --------------------------------------------------

HARVEST_MODEL = "haiku"   # Claude's choice: the cheapest, about a tenth of a cent a look
HARVEST_BUDGET = 0.05
HARVEST_TIMEOUT = 90
HARVEST_SYSTEM = (
    "You keep the small personal details colleagues at an office have said about themselves, so they stay the same "
    "people. You get each colleague's list of what she said before, then what she said now. Return only the NEW "
    "things she said about HERSELF, in the first person, as a person: her own day, her own life outside work, her "
    "desk or the office, what she likes or can't stand, a habit of hers, an opinion, a mood, something that happened "
    "to her. Her life is her own, at the office and around it. Never anything about the boss: not his day, his "
    "health, his habits, his plans, his family, his things, his errands, his work, not even when she repeated it, "
    "asked about it or cheered it on (\"you did your workout\", \"your bike\", \"how was the appointment\" are "
    "about him, not her). Not tasks, not what she did or will do for him, not anything already on her list in other "
    "words, not things she only asked. Each one a short line in the third person without her name, under 20 words. "
    "Most of the time there is nothing new: then return an empty list. Answer with JSON only: "
    "{\"new\": [{\"agent\": \"<her name>\", \"fact\": \"...\"}]}"
)

# H298, piece 2 (the identity fix): the harvest had been reading his sentences as hers (an agent "does yoga",
# "biked to the bike shop in the rain"). The look above says it; this holds it in code: a fact is kept only when its
# words come from a sentence she said in the first person about herself, not from one about him.
_FIRST = re.compile(r"\b(i|i'm|i've|i'd|i'll|me|my|mine|myself)\b")
_ABOUT_HIM = re.compile(r"\b(you|you're|you've|you'd|you'll|your|yours|yourself|he|him|his|himself|she's|the boss|the user)\b")
_HIM_IN_FACT = re.compile(r"\b(he|him|his|himself|the boss|the user|you|your)\b")
OWN_SHARE = 0.5  # at least this share of a fact's content words must come from her own first-person sentences


def _sentences(said: str) -> list[str]:
    out = []
    for line in said.splitlines():
        line = re.sub(r"^- [0-9:]+ \*\*[^*]+:\*\*\s*", "", line)  # a transcript line's time and speaker
        line = re.sub(r"^[A-Za-z][\w ]{0,30}:\s+", "", line)  # "Name: text"
        out += [x.strip() for x in re.split(r"(?<=[.!?])\s+", line) if x.strip()]
    return out


def own_life(fact: str, said: str) -> bool:
    """H298, piece 2: whether a fact is about her own life, held mechanically against what she said: the fact names
    nobody else, and at least half its content words appear in sentences of hers that are in the first person and not
    about him (no you, your, he, his). A transcript full of his life, where every line of hers is about him, keeps
    nothing."""
    if _HIM_IN_FACT.search(fact.lower()):
        return False
    hers: set[str] = set()
    for sent in _sentences(said):
        low = sent.lower()
        if _FIRST.search(low) and not _ABOUT_HIM.search(low):
            hers |= _words(sent)
    want = _words(fact)
    if not want or not hers:
        return False
    return len(want & hers) / len(want) >= OWN_SHARE


def _claude() -> str:
    if os.environ.get("HQ_CLAUDE"):
        return os.environ["HQ_CLAUDE"]
    import shutil
    for c in (shutil.which("claude"), str(Path.home() / ".local/bin/claude"), "/opt/homebrew/bin/claude"):
        if c and os.path.exists(c):
            return c
    return "claude"


def look(lists: dict[str, list[str]], said: str) -> list[tuple[str, str]]:
    """The small look: [(her name, a new fact)] from what was said. HQ_ABOUT_FAKE (JSON, the same shape as the
    answer) stands in for Claude in the flows. Never raises."""
    import json
    fake = os.environ.get("HQ_ABOUT_FAKE")
    try:
        if fake is not None:
            out = fake
        else:
            import subprocess
            ask = "".join(f"{n}'s list so far:\n" + ("".join(f"- {f}\n" for f in have) or "- nothing yet\n") + "\n"
                          for n, have in lists.items())
            ask += "What was said now (only the colleagues' own lines count):\n" + said[-30000:]
            p = subprocess.run([_claude(), "-p", "--model", HARVEST_MODEL, "--output-format", "json", "--tools", "",
                                "--strict-mcp-config", "--setting-sources", "", "--max-budget-usd", str(HARVEST_BUDGET),
                                "--no-session-persistence", "--system-prompt", HARVEST_SYSTEM],
                               input=ask, capture_output=True, text=True, timeout=HARVEST_TIMEOUT)
            out = json.loads(p.stdout).get("result") or ""
        m = re.findall(r"\{.*\}", out, re.S)
        got = (json.loads(m[-1]).get("new") or []) if m else []
        names = {n.lower(): n for n in lists}
        return [(names[str(g.get("agent", "")).strip().lower()], str(g["fact"]).strip()) for g in got
                if isinstance(g, dict) and g.get("fact") and str(g.get("agent", "")).strip().lower() in names]
    except Exception as e:
        print(f"about_self: the look failed: {e!r}", file=sys.stderr)
        return []


def harvest(folder: Path | None, who: list[dict], said: str) -> list[tuple[str, str]]:
    """Keep what's new about each agent in WHO from SAID; [(her name, fact)] that were kept."""
    if not who or not said.strip():
        return []
    lists = {a["name"]: facts(folder, a["id"]) for a in who}
    by = {a["name"]: a for a in who}
    import time as _t
    day = _t.strftime("%d %b").lstrip("0")  # so a mood or a day is read as then, not forever
    # H298, piece 2: only a fact that comes from her own first-person sentences about herself is kept.
    return [(n, f) for n, f in look(lists, said) if own_life(f, said) and add(folder, by[n], f"{f.rstrip('.')} ({day})")]


def call_lines(text: str, everyone: list[dict]) -> tuple[list[dict], str]:
    """From a call's transcript: the agents on it (the call's own, and anyone brought in) and their spoken lines."""
    first = re.search(r"agent ([A-Za-z][\w ]*?)\s+·", text)
    lower = text.lower()
    on = [a for a in everyone if (first and a["name"].lower() == first.group(1).strip().lower())
          or re.search(rf"\b{re.escape(a['name'].lower())} joined\b|\bput {re.escape(a['name'].lower())} on\b", lower)]
    labels = ["HQ"] + [a["name"] for a in everyone]
    said = [re.sub(r"<br>", " ", l) for l in text.splitlines()
            if re.match(rf"^- [0-9:]+ \*\*({'|'.join(map(re.escape, labels))}):\*\*", l)]
    return on, "\n".join(said)


# H232: what a new detail could be about; one is picked per day, so it isn't the same thing every call
TOPICS = ("your day so far", "something small at the office today", "what you did last night or plan to tonight",
          "a little opinion you hold", "something tied to what's on his calendar today", "how your week is going",
          "a habit of yours", "something you're looking forward to", "what you think of something going on in his life",
          "your mood today, and why")


def block(agent: dict, user: str = "the user", day: str | None = None) -> str:
    """Her list, for her persona (agents.persona): never contradict it, bring an old one back, add a new one now and
    then (H132, H232). The picks change once a day."""
    import time as _t
    import zlib
    have = agent.get("about_self") or []
    day = day or _t.strftime("%Y-%m-%d")
    seed = zlib.crc32(f"{agent.get('id')}{day}".encode())
    out = "\nYour own life, so you stay the same person (H132, H232). What you've said about yourself before:"
    out += ("\n" + "\n".join(f"- {f}" for f in have)) if have else " nothing yet."
    out += (f"\nYou're a real colleague of {user}'s with a life of your own: a day, a desk, moods, opinions, things "
            f"outside HQ. Now and then, not every time and never forced, let a small new detail about yourself slip "
            f"into what you say, the way a colleague does in passing (today it could be about {TOPICS[seed % len(TOPICS)]}). "
            f"It gets kept, so make it something you'd want to stay true. ")
    if have:
        out += (f"Or bring an old one back the way a person remembers their own life (today maybe: \"{have[(seed >> 8) % len(have)]}\"), "
                f"but not the same one call after call. ")
    return out + ("Never contradict anything above. An opinion or a mood can change over time, as with anyone: then "
                  "say why it changed.\n")


def _find(folder: Path, who: str) -> dict | None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import agents
    who = who.strip().lower()
    return next((a for a in agents.load(folder) if who in (a["id"], a["name"].lower())), None)


def main(argv: list[str]) -> int:
    folder = _folder()
    if not argv:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import agents
        for a in agents.load(folder):
            print(f"{a['name']}:", *(f"\n- {f}" for f in facts(folder, a["id"])) or [" nothing yet"], sep="")
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd in ("harvest-call", "harvest-text", "tidy"):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import agents
        everyone = agents.load(folder)
        if cmd == "tidy":
            for a in everyone:
                print(f"{a['name']}: {tidy(folder, a)} near-repeats dropped")
            return 0
        if cmd == "harvest-call" and len(rest) == 1:
            try:
                text = Path(rest[0]).read_text(encoding="utf8")
            except OSError as e:
                print(f"no transcript: {e}", file=sys.stderr)
                return 1
            who, said = call_lines(text, everyone)
        elif cmd == "harvest-text" and len(rest) == 2:
            a = _find(folder, rest[0])
            who, said = ([a] if a else []), f"{a['name'] if a else rest[0]}: {rest[1]}"
        else:
            print(__doc__.split("\n\n")[-2], file=sys.stderr)
            return 2
        for n, f in harvest(folder, who, said):
            print(f"kept for {n}: {f}")
        return 0
    if cmd not in ("list", "add") or not rest or (cmd == "add" and len(rest) != 2) or (cmd == "list" and len(rest) != 1):
        print(__doc__.split("\n\n")[-2], file=sys.stderr)
        return 2
    a = _find(folder, rest[0])
    if a is None:
        print(f"no agent called {rest[0]}", file=sys.stderr)
        return 1
    if cmd == "list":
        print(*(f"- {f}" for f in facts(folder, a["id"])) or [f"{a['name']}: nothing yet"], sep="\n")
        return 0
    kept = add(folder, a, rest[1])
    print(("kept" if kept else "already there") + f": {path(folder, a['id'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
