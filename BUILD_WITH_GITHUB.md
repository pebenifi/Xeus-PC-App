# Сборка приложения для Windows через GitHub Actions

## Автоматическая сборка

Я создал GitHub Actions workflow, который автоматически соберет приложение для Windows при каждом push в репозиторий.

## Как использовать:

### 1. Загрузите код в GitHub

Если у вас еще нет репозитория:

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/ВАШ_USERNAME/xeusgui.git
git push -u origin main
```

### 2. Запуск сборки

Сборка запустится автоматически при:
- Push в ветку `main` или `master`
- Создании тега (например, `v1.0.0`)
- Создании Pull Request
- Ручном запуске через GitHub Actions UI

### 3. Получение собранного приложения

1. Перейдите на страницу вашего репозитория на GitHub
2. Откройте вкладку **Actions**
3. Выберите последний запуск workflow "Build Windows"
4. В разделе **Artifacts** скачайте:
   - `XeusGUI-Windows-onedir.zip` - папка с приложением (рекомендуется)
   - `XeusGUI-Windows-onefile.zip` - один исполняемый файл

## Ручной запуск сборки

1. Перейдите на страницу репозитория
2. Откройте вкладку **Actions**
3. Выберите workflow "Build Windows"
4. Нажмите **Run workflow**
5. Выберите ветку и нажмите **Run workflow**

## Альтернативные способы

### Вариант 1: Локальная сборка на Windows

Если у вас есть доступ к Windows-машине:

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
build_windows.bat onedir
```

### Вариант 2: Использование виртуальной машины

Можно использовать виртуальную машину Windows на вашем Mac (через Parallels, VMware, VirtualBox).

### Вариант 3: Удаленный доступ

Если у вас есть доступ к удаленной Windows-машине, можно собрать там.

## Структура артефактов

После сборки вы получите:

- **onedir версия**: папка `XeusGUI` с `XeusGUI.exe` и всеми библиотеками
- **onefile версия**: один файл `XeusGUI.exe` (больше размер, медленнее запуск)

Рекомендуется использовать **onedir** версию для лучшей производительности.

