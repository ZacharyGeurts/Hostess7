#!/usr/bin/env python3
"""H7s condenser lane — Hostess 7 + Ironclad orchestrate adopt, read, cleanup."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-h7s-lane-panel.json"
ENABLED = os.environ.get("NEXUS_H7S_LANE", "1") == "1"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _import_mod(rel: str, name: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _adopt() -> Any | None:
    return _import_mod("field-h7s-adopt.py", "field_h7s_adopt_lane")


def _cleanup() -> Any | None:
    return _import_mod("field-h7s-cleanup.py", "field_h7s_cleanup_lane")


def _h7s() -> Any | None:
    return _import_mod("field-h7s-format.py", "field_h7s_format_lane")


def _bundle() -> Any | None:
    return _import_mod("field-h7s-desktop-bundle.py", "field_h7s_desktop_lane")


def _reconstruct_chips_redense(read_path: Path, header: dict[str, Any], h7s: Any) -> dict[str, Any]:
    """Reassemble CHIPS redense slices into a combinatorics-shaped document."""
    counts = header.get("counts") or {}
    slice_count = int(header.get("slice_count") or counts.get("redensed_slices") or 0)
    modules: list[dict[str, Any]] = []
    chips: list[dict[str, Any]] = []
    leaves: list[dict[str, Any]] = []
    for i in range(slice_count):
        hit = h7s.instant_execute(read_path, slice_index=i)
        mod = hit.get("slice")
        if not isinstance(mod, dict):
            continue
        modules.append(mod)
        fam = str(mod.get("family") or "unknown")
        for lid in mod.get("leaf_ids") or []:
            lid_s = str(lid)
            chip_id = lid_s.split(":", 2)[-1] if lid_s.startswith("chip:") else lid_s
            leaves.append({"id": lid_s, "chip_id": chip_id, "family": fam})
            chips.append({
                "id": chip_id,
                "family": fam,
                "combinatorics_leaf": lid_s,
                "label": chip_id,
            })
    orig = str(header.get("original_name") or read_path.name)
    if "plate-stack" in orig or "plate_stack" in orig:
        schema = "field-chips-plate-stack/v1"
    elif "chips-core" in orig or "chips_core" in orig:
        schema = "field-chips-core/v1"
    else:
        schema = "field-ironclad-chips-combinatorics/v1"
    chip_n = len(chips) or int(counts.get("source_chips") or 0)
    leaf_n = len(leaves) or int(counts.get("source_leaves") or 0)
    mod_n = len(modules) or int(counts.get("source_modules") or 0)
    return {
        "schema": schema,
        "h7s_reconstructed": True,
        "chips": chips,
        "combinatorics_leaves": leaves,
        "modules": modules,
        "core_modules": modules,
        "counts": {
            "chips": chip_n,
            "leaves": leaf_n,
            "modules": mod_n,
            "core_modules": mod_n,
            "resolution_lossless": True,
        },
    }


def load_json(path: Path, default: Any = None) -> Any:
    """Hot read — handle H7s in-place at original extension; CHIPS redense slice-fast."""
    adopt = _adopt()
    h7s = _h7s()
    if adopt and h7s:
        read_path = adopt.resolve_read_path(path)
        try:
            blob = read_path.read_bytes()
            if h7s.is_h7s_blob(blob):
                header, _, _, _ = h7s.parse_h7s(blob)
                inner = header.get("inner_kind") or ""
                if header.get("lossless_restore", True) and inner != "chips_redense":
                    raw = h7s.restore_bytes(blob)
                    return json.loads(raw.decode("utf-8"))
                if inner == "chips_redense":
                    return _reconstruct_chips_redense(read_path, header, h7s)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def sync_speedup(path: Path, *, apply: bool = True) -> dict[str, Any]:
    """Repack in-place when native JSON was published over H7s disguise."""
    adopt = _adopt()
    h7s = _h7s()
    if not adopt or not path.is_file():
        return {"ok": False, "reason": "missing", "path": str(path)}
    if adopt.is_kernel_boot_artifact(path):
        return {"ok": False, "reason": "kernel_boot_excluded", "path": str(path)}
    dest = adopt.speedup_dest(path)
    try:
        if h7s and adopt.is_h7s_at_path(path) if hasattr(adopt, "is_h7s_at_path") else h7s.is_h7s_blob(path.read_bytes()):
            return {"ok": True, "skipped": True, "reason": "h7s_in_place", "path": str(path), "sidecars": False}
    except OSError:
        pass
    if not apply:
        return {"ok": True, "dry_run": True, "path": str(path), "dest": str(dest), "in_place": True, "sidecars": False}
    return adopt.adopt_speedup(path, apply=True)


def after_json_publish(path: Path) -> dict[str, Any]:
    """Hook after Ironclad / panel / CHIPS writes native JSON."""
    if not ENABLED:
        return {"ok": True, "skipped": True, "reason": "lane_disabled"}
    return sync_speedup(path, apply=True)


def ironclad_lane(*, pack_desktop: bool = True) -> dict[str, Any]:
    """Ironclad seal hook — speedup CHIPS corpora + optional desktop bundle grow."""
    if not ENABLED:
        return {"ok": True, "lane": "ironclad", "skipped": True}
    results: dict[str, Any] = {"lane": "ironclad", "sync": [], "desktop": None}
    for rel in (
        "field-chips-core.json",
        "field-ironclad-chips-combinatorics.json",
        "field-g16-universal-combinatronic.json",
    ):
        p = STATE / rel
        if p.is_file():
            results["sync"].append(after_json_publish(p))
    if pack_desktop:
        bmod = _bundle()
        if bmod and hasattr(bmod, "pack_desktop_bundle"):
            try:
                results["desktop"] = bmod.pack_desktop_bundle(grow=True)
            except Exception as exc:
                results["desktop"] = {"ok": False, "error": str(exc)[:200]}
    results["ok"] = True
    results["updated"] = _now()
    return results


def hostess7_lane(*, cleanup: bool = False, ocr_clean: bool = False) -> dict[str, Any]:
    """Hostess 7 maintenance tick — adopt hot corpora, H7s FS, optional OCR/data cleanup."""
    if not ENABLED:
        return {"ok": True, "lane": "hostess7", "skipped": True}
    adopt = _adopt()
    results: dict[str, Any] = {"lane": "hostess7", "adopt": None, "audit": None, "fs": None, "cleanup": None, "ocr": None}
    if adopt:
        results["adopt"] = adopt.adopt_all(apply=True)
        results["audit"] = adopt.audit()
    fs = _import_mod("field-h7s-fs.py", "field_h7s_lane_fs")
    if fs and hasattr(fs, "adopt_state_tree"):
        results["fs"] = fs.adopt_state_tree(apply=True)
    bmod = _bundle()
    if bmod and hasattr(bmod, "bundle_status"):
        results["desktop"] = bmod.bundle_status()
    cmod = _cleanup()
    if cmod:
        if ocr_clean and hasattr(cmod, "clean_ocr"):
            results["ocr"] = cmod.clean_ocr(dry_run=False)
        if cleanup and hasattr(cmod, "clean"):
            results["cleanup"] = cmod.clean(dry_run=False)
    results["ok"] = True
    results["updated"] = _now()
    _save(PANEL, results)
    return results


def lane_status() -> dict[str, Any]:
    adopt = _adopt()
    bmod = _bundle()
    return {
        "schema": "field-h7s-lane/v1",
        "ok": True,
        "enabled": ENABLED,
        "kilroy_kernel_boot_excluded": True,
        "adopt_audit": adopt.audit() if adopt else None,
        "desktop": bmod.bundle_status() if bmod else None,
        "panel": str(PANEL),
        "updated": _now(),
    }


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    cmd = (args[0] if args else "status").lower()
    if cmd in ("status", "json"):
        print(json.dumps(lane_status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ironclad":
        print(json.dumps(ironclad_lane(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "hostess7":
        cleanup = "--cleanup" in args
        ocr_clean = "--ocr-clean" in args
        print(json.dumps(hostess7_lane(cleanup=cleanup, ocr_clean=ocr_clean), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ocr-clean":
        cmod = _cleanup()
        apply = "--apply" in args
        if cmod and hasattr(cmod, "clean_ocr"):
            print(json.dumps(cmod.clean_ocr(dry_run=not apply), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps({"ok": False, "error": "cleanup_module_missing"}, indent=2))
        return 1
    if cmd == "load" and len(args) >= 2:
        doc = load_json(Path(args[1]))
        print(json.dumps({"ok": True, "keys": list(doc.keys())[:12] if isinstance(doc, dict) else None}, indent=2))
        return 0
    if cmd == "sync" and len(args) >= 2:
        print(json.dumps(sync_speedup(Path(args[1]), apply="--apply" in args), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["status", "ironclad", "hostess7 [--cleanup]", "load <json>", "sync <json> [--apply]"],
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())