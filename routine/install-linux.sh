#!/bin/sh
# H56.1 (12 October 2026): HQ's helper and watchdog on a Linux server, as systemd user units. What the Mac
# does with the HQ Routine helper app, its LaunchAgent and the watchdog's LaunchAgent:
#   <U>-routine.timer    every minute on the minute: <U>-routine.service runs routine/tick.py once (no Claude)
#   <U>-start.service    at the start of the server: app/start-linux.sh, the call line (the helper's "on run")
#   <U>-watchdog.timer   every 5 minutes on the five-minute marks, and a minute after the start:
#                        <U>-watchdog.service runs routine/watchdog.py, which starts or restarts the helper
# <U> is "hq", or HQ_UNIT. Every HQ_* setting in the environment when this runs goes into the units
# (e.g. HQ_SUPPORT, HQ_WORKSPACE, HQ_PORT, HQ_STATUS_PORT, HQ_NO_PHONE, HQ_CALL_FIX), so a second HQ on one
# server gets its own units, memory and ports. Lingering is switched on for the user (through sudo -n when
# needed), so the units run without anyone logged in and start by themselves after a restart.
#   routine/install-linux.sh             install (again), and start the timers
#   routine/install-linux.sh --no-start  install and enable, start nothing now (no call line either)
#   routine/install-linux.sh --dry       print the units, change nothing
#   routine/install-linux.sh --remove    stop and remove this HQ's units
# Run again after moving HQ. Logs: scratch/routine/routine.log, scratch/launchagent.log, and the
# watchdog's own log in HQ's memory folder (~/.local/state/hq/watchdog.log, or HQ_SUPPORT).
set -e
HQ="$(cd "$(dirname "$0")/.." && pwd)"
U="${HQ_UNIT:-hq}"
DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
PY="$(command -v python3)"
MODE="${1:-}"
if [ "$(uname)" = Darwin ]; then echo "This is the Linux one; on a Mac the helper app and install-watchdog.sh do this."; exit 1; fi

units() { echo "$U-routine.service $U-routine.timer $U-start.service $U-watchdog.service $U-watchdog.timer"; }

if [ "$MODE" = --remove ]; then
  systemctl --user disable --now "$U-routine.timer" "$U-watchdog.timer" "$U-start.service" 2>/dev/null || true
  systemctl --user stop "$U-routine.service" "$U-watchdog.service" 2>/dev/null || true
  for f in $(units); do rm -f "$DIR/$f"; done
  systemctl --user daemon-reload
  echo "Removed: $(units)"
  exit 0
fi

# The settings for every unit: PATH (where claude and node are), and every HQ_* setting given now.
EXTRA_PATH="$HOME/.npm-global/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
envlines() {
  echo "Environment=PATH=$EXTRA_PATH"
  echo "Environment=LANG=${LANG:-C.UTF-8}"
  echo "Environment=HQ_UNIT=$U"
  env | grep '^HQ_' | grep -v '^HQ_UNIT=' | sort | while IFS= read -r kv; do echo "Environment=\"$kv\""; done
}

write() {  # write <name>: the unit's text on stdin
  if [ "$MODE" = --dry ]; then echo "### $1"; cat; echo; else cat > "$DIR/$1"; fi
}
[ "$MODE" = --dry ] || mkdir -p "$DIR" "$HQ/scratch/routine"

write "$U-routine.service" <<EOF
[Unit]
Description=HQ routine: one look at the queue, the status page and the call line (routine/tick.py)

[Service]
Type=oneshot
WorkingDirectory=$HQ
$(envlines)
ExecStart=$PY $HQ/routine/tick.py
StandardOutput=append:$HQ/scratch/routine/routine.log
StandardError=append:$HQ/scratch/routine/routine.log
TimeoutStartSec=15min
# What a run starts (the status page, the call line) keeps running after the run ends; only tick.py itself
# is ended when the run is stopped.
KillMode=process
EOF

write "$U-routine.timer" <<EOF
[Unit]
Description=HQ routine every minute (the Mac's HQ Routine helper)

[Timer]
OnCalendar=*-*-* *:*:00
AccuracySec=1s
Unit=$U-routine.service

[Install]
WantedBy=timers.target
EOF

write "$U-start.service" <<EOF
[Unit]
Description=HQ: start the call line when the server starts (app/start-linux.sh)
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$HQ
$(envlines)
ExecStart=/bin/bash $HQ/app/start-linux.sh
StandardOutput=append:$HQ/scratch/launchagent.log
StandardError=append:$HQ/scratch/launchagent.log
TimeoutStartSec=3min
KillMode=process

[Install]
WantedBy=default.target
EOF

write "$U-watchdog.service" <<EOF
[Unit]
Description=HQ watchdog: starts the routine again when it's gone or stuck (routine/watchdog.py)

[Service]
Type=oneshot
$(envlines)
ExecStart=$PY $HQ/routine/watchdog.py
TimeoutStartSec=2min
EOF

write "$U-watchdog.timer" <<EOF
[Unit]
Description=HQ watchdog every 5 minutes, and a minute after the start

[Timer]
OnCalendar=*-*-* *:00/5:00
OnStartupSec=1min
AccuracySec=1s
Unit=$U-watchdog.service

[Install]
WantedBy=timers.target
EOF

[ "$MODE" = --dry ] && exit 0

# Lingering: the user's units run without a login, and start at boot.
if [ "$(loginctl show-user "$USER" -p Linger --value 2>/dev/null)" != yes ]; then
  sudo -n loginctl enable-linger "$USER" 2>/dev/null \
    || echo "Couldn't switch on lingering: run once:  sudo loginctl enable-linger $USER"
fi
systemctl --user daemon-reload
systemctl --user enable "$U-routine.timer" "$U-watchdog.timer" "$U-start.service" >/dev/null
if [ "$MODE" != --no-start ]; then
  systemctl --user start "$U-start.service" "$U-routine.timer" "$U-watchdog.timer"
fi
echo "Installed: $(units)"
echo "The routine runs every minute and the watchdog every 5 minutes, also after a restart of this server."
