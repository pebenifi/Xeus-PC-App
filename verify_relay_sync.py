#!/usr/bin/env python3
"""Проверка синхронизации реле 1021: UI ↔ драйвер для всех 7 реле."""
from __future__ import annotations

import sys
import time

from PySide6.QtCore import QCoreApplication, QTimer

from modbus_manager import ModbusManager

RELAYS = [
    (1, "water_chiller", "setWaterChiller"),
    (2, "magnet_psu", "setMagnetPSU"),
    (3, "laser_psu", "setLaserPSU"),
    (4, "vacuum_pump", "setVacuumPump"),
    (5, "vacuum_gauge", "setVacuumGauge"),
    (6, "pid_controller", "setPIDController"),
]

BIT = {name: 1 << (num - 1) for num, name, _ in RELAYS}


def ui_matches_cached_raw(mgr: ModbusManager) -> tuple[bool, int]:
    raw = mgr._relay_1021_raw
    low = raw & 0xFF
    for _, name, _ in RELAYS:
        expected = bool(low & BIT[name])
        if mgr._relay_states[name] != expected:
            return False, raw
    return True, raw


def main() -> int:
    app = QCoreApplication(sys.argv)
    mgr = ModbusManager()
    exit_code = 1
    errors: list[str] = []
    step = {"i": 0, "toggle_on": True}

    def fail(msg: str) -> None:
        errors.append(msg)
        print(f"FAIL: {msg}")

    def shutdown(code: int) -> None:
        nonlocal exit_code
        exit_code = code
        mgr._shutdownIoThread()
        app.quit()

    def verify_all_relays(label: str) -> bool:
        ok, raw = ui_matches_cached_raw(mgr)
        if not ok:
            fail(f"{label}: UI != cached 1021 raw=0x{raw:04X}")
            for _, name, _ in RELAYS:
                low = raw & 0xFF
                exp = bool(low & BIT[name])
                if mgr._relay_states[name] != exp:
                    print(f"  {name}: UI={mgr._relay_states[name]} expected={exp}")
            return False
        print(f"OK {label}: UI matches 1021 (raw=0x{raw:04X})")
        return True

    def run_step() -> None:
        if step["i"] >= len(RELAYS):
            # verify 1541 does NOT overwrite relay UI
            wc_ui = mgr._relay_states["water_chiller"]
            wc_drv = mgr._water_chiller_state
            low = mgr._relay_1021_raw & 0xFF
            wc_from_1021 = bool(low & BIT["water_chiller"])
            print(f"Water chiller relay UI={wc_ui} from1021={wc_from_1021}, driver1541={wc_drv}")
            if wc_ui != wc_from_1021:
                fail("final: water chiller relay UI != bit in 1021")
            else:
                print("OK: relay state independent from 1541 driver state")
            print("\n=== Summary ===")
            if errors:
                for e in errors:
                    print(f"  - {e}")
                shutdown(2)
            else:
                print("All relay sync checks passed")
                shutdown(0)
            return

        num, name, method_name = RELAYS[step["i"]]
        target = step["toggle_on"]
        setter = getattr(mgr, method_name)
        print(f"Step {step['i']+1}: {method_name}({target})")
        if not setter(target):
            fail(f"{method_name} returned False")
            shutdown(2)
            return
        QTimer.singleShot(600, verify_step)

    def verify_step() -> None:
        mgr._readRelay1021Now()
        QTimer.singleShot(250, do_verify)

    def do_verify() -> None:
        if not verify_all_relays(f"after {RELAYS[step['i']][2]}"):
            shutdown(2)
            return
        if step["toggle_on"]:
            step["toggle_on"] = False
            QTimer.singleShot(100, run_step)
        else:
            step["toggle_on"] = True
            step["i"] += 1
            QTimer.singleShot(100, run_step)

    def on_connected(connected: bool) -> None:
        if not connected:
            return
        print("Connected, waiting for initial batch...")
        QTimer.singleShot(1500, initial_sync)

    def initial_sync() -> None:
        if verify_all_relays("initial"):
            run_step()
        else:
            shutdown(2)

    mgr.connectionStatusChanged.connect(on_connected)
    mgr.connect()
    QTimer.singleShot(120000, lambda: (fail("timeout"), shutdown(2)))

    app.exec()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
