Run the hourly mail check for the user's private workspace: {WORKSPACE}

[Started by the HQ Routine helper (phase L, L8, 9 October 2026), hidden in a Terminal window that closes itself when this is done. Nobody is watching: never wait for a yes.]

1. Read {WORKSPACE}/inbox.md with the Read tool. Its section "The mail check" holds the exact steps and the marker (epoch seconds of the newest mail already checked), and "What counts as very important" holds the rules for judging each mail. Follow those exactly.
2. To skip what's already known, read challenges.md and current-situation.md in the same folder (Read tool, never cat).
3. Use the Gmail connector (search_threads with the query `after:<marker epoch seconds>`, get_thread only when the snippet isn't enough). Account: the one the Gmail connector is signed in to (inbox.md may name it). If nothing is newer than the marker, stop: change nothing, commit nothing.
4. Judge every kept mail. Very important ones go under "## Very important", one line each, in exactly the shape inbox.md gives (ending in `Status: new` and the Gmail link), because every chat and every HQ call reads that section by its shape. The rest go under "## To check", under a heading with today's date (add to that heading if it already exists). Never remove or shorten anything already in either section: items stay until the user resolves them. Move the marker to the newest mail seen, even when nothing was kept. Keep the section headings exactly as they are.
5. If inbox.md changed, commit and push it with exactly this one Bash command, run from the folder itself, nothing added before or after it (no `cd`, no `&&`), so it matches the pre-approved permission and nobody gets asked:
   `sh .claude/mail-commit.sh`
   Never run git commands yourself. If the script fails, leave the change in the file; the next chat will commit it.

Hard limits: never send, reply, forward or draft email; never label, archive, trash or mark mail as read. Change no file other than inbox.md. Everything here is private and sensitive: don't copy any of it anywhere outside this folder and its private GitHub repo. No need to message anyone; the result is the updated inbox.md. End with one short line saying what changed (or that nothing was new).
