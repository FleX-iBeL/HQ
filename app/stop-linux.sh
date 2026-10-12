#!/bin/bash
# H56.1: stop the call server on a Linux server and close the phone line (Tailscale serve on 8443).
# app/stop.sh is the Mac's. If a call is still running, hang up first: the after-call work gets up to a
# minute to finish before the server is stopped. HQ_NO_PHONE=1 leaves the phone line alone.
cd "$(dirname "$0")/.." || exit 1
PORT="${HQ_PORT:-7860}"
P="$PATH:$HOME/.npm-global/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
TS="${HQ_TAILSCALE:-$(PATH="$P" command -v tailscale)}"
PIDFILE="${HQ_PID_FILE:-$PWD/scratch/server.pid}"
ts() {
  if [ "$(id -u)" != 0 ] && [ "${HQ_TS_SUDO:-1}" != 0 ]; then sudo -n "$TS" "$@"; else "$TS" "$@"; fi
}

[ -z "$HQ_NO_PHONE" ] && ts serve --https=8443 off >/dev/null 2>&1 && echo "Phone line off."
# Only this HQ's own bot counts: the pid file's process, if it really is app/bot.py, else whoever listens on
# the port as this user and runs app/bot.py (never a loose name match).
PIDS=""
if [ -r "$PIDFILE" ]; then
  P1=$(cat "$PIDFILE")
  if [ -n "$P1" ] && kill -0 "$P1" 2>/dev/null && ps -o command= -p "$P1" 2>/dev/null | grep -q "app/bot.py"; then
    PIDS=$P1
  fi
fi
if [ -z "$PIDS" ]; then
  for p in $(ss -Hltnp "sport = :$PORT" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u); do
    ps -o command= -p "$p" 2>/dev/null | grep -q "app/bot.py" && PIDS="$PIDS $p"
  done
fi
running() {
  for p in $PIDS; do kill -0 "$p" 2>/dev/null && return 0; done
  return 1
}
if [ -z "$PIDS" ]; then
  echo "HQ was not running."
else
  kill -INT $PIDS   # a polite stop: lets a call's after-call work finish
  for i in $(seq 1 60); do
    sleep 1
    running || break
  done
  if running; then
    kill -TERM $PIDS; sleep 2; echo "HQ stopped (forced)."
  else
    echo "HQ stopped."
  fi
fi
rm -f "$PIDFILE"
