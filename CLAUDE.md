# HQ

HQ is the app: a live voice call with Claude (the call line), a job queue the computer runs by itself (the routine), a watchdog, and a status page. The same code for everyone. Still in development. To install and check it: `README.md` (written for the user's Claude, including what's Mac-only and the mail and calendar connectors). What HQ is, how it works, the agents and what's coming: `ABOUT.md`; use it to explain HQ to whoever asks.

## Layout

- `app/` the call line (Pipecat, Whisper, Kokoro, Claude through the Agent SDK), its call page in `app/web/`, and the happy flows (`app/happy_flows.py`).
- `routine/` the helper's every-minute routine (`tick.py`), the queue (`jobs.py`), the watchdog, the hourly mail check, the laptop readings.
- `status/` the status page (`server.mjs`, port 4748).
- `workspace/` the user's own files. Never part of this repo (`.gitignore`). HQ reads them through it: `routine/hqpaths.py`, `status/paths.mjs` and `app/config.py` all say the same: the workspace (or `HQ_WORKSPACE`), resolved; the roadmap with its status block and queue at `workspace/HQ/roadmap.md` (or `HQ_ROADMAP`); the call transcripts in `workspace/HQ/calls/`.
- `template/` the blank workspace HQ ships (M2): the same files the app reads from a workspace, each saying "put your own things here" (`me.md`: the name, what's important, what HQ should manage), and the coaching skill without anything personal. The installer copies it into `workspace/` on a fresh install. Happy flow 41 checks it stays blank and readable.
- `install/` the installer (M4): `install.py` (two rounds, setup then a test that asks nothing; standard library only) and `checklist.html`, the live checklist on :4749 and on the status page at `/install`. Happy flow 43 runs it in a throwaway copy, simulated.
- Runtime, per machine and never in the repo: `scratch/` (logs, the routine's state), `.status/` (readings for the status page), `.venv/`, `models/`.

Git: commits for the user's files go through `routine/gitlock.py`, which runs git in the workspace. The HQ repo itself is committed separately.

Never stop processes by a loose name pattern; only by their exact pid.
