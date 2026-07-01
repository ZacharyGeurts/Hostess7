#!/usr/bin/env pythong
"""Host OS start menu + taskbar — one canonical nexus-field.desktop; idempotent install and pin."""
from __future__ import annotations

import hashlib
import json
import os
import pwd
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parent.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SCHEMA = "nexus-host-desktop/v1"
STATE_FILE = STATE / "nexus-host-desktop.json"
CANONICAL = "nexus-field.desktop"
CANONICAL_BROWSER = "queen-browser.desktop"

# Superseded start-menu entries — keep exactly one launcher (nexus-field.desktop).
VESTIGIAL_STEMS = (
    "ammocode-stack",
    "amouranthrtx",
    "amouranthrtx-comp",
    "amouranthrtx-engine",
    "amouranthrtx-spv",
    "sg-code-open",
    "world-repack",
    "queen-browser",
    "nexus-shield",
    "nexus-tristate-installer",
    "nexus-threat-panel",
    "nexus-panel",
    "nexus-shield-panel",
    "nexus-shield-tray",
    "nexus-genius",
    "queen-shield",
    "ammoos-c2",
    "ammoos-field",
    "ammoos",
)

VESTIGIAL_PREFIXES = ("ammocode", "amouranth", "ammoos", "sg-code", "world-repack")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def _home_dirs() -> list[Path]:
    only = os.environ.get("NEXUS_HOST_DESKTOP_HOME", "").strip()
    if only:
        p = Path(only).expanduser()
        return [p] if p.is_dir() else []
    homes: list[Path] = []
    try:
        homes.append(Path.home())
    except RuntimeError:
        pass
    for key in ("SUDO_USER", "USER"):
        user = os.environ.get(key, "").strip()
        if not user or user == "root":
            continue
        try:
            homes.append(Path(pwd.getpwnam(user).pw_dir))
        except KeyError:
            continue
    seen: set[str] = set()
    out: list[Path] = []
    for h in homes:
        s = str(h)
        if s not in seen:
            seen.add(s)
            out.append(h)
    return out


def _desktop_dirs() -> list[Path]:
    dirs: list[Path] = [Path("/usr/share/applications")]
    for home in _home_dirs():
        dirs.extend([
            home / ".local" / "share" / "applications",
            home / "Desktop",
        ])
    return [d for d in dirs if d.is_dir()]


def _read_state() -> dict[str, Any]:
    if not STATE_FILE.is_file():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_state(doc: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resolve_exec(root: Path) -> str:
    sys_launcher = Path("/usr/local/bin/nexus.sh")
    if sys_launcher.is_file() and root == Path("/usr/local/lib/nexus-shield"):
        return str(sys_launcher)
    return str(root / "nexus.sh")


def _resolve_version(root: Path) -> str:
    common = root / "lib" / "nexus-common.sh"
    if common.is_file():
        m = re.search(r'NEXUS_VERSION="([^"]+)"', common.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1)
    return "10.4.1"


def _queen_browser_desktop_body(root: Path) -> str:
    launcher = root / "Queen" / "field-gecko" / "bin" / "launch-field-gecko.sh"
    exec_path = str(launcher) if launcher.is_file() else _resolve_exec(root)
    icon = "queen-prog-browser"
    for cand in (
        root / "panel" / "assets" / "queen-prog-browser.png",
        root / "Queen" / "world" / "assets" / "icons" / "prog-browser-48.png",
        root / "panel" / "assets" / "ammoos-field-48.png",
    ):
        if cand.is_file():
            icon = str(cand)
            break
    return f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Queen Browser
GenericName=Web Browser
Comment=AmmoOS — KILROY field stack in Queen Browser with ZNetwork
Exec={exec_path} %u
Path={root}
Icon={icon}
Terminal=false
Categories=Network;WebBrowser;
MimeType=text/html;text/xml;application/xhtml+xml;application/vnd.mozilla.xul+xml;x-scheme-handler/http;x-scheme-handler/https;x-scheme-handler/about;
StartupNotify=true
StartupWMClass=QueenBrowser
Keywords=queen;browser;ammoos;kilroy;znetwork;nexus;
"""


def _desktop_body(root: Path) -> str:
    exec_path = _resolve_exec(root)
    ver = _resolve_version(root)
    return f"""[Desktop Entry]
Version={ver}
Type=Application
Name=AmmoOS
GenericName=NEXUS Field C2
Comment=AmmoOS field command — Queen browser, panel, ZNetwork, Grok16
Exec={exec_path}
Icon=nexus-field
Path={root}
Terminal=false
Categories=Security;Network;System;
Keywords=ammoos;nexus;field;znetwork;queen;grok16;
StartupNotify=true
Actions=Underlay;Tray;

[Desktop Action Underlay]
Name=2026 Tristate Installer
Exec={exec_path} --underlay

[Desktop Action Tray]
Name=Show Taskbar Icon
Exec={exec_path} --tray
"""


def _is_vestigial_name(name: str) -> bool:
    stem = name.removesuffix(".desktop").lower()
    if stem == "nexus-field":
        return False
    if stem in VESTIGIAL_STEMS:
        return True
    return any(stem.startswith(p) for p in VESTIGIAL_PREFIXES)


def _remove_vestigial(results: dict[str, Any]) -> int:
    count = 0
    for base in _desktop_dirs():
        for path in base.glob("*.desktop"):
            if path.name == CANONICAL:
                continue
            if _is_vestigial_name(path.name):
                try:
                    path.unlink()
                    results["removed"].append(str(path))
                    count += 1
                except OSError as exc:
                    results["errors"].append({"path": str(path), "error": str(exc)})
    legacy = INSTALL / ".local-queen-browser.desktop"
    if legacy.is_file():
        try:
            legacy.unlink()
            results["removed"].append(str(legacy))
            count += 1
        except OSError as exc:
            results["errors"].append({"path": str(legacy), "error": str(exc)})
    return count


def _install_icons(root: Path, home: Path) -> None:
    kit = root / "Queen" / "scripts" / "queen-icon-kit.py"
    if kit.is_file():
        env = {**os.environ, "NEXUS_INSTALL_ROOT": str(root)}
        for py in (os.environ.get("NEXUS_PYTHONG", ""), sys.executable, "python3", "pythong"):
            if not py:
                continue
            try:
                subprocess.run([py, str(kit)], env=env, capture_output=True, timeout=60, check=False)
                break
            except (OSError, subprocess.TimeoutExpired):
                continue
    src_candidates = [
        root / "panel" / "assets" / "nexus-field-256.png",
        root / "panel" / "assets" / "nexus-field.png",
        root / "assets" / "nexus-field.png",
    ]
    src = next((p for p in src_candidates if p.is_file()), None)
    if not src:
        return
    for sz in (48, 64, 128, 256):
        sized = root / "panel" / "assets" / f"nexus-field-{sz}.png"
        icon_src = sized if sized.is_file() else src
        dest_dir = home / ".local" / "share" / "icons" / "hicolor" / f"{sz}x{sz}" / "apps"
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / "nexus-field.png"
            if not dest.is_file() or dest.read_bytes() != icon_src.read_bytes():
                dest.write_bytes(icon_src.read_bytes())
        except OSError:
            pass
    try:
        subprocess.run(
            ["gtk-update-icon-cache", "-f", str(home / ".local" / "share" / "icons" / "hicolor")],
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _install_queen_browser_desktop(results: dict[str, Any]) -> dict[str, Any]:
    root = INSTALL.resolve()
    body = _queen_browser_desktop_body(root)
    digest = _sha256_text(body)
    info: dict[str, Any] = {
        "path": "",
        "sha256": digest,
        "installed": False,
        "skipped": False,
    }
    for home in _home_dirs():
        apps = home / ".local" / "share" / "applications"
        dest = apps / CANONICAL_BROWSER
        apps.mkdir(parents=True, exist_ok=True)
        if dest.is_file() and _sha256_text(dest.read_text(encoding="utf-8", errors="replace")) == digest:
            info["path"] = str(dest)
            info["skipped"] = True
            continue
        try:
            dest.write_text(body, encoding="utf-8")
            dest.chmod(0o644)
            info["path"] = str(dest)
            info["installed"] = True
        except OSError as exc:
            results["errors"].append({"kind": "install_browser", "path": str(dest), "error": str(exc)})
        try:
            subprocess.run(["update-desktop-database", str(apps)], capture_output=True, timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    results["queen_browser_desktop"] = info
    return info


def _set_default_web_browser(results: dict[str, Any]) -> dict[str, Any]:
    info: dict[str, Any] = {"desktop": CANONICAL_BROWSER, "set": False, "skipped": False}
    if os.environ.get("NEXUS_QUEEN_DEFAULT_BROWSER", "1") in ("0", "false", "no", "off"):
        info["skipped"] = True
        info["reason"] = "disabled"
        results["default_browser"] = info
        return info
    try:
        proc = subprocess.run(
            ["xdg-settings", "get", "default-web-browser"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        current = (proc.stdout or "").strip()
        if current == CANONICAL_BROWSER:
            info["skipped"] = True
            info["already_default"] = True
            results["default_browser"] = info
            return info
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        proc = subprocess.run(
            ["xdg-settings", "set", "default-web-browser", CANONICAL_BROWSER],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if proc.returncode == 0:
            info["set"] = True
        else:
            info["error"] = (proc.stderr or proc.stdout or "xdg-settings failed").strip()[:200]
    except (OSError, subprocess.TimeoutExpired) as exc:
        info["error"] = str(exc)
    results["default_browser"] = info
    return info


def _install_desktop(results: dict[str, Any]) -> dict[str, Any]:
    root = INSTALL.resolve()
    body = _desktop_body(root)
    digest = _sha256_text(body)
    prior = _read_state()
    info: dict[str, Any] = {
        "path": "",
        "sha256": digest,
        "installed": False,
        "skipped": False,
    }

    for home in _home_dirs():
        apps = home / ".local" / "share" / "applications"
        dest = apps / CANONICAL
        apps.mkdir(parents=True, exist_ok=True)
        _install_icons(root, home)

        if dest.is_file() and _sha256_text(dest.read_text(encoding="utf-8", errors="replace")) == digest:
            info["path"] = str(dest)
            info["skipped"] = True
            continue

        if prior.get("desktop_sha256") == digest and dest.is_file():
            info["path"] = str(dest)
            info["skipped"] = True
            continue

        try:
            dest.write_text(body, encoding="utf-8")
            dest.chmod(0o644)
            info["path"] = str(dest)
            info["installed"] = True
        except OSError as exc:
            results["errors"].append({"kind": "install", "path": str(dest), "error": str(exc)})

        desktop_shortcut = home / "Desktop" / CANONICAL
        if (home / "Desktop").is_dir():
            try:
                desktop_shortcut.write_text(body, encoding="utf-8")
                desktop_shortcut.chmod(0o755)
                subprocess.run(
                    ["gio", "set", str(desktop_shortcut), "metadata::trusted", "true"],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
            except OSError:
                pass

        try:
            subprocess.run(["update-desktop-database", str(apps)], capture_output=True, timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass

    results["desktop"] = info
    return info


def _pin_cinnamon(home: Path, results: dict[str, Any]) -> bool:
    spice_dir = home / ".config" / "cinnamon" / "spices"
    if not spice_dir.is_dir():
        return False
    target_path = None
    for cfg in spice_dir.rglob("*.json"):
        try:
            doc = json.loads(cfg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        pins = doc.get("pinned-apps")
        if not isinstance(pins, dict):
            continue
        value = pins.get("value")
        if not isinstance(value, list):
            continue
        if any(CANONICAL in str(x) for x in value):
            results["pin"] = {"backend": "cinnamon", "path": str(cfg), "skipped": True, "already_pinned": True}
            return True
        value.append(CANONICAL)
        pins["value"] = value
        doc.pop("__md5__", None)
        try:
            cfg.write_text(json.dumps(doc, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
            results["pin"] = {"backend": "cinnamon", "path": str(cfg), "pinned": True}
            return True
        except OSError as exc:
            results["errors"].append({"kind": "pin_cinnamon", "path": str(cfg), "error": str(exc)})
            target_path = str(cfg)
    if target_path:
        return False
    return False


def _pin_gnome(results: dict[str, Any]) -> bool:
    try:
        proc = subprocess.run(
            ["gsettings", "get", "org.gnome.shell", "favorite-apps"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if proc.returncode != 0:
            return False
        raw = (proc.stdout or "").strip()
        if CANONICAL in raw:
            results["pin"] = {"backend": "gnome", "skipped": True, "already_pinned": True}
            return True
        favorites: list[str] = []
        if raw.startswith("[") and raw.endswith("]"):
            for part in raw[1:-1].split(","):
                part = part.strip().strip("'\"")
                if part:
                    favorites.append(part)
        if CANONICAL not in favorites:
            favorites.insert(0, CANONICAL)
        quoted = ", ".join(f"'{x}'" for x in favorites)
        set_proc = subprocess.run(
            ["gsettings", "set", "org.gnome.shell", "favorite-apps", f"[{quoted}]"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if set_proc.returncode == 0:
            results["pin"] = {"backend": "gnome", "pinned": True}
            return True
    except (OSError, subprocess.TimeoutExpired) as exc:
        results["errors"].append({"kind": "pin_gnome", "error": str(exc)})
    return False


def _pin_xfce(home: Path, results: dict[str, Any]) -> bool:
    panel_xml = home / ".config" / "xfce4" / "panel" / "default.xml"
    if not panel_xml.is_file():
        panel_xml = home / ".config" / "xfce4" / "xfconf" / "xfce-perchannel-xml" / "xfce4-panel.xml"
    if not panel_xml.is_file():
        return False
    try:
        text = panel_xml.read_text(encoding="utf-8", errors="replace")
        if CANONICAL in text:
            results["pin"] = {"backend": "xfce", "skipped": True, "already_pinned": True}
            return True
        marker = '<property name="plugin-ids" type="array">'
        if marker not in text:
            return False
        launcher = (
            f'  <property name="launcher" type="array">\n'
            f'    <value type="string">{CANONICAL}</value>\n'
            f'  </property>\n'
        )
        if launcher.strip() in text:
            return True
        # Best-effort: do not rewrite full panel layout automatically.
        results["pin"] = {"backend": "xfce", "skipped": True, "hint": "desktop_installed_pin_from_menu"}
        return False
    except OSError as exc:
        results["errors"].append({"kind": "pin_xfce", "error": str(exc)})
    return False


def _pin_taskbar(results: dict[str, Any]) -> dict[str, Any]:
    prior = _read_state()
    if prior.get("pinned") and prior.get("pin_backend"):
        for home in _home_dirs():
            if prior["pin_backend"] == "cinnamon":
                spice_dir = home / ".config" / "cinnamon" / "spices"
                if spice_dir.is_dir():
                    for cfg in spice_dir.rglob("*.json"):
                        try:
                            doc = json.loads(cfg.read_text(encoding="utf-8"))
                            value = (doc.get("pinned-apps") or {}).get("value") or []
                            if any(CANONICAL in str(x) for x in value):
                                results["pin"] = {
                                    "backend": "cinnamon",
                                    "skipped": True,
                                    "state": "already_pinned",
                                }
                                return results.get("pin", {})
                        except (OSError, json.JSONDecodeError):
                            continue

    for home in _home_dirs():
        if _pin_cinnamon(home, results):
            return results.get("pin", {})
    if _pin_gnome(results):
        return results.get("pin", {})
    for home in _home_dirs():
        if _pin_xfce(home, results):
            return results.get("pin", {})
    results["pin"] = {"skipped": True, "hint": "no_supported_pin_backend"}
    return results.get("pin", {})


def run(*, force_pin: bool = False) -> dict[str, Any]:
    """Remove vestigial entries, install canonical desktop once, pin taskbar once."""
    session_marker = STATE / "nexus-host-desktop.session"
    boot = _boot_id()
    if session_marker.is_file() and os.environ.get("NEXUS_HOST_DESKTOP_FORCE", "0") != "1":
        try:
            marker = json.loads(session_marker.read_text(encoding="utf-8"))
            if marker.get("boot_id") == boot and marker.get("ok"):
                return {**_read_state(), "schema": SCHEMA, "session": "skipped", "boot_id": boot}
        except (OSError, json.JSONDecodeError):
            pass

    results: dict[str, Any] = {
        "schema": SCHEMA,
        "updated": _now(),
        "boot_id": boot,
        "ok": True,
        "motto": "One AmmoOS launcher — start menu and taskbar, no duplicates.",
        "removed": [],
        "errors": [],
    }

    results["counts"] = {"vestigial_removed": _remove_vestigial(results)}
    desktop = _install_desktop(results)
    _install_queen_browser_desktop(results)
    _set_default_web_browser(results)
    pin = _pin_taskbar(results) if force_pin or os.environ.get("NEXUS_HOST_DESKTOP_PIN", "1") != "0" else {}

    doc = {
        "schema": SCHEMA,
        "updated": results["updated"],
        "boot_id": boot,
        "desktop_sha256": desktop.get("sha256"),
        "desktop_path": desktop.get("path"),
        "pinned": bool(pin.get("pinned") or pin.get("already_pinned")),
        "pin_backend": pin.get("backend"),
        "counts": results["counts"],
        "ok": not results["errors"],
    }
    _write_state(doc)
    session_marker.write_text(json.dumps({"boot_id": boot, "ok": True, "ts": _now()}, ensure_ascii=False) + "\n")
    results.update(doc)
    if results["errors"]:
        results["ok"] = len(results["errors"]) < 3
    return results


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "run").strip().lower()
    if cmd in ("run", "install", "json"):
        print(json.dumps(run(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "remove":
        r: dict[str, Any] = {"removed": [], "errors": []}
        n = _remove_vestigial(r)
        print(json.dumps({"removed": r["removed"], "count": n}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "pin":
        r: dict[str, Any] = {"errors": []}
        p = _pin_taskbar(r)
        print(json.dumps({"pin": p, "errors": r["errors"]}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "browser":
        r: dict[str, Any] = {"errors": [], "ok": True}
        _install_queen_browser_desktop(r)
        _set_default_web_browser(r)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["run", "install", "json", "remove", "pin", "browser"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())