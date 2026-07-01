#!/usr/bin/env pythong
"""DNS/DHCP threat guard — listen first, reject attacks, permanent eradication."""
from __future__ import annotations

import json
import os
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
THREAT_LOG = STATE / "dns-threat-eradicated.jsonl"
PANEL_CACHE = STATE / "dns-threat-guard-panel.json"
PERM_BLOCK = STATE / "dns-threat-permanent-blocks.json"

# Rate limits — DDoS immunity both directions
MAX_QPS_PER_CLIENT = int(os.environ.get("NEXUS_DNS_MAX_QPS", "30"))
MAX_PACKET_BYTES = int(os.environ.get("NEXUS_DNS_MAX_PACKET", "512"))
WINDOW_SEC = float(os.environ.get("NEXUS_DNS_RATE_WINDOW", "1.0"))

_rate: dict[str, list[float]] = defaultdict(list)
_dig_sem_count = 0
_dig_sem_max = int(os.environ.get("NEXUS_DNS_MAX_CONCURRENT_DIG", "4"))


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _permanent_blocks() -> dict[str, Any]:
    doc = _load_json(PERM_BLOCK, {"blocks": [], "updated": _now()})
    return doc


def listen_before_reject(
    *,
    client_key: str,
    packet_len: int,
    qtype: int | None = None,
) -> tuple[bool, str]:
    """Accept listener state first; reject only after classify."""
    now = time.time()
    if packet_len > MAX_PACKET_BYTES:
        return False, "oversized_packet"
    if qtype == 255:
        return False, "any_query_rejected"
    window = _rate[client_key]
    window[:] = [t for t in window if now - t < WINDOW_SEC]
    if len(window) >= MAX_QPS_PER_CLIENT:
        return False, "rate_limit_ddos"
    window.append(now)
    return True, "listen_ok"


def eradicate_threat(
    *,
    client_key: str,
    reason: str,
    vector: str = "DDOS_FLOOD",
    direction: str = "ingress",
) -> dict[str, Any]:
    """Permanent threat removal — block and log."""
    blocks = _permanent_blocks()
    entry = {
        "ts": _now(),
        "client": client_key,
        "reason": reason,
        "vector": vector,
        "direction": direction,
        "action": "permanent_block",
        "undone": False,
    }
    existing = {b.get("client") for b in blocks.get("blocks") or []}
    if client_key not in existing:
        blocks.setdefault("blocks", []).append(entry)
        blocks["updated"] = _now()
        _save_json(PERM_BLOCK, blocks)
    STATE.mkdir(parents=True, exist_ok=True)
    with THREAT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _invoke_autosanitize(vector, client_key, reason)
    return entry


def is_permanently_blocked(client_key: str) -> bool:
    blocks = _permanent_blocks().get("blocks") or []
    return any(b.get("client") == client_key and not b.get("undone") for b in blocks)


def _invoke_autosanitize(vector: str, target: str, detail: str) -> None:
    script = INSTALL / "lib" / "threat-autosanitize.sh"
    if not script.is_file():
        return
    try:
        subprocess.run(
            ["bash", "-c", f'source "{script}" && nexus_autosanitize_on_threat "{vector}" critical "{detail}"'],
            capture_output=True,
            timeout=8,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def acquire_dig_slot() -> bool:
    global _dig_sem_count
    if _dig_sem_count >= _dig_sem_max:
        return False
    _dig_sem_count += 1
    return True


def release_dig_slot() -> None:
    global _dig_sem_count
    _dig_sem_count = max(0, _dig_sem_count - 1)


def build_panel() -> dict[str, Any]:
    blocks = _permanent_blocks()
    eradicated: list[dict[str, Any]] = []
    if THREAT_LOG.is_file():
        try:
            for line in THREAT_LOG.read_text(encoding="utf-8").splitlines()[-200:]:
                if line.strip():
                    eradicated.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    doc = {
        "schema": "dns-threat-guard/v1",
        "updated": _now(),
        "motto": "Listen before reject · DDoS immunity · permanent eradication.",
        "policy": {
            "listen_before_reject": True,
            "dhcp_dns_only": True,
            "no_lateral_movement": True,
            "max_qps_per_client": MAX_QPS_PER_CLIENT,
            "max_packet_bytes": MAX_PACKET_BYTES,
        },
        "permanent_blocks": blocks.get("blocks") or [],
        "eradicated_recent": list(reversed(eradicated[-24:])),
        "stats": {
            "permanent_blocks": len(blocks.get("blocks") or []),
            "eradicated_total": len(eradicated),
            "active_rate_clients": len(_rate),
        },
    }
    _save_json(PANEL_CACHE, doc)
    return doc


def panel_json() -> dict[str, Any]:
    return build_panel()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: dns-threat-guard.py [json|build]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())