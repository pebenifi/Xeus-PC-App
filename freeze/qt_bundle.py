"""Filter PyInstaller TOCs so unused Qt / pymodbus bits stay out of the frozen app."""

from __future__ import annotations

import os
import sys

# Substrings matched against dest + source paths (case-insensitive).
BINARY_DROP = (
    "qtwebengine",
    "qtwebview",
    "qtwebchannel",
    "qtwebsockets",
    "qt3d",
    "qtquick3d",
    "qtpdf",
    "qtcharts",
    "qtdatavisualization",
    "qtmultimedia",
    "qtspatialaudio",
    "qtbluetooth",
    "qtnfc",
    "qtpositioning",
    "qtlocation",
    "qtsensors",
    "qtserialport",
    "qtserialbus",
    "qttexttospeech",
    "qtdesigner",
    "qthelp",
    "qthttpserver",
    "qtremoteobjects",
    "qtscxml",
    "qtstatemachine",
    "qtsql",
    "qttest",
    "qtprintsupport",
    "qtnetworkauth",
    "qtquickwidgets",
    "qtopenglwidgets",
    "qtsvgwidgets",
    "qtgraphswidgets",
    "qtmultimediawidgets",
    "qtpdfwidgets",
    "qtuitools",
    "qtconcurrent",
    "qtxml",
    "libavcodec",
    "libavformat",
    "libavutil",
    "libavfilter",
    "libswscale",
    "libswresample",
    "assistant.app",
    "designer.app",
    "linguist.app",
    "sceneparsers",
    "assetimporters",
    "geometryloaders",
    "qmltooling",
    "qmllint",
    "geoservices",
    "canbus",
    "sqldrivers",
    "webview",
    "texttospeech",
    "renderers",
    "qtquickcontrols2imagine",
    "qtquickcontrols2material",
    "qtquickcontrols2universal",
    "qtquickcontrols2fluent",
    "qtquickcontrols2ios",
    "qtquickcontrols2macos",
    "qtquickcontrols2imagine",
    "qpdf",
    "opengl32sw",  # huge software GL; real GPU is expected
)

# Drop unused QML modules / Controls styles. Fusion is the app style.
QML_DROP = (
    "/qtwebengine",
    "/qtwebview",
    "/qtwebchannel",
    "/qtwebsockets",
    "/qt3d",
    "/qtquick3d",
    "/qtpdf",
    "/qtquick/pdf",
    "/qtcharts",
    "/qtdatavisualization",
    "/qtmultimedia",
    "/qtlocation",
    "/qtpositioning",
    "/qttest",
    "/qttexttospeech",
    "/qtremoteobjects",
    "/qtsensors",
    "/qtscxml",
    "/qt5compat",
    "/qtquick/particles",
    "/qtquick/scene3d",
    "/qtquick/scene2d",
    "/qtquick/timeline",
    "/qtquick/vectorimage",
    "/qtquick/effects",
    "/qtquick/localstorage",
    "/qtquick/dialogs",
    "/qtquick/nativestyle",
    "/qtquick/controls/material",
    "/qtquick/controls/imagine",
    "/qtquick/controls/universal",
    "/qtquick/controls/fluentwinui3",
    "/qtquick/controls/ios",
    "/qtquick/controls/macos",
    "/qtquick/controls/designer",
    "/translations/",
)

HIDDENIMPORTS = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtNetwork",
    "PySide6.QtOpenGL",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickControls2",
    "PySide6.QtGraphs",
    "PySide6.QtSvg",
    "shiboken6",
    "modbus_manager",
    "modbus_client",
    "clinical_batch",
    "display_text",
    "pymodbus",
    "pymodbus.client",
    "pymodbus.client.tcp",
    "pymodbus.framer",
    "pymodbus.framer.rtu",
    "pymodbus.framer.socket",
    "pymodbus.framer.tls",
    "pymodbus.pdu",
    "pymodbus.transport",
]

EXCLUDES = [
    "tkinter",
    "turtle",
    "turtledemo",
    "unittest",
    "pydoc",
    "doctest",
    "ensurepip",
    "venv",
    "idlelib",
    "lib2to3",
    "xmlrpc",
    "IPython",
    "matplotlib",
    "numpy",
    "pandas",
    "PIL",
    "cv2",
    "scipy",
    "modbus_tk",
    "serial",
    "serial.tools",
    "pymodbus.server",
    "pymodbus.simulator",
    "pymodbus.datastore",
    "pymodbus.client.serial",
    "pymodbus.client.udp",
    "pymodbus.client.tls",
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebView",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras",
    "PySide6.QtQuick3D",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtLocation",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSerialBus",
    "PySide6.QtTextToSpeech",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtHttpServer",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtStateMachine",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtPrintSupport",
    "PySide6.QtNetworkAuth",
    "PySide6.QtQuickWidgets",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtSvgWidgets",
    "PySide6.QtGraphsWidgets",
    "PySide6.QtWidgets",
    "PySide6.QtUiTools",
    "PySide6.QtXml",
    "PySide6.QtConcurrent",
    "PySide6.QtSpatialAudio",
    "PySide6.scripts",
    "PySide6.QtAsyncio",
]


def _blob(entry) -> str:
    dest = entry[0] if entry else ""
    src = entry[1] if len(entry) > 1 else ""
    return f"{dest}|{src}".replace("\\", "/").lower()


def _drop_binary(blob: str) -> bool:
    return any(needle in blob for needle in BINARY_DROP)


def _drop_data(blob: str) -> bool:
    if _drop_binary(blob):
        return True
    if "/qml/" in blob or "\\qml\\" in blob or blob.endswith(".qml") or "/qmldir" in blob:
        return any(needle in blob for needle in QML_DROP)
    if "/translations/" in blob or "qt_" in blob and blob.endswith(".qm"):
        return True
    return False


def filter_binaries(toc):
    kept = []
    dropped = 0
    for entry in toc:
        if _drop_binary(_blob(entry)):
            dropped += 1
            continue
        kept.append(entry)
    print(f"[XeusGUI.spec] binaries kept={len(kept)} dropped={dropped}", file=sys.stderr)
    return kept


def filter_datas(toc):
    kept = []
    dropped = 0
    for entry in toc:
        if _drop_data(_blob(entry)):
            dropped += 1
            continue
        kept.append(entry)
    print(f"[XeusGUI.spec] datas kept={len(kept)} dropped={dropped}", file=sys.stderr)
    return kept


def app_qml_datas(spec_root: str):
    files = ("app.qml", "Screen01.qml", "Clinicalmode.qml", "Constants.qml", "qmldir")
    datas = []
    for name in files:
        src = os.path.join(spec_root, name)
        if not os.path.isfile(src):
            raise FileNotFoundError(f"Missing QML/resource: {src}")
        datas.append((src, "."))
    return datas
