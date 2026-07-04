#!/usr/bin/env pythong
"""Dynamic sovereign route return + hostile/DNS/kill-rekill table trash purge at runtime."""
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
DOCTRINE = INSTALL / "data" / "field-dynamic-routes-doctrine.json"
PANEL = STATE / "field-dynamic-routes-panel.json"
ROUTES_PUBLIC = INSTALL / "Hostess7" / "docs" / "api" / "field-endpoint-registry.json"
SCHEMA = "field-dynamic-routes/v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _env() -> dict[str, str]:
    return {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}


def _py(script: str, *args: str, timeout: int = 45) -> dict[str, Any]:
    path = INSTALL / "lib" / script
    if not path.is_file():
        return {"ok": False, "error": "missing", "script": script}
    py = os.environ.get("PYTHON", "python3")
    try:
        proc = subprocess.run(
            [py, str(path), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_env(),
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            out = json.loads(raw)
            out.setdefault("ok", proc.returncode == 0)
            return out
        return {"ok": proc.returncode == 0, "raw": raw[:400], "rc": proc.returncode, "script": script}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc), "script": script}


def _run_script(rel: str, *args: str, timeout: int = 90) -> dict[str, Any]:
    path = INSTALL / rel
    if not path.is_file():
        return {"ok": False, "error": "missing", "path": rel}
    try:
        proc = subprocess.run(
            ["bash", str(path), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_env(),
            check=False,
        )
        return {"ok": proc.returncode == 0, "rc": proc.returncode, "stdout": (proc.stdout or "")[:500]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "path": rel}


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _route_count() -> int | None:
    for fp in (ROUTES_PUBLIC, STATE / "field-endpoint-registry-routes.json"):
        if not fp.is_file():
            continue
        doc = _load(fp, {})
        if doc.get("route_count") is not None:
            return int(doc["route_count"])
        routes = doc.get("routes") or {}
        if routes:
            return len(routes)
    return None


def _ensure_api_pins(doc: dict[str, Any]) -> dict[str, Any]:
    """Append sovereign API wires via endpoint registry seed --append."""
    pins = list(doc.get("sovereign_api_pins") or [])
    if not pins:
        return {"ok": True, "skipped": True, "reason": "no_pins"}
    seed_append = _py("field-endpoint-registry.py", "seed", "--append", timeout=60)
    verify = _py("field-endpoint-registry.py", "verify", timeout=30)
    return {
        "ok": bool(seed_append.get("ok")),
        "seed_append": seed_append,
        "verify": verify,
        "pin_count": len(pins),
    }


def return_routes(*, fast: bool = False) -> dict[str, Any]:
    """Restore sovereign routes — registry, ironclad, internet control plane."""
    doc = doctrine()
    cfg = doc.get("return_routes") or {}
    steps: list[dict[str, Any]] = []

    if cfg.get("dns_clean", True) and not fast:
        clean = _py("field-dns-table-clean.py", "clean", timeout=45)
        steps.append({"step": "dns_clean", **clean})

    if cfg.get("endpoint_registry_seed_append", True):
        pins = _ensure_api_pins(doc)
        steps.append({"step": "endpoint_registry", **pins})
    elif cfg.get("endpoint_registry_verify", True):
        verify = _py("field-endpoint-registry.py", "verify", timeout=30)
        steps.append({"step": "endpoint_verify", **verify})

    if cfg.get("propagate_pages_registry", True) and doc.get("policy", {}).get("propagate_registry", True):
        prop = _run_script("scripts/propagate-pages-registry.sh", "field-dynamic-routes", timeout=120)
        if not prop.get("ok"):
            prop["fallback"] = _py("field-endpoint-registry.py", "propagate", timeout=90)
        steps.append({"step": "propagate_registry", **prop})

    if cfg.get("ironclad_routes", True):
        routes = _py("ironclad-secure-api.py", "routes", timeout=45)
        steps.append({"step": "ironclad_routes", **routes})
    if cfg.get("ironclad_publish", True) and not fast:
        publish = _py("ironclad-secure-api.py", "publish", timeout=45)
        steps.append({"step": "ironclad_publish", **publish})

    if cfg.get("legacy_connect_primary", False) and not fast:
        legacy = _py("field-legacy-connect.py", "ensure-primary", timeout=120)
        steps.append({"step": "legacy_connect_primary", **legacy})

    if cfg.get("internet_panels", True) and not fast:
        for spec in doc.get("internet_panels") or []:
            parts = str(spec).split(":", 1)
            if len(parts) != 2:
                continue
            script, cmd = parts[0].replace("lib/", ""), parts[1]
            panel = _py(script, cmd, timeout=30)
            steps.append({"step": f"panel:{script}:{cmd}", **panel})

    ok = any(s.get("ok") for s in steps) if steps else True
    out = {
        "ok": ok,
        "schema": SCHEMA,
        "phase": "return_routes",
        "updated": _utc(),
        "route_count": _route_count(),
        "steps": steps,
        "fast": fast,
    }
    return out


def kick_table_trash(*, boot_rekill: bool | None = None) -> dict[str, Any]:
    """Purge trash from hostile, kill-rekill, DNS, fork-guard, and host-map tables."""
    doc = doctrine()
    cfg = doc.get("kick_trash") or {}
    pol = doc.get("policy") or {}
    steps: list[dict[str, Any]] = []

    if cfg.get("purge_rekill_trash", True):
        purge = _py("field-attack-kit.py", "purge-rekill-trash", timeout=60)
        steps.append({"step": "purge_rekill_trash", **purge})

    if cfg.get("dns_table_clean", True):
        clean = _py("field-dns-table-clean.py", "clean", timeout=45)
        steps.append({"step": "dns_table_clean", **clean})

    if cfg.get("fork_guard_burn_stale", True):
        burn = _py("field-zachub-fork-guard.py", "burn-stale", timeout=90)
        steps.append({"step": "fork_guard_burn_stale", **burn})

    if doc.get("policy", {}).get("convert_dns_dhcp_redundant", True):
        conv = _py("field-zachub-qemu-racks.py", "convert", timeout=90)
        steps.append({"step": "dns_dhcp_redundant_convert", **conv})

    rekill_result: dict[str, Any] | None = None
    do_rekill = boot_rekill if boot_rekill is not None else bool(pol.get("boot_rekill_after_purge", True))
    if do_rekill:
        perm = _py("field-attack-kit.py", "permanent-rekill-enforce", timeout=90)
        steps.append({"step": "permanent_rekill_enforce", **perm})
        rekill_result = _py("field-attack-kit.py", "boot-rekill", timeout=90)
        steps.append({"step": "boot_rekill", **rekill_result})

    purge_step = next((s for s in steps if s.get("step") == "purge_rekill_trash"), {})
    critical_ok = bool(purge_step.get("ok", True))
    optional_ok = all(
        s.get("ok", True)
        for s in steps
        if s.get("step") not in ("purge_rekill_trash",)
    )
    ok = critical_ok
    out = {
        "ok": ok,
        "schema": SCHEMA,
        "phase": "kick_table_trash",
        "updated": _utc(),
        "steps": steps,
        "removed_count": purge_step.get("removed_count"),
        "kept_count": purge_step.get("kept_count"),
        "host_trash_cleared": purge_step.get("host_trash_cleared"),
        "validated_hostile_count": purge_step.get("validated_hostile_count"),
        "rekilled_count": (rekill_result or {}).get("rekilled_count"),
        "partial": critical_ok and not optional_ok,
    }
    return out


def run(*, fast: bool = False) -> dict[str, Any]:
    """Full dynamic cycle — return routes, kick trash, war hardening stamp."""
    routes = return_routes(fast=fast)
    trash = kick_table_trash()
    stamp = _py("field-war-hardening.py", "stamp", timeout=60)
    ok = bool(routes.get("ok")) and bool(trash.get("ok")) and bool(stamp.get("ok", True))
    out = {
        "ok": ok,
        "schema": SCHEMA,
        "phase": "run",
        "updated": _utc(),
        "motto": doc_motto(),
        "route_count": routes.get("route_count"),
        "return_routes": routes,
        "kick_table_trash": trash,
        "war_hardening": stamp,
        "summary": {
            "endpoint_routes": routes.get("route_count"),
            "kill_rekill_kept": trash.get("kept_count"),
            "hostile_validated": trash.get("validated_hostile_count"),
            "hostile_removed": trash.get("removed_count"),
            "host_trash_cleared": trash.get("host_trash_cleared"),
        },
    }
    _save(PANEL, out)
    return out


def doc_motto() -> str:
    return str(doctrine().get("motto") or "Return routes dynamically — kick table trash off sovereign tables.")


def panel() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema") == SCHEMA:
        cached["_panel_cache"] = True
        return cached
    return {
        "ok": True,
        "schema": SCHEMA,
        "updated": _utc(),
        "motto": doc_motto(),
        "route_count": _route_count(),
        "cached": False,
        "hint": "POST /api/field-dynamic-routes/run or ?refresh=1 for live cycle",
    }


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    cmd = (args[0] if args else "json").strip().lower()
    fast = "--fast" in args

    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("return-routes", "return_routes", "routes"):
        print(json.dumps(return_routes(fast=fast), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("kick-trash", "kick_trash", "kick", "purge"):
        print(json.dumps(kick_table_trash(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "run":
        out = run(fast=fast)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    print(json.dumps({"ok": False, "error": "unknown_cmd", "cmds": ["json", "return-routes", "kick-trash", "run"]}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())