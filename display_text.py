"""Display text block: Modbus input registers 600+ (как text600 в test_modbus.py)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from modbus_client import ModbusClient

REG600_START = 600
REG600_CHUNK = 30
REG600_MAX_REGISTERS = 150
REG600_HEADER_BYTES = 6


def registers_to_bytes(registers: list[int]) -> bytes:
    data = bytearray()
    for reg in registers:
        v = int(reg) & 0xFFFF
        data.append((v >> 8) & 0xFF)
        data.append(v & 0xFF)
    return bytes(data)


def parse_display_text(registers: list[int]) -> str:
    """Из блока 600+ извлечь текст (после 6-байтного заголовка)."""
    if not registers:
        return ""
    data = registers_to_bytes(registers)
    if len(data) < REG600_HEADER_BYTES:
        return ""
    text_raw = data[REG600_HEADER_BYTES:]
    null_pos = text_raw.find(b"\x00")
    if null_pos >= 0:
        text_raw = text_raw[:null_pos]
    if not text_raw or not text_raw.strip(b"\x00 \t\r\n"):
        return ""
    return text_raw.decode("utf-8", errors="replace").strip()


def read_display_registers_fast(client: ModbusClient) -> list[int]:
    """FC04: один запрос 600–629 (как text600 по умолчанию)."""
    chunk = client.read_input_registers(REG600_START, REG600_CHUNK)
    if chunk is None:
        return []
    if all(int(r) == 0 for r in chunk):
        return []
    return [int(r) for r in chunk]


def read_display_registers(
    client: ModbusClient,
    start: int = REG600_START,
    chunk_size: int = REG600_CHUNK,
    max_registers: int = REG600_MAX_REGISTERS,
) -> list[int]:
    """
    FC04: читаем 600, 630, … пока chunk не вернёт ошибку или все нули.
    На устройстве обычно 600–629; дальше — Illegal Data Address.
    """
    out: list[int] = []
    addr = start
    while len(out) < max_registers:
        qty = min(chunk_size, max_registers - len(out))
        chunk = client.read_input_registers(addr, qty)
        if chunk is None:
            break
        if all(int(r) == 0 for r in chunk):
            if out:
                break
            return []
        out.extend(int(r) for r in chunk)
        if len(chunk) < qty:
            break
        addr += qty
    return out


def read_and_parse_display_text(client: ModbusClient) -> Optional[str]:
    regs = read_display_registers_fast(client)
    if not regs:
        return None
    text = parse_display_text(regs)
    return text if text else None
