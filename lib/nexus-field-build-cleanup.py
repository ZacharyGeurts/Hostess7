#!/usr/bin/env pythong
"""NEXUS field build cleanup — remove stale compile trees; keep source and nexus.sh OS."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "nexus-field-build-cleanup-panel.json"

# Regenerable artifacts only — never delete panel/, lib/, data/, Queen source
ARTIFACT_DIRS: tuple[str, ...] = (
    "Queen/build",
    "Queen/build-rtx",
    "Grok16/build",
    "KILROY/build",
    "ZNetwork/build",
    "GIMP/build",
    "OBS-FieldVoiceFilter/build",
    "World_Redata/cpp/build",
    "CMakeFiles",
    "dist/ammoos-2.0.0-beta",
    "dist/ammoos-export-2.0.0-beta",
)

ARTIFACT_FILES: tuple[str, ...] = (
    "amouranth_engine.log",
    "Queen/amouranth_engine.log",
    "dist/ammoos-beta2-build.log",
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
    except OSError:
        pass
    return total


def _remove_path(path: Path, *, results: dict[str, Any]) -> int:
    if not path.exists():
        return 0
    try:
        size = _dir_size(path) if path.is_dir() else path.stat().st_size
    except OSError:
        size = 0
    try:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        results["removed"].append({"path": str(path.relative_to(INSTALL)), "bytes": size})
        return size
    except OSError as exc:
        results["errors"].append({"path": str(path), "error": str(exc)})
        return 0


def cleanup(*, dry_run: bool = False) -> dict[str, Any]:
    results: dict[str, Any] = {
        "schema": "nexus-field-build-cleanup/v1",
        "updated": _now(),
        "ok": True,
        "dry_run": dry_run,
        "install_root": str(INSTALL),
        "motto": "Build trees cleaned — ./nexus.sh is the OS launcher.",
        "removed": [],
        "errors": [],
        "bytes_freed": 0,
    }
    for rel in ARTIFACT_DIRS:
        path = INSTALL / rel
        if dry_run:
            if path.exists():
                results["removed"].append({"path": rel, "bytes": _dir_size(path) if path.is_dir() else 0, "dry": True})
            continue
        results["bytes_freed"] += _remove_path(path, results=results)
    for rel in ARTIFACT_FILES:
        path = INSTALL / rel
        if dry_run:
            if path.is_file():
                results["removed"].append({"path": rel, "bytes": path.stat().st_size, "dry": True})
            continue
        results["bytes_freed"] += _remove_path(path, results=results)
    if results["errors"]:
        results["ok"] = len(results["errors"]) < 2
    STATE.mkdir(parents=True, exist_ok=True)
    if not dry_run:
        PANEL.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return results


def main() -> int:
    dry = "--dry" in sys.argv or os.environ.get("NEXUS_CLEAN_DRY", "") == "1"
    doc = cleanup(dry_run=dry)
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    freed_mb = int(doc.get("bytes_freed", 0) / (1024 * 1024))
    if not dry and freed_mb:
        print(f"freed ~{freed_mb} MB", file=sys.stderr)
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())