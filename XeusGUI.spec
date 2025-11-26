# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

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

import os
base_path = os.path.abspath(os.path.dirname(SPECPATH))

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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='XeusGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='XeusGUI',
)

app = BUNDLE(
    coll,
    name='XeusGUI.app',
    icon=None,
    bundle_identifier='com.example.XeusGUI',
)