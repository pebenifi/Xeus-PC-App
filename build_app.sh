#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
pip install pyinstaller --quiet
pyinstaller XeusGUI.spec --clean --noconfirm
echo "Сборка завершена. Приложение находится в dist/XeusGUI.app"

