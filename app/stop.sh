#!/bin/zsh
# HQ: stop the call line and the status server this HQ started, each only by the pid it saved when it started (never by
# a port or a name, so another HQ on the same computer is never touched). If a call is on, its after-call work gets up
# to a minute before the call line is forced.
cd "$(dirname "$0")/.." || exit 1
PIDFILE="${HQ_PID_FILE:-$PWD/scratch/server.pid}"
SPIDFILE="${HQ_STATUS_PID_FILE:-$PWD/scratch/status-server.pid}"
[[ "$HQ_PHONE" == 1 ]] && /usr/local/bin/tailscale serve --https="${HQ_TS_CALL_PORT:-8453}" off >/dev/null 2>&1 && echo "Phone line off."

ours() {  # the saved pid is still the process this HQ started ($2: what its command line must hold)
  [[ -n "$1" ]] && kill -0 "$1" 2>/dev/null && ps -o command= -p "$1" 2>/dev/null | grep -q -e "$2"
}
stop_one() {  # $1 the pid file, $2 what the command line holds, $3 its name
  local P=""
  [[ -r "$1" ]] && P=$(<"$1")
  if ! ours "$P" "$2"; then
    echo "$3 was not running."
    rm -f "$1"
    return
  fi
  kill -INT "$P"
  for i in {1..60}; do
    sleep 1
    kill -0 "$P" 2>/dev/null || break
  done
  if kill -0 "$P" 2>/dev/null; then
    kill -TERM "$P"; sleep 2; echo "$3 stopped (forced)."
  else
    echo "$3 stopped."
  fi
  rm -f "$1"
}
stop_one "$PIDFILE" "app/bot.py" "The call line"
stop_one "$SPIDFILE" "status/server.mjs" "The status server"
