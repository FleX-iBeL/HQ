# Changelog

What was added and changed in each version of HQ, newest first. The small grey version number on the call page, the status page and in the Mac app opens this. Fixes get a patch number (0.2.1), bigger features the next minor (0.3). "Coming next" is what's built but not in a version yet; at a release it gets the version's number and date.

## Coming next

### Added
- With two HQs (the laptop and a server), you see at a glance which one is main: a pill next to the name on the status page, in the Mac app, the phone version and on the call page. Green "Main" on the main one; grey "Backup · VPS is main" (or "Laptop is main") on the other. An HQ on its own shows nothing new (H118).

### Changed
- On a call the chat's top line says only who you're calling with: her name, both names on a three-way call, all of them with more (H115).
- The quick notes are just text now: the paper to doodle on is gone, and the field you type a note in grows with what you type, over more lines, like the chat's (H117).

### Fixed
- Changing the mic and sound during a call. Picking the AirPods (or any output the computer already plays on) as the Sound no longer makes her voice much quieter. On the iPhone, Safari and the Mac app the old mic is let go first, so the new one can take over. Where a device won't switch, the call screen says so plainly: on the iPhone, iOS picks the mic and sound itself during a call (Control Center); with the AirPods' own mic on, they play in quieter call mode; a mic that sends no sound is named (F24).

## 0.4.2 · 13 October 2026

### New
- "Bring in Pepper" always makes a three-way call and "give me Pepper" (or "connect me through", "put her on") always hands over, without asking first. She only asks which one you mean when you put it in other words (H122).
- Change the microphone and the sound in the middle of a call, without hanging up. A round mic button on the call screen, right above the chat bubble, opens just those two choices; a new mic takes over at once and the call goes on (muted stays muted), and her voice moves to the new sound right away where the browser allows it (H112).
- A job the usage limit stopped carries on where it left off: on the same computer it picks its own chat back up, with everything it remembers; when it can't (the other computer takes it, or the chat is gone), a fresh chat is told it was stopped and at about which step, and looks at what the first run left before carrying on (H113).
- When the usage limit holds the jobs, the estimates stay: every waiting job and planned item still shows how long it takes and when it should be done, as if the usage allowed it, with a note next to it in soft red that it will be later because of the usage limit. The totals too, on the status page and in the lists on calls (H109).
- A priority tag for planned work. Tag an item when you plan it, or later, and when its time comes it doesn't wait for the job list: it goes first in line, ahead of the waiting jobs, and starts as soon as the running job is done (a running job is never stopped for it). Without the tag the job list goes first, as before. The tag shows under Scheduled on the status page and in the scheduler's list on calls (H99).
- When a newer version of HQ is out, the watchdog dog in the Mac app and the phone version sits wagging in front of its empty food bowl, looks up at you now and then, and barks Update! in green, the way it barks Woof! in red. Something that's off or asleep still comes first (H98).
- Donna texts you on HQ's own direct line: a chat with only her on the phone's HQ page (the speech bubble at the bottom left), with her texts on the lock screen once you allow notifications there (iPhone with iOS 16.4 or later, from the home-screen icon). No Telegram, no paid service. She texts like a person when the job list is finished, when a very important mail comes in, when something stays down (and when it's back), and when the backup takes over from the main. Text her back and she answers and acts as on a call, with the same limits (H80).
- Ask for another agent by name on a call. "Give me Pepper" and she puts her on: the call ends the way a hang-up does (notes and all) and Pepper picks up a new call right away, knowing what was said. Or ask for a three-way call: both stay in the same conversation, the one you name (or whose thing it is) answers, in her own voice and model, and the screen is split in both colours. Not sure which you mean, and she asks (H79).
- The planned work has a total too, like the job list: the Scheduled heading on the status page and the scheduler's list on calls say how long all planned items take together and when the last one should be done, after the job list (H107).
- In Settings, choose which microphone the call listens with (every one the device has, like AirPods, the phone's own or a podcast mic), and, where the browser allows it, where her voice plays. Remembered on each device. An experiment: on an iPhone the sound can't be chosen by a page.
- A notes button on the call page, right above Past calls, always there: your own quick notes to go through with your agent whenever you like, each cleared once it's done (or all at once), and a small paper space under them to write or doodle on with a finger or the mouse. Your agent can read both on a call.
- With a second HQ (a laptop and a server), a heartbeat for each under Routines on both status pages: whether this computer is up and online, and whether the other one answers, every minute, apart from which one is main. Two missed answers in a row turn it red and go in the incident log.
- On a call the screen takes a soft tint of who you're talking to: purple for Donna, red for Pepper, yellow for Moneypenny. In the chat your lines are green and hers are in her own colour, also in past calls.
- Your agents look things up on the web straight away, without asking you first.
- Your agents say times the way the clock shows them: 9:30 is "nine thirty", 10:45 "ten forty five", never "half" or "quarter". In the chat they show as "5 30 in the afternoon" or "10 in the evening": easy to read, and no colon for the voice to pause at.
- More goodbyes she hangs up on: "okay, thanks, appreciate you" and "cheers" end the call by themselves, the same as "bye".
- Your agents put things in your calendar, move them and delete them without asking first. An appointment with other people in it, or an invitation, still gets checked with you. Before moving or deleting one she looks at it, and what it was is kept in the call's transcript, so it can always be put back.
- Planned work under Scheduled shows an estimate too: how long it should take, and when it should be done, counting the jobs and the planned work before it. A call can say what kind of work it is when planning it, and that goes with it when it becomes a job.
- A new job keeps a little room under the usage limits before it starts: it waits when the usage is within 5% of the 5-hour line or within 1% of a weekly line, so a job doesn't start just to be stopped (H114).
- Planned work whose time passed while the job list, the usage or a switched-off routine held it back still runs, one after another, earliest first; none is skipped. The scheduler's list on calls says how many more are waiting (H111).

### Fixed
- With a laptop and a server, the laptop waking up from sleep no longer takes over as main: only minutes it was awake the whole time count as the server being gone. Before taking over it asks the server once more, also through the sync, and a server that gave way stays the backup through a missed look, so there are never two mains at once (F23).
- A call left quiet no longer drops after five minutes. Nothing spoken or heard for five minutes (typing and her thinking didn't count) used to end the call; now it stays on until someone hangs up or the connection itself goes.
- Making one HQ main from a call switches right away when nothing runs on the other one, instead of a minute or two later; with a job running there, it switches the moment that job is done. The reason shown no longer says the other one took over when it was simply main before.

## 0.4.1 · 12 October 2026

### New
- Which HQ it is, small under the name: VPS on a server, Local · macOS on a laptop. On the status page, the call page and in the Mac app's strip.

### Changed
- Moneypenny's locked card now just says "Clearance pending."
- On a server, the status page leaves out the Laptop section and the laptop's temperature and battery lines, since a server has no laptop to read.

### Fixed
- The server's call page has the night icon too, also when you add it to your phone's home screen (no old icon, no white border).

## 0.4 · 12 October 2026

### New
- Moneypenny, coming soon: a third agent on Fable, shown as a small locked card under Donna and Pepper. She can't be picked or called yet. A workspace can unlock her in `agents/agents.json` with `"coming_soon": false`.
- HQ's routine and watchdog run on a Linux server too, as systemd timers that start by themselves after a restart (`routine/install-linux.sh`). The call line has a Linux start and stop (`app/start-linux.sh`, `app/stop-linux.sh`). On a Mac nothing changes.
- A hidden Yes on a call: with nothing typed, hold the greyed-out Send for a moment, slide up onto Yes and let go; it sends Yes, also as the answer to a question waiting for your yes.
- She hangs up herself: say a clear goodbye ("that's it, see you later") and she says goodbye and ends the call, the same as tapping Hang up. Anything you say right after keeps the call going.
- HQ on a server: the whole HQ runs on a Linux server as well as on a Mac, installed the same way (the installer has a Linux path; jobs and the mail check run in tmux, listening runs on the CPU). Two HQs can pair as main and backup: only the main runs the jobs and the mail check, the backup takes over by itself after five minutes without the main and hands back when it returns, and a call on the backup sends its jobs to the main.
- The two-way sync: with two HQs, the workspace and Claude's memory stay the same on both within seconds (Syncthing). When both change the same file at once, both versions are kept and a job merges them.
- The server's HQ has its own icon: HQ's house at night, with the stars and the moon.

### Changed
- Each agent has her own character on calls and sounds like a person, not an AI: Donna quick and dry, a bit cheeky; Pepper warm, calm and direct; Moneypenny few words, cool, all business. Each greets you her own way and pushes back her own way, and nobody talks while she thinks (the thinking sound stays). These are HQ's defaults: Settings shows each one's character under her voice, `python3 app/agents.py` prints them, and you change them for yourself in `agents/agents.json`.
- All three usage stop lines (the 5-hour line, the weekly all-models line and the weekly Fable line) move every minute: each is the share of its window gone by, from 10% (5-hour) or 20% (weekly) up to 100% at its reset. Each has its own switch on the status page (and from a call, on your ask) to keep it at a fixed number of your choice instead. A job let past the line still only skips the 5-hour line; the weekly lines always count.
- Each agent starts with her own voice: Donna with Bella, Pepper with Heart. Still yours to change in Settings; a voice you already picked stays.
- On a call, HQ itself can be read without asking, the same as your workspace: its files, its logs (like the hourly mail check's) and the status page's data. Changing anything in HQ still asks you first.
- Job estimates know what kind of job it is: a call gives each job its kind when it adds it, so builds are no longer counted as general.
- The status page opens the same way every time: Routines, Laptop and Recent activity closed; the jobs, Scheduled and what's not finished open.
- Updates only come from released versions: work goes on a working branch first, and the version your update bar sees only moves on a release.

### Fixed
- A Quick call kept the log's open commitments only when they stood above the newest entries; now wherever they stand.
- The Mac app's window moves like a normal Mac app: drag it from anywhere in the top bar that isn't a button. A double click there does what your Mac's title bar setting says.
- The call screen on a phone no longer scrolls into empty space during a call, and keeps its old layout.
- The happy flows never touch your real job list, also not on a server.

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
