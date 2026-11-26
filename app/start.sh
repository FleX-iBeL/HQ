#!/bin/zsh
# HQ: start the call line (app/bot.py) and the status server (status/server.mjs) on this computer.
#   app/start.sh        starts both in the background (and keeps the computer awake while the call line runs)
#   app/stop.sh         stops both, each only by the pid saved here when it was started
# The app's page: http://127.0.0.1:7870 (HQ_PORT). The status server: http://127.0.0.1:4758 (HQ_STATUS_PORT); the page
# reaches it through the call line, at /status/... there.
# Settings (environment variables), e.g.  HQ_MODEL=haiku app/start.sh
#   HQ_PORT, HQ_STATUS_PORT       the two ports (7870 and 4758)
#   HQ_PHONE=1                    also put both on the phone through Tailscale serve, on HQ_TS_CALL_PORT (8453) and
#                                 HQ_TS_STATUS_PORT (8454); off by default
#   HQ_ROLE_READ=DIR              read the pairing and the role (main or backup) from another HQ's memory in DIR, never
#                                 writing there; by default the HQ memory next to this one (Application Support/HQ) when
#                                 this HQ has no pairing of its own, so a write on the backup still goes to the main
#   HQ_SUPPORT=DIR                this HQ's own memory (default: scratch/support inside this HQ while it's tried out)
#   HQ_UPDATE_LOOK=0              no look on GitHub for a newer version in the background (default 0 here)
#   HQ_BESIDE=1                   next to the current HQ on this computer (the default): see below
#   HQ_MAPS_KEY_FILE, HQ_FIX_DRY  the maps key's file (a test's own), Turn everything on only says what it would do
#   HQ_MODEL=haiku, HQ_PLAIN=1, HQ_WRAP_UP=off    as before: another model, the plain Claude, no after-call work
#   HQ_WORKSPACE, HQ_PID_FILE, HQ_LOG, HQ_STATUS_PID_FILE, HQ_STATUS_LOG, HQ_DIRECT_DRY, HQ_NO_OUTSIDE, HQ_STATUS_TRIAL,
#                                 HQ_TODO_UNDO, HQ_LISTS_UNDO, HQ_GAMES_UNDO
#                                 a second instance on a copy of the workspace (tools/test_instance.sh sets these)
cd "$(dirname "$0")/.." || exit 1
ROOT="$PWD"
PORT="${HQ_PORT:-7870}"
SPORT="${HQ_STATUS_PORT:-4758}"
TS=/usr/local/bin/tailscale
TS_CALL="${HQ_TS_CALL_PORT:-8453}"
LOG="${HQ_LOG:-$ROOT/scratch/server.log}"
PIDFILE="${HQ_PID_FILE:-$ROOT/scratch/server.pid}"
SUPPORT="${HQ_SUPPORT:-$ROOT/scratch/support}"
mkdir -p "$ROOT/scratch" "$SUPPORT"
PATH="$PATH:/usr/sbin:/sbin"   # lsof is in /usr/sbin on a Mac
if [[ -z "$HQ_ROLE_READ" && ! -r "$SUPPORT/role.json" && -r "$HOME/Library/Application Support/HQ/role.json" ]]; then
  HQ_ROLE_READ="$HOME/Library/Application Support/HQ"
fi
# HQ_BESIDE=1 (the default for now): this HQ runs next to the current HQ on this computer, on the same live workspace.
# The current HQ keeps sending the texts and pushes, the mail check, the reminders and the sync; this one writes nothing
# by itself into the live workspace or the other HQ's folders (the texts' phone list, the page's reports, the weather it
# reads for the page stay in this HQ's own scratch). HQ_BESIDE=0 once this HQ takes over.
BESIDE="${HQ_BESIDE:-1}"
# Beside the current HQ, health (routines, incidents, the laptop) is read from that HQ: its routine is the one running.
if [[ "$BESIDE" == 1 && -z "$HQ_WORKSPACE" && -z "$HQ_HEALTH_ROOT" && -d "$ROOT/../HQ/.status" ]]; then
  HQ_HEALTH_ROOT="$(cd "$ROOT/../HQ" && pwd)"
fi
PY="$ROOT/.venv/bin/python"
[[ -x "$PY" ]] || PY=/usr/bin/python3
OWN_ENV=(HQ_HOST=127.0.0.1 HQ_PORT="$PORT" HQ_STATUS_PORT="$SPORT" HQ_SUPPORT="$SUPPORT" HQ_UPDATE_LOOK="${HQ_UPDATE_LOOK:-0}"
         HQ_NO_PHONE="$([[ "$HQ_PHONE" == 1 ]] || echo 1)" HQ_TS_STATUS_PORT="${HQ_TS_STATUS_PORT:-8454}"
         ${HQ_ROLE_READ:+HQ_ROLE_READ="$HQ_ROLE_READ"} ${HQ_MODEL:+HQ_MODEL="$HQ_MODEL"} ${HQ_PLAIN:+HQ_PLAIN="$HQ_PLAIN"}
         ${HQ_WRAP_UP:+HQ_WRAP_UP="$HQ_WRAP_UP"} ${HQ_CALLS:+HQ_CALLS="$HQ_CALLS"} ${HQ_LABEL:+HQ_LABEL="$HQ_LABEL"}
         ${HQ_WORKSPACE:+HQ_WORKSPACE="$HQ_WORKSPACE"} ${HQ_STATUS_PID_FILE:+HQ_STATUS_PID_FILE="$HQ_STATUS_PID_FILE"}
         ${HQ_STATUS_LOG:+HQ_STATUS_LOG="$HQ_STATUS_LOG"} ${HQ_DIRECT_DRY:+HQ_DIRECT_DRY="$HQ_DIRECT_DRY"}
         ${HQ_NO_OUTSIDE:+HQ_NO_OUTSIDE="$HQ_NO_OUTSIDE"} ${HQ_STATUS_TRIAL:+HQ_STATUS_TRIAL="$HQ_STATUS_TRIAL"}
         ${HQ_TODO_UNDO:+HQ_TODO_UNDO="$HQ_TODO_UNDO"} ${HQ_LISTS_UNDO:+HQ_LISTS_UNDO="$HQ_LISTS_UNDO"}
         ${HQ_GAMES_UNDO:+HQ_GAMES_UNDO="$HQ_GAMES_UNDO"} ${HQ_MAPS_KEY_FILE:+HQ_MAPS_KEY_FILE="$HQ_MAPS_KEY_FILE"}
         ${HQ_FIX_DRY:+HQ_FIX_DRY="$HQ_FIX_DRY"} ${HQ_HEALTH_ROOT:+HQ_HEALTH_ROOT="$HQ_HEALTH_ROOT"} HQ_BESIDE="$BESIDE")

# The status server first (status/phone.sh starts it when nothing listens on its port, and keeps its own pid).
env -i HOME="$HOME" USER="$USER" PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" LANG=en_US.UTF-8 \
  "${OWN_ENV[@]}" /bin/zsh "$ROOT/status/phone.sh"

if lsof -ti "tcp:$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "The call line is already running (port $PORT). Use app/stop.sh first to restart it."
else
  # A clean environment: the call runs on the Max login of the claude CLI, never on an API key.
  env -i HOME="$HOME" USER="$USER" PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" LANG=en_US.UTF-8 \
    "${OWN_ENV[@]}" nohup "$PY" "$ROOT/app/bot.py" "$@" >> "$LOG" 2>&1 &
  PID=$!
  echo $PID > "$PIDFILE"
  nohup caffeinate -i -w $PID >/dev/null 2>&1 &   # keep the computer from sleeping while the call line runs
  echo "The call line is starting (about 10 seconds)..."
  for i in {1..60}; do
    sleep 1
    [[ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/")" == "200" ]] && break
  done
fi

if [[ "$HQ_PHONE" != 1 ]]; then
  echo "Phone line not touched (HQ_PHONE=1 puts it on). This computer: http://127.0.0.1:$PORT"
  echo "Log: $LOG"
  exit 0
fi
# HTTPS for the phone, inside the tailnet only (never Funnel).
"$TS" serve --bg --https=$TS_CALL "http://127.0.0.1:$PORT" >/dev/null 2>&1 \
  && echo "Phone line on (port $TS_CALL)." || echo "Could not turn on Tailscale serve. Is Tailscale running?"
