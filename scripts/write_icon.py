#!/usr/bin/env python3
"""Write a tiny PNG icon (stdlib only) for AppImage / optional .ico conversion."""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_png(path: Path, size: int = 256, rgb=(0x29, 0x35, 0x55)) -> None:
    raw = b""
    r, g, b = rgb
    row = b"\x00" + bytes([r, g, b]) * size
    raw = row * size
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "freeze/xeusgui.png")
    write_png(out)
    print(out)
