#!/usr/bin/env pythong
"""Map NEXUS_FIELD_* runtime to AMOURANTHRTX FieldFabric modules."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "."))
MAP_FILE = INSTALL / "data" / "amouranthrtx-field-fabric-map.json"


def _load_map() -> dict[str, Any]:
    if not MAP_FILE.is_file():
        return {"schema": "amouranthrtx-field-fabric/v1", "fabric": {}}
    try:
        return json.loads(MAP_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "amouranthrtx-field-fabric/v1", "fabric": {}}


def _nexus_env_snapshot(keys: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in keys:
        val = os.environ.get(key)
        if val is not None:
            out[key] = val
    return out


def build_panel() -> dict[str, Any]:
    doc = _load_map()
    fabric = doc.get("fabric") if isinstance(doc.get("fabric"), dict) else {}
    modules: list[dict[str, Any]] = []
    for name, spec in fabric.items():
        if not isinstance(spec, dict):
            continue
        keys = spec.get("nexus_keys") if isinstance(spec.get("nexus_keys"), list) else []
        modules.append({
            "id": name,
            "amouranthrtx": spec.get("amouranthrtx"),
            "role": spec.get("role"),
            "nexus_env": _nexus_env_snapshot([str(k) for k in keys]),
            "active": any(os.environ.get(str(k), "0") not in ("", "0") for k in keys),
        })
    return {
        "schema": "field-fabric-bridge/v1",
        "map_path": str(MAP_FILE),
        "module_count": len(modules),
        "modules": modules,
        "heat_crush_threshold": float(os.environ.get("NEXUS_HEAT_CRUSH_THRESHOLD", "0.7")),
        "rust_core": os.environ.get("NEXUS_RUST_CORE", "0") == "1",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd == "panel":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-fabric-bridge.py [panel]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
