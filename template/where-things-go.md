# Where things go

Every kind of update has one place. Put it there, and only there. If something doesn't fit anywhere below, ask, then add a line here.

## Loaded or not

A file with an @ in front of its name in CLAUDE.md is loaded in full at the start of every session. Files without the @ are only read when needed, with the Read tool (never `cat` in Bash).

## The map

| What | Where | Loaded |
|---|---|---|
| How Claude talks and behaves; your corrections ("rule") | `rules.md` | @ + every message |
| Workspace setup: what's loaded, start of session, privacy, git, email, dictation slips | `CLAUDE.md` | always |
| Where things go, and the maintenance check | `where-things-go.md` (this file) | @ |
| Who you are, what's important, what HQ should manage | `me.md` | @ |
| How the coaching works | `.claude/skills/life-coach/SKILL.md` | when coaching |
| Hard blocks (no sending email) and the rules hook | `.claude/settings.json` | always |
| The north star | `vision.md` | @ |
| Where you stand now: work, health, money, home, people, appointments and their context | `current-situation.md` | @ |
| Everything to do: tasks, priorities, deadlines, status, done, let go, shopping wishlist, groceries | `challenges.md` | @ |
| What happened in each conversation: your words, commitments, follow-ups | `coaching/log.md` | @ |
| Log entries older than two weeks | `coaching/log-archive.md` | on demand |
| Done and let-go items, and challenge log lines, older than two weeks | `challenges-archive.md` | on demand |
| New mail from the hourly mail check, waiting for your yes | `inbox.md` | @ |
| Weekly reviews | `reviews/YYYY-Www.md` | on demand |
| The status block, the job queue, the roadmap of what HQ builds next | `HQ/roadmap.md` | on demand (the status page reads it) |
| Call transcripts (full, one file per call) | `HQ/calls/YYYY-MM-DD-HHMM.md` | on demand |
| Appointments and time blocks | the calendar: the visual of the files above, never the only place | when asked or when planning |
| Something new (a goal, a plan, a project) | a new `.md` file or folder here, plus a line in this map | decide per file |

## Common updates

- A fact about your life changes → `current-situation.md`. If it creates something to do → also a row in `challenges.md`.
- Something to do comes up (from you, email or calendar) → `challenges.md`, details in your words.
- Something gets done or let go → moved in `challenges.md` (with date and time), one line in the log.
- An appointment → the calendar, and its context in `current-situation.md`.
- You correct how Claude talks or works → `rules.md` if it's about behaviour, the skill if it's about coaching, CLAUDE.md if it's about the setup. Plus one line in the log.
- Your vision changes → only `vision.md` and `me.md`, only when you say so, in your words.

## Two-week cycle

So the loaded files stay small. At the start of every session (and in every maintenance check):

- Coaching log: entries older than 14 days move to `coaching/log-archive.md`, newest first. Open commitments stay, whatever their age.
- Challenges: done and let-go rows older than 14 days move to `challenges-archive.md`, with their details. Log lines older than 14 days move there too. Open items never move.
- Moving only: never shorten, rewrite or delete.

## Maintenance check

When you say "maintenance check" or "cleanup":

1. Read every file in the map.
2. Check each piece of information is in its right place: nothing duplicated, contradicting, misplaced or stale.
3. Fix it: move things where they belong, keep your wording, never delete history.
4. If the map itself is missing something, add it here.
5. One line in the log, and tell you in plain words what moved and why.
