#!/bin/zsh
# H13: the status page on the phone, on its own address, independent of the call line.
# Makes sure the status server runs (quietly, no browser window) and that Tailscale serves it
# over HTTPS inside the tailnet only (never Funnel). Does nothing when both are already so.
# Run every minute by the HQ Routine helper (routine/tick.py), so it also starts at login.
# Phone: https://<this-mac>.<tailnet>.ts.net:8444  (Tailscale on)
# H56.1: plain sh too, so it runs on a Linux server (tick.py runs it with /bin/sh there). There Tailscale's
# serve settings belong to root, so it goes through sudo -n (HQ_TS_SUDO=0 leaves that out). HQ_NO_PHONE=1
# leaves Tailscale alone (a second HQ on one computer, or a test). HQ_NODE / HQ_TAILSCALE override the paths.
cd "$(dirname "$0")/.." || exit 1
if [ "$(uname)" = Darwin ]; then
  TS="${HQ_TAILSCALE:-/usr/local/bin/tailscale}"
  NODE="${HQ_NODE:-/opt/homebrew/bin/node}"
else
  P="$PATH:$HOME/.npm-global/bin:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
  TS="${HQ_TAILSCALE:-$(PATH="$P" command -v tailscale)}"
  NODE="${HQ_NODE:-$(PATH="$P" command -v node)}"
fi
ts() {
  if [ "$(uname)" != Darwin ] && [ "$(id -u)" != 0 ] && [ "${HQ_TS_SUDO:-1}" != 0 ]; then
    sudo -n "$TS" "$@"
  else
    "$TS" "$@"
  fi
}
listening() {
  if [ "$(uname)" = Darwin ]; then
    lsof -ti "tcp:$1" -sTCP:LISTEN >/dev/null 2>&1
  else
    ss -Hltn "sport = :$1" 2>/dev/null | grep -q .
  fi
}
PORT="${HQ_STATUS_PORT:-4748}"
TS_HTTPS_PORT=8444   # 443 is another service, 8443 is the call line
mkdir -p scratch
if ! listening "$PORT"; then
  nohup "$NODE" status/server.mjs --quiet >> scratch/status-server.log 2>&1 &
  echo "Status server started."
fi
[ -n "$HQ_NO_PHONE" ] && exit 0
if ! ts serve status 2>/dev/null | grep -q ":$TS_HTTPS_PORT "; then
  ts serve --bg --https=$TS_HTTPS_PORT "http://127.0.0.1:$PORT" >/dev/null 2>&1 \
    && echo "Status on the phone: on." || echo "Could not turn on Tailscale serve for the status page."
fi
