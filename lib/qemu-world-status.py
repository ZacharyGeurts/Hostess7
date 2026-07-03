#!/usr/bin/env pythong
"""QEMU world pipeline status — secure transfer bot lane for C2 + Pages."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
PIPELINE = INSTALL / "GrokLab" / "deploy" / "qemu-world-pipeline.py"


def status_json() -> dict[str, Any]:
    if not PIPELINE.is_file():
        return {
            "ok": False,
            "schema": "qemu-world-pipeline/v1",
            "error": "qemu-world-pipeline.py missing",
            "running": False,
            "completed": 0,
            "target": 0,
        }
    try:
        proc = subprocess.run(
            [sys.executable, str(PIPELINE), "status"],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        doc = json.loads(proc.stdout or "{}")
        doc.setdefault("ok", True)
        doc["schema"] = "qemu-world-pipeline/v1"
        port_base = int(doc.get("tunnel_port_base") or 19477)
        slots_n = int(doc.get("target") or doc.get("slots_total") or 6)
        slots_n = max(1, min(slots_n, 16))
        doc["gaming_roles"] = ["sap_relay", "frame_witness", "rom_caravan"]
        doc["slots"] = [
            {
                "slot": i,
                "tunnel": port_base + i,
                "id": f"qemu-world-{i}",
                "roles": ["sap_relay", "frame_witness"],
            }
            for i in range(slots_n)
        ]
        return doc
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {
            "ok": False,
            "schema": "qemu-world-pipeline/v1",
            "error": str(exc),
            "running": False,
            "completed": 0,
            "target": 0,
        }


def main() -> int:
    print(json.dumps(status_json(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())