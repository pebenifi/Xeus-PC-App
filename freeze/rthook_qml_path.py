"""Ensure bundled QML is visible when the frozen app starts."""

import os
import sys

meipass = getattr(sys, "_MEIPASS", None)
if meipass:
    existing = os.environ.get("QML2_IMPORT_PATH", "")
    parts = [meipass]
    if existing:
        parts.append(existing)
    os.environ["QML2_IMPORT_PATH"] = os.pathsep.join(parts)
    os.environ["QML_IMPORT_PATH"] = os.environ["QML2_IMPORT_PATH"]
