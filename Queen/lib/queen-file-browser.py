#!/usr/bin/env pythong
"""Queen file browser — split-pane roots, hotbar, zero-cost 4-slot path jail."""
from __future__ import annotations

import base64
import importlib.util
import json
import mimetypes
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

QUEEN = Path(__file__).resolve().parents[1]
_SG_PATHS_LIB = Path(__file__).resolve().parents[2] / "lib"
if str(_SG_PATHS_LIB) not in sys.path:
    sys.path.insert(0, str(_SG_PATHS_LIB))
from sg_paths import grok16_root as _grok16_root
SG = QUEEN.parent.parent
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
HOTBAR_FILE = STATE / "queen-file-hotbar.json"
DOCK_FILE = STATE / "queen-file-dock.json"
NAV_FILE = STATE / "queen-file-nav.json"
DOCTRINE = QUEEN / "data" / "queen-zero-cost-4slot.json"
WISHLIST = QUEEN / "data" / "queen-file-wishlist-doctrine.json"

_BLOCKED_PARTS = frozenset({".git", "__pycache__", ".venv-browser"})
_MAX_LIST = 0  # 0 = no cap unless client passes list_cap
_MAX_PREVIEW = int(os.environ.get("QUEEN_PREVIEW_MAX_BYTES", str(512 * 1024)))
_IMAGE_PREVIEW_MAX = int(os.environ.get("QUEEN_PREVIEW_IMAGE_MAX", str(2 * 1024 * 1024)))
_MAX_HOTBAR = 24
_MAX_DOCK = 16
_MAX_NAV = 128
_INSPECT = None
_CHAMBER = None
_POWER_SORT = None
_ALWAYS_FILES = None
_PROGRAM_LIB = None
_ALWAYS_ENRICH = os.environ.get("QUEEN_ALWAYS_FILES", "1").strip().lower() not in ("0", "false", "no")


def _always_files_mod():
    global _ALWAYS_FILES
    if _ALWAYS_FILES is not None:
        return _ALWAYS_FILES
    nexus = SG / "NewLatest"
    path = nexus / "lib" / "field-always-files.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_always_files_qfb", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _ALWAYS_FILES = mod
    return mod


def _maybe_enrich_row(row: dict[str, Any]) -> dict[str, Any]:
    if not _ALWAYS_ENRICH:
        return row
    mod = _always_files_mod()
    if mod and hasattr(mod, "enrich_entry"):
        try:
            return mod.enrich_entry(row)
        except Exception:
            row["always"] = {"knows": [], "error": "enrich_failed"}
    return row


def _power_sort_mod():
    global _POWER_SORT
    if _POWER_SORT is not None:
        return _POWER_SORT
    import importlib.util
    grok16 = _grok16_root()
    path = grok16 / "lib" / "field-power-sort.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_power_sort", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _POWER_SORT = mod
    return mod


def _power_sort_slice() -> dict[str, Any]:
    state = Path(os.environ.get("NEXUS_STATE_DIR", str(SG / "NewLatest" / ".nexus-field-drive" / "nexus-field" / "state")))
    for plate_path in (state / "g16-power-sort-plate.json",):
        try:
            plate = json.loads(plate_path.read_text(encoding="utf-8"))
            sections = plate.get("sections") or {}
            qf = sections.get("queen_files") or sections.get("file_list") or {}
            return {
                "mode": plate.get("file_list_mode") or "dirs_first",
                "algorithm": qf.get("algorithm") or plate.get("file_list_mode") or "dirs_first",
                "available": bool(qf.get("available", plate.get("ok"))),
                "cool": bool(qf.get("cool", True)),
                "sections": sections,
                "selection": plate.get("selection") or {},
                "thermal": plate.get("thermal") or {},
                "always_best_sort": True,
                "source": "power_sort_plate",
            }
        except (OSError, json.JSONDecodeError):
            pass
    env_mode = os.environ.get("G16_BEST_FILE_SORT", "").strip()
    if env_mode:
        return {"mode": env_mode, "source": "integrate_env", "always_best_sort": True, "available": True, "cool": True}
    mod = _power_sort_mod()
    if mod and hasattr(mod, "compute_selections"):
        sel = mod.compute_selections()
        sections = mod.compute_sections(sel) if hasattr(mod, "compute_sections") else {}
        qf = sections.get("queen_files") or sections.get("file_list") or {}
        return {
            "mode": sel.get("file_list_mode") or "dirs_first",
            "algorithm": qf.get("algorithm") or sel.get("file_list_mode") or "dirs_first",
            "available": bool(qf.get("available", True)),
            "cool": bool(qf.get("cool", True)),
            "selection": sel,
            "sections": sections,
            "always_best_sort": True,
            "source": "power_sort_panel",
        }
    return {"mode": "dirs_first", "always_best_sort": False, "available": False, "source": "default"}


def _ironclad_index_mod():
    nexus = SG / "NewLatest"
    path = nexus / "lib" / "ironclad-search-index.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("ironclad_search_idx_qfb", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sort_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    idx = _ironclad_index_mod()
    if idx and hasattr(idx, "ironclad_sort"):
        try:
            sorted_rows, _ = idx.ironclad_sort(entries, context="file_list", n=len(entries))
            return sorted_rows
        except Exception:
            pass
    mod = _power_sort_mod()
    if mod and hasattr(mod, "apply_sort"):
        try:
            return mod.apply_sort(entries, context="file_list", n=len(entries))
        except Exception:
            pass
    return sorted(
        entries,
        key=lambda r: (
            0 if r.get("kind") in ("dir", "launch_facade") else 1,
            str(r.get("name") or "").lower(),
        ),
    )


def _chamber_mod():
    global _CHAMBER
    if _CHAMBER is not None:
        return _CHAMBER
    import importlib.util
    spec = importlib.util.spec_from_file_location("queen_launch_chamber", QUEEN / "lib" / "queen-launch-chamber.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _CHAMBER = mod
    return mod


def _program_library_mod():
    global _PROGRAM_LIB
    if _PROGRAM_LIB is not None:
        return _PROGRAM_LIB
    spec = importlib.util.spec_from_file_location("queen_program_library", QUEEN / "lib" / "queen-program-library.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _PROGRAM_LIB = mod
    return mod


def _inspect_mod():
    global _INSPECT
    if _INSPECT is not None:
        return _INSPECT
    import importlib.util
    spec = importlib.util.spec_from_file_location("queen_file_inspect", QUEEN / "lib" / "queen-file-inspect.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _INSPECT = mod
    return mod


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _wishlist_policy() -> dict[str, Any]:
    doc = _read(WISHLIST, {})
    return doc.get("policy") or {}


def _roots() -> list[dict[str, str]]:
    env_map = {
        "KILROY": os.environ.get("KILROY_ROOT", str(SG / "KILROY")),
        "SG": os.environ.get("SG_ROOT", str(SG)),
        "Queen": os.environ.get("QUEEN_ROOT", str(QUEEN)),
        "AMOURANTHRTX": os.environ.get("AMOURANTHRTX_ROOT", str(SG / "NewLatest" / "AMOURANTHRTX")),
        "Hostess7": os.environ.get("HOSTESS7_ROOT", str(SG / "Hostess7")),
        "Grok16": str(_grok16_root()),
        "ZOCR": str(SG / "ZOCR"),
        "Final_Eye": os.environ.get("FINAL_EYE_ROOT", str(SG / "Final_Eye")),
        "Final_Ear": os.environ.get("FINAL_EAR_ROOT", str(SG / "Final_Ear")),
    }
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for label, raw in env_map.items():
        p = Path(raw).expanduser().resolve()
        key = str(p)
        if key in seen or not p.is_dir():
            continue
        seen.add(key)
        out.append({"id": label.lower().replace(" ", "_"), "label": label, "path": key})
    if _wishlist_policy().get("kilroy_first", True):
        out.sort(key=lambda r: (0 if r["id"] == "kilroy" else 1, r["label"].lower()))
    return out


def _allowed_bases() -> list[Path]:
    return [Path(r["path"]) for r in _roots()]


def _normalize_input(raw: str) -> str:
    text = unquote((raw or "").strip())
    if not text:
        return str(SG)
    if text.startswith("queen://files/"):
        return text[len("queen://files/") :]
    if text.startswith("queen://"):
        rest = text[len("queen://") :]
        if rest in ("sg", "SG"):
            return str(SG)
        for r in _roots():
            if rest.lower().startswith(r["id"] + "/") or rest.lower() == r["id"]:
                suffix = rest[len(r["id"]) :].lstrip("/")
                return str(Path(r["path"]) / suffix) if suffix else r["path"]
        return str(SG / rest)
    if text.startswith("file://"):
        return urlparse(text).path
    if text.startswith("~/"):
        return str(Path.home() / text[2:])
    if text.startswith("SG/") or text.startswith("sg/"):
        return str(SG / text[3:])
    return text


def _field_virus_gate(path: Path, *, direction: str = "ingress") -> dict[str, Any] | None:
    if os.environ.get("SG_FIELD_VIRUS_OFF", "").strip().lower() in ("1", "true", "yes"):
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("queen_field_virus", QUEEN / "lib" / "queen-field-virus.py")
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.gate_file(path, direction=direction)
    except Exception:
        return None


def _resolve_jailed(raw: str) -> tuple[Path | None, str | None]:
    """Zero-cost jail — path must stay inside allowed roots."""
    text = _normalize_input(raw)
    try:
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = (SG / path).resolve()
        else:
            path = path.resolve()
    except (OSError, RuntimeError):
        return None, "path_invalid"
    bases = _allowed_bases()
    if not bases:
        return None, "no_roots"
    for base in bases:
        try:
            path.relative_to(base)
            return path, None
        except ValueError:
            continue
    return None, "jail_denied"


_FOLDER_HEAT_CAP = int(os.environ.get("QUEEN_FOLDER_HEAT_CAP", "2500"))


def _folder_heat(p: Path) -> dict[str, Any]:
    """Shallow folder metrics — blue=file count, yellow=bytes, darken=subdirs."""
    child_count = 0
    file_count = 0
    subdir_count = 0
    total_bytes = 0
    try:
        with os.scandir(p) as it:
            for ent in it:
                if ent.name.startswith("."):
                    continue
                child_count += 1
                try:
                    if ent.is_dir(follow_symlinks=False):
                        subdir_count += 1
                    elif ent.is_file(follow_symlinks=False):
                        file_count += 1
                        total_bytes += ent.stat(follow_symlinks=False).st_size
                except OSError:
                    pass
                if child_count >= _FOLDER_HEAT_CAP:
                    break
    except OSError:
        pass
    return {
        "child_count": child_count,
        "file_count": file_count,
        "subdir_count": subdir_count,
        "total_bytes": total_bytes,
        "capped": child_count >= _FOLDER_HEAT_CAP,
    }


def _entry_kind(p: Path) -> str:
    try:
        st = p.lstat()
    except OSError:
        return "unknown"
    if stat.S_ISDIR(st.st_mode):
        return "dir"
    if stat.S_ISLNK(st.st_mode):
        return "symlink"
    if stat.S_ISREG(st.st_mode):
        return "file"
    return "other"


def _entry_row(p: Path, *, with_folder_heat: bool = True) -> dict[str, Any]:
    kind = _entry_kind(p)
    row: dict[str, Any] = {
        "name": p.name,
        "path": str(p),
        "kind": kind,
        "hidden": p.name.startswith("."),
    }
    try:
        st = p.stat()
        row["size"] = st.st_size if kind == "file" else None
        row["mtime"] = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        row["size"] = None
    if kind == "file":
        row["ext"] = p.suffix.lower()
    insp = _inspect_mod()
    if insp:
        try:
            ft = insp.inspect_file(p)
            row["file_type"] = ft
            row["icon"] = ft.get("icon")
            row["action"] = ft.get("action")
        except Exception:
            pass
    elif kind == "dir":
        row["icon"] = "📁"
        row["action"] = "open_dir"
    else:
        row["icon"] = "📄"
        row["action"] = "open_tab"
    if kind == "dir" and with_folder_heat:
        row["folder_heat"] = _folder_heat(p)
    return _maybe_enrich_row(row)


def _launchable_entry_row(chamber_root: Path, row: dict[str, Any]) -> dict[str, Any]:
    rel = str(row.get("path") or "")
    p = chamber_root / rel
    base = _entry_row(p) if p.is_file() else {
        "name": row.get("name") or Path(rel).name,
        "path": str(p),
        "kind": "file",
        "size": row.get("bytes"),
    }
    base["launchable"] = True
    base["runtime"] = row.get("runtime")
    base["action"] = "run_launchable"
    ft = base.get("file_type") or {}
    ft = {**ft, "action": "run_launchable", "launchable": True, "runtime": row.get("runtime")}
    base["file_type"] = ft
    base["icon"] = "▶"
    return base


def _chamber_launchables(path: Path) -> list[dict[str, Any]]:
    ch = _chamber_mod()
    if not ch:
        return []
    try:
        lp = ch.launch_facade_path(path)
        if lp.is_file():
            doc = ch.load_launch_manifest(lp)
        else:
            doc = ch.build_manifest_fast(path)
        return list(doc.get("launchables") or [])
    except Exception:
        return []


def _launch_facade_row(chamber_dir: Path, launch_path: Path, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    row = _entry_row(launch_path)
    row["kind"] = "launch_facade"
    row["facade"] = True
    row["chamber_root"] = str(chamber_dir)
    row["name"] = launch_path.name
    if manifest:
        row["launch_meta"] = {
            "entry": manifest.get("entry"),
            "runtime": manifest.get("runtime"),
            "file_count": manifest.get("file_count"),
            "launchable_count": manifest.get("launchable_count"),
            "bytes": manifest.get("bytes"),
            "scan": manifest.get("scan"),
            "locked": manifest.get("locked"),
            "secured": manifest.get("secured"),
            "seal_generation": manifest.get("seal_generation"),
            "fingerprint": manifest.get("fingerprint"),
        }
    insp = _inspect_mod()
    if insp:
        try:
            ft = insp.inspect_file(launch_path)
            ft["facade"] = True
            ft["browse_action"] = "browse_inside"
            ft["chamber_root"] = str(chamber_dir)
            if manifest:
                for k in ("entry", "runtime", "file_count", "bytes"):
                    if manifest.get(k) is not None:
                        ft[k] = manifest[k]
            row["file_type"] = ft
            row["icon"] = ft.get("icon")
            row["action"] = ft.get("action") or "run_launch"
        except Exception:
            row["action"] = "run_launch"
    return row


def _list_dir(path: Path, *, show_hidden: bool = False, browse_inside: bool = False) -> dict[str, Any]:
    ch = _chamber_mod()
    if ch and not browse_inside and ch.is_chamber_dir(path):
        try:
            facade = ch.ensure_launch_facade(path, write=True)
        except Exception:
            facade = {"ok": False}
        if facade.get("ok"):
            launch_path = Path(str(facade.get("path") or ch.launch_facade_path(path)))
            manifest = facade.get("manifest") or {}
            return {
                "ok": True,
                "path": str(path),
                "parent": str(path.parent) if path.parent != path else None,
                "facade": True,
                "browse_inside_required": True,
                "message": "Chamber sealed as .launch — browse inside from context menu",
                "entries": [_launch_facade_row(path, launch_path, manifest)],
                "truncated": False,
            }

    entries: list[dict[str, Any]] = []
    facade_names: set[str] = set()
    heat_budget = int(os.environ.get("QUEEN_FOLDER_HEAT_BUDGET", "64"))
    try:
        children = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
    except OSError as exc:
        return {"ok": False, "error": "list_failed", "detail": str(exc)[:120]}
    want_heat = os.environ.get("QUEEN_FOLDER_HEAT", "1").strip().lower() not in ("0", "false", "no")
    for child in children:
        if child.name in _BLOCKED_PARTS:
            continue
        if not show_hidden and child.name.startswith("."):
            continue
        if child.is_dir() and ch and ch.is_chamber_dir(child):
            try:
                facade = ch.ensure_launch_facade(child, write=True)
            except Exception:
                facade = {"ok": False}
            if facade.get("ok"):
                launch_path = Path(str(facade.get("path") or ch.launch_facade_path(child)))
                facade_names.add(launch_path.name.lower())
                entries.append(_launch_facade_row(child, launch_path, facade.get("manifest")))
                continue
        if child.suffix.lower() == ".launch" and child.name.lower() in facade_names:
            continue
        use_heat = want_heat and child.is_dir() and heat_budget > 0
        if use_heat:
            heat_budget -= 1
        entries.append(_entry_row(child, with_folder_heat=use_heat))
        list_cap = int(os.environ.get("QUEEN_FILE_LIST_CAP", "0") or "0")
        if list_cap > 0 and len(entries) >= list_cap:
            break
    launchables: list[dict[str, Any]] = []
    if browse_inside or ch and ch.is_chamber_dir(path):
        for row in _chamber_launchables(path):
            launchables.append(_launchable_entry_row(path, row))
    parent = str(path.parent) if path.parent != path else None
    rel = None
    for base in _allowed_bases():
        try:
            rel = str(path.relative_to(base))
            root_label = next((r["label"] for r in _roots() if Path(r["path"]) == base), "SG")
            rel = f"{root_label}/{rel}" if rel != "." else root_label
            break
        except ValueError:
            continue
    entries = _sort_entries(entries)
    list_cap = int(os.environ.get("QUEEN_FILE_LIST_CAP", "0") or "0")
    truncated = list_cap > 0 and len(children) > list_cap
    ps = _power_sort_slice()
    return {
        "ok": True,
        "path": str(path),
        "parent": parent,
        "relative": rel,
        "entries": entries,
        "launchables": launchables,
        "launchable_count": len(launchables),
        "truncated": truncated,
        "capped": truncated,
        "power_sort": ps,
    }


def _tree_slice(path: Path, depth: int = 2) -> list[dict[str, Any]]:
    if depth <= 0:
        return []
    nodes: list[dict[str, Any]] = []
    try:
        children = sorted(path.iterdir(), key=lambda x: x.name.lower())
    except OSError:
        return []
    for child in children:
        if child.name in _BLOCKED_PARTS or child.name.startswith("."):
            continue
        if not child.is_dir():
            continue
        nodes.append({
            "name": child.name,
            "path": str(child),
            "children": _tree_slice(child, depth - 1) if depth > 1 else [],
        })
        if len(nodes) >= 256:
            break
    return nodes


def load_dock() -> dict[str, Any]:
    doc = _read(DOCK_FILE, {})
    if doc.get("schema") != "queen-file-dock/v1":
        doc = {"schema": "queen-file-dock/v1", "updated": _ts(), "slots": []}
    return doc


def save_dock(slots: list[dict[str, Any]]) -> dict[str, Any]:
    clean: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, row in enumerate(slots[:_MAX_DOCK]):
        path, err = _resolve_jailed(str(row.get("path") or ""))
        if err or not path or not path.is_dir():
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        clean.append({
            "id": str(row.get("id") or f"dock-{i}"),
            "path": key,
            "label": str(row.get("label") or path.name),
            "pinned_at": row.get("pinned_at") or _ts(),
            "order": int(row.get("order", i)),
        })
    doc = {"schema": "queen-file-dock/v1", "updated": _ts(), "slots": clean}
    _save(DOCK_FILE, doc)
    return doc


def dock_push(path: str, *, label: str | None = None) -> dict[str, Any]:
    resolved, err = _resolve_jailed(path)
    if err or not resolved or not resolved.is_dir():
        return {"ok": False, "error": err or "not_a_directory"}
    doc = load_dock()
    slots = [s for s in doc.get("slots") or [] if s.get("path") != str(resolved)]
    slots.insert(0, {
        "id": f"dock-{int(datetime.now().timestamp())}",
        "path": str(resolved),
        "label": label or resolved.name,
        "pinned_at": _ts(),
        "order": 0,
    })
    for i, s in enumerate(slots):
        s["order"] = i
    out = save_dock(slots)
    return {"ok": True, "dock": out}


def load_nav() -> dict[str, Any]:
    doc = _read(NAV_FILE, {})
    if doc.get("schema") != "queen-file-nav/v1":
        doc = {"schema": "queen-file-nav/v1", "updated": _ts(), "stack": [], "index": -1}
    return doc


def save_nav(stack: list[str], index: int) -> dict[str, Any]:
    clean: list[str] = []
    for raw in stack[-_MAX_NAV:]:
        p, err = _resolve_jailed(raw)
        if err or not p:
            continue
        clean.append(str(p))
    index = max(-1, min(index, len(clean) - 1))
    doc = {"schema": "queen-file-nav/v1", "updated": _ts(), "stack": clean, "index": index}
    _save(NAV_FILE, doc)
    return doc


def nav_push(path: str) -> dict[str, Any]:
    resolved, err = _resolve_jailed(path)
    if err or not resolved:
        return {"ok": False, "error": err or "jail_denied"}
    doc = load_nav()
    stack = list(doc.get("stack") or [])
    index = int(doc.get("index") or -1)
    key = str(resolved)
    if index >= 0 and index < len(stack) and stack[index] == key:
        return {"ok": True, "nav": doc, "path": key, "noop": True}
    stack = stack[: index + 1] if index >= 0 else stack
    stack.append(key)
    out = save_nav(stack, len(stack) - 1)
    return {"ok": True, "nav": out, "path": key}


def nav_step(delta: int) -> dict[str, Any]:
    doc = load_nav()
    stack = list(doc.get("stack") or [])
    index = int(doc.get("index") or -1)
    new_index = index + int(delta)
    if new_index < 0 or new_index >= len(stack):
        return {"ok": False, "error": "nav_bounds", "nav": doc}
    out = save_nav(stack, new_index)
    return {"ok": True, "nav": out, "path": stack[new_index]}


def default_hotbar() -> dict[str, Any]:
    wish = _read(WISHLIST, {})
    slots: list[dict[str, Any]] = []
    roots_by_id = {r["id"]: r for r in _roots()}
    for i, row in enumerate(wish.get("default_slots") or []):
        root_key = str(row.get("root") or row.get("id") or "").lower()
        r = roots_by_id.get(root_key)
        if not r:
            continue
        slots.append({
            "id": f"wish-{r['id']}",
            "path": r["path"],
            "label": str(row.get("label") or r["label"]),
            "kind": "folder",
            "order": i,
        })
    if not slots:
        for i, r in enumerate(_roots()[:8]):
            slots.append({
                "id": f"root-{r['id']}",
                "path": r["path"],
                "label": r["label"],
                "kind": "folder",
                "order": i,
            })
    return {"schema": "queen-file-hotbar/v1", "updated": _ts(), "slots": slots, "wishlist": True}


def load_hotbar() -> dict[str, Any]:
    doc = _read(HOTBAR_FILE, {})
    if doc.get("schema") != "queen-file-hotbar/v1":
        doc = default_hotbar()
        _save(HOTBAR_FILE, doc)
    return doc


def save_hotbar(slots: list[dict[str, Any]]) -> dict[str, Any]:
    clean: list[dict[str, Any]] = []
    for i, row in enumerate(slots[:_MAX_HOTBAR]):
        path, err = _resolve_jailed(str(row.get("path") or ""))
        if err or not path:
            continue
        kind = _entry_kind(path)
        clean.append({
            "id": str(row.get("id") or f"slot-{i}"),
            "path": str(path),
            "label": str(row.get("label") or path.name or path),
            "kind": "folder" if kind == "dir" else "file",
            "order": int(row.get("order", i)),
        })
    doc = {"schema": "queen-file-hotbar/v1", "updated": _ts(), "slots": clean}
    _save(HOTBAR_FILE, doc)
    return doc


def _launch_seal_slice() -> dict[str, Any]:
    ch = _chamber_mod()
    if ch and hasattr(ch, "launch_seal_state"):
        return ch.launch_seal_state()
    return {"generation": 0, "required_for_refresh": False}


def _search_tree(path: Path, query: str, *, depth: int, limit: int) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q:
        return []

    idx = _ironclad_index_mod()
    if idx and hasattr(idx, "search_files_fast"):
        try:
            roots = [str(path.resolve())]
            for base in _allowed_bases():
                if path == base or str(path).startswith(str(base)):
                    roots = [str(base)]
                    break
            fast = idx.search_files_fast(q, roots=roots, limit=limit, depth=depth)
            out: list[dict[str, Any]] = []
            for row in fast:
                p = Path(str(row.get("path") or ""))
                if p.is_file() or p.is_dir():
                    try:
                        p.relative_to(path.resolve())
                    except ValueError:
                        continue
                    out.append(_entry_row(p))
                if len(out) >= limit:
                    break
            if out:
                return _sort_entries(out)
        except Exception:
            pass

    hits: list[dict[str, Any]] = []

    def walk(node: Path, remaining: int) -> None:
        if remaining < 0 or len(hits) >= limit:
            return
        try:
            children = list(node.iterdir())
        except OSError:
            return
        children.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
        for child in children:
            if len(hits) >= limit:
                return
            if child.name in _BLOCKED_PARTS or child.name.startswith("."):
                continue
            if q in child.name.lower():
                hits.append(_entry_row(child))
            if child.is_dir() and remaining > 0:
                walk(child, remaining - 1)

    walk(path, depth)
    return _sort_entries(hits)


def _mkdir_jailed(parent_raw: str, name: str) -> dict[str, Any]:
    clean = re.sub(r"[^\w.\- +]+", "_", (name or "").strip())
    if not clean or clean in (".", ".."):
        return {"ok": False, "error": "invalid_name"}
    parent, err = _resolve_jailed(parent_raw)
    if err or not parent or not parent.is_dir():
        return {"ok": False, "error": err or "not_a_directory"}
    target = (parent / clean).resolve()
    _, err2 = _resolve_jailed(str(target))
    if err2:
        return {"ok": False, "error": err2}
    if target.exists():
        return {"ok": False, "error": "exists", "path": str(target)}
    try:
        target.mkdir(parents=False, exist_ok=False)
        return {"ok": True, "path": str(target), "entry": _entry_row(target)}
    except OSError as exc:
        return {"ok": False, "error": str(exc)[:120]}


def zero_cost_slice() -> dict[str, Any]:
    doc = _read(DOCTRINE, {})
    if not doc.get("schema"):
        doc = {
            "schema": "queen-zero-cost-4slot/v1",
            "runtime_tax": 0,
            "slots": [{"id": "TIME"}, {"id": "MEMORY"}, {"id": "THERMO"}, {"id": "CONTEXT"}],
        }
    doc["active"] = True
    doc["file_browser_jail"] = True
    doc["queen_best_zero_cost"] = True
    doc["launch_seal"] = _launch_seal_slice()
    return doc


def browser_status() -> dict[str, Any]:
    doctrine = zero_cost_slice()
    return {
        "schema": "queen-file-browser/v1",
        "updated": _ts(),
        "title": "Queen Files — split pane",
        "roots": _roots(),
        "hotbar": load_hotbar(),
        "dock": load_dock(),
        "nav": load_nav(),
        "zero_cost_4_slot": doctrine,
        "conventions": {
            "path_absolute": True,
            "path_relative_sg": True,
            "tilde_home": True,
            "queen_scheme": "queen://files/<root>/…",
            "queen_legacy": "queen://sg/…",
            "file_uri": "file:///…",
            "sg_prefix": "SG/…",
            "show_hidden": "action show_hidden",
        },
        "wishlist": _read(WISHLIST, {}),
        "power_sort": _power_sort_slice(),
        "capabilities": {
            "split_pane": True,
            "tree_pane": True,
            "wishlist_menu": True,
            "hotbar_drag_drop": True,
            "hotbar_custom_label": True,
            "wishlist_search": True,
            "wishlist_mkdir": True,
            "folder_menu": True,
            "zero_cost_jail": True,
            "context_menu": True,
            "file_type_inspect": True,
            "icon_overrides": True,
            "program_library_v2": True,
            "zero_copy_icons": True,
            "launch_spv": True,
            "launch_chamber": True,
            "singular_field_plane": True,
            "compile_mode": True,
            "folder_dock": True,
            "nav_history": True,
            "launchables_panel": True,
            "lock_launch": True,
            "secured_launch": True,
            "launch_refresh_requires_sync": True,
            "unlimited_list": True,
            "power_sort": True,
            "syntax_highlight": True,
            "universal_preview": True,
            "always_files": _ALWAYS_ENRICH,
            "always_knows_badge": True,
            "always_rollback_hint": True,
            "always_properties_menu": True,
            "system_security_no_password": True,
            "viewer_modules": [
                "world/queen-syntax.css",
                "world/queen-viewer.css",
                "world/queen-code-highlight.js",
                "world/queen-viewer.js",
            ],
        },
        "launch_seal": _launch_seal_slice(),
        "file_types": (_inspect_mod().file_types_registry() if _inspect_mod() else None),
    }


def _code_mod():
    spec = importlib.util.spec_from_file_location("queen_code", QUEEN / "lib" / "queen-code.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _preview_file(path: Path, *, entry: dict[str, Any] | None = None) -> dict[str, Any]:
    if path.is_dir():
        return {"ok": True, "mode": "folder", "path": str(path)}
    if not path.is_file():
        return {"ok": False, "error": "not_a_file"}
    scan = _field_virus_gate(path, direction="ingress")
    if scan and not scan.get("ok"):
        return {"ok": False, "error": "field_virus_hold", "field_virus": scan}
    size = path.stat().st_size
    ext = path.suffix.lower()
    insp = _inspect_mod()
    ft = insp.inspect_file(path) if insp else {}
    image_exts = {
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".bmp", ".avif",
    }
    if ext in image_exts and size <= _IMAGE_PREVIEW_MAX:
        mime = (ft or {}).get("mime") or mimetypes.guess_type(str(path))[0] or "image/png"
        raw = path.read_bytes()
        return {
            "ok": True,
            "mode": "image",
            "path": str(path),
            "bytes": size,
            "mime": mime,
            "data_url": f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}",
            "type_label": (ft or {}).get("label") or "image",
        }
    text_exts = {
        ".py", ".js", ".ts", ".json", ".md", ".html", ".css", ".sh", ".c", ".cpp", ".h",
        ".rs", ".go", ".zig", ".toml", ".yaml", ".yml", ".sql", ".cmake", ".fld", ".log",
        ".diff", ".patch", ".xml", ".ini", ".vert", ".frag", ".comp", ".glsl", ".gpy",
    }
    if ext in text_exts or size <= _MAX_PREVIEW:
        code = _code_mod()
        if code:
            doc = code.dispatch({"action": "read", "path": str(path)})
            if doc.get("ok"):
                mode = "markdown" if ext == ".md" else ("json" if ext == ".json" else "code")
                return {
                    "ok": True,
                    "mode": mode,
                    "path": str(path),
                    "content": doc.get("content") or "",
                    "language": doc.get("language") or doc.get("g16_discern") or "plaintext",
                    "bytes": doc.get("bytes") or size,
                    "lines": doc.get("lines"),
                    "type_label": (ft or {}).get("label"),
                }
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        return {
            "ok": True,
            "mode": "code",
            "path": str(path),
            "content": text[:_MAX_PREVIEW],
            "language": "plaintext",
            "bytes": size,
            "lines": text.count("\n") + 1,
            "type_label": (ft or {}).get("label"),
        }
    # binary hex slice
    try:
        blob = path.read_bytes()[:4096]
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    lines = []
    for i in range(0, len(blob), 16):
        chunk = blob[i : i + 16]
        hexpart = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f'<span class="offset">{i:08x}</span>  {hexpart:<48}  <span class="ascii">{asc}</span>')
    return {
        "ok": True,
        "mode": "hex",
        "path": str(path),
        "bytes": size,
        "hex_html": "\n".join(lines),
        "type_label": (ft or {}).get("label") or "binary",
        "truncated": size > 4096,
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json"):
        return {"ok": True, **browser_status()}

    if action in ("roots", "list_roots"):
        return {"ok": True, "roots": _roots(), "zero_cost_4_slot": zero_cost_slice()}

    if action in ("list", "ls", "readdir"):
        raw = str(body.get("path") or body.get("dir") or SG)
        path, err = _resolve_jailed(raw)
        if err or not path:
            return {"ok": False, "error": err or "jail_denied", "zero_cost_4_slot": zero_cost_slice()}
        if not path.is_dir():
            return {"ok": False, "error": "not_a_directory", "path": str(path)}
        out = _list_dir(
            path,
            show_hidden=bool(body.get("show_hidden")),
            browse_inside=bool(body.get("browse_inside")),
        )
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action == "tree":
        raw = str(body.get("path") or SG)
        path, err = _resolve_jailed(raw)
        if err or not path or not path.is_dir():
            return {"ok": False, "error": err or "not_a_directory"}
        depth = min(4, max(1, int(body.get("depth") or 2)))
        return {
            "ok": True,
            "path": str(path),
            "tree": _tree_slice(path, depth=depth),
            "zero_cost_4_slot": zero_cost_slice(),
        }

    if action in ("stat", "info"):
        raw = str(body.get("path") or "")
        path, err = _resolve_jailed(raw)
        if err or not path:
            return {"ok": False, "error": err or "jail_denied"}
        if not path.exists():
            return {"ok": False, "error": "missing", "path": str(path)}
        if path.is_file():
            scan = _field_virus_gate(path, direction="ingress")
            if scan and not scan.get("ok"):
                return {
                    "ok": False,
                    "error": "field_virus_hold",
                    "field_virus": scan,
                    "path": str(path),
                    "zero_cost_4_slot": zero_cost_slice(),
                }
        entry = _entry_row(path)
        return {"ok": True, "entry": entry, "inspect": entry.get("file_type"), "zero_cost_4_slot": zero_cost_slice()}

    if action in ("inspect", "file_inspect"):
        raw = str(body.get("path") or "")
        path, err = _resolve_jailed(raw)
        if err or not path:
            return {"ok": False, "error": err or "jail_denied"}
        if not path.exists():
            return {"ok": False, "error": "missing", "path": str(path)}
        insp = _inspect_mod()
        if not insp:
            return {"ok": False, "error": "inspect_unavailable"}
        return {
            "ok": True,
            "path": str(path),
            "inspect": insp.inspect_file(path),
            "entry": _entry_row(path),
            "zero_cost_4_slot": zero_cost_slice(),
        }

    if action == "preview":
        raw = str(body.get("path") or "")
        path, err = _resolve_jailed(raw)
        if err or not path:
            return {"ok": False, "error": err or "jail_denied"}
        if not path.exists():
            return {"ok": False, "error": "missing", "path": str(path)}
        out = _preview_file(path)
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action in ("file_types", "types"):
        insp = _inspect_mod()
        if not insp:
            return {"ok": False, "error": "inspect_unavailable"}
        return {"ok": True, **insp.file_types_registry(), "zero_cost_4_slot": zero_cost_slice()}

    if action in ("set_type_pref", "type_pref", "toggle_type_flag"):
        insp = _inspect_mod()
        if not insp:
            return {"ok": False, "error": "inspect_unavailable"}
        tid = str(body.get("type_id") or body.get("id") or "").strip()
        key = str(body.get("key") or body.get("flag") or "").strip()
        if not tid or not key:
            return {"ok": False, "error": "type_id_and_key_required"}
        value = body.get("value")
        if body.get("toggle") and key == "compileable":
            reg = insp.file_types_registry()
            cur = (reg.get("types") or {}).get(tid, {}).get("flags", {}).get("compileable")
            value = not cur
        if body.get("toggle") and key == "on_bar":
            prefs = insp.load_type_prefs()
            pins = list(prefs.get("bar_pins") or [])
            if tid in pins:
                pins = [x for x in pins if x != tid]
            else:
                pins.append(tid)
            insp.set_bar_pins(pins)
            return {"ok": True, **insp.file_types_registry(), "zero_cost_4_slot": zero_cost_slice()}
        insp.set_type_pref(tid, key, value)
        return {"ok": True, **insp.file_types_registry(), "zero_cost_4_slot": zero_cost_slice()}

    if action in ("set_bar_pins", "bar_pins"):
        insp = _inspect_mod()
        if not insp:
            return {"ok": False, "error": "inspect_unavailable"}
        pins = body.get("pins") or body.get("bar_pins") or []
        insp.set_bar_pins(list(pins) if isinstance(pins, list) else [])
        return {"ok": True, **insp.file_types_registry(), "zero_cost_4_slot": zero_cost_slice()}

    if action in ("nes_catalog", "nes_library"):
        cat_path = QUEEN.parent / "data" / "nes-cartridge-catalog.json"
        try:
            doc = json.loads(cat_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"ok": False, "error": "nes_catalog_missing"}
        entries = list(doc.get("entries") or [])
        if body.get("rom_only"):
            entries = [e for e in entries if e.get("rom")]
        q = str(body.get("query") or body.get("q") or "").lower().strip()
        if q:
            entries = [
                e for e in entries
                if q in json.dumps(e, ensure_ascii=False).lower()
            ]
        limit = int(body.get("limit") or 48)
        return {
            "ok": True,
            "count": doc.get("count", len(entries)),
            "rom_count": doc.get("rom_count", 0),
            "entries": entries[:limit],
            "zero_cost_4_slot": zero_cost_slice(),
        }

    if action in ("program_library", "library", "library_scan", "library_search"):
        lib = _program_library_mod()
        if not lib:
            return {"ok": False, "error": "library_unavailable"}
        sub = "library_scan" if action == "library_scan" else "library_search" if action == "library_search" else "library"
        if sub == "library_scan":
            out = lib.build_library(include_host=body.get("host", True) is not False)
        elif sub == "library_search":
            out = lib.search_library(
                str(body.get("query") or body.get("q") or ""),
                limit=int(body.get("limit") or 80),
                kind=str(body.get("kind") or body.get("facet_kind") or ""),
                dewey=str(body.get("dewey") or body.get("facet_dewey") or ""),
                platform=str(body.get("platform") or body.get("facet_platform") or ""),
            )
        else:
            out = lib.library_doc()
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action in ("icon_get", "icons"):
        insp = _inspect_mod()
        if not insp:
            return {"ok": False, "error": "inspect_unavailable"}
        return {"ok": True, **insp.file_types_registry(), "zero_cost_4_slot": zero_cost_slice()}

    if action in ("icon_save", "save_icon"):
        insp = _inspect_mod()
        if not insp:
            return {"ok": False, "error": "inspect_unavailable"}
        scope = str(body.get("scope") or "type").strip().lower()
        icon = str(body.get("icon") or body.get("program_icon") or "").strip() or None
        key = str(body.get("key") or body.get("type_id") or "").strip()
        if scope == "path":
            raw = str(body.get("path") or key)
            path, err = _resolve_jailed(raw)
            if err or not path:
                return {"ok": False, "error": err or "jail_denied"}
            key = str(path)
        elif not key:
            return {"ok": False, "error": "key_required"}
        doc = insp.save_icon_override(scope=scope, key=key, program_icon=icon)
        return {"ok": True, "overrides": doc, "zero_cost_4_slot": zero_cost_slice()}

    if action in ("compile_mode", "release_compile", "compile"):
        raw = str(body.get("path") or "")
        path, err = _resolve_jailed(raw)
        if err or not path:
            return {"ok": False, "error": err or "jail_denied"}
        if not path.is_file():
            return {"ok": False, "error": "not_a_file", "path": str(path)}
        scan = _field_virus_gate(path, direction="ingress")
        if scan and not scan.get("ok"):
            return {
                "ok": False,
                "error": "field_virus_hold",
                "field_virus": scan,
                "path": str(path),
                "zero_cost_4_slot": zero_cost_slice(),
            }
        insp = _inspect_mod()
        if not insp:
            return {"ok": False, "error": "inspect_unavailable"}
        out = insp.release_compile_mode(path, profile=str(body.get("profile") or "belt_2_0"))
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action in ("run_launch", "launch_chamber", "launch_run"):
        raw = str(body.get("path") or "")
        path, err = _resolve_jailed(raw)
        if err or not path:
            return {"ok": False, "error": err or "jail_denied"}
        if path.is_file():
            scan = _field_virus_gate(path, direction="ingress")
            if scan and not scan.get("ok"):
                return {
                    "ok": False,
                    "error": "field_virus_hold",
                    "field_virus": scan,
                    "path": str(path),
                    "zero_cost_4_slot": zero_cost_slice(),
                }
        insp = _inspect_mod()
        if not insp:
            return {"ok": False, "error": "inspect_unavailable"}
        out = insp.run_launch_chamber(path, timeout=int(body.get("timeout") or 120))
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action in ("create_launch", "launch_create", "seal_launch"):
        raw = str(body.get("path") or "")
        path, err = _resolve_jailed(raw)
        if err or not path:
            return {"ok": False, "error": err or "jail_denied"}
        if not path.is_dir():
            return {"ok": False, "error": "not_a_directory", "path": str(path)}
        insp = _inspect_mod()
        if not insp:
            return {"ok": False, "error": "inspect_unavailable"}
        refresh = bool(body.get("refresh")) or not bool(body.get("lock", True))
        seal_raw = body.get("launch_seal_generation")
        seal_gen = int(seal_raw) if seal_raw is not None and str(seal_raw).strip() != "" else None
        out = insp.create_launch_file(
            path,
            lock=True,
            refresh=refresh,
            seal_generation=seal_gen,
        )
        out["launch_seal"] = _launch_seal_slice()
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action in ("run_launchable", "launch_file"):
        raw = str(body.get("path") or "")
        path, err = _resolve_jailed(raw)
        if err or not path or not path.is_file():
            return {"ok": False, "error": err or "not_a_file"}
        ch = _chamber_mod()
        if not ch:
            return {"ok": False, "error": "chamber_unavailable"}
        root = path.parent
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            return {"ok": False, "error": "outside_chamber"}
        manifest = ch.build_manifest_fast(root)
        manifest["entry"] = rel
        manifest["runtime"] = ch._runtime_for_entry(path.name)
        tmp_launch = STATE / "launch-one-shot" / f"{root.name}.launch"
        tmp_launch.parent.mkdir(parents=True, exist_ok=True)
        tmp_launch.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        out = insp.run_launch_chamber(tmp_launch, timeout=int(body.get("timeout") or 120))
        out["launchable"] = rel
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action in ("dock", "dock_get"):
        return {"ok": True, "dock": load_dock(), "zero_cost_4_slot": zero_cost_slice()}

    if action in ("dock_push", "dock_pin"):
        raw = str(body.get("path") or "")
        out = dock_push(raw, label=str(body.get("label") or "") or None)
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action in ("dock_save",):
        slots = body.get("slots")
        if not isinstance(slots, list):
            return {"ok": False, "error": "slots_required"}
        doc = save_dock(slots)
        return {"ok": True, "dock": doc, "zero_cost_4_slot": zero_cost_slice()}

    if action in ("nav_get",):
        return {"ok": True, "nav": load_nav(), "zero_cost_4_slot": zero_cost_slice()}

    if action in ("nav_push",):
        out = nav_push(str(body.get("path") or ""))
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action in ("nav_back",):
        out = nav_step(-1)
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action in ("nav_forward",):
        out = nav_step(1)
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action in ("launch", "launch_spv", "run_spv"):
        raw = str(body.get("path") or "")
        path, err = _resolve_jailed(raw)
        if err or not path:
            return {"ok": False, "error": err or "jail_denied"}
        if not path.is_file():
            return {"ok": False, "error": "not_a_file", "path": str(path)}
        scan = _field_virus_gate(path, direction="ingress")
        if scan and not scan.get("ok"):
            return {
                "ok": False,
                "error": "field_virus_hold",
                "field_virus": scan,
                "path": str(path),
                "zero_cost_4_slot": zero_cost_slice(),
            }
        insp = _inspect_mod()
        if not insp:
            return {"ok": False, "error": "inspect_unavailable"}
        out = insp.launch_spv(path)
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action in ("scan", "virus_scan", "field_virus"):
        raw = str(body.get("path") or "")
        path, err = _resolve_jailed(raw)
        if err or not path:
            return {"ok": False, "error": err or "jail_denied"}
        scan = _field_virus_gate(path, direction=str(body.get("direction") or "ingress"))
        if scan is None:
            return {"ok": False, "error": "field_virus_unavailable"}
        return {"ok": scan.get("ok", False), "field_virus": scan, "zero_cost_4_slot": zero_cost_slice()}

    if action in ("hotbar", "hotbar_get"):
        return {"ok": True, "hotbar": load_hotbar(), "zero_cost_4_slot": zero_cost_slice()}

    if action in ("hotbar_save", "save_hotbar", "wishlist_save"):
        slots = body.get("slots")
        if not isinstance(slots, list):
            return {"ok": False, "error": "slots_required"}
        doc = save_hotbar(slots)
        return {"ok": True, "hotbar": doc, "wishlist": doc, "zero_cost_4_slot": zero_cost_slice()}

    if action in ("search", "find", "wishlist_search"):
        policy = _wishlist_policy()
        if not policy.get("search_enabled", True):
            return {"ok": False, "error": "search_disabled"}
        raw = str(body.get("path") or body.get("root") or SG)
        path, err = _resolve_jailed(raw)
        if err or not path or not path.is_dir():
            return {"ok": False, "error": err or "not_a_directory"}
        query = str(body.get("query") or body.get("q") or "").strip()
        depth = min(6, max(1, int(body.get("depth") or policy.get("search_max_depth") or 4)))
        limit = min(500, max(1, int(body.get("limit") or policy.get("search_max_hits") or 200)))
        hits = _search_tree(path, query, depth=depth, limit=limit)
        return {
            "ok": True,
            "path": str(path),
            "query": query,
            "hits": hits,
            "count": len(hits),
            "truncated": len(hits) >= limit,
            "zero_cost_4_slot": zero_cost_slice(),
        }

    if action in ("mkdir", "wishlist_mkdir"):
        policy = _wishlist_policy()
        if not policy.get("mkdir_enabled", True):
            return {"ok": False, "error": "mkdir_disabled"}
        parent = str(body.get("path") or body.get("parent") or body.get("dir") or SG)
        name = str(body.get("name") or body.get("folder") or "")
        out = _mkdir_jailed(parent, name)
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action == "resolve":
        raw = str(body.get("path") or "")
        path, err = _resolve_jailed(raw)
        if err or not path:
            return {"ok": False, "error": err or "jail_denied"}
        return {"ok": True, "resolved": str(path), "entry": _entry_row(path) if path.exists() else None}

    if action in ("always_resolve", "always_properties", "always_menu", "always_properties_menu"):
        raw = str(body.get("path") or "")
        path, err = _resolve_jailed(raw)
        if err or not path:
            return {"ok": False, "error": err or "jail_denied"}
        mod = _always_files_mod()
        if not mod:
            return {"ok": False, "error": "always_files_missing"}
        try:
            af = mod.resolve(str(path), compute_hash=bool(body.get("hash")), inspect=True)
            menu = mod.properties_menu(af) if hasattr(mod, "properties_menu") else {}
            sec = mod.system_security(af=af) if hasattr(mod, "system_security") else {}
            entry = _maybe_enrich_row(_entry_row(path) if path.exists() else {"path": str(path), "name": path.name, "kind": "ghost"})
            return {
                "ok": True,
                "path": str(path),
                "always_file": af,
                "properties_menu": menu,
                "security": sec,
                "entry": entry,
                "zero_cost_4_slot": zero_cost_slice(),
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:160]}

    if action in ("always_checkpoint", "timeshift_checkpoint"):
        mod = _always_files_mod()
        if not mod or not hasattr(mod, "dispatch"):
            return {"ok": False, "error": "always_files_missing"}
        note = str(body.get("note") or body.get("path") or "queen-files checkpoint")[:120]
        out = mod.dispatch({"action": "timeshift_checkpoint", "note": note})
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action in ("always_timeshift_list", "timeshift_list"):
        mod = _always_files_mod()
        if not mod or not hasattr(mod, "dispatch"):
            return {"ok": False, "error": "always_files_missing"}
        out = mod.dispatch({"action": "timeshift_list"})
        out["zero_cost_4_slot"] = zero_cost_slice()
        return out

    if action == "verify_jail":
        samples = [
            str(SG),
            "SG/NewLatest/Queen",
            "queen://files/sg",
            "../../../etc/passwd",
            "/etc/passwd",
        ]
        results = []
        for s in samples:
            p, e = _resolve_jailed(s)
            results.append({"input": s, "ok": e is None, "path": str(p) if p else None, "error": e})
        return {"ok": True, "samples": results, "zero_cost_4_slot": zero_cost_slice()}

    return {"ok": False, "error": "unknown_action", "actions": [
        "status", "list", "tree", "stat", "inspect", "file_types", "icon_get", "icon_save",
        "set_type_pref", "set_bar_pins", "program_library", "library_scan", "library_search",
        "compile_mode", "run_launch", "run_launchable", "create_launch", "launch",
        "dock", "dock_push", "dock_save", "nav_get", "nav_push", "nav_back", "nav_forward",
        "scan", "hotbar", "hotbar_save", "wishlist_save", "search", "mkdir", "resolve", "verify_jail",
        "always_properties", "always_checkpoint", "always_timeshift_list",
    ]}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(browser_status(), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-file-browser.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())