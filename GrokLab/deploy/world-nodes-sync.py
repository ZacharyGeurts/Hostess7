#!/usr/bin/env python3
"""Sync world-nodes.json from world-node-regions.json (30 geographic nodes)."""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

DEPLOY = Path(__file__).resolve().parent
REGIONS_PATH = DEPLOY / "world-node-regions.json"
NODES_PATH = DEPLOY / "world-nodes.json"
PROVISIONED_PATH = DEPLOY / ".qemu-provisioned.json"
ACTIVE_BATCH_PATH = DEPLOY / ".qemu-active-batch"
SSH_KEY = os.environ.get(
    "GROK_LAB_SSH_KEY",
    str(DEPLOY / "world-ssh" / "id_ed25519"),
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _regions_meta() -> tuple[dict, list[dict], int, int, int, int]:
    regions_doc = _load(REGIONS_PATH)
    nodes = regions_doc.get("nodes") or []
    port_base = int(regions_doc.get("ssh_port_base", 2222))
    tunnel_base = int(regions_doc.get("tunnel_port_base", 19477))
    slots = int(regions_doc.get("qemu_concurrent_slots", 3))
    batch_lists: dict[int, list[dict]] = {}
    for spec in nodes:
        batch_lists.setdefault(int(spec.get("batch") or 0), []).append(spec)
    return regions_doc, nodes, port_base, tunnel_base, slots, batch_lists


def _slot_for(spec: dict, batch_lists: dict[int, list[dict]]) -> int:
    batch = int(spec.get("batch") or 0)
    return batch_lists[batch].index(spec)


def _node_entry(
    spec: dict,
    *,
    port: int,
    tunnel: int,
    slot: int,
    key: str,
    slots: int,
) -> dict:
    return {
        "id": spec["id"],
        "region": spec["region"],
        "geo": spec.get("geo", ""),
        "city": spec.get("city", ""),
        "provider": "qemu-free",
        "role": "field_node",
        "ssh": "ubuntu@127.0.0.1",
        "ssh_port": port,
        "ssh_key": key,
        "enabled": True,
        "batch": spec.get("batch"),
        "qemu_slot": slot,
        "qemu_slots": slots,
        "provisioned": spec["id"] in _load_provisioned(),
        "tunnel": (
            f"ssh -N -L {tunnel}:127.0.0.1:9477 -p {port} -i {key} ubuntu@127.0.0.1"
        ),
    }


def sync(*, write: bool = True) -> dict:
    regions_doc, nodes, port_base, tunnel_base, slots, batch_lists = _regions_meta()

    qemu_nodes = []
    for spec in nodes:
        slot = _slot_for(spec, batch_lists)
        port = port_base + slot
        tunnel = tunnel_base + slot
        qemu_nodes.append(
            _node_entry(spec, port=port, tunnel=tunnel, slot=slot, key=SSH_KEY, slots=slots)
        )

    if NODES_PATH.is_file():
        doc = _load(NODES_PATH)
    else:
        doc = {
            "schema": "grok-lab-world-nodes/v1",
            "motto": regions_doc.get("motto", ""),
            "operator": {"name": "field-operator", "home_node": "node-local"},
        }

    local = [n for n in doc.get("nodes", []) if n.get("id") == "node-local"]
    if not local:
        local = [
            {
                "id": "node-local",
                "region": "local",
                "provider": "sovereign-host",
                "role": "home_sanctuary",
                "ssh": "",
                "enabled": True,
                "note": "This machine — loopback only, no SSH deploy",
            }
        ]

    doc["updated"] = str(date.today())
    doc["target_geographic_nodes"] = len(qemu_nodes)
    doc["nodes"] = local + qemu_nodes
    doc["qemu"] = {
        "launched": doc.get("qemu", {}).get("launched", False),
        "ssh_key": SSH_KEY,
        "concurrent_slots": slots,
        "ssh_ports": [port_base + i for i in range(slots)],
    }
    doc["regions_manifest"] = str(REGIONS_PATH.relative_to(DEPLOY.parent.parent))

    if write:
        NODES_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "geographic_nodes": len(qemu_nodes),
        "total_nodes": len(doc["nodes"]),
        "batches": max((n.get("batch") or 0) for n in nodes) if nodes else 0,
        "path": str(NODES_PATH),
    }


def _indexed_nodes() -> list[tuple[dict, int, int, int]]:
    _doc, nodes, port_base, tunnel_base, slots, batch_lists = _regions_meta()
    out: list[tuple[dict, int, int, int]] = []
    for spec in nodes:
        slot = _slot_for(spec, batch_lists)
        out.append((spec, port_base + slot, tunnel_base + slot, slot))
    return out


def batch_nodes(batch: int) -> list[str]:
    lines: list[str] = []
    for spec, port, _tunnel, _slot in _indexed_nodes():
        if int(spec.get("batch") or 0) != batch:
            continue
        lines.append(f"{port}:{spec['id']}:{spec['region']}")
    return lines


def launch_specs(batch: int) -> list[str]:
    lines: list[str] = []
    for spec, port, _tunnel, _slot in _indexed_nodes():
        if int(spec.get("batch") or 0) != batch:
            continue
        mem = int(spec.get("mem_mb") or 1024)
        lines.append(f"{spec['id']}:{spec['region']}:{port}:{mem}")
    return lines


def batch_max() -> int:
    return max((int(spec.get("batch") or 0) for spec, _p, _t, _s in _indexed_nodes()), default=0)


def port_for_id(node_id: str) -> int:
    for spec, port, _tunnel, _slot in _indexed_nodes():
        if spec.get("id") == node_id:
            return port
    return 0


def _load_provisioned() -> set[str]:
    if not PROVISIONED_PATH.is_file():
        return set()
    try:
        doc = _load(PROVISIONED_PATH)
        return set(doc.get("provisioned") or [])
    except (json.JSONDecodeError, OSError):
        return set()


def _save_provisioned(ids: set[str], *, active_batch: int | None = None) -> None:
    doc: dict = {
        "schema": "grok-lab-qemu-provisioned/v1",
        "updated": str(date.today()),
        "provisioned": sorted(ids),
        "count": len(ids),
        "target": 30,
    }
    if active_batch is not None:
        doc["active_batch"] = active_batch
    PROVISIONED_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def mark_active_batch(batch: int) -> None:
    ACTIVE_BATCH_PATH.write_text(f"{batch}\n", encoding="utf-8")
    ids = _load_provisioned()
    _save_provisioned(ids, active_batch=batch)


def mark_provisioned_batch(batch: int) -> dict:
    ids = _load_provisioned()
    for line in batch_nodes(batch):
        node_id = line.split(":", 2)[1]
        ids.add(node_id)
    _save_provisioned(ids, active_batch=None)
    added = len(batch_nodes(batch))
    return {"ok": True, "batch": batch, "added": added, "provisioned": len(ids)}


def provisioned_count() -> int:
    return len(_load_provisioned())


def active_batch_nodes() -> list[str]:
    if not ACTIVE_BATCH_PATH.is_file():
        return []
    try:
        active = int(ACTIVE_BATCH_PATH.read_text(encoding="utf-8").strip())
    except ValueError:
        return []
    return batch_nodes(active)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "sync").strip().lower()
    if cmd == "sync":
        out = sync(write="--dry" not in sys.argv)
        print(json.dumps(out, indent=2))
        return 0
    if cmd == "batch-max":
        print(batch_max())
        return 0
    if cmd == "batch-nodes" and len(sys.argv) > 2:
        for line in batch_nodes(int(sys.argv[2])):
            print(line)
        return 0
    if cmd == "launch-specs" and len(sys.argv) > 2:
        for line in launch_specs(int(sys.argv[2])):
            print(line)
        return 0
    if cmd == "port-for-id" and len(sys.argv) > 2:
        print(port_for_id(sys.argv[2]))
        return 0
    if cmd == "mark-active" and len(sys.argv) > 2:
        mark_active_batch(int(sys.argv[2]))
        return 0
    if cmd == "mark-provisioned" and len(sys.argv) > 2:
        print(json.dumps(mark_provisioned_batch(int(sys.argv[2])), indent=2))
        return 0
    if cmd == "provisioned-count":
        print(provisioned_count())
        return 0
    print(
        "usage: world-nodes-sync.py [sync [--dry]|batch-max|batch-nodes N|"
        "launch-specs N|port-for-id ID|mark-active N|mark-provisioned N|provisioned-count]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())