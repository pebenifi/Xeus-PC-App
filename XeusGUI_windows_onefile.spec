# -*- mode: python ; coding: utf-8 -*-
# Windows build configuration for XeusGUI (onefile mode - single executable)
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

block_cipher = None

# Определяем базовый путь (универсальный для Windows и других ОС)
base_path = os.path.abspath(os.path.dirname(SPECPATH))

# Собираем QML-файлы и qmldir
qml_files = [
    ('app.qml', '.'),
    ('Screen01.qml', '.'),
    ('Clinicalmode.qml', '.'),
    ('Constants.qml', '.'),
    ('qmldir', '.')
]

# Собираем Qt-плагины и QML-ресурсы
qt_plugins = collect_data_files('PySide6', subdir='plugins')
qt_qml = collect_data_files('PySide6', subdir='qml')

a = Analysis(
    ['main.py'],
    pathex=[base_path],
    binaries=[],
    datas=qml_files + qt_plugins + qt_qml,
    hiddenimports=['PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtGraphs', 'PySide6.QtCore'] + collect_submodules('PySide6'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.Qt3DAnimation', 'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Windows: создаем один исполняемый файл (onefile)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='XeusGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Не показывать консольное окно
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Для onefile режима не нужна секция COLLECT и BUNDLE

