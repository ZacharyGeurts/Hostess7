"""Resolve SG Field Kernel, substrate, and field drive paths."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


def sg_root(queen: Path) -> Path:
    env = os.environ.get("SG_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    # NewLatest/Queen → SG
    return queen.parent.parent.resolve()


def kilroy_root(queen: Path) -> Path:
    env = os.environ.get("KILROY_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "scripts" / "build-kilroy.sh").is_file():
            return p
    sg = sg_root(queen)
    for candidate in (
        sg.parent / "KILROY",
        sg / "KILROY",
        Path.home() / "Desktop" / "KILROY",
        Path.home() / "KILROY",
    ):
        if (candidate / "scripts" / "build-kilroy.sh").is_file():
            return candidate.resolve()
    return sg / "KILROY"


def substrate_root(queen: Path) -> Path | None:
    env = os.environ.get("KILROY_COMPAT_SRC", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "Makefile").is_file():
            return p
    sg = sg_root(queen)
    for candidate in (
        sg / "compat" / "linux-7.1.1",
        sg / "linux-kernel" / "linux-7.1.1",
    ):
        if (candidate / "Makefile").is_file():
            return candidate.resolve()
    script = kilroy_root(queen) / "scripts" / "kilroy-compat-path.sh"
    if script.is_file():
        try:
            proc = subprocess.run(
                ["bash", str(script), "--print"],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                p = Path(proc.stdout.strip()).resolve()
                if (p / "Makefile").is_file():
                    return p
        except (subprocess.TimeoutExpired, OSError):
            pass
    return None


def field_storage_root(queen: Path) -> Path | None:
    env = os.environ.get("HOSTESS7_STORAGE", "").strip() or os.environ.get(
        "HOSTESS7_TEAM_FIELD", ""
    ).strip()
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_dir():
            return p
    sg = sg_root(queen)
    candidates = [
        sg / "Hostess7" / "cache" / "fieldstorage",
        sg / "NewLatest" / "AMOURANTHRTX" / "cache" / "fieldstorage",
        queen / "cache" / "fieldstorage",
        queen / ".nexus-field-drive" / "fieldstorage",
        Path("/mnt/team/fieldstorage"),
    ]
    for c in candidates:
        if c.is_dir():
            return c.resolve()
    field_root_py = sg / "NewLatest" / "lib" / "field-root.py"
    if not field_root_py.is_file():
        field_root_py = sg / "Latest" / "NEXUS-Shield" / "lib" / "field-root.py"
    if field_root_py.is_file():
        try:
            proc = subprocess.run(
                ["pythong", str(field_root_py), "primary-path"],
                capture_output=True, text=True, timeout=15,
                env={**os.environ, "SG_ROOT": str(sg)},
            )
            if proc.returncode == 0 and proc.stdout.strip():
                p = Path(proc.stdout.strip()).resolve()
                if p.is_dir():
                    return p
        except (subprocess.TimeoutExpired, OSError):
            pass
    return None


def kernel_artifacts(queen: Path) -> dict[str, Path | None]:
    kilroy = kilroy_root(queen)
    out: dict[str, Path | None] = {
        "bzImage": None,
        "grok_img": None,
        "grok_iso": None,
        "rootfs_staging": None,
    }
    def _safe_file(path: Path) -> Path | None:
        try:
            return path.resolve() if path.is_file() else None
        except OSError:
            return None

    for bz in (
        kilroy / "build" / "bzImage",
        kilroy / "rootfs" / "production-staging" / "boot" / "kilroy" / "bzImage",
        queen.parent / "AMOURANTHRTX" / "build" / "kernel-rtx" / "bzImage",
    ):
        found = _safe_file(bz)
        if found is not None:
            out["bzImage"] = found
            break
    found = _safe_file(kilroy / "build" / "grok-kilroy.img")
    if found is not None:
        out["grok_img"] = found
    found = _safe_file(kilroy / "build" / "grok-kilroy.iso")
    if found is not None:
        out["grok_iso"] = found
    staging = kilroy / "rootfs" / "production-staging"
    try:
        if staging.is_dir() and (staging / "bin" / "busybox").is_file():
            out["rootfs_staging"] = staging.resolve()
    except OSError:
        pass
    return out


def kernel_runtime() -> dict[str, Any]:
    running = Path("/proc/kilroy_field").exists()
    dev = Path("/dev/kilroy_field").exists()
    version = ""
    try:
        version = Path("/proc/version").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        pass
    is_kilroy = "kilroy" in version.lower()
    return {
        "field_kernel_running": running or is_kilroy,
        "proc_kilroy_field": running,
        "dev_kilroy_field": dev,
        "kernel_version": version[:200],
        "is_kilroy": is_kilroy,
    }


def field_status(queen: Path) -> dict[str, Any]:
    sg = sg_root(queen)
    kilroy = kilroy_root(queen)
    substrate = substrate_root(queen)
    storage = field_storage_root(queen)
    arts = kernel_artifacts(queen)
    runtime = kernel_runtime()
    return {
        "schema": "queen-field-paths/v1",
        "sg_root": str(sg),
        "kilroy_root": str(kilroy),
        "kilroy_present": kilroy.is_dir(),
        "substrate": str(substrate) if substrate else None,
        "substrate_ready": substrate is not None,
        "field_storage": str(storage) if storage else None,
        "field_drive_ready": storage is not None,
        "artifacts": {k: str(v) if v else None for k, v in arts.items()},
        "runtime": runtime,
        "field_package": str(queen / "field" / "sovereign"),
    }