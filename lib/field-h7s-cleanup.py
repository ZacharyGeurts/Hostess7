#!/usr/bin/env python3
"""H7s data cleanup — dedupe ingested sources; keep field-desktop.h7s canonical."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-h7s-global-doctrine.json"
BUNDLE = STATE / "field-desktop.h7s"
LIBRARY = STATE / "queen-program-library.json"
FINAL_EYE_OUT = INSTALL / "Final_Eye" / "out"
FINAL_EYE_MANIFEST = INSTALL / "Final_Eye" / "manifest.jsonl"
OCR_DESKTOP = STATE / "ocr-desktop"
PANEL = STATE / "field-h7s-cleanup-panel.json"
DEFAULT_OCR_KEEP = frozenset({"desktop-live"})

KEEP_H7S = frozenset({"field-desktop.h7s"})
DEV_LOGS = ("ammolang-hang-freeze.log", "field-ammolang-build.log")


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


def _import_bundle() -> Any | None:
    path = INSTALL / "lib" / "field-h7s-desktop-bundle.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_h7s_cleanup_bundle", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _bundle_blob_digests() -> set[str]:
    bmod = _import_bundle()
    if not bmod or not BUNDLE.is_file():
        return set()
    manifest = bmod.read_manifest(BUNDLE)
    return set((manifest.get("blobs") or {}).keys())


def _bundle_icon_ids() -> set[str]:
    bmod = _import_bundle()
    if not bmod or not BUNDLE.is_file():
        return set()
    manifest = bmod.read_manifest(BUNDLE)
    return set((manifest.get("icons") or {}).keys())


def audit_ocr() -> dict[str, Any]:
    bmod = _import_bundle()
    ocr_count = 0
    ocr_ids: list[str] = []
    if bmod and BUNDLE.is_file():
        m = bmod.read_manifest(BUNDLE)
        ocr = m.get("ocr") or {}
        ocr_count = len(ocr)
        ocr_ids = sorted(ocr.keys())[:20]
    out_files = 0
    if FINAL_EYE_OUT.is_dir():
        out_files = sum(1 for p in FINAL_EYE_OUT.rglob("*") if p.is_file() and p.name != "manifest.jsonl")
    manifest_lines = 0
    if FINAL_EYE_MANIFEST.is_file():
        manifest_lines = sum(1 for line in FINAL_EYE_MANIFEST.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())
    desktop_loose = 0
    if OCR_DESKTOP.is_dir():
        desktop_loose = sum(1 for p in OCR_DESKTOP.iterdir() if p.is_file())
    return {
        "schema": "field-h7s-ocr-cleanup-audit/v1",
        "ok": True,
        "bundle_ocr_count": ocr_count,
        "bundle_ocr_sample": ocr_ids,
        "final_eye_out_files": out_files,
        "manifest_lines": manifest_lines,
        "ocr_desktop_loose": desktop_loose,
        "keep_default": sorted(DEFAULT_OCR_KEEP),
    }


def clean_ocr(
    *,
    dry_run: bool = True,
    keep_ids: set[str] | frozenset[str] | None = None,
    wipe_manifest: bool = True,
) -> dict[str, Any]:
    """Purge stale OCR — bundle keeps live feed; wipe Final_Eye/out sources."""
    keep = set(keep_ids or DEFAULT_OCR_KEEP)
    audit_before = audit_ocr()
    removed: list[dict[str, Any]] = []
    reclaimed = 0
    prune_result: dict[str, Any] | None = None

    if not dry_run:
        bmod = _import_bundle()
        if bmod and hasattr(bmod, "prune_ocr_feeds"):
            prune_result = bmod.prune_ocr_feeds(keep)

    if FINAL_EYE_OUT.is_dir():
        for path in sorted(FINAL_EYE_OUT.rglob("*")):
            if not path.is_file() or path.name == "manifest.jsonl":
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if not dry_run:
                try:
                    path.unlink()
                except OSError:
                    continue
            removed.append({"path": str(path.relative_to(INSTALL)), "bytes": size, "lane": "final_eye_out"})
            reclaimed += size

    if OCR_DESKTOP.is_dir():
        for path in sorted(OCR_DESKTOP.iterdir()):
            if not path.is_file():
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if not dry_run:
                try:
                    path.unlink()
                except OSError:
                    continue
            removed.append({"path": str(path.relative_to(INSTALL)), "bytes": size, "lane": "ocr_desktop"})
            reclaimed += size

    manifest_trimmed = 0
    if wipe_manifest and FINAL_EYE_MANIFEST.is_file():
        try:
            old_lines = FINAL_EYE_MANIFEST.read_text(encoding="utf-8", errors="replace").splitlines()
            manifest_trimmed = len([ln for ln in old_lines if ln.strip()])
            if not dry_run:
                FINAL_EYE_MANIFEST.write_text("", encoding="utf-8")
        except OSError:
            pass

    fs_mod = _import_mod("field-h7s-fs.py", "field_h7s_cleanup_fs")
    fs_adopt = None
    if fs_mod and hasattr(fs_mod, "adopt_state_tree") and not dry_run:
        fs_adopt = fs_mod.adopt_state_tree(apply=True)

    return {
        "schema": "field-h7s-ocr-cleanup/v1",
        "ok": True,
        "dry_run": dry_run,
        "kept_feeds": sorted(keep),
        "prune": prune_result,
        "removed_count": len(removed),
        "reclaimed_bytes": reclaimed,
        "manifest_lines_cleared": manifest_trimmed,
        "fs_adopt": fs_adopt,
        "audit_before": audit_before,
        "removed": removed[:40],
        "updated": _now(),
    }


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


def audit() -> dict[str, Any]:
    digests = _bundle_blob_digests()
    icon_ids = _bundle_icon_ids()
    bundle_live = BUNDLE.is_file()

    final_eye_dupes: list[dict[str, Any]] = []
    if FINAL_EYE_OUT.is_dir() and digests:
        for path in sorted(FINAL_EYE_OUT.rglob("*")):
            if not path.is_file():
                continue
            if path.name == "manifest.jsonl":
                continue
            digest = _sha256_file(path)
            if digest and digest in digests:
                try:
                    final_eye_dupes.append({
                        "path": str(path.relative_to(INSTALL)),
                        "bytes": path.stat().st_size,
                        "sha256": digest[:16],
                    })
                except ValueError:
                    pass

    loose_h7s: list[dict[str, Any]] = []
    if STATE.is_dir():
        for path in STATE.glob("*.h7s"):
            if path.name in KEEP_H7S:
                continue
            if path.name.endswith(".json.h7s"):
                loose_h7s.append({
                    "path": str(path.relative_to(INSTALL)),
                    "bytes": path.stat().st_size,
                    "legacy_sidecar": True,
                    "migrate_to": str(path.with_suffix("").relative_to(INSTALL)),
                })
                continue
            loose_h7s.append({"path": str(path.relative_to(INSTALL)), "bytes": path.stat().st_size})

    plate_bak: list[dict[str, Any]] = []
    meld = STATE / "plate-meld-redundant"
    if meld.is_dir():
        for path in meld.rglob("*.bak"):
            if path.is_file():
                plate_bak.append({"path": str(path.relative_to(INSTALL)), "bytes": path.stat().st_size})

    dev_logs: list[dict[str, Any]] = []
    trim_mb = float((_load(DOCTRINE, {}).get("cleanup") or {}).get("dev_log_trim_mb") or 2)
    for name in DEV_LOGS:
        p = STATE / name
        if p.is_file() and p.stat().st_size > trim_mb * 1024 * 1024:
            dev_logs.append({"path": str(p.relative_to(INSTALL)), "bytes": p.stat().st_size})

    library_annotatable = 0
    if LIBRARY.is_file() and icon_ids:
        doc = _load(LIBRARY, {})
        for eid in (doc.get("entries") or {}):
            if eid in icon_ids:
                library_annotatable += 1

    reclaim = sum(r["bytes"] for r in final_eye_dupes + loose_h7s + plate_bak + dev_logs)
    return {
        "schema": "field-h7s-cleanup-audit/v1",
        "ok": True,
        "bundle_live": bundle_live,
        "bundle": str(BUNDLE),
        "bundle_bytes": BUNDLE.stat().st_size if bundle_live else 0,
        "blob_count": len(digests),
        "icon_count": len(icon_ids),
        "final_eye_dupes": final_eye_dupes,
        "loose_h7s": loose_h7s,
        "plate_meld_bak": plate_bak,
        "dev_logs": dev_logs,
        "library_annotatable": library_annotatable,
        "reclaimable_bytes": reclaim,
        "updated": _now(),
    }


def _remove(path: Path, *, dry_run: bool, removed: list[dict[str, Any]]) -> int:
    if not path.is_file():
        return 0
    try:
        size = path.stat().st_size
    except OSError:
        return 0
    if not dry_run:
        try:
            path.unlink()
        except OSError:
            return 0
    removed.append({"path": str(path), "bytes": size})
    return size


def migrate_legacy_sidecars(*, dry_run: bool = True) -> dict[str, Any]:
    """Fold legacy *.ext.h7s twins into canonical paths — same extension, no sidecars."""
    adopt = _import_mod("field-h7s-adopt.py", "field_h7s_cleanup_adopt")
    if not adopt or not hasattr(adopt, "migrate_legacy_sidecar"):
        return {"ok": False, "error": "h7s_adopt_missing"}
    rows: list[dict[str, Any]] = []
    migrated = 0
    targets: list[Path] = []
    if hasattr(adopt, "hot_corpus_paths"):
        targets.extend(adopt.hot_corpus_paths())
    if STATE.is_dir():
        for leg in STATE.rglob("*.h7s"):
            if leg.name.count(".") >= 2 and leg.name.endswith(".h7s"):
                targets.append(leg.with_suffix(""))
    seen: set[str] = set()
    for src in targets:
        key = str(src)
        if key in seen:
            continue
        seen.add(key)
        row = adopt.migrate_legacy_sidecar(src, apply=not dry_run)
        rows.append(row)
        if row.get("migrated"):
            migrated += 1
    return {
        "schema": "field-h7s-migrate-legacy-sidecars/v1",
        "ok": True,
        "dry_run": dry_run,
        "sidecars": False,
        "in_place": True,
        "migrated_count": migrated,
        "rows": rows,
        "updated": _now(),
    }


def reclaim_native_json(*, dry_run: bool = True) -> dict[str, Any]:
    """Deprecated — sidecars removed; migrate legacy twins in-place instead."""
    return migrate_legacy_sidecars(dry_run=dry_run)


def clean(*, dry_run: bool = True, annotate_library: bool = True, reclaim_native: bool = True) -> dict[str, Any]:
    report = audit()
    removed: list[dict[str, Any]] = []
    reclaimed = 0

    for row in report.get("final_eye_dupes") or []:
        p = INSTALL / row["path"]
        reclaimed += _remove(p, dry_run=dry_run, removed=removed)

    for row in report.get("loose_h7s") or []:
        p = INSTALL / row["path"]
        reclaimed += _remove(p, dry_run=dry_run, removed=removed)

    for row in report.get("plate_meld_bak") or []:
        p = INSTALL / row["path"]
        reclaimed += _remove(p, dry_run=dry_run, removed=removed)

    for row in report.get("dev_logs") or []:
        p = INSTALL / row["path"]
        reclaimed += _remove(p, dry_run=dry_run, removed=removed)

    native_reclaim: dict[str, Any] | None = None
    if reclaim_native:
        native_reclaim = reclaim_native_json(dry_run=dry_run)
        reclaimed += int(native_reclaim.get("reclaimed_bytes") or 0)
        removed.extend(native_reclaim.get("removed") or [])

    library_updated = 0
    if annotate_library and LIBRARY.is_file() and not dry_run:
        icon_ids = _bundle_icon_ids()
        bmod = _import_bundle()
        doc = _load(LIBRARY, {})
        entries = doc.get("entries") or {}
        for eid, row in entries.items():
            if eid not in icon_ids:
                continue
            ref = (bmod.read_manifest(BUNDLE).get("icons") or {}).get(eid) if bmod else {}
            row["icon_h7s"] = True
            row["icon_sha256"] = ref.get("sha256")
            row["icon_source"] = "field-desktop.h7s"
            library_updated += 1
        if library_updated:
            doc["entries"] = entries
            doc["h7s_bundle"] = str(BUNDLE.relative_to(INSTALL))
            doc["updated"] = _now()
            _save(LIBRARY, doc)

    result = {
        "schema": "field-h7s-cleanup/v1",
        "ok": True,
        "dry_run": dry_run,
        "removed_count": len(removed),
        "reclaimed_bytes": reclaimed,
        "library_annotated": library_updated,
        "removed": removed,
        "native_reclaim": native_reclaim,
        "audit_before": {
            "reclaimable_bytes": report.get("reclaimable_bytes"),
            "final_eye_dupes": len(report.get("final_eye_dupes") or []),
        },
        "updated": _now(),
    }
    if not dry_run:
        _save(PANEL, result)
    return result


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    cmd = (args[0] if args else "audit").lower()
    apply = "--apply" in args

    if cmd == "audit":
        print(json.dumps(audit(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("audit-ocr", "ocr-audit"):
        print(json.dumps(audit_ocr(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("reclaim-native", "reclaim_native", "migrate-sidecars", "migrate_sidecars"):
        print(json.dumps(migrate_legacy_sidecars(dry_run=not apply), ensure_ascii=False, indent=2))
        return 0
    if cmd == "clean":
        print(json.dumps(clean(dry_run=not apply), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("clean-ocr", "ocr-clean"):
        print(json.dumps(clean_ocr(dry_run=not apply), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["audit", "audit-ocr", "reclaim-native [--apply]", "clean [--apply]", "clean-ocr [--apply]"],
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())