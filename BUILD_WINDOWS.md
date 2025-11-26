# Инструкция по сборке приложения для Windows

## Требования

1. **Windows 10/11** (64-bit)
2. **Python 3.8+** (рекомендуется 3.10 или 3.11)
3. **PyInstaller** (установится автоматически)

## Установка зависимостей

### 1. Создание виртуального окружения

```cmd
python -m venv venv
venv\Scripts\activate
```

### 2. Установка зависимостей

```cmd
pip install -r requirements.txt
pip install pyinstaller
```

## Сборка приложения

### Вариант 1: Сборка в папку (onedir) - Рекомендуется

Создает папку `dist\XeusGUI` с исполняемым файлом и всеми зависимостями.

**Преимущества:**
- Быстрый запуск
- Легче отлаживать
- Можно видеть структуру файлов

**Команда:**
```cmd
build_windows.bat onedir
```

Или напрямую:
```cmd
pyinstaller XeusGUI_windows.spec --clean --noconfirm
```

### Вариант 2: Сборка в один файл (onefile)

Создает один исполняемый файл `dist\XeusGUI.exe`.

**Преимущества:**
- Один файл для распространения
- Удобно для пользователей

**Недостатки:**
- Медленнее запуск (распаковка во временную папку)
- Больше размер файла

**Команда:**
```cmd
build_windows.bat onefile
```

Или напрямую:
```cmd
pyinstaller XeusGUI_windows_onefile.spec --clean --noconfirm
```

## Результат сборки

После успешной сборки приложение будет находиться в:
- **onedir**: `dist\XeusGUI\XeusGUI.exe`
- **onefile**: `dist\XeusGUI.exe`

## Запуск приложения

Двойной клик на `XeusGUI.exe` или через командную строку:
```cmd
dist\XeusGUI\XeusGUI.exe
```

## Устранение проблем

### Проблема: "ModuleNotFoundError"

**Решение:** Убедитесь, что все зависимости установлены:
```cmd
pip install -r requirements.txt
```

### Проблема: "Qt platform plugin not found"

**Решение:** PyInstaller должен автоматически включить Qt плагины. Если проблема сохраняется, проверьте, что в `.spec` файле правильно указаны `qt_plugins`.

### Проблема: QML файлы не загружаются

**Решение:** Убедитесь, что все QML файлы указаны в секции `qml_files` в `.spec` файле.

### Проблема: Большой размер приложения

**Решение:** Это нормально для приложений с Qt/PySide6. Размер обычно составляет 200-500 MB из-за включения всех Qt библиотек.

## Альтернативные способы сборки

### Использование GitHub Actions

Можно настроить автоматическую сборку для Windows через GitHub Actions. Пример конфигурации:

```yaml
name: Build Windows

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller
      - name: Build application
        run: |
          pyinstaller XeusGUI_windows.spec --clean --noconfirm
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: XeusGUI-Windows
          path: dist/XeusGUI
```

## Примечания

- Для распространения приложения может потребоваться кодовая подпись (code signing) для избежания предупреждений Windows Defender
- Рекомендуется тестировать приложение на чистой Windows-машине перед распространением
- Убедитесь, что все необходимые Visual C++ Redistributables установлены на целевой системе

