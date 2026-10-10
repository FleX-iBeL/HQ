#!/bin/zsh
# Jarvis VA: stop the call server and close the phone line (Tailscale serve on port 8443).
# If a call is still running, hang up first: the after-call work (writing down, commit, push)
# gets up to a minute to finish before the server is stopped.
cd "$(dirname "$0")/.." || exit 1
PORT="${JARVIS_PORT:-7860}"
TS=/usr/local/bin/tailscale
PIDFILE="${JARVIS_PID_FILE:-$PWD/scratch/server.pid}"
# JARVIS_NO_PHONE=1 (tests, on another port): the Tailscale phone line is left alone.

[[ -z "$JARVIS_NO_PHONE" ]] && "$TS" serve --https=8443 off >/dev/null 2>&1 && echo "Phone line off."
PIDS=$(lsof -ti "tcp:$PORT" -sTCP:LISTEN 2>/dev/null)
# lsof can come back empty without the server being gone (9 October 03:10: "stopped", and the old
# version kept answering). The pid file knows it too; only a process that really is the bot counts.
if [[ -z "$PIDS" && -r "$PIDFILE" ]]; then
  P=$(<"$PIDFILE")
  if [[ -n "$P" ]] && kill -0 "$P" 2>/dev/null && ps -o command= -p "$P" 2>/dev/null | grep -q "app/bot.py"; then
    PIDS=$P
  fi
fi
running() {
  lsof -ti "tcp:$PORT" -sTCP:LISTEN >/dev/null 2>&1 && return 0
  for p in $=PIDS; do kill -0 "$p" 2>/dev/null && return 0; done
  return 1
}
if [[ -z "$PIDS" ]]; then
  echo "Jarvis was not running."
else
  kill -INT $=PIDS   # a polite stop: lets a call's after-call work finish
  for i in {1..60}; do
    sleep 1
    running || break
  done
  if running; then
    kill -TERM $=PIDS; sleep 2; echo "Jarvis stopped (forced)."
  else
    echo "Jarvis stopped."
  fi
fi
rm -f "$PIDFILE"
