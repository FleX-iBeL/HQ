#!/bin/zsh
# HQ: stop the call line and the status server this HQ started, each only by the pid it saved when it started (or, with
# no pid saved, the one listening on its own port whose command is this HQ's own script), never by a name. If a call is
# on, its after-call work gets up to a minute before the call line is forced. The phone line goes off unless HQ_NO_PHONE.
cd "$(dirname "$0")/.." || exit 1
ROOT="$PWD"
PATH="$PATH:/usr/sbin:/sbin"
BESIDE="${HQ_BESIDE:-0}"
if [[ "$BESIDE" == 1 ]]; then
  : ${HQ_PORT:=7870} ${HQ_STATUS_PORT:=4758} ${HQ_TS_CALL_PORT:=8453}
  [[ "$HQ_PHONE" == 1 ]] || HQ_NO_PHONE=1
fi
PORT="${HQ_PORT:-7860}"
SPORT="${HQ_STATUS_PORT:-4748}"
PIDFILE="${HQ_PID_FILE:-$ROOT/scratch/server.pid}"
SPIDFILE="${HQ_STATUS_PID_FILE:-$ROOT/scratch/status-server.pid}"
[[ -z "$HQ_NO_PHONE" ]] && /usr/local/bin/tailscale serve --https="${HQ_TS_CALL_PORT:-8443}" off >/dev/null 2>&1 && echo "Phone line off."

ours() {  # the pid is a process of this HQ's ($2: what its command line must hold)
  [[ -n "$1" ]] && kill -0 "$1" 2>/dev/null && ps -o command= -p "$1" 2>/dev/null | grep -q -e "$2"
}
stop_one() {  # $1 the pid file, $2 what the command line holds, $3 its name, $4 its port
  local P=""
  [[ -r "$1" ]] && P=$(<"$1")
  if ! ours "$P" "$2"; then
    P=$(lsof -ti "tcp:$4" -sTCP:LISTEN 2>/dev/null | head -1)
    ours "$P" "$2" || P=""
    if [[ -n "$P" && "$2" == "status/server.mjs" ]]; then  # node's command line holds a relative path: its folder must be ours
      [[ "$(lsof -a -p "$P" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')" == "$ROOT" ]] || P=""
    fi
  fi
  if [[ -z "$P" ]]; then
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
stop_one "$PIDFILE" "$ROOT/app/bot.py" "The call line" "$PORT"
stop_one "$SPIDFILE" "status/server.mjs" "The status server" "$SPORT"
