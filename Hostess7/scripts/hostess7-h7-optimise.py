#!/usr/bin/env python3
"""Hostess7 H7 optimise — compression + H7s speedups before GitHub push (2.0.7e)."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(ROOT.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "hostess7-h7-optimise-panel.json"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
H7S_MAGIC = b"H7S\x01"
H7_MAGIC = b"H7\x07\x01"
JSON_MIN_H7S = 4096
PNG_MIN_RECOMPRESS = 2048
# Browser + Pages fetch these as JSON.parse — keep plain UTF-8 on gh-pages.
BROWSER_JSON_PREFIXES = (
    "docs/api/",
    "docs/github-brain/",
    "docs/boot.json",
    "docs/status.json",
    "docs/manifest.json",
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_mod(name: str, path: Path) -> Any | None:
    if not path.is_file():
        return None
    key = f"h7opt_{name}_{path.stem}"
    spec = importlib.util.spec_from_file_location(key, path)
    if not spec or not spec.loader:
        return None
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _is_hostess7_container(data: bytes) -> str | None:
    if len(data) < 4:
        return None
    if data[:4] == H7S_MAGIC:
        return "h7s/1"
    if data[:4] == H7_MAGIC:
        return "h7/7"
    return None


def _scan_targets(base: Path) -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = {"json": [], "png": [], "jpg": []}
    if not base.is_dir():
        return out
    for p in base.rglob("*"):
        if not p.is_file() or ".git" in p.parts:
            continue
        suf = p.suffix.lower()
        if suf == ".json" and p.stat().st_size >= JSON_MIN_H7S:
            out["json"].append(p)
        elif suf == ".png" and p.stat().st_size >= PNG_MIN_RECOMPRESS:
            out["png"].append(p)
        elif suf in (".jpg", ".jpeg") and p.stat().st_size >= 8192:
            out["jpg"].append(p)
    return out


def _skip_browser_json(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT).as_posix()
    except ValueError:
        return False
    if rel in ("docs/boot.json", "docs/status.json", "docs/manifest.json"):
        return True
    return any(rel.startswith(p) for p in BROWSER_JSON_PREFIXES)


def _pages_publish_dirs() -> list[Path]:
    out: list[Path] = []
    for p in sorted(ROOT.glob(".pages-*")):
        if p.is_dir() and ".git" not in p.parts:
            out.append(p)
    return out


def _hostess7_trees() -> list[Path]:
    trees = [ROOT]
    for rel in (
        "data/combinatronic-visuals",
        "Queen/world/assets/combinatronic",
        "brain",
    ):
        p = ROOT / rel if rel == "brain" else INSTALL / rel
        if p.is_dir() and p not in trees:
            trees.append(p)
    trees.extend(_pages_publish_dirs())
    return trees


def optimise_json(path: Path, *, apply: bool) -> dict[str, Any]:
    before = path.stat().st_size
    data = path.read_bytes()
    fmt = _is_hostess7_container(data)
    if fmt:
        return {"ok": True, "path": str(path), "skipped": f"already_{fmt}", "bytes_before": before}
    h7s_py = INSTALL / "lib" / "field-h7s-format.py"
    h7s = _load_mod("h7s", h7s_py)
    if not h7s or not hasattr(h7s, "pack_any_file"):
        return {"ok": False, "path": str(path), "error": "h7s_missing"}
    if not apply:
        return {"ok": True, "dry_run": True, "path": str(path), "bytes_before": before, "target": "h7s/1"}
    try:
        out = h7s.pack_any_file(path, path)
        if out.get("skipped"):
            return {"ok": True, "path": str(path), "skipped": out.get("skipped"), "bytes_before": before}
        after = path.stat().st_size
        return {
            "ok": True,
            "path": str(path),
            "applied": True,
            "format": "h7s/1",
            "bytes_before": before,
            "bytes_after": after,
            "saved": max(0, before - after),
            "smaller": after < before,
        }
    except Exception as exc:
        return {"ok": False, "path": str(path), "error": str(exc)[:160]}


def optimise_png(path: Path, *, apply: bool) -> dict[str, Any]:
    before = path.stat().st_size
    data = path.read_bytes()
    fmt = _is_hostess7_container(data)
    if fmt:
        return {"ok": True, "path": str(path), "skipped": f"already_{fmt}", "bytes_before": before}
    if not data.startswith(PNG_MAGIC):
        return {"ok": False, "path": str(path), "error": "not_png", "bytes_before": before}
    fig = _load_mod("h7c_fig", INSTALL / "lib" / "field-h7c-figure-compress.py")
    if not fig or not hasattr(fig, "zlib_recompress_png"):
        return {"ok": False, "path": str(path), "error": "compress_module_missing"}
    new_data = fig.zlib_recompress_png(data)
    saved = before - len(new_data)
    if not apply:
        return {
            "ok": True,
            "dry_run": True,
            "path": str(path),
            "bytes_before": before,
            "bytes_after_est": len(new_data),
            "saved_est": max(0, saved),
            "method": "png_idat_recompress",
        }
    if saved > 0:
        path.write_bytes(new_data)
    return {
        "ok": True,
        "path": str(path),
        "applied": saved > 0,
        "method": "png_idat_recompress",
        "bytes_before": before,
        "bytes_after": len(new_data),
        "saved": max(0, saved),
        "smaller": saved > 0,
    }


def optimise_large_png_h7s(path: Path, *, apply: bool, min_bytes: int = 120_000) -> dict[str, Any]:
    """Hot-read lane — in-place H7s for large PNGs only (skips small icon overhead)."""
    before = path.stat().st_size
    if before < min_bytes:
        return optimise_png(path, apply=apply)
    data = path.read_bytes()
    if _is_hostess7_container(data):
        return {"ok": True, "path": str(path), "skipped": "already_wrapped", "bytes_before": before}
    vis = _load_mod("visual", INSTALL / "lib" / "field-h7-visual-adopt.py")
    if vis and hasattr(vis, "adopt_visual"):
        return vis.adopt_visual(path, apply=apply)
    return optimise_png(path, apply=apply)


def run_optimize(*, apply: bool = False, profile: str = "publish") -> dict[str, Any]:
    json_paths: list[Path] = []
    png_paths: list[Path] = []

    for rel in ("data", "brain"):
        d = ROOT / rel
        if d.is_dir():
            json_paths.extend(_scan_targets(d)["json"])
    for pages in _pages_publish_dirs():
        json_paths.extend(_scan_targets(pages)["json"])
    if profile not in ("publish", "hostess7"):
        for rel in ("docs/github-brain", "docs/api"):
            d = ROOT / rel
            if d.is_dir():
                json_paths.extend(_scan_targets(d)["json"])

    if profile in ("publish", "full", "hostess7"):
        for rel in ("docs/assets", "docs/queen/assets"):
            d = ROOT / rel
            if d.is_dir():
                png_paths.extend(_scan_targets(d)["png"])

    if profile in ("full", "field", "combinatronic"):
        for tree in _hostess7_trees():
            if tree == ROOT:
                continue
            png_paths.extend(_scan_targets(tree)["png"])

    json_paths = sorted(set(json_paths))
    png_paths = sorted(set(png_paths))

    results: list[dict[str, Any]] = []
    saved_total = 0
    adopted = 0
    skipped = 0

    for p in json_paths:
        if _skip_browser_json(p):
            skipped += 1
            results.append({"ok": True, "path": str(p), "skipped": "browser_json"})
            continue
        row = optimise_json(p, apply=apply)
        results.append(row)
        if row.get("applied"):
            adopted += 1
            saved_total += int(row.get("saved") or 0)
        elif row.get("skipped"):
            skipped += 1

    for p in png_paths:
        if profile == "publish":
            row = optimise_png(p, apply=apply)
        else:
            row = optimise_large_png_h7s(p, apply=apply)
        results.append(row)
        if row.get("applied") or row.get("smaller"):
            adopted += 1
            saved_total += int(row.get("saved") or row.get("saved_est") or 0)
        elif row.get("skipped"):
            skipped += 1

    rep = {
        "schema": "hostess7-h7-optimise/v1",
        "ok": True,
        "version": "2.0.7h",
        "updated": _now(),
        "apply": apply,
        "profile": profile,
        "json_count": len(json_paths),
        "png_count": len(png_paths),
        "adopted": adopted,
        "skipped": skipped,
        "saved_bytes": saved_total,
        "saved_mb": round(saved_total / (1024 * 1024), 2),
        "install_root": str(INSTALL),
        "hostess7_root": str(ROOT),
        "statement": "H7s for hot JSON · PNG IDAT recompress for Pages · H7s for large field visuals",
        "results_sample": results[:40],
        "truncated": len(results) > 40,
    }
    STATE.mkdir(parents=True, exist_ok=True)
    PANEL.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    return rep


def main() -> int:
    args = sys.argv[1:]
    apply = "--apply" in args
    profile = "publish"
    for a in args:
        if a.startswith("--profile="):
            profile = a.split("=", 1)[1]
    if "full" in args:
        profile = "full"
    if "combinatronic" in args:
        profile = "combinatronic"
    rep = run_optimize(apply=apply, profile=profile)
    print(json.dumps(rep, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())