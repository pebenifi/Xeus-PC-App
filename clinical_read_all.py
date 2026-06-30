#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clinical (Screen02): одно подключение, все регистры Screen01 + Clinical подряд без sleep.
"""
from __future__ import annotations

import sys
import time

from modbus_client import ModbusClient
from clinical_batch import CLINICAL_PARAM_REGISTERS, clinical_batch_read
from screen01_read_all import SCREEN01_READS, _read_one

IP = "192.168.4.1"
PORT = 503
UNIT_ID = 1


def main() -> int:
    print(f"Clinical read-all — {IP}:{PORT} unit={UNIT_ID}")
    print("Single connect, no delays, no reconnect\n")

    client = ModbusClient(host=IP, port=PORT, unit_id=UNIT_ID, framer="rtu")
    t0 = time.perf_counter()

    if not client.connect():
        print("CONNECT FAILED")
        return 1

    print(f"Connected in {(time.perf_counter() - t0) * 1000:.0f} ms\n")

    # --- Screen01 IO registers (individual scan for OK/FAIL table) ---
    print("=== Screen01 IO registers ===")
    print(f"{'Addr':>4}  {'Label':32s}  {'Status':6s}  Detail")
    print("-" * 90)
    ok = fail = conn = 0
    broken_at: str | None = None
    for address, label, fc in SCREEN01_READS:
        status, detail = _read_one(client, address, fc)
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
            broken_at = f"{address} ({label}): socket closed"
            break

    if conn == 0 and client.client is not None and client.client.is_socket_open():
        print("\n=== Clinical parameter registers (FC04) ===")
        print(f"{'Addr':>4}  {'Status':6s}  Detail")
        print("-" * 60)
        for address in CLINICAL_PARAM_REGISTERS:
            if address in (5010, 5020, 5030, 5060):
                continue
            if address in (5011, 5021, 5031, 5061):
                regs = client.read_input_registers(address, 2)
                if regs is None or len(regs) < 2:
                    status, detail = "FAIL", f"uint32 pair @ {address}"
                    fail += 1
                else:
                    status, detail = "OK", f"lo={regs[0]} hi={regs[1]}"
                    ok += 1
            else:
                v = client.read_input_register(address)
                if client.client is None or not client.client.is_socket_open():
                    status, detail = "CONN", "socket closed"
                    conn += 1
                    broken_at = f"{address}: socket closed"
                    break
                if v is None:
                    status, detail = "FAIL", "FC04"
                    fail += 1
                else:
                    status, detail = "OK", f"value={v} (0x{int(v):04X})"
                    ok += 1
            print(f"{address:4d}  {status:6s}  {detail}")

        if conn == 0 and client.client is not None and client.client.is_socket_open():
            print("\n=== Unified clinical_batch_read() ===")
            batch = clinical_batch_read(client)
            sections = (
                "1020", "1021", "1111", "1131", "power_supply", "1331", "1341",
                "pid_controller", "1421", "water_chiller", "alicats", "1701", "laser",
                "seop_parameters", "calculated_parameters", "measured_parameters",
                "additional_parameters", "manual_mode_settings",
            )
            for key in sections:
                present = key in batch
                extra = ""
                if present and isinstance(batch[key], dict):
                    extra = f" ({len(batch[key])} fields)"
                print(f"  {key:24s}  {'OK' if present else 'MISSING'}{extra}")
            print(f"  _ok={batch.get('_ok')}  _conn={batch.get('_conn')}")

    elapsed = time.perf_counter() - t0
    still_open = client.client is not None and client.client.is_socket_open()
    client.disconnect()

    print("\n" + "=" * 90)
    print(f"OK={ok}  FAIL={fail}  CONN={conn}")
    print(f"Elapsed: {elapsed * 1000:.0f} ms ({elapsed:.2f} s)")
    print(f"Socket alive at end: {still_open}")
    if broken_at:
        print(f"Connection lost at: {broken_at}")
    else:
        print("Connection survived full Clinical read pass.")

    return 0 if conn == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
