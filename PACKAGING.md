# Сборка автономных приложений XeusGUI

Пользователю **не нужно** ставить Python, pip или библиотеки. Он ставит/запускает готовый файл.

## Что скачивать

Готовые файлы лежат во вкладке **Releases** (`latest` после пуша в `main`, либо тег `v*`). Дубликаты также в Actions → Artifacts.

| Платформа | Артефакт | Как запускать |
|-----------|----------|----------------|
| Windows | `XeusGUI-windows` → `XeusGUI-Setup.exe` | Двойной клик по установщику, затем ярлык **XeusGUI**. Python не ставится. |
| macOS | `XeusGUI-macos` → `XeusGUI-macos.dmg` | Открыть DMG, перетащить `XeusGUI.app` в Программы. Если Gatekeeper ругается — правый клик по приложению → «Открыть», либо Системные настройки → Конфиденциальность и безопасность. |
| Linux | `XeusGUI-linux` → `XeusGUI-x86_64.AppImage` (или `.tar.gz`) | `chmod +x` и запуск AppImage; либо распаковать tar.gz и запустить `XeusGUI`. |

Локально на Mac после `scripts/build.sh`: `dist/XeusGUI.app` и `dist/XeusGUI-macos.dmg`.

## Сборка у разработчика (не для конечного пользователя)

Нужен venv с PySide6 и PyInstaller (уже есть в репозитории как `venv/`):

```bash
chmod +x scripts/build.sh
./scripts/build.sh
```

Windows (на машине Windows): `powershell -File scripts/build.ps1`  
Linux: тот же `scripts/build.sh`, затем `scripts/linux_appimage.sh`.

CI: Python 3.12 + `requirements.txt` + `requirements-build.txt` на `macos-latest`, `ubuntu-latest`, `windows-latest`.

## Размер

Локальная macOS-сборка (Apple Silicon): **~121 MB** `.app`, **~49 MB** `.dmg`.

В бандл входят Qt Core/Gui/Qml/Quick/QuickControls2 (Fusion/Basic), Graphs, Svg, Network, OpenGL, VirtualKeyboard. Выкинуты WebEngine (~576 MB), Multimedia/ffmpeg, 3D, Pdf, Charts, Bluetooth и прочие неиспользуемые модули (в логе сборки: binaries dropped=123, datas dropped=2518). UPX не используется (ломает Qt).
