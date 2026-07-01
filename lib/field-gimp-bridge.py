#!/usr/bin/env pythong
"""AmmoOS Image bridge — upstream inventory, field rewrite posture, RTX gate, NEXUS hook."""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = SG / "GIMP-Field" / "data" / "field-gimp-doctrine.json"
FORMATS = SG / "GIMP-Field" / "data" / "field-formats.json"
IO_BACKEND = SG / "GIMP-Field" / "lib" / "field-image-io.py"
GIMP_ROOT = SG / "GIMP"
TREE = SG / "GIMP-Field" / "tree"
MANIFEST = SG / "GIMP-Field" / "data" / "rewrite-manifest.json"
CONSOLIDATION = SG / "GIMP-Field" / "data" / "consolidation-manifest.json"
CONSOLIDATE = SG / "GIMP-Field" / "forge" / "field-gimp-consolidate.py"
PANEL = STATE / "field-gimp-bridge.json"
RTX_GATE = SG / "GIMP-Field" / "forge" / "rtx-content-gate.py"
REWRITE = SG / "GIMP-Field" / "forge" / "field-gimp-rewrite.py"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _run_json(script: Path, *args: str, timeout: int = 60) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": "script_missing", "path": str(script)}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(INSTALL),
            env={**os.environ, "SG_ROOT": str(SG), "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        raw = (proc.stdout or "").strip()
        if not raw:
            return {"ok": False, "error": "empty_output", "stderr": proc.stderr[-400:]}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            depth = 0
            buf: list[str] = []
            for ch in raw:
                if ch == "{":
                    if depth == 0:
                        buf = ["{"]
                    else:
                        buf.append(ch)
                    depth += 1
                elif ch == "}":
                    if depth > 0:
                        buf.append(ch)
                        depth -= 1
                        if depth == 0:
                            return json.loads("".join(buf))
                elif depth > 0:
                    buf.append(ch)
            return {"ok": False, "error": "json_parse_failed", "raw": raw[-400:]}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _inventory() -> dict[str, Any]:
    root = TREE if TREE.is_dir() and (TREE / "meson.build").is_file() else GIMP_ROOT
    if not root.is_dir():
        return {"ok": False, "error": "ammoos_tree_missing", "path": str(root)}
    counts: dict[str, int] = {}
    for sub in ("app", "plug-ins", "libgimp", "libgimpbase", "libgimpmath", "libgimpwidgets", "po", "desktop"):
        p = root / sub
        if p.is_dir():
            counts[sub] = sum(1 for _ in p.rglob("*") if _.is_file())
    version = _load(DOCTRINE, {}).get("version") or "1.0.0"
    meson = root / "meson.build"
    if meson.is_file():
        for line in meson.read_text(encoding="utf-8", errors="replace").splitlines()[:40]:
            if "version:" in line and "'" in line:
                version = line.split("'", 2)[1]
                break
    rewrite = _load(MANIFEST, {})
    consolidation = _load(CONSOLIDATION, {})
    return {
        "ok": True,
        "path": str(root),
        "upstream_path": str(GIMP_ROOT),
        "version": version,
        "version_hint": version,
        "file_counts": counts,
        "total_files": sum(counts.values()),
        "rewrite_stats": rewrite.get("stats") or {},
        "consolidation": {
            "files_before": consolidation.get("files_before"),
            "files_after": consolidation.get("files_after"),
            "files_removed": consolidation.get("files_removed"),
            "libammoos": "libammoos" in str(consolidation.get("libs", {}).get("removed_libs", [])),
        },
        "os_brand": "AmmoOS",
        "product": "AmmoOS Image",
    }


def posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    inv = _inventory()
    rtx = _run_json(RTX_GATE, "json") if RTX_GATE.is_file() else {"ok": False, "verdict": "FIELD_OPT_CPU"}
    rewrite_status = _run_json(REWRITE, "status") if REWRITE.is_file() else {}
    consolidation_status = _run_json(CONSOLIDATE, "status") if CONSOLIDATE.is_file() else {}
    phases = doctrine.get("rewrite_phases") or []
    active = next((p["id"] for p in phases if p.get("status") == "active"), "phase-1-tree-rewrite")
    doc = {
        "schema": "field-gimp-bridge/v2",
        "ts": _now(),
        "ok": inv.get("ok", False),
        "doctrine": doctrine.get("title", "AmmoOS Image"),
        "product": doctrine.get("product") or "AmmoOS Image",
        "version": doctrine.get("version") or "1.0.0",
        "os_brand": doctrine.get("os_brand") or "AmmoOS",
        "upstream": inv,
        "phases": phases,
        "active_phase": active,
        "field_mandate": doctrine.get("field_mandate") or {},
        "rtx": rtx,
        "rewrite_manifest": rewrite_status,
        "consolidation_manifest": consolidation_status,
        "nexus_program": doctrine.get("nexus_program") or {},
        "host": {"system": platform.system(), "machine": platform.machine()},
        "field_formats": _load(FORMATS, {}),
        "field_io": {
            "backend": str(IO_BACKEND),
            "rtx": rtx,
            "formats": list((_load(FORMATS, {}).get("magics") or {}).keys()),
        },
        "routes": {"panel": "/field-gimp", "api": "/api/field-gimp"},
        "posture": (
            "AmmoOS Image 1.0 — GIMP rewritten for field research; "
            f"g16 {doctrine.get('field_mandate', {}).get('default_profile', 'field_opt')}; "
            f"RTX verdict {rtx.get('verdict', 'FIELD_OPT_CPU')}"
        ),
        "cpu_operable": True,
        "rtx_autodetect": True,
    }
    _save_atomic(PANEL, doc)
    return doc


def build_status() -> dict[str, Any]:
    build_log = SG / "GIMP-Field" / "build" / "build.log"
    configure_log = SG / "GIMP-Field" / "build" / "configure.log"
    out = posture()
    out["build"] = {
        "dir": str(SG / "GIMP-Field" / "build"),
        "script": str(SG / "GIMP-Field" / "build-field-gimp.sh"),
        "configure_log": str(configure_log) if configure_log.is_file() else None,
        "build_log": str(build_log) if build_log.is_file() else None,
    }
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "build":
        print(json.dumps(build_status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "inventory":
        print(json.dumps(_inventory(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "rewrite":
        print(json.dumps(_run_json(REWRITE, "rewrite"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "pipeline":
        print(json.dumps(_run_json(REWRITE, "pipeline"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "consolidate":
        print(json.dumps(_run_json(CONSOLIDATE, "run"), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-gimp-bridge.py [json|build|inventory|rewrite|consolidate|pipeline]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())