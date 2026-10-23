#!/usr/bin/env bash
# Build Claudou.app (menu bar app) — no Xcode project needed.
# Usage: ./build_app.sh        → build/Claudou.app
set -euo pipefail
cd "$(dirname "$0")"

swift build -c release --arch arm64 --arch x86_64
BIN="$(swift build -c release --arch arm64 --arch x86_64 --show-bin-path)/Claudou"

VERSION="$(tr -d '[:space:]' < ../../VERSION)"
APP="build/Claudou.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
cp "$BIN" "$APP/Contents/MacOS/Claudou"

# App icon + header logo
LOGO="../../assets/logo.png"
if [[ -f "$LOGO" ]]; then
    mkdir -p "$APP/Contents/Resources"
    ICONSET="$(mktemp -d)/AppIcon.iconset"
    swift scripts/make_icon.swift "$LOGO" "$ICONSET"
    iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/AppIcon.icns"
    cp "$LOGO" "$APP/Contents/Resources/logo.png"
fi
# Menu bar glyph (template image)
MENUBAR="../../assets/logo-menubar.png"
if [[ -f "$MENUBAR" ]]; then
    mkdir -p "$APP/Contents/Resources"
    swift scripts/make_menubar.swift "$MENUBAR" "$APP/Contents/Resources/menubar.png" 40
fi

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>vn.com.dtn.claudou</string>
  <key>CFBundleName</key><string>Claudou</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundleExecutable</key><string>Claudou</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>LSUIElement</key><true/>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST

codesign --force --sign - "$APP" >/dev/null 2>&1 || true
echo "Built: $APP"
