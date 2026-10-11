#!/bin/zsh
# H20: installs the watchdog (watchdog.py) outside the Documents folder and lets macOS run it every
# 5 minutes on the five-minute marks (H22) and at login, as a LaunchAgent. Run again after changing watchdog.py.
set -e
SUPPORT="$HOME/Library/Application Support/HQ"
PLIST="$HOME/Library/LaunchAgents/com.hq.watchdog.plist"
mkdir -p "$SUPPORT"
cp "$(dirname "$0")/watchdog.py" "$SUPPORT/watchdog.py"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.hq.watchdog</string>
  <key>ProgramArguments</key>
  <array><string>/usr/bin/python3</string><string>$SUPPORT/watchdog.py</string></array>
  <key>StartCalendarInterval</key>
  <array>
$(for m in 0 5 10 15 20 25 30 35 40 45 50 55; do echo "    <dict><key>Minute</key><integer>$m</integer></dict>"; done)
  </array>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$SUPPORT/watchdog.out</string>
  <key>StandardErrorPath</key><string>$SUPPORT/watchdog.out</string>
</dict>
</plist>
PL
# One watchdog only: one installed under another id before (an older HQ) is taken out first.
# Also the one from before H54 (11 October 2026), under the old name.
for old in "$HOME"/Library/LaunchAgents/*.watchdog.plist(N) "$HOME"/Library/LaunchAgents/*.jarvis-watchdog.plist(N); do
  [ "$old" = "$PLIST" ] && continue
  launchctl bootout "gui/$(id -u)/$(basename "$old" .plist)" 2>/dev/null || true
  rm -f "$old"
done
launchctl bootout "gui/$(id -u)/com.hq.watchdog" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "Watchdog installed: every 5 minutes and at login."
