#!/usr/bin/env pythong
"""Rewrite upstream GIMP tree → AmmoOS Image 1.0 field research + g16 optimization overlay."""
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
UPSTREAM = Path(os.environ.get("GIMP_ROOT", SG / "GIMP"))
TREE = Path(os.environ.get("AMMOOS_GIMP_TREE", OVERLAY / "tree"))
DOCTRINE = OVERLAY / "data" / "field-gimp-doctrine.json"
GATED = OVERLAY / "data" / "rtx-gated-content.json"
MANIFEST = OVERLAY / "data" / "rewrite-manifest.json"

TEXT_EXTS = {
    ".c", ".cc", ".cpp", ".h", ".hh", ".hpp", ".m", ".mm",
    ".py", ".sh", ".bash", ".meson", ".build", ".in", ".xml", ".desktop",
    ".json", ".md", ".txt", ".po", ".pot", ".xsl", ".css", ".js", ".html",
    ".yml", ".yaml", ".toml", ".doap", ".ini", ".cfg",
}

SKIP_DIRS = {
    ".git", "build", "subprojects", ".cache", "__pycache__", "node_modules",
}

FIELD_HEADER_C = """/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
"""

FIELD_HEADER_OTHER = "# AmmoOS Image 1.0 — field research rewrite (G16 field_opt)\n"

BRAND_REPLACEMENTS = [
    (re.compile(r"project\('gimp'"), "project('ammoos-image'"),
    (re.compile(r"GNU Image Manipulation Program"), "AmmoOS Field Image Research"),
    (re.compile(r"GIMP —"), "AmmoOS Image —"),
    (re.compile(r"\bGIMP\b"), "AmmoOS Image"),
    (re.compile(r"\bgimp\b"), "ammoos"),
    (re.compile(r"version:\s*'3\.3\.1'"), "version: '1.0.0'"),
    (re.compile(r"prettyname\s*=\s*'GIMP'"), "prettyname = 'AmmoOS Image'"),
    (re.compile(r"full_name\s*=\s*'GNU Image Manipulation Program'"), "full_name  = 'AmmoOS Field Image Research'"),
    (re.compile(r"org\.gimp\.GIMP"), "org.ammoos.Image"),
    (re.compile(r"Name=GNU Image Manipulation Program"), "Name=AmmoOS Image"),
    (re.compile(r"GenericName=Image Editor"), "GenericName=AmmoOS Field Image Editor"),
    (re.compile(r"Keywords=GIMP;"), "Keywords=AmmoOS;AmmoOS Image;"),
    (re.compile(r"Icon=gimp"), "Icon=ammoos-image"),
    (re.compile(r"TryExec=gimp-"), "TryExec=ammoos-image-"),
    (re.compile(r"StartupWMClass=@GIMP_DESKTOP_NAME@"), "StartupWMClass=AmmoOS Image"),
]

G16_CXX_ATTR = "\n#if defined(__GNUC__) && defined(FIELD_AMMOOS_G16_OPT)\n__attribute__((hot, optimize(\"O3\")))\n#endif\n"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _is_gated_path(rel: str, gated_paths: list[str]) -> bool:
    norm = rel.replace("\\", "/")
    return any(norm.startswith(g) or g in norm for g in gated_paths)


def _should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def _rewrite_text(content: str, rel: str, gated_paths: list[str]) -> str:
    out = content
    for pat, repl in BRAND_REPLACEMENTS:
        out = pat.sub(repl, out)
    if _is_gated_path(rel, gated_paths):
        guard = (
            "\n/* FIELD_AMMOOS_RTX_GATED — requires RTX autodetect permit; "
            "CPU fallback via field_opt when gated */\n"
            "#ifndef FIELD_AMMOOS_RTX_PERMIT\n"
            "#define FIELD_AMMOOS_RTX_GATED 1\n"
            "#endif\n"
        )
        if rel.endswith((".c", ".cc", ".cpp", ".h", ".hh")) and "FIELD_AMMOOS_RTX_GATED" not in out:
            out = guard + out
    if "FIELD_AMMOOS_G16_OPT" not in out and rel.endswith((".c", ".cc", ".cpp")):
        if "gegl" in rel.lower() or "operation" in rel.lower() or "paint" in rel.lower():
            out = "#define FIELD_AMMOOS_G16_OPT 1\n" + out
    return out


def _inject_header(content: str, rel: str) -> str:
    if rel.endswith((".c", ".cc", ".cpp", ".h", ".hh", ".hpp")):
        if "AmmoOS Image — field research rewrite" in content[:400]:
            return content
        return FIELD_HEADER_C + content
    if rel.endswith((".py", ".sh", ".meson", ".build")):
        if content.startswith("# AmmoOS Image"):
            return content
        return FIELD_HEADER_OTHER + content
    return content


def sync_tree(*, force: bool = False) -> dict[str, Any]:
    if not UPSTREAM.is_dir():
        return {"ok": False, "error": "upstream_missing", "path": str(UPSTREAM)}
    if TREE.exists() and not force:
        return {"ok": True, "action": "skip_sync", "tree": str(TREE)}
    if TREE.exists():
        shutil.rmtree(TREE)
    shutil.copytree(
        UPSTREAM,
        TREE,
        ignore=shutil.ignore_patterns(".git", "build", "subprojects"),
        dirs_exist_ok=False,
    )
    return {"ok": True, "action": "synced", "tree": str(TREE)}


def rewrite_consolidated() -> dict[str, Any]:
    """Re-apply field rewrite after consolidation (in-place on tree)."""
    return rewrite_all(in_place=True)


def rewrite_all(*, in_place: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    gated_doc = _load(GATED, {})
    gated_paths = gated_doc.get("gated_paths") or []

    if not TREE.is_dir() and not in_place:
        sync = sync_tree(force=True)
        if not sync.get("ok"):
            return sync
    if not TREE.is_dir():
        return {"ok": False, "error": "tree_missing", "path": str(TREE)}

    stats = {"rewritten": 0, "skipped_binary": 0, "skipped_dir": 0, "errors": 0, "gated": 0}
    files_out: list[dict[str, str]] = []

    for path in TREE.rglob("*"):
        if path.is_dir():
            continue
        if _should_skip(path.relative_to(TREE)):
            stats["skipped_dir"] += 1
            continue
        rel = str(path.relative_to(TREE))
        suffix = path.suffix.lower()
        if suffix not in TEXT_EXTS and suffix not in (".in.in",):
            try:
                raw = path.read_bytes()[:256]
                if b"\0" in raw:
                    stats["skipped_binary"] += 1
                    continue
            except OSError:
                stats["errors"] += 1
                continue

        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8", errors="replace")
        except OSError:
            stats["errors"] += 1
            continue

        new_text = _rewrite_text(text, rel, gated_paths)
        new_text = _inject_header(new_text, rel)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8", errors="replace")
            stats["rewritten"] += 1
            entry = {"path": rel, "kind": "rewrite"}
            if _is_gated_path(rel, gated_paths):
                stats["gated"] += 1
                entry["rtx_gated"] = True
            files_out.append(entry)

    # Meson overlay snippet in tree
    overlay_meson = TREE / "ammoos-field-overlay.meson"
    overlay_meson.write_text(
        "# AmmoOS field overlay\n"
        "add_project_arguments('-DFIELD_AMMOOS_G16_OPT=1', language: 'c')\n"
        "add_project_arguments('-DFIELD_AMMOOS_G16_OPT=1', language: 'cpp')\n"
        "add_project_arguments('-DFIELD_AMMOOS_OS=1', language: 'c')\n"
        "add_project_arguments('-DFIELD_AMMOOS_OS=1', language: 'cpp')\n",
        encoding="utf-8",
    )

    manifest = {
        "schema": "ammoos-gimp-rewrite-manifest/v1",
        "ts": _now(),
        "ok": True,
        "product": doctrine.get("product") or "AmmoOS Image",
        "version": doctrine.get("version") or "1.0.0",
        "os_brand": doctrine.get("os_brand") or "AmmoOS",
        "upstream": str(UPSTREAM),
        "tree": str(TREE),
        "stats": stats,
        "files_sample": files_out[:200],
        "total_manifested": len(files_out),
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "rewrite").strip().lower()
    if cmd == "sync":
        print(json.dumps(sync_tree(force="--force" in sys.argv), ensure_ascii=False, indent=2))
        return 0
    if cmd == "pipeline":
        sync = sync_tree(force=True)
        if not sync.get("ok"):
            print(json.dumps(sync, ensure_ascii=False, indent=2))
            return 1
        import importlib.util
        cons = OVERLAY / "forge" / "field-gimp-consolidate.py"
        spec = importlib.util.spec_from_file_location("cons", cons)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cdoc = mod.consolidate()
        else:
            cdoc = {"ok": False, "error": "consolidate_missing"}
        rdoc = rewrite_all(in_place=True)
        print(json.dumps({"ok": True, "sync": sync, "consolidate": cdoc, "rewrite": rdoc}, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("rewrite", "all"):
        print(json.dumps(rewrite_all(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("rewrite2", "consolidated"):
        print(json.dumps(rewrite_all(in_place=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "status":
        print(json.dumps(_load(MANIFEST, {"ok": False, "error": "no_manifest"}), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-gimp-rewrite.py [sync|rewrite|status]"}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())