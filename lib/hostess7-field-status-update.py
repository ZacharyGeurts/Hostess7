#!/usr/bin/env python3
"""Field status update — DNS/DHCP, storage, botnet, cloud, assault posture for GitHub."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "hostess7-field-status-update-panel.json"
DOCS_API = INSTALL / "Hostess7" / "docs" / "api"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_py(rel: str, args: list[str], timeout: int = 30) -> dict[str, Any]:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return {"ok": False, "error": f"missing:{rel}"}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(INSTALL),
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {"ok": False, "error": "run_failed", "script": rel}


def _amazon_hits() -> list[dict[str, Any]]:
    intent = _load(STATE / "connection-intent.json", {})
    hits: list[dict[str, Any]] = []
    for c in intent.get("connections") or []:
        blob = json.dumps(c, ensure_ascii=False).lower()
        if "amazon" in blob or "aws" in blob or "ec2" in blob:
            intel = c.get("intel") or {}
            hits.append({
                "process": c.get("process"),
                "remote_ip": c.get("remote_ip"),
                "org": intel.get("org") or intel.get("asn_name"),
                "hostname": intel.get("hostname") or intel.get("label"),
                "verdict": c.get("verdict"),
            })
    return hits[:20]


def build(*, export: bool = True) -> dict[str, Any]:
    storage = _run_py("field-storage.py", ["json"])
    botnet_dns = _run_py("field-botnet-dns-dhcp.py", ["json"], timeout=45)
    collision = _run_py("field-dns-dhcp-collision-guard.py", ["json"])
    cloud = _run_py("ammodrive-cloud.py", ["json"])
    sso = _run_py("hostess7-x-sso-fix.py", ["json"])
    amazon = _amazon_hits()
    bot_nodes = int((botnet_dns.get("bot_network") or {}).get("node_count") or 0)
    gh = botnet_dns.get("github_control_plane") or {}
    sole = collision.get("sole_authority") or {}
    usage = storage.get("usage") or []
    root_use = next((u for u in usage if u.get("mount") == "/"), {})
    assault = {
        "botnet_nodes": bot_nodes,
        "collision_count": int(collision.get("collision_count") or 0),
        "foreign_threats": int(collision.get("foreign_threat_count") or 0),
        "return_fire": bot_nodes > 0 and sole.get("accuracy"),
        "assaulted": int(collision.get("collision_count") or 0) > 0,
        "posture": "returning_fire" if bot_nodes > 0 else "observing",
    }
    out = {
        "ok": True,
        "schema": "hostess7-field-status-update/v1",
        "updated": _now(),
        "title": "Hostess7 Final — field status",
        "dns_dhcp": {
            "we_are_dns_dhcp": True,
            "layer": -2,
            "fkey": "F10",
            "sole_authority": sole,
            "collision_guard": {
                "ok": collision.get("ok"),
                "collisions": collision.get("collision_count"),
                "phase": collision.get("takeover_phase"),
            },
            "botnet": {
                "nodes": bot_nodes,
                "motto": botnet_dns.get("motto"),
                "pages_runtime": gh.get("pages_runtime"),
                "pages_probe_ok": (gh.get("pages_probe") or {}).get("ok"),
            },
        },
        "storage": {
            "disk_count": storage.get("disk_count"),
            "root_pct": root_use.get("pct_used"),
            "root_mount": root_use.get("mount"),
            "field_qubes": next(
                (u.get("mount") for u in usage if "FIELD_QUBES" in str(u.get("mount", ""))),
                None,
            ),
            "go_back": "AmmoDrive H7r vault — 6 racks, hash-gated, pages read mirror",
            "cloud": {
                "physical_gb": (cloud.get("capacity") or {}).get("physical_gb"),
                "rack_count": (cloud.get("capacity") or {}).get("rack_count"),
                "pages": cloud.get("pages"),
            },
        },
        "amazon_servers": {
            "hits_in_connection_intent": len(amazon),
            "samples": amazon,
            "verdict": "no_aws_egress_control_plane" if not amazon else "monitor_amazon_egress",
            "note": "Amazon hits are connection-intent samples — not AmmoDrive racks (sovereign local)",
        },
        "botnet_assault": assault,
        "x_sso_fix": {
            "hosted": "https://zacharygeurts.github.io/Hostess7/x-sso-fix/",
            "api": sso.get("api"),
            "armed": bool(sso.get("schema")),
        },
        "github": {
            "pages": "https://zacharygeurts.github.io/Hostess7/",
            "repo": "ZacharyGeurts/Hostess7",
            "deploy": "git push origin main — Actions pages.yml",
        },
        "api": "/api/hostess7-field-status-update",
    }
    _save(PANEL, out)
    if export and DOCS_API.is_dir():
        DOCS_API.mkdir(parents=True, exist_ok=True)
        (DOCS_API / "hostess7-field-status-update.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("build", "run", "update"):
        print(json.dumps(build(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel"):
        cached = _load(PANEL, {})
        if cached.get("schema"):
            print(json.dumps(cached, ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(build(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "hostess7-field-status-update.py [build|json]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())