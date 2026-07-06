#!/usr/bin/env pythong
"""QEMU world pipeline status — botnet edge/DNS/DHCP/witness lanes for AmmoDrive racks."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
PIPELINE = INSTALL / "GrokLab" / "deploy" / "qemu-world-pipeline.py"


def _load_racks_mod() -> Any | None:
    py = INSTALL / "lib" / "field-zachub-qemu-racks.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_zachub_qemu_racks", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
        doc["qemu_source"] = "GrokLab/deploy/qemu-world-pipeline.py"
        doc["not_team_field1"] = True
        doc["no_team_drive_servers"] = True
        doc["deploy_root"] = "GrokLab/deploy"
        doc["edge_roles"] = ["dhcp", "dns", "edge", "github_mirror_witness"]
        doc["botnet_roles"] = ["dns_relay", "dhcp_relay", "truth_mirror"]
        doc["zachub_racks_api"] = "/api/field-zachub-qemu-racks"

        racks_mod = _load_racks_mod()
        if racks_mod and hasattr(racks_mod, "build_slots"):
            slots = racks_mod.build_slots(doc)
            doc["slots"] = slots
            doc["gaming_roles"] = doc["edge_roles"]
            doc["tunnel_port_base"] = int(
                doc.get("tunnel_port_base")
                or (slots[0].get("tunnel", 19477) - slots[0].get("slot", 0) if slots else 19477)
            )
        else:
            port_base = int(doc.get("tunnel_port_base") or 19477)
            slots_n = int(doc.get("target") or doc.get("slots_total") or 6)
            slots_n = max(1, min(slots_n, int(os.environ.get("NEXUS_GLOBAL_SERVER_TARGET") or 2500)))
            cycle = ["dhcp", "dns", "edge", "github_mirror_witness"]
            doc["slots"] = [
                {
                    "slot": i,
                    "tunnel": port_base + i,
                    "id": f"qemu-world-{i}",
                    "field_id": f"qemu-rack-{i}",
                    "primary_role": cycle[i % len(cycle)],
                    "roles": [cycle[i % len(cycle)], "dns_relay", "dhcp_relay", "truth_mirror", "edge"],
                }
                for i in range(slots_n)
            ]
            doc["gaming_roles"] = doc["edge_roles"]
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