#!/usr/bin/env pythong
"""H7 visual asset adoption — combinatronic PNGs → in-place H7s; skip disguised containers."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve()
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parents[1])))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-combinatronic-visuals-doctrine.json"
PANEL = STATE / "field-h7-visual-adopt-panel.json"
REGISTRY = STATE / "field-h7-visual-adopt-registry.json"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
H7S_MAGIC = b"H7S\x01"
H7_MAGIC = b"H7\x07\x01"
H7E_MAGIC = b"H7E\x01"

VISUAL_DIRS = (
    "data/combinatronic-visuals/chips",
    "data/combinatronic-visuals/chips/thumbs",
    "data/combinatronic-visuals/chips/detail",
    "data/combinatronic-visuals/books",
    "data/combinatronic-visuals/formats",
    "Queen/world/assets/combinatronic/chips",
    "Queen/world/assets/combinatronic/chips/thumbs",
    "Queen/world/assets/combinatronic/chips/detail",
    "Queen/world/assets/combinatronic/books",
    "Queen/world/assets/combinatronic/formats",
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    mod_key = f"field_adopt_{name}_{rel.replace('/', '_').replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(mod_key, path)
    if not spec or not spec.loader:
        return None
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _h7_family() -> Any | None:
    return _import_mod("field_h7_family", "lib/field-h7-format.py")


def _h7s_mod() -> Any | None:
    return _import_mod("field_h7s", "lib/field-h7s-format.py")


def _h7s_adopt() -> Any | None:
    return _import_mod("field_h7s_adopt", "lib/field-h7s-adopt.py")


def visual_png_paths() -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for rel in VISUAL_DIRS:
        root = INSTALL / rel
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*.png")):
            key = str(p.resolve())
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return out


def classify_visual_asset(path: Path) -> dict[str, Any]:
    """Detect native PNG vs disguised H7/H7s — never double-wrap."""
    if not path.is_file():
        return {"ok": False, "storage": "missing", "path": str(path)}
    try:
        blob = path.read_bytes()
    except OSError as exc:
        return {"ok": False, "storage": "unreadable", "path": str(path), "error": str(exc)[:120]}

    fmt: str | None = None
    if len(blob) >= 4:
        if blob[:4] == H7S_MAGIC:
            fmt = "h7s/1"
        elif blob[:4] == H7_MAGIC:
            fmt = "h7/7"
        elif blob[:4] == H7E_MAGIC:
            fmt = "h7e/1"
    if fmt is None:
        h7 = _h7_family()
        if h7 and hasattr(h7, "classify_hostess7_blob"):
            cls = h7.classify_hostess7_blob(blob)
            if cls.get("is_container"):
                fmt = str(cls.get("format") or "hostess7")
    if fmt:
        props: dict[str, Any] = {}
        if fmt == "h7s/1":
            h7s = _h7s_mod()
            if h7s and hasattr(h7s, "read_properties"):
                try:
                    props = h7s.read_properties(blob)
                except Exception:
                    props = {}
        elif fmt == "h7/7":
            h7 = _h7_family()
            if h7 and hasattr(h7, "read_properties"):
                try:
                    props = h7.read_properties(blob)
                except Exception:
                    props = {}
        face_ext = str(props.get("face_extension") or props.get("original_extension") or path.suffix)
        return {
            "ok": True,
            "storage": "disguised_hostess7",
            "true_format": fmt,
            "path": str(path),
            "bytes": len(blob),
            "face_extension": face_ext,
            "face_format_id": props.get("face_format_id"),
            "already_wrapped": True,
            "can_adopt": False,
            "skip_reason": f"already_{fmt.replace('/', '_')}",
            "properties": props,
        }

    if blob.startswith(PNG_MAGIC):
        return {
            "ok": True,
            "storage": "native_png",
            "true_format": "native",
            "path": str(path),
            "bytes": len(blob),
            "already_wrapped": False,
            "can_adopt": True,
        }

    return {
        "ok": True,
        "storage": "unknown",
        "true_format": "unknown",
        "path": str(path),
        "bytes": len(blob),
        "magic_hex": blob[:4].hex() if len(blob) >= 4 else "",
        "already_wrapped": False,
        "can_adopt": False,
        "skip_reason": "not_png_or_hostess7",
    }


def can_adopt_visual(path: Path) -> dict[str, Any]:
    cls = classify_visual_asset(path)
    if not cls.get("ok"):
        return {**cls, "can_adopt": False}
    if cls.get("already_wrapped"):
        return {
            **cls,
            "can_adopt": False,
            "reason": cls.get("skip_reason") or "already_disguised_h7",
            "statement": "File is already a Hostess7 container — never double-wrap.",
        }
    if cls.get("storage") != "native_png":
        return {**cls, "can_adopt": False, "reason": cls.get("skip_reason") or "not_native_png"}
    adopt = _h7s_adopt()
    if adopt and hasattr(adopt, "is_kernel_boot_artifact") and adopt.is_kernel_boot_artifact(path):
        return {**cls, "can_adopt": False, "reason": "kernel_boot_excluded"}
    return {
        **cls,
        "can_adopt": True,
        "target_format": "h7s/1",
        "in_place": True,
        "extension_preserved": path.suffix,
        "statement": "Native PNG → in-place H7s/1 — speedup lane, PNG face, same URL.",
    }


def adopt_visual(path: Path, *, apply: bool = False) -> dict[str, Any]:
    gate = can_adopt_visual(path)
    if not gate.get("can_adopt"):
        return {"ok": True, "applied": False, **gate}

    h7s = _h7s_mod()
    if not h7s:
        return {"ok": False, "applied": False, "error": "h7s_module_missing", "path": str(path)}

    if not apply:
        before = path.stat().st_size
        return {
            "ok": True,
            "dry_run": True,
            "applied": False,
            "path": str(path),
            "bytes_before": before,
            "target_format": "h7s/1",
            "in_place": True,
        }

    try:
        out = h7s.pack_any_file(path, path)
        if out.get("skipped"):
            return {
                "ok": True,
                "applied": False,
                "path": str(path),
                "reason": out.get("skipped"),
                "guard": out.get("guard"),
            }
        after = path.stat().st_size
        verify = classify_visual_asset(path)
        row = {
            "ok": True,
            "applied": True,
            "path": str(path),
            "bytes_before": gate.get("bytes"),
            "bytes_after": after,
            "smaller": after < int(gate.get("bytes") or after),
            "target_format": "h7s/1",
            "in_place": True,
            "verify": verify,
            **{k: v for k, v in out.items() if k not in ("ok",)},
        }
        reg = _load(REGISTRY, {"schema": "field-h7-visual-adopt/v1", "entries": {}})
        reg.setdefault("entries", {})
        try:
            rel = str(path.relative_to(INSTALL))
        except ValueError:
            rel = str(path)
        reg["entries"][rel] = {
            "adopted_at": _now(),
            "bytes_before": gate.get("bytes"),
            "bytes_after": after,
            "true_format": "h7s/1",
        }
        reg["updated"] = _now()
        _save(REGISTRY, reg)
        return row
    except Exception as exc:
        return {"ok": False, "applied": False, "path": str(path), "error": str(exc)[:200]}


def audit_visuals() -> dict[str, Any]:
    paths = visual_png_paths()
    rows: list[dict[str, Any]] = []
    counts = {"native_png": 0, "disguised_hostess7": 0, "missing": 0, "other": 0}
    for p in paths:
        cls = classify_visual_asset(p)
        storage = cls.get("storage") or "other"
        if storage == "native_png":
            counts["native_png"] += 1
        elif storage == "disguised_hostess7":
            counts["disguised_hostess7"] += 1
        else:
            counts["other"] += 1
        try:
            rel = str(p.relative_to(INSTALL))
        except ValueError:
            rel = str(p)
        rows.append({
            "path": rel,
            "storage": storage,
            "true_format": cls.get("true_format"),
            "bytes": cls.get("bytes"),
            "can_adopt": bool(cls.get("can_adopt")),
            "skip_reason": cls.get("skip_reason"),
            "face_format_id": cls.get("face_format_id"),
        })

    rep = {
        "schema": "field-h7-visual-adopt-audit/v1",
        "ok": True,
        "updated": _now(),
        "motto": "H7s/1 for hot-read visuals — skip disguised H7; never double-wrap.",
        "target_format": "h7s/1",
        "png_count": len(paths),
        "counts": counts,
        "native_png_pending": counts["native_png"],
        "already_disguised": counts["disguised_hostess7"],
        "rows": rows,
    }
    _save(PANEL, rep)
    return rep


def adopt_all_visuals(*, apply: bool = False) -> dict[str, Any]:
    paths = visual_png_paths()
    results: list[dict[str, Any]] = []
    adopted = 0
    skipped = 0
    errors = 0
    saved_bytes = 0
    for p in paths:
        row = adopt_visual(p, apply=apply)
        results.append(row)
        if row.get("applied"):
            adopted += 1
            before = int(row.get("bytes_before") or 0)
            after = int(row.get("bytes_after") or before)
            if before > after:
                saved_bytes += before - after
        elif row.get("ok") and not row.get("applied"):
            skipped += 1
        elif not row.get("ok"):
            errors += 1

    return {
        "schema": "field-h7-visual-adopt-batch/v1",
        "ok": errors == 0,
        "apply": apply,
        "count": len(paths),
        "adopted": adopted,
        "skipped": skipped,
        "errors": errors,
        "saved_bytes": saved_bytes,
        "target_format": "h7s/1",
        "results": results[:80],
        "truncated": len(results) > 80,
        "updated": _now(),
    }


def explain_format() -> str:
    return "\n".join([
        "Visual assets: H7s/1 is the hot-read lane — in-place at .png, slice execute, smaller + faster.",
        "H7/7 is canonical cold storage (zlib). H7c is text/figures in Exploring books.",
        "Never double-wrap: classify checks H7S\\x01 and H7\\x07\\x01 magic before adopt.",
        "Already disguised files are skipped with skip_reason already_h7s_1 or already_h7_7.",
        "Commands: field-h7-visual-adopt.py audit | adopt [--apply] | classify <path>",
    ])


def main() -> int:
    args = sys.argv[1:]
    cmd = (args[0] if args else "audit").lower()
    apply = "--apply" in args

    if cmd == "audit":
        print(json.dumps(audit_visuals(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("adopt", "migrate", "pack"):
        print(json.dumps(adopt_all_visuals(apply=apply), ensure_ascii=False, indent=2))
        return 0
    if cmd == "classify" and len(args) >= 2:
        p = Path(args[1])
        if not p.is_absolute():
            p = INSTALL / args[1]
        print(json.dumps(classify_visual_asset(p), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("explain", "teach"):
        print(explain_format())
        return 0
    print(
        json.dumps(
            {
                "error": "usage",
                "cmds": ["audit", "adopt [--apply]", "classify <path>", "explain"],
                "doctrine": str(DOCTRINE),
            },
            ensure_ascii=False,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())