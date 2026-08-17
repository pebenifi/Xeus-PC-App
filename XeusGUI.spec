# -*- mode: python ; coding: utf-8 -*-
"""Standalone XeusGUI freeze (onedir). End users do not install Python.

Windows: dist/XeusGUI/XeusGUI.exe — wrap with installer/xeusgui.iss for a Setup.exe.
macOS:   dist/XeusGUI.app
Linux:   dist/XeusGUI/XeusGUI — pack as tar.gz / AppImage in CI.
"""

from __future__ import annotations

import os
import sys

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_submodules
import importlib.util

spec_root = os.path.abspath(SPECPATH)
_bundle_path = os.path.join(spec_root, "freeze", "qt_bundle.py")
_spec = importlib.util.spec_from_file_location("xeus_qt_bundle", _bundle_path)
_bundle = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bundle)
EXCLUDES = _bundle.EXCLUDES
HIDDENIMPORTS = _bundle.HIDDENIMPORTS
app_qml_datas = _bundle.app_qml_datas
filter_binaries = _bundle.filter_binaries
filter_datas = _bundle.filter_datas

# pymodbus.client.__init__ pulls serial/udp/tls; we import tcp only, but collect
# the tcp/framer stack explicitly and leave the rest excluded.
pymodbus_hidden = [
    m
    for m in collect_submodules("pymodbus")
    if not m.startswith(("pymodbus.server", "pymodbus.simulator", "pymodbus.datastore", "pymodbus.client.serial"))
]

a = Analysis(
    [os.path.join(spec_root, "main.py")],
    pathex=[spec_root],
    binaries=[],
    datas=app_qml_datas(spec_root),
    hiddenimports=HIDDENIMPORTS + pymodbus_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(spec_root, "freeze", "rthook_qml_path.py")],
    excludes=EXCLUDES,
    noarchive=False,
)

a.binaries = filter_binaries(a.binaries)
a.datas = filter_datas(a.datas)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="XeusGUI",
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
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="XeusGUI",
)

if sys.platform == "darwin":
    from PyInstaller.building.osx import BUNDLE

    app = BUNDLE(
        coll,
        name="XeusGUI.app",
        icon=None,
        bundle_identifier="com.xeus.gui",
        info_plist={
            "CFBundleName": "XeusGUI",
            "CFBundleDisplayName": "XeusGUI",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "12.0",
        },
    )
