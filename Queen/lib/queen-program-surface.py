#!/usr/bin/env pythong
"""Queen Program Surface — all Queen software; Window vs Browser is operator choice only."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", SG / "NewLatest"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
DOCTRINE = QUEEN / "data" / "queen-program-surface-doctrine.json"
PREFS_PATH = STATE / "queen-program-surface.json"

SURFACES = frozenset({"window", "browser", "auto"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _world_base() -> str:
    port = os.environ.get("QUEEN_WORLD_PORT", "9481")
    return f"http://127.0.0.1:{port}"


def _desktop_mod() -> Any:
    spec = importlib.util.spec_from_file_location("queen_desktop", QUEEN / "lib" / "queen-desktop.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _field_net_resolve(url: str) -> str:
    script = QUEEN / "lib" / "queen-field-net.py"
    if not script.is_file():
        return url
    try:
        spec = importlib.util.spec_from_file_location("queen_field_net", script)
        if not spec or not spec.loader:
            return url
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        doc = mod.dispatch({"action": "resolve", "url": url})
        if doc.get("ok"):
            return str(doc.get("resolved") or doc.get("url") or url)
    except Exception:
        pass
    return url


def _normalize_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return f"{_world_base()}/world/browser.html"
    if u.startswith("/"):
        return f"{_world_base()}{u}"
    return u


def _default_surface_for(prog: dict[str, Any]) -> str:
    if prog.get("default_surface") in SURFACES:
        return str(prog["default_surface"])
    url = str(prog.get("url") or "")
    if prog.get("id") == "browser":
        return "browser"
    if url.startswith("queen://"):
        return "browser"
    if ":9477/" in url or url.startswith("http://127.0.0.1:9477"):
        return "browser"
    return "window"


def _catalog() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    desk = _desktop_mod()
    programs = list(getattr(desk, "CLASSIC_PROGRAMS", ()) or []) if desk else []
    for raw in programs:
        pid = str(raw.get("id") or "").strip()
        if not pid:
            continue
        url = _normalize_url(str(raw.get("url") or ""))
        browser_url = url
        window_url = url
        if url.endswith("/browser.html") or "/world/browser.html" in url:
            window_url = url + ("&" if "?" in url else "?") + "desktop_embed=1"
        if str(raw.get("url") or "").startswith("queen://"):
            resolved = _field_net_resolve(str(raw.get("url")))
            browser_url = _normalize_url(resolved) if resolved.startswith("/") else resolved
            window_url = browser_url
        out[pid] = {
            "id": pid,
            "name": raw.get("name") or pid,
            "kind": raw.get("kind") or "program",
            "category": raw.get("category") or "Queen",
            "menu_folder": raw.get("menu_folder") or "os",
            "url": str(raw.get("url") or ""),
            "browser_url": browser_url,
            "window_url": window_url,
            "icon": raw.get("icon"),
            "queen_software": True,
            "interchangeable": True,
            "default_surface": _default_surface_for(raw),
            "dock": _dock_for_url(str(raw.get("url") or "")),
            "legacy_id": raw.get("legacy_id"),
        }
    return out


def _dock_for_url(url: str) -> str | None:
    u = (url or "").strip()
    if u == "queen://terminal" or "dock=terminal" in u:
        return "terminal"
    if u == "queen://gameroom" or "gameroom" in u:
        return "gameroom"
    if u == "queen://kilroy" or "dock=kilroy" in u:
        return "kilroy"
    if u == "queen://hostess" or "dock=hostess" in u:
        return "hostess"
    if u == "queen://eyeball" or "dock=eyeball" in u:
        return "eyeball"
    if u == "queen://earball" or "dock=earball" in u:
        return "earball"
    if u == "queen://field" or "dock=field" in u:
        return "field"
    if u == "queen://chips":
        return "browser"
    return None


def _prefs() -> dict[str, Any]:
    doc = _load(PREFS_PATH, {"schema": "queen-program-surface-prefs/v1", "programs": {}})
    if not isinstance(doc.get("programs"), dict):
        doc["programs"] = {}
    return doc


def _user_surface(program_id: str) -> str | None:
    pref = (_prefs().get("programs") or {}).get(program_id)
    if isinstance(pref, dict):
        s = str(pref.get("surface") or "").strip()
        return s if s in SURFACES else None
    return None


def resolve_surface(program_id: str, override: str | None = None) -> str:
    if override and override in SURFACES and override != "auto":
        return override
    user = _user_surface(program_id)
    if user and user != "auto":
        return user
    prog = _catalog().get(program_id)
    if not prog:
        return "browser"
    default = prog.get("default_surface") or "window"
    return default if default != "auto" else "window"


def resolve_launch(program_id: str, *, surface: str | None = None, new_tab: bool = False) -> dict[str, Any]:
    prog = _catalog().get(program_id)
    if not prog:
        return {"ok": False, "error": "unknown_program", "program_id": program_id}
    surf = resolve_surface(program_id, surface)
    if surf == "browser":
        launch_url = prog.get("browser_url") or prog.get("url")
        launch_mode = "queen_browser_tab" if new_tab else "queen_browser"
    else:
        launch_url = prog.get("window_url") or prog.get("browser_url") or prog.get("url")
        launch_mode = "queen_window"
    dock = prog.get("dock")
    if dock and surf == "browser" and not new_tab and str(prog.get("url") or "").startswith("queen://"):
        launch_url = f"{_world_base()}/world/?dock={dock}"
    return {
        "ok": True,
        "program_id": program_id,
        "name": prog.get("name"),
        "surface": surf,
        "launch_mode": launch_mode,
        "launch_url": launch_url,
        "new_tab": bool(new_tab),
        "dock": dock,
        "queen_software": True,
    }


def _field(label: str, value: Any, **extra: Any) -> dict[str, Any]:
    row = {"label": label, "value": value if value is not None and value != "" else "—"}
    row.update(extra)
    return row


def properties_menu(program_id: str) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    prog = _catalog().get(program_id)
    if not prog:
        return {"ok": False, "error": "unknown_program", "program_id": program_id}

    user_surf = _user_surface(program_id) or "auto"
    effective = resolve_surface(program_id)
    surf_meta = doctrine.get("surfaces") or {}

    sections = [
        {
            "id": "general",
            "title": "General",
            "fields": [
                _field("Name", prog.get("name")),
                _field("Program ID", program_id, mono=True, copy=True),
                _field("Kind", prog.get("kind")),
                _field("Category", prog.get("category")),
                _field("Menu folder", prog.get("menu_folder")),
                _field("Queen software", "Yes — sole product family"),
            ],
        },
        {
            "id": "launch",
            "title": "Launch surface",
            "banner": doctrine.get("motto"),
            "fields": [
                _field("Default surface", surf_meta.get(prog.get("default_surface"), {}).get("label") or prog.get("default_surface")),
                _field("Your preference", surf_meta.get(user_surf, {}).get("label") or user_surf),
                _field("Effective now", surf_meta.get(effective, {}).get("label") or effective),
                _field("Interchangeable", "Yes — Window ↔ Browser"),
                _field("Queen Window URL", prog.get("window_url"), mono=True, copy=True),
                _field("Queen Browser URL", prog.get("browser_url"), mono=True, copy=True),
                _field("Protocol URL", prog.get("url"), mono=True, copy=True),
                _field("Dock target", prog.get("dock")),
            ],
            "surface_options": [
                {"id": "auto", "label": "Remember last", "selected": user_surf == "auto"},
                {"id": "window", "label": "Queen Window", "selected": user_surf == "window"},
                {"id": "browser", "label": "Queen Browser", "selected": user_surf == "browser"},
            ],
        },
        {
            "id": "queen",
            "title": "Queen stack",
            "fields": [
                _field("World port", os.environ.get("QUEEN_WORLD_PORT", "9481")),
                _field("Panel port", os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")),
                _field("Icon", prog.get("icon")),
                _field("Legacy ID", prog.get("legacy_id")),
                _field("Schema", "queen-program-surface/v1"),
            ],
        },
        {
            "id": "security",
            "title": "Security",
            "banner": "Queen sovereign shell — no host browser hook",
            "fields": [
                _field("Gates", "Held at Queen Browser boot"),
                _field("Host mirror", "Disabled — AmmoOS C2 only"),
                _field("Launch seal", "field-native"),
            ],
        },
    ]

    base = _world_base()
    actions = [
        {"id": "open", "label": "Open", "group": "launch", "ui": "open", "primary": True},
        {"id": "open_window", "label": "Open in Queen Window", "group": "launch", "ui": "open_window"},
        {"id": "open_browser", "label": "Open in Queen Browser", "group": "launch", "ui": "open_browser"},
        {"id": "open_browser_tab", "label": "Open in new browser tab", "group": "launch", "ui": "open_browser_tab"},
        {"id": "properties", "label": "Properties…", "group": "file", "ui": "properties"},
        {"id": "surface_auto", "label": "Prefer: Remember last", "group": "surface", "ui": "surface_auto"},
        {"id": "surface_window", "label": "Prefer: Queen Window", "group": "surface", "ui": "surface_window"},
        {"id": "surface_browser", "label": "Prefer: Queen Browser", "group": "surface", "ui": "surface_browser"},
        {"id": "copy_window_url", "label": "Copy Window URL", "group": "clipboard", "ui": "copy_window_url"},
        {"id": "copy_browser_url", "label": "Copy Browser URL", "group": "clipboard", "ui": "copy_browser_url"},
        {
            "id": "api_launch",
            "label": "Launch API",
            "group": "links",
            "href": f"{base}/api/queen-program-surface",
            "external": True,
        },
        {
            "id": "desktop_json",
            "label": "Desktop posture",
            "group": "links",
            "href": f"{base}/api/queen-desktop",
            "external": True,
        },
    ]

    context_groups = [
        {"id": "launch", "title": "Open", "items": ["open", "open_window", "open_browser", "open_browser_tab"]},
        {"id": "surface", "title": "Launch preference", "hint": "Both surfaces run the same Queen program", "items": [
            "surface_auto", "surface_window", "surface_browser",
        ]},
        {"id": "file", "title": "Program", "items": ["properties"]},
        {"id": "clipboard", "title": "Clipboard", "items": ["copy_window_url", "copy_browser_url"]},
        {"id": "links", "title": "Links", "items": ["api_launch", "desktop_json"]},
    ]

    return {
        "ok": True,
        "schema": "queen-program-properties/v1",
        "program_id": program_id,
        "name": prog.get("name"),
        "queen_software": True,
        "program": prog,
        "effective_surface": effective,
        "user_surface": user_surf,
        "sections": sections,
        "actions": actions,
        "context_groups": context_groups,
        "updated": _now(),
    }


def posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    catalog = _catalog()
    return {
        "ok": True,
        "schema": "queen-program-surface/v1",
        "motto": doctrine.get("motto"),
        "queen_software_only": True,
        "interchangeable": True,
        "surfaces": doctrine.get("surfaces") or {},
        "program_count": len(catalog),
        "programs": [
            {"id": p["id"], "name": p["name"], "default_surface": p.get("default_surface"), "dock": p.get("dock")}
            for p in catalog.values()
        ],
        "prefs_path": str(PREFS_PATH),
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "posture"):
        return posture()

    program_id = str(body.get("program_id") or body.get("id") or "").strip()

    if action in ("properties", "properties_menu", "menu"):
        if not program_id:
            return {"ok": False, "error": "program_id_required"}
        return properties_menu(program_id)

    if action == "set_surface":
        if not program_id:
            return {"ok": False, "error": "program_id_required"}
        surf = str(body.get("surface") or "auto").strip()
        if surf not in SURFACES:
            return {"ok": False, "error": "invalid_surface", "surface": surf}
        doc = _prefs()
        doc.setdefault("programs", {})[program_id] = {"surface": surf, "updated": _now()}
        doc["updated"] = _now()
        _save(PREFS_PATH, doc)
        return {**properties_menu(program_id), "surface_saved": surf}

    if action == "resolve_launch":
        if not program_id:
            return {"ok": False, "error": "program_id_required"}
        return resolve_launch(
            program_id,
            surface=str(body.get("surface") or "").strip() or None,
            new_tab=bool(body.get("new_tab")),
        )

    if action == "catalog":
        return {"ok": True, "programs": list(_catalog().values())}

    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(posture(), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "properties" and len(sys.argv) > 2:
        print(json.dumps(properties_menu(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(dispatch({"action": cmd}), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())