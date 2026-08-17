#!/usr/bin/env bash
# Pack PyInstaller onedir as an AppImage (no system Python).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$ROOT/dist/XeusGUI"
APPDIR="$ROOT/dist/XeusGUI.AppDir"
OUT="$ROOT/dist/XeusGUI-x86_64.AppImage"

if [[ ! -d "$DIR" ]]; then
  echo "Missing $DIR — run PyInstaller first"
  exit 1
fi

rm -rf "$APPDIR"
mkdir -p "$APPDIR"
cp -a "$DIR"/. "$APPDIR"/
python3 "$ROOT/scripts/write_icon.py" "$APPDIR/xeusgui.png"

cat > "$APPDIR/XeusGUI.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=XeusGUI
Exec=XeusGUI
Icon=xeusgui
Categories=Science;Utility;
Terminal=false
EOF

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/XeusGUI" "$@"
EOF
chmod +x "$APPDIR/AppRun" "$APPDIR/XeusGUI"

TOOL="$ROOT/dist/appimagetool-x86_64.AppImage"
if [[ ! -x "$TOOL" ]]; then
  curl -L --fail -o "$TOOL" \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
  chmod +x "$TOOL"
fi

ARCH=x86_64 "$TOOL" --appimage-extract-and-run "$APPDIR" "$OUT"
echo "$OUT"
du -sh "$OUT"
