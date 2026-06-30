#!/usr/bin/env python3
"""Cross-screen sync: toggle on Clinical → Screen01 must match Modbus; vice versa."""
from __future__ import annotations

import os
import sys
import time

from PySide6.QtCore import QTimer, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from modbus_manager import ModbusManager

RELAYS = (
    ("Magnet PSU", "Magnet PSU:", "magnet_psu", 1),
    ("Water Chiller", "Water Chiller:", "water_chiller", 0),
)


def process(app: QGuiApplication, ms: int = 400) -> None:
    end = time.time() + ms / 1000.0
    while time.time() < end:
        app.processEvents()


def find_by_text(scope: QObject, text: str) -> QObject | None:
    for obj in scope.findChildren(QObject):
        try:
            if obj.property("text") == text:
                return obj
        except Exception:
            pass
    return None


def find_checkable_near_label(scope: QObject, label: str) -> QObject | None:
    label_obj = find_by_text(scope, label)
    if not label_obj:
        return None
    node = label_obj
    for _ in range(6):
        if node is None:
            break
        for child in node.findChildren(QObject):
            try:
                if child.property("checkable") is True:
                    return child
            except Exception:
                pass
        node = node.parent()
    return None


def read_1021(mgr: ModbusManager, app: QGuiApplication) -> int | None:
    result: dict = {"v": None}

    def slot(key: str, val: object) -> None:
        if key in ("clinical", "screen01") and isinstance(val, dict) and "1021" in val:
            result["v"] = int(val["1021"])
        elif key == "1021" and val is not None:
            result["v"] = int(val)

    mgr._io_worker.readFinished.connect(slot)
    if mgr._clinical_foreground:
        mgr._readClinicalBatch()
    else:
        mgr._readScreen01Batch()
    deadline = time.time() + 25
    while result["v"] is None and time.time() < deadline:
        app.processEvents()
    try:
        mgr._io_worker.readFinished.disconnect(slot)
    except Exception:
        pass
    return result["v"]


def relay_bit(raw: int, bit: int) -> bool:
    return bool((raw & 0xFF) & (1 << bit))


def main() -> int:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Fusion")
    app = QGuiApplication(sys.argv)
    mgr = ModbusManager()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("modbusManager", mgr)
    base = os.path.dirname(os.path.abspath(__file__))
    engine.addImportPath(base)
    engine.load(os.path.join(base, "app.qml"))
    window = engine.rootObjects()[0]
    errors: list[str] = []
    exit_code = 1

    def fail(msg: str) -> None:
        errors.append(msg)
        print(f"FAIL: {msg}")

    def ok(msg: str) -> None:
        print(f"OK: {msg}")

    def finish(code: int) -> None:
        nonlocal exit_code
        exit_code = code
        print("\n=== SUMMARY ===")
        for e in errors:
            print(f"  - {e}")
        if not errors:
            print("Cross-screen relay sync OK.")
        mgr.setClinicalForeground(False)
        mgr._shutdownIoThread()
        QTimer.singleShot(200, app.quit)

    def check_pair(name: str, clinical_label: str, key: str, bit: int) -> bool:
        raw = read_1021(mgr, app)
        if raw is None:
            fail(f"{name}: cannot read 1021")
            return False
        dev = relay_bit(raw, bit)
        mgr_st = mgr._relay_states.get(key)
        s01 = find_by_text(window, name)
        clinical = None
        for obj in window.findChildren(QObject):
            if obj.metaObject().className() == "QQuickLoader":
                clinical = obj.property("item")
        cbtn = find_checkable_near_label(clinical, clinical_label) if clinical else None
        s01_st = bool(s01.property("checked")) if s01 and s01.property("checkable") else None
        c_st = bool(cbtn.property("checked")) if cbtn else None
        if dev != mgr_st or (s01_st is not None and s01_st != dev) or (c_st is not None and c_st != dev):
            fail(f"{name}: dev={dev} mgr={mgr_st} screen01={s01_st} clinical={c_st} raw=0x{raw:04X}")
            return False
        ok(f"{name}: all screens=0x{raw:04X} bit={dev}")
        return True

    def run_tests() -> None:
        clinical = None
        for obj in window.findChildren(QObject):
            if obj.metaObject().className() == "QQuickLoader":
                clinical = obj.property("item")

        # --- Clinical: toggle Magnet PSU ---
        window.changeScreen("Clinicalmode")
        process(app, 4000)
        mgr.refreshUIOnScreenSwitch()
        process(app, 1000)

        btn_c = find_checkable_near_label(clinical, "Magnet PSU:")
        if not btn_c:
            fail("Clinical Magnet PSU button missing")
            finish(2)
            return
        target = not bool(btn_c.property("checked"))
        btn_c.setProperty("checked", target)
        btn_c.clicked.emit()
        process(app, 1000)

        # --- Switch to Screen01, must match ---
        window.changeScreen("Screen01")
        process(app, 1500)
        if not check_pair("Magnet PSU", "Magnet PSU:", "magnet_psu", 1):
            finish(2)
            return

        # --- Screen01: toggle Water Chiller ---
        btn_s = find_by_text(window, "Water Chiller")
        if not btn_s or not btn_s.property("checkable"):
            fail("Screen01 Water Chiller button missing")
            finish(2)
            return
        target2 = not bool(btn_s.property("checked"))
        btn_s.setProperty("checked", target2)
        btn_s.clicked.emit()
        process(app, 1000)

        window.changeScreen("Clinicalmode")
        process(app, 1500)
        if not check_pair("Water Chiller", "Water Chiller:", "water_chiller", 0):
            finish(2)
            return

        finish(0)

    def start() -> None:
        mgr.connect()
        deadline = time.time() + 45
        while not mgr._is_connected and time.time() < deadline:
            app.processEvents()
            time.sleep(0.05)
        if not mgr._is_connected:
            fail("not connected")
            finish(2)
            return
        run_tests()

    QTimer.singleShot(300, start)
    QTimer.singleShot(180000, lambda: (fail("timeout"), finish(2)))
    app.exec()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
