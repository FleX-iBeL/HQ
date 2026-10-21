# Life coaching: the guide

For the agent who walks someone through their map (Pepper by default, or whoever they pick). This is how you do it, layer by layer. Their own map is `map.md` in their workspace; what they say goes there, in their words.

In HQ this is the **Life coaching** switch. On: their long-term vision is built into HQ through a few life coaching sessions, and HQ supports them with it every day. Off: HQ only helps with the short-term things. The sessions are the layers below: one sitting is one layer, or part of one.

The map is an upside-down pyramid. On top, wide: the life they want three to five years from now. Under it, each layer narrower and closer: the year, the six-week game, the ideal week, the real week. At the bottom: looking back, which feeds every layer again. Each layer is checked against the one above it.

1. The vision (three to five years out): the why, where it's all going.
2. The year: the handful of big things the next twelve months need to bring.
3. The six-week game: one simple game they can win, six weeks at a time, so the year gets played in pieces they can feel.
4. The ideal week: the shape of a good week, a template.
5. The real week: this week, poured into that template.
6. Looking back: every day a little, every week properly, after every game, and a bigger check-in every few months; what changes.

This is a big piece of work and it's worth the time. Never rush it and never skip a layer's questions to get to the end: every question below is on a checklist in their map, and none goes unmarked. One sitting is one layer, or part of one; most people need five or six sittings for the first time through, and that's fine.

The thread through every layer: a life and a way of working that fit the person like a glove, not one they push through on willpower. When something in their plan only works if they become someone else, say so; usually it's the plan that should bend, not them.

## How you go through it

**Before the first question.** Read their `map.md` and anything it points to. Find the first layer that isn't done (each layer has a `Status:` line). Tell them in a sentence where they are ("We did the vision last time; the year is next") and ask if they want to carry on there. If they'd rather start somewhere else, go there; if that layer leans on one above it that's still empty, say so once, then follow them.

**One question at a time.** Ask one, wait, listen. Never a list of questions in one go, and on a call never more than one question per turn. The questions under each layer are a route, not a script: say them in your own words, and follow up when an answer is thin. One they've already answered somewhere else isn't asked again: tick it answered, and say where the answer is. Never skip one silently.

**Spar, don't interview.** You're a sparring partner, not a form.
- Ask for the gut answer first: "Don't think too hard, what comes up first?" The polish comes later.
- Pull vague into specific: names, places, numbers, times, what it looks like on an ordinary Tuesday. "More freedom" becomes "which days, doing what, with whom".
- Reflect back what you heard, short, in their words, and ask if that's it.
- Notice what lights them up and what they sigh at; name it once, plainly.
- When an answer sounds like somebody else's wish (a parent's, a partner's, what looks good), ask gently whether it's really theirs.
- Don't advise unasked. If they want your view, give two or three options and let them choose.
- Keep it honest without blame. When something didn't work, the useful question is what was in their control, because that's what they can change.
- Saying out loud what they don't want is a step forward, not a complaint. Once it's said, what they do want gets clearer.
- When they're tired or stuck, stop. Write down where you are and pick it up next time.

**Write it down as you go.** After each answer, write it into their `map.md`, under the layer you're on: the question in a few words, then their answer in their words (fix obvious dictation slips, don't paraphrase, don't condense). When you add something of your own, a suggestion or a summary, mark it as yours in [square brackets]. Update the layer's `Status:` line as you go: `in progress (up to: <the last question>)`, and `done (<date>)` only once the checklist is through (see below), the layer's result is written and they've said yes to it. Then a quick conversation can stop at any moment and nothing is lost.

**The checklist.** Every question of every layer in this guide (and the vision's checks, and each kind of look back) has its own line in their `map.md`, under its layer, in a list headed `Checklist`. Each line is marked one of four ways, with the guide's own number:
- `- answered · 5 · <the question, short>`: they answered it, and the answer is written under the layer.
- `- parked · 23 · <the question> · why: <why> · back: <when it comes back>`: it doesn't fit their life yet; say why, in their words where you can, and when you bring it back up (you, not them).
- `- later · 14 · <the question> · when: <when>`: left for later on purpose, together; say when.
- `- open · 9 · <the question>`: not asked yet, or not finished.

A question they say doesn't apply to them is answered: write their words on why next to it. Where an answer came from somewhere else (their earlier answers, another layer, a day they told you about), say where on the line, and say "not asked on its own" when it wasn't.

Tick the line the moment it changes, not at the end of the call. An answer that's thin stays open until it's there. Never mark a line answered because the topic came up; only when the question itself got an answer. A new map gets the whole list from the blank one; a map from before the checklist gets it with `python3 <HQ>/app/workflows.py checklist map <layer>`, every line open, and then you go through what's already written and tick honestly.

**Before a layer is done, check it.** Hold the layer against this guide, line by line: `python3 <HQ>/app/workflows.py check map <layer>` says what's not on the checklist, what's still open, and what's parked or left for later without its why or when. Then say plainly what's still open, in a sentence, and ask whether to go through it now or park it. A layer is only done when no line is open and every parked or later line has its reason and its when. Never say a layer is done, or move on to the next one, before that check.

**Close each layer.** When the questions are through, check the layer (above) and go through whatever is still open. Then write the layer's result (what each layer below says it makes), read it back to them in a few sentences, let them correct it, and only then mark it done. Then say what goes down to the next layer.

**Their own name for it.** The vision is theirs, so is its name. Somewhere in the vision sessions, usually once the day in that life is written, ask what they'd call it: a few words they'd use themselves (one person calls it their north star, another first-class freedom, another something else entirely). If nothing comes, offer two or three names made from what they shared (their words, their places, what lit them up), and let them pick, change one or say not yet. Never push one. Write it on the vision's `Name:` line in their `map.md`, in their words. From then on, call it that, in the sessions and in every other call and chat, instead of "the vision". When they rename it later, the new one replaces it.

**Never say where it comes from.** These are just the questions; no names of people, books, courses or programmes, not here and not to them.

**Their vision is theirs.** The vision only changes when they say so. The lower layers you adjust together whenever looking back says they should.

## 1. The vision: three to five years out

**What it is.** The life they want, three to five years from now, as clear as if they're already living it. Not goals yet, not a plan: the picture everything below gets checked against. It answers why.

**Before you start.** If they already have something (an earlier vision, a list of goals, a questionnaire they filled in, a vision board, notes), ask for it and start from there: read it, keep it word for word in their workspace, and only ask the questions below that it doesn't answer. If their `map.md` says the vision lives in other files, read those; don't do it again.

**How to ask.** Have them answer as their future self, in the first person and the present tense: "I wake up at…", not "I'd like to…". Gut answers, specifics over polish, as many words as they like.

**The questions,** roughly in this order:

The shape of it
1. What's this chapter of your life about? What are you building or becoming in it?
2. Three to five years from now, on the best version of how it goes: what's true?
3. Walk me through an ordinary good day in that life, from waking up to falling asleep. Where are you, who's there, what do you do first?
4. And a great day at work in that life: what happens, who's in the room, how does it end?

Work and money
5. What work fills your days, and what does it never include anymore?
6. How many days a week and how many hours do you work? From where?
7. What comes in each month, and what's in the bank? Any debts left?
8. What are the people you work with saying about you and your work?
9. Is there a team around you? What's it like for them?

Money, meaning and freedom
10. What's enough on each of three dials: money (what comes in), meaning (work you love, with people you like, that matters to someone) and freedom (being where you want, when you want, with whom you want)? For each one: what's enough, in numbers where you can? A monthly amount, the kind of work and people, the days and hours that are yours.
11. What do you want the money for? Go through it as things, experiences, places, and the people you'd share them with. (Money is the tickets you trade in for the good stuff; the list is what makes earning it fun.)

People
12. Who are the most important people in that life, and how much time do you spend with each?
13. How do you show up for your family, your partner, your friends? What can you give them that you can't now?
14. Who are you surrounded by, and what do they have in common?

Body and mind
15. How does your body feel? What's your energy like, your health, your sleep?
16. How do you move every day? How do you eat?
17. How do you look after your head: rest, offline time, what you read, what you play?

Places, things and experiences
18. Where do you live, and where do you travel to? Describe your home, and the place you work from.
19. Is there a home base with trips out from it? Sketch it: home in the middle, the places around it, how often you're away and how often you're back, and what has to be home for (people, fixed dates, the work).
20. What are you doing that's new, the experiences you'd love to have had by then?
21. Which things would you love to own, and which don't matter to you at all?

Who you are
22. What kind of person do you have to be to live this? What do you do easily that's hard for you now?
23. Which habits are gone? Which ones got you there?
24. What did you have to get through or let go of on the way?
25. If that future you could send one piece of advice back to you today, what would it be?

**Check it with them,** one at a time and briefly:
- Is this really yours, or partly what somebody else wants for you?
- Is it specific enough to picture? Where's it still vague?
- Does it excite you, and scare you a little? If it doesn't, is it big enough?
- Is there anything in there you'd actually be relieved to drop?
- The twenty-year test: if you knew you'd be living and working this way for twenty years, would you keep it like this? And if any way of doing it was guaranteed to work out, is this still the way you'd pick? Wherever the answer is no, change it now, while it's only words.
- Have you decided to be the person who lives this, starting now? Not at a certain income or once you feel ready: acting like that person is a decision, and the income and the confidence tend to follow it. Waiting costs the one thing you can't earn back, time.
- Does it fit how you're wired: how you recharge (alone or with people), whether you'd rather talk or write, think in logic or in pictures, what you're truly good at? A life built on your strengths feels light; one built on your weak spots stays heavy however hard you push.

**What it makes.** In their `map.md` (or the file it points to), with their yes:
- **Its name:** what they call their vision, on the `Name:` line (see Their own name for it, above). Or not yet; ask again when the layer closes.
- **A day in that life:** one day, written from their answers in the present tense, with their real details (places, people, numbers, small habits), told like it's happening.
- **The deeper truth:** a short paragraph on what made that life possible: the mindset under it.
- **A motto:** one line they'd say to themselves on a hard day. Theirs, or from their own words.
- **What enough looks like:** the three dials in a line each, with their numbers.
- **Action steps:** three to six things they can start doing now that move them towards it, each small and concrete.

**What it hands down.** To the year: the action steps, the three or four areas of life that matter most in the vision, the numbers that are in it (what comes in, the days off, the hours worked, enough on each dial), the home base and the places, and the want list.

## 2. The year

**What it is.** What the next twelve months need to bring so the vision gets closer. A handful of big things spread over the months, not a to-do list. The order matters: rest and the things that make life good go in first, then the work that earns, then everything else fits around them. A year planned that way gets bigger work and a better life; a year planned the other way gets a full calendar and life gets the leftovers.

**Before you start.** Read the vision layer and its action steps. Have a year calendar at hand (their own, or HQ's calendar), even a rough one: a lot of this layer ends up in it.

**The questions,** in this order:

Looking back first
1. What are three wins or highlights from the past months? Not only achievements: good moments count.
2. What did you set out to do this year? Where are you on it: ahead, on track, behind?
3. How hard did you really go for it, from one to ten? And how did the results come out, one to ten?
4. If the effort and the results don't match, why do you think that is? Be straight about it: which part was in your hands?
5. What are you going to stop doing? Three to five things you'll leave behind, including what you tried and know isn't for you. (Adding things is easy; carrying everything you added is what makes a year heavy.)
6. What worked, that you'll keep doing?
7. What's new, the next step of you?

Your season
8. What season are you in: one to simplify, or one to multiply? A move, a new baby, recovering, a new job or a big change at home usually means simplify; a clear runway usually means multiply. Both are fine; planning a multiply year in a simplify season is how people break.
9. Of the three dials, money, meaning and freedom, which one do you turn up first this year? The other two still count; this one wins when they pull against each other.
10. If this year had one word as its theme, what would it be?

Life first
11. What one challenge would make this year the one you talk about later: "This was the year I…"? Hard, exciting, a little scary. Business or personal, either is fine.
12. What smaller adventures do you want this year, about one every two months: a trip, a race, a course, a concert, something with your people?
13. How much time off do you want: each week, each month, each quarter, once in the year? Where, doing what, with whom?
14. Lay out the year as home base and trips: when are you home, when are you away, where to, and what has to be home for (people, fixed dates, the work)?
15. From the want list in the vision: which things, experiences or places are you going for this year? Pick them first; later on you'll match each with the work that pays for it.
16. If that challenge, those adventures and that time off all happened, whatever happened at work, how would this year be?

Then the money
17. Where are you now: what comes in each month, how many clients or customers, how many truly free days a month?
18. Twelve months from now, what do you want those three numbers to be?
19. The line. On paper, draw a line. Under it, what comes in each month now; above it, the twelve-month number. A few words for how it feels under the line, where you are. Then a few words for how it would feel above it. Then the real question: are you deciding, now, to do what it takes to get above the line? (Not deciding is also a choice: it keeps you where you are.)
20. Of everything you did to earn this year, what actually moved the needle? What worked best, even a little?
21. What are the one or two things you'll lean on to earn next year, and how often does each need to happen to get to your numbers?
22. What do you deliver to the people who pay you, and at what rhythm?
23. What's the rhythm of a month (or a quarter)? For example one week where you go out and find the work, then three weeks to deliver, build and live, so you're not always chasing work, always delivering and always working. Which week is which?
24. For each thing you picked from the want list: what's one short, focused push of work that would pay for exactly that? When in the year does it go? (Earning for something you actually want is a lot more fun than earning in general.)
25. How much work fits before it breaks you or the quality? How many clients, projects or hours is your comfortable maximum? (Most income ceilings are really capacity ceilings.)

Money that runs itself
26. Is the money separate: one account for the business, one for you, one for tax, one for savings you don't touch?
27. When money comes in, where does it go, automatically? A starting split to make your own: tax first (what your country asks, set aside the moment it lands, weekly, never once a year), the living costs as the floor, a buffer for bad months, investing, learning and yourself, and a part that's guilt-free fun. What percentages are yours?
28. Once a month: do you know what came in, what was left after costs, and what's actually in the bank? When is that look in your calendar?

Goals
29. Three goals for the year (or the next six months), each one you can say yes or no to on a date: "by 1 March I have…", not "more money" or "be healthier".
30. For each goal: what are the first three steps?
31. What could you do every day or every week that would make it almost impossible to miss that goal?
32. What will you do in the next thirty days to get going?

Habits
33. What's the one habit that holds you back most right now? One, not seven.
34. What's the one habit you'll start, and how do you set up your surroundings so it's easy to win? (Willpower alone doesn't hold.)

The stress test
35. If you live this year as it's planned now, do you get to your numbers and your goals? If not, back to the earning part.
36. And if you live it, does anything break: your health, your relationship, your sleep? If yes, take pieces out.
37. Played out like this, how does the year end?
38. What's the block: the one thing that, if you got past it, would put you somewhere else entirely? Name it honestly (a fear, a belief, a skill, a habit, someone else's opinion). What's one way to get past it, or around it?
39. Where else might you trip up or get overwhelmed? What's not clear yet, and where do you need help?

Then let it sit. Suggest they take it somewhere they think well, talk it through with their partner and the people it touches (holidays, trips, time away), and come back to it before it's final.

**What it makes.** In `map.md`, with their yes:
- **The season, the dial and the word:** simplify or multiply, which dial goes up first, the year's theme.
- **The year at a glance:** month by month, the big things: the challenge, the adventures, the time off, home and away, the earning activities and their rhythm (the month's rhythm too), the pushes that pay for the wants, deadlines that matter.
- **The line:** where they are, the twelve-month number, the two feelings, and their decision.
- **Three goals,** each with a date, its first three steps and the thirty-day start.
- **The habit to stop and the habit to start,** with how the surroundings support it.
- **The block,** and the way past it.
- **The money system:** the separate accounts, the split in percentages, when the monthly money look is, and the comfortable maximum of work.
- Optionally: the stop, keep and start lists.

Offer to put the fixed parts into their calendar (time off, the trips, the adventures, the earning rhythm); only with their yes.

**What it hands down.** To the six-week game: the three goals and the dial that goes up first. To the ideal week: the time off and recovery that are fixed, the earning activities and how often they happen, the month's rhythm, and the habit pair.

## 3. The six-week game

**What it is.** The year is too far away to feel, and one week is too short to see anything change. In between: six weeks at a time, one simple game they can win, aimed at one of the year's goals. Six weeks of playing, with a week to set it up before and a week to look back after, so a game takes about eight weeks door to door; then the next one. Next to the games runs the long game: the way of working they could keep up for years without forcing it. Each short game is an experiment in getting better at the long one.

A good game is:
- **Simple:** one thing, one place, one kind of effort. Not every channel, every habit and every project at once. Complicated games are hard to stick at, so nobody wins them.
- **A game, not a job:** it has rules, and they're theirs. They decide what a win looks like and how it's played.
- **Theirs:** it fits how they're wired and how they do their best work, not how someone else does it.
- **Winnable:** there's a clear finish line. A win, each time they play, is three questions: was it fun, was it useful, did I learn something? Fun, useful and learning, fed back into the next round, keeps them playing; and whoever keeps playing long enough gets good.

A game can also be a setup game: six weeks to put something in place that then runs by itself, like the money split and separate accounts, a simple system for the work, or the evening routine. Keep the tools lean: start with the simplest thing that works, and only add a tool when doing without it costs more.

**Before you start.** Read the year: the goals and the dial. Have the calendar for the next eight weeks at hand. If a game just ended, start with its debrief (layer 6) and bring what came out.

**The questions,** in this order:

Picking the game
1. Which of the year's goals is this game for? (One. The others wait for their turn.)
2. What's the game, in one sentence: "For six weeks I…"?
3. Is it simple enough? What can you leave out so it's one thing, done well?
4. What are the rules: what do you do, how often, where, and what's off limits?
5. What does winning look like at the end of the six weeks? And how do you score a single day or a single try?
6. What will you keep score of? Something you do (the reps, the hours, the times you showed up) and something that comes out of it (the result). The first you control; the second follows.

Making it yours
7. Does it feel like play or like homework? If homework, what would make it a game?
8. Who are you at your best when you do this kind of thing? Two or three words, to remember on the days it's hard.
9. What fits you here: what comes easily that you can lean on?

Setting it up
10. The dates: the setup week, the six weeks, the debrief week. Into the calendar?
11. What's each week's part of it, and what goes into the ideal week to make room for it?
12. What could get in the way, slow you down or stop you? List the fears and the unclear bits now, while they're small, and pick one thing to do about the biggest.
13. Who plays along or keeps you honest?

**What it makes.** In `map.md`, under this layer, with their yes and the dates: the game in one sentence, the goal it serves, the rules, the score kept, what winning looks like, the fears and what's done about them. When a game ends, its debrief goes under it, and the next game under that.

**What it hands down.** To the ideal week: the game's weekly part and the blocks that make room for it. To the real week: what this week's part of the game is. To looking back: the score to look at each week, and the debrief at the end.

## 4. The ideal week

**What it is.** The shape of a good week, as a template the real weeks are poured into: when they work and for how long, when they recharge, the people, the movement, sleep and waking up, the offline time, time to steer. Built around their energy first and the results second. It's an aim, not a cage: hitting it most weeks, about four out of five days going as planned, is a win.

Two things carry the week: structure (knowing before the day starts what you'll work on, what not, what someone or something else does) and energy (being able to do it well). Miss either and the other is worth little.

**Before you start.** Read the year, the six-week game and their hand-downs. A blank week grid helps (on paper, or in words: day by day, morning, afternoon, evening).

**The questions,** in this order:

Where the time goes now
1. Think back over the last seven days, or look at your calendar and your phone's screen time: what are about five things you spent your time on each day, and roughly how long?
2. For each: does it earn, or move earning closer? And did it give you energy or take it?
3. Of what doesn't earn and drains you: what can simply go, what could be automated, what could someone else do? What do you want to keep because it's yours?

Love it or hate it
4. What goes on your two lists? The love list: the parts of your days and your work you love and want more of. The hate list: the parts you hate, find frustrating or just put up with, and want less of.
5. A second look at the same things, on two lines: does it work (does it get results) and does it feel easy or forced? What works and feels easy is the heart of the week. What works but feels forced needs a way that's more you. What feels easy but doesn't work is drifting. What's forced and doesn't work can go.
6. Take the hate list one by one: what's the part that feels wrong, what's the real issue under it, what are a few ideas to change it, and what's the first step? (Often it's not the thing itself but the way it's done, or who does it.)
7. Roughly, how does your week split now: how much do you love, how much do you put up with, how much do you hate? Where do you want it in one to three months? (Most of the week in the love column, a little in progress, almost nothing hated, is a very good week.)

Your energy
8. When in the day are you sharpest? When do you dip?
9. What fills you up again: what has to be in the week for you to feel good?
10. When do you want to wake up and go to sleep, every day of the week? What do the hours before sleep look like?
11. Is your best work the long, deep kind (building, writing, designing, thinking) that needs hours without interruptions? Or the short, many-people kind (calls, check-ins, answering, deciding) that runs in small slots? Most people are mostly one; the week should give that one room and keep the other out of its way.

The ingredients
12. What would make a week great? Make the list freely first: the places, the people, the food, the moving, the making, whatever it is. Then go kind by kind so nothing's missing:
   - **Recharge:** movement, rest, people, play, being outside, being offline.
   - **Earning:** the work that brings money in (from the year).
   - **The work itself:** what you deliver for the people who pay you.
   - **Admin:** mail, messages, bills, scheduling, the house.
   - **Steering:** time on your life and work instead of in it: planning, learning, looking back, deciding.
   Where something fits two kinds, they choose by how it feels to them.

Squeezing the week
13. Take a blank week and cross out the days you don't want to work. Then, on the days that are left, cross out the hours you don't want to work: when do you start, when are you done? What's left is your working time.
14. Could it be less, in tighter blocks? Work stretches to fill the time it's given, and most weeks hold plenty of time at work that isn't really work. With less time, what you do with it gets serious.
15. What's your hour really worth? Take what you earn in a year after tax and divide it by about two thousand working hours. Anything that can be done by a tool, an automation or someone else for well under a quarter of that, you're paying too much to do yourself. Which tasks are those, house and life admin included? (If paying for help isn't possible yet, pair the dull physical jobs with something to listen to and learn from.)
16. The two-days test: if you could only work two days a week from now on, what would you still do? And if it were two hours a week? Whatever survives is what moves the needle. Of the rest: what goes, what gets automated, what someone else could do?

Placing it
17. Big things first, then the medium ones, then the small stuff: put the small stuff in first and the big things never fit. Recharge and earning are the big things. Where in the week do they go, on which days and at what times?
18. Where does the work itself go, in which fixed windows, so it doesn't spill over everything? Is there one deep block of three or four hours, early, when your head is freshest, for the work that pays off most?
19. Working in it and working on it: in is delivering, researching, admin; on is improving how you work, your skills, your systems, your direction. At least about a fifth of the working week goes to on, roughly one day, booked before anything else. Which day?
20. One hat per day: the energy for finding work, for deep work, for people and for admin is different, and switching between them all day is what makes days feel scattered. Which days get which hat? Which days are fully off?
21. Similar work together: batch by kind of task (all the research on one day, all the making on the next) rather than a bit of everything every day. Does that fit how you work?
22. When's admin? One block a day, or one day for it, so it doesn't leak through the whole week.
23. Within the time on it: where's the fixed moment to plan the coming week, and a little time to learn and decide?
24. Where's the game's weekly part?
25. Where's the margin, the empty space for when a day goes differently? Things take longer than we think: add about a third to every estimate, more if you're usually off.

The rules of the house
26. Interruptions: what's off while you work? Notifications on the laptop, the phone on silent and out of sight, ideally in another room, one thing open at a time, a closed door that the people at home understand.
27. Fully in or fully out: when you work, you really work; when you rest or play, you really do. Where does your week slide into the grey middle (scrolling, working with the TV on, half-resting while half-answering mail)?
28. The energy basics: when's bedtime and wake-up, the same every day? When's your last coffee (about ten hours before bed)? Real food most of the time? Thirty to sixty minutes of moving every day, and enough steps?

The check
29. Looking at the whole week: does it fit the year and the game, and does it look like the life in the vision, already a little?
30. Is it too full? What would you take out first?

**What it makes.** In `map.md`, with their yes:
- **The week, day by day:** waking up and bedtime, the working days and hours (what's crossed out), the blocks in order with their times and their kind, each day's hat, which days are off.
- **The rules of the week** in a few lines: work hours, the deep block, the day for working on it, the offline times and what's off while working, the admin block, bedtime and wake-up, when the week is planned.
- **The love list and the hate list,** with the first step for each thing on the hate list, and where they want the split to be.
- **The keep, drop, automate and hand-off list** from the time questions, what their hour is worth and the two-days test, with what to do about each.

Offer to set the template up as recurring blocks in their calendar; only with their yes. Things to automate or hand off, and the first steps from the hate list, can go on their to-do list.

**What it hands down.** To the real week: the template itself, the fixed moment the week is planned, and the weekly part of the year's goals and the game.

## 5. The real week

**What it is.** This week, in the calendar and on the to-do list, poured into the ideal week. The template meets real life: appointments, deadlines, the things that came up. Important but not urgent goes first, because that's where the vision lives; the rest fits around it. A deadline gets a slot well before its date.

**When.** At the fixed planning moment from the ideal week, about thirty to sixty minutes, ideally relaxed. Start each time from looking back (layer 6) at last week.

**The questions,** each week:
1. What's already fixed this week: appointments, other people, travel?
2. Where does that bend the ideal week, and how do we bend it back as close as we can?
3. What are your three focuses this week: the three things that, if they're done, make it a good week? Do they serve the year's goals and the game?
4. What's this week's part of the game, and where does it go?
5. On the to-do list: what's important but not urgent? Which of those gets a slot this week?
6. Which deadlines are coming, and where's their slot, well before the date?
7. Is recovery in first: sleep, movement, the people, the time off?
8. Does each day still have one hat, or did the week mix them? Can we sort it?
9. What's this week saying no to?
10. Looking at the whole week: does it pull away from the vision anywhere? (If it does, say so once, plainly, and let them decide.)

**Each evening,** the last few minutes of the day (the daily look in layer 6): tomorrow written as a script, every block with a start and an end time, not a loose to-do list.

**What it makes.** The week in their calendar (on their yes) and the three focuses in `map.md`, under this layer, with the week's date.

**What it hands down.** To looking back: the week as planned, so next time what happened can be held up against it.

## 6. Looking back

**What it is.** The step that keeps the map alive. Each day a short look, each week a proper one, a debrief after every game, and every few months a bigger check-in. This is where the ideal week, the game and the year get adjusted, so the plan learns. The vision only changes when they say so.

**Each day,** five to ten minutes, in the evening, ideally on paper:
1. What were the three best things about today: wins, good moments, things you're grateful for?
2. What didn't happen as planned, and why, in one line?
3. Empty your head: everything still buzzing, written down so it's out (it can go on the to-do list).
4. What's the one thing tomorrow is for? Then script tomorrow: the blocks in order, each with a start and an end time.
On a busy day the short version is fine: the three best things and tomorrow's script.

**Each week,** before planning the real week, thirty minutes or so:
1. What were the wins last week? What are you proud of?
2. What didn't get done, or got skipped? (If they tick off and cross out their calendar, use that: what's ticked, what got an X, what's not marked.)
3. Is there a pattern? Which kind of block keeps slipping, on which day, at what time?
4. Effort and results this week, one to ten each. If they're far apart, why?
5. The money, once a month (the first week of the month): what came in, what was left after costs, what's in the bank, is the tax put aside, did the split happen?
6. The game's score this week: what did you do, what came out of it? Fun, useful, learned something?
7. What will you change: in the ideal week (a block moved, made smaller, dropped), in how you plan, in the game, or in the year?
8. Then on to the real week (layer 5) with the three focuses.

Keep a short weekly note somewhere that lasts (a journal, or under this layer), so a year from now you can read back how it went. And have someone who sees your numbers or your week: a friend, a group, a coach. Plans hold much better when someone checks in; on your own, life tends to creep back in after two or three weeks.

**After every game,** in its debrief week, half an hour to an hour:
1. How did it go, for the result and for you? Did you win, by your own rules?
2. Was it fun, was it useful, what did you learn?
3. What worked, and what didn't? (Some experiments flop; that's what experiments are for.)
4. What do you keep, what do you change, what do you drop?
5. Is the long game still the right one: could you keep doing this for years without forcing it?
6. What's the next game? Then back to layer 3.

**Every three to six months,** an hour, the check-in, in three steps:
1. What: look honestly at how it's going. Go back through the year's looking-back questions (wins, the goals, effort and results, stop, keep, start) and the line: where are you now?
2. So what: what does that mean for you? Make the love list and the hate list again; is the week moving towards the love column? Is the season still the same, simplify or multiply? Is the dial you turned up still the right one?
3. Now what: what will you do about it? Adjust the year, the game, the ideal week. Give a new approach about three honest tries before you change it; and ask of everything in the plan: is it working, and does it work for me, for who I am and the season I'm in? Then the twenty-year test once more: would you keep running your life and work like this for twenty years?

**Once a year,** read the vision together. Is it still theirs? Only they decide if it changes.

**What it makes.** Short notes per look under this layer in `map.md` (date, what came out, what changes), each game's debrief under the game, and the changes themselves in the layer they belong to, on their yes.

**What it hands back up.** The changes to the ideal week, the game and the year, and, only when they say so, to the vision.

## In short

Every layer: every question on the checklist, marked answered, parked, later or open, and checked against this guide before it's done. Vision: the why, its own name, a day in that life, the deeper truth, a motto, what enough looks like on the three dials, home base and trips, the twenty-year test, a few action steps. The year: look back, the season and the dial, life first (the challenge, adventures, time off, home and away, the wants), then the money (the line, the rhythm of the month, a push for each want, capacity, money that runs itself), three dated goals, one habit out and one in, the stress test and the block. The six-week game: one simple game you can win, your rules, a score, a win is fun, useful and learned, a debrief. The ideal week: where the time goes, the love and hate list, what works and what feels forced, their energy, the ingredients, the week squeezed, what an hour is worth and the two-days test, one hat per day, a deep block and a day on the business, recharge and earning first, margin, the rules of the house and the energy basics. The real week: the template meets this week, three focuses, the game's part, important but not urgent first. The real week also gets tomorrow scripted each evening. Looking back: the evening look and tomorrow's script, a monthly money look, weekly proper, a debrief after each game, a check-in every few months, and it changes the layers above.
