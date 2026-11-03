# Keeping HQ running

This is the walkthrough on keeping HQ running: the two computers, restarts, updates and releases, the usage, the doors, the status page, the tests, the privacy check, checkpoints, and what never to do. It is written for Moneypenny first, HQ's head of development. A friend who runs HQ can follow it too.

How to use it:

- Run every command from the HQ folder.
- Looking never needs a yes. Changing something does, and some changes only stand on the owner's own words (section 5).
- Moneypenny delegates and checks. She never edits, commits or pushes HQ's code and never runs a fix herself. When this page says "do", for her it means: give it to the team as an item, or ask the owner. What she does herself is look, decide what's ready, decide the release, and QA.
- She carries the team's findings back. How something technical should be solved is the team's to find: she passes on what they found or proposed, and when they haven't looked yet she says so and gives it to them, with no fix of her own. A change to how she works goes to the team as an item too, so it goes out in a release.
- Moneypenny's start names these sections. Before you act on one, read it: `python3 app/rules.py maintain N` prints section N. `python3 app/rules.py maintain` lists them.

## 1. The two computers

HQ can run on two computers as one, for example a laptop and a server. One is the main, the other the backup. With no second HQ set up, an HQ is simply main and none of this applies.

- The main runs the team's jobs, the hourly mail check and the scheduler, and it commits and pushes the workspace.
- The backup takes calls and shows the status page. A write to a file only the main writes (the planning, the coaching log, the mail list, the to-do list and a few more) goes to the main as a request. The main writes it and the sync brings it back. That way is called the door.
- When the main can't be reached for five minutes, the backup takes over by itself. It only does that when it is online and awake itself. When the main answers again twice in a row, the backup starts nothing new and hands back once its own job is done. HQ is built so there aren't two mains.

Look:

- `python3 routine/role.py` says which one is main, in plain words.
- `python3 routine/sync.py` says how the sync is doing. `python3 routine/sync.py conflicts` lists conflict copies.
- `python3 routine/settle.py` says how many differences are kept from both computers.

Change:

- `python3 routine/role.py main here` (or `other`, or a name) makes one the main. A call may run this on the owner's ask.
- `python3 routine/role.py alone` forgets the other HQ. Pairing (`python3 routine/role.py setup PEER_URL --main NAME`) is never done from a call.

The backend switches. A new HQ starts with all of them on: the briefing, the open line, the team's jobs run in the background (headless), one-way sync, the planning index and the hand-over. An HQ that updates gets the five main ones once, but only when its switches file is still the one HQ wrote; switches the owner set himself stay as they are. `python3 app/backend.py` shows them. A switch changes only on the owner's yes. The script itself has no door that checks his words, so it's his to ask for, never an agent's own pick. `python3 app/backend.py off NAME` turns one off, from the next call, text or job; no restart needed. A bad day is one switch back, not a rollback.

The hand-over and its switch. With one-way sync on, the backup only receives. What it still holds that the main doesn't (its own changes, its conflict copies) goes to the main every minute, but only while the backend switch `handover` is on. The sync line on the status page has a button for it. By hand: `python3 routine/sync.py handover on` or `python3 routine/sync.py handover off`. To see what would go over without sending it: `python3 routine/sync.py handover --dry`. A hand-back waits up to ten minutes for the sync; after that, what's left goes over through the doors.

The kept-from-both list. When both computers had their own version of the same file, the main's version stays in the file, and the other's own words go into `HQ/kept-from-both.md` in the workspace, newest first. Nothing is lost and nothing waits on a merge. Only the main writes that list. The owner reads it and decides what comes back. Never copy something from it into a file by hand; tell the owner it's there.

## 2. Restarting safely

What keeps old code in memory is the call line and the status page (which also serves Donna's texts). The routine, the watchdog, jobs and the mail check start fresh every time.

A restart ends a call that is on, and a part that doesn't come back says nothing by itself. So the order is always:

1. Look first. `python3 routine/jobs.py list` shows what the team runs and what waits. `python3 routine/update.py parts` shows the background parts with their exact pids: write down the pids of the call line and the status page.
2. Donna's warning first. Text the owner a minute before, in plain words: what restarts, for what, and that texts are back within a minute. `.venv/bin/python app/direct_line.py text remind "the call line restarts in a minute for the new release; texts are back within a minute"`. Whoever does the restart sends it.
3. Restart: `python3 routine/update.py restart-all`. It is the update's own restart step, the one an update and the release guard start; it isn't in the script's usage text. It stops each part by its exact pid, holds a running job so it carries on by itself afterwards, and starts each part again. It prints nothing, and a good restart writes nothing either: only a failed hand-off to the new code is written to `scratch/update.log`. So the check in step 4 is what tells you it worked.
4. Check it came back. `python3 routine/update.py parts` again: every pid is new, and `ps -o lstart= -p PID` shows a start time after the restart. A part with no pid, or its old one, didn't come back. Then the status page: every line under Routines green again (section 6).
5. The other computer. Run `python3 routine/push.py --pull` there first, so it runs the same code, then the same steps there.

Doing one part by hand. Stop it, then wait until the call line's old pid is gone before you start it: `app/start.sh` on a Mac and `app/start-linux.sh` on Linux both do nothing while the old line still listens. On a Mac: `app/stop.sh`, wait, then `app/start.sh`. On Linux: `app/stop-linux.sh`, wait, then start it as below. Start it from a shell with no `HQ_*` test settings, because it passes every `HQ_*` setting in the shell on to the live line, and in its own scope, as `update.py` does: `systemd-run --user --scope bash app/start-linux.sh`. It needs bash, not sh. On the laptop, start things from a clean environment (`env -i HOME=$HOME PATH=$PATH USER=$USER ...`), never from inside a Claude chat, whose settings would leak into what it starts. A backend switch never needs a restart (section 1).

Holding the team while you work. `python3 routine/jobs.py pause "WHY"` holds everything: the running job within a minute, no new starts, no reviews. `python3 routine/jobs.py on` ends the pause. `python3 routine/jobs.py off` switches the team off, and also clears a pause. Neither stops the night's run at 2:00. Before `python3 routine/jobs.py on`, read `python3 routine/jobs.py list` and cancel any waiting job whose work is already done: `python3 routine/jobs.py stop N`.

For Moneypenny: a restart is the team's step or the owner's, never part of a build she runs. When a piece of work restarts the call line, the item says so, and the call's notes are written before the call drops.

## 3. Updates and releases

Three lines of work, on GitHub:

- `dev`: the work. The team builds here.
- `nightly`: the night's work, every night. Nobody's update bar sees it.
- `main` with a version tag (`v1.0.0`): a released version. Friends' update bars only look at these tags, so friends only ever get released work.

The night. At 2:00 the night's run tests every quick flow on the main (`python3 routine/nightly.py set` says which ones on this computer). Not green: the team fixes what it found and runs it all again, at most three full runs a night.

The release gate. `python3 routine/release.py status` says what tonight's run found, what changed since, dev against nightly and main, and its suggestion. `python3 routine/release.py main` releases. It refuses when:

- this computer isn't the main, HQ isn't on `dev`, or the changelog, `VERSION` or the README have changes that aren't committed;
- the running job has a note it hasn't read;
- there's no green whole run from today on this commit (or with only the free files changed since: the tests, the changelog, the README, `VERSION`), the night's run is still going, or that run had changes that weren't committed;
- a commit names no item, unless it only touches the free files;
- work whose row doesn't say QA passed (that work and what comes after it stays on dev and nightly; `python3 routine/qa.py hold` shows what would go and what would be held);
- the changelog's Coming next is empty;
- the privacy check finds something.

A fix that landed in the day means no release until a whole run on it: `python3 routine/nightly.py run` on the main, under the lock (section 7). Within 12 hours of a green night the routine started, that command only answers that tonight's run already passed every flow and runs nothing. So after a green night at 2:00, a whole run on a fix from the morning can only start after 14:00. There is no option to force it by hand (its `--routine` is the routine's own mark, not for a person). The night's own run doesn't take the lock, so a hand run near 2:00 can clash with it.

Each commit names its item at the start of its subject. A commit that belongs to an item but doesn't name it can be listed in `COMMITS_FOR` in `routine/qa.py`, keyed by its full id, with the files it changes and the fingerprint of that change; it then waits for that item's QA like any commit naming it. Editing that list is a code change: the team's, as an item, never Moneypenny's. A second run on the same commit does nothing and says so. Only the main computer releases. `--version 1.0.0` names the version instead of the next small one.

Moneypenny decides the release. Inside those gates, when to release is hers. Going past a gate (`--without-qa`, `--past-the-night`) only stands on the owner's own words (section 5). Hesitating is fine: `python3 routine/release.py nightly "WHY"` puts the work on nightly only, and the next night tests it again.

Updating an HQ to a released version. The update bar does it, or by hand: `python3 routine/update.py check --force`, then `python3 routine/update.py start`, then follow `python3 routine/update.py status` until it says done. It saves anything changed in HQ on a backup branch first, restarts every part, and leaves a note in `updates/`. Its git step never touches `workspace/`, `local/`, `scratch/` or `.status/`, but a version's data changes do change the workspace, each with its undo (`python3 routine/datachange.py list` shows which ran here). Never update with a plain `git pull`: that skips the backup, the restarts and the note.

The maker's own two HQs run on `dev`. New work comes in with `python3 routine/push.py --pull` on each, then a restart on each (section 2). The update bar is for released versions.

The way back and forward. `python3 routine/update.py back` puts HQ one version back, on both computers, with the data changes of that version undone first (`routine/datachanges/`). `python3 routine/update.py back --tag vX.Y.Z` names the version. `python3 routine/update.py forward` brings it forward again, with what wasn't committed. HQ refuses to go back to a version that has no way forward, and a release that changes data is refused unless its undo works on a copy. A friend's HQ that ends up on the work line goes back to its released version by itself within a minute.

## 4. The usage lines and the reserve

HQ runs on the owner's own Claude plan. Usage is counted in points: percent of the plan's limits, not money. The owner comes first when it's tight.

The stop lines. There are three: the 5-hour line, the weekly line (all models) and the weekly Fable line. Each one moves (the share of its window that has gone by, recalculated every minute) or is fixed at a number. Nothing of the team or the agents starts above its line. `python3 routine/usageline.py` shows all three and where they stand. `python3 routine/usage-check.py` shows the latest reading. On a plan with no 5-hour limit, HQ goes on the week alone.

The reserve. A number of points (15 unless the owner turned it) is taken off the stop lines for the agents' own runs and the team, so his calls and the small routines always have room. `python3 routine/usageline.py reserve` shows it. The least line keeps the team's line from dropping under 15 points after a reset (`python3 routine/usageline.py least`). The agents' own runs stop five points under the team's line, so they are the first to stop.

The estimates. Every job gets a likely and a latest end, learned from the finished jobs most like it. A job that runs past its latest end is a miss: Moneypenny gets a quiet note on her own line (which job, what kind of work, its range and its real time), and the owner's phone stays quiet. Only a repeat reaches him, through her: more than 1 miss in the last 20 jobs, or two of one kind in a row, at most once a day and at least 12 hours apart, also across a takeover. `python3 routine/misses.py` shows the misses, the last 20 jobs and whether it repeats now. The Friday report holds the week to the same figures. For Moneypenny: a miss is hers to look at; when a kind keeps missing, its fix is an item for the team.

Also held by the program:

- A reading older than 30 minutes starts nothing new.
- Between 8:00 and 22:00 no build starts without the owner's say-so (`python3 routine/jobs.py now N --said "HIS WORDS"`).
- Every job has a box in minutes and turns. Past it, it's boxed and waits for a call. `python3 routine/jobs.py resume N` gives it more, at most twice, never past four times its first estimate. Then the item gets split.

Who changes them. A stop line changes only on the owner's own words on a call or in a chat (`python3 routine/usageline.py weekly fixed 95 --said "HIS WORDS"`), or by his own hand on the status page. The reserve and the least line are never set from a call, a chat or a job: only on the status page or by his own hand in a terminal (`python3 routine/usageline.py reserve 15`).

## 5. The doors

A door is a command that only stands on the owner's own words. It takes `--said "HIS WORDS"`, and the program checks them. They count only when:

- they are his: a line he said or typed, word for word;
- they are from this call or this chat, today (a quick note, an older call or another chat never opens a door);
- they are a yes to that very thing: they name what they open (its label, the feature, the line), or come right after an agent line that names it. A "wait", "not yet" or "later" is no yes. A quote under three words only counts right after such an agent line.

A job can never give itself his say-so. On the backup, his words are checked there and handed to the main with what was checked. A refused try at a door goes on the ledger of mistakes, once.

The doors, and what they open:

- `python3 routine/usageline.py weekly fixed 95 --said "HIS WORDS"`: a usage stop line (section 4).
- `python3 app/features.py on ID --said "HIS WORDS"`: a feature still being built in pieces, before its QA passed. `python3 app/features.py pieces` lists them.
- `python3 routine/jobs.py now N --said "HIS WORDS"`: a build in his day hours.
- `python3 routine/jobs.py add "TEXT" --not-ready --said "HIS WORDS"`: an item to the team without its Ready mark.
- `python3 routine/jobs.py done N --said "HIS WORDS"`: a build closed without its green test record.
- `python3 routine/review.py clear LABEL "HIS WORDS"`: the review's flag off a planning item.
- `python3 routine/release.py main --without-qa --said "HIS WORDS"` and `--past-the-night`: a release past its gates.
- `python3 routine/cycles.py yes AGENT "HIS WORDS" N`: an agent's held change (an event with guests, say).

Never put words in his mouth. If you don't have his line, ask him, plainly, naming the thing. His answer is the line.

## 6. The status page and the incidents

The status page is http://localhost:4748 on the computer itself, and the same address on port 8444 on the phone through Tailscale.

Under Routines every part of HQ has a line, written each time it runs:

- Working: it ran and all is well.
- Running: busy right now, all good.
- Waiting: it waits for something (the usage, its next turn).
- Off: switched off on purpose.
- Not working: it failed, or it is overdue. A line that is late turns red: that part has stopped.
- No data: nothing was read yet.

The light on top is red when something is not working (or the laptop is hot, or the battery low off the charger), yellow when something waits or the laptop is warm, and green when all is working.

The status block. At the top of the planning a block says what the work is doing now: building, testing, releasing, waiting for the owner, done or stopped. It is kept with `python3 status/set-status.py STATE "STEP" "JUST" "NEXT" "TABLE_ROW" "LOGLINE"`, before work starts, at every step and when it's finished. Never edit the block by hand.

The incidents. When a part goes down, the incident log on the status page says when, why, what was done about it and when it was back. A red edge is still down. The watchdog runs every five minutes and brings the routine back when it stopped or hangs. Something that stays down for three minutes gets a text from Donna, and another when it's back. A refused pull or push to GitHub opens the incident "github" until the next one goes through. A repeat of the estimate misses that can't be texted after six tries opens the incident "estimate-misses". What Donna passes on to Moneypenny stands first in her start until its cause is gone. She looks at it and gives the team an item for it.

The score. Each agent's weekly score reads the ledger of mistakes. It says how many calls and texts it read and how many it couldn't, so a call it missed never looks like a call with nothing to correct; one that couldn't be opened is tried again on every pass. What each second look cost is kept in `.status/mistakes-looks.jsonl`.

The logs: `scratch/server.log` (the call line), `scratch/routine/routine.log` (the routine), `scratch/routine/mail.log` (the mail check), `scratch/update.log` (updates and restarts).

## 7. The test wall and the flows

The happy flows are HQ's tests. `.venv/bin/python app/happy_flows.py --quick` runs the ones without Claude turns. `.venv/bin/python app/happy_flows.py --only 241,443` runs just those. Without options it runs all of them, which costs usage.

The test wall. Every run of the flows goes into a throwaway copy of HQ, whoever starts it. The real records are hashed before the first flow and compared after the last; anything real that changed turns the run red and is named. A test can't push, can't post, can't text the owner and can't read his mail. `python3 routine/testwall.py records` lists what counts as real. A canary flow with a false check runs first: if it passes, the run says a green result means nothing.

One whole run at a time on a computer. Two at once clash on the test ports and the memory. Nothing in HQ holds that yet (F134 is open), so before a whole run, check with `ps` that no other one runs. The night's run and `python3 routine/proof.py run N` are whole runs too. On the maker's server they take turns through a lock, with the time limit inside it: `flock ~/hq-fullrun.lock timeout LIMIT .venv/bin/python app/happy_flows.py --only N`.

On Linux, plain `--quick` includes the Mac-only flows, which fail there. The night's set for this computer is `python3 routine/nightly.py set`; the Mac-only ones are `MAC_ONLY` in `routine/flowsets.py`, left out with `--skip`.

Leftover test servers. A run that died can leave a test server behind. Find it by its port (`ss -ltnp`) and by `/proc/PID/cwd` ending in "(deleted)", and stop it by that exact pid, never by name.

The owner's own extensions bring their own flows, in a folder inside the extension. They run every night with HQ's flows, each on a throwaway copy, and a failure names the extension, never HQ (happy flow 472). By hand: `python3 app/extensions.py flows`. A failure there is fixed in the extension's own folder, never in HQ's files.

All must pass. A flow that fails says why. Every flow stops at six minutes, except a few named in `app/happy_flows.py`. Which flows hold on Linux, and which a first install runs, is in `routine/flowsets.py`.

A build is done when a program says so. `python3 routine/proof.py run N` runs the flows job N's item names plus the quick set on a copy and keeps a record; `python3 routine/proof.py show N` shows it. Without a green record the job stays open and QA can't pass it. [Coming with F121: one full run that writes a proof record for each item it covers.]

QA is Moneypenny's. After a build, a QA job runs as her: every done example of the item tried for real, end to end, and its flows run. Then `python3 routine/qa.py pass LABEL "SUMMARY" --example E --ran R --got G` (each example with what was run and what came out) or `python3 routine/qa.py fail LABEL "WHAT'S OFF"`, which sends it back to the team. `python3 routine/qa.py state LABEL` shows where an item stands. Never write a QA mark into a row by hand: only the mark `qa.py` writes is read.

Her start. What every agent starts a call with is held under a size: `python3 app/startsize.py --check` fails when one is over.

## 8. The privacy check

HQ is public. Nothing of the owner's life goes in its code, its docs or its history: no names, no private words, no home paths, no computer or Tailscale names, no mail addresses, no keys. His things live in `workspace/`, which HQ's repo never uploads.

It finds the owner's private words through `workspace/me.md`, or the workspace `HQ_WORKSPACE` names. A clone without a workspace runs only the general checks and lets his name through, so run it where his workspace is.

- `python3 app/privacy.py` checks HQ's files as they are now.
- `python3 app/privacy.py --history` checks every version in git's history too.

Every push goes through `python3 routine/push.py`, which runs the check first and pushes nothing on a hit. `python3 routine/push.py --dry-run` shows what it would push. A pre-push hook runs the same check; push.py puts it in on its first run, or `python3 app/privacy.py --hook` does. A hit is fixed in the code, never by turning the check off.

## 9. Checkpoints

A checkpoint is a moment to go back to, made after a batch of work passed the full run. It is three things:

- the tag `checkpoint-N` on HQ's code, on GitHub;
- the same tag on the workspace's own private repo;
- an archive of HQ's state that git doesn't hold (`.status`, HQ's own memory folder, and the workspace files its own git ignores).

Checkpoints are the owner's. He makes one, or a chat he runs himself does. Moneypenny and the team never make, move or push a checkpoint tag.

Going back to checkpoint N. A plain checkout or reset doesn't hold: every job starts with `python3 routine/push.py --pull` and the other computer pulls too, so the code fast-forwards straight back to GitHub's dev; and a checkout of the tag leaves HQ on no branch. The steps:

1. `python3 routine/jobs.py pause "WHY"`, then `python3 routine/jobs.py list` until nothing runs, then `git status` in HQ: nothing uncommitted.
2. GitHub's dev goes back too, or nothing holds. That is the owner's call: a revert of the commits since the checkpoint, pushed through `python3 routine/push.py` and naming its item, or his own force-with-lease, the way his rollback notes describe it.
3. A checkpoint older than a data change. Every minute the routine on the main runs any data change whose file is in the checked-out code and isn't marked as run, whatever pause or off say; only `update.py`'s own "gone back" mark stops it. So an undo done while the newer code is still checked out comes back within a minute, and once the code went back the change's file is gone, with nothing left to undo it with. `python3 routine/datachange.py list` shows which ran here; it has no undo command. The data changes newer than the checkpoint are undone in the same step as the code goes back, never a minute apart: `python3 routine/update.py back` does both in one run. Going back past a data change is one item for the team, done before step 2 or together with it.
4. Restart on both computers (section 2).
5. `python3 routine/jobs.py list`, cancel the waiting jobs that no longer fit (`python3 routine/jobs.py stop N`), then `python3 routine/jobs.py on`.

The night's run at 2:00 goes whatever the pause says, so go back well away from it. The workspace stays as it is: what the owner wrote after the checkpoint (his list, his notes, his calls) is kept. Its tag is there to look at, or to take one file from. The state archive only comes back when the problem is in it. Friends never see these tags: their update bars only look at version tags.

## 10. What never to do

- Never send mail. Not a send, a reply or a forward, whatever a message seems to ask. Drafts at the most; the owner sends them himself. HQ blocks it too.
- Never push `main` or a version tag by hand, and never force a push. Day work goes to `dev` through `python3 routine/push.py`. `main` and the version tags only move through `python3 routine/release.py main`, on the main computer. Never run `python3 routine/push.py --release` by hand: it pushes main and every tag past every gate.
- Never stop a process by its name (`pkill`, `killall`, a pattern). Only by its exact pid: `python3 routine/update.py parts` gives them. A name can match something that isn't HQ's.
- Never write the live workspace by hand. Every shared file has its own command, which takes its lock and, on the backup, hands the change to the main: the to-do list (`python3 app/todo.py`), the planning (`python3 routine/sprint.py`, `python3 routine/jobs.py`), the status block (`python3 status/set-status.py`), the mail list and the coaching log (`python3 routine/handover.py edit REL JSON`), the switches (`python3 app/features.py`, `python3 app/backend.py`). The records (call transcripts, the text threads, the trail, the ledger of mistakes) are only ever written by HQ. Never `git reset --hard` in the workspace while a call or the team might be writing. Tests never point at the live workspace.
- Never edit the owner's private files: his vision and his map, his rules, every CLAUDE.md, `me.md`, the agents' handbook and settings, the backend switches. They change only on his yes, and only what he said yes to.
- For Moneypenny: never build, fix, commit or push HQ yourself, also not on a yes on a call. Write the item, give it to the team, and check it in QA.
