#!/bin/bash
# H56.1: start the call server on a Linux server, and put it on the phone line. app/start.sh is the Mac's.
#   app/start-linux.sh   starts it in the background (does nothing if it already runs)
#   app/stop-linux.sh    stops it
# Phone: https://<this-server>.<tailnet>.ts.net:8443 (Tailscale on, tailnet only, never Funnel).
# The same options as start.sh (HQ_MODEL, HQ_PLAIN, HQ_WRAP_UP, HQ_NO_PHONE, HQ_PORT, HQ_LOG, HQ_PID_FILE);
# every HQ_* setting in the environment is passed on to the call. Off a Mac it listens with faster-whisper
# (HQ_STT=faster, HQ_WHISPER=small unless set; small was the pick in H55). The math libraries get one
# thread each (else numpy fights the turn detector and a call hangs, found in H55).
# Tailscale's serve settings belong to root here unless the user is its operator: sudo -n, never a password
# (HQ_TS_SUDO=0 leaves sudo out).
cd "$(dirname "$0")/.." || exit 1
ROOT="$PWD"
PORT="${HQ_PORT:-7860}"
P="$PATH:$HOME/.npm-global/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
TS="${HQ_TAILSCALE:-$(PATH="$P" command -v tailscale)}"
CLAUDE="${HQ_CLAUDE_CLI:-$(PATH="$P" command -v claude)}"
TS_HTTPS_PORT=8443
LOG="${HQ_LOG:-$ROOT/scratch/server.log}"
PIDFILE="${HQ_PID_FILE:-$ROOT/scratch/server.pid}"
mkdir -p "$ROOT/scratch"
ts() {
  if [ "$(id -u)" != 0 ] && [ "${HQ_TS_SUDO:-1}" != 0 ]; then sudo -n "$TS" "$@"; else "$TS" "$@"; fi
}
listening() { ss -Hltn "sport = :$1" 2>/dev/null | grep -q .; }

if listening "$PORT"; then
  echo "HQ is already running (port $PORT). Use app/stop-linux.sh first to restart it."
elif [ ! -x "$ROOT/.venv/bin/python" ]; then
  echo "HQ's Python environment isn't set up here ($ROOT/.venv): run the installer first."
  exit 1
else
  # A clean environment: the call runs on the claude CLI's own login, never on an API key.
  # The bot listens on this server only (127.0.0.1); Tailscale serve is the only way in.
  HQENV=()
  while IFS='=' read -r k v; do HQENV+=("$k=$v"); done < <(env | grep '^HQ_' | grep -v '^HQ_\(HOST\|PORT\|CLAUDE_CLI\)=')
  env -i HOME="$HOME" USER="$USER" PATH="$(dirname "$CLAUDE"):/usr/local/bin:/usr/bin:/bin" LANG=en_US.UTF-8 \
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    HQ_STT="${HQ_STT:-faster}" HQ_WHISPER="${HQ_WHISPER:-small}" "${HQENV[@]}" \
    HQ_HOST=127.0.0.1 HQ_PORT="$PORT" HQ_CLAUDE_CLI="$CLAUDE" \
    nohup "$ROOT/.venv/bin/python" "$ROOT/app/bot.py" "$@" >> "$LOG" 2>&1 &
  PID=$!
  echo $PID > "$PIDFILE"
  echo "HQ is starting (about 10 seconds)..."
  for i in $(seq 1 60); do
    sleep 1
    [ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/")" = "200" ] && break
  done
fi

if [ -n "$HQ_NO_PHONE" ]; then
  echo "Phone line not touched (HQ_NO_PHONE=1). This server: http://127.0.0.1:$PORT"
  echo "Log: $LOG"
  exit 0
fi

ts serve --bg --https=$TS_HTTPS_PORT "http://127.0.0.1:$PORT" >/dev/null 2>&1 \
  && echo "Phone line on." || echo "Could not turn on Tailscale serve. Is Tailscale running, and may this user use sudo -n?"
HOSTNAME_TS="$("$TS" status --json 2>/dev/null | python3 -c 'import sys,json;print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))' 2>/dev/null)"
echo "Open on your phone (Tailscale on): https://${HOSTNAME_TS:-<this-server>.<tailnet>.ts.net}:$TS_HTTPS_PORT"
echo "Log: $LOG"
