#!/usr/bin/env pythong
"""FieldFox native messaging bridge — tab egress receipts to NEXUS gatekeeper."""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(__import__("os").environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))


def _read_message() -> dict[str, Any] | None:
    raw_len = sys.stdin.buffer.read(4)
    if len(raw_len) < 4:
        return None
    length = struct.unpack("@I", raw_len)[0]
    data = sys.stdin.buffer.read(length)
    if not data:
        return None
    return json.loads(data.decode("utf-8"))


def _send_message(msg: dict[str, Any]) -> None:
    encoded = json.dumps(msg).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("@I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def handle(msg: dict[str, Any]) -> dict[str, Any]:
    action = (msg.get("action") or "ping").strip()
    if action == "ping":
        return {"ok": True, "bridge": "fieldfox-native/v1", "queen": True, "hold_all_gates": True}
    if action == "gate_check":
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "field_queen_browser", INSTALL / "lib" / "field-queen-browser.py"
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        gate_id = str(msg.get("gate_id") or "")
        return mod.gate_check(gate_id)
    if action == "panel":
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "field_queen_browser", INSTALL / "lib" / "field-queen-browser.py"
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        return mod.panel_json()
    return {"ok": False, "error": f"unknown action: {action}"}


def main() -> int:
    while True:
        msg = _read_message()
        if msg is None:
            break
        _send_message(handle(msg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())