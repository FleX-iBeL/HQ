#!/bin/zsh
# H13: the status page on the phone, on its own address, independent of the call line.
# Makes sure the status server runs (quietly, no browser window) and that Tailscale serves it
# over HTTPS inside the tailnet only (never Funnel). Does nothing when both are already so.
# Run every minute by the HQ Routine helper (routine/tick.py), so it also starts at login.
# Phone: https://<this-mac>.<tailnet>.ts.net:8444  (Tailscale on)
cd "$(dirname "$0")/.." || exit 1
TS=/usr/local/bin/tailscale
NODE=/opt/homebrew/bin/node
PORT="${HQ_STATUS_PORT:-4748}"
TS_HTTPS_PORT=8444   # 443 is another service, 8443 is the call line
mkdir -p scratch
if ! lsof -ti "tcp:$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  nohup "$NODE" status/server.mjs --quiet >> scratch/status-server.log 2>&1 &
  echo "Status server started."
fi
if ! "$TS" serve status 2>/dev/null | grep -q ":$TS_HTTPS_PORT "; then
  "$TS" serve --bg --https=$TS_HTTPS_PORT "http://127.0.0.1:$PORT" >/dev/null 2>&1 \
    && echo "Status on the phone: on." || echo "Could not turn on Tailscale serve for the status page."
fi
