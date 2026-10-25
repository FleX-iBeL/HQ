# Installing HQ: the details

This page is for Claude, and for anyone technical helping with an install. The friendly overview, what HQ is and what it does, is in [README.md](README.md); the big picture of how it works in [ABOUT.md](ABOUT.md). This page is for HQ as it is now (the version in `VERSION`, what changed in [CHANGELOG.md](CHANGELOG.md)).

## The first install

If the person you're helping says something like *"read me and install everything and check everything and make sure it works"*, this section is for you. Work through it top to bottom. After each step, check it worked before going on. When something fails, read the log it names, fix it, and say in plain words what you fixed. The person may not be technical: talk to them like a person, short sentences, no jargon, and only ask them for what only they can do (a password, clicking Allow, signing in).

**Which computer?** A Mac with an Apple chip runs everything. A Linux server runs everything except the laptop readings and the lid switch (see [On a Linux server](#on-a-linux-server)). Windows has no ready version yet: Claude builds the Mac-only parts for it (see [Windows](#mac-only-parts-and-what-to-do-on-windows)). Two HQs, say a laptop and a server, can work together as main and backup (see [Two HQs](#two-hqs-main-and-backup)).

**Tell them first (on a Mac):** the setup will ask for their password, and macOS will ask a few times whether something may have access (the Documents folder, Terminal, the microphone). If they want those features, they should allow it. It's asked once; after that it runs by itself.

### The installer does it for you

```sh
python3 install/install.py
```

It runs two rounds and ticks every step off on a live checklist, http://localhost:4749 while it runs and afterwards on the status page at http://localhost:4748/install (also on the phone's status address), so the person, or whoever helps them, can see exactly where it stopped and why. Round one sets everything up: what's needed, the workspace from the template (an existing workspace is never touched), the Python environment, the voice, and every password and macOS permission once (the helper's Documents access, Terminal windows, the watchdog, the lid switch, the status page, the call line). It tells them up front about the password and Allow. Round two is the installer's happy flow: everything again, and nothing may ask any more; a check that would need a password or a click fails instead of waiting.

- `--test-only`: only round two, read only. Run it any time to check an install.
- `--skip lidsleep,tailscale,flows,helper`: leave optional parts out.
- `--yes`: no Enter after the heads-up (when you run it for them). The lid switch needs their password typed in Terminal; in a run without a terminal it says how, and goes on.
- Its output: `scratch/install/install.log`; the checklist's data: `scratch/install/checklist.json`.

When a step fails, its line says why and what to do; fix it and run the installer again (finished steps just say they're already there). The steps below are what it does, for when you need to do one by hand or build it on Windows.

### 0. What you need

| Need | Why | Check |
|---|---|---|
| A Mac with an Apple chip (M1 or newer), or a Linux server with systemd | On a Mac, speech recognition runs on the Apple chip (MLX); on Linux on the CPU (faster-whisper). On Windows, or an Intel Mac, see [Mac-only parts](#mac-only-parts-and-what-to-do-on-windows) | `uname -m` says `arm64` |
| Claude Code, signed in with a Claude plan (Pro or Max) | The call's brain, the jobs and the mail check are Claude Code, on the person's own plan; no API key | `claude --version`, then `claude` and `/status` |
| Homebrew | Installs the rest | `brew --version` |
| Python 3.12 and `uv` | The call line | `brew install python@3.12 uv` |
| Node.js 20 or newer | The status page | `brew install node` |
| git | Updates, and the workspace's own backup | `git --version` |
| Tailscale (optional) | Calling from the phone, privately, without opening anything to the internet | `brew install --cask tailscale`, then sign in |
| About 4 GB free | The Python environment (~1.6 GB), the voice (~330 MB), speech recognition (~1.6 GB, downloaded on the first call) | `df -h ~` |

Some scripts call Claude Code and Node at Homebrew's place (`/opt/homebrew/bin/claude`, `/opt/homebrew/bin/node`). If `which claude` says something else, either link it there or set `HQ_CLAUDE_CLI` for the call line and change `CLAUDE` and `NODE` at the top of `routine/tick.py`.

### 1. The workspace: the person's own files

HQ is the app; **`workspace/` is theirs.** HQ's repo never uploads it, and updating HQ never touches it.

- Fresh install (no `workspace/` yet): `cp -R template workspace`.
- **If `workspace/` already exists, never overwrite it.** It holds their notes.
- Make it its own git repo: `git -C workspace init`, then a first commit. HQ commits and pushes their notes after calls and jobs; a private GitHub repo as `origin` is the backup. Until there is a remote, the push step fails while the commit is kept; set one up with them, or leave it.
- Then ask them to fill in `workspace/me.md` (their name, what's important, what HQ should manage), or offer to do it together: they talk, you write it down in their words.
- The call reads a few lines of `me.md` itself: **Name** (how HQ greets them and what their lines in a transcript are called), **Names to hear** (names speech recognition should get right), **Never change** (workspace folders a call never changes or commits), **Private words** (for the privacy check below) and the section **On calls** (their language, how they like times said). All optional; nothing about a person is in HQ's own code.

### 2. The call line's Python environment

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python --only-binary :all: tokenizers faster-whisper==1.2.1
uv pip install --python .venv/bin/python -r app/requirements.txt
```

The first line of `app/requirements.txt` explains the faster-whisper exception. Check: `.venv/bin/python -c "import pipecat, mlx_whisper, kokoro_onnx, claude_agent_sdk; print('ok')"`.

### 3. The voice

Kokoro, local and free. Download `kokoro-v1.0.onnx` and `voices-v1.0.bin` from the `model-files-v1.0` release of [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx/releases) into `models/`. All nine voices are in that one file (about 28 MB); Heart (`af_heart`) is the default; Donna starts with Bella (`af_bella`), Pepper with Heart, both changeable in Settings. Speech recognition (Whisper large-v3-turbo, MLX) downloads itself on the first call.

### 4. Mail and calendar: the connectors

HQ reads mail through the **Gmail** connector and the calendar through the **Google Calendar** connector of the person's Claude account (claude.ai → Settings → Connectors). Ask them to connect both, then check in Claude Code that the tools show up (`mcp__claude_ai_Gmail__…`, `mcp__claude_ai_Google_Calendar__…`). HQ never sends mail: sending, replying and forwarding are blocked in `workspace/.claude/settings.json`; drafts at the most.

**Not Gmail or Google Calendar?** Then HQ isn't built for it yet. Find out whether their provider has a Claude connector or an MCP server, and if it has, adapt the mail check (`routine/mail-check.md`, `workspace/inbox.md`) and the tool names in `app/policy.py` and `app/config.py`. If nothing exists, research and build an alternative with them (IMAP for mail, CalDAV or an `.ics` link for a calendar), and write down what you built in `ABOUT.md`.

### 5. The call line

```sh
app/start.sh                     # with Tailscale: the phone line too
HQ_NO_PHONE=1 app/start.sh   # without Tailscale: this computer only
```

Then open http://127.0.0.1:7860 in the browser, allow the microphone, pick Donna, and say hello. Log: `scratch/server.log`. Stop: `app/stop.sh`.

On the phone (Tailscale on, on both): the address `start.sh` prints, `https://<this-mac>.<tailnet>.ts.net:8443`, in Safari, then Share → Add to Home Screen; it gets HQ's own icon, the house (on the Mac too, with Safari's File → Add to Dock).

Who to call, the agents: **Donna** (Opus, the basics loaded, fast; was Quick), **Pepper** (Opus, everything loaded, for planning and thinking; was Deep) and **Moneypenny** (Opus, everything loaded, for building HQ with the team). Their headshots are placeholders until the user puts pictures in `workspace/HQ/agents/` (`pepper.jpg`, `donna.jpg`); agents can be changed or added there in `agents.json` (see `app/agents.py`). Each agent has her own character on calls (H76): Donna quick and dry, a bit cheeky; Pepper warm, calm and direct; Moneypenny cool and composed, dry wit, few words, head of development with the definition of ready and done; each with her own greetings and her own way of pushing back. These are HQ's defaults. Show the user what each default is (`python3 app/agents.py` prints them, marked HQ's default or changed; Settings on the call page shows each one's character under her voice), and tell them they can change any of it for themselves in `workspace/HQ/agents/agents.json`: `character` (one line), `personality`, `pushback`, `greetings` (per part of the day, `morning`, `afternoon`, `evening`, `night`, or one list; `{s}` is " Name", `{n}` ", Name", `{N}` "Name. ", from their me.md) and `continue_greetings`. Only what they change goes in; the rest stays HQ's default. The call line needs a restart to pick it up (`app/stop.sh` then `app/start.sh`). On top of any agent, **Free**: plain Claude with no connectors, none of their files, no notes and nothing saved, only the web. Free is for testing and showing HQ to others.

### 6. The status page

```sh
node status/server.mjs
```

http://localhost:4748, this computer only. It reads `workspace/HQ/roadmap.md` every few seconds; that file is the only place the status is written. On the phone: `status/phone.sh` puts it on `:8444` in the tailnet, with its own home-screen icon.

### 6b. The Mac app (optional)

`desktop/build.sh --install` builds **HQ.app** with `swiftc` (the Command Line Tools are enough) and puts it in `~/Applications`. One window: the watchdog dog on top (its mood follows the status page's light; click it for every routine), the status page or the call page below, and **Turn everything on**, which starts the status page, the helper, the watchdog and the call line when they're off and never stops anything. The routines keep running when the app is closed. The first time, macOS asks once for Documents access and, on the first call, for the microphone. Check: `~/Applications/HQ.app/Contents/MacOS/HQ --check`.

The same on the phone, nothing to build: the status page's phone address with `/hq` behind it (`https://<your-mac>.<tailnet>.ts.net:8444/hq`), in Safari Share, Add to Home Screen. It's the same strip, served by the status server with `desktop/phone.js` and `desktop/phone.css`; the call page below it is the call line's own address. Turn everything on works from there too; it only starts what's off.

### 7. The routine, the start at login and the watchdog (Mac)

These keep HQ running without anyone watching. All three ask macOS for permission once.

- **The helper app** (the routine, every minute, and the start at login): `sh routine/build-app.sh` builds *HQ Routine* into `~/Applications`. Then copy the LaunchAgent (the `.plist` file in `app/`) to `~/Library/LaunchAgents/` and `launchctl load` it there. macOS asks whether it may reach the Documents folder: **Allow**. When it starts a job or the mail check, macOS may ask whether it may control Terminal: **Allow**. Log: `scratch/routine/routine.log`.
- **The watchdog** (every 5 minutes, brings the helper back): `sh routine/install-watchdog.sh`.
- **Lid closed, keep working** (optional): `sudo sh routine/install-lidsleep.sh` once, with their password typed by them. After that a call can switch it on and off. Never type or store their password yourself.

Paths inside that `.plist` and `routine/routine.applescript` must point at this HQ folder; fix them if they don't, and rebuild.

### 8. Check everything: the happy flows

The happy flows are HQ's tests: the main things that must work when all goes well.

```sh
.venv/bin/python app/happy_flows.py --quick   # the ones without Claude, about a minute
.venv/bin/python app/happy_flows.py           # all of them, about five minutes, a few Claude turns
.venv/bin/python app/happy_flows.py --only 3,5
```

They run on their own port and never touch the live call line. **All must pass.** A failed flow says why; fix it and run it again. A flow that needs something they chose not to set up (Tailscale, the lid switch) may fail for that reason: say so plainly instead of hiding it.

Then the real test: a call from the phone or the browser, a question about today's calendar, and hang up. The transcript lands in `workspace/HQ/calls/`, and the notes in `workspace/coaching/log.md`.

### When it breaks

- The status page, under Routines: every routine's state, and the incident log (what went down, when, why, what was done).
- Logs: `scratch/server.log` (the call line), `scratch/routine/routine.log` (the helper), `scratch/routine/mail.log` (the mail check).
- `.venv/bin/python app/happy_flows.py --quick` narrows it down.
- How each part works: [ABOUT.md](ABOUT.md), and the build notes in `CLAUDE.md`.

---

## On a Linux server

On Linux the helper app and the LaunchAgents are systemd user units instead: `sh routine/install-linux.sh` puts in `hq-routine.timer` (the routine, every minute), `hq-watchdog.timer` (every 5 minutes, starts the routine again when it's gone, ends a run that hangs), both in UTC so the clocks going back doesn't stop them for an hour (F52) and `hq-start.service` (the call line, through `app/start-linux.sh`, when the server starts), switches lingering on, and starts them. They start by themselves after a restart. HQ's own memory is `~/.local/state/hq` there. `--dry` shows the units, `--remove` takes them out. Tailscale's serve settings belong to root on Linux, so HQ calls it with `sudo -n` (no password; `HQ_TS_SUDO=0` if the user is Tailscale's operator). Battery, temperature, the laptop stats and the lid switch stay Mac only (the status page leaves them out on a server). Jobs and the hourly mail check run in tmux sessions there instead of Terminal windows (`tmux attach -t hq-job-<N>` to watch one); without tmux, your own `local/open-window` stands in. Happy flow 61 checks all of it on a Linux machine: run it there, or from a Mac with `HQ_TEST_LINUX=<ssh host>`. Since H56.5 the installer does all of this on Linux too: `python3 install/install.py --yes --no-page` on the server installs nothing with sudo (what's missing is named with the line to install it), makes the Python environment without MLX (faster-whisper listens there), puts in the units, checks a tmux session, and checks that Claude trusts the workspace (run `claude` once in it and answer yes, since nobody answers that question for a job). Its test round runs the happy flows that hold on Linux.

A server needs: Ubuntu or another Linux with systemd, about 4 GB of memory or more (speech recognition on the CPU is the biggest user), the same 4 GB of disk as a Mac, Python 3.12 with `uv`, Node.js 20+, git, tmux, Claude Code signed in, and Tailscale for the phone. On the phone the server's call page is `https://<server>.<tailnet>.ts.net:8443` and its status page `:8444`, the same as a Mac's.

## Two HQs: main and backup

Two HQs, for example a laptop and a server, can work as one: the **main** runs the jobs, the hourly mail check and the scheduler, and commits; the **backup** takes calls and shows the status page, and hands anything that changes the job list, the to-do list, the roadmap or the notes to the main (so only one of them ever writes those files). When the main can't be reached for five minutes, the backup takes over by itself, and hands back when the main returns and its own work is done. With no second HQ set up, an HQ is simply main and never looks for another; nothing below is needed.

Setting it up, once, on both computers (both need Tailscale, and Syncthing for the sync):

1. **Install HQ on both**, the normal way above. Both run the same code: when you help build HQ itself, both stay on the same branch.
2. **Pair them** (`routine/role.py`): on each, `python3 routine/role.py setup https://<the-other>.<tailnet>.ts.net:8444 --main <name of the one that should be main>`. `python3 routine/role.py` says which one is main, in plain words; `main here` or `main other` switches it (a call may do that too); `alone` forgets the other.
3. **Share the workspace** (`routine/sync.py`, on top of Syncthing): on each, `python3 routine/sync.py setup <the other's Syncthing device ID or name>`. The workspace and Claude's memory of the person then stay the same on both within seconds. Video, audio and git's own folder don't go over. When both change the same file at once, both versions are kept and the main queues a small job that merges them without dropping anything.
4. **Check it**: the status page shows a pill, green **Main** on the main and grey **Backup · <name> is main** on the other, and a Two-way sync line under Routines.

Only the main commits the workspace and pushes it to its private GitHub repo. The details are in the docstrings of `routine/role.py` and `routine/sync.py`.

## Mac-only parts, and what to do on Windows

**HQ is built and tested on a Mac with an Apple chip and on a Linux server.** Windows has no ready version yet. On Windows, **Claude builds the missing parts itself** for that computer, following how the Mac version works (and the Linux version, which is closer for some of them):

| Part | On the Mac | On Windows, build it with |
|---|---|---|
| Speech recognition | Whisper through MLX, on the Apple chip | Pipecat's `WhisperSTTService` (faster-whisper) on the CPU or an NVIDIA GPU, in `app/pipeline.py` |
| Start at login | A LaunchAgent opens the helper app | Task Scheduler, "At log on" |
| The routine (every minute) | The helper app runs `routine/tick.py` | Task Scheduler, every minute, `python routine\tick.py` |
| The watchdog | A LaunchAgent every 5 minutes (`routine/watchdog.py`) | Task Scheduler, every 5 minutes |
| Job and mail check windows | Terminal windows, minimized, closed when done (AppleScript) | Windows Terminal or PowerShell windows, started minimized |
| Keeping awake during a call | `caffeinate` | `powercfg` or `SetThreadExecutionState` |
| Lid closed, keep working | `pmset disablesleep`, allowed once through `sudoers` | `powercfg` (lid close action), set once as administrator |
| Temperature, battery, laptop stats | IOKit, `pmset`, `vm_stat` (`routine/*.py`, `*.m`) | WMI or `psutil` |
| Paths and shells | zsh scripts, Homebrew paths | PowerShell, the Windows paths |
| The desktop app | `desktop/HQ.swift` (Swift, WebKit), built by `desktop/build.sh` | A WebView2 window around the same strip (`desktop/shell.html`) and `desktop/hq_control.py`, or just the browser |

Not tried yet, so say so if you go this way: running HQ inside WSL (Ubuntu on Windows) as if it were a Linux server, with the installer's Linux path; the call page then opens in the Windows browser on `http://127.0.0.1:7860`.

What works the same everywhere: the call page, the voice (Kokoro), Claude Code, the connectors, Tailscale, the status page (Node), the queue and the workspace. Keep the Mac files as they are and build the Windows ones **only in `local/`** (see *Your own parts* below), so an update never erases them; HQ looks there first.

---

## Sharing changes: the privacy check

HQ is public, so nothing of anyone's own may go in it: their notes stay in `workspace/`. Before pushing a change to HQ, run

```sh
python3 app/privacy.py --history
```

It looks through HQ's files and its whole git history for the person's name and **Private words** (from `workspace/me.md`), home folder paths, Tailscale names and addresses, mail addresses, and keys or tokens. Happy flow 44 runs the same check. Paths in the shipped files are written as `/Users/you/HQ`; the installer and `routine/build-app.sh` put the real path in.

## Updating HQ

**The easy way:** when a newer version is out, the call page, the status page and the Mac app show a small bar with what's new and an **Update** button. HQ looks for one on this repo a few times a day (read only, no login; when the computer is offline it just tries again later). When there's nothing newer, the small grey version number says you're on the latest version. Tap the version number any time to see the changelog: what was added and changed in each version, newest first.

What **Update** does (`routine/update.py`, which you can also run yourself: `python3 routine/update.py start`):

1. It waits while a call is on or a job runs, and says so; it starts by itself when they've ended.
2. Anything changed in HQ's own files (and any commits of your own) is saved first on a backup branch, `hq-backup/<date>-before-<version>-changes` (or `-commits`). Nothing is ever sent anywhere. To get the changes back: `git stash apply <that branch>`.
3. It fetches that version from this repo and moves HQ to it. `workspace/`, `local/`, `scratch/` and `.status/` are never touched.
4. It restarts what needs it: the call line (if it ran), the status page (if its server changed), the Mac app (if it changed and is installed: reopen it afterwards), the watchdog (if it changed), and the Python packages if the requirements changed.
5. It leaves a note for Claude in `updates/<version>.md`: what's new, what was kept, what it restarted, and what to check or rebuild. **Claude: when there's a note in `updates/` that isn't in `updates/done/`, read it, do what it says, tell the person in a sentence or two, then move it into `updates/done/`.**

On a computer that isn't a Mac, tapping Update first explains that their own parts are kept safe and that Claude gets instructions to patch things up locally afterwards.

By hand, for a Claude helping out: don't `git pull` or check out a tag and restart things one by one; that skips the backup, the restarts and the note. Run the same path the button runs: `python3 routine/update.py check --force` (it should say `"available": true`), then `python3 routine/update.py start`, and follow `python3 routine/update.py status` until its `run` says `done`; then read the note in `updates/`. If the check says `"offline": true`, its `why` says what failed.

### Your own parts: local/

Whatever Claude builds for this one computer (the Windows parts above, or anything else of the person's own) goes **only in `local/`**, at the top of HQ. That folder is ignored by HQ's repo: it is never uploaded, and an update never touches it. Where HQ has a part that differs per computer, it looks in `local/` first, by name, with any of the endings `.sh`, `.py`, `.ps1`, `.cmd`, `.bat` (or none):

| Name in local/ | Stands in for | Called with |
|---|---|---|
| `open-window` | the Terminal window a job or the mail check runs in (`routine/tick.py`) | the path of the script to run |
| `start-call-line` | `app/start.sh`, when the call line is off ("Turn everything on") | nothing |
| `restart-call-line` | `app/stop.sh` then `app/start.sh`, after an update | nothing |
| `start-status-page` | `node status/server.mjs --quiet` | nothing |
| `restart-status-page` | restarting the status page after an update | nothing |
| `start-helper` | opening the helper app that runs the routine every minute | nothing |
| `start-at-login` | the installer's helper app and its LaunchAgent | nothing |
| `start-watchdog` | loading or waking the watchdog's LaunchAgent | nothing |
| `install-watchdog` | `routine/install-watchdog.sh` (installer and updates) | nothing |

Something with no name here (the speech recognition, the laptop readings): change HQ's file as little as possible, and keep a copy of the change in `local/` with a line on what it is, so it can be put back after an update (the update saves the change on a backup branch too, and its note says so).

### Their own extensions: the workspace's HQ/extensions

What the person builds on top of HQ (a connector for another mail app, a routine of their own, their own kind of text, extra rules for calls) is an **extension**, in the workspace's `HQ/extensions/`, one folder each, never in HQ's own files. HQ reads them at fixed points (the call and text rules, the mail check, its routine every minute), an update never touches them, and after every update HQ checks on that computer whether anything might clash, and says so in plain words with two buttons: talk it through, or send it to their team. **EXTENSIONS.md** says how to build one, and how to move what was already built into HQ's files into an extension.

### Versions

Versions are git tags on this repo: `v0.4`, `v0.4.5`, and so on. **Fixes get a patch number (0.4.5); bigger features the next minor (0.5).** An update only ever moves to a released version; the work in between lives on the `dev` branch, and a nightly test line, never on what everyone's update bar sees. HQ reads its own version from the newest tag in its history (`git describe`), else (no history, no tags, or only older ones) from the `VERSION` file.

Releasing one (the maintainer): in `CHANGELOG.md`, rename **Coming next** to the version and date (`## 0.4.5 · 18 October 2026`), put the same number in `VERSION` and in the version line near the top of `README.md`, commit, tag it with a short message (`git tag -a v0.4.5 -m "HQ 0.4.5"`), and push main and the tag with `python3 routine/push.py --release`, which runs the privacy check first. Everyone's HQ sees it within a few hours.
