#!/usr/bin/env python3
"""Local threat panel server — HTTP on loopback only (Hostess7-secured)."""

import importlib.util
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9477
PANEL_DIR = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("panel")
STATUS_JSON = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("threat-panel.json")
STATE_DIR = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL_ROOT = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
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


def _nexus_py_json(script: Path, args: list[str], timeout: int = 25) -> dict:
    if not script.is_file():
        return {"ok": False, "error": "script_missing"}
    env = _field_stack_env()
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
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "error": "script_failed", "detail": (proc.stderr or "")[:200]}


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
        mod.copilot(reload=True)
    except Exception:
        pass
    _FIELD_OPERATOR_MOD = mod
    return mod


def _field_operator_copilot_route(target: str, *, override: str | None = None) -> dict:
    mod = _field_operator_inproc()
    if mod is None:
        return _nexus_py_json(INSTALL_ROOT / "lib" / "field-operator.py", ["route", target], timeout=3)
    if override:
        return mod.route_to_board(target, override=override)
    return mod.copilot_route(target)


def _field_operator_copilot_batch(batch: list[str], *, override: str | None = None) -> dict:
    mod = _field_operator_inproc()
    if mod is None:
        args = ["route-batch", *[str(x) for x in batch if x]]
        return _nexus_py_json(INSTALL_ROOT / "lib" / "field-operator.py", args, timeout=5)
    if override:
        return mod.route_batch(batch, override=override)
    return mod.copilot_batch(batch)


def _field_operator_copilot_status() -> dict:
    mod = _field_operator_inproc()
    if mod is None:
        return _nexus_py_json(INSTALL_ROOT / "lib" / "field-operator.py", ["copilot"], timeout=8)
    return mod.copilot_status()


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

    def handle(self):
        if not self._peer_loopback(self):
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
            "camera=(), microphone=(), display-capture=(), clipboard-read=(), geolocation=()",
        )
        self.send_header("X-Admin-Shield", "keyboard-hooks-blocked")
        self.send_header("X-Smart-Wire", "nexus-keyboard-no-middleman")
        self.send_header("X-Hardware-Wire", "nexus-field-hardware-hooks")
        if "text/html" in str(ctype):
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
                "connect-src 'self' http://127.0.0.1:* https://127.0.0.1:*; "
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
        if path.startswith("/api/") and not self._ironclad_api_gate(path, "GET"):
            return
        query = parse_qs(urlparse(self.path).query)

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
            payload = _field_operator_copilot_route(target)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-operator/copilot":
            payload = _field_operator_copilot_status()
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

        if path == "/api/field-bus/copilot":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-unified-bus.py", ["copilot"], timeout=15)
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

        if path in ("/api/queen-browser/open", "/api/queen-browser/f9"):
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

        if path.startswith("/api/field-monster-monitor"):
            script = INSTALL_ROOT / "lib" / "field-monster-monitor.py"
            if not script.is_file():
                self._send(503, json.dumps({"ok": False, "error": "monster_monitor_missing"}), "application/json")
                return
            sub = path[len("/api/field-monster-monitor") :].strip("/") or "json"
            args = ["json"] if sub in ("", "json", "status") else [sub]
            payload = _nexus_py_json(script, args, timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
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

        if path in ("/api/field-c2-bookmarks", "/api/ammo-bookmarks"):
            script = INSTALL_ROOT / "lib" / "field-c2-bookmark-boot.py"
            if script.is_file():
                payload = _nexus_py_json(script, ["json"], timeout=120)
            else:
                payload = {"ok": False, "error": "field_c2_bookmark_boot_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
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

        if path == "/api/field-host-desktop":
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

        if path == "/api/combinatorics":
            layers = INSTALL_ROOT / "lib" / "field-compatibility-layers.py"
            if layers.is_file():
                payload = _nexus_py_json(layers, ["json"], timeout=45)
            else:
                studio = INSTALL_ROOT / "lib" / "field-combinatorics-studio.py"
                payload = _nexus_py_json(studio, ["json"], timeout=45) if studio.is_file() else {
                    "schema": "field-combinatorics-studio/v1",
                    "ok": False,
                    "hint": "combinatorics studio missing",
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
            action = str((qparams.get("action") or ["optimal"])[0]).strip().lower()
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
            payload = _read_field_panel_file("field_dns")
            if payload is None:
                live = _nexus_py_json(INSTALL_ROOT / "lib" / "field-dns.py", ["json"])
                payload = _panel_slice(
                    "field_dns",
                    live=live,
                    default={"schema": "field-dns/v2"},
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

        if path in ("/control-panel", "/control-panel/"):
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
        elif path in ("/field-popcorn", "/field-popcorn/"):
            target = PANEL_DIR / "field-popcorn.html"
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
            target = PANEL_DIR / "compatibility-layers.html"
            if not target.is_file():
                target = PANEL_DIR / "combinatorics-studio.html"
        elif path in ("/field-talk", "/field-talk/"):
            target = PANEL_DIR / "field-talk.html"
        elif path in (
            "/tristate-installer", "/tristate-installer/",
            "/install-underlay", "/install-underlay/",
        ):
            target = PANEL_DIR / "tristate-installer.html"
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
        elif path in (
            "/field", "/field/", "/app", "/app/", "/", "/index.html",
        ):
            desktop = PANEL_DIR / "field-desktop.html"
            if desktop.is_file():
                self._send(200, desktop.read_bytes(), "text/html; charset=utf-8")
                return
            target = PANEL_DIR / "threat-panel.html"
            if target.is_file():
                _serve_panel_html(self, target)
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
            target = (PANEL_DIR / path.lstrip("/")).resolve()
            if PANEL_DIR.resolve() not in target.parents and target != PANEL_DIR.resolve():
                self._send(403, "forbidden", "text/plain")
                return
        if target.is_file():
            if target.suffix == ".html" and target.name == "threat-panel.html":
                _serve_panel_html(self, target)
            else:
                self._send(200, target.read_bytes(), _panel_static_mime(target))
            return
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        path = unquote(self.path.split("?", 1)[0])
        if path.startswith("/api/compile-autocorrect"):
            body = self._read_json_body()
            content = str(body.get("content") or "")
            lang = str(body.get("language") or body.get("lang") or "")
            profile = str(body.get("profile") or "belt_2_0")
            g16_py = INSTALL_ROOT / "Grok16" / "lib" / "g16-universal-compiler.py"
            if not g16_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "g16_universal_missing"}), "application/json")
                return
            import importlib.util
            spec = importlib.util.spec_from_file_location("g16_uni_panel", g16_py)
            payload: dict[str, Any] = {"ok": False, "error": "compile_unavailable"}
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "compile_source"):
                    payload = mod.compile_source(
                        content,
                        lang=lang,
                        path=str(body.get("path") or "snippet"),
                        profile=profile,
                    )
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return
        if path.startswith("/api/ironclad/access") or path.startswith("/api/ironclad/h7-access"):
            acc = INSTALL_ROOT / "lib" / "ironclad-access.py"
            body = self._read_json_body()
            if acc.is_file():
                import importlib.util
                spec = importlib.util.spec_from_file_location("ironclad_access_http_post", acc)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    action = str(body.get("action") or "search").strip().lower()
                    payload = mod.dispatch(action, body=body)
                    sec = _ironclad_secure_api_mod()
                    extra = sec.security_headers() if sec and hasattr(sec, "security_headers") else {}
                    self._send(200, json.dumps(payload, ensure_ascii=False), "application/json", extra_headers=extra)
                    return
            self._send(503, json.dumps({"ok": False, "error": "ironclad_access_missing"}), "application/json")
            return
        if path.startswith("/api/ironclad/secure-api"):
            mod = _ironclad_secure_api_mod()
            body = self._read_json_body()
            if mod and hasattr(mod, "ironclad_secure_api"):
                api = mod.ironclad_secure_api()
                entries = body.get("entries") if isinstance(body.get("entries"), list) else None
                if entries is not None:
                    sorted_rows, sort_meta = api.sort_index(
                        entries, context=str(body.get("context") or "registry_index"),
                    )
                    payload = {"ok": True, "entries": sorted_rows, "sort": sort_meta, "singleton": True}
                elif path.rstrip("/").endswith("/search") or body.get("query") is not None or body.get("q") is not None:
                    payload = api.search_index(
                        str(body.get("query") or body.get("q") or ""),
                        context=str(body.get("context") or "all"),
                        limit=int(body.get("limit") or 48),
                    )
                else:
                    payload = api.handle_api(path, query=parse_qs(urlparse(self.path).query))
                extra = mod.security_headers() if hasattr(mod, "security_headers") else {}
                self._send(200, json.dumps(payload, ensure_ascii=False), "application/json", extra_headers=extra)
                return
            self._send(503, json.dumps({"ok": False, "error": "ironclad_secure_api_missing"}), "application/json")
            return
        max_body = 8_388_608 if path.startswith("/api/library/") else 48_000_000 if path.startswith("/api/znetwork/vault/") else 65536
        if self.headers.get("Content-Length"):
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                length = 0
            if length > max_body:
                self._send(413, "payload too large", "text/plain")
                return
        body = self._read_json_body()
        if path.startswith("/api/") and not self._ironclad_api_gate(path, "POST", body):
            return

        if path.startswith("/api/hostess7/kill-library") or path.startswith("/api/hostess7-kill-library"):
            kill_py = INSTALL_ROOT / "lib" / "hostess7-kill-library.py"
            if not kill_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "kill_library_missing"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            sub = (
                path.replace("/api/hostess7-kill-library", "")
                .replace("/api/hostess7/kill-library", "")
                .strip("/")
            )
            os.environ.setdefault("HOSTESS7_OPERATOR", "1")
            if sub in ("sync", "rebuild") or req.get("action") in ("sync", "rebuild"):
                os.environ["HOSTESS7_KILL_LIBRARY_SYNC"] = "1"
                req = {**req, "action": "sync"}
            elif not req.get("action"):
                req = {
                    "read": {"action": "read"},
                    "books": {"action": "books"},
                    "list": {"action": "books"},
                }.get(sub, {"action": "panel"})
            env = _field_stack_env()
            env["HOSTESS7_OPERATOR"] = "1"
            if req.get("action") == "sync":
                env["HOSTESS7_KILL_LIBRARY_SYNC"] = "1"
            try:
                proc = subprocess.run(
                    [sys.executable, str(kill_py), "dispatch"],
                    input=json.dumps(req),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=env,
                    cwd=str(INSTALL_ROOT),
                )
                payload = json.loads(proc.stdout or "{}")
            except (subprocess.TimeoutExpired, json.JSONDecodeError):
                payload = {"ok": False, "error": "kill_library_dispatch_failed"}
            code = 200 if isinstance(payload, dict) and payload.get("ok") else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/book-maker/pack", "/api/hostess7-book-maker/pack"):
            maker_py = INSTALL_ROOT / "lib" / "hostess7-book-maker.py"
            req = body if isinstance(body, dict) else {}
            title = str(req.get("title") or "").strip()
            book_body = str(req.get("body") or "").strip()
            if not title or not book_body:
                self._send(400, json.dumps({"ok": False, "error": "title_and_body_required"}), "application/json")
                return
            import importlib.util
            spec = importlib.util.spec_from_file_location("hostess7_book_maker_http", maker_py)
            payload: dict[str, Any] = {"ok": False, "error": "book_maker_missing"}
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "pack_book"):
                    payload = mod.pack_book(
                        title=title,
                        body=book_body,
                        author=str(req.get("author") or "hostess7"),
                        co_author=str(req.get("co_author") or req.get("co-author") or ""),
                        dewey=str(req.get("dewey") or "000"),
                        shelf=str(req.get("shelf") or "000-computer-science"),
                        book_id=str(req.get("book_id") or ""),
                    )
            code = 200 if isinstance(payload, dict) and payload.get("ok") else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path.startswith("/api/znetwork/registry/"):
            reg_py = INSTALL_ROOT / "lib" / "znetwork-operator-registry.py"
            if not reg_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "znetwork_registry_missing"}), "application/json")
                return
            sub = path[len("/api/znetwork/registry/") :].strip("/")
            req = body if isinstance(body, dict) else {}
            if sub == "register":
                payload = _nexus_py_json(reg_py, ["register", json.dumps(req)], timeout=45)
            elif sub == "ingest":
                payload = _nexus_py_json(reg_py, ["ingest", json.dumps(req)], timeout=45)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_registry_post"}), "application/json")
                return
            code = 200 if isinstance(payload, dict) and payload.get("ok") else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path.startswith("/api/znetwork/vault/"):
            vault_py = INSTALL_ROOT / "lib" / "znetwork-secure-vault.py"
            if not vault_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "znetwork_vault_missing"}), "application/json")
                return
            sub = path[len("/api/znetwork/vault/") :].strip("/")
            req = body if isinstance(body, dict) else {}
            if sub == "send":
                payload = _nexus_py_json(vault_py, ["send", json.dumps(req)], timeout=120)
            elif sub == "accept":
                tid = str(req.get("transfer_id") or "")
                payload = _nexus_py_json(vault_py, ["accept", tid], timeout=60)
            elif sub == "reject":
                tid = str(req.get("transfer_id") or "")
                reason = str(req.get("reason") or "operator_reject")
                payload = _nexus_py_json(vault_py, ["reject", tid, reason], timeout=30)
            elif sub == "ingest":
                payload = _nexus_py_json(vault_py, ["ingest", json.dumps(req)], timeout=60)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_vault_post"}), "application/json")
                return
            code = 200 if isinstance(payload, dict) and payload.get("ok") else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        ruler_py = INSTALL_ROOT / "lib" / "hostess7-brain-ruler.py"
        if path.startswith("/api/hostess7/brain/"):
            if not ruler_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "brain_ruler_missing"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            sub = path.replace("/api/hostess7/brain/", "").strip("/")
            if not req.get("action"):
                req = {
                    "grow": {"action": "grow"},
                    "rule": {"action": "rule"},
                    "sovereignty": {"action": "assess_sovereignty"},
                    "assess": {"action": "assess_sovereignty"},
                    "expand": {"action": "expand_chambers"},
                }.get(sub.split("/")[0], {"action": "status"})
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(ruler_py), "dispatch"],
                    input=json.dumps(req),
                    capture_output=True,
                    text=True,
                    timeout=600,
                    env=env,
                    cwd=str(INSTALL_ROOT),
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "brain_ruler_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "brain_ruler_bad_json", "tail": (proc.stdout or "")[-1500:]}
            code = 200 if isinstance(payload, dict) and payload.get("ok", True) else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        training_py = INSTALL_ROOT / "lib" / "hostess7-training-chamber.py"
        if path.startswith("/api/hostess7/training-chamber"):
            if not training_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "training_chamber_missing"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            if not req.get("action"):
                sub = path.replace("/api/hostess7-training-chamber", "").replace("/api/hostess7/training-chamber", "").strip("/")
                if sub.startswith("floor/"):
                    req = {"zone": "floor", "action": sub[6:].replace("-", "_") or "status"}
                else:
                    req = {
                        "session": {"action": "session"},
                        "complete-all": {"action": "complete_all"},
                        "needs": {"action": "needs"},
                        "try-body": {"action": "try_body"},
                        "combat": {"action": "combat_drill"},
                    }.get(sub, {"action": "status"})
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(training_py), "dispatch"],
                    input=json.dumps(req),
                    capture_output=True,
                    text=True,
                    timeout=600,
                    env=env,
                    cwd=str(INSTALL_ROOT),
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "training_chamber_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "training_chamber_parse_failed"}
            code = 200 if isinstance(payload, dict) and payload.get("ok", True) else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/training") and not path.startswith("/api/hostess7/training-room") and not path.startswith("/api/hostess7/training-floor") and not path.startswith("/api/hostess7/training-chamber"):
            if not training_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "training_missing"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            if not req.get("action"):
                sub = path.replace("/api/hostess7-training", "").replace("/api/hostess7/training", "").strip("/")
                if sub.startswith("floor/"):
                    req = {"zone": "floor", "action": sub[6:].replace("-", "_") or "status"}
                else:
                    req = {
                        "session": {"action": "session"},
                        "train": {"action": "session"},
                        "complete-all": {"action": "complete_all"},
                        "complete_all": {"action": "complete_all"},
                        "complete": {"action": "complete_all"},
                        "needs": {"action": "needs"},
                        "try-body": {"action": "try_body"},
                        "try_body": {"action": "try_body"},
                        "combat": {"action": "combat_drill"},
                    }.get(sub, {"action": "status"})
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(training_py), "dispatch"],
                    input=json.dumps(req),
                    capture_output=True,
                    text=True,
                    timeout=600,
                    env=env,
                    cwd=str(INSTALL_ROOT),
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "training_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "training_parse_failed"}
            code = 200 if isinstance(payload, dict) and payload.get("ok", True) else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/training-room") or path in ("/api/hostess7-training-room",):
            if not training_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "training_missing"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            if not req.get("action"):
                sub = path.replace("/api/hostess7-training-room", "").replace("/api/hostess7/training-room", "").strip("/")
                req = {
                    "session": {"action": "session"},
                    "train": {"action": "session"},
                    "complete-all": {"action": "complete_all"},
                    "complete_all": {"action": "complete_all"},
                    "complete": {"action": "complete_all"},
                    "needs": {"action": "needs"},
                    "try-body": {"action": "try_body"},
                    "try_body": {"action": "try_body"},
                    "combat": {"action": "combat_drill"},
                }.get(sub, {"action": "status"})
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(training_py), "dispatch"],
                    input=json.dumps(req),
                    capture_output=True,
                    text=True,
                    timeout=600,
                    env=env,
                    cwd=str(INSTALL_ROOT),
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "training_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "training_parse_failed"}
            code = 200 if isinstance(payload, dict) and payload.get("ok", True) else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/training-floor") or path in ("/api/hostess7-training-floor",):
            if not training_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "training_missing"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            if not req.get("action"):
                sub = path.replace("/api/hostess7-training-floor", "").replace("/api/hostess7/training-floor", "").strip("/")
                req = {
                    "complete": {"zone": "floor", "action": "complete"},
                    "complete-all": {"zone": "floor", "action": "complete"},
                    "complete_all": {"zone": "floor", "action": "complete"},
                }.get(sub, {"zone": "floor", "action": "status"})
            elif not req.get("zone"):
                req = {**req, "zone": "floor"}
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(training_py), "dispatch"],
                    input=json.dumps(req),
                    capture_output=True,
                    text=True,
                    timeout=600,
                    env=env,
                    cwd=str(INSTALL_ROOT),
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "training_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "training_parse_failed"}
            code = 200 if isinstance(payload, dict) and payload.get("ok", True) else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path.startswith("/api/beyond-darpa-security") or path in ("/api/beyond-darpa-security",):
            bds_py = INSTALL_ROOT / "lib" / "beyond-darpa-security.py"
            if not bds_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "beyond_darpa_missing"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            sub = path.replace("/api/beyond-darpa-security", "").strip("/")
            if not req.get("action"):
                req = {
                    "assess": {"action": "assess"},
                    "gate": {"action": "gate"},
                    "threat": {"action": "assess"},
                }.get(sub, {"action": "posture"})
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(bds_py), "dispatch"],
                    input=json.dumps(req),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=env,
                    cwd=str(INSTALL_ROOT),
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "beyond_darpa_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "beyond_darpa_parse_failed"}
            code = 200 if isinstance(payload, dict) and payload.get("ok", True) else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/advisory") or path in ("/api/hostess7-advisory", "/api/hostess7-advisory-body"):
            adv_py = INSTALL_ROOT / "lib" / "hostess7-advisory-body.py"
            if not adv_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "hostess7_advisory_missing"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            sub = path.replace("/api/hostess7-advisory-body", "").replace("/api/hostess7-advisory", "").replace("/api/hostess7/advisory", "").strip("/")
            if not req.get("action"):
                req = {
                    "ingest": {"action": "ingest"},
                    "discern": {"action": "discern"},
                    "promote": {"action": "promote"},
                    "body-permit": {"action": "body_permit"},
                    "body_permit": {"action": "body_permit"},
                    "gate": {"action": "check"},
                }.get(sub.replace("-", "_"), {"action": "status"})
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(adv_py), "dispatch"],
                    input=json.dumps(req),
                    capture_output=True,
                    text=True,
                    timeout=90,
                    env=env,
                    cwd=str(INSTALL_ROOT),
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "hostess7_advisory_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "hostess7_advisory_parse_failed"}
            code = 200 if isinstance(payload, dict) and payload.get("ok", True) else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/targets") or path in ("/api/hostess7-targets",):
            tgt_py = INSTALL_ROOT / "lib" / "hostess7-targets.py"
            if not tgt_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "hostess7_targets_missing", "TARGET": "KILL"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            sub = path.replace("/api/hostess7-targets", "").replace("/api/hostess7/targets", "").strip("/")
            if not req.get("action"):
                req = {
                    "sync": {"action": "sync"},
                    "lookup": {"action": "lookup"},
                    "promote": {"action": "promote"},
                    "correlate": {"action": "correlate"},
                }.get(sub, {"action": "status"})
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(tgt_py), "dispatch"],
                    input=json.dumps(req),
                    capture_output=True,
                    text=True,
                    timeout=90,
                    env=env,
                    cwd=str(INSTALL_ROOT),
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "hostess7_targets_timeout", "TARGET": "KILL"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "hostess7_targets_parse_failed", "TARGET": "KILL"}
            code = 200 if isinstance(payload, dict) and payload.get("ok", True) else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False, "TARGET": "KILL"}), "application/json")
            return

        if path.startswith("/api/hostess7/body") or path in ("/api/hostess7-body", "/api/hostess7-body-control"):
            body_py = INSTALL_ROOT / "lib" / "hostess7-body-control.py"
            if not body_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "hostess7_body_control_missing"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            if not req.get("action"):
                sub = path.replace("/api/hostess7-body-control", "").replace("/api/hostess7-body", "").replace("/api/hostess7/body", "").strip("/")
                if sub in ("touch-toes", "touch_toes"):
                    req = {"action": "touch_toes"}
                elif sub == "bend":
                    req = {"action": "bend", "degrees": float(req.get("degrees") or 45)}
                elif sub == "cycle":
                    req = {"action": "cycle"}
                else:
                    req = {"action": "status"}
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(body_py), "dispatch"],
                    input=json.dumps(req),
                    capture_output=True,
                    text=True,
                    timeout=180,
                    env=env,
                    cwd=str(INSTALL_ROOT),
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "hostess7_body_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "hostess7_body_parse_failed"}
            code = 200 if isinstance(payload, dict) and payload.get("ok", True) else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/ocr") or path in ("/api/hostess7-ocr", "/api/hostess7-ocr-control"):
            ocr_py = INSTALL_ROOT / "lib" / "hostess7-ocr-control.py"
            if not ocr_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "hostess7_ocr_control_missing"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            if not req.get("action"):
                sub = path.replace("/api/hostess7-ocr-control", "").replace("/api/hostess7-ocr", "").replace("/api/hostess7/ocr", "").strip("/")
                if sub in ("ingest-all", "ingest_all"):
                    req = {"action": "ingest_all"}
                elif sub in ("train-all", "train_all"):
                    req = {"action": "train_all"}
                elif sub == "cycle":
                    req = {"action": "cycle"}
                elif sub in ("assume", "charge"):
                    req = {"action": "assume"}
                else:
                    req = {"action": "status"}
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(ocr_py), "dispatch"],
                    input=json.dumps(req),
                    capture_output=True,
                    text=True,
                    timeout=900,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "hostess7_ocr_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "hostess7_ocr_parse_failed"}
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/hostess7/znetwork") or path.startswith("/api/znetwork/hostess7"):
            wire_py = INSTALL_ROOT / "lib" / "hostess7-znetwork-wire.py"
            if not wire_py.is_file():
                self._send(503, json.dumps({"ok": False, "error": "hostess7_znetwork_wire_missing"}), "application/json")
                return
            sub = path.split("/api/hostess7/znetwork", 1)[-1].split("/api/znetwork/hostess7", 1)[-1].strip("/")
            req = body if isinstance(body, dict) else {}
            if sub in ("speak", "out", "egress"):
                req.setdefault("action", "speak")
            elif sub in ("rebuild-profile", "rebuild"):
                req.setdefault("action", "rebuild-profile")
            elif not req.get("action"):
                req.setdefault("action", "panel")
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(wire_py), "dispatch"],
                    input=json.dumps(req),
                    capture_output=True,
                    text=True,
                    timeout=90,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "hostess7_znetwork_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "hostess7_znetwork_parse_failed"}
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-clipboard":
            script = INSTALL_ROOT / "lib" / "field-clipboard-wire.py"
            action = str((body or {}).get("action") or "").strip().lower()
            scheme = str((body or {}).get("scheme") or "").strip()
            text = (body or {}).get("text")
            hist_idx = (body or {}).get("history_index")
            if scheme:
                payload = _nexus_py_json(script, ["scheme", scheme], timeout=20)
            elif action in ("history", "historic"):
                payload = _nexus_py_json(script, ["history"], timeout=20)
            elif action in ("history_paste", "historic_paste", "paste_history"):
                idx = str(hist_idx if hist_idx is not None else (body or {}).get("index", "0"))
                payload = _nexus_py_json(script, ["history-paste", idx], timeout=20)
            elif action:
                argv = ["action", action]
                if text is not None and str(text):
                    env = os.environ.copy()
                    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
                    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
                    try:
                        proc = subprocess.run(
                            [sys.executable, str(script), *argv],
                            input=str(text),
                            capture_output=True,
                            text=True,
                            timeout=20,
                            env=env,
                        )
                        payload = json.loads(proc.stdout.strip() or "{}") if proc.stdout.strip() else {"ok": False}
                    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
                        payload = {"ok": False, "error": str(exc)}
                else:
                    payload = _nexus_py_json(script, argv, timeout=20)
            else:
                payload = _nexus_py_json(script, ["enforce"], timeout=25)
            code = 200 if payload.get("ok", True) and not payload.get("error") else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-lock") or path.startswith("/api/field-keepass"):
            script = INSTALL_ROOT / "lib" / "field-keepass.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_lock_missing"}), "application/json")
                return
            prefix = "/api/field-lock" if path.startswith("/api/field-lock") else "/api/field-keepass"
            sub = path[len(prefix) :].strip("/")
            if sub in ("", "status", "json"):
                payload = _nexus_py_json(script, ["json"], timeout=45)
            elif sub == "launch":
                vault = str((body or {}).get("vault") or "")
                argv = ["launch", vault] if vault else ["launch"]
                payload = _nexus_py_json(script, argv, timeout=30)
            elif sub == "new":
                payload = _nexus_py_json(script, ["new"], timeout=30)
            elif sub == "settings":
                patch = body if isinstance(body, dict) else {}
                payload = _nexus_py_json(script, ["settings", json.dumps(patch)], timeout=30)
            elif sub == "import":
                imp = INSTALL_ROOT / "lib" / "field-lock-import.py"
                req = body if isinstance(body, dict) else {}
                req.setdefault("action", "import")
                if imp.is_file():
                    try:
                        proc = subprocess.run(
                            [sys.executable, str(imp), "dispatch", json.dumps(req)],
                            capture_output=True,
                            text=True,
                            timeout=120,
                            env=_field_stack_env(),
                        )
                        payload = json.loads(proc.stdout or "{}")
                    except (subprocess.TimeoutExpired, json.JSONDecodeError):
                        payload = {"ok": False, "error": "lock_import_failed"}
                else:
                    payload = {"ok": False, "error": "lock_import_missing"}
            elif sub in ("import-scan", "import_scan"):
                imp = INSTALL_ROOT / "lib" / "field-lock-import.py"
                payload = _nexus_py_json(imp, ["scan"], timeout=90) if imp.is_file() else {"ok": False, "error": "lock_import_missing"}
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_field_keepass_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-gdb"):
            script = INSTALL_ROOT / "lib" / "field-gdb.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_gdb_missing"}), "application/json")
                return
            sub = path[len("/api/field-gdb") :].strip("/")
            if sub in ("", "status", "json"):
                payload = _nexus_py_json(script, ["json"], timeout=45)
            else:
                req = {"action": sub, **(body if isinstance(body, dict) else {})}
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(script), "dispatch"],
                        input=json.dumps(req),
                        capture_output=True,
                        text=True,
                        timeout=120,
                        env=env,
                    )
                    payload = json.loads(proc.stdout or "{}")
                except subprocess.TimeoutExpired:
                    payload = {"ok": False, "error": "field_gdb_timeout"}
                except json.JSONDecodeError:
                    payload = {"ok": False, "error": "field_gdb_parse_failed"}
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-gpu"):
            script = INSTALL_ROOT / "lib" / "field-gpu-control.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_gpu_missing"}), "application/json")
                return
            sub = path[len("/api/field-gpu") :].strip("/")
            if sub in ("", "status", "json"):
                payload = _nexus_py_json(script, ["json"], timeout=45)
            elif sub == "settings":
                patch = body if isinstance(body, dict) else {}
                payload = _nexus_py_json(script, ["settings", json.dumps(patch)], timeout=30)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_field_gpu_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/vsync-locker"):
            script = INSTALL_ROOT / "lib" / "field-vsync-locker.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "vsync_locker_missing"}), "application/json")
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
                args = ["drift"]
                if isinstance(body, dict) and body.get("expose"):
                    args.append("--expose")
                if isinstance(body, dict) and body.get("force"):
                    args.append("--force")
                payload = _nexus_py_json(script, args, timeout=45)
            elif sub == "harden":
                payload = _nexus_py_json(script, ["harden"], timeout=45)
            elif sub == "guard":
                payload = _nexus_py_json(script, ["guard", "--status"], timeout=20)
            elif sub == "launch":
                payload = _nexus_py_json(script, ["launch"], timeout=30)
            elif sub == "stop":
                force = isinstance(body, dict) and body.get("force")
                args = ["stop", "--force"] if force else ["stop"]
                payload = _nexus_py_json(script, args, timeout=20)
            elif sub == "patrol":
                payload = _nexus_py_json(script, ["patrol"], timeout=120)
            elif sub == "kill" and isinstance(body, dict) and body.get("pid"):
                args = ["kill", str(body.get("pid")), str(body.get("reason") or "vsync_trespass_api")]
                payload = _nexus_py_json(script, args, timeout=90)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_vsync_locker_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-shell-dock"):
            script = INSTALL_ROOT / "lib" / "field-shell-dock.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_shell_dock_missing"}), "application/json")
                return
            sub = path[len("/api/field-shell-dock") :].strip("/")
            active = str((body or {}).get("active_icon") or "").strip() if isinstance(body, dict) else ""
            if sub in ("", "status", "json"):
                args = ["json"] + ([active] if active else [])
                payload = _nexus_py_json(script, args, timeout=20)
            elif sub == "settings":
                patch = body if isinstance(body, dict) else {}
                payload = _nexus_py_json(script, ["settings", json.dumps(patch)], timeout=15)
            elif sub == "sync":
                args = ["sync"] + ([active] if active else [])
                payload = _nexus_py_json(script, args, timeout=25)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_field_shell_dock_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-body-system"):
            sub = path[len("/api/field-body-system"):].strip("/")
            req = body if isinstance(body, dict) else {}
            if not req.get("action"):
                req = {"action": sub.replace("-", "_") if sub else "status"}
            payload = _field_body_system_dispatch(req, timeout=120)
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-eye-threat"):
            sub = path[len("/api/field-eye-threat"):].strip("/")
            req = body if isinstance(body, dict) else {}
            if not req.get("action"):
                req = {"action": sub.replace("-", "_") if sub else "status"}
            payload = _field_eye_threat_dispatch(req, timeout=60)
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/hostess7/anatomy-books"):
            sub = path[len("/api/hostess7/anatomy-books"):].strip("/")
            book_py = INSTALL_ROOT / "lib" / "hostess7-anatomy-book.py"
            if not book_py.is_file():
                payload = {"ok": False, "error": "anatomy_book_missing"}
            elif sub in ("build", "build-all"):
                payload = _nexus_py_json(book_py, [sub], timeout=180)
            elif sub in ("", "index", "list"):
                payload = _nexus_py_json(book_py, ["index"], timeout=30)
            else:
                payload = _nexus_py_json(book_py, ["build-one", sub], timeout=60)
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-audio-dac"):
            sub = path[len("/api/field-audio-dac"):].strip("/")
            req = body if isinstance(body, dict) else {}
            if not req.get("action"):
                req = {"action": sub.replace("-", "_") if sub else "apply"}
            payload = _field_audio_dac_dispatch(req, timeout=90)
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-audio-settings"):
            script = INSTALL_ROOT / "lib" / "field-audio-settings.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_audio_settings_missing"}), "application/json")
                return
            sub = path[len("/api/field-audio-settings") :].strip("/")
            if sub in ("apply", "settings") or (not sub and isinstance(body, dict) and body):
                patch = body if isinstance(body, dict) else {}
                payload = _nexus_py_json(script, ["apply", json.dumps(patch)], timeout=20)
            elif sub in ("", "status", "json"):
                payload = _nexus_py_json(script, ["json"], timeout=20)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_field_audio_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-display-settings"):
            script = INSTALL_ROOT / "lib" / "field-display-settings.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_display_settings_missing"}), "application/json")
                return
            sub = path[len("/api/field-display-settings") :].strip("/")
            if sub in ("apply", "settings") or (not sub and isinstance(body, dict) and body):
                patch = body if isinstance(body, dict) else {}
                payload = _nexus_py_json(script, ["apply", json.dumps(patch)], timeout=20)
            elif sub in ("", "status", "json"):
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
                self._send(404, json.dumps({"ok": False, "error": "unknown_field_display_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-thermal-guard"):
            script = INSTALL_ROOT / "lib" / "field-thermal-guard.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_thermal_guard_missing"}), "application/json")
                return
            sub = path[len("/api/field-thermal-guard") :].strip("/")
            if sub in ("cycle", "gatekeeper"):
                payload = _nexus_py_json(script, [sub], timeout=30)
            elif sub in ("anomaly",):
                payload = _nexus_py_json(script, ["anomaly"], timeout=15)
            elif sub in ("", "status", "json"):
                payload = _nexus_py_json(script, ["json"], timeout=25)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_field_thermal_guard_action"}), "application/json")
                return
            code = 200 if payload.get("ok", payload.get("headroom_pct") is not None) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-ammoos-blocks"):
            script = INSTALL_ROOT / "lib" / "field-ammoos-blocks.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_ammoos_blocks_missing"}), "application/json")
                return
            sub = path[len("/api/field-ammoos-blocks") :].strip("/")
            if sub in ("publish", "refresh"):
                payload = _nexus_py_json(script, ["publish"], timeout=30)
            elif sub in ("scan",):
                payload = _nexus_py_json(script, ["scan"], timeout=25)
            elif sub in ("thermal",):
                payload = _nexus_py_json(script, ["thermal"], timeout=15)
            elif sub in ("", "status", "json"):
                payload = _nexus_py_json(script, ["json"], timeout=25)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_field_ammoos_blocks_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-audio-secure-bind"):
            script = INSTALL_ROOT / "lib" / "field-audio-secure-bind.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_audio_secure_bind_missing"}), "application/json")
                return
            sub = path[len("/api/field-audio-secure-bind") :].strip("/")
            if sub in ("bind", "auto"):
                args = ["auto"] if sub == "auto" else ["bind"]
                sink = str((body or {}).get("sink_name") or (body or {}).get("sink") or "").strip()
                if sink:
                    args.append(sink)
                if (body or {}).get("force"):
                    args.append("--force")
                payload = _nexus_py_json(script, args, timeout=30)
            elif sub in ("probe", "hardware"):
                payload = _nexus_py_json(script, ["probe"], timeout=25)
            elif sub in ("", "status", "json"):
                payload = _nexus_py_json(script, ["json"], timeout=25)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_field_audio_secure_bind_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/video-codec"):
            pipe_script = INSTALL_ROOT / "lib" / "field-video-codec-pipe.py"
            if not pipe_script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_video_codec_pipe_missing"}), "application/json")
                return
            sub = path[len("/api/video-codec") :].strip("/")
            dispatch_body = dict(body if isinstance(body, dict) else {})
            if sub and sub not in ("decode", "probe", "route", "battery", "pipe", "status"):
                dispatch_body.setdefault("action", sub)
            elif sub == "decode":
                dispatch_body["action"] = "decode"
            elif sub == "probe":
                dispatch_body["action"] = "probe"
            elif sub == "route":
                dispatch_body["action"] = "route"
            elif sub == "battery":
                dispatch_body["action"] = "battery"
            else:
                dispatch_body.setdefault("action", "status")
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(pipe_script), "dispatch"],
                    input=json.dumps(dispatch_body),
                    capture_output=True,
                    text=True,
                    timeout=360,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "video_codec_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "video_codec_dispatch_failed"}
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-big-drive":
            script = INSTALL_ROOT / "lib" / "field-big-drive.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_big_drive_missing"}), "application/json")
                return
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(body if isinstance(body, dict) else {}),
                    capture_output=True,
                    text=True,
                    timeout=180,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "field_big_drive_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "dispatch_failed"}
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-storage":
            script = INSTALL_ROOT / "lib" / "field-storage.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_storage_missing"}), "application/json")
                return
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(body if isinstance(body, dict) else {}),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "field_storage_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "dispatch_failed"}
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-g16-launch"):
            script = INSTALL_ROOT / "lib" / "field-g16-launch.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_g16_launch_missing"}), "application/json")
                return
            sub = path[len("/api/field-g16-launch") :].strip("/")
            if sub == "run" or (not sub and isinstance(body, dict) and body.get("path")):
                path_arg = str((body or {}).get("path") or "").strip()
                if not path_arg:
                    self._send(400, json.dumps({"ok": False, "error": "path_required"}), "application/json")
                    return
                timeout = int((body or {}).get("timeout") or 180)
                payload = _nexus_py_json(
                    script,
                    ["run", path_arg],
                    timeout=min(timeout + 30, 300),
                )
            elif sub == "discover":
                payload = _nexus_py_json(script, ["discover"], timeout=120)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_field_g16_launch_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-popcorn"):
            script = INSTALL_ROOT / "lib" / "field-popcorn-player.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_popcorn_missing"}), "application/json")
                return
            sub = path[len("/api/field-popcorn") :].strip("/")
            if sub == "thumb":
                payload = _nexus_py_json(script, ["thumb", json.dumps(body if isinstance(body, dict) else {})], timeout=30)
            elif sub == "thumb-mode":
                payload = _nexus_py_json(script, ["thumb-mode", json.dumps(body if isinstance(body, dict) else {})], timeout=15)
            elif sub == "position":
                payload = _nexus_py_json(script, ["position", json.dumps(body if isinstance(body, dict) else {})], timeout=15)
            elif sub in ("settings",) or (not sub and isinstance(body, dict) and body and not body.get("data_url")):
                patch = body if isinstance(body, dict) else {}
                payload = _nexus_py_json(script, ["settings", json.dumps(patch)], timeout=30)
            elif sub == "scan":
                payload = _nexus_py_json(script, ["scan"], timeout=120)
            elif sub == "inspect":
                media_id = str((body or {}).get("media_id") or (body or {}).get("id") or "").strip()
                deep = not bool((body or {}).get("light"))
                if media_id:
                    args = ["inspect", media_id] + ([] if deep else ["--light"])
                    payload = _nexus_py_json(script, args, timeout=120)
                else:
                    payload = {"ok": False, "error": "id_required"}
            elif sub == "details":
                media_id = str((body or {}).get("media_id") or (body or {}).get("id") or "").strip()
                if media_id:
                    payload = _nexus_py_json(script, ["details", media_id], timeout=120)
                else:
                    payload = {"ok": False, "error": "id_required"}
            elif not sub and isinstance(body, dict) and body.get("data_url"):
                payload = _nexus_py_json(script, ["thumb", json.dumps(body)], timeout=30)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_field_popcorn_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-ellie-fier"):
            script = INSTALL_ROOT / "lib" / "field-ellie-fier.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_ellie_fier_missing"}), "application/json")
                return
            sub = path[len("/api/field-ellie-fier") :].strip("/")
            if sub in ("", "status", "json"):
                do_scan = bool((body or {}).get("scan")) if isinstance(body, dict) else False
                args = ["json"] + (["--scan"] if do_scan else [])
                payload = _nexus_py_json(script, args, timeout=180)
            elif sub == "scan":
                payload = _nexus_py_json(script, ["scan"], timeout=300)
            elif sub == "threat":
                payload = _nexus_py_json(script, ["threat"], timeout=300)
            elif sub == "slices":
                payload = _nexus_py_json(script, ["slices"], timeout=120)
            elif sub == "authority":
                payload = _nexus_py_json(script, ["authority"], timeout=60)
            elif sub.startswith("pillar/"):
                slug = sub[len("pillar/") :].strip("/").split("/")[0]
                do_scan = bool((body or {}).get("scan")) if isinstance(body, dict) else False
                if not slug:
                    payload = {"ok": False, "error": "pillar_required"}
                else:
                    args = ["pillar", slug] + (["--scan"] if do_scan else [])
                    payload = _nexus_py_json(script, args, timeout=180)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_ellie_fier_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 404
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-final-eye-canvas"):
            sub = path[len("/api/field-final-eye-canvas"):].strip("/")
            req = body if isinstance(body, dict) else {}
            if sub == "connect":
                req = {**req, "action": "connect", "connect": True}
            elif sub == "feed":
                req = {**req, "action": "feed"}
            elif not req.get("action"):
                req = {**req, "action": "status"}
            payload = _field_final_eye_canvas_dispatch(req, timeout=60)
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-broadcaster") or path.startswith("/api/field-obs"):
            script = INSTALL_ROOT / "lib" / "field-broadcaster.py"
            if not script.is_file():
                script = INSTALL_ROOT / "lib" / "field-obs.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "broadcaster_missing"}), "application/json")
                return
            prefix = "/api/field-broadcaster" if path.startswith("/api/field-broadcaster") else "/api/field-obs"
            sub = path[len(prefix) :].strip("/")
            if sub == "chamber":
                req = body if isinstance(body, dict) else {}
                if not req.get("action"):
                    req = {"action": "status"}
                payload = _field_broadcaster_chamber_dispatch(req, timeout=90)
            elif sub in ("", "status", "json"):
                payload = _nexus_py_json(script, ["json"], timeout=45)
            elif sub in ("launch", "go-live", "golive"):
                cmd = "go-live" if sub in ("go-live", "golive") else "launch"
                payload = _nexus_py_json(script, [cmd], timeout=30)
            elif sub == "record":
                payload = _nexus_py_json(script, ["record"], timeout=30)
            elif sub == "virtualcam":
                payload = _nexus_py_json(script, ["virtualcam"], timeout=30)
            elif sub in ("clear-filters", "clear_filters", "passthrough"):
                payload = _nexus_py_json(script, ["clear-filters"], timeout=30)
            elif sub == "audio":
                audio_py = INSTALL_ROOT / "lib" / "field-broadcaster-audio.py"
                if body and isinstance(body, dict) and body.get("clear"):
                    payload = _nexus_py_json(audio_py, ["clear"], timeout=30)
                elif body and isinstance(body, dict) and body:
                    payload = _nexus_py_json(audio_py, ["settings", json.dumps(body)], timeout=30)
                else:
                    payload = _nexus_py_json(audio_py, ["json"], timeout=30)
            elif sub == "settings":
                patch = body if isinstance(body, dict) else {}
                payload = _nexus_py_json(script, ["settings", json.dumps(patch)], timeout=30)
            elif sub == "studio":
                req = body if isinstance(body, dict) else {}
                payload = _field_broadcaster_studio_dispatch(req, timeout=90)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_broadcaster_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-taskbar-pins":
            pins_py = INSTALL_ROOT / "lib" / "field-taskbar-pins.py"
            req = body if isinstance(body, dict) else {}
            if pins_py.is_file():
                try:
                    proc = subprocess.run(
                        [sys.executable, str(pins_py), "dispatch", json.dumps(req)],
                        capture_output=True,
                        text=True,
                        timeout=15,
                        env=_field_stack_env(),
                    )
                    payload = json.loads(proc.stdout or "{}")
                except (subprocess.TimeoutExpired, json.JSONDecodeError):
                    payload = {"ok": False, "error": "taskbar_pins_failed"}
            else:
                payload = {"ok": False, "error": "taskbar_pins_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/ammoos-themes":
            script = INSTALL_ROOT / "lib" / "ammoos-theme-engine.py"
            if not script.is_file():
                self._send(503, json.dumps({"ok": False, "error": "ammoos_theme_engine_missing"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(req, ensure_ascii=False),
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
                payload = {"ok": False, "error": str(exc)}
            code = 200 if isinstance(payload, dict) and payload.get("ok", True) else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/weapons-defense", "/api/hostess7-weapons-defense"):
            script = INSTALL_ROOT / "lib" / "hostess7-weapons-defense.py"
            if not script.is_file():
                self._send(503, json.dumps({"ok": False, "error": "hostess7_weapons_defense_missing"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            env["NEXUS_HOSTESS7_FULL_CONTROL"] = "1"
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(req, ensure_ascii=False),
                    capture_output=True,
                    text=True,
                    timeout=90,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
                payload = {"ok": False, "error": str(exc)}
            code = 200 if isinstance(payload, dict) and payload.get("ok", True) else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/system-control", "/api/hostess7-system-control"):
            script = INSTALL_ROOT / "lib" / "hostess7-system-control.py"
            if not script.is_file():
                self._send(503, json.dumps({"ok": False, "error": "hostess7_system_control_missing"}), "application/json")
                return
            req = body if isinstance(body, dict) else {}
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            env["NEXUS_HOSTESS7_FULL_CONTROL"] = "1"
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(req, ensure_ascii=False),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
                payload = {"ok": False, "error": str(exc)}
            code = 200 if isinstance(payload, dict) and payload.get("ok", True) else 400
            self._send(code, json.dumps(payload if isinstance(payload, dict) else {"ok": False}), "application/json")
            return

        if path == "/api/field-shell-settings":
            script = INSTALL_ROOT / "lib" / "field-shell-settings.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "field_shell_settings_missing"}), "application/json")
                return
            patch = body if isinstance(body, dict) else {}
            if patch.get("resolution") and patch.get("display_id"):
                payload = _nexus_py_json(
                    script,
                    ["resolution", str(patch.get("display_id")), str(patch.get("resolution"))],
                    timeout=20,
                )
            else:
                env = os.environ.copy()
                env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
                env["NEXUS_STATE_DIR"] = str(STATE_DIR)
                try:
                    proc = subprocess.run(
                        [sys.executable, str(script), "apply"],
                        input=json.dumps(patch, ensure_ascii=False),
                        capture_output=True,
                        text=True,
                        timeout=20,
                        env=env,
                    )
                    payload = json.loads(proc.stdout or "{}")
                except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
                    payload = {"ok": False, "error": str(exc)}
            code = 200 if payload.get("ok", True) and not payload.get("error") else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-monster-monitor"):
            script = INSTALL_ROOT / "lib" / "field-monster-monitor.py"
            if not script.is_file():
                self._send(503, json.dumps({"ok": False, "error": "monster_monitor_missing"}), "application/json")
                return
            if path.rstrip("/").endswith("/action") or isinstance(body, dict) and body.get("action"):
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("monster", script)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        payload = mod.handle_action(body if isinstance(body, dict) else {})
                    else:
                        payload = {"ok": False, "error": "monster_load_failed"}
                except Exception as exc:
                    payload = {"ok": False, "error": str(exc)}
            else:
                payload = _nexus_py_json(script, ["json"], timeout=25) or {"ok": False}
            code = 200 if payload.get("ok") else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-os-keybindings"):
            script = INSTALL_ROOT / "lib" / "field-os-keybindings.py"
            if not script.is_file():
                self._send(503, json.dumps({"ok": False, "error": "os_keybindings_missing"}), "application/json")
                return
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(body if isinstance(body, dict) else {}),
                    capture_output=True,
                    text=True,
                    timeout=15,
                    env=_field_stack_env(),
                )
                payload = json.loads(proc.stdout or "{}")
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
                payload = {"ok": False, "error": str(exc)}
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-monster-shell"):
            script = INSTALL_ROOT / "lib" / "field-monster-shell.py"
            if not script.is_file():
                self._send(503, json.dumps({"ok": False, "error": "monster_shell_missing"}), "application/json")
                return
            try:
                import importlib.util

                spec = importlib.util.spec_from_file_location("monster_shell", script)
                if not spec or not spec.loader:
                    payload = {"ok": False, "error": "monster_shell_load_failed"}
                else:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    req = body if isinstance(body, dict) else {}
                    sub = path[len("/api/field-monster-shell") :].strip("/")
                    if sub in ("hang-respond", "hang_respond"):
                        req = {**req, "action": "hang_respond"}
                    elif sub in ("nuke", "kill"):
                        req = {**req, "action": "nuke"}
                    elif sub in ("dispatch",):
                        req = {**req, "action": req.get("action") or "hang_pending"}
                    payload = mod.handle_api(req)
            except Exception as exc:
                payload = {"ok": False, "error": str(exc)}
            code = 200 if payload.get("ok", True) and not payload.get("error") else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-performance-flyout":
            reset = bool((body or {}).get("reset"))
            payload = _field_perf_flyout_sample(reset=reset)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in (
            "/api/field-depth-snap",
            "/api/field-depth/instant",
            "/api/field-depth-singularizer/instant",
        ):
            script = INSTALL_ROOT / "lib" / "field-depth-singularizer.py"
            verb = "field_die" if str((body or {}).get("action") or "").lower() == "field_die" else "instant"
            if script.is_file():
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(script), verb],
                        input=json.dumps(body or {}, ensure_ascii=False),
                        capture_output=True,
                        text=True,
                        timeout=5,
                        env=env,
                    )
                    payload = json.loads(proc.stdout.strip() or "{}") if proc.stdout.strip() else {"ok": False}
                except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
                    payload = {"ok": False, "error": str(exc), "instant": True}
            else:
                payload = {"ok": False, "error": "singularizer_missing", "instant": True}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/ai-integration":
            peer = self.client_address[0] if self.client_address else "127.0.0.1"
            hdrs = {k: v for k, v in self.headers.items()}
            payload = _ai_integration_json(body, peer=str(peer), headers=hdrs)
            code = 200 if payload.get("ok") or str(payload.get("action", "")) in ("status", "json", "posture") else 403
            if payload.get("error") == "human_integration_forbidden":
                code = 403
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/tristate-installer"):
            sub = path[len("/api/tristate-installer") :].strip("/") or "status"
            if sub in ("", "status"):
                payload = _tristate_installer_json()
            elif sub == "scan-wrdt":
                payload = _tristate_installer_json(verb="scan-wrdt")
            elif sub == "refield":
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-drive-converter.py",
                    ["refield"],
                    timeout=120,
                )
                if isinstance(payload, dict) and "posture" not in payload:
                    payload["posture"] = _tristate_installer_json()
            elif sub == "drive-restore-scan":
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-drive-converter.py",
                    ["scan-restore"],
                    timeout=180,
                )
                if isinstance(payload, dict):
                    payload["posture"] = _tristate_installer_json()
            elif sub == "drive-restore":
                dc_py = INSTALL_ROOT / "lib" / "field-drive-converter.py"
                if body.get("dry_run"):
                    payload = _nexus_py_json(dc_py, ["restore-out"], timeout=600)
                else:
                    payload = _nexus_py_json(
                        dc_py,
                        ["restore-out", "--apply", "--confirm"],
                        timeout=900,
                    )
                if isinstance(payload, dict) and "posture" not in payload:
                    payload["posture"] = _tristate_installer_json()
            elif sub == "drive-audit":
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-drive-converter.py",
                    ["audit"],
                    timeout=120,
                )
                if isinstance(payload, dict):
                    payload["posture"] = _tristate_installer_json()
            elif sub == "defield-audit":
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-drive-converter.py",
                    ["defield-audit"],
                    timeout=300,
                )
                if isinstance(payload, dict):
                    payload["posture"] = _tristate_installer_json()
            elif sub == "purge-nested-drive":
                nf_py = INSTALL_ROOT / "lib" / "field-non-fielded-safety.py"
                args = ["purge-nested-drive"]
                if body.get("apply") or body.get("confirm"):
                    args.append("--apply")
                payload = _nexus_py_json(nf_py, args, timeout=300)
                if isinstance(payload, dict):
                    payload["posture"] = _tristate_installer_json()
            elif sub == "drive-convert":
                dc_py = INSTALL_ROOT / "lib" / "field-drive-converter.py"
                if body.get("dry_run"):
                    payload = _nexus_py_json(dc_py, ["dry-run"], timeout=600)
                else:
                    payload = _tristate_elevated_json("wrdt-apply", body)
                if isinstance(payload, dict) and "posture" not in payload:
                    payload["posture"] = _tristate_installer_json()
            elif sub == "commit":
                payload = _tristate_elevated_json("commit", body)
            elif sub == "wrdt-apply":
                payload = _tristate_elevated_json("wrdt-apply", body)
            elif sub == "reboot":
                payload = _tristate_elevated_json("reboot", body)
            elif sub == "grok-prep":
                payload = _tristate_elevated_json("grok-prep", body)
            elif sub == "znetwork-offer":
                payload = _tristate_installer_json(verb="znetwork-offer", body=body)
                if isinstance(payload, dict) and "posture" not in payload:
                    payload["posture"] = _tristate_installer_json()
            elif sub == "znetwork-choice":
                payload = _tristate_installer_json(verb="znetwork-choice", body=body)
                if isinstance(payload, dict) and "posture" not in payload:
                    payload["posture"] = _tristate_installer_json()
            elif sub == "acquire-root":
                payload = _tristate_acquire_root_json()
            elif sub == "root-status":
                root = _tristate_root_json()
                payload = {"ok": bool(root.get("ready")), "root": root}
            elif sub == "install-nexus":
                installer = INSTALL_ROOT / "install-all.sh"
                if not installer.is_file():
                    installer = INSTALL_ROOT / "install-all.sh"
                dev = INSTALL_ROOT.parent / "install-all.sh"
                if not installer.is_file() and dev.is_file():
                    installer = dev
                bridge = INSTALL_ROOT / "lib" / "nexus-pkexec-bridge.sh"
                env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL_ROOT), "NEXUS_STATE_DIR": str(STATE_DIR)}
                if installer.is_file() and (_tristate_has_cached_sudo() or os.geteuid() == 0):
                    subprocess.Popen(
                        ["sudo", "-n", "-E", "bash", str(installer)],
                        env=env,
                    )
                    payload = {"ok": True, "started": True, "installer": str(installer), "method": "sudo_cached"}
                elif installer.is_file() and bridge.is_file():
                    subprocess.Popen(
                        [
                            "pkexec",
                            "--action",
                            "com.nexus.field.install",
                            str(bridge),
                            "run-install",
                            str(installer),
                        ],
                        env=env,
                    )
                    payload = {"ok": True, "started": True, "installer": str(installer), "method": "pkexec"}
                else:
                    payload = {
                        "ok": False,
                        "error": "installer_missing",
                        "hint": "Run ./install-all.sh from NewLatest",
                    }
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown tristate action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/drop-in-orchestrator") or path.startswith("/api/drop-in"):
            sub = path.split("/api/drop-in-orchestrator")[-1].split("/api/drop-in")[-1].strip("/") or "status"
            orch = INSTALL_ROOT / "lib" / "field-drop-in-orchestrator.py"
            if sub in ("", "status", "json"):
                payload = _nexus_py_json(orch, ["json"], timeout=45)
            elif sub == "force":
                payload = _nexus_py_json(orch, ["force"], timeout=60)
            elif sub == "defield":
                payload = _nexus_py_json(orch, ["defield"], timeout=320)
            elif sub == "redata":
                args = ["redata"]
                if body.get("confirm") or body.get("apply"):
                    args.append("--confirm")
                payload = _nexus_py_json(orch, args, timeout=900)
            elif sub == "secure-network":
                payload = _nexus_py_json(orch, ["secure-network"], timeout=120)
            elif sub == "pipeline":
                args = ["pipeline"]
                if body.get("confirm") or body.get("apply"):
                    args.append("--confirm")
                payload = _nexus_py_json(orch, args, timeout=900)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown drop-in action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/sovereign-protocol"):
            sub = path[len("/api/sovereign-protocol") :].strip("/") or "status"
            bridge = INSTALL_ROOT / "lib" / "field-sovereign-protocol-bridge.py"
            if sub in ("", "status", "json"):
                payload = _nexus_py_json(bridge, ["json"], timeout=40)
            elif sub == "activate":
                payload = _nexus_py_json(bridge, ["activate"], timeout=90)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown protocol action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/display-open"):
            sub = path[len("/api/display-open") :].strip("/") or "status"
            disp = INSTALL_ROOT / "lib" / "field-display-open.py"
            if sub in ("", "status", "json"):
                payload = _nexus_py_json(disp, ["json"], timeout=25)
            elif sub in ("local", "browser"):
                route = str(body.get("route") or "underlay-f9")
                display_id = str(body.get("display_id") or body.get("display") or "")
                args = ["local"]
                if display_id:
                    args.append(display_id)
                if route:
                    args.append(route)
                payload = _nexus_py_json(disp, args, timeout=50)
            elif sub == "peers":
                payload = _nexus_py_json(disp, ["peers"], timeout=60)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown display action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/plate-test-runner") or path.startswith("/api/plate-tests"):
            sub = path.split("/api/plate-test-runner")[-1].split("/api/plate-tests")[-1].strip("/") or "status"
            runner = INSTALL_ROOT / "lib" / "field-plate-test-runner.py"
            if sub in ("", "status", "json"):
                payload = _nexus_py_json(runner, ["json"], timeout=30)
            elif sub in ("run", "incomplete", "cycle"):
                tier = str(body.get("tier") or "")
                args = ["run"] if not tier else ["run-tier", tier]
                payload = _nexus_py_json(runner, args, timeout=900)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown plate-test action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/g16-compiler-sense") or path.startswith("/api/compiler-sense-plate"):
            sub = path.split("/api/g16-compiler-sense")[-1].split("/api/compiler-sense-plate")[-1].strip("/") or "status"
            sense_py = INSTALL_ROOT / "lib" / "g16-compiler-sense-plate.py"
            if sub in ("", "status", "json"):
                payload = _nexus_py_json(sense_py, ["json"], timeout=40)
            elif sub in ("cycle", "optimize", "meld"):
                payload = _nexus_py_json(sense_py, ["cycle"], timeout=45)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown compiler-sense action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-operator"):
            sub = path[len("/api/field-operator") :].strip("/") or "board"
            op_py = INSTALL_ROOT / "lib" / "field-operator.py"
            if sub in ("", "board", "iron-plate"):
                args = ["iron-plate"] if sub == "iron-plate" else ["board"]
                if body.get("override"):
                    args.extend(["--override", str(body.get("override"))])
                payload = _nexus_py_json(op_py, args, timeout=60)
            elif sub == "communicate":
                target = str(body.get("id") or body.get("path") or "").strip()
                args = ["communicate", target] if target else ["json"]
                if body.get("override"):
                    args.extend(["--override", str(body.get("override"))])
                payload = _nexus_py_json(op_py, args, timeout=30)
            elif sub == "fast":
                names = body.get("profiles") or []
                args = ["fast"] + [str(n) for n in names if n]
                payload = _nexus_py_json(op_py, args or ["fast"], timeout=30)
            elif sub == "route":
                target = str(body.get("id") or body.get("target") or "").strip()
                if not target:
                    self._send(400, json.dumps({"ok": False, "error": "missing id"}), "application/json")
                    return
                override = str(body.get("override") or "").strip() or None
                payload = _field_operator_copilot_route(target, override=override)
            elif sub == "route-batch":
                batch = body.get("batch") or body.get("targets") or []
                if not batch:
                    self._send(400, json.dumps({"ok": False, "error": "missing batch"}), "application/json")
                    return
                override = str(body.get("override") or "").strip() or None
                payload = _field_operator_copilot_batch([str(x) for x in batch if x], override=override)
            elif sub == "copilot":
                payload = _field_operator_copilot_status()
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown operator action"}), "application/json")
                return
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/kill-codes/execute":
            code = str(body.get("code") or "").strip()
            if not code:
                self._send(400, json.dumps({"ok": False, "error": "missing code"}), "application/json")
                return
            payload = _kill_codes_json(["execute", json.dumps(body, ensure_ascii=False)], timeout=90)
            code_http = 200 if payload.get("ok") else (403 if payload.get("friendly_refused") else 400)
            self._send(code_http, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/jockey/ack":
            alert_id = str(body.get("alert_id") or "").strip()[:256]
            response = str(body.get("response") or "seen").strip().lower()
            if not alert_id:
                self._send(400, json.dumps({"ok": False, "error": "missing alert_id"}), "application/json")
                return
            if response not in ("seen", "needs_action", "needs_more_action"):
                self._send(400, json.dumps({"ok": False, "error": "invalid response"}), "application/json")
                return
            payload = _jockey_json(["ack", alert_id, response], timeout=15)
            code = 200 if payload.get("ok") else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/packet-field/capture":
            script = INSTALL_ROOT / "lib" / "packet-field.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "packet_field_missing"}), "application/json")
                return
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            proc = subprocess.run(
                [sys.executable, str(script), "capture"],
                capture_output=True,
                text=True,
                timeout=12,
                env=env,
            )
            try:
                doc = json.loads(proc.stdout or "{}")
            except json.JSONDecodeError:
                doc = {"ok": False, "error": (proc.stderr or "capture_failed")[:300]}
            if isinstance(doc, dict):
                doc["ok"] = proc.returncode == 0
            self._send(200 if proc.returncode == 0 else 500, json.dumps(doc), "application/json")
            return

        if path in ("/api/bugfinder/scan", "/api/bugfinder/text", "/api/bugfinder/ironclad-cycle", "/api/code-bugfinder/scan"):
            bug_py = INSTALL_ROOT / "lib" / "field-code-bugfinder.py"
            if not bug_py.is_file():
                self._send(500, json.dumps({"ok": False, "error": "bugfinder_missing"}), "application/json")
                return
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            env.setdefault("SG_ROOT", str(INSTALL_ROOT.parent.parent))
            env.setdefault("HOSTESS7_ROOT", str(_resolve_hostess7_root()))
            if path.endswith("/ironclad-cycle"):
                max_t = int(body.get("max_targets") or 6)
                max_c = int(body.get("max_compares") or 48)
                proc = subprocess.run(
                    [
                        sys.executable, str(bug_py), "ironclad-cycle",
                        "--max-targets", str(max_t),
                        "--max-compares", str(max_c),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    env=env,
                )
            elif path.endswith("/text"):
                snippet = str(body.get("text", body.get("code", ""))).strip()
                if not snippet:
                    self._send(400, json.dumps({"ok": False, "error": "missing text"}), "application/json")
                    return
                proc = subprocess.run(
                    [sys.executable, str(bug_py), "text", snippet[:12000]],
                    capture_output=True,
                    text=True,
                    timeout=90,
                    env=env,
                )
            else:
                target = str(body.get("path", body.get("target", ""))).strip()
                if not target:
                    self._send(400, json.dumps({"ok": False, "error": "missing path"}), "application/json")
                    return
                max_c = int(body.get("max_compares") or body.get("max") or 256)
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

        if path.startswith("/api/library/"):
            script = INSTALL_ROOT / "lib" / "h7-library-bridge.py"
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            env.setdefault("HOSTESS7_ROOT", str(_resolve_hostess7_root()))
            env.setdefault("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage")

            reader_py = INSTALL_ROOT / "lib" / "h7-library-secure-reader.py"

            if path == "/api/library/checkout":
                action = str(body.get("action", "checkout")).strip().lower()
                book_id = str(body.get("book_id", body.get("book", ""))).strip()
                if action == "remind":
                    payload = _lib_json(["checkout-remind"], timeout=30)
                    self._send(200, json.dumps(payload), "application/json")
                    return
                if not book_id:
                    self._send(400, json.dumps({"ok": False, "error": "missing book_id"}), "application/json")
                    return
                if action in ("checkin", "return"):
                    payload = _lib_json(["checkin", book_id, str(body.get("patron", "operator"))], timeout=30)
                else:
                    co_body = {
                        "days": body.get("days", 14),
                        "patron": body.get("patron", "operator"),
                        "book": body.get("book_meta") or body.get("book"),
                    }
                    payload = _lib_json(["checkout", book_id, json.dumps(co_body)], timeout=30)
                self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
                return

            if path == "/api/g16/language-test/start":
                mod = _g16_language_test_mod()
                if not mod:
                    self._send(500, json.dumps({"ok": False, "error": "g16_language_test_missing"}), "application/json")
                    return
                import threading

                if getattr(mod, "_RUNNING", False):
                    self._send(200, json.dumps({"ok": True, "started": False, "message": "already_running"}), "application/json")
                    return

                def _bg() -> None:
                    mod.run_all()

                threading.Thread(target=_bg, daemon=True).start()
                self._send(200, json.dumps({"ok": True, "started": True}), "application/json")
                return

            if path == "/api/library/reader/issue":
                book_id = str(body.get("book_id", body.get("book", ""))).strip()
                if not book_id:
                    self._send(400, json.dumps({"ok": False, "error": "missing book_id"}), "application/json")
                    return
                if not script.is_file():
                    self._send(500, json.dumps({"ok": False, "error": "library_bridge_missing"}), "application/json")
                    return
                proc = subprocess.run(
                    [sys.executable, str(script), "reader-issue", book_id],
                    capture_output=True,
                    text=True,
                    timeout=45,
                    env=env,
                )
                try:
                    payload = json.loads(proc.stdout or "{}")
                except json.JSONDecodeError:
                    payload = {"ok": False, "error": "reader_issue_failed"}
                self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
                return

            if path in ("/api/library/reader/bookmarks", "/api/library/reader/progress", "/api/library/reader/layout"):
                if not reader_py.is_file():
                    self._send(500, json.dumps({"ok": False, "error": "secure_reader_missing"}), "application/json")
                    return
                book_id = str(body.get("book_id", "")).strip()
                token = str(body.get("token", self.headers.get("X-Reader-Token", ""))).strip()
                signature = str(body.get("signature", self.headers.get("X-Reader-Signature", ""))).strip()
                if not book_id or not token or not signature:
                    self._send(403, json.dumps({"ok": False, "error": "invalid_session"}), "application/json")
                    return
                import importlib.util
                spec = importlib.util.spec_from_file_location("h7_secure_reader", reader_py)
                if not spec or not spec.loader:
                    self._send(500, json.dumps({"ok": False, "error": "secure_reader_missing"}), "application/json")
                    return
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if path.endswith("/bookmarks"):
                    action = str(body.get("action", "list")).strip().lower()
                    if action == "add":
                        payload = mod.save_bookmark(
                            book_id,
                            page=int(body.get("page", 1)),
                            label=str(body.get("label", "")),
                            token=token,
                            signature=signature,
                        )
                    elif action == "delete":
                        payload = mod.delete_bookmark(
                            book_id,
                            bookmark_id=str(body.get("bookmark_id", "")),
                            token=token,
                            signature=signature,
                        )
                    else:
                        payload = mod.list_bookmarks(book_id, token=token, signature=signature)
                elif path.endswith("/progress"):
                    payload = mod.save_progress(
                        book_id,
                        page=int(body.get("page", 1)),
                        page_count=int(body.get("page_count", 0)),
                        token=token,
                        signature=signature,
                    )
                else:
                    payload = mod.save_layout(
                        book_id,
                        layout=body.get("layout") if isinstance(body.get("layout"), dict) else {},
                        token=token,
                        signature=signature,
                    )
                self._send(200 if payload.get("ok") else 403, json.dumps(payload), "application/json")
                return

            if path == "/api/library/upload":
                if not script.is_file():
                    self._send(500, json.dumps({"ok": False, "error": "library_bridge_missing"}), "application/json")
                    return
                proc = subprocess.run(
                    [sys.executable, str(script), "upload", json.dumps(body)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=env,
                )
                try:
                    payload = json.loads(proc.stdout or "{}")
                except json.JSONDecodeError:
                    payload = {"ok": False, "error": "upload_failed"}
                self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
                return

        if path == "/api/ammoos-incorporate/apply":
            script = INSTALL_ROOT / "lib" / "ammoos-incorporate.py"
            if not script.is_file():
                self._send(500, json.dumps({"ok": False, "error": "ammoos_incorporate_missing"}), "application/json")
                return
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "apply"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
                payload = {"ok": False, "error": "ammoos_incorporate_apply_failed", "detail": str(exc)[:200]}
            self._send(200 if payload.get("ok") else 500, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/ammoos-startup/apply":
            script = INSTALL_ROOT / "lib" / "ammoos-startup-sovereign.py"
            if not script.is_file():
                self._send(500, json.dumps({"ok": False, "error": "ammoos_startup_sovereign_missing"}), "application/json")
                return
            choice = ""
            if isinstance(body, dict):
                choice = str(body.get("choice") or "").strip().lower()
            if not choice:
                qparams = parse_qs(urlparse(self.path).query)
                choice = str((qparams.get("choice") or [""])[0]).strip().lower()
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "apply", "--choice", choice],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
                payload = {"ok": False, "error": "ammoos_startup_apply_failed", "detail": str(exc)[:200]}
            self._send(200 if payload.get("ok") else 400, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/ammoos-update/apply":
            lock = _nexus_update_lock(["status"])
            if lock.get("locked"):
                self._send(
                    409,
                    json.dumps({
                        "ok": False,
                        "error": "update_in_progress",
                        "update_in_progress": True,
                        "message": lock.get("message") or "Update already running",
                        "update_lock": lock,
                    }),
                    "application/json",
                )
                return
            try:
                STATE_DIR.joinpath("update-needs-sudo.json").unlink(missing_ok=True)
            except OSError:
                pass
            upd = _ammoos_update_check(force=True)
            if upd.get("update_in_progress"):
                self._send(
                    409,
                    json.dumps({
                        "ok": False,
                        "error": "update_in_progress",
                        "update_in_progress": True,
                        "message": upd.get("label") or "Update in progress",
                        "update_lock": upd.get("update_lock"),
                    }),
                    "application/json",
                )
                return
            if not upd.get("update_available"):
                self._send(200, json.dumps({"ok": True, "already_current": True, **upd}), "application/json")
                return
            target = str(upd.get("latest") or "")
            previous = str(upd.get("previous") or upd.get("current") or "")
            update_mode = str(upd.get("update_mode") or os.environ.get("AMMOOS_UPDATE_MODE", "git_tree"))
            apply_via = str(upd.get("apply_via") or "git_tree")
            tarball_url = str(upd.get("source_tarball") or "")
            lock_phase = "git_fetch" if update_mode != "release" else "download_tarball"
            acq = _nexus_update_lock([
                "acquire",
                "--holder=ammoos-update-os",
                f"--phase={lock_phase}",
                f"--target={target}",
                f"--previous={previous}",
            ])
            if not acq.get("ok"):
                self._send(
                    409,
                    json.dumps({
                        "ok": False,
                        "error": acq.get("error") or "update_in_progress",
                        "update_in_progress": True,
                        "message": acq.get("message") or "Could not acquire update lock",
                    }),
                    "application/json",
                )
                return
            token = str(acq.get("token") or "")
            git_dir = _resolve_ammoos_source_root()
            install_sh = None
            if git_dir:
                for name in ("install-all.sh", "stealth_install.sh"):
                    candidate = git_dir / name
                    if candidate.is_file():
                        install_sh = candidate
                        break
            if update_mode == "release" and not tarball_url:
                _nexus_update_lock(["release", f"--token={token}"])
                self._send(
                    500,
                    json.dumps({
                        "ok": False,
                        "applied": False,
                        "error": "release_tarball_missing",
                        "message": "No AmmoOS release tarball URL — use git_tree or publish a release",
                        "release_url": upd.get("release_url"),
                    }),
                    "application/json",
                )
                return
            if apply_via == "git_tree" and not git_dir:
                _nexus_update_lock(["release", f"--token={token}"])
                self._send(
                    500,
                    json.dumps({
                        "ok": False,
                        "applied": False,
                        "error": "ammoos_tree_missing",
                        "message": "AmmoOS source tree not found — clone github.com/ZacharyGeurts/AmmoOS",
                        "install_root": str(INSTALL_ROOT),
                    }),
                    "application/json",
                )
                return
            started = _spawn_nexus_update_apply(
                git_dir=git_dir,
                install_sh=install_sh,
                token=token,
                target=target,
                previous=previous,
                tarball_url=tarball_url,
                update_mode=update_mode,
                apply_via=apply_via,
            )
            if not started:
                _nexus_update_lock(["release", f"--token={token}"])
                self._send(
                    500,
                    json.dumps({
                        "ok": False,
                        "error": "update_spawn_failed",
                        "message": "Could not start AmmoOS background update — see update-apply.log",
                    }),
                    "application/json",
                )
                return
            lock_now = _nexus_update_lock(["status"])
            self._send(
                202,
                json.dumps({
                    "ok": True,
                    "started": True,
                    "update_in_progress": True,
                    "reload_panel": True,
                    "message": f"AmmoOS update started — {previous} → {target}",
                    "previous": previous,
                    "latest": target,
                    "update_mode": update_mode,
                    "apply_via": apply_via,
                    "source_tarball": tarball_url or None,
                    "source_root": str(git_dir) if git_dir else None,
                    "update_lock": lock_now,
                    "log": str(STATE_DIR / "update-apply.log"),
                    "github_repo": upd.get("github_repo"),
                }),
                "application/json",
            )
            return

        if path == "/api/ammoos-update/sudo-prompt":
            lock = _nexus_update_lock(["status"])
            needs = _nexus_update_needs_sudo()
            if not needs and not lock.get("locked"):
                self._send(
                    400,
                    json.dumps({"ok": False, "error": "no_pending_sudo"}),
                    "application/json",
                )
                return
            git_dir = _resolve_ammoos_source_root()
            token = str(lock.get("token") or os.environ.get("NEXUS_UPDATE_LOCK_TOKEN", ""))
            previous = str(lock.get("previous_version") or (needs.get("previous") if needs else ""))
            target = str(lock.get("target_version") or (needs.get("target") if needs else ""))
            update_mode = str(
                os.environ.get("AMMOOS_UPDATE_MODE", "git_tree")
                if not needs else needs.get("update_mode") or os.environ.get("AMMOOS_UPDATE_MODE", "git_tree")
            )
            env = os.environ.copy()
            env.update({
                "NEXUS_INSTALL_ROOT": str(INSTALL_ROOT),
                "NEXUS_STATE_DIR": str(STATE_DIR),
                "NEXUS_UPDATE_LOCK_TOKEN": token,
                "NEXUS_UPDATE_TARGET": target,
                "NEXUS_UPDATE_PREVIOUS": previous,
                "NEXUS_UPDATE_MODE": update_mode,
                "AMMOOS_UPDATE_MODE": update_mode,
            })
            if git_dir:
                env["NEXUS_UPDATE_GIT_DIR"] = str(git_dir)
            cache_upd = _ammoos_update_check()
            if cache_upd.get("source_tarball"):
                env["NEXUS_UPDATE_TARBALL_URL"] = str(cache_upd["source_tarball"])
            helper = INSTALL_ROOT / "lib" / "nexus-update-apply.sh"
            try:
                subprocess.Popen(
                    ["bash", str(helper)],
                    env=env,
                    start_new_session=True,
                    cwd=str(git_dir or INSTALL_ROOT),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._send(
                    202,
                    json.dumps({
                        "ok": True,
                        "prompt_started": True,
                        "message": "Password prompt opened — complete sudo to finish AmmoOS update",
                    }),
                    "application/json",
                )
            except OSError as exc:
                self._send(
                    500,
                    json.dumps({"ok": False, "error": str(exc)}),
                    "application/json",
                )
            return

        if path == "/api/update/apply":
            lock = _nexus_update_lock(["status"])
            if lock.get("locked"):
                self._send(
                    409,
                    json.dumps({
                        "ok": False,
                        "error": "update_in_progress",
                        "update_in_progress": True,
                        "message": lock.get("message") or "Update already running",
                        "update_lock": lock,
                    }),
                    "application/json",
                )
                return
            try:
                STATE_DIR.joinpath("update-needs-sudo.json").unlink(missing_ok=True)
            except OSError:
                pass
            upd = _nexus_update_check(force=True)
            if upd.get("update_in_progress"):
                self._send(
                    409,
                    json.dumps({
                        "ok": False,
                        "error": "update_in_progress",
                        "update_in_progress": True,
                        "message": upd.get("label") or "Update in progress",
                        "update_lock": upd.get("update_lock"),
                    }),
                    "application/json",
                )
                return
            if not upd.get("update_available"):
                self._send(200, json.dumps({"ok": True, "already_current": True, **upd}), "application/json")
                return
            target = str(upd.get("latest") or "")
            previous = str(upd.get("previous") or upd.get("current") or "")
            lock_phase = "download_tarball" if str(upd.get("update_mode") or "release") == "release" else "git_fetch"
            acq = _nexus_update_lock([
                "acquire",
                "--holder=panel",
                f"--phase={lock_phase}",
                f"--target={target}",
                f"--previous={previous}",
            ])
            if not acq.get("ok"):
                self._send(
                    409,
                    json.dumps({
                        "ok": False,
                        "error": acq.get("error") or "update_in_progress",
                        "update_in_progress": True,
                        "message": acq.get("message") or "Could not acquire update lock",
                    }),
                    "application/json",
                )
                return
            token = str(acq.get("token") or "")
            update_mode = str(upd.get("update_mode") or os.environ.get("NEXUS_UPDATE_MODE", "release"))
            tarball_url = str(upd.get("source_tarball") or "")
            git_dir = _resolve_nexus_source_root()
            install_sh = None
            if git_dir:
                for name in ("install-all.sh", "stealth_install.sh"):
                    candidate = git_dir / name
                    if candidate.is_file():
                        install_sh = candidate
                        break
            if update_mode == "release" and not tarball_url:
                _nexus_update_lock(["release", f"--token={token}"])
                self._send(
                    500,
                    json.dumps({
                        "ok": False,
                        "applied": False,
                        "error": "release_tarball_missing",
                        "message": "No release tarball URL — check GitHub release assets",
                        "release_url": upd.get("release_url"),
                    }),
                    "application/json",
                )
                return
            if update_mode != "release" and (not git_dir or not install_sh):
                _nexus_update_lock(["release", f"--token={token}"])
                self._send(
                    500,
                    json.dumps({
                        "ok": False,
                        "applied": False,
                        "error": "install_tree_missing",
                        "message": "install-all.sh not found — set NEXUS_SHIELD_SOURCE or use release mode",
                        "install_root": str(INSTALL_ROOT),
                    }),
                    "application/json",
                )
                return
            apply_via = str(upd.get("apply_via") or "")
            catalog_url = str(upd.get("catalog_url") or "")
            started = _spawn_nexus_update_apply(
                git_dir=git_dir,
                install_sh=install_sh,
                token=token,
                target=target,
                previous=previous,
                tarball_url=tarball_url,
                update_mode=update_mode,
                apply_via=apply_via,
                catalog_url=catalog_url,
            )
            if not started:
                _nexus_update_lock(["release", f"--token={token}"])
                self._send(
                    500,
                    json.dumps({
                        "ok": False,
                        "error": "update_spawn_failed",
                        "message": "Could not start background update — see update-apply.log",
                    }),
                    "application/json",
                )
                return
            lock_now = _nexus_update_lock(["status"])
            self._send(
                202,
                json.dumps({
                    "ok": True,
                    "started": True,
                    "update_in_progress": True,
                    "reload_panel": True,
                    "message": (
                        f"Release installer started — {previous} → {target}"
                        if update_mode == "release"
                        else f"Update started — {previous} → {target}"
                    ),
                    "previous": previous,
                    "latest": target,
                    "update_mode": update_mode,
                    "apply_via": upd.get("apply_via") or ("release_tarball" if update_mode == "release" else "git_tree"),
                    "source_tarball": tarball_url or None,
                    "tristate_installer_url": upd.get("tristate_installer_url"),
                    "source_root": str(git_dir) if git_dir else None,
                    "update_lock": lock_now,
                    "log": str(STATE_DIR / "update-apply.log"),
                }),
                "application/json",
            )
            return

        if path == "/api/update/sudo-prompt":
            lock = _nexus_update_lock(["status"])
            needs = _nexus_update_needs_sudo()
            if not needs and not lock.get("locked"):
                self._send(
                    400,
                    json.dumps({"ok": False, "error": "no_pending_sudo"}),
                    "application/json",
                )
                return
            git_dir = _resolve_nexus_source_root()
            install_sh = None
            if git_dir:
                for name in ("install-all.sh", "stealth_install.sh"):
                    candidate = git_dir / name
                    if candidate.is_file():
                        install_sh = candidate
                        break
            token = str(lock.get("token") or os.environ.get("NEXUS_UPDATE_LOCK_TOKEN", ""))
            previous = str(lock.get("previous_version") or (needs.get("previous") if needs else ""))
            target = str(lock.get("target_version") or (needs.get("target") if needs else ""))
            update_mode = str(
                os.environ.get("NEXUS_UPDATE_MODE", "release")
                if not needs else needs.get("update_mode") or os.environ.get("NEXUS_UPDATE_MODE", "release")
            )
            env = os.environ.copy()
            env.update({
                "NEXUS_INSTALL_ROOT": str(INSTALL_ROOT),
                "NEXUS_STATE_DIR": str(STATE_DIR),
                "NEXUS_UPDATE_LOCK_TOKEN": token,
                "NEXUS_UPDATE_TARGET": target,
                "NEXUS_UPDATE_PREVIOUS": previous,
                "NEXUS_UPDATE_MODE": update_mode,
            })
            if git_dir:
                env["NEXUS_UPDATE_GIT_DIR"] = str(git_dir)
            if install_sh and install_sh.is_file():
                env["NEXUS_UPDATE_INSTALL_SH"] = str(install_sh)
            cache_upd = _nexus_update_check()
            if cache_upd.get("source_tarball"):
                env["NEXUS_UPDATE_TARBALL_URL"] = str(cache_upd["source_tarball"])
            helper = INSTALL_ROOT / "lib" / "nexus-update-apply.sh"
            try:
                subprocess.Popen(
                    ["bash", str(helper)],
                    env=env,
                    start_new_session=True,
                    cwd=str(git_dir),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._send(
                    202,
                    json.dumps({
                        "ok": True,
                        "prompt_started": True,
                        "message": "Password prompt opened — complete sudo to finish update",
                    }),
                    "application/json",
                )
            except OSError as exc:
                self._send(
                    500,
                    json.dumps({"ok": False, "error": str(exc)}),
                    "application/json",
                )
            return

        if path == "/api/home-protector/block":
            entity_id = str(body.get("entity_id", body.get("id", ""))).strip()
            if not entity_id:
                self._send(400, json.dumps({"ok": False, "error": "missing entity_id"}), "application/json")
                return
            force = body.get("force") in (True, 1, "1", "true", "yes", "on")
            args = ["block", entity_id]
            if force:
                args.append("--force")
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "home-protector.py", args)
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/home-protector/permit":
            entity_id = str(body.get("entity_id", body.get("id", ""))).strip()
            if not entity_id:
                self._send(400, json.dumps({"ok": False, "error": "missing entity_id"}), "application/json")
                return
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "home-protector.py", ["permit", entity_id])
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/home-protector/block-all":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "home-protector.py", ["block-all"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/local-services/close":
            listener_id = str(body.get("listener_id", body.get("id", ""))).strip()
            if not listener_id:
                self._send(400, json.dumps({"ok": False, "error": "missing listener_id"}), "application/json")
                return
            force = body.get("force") in (True, 1, "1", "true", "yes", "on")
            args = ["close", listener_id]
            if force:
                args.append("--force")
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "local-services-audit.py", args)
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/local-services/permit":
            listener_id = str(body.get("listener_id", body.get("id", ""))).strip()
            if not listener_id:
                self._send(400, json.dumps({"ok": False, "error": "missing listener_id"}), "application/json")
                return
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "local-services-audit.py", ["permit", listener_id])
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/local-services/close-all":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "local-services-audit.py", ["close-all"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/heavyboi/ingest":
            intel = body if isinstance(body, dict) else {}
            if not intel.get("kill_orders") and not intel.get("orders"):
                self._send(400, json.dumps({"ok": False, "error": "missing kill_orders"}), "application/json")
                return
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "heavyboi-importer.py",
                ["ingest", "--json", json.dumps(intel)],
            )
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/heavyboi/pending":
            intel = body if isinstance(body, dict) else {}
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "heavyboi-importer.py",
                ["pending", json.dumps(intel)],
            )
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/signals-field":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "signals-field.py", ["build"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/stress-terror-discern":
            script = INSTALL_ROOT / "lib" / "field-stress-terror-discern.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "stress_terror_discern_missing"}), "application/json")
                return
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            req = body if isinstance(body, dict) else {}
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(req, ensure_ascii=False),
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
                payload = {"ok": False, "error": str(exc)}
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field/field", "/api/field/plate-field", "/api/field/parallel"):
            publish = str(body.get("publish", "0")).strip().lower() in ("1", "true", "yes")
            payload = _field_field_payload(publish=publish)
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field":
            _nexus_shell_publish_panel()
            if STATUS_JSON.is_file():
                self._send(200, STATUS_JSON.read_text(encoding="utf-8"), "application/json")
            else:
                self._send(200, '{"field":true,"panel_ready":false}', "application/json")
            return

        if path == "/api/field-radio":
            action = str(body.get("action") or "build").strip().lower()
            if action == "tune":
                tune_body = {
                    "station_id": body.get("station_id") or body.get("id") or "",
                    "call_sign": body.get("call_sign") or "",
                    "freq_mhz": body.get("freq_mhz"),
                }
                payload = _nexus_py_json(
                    INSTALL_ROOT / "lib" / "field-radio-catcher.py",
                    ["tune", json.dumps(tune_body)],
                )
                self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
                return
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-radio-catcher.py", ["build"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-antenna":
            payload = {
                "schema": "field-antenna/v1",
                "destroyed": True,
                "removed": True,
                "ok": False,
                "error": "field_antenna_destroyed",
            }
            self._send(410, json.dumps(payload), "application/json")
            return

        if path == "/api/field-dns":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-dns.py", ["build"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-outside-talk":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-outside-talk.py", ["build"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-outside-talk/connect":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-outside-talk.py",
                ["connect", json.dumps(body if isinstance(body, dict) else {})],
            )
            self._send(200 if payload.get("ok") or payload.get("session_id") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/field-outside-talk/probe":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-outside-talk.py",
                ["probe", json.dumps(body if isinstance(body, dict) else {})],
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-outside-talk/disconnect":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-outside-talk.py",
                ["disconnect", json.dumps(body if isinstance(body, dict) else {})],
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-drive":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-drive-system.py", ["build"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-drive/talk":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-drive-system.py",
                ["talk", json.dumps(body if isinstance(body, dict) else {})],
            )
            self._send(200 if payload.get("ok") is not False else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/panel-language":
            code = str((body or {}).get("code") or "").strip()
            if not code:
                self._send(400, json.dumps({"ok": False, "error": "missing code"}), "application/json")
                return
            remember = (body or {}).get("remember", True)
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "panel-i18n.py",
                ["set", code, json.dumps({"code": code, "remember": remember})],
            )
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/hostess-profile":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess-profile.py",
                ["save", json.dumps(body if isinstance(body, dict) else {})],
            )
            if payload.get("extreme_active") or int(payload.get("host_star_tier") or 0) >= 4:
                inner = _nexus_shell_prelude() + "nexus_host_extreme_apply_if_eligible"
                _run_nexus_bash(inner, timeout=60)
                tier = _nexus_py_json(INSTALL_ROOT / "lib" / "host-security-tier.py", ["publish"])
                payload["extreme_applied"] = bool(tier.get("extreme_active"))
                payload["host_security"] = tier
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/humanoid-motion/load":
            skill_id = str(body.get("skill_id") or body.get("skill") or "").strip()
            if not skill_id:
                self._send(400, json.dumps({"ok": False, "error": "missing skill_id"}), "application/json")
                return
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "humanoid-motion-training.py",
                ["load", skill_id],
                timeout=30,
            )
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/humanoid-motion/train":
            skill_id = str(body.get("skill_id") or body.get("skill") or "").strip()
            ticks = int(body.get("ticks") or body.get("duration_ticks") or 0)
            args = ["train"]
            if skill_id:
                args.append(skill_id)
            if ticks > 0:
                args.append(str(ticks))
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "humanoid-motion-training.py",
                args,
                timeout=90,
            )
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path in ("/api/humanoid-motion/train-blast", "/api/humanoid-motion/blast"):
            skill_id = str(body.get("skill_id") or body.get("skill") or "").strip()
            ticks = int(body.get("ticks") or body.get("blast_ticks") or 0)
            args = ["blast"]
            if skill_id:
                args.append(skill_id)
            if ticks > 0:
                args.append(str(ticks))
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "humanoid-motion-training.py",
                args,
                timeout=30,
            )
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/audio-train/ingest":
            sample = body.get("sample") or body
            sid = str(body.get("source_id") or sample.get("source_id") or "manual").strip()
            ingest_body = json.dumps({
                "source_id": sid,
                "label": body.get("label") or sample.get("label") or sid,
                "kind": body.get("kind") or sample.get("kind") or "",
                "sample": sample if isinstance(sample, dict) else body,
            })
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "audio-train.py", ["ingest", ingest_body])
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/field-toolkit/defense":
            defense_id = str(body.get("defense_id", body.get("id", ""))).strip()
            if not defense_id:
                self._send(400, json.dumps({"ok": False, "error": "missing defense_id"}), "application/json")
                return
            enabled = body.get("enabled")
            args = ["toggle", defense_id]
            if enabled is not None:
                args.append("on" if enabled else "off")
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-toolkit-db.py", args)
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path in (
            "/api/field-toolkit/sever",
            "/api/field-toolkit/regional-disable",
            "/api/field-toolkit/human-threat",
            "/api/field-toolkit/hell-rip",
            "/api/field-toolkit/field-die",
            "/api/field-toolkit/laser-corridor",
            "/api/field-toolkit/disable",
        ):
            script = INSTALL_ROOT / "lib" / "field-toolkit-db.py"
            if path == "/api/field-toolkit/sever":
                ip = str(body.get("ip", "")).strip()
                if not ip:
                    self._send(400, json.dumps({"ok": False, "error": "missing ip"}), "application/json")
                    return
                payload = _nexus_py_json(script, ["sever", ip])
            elif path == "/api/field-toolkit/regional-disable":
                region = str(body.get("region", body.get("value", ""))).strip()
                if not region:
                    self._send(400, json.dumps({"ok": False, "error": "missing region"}), "application/json")
                    return
                args = ["regional", region]
                if body.get("field") and ":" not in region:
                    args.append(str(body.get("field")))
                payload = _nexus_py_json(script, args)
            elif path == "/api/field-toolkit/human-threat":
                payload = _nexus_py_json(script, ["human-threat"])
            elif path == "/api/field-toolkit/hell-rip":
                payload = _nexus_py_json(script, ["hell-rip"])
            elif path == "/api/field-toolkit/field-die":
                ip = str(body.get("ip", "")).strip()
                payload = _nexus_py_json(script, ["field-die"] + ([ip] if ip else []))
            elif path == "/api/field-toolkit/laser-corridor":
                ip = str(body.get("ip", "")).strip()
                if not ip:
                    self._send(400, json.dumps({"ok": False, "error": "missing ip"}), "application/json")
                    return
                payload = _nexus_py_json(script, ["laser-corridor", ip])
            else:
                payload = _nexus_py_json(
                    script,
                    ["disable", json.dumps(body, ensure_ascii=False)],
                )
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/host-attack/trash":
            pin_id = str(body.get("id", "")).strip()
            if not pin_id:
                self._send(400, json.dumps({"ok": False, "error": "missing id"}), "application/json")
                return
            ok = _nexus_host_map_trash_add(pin_id)
            if ok:
                map_py = INSTALL_ROOT / "lib" / "host-attack-map.py"
                if map_py.is_file():
                    env = os.environ.copy()
                    env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
                    env["NEXUS_STATE_DIR"] = str(STATE_DIR)
                    subprocess.run(
                        [sys.executable, str(map_py), "build-fast"],
                        capture_output=True,
                        timeout=45,
                        env=env,
                    )
            self._send(200 if ok else 500, json.dumps({"ok": ok, "id": pin_id}), "application/json")
            return

        if path == "/api/honorability/accept":
            domain = str(body.get("domain", body.get("host", ""))).strip().lower()
            if not domain:
                self._send(400, json.dumps({"ok": False, "error": "missing domain"}), "application/json")
                return
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "honorability-db.py", ["accept", domain])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/honorability/rate":
            domain = str(body.get("domain", "")).strip().lower()
            stars = body.get("stars")
            if not domain or stars is None:
                self._send(400, json.dumps({"ok": False, "error": "missing domain or stars"}), "application/json")
                return
            note = str(body.get("note", ""))[:200]
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "honorability-db.py",
                ["rate", domain, str(int(stars)), note],
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-rf/shield":
            enabled = body.get("enabled")
            auto_rfkill = body.get("auto_rfkill")
            lawful_kick = body.get("lawful_kick")
            shoot_to_kill = body.get("shoot_to_kill")
            if enabled is None:
                self._send(400, json.dumps({"ok": False, "error": "missing enabled"}), "application/json")
                return
            flag = "on" if enabled in (True, 1, "1", "true", "yes", "on") else "off"
            auto_flag = "on" if auto_rfkill in (True, 1, "1", "true", "yes", "on") else "off"
            lawful_flag = "on" if lawful_kick in (True, 1, "1", "true", "yes", "on", None) else "off"
            shoot_flag = "on" if shoot_to_kill in (True, 1, "1", "true", "yes", "on", None) else "off"
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "field-rf-sentinel.py",
                ["shield", flag, auto_flag, lawful_flag, shoot_flag],
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/field-rf/cycle":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "field-rf-sentinel.py", ["cycle"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/terror-spiderweb/rebuild":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "terror-spiderweb.py",
                ["build"],
                timeout=120,
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/lethal-enforcement/cycle":
            dry = body.get("dry_run") in (True, 1, "1", "true")
            args = ["cycle"] + (["--dry-run"] if dry else [])
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "lethal-enforcement.py", args)
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/hostess7-lethal-insight/ask":
            claim = str(body.get("claim") or "MERCILESS lethal heaven hell spatial trespass").strip()
            target = body.get("target") if isinstance(body.get("target"), dict) else {}
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-lethal-insight.py",
                ["ask", claim, json.dumps(target)],
            )
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/queen-eyeball":
            timeout = 180 if str(body.get("action") or "").lower() in (
                "wire", "fused_analyze", "neural_analyze", "bench", "weaponize"
            ) else 120
            payload = _queen_ball_dispatch(_queen_eyeball_script(), body, timeout=timeout)
            self._send(200 if payload.get("ok", True) else 400, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/queen-earball", "/api/final-ear", "/api/earball"):
            timeout = 180 if str(body.get("action") or "").lower() in (
                "eye_ear_fusion", "secure_identify", "sense_all", "spectrum", "spectrum_analyze"
            ) else 90
            payload = _queen_ball_dispatch(_queen_earball_script(), body, timeout=timeout)
            self._send(200 if payload.get("ok", True) else 400, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/queen-mouthball", "/api/final-mouth", "/api/mouthball"):
            payload = _queen_ball_dispatch(_queen_mouthball_script(), body, timeout=90)
            self._send(200 if payload.get("ok", True) else 400, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/queen-boot":
            script = _queen_boot_script()
            if not script.is_file():
                self._send(500, json.dumps({"ok": False, "error": "queen_boot_missing"}), "application/json")
                return
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            env.setdefault("QUEEN_ROOT", str(INSTALL_ROOT if (INSTALL_ROOT / ".queen-inside").is_file() else INSTALL_ROOT.parent / "Queen"))
            env.setdefault("HOSTESS7_ROOT", str(INSTALL_ROOT / "Hostess7"))
            for k in ("NEXUS_AI_SECURE_CHANNEL", "QUEEN_AI_TELEMETRY_OK", "QUEEN_GROK_BUILD", "QUEEN_GROK_BUILD_SECURE", "QUEEN_FIELD_GPU"):
                env.setdefault(k, "1")
            act = str(body.get("action") or "").lower()
            timeout = 7200 if act in ("rebuild", "build", "full-boot", "boot") else 600 if act in ("login", "zac_restore") else 60
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(body if isinstance(body, dict) else {}),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "dispatch_failed"}
            self._send(200 if payload.get("ok", True) else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/grok-build":
            script = _grok_build_script()
            if not script.is_file():
                self._send(500, json.dumps({"ok": False, "error": "grok_build_missing"}), "application/json")
                return
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            env.setdefault("QUEEN_ROOT", str(INSTALL_ROOT if (INSTALL_ROOT / ".queen-inside").is_file() else INSTALL_ROOT.parent / "Queen"))
            for k in ("NEXUS_AI_SECURE_CHANNEL", "QUEEN_AI_TELEMETRY_OK", "QUEEN_GROK_BUILD", "QUEEN_GROK_BUILD_SECURE"):
                env.setdefault(k, "1")
            timeout = 120 if str(body.get("action") or "").lower() in ("acp_start", "start") else 30
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(body if isinstance(body, dict) else {}),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "dispatch_failed"}
            self._send(200 if payload.get("ok", True) else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/queen-build":
            script = _queen_build_script()
            if not script.is_file():
                self._send(500, json.dumps({"ok": False, "error": "queen_build_missing"}), "application/json")
                return
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            env.setdefault("QUEEN_ROOT", str(INSTALL_ROOT if (INSTALL_ROOT / ".queen-inside").is_file() else INSTALL_ROOT.parent / "Queen"))
            timeout = 3700 if str(body.get("action") or "").lower() in ("run", "run-all", "run_all", "build", "build_all") else 60
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(body if isinstance(body, dict) else {}),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "dispatch_failed"}
            self._send(200 if payload.get("ok", True) else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/logic-gate/ingress":
            gate_body = body if isinstance(body, dict) else {}
            payload = str(
                gate_body.get("payload") or gate_body.get("message") or gate_body.get("text") or ""
            )
            proc = subprocess.run(
                [sys.executable, str(INSTALL_ROOT / "lib" / "nexus-logic-gate.py"), "ingress"],
                input=json.dumps(gate_body),
                capture_output=True,
                text=True,
                timeout=20,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL_ROOT), "NEXUS_STATE_DIR": str(STATE_DIR)},
            )
            try:
                gate_out = json.loads(proc.stdout or "{}")
            except json.JSONDecodeError:
                gate_out = {"ok": False, "error": "logic_gate_failed"}
            self._send(200 if gate_out.get("permit") else 403, json.dumps(gate_out), "application/json")
            return

        if path == "/api/logic-gate/egress":
            gate_body = body if isinstance(body, dict) else {}
            proc = subprocess.run(
                [sys.executable, str(INSTALL_ROOT / "lib" / "nexus-logic-gate.py"), "egress"],
                input=json.dumps(gate_body),
                capture_output=True,
                text=True,
                timeout=20,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL_ROOT), "NEXUS_STATE_DIR": str(STATE_DIR)},
            )
            try:
                gate_out = json.loads(proc.stdout or "{}")
            except json.JSONDecodeError:
                gate_out = {"ok": False, "error": "logic_gate_failed"}
            self._send(200 if gate_out.get("permit") else 403, json.dumps(gate_out), "application/json")
            return

        _TRAIN_TRACK_TIMEOUTS = {
            "master_curriculum": 150,
            "curriculum": 150,
            "codecraft": 240,
            "iq_battery": 200,
            "self_interaction": 200,
            "turing_battery": 300,
            "neural_suite": 180,
            "omnibus": 240,
            "calculator": 200,
            "biology": 200,
            "engineering": 200,
            "combat": 200,
            "mos": 200,
        }

        if path in ("/api/ironclad/realize", "/api/ironclad/seal"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "ironclad-plate.py", ["realize"], timeout=30)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/field-underlay-surface"):
            sub = path[len("/api/field-underlay-surface") :].strip("/") or "status"
            script = INSTALL_ROOT / "lib" / "field-underlay-surface.py"
            if sub in ("", "status", "json"):
                payload = _nexus_py_json(script, ["json"], timeout=25) if script.is_file() else {
                    "schema": "field-underlay-surface/v1", "ok": False, "error": "underlay_surface_missing",
                }
            elif sub == "drop":
                payload = _nexus_py_json(script, ["drop"], timeout=30)
            elif sub == "rise":
                payload = _nexus_py_json(script, ["rise"], timeout=60)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_underlay_surface_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-keyboard-sovereign"):
            sub = path[len("/api/field-keyboard-sovereign") :].strip("/") or "status"
            script = INSTALL_ROOT / "lib" / "field-keyboard-sovereign.py"
            reason = str((body or {}).get("reason") or "api").strip()
            if sub in ("", "status", "json"):
                payload = _nexus_py_json(script, ["json"], timeout=15) if script.is_file() else {
                    "schema": "field-keyboard-sovereign/v1", "ok": False, "error": "keyboard_sovereign_missing",
                }
            elif sub == "engage":
                payload = _nexus_py_json(script, ["engage"], timeout=20) if script.is_file() else {
                    "schema": "field-keyboard-sovereign/v1", "ok": False, "error": "keyboard_sovereign_missing",
                }
            elif sub == "release":
                payload = _nexus_py_json(script, ["release", reason], timeout=20) if script.is_file() else {
                    "schema": "field-keyboard-sovereign/v1", "ok": False, "error": "keyboard_sovereign_missing",
                }
            else:
                payload = {"ok": False, "error": "unknown_keyboard_sovereign_action", "sub": sub}
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/ammoos/close":
            script = INSTALL_ROOT / "lib" / "queen-integrated-browser.py"
            payload = (
                _nexus_py_json(script, ["close"], timeout=20)
                if script.is_file()
                else {"ok": False, "error": "queen_integrated_browser_missing"}
            )
            code = 200 if payload.get("ok") else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/host/poweroff":
            payload = _host_poweroff_json()
            code = 200 if payload.get("ok") else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path.startswith("/api/field-host-freeze"):
            sub = path[len("/api/field-host-freeze") :].strip("/") or "status"
            mode = str((body or {}).get("mode") or "soft").strip().lower()
            elevated = bool((body or {}).get("elevated") or (body or {}).get("confirm"))
            script = INSTALL_ROOT / "lib" / "field-host-freeze.py"
            if sub in ("", "status", "json"):
                payload = _nexus_py_json(script, ["json"], timeout=45) if script.is_file() else {
                    "schema": "field-host-freeze/v1", "ok": False, "error": "field_host_freeze_missing",
                }
            elif sub == "prepare":
                payload = (
                    _host_freeze_elevated_json("prepare", mode)
                    if elevated
                    else _nexus_py_json(script, ["prepare", mode], timeout=45)
                )
            elif sub == "freeze":
                payload = _host_freeze_elevated_json("freeze", mode) if elevated else _nexus_py_json(
                    script, ["freeze", mode], timeout=45,
                )
            elif sub == "thaw":
                payload = _host_freeze_elevated_json("thaw") if elevated else _nexus_py_json(script, ["thaw"], timeout=45)
            elif sub in ("close", "hibernate", "shutdown"):
                close_mode = mode if mode in ("mem", "disk") else "disk"
                payload = _host_freeze_elevated_json("close", close_mode) if elevated else _nexus_py_json(
                    script, ["close", close_mode], timeout=45,
                )
            elif sub in ("resume-witness", "resume", "wake"):
                payload = _nexus_py_json(script, ["resume-witness"], timeout=45)
            elif sub == "lock-memory":
                payload = _nexus_py_json(script, ["lock-memory"], timeout=30)
            else:
                self._send(404, json.dumps({"ok": False, "error": "unknown_host_freeze_action"}), "application/json")
                return
            code = 200 if payload.get("ok", True) and not payload.get("error") else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/ironclad/reality-field/cycle", "/api/ironclad/truth-serum/cycle"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "ironclad-reality-field.py", ["cycle"], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/ironclad/field-sanity/pass", "/api/ironclad/field-sanity/cycle", "/api/ironclad/field-sanity"):
            script = INSTALL_ROOT / "lib" / "ironclad-field-sanity.py"
            if not script.is_file():
                self._send(200, json.dumps({"ok": False, "error": "script_missing"}), "application/json")
                return
            cmd = "cycle" if path.endswith("/cycle") else "pass"
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), cmd],
                    input=json.dumps(body if isinstance(body, dict) else {}),
                    capture_output=True,
                    text=True,
                    timeout=45,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "script_failed", "detail": (proc.stderr or "")[:200]}
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/userwatch", "/api/hostess7-userwatch"):
            script = INSTALL_ROOT / "lib" / "hostess7-userwatch.py"
            req = body if isinstance(body, dict) else {}
            payload = _nexus_py_json(script, ["dispatch", json.dumps(req)], timeout=45)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/training/assess", "/api/hostess7-training/assess"):
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-training.py", ["assess"], timeout=60)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/archaeology/help", "/api/hostess7-archaeology/help"):
            req = body if isinstance(body, dict) else {}
            q = str(req.get("query") or req.get("q") or "").strip()
            human = bool(req.get("human")) or str(req.get("audience") or "").lower() == "human"
            args = ["help", q] if q else ["help"]
            if human:
                args.append("--human")
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-archaeology-training.py", args, timeout=25)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/archaeology/corroborate", "/api/hostess7-archaeology/corroborate"):
            req = body if isinstance(body, dict) else {}
            q = str(req.get("claim") or req.get("q") or req.get("query") or "").strip()
            args = ["corroborate", q] if q else ["corroborate"]
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "hostess7-archaeology-training.py", args, timeout=20)
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/operator", "/api/hostess7-operator", "/api/hostess7/operator/brief",
                    "/api/hostess7/operator/evaluate", "/api/hostess7/operator/catalog"):
            script = INSTALL_ROOT / "lib" / "hostess7-operator.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "hostess7_operator_missing"}), "application/json")
                return
            dispatch_body = dict(body if isinstance(body, dict) else {})
            if path.endswith("/brief"):
                dispatch_body["action"] = "brief"
            elif path.endswith("/evaluate"):
                dispatch_body["action"] = "evaluate"
            elif path.endswith("/catalog"):
                dispatch_body["action"] = "catalog"
            else:
                dispatch_body.setdefault("action", "panel")
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(dispatch_body),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "hostess7_operator_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "hostess7_operator_dispatch_failed"}
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/hostess7/tasklist", "/api/hostess7-tasklist"):
            script = INSTALL_ROOT / "lib" / "hostess7-tasklist.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "hostess7_tasklist_missing"}), "application/json")
                return
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(body if isinstance(body, dict) else {}),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "hostess7_tasklist_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "hostess7_tasklist_dispatch_failed"}
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/hostess7/virtual-workspace", "/api/hostess7-virtual-workspace"):
            script = INSTALL_ROOT / "lib" / "hostess7-virtual-workspace.py"
            if not script.is_file():
                self._send(404, json.dumps({"ok": False, "error": "hostess7_virtual_workspace_missing"}), "application/json")
                return
            env = _field_stack_env()
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(body if isinstance(body, dict) else {}),
                    capture_output=True,
                    text=True,
                    timeout=180,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "hostess7_virtual_timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "hostess7_virtual_dispatch_failed"}
            code = 200 if payload.get("ok", True) else 400
            self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/hostess7/training/solidify", "/api/hostess7/training/complete"):
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-training.py",
                ["complete", "--skip-omnibus"],
                timeout=600,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/training/self-interaction", "/api/hostess7-training/self-interaction"):
            rounds = int(body.get("rounds") or 6)
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-training.py",
                ["self-interaction", str(rounds)],
                timeout=200,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/training/author", "/api/hostess7-training/author"):
            track = str(body.get("track") or body.get("track_id") or "").strip()
            args = ["author"]
            if track:
                args.append(track)
            if body.get("force"):
                args.append("--force")
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-training-author.py",
                args,
                timeout=120,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/training/gaps", "/api/hostess7-training/gaps"):
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-training-author.py",
                ["gaps"],
                timeout=90,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/training/curriculum-step", "/api/hostess7-training/curriculum-step"):
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-training.py",
                ["curriculum-step"],
                timeout=150,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path in ("/api/hostess7/training/iq", "/api/hostess7-training/iq"):
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-truth-rating.py",
                ["iq-test"],
                timeout=300,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path.startswith("/api/hostess7/training/track/") or path.startswith("/api/hostess7-training/track/"):
            track_id = path.split("/track/", 1)[-1].strip("/")
            if not track_id:
                self._send(400, json.dumps({"ok": False, "error": "track_required"}), "application/json")
                return
            args = ["track", track_id]
            if body.get("ocr_train"):
                args.append("--ocr-train")
            timeout = _TRAIN_TRACK_TIMEOUTS.get(track_id, 180)
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "hostess7-training.py",
                args,
                timeout=timeout,
            )
            self._send(200, json.dumps(payload or {"ok": False}), "application/json")
            return

        if path == "/api/hostess7-command":
            script = INSTALL_ROOT / "lib" / "hostess7-command.py"
            if not script.is_file():
                self._send(500, json.dumps({"ok": False, "error": "script_missing"}), "application/json")
                return
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            env.setdefault("HOSTESS7_ROOT", str(_resolve_hostess7_root()))
            if os.environ.get("NEXUS_LOGIC_GATE", "1") == "1":
                msg = str(body.get("message") or body.get("query") or "")
                if msg.strip() and str(body.get("action") or "ask").lower() in ("ask", "message", "chat"):
                    gate = _nexus_py_json(
                        INSTALL_ROOT / "lib" / "nexus-logic-gate.py",
                        ["ingress", msg],
                        timeout=15,
                    )
                    if not gate.get("permit"):
                        self._send(
                            403,
                            json.dumps({
                                "ok": False,
                                "logic_gate": gate,
                                "reply": "Equipment logic gate held inbound message.",
                                "threat_warn_level": "high",
                            }),
                            "application/json",
                        )
                        return
            timeout = 180 if str(body.get("action") or "").lower() in ("teach-art", "teach_art") else 120
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), "dispatch"],
                    input=json.dumps(body if isinstance(body, dict) else {}),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=env,
                )
                payload = json.loads(proc.stdout or "{}")
            except subprocess.TimeoutExpired:
                payload = {"ok": False, "error": "timeout"}
            except json.JSONDecodeError:
                payload = {"ok": False, "error": "dispatch_failed"}
            self._send(200 if payload.get("ok", True) else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/plugins/toggle":
            plugin_id = str(body.get("id", body.get("plugin_id", ""))).strip()
            if not plugin_id:
                self._send(400, json.dumps({"ok": False, "error": "missing id"}), "application/json")
                return
            enabled = body.get("enabled") in (True, 1, "1", "true", "yes", "on")
            flag = "on" if enabled else "off"
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "nexus-plugins.py",
                ["enable", flag, plugin_id],
            )
            if payload.get("ok"):
                _nexus_py_json(INSTALL_ROOT / "lib" / "nexus-plugins.py", ["merge"])
            self._send(200, json.dumps(payload), "application/json")
            return

        if path == "/api/police-agencies/select":
            agency_id = str(body.get("agency_id", body.get("id", ""))).strip()
            if not agency_id:
                self._send(400, json.dumps({"ok": False, "error": "missing agency_id"}), "application/json")
                return
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "police-agency-db.py", ["select", agency_id])
            self._send(200 if payload.get("ok") else 404, json.dumps(payload), "application/json")
            return

        if path == "/api/police-agencies/import":
            agency_id = str(body.get("agency_id", "")).strip()
            format_id = str(body.get("format_id", "")).strip()
            payload_text = str(body.get("payload", body.get("data", "")))
            filename = str(body.get("filename", ""))[:120]
            images = body.get("images") if isinstance(body.get("images"), list) else None
            if not agency_id or not format_id or not payload_text:
                self._send(400, json.dumps({"ok": False, "error": "missing agency_id, format_id, or payload"}), "application/json")
                return
            import_doc = {
                "agency_id": agency_id,
                "format_id": format_id,
                "payload": payload_text,
                "filename": filename,
                "images": images,
            }
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            proc = subprocess.run(
                [sys.executable, str(INSTALL_ROOT / "lib" / "police-agency-db.py"), "import-json", json.dumps(import_doc)],
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
            try:
                result = json.loads(proc.stdout or "{}")
            except json.JSONDecodeError:
                result = {"ok": False, "error": "import_failed"}
            self._send(200 if result.get("ok") else 400, json.dumps(result), "application/json")
            return

        if path == "/api/program-tags/apply":
            tag_ids = body.get("tag_ids") or body.get("tags")
            if isinstance(tag_ids, str):
                tag_ids = [t.strip() for t in tag_ids.split(",") if t.strip()]
            if not tag_ids:
                self._send(400, json.dumps({"ok": False, "error": "missing tag_ids"}), "application/json")
                return
            apply_doc = {
                "tag_ids": tag_ids,
                "record_key": str(body.get("record_key", "")).strip(),
                "lat": body.get("lat"),
                "lon": body.get("lon"),
                "coords": str(body.get("coords", "")),
                "place": str(body.get("place", "")),
                "address": str(body.get("address", "")),
                "city": str(body.get("city", "")),
                "country": str(body.get("country", "")),
                "label": str(body.get("label", "")),
                "notes": str(body.get("notes", "")),
            }
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            proc = subprocess.run(
                [sys.executable, str(INSTALL_ROOT / "lib" / "program-tags-db.py"), "apply-json", json.dumps(apply_doc)],
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )
            try:
                result = json.loads(proc.stdout or "{}")
            except json.JSONDecodeError:
                result = {"ok": False, "error": "tag_apply_failed"}
            self._send(200 if result.get("ok") else 400, json.dumps(result), "application/json")
            return

        if path == "/api/operator/location":
            mode = str(body.get("mode", "gps")).strip().lower()
            loc_py = INSTALL_ROOT / "lib" / "operator-location.py"
            if mode == "wireless":
                payload = _nexus_py_json(loc_py, ["wireless"])
            elif mode == "address":
                address = str(body.get("address", "")).strip()
                if not address:
                    self._send(400, json.dumps({"ok": False, "error": "missing address"}), "application/json")
                    return
                payload = _nexus_py_json(loc_py, ["address", address])
            elif mode == "gps":
                lat = body.get("lat")
                lon = body.get("lon")
                if lat is None or lon is None:
                    self._send(400, json.dumps({"ok": False, "error": "missing lat/lon"}), "application/json")
                    return
                label = str(body.get("label", ""))[:120]
                args = ["gps", str(lat), str(lon)]
                if label:
                    args.append(label)
                payload = _nexus_py_json(loc_py, args)
            else:
                self._send(400, json.dumps({"ok": False, "error": "invalid mode"}), "application/json")
                return
            if payload.get("ok") is False and payload.get("error"):
                self._send(500, json.dumps(payload), "application/json")
                return
            map_py = INSTALL_ROOT / "lib" / "host-attack-map.py"
            if map_py.is_file():
                env = os.environ.copy()
                env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
                env["NEXUS_STATE_DIR"] = str(STATE_DIR)
                subprocess.run(
                    [sys.executable, str(map_py), "build-fast"],
                    capture_output=True,
                    timeout=45,
                    env=env,
                )
            census_py = INSTALL_ROOT / "lib" / "census-field-populate.py"
            if census_py.is_file() and mode in ("address", "gps", "wireless"):
                env = os.environ.copy()
                env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
                env["NEXUS_STATE_DIR"] = str(STATE_DIR)
                subprocess.run(
                    [sys.executable, str(census_py), "populate"],
                    capture_output=True,
                    timeout=60,
                    env=env,
                )
            self._send(200, json.dumps({"ok": True, **payload}), "application/json")
            return

        if path == "/api/census-field/populate":
            census_py = INSTALL_ROOT / "lib" / "census-field-populate.py"
            address = str(body.get("address", "")).strip()
            args = ["populate"]
            if address:
                args.append(address)
            payload = _nexus_py_json(census_py, args)
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/thermal-earth/rebuild":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "thermal-earth-field.py", ["build"])
            self._send(200 if payload.get("schema") else 500, json.dumps(payload), "application/json")
            return

        if path == "/api/precision-field/rebuild":
            payload = _nexus_py_json(INSTALL_ROOT / "lib" / "precision-field.py", ["build"])
            self._send(200 if payload.get("schema") else 500, json.dumps(payload), "application/json")
            return

        if path == "/api/precision-field/place":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "precision-field.py",
                ["place", json.dumps(body)],
            )
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/autosanitize/toggle":
            enabled = bool(body.get("enabled", True))
            ok = _run_nexus_autosanitize_toggle(enabled)
            self._send(200 if ok else 500, json.dumps({"ok": ok, "enabled": enabled}), "application/json")
            return

        if path == "/api/autosanitize/undo":
            action_id = str(body.get("id", "")).strip()
            if not action_id:
                self._send(400, json.dumps({"ok": False, "error": "missing id"}), "application/json")
                return
            ok = _run_nexus_undo(action_id)
            self._send(200 if ok else 404, json.dumps({"ok": ok, "id": action_id}), "application/json")
            return

        if path == "/api/paranoia/toggle":
            block = bool(body.get("block", False))
            ok = _run_nexus_paranoia("block_on" if block else "block_off")
            self._send(200 if ok else 500, json.dumps({"ok": ok, "block": block}), "application/json")
            return

        if path == "/api/paranoia/disable":
            incident_id = str(body.get("id", "")).strip()
            if not incident_id:
                self._send(400, json.dumps({"ok": False, "error": "missing id"}), "application/json")
                return
            ok = _run_nexus_paranoia("disable", incident_id)
            self._send(200 if ok else 404, json.dumps({"ok": ok, "id": incident_id}), "application/json")
            return

        if path == "/api/nexus/restart":
            policy = str(body.get("policy", "block")).strip().lower()
            offender = str(body.get("offender_ip", body.get("offender", ""))).strip()
            script = INSTALL_ROOT / "lib" / "shutdown-guard.sh"
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            cmd = (
                f"source {INSTALL_ROOT}/lib/nexus-common.sh && "
                f"source {INSTALL_ROOT}/lib/firewall-sentinel.sh && "
                f"source {INSTALL_ROOT}/lib/threat-vectors.sh && "
                f"source {INSTALL_ROOT}/lib/packet-oracle.sh && "
                f"source {INSTALL_ROOT}/lib/paranoia-mode.sh && "
                f"source {script} && "
                f"nexus_shutdown_restart '{policy}' '{offender}'"
            )
            proc = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            ok = proc.returncode == 0
            self._send(
                200 if ok else 500,
                json.dumps({"ok": ok, "policy": policy, "offender_ip": offender}),
                "application/json",
            )
            return

        if path == "/api/firewall/authorize":
            ip = str(body.get("ip", "")).strip()
            direction = str(body.get("direction", "out")).strip().lower() or "out"
            label = str(body.get("label", "")).strip()
            if not ip:
                self._send(400, json.dumps({"ok": False, "error": "missing ip"}), "application/json")
                return
            if direction not in ("in", "out", "both"):
                direction = "out"
            ok = _run_nexus_firewall_trust("authorize", ip, direction, label)
            self._send(
                200 if ok else 500,
                json.dumps({"ok": ok, "ip": ip, "direction": direction, "label": label}),
                "application/json",
            )
            return

        if path == "/api/firewall/block":
            ip = str(body.get("ip", "")).strip()
            direction = str(body.get("direction", "out")).strip().lower() or "out"
            reason = str(body.get("reason", "harm_candidate")).strip()
            duration = str(body.get("duration", "day")).strip().lower() or "day"
            if not ip:
                self._send(400, json.dumps({"ok": False, "error": "missing ip"}), "application/json")
                return
            script = INSTALL_ROOT / "lib" / "firewall-sentinel.sh"
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            safe_ip = ip.replace("'", "'\"'\"'")
            if duration in ("forever", "permanent"):
                block_fn = f"nexus_firewall_block_ip_forever {direction} '{safe_ip}' '{reason}'"
            else:
                timeout = str(body.get("timeout", 86400))
                block_fn = f"nexus_firewall_block_ip {direction} '{safe_ip}' {timeout} '{reason}'"
            cmd = (
                f"source {INSTALL_ROOT}/lib/nexus-common.sh && nexus_load_config && "
                f"source {script} && {block_fn}"
            )
            proc = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=20, env=env)
            ok = proc.returncode == 0
            self._send(
                200 if ok else 500,
                json.dumps({"ok": ok, "ip": ip, "duration": duration}),
                "application/json",
            )
            return

        if path == "/api/firewall/unblock":
            ip = str(body.get("ip", "")).strip()
            direction = str(body.get("direction", "out")).strip().lower() or "out"
            duration = str(body.get("duration", "day")).strip().lower() or "day"
            if not ip:
                self._send(400, json.dumps({"ok": False, "error": "missing ip"}), "application/json")
                return
            script = INSTALL_ROOT / "lib" / "firewall-sentinel.sh"
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            safe_ip = ip.replace("'", "'\"'\"'")
            if duration in ("day", "1day", "24h"):
                unblock_fn = f"nexus_firewall_temp_allow_ip {direction} '{safe_ip}' 86400"
            else:
                unblock_fn = f"nexus_firewall_unblock_ip {direction} '{safe_ip}'"
            cmd = (
                f"source {INSTALL_ROOT}/lib/nexus-common.sh && nexus_load_config && "
                f"source {script} && {unblock_fn}"
            )
            proc = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=20, env=env)
            ok = proc.returncode == 0
            self._send(
                200 if ok else 500,
                json.dumps({"ok": ok, "ip": ip, "duration": duration}),
                "application/json",
            )
            return

        if path in ("/api/attack-kit/disable", "/api/attack-kit/kill"):
            ip = str(body.get("ip", "")).strip()
            vector = str(body.get("vector", "HOSTILE")).strip() or "HOSTILE"
            severity = str(body.get("severity", "high")).strip() or "high"
            reason = str(body.get("reason", "target_kill" if path.endswith("/kill") else "operator_disable")).strip()
            reason = reason or ("target_kill" if path.endswith("/kill") else "operator_disable")
            if not ip:
                self._send(400, json.dumps({"ok": False, "error": "missing ip"}), "application/json")
                return
            guard_script = INSTALL_ROOT / "lib" / "friendly-guard.py"
            if guard_script.is_file():
                import importlib.util

                spec = importlib.util.spec_from_file_location("friendly_guard_http", guard_script)
                fg_mod = importlib.util.module_from_spec(spec)
                assert spec and spec.loader
                spec.loader.exec_module(fg_mod)
                monitor = body.get("monitor") if isinstance(body.get("monitor"), dict) else None
                refuse, guard_reason = fg_mod.refuse_kill(ip, monitor=monitor)
                if refuse:
                    self._send(
                        403,
                        json.dumps({
                            "ok": False,
                            "friendly_refused": True,
                            "immutable": True,
                            "reason": guard_reason,
                            "ip": ip,
                        }),
                        "application/json",
                    )
                    return
            script = INSTALL_ROOT / "lib" / "field-attack-kit.py"
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            cmd = "kill" if path.endswith("/kill") else "disable"
            proc = subprocess.run(
                [sys.executable, str(script), cmd, ip, vector, severity],
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )
            ok = proc.returncode == 0
            try:
                payload = json.loads(proc.stdout or "{}")
            except json.JSONDecodeError:
                payload = {"ok": ok, "ip": ip, "killed": ok}
            self._send(200 if ok else 500, json.dumps(payload), "application/json")
            return

        if path == "/api/attack-kit/crush-hot":
            script = INSTALL_ROOT / "lib" / "field-attack-kit.py"
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            proc = subprocess.run(
                [sys.executable, str(script), "crush-hot"],
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
            ok = proc.returncode == 0
            try:
                payload = json.loads(proc.stdout or "{}")
            except json.JSONDecodeError:
                payload = {"ok": ok}
            self._send(200 if ok else 500, json.dumps(payload), "application/json")
            return

        if path == "/api/attack-kit/check-online":
            ip = str(body.get("ip", "")).strip()
            if not ip:
                self._send(400, json.dumps({"ok": False, "error": "missing ip"}), "application/json")
                return
            script = INSTALL_ROOT / "lib" / "field-attack-kit.py"
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            proc = subprocess.run(
                [sys.executable, str(script), "check-online", ip],
                capture_output=True,
                text=True,
                timeout=45,
                env=env,
            )
            try:
                payload = json.loads(proc.stdout or "{}")
            except json.JSONDecodeError:
                payload = {"ok": False, "ip": ip}
            self._send(200 if proc.returncode == 0 else 500, json.dumps(payload), "application/json")
            return

        if path == "/api/attack-kit/nokill":
            ip = str(body.get("ip", "")).strip()
            vector = str(body.get("vector", "HOSTILE")).strip() or "HOSTILE"
            severity = str(body.get("severity", "high")).strip() or "high"
            reason = str(body.get("reason", "operator_nokill")).strip() or "operator_nokill"
            if not ip:
                self._send(400, json.dumps({"ok": False, "error": "missing ip"}), "application/json")
                return
            script = INSTALL_ROOT / "lib" / "field-attack-kit.py"
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            proc = subprocess.run(
                [sys.executable, str(script), "nokill", ip, vector, severity, reason],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            try:
                payload = json.loads(proc.stdout or "{}")
            except json.JSONDecodeError:
                payload = {"ok": proc.returncode == 0, "ip": ip}
            self._send(200 if proc.returncode == 0 else 500, json.dumps(payload), "application/json")
            return

        if path == "/api/attack-kit/rekill":
            ip = str(body.get("ip", "")).strip()
            vector = str(body.get("vector", "HOSTILE")).strip() or "HOSTILE"
            severity = str(body.get("severity", "high")).strip() or "high"
            if not ip:
                self._send(400, json.dumps({"ok": False, "error": "missing ip"}), "application/json")
                return
            guard_script = INSTALL_ROOT / "lib" / "friendly-guard.py"
            if guard_script.is_file():
                import importlib.util

                spec = importlib.util.spec_from_file_location("friendly_guard_rekill", guard_script)
                fg_mod = importlib.util.module_from_spec(spec)
                assert spec and spec.loader
                spec.loader.exec_module(fg_mod)
                refuse, guard_reason = fg_mod.refuse_kill(ip)
                if refuse:
                    self._send(
                        403,
                        json.dumps({
                            "ok": False,
                            "friendly_refused": True,
                            "reason": guard_reason,
                            "ip": ip,
                        }),
                        "application/json",
                    )
                    return
            script = INSTALL_ROOT / "lib" / "field-attack-kit.py"
            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL_ROOT)
            env["NEXUS_STATE_DIR"] = str(STATE_DIR)
            proc = subprocess.run(
                [sys.executable, str(script), "rekill", ip, vector, severity],
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )
            try:
                payload = json.loads(proc.stdout or "{}")
            except json.JSONDecodeError:
                payload = {"ok": proc.returncode == 0, "ip": ip}
            self._send(200 if proc.returncode == 0 else 500, json.dumps(payload), "application/json")
            return

        if path == "/api/attack-kit/sync-field":
            kit = INSTALL_ROOT / "lib" / "field-attack-kit.sh"
            ok, _ = _run_nexus_bash(
                f"source {INSTALL_ROOT}/lib/nexus-settings.sh && "
                f"source {kit} && nexus_field_attack_sync_from_memory && nexus_field_attack_apply_registry",
                timeout=60,
            )
            self._send(200 if ok else 500, json.dumps({"ok": ok}), "application/json")
            return

        if path == "/api/hostile-ai/destroy":
            script = INSTALL_ROOT / "lib" / "hostile-ai-destroy.py"
            payload = _nexus_py_json(
                script,
                ["destroy", json.dumps(body, ensure_ascii=False)],
                timeout=90,
            )
            self._send(200 if payload.get("ok") else 400, json.dumps(payload), "application/json")
            return

        if path == "/api/planetary-observer/cycle":
            payload = _nexus_py_json(
                INSTALL_ROOT / "lib" / "planetary-observer.py",
                ["cycle"],
                timeout=120,
            )
            self._send(200 if payload.get("ok", True) else 500, json.dumps(payload), "application/json")
            return

        if path == "/api/firewall/revoke":
            ip = str(body.get("ip", "")).strip()
            direction = str(body.get("direction", "both")).strip().lower() or "both"
            if not ip:
                self._send(400, json.dumps({"ok": False, "error": "missing ip"}), "application/json")
                return
            ok = _run_nexus_firewall_trust("revoke", ip, direction)
            self._send(
                200 if ok else 500,
                json.dumps({"ok": ok, "ip": ip, "direction": direction}),
                "application/json",
            )
            return

        if path == "/api/paranoia/reenable":
            incident_id = str(body.get("id", "")).strip()
            if not incident_id:
                self._send(400, json.dumps({"ok": False, "error": "missing id"}), "application/json")
                return
            ok = _run_nexus_paranoia("reenable", incident_id)
            self._send(200 if ok else 404, json.dumps({"ok": ok, "id": incident_id}), "application/json")
            return

        if path == "/api/settings":
            key = str(body.get("key", "")).strip()
            val = str(body.get("value", body.get("val", ""))).strip()
            bulk = body.get("settings")
            if isinstance(bulk, dict) and bulk:
                ok_all = True
                for k, v in bulk.items():
                    if not _run_nexus_settings_set(str(k), str(v)):
                        ok_all = False
                self._send(200 if ok_all else 500, json.dumps({"ok": ok_all}), "application/json")
                return
            if not key:
                self._send(400, json.dumps({"ok": False, "error": "missing key"}), "application/json")
                return
            if val not in ("0", "1"):
                self._send(400, json.dumps({"ok": False, "error": "value must be 0 or 1"}), "application/json")
                return
            ok = _run_nexus_settings_set(key, val)
            self._send(200 if ok else 500, json.dumps({"ok": ok, "key": key, "value": val}), "application/json")
            return

        if path in ("/api/field-filesystem", "/api/filesystem-update"):
            fs_py = INSTALL_ROOT / "lib" / "field-filesystem-update.py"
            if not fs_py.is_file():
                payload = {"ok": False, "error": "field_filesystem_missing"}
            else:
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(fs_py), "dispatch"],
                        input=json.dumps(body if isinstance(body, dict) else {}),
                        capture_output=True,
                        text=True,
                        timeout=120,
                        env=env,
                    )
                    payload = json.loads(proc.stdout or "{}")
                except (subprocess.TimeoutExpired, json.JSONDecodeError):
                    payload = {"ok": False, "error": "field_filesystem_dispatch_failed"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-c2-bookmarks", "/api/ammo-bookmarks"):
            script = INSTALL_ROOT / "lib" / "field-c2-bookmark-boot.py"
            force = bool((body or {}).get("force"))
            args = ["json"] if not force else ["json", "--force"]
            if script.is_file():
                payload = _nexus_py_json(script, args, timeout=180)
            else:
                payload = {"ok": False, "error": "field_c2_bookmark_boot_missing"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-vfs", "/api/always-files"):
            payload = _field_always_files_dispatch(body if isinstance(body, dict) else {})
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-timeshift/checkpoint":
            note = str((body or {}).get("note") or "panel checkpoint")
            payload = _field_always_files_dispatch({"action": "timeshift_checkpoint", "note": note})
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/field-timeshift/rollback":
            cid = str((body or {}).get("id") or (body or {}).get("checkpoint_id") or "")
            if not cid:
                self._send(400, json.dumps({"ok": False, "error": "checkpoint_id_required"}), "application/json")
                return
            payload = _field_always_files_dispatch({
                "action": "timeshift_rollback",
                "id": cid,
                "confirm": bool((body or {}).get("confirm")),
            }, timeout=180)
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/field-timeshift", "/api/field-timeshift/list"):
            action = str((body or {}).get("action") or "timeshift_list").strip().lower().replace("-", "_")
            payload = _field_always_files_dispatch({"action": action, **(body or {})})
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/diagnostic-mode", "/api/field-diagnostic"):
            diag_py = INSTALL_ROOT / "lib" / "field-diagnostic-mode.py"
            if not diag_py.is_file():
                payload = {"ok": False, "error": "field_diagnostic_missing"}
            else:
                env = _field_stack_env()
                try:
                    proc = subprocess.run(
                        [sys.executable, str(diag_py), "dispatch"],
                        input=json.dumps(body if isinstance(body, dict) else {}),
                        capture_output=True,
                        text=True,
                        timeout=180,
                        env=env,
                    )
                    payload = json.loads(proc.stdout or "{}")
                except (subprocess.TimeoutExpired, json.JSONDecodeError):
                    payload = {"ok": False, "error": "field_diagnostic_dispatch_failed"}
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/compatibility/refresh", "/api/compatibility-layers/refresh"):
            layers = INSTALL_ROOT / "lib" / "field-compatibility-layers.py"
            deep = bool(body.get("deep") or body.get("full"))
            cmd = "full" if deep else "refresh"
            timeout = 300 if deep else 150
            payload = _nexus_py_json(layers, [cmd], timeout=timeout) if layers.is_file() else {
                "ok": False,
                "error": "compatibility_layers_missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/always-optimal/apply", "/api/g16/always-optimal/apply"):
            ao = _grok16_root() / "lib" / "field-always-optimal.py"
            skip_layers = bool(body.get("no_layers"))
            args = ["apply"] + (["--no-layers"] if skip_layers else [])
            timeout = 90 if skip_layers else 180
            payload = _nexus_py_json(ao, args, timeout=timeout) if ao.is_file() else {
                "schema": "g16-always-optimal-panel/v1",
                "ok": False,
                "error": "always_optimal_missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path in ("/api/power-sort/apply", "/api/g16/power-sort/apply", "/api/power-sort/bench"):
            ps = _grok16_root() / "lib" / "field-power-sort.py"
            if path.endswith("/bench"):
                args = ["bench"]
                timeout = 60
            else:
                skip_bench = bool(body.get("no_bench"))
                args = ["apply"] + (["--no-bench"] if skip_bench else [])
                timeout = 60 if skip_bench else 120
            payload = _nexus_py_json(ps, args, timeout=timeout) if ps.is_file() else {
                "schema": "g16-power-sort-panel/v1",
                "ok": False,
                "error": "power_sort_missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/combinatorics/run":
            layers = INSTALL_ROOT / "lib" / "field-compatibility-layers.py"
            if layers.is_file():
                deep = str(body.get("action") or "cycle").strip().lower() == "full"
                cmd = "full" if deep else "refresh"
                timeout = 300 if deep else 150
                payload = _nexus_py_json(layers, [cmd], timeout=timeout)
            else:
                action = str(body.get("action") or "cycle").strip().lower()
                studio = INSTALL_ROOT / "lib" / "field-combinatorics-studio.py"
                timeout = 300 if action == "full" else 120
                payload = _nexus_py_json(studio, ["run", action], timeout=timeout) if studio.is_file() else {
                    "ok": False,
                    "error": "combinatorics_studio_missing",
                }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/combinatorics/brain-try":
            comb_py = INSTALL_ROOT / "lib" / "field-combinatorics-comb.py"
            intent = str(body.get("intent") or "").strip() or None
            payload = _nexus_py_json(comb_py, ["try-brain", intent] if intent else ["try-brain"], timeout=45) if comb_py.is_file() else {
                "ok": False,
                "error": "field-combinatorics-comb_missing",
            }
            self._send(200, json.dumps(payload, ensure_ascii=False), "application/json")
            return

        if path == "/api/adblock/load":
            preset = str(body.get("preset", "")).strip()
            url = str(body.get("url", "")).strip()
            if not preset and not url:
                self._send(400, json.dumps({"ok": False, "error": "preset or url required"}), "application/json")
                return
            ok = _run_nexus_adblock_load(preset=preset, url=url)
            if ok and body.get("apply", True):
                _run_nexus_adblock_apply()
            self._send(200 if ok else 500, json.dumps({"ok": ok, "preset": preset, "url": url}), "application/json")
            return

        if path == "/api/adblock/toggle":
            enabled = bool(body.get("enabled", body.get("value", "0") in ("1", True, "true")))
            ok = _run_nexus_settings_set("NEXUS_ADBLOCK", "1" if enabled else "0")
            self._send(200 if ok else 500, json.dumps({"ok": ok, "enabled": enabled}), "application/json")
            return

        if path == "/api/adblock/apply":
            ok = _run_nexus_adblock_apply()
            self._send(200 if ok else 500, json.dumps({"ok": ok}), "application/json")
            return

        if path == "/api/adblock/policy":
            policy = str(body.get("policy", "annoyance")).strip().lower()
            if policy not in ("annoyance", "fair", "strict"):
                self._send(400, json.dumps({"ok": False, "error": "invalid policy"}), "application/json")
                return
            inner = _nexus_shell_prelude() + f"nexus_adblock_set_policy '{policy}'"
            ok, _ = _run_nexus_bash(inner, timeout=120)
            self._send(200 if ok else 500, json.dumps({"ok": ok, "policy": policy}), "application/json")
            return

        if path == "/api/adblock/site-policy":
            domain = str(body.get("domain", "")).strip().lower()
            policy = str(body.get("policy", "ads_required")).strip().lower()
            note = str(body.get("note", "")).strip()
            if not domain:
                self._send(400, json.dumps({"ok": False, "error": "missing domain"}), "application/json")
                return
            safe_d = domain.replace("'", "'\"'\"'")
            safe_p = policy.replace("'", "'\"'\"'")
            safe_n = note.replace("'", "'\"'\"'")
            inner = _nexus_shell_prelude() + f"nexus_adblock_site_policy '{safe_d}' '{safe_p}' '{safe_n}'"
            ok, _ = _run_nexus_bash(inner, timeout=30)
            if ok:
                _run_nexus_adblock_apply()
            self._send(200 if ok else 500, json.dumps({"ok": ok, "domain": domain, "policy": policy}), "application/json")
            return

        if path == "/api/pest/eradicate":
            ip = str(body.get("ip", "")).strip()
            pid = str(body.get("pid", body.get("process_id", "0"))).strip() or "0"
            vector = str(body.get("vector", "HARM_CANDIDATE")).strip()
            exe = str(body.get("exe", body.get("path", ""))).strip()
            if not ip and pid == "0":
                self._send(400, json.dumps({"ok": False, "error": "ip or pid required"}), "application/json")
                return
            safe_ip = ip.replace("'", "'\"'\"'")
            safe_exe = exe.replace("'", "'\"'\"'")
            inner = (
                f"source {INSTALL_ROOT}/lib/nexus-common.sh && nexus_load_config && "
                f"source {INSTALL_ROOT}/lib/firewall-sentinel.sh && "
                f"source {INSTALL_ROOT}/lib/firewall-trust.sh && "
                f"source {INSTALL_ROOT}/lib/self-access.sh && "
                f"source {INSTALL_ROOT}/lib/pest-arsenal.sh && "
                f"nexus_pest_eradicate '{safe_ip}' '{pid}' '{vector}' '{safe_exe}'"
            )
            ok, _ = _run_nexus_bash(inner, timeout=45)
            self._send(
                200 if ok else 500,
                json.dumps({"ok": ok, "ip": ip, "pid": pid, "vector": vector}),
                "application/json",
            )
            return

        self._send(404, "not found", "text/plain")


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


def main():
    global PANEL_DIR
    PANEL_DIR = PANEL_DIR.resolve()
    os.chdir(PANEL_DIR)
    threading.Thread(target=_startup_always_optimal, daemon=True, name="always-optimal-boot").start()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()