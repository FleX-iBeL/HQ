# Changelog

What was added and changed in each version of HQ, newest first. The small grey version number on the call page, the status page and in the Mac app opens this. Fixes get a patch number (0.2.1), bigger features the next minor (0.3). "Coming next" is what's built but not in a version yet; at a release it gets the version's number and date.

## Coming next

- Ready for the sprint: only items you've signed off as ready go to the team. Each item on the planning has a Ready tick in Sprint planning on the Status page, next to its place and its MoSCoW tag, and on a call you can say it: "the feedback button is ready", or "take its ready off". If an item's words change after it was marked, it shows Changed since ready until you mark it again. Plan the sprint and Send to the team leave out an item that isn't ready and say what it still seems to miss, like no out of scope or no size; only on your clear say-so on a call does one go to the team anyway, and the team is told it went without the mark (H272).

## 0.4.13 · 25 October 2026

- Bugs before features, always. Moneypenny ranks every bug above the features and puts it first in the sprint, to keep the tech debt down: the shortcuts and unfixed bugs that pile up like interest on a loan, until every new change gets slower and riskier. Ask her what tech debt is and she'll say it plainly. Every planning keeps Bugs and Features apart (a fresh one starts that way), and if your HQ has no routine check for bugs, she suggests one (H271).
- The sprint by MoSCoW: give each item on the planning a tag, Must, Should, Could or Won't this time, on the item in Sprint planning on the Status page or on a call ("the feedback button is a must"). The planning shows in groups, each in its own colour in light and dark, with a legend: Must first, then Should, Could, the ones not sorted yet, Won't last; bugs first in each group, then the rank. The sprint falls into the nights in that same order (H271).
- Sprint planning, the second half: on the Status page, Sprint planning shows the planning in rank order with each item's estimate. Tick the items for this sprint and see them fall into the coming nights in that order (the team's room is every night from 22:00 to 8 in the morning), each with when it should be done and its share of the 5-hour and weekly usage, and a line where the room runs out. Pick the night it starts, then Plan the sprint plans them for the team in that order from 22:00, the same as a call planning them; on a second HQ it goes to the main one. On a call: "plan these for tonight" (H269).
- Sprint planning, the first half: every open item on the planning now has an estimate by itself, about how long it takes and how much of the 5-hour and weekly usage, made the same way as for the team's own work (and made again when its words change, never when it's only moved). On a call, give items their place: "make the feedback button number one", "put it third", "take its rank off". A new item has no place until you give it one, so the others keep theirs. The Status page shows each item's place and estimate, and a call can read the whole planning in rank order (H269).
- Moneypenny is here. She's no longer coming soon: a card next to Donna and Pepper, called directly, handed over to, or brought into a call. Cool and composed, dry wit, few words: she's head of development, sitting with the team that builds HQ. She keeps the planning ready: before a piece of work goes to the team she goes through it with you (what's asked, what done looks like with examples, what to test and which new checks to add, why it matters, what's out of scope, which parts of HQ it touches and whether the call line restarts, how big it is, what it waits on, and that nothing private goes in) and politely says no until it's complete. When it's built she checks it's really done (it does what was asked, the old checks still pass, the new ones are added, the tutorial and changelog are updated) before you test it yourself. She runs on Opus (H250, H256).

## 0.4.12 · 24 October 2026

- An X on an appointment is now just a mark in HQ: nothing moves in your Google Calendar any more, and you don't need a calendar called HQ Planning. Done and X are still there for the weekly look back. Anything an X moved there before goes back where it came from by itself; once that calendar is empty you can delete it in Google.
- Ask Donna how to get to something in your calendar and her 9292 link now plans for the right time: leaving when the trip starts, or getting there by the start of an appointment, instead of from right now. With the link she says in one short line what's off at the stops and stations near both ends, like a stop that's closed, from the open live data; when there's nothing, she says nothing.

## 0.4.11 · 23 October 2026

- Your own news, inside HQ. Turn on News under What HQ helps you with and a News button shows up. The first time, set it up in a short call with your agent: what you want to stay up to date on, what you don't want to hear about, and where from (your agent suggests free sources and checks they work). About every hour HQ reads those sources, keeps only what's about your topics, leaves out what you said no to, and shows it as your own newspaper: short items with their source, newest first, a tap to read the whole thing inside HQ. Kept apart from your mail. Change it any time the same way.
- Build your own on your HQ, and updates never break it. What you add yourself (a connector for another mail app, a routine of your own, your own kind of text from your agent, extra rules for calls) is an extension: a folder of its own in your workspace that an update never touches, with a line on what it does. HQ reads it at its fixed points: the call and text rules, the mail check, its routine every minute, and the scripts a call may run. HQ's own version always leads. After every update HQ checks on your computer whether something you added might not fit the new version; if so, a short message says which one in plain words, with two buttons: talk it through with your agent, or send it to your team to fix. EXTENSIONS.md explains how to build one, and how to move what's already built into HQ's own files into an extension (H235).
- Donna, Pepper and Moneypenny now really build their own lives. After every call and every text of theirs, HQ itself keeps the new little things they said about themselves (their day, the office, a mood, an opinion), dated, and skips a detail they'd already told you in other words. Each call and text they're nudged, now and then, to let a new one slip in or bring an old one back the way a person remembers, never contradicting one; when an opinion or a mood changes, they say why (H232).
- Your to-do lists in your own order, and a new name when you want one. Every open list, the groceries too, has dots at the start of each row: drag them to put the item higher or lower (or the arrow keys on a keyboard). An item's own page has Rename. Both land in your list with a line in its log, and Undo puts it back. The ticked-off groceries are easy to read again: plain text, no line through them, and the Tick off button keeps its green in dark mode (H231).
- Travel on appointments, by public transport. An appointment away from home gets its trip by itself once HQ knows where it is: its place in the calendar, or a friend's address you gave once by name. It starts at home, or at the appointment just before it that day. In the hours before, HQ watches the live train, bus, tram and metro data, and Donna texts you when your train is cancelled, late or leaves from another platform, or a stop near either end has a message, with a 9292 link to plan again. Tap Travel in an appointment to turn it on or off; it's a switch in What HQ helps you with, and the tutorial explains it. It uses open data, free and without a key (OVapi's feeds from the Dutch transport companies' own open data). Driving comes as its own feature.
- A six-week game can have Donna keep you honest: a text in the evening, at the time you picked, when today's tick isn't in yet, and on a day your calendar shows you away from home around the time you usually play it, a heads-up earlier that today is different and what still counts. The weekly look back now goes through the game's score, and the game's card shows the rest of its design: who you are at your best in it, what comes easily, what could get in the way and who keeps you honest (H239).
- The get-started tutorial now covers the Game and Coaching buttons, the microphone button and Cancel, and it stays right: every night a check finds any button or screen without a piece in the tutorial, and the tutorial is read again against what HQ does now and fixed the same night.
- A past call opens at its end, where the call finished, like a chat; scroll up for the start (H233).
- The changelog no longer jumps to the bottom right of the screen when you scroll it on the iPhone; it stays in the middle, readable (F48).
- The nightly check works in rounds: when it finds problems, everything gets fixed first and then the whole check runs again, at most three times. If it ends green, the update goes out that same night; if it's still not right after the third time, it waits and you hear why in the morning.

## 0.4.10 · 22 October 2026

### Added
- Life coaching has its own place in the app: a Coaching button. It shows your map's layers with their checklist and how far each one is, and each layer, and each check-in, has its own Start button that begins a call with your agent about only that, so a session doesn't drift. There's a coaching line too, a chat with your agent just for life coaching. HQ keeps your check-ins for you, read from your map: the weekly look back (on the day and part of the day you set in your ideal week), the look back at the end of each six-week game, and a bigger check-in every few months. When one is due, the button gets a red dot and the check-in lands on the coaching line; one tap and you're in it. No notifications, just the dot. Done, or Not now until the next morning (H225).
- The six-week game. When you want to play one, your agent holds a short design session with you as part of Life coaching: what it's for, the dates (a setup week, six weeks, a week to look back), how you win, and what you keep track of: a tick a day, counts against a target, a diary of how it felt, a graph. It's written in your map and handed to your team, who set it up in HQ. Then a Game button shows up in the app, where you tick the day, add to a count, keep the diary, write a note and look back on each week; your agent and Donna's texts do the same when you tell them. Past games stay there to open again (H222).
- Life coaching keeps a checklist. Every question of every layer of your map has its own line in your map, marked answered, parked (with why and when it comes back), left for later (with when) or open. Your agent ticks it as you go, never skips a question without saying so, and before a layer is called done it holds it against the guide line by line and tells you what's still open. A new map starts with the whole list (H224)

### Changed
- A team job is now only paused for its usage once it has used about four times its estimate, not twice, so jobs stop getting paused for using a bit more than guessed. The 5-hour and weekly stop lines stay as they were (H221).
- The team's work is sorted into one clear set of kinds, made from everything the team has done so far: small and big builds, research and reading, transcribing, the routine's own maintenance, releases and merges. Reading work no longer lands in a pile of one-minute jobs, and the pause now counts how sure the estimate is: when the first look, the call or the team itself guessed a job would take longer, it gets that much more room (at most twice) before the pause at four times (H220).

### Fixed
- The Coaching place shows every layer of your map and the check-ins without scrolling. Before a call it kept a big empty space at the bottom, so only the first three layers showed; now each layer is one short row, the map comes first and the check-ins right under it, before a call and on one. The six-week game screen had the same empty space; it is gone there too (F47).
- A long typed message on a call goes in whole. The chat's box and the call cut anything past 2000 characters without a word, so a long dictated message lost its end; now one message takes up to 10000, and past that it stays in the box and says so instead of being cut (F46).
- On a call, what you say while thinking out loud no longer gets lost. A long, quieter stretch of talking could be taken for silence and dropped whole, so the call answered only the last bit; now a long stretch is only dropped when it really is just noise, a quiet one is made louder first, and anything dropped is noted so it can be found (F45).

## 0.4.9 · 21 October 2026

### Added
- Public transport advice from your front door. Ask on a call or in Donna's chat how to get somewhere in the Netherlands and you get a 9292 link that opens with both ends filled in and the advice ready: from your home (a new Home line in me.md) or any address, street, postcode, town or train station you name, to wherever you're going, and trains (and walking) only when you ask. Addresses are looked up in the government's open address service and stations in an open station list; no hidden browser, and no 9292 account or key (H214).
- The 9292 link starts where your phone is when you don't say where from, once you've allowed your location in the app (the weather's "Use my location"); otherwise from home, and it tells you which. And it never gives you trips with a surcharge ("vervoer met toeslag") unless you ask for them (H216, H217).
- The 9292 link also never gives you trips that need a reservation ("vervoer met reservering": buses, boats and taxis you book ahead) unless you ask for them (H218)

## 0.4.8 · 20 October 2026

### Added
- Donna nudges you until you say it's done. Ask on a call or in her chat ("keep nudging me about this until I say it's done"), say from when and why it matters, and she texts you about it now and then, more often when it matters more or a deadline is close, never at night, in her own words and without numbers or schedules. Tell her it's done, by text or on any call, and she stops; "later" gives you a break until the next morning. While it's open it shows with a bell in Donna's part of the notes, with a Done button (H211).
- Donna tidies your mail when you ask: mark it read or unread, archive it, star it, mark it important, put it in a label, and make or rename labels, on a call or in her chat. She never sends, replies or forwards; the trash, spam or deleting a label only when you ask for exactly that, and she suggests archiving instead. For mail you want sorted from now on she offers two ways: she walks you through a real Gmail filter, step by step, or the hourly mail check puts new mail in its label for you, by a rule you agreed, with a line for each mail it sorted and rules you can see and stop. Without a rule the mail check only reads (H213).

### Changed
- Donna now thinks on the same model as Pepper, the stronger one, to see how it feels. She stays quick and light: the same things to look after, the same character, rights and voice. The main page no longer names the models; under each agent it just says what she's for. If it doesn't feel right, it goes back in a later update (H213).

### Fixed
- Something done no longer comes back. When you tick an item off or let it go, what still hangs on to it goes with it: Donna's notes and reminders about it, her watches and nudges for it, and its lines under To check on the mail list. What only might be about it is left and named once, so you can say clear it too; a very important mail stays until you say so. Every thing cleared gets its own line in the list's log, and Undo puts it all back. Reminders, watches, nudges and notes can now be tied to a to-do item, and the mail check no longer adds mail about something already done, unless it asks something new with a date (F43).

## 0.4.7 · 19 October 2026

### Added
- Groceries tick off in the app. Each grocery has a tick; a ticked one moves to its own Ticked off list under the groceries, A to Z, and one tap puts it back on the list. Adding a few at once, one per line or with commas, gives one item each, and one that's already there isn't added twice (F40).

### Changed
- The README's version now moves along with every release, so GitHub's front page always says the version that's out.

## 0.4.6 · 18 October 2026

### Changed
- The README is rewritten for someone new to HQ: what it is in a few lines, everything it helps you with, and how to get it running step by step on a Mac, a server, the phone, two HQs as main and backup, and Windows, plus how updates work. The install in technical detail, for your Claude, moved to its own page, INSTALL.md. Nothing says 0.1 any more.

## 0.4.5 · 18 October 2026

### Added
- A get-started tutorial, always to find again behind the new question mark next to Settings. Short pieces for what you're looking for (calling your team, the chat and typing, the to-do list, texts with Donna, the calendar, notes, past calls, the team working while you're away, the mail check, the weather, Settings) walk over the real screen with a highlight and a caption, on made-up demo content: nothing you tap there changes your HQ, and it says so. It ends with how HQ is built to be expanded, with shared best practices coming soon. Or try a demo call: call Donna or Pepper on a safe playground, both on Opus, and ask anything about HQ, also straight from the piece you're reading. Nothing on a demo call is saved and nothing changes (H74).
- Turn on what you want. Settings has a new page, What HQ helps you with: one line per part of HQ (the calendar, the to-do list, texts with Donna, the weather, the mail check, quick notes, the team's work and Life coaching), each with its own switch. Everything starts on. Turn one off and its button goes, the rest moves up, on the phone and in the Mac app, and your calls stop bringing it up unless you ask. What leans on another says so: the weather needs Donna's texts (H205).
- Your to-do list, the Eisenhower way, at the heart of HQ. Everything to do in your own priority lists (what you promised other people, the four squares of important or not and urgent or not, let go, done, a wishlist and groceries), kept up to date just by talking: on a call or in Donna's chat things are sorted in, moved, ticked off or let go, each with a line in the list's log. In the app the new To-do button shows it as the matrix, with how many in each square and the first few; tap a square for its list and an item for everything about it, your own words included. Tick it off, move it, let it go or add one by hand, with Undo for the last change, or call about it. The hourly mail check says when a mail is about something already on your list; a mail only goes on it after your yes. A new install starts with the lists empty (H200).
- The map, a guided workflow you can turn on: from the life you want three to five years from now down to next week, in six layers (the vision, the year, the six-week game, the ideal week, the real week, looking back), with what to optimise for right now, home base and trips, money for the things you want, squeezing the week, one kind of work per day, the love and hate list, the money that runs itself and a check-in every few months. Your agent, Pepper by default, walks you through it on a call, one question at a time, sparring with you and writing your answers into your own map as you go. Each layer says what it is, the questions to go through, what it makes and what it hands to the layer below. Turn it on with `python3 app/workflows.py on map`, then on a call say "let's go through my map".
- On the Mac, your music can stay at its normal volume during a call: Settings has a new row, Other sound, Lower or Normal. With Bluetooth headphones on, the call uses the MacBook's own mic, so the headphones keep their full sound (H198).
- The 5-hour bar on the status page unfolds into the whole day: the next four 5-hour windows, each with its reset, its stop line, the work landing in it and what waits until when (H199).
- A switch on the lid line of the laptop's status page: one tap turns sleeping with the lid closed on or off, no call needed (H191).

### Changed
- HQ's page on GitHub now always says the version that's out: every release also updates its About, which has a new description in everyday words. Setting it needs a GitHub token with Administration access on your copy (in `~/.config/hq/github-token`); without one the release still goes out, and the status page and Donna tell you the About wasn't updated (H197).
- Modern 3, the one look. What was Modern 2 is now how HQ always looks, and the Look row in Settings is gone: nothing to pick. On top of it, every sheet follows your finger: pull a sheet down to close it (on a call, where the sheets hang from the top, pull it up by its title), and swipe right to go back a level, from an appointment to the days, from a past call to the list, from a to-do item or list back to the squares. Scrolling a list never closes it, and a short pull springs back. Sheets fade in, every tap answers with a small press, and the important-but-not-urgent square keeps its mark. The status page and Donna's chat look the same way.
- New versions come out steadier. Every night the team tests HQ, fixes what it finds and decides itself: when it's sure, the night's work comes out as a new version; when it hesitates, the work waits on a test line of its own and never reaches your update bar until it's sure. Nothing personal ever goes up.
- The rain alert follows the shower. While it's on, Donna looks every five minutes and texts again only when the shower comes a quarter of an hour earlier or later than she said, starts early, stops, or is gone. The switch just says it's on, no end date (H196, H188).
- HQ's own icon, the house, wherever a page is saved: the iPhone's home screen, the Dock on the Mac, the Mac app. An icon already on your home screen keeps the old one until you add the page again (H194).
- With two computers, only one writes. A call on the backup hands its changes to the roadmap, the notes, the mail list, the to-do list and the reminders to the main computer, so no more two versions of the same file (H203).
- The team's time guesses got better: a quick look guesses each piece of work as it's given, and the guess counts how much there is to read (H190, H204).

### Fixed
- Every sheet and menu closes again on the phone. The changelog, Are you sure and the other menus close with their button, a tap beside them or a pull down, the same as every sheet, and the tutorial's Next moves on; a tap beside a sheet only closes it, nothing under it is pressed. On a call a sheet closes with a pull down on its title too, and Hang up ends the call. A pull on the screen itself no longer makes it bounce like it's reloading (F39).
- Donna answers again when her notes have grown big (F38).
- Small fixes from the weekly test run: an old laptop name no longer keeps a warning open, and the logs stop repeating the same line (H162).

## 0.4.4 · 17 October 2026

### Added
- Modern 2, a second look to pick in Settings (Look: Modern or Modern 2, kept on the device; Modern stays until you pick). Made for ease of use: the Call button wide and low, right above the bar at the bottom where your thumb is; Mute above Hang up on a call; the picked agent marked with a tick; the open button in the bar in a soft pill; every sheet with a clear title and a round close; past calls, the calendar, notes, the weather and Settings as white cards on a soft grey, with bigger buttons and a visible focus ring for the keyboard. The status page and Donna's chat follow it when opened from the app (H185).
- Links you can tap. A web address in her text opens with one tap in the call's chat, in past calls and in Donna's chat, on the phone, the phone version and in the Mac app (a new tab, or your browser from the app, so the call goes on); she can also give it as a few words that are the link. Your own links work too. Only web links (https and http), and the voice never reads one out (H170).
- Tick off or X your appointments. In the calendar in the app every appointment has a check (done) and an X (didn't happen as planned); tap again to undo. An X greys it out and moves it in your Google Calendar to your calendar named HQ Planning (the name is a setting, HQ_PLANNING_CALENDAR in switches.env); undo moves it back. Appointments with other people in them and birthdays keep their X in HQ only and stay where they are. The past days of this week stay in the calendar, so you can still tick them, and a call can go through the week with you: what's not ticked off, what got an X, and the patterns (H143).
- Your calendar during a call. The Calendar button stays in the bar at the bottom on a call, with any agent and on a three-way call too, next to the Mic button; the calendar opens above the call's own buttons and the call and your mic carry on. Calling about an appointment waits until the call has ended (H144).
- A quick note on each appointment. In the calendar in the app every appointment has a note button: one tap and you're typing ("arrived 16:00, left 17:00"). The notes show under the appointment in the list and when you open it, each with its own Clear; they stay with an appointment X'd to HQ Planning. A call and Donna's chat read them, so "look at the haircut and update my calendar" puts its times right in Google Calendar, keeping the old times in its description (H146).

### Changed
- The totals on the status page say what they count. Under Jobs from calls the total is the running job's time left, the waiting and held jobs and the minutes between them, with the usage they should take, and a line under the heading says so, part by part, so it adds up with the jobs below it. Under Scheduled each planned item counts once, a repeating one only its next time. Both say they're the computed estimate. The team's own guess is on its own quieter line under each job, so it doesn't read as a second estimate (H174).
- Usage that keeps itself in check. Every job the team runs now has an estimated usage next to its time (how much of the 5-hour and the weekly limit it should take), learned from what the jobs like it really used; the old rule of thumb (1% per 2 minutes, 0.2% on the weekly) is only the fallback for work with no history. A job starts when that usage fits under the stop lines, else it waits, and the status page, the team's list and the planned items say when it should start ("starts around 14:20 when the usage leaves room for it"), worked out from how the lines move and when they reset. After each job its real usage is learned, so an overrun makes the next ones wait a little longer by themselves. A job that uses about twice its estimated usage pauses for good, Donna texts you, and a call lets it carry on or drops it. The past jobs got their real usage from the saved readings (H172).
- A job's usage is its own. Each job's usage is now counted from its own chat's tokens (input, output, cache read and cache write, per model), turned into percent with a rate the team learns from the finished jobs: how many tokens make one point of the 5-hour and of the weekly limit, the weights per kind of token and per model learned too, with readings where someone else was on the plan at the same time (a call, the mail check, another person) left out, and the nightly run counting most. So a call or anyone else using Claude no longer makes a job look expensive or pauses it at twice its estimate; the start still waits on the real total under the lines. Estimates are in tokens as a range, shown in percent as before. The past jobs got their own tokens from their chats, and a call can say what a call cost on its own (H173).
- The team's time estimates now look at the finished jobs most like the new one: the same part of HQ (the calendar, the call page, the mail check ...), the same roadmap item, similar words. A calendar job is estimated from how long the earlier calendar jobs took, not just from all builds; when nothing earlier is like it, the estimate for its kind of work stays. Checked against every finished job: off by 3.8 minutes on average instead of 4.1, and 4.2 instead of 5.1 over the last 30 (H166).

### Fixed
- An update never needs a reboot. Installing a new version doesn't wait any more: it ends whatever runs (a call hangs up, a job's chat stops and carries on by itself afterwards, the mail check comes again within a minute), then restarts every HQ background part, all of them: the call line, the status page, the watchdog, and the routine (the HQ Routine helper on a Mac, its timers on Linux); the Mac app too when it changed. Each by its exact process, on a Mac and on Linux, and checked: only a part that really came back on the new code counts; one that doesn't is named in the update's note. The computer itself is never restarted. From the next update on, the new version itself decides what to restart.
- The calendar in the app shows a change right away. When a call or Donna adds, moves or changes an appointment in your Google Calendar, or an X moves one, HQ reads your calendar again within the minute, at any hour, also when the change was made on the other computer; before, it only read it once an hour. Whole-day appointments sit at the top of their day instead of between the night's appointments, and the list is always in time order (H153).
- Two computers come back in step by themselves after a crash or restart. Donna's pings file is only saved when something in it changed (it was saved every minute, so a crash nearly always caught it on its way over), lock and half-written files stay on their own computer, a conflict copy that is the same as the file is cleared without a merge job, and a call's transcript that its own commit missed is committed by the main computer half an hour later.

## 0.4.3 · 14 October 2026

### Added
- A new look for HQ, everywhere (phone, phone version and Mac app): a calmer layout in one column, Settings as a small pill top left, the weather as a quiet chip under the name, Donna and Pepper as cards side by side with the one you pick in her own colour, and on a call her orb leads with Mute and Hang up under it. The round buttons are gathered in one dock at the bottom with their names under them, and every sheet reaches down to the dock. Same buttons, same behaviour. It's the only look: there's nothing to pick in Settings (H137, H140).
- The weather in the app. Before a call, a small chip under the name on the call page shows the weather where you are (the town in your me.md, under Where I am): sunny or not, the degrees, the wind in Beaufort and the chance of rain, with a yellow, orange or red mark when there's an official weather warning (KNMI's in the Netherlands, through MeteoAlarm in Europe). Tap it for more: the warnings in full, now (feels like, wind and gusts, UV), the rain radar's next two hours, the next twelve hours, and today and tomorrow with UV, rain and sunrise and sunset. With no town set, it says so. Not on Free (H135).
- "The team" instead of the job list. On calls and in Donna's chat the work the computer builds is "the team": no more job list, queue or job numbers in what's said. "Put it on the roadmap" only writes it on the roadmap; "give it to the team" is your go: it goes on the roadmap first if it isn't there yet, then to the team, without asking again.
- Pepper sounds like herself on a call: warm, calm and unhurried, like a good phone call with someone who has time for you. Her own cadence and small human touches, no one-liners or jokes as her style, nothing like Donna. And no agent says "honestly" any more (H131).
- Whoever you bring in says hi. On a three-way or four-way call, once the line bringing her in has been heard, the one who joined says a short line of her own that she's there, in her own voice and character, before you go on. If you speak first, she just answers you (H130).
- A goodbye that fits your moment. When you close a call, Donna and Pepper say goodbye with a short comment on what you're doing right now: the appointment on now or coming up in your calendar, else something up on your to-do list. Moneypenny keeps her own goodbye (H129).
- Donna keeps an eye out. Ask her "let me know when …" for your mail (a package you're expecting: she texts you each update until it's delivered, or for a week) or the weather ("let me know if it rains later today": she texts you when the forecast shows it, with when). While a weather watch is open she looks every half hour. She texts when a watch ends too: answered, its time up, or you stopped it. Her watches show under her notes behind the notes button (H125).
- Donna texts first. Ask her (on a call or in her chat) to text you when an appointment starts, only the ones you pick, or a few minutes before; a bell shows them in the calendar inside HQ, and an appointment there has its own button for it. She also texts reminders you ask for outside the calendar ("remind me at 3 to …"), and keeps her own notes list, shown under your quick notes, which she may text you about on her own a few times a day, only when it's worth it. Your Google Calendar itself is never changed for this (H124).
- Your calendar inside HQ: a calendar button in the dock on the call page (before and after a call; phone and Mac app) shows today and the next two weeks from your Google Calendar, read only. Tap an appointment to see it, then "Call about this": the call starts knowing what it's about, and she greets you naming it. HQ reads Google through the calendar connector of your own Claude, every hour in the day and when you open the calendar, and never changes anything in it (H101).
- The weather every three hours: in the day, HQ looks at the weather where you are (the town in your me.md, under Where I am), with rain by the minute in the Netherlands and Belgium. When there's something worth saying, Donna texts you on the direct line: sun, something nice outside; rain coming, a heads-up with when; a rainy day, something cosy inside, never "go outside". Quiet otherwise, and never at night (H120).
- With two HQs (the laptop and a server), you see at a glance which one is main: a pill next to the name on the status page, in the Mac app, the phone version and on the call page. Green "Main" on the main one; grey "Backup · VPS is main" (or "Laptop is main") on the other. An HQ on its own shows nothing new (H118).
- Moneypenny can be brought into a call: "bring in Moneypenny" makes a three-way call, and bringing in one more makes it a four-way call, so you can hear the voices side by side. She still can't be picked or handed over to, and runs on Opus until Fable is out (H121).
- There's an easter egg. It has to do with Moneypenny, and it lasts until you close the app.
- Call back from the chat: when you open the app and tap the chat bubble, it shows your last call with a button at the bottom to call back and carry on where you left off, with the same agent, like Continue in Past calls (H119).
- Each agent keeps what she says about herself. When Donna, Pepper or Moneypenny tells you something about herself on a call, it goes in her own list in your workspace and comes with her on every later call, three-way call and text, so she stays the same person (H132).
- Donna's direct line on the phone: the chat bubble now also shows in the call page on the phone, inside or outside the HQ page, and never covers the voice button (F25).

### Changed
- The room a job needs under the usage limits grows with how long it's expected to take, instead of a fixed 5% and 1%: 1% under the 5-hour line and 0.2% under each weekly line for every 2 minutes of its estimate (a 12-minute job needs 6% and 1.2%), so a long job doesn't start just to get stuck halfway. Without an estimate it's the room of 10 minutes, as before. The status page and the team's list say why a job waits: how much room it needs and how much there is. The two rates are in one place, at the top of the usage code (H141).
- Donna's texts read like a person texting you in between: short, quick, casual, never the same line twice in a row. When the dev team's done building she just tells you they finished up, no details or status talk. The texts without Claude come in a few versions too, and never give technical details (H127).
- Her replies in the call's chat read like a reply in an AI chat app: more space between lines and paragraphs, numbered lists and lists inside a list, a bold word to start an item, softer list marks. She's told to lay longer answers out that way. Still no headings or tables, and the voice stays plain (H116).
- On a call the chat's top line says only who you're calling with: her name, both names on a three-way call, all of them with more (H115).
- The quick notes are just text now: the paper to doodle on is gone, and the field you type a note in grows with what you type, over more lines, like the chat's (H117).
- Every agent on a call is as human as Donna's texts: Donna, Pepper and Moneypenny each have a fuller character of their own, one of the people at a real HQ, with her own habits and more greetings in her voice, and vary how they say things (H128).
- "You're the best" closes the call, like the other goodbyes (H134).
- "Bring in" someone is always a three-way call, and "give me" someone always hands the call over to her (H122).
- On the phone, Settings has one row, Microphone and sound: what you pick there switches the mic, and her voice follows it. On the computer the Microphone and Sound rows stay apart (F26).

### Fixed
- The team's time estimates no longer drop to about a minute for every job. A computer that didn't know how a job was meant (the backup, or one that just took over) guessed it from the words and lumped builds in with the quick merge jobs. Now merges and releases have their own kind, builds are recognised from more wording, the two computers share how each waiting job was meant, and a waiting job's estimate follows what the team learns while it waits. Every job since the first was sorted again, and only jobs with a measured time count (F34).
- The update button on a copy of HQ that came without its git history (a download, or a clone whose tags didn't come along) never showed a newer version: the look failed quietly and counted as offline, and Update couldn't have run. Now a newer version always shows, and the first Update turns such a copy into a clone in place, keeping every file; it also works on a computer whose git has no name and email yet. The README says to clone, and how a Claude updates by hand the same way the button does (F32).
- A pull or push of the team's work that GitHub refuses no longer passes silently: it shows under Incidents on the status page and Donna texts you at once; the next one that goes through closes it (F31).
- Closing and opening the laptop's lid no longer leaves two mains. On a café's or a phone hotspot's network without real internet the laptop thought it was online, took over from the server while the server carried on, and both ran: duplicate merge jobs and sync conflicts once the lid opened. Now the laptop only takes over with a real internet connection; a main that stayed awake, online and working stays main, and the other hands back at its first look; and a main that's handing back queues no merge jobs (H139).
- Opening Donna's chat during a call no longer hangs up the call. The purple bubble now opens her chat as a sheet over the call page: drag its handle up to nearly the full screen, drag it down or tap Close to put it away, and the call keeps running. Her notifications work as before (F29).
- Donna's texts when something in HQ stays down (and when it's back) never came, and since the weather, the calendar and her pings were added to the same minute's look, those stopped with it on the computer where it happened. Fixed, and each of those looks now runs on its own, so one can't stop the others (F28).
- Changing the mic and sound during a call. Picking the AirPods (or any output the computer already plays on) as the Sound no longer makes her voice much quieter. On the iPhone, Safari and the Mac app the old mic is let go first, so the new one can take over. Where a device won't switch, the call screen says so plainly: on the iPhone, iOS picks the mic and sound itself during a call (Control Center); with the AirPods' own mic on, they play in quieter call mode; a mic that sends no sound is named (F24).
- Calling about an appointment from the calendar inside HQ always goes to Donna, who keeps the agenda, whoever was picked (F30).
- Donna's replies in her direct line also work on a computer that isn't a Mac (F27).

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
