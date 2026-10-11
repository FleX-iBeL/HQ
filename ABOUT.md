# About HQ: the big picture

This file is for Claude, to search and explain. When someone asks *"What is this app? How does it work? What's coming?"*, the answers are here. Explain it plainly, like a person, and always say that **HQ is still in development**: version 0.1, built and used daily by one person first, now shared with friends. Things change, and some parts are rough.

How to install it is in [README.md](README.md). The details of each part are in the build notes in `CLAUDE.md` and in the code.

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
- **Voice:** the reply spoken sentence by sentence while Claude is still thinking (Kokoro, local, nine voices, Heart by default).
- **Phone line:** your phone reaches your computer privately through Tailscale, with nothing open to the internet.

On the call page: hold to talk (or talk freely), a chat that shows what you both said, a text box to type instead of talking, a Cancel button when you said something you didn't mean, a mute switch for her voice, and the status page one tap away.

**Who you call: the agents.** Since 0.2 you pick an agent, each with her own name, face, personality and speciality:

- **Donna:** Sonnet, with the basics loaded (your rules, your to-do list, the mail list, the last notes). Calm, quick, organised. For your agenda, your list, mail and quick orders. (This was Quick.)
- **Pepper:** Opus, with everything loaded, your vision too. Warm, sharp, sees the whole picture. For planning, sparring, thinking things through. (This was Deep.)

Each agent's headshot is a drawn placeholder until you put a picture in your workspace (`HQ/agents/donna.jpg`, `pepper.jpg`; pictures stay in your workspace, never in HQ). You can change an agent or add your own in `HQ/agents/agents.json` (see `app/agents.py`): a name, a personality, a speciality, a model, and how much of your workspace she loads (`quick` or `deep`).

**And Free on top of any agent:**

- **Free:** plain Claude. No connectors, none of your files, no notes, nothing saved, only the web. For testing, and for showing HQ to other people without showing your life.

After a call, the transcript is saved and the call's notes go into your log, in your own words, then committed (Free calls are never saved).

**Things that need your yes** (changing your calendar, anything in your mail) are checked with you in one sentence first. **Mail is never sent**: drafts at the most.

### The workspace and its files

Your workspace is a folder of plain text (Markdown) files that Claude reads at the start of every chat and every call: your rules for how Claude talks to you, who you are and what matters to you (`me.md`), your north star (`vision.md`), where you stand now, everything to do in your own priority lists, the log of every conversation, and the mail list. `where-things-go.md` says where each kind of update goes, so nothing gets written down in five places. A life-coach skill helps you plan your days from your north star.

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

HQ's tests: over forty checks of the main things that must work when all goes well (the call starts, the greeting plays, a question gets an answer, cutting in stops the voice, the transcript is saved, the queue works, the status page reads the roadmap, the template stays blank...). They run before and after every change, on their own port, without touching the live call.

## What it runs on

**HQ 0.1 is built for Claude on a Mac with an Apple chip.** The start at login, the routine, the watchdog, the Terminal windows, the lid-closed switch, the laptop readings and the speech recognition (MLX) are Mac-only. On Windows, Claude builds those parts itself, only in the `local/` folder, which updates never touch; the readme has a table of what to build with what, and the names HQ looks for there.

**Mail is built for Gmail and the calendar for Google Calendar**, through the Claude connectors. With another provider, Claude first researches whether it has a connector or an MCP server, and otherwise builds an alternative (IMAP, CalDAV, an `.ics` link).

Everything runs on your own Claude plan (Pro or Max), through Claude Code; no API key, no extra costs beyond the plan.

## Coming next

HQ is still being built. The order isn't fixed and can change:

- **0.1:** the call (Quick, Deep, Free), the workspace and its template, the status page, the hourly mail check, the job queue, the watchdog, the usage check, the happy flows, and an installer with a live checklist page, so you can see exactly where an install broke. Since then: the scheduler, the Mac desktop app, and the phone version that looks like it.
- **0.2 (now):** the agents. Pepper and Donna replace Quick and Deep, each with her own name, face, personality and speciality. That's why it's called HQ: it's where they all work, like building a small company inside the app.
- **More agents:** one for creative work, one for life coaching (maybe Moneypenny), each with what it needs to know loaded.

Further out, ideas rather than plans: the status page reachable when the laptop is offline, and a simple backup assistant on a server for when the laptop is closed.

## In one paragraph

HQ is a personal assistant you call and talk to, running on your own Mac, built on Claude Code and your own Claude plan. It knows your notes and your goals, reads your mail and calendar, writes down what you agree, and can do work by itself from a job list while you're away, with a live status page on your phone. Your own files stay in your own workspace and never go into HQ's repo. It's still in development: version 0.1, Mac-first, Gmail and Google Calendar first, with a Mac desktop app and its phone version, and named agents coming next.
