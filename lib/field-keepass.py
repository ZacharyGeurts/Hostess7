#!/usr/bin/env pythong
"""Lock — hardened offline vault (KeePassXC engine), all platforms, readable UI."""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
FIELD = Path(os.environ.get("KEEPASS_FIELD_ROOT", SG / "KeePass-Field"))
DOCTRINE = FIELD / "data" / "field-keepass-doctrine.json"
TIERS = FIELD / "data" / "field-keepass-ui-tiers.json"
HARDEN = FIELD / "forge" / "field-keepass-harden.py"
PANEL = STATE / "field-keepass-panel.json"
VAULT_DIR = STATE / "field-keepass-vault"
SETTINGS = STATE / "field-keepass-settings.json"
from sg_paths import grok16_root

GROK16 = grok16_root()


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


def _guest_os() -> str:
    system = platform.system().lower()
    if "windows" in system:
        return "windows"
    if "darwin" in system:
        return "darwin"
    return "linux"


def _display_size() -> tuple[int, int]:
    try:
        proc = subprocess.run(
            ["xrandr", "--current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            for line in (proc.stdout or "").splitlines():
                if "*" in line:
                    parts = line.split()[0]
                    if "x" in parts:
                        w, h = parts.split("x", 1)
                        return int(w), int(h)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return 1920, 1080


def _rtx_detected() -> bool:
    gate = GROK16 / "forge" / "rtx_gate.py"
    if gate.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(gate), "json", "queen_rtx"],
                capture_output=True,
                text=True,
                timeout=12,
                cwd=str(GROK16),
            )
            if proc.returncode == 0 and "permit" in (proc.stdout or ""):
                return '"permit": true' in proc.stdout or '"permit":true' in proc.stdout.replace(" ", "")
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=6,
        )
        if proc.returncode == 0 and "RTX" in (proc.stdout or "").upper():
            return True
    except (OSError, subprocess.TimeoutExpired):
        pass
    return False


def _panel_shell_ui_scale() -> int | None:
    shell = _load(STATE / "field-shell-settings.json", {})
    raw = shell.get("ui_scale")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _tier(width: int) -> dict[str, Any]:
    doc = _load(TIERS, {})
    for tier in doc.get("tiers") or []:
        if tier.get("min_width", 0) <= width <= tier.get("max_width", 99999):
            return tier
    return {"id": "fhd", "scale": 1.1, "font_pt": 12, "icon_px": 24, "btn_min_h": 34}


def ui_posture(*, width: int | None = None, ui_scale_pct: int | None = None, rtx_reduce: bool | None = None) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    ui_doc = doctrine.get("ui") or {}
    saved = _load(SETTINGS, {})
    w, h = _display_size() if width is None else (width, 1080)
    pct = ui_scale_pct if ui_scale_pct is not None else int(
        saved.get("ui_scale_pct") or _panel_shell_ui_scale() or ui_doc.get("default_ui_scale_pct") or 125
    )
    rtx = _rtx_detected()
    reduce = rtx_reduce if rtx_reduce is not None else bool(saved.get("rtx_reduce", ui_doc.get("rtx_reduce_default", True)) and rtx)
    tier = _tier(w)
    bump = float(ui_doc.get("desktop_bump_pct", 10)) / 100.0 + 1.0
    scale = float(tier.get("scale", 1.1)) * (pct / 100.0)
    if reduce:
        scale *= float(ui_doc.get("rtx_reduce_factor", 0.92))
    scale = round(min(float(ui_doc.get("max_ui_scale_pct", 200)) / 100.0, max(float(ui_doc.get("min_ui_scale_pct", 85)) / 100.0, scale)), 3)
    return {
        "width": w,
        "height": h,
        "tier": tier.get("id"),
        "ui_scale_pct": pct,
        "qt_scale_factor": scale,
        "font_pt": tier.get("font_pt"),
        "icon_px": tier.get("icon_px"),
        "btn_min_h": tier.get("btn_min_h"),
        "desktop_bump": bump,
        "rtx_detected": rtx,
        "rtx_reduce": reduce,
        "overflow_guards": (_load(TIERS, {}).get("overflow_guards") or {}),
    }


def _resolve_binary() -> str | None:
    doctrine = _load(DOCTRINE, {})
    platforms = doctrine.get("platforms") or {}
    guest = _guest_os()
    plat = platforms.get(guest) or {}

    if guest == "linux":
        for name in plat.get("binary") or ["keepassxc", "/usr/bin/keepassxc"]:
            path = shutil.which(name) if not name.startswith("/") else name
            if path and Path(path).is_file():
                return path
        flatpak = plat.get("flatpak")
        if flatpak and shutil.which("flatpak"):
            return f"flatpak run {flatpak}"
    elif guest == "darwin":
        app = plat.get("app")
        if app and Path(app).is_file():
            return app
    elif guest == "windows":
        for name in plat.get("binary") or []:
            if Path(name).is_file():
                return str(name)
            found = shutil.which(name)
            if found:
                return found
    return shutil.which("keepassxc")


def _harden_config(ui: dict[str, Any]) -> Path:
    env = {
        **os.environ,
        "KEEPASS_FIELD_ROOT": str(FIELD),
        "FIELD_KEEPASS_CONFIG_DIR": str(STATE / "keepass-config"),
        "FIELD_KEEPASS_WIDTH": str(ui.get("width", 1920)),
        "FIELD_KEEPASS_UI_SCALE": str(ui.get("ui_scale_pct", 110)),
        "FIELD_KEEPASS_RTX_REDUCE": "1" if ui.get("rtx_reduce") else "0",
    }
    if HARDEN.is_file():
        subprocess.run(
            [sys.executable, str(HARDEN), "json"],
            check=False,
            env=env,
            timeout=30,
            capture_output=True,
            text=True,
        )
    return STATE / "keepass-config" / "keepassxc-field.ini"


def _launch_env(ui: dict[str, Any], config: Path) -> dict[str, str]:
    qss = STATE / "keepass-config" / "field-keepass.qss"
    env = {
        **os.environ,
        "QT_AUTO_SCREEN_SCALE_FACTOR": "0",
        "QT_SCALE_FACTOR": str(ui.get("qt_scale_factor", 1.1)),
        "QT_FONT_DPI": str(int(96 * float(ui.get("qt_scale_factor", 1.1)))),
    }
    if qss.is_file():
        env["QT_STYLE_OVERRIDE"] = ""
        env["FIELD_KEEPASS_QSS"] = str(qss)
    if config.is_file():
        env["FIELD_KEEPASS_CONFIG"] = str(config)
    return env


def find_vaults() -> list[dict[str, Any]]:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for base in (VAULT_DIR, Path.home() / "Documents", Path.home()):
        if not base.is_dir():
            continue
        try:
            for p in base.glob("*.kdbx"):
                if p.is_file() and p not in paths:
                    paths.append(p)
        except OSError:
            continue
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"path": str(p), "name": p.name, "bytes": p.stat().st_size} for p in paths[:24]]


def _import_mod() -> Any | None:
    path = INSTALL / "lib" / "field-lock-import.py"
    if not path.is_file():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location("field_lock_import", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def import_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    mod = _import_mod()
    if mod and hasattr(mod, "dispatch"):
        return mod.dispatch(body)
    return {"ok": False, "error": "lock_import_missing"}


def posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    ui = ui_posture()
    binary = _resolve_binary()
    config = _harden_config(ui) if binary else None
    shell_settings = _load(STATE / "field-shell-settings.json", {})
    panel_scale = (shell_settings.get("settings") or {}).get("ui_scale")
    doc = {
        "schema": "field-lock/v1",
        "legacy_schema": "field-keepass/v1",
        "ts": _now(),
        "ok": bool(binary),
        "product": "Lock",
        "legacy_product": "Field KeePass",
        "doctrine": doctrine.get("title"),
        "policy": doctrine.get("policy"),
        "binary": binary,
        "platform": _guest_os(),
        "offline_only": True,
        "no_login_required": True,
        "ui": ui,
        "panel_ui_scale": panel_scale,
        "config": str(config) if config else None,
        "qss": str(STATE / "keepass-config" / "field-keepass.qss"),
        "vaults": find_vaults(),
        "vault_dir": str(VAULT_DIR),
        "queen_vault": str(STATE / "queen-vault.enc"),
        "import": (lambda m: m.posture() if m and hasattr(m, "posture") else {})(_import_mod()),
        "routes": {
            "panel": "/field-lock",
            "api": "/api/field-lock",
            "legacy_panel": "/field-keepass",
            "legacy_api": "/api/field-keepass",
        },
        "posture": (
            f"Lock — offline .kdbx · scale {ui.get('qt_scale_factor')} · "
            f"tier {ui.get('tier')} · RTX {'reduce' if ui.get('rtx_reduce') else 'native'}"
        ),
    }
    _save_atomic(PANEL, doc)
    return doc


def launch(*, vault: str = "", new_vault: bool = False) -> dict[str, Any]:
    binary = _resolve_binary()
    if not binary:
        return {"ok": False, "error": "keepassxc_missing", "hint": "install keepassxc package"}
    ui = ui_posture()
    config = _harden_config(ui)
    env = _launch_env(ui, config)
    VAULT_DIR.mkdir(parents=True, exist_ok=True)

    argv: list[str]
    if binary.startswith("flatpak "):
        argv = binary.split() + ["--config", str(config), "--localconfig", str(config)]
    else:
        argv = [binary, "--config", str(config), "--localconfig", str(config)]

    qss = Path(env.get("FIELD_KEEPASS_QSS", ""))
    if qss.is_file():
        argv.extend(["-style", "Fusion"])

    target = ""
    if vault:
        vp = Path(vault).expanduser()
        if vp.is_file():
            target = str(vp)
            argv.append(target)
    elif new_vault:
        target = str(VAULT_DIR / f"field-vault-{datetime.now(timezone.utc).strftime('%Y%m%d')}.kdbx")
        argv.append(target)

    try:
        proc = subprocess.Popen(
            argv,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return {
            "ok": True,
            "pid": proc.pid,
            "binary": binary,
            "vault": target or None,
            "ui": ui,
            "config": str(config),
        }
    except OSError as exc:
        return {"ok": False, "error": str(exc), "argv": argv}


def save_settings(patch: dict[str, Any]) -> dict[str, Any]:
    allowed = {"ui_scale_pct", "rtx_reduce", "tier_override"}
    saved = _load(SETTINGS, {})
    for key, val in patch.items():
        if key in allowed:
            saved[key] = val
    _save_atomic(SETTINGS, saved)
    return posture()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "launch":
        vault = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(launch(vault=vault), ensure_ascii=False, indent=2))
        return 0
    if cmd == "new":
        print(json.dumps(launch(new_vault=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "settings" and len(sys.argv) > 2:
        try:
            patch = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            patch = {}
        print(json.dumps(save_settings(patch), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-keepass.py [json|launch [vault]|new|settings JSON]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())