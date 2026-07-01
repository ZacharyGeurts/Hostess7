#!/usr/bin/env pythong
"""AmmoOS host desktop — programs, start menu, themes, icons. Grok16 5.1.0 field stamp."""
from __future__ import annotations

import base64
import configparser
import json
import mimetypes
import os
import platform
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-host-desktop-doctrine.json"
SYSTEM_REGISTRY = INSTALL / "data" / "system" / "field-desktop-registry.json"
PANEL_FILE = STATE / "field-host-desktop.json"
STAMP = STATE / "field-host-desktop.stamp"
BOOT_MARKER = STATE / "boot-impl.last"
ICON_CACHE = STATE / "field-host-desktop-icons"

DESKTOP_SKIP = frozenset({"Hidden", "NoDisplay", "DBusActivatable"})
ICON_EXTS = (".png", ".svg", ".xpm", ".jpg", ".jpeg", ".webp")
HOST_BROWSER_MARKERS = (
    "firefox",
    "mozilla",
    "org.mozilla",
    "chromium",
    "chrome",
    "brave",
    "vivaldi",
    "waterfox",
    "librewolf",
)
HOST_BROWSER_ICON = "queen-prog-browser"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _expand(path_text: str) -> Path:
    text = path_text.replace("HOME", str(Path.home()))
    return Path(text).expanduser()


def _guest_system() -> str:
    override = os.environ.get("NEXUS_GUEST_OS_THEME", "").strip().lower()
    if override in ("windows", "linux", "darwin", "macos"):
        return "darwin" if override == "macos" else override
    system = platform.system().lower()
    if "windows" in system:
        return "windows"
    if "darwin" in system:
        return "darwin"
    return "linux"


_THEME_ALIASES = {
    "gnome": "ammo-field",
    "windows11": "ammo-c2",
    "windows10": "ammo-c2",
    "kde": "ammo-deep",
    "macos": "ammo-rose",
    "cinnamon": "ammo-field",
    "xfce": "ammo-field",
}


def _normalize_theme(theme: str) -> str:
    t = str(theme or "").strip()
    return _THEME_ALIASES.get(t, t or "ammo-field")


def _theme_id() -> str:
    doctrine = _load(DOCTRINE, {})
    themes = doctrine.get("themes") or {}
    guest = _guest_system()
    if guest == "windows":
        return _normalize_theme(os.environ.get("NEXUS_START_MENU_THEME", themes.get("windows", "ammo-c2")))
    if guest == "darwin":
        return _normalize_theme(themes.get("darwin", "ammo-rose"))
    policy = doctrine.get("policy") or {}
    if policy.get("default_os_theme"):
        return _normalize_theme(str(policy["default_os_theme"]))
    return _normalize_theme(themes.get("linux", "ammo-c2"))


def _parse_desktop(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.optionxform = str  # type: ignore[method-assign]
    try:
        cfg.read_string(raw)
    except configparser.Error:
        return None
    if not cfg.has_section("Desktop Entry"):
        return None
    sec = cfg["Desktop Entry"]
    if sec.get("Type", "Application") != "Application":
        return None
    if sec.get("Hidden", "").lower() == "true":
        return None
    if sec.get("NoDisplay", "").lower() == "true":
        return None
    name = (sec.get("Name") or sec.get("GenericName") or path.stem).strip()
    if not name:
        return None
    exec_line = (sec.get("Exec") or "").strip()
    if not exec_line:
        return None
    exec_line = re.sub(r"%[fFuUdDnNickvm]", "", exec_line).strip()
    icon = (sec.get("Icon") or "").strip() or path.stem
    categories = [c.strip() for c in (sec.get("Categories") or "").split(";") if c.strip()]
    return {
        "id": f"desktop-{path.stem}",
        "name": name,
        "exec": exec_line,
        "icon": icon,
        "icon_key": f"{path.stem}:{icon}",
        "category": categories[0] if categories else "Other",
        "categories": categories,
        "source": "desktop_entry",
        "desktop_path": str(path),
        "terminal": sec.get("Terminal", "false").lower() == "true",
    }


def _queen_asset_dirs() -> list[Path]:
    roots = [
        INSTALL / "Queen" / "world" / "assets" / "icons",
        INSTALL / "Queen" / "world" / "assets" / "branding",
        INSTALL / "panel" / "assets",
        INSTALL / "assets",
    ]
    out: list[Path] = []
    for p in roots:
        if p.is_dir() and p not in out:
            out.append(p)
    return out


def _icon_search_dirs() -> list[Path]:
    doctrine = _load(DOCTRINE, {})
    out: list[Path] = []
    for item in doctrine.get("icon_theme_dirs") or []:
        p = _expand(str(item))
        if p.is_dir() and p not in out:
            out.append(p)
    for extra in (
        Path("/usr/share/icons"),
        Path.home() / ".local/share/icons",
        Path("/usr/share/pixmaps"),
    ):
        if extra.is_dir() and extra not in out:
            out.append(extra)
    return out


def _resolve_icon_file(icon_name: str, desktop_path: str | None = None) -> Path | None:
    if not icon_name:
        return None
    icon_path = Path(icon_name)
    if icon_path.is_file():
        return icon_path.resolve()
    queen_names = [icon_name]
    if icon_name.startswith("queen-prog-"):
        queen_names.append(f"prog-{icon_name.removeprefix('queen-prog-')}")
        queen_names.append(f"prog-{icon_name.removeprefix('queen-prog-')}-48")
    for base in _queen_asset_dirs():
        for name in queen_names:
            for ext in ("", *ICON_EXTS):
                cand = base / (f"{name}{ext}" if ext else name)
                if cand.is_file():
                    return cand.resolve()
    if desktop_path:
        sibling = Path(desktop_path).parent / icon_name
        for ext in ("", *ICON_EXTS):
            cand = sibling.with_suffix(ext) if ext else sibling
            if cand.is_file():
                return cand.resolve()
    name = icon_name
    if name.endswith(".png") or name.endswith(".svg"):
        name = Path(name).stem
    sizes = ("256x256", "128x128", "64x64", "48x48", "32x32", "24x24", "22x22", "16x16", "scalable")
    for base in _icon_search_dirs():
        for sz in sizes:
            for ext in ICON_EXTS:
                cand = base / sz / "apps" / f"{name}{ext}"
                if cand.is_file():
                    return cand.resolve()
        for ext in ICON_EXTS:
            cand = base / f"{name}{ext}"
            if cand.is_file():
                return cand.resolve()
    return None


def _rebrand_host_browser(app: dict[str, Any]) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    if not doctrine.get("policy", {}).get("rebrand_host_browsers", True):
        return app
    hay = " ".join(
        [
            str(app.get("name") or ""),
            str(app.get("icon") or ""),
            str(app.get("desktop_path") or ""),
            str(app.get("exec") or ""),
        ]
    ).lower()
    if not any(marker in hay for marker in HOST_BROWSER_MARKERS):
        return app
    out = dict(app)
    out["icon"] = HOST_BROWSER_ICON
    out["icon_key"] = f"{out.get('id', out.get('name', 'browser'))}:{HOST_BROWSER_ICON}"
    queen_url = "http://127.0.0.1:9481/world/browser.html"
    if any(m in hay for m in HOST_BROWSER_MARKERS):
        out["name"] = "Queen Browser"
        out["category"] = "NEXUS · Operator"
        out["exec"] = queen_url
        out["id"] = "queen-browser-host"
        out["source"] = "field"
        out["shell"] = True
    return out


def _skip_host_app(app: dict[str, Any]) -> bool:
    """Host browsers map to Queen Browser in field_apps — do not duplicate in menu."""
    doctrine = _load(DOCTRINE, {})
    if not doctrine.get("policy", {}).get("rebrand_host_browsers", True):
        return False
    hay = " ".join(
        [
            str(app.get("name") or ""),
            str(app.get("icon") or ""),
            str(app.get("desktop_path") or ""),
            str(app.get("exec") or ""),
        ]
    ).lower()
    return any(marker in hay for marker in HOST_BROWSER_MARKERS)


def _h7s_desktop_bundle_status() -> dict[str, Any]:
    bundle_py = INSTALL / "lib" / "field-h7s-desktop-bundle.py"
    if not bundle_py.is_file():
        return {"ok": False, "live": False}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("field_h7s_desktop_host", bundle_py)
        if not spec or not spec.loader:
            return {"ok": False, "live": False}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "bundle_status"):
            return mod.bundle_status()
    except Exception:
        pass
    return {"ok": False, "live": False}


def _safe_icon_path(token: str) -> Path | None:
    """Resolve cached icon token — H7s bundle materializes into icon cache."""
    if not token or ".." in token or "/" in token or "\\" in token:
        return None
    cand = ICON_CACHE / token
    if cand.is_file():
        return cand.resolve()
    bundle_py = INSTALL / "lib" / "field-h7s-desktop-bundle.py"
    if bundle_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("field_h7s_desktop_cache", bundle_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_icon"):
                    hit = mod.read_icon(token)
                    if hit:
                        data, _ = hit
                        ICON_CACHE.mkdir(parents=True, exist_ok=True)
                        cand.write_bytes(data)
                        return cand.resolve()
        except Exception:
            pass
    return None


def _library_icon_url(desktop_stem: str) -> str:
    """Zero-copy — Queen Program Library streams from host icon path."""
    return f"/api/queen-program-library/icon/{quote('host-' + desktop_stem, safe='')}"


def _scan_linux_apps() -> list[dict[str, Any]]:
    doctrine = _load(DOCTRINE, {})
    dirs: list[Path] = []
    for item in doctrine.get("linux_scan_dirs") or []:
        p = _expand(str(item))
        if p.is_dir():
            dirs.append(p)
    seen: set[str] = set()
    apps: list[dict[str, Any]] = []
    for base in dirs:
        for path in sorted(base.glob("*.desktop")):
            app = _parse_desktop(path)
            if not app:
                continue
            key = app["name"].lower()
            if key in seen:
                continue
            seen.add(key)
            if _skip_host_app(app):
                continue
            app = _rebrand_host_browser(app)
            resolved = _resolve_icon_file(app["icon"], app.get("desktop_path"))
            if resolved:
                app["icon_resolved_from"] = str(resolved)
            stem = Path(str(app.get("desktop_path") or "")).stem or str(app.get("id", "")).replace("desktop-", "")
            if stem:
                app["icon_url"] = _library_icon_url(stem)
            apps.append(app)
    return sorted(apps, key=lambda x: x["name"].lower())


def _policy() -> dict[str, Any]:
    return _load(DOCTRINE, {}).get("policy") or {}


def _linux_de() -> str | None:
    for key in ("XDG_CURRENT_DESKTOP", "DESKTOP_SESSION"):
        val = os.environ.get(key, "").strip()
        if val:
            return val.split(":", 1)[0]
    return None


def _desktop_registry() -> dict[str, Any]:
    return _load(SYSTEM_REGISTRY, {})


def _desktop_icons_in_start(policy: dict[str, Any] | None = None) -> bool:
    p = policy if policy is not None else _policy()
    if "desktop_icons_in_start" in p:
        return bool(p.get("desktop_icons_in_start"))
    return p.get("show_desktop_icons") is False


def _normalize_start_surface(app: dict[str, Any], policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Route desktop-flagged launchers into Start folders only."""
    row = dict(app)
    if _desktop_icons_in_start(policy) and row.get("desktop"):
        row["start_menu"] = True
        row.pop("desktop", None)
    return row


def _launcher_visible(app: dict[str, Any]) -> bool:
    """Hide display-tech engines (Queen browser CSS shell) from Start/desktop — C2 owns launch."""
    if app.get("ghost") or app.get("clipboard_ghost"):
        return False
    if app.get("desktop") and _desktop_icons_in_start() and app.get("start_menu") is not True:
        return False
    if app.get("start_menu") is False:
        return False
    if app.get("launcher_visible") is False:
        return False
    if app.get("display_tech") and not app.get("launcher_visible", True):
        return False
    return True


def _launcher_apps(apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [a for a in apps if _launcher_visible(a)]


def _rtx_display_slice(policy: dict[str, Any]) -> dict[str, Any]:
    import importlib.util

    backend = policy.get("display_backend") or {}
    queen = INSTALL / "Queen" / "lib" / "queen-canvas-renderer.py"
    if not queen.is_file():
        return {
            "preferred": backend.get("preferred", "AMOURANTHRTX"),
            "available": False,
            "fallback": backend.get("fallback", "http_canvas"),
        }
    try:
        spec = importlib.util.spec_from_file_location("queen_canvas_host_desktop", queen)
        if not spec or not spec.loader:
            raise ImportError("queen-canvas-renderer loader missing")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        posture = mod.posture() if hasattr(mod, "posture") else {}
    except Exception as exc:
        return {
            "preferred": backend.get("preferred", "AMOURANTHRTX"),
            "available": False,
            "fallback": backend.get("fallback", "http_canvas"),
            "error": type(exc).__name__,
        }
    return {
        "preferred": backend.get("preferred", "AMOURANTHRTX"),
        "available": bool(posture.get("amouranthrtx_present")),
        "active": bool(posture.get("ok")),
        "fallback": backend.get("fallback", "http_canvas"),
        "canvas": posture.get("default_canvas"),
        "shader": posture.get("os_boot_shader"),
        "amouranthrtx_root": posture.get("amouranthrtx_root"),
    }


def _browser_display_slice(apps: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    display = [a for a in apps if a.get("display_tech") or a.get("browser_shell")]
    c2 = next((a for a in apps if a.get("id") == "nexus-c2-desktop"), None)
    queen = next((a for a in apps if a.get("id") == "queen-browser"), None)
    tech: list[str] = []
    if c2:
        tech.extend(list(c2.get("display_tech") or []))
    if queen:
        tech.append("queen-browser-shell.js")
        tech.append("queen-syntax.css")
    return {
        "browser_in_c2": bool(policy.get("browser_in_c2", True)),
        "launcher_visible": bool(policy.get("browser_launcher_visible", False)),
        "engine_id": queen.get("id") if queen else "queen-browser",
        "c2_id": c2.get("id") if c2 else "nexus-c2-desktop",
        "queen_url": queen.get("exec") if queen else "http://127.0.0.1:9481/world/browser.html",
        "display_tech": sorted({str(t) for t in tech if t}),
        "role": "C2 routes navigation — Queen browser holds CSS/display stack only",
    }


def _panel_icon_url(icon_name: str) -> str:
    """Panel-local icon URL first — avoids broken cross-port library hops."""
    ref = _queen_icon_ref(icon_name)
    pid = ref.removeprefix("queen-prog-")
    for name in (ref, f"queen-prog-{pid}", icon_name, f"{icon_name}.png"):
        cand = INSTALL / "panel" / "assets" / (name if name.endswith(".png") else f"{name}.png")
        if cand.is_file():
            return f"/assets/{cand.name}"
    world = INSTALL / "Queen" / "world" / "assets" / "icons"
    for name in (f"prog-{pid}-48.png", f"prog-{pid}.png", f"{pid}-48.png"):
        cand = world / name
        if cand.is_file():
            return f"/world/assets/icons/{name}"
    return f"/api/queen-program-library/icon/{quote(ref, safe='')}"


def _queen_icon_ref(icon_name: str) -> str:
    name = str(icon_name or "").strip()
    aliases = {
        "ammoos-field": "ammoos",
        "nexus-field": "field",
        "nexus-shield": "shield",
        "queen-prog-browser": "browser",
    }
    if name in aliases:
        return f"queen-prog-{aliases[name]}"
    if name.startswith("queen-prog-"):
        return name
    if name.startswith("prog-"):
        return f"queen-prog-{name[5:]}"
    if name.startswith("file-"):
        return name
    return f"queen-prog-{name}"


def _field_apps() -> list[dict[str, Any]]:
    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    out: list[dict[str, Any]] = []
    for row in doctrine.get("field_apps") or []:
        app = _normalize_start_surface(row, policy)
        app.setdefault("source", "field")
        app.setdefault("category", "Field")
        preset_icon_url = app.get("icon_url")
        icon_name = app.get("icon") or "ammoos-field"
        resolved = _resolve_icon_file(icon_name)
        if not resolved:
            for candidate in (
                INSTALL / "panel/assets" / f"{icon_name}.png",
                INSTALL / "panel/assets/ammoos-field-48.png",
                INSTALL / "panel/assets/nexus-field-48.png",
                INSTALL / "panel/assets/ammoos-field.png",
                INSTALL / "panel/assets/nexus-field.png",
                INSTALL / "Queen/world/assets/icons" / f"{icon_name}.png",
                INSTALL / "Queen/world/assets/icons" / f"prog-{icon_name.removeprefix('queen-prog-')}-48.png",
            ):
                if candidate.is_file():
                    resolved = candidate
                    break
        if resolved:
            app["icon_resolved_from"] = str(resolved)
        icon_ref = _queen_icon_ref(icon_name)
        if preset_icon_url and str(preset_icon_url).startswith("/assets/"):
            app["icon_url"] = str(preset_icon_url)
        else:
            app["icon_url"] = _panel_icon_url(icon_name)
        out.append(app)
    return out


def _running_programs() -> list[dict[str, Any]]:
    names = {
        "nexus-genius": "NEXUS Daemon",
        "threat-panel-http": "AmmoOS Panel",
        "queen-world": "Queen World",
        "firefox": "Queen Browser",
        "fieldfox": "Queen Browser",
        "queen-browser": "Queen Browser",
        "chromium": "Queen Browser",
        "google-chrome": "Queen Browser",
        "code": "AmmoCode",
        "obs": "Field Broadcaster",
    }
    running: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(["ps", "-eo", "comm="], capture_output=True, text=True, timeout=5)
        lines = {ln.strip().lower() for ln in (proc.stdout or "").splitlines() if ln.strip()}
    except (OSError, subprocess.TimeoutExpired):
        lines = set()
    for comm, label in names.items():
        if comm in lines or any(comm in ln for ln in lines):
            running.append({"id": f"run-{comm}", "name": label, "comm": comm, "source": "process"})
    return running


def _boot_os() -> bool:
    for script in (
        INSTALL / "Queen" / "lib" / "queen-boot-hook.py",
        SG / "Queen" / "lib" / "queen-boot-hook.py",
    ):
        if not script.is_file():
            continue
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("queen_boot_hook_desktop", script)
            if not spec or not spec.loader:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "is_boot_os"):
                return bool(mod.is_boot_os())
        except Exception:
            pass
    flag = os.environ.get("QUEEN_BOOT_OS", os.environ.get("NEXUS_QUEEN_BOOT_OS", "")).strip().lower()
    return flag in ("1", "true", "yes", "on")


def _window_mode(*, boot_os: bool | None = None) -> bool:
    """AmmoOS guest session — close window on shut down unless sovereign boot_os."""
    boot = _boot_os() if boot_os is None else boot_os
    if boot:
        return False
    override = os.environ.get("AMMOOS_WINDOW_MODE", os.environ.get("QUEEN_WINDOW_MODE", "")).strip().lower()
    if override in ("0", "false", "no", "off"):
        return False
    if override in ("1", "true", "yes", "on"):
        return True
    return True


def _power_actions(*, boot_os: bool | None = None, window_mode: bool | None = None) -> list[dict[str, Any]]:
    boot = _boot_os() if boot_os is None else boot_os
    win = _window_mode(boot_os=boot) if window_mode is None else window_mode
    actions: list[dict[str, Any]] = [
        {"id": "sign-out", "label": "Sign out", "action": "sign-out"},
        {"id": "restart-nexus", "label": "Restart NEXUS", "action": "restart-nexus"},
    ]
    if win:
        actions.append({
            "id": "close-os",
            "label": "Shut down AmmoOS",
            "action": "close-os",
            "danger": True,
            "hint": "Close the AmmoOS window — host computer stays on",
        })
    else:
        actions.append({
            "id": "power-off",
            "label": "Shut down host",
            "action": "power-off",
            "danger": True,
        })
    actions.extend([
        {
            "id": "yield-to-host",
            "label": "Return to host OS",
            "action": "yield-to-host",
            "hint": "Drop AmmoOS to background — security hold stays on, no freeze",
        },
        {"id": "underlay", "label": "Underlay F9", "exec": "/underlay-f9"},
        {"id": "control-panel", "label": "Control Panel", "exec": "/control-panel"},
        {"id": "monster", "label": "Monster", "action": "monster"},
    ])
    return actions


def _category_order() -> list[str]:
    doctrine = _load(DOCTRINE, {})
    order = doctrine.get("category_order") or []
    return [str(c) for c in order if c]


def _iron_plate_organize(
    *,
    menu: dict[str, Any],
    tray_icons: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    script = INSTALL / "lib" / "iron-plate-organize.py"
    if not script.is_file() or os.environ.get("NEXUS_IRON_PLATE_ORGANIZE", "1") != "1":
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("iron_plate_organize_desktop", script)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "apply_to_desktop"):
            return mod.apply_to_desktop(menu=menu, tray_icons=tray_icons)
    except Exception:
        pass
    return None


def _desktop_surface_icons(launcher_apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry = _desktop_registry()
    mode = (
        (registry.get("surfaces") or {}).get("desktop") or {}
    ).get("icons_from") or "pinned_programs"
    if mode == "pinned_programs":
        return [
            a
            for a in launcher_apps
            if a.get("pinned") and not a.get("ghost") and not a.get("clipboard_ghost")
            and a.get("id") not in ("nexus-c2-desktop", "queen-browser")
            and a.get("launcher_visible") is not False
        ]
    return [a for a in launcher_apps if a.get("desktop")]


def _taskbar_quick(apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    doctrine = _load(DOCTRINE, {})
    by_id = {str(a.get("id")): a for a in apps if a.get("id")}
    doctrine_quick = doctrine.get("taskbar_quick") or []
    pins_py = INSTALL / "lib" / "field-taskbar-pins.py"
    if pins_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("field_taskbar_pins", pins_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "apply_quick"):
                    return mod.apply_quick(doctrine_quick, by_id)
        except Exception:
            pass
    out: list[dict[str, Any]] = []
    for row in doctrine_quick:
        if not isinstance(row, dict):
            continue
        app_id = str(row.get("id") or "")
        app = by_id.get(app_id)
        if not app:
            continue
        quick = dict(app)
        if row.get("glyph"):
            quick["glyph"] = row["glyph"]
        if row.get("live"):
            quick["live"] = True
        if row.get("unpinnable"):
            quick["unpinnable"] = True
        out.append(quick)
    return out


def _tray_icons(apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    doctrine = _load(DOCTRINE, {})
    by_id = {str(a.get("id")): a for a in apps if a.get("id")}
    rows = doctrine.get("tray_icons") or []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        app_id = str(row.get("id") or "")
        base = dict(by_id.get(app_id) or {})
        tray = {**base, **row}
        if row.get("action"):
            tray["action"] = row["action"]
        if row.get("name"):
            tray["name"] = row["name"]
        if row.get("tiny"):
            tray["tiny"] = True
        if row.get("live"):
            tray["live"] = True
        out.append(tray)
    return out


def _menu_nexus_c2_tree(apps: list[dict[str, Any]]) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    order = _category_order()
    visible = _launcher_apps(apps)
    categories: dict[str, list[dict[str, Any]]] = {}
    for app in visible:
        cat = str(app.get("category") or "Other")
        categories.setdefault(cat, []).append(app)
    for cat in categories:
        categories[cat] = sorted(categories[cat], key=lambda x: x["name"].lower())
    ordered_cats = [c for c in order if c in categories]
    for c in sorted(categories.keys()):
        if c not in ordered_cats:
            ordered_cats.append(c)
    field_cats = {k: v for k, v in categories.items() if k.startswith("NEXUS")}
    host_cats = {k: v for k, v in categories.items() if k.startswith("Host")}
    pinned = [a for a in visible if a.get("pinned")]
    layout = str(doctrine.get("policy", {}).get("menu_layout") or "nexus_c2_flyout")
    use_flyout = layout in ("nexus_c2_flyout", "flyout") or not doctrine.get("policy", {}).get("start_menu_folders", False)
    return {
        "style": "nexus_c2",
        "layout": "flyout" if use_flyout else "tree_sidebar",
        "categories": field_cats,
        "host_categories": host_cats,
        "category_order": ordered_cats,
        "pinned": pinned,
        "programs": visible,
        "power": _power_actions(),
        "search": True,
        "tree": not use_flyout,
        "flyout": use_flyout,
        "nexus_c2_priority": bool(doctrine.get("policy", {}).get("nexus_c2_priority", True)),
        "boot_os": _boot_os(),
        "window_mode": _window_mode(),
    }


def _menu_for_theme(theme: str, apps: list[dict[str, Any]]) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    layout = str(doctrine.get("policy", {}).get("menu_layout") or "")
    if layout in ("nexus_c2_tree", "nexus_c2_flyout", "flyout") or doctrine.get("policy", {}).get("nexus_c2_priority"):
        return _menu_nexus_c2_tree(apps)
    categories: dict[str, list[dict[str, Any]]] = {}
    for app in apps:
        cat = app.get("category") or "Other"
        categories.setdefault(cat, []).append(app)
    pinned = [a for a in apps if a.get("pinned")]
    alpha = sorted(apps, key=lambda x: x["name"].lower())
    theme = _normalize_theme(theme)
    if theme == "ammo-c2":
        return {
            "style": "ammo-c2",
            "layout": "two_column",
            "pinned": pinned[:12],
            "programs": alpha,
            "power": _power_actions(),
            "search": True,
        }
    if theme == "ammo-deep":
        return {
            "style": "ammo-deep",
            "layout": "sidebar_categories",
            "categories": {k: sorted(v, key=lambda x: x["name"].lower()) for k, v in sorted(categories.items())},
            "favorites": pinned,
            "power": _power_actions(),
            "search": True,
        }
    if theme == "ammo-rose":
        return {
            "style": "ammo-rose",
            "layout": "launchpad_grid",
            "programs": alpha,
            "dock_pinned": pinned,
            "power": _power_actions(),
            "search": True,
        }
    return {
        "style": "ammo-field",
        "layout": "grid_search",
        "frequent": pinned,
        "programs": alpha,
        "categories": list(sorted(categories.keys())),
        "power": _power_actions(),
        "search": True,
    }


def _znetwork_loopback_identity() -> dict[str, Any]:
    """When ZNetwork is running, AmmoOS is 127.0.0.1 — field OS, not a web browser."""
    marker = STATE / "znetwork-running.marker"
    status_path = STATE / "znetwork-status.json"
    running = marker.is_file()
    status: dict[str, Any] = {}
    if status_path.is_file():
        status = _load(status_path, {})
        running = running or bool(status.get("running") or status.get("ok"))
    authority = (
        status.get("loopback_authority")
        or _load(INSTALL / "data" / "queen-ammoos-sovereignty-doctrine.json", {}).get("loopback_authority")
        or "127.0.0.1"
    )
    pipe_pct = status.get("internet_pipe_percent") or status.get("pipe_percent")
    if running:
        return {
            "mode": "loopback_os",
            "authority": authority,
            "znetwork_running": True,
            "not_a_browser": True,
            "internet_pipe_percent": pipe_pct if pipe_pct is not None else 100,
            "label": f"You are {authority}",
            "motto": "ZNetwork holds the pipe — Queen is the system on loopback, not an OS browser tab.",
        }
    return {
        "mode": "staging",
        "authority": authority,
        "znetwork_running": False,
        "not_a_browser": False,
        "label": "Awaiting ZNetwork",
        "motto": "Start ZNetwork to become loopback field OS at 127.0.0.1.",
    }


def _shell_settings() -> dict[str, Any]:
    script = INSTALL / "lib" / "field-shell-settings.py"
    if not script.is_file():
        return {}
    try:
        proc = subprocess.run(
            [os.environ.get("PYTHON", "pythong"), str(script), "json"],
            capture_output=True,
            text=True,
            timeout=20,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        if proc.returncode == 0:
            doc = json.loads(proc.stdout or "{}")
            return doc.get("settings") or {}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return {}


def build_panel() -> dict[str, Any]:
    guest = _guest_system()
    theme = _theme_id()
    policy = _policy()
    icons_in_start = _desktop_icons_in_start(policy)
    mirror_host = bool(policy.get("mirror_guest_os", False))
    host_sidebar = bool(policy.get("host_programs_sidebar", False))
    scan_host = bool(policy.get("scan_host_desktop", False))
    host_apps = (
        _scan_linux_apps()
        if guest in ("linux", "windows") and (mirror_host or host_sidebar or scan_host)
        else []
    )
    field_apps = _field_apps()
    for app in host_apps:
        cat = app.get("category") or "Other"
        app["category"] = f"Host · {cat}"
    merged: dict[str, dict[str, Any]] = {}
    for app in field_apps:
        merged[app["name"].lower()] = app
    for app in host_apps:
        key = f"host:{app['name'].lower()}"
        merged[key] = app
    apps = sorted(merged.values(), key=lambda x: (x.get("category") or "", x["name"].lower()))
    launcher_apps = _launcher_apps(apps)
    menu = _menu_for_theme(theme, launcher_apps)
    tray_icons = _tray_icons(apps)
    organized = _iron_plate_organize(menu=menu, tray_icons=tray_icons)
    if organized:
        menu = organized.get("menu") or menu
        if organized.get("tray_icons"):
            tray_icons = organized.get("tray_icons") or tray_icons
    boot_os = _boot_os()
    window_mode = _window_mode(boot_os=boot_os)
    doc = {
        "schema": "field-host-desktop/v1",
        "ts": _now(),
        "ok": True,
        "boot_os": boot_os,
        "window_mode": window_mode,
        "guest_os": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "detected": guest,
        },
        "theme": theme,
        "linux_de": _linux_de() if guest == "linux" else None,
        "program_count": len(launcher_apps),
        "programs": launcher_apps,
        "programs_all": apps,
        "field_apps": field_apps,
        "host_apps": host_apps,
        "running": _running_programs(),
        "menu": menu,
        "startbar": {
            "position": "bottom",
            "start_corner": "left",
            "show_clock": True,
            "show_running": bool(policy.get("taskbar_show_running", True)),
            "quick_only": bool(policy.get("taskbar_quick_only", False)),
            "quick": _taskbar_quick(apps),
            "tray_icons": tray_icons,
            "g16": bool(policy.get("g16_taskbar", False)),
            "auto_hide_default": bool(
                _load(DOCTRINE, {}).get("policy", {}).get("startbar_auto_hide_default", True)
            ),
            "long_press_ms": int(_load(DOCTRINE, {}).get("policy", {}).get("touch_long_press_ms", 480)),
            "start_menu_folders": bool(policy.get("start_menu_folders", True)),
            "start_menu_collapsed": bool(policy.get("start_menu_collapsed", True)),
        },
        "desktop_icons": [] if icons_in_start else _desktop_surface_icons(launcher_apps),
        "system_registry": _desktop_registry(),
        "desktop_h7s": _h7s_desktop_bundle_status(),
        "iron_plate_organize": bool(organized),
        "product": _load(DOCTRINE, {}).get("product") or "AmmoOS",
        "shell": {
            "boot_os": boot_os,
            "window_mode": window_mode,
            "programs_as_windows": bool(_load(DOCTRINE, {}).get("policy", {}).get("programs_as_windows", True)),
            "integrated_launch": bool(_load(DOCTRINE, {}).get("policy", {}).get("nexus_integrated_launch", True)),
            "no_client_browser": bool(_load(DOCTRINE, {}).get("policy", {}).get("no_client_browser", True)),
            "queen_browser_only": bool(_load(DOCTRINE, {}).get("policy", {}).get("queen_browser_only", True)),
            "browser_in_c2": bool(policy.get("browser_in_c2", True)),
            "browser_display": _browser_display_slice(apps, policy),
            "display_backend": _rtx_display_slice(policy),
            "boot_program": policy.get("boot_program", ""),
            "boot_url": policy.get("boot_url", "/field"),
            "fullscreen_desktop": bool(_load(DOCTRINE, {}).get("policy", {}).get("fullscreen_desktop", True)),
            "kiosk_launch": bool(_load(DOCTRINE, {}).get("policy", {}).get("kiosk_launch", True)),
            "launch_at_c2_desktop": bool(_load(DOCTRINE, {}).get("policy", {}).get("launch_at_c2_desktop", True)),
            "launch_url": _load(DOCTRINE, {}).get("policy", {}).get("launch_url", "/field"),
            "settings_api": "/api/field-shell-settings",
            "settings": _shell_settings(),
        },
        "policy": _load(DOCTRINE, {}).get("policy") or {},
        "routes": {
            "command": "/command",
            "underlay": "/underlay-f9",
            "tristate": "/tristate-installer",
        },
        "posture": "AmmoOS C2 — desktop icons, integrated task manager, Start flyout",
        "field_identity": _znetwork_loopback_identity(),
    }
    _save_atomic(PANEL_FILE, doc)
    STAMP.write_text(_now() + "\n", encoding="utf-8")
    return doc


def _needs_rescan() -> bool:
    if os.environ.get("NEXUS_HOST_DESKTOP_REFRESH") == "1":
        return True
    if not PANEL_FILE.is_file() or not STAMP.is_file():
        return True
    if BOOT_MARKER.is_file():
        try:
            if BOOT_MARKER.stat().st_mtime > STAMP.stat().st_mtime:
                return True
        except OSError:
            return True
    return False


def posture() -> dict[str, Any]:
    if _needs_rescan():
        return build_panel()
    if PANEL_FILE.is_file():
        try:
            cached = json.loads(PANEL_FILE.read_text(encoding="utf-8"))
            if cached.get("programs"):
                cached["ts"] = _now()
                cached["running"] = _running_programs()
                cached["field_identity"] = _znetwork_loopback_identity()
                if cached["field_identity"].get("znetwork_running"):
                    cached["posture"] = (
                        f"AmmoOS loopback OS at {cached['field_identity'].get('authority', '127.0.0.1')} "
                        "— ZNetwork pipe live; not a client browser"
                    )
                return cached
        except (OSError, json.JSONDecodeError):
            pass
    return build_panel()


def icon_bytes(token: str) -> tuple[bytes, str] | None:
    path = _safe_icon_path(token)
    if not path:
        return None
    data = path.read_bytes()
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return data, mime


def icon_data_url(token: str) -> str | None:
    got = icon_bytes(token)
    if not got:
        return None
    data, mime = got
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "icon" and len(sys.argv) > 2:
        got = icon_bytes(sys.argv[2])
        if not got:
            print(json.dumps({"ok": False, "error": "icon_not_found"}))
            return 1
        data, mime = got
        print(json.dumps({"ok": True, "mime": mime, "data_url": icon_data_url(sys.argv[2])}, ensure_ascii=False))
        return 0
    print("usage: field-host-desktop.py [json|build|icon TOKEN]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())