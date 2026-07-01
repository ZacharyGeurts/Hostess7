#!/usr/bin/env pythong
"""KILROY boot services — DNS/DHCP tables verified and connected on kernel boot."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "kilroy-boot-services.json"
MARKER = STATE / "kilroy-boot-services.json"


def _now() -> str:
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


def _pid_alive(rel_pid: str) -> bool:
    path = STATE / rel_pid
    if not path.is_file():
        return False
    try:
        pid = int(path.read_text(encoding="utf-8").strip().split()[0])
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _verify_dns_tables(doctrine: dict[str, Any]) -> dict[str, Any]:
    tables = doctrine.get("dns_tables") or {}
    verified: dict[str, Any] = {}
    for key, rel in tables.items():
        path = INSTALL / str(rel)
        doc = _load(path, {})
        verified[key] = {
            "path": str(rel),
            "present": path.is_file(),
            "schema": doc.get("schema"),
            "ok": path.is_file() and bool(doc),
        }
    return {
        "all_present": all(v.get("ok") for v in verified.values()) if verified else False,
        "tables": verified,
    }


def _verify_dhcp_table(doctrine: dict[str, Any]) -> dict[str, Any]:
    rel = str(doctrine.get("dhcp_table") or "data/field-dhcp-seed.json")
    path = INSTALL / rel
    doc = _load(path, {})
    return {
        "path": rel,
        "present": path.is_file(),
        "schema": doc.get("schema"),
        "pool": doc.get("pool") or {},
        "dns_option": doc.get("dns_option") or {},
        "ok": path.is_file() and bool(doc),
    }


def _service_status(doctrine: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for svc in doctrine.get("services") or []:
        sid = str(svc.get("id") or "")
        if sid == "field_dns":
            out[sid] = {"running": _pid_alive("field-dns.pid"), "listener": "127.0.0.1:53"}
        elif sid == "field_dhcp":
            out[sid] = {"running": _pid_alive("field-dhcp.pid"), "listener": "0.0.0.0:67"}
        elif sid == "nexus_c2":
            port = int(svc.get("port") or 9477)
            up = False
            try:
                import urllib.request

                with urllib.request.urlopen(f"http://127.0.0.1:{port}/field", timeout=1.5) as resp:
                    up = resp.status == 200
            except Exception:
                up = False
            out[sid] = {"running": up, "listener": f"127.0.0.1:{port}"}
        elif sid == "queen_world":
            port = int(svc.get("port") or 9481)
            up = False
            try:
                import urllib.request

                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status?fast=1", timeout=1.5) as resp:
                    up = resp.status == 200
            except Exception:
                up = False
            out[sid] = {"running": up, "role": "web_browser", "listener": f"127.0.0.1:{port}"}
        else:
            out[sid] = {"configured": True}
    return out


def _connect_dns_dhcp() -> dict[str, Any]:
    mod = _import_mod("field_local_dns_connect", "lib/field-local-dns-connect.py")
    if not mod or not hasattr(mod, "connect"):
        return {"ok": False, "skipped": True, "reason": "module_missing"}
    try:
        return mod.connect(persist=True)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def board(*, connect: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    dns_check = _verify_dns_tables(doctrine)
    dhcp_check = _verify_dhcp_table(doctrine)
    services = _service_status(doctrine)
    connect_doc: dict[str, Any] = {"ok": False, "skipped": True}
    if connect and (services.get("field_dns", {}).get("running") or services.get("field_dhcp", {}).get("running")):
        connect_doc = _connect_dns_dhcp()

    branding: dict[str, Any] = {"ok": False, "skipped": True}
    brand_mod = _import_mod("queen_profile_branding", "lib/queen-profile-branding.py")
    if brand_mod and hasattr(brand_mod, "seed_all"):
        try:
            ammoos = f"http://127.0.0.1:{int(os.environ.get('NEXUS_THREAT_PANEL_PORT', '9477') or '9477')}/field"
            branding = brand_mod.seed_all(homepage=ammoos)
        except Exception as exc:
            branding = {"ok": False, "error": str(exc)}

    surfaces = doctrine.get("surfaces") or {}
    doc: dict[str, Any] = {
        "schema": "kilroy-boot-services-runtime/v1",
        "updated": _now(),
        "owner": "kilroy_core",
        "motto": doctrine.get("motto", ""),
        "loopback_authority": doctrine.get("loopback_authority") or "127.0.0.1",
        "surfaces": surfaces,
        "queen_role": (surfaces.get("queen") or {}).get("role") or "web_browser",
        "ammoos_role": (surfaces.get("ammoos") or {}).get("role") or "normal_desktop",
        "boot_order": doctrine.get("boot_order") or [],
        "dns_tables": dns_check,
        "dhcp_table": dhcp_check,
        "services": services,
        "dns_dhcp_connect": connect_doc,
        "queen_branding": branding,
        "kernel_boot_preconfigured": True,
        "configured_in_advance": bool(dns_check.get("all_present") and dhcp_check.get("ok")),
    }
    _save(MARKER, doc)
    return doc


def posture() -> dict[str, Any]:
    cached = _load(MARKER, {})
    if cached:
        live = board(connect=False)
        live["cached"] = cached
        return live
    return board(connect=False)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "board":
        print(json.dumps(board(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        doctrine = _load(DOCTRINE, {})
        out = {
            "dns_tables": _verify_dns_tables(doctrine),
            "dhcp_table": _verify_dhcp_table(doctrine),
            "services": _service_status(doctrine),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print("usage: kilroy-boot-services.py [json|board|verify]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())