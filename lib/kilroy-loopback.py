#!/usr/bin/env pythong
"""KILROY loopback sovereignty — 127.0.0.1 on any computer, transparent boons."""
from __future__ import annotations

import importlib.util
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "kilroy-loopback-doctrine.json"
MARKER = STATE / "kilroy-loopback.json"
LOOPBACK = "127.0.0.1"
LOOPBACK_V6 = "::1"


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _port_open(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_up(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def _dns_status() -> dict[str, Any]:
    doc = _load(STATE / "field-dns.json", {})
    if doc:
        return {
            "running": bool(doc.get("running")),
            "listener": LOOPBACK,
            "port": 53,
            "truthful": bool(doc.get("truthful", True)),
        }
    return {"running": _port_open(LOOPBACK, 53), "listener": LOOPBACK, "port": 53}


def _storage_boon() -> dict[str, Any]:
    mirror = INSTALL / ".nexus-field-drive"
    active = False
    files = 0
    bytes_total = 0
    drive_mod = _import_mod("field_drive_system", "lib/field-drive-system.py")
    if drive_mod:
        try:
            if hasattr(drive_mod, "field_drive_active"):
                active = bool(drive_mod.field_drive_active())
            if hasattr(drive_mod, "primary_field_root"):
                root = Path(drive_mod.primary_field_root())
                if root.is_dir():
                    mirror = root
        except Exception:
            pass
    if mirror.is_dir():
        for p in mirror.rglob("*"):
            if p.is_file():
                files += 1
                try:
                    bytes_total += p.stat().st_size
                except OSError:
                    pass
    return {
        "field_mirror": str(mirror) if mirror.is_dir() else "",
        "mirror_active": active or mirror.is_dir(),
        "mirror_files": files,
        "mirror_bytes": bytes_total,
        "mirror_mb": round(bytes_total / (1024 * 1024), 2) if bytes_total else 0,
        "boon": "field_tech_storage_without_reformat",
    }


def posture(*, board: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    panel_port = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477") or "9477")
    queen_port = int(os.environ.get("QUEEN_WORLD_PORT", "9481") or "9481")
    services = {
        "nexus_c2": {
            "url": f"http://{LOOPBACK}:{panel_port}/field",
            "up": _http_up(f"http://{LOOPBACK}:{panel_port}/field"),
            "port": panel_port,
        },
        "queen": {
            "url": f"http://{LOOPBACK}:{queen_port}/api/status",
            "up": _http_up(f"http://{LOOPBACK}:{queen_port}/api/status?fast=1"),
            "port": queen_port,
        },
        "field_dns": _dns_status(),
    }
    storage = _storage_boon()
    any_up = any(s.get("up") for s in services.values() if "up" in s) or services["field_dns"].get("running")
    doc: dict[str, Any] = {
        "schema": "kilroy-loopback/v1",
        "updated": _now(),
        "owner": "kilroy_core",
        "loopback_authority": LOOPBACK,
        "loopback_ipv6": LOOPBACK_V6,
        "motto": doctrine.get(
            "motto",
            "KILROY is 127.0.0.1 — security, Field Tech speed, storage — guest OS untouched",
        ),
        "transparent": True,
        "guest_unmodified": True,
        "any_computer": True,
        "active": bool(any_up),
        "services": services,
        "boons": {
            "security": {
                "active": bool(services["nexus_c2"]["up"] or services["field_dns"].get("running")),
                "detail": "loopback C2 + truth DNS + field protections",
            },
            "field_tech_speed": {
                "active": bool(services["nexus_c2"]["up"] or services["queen"]["up"]),
                "detail": "loopback-first panel and Queen — no cloud hop",
            },
            "storage_space": storage,
        },
        "doctrine": str(DOCTRINE.relative_to(INSTALL)) if DOCTRINE.is_file() else "data/kilroy-loopback-doctrine.json",
    }
    if board:
        _save(MARKER, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(posture(board=False), ensure_ascii=False, indent=2))
        return 0
    if cmd == "board":
        print(json.dumps(posture(board=True), ensure_ascii=False, indent=2))
        return 0
    print("usage: kilroy-loopback.py [json|board]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())