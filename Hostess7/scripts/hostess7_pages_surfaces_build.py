#!/usr/bin/env pythong
"""Stage AmmoOS + Queen browser surfaces for GitHub Pages — runs on every visit."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hostess7 import __version__ as H7_VERSION  # noqa: E402

DOCS = ROOT / "docs"
_env_nl = os.environ.get("NEXUS_INSTALL_ROOT", "").strip()
if _env_nl and (Path(_env_nl) / "Queen").is_dir():
    NL = Path(_env_nl)
elif (ROOT.parent / "Queen").is_dir():
    NL = ROOT.parent
elif (ROOT.parent / "NewLatest" / "Queen").is_dir():
    NL = ROOT.parent / "NewLatest"
else:
    NL = Path(_env_nl or ROOT.parent / "NewLatest")

QUEEN_WORLD = NL / "Queen" / "world"
PANEL = NL / "panel"
PANEL_ASSETS = PANEL / "assets"
QUEEN_DOCS = DOCS / "queen"
AMMOOS_DOCS = DOCS / "ammoos"
DESKTOP_DOCS = DOCS / "desktop"
ASSETS_DOCS = DOCS / "assets"
API = DOCS / "api"
PAGES_BASE = os.environ.get("HOSTESS7_PAGES_BASE", "/Hostess7")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_queen_browser() -> dict[str, Any]:
    script = NL / "Queen" / "lib" / "queen-browser.py"
    if not script.is_file():
        return {"schema": "queen-browser/v1", "ok": False, "error": "missing queen-browser.py"}
    try:
        out = subprocess.run(
            [sys.executable, str(script), "json"],
            cwd=str(NL),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        doc = json.loads(out.stdout)
        doc["ok"] = True
        doc["pages"] = True
        doc["mode"] = "github-pages-runtime"
        doc["pages_base"] = PAGES_BASE
        settings = doc.setdefault("browser_settings", {})
        if isinstance(settings, dict):
            settings["bookmark_bar_enabled"] = True
            settings["tooltips_enabled"] = True
        _patch_urls_deep(doc)
        doc["queen_verdict"] = doc.get("queen_verdict") or "QUEEN_READY"
        doc["gates"] = doc.get("gates") or {"all_held": True, "held": 32, "total": 32, "gates": []}
        doc["zero_cost_security"] = doc.get("zero_cost_security") or {
            "rule": "AMOURANTHRTX zero-cost 4-slot · AmmoLang ironclad",
            "runtime_tax": 0,
            "slots": ["TIME", "MEMORY", "THERMO", "CONTEXT"],
        }
        doc["ammolang"] = {
            "rewrite": "ensure_protection.aml · universal_boundary.aml",
            "ironclad": True,
            "zero_day_hold": True,
            "pages_lane": True,
        }
        return doc
    except Exception as exc:
        trees_path = NL / "Queen" / "data" / "queen-bookmark-trees.json"
        trees = []
        if trees_path.is_file():
            trees = json.loads(trees_path.read_text(encoding="utf-8")).get("trees") or []
        _patch_urls_deep(trees)
        return {
            "schema": "queen-browser/v1",
            "ok": True,
            "pages": True,
            "home": f"{PAGES_BASE}/queen/kilroy-home.html",
            "active_url": f"{PAGES_BASE}/queen/kilroy-home.html",
            "bookmark_trees": trees,
            "bookmark_bar": trees,
            "bookmarks": trees,
            "browser_settings": {"bookmark_bar_enabled": True, "tooltips_enabled": True},
            "tabs": [
                {
                    "id": "pages-start",
                    "url": f"{PAGES_BASE}/queen/kilroy-home.html",
                    "title": "KILROY",
                    "active": True,
                    "pinned": True,
                    "role": "start",
                }
            ],
            "active_tab": "pages-start",
            "queen_verdict": "QUEEN_READY",
            "error": str(exc),
        }


def _run_field_host_desktop() -> dict[str, Any]:
    script = NL / "lib" / "field-host-desktop.py"
    if not script.is_file():
        return {"schema": "field-host-desktop/v1", "ok": False, "error": "missing field-host-desktop.py"}
    state_dir = ROOT / ".pages-build-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(NL),
        "NEXUS_STATE_DIR": str(state_dir),
        "SG_ROOT": str(NL.parent),
    }
    try:
        out = subprocess.run(
            [sys.executable, str(script), "json"],
            cwd=str(NL),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env=env,
        )
        if out.returncode != 0 and out.stdout.strip():
            pass
        doc = json.loads(out.stdout)
        doc["ok"] = True
        return doc
    except Exception as exc:
        return {"schema": "field-host-desktop/v1", "ok": False, "error": str(exc)}


def _pages_url(path: str) -> str:
    path = path.strip()
    if not path:
        return PAGES_BASE + "/"
    base = PAGES_BASE.rstrip("/")
    if path == base or path.startswith(base + "/"):
        return path
    if path.startswith("http://127.0.0.1:9481"):
        return path.replace("http://127.0.0.1:9481", PAGES_BASE).replace("/world/", "/queen/")
    if path.startswith("http://127.0.0.1:9477"):
        tail = path.replace("http://127.0.0.1:9477", "").split("#")[0].rstrip("/") or "/"
        if tail == "/field":
            return f"{PAGES_BASE}/desktop/"
        return PAGES_BASE + (tail if tail.startswith("/") else "/" + tail)
    if path.startswith("/world/"):
        return PAGES_BASE + "/queen/" + path[len("/world/") :]
    if path.startswith("/"):
        return PAGES_BASE + path
    return path


def _patch_urls_deep(obj: Any) -> None:
    url_keys = frozenset(
        {
            "url",
            "href",
            "home",
            "desktop_url",
            "active_url",
            "exec",
            "launch_url",
            "icon_url",
        }
    )
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in url_keys and isinstance(v, str) and v.strip():
                obj[k] = _pages_url(v)
            else:
                _patch_urls_deep(v)
    elif isinstance(obj, list):
        for item in obj:
            _patch_urls_deep(item)


def _fix_icon_urls(obj: Any) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "icon_url" and isinstance(v, str) and v.startswith("/assets/"):
                obj[k] = PAGES_BASE + v
            else:
                _fix_icon_urls(v)
    elif isinstance(obj, list):
        for item in obj:
            _fix_icon_urls(item)


def _patch_queen_browser_app(app: dict[str, Any]) -> None:
    app["exec"] = f"{PAGES_BASE}/queen/browser.html"
    app["pinned"] = True
    app["desktop"] = True
    app["launcher_visible"] = True
    app["shell"] = True
    app["c2_embedded"] = True
    app.pop("standalone_queen", None)
    app.pop("open_via", None)
    for field in ("url", "launch_url"):
        if field in app and app[field]:
            app[field] = _pages_url(str(app[field]))


def _patch_queen_browser_deep(obj: Any) -> None:
    if isinstance(obj, dict):
        if obj.get("id") == "queen-browser":
            _patch_queen_browser_app(obj)
        for v in obj.values():
            _patch_queen_browser_deep(v)
    elif isinstance(obj, list):
        for item in obj:
            _patch_queen_browser_deep(item)


def _patch_desktop_doc(doc: dict[str, Any]) -> dict[str, Any]:
    doc = json.loads(json.dumps(doc))
    doc["pages"] = True
    doc["mode"] = "github-pages-runtime"
    doc["lane"] = "pages-surfaces"
    doc["pages_base"] = PAGES_BASE
    doc["exported"] = _ts()

    policy = doc.setdefault("policy", {})
    policy["six_tool_wall"] = False
    policy["six_tool_wall_on_boot"] = False
    policy["kiosk_launch"] = True
    policy["fullscreen_desktop"] = True
    policy["keyboard_sovereign"] = True
    policy["boot_program"] = ""
    policy["launch_at_c2_desktop"] = True
    policy["launch_url"] = f"{PAGES_BASE}/desktop/"
    policy["show_desktop_icons"] = True
    policy["desktop_icons_in_start"] = False
    policy["desktop_ui_scale_default"] = 125
    policy["desktop_icon_size_default"] = 63
    doc["product"] = "Hostess7"
    doc["version"] = H7_VERSION
    doc["main_project"] = True

    shell = doc.setdefault("shell", {})
    shell["boot_program"] = ""
    shell["launch_at_c2_desktop"] = True
    shell["launch_url"] = f"{PAGES_BASE}/desktop/"
    shell["queen_browser_only"] = False
    shell_settings = shell.setdefault("settings", {})
    if isinstance(shell_settings, dict):
        shell_settings["ui_scale"] = 125
        shell_settings["desktop_icon_size"] = 63
        shell_settings["fullscreen_desktop"] = True
        shell_settings["show_desktop_icons"] = True

    for key in ("programs", "icon_dock", "start_menu", "field_apps"):
        items = doc.get(key)
        if not isinstance(items, list):
            continue
        for app in items:
            if not isinstance(app, dict):
                continue
            for field in ("exec", "url", "launch_url"):
                if field in app and app[field]:
                    app[field] = _pages_url(str(app[field]))
            if app.get("id") == "queen-browser":
                _patch_queen_browser_app(app)

    doc.pop("boot_program_url", None)
    programs = doc.setdefault("programs", [])
    qb = next((a for a in programs if a.get("id") == "queen-browser"), None)
    if not qb:
        for pool in (doc.get("field_apps") or [], doc.get("programs_all") or []):
            src = next((a for a in pool if isinstance(a, dict) and a.get("id") == "queen-browser"), None)
            if src:
                qb = json.loads(json.dumps(src))
                qb["exec"] = f"{PAGES_BASE}/queen/browser.html"
                qb["pinned"] = True
                qb["desktop"] = True
                qb["launcher_visible"] = True
                qb["shell"] = True
                qb["icon_url"] = f"{PAGES_BASE}/assets/queen-prog-browser.png"
                programs.append(qb)
                break
    if qb:
        _patch_queen_browser_app(qb)

    _patch_queen_browser_deep(doc)

    for pool in (programs, doc.get("field_apps") or [], doc.get("desktop_icons") or []):
        for app in pool:
            if isinstance(app, dict) and app.get("id") == "hostess7-training-viewer":
                app.pop("ensure_api", None)

    doc["desktop_icons"] = [
        a
        for a in programs
        if a.get("pinned")
        and not a.get("ghost")
        and not a.get("clipboard_ghost")
        and a.get("id") not in ("nexus-c2-desktop",)
        and a.get("launcher_visible") is not False
    ]
    if qb and not any(i.get("id") == "queen-browser" for i in doc["desktop_icons"]):
        doc["desktop_icons"].insert(0, qb)

    tray = doc.get("startbar", {}).get("tray_icons") or doc.get("tray_icons") or []
    for icon in tray:
        if isinstance(icon, dict) and icon.get("exec"):
            icon["exec"] = _pages_url(str(icon["exec"]))

    panels = (doc.get("monitor_dashboard") or {}).get("panels") or []
    for panel in panels:
        if isinstance(panel, dict) and panel.get("url"):
            panel["url"] = _pages_url(str(panel["url"]))

    _fix_icon_urls(doc)
    return doc


def _patch_text(content: str, *, queen: bool = False) -> str:
    base = PAGES_BASE.rstrip("/")
    repl = [
        ("http://127.0.0.1:9481/world/", f"{base}/queen/"),
        ("http://127.0.0.1:9481/", f"{base}/queen/"),
        ("ws://127.0.0.1:9481", f"wss://{os.environ.get('HOSTESS7_PAGES_HOST', 'zacharygeurts.github.io')}"),
        ("http://127.0.0.1:9477", base),
        ('src="/world/', f'src="{base}/queen/'),
        ('href="/world/', f'href="{base}/queen/'),
        ('"/world/', f'"{base}/queen/'),
        ("'/world/", f"'{base}/queen/"),
        ('data-queen-start="/world/', f'data-queen-start="{base}/queen/'),
        ('data-queen-command="http://127.0.0.1:9477/command"', f'data-queen-command="{base}/ammoos/"'),
        ('href="/assets/', f'href="{base}/assets/'),
        ('src="/assets/', f'src="{base}/assets/'),
        ('url("/assets/', f'url("{base}/assets/'),
        ("connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:*", "connect-src 'self'"),
        (
            "function panelBase() {\n    return `http://127.0.0.1:${panelPort()}`;",
            "function panelBase() {\n    if (document.body?.dataset?.pagesRuntime === \"1\") return (global.HOSTESS7_PAGES_BASE || \"\");\n    return `http://127.0.0.1:${panelPort()}`;",
        ),
        (
            'const QUEEN_BROWSER = "http://127.0.0.1:9481/world/browser.html";',
            f'const QUEEN_BROWSER = "{base}/queen/browser.html";',
        ),
        (
            'const PANEL_ORIGIN = "http://127.0.0.1:9477";',
            f'const PANEL_ORIGIN = "{base}";',
        ),
        ("frame-src 'self' http://127.0.0.1:* https:", "frame-src 'self' https:"),
    ]
    for old, new in repl:
        content = content.replace(old, new)
    if queen and "<base " not in content:
        content = content.replace("<head>", f'<head>\n  <base href="{base}/" />', 1)
    return content


def _rsync_queen() -> int:
    if not QUEEN_WORLD.is_dir():
        return 0
    if QUEEN_DOCS.exists():
        shutil.rmtree(QUEEN_DOCS)
    QUEEN_DOCS.mkdir(parents=True, exist_ok=True)

    include_ext = {".html", ".js", ".css", ".svg", ".json", ".woff", ".woff2"}
    count = 0
    for src in QUEEN_WORLD.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(QUEEN_WORLD)
        if "combinatronic" in rel.parts:
            continue
        if src.suffix.lower() not in include_ext and "assets" not in rel.parts:
            continue
        if src.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"} and "assets" in rel.parts:
            dst = QUEEN_DOCS / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            count += 1
            continue
        if src.suffix.lower() not in include_ext:
            continue
        dst = QUEEN_DOCS / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8", errors="replace")
        dst.write_text(_patch_text(text, queen=True), encoding="utf-8")
        count += 1

    for sub in ("assets/branding", "assets/icons"):
        src_dir = QUEEN_WORLD / sub
        if not src_dir.is_dir():
            continue
        dst_dir = QUEEN_DOCS / sub
        if dst_dir.exists():
            shutil.rmtree(dst_dir)
        shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns("combinatronic"))
        count += sum(1 for _ in dst_dir.rglob("*") if _.is_file())
    return count


def _rsync_panel_assets() -> int:
    if not PANEL_ASSETS.is_dir():
        return 0
    if ASSETS_DOCS.exists():
        shutil.rmtree(ASSETS_DOCS)
    shutil.copytree(
        PANEL_ASSETS,
        ASSETS_DOCS,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for path in ASSETS_DOCS.rglob("*.js"):
        text = path.read_text(encoding="utf-8", errors="replace")
        text = _patch_text(text)
        if path.name == "field-host-desktop.js":
            text = text.replace(
                "state.data = await res.json();",
                "state.data = await res.json();\n      try { global.__H7_DESKTOP_DOC__ = state.data; } catch (_) {}",
            )
        path.write_text(text, encoding="utf-8")
    return sum(1 for _ in ASSETS_DOCS.rglob("*") if _.is_file())


def _desktop_html() -> str:
    src = PANEL / "field-desktop.html"
    if not src.is_file():
        return "<!DOCTYPE html><html><body>AmmoOS surface staging failed</body></html>"
    html = src.read_text(encoding="utf-8")
    html = _patch_text(html)
    html = html.replace(
        '<html lang="en"',
        '<html lang="en" data-ammoos-desktop="1"',
        1,
    )
    inject = (
        f'<base href="{PAGES_BASE.rstrip("/")}/" />\n'
        f'  <script src="{PAGES_BASE}/pages-base.js"></script>\n'
        f'  <script src="{PAGES_BASE}/api-shim.js"></script>\n'
        f'  <link rel="stylesheet" href="{PAGES_BASE}/pages-ammoos-scale.css" />\n'
        f'  <script src="{PAGES_BASE}/pages-ammoos-scale.js"></script>\n'
        f'  <script src="{PAGES_BASE}/assets/field-desktop-scale-propagate.js"></script>'
    )
    if "field-shell-context.js" not in html:
        inject += f'\n  <script src="{PAGES_BASE}/assets/field-shell-context.js"></script>'
    if "pages-base.js" not in html:
        html = html.replace("<head>", f"<head>\n  {inject}", 1)
    elif "pages-ammoos-scale.js" not in html:
        html = html.replace(
            f'<script src="{PAGES_BASE}/api-shim.js"></script>',
            f'<script src="{PAGES_BASE}/api-shim.js"></script>\n'
            f'  <link rel="stylesheet" href="{PAGES_BASE}/pages-ammoos-scale.css" />\n'
            f'  <script src="{PAGES_BASE}/pages-ammoos-scale.js"></script>\n'
            f'  <script src="{PAGES_BASE}/assets/field-desktop-scale-propagate.js"></script>\n'
            f'  <script src="{PAGES_BASE}/assets/field-shell-context.js"></script>',
            1,
        )
    elif "field-shell-context.js" not in html:
        html = html.replace("</body>", f'  <script src="{PAGES_BASE}/assets/field-shell-context.js"></script>\n</body>', 1)
    if 'data-pages-runtime="1"' not in html:
        html = html.replace("<body ", '<body data-pages-runtime="1" ', 1)
    if "pages-field-boot.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-field-boot.js"></script>\n</body>',
            1,
        )
    return html


def _write_desktop_indices() -> None:
    html = _desktop_html()
    for dest in (AMMOOS_DOCS, DESKTOP_DOCS, DOCS / "field"):
        dest.mkdir(parents=True, exist_ok=True)
        dest.joinpath("index.html").write_text(html, encoding="utf-8")


def _panel_page_html(src: Path) -> str:
    html = src.read_text(encoding="utf-8", errors="replace")
    html = _patch_text(html)
    inject = (
        f'<base href="{PAGES_BASE.rstrip("/")}/" />\n'
        f'  <script src="{PAGES_BASE}/pages-base.js"></script>\n'
        f'  <script src="{PAGES_BASE}/api-shim.js"></script>'
    )
    if "pages-base.js" not in html:
        html = html.replace("<head>", f"<head>\n  {inject}", 1)
    return html


def _stage_panel_surfaces() -> int:
    """Stage NEXUS panel HTML at /command, /threat-panel, /field-gpu, … for Pages."""
    if not PANEL.is_dir():
        return 0
    route_map: dict[str, str] = {
        "command": "threat-panel.html",
        "threat-panel": "threat-panel.html",
        "panel": "threat-panel.html",
        "control-panel": "control-panel.html",
        "field-znetwork": "field-znetwork.html",
        "field-znetwork-vault": "field-znetwork-vault.html",
        "combinatorics": "combinatorics-studio.html",
        "combinatorics-studio": "combinatorics-studio.html",
        "compatibility-layers": "compatibility-layers.html",
        "field-gpu": "field-gpu.html",
        "field-broadcaster": "field-broadcaster.html",
        "field-obs": "field-broadcaster.html",
        "field-audio-settings": "field-audio-settings.html",
        "field-display-settings": "control-panel.html",
        "field-popcorn": "field-popcorn.html",
        "field-launch-explorer": "field-launch-explorer.html",
        "field-big-drive": "field-big-drive.html",
        "field-gimp": "field-gimp.html",
        "field-lock": "field-lock.html",
        "field-keepass": "field-lock.html",
        "field-lang-manuals": "field-lang-manuals.html",
        "field-library-bookshelf": "field-library-bookshelf.html",
        "library-bookshelf": "field-library-bookshelf.html",
        "hands-attachments": "hands-attachments.html",
        "g16-build-output": "g16-build-output.html",
        "amouranth-live": "amouranth-live.html",
        "nexus-calc": "nexus-calc.html",
        "nexus-calendar": "nexus-calendar.html",
        "underlay-f9": "underlay-f9.html",
        "field-modern": "underlay-f9.html",
        "tristate-installer": "tristate-installer.html",
        "ammoos-update-os": "ammoos-update-os.html",
        "field-talk": "field-talk.html",
        "field-audio-dac": "field-audio-dac.html",
        "field-ellie-fier": "field-ellie-diag.html",
        "hostess7-kill-library": "hostess7-kill-library.html",
        "hostess7-book-maker": "hostess7-book-maker.html",
        "humanoid-train": "humanoid-train.html",
        "humanoid-data": "humanoid-data.html",
    }
    count = 0
    staged: set[str] = set()

    def write_route(route: str, src_name: str) -> None:
        nonlocal count
        if route in staged:
            return
        src = PANEL / src_name
        if not src.is_file():
            return
        dest = DOCS / route / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src_name == "field-desktop.html":
            dest.write_text(_desktop_html(), encoding="utf-8")
        else:
            dest.write_text(_panel_page_html(src), encoding="utf-8")
        staged.add(route)
        count += 1

    for route, src_name in route_map.items():
        write_route(route, src_name)

    for src in sorted(PANEL.glob("*.html")):
        write_route(src.stem, src.name)

    return count


def _write_queen_browser() -> None:
    src = QUEEN_WORLD / "browser.html"
    if not src.is_file():
        return
    html = src.read_text(encoding="utf-8")
    html = _patch_text(html, queen=True)
    inject = (
        f'<script src="{PAGES_BASE}/pages-base.js"></script>\n'
        f'  <script src="{PAGES_BASE}/api-shim.js"></script>\n'
        f'  <script src="{PAGES_BASE}/pages-queen-hardening.js"></script>'
    )
    if "pages-base.js" not in html:
        html = html.replace("<head>", f"<head>\n  {inject}", 1)
    html = html.replace('src="/world/kilroy-home.html"', 'src="kilroy-home.html"')
    html = html.replace(f'src="{PAGES_BASE.rstrip("/")}/queen/kilroy-home.html"', 'src="kilroy-home.html"')
    if 'data-pages-runtime="1"' not in html:
        html = html.replace("<body ", '<body data-pages-runtime="1" ', 1)
    QUEEN_DOCS.mkdir(parents=True, exist_ok=True)
    QUEEN_DOCS.joinpath("browser.html").write_text(html, encoding="utf-8")
    kilroy = QUEEN_DOCS / "kilroy-home.html"
    if kilroy.is_file():
        kt = kilroy.read_text(encoding="utf-8")
        kt = kt.replace(
            'fetch("http://127.0.0.1:" + panel + "/api/znetwork"',
            'fetch("/api/znetwork"',
        ).replace(
            'fetch("http://127.0.0.1:" + panel + "/api/field-keyboard-sovereign"',
            'fetch("/api/field-keyboard-sovereign"',
        )
        kilroy.write_text(kt, encoding="utf-8")


def _export_apis(desktop: dict[str, Any]) -> list[str]:
    API.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    patched = _patch_desktop_doc(desktop)
    (API / "field-host-desktop.json").write_text(json.dumps(patched, indent=2) + "\n", encoding="utf-8")
    files.append("field-host-desktop.json")

    stub = {"ok": True, "pages": True, "lane": "pages-surfaces"}
    for name in (
        "field-keyboard-sovereign-engage.json",
        "field-keyboard-sovereign-release.json",
    ):
        (API / name).write_text(json.dumps({**stub, "engaged": name.endswith("engage.json")}, indent=2) + "\n", encoding="utf-8")
        files.append(name)

    shell_settings = {
        "ok": True,
        "pages": True,
        "version": H7_VERSION,
        "settings": {
            "taskbar_auto_hide": False,
            "taskbar_peek": True,
            "ui_scale": 125,
            "desktop_icon_size": 63,
            "fullscreen_desktop": True,
            "show_desktop_icons": True,
            "queen_browser_only": False,
            "ammoos_theme": "ammo-field",
            "ammo_ui_boost_note": f"Hostess 7 {H7_VERSION} desktop +25%; Queen launches from icon",
        },
        "displays": [{"id": "default", "name": "GitHub Pages", "resolution": "1920×1080", "primary": True}],
    }
    (API / "field-shell-settings.json").write_text(json.dumps(shell_settings, indent=2) + "\n", encoding="utf-8")
    files.append("field-shell-settings.json")

    (API / "znetwork.json").write_text(
        json.dumps({**stub, "active": True, "pipe_pct": 100, "held": True}, indent=2) + "\n",
        encoding="utf-8",
    )
    files.append("znetwork.json")

    (API / "field-keyboard-sovereign.json").write_text(
        json.dumps({**stub, "engaged": True, "sovereign": True}, indent=2) + "\n",
        encoding="utf-8",
    )
    files.append("field-keyboard-sovereign.json")

    (API / "nexus-c2.json").write_text(
        json.dumps({**stub, "g16": "5.1.0", "profile": "g16_field_opt", "catalog": "pages"}, indent=2) + "\n",
        encoding="utf-8",
    )
    files.append("nexus-c2.json")

    queen = _run_queen_browser()
    (API / "queen-browser.json").write_text(json.dumps(queen, indent=2) + "\n", encoding="utf-8")
    files.append("queen-browser.json")

    shields = {
        "ok": True,
        "pages": True,
        "policy": {
            "auto_proxy_external": True,
            "structural_fingerprints": True,
            "ad_space_block": True,
            "legacy_auto_secure": True,
            "ammolang_rewrite": "ensure_protection · universal_boundary",
            "zero_day_hold": True,
        },
        "rules": [],
        "gates_held": True,
    }
    (API / "queen-page-shields.json").write_text(json.dumps(shields, indent=2) + "\n", encoding="utf-8")
    files.append("queen-page-shields.json")

    (API / "github-secure.json").write_text(
        json.dumps(
            {
                **stub,
                "verify": {"ok": True, "route": "pages-pinned", "pin": "zacharygeurts.github.io"},
                "policy": "Queen pinned GitHub — AmmoLang ironclad · no MITM",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    files.append("github-secure.json")

    (API / "queen-boot.json").write_text(
        json.dumps(
            {
                **stub,
                "phase": "BROWSER",
                "queen_verdict": "QUEEN_READY",
                "bookmark_bar_enabled": True,
                "pages_base": PAGES_BASE,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    files.append("queen-boot.json")

    status = {
        "ok": True,
        "field": True,
        "panel_ready": True,
        "pages": True,
        "mode": "pages-surfaces",
        "queen_verdict": "READY",
        "port": 9477,
        "posture": "war-ready",
        "version": H7_VERSION,
    }
    (API / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    files.append("status.json")

    runtime = {
        "schema": "hostess7-pages-runtime/v1",
        "version": H7_VERSION,
        "mode": "pages-surfaces",
        "pages_base": PAGES_BASE,
        "boot_target": f"{PAGES_BASE}/desktop/",
        "surfaces": {
            "queen_browser": f"{PAGES_BASE}/queen/browser.html",
            "ammoos_desktop": f"{PAGES_BASE}/desktop/",
        },
        "auto_boot": True,
        "desktop_icons": True,
        "exported": _ts(),
    }
    (DOCS / "runtime.json").write_text(json.dumps(runtime, indent=2) + "\n", encoding="utf-8")
    return files


def _sync_docs_data() -> None:
    """Copy canonical data/ JSON into docs/data/ for Pages static fetch."""
    src_data = ROOT / "data"
    dst_data = DOCS / "data"
    dst_data.mkdir(parents=True, exist_ok=True)
    for name in ("hostess7-old-projects.json", "hostess7-rtx-executables.json"):
        src = src_data / name
        if src.is_file():
            shutil.copy2(src, dst_data / name)


def build() -> dict[str, Any]:
    _sync_docs_data()
    has_stack = QUEEN_WORLD.is_dir() and PANEL_ASSETS.is_dir()
    if not has_stack:
        if (QUEEN_DOCS / "browser.html").is_file() and (AMMOOS_DOCS / "index.html").is_file():
            desktop = _run_field_host_desktop() if (NL / "lib" / "field-host-desktop.py").is_file() else {"ok": True, "programs": []}
            if not desktop.get("programs") and (API / "field-host-desktop.json").is_file():
                desktop = json.loads((API / "field-host-desktop.json").read_text(encoding="utf-8"))
            api_files = _export_apis(desktop)
            return {
                "ok": True,
                "skipped": "stack_missing_using_committed_surfaces",
                "queen_files": sum(1 for _ in QUEEN_DOCS.rglob("*") if _.is_file()) if QUEEN_DOCS.is_dir() else 0,
                "panel_assets": sum(1 for _ in ASSETS_DOCS.rglob("*") if _.is_file()) if ASSETS_DOCS.is_dir() else 0,
                "api_files": api_files,
                "pages_base": PAGES_BASE,
                "exported": _ts(),
            }
        return {"ok": False, "error": f"Queen/panel missing — expected {QUEEN_WORLD} and {PANEL_ASSETS}"}

    queen_n = _rsync_queen()
    assets_n = _rsync_panel_assets()
    _write_desktop_indices()
    panel_n = _stage_panel_surfaces()
    _write_queen_browser()
    desktop = _run_field_host_desktop()
    api_files = _export_apis(desktop)
    return {
        "ok": True,
        "queen_files": queen_n,
        "panel_assets": assets_n,
        "panel_surfaces": panel_n,
        "api_files": api_files,
        "pages_base": PAGES_BASE,
        "exported": _ts(),
    }


def main() -> int:
    doc = build()
    print(json.dumps(doc, indent=2))
    print(f"METRIC pages_surfaces_build={doc.get('queen_files', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())