#!/usr/bin/env python3
"""Test: start program 2091, poll display text 600+, print log lines."""
from __future__ import annotations

import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from modbus_manager import ModbusManager

PROGRAM_REG = 2091  # Timed Polarization Decay


def main() -> int:
    app = QApplication(sys.argv)
    mgr = ModbusManager()
    logs: list[str] = []

    def on_log(msg: str) -> None:
        logs.append(msg)
        print(msg)

    mgr.logMessageChanged.connect(on_log)

    def after_connect() -> None:
        mgr.setClinicalForeground(True)
        print(f"Starting program register {PROGRAM_REG}...")
        mgr.startAdvancedProgram(PROGRAM_REG)
        mgr.startDisplayTextPolling()
        print("Polling display text 600+ (30s)...")

    def finish() -> None:
        mgr.stopDisplayTextPolling()
        mgr.setClinicalForeground(False)
        display_lines = [l for l in logs if "Display:" in l]
        print("\n=== SUMMARY ===")
        print(f"Total log lines: {len(logs)}")
        print(f"Display lines: {len(display_lines)}")
        for line in display_lines:
            print(f"  {line}")
        mgr._shutdownIoThread()
        QTimer.singleShot(200, app.quit)

    def on_connected(ok: bool) -> None:
        if ok:
            QTimer.singleShot(300, after_connect)

    mgr.connectionStatusChanged.connect(on_connected)
    mgr.connect()

    QTimer.singleShot(45000, finish)

    app.exec()
    return 0 if any("Display:" in l for l in logs) else 2


if __name__ == "__main__":
    sys.exit(main())
