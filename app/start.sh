#!/bin/zsh
# HQ: start the call line (app/bot.py) and the status server (status/server.mjs) on this computer, and put both on the
# phone line through Tailscale serve (tailnet only, never Funnel).
#   app/start.sh        starts both in the background (and keeps the computer awake while the call line runs);
#                       does nothing for a part that already runs
#   app/stop.sh         stops both, each only by the pid saved here when it was started
# The app's page: http://127.0.0.1:7860 (HQ_PORT), on the phone https://<this-computer>.<tailnet>.ts.net:8443. The status
# server: 127.0.0.1:4748 (HQ_STATUS_PORT), on the phone :8444; the page reaches it through the call line at /status/...
# Settings (environment variables), e.g.  HQ_MODEL=haiku app/start.sh
#   HQ_PORT, HQ_STATUS_PORT        the two ports (7860 and 4748)
#   HQ_TS_CALL_PORT, HQ_TS_STATUS_PORT   their phone addresses (8443 and 8444)
#   HQ_NO_PHONE=1                  leave Tailscale serve alone (a test, or a second HQ on this computer)
#   HQ_MODEL=haiku, HQ_PLAIN=1, HQ_WRAP_UP=off    another model, the plain Claude, no after-call work
#   HQ_BESIDE=1                    a second HQ next to the one that runs on this computer (a copy being worked on): its
#                                  own ports (7870 and 4758), no phone line unless HQ_PHONE=1 (8453 and 8454), its own
#                                  memory in scratch/support, the pairing read (never written) from the HQ next to it, its
#                                  health read from that HQ, no pushes, no sign-ups, no calendar or coaching refresh
# Every other HQ_* setting in the environment is passed on as it is (tools/test_instance.sh sets its own this way).
cd "$(dirname "$0")/.." || exit 1
ROOT="$PWD"
PATH="$PATH:/usr/sbin:/sbin"   # lsof is in /usr/sbin on a Mac; the helper app's PATH leaves it out
TS=/usr/local/bin/tailscale
BESIDE="${HQ_BESIDE:-0}"
if [[ "$BESIDE" == 1 ]]; then
  : ${HQ_PORT:=7870} ${HQ_STATUS_PORT:=4758} ${HQ_TS_CALL_PORT:=8453} ${HQ_TS_STATUS_PORT:=8454} ${HQ_UPDATE_LOOK:=0}
  : ${HQ_SUPPORT:=$ROOT/scratch/support}
  [[ "$HQ_PHONE" == 1 ]] || HQ_NO_PHONE=1
  if [[ -z "$HQ_ROLE_READ" && ! -r "$HQ_SUPPORT/role.json" && -r "$HOME/Library/Application Support/HQ/role.json" ]]; then
    HQ_ROLE_READ="$HOME/Library/Application Support/HQ"
  fi
  if [[ -z "$HQ_WORKSPACE" && -z "$HQ_HEALTH_ROOT" && -d "$ROOT/../HQ/.status" && "$(cd "$ROOT/../HQ" && pwd)" != "$ROOT" ]]; then
    HQ_HEALTH_ROOT="$(cd "$ROOT/../HQ" && pwd)"
  fi
  export HQ_SUPPORT HQ_ROLE_READ HQ_HEALTH_ROOT HQ_NO_PHONE HQ_UPDATE_LOOK
fi
export HQ_BESIDE="$BESIDE" HQ_PORT="${HQ_PORT:-7860}" HQ_STATUS_PORT="${HQ_STATUS_PORT:-4748}"
export HQ_TS_CALL_PORT="${HQ_TS_CALL_PORT:-8443}" HQ_TS_STATUS_PORT="${HQ_TS_STATUS_PORT:-8444}" HQ_HOST=127.0.0.1
[[ -n "$HQ_SUPPORT" ]] && mkdir -p "$HQ_SUPPORT"
PORT="$HQ_PORT"
LOG="${HQ_LOG:-$ROOT/scratch/server.log}"
PIDFILE="${HQ_PID_FILE:-$ROOT/scratch/server.pid}"
mkdir -p "$ROOT/scratch"
PY="$ROOT/.venv/bin/python"
[[ -x "$PY" ]] || PY=/usr/bin/python3
HQ_ENV=("${(@f)$(/usr/bin/env | /usr/bin/grep '^HQ_')}")   # every HQ_ setting, as it is

# The status server first (status/phone.sh starts it when nothing listens on its port, keeps its own pid, and puts it on
# the phone line unless HQ_NO_PHONE).
env -i HOME="$HOME" USER="$USER" PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" LANG=en_US.UTF-8 \
  "${HQ_ENV[@]}" /bin/zsh "$ROOT/status/phone.sh"

if lsof -ti "tcp:$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "The call line is already running (port $PORT). Use app/stop.sh first to restart it."
else
  # A clean environment: the call runs on the Max login of the claude CLI, never on an API key, and never through the
  # Claude desktop host this may have been started from. It listens on this computer only; Tailscale serve is the way in.
  env -i HOME="$HOME" USER="$USER" PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" LANG=en_US.UTF-8 \
    "${HQ_ENV[@]}" nohup "$PY" "$ROOT/app/bot.py" "$@" >> "$LOG" 2>&1 &
  PID=$!
  echo $PID > "$PIDFILE"
  nohup caffeinate -i -w $PID >/dev/null 2>&1 &   # keep the computer from sleeping while the call line runs
  echo "The call line is starting (about 10 seconds)..."
  for i in {1..60}; do
    sleep 1
    [[ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/")" == "200" ]] && break
  done
fi

if [[ -n "$HQ_NO_PHONE" ]]; then
  echo "Phone line not touched (HQ_NO_PHONE). This computer: http://127.0.0.1:$PORT"
  echo "Log: $LOG"
  exit 0
fi
"$TS" serve --bg --https=$HQ_TS_CALL_PORT "http://127.0.0.1:$PORT" >/dev/null 2>&1 \
  && echo "Phone line on." || echo "Could not turn on Tailscale serve. Is Tailscale running?"
HOSTNAME_TS="$("$TS" status --json 2>/dev/null | /usr/bin/python3 -c 'import sys,json;print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))' 2>/dev/null)"
echo "Open on your iPhone (Tailscale on): https://${HOSTNAME_TS:-<this-mac>.<tailnet>.ts.net}:$HQ_TS_CALL_PORT"
echo "Log: $LOG"
