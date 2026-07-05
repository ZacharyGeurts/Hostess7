#!/usr/bin/env python3
"""Sole IPv4 DHCP/DNS enforcement — rescue devices, burn stale equipment, preserve live leases."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-sovereign-ipv4-enforce-panel.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _env() -> dict[str, str]:
    return {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "NEXUS_FIELD_INTERNET_UNRESTRICT": "0",
        "NEXUS_FIELD_COLLISION_SOFT_INGRESS": "1",
        "NEXUS_FIELD_DHCP_SOFT_INGRESS": "1",
        "NEXUS_TRUTH_KEEPALIVE_FAST": "1",
    }


def _run(rel: str, args: list[str], *, timeout: float = 90.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": "missing", "script": rel}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_env(),
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            doc = json.loads(raw)
            if isinstance(doc, dict):
                doc.setdefault("ok", proc.returncode == 0)
                return doc
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                doc = json.loads(line)
                if isinstance(doc, dict):
                    doc.setdefault("ok", proc.returncode == 0)
                    return doc
        return {"ok": proc.returncode == 0, "stdout": raw[:400], "stderr": (proc.stderr or "")[:200]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "script": rel}
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc), "script": rel}


def enforce(*, crush: bool = False, kick_trash: bool = True) -> dict[str, Any]:
    """Rescue live devices, enforce sole DHCP/DNS, destroy stale equipment only."""
    steps: list[dict[str, Any]] = []

    rescue = _run("lib/field-rescue-ingress.py", ["rescue"], timeout=120)
    steps.append({"step": "rescue_ingress", **rescue})

    absorb_args = ["absorb"] if crush else ["absorb", "--no-crush"]
    absorb = _run("lib/field-planetary-dns-dhcp.py", absorb_args, timeout=120)
    steps.append({"step": "planetary_absorb", "crush": crush, **absorb})

    collision = _run("lib/field-dns-dhcp-collision-guard.py", ["enforce"], timeout=60)
    steps.append({"step": "collision_guard_enforce", **collision})

    takeover = _run("lib/dns-service-takeover.py", ["evaluate"], timeout=45)
    if not takeover:
        takeover = _run("lib/dns-service-takeover.py", ["json"], timeout=30)
    steps.append({"step": "dns_takeover", **takeover})

    qemu_burn = _run("lib/field-attack-kit.py", ["qemu-bot-rekill"], timeout=60)
    steps.append({"step": "qemu_bot_rekill", **qemu_burn})

    if kick_trash:
        for label, rel, args, tmo in (
            ("purge_rekill_trash", "lib/field-attack-kit.py", ["purge-rekill-trash"], 60),
            ("dns_table_clean", "lib/field-dns-table-clean.py", ["clean"], 45),
            ("fork_guard_burn_stale", "lib/field-zachub-fork-guard.py", ["burn-stale"], 90),
        ):
            row = _run(rel, args, timeout=tmo)
            steps.append({"step": label, **row})

    device_map = _run("lib/field-device-map.py", ["build"], timeout=60)
    steps.append({"step": "device_map_build", **device_map})

    dns_zones = _run("lib/ammonet-dns-zones.py", ["panel"], timeout=20)
    steps.append({"step": "ammonet_dns_zones", **dns_zones})

    rekill = _run("lib/field-attack-kit.py", ["permanent-rekill-enforce"], timeout=60)
    steps.append({"step": "permanent_rekill_enforce", **rekill})

    sole = (collision.get("sole_authority") or absorb.get("sole_authority") or {})
    connected = int((device_map.get("connected_count") or device_map.get("connected") or 0))
    if not connected:
        connected = int((rescue.get("cleared_fakes") or {}).get("registry_devices") or 0)

    out = {
        "ok": bool(rescue.get("ok")) and bool(collision.get("ok", True)),
        "schema": "field-sovereign-ipv4-enforce/v1",
        "updated": _utc(),
        "motto": "Sole IPv4 DHCP/DNS — rescue live leases, burn stale equipment, ZNetwork sole internet",
        "ingress_policy": "quarantine_not_kill",
        "crush_dhcp": crush,
        "connected_devices": connected,
        "sole_authority": sole,
        "takeover_phase": collision.get("takeover_phase") or takeover.get("phase"),
        "rescue": {
            "registry_devices": (rescue.get("cleared_fakes") or {}).get("registry_devices"),
            "dhcp_leases_real": (rescue.get("cleared_fakes") or {}).get("dhcp_leases_real"),
        },
        "planetary": rescue.get("planetary") or {},
        "qemu_destroyed": qemu_burn.get("destroyed_count") or qemu_burn.get("killed_count"),
        "steps": steps,
        "api": "/api/field-sovereign-ipv4-enforce",
    }
    _save(PANEL, out)
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "enforce").strip().lower()
    if cmd in ("enforce", "sole", "rescue", "json", "panel"):
        crush = "--crush" in sys.argv[2:]
        no_kick = "--no-kick-trash" in sys.argv[2:]
        print(json.dumps(enforce(crush=crush, kick_trash=not no_kick), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-sovereign-ipv4-enforce.py [enforce|--no-crush|--crush|--no-kick-trash]",
        "note": "Default: rescue + absorb --no-crush + collision enforce + burn stale QEMU + kick-trash",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())