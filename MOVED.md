# What moved from HQ, and what stayed behind

HQ2's backend is HQ's, moved: the same data files, the same formats, the same commands. What served the team (building
and running work by itself), the agents running themselves, news and feedback stayed behind. Decisions per module:
**whole** (copied as it was), **trimmed** (the team's parts taken out, the rest as it was), **new** (written for HQ2),
**left** (not moved).

## app/

| Module | Decision | Why |
|---|---|---|
| about_self.py | trimmed | an agent's facts about herself; reads his own lines from routine/hislines.py instead of sprint.py |
| agenda.py, appt_notes.py, kinds.py, planning.py | whole | the calendar copy, notes on an appointment, the five kinds in colour, the done and didn't-happen marks |
| agents.py | trimmed | the three agents; Moneypenny's character and craft rewritten so she prepares hand-overs instead of handing work to a team; no handbook |
| backend.py | trimmed | the switches briefing, open_line, one_way_sync, handover; names it doesn't know stay in the file |
| bot.py | trimmed | the call line; serves web/ at /, the status server under /status/; no news, feedback or cycles endpoints |
| brain.py, call_end.py, call_state.py, claude_llm.py, fillers.py, pipeline.py, lines.py, transcript.py | whole | the voice pipeline, the Claude session, call transcripts, the open line |
| call.py | trimmed | no news call, no mistakes ledger after a call |
| coaching.py, workflows.py, games.py, lists.py, notes.py, todo.py, loose_ends.py, open_loops.py | whole | Life coaching, the map, the games, the bucketlist and wishlist, quick notes, the to-do list |
| config.py | trimmed | the call rules: the team, the queue, the scheduler, the sprint, the stop lines' switches, cycles and feedback taken out; one building rule (hand-overs) in their place |
| direct_line.py | trimmed | the texts on three lines; no team kinds (jobs, QA, estimates, releases), no record, no ledger, no item record |
| drive.py, travel.py, trips.py, weather.py | whole | travel, driving, the weather |
| extensions.py | trimmed | a friend's own add-ons; the clash bar keeps "talk it through" and "it's fine", no "send to the team" |
| features.py | trimmed | the switches; no features built in pieces (that was QA's), no "agents run themselves", no news; unknown ids kept in the file |
| maintaining.py, me.py, privacy.py, ringing.py, thread_search.py, tour.py | whole | the walkthrough index, me.md, the privacy check, an agent calls him, old texts, the tutorial's demo call |
| outbox.py | trimmed | the texts' style filter and claim check; no batches (those were the cycles') |
| policy.py | trimmed | what a call may run; the team's scripts out, the planning board, the hand-overs and the mail switch in; every guard on his files kept; shell reading from routine/shellread.py |
| quick_context.py | trimmed | an agent's start; Moneypenny's is the status block, the planning board and the hand-overs |
| rules.py | trimmed | the rule topics looked up during a call; no handbook |
| tour.json | whole (moved from app/web/) | the tutorial's data |
| start.sh, stop.sh | trimmed | both servers, their own ports and pid files, the phone line off by default |
| start-linux.sh, stop-linux.sh, requirements.txt | whole | (ports changed) |
| com.hq2.routine.plist | whole, renamed | its own LaunchAgent id |
| lists_test.py | moved to tests/test_lists.py | |
| happy_flows.py, news.py, feedback.py, feedback_box.py, item_record.py, departments.py, handbook.py, startsize.py, measure_call.py, check_pieces.py, make_samples.py, test_*.py, features-in-pieces.json, web/ | left | old tests; news and feedback (taken out in the design); the team's record and departments; the agents' handbook; measuring tools; the old page (the new one is web/ at HQ2's top) |

## routine/

| Module | Decision | Why |
|---|---|---|
| tick.py | trimmed | the minute: role, sync, heartbeat, the status server, the call line, usage, the laptop, the watchdog, the mail check, the log's three hours, the briefing, helpers, data changes, saving, Donna's looks, reminders and the game's texts, extensions; no job starting; `--dry` added |
| jobs.py | new (same name) | only the mail check's switch line on the roadmap (next, list, mail-on, mail-off, mail-fast, mail-hourly) and the queue's lock, so the commands handed to the main stay the same |
| planning_board.py | new | the planning board, read only: open rows with rank and MoSCoW from sprint.json |
| handovers.py | new | the hand-overs in HQ/prep/, read only |
| shellread.py | new | the shell reading the policy uses, taken from cyclehook.py unchanged |
| hislines.py | new | his own lines, taken from sprint.py unchanged (about_self's filter) |
| role.py | trimmed | main and backup; WRITES only for what HQ2 has; HQ_ROLE_READ reads the pairing from another HQ's memory and never writes there |
| update.py | trimmed | the update check and button, the release guard; no job ending or holding; HQ_UPDATE_LOOK=0 skips the background look |
| handover.py | trimmed | no round journal |
| hqpaths.py | trimmed | ports 7870 and 4758, its own memory (Application Support/HQ2), its own LaunchAgent and unit names |
| incidents.py | trimmed | no record step |
| briefing.py | trimmed | (words only) |
| battery.py, datachange.py (+ datachanges/ 001–003, 005), failures.py, gitlock.py, heartbeat.py, helper.py, hqlock.py, lidsleep.py, log_cycle.py, mailfast.py, mailguard.py, mailsort.py, pings.py, routines.py, saver.py, settle.py, stats.py (+ .m), statusline.py, stream-usage.py, sync.py, tailnet.py, temperature.py (+ thermal.m), usage-check.py, usagelive.py, watchdog.py, mail-check.md, the install and helper-app scripts | whole | (names and paths changed to HQ2's own where they were shared) |
| datachanges/004 | left | it needs sprint.py; it has run on the live workspace |
| carryon, crash, cycles, cyclehook, estimate, usagecost, usageline, sprint, review, qa, qatests, proof, nightly, release, flowsets, schedule, planning_index, runjob, quiet, nudge, line, machalf, wall, daygo, front, prepfeed, wholebuild, sidebyside, chainrun, nowroad, qaroad, textrun, realcase, testwall, measured, misses, mistakes, ledger, pokes, trail, roundlog, happy, push, about, helper app's job parts | left | the team, its queue, estimates, sprints, reviews, QA, nights, releases, the agents running themselves |

## status/

| File | Decision | Why |
|---|---|---|
| server.mjs | trimmed | 1,407 lines to about 780: routines, incidents, the laptop, usage, updates, texts, role; new /status.json, /planning.json, /handovers.json, /sessions.json; no page, sprint, team, QA or night-road endpoints |
| parse.mjs, paths.mjs | whole (parse trimmed of the reserve) | the roadmap's status block |
| usage.mjs | trimmed | the reading and the stop lines for the bars; no gate, landing, windows or reserve |
| save-usage.mjs | trimmed | saving a reading; no gate |
| set-status.py, phone.sh, direct-sw.js, manifest.webmanifest, icons/ | whole | (ports and pid files configurable) |
| index.html, direct.html, direct-check.js, update-ui.js, night-road.mjs, backfill-jobs.py | left | the old pages (the new page is web/) and the team's night road |

## Elsewhere

| | Decision | Why |
|---|---|---|
| desktop/ | whole | the Mac app, copied, not reworked (it still points at 4748 and 7860) |
| install/ | trimmed | its test step runs tests/run.py instead of the old flows |
| template/ | trimmed | no cycles.json or handbook; the backend switches HQ2 has; no team in its texts |
| workflows/ | whole | the map's guide and blank |
| tests/ | new | one small test per module with logic of its own; tests/run.py runs them |
| tools/test_instance.sh | new | a second pair of servers on a throwaway copy of the workspace |

Counts: 80 Python modules in app/ and routine/ (HQ had 163 with its tests); about 38,000 lines of backend against HQ's
77,700 (120,500 with the old flows file).
