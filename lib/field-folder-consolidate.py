#!/usr/bin/env pythong
"""Folder consolidation + subfolder AmmoLang wiring — gut vestigial, merge useful, route AML."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
MANIFEST = INSTALL / "data" / "folder-consolidation-manifest.json"
ROUTES = INSTALL / "data" / "field-subfolder-ammolang-routes.json"
PANEL = STATE / "folder-consolidate-panel.json"
LEDGER = STATE / "folder-consolidate-ledger.jsonl"

AML_MARKER = "# AmmoLang subfolder route"
AML_SHIM_TEMPLATE = """{marker} — AML_BUILD=1 (default)
_aml_find_root() {{
  local d="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}}
if [[ "${{AML_BUILD:-1}}" != "0" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    exec bash "${{_AML_ROOT}}/lib/ammolang-run.sh" {task} "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _log(row: dict[str, Any]) -> None:
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _resolve(rel: str, *, sg_relative: bool = False) -> Path:
    p = Path(rel)
    if p.is_absolute():
        return p
    if rel.startswith("../") or sg_relative:
        name = rel[3:] if rel.startswith("../") else rel
        return SG / name
    return INSTALL / rel


def _harvest_item(src: Path, dst: Path, *, if_missing_only: bool = False) -> bool:
    if not src.is_file():
        return False
    if if_missing_only and dst.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    _log({"op": "harvest", "src": str(src), "dst": str(dst)})
    return True


def _drop_path(path: Path, *, dry: bool = False) -> bool:
    if not path.exists() and not path.is_symlink():
        return False
    resolved = path.resolve()
    if resolved == INSTALL.resolve() or INSTALL.resolve() in resolved.parents:
        if path.is_symlink():
            target = Path(os.readlink(path))
            if not target.is_absolute():
                target = (path.parent / target).resolve()
            if INSTALL.resolve() in target.parents or target == INSTALL.resolve():
                return False
        elif path.is_dir() and not path.is_symlink():
            try:
                if (path / "lib" / "ammolang-run.sh").is_file():
                    return False
            except OSError:
                pass
    if dry:
        _log({"op": "drop_dry", "path": str(path)})
        return True
    if path.is_symlink():
        path.unlink()
    elif path.is_file():
        path.unlink()
    else:

        def _on_rm_error(func, p, exc_info):  # type: ignore[no-untyped-def]
            try:
                os.chmod(p, 0o700)
                func(p)
            except OSError:
                pass

        shutil.rmtree(path, onexc=_on_rm_error)
    _log({"op": "drop", "path": str(path)})
    return True


def _archive_path(src: Path, archive_to: Path, *, dry: bool = False) -> bool:
    if not src.exists():
        return False
    dest = INSTALL / archive_to if not archive_to.is_absolute() else archive_to
    if dry:
        _log({"op": "archive_dry", "src": str(src), "dst": str(dest)})
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(src), str(dest))
    _log({"op": "archive", "src": str(src), "dst": str(dest)})
    return True


def consolidate(*, dry: bool = False) -> dict[str, Any]:
    doc = _load(MANIFEST)
    if not doc:
        return {"ok": False, "error": "manifest_missing"}

    harvested = dropped = archived = relocated = 0
    actions: list[dict[str, Any]] = []

    for item in doc.get("consume_drop") or []:
        rel = str(item.get("path") or "")
        base = _resolve(rel)
        for h in item.get("harvest") or []:
            src = base / str(h.get("src") or "")
            dst = _resolve(str(h.get("dst") or ""))
            if _harvest_item(src, dst, if_missing_only=bool(h.get("if_missing_only"))):
                harvested += 1
                actions.append({"harvest": str(src), "to": str(dst)})
        if base.exists() and _drop_path(base, dry=dry):
            dropped += 1
            actions.append({"drop": rel, "reason": item.get("reason")})

    for item in doc.get("drop_sg_stubs") or []:
        rel = str(item.get("path") or "")
        path = _resolve(rel, sg_relative=rel.startswith("../"))
        if (path.exists() or path.is_symlink()) and _drop_path(path, dry=dry):
            dropped += 1
            actions.append({"drop_sg": rel})

    drop_clones = doc.get("drop_publish_clones") or {}
    for pattern in drop_clones.get("glob") or []:
        for path in sorted(INSTALL.glob(pattern)):
            if path.is_dir() and _drop_path(path, dry=dry):
                dropped += 1
                actions.append({"drop_clone": str(path.relative_to(INSTALL))})

    for item in doc.get("archive") or []:
        rel = str(item.get("path") or "")
        arch = str(item.get("archive_to") or f"_archive/{rel}")
        src = _resolve(rel)
        if src.exists() and _archive_path(src, Path(arch), dry=dry):
            archived += 1
            actions.append({"archive": rel, "to": arch})

    extra_drops = ["=", "ZOCR", "ZNEWOCR"]
    for name in extra_drops:
        path = INSTALL / name
        if path.exists() and _drop_path(path, dry=dry):
            dropped += 1
            actions.append({"drop_extra": name})

    sg_stubs = [
        SG / "KILROY",
        SG / "data",
        SG / "compat",
        SG / "OBS-FieldVoiceFilter",
    ]
    for path in sg_stubs:
        if path.exists() and _drop_path(path, dry=dry):
            dropped += 1
            actions.append({"drop_sg_stub": str(path)})

    deploy = INSTALL / "GrokLab" / "deploy"
    if deploy.is_dir() and deploy.stat().st_size > 0:
        if _archive_path(deploy, Path("_archive/groklab-deploy"), dry=dry):
            archived += 1
            actions.append({"archive": "GrokLab/deploy", "to": "_archive/groklab-deploy"})

    relocate = doc.get("relocate") or {}
    for _key, rule in relocate.items():
        dest_dir = INSTALL / str(rule.get("to") or "")
        globs = rule.get("glob") or []
        if isinstance(globs, str):
            globs = [globs]
        from_dir = INSTALL if str(rule.get("from") or ".") == "." else _resolve(str(rule.get("from")))
        exclude = bool(rule.get("exclude_subdirs"))
        keep_links = set(rule.get("keep_symlinks") or [])
        for glob_pat in globs:
            for src in from_dir.glob(glob_pat):
                if not src.is_file():
                    continue
                if exclude and src.parent != from_dir:
                    continue
                if src.name in keep_links and src.is_symlink():
                    continue
                dst = dest_dir / src.name
                if dst.resolve() == src.resolve():
                    continue
                if dry:
                    actions.append({"relocate_dry": str(src), "to": str(dst)})
                    continue
                dest_dir.mkdir(parents=True, exist_ok=True)
                if dst.exists():
                    dst.unlink()
                shutil.move(str(src), str(dst))
                relocated += 1
                actions.append({"relocate": src.name, "to": str(dest_dir.relative_to(INSTALL))})

    _sync_manifests(doc)

    result = {
        "schema": "folder-consolidate/v1",
        "updated": _now(),
        "ok": True,
        "dry": dry,
        "harvested": harvested,
        "dropped": dropped,
        "archived": archived,
        "relocated": relocated,
        "actions": actions[-80:],
    }
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        PANEL.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return result


def _sync_manifests(doc: dict[str, Any]) -> None:
    updates = doc.get("manifest_updates") or {}
    stack_path = INSTALL / str(updates.get("field_stack_manifest") or "data/field-stack-manifest.json")
    canon_path = INSTALL / str(updates.get("sg_canonical") or "data/sg-canonical.json")
    layer_path = INSTALL / "data/field-stack-layer-doctrine.json"

    layer = _load(layer_path)
    if layer:
        order = [row.get("id") for row in layer.get("layers_bottom_up") or [] if row.get("id")]
        canon = _load(canon_path)
        if canon and order:
            canon["stack_layers"] = {
                **(canon.get("stack_layers") or {}),
                "order": order,
                "doctrine": "NewLatest/data/field-stack-layer-doctrine.json",
                "version": layer.get("version", "2.0.0"),
            }
            canon["motto"] = (
                "SG/NewLatest — KILROY PC core · AmmoOS+AMOURANTHRTX · Queen standalone — hardware no-break"
            )
            canon["updated"] = _now().split("T")[0]
            canon_path.write_text(json.dumps(canon, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    stack = _load(stack_path)
    if stack:
        remove = set(updates.get("remove_layers") or [])
        layers = stack.get("layers") or stack.get("components") or []
        if isinstance(layers, list):
            stack["layers"] = [x for x in layers if str(x.get("id", x)).lower() not in remove]
        stack["final_eye_root"] = updates.get("final_eye_root", str(INSTALL / "Final_Eye"))
        stack["updated"] = _now().split("T")[0]
        stack_path.write_text(json.dumps(stack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _inject_aml_shim(path: Path, task: str, *, dry: bool = False) -> bool:
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if AML_MARKER in text:
        return False
    lines = text.splitlines()
    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    shim = AML_SHIM_TEMPLATE.format(marker=AML_MARKER, task=task)
    new_text = "\n".join(lines[:insert_at] + [shim.rstrip(), ""] + lines[insert_at:])
    if not new_text.endswith("\n"):
        new_text += "\n"
    if dry:
        _log({"op": "wire_dry", "path": str(path), "task": task})
        return True
    path.write_text(new_text, encoding="utf-8")
    try:
        path.chmod(path.stat().st_mode | 0o111)
    except OSError:
        pass
    try:
        rel = str(path.resolve().relative_to(INSTALL.resolve()))
    except ValueError:
        rel = str(path)
    _log({"op": "wire", "path": rel, "task": task})
    return True


def wire_aml(*, dry: bool = False) -> dict[str, Any]:
    routes_doc = _load(ROUTES)
    wired: list[str] = []
    skipped: list[str] = []
    missing: list[str] = []

    for _folder, spec in (routes_doc.get("routes") or {}).items():
        task = str(spec.get("task") or spec.get("aml") or "")
        if not task:
            continue
        for rel in spec.get("entry_scripts") or []:
            path = INSTALL / rel
            if not path.is_file():
                missing.append(rel)
                continue
            if _inject_aml_shim(path, task, dry=dry):
                wired.append(rel)
            else:
                skipped.append(rel)

    core_scripts = [
        "scripts/ammoos-beta-pipeline.sh",
        "scripts/integrate-compiler-stack.sh",
        "scripts/nexus-g16-recompile.sh",
        "scripts/ammoos-ship-beta3.sh",
        "scripts/ammoos-update-inplace.sh",
        "scripts/aml.sh",
    ]
    core_tasks = {
        "scripts/ammoos-beta-pipeline.sh": "beta_pipeline",
        "scripts/integrate-compiler-stack.sh": "compiler_stack",
        "scripts/nexus-g16-recompile.sh": "g16_recompile",
        "scripts/ammoos-ship-beta3.sh": "ship",
        "scripts/ammoos-update-inplace.sh": "ammoos_update",
        "scripts/aml.sh": "tasks",
    }
    for rel, task in core_tasks.items():
        path = INSTALL / rel
        if path.is_file() and AML_MARKER not in path.read_text(encoding="utf-8", errors="replace"):
            if _inject_aml_shim(path, task, dry=dry):
                wired.append(rel)

    return {
        "schema": "folder-aml-wire/v1",
        "updated": _now(),
        "ok": True,
        "dry": dry,
        "wired": len(wired),
        "wired_paths": wired,
        "skipped": skipped,
        "missing": missing,
    }


def status() -> dict[str, Any]:
    doc = _load(MANIFEST)
    vestigial = []
    for item in doc.get("consume_drop") or []:
        p = _resolve(str(item.get("path") or ""))
        if p.exists():
            vestigial.append({"path": str(p.relative_to(INSTALL)), "id": item.get("id")})
    for pattern in (doc.get("drop_publish_clones") or {}).get("glob") or []:
        for p in INSTALL.glob(pattern):
            vestigial.append({"path": str(p.relative_to(INSTALL)), "id": "pages_clone"})
    for name in ("=", "ZOCR", "ZNEWOCR", "znetwork", "NewLatest"):
        p = INSTALL / name
        if p.exists():
            vestigial.append({"path": name, "id": "stub"})
    if (INSTALL / "dist").exists():
        vestigial.append({"path": "dist", "id": "archive_candidate"})
    if (INSTALL / "GrokLab" / "deploy").exists():
        vestigial.append({"path": "GrokLab/deploy", "id": "archive_candidate"})
    return {
        "schema": "folder-consolidate-status/v1",
        "updated": _now(),
        "vestigial_remaining": vestigial,
        "count": len(vestigial),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    dry = "--dry" in sys.argv or os.environ.get("AML_CONSOLIDATE_DRY") == "1"

    if cmd in ("consolidate", "gut", "merge"):
        doc = consolidate(dry=dry)
    elif cmd in ("wire", "wire_aml", "aml"):
        doc = wire_aml(dry=dry)
    elif cmd == "all":
        c = consolidate(dry=dry)
        w = wire_aml(dry=dry)
        doc = {"consolidate": c, "wire": w, "ok": c.get("ok") and w.get("ok")}
    elif cmd == "status":
        doc = status()
    else:
        print(json.dumps({"error": "unknown_cmd", "cmd": cmd}, indent=2))
        return 1

    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0 if doc.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())