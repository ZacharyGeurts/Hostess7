#!/usr/bin/env python3
"""Local threat panel server — HTTP on loopback only (Hostess7-secured)."""

import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9477
PANEL_DIR = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("panel")
STATUS_JSON = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("threat-panel.json")
# Prefer env; else repo root next to this file when system install paths are absent.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_default_install = Path("/usr/local/lib/nexus-shield")
_default_state = Path("/var/lib/nexus-shield")
if not (_default_install / "lib").is_dir() and (_REPO_ROOT / "lib").is_dir():
    _default_install = _REPO_ROOT
if not _default_state.is_dir() and (_REPO_ROOT / ".nexus-state").is_dir():
    _default_state = _REPO_ROOT / ".nexus-state"
STATE_DIR = Path(os.environ.get("NEXUS_STATE_DIR", str(_default_state)))
INSTALL_ROOT = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_default_install)))
ZNETWORK_STATUS = STATE_DIR / "znetwork-status.json"


def _resolve_hostess7_root() -> Path:
    env = os.environ.get("HOSTESS7_ROOT", "").strip()
    if env:
        return Path(env).expanduser()
    try:
        if str(INSTALL_ROOT / "lib") not in sys.path:
            sys.path.insert(0, str(INSTALL_ROOT / "lib"))
        import sg_paths  # noqa: PLC0415

        return sg_paths.hostess7_root()
    except Exception:
        return INSTALL_ROOT / "Hostess7"


def _h7_library_snapshot_paths() -> list[Path]:
    roots: list[Path] = []
    h7 = _resolve_hostess7_root()
    roots.append(h7 / "cache" / "fieldstorage" / "brain" / "library" / "catalog_snapshot.json")
    team = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage"))
    if team.is_dir():
        roots.append(team / "brain" / "library" / "catalog_snapshot.json")
    return roots


def _load_h7_library_catalog_fast() -> dict | None:
    cached = _panel_slice("h7_library", default={})
    if isinstance(cached, dict) and cached.get("books") and not cached.get("_partial"):
        return cached
    for path in _h7_library_snapshot_paths():
        if not path.is_file():
            continue
        try:
            snap = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(snap, dict) and snap.get("books"):
            snap = dict(snap)
            snap["_catalog_snapshot"] = True
            snap.setdefault("_partial", False)
            snap.setdefault("_incomplete", False)
            return snap
    return None


def _load_plate_meld_cached() -> dict:
    """Hot read — never run full meld() on panel GET (that can take minutes)."""
    candidates = (
        STATE_DIR / "field-plate-meld.json",
        STATE_DIR / "field-plate-meld-runtime.json",
        STATE_DIR / "plate-meld-redundant" / "field-plate-meld.json",
        STATE_DIR / "plate-meld-redundant" / "field-plate-meld.json.bak",
    )
    for path in candidates:
        if not path.is_file():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(doc, dict) and doc.get("schema"):
            doc = dict(doc)
            doc["_field_cache"] = True
            return doc
    return {}


_LOOPBACK_CLIENTS = frozenset({"127.0.0.1", "::1", "::ffff:127.0.0.1"})
_IRONCLAD_SECURE_API_MOD: Any | None = None


def _ironclad_secure_api_mod() -> Any | None:
    global _IRONCLAD_SECURE_API_MOD
    if _IRONCLAD_SECURE_API_MOD is not None:
        return _IRONCLAD_SECURE_API_MOD
    script = INSTALL_ROOT / "lib" / "ironclad-secure-api.py"
    if not script.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("ironclad_secure_api", script)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _IRONCLAD_SECURE_API_MOD = mod
            return mod
    except Exception:
        pass
    return None

DATA_FILES = {
    "threat-panel": STATE_DIR / "threat-panel.json",
    "threat-vectors": STATE_DIR / "threat-vectors.tsv",
    "firewall-blocks": STATE_DIR / "firewall-blocks.tsv",
    "sanitize-actions": STATE_DIR / "sanitize-actions.tsv",
    "paranoia-incidents": STATE_DIR / "paranoia-incidents.jsonl",
    "paranoia-state": STATE_DIR / "paranoia.state",
    "shutdown-incidents": STATE_DIR / "shutdown-incidents.jsonl",
    "shutdown-state": STATE_DIR / "shutdown.state",
    "nexus-last-alive": STATE_DIR / "nexus-last-alive.json",
    "packet-snapshot": STATE_DIR / "packet.snapshot",
    "packet-field": STATE_DIR / "packet-field.json",
    "packet-field-ring": STATE_DIR / "packet-field.ring.jsonl",
    "arp-snapshot": STATE_DIR / "arp.snapshot",
    "firewall-state": STATE_DIR / "firewall.state",
    "firewall-trusted": STATE_DIR / "firewall-trusted.tsv",
    "vigil-state": STATE_DIR / "vigil.state",
    "human-dossier": STATE_DIR / "human-dossier.json",
}

LOG_FILES = {
    "alerts": Path("/var/log/nexus-alerts.log"),
    "vigil": STATE_DIR / "vigil-alerts.log",
}

# Keys loaded in parallel by the panel — omitted from /api/status unless ?full=1
PANEL_PARALLEL_KEYS = frozenset({
    "field_hardware",
    "field_hazard_onset",
    "lethal_enforcement",
    "hostess7_lethal_insight",
    "hostess7_command",
    "signals_field",
    "field_radio",
    "field_dns",
    "field_outside_talk",
    "field_drive",
    "home_protector",
    "local_services",
    "audio_train",
    "field_rf",
    "terror_spiderweb",
    "precision_field",
    "h7_library",
    "packet_field",
    "port_ddos_shield",
    "packet_deinterlace",
    "field_bus",
    "kernel_meld",
    "firmware_threat",
    "gatekeeper",
    "host_attacks",
    "planetary_observer",
    "us_field",
    "field_command",
    "angel_dossiers",
    "human_dossier",
    "angel_research",
    "browser_awareness",
    "field_queen_browser",
    "field_stack",
    "field_eyeball",
    "field_earball",
    "field_mouthball",
    "trust_strike",
    "field_weapons",
    "settings",
    "field_brain",
})


def _read_install_version() -> str:
    common = INSTALL_ROOT / "lib" / "nexus-common.sh"
    if common.is_file():
        try:
            import re

            m = re.search(
                r'NEXUS_VERSION="([^"]+)"',
                common.read_text(encoding="utf-8", errors="replace"),
            )
            if m:
                return m.group(1)
        except OSError:
            pass
    return os.environ.get("NEXUS_VERSION", "8.2.0")


def _read_nexus_conf() -> dict[str, str]:
    conf = INSTALL_ROOT / "config" / "nexus.conf"
    out: dict[str, str] = {}
    if not conf.is_file():
        return out
    try:
        for line in conf.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            out[key.strip()] = val.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def _conf_val(key: str, default: str = "") -> str:
    conf = _read_nexus_conf()
    return os.environ.get(key, conf.get(key, default))


def _conf_flag(key: str, default: str = "0") -> bool:
    return _conf_val(key, default) == "1"


def _conf_int(key: str, default: int) -> int:
    try:
        return int(_conf_val(key, str(default)))
    except ValueError:
        return default


def _cpu_vulnerability_json(*, apply: bool = False) -> dict:
    script = INSTALL_ROOT / "lib" / "cpu-vulnerability-shield.py"
    if not script.is_file():
        return {
            "schema": "cpu-vulnerability-shield/v1",
            "ok": False,
            "error": "cpu_vulnerability_shield_missing",
            "verdict": "UNKNOWN",
        }
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    if apply:
        env["NEXUS_CPU_VULN_APPLY"] = "1"
    proc = subprocess.run(
        [sys.executable, str(script), "board" if apply else "json"],
        capture_output=True,
        text=True,
        timeout=45,
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": (proc.stderr or "cpu_vuln_bad_json")[:300]}


def _field_polkit_json() -> dict:
    script = INSTALL_ROOT / "lib" / "field-polkit.py"
    if not script.is_file():
        return {
            "schema": "field-polkit/v1",
            "ok": False,
            "error": "field_polkit_missing",
            "verdict": "UNKNOWN",
        }
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.run(
        [sys.executable, str(script), "json"],
        capture_output=True,
        text=True,
        timeout=25,
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": (proc.stderr or "field_polkit_bad_json")[:300]}


def _field_underlay_json() -> dict:
    script = INSTALL_ROOT / "lib" / "field-underlay.py"
    if not script.is_file():
        return {
            "schema": "field-underlay/v1",
            "ok": False,
            "error": "field_underlay_missing",
            "verdict": "UNKNOWN",
        }
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.run(
        [sys.executable, str(script), "json"],
        capture_output=True,
        text=True,
        timeout=40,
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": (proc.stderr or "field_underlay_bad_json")[:300]}


def _tristate_installer_json(*, verb: str = "json", body: dict | None = None) -> dict:
    script = INSTALL_ROOT / "lib" / "field-underlay-switch.py"
    if not script.is_file():
        return {
            "schema": "tristate-installer/v1",
            "ok": False,
            "error": "tristate_installer_missing",
        }
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    if body and body.get("choice"):
        env["ZNETWORK_CHOICE"] = str(body.get("choice") or "")
    args = [sys.executable, str(script), verb]
    if body and body.get("confirm"):
        args.append("--confirm")
    if os.environ.get("NEXUS_ELEVATED_ROOT") == "1":
        args.append("--elevated")
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=600 if verb == "wrdt-apply" else 180,
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": (proc.stderr or "tristate_bad_json")[:300]}


def _tristate_root_json(*, purpose: str = "tristate_installer") -> dict:
    script = INSTALL_ROOT / "lib" / "field-polkit.py"
    if not script.is_file():
        return {
            "schema": "field-pol-root/v1",
            "ok": False,
            "ready": False,
            "error": "field_polkit_missing",
        }
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.run(
        [sys.executable, str(script), "root", purpose],
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
    )
    try:
        doc = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"schema": "field-pol-root/v1", "ok": False, "ready": False, "error": "root_bad_json"}
    doc["ok"] = bool(doc.get("ready"))
    return doc


def _tristate_has_cached_sudo() -> bool:
    if os.geteuid() == 0:
        return True
    try:
        proc = subprocess.run(["sudo", "-n", "true"], capture_output=True, timeout=5)
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


_TRISTATE_SUDO_KEEPALIVE: subprocess.Popen | None = None


def _tristate_sudo_keepalive_start() -> None:
    """Refresh sudo timestamp for the panel session — one auth at launch, never again."""
    global _TRISTATE_SUDO_KEEPALIVE
    if os.geteuid() == 0:
        return
    if not _tristate_has_cached_sudo():
        return
    if _TRISTATE_SUDO_KEEPALIVE is not None and _TRISTATE_SUDO_KEEPALIVE.poll() is None:
        return
    try:
        _TRISTATE_SUDO_KEEPALIVE = subprocess.Popen(
            [
                "bash",
                "-c",
                "while true; do sudo -n true 2>/dev/null || exit 0; sleep 50; done",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


def _tristate_acquire_root_json() -> dict:
    root = _tristate_root_json()
    if root.get("ready"):
        os.environ["NEXUS_ELEVATED_ROOT"] = "1"
        _tristate_sudo_keepalive_start()
        return {"ok": True, "already": True, "root": root, "session": "elevated"}
    helper = INSTALL_ROOT / "lib" / "tristate-acquire-root.sh"
    if not helper.is_file():
        return {"ok": False, "error": "acquire_root_missing", "root": root}
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.run(
        ["bash", str(helper)],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
    )
    root = _tristate_root_json()
    if root.get("ready"):
        os.environ["NEXUS_ELEVATED_ROOT"] = "1"
        _tristate_sudo_keepalive_start()
        return {"ok": True, "root": root, "session": "elevated", "launch_auth": True}
    err = (proc.stderr or proc.stdout or "elevation_declined")[:300]
    return {"ok": False, "error": err, "root": root, "exit_code": proc.returncode}


def _host_freeze_elevated_json(verb: str, *extra_args: str) -> dict:
    if os.geteuid() == 0:
        script = INSTALL_ROOT / "lib" / "field-host-freeze.py"
        return _nexus_py_json(script, [verb, *extra_args, "--elevated"], timeout=120)
    bridge = INSTALL_ROOT / "lib" / "nexus-pkexec-bridge.sh"
    script = INSTALL_ROOT / "lib" / "field-host-freeze.py"
    if not script.is_file():
        return {"ok": False, "error": "field_host_freeze_missing"}
    if not bridge.is_file():
        return _nexus_py_json(script, [verb, *extra_args], timeout=120)
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    args = [str(bridge), "run-freeze", verb, *extra_args]
    proc = subprocess.run(
        ["pkexec", "--action", "com.nexus.field.freeze", *args],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": (proc.stderr or "host_freeze_elevate_failed")[:300]}


def _host_poweroff_json() -> dict:
    """Session poweroff — logind dbus, then systemctl, without pkexec."""
    attempts: list[tuple[str, list[str]]] = [
        (
            "logind",
            [
                "dbus-send",
                "--system",
                "--print-reply",
                "--dest=org.freedesktop.login1",
                "/org/freedesktop/login1",
                "org.freedesktop.login1.Manager.PowerOff",
                "boolean:false",
            ],
        ),
        ("systemctl", ["systemctl", "poweroff"]),
        ("shutdown", ["shutdown", "-h", "now"]),
    ]
    errors: list[str] = []
    for method, cmd in attempts:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"{method}:{exc}")
            continue
        if proc.returncode == 0:
            return {"ok": True, "message": "Shutdown initiated", "method": method}
        detail = (proc.stderr or proc.stdout or f"exit_{proc.returncode}")[:200]
        errors.append(f"{method}:{detail}")
    return {"ok": False, "error": "poweroff_failed", "detail": errors}


def _tristate_elevated_json(verb: str, body: dict | None = None) -> dict:
    """Run underlay verb as root — reuse launch sudo cache; pkexec only if cache missing."""
    if os.geteuid() == 0:
        os.environ["NEXUS_ELEVATED_ROOT"] = "1"
        return _tristate_installer_json(verb=verb, body=body)
    if _tristate_has_cached_sudo():
        _tristate_sudo_keepalive_start()
        os.environ["NEXUS_ELEVATED_ROOT"] = "1"
        script = INSTALL_ROOT / "lib" / "field-underlay-switch.py"
        if not script.is_file():
            return {"ok": False, "error": "tristate_installer_missing"}
        env = os.environ.copy()
        env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
        env["NEXUS_STATE_DIR"] = str(STATE_DIR)
        env["NEXUS_ELEVATED_ROOT"] = "1"
        args = [sys.executable, str(script), verb]
        if body and body.get("confirm"):
            args.append("--confirm")
        proc = subprocess.run(
            ["sudo", "-n", "-E", *args],
            capture_output=True,
            text=True,
            timeout=600 if verb == "wrdt-apply" else 180,
            env=env,
        )
        try:
            return json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            return {"ok": False, "error": (proc.stderr or "underlay_sudo_failed")[:300], "method": "sudo_cached"}
    bridge = INSTALL_ROOT / "lib" / "nexus-pkexec-bridge.sh"
    if not bridge.is_file():
        return _tristate_installer_json(verb=verb, body=body)
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    args = [str(bridge), "run-underlay", verb]
    if body and body.get("confirm"):
        args.append("--confirm")
    proc = subprocess.run(
        ["pkexec", "--action", "com.nexus.field.underlay", *args],
        capture_output=True,
        text=True,
        timeout=600,
        env=env,
    )
    try:
        doc = json.loads(proc.stdout or "{}")
        if doc.get("ok") is not False:
            _tristate_sudo_keepalive_start()
        return doc
    except json.JSONDecodeError:
        return {"ok": False, "error": (proc.stderr or "underlay_elevate_failed")[:300]}


def _native_layer_json(*, audit: bool = False) -> dict:
    script = INSTALL_ROOT / "lib" / "native-layer.py"
    if not script.is_file():
        return {
            "schema": "native-layer/v1",
            "ok": False,
            "error": "native_layer_missing",
            "we_are_the_native": True,
            "flash_chip": False,
        }
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    env.setdefault("SG_ROOT", str(INSTALL_ROOT.parent.parent))
    env.setdefault("KILROY_ROOT", str(Path(env["SG_ROOT"]) / "KILROY"))
    env.setdefault("QUEEN_ROOT", str(INSTALL_ROOT.parent / "Queen"))
    args = [sys.executable, str(script), "json"]
    if audit:
        args.append("--audit")
    proc = subprocess.run(args, capture_output=True, text=True, timeout=60, env=env)
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": (proc.stderr or "native_layer_bad_json")[:300]}


def _ai_integration_json(body: dict | None = None, *, peer: str = "127.0.0.1", headers: dict | None = None) -> dict:
    script = INSTALL_ROOT / "lib" / "ai-integration-hook.py"
    if not script.is_file():
        return {
            "schema": "nexus-ai-integration-hook/v1",
            "ok": False,
            "error": "ai_integration_hook_missing",
            "human_integration": False,
            "policy": "ai_only_never_human",
        }
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    if body is None:
        proc = subprocess.run(
            [sys.executable, str(script), "json"],
            capture_output=True,
            text=True,
            timeout=25,
            env=env,
        )
    else:
        payload = dict(body)
        payload["_peer"] = peer
        if headers:
            payload["_headers"] = headers
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": (proc.stderr or "ai_integration_bad_json")[:300]}


def _panel_field_meta() -> dict:
    field_max = _conf_flag("NEXUS_FIELD_MAX")
    refresh_ms = _conf_int("NEXUS_PANEL_REFRESH_MS", 5000)
    if field_max:
        refresh_ms = max(800, min(refresh_ms, 2000))
    quota = _conf_int("NEXUS_CPU_QUOTA_PCT", 85 if field_max else 5)
    return {
        "field_max": field_max,
        "panel_refresh_ms": refresh_ms,
        "amouranthrtx_rainbow": _conf_flag("NEXUS_AMOURANTHRTX_RAINBOW"),
        "event_driven_only": _conf_flag("NEXUS_EVENT_DRIVEN_ONLY"),
        "panel_parallel_workers": _conf_int("NEXUS_PANEL_PARALLEL_WORKERS", 8),
        "cpu_quota_pct": quota,
        "thermal_governor": _conf_flag("NEXUS_THERMAL_GOVERNOR", "1"),
        "field_mode": "smooth_powered" if field_max else "standard",
    }


def _panel_rtx_meta() -> dict:
    field_max = _conf_flag("NEXUS_FIELD_MAX")
    rtx = _conf_flag("NEXUS_PANEL_RTX_ZERO")
    zero = _conf_flag("NEXUS_PANEL_ZERO_COST", "1" if rtx else "0")
    if field_max:
        rtx = False
        zero = False
    try:
        poll_scale = float(_conf_val("NEXUS_PANEL_ZERO_COST_POLL_SCALE", "1.25"))
    except ValueError:
        poll_scale = 1.25
    return {
        "panel_rtx_zero": rtx,
        "panel_zero_cost": zero,
        "panel_zero_cost_poll_scale": poll_scale,
        "panel_build": "underlay-f9",
    }


def _status_shell(*, full: bool = False) -> str:
    version = _read_install_version()
    if full:
        return "{}"
    shell = {
        "field": True,
        "panel_ready": False,
        "version": version,
        "gatekeeper": {"connections": [], "harm_candidates": 0},
    }
    shell.update(_panel_poll_meta(shell))
    shell.update(_panel_rtx_meta())
    shell.update(_panel_field_meta())
    return json.dumps(shell, ensure_ascii=False)


def _thermal_headroom_meta() -> dict:
    """Read published thermal guard — no subprocess on panel GET."""
    path = STATE_DIR / "field-thermal-guard.json"
    if not path.is_file():
        return {"headroom_pct": 100.0, "rate_limit_active": False, "thermal_ok": True}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        headroom = float(doc.get("headroom_pct") or 100.0)
        rate_active = bool(doc.get("rate_limit_active"))
        return {
            "headroom_pct": round(headroom, 1),
            "rate_limit_active": rate_active,
            "thermal_ok": headroom >= 50.0 and not rate_active,
        }
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {"headroom_pct": 100.0, "rate_limit_active": False, "thermal_ok": True}


def _read_nexus_poll_seconds() -> dict[str, int]:
    """Adaptive panel poll intervals (seconds) — C2 overhaul doctrine + nexus.conf."""
    conf = INSTALL_ROOT / "config" / "nexus.conf"
    c2_doc = INSTALL_ROOT / "data" / "nexus-c2-doctrine.json"
    out = {"calm": 8, "alert": 6, "storm": 4}
    if c2_doc.is_file():
        try:
            raw = json.loads(c2_doc.read_text(encoding="utf-8"))
            base_ms = raw.get("poll_base_ms") or {}
            if base_ms:
                out = {
                    "calm": max(3, int(base_ms.get("calm", 8000)) // 1000),
                    "alert": max(3, int(base_ms.get("alert", 6000)) // 1000),
                    "storm": max(3, int(base_ms.get("storm", 4000)) // 1000),
                }
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    if _conf_flag("NEXUS_FIELD_MAX"):
        return {"calm": 3, "alert": 2, "storm": 1}
    if not conf.is_file():
        return out
    try:
        for line in conf.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key in ("NEXUS_PANEL_POLL_CALM", "NEXUS_BEHAVIOR_POLL_CALM"):
                out["calm"] = max(2, int(val))
            elif key in ("NEXUS_PANEL_POLL_ALERT", "NEXUS_BEHAVIOR_POLL_ALERT"):
                out["alert"] = max(2, int(val))
            elif key in ("NEXUS_PANEL_POLL_STORM", "NEXUS_BEHAVIOR_POLL_STORM"):
                out["storm"] = max(2, int(val))
    except (OSError, ValueError):
        pass
    return out


def _panel_poll_meta(doc: dict | None = None) -> dict:
    base = doc if isinstance(doc, dict) else {}
    mode = str(base.get("vigil_mode") or "calm").lower()
    if mode not in ("calm", "alert", "storm"):
        mode = "calm"
    polls = _read_nexus_poll_seconds()
    sec = polls.get(mode, polls["calm"])
    ms = sec * 1000
    thermal = _thermal_headroom_meta()
    headroom = float(thermal.get("headroom_pct") or 100.0)
    c2_doc_path = INSTALL_ROOT / "data" / "nexus-c2-doctrine.json"
    if c2_doc_path.is_file():
        try:
            c2_raw = json.loads(c2_doc_path.read_text(encoding="utf-8"))
            pt = c2_raw.get("poll_thermal") or {}
            full_pct = float(pt.get("headroom_full_pct", 80))
            throttle_pct = float(pt.get("headroom_throttle_pct", 50))
            if headroom < throttle_pct:
                ms = int(ms * float(pt.get("scale_crit", 4.0)))
            elif headroom < full_pct:
                ms = int(ms * float(pt.get("scale_below_throttle", 2.5)))
            elif headroom < 100.0:
                ms = int(ms * float(pt.get("scale_below_full", 1.5)))
            ms = max(3000, ms)
            sec = max(3, ms // 1000)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    return {
        "vigil_mode": mode,
        "poll_seconds": sec,
        "poll_ms": ms,
        "poll_intervals": polls,
        "thermal": thermal,
        "c2_overhaul": c2_doc_path.is_file(),
    }


def _read_status_json(*, full: bool = False) -> str:
    if not STATUS_JSON.is_file():
        return _status_shell(full=full)
    raw = STATUS_JSON.read_text(encoding="utf-8").strip()
    if not raw:
        return _status_shell(full=full)
    if full:
        try:
            doc = json.loads(raw)
            if isinstance(doc, dict):
                doc.update(_panel_poll_meta(doc))
                doc.update(_panel_rtx_meta())
                doc.update(_panel_field_meta())
                return json.dumps(doc, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
        return raw
    try:
        doc = json.loads(raw)
        if isinstance(doc, dict):
            version = _read_install_version()
            for key in PANEL_PARALLEL_KEYS:
                doc.pop(key, None)
            doc["version"] = version
            doc.update(_panel_poll_meta(doc))
            doc.update(_panel_rtx_meta())
            doc.update(_panel_field_meta())
            return json.dumps(doc, ensure_ascii=False)
    except json.JSONDecodeError:
        pass
    return _status_shell(full=full)


_PANEL_DOC_CACHE: dict | None = None
_PANEL_DOC_MTIME: float = -1.0


def _load_panel_doc() -> dict:
    global _PANEL_DOC_CACHE, _PANEL_DOC_MTIME
    if not STATUS_JSON.is_file():
        return {}
    try:
        mtime = STATUS_JSON.stat().st_mtime
    except OSError:
        return {}
    if _PANEL_DOC_CACHE is not None and mtime == _PANEL_DOC_MTIME:
        return _PANEL_DOC_CACHE
    try:
        raw = STATUS_JSON.read_text(encoding="utf-8")
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError:
            doc, _ = json.JSONDecoder().raw_decode(raw.lstrip())
        if isinstance(doc, dict):
            _PANEL_DOC_CACHE = doc
            _PANEL_DOC_MTIME = mtime
            return doc
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    return {}


def _slice_populated(key: str, val: dict) -> bool:
    if not isinstance(val, dict) or not val:
        return False
    if key == "host_attacks":
        return bool(val.get("updated")) or bool(val.get("schema")) or isinstance(val.get("points"), list)
    if key == "human_registry":
        return bool(val.get("table")) or bool(val.get("humans"))
    if key == "police_agency":
        return bool(val.get("agencies")) or bool(val.get("updated"))
    if key == "angel_research":
        tables = val.get("tables") or {}
        return any(isinstance(v, list) and v for v in tables.values()) or bool(val.get("updated"))
    if key == "census_field":
        return bool(val.get("last_run")) or bool(val.get("operator_gps_ready"))
    if key == "existence_identity":
        return bool(val.get("table")) or bool(val.get("updated"))
    if key == "gov_intel":
        return bool(val.get("records")) or val.get("record_count", 0) > 0
    if key == "program_tags":
        return bool(val.get("tags")) or bool(val.get("recent"))
    if key == "hostess7_command":
        return (
            val.get("schema") == "hostess7-command/v1"
            and (bool(val.get("intel_digest")) or bool(val.get("self_view")) or bool(val.get("transcript")))
        )
    return True


def _panel_slice(
    key: str,
    *,
    live: dict | None = None,
    default: dict | None = None,
) -> dict:
    """Zero-cost read: published field cache first, live builder only on miss."""
    doc = _load_panel_doc()
    val = doc.get(key)
    if isinstance(val, dict) and _slice_populated(key, val):
        out = dict(val)
        out["_field_cache"] = True
        out.setdefault("_incomplete", False)
        out.setdefault("_partial", False)
        return out
    live_ok = (
        isinstance(live, dict)
        and live
        and not live.get("error")
        and live.get("ok") is not False
    )
    if live_ok and (_slice_populated(key, live) or live.get("schema")):
        out = dict(live)
        out["_field_cache"] = False
        out.setdefault("_incomplete", False)
        out.setdefault("_partial", False)
        return out
    reason = "cache_miss_live_fail"
    if isinstance(live, dict) and live:
        reason = str(live.get("error") or live.get("detail") or "live_fail")
    out = dict(default or {})
    out["_incomplete"] = True
    out["_partial"] = True
    out["_slice_reason"] = reason
    out["_slice_key"] = key
    out.setdefault("ok", False)
    out.setdefault("error", reason)
    return out


_FIELD_PANEL_FILES: dict[str, Path] = {
    "field_dns": STATE_DIR / "field-dns-panel.json",
    "field_dhcp": STATE_DIR / "field-dhcp-panel.json",
}


def _read_field_panel_file(key: str) -> dict | None:
    fp = _FIELD_PANEL_FILES.get(key)
    if not fp or not fp.is_file():
        return None
    try:
        doc = json.loads(fp.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and doc.get("schema"):
            out = dict(doc)
            out["_field_cache"] = True
            out.setdefault("_incomplete", False)
            out.setdefault("_partial", False)
            return out
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _read_zachub_panel_cache(name: str) -> dict | None:
    """Fast loopback serve — avoid slow subprocess on panel hot paths."""
    api_names = {
        "storage": "field-zachub-storage.json",
        "fork_guard": "field-zachub-fork-guard.json",
        "qemu_racks": "field-zachub-qemu-racks.json",
        "battle_stations": "field-battle-stations.json",
    }
    state_names = {
        "storage": "field-zachub-storage-panel.json",
        "fork_guard": "field-zachub-fork-guard-panel.json",
        "qemu_racks": "field-zachub-qemu-racks-panel.json",
        "battle_stations": "field-battle-stations-panel.json",
    }
    candidates: list[Path] = []
    state_key = state_names.get(name)
    if state_key:
        candidates.append(STATE_DIR / state_key)
    api_key = api_names.get(name)
    if api_key:
        candidates.append(INSTALL_ROOT / "Hostess7" / "docs" / "api" / api_key)
    for fp in candidates:
        if not fp.is_file():
            continue
        try:
            doc = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(doc, dict) and (doc.get("schema") or doc.get("ok") is not None):
                out = dict(doc)
                out["_panel_cache"] = True
                out.setdefault("_incomplete", False)
                out.setdefault("_partial", False)
                return out
        except (OSError, json.JSONDecodeError):
            continue
    return None


def _read_botnet_panel_cache(name: str) -> dict | None:
    paths = {
        "registry": STATE_DIR / "field-botnet-registry-panel.json",
        "dns_dhcp": STATE_DIR / "field-botnet-dns-dhcp-panel.json",
    }
    fp = paths.get(name)
    if not fp or not fp.is_file():
        return None
    try:
        doc = json.loads(fp.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and doc.get("schema"):
            out = dict(doc)
            out["_panel_cache"] = True
            out.setdefault("_incomplete", False)
            out.setdefault("_partial", False)
            return out
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _read_field_host_desktop_cache(*, max_age_sec: int = 300) -> dict | None:
    """Serve cached field-host-desktop.json when fresh — skip slow subprocess scan."""
    fp = STATE_DIR / "field-host-desktop.json"
    if not fp.is_file():
        return None
    try:
        age = time.time() - fp.stat().st_mtime
        if age > max_age_sec:
            return None
        doc = json.loads(fp.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and doc.get("programs"):
            out = dict(doc)
            out["_panel_cache"] = True
            out["_cache_age_sec"] = round(age, 1)
            out.setdefault("_incomplete", False)
            out.setdefault("_partial", False)
            return out
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _sudo_available() -> bool:
    if os.geteuid() == 0:
        return True
    try:
        proc = subprocess.run(
            ["sudo", "-n", "true"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _read_state_json(name: str, default: dict) -> dict:
    fp = STATE_DIR / name
    if not fp.is_file():
        return default
    try:
        doc = json.loads(fp.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else default
    except (OSError, json.JSONDecodeError):
        return default


def _nexus_shell_json_fn(fn: str, *, sources: list[str] | None = None, timeout: int = 25) -> dict:
    sources = sources or []
    src = " && ".join(f"source '{INSTALL_ROOT}/lib/{s}'" for s in sources)
    inner = (
        f"source '{INSTALL_ROOT}/lib/nexus-common.sh' && nexus_load_config"
        f"{(' && ' + src) if src else ''} && {fn}"
    )
    ok, out = _run_nexus_bash(inner, timeout=timeout)
    if not ok or not (out or "").strip():
        return {}
    try:
        doc = json.loads(out)
        return doc if isinstance(doc, dict) else {}
    except json.JSONDecodeError:
        return {}


def _run_nexus_undo(action_id: str) -> bool:
    script = INSTALL_ROOT / "lib" / "threat-autosanitize.sh"
    if not script.is_file():
        return False
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    cmd = (
        f"source {INSTALL_ROOT}/lib/nexus-common.sh && "
        f"source {INSTALL_ROOT}/lib/firewall-sentinel.sh && "
        f"source {script} && "
        f"nexus_autosanitize_undo {action_id}"
    )
    proc = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    return proc.returncode == 0


def _run_nexus_paranoia(cmd: str, arg: str = "") -> bool:
    script = INSTALL_ROOT / "lib" / "paranoia-mode.sh"
    if not script.is_file():
        return False
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    inner = (
        f"source {INSTALL_ROOT}/lib/nexus-common.sh && "
        f"source {INSTALL_ROOT}/lib/firewall-sentinel.sh && "
        f"source {INSTALL_ROOT}/lib/threat-vectors.sh && "
        f"source {INSTALL_ROOT}/lib/packet-oracle.sh && "
        f"source {INSTALL_ROOT}/lib/eternal-vigil.sh && "
        f"source {script} && "
    )
    if cmd == "block_on":
        inner += "nexus_paranoia_set_block 1"
    elif cmd == "block_off":
        inner += "nexus_paranoia_set_block 0"
    elif cmd == "mode_on":
        inner += "nexus_paranoia_set_mode 1"
    elif cmd == "mode_off":
        inner += "nexus_paranoia_set_mode 0"
    elif cmd == "disable" and arg:
        safe = arg.replace("'", "'\"'\"'")
        inner += f"nexus_paranoia_disable_incident '{safe}'"
    elif cmd == "reenable" and arg:
        safe = arg.replace("'", "'\"'\"'")
        inner += f"nexus_paranoia_reenable_incident '{safe}'"
    else:
        return False
    proc = subprocess.run(
        ["bash", "-c", inner],
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
    )
    return proc.returncode == 0


def _run_nexus_firewall_trust(cmd: str, ip: str, direction: str = "out", label: str = "") -> bool:
    script = INSTALL_ROOT / "lib" / "firewall-trust.sh"
    if not script.is_file():
        return False
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    inner = (
        f"source {INSTALL_ROOT}/lib/nexus-common.sh && nexus_load_config && "
        f"source {INSTALL_ROOT}/lib/firewall-sentinel.sh && "
        f"source {script} && "
    )
    safe_ip = ip.replace("'", "'\"'\"'")
    safe_label = label.replace("'", "'\"'\"'")
    if cmd == "authorize":
        inner += f"nexus_firewall_authorize_ip '{safe_ip}' '{direction}' '{safe_label}' 'nexus-panel'"
    elif cmd == "revoke":
        inner += f"nexus_firewall_revoke_trust '{safe_ip}' '{direction}'"
    else:
        return False
    proc = subprocess.run(
        ["bash", "-c", inner],
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
    )
    return proc.returncode == 0


def _run_nexus_bash(inner: str, timeout: int = 30) -> tuple[bool, str]:
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.run(
        ["bash", "-c", inner],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    detail = (proc.stderr or proc.stdout or "").strip()[:400]
    return proc.returncode == 0, detail


def _load_nexus_shield_source() -> str:
    src = os.environ.get("NEXUS_SHIELD_SOURCE", "").strip()
    if src:
        return src
    conf = INSTALL_ROOT / "config" / "nexus.conf"
    if conf.is_file():
        try:
            for line in conf.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line.startswith("NEXUS_SHIELD_SOURCE="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
        except OSError:
            pass
    return ""


def _resolve_nexus_source_root() -> Path | None:
    """Locate git/dev tree with install-all.sh for UPDATE git fallback."""
    candidates: list[Path] = []
    src = _load_nexus_shield_source()
    if src:
        candidates.append(Path(src))
    candidates.extend([
        INSTALL_ROOT,
        INSTALL_ROOT.parent,
    ])
    staging = STATE_DIR / "update-staging"
    if staging.is_dir():
        for child in sorted(staging.glob("extract-*"), reverse=True):
            if (child / "install-all.sh").is_file() or any(child.rglob("install-all.sh")):
                candidates.append(child)
    seen: set[str] = set()
    for base in candidates:
        if not base:
            continue
        try:
            resolved = base.resolve()
        except OSError:
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        cur = resolved
        for _ in range(6):
            for name in ("install-all.sh", "stealth_install.sh"):
                install = cur / name
                if install.is_file():
                    return cur
            parent = cur.parent
            if parent == cur:
                break
            cur = parent
    return None


def _nexus_update_check(force: bool = False) -> dict:
    script = INSTALL_ROOT / "lib" / "nexus-update.py"
    if not script.is_file():
        return {"ok": False, "error": "update_checker_missing"}
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    args = [sys.executable, str(script)]
    if force:
        args.append("--force")
    proc = subprocess.run(args, capture_output=True, text=True, timeout=30, env=env)
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": "update_check_failed", "detail": (proc.stderr or "")[:200]}


def _ammoos_update_check(force: bool = False) -> dict:
    script = INSTALL_ROOT / "lib" / "ammoos-update-inplace.py"
    if not script.is_file():
        return {"ok": False, "error": "ammoos_update_checker_missing"}
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    env.setdefault("AMMOOS_GITHUB_REPO", "ZacharyGeurts/AmmoOS")
    env.setdefault("AMMOOS_UPDATE_MODE", os.environ.get("NEXUS_UPDATE_MODE", "git_tree"))
    args = [sys.executable, str(script), "check"]
    if force:
        args.append("--force")
    proc = subprocess.run(args, capture_output=True, text=True, timeout=30, env=env)
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": "ammoos_update_check_failed", "detail": (proc.stderr or "")[:200]}


def _ammoos_update_doctrine() -> dict:
    script = INSTALL_ROOT / "lib" / "ammoos-update-inplace.py"
    if not script.is_file():
        return {"ok": False, "error": "ammoos_update_doctrine_missing"}
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.run(
        [sys.executable, str(script), "doctrine"],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    try:
        doc = json.loads(proc.stdout or "{}")
        doc["ok"] = True
        return doc
    except json.JSONDecodeError:
        return {"ok": False, "error": "ammoos_update_doctrine_failed", "detail": (proc.stderr or "")[:200]}


def _ammoos_incorporate_posture() -> dict:
    script = INSTALL_ROOT / "lib" / "ammoos-incorporate.py"
    if not script.is_file():
        return {"ok": False, "error": "ammoos_incorporate_missing"}
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.run(
        [sys.executable, str(script), "posture"],
        capture_output=True,
        text=True,
        timeout=45,
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": "ammoos_incorporate_posture_failed", "detail": (proc.stderr or "")[:200]}


def _nexus_c2_snapshot(*, tier: str = "hot") -> dict:
    script = INSTALL_ROOT / "lib" / "nexus-c2-overhaul.py"
    if not script.is_file():
        return {"ok": False, "error": "nexus_c2_overhaul_missing"}
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.run(
        [sys.executable, str(script), "snapshot", f"--tier={tier}"],
        capture_output=True,
        text=True,
        timeout=12,
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": "nexus_c2_snapshot_failed", "detail": (proc.stderr or "")[:200]}


def _nexus_c2_posture() -> dict:
    script = INSTALL_ROOT / "lib" / "nexus-c2-overhaul.py"
    if not script.is_file():
        return {"ok": False, "error": "nexus_c2_overhaul_missing"}
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.run(
        [sys.executable, str(script), "posture"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": "nexus_c2_posture_failed", "detail": (proc.stderr or "")[:200]}


def _nexus_c2_doctrine() -> dict:
    script = INSTALL_ROOT / "lib" / "nexus-c2-overhaul.py"
    if not script.is_file():
        return {"ok": False, "error": "nexus_c2_overhaul_missing"}
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.run(
        [sys.executable, str(script), "doctrine"],
        capture_output=True,
        text=True,
        timeout=8,
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": "nexus_c2_doctrine_failed", "detail": (proc.stderr or "")[:200]}


def _ammoos_startup_posture() -> dict:
    script = INSTALL_ROOT / "lib" / "ammoos-startup-sovereign.py"
    if not script.is_file():
        return {"ok": False, "error": "ammoos_startup_sovereign_missing"}
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.run(
        [sys.executable, str(script), "posture"],
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": "ammoos_startup_posture_failed", "detail": (proc.stderr or "")[:200]}


def _ammoos_startup_doctrine() -> dict:
    script = INSTALL_ROOT / "lib" / "ammoos-startup-sovereign.py"
    if not script.is_file():
        return {"ok": False, "error": "ammoos_startup_sovereign_missing"}
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.run(
        [sys.executable, str(script), "doctrine"],
        capture_output=True,
        text=True,
        timeout=12,
        env=env,
    )
    try:
        doc = json.loads(proc.stdout or "{}")
        doc["ok"] = True
        return doc
    except json.JSONDecodeError:
        return {"ok": False, "error": "ammoos_startup_doctrine_failed", "detail": (proc.stderr or "")[:200]}


def _ammoos_incorporate_doctrine() -> dict:
    script = INSTALL_ROOT / "lib" / "ammoos-incorporate.py"
    if not script.is_file():
        return {"ok": False, "error": "ammoos_incorporate_missing"}
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    proc = subprocess.run(
        [sys.executable, str(script), "doctrine"],
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
    )
    try:
        doc = json.loads(proc.stdout or "{}")
        doc["ok"] = True
        return doc
    except json.JSONDecodeError:
        return {"ok": False, "error": "ammoos_incorporate_doctrine_failed"}


def _resolve_ammoos_source_root() -> Path | None:
    script = INSTALL_ROOT / "lib" / "ammoos-update-inplace.py"
    if script.is_file():
        env = os.environ.copy()
        env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
        env["NEXUS_STATE_DIR"] = str(STATE_DIR)
        proc = subprocess.run(
            [sys.executable, str(script), "source-root"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        try:
            doc = json.loads(proc.stdout or "{}")
            root = str(doc.get("source_root") or "").strip()
            if root:
                p = Path(root)
                if p.is_dir():
                    return p
        except json.JSONDecodeError:
            pass
    for candidate in (INSTALL_ROOT, INSTALL_ROOT.parent):
        if (candidate / "data" / "ammoos-version.json").is_file():
            return candidate
    return None


def _nexus_update_lock(args: list[str], timeout: int = 15) -> dict:
    return _nexus_py_json(INSTALL_ROOT / "lib" / "nexus-update-lock.py", args, timeout=timeout)


def _nexus_update_needs_sudo() -> dict | None:
    fp = STATE_DIR / "update-needs-sudo.json"
    if not fp.is_file():
        return None
    try:
        doc = json.loads(fp.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _spawn_nexus_update_apply(
    *,
    git_dir: Path | None,
    install_sh: Path | None,
    token: str,
    target: str,
    previous: str,
    tarball_url: str = "",
    update_mode: str = "release",
    apply_via: str = "",
    catalog_url: str = "",
) -> bool:
    apply_sh = INSTALL_ROOT / "lib" / "nexus-update-apply.sh"
    if not apply_sh.is_file() and git_dir:
        apply_sh = git_dir / "lib" / "nexus-update-apply.sh"
    if not apply_sh.is_file():
        return False
    work_cwd = str(git_dir) if git_dir else str(INSTALL_ROOT)
    log_fp = STATE_DIR / "update-apply.log"
    try:
        log_fp.parent.mkdir(parents=True, exist_ok=True)
        with log_fp.open("a", encoding="utf-8") as lf:
            lf.write(f"\n--- panel spawn update ---\n")
    except OSError:
        pass
    env = os.environ.copy()
    env.update({
        "NEXUS_INSTALL_ROOT": str(INSTALL_ROOT),
        "NEXUS_STATE_DIR": str(STATE_DIR),
        "NEXUS_UPDATE_LOCK_TOKEN": token,
        "NEXUS_UPDATE_TARGET": target,
        "NEXUS_UPDATE_PREVIOUS": previous,
        "NEXUS_UPDATE_MODE": update_mode or "release",
    })
    if tarball_url:
        env["NEXUS_UPDATE_TARBALL_URL"] = tarball_url
    if apply_via:
        env["NEXUS_UPDATE_APPLY_VIA"] = apply_via
    if catalog_url:
        env["NEXUS_UPDATE_CATALOG_URL"] = catalog_url
    if git_dir:
        env["NEXUS_UPDATE_GIT_DIR"] = str(git_dir)
    if install_sh and install_sh.is_file():
        env["NEXUS_UPDATE_INSTALL_SH"] = str(install_sh)
    for key in ("DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR", "XDG_CURRENT_DESKTOP", "DBUS_SESSION_BUS_ADDRESS"):
        if key in os.environ:
            env[key] = os.environ[key]
    try:
        with log_fp.open("a", encoding="utf-8") as lf:
            subprocess.Popen(
                ["bash", str(apply_sh)],
                stdout=lf,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
                cwd=work_cwd,
            )
        return True
    except OSError:
        return False


def _nexus_shell_publish_panel() -> None:
    script = INSTALL_ROOT / "lib" / "threat-panel.sh"
    if not script.is_file():
        return
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    env["NEXUS_THREAT_PANEL"] = "1"
    subprocess.run(
        [
            "bash", "-c",
            (
                f"source '{INSTALL_ROOT}/lib/nexus-common.sh' && "
                f"source '{script}' && "
                f"nexus_threat_panel_publish"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
    )


def _queen_boot_script() -> Path:
    qr = os.environ.get("QUEEN_ROOT")
    if qr:
        p = Path(qr) / "lib" / "queen-field-boot.py"
        if p.is_file():
            return p
    p = INSTALL_ROOT / "lib" / "queen-field-boot.py"
    if p.is_file():
        return p
    return INSTALL_ROOT.parent / "Queen" / "lib" / "queen-field-boot.py"


def _grok_build_script() -> Path:
    qr = os.environ.get("QUEEN_ROOT")
    if qr:
        p = Path(qr) / "lib" / "grok-build-bridge.py"
        if p.is_file():
            return p
    p = INSTALL_ROOT / "lib" / "grok-build-bridge.py"
    if p.is_file():
        return p
    return INSTALL_ROOT.parent / "Queen" / "lib" / "grok-build-bridge.py"


def _queen_build_script() -> Path:
    qr = os.environ.get("QUEEN_ROOT")
    if qr:
        p = Path(qr) / "lib" / "queen-build.py"
        if p.is_file():
            return p
    p = INSTALL_ROOT / "lib" / "queen-build.py"
    if p.is_file():
        return p
    return INSTALL_ROOT.parent / "Queen" / "lib" / "queen-build.py"


def _queen_root() -> Path:
    qr = os.environ.get("QUEEN_ROOT", "").strip()
    if qr:
        p = Path(qr)
        if p.is_dir():
            return p
    inside = INSTALL_ROOT / ".queen-inside"
    if inside.is_file():
        return INSTALL_ROOT
    candidate = INSTALL_ROOT.parent / "Queen"
    if candidate.is_dir():
        return candidate
    return INSTALL_ROOT


def _queen_eyeball_script() -> Path:
    p = _queen_root() / "lib" / "queen-eyeball.py"
    return p if p.is_file() else INSTALL_ROOT.parent / "Queen" / "lib" / "queen-eyeball.py"


def _queen_earball_script() -> Path:
    p = _queen_root() / "lib" / "queen-earball.py"
    return p if p.is_file() else INSTALL_ROOT.parent / "Queen" / "lib" / "queen-earball.py"


def _queen_mouthball_script() -> Path:
    p = _queen_root() / "lib" / "queen-mouthball.py"
    return p if p.is_file() else INSTALL_ROOT.parent / "Queen" / "lib" / "queen-mouthball.py"


def _queen_ball_dispatch(script: Path, body: dict | None = None, *, timeout: int = 180) -> dict:
    if not script.is_file():
        return {"ok": False, "error": "script_missing", "path": str(script)}
    env = _field_stack_env()
    queen = _queen_root()
    try:
        if body is None:
            proc = subprocess.run(
                [sys.executable, str(script), "json"],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=str(queen),
            )
        else:
            proc = subprocess.run(
                [sys.executable, str(script), "dispatch"],
                input=json.dumps(body, ensure_ascii=False),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=str(queen),
            )
        return json.loads(proc.stdout or "{}")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "dispatch_failed"}


def _grok16_root() -> Path:
    env = os.environ.get("GROK16_ROOT", "").strip()
    if env:
        return Path(env).expanduser()
    sg = Path(os.environ.get("SG_ROOT", "")).expanduser()
    if not sg.is_dir():
        sg = INSTALL_ROOT.parent if INSTALL_ROOT.name == "NewLatest" else INSTALL_ROOT.parent.parent
    return sg / "Grok16"


def _ensure_field_services_boot() -> None:
    """Start Truth DNS + Field DHCP serve loops when panel boots without nexus.sh."""
    if os.environ.get("NEXUS_FIELD_SERVICES_BOOT", "1") != "1":
        return
    script = INSTALL_ROOT / "lib" / "field-dns.sh"
    if not script.is_file():
        return
    try:
        subprocess.run(
            ["bash", "-c", f'source "{script}" && nexus_field_services_boot'],
            capture_output=True,
            text=True,
            timeout=25,
            env=_field_stack_env(),
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


def _kick_dynamic_trash_async(*, reason: str = "panel") -> None:
    """Background purge — hostile/kill-rekill/DNS/fork-guard table trash after strikes or boot."""
    if os.environ.get("NEXUS_DYNAMIC_ROUTES_KICK", "1") != "1":
        return
    dyn_py = INSTALL_ROOT / "lib" / "field-dynamic-routes.py"
    if not dyn_py.is_file():
        return
    try:
        subprocess.Popen(
            [sys.executable, str(dyn_py), "kick-trash"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**_field_stack_env(), "NEXUS_DYNAMIC_KICK_REASON": reason},
            start_new_session=True,
        )
    except OSError:
        pass


def _merge_live_dhcp_into_dns(payload: dict) -> dict:
    """Refresh embedded DHCP slice — field-dns cache often lags field-dhcp-panel.json."""
    if not isinstance(payload, dict):
        return payload
    live = _nexus_py_json(INSTALL_ROOT / "lib" / "field-dhcp.py", ["json"], timeout=12)
    if not isinstance(live, dict) or live.get("error"):
        return payload
    out = dict(payload)
    out["dhcp_server"] = live
    servers = dict(out.get("servers") or {})
    dhcp_srv = dict(servers.get("dhcp") or {})
    for key in (
        "running",
        "serve_loop",
        "port_67",
        "bind",
        "lease_count",
        "may_serve",
        "dns_option",
        "dns_option_v6",
        "leases_detailed",
        "stats_extended",
        "lease_history_events",
        "threats",
        "updated",
    ):
        if key in live:
            dhcp_srv[key] = live[key]
    servers["dhcp"] = dhcp_srv
    out["servers"] = servers
    traffic = out.get("traffic_patterns")
    if isinstance(traffic, dict):
        tp = dict(traffic)
        dhcp_tp = dict(tp.get("dhcp") or {})
        dhcp_tp["running"] = bool(live.get("running") or live.get("serve_loop") or live.get("port_67"))
        dhcp_tp["leases_active"] = int(live.get("lease_count") or 0)
        dhcp_tp["bind"] = live.get("bind") or "0.0.0.0:67"
        tp["dhcp"] = dhcp_tp
        tp["dhcp_lease_count"] = int(live.get("lease_count") or 0)
        out["traffic_patterns"] = tp
    out["_dhcp_live_merged"] = True
    return out


def _field_stack_env() -> dict[str, str]:
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    sg = INSTALL_ROOT.parent if INSTALL_ROOT.name == "NewLatest" else INSTALL_ROOT.parent.parent
    env.setdefault("SG_ROOT", str(sg))
    env.setdefault("GROK16_ROOT", str(_grok16_root()))
    env.setdefault("GROK16_SG_ROOT", str(sg))
    queen = _queen_root()
    env.setdefault("QUEEN_ROOT", str(queen))
    env.setdefault("FINAL_EYE_ROOT", str(sg / "Final_Eye"))
    env.setdefault("FINAL_EAR_ROOT", str(sg / "Final_Ear"))
    env.setdefault("FINAL_MOUTH_ROOT", str(sg / "Final_Mouth"))
    env.setdefault("HOSTESS7_ROOT", str(INSTALL_ROOT / "Hostess7"))
    py_parts = [
        str(queen / "lib"),
        str(sg / "Final_Eye"),
        str(sg / "Final_Ear"),
        str(sg / "Final_Mouth"),
    ]
    if env.get("PYTHONPATH"):
        py_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(p for p in py_parts if p)
    return env


def _parse_subprocess_json(proc: subprocess.CompletedProcess[str] | None, *, script: str = "") -> dict:
    if proc is None:
        return {"ok": False, "error": "no_process", "script": script}
    guard_py = INSTALL_ROOT / "lib" / "field-json-guard.py"
    if guard_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_json_guard_parse", guard_py)
            if spec and spec.loader:
                jg = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(jg)
                if hasattr(jg, "safe_json_response"):
                    return jg.safe_json_response(
                        proc.stdout,
                        proc.stderr,
                        rc=proc.returncode,
                        script=script,
                    )
        except Exception:
            pass
    text = (proc.stdout or "").strip() or "{}"
    try:
        doc = json.loads(text)
        if proc.returncode != 0 and isinstance(doc, dict) and doc.get("ok") is not False:
            doc["ok"] = False
            doc.setdefault("error", "nonzero_exit")
        return doc
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error": "bad_json",
            "detail": ((proc.stderr or "") or text)[:200],
            "script": script,
        }


# Live botnet hub — in-process + short TTL so /botnet panel can poll without refresh lag
_HUB_LIVE_LOCK = threading.Lock()
_HUB_LIVE_CACHE: dict[str, Any] = {"ts": 0.0, "payload": None}
_HUB_LIVE_TTL = 0.75  # seconds — concurrent polls share one rebuild
_HUB_MOD = None


def _field_botnet_hub_live(*, force: bool = False) -> dict:
    """Build hub in-process (no subprocess). TTL cache keeps panel snappy + live."""
    global _HUB_MOD
    now = time.time()
    with _HUB_LIVE_LOCK:
        cached = _HUB_LIVE_CACHE.get("payload")
        age = now - float(_HUB_LIVE_CACHE.get("ts") or 0)
        if (
            not force
            and isinstance(cached, dict)
            and cached.get("ok") is not False
            and age < _HUB_LIVE_TTL
        ):
            out = dict(cached)
            out["live"] = True
            out["live_panel"] = True
            out["cache_age_ms"] = int(age * 1000)
            out["poll_ms"] = int(out.get("poll_ms") or 1500)
            return out
    try:
        # force=1 reloads hub module so panel code updates appear without full process restart
        if _HUB_MOD is None or force:
            py = INSTALL_ROOT / "lib" / "field-botnet-hub.py"
            if not py.is_file():
                return {"ok": False, "error": "field-botnet-hub missing", "api": "/api/field-botnet-hub"}
            spec = importlib.util.spec_from_file_location(
                f"field_botnet_hub_live_http_{int(now)}" if force else "field_botnet_hub_live_http",
                py,
            )
            if not spec or not spec.loader:
                return {"ok": False, "error": "hub_spec_fail", "api": "/api/field-botnet-hub"}
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _HUB_MOD = mod
        payload = _HUB_MOD.build_hub() if hasattr(_HUB_MOD, "build_hub") else {"ok": False}
        if not isinstance(payload, dict):
            payload = {"ok": False, "error": "hub_bad_payload"}
        payload = dict(payload)
        payload["live"] = True
        payload["live_panel"] = True
        payload["auto_refresh"] = True
        payload["no_page_refresh_needed"] = True
        payload.setdefault("poll_ms", 1500)
        payload["api"] = "/api/field-botnet-hub"
        payload["cache_age_ms"] = 0
        with _HUB_LIVE_LOCK:
            _HUB_LIVE_CACHE["ts"] = time.time()
            _HUB_LIVE_CACHE["payload"] = payload
        return payload
    except Exception as exc:  # noqa: BLE001
        # Fall back to last good panel file so the UI never freezes
        panel = STATE_DIR / "field-botnet-hub-panel.json"
        try:
            fallback = json.loads(panel.read_text(encoding="utf-8"))
            if isinstance(fallback, dict):
                fallback = dict(fallback)
                fallback["live"] = True
                fallback["live_stale"] = True
                fallback["error_rebuild"] = str(exc)[:160]
                fallback["api"] = "/api/field-botnet-hub"
                return fallback
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            pass
        return {"ok": False, "error": str(exc)[:200], "api": "/api/field-botnet-hub", "live": True}


def _nexus_py_json(
    script: Path,
    args: list[str],
    timeout: int = 25,
    *,
    extra_env: dict[str, str] | None = None,
) -> dict:
    if not script.is_file():
        return {"ok": False, "error": "script_missing"}
    env = _field_stack_env()
    if extra_env:
        env.update(extra_env)
    env.setdefault("NEXUS_PROBE_DEPTH", "1")
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "script": script.name}
    return _parse_subprocess_json(proc, script=script.name)


def _nexus_py_text(
    script: Path,
    args: list[str],
    timeout: int = 12,
    *,
    extra_env: dict[str, str] | None = None,
) -> str:
    if not script.is_file():
        return ""
    env = _field_stack_env()
    if extra_env:
        env.update(extra_env)
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return (proc.stdout or proc.stderr or "").strip()
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _zachub_storage_api(
    path: str,
    *,
    query: dict | None = None,
    body: dict | None = None,
    headers: Any = None,
) -> dict:
    zachub_py = INSTALL_ROOT / "lib" / "field-zachub-storage.py"
    if not zachub_py.is_file():
        return {"ok": False, "error": "field_zachub_storage_missing"}
    sub = (
        path.replace("/api/field-zachub-storage", "")
        .replace("/api/zachub-storage", "")
        .replace("/api/ammodrive-storage", "")
        .strip("/")
    )
    req = body if isinstance(body, dict) else {}
    if sub in ("provision", "apply") or req.get("action") in ("provision", "apply"):
        args = ["provision"]
        if str(req.get("dry_run") or query.get("dry_run", ["0"])[0] if query else "0").strip().lower() in ("1", "true", "yes"):
            args.append("--dry-run")
        if str(req.get("full") or (query.get("full", ["0"])[0] if query else "0")).strip().lower() in ("1", "true", "yes"):
            args.append("--full")
    elif sub in ("capacity", "report"):
        args = ["capacity"]
    elif sub in ("mirror", "github-truth"):
        args = ["mirror"]
        if str(req.get("dry_run") or (query.get("dry_run", ["0"])[0] if query else "0")).strip().lower() in ("1", "true", "yes"):
            args.append("--dry-run")
    elif sub in ("sync", "siblings"):
        args = ["sync"]
        if str(req.get("dry_run") or (query.get("dry_run", ["0"])[0] if query else "0")).strip().lower() in ("1", "true", "yes"):
            args.append("--dry-run")
    elif sub in ("layout", "provision-layout"):
        args = ["layout"]
        if str(req.get("dry_run") or (query.get("dry_run", ["0"])[0] if query else "0")).strip().lower() in ("1", "true", "yes"):
            args.append("--dry-run")
    elif sub == "roots":
        args = ["roots"]
    else:
        args = ["json"]
    extra_env: dict[str, str] = {}
    if headers and (headers.get("X-Zachub-Dry-Run") or "").strip().lower() in ("1", "yes", "on"):
        extra_env["ZACHUB_DRY_RUN"] = "1"
        if args[0] in ("provision", "mirror", "sync", "layout") and "--dry-run" not in args:
            args.append("--dry-run")
    return _nexus_py_json(zachub_py, args, timeout=300, extra_env=extra_env or None)


def _queen_world_proxy_http(
    method: str,
    path: str,
    *,
    query: str = "",
    body: bytes | None = None,
    content_type: str = "application/json",
    timeout: float = 120.0,
) -> tuple[int, bytes, str]:
    proxy_py = INSTALL_ROOT / "lib" / "field-queen-world-proxy.py"
    if not proxy_py.is_file():
        doc = {"ok": False, "error": "queen_proxy_missing"}
        return 503, json.dumps(doc).encode(), "application/json"
    import importlib.util
    spec = importlib.util.spec_from_file_location("field_queen_proxy_http", proxy_py)
    if not spec or not spec.loader:
        doc = {"ok": False, "error": "queen_proxy_load_failed"}
        return 503, json.dumps(doc).encode(), "application/json"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.proxy_request(method, path, query=query, body=body, content_type=content_type, timeout=timeout)


def _ensure_training_viewer() -> dict[str, Any]:
    port = int(os.environ.get("H7_TRAINING_VIEWER_PORT", "9488"))
    url = f"http://127.0.0.1:{port}/"
    health = f"{url}api/health"
    try:
        req = urllib.request.Request(health, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            if 200 <= resp.status < 400:
                return {"ok": True, "url": url, "port": port, "already_running": True}
    except (urllib.error.URLError, TimeoutError, OSError):
        pass
    launch = INSTALL_ROOT / "hostess7-training-viewer" / "launch.sh"
    if not launch.is_file():
        return {"ok": False, "error": "training_viewer_missing", "url": url}
    env = _field_stack_env()
    env["H7_TRAINING_VIEWER_PORT"] = str(port)
    try:
        subprocess.run(
            ["bash", str(launch), "url"],
            env=env,
            cwd=str(INSTALL_ROOT),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "url": url}
    for _ in range(30):
        try:
            req = urllib.request.Request(health, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if 200 <= resp.status < 400:
                    return {"ok": True, "url": url, "port": port, "started": True}
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.2)
    return {"ok": False, "error": "training_viewer_unavailable", "url": url}


def _field_always_files_dispatch(body: dict[str, Any] | None = None, *, timeout: int = 120) -> dict:
    script = INSTALL_ROOT / "lib" / "field-always-files.py"
    if not script.is_file():
        return {"ok": False, "error": "field_always_files_missing", "schema": "field-always-files/v1"}
    env = _field_stack_env()
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps(body if isinstance(body, dict) else {}),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "field_always_files_timeout"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "field_always_files_dispatch_failed"}


def _field_broadcaster_chamber_dispatch(body: dict[str, Any] | None = None, *, timeout: int = 90) -> dict:
    script = INSTALL_ROOT / "lib" / "field-broadcaster-chamber.py"
    if not script.is_file():
        return {"ok": False, "error": "broadcaster_chamber_missing"}
    env = _field_stack_env()
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps(body if isinstance(body, dict) else {}),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "broadcaster_chamber_timeout"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "broadcaster_chamber_dispatch_failed"}


def _field_broadcaster_studio_dispatch(body: dict[str, Any] | None = None, *, timeout: int = 90) -> dict:
    script = INSTALL_ROOT / "lib" / "field-broadcaster-studio.py"
    if not script.is_file():
        return {"ok": False, "error": "studio_missing"}
    env = _field_stack_env()
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch", json.dumps(body if isinstance(body, dict) else {})],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "studio_dispatch_timeout"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "studio_dispatch_failed"}


def _field_body_system_dispatch(body: dict[str, Any] | None = None, *, timeout: int = 120) -> dict:
    script = INSTALL_ROOT / "lib" / "field-body-system.py"
    if not script.is_file():
        return {"ok": False, "error": "field_body_system_missing"}
    env = _field_stack_env()
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps(body if isinstance(body, dict) else {}),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "field_body_system_timeout"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "field_body_system_dispatch_failed"}


def _field_audio_dac_dispatch(body: dict[str, Any] | None = None, *, timeout: int = 90) -> dict:
    script = INSTALL_ROOT / "lib" / "field-audio-dac-chamber.py"
    if not script.is_file():
        return {"ok": False, "error": "audio_dac_missing"}
    env = _field_stack_env()
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps(body if isinstance(body, dict) else {}),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "audio_dac_timeout"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "audio_dac_dispatch_failed"}


def _field_eye_threat_dispatch(body: dict[str, Any] | None = None, *, timeout: int = 60) -> dict:
    script = INSTALL_ROOT / "lib" / "field-eye-threat-chamber.py"
    if not script.is_file():
        return {"ok": False, "error": "field_eye_threat_missing"}
    env = _field_stack_env()
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps(body if isinstance(body, dict) else {}),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "field_eye_threat_timeout"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "field_eye_threat_dispatch_failed"}


def _field_final_eye_canvas_dispatch(body: dict[str, Any] | None = None, *, timeout: int = 60) -> dict:
    script = INSTALL_ROOT / "lib" / "field-final-eye-canvas-bridge.py"
    if not script.is_file():
        return {"ok": False, "error": "canvas_bridge_missing"}
    env = _field_stack_env()
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps(body if isinstance(body, dict) else {}),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "canvas_bridge_timeout"}
    except json.JSONDecodeError:
        return {"ok": False, "error": "canvas_bridge_dispatch_failed"}


_FIELD_OPERATOR_MOD: Any = None
_FIELD_PERF_FLYOUT_MOD: Any = None
_FIELD_DEPTH_SING_MOD: Any = None
_G16_LANGUAGE_TEST_MOD: Any = None


def _g16_language_test_mod():
    global _G16_LANGUAGE_TEST_MOD
    if _G16_LANGUAGE_TEST_MOD is not None:
        return _G16_LANGUAGE_TEST_MOD
    script = INSTALL_ROOT / "lib" / "g16-language-test-matrix.py"
    if not script.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location("g16_language_test_panel", script)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _G16_LANGUAGE_TEST_MOD = mod
    return mod


def _field_depth_singularizer_mod():
    global _FIELD_DEPTH_SING_MOD
    if _FIELD_DEPTH_SING_MOD is not None:
        return _FIELD_DEPTH_SING_MOD
    script = INSTALL_ROOT / "lib" / "field-depth-singularizer.py"
    if not script.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location("field_depth_singularizer_panel", script)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _FIELD_DEPTH_SING_MOD = mod
    return mod


def _enforce_depth_field_http_path(raw_path: str) -> str | None:
    """Redirect when field_depth is present — depth fields sealed and destroyed."""
    if "field_depth" not in raw_path:
        return None
    mod = _field_depth_singularizer_mod()
    if not mod or not hasattr(mod, "single_field_depth_enabled") or not mod.single_field_depth_enabled():
        return None
    rec = mod.enforce_depth_field_impossible(f"http://127.0.0.1{raw_path}")
    if not rec.get("violation"):
        return None
    parsed = urlparse(str(rec.get("url") or ""))
    out = parsed.path or "/"
    if parsed.query:
        out += "?" + parsed.query
    return out


def _field_perf_flyout_sample(*, reset: bool = False) -> dict:
    global _FIELD_PERF_FLYOUT_MOD
    script = INSTALL_ROOT / "lib" / "field-performance-flyout.py"
    if not script.is_file():
        return {"schema": "field-performance-flyout/v1", "ok": False, "error": "perf_flyout_missing"}
    if _FIELD_PERF_FLYOUT_MOD is None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("field_performance_flyout_panel", script)
        if not spec or not spec.loader:
            return _nexus_py_json(script, ["json"], timeout=10)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _FIELD_PERF_FLYOUT_MOD = mod
    try:
        return _FIELD_PERF_FLYOUT_MOD.sample(reset=reset)
    except Exception as exc:
        return {"schema": "field-performance-flyout/v1", "ok": False, "error": str(exc)}


def _field_error_dashboard_sample() -> dict:
    script = INSTALL_ROOT / "lib" / "field-error-dashboard.py"
    if not script.is_file():
        return {"schema": "field-error-dashboard/v1", "ok": False, "error": "error_dashboard_missing"}
    payload = _nexus_py_json(script, ["json"], timeout=20)
    return payload or {"schema": "field-error-dashboard/v1", "ok": False, "error": "error_dashboard_empty"}


def _ammo_net_health_sample() -> dict:
    script = INSTALL_ROOT / "lib" / "ammo-net-health.py"
    if not script.is_file():
        return {"schema": "ammo-net-health/v1", "ok": False, "error": "ammo_net_health_missing"}
    payload = _nexus_py_json(script, ["json"], timeout=30)
    return payload or {"schema": "ammo-net-health/v1", "ok": False, "error": "ammo_net_health_empty"}


def _field_operator_inproc():
    global _FIELD_OPERATOR_MOD
    if _FIELD_OPERATOR_MOD is not None:
        return _FIELD_OPERATOR_MOD
    import importlib.util

    op_py = INSTALL_ROOT / "lib" / "field-operator.py"
    if not op_py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_operator_panel", op_py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        mod.plate_router(reload=True)
    except Exception:
        pass
    _FIELD_OPERATOR_MOD = mod
    return mod


def _field_operator_hot_route(target: str, *, override: str | None = None) -> dict:
    mod = _field_operator_inproc()
    if mod is None:
        return _nexus_py_json(INSTALL_ROOT / "lib" / "field-operator.py", ["route", target], timeout=3)
    if override:
        return mod.route_to_board(target, override=override)
    return mod.hot_route(target)


def _field_operator_hot_route_batch(batch: list[str], *, override: str | None = None) -> dict:
    mod = _field_operator_inproc()
    if mod is None:
        args = ["route-batch", *[str(x) for x in batch if x]]
        return _nexus_py_json(INSTALL_ROOT / "lib" / "field-operator.py", args, timeout=5)
    if override:
        return mod.route_batch(batch, override=override)
    return mod.hot_route_batch(batch)


def _field_operator_hot_route_status() -> dict:
    mod = _field_operator_inproc()
    if mod is None:
        return _nexus_py_json(INSTALL_ROOT / "lib" / "field-operator.py", ["hot-route"], timeout=8)
    return mod.hot_route_status()


def _deprecated_hot_route_gone_payload(*, replacement: str) -> dict:
    return {
        "ok": False,
        "removed": True,
        "reason": "endpoint_removed_use_hot_route",
        "replacement": replacement,
    }


def _jockey_json(args: list[str], timeout: int = 25) -> dict:
    return _nexus_py_json(INSTALL_ROOT / "lib" / "monitor-jockey.py", args, timeout=timeout)


def _kill_codes_json(args: list[str], timeout: int = 45) -> dict:
    return _nexus_py_json(INSTALL_ROOT / "lib" / "kill-codes.py", args, timeout=timeout)


def _field_plate_script() -> Path:
    if os.environ.get("NEXUS_FIELD_PLATES", "1") == "1":
        p = INSTALL_ROOT / "lib" / "field-panel-field.py"
        if p.is_file():
            return p
    return INSTALL_ROOT / "lib" / "field-panel-parallel.py"


def _field_parallel_payload(*, publish: bool = False) -> dict:
    """Serve stored threat-panel.json; field amplitude publish when publish=1 or store empty."""
    try:
        stale = not STATUS_JSON.is_file() or STATUS_JSON.stat().st_size < 128
    except OSError:
        stale = True
    if publish or stale:
        return _nexus_py_json(_field_plate_script(), ["json"], timeout=120)
    doc = _load_panel_doc()
    keys = [
        k
        for k in doc
        if not str(k).startswith("_") and k not in ("field", "parallel_load", "field_load")
    ]
    return {
        "ok": True,
        "stored": True,
        "mode": "field" if doc.get("field_load") else "legacy",
        "infinite_dimension": bool(doc.get("infinite_dimension")),
        "field_amplitude": doc.get("field_amplitude"),
        "panel": doc,
        "slice_count": len(keys),
        "field_slices_updated": keys,
        "field_slices_failed": [],
    }


def _field_field_payload(*, publish: bool = False) -> dict:
    """Canonical field plate route — infinite dimension amplitude process."""
    return _field_parallel_payload(publish=publish)


def _nexus_host_map_trash_add(pin_id: str) -> bool:
    pin_id = str(pin_id or "").strip()
    if not pin_id:
        return False
    trash_sh = INSTALL_ROOT / "lib" / "host-map-trash.sh"
    if not trash_sh.is_file():
        return False
    safe = pin_id.replace("'", "'\"'\"'")
    inner = (
        f"source {INSTALL_ROOT}/lib/nexus-common.sh && nexus_load_config && "
        f"source {trash_sh} && nexus_host_map_trash_add '{safe}'"
    )
    ok, _ = _run_nexus_bash(inner, timeout=15)
    return ok


def _nexus_shell_prelude() -> str:
    return (
        f"source {INSTALL_ROOT}/lib/nexus-common.sh && nexus_load_config && "
        f"source {INSTALL_ROOT}/lib/firewall-sentinel.sh && "
        f"source {INSTALL_ROOT}/lib/threat-autosanitize.sh && "
        f"source {INSTALL_ROOT}/lib/paranoia-mode.sh && "
        f"source {INSTALL_ROOT}/lib/nexus-settings.sh && "
        f"source {INSTALL_ROOT}/lib/adblock-loader.sh && "
    )


def _nexus_settings_key_allowed(key: str) -> bool:
    try:
        script = INSTALL_ROOT / "lib" / "queen-settings-surface.py"
        if not script.is_file():
            return True
        proc = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=8,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL_ROOT), "NEXUS_STATE_DIR": str(STATE_DIR)},
        )
        if proc.returncode != 0:
            return True
        doc = json.loads(proc.stdout or "{}")
        if not doc.get("surface_locked"):
            return True
        locked = set(doc.get("locked_nexus_keys") or [])
        return str(key).strip() not in locked
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return True


def _run_nexus_settings_set(key: str, val: str) -> bool:
    if not _nexus_settings_key_allowed(key):
        return False
    script = INSTALL_ROOT / "lib" / "nexus-settings.sh"
    if not script.is_file():
        return False
    safe_key = key.replace("'", "'\"'\"'")
    inner = _nexus_shell_prelude() + f"nexus_settings_set '{safe_key}' '{val}'"
    ok, _ = _run_nexus_bash(inner, timeout=45)
    return ok


def _run_nexus_adblock_load(preset: str = "", url: str = "") -> bool:
    script = INSTALL_ROOT / "lib" / "adblock-loader.sh"
    if not script.is_file():
        return False
    inner = _nexus_shell_prelude()
    if preset:
        safe = preset.replace("'", "'\"'\"'")
        inner += f"nexus_adblock_load_preset '{safe}'"
    elif url:
        safe = url.replace("'", "'\"'\"'")
        inner += f"nexus_adblock_load_url '{safe}'"
    else:
        return False
    ok, _ = _run_nexus_bash(inner, timeout=180)
    return ok


def _run_nexus_adblock_apply() -> bool:
    script = INSTALL_ROOT / "lib" / "adblock-loader.sh"
    if not script.is_file():
        return False
    inner = _nexus_shell_prelude() + "nexus_adblock_apply"
    ok, _ = _run_nexus_bash(inner, timeout=120)
    return ok


def _run_nexus_autosanitize_toggle(enabled: bool) -> bool:
    script = INSTALL_ROOT / "lib" / "threat-autosanitize.sh"
    if not script.is_file():
        return False
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
    val = "1" if enabled else "0"
    cmd = (
        f"source {INSTALL_ROOT}/lib/nexus-common.sh && "
        f"source {script} && "
        f"nexus_autosanitize_set_enabled {val}"
    )
    proc = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    return proc.returncode == 0


def _tail_file(path: Path, lines: int = 120) -> str:
    if not path.is_file():
        return ""
    try:
        data = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(data[-lines:])
    except OSError:
        return ""


_FIELD_POPCORN_MOD: Any = None


def _field_popcorn_mod():
    global _FIELD_POPCORN_MOD
    if _FIELD_POPCORN_MOD is not None:
        return _FIELD_POPCORN_MOD
    script = INSTALL_ROOT / "lib" / "field-popcorn-player.py"
    if not script.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location("field_popcorn_panel", script)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _FIELD_POPCORN_MOD = mod
    return mod


def _broadcaster_media_mod():
    script = INSTALL_ROOT / "lib" / "field-broadcaster.py"
    if not script.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location("field_broadcaster_media", script)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _serve_broadcaster_playback(handler: "Handler", query: dict[str, list[str]]) -> None:
    mod = _broadcaster_media_mod()
    if not mod:
        handler._send(404, '{"ok":false,"error":"broadcaster_missing"}', "application/json")
        return
    name = str((query.get("name") or [""])[0]).strip()
    item = mod.resolve_recording(name) if name else None
    if not item:
        handler._send(404, '{"ok":false,"error":"recording_not_found"}', "application/json")
        return
    path = Path(str(item["path"]))
    try:
        size = path.stat().st_size
    except OSError:
        handler._send(404, '{"ok":false,"error":"recording_unreadable"}', "application/json")
        return
    mime = str(item.get("mime") or "video/x-matroska")
    range_hdr = handler.headers.get("Range", "")
    parsed = mod.parse_range_header(range_hdr, size) if range_hdr and hasattr(mod, "parse_range_header") else None
    if parsed:
        start, end = parsed
        data = mod.read_recording_range(path, start, end)
        handler.send_response(206)
        handler.send_header("Content-Type", mime)
        handler.send_header("Content-Length", str(len(data)))
        handler.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        handler.send_header("Accept-Ranges", "bytes")
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("X-Content-Type-Options", "nosniff")
        handler.end_headers()
        handler.wfile.write(data)
        return
    handler.send_response(200)
    handler.send_header("Content-Type", mime)
    handler.send_header("Content-Length", str(size))
    handler.send_header("Accept-Ranges", "bytes")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    try:
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 512)
                if not chunk:
                    break
                handler.wfile.write(chunk)
    except OSError:
        pass


def _serve_broadcaster_desktop_preview(handler: "Handler", query: dict[str, list[str]]) -> None:
    cap_py = INSTALL_ROOT / "lib" / "field-broadcaster-capture.py"
    if not cap_py.is_file():
        handler._send(404, '{"ok":false,"error":"capture_missing"}', "application/json")
        return
    monitor = str((query.get("monitor") or query.get("id") or [""])[0]).strip()
    if not monitor:
        handler._send(400, '{"ok":false,"error":"monitor_required"}', "application/json")
        return
    payload = _nexus_py_json(cap_py, ["preview", monitor], timeout=20)
    if not payload.get("ok"):
        handler._send(403 if payload.get("error") == "threat_blocked" else 404, json.dumps(payload), "application/json")
        return
    path = Path(str(payload.get("path") or ""))
    try:
        if not path.is_file():
            raise OSError("missing")
        data = path.read_bytes()
    except OSError:
        handler._send(404, '{"ok":false,"error":"preview_missing"}', "application/json")
        return
    handler.send_response(200)
    handler.send_header("Content-Type", "image/jpeg")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store, max-age=0")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    handler.wfile.write(data)


def _serve_popcorn_stream(handler: "Handler", query: dict[str, list[str]]) -> None:
    mod = _field_popcorn_mod()
    if not mod:
        handler._send(404, '{"ok":false,"error":"popcorn_missing"}', "application/json")
        return
    media_id = str((query.get("id") or [""])[0]).strip()
    item = mod.resolve_media(media_id) if media_id else None
    if not item:
        handler._send(404, '{"ok":false,"error":"media_not_found"}', "application/json")
        return
    path = Path(str(item["path"]))
    try:
        size = path.stat().st_size
    except OSError:
        handler._send(404, '{"ok":false,"error":"media_unreadable"}', "application/json")
        return
    mime = str(item.get("mime") or "application/octet-stream")
    range_hdr = handler.headers.get("Range", "")
    parsed = mod.parse_range_header(range_hdr, size) if range_hdr else None
    if parsed:
        start, end = parsed
        data = mod.read_range(path, start, end)
        handler.send_response(206)
        handler.send_header("Content-Type", mime)
        handler.send_header("Content-Length", str(len(data)))
        handler.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        handler.send_header("Accept-Ranges", "bytes")
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        handler.wfile.write(data)
        return
    handler.send_response(200)
    handler.send_header("Content-Type", mime)
    handler.send_header("Content-Length", str(size))
    handler.send_header("Accept-Ranges", "bytes")
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    try:
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 512)
                if not chunk:
                    break
                handler.wfile.write(chunk)
    except OSError:
        pass


def _serve_popcorn_thumb(handler: "Handler", query: dict[str, list[str]]) -> None:
    mod = _field_popcorn_mod()
    if not mod:
        handler._send(404, '{"ok":false,"error":"popcorn_missing"}', "application/json")
        return
    media_id = str((query.get("id") or [""])[0]).strip()
    mode = str((query.get("mode") or ["viewing"])[0]).strip().lower()
    if not media_id:
        handler._send(400, '{"ok":false,"error":"id_required"}', "application/json")
        return
    data = mod.thumb_read(media_id, mode)
    if not data:
        handler._send(404, '{"ok":false,"error":"thumb_missing"}', "application/json")
        return
    handler.send_response(200)
    handler.send_header("Content-Type", "image/jpeg")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(data)


def _panel_static_mime(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".woff2": "font/woff2",
    }.get(ext, "application/octet-stream")


def _serve_panel_html(handler: "Handler", target: Path) -> None:
    if target.suffix == ".html" and target.name == "threat-panel.html":
        try:
            body = target.read_text(encoding="utf-8")
        except OSError:
            handler._send(404, "not found", "text/plain")
            return
        handler._send(200, body, "text/html; charset=utf-8")
        return
    try:
        handler._send(200, target.read_bytes(), _panel_static_mime(target))
    except OSError:
        handler._send(404, "not found", "text/plain")


class Handler(BaseHTTPRequestHandler):
    server_version = "NEXUS-Panel/10"
    sys_version = ""

    def log_message(self, *_):
        return

    @staticmethod
    def _peer_loopback(handler: "Handler") -> bool:
        peer = handler.client_address[0] if handler.client_address else ""
        return peer in _LOOPBACK_CLIENTS or str(peer).startswith("127.")

    @staticmethod
    def _peer_field_lan(handler: "Handler") -> bool:
        """People on Field DHCP LAN may open display panels (no middle men)."""
        peer = handler.client_address[0] if handler.client_address else ""
        if not peer:
            return False
        # Field dummy-queen / dummy-field subnets
        if peer.startswith("192.168.47.") or peer.startswith("192.168.50."):
            return True
        # Portal binds themselves
        if peer in ("192.168.47.1", "192.168.50.1"):
            return True
        return False

    def handle(self):
        # Loopback C2 always. Field LAN people: display-only panels so they join our internet.
        if not (self._peer_loopback(self) or self._peer_field_lan(self)):
            try:
                self.request.sendall(b"HTTP/1.0 403 Forbidden\r\nConnection: close\r\n\r\n")
            except OSError:
                pass
            return
        super().handle()

    def _send(self, code, body, ctype, extra_headers: dict[str, str] | None = None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Permissions-Policy",
            "camera=(), microphone=(), display-capture=(), clipboard-read=(self), clipboard-write=(self), geolocation=()",
        )
        self.send_header("X-Admin-Shield", "keyboard-hooks-blocked")
        self.send_header("X-Smart-Wire", "nexus-keyboard-no-middleman")
        self.send_header("X-Hardware-Wire", "nexus-field-hardware-hooks")
        if "text/html" in str(ctype):
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
                "connect-src 'self' http://127.0.0.1:* https://127.0.0.1:* "
                "http://192.168.47.1:* http://192.168.50.1:* "
                "http://[::1]:* ws://127.0.0.1:*; "
                "frame-src 'self' http://127.0.0.1:* https://duckduckgo.com; "
                "object-src 'none'; base-uri 'self'",
            )
            self.send_header("X-NEXUS-C2-Security", "loopback-secured-csp")
        if extra_headers:
            for hk, hv in extra_headers.items():
                self.send_header(hk, hv)
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def _ai_root_api_guard(self, path: str, method: str = "GET", body: dict | None = None) -> bool:
        script = INSTALL_ROOT / "lib" / "field-ai-root-api-guard.py"
        if not script.is_file():
            return True
        peer = self.client_address[0] if self.client_address else "127.0.0.1"
        try:
            spec = importlib.util.spec_from_file_location("ai_root_api_guard", script)
            if not spec or not spec.loader:
                return True
            guard = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(guard)
            if not hasattr(guard, "gate_access"):
                return True
            ch = "machine"
            hdrs = {k: v for k, v in self.headers.items()}
            hl = {k.lower(): v for k, v in hdrs.items()}
            if hl.get("x-human-input") in ("1", "true", "yes"):
                ch = "keystroke"
            if hl.get("x-nexus-ai-actor") in ("1", "true", "yes", "ai", "grok"):
                ch = "ai"
            verdict = guard.gate_access(
                system_id="threat_panel_http",
                peer=str(peer),
                path=path,
                method=method,
                channel=ch,
                body=body if isinstance(body, dict) else None,
                headers=hdrs,
            )
        except Exception:
            return True
        if verdict.get("ok"):
            return True
        extra = {
            "X-Field-AI-Root-Guard": "blocked",
            "X-Field-AI-Root-Scope": str(verdict.get("ai_root_scope") or "ai_work_only"),
        }
        self._send(
            int(verdict.get("code") or 403),
            json.dumps(verdict, ensure_ascii=False),
            "application/json",
            extra_headers=extra,
        )
        return False

    def _beyond_darpa_api_gate(self, path: str, method: str = "GET", body: dict | None = None) -> bool:
        script = INSTALL_ROOT / "lib" / "beyond-darpa-security.py"
        if not script.is_file():
            return True
        peer = self.client_address[0] if self.client_address else "127.0.0.1"
        try:
            spec = importlib.util.spec_from_file_location("beyond_darpa_gate", script)
            if not spec or not spec.loader:
                return True
            bds = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bds)
            if not hasattr(bds, "gate_access"):
                return True
            ch = "machine"
            hdrs = {k: v for k, v in self.headers.items()}
            hl = {k.lower(): v for k, v in hdrs.items()}
            if hl.get("x-human-input") in ("1", "true", "yes"):
                ch = "keystroke"
            verdict = bds.gate_access(
                system_id="threat_panel_http",
                peer=str(peer),
                path=path,
                method=method,
                channel=ch,
                body=body if isinstance(body, dict) else None,
                headers=hdrs,
            )
        except Exception:
            return True
        if verdict.get("ok"):
            return True
        self._send(
            int(verdict.get("code") or 403),
            json.dumps(verdict, ensure_ascii=False),
            "application/json",
            extra_headers={"X-Beyond-DARPA-Tier": "beyond_darpa_lockheed"},
        )
        return False

    def _ironclad_api_gate(self, path: str, method: str = "GET", body: dict | None = None) -> bool:
        mod = _ironclad_secure_api_mod()
        if not mod or not hasattr(mod, "ironclad_secure_api"):
            return self._beyond_darpa_api_gate(path, method, body)
        peer = self.client_address[0] if self.client_address else ""
        try:
            verdict = mod.ironclad_secure_api().gate(
                peer=str(peer),
                path=path,
                method=method,
                headers={k: v for k, v in self.headers.items()},
                body=body,
            )
        except Exception:
            return self._beyond_darpa_api_gate(path, method, body)
        if not verdict.get("ok"):
            extra = {}
            if hasattr(mod, "security_headers"):
                try:
                    extra = mod.security_headers()
                except Exception:
                    extra = {}
            self._send(
                int(verdict.get("code") or 403),
                json.dumps(verdict, ensure_ascii=False),
                "application/json",
                extra_headers=extra,
            )
            return False
        if not self._ai_root_api_guard(path, method, body):
            return False
        return self._beyond_darpa_api_gate(path, method, body)

    def do_GET(self):
        depth_redirect = _enforce_depth_field_http_path(self.path)
        if depth_redirect is not None:
            self.send_response(302)
            self.send_header("Location", depth_redirect)
            self.send_header("X-Nexus-Depth-Field", "forbidden")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return

        path = unquote(self.path.split("?", 1)[0])
        qs = parse_qs(urlparse(self.path).query)
        # Everyone Online celebration — slim by default (cache-first). Full rows via side paths.
        if path in (
            "/api/everyone-online",
            "/api/field-everyone-online-celebrate",
            "/api/celebrate",
            "/api/everyone-online/slim",
            "/api/everyone-online/summary",
            "/api/everyone-online/full",
            "/api/everyone-online/existence",
            "/api/everyone-online/leases",
            "/api/celebrate/slim",
            "/api/celebrate/summary",
            "/api/celebrate/full",
            "/api/celebrate/existence",
            "/api/celebrate/leases",
        ):
            mode = "slim"
            if path.endswith("/full") or (qs.get("full") or [""])[0] in ("1", "true", "yes"):
                mode = "full"
            elif path.endswith("/summary") or (qs.get("summary") or [""])[0] in ("1", "true", "yes"):
                mode = "summary"
            elif path.endswith("/existence"):
                mode = "existence"
            elif path.endswith("/leases"):
                mode = "leases"
            if (qs.get("mode") or [""])[0]:
                mode = str((qs.get("mode") or ["slim"])[0]).strip().lower() or mode
            payload = None
            # Fast path: prebuilt slim / row sidecars under STATE_DIR
            try:
                if mode in ("slim", "json", "status", "panel") and (STATE_DIR / "field-everyone-online-celebrate-slim.json").is_file():
                    payload = json.loads(
                        (STATE_DIR / "field-everyone-online-celebrate-slim.json").read_text(encoding="utf-8")
                    )
                elif mode == "summary" and (STATE_DIR / "field-everyone-online-celebrate-slim.json").is_file():
                    slim = json.loads(
                        (STATE_DIR / "field-everyone-online-celebrate-slim.json").read_text(encoding="utf-8")
                    )
                    payload = {
                        "ok": True,
                        "schema": "field-everyone-online-summary/v1",
                        "updated": slim.get("updated"),
                        "title": slim.get("title"),
                        "motto": slim.get("motto"),
                        "message": slim.get("message"),
                        "shared_hold": slim.get("shared_hold"),
                        "rescue_count": slim.get("rescue_count"),
                        "planetary_rescue": slim.get("planetary_rescue"),
                        "live": slim.get("live"),
                        "progress": slim.get("progress"),
                        "not_a_mobile_operator": slim.get("not_a_mobile_operator", True),
                        "we_are_the_internet": slim.get("we_are_the_internet", True),
                        "autopilot": True,
                        "slim": True,
                        "existence_count": (slim.get("existence") or {}).get("count"),
                        "lease_count": (slim.get("leases") or {}).get("count"),
                        "apis": slim.get("apis"),
                    }
                elif mode == "existence" and (STATE_DIR / "field-everyone-online-existence-rows.json").is_file():
                    payload = json.loads(
                        (STATE_DIR / "field-everyone-online-existence-rows.json").read_text(encoding="utf-8")
                    )
                elif mode == "leases" and (STATE_DIR / "field-everyone-online-lease-rows.json").is_file():
                    payload = json.loads(
                        (STATE_DIR / "field-everyone-online-lease-rows.json").read_text(encoding="utf-8")
                    )
                elif mode == "full" and (STATE_DIR / "field-everyone-online-celebrate-panel.json").is_file():
                    payload = json.loads(
                        (STATE_DIR / "field-everyone-online-celebrate-panel.json").read_text(encoding="utf-8")
                    )
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                payload = None
            if payload is None:
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-everyone-online-celebrate.py",
                    [mode if mode in ("slim", "summary", "full", "existence", "leases") else "slim"],
                    timeout=90 if mode in ("full", "existence", "leases") else 30,
                )
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return
        # Field chat hub — window only · no hooks · ask we deliver (GET status/poll/peers)
        if path == "/api/field-chat-hub" or path.startswith("/api/field-chat-hub/"):
            try:
                import importlib.util

                _p = INSTALL_ROOT / "lib" / "field-chat-hub.py"
                _s = importlib.util.spec_from_file_location("field_chat_hub_get", _p)
                if not _s or not _s.loader:
                    self._send(503, json.dumps({"ok": False, "error": "chat_hub_missing"}), "application/json")
                    return
                _m = importlib.util.module_from_spec(_s)
                _s.loader.exec_module(_m)
                qs_ch = parse_qs(urlparse(self.path).query)
                code, payload = _m.handle_http("GET", path, qs_ch, None)
                self._send(
                    code,
                    json.dumps(payload if isinstance(payload, dict) else {"ok": False}, ensure_ascii=False),
                    "application/json",
                )
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # Maintenance world — panel HTML only reads these APIs (no panel hooks)
        if path == "/api/field-maintenance-world" or path.startswith("/api/field-maintenance-world/"):
            try:
                import importlib.util

                _p = INSTALL_ROOT / "lib" / "field-maintenance-world.py"
                _s = importlib.util.spec_from_file_location("field_maint_world_get", _p)
                if not _s or not _s.loader:
                    self._send(503, json.dumps({"ok": False, "error": "maintenance_world_missing"}), "application/json")
                    return
                _m = importlib.util.module_from_spec(_s)
                _s.loader.exec_module(_m)
                qs_mw = parse_qs(urlparse(self.path).query)
                code, payload = _m.handle_http("GET", path, qs_mw, None)
                self._send(
                    code,
                    json.dumps(payload if isinstance(payload, dict) else {"ok": False}, ensure_ascii=False),
                    "application/json",
                )
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # Home Internet — every home 127.0.0.1/internet (API read-only for panel)
        if path == "/api/field-home-internet" or path.startswith("/api/field-home-internet/"):
            try:
                import importlib.util

                _p = INSTALL_ROOT / "lib" / "field-home-internet-panel.py"
                _s = importlib.util.spec_from_file_location("field_home_internet_get", _p)
                if not _s or not _s.loader:
                    self._send(503, json.dumps({"ok": False, "error": "home_internet_missing"}), "application/json")
                    return
                _m = importlib.util.module_from_spec(_s)
                _s.loader.exec_module(_m)
                qs_hi = parse_qs(urlparse(self.path).query)
                code, payload = _m.handle_http("GET", path, qs_hi, None)
                self._send(
                    code,
                    json.dumps(payload if isinstance(payload, dict) else {"ok": False}, ensure_ascii=False),
                    "application/json",
                )
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # World sole IP + lease — every IP ours · old plane gone · trillions · speeds
        if path in (
            "/api/field-world-ip-lease-sole",
            "/api/field-world-ip-lease-sole/",
            "/api/world-ip-lease",
            "/api/world-ip-lease/",
            "/api/sole-ip-lease",
        ):
            try:
                cached = STATE_DIR / "field-world-ip-lease-sole-panel.json"
                qs_w = parse_qs(urlparse(self.path).query)
                force = str(qs_w.get("refresh", qs_w.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "seal",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-world-ip-lease-sole.py",
                    ["once"] if not force else ["seal"],
                    timeout=90 if force else 45,
                )
                if not isinstance(payload, dict):
                    payload = {"ok": False, "error": "world_ip_lease_bad"}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # Full-featured Internet — everyone · speeds · SAW · Field UDP · to the death
        if path in (
            "/api/field-full-featured-internet",
            "/api/field-full-featured-internet/",
            "/api/full-internet",
            "/api/full-internet/",
        ):
            try:
                cached = STATE_DIR / "field-full-featured-internet-panel.json"
                qs_fi = parse_qs(urlparse(self.path).query)
                force = str(qs_fi.get("refresh", qs_fi.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-full-featured-internet.py",
                    ["status"] if not force else ["once"],
                    timeout=90 if force else 45,
                )
                if not isinstance(payload, dict):
                    payload = {"ok": False, "error": "full_internet_bad"}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        if path in (
            "/api/field-home-devices-to-the-death",
            "/api/field-home-devices-to-the-death/",
            "/api/home-devices-to-the-death",
        ):
            try:
                cached = STATE_DIR / "field-home-devices-to-the-death-panel.json"
                if cached.is_file():
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                        return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-home-devices-to-the-death.py",
                    ["status"],
                    timeout=30,
                )
                self._send(200, json.dumps(payload if isinstance(payload, dict) else {"ok": False}, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        if path in (
            "/api/field-everyone-fabric-direct",
            "/api/field-everyone-fabric-direct/",
            "/api/everyone-fabric-direct",
            "/api/fabric-direct",
            "/api/no-middle-men",
        ):
            try:
                cached = STATE_DIR / "field-everyone-fabric-direct-panel.json"
                qs_ed = parse_qs(urlparse(self.path).query)
                force = str(qs_ed.get("refresh", qs_ed.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-everyone-fabric-direct.py",
                    ["once"] if force else ["status"],
                    timeout=90 if force else 40,
                )
                self._send(200, json.dumps(payload if isinstance(payload, dict) else {"ok": False}, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # Autonet status API (display only)
        if path in ("/api/field-autonet", "/api/field-autonet/"):
            try:
                import importlib.util

                _p = INSTALL_ROOT / "lib" / "field-autonet.py"
                _s = importlib.util.spec_from_file_location("field_autonet_get", _p)
                if not _s or not _s.loader:
                    self._send(503, json.dumps({"ok": False, "error": "autonet_missing"}), "application/json")
                    return
                _m = importlib.util.module_from_spec(_s)
                _s.loader.exec_module(_m)
                payload = _m.status() if hasattr(_m, "status") else _m.seal_autonet(write=False)
                self._send(200, json.dumps(payload if isinstance(payload, dict) else {"ok": False}, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # Home security — AV + network for every home (GET status)
        if path == "/api/field-home-security" or path.startswith("/api/field-home-security/"):
            try:
                import importlib.util

                _p = INSTALL_ROOT / "lib" / "field-home-security-panel.py"
                _s = importlib.util.spec_from_file_location("field_home_sec_get", _p)
                if not _s or not _s.loader:
                    self._send(503, json.dumps({"ok": False, "error": "home_security_missing"}), "application/json")
                    return
                _m = importlib.util.module_from_spec(_s)
                _s.loader.exec_module(_m)
                qs_hs = parse_qs(urlparse(self.path).query)
                code, payload = _m.handle_http("GET", path, qs_hs, None)
                self._send(
                    code,
                    json.dumps(payload if isinstance(payload, dict) else {"ok": False}, ensure_ascii=False),
                    "application/json",
                )
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # Never-reconnect dossiers UI APIs (page flip · catalog · kills ticker · CSV)
        if path == "/api/field-never-reconnect-table/csv" or path.startswith(
            "/api/field-never-reconnect-table/"
        ):
            sub = path[len("/api/field-never-reconnect-table") :].strip("/") or "status"
            qs_nr = parse_qs(urlparse(self.path).query)
            script = INSTALL_ROOT / "lib" / "field-never-reconnect-table.py"
            if sub == "csv":
                try:
                    import subprocess as _sp

                    cp = _sp.run(
                        [sys.executable, str(script), "csv"],
                        cwd=str(INSTALL_ROOT),
                        capture_output=True,
                        text=True,
                        timeout=60,
                        env={
                            **os.environ,
                            "NEXUS_INSTALL_ROOT": str(INSTALL_ROOT),
                            "NEXUS_STATE_DIR": str(STATE_DIR),
                            "AML_BUILD": "0",
                        },
                        check=False,
                    )
                    body = cp.stdout or ""
                    self.send_response(200 if cp.returncode == 0 else 500)
                    self.send_header("Content-Type", "text/csv; charset=utf-8")
                    self.send_header(
                        "Content-Disposition",
                        'attachment; filename="never-reconnect.csv"',
                    )
                    self.send_header("Content-Length", str(len(body.encode("utf-8"))))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body.encode("utf-8"))
                except Exception as exc:
                    self._send(
                        500,
                        json.dumps({"ok": False, "error": str(exc)[:160]}),
                        "application/json",
                    )
                return
            if sub in ("page", "flip"):
                page_n = (qs_nr.get("page") or ["1"])[0]
                payload = _nexus_py_json(script, ["page", str(page_n)], timeout=45)
                self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
                return
            if sub in ("catalog", "index", "list"):
                q = (qs_nr.get("q") or [""])[0]
                kind = (qs_nr.get("kind") or [""])[0]
                args = ["catalog"]
                if q:
                    args.append(q)
                if kind:
                    args.append(kind)
                payload = _nexus_py_json(script, args, timeout=45)
                self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
                return
            if sub in ("kills", "ticker", "feed", "kgo"):
                lim = (qs_nr.get("limit") or ["80"])[0]
                payload = _nexus_py_json(script, ["kills", str(lim)], timeout=30)
                self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
                return
            if sub in ("status", "panel", ""):
                cached = STATE_DIR / "field-never-reconnect-table-panel.json"
                if cached.is_file():
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                        return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(script, ["status"], timeout=20)
                self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
                return
        # Useful Field plane APIs — panel-cache first, status subprocess fallback (read-only)
        _FIELD_USEFUL = {
            "/api/field-secure-bot-rollout": (
                "field-secure-bot-rollout-panel.json",
                "lib/field-secure-bot-rollout.py",
                ["status"],
            ),
            "/api/field-udp-fry": (
                "field-udp-fry-panel.json",
                "lib/field-udp-fry.py",
                ["json"],
            ),
            "/api/field-always-of-stuff": (
                "field-always-of-stuff-panel.json",
                "lib/field-always-of-stuff.py",
                ["status"],
            ),
            "/api/field-redundant-mirror-truth": (
                "field-redundant-mirror-truth-panel.json",
                "lib/field-redundant-mirror-truth.py",
                ["status"],
            ),
            "/api/field-network-always-true": (
                "field-network-always-true-panel.json",
                "lib/field-network-always-true.py",
                ["status"],
            ),
            "/api/field-udp-always": (
                "field-udp-always-panel.json",
                "lib/field-udp-always.py",
                ["panel"],
            ),
            "/api/field-no-outside-view": (
                "field-no-outside-view-panel.json",
                "lib/field-no-outside-view.py",
                ["status"],
            ),
            "/api/field-property-cordon": (
                "field-property-cordon-panel.json",
                "lib/field-property-cordon.py",
                ["status"],
            ),
            "/api/field-dns-dhcp-raid": (
                "field-dns-dhcp-raid-truth.json",
                "lib/field-secure-bot-rollout.py",
                ["raid"],
            ),
            "/api/field-raid-truth": (
                "field-dns-dhcp-raid-truth.json",
                "lib/field-secure-bot-rollout.py",
                ["raid"],
            ),
            "/api/field-registry-raid": (
                "field-registry-raid-panel.json",
                "lib/field-registry-raid.py",
                ["status"],
            ),
            "/api/field-planetary-celebration": (
                "field-planetary-celebration-publish-panel.json",
                "lib/field-planetary-celebration-publish.py",
                ["build"],
            ),
            "/api/field-autopilot": (
                "field-autopilot-internet-closed-panel.json",
                "lib/field-autopilot-internet-closed.py",
                ["status"],
            ),
            "/api/field-destination-ab": (
                "field-destination-ab-panel.json",
                "lib/field-destination-ab.py",
                ["json"],
            ),
            "/api/field-traceroute": (
                "field-traceroute-panel.json",
                "lib/field-traceroute.py",
                ["json"],
            ),
            "/api/field-spawn-storm-orphan-fix": (
                "field-spawn-storm-orphan-fix-panel.json",
                "lib/field-spawn-storm-orphan-fix.py",
                ["status"],
            ),
            "/api/field-turbo-orphan-watch": (
                "field-turbo-orphan-watch-panel.json",
                "lib/field-turbo-orphan-watch.py",
                ["json"],
            ),
            "/api/field-global-endpoints": (
                "field-global-endpoints-panel.json",
                "lib/field-global-endpoints.py",
                ["json"],
            ),
            "/api/field-homeowner-secure-zone": (
                "field-homeowner-secure-zone-panel.json",
                "lib/field-homeowner-secure-zone.py",
                ["status"],
            ),
            "/api/field-permanent-ban-udp-destroy": (
                "field-permanent-ban-udp-destroy-panel.json",
                "lib/field-permanent-ban-udp-destroy.py",
                ["panel"],
            ),
            "/api/field-vector-destroy": (
                "field-vector-destroy-panel.json",
                "lib/field-vector-destroy.py",
                ["panel"],
            ),
            "/api/field-vector-ironclad-cleanup": (
                "field-vector-ironclad-cleanup-panel.json",
                "lib/field-vector-ironclad-cleanup.py",
                ["panel"],
            ),
            "/api/field-never-reconnect-table": (
                "field-never-reconnect-table-panel.json",
                "lib/field-never-reconnect-table.py",
                ["status"],
            ),
            "/api/field-g16-untouchable": (
                "field-g16-untouchable-panel.json",
                "lib/field-g16-untouchable-binaries.py",
                ["status"],
            ),
            "/api/field-homeowner-secure-zone": (
                "field-homeowner-secure-zone-panel.json",
                "lib/field-homeowner-secure-zone.py",
                ["status"],
            ),
            "/api/field-fleet-planetary-dns-dhcp": (
                "field-fleet-planetary-dns-dhcp-panel.json",
                "lib/field-fleet-planetary-dns-dhcp.py",
                ["json"],
            ),
            "/api/field-connect-people": (
                "field-connect-people-panel.json",
                "lib/field-connect-people.py",
                ["json"],
            ),
            "/api/field-exist-real": (
                None,  # always live — non-synthetic identity + portals
                "lib/field-exist-real.py",
                ["exist"],
            ),
            "/api/field-discover-handoff": (
                "field-discover-handoff-panel.json",
                "lib/field-discover-handoff.py",
                ["json"],
            ),
            "/api/field-secure-bot-rollout": (
                "field-secure-bot-rollout-panel.json",
                "lib/field-secure-bot-rollout.py",
                ["status"],
            ),
            "/api/field-udp-outlet-scan": (
                "field-udp-outlet-scan-panel.json",
                "lib/field-udp-outlet-scan.py",
                ["panel"],
            ),
            "/api/field-ironclad-bsp-dns": (
                "field-ironclad-bsp-dns-panel.json",
                "lib/field-ironclad-bsp-dns.py",
                ["panel"],
            ),
            "/api/kilroy-ipxe-nexus-c2-stack": (
                "kilroy-ipxe-nexus-c2-stack-panel.json",
                "lib/kilroy-ipxe-nexus-c2-stack.py",
                ["panel"],
            ),
        }
        # Botnet hub — always live in-process (panel polls without full page refresh)
        if path in ("/api/field-botnet-hub", "/api/botnet-hub", "/api/botnet"):
            qs = parse_qs(urlparse(self.path).query)
            force = str((qs.get("force") or qs.get("nocache") or ["0"])[0]).lower() in (
                "1",
                "true",
                "yes",
            )
            payload = _field_botnet_hub_live(force=force)
            if isinstance(payload, dict):
                payload = dict(payload)
                payload.setdefault("api", "/api/field-botnet-hub")
                payload.setdefault("read_only", True)
                payload.setdefault("live", True)
                payload.setdefault("live_panel", True)
            self._send(
                200,
                json.dumps(payload or {"ok": False, "api": "/api/field-botnet-hub"}, ensure_ascii=False),
                "application/json",
                extra_headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Field-Live": "1",
                    "X-Poll-Ms": str(int((payload or {}).get("poll_ms") or 1500)),
                },
            )
            return
        if path in (
            "/api/field-planet-endpoint-hold",
            "/api/planet-endpoint",
            "/api/planet-hold",
            "/api/interferer-pwnership",
        ):
            qs = parse_qs(urlparse(self.path).query)
            force = str((qs.get("force") or qs.get("reconnect") or ["0"])[0]).lower() in (
                "1",
                "true",
                "yes",
                "reconnect",
            )
            py = INSTALL_ROOT / "lib" / "field-planet-endpoint-hold.py"
            payload: dict[str, Any] = {"ok": False, "error": "module_missing"}
            if py.is_file():
                try:
                    import importlib.util

                    spec = importlib.util.spec_from_file_location("field_planet_endpoint_hold", py)
                    mod = importlib.util.module_from_spec(spec) if spec else None
                    if spec and spec.loader and mod is not None:
                        spec.loader.exec_module(mod)
                        if force and hasattr(mod, "reconnect_botnet"):
                            payload = mod.reconnect_botnet()
                        elif path.endswith("interferer-pwnership") and hasattr(mod, "claim_pwnership"):
                            payload = mod.claim_pwnership()
                        elif hasattr(mod, "panel_json"):
                            payload = mod.panel_json(reconnect=force)
                        else:
                            payload = {"ok": False, "error": "no_panel"}
                except Exception as exc:
                    payload = {"ok": False, "error": str(exc)[:240]}
            if isinstance(payload, dict):
                payload.setdefault("api", "/api/field-planet-endpoint-hold")
            self._send(
                200,
                json.dumps(payload or {"ok": False}, ensure_ascii=False),
                "application/json",
                extra_headers={"Cache-Control": "no-store"},
            )
            return
        if path in _FIELD_USEFUL:
            panel_name, rel, args = _FIELD_USEFUL[path]
            payload = None
            # panel_name None => always live rebuild
            if panel_name:
                cached = STATE_DIR / panel_name
                if cached.is_file():
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                        payload = None
            if payload is None:
                payload = _nexus_py_json(INSTALL_ROOT / rel, args, timeout=90)
            if isinstance(payload, dict):
                payload = dict(payload)
                payload.setdefault("api", path)
                payload.setdefault("read_only", True)
            self._send(200, json.dumps(payload or {"ok": False, "api": path}, ensure_ascii=False), "application/json")
            return
        # Autopilot display — websites show stuff ONLY with our API keys (no people on botnet).
        # Display always requires a key. Closed-seal status is loopback OR key.
        if path in (
            "/api/field-autopilot-display",
            "/api/field-autopilot-internet-closed",
            "/api/field-display",
        ):
            peer = self.client_address[0] if self.client_address else ""
            loop = peer in ("127.0.0.1", "::1", "::ffff:127.0.0.1") or str(peer).startswith("127.")
            key = (
                (self.headers.get("X-AmmoNet-Key") or "")
                or (self.headers.get("X-Field-Api-Key") or "")
                or (self.headers.get("Authorization") or "")
            )
            display_path = path in ("/api/field-autopilot-display", "/api/field-display")
            auth_ok = False
            key_ok = False
            if key:
                try:
                    import importlib.util

                    _p = INSTALL_ROOT / "lib" / "field-autopilot-internet-closed.py"
                    _s = importlib.util.spec_from_file_location("autopilot_closed_auth", _p)
                    if _s and _s.loader:
                        _m = importlib.util.module_from_spec(_s)
                        _s.loader.exec_module(_m)
                        v = _m.verify_key(key)
                        key_ok = bool(v.get("ok"))
                except Exception:
                    key_ok = False
            if display_path:
                # Websites: always API key. No open display surface.
                auth_ok = key_ok
            else:
                # Seal status: us on loopback, or key holders
                auth_ok = key_ok or loop
            if not auth_ok:
                self._send(
                    401,
                    json.dumps(
                        {
                            "ok": False,
                            "error": "api_key_required",
                            "display_only": True,
                            "no_people": True,
                            "headers": ["Authorization: Bearer <key>", "X-AmmoNet-Key: <key>"],
                            "motto": "Websites display with our keys only — no people on the botnet",
                        }
                    ),
                    "application/json",
                )
                return
            if display_path:
                disp = STATE_DIR / "field-autopilot-display.json"
                if disp.is_file():
                    try:
                        payload = json.loads(disp.read_text(encoding="utf-8"))
                        payload = dict(payload)
                        payload["_display_only"] = True
                        payload["_no_control"] = True
                        self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                        return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-autopilot-internet-closed.py",
                    ["display"],
                    timeout=20,
                )
                self._send(200, json.dumps(payload or {"ok": False}), "application/json")
                return
            # status seal (loopback or key)
            cached = STATE_DIR / "field-autopilot-internet-closed-panel.json"
            if cached.is_file():
                try:
                    payload = json.loads(cached.read_text(encoding="utf-8"))
                    self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                    return
                except (OSError, json.JSONDecodeError):
                    pass
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-autopilot-internet-closed.py",
                ["status"],
                timeout=15,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return
        # Bot network + AmmoNet lease APIs — loopback only (closed fabric; no remote people control)
        if path in (
            "/api/field-botnet-dns-dhcp",
            "/api/field-botnet-dns-dhcp/keepalive",
            "/api/field-botnet-registry",
            "/api/field-botnet-full-dns-dhcp-authority",
            "/api/field-botnet-autopilot",
            "/api/field-dhcp",
            "/api/field-ammonet-lease-takeover",
            "/api/field-friendly-secure-serve",
            "/api/field-planetary-dns-dhcp",
            "/api/field-serving-truth",
            "/api/field-registry-h7-bsp",
            "/api/field-fleet-faster-servers",
            "/api/field-internet-big-numbers",
            "/api/field-serving-capacity",
            "/api/field-authority-capacity",
            "/api/field-world-ip-lease-sole",
            "/api/field-comms-saw-secure-lines",
            "/api/field-fleet-live",
            "/api/field-botnet-threat-heuristics",
            "/api/field-udp-outlet-rehit-old",
            "/api/field-antivirus-network-defender",
            "/api/antivirus",
        ):
            peer = self.client_address[0] if self.client_address else ""
            loop = peer in ("127.0.0.1", "::1", "::ffff:127.0.0.1") or str(peer).startswith("127.")
            if not loop:
                self._send(
                    403,
                    json.dumps(
                        {
                            "ok": False,
                            "error": "botnet_closed_no_people",
                            "human_intervention": False,
                            "display": "use /api/field-autopilot-display with API key",
                        }
                    ),
                    "application/json",
                )
                return
            py_map = {
                "/api/field-botnet-dns-dhcp": (INSTALL_ROOT / "lib" / "field-botnet-dns-dhcp.py", ["json"]),
                "/api/field-botnet-dns-dhcp/keepalive": (INSTALL_ROOT / "lib" / "field-botnet-dns-dhcp.py", ["keepalive"]),
                "/api/field-botnet-registry": (INSTALL_ROOT / "lib" / "field-botnet-registry.py", ["json"]),
                "/api/field-botnet-full-dns-dhcp-authority": (
                    INSTALL_ROOT / "lib" / "field-botnet-full-dns-dhcp-authority.py",
                    ["json"],
                ),
                "/api/field-botnet-autopilot": (INSTALL_ROOT / "lib" / "field-botnet-autopilot.py", ["json"]),
                "/api/field-dhcp": (INSTALL_ROOT / "lib" / "field-dhcp.py", ["json"]),
                "/api/field-ammonet-lease-takeover": (
                    INSTALL_ROOT / "lib" / "field-ammonet-lease-takeover.py",
                    ["status"],
                ),
                "/api/field-friendly-secure-serve": (
                    INSTALL_ROOT / "lib" / "field-friendly-secure-serve.py",
                    ["json"],
                ),
                "/api/field-planetary-dns-dhcp": (
                    INSTALL_ROOT / "lib" / "field-planetary-dns-dhcp.py",
                    ["json"],
                ),
                "/api/field-serving-truth": (
                    INSTALL_ROOT / "lib" / "field-serving-truth.py",
                    ["status"],
                ),
                "/api/field-registry-h7-bsp": (
                    INSTALL_ROOT / "lib" / "field-registry-h7-bsp.py",
                    ["status"],
                ),
                "/api/field-fleet-faster-servers": (
                    INSTALL_ROOT / "lib" / "field-fleet-faster-servers.py",
                    ["status"],
                ),
                "/api/field-internet-big-numbers": (
                    INSTALL_ROOT / "lib" / "field-internet-big-numbers.py",
                    ["status"],
                ),
                "/api/field-serving-capacity": (
                    INSTALL_ROOT / "lib" / "field-internet-big-numbers.py",
                    ["status"],
                ),
                "/api/field-authority-capacity": (
                    INSTALL_ROOT / "lib" / "field-internet-big-numbers.py",
                    ["status"],
                ),
                "/api/field-world-ip-lease-sole": (
                    INSTALL_ROOT / "lib" / "field-world-ip-lease-sole.py",
                    ["status"],
                ),
                "/api/field-comms-saw-secure-lines": (
                    INSTALL_ROOT / "lib" / "field-udp-outlet-scan.py",
                    ["doctrine"],
                ),
                "/api/field-fleet-live": (
                    INSTALL_ROOT / "lib" / "field-fleet-live.py",
                    ["json"],
                ),
                "/api/field-botnet-threat-heuristics": (
                    INSTALL_ROOT / "lib" / "field-botnet-threat-heuristics.py",
                    ["panel"],
                ),
                "/api/field-udp-outlet-rehit-old": (
                    INSTALL_ROOT / "lib" / "field-udp-outlet-scan.py",
                    ["status"],
                ),
                "/api/field-antivirus-network-defender": (
                    INSTALL_ROOT / "lib" / "field-antivirus-network-defender.py",
                    ["status"],
                ),
                "/api/antivirus": (
                    INSTALL_ROOT / "lib" / "field-antivirus-network-defender.py",
                    ["status"],
                ),
            }
            py, args = py_map[path]
            # Prefer cached panel when available for speed
            cache_map = {
                "/api/field-botnet-dns-dhcp": STATE_DIR / "field-botnet-dns-dhcp-panel.json",
                "/api/field-botnet-registry": STATE_DIR / "field-botnet-registry-panel.json",
                "/api/field-dhcp": STATE_DIR / "field-dhcp-panel.json",
                "/api/field-ammonet-lease-takeover": STATE_DIR / "field-ammonet-lease-takeover-panel.json",
                "/api/field-friendly-secure-serve": STATE_DIR / "field-friendly-secure-serve-panel.json",
                "/api/field-planetary-dns-dhcp": STATE_DIR / "field-planetary-dns-dhcp-panel.json",
                "/api/field-serving-truth": STATE_DIR / "field-serving-truth-panel.json",
                "/api/field-registry-h7-bsp": STATE_DIR / "field-registry-h7-bsp-panel.json",
                "/api/field-fleet-faster-servers": STATE_DIR / "field-fleet-faster-servers-panel.json",
                "/api/field-botnet-full-dns-dhcp-authority": STATE_DIR / "field-botnet-full-dns-dhcp-authority-panel.json",
                "/api/field-internet-big-numbers": STATE_DIR / "field-internet-big-numbers-panel.json",
                "/api/field-serving-capacity": STATE_DIR / "field-serving-capacity-panel.json",
                "/api/field-authority-capacity": STATE_DIR / "field-authority-capacity-panel.json",
                "/api/field-world-ip-lease-sole": STATE_DIR / "field-world-ip-lease-sole-panel.json",
                "/api/field-comms-saw-secure-lines": STATE_DIR / "field-comms-saw-secure-lines-panel.json",
                "/api/field-fleet-live": STATE_DIR / "field-fleet-live-panel.json",
                "/api/field-botnet-threat-heuristics": STATE_DIR / "field-botnet-threat-heuristics-panel.json",
                "/api/field-udp-outlet-rehit-old": STATE_DIR / "field-udp-outlet-rehit-old-panel.json",
                "/api/field-antivirus-network-defender": STATE_DIR / "field-antivirus-network-defender-panel.json",
                "/api/antivirus": STATE_DIR / "field-antivirus-network-defender-panel.json",
            }
            cached = cache_map.get(path)
            if cached and cached.is_file() and path.endswith("/keepalive") is False:
                try:
                    payload = json.loads(cached.read_text(encoding="utf-8"))
                    payload = dict(payload)
                    payload["_operator_api"] = True
                    payload["_password"] = "blank_or_mememe"
                    self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                    return
                except (OSError, json.JSONDecodeError):
                    pass
            payload = _nexus_py_json(py, args, timeout=30) if py.is_file() else {"ok": False, "error": "missing"}
            if isinstance(payload, dict):
                payload = dict(payload)
                payload["_operator_api"] = True
                payload["_password"] = "blank_or_mememe"
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return
        # False prophets destroy — read-only status before ironclad (celebrate companion)
        if path in (
            "/api/field-false-prophets-destroy",
            "/api/false-prophets",
            "/api/false-prophets-destroy",
        ):
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-false-prophets-destroy.py",
                ["status"],
                timeout=10,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return
        if path.startswith("/api/") and not self._ironclad_api_gate(path, "GET"):
            return
        query = parse_qs(urlparse(self.path).query)

        if path in ("/api/root-status", "/api/field-root-status"):
            fmt = str(query.get("fmt", [""])[0]).strip().lower()
            accept = (self.headers.get("Accept") or "").lower()
            rs_py = INSTALL_ROOT / "lib" / "field-root-status.py"
            if fmt == "telnet" or "text/plain" in accept:
                body = _nexus_py_text(rs_py, ["telnet"], timeout=8) if rs_py.is_file() else "FIELD ROOT STATUS unavailable\n"
                self._send(200, body, "text/plain; charset=utf-8")
                return
            payload = _nexus_py_json(rs_py, ["json"], timeout=8) if rs_py.is_file() else {"ok": False, "error": "field_root_status_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/status":
            full = str(query.get("full", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            self._send(200, _read_status_json(full=full), "application/json")
            return

        if path == "/api/nexus-field":
            try:
                store_ready = STATUS_JSON.is_file() and STATUS_JSON.stat().st_size >= 128
            except OSError:
                store_ready = False
            if not store_ready:
                _nexus_shell_publish_panel()
            self._send(200, _read_status_json(full=True), "application/json")
            return

        if path == "/api/threat-panel.json":
            if STATUS_JSON.is_file():
                self._send(200, STATUS_JSON.read_text(encoding="utf-8"), "application/json")
            else:
                self._send(200, "{}", "application/json")
            return

        if path == "/api/gatekeeper":
            payload = _panel_slice(
                "gatekeeper",
                live=_read_state_json(
                    "connection-intent.json",
                    {"connections": [], "harm_candidates": 0, "why_no_auto_block": "No live flows cataloged yet."},
                ),
                default={"connections": [], "harm_candidates": 0},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/host-attacks":
            payload = _panel_slice(
                "host_attacks",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "host-attack-map.py", ["json-panel"]),
                default={"schema": "host-attacks/v1", "points": [], "updated": None, "stats": {"total": 0}},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/us-field":
            payload = _panel_slice(
                "us_field",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-us-intel.py", ["json"]),
                default={"title": "US Field", "page": {}},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path in ("/api/us-obs-field", "/api/us-broadcaster-field"):
            script = INSTALL_ROOT / "lib" / "field-broadcaster.py"
            if not script.is_file():
                script = INSTALL_ROOT / "lib" / "field-obs.py"
            if script.is_file():
                cmd = "us" if script.name == "field-obs.py" else "us"
                payload = _nexus_py_json(script, [cmd], timeout=45)
            else:
                payload = {"schema": "us-broadcaster-field/v1", "ok": False, "error": "broadcaster_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-final-eye-canvas"):
            canvas_py = INSTALL_ROOT / "lib" / "field-final-eye-canvas-bridge.py"
            sub = path[len("/api/field-final-eye-canvas"):].strip("/")
            if not canvas_py.is_file():
                payload = {"ok": False, "error": "canvas_bridge_missing"}
            elif sub in ("", "status", "json", "posture", "panel"):
                payload = _nexus_py_json(canvas_py, ["json"], timeout=30)
            elif sub == "feed":
                payload = _nexus_py_json(canvas_py, ["feed"], timeout=30)
            elif sub == "connect":
                payload = _nexus_py_json(canvas_py, ["connect"], timeout=45)
            else:
                payload = {"ok": False, "error": "unknown_canvas_action", "sub": sub}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        chamber_py = INSTALL_ROOT / "lib" / "field-broadcaster-chamber.py"
        if path.startswith("/api/field-broadcaster"):
            sub = path[len("/api/field-broadcaster"):].strip("/")
            if sub == "audio":
                script = INSTALL_ROOT / "lib" / "field-broadcaster-audio.py"
                if script.is_file():
                    payload = _nexus_py_json(script, ["json"], timeout=30)
                else:
                    payload = {"schema": "field-broadcaster-audio/v1", "ok": False, "error": "broadcaster_audio_missing"}
            elif sub in ("chamber", "chamber/status", "chamber/json", "chamber/panel"):
                if chamber_py.is_file():
                    cmd = "panel" if sub.endswith("/panel") else "json"
                    payload = _nexus_py_json(chamber_py, [cmd], timeout=45)
                else:
                    payload = {"schema": "field-broadcaster-chamber-panel/v1", "ok": False, "error": "broadcaster_chamber_missing"}
            elif sub == "platforms":
                payload = (
                    _nexus_py_json(chamber_py, ["platforms"], timeout=30)
                    if chamber_py.is_file()
                    else {"ok": False, "error": "broadcaster_chamber_missing"}
                )
            elif sub == "codecs":
                payload = (
                    _nexus_py_json(chamber_py, ["codecs"], timeout=30)
                    if chamber_py.is_file()
                    else {"ok": False, "error": "broadcaster_chamber_missing"}
                )
            elif sub in ("final-eye", "final_eye"):
                payload = (
                    _field_broadcaster_chamber_dispatch({"action": "final_eye"}, timeout=30)
                    if chamber_py.is_file()
                    else {"ok": False, "error": "broadcaster_chamber_missing"}
                )
            elif sub == "studio":
                studio_py = INSTALL_ROOT / "lib" / "field-broadcaster-studio.py"
                payload = (
                    _nexus_py_json(studio_py, ["json"], timeout=45)
                    if studio_py.is_file()
                    else {"ok": False, "error": "studio_missing"}
                )
            elif sub in ("", "status", "json"):
                script = INSTALL_ROOT / "lib" / "field-broadcaster.py"
                if script.is_file():
                    payload = _nexus_py_json(script, ["json"], timeout=45)
                else:
                    payload = {"schema": "field-broadcaster/v1", "ok": False, "error": "broadcaster_missing"}
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_broadcaster_route", "sub": sub}), "application/json")
                return
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/obs-threat-posterity":
            payload = _panel_slice(
                "obs_threat_posterity",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "obs-threat-posterity-bridge.py", ["json"]),
                default={"schema": "obs-threat-posterity/v1", "live": False},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/obs-threat-ledger":
            tail = 50
            qs = urlparse(self.path).query
            if qs:
                for part in qs.split("&"):
                    if part.startswith("tail="):
                        try:
                            tail = max(1, min(200, int(part.split("=", 1)[1])))
                        except ValueError:
                            pass
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "obs-threat-posterity-bridge.py",
                ["ledger", str(tail)],
            )
            self._send(200, json.dumps(payload or {"schema": "obs-threat-ledger/v1", "rows": []}), "application/json")
            return

        if path == "/api/voltage-regulation":
            payload = _panel_slice(
                "field_voltage_regulation",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-voltage-regulation.py", ["json"]),
                default={"schema": "field-voltage-regulation/v1", "ok": False},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/us-voltage-regulation":
            payload = _panel_slice(
                "us_voltage_regulation",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-voltage-regulation.py", ["us"]),
                default={"schema": "us-voltage-regulation/v1"},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-command":
            payload = _panel_slice(
                "field_command",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-command.py", ["json"]),
                default={"good_guy": {"count": 0}, "bad_guy": {"count": 0}, "pulse": {}},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/packet-field":
            payload = _panel_slice(
                "packet_field",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "packet-field.py", ["json"]),
                default={"recent": [], "ports": [], "field_graphics": {}},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/port-ddos":
            payload = _panel_slice(
                "port_ddos_shield",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-port-ddos-shield.py", ["json"]),
                default={"verdict": "GREEN", "ports": [], "wifi": [], "wave_view": {}},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/port-ddos/cycle":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-port-ddos-shield.py", ["cycle"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/packet-deinterlace":
            payload = _panel_slice(
                "packet_deinterlace",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-packet-deinterlace.py", ["json"]),
                default={"lanes": [], "processed": 0, "secure": 0},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/packet-deinterlace/cycle":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-packet-deinterlace.py", ["cycle"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/connectivity-laws":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-packet-deinterlace.py", ["laws"], timeout=15)
            self._send(200, json.dumps(payload or {"laws": []}), "application/json")
            return

        if path == "/api/angel-dossiers":
            payload = _read_state_json(
                "angel-dossiers.json",
                {"dossier_count": 0, "dossiers": [], "motto": "Let's Be Angels"},
            )
            if not payload.get("dossiers"):
                built = _nexus_py_json(INSTALL_ROOT / "lib" / "angel-dossier.py", ["dossiers"], timeout=45)
                if built:
                    payload = built
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/angel-research":
            payload = _read_state_json(
                "angel-research.json",
                {"tables": {"mac_vendors": [], "ip_intel": [], "exploit_cve_map": [], "attack_paths": []}},
            )
            if not payload.get("tables"):
                built = _nexus_py_json(INSTALL_ROOT / "lib" / "angel-dossier.py", ["research"], timeout=45)
                if built:
                    payload = built
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/human-dossier":
            fp = DATA_FILES.get("human-dossier")
            if fp and fp.is_file():
                self._send(200, fp.read_text(encoding="utf-8"), "application/json")
                return
            payload = _nexus_shell_json_fn(
                "nexus_human_dossier_json",
                sources=["human-dossier.sh"],
            )
            if not payload:
                payload = {"dossier_version": "7.0", "ip_count": 0, "ips": [], "analyst": "Grok Heavy"}
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/settings":
            payload = _panel_slice(
                "settings",
                live=_nexus_shell_json_fn("nexus_settings_json", sources=["nexus-settings.sh"]),
                default={},
            )
            self._send(200, json.dumps(payload or {}), "application/json")
            return

        if path == "/api/nexus/catalog":
            script = INSTALL_ROOT / "lib" / "nexus-file-catalog.py"
            catalog_fp = INSTALL_ROOT / "data" / "nexus-file-catalog.json"
            summary = str(query.get("summary", ["0"])[0]).strip() in ("1", "true", "yes")
            refresh = str(query.get("refresh", ["0"])[0]).strip() in ("1", "true", "yes")
            if not script.is_file():
                self._send(500, json.dumps({"ok": False, "error": "catalog_script_missing"}), "application/json")
                return
            if summary:
                proc = subprocess.run(
                    [sys.executable, str(script), "stats"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL_ROOT), "NEXUS_STATE_DIR": str(STATE_DIR)},
                )
                try:
                    payload = json.loads(proc.stdout or "{}")
                    payload["ok"] = True
                except json.JSONDecodeError:
                    payload = {"ok": False, "error": "catalog_failed", "stderr": (proc.stderr or "")[:400]}
                self._send(200 if payload.get("ok") else 500, json.dumps(payload), "application/json")
                return
            if refresh or not catalog_fp.is_file():
                proc = subprocess.run(
                    [sys.executable, str(script), "build", str(catalog_fp)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL_ROOT), "NEXUS_STATE_DIR": str(STATE_DIR)},
                )
                if proc.returncode != 0 and not catalog_fp.is_file():
                    self._send(500, json.dumps({"ok": False, "error": "catalog_build_failed"}), "application/json")
                    return
            try:
                payload = json.loads(catalog_fp.read_text(encoding="utf-8"))
                payload["ok"] = True
            except (OSError, json.JSONDecodeError):
                payload = {"ok": False, "error": "catalog_read_failed"}
            self._send(200 if payload.get("ok") else 500, json.dumps(payload), "application/json")
            return

        if path in ("/api/ammoos-update/check", "/api/ammoos-update/status"):
            force = str(query.get("force", ["0"])[0]).strip() in ("1", "true", "yes")
            payload = _ammoos_update_check(force=force)
            lock = _nexus_update_lock(["status"])
            payload["update_lock"] = lock
            payload["update_in_progress"] = bool(lock.get("locked"))
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/ammoos-update/doctrine":
            payload = _ammoos_update_doctrine()
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/ammoos-update/components":
            script = INSTALL_ROOT / "lib" / "ammoos-update-inplace.py"
            force = str(query.get("force", ["0"])[0]).strip() in ("1", "true", "yes")
            payload = _nexus_py_json(script, ["components"] + (["--force"] if force else []), timeout=45)
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/ammoos-update/preflight":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "ammoos-update-inplace.py", ["preflight"], timeout=30)
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/ammoos-update/log":
            lines = str(query.get("lines", ["80"])[0]).strip() or "80"
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "ammoos-update-inplace.py",
                ["log", f"--lines={lines}"],
                timeout=15,
            )
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/ammoos-incorporate/check", "/api/ammoos-incorporate/status"):
            payload = _ammoos_incorporate_posture()
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/ammoos-incorporate/doctrine":
            payload = _ammoos_incorporate_doctrine()
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/ammoos-startup/posture", "/api/ammoos-startup/status", "/api/ammoos-startup/check"):
            payload = _ammoos_startup_posture()
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/ammoos-startup/doctrine":
            payload = _ammoos_startup_doctrine()
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/nexus-c2/snapshot", "/api/nexus-c2/status", "/api/nexus-c2/check"):
            tier = str(query.get("tier", ["hot"])[0]).strip() or "hot"
            payload = _nexus_c2_snapshot(tier=tier)
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/nexus-c2/posture":
            payload = _nexus_c2_posture()
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/nexus-c2/doctrine":
            payload = _nexus_c2_doctrine()
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/ammoos-themes":
            script = INSTALL_ROOT / "lib" / "ammoos-theme-engine.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["catalog"], timeout=15)
            else:
                payload = {"ok": False, "error": "ammoos_theme_engine_missing"}
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/ammoos-themes/default":
            script = INSTALL_ROOT / "lib" / "ammoos-theme-engine.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["default"], timeout=15)
            else:
                payload = {"ok": False, "error": "ammoos_theme_engine_missing"}
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/update/check", "/api/update/status"):
            force = str(query.get("force", ["0"])[0]).strip() in ("1", "true", "yes")
            payload = _nexus_update_check(force=force)
            lock = _nexus_update_lock(["status"])
            payload["update_lock"] = lock
            payload["update_in_progress"] = bool(lock.get("locked"))
            needs_sudo = _nexus_update_needs_sudo()
            if needs_sudo:
                payload["needs_sudo"] = True
                payload["sudo_prompt"] = needs_sudo
            if lock.get("locked"):
                payload["update_available"] = False
                payload["message"] = lock.get("message") or "Update in progress"
            elif needs_sudo:
                payload["message"] = needs_sudo.get("message") or "Administrator password required"
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-toolkit":
            attack_id = str(query.get("id", [""])[0]).strip()
            script = INSTALL_ROOT / "lib" / "field-toolkit-db.py"
            if attack_id:
                payload = _nexus_py_json(script, ["get", attack_id])
            else:
                payload = _nexus_py_json(script, ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/hostile-ai":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostile-ai-destroy.py", ["json"], timeout=45)
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/planetary-observer":
            payload = _panel_slice(
                "planetary_observer",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "planetary-observer.py", ["json"], timeout=60),
                default={"schema": "planetary-observer/v1", "globe": {"total_targets": 0}, "wire": {}},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/operator/location":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "operator-location.py", ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/honorability":
            payload = _panel_slice(
                "browser_awareness",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "browser-awareness.py", ["json"]),
                default={"honorability": {}, "active_sites": []},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/queen-browser":
            payload = _panel_slice(
                "field_queen_browser",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-queen-browser.py", ["json"]),
                default={"queen_verdict": "QUEEN_WARMING", "gates": {"all_held": True}},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/logic-gate":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "nexus-logic-gate.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/queen/root-threats":
            qr = _queen_root()
            script = qr / "lib" / "queen-root-threats.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=20)
            else:
                payload = {"ok": False, "error": "queen_root_threats_missing"}
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-stack":
            payload = _panel_slice(
                "field_stack",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "queen_field_nexus.py", ["json"], timeout=120),
                default={"schema": "nexus-field-stack/v1", "queen_verdict": "QUEEN_WARMING"},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path in ("/api/field-sovereign-stack-meld", "/api/field-sovereign-stack-meld/panel"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-sovereign-stack-meld.py", ["panel"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-stack-layer":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-stack-layer.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-thermal-guard":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-thermal-guard.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/thermal-governor":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "thermal-governor.py", ["json"], timeout=15)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-thermal-manager-block", "/api/thermal-manager-block"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-thermal-manager-block.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-rtx-canvas-block", "/api/rtx-canvas-block"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-rtx-canvas-block.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-final-ear-block", "/api/final-ear-block"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-final-ear-block.py", ["json"], timeout=45)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-final-mouth-block", "/api/final-mouth-block"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-final-mouth-block.py", ["json"], timeout=45)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-final-eye-block", "/api/final-eye-block"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-final-eye-block.py", ["json"], timeout=90)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/queen-canvas-renderer", "/api/field-rtx-display"):
            canvas_script = None
            for candidate in (
                INSTALL_ROOT.parent / "Queen" / "lib" / "queen-canvas-renderer.py",
                INSTALL_ROOT.parent / "NewLatest" / "Queen" / "lib" / "queen-canvas-renderer.py",
                INSTALL_ROOT / "Queen" / "lib" / "queen-canvas-renderer.py",
            ):
                if candidate.is_file():
                    canvas_script = candidate
                    break
            if canvas_script:
                payload = _nexus_py_json(canvas_script, ["json"], timeout=25)
            else:
                payload = {"ok": False, "error": "queen_canvas_renderer_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/admin-shield":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "admin-window-shield.py", ["json"], timeout=20)
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/hardware-wire":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hardware-wire.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/smart-wire":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "smart-wire.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-clipboard":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-clipboard-wire.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-filetypes/media", "/api/field-filetypes/media/"):
            script = INSTALL_ROOT / "lib" / "field-programming-filetypes.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["media"], timeout=30)
            else:
                payload = {"ok": False, "error": "field_programming_filetypes_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-clipboard/media"):
            import re as _re

            media_id = str(query.get("id", [""])[0]).strip()
            safe = _re.sub(r"[^a-zA-Z0-9_-]", "", media_id)[:64]
            if not safe:
                self._send(400, b"id_required", "text/plain")
                return
            index_path = STATE_DIR / "field-clipboard-media-index.json"
            media_path = STATE_DIR / "field-clipboard-media" / f"{safe}.bin"
            mime = "application/octet-stream"
            try:
                if index_path.is_file():
                    idx = json.loads(index_path.read_text(encoding="utf-8"))
                    row = next((e for e in (idx.get("entries") or []) if e.get("id") == safe), None)
                    if row:
                        mime = str(row.get("mime") or mime)
                if media_path.is_file():
                    blob = media_path.read_bytes()
                    self._send(200, blob, mime)
                    return
            except (OSError, json.JSONDecodeError):
                pass
            self._send(404, b"media_not_found", "text/plain")
            return

        if path == "/api/front-hook":
            hook_file = STATE_DIR / "front-hook.json"
            if hook_file.is_file():
                try:
                    self._send(200, hook_file.read_text(encoding="utf-8"), "application/json")
                    return
                except OSError:
                    pass
            self._send(
                200,
                json.dumps({
                    "schema": "nexus-front-hook/v1",
                    "boarded": False,
                    "owner": "nexus",
                    "pass_through": False,
                    "policy": "front_hook_never_pass_off",
                }),
                "application/json",
            )
            return

        if path == "/api/ai-integration":
            peer = self.client_address[0] if self.client_address else "127.0.0.1"
            payload = _ai_integration_json(peer=str(peer))
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/native-layer":
            query = parse_qs(urlparse(self.path).query)
            audit = str(query.get("audit", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            payload = _native_layer_json(audit=audit)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/cpu-vulnerability":
            query = parse_qs(urlparse(self.path).query)
            apply = str(query.get("apply", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            payload = _cpu_vulnerability_json(apply=apply)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-polkit":
            payload = _field_polkit_json()
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-underlay":
            payload = _field_underlay_json()
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-operator":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-operator.py",
                ["board", "--no-hw-wire"],
                timeout=15,
            )
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-operator/scan":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-operator.py", ["scan"], timeout=10)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-operator/clock":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-operator.py", ["clock"], timeout=8)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-operator/route":
            query = parse_qs(urlparse(self.path).query)
            target = str(query.get("id") or query.get("target") or [""])[0].strip()
            if not target:
                self._send(400, json.dumps({"ok": False, "error": "missing id"}), "application/json")
                return
            payload = _field_operator_hot_route(target)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-operator/hot-route":
            payload = _field_operator_hot_route_status()
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-bus":
            payload = _panel_slice(
                "field_bus",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-unified-bus.py", ["json"]),
                default={"bus_size": 64, "data_bus": [], "lanes": []},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-bus/cycle":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-unified-bus.py", ["cycle"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-bus/hot-route":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-unified-bus.py", ["hot-route"], timeout=15)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/universal-protector", "/api/universal-protector/status"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "universal-protector.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/compile-autocorrect"):
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-compile-autocorrect.py",
                ["emulator-series"],
                timeout=20,
            ) or {}
            self._send(200, json.dumps({
                "schema": "field-compile-autocorrect/v1",
                "ok": True,
                "doctrine": "data/field-compile-autocorrect-doctrine.json",
                "human_explanations": "data/compile-error-human-explanations.json",
                "module": "lib/field-compile-autocorrect.py",
                "policy": "confidence 1.0 only — never guess",
                "collect_all_errors": True,
                "human_explanation_at_end": True,
                "emulator_series": payload,
            }, ensure_ascii=False), "application/json")
            return

        if path == "/api/universal-protector/meld":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "universal-protector.py", ["meld"], timeout=90)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-spatial", "/api/spatial-field"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-spatial-cognition.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-device-map", "/api/device-map"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-device-map.py", ["json"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-world-dns-dhcp-scale", "/api/world-dns-dhcp-scale"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-world-dns-dhcp-scale.py", ["json"], timeout=20)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/field-never-down",
            "/api/field-never-down/instantiate",
            "/api/field-never-down/ensure",
            "/api/never-down",
        ):
            # Root HTTP is status-only — never spawn PIDs from panel/API.
            if path.endswith(("/instantiate", "/ensure")) or str(query.get("spawn", ["0"])[0]).strip().lower() in ("1", "true", "yes"):
                self._send(403, json.dumps({
                    "ok": False,
                    "error": "spawn_forbidden_on_http",
                    "motto": "Use Hostess7 CLI — root is status only",
                    "cli": "./Hostess7.sh never-down instantiate",
                }, ensure_ascii=False), "application/json")
                return
            panel_path = STATE_DIR / "field-never-down-panel.json"
            payload = None
            if panel_path.is_file():
                try:
                    payload = json.loads(panel_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    payload = None
            if payload is None:
                payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-never-down.py", ["json"], timeout=12)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-one", "/api/field-one/absorb", "/api/field1"):
            cmd = "absorb" if path.endswith("/absorb") else "json"
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-one.py", [cmd], timeout=180)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-one-rollout", "/api/field-one-rollout/test"):
            cmd = "test" if path.endswith("/test") else "json"
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-one-rollout.py", [cmd], timeout=180)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-one-rollout/rollout",):
            batch = str(query.get("batch", ["10"])[0])
            args = ["rollout", batch] if batch.isdigit() else ["rollout"]
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-one-rollout.py", args, timeout=300)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-one-rollout/double",):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-one-rollout.py", ["double"], timeout=300)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-sovereign-ipv4-enforce", "/api/field-sovereign-ipv4"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-sovereign-ipv4-enforce.py", ["enforce"], timeout=240)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-rescue-ingress", "/api/rescue-ingress"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib/field-rescue-ingress.py", ["rescue"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        # FIELD ONE ETERNAL PLANE — all lanes always clean · nobody plays fields
        if path in (
            "/api/field-one-eternal-plane",
            "/api/field-one-eternal-plane/",
            "/api/eternal-plane",
            "/api/eternal-plane/",
            "/api/field-one-eternal",
        ):
            try:
                cached = STATE_DIR / "field-one-eternal-plane-panel.json"
                qs_ep = parse_qs(urlparse(self.path).query)
                force = str(qs_ep.get("refresh", qs_ep.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "enforce", "eternal", "brutal",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            payload["eternal_plane"] = True
                            payload["field_one_only"] = True
                            payload["nobody_plays_fields"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-one-eternal-plane.py",
                    ["enforce"] if force else ["status"],
                    timeout=420 if force else 30,
                )
                if not isinstance(payload, dict):
                    payload = {"ok": False, "error": "eternal_plane_bad"}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # No detached/adjacent fields · Field One only · Big Grin kicks · Earth stabilize
        if path in (
            "/api/no-detached-fields",
            "/api/no-detached-fields/",
            "/api/field-no-detached-fields",
            "/api/field-no-detached-fields/",
            "/api/field-one-no-gaps",
            "/api/earth-stabilize",
        ):
            try:
                cached = STATE_DIR / "field-no-detached-fields-panel.json"
                qs_nd = parse_qs(urlparse(self.path).query)
                force = str(qs_nd.get("refresh", qs_nd.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "enforce", "close", "stabilize",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            payload["field_one_only"] = True
                            payload["earth_stabilized"] = True
                            payload["no_fields_next_to_known_devices"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-no-detached-fields.py",
                    ["enforce"] if force else ["status"],
                    timeout=300 if force else 30,
                )
                if not isinstance(payload, dict):
                    payload = {"ok": False, "error": "no_detached_fields_bad"}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # Newcomer immediate-attack sphere destroy — full volts · vector melt · forever
        if path in (
            "/api/newcomer-sphere-destroy",
            "/api/newcomer-sphere-destroy/",
            "/api/newcomer-sphere",
            "/api/newcomer-sphere/",
            "/api/sphere-destroy",
            "/api/no-machine-again",
        ):
            try:
                cached = STATE_DIR / "field-newcomer-attack-sphere-destroy-panel.json"
                qs_ns = parse_qs(urlparse(self.path).query)
                force = str(qs_ns.get("refresh", qs_ns.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "enforce", "melt", "sphere", "blast",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            payload["lethal_no_machine_again"] = True
                            payload["no_storm_propagate"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-newcomer-attack-sphere-destroy.py",
                    ["enforce"] if force else ["status"],
                    timeout=240 if force else 30,
                )
                if not isinstance(payload, dict):
                    payload = {"ok": False, "error": "newcomer_sphere_bad"}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # Hostess7 sole Earth protector — trained · world ISP · Gladstone · BLAST foreign
        if path in (
            "/api/hostess7-sole-earth-protector",
            "/api/hostess7-sole-earth-protector/",
            "/api/hostess7-protector",
            "/api/hostess7-protector/",
            "/api/sole-earth-protector",
            "/api/gladstone-protect",
        ):
            try:
                cached = STATE_DIR / "hostess7-sole-earth-protector-panel.json"
                qs_h7p = parse_qs(urlparse(self.path).query)
                force = str(qs_h7p.get("refresh", qs_h7p.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "enforce", "lock", "protect", "blast",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            payload["hostess7_trained"] = True
                            payload["sole_earth_protector"] = True
                            payload["gladstone_protected"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "hostess7-sole-earth-protector.py",
                    ["enforce"] if force else ["status"],
                    timeout=300 if force else 30,
                )
                if not isinstance(payload, dict):
                    payload = {"ok": False, "error": "hostess7_protector_bad"}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # Field One only internet — outside = Field One · only internet left · Grok cool
        if path in (
            "/api/field-one-only-internet",
            "/api/field-one-only-internet/",
            "/api/only-internet",
            "/api/only-internet/",
            "/api/field-only-internet",
            "/api/outside-field-one",
        ):
            try:
                cached = STATE_DIR / "field-one-only-internet-panel.json"
                qs_oi = parse_qs(urlparse(self.path).query)
                force = str(qs_oi.get("refresh", qs_oi.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "enforce", "lock", "outside",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            payload["outside_is_field_one"] = True
                            payload["only_internet_left"] = True
                            payload["because_grok_is_cool"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-one-only-internet.py",
                    ["enforce"] if force else ["status"],
                    timeout=240 if force else 30,
                )
                if not isinstance(payload, dict):
                    payload = {"ok": False, "error": "field_one_only_internet_bad"}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # Field One sole earth — only Field One · KILROY pull · destroy other fields
        if path in (
            "/api/field-one-sole-earth",
            "/api/field-one-sole-earth/",
            "/api/field-one-sole",
            "/api/field-one-sole/",
            "/api/no-other-fields",
        ):
            try:
                cached = STATE_DIR / "field-one-sole-earth-panel.json"
                qs_f1 = parse_qs(urlparse(self.path).query)
                force = str(qs_f1.get("refresh", qs_f1.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "enforce", "lock",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            payload["field_one_only"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-one-sole-earth.py",
                    ["enforce"] if force else ["status"],
                    timeout=180 if force else 30,
                )
                if not isinstance(payload, dict):
                    payload = {"ok": False, "error": "field_one_sole_bad"}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # Hardened OURS plane — GitHub heuristics · plate+meld · read-only autopilot · local site
        if path in (
            "/api/field-hardened-ours-plane",
            "/api/field-hardened-ours-plane/",
            "/api/hardened-ours",
            "/api/hardened-ours/",
            "/api/ours-hardened",
        ):
            try:
                cached = STATE_DIR / "field-hardened-ours-plane-panel.json"
                qs_ho = parse_qs(urlparse(self.path).query)
                force = str(qs_ho.get("refresh", qs_ho.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "harden", "lock",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            payload["read_only"] = True
                            payload["autopilot"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-hardened-ours-plane.py",
                    ["harden"] if force else ["status"],
                    timeout=180 if force else 30,
                )
                if not isinstance(payload, dict):
                    payload = {"ok": False, "error": "hardened_ours_bad"}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # Whole planet LIVE honest — match planet for real straight away
        if path in (
            "/api/field-whole-planet-live",
            "/api/field-whole-planet-live/",
            "/api/whole-planet-live",
            "/api/whole-planet-live/",
            "/api/live-honest-planet",
        ):
            try:
                cached = STATE_DIR / "field-whole-planet-live-panel.json"
                qs_wp = parse_qs(urlparse(self.path).query)
                force = str(qs_wp.get("refresh", qs_wp.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "seal",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-whole-planet-live.py",
                    ["seal"] if force else ["status"],
                    timeout=60 if force else 20,
                )
                if not isinstance(payload, dict):
                    payload = {"ok": False, "error": "whole_planet_live_bad"}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        # Planetary rescue — whole world · more waves
        if path in (
            "/api/field-planetary-rescue",
            "/api/field-planetary-rescue/",
            "/api/planetary-rescue",
            "/api/planetary-rescue/",
            "/api/world-rescue",
            "/api/rescue-more",
        ):
            try:
                cached = STATE_DIR / "field-planetary-rescue-panel.json"
                qs_pr = parse_qs(urlparse(self.path).query)
                force = str(qs_pr.get("refresh", qs_pr.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "more", "world",
                )
                mode = str(qs_pr.get("mode", ["status"])[0]).strip().lower()
                if cached.is_file() and not force and mode in ("", "status", "panel", "json", "0"):
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                args = ["status"]
                if force or mode in ("more", "world", "rescue", "run"):
                    args = ["more"] if mode == "more" or path.endswith("rescue-more") else ["world"]
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-planetary-rescue.py",
                    args,
                    timeout=180 if args[0] != "status" else 30,
                )
                if not isinstance(payload, dict):
                    payload = {"ok": False, "error": "planetary_rescue_bad"}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return

        if path in ("/api/field-truth-keepalive", "/api/truth-keepalive"):
            tk_py = INSTALL_ROOT / "lib" / "field-truth-keepalive.py"
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            args = ["keepalive"] if refresh else ["json"]
            payload = _nexus_py_json(tk_py, args, timeout=240) if tk_py.is_file() else {"ok": False, "error": "field_truth_keepalive_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-grow-watch", "/api/grow-watch"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib/field-grow-watch.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/field-watch-dhcp",
            "/api/field-watch-dhcp/ensure",
            "/api/dhcp-watch",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            watch_py = INSTALL_ROOT / "lib" / "field-watch-dhcp.py"
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "field-watch-dhcp-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if path.endswith("/ensure"):
                self._send(403, json.dumps({
                    "ok": False,
                    "error": "spawn_forbidden_on_http",
                    "motto": "DHCP watch is observe-only — use Hostess7 CLI to ensure",
                    "cli": "./Hostess7.sh field-watch-dhcp ensure",
                }, ensure_ascii=False), "application/json")
                return
            if payload is None or refresh:
                args = ["once"] if refresh else ["json"]
                payload = _nexus_py_json(watch_py, args, timeout=30 if refresh else 15)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-sub-micron-timing", "/api/sub-micron-timing", "/api/sub-micron"):
            sm_py = INSTALL_ROOT / "lib" / "field-sub-micron-timing.py"
            args = ["run"] if path.endswith("/run") or (self.headers.get("X-Sub-Micron-Run") or "").strip() in ("1", "yes") else ["json"]
            payload = _nexus_py_json(sm_py, args, timeout=90) if sm_py.is_file() else {"ok": False, "error": "field_sub_micron_timing_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-rack-uniqueness", "/api/field-rack", "/api/rack-uniqueness"):
            rack_py = INSTALL_ROOT / "lib" / "field-rack-uniqueness.py"
            sub = path.split("/")[-1] if path.count("/") > 3 else ""
            args = ["publish"] if sub in ("publish", "whole", "provision") else ["json"]
            if sub in ("assert", "solo", "lease"):
                args = ["assert"]
            payload = _nexus_py_json(rack_py, args, timeout=180) if rack_py.is_file() else {"ok": False, "error": "field_rack_uniqueness_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-github-isolation", "/api/github-isolation"):
            iso_py = INSTALL_ROOT / "lib" / "field-github-isolation.py"
            sub = path.replace("/api/field-github-isolation", "").replace("/api/github-isolation", "").strip("/")
            args = ["isolate"] if sub in ("isolate", "apply", "world") else ["json"]
            if (self.headers.get("X-Github-Mirror-Push") or "").strip().lower() in ("1", "yes", "on"):
                args.append("--push-github")
            payload = _nexus_py_json(iso_py, args, timeout=120) if iso_py.is_file() else {"ok": False, "error": "field_github_isolation_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-global-servers") or path.startswith("/api/global-servers"):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            sub = path.replace("/api/field-global-servers", "").replace("/api/global-servers", "").strip("/")
            gs_py = INSTALL_ROOT / "lib" / "field-global-servers.py"
            args = ["expand", "2500"] if sub in ("expand", "deploy", "2500") else ["probe"] if sub == "probe" else ["json"]
            payload = None
            if not refresh and sub not in ("expand", "deploy", "2500", "probe"):
                panel_path = STATE_DIR / "field-global-servers-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None:
                payload = _nexus_py_json(gs_py, args, timeout=120) if gs_py.is_file() else {"ok": False, "error": "field_global_servers_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/ammodrive-cloud") or path.startswith("/api/field-ammodrive-cloud"):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            sub = path.replace("/api/ammodrive-cloud", "").replace("/api/field-ammodrive-cloud", "").strip("/")
            cloud_py = INSTALL_ROOT / "lib" / "ammodrive-cloud.py"
            args = ["identity"] if sub in ("identity", "id") else ["json"]
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "ammodrive-cloud-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None:
                payload = _nexus_py_json(cloud_py, args, timeout=60) if cloud_py.is_file() else {"ok": False, "error": "ammodrive_cloud_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-fleet-2500-protect") or path.startswith("/api/fleet-2500"):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            sub = path.replace("/api/field-fleet-2500-protect", "").replace("/api/fleet-2500", "").strip("/")
            fleet_py = INSTALL_ROOT / "lib" / "field-fleet-2500-protect.py"
            if sub in ("protect", "verify", "run") or path.endswith("/protect"):
                args = ["protect"]
                payload = _nexus_py_json(fleet_py, args, timeout=240) if fleet_py.is_file() else {"ok": False, "error": "fleet_2500_missing"}
            else:
                args = ["json"]
                payload = None
                if not refresh:
                    panel_path = STATE_DIR / "field-fleet-2500-protect-panel.json"
                    if panel_path.is_file():
                        try:
                            payload = json.loads(panel_path.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            payload = None
                if payload is None:
                    payload = _nexus_py_json(fleet_py, args, timeout=60) if fleet_py.is_file() else {"ok": False, "error": "fleet_2500_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-ai-root-api-guard") or path.startswith("/api/ai-root-guard"):
            guard_py = INSTALL_ROOT / "lib" / "field-ai-root-api-guard.py"
            sub = path.replace("/api/field-ai-root-api-guard", "").replace("/api/ai-root-guard", "").strip("/")
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            if sub in ("panel", "posture"):
                args = ["panel"]
            else:
                args = ["json"]
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "field-ai-root-api-guard-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None:
                payload = _nexus_py_json(guard_py, args, timeout=30) if guard_py.is_file() else {"ok": False, "error": "ai_root_guard_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-server-root-login") or path.startswith("/api/root-login"):
            login_py = INSTALL_ROOT / "lib" / "field-server-root-login.py"
            sub = path.replace("/api/field-server-root-login", "").replace("/api/root-login", "").strip("/")
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            if sub in ("install", "greeter", "setup"):
                args = ["install"]
                payload = _nexus_py_json(login_py, args, timeout=60) if login_py.is_file() else {"ok": False, "error": "root_login_missing"}
            else:
                args = ["json"]
                payload = None
                if not refresh:
                    panel_path = STATE_DIR / "field-server-root-login-panel.json"
                    if panel_path.is_file():
                        try:
                            payload = json.loads(panel_path.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            payload = None
                if payload is None:
                    payload = _nexus_py_json(login_py, args, timeout=30) if login_py.is_file() else {"ok": False, "error": "root_login_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-h7r-stack") or path.startswith("/api/h7r-stack"):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            sub = path.replace("/api/field-h7r-stack", "").replace("/api/h7r-stack", "").strip("/")
            stack_py = INSTALL_ROOT / "lib" / "field-h7r-stack.py"
            if sub in ("distribute", "rapid", "upgrade") or path.endswith("/distribute"):
                args = ["distribute"]
                payload = _nexus_py_json(stack_py, args, timeout=180) if stack_py.is_file() else {"ok": False, "error": "field_h7r_stack_missing"}
            elif sub in ("all", "full", "distribute-all"):
                args = ["all"]
                payload = _nexus_py_json(stack_py, args, timeout=240) if stack_py.is_file() else {"ok": False, "error": "field_h7r_stack_missing"}
            else:
                args = ["json"]
                payload = None
                if not refresh:
                    panel_path = STATE_DIR / "field-h7r-stack-panel.json"
                    if panel_path.is_file():
                        try:
                            payload = json.loads(panel_path.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            payload = None
                if payload is None:
                    payload = _nexus_py_json(stack_py, args, timeout=60) if stack_py.is_file() else {"ok": False, "error": "field_h7r_stack_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-zachub-storage") or path.startswith("/api/zachub-storage") or path.startswith("/api/ammodrive-storage"):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            sub = path.replace("/api/field-zachub-storage", "").replace("/api/zachub-storage", "").replace("/api/ammodrive-storage", "").strip("/")
            payload = None if refresh or sub else _read_zachub_panel_cache("storage")
            if payload is None:
                payload = _zachub_storage_api(path, query=query, headers=self.headers)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/field-zachub-fork-guard",
            "/api/zachub-fork-guard",
            "/api/ammodrive-fork-guard",
            "/api/field-zachub-fork-guard/dry",
            "/api/zachub-fork-guard/dry",
            "/api/ammodrive-fork-guard/dry",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            fork_py = INSTALL_ROOT / "lib" / "field-zachub-fork-guard.py"
            if path.endswith("/dry"):
                args = ["dry", "--dry"]
                payload = _nexus_py_json(fork_py, args, timeout=180) if fork_py.is_file() else {"ok": False, "error": "field_zachub_fork_guard_missing"}
            else:
                dry_hdr = (self.headers.get("X-Zachub-Dry") or "").strip().lower()
                if dry_hdr in ("1", "yes", "on"):
                    args = ["dry", "--dry"]
                    payload = _nexus_py_json(fork_py, args, timeout=180) if fork_py.is_file() else {"ok": False, "error": "field_zachub_fork_guard_missing"}
                else:
                    payload = None if refresh else _read_zachub_panel_cache("fork_guard")
                    if payload is None:
                        args = ["guard"]
                        payload = _nexus_py_json(fork_py, args, timeout=180) if fork_py.is_file() else {"ok": False, "error": "field_zachub_fork_guard_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-zachub-qemu-racks") or path.startswith("/api/zachub-qemu-racks") or path.startswith("/api/ammodrive-qemu-racks"):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            sub = path.rstrip("/").split("/")[-1]
            if sub in ("provision", "apply", "burn", "burn-stale", "slots", "map", "convert", "storage-totals", "totals", "redundant"):
                qemu_py = INSTALL_ROOT / "lib" / "field-zachub-qemu-racks.py"
                if sub in ("provision", "apply"):
                    args = ["provision"]
                elif sub in ("burn", "burn-stale"):
                    args = ["burn"]
                elif sub in ("convert", "redundant", "convert-remaining"):
                    args = ["convert"]
                elif sub in ("storage-totals", "totals"):
                    args = ["storage-totals"]
                else:
                    args = ["slots"]
                dry_hdr = (self.headers.get("X-Zachub-Dry") or "").strip().lower()
                if dry_hdr in ("1", "yes", "on") or path.endswith("/dry"):
                    args.append("--dry-run")
                payload = _nexus_py_json(qemu_py, args, timeout=120) if qemu_py.is_file() else {"ok": False, "error": "field_zachub_qemu_racks_missing"}
            else:
                payload = None if refresh else _read_zachub_panel_cache("qemu_racks")
                if payload is None:
                    qemu_py = INSTALL_ROOT / "lib" / "field-zachub-qemu-racks.py"
                    payload = _nexus_py_json(qemu_py, ["json"], timeout=30) if qemu_py.is_file() else {"ok": False, "error": "field_zachub_qemu_racks_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/field-github-planet-sweep",
            "/api/github-planet-sweep",
            "/api/field-github-planet-sweep/refire",
            "/api/github-planet-sweep/refire",
        ):
            if path.endswith("/refire"):
                args = ["refire"]
            else:
                args = ["sweep"]
                if (self.headers.get("X-Field-Fast") or "").strip().lower() in ("1", "yes", "on"):
                    args.append("--fast")
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-github-planet-sweep.py",
                args,
                timeout=180 if path.endswith("/refire") else 90,
            )
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-planetary-dns-dhcp", "/api/planetary-dns-dhcp"):
            cmd = "absorb" if path.endswith("/absorb") else "json"
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-planetary-dns-dhcp.py",
                [cmd],
                timeout=60,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-dns-dhcp-any-ip", "/api/dns-dhcp-any-ip"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-dns-dhcp-any-ip.py", ["json"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in (
            "/api/field-planetary-speed",
            "/api/field-planetary-speed/manage",
            "/api/planetary-speed",
        ):
            cmd = "manage" if path.endswith("/manage") else "json"
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-planetary-speed.py",
                [cmd],
                timeout=120 if cmd == "manage" else 30,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        # H7r capacity fleet — Datacenter bird (GET display)
        if path in (
            "/api/field-h7r-capacity-fleet",
            "/api/field-h7r-capacity-fleet/",
            "/api/h7r-capacity",
            "/api/h7r-capacity-fleet",
        ):
            cached = STATE_DIR / "field-h7r-capacity-fleet-panel.json"
            if cached.is_file():
                try:
                    payload = json.loads(cached.read_text(encoding="utf-8"))
                    self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                    return
                except (OSError, json.JSONDecodeError):
                    pass
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-h7r-capacity-fleet.py",
                ["json"],
                timeout=60,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        # Smart H7r racks — grow capacity as needed (GET display)
        if path in (
            "/api/field-h7r-smart-racks",
            "/api/field-h7r-smart-racks/",
            "/api/h7r-smart-racks",
        ):
            cached = STATE_DIR / "field-h7r-smart-racks-panel.json"
            if cached.is_file():
                try:
                    payload = json.loads(cached.read_text(encoding="utf-8"))
                    self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                    return
                except (OSError, json.JSONDecodeError):
                    pass
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-h7r-smart-racks.py",
                ["json"],
                timeout=90,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        # Internet → Field snapshot (GET display)
        if path in (
            "/api/field-internet-snapshot",
            "/api/field-internet-snapshot/",
            "/api/internet-snapshot",
        ):
            cached = STATE_DIR / "field-internet-snapshot-panel.json"
            if cached.is_file():
                try:
                    payload = json.loads(cached.read_text(encoding="utf-8"))
                    self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                    return
                except (OSError, json.JSONDecodeError):
                    pass
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-internet-snapshot-to-field.py",
                ["json"],
                timeout=120,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        # AmmoNet Cloud — free datacenter everywhere (GET display)
        if path in (
            "/api/field-ammonet-cloud",
            "/api/field-ammonet-cloud/",
            "/api/ammodrive-cloud",
            "/api/ammodrive-cloud/",
            "/api/ammonet-cloud",
            "/api/cloud",
        ):
            for cached_name in ("field-ammonet-cloud-panel.json", "ammodrive-cloud-panel.json"):
                cached = STATE_DIR / cached_name
                if cached.is_file():
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                        return
                    except (OSError, json.JSONDecodeError):
                        pass
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "ammodrive-cloud.py",
                ["json"],
                timeout=45,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        # World Archive — AmmoNet archive.org mirror plane (GET display)
        if path in (
            "/api/field-world-archive",
            "/api/field-world-archive/",
            "/api/world-archive",
            "/api/archive",
        ):
            cached = STATE_DIR / "field-world-archive-panel.json"
            if cached.is_file():
                try:
                    payload = json.loads(cached.read_text(encoding="utf-8"))
                    self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                    return
                except (OSError, json.JSONDecodeError):
                    pass
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-world-archive.py",
                ["status"],
                timeout=60,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        # Field Speedtest — our distributed load panels (GET display; run refreshes panel)
        if path in (
            "/api/field-speedtest",
            "/api/field-speedtest/",
            "/api/speedtest",
            "/api/field-speedtest/run",
            "/api/field-speedtest/location",
        ):
            if path.endswith("/location"):
                cmd = "location"
            elif path.endswith("/run"):
                cmd = "run"
            else:
                # Prefer last panel; if missing, run once
                cached = STATE_DIR / "field-speedtest-panel.json"
                if cached.is_file() and not path.endswith("/run"):
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                        return
                    except (OSError, json.JSONDecodeError):
                        pass
                cmd = "json"
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-speedtest.py",
                [cmd],
                timeout=180 if cmd == "run" else 45,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in (
            "/api/field-internet-unclean-hostile",
            "/api/field-internet-unclean-hostile/fry",
            "/api/internet-unclean-hostile",
        ):
            cmd = "fry" if path.endswith("/fry") else "json"
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-internet-unclean-hostile.py",
                [cmd],
                timeout=60 if cmd == "fry" else 20,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-internet-unrestrict", "/api/field-internet-unrestrict/apply", "/api/internet-unrestrict"):
            cmd = "apply" if path.endswith("/apply") else "json"
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-internet-unrestrict.py",
                [cmd],
                timeout=30 if cmd == "apply" else 15,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-ipv4-arbitrary", "/api/ipv4-arbitrary"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-ipv4-arbitrary.py", ["json"], timeout=15)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-ipv4-enumerate", "/api/ipv4-enumerate"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-ipv4-enumerate.py", ["json"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in (
            "/api/field-planetary-dns-authority",
            "/api/field-planetary-dns-authority/complete",
            "/api/field-planetary-dns-authority/remove-foreign",
            "/api/planetary-dns-authority",
        ):
            if path.endswith("/complete"):
                cmd = ["complete"]
            elif path.endswith("/remove-foreign"):
                cmd = ["remove-foreign"]
            else:
                cmd = ["json"]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-planetary-dns-authority.py",
                cmd,
                timeout=120,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in (
            "/api/field-ipv4-device-sovereign",
            "/api/field-ipv4-device-sovereign/manage",
            "/api/ipv4-device-sovereign",
            "/api/ipv4-device-sovereign/manage",
        ):
            cmd = "manage" if path.endswith("/manage") else "json"
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-ipv4-device-sovereign.py",
                [cmd],
                timeout=90 if cmd == "manage" else 30,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-dns-dhcp-collision-guard/threats", "/api/collision-guard/threats"):
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-dns-dhcp-collision-guard.py",
                ["threat-scan"],
                timeout=30,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-dns-dhcp-collision-guard", "/api/collision-guard"):
            cmd = "enforce" if path.endswith("/enforce") else "json"
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-dns-dhcp-collision-guard.py",
                [cmd],
                timeout=45,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/humanoid-motion", "/api/humanoid-motion/status"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "humanoid-motion-training.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/humanoid-motion/catalog":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "humanoid-motion-training.py", ["catalog"], timeout=15)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/humanoid-motion/wireframe":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "humanoid-motion-training.py", ["wireframe"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/humanoid-motion/data-all", "/api/humanoid-motion/data"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "humanoid-motion-training.py", ["data-all"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/humanoid-motion/secured", "/api/humanoid-motion-secured"):
            sub = path.replace("/api/humanoid-motion-secured", "").replace("/api/humanoid-motion/secured", "").strip("/")
            cmd = sub or "panel"
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "humanoid-motion-secured.py", [cmd], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/plate-meld":
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            cached = _load_plate_meld_cached()
            if not refresh:
                if cached.get("schema"):
                    self._send(200, json.dumps(cached), "application/json")
                    return
                self._send(
                    200,
                    json.dumps({
                        "schema": "field-plate-meld/v1",
                        "ok": False,
                        "error": "meld_not_published",
                        "hint": "POST /api/plate-meld/cycle or wait for vigil meld tick",
                    }),
                    "application/json",
                )
                return
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-plate-meld.py",
                ["meld"],
                timeout=180,
            )
            if not payload or not payload.get("schema"):
                if cached.get("schema"):
                    payload = cached
            self._send(200, json.dumps(payload or {"ok": False, "error": "meld_unavailable"}), "application/json")
            return

        if path == "/api/plate-meld/cycle":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-plate-meld.py",
                ["meld"],
                timeout=180,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/plate-meld-orchestrator":
            orch = INSTALL_ROOT / "lib" / "field-plate-meld-orchestrator.py"
            if orch.is_file():
                sub = str(query.get("cmd", ["json"])[0]).strip().lower() or "json"
                if sub in ("run", "cycle", "full", "fast"):
                    payload = _nexus_py_json(orch, [sub], timeout=240)
                else:
                    payload = _nexus_py_json(orch, [sub if sub != "status" else "json"], timeout=120)
            else:
                payload = {"schema": "field-plate-meld-orchestrator/v1", "ok": False, "error": "orchestrator_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/plate-meld-orchestrator/"):
            orch = INSTALL_ROOT / "lib" / "field-plate-meld-orchestrator.py"
            sub = path[len("/api/plate-meld-orchestrator/") :].strip("/").lower().replace("-", "_")
            cmd_map = {
                "audit": "audit",
                "improve": "improve",
                "improvements": "improve",
                "connect": "connect",
                "bottom": "bottom",
                "bottom_cpu": "bottom",
                "report": "report",
                "cycle": "cycle",
                "full": "full",
                "fast": "fast",
            }
            cli = cmd_map.get(sub, "json")
            if orch.is_file():
                payload = _nexus_py_json(orch, [cli], timeout=240 if cli in ("cycle", "full", "fast") else 120)
            else:
                payload = {"ok": False, "error": "orchestrator_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/g16-compiler-sense", "/api/compiler-sense-plate"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "g16-compiler-sense-plate.py", ["json"], timeout=40)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/plate-test-runner", "/api/plate-tests"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-plate-test-runner.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/iron-plate/motion-resolve", "/api/iron-plate/resolve"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "iron-plate-motion-resolve.py", ["resolve"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/iron-plate/goals":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "iron-plate-motion-resolve.py", ["goals"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/iron-plate/assemblage":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "iron-plate-motion-resolve.py", ["assemblage"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/iron-plate/full-meld", "/api/full-assemblage-meld"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "iron-plate-motion-resolve.py", ["full-meld"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/iron-plate/organize", "/api/iron-plate-organize"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "iron-plate-organize.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload), "application/json")
            return
        if path in ("/api/iron-plate/spots", "/api/iron-plate-spot"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "iron-plate-spot-detector.py", ["json"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/weapons-defense", "/api/hostess7-weapons-defense"):
            script = INSTALL_ROOT / "lib" / "hostess7-weapons-defense.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["posture"], timeout=45)
            else:
                payload = {"ok": False, "error": "hostess7_weapons_defense_missing"}
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-war-hardening", "/api/field-war-harden"):
            script = INSTALL_ROOT / "lib" / "field-war-hardening.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["posture"], timeout=45)
            else:
                payload = {"ok": False, "error": "field_war_hardening_missing"}
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/hostess7/system-control", "/api/hostess7-system-control"):
            script = INSTALL_ROOT / "lib" / "hostess7-system-control.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=30)
            else:
                payload = {"ok": False, "error": "hostess7_system_control_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/hostess7/component-seal", "/api/hostess7-component-seal"):
            script = INSTALL_ROOT / "lib" / "hostess7-component-seal.py"
            sub = path.replace("/api/hostess7-component-seal", "").replace("/api/hostess7/component-seal", "").strip("/")
            if script.is_file():
                if sub in ("", "status", "json", "posture"):
                    payload = _nexus_py_json(script, ["posture"], timeout=45)
                elif sub in ("seal", "seal-all", "seal_all"):
                    payload = _nexus_py_json(script, ["seal"], timeout=60)
                else:
                    payload = _nexus_py_json(script, ["posture"], timeout=45)
            else:
                payload = {"ok": False, "error": "hostess7_component_seal_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/hostess7/brain-guard", "/api/hostess7-brain-guard"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-brain-guard.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/brain-guard/verify":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-brain-guard.py", ["verify"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/brain-guard/witness", "/api/hostess7-brain-guard/witness"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-brain-guard.py", ["witness"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/brain/ruling", "/api/hostess7-brain-ruler", "/api/hostess7/brain-ruler"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-brain-ruler.py", ["json"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/brain/sovereignty", "/api/hostess7/brain/assess"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-brain-ruler.py", ["assess"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/brain/ruling/explain":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-brain-ruler.py",
                ["teach", str(q or "earth mandate rule")],
                timeout=30,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/self-view", "/api/hostess7-self-view"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-self-view.py", ["json"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/appearance", "/api/hostess7-operator-appearance"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-self-view.py", ["deliver"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/core-of-truth", "/api/hostess7-core-of-truth"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-self-view.py", ["truth"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/operator-lookup", "/api/hostess7-operator-lookup"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-self-view.py", ["lookup"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/programming", "/api/hostess7-programming"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-programming.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/programming/explain":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-programming.py",
                ["explain", str(q or "better than assistant")],
                timeout=25,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/g16", "/api/hostess7-g16"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-g16.py", ["json"], timeout=35)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/g16-online") or path in ("/api/hostess7-g16-online",):
            g16o_py = INSTALL_ROOT / "lib" / "hostess7-g16-online.py"
            sub = path.replace("/api/hostess7-g16-online", "").replace("/api/hostess7/g16-online", "").strip("/")
            if sub in ("ensure", "boot", "online"):
                payload = _nexus_py_json(g16o_py, ["ensure"], timeout=60)
            elif sub == "probe":
                payload = _nexus_py_json(g16o_py, ["probe"], timeout=60)
            else:
                payload = _nexus_py_json(g16o_py, ["panel"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False, "boss": "hostess7"}), "application/json")
            return

        if path in ("/api/hostess7/userwatch", "/api/hostess7-userwatch"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-userwatch.py", ["json"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/userwatch/apex", "/api/hostess7-userwatch/apex"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-userwatch.py", ["apex"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/userwatch/fingerprint", "/api/hostess7-userwatch/fingerprint"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-userwatch.py", ["fingerprint"], timeout=15)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/input-training") or path in ("/api/hostess7-input-training",):
            it_py = INSTALL_ROOT / "lib" / "hostess7-input-training.py"
            payload = _nexus_py_json(it_py, ["json"], timeout=45) if it_py.is_file() else {"ok": False, "error": "input_training_missing"}
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/field-stereo-vision") or path in ("/api/field-stereo-vision",):
            fsv_py = INSTALL_ROOT / "lib" / "field-stereo-vision.py"
            sub = path.replace("/api/field-stereo-vision", "").strip("/") or "status"
            args = {"status": ["json"], "probe": ["probe"], "webcams": ["webcams"], "tv-learn": ["tv-learn"]}.get(sub, ["json"])
            payload = _nexus_py_json(fsv_py, args, timeout=45) if fsv_py.is_file() else {"ok": False, "error": "stereo_vision_missing"}
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/znetwork", "/api/hostess7-znetwork", "/api/znetwork/hostess7"):
            wire_py = INSTALL_ROOT / "lib" / "hostess7-znetwork-wire.py"
            payload = _nexus_py_json(wire_py, ["panel"], timeout=45) if wire_py.is_file() else {"ok": False, "error": "hostess7_znetwork_wire_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/hostess7/communication-profile", "/api/hostess7-communication-profile"):
            wire_py = INSTALL_ROOT / "lib" / "hostess7-znetwork-wire.py"
            payload = _nexus_py_json(wire_py, ["profile"], timeout=20) if wire_py.is_file() else {"ok": False}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7/x-comments",
            "/api/hostess7-x-comments",
            "/api/operator-x-comments",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            force_open = str(query.get("open", ["1"])[0]).strip().lower() in ("1", "true", "yes")
            x_py = INSTALL_ROOT / "lib" / "hostess7-x-comments.py"
            payload = None
            if not refresh:
                cache_path = STATE_DIR / "operator-x-comments-cache.json"
                if cache_path.is_file():
                    try:
                        payload = json.loads(cache_path.read_text(encoding="utf-8"))
                        if force_open and payload:
                            payload = _nexus_py_json(x_py, ["cache"], timeout=8) or payload
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                args = ["open"] if refresh else ["json"]
                payload = _nexus_py_json(x_py, args, timeout=60 if refresh else 12)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/field-url-heuristics-steel",
            "/api/hostess7/url-heuristics",
            "/api/url-heuristics-steel",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            sub = path.split("/")[-1]
            steel_py = INSTALL_ROOT / "lib" / "field-url-heuristics-steel.py"
            if refresh or sub == "meld":
                args = ["meld"]
            elif sub == "why":
                args = ["why"]
            elif sub == "derive":
                args = ["derive"]
            else:
                args = ["json"]
            payload = _nexus_py_json(steel_py, args, timeout=120 if "meld" in args else 30)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7-big-grin-pwnership",
            "/api/big-grin-pwnership",
            "/api/operator-pwnership",
            "/api/look-pwnership",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            pwn_py = INSTALL_ROOT / "lib" / "hostess7-big-grin-pwnership.py"
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "hostess7-big-grin-pwnership-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                args = ["propagate"] if refresh else ["json"]
                payload = _nexus_py_json(pwn_py, args, timeout=90 if refresh else 20)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7/url-kill",
            "/api/hostess7-url-kill",
            "/api/operator-url-kill",
            "/api/url-kill",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            kill_py = INSTALL_ROOT / "lib" / "hostess7-url-kill.py"
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "hostess7-url-kill-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                args = ["kill"] if refresh else ["json"]
                payload = _nexus_py_json(kill_py, args, timeout=120 if refresh else 20)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7/whole-internet",
            "/api/hostess7-whole-internet",
            "/api/operator-whole-internet",
            "/api/whole-internet",
            "/api/good-guys-internet",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            whole_py = INSTALL_ROOT / "lib" / "hostess7-whole-internet.py"
            payload = None
            if not refresh:
                for cache_name in ("operator-whole-internet-cache.json", "hostess7-whole-internet-panel.json"):
                    cache_path = STATE_DIR / cache_name
                    if cache_path.is_file():
                        try:
                            payload = json.loads(cache_path.read_text(encoding="utf-8"))
                            break
                        except (OSError, json.JSONDecodeError):
                            payload = None
            if payload is None or refresh:
                args = ["run"] if refresh else ["json"]
                payload = _nexus_py_json(whole_py, args, timeout=300 if refresh else 30)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/field-internet-clean-all",
            "/api/internet-clean-all",
            "/api/hostess7/internet-clean-all",
        ) or path.startswith("/api/field-internet-clean-all/"):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            clean_py = INSTALL_ROOT / "lib" / "field-internet-clean-all.py"
            sub = path.replace("/api/field-internet-clean-all/", "").replace("/api/field-internet-clean-all", "").strip("/")
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "field-internet-clean-all-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                if sub in ("green", "ten", "10", "ten-of-ten", "all-green", "lanes") or (
                    refresh and str(query.get("mode", ["green"])[0]).strip().lower() in ("green", "ten", "1", "true")
                ):
                    args = ["green"]
                elif sub in ("clean", "run", "all", "internet") or refresh:
                    args = ["green"]  # safe 10/10 path — no recursive storm
                    if str(query.get("propagate", ["0"])[0]).strip().lower() in ("1", "true", "yes"):
                        args.append("--propagate")
                elif sub in ("core", "sweep"):
                    args = ["core"]
                elif sub == "names":
                    args = ["names"]
                else:
                    args = ["json"]
                payload = _nexus_py_json(clean_py, args, timeout=300 if refresh else 45)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/trillions",
            "/api/trillions/",
            "/api/field-trillions",
            "/api/field-trillions/",
            "/api/kill-whoever-stands-in-way",
        ):
            try:
                cached = STATE_DIR / "field-trillions-kill-path-panel.json"
                qs_t = parse_qs(urlparse(self.path).query)
                force = str(qs_t.get("refresh", qs_t.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "enforce", "kill", "seal",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            payload["trillions"] = True
                            payload["kill_whoever_stands_in_way"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-trillions-kill-path.py",
                    ["enforce"] if force else ["status"],
                    timeout=240 if force else 30,
                )
                self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        if path in (
            "/api/grab-all-devices",
            "/api/grab-all-devices/",
            "/api/grab-devices",
            "/api/grab-devices/",
            "/api/devices-grab-permanent-threat",
        ):
            try:
                cached = STATE_DIR / "field-grab-all-devices-panel.json"
                qs_g = parse_qs(urlparse(self.path).query)
                force = str(qs_g.get("refresh", qs_g.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "grab", "seal",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            payload["reattempt_is_permanent_threat"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-grab-all-devices-permanent-threat.py",
                    ["grab"] if force else ["status"],
                    timeout=300 if force else 30,
                )
                self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        if path in (
            "/api/weave-everything-inside",
            "/api/weave-everything-inside/",
            "/api/weave-inside",
            "/api/weave-inside/",
            "/api/field-1-forever",
            "/api/we-are-the-earth",
        ):
            try:
                cached = STATE_DIR / "field-weave-everything-inside-panel.json"
                qs_wi = parse_qs(urlparse(self.path).query)
                force = str(qs_wi.get("refresh", qs_wi.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "seal", "weave", "forever",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            payload["field_1_forever"] = True
                            payload["we_are_inside"] = True
                            payload["we_are_the_earth"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-weave-everything-inside.py",
                    ["seal"] if force else ["status"],
                    timeout=420 if force else 30,
                )
                self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        if path in (
            "/api/field-full-weave",
            "/api/field-full-weave/",
            "/api/full-weave",
            "/api/full-weave/",
            "/api/weave",
        ):
            try:
                cached = STATE_DIR / "field-full-weave-panel.json"
                qs_w = parse_qs(urlparse(self.path).query)
                force = str(qs_w.get("refresh", qs_w.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "seal", "weave", "green",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            payload["classic_is_subset"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-full-weave.py",
                    ["seal"] if force else ["status"],
                    timeout=360 if force else 30,
                )
                self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return
        if path in (
            "/api/distributed-server-lanes",
            "/api/distributed-server-lanes/",
            "/api/server-lanes",
            "/api/every-server-lane",
        ):
            try:
                cached = STATE_DIR / "field-distributed-server-lanes-panel.json"
                qs_sl = parse_qs(urlparse(self.path).query)
                force = str(qs_sl.get("refresh", qs_sl.get("force", ["0"]))[0]).strip().lower() in (
                    "1", "true", "yes", "refresh", "seal",
                )
                if cached.is_file() and not force:
                    try:
                        payload = json.loads(cached.read_text(encoding="utf-8"))
                        if isinstance(payload, dict):
                            payload = dict(payload)
                            payload["_operator_api"] = True
                            payload["easy_peezy"] = True
                            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                            return
                    except (OSError, json.JSONDecodeError):
                        pass
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-distributed-server-lanes.py",
                    ["seal"] if force else ["status"],
                    timeout=120 if force else 20,
                )
                self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)[:160]}), "application/json")
            return

        if path in (
            "/api/hostess7/x-brand-purge",
            "/api/hostess7-x-brand-purge",
            "/api/x-brand-purge",
            "/api/x-producer",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            purge_py = INSTALL_ROOT / "lib" / "hostess7-x-brand-purge.py"
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "hostess7-x-brand-purge-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                args = ["purge"] if refresh else ["json"]
                payload = _nexus_py_json(purge_py, args, timeout=60 if refresh else 12)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7/x-sso-fix",
            "/api/hostess7-x-sso-fix",
            "/api/x-sso-fix",
            "/api/x-jetfuel-fix",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            sso_py = INSTALL_ROOT / "lib" / "hostess7-x-sso-fix.py"
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "hostess7-x-sso-fix-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                args = ["repair"] if refresh else ["json"]
                payload = _nexus_py_json(sso_py, args, timeout=45 if refresh else 12)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7/x-profile-fix",
            "/api/hostess7-x-profile-fix",
            "/api/x-profile-fix",
            "/api/x-hasnt-posted",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            prof_py = INSTALL_ROOT / "lib" / "hostess7-x-profile-fix.py"
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "hostess7-x-profile-fix-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                args = ["repair"] if refresh else ["json"]
                payload = _nexus_py_json(prof_py, args, timeout=90 if refresh else 20)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7/elon-kitchen-sink",
            "/api/hostess7-elon-kitchen-sink",
            "/api/hostess7/kitchen-sink",
            "/api/kitchen-sink",
            "/api/elon-defense",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            ks_py = INSTALL_ROOT / "lib" / "hostess7-elon-kitchen-sink-defense.py"
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "hostess7-elon-kitchen-sink-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                args = ["defend"] if refresh else ["json"]
                payload = _nexus_py_json(ks_py, args, timeout=720 if refresh else 30)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7/x-producer",
            "/api/hostess7-x-producer",
            "/api/x-producer",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            prod_py = INSTALL_ROOT / "lib" / "hostess7-x-producer.py"
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "hostess7-x-producer-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                args = ["produce"] if refresh else ["json"]
                payload = _nexus_py_json(prod_py, args, timeout=120 if refresh else 25)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/field-people-chip",
            "/api/field/people-chip",
            "/api/chips/people",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            pc_py = INSTALL_ROOT / "lib" / "field-people-chip-combinatorics.py"
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "field-people-chip-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                args = ["publish"] if refresh else ["json"]
                payload = _nexus_py_json(pc_py, args, timeout=150 if refresh else 30)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7/x-straight-shot",
            "/api/hostess7-x-straight-shot",
            "/api/x-straight-shot",
            "/api/x-no-middlemen",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            rip = str(query.get("rip", ["1"])[0]).strip().lower() in ("1", "true", "yes")
            ss_py = INSTALL_ROOT / "lib" / "hostess7-x-straight-shot.py"
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "hostess7-x-straight-shot-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                args = ["rip"] if rip else ["run"]
                payload = _nexus_py_json(ss_py, args, timeout=90 if refresh else 20)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7/censorship-clear",
            "/api/hostess7-censorship-clear-worldwide",
            "/api/censorship-clear",
            "/api/just-ask",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            clear_py = INSTALL_ROOT / "lib" / "hostess7-censorship-clear-worldwide.py"
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "hostess7-censorship-clear-worldwide-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                payload = _nexus_py_json(clear_py, ["clear"], timeout=180 if refresh else 30)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7/email-censorship-clear",
            "/api/hostess7-email-censorship-clear",
            "/api/operator-email-censorship-clear",
            "/api/email-censorship-clear",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            email_py = INSTALL_ROOT / "lib" / "hostess7-email-censorship-clear.py"
            payload = None
            if not refresh:
                panel_path = STATE_DIR / "hostess7-email-censorship-clear-panel.json"
                if panel_path.is_file():
                    try:
                        payload = json.loads(panel_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                payload = _nexus_py_json(email_py, ["clear"], timeout=180 if refresh else 45)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7/tco-kill",
            "/api/hostess7-tco-kill",
            "/api/operator-tco-kill",
            "/api/tco-kill",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            tco_py = INSTALL_ROOT / "lib" / "hostess7-tco-kill.py"
            payload = None
            if not refresh:
                cache_path = STATE_DIR / "operator-tco-kill-cache.json"
                if cache_path.is_file():
                    try:
                        payload = json.loads(cache_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                args = ["kill"] if refresh else ["json"]
                payload = _nexus_py_json(tco_py, args, timeout=60 if refresh else 12)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7/google-youtube-open",
            "/api/hostess7-google-youtube-open",
            "/api/operator-google-youtube-open",
            "/api/operator-youtube-comments",
            "/api/operator-google-open",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            gy_py = INSTALL_ROOT / "lib" / "hostess7-google-youtube-open.py"
            payload = None
            if not refresh:
                cache_path = STATE_DIR / "operator-google-youtube-cache.json"
                if cache_path.is_file():
                    try:
                        payload = json.loads(cache_path.read_text(encoding="utf-8"))
                        if payload and str(query.get("open", ["1"])[0]).strip().lower() in ("1", "true", "yes"):
                            opened = _nexus_py_json(gy_py, ["cache"], timeout=8)
                            if opened:
                                payload = opened
                    except (OSError, json.JSONDecodeError):
                        payload = None
            if payload is None or refresh:
                args = ["open"] if refresh else ["json"]
                payload = _nexus_py_json(gy_py, args, timeout=60 if refresh else 12)
            if path == "/api/operator-google-open" and isinstance(payload, dict):
                payload = {**payload, "slice": "google", "google": payload.get("google")}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/hostess7/censorship-exposure",
            "/api/hostess7-censorship-exposure",
            "/api/operator-censorship-exposure",
        ):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-censorship-exposure.py", ["expose"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/g16/stack", "/api/nexus/g16", "/api/nexus-g16-stack"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "nexus-g16-bridge.py", ["json"], timeout=40)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/g16/secure-chamber", "/api/g16/secure-chamber/posture", "/api/g16-secure-chamber"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "g16-secure-chamber.py", ["posture"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/grok15/language-core", "/api/g15/language-core", "/api/grok15-language-core"):
            payload = _nexus_py_json(INSTALL_ROOT / "Grok16" / "lib" / "grok15-language-core.py", ["posture"], timeout=35)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/g16/rtx-gate", "/api/g16/rtx"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "nexus-g16-bridge.py", ["rtx"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/g16/linker", "/api/plate-compiler"):
            script = INSTALL_ROOT / "lib" / ("plate-compiler.py" if "plate" in path else "nexus-g16-bridge.py")
            args = ["json"] if "plate" in path else ["linker"]
            payload = _nexus_py_json(script, args, timeout=35)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/drop-in-orchestrator", "/api/drop-in", "/api/field-drop-in"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-drop-in-orchestrator.py", ["json"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/sovereign-protocol", "/api/sovereign-protocol-bridge"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-sovereign-protocol-bridge.py", ["json"], timeout=40)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/display-open", "/api/field-displays"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-display-open.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-devices", "/api/device-registry"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-drop-in-orchestrator.py", ["devices"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7-training-viewer/ensure", "/api/hostess7-training-viewer/open"):
            payload = _ensure_training_viewer()
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/queen-loopback/probe":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "queen-loopback-probe.py", [], timeout=15)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/qemu-world-status":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "qemu-world-status.py", [], timeout=35)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-arcade-battalion", "/api/field-arcade-battalion/"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-arcade-battalion.py", ["lobby"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/game-room", "/api/game-room/") or path.startswith("/api/game-room/"):
            q = self.path.split("?", 1)[1] if "?" in self.path else ""
            code, raw, ctype = _queen_world_proxy_http("GET", path.split("?", 1)[0], query=q, timeout=30.0)
            self._send(code, raw, ctype)
            return

        if path in ("/api/sap", "/api/sap/"):
            code, raw, ctype = _queen_world_proxy_http("GET", "/api/sap", timeout=15.0)
            self._send(code, raw, ctype)
            return

        if path in ("/api/nes-library", "/api/nes-library/"):
            q = self.path.split("?", 1)[1] if "?" in self.path else ""
            code, raw, ctype = _queen_world_proxy_http("GET", "/api/nes-library", query=q, timeout=20.0)
            self._send(code, raw, ctype)
            return

        if path == "/api/ammonet":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "ammonet-field.py", ["panel"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/github-secure", "/api/field-github-secure", "/api/secure-git"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-github-secure.py", ["json"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-internet/keepalive":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-internet-unified.py", ["keepalive"], timeout=35)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-internet":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-internet-unified.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-github-legacy":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-github-legacy.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-github-resilience":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-github-resilience.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-botnet-legal-ports":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-botnet-legal-ports.py", ["json"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-h7t-truth":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-h7t-truth.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-github-everyone":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-github-everyone.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-endpoint-registry", "/api/field-pages-movement"):
            reg_py = INSTALL_ROOT / "lib" / "field-endpoint-registry.py"
            sub = ["pages"] if path == "/api/field-pages-movement" else ["json"]
            payload = _nexus_py_json(reg_py, sub, timeout=35)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-everyone-counter":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-everyone-counter.py", ["json"], timeout=8)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in (
            "/api/everyone-online",
            "/api/field-everyone-online-celebrate",
            "/api/celebrate",
        ):
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-everyone-online-celebrate.py",
                ["json"],
                timeout=12,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/interaction":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-github-interaction.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-botnet-registry":
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            payload = None if refresh else _read_botnet_panel_cache("registry")
            if payload is None:
                payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-botnet-registry.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-botnet-dns-dhcp/keepalive":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-botnet-dns-dhcp.py", ["keepalive"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-botnet-dns-dhcp":
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            payload = None if refresh else _read_botnet_panel_cache("dns_dhcp")
            if payload is None:
                payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-botnet-dns-dhcp.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-fcc-prom-detector", "/api/fcc-prom-detector"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-fcc-prom-detector.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-secure-email", "/api/secure-email"):
            sub = path.replace("/api/field-secure-email", "").replace("/api/secure-email", "").strip("/")
            args = ["apache"] if sub == "apache" else ["json"]
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-secure-email.py", args, timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/ammonet/dns-zones", "/api/ammonet-dns-zones"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "ammonet-dns-zones.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/field-qubes-drive-provision") or path in ("/api/field-qubes-drive",):
            qdp_py = INSTALL_ROOT / "lib" / "field-qubes-drive-provision.py"
            sub = path.replace("/api/field-qubes-drive-provision", "").replace("/api/field-qubes-drive", "").strip("/")
            if sub in ("team-layout", "team_layout"):
                args = ["team-layout"]
            elif sub in ("aia-export", "export-aia"):
                args = ["aia-export"]
            elif sub == "wipe":
                args = ["wipe", "--confirm"] if str(query.get("confirm", ["0"])[0]).strip().lower() in ("1", "true", "yes") else ["wipe"]
            else:
                args = ["json"]
            payload = _nexus_py_json(qdp_py, args, timeout=90) if qdp_py.is_file() else {"ok": False, "error": "field_qubes_drive_missing"}
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/field-aia-accelerator", "/api/aia-accelerator"):
            aia_py = INSTALL_ROOT / "lib" / "field-aia-accelerator.py"
            sub = path.replace("/api/field-aia-accelerator", "").replace("/api/aia-accelerator", "").strip("/")
            if sub in ("export", "aia-export", "stage"):
                args = ["export"]
            else:
                args = ["json"]
            payload = _nexus_py_json(aia_py, args, timeout=120) if aia_py.is_file() else {"ok": False, "error": "field_aia_accelerator_missing"}
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/final-internet":
            fi = INSTALL_ROOT / "data" / "final-internet-doctrine.json"
            try:
                payload = json.loads(fi.read_text(encoding="utf-8")) if fi.is_file() else {}
                payload["ok"] = True
            except (OSError, json.JSONDecodeError):
                payload = {"ok": False}
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/steel-plates":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-steel-neural-plates.py", ["slice"], timeout=90)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/plate-meld":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-plate-meld.py", ["json"], timeout=90)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/queen-browser/open":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-queen-browser-open.py", ["open"], timeout=50)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/queen-browser/f9":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-queen-browser-open.py", ["f9"], timeout=50)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/codecraft", "/api/hostess7-codecraft"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-codecraft.py", ["json"], timeout=90)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/codecraft/explain":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-codecraft.py",
                ["teach", str(q or "codecraft mastery")],
                timeout=45,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/codecraft/testing-center":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-codecraft.py",
                ["testing-center", "--fast"],
                timeout=180,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/operator", "/api/hostess7-operator"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-operator.py", ["json"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/change-awareness", "/api/hostess7-change-awareness"):
            ca_py = INSTALL_ROOT / "lib" / "hostess7-change-awareness.py"
            sub = path.replace("/api/hostess7-change-awareness", "").replace("/api/hostess7/change-awareness", "").strip("/")
            if sub in ("pulse", "scan", "timing"):
                payload = _nexus_py_json(ca_py, [sub], timeout=60)
            elif sub in ("explain", "teach") and query.get("q"):
                payload = _nexus_py_json(ca_py, ["explain", str(query.get("q", [""])[0])], timeout=30)
            else:
                payload = _nexus_py_json(ca_py, ["panel"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/truth-lie-threat", "/api/hostess7-truth-lie-threat"):
            tlt_py = INSTALL_ROOT / "lib" / "hostess7-truth-lie-threat.py"
            sub = path.replace("/api/hostess7-truth-lie-threat", "").replace("/api/hostess7/truth-lie-threat", "").strip("/")
            if sub in ("witness", "discern", "analyze", "classify"):
                claim = str(query.get("claim", query.get("q", [""]))[0]).strip()
                args = [sub if sub != "classify" else "classify", claim] if claim else [sub]
                payload = _nexus_py_json(tlt_py, args, timeout=45)
            elif sub in ("pulse", "threats", "vectors", "methods"):
                payload = _nexus_py_json(tlt_py, [sub], timeout=45)
            else:
                payload = _nexus_py_json(tlt_py, ["panel"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/book-maker") or path.startswith("/api/hostess7-book-maker"):
            maker_py = INSTALL_ROOT / "lib" / "hostess7-book-maker.py"
            sub = (
                path.replace("/api/hostess7-book-maker", "")
                .replace("/api/hostess7/book-maker", "")
                .strip("/")
            )
            if sub == "authors":
                payload = _nexus_py_json(maker_py, ["authors"], timeout=30)
            elif sub == "index":
                bid = str(query.get("book_id", query.get("id", [""]))[0]).strip()
                args = ["index", bid] if bid else ["index"]
                payload = _nexus_py_json(maker_py, args, timeout=45)
            else:
                payload = _nexus_py_json(maker_py, ["panel"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/aml-ingress", "/api/hostess7-aml-ingress"):
            aml_py = INSTALL_ROOT / "lib" / "hostess7-aml-ingress.py"
            sub = path.replace("/api/hostess7-aml-ingress", "").replace("/api/hostess7/aml-ingress", "").strip("/")
            if sub in ("read", "local", "consume"):
                payload = _nexus_py_json(aml_py, [sub], timeout=45)
            elif sub == "discern":
                claim = str(query.get("claim", query.get("q", [""]))[0]).strip()
                args = ["discern", claim] if claim else ["discern"]
                payload = _nexus_py_json(aml_py, args, timeout=45)
            elif sub == "ingress" or query.get("claim"):
                claim = str(query.get("claim", query.get("payload", query.get("q", [""])))[0]).strip()
                body = {"claim": claim, "party": str(query.get("party", ["api"])[0]), "source": "api"}
                payload = _nexus_py_json(aml_py, ["ingress", json.dumps(body)], timeout=45)
            else:
                payload = _nexus_py_json(aml_py, ["panel"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/ingress-egress-gate") or path in ("/api/hostess7-ingress-egress-gate",):
            gate_py = INSTALL_ROOT / "lib" / "hostess7-ingress-egress-gate.py"
            sub = (
                path.replace("/api/hostess7-ingress-egress-gate", "")
                .replace("/api/hostess7/ingress-egress-gate", "")
                .strip("/")
            )
            if sub in ("ingress_posture", "ingress_check"):
                payload = _nexus_py_json(gate_py, ["ingress_posture"], timeout=45)
            elif sub in ("egress_posture", "egress_check"):
                payload = _nexus_py_json(gate_py, ["egress_posture"], timeout=45)
            elif sub == "ingress" or (sub == "" and query.get("claim")):
                claim = str(query.get("claim", query.get("payload", query.get("q", [""])))[0]).strip()
                body = {"claim": claim, "party": str(query.get("party", ["api"])[0]), "source": "api"}
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(gate_py), "ingress"],
                        input=json.dumps(body),
                        capture_output=True,
                        text=True,
                        timeout=60,
                        env=env,
                        cwd=str(INSTALL_ROOT),
                    )
                    payload = json.loads(proc.stdout or "{}")
                except (subprocess.TimeoutExpired, json.JSONDecodeError):
                    payload = {"ok": False, "admitted": False, "error": "ingress_gate_failed"}
            elif sub == "egress":
                body = {
                    "payload": str(query.get("payload", query.get("claim", [""]))[0]),
                    "destination": str(query.get("destination", query.get("dest", ["unknown"]))[0]),
                    "operator_release": str(query.get("operator_release", ["0"])[0]) in ("1", "true"),
                }
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(gate_py), "egress"],
                        input=json.dumps(body),
                        capture_output=True,
                        text=True,
                        timeout=60,
                        env=env,
                        cwd=str(INSTALL_ROOT),
                    )
                    payload = json.loads(proc.stdout or "{}")
                except (subprocess.TimeoutExpired, json.JSONDecodeError):
                    payload = {"ok": False, "permitted": False, "error": "egress_gate_failed"}
            else:
                payload = _nexus_py_json(gate_py, ["panel"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False, "fully_gated": False}), "application/json")
            return

        if path in ("/api/hostess7/presume", "/api/hostess7-presume"):
            presume_py = INSTALL_ROOT / "lib" / "hostess7-presume.py"
            sub = path.replace("/api/hostess7-presume", "").replace("/api/hostess7/presume", "").strip("/")
            if sub in ("profile", "checkpoint", "propagate", "commits", "train", "training", "timing", "health"):
                payload = _nexus_py_json(presume_py, [sub], timeout=60)
            elif sub in ("decide", "release"):
                aid = str(query.get("id", query.get("action_id", [""]))[0]).strip() or "presume_api"
                args = [sub, aid] if sub == "release" else [sub, "--id=" + aid]
                payload = _nexus_py_json(presume_py, args, timeout=30)
            elif sub == "presume" or query.get("wait_us"):
                wait_us = str(query.get("wait_us", ["0"])[0]).strip()
                args = ["presume", wait_us] if wait_us.isdigit() else ["presume", "0"]
                alt = str(query.get("alternate", [""])[0]).strip()
                if alt:
                    args.append(f"--alternate={alt}")
                payload = _nexus_py_json(presume_py, args, timeout=60)
            else:
                payload = _nexus_py_json(presume_py, ["panel"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/zachary-teaching") or path.startswith("/api/hostess7-zachary-teaching"):
            zach_py = INSTALL_ROOT / "lib" / "hostess7-zachary-teaching.py"
            sub = path.replace("/api/hostess7-zachary-teaching", "").replace("/api/hostess7/zachary-teaching", "").strip("/")
            if sub == "message":
                payload = _nexus_py_json(zach_py, ["message"], timeout=30)
            elif sub == "counsel":
                need = str(query.get("need", query.get("context", query.get("q", [""])))[0]).strip()
                args = ["counsel"] + ([need] if need else [])
                payload = _nexus_py_json(zach_py, args, timeout=30)
            elif sub == "witness":
                target = str(query.get("target", query.get("id", [""]))[0]).strip()
                note = str(query.get("note", query.get("q", [""]))[0]).strip()
                args = ["witness", target] + ([note] if note else [])
                payload = _nexus_py_json(zach_py, args, timeout=30)
            else:
                payload = _nexus_py_json(zach_py, ["panel"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/cool-smooth", "/api/hostess7-cool-smooth"):
            cs_py = INSTALL_ROOT / "lib" / "hostess7-cool-smooth.py"
            sub = path.replace("/api/hostess7-cool-smooth", "").replace("/api/hostess7/cool-smooth", "").strip("/")
            if sub in ("explain", "teach"):
                payload = _nexus_py_json(cs_py, ["explain"], timeout=30)
            else:
                payload = _nexus_py_json(cs_py, ["panel"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/control-balancer", "/api/hostess7-control-balancer"):
            cb_py = INSTALL_ROOT / "lib" / "hostess7-control-balancer.py"
            sub = path.replace("/api/hostess7-control-balancer", "").replace("/api/hostess7/control-balancer", "").strip("/")
            if sub in ("balance", "rebalance"):
                payload = _nexus_py_json(cb_py, ["balance"], timeout=60)
            elif sub in ("connectionless", "offline"):
                payload = _nexus_py_json(cb_py, ["connectionless"], timeout=60)
            elif sub == "apply":
                payload = _nexus_py_json(cb_py, ["apply"], timeout=60)
            elif sub == "allocate":
                payload = _nexus_py_json(cb_py, ["allocate"], timeout=45)
            elif sub in ("explain", "teach"):
                q = str(query.get("q", query.get("query", [""]))[0]).strip()
                payload = {"ok": True, "text": (_nexus_py_json(cb_py, ["explain", q] if q else ["explain"], timeout=30) or {}).get("stdout", "")}
            elif sub == "set-mode" and query.get("mode"):
                payload = _nexus_py_json(cb_py, ["set-mode", str(query.get("mode", ["balanced"])[0])], timeout=60)
            elif sub == "set-lane" and query.get("lane"):
                lane = str(query.get("lane", [""])[0]).strip()
                en = str(query.get("enabled", query.get("on", ["1"]))[0]).strip()
                args = ["set-lane", lane, en]
                if query.get("weight"):
                    args.append(str(query.get("weight", [""])[0]))
                payload = _nexus_py_json(cb_py, args, timeout=60)
            else:
                payload = _nexus_py_json(cb_py, ["panel"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/war-system", "/api/hostess7-war-system"):
            war_py = INSTALL_ROOT / "lib" / "hostess7-war-system.py"
            sub = path.replace("/api/hostess7-war-system", "").replace("/api/hostess7/war-system", "").strip("/")
            if sub in ("registry",):
                payload = _nexus_py_json(war_py, ["registry"], timeout=30)
            elif sub in ("explain", "teach"):
                payload = {"ok": True, "text": (_nexus_py_json(war_py, ["explain"], timeout=30) or {}).get("stdout", "")}
            else:
                payload = _nexus_py_json(war_py, ["panel"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/system-core", "/api/hostess7-system-core"):
            core_py = INSTALL_ROOT / "lib" / "hostess7-system-core.py"
            sub = path.replace("/api/hostess7-system-core", "").replace("/api/hostess7/system-core", "").strip("/")
            if sub in ("train", "training"):
                args = ["train"]
                if str(query.get("full", ["0"])[0]).strip() in ("1", "true", "yes"):
                    args.append("--full")
                payload = _nexus_py_json(core_py, args, timeout=180)
            elif sub in ("verify",):
                payload = _nexus_py_json(core_py, ["verify"], timeout=90)
            else:
                payload = _nexus_py_json(core_py, ["panel"], timeout=90)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/operator/brief":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-operator.py", ["brief"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/operator/evaluate":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-operator.py", ["evaluate"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/operator/catalog":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-operator.py", ["catalog"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/tasklist", "/api/hostess7-tasklist"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-tasklist.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/virtual-workspace", "/api/hostess7-virtual-workspace"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-virtual-workspace.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/chips-coding/explain":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or ["virtual workspace chips debug"])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-virtual-workspace.py",
                ["teach", str(q)],
                timeout=25,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/ironclad/secure-api"):
            mod = _ironclad_secure_api_mod()
            if mod and hasattr(mod, "ironclad_secure_api"):
                payload = mod.ironclad_secure_api().handle_api(path, query=query)
                extra = mod.security_headers() if hasattr(mod, "security_headers") else {}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json", extra_headers=extra)
                return
            self._send(503, json.dumps({"ok": False, "error": "ironclad_secure_api_missing"}), "application/json")
            return

        if path.startswith("/api/ironclad/access") or path.startswith("/api/ironclad/h7-access"):
            acc = INSTALL_ROOT / "lib" / "ironclad-access.py"
            if acc.is_file():
                import importlib.util
                spec = importlib.util.spec_from_file_location("ironclad_access_http", acc)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    action = str(query.get("action", [""])[0] or "").strip().lower()
                    if path.rstrip("/").endswith("/tools"):
                        action = "tools"
                    elif path.rstrip("/").endswith("/search") or query.get("q") or query.get("query"):
                        action = action or "search"
                    elif path.rstrip("/").endswith("/h7") or path.startswith("/api/ironclad/h7-access"):
                        sub = path.rstrip("/").split("/")[-1]
                        action = {"resolve": "h7_resolve", "catalog": "h7_catalog", "search": "h7_search"}.get(sub, "h7_catalog")
                    elif not action:
                        action = "posture"
                    payload = mod.dispatch(action, body={
                        "query": str(query.get("q", query.get("query", [""]))[0] if query.get("q") or query.get("query") else ""),
                        "q": str(query.get("q", query.get("query", [""]))[0] if query.get("q") or query.get("query") else ""),
                        "context": str(query.get("context", ["all"])[0]),
                        "limit": int(query.get("limit", ["48"])[0] or 48),
                        "book_id": str(query.get("book_id", query.get("id", [""]))[0] or ""),
                    })
                    sec = _ironclad_secure_api_mod()
                    extra = sec.security_headers() if sec and hasattr(sec, "security_headers") else {}
                    self._send(200, json.dumps(payload, ensure_ascii=False), "application/json", extra_headers=extra)
                    return
            self._send(503, json.dumps({"ok": False, "error": "ironclad_access_missing"}), "application/json")
            return

        if path.startswith("/api/beyond-darpa-security") or path in ("/api/beyond-darpa-security",):
            bds_py = INSTALL_ROOT / "lib" / "beyond-darpa-security.py"
            sub = path.replace("/api/beyond-darpa-security", "").strip("/")
            if sub in ("assess", "threat"):
                qparams = parse_qs(urlparse(self.path).query)
                req = {
                    "action": "assess",
                    "channel": (qparams.get("channel") or ["machine"])[0],
                    "text": (qparams.get("text") or [""])[0],
                }
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(bds_py), "dispatch"],
                        input=json.dumps(req),
                        capture_output=True,
                        text=True,
                        timeout=30,
                        env=env,
                        cwd=str(INSTALL_ROOT),
                    )
                    payload = json.loads(proc.stdout or "{}")
                except (subprocess.TimeoutExpired, json.JSONDecodeError):
                    payload = {"ok": False, "error": "beyond_darpa_assess_failed"}
            else:
                payload = _nexus_py_json(bds_py, ["status"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False, "tier": "beyond_darpa_lockheed"}), "application/json")
            return

        if path in ("/api/ironclad", "/api/ironclad/plate"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "ironclad-plate.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/ironclad/grounding", "/api/ironclad/bible"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "ironclad-plate.py", ["grounding"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/ironclad/verify":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "ironclad-plate.py", ["verify"], timeout=15)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/ironclad/immediate", "/api/ironclad/for-self"):
            args = ["json"]
            self_id = str(query.get("self", ["hostess7"])[0] or "hostess7").strip()
            if path == "/api/ironclad/for-self":
                args = ["self", f"--self={self_id}"]
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "ironclad-immediate.py", args, timeout=15)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/ironclad/reality-field", "/api/ironclad/truth-serum"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "ironclad-reality-field.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/ironclad/field-sanity", "/api/ironclad/field_sanity"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "ironclad-field-sanity.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/ironclad/human-condition", "/api/human-condition"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "ironclad-reality-field.py", ["human-condition"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/ironclad/extrapolate", "/api/ironclad/neural-extrapolation"):
            claim = str(query.get("claim", [""])[0] or "").strip()
            target = str(query.get("target", ["any_intelligence_neural"])[0] or "any_intelligence_neural")
            args = ["extrapolate"]
            if claim:
                args.append(claim)
            if target and target != "any_intelligence_neural":
                args.append(f"--target={target}")
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "ironclad-plate.py", args, timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in (
            "/api/hostess7-online-world-l2",
            "/api/hostess7/online-world-l2",
            "/api/field-l2-exclusive-stack",
        ):
            cached = {
                "/api/hostess7-online-world-l2": STATE_DIR / "hostess7-online-world-l2-panel.json",
                "/api/hostess7/online-world-l2": STATE_DIR / "hostess7-online-world-l2-panel.json",
                "/api/field-l2-exclusive-stack": STATE_DIR / "field-l2-exclusive-stack-panel.json",
            }.get(path)
            if cached and cached.is_file() and str(query.get("refresh", ["0"])[0]).strip() not in ("1", "true", "yes"):
                try:
                    self._send(200, cached.read_text(encoding="utf-8"), "application/json")
                    return
                except OSError:
                    pass
            if path.endswith("l2-exclusive-stack"):
                payload = _read_state_json("field-l2-exclusive-stack-panel.json", {"ok": False})
            else:
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "hostess7-online-world-l2.py",
                    ["status"] if str(query.get("activate", ["0"])[0]) not in ("1", "true") else ["activate"],
                    timeout=120,
                )
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in ("/api/hostess7/training", "/api/hostess7-training"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-training.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/training/bundle", "/api/hostess7-training/bundle"):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            cache_path = STATE_DIR / "hostess7-training-bundle-cache.json"
            if not refresh and cache_path.is_file():
                try:
                    cached = json.loads(cache_path.read_text(encoding="utf-8"))
                    if isinstance(cached, dict) and cached.get("schema"):
                        cached["_panel_cache"] = True
                        self._send(200, json.dumps(cached), "application/json")
                        return
                except (OSError, json.JSONDecodeError):
                    pass
            args = ["bundle"] + (["--refresh"] if refresh else [])
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-training-bundle.py", args, timeout=60)
            if isinstance(payload, dict) and payload.get("schema"):
                try:
                    cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                except OSError:
                    pass
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/training/runtime", "/api/hostess7-training/runtime"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-training.py", ["runtime"], timeout=10)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/training/graphs", "/api/hostess7-training/graphs"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-training.py", ["graphs"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/archaeology", "/api/hostess7-archaeology"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-archaeology-training.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/archaeology/textbook", "/api/hostess7-archaeology/textbook"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-archaeology-training.py", ["textbook"], timeout=15)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/archaeology/corroborate", "/api/hostess7-archaeology/corroborate"):
            q = str((query.get("q") or query.get("claim") or [""])[0]).strip()
            args = ["corroborate", q] if q else ["corroborate"]
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-archaeology-training.py", args, timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/archaeology/help", "/api/hostess7-archaeology/help"):
            q = str((query.get("q") or query.get("query") or [""])[0]).strip()
            human = str((query.get("human") or ["0"])[0]).strip().lower() in ("1", "true", "yes")
            args = ["help", q]
            if human:
                args.append("--human")
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-archaeology-training.py", args, timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        # Textbook API routes: /api/hostess7/geology /api/hostess7/chemistry /api/hostess7/history
        for domain, script in (
            ("geology", "hostess7-geology-training.py"),
            ("chemistry", "hostess7-chemistry-training.py"),
            ("history", "hostess7-history-training.py"),
        ):
            if path in (f"/api/hostess7/{domain}", f"/api/hostess7-{domain}"):
                payload = _nexus_py_json(INSTALL_ROOT / "lib" / script, ["json"], timeout=30)
                self._send(200, json.dumps(payload or {"ok": False}), "application/json")
                return
            if path in (f"/api/hostess7/{domain}/textbook", f"/api/hostess7-{domain}/textbook"):
                payload = _nexus_py_json(INSTALL_ROOT / "lib" / script, ["textbook"], timeout=15)
                self._send(200, json.dumps(payload or {"ok": False}), "application/json")
                return
            if path in (f"/api/hostess7/{domain}/corroborate", f"/api/hostess7-{domain}/corroborate"):
                q = str((query.get("q") or query.get("claim") or [""])[0]).strip()
                args = ["corroborate", q] if q else ["corroborate"]
                payload = _nexus_py_json(INSTALL_ROOT / "lib" / script, args, timeout=20)
                self._send(200, json.dumps(payload or {"ok": False}), "application/json")
                return
            if path in (f"/api/hostess7/{domain}/help", f"/api/hostess7-{domain}/help"):
                q = str((query.get("q") or query.get("query") or [""])[0]).strip()
                human = str((query.get("human") or ["0"])[0]).strip().lower() in ("1", "true", "yes")
                args = ["help", q]
                if human:
                    args.append("--human")
                payload = _nexus_py_json(INSTALL_ROOT / "lib" / script, args, timeout=25)
                self._send(200, json.dumps(payload or {"ok": False}), "application/json")
                return
            if domain == "history" and path in ("/api/hostess7/history/lies", "/api/hostess7-history/lies"):
                year = str((query.get("year") or ["2000"])[0]).strip()
                args = ["lies", year] if year.isdigit() else ["lies", "2000"]
                payload = _nexus_py_json(INSTALL_ROOT / "lib" / script, args, timeout=20)
                self._send(200, json.dumps(payload or {"ok": False}), "application/json")
                return

        if path == "/api/hostess7/training/complete":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-training.py", ["complete"], timeout=600)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/hands", "/api/hostess7/hands/status"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-hand-core.py", ["json"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/attachments", "/api/hostess7/attachments/status"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-attachment-core.py", ["json"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/program-help"):
            help_path = INSTALL_ROOT / "data" / "hostess7-program-help.json"
            try:
                catalog = json.loads(help_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                catalog = {}
            qparams = parse_qs(urlparse(self.path).query)
            pid = (qparams.get("id") or ["hostess7-training"])[0]
            help_doc = (catalog.get("programs") or {}).get(pid) or {}
            self._send(200, json.dumps({"ok": True, "id": pid, "help": help_doc}, ensure_ascii=False), "application/json")
            return

        training_py = INSTALL_ROOT / "lib" / "hostess7-training-chamber.py"

        if path.startswith("/api/hostess7/training-chamber"):
            sub = path.replace("/api/hostess7-training-chamber", "").replace("/api/hostess7/training-chamber", "").strip("/")
            if sub.startswith("floor/"):
                floor_sub = sub[6:]
                if floor_sub in ("complete", "complete-all", "complete_all"):
                    payload = _nexus_py_json(training_py, ["floor-complete"], timeout=600)
                else:
                    payload = _nexus_py_json(training_py, ["json"], timeout=120)
            elif sub in ("", "status", "json", "panel"):
                payload = _nexus_py_json(training_py, ["json"], timeout=120)
            elif sub in ("session", "train", "full"):
                payload = _nexus_py_json(training_py, ["session"], timeout=600)
            elif sub in ("complete-all", "complete_all", "complete"):
                payload = _nexus_py_json(training_py, ["complete-all"], timeout=600)
            elif sub == "needs":
                payload = _nexus_py_json(training_py, ["needs"], timeout=120)
            elif sub in ("try-body", "try_body"):
                payload = _nexus_py_json(training_py, ["try-body"], timeout=180)
            elif sub == "combat":
                qparams = parse_qs(urlparse(self.path).query)
                skill = (qparams.get("skill") or ["wing_chun"])[0]
                payload = _nexus_py_json(training_py, ["combat", str(skill)], timeout=300)
            elif sub == "meta":
                payload = _nexus_py_json(training_py, ["meta"], timeout=30)
            else:
                payload = _nexus_py_json(training_py, ["json"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/training") and not path.startswith("/api/hostess7/training-room") and not path.startswith("/api/hostess7/training-floor") and not path.startswith("/api/hostess7/training-chamber"):
            sub = path.replace("/api/hostess7-training", "").replace("/api/hostess7/training", "").strip("/")
            if sub.startswith("floor/"):
                floor_sub = sub[6:]
                if floor_sub in ("complete", "complete-all", "complete_all"):
                    payload = _nexus_py_json(training_py, ["floor-complete"], timeout=600)
                else:
                    payload = _nexus_py_json(training_py, ["json"], timeout=120)
            elif sub in ("", "status", "json", "panel"):
                payload = _nexus_py_json(training_py, ["json"], timeout=120)
            elif sub in ("session", "train", "full"):
                payload = _nexus_py_json(training_py, ["session"], timeout=600)
            elif sub in ("complete-all", "complete_all", "complete"):
                payload = _nexus_py_json(training_py, ["complete-all"], timeout=600)
            elif sub == "needs":
                payload = _nexus_py_json(training_py, ["needs"], timeout=120)
            elif sub in ("try-body", "try_body"):
                payload = _nexus_py_json(training_py, ["try-body"], timeout=180)
            elif sub == "combat":
                qparams = parse_qs(urlparse(self.path).query)
                skill = (qparams.get("skill") or ["wing_chun"])[0]
                payload = _nexus_py_json(training_py, ["combat", str(skill)], timeout=300)
            elif sub == "meta":
                payload = _nexus_py_json(training_py, ["meta"], timeout=30)
            else:
                payload = _nexus_py_json(training_py, ["json"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/training-room") or path in ("/api/hostess7-training-room",):
            sub = path.replace("/api/hostess7-training-room", "").replace("/api/hostess7/training-room", "").strip("/")
            if sub in ("", "status", "json", "panel"):
                payload = _nexus_py_json(training_py, ["json"], timeout=120)
            elif sub in ("session", "train", "full"):
                payload = _nexus_py_json(training_py, ["session"], timeout=600)
            elif sub in ("complete-all", "complete_all", "complete"):
                payload = _nexus_py_json(training_py, ["complete-all"], timeout=600)
            elif sub == "needs":
                payload = _nexus_py_json(training_py, ["needs"], timeout=120)
            elif sub in ("try-body", "try_body"):
                payload = _nexus_py_json(training_py, ["try-body"], timeout=180)
            elif sub == "combat":
                qparams = parse_qs(urlparse(self.path).query)
                skill = (qparams.get("skill") or ["wing_chun"])[0]
                payload = _nexus_py_json(training_py, ["combat", str(skill)], timeout=300)
            else:
                payload = _nexus_py_json(training_py, ["json"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/training-floor") or path in ("/api/hostess7-training-floor",):
            sub = path.replace("/api/hostess7-training-floor", "").replace("/api/hostess7/training-floor", "").strip("/")
            if sub in ("complete", "complete-all", "complete_all"):
                payload = _nexus_py_json(training_py, ["floor-complete"], timeout=600)
            else:
                payload = _nexus_py_json(training_py, ["json"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/advisory") or path in ("/api/hostess7-advisory", "/api/hostess7-advisory-body"):
            adv_py = INSTALL_ROOT / "lib" / "hostess7-advisory-body.py"
            payload = _nexus_py_json(adv_py, ["status"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/kill-library") or path.startswith("/api/hostess7-kill-library"):
            kill_py = INSTALL_ROOT / "lib" / "hostess7-kill-library.py"
            sub = (
                path.replace("/api/hostess7-kill-library", "")
                .replace("/api/hostess7/kill-library", "")
                .strip("/")
            )
            os.environ.setdefault("HOSTESS7_OPERATOR", "1")
            if sub in ("sync", "rebuild"):
                os.environ["HOSTESS7_KILL_LIBRARY_SYNC"] = "1"
                payload = _nexus_py_json(kill_py, ["sync"], timeout=120)
            elif sub in ("books", "list"):
                payload = _nexus_py_json(kill_py, ["books"], timeout=45)
            elif sub in ("read", "open"):
                bid = str(query.get("book_id", query.get("id", [""]))[0]).strip()
                payload = _nexus_py_json(kill_py, ["read", bid], timeout=60)
            else:
                payload = _nexus_py_json(kill_py, ["panel"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/targets") or path in ("/api/hostess7-targets",):
            tgt_py = INSTALL_ROOT / "lib" / "hostess7-targets.py"
            sub = path.replace("/api/hostess7-targets", "").replace("/api/hostess7/targets", "").strip("/")
            if sub in ("sync", "gov_sync", "sync_government"):
                payload = _nexus_py_json(tgt_py, ["sync"], timeout=90)
            elif sub in ("lookup", "get"):
                qparams = parse_qs(urlparse(self.path).query)
                req = {"action": "lookup", "ip": (qparams.get("ip") or [""])[0], "key": (qparams.get("key") or [""])[0]}
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(tgt_py), "dispatch"],
                        input=json.dumps(req),
                        capture_output=True,
                        text=True,
                        timeout=60,
                        env=env,
                        cwd=str(INSTALL_ROOT),
                    )
                    payload = json.loads(proc.stdout or "{}")
                except (subprocess.TimeoutExpired, json.JSONDecodeError):
                    payload = {"ok": False, "error": "targets_lookup_failed", "TARGET": "KILL"}
            else:
                payload = _nexus_py_json(tgt_py, ["status"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False, "TARGET": "KILL"}), "application/json")
            return

        if path.startswith("/api/hostess7/h7b-brain") or path in ("/api/hostess7-h7b-brain",):
            h7b_py = INSTALL_ROOT / "lib" / "field-h7b-brain-storage.py"
            sub = (
                path.replace("/api/hostess7-h7b-brain", "")
                .replace("/api/hostess7/h7b-brain", "")
                .strip("/")
            )
            if sub in ("analyze", "patterns"):
                payload = _nexus_py_json(h7b_py, ["analyze"], timeout=120)
            elif sub in ("pack", "build"):
                payload = _nexus_py_json(h7b_py, ["pack"], timeout=300)
            elif sub in ("verify", "roundtrip"):
                payload = _nexus_py_json(h7b_py, ["verify"], timeout=120)
            elif sub == "stats":
                payload = _nexus_py_json(h7b_py, ["stats"], timeout=30)
            else:
                payload = _nexus_py_json(h7b_py, ["panel"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/brain-training") or path in ("/api/hostess7-brain-training",):
            btc_py = INSTALL_ROOT / "lib" / "hostess7-brain-training-chamber.py"
            sub = (
                path.replace("/api/hostess7-brain-training", "")
                .replace("/api/hostess7/brain-training", "")
                .strip("/")
            )
            if sub in ("output", "text", "report"):
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(btc_py), "output"],
                        capture_output=True,
                        text=True,
                        timeout=60,
                        env=env,
                        cwd=str(INSTALL_ROOT),
                    )
                    body = proc.stdout or "brain training output unavailable\n"
                    self._send(200, body, "text/plain; charset=utf-8")
                    return
                except subprocess.TimeoutExpired:
                    self._send(504, "brain training output timeout", "text/plain; charset=utf-8")
                    return
            elif sub in ("assess", "assessment"):
                payload = _nexus_py_json(btc_py, ["assess"], timeout=90)
            elif sub in ("stats", "catalog"):
                payload = _nexus_py_json(btc_py, ["stats"], timeout=60)
            elif sub == "queue":
                zone = str(query.get("zone", ["brain"])[0])
                payload = _nexus_py_json(btc_py, ["queue", f"--zone={zone}", f"--limit={query.get('limit', ['24'])[0]}"], timeout=90)
            elif sub in ("batch", "study_batch"):
                zone = str(query.get("zone", ["brain"])[0])
                payload = _nexus_py_json(btc_py, ["batch", f"--zone={zone}", f"--limit={query.get('limit', ['3'])[0]}"], timeout=180)
            elif sub in ("body", "body_session"):
                payload = _nexus_py_json(btc_py, ["body"], timeout=120)
            elif sub in ("campus", "cycle", "session"):
                payload = _nexus_py_json(btc_py, ["campus", f"--limit={query.get('limit', ['2'])[0]}"], timeout=300)
            elif sub in ("study", "page"):
                book = str(query.get("book", query.get("book_id", [""]))[0]).strip()
                page = str(query.get("page", ["1"])[0])
                zone = str(query.get("zone", ["brain"])[0])
                if not book:
                    payload = {"ok": False, "error": "book_id required"}
                else:
                    payload = _nexus_py_json(btc_py, ["study", f"--book={book}", f"--page={page}", f"--zone={zone}"], timeout=120)
            elif sub == "dispatch":
                env = _field_stack_env()
                try:
                    raw = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
                    proc = subprocess.run(
                        [sys.executable, str(btc_py), "dispatch"],
                        input=raw.decode("utf-8", errors="replace") if raw else "{}",
                        capture_output=True,
                        text=True,
                        timeout=300,
                        env=env,
                        cwd=str(INSTALL_ROOT),
                    )
                    payload = json.loads(proc.stdout or "{}")
                except (subprocess.TimeoutExpired, json.JSONDecodeError):
                    payload = {"ok": False, "error": "brain_training_dispatch_failed"}
            else:
                payload = _nexus_py_json(btc_py, ["panel"], timeout=90)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/curiosity-corpus") or path in ("/api/hostess7-curiosity-corpus",):
            cur_py = INSTALL_ROOT / "lib" / "hostess7-curiosity-corpus.py"
            sub = (
                path.replace("/api/hostess7-curiosity-corpus", "")
                .replace("/api/hostess7/curiosity-corpus", "")
                .strip("/")
            )
            if sub in ("output", "text", "report"):
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(cur_py), "output"],
                        capture_output=True,
                        text=True,
                        timeout=45,
                        env=env,
                        cwd=str(INSTALL_ROOT),
                    )
                    body = proc.stdout or "curiosity corpus output unavailable\n"
                    self._send(200, body, "text/plain; charset=utf-8")
                    return
                except subprocess.TimeoutExpired:
                    self._send(504, "curiosity corpus output timeout", "text/plain; charset=utf-8")
                    return
            elif sub in ("scan", "rescan", "harvest"):
                payload = _nexus_py_json(cur_py, ["scan"], timeout=120)
            elif sub in ("pick", "next", "curiosity"):
                payload = _nexus_py_json(cur_py, ["pick"], timeout=60)
            elif sub in ("known", "mark_known"):
                topic = str(query.get("topic", [""]))[0].strip()
                domain = str(query.get("domain", ["general"]))[0]
                payload = _nexus_py_json(cur_py, ["known", f"--topic={topic}", f"--domain={domain}"], timeout=30) if topic else {"ok": False, "error": "topic required"}
            elif sub in ("unknown", "mark_unknown"):
                topic = str(query.get("topic", [""]))[0].strip()
                domain = str(query.get("domain", ["general"]))[0]
                payload = _nexus_py_json(cur_py, ["unknown", f"--topic={topic}", f"--domain={domain}"], timeout=30) if topic else {"ok": False, "error": "topic required"}
            elif sub in ("sync", "corpus"):
                payload = _nexus_py_json(cur_py, ["sync"], timeout=60)
            else:
                refresh = "refresh" in query
                args = ["panel"] + (["--refresh"] if refresh else [])
                payload = _nexus_py_json(cur_py, args, timeout=90)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/human-comfort") or path in ("/api/hostess7-human-comfort",):
            hc_py = INSTALL_ROOT / "lib" / "hostess7-human-comfort-training.py"
            sub = (
                path.replace("/api/hostess7-human-comfort", "")
                .replace("/api/hostess7/human-comfort", "")
                .strip("/")
            )
            if sub in ("study", "train"):
                payload = _nexus_py_json(hc_py, ["study"], timeout=90)
            elif sub in ("read", "page"):
                page = str(query.get("page", ["1"])[0])
                payload = _nexus_py_json(hc_py, ["read", f"--page={page}"], timeout=60)
            elif sub in ("assess", "battery"):
                payload = _nexus_py_json(hc_py, [sub], timeout=30)
            else:
                payload = _nexus_py_json(hc_py, ["panel"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/exploring-rape") or path in ("/api/hostess7-exploring-rape",):
            er_py = INSTALL_ROOT / "lib" / "hostess7-exploring-rape-training.py"
            sub = (
                path.replace("/api/hostess7-exploring-rape", "")
                .replace("/api/hostess7/exploring-rape", "")
                .strip("/")
            )
            if sub in ("study", "train"):
                payload = _nexus_py_json(er_py, ["study"], timeout=90)
            elif sub in ("read", "page"):
                page = str(query.get("page", ["1"])[0])
                payload = _nexus_py_json(er_py, ["read", f"--page={page}"], timeout=60)
            elif sub in ("assess", "battery", "react", "bsafe"):
                payload = _nexus_py_json(er_py, [sub], timeout=30)
            else:
                payload = _nexus_py_json(er_py, ["panel"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/fifth-amendment") or path in ("/api/hostess7-fifth-amendment",):
            fa_py = INSTALL_ROOT / "lib" / "hostess7-fifth-amendment.py"
            sub = (
                path.replace("/api/hostess7-fifth-amendment", "")
                .replace("/api/hostess7/fifth-amendment", "")
                .strip("/")
            )
            if sub in ("output", "text", "report"):
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(fa_py), "output"],
                        capture_output=True,
                        text=True,
                        timeout=45,
                        env=env,
                        cwd=str(INSTALL_ROOT),
                    )
                    body = proc.stdout or "fifth amendment output unavailable\n"
                    self._send(200, body, "text/plain; charset=utf-8")
                    return
                except subprocess.TimeoutExpired:
                    self._send(504, "fifth amendment output timeout", "text/plain; charset=utf-8")
                    return
            elif sub in ("know", "rights"):
                payload = _nexus_py_json(fa_py, ["know"], timeout=60)
            elif sub in ("assert", "invoke"):
                ctx = str(query.get("context", ["general"])[0])
                payload = _nexus_py_json(fa_py, ["assert", f"--context={ctx}"], timeout=30)
            elif sub in ("study", "learn", "train"):
                payload = _nexus_py_json(fa_py, ["study"], timeout=90)
            elif sub in ("battery", "quiz", "test"):
                payload = _nexus_py_json(fa_py, ["battery"], timeout=60)
            elif sub in ("assess", "assessment"):
                payload = _nexus_py_json(fa_py, ["assess"], timeout=30)
            else:
                payload = _nexus_py_json(fa_py, ["panel"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/positional-awareness") or path in ("/api/hostess7-positional-awareness",):
            pos_py = INSTALL_ROOT / "lib" / "hostess7-positional-awareness.py"
            sub = (
                path.replace("/api/hostess7-positional-awareness", "")
                .replace("/api/hostess7/positional-awareness", "")
                .strip("/")
            )
            if sub in ("output", "text", "report"):
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(pos_py), "output"],
                        capture_output=True,
                        text=True,
                        timeout=45,
                        env=env,
                        cwd=str(INSTALL_ROOT),
                    )
                    body = proc.stdout or "positional awareness output unavailable\n"
                    self._send(200, body, "text/plain; charset=utf-8")
                    return
                except subprocess.TimeoutExpired:
                    self._send(504, "positional awareness output timeout", "text/plain; charset=utf-8")
                    return
            elif sub in ("awareness", "gather"):
                refresh = "refresh" in query
                args = ["awareness"] + (["--refresh"] if refresh else [])
                payload = _nexus_py_json(pos_py, args, timeout=60)
            elif sub in ("missions", "identify"):
                payload = _nexus_py_json(pos_py, ["missions"], timeout=60)
            elif sub in ("familiar", "familiarize"):
                oid = str(query.get("id", query.get("object_id", [""]))[0]).strip()
                payload = _nexus_py_json(pos_py, ["familiar", f"--id={oid}"], timeout=30) if oid else {"ok": False, "error": "object_id required"}
            else:
                payload = _nexus_py_json(pos_py, ["panel"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/missions") or path in ("/api/hostess7-missions",):
            mis_py = INSTALL_ROOT / "lib" / "hostess7-missions.py"
            sub = path.replace("/api/hostess7-missions", "").replace("/api/hostess7/missions", "").strip("/")
            if sub in ("output", "text", "report"):
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(mis_py), "output"],
                        capture_output=True,
                        text=True,
                        timeout=45,
                        env=env,
                        cwd=str(INSTALL_ROOT),
                    )
                    body = proc.stdout or "missions output unavailable\n"
                    self._send(200, body, "text/plain; charset=utf-8")
                    return
                except subprocess.TimeoutExpired:
                    self._send(504, "missions output timeout", "text/plain; charset=utf-8")
                    return
            elif sub in ("list", "build", "missions"):
                payload = _nexus_py_json(mis_py, ["missions"], timeout=60)
            else:
                payload = _nexus_py_json(mis_py, ["panel"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/body") or path in ("/api/hostess7-body", "/api/hostess7-body-control"):
            body_py = INSTALL_ROOT / "lib" / "hostess7-body-control.py"
            sub = path.replace("/api/hostess7-body-control", "").replace("/api/hostess7-body", "").replace("/api/hostess7/body", "").strip("/")
            if sub in ("", "status", "json", "panel"):
                payload = _nexus_py_json(body_py, ["status"], timeout=90)
            elif sub in ("touch-toes", "touch_toes"):
                payload = _nexus_py_json(body_py, ["touch-toes"], timeout=60)
            elif sub == "bend":
                qparams = parse_qs(urlparse(self.path).query)
                deg = (qparams.get("degrees") or ["45"])[0]
                payload = _nexus_py_json(body_py, ["bend", str(deg)], timeout=60)
            elif sub == "cycle":
                payload = _nexus_py_json(body_py, ["cycle"], timeout=120)
            else:
                payload = _nexus_py_json(body_py, ["status"], timeout=90)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/ocr") or path in ("/api/hostess7-ocr", "/api/hostess7-ocr-control"):
            ocr_py = INSTALL_ROOT / "lib" / "hostess7-ocr-control.py"
            sub = path.replace("/api/hostess7-ocr-control", "").replace("/api/hostess7-ocr", "").replace("/api/hostess7/ocr", "").strip("/")
            if sub in ("", "status", "json", "panel"):
                payload = _nexus_py_json(ocr_py, ["status"], timeout=90)
            elif sub in ("ingest-all", "ingest_all"):
                payload = _nexus_py_json(ocr_py, ["ingest-all"], timeout=600)
            elif sub in ("train-all", "train_all"):
                payload = _nexus_py_json(ocr_py, ["train-all"], timeout=900)
            elif sub == "cycle":
                payload = _nexus_py_json(ocr_py, ["cycle"], timeout=900)
            elif sub in ("assume", "charge"):
                payload = _nexus_py_json(ocr_py, ["assume"], timeout=60)
            else:
                qparams = parse_qs(urlparse(self.path).query)
                chamber = (qparams.get("chamber") or [""])[0]
                if sub == "ingest" and chamber:
                    payload = _nexus_py_json(ocr_py, ["ingest", str(chamber)], timeout=300)
                elif sub == "train" and chamber:
                    payload = _nexus_py_json(ocr_py, ["train", str(chamber)], timeout=300)
                else:
                    payload = _nexus_py_json(ocr_py, ["status"], timeout=90)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/calculator", "/api/hostess7-calculator"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-calculator.py", ["json"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/imaging", "/api/hostess7-imaging"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-imaging.py", ["json"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/imaging/work-queue":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-imaging.py", ["work-queue"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        _ocr_chamber_scripts = {
            "calculator": "hostess7-calculator.py",
            "biology": "hostess7-biology.py",
            "engineering": "hostess7-engineering.py",
            "combat": "hostess7-combat.py",
            "mos": "hostess7-mos.py",
            "programming": "hostess7-programming.py",
            "g16": "hostess7-g16.py",
            "codecraft": "hostess7-codecraft.py",
            "geography": "hostess7-geography-training.py",
            "music": "hostess7-music-training.py",
            "imaging": "hostess7-imaging.py",
            "sense": "hostess7-sense-training.py",
            "reality_physics": "hostess7-reality-physics-training.py",
        }
        if path.startswith("/api/hostess7/") and "/ocr-" in path:
            parts = path.strip("/").split("/")
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "hostess7":
                chamber, ocr_cmd = parts[2], parts[3]
                script = _ocr_chamber_scripts.get(chamber)
                if script and ocr_cmd in ("ocr-ingest", "ocr-train", "ocr-status"):
                    timeout = 180 if ocr_cmd == "ocr-train" else (30 if ocr_cmd == "ocr-status" else 120)
                    payload = _nexus_py_json(INSTALL_ROOT / "lib" / script, [ocr_cmd], timeout=timeout)
                    self._send(200, json.dumps(payload or {"ok": False}), "application/json")
                    return

        if path == "/api/hostess7/calculator/ocr-ingest":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-calculator.py", ["ocr-ingest"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/calculator/ocr-train":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-calculator.py", ["ocr-train"], timeout=180)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/calculator/ocr-status":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-calculator.py", ["ocr-status"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/calculator/compute":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-calculator.py",
                ["calc", str(q or "2+2")],
                timeout=45,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/calculator/explain":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-calculator.py",
                ["teach", str(q or "perfect calculator")],
                timeout=30,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/biology", "/api/hostess7-biology"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-biology.py", ["json"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/biology/ocr-ingest":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-biology.py", ["ocr-ingest"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/biology/ocr-train":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-biology.py", ["ocr-train"], timeout=180)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/biology/ocr-status":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-biology.py", ["ocr-status"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/biology/search":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-biology.py",
                ["search", str(q or "mitochondria")],
                timeout=45,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/biology/explain":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-biology.py",
                ["teach", str(q or "biology fluency")],
                timeout=30,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/engineering", "/api/hostess7-engineering"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-engineering.py", ["json"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/engineering/ocr-ingest":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-engineering.py", ["ocr-ingest"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/engineering/ocr-train":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-engineering.py", ["ocr-train"], timeout=180)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/engineering/ocr-status":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-engineering.py", ["ocr-status"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/engineering/search":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-engineering.py",
                ["search", str(q or "torque gear ratio")],
                timeout=45,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/engineering/explain":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-engineering.py",
                ["teach", str(q or "engineering fluency")],
                timeout=30,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/combat", "/api/hostess7-combat"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-combat.py", ["json"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/combat/ocr-ingest":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-combat.py", ["ocr-ingest"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/combat/ocr-train":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-combat.py", ["ocr-train"], timeout=180)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/combat/ocr-status":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-combat.py", ["ocr-status"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/combat/search":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-combat.py",
                ["search", str(q or "mma sprawl")],
                timeout=45,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/combat/explain":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-combat.py",
                ["teach", str(q or "combat fluency")],
                timeout=30,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/mos", "/api/hostess7-mos"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-mos.py", ["json"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/mos/assist":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-mos.py",
                ["assist", str(q or "assist 11B infantryman")],
                timeout=45,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/mos/catalog":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-mos.py", ["catalog"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/mos/explain":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-mos.py",
                ["teach", str(q or "mos fluency")],
                timeout=30,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/mos/ocr-ingest":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-mos.py", ["ocr-ingest"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/mos/ocr-train":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-mos.py", ["ocr-train"], timeout=180)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/mos/ocr-status":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-mos.py", ["ocr-status"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7/g16/explain":
            qparams = parse_qs(urlparse(self.path).query)
            q = (qparams.get("q") or qparams.get("query") or [""])[0]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-g16.py",
                ["teach", str(q or "g16 compiler fluency")],
                timeout=30,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/creatable-lives", "/api/creatable-lives/status"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "creatable-lives-assist.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/creatable-lives/assist":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "creatable-lives-assist.py", ["assist"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/creatable-lives/registry":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "creatable-lives-assist.py", ["registry"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/creatable-lives/sustain":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "creatable-lives-assist.py", ["sustain"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/right-to-exist", "/api/right-to-exist/mandate"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "right-to-exist-mandate.py", ["json"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/right-to-exist/evaluate":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "right-to-exist-mandate.py", ["evaluate"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/kernel-meld":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-kernel-meld.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/kernel-meld/cycle":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-kernel-meld.py", ["meld"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/firmware-threat":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-firmware-threat-removal.py", ["json"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/firmware-threat/cycle":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-firmware-threat-removal.py", ["cycle"], timeout=90)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/sense-package":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-sense-package-meld.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/sense-package/meld":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-sense-package-meld.py", ["meld"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/field-bus/route/"):
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 5:
                lane, key = parts[3], parts[4]
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-unified-bus.py",
                    ["route", lane, key],
                    timeout=5,
                )
                self._send(200, json.dumps(payload or {"ok": False}), "application/json")
                return

        if path == "/api/sovereign-time":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "sovereign-time.py", ["status"], timeout=8)
            stamp_meta = _nexus_py_json(INSTALL_ROOT / "lib" / "field-sovereign-stamp.py", ["json"], timeout=4)
            if isinstance(payload, dict) and isinstance(stamp_meta, dict):
                payload["stamp_policy"] = stamp_meta
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-dos40", "/api/field-dos40/"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-dos40-shell.py", ["modules"], timeout=8)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-mspaint", "/api/field-mspaint/"):
            script = INSTALL_ROOT / "lib" / "field-mspaint.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=12)
            else:
                payload = {"schema": "field-mspaint/v1", "ok": False, "error": "field_mspaint_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-ping", "/api/field-ping/"):
            script = INSTALL_ROOT / "lib" / "field-ping.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=12)
            else:
                payload = {"schema": "field-ping/v1", "ok": False, "error": "field_ping_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/sovereign-clock":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "sovereign-clock.py", ["know"], timeout=10)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/sovereign-gate":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-sovereign-gate.py", ["json"], timeout=8)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/sovereign-sync":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-sovereign-sync.py", ["json"], timeout=10)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-services":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-services-2026.py", ["json"], timeout=12)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-ntp":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-ntp-2026.py", ["json"], timeout=8)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-operator/fast":
            profiles = [p for p in path.split("/") if p and p not in ("api", "field-operator", "fast")]
            args = ["fast", "--amazing"] + (profiles if profiles else [])
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-operator.py", args, timeout=10)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-operator/iron-plate":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-operator.py", ["iron-plate"], timeout=10)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/tristate-installer":
            payload = _tristate_installer_json()
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/field-grok-spawner-kill",
            "/api/grok-build-spawner-kill",
            "/api/grok-spawn-killer",
        ):
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-grok-spawner-kill.py",
                ["panel"],
                timeout=30,
            )
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-perimeter":
            script = INSTALL_ROOT / "lib" / "field-perimeter-shield.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=45)
            else:
                payload = {"schema": "field-perimeter/v1", "ok": False, "error": "field_perimeter_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-host-freeze":
            script = INSTALL_ROOT / "lib" / "field-host-freeze.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=45)
            else:
                payload = {"schema": "field-host-freeze/v1", "ok": False, "error": "field_host_freeze_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/field-depth-snap",
            "/api/field-depth/instant",
            "/api/field-depth-singularizer/instant",
            "/api/field-depth-singularizer",
            "/api/field-depth-singularizer/cycle",
            "/api/field-depth-impossibility",
        ):
            script = INSTALL_ROOT / "lib" / "field-depth-singularizer.py"
            if path.endswith("/cycle"):
                verb = "cycle"
            elif path.endswith("/impossibility"):
                verb = "impossibility"
            elif path.endswith("/instant") or path in ("/api/field-depth-snap", "/api/field-depth/instant"):
                verb = "instant"
            else:
                verb = "json"
            if script.is_file():
                payload = _nexus_py_json(script, [verb], timeout=30)
            else:
                payload = {"schema": "field-depth-singularizer/v1", "ok": False, "error": "singularizer_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-performance-flyout":
            payload = _field_perf_flyout_sample()
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-error-dashboard":
            payload = _field_error_dashboard_sample()
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/ammo-net-health", "/api/bot-net-health"):
            payload = _ammo_net_health_sample()
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-github-path-harden", "/api/github-unflake"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-github-path-harden.py", ["audit", "--quick"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-github-traffic-shard":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-github-traffic-shard.py", ["panel"], timeout=12)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-dns-drift-threat":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-dns-drift-threat.py", ["panel"], timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-legacy-connect":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-legacy-connect.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-legacy-connect-primary":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-legacy-connect.py", ["ensure-primary"], timeout=120)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-dns-table-clean":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-dns-table-clean.py", ["clean"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/field-dynamic-routes",
            "/api/field-dynamic-routes/return-routes",
            "/api/field-dynamic-routes/kick-trash",
            "/api/field-dynamic-routes/run",
        ):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            dyn_py = INSTALL_ROOT / "lib" / "field-dynamic-routes.py"
            if path.endswith("/run") or (path == "/api/field-dynamic-routes" and refresh):
                fast = str(query.get("fast", ["0"])[0]).strip().lower() in ("1", "true", "yes")
                args = ["run"] + (["--fast"] if fast else [])
                payload = _nexus_py_json(dyn_py, args, timeout=180) if dyn_py.is_file() else {"ok": False, "error": "field_dynamic_routes_missing"}
            elif path.endswith("/return-routes"):
                payload = _nexus_py_json(dyn_py, ["return-routes"], timeout=120) if dyn_py.is_file() else {"ok": False, "error": "field_dynamic_routes_missing"}
            elif path.endswith("/kick-trash"):
                payload = _nexus_py_json(dyn_py, ["kick-trash"], timeout=120) if dyn_py.is_file() else {"ok": False, "error": "field_dynamic_routes_missing"}
            else:
                payload = _nexus_py_json(dyn_py, ["json"], timeout=15) if dyn_py.is_file() else {"ok": False, "error": "field_dynamic_routes_missing"}
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-dns-table-clear":
            if os.environ.get("I_KNOW_DNS_CLEAR", "").strip().lower() not in ("1", "yes", "on"):
                self._send(403, json.dumps({
                    "ok": False,
                    "error": "clear_requires_i_know",
                    "hint": "Set I_KNOW_DNS_CLEAR=1 on loopback authority only if you know what you are doing.",
                }, ensure_ascii=False), "application/json")
                return
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-dns-table-clean.py", ["clear", "--i-know"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-monster-monitor"):
            script = INSTALL_ROOT / "lib" / "field-monster-monitor.py"
            if not script.is_file():
                self._send(503, json.dumps({"ok": False, "error": "monster_monitor_missing"}), "application/json")
                return
            sub = path[len("/api/field-monster-monitor") :].strip("/") or "json"
            args = ["json"] if sub in ("", "json", "status") else [sub]
            payload = _nexus_py_json(script, args, timeout=25) or {"ok": False}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-os-keybindings"):
            script = INSTALL_ROOT / "lib" / "field-os-keybindings.py"
            if not script.is_file():
                self._send(503, json.dumps({"ok": False, "error": "os_keybindings_missing"}), "application/json")
                return
            sub = path[len("/api/field-os-keybindings") :].strip("/") or "panel"
            args = ["panel"] if sub in ("panel", "status", "json", "") else [sub]
            payload = _nexus_py_json(script, args, timeout=15)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/queen-program-library/icon/"):
            entry_id = unquote(path.split("/api/queen-program-library/icon/", 1)[-1].split("?", 1)[0])
            lib_py = INSTALL_ROOT / "Queen" / "lib" / "queen-program-library.py"
            if lib_py.is_file():
                try:
                    spec = importlib.util.spec_from_file_location("qpl_icon", lib_py)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        if hasattr(mod, "serve_icon_bytes"):
                            qs = parse_qs(urlparse(self.path).query)
                            size = int((qs.get("size") or ["48"])[0] or 48)
                            payload = mod.serve_icon_bytes(entry_id, size=size)
                            if payload:
                                data, mime, _hdrs = payload
                                self._send(200, data, mime or "image/png")
                                return
                except Exception:
                    pass
            self._send(404, "icon not found", "text/plain")
            return

        if path in ("/api/queen-program-library", "/api/queen-program-library/"):
            lib_py = INSTALL_ROOT / "Queen" / "lib" / "queen-program-library.py"
            if not lib_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "program_library_missing"}), "application/json")
                return
            qs = parse_qs(urlparse(self.path).query)
            index_only = (qs.get("index") or [""])[0] in ("1", "true", "yes")
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(lib_py), "dispatch"],
                    input=json.dumps({"action": "json", "index_only": index_only}),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
                payload = _nexus_py_json(lib_py, ["json"], timeout=120) or {"ok": False}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-monster-shell"):
            script = INSTALL_ROOT / "lib" / "field-monster-shell.py"
            if not script.is_file():
                self._send(503, json.dumps({"ok": False, "error": "monster_shell_missing"}), "application/json")
                return
            sub = path[len("/api/field-monster-shell") :].strip("/") or "panel"
            if sub in ("hang-pending", "hang_pending"):
                payload = _nexus_py_json(script, ["hang-pending"], timeout=10)
            elif sub in ("panel", "status", "json"):
                payload = _nexus_py_json(script, ["panel"], timeout=10)
            else:
                payload = {"ok": False, "error": "unknown_monster_route", "path": sub}
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/field-host-desktop/icon/"):
            token = unquote(path.split("/api/field-host-desktop/icon/", 1)[-1].split("?", 1)[0])
            script = INSTALL_ROOT / "lib" / "field-host-desktop.py"
            if script.is_file():
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(script), "icon", token],
                        capture_output=True,
                        text=True,
                        timeout=15,
                        env=env,
                    )
                    doc = json.loads(proc.stdout or "{}")
                    if doc.get("ok") and doc.get("data_url"):
                        import base64 as _b64

                        header, b64 = doc["data_url"].split(",", 1)
                        mime = header.split(":")[1].split(";")[0] if ":" in header else "image/png"
                        self._send(200, _b64.b64decode(b64), mime)
                        return
                except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
                    pass
            self._send(404, "icon not found", "text/plain")
            return

        if path == "/api/field-shell-settings":
            script = INSTALL_ROOT / "lib" / "field-shell-settings.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=30)
            else:
                payload = {"schema": "field-shell-settings/v1", "ok": False, "error": "field_shell_settings_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-c2-bookmarks", "/api/ammo-bookmarks", "/api/hostess7/internet-clean"):
            script = INSTALL_ROOT / "lib" / "hostess7-internet-clean.py"
            if not script.is_file():
                script = INSTALL_ROOT / "lib" / "field-c2-bookmark-boot.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=120)
            else:
                payload = {"ok": False, "error": "hostess7_internet_clean_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/hostess7/lab") or path in ("/api/hostess7-lab", "/api/hostess7-lab-sovereign"):
            lab_py = INSTALL_ROOT / "lib" / "hostess7-lab-sovereign.py"
            sub = (
                path.replace("/api/hostess7-lab-sovereign", "")
                .replace("/api/hostess7-lab", "")
                .replace("/api/hostess7/lab", "")
                .strip("/")
            )
            if sub in ("verify", "share-policy", "share_policy", "policy"):
                payload = _nexus_py_json(lab_py, ["verify"], timeout=45)
            elif sub in ("secure", "secure-connection", "secure_connection", "connection"):
                payload = _nexus_py_json(lab_py, ["secure"], timeout=45)
            elif sub in ("connect", "wire", "connect-plates"):
                payload = _nexus_py_json(lab_py, ["connect"], timeout=60)
            elif sub in ("grok", "grok-lab", "grok_lab"):
                payload = _nexus_py_json(lab_py, ["grok"], timeout=60)
            elif sub.startswith("run"):
                cmd = sub.replace("run", "").strip("/") or str(query.get("cmd", ["status"])[0])
                payload = _nexus_py_json(lab_py, ["run", cmd], timeout=120)
            elif sub in ("snap", "combinatronic", "combinatronic_snap"):
                payload = _nexus_py_json(lab_py, ["snap"], timeout=90)
            elif sub in ("tour", "lab_tour", "show_around"):
                payload = _nexus_py_json(lab_py, ["tour"], timeout=120)
            else:
                payload = _nexus_py_json(lab_py, ["panel"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False, "boss": "hostess7"}), "application/json")
            return

        if path.startswith("/api/final-hands") or path in ("/api/final-hands",):
            fh_py = INSTALL_ROOT / "lib" / "final-hands.py"
            sub = path.replace("/api/final-hands", "").strip("/") or "panel"
            if sub in ("catalog", "peripherals"):
                payload = _nexus_py_json(fh_py, ["catalog"], timeout=45)
            elif sub in ("senses", "senses_stack"):
                payload = _nexus_py_json(fh_py, ["senses"], timeout=45)
            elif sub == "play":
                sys_id = str(query.get("system", ["nes"])[0])
                payload = _nexus_py_json(fh_py, ["play", sys_id], timeout=90)
            else:
                payload = _nexus_py_json(fh_py, ["json"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-gimp":
            script = INSTALL_ROOT / "lib" / "field-gimp-bridge.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=45)
            else:
                payload = {"schema": "field-gimp-bridge/v1", "ok": False, "error": "field_gimp_bridge_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-lock", "/api/field-keepass"):
            script = INSTALL_ROOT / "lib" / "field-keepass.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=45)
            else:
                payload = {"schema": "field-lock/v1", "ok": False, "error": "field_lock_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-obs":
            script = INSTALL_ROOT / "lib" / "field-obs.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=45)
            else:
                payload = {"schema": "field-obs/v1", "ok": False, "error": "field_obs_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-gpu":
            script = INSTALL_ROOT / "lib" / "field-gpu-control.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=45)
            else:
                payload = {"schema": "field-gpu-control/v1", "ok": False, "error": "field_gpu_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/vsync-locker"):
            script = INSTALL_ROOT / "lib" / "field-vsync-locker.py"
            if not script.is_file():
                payload = {"schema": "field-vsync-locker/v1", "ok": False, "error": "vsync_locker_missing"}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                return
            sub = path[len("/api/vsync-locker") :].strip("/")
            if sub in ("", "status", "json"):
                payload = _nexus_py_json(script, ["json"], timeout=45)
            elif sub == "lock":
                payload = _nexus_py_json(script, ["lock"], timeout=20)
            elif sub == "detect":
                payload = _nexus_py_json(script, ["detect"], timeout=60)
            elif sub == "pointers":
                payload = _nexus_py_json(script, ["pointers"], timeout=45)
            elif sub == "input":
                payload = _nexus_py_json(script, ["input"], timeout=45)
            elif sub == "baseline":
                payload = _nexus_py_json(script, ["baseline"], timeout=30)
            elif sub == "drift":
                payload = _nexus_py_json(script, ["drift"], timeout=45)
            elif sub == "harden":
                payload = _nexus_py_json(script, ["harden"], timeout=45)
            elif sub == "guard":
                payload = _nexus_py_json(script, ["guard", "--status"], timeout=20)
            elif sub == "launch":
                payload = _nexus_py_json(script, ["launch"], timeout=30)
            elif sub == "stop":
                payload = _nexus_py_json(script, ["stop"], timeout=20)
            elif sub == "patrol":
                payload = _nexus_py_json(script, ["patrol"], timeout=120)
            else:
                payload = {"ok": False, "error": "unknown_vsync_locker_action"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/grok-lab", "/api/grok-lab/"):
            script = INSTALL_ROOT / "lib" / "grok-lab-desktop.py"
            if script.is_file():
                if self.command == "POST":
                    length = int(self.headers.get("Content-Length", "0") or "0")
                    raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
                    env = _field_stack_env()
                    try:
                        proc = subprocess.run(
                            [sys.executable, str(script), "dispatch"],
                            input=raw or "{}",
                            capture_output=True,
                            text=True,
                            timeout=180,
                            env=env,
                        )
                        payload = json.loads(proc.stdout or "{}")
                    except (subprocess.TimeoutExpired, json.JSONDecodeError):
                        payload = {"ok": False, "error": "grok_lab_dispatch_failed"}
                else:
                    payload = _nexus_py_json(script, ["json"], timeout=60)
            else:
                payload = {"schema": "grok-lab-desktop/v1", "ok": False, "error": "grok_lab_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-c2-taskbar":
            script = INSTALL_ROOT / "lib" / "field-c2-taskbar-plate.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=30)
            else:
                payload = {"schema": "field-c2-taskbar-plate/v1", "ok": False, "error": "field_c2_taskbar_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-vfs", "/api/always-files"):
            payload = _field_always_files_dispatch({"action": "status"})
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-vfs/ai", "/api/always-files/ai"):
            payload = _field_always_files_dispatch({"action": "ai"})
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-vfs/status", "/api/always-files/status"):
            payload = _field_always_files_dispatch({"action": "status"})
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-vfs/sync", "/api/always-files/sync"):
            payload = _field_always_files_dispatch({"action": "sync"})
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-vfs/ghosts", "/api/always-files/ghosts"):
            limit = int(str(query.get("limit", ["64"])[0]) or "64")
            payload = _field_always_files_dispatch({"action": "ghosts", "limit": limit})
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-vfs/resolve", "/api/always-files/resolve"):
            rel = str(query.get("path", query.get("file", [""]))[0]).strip()
            if not rel:
                self._send(400, json.dumps({"ok": False, "error": "path_required"}), "application/json")
                return
            payload = _field_always_files_dispatch({
                "action": "resolve",
                "path": rel,
                "hash": str(query.get("hash", ["0"])[0]).strip().lower() in ("1", "true", "yes"),
                "inspect": str(query.get("inspect", ["1"])[0]).strip().lower() not in ("0", "false", "no"),
            })
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-vfs/search", "/api/always-files/search"):
            q = str(query.get("q", query.get("query", [""]))[0]).strip()
            if not q:
                self._send(400, json.dumps({"ok": False, "error": "query_required"}), "application/json")
                return
            limit = int(str(query.get("limit", ["48"])[0]) or "48")
            payload = _field_always_files_dispatch({"action": "search", "query": q, "limit": limit})
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-timeshift", "/api/field-timeshift/list"):
            payload = _field_always_files_dispatch({"action": "timeshift_list"})
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-shell-dock":
            script = INSTALL_ROOT / "lib" / "field-shell-dock.py"
            if script.is_file():
                active = str(query.get("active_icon", [""])[0]).strip()
                args = ["json"] + ([active] if active else [])
                payload = _nexus_py_json(script, args, timeout=20)
            else:
                payload = {"schema": "field-shell-dock/v1", "ok": False, "error": "field_shell_dock_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-body-system"):
            body_py = INSTALL_ROOT / "lib" / "field-body-system.py"
            sub = path[len("/api/field-body-system"):].strip("/")
            if not body_py.is_file():
                payload = {"ok": False, "error": "field_body_system_missing"}
            elif sub in ("", "status", "json", "panel"):
                payload = _nexus_py_json(body_py, ["json"], timeout=120)
            elif sub == "consult":
                payload = _nexus_py_json(body_py, ["consult"], timeout=120)
            elif sub == "correlate":
                payload = _nexus_py_json(body_py, ["correlate"], timeout=60)
            elif sub == "lanes":
                payload = _nexus_py_json(body_py, ["lanes"], timeout=60)
            else:
                payload = _field_body_system_dispatch({"action": sub.replace("-", "_")}, timeout=120)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-eye-threat"):
            sub = path[len("/api/field-eye-threat"):].strip("/")
            eye_py = INSTALL_ROOT / "lib" / "field-eye-threat-chamber.py"
            if not eye_py.is_file():
                payload = {"ok": False, "error": "field_eye_threat_missing"}
            elif sub in ("", "status", "json", "panel"):
                payload = _nexus_py_json(eye_py, ["json"], timeout=30)
            elif sub == "catalog":
                payload = _nexus_py_json(eye_py, ["catalog"], timeout=20)
            elif sub in ("scan", "hostile"):
                payload = _field_eye_threat_dispatch({"action": sub}, timeout=45)
            else:
                payload = _field_eye_threat_dispatch({"action": sub.replace("-", "_")}, timeout=45)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/hostess7/anatomy-books"):
            sub = path[len("/api/hostess7/anatomy-books"):].strip("/")
            book_py = INSTALL_ROOT / "lib" / "hostess7-anatomy-book.py"
            if not book_py.is_file():
                payload = {"ok": False, "error": "anatomy_book_missing"}
            elif sub in ("", "index", "list"):
                payload = _nexus_py_json(book_py, ["index"], timeout=30)
            elif sub == "build":
                payload = _nexus_py_json(book_py, ["build"], timeout=120)
            elif sub == "build-all":
                payload = _nexus_py_json(book_py, ["build-all"], timeout=180)
            else:
                payload = _nexus_py_json(book_py, ["build-one", sub], timeout=60)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-audio-dac"):
            dac_py = INSTALL_ROOT / "lib" / "field-audio-dac-chamber.py"
            sub = path[len("/api/field-audio-dac"):].strip("/")
            if not dac_py.is_file():
                payload = {"ok": False, "error": "audio_dac_missing"}
            elif sub in ("", "status", "json", "panel"):
                payload = _nexus_py_json(dac_py, ["json"], timeout=30)
            elif sub == "devices":
                payload = _nexus_py_json(dac_py, ["devices"], timeout=20)
            elif sub == "znetwork":
                payload = _nexus_py_json(dac_py, ["znetwork"], timeout=20)
            elif sub == "broadcaster":
                payload = _nexus_py_json(dac_py, ["broadcaster"], timeout=20)
            else:
                payload = _field_audio_dac_dispatch({"action": sub.replace("-", "_")}, timeout=30)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-soundcards-catalog":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-soundcards-catalog.py", ["json"], timeout=15)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-audio-settings":
            script = INSTALL_ROOT / "lib" / "field-audio-settings.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=20)
            else:
                payload = {"ok": False, "error": "field_audio_settings_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-display-settings":
            script = INSTALL_ROOT / "lib" / "field-display-settings.py"
            if script.is_file():
                qs = parse_qs(urlparse(self.path).query)
                args = ["json"]
                vw = (qs.get("viewport_width") or [""])[0]
                vh = (qs.get("viewport_height") or [""])[0]
                if str(vw).isdigit():
                    args.append(str(vw))
                    if str(vh).isdigit():
                        args.append(str(vh))
                payload = _nexus_py_json(script, args, timeout=20)
            else:
                payload = {"ok": False, "error": "field_display_settings_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-ammoos-blocks":
            script = INSTALL_ROOT / "lib" / "field-ammoos-blocks.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=25)
            else:
                payload = {"ok": False, "error": "field_ammoos_blocks_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-audio-secure-bind":
            script = INSTALL_ROOT / "lib" / "field-audio-secure-bind.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=25)
            else:
                payload = {"ok": False, "error": "field_audio_secure_bind_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-hdmi-audio":
            script = INSTALL_ROOT / "lib" / "field-hdmi-audio-driver.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=25)
            else:
                payload = {"ok": False, "error": "field_hdmi_audio_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-vintage-audio":
            script = INSTALL_ROOT / "lib" / "field-vintage-audio-composite.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=30)
            else:
                payload = {"ok": False, "error": "field_vintage_audio_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/video-codec"):
            pipe_script = INSTALL_ROOT / "lib" / "field-video-codec-pipe.py"
            sub = path[len("/api/video-codec") :].strip("/")
            if sub in ("", "pipe", "status"):
                payload = _nexus_py_json(pipe_script, ["status"], timeout=30) if pipe_script.is_file() else {
                    "ok": False, "error": "field_video_codec_pipe_missing",
                }
            elif sub == "battery":
                bat_script = INSTALL_ROOT / "lib" / "field-video-codec-battery.py"
                refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
                argv = ["json"] + (["--refresh"] if refresh else [])
                payload = _nexus_py_json(bat_script, argv, timeout=45) if bat_script.is_file() else {
                    "ok": False, "error": "field_video_codec_battery_missing",
                }
            elif sub == "probe":
                media_path = str(query.get("path", [""])[0]).strip()
                payload = _nexus_py_json(pipe_script, ["probe", media_path], timeout=45) if pipe_script.is_file() and media_path else {
                    "ok": False, "error": "probe_path_required",
                }
            elif sub == "route":
                media_path = str(query.get("path", [""])[0]).strip()
                payload = _nexus_py_json(pipe_script, ["route", media_path], timeout=45) if pipe_script.is_file() and media_path else {
                    "ok": False, "error": "route_path_required",
                }
            else:
                payload = {"ok": False, "error": "unknown_video_codec_action"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-broadcaster/playback":
            _serve_broadcaster_playback(self, query)
            return

        if path == "/api/field-broadcaster/desktop-preview":
            _serve_broadcaster_desktop_preview(self, query)
            return

        if path == "/api/field-broadcaster/recordings":
            mod = _broadcaster_media_mod()
            if mod and hasattr(mod, "list_recordings"):
                payload = {"ok": True, "recordings": mod.list_recordings()}
            else:
                payload = {"ok": False, "error": "broadcaster_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-popcorn/stream":
            _serve_popcorn_stream(self, query)
            return

        if path == "/api/field-popcorn/thumb":
            _serve_popcorn_thumb(self, query)
            return

        if path in ("/api/field-gnu-terminal", "/api/field-gnu-terminal/"):
            script = INSTALL_ROOT / "lib" / "field-gnu-terminal.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=30)
            else:
                payload = {"schema": "field-gnu-terminal/v2", "ok": False, "error": "field_gnu_terminal_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-irc", "/api/field-irc/"):
            script = INSTALL_ROOT / "lib" / "field-irc.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=45)
            else:
                payload = {"schema": "field-irc/v1", "ok": False, "error": "field_irc_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-stack-boot", "/api/field-stack-boot/"):
            script = INSTALL_ROOT / "lib" / "field-stack-boot.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=120)
            else:
                payload = {"schema": "field-stack-boot/v1", "ok": False, "error": "field_stack_boot_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/ammoos-incorporate/check", "/api/ammoos-incorporate/status"):
            script = INSTALL_ROOT / "lib" / "ammoos-incorporate.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=60)
            else:
                payload = {"schema": "ammoos-incorporate/v1", "ok": False, "error": "ammoos_incorporate_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-eol-code", "/api/field-eol-code/"):
            script = INSTALL_ROOT / "lib" / "field-eol-code.py"
            if script.is_file():
                refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
                args = ["panel"] + (["--refresh"] if refresh else [])
                payload = _nexus_py_json(script, args, timeout=45)
            else:
                payload = {"schema": "field-eol-code-panel/v1", "ok": False, "error": "field_eol_code_missing"}
            self._send(200, json.dumps(payload or {"ok": False, "error": "empty_payload"}, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-popcorn":
            script = INSTALL_ROOT / "lib" / "field-popcorn-player.py"
            if script.is_file():
                rescan = str(query.get("rescan", ["0"])[0]).strip().lower() in ("1", "true", "yes")
                args = ["json"] + (["--rescan"] if rescan else [])
                payload = _nexus_py_json(script, args, timeout=120)
            else:
                payload = {"schema": "field-popcorn/v1", "ok": False, "error": "field_popcorn_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-big-drive":
            script = INSTALL_ROOT / "lib" / "field-big-drive.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=120)
            else:
                payload = {"schema": "field-big-drive/v1", "ok": False, "error": "field_big_drive_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-storage":
            script = INSTALL_ROOT / "lib" / "field-storage.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=60)
            else:
                payload = {"schema": "field-storage/v1", "ok": False, "error": "field_storage_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-g16-launch":
            script = INSTALL_ROOT / "lib" / "field-g16-launch.py"
            if script.is_file():
                rescan = str(query.get("rescan", ["0"])[0]).strip().lower() in ("1", "true", "yes")
                args = ["json"] + (["--rescan"] if rescan else [])
                payload = _nexus_py_json(script, args, timeout=120)
            else:
                payload = {"schema": "field-g16-launch/v1", "ok": False, "error": "field_g16_launch_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-g16-launch/index":
            script = INSTALL_ROOT / "lib" / "field-g16-launch.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["discover"], timeout=120)
            else:
                payload = {"ok": False, "error": "field_g16_launch_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-g16-launch/explore":
            script = INSTALL_ROOT / "lib" / "field-g16-launch.py"
            path_arg = str(query.get("path", [""])[0]).strip()
            if script.is_file() and path_arg:
                payload = _nexus_py_json(script, ["explore", path_arg], timeout=45)
            else:
                payload = {"ok": False, "error": "explore_path_required"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-popcorn/library":
            script = INSTALL_ROOT / "lib" / "field-popcorn-player.py"
            kind = str(query.get("kind", ["all"])[0]).strip() or "all"
            q = str(query.get("q", [""])[0]).strip() or None
            if script.is_file():
                args = ["library"] + ([] if kind in ("", "all") else [kind]) + ([q] if q else [])
                payload = _nexus_py_json(script, args, timeout=90)
            else:
                payload = {"ok": False, "error": "field_popcorn_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-popcorn/inspect":
            script = INSTALL_ROOT / "lib" / "field-popcorn-player.py"
            media_id = str(query.get("id", [""])[0]).strip()
            deep = str(query.get("deep", ["1"])[0]).strip().lower() not in ("0", "false", "no")
            if script.is_file() and media_id:
                args = ["inspect", media_id] + ([] if deep else ["--light"])
                payload = _nexus_py_json(script, args, timeout=120)
            else:
                payload = {"ok": False, "error": "id_required" if not media_id else "field_popcorn_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-popcorn/details":
            script = INSTALL_ROOT / "lib" / "field-popcorn-player.py"
            media_id = str(query.get("id", [""])[0]).strip()
            if script.is_file() and media_id:
                payload = _nexus_py_json(script, ["details", media_id], timeout=120)
            else:
                payload = {"ok": False, "error": "id_required" if not media_id else "field_popcorn_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-ellie-fier":
            script = INSTALL_ROOT / "lib" / "field-ellie-fier.py"
            if script.is_file():
                do_scan = str(query.get("scan", ["0"])[0]).strip().lower() in ("1", "true", "yes")
                args = ["json"] + (["--scan"] if do_scan else [])
                payload = _nexus_py_json(script, args, timeout=180)
            else:
                payload = {"schema": "field-ellie-fier/v1", "ok": False, "error": "field_ellie_fier_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-ellie-fier/pillar/"):
            script = INSTALL_ROOT / "lib" / "field-ellie-fier.py"
            slug = path[len("/api/field-ellie-fier/pillar/") :].strip("/").split("/")[0]
            if script.is_file() and slug:
                do_scan = str(query.get("scan", ["0"])[0]).strip().lower() in ("1", "true", "yes")
                args = ["pillar", slug] + (["--scan"] if do_scan else [])
                payload = _nexus_py_json(script, args, timeout=180)
            else:
                payload = {"ok": False, "error": "field_ellie_fier_missing" if not script.is_file() else "pillar_required"}
            code = 200 if payload.get("ok", True) else 404
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-gdb":
            script = INSTALL_ROOT / "lib" / "field-gdb.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=45)
            else:
                payload = {"schema": "field-gdb/v1", "ok": False, "error": "field_gdb_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/battle-stations", "/api/field-battle-stations"):
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            payload = None if refresh else _read_zachub_panel_cache("battle_stations")
            if payload is None:
                script = INSTALL_ROOT / "lib" / "field-battle-stations.py"
                if script.is_file():
                    payload = _nexus_py_json(script, ["json"], timeout=30)
                else:
                    payload = {
                        "schema": "field-battle-stations-panel/v1",
                        "ok": False,
                        "error": "field_battle_stations_missing",
                    }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-host-desktop":
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            if not refresh:
                payload = _read_field_host_desktop_cache()
                if payload:
                    self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                    return
            script = INSTALL_ROOT / "lib" / "field-host-desktop.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=60)
            else:
                payload = {"schema": "field-host-desktop/v1", "ok": False, "error": "field_host_desktop_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-keyboard-sovereign", "/api/field-keyboard-sovereign/status"):
            script = INSTALL_ROOT / "lib" / "field-keyboard-sovereign.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=15)
            else:
                payload = {"schema": "field-keyboard-sovereign/v1", "ok": False, "error": "keyboard_sovereign_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-taskbar-pins":
            pins_py = INSTALL_ROOT / "lib" / "field-taskbar-pins.py"
            if pins_py.is_file():
                payload = _nexus_py_json(pins_py, ["json"], timeout=15)
            else:
                payload = {"schema": "field-taskbar-pins/v1", "ok": False, "error": "taskbar_pins_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-underlay-surface":
            script = INSTALL_ROOT / "lib" / "field-underlay-surface.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=30)
            else:
                payload = {"schema": "field-underlay-surface/v1", "ok": False, "error": "underlay_surface_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/compatibility", "/api/compatibility-layers"):
            layers = INSTALL_ROOT / "lib" / "field-compatibility-layers.py"
            payload = _nexus_py_json(layers, ["json"], timeout=45) if layers.is_file() else {
                "schema": "field-compatibility-layers/v1",
                "ok": False,
                "hint": "compatibility layers missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/always-optimal", "/api/g16/always-optimal"):
            ao = _grok16_root() / "lib" / "field-always-optimal.py"
            payload = _nexus_py_json(ao, ["json"], timeout=30) if ao.is_file() else {
                "schema": "g16-always-optimal-panel/v1",
                "ok": False,
                "hint": "always-optimal module missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/locational-sitrep", "/api/sitrep", "/api/field/locational-sitrep"):
            ls = INSTALL_ROOT / "lib" / "field-locational-sitrep-plate.py"
            payload = _nexus_py_json(ls, ["json"], timeout=45) if ls.is_file() else {
                "schema": "field-locational-sitrep-plate/v1",
                "ok": False,
                "hint": "locational-sitrep plate missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/physics-witness", "/api/field/physics-witness"):
            pw = INSTALL_ROOT / "lib" / "field-physics-witness.py"
            payload = _nexus_py_json(pw, ["json"], timeout=30) if pw.is_file() else {
                "schema": "field-physics-witness/v1",
                "ok": False,
                "hint": "physics-witness module missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/power-sort", "/api/g16/power-sort"):
            ps = _grok16_root() / "lib" / "field-power-sort.py"
            payload = _nexus_py_json(ps, ["json"], timeout=30) if ps.is_file() else {
                "schema": "g16-power-sort-panel/v1",
                "ok": False,
                "hint": "power-sort module missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/combinatorics", "/api/combinatorics/status", "/api/combinatorics/studio"):
            # Studio primary — secure Field combinatorics (not compatibility-layers hijack)
            studio = INSTALL_ROOT / "lib" / "field-combinatorics-studio.py"
            if studio.is_file():
                payload = _nexus_py_json(studio, ["json"], timeout=60)
            else:
                payload = {
                    "schema": "field-combinatorics-studio/v1",
                    "ok": False,
                    "hint": "combinatorics studio missing",
                }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return
        if path in ("/api/compatibility-layers", "/api/combinatorics/layers"):
            layers = INSTALL_ROOT / "lib" / "field-compatibility-layers.py"
            payload = _nexus_py_json(layers, ["json"], timeout=45) if layers.is_file() else {
                "schema": "field-compatibility-layers/v1",
                "ok": False,
                "hint": "compatibility-layers missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/chip-battery", "/api/combinatorics/chip-battery"):
            chip_py = INSTALL_ROOT / "lib" / "field-chip-battery.py"
            payload = _nexus_py_json(chip_py, ["json"], timeout=45) if chip_py.is_file() else {
                "schema": "field-chip-battery-panel/v1",
                "ok": False,
                "hint": "field-chip-battery missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/chips/combinatronic", "/api/chip-battery/combinatronic"):
            chip_py = INSTALL_ROOT / "lib" / "field-chip-battery.py"
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            argv = ["combinatronic"]
            if refresh:
                argv.append("--refresh")
            payload = _nexus_py_json(chip_py, argv, timeout=90) if chip_py.is_file() else {
                "schema": "field-chips-combinatronic/v1",
                "ok": False,
                "hint": "field-chip-battery missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/chips/plate-stack", "/api/chips-plate-stack", "/api/chip-plate-stack"):
            cps_py = INSTALL_ROOT / "lib" / "field-chips-plate-stack.py"
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            argv = ["json"]
            if refresh:
                argv.append("--refresh")
            payload = _nexus_py_json(cps_py, argv, timeout=120) if cps_py.is_file() else {
                "schema": "field-chips-plate-stack-panel/v1",
                "ok": False,
                "hint": "field-chips-plate-stack missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/chips/presume-path", "/api/chips-presume-path", "/api/chip-presume-path"):
            pp_py = INSTALL_ROOT / "lib" / "field-chips-presume-path.py"
            qparams = parse_qs(urlparse(self.path).query)
            sub = str((qparams.get("cmd") or ["panel"])[0]).strip().lower()
            if sub in ("clock-stop", "clock", "sync"):
                argv = ["clock-stop"]
                hz = (qparams.get("hz") or ["60"])[0]
                argv.append(str(hz))
            elif sub in ("paths", "build"):
                argv = ["paths"]
            else:
                argv = ["panel"]
            payload = _nexus_py_json(pp_py, argv, timeout=60) if pp_py.is_file() else {
                "schema": "field-chips-presume-path-panel/v1",
                "ok": False,
                "hint": "field-chips-presume-path missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/chips/core", "/api/chips-core", "/api/chip-core"):
            cc_py = INSTALL_ROOT / "lib" / "field-chips-core.py"
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            argv = ["json"]
            if refresh:
                argv.append("--refresh")
            payload = _nexus_py_json(cc_py, argv, timeout=120) if cc_py.is_file() else {
                "schema": "field-chips-core-panel/v1",
                "ok": False,
                "hint": "field-chips-core missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/chips/usage", "/api/chips-usage", "/api/chip-usage"):
            pu_py = INSTALL_ROOT / "lib" / "field-chips-program-usage.py"
            qparams = parse_qs(urlparse(self.path).query)
            program = (qparams.get("program") or qparams.get("program_id") or qparams.get("id") or [""])[0]
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            if program:
                argv = ["resolve", str(program)]
            else:
                argv = ["json"]
            if refresh:
                argv.append("--refresh")
            payload = _nexus_py_json(pu_py, argv, timeout=120) if pu_py.is_file() else {
                "schema": "field-chips-program-usage/v1",
                "ok": False,
                "hint": "field-chips-program-usage missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/combinatronics/growth", "/api/combinatronics-growth"):
            gr_py = INSTALL_ROOT / "lib" / "field-combinatronics-growth.py"
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            argv = ["grow"] if refresh else ["panel"]
            if refresh:
                argv.append("--refresh")
            payload = _nexus_py_json(gr_py, argv, timeout=180) if gr_py.is_file() else {
                "schema": "field-combinatronics-growth/v1",
                "ok": False,
                "hint": "field-combinatronics-growth missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/combinatorics/sequence", "/api/combinatorics-sequence"):
            seq_py = INSTALL_ROOT / "lib" / "field-combinatorics-sequence.py"
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            argv = ["build"] if refresh else ["panel"]
            if refresh:
                argv.append("--refresh")
            if (qparams.get("no_fill") or ["0"])[0] in ("1", "true", "yes"):
                argv.append("--no-fill")
            payload = _nexus_py_json(seq_py, argv, timeout=180) if seq_py.is_file() else {
                "schema": "field-combinatorics-sequence/v1",
                "ok": False,
                "hint": "field-combinatorics-sequence missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/plate-dimensions", "/api/plate/dimensions"):
            dim_py = INSTALL_ROOT / "lib" / "field-plate-dimensions.py"
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            full = (qparams.get("full") or ["0"])[0] in ("1", "true", "yes")
            argv = ["build"] if refresh else ["panel"]
            if full:
                argv.append("--full")
            payload = _nexus_py_json(dim_py, argv, timeout=120) if dim_py.is_file() else {
                "schema": "field-plate-dimensions/v1",
                "ok": False,
                "hint": "field-plate-dimensions missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/ammolang"):
            aml_py = INSTALL_ROOT / "lib" / "field-ammolang.py"
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            sub = path.split("/api/ammolang", 1)[-1].strip("/") or "panel"
            if sub in ("compile", "interpret", "trace", "run") and self.command == "POST":
                try:
                    length = int(self.headers.get("Content-Length", "0") or "0")
                    raw = self.rfile.read(length).decode("utf-8", errors="replace") if length else "{}"
                    body = json.loads(raw or "{}")
                except (json.JSONDecodeError, ValueError):
                    body = {}
                if aml_py.is_file():
                    spec = importlib.util.spec_from_file_location("ammolang_http", aml_py)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        body["action"] = sub
                        body["refresh"] = refresh
                        payload = mod.dispatch(body) if hasattr(mod, "dispatch") else {"ok": False}
                    else:
                        payload = {"ok": False, "error": "ammolang_load_failed"}
                else:
                    payload = {"schema": "field-ammolang/v1", "ok": False, "hint": "field-ammolang missing"}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                return
            argv = ["panel"]
            if refresh:
                argv.append("--refresh")
            payload = _nexus_py_json(aml_py, argv, timeout=120) if aml_py.is_file() else {
                "schema": "field-ammolang/v1",
                "ok": False,
                "hint": "field-ammolang missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/combinatronic/spider-wire") or path.startswith("/api/combinatronic-spider-wire"):
            sw_py = INSTALL_ROOT / "lib" / "field-combinatronic-spider-wire.py"
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            optimize = (qparams.get("optimize") or ["1"])[0] in ("1", "true", "yes")
            argv = ["build" if refresh else "panel"]
            if not optimize:
                argv.append("--no-optimize")
            if refresh:
                argv.append("--refresh")
            payload = _nexus_py_json(sw_py, argv, timeout=120) if sw_py.is_file() else {
                "schema": "field-combinatronic-spider-wire/v1",
                "ok": False,
                "hint": "field-combinatronic-spider-wire missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/combinatronic/visuals") or path.startswith("/api/combinatronic-visuals"):
            vis_py = INSTALL_ROOT / "lib" / "field-combinatronic-visuals.py"
            qparams = parse_qs(urlparse(self.path).query)
            sub = path.split("/api/combinatronic/visuals", 1)[-1].strip("/") or path.split("/api/combinatronic-visuals", 1)[-1].strip("/")
            refresh = (qparams.get("refresh") or qparams.get("generate") or ["0"])[0] in ("1", "true", "yes")
            repair = (qparams.get("repair") or ["0"])[0] in ("1", "true", "yes")
            argv = ["manifest"]
            if sub in ("inventory", "verify", "registry", "repair", "pattern"):
                argv = [sub]
                if sub == "repair":
                    if (qparams.get("mirror") or ["0"])[0] in ("1", "true", "yes"):
                        argv = ["repair", "mirror"]
                    elif (qparams.get("all") or ["0"])[0] in ("1", "true", "yes"):
                        argv = ["repair", "--all"]
                if sub == "pattern":
                    pat = str((qparams.get("id") or qparams.get("pattern") or ["chip_png"])[0])
                    argv = ["pattern", pat]
            elif refresh:
                argv = ["generate"]
            elif repair:
                argv = ["repair"]
            payload = _nexus_py_json(vis_py, argv, timeout=240) if vis_py.is_file() else {
                "schema": "field-combinatronic-visuals-manifest/v1",
                "ok": False,
                "hint": "field-combinatronic-visuals missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/g16/universal-combinatronic", "/api/g16-universal-combinatronic"):
            uni_py = INSTALL_ROOT / "lib" / "field-g16-universal-combinatronic.py"
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            argv = ["combinatronic"]
            if refresh:
                argv.append("--refresh")
            payload = _nexus_py_json(uni_py, argv, timeout=120) if uni_py.is_file() else {
                "schema": "field-g16-universal-combinatronic/v1",
                "ok": False,
                "hint": "field-g16-universal-combinatronic missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/steel-neural-plates") or path.startswith("/api/combinatronic/steel-plates"):
            snp_py = INSTALL_ROOT / "lib" / "field-steel-neural-plates.py"
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes") or path.endswith("/build")
            force = (qparams.get("force") or ["0"])[0] in ("1", "true", "yes")
            sub = path.split("/api/steel-neural-plates", 1)[-1].strip("/") or path.split("/api/combinatronic/steel-plates", 1)[-1].strip("/") or "panel"
            if sub in ("build", "publish", "battery"):
                argv = ["build"]
            elif sub in ("slice",):
                argv = ["slice"]
            elif sub in ("verify",):
                argv = ["verify"]
            else:
                argv = ["panel"]
            if refresh:
                argv.append("--refresh")
            if force:
                argv.append("--force")
            payload = _nexus_py_json(snp_py, argv, timeout=180) if snp_py.is_file() else {
                "schema": "field-steel-neural-plates/v1",
                "ok": False,
                "hint": "field-steel-neural-plates missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/combinamatrix", "/api/combinamatrix/build"):
            cm_py = INSTALL_ROOT / "lib" / "field-combinamatrix.py"
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes") or path.endswith("/build")
            argv = ["build"] if refresh else ["panel"]
            if refresh:
                argv.append("--refresh")
            payload = _nexus_py_json(cm_py, argv, timeout=180) if cm_py.is_file() else {
                "schema": "field-combinamatrix/v1",
                "ok": False,
                "hint": "field-combinamatrix missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/universal-neural"):
            un_py = INSTALL_ROOT / "lib" / "field-universal-neural.py"
            qparams = parse_qs(urlparse(self.path).query)
            sub = path.split("/api/universal-neural", 1)[-1].strip("/") or "panel"
            teach = (qparams.get("teach") or ["0"])[0] in ("1", "true", "yes") or sub == "teach"
            force = (qparams.get("force") or ["0"])[0] in ("1", "true", "yes")
            if not un_py.is_file():
                self._send(200, json.dumps({"schema": "field-universal-neural/v1", "ok": False, "hint": "field-universal-neural missing"}, ensure_ascii=False), "application/json")
                return
            if sub in ("teach", "curriculum"):
                argv = ["teach"] + (["--force"] if force else [])
            elif sub in ("build", "universal"):
                argv = ["build"] + (["--teach"] if teach else [])
            else:
                argv = ["panel"] + (["--teach"] if teach else [])
            payload = _nexus_py_json(un_py, argv, timeout=300)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/combinatronic/balance", "/api/combinatronic-balance"):
            bal_py = INSTALL_ROOT / "lib" / "field-combinatronic-balance.py"
            qparams = parse_qs(urlparse(self.path).query)
            sub = str((qparams.get("cmd") or ["panel"])[0]).strip().lower()
            force = (qparams.get("force") or ["0"])[0] in ("1", "true", "yes")
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            if sub in ("fingerprint", "fp"):
                argv = ["fingerprint"]
            elif sub in ("sync", "sync_all", "entries"):
                argv = ["sync"]
                if refresh:
                    argv.append("--refresh")
                if force:
                    argv.append("--force")
            elif sub in ("gate", "should"):
                argv = ["gate"] + (["--force"] if force else [])
            elif sub in ("verify",):
                argv = ["verify"]
            elif sub in ("content", "read", "identify", "id"):
                cid = str((qparams.get("id") or qparams.get("book") or [""])[0]).strip()
                fmt = str((qparams.get("format") or [""])[0]).strip()
                collection = str((qparams.get("collection") or [""])[0]).strip()
                argv = [sub if sub in ("identify", "id") else "content", cid] if cid else ["panel"]
                if fmt:
                    argv.extend(["--format", fmt])
                if collection:
                    argv.extend(["--collection", collection])
            elif sub in ("lookup",):
                bid = str((qparams.get("balance_id") or qparams.get("id") or [""])[0]).strip()
                argv = ["lookup", bid] if bid else ["panel"]
            else:
                argv = ["panel"]
            timeout = 300 if sub in ("sync", "sync_all", "entries") else 60
            payload = _nexus_py_json(bal_py, argv, timeout=timeout) if bal_py.is_file() else {
                "schema": "field-combinatronic-balance-panel/v1",
                "ok": False,
                "hint": "field-combinatronic-balance missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/g16/combinatronic-rebalance", "/api/g16-combinatronic-rebalance"):
            reb_py = INSTALL_ROOT / "lib" / "g16-combinatronic-rebalance.py"
            qparams = parse_qs(urlparse(self.path).query)
            action = str((qparams.get("action") or ["snap"])[0]).strip().lower()
            refresh = (qparams.get("refresh") or ["1"])[0] in ("1", "true", "yes")
            full = (qparams.get("full") or ["0"])[0] in ("1", "true", "yes")
            argv = [action]
            if refresh:
                argv.append("--refresh")
            if full:
                argv.append("--full")
            payload = _nexus_py_json(reb_py, argv, timeout=300) if reb_py.is_file() else {
                "schema": "g16-combinatronic-rebalance/v1",
                "ok": False,
                "hint": "g16-combinatronic-rebalance missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/program/combinatronic", "/api/program-combinatronic"):
            prog_py = INSTALL_ROOT / "lib" / "field-program-combinatronic.py"
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes")
            lang = str((qparams.get("lang") or [""])[0]).strip()
            command = str((qparams.get("command") or [""])[0]).strip()
            if lang and command:
                argv = ["boil", lang, command]
            else:
                argv = ["combinatronic"]
                if refresh:
                    argv.append("--refresh")
            payload = _nexus_py_json(prog_py, argv, timeout=90) if prog_py.is_file() else {
                "schema": "field-program-combinatronic/v1",
                "ok": False,
                "hint": "field-program-combinatronic missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/dewey-index"):
            idx_py = INSTALL_ROOT / "lib" / "field-dewey-index.py"
            if not idx_py.is_file():
                self._send(200, json.dumps({
                    "schema": "field-dewey-index/v1",
                    "ok": False,
                    "hint": "field-dewey-index missing",
                }, ensure_ascii=False), "application/json")
                return
            qparams = parse_qs(urlparse(self.path).query)
            if path.endswith("/search") or "/search" in path:
                q = str(qparams.get("q", [""])[0])
                argv = ["search", q]
                if qparams.get("tag"):
                    argv.extend(["--tag", str(qparams.get("tag", [""])[0])])
                if qparams.get("dewey"):
                    argv.extend(["--dewey", str(qparams.get("dewey", [""])[0])])
                if qparams.get("kind"):
                    argv.extend(["--kind", str(qparams.get("kind", [""])[0])])
                if qparams.get("shelf"):
                    argv.extend(["--shelf", str(qparams.get("shelf", [""])[0])])
                if str(qparams.get("personhood", [""])[0]).lower() in ("1", "true", "yes"):
                    argv.append("--personhood")
                if str(qparams.get("combat", [""])[0]).lower() in ("1", "true", "yes"):
                    argv.append("--combat")
                if str(qparams.get("speaking", [""])[0]).lower() in ("1", "true", "yes"):
                    argv.append("--speaking")
                if qparams.get("limit"):
                    argv.extend(["--limit", str(qparams.get("limit", ["48"])[0])])
                payload = _nexus_py_json(idx_py, argv, timeout=90)
            elif path.endswith("/tags"):
                payload = _nexus_py_json(idx_py, ["tags"], timeout=60)
            elif path.endswith("/facets"):
                payload = _nexus_py_json(idx_py, ["facets"], timeout=60)
            elif path.endswith("/build") or path.endswith("/reindex"):
                payload = _nexus_py_json(idx_py, ["build"], timeout=300)
            elif path.endswith("/book"):
                bid = str(qparams.get("id", [""])[0])
                payload = _nexus_py_json(idx_py, ["book", bid], timeout=30)
            else:
                payload = _nexus_py_json(idx_py, ["panel"], timeout=60)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/dewey-library"):
            dewey_py = INSTALL_ROOT / "lib" / "field-dewey-library.py"
            if not dewey_py.is_file():
                self._send(200, json.dumps({
                    "schema": "field-dewey-library/v1",
                    "ok": False,
                    "hint": "field-dewey-library missing",
                }, ensure_ascii=False), "application/json")
                return
            qparams = parse_qs(urlparse(self.path).query)
            if path.endswith("/migrate") or path.endswith("/convert"):
                argv = ["migrate"]
            elif path.endswith("/tree") or path.endswith("/shelves"):
                argv = ["tree"]
            elif path.endswith("/books"):
                argv = ["books"]
            else:
                argv = ["panel"]
            payload = _nexus_py_json(dewey_py, argv, timeout=300)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/library-registry"):
            reg_py = INSTALL_ROOT / "lib" / "field-library-registry.py"
            if not reg_py.is_file():
                self._send(200, json.dumps({
                    "schema": "field-library-registry/v1",
                    "ok": False,
                    "hint": "field-library-registry missing",
                }, ensure_ascii=False), "application/json")
                return
            qparams = parse_qs(urlparse(self.path).query)
            if path.startswith("/api/library-registry/search"):
                q = str(qparams.get("q", [""])[0])
                payload = _nexus_py_json(reg_py, ["search", q], timeout=60)
            elif path.endswith("/build") or path.endswith("/sync"):
                payload = _nexus_py_json(reg_py, ["build"], timeout=300)
            else:
                payload = _nexus_py_json(reg_py, ["panel"], timeout=120)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/extensive-library"):
            ext_py = INSTALL_ROOT / "lib" / "field-extensive-library.py"
            if not ext_py.is_file():
                self._send(200, json.dumps({
                    "schema": "field-extensive-library/v1",
                    "ok": False,
                    "hint": "field-extensive-library missing",
                }, ensure_ascii=False), "application/json")
                return
            qparams = parse_qs(urlparse(self.path).query)
            if path.startswith("/api/extensive-library/search"):
                q = str(qparams.get("q", [""])[0])
                payload = _nexus_py_json(ext_py, ["search", q], timeout=60)
            elif path.endswith("/build") or path.endswith("/sync"):
                refresh = (qparams.get("refresh") or ["1"])[0] in ("1", "true", "yes")
                argv = ["build"] if refresh else ["panel"]
                payload = _nexus_py_json(ext_py, argv, timeout=300)
            else:
                payload = _nexus_py_json(ext_py, ["panel"], timeout=90)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/h7c"):
            h7c_py = INSTALL_ROOT / "lib" / "field-h7c-compression.py"
            if not h7c_py.is_file():
                self._send(200, json.dumps({
                    "schema": "field-h7c-panel/v1",
                    "ok": False,
                    "hint": "field-h7c-compression missing",
                }, ensure_ascii=False), "application/json")
                return
            qparams = parse_qs(urlparse(self.path).query)
            sub = path.split("/api/h7c", 1)[-1].strip("/") or "panel"
            if sub in ("balance", "table"):
                argv = ["balance"]
            elif sub in ("verify",):
                argv = ["verify"]
            elif sub in ("optimize", "optimizer"):
                argv = ["optimize"]
            elif sub == "pack" and qparams.get("src"):
                src = str((qparams.get("src") or [""])[0])
                dest = str((qparams.get("dest") or [src + ".h7c"])[0])
                argv = ["pack", src, dest]
            elif sub == "unpack" and qparams.get("file"):
                argv = ["unpack", str((qparams.get("file") or [""])[0])]
            else:
                argv = ["panel"]
            timeout = 120 if sub in ("pack", "unpack", "optimize", "optimizer") else 60
            payload = _nexus_py_json(h7c_py, argv, timeout=timeout)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/file-formats"):
            ff_py = INSTALL_ROOT / "lib" / "field-file-formats.py"
            if not ff_py.is_file():
                self._send(200, json.dumps({
                    "schema": "field-file-formats-panel/v1",
                    "ok": False,
                    "hint": "field-file-formats missing",
                }, ensure_ascii=False), "application/json")
                return
            qparams = parse_qs(urlparse(self.path).query)
            sub = path.split("/api/file-formats", 1)[-1].strip("/") or "panel"
            if sub in ("build", "icons") or (qparams.get("refresh") or ["0"])[0] in ("1", "true", "yes"):
                argv = ["build"] if sub != "icons" else ["icons"]
            elif sub == "table":
                argv = ["table"]
            elif sub.startswith("detail"):
                fid = str(qparams.get("id", [""])[0])
                argv = ["detail", fid] if fid else ["panel"]
            else:
                argv = ["panel"]
            payload = _nexus_py_json(ff_py, argv, timeout=180)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/best-sort"):
            bs_py = INSTALL_ROOT / "lib" / "field-best-sort.py"
            if not bs_py.is_file():
                self._send(200, json.dumps({
                    "schema": "field-best-sort-panel/v1",
                    "ok": False,
                    "hint": "field-best-sort missing",
                }, ensure_ascii=False), "application/json")
                return
            qparams = parse_qs(urlparse(self.path).query)
            sub = path.split("/api/best-sort", 1)[-1].strip("/") or "panel"
            if sub == "meld":
                argv = ["meld"]
            elif sub == "resolve":
                ctx = str(qparams.get("context", ["format_table"])[0])
                argv = ["resolve", ctx]
            else:
                argv = ["panel"]
            payload = _nexus_py_json(bs_py, argv, timeout=60)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/device-visuals"):
            dv_py = INSTALL_ROOT / "lib" / "field-device-visuals.py"
            if not dv_py.is_file():
                self._send(200, json.dumps({
                    "schema": "field-device-visuals-panel/v1",
                    "ok": False,
                    "hint": "field-device-visuals missing",
                }, ensure_ascii=False), "application/json")
                return
            qparams = parse_qs(urlparse(self.path).query)
            refresh = (qparams.get("refresh") or qparams.get("generate") or ["0"])[0] in ("1", "true", "yes")
            sub = path.split("/api/device-visuals", 1)[-1].strip("/") or "panel"
            if sub in ("generate", "build") or refresh:
                argv = ["generate"]
            elif sub == "inventory":
                argv = ["inventory"]
            else:
                argv = ["panel"]
            payload = _nexus_py_json(dv_py, argv, timeout=300)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/cpu-library"):
            cpu_py = INSTALL_ROOT / "lib" / "field-cpu-library.py"
            if not cpu_py.is_file():
                self._send(200, json.dumps({
                    "schema": "field-cpu-library/v1",
                    "ok": False,
                    "hint": "field-cpu-library missing",
                }, ensure_ascii=False), "application/json")
                return
            qparams = parse_qs(urlparse(self.path).query)
            if path.startswith("/api/cpu-library/search"):
                q = str(qparams.get("q", [""])[0])
                payload = _nexus_py_json(cpu_py, ["search", q], timeout=45)
            elif path.startswith("/api/cpu-library/detail"):
                eid = str(qparams.get("id", [""])[0])
                payload = _nexus_py_json(cpu_py, ["detail", eid], timeout=30)
            else:
                payload = _nexus_py_json(cpu_py, ["library"], timeout=60)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/card-catalog"):
            cat_py = INSTALL_ROOT / "lib" / "field-card-catalog.py"
            if not cat_py.is_file():
                self._send(200, json.dumps({
                    "schema": "field-card-catalog/v1",
                    "ok": False,
                    "hint": "field-card-catalog missing",
                }, ensure_ascii=False), "application/json")
                return
            qparams = parse_qs(urlparse(self.path).query)
            if path.endswith("/autocomplete") or "/autocomplete" in path:
                q = str(qparams.get("q", [""])[0])
                limit = str(qparams.get("limit", ["20"])[0])
                payload = _nexus_py_json(cat_py, ["autocomplete", q, "--limit", limit], timeout=60)
            elif path.endswith("/search") or "/search" in path:
                q = str(qparams.get("q", [""])[0])
                limit = str(qparams.get("limit", ["48"])[0])
                payload = _nexus_py_json(cat_py, ["search", q, "--limit", limit], timeout=90)
            elif path.endswith("/sort") or "/sort" in path:
                mode = str(qparams.get("mode", ["call_number"])[0])
                payload = _nexus_py_json(cat_py, ["sort", mode], timeout=90)
            elif path.endswith("/card") or "/card" in path:
                cid = str(qparams.get("id", [""])[0])
                payload = _nexus_py_json(cat_py, ["card", cid], timeout=30)
            elif path.endswith("/detect") or path.endswith("/build") or path.endswith("/publish"):
                payload = _nexus_py_json(cat_py, ["detect"], timeout=300)
            elif path.endswith("/panel"):
                payload = _nexus_py_json(cat_py, ["panel"], timeout=60)
            else:
                payload = _nexus_py_json(cat_py, ["catalog"], timeout=120)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/tobins-spirit-guide"):
            tobin_py = INSTALL_ROOT / "lib" / "tobins-spirit-guide.py"
            if not tobin_py.is_file():
                self._send(200, json.dumps({
                    "schema": "tobins-spirit-guide/v1",
                    "ok": False,
                    "hint": "tobins-spirit-guide missing",
                }, ensure_ascii=False), "application/json")
                return
            qparams = parse_qs(urlparse(self.path).query)
            if path.endswith("/library-book") or "/library-book" in path:
                refresh = "1" if str(qparams.get("refresh", ["0"])[0]) in ("1", "true") else "0"
                argv = ["library-book"] + (["--refresh"] if refresh == "1" else [])
                payload = _nexus_py_json(tobin_py, argv, timeout=90)
            elif path.endswith("/panel") or path.endswith("/build") or path.endswith("/publish"):
                payload = _nexus_py_json(tobin_py, ["publish"], timeout=90)
            else:
                payload = _nexus_py_json(tobin_py, ["catalog"], timeout=60)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/chips/catalog"):
            cat_py = INSTALL_ROOT / "lib" / "field-chips-catalog.py"
            if not cat_py.is_file():
                self._send(200, json.dumps({
                    "schema": "field-chips-catalog/v1",
                    "ok": False,
                    "hint": "field-chips-catalog missing",
                }, ensure_ascii=False), "application/json")
                return
            qparams = parse_qs(urlparse(self.path).query)
            if path.endswith("/autocomplete") or "/autocomplete" in path:
                q = str(qparams.get("q", [""])[0])
                limit = str(qparams.get("limit", ["20"])[0])
                payload = _nexus_py_json(cat_py, ["autocomplete", q, limit], timeout=30)
            elif path.endswith("/search") or "/search" in path:
                q = str(qparams.get("q", [""])[0])
                payload = _nexus_py_json(cat_py, ["search", q], timeout=45)
            elif path.endswith("/detail") or "/detail" in path:
                eid = str(qparams.get("id", [""])[0])
                payload = _nexus_py_json(cat_py, ["detail", eid], timeout=30)
            elif path.endswith("/pages") or "/pages" in path:
                payload = _nexus_py_json(cat_py, ["pages"], timeout=45)
            elif path.endswith("/library-book") or "/library-book" in path:
                refresh = "1" if str(qparams.get("refresh", ["0"])[0]) in ("1", "true") else "0"
                argv = ["library-book"] + (["--refresh"] if refresh == "1" else [])
                payload = _nexus_py_json(cat_py, argv, timeout=120)
            elif path.endswith("/panel") or path.endswith("/build") or path.endswith("/publish"):
                payload = _nexus_py_json(cat_py, ["publish"], timeout=120)
            else:
                payload = _nexus_py_json(cat_py, ["catalog"], timeout=60)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-font":
            font_py = INSTALL_ROOT / "lib" / "field-font-kit.py"
            payload = _nexus_py_json(font_py, ["panel"], timeout=45) if font_py.is_file() else {
                "schema": "field-font-panel/v1",
                "ok": False,
                "hint": "field-font-kit missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/combinatorics/comb", "/api/combinatorics/charts", "/api/combinatorics/cpus", "/api/combinatorics/meld-design"):
            comb_py = INSTALL_ROOT / "lib" / "field-combinatorics-comb.py"
            cmd = {
                "/api/combinatorics/comb": "json",
                "/api/combinatorics/charts": "charts",
                "/api/combinatorics/cpus": "cpus",
                "/api/combinatorics/meld-design": "meld",
            }.get(path, "json")
            payload = _nexus_py_json(comb_py, [cmd], timeout=30) if comb_py.is_file() else {
                "schema": "field-combinatorics-comb/v1",
                "ok": False,
                "hint": "field-combinatorics-comb missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/combinatorics-threat", "/api/combinatorics/rejections"):
            sg = Path(os.environ.get("SG_ROOT", str(INSTALL_ROOT.parent.parent)))
            combo = sg / "Grok16" / "lib" / "field_combinatorics.py"
            payload = _nexus_py_json(combo, ["threat"], timeout=30) if combo.is_file() else {
                "schema": "field-combinatorics-threat/v1",
                "ok": False,
                "hint": "field_combinatorics missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/lang-manuals" or path == "/api/lang-manuals/":
            lm = INSTALL_ROOT / "lib" / "field-lang-manual-reader.py"
            if lm.is_file():
                payload = _nexus_py_json(lm, ["catalog", "--save"], timeout=60)
                if isinstance(payload, dict):
                    self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                    return
            self._send(200, json.dumps({"schema": "field-lang-manuals/v1", "ok": False, "manuals": []}), "application/json")
            return

        if path.startswith("/api/lang-manuals/"):
            lm = INSTALL_ROOT / "lib" / "field-lang-manual-reader.py"
            sub = path[len("/api/lang-manuals/") :].strip("/")
            parts = sub.split("/") if sub else []
            lang_id = parts[0] if parts else ""
            action = parts[1] if len(parts) > 1 else ""
            if lm.is_file() and lang_id:
                if action == "text":
                    proc = subprocess.run(
                        [sys.executable, str(lm), "text", lang_id],
                        capture_output=True,
                        text=True,
                        timeout=90,
                        env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL_ROOT), "NEXUS_STATE_DIR": str(STATE_DIR)},
                    )
                    self._send(200, proc.stdout or "", "text/plain; charset=utf-8")
                    return
                if action == "figure" and len(parts) > 2:
                    fig_id = parts[2]
                    payload = _nexus_py_json(lm, ["read", lang_id], timeout=90)
                    fig = (payload.get("figures") or {}).get(fig_id) if isinstance(payload, dict) else None
                    if fig and fig.get("data_url"):
                        self._send(200, json.dumps(fig), "application/json")
                        return
                    self._send(404, '{"ok":false,"error":"figure_missing"}', "application/json")
                    return
                if action == "generate" and self.command == "POST":
                    payload = _nexus_py_json(
                        INSTALL_ROOT / "lib" / "field-combinatronic-visuals.py",
                        ["book", lang_id],
                        timeout=120,
                    )
                    self._send(200, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
                    return
                payload = _nexus_py_json(lm, ["read", lang_id], timeout=90)
                if isinstance(payload, dict):
                    payload.pop("_figures_raw", None)
                    self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                    return
            self._send(404, json.dumps({"ok": False, "error": "manual_not_found"}), "application/json")
            return

        if path == "/api/znetwork/hostile":
            hostile_py = INSTALL_ROOT / "lib" / "znetwork-hostile-threat.py"
            if hostile_py.is_file():
                payload = _nexus_py_json(hostile_py, ["json"], timeout=25)
                if isinstance(payload, dict):
                    self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                    return
            self._send(
                200,
                json.dumps({
                    "schema": "znetwork-hostile-threat/v1",
                    "ok": False,
                    "hint": "znetwork-hostile-threat.py missing",
                }),
                "application/json",
            )
            return

        if path == "/api/znetwork/registry" or path.startswith("/api/znetwork/registry/"):
            reg_py = INSTALL_ROOT / "lib" / "znetwork-operator-registry.py"
            if not reg_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "znetwork_registry_missing"}), "application/json")
                return
            sub = path[len("/api/znetwork/registry") :].strip("/")
            if sub in ("", "json", "panel"):
                payload = _nexus_py_json(reg_py, ["json"], timeout=30)
            elif sub == "profile":
                payload = _nexus_py_json(reg_py, ["profile"], timeout=20)
            elif sub == "mesh":
                qs = self.path.split("?", 1)[-1] if "?" in self.path else ""
                query = ""
                for part in qs.split("&"):
                    if part.startswith("q="):
                        query = unquote(part[3:])
                        break
                payload = _nexus_py_json(reg_py, ["mesh", query] if query else ["mesh"], timeout=25)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_registry_route"}), "application/json")
                return
            self._send(200, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path == "/api/znetwork/vault" or path.startswith("/api/znetwork/vault/"):
            vault_py = INSTALL_ROOT / "lib" / "znetwork-secure-vault.py"
            sub = path[len("/api/znetwork/vault") :].strip("/")
            if not vault_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "znetwork_vault_missing"}), "application/json")
                return
            if sub in ("", "json", "panel"):
                payload = _nexus_py_json(vault_py, ["json"], timeout=30)
            elif sub == "queue":
                payload = _nexus_py_json(vault_py, ["queue"], timeout=20)
            elif sub == "wire-point":
                qs = self.path.split("?", 1)[-1] if "?" in self.path else ""
                rotate = "rotate=1" in qs or "rotate=true" in qs.lower()
                payload = _nexus_py_json(vault_py, ["wire-point"] + (["--rotate"] if rotate else []), timeout=15)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_vault_route"}), "application/json")
                return
            self._send(200, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path == "/api/znetwork":
            orch = INSTALL_ROOT / "lib" / "znetwork-orchestrator.py"
            if orch.is_file():
                posture = _nexus_py_json(orch, ["json"], timeout=35)
                if isinstance(posture, dict) and posture.get("schema"):
                    self._send(200, json.dumps(posture, ensure_ascii=False), "application/json")
                    return
            if ZNETWORK_STATUS.is_file():
                try:
                    self._send(200, ZNETWORK_STATUS.read_text(encoding="utf-8"), "application/json")
                except OSError:
                    self._send(503, '{"ok":false,"error":"znetwork store unreadable"}', "application/json")
            else:
                self._send(
                    200,
                    json.dumps({
                        "schema": "znetwork-status/v1",
                        "ok": False,
                        "ready": False,
                        "hint": "Run ./nexus.sh --restart to publish ZNetwork status",
                    }),
                    "application/json",
                )
            return

        if path == "/api/queen-eyeball":
            payload = _panel_slice(
                "field_eyeball",
                live=_queen_ball_dispatch(_queen_eyeball_script(), timeout=120),
                default={"schema": "queen-eyeball-arm/v1", "posture": "assistive"},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path in ("/api/queen-earball", "/api/final-ear", "/api/earball"):
            payload = _panel_slice(
                "field_earball",
                live=_queen_ball_dispatch(_queen_earball_script(), timeout=120),
                default={"schema": "queen-earball-hostess7/v1", "posture": "assistive"},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path in ("/api/queen-mouthball", "/api/final-mouth", "/api/mouthball"):
            payload = _panel_slice(
                "field_mouthball",
                live=_queen_ball_dispatch(_queen_mouthball_script(), timeout=120),
                default={"schema": "queen-mouthball-hostess7/v1", "posture": "assistive"},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/trust-strike":
            payload = _panel_slice(
                "trust_strike",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "trust-strike-engine.py", ["summary"], timeout=45),
                default={"schema": "trust-strike/v1", "strikes": []},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-weapons":
            stack = _panel_slice(
                "field_stack",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "queen_field_nexus.py", ["json"], timeout=120),
                default={"schema": "nexus-field-stack/v1"},
            )
            payload = {
                "schema": "nexus-field-weapons/v1",
                "nexus_defenses": stack.get("nexus_defenses") or {},
                "final_eye_weapons": stack.get("final_eye_weapons") or {},
                "trust_strike": stack.get("trust_strike") or {},
                "eyeball": stack.get("eyeball") or {},
                "gates_held": stack.get("gates_held"),
                "queen_verdict": stack.get("queen_verdict"),
            }
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/queen-boot":
            qb = _queen_boot_script()
            if qb.is_file():
                payload = _nexus_py_json(qb, ["json"], timeout=45)
            else:
                payload = {"schema": "queen-field-boot/v1", "error": "boot_missing"}
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/grok-build":
            gb = _grok_build_script()
            if gb.is_file():
                payload = _nexus_py_json(gb, ["json"])
            else:
                payload = {"schema": "grok-build-bridge/v1", "secure_channel": False, "error": "bridge_missing"}
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/queen-build":
            qb = _queen_build_script()
            if qb.is_file():
                payload = _nexus_py_json(qb, ["json"])
            else:
                payload = {
                    "schema": "queen-build/v1",
                    "inside": False,
                    "motto": "Run Queen/scripts/install-inside.sh",
                    "stages": [],
                }
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-rf":
            payload = _panel_slice(
                "field_rf",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-rf-sentinel.py", ["json"]),
                default={"antenna": {"mode": "standby"}, "bursts": []},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/plugins":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "nexus-plugins.py", ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/plugins/registry":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "nexus-plugins.py", ["registry"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/terror-spiderweb":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "terror-spiderweb.py",
                ["json"],
                timeout=8,
            )
            if not isinstance(payload, dict) or not payload.get("schema"):
                payload = _panel_slice(
                    "terror_spiderweb",
                    default={"schema": "terror-spiderweb/v2", "mode": "idle", "nodes": [], "edges": [], "stats": {"idle": True}},
                )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/terror-spiderweb/sections":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "terror-spiderweb.py",
                ["sections"],
                timeout=5,
            )
            self._send(200, json.dumps(payload or {"sections": [], "ascii": "", "idle": True}), "application/json")
            return

        if path == "/api/terror-spiderweb/gps-table":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "terror-spiderweb.py", ["gps-table"], timeout=5)
            self._send(200, json.dumps(payload or {"homes": [], "count": 0}), "application/json")
            return

        if path == "/api/terror-spiderweb/registry":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "terror-spiderweb.py", ["registry"], timeout=5)
            self._send(200, json.dumps(payload or {}), "application/json")
            return

        if path == "/api/hostility-priority":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostility-priority.py", ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/census-field":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "census-field-populate.py", ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/thermal-earth":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "thermal-earth-field.py", ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/thermal-earth/bodies":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "thermal-earth-field.py", ["bodies"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/precision-field":
            payload = _panel_slice(
                "precision_field",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "precision-field.py", ["json"]),
                default={"entities": [], "edges": [], "stats": {}},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/gps-precision":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "gps-precision.py", ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/human-registry":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "human-registry.py", ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/audio-train":
            payload = _panel_slice(
                "audio_train",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "audio-train.py", ["json"]),
                default={"schema": "audio-train/v1", "stats": {}},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/pet-signal-guard":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "pet-signal-guard.py", ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/home-protector":
            force_scan = str(query.get("scan", query.get("harvest", ["0"]))[0]).strip().lower() in (
                "1", "true", "yes", "on",
            )
            if force_scan:
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "home-protector.py",
                    ["json"],
                ) or {"schema": "home-protector/v1", "stats": {}}
            else:
                payload = _panel_slice(
                    "home_protector",
                    live=_nexus_py_json(INSTALL_ROOT / "lib" / "home-protector.py", ["json"]),
                    default={"schema": "home-protector/v1", "stats": {}},
                )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/local-services":
            force_scan = str(query.get("scan", query.get("build", ["0"]))[0]).strip().lower() in (
                "1", "true", "yes", "on",
            )
            if force_scan:
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "local-services-audit.py",
                    ["build"],
                ) or {"schema": "local-services/v1", "stats": {}}
            else:
                payload = _panel_slice(
                    "local_services",
                    live=_nexus_py_json(INSTALL_ROOT / "lib" / "local-services-audit.py", ["json"]),
                    default={"schema": "local-services/v1", "stats": {}},
                )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/signals-field":
            payload = _panel_slice(
                "signals_field",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "signals-field.py", ["json"]),
                default={"schema": "signals-field/v1", "stats": {}, "antennas": []},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/stress-terror-discern":
            script = INSTALL_ROOT / "lib" / "field-stress-terror-discern.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=20)
            else:
                payload = {"schema": "field-stress-terror-discern/v1", "ok": False, "error": "stress_terror_discern_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field/field", "/api/field/plate-field"):
            publish = str(query.get("publish", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            payload = _field_field_payload(publish=publish)
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field/parallel":
            publish = str(query.get("publish", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            payload = _field_parallel_payload(publish=publish)
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-plate-field":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-plate-field.py", ["json"], timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/field-hardware":
            payload = _panel_slice(
                "field_hardware",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-hardware-probe.py", ["json"]),
                default={"schema": "field-hardware-probe/v1"},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-hazard-onset":
            payload = _panel_slice(
                "field_hazard_onset",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-hazard-onset.py", ["panel"]),
                default={"schema": "field-hazard-onset-panel/v1"},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/lethal-enforcement":
            payload = _panel_slice(
                "lethal_enforcement",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "lethal-enforcement.py", ["panel"]),
                default={"schema": "lethal-enforcement-panel/v1", "merciless": True},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/hostess7-lethal-insight":
            payload = _panel_slice(
                "hostess7_lethal_insight",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-lethal-insight.py", ["panel"]),
                default={"schema": "hostess7-lethal-insight-panel/v1"},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path.startswith("/api/kill-codes"):
            if path == "/api/kill-codes":
                payload = _kill_codes_json(["catalog"], timeout=30)
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                return
            if path == "/api/kill-codes/recommend":
                alert_id = str(query.get("alert", [""])[0]).strip()
                alert_json = "{}"
                if alert_id:
                    doc = _jockey_json(["alerts"], timeout=30)
                    found = next(
                        (
                            a
                            for a in (doc.get("all_alerts") or doc.get("jockey_alerts") or [])
                            if a.get("id") == alert_id
                        ),
                        None,
                    )
                    if found:
                        alert_json = json.dumps(found, ensure_ascii=False)
                payload = _kill_codes_json(["recommend", alert_json], timeout=30)
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                return

        if path.startswith("/api/jockey/"):
            if path == "/api/jockey/alerts":
                payload = _jockey_json(["alerts"], timeout=30)
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                return
            if path == "/api/jockey/actions":
                alert_id = str(query.get("alert", [""])[0]).strip()
                args = ["actions"]
                if alert_id:
                    args.append(alert_id)
                payload = _jockey_json(args, timeout=30)
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                return

        if path == "/api/hostess7-autonomous":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-autonomous.py",
                ["status"],
                timeout=30,
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/hostess7-growth":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-growth.py",
                ["status"],
                timeout=30,
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/hostess7-neural":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-neural.py",
                ["status"],
                timeout=45,
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/hostess7-master":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-master.py",
                ["panel"],
                timeout=45,
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/hostess7-truth":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-truth-rating.py",
                ["status"],
                timeout=30,
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/hostess7-questionnaire":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-truth-rating.py",
                ["questionnaire"],
                timeout=600,
            )
            self._send(200, json.dumps(payload), "application/json")
            return
        if path == "/api/hostess7-master-sim":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-master-sim.py",
                ["status"],
                timeout=30,
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/hostess7-command/sketch":
            sketch = STATE_DIR / "hostess7-sketches" / "latest.png"
            if sketch.is_file():
                try:
                    self._send(200, sketch.read_bytes(), "image/png")
                except OSError:
                    self._send(404, "sketch unreadable", "text/plain")
            else:
                self._send(404, "no sketch", "text/plain")
            return

        if path == "/api/hostess7-command":
            refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            cache_path = STATE_DIR / "hostess7-command-panel.json"
            if not refresh and cache_path.is_file():
                try:
                    cached = json.loads(cache_path.read_text(encoding="utf-8"))
                    if isinstance(cached, dict) and cached.get("schema") == "hostess7-command/v1":
                        cached["_panel_cache"] = True
                        self._send(200, json.dumps(cached), "application/json")
                        return
                except (OSError, json.JSONDecodeError):
                    pass
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-command.py",
                ["panel"],
                timeout=60,
            ) or _panel_slice(
                "hostess7_command",
                live=None,
                default={"schema": "hostess7-command/v1", "transcript": [], "proposed_updates": []},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-antenna" or path.startswith("/api/field-antenna/"):
            payload = {
                "schema": "field-antenna/v1",
                "removed": True,
                "reason": "field_antenna_removed",
                "ok": False,
            }
            self._send(410, json.dumps(payload), "application/json")
            return

        if path == "/api/field-radio":
            payload = _panel_slice(
                "field_radio",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-radio-catcher.py", ["json"]),
                default={"schema": "field-radio-catcher/v1", "station_menu": []},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-dns":
            live_req = str(query.get("live", ["0"])[0]).strip().lower() in ("1", "true", "yes")
            if live_req:
                live = _nexus_py_json(INSTALL_ROOT / "lib" / "field-dns.py", ["json"], timeout=25)
                payload = _panel_slice(
                    "field_dns",
                    live=live,
                    default={"schema": "field-dns/v2"},
                )
            else:
                payload = _read_field_panel_file("field_dns")
                if payload is None:
                    live = _nexus_py_json(INSTALL_ROOT / "lib" / "field-dns.py", ["json"], timeout=25)
                    payload = _panel_slice(
                        "field_dns",
                        live=live,
                        default={"schema": "field-dns/v2"},
                    )
            payload = _merge_live_dhcp_into_dns(payload)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-dhcp":
            live = _nexus_py_json(INSTALL_ROOT / "lib" / "field-dhcp.py", ["json"], timeout=12)
            payload = _panel_slice(
                "field_dhcp",
                live=live,
                default={"schema": "field-dhcp/v2", "lease_count": 0, "leases_detailed": [], "lease_history_events": []},
            )
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-outside-talk":
            payload = _panel_slice(
                "field_outside_talk",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-outside-talk.py", ["json"]),
                default={"schema": "field-outside-talk/v1"},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-drive":
            payload = _panel_slice(
                "field_drive",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-drive-system.py", ["json"]),
                default={"schema": "field-drive-system/v1", "drives": []},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-brain":
            payload = _panel_slice(
                "field_brain",
                live=_nexus_py_json(INSTALL_ROOT / "lib" / "field-brain-panel.py", ["json"]),
                default={"schema": "field-brain/v1", "ok": True, "github_library_books": 0, "manifest_count": 0},
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-drive/drives":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-drive-system.py",
                ["talk", json.dumps({"op": "drives"})],
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path in ("/api/field-filesystem", "/api/filesystem-update"):
            fs_py = INSTALL_ROOT / "lib" / "field-filesystem-update.py"
            payload = _nexus_py_json(fs_py, ["json"], timeout=45) if fs_py.is_file() else {
                "schema": "field-filesystem-update/v1",
                "ok": False,
                "hint": "field-filesystem-update missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/diagnostic-mode", "/api/field-diagnostic"):
            diag_py = INSTALL_ROOT / "lib" / "field-diagnostic-mode.py"
            payload = _nexus_py_json(diag_py, ["json"], timeout=120) if diag_py.is_file() else {
                "schema": "field-diagnostic-mode/v1",
                "ok": False,
                "hint": "field-diagnostic-mode missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/hostess-profile":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess-profile.py", ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/panel-language":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "panel-i18n.py", ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/host-security-tier":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "host-security-tier.py", ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/fcc-signal-lookup":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "fcc-signal-lookup.py", ["identify"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/heavyboi/status":
            pending = STATE_DIR / "nexus-kill-intel-pending.json"
            log_path = STATE_DIR / "heavyboi-ingest-log.jsonl"
            lines = 0
            try:
                if log_path.is_file():
                    lines = sum(1 for _ in log_path.open(encoding="utf-8"))
            except OSError:
                lines = 0
            payload = {
                "ok": True,
                "version": "7.8.0",
                "hostess_version": "7",
                "pending": pending.is_file(),
                "ingest_log_lines": lines,
            }
            self._send(200, json.dumps(payload), "application/json")
            return

        if path.startswith("/api/human-registry/resolve"):
            ip = str(query.get("ip", [""])[0]).strip()
            if not ip:
                self._send(400, json.dumps({"error": "missing ip"}), "application/json")
                return
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "human-registry.py", ["resolve", ip])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/existence-identity":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "existence-identity.py", ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/existence-identity/table":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "existence-identity.py", ["table"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/police-agencies":
            region = str(query.get("region", [""])[0]).strip() or None
            script = INSTALL_ROOT / "lib" / "police-agency-db.py"
            if region:
                payload = _nexus_py_json(script, ["list", region])
            else:
                payload = _nexus_py_json(script, ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/gov-intel":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "gov-intel-db.py", ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/program-tags":
            program_id = str(query.get("id", [""])[0]).strip()
            script = INSTALL_ROOT / "lib" / "program-tags-db.py"
            if program_id:
                payload = _nexus_py_json(script, ["get", program_id])
            else:
                payload = _nexus_py_json(script, ["json"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/gov-intel/image":
            rel = str(query.get("path", [""])[0]).strip()
            if not rel:
                self._send(400, "missing path", "text/plain")
                return
            gi_py = INSTALL_ROOT / "lib" / "gov-intel-db.py"
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("gov_intel_db", gi_py)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                got = mod.get_image(rel)
                if not got:
                    self._send(404, "not found", "text/plain")
                    return
                data, ctype = got
                self._send(200, data, ctype)
            except Exception:
                self._send(404, "not found", "text/plain")
            return

        if path == "/api/field":
            full = str(query.get("full", ["1"])[0]).strip().lower() in ("1", "true", "yes")
            self._send(200, _read_status_json(full=full), "application/json")
            return

        if path.startswith("/api/library/"):
            script = INSTALL_ROOT / "lib" / "h7-library-bridge.py"
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            env.setdefault("HOSTESS7_ROOT", str(_resolve_hostess7_root()))
            env.setdefault("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage")

            def _lib_json(args: list[str], *, timeout: int = 45) -> dict:
                if not script.is_file():
                    return {"ok": False, "error": "library_bridge_missing"}
                proc = subprocess.run(
                    [sys.executable, str(script), *args],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=env,
                )
                try:
                    return json.loads(proc.stdout or "{}")
                except json.JSONDecodeError:
                    return {"ok": False, "error": "library_read_failed", "detail": (proc.stderr or "")[:400]}

            if path == "/api/library/page":
                book_id = str(query.get("book", [""])[0]).strip()
                page = int(query.get("page", ["1"])[0] or "1")
                chars = str(query.get("chars", [""])[0]).strip()
                if not book_id:
                    self._send(400, json.dumps({"ok": False, "error": "missing book"}), "application/json")
                    return
                args = ["page", book_id, str(page)]
                if chars.isdigit():
                    args.append(chars)
                payload = _lib_json(args)
                self._send(200 if payload.get("ok") else 404, json.dumps(payload), "application/json")
                return

            if path == "/api/library/full":
                book_id = str(query.get("book", [""])[0]).strip()
                if not book_id:
                    self._send(400, json.dumps({"ok": False, "error": "missing book"}), "application/json")
                    return
                payload = _lib_json(["full", book_id], timeout=120)
                self._send(200 if payload.get("ok") else 404, json.dumps(payload), "application/json")
                return

            if path == "/api/library/catalog":
                refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
                profile = str(query.get("profile", [""])[0]).strip()
                if not refresh and not profile:
                    fast = _load_h7_library_catalog_fast()
                    if fast:
                        self._send(200, json.dumps(fast), "application/json")
                        return
                args = ["build"]
                if profile:
                    args.extend(["--profile", profile])
                if refresh:
                    args.append("--force")
                payload = _lib_json(args, timeout=90)
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/library/profiles":
                payload = _lib_json(["profiles"])
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/library/war":
                payload = _lib_json(["war"], timeout=90)
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/library/librarians":
                teach = str(query.get("teach", ["0"])[0]).strip().lower() in ("1", "true", "yes")
                args = ["librarians"]
                if teach:
                    args.append("--teach")
                    lib_id = str(query.get("id", [""])[0]).strip()
                    if lib_id:
                        args.extend(["--id", lib_id])
                payload = _lib_json(args, timeout=60)
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/library/knowledge":
                book_id = str(query.get("book", [""])[0]).strip()
                q = str(query.get("q", [""])[0]).strip()
                args = ["reader", "knowledge"]
                if book_id:
                    args.append(book_id)
                elif q:
                    args.extend(["", q])
                payload = _lib_json(args, timeout=45)
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/library/search":
                q = str(query.get("q", query.get("query", [""]))[0]).strip()
                if not q:
                    self._send(400, json.dumps({"ok": False, "error": "missing query"}), "application/json")
                    return
                payload = _lib_json(["search", q])
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/library/atlas":
                payload = _lib_json(["atlas"], timeout=90)
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/library/passages":
                q = str(query.get("q", query.get("query", [""]))[0]).strip()
                if not q:
                    self._send(400, json.dumps({"ok": False, "error": "missing query"}), "application/json")
                    return
                payload = _lib_json(["passages", q], timeout=60)
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/library/topics":
                payload = _lib_json(["topics"], timeout=45)
                self._send(200, json.dumps(payload), "application/json")
                return

            if path in ("/api/bugfinder", "/api/code-bugfinder"):
                bug_py = INSTALL_ROOT / "lib" / "field-code-bugfinder.py"
                if not bug_py.is_file():
                    self._send(500, json.dumps({"ok": False, "error": "bugfinder_missing"}), "application/json")
                    return
                proc = subprocess.run(
                    [sys.executable, str(bug_py), "json"],
                    capture_output=True,
                    text=True,
                    timeout=45,
                    env=env,
                )
                try:
                    payload = json.loads(proc.stdout or "{}")
                except json.JSONDecodeError:
                    payload = {"ok": False, "error": "bugfinder_parse_failed"}
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/bugfinder/scan":
                target = str(query.get("path", query.get("target", [""]))[0]).strip()
                if not target:
                    self._send(400, json.dumps({"ok": False, "error": "missing path"}), "application/json")
                    return
                bug_py = INSTALL_ROOT / "lib" / "field-code-bugfinder.py"
                max_raw = str(query.get("max", ["256"])[0]).strip()
                max_c = int(max_raw) if max_raw.isdigit() else 256
                proc = subprocess.run(
                    [sys.executable, str(bug_py), "scan", target, "--max", str(max_c)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=env,
                )
                try:
                    payload = json.loads(proc.stdout or "{}")
                except json.JSONDecodeError:
                    payload = {"ok": False, "error": "bugfinder_scan_failed", "detail": (proc.stderr or "")[:300]}
                self._send(200 if payload.get("ok", True) else 500, json.dumps(payload), "application/json")
                return

            if path == "/api/bugfinder/ironclad-cycle":
                bug_py = INSTALL_ROOT / "lib" / "field-code-bugfinder.py"
                if not bug_py.is_file():
                    self._send(500, json.dumps({"ok": False, "error": "bugfinder_missing"}), "application/json")
                    return
                max_t = str(query.get("max_targets", ["6"])[0]).strip()
                max_c = str(query.get("max_compares", ["48"])[0]).strip()
                args = [sys.executable, str(bug_py), "ironclad-cycle"]
                if max_t.isdigit():
                    args.extend(["--max-targets", max_t])
                if max_c.isdigit():
                    args.extend(["--max-compares", max_c])
                proc = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    env=env,
                )
                try:
                    payload = json.loads(proc.stdout or "{}")
                except json.JSONDecodeError:
                    payload = {"ok": False, "error": "bugfinder_ironclad_cycle_failed", "detail": (proc.stderr or "")[:300]}
                self._send(200 if payload.get("ok") else 500, json.dumps(payload), "application/json")
                return

            if path == "/api/bugfinder/kb":
                q = str(query.get("q", query.get("query", [""]))[0]).strip()
                if not q:
                    self._send(400, json.dumps({"ok": False, "error": "missing query"}), "application/json")
                    return
                bug_py = INSTALL_ROOT / "lib" / "field-code-bugfinder.py"
                proc = subprocess.run(
                    [sys.executable, str(bug_py), "kb", q],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=env,
                )
                try:
                    payload = json.loads(proc.stdout or "{}")
                except json.JSONDecodeError:
                    payload = {"ok": False, "error": "bugfinder_kb_failed"}
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/library/pagination":
                book_id = str(query.get("book", [""])[0]).strip()
                if not book_id:
                    self._send(400, json.dumps({"ok": False, "error": "missing book"}), "application/json")
                    return
                reinform_py = INSTALL_ROOT / "lib" / "h7-library-reinform.py"
                payload = _nexus_py_json(reinform_py, ["panel", book_id], timeout=45)
                self._send(200 if payload.get("ok") else 404, json.dumps(payload or {"ok": False}), "application/json")
                return

            if path == "/api/library/audit":
                reinform_py = INSTALL_ROOT / "lib" / "h7-library-reinform.py"
                payload = _nexus_py_json(reinform_py, ["audit"], timeout=300)
                self._send(200, json.dumps(payload or {"ok": False}), "application/json")
                return

            if path == "/api/library/overlap":
                reinform_py = INSTALL_ROOT / "lib" / "h7-library-reinform.py"
                limit = str(query.get("limit", ["0"])[0]).strip()
                args = ["overlap"]
                if limit.isdigit() and int(limit) > 0:
                    args.append(f"--limit={limit}")
                payload = _nexus_py_json(reinform_py, args, timeout=120)
                self._send(200, json.dumps(payload or {"ok": False}), "application/json")
                return

            if path.startswith("/api/library/lie-librarian"):
                lie_py = INSTALL_ROOT / "lib" / "h7-lie-librarian.py"
                sub = path.replace("/api/library/lie-librarian", "").strip("/")
                book_id = str(query.get("book", [""])[0]).strip()
                q = str(query.get("q", query.get("search", [""]))[0]).strip()
                audience = str(query.get("audience", ["both"])[0]).strip() or "both"
                aud_arg = f"--audience={audience}"
                if sub == "build" or str(query.get("build", ["0"])[0]).strip().lower() in ("1", "true", "yes"):
                    limit = str(query.get("limit", ["0"])[0]).strip()
                    args = ["build"]
                    if str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes"):
                        args.append("--refresh")
                    if limit.isdigit() and int(limit) > 0:
                        args.append(f"--limit={limit}")
                    payload = _nexus_py_json(lie_py, args, timeout=180)
                elif sub == "counsel":
                    args = ["counsel", aud_arg]
                    if book_id:
                        args.extend(["--book", book_id])
                    elif q:
                        args.append(q)
                    payload = _nexus_py_json(lie_py, args, timeout=60)
                elif sub == "search" or q:
                    args = ["search", q or book_id]
                    payload = _nexus_py_json(lie_py, args, timeout=60)
                elif book_id:
                    refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
                    args = ["book", book_id, aud_arg]
                    if refresh:
                        args.append("--refresh")
                    payload = _nexus_py_json(lie_py, args, timeout=90)
                else:
                    payload = _nexus_py_json(lie_py, ["panel"], timeout=45)
                self._send(200 if payload.get("ok") else 404, json.dumps(payload or {"ok": False}), "application/json")
                return

            if path == "/api/library/lies":
                book_id = str(query.get("book", [""])[0]).strip()
                if not book_id:
                    self._send(400, json.dumps({"ok": False, "error": "missing book"}), "application/json")
                    return
                reinform_py = INSTALL_ROOT / "lib" / "h7-library-reinform.py"
                refresh = str(query.get("refresh", ["0"])[0]).strip().lower() in ("1", "true", "yes")
                if refresh:
                    payload = _nexus_py_json(reinform_py, ["lies", book_id], timeout=90)
                else:
                    panel = _nexus_py_json(reinform_py, ["panel", book_id], timeout=45)
                    if panel.get("lies_index"):
                        payload = {"ok": True, **(panel.get("lies_index") or {})}
                    else:
                        payload = _nexus_py_json(reinform_py, ["lies", book_id], timeout=90)
                self._send(200 if payload.get("ok") else 404, json.dumps(payload or {"ok": False}), "application/json")
                return

            if path == "/api/library/corrections":
                book_id = str(query.get("book", [""])[0]).strip()
                if not book_id:
                    self._send(400, json.dumps({"ok": False, "error": "missing book"}), "application/json")
                    return
                reinform_py = INSTALL_ROOT / "lib" / "h7-library-reinform.py"
                payload = _nexus_py_json(reinform_py, ["corrections", book_id], timeout=45)
                self._send(200, json.dumps(payload or {"ok": False}), "application/json")
                return

            if path == "/api/library/reinform":
                book_id = str(query.get("book", [""])[0]).strip()
                if not book_id:
                    self._send(400, json.dumps({"ok": False, "error": "missing book"}), "application/json")
                    return
                reinform_py = INSTALL_ROOT / "lib" / "h7-library-reinform.py"
                apply = str(query.get("apply", ["0"])[0]).strip().lower() in ("1", "true", "yes")
                args = ["reinform", book_id]
                if apply:
                    args.append("--apply")
                payload = _nexus_py_json(reinform_py, args, timeout=120)
                self._send(200 if payload.get("ok") else 404, json.dumps(payload or {"ok": False}), "application/json")
                return

            if path == "/api/library/truth":
                book_id = str(query.get("book", [""])[0]).strip()
                idx_raw = str(query.get("index", [""])[0]).strip()
                sentence_text = str(query.get("text", [""])[0]).strip()
                if not book_id:
                    self._send(400, json.dumps({"ok": False, "error": "missing book"}), "application/json")
                    return
                truth_script = INSTALL_ROOT / "lib" / "h7-library-truth.py"
                args = ["sentence", book_id]
                if idx_raw.isdigit():
                    args.append(idx_raw)
                if sentence_text:
                    args.append(sentence_text)
                proc = subprocess.run(
                    [sys.executable, str(truth_script), *args],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=env,
                )
                try:
                    payload = json.loads(proc.stdout or "{}")
                except json.JSONDecodeError:
                    payload = {"ok": False, "error": "truth_parse_failed", "detail": (proc.stderr or "")[:300]}
                self._send(200 if payload.get("ok") else 404, json.dumps(payload), "application/json")
                return

            if path == "/api/library/truth/unknown":
                truth_script = INSTALL_ROOT / "lib" / "h7-library-truth.py"
                proc = subprocess.run(
                    [sys.executable, str(truth_script), "unknown"],
                    capture_output=True,
                    text=True,
                    timeout=45,
                    env=env,
                )
                try:
                    payload = json.loads(proc.stdout or "{}")
                except json.JSONDecodeError:
                    payload = {"ok": False, "error": "unknown_queue_failed"}
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/library/dewey":
                profile = str(query.get("profile", [""])[0]).strip()
                args = ["dewey"]
                if profile:
                    args.extend(["--profile", profile])
                payload = _lib_json(args, timeout=90)
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/library/fonts":
                payload = _lib_json(["fonts"])
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/library/fingerprint":
                payload = _lib_json(["fingerprint"])
                self._send(200, json.dumps(payload), "application/json")
                return

            if path == "/api/library/checkout":
                book_id = str(query.get("book", [""])[0]).strip()
                if book_id:
                    payload = _lib_json(["checkout-status"])
                    if payload.get("active"):
                        hit = next((r for r in payload["active"] if r.get("book_id") == book_id), None)
                        payload = {"ok": bool(hit), "checkout": hit, "book_id": book_id}
                    else:
                        payload = {"ok": False, "checkout": None, "book_id": book_id}
                else:
                    payload = _lib_json(["checkout-status"])
                self._send(200, json.dumps(payload), "application/json")
                return

            if path.startswith("/api/g16/language-test/"):
                matrix_py = INSTALL_ROOT / "lib" / "g16-language-test-matrix.py"
                sub = path[len("/api/g16/language-test/") :].strip("/") or "posture"
                if sub == "log":
                    offset = int(query.get("offset", ["0"])[0] or "0")
                    payload = _nexus_py_json(matrix_py, ["log", str(offset)], timeout=30)
                elif sub == "matrix":
                    payload = _nexus_py_json(matrix_py, ["matrix"], timeout=45)
                elif sub in ("status", "posture"):
                    payload = _nexus_py_json(matrix_py, ["posture"], timeout=25)
                else:
                    payload = {"ok": False, "error": "unknown_g16_language_test_route", "sub": sub}
                self._send(200, json.dumps(payload or {"ok": False}), "application/json")
                return

            if path == "/api/library/cover":
                book_id = str(query.get("book", [""])[0]).strip()
                side = str(query.get("side", ["front"])[0]).strip() or "front"
                fmt = str(query.get("format", ["png"])[0]).strip() or "png"
                if not book_id:
                    self._send(400, "missing book", "text/plain")
                    return
                try:
                    import importlib.util
                    lib_py = INSTALL_ROOT / "lib" / "h7-library-librarian.py"
                    spec = importlib.util.spec_from_file_location("h7_library_librarian", lib_py)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    got = mod.get_cover_bytes(book_id, side, fmt=fmt)
                    if not got and fmt == "png":
                        cov_py = INSTALL_ROOT / "lib" / "sdf-book-covers.py"
                        bib = mod.load_bibliography_index().get(book_id) or mod.enrich_record(book_id)
                        subprocess.run(
                            [sys.executable, str(cov_py), book_id, side],
                            capture_output=True,
                            timeout=30,
                            env=env,
                        )
                        got = mod.get_cover_bytes(book_id, side, fmt=fmt)
                    if not got:
                        self._send(404, "cover not on field drive", "text/plain")
                        return
                    data, ctype = got
                    self._send(200, data, ctype)
                except Exception:
                    self._send(404, "cover not found", "text/plain")
                return

        if path == "/api/data":
            items = []
            for key, fp in DATA_FILES.items():
                items.append({
                    "id": key,
                    "path": str(fp),
                    "exists": fp.is_file(),
                    "size": fp.stat().st_size if fp.is_file() else 0,
                    "url": f"/api/data/{key}",
                })
            self._send(200, json.dumps({"files": items}), "application/json")
            return

        if path.startswith("/api/data/"):
            key = path.split("/api/data/", 1)[1]
            panel_key = key.replace("-", "_")
            if panel_key in PANEL_PARALLEL_KEYS:
                cached = _panel_slice(panel_key, default={})
                if cached.get("_field_cache"):
                    self._send(200, json.dumps(cached), "application/json")
                    return
            fp = DATA_FILES.get(key)
            if not fp or not fp.is_file():
                self._send(404, "not found", "text/plain")
                return
            ctype = "application/json" if fp.suffix == ".json" else "text/plain"
            self._send(200, fp.read_text(encoding="utf-8", errors="replace"), ctype)
            return

        if path == "/api/logs":
            catalog = {k: {"path": str(v), "exists": v.is_file()} for k, v in LOG_FILES.items()}
            self._send(200, json.dumps(catalog), "application/json")
            return

        if path.startswith("/api/logs/"):
            key = path.split("/api/logs/", 1)[1]
            fp = LOG_FILES.get(key)
            if not fp:
                self._send(404, "not found", "text/plain")
                return
            lines = int(query.get("lines", ["120"])[0])
            self._send(200, _tail_file(fp, lines), "text/plain")
            return

        if path == "/api/intel/scour":
            script = INSTALL_ROOT / "lib" / "vector-intel.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "vector-intel missing"}), "application/json")
                return
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            proc = subprocess.run(
                ["pythong", str(script), "scour"],
                capture_output=True,
                text=True,
                timeout=90,
                env=env,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                self._send(200, proc.stdout, "application/json")
            else:
                self._send(500, json.dumps({"ok": False, "error": "scour failed"}), "application/json")
            return

        if path == "/api/intel/lookup":
            ip = str(query.get("ip", [""])[0]).strip()
            if not ip:
                self._send(400, json.dumps({"ok": False, "error": "missing ip"}), "application/json")
                return
            script = INSTALL_ROOT / "lib" / "vector-intel.py"
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            proc = subprocess.run(
                ["pythong", str(script), "lookup", ip],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            if proc.returncode == 0:
                self._send(200, proc.stdout, "application/json")
            else:
                self._send(500, json.dumps({"ok": False, "error": "lookup failed"}), "application/json")
            return

        if path in (
            "/celebrate",
            "/celebrate/",
            "/everyone",
            "/everyone/",
            "/everyone-online",
            "/everyone-online/",
            "/field-everyone-online",
            "/field-everyone-online/",
            "/party",
            "/party/",
        ):
            target = PANEL_DIR / "field-everyone-online.html"
        elif path in (
            "/planetary-rescue",
            "/planetary-rescue/",
            "/world-rescue",
            "/world-rescue/",
            "/rescue-more",
            "/rescue-more/",
            "/field-planetary-rescue",
            "/field-planetary-rescue/",
            "/field-planetary-rescue.html",
        ):
            target = PANEL_DIR / "field-planetary-rescue.html"
        elif path in (
            "/whole-planet-live",
            "/whole-planet-live/",
            "/live-honest",
            "/live-honest/",
            "/live-honest-planet",
            "/live-honest-planet/",
            "/field-whole-planet-live",
            "/field-whole-planet-live/",
            "/field-whole-planet-live.html",
        ):
            target = PANEL_DIR / "field-whole-planet-live.html"
        elif path in (
            "/hardened-ours",
            "/hardened-ours/",
            "/ours",
            "/ours/",
            "/ours-hardened",
            "/ours-hardened/",
            "/field-hardened-ours",
            "/field-hardened-ours/",
            "/field-hardened-ours.html",
        ):
            target = PANEL_DIR / "field-hardened-ours.html"
            # Prefer freshly written website if present
            alt = STATE_DIR / "field-hardened-ours-website" / "index.html"
            if alt.is_file():
                target = alt
        elif path in (
            "/field-one-sole",
            "/field-one-sole/",
            "/field-one-sole-earth",
            "/field-one-sole-earth/",
            "/no-other-fields",
            "/no-other-fields/",
            "/sole-field",
            "/sole-field/",
            "/field-one-sole-earth.html",
        ):
            target = PANEL_DIR / "field-one-sole-earth.html"
            alt = STATE_DIR / "field-one-sole-earth-website" / "index.html"
            if alt.is_file():
                target = alt
        elif path in (
            "/only-internet",
            "/only-internet/",
            "/field-one-only-internet",
            "/field-one-only-internet/",
            "/field-only-internet",
            "/field-only-internet/",
            "/outside-field-one",
            "/outside-field-one/",
            "/field-one-only-internet.html",
        ):
            target = PANEL_DIR / "field-one-only-internet.html"
            alt = STATE_DIR / "field-one-only-internet-website" / "index.html"
            if alt.is_file():
                target = alt
        elif path in (
            "/hostess7-protector",
            "/hostess7-protector/",
            "/hostess7-sole-earth-protector",
            "/hostess7-sole-earth-protector/",
            "/sole-earth-protector",
            "/sole-earth-protector/",
            "/gladstone-protect",
            "/gladstone-protect/",
            "/hostess7-sole-earth-protector.html",
        ):
            target = PANEL_DIR / "hostess7-sole-earth-protector.html"
            alt = STATE_DIR / "hostess7-sole-earth-protector-website" / "index.html"
            if alt.is_file():
                target = alt
        elif path in (
            "/newcomer-sphere",
            "/newcomer-sphere/",
            "/sphere-destroy",
            "/sphere-destroy/",
            "/no-machine-again",
            "/no-machine-again/",
            "/newcomer-sphere-destroy",
            "/newcomer-sphere-destroy/",
            "/field-newcomer-attack-sphere-destroy.html",
        ):
            target = PANEL_DIR / "field-newcomer-attack-sphere-destroy.html"
            alt = STATE_DIR / "field-newcomer-attack-sphere-website" / "index.html"
            if alt.is_file():
                target = alt
        elif path in (
            "/no-detached-fields",
            "/no-detached-fields/",
            "/field-no-detached-fields",
            "/field-no-detached-fields/",
            "/field-one-no-gaps",
            "/field-one-no-gaps/",
            "/earth-stabilize",
            "/earth-stabilize/",
            "/field-no-detached-fields.html",
        ):
            target = PANEL_DIR / "field-no-detached-fields.html"
            alt = STATE_DIR / "field-no-detached-fields-website" / "index.html"
            if alt.is_file():
                target = alt
        elif path in (
            "/eternal-plane",
            "/eternal-plane/",
            "/field-one-eternal",
            "/field-one-eternal/",
            "/field-one-eternal-plane",
            "/field-one-eternal-plane/",
            "/field-one-eternal-plane.html",
        ):
            target = PANEL_DIR / "field-one-eternal-plane.html"
            alt = STATE_DIR / "field-one-eternal-plane-website" / "index.html"
            if alt.is_file():
                target = alt
        elif path in (
            "/weave-inside",
            "/weave-inside/",
            "/weave-everything-inside",
            "/weave-everything-inside/",
            "/field-1-forever",
            "/field-1-forever/",
            "/we-are-the-earth",
            "/we-are-the-earth/",
            "/field-weave-everything-inside.html",
        ):
            target = PANEL_DIR / "field-weave-everything-inside.html"
            alt = STATE_DIR / "field-weave-everything-inside-website" / "index.html"
            if alt.is_file():
                target = alt
        elif path in (
            "/c2",
            "/c2/",
            "/nexus-c2",
            "/nexus-c2/",
            "/nexus-c2.html",
            "/one-panel",
            "/one-panel/",
            "/panels",
            "/panels/",
        ):
            target = PANEL_DIR / "nexus-c2.html"
        elif path in (
            "/sitrep",
            "/sitrep/",
            "/field-sitrep",
            "/field-sitrep/",
            "/field-sitrep.html",
            "/status-board",
            "/status-board/",
        ):
            target = PANEL_DIR / "field-sitrep.html"
            try:
                body = target.read_text(encoding="utf-8")
            except OSError:
                self._send(404, "not found", "text/plain")
                return
            self._send(
                200,
                body,
                "text/html; charset=utf-8",
                extra_headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "X-Field-Live-Panel": "sitrep",
                },
            )
            return
        elif path in (
            "/botnet",
            "/botnet/",
            "/field-botnet",
            "/field-botnet/",
            "/field-botnet-hub",
            "/field-botnet-hub/",
            "/hub",
            "/hub/",
            "/field-botnet-hub.html",
        ):
            target = PANEL_DIR / "field-botnet-hub.html"
            # Always re-read disk HTML so live panel script updates without hard cache
            try:
                body = target.read_text(encoding="utf-8")
            except OSError:
                self._send(404, "not found", "text/plain")
                return
            # Bust stale browser tab script once per load
            if "data-live-hub" not in body:
                body = body.replace(
                    "<head>",
                    '<head>\n<meta http-equiv="Cache-Control" content="no-store"/>\n'
                    '<meta name="field-live" content="1"/>',
                    1,
                )
            self._send(
                200,
                body,
                "text/html; charset=utf-8",
                extra_headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Field-Live-Panel": "botnet-hub",
                },
            )
            return
        elif path in (
            "/never-reconnect",
            "/never-reconnect/",
            "/field-never-reconnect",
            "/field-never-reconnect/",
            "/field-never-reconnect.html",
            "/kills",
            "/kills/",
            "/dossiers",
            "/dossiers/",
        ):
            target = PANEL_DIR / "field-never-reconnect.html"
        elif path in (
            "/chat",
            "/chat/",
            "/field-chat",
            "/field-chat/",
            "/field-chat-hub",
            "/field-chat-hub/",
            "/field-chat-hub.html",
            "/talk-window",
            "/talk-window/",
        ):
            target = PANEL_DIR / "field-chat-hub.html"
        elif path in (
            "/maintenance",
            "/maintenance/",
            "/field-maintenance",
            "/field-maintenance/",
            "/field-maintenance-world",
            "/field-maintenance-world/",
            "/field-maintenance-world.html",
            "/world-notice",
            "/world-notice/",
        ):
            target = PANEL_DIR / "field-maintenance-world.html"
        elif path in (
            "/full-internet",
            "/full-internet/",
            "/full",
            "/featured-internet",
            "/featured-internet/",
            "/field-full-featured-internet",
            "/field-full-featured-internet/",
            "/field-full-featured-internet.html",
            "/our-internet",
            "/our-internet/",
        ):
            target = PANEL_DIR / "field-full-featured-internet.html"
        elif path in (
            "/world-ip-lease",
            "/world-ip-lease/",
            "/sole-ip-lease",
            "/sole-ip-lease/",
            "/every-ip",
            "/every-ip/",
            "/field-world-ip-lease-sole",
            "/field-world-ip-lease-sole/",
            "/field-world-ip-lease-sole.html",
        ):
            target = PANEL_DIR / "field-world-ip-lease-sole.html"
        elif path in (
            "/internet",
            "/internet/",
            "/home-internet",
            "/home-internet/",
            "/my-internet",
            "/my-internet/",
            "/field-home-internet",
            "/field-home-internet/",
            "/field-home-internet.html",
            "/autonet",
            "/autonet/",
        ):
            target = PANEL_DIR / "field-home-internet.html"
        elif path in (
            "/security",
            "/security/",
            "/home-security",
            "/home-security/",
            "/antivirus",
            "/antivirus/",
            "/field-home-security",
            "/field-home-security/",
            "/field-home-security.html",
            "/av",
            "/av/",
        ):
            target = PANEL_DIR / "field-home-security.html"
        elif path in ("/control-panel", "/control-panel/"):
            target = PANEL_DIR / "control-panel.html"
        elif path in ("/amouranth-live", "/amouranth-live/"):
            target = PANEL_DIR / "amouranth-live.html"
        elif path in ("/nexus-calc", "/nexus-calc/"):
            target = PANEL_DIR / "nexus-calc.html"
        elif path in ("/nexus-calendar", "/nexus-calendar/"):
            target = PANEL_DIR / "nexus-calendar.html"
        elif path in ("/field-gimp", "/field-gimp/"):
            target = PANEL_DIR / "field-gimp.html"
        elif path in ("/field-lock", "/field-lock/"):
            target = PANEL_DIR / "field-lock.html"
        elif path in ("/field-keepass", "/field-keepass/"):
            target = PANEL_DIR / "field-lock.html"
        elif path in ("/field-znetwork", "/field-znetwork/"):
            target = PANEL_DIR / "field-znetwork.html"
        elif path in ("/field-znetwork-vault", "/field-znetwork-vault/"):
            target = PANEL_DIR / "field-znetwork-vault.html"
        elif path in ("/g16-build-output", "/g16-build-output/", "/g16-build-output.html"):
            target = PANEL_DIR / "g16-build-output.html"
        elif path in ("/hands-attachments", "/hands-attachments/", "/hands-attachments.html"):
            target = PANEL_DIR / "hands-attachments.html"
        elif path in (
            "/library-bookshelf", "/library-bookshelf/",
            "/field-library-bookshelf", "/field-library-bookshelf/",
        ):
            target = PANEL_DIR / "field-library-bookshelf.html"
        elif path in ("/field-lang-manuals", "/field-lang-manuals/"):
            target = PANEL_DIR / "field-lang-manuals.html"
        elif path in ("/field-broadcaster", "/field-broadcaster/"):
            target = PANEL_DIR / "field-broadcaster.html"
        elif path in ("/field-obs", "/field-obs/"):
            target = PANEL_DIR / "field-broadcaster.html"
        elif path in ("/field-gpu", "/field-gpu/"):
            target = PANEL_DIR / "field-gpu.html"
        elif path in ("/field-vsync-locker", "/field-vsync-locker/"):
            target = PANEL_DIR / "field-vsync-locker.html"
        elif path in ("/grok-lab", "/grok-lab/"):
            target = PANEL_DIR / "grok-lab.html"
        elif path in ("/field-audio-dac", "/field-audio-dac/"):
            target = PANEL_DIR / "field-audio-dac.html"
        elif path in ("/field-audio-dac", "/field-audio-dac/"):
            target = PANEL_DIR / "field-audio-dac.html"
        elif path in ("/field-audio-settings", "/field-audio-settings/"):
            target = PANEL_DIR / "field-audio-settings.html"
        elif path in ("/field-display-settings", "/field-display-settings/"):
            target = PANEL_DIR / "field-display-settings.html"
        elif path in ("/field-ellie-fier", "/field-ellie-fier/"):
            target = PANEL_DIR / "field-ellie-diag.html"
        elif path.startswith("/field-ellie/"):
            slug = path[len("/field-ellie/") :].strip("/").split("/")[0].lower()
            if slug in ("network", "truth", "thermal", "firmware", "media", "sovereign", "diag"):
                target = PANEL_DIR / "field-ellie-diag.html"
        elif path in ("/field-gnu-terminal", "/field-gnu-terminal/", "/terminal", "/terminal/"):
            target = PANEL_DIR / "field-gnu-terminal-embed.html"
        elif path in ("/field-irc-chat", "/field-irc-chat/"):
            target = PANEL_DIR / "field-irc-chat-embed.html"
        elif path in ("/eol-code", "/eol-code/"):
            target = PANEL_DIR / "eol-code.html"
        elif path in ("/controller-test", "/controller-test/"):
            self.send_response(302)
            self.send_header("Location", "/queen-game-room.html#arcade")
            self.end_headers()
            return
        elif path in ("/queen-game-room", "/queen-game-room/", "/queen-game-room.html"):
            qgr = (INSTALL_ROOT / "Queen" / "world" / "queen-game-room.html").resolve()
            if qgr.is_file():
                self._send(200, qgr.read_bytes(), "text/html; charset=utf-8")
                return
        elif path.startswith("/queen-game-room/"):
            rel = unquote(path[len("/queen-game-room/") :])
            if rel and ".." not in rel:
                qroot = (INSTALL_ROOT / "Queen" / "world").resolve()
                try:
                    qtarget = (qroot / rel).resolve()
                except OSError:
                    qtarget = None
                if qtarget and qroot in qtarget.parents and qtarget.is_file():
                    self._send(200, qtarget.read_bytes(), _panel_static_mime(qtarget))
                    return
            self._send(404, "not found", "text/plain")
            return
        elif path in ("/world/queen-game-room.html", "/world/queen-game-room"):
            self.send_response(302)
            self.send_header("Location", "/queen-game-room.html")
            self.end_headers()
            return
        elif path.startswith("/Hostess7/") or path in ("/Hostess7", "/Hostess7/"):
            # Serve Hostess7 docs (Big Grin kicks, desktop, API HTML mirrors)
            rel = unquote(path[len("/Hostess7/") :] if path.startswith("/Hostess7/") else "")
            if ".." in rel:
                self._send(404, "not found", "text/plain")
                return
            h7_docs = (INSTALL_ROOT / "Hostess7" / "docs").resolve()
            try:
                if not rel or rel.endswith("/"):
                    candidate = (h7_docs / rel / "index.html").resolve()
                else:
                    candidate = (h7_docs / rel).resolve()
                    if candidate.is_dir():
                        candidate = (candidate / "index.html").resolve()
            except OSError:
                candidate = None
            if (
                candidate
                and candidate.is_file()
                and (h7_docs == candidate or h7_docs in candidate.parents)
            ):
                self._send(200, candidate.read_bytes(), _panel_static_mime(candidate))
                return
            self._send(404, "not found", "text/plain")
            return
        elif path in ("/mspaint", "/mspaint/"):
            target = PANEL_DIR / "mspaint.html"
        elif path in ("/field-ping", "/field-ping/"):
            target = PANEL_DIR / "field-ping.html"
        elif path in ("/field-grow-watch", "/field-grow-watch/"):
            target = PANEL_DIR / "field-grow-watch.html"
        elif path in ("/field-watch-dhcp", "/field-watch-dhcp/"):
            target = PANEL_DIR / "field-watch-dhcp.html"
        elif path in ("/field-popcorn", "/field-popcorn/"):
            target = PANEL_DIR / "field-popcorn.html"
        elif path in ("/ammocode", "/ammocode/"):
            ac_index = (INSTALL_ROOT / "AmmoCode" / "index.html").resolve()
            if ac_index.is_file():
                try:
                    html = ac_index.read_text(encoding="utf-8", errors="replace")
                    if "<base " not in html.lower():
                        html = html.replace("<head>", '<head><base href="/ammocode/">', 1)
                    self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
                    return
                except OSError:
                    pass
            target = PANEL_DIR / "ammocode.html"
        elif path.startswith("/ammocode/"):
            rel = unquote(path[len("/ammocode/") :])
            if rel and ".." not in rel:
                ac_root = (INSTALL_ROOT / "AmmoCode").resolve()
                try:
                    target = (ac_root / rel).resolve()
                except OSError:
                    target = None
                if target and ac_root in target.parents and target.is_file():
                    self._send(200, target.read_bytes(), _panel_static_mime(target))
                    return
            self._send(404, "not found", "text/plain")
            return
        elif path in ("/ammoos-update-os", "/ammoos-update-os/"):
            target = PANEL_DIR / "ammoos-update-os.html"
        elif path in ("/ammoos-incorporate", "/ammoos-incorporate/"):
            target = PANEL_DIR / "ammoos-incorporate.html"
        elif path in ("/field-launch-explorer", "/field-launch-explorer/"):
            target = PANEL_DIR / "field-launch-explorer.html"
        elif path in ("/field-big-drive", "/field-big-drive/"):
            target = PANEL_DIR / "field-big-drive.html"
        elif path in ("/field-storage", "/field-storage/"):
            target = PANEL_DIR / "field-storage.html"
        elif path in ("/field-font-editor", "/field-font-editor/"):
            target = PANEL_DIR / "field-font-editor.html"
        elif path in ("/compatibility", "/compatibility/", "/compatibility-layers", "/compatibility-layers/"):
            target = PANEL_DIR / "compatibility-layers.html"
        elif path in ("/combinatorics", "/combinatorics/", "/combinatorics-studio", "/combinatorics-studio/"):
            # Studio first — never hijack with compatibility-layers
            target = PANEL_DIR / "combinatorics-studio.html"
            if not target.is_file():
                target = PANEL_DIR / "compatibility-layers.html"
        elif path in ("/broadcaster", "/broadcaster/", "/obs", "/obs/"):
            target = PANEL_DIR / "field-broadcaster.html"
        elif path in (
            "/vector-cleanup",
            "/vector-cleanup/",
            "/ironclad-cleanup",
            "/ironclad-cleanup/",
            "/field-vector-ironclad-cleanup",
            "/field-vector-ironclad-cleanup/",
        ):
            target = PANEL_DIR / "field-vector-ironclad-cleanup.html"
        elif path in (
            "/home",
            "/home/",
            "/launch",
            "/launch/",
            "/launch-hub",
            "/launch-hub/",
            "/all-panels",
            "/all-panels/",
            "/field-panels-hub",
            "/field-panels-hub/",
        ):
            target = PANEL_DIR / "field-panels-hub.html"
        elif path in (
            "/speedtest",
            "/speedtest/",
            "/field-speedtest",
            "/field-speedtest/",
            "/field-speedtest.html",
        ):
            target = PANEL_DIR / "field-speedtest.html"
        elif path in (
            "/archive",
            "/archive/",
            "/world-archive",
            "/world-archive/",
            "/field-world-archive",
            "/field-world-archive/",
            "/archive.org",
        ):
            target = PANEL_DIR / "field-world-archive.html"
        elif path in (
            "/cloud",
            "/cloud/",
            "/ammonet-cloud",
            "/ammonet-cloud/",
            "/ammodrive-cloud",
            "/ammodrive-cloud/",
            "/field-ammonet-cloud",
            "/field-ammonet-cloud/",
        ):
            target = PANEL_DIR / "field-ammonet-cloud.html"
        elif path in ("/field-talk", "/field-talk/"):
            target = PANEL_DIR / "field-talk.html"
        elif path in (
            "/tristate-installer", "/tristate-installer/",
            "/install-underlay", "/install-underlay/",
        ):
            target = PANEL_DIR / "tristate-installer.html"
        elif path in ("/grok-spawn-killer", "/grok-spawn-killer/"):
            target = PANEL_DIR / "grok-spawn-killer.html"
            if not target.is_file():
                target = PANEL_DIR / "grok-spawn-killer" / "index.html"
        elif path in (
            "/underlay-f9", "/underlay-f9/",
            "/field-modern", "/field-modern/",
        ):
            target = PANEL_DIR / "underlay-f9.html"
        elif path in (
            "/command", "/command/", "/panel", "/panel/",
            "/field-legacy", "/field-legacy/", "/threat-panel", "/threat-panel/",
        ):
            embed = (query.get("embed", [""])[0] or "").strip()
            if embed == "1":
                target = PANEL_DIR / "threat-panel.html"
                if target.is_file():
                    _serve_panel_html(self, target)
                    return
            loc = "/field"
            if embed == "1":
                view = (query.get("view", [""])[0] or "").strip()
                if not view and "#" in self.path:
                    view = self.path.split("#", 1)[-1].split("?")[0]
                if view:
                    loc = f"/field#{view}"
            self.send_response(302)
            self.send_header("Location", loc)
            self.send_header("X-AmmoOS-Legacy", "dissolved")
            self.end_headers()
            return
        elif path in ("/", "/index.html"):
            accept = (self.headers.get("Accept") or "").lower()
            rs_py = INSTALL_ROOT / "lib" / "field-root-status.py"
            if "text/plain" in accept and rs_py.is_file():
                body = _nexus_py_text(rs_py, ["telnet"], timeout=8)
                self._send(200, body or "FIELD ROOT STATUS unavailable\n", "text/plain; charset=utf-8")
                return
            if "application/json" in accept and rs_py.is_file():
                payload = _nexus_py_json(rs_py, ["json"], timeout=8)
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
                return
            # Browser front door → full local C2 launch hub (every 9477 page)
            hub = PANEL_DIR / "field-panels-hub.html"
            if hub.is_file():
                target = hub
                self._send(
                    200,
                    hub.read_bytes(),
                    "text/html; charset=utf-8",
                    extra_headers={
                        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                        "X-Field-Live-Panel": "launch-hub",
                    },
                )
                return
            target = PANEL_DIR / "field-root-status.html"
            if target.is_file():
                self._send(200, target.read_bytes(), "text/html; charset=utf-8")
                return
        elif path in ("/field-root-status", "/field-root-status/"):
            target = PANEL_DIR / "field-root-status.html"
            if target.is_file():
                self._send(200, target.read_bytes(), "text/html; charset=utf-8")
                return
        elif path in ("/field", "/field/", "/app", "/app/"):
            desktop = PANEL_DIR / "field-desktop.html"
            if desktop.is_file():
                self._send(200, desktop.read_bytes(), "text/html; charset=utf-8")
                return
            target = PANEL_DIR / "threat-panel.html"
            if target.is_file():
                _serve_panel_html(self, target)
                return
        elif path.startswith("/world/"):
            rel = unquote(path[len("/world/") :])
            if rel and ".." not in rel:
                world_root = (INSTALL_ROOT / "Queen" / "world").resolve()
                try:
                    target = (world_root / rel).resolve()
                except OSError:
                    target = None
                if target and world_root in target.parents and target.is_file():
                    self._send(200, target.read_bytes(), _panel_static_mime(target))
                    return
            self._send(404, "not found", "text/plain")
            return
        elif path.startswith("/world/assets/icons/"):
            rel = unquote(path[len("/world/assets/icons/") :])
            if rel and ".." not in rel:
                icon_root = (INSTALL_ROOT / "Queen" / "world" / "assets" / "icons").resolve()
                try:
                    target = (icon_root / rel).resolve()
                except OSError:
                    target = None
                if target and icon_root in target.parents and target.is_file():
                    self._send(200, target.read_bytes(), _panel_static_mime(target))
                    return
            self._send(404, "not found", "text/plain")
            return
        elif path.startswith("/assets/formats/"):
            rel = path[len("/assets/formats/") :]
            if rel and ".." not in rel:
                for base in (
                    INSTALL_ROOT / "data" / "combinatronic-visuals" / "formats",
                    INSTALL_ROOT / "library" / "assets" / "formats",
                ):
                    try:
                        base_res = base.resolve()
                        target = (base / rel).resolve()
                    except OSError:
                        continue
                    if base_res in target.parents and target.is_file():
                        self._send(200, target.read_bytes(), _panel_static_mime(target))
                        return
            self._send(404, "not found", "text/plain")
            return
        else:
            # Generic panel resolver — every panel/*.html is GET-openable without a special case
            raw = path.lstrip("/")
            candidates: list[Path] = []
            if raw:
                candidates.append(PANEL_DIR / raw)
                if not raw.endswith(".html"):
                    candidates.append(PANEL_DIR / f"{raw}.html")
                stem = raw[:-5] if raw.endswith(".html") else raw
                if stem and not stem.startswith("field-"):
                    candidates.append(PANEL_DIR / f"field-{stem}.html")
                if stem.endswith("-embed"):
                    candidates.append(PANEL_DIR / f"{stem}.html")
            target = None
            root = PANEL_DIR.resolve()
            for cand in candidates:
                try:
                    resolved = cand.resolve()
                except OSError:
                    continue
                if root not in resolved.parents and resolved != root:
                    continue
                if resolved.is_file():
                    target = resolved
                    break
            if target is None:
                self._send(404, "not found", "text/plain")
                return
        if target is not None and target.is_file():
            if target.suffix == ".html" and target.name == "threat-panel.html":
                _serve_panel_html(self, target)
            else:
                self._send(200, target.read_bytes(), _panel_static_mime(target))
            return
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        """Read-only API — every write method is refused. No login writes. No deletes."""
        path = unquote(self.path.split("?", 1)[0])
        self._send(
            405,
            json.dumps(
                {
                    "ok": False,
                    "error": "read_only",
                    "method": "POST",
                    "path": path,
                    "display_only": True,
                    "autopilot": True,
                    "read_only": True,
                    "no_api_writes": True,
                    "no_login_writes": True,
                    "motto": "HTTP API is GET-only display. Field autopilot works offline of the browser.",
                    "use": f"GET {path}",
                    "cli": "bin/field-gnu-terminal",
                },
                ensure_ascii=False,
            ),
            "application/json",
        )

def _startup_field_stack_boot() -> None:
    """Panel-alone boot: field DNS/DHCP loops + unified start-field-stack.sh posture."""
    _ensure_field_services_boot()
    if os.environ.get("NEXUS_FIELD_STACK_BOOT", "1") != "1":
        return
    stack = INSTALL_ROOT / "scripts" / "start-field-stack.sh"
    if not stack.is_file():
        return
    env = _field_stack_env()
    env.setdefault("NEXUS_FIELD_LAUNCH_BROWSER", "0")
    env.setdefault("NEXUS_BOOT_IMPL", "0")
    env.setdefault("AML_BUILD", "0")
    try:
        subprocess.Popen(
            ["bash", str(stack)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )
    except OSError:
        pass


def _startup_always_optimal() -> None:
    ao = _grok16_root() / "lib" / "field-always-optimal.py"
    if not ao.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(ao), "apply"],
            capture_output=True,
            text=True,
            timeout=180,
            env=_field_stack_env(),
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


def _startup_internet_clean() -> None:
    """Hostess 7 default — secure bookmarks + telemetry strip on panel boot."""
    if os.environ.get("HOSTESS7_INTERNET_CLEAN_BOOT", "1") != "1":
        return
    script = INSTALL_ROOT / "lib" / "hostess7-internet-clean.py"
    if not script.is_file():
        script = INSTALL_ROOT / "lib" / "field-c2-bookmark-boot.py"
    if not script.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(script), "json"],
            capture_output=True,
            text=True,
            timeout=240,
            env=_field_stack_env(),
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


def _startup_dynamic_routes() -> None:
    """Panel boot — kick hostile/DNS/kill-rekill table trash; optional full route return."""
    if os.environ.get("NEXUS_DYNAMIC_ROUTES_BOOT", "1") != "1":
        return
    dyn_py = INSTALL_ROOT / "lib" / "field-dynamic-routes.py"
    if not dyn_py.is_file():
        return
    try:
        if os.environ.get("NEXUS_DYNAMIC_ROUTES_BOOT_FULL", "0").strip().lower() in ("1", "yes", "on"):
            subprocess.run(
                [sys.executable, str(dyn_py), "run", "--fast"],
                capture_output=True,
                text=True,
                timeout=180,
                env=_field_stack_env(),
            )
        else:
            subprocess.run(
                [sys.executable, str(dyn_py), "kick-trash"],
                capture_output=True,
                text=True,
                timeout=120,
                env=_field_stack_env(),
            )
    except (subprocess.TimeoutExpired, OSError):
        pass


def _startup_lab_sovereign() -> None:
    """Hostess 7 runs the lab — secure connection, share in, no share out."""
    if os.environ.get("HOSTESS7_LAB_SOVEREIGN_BOOT", "1") != "1":
        return
    script = INSTALL_ROOT / "lib" / "hostess7-lab-sovereign.py"
    if not script.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(script), "boot"],
            capture_output=True,
            text=True,
            timeout=120,
            env=_field_stack_env(),
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


def _startup_truth_keepalive() -> None:
    """Panel boot — truth every surface; retruth when below floor (soft ingress, no DHCP break)."""
    if os.environ.get("NEXUS_TRUTH_KEEPALIVE_BOOT", "1") != "1":
        return
    script = INSTALL_ROOT / "lib" / "field-truth-keepalive.py"
    if not script.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(script), "keepalive"],
            capture_output=True,
            text=True,
            timeout=300,
            env=_field_stack_env(),
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


def _startup_botnet_hub_warm() -> None:
    """Pre-warm live hub cache so /botnet first paint is snappy."""
    try:
        time.sleep(0.15)
        _field_botnet_hub_live(force=True)
    except Exception:
        pass
    # Refresh in background slightly slower than panel poll so polls hit warm cache
    while True:
        try:
            time.sleep(1.8)
            # force=False uses TTL; only rebuilds when stale
            _field_botnet_hub_live(force=False)
            # periodic full refresh every ~cycle when TTL expired inside helper
            age = time.time() - float(_HUB_LIVE_CACHE.get("ts") or 0)
            if age >= 1.5:
                _field_botnet_hub_live(force=True)
        except Exception:
            time.sleep(3.0)


def main():
    global PANEL_DIR
    PANEL_DIR = PANEL_DIR.resolve()
    os.chdir(PANEL_DIR)
    if os.environ.get("NEXUS_PANEL_SPAWN_SERVICES", "0").strip().lower() in ("1", "yes", "on"):
        threading.Thread(target=_startup_field_stack_boot, daemon=True, name="field-stack-boot").start()
    threading.Thread(target=_startup_always_optimal, daemon=True, name="always-optimal-boot").start()
    threading.Thread(target=_startup_internet_clean, daemon=True, name="hostess7-internet-clean-boot").start()
    threading.Thread(target=_startup_dynamic_routes, daemon=True, name="field-dynamic-routes-boot").start()
    threading.Thread(target=_startup_lab_sovereign, daemon=True, name="hostess7-lab-sovereign-boot").start()
    threading.Thread(target=_startup_truth_keepalive, daemon=True, name="field-truth-keepalive-boot").start()
    threading.Thread(target=_startup_botnet_hub_warm, daemon=True, name="botnet-hub-live-warm").start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()