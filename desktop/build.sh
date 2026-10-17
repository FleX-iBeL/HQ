#!/bin/zsh
# H27: build HQ, the Mac desktop app, from desktop/HQ.swift with swiftc (the Command Line Tools are enough).
#   desktop/build.sh            builds scratch/desktop/HQ.app and checks it (HQ.app --check)
#   desktop/build.sh --install  also puts it in ~/Applications/HQ.app (replacing an older one)
# The app gets this HQ's folder in its Info.plist (HQPath), so it finds shell.html and hq_control.py.
# Signed ad hoc on this Mac. The first time it reads the Documents folder macOS asks once (Allow), and
# the first call asks for the microphone once.
set -e
cd "$(dirname "$0")/.."
HQ="$PWD"
OUT="$HQ/scratch/desktop"
APP="$OUT/HQ.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
swiftc -O -target arm64-apple-macos13 -framework Cocoa -framework WebKit -framework CoreAudio \
  -o "$APP/Contents/MacOS/HQ" "$HQ/desktop/HQ.swift"

# The icon: HQ's house (H48). H194: drawn once and shipped as desktop/HQ.icns (make_dock_icon.py), so a friend's
# fresh install has it in the Dock without drawing anything; drawing it from icon.svg is only the fallback.
ICON=""
if [[ -f "$HQ/desktop/HQ.icns" ]]; then
  cp "$HQ/desktop/HQ.icns" "$APP/Contents/Resources/HQ.icns" && ICON="<key>CFBundleIconFile</key><string>HQ</string>"
fi
# H48: drawn with svg2png (macOS reads SVG itself), so the corners stay transparent; qlmanage only as a fallback
# (it gives a white square around the icon in the Dock).
rm -f "$OUT/icon.svg.png"
if [[ -n "$ICON" ]]; then :
elif swiftc -O -o "$OUT/svg2png" "$HQ/desktop/svg2png.swift" >/dev/null 2>&1 && "$OUT/svg2png" "$HQ/desktop/icon.svg" "$OUT/icon.svg.png" 1024; then :
else qlmanage -t -s 1024 -o "$OUT" "$HQ/desktop/icon.svg" >/dev/null 2>&1; fi
if [[ -z "$ICON" && -f "$OUT/icon.svg.png" ]]; then
  SET="$OUT/HQ.iconset"; rm -rf "$SET"; mkdir -p "$SET"
  for s in 16 32 128 256 512; do
    sips -z $s $s "$OUT/icon.svg.png" --out "$SET/icon_${s}x${s}.png" >/dev/null
    sips -z $((s*2)) $((s*2)) "$OUT/icon.svg.png" --out "$SET/icon_${s}x${s}@2x.png" >/dev/null
  done
  iconutil -c icns "$SET" -o "$APP/Contents/Resources/HQ.icns" && ICON="<key>CFBundleIconFile</key><string>HQ</string>"
fi

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>HQ</string>
  <key>CFBundleDisplayName</key><string>HQ</string>
  <key>CFBundleIdentifier</key><string>com.hq.desktop</string>
  <key>CFBundleExecutable</key><string>HQ</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.1</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSMicrophoneUsageDescription</key><string>HQ uses the microphone for calls.</string>
  <key>NSAppTransportSecurity</key><dict><key>NSAllowsLocalNetworking</key><true/></dict>
  <key>HQPath</key><string>$HQ</string>
  $ICON
</dict></plist>
PLIST

codesign --force --sign - "$APP" >/dev/null 2>&1 || true
"$APP/Contents/MacOS/HQ" --check
echo "Built: $APP"

if [[ "$1" == "--install" ]]; then
  mkdir -p "$HOME/Applications"
  rm -rf "$HOME/Applications/HQ.app"
  cp -R "$APP" "$HOME/Applications/HQ.app"
  # H194: the Dock and Finder keep an icon they saw before; tell them this one is new.
  touch "$HOME/Applications/HQ.app"
  LSR=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
  [[ -x "$LSR" ]] && "$LSR" -f "$HOME/Applications/HQ.app" >/dev/null 2>&1 || true
  echo "Installed: ~/Applications/HQ.app"
fi
