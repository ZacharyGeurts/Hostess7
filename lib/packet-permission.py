#!/usr/bin/env pythong
"""NEXUS Packet Permission v4.0 — sync flow permits/blocks and DPI segment enforcement."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
RING = STATE / "packet-field.ring.jsonl"
INTENT = STATE / "connection-intent.json"

TRUST_RANK = {
    "USER_OK": 0,
    "EPHEMERAL": 1,
    "MONITOR": 2,
    "SUSPICIOUS": 3,
    "HARM_CANDIDATE": 4,
}


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def flow_actions_from_intent() -> list[dict[str, Any]]:
    doc = _load_json(INTENT, {})
    actions: list[dict[str, Any]] = []
    seen_permit: set[str] = set()
    seen_block_seg: set[str] = set()
    seen_block_ip: set[str] = set()
    for row in doc.get("connections") or []:
        policy = row.get("flow_policy") or {}
        rip = str(row.get("remote_ip") or "").strip()
        rport = int(row.get("remote_port") or 0)
        proc = str(row.get("process") or "")
        verdict = row.get("verdict") or "MONITOR"
        rank = int(row.get("trust_rank") or TRUST_RANK.get(verdict, 5))
        scope = policy.get("block_scope") or "none"
        if not rip or rport <= 0:
            continue
        flow_key = f"{rip}:{rport}"
        if policy.get("permit") or rank <= 2:
            if flow_key not in seen_permit:
                seen_permit.add(flow_key)
                actions.append({
                    "action": "PERMIT",
                    "direction": "out",
                    "ip": rip,
                    "port": rport,
                    "reason": f"gatekeeper-{verdict.lower()}",
                    "scope": "flow",
                    "process": proc,
                })
            continue
        if scope == "ip" or rank >= 4:
            if rip not in seen_block_ip:
                seen_block_ip.add(rip)
                actions.append({
                    "action": "BLOCK_IP",
                    "direction": "both",
                    "ip": rip,
                    "port": 0,
                    "reason": f"gatekeeper-{verdict.lower()}",
                    "scope": "ip",
                    "process": proc,
                })
        elif scope == "segment" or rank == 3:
            seg_key = f"{rip}:{rport}"
            if seg_key not in seen_block_seg:
                seen_block_seg.add(seg_key)
                direction = policy.get("block_direction") or row.get("traffic_direction") or "out"
                if direction == "at_us":
                    direction = "in"
                elif direction not in ("in", "out"):
                    direction = "out"
                actions.append({
                    "action": "BLOCK_SEGMENT",
                    "direction": direction,
                    "ip": rip,
                    "port": rport,
                    "reason": f"gatekeeper-{verdict.lower()}",
                    "scope": "segment",
                    "process": proc,
                })
    return actions


def dpi_segment_actions(limit: int = 48) -> list[dict[str, Any]]:
    if not RING.is_file():
        return []
    lines = RING.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    actions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            pkt = json.loads(line)
        except json.JSONDecodeError:
            continue
        dpi = pkt.get("dpi") or {}
        if not dpi.get("alert"):
            continue
        seg = dpi.get("segment_block")
        if not seg:
            continue
        ip = str(seg.get("ip") or "").strip()
        port = int(seg.get("port") or 0)
        if not ip or port <= 0:
            continue
        key = f"{seg.get('direction', 'out')}:{ip}:{port}:{seg.get('reason', '')}"
        if key in seen:
            continue
        seen.add(key)
        actions.append({
            "action": "BLOCK_SEGMENT",
            "direction": seg.get("direction") or "out",
            "ip": ip,
            "port": port,
            "reason": seg.get("reason") or "dpi-segment",
            "scope": "segment",
            "process": pkt.get("process") or dpi.get("intent", {}).get("who", ""),
        })
    return actions


def emit_actions(actions: list[dict[str, Any]]) -> None:
    for act in actions:
        print(
            "\t".join([
                act.get("action", ""),
                act.get("direction", ""),
                act.get("ip", ""),
                str(act.get("port") or 0),
                act.get("reason", ""),
                act.get("scope", ""),
            ])
        )


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: packet-permission.py [flows|segments|all]", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "flows":
        emit_actions(flow_actions_from_intent())
    elif cmd == "segments":
        emit_actions(dpi_segment_actions())
    elif cmd == "all":
        emit_actions(flow_actions_from_intent() + dpi_segment_actions())
    else:
        print("usage: packet-permission.py [flows|segments|all]", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())