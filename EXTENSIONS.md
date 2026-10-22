# Extensions: build your own on your HQ

Anyone can add to their own HQ: a connector for another mail app, a routine that looks something up every hour, a new kind of text from their agent, extra rules for calls. These are **extensions**. They live in the workspace, in `HQ/extensions/`, one folder each. HQ's repo never contains them and an update never touches them. After every update HQ checks, on that computer, whether anything you added might clash with the new version, and tells you in plain words.

**HQ's version leads.** An extension adds to HQ; it never replaces HQ's own files, rules or kinds of texts. When HQ later does the same thing itself, HQ's version counts, and the check after the update says so, so you can decide whether to keep yours.

This page is written for the Claude that runs someone's HQ.

## What an extension looks like

```
HQ/extensions/
  apple-mail/
    extension.json     what it is (needed)
    call.md            extra rules for calls (optional)
    text.md            extra rules for the agent's texts (optional)
    mail.md            extra steps for the hourly mail check (optional)
    read_mail.py       its own scripts and routines (any number)
```

`extension.json`, with only `name` and `what` needed:

```json
{
  "name": "Apple Mail",
  "what": "Reads the Mail app on this Mac, so the mail check also sees mail that isn't in Gmail.",
  "on": true,
  "scripts": {
    "read": {"run": "read_mail.py", "what": "the new mail since a date, one line each", "mail": true}
  },
  "routines": {
    "alerts": {"run": "alerts.py", "every": 3600, "what": "looks for new job alerts every hour"}
  },
  "texts": {
    "job-alert": "A new job alert came in that fits what they look for (the facts say which). One short line, what and where."
  },
  "uses": ["routine/mail-check.md"],
  "keywords": ["Apple Mail"]
}
```

- **what**: one plain line on what it does. Calls, texts and the check after an update use it.
- **on**: `false` keeps it in the folder but HQ ignores it.
- **scripts**: commands a call, a text or the mail check may run, as `python3 <HQ>/app/extensions.py run <extension> <script> [args]`. Only scripts named here run. `"ask": true` makes a call ask for a yes first; `"mail": true` lets the mail check run it (only then, and only that script).
- **routines**: run by HQ's routine on the main HQ, each at its own `every` (seconds, at least 60), one at a time, at most ten minutes per run. Their output goes to `scratch/extensions/<extension>-<routine>.log`. They show as one line, Your own routines, on the status page.
- **texts**: your own kinds of texts from the agent. A script or routine sends one with `$HQ_TEXT <kind> "<facts>"` (the environment gives it), the agent writes it in her own words from what the kind says it's for. HQ's own kinds come first: a kind with the same name as one of HQ's is never used.
- **uses**: HQ's files this extension relies on (paths inside HQ). The check after an update also finds them by itself when the extension's own files mention them, so this is for what it can't see.
- **keywords**: words that would show up in HQ's changelog if HQ started doing the same thing; the name counts too.

Scripts and routines run in their own folder, with `HQ_ROOT` (HQ), `HQ_WORKSPACE` (the workspace), `HQ_EXTENSION` (their folder) and `HQ_TEXT` set. `.py` runs with Python, `.sh` with sh, anything else as it is. Keep what they write inside the workspace.

`python3 app/extensions.py` lists them, what each does, and anything wrong with one. `rule call`, `rule text` and `mail` show exactly what calls, texts and the mail check will read.

## Where HQ reads them

| Fixed point | When | From |
|---|---|---|
| The call rules | at every call start | each extension's `call.md` and its scripts |
| The text rules | at every text | `text.md` and its scripts |
| Kinds of texts | when the agent texts | `texts`, after HQ's own |
| The mail check | every run | `mail.md`, its scripts with `"mail": true` |
| Routines | every minute, each at its own `every` | `routines` |
| Scripts | when a call, text or the mail check runs one | `scripts` |

HQ's own rules and hard limits always come first: an extension can't make the mail check send or change mail, or a call skip asking for a yes.

## After an update

Every update runs a check on that computer (and the routine runs it again within a minute, so an update started by an older HQ is checked too). An extension might clash when:

- it uses or mentions a part of HQ that the update changed,
- HQ now has its own kind of text with the same name,
- HQ just added a file named like one of the extension's scripts or routines,
- its name or keywords show up in what's new.

When something might clash, the version bar on the call page and the status page says so in plain words, with two buttons: **Talk it through** (a text to their agent, who answers in the texts) and **Send to the team** (a roadmap row and a job for their team to fix it), and × for it's fine. Calls and texts know about it until it's settled. The note in `updates/<version>.md` gets a section for their Claude, too. The result is kept in `.status/extensions-check.json`; `python3 app/extensions.py clash` shows it.

Fixing one: make it work with the new version **inside its own folder**, never in HQ's files. Then `python3 app/extensions.py check app/<the changed file> …` (with the files the update changed) should say nothing might clash.

## Moving what's already built into HQ's own files into an extension

Before extensions existed, some HQs had their own connectors built straight into HQ's files: an extra step in `routine/mail-check.md`, new files next to HQ's in `app/` or `routine/`, a new kind of text added to `app/direct_line.py`. An update then saves those changes on a backup branch and puts HQ's own version back, so they stop working. To move them:

1. Find what was built: `git -C <HQ> branch --list 'hq-backup/*'` and the note in `updates/`; `git diff <version tag> <backup branch>` shows exactly what changed in HQ's files, and new files of their own show as added.
2. Make one folder per thing it does in `HQ/extensions/` (a mail connector, a job-alert routine), with its `extension.json` and a line on what it does.
3. Move the new files (`app/apple_mail.py`, `routine/jobalerts.py`, …) into that folder. Where they imported HQ's modules, add `sys.path.insert(0, os.path.join(os.environ["HQ_ROOT"], "app"))` first, and list those files under `uses`.
4. Steps added to HQ's mail check go into the extension's `mail.md`, written as a step; the commands they ran become `scripts` with `"mail": true`.
5. Job types or kinds of texts added to HQ's code become `texts`; something that ran on a timer becomes a `routine`.
6. Put HQ's own files back as the release has them: `git -C <HQ> status` should show nothing changed outside `local/`.
7. Check it: `python3 app/extensions.py` (no problems), `python3 app/extensions.py mail` and `rule call` read right, a script runs with `run`, and one mail check or call uses it. Then tell the person in a sentence or two what moved and that updates won't break it any more.

Parts that stand in for HQ's own on a computer that isn't a Mac (the Terminal window, starting at login) stay in `local/`, as INSTALL.md says. Extensions are for what's added on top.
