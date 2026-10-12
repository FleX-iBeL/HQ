# Changelog

What was added and changed in each version of HQ, newest first. The small grey version number on the call page, the status page and in the Mac app opens this. Fixes get a patch number (0.2.1), bigger features the next minor (0.3). "Coming next" is what's built but not in a version yet; at a release it gets the version's number and date.

## Coming next

### New
- Moneypenny, coming soon: a third agent on Fable, shown as a small locked card under Donna and Pepper. She can't be picked or called yet. A workspace can unlock her in `agents/agents.json` with `"coming_soon": false`.
- HQ's routine and watchdog run on a Linux server too, as systemd timers that start by themselves after a restart (`routine/install-linux.sh`). The call line has a Linux start and stop (`app/start-linux.sh`, `app/stop-linux.sh`). On a Mac nothing changes.

### Changed
- Each agent has her own character on calls and sounds like a person, not an AI: Donna quick and dry, a bit cheeky; Pepper warm, calm and direct; Moneypenny few words, cool, all business. Each greets you her own way and pushes back her own way, and nobody talks while she thinks (the thinking sound stays). These are HQ's defaults: Settings shows each one's character under her voice, `python3 app/agents.py` prints them, and you change them for yourself in `agents/agents.json`.
- All three usage stop lines (the 5-hour line, the weekly all-models line and the weekly Fable line) move every minute: each is the share of its window gone by, from 10% (5-hour) or 20% (weekly) up to 100% at its reset. Each has its own switch on the status page (and from a call, on your ask) to keep it at a fixed number of your choice instead. A job let past the line still only skips the 5-hour line; the weekly lines always count.
- Each agent starts with her own voice: Donna with Bella, Pepper with Heart. Still yours to change in Settings; a voice you already picked stays.
- On a call, HQ itself can be read without asking, the same as your workspace: its files, its logs (like the hourly mail check's) and the status page's data. Changing anything in HQ still asks you first.

### Fixed
- A Quick call kept the log's open commitments only when they stood above the newest entries; now wherever they stand.
- The Mac app's window moves like a normal Mac app: drag it from anywhere in the top bar that isn't a button. A double click there does what your Mac's title bar setting says.

## 0.3 · 11 October 2026

### New
- Updates: HQ looks a few times a day whether a newer version is out. A small bar shows what's new with an Update button; your changes are saved on a backup branch first, and your workspace and your own builds in local/ are never touched.
- The version number, small and grey, on the call page, the status page and in the Mac app; a tap shows this changelog. When there's nothing newer, it says you're on the latest version.
- local/: one place for your own builds (for example the Windows parts). Never uploaded, never touched by an update, and HQ looks there first.
- Every past call: a button above the voice button opens the list of saved calls, and each one read only.
- Continue an earlier call: open it in Past calls and tap Continue. The new call knows what was said, and she greets you with "let's continue from where we left off".
- How long the jobs should take: an estimate per job and for the whole list, learning from how long jobs really took.
- The space bar in the Mac app: a tap mutes, holding it is push to talk, letting go sends.
- Pushing HQ goes through its own key, and only after the privacy check.
- After a crash, the job carries on: when the Mac went down while a job ran, HQ puts that job back first in line, with a note to pick up from what it had already done, and says it was a crash. Once only, so a job that keeps crashing can't loop.

### Changed
- The old project name is gone: everything is called HQ.
- Donna (Sonnet) does the day-to-day, Pepper (Opus) the sparring; the app opens on Call, with a voice per agent.
- HQ's icon: the house on the cliff, drawn flat like the dog.
- The status page in the app can be made bigger or smaller (Cmd +, Cmd −, Cmd 0).
- A call saves the usage it gets back, for the status page.
- The template: clearer to fill in, and the vision guides Claude while it's still empty.

### Fixed
- Her voice off also silences the thinking tick, the talk sound and the click.
- The call screen: nothing covered with the chat open, nothing cut off on short screens.
- Calls from inside the Mac app connect.

## 0.2 · 10 October 2026

### New
- The agents: Pepper and Donna replace Quick and Deep, each with a name, a personality, a speciality and a headshot.
- The Mac desktop app: the status page and calling in one window, with the watchdog drawn as a dog whose mood follows the status.
- The phone version: the same strip, status and call, on the status page's address with /hq behind it.
- The scheduler: plan work for a day and a time; the job list always goes first.

## 0.1 · 10 October 2026

### New
- The call: talk with Claude by voice from the phone or the browser, with push to talk, cutting in, typing, a cancel button and a mute button. Every call is saved as a transcript, with notes afterwards.
- The status page: the roadmap's live status, the jobs, the routines and their history, the incident log, the usage, and the laptop's temperature, battery and more.
- The routine: jobs agreed on a call run one at a time on the computer, an hourly mail check, a usage check, a watchdog that brings things back, and waking up a job that went quiet.
- The installer, the blank workspace template, the readme for your Claude, and the privacy check before sharing.
