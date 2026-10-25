# Mail to check

> **Private.** Only for this workspace.

New mail that might need something from the user, waiting for their yes. Days can stack up; that's fine. Built for Gmail through Claude's Gmail connector; with another mail provider, Claude has to find out whether it's supported and build its own version.

Two sections, one writer and one reader. The hourly mail check writes them; the start of every chat and every call (Quick and Deep, not Free) reads them, the "Very important" section first.

## The mail check

Runs every hour, started by HQ's routine on the computer, hidden. Only reads mail and changes this file.

1. Search Gmail (the Gmail connector) with `after:<marker>`, using the epoch seconds of the marker below. Only mail newer than the marker counts; never rescan older mail. When the marker isn't set yet (a fresh install), look at the last 7 days.
2. Keep what might need something from the user: a person writing to them, a bill, payment or money matter, a deadline, an appointment, their work, their health care, the government, their home, the people in `me.md`, or an account or security warning. Skip newsletters, ads, promotions and notifications that ask nothing. Skip what's already in challenges.md or current-situation.md, unless the mail adds something new (then say what's new).
3. Judge each kept mail: is it very important (see below)? Very important → one line under "Very important". Everything else → one line under "To check", under a heading with the date of the check.
   - "To check" line: received date, sender, subject, one plain line on what it is and what it might ask of them, and the Gmail link.
   - "Very important" line, exactly this shape, so every chat and call can read it: `- <received date> · <sender> · <subject> · <one plain line on what it is and what it asks of them> · Why: <which rule below, in a few words> · Status: new · [Gmail](<link>)`
4. Never remove or shorten a line under "Very important": it stays until the user resolves it. A new mail about an item that's already there goes into that same line.
4b. One event, one line (H248): a login, a parcel, a payment is one line, however many mails it came in. Mails from the same sender about the same thing within 30 minutes (or about the same order, parcel, payment or sign-in) go in one line that says how many and when each came in, e.g. `(2 mails, 01:52 and 01:52)`. A later mail about an event already here goes into its line, keeping the line's first three parts as they are. A mail about an event under "Closed" (already answered) is skipped, unless it asks something new with a date.
5. Move the marker to the newest mail seen (also when nothing was kept): epoch seconds plus the readable date and time.
6. Never send, reply, forward or draft, and never label, archive, trash or mark mail as read. The one exception: a sorting rule agreed on a call or in the texts (HQ's mail sorting rules, H213) adds its label and archives if it says so, only for new mail that fits it, with a line for each.

## What counts as very important

[A starting point; change it to your own.] A kept mail is very important when at least one of these is true:

- Money with a date or a cost: a payment, reminder or collection notice, a fine, a charge they didn't expect.
- A deadline or appointment within the next two weeks.
- Their work or employer, or anything about their salary.
- Their health care: a doctor, a clinic or a referral.
- The government asking them to do something.
- A person waiting for their answer: a client, a partner, family.
- A security warning they can't place: a sign-in, a password reset or a new device they didn't do.

Everything else that might need them goes under "To check".

## Reading it at the start

At the start of a chat: tell them in plain words, the "Very important" items first, every time. Then what's under "To check". At the start of a call: name the "Very important" items in the first reply, after answering what they said; the rest only when they ask.

After their answer:

- "To check": only after they confirm an item, write it into the right place (see where-things-go.md), then remove it from here.
- "Very important": when they confirm it, write it into the right place and change its status to `Status: on the list`; it stays here. It goes only when they say it's resolved or that it's not that important. One line in the log either way.
- When they answer a line ("that's me", resolved) and it's taken out, it gets one line under "Closed": `- <date> · <sender> · <subject> · <the answer in a few words>`, so the mail check doesn't flag the same thing again. Lines there older than 3 days may go.

Marker: not set yet (the first mail check sets it)

## Closed

Events already answered (H248), so a later mail about the same thing isn't flagged again. Kept 3 days.

## Very important

Stays here until the user says it's resolved or not that important.


## To check
