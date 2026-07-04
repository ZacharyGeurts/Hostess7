#!/usr/bin/env python3
"""Provision former Qubes disk (sdb) as FIELD_QUBES — field build cache + stabilizer staging."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-qubes-drive-panel.json"

QUBES_CANDIDATES = (
    "/dev/sdb",
    "/dev/disk/by-id/ata-T-FORCE_1TB_TPBF2411190010300627",
)
TEAM_MOUNT = Path(os.environ.get("HOSTESS7_TEAM_MOUNT", "/media/default/HOSTESS7_TEAM1"))
TEAM_FIELD = Path(os.environ.get("HOSTESS7_TEAM_FIELD", str(TEAM_MOUNT / "fieldstorage")))
LABEL = "FIELD_QUBES"
MOUNT = Path(os.environ.get("FIELD_QUBES_MOUNT", "/media/default/FIELD_QUBES"))


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _run(cmd: list[str], *, timeout: int = 600) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "ok": proc.returncode == 0,
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[-2000:],
            "stderr": (proc.stderr or "")[-2000:],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "cmd": cmd, "error": type(exc).__name__, "detail": str(exc)[:300]}


def _lsblk() -> list[dict[str, Any]]:
    out = _run(["lsblk", "-J", "-o", "NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINT,MODEL"])
    if not out.get("ok"):
        return []
    try:
        doc = json.loads(out.get("stdout") or "{}")
        return doc.get("blockdevices") or []
    except json.JSONDecodeError:
        return []


def _find_qubes_disk() -> str | None:
    for dev in QUBES_CANDIDATES:
        if Path(dev).exists():
            return dev
    for row in _lsblk():
        model = str(row.get("model") or "").upper()
        if "T-FORCE" in model and row.get("type") == "disk":
            return f"/dev/{row.get('name')}"
    return None


def _layout_paths(root: Path) -> dict[str, Path]:
    return {
        "root": root,
        "fieldstorage": root / "fieldstorage",
        "build_cache": root / "fieldstorage" / "build-cache",
        "g16_rtx": root / "fieldstorage" / "build-cache" / "g16-rtx",
        "cmake": root / "fieldstorage" / "build-cache" / "cmake",
        "roms": root / "fieldstorage" / "build-cache" / "queen-roms",
        "zacs": root / "fieldstorage" / "zacs-mirror",
        "stabilizer": root / "fieldstorage" / "stabilizer-staging",
    }


def ensure_team_layout() -> dict[str, Any]:
    paths = _layout_paths(TEAM_FIELD)
    created = []
    for key, p in paths.items():
        if key == "root":
            continue
        p.mkdir(parents=True, exist_ok=True)
        created.append(str(p))
    local_cmake = Path.home() / ".local" / "cmake-full"
    if local_cmake.is_dir() and not (paths["cmake"] / "usr").is_dir():
        try:
            shutil.copytree(local_cmake, paths["cmake"], dirs_exist_ok=True, symlinks=True)
        except OSError as exc:
            pass
    rom_src = INSTALL / "assets" / "dos" / "incoming"
    if rom_src.is_dir():
        for sys_d in rom_src.iterdir():
            if sys_d.is_dir():
                dst = paths["roms"] / sys_d.name
                dst.mkdir(parents=True, exist_ok=True)
                for rom in sys_d.glob("*"):
                    if rom.is_file() and rom.stat().st_size > 64:
                        hit = dst / rom.name
                        if not hit.is_file():
                            try:
                                shutil.copy2(rom, hit)
                            except OSError:
                                pass
    return {"ok": True, "team_field": str(TEAM_FIELD), "created": created}


def wipe_and_format_qubes(*, confirm: bool = False) -> dict[str, Any]:
    dev = _find_qubes_disk()
    if not dev:
        return {"ok": False, "error": "qubes_disk_not_found", "candidates": list(QUBES_CANDIDATES)}
    if not confirm:
        return {
            "ok": False,
            "error": "confirm_required",
            "device": dev,
            "hint": f"Run: {Path(__file__).name} wipe --confirm",
            "destructive": True,
        }
    steps = []
    for part in Path("/dev").glob(f"{Path(dev).name}[0-9]*"):
        steps.append(_run(["udisksctl", "unmount", "-b", str(part)], timeout=30))
    steps.append(_run([
        "gdbus", "call", "--system",
        "--dest", "org.freedesktop.UDisks2",
        "--object-path", f"/org/freedesktop/UDisks2/block_devices/{Path(dev).name}",
        "--method", "org.freedesktop.UDisks2.Block.Format",
        "ext4", "{}",
    ], timeout=900))
    ok = any(s.get("ok") for s in steps)
    mount = _run(["udisksctl", "mount", "-b", dev], timeout=120)
    mount_point = ""
    if mount.get("ok"):
        for line in (mount.get("stdout") or "").splitlines():
            if "at" in line:
                mount_point = line.split("at", 1)[-1].strip()
    root = Path(mount_point) if mount_point else MOUNT
    layout = {}
    if root.is_dir():
        layout = _layout_paths(root / "fieldstorage" if (root / "fieldstorage").is_dir() else root)
        for key, p in layout.items():
            if key != "root":
                p.mkdir(parents=True, exist_ok=True)
    return {
        "ok": ok or mount.get("ok"),
        "device": dev,
        "label": LABEL,
        "mount": str(root) if root else None,
        "steps": steps,
        "mount_result": mount,
        "layout": {k: str(v) for k, v in layout.items()} if layout else {},
    }


def _aia_lane() -> dict[str, Any]:
    aia_py = INSTALL / "lib" / "field-aia-accelerator.py"
    if not aia_py.is_file():
        return {"present": False}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("qubes_aia_lane", aia_py)
        if not spec or not spec.loader:
            return {"present": False}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "export_aia_bundle"):
            row = mod.export_aia_bundle(write_readme=False)
            return {"present": True, "repo": "ZacharyGeurts/AIA", **row}
    except Exception as exc:
        return {"present": True, "ok": False, "error": str(exc)[:200]}
    return {"present": False}


def panel() -> dict[str, Any]:
    dev = _find_qubes_disk()
    team = ensure_team_layout()
    mount_ready = MOUNT.is_dir()
    doc = {
        "schema": "field-qubes-drive-panel/v1",
        "updated": _now(),
        "qubes_device": dev,
        "qubes_mount": str(MOUNT),
        "qubes_mounted": mount_ready,
        "team_mount": str(TEAM_MOUNT),
        "team_field": str(TEAM_FIELD),
        "team_layout": team,
        "lsblk": _lsblk(),
        "aia_accelerator": {
            "repo": "ZacharyGeurts/AIA",
            "pages_url": "https://zacharygeurts.github.io/AIA/",
            "hostess7_api": "/api/field-aia-accelerator",
            "lane": _aia_lane(),
        },
        "steel_plate_ids": [
            "steel_plate:field_qubes_drive",
            "steel_plate:g16_build_cache",
            "steel_plate:field_big_drive",
            "steel_plate:aia_accelerator",
        ],
    }
    PANEL.parent.mkdir(parents=True, exist_ok=True)
    PANEL.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd == "wipe":
        confirm = "--confirm" in sys.argv[2:]
        print(json.dumps(wipe_and_format_qubes(confirm=confirm), indent=2))
        return 0
    if cmd == "team-layout":
        print(json.dumps(ensure_team_layout(), indent=2))
        return 0
    if cmd in ("aia-export", "export-aia"):
        aia_py = INSTALL / "lib" / "field-aia-accelerator.py"
        if aia_py.is_file():
            import importlib.util

            spec = importlib.util.spec_from_file_location("qubes_aia_export", aia_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "export_aia_bundle"):
                    print(json.dumps(mod.export_aia_bundle(), indent=2))
                    return 0
        print(json.dumps({"ok": False, "error": "field_aia_accelerator_missing"}, indent=2))
        return 1
    print(json.dumps(panel(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())