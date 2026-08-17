#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/dist/XeusGUI.app"
OUT="$ROOT/dist/XeusGUI-macos.dmg"
STAGE="$ROOT/dist/dmg-stage"

if [[ ! -d "$APP" ]]; then
  echo "Missing $APP — run scripts/build.sh first"
  exit 1
fi

rm -rf "$STAGE" "$OUT"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/XeusGUI.app"
ln -s /Applications "$STAGE/Applications"

hdiutil create -volname XeusGUI -srcfolder "$STAGE" -ov -format UDZO "$OUT" >/dev/null
rm -rf "$STAGE"
echo "$OUT"
