# Инструкции по сборке XeusGUI

## Сборка для macOS

```bash
./build_app.sh
```

Или вручную:
```bash
source venv/bin/activate
pip install pyinstaller
pyinstaller XeusGUI.spec --clean --noconfirm
```

Результат: `dist/XeusGUI.app`

## Сборка для Windows

**Требования:** Windows 10/11, Python 3.8+

### Быстрый старт:

1. Откройте командную строку (cmd) или PowerShell
2. Перейдите в папку проекта
3. Создайте виртуальное окружение:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```
4. Установите зависимости:
   ```cmd
   pip install -r requirements.txt
   pip install pyinstaller
   ```
5. Запустите сборку:
   ```cmd
   build_windows.bat onedir
   ```

Результат: `dist\XeusGUI\XeusGUI.exe`

### Варианты сборки:

- **onedir** (рекомендуется): папка с исполняемым файлом
  ```cmd
   build_windows.bat onedir
   ```

- **onefile**: один исполняемый файл
  ```cmd
   build_windows.bat onefile
   ```

Подробные инструкции см. в [BUILD_WINDOWS.md](BUILD_WINDOWS.md)

## Структура файлов сборки

- `XeusGUI.spec` - конфигурация для macOS
- `XeusGUI_windows.spec` - конфигурация для Windows (onedir)
- `XeusGUI_windows_onefile.spec` - конфигурация для Windows (onefile)
- `build_app.sh` - скрипт сборки для macOS
- `build_windows.bat` - скрипт сборки для Windows

## Примечания

- Код в `main.py` автоматически определяет платформу и использует правильные пути
- Все QML файлы автоматически включаются в сборку
- Qt библиотеки и плагины включаются автоматически

