#!/usr/bin/env python3
"""
Live Clinical verification: real app.qml, Clinical screen, click IO controls,
verify Modbus (1021/1111/1131) via same TCP connection.
"""
from __future__ import annotations

import os
import sys
import time

from PySide6.QtCore import QTimer, QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from modbus_manager import ModbusManager

RELAY_ROWS = (
    ("Water Chiller:", "water_chiller", 0),
    ("Magnet PSU:", "magnet_psu", 1),
    ("Laser PSU:", "laser_psu", 2),
    ("Vacuum Pump:", "vacuum_pump", 3),
    ("Vacuum Gauge:", "vacuum_gauge", 4),
    ("PID Controller:", "pid_controller", 5),
)


def process(app: QGuiApplication, ms: int = 400) -> None:
    end = time.time() + ms / 1000.0
    while time.time() < end:
        app.processEvents()


def clinical_root(window: QObject) -> QObject | None:
    for obj in window.findChildren(QObject):
        if obj.metaObject().className() == "QQuickLoader":
            src = obj.property("source")
            if src and "Clinicalmode" in str(src):
                item = obj.property("item")
                if item:
                    return item
    return None


def find_by_text(scope: QObject, text: str) -> QObject | None:
    for obj in scope.findChildren(QObject):
        try:
            if obj.property("text") == text:
                return obj
        except Exception:
            pass
    return None


def find_checkable_button_near_label(scope: QObject, label: str) -> QObject | None:
    label_obj = find_by_text(scope, label)
    if label_obj is None:
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


def read_clinical_batch(mgr: ModbusManager, app: QGuiApplication, timeout: float = 30.0) -> dict:
    result: dict = {"batch": None}

    def slot(key: str, val: object) -> None:
        if key == "clinical" and isinstance(val, dict):
            result["batch"] = val

    mgr._io_worker.readFinished.connect(slot)
    mgr._readClinicalBatch()
    deadline = time.time() + timeout
    while result["batch"] is None and time.time() < deadline:
        app.processEvents()
    try:
        mgr._io_worker.readFinished.disconnect(slot)
    except Exception:
        pass
    return result["batch"] or {}


def relay_bit(raw: int, bit: int) -> bool:
    return bool((int(raw) & 0xFF) & (1 << bit))


def valve_bit(raw: int, valve_index: int) -> bool:
    return bool(int(raw) & (1 << valve_index))


def fan_bit(batch: dict, fan_index: int) -> bool | None:
    fans = batch.get("1131")
    if not isinstance(fans, dict):
        return None
    r1131 = int(fans.get("1131", 0))
    mapping = {0: 0, 1: 1, 2: 2, 3: 3, 4: 8, 5: 9, 6: 4, 7: 5, 8: 6, 9: 7}
    if fan_index == 10:
        r1132 = int(fans.get("1132", 0))
        return bool(r1132 & 0x03)
    bit = mapping.get(fan_index)
    if bit is None:
        return None
    return bool(r1131 & (1 << bit))


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
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        if errors:
            for e in errors:
                print(f"  FAIL: {e}")
        else:
            print("  All Clinical live checks passed.")
        mgr.setClinicalForeground(False)
        mgr._shutdownIoThread()
        QTimer.singleShot(300, app.quit)

    def wait_connected(timeout: float = 45.0) -> bool:
        deadline = time.time() + timeout
        while not mgr._is_connected and time.time() < deadline:
            app.processEvents()
            time.sleep(0.05)
        return mgr._is_connected

    def read_batch() -> dict:
        batch = read_clinical_batch(mgr, app)
        if batch.get("1021") is not None:
            return batch
        process(app, 800)
        return read_clinical_batch(mgr, app)

    def check_relays(clinical: QObject) -> bool:
        batch = read_batch()
        raw = batch.get("1021")
        if raw is None:
            fail(f"1021 missing from clinical batch (connected={mgr._is_connected}, fg={mgr._clinical_foreground})")
            return False
        raw_i = int(raw)
        all_ok = True
        for label, key, bit in RELAY_ROWS:
            dev = relay_bit(raw_i, bit)
            ui_mgr = mgr._relay_states.get(key)
            btn = find_checkable_button_near_label(clinical, label)
            ui_btn = bool(btn.property("checked")) if btn else None
            if dev != ui_mgr:
                fail(f"{label} driver={dev} mgr={ui_mgr} raw=0x{raw_i:04X}")
                all_ok = False
            elif ui_btn is not None and ui_btn != dev:
                fail(f"{label} QML={ui_btn} driver={dev}")
                all_ok = False
            else:
                ok(f"{label.rstrip(':')} sync={dev} (1021=0x{raw_i:04X})")
        return all_ok

    def toggle_valves_fans(clinical: QObject) -> None:
        mgr.enableValvePolling()
        mgr.enableFanPolling()
        process(app, 400)
        print("\n--- Valves: toggle X6 ---")
        btn = find_checkable_button_near_label(clinical, "X6:")
        if btn is None:
            fail("X6 valve button not found")
            finish(2)
            return
        target = not bool(btn.property("checked"))
        btn.setProperty("checked", target)
        btn.clicked.emit()
        process(app, 900)
        batch = read_batch()
        raw1111 = batch.get("1111")
        if raw1111 is None:
            fail("1111 missing after valve click")
            finish(2)
            return
        dev = valve_bit(int(raw1111), 5)
        mgr_state = mgr._valve_states.get(5)
        ui_btn = bool(btn.property("checked"))
        if dev != target or mgr_state != dev or ui_btn != dev:
            fail(f"X6: want={target} dev={dev} mgr={mgr_state} qml={ui_btn} raw=0x{int(raw1111):04X}")
            finish(2)
            return
        ok(f"X6 valve verified open={dev} (1111=0x{int(raw1111):04X})")

        print("\n--- Fan: toggle Inlet Fan 1 ---")
        btn_f = find_checkable_button_near_label(clinical, "Inlet Fan 1:")
        if btn_f is None:
            fail("Inlet Fan 1 button not found")
            finish(2)
            return
        target_f = not bool(btn_f.property("checked"))
        btn_f.setProperty("checked", target_f)
        btn_f.clicked.emit()
        process(app, 900)
        batch = read_batch()
        dev_f = fan_bit(batch, 0)
        mgr_f = mgr._fan_states.get(0)
        ui_f = bool(btn_f.property("checked"))
        if dev_f is None or dev_f != target_f or mgr_f != dev_f or ui_f != dev_f:
            fail(f"Inlet Fan 1: want={target_f} dev={dev_f} mgr={mgr_f} qml={ui_f}")
            finish(2)
            return
        ok(f"Inlet Fan 1 verified on={dev_f}")
        finish(0)

    def toggle_relays(clinical: QObject) -> None:
        print("\n--- External Relays: toggle each ---")
        for label, key, bit in RELAY_ROWS:
            btn = find_checkable_button_near_label(clinical, label)
            if btn is None:
                fail(f"relay button not found: {label}")
                finish(2)
                return
            before = bool(btn.property("checked"))
            target = not before
            print(f"  click {label.rstrip(':')}: {before} -> {target}")
            btn.setProperty("checked", target)
            btn.clicked.emit()
            process(app, 900)
            batch = read_batch()
            raw = batch.get("1021")
            if raw is None:
                fail(f"{label} no 1021 after click")
                finish(2)
                return
            dev = relay_bit(int(raw), bit)
            ui_mgr = mgr._relay_states.get(key)
            ui_btn = bool(btn.property("checked"))
            if dev != target or dev != ui_mgr or ui_btn != dev:
                fail(f"{label} after click: want={target} dev={dev} mgr={ui_mgr} qml={ui_btn}")
                finish(2)
                return
            ok(f"{label.rstrip(':')} click verified dev=mgr=qml={dev}")
        toggle_valves_fans(clinical)

    def run_clinical_tests() -> None:
        process(app, 6000)
        clinical = clinical_root(window)
        if clinical is None:
            fail("Clinicalmode item not loaded")
            finish(2)
            return
        mgr.enableRelayPolling()
        print("\n=== Initial relay sync (Clinical) ===")
        if not check_relays(clinical):
            finish(2)
            return
        toggle_relays(clinical)

    def start() -> None:
        print("Connecting to Modbus 192.168.4.1:503 ...")
        mgr.connect()
        if not wait_connected():
            fail("Modbus not connected within 45s")
            finish(2)
            return
        print("Connected. Switching to Clinicalmode ...")
        window.changeScreen("Clinicalmode")
        process(app, 2000)
        run_clinical_tests()

    QTimer.singleShot(300, start)
    QTimer.singleShot(240000, lambda: (fail("timeout 240s"), finish(2)))

    app.exec()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
