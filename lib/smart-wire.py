#!/usr/bin/env pythong
"""NEXUS Smart Wire — keyboard leg; delegates to hardware-wire for full field scan."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hardware_wire as hw

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
PANEL_JSON = STATE / "smart-wire.json"


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def scan_wire() -> list[dict[str, Any]]:
    return hw.scan_wire(hw_class_filter="input")


def enforce(*, kill: bool | None = None) -> dict[str, Any]:
    hw.enforce(kill=kill)
    doc = _load_json(PANEL_JSON, {})
    if doc.get("schema") == "nexus-smart-wire/v1":
        return doc
    hits = scan_wire()
    return {
        "schema": "nexus-smart-wire/v1",
        "enabled": hw._enabled(),
        "hit_count": len(hits),
        "hits": hits,
        "hardware_wire": True,
    }


def panel_json() -> dict[str, Any]:
    if PANEL_JSON.is_file():
        doc = _load_json(PANEL_JSON, {})
        if doc.get("schema") == "nexus-smart-wire/v1":
            return doc
    return enforce(kill=False)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "enforce":
        print(json.dumps(enforce(), ensure_ascii=False))
        return 0
    if cmd == "scan":
        print(json.dumps({"hits": scan_wire()}, ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: smart-wire.py [json|scan|enforce]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())