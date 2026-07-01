#!/usr/bin/env pythong
"""NEXUS Field Polkit (pol) — root posture, secure elevation, policy integrity."""
from __future__ import annotations

import json
import os
import platform
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-polkit-doctrine.json"
PANEL_FILE = STATE / "field-polkit-panel.json"
STAMP_FILE = STATE / "field-polkit.stamp"

POLICY = Path("/usr/share/polkit-1/actions/com.nexus.field.policy")
LEGACY_POLICY = Path("/usr/share/polkit-1/actions/com.nexus.field.install.policy")
RULES = Path("/etc/polkit-1/rules.d/49-com.nexus.field.rules")
AUDIT = STATE / "pkexec-audit.jsonl"


def _bridge_path() -> Path:
    for candidate in (
        INSTALL / "lib" / "nexus-pkexec-bridge.sh",
        Path("/usr/local/lib/nexus-shield/lib/nexus-pkexec-bridge.sh"),
    ):
        if candidate.is_file():
            return candidate
    return INSTALL / "lib" / "nexus-pkexec-bridge.sh"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _path_is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _file_mode_ok(path: Path, *, must_exec: bool = False) -> bool:
    try:
        st = path.stat()
    except OSError:
        return False
    if stat.S_IWOTH & st.st_mode:
        return False
    if must_exec and not (st.st_mode & stat.S_IXUSR):
        return False
    return True


def _audit_tail(limit: int = 5) -> list[dict[str, Any]]:
    if not AUDIT.is_file():
        return []
    lines: list[str] = []
    try:
        lines = AUDIT.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _polkitd_active() -> str:
    try:
        proc = subprocess.run(
            ["systemctl", "is-active", "polkit"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return (proc.stdout or proc.stderr or "unknown").strip()
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def detect_platform() -> str:
    sys_name = (platform.system() or "").lower()
    if sys_name == "windows":
        return "windows"
    if sys_name == "darwin":
        return "darwin"
    if sys_name == "linux":
        return "linux"
    return sys_name or "unknown"


def is_windows_admin() -> bool:
    if detect_platform() != "windows":
        return False
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def is_root() -> bool:
    plat = detect_platform()
    if plat == "windows":
        return is_windows_admin()
    try:
        return os.geteuid() == 0
    except AttributeError:
        return is_windows_admin()


def has_cached_sudo() -> bool:
    if detect_platform() != "linux":
        return False
    try:
        proc = subprocess.run(
            ["sudo", "-n", "true"],
            capture_output=True,
            timeout=5,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def root_posture(*, purpose: str = "") -> dict[str, Any]:
    plat = detect_platform()
    root = is_root()
    cached = has_cached_sudo()
    needs_elevation = not root and plat in ("linux", "windows")
    method = "none"
    if root:
        method = "administrator" if plat == "windows" else "root"
    elif cached:
        method = "sudo_cached"
    elif plat == "linux":
        method = "pkexec_or_secure_sudo"
    elif plat == "windows":
        method = "uac_elevate"
    return {
        "schema": "field-pol-root/v1",
        "ts": _now(),
        "platform": plat,
        "arch": platform.machine() or "unknown",
        "is_root": root,
        "is_admin": root if plat == "windows" else None,
        "euid": os.geteuid() if hasattr(os, "geteuid") else None,
        "has_cached_sudo": cached,
        "needs_elevation": needs_elevation,
        "elevation_method": method,
        "purpose": purpose or "general",
        "polkit_installed": _path_is_file(POLICY),
        "bridge_present": _path_is_file(_bridge_path()),
        "ready": root or cached or not needs_elevation,
    }


def posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    root = root_posture()
    checks = {
        "policy_present": _path_is_file(POLICY),
        "rules_present": _path_is_file(RULES),
        "bridge_present": _path_is_file(_bridge_path()),
        "bridge_secure": _file_mode_ok(_bridge_path(), must_exec=True),
        "legacy_policy_absent": not _path_is_file(LEGACY_POLICY),
        "polkitd": _polkitd_active(),
    }
    deny_recent = sum(
        1 for row in _audit_tail(20) if str(row.get("event", "")).startswith("deny")
    )
    verdict = "GREEN"
    if not all(
        (
            checks["policy_present"],
            checks["rules_present"],
            checks["bridge_present"],
            checks["bridge_secure"],
            checks["legacy_policy_absent"],
        )
    ):
        verdict = "WARN"
    if deny_recent >= 3:
        verdict = "WARN"
    if checks["polkitd"] not in ("active", "unknown"):
        verdict = "WARN"
    return {
        "schema": "field-polkit/v1",
        "ts": _now(),
        "verdict": verdict,
        "doctrine": doctrine.get("title", "field-polkit"),
        "checks": checks,
        "actions": [a.get("id") for a in doctrine.get("actions", []) if isinstance(a, dict)],
        "audit_tail": _audit_tail(),
        "deny_recent": deny_recent,
        "root": root,
    }


def board_once() -> dict[str, Any]:
    doc = posture()
    _save_panel(doc)
    STAMP_FILE.write_text(_now() + "\n", encoding="utf-8")
    return doc


def _save_panel(doc: dict[str, Any]) -> None:
    PANEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = PANEL_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PANEL_FILE)


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if mode == "board":
        board_once()
        return 0
    if mode == "json":
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if mode == "root":
        purpose = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(root_posture(purpose=purpose), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-polkit.py [json|board|root [purpose]]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())