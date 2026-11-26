# HQ2

HQ is a voice-first assistant: you call Donna, Pepper or Moneypenny, or text them, and they keep your calendar, to-do
list, bucketlist and wishlist, life coaching map and six-week games, and tell you what needs you in your mail. HQ only
does what you ask; nothing in it builds or runs work by itself.

- `app/` the call line (`app/bot.py`): the voice pipeline, the agents, the call rules, the app's API; `app/start.sh`
  and `app/stop.sh` start and stop it with the status server.
- `routine/` the every-minute routine (`routine/tick.py`) and the scripts it and the calls use.
- `status/` the status server (`status/server.mjs`).
- `web/` the app's page, served by the call line at `/`.
- `tests/` the tests (`python3 tests/run.py`), `tools/test_instance.sh` a safe instance on a copy of the workspace.
- `API.md` every endpoint the page uses; `MOVED.md` what came over from HQ and what didn't.

Your own data lives in `workspace/` (a link to your folder), never in HQ. See INSTALL.md to set it up and EXTENSIONS.md
to add your own parts.
