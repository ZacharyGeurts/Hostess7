#!/usr/bin/env pythong
"""Always Files — unified VFS fabric: catalog + index + overlay + types + rollback + AI."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL.parent / "Queen"))
DOCTRINE = INSTALL / "data" / "field-always-files-doctrine.json"
AI_CONTRACT = INSTALL / "data" / "field-vfs-ai-contract.json"
AWARENESS_PLATE = STATE / "field-always-files-plate.json"
AWARENESS_INDEX = STATE / "field-always-files-index.json"

SCHEMA_FILE = "field-always-file/v1"
SCHEMA_PLATE = "field-always-files-plate/v1"

_MOD_CACHE: dict[str, Any] = {}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_py(path: Path, name: str) -> Any | None:
    if name in _MOD_CACHE:
        return _MOD_CACHE[name]
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MOD_CACHE[name] = mod
        return mod
    except Exception:
        return None


def _catalog_mod() -> Any | None:
    return _import_py(INSTALL / "lib" / "nexus-file-catalog.py", "nexus_file_catalog_af")


def _indexer_mod() -> Any | None:
    return _import_py(INSTALL / "lib" / "field-drive-indexer.py", "field_drive_indexer_af")


def _fs_mod() -> Any | None:
    return _import_py(INSTALL / "lib" / "field-filesystem-update.py", "field_filesystem_update_af")


def _timeshift_mod() -> Any | None:
    return _import_py(INSTALL / "lib" / "field-timeshift.py", "field_timeshift_af")


def _soft_mod() -> Any | None:
    return _import_py(INSTALL / "lib" / "field-soft-value.py", "field_soft_value_af")


def _inspect_mod() -> Any | None:
    return _import_py(QUEEN / "lib" / "queen-file-inspect.py", "queen_file_inspect_af")


def _rel_paths(abs_path: str | Path) -> tuple[str | None, str | None]:
    """Return (install_rel, sg_rel) if path is under known roots."""
    try:
        p = Path(abs_path).resolve()
    except OSError:
        return None, None
    install_rel = sg_rel = None
    try:
        install_rel = p.relative_to(INSTALL.resolve()).as_posix()
    except ValueError:
        pass
    try:
        sg_rel = p.relative_to(SG.resolve()).as_posix()
    except ValueError:
        pass
    return install_rel, sg_rel


def _catalog_index() -> dict[str, dict[str, Any]]:
    cat_path = INSTALL / "data" / "nexus-file-catalog.json"
    if not cat_path.is_file():
        mod = _catalog_mod()
        if mod and hasattr(mod, "build_catalog"):
            try:
                doc = mod.build_catalog(INSTALL)
                return {r["path"]: r for r in doc.get("files") or [] if r.get("path")}
            except Exception:
                return {}
        return {}
    doc = _load(cat_path, {})
    mod = _catalog_mod()
    if mod and hasattr(mod, "catalog_index"):
        return mod.catalog_index(doc)
    return {r["path"]: r for r in doc.get("files") or [] if r.get("path")}


def _drive_index_by_path() -> dict[str, dict[str, Any]]:
    idx = _indexer_mod()
    if not idx or not hasattr(idx, "load_table"):
        return {}
    table = idx.load_table()
    out: dict[str, dict[str, Any]] = {}
    for row in table.get("entries") or []:
        key = str(row.get("path") or row.get("sort_key") or "")
        if key:
            out[key] = row
    return out


def _overlay_entries() -> dict[str, dict[str, Any]]:
    fs = _fs_mod()
    if fs and hasattr(fs, "load_overlay"):
        doc = fs.load_overlay()
        return dict(doc.get("entries") or {})
    return _load(STATE / "field-filesystem-overlay.json", {}).get("entries") or {}


def _file_types_registry() -> dict[str, Any]:
    reg = _load(QUEEN / "data" / "queen-file-types.json", {})
    return reg.get("types") or {}


def _type_for_path(path: Path) -> dict[str, Any]:
    ext = path.suffix.lower().lstrip(".")
    types = _file_types_registry()
    for tid, spec in types.items():
        exts = [str(e).lower().lstrip(".") for e in (spec.get("extensions") or [])]
        if ext in exts:
            return {
                "type_id": tid,
                "label": spec.get("label") or tid,
                "action": spec.get("action"),
                "compileable": bool(spec.get("compileable")),
                "open_with": spec.get("open_with"),
            }
    return {"type_id": "unknown", "label": ext or "file", "action": "open_tab"}


def _value_for_ext(ext: str) -> dict[str, Any]:
    vv = _load(INSTALL / "data" / "field-valuable-values.json", {})
    by_type = vv.get("by_type") or {}
    key = ext.lstrip(".").lower() or "unknown"
    for candidate in (key, "binary" if key in ("so", "o", "a") else None, "default"):
        if not candidate:
            continue
        row = by_type.get(candidate)
        if row:
            return {"value": int(row.get("value", vv.get("default_value", 50))), "label": row.get("label", "standard")}
    return {"value": int(vv.get("default_value", 50)), "label": "standard"}


def _ai_policy(type_id: str, *, destroyed: bool = False) -> dict[str, Any]:
    contract = _load(AI_CONTRACT, {})
    if destroyed:
        pol = contract.get("file_policies", {}).get("destroyed") or {}
        return {
            "read_max_bytes": 0,
            "edit_policy": "forbidden",
            "grep_ok": False,
            "catalog_only": True,
            "checkpoint_before_edit": False,
        }
    policies = contract.get("file_policies") or {}
    key = "default"
    if type_id in ("python", "py"):
        key = "runtime_py"
    elif type_id in ("json", "doctrine"):
        key = "data_json"
    elif type_id in ("html", "panel"):
        key = "panel_html"
    pol = policies.get(key) or policies.get("default") or {}
    doctrine = _load(DOCTRINE, {})
    ai_doc = doctrine.get("ai") or {}
    return {
        "read_max_bytes": int(pol.get("read_max_bytes") or ai_doc.get("default_read_max_bytes") or 65536),
        "edit_policy": pol.get("edit_policy") or "checkpoint_first",
        "grep_ok": bool(pol.get("grep_ok", True)),
        "checkpoint_before_edit": bool(ai_doc.get("checkpoint_before_edit", True)),
        "tools": ["read", "stat", "grep", "resolve"],
    }


def _checkpoint_meta() -> dict[str, Any]:
    ts = _timeshift_mod()
    if not ts or not hasattr(ts, "list_checkpoints"):
        return {"available": False, "count": 0, "latest": None}
    try:
        rows = ts.list_checkpoints() or []
        latest = rows[0] if rows else None
        return {
            "available": bool(rows),
            "count": len(rows),
            "latest": (latest or {}).get("id"),
            "latest_at": (latest or {}).get("created_at"),
        }
    except Exception:
        return {"available": False, "count": 0, "latest": None}


def _history_for_path(path_keys: list[str]) -> list[dict[str, Any]]:
    idx = _indexer_mod()
    if not idx or not hasattr(idx, "history_for_path"):
        return []
    hits: list[dict[str, Any]] = []
    for key in path_keys:
        if not key:
            continue
        try:
            rows = idx.history_for_path(key) or []
            hits.extend(rows[:8])
        except Exception:
            pass
    return hits[:12]


def _knows_list(
    *,
    catalog: dict[str, Any] | None,
    index: dict[str, Any] | None,
    overlay: dict[str, Any] | None,
    type_row: dict[str, Any] | None,
) -> list[str]:
    knows: list[str] = []
    if catalog:
        knows.extend(["catalog", "sha256", "role", "description"])
    if index:
        knows.extend(["index", "mtime_ns", "bucket"])
    if overlay:
        knows.append("overlay")
        if overlay.get("destroyed"):
            knows.append("destroyed")
        if overlay.get("deleted"):
            knows.append("deleted")
    if type_row and type_row.get("type_id") != "unknown":
        knows.extend(["types", "action"])
    knows.append("ai_policy")
    if _checkpoint_meta().get("available"):
        knows.append("timeshift")
    return sorted(set(knows))


def resolve(
    path: str | Path,
    *,
    compute_hash: bool = False,
    inspect: bool = False,
) -> dict[str, Any]:
    """Fuse all VFS layers into one always-file record."""
    raw = str(path).replace("\\", "/")
    p = Path(raw)
    if not p.is_absolute():
        for base in (INSTALL, SG):
            candidate = base / raw
            if candidate.exists():
                p = candidate.resolve()
                break
        else:
            p = (INSTALL / raw).resolve()

    install_rel, sg_rel = _rel_paths(p)
    lookup_keys = [k for k in (install_rel, sg_rel, str(p)) if k]
    cat_idx = _catalog_index()
    drv_idx = _drive_index_by_path()
    overlay = _overlay_entries()

    catalog_row: dict[str, Any] = {}
    for key in lookup_keys:
        if key in cat_idx:
            catalog_row = cat_idx[key]
            break

    index_row: dict[str, Any] = {}
    for key in lookup_keys:
        if key in drv_idx:
            index_row = drv_idx[key]
            break
        resolved = str(p)
        if resolved in drv_idx:
            index_row = drv_idx[resolved]
            break

    overlay_row: dict[str, Any] = {}
    for key in lookup_keys:
        if key in overlay:
            overlay_row = overlay[key]
            break

    exists = p.exists()
    destroyed = bool(overlay_row.get("destroyed") or catalog_row.get("destroyed"))
    catalog_only = destroyed or bool(overlay_row.get("catalog_only") or catalog_row.get("catalog_only"))

    type_row = _type_for_path(p) if p.suffix else {"type_id": "dir" if exists and p.is_dir() else "unknown", "label": "directory" if exists and p.is_dir() else "file"}
    if inspect and exists and p.is_file():
        insp = _inspect_mod()
        if insp and hasattr(insp, "inspect_file"):
            try:
                ft = insp.inspect_file(p)
                type_row = {**type_row, **{k: ft.get(k) for k in ("type_id", "label", "action", "compileable", "icon") if ft.get(k) is not None}}
            except Exception:
                pass

    ext = p.suffix.lower()
    value_row = _value_for_ext(ext)
    cp = _checkpoint_meta()

    size = index_row.get("size")
    mtime_ns = index_row.get("mtime_ns")
    if exists:
        try:
            st = p.stat()
            size = int(st.st_size)
            mtime_ns = int(st.st_mtime_ns)
        except OSError:
            pass

    sha = catalog_row.get("sha256")
    if compute_hash and exists and p.is_file() and not sha:
        try:
            h = hashlib.sha256()
            with p.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                    h.update(chunk)
            sha = h.hexdigest()
        except OSError:
            sha = None

    ai = _ai_policy(str(type_row.get("type_id") or "default"), destroyed=destroyed)
    knows = _knows_list(catalog=catalog_row or None, index=index_row or None, overlay=overlay_row or None, type_row=type_row)

    h7s_fs: dict[str, Any] = {}
    if exists and p.is_file() and os.environ.get("NEXUS_H7S_FS", "1") == "1":
        fs_py = INSTALL / "lib" / "field-h7s-fs.py"
        if fs_py.is_file():
            try:
                fs_mod = _import_py(fs_py, "field_always_files_h7s_fs")
                if fs_mod and hasattr(fs_mod, "vfs_resolve"):
                    h7s_fs = fs_mod.vfs_resolve(p)
            except Exception:
                h7s_fs = {}

    row: dict[str, Any] = {
        "schema": SCHEMA_FILE,
        "path": str(p),
        "rel_install": install_rel,
        "rel_sg": sg_rel,
        "name": p.name,
        "ext": ext,
        "exists": exists,
        "h7s": h7s_fs or None,
        "kind": "dir" if exists and p.is_dir() else "file" if exists else "ghost" if catalog_only else "missing",
        "size": size,
        "mtime_ns": mtime_ns,
        "sha256": sha,
        "role": catalog_row.get("role"),
        "description": catalog_row.get("description"),
        "catalog": {
            "present": bool(catalog_row),
            "version": _load(INSTALL / "data" / "nexus-file-catalog.json", {}).get("version"),
        },
        "index": {
            "present": bool(index_row),
            "bucket": index_row.get("bucket"),
            "indexed_at": _load(STATE / "field-drive-index/table.json", {}).get("indexed_at"),
        },
        "overlay": {
            "present": bool(overlay_row),
            "deleted": bool(overlay_row.get("deleted") or catalog_row.get("deleted")),
            "destroyed": destroyed,
            "destroyed_at": overlay_row.get("destroyed_at") or catalog_row.get("destroyed_at"),
            "destroyed_date": overlay_row.get("destroyed_date") or catalog_row.get("destroyed_date"),
            "tier": overlay_row.get("tier") or catalog_row.get("tier") or "active",
            "catalog_only": catalog_only,
        },
        "type": type_row,
        "value": value_row,
        "timeshift": {
            "rollback_available": cp.get("available"),
            "latest_checkpoint": cp.get("latest"),
            "lineage": _history_for_path(lookup_keys),
        },
        "security": {
            "pin_rollback": True,
            "never_hard_delete": True,
            "jail_roots": [str(SG), str(INSTALL)],
        },
        "ai": ai,
        "knows": knows,
        "knows_count": len(knows),
        "confidence": round(min(1.0, len(knows) / 10.0), 2),
        "updated": _now(),
    }
    if inspect and exists and p.is_file():
        insp = _inspect_mod()
        if insp and hasattr(insp, "inspect_file"):
            try:
                row["inspect"] = insp.inspect_file(p)
            except Exception:
                pass
    return row


def _panel_port() -> int:
    try:
        return int(os.environ.get("NEXUS_THREAT_PANEL_PORT") or _load(DOCTRINE, {}).get("ui", {}).get("default_panel_port") or 9477)
    except (TypeError, ValueError):
        return 9477


def _panel_base() -> str:
    return f"http://127.0.0.1:{_panel_port()}"


def system_security(*, af: dict[str, Any] | None = None) -> dict[str, Any]:
    """System-managed security — operator never sets passwords or seals files."""
    doctrine = _load(DOCTRINE, {})
    sec_doc = doctrine.get("system_security") or {}
    af = af or {}
    sec = af.get("security") or {}
    overlay = af.get("overlay") or {}
    cp = _checkpoint_meta()
    layers_out: list[dict[str, Any]] = []
    for layer in sec_doc.get("layers") or []:
        lid = str(layer.get("id") or "")
        mod_path = str(layer.get("module") or "")
        live = False
        if mod_path.startswith("Queen/"):
            live = (QUEEN / mod_path.replace("Queen/", "", 1)).is_file()
        elif mod_path.startswith("lib/"):
            live = (INSTALL / mod_path.replace("lib/", "", 1)).is_file()
        else:
            live = (INSTALL / mod_path).is_file() or (SG / mod_path).is_file()
        row: dict[str, Any] = {
            "id": lid,
            "label": layer.get("label") or lid,
            "live": live,
            "system": True,
        }
        if lid == "jail":
            row["ok"] = True
            row["detail"] = "Paths resolve under SG roots only"
        elif lid == "timeshift":
            row["ok"] = bool(cp.get("available"))
            row["detail"] = f"{cp.get('count', 0)} checkpoints" if cp.get("available") else "checkpoints on demand"
        elif lid == "overlay":
            row["ok"] = True
            row["detail"] = "destroyed/catalog_only never hard-deleted"
        elif lid == "pin_rollback":
            row["ok"] = bool(sec.get("pin_rollback", True))
            row["detail"] = "Redata pin rollback witness"
        else:
            row["ok"] = live
            row["detail"] = "system layer active" if live else "module present"
        layers_out.append(row)
    live_count = sum(1 for L in layers_out if L.get("ok"))
    return {
        "system_managed": bool(sec_doc.get("system_managed", True)),
        "password_required": False,
        "operator_never_secures": bool(sec_doc.get("operator_never_secures", True)),
        "never_hard_delete": bool(sec.get("never_hard_delete", True)),
        "motto": sec_doc.get("motto") or "The system secures every file — you never set a password.",
        "layers": layers_out,
        "layers_live": live_count,
        "posture": f"System secures · {live_count} layers live · no password",
        "destroyed": bool(overlay.get("destroyed")),
        "catalog_only": bool(overlay.get("catalog_only")),
    }


def _theme_engine_mod() -> Any | None:
    return _import_py(INSTALL / "lib" / "ammoos-theme-engine.py", "ammoos_theme_engine_af")


def _theme_properties_section(af: dict[str, Any]) -> dict[str, Any] | None:
    mod = _theme_engine_mod()
    if not mod or not hasattr(mod, "properties_menu_for_file"):
        return None
    try:
        sec = mod.properties_menu_for_file(af)
        if not sec:
            return None
        return {
            "id": sec.get("id") or "theme_file_type",
            "title": sec.get("title") or "File type & launch",
            "banner": sec.get("hint"),
            "fields": sec.get("fields") or [],
            "surface_options": sec.get("surface_options") or [],
            "type_id": sec.get("type_id"),
            "settings_link": sec.get("rule", {}).get("settings_link") or "/control-panel?tab=themes&section=file_types",
        }
    except Exception:
        return None


def properties_menu(af: dict[str, Any]) -> dict[str, Any]:
    """Rich properties + context actions for Queen Files UI."""
    base = _panel_base()
    rel = af.get("rel_install") or af.get("rel_sg") or ""
    path = str(af.get("path") or "")
    name = str(af.get("name") or path.split("/")[-1] or "—")
    typ = af.get("type") or {}
    overlay = af.get("overlay") or {}
    ai = af.get("ai") or {}
    ts = af.get("timeshift") or {}
    value = af.get("value") or {}
    security = system_security(af=af)
    knows = list(af.get("knows") or [])

    def field(label: str, value: Any, **extra: Any) -> dict[str, Any]:
        row = {"label": label, "value": value if value is not None else "—"}
        row.update(extra)
        return row

    sections: list[dict[str, Any]] = [
        {
            "id": "general",
            "title": "General",
            "fields": [
                field("Name", name),
                field("Kind", af.get("kind")),
                field("Type", typ.get("label") or typ.get("type_id")),
                field("Size", af.get("size"), format="bytes"),
                field("Path", path, copy=True, mono=True),
                field("Install rel", rel or None, copy=True, mono=True, link=f"{base}/api/field-vfs/resolve?path={rel}" if rel else None),
            ],
        },
        {
            "id": "always",
            "title": "Always Knows",
            "tags": knows,
            "fields": [
                field("Awareness", f"{int((af.get('confidence') or 0) * 100)}%"),
                field("Knows count", af.get("knows_count") or len(knows)),
                field("Role", af.get("role")),
                field("Description", af.get("description")),
                field("SHA-256", af.get("sha256"), copy=True, mono=True),
                field("Value", f"{value.get('label', '')} ({value.get('value', '')})" if value else None),
            ],
        },
        {
            "id": "security",
            "title": "Security",
            "banner": security.get("motto"),
            "fields": [
                field("Managed by", "NEXUS Field system"),
                field("Password", "Never required"),
                field("Operator seal", "Not required — system handles it"),
                field("Hard delete", "Forbidden"),
                field("Jail", "Queen file browser"),
            ],
            "layers": security.get("layers"),
        },
    ]
    if overlay.get("present") or overlay.get("destroyed") or overlay.get("deleted"):
        sections.append({
            "id": "overlay",
            "title": "Overlay",
            "fields": [
                field("Tier", overlay.get("tier")),
                field("Deleted", overlay.get("deleted")),
                field("Destroyed", overlay.get("destroyed")),
                field("Catalog only", overlay.get("catalog_only")),
                field("Destroyed at", overlay.get("destroyed_at") or overlay.get("destroyed_date")),
            ],
        })
    if ts.get("rollback_available") or (ts.get("lineage") or []):
        sections.append({
            "id": "timeshift",
            "title": "TimeShift",
            "fields": [
                field("Rollback", "Available" if ts.get("rollback_available") else "—"),
                field("Latest checkpoint", ts.get("latest_checkpoint")),
                field("Lineage rows", len(ts.get("lineage") or [])),
            ],
        })
    sections.append({
        "id": "ai",
        "title": "AI policy",
        "fields": [
            field("Read cap", ai.get("read_max_bytes"), format="bytes"),
            field("Edit policy", ai.get("edit_policy")),
            field("Checkpoint before edit", ai.get("checkpoint_before_edit")),
            field("Grep allowed", ai.get("grep_ok")),
        ],
    })

    theme_sec = _theme_properties_section(af)
    if theme_sec:
        sections.insert(2, theme_sec)

    resolve_href = f"{base}/api/field-vfs/resolve?path={rel or path}"
    actions: list[dict[str, Any]] = [
        {"id": "open", "label": "Open", "group": "file", "primary": True, "ui": "open"},
        {"id": "properties", "label": "Properties…", "group": "file", "ui": "properties"},
        {"id": "preview", "label": "Preview", "group": "file", "ui": "preview"},
        {"id": "queen_code", "label": "Queen Code", "group": "file", "ui": "queen_code", "when": "file"},
        {"id": "tab", "label": "Open in tab", "group": "file", "ui": "tab"},
        {"id": "hotbar", "label": "Add to wishlist", "group": "organize", "ui": "hotbar"},
        {"id": "copy_path", "label": "Copy path", "group": "clipboard", "ui": "copy_path"},
        {"id": "copy_rel", "label": "Copy install path", "group": "clipboard", "ui": "copy_rel", "when": "rel"},
        {"id": "copy_sha", "label": "Copy SHA-256", "group": "clipboard", "ui": "copy_sha", "when": "sha"},
        {"id": "checkpoint", "label": "TimeShift checkpoint", "group": "timeshift", "ui": "checkpoint"},
        {"id": "rollback", "label": "TimeShift rollback…", "group": "timeshift", "ui": "rollback", "when": "rollback"},
        {"id": "vfs_resolve", "label": "VFS resolve API", "group": "links", "href": resolve_href, "external": True},
        {"id": "vfs_search", "label": "Search VFS", "group": "links", "href": f"{base}/api/field-vfs/search?query={name}", "external": True},
        {"id": "vfs_ai", "label": "VFS AI contract", "group": "links", "href": f"{base}/api/field-vfs/ai", "external": True},
    ]

    context_groups = [
        {"id": "always", "title": "Always Files", "hint": security.get("posture"), "items": ["properties", "checkpoint", "vfs_resolve"]},
        {"id": "file", "title": "File", "items": ["open", "preview", "queen_code", "tab"]},
        {"id": "organize", "title": "Organize", "items": ["hotbar", "copy_path", "copy_rel", "copy_sha"]},
        {"id": "timeshift", "title": "TimeShift", "items": ["rollback"]},
        {"id": "links", "title": "Links", "items": ["vfs_search", "vfs_ai"]},
    ]

    return {
        "schema": "field-always-properties/v1",
        "path": path,
        "name": name,
        "security": security,
        "sections": sections,
        "actions": actions,
        "context_groups": context_groups,
        "clickables": [a for a in actions if a.get("href")],
        "updated": _now(),
    }


def enrich_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Attach always-file slice to a Queen browser entry."""
    path = str(entry.get("path") or "")
    if not path:
        return entry
    try:
        af = resolve(path, inspect=bool(entry.get("kind") == "file"))
        sec = system_security(af=af)
        entry["always"] = {
            "knows": af.get("knows"),
            "knows_count": af.get("knows_count"),
            "confidence": af.get("confidence"),
            "role": af.get("role"),
            "description": (af.get("description") or "")[:120] or None,
            "value": af.get("value"),
            "overlay": af.get("overlay"),
            "ai": af.get("ai"),
            "timeshift": {
                "rollback_available": (af.get("timeshift") or {}).get("rollback_available"),
                "latest_checkpoint": (af.get("timeshift") or {}).get("latest_checkpoint"),
            },
            "security": {
                "system_managed": sec.get("system_managed"),
                "password_required": False,
                "posture": sec.get("posture"),
                "layers_live": sec.get("layers_live"),
            },
            "rel_install": af.get("rel_install"),
            "rel_sg": af.get("rel_sg"),
            "sha256": (af.get("sha256") or "")[:16] + "…" if af.get("sha256") else None,
            "sha256_full": af.get("sha256"),
            "properties_available": True,
        }
    except Exception:
        entry["always"] = {"knows": [], "error": "enrich_failed"}
    return entry


def search(query: str, *, limit: int = 48) -> dict[str, Any]:
    q = (query or "").strip().lower()
    if not q:
        return {"ok": False, "error": "query_required"}
    hits: list[dict[str, Any]] = []
    cat = _catalog_index()
    for path, row in cat.items():
        if q in path.lower() or q in str(row.get("description") or "").lower() or q in str(row.get("role") or "").lower():
            hits.append(resolve(path))
        if len(hits) >= limit:
            break
    if len(hits) < limit:
        for path in _drive_index_by_path():
            if q in path.lower():
                if not any(h.get("path") == path or h.get("rel_install") in path for h in hits):
                    hits.append(resolve(path))
            if len(hits) >= limit:
                break
    return {"ok": True, "query": query, "count": len(hits), "hits": hits[:limit]}


def ghost_catalog(*, limit: int = 64) -> dict[str, Any]:
    """Destroyed / catalog-only entries still known to the VFS."""
    rows: list[dict[str, Any]] = []
    for path, ov in _overlay_entries().items():
        if not ov.get("destroyed") and not ov.get("catalog_only"):
            continue
        rows.append(resolve(path))
        if len(rows) >= limit:
            break
    cat = _catalog_index()
    for path, row in cat.items():
        if not row.get("destroyed") and not row.get("catalog_only"):
            continue
        if any(r.get("rel_install") == path for r in rows):
            continue
        rows.append(resolve(path))
        if len(rows) >= limit:
            break
    return {"ok": True, "count": len(rows), "ghosts": rows}


def ai_context() -> dict[str, Any]:
    """Agent bootstrap bundle — mirrors WRDT ai_context pattern."""
    contract = _load(AI_CONTRACT, {})
    doctrine = _load(DOCTRINE, {})
    plate = _load(AWARENESS_PLATE, {})
    return {
        "schema": "field-vfs-ai-context/v1",
        "tag": contract.get("tag"),
        "updated": _now(),
        "constraints": contract.get("constraints"),
        "workflows": contract.get("workflows"),
        "tools": contract.get("tools"),
        "file_policies": contract.get("file_policies"),
        "apis": doctrine.get("apis"),
        "layers": doctrine.get("layers"),
        "plate": {
            "file_count": plate.get("file_count"),
            "catalog_count": plate.get("catalog_count"),
            "index_count": plate.get("index_count"),
            "ghost_count": plate.get("ghost_count"),
            "synced_at": plate.get("synced_at"),
        },
        "timeshift": _checkpoint_meta(),
        "disk": (_fs_mod().disk_snapshot(STATE) if _fs_mod() and hasattr(_fs_mod(), "disk_snapshot") else {}),
        "bootstrap_cli": "field-always-files.py ai",
    }


def sync_plate(*, write: bool = True) -> dict[str, Any]:
    """Refresh VFS awareness plate — summary counts + sample always-files."""
    cat = _catalog_index()
    drv = _drive_index_by_path()
    overlay = _overlay_entries()
    ghosts = sum(1 for v in overlay.values() if v.get("destroyed"))
    cp = _checkpoint_meta()

    samples: list[dict[str, Any]] = []
    for rel in sorted(cat.keys())[:12]:
        samples.append(resolve(rel))

    doc = {
        "schema": SCHEMA_PLATE,
        "synced_at": _now(),
        "ok": True,
        "motto": (_load(DOCTRINE, {}).get("motto")),
        "catalog_count": len(cat),
        "index_count": len(drv),
        "overlay_count": len(overlay),
        "ghost_count": ghosts,
        "file_count": max(len(cat), len(drv)),
        "timeshift": cp,
        "layers_live": {
            "catalog": bool(cat),
            "index": bool(drv),
            "overlay": bool(overlay),
            "types": bool(_file_types_registry()),
            "timeshift": cp.get("available"),
        },
        "samples": samples,
        "ai": {"contract": str(AI_CONTRACT.name), "bootstrap": "/api/field-vfs/ai"},
    }
    if write:
        _save_atomic(AWARENESS_PLATE, doc)
        _save_atomic(AWARENESS_INDEX, {
            "schema": "field-always-files-index/v1",
            "synced_at": doc["synced_at"],
            "paths": sorted(set(list(cat.keys()) + list(drv.keys())))[:5000],
        })
    return doc


def dispatch(body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body or {}
    action = str(body.get("action") or body.get("cmd") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json", "plate"):
        plate = _load(AWARENESS_PLATE, {})
        if not plate:
            plate = sync_plate(write=True)
        return {"ok": True, **plate, "doctrine": _load(DOCTRINE, {}).get("title")}

    if action == "sync":
        return sync_plate(write=True)

    if action == "ai":
        return {"ok": True, **ai_context()}

    if action in ("resolve", "know", "always"):
        raw = str(body.get("path") or body.get("file") or "")
        if not raw:
            return {"ok": False, "error": "path_required"}
        return {"ok": True, "always_file": resolve(raw, compute_hash=bool(body.get("hash")), inspect=bool(body.get("inspect", True)))}

    if action == "search":
        return search(str(body.get("query") or body.get("q") or ""), limit=int(body.get("limit") or 48))

    if action == "ghosts":
        return ghost_catalog(limit=int(body.get("limit") or 64))

    if action == "enrich":
        entry = body.get("entry") or {}
        return {"ok": True, "entry": enrich_entry(dict(entry))}

    if action in ("properties", "properties_menu", "menu"):
        raw = str(body.get("path") or body.get("file") or "")
        if not raw:
            return {"ok": False, "error": "path_required"}
        af = resolve(raw, compute_hash=bool(body.get("hash")), inspect=bool(body.get("inspect", True)))
        return {
            "ok": True,
            "always_file": af,
            "properties_menu": properties_menu(af),
            "security": system_security(af=af),
        }

    if action == "timeshift_list":
        ts = _timeshift_mod()
        if not ts or not hasattr(ts, "list_checkpoints"):
            return {"ok": False, "error": "timeshift_missing"}
        return {"ok": True, "checkpoints": ts.list_checkpoints()}

    if action == "timeshift_checkpoint":
        ts = _timeshift_mod()
        if not ts or not hasattr(ts, "create_checkpoint"):
            return {"ok": False, "error": "timeshift_missing"}
        note = str(body.get("note") or "always-files checkpoint")
        return ts.create_checkpoint(note=note)

    if action == "timeshift_rollback":
        ts = _timeshift_mod()
        if not ts or not hasattr(ts, "rollback"):
            return {"ok": False, "error": "timeshift_missing"}
        cid = str(body.get("id") or body.get("checkpoint_id") or "")
        if not cid:
            return {"ok": False, "error": "checkpoint_id_required"}
        return ts.rollback(cid, confirm=bool(body.get("confirm")))

    return {"ok": False, "error": "unknown_action", "action": action}


def posture() -> dict[str, Any]:
    plate = sync_plate(write=True)
    return {
        "schema": "field-always-files/v1",
        "ok": True,
        "product": "Always Files",
        "motto": _load(DOCTRINE, {}).get("motto"),
        "plate": plate,
        "routes": (_load(DOCTRINE, {}).get("apis") or {}),
        "posture": (
            f"Always Files — {plate.get('file_count', 0)} known · "
            f"{plate.get('ghost_count', 0)} ghosts · "
            f"timeshift {'on' if (plate.get('timeshift') or {}).get('available') else 'off'}"
        ),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "sync":
        print(json.dumps(sync_plate(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ai":
        print(json.dumps(ai_context(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "resolve" and len(sys.argv) > 2:
        print(json.dumps(resolve(sys.argv[2], compute_hash="--hash" in sys.argv, inspect=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "properties" and len(sys.argv) > 2:
        af = resolve(sys.argv[2], compute_hash="--hash" in sys.argv, inspect=True)
        print(json.dumps({"ok": True, "properties_menu": properties_menu(af), "always_file": af}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "search" and len(sys.argv) > 2:
        print(json.dumps(search(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ghosts":
        print(json.dumps(ghost_catalog(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch" and len(sys.argv) > 2:
        try:
            body = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            body = {"action": sys.argv[2]}
        print(json.dumps(dispatch(body), ensure_ascii=False, indent=2))
        return 0
    if cmd not in ("help", "-h"):
        print(json.dumps(dispatch({"action": cmd, **({"path": sys.argv[2]} if len(sys.argv) > 2 else {})}), ensure_ascii=False, indent=2))
        return 0
    print(
        "usage: field-always-files.py [json|sync|ai|resolve PATH|search QUERY|ghosts|dispatch JSON]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())