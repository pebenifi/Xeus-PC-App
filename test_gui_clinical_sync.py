#!/usr/bin/env python3
"""
GUI Clinical sync test: loads app, switches to Clinicalmode, clicks relay buttons,
verifies 1021 / manager / QML stay in sync.
"""
from __future__ import annotations

import os
import sys
import time

from PySide6.QtCore import QTimer, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from modbus_manager import ModbusManager

RELAY_BUTTONS = (
    ("Water Chiller", "water_chiller", 0),
    ("Magnet PSU", "magnet_psu", 1),
    ("Laser PSU", "laser_psu", 2),
    ("Vacuum Pump", "vacuum_pump", 3),
    ("Vacuum Gauge", "vacuum_gauge", 4),
    ("PID Controller", "pid_controller", 5),
)


def find_by_text(root: QObject, text: str) -> QObject | None:
    for obj in root.findChildren(QObject):
        try:
            if obj.property("text") == text:
                return obj
        except Exception:
            pass
    return None


def read_1021_via_batch(mgr: ModbusManager, app: QGuiApplication, timeout: float = 15.0) -> int | None:
    """Читаем 1021 через clinical batch (не конкурируем с IR/NMR priority)."""
    result: dict = {"v": None}

    def slot(key: str, val: object) -> None:
        if key == "clinical" and isinstance(val, dict) and "1021" in val:
            result["v"] = int(val["1021"])

    mgr._io_worker.readFinished.connect(slot)
    mgr._readClinicalBatch()
    deadline = time.time() + timeout
    while result["v"] is None and time.time() < deadline:
        app.processEvents()
    try:
        mgr._io_worker.readFinished.disconnect(slot)
    except Exception:
        pass
    return result["v"]


def read_1021_in_app(mgr: ModbusManager, app: QGuiApplication, timeout: float = 3.0) -> int | None:
    result: dict = {"v": None}

    def slot(key: str, val: object) -> None:
        if key == "1021" and val is not None:
            result["v"] = int(val)

    mgr._io_worker.readFinished.connect(slot)
    mgr._readRelay1021Now()
    deadline = time.time() + timeout
    while result["v"] is None and time.time() < deadline:
        app.processEvents()
    try:
        mgr._io_worker.readFinished.disconnect(slot)
    except Exception:
        pass
    return result["v"]


def relay_bit(raw: int | None, bit: int) -> bool | None:
    if raw is None:
        return None
    return bool((raw & 0xFF) & (1 << bit))


def main() -> int:
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Fusion")
    app = QGuiApplication(sys.argv)
    qmlRegisterType(ModbusManager, "XeusGUI", 1, 0, "ModbusManager")
    mgr = ModbusManager()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("modbusManager", mgr)
    base = os.path.dirname(os.path.abspath(__file__))
    engine.addImportPath(base)
    engine.load(os.path.join(base, "app.qml"))
    if not engine.rootObjects():
        print("FAIL: QML not loaded")
        return 1

    root = engine.rootObjects()[0]
    errors: list[str] = []
    exit_code = 1
    phase = {"step": 0}

    def fail(msg: str) -> None:
        errors.append(msg)
        print(f"FAIL: {msg}")

    def ok(msg: str) -> None:
        print(f"OK: {msg}")

    def process(ms: int = 400) -> None:
        end = time.time() + ms / 1000.0
        while time.time() < end:
            app.processEvents()

    def check_relay(name: str, key: str, bit: int, label: str) -> bool:
        raw = read_1021_via_batch(mgr, app)
        dev = relay_bit(raw, bit)
        ui_mgr = mgr._relay_states.get(key)
        btn = find_by_text(root, name)
        ui_btn = bool(btn.property("checked")) if btn else None
        if dev is None:
            fail(f"{label}: cannot read 1021")
            return False
        if dev != ui_mgr:
            fail(f"{label}: driver={dev} mgr={ui_mgr} raw=0x{raw:04X}")
            return False
        if ui_btn is not None and ui_btn != dev:
            fail(f"{label}: QML checked={ui_btn} driver={dev}")
            return False
        ok(f"{label}: driver=mgr=ui={dev} (1021=0x{raw:04X})")
        return True

    def run_clicks(step_idx: int = 0) -> None:
        if step_idx >= len(RELAY_BUTTONS):
            finish(0 if not errors else 2)
            return
        name, key, bit = RELAY_BUTTONS[step_idx]
        btn = find_by_text(root, name)
        if btn is None:
            fail(f"Button not found: {name}")
            finish(2)
            return
        before = mgr._relay_states.get(key, False)
        target = not before
        print(f"\n--- Clinical click {name}: {before} -> {target} ---")
        btn.setProperty("checked", target)
        btn.clicked.emit()
        process(800)
        if not check_relay(name, key, bit, name):
            finish(2)
            return
        QTimer.singleShot(100, lambda: run_clicks(step_idx + 1))

    def finish(code: int) -> None:
        nonlocal exit_code
        exit_code = code
        print("\n=== SUMMARY ===")
        if errors:
            for e in errors:
                print(f"  - {e}")
        else:
            print("Clinical relay/GUI/driver checks passed.")
        mgr.setClinicalForeground(False)
        mgr._shutdownIoThread()
        QTimer.singleShot(200, app.quit)

    def after_clinical_ready() -> None:
        process(3500)
        if not mgr._clinical_foreground:
            fail("clinical foreground not active")
            finish(2)
            return
        print("\n=== Initial Clinical sync ===")
        for name, key, bit in RELAY_BUTTONS:
            if not check_relay(name, key, bit, f"init {name}"):
                finish(2)
                return
        run_clicks(0)

    def after_connect() -> None:
        process(500)
        print("\n=== Switch to Clinicalmode ===")
        root.changeScreen("Clinicalmode")
        process(2000)
        QTimer.singleShot(100, after_clinical_ready)

    def on_connected(connected: bool) -> None:
        if connected and phase["step"] == 0:
            phase["step"] = 1
            QTimer.singleShot(100, after_connect)

    mgr.connectionStatusChanged.connect(on_connected)
    mgr.connect()

    QTimer.singleShot(120000, lambda: (fail("timeout 120s"), finish(2)))

    app.exec()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
