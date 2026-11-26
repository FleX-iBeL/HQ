# The takeover: the new HQ in the old one's place

This code replaces the old HQ on both computers. It runs with the old HQ's names, folders and ports, so nothing around it
has to change: the Mac app, the phone app, the helper, the units and the phone list all stay as they are.

## What the switch does

The switch is the same on both computers. HQ's folder goes from the old code to this code with git, and HQ starts again.
The workspace is not touched, because both versions read and write the same files. The same goes for HQ's own memory
(`~/Library/Application Support/HQ` on the Mac, `~/.local/state/hq` on Linux): the push keys, the role and the pairing
stay. So the phones that signed up for pushes keep getting them, from the same keys and the same list.

On the laptop, which is the backup:
- The call line and the status server are stopped with the old stop script and by their saved pids.
- `git switch dev` follows, with the new code on dev.
- `app/start.sh` brings the call line back on 7860, with the phone on 8443.
- `status/phone.sh` brings the status server back on 4748, with the phone on 8444.
- The HQ Routine helper keeps running `routine/tick.py` every minute. It doesn't change and isn't rebuilt.
- The old Mac app keeps its tabs on 4748 and 7860. Both now show the new app, because the status server passes every page to the call line.

On the server, which is the main:
- The `hq-routine` and `hq-watchdog` timers are stopped.
- Then come `app/stop-linux.sh`, the status server by its pid, and `git pull --ff-only origin dev`.
- `hq-start` is started again, and with it the call line on 7860 and the phone on 8443. The status server on 4748 and 8444 comes back too.
- The timers are started again. The units are unchanged.

What the routine does every minute (`routine/tick.py`):
- The mail check.
- Reminders, nudges and watches (`pings.watch`), plus Donna's look and the game texts.
- Travel and the weather.
- The sync and the hand-over between the two computers, the heartbeat and Tailscale.
- The 3-hour log cycle and the laptop's readings.
- The phone keep-alive and the watchdog check.
- The usage and the extensions.

It doesn't do the team, the job queue, the nights, the reviews, the sprint, news or feedback. Those parts are left
behind, and their old lines on the status page are closed the first minute (`gone_lines`).

`HQ_BESIDE=1` still runs a copy next to a working HQ, on 7870/4758. It uses its own memory in `scratch/support`, without
the phone and without pushes. `tools/test_instance.sh` runs a third copy on 7872/4759 that never texts, writes or reaches
outside.

## The way back

`before-hq2` tags the old HQ's last commit, on GitHub too. To put a computer back, run this in its HQ folder:

    bash tools/back_to_old.sh

It stops this HQ by its saved pids and puts the code on the branch `old-hq` at `before-hq2`. Then it starts the old call
line and status server; on Linux it does that through `hq-start`. The other computer stays as it is. To come back to the
new code: `git switch dev`, then start it again (`app/start.sh` and `status/phone.sh` on the Mac, or
`systemctl --user restart hq-start.service` on Linux).
