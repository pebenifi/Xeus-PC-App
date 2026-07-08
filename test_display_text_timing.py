#!/usr/bin/env python3
"""Measure delay between Display log lines (clinical batch polling)."""
from __future__ import annotations

import re
import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from modbus_manager import ModbusManager

PROGRAM_REG = 2091
DURATION_S = 35


def main() -> int:
    app = QApplication(sys.argv)
    mgr = ModbusManager()
    display_lines: list[tuple[float, str]] = []
    t0 = time.time()

    def on_log(msg: str) -> None:
        if "Display:" in msg:
            display_lines.append((time.time() - t0, msg))
            print(msg)

    mgr.logMessageChanged.connect(on_log)

    def after_connect() -> None:
        mgr.setClinicalForeground(True)
        mgr.startAdvancedProgram(PROGRAM_REG)
        mgr.startDisplayTextPolling()
        print(f"Timing display text for {DURATION_S}s...")

    def finish() -> None:
        mgr.stopDisplayTextPolling()
        mgr.setClinicalForeground(False)
        print("\n=== TIMING ===")
        print(f"Display lines: {len(display_lines)}")
        if len(display_lines) >= 2:
            gaps = []
            for i in range(1, len(display_lines)):
                gap = display_lines[i][0] - display_lines[i - 1][0]
                gaps.append(gap)
                print(f"  gap {i}: {gap:.2f}s  {display_lines[i][1][:60]}")
            print(f"  avg gap: {sum(gaps) / len(gaps):.2f}s  max: {max(gaps):.2f}s")
        mgr._shutdownIoThread()
        QTimer.singleShot(200, app.quit)

    mgr.connectionStatusChanged.connect(
        lambda ok: QTimer.singleShot(300, after_connect) if ok else None
    )
    mgr.connect()
    QTimer.singleShot(DURATION_S * 1000, finish)
    app.exec()
    return 0 if display_lines else 2


if __name__ == "__main__":
    sys.exit(main())
