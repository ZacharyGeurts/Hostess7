#!/usr/bin/env pythong
"""AmmoOS Theme Engine — single index for Queen Styles, C2 shell, editor, file-type properties."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL / "Queen"))
DOCTRINE = INSTALL / "data" / "ammoos-themes-doctrine.json"
PREFS_PATH = STATE / "ammoos-themes.json"
SHELL_SETTINGS = STATE / "field-shell-settings.json"

SURFACES = frozenset({"auto", "window", "browser"})


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


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {"default_ammoos_theme": "nexus_c2", "default_queen_styles": "black_emerald_rose_2026"})


def _queen_styles_catalog() -> dict[str, Any]:
    for rel in ("Queen/gui/queen-styles-themes.json", "gui/queen-styles-themes.json"):
        path = INSTALL / rel if rel.startswith("Queen") else QUEEN / rel.split("/", 1)[-1]
        if not path.is_file() and rel.startswith("Queen"):
            path = QUEEN / "gui" / "queen-styles-themes.json"
        if path.is_file():
            return _load(path, {})
    return {"themes": [], "default": "black_emerald_rose_2026"}


def _editor_catalog() -> dict[str, Any]:
    for path in (INSTALL / "AmmoCode/data/ammocode-syntax-themes.json", INSTALL / "data/ammocode-syntax-themes.json"):
        if path.is_file():
            return _load(path, {})
    return {"editor_themes": {}, "syntax_themes": {}}


def _file_types_registry() -> dict[str, Any]:
    path = QUEEN / "data" / "queen-file-types.json"
    doc = _load(path, {})
    return doc.get("types") or {}


def _program_surface_prefs() -> dict[str, Any]:
    path = STATE / "queen-program-surface.json"
    doc = _load(path, {})
    return doc.get("programs") or {}


def _program_catalog() -> dict[str, dict[str, Any]]:
    script = QUEEN / "lib" / "queen-program-surface.py"
    if not script.is_file():
        return {}
    try:
        spec = importlib.util.spec_from_file_location("qps_theme", script)
        if not spec or not spec.loader:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "_catalog"):
            return mod._catalog()
    except Exception:
        pass
    return {}


def _prefs() -> dict[str, Any]:
    doc = _load(PREFS_PATH, {})
    doctrine = _doctrine()
    return {
        "schema": "ammoos-themes-prefs/v1",
        "active_c2": doc.get("active_c2") or doctrine.get("default_ammoos_theme") or "nexus_c2",
        "active_queen_styles": doc.get("active_queen_styles") or doctrine.get("default_queen_styles") or "black_emerald_rose_2026",
        "active_editor": doc.get("active_editor") or doctrine.get("default_editor_theme") or "nexus_c2",
        "active_syntax": doc.get("active_syntax") or doctrine.get("default_syntax_theme") or "nexus_c2",
        "active_terminal": doc.get("active_terminal") or doctrine.get("default_terminal_theme") or "black_emerald_rose_2026",
        "shell_theme": doc.get("shell_theme") or "",
        "wallpaper": doc.get("wallpaper") or "default",
        "custom_queen_styles": doc.get("custom_queen_styles") or [],
        "file_types": doc.get("file_types") or {},
        "programs": doc.get("programs") or {},
        "ts": doc.get("ts") or _now(),
    }


def _merge_file_type_rules() -> list[dict[str, Any]]:
    registry = _file_types_registry()
    prefs = _prefs().get("file_types") or {}
    defaults = (_doctrine().get("file_type_defaults") or {})
    out: list[dict[str, Any]] = []
    for tid, spec in sorted(registry.items(), key=lambda x: x[1].get("label") or x[0]):
        exts = [str(e).lower() for e in (spec.get("extensions") or [])]
        user = prefs.get(tid) or prefs.get(exts[0].lstrip(".") if exts else "") or {}
        out.append({
            "type_id": tid,
            "label": spec.get("label") or tid,
            "extensions": exts,
            "default_open_with": spec.get("open_with"),
            "default_action": spec.get("action"),
            "open_with": user.get("open_with") or defaults.get("open_with") or spec.get("open_with") or "inherit",
            "surface": user.get("surface") or defaults.get("surface") or "auto",
            "show_in_context": user.get("show_in_context", defaults.get("show_in_context", True)),
            "properties_sections": user.get("properties_sections") or defaults.get("properties_sections") or [
                "general", "launch", "always", "security",
            ],
            "icon": user.get("icon") or spec.get("program_icon") or spec.get("global_icon"),
            "compileable": bool(spec.get("compileable")),
        })
    return out


def catalog() -> dict[str, Any]:
    doctrine = _doctrine()
    prefs = _prefs()
    queen_doc = _queen_styles_catalog()
    editor_doc = _editor_catalog()
    c2 = doctrine.get("c2_themes") or {}
    custom = prefs.get("custom_queen_styles") or []
    queen_themes = list(queen_doc.get("themes") or []) + list(custom)
    programs = _program_catalog()
    prog_prefs = _program_surface_prefs()
    program_rows = [
        {
            "id": pid,
            "name": p.get("name") or pid,
            "default_surface": p.get("default_surface") or "auto",
            "user_surface": (prog_prefs.get(pid) or {}).get("surface")
            or (prefs.get("programs") or {}).get(pid, {}).get("surface"),
        }
        for pid, p in sorted(programs.items(), key=lambda x: x[1].get("name") or x[0])
    ]
    return {
        "ok": True,
        "schema": doctrine.get("schema") or "ammoos-themes/v1",
        "title": doctrine.get("title") or "AmmoOS Themes",
        "motto": doctrine.get("motto"),
        "control_panel_index": doctrine.get("control_panel_index") or "/control-panel?tab=themes",
        "default_ammoos_theme": doctrine.get("default_ammoos_theme") or "nexus_c2",
        "active": {
            "c2": prefs.get("active_c2"),
            "queen_styles": prefs.get("active_queen_styles"),
            "editor": prefs.get("active_editor"),
            "syntax": prefs.get("active_syntax"),
            "terminal": prefs.get("active_terminal"),
            "shell_theme": prefs.get("shell_theme"),
            "wallpaper": prefs.get("wallpaper"),
        },
        "sections": doctrine.get("sections") or [],
        "engines": doctrine.get("engines") or {},
        "c2_themes": c2,
        "shell_themes": doctrine.get("shell_themes") or {},
        "surface_options": doctrine.get("surface_options") or [],
        "queen_styles": {
            "catalog": queen_doc.get("schema") or "queen-styles-themes/v1",
            "default": queen_doc.get("default") or doctrine.get("default_queen_styles"),
            "themes": queen_themes,
            "custom_count": len(custom),
        },
        "editor": {
            "default_editor": editor_doc.get("default_editor_theme"),
            "default_syntax": editor_doc.get("default_syntax_theme"),
            "editor_themes": editor_doc.get("editor_themes") or {},
            "syntax_themes": editor_doc.get("syntax_themes") or {},
        },
        "file_types": _merge_file_type_rules(),
        "programs": program_rows,
        "ts": _now(),
    }


def default_posture() -> dict[str, Any]:
    cat = catalog()
    active_c2 = cat["active"]["c2"]
    c2_meta = (cat.get("c2_themes") or {}).get(active_c2) or {}
    return {
        "ok": True,
        "schema": "ammoos-themes-default/v1",
        "default_ammoos_theme": cat.get("default_ammoos_theme") or "nexus_c2",
        "active_c2": active_c2,
        "active_c2_label": c2_meta.get("label") or active_c2,
        "active_queen_styles": cat["active"]["queen_styles"],
        "data_attr": c2_meta.get("data_attr") or "nexus-military-v8",
        "css": c2_meta.get("css") or "panel/assets/ammoos-c2-themes.css",
        "vars": c2_meta.get("vars") or {},
        "ts": _now(),
    }


def file_type_rule(type_id: str) -> dict[str, Any] | None:
    for row in _merge_file_type_rules():
        if row.get("type_id") == type_id:
            return row
    return None


def properties_menu_for_file(af: dict[str, Any]) -> dict[str, Any]:
    """Theme-index slice for Always Files right-click properties."""
    typ = af.get("type") or {}
    tid = str(typ.get("type_id") or "unknown")
    rule = file_type_rule(tid) or {}
    prefs = _prefs()
    doctrine = _doctrine()
    sections = list(rule.get("properties_sections") or [])
    launch_fields = [
        {"label": "Open with", "value": rule.get("open_with") or typ.get("open_with") or "—"},
        {"label": "Launch surface", "value": rule.get("surface") or "auto"},
        {"label": "Default action", "value": typ.get("action") or rule.get("default_action")},
        {"label": "Theme index", "value": doctrine.get("control_panel_index"), "link": doctrine.get("control_panel_index")},
    ]
    return {
        "id": "theme_file_type",
        "title": "File type & launch",
        "hint": "Edit in Queen Settings → Themes → File types",
        "type_id": tid,
        "fields": launch_fields,
        "surface_options": doctrine.get("surface_options") or [],
        "rule": rule,
        "active_queen_styles": prefs.get("active_queen_styles"),
        "sections_enabled": sections,
    }


def apply_patch(patch: dict[str, Any]) -> dict[str, Any]:
    prefs = _prefs()
    changed: list[str] = []

    for key, dest in (
        ("active_c2", "active_c2"),
        ("c2_theme", "active_c2"),
        ("active_queen_styles", "active_queen_styles"),
        ("queen_styles", "active_queen_styles"),
        ("active_editor", "active_editor"),
        ("editor_theme", "active_editor"),
        ("active_syntax", "active_syntax"),
        ("syntax_theme", "active_syntax"),
        ("active_terminal", "active_terminal"),
        ("terminal_theme", "active_terminal"),
        ("shell_theme", "shell_theme"),
        ("theme_override", "shell_theme"),
        ("wallpaper", "wallpaper"),
    ):
        if key in patch and patch[key] is not None:
            prefs[dest] = str(patch[key])
            changed.append(dest)

    if "custom_queen_styles" in patch and isinstance(patch["custom_queen_styles"], list):
        prefs["custom_queen_styles"] = patch["custom_queen_styles"]
        changed.append("custom_queen_styles")

    if "file_type" in patch and isinstance(patch["file_type"], dict):
        ft = patch["file_type"]
        tid = str(ft.get("type_id") or "").strip()
        if tid:
            rules = prefs.setdefault("file_types", {})
            row = dict(rules.get(tid) or {})
            for k in ("open_with", "surface", "icon", "show_in_context", "properties_sections"):
                if k in ft:
                    row[k] = ft[k]
            if row.get("surface") not in SURFACES:
                row["surface"] = "auto"
            rules[tid] = row
            changed.append(f"file_types.{tid}")

    if "program" in patch and isinstance(patch["program"], dict):
        pid = str(patch["program"].get("id") or patch["program"].get("program_id") or "").strip()
        if pid:
            progs = prefs.setdefault("programs", {})
            row = dict(progs.get(pid) or {})
            if "surface" in patch["program"]:
                surf = str(patch["program"]["surface"])
                row["surface"] = surf if surf in SURFACES else "auto"
            progs[pid] = row
            changed.append(f"programs.{pid}")
            script = QUEEN / "lib" / "queen-program-surface.py"
            if script.is_file() and row.get("surface"):
                try:
                    spec = importlib.util.spec_from_file_location("qps_apply", script)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        if hasattr(mod, "dispatch"):
                            mod.dispatch({
                                "action": "set_surface",
                                "program_id": pid,
                                "surface": row["surface"],
                            })
                except Exception:
                    pass

    prefs["ts"] = _now()
    _save_atomic(PREFS_PATH, prefs)

    shell_patch: dict[str, Any] = {}
    if "shell_theme" in changed or "active_c2" in changed:
        shell_patch["ammoos_theme"] = prefs.get("active_c2")
    if prefs.get("shell_theme") is not None:
        shell_patch["theme_override"] = prefs.get("shell_theme") or ""
    if prefs.get("wallpaper"):
        shell_patch["wallpaper"] = prefs.get("wallpaper")
    if shell_patch:
        shell_doc = _load(SHELL_SETTINGS, {})
        shell_doc.update({k: v for k, v in shell_patch.items()})
        shell_doc["ts"] = _now()
        _save_atomic(SHELL_SETTINGS, shell_doc)

    out = catalog()
    out["applied"] = changed
    out["ok"] = True
    return out


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "catalog").strip().lower()
    if action in ("catalog", "index", "json"):
        return catalog()
    if action in ("default", "posture"):
        return default_posture()
    if action == "file_type_properties":
        af = body.get("always_file") or body.get("af") or {}
        return {"ok": True, "section": properties_menu_for_file(af)}
    if action == "apply":
        return apply_patch(body.get("patch") or body)
    if action == "patch":
        return apply_patch(body)
    if action == "get_file_type":
        tid = str(body.get("type_id") or "").strip()
        row = file_type_rule(tid)
        return {"ok": bool(row), "file_type": row}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "catalog").strip().lower()
    if cmd in ("catalog", "index"):
        print(json.dumps(catalog(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("default", "posture"):
        print(json.dumps(default_posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read() if not sys.stdin.isatty() else (sys.argv[2] if len(sys.argv) > 2 else "{}")
        try:
            body = json.loads(raw or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "invalid_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False, indent=2))
        return 0
    if cmd == "apply":
        raw = sys.stdin.read() if not sys.stdin.isatty() else (sys.argv[2] if len(sys.argv) > 2 else "{}")
        try:
            patch = json.loads(raw or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "invalid_json"}))
            return 1
        print(json.dumps(apply_patch(patch), ensure_ascii=False, indent=2))
        return 0
    print("usage: ammoos-theme-engine.py [catalog|default|dispatch|apply]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())