#!/bin/zsh
# HQ: start the call server on this MacBook, and put it on the phone line.
#   app/start.sh        starts it in the background (and keeps the MacBook awake while it runs)
#   app/stop.sh         stops it
# Phone: open  https://<this-mac>.<tailnet>.ts.net:8443  in Safari (Tailscale on); printed below.
# This MacBook: http://127.0.0.1:7860 works too.
# Options (environment variables), e.g.  HQ_MODEL=haiku app/start.sh
#   HQ_MODEL=haiku    talk to Haiku 4.5 instead of Sonnet
#   HQ_PLAIN=1        the plain Claude of A2 (no files, tools or connectors)
#   HQ_WRAP_UP=off    no writing down, committing and pushing after a call
# For tests (happy_flows.py), on another port: HQ_NO_PHONE=1 leaves the Tailscale phone line
# alone; HQ_LOG and HQ_PID_FILE keep the log and the pid file apart from the live ones.
cd "$(dirname "$0")/.." || exit 1
ROOT="$PWD"
PORT="${HQ_PORT:-7860}"
TS=/usr/local/bin/tailscale
TS_HTTPS_PORT=8443   # 443 is already used on this MacBook by another service
LOG="${HQ_LOG:-$ROOT/scratch/server.log}"
PIDFILE="${HQ_PID_FILE:-$ROOT/scratch/server.pid}"
mkdir -p "$ROOT/scratch"
PATH="$PATH:/usr/sbin:/sbin"   # F44: lsof is in /usr/sbin on a Mac; the helper app's PATH leaves it out

if lsof -ti "tcp:$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "HQ is already running (port $PORT). Use app/stop.sh first to restart it."
else
  # A clean environment: the call runs on the Max login of the claude CLI, never on an API
  # key, and never through the Claude desktop host this may have been started from.
  # The bot listens on this MacBook only (127.0.0.1); Tailscale serve is the only way in.
  # F99: a test server (HQ_NO_PHONE) keeps every HQ_ setting of the test: without them it read and wrote the real files, and
  # through the pairing the main's. The live server starts clean as before.
  TEST_ENV=()
  [[ -n "$HQ_NO_PHONE" ]] && TEST_ENV=("${(f)$(/usr/bin/env | /usr/bin/grep '^HQ_')}")
  env -i HOME="$HOME" USER="$USER" PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin" LANG=en_US.UTF-8 \
    "${TEST_ENV[@]}" HQ_HOST=127.0.0.1 HQ_PORT="$PORT" \
    ${HQ_MODEL:+HQ_MODEL="$HQ_MODEL"} ${HQ_PLAIN:+HQ_PLAIN="$HQ_PLAIN"} \
    ${HQ_WRAP_UP:+HQ_WRAP_UP="$HQ_WRAP_UP"} ${HQ_CALLS:+HQ_CALLS="$HQ_CALLS"} \
    nohup "$ROOT/.venv/bin/python" "$ROOT/app/bot.py" "$@" >> "$LOG" 2>&1 &
  PID=$!
  echo $PID > "$PIDFILE"
  # Keep the MacBook from sleeping while the server runs (the screen may still turn off).
  nohup caffeinate -i -w $PID >/dev/null 2>&1 &
  echo "HQ is starting (about 10 seconds)..."
  for i in {1..60}; do
    sleep 1
    [[ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/")" == "200" ]] && break
  done
fi

if [[ -n "$HQ_NO_PHONE" ]]; then
  echo "Phone line not touched (HQ_NO_PHONE=1). This MacBook: http://127.0.0.1:$PORT"
  echo "Log: $LOG"
  exit 0
fi

# HTTPS for the phone, inside the tailnet only (never Funnel, which would be the open internet).
"$TS" serve --bg --https=$TS_HTTPS_PORT "http://127.0.0.1:$PORT" >/dev/null 2>&1 \
  && echo "Phone line on." || echo "Could not turn on Tailscale serve. Is Tailscale running?"
HOSTNAME_TS="$("$TS" status --json 2>/dev/null | python3 -c 'import sys,json;print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))' 2>/dev/null)"
echo "Open on your iPhone (Tailscale on): https://${HOSTNAME_TS:-<this-mac>.<tailnet>.ts.net}:$TS_HTTPS_PORT"
echo "Log: scratch/server.log"
