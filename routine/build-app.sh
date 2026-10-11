#!/bin/zsh
# Builds the HQ Routine helper app into ~/Applications (phase L). Run again after changing
# routine.applescript; macOS may then ask once more for access to the Documents folder.
# M4: the installer passes its own copy of routine.applescript, with this HQ's path in it.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Applications/HQ Routine.app"
mkdir -p "$HOME/Applications"
osascript -e 'tell application "HQ Routine" to quit' >/dev/null 2>&1 || true
rm -rf "$APP"
# H54 (11 October 2026): the helper under its name from before, if it is still there, makes way.
OLD="$HOME/Applications/Jarvis Routine.app"
if [ -d "$OLD" ]; then
  osascript -e 'tell application "Jarvis Routine" to quit' >/dev/null 2>&1 || true
  rm -rf "$OLD"
fi
SRC="$1"
if [ -z "$SRC" ]; then
  # The repo ships it for /Users/you/HQ; this HQ's own path goes in.
  SRC="$(mktemp -t routine).applescript"
  sed "s#/Users/you/HQ/#$(cd "$HERE/.." && pwd)/#" "$HERE/routine.applescript" > "$SRC"
fi
osacompile -s -o "$APP" "$SRC"
/usr/bin/defaults write "$APP/Contents/Info" LSUIElement -bool true
/usr/bin/defaults write "$APP/Contents/Info" CFBundleIdentifier "com.hq.routine-helper"
/usr/bin/defaults write "$APP/Contents/Info" NSAppleEventsUsageDescription "HQ Routine starts jobs agreed on a call."
plutil -convert xml1 "$APP/Contents/Info.plist"
codesign --force --deep -s - "$APP"
echo "Built: $APP"
