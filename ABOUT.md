# About HQ: the big picture

This file is for Claude, to search and explain. When someone asks *"What is this app? How does it work? What's coming?"*, the answers are here. Explain it plainly, like a person, and always say that **HQ is still in development**: the version is in `VERSION` (0.4.5 as of this writing), built and used daily by one person first, now shared with friends. Things change, and some parts are rough.

What it helps with and how to get it running, for a newcomer: [README.md](README.md). The install in technical detail: [INSTALL.md](INSTALL.md). The details of each part are in the build notes in `CLAUDE.md` and in the code.

## What HQ is

HQ is your own headquarters, running on your own computer. The idea: you talk to Claude like you'd call an assistant, and it doesn't just answer, it does the work. It knows your notes, your plans and what matters to you, because they're all in your workspace. It checks your mail every hour and tells you what needs you. You can agree on a piece of work on a call, hang up, and the computer does it by itself while you're out, and the status page on your phone shows how far it is.

The name: it's the place where your agents work (see [Coming next](#coming-next)). Everyone who installs it gets their own HQ.

Two halves:

- **HQ, the app.** The same code for everyone, public on GitHub. The call line, the routine, the watchdog, the status page, the happy flows.
- **Your workspace.** Your own files, in `workspace/` at the top of HQ. Never uploaded with HQ; updating HQ never touches it. You can back it up as your own private git repo. HQ ships a blank one in `template/`, where every file says "put your own things here".

## How it works

### The call

You open the call page (in the browser, or as an icon on your phone's home screen) and talk. Everything runs on your computer:

- **Ears:** knows when you start and stop talking, and stops talking itself when you cut in (Silero VAD and Pipecat's smart-turn model).
- **Hearing:** your voice into text (Whisper large-v3-turbo, local).
- **Brain:** Claude Code, on your own Claude plan, working in your workspace with your rules and your connectors. Only the thinking goes to Anthropic, the same as any Claude chat.
- **Voice:** the reply spoken sentence by sentence while Claude is still thinking (Kokoro, local, nine voices; by default Bella for Donna and Heart for Pepper).
- **Phone line:** your phone reaches your computer privately through Tailscale, with nothing open to the internet.

On the call page: hold to talk (or talk freely), a chat that shows what you both said, a text box to type instead of talking, a Cancel button when you said something you didn't mean, a mute switch for her voice, and the status page one tap away.

**Who you call: the agents.** Since 0.2 you pick an agent, each with her own name, face, personality and speciality:

- **Donna:** Sonnet, with the basics loaded (your rules, your to-do list, the mail list, the last notes). Quick and dry, a bit cheeky, knows what you need before you finish. For your agenda, your list, mail and quick orders. (This was Quick.) She picks up with "Hey you. What do you need?"
- **Pepper:** Opus, with everything loaded, your vision too. Warm, calm and unhurried, talks it through with you like a real phone call. For planning, sparring, thinking things through. (This was Deep.) She picks up with "Hey, <your name>. What's on your mind?"
- **Moneypenny** (coming soon, Fable): few words, cool, a little mysterious, all business. For the big jobs behind the scenes. "<Your name>. Go ahead." Until then she can be brought into a three-way or four-way call, on Opus.

Each one talks like her own person, not like an AI: her own greetings and her own way of pushing back, and no talking while she thinks (a soft thinking sound instead). These characters are HQ's defaults; Settings on the call page shows each agent's character under her voice, marked HQ's default or your own. You can change any of it for your own HQ (see below), and `python3 app/agents.py` prints each agent's character as it is now.

Each agent's headshot is a drawn placeholder until you put a picture in your workspace (`HQ/agents/donna.jpg`, `pepper.jpg`; pictures stay in your workspace, never in HQ). You can change an agent or add your own in `HQ/agents/agents.json` (see `app/agents.py`): a name, a character, a personality, how she pushes back, her greetings, a speciality, a model, and how much of your workspace she loads (`quick` or `deep`).

**And Free on top of any agent:**

- **Free:** plain Claude. No connectors, none of your files, no notes, nothing saved, only the web. For testing, and for showing HQ to other people without showing your life.

**New to HQ?** The question mark next to Settings opens the get-started tutorial: short pieces that walk over the real screen with a highlight and a caption, on made-up demo content, and a demo call with Donna or Pepper (both on Opus, no tools, nothing saved) to ask anything about HQ.

After a call, the transcript is saved and the call's notes go into your log, in your own words, then committed (Free calls are never saved).

**Things that need your yes** (a calendar appointment with other people in it, anything in your mail) are checked with you in one sentence first. Your own calendar she just changes: adding, moving, deleting, and what it was is kept in the call's transcript so it can be put back. **Mail is never sent**: drafts at the most.

### The workspace and its files

Your workspace is a folder of plain text (Markdown) files that Claude reads at the start of every chat and every call: your rules for how Claude talks to you, who you are and what matters to you (`me.md`), your north star (`vision.md`), where you stand now, everything to do in your own priority lists, the log of every conversation, and the mail list. `where-things-go.md` says where each kind of update goes, so nothing gets written down in five places. A life-coach skill helps you plan your days from your north star.

### The to-do list, the Eisenhower way

The heart of HQ. Everything you have to do lives in one list in your workspace (`challenges.md`), in your own priority lists: what you promised other people, then the four squares of the Eisenhower matrix (important or not, urgent or not), with important but not urgent first, because that's where the needle movers are; then what you decided to let go, what's done (never deleted), a wishlist and groceries. Keeping a list like that is a lot of admin; in HQ you just talk. Something comes up on a call or in Donna's chat, and it's sorted into the right list in your words; something's done or let go, and it moves, with a line in the list's log so you can look back. The hourly mail check says when a mail is about something already on your list, and a new mail only goes on it after your yes.

In the app, the To-do button shows it as the matrix: each square with how many and the first few, what's promised to other people and very important mail above it, the other lists under it. Tap a square for its list, an item for everything about it and your own words on it. Tick it off, move it, let it go or add one by hand (Undo puts the last change back), or call about it. A new install starts with the lists empty, ready for yours.

### Donna's texts, the calendar, notes, weather

- **Texts with Donna:** her own text line. She texts reminders at the time you asked, check-ins and a heads-up when something needs you; you text back and she does it.
- **The calendar:** your Google Calendar inside HQ, today and the days ahead, with a note of your own on any appointment. Plan it on a call.
- **Quick notes:** write a thought down in the app; the next call reads them.
- **Past calls:** every call kept as text, to read back or continue where you left off.
- **Weather:** at a glance, with a rain alert where Donna texts you before a shower and follows it.
- **Life coaching:** a few sessions with Pepper build your long-term vision, from three to five years out down to your ideal week (the map, `workflows/map/`), and HQ supports you with it every day. You give your vision its own name.

**What HQ helps you with:** every feature is a switch in Settings (the calendar, the to-do list, texts, the weather, the mail check, notes, the team's work, Life coaching). Off takes its button away, and calls don't bring it up unless asked.

### The routine and the job queue

A small helper runs every minute, without Claude, so it costs nothing while waiting. It looks at the job queue on your roadmap (`workspace/HQ/roadmap.md`). A job is work you agreed on a call ("build this", "sort that out"). When nothing is running, it starts the highest job on the list in a Terminal window, as a normal Claude chat, minimized so it doesn't take over your screen. One job at a time; the rest wait their turn. From a call you can add jobs, move them up or down, stop one, or switch the whole thing off.

It watches your Claude usage: it stops at the line you set for the 5-hour and the weekly limits, and starts again when there's room. If a job goes quiet (no internet, say), it types "continue" into its window, three times at the most, then marks it as stuck.

### The hourly mail check

Every hour, hidden, Claude reads your new mail (only what's newer than last time), keeps what might need you, and writes it on your mail list. What's very important (money with a date, a deadline soon, health care, the government, a person waiting for your answer, a security warning) goes on top, and you hear it at the start of every chat and call until you say it's resolved. It only reads mail and changes the mail list.

### The watchdog

Every five minutes, separate from everything else, it checks the helper is alive and starts it again if it isn't. The helper in turn brings back the call line, catches up a missed mail check, and retries a failed one. Everything that goes down, why, what was done and when it came back goes in the incident log on the status page.

### The status page

One page, live, on the computer and on the phone: what's being built right now and its step, the job queue, the roadmap, your Claude usage against its stop lines, every routine's state with a graph over the last hours, the incident log, and the laptop itself (temperature, battery, CPU, memory, disk, network). It reads only your roadmap file, so whatever writes the roadmap (a call, a job) shows up within seconds.

### The Mac app

HQ.app puts it in one window: the watchdog on top, drawn as a small dog whose mood follows the status page's light (wagging when all is well, sniffing when something waits, barking when something stopped, asleep when the status page itself is down, running while it turns things on), and below it the status page or the call page, the same pages as in the browser and on the phone. **Turn everything on** starts what's off; it never stops what runs. The routines keep running in the background when the app is closed.

On the phone it looks the same: the status page's address with `/hq` behind it, added to the home screen, gives the same dog, the same light, Status and Call, and Turn everything on.

### Versions and updates

HQ knows its version and looks a few times a day whether a newer one is out. When there is one, a small bar shows what's new with an **Update** button; one tap saves anything you changed on a backup branch, moves HQ to the new version, restarts what needs it, and leaves your Claude a note on what changed. Your workspace and your own builds in `local/` are never touched, and nothing of yours is ever sent anywhere. The small grey version number (on the call page, the status page and in the Mac app) opens the changelog: what was added and changed in each version. Fixes get a patch number (0.2.1), bigger features the next minor (0.3).

### The happy flows

HQ's tests: over a hundred checks of the main things that must work when all goes well (the call starts, the greeting plays, a question gets an answer, cutting in stops the voice, the transcript is saved, the queue works, the status page reads the roadmap, the template stays blank...). They run before and after every change, on their own port, without touching the live call.

## What it runs on

**HQ runs on a Mac with an Apple chip and on a Linux server.** On a Mac everything works. On a Linux server everything except the laptop parts (battery, temperature, the lid switch): the routine and the watchdog are systemd timers there, jobs and the mail check run in tmux, and speech recognition runs on the CPU. **Two HQs** (say a laptop and a server) can pair as main and backup: the main runs the team and the mail check, the backup takes calls and hands changes to the main, the workspace stays the same on both through Syncthing, and the backup takes over by itself when the main is gone for five minutes. **Windows** has no ready version: Claude builds the Mac-only parts itself, only in the `local/` folder, which updates never touch; INSTALL.md has a table of what to build with what, and the names HQ looks for there.

**Mail is built for Gmail and the calendar for Google Calendar**, through the Claude connectors. With another provider, Claude first researches whether it has a connector or an MCP server, and otherwise builds an alternative (IMAP, CalDAV, an `.ics` link).

Everything runs on your own Claude plan (Pro or Max), through Claude Code; no API key, no extra costs beyond the plan.

## Coming next

HQ is still being built. The order isn't fixed and can change. What came so far, in short (the full list per version is in [CHANGELOG.md](CHANGELOG.md)):

- **0.1:** the call (then Quick, Deep and Free), the workspace and its template, the status page, the hourly mail check, the job queue, the watchdog, the usage check, the happy flows and the installer.
- **0.2:** the agents. Pepper and Donna replace Quick and Deep, each with her own name, face, personality and speciality. That's why it's called HQ: it's where they all work.
- **0.3 and 0.4:** updates with one tap, HQ on a Linux server, two HQs as main and backup, the characters, Donna's texts, the calendar, weather, quick notes, past calls; then the to-do list in the app, What HQ helps you with, Life coaching, the tutorial and the demo call, the look (Modern 3).

Next, ideas rather than promises:

- **Moneypenny:** a third agent, for the big jobs behind the scenes (shown as coming soon).
- **Shared best practices:** ways of working that keep a build stable, written so your own HQ understands them and suggests them itself.
- **More agents**, each with what it needs to know loaded, and a ready Windows version.

## In one paragraph

HQ is a personal assistant you call and talk to, running on your own Mac or server, built on Claude Code and your own Claude plan. It knows your notes and your goals, reads your mail and calendar, writes down what you agree, and can do work by itself from a job list while you're away, with a live status page on your phone. Your own files stay in your own workspace and never go into HQ's repo. It's still in development: Mac and Linux, Gmail and Google Calendar first, with a Mac desktop app, its phone version, and two named agents, Donna and Pepper.
