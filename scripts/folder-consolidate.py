#!/usr/bin/env python3
"""Audit folders, harvest useful code, drop outside trees — tight NewLatest structure."""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def _root() -> Path:
    return Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1])).resolve()


def _load_manifest(root: Path) -> dict:
    p = root / "data" / "folder-consolidation-manifest.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _log(msg: str, *, apply: bool) -> None:
    prefix = "[consolidate]" if apply else "[dry-run]"
    print(f"{prefix} {msg}")


def _harvest(src: Path, dst: Path, *, if_missing_only: bool, apply: bool) -> bool:
    if not src.is_file():
        return False
    if if_missing_only and dst.is_file():
        _log(f"skip harvest {src.name} -> {dst} (dest exists)", apply=apply)
        return False
    _log(f"harvest {src} -> {dst}", apply=apply)
    if apply:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return True


def _drop(path: Path, apply: bool) -> None:
    if not path.exists():
        _log(f"skip drop {path} (absent)", apply=apply)
        return
    _log(f"drop {path}", apply=apply)
    if apply:
        if path.is_symlink() or path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)


def _archive_dir(src: Path, dst: Path, apply: bool) -> None:
    if not src.is_dir():
        _log(f"skip archive {src} (not a directory)", apply=apply)
        return
    _log(f"archive {src} -> {dst}", apply=apply)
    if apply:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(str(src), str(dst))


def _move_file(src: Path, dst: Path, apply: bool) -> None:
    _log(f"move {src.name} -> {dst}", apply=apply)
    if apply:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            dst.unlink()
        shutil.move(str(src), str(dst))


def _glob_matches(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def consume_drop(root: Path, manifest: dict, apply: bool) -> int:
    n = 0
    for item in manifest.get("consume_drop", []):
        folder = root / item["path"]
        if not folder.exists():
            _log(f"skip consume_drop {item['id']} ({item['path']} absent)", apply=apply)
            continue
        for h in item.get("harvest", []):
            src = folder / h["src"]
            dst = root / h["dst"]
            if _harvest(src, dst, if_missing_only=bool(h.get("if_missing_only")), apply=apply):
                n += 1
        _drop(folder, apply)
        n += 1
    return n


def drop_sg_stubs(root: Path, manifest: dict, apply: bool) -> int:
    n = 0
    for item in manifest.get("drop_sg_stubs", []):
        p = (root / item["path"]).resolve()
        if p.exists() and p != root:
            _drop(p, apply)
            n += 1
    return n


def drop_publish_clones(root: Path, manifest: dict, apply: bool) -> int:
    n = 0
    globs = manifest.get("drop_publish_clones", {}).get("glob", [])
    for pat in globs:
        for p in sorted(root.glob(pat)):
            if p.is_dir():
                _drop(p, apply)
                n += 1
    return n


def archive_heavy(root: Path, manifest: dict, apply: bool) -> int:
    n = 0
    for item in manifest.get("archive", []):
        src = root / item["path"]
        dst = root / item["archive_to"]
        if src.is_dir():
            _archive_dir(src, dst, apply)
            n += 1
    return n


def relocate_clutter(root: Path, manifest: dict, apply: bool) -> int:
    n = 0
    rel = manifest.get("relocate", {})

    rel_md = rel.get("releases_md", {})
    if rel_md:
        dest = root / rel_md.get("to", "docs/releases")
        for p in sorted(root.glob(rel_md.get("glob", "RELEASE-*.md"))):
            if p.is_file() and p.parent == root:
                _move_file(p, dest / p.name, apply)
                n += 1

    seeds = rel.get("panel_seeds", {})
    if seeds:
        dest = root / seeds.get("to", "data/panel-seeds")
        patterns = seeds.get("glob", [])
        keep = set(seeds.get("keep_symlinks", []))
        for p in sorted(root.iterdir()):
            if not p.is_file():
                continue
            if not _glob_matches(p.name, patterns):
                continue
            target = dest / p.name
            _move_file(p, target, apply)
            if p.name in keep and apply:
                root.joinpath(p.name).symlink_to(Path("data/panel-seeds") / p.name)
                _log(f"symlink {p.name} -> data/panel-seeds/{p.name}", apply=apply)
            n += 1
    return n


def update_field_stack_manifest(root: Path, manifest: dict, apply: bool) -> None:
    cfg = manifest.get("manifest_updates", {})
    path = root / cfg.get("field_stack_manifest", "data/field-stack-manifest.json")
    if not path.is_file():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    layers = doc.setdefault("layers", {})
    for lid in cfg.get("remove_layers", []):
        if lid in layers:
            _log(f"remove layer {lid} from field-stack-manifest", apply=apply)
            if apply:
                del layers[lid]
    eye_root = cfg.get("final_eye_root", "NewLatest/Final_Eye")
    layers["final_eye"] = {
        "root": eye_root,
        "version": _read_version(root / "Final_Eye"),
        "codename": "heaven-hell-ops",
        "role": "Assist tenant — vision offense, entity weapons, IRTN mesh",
        "port": 9479,
    }
    znet = layers.get("znetwork", {})
    znet.pop("integrated_pointer", None)
    znet["outside_lab_pointer"] = "ZNetwork/data/outside-lab-pointer.json"
    layers["znetwork"] = znet
    doc["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _log(f"update {path.relative_to(root)}", apply=apply)
    if apply:
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def update_sg_canonical(root: Path, manifest: dict, apply: bool) -> None:
    cfg = manifest.get("manifest_updates", {})
    path = root / cfg.get("sg_canonical", "data/sg-canonical.json")
    if not path.is_file():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    stack = doc.setdefault("stack", {})
    stack["final_eye"] = "NewLatest/Final_Eye"
    for key in ("zocr", "zocr_legacy", "znewocr"):
        stack.pop(key, None)
    doc.setdefault("retired", {}).update(manifest.get("retired", {}))
    sense = doc.setdefault("sense_package", {})
    sense["motto"] = "Eye · Ear · Final_Eye · Redata · Hostess7 — melded and protected; brain witnessed read-only"
    doc["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _log(f"update {path.relative_to(root)}", apply=apply)
    if apply:
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def update_wire_stack(root: Path, manifest: dict, apply: bool) -> None:
    cfg = manifest.get("manifest_updates", {})
    path = root / cfg.get("wire_stack", "scripts/wire-stack.sh")
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    out: list[str] = []
    seen: set[str] = set()
    skip_names = {"ZOCR", "ZNEWOCR", "znetwork"}
    for line in lines:
        stripped = line.strip()
        if stripped in skip_names or (stripped.endswith("ZOCR") and "  " in line):
            for name in skip_names:
                if name in line and line.strip() == name:
                    _log(f"remove {name} from wire-stack.sh", apply=apply)
                    break
            else:
                out.append(line)
            continue
        if stripped in ("Final_Eye",) and stripped in seen:
            _log("remove duplicate Final_Eye from wire-stack.sh", apply=apply)
            continue
        if stripped in ("Final_Eye", "Final_Ear", "Final_Mouth", "ZOCR", "ZNEWOCR"):
            if stripped in seen:
                continue
            seen.add(stripped)
        out.append(line)
    new_text = "\n".join(out) + ("\n" if text.endswith("\n") else "")
    if new_text != text:
        _log(f"update {path.relative_to(root)}", apply=apply)
        if apply:
            path.write_text(new_text, encoding="utf-8")


def _read_version(eye: Path) -> str:
    vf = eye / "VERSION"
    return vf.read_text(encoding="utf-8").strip() if vf.is_file() else "1.3.0"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Execute changes (default: dry-run)")
    ap.add_argument("--skip-archive", action="store_true", help="Skip moving dist/ to _archive/")
    args = ap.parse_args()
    apply = args.apply
    root = _root()
    manifest = _load_manifest(root)

    _log(f"root={root}", apply=apply)
    total = 0
    total += consume_drop(root, manifest, apply)
    total += drop_sg_stubs(root, manifest, apply)
    total += drop_publish_clones(root, manifest, apply)
    if not args.skip_archive:
        total += archive_heavy(root, manifest, apply)
    total += relocate_clutter(root, manifest, apply)
    update_field_stack_manifest(root, manifest, apply)
    update_sg_canonical(root, manifest, apply)
    update_wire_stack(root, manifest, apply)
    _log(f"done actions={total}", apply=apply)
    if not apply:
        _log("re-run with --apply to execute", apply=apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())