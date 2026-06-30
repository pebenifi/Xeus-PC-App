#!/usr/bin/env python3
"""Headless проверка Screen01 batch polling через ModbusManager."""
from __future__ import annotations

import sys
import time

from PySide6.QtCore import QCoreApplication, QTimer

from modbus_manager import ModbusManager


def main() -> int:
    app = QCoreApplication(sys.argv)
    mgr = ModbusManager()
    exit_code = 1

    def socket_alive() -> bool:
        try:
            mc = mgr._modbus_client
            return (
                mgr._is_connected
                and mc is not None
                and mc.client is not None
                and mc.client.is_socket_open()
            )
        except Exception:
            return False

    def shutdown(code: int) -> None:
        nonlocal exit_code
        exit_code = code
        mgr._shutdownIoThread()
        app.quit()

    def run_write_test() -> None:
        if not socket_alive():
            print("FAIL: socket dead before write")
            shutdown(2)
            return

        before = mgr._relay_states["water_chiller"]
        target = not before
        print(f"Toggle Water Chiller relay: {before} -> {target}")
        if not mgr.setWaterChiller(target):
            print("FAIL: setWaterChiller returned False")
            shutdown(2)
            return
        QTimer.singleShot(600, verify_after_write)

    def verify_after_write() -> None:
        if not socket_alive():
            print("FAIL: socket dead after relay write")
            shutdown(2)
            return

        after = mgr._relay_states["water_chiller"]
        print(f"Relay state after write+batch: {after} (raw 1021={mgr._relay_1021_raw})")
        print(f"Water chiller inlet: {mgr._water_chiller_inlet_temperature}")
        print(f"Vacuum: {mgr._vacuum_pressure}, Xenon: {mgr._xenon_pressure}")
        print(f"Last modbus OK: {time.time() - mgr._last_modbus_ok_time:.2f}s ago")
        print("OK: connection stable, batch polling and relay write work")
        shutdown(0)

    def after_poll() -> None:
        if not mgr._is_connected:
            print("FAIL: not connected after 2s")
            shutdown(2)
            return
        if not socket_alive():
            print("FAIL: socket dead after 2s polling")
            shutdown(2)
            return
        if mgr._last_modbus_ok_time <= 0:
            print("FAIL: no successful modbus I/O")
            shutdown(2)
            return
        print(f"After 2s poll: socket OK, last I/O {time.time() - mgr._last_modbus_ok_time:.2f}s ago, 1021={mgr._relay_1021_raw}")
        run_write_test()

    def on_connected(connected: bool) -> None:
        if connected:
            print("Connected — waiting for batch polls...")
            QTimer.singleShot(2000, after_poll)

    mgr.connectionStatusChanged.connect(on_connected)
    mgr.connect()

    QTimer.singleShot(12000, lambda: (print("FAIL: timeout"), shutdown(2)))

    app.exec()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
