#!/usr/bin/env pythong
"""KILROY Field OS diagnostics — JSON report for host graft, live kernel, and QEMU."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KILROY = Path(os.environ.get("KILROY_ROOT", ""))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", KILROY.parent if KILROY else Path(".")))
PROC = Path("/proc/kilroy_field")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_proc(name: str, limit: int = 4000) -> str | None:
    p = PROC / name
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
        return text[:limit] if text else None
    except OSError:
        return None


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _bzimage_info(kr: Path) -> dict[str, Any]:
    bz = kr / "build" / "bzImage"
    out: dict[str, Any] = {"path": str(bz), "present": bz.is_file()}
    if bz.is_file():
        out["bytes"] = bz.stat().st_size
        try:
            proc = subprocess.run(
                ["strings", str(bz)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            blob = proc.stdout
            out["release_1_0"] = "1.0.0" in blob
            out["kilroy_field"] = "kilroy_field" in blob
            out["debug_proc"] = "kilroy-debug" in blob or "/proc/kilroy_field/debug" in blob
        except (subprocess.TimeoutExpired, OSError):
            pass
    return out


def build_report() -> dict[str, Any]:
    kr = KILROY if KILROY.is_dir() else INSTALL / "KILROY"
    proc_live = PROC.is_dir()
    nodes = [
        "status", "boot", "security", "debug", "brain", "ai", "stack",
        "slots", "cpu", "ram", "flow", "cache", "direct", "gpu", "audio", "eye", "power",
    ]
    proc_nodes: dict[str, Any] = {}
    for n in nodes:
        proc_nodes[n] = {
            "present": (PROC / n).exists(),
            "readable": os.access(PROC / n, os.R_OK) if (PROC / n).exists() else False,
            "preview": _read_proc(n, 500) if proc_live else None,
        }

    brain: dict[str, Any] = {}
    brain_py = INSTALL / "lib" / "kilroy-field-brain.py"
    if brain_py.is_file():
        try:
            env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "KILROY_ROOT": str(kr)}
            proc = subprocess.run(
                [sys.executable, str(brain_py), "evaluate", "127.0.0.1"],
                capture_output=True,
                text=True,
                timeout=15,
                env=env,
            )
            if proc.stdout.strip():
                brain["home_verdict"] = json.loads(proc.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            brain["error"] = "brain_evaluate_failed"

    final_eye: dict[str, Any] = {}
    eye_py = INSTALL / "lib" / "kilroy-final-eye-brain.py"
    if eye_py.is_file():
        try:
            env = {
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "KILROY_ROOT": str(kr),
                "NEXUS_STATE_DIR": os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")),
            }
            proc = subprocess.run(
                [sys.executable, str(eye_py), "ocr-brain"],
                capture_output=True,
                text=True,
                timeout=20,
                env=env,
            )
            if proc.stdout.strip():
                final_eye = json.loads(proc.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            final_eye = {"error": "ocr_brain_failed"}

    qemu_log = kr / "build" / "qemu-serial.log"
    qemu_diag = kr / "build" / "qemu-diagnostics.log"
    qemu: dict[str, Any] = {"serial_log": str(qemu_log) if qemu_log.is_file() else None}
    if qemu_log.is_file():
        text = qemu_log.read_text(encoding="utf-8", errors="replace")
        qemu["banner"] = "KILROY Field OS 1.0.0" in text
        qemu["field_init_ok"] = "field-init" in text and "smoke OK" in text
        qemu["init_panic"] = "Attempted to kill init" in text
        qemu["debug_proc"] = "kilroy-debug" in text or "schema=kilroy-debug" in text

    return {
        "schema": "kilroy-diagnostics/v1",
        "updated": _now(),
        "host": {
            "machine": platform.machine(),
            "kernel": platform.release(),
            "graft_mode": not proc_live,
        },
        "kilroy": {
            "root": str(kr),
            "version": _load_json(kr / "data" / "kilroy-version.json"),
            "linux_tree": str(kr / "linux-1.0") if (kr / "linux-1.0").is_dir() else None,
            "bzimage": _bzimage_info(kr),
        },
        "proc_live": proc_live,
        "proc_nodes": proc_nodes,
        "debug": _read_proc("debug", 3000) if proc_live else None,
        "brain": brain,
        "final_eye": final_eye,
        "qemu": qemu,
        "logs": {
            "diagnostics": str(kr / "build" / "diagnostics.log"),
            "qemu_serial": str(qemu_log) if qemu_log.is_file() else None,
            "qemu_diag": str(qemu_diag) if qemu_diag.is_file() else None,
        },
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    doc = build_report()
    if cmd in ("json", "report", "status"):
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    if cmd == "proc" and doc.get("debug"):
        print(doc["debug"])
        return 0
    print(json.dumps({"error": "usage: kilroy-diagnostics.py [json|proc]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())