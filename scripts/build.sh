#!/usr/bin/env bash
# Maintainer freeze script. End users download the .app / Setup.exe / AppImage — no Python.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/venv/bin/python" ]]; then
  PY="$ROOT/venv/bin/python"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
else
  echo "Build machine needs a venv with PySide6 + PyInstaller (see PACKAGING.md)."
  echo "End users should not pip-install anything — they run the frozen app."
  exit 1
fi

if ! "$PY" -c "import PyInstaller, PySide6" 2>/dev/null; then
  echo "This venv is missing PySide6 or PyInstaller. Install them in the *build* venv only."
  exit 1
fi

echo "Using $($PY --version) at $PY"
"$PY" -m PyInstaller XeusGUI.spec --noconfirm --clean

if [[ "$(uname -s)" == "Darwin" ]]; then
  APP="$ROOT/dist/XeusGUI.app"
  if [[ ! -d "$APP" ]]; then
    echo "Expected $APP"
    exit 1
  fi
  chmod +x "$APP/Contents/MacOS/XeusGUI" || true
  xattr -cr "$APP" 2>/dev/null || true
  "$PY" "$ROOT/scripts/write_icon.py" "$ROOT/freeze/xeusgui.png"
  bash "$ROOT/scripts/make_dmg.sh"
  echo "macOS app: $APP"
  echo "macOS dmg: $ROOT/dist/XeusGUI-macos.dmg"
  du -sh "$APP" "$ROOT/dist/XeusGUI-macos.dmg" 2>/dev/null || du -sh "$APP"
else
  BIN="$ROOT/dist/XeusGUI/XeusGUI"
  if [[ ! -x "$BIN" && ! -f "$BIN" ]]; then
    echo "Expected $BIN"
    exit 1
  fi
  chmod +x "$BIN" || true
  echo "Linux/onedir folder: $ROOT/dist/XeusGUI"
  du -sh "$ROOT/dist/XeusGUI"
fi
