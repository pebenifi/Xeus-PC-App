#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Screen01: одно подключение, все чтения подряд без sleep и без reconnect.
Использует тот же ModbusClient (pymodbus RTU over TCP), что и GUI.
"""
from __future__ import annotations

import sys
import time

from modbus_client import ModbusClient

IP = "192.168.4.1"
PORT = 503
UNIT_ID = 1

# (address, label, fc)  fc: 3=holding, 4=input, "1020"=как в app
SCREEN01_READS: list[tuple] = [
    (1020, "External relays meta", "1020"),
    (1021, "Relays", 4),
    (1111, "Valves", 4),
    (1131, "Fans 1-16 (+1132 pair read)", "1131_1132"),
    (1211, "Laser PSU voltage", 4),
    (1221, "Laser PSU voltage SP", 4),
    (1231, "Laser PSU current", 4),
    (1241, "Laser PSU current SP", 4),
    (1251, "Laser PSU state", 4),
    (1301, "Magnet PSU voltage", 4),
    (1311, "Magnet PSU voltage SP", 4),
    (1321, "Magnet PSU current", 4),
    (1331, "Magnet PSU current SP", 3),
    (1341, "Magnet PSU state", 4),
    (1411, "SEOP cell / PID temp", 4),
    (1421, "SEOP cell setpoint", 3),
    (1431, "PID driver on/off", 4),
    (1511, "Water chiller inlet temp", 4),
    (1521, "Water chiller outlet temp", 4),
    (1531, "Water chiller setpoint", 3),
    (1541, "Water chiller state", 4),
    (1611, "Xenon pressure", 4),
    (1621, "Xenon setpoint", 3),
    (1651, "N2 pressure", 4),
    (1661, "N2 setpoint", 3),
    (1701, "Vacuum pressure", 4),
    (1811, "Laser beam state", 4),
    (1821, "Laser MPD", 4),
    (1831, "Laser output power", 4),
    (1841, "Laser temp", 4),
]


def _read_one(client: ModbusClient, address: int, fc) -> tuple[str, str]:
    """Returns (status, detail) where status is OK|FAIL|CONN."""
    if client.client is None or not client.client.is_socket_open():
        return "CONN", "socket not open"

    if fc == "1020":
        v = client.read_holding_register(address)
        if v is None:
            v = client.read_input_register(address)
        fc_label = "FC03→FC04"
    elif fc == "1131_1132":
        regs = client.read_input_registers(1131, 2)
        if regs is None or len(regs) < 2:
            return "FAIL", "read_input_registers(1131,2)=None"
        return "OK", f"1131={regs[0]} (0x{regs[0]:04X}), 1132={regs[1]} (0x{regs[1]:04X})"
    elif fc == 4:
        v = client.read_input_register(address)
        fc_label = "FC04"
    elif fc == 3:
        v = client.read_holding_register(address)
        fc_label = "FC03"
    else:
        return "FAIL", f"unknown fc {fc!r}"

    if client.client is None or not client.client.is_socket_open():
        return "CONN", f"{fc_label} read closed socket"

    if v is None:
        return "FAIL", fc_label
    return "OK", f"{fc_label} value={v} (0x{int(v):04X})"


def main() -> int:
    print(f"Screen01 read-all — {IP}:{PORT} unit={UNIT_ID}")
    print("Single connect, no delays, no reconnect\n")

    client = ModbusClient(host=IP, port=PORT, unit_id=UNIT_ID, framer="rtu")
    t0 = time.perf_counter()

    if not client.connect():
        print("CONNECT FAILED")
        return 1

    print(f"Connected in {(time.perf_counter() - t0) * 1000:.0f} ms\n")
    print(f"{'Addr':>4}  {'Label':32s}  {'Status':6s}  Detail")
    print("-" * 90)

    ok = fail = conn = 0
    broken_at: str | None = None
    rows: list[tuple] = []

    for address, label, fc in SCREEN01_READS:
        status, detail = _read_one(client, address, fc)
        rows.append((address, label, status, detail))
        print(f"{address:4d}  {label:32s}  {status:6s}  {detail}")

        if status == "OK":
            ok += 1
        elif status == "CONN":
            conn += 1
            broken_at = f"{address} ({label}): {detail}"
            break
        else:
            fail += 1

        if client.client is not None and not client.client.is_socket_open():
            if broken_at is None:
                broken_at = f"{address} ({label}): socket closed after read"
            break

    elapsed = time.perf_counter() - t0
    still_open = client.client is not None and client.client.is_socket_open()
    client.disconnect()

    print("\n" + "=" * 90)
    print(f"Total reads attempted: {len(rows)} / {len(SCREEN01_READS)}")
    print(f"OK={ok}  FAIL={fail}  CONN={conn}")
    print(f"Elapsed: {elapsed * 1000:.0f} ms ({elapsed:.2f} s)")
    print(f"Socket alive at end: {still_open}")
    if broken_at:
        print(f"Connection lost at: {broken_at}")
    else:
        print("Connection survived full Screen01 read pass.")

    failed_regs = [f"{a} {lbl}" for a, lbl, st, _ in rows if st == "FAIL"]
    if failed_regs:
        print(f"\nFailed registers ({len(failed_regs)}):")
        for line in failed_regs:
            print(f"  - {line}")

    return 0 if conn == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
