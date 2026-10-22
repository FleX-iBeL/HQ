# HQ

**Your own headquarters: a small team you call, that doesn't just answer but does the work.**

You open HQ on your phone or laptop and call Donna or Pepper. You talk like you would on the phone, and you can cut in any time. They know your notes, your to-do list and your calendar, they write down what you agree, and bigger pieces of work they hand to "the team": your computer does it by itself while you get on with your day. A live status page shows how far it is.

Everything runs on your own computer, with your own Claude plan. Your own files stay yours.

HQ is at version **0.4.10** (what's new in each version: [CHANGELOG.md](CHANGELOG.md)). It's still in development: built and used every day by one person first, now shared with friends. Things change, and some parts are rough.

---

## What HQ helps you with

**Call your team.** Pick who you call. **Donna** is quick and dry: your day, your list, your mail, quick orders. **Pepper** takes her time: planning, sparring, thinking something through. Each has her own voice and character, and you can change both. Hold to talk or just talk, read everything back in the chat, or type when you can't talk (on a train, in a library). Bring the other one into the call when you need both.

**Your to-do list, the Eisenhower way.** One list for everything, in four squares: important or not, urgent or not, with important but not urgent first, because that's where the things that move your life forward are. You don't keep it, you just say it: on a call or in a text it lands in the right square, in your own words. In the app you can tick things off, move them, let them go, or start a call about one.

**Texts with Donna.** She texts you reminders at the time you asked, check-ins, and a heads-up when something needs you. Text her back like any chat app and she does what you ask.

**Your calendar.** Your Google Calendar inside HQ: today and the days ahead. Ask on a call to plan your week, move something or block time, and it's done. Each appointment can have a quick note of your own.

**The mail check.** Every hour HQ reads your new mail and keeps only what might need you. Very important things, like a bill with a date or someone waiting for your answer, you hear at the start of every call until you say it's sorted. HQ never sends mail: drafts at the most, you send them yourself.

**Quick notes.** A thought you don't want to lose? Write it down in HQ. The next call reads your notes, so you can say "let's go through my notes".

**Every call, kept.** Every call is saved as text. Read one back, or tap Continue this call and she picks up where you left off.

**The team works while you're away.** Agree a bigger piece of work on a call (build something, sort something out, research something), say "give it to the team", and hang up. Your computer does it by itself, one piece at a time, and Donna texts you when it's done. Plan work for later, like tonight at ten, so it doesn't get in your way during the day.

**The status page.** What the team is doing right now, what's waiting and what's planned, your Claude usage against the limits you set (the team stops before it eats your whole plan, and carries on when there's room), and whether every part of HQ is running.

**Weather and rain alerts.** The weather where you are, at a glance. Turn on the rain alert and Donna texts you before a shower comes, and follows it as it moves.

**Life coaching.** A few calm sessions with Pepper build your long-term vision, from three to five years out down to your ideal week, and HQ helps you live towards it every day.

**Turn on only what you want.** Every feature above is a switch in Settings, under What HQ helps you with. Turn off what you don't use: its button goes away and the rest moves up.

**A tutorial and a demo call.** The question mark next to Settings walks you over the real screen, piece by piece, on made-up example content. Or start a demo call and ask Donna or Pepper anything about HQ.

**Free, to show it to others.** Free is plain Claude with only the web: none of your files, nothing saved. Handy to show HQ to someone without showing your life.

**On your phone and your Mac.** HQ works in the browser, as an icon on your phone's home screen, and as a Mac app with a little watchdog that shows at a glance whether everything is running.

**Make it yours.** HQ is built to be expanded. Ask on a call for something new, give it to the team, and they build it into your HQ. Your own builds stay yours: updates never touch them.

---

## What you need

- **A Claude plan, Pro or Max.** HQ runs on Claude Code with your own plan. No API key, no extra costs beyond the plan.
- **A computer that stays on.** A Mac with an Apple chip (M1 or newer) is the easiest: everything works. A Linux server works too. Windows has no ready version yet (see [On Windows](#on-windows) below).
- **About 4 GB of free disk space**, for the voice and the speech recognition. Both run on your own computer.
- **Gmail and Google Calendar**, if you want the mail check and the calendar. Something else? Claude can look for a way to connect it; it's not built in yet.
- **Tailscale (free)**, if you want to call from your phone. It connects your phone to your computer privately, without opening anything to the internet.

---

## Get it running

You don't have to do the setup yourself: Claude does it with you. HQ comes with an installer and step-by-step instructions written for Claude.

### On a Mac

1. **Install Claude Code** and sign in with your Claude plan ([how](https://docs.claude.com/en/docs/claude-code/setup)).
2. **Get HQ.** Open Terminal and type:

   ```sh
   git clone https://github.com/FleX-iBeL/HQ.git
   cd HQ
   claude
   ```

   Use `git clone`, not a ZIP download: that's what lets HQ update itself later.
3. **Ask Claude:** *"read me and install everything and check everything and make sure it works"*.
4. **Allow what it asks.** Your Mac asks for your password and a few times whether something may have access (the Documents folder, Terminal, the microphone). Say yes to what you want to use. It's asked once; after that it runs by itself.
5. **Watch it happen.** A checklist opens in your browser (http://localhost:4749) and ticks off every step, so you can see exactly where it is, and where it stopped if something goes wrong. Claude fixes what it can and tells you in plain words.
6. **Tell HQ who you are.** Claude asks for your name, what's important to you and what HQ should help with. Just talk; it writes it down in your words.
7. **Connect your mail and calendar** (optional): on claude.ai, Settings, Connectors, connect Gmail and Google Calendar.
8. **Make your first call.** Open http://127.0.0.1:7860, allow the microphone, pick Donna and say hello. New to it? Tap the question mark for the tutorial.

The Mac app (optional): ask Claude to build it for you. It puts the call, the status page and Donna's texts in one window.

### On a server

HQ runs on a Linux server too (Ubuntu, with about 4 GB of memory or more). A server is always on, so the team keeps working and the mail keeps getting checked while your laptop is closed. Everything works there except what's about a laptop (the battery, the temperature, the lid).

The steps are the same as on a Mac: install Claude Code, clone HQ, start `claude` in the HQ folder and ask it to install everything. On a server nothing asks for a password; what's missing is named with the line to install it. You reach it from your phone or laptop through Tailscale.

### On your phone

There's nothing to install on the phone itself. HQ runs on your computer (or server), and the phone calls it.

1. Install **Tailscale** on your computer and on your phone, and sign in on both with the same account.
2. Open the address Claude gives you after the install, `https://<your-computer>.<your-tailnet>.ts.net:8443`, in Safari.
3. Tap Share, then **Add to Home Screen**. HQ's icon, the house, lands next to your other apps.

The status page has its own address on the phone (the same, with `:8444`), and `:8444/hq` gives you the same view as the Mac app, watchdog and all.

### Two HQs: main and backup

Want HQ on your laptop and on a server? They can work as one. The **main** does the work: the team, the mail check, the planned jobs. The **backup** takes your calls and shows the status page, and passes anything you agree on to the main. Your files stay the same on both within seconds. If the main goes offline, the backup takes over by itself after five minutes, and hands back when the main returns. You can see which one is main on the status page, and switch it on a call.

Ask Claude to set it up once both are installed. The steps are in [INSTALL.md](INSTALL.md#two-hqs-main-and-backup).

### On Windows

There's no ready Windows version yet. A few parts are built for the Mac (starting at login, the background routine, the watchdog, the speech recognition), and on Windows Claude builds those itself for your computer, in a folder that updates never touch. It's more work and nobody has tested it yet, so expect some back and forth. If you have a choice, a Mac or a small Linux server is the smoother path today. The details for Claude are in [INSTALL.md](INSTALL.md#mac-only-parts-and-what-to-do-on-windows).

---

## Updates

When a new version is out, a small bar shows up on the call page, the status page and the Mac app, with what's new and an **Update** button. One tap:

- waits until you're off a call and the team is between jobs,
- saves anything you changed in HQ itself, just in case,
- moves HQ to the new version and restarts what needs it,
- and leaves your Claude a note on what changed, so it can tell you.

Your own files and your own builds are never touched, and nothing of yours is sent anywhere. HQ looks for updates a few times a day. Tap the small grey version number any time to see what changed in each version.

---

## Your files stay yours

HQ is two halves. **HQ itself** is the same app for everyone, public here on GitHub. **Your workspace** is your own folder of notes: who you are, what matters to you, your to-do list, your calls. It lives in `workspace/` inside HQ, is never uploaded with HQ, and you can back it up as your own private GitHub repo. Before anything goes into HQ's public code, a privacy check looks for anything of yours and stops it.

Only the thinking goes to Anthropic, the same as any Claude chat. The listening and the voice run on your own computer.

---

## When something isn't working

- Look at the status page: under Routines, every part of HQ has a light, and the incident log says what went down, when and why.
- Ask Claude in the HQ folder: *"something isn't working, can you check?"* It knows where the logs are and how to test everything.

---

## More

- [ABOUT.md](ABOUT.md): the big picture. What HQ is, how each part works, and what's coming.
- [INSTALL.md](INSTALL.md): the install step by step, in technical detail, for Claude or anyone technical helping out. Also the Linux server, two HQs, Windows, your own builds in `local/`, and how updates and versions work.
- [CHANGELOG.md](CHANGELOG.md): what changed in each version.

---

**Claude, if you're reading this to install HQ:** the full instructions are in [INSTALL.md](INSTALL.md). Read it top to bottom and follow it.
