#!/usr/bin/env pythong
"""NEXUS Friendly Guard v3.3.2 — IMMUTABLE. Never KILL friendlies.

Tamper-sealed via MANIFEST.sha256. Fail-closed: if this module cannot run,
every KILL is refused. Cannot be disabled by environment variables.
HeavyBoi v7 validates pasted kill-order blocks before ingest.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

GUARD_VERSION = "3.3.2"

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))

# Immutable friendly policy — do not make these configurable.
FRIENDLY_VERDICTS: frozenset[str] = frozenset({"USER_OK", "EPHEMERAL"})
FRIENDLY_TRUST_RANK_MAX: int = 1
SACRED_IPV4: frozenset[str] = frozenset({
    "0.0.0.0",
    "1.0.0.1",
    "1.1.1.1",
    "8.8.4.4",
    "8.8.8.8",
    "9.9.9.9",
    "127.0.0.0",
    "127.0.0.1",
    "149.112.112.112",
})
TRUSTED_TSV = STATE / "firewall-trusted.tsv"
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
HOSTESS7_TEAM_FIELD = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage"))
TRUST_MEMORY_FILE = os.environ.get("NEXUS_TRUST_MEMORY_FILE", "nexus-trusted.jsonl")

PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.|::1|fe80:|fd)"
)


def _local_wan_gateway() -> tuple[str, str]:
    wan, gw = "", ""
    try:
        proc = subprocess.run(
            ["ip", "-4", "route", "get", "1.1.1.1"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        parts = proc.stdout.split()
        if "src" in parts:
            wan = parts[parts.index("src") + 1]
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    try:
        proc = subprocess.run(
            ["ip", "-4", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        parts = proc.stdout.split()
        if len(parts) >= 3 and parts[0] == "default":
            gw = parts[2]
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return wan, gw


def _is_private_ip(ip: str) -> bool:
    if not ip:
        return True
    if PRIVATE_RE.match(ip):
        return True
    try:
        addr = ipaddress.ip_address(ip.split("%")[0])
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


def _is_sacred_ip(ip: str) -> bool:
    if not ip:
        return True
    if ip.startswith("127."):
        return True
    if ip in SACRED_IPV4:
        return True
    wan, gw = _local_wan_gateway()
    if wan and ip == wan:
        return True
    if gw and ip == gw:
        return True
    return False


def _load_trusted_tsv() -> set[str]:
    ips: set[str] = set()
    if not TRUSTED_TSV.is_file():
        return ips
    try:
        for line in TRUSTED_TSV.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 3 and parts[2]:
                ips.add(parts[2].strip())
    except OSError:
        pass
    return ips


def _trust_memory_paths() -> list[Path]:
    return [
        HOSTESS7_ROOT / "cache" / "fieldstorage" / "brain" / "security" / TRUST_MEMORY_FILE,
        HOSTESS7_TEAM_FIELD / "brain" / "security" / TRUST_MEMORY_FILE,
    ]


def _load_trusted_memory() -> set[str]:
    ips: set[str] = set()
    for path in _trust_memory_paths():
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("kind") == "nexus_trust" and not obj.get("revoked"):
                    ip = str(obj.get("ip") or "").strip()
                    if ip:
                        ips.add(ip)
        except OSError:
            continue
    return ips


def _load_trusted_ips() -> set[str]:
    trusted = _load_trusted_tsv()
    trusted.update(_load_trusted_memory())
    return trusted


def _monitor_is_friendly(monitor: dict[str, Any] | None) -> str | None:
    if not monitor:
        return None
    verdict = str(monitor.get("verdict") or "")
    trust_rank = int(monitor.get("trust_rank") or 99)
    if verdict in FRIENDLY_VERDICTS:
        return f"friendly_verdict:{verdict}"
    if trust_rank <= FRIENDLY_TRUST_RANK_MAX:
        return f"friendly_trust_rank:{trust_rank}"
    axis = monitor.get("axis_scores") or {}
    if int(axis.get("operator_auth") or 0) >= 8:
        return "operator_trust_forever"
    return None


def refuse_kill(ip: str, monitor: dict[str, Any] | None = None) -> tuple[bool, str]:
    """Return (refuse, reason). refuse=True means KILL must NOT proceed."""
    ip = str(ip or "").strip()
    if not ip:
        return True, "empty_ip"
    if _is_private_ip(ip):
        return True, "private_or_local"
    if _is_sacred_ip(ip):
        return True, "sacred_infrastructure"
    if ip in _load_trusted_ips():
        return True, "operator_trusted"
    friendly = _monitor_is_friendly(monitor)
    if friendly:
        return True, friendly
    return False, "hostile_eligible"


def check_payload(ip: str, monitor: dict[str, Any] | None = None) -> dict[str, Any]:
    refuse, reason = refuse_kill(ip, monitor=monitor)
    return {
        "refuse": refuse,
        "reason": reason,
        "ip": ip,
        "immutable": True,
        "fail_closed": True,
        "version": GUARD_VERSION,
    }


def validate_kill_block(orders: list[dict[str, Any]]) -> dict[str, Any]:
    """HeavyBoi v7 — validate a pasted kill_orders block before ingest."""
    validated: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    for order in orders:
        ip = str(order.get("ip") or "").strip()
        if not ip:
            refused.append({"ip": "", "reason": "empty_ip"})
            continue
        refuse, reason = refuse_kill(ip)
        if refuse:
            refused.append({"ip": ip, "reason": reason})
        else:
            validated.append(order)
    return {
        "version": GUARD_VERSION,
        "validated": validated,
        "refused": refused,
        "validated_count": len(validated),
        "refused_count": len(refused),
        "immutable": True,
        "fail_closed": True,
    }


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "validate-block":
        raw = sys.argv[2] if len(sys.argv) > 2 else "{}"
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            return 2
        orders = list(body.get("kill_orders") or body.get("orders") or [])
        json.dump(validate_kill_block(orders), sys.stdout)
        sys.stdout.write("\n")
        return 0
    if len(sys.argv) < 3 or sys.argv[1] != "check":
        print("usage: friendly-guard.py [check <ip> [monitor_json]|validate-block JSON]", file=sys.stderr)
        return 2
    ip = sys.argv[2]
    monitor = None
    if len(sys.argv) > 3 and sys.argv[3]:
        try:
            monitor = json.loads(sys.argv[3])
        except json.JSONDecodeError:
            return 2
    payload = check_payload(ip, monitor=monitor)
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")
    return 0 if payload["refuse"] else 1


if __name__ == "__main__":
    raise SystemExit(main())