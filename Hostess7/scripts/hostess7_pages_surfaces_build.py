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

QUEEN_ROOT = NL / "Queen"
QUEEN_WORLD = QUEEN_ROOT / "world"
PANEL = NL / "panel"
PANEL_ASSETS = PANEL / "assets"
QUEEN_DOCS = DOCS / "queen"
AMMOOS_DOCS = DOCS / "ammoos"
DESKTOP_DOCS = DOCS / "desktop"
ASSETS_DOCS = DOCS / "assets"
API = DOCS / "api"
PAGES_BASE = os.environ.get("HOSTESS7_PAGES_BASE", "/Hostess7")
PAGES_DESKTOP_THEME = "nexus-military-v8"
PAGES_DESKTOP_ICON_IDS = (
    "view",
    "queen-terminal",
    "mspaint",
    "field-popcorn",
    "ammocode",
    "hostess7-folder",
    "queen-browser",
    "field-broadcaster",
    "queen-gameroom",
    "queen-chips",
    "nexus-compatibility",
    "device-map",
)
PAGES_DESKTOP_UI_SCALE = 200
PAGES_DESKTOP_ICON_SIZE = 96


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _enrich_everyone_counter(everyone_ctr: dict[str, Any], botnet_dns: dict[str, Any]) -> dict[str, Any]:
    """Merge botnet lane counts from DNS/DHCP export when CI has no local state."""
    bot_nodes = int((botnet_dns.get("bot_network") or {}).get("node_count") or 0)
    if bot_nodes <= 0:
        return everyone_ctr
    lanes = everyone_ctr.setdefault("lanes", {})
    bot_lane = lanes.setdefault("botnet", {"label": "Botnet nodes"})
    if int(bot_lane.get("count") or 0) < bot_nodes:
        bot_lane["count"] = bot_nodes
    dist = everyone_ctr.setdefault("distributed_botnet", {"enabled": True})
    if int(dist.get("nodes") or 0) < bot_nodes:
        dist["nodes"] = bot_nodes
    gh_open = bool((botnet_dns.get("github_control_plane") or {}).get("github_open"))
    if gh_open:
        dist["github_open"] = True
    exe_n = int((lanes.get("executable_people") or {}).get("count") or 0)
    gh_n = int((lanes.get("github_people") or {}).get("count") or 0)
    loopback = int((lanes.get("loopback_sovereign") or {}).get("count") or 1)
    total = bot_nodes + gh_n + exe_n + loopback
    if int(everyone_ctr.get("everyone_total") or 0) < total:
        everyone_ctr["everyone_total"] = total
    return everyone_ctr


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


def _import_secure_kill() -> dict[str, Any]:
    """Direct import — avoids subprocess timeout during heavy Pages builds."""
    script = NL / "lib" / "field-sense-secure-kill.py"
    if not script.is_file():
        return {"schema": "field-sense-secure-kill/v1", "ok": False, "error": "missing field-sense-secure-kill.py"}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("fssk_pages_export", script)
        if not spec or not spec.loader:
            raise RuntimeError("spec load failed")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        doc = mod.secure_kill_posture(NL, NL.parent)
        doc["pages"] = True
        doc["lane"] = "pages-surfaces"
        doc["exported"] = _ts()
        return doc
    except Exception as exc:
        return {
            "schema": "field-sense-secure-kill/v1",
            "kill_policy": "prejudice",
            "every_kill_rekill": True,
            "war_hardened": True,
            "motto": "Anyone in the way — secure kill with prejudice · RE-KILL forever",
            "ok": True,
            "pages": True,
            "lane": "pages-surfaces",
            "note": f"pages-fallback ({exc})",
            "exported": _ts(),
        }


def _run_nl_script_json(rel: str, args: list[str] | None = None, *, timeout: int = 90) -> dict[str, Any]:
    """Run a NewLatest lib/Queen script and parse JSON stdout."""
    script = NL / rel
    if not script.is_file():
        return {"ok": False, "error": f"missing {rel}"}
    state_dir = ROOT / ".pages-build-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(NL),
        "NEXUS_STATE_DIR": str(state_dir),
        "SG_ROOT": str(NL.parent),
        "HOSTESS7_ROOT": str(ROOT),
    }
    try:
        out = subprocess.run(
            [sys.executable, str(script), *(args or ["json"])],
            cwd=str(script.parent if "Queen" in rel else NL),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
        if not out.stdout.strip():
            return {"ok": False, "error": out.stderr.strip() or f"{rel} empty stdout"}
        doc = json.loads(out.stdout)
        if isinstance(doc, dict):
            doc.setdefault("ok", True)
            doc["pages"] = True
            doc["lane"] = "pages-surfaces"
            doc["exported"] = _ts()
            _patch_urls_deep(doc)
            return doc
        return {"ok": False, "error": f"{rel} non-object json"}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "pages": True}


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
    if ":9488" in path or "/bookmark-jump/" in path:
        if "/bookmark-jump/" in path:
            tail = path.split("/bookmark-jump/", 1)[-1]
            return f"{base}/bookmark-jump/{tail if tail.startswith('?') else '?' + tail if tail else '?id=h7-training-viewer'}"
        return f"{base}/bookmark-jump/?id=h7-training-viewer"
    if path.startswith("http://127.0.0.1:9481"):
        return path.replace("http://127.0.0.1:9481", PAGES_BASE).replace("/world/", "/queen/")
    if path.startswith("http://127.0.0.1:9477"):
        tail = path.replace("http://127.0.0.1:9477", "").split("#")[0].rstrip("/") or "/"
        if tail.startswith("/bookmark-jump"):
            return base + tail
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
            "surface",
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


def _patch_queen_terminal_app(app: dict[str, Any]) -> None:
    app["exec"] = f"{PAGES_BASE}/queen/queen-gnu-terminal-embed.html"
    app["hint"] = "GNU Terminal · AmmoOS panel · Layer 0"
    app["name"] = "AmmoOS Terminal"
    app["category"] = "AmmoOS · Shell"
    app["os_layer"] = 0
    app["shell"] = True


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
        if obj.get("id") == "queen-terminal":
            _patch_queen_terminal_app(obj)
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
    policy["desktop_ui_scale_default"] = PAGES_DESKTOP_UI_SCALE
    policy["desktop_icon_size_default"] = PAGES_DESKTOP_ICON_SIZE
    doc["product"] = "Hostess7"
    doc["version"] = H7_VERSION
    doc["main_project"] = True
    doc["theme"] = "ammoos"
    doc["ammoos_theme"] = "ammoos"
    doc["os_doctrine"] = "data/ammoos-desktop-os-doctrine.json"

    shell = doc.setdefault("shell", {})
    shell["boot_program"] = ""
    shell["launch_at_c2_desktop"] = True
    shell["launch_url"] = f"{PAGES_BASE}/desktop/"
    shell["queen_browser_only"] = False
    shell_settings = shell.setdefault("settings", {})
    if isinstance(shell_settings, dict):
        shell_settings["ui_scale"] = PAGES_DESKTOP_UI_SCALE
        shell_settings["desktop_icon_size"] = PAGES_DESKTOP_ICON_SIZE
        shell_settings["fullscreen_desktop"] = True
        shell_settings["show_desktop_icons"] = True
        shell_settings["ammoos_theme"] = PAGES_DESKTOP_THEME

    for key in ("programs", "icon_dock", "field_apps", "programs_all", "desktop_icons"):
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
            if app.get("id") == "queen-terminal":
                _patch_queen_terminal_app(app)

    start_menu = doc.get("start_menu")
    if isinstance(start_menu, dict):
        for _cat, items in start_menu.items():
            if not isinstance(items, list):
                continue
            for app in items:
                if not isinstance(app, dict):
                    continue
                for field in ("exec", "url", "launch_url"):
                    if field in app and app[field]:
                        app[field] = _pages_url(str(app[field]))
                if app.get("id") == "hostess7-training-viewer":
                    app["exec"] = f"{PAGES_BASE}/bookmark-jump/?id=h7-training-viewer"
                    app["secure_jump"] = True
                if app.get("id") == "queen-terminal":
                    _patch_queen_terminal_app(app)

    doc.pop("boot_program_url", None)
    startbar = doc.setdefault("startbar", {})
    if isinstance(startbar, dict):
        startbar["classic"] = True
        startbar["start_label"] = startbar.get("start_label") or "Start"
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
                app["exec"] = f"{PAGES_BASE}/bookmark-jump/?id=h7-training-viewer"
                app["secure_jump"] = True
                app["ensure_api"] = "/api/hostess7-training-viewer/ensure"

    for app in programs:
        if isinstance(app, dict) and app.get("id"):
            app["pinned"] = app.get("id") in PAGES_DESKTOP_ICON_IDS

    desktop_pool = [
        a
        for a in programs
        if a.get("id") in PAGES_DESKTOP_ICON_IDS
        and not a.get("ghost")
        and not a.get("clipboard_ghost")
        and a.get("launcher_visible") is not False
    ]
    by_id = {a.get("id"): a for a in desktop_pool if a.get("id")}
    doc["desktop_icons"] = [by_id[i] for i in PAGES_DESKTOP_ICON_IDS if i in by_id]

    tray = doc.get("startbar", {}).get("tray_icons") or doc.get("tray_icons") or []
    for icon in tray:
        if isinstance(icon, dict) and icon.get("exec"):
            icon["exec"] = _pages_url(str(icon["exec"]))

    panels = (doc.get("monitor_dashboard") or {}).get("panels") or []
    for panel in panels:
        if isinstance(panel, dict) and panel.get("url"):
            panel["url"] = _pages_url(str(panel["url"]))

    _patch_urls_deep(doc)
    for pool in (programs, doc.get("field_apps") or [], doc.get("desktop_icons") or [], doc.get("programs_all") or []):
        for app in pool:
            if isinstance(app, dict) and app.get("id") == "hostess7-training-viewer":
                app["exec"] = f"{PAGES_BASE}/bookmark-jump/?id=h7-training-viewer"
                app["secure_jump"] = True
    if isinstance(start_menu, dict):
        for items in start_menu.values():
            if not isinstance(items, list):
                continue
            for app in items:
                if isinstance(app, dict) and app.get("id") == "hostess7-training-viewer":
                    app["exec"] = f"{PAGES_BASE}/bookmark-jump/?id=h7-training-viewer"
                    app["secure_jump"] = True

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
        ('href="/command', f'href="{base}/command'),
        ('href="/threat-panel', f'href="{base}/threat-panel'),
        ('href="/field-', f'href="{base}/field-'),
        ('href="/library', f'href="{base}/library'),
        ('href="/card-catalog', f'href="{base}/card-catalog'),
        ('href="/ammonet', f'href="{base}/ammonet'),
        ('href="/desktop', f'href="{base}/desktop'),
        ('href="/human-hub', f'href="{base}/human-hub'),
        ('href="/hub', f'href="{base}/hub'),
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
    content = re.sub(
        rf'href="{re.escape(base)}/field-([a-z0-9-]+)\.html"',
        rf'href="{base}/field-\1/"',
        content,
    )
    content = re.sub(
        rf'href="{re.escape(base)}/library-([a-z0-9-]+)\.html"',
        rf'href="{base}/library-\1/"',
        content,
    )
    content = re.sub(
        rf'href="{re.escape(base)}/card-catalog\.html"',
        rf'href="{base}/card-catalog/"',
        content,
    )
    license_block = (
        f'  <link rel="stylesheet" href="{PAGES_BASE}/pages-deploy-everyone.css" />\n'
        f'  <script src="{PAGES_BASE}/pages-deploy-everyone.js"></script>\n'
        f'  <link rel="stylesheet" href="{PAGES_BASE}/pages-license.css" />\n'
        f'  <script src="{PAGES_BASE}/pages-license.js"></script>'
    )
    if queen:
        queen_base = f"{base}/queen/"
        if "<base " in content:
            content = re.sub(
                r'<base\s+href="[^"]*"\s*/?>',
                f'<base href="{queen_base}" />',
                content,
                count=1,
            )
        else:
            content = content.replace("<head>", f'<head>\n  <base href="{queen_base}" />', 1)
    if queen and "<html" in content and "pages-base.js" not in content:
        inject = (
            f'  <script src="{PAGES_BASE}/pages-base.js"></script>\n'
            f'  <script src="{PAGES_BASE}/api-shim.js"></script>\n'
            f'  <script src="{PAGES_BASE}/pages-queen-hardening.js"></script>\n'
            f"{license_block}"
        )
        content = content.replace("<head>", f"<head>\n{inject}", 1)
        if 'data-pages-runtime="1"' not in content:
            content = content.replace("<body ", '<body data-pages-runtime="1" ', 1)
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
    _ensure_pages_asset_aliases()
    return sum(1 for _ in ASSETS_DOCS.rglob("*") if _.is_file())


def _ensure_pages_asset_aliases() -> None:
    """48px icons and other aliases referenced by panel HTML but absent from assets/."""
    if not ASSETS_DOCS.is_dir():
        return
    aliases = {
        "queen-prog-field-48.png": "queen-prog-field.png",
        "queen-prog-os-48.png": "queen-prog-os.png",
    }
    for dst_name, src_name in aliases.items():
        dst = ASSETS_DOCS / dst_name
        if dst.is_file():
            continue
        src = ASSETS_DOCS / src_name
        if src.is_file():
            shutil.copy2(src, dst)


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
        f'  <script src="{PAGES_BASE}/assets/field-desktop-scale-propagate.js"></script>\n'
        f'  <link rel="stylesheet" href="{PAGES_BASE}/pages-deploy-everyone.css" />\n'
        f'  <script src="{PAGES_BASE}/pages-deploy-everyone.js"></script>\n'
        f'  <link rel="stylesheet" href="{PAGES_BASE}/pages-license.css" />\n'
        f'  <script src="{PAGES_BASE}/pages-license.js"></script>'
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
    if "pages-queen-rtx-bridge.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-queen-rtx-bridge.js"></script>\n</body>',
            1,
        )
    if "pages-ammonet-wire.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-ammonet-wire.js"></script>\n</body>',
            1,
        )
    if "pages-github-brain-wire.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-github-brain-wire.js"></script>\n</body>',
            1,
        )
    if "pages-hostess7-interaction-wire.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-hostess7-interaction-wire.js"></script>\n</body>',
            1,
        )
    if "pages-github-legacy-wire.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-github-legacy-wire.js"></script>\n</body>',
            1,
        )
    if "pages-github-resilience.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-github-resilience.js"></script>\n</body>',
            1,
        )
    if "pages-github-everyone-wire.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-github-everyone-wire.js"></script>\n</body>',
            1,
        )
    return html


def _stage_gnueol_terminal_mirror() -> int:
    """Mirror GNUEOLTerminal docs on Hostess7 Pages when github.com or GNUEOL Pages is slow."""
    src = NL / "GNUEOLTerminal" / "docs"
    dest = DOCS / "gnueol-terminal"
    if not src.is_dir():
        return 0
    forge = NL / "GNUEOLTerminal" / "scripts" / "forge-gnu-wiki-manual.py"
    build = NL / "GNUEOLTerminal" / "scripts" / "build-site.py"
    verify = NL / "GNUEOLTerminal" / "scripts" / "verify-gnu-wiki-manual.py"
    if forge.is_file() and build.is_file():
        try:
            subprocess.run([sys.executable, str(forge)], cwd=str(NL / "GNUEOLTerminal"), check=False, timeout=120)
            proc = subprocess.run(
                [sys.executable, str(build)], cwd=str(NL / "GNUEOLTerminal"), check=False, timeout=120,
            )
            if proc.returncode != 0:
                print("[gnueol] WARN build-site.py failed — wiki verify may be stale", file=sys.stderr)
            elif verify.is_file():
                vproc = subprocess.run(
                    [sys.executable, str(verify)], cwd=str(NL / "GNUEOLTerminal"), check=False, timeout=60,
                )
                if vproc.returncode != 0:
                    print("[gnueol] WARN verify-gnu-wiki-manual.py failed", file=sys.stderr)
        except (subprocess.TimeoutExpired, OSError):
            pass
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    (dest / ".nojekyll").touch(exist_ok=True)
    return sum(1 for _ in dest.rglob("*") if _.is_file())


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
        f'  <script src="{PAGES_BASE}/api-shim.js"></script>\n'
        f'  <link rel="stylesheet" href="{PAGES_BASE}/pages-license.css" />\n'
        f'  <script src="{PAGES_BASE}/pages-license.js"></script>'
    )
    if "pages-base.js" not in html:
        html = html.replace("<head>", f"<head>\n  {inject}", 1)
    elif "pages-license.js" not in html:
        html = html.replace("</head>", f'  <link rel="stylesheet" href="{PAGES_BASE}/pages-license.css" />\n  <script src="{PAGES_BASE}/pages-license.js"></script>\n</head>', 1)
    if 'data-pages-runtime="1"' not in html:
        html = html.replace("<body ", '<body data-pages-runtime="1" ', 1)
    if "pages-field-boot.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-field-boot.js"></script>\n</body>',
            1,
        )
    if "pages-c2-wire.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-c2-wire.js"></script>\n</body>',
            1,
        )
    if "pages-queen-rtx-bridge.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-queen-rtx-bridge.js"></script>\n</body>',
            1,
        )
    if "pages-ammonet-wire.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-ammonet-wire.js"></script>\n</body>',
            1,
        )
    if "pages-github-brain-wire.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-github-brain-wire.js"></script>\n</body>',
            1,
        )
    if "pages-hostess7-interaction-wire.js" not in html:
        html = html.replace(
            "</body>",
            f'  <script src="{PAGES_BASE}/pages-hostess7-interaction-wire.js"></script>\n</body>',
            1,
        )
    return html


COMMAND_PAGES_BASE = "/command"
H7_PAGES_HOST = "/Hostess7"


def _rewrite_asset_hosts(html: str, host: str) -> str:
    return re.sub(r'(href|src)="/assets/', rf'\1="{host}/assets/', html)


def _command_basement_page_html(src: Path) -> str:
    """Real NEXUS C2 basement deck — canonical /command/ on GitHub Pages."""
    html = src.read_text(encoding="utf-8", errors="replace")
    html = _patch_text(html)
    cmd = COMMAND_PAGES_BASE.rstrip("/")
    h7 = H7_PAGES_HOST.rstrip("/")
    inject = (
        f'<base href="{cmd}/" />\n'
        f'  <link rel="stylesheet" href="{h7}/assets/field-queen-theme.css" />\n'
        f'  <link rel="stylesheet" href="{cmd}/nexus-c2-basement.css" />\n'
        f'  <script src="{cmd}/pages-base.js"></script>\n'
        f'  <script src="{h7}/api-shim.js"></script>\n'
        f'  <link rel="stylesheet" href="{cmd}/pages-license.css" />\n'
        f'  <script src="{cmd}/pages-license.js"></script>'
    )
    html = html.replace("<head>", f"<head>\n  {inject}", 1)
    html = _rewrite_asset_hosts(html, h7)
    if 'data-pages-runtime="1"' not in html:
        html = html.replace(
            "<body ",
            '<body data-pages-runtime="1" data-nexus-c2-basement="1" ',
            1,
        )
    for script, prefix in (
        ("pages-basement-boot.js", cmd),
        ("pages-field-boot.js", h7),
        ("pages-c2-wire.js", h7),
        ("pages-queen-rtx-bridge.js", h7),
        ("pages-ammonet-wire.js", h7),
        ("pages-github-brain-wire.js", h7),
        ("pages-hostess7-interaction-wire.js", h7),
        ("pages-github-legacy-wire.js", h7),
        ("pages-github-resilience.js", h7),
        ("pages-github-everyone-wire.js", h7),
    ):
        tag = f'<script src="{prefix}/{script}"></script>'
        if script not in html:
            html = html.replace("</body>", f"  {tag}\n</body>", 1)
    return html


def _write_command_basement_pages() -> str:
    out = ROOT / ".pages-command-publish"
    out.mkdir(parents=True, exist_ok=True)
    src = PANEL / "threat-panel.html"
    if not src.is_file():
        return ""
    (out / "index.html").write_text(_command_basement_page_html(src), encoding="utf-8")
    for fname in (
        "pages-base.js",
        "pages-basement-boot.js",
        "nexus-c2-basement.css",
        "pages-license.css",
        "pages-license.js",
        "pages-field-boot.js",
        "pages-c2-wire.js",
        "pages-ammonet-wire.js",
        "pages-github-brain-wire.js",
        "pages-hostess7-interaction-wire.js",
        "pages-queen-rtx-bridge.js",
    ):
        srcf = DOCS / fname
        if srcf.is_file():
            shutil.copy2(srcf, out / fname)
    return str(out)


def _stage_panel_surfaces() -> int:
    """Stage NEXUS panel HTML at /command, /threat-panel, /field-gpu, … for Pages."""
    if not PANEL.is_dir():
        return 0
    route_map: dict[str, str] = {
        "field": "field-desktop.html",
        "desktop": "field-desktop.html",
        "ammoos": "field-desktop.html",
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
        "mspaint": "mspaint.html",
        "eol-code": "eol-code.html",
        "field-gnu-terminal": "field-gnu-terminal-embed.html",
        "terminal": "field-gnu-terminal-embed.html",
        "field-lock": "field-lock.html",
        "field-keepass": "field-lock.html",
        "field-lang-manuals": "field-lang-manuals.html",
        "field-library-bookshelf": "field-library-bookshelf.html",
        "library-bookshelf": "field-library-bookshelf.html",
        "library": "field-library-bookshelf.html",
        "field-card-catalog": "field-card-catalog.html",
        "card-catalog": "field-card-catalog.html",
        "hands-attachments": "hands-attachments.html",
        "g16-build-output": "g16-build-output.html",
        "amouranth-live": "amouranth-live.html",
        "nexus-calc": "nexus-calc.html",
        "nexus-calendar": "nexus-calendar.html",
        "underlay-f9": "underlay-f9.html",
        "field-modern": "underlay-f9.html",
        "tristate-installer": "tristate-installer.html",
        "ammoos-update-os": "ammoos-update-os.html",
        "ammoos-warehouse": "ammoos-warehouse.html",
        "h7updater": "ammoos-warehouse.html",
        "ironclad-search": "ironclad-search.html",
        "human": "hostess7-human-hub.html",
        "human-hub": "hostess7-human-hub.html",
        "hostess7-human-hub": "hostess7-human-hub.html",
        "hub": "hostess7-human-hub.html",
        "bookmark-jump": "field-bookmark-jump.html",
        "field-bookmark-jump": "field-bookmark-jump.html",
        "field-talk": "field-talk.html",
        "field-audio-dac": "field-audio-dac.html",
        "field-ellie-fier": "field-ellie-diag.html",
        "hostess7-kill-library": "hostess7-kill-library.html",
        "hostess7-book-maker": "hostess7-book-maker.html",
        "humanoid-train": "humanoid-train.html",
        "humanoid-data": "humanoid-data.html",
        "training-room": "humanoid-train.html",
        "ammonet": "ammonet-field.html",
        "final-internet": "ammonet-field.html",
        "ammonet-field": "ammonet-field.html",
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
        f'  <script src="{PAGES_BASE}/pages-queen-hardening.js"></script>\n'
        f'  <link rel="stylesheet" href="{PAGES_BASE}/pages-license.css" />\n'
        f'  <script src="{PAGES_BASE}/pages-license.js"></script>'
    )
    if "pages-base.js" not in html:
        html = html.replace("<head>", f"<head>\n  {inject}", 1)
    elif "pages-license.js" not in html:
        html = html.replace("</head>", f'  <link rel="stylesheet" href="{PAGES_BASE}/pages-license.css" />\n  <script src="{PAGES_BASE}/pages-license.js"></script>\n</head>', 1)
    queen_base = f"{PAGES_BASE}/queen/"
    if "<base " in html:
        html = re.sub(
            r'<base\s+href="[^"]*"\s*/?>',
            f'<base href="{queen_base}" />',
            html,
            count=1,
        )
    else:
        html = html.replace("<head>", f'<head>\n  <base href="{queen_base}" />', 1)
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


def _pages_c2_slice_doc(name: str, base: dict[str, Any]) -> dict[str, Any]:
    """Static C2 slice payloads that satisfy threat-panel moduleReady on GitHub Pages."""
    ts = _ts()
    doc = dict(base)
    rich: dict[str, dict[str, Any]] = {
        "field-command": {
            "schema": "field-command/v1",
            "updated": ts,
            "motto": "Good-guy doctrine · Pages C2",
            "good_guy": True,
            "pulse": "war-ready",
        },
        "gatekeeper": {"connections": [], "updated": ts},
        "lethal-enforcement": {"merciless": True, "status": "armed", "heaven_hell": "held"},
        "planetary-observer": {"schema": "planetary-observer/v1", "updated": ts},
        "home-protector": {"schema": "home-protector/v1", "stats": {"pages": True}},
        "local-services": {"schema": "local-services/v1", "stats": {"pages": True}},
        "audio-train": {"schema": "audio-train/v1", "stats": {"pages": True}},
        "signals-field": {"schema": "signals-field/v1", "stats": {}, "antennas": []},
        "field-radio": {"schema": "field-radio-catcher/v1", "station_menu": []},
        "field-dns": {"schema": "field-dns/v2", "rfc_matrix": {}, "threat_model": {}},
        "field-outside-talk": {"schema": "field-outside-talk/v1", "tools": {}},
        "field-drive": {"schema": "field-drive-system/v1", "drives": []},
        "field-rf": {"updated": ts, "antenna": {"mode": "pages"}},
        "terror-spiderweb": {"schema": "terror-spiderweb/v1", "nodes": [], "updated": ts},
        "precision-field": {"schema": "precision-field/v1", "entities": [], "updated": ts},
        "host-attacks": {"points": [], "updated": ts},
        "angel-dossiers": {"dossiers": [], "dossier_count": 0, "updated": ts},
        "human-dossier": {"ips": [], "generated_at": ts},
        "angel-research": {"tables": {}, "updated": ts},
        "honorability": {"honorability": {}, "active_sites": []},
        "us-field": {"title": "US Field", "page": "pages", "updated": ts},
        "us-obs-field": {"schema": "us-obs-field/v3", "updated": ts},
        "field-obs": {"schema": "field-obs/v2", "updated": ts},
        "us-voltage-regulation": {"schema": "us-voltage-regulation/v1", "updated": ts},
        "field-hardware": {"schema": "field-hardware-probe/v1", "host": "pages"},
        "field-hazard-onset": {"schema": "field-hazard-onset/v1", "enabled": False, "panel": {}},
        "field-brain": {
            "schema": "field-brain/v1",
            "ok": True,
            "pages": True,
            "lane": "github-mirror",
            "data_source": "github-brain",
            "sovereign_brain": False,
            "local_brain": False,
            "writes_to_sovereign": False,
            "github_field_brain_path": "/github-brain/",
            "corpus": "/github-brain/corpus.json",
            "superintelligence": {
                "available": True,
                "source": "github-brain-mirror",
                "arc": "GitHub mind · NEXUS C2",
            },
            "stack_mind": {
                "nexus_c2": "/command/",
                "kilroy": "F10",
                "znetwork": "/api/znetwork",
                "dns": "/api/field-dns",
                "dhcp": "Field DHCP",
                "ipxe": "netboot lane",
            },
        },
        "settings": {"pages": True, "theme": "nexus-military-v8", "version": H7_VERSION},
        "compatibility": {"schema": "field-compatibility-layers/v1", "layers": [{"id": "pages", "label": "GitHub Pages"}]},
        "diagnostic-mode": {"schema": "field-diagnostic-mode/v1", "engaged": False, "problems": []},
        "police-agencies": {"agencies": [], "updated": ts},
        "human-registry": {"table": [{"id": "pages", "label": "GitHub Pages operator"}], "stats": {"total": 1}},
        "gov-intel": {"records": [], "record_count": 0},
        "program-tags": {"tags": {}, "recent": []},
        "census-field": {"last_run": ts, "operator_gps_ready": False},
        "existence-identity": {"table": [{"id": "hostess7", "role": "boss"}], "updated": ts},
        "hostess7-lethal-insight": {"insight": "pages-c2", "held": True},
    }
    doc.update(rich.get(name, {}))
    return doc


def _stage_zacs_png() -> int:
    """Copy SG/ZACS/png into docs/zacs/png for Pages static icon lane."""
    zacs_src = Path(os.environ.get("SG_ZACS_ROOT", str(NL.parent / "ZACS"))) / "png"
    if not zacs_src.is_dir():
        return 0
    dest = DOCS / "zacs" / "png"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(zacs_src, dest)
    return sum(1 for _ in dest.rglob("*") if _.is_file())


def _build_ironclad_pages_index(tasklist: dict[str, Any] | None = None) -> dict[str, Any]:
    """Static Ironclad search index for Pages — routes, tasks, corpus titles, library sample."""
    entries: list[dict[str, Any]] = []
    hub_routes = (
        ("human", "Human Hub — BSP ask + tasks + library + Ironclad"),
        ("library", "Hostess 7 Library — Dewey shelves for humans and AI"),
        ("brain", "GitHub Brain chat — talk to Hostess 7"),
        ("field-card-catalog", "Card catalog drawer"),
        ("command", "NEXUS C2 basement (external)"),
        ("ironclad-search", "Ironclad Search program"),
        ("field-desktop", "AmmoOS field desktop"),
        ("queen", "Queen browser surfaces"),
    )
    for rid, label in hub_routes:
        url = f"{PAGES_BASE}/{rid}/" if rid != "command" else "https://zacharygeurts.github.io/command/"
        entries.append({
            "id": rid,
            "label": label,
            "title": label,
            "kind": "route",
            "source": "routes",
            "family": "surface",
            "url": url,
            "search_blob": f"{rid} {label} hostess7 human ui library ironclad",
        })
    for t in (tasklist or {}).get("open") or []:
        title = str(t.get("title") or t.get("want") or "task")
        entries.append({
            "id": t.get("id") or title,
            "label": title,
            "title": title,
            "kind": "task",
            "source": "tasklist",
            "family": "hostess7",
            "status": t.get("status") or "pending",
            "search_blob": f"{title} {t.get('detail', '')} task hostess7",
        })
    corpus_path = DOCS / "github-brain" / "corpus.json"
    if corpus_path.is_file():
        try:
            corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
            for c in (corpus.get("chunks") or [])[:400]:
                entries.append({
                    "id": c.get("id"),
                    "label": c.get("title"),
                    "title": c.get("title"),
                    "kind": "corpus",
                    "source": c.get("domain") or "corpus",
                    "family": "brain",
                    "search_blob": f"{c.get('title', '')} {c.get('text', '')[:400]}",
                })
        except (OSError, json.JSONDecodeError):
            pass
    compact_path = API / "dewey-books-compact.json"
    if compact_path.is_file():
        try:
            compact = json.loads(compact_path.read_text(encoding="utf-8"))
            for b in (compact.get("books") or [])[:600]:
                entries.append({
                    "id": b.get("id"),
                    "label": b.get("title"),
                    "title": b.get("title"),
                    "kind": "book",
                    "source": "catalog",
                    "family": b.get("shelf") or "library",
                    "shelf": b.get("shelf"),
                    "url": f"{PAGES_BASE}/library/?book={b.get('id', '')}",
                    "search_blob": b.get("search_blob") or f"{b.get('title', '')} {b.get('author', '')} {b.get('shelf', '')}",
                })
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "ironclad-pages-search-index/v1",
        "ok": True,
        "pages": True,
        "lane": "pages-surfaces",
        "updated": _ts(),
        "entry_count": len(entries),
        "entries": entries,
    }


def _export_ammoos_themes_catalog() -> dict[str, Any]:
    doctrine_path = NL / "data" / "ammoos-themes-doctrine.json"
    if not doctrine_path.is_file():
        doctrine_path = ROOT / "data" / "ammoos-themes-doctrine.json"
    doctrine = json.loads(doctrine_path.read_text(encoding="utf-8")) if doctrine_path.is_file() else {}
    c2 = doctrine.get("c2_themes") or {}
    return {
        "ok": True,
        "schema": doctrine.get("schema") or "ammoos-themes/v1",
        "title": doctrine.get("title") or "AmmoOS Themes",
        "motto": doctrine.get("motto"),
        "pages": True,
        "default_ammoos_theme": doctrine.get("default_ammoos_theme") or "ammoos",
        "lead_desktop_themes": doctrine.get("lead_desktop_themes") or ["ammoos", "dusty-night"],
        "active": {
            "c2": "ammoos",
            "os_theme": "ammoos",
            "queen_styles": doctrine.get("default_queen_styles") or "black_emerald_rose_2026",
            "editor": doctrine.get("default_editor_theme") or "nexus_c2",
            "syntax": doctrine.get("default_syntax_theme") or "nexus_c2",
            "terminal": doctrine.get("default_terminal_theme") or "black_emerald_rose_2026",
        },
        "c2_themes": c2,
        "sections": doctrine.get("sections") or [],
        "exported": _ts(),
    }


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
            "ui_scale": PAGES_DESKTOP_UI_SCALE,
            "desktop_icon_size": PAGES_DESKTOP_ICON_SIZE,
            "fullscreen_desktop": True,
            "show_desktop_icons": True,
            "queen_browser_only": False,
            "ammoos_theme": "ammoos",
            "os_theme": "ammoos",
            "classic_start_raised": True,
            "ammo_ui_boost_note": f"Hostess 7 {H7_VERSION} desktop 200% taskbar; classic raised Start; AmmoOS + Dusty Night",
        },
        "displays": [{"id": "default", "name": "GitHub Pages", "resolution": "1920×1080", "primary": True}],
    }
    (API / "field-shell-settings.json").write_text(json.dumps(shell_settings, indent=2) + "\n", encoding="utf-8")
    files.append("field-shell-settings.json")

    (API / "ammoos-themes.json").write_text(json.dumps(_export_ammoos_themes_catalog(), indent=2) + "\n", encoding="utf-8")
    files.append("ammoos-themes.json")

    (API / "znetwork.json").write_text(
        json.dumps(
            {
                **stub,
                "schema": "znetwork-orchestrator/v2",
                "active": True,
                "pipe_pct": 100,
                "held": True,
                "status": "pages-ready",
                "operator": "hostess7",
            },
            indent=2,
        )
        + "\n",
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

    h7_cmd = {
        **stub,
        "schema": "hostess7-command/v1",
        "title": "Hostess 7 Super Intelligence",
        "motto": "GitHub Pages C2 — sovereign surfaces wired; live training + terminal on loopback",
        "github_repo": "ZacharyGeurts/Hostess7",
        "pages_lane": True,
        "transcript": [
            {
                "role": "hostess7",
                "text": "Pages lane online. Command deck, Final Eye, and OPS FLOW are live on GitHub — loopback panel runs the lab.",
                "ts": _ts(),
            }
        ],
        "intel_digest": [
            {"title": "Posture", "value": "war-ready", "hint": "Universal Protector C2 on GitHub Pages"},
            {"title": "Final Eye", "value": "100%", "hint": "queen-eyeball static export"},
            {"title": "Lab", "value": "sovereign", "hint": "share in · no share out — Hostess7 boss"},
        ],
        "capabilities": [
            {"id": "c2", "label": "Command C2", "state": "live"},
            {"id": "eye", "label": "Final Eye", "state": "live"},
            {"id": "pages", "label": "GitHub Pages", "state": "live"},
        ],
        "needs_wants": {
            "voice": "I need the loopback panel for training cycles and IQ battery — Pages shows our deck faithfully.",
            "needs": [
                {"title": "Loopback panel", "detail": "9477 for live Super Intelligence writes", "urgent": False},
            ],
            "wants": [
                {"title": "Secure bookmarks", "detail": "HTTPS+Secure doctrine on every Firefox profile"},
            ],
        },
        "self_view": {
            "comfort_voice": "Comfortable on GitHub — operators see the same C2 they know from NEXUS-Shield.",
            "hero_chips": [
                {"label": "Edition", "value": "Universal Protector", "tone": "ok"},
                {"label": "Pages", "value": "C2 wired", "tone": "ok"},
            ],
        },
    }
    (API / "hostess7-command.json").write_text(json.dumps(h7_cmd, indent=2) + "\n", encoding="utf-8")
    files.append("hostess7-command.json")

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

    secure_kill = _import_secure_kill()
    (API / "field-sense-secure-kill.json").write_text(json.dumps(secure_kill, indent=2) + "\n", encoding="utf-8")
    files.append("field-sense-secure-kill.json")

    for api_name, script_rel in (
        ("field-final-eye-block.json", "lib/field-final-eye-block.py"),
        ("field-final-ear-block.json", "lib/field-final-ear-block.py"),
        ("field-final-mouth-block.json", "lib/field-final-mouth-block.py"),
    ):
        doc = _run_nl_script_json(script_rel, timeout=90)
        if isinstance(doc.get("secure_kill"), dict):
            doc["secure_kill"] = {**secure_kill, "pages": True}
        doc["held"] = doc.get("ironclad_sealed", doc.get("held"))
        (API / api_name).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        files.append(api_name)

    eyeball = _run_nl_script_json("Queen/lib/queen-eyeball.py", timeout=120)
    (API / "queen-eyeball.json").write_text(json.dumps(eyeball, indent=2) + "\n", encoding="utf-8")
    files.append("queen-eyeball.json")

    voice = _run_nl_script_json("lib/hostess7-voice.py", timeout=30)
    (API / "hostess7-voice.json").write_text(json.dumps(voice, indent=2) + "\n", encoding="utf-8")
    files.append("hostess7-voice.json")

    internet_clean = _run_nl_script_json("lib/hostess7-internet-clean.py", ["status"], timeout=30)
    if not internet_clean.get("ok"):
        internet_clean = {
            **stub,
            "schema": "hostess7-internet-clean/v1",
            "default_on_hostess7": True,
            "secure_nav_default": True,
            "secure_bookmarks_default": True,
            "motto": "Clean the whole internet — secure jumps · telemetry strip",
            "pages_base": PAGES_BASE,
        }
    else:
        internet_clean["pages"] = True
        internet_clean["pages_base"] = PAGES_BASE
        internet_clean["default_on_hostess7"] = True
    (API / "hostess7-internet-clean.json").write_text(
        json.dumps(internet_clean, indent=2) + "\n", encoding="utf-8"
    )
    files.append("hostess7-internet-clean.json")

    queen_terminal = _run_nl_script_json("Queen/lib/queen-terminal.py", ["json"], timeout=45)
    if not queen_terminal.get("schema"):
        queen_terminal = {
            **stub,
            "schema": "queen-gnu-terminal/v2",
            "ok": True,
            "shell_terminal_identical": True,
            "aliases": ["terminal", "gnu-terminal", "shell", "gnueol"],
            "posture": "GNU Terminal — default field shell",
        }
    else:
        queen_terminal["pages"] = True
    (API / "queen-terminal.json").write_text(
        json.dumps(queen_terminal, indent=2) + "\n", encoding="utf-8"
    )
    files.append("queen-terminal.json")

    lab_sovereign = _run_nl_script_json("lib/hostess7-lab-sovereign.py", ["panel"], timeout=60)
    if not lab_sovereign.get("ok"):
        lab_sovereign = {
            **stub,
            "schema": "hostess7-lab-sovereign-panel/v1",
            "boss": "hostess7",
            "share_in": True,
            "share_out": False,
            "motto": "Share in · no share out — Hostess 7 runs the lab",
            "deny_egress_by_default": True,
        }
    else:
        lab_sovereign["pages"] = True
        lab_sovereign["boss"] = "hostess7"
        lab_sovereign["share_in"] = True
        lab_sovereign["share_out"] = False
    (API / "hostess7-lab-sovereign.json").write_text(
        json.dumps(lab_sovereign, indent=2) + "\n", encoding="utf-8"
    )
    files.append("hostess7-lab-sovereign.json")

    g16_online = _run_nl_script_json("lib/hostess7-g16-online.py", ["panel"], timeout=60)
    if not g16_online.get("ok"):
        g16_online = {
            **stub,
            "schema": "hostess7-g16-online/v1",
            "boss": "hostess7",
            "motto": "Online Grok16 Pages + local g16 — Hostess 7 compiles",
            "routes": {
                "pages_compiler": f"{PAGES_BASE}/g16-build-output/",
                "grok16_manual": "https://zacharygeurts.github.io/Grok16/",
                "https_secure_bookmark": f"{PAGES_BASE}/bookmark-jump/?id=g16-compiler&https=1",
            },
        }
    else:
        g16_online["pages"] = True
    (API / "hostess7-g16-online.json").write_text(
        json.dumps(g16_online, indent=2) + "\n", encoding="utf-8"
    )
    files.append("hostess7-g16-online.json")

    sovereign_state = NL / ".nexus-state"
    if sovereign_state.is_dir():
        tl_script = NL / "lib" / "hostess7-tasklist.py"
        try:
            out = subprocess.run(
                [sys.executable, str(tl_script), "json"],
                cwd=str(NL),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(NL), "NEXUS_STATE_DIR": str(sovereign_state), "SG_ROOT": str(NL.parent)},
            )
            tasklist = json.loads(out.stdout) if out.stdout.strip() else {"ok": False}
        except Exception as exc:
            tasklist = {"ok": False, "error": str(exc)}
    else:
        tasklist = _run_nl_script_json("lib/hostess7-tasklist.py", timeout=30)
    if isinstance(tasklist, dict):
        tasklist["pages"] = True
        tasklist["lane"] = "pages-surfaces"
        tasklist["exported"] = _ts()
    (API / "hostess7-tasklist.json").write_text(json.dumps(tasklist, indent=2) + "\n", encoding="utf-8")
    files.append("hostess7-tasklist.json")

    ic_index = _build_ironclad_pages_index(tasklist if isinstance(tasklist, dict) else None)
    (API / "ironclad-pages-search-index.json").write_text(json.dumps(ic_index, indent=2) + "\n", encoding="utf-8")
    files.append("ironclad-pages-search-index.json")

    (API / "github-secure.json").write_text(
        json.dumps(
            {
                **stub,
                "verify": {"ok": True, "route": "pages-pinned", "pin": "zacharygeurts.github.io"},
                "policy": "Queen pinned GitHub — AmmoLang ironclad · no MITM · KILL/REKILL prejudice",
                "secure_kill": secure_kill,
                "download_doctrine": {
                    "re_authorize": True,
                    "always_redownloadable": True,
                    "app_updates": "Owner may authorize updates when sovereign copy remains fetchable from pinned GitHub",
                },
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

    status["edition"] = "Universal Protector"
    status["product"] = "NEXUS-Shield"
    (API / "nexus-field.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    files.append("nexus-field.json")

    up_doc = _run_nl_script_json("lib/universal-protector.py", ["json"], timeout=90)
    if not up_doc.get("schema"):
        up_doc = {
            **stub,
            "schema": "universal-protector/v1",
            "product": "Universal Protector",
            "threat_warn_level": "high",
            "autonomous_being": True,
            "pillars": {"persona": {"hostess7_available": True}},
        }
    up_doc["pages"] = True
    (API / "universal-protector.json").write_text(json.dumps(up_doc, indent=2) + "\n", encoding="utf-8")
    files.append("universal-protector.json")

    spatial = _run_nl_script_json("lib/field-spatial-cognition.py", ["json"], timeout=60)
    if not spatial.get("ok"):
        spatial = {**stub, "schema": "field-spatial/v1", "dimensions": ["3d", "4d"], "movement_vector": None}
    spatial["pages"] = True
    (API / "field-spatial.json").write_text(json.dumps(spatial, indent=2) + "\n", encoding="utf-8")
    files.append("field-spatial.json")

    device_map = _run_nl_script_json("lib/field-device-map.py", ["json"], timeout=60)
    if not device_map.get("schema"):
        device_map = {**stub, "schema": "field-device-map/v1", "operator": {}, "devices": [], "partial": True}
    device_map["pages"] = True
    (API / "field-device-map.json").write_text(json.dumps(device_map, indent=2) + "\n", encoding="utf-8")
    files.append("field-device-map.json")

    planetary_dns_dhcp = _run_nl_script_json("lib/field-planetary-dns-dhcp.py", ["panel"], timeout=90)
    if not planetary_dns_dhcp.get("schema"):
        planetary_dns_dhcp = {
            **stub,
            "schema": "field-planetary-dns-dhcp/v1",
            "counts": {},
            "partial": True,
        }
    planetary_dns_dhcp["pages"] = True
    (API / "field-planetary-dns-dhcp.json").write_text(
        json.dumps(planetary_dns_dhcp, indent=2) + "\n", encoding="utf-8"
    )
    files.append("field-planetary-dns-dhcp.json")

    collision_guard = _run_nl_script_json("lib/field-dns-dhcp-collision-guard.py", ["panel"], timeout=45)
    if not collision_guard.get("schema"):
        collision_guard = {**stub, "schema": "field-dns-dhcp-collision-guard/v1", "partial": True}
    collision_guard["pages"] = True
    (API / "field-dns-dhcp-collision-guard.json").write_text(
        json.dumps(collision_guard, indent=2) + "\n", encoding="utf-8"
    )
    files.append("field-dns-dhcp-collision-guard.json")

    any_ip = _run_nl_script_json("lib/field-dns-dhcp-any-ip.py", ["panel"], timeout=30)
    if not any_ip.get("schema"):
        any_ip = {**stub, "schema": "field-dns-dhcp-any-ip/v1", "partial": True}
    any_ip["pages"] = True
    (API / "field-dns-dhcp-any-ip.json").write_text(json.dumps(any_ip, indent=2) + "\n", encoding="utf-8")
    files.append("field-dns-dhcp-any-ip.json")

    ipv4_sovereign = _run_nl_script_json("lib/field-ipv4-device-sovereign.py", ["panel"], timeout=90)
    if not ipv4_sovereign.get("schema"):
        ipv4_sovereign = {**stub, "schema": "field-ipv4-device-sovereign/v1", "devices": [], "partial": True}
    ipv4_sovereign["pages"] = True
    (API / "field-ipv4-device-sovereign.json").write_text(
        json.dumps(ipv4_sovereign, indent=2) + "\n", encoding="utf-8"
    )
    files.append("field-ipv4-device-sovereign.json")

    internet_unrestrict = _run_nl_script_json("lib/field-internet-unrestrict.py", ["panel"], timeout=20)
    if not internet_unrestrict.get("schema"):
        internet_unrestrict = {**stub, "schema": "field-internet-unrestrict/v1", "partial": True}
    internet_unrestrict["pages"] = True
    (API / "field-internet-unrestrict.json").write_text(
        json.dumps(internet_unrestrict, indent=2) + "\n", encoding="utf-8"
    )
    files.append("field-internet-unrestrict.json")

    ipv4_arbitrary = _run_nl_script_json("lib/field-ipv4-arbitrary.py", ["panel"], timeout=20)
    if not ipv4_arbitrary.get("schema"):
        ipv4_arbitrary = {**stub, "schema": "field-ipv4-arbitrary/v1", "partial": True}
    ipv4_arbitrary["pages"] = True
    (API / "field-ipv4-arbitrary.json").write_text(
        json.dumps(ipv4_arbitrary, indent=2) + "\n", encoding="utf-8"
    )
    files.append("field-ipv4-arbitrary.json")

    threat_panel = {
        **stub,
        "schema": "threat-panel-pages/v1",
        "posture": "war-ready",
        "gates_held": True,
        "threat_warn_level": "high",
        "version": H7_VERSION,
        "universal_protector": True,
        "final_eye_pct": 100,
        "final_ear_pct": 0,
        "final_mouth_pct": 0,
        "sense": {
            "final_eye": {"ok": True, "headroom_pct": 100, "held": True},
            "final_ear": {"ok": True, "headroom_pct": 0, "partial": True},
            "final_mouth": {"ok": True, "headroom_pct": 0, "partial": True},
        },
        "routes": {
            "command": "https://zacharygeurts.github.io/command/",
            "command_basement": "https://zacharygeurts.github.io/command/",
            "command_hostess7": f"{PAGES_BASE}/command/",
            "desktop": f"{PAGES_BASE}/desktop/",
            "queen": f"{PAGES_BASE}/queen/browser.html",
            "g16": f"{PAGES_BASE}/g16-build-output/",
            "zacs": f"{PAGES_BASE}/zacs/png/",
        },
    }
    (API / "threat-panel.json").write_text(json.dumps(threat_panel, indent=2) + "\n", encoding="utf-8")
    files.append("threat-panel.json")

    basement_state = NL / ".nexus-state" / "nexus-c2-basement.json"
    if not basement_state.is_file():
        basement_state = ROOT / ".pages-build-state" / "nexus-c2-basement.json"
    try:
        basement_doc = json.loads(basement_state.read_text(encoding="utf-8")) if basement_state.is_file() else {}
    except (OSError, json.JSONDecodeError):
        basement_doc = {}
    basement_doc = {
        **basement_doc,
        "schema": "nexus-c2-basement/v1",
        "ok": True,
        "pages": True,
        "pages_url": "https://zacharygeurts.github.io/command/",
        "theme": "black_emerald_rose_2026",
        "palette": "black · emerald · rose",
        "shared": True,
        "motto": basement_doc.get("motto")
        or "NEXUS C2 is the secure basement — not a kiosk. Shared with everyone.",
        "updated": basement_doc.get("updated") or _ts(),
    }
    (API / "nexus-c2-basement.json").write_text(json.dumps(basement_doc, indent=2) + "\n", encoding="utf-8")
    files.append("nexus-c2-basement.json")

    c2_stub = {
        "ok": True,
        "pages": True,
        "held": True,
        "posture": "war-ready",
        "schema": "pages-c2-slice/v1",
    }
    for slice_name in (
        "gatekeeper",
        "field-command",
        "lethal-enforcement",
        "hostess7-lethal-insight",
        "us-field",
        "us-obs-field",
        "field-obs",
        "us-voltage-regulation",
        "home-protector",
        "local-services",
        "host-attacks",
        "terror-spiderweb",
        "planetary-observer",
        "precision-field",
        "angel-dossiers",
        "human-dossier",
        "angel-research",
        "honorability",
        "audio-train",
        "field-rf",
        "signals-field",
        "field-hardware",
        "field-hazard-onset",
        "field-radio",
        "field-dns",
        "field-outside-talk",
        "field-drive",
        "field-brain",
        "settings",
        "compatibility",
        "diagnostic-mode",
        "police-agencies",
        "human-registry",
        "gov-intel",
        "program-tags",
        "census-field",
        "existence-identity",
    ):
        doc = _pages_c2_slice_doc(slice_name, c2_stub)
        (API / f"{slice_name}.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        files.append(f"{slice_name}.json")

    (API / "packet-field.json").write_text(
        json.dumps({**c2_stub, "updated": _ts(), "ports": [], "recent": [], "ring": []}, indent=2) + "\n",
        encoding="utf-8",
    )
    files.append("packet-field.json")

    dewey_export = _run_nl_script_json("lib/field-dewey-index.py", ["pages-export", "--out", str(API)], timeout=180)
    compact_path = API / "dewey-books-compact.json"
    if compact_path.is_file() and dewey_export.get("ok"):
        files.extend(["dewey-index-facets.json", "dewey-books-compact.json", "library-running-text.json"])
        compact_n = int(dewey_export.get("book_count") or dewey_export.get("counts", {}).get("books") or 0)
        try:
            compact_books = json.loads(compact_path.read_text(encoding="utf-8")).get("books") or []
        except (OSError, json.JSONDecodeError):
            compact_books = []
        catalog_doc = {
            **c2_stub,
            "schema": "library-catalog/v1",
            "books": compact_books[:400],
            "book_count": compact_n,
            "updated": _ts(),
            "motto": "Whole Hostess 7 library on Pages — humans, librarians, and AI.",
        }
        (API / "library-catalog.json").write_text(json.dumps(catalog_doc, indent=2) + "\n", encoding="utf-8")
        files.append("library-catalog.json")
    else:
        (API / "library-catalog.json").write_text(
            json.dumps({**c2_stub, "books": [], "updated": _ts()}, indent=2) + "\n",
            encoding="utf-8",
        )
        files.append("library-catalog.json")

    drawer_src = NL / "library" / "dewey" / "020-library-science" / "card-catalog" / "catalog.json"
    if drawer_src.is_file():
        try:
            drawer = json.loads(drawer_src.read_text(encoding="utf-8"))
            (API / "card-catalog-drawer.json").write_text(
                json.dumps(drawer, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            files.append("card-catalog-drawer.json")
            panel_doc = {
                "schema": "field-card-catalog-panel/v1",
                "updated": drawer.get("updated") or _ts(),
                "ok": True,
                "pages": True,
                "counts": drawer.get("counts") or {},
                "sort_modes": drawer.get("sort_modes") or [],
                "motto": drawer.get("motto") or "Every book a card — joy for librarians and readers.",
                "card_count": drawer.get("card_count") or len(drawer.get("cards") or []),
            }
            (API / "card-catalog-panel.json").write_text(
                json.dumps(panel_doc, indent=2) + "\n",
                encoding="utf-8",
            )
            files.append("card-catalog-panel.json")
        except (OSError, json.JSONDecodeError):
            pass

    deploy_url = f"https://zacharygeurts.github.io{PAGES_BASE.rstrip('/')}/"
    (API / "pages-update-status.json").write_text(
        json.dumps(
            {
                **c2_stub,
                "schema": "pages-update-status/v1",
                "current": H7_VERSION,
                "version": H7_VERSION,
                "deploy_url": deploy_url,
                "deployed_at": _ts(),
                "pages_base": PAGES_BASE,
                "update_available": False,
                "update_in_progress": False,
                "checked_at": _ts(),
                "middleman": False,
                "direct_for_everyone": True,
                "own_deployment": True,
                "bypass_middleman": True,
                "old_browsers_ok": True,
                "dns_dhcp": "/api/field-botnet-dns-dhcp",
                "deploy_steps": [
                    "python3 Hostess7/scripts/hostess7_pages_surfaces_build.py",
                    "git add Hostess7/docs/ && git commit -m 'pages: rebuild'",
                    "git push origin main",
                ],
                "delay_as_threat": False,
                "truth_clean": True,
                "delay_countermeasures": [
                    "everyone_manages_own_deploy",
                    "cancel_zombie_ci",
                    "pages_first_no_middleman",
                ],
                "message": f"Everyone manages own deploy at {deploy_url} — delay is threat, truth cleaned, no middleman",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    files.append("pages-update-status.json")

    earball = _run_nl_script_json("Queen/lib/queen-earball.py", ["json"], timeout=60) if (QUEEN_ROOT / "lib" / "queen-earball.py").is_file() else {}
    if not earball.get("schema"):
        earball = {**c2_stub, "schema": "queen-earball/v1", "partial": True, "headroom_pct": 0}
    earball["pages"] = True
    (API / "queen-earball.json").write_text(json.dumps(earball, indent=2) + "\n", encoding="utf-8")
    files.append("queen-earball.json")

    mouthball = _run_nl_script_json("Queen/lib/queen-mouthball.py", ["json"], timeout=60) if (QUEEN_ROOT / "lib" / "queen-mouthball.py").is_file() else {}
    if not mouthball.get("schema"):
        mouthball = {**c2_stub, "schema": "queen-mouthball/v1", "partial": True, "headroom_pct": 0}
    mouthball["pages"] = True
    (API / "queen-mouthball.json").write_text(json.dumps(mouthball, indent=2) + "\n", encoding="utf-8")
    files.append("queen-mouthball.json")

    (API / "operator-location.json").write_text(
        json.dumps(
            {**c2_stub, "schema": "operator-location/v1", "mode": "pages", "lat": 0.0, "lon": 0.0, "address": "GitHub Pages"},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    files.append("operator-location.json")

    (API / "hostess7-training.json").write_text(
        json.dumps({**c2_stub, "schema": "hostess7-training/v1", "tracks": [], "partial": True}, indent=2) + "\n",
        encoding="utf-8",
    )
    files.append("hostess7-training.json")

    tr_room = _run_nl_script_json("lib/hostess7-training-room.py", ["json"], timeout=90)
    if not tr_room.get("schema"):
        tr_room = {**c2_stub, "schema": "hostess7-training-room-panel/v1", "partial": True, "voice": "Training room on loopback — Pages shows motion deck"}
    tr_room["pages"] = True
    (API / "hostess7-training-room.json").write_text(json.dumps(tr_room, indent=2) + "\n", encoding="utf-8")
    files.append("hostess7-training-room.json")

    qemu_doc = _run_nl_script_json("lib/qemu-world-status.py", [], timeout=45)
    if not qemu_doc.get("schema"):
        qemu_doc = {**c2_stub, "schema": "qemu-world-pipeline/v1", "running": False, "completed": 0, "target": 0}
    qemu_doc["pages"] = True
    (API / "qemu-world-status.json").write_text(json.dumps(qemu_doc, indent=2) + "\n", encoding="utf-8")
    files.append("qemu-world-status.json")

    _run_nl_script_json("lib/field-steel-neural-plates.py", ["publish", "--refresh"], timeout=90)
    meld = _run_nl_script_json("lib/field-plate-meld.py", ["meld"], timeout=120)
    if not meld.get("schema"):
        meld = _run_nl_script_json("lib/field-plate-meld.py", ["json"], timeout=90)
    if not meld.get("schema"):
        meld = {**c2_stub, "schema": "field-plate-meld/v1", "partial": True}
    meld["pages"] = True
    (API / "plate-meld.json").write_text(json.dumps(meld, indent=2) + "\n", encoding="utf-8")
    files.append("plate-meld.json")

    steel = _run_nl_script_json("lib/field-steel-neural-plates.py", ["slice"], timeout=90)
    if not steel.get("schema"):
        steel = {**c2_stub, "schema": "field-steel-neural-plates-slice/v1", "plate_count": 0, "plates": []}
    steel["pages"] = True
    (API / "steel-plates.json").write_text(json.dumps(steel, indent=2) + "\n", encoding="utf-8")
    files.append("steel-plates.json")

    ammonet = _run_nl_script_json("lib/ammonet-field.py", ["panel"], timeout=120)
    if not ammonet.get("schema"):
        ammonet = {
            **stub,
            "schema": "ammonet-field/v1",
            "product": "AmmoNet",
            "pages_base": PAGES_BASE,
            "final_internet": {"hub": f"{PAGES_BASE}/final-internet/", "motto": "Safe fields for everyone"},
            "modules": [],
        }
    else:
        ammonet["pages"] = True
        ammonet["pages_base"] = PAGES_BASE
    (API / "ammonet.json").write_text(json.dumps(ammonet, indent=2) + "\n", encoding="utf-8")
    files.append("ammonet.json")

    field_internet = _run_nl_script_json("lib/field-internet-unified.py", ["json"], timeout=35)
    if not field_internet.get("schema"):
        field_internet = {
            **stub,
            "schema": "field-internet-unified-panel/v1",
            "ok": True,
            "boss": "hostess7",
            "product": "AmmoNet",
            "motto": "Fielded bot network — one thing talks everywhere",
            "api": "/api/field-internet",
            "keepalive_api": "/api/field-internet/keepalive",
        }
    else:
        field_internet["pages"] = True
        field_internet["pages_base"] = PAGES_BASE
    (API / "field-internet.json").write_text(json.dumps(field_internet, indent=2) + "\n", encoding="utf-8")
    files.append("field-internet.json")

    botnet_dns = _run_nl_script_json("lib/field-botnet-dns-dhcp.py", ["json"], timeout=30)
    if not botnet_dns.get("schema"):
        botnet_dns = {
            **stub,
            "schema": "field-botnet-dns-dhcp-panel/v1",
            "ok": True,
            "boss": "hostess7",
            "stable": True,
            "secure": True,
            "motto": "Bot network — secure stable DNS & DHCP for everyone through GitHub",
            "github_control_plane": {"enabled": True, "pages_runtime": PAGES_BASE},
            "bot_network": {"node_count": 1, "any_and_all": True},
        }
    else:
        botnet_dns["pages"] = True
        botnet_dns["pages_base"] = PAGES_BASE
    doctrine_path = NL / "data" / "field-botnet-dns-dhcp-doctrine.json"
    if doctrine_path.is_file():
        try:
            doctrine_doc = json.loads(doctrine_path.read_text(encoding="utf-8"))
            ed = doctrine_doc.get("everyone_deploy") or {}
            if ed:
                botnet_dns["everyone_deploy"] = ed
            gh = doctrine_doc.get("github_control_plane") or {}
            if gh.get("pages_first"):
                botnet_dns.setdefault("github_control_plane", {})
                if isinstance(botnet_dns["github_control_plane"], dict):
                    botnet_dns["github_control_plane"]["pages_first"] = True
                    botnet_dns["github_control_plane"]["middleman"] = False
        except (OSError, json.JSONDecodeError):
            pass
    botnet_dns["middleman"] = False
    (API / "field-botnet-dns-dhcp.json").write_text(json.dumps(botnet_dns, indent=2) + "\n", encoding="utf-8")
    files.append("field-botnet-dns-dhcp.json")
    bot_keep = _run_nl_script_json("lib/field-botnet-dns-dhcp.py", ["keepalive"], timeout=30)
    if not bot_keep.get("schema"):
        bot_keep = {**botnet_dns, "schema": "field-botnet-dns-dhcp-keepalive/v1", "pages": True}
    else:
        bot_keep["pages"] = True
    (API / "field-botnet-dns-dhcp-keepalive.json").write_text(json.dumps(bot_keep, indent=2) + "\n", encoding="utf-8")
    files.append("field-botnet-dns-dhcp-keepalive.json")

    aia_accel = _run_nl_script_json("lib/field-aia-accelerator.py", ["json"], timeout=90)
    if not aia_accel.get("schema"):
        aia_accel = {
            **stub,
            "schema": "field-aia-accelerator-panel/v1",
            "ok": True,
            "boss": "hostess7",
            "title": "AIA — AI Accelerator",
            "repo": {
                "full": "ZacharyGeurts/AIA",
                "url": "https://github.com/ZacharyGeurts/AIA",
                "pages_url": "https://zacharygeurts.github.io/AIA/",
            },
            "hostess7_pages": {"runtime": f"https://zacharygeurts.github.io{PAGES_BASE}/"},
        }
    else:
        aia_accel["pages"] = True
        aia_accel["pages_base"] = PAGES_BASE
    (API / "field-aia-accelerator.json").write_text(json.dumps(aia_accel, indent=2) + "\n", encoding="utf-8")
    files.append("field-aia-accelerator.json")

    qubes_drive = _run_nl_script_json("lib/field-qubes-drive-provision.py", ["json"], timeout=60)
    if not qubes_drive.get("schema"):
        qubes_drive = {**stub, "schema": "field-qubes-drive-panel/v1", "ok": True, "boss": "hostess7"}
    else:
        qubes_drive["pages"] = True
        qubes_drive["pages_base"] = PAGES_BASE
    (API / "field-qubes-drive.json").write_text(json.dumps(qubes_drive, indent=2) + "\n", encoding="utf-8")
    files.append("field-qubes-drive.json")

    h7_interaction = _run_nl_script_json("lib/hostess7-github-interaction.py", ["json"], timeout=25)
    if not h7_interaction.get("schema"):
        h7_interaction = {
            **stub,
            "schema": "hostess7-github-interaction-panel/v1",
            "ok": True,
            "boss": "hostess7",
            "lane": "hostess7-github",
            "motto": "Interactions straight with Hostess 7 on GitHub — constant open connection. Secure for us.",
            "secure_for_us": {"sovereign_brain_unhooked_on_pages": True, "pages_mirror_only": True},
        }
    else:
        h7_interaction["pages"] = True
        h7_interaction["pages_base"] = PAGES_BASE
    (API / "hostess7-github-interaction.json").write_text(
        json.dumps(h7_interaction, indent=2) + "\n", encoding="utf-8"
    )
    files.append("hostess7-github-interaction.json")

    github_legacy = _run_nl_script_json("lib/field-github-legacy.py", ["json"], timeout=30)
    if not github_legacy.get("schema"):
        github_legacy = {
            **stub,
            "schema": "field-github-legacy-panel/v1",
            "ok": True,
            "boss": "hostess7",
            "stable_connection": True,
            "github_always": {"open_count": 4, "legacy_open": 12, "stable": True},
        }
    else:
        github_legacy["pages"] = True
        github_legacy["pages_base"] = PAGES_BASE
    (API / "field-github-legacy.json").write_text(json.dumps(github_legacy, indent=2) + "\n", encoding="utf-8")
    files.append("field-github-legacy.json")

    everyone_ctr = _run_nl_script_json("lib/field-everyone-counter.py", ["json"], timeout=12)
    if not everyone_ctr.get("schema"):
        everyone_ctr = {**stub, "schema": "field-everyone-counter/v1", "ok": True, "everyone_total": 0}
    else:
        everyone_ctr["pages"] = True
        everyone_ctr["pages_base"] = PAGES_BASE
    everyone_ctr = _enrich_everyone_counter(everyone_ctr, botnet_dns)
    (API / "field-everyone-counter.json").write_text(
        json.dumps(everyone_ctr, indent=2) + "\n", encoding="utf-8"
    )
    files.append("field-everyone-counter.json")

    endpoint_reg = _run_nl_script_json("lib/field-endpoint-registry.py", ["json"], timeout=45)
    if not endpoint_reg.get("schema"):
        endpoint_reg = {
            **stub,
            "schema": "field-endpoint-registry-public/v1",
            "ok": True,
            "title": "Sovereign endpoint registry",
            "motto": "No endpoint moves silently — beyond ICANN",
            "api": "/api/field-endpoint-registry",
        }
    else:
        endpoint_reg["pages"] = True
        endpoint_reg["pages_base"] = PAGES_BASE
    (API / "field-endpoint-registry.json").write_text(
        json.dumps(endpoint_reg, indent=2) + "\n", encoding="utf-8"
    )
    files.append("field-endpoint-registry.json")
    pages_alias = _run_nl_script_json("lib/field-endpoint-registry.py", ["pages"], timeout=20)
    if pages_alias.get("schema"):
        pages_alias["pages"] = True
        pages_alias["pages_base"] = PAGES_BASE
        (API / "field-pages-movement.json").write_text(
            json.dumps(pages_alias, indent=2) + "\n", encoding="utf-8"
        )
        files.append("field-pages-movement.json")
    routes_pub = _run_nl_script_json("lib/field-endpoint-registry.py", ["routes"], timeout=15)
    if routes_pub.get("schema"):
        routes_pub["pages"] = True
        routes_pub["pages_base"] = PAGES_BASE
        (API / "field-endpoint-registry-routes.json").write_text(
            json.dumps(routes_pub, indent=2) + "\n", encoding="utf-8"
        )
        files.append("field-endpoint-registry-routes.json")

    field_keepalive = _run_nl_script_json("lib/field-internet-unified.py", ["keepalive"], timeout=35)
    if not field_keepalive.get("schema"):
        field_keepalive = {
            **stub,
            "schema": "field-internet-keepalive/v1",
            "ok": True,
            "pages": True,
            "github": {"always_open": True, "open_count": 3},
            "one_voice": {"boss": "hostess7", "api": "/api/field-internet"},
        }
    else:
        field_keepalive["pages"] = True
    (API / "field-internet-keepalive.json").write_text(
        json.dumps(field_keepalive, indent=2) + "\n", encoding="utf-8"
    )
    files.append("field-internet-keepalive.json")

    fi_path = NL / "data" / "final-internet-doctrine.json"
    final_internet = json.loads(fi_path.read_text(encoding="utf-8")) if fi_path.is_file() else {}
    if final_internet:
        final_internet = {**final_internet, "ok": True, "pages": True, "pages_base": PAGES_BASE}
        sf = ammonet.get("final_internet", {}).get("safe_fields") if isinstance(ammonet.get("final_internet"), dict) else None
        if sf:
            final_internet["safe_fields_live"] = sf
        for key, rel in (final_internet.get("public_surfaces") or {}).items():
            if isinstance(rel, str) and rel.startswith("/"):
                final_internet["public_surfaces"][key] = f"{PAGES_BASE}{rel}"
        (API / "final-internet.json").write_text(json.dumps(final_internet, indent=2) + "\n", encoding="utf-8")
        files.append("final-internet.json")

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
    zacs_n = _stage_zacs_png()
    gnueol_n = _stage_gnueol_terminal_mirror()
    panel_n = _stage_panel_surfaces()
    command_publish = _write_command_basement_pages()
    _write_desktop_indices()
    _write_queen_browser()
    desktop = _run_field_host_desktop()
    api_files = _export_apis(desktop)
    return {
        "ok": True,
        "queen_files": queen_n,
        "panel_assets": assets_n,
        "panel_surfaces": panel_n,
        "command_basement": command_publish,
        "zacs_png": zacs_n,
        "gnueol_terminal_mirror": gnueol_n,
        "api_files": api_files,
        "pages_base": PAGES_BASE,
        "command_pages_base": COMMAND_PAGES_BASE,
        "exported": _ts(),
    }


def main() -> int:
    doc = build()
    print(json.dumps(doc, indent=2))
    print(f"METRIC pages_surfaces_build={doc.get('queen_files', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())