#!/usr/bin/env pythong
"""High-level AmmoOS Image consolidation — merge libs, drop surface, amalgamate, lose sources."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SG = Path(os.environ.get("SG_ROOT", Path(__file__).resolve().parents[2]))
OVERLAY = Path(__file__).resolve().parents[1]
TREE = Path(os.environ.get("AMMOOS_GIMP_TREE", OVERLAY / "tree"))
PLAN = OVERLAY / "data" / "consolidation-plan.json"
MANIFEST = OVERLAY / "data" / "consolidation-manifest.json"

C_SRC = {".c", ".cc", ".cpp"}
SKIP_NAMES = {"meson.build", "meson_options.txt"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _rel(path: Path) -> str:
    return str(path.relative_to(TREE)).replace("\\", "/")


def _amalgamate_dir(target_dir: Path, bundle_name: str, min_files: int = 3) -> dict[str, Any]:
    """Concatenate small .c/.cc sources into one bundle; delete originals."""
    if not target_dir.is_dir():
        return {"ok": False, "error": "missing", "path": str(target_dir)}

    sources = sorted(
        p for p in target_dir.rglob("*")
        if p.is_file() and p.suffix in C_SRC and p.name != bundle_name
    )
    if len(sources) < min_files:
        return {"ok": True, "action": "skip_amalgam", "count": len(sources), "dir": _rel(target_dir)}

    parts = [
        f"/* AmmoOS amalgamation — {bundle_name} — g16 field_opt unity bundle */\n",
        "#define FIELD_AMMOOS_G16_OPT 1\n",
        "#define FIELD_AMMOOS_UNITY 1\n",
    ]
    included: list[str] = []
    for src in sources:
        rel = src.relative_to(target_dir)
        parts.append(f'\n/* --- begin {_rel(src)} --- */\n')
        try:
            body = src.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        parts.append(body)
        parts.append(f"\n/* --- end {_rel(src)} --- */\n")
        included.append(_rel(src))
        src.unlink()

    bundle = target_dir / bundle_name
    bundle.write_text("".join(parts), encoding="utf-8", errors="replace")
    return {
        "ok": True,
        "action": "amalgamated",
        "bundle": _rel(bundle),
        "merged": included,
        "count": len(included),
    }


def _move_tree(src: Path, dst: Path) -> list[str]:
    moved: list[str] = []
    if not src.is_dir():
        return moved
    dst.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.iterdir()):
        target = dst / item.name
        if target.exists():
            if item.is_dir():
                moved.extend(_move_tree(item, target))
                try:
                    item.rmdir()
                except OSError:
                    pass
            else:
                stem, suf = item.stem, item.suffix
                n = 1
                while target.exists():
                    target = dst / f"{stem}_{n}{suf}"
                    n += 1
                shutil.move(str(item), str(target))
                moved.append(_rel(target))
        else:
            shutil.move(str(item), str(target))
            moved.append(_rel(target))
    try:
        src.rmdir()
    except OSError:
        pass
    return moved


def _drop_dirs(names: list[str]) -> list[str]:
    dropped: list[str] = []
    for name in names:
        path = TREE / name
        if path.is_dir():
            shutil.rmtree(path)
            dropped.append(name)
    return dropped


def _trim_po(keep: list[str]) -> dict[str, Any]:
    po = TREE / "po"
    if not po.is_dir():
        return {"ok": False, "error": "no_po"}
    removed = 0
    for f in list(po.iterdir()):
        if f.name in keep or f.name in SKIP_NAMES:
            continue
        if f.suffix == ".po" or f.name.endswith(".po"):
            f.unlink()
            removed += 1
    ling = po / "LINGUAS"
    if ling.is_file():
        ling.write_text("en_GB\n", encoding="utf-8")
    return {"ok": True, "po_removed": removed, "kept": keep}


def _merge_plugins(plan: dict[str, Any]) -> dict[str, Any]:
    plug_root = TREE / "plug-ins"
    if not plug_root.is_dir():
        return {"ok": False, "error": "no_plugins"}

    keep = set(plan.get("plugins_keep") or [])
    drop = set(plan.get("plugins_drop") or [])
    merge_map: dict[str, list[str]] = plan.get("plugins_merge_into") or {}
    merge_targets = {Path(t).name for t in merge_map}
    keep |= merge_targets
    stats = {"dropped": [], "merged": {}, "kept": list(keep)}

    for name in drop:
        p = plug_root / name
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            stats["dropped"].append(name)

    for target, sources in merge_map.items():
        tgt = TREE / target
        tgt.mkdir(parents=True, exist_ok=True)
        moved: list[str] = []
        for src_name in sources:
            src = plug_root / src_name
            if not src.exists():
                continue
            moved.extend(_move_tree(src, tgt / src_name))
            stats["dropped"].append(src_name)
        stats["merged"][target] = moved

    for item in list(plug_root.iterdir()):
        if item.name in ("meson.build", "common") or item.name in keep:
            continue
        if item.name in stats["dropped"]:
            continue
        if item.name.endswith(".py"):
            item.unlink()
            stats["dropped"].append(item.name)
            continue
        if item.is_dir():
            shutil.rmtree(item)
            stats["dropped"].append(item.name)

    for target in merge_map:
        tgt = TREE / target
        if tgt.is_dir():
            am = _amalgamate_dir(tgt, "field-unity-plugins.c", min_files=2)
            if am.get("action") == "amalgamated":
                stats.setdefault("amalgamated", []).append(am)
    return {"ok": True, **stats}


def _merge_libs(plan: dict[str, Any]) -> dict[str, Any]:
    merge_libs: dict[str, list[str]] = plan.get("merge_libs") or {}
    amalg_min = int(plan.get("amalgamate_min_files") or 3)
    result: dict[str, Any] = {"merged": {}, "amalgamated": [], "removed_libs": []}

    for target, sources in merge_libs.items():
        tgt = TREE / target
        tgt.mkdir(parents=True, exist_ok=True)
        all_moved: list[str] = []
        for lib in sources:
            src = TREE / lib
            if not src.is_dir():
                continue
            sub = tgt / lib.replace("libgimp", "field").replace("lib", "field")
            all_moved.extend(_move_tree(src, sub))
            shutil.rmtree(src, ignore_errors=True)
            result["removed_libs"].append(lib)
        result["merged"][target] = all_moved

        # Amalgamate each subfolder under target
        for sub in sorted(tgt.iterdir()):
            if not sub.is_dir():
                continue
            bundle = f"field-unity-{sub.name}.c"
            am = _amalgamate_dir(sub, bundle, min_files=amalg_min)
            if am.get("action") == "amalgamated":
                result["amalgamated"].append(am)

    # Write libammoos meson stub
    meson = tgt if (tgt := TREE / "libammoos") else None
    if meson and meson.is_dir():
        _write_libammoos_meson(meson, result.get("amalgamated") or [])

    return result


def _write_libammoos_meson(libammoos: Path, amalgamated: list[dict[str, Any]]) -> None:
    bundles: list[str] = []
    for sub in sorted(libammoos.iterdir()):
        if not sub.is_dir():
            continue
        for c in sorted(sub.glob("field-unity-*.c")):
            bundles.append(f"  '{_rel(c)}',")
    meson_path = libammoos / "meson.build"
    content = (
        "# AmmoOS Image — consolidated libammoos (g16 field_opt)\n"
        "libammoos_sources = files(\n"
        + "\n".join(bundles)
        + "\n)\n\n"
        "libammoos_lib = static_library('ammoos-field',\n"
        "  libammoos_sources,\n"
        "  include_directories: include_directories('.'),\n"
        "  c_args: ['-DFIELD_AMMOOS_G16_OPT=1', '-DFIELD_AMMOOS_OS=1'],\n"
        "  install: false,\n"
        ")\n"
    )
    meson_path.write_text(content, encoding="utf-8")


def _patch_root_meson(plan: dict[str, Any]) -> list[str]:
    meson = TREE / "meson.build"
    if not meson.is_file():
        return []
    text = meson.read_text(encoding="utf-8", errors="replace")
    patches: list[str] = []

    for drop in plan.get("drop_dirs") or []:
        pat = re.compile(rf"^subdir\('{re.escape(drop)}'\)\s*$", re.M)
        if pat.search(text):
            text = pat.sub(f"# consolidated drop: {drop}", text)
            patches.append(f"drop_subdir:{drop}")

    for lib in (plan.get("merge_libs") or {}).values():
        for src_lib in lib:
            pat = re.compile(rf"^subdir\('{re.escape(src_lib)}'\)\s*$", re.M)
            if pat.search(text):
                text = pat.sub(f"# merged into libammoos: {src_lib}", text)
                patches.append(f"merge_subdir:{src_lib}")

    if "subdir('libammoos')" not in text:
        anchor = "subdir('app')"
        if anchor in text:
            text = text.replace(anchor, "subdir('libammoos')\n" + anchor, 1)
            patches.append("add:libammoos")

    for drop in plan.get("drop_dirs") or []:
        if drop.startswith("po-"):
            pat = re.compile(rf"^subdir\('{re.escape(drop)}'\)\s*$", re.M)
            text = pat.sub(f"# dropped i18n: {drop}", text)

    meson.write_text(text, encoding="utf-8", errors="replace")
    return patches


def _consolidate_app(plan: dict[str, Any]) -> dict[str, Any]:
    app = TREE / "app"
    if not app.is_dir():
        return {"ok": False}
    cfg = plan.get("app_consolidate") or {}
    dialogs_dst = TREE / cfg.get("dialogs_into", "app/field-dialogs")
    widgets_dst = TREE / cfg.get("widgets_into", "app/field-widgets")
    stats: dict[str, Any] = {"dialogs_merged": 0, "widgets_merged": 0}

    for sub, dst in (("dialogs", dialogs_dst), ("widgets", widgets_dst)):
        src = app / sub
        if not src.is_dir():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        # Merge only shallow .c files into unity per subfolder category
        categories: dict[str, list[Path]] = {}
        for f in sorted(src.rglob("*.c")):
            cat = f.parent.name if f.parent != src else "root"
            categories.setdefault(cat, []).append(f)
        for cat, files in categories.items():
            if len(files) < 4:
                continue
            cat_dir = dst / sub / cat
            cat_dir.mkdir(parents=True, exist_ok=True)
            bundle = cat_dir / f"field-{sub}-{cat}-unity.c"
            parts = [f"/* AmmoOS app {sub}/{cat} unity — g16 field_opt */\n"]
            merged_names: list[str] = []
            for f in files:
                parts.append(f"\n/* --- {f.name} --- */\n")
                parts.append(f.read_text(encoding="utf-8", errors="replace"))
                merged_names.append(_rel(f))
                f.unlink()
            bundle.write_text("".join(parts), encoding="utf-8", errors="replace")
            stats[f"{sub}_merged"] += len(merged_names)
    return {"ok": True, **stats}


def consolidate() -> dict[str, Any]:
    if not TREE.is_dir():
        return {"ok": False, "error": "tree_missing", "path": str(TREE)}

    plan = _load(PLAN, {})
    before = sum(1 for _ in TREE.rglob("*") if _.is_file())

    dropped = _drop_dirs(plan.get("drop_dirs") or [])
    po = _trim_po(plan.get("drop_po_keep") or ["en_GB.po"])
    plugins = _merge_plugins(plan)
    libs = _merge_libs(plan)
    app = _consolidate_app(plan)
    meson_patches = _patch_root_meson(plan)

    after = sum(1 for _ in TREE.rglob("*") if _.is_file())
    doc = {
        "schema": "ammoos-gimp-consolidation-manifest/v1",
        "ts": _now(),
        "ok": True,
        "tree": str(TREE),
        "files_before": before,
        "files_after": after,
        "files_removed": before - after,
        "dropped_dirs": dropped,
        "po": po,
        "plugins": plugins,
        "libs": libs,
        "app": app,
        "meson_patches": meson_patches,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "run").strip().lower()
    if cmd in ("run", "consolidate", "all"):
        print(json.dumps(consolidate(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "status":
        print(json.dumps(_load(MANIFEST, {"ok": False}), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-gimp-consolidate.py [run|status]"}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())