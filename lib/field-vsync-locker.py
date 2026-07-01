#!/usr/bin/env python3
"""VSYNC Locker — lock sovereign display timing; detect rogue VSYNC ops; KILL trespassers."""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import os
import random
import re
import secrets
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

MODULE = Path(__file__).resolve()
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", MODULE.parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-vsync-locker-doctrine.json"
PANEL = STATE / "field-vsync-locker-panel.json"
LOCK = STATE / "field-vsync-locker-lock.json"
LEDGER = STATE / "field-vsync-locker-kills.jsonl"
ROGUE = STATE / "field-vsync-locker-rogues.json"
POINTER_BASELINE = STATE / "field-vsync-locker-pointer-baseline.json"
INPUT_BASELINE = STATE / "field-vsync-locker-input-baseline.json"
POINTER_PANEL = STATE / "field-vsync-locker-pointers.json"
INPUT_PANEL = STATE / "field-vsync-locker-input.json"
DRIFT_STATE = STATE / "field-vsync-locker-drift.json"
SEAL = STATE / "field-vsync-locker-seal.json"
HOST_SECRET = STATE / "field-vsync-locker-host-secret"
GUARD_PID = STATE / "field-vsync-locker-guard.pid"
GUARD_STATUS = STATE / "field-vsync-locker-guard.json"

VSYNC_ENV_KEYS = frozenset({
    "__GL_SYNC_TO_VBLANK",
    "__GL_ALLOW_UNOFFICIAL_PROTOCOL",
    "vblank_mode",
    "VDPAU_VSYNC",
    "CLUTTER_VBLANK",
    "MESA_VK_WSI_PRESENT_MODE",
    "_JAVA_AWT_WM_SYNC",
})
ROGUE_NAME_RE = re.compile(
    r"(rogue|covert|agent[_-]?ops|vsync[_-]?ops|sidechannel|injector|hijack|stowaway)",
    re.I,
)
DRM_RE = re.compile(r"^/dev/dri/")
INPUT_RE = re.compile(r"^/dev/input/")
POINTER_NAME_RE = re.compile(
    r"(mouse|pointer|trackpad|touchpad|digitizer|stylus|pen|tablet|touchscreen)",
    re.I,
)
KEYBOARD_NAME_RE = re.compile(
    r"(keyboard|key\s*pad|keypad|entry\s*keyboard|typewriter)",
    re.I,
)
CONTROL_NAME_RE = re.compile(
    r"(joystick|gamepad|controller|control\s*pad|throttle|wheel|steering|"
    r"xbox|playstation|dualsense|dualshock|switch\s*pro|hid\s*game)",
    re.I,
)
SYSTEM_INPUT_SKIP_RE = re.compile(
    r"(power\s*button|video\s*bus|lid\s*switch|sleep\s*button|rfkill)",
    re.I,
)

try:
    sys.path.insert(0, str(INSTALL / "lib"))
    from hardware_wire_registry import INPUT_MIDDLEMAN, WIRE_ALLOWED  # noqa: E402
except ImportError:
    INPUT_MIDDLEMAN = frozenset({
        "xinput", "xdotool", "ydotool", "vnc", "x11vnc", "teamviewer", "anydesk",
        "remmina", "pynput", "evemu-event", "libinput-debug-events", "xev",
    })
    WIRE_ALLOWED = frozenset({"Xorg", "Xwayland", "cinnamon", "mutter", "gnome-shell"})


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append(path: Path, row: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": row.get("ts") or _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _harden_cfg() -> dict[str, Any]:
    return _doctrine().get("release_hardening") or {}


def _maintenance_allowed() -> bool:
    return os.environ.get("FIELD_VSYNC_LOCKER_MAINTENANCE") == "1"


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _ensure_host_secret() -> bytes:
    try:
        if HOST_SECRET.is_file():
            return HOST_SECRET.read_bytes()[:64]
        key = secrets.token_bytes(32)
        HOST_SECRET.parent.mkdir(parents=True, exist_ok=True)
        HOST_SECRET.write_bytes(key)
        try:
            HOST_SECRET.chmod(0o600)
        except OSError:
            pass
        return key
    except OSError:
        return secrets.token_bytes(32)


def _host_entropy_key() -> bytes:
    parts = [_ensure_host_secret()]
    env_secret = os.environ.get("FIELD_VSYNC_HOST_SECRET", "").strip()
    if env_secret:
        parts.append(env_secret.encode())
    machine_id = Path("/etc/machine-id")
    if machine_id.is_file():
        try:
            parts.append(machine_id.read_bytes())
        except OSError:
            pass
    parts.append(str(INSTALL.resolve()).encode())
    return hashlib.sha256(b"|".join(parts)).digest()


def _host_bound_rng(*, exposure: bool, tick: float) -> random.Random:
    cfg = _harden_cfg()
    if not cfg.get("host_bound_drift", True):
        return random.SystemRandom()
    blob = f"{tick:.6f}:{int(exposure)}:{secrets.token_bytes(16).hex()}".encode()
    digest = hmac.new(_host_entropy_key(), blob, hashlib.sha256).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _trusted_exe_prefixes() -> list[str]:
    cfg = _harden_cfg()
    prefixes = list(cfg.get("trusted_exe_prefixes") or [
        "/usr/", "/bin/", "/sbin/", "/lib/", "/opt/",
    ])
    prefixes.append(str(INSTALL.resolve()) + os.sep)
    return prefixes


def _read_exe(pid: int) -> str:
    try:
        return os.readlink(f"/proc/{pid}/exe")
    except OSError:
        return ""


def _exe_is_trusted(exe: str) -> bool:
    if not exe:
        return False
    if exe.startswith("(") and exe.endswith(")"):  # deleted/replaced binary still running
        return False
    for prefix in _trusted_exe_prefixes():
        if exe.startswith(prefix):
            return True
    return False


def _allowlist() -> tuple[list[str], list[str]]:
    doc = _doctrine()
    al = doc.get("allowlist") or {}
    return list(al.get("process_patterns") or []), list(al.get("cmdline_patterns") or [])


def _name_allowlist_hit(comm: str, cmdline: str) -> bool:
    proc_pats, cmd_pats = _allowlist()
    comm_l = (comm or "").lower()
    cmd_l = (cmdline or "").lower()
    for p in proc_pats:
        if p.lower() in comm_l or p.lower() in cmd_l:
            return True
    for p in cmd_pats:
        if p.lower() in cmd_l:
            return True
    if comm_l in ("python3", "python", "bash", "sh"):
        if any(x in cmd_l for x in ("hostess7", "field-", "queen", "nexus", "lib/")):
            return True
    return False


def _allowlist_verdict(comm: str, cmdline: str, *, pid: int = 0) -> tuple[bool, list[str]]:
    signals: list[str] = []
    if comm in WIRE_ALLOWED:
        return True, signals
    if not _name_allowlist_hit(comm, cmdline):
        return False, signals
    harden = _harden_cfg()
    if not harden.get("enabled", True) or not harden.get("require_trusted_exe", True):
        return True, signals
    if pid <= 1:
        return True, signals
    if _exe_is_trusted(_read_exe(pid)):
        return True, signals
    signals.append("allowlist_spoof_attempt")
    return False, signals


def _is_allowlisted(comm: str, cmdline: str, *, pid: int = 0) -> bool:
    allow, _signals = _allowlist_verdict(comm, cmdline, pid=pid)
    return allow


def _bypass_signals() -> list[str]:
    if _maintenance_allowed():
        return []
    harden = _harden_cfg()
    if not harden.get("detect_disable_bypass", True):
        return []
    signals: list[str] = []
    for marker in harden.get("disable_env_markers") or (
        "NEXUS_VSYNC_LOCKER=0",
        "FIELD_VSYNC_LOCKER_DISABLE=1",
        "FIELD_VSYNC_LOCK=0",
    ):
        key, _, val = marker.partition("=")
        if key and os.environ.get(key) == val:
            signals.append("locker_disable_bypass")
    return signals


def _canonical_seal_payload() -> dict[str, str]:
    return {
        "doctrine_sha256": _file_sha256(DOCTRINE),
        "module_sha256": _file_sha256(MODULE),
        "install_root": str(INSTALL.resolve()),
    }


def _baseline_seal_hash(device_ids: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(sorted(device_ids), ensure_ascii=False, separators=(",", ":")).encode(),
    ).hexdigest()


def _refresh_seal(*, device_ids: list[str] | None = None) -> dict[str, Any]:
    payload = _canonical_seal_payload()
    doc = {
        "schema": "field-vsync-locker-seal/v1",
        "updated": _now(),
        **payload,
        "host_secret_present": HOST_SECRET.is_file(),
        "release_safe": True,
        "statement": "Integrity seal — open source safe; host-bound drift, not obscurity",
    }
    if device_ids is not None:
        doc["baseline_seal"] = _baseline_seal_hash(device_ids)
    _save(SEAL, doc)
    return doc


def _verify_seal() -> tuple[bool, list[str]]:
    seal = _load(SEAL, {})
    if not seal:
        return True, []
    harden = _harden_cfg()
    if not harden.get("enabled", True):
        return True, []
    signals: list[str] = []
    current = _canonical_seal_payload()
    if seal.get("doctrine_sha256") and seal["doctrine_sha256"] != current["doctrine_sha256"]:
        signals.append("doctrine_tamper")
    if seal.get("module_sha256") and seal["module_sha256"] != current["module_sha256"]:
        signals.append("module_tamper")
    baseline = _load(INPUT_BASELINE, {})
    ids = list(baseline.get("device_ids") or [])
    if seal.get("baseline_seal") and ids:
        if _baseline_seal_hash(ids) != seal["baseline_seal"]:
            signals.append("baseline_tamper")
    return len(signals) == 0, signals


def _integrity_posture() -> dict[str, Any]:
    ok, seal_signals = _verify_seal()
    bypass = _bypass_signals()
    signals = list(seal_signals) + bypass
    harden = _harden_cfg()
    fail_closed = bool(
        signals
        and harden.get("fail_closed_on_tamper", True)
        and not _maintenance_allowed()
    )
    return {
        "ok": ok and not bypass,
        "release_safe": True,
        "seal": _load(SEAL, {}),
        "signals": signals,
        "fail_closed": fail_closed,
        "maintenance": _maintenance_allowed(),
        "host_bound_drift": bool(harden.get("host_bound_drift", True)),
        "statement": "Open-source hardened — predictability requires host secret, not source alone",
    }


def _hardening_rogues() -> list[dict[str, Any]]:
    posture_doc = _integrity_posture()
    rogues: list[dict[str, Any]] = []
    for sig in posture_doc.get("signals") or []:
        rogues.append({
            "kind": "integrity_violation",
            "signals": [sig],
            "rogue": True,
            "touching_vsync": True,
            "statement": "Release-safe hardening — fail closed, no workaround from source alone",
        })
    return rogues


def list_displays() -> list[dict[str, Any]]:
    displays: list[dict[str, Any]] = []
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        displays.append({
            "id": "wayland-primary",
            "backend": "wayland",
            "connected": True,
            "primary": True,
            "vsync_locked": _load(LOCK, {}).get("active", False),
        })
    try:
        proc = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        current = None
        for line in (proc.stdout or "").splitlines():
            if " connected" in line and "disconnected" not in line:
                parts = line.split()
                current = parts[0]
                res = parts[3] if len(parts) > 3 and "+" in parts[3] else ""
                displays.append({
                    "id": current,
                    "backend": "x11",
                    "connected": True,
                    "primary": "primary" in line,
                    "resolution": res,
                    "refresh_hz": _parse_refresh(res),
                    "vsync_locked": _load(LOCK, {}).get("active", False),
                })
    except (OSError, subprocess.SubprocessError):
        pass
    if not displays:
        displays.append({
            "id": "default",
            "backend": "unknown",
            "connected": True,
            "primary": True,
            "vsync_locked": _load(LOCK, {}).get("active", False),
        })
    return displays


def _parse_refresh(res_token: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\*?", res_token or "")
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def _drift_cfg() -> dict[str, Any]:
    return _doctrine().get("anti_perfect_sync") or {}


def _xrandr_outputs() -> list[dict[str, Any]]:
    """Parse connected outputs, active mode, and available refresh rates."""
    outputs: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return outputs
    current_out: dict[str, Any] | None = None
    mode_re = re.compile(r"^\s+(\d+x\d+)\s+((?:\d+(?:\.\d+)?\*?\+?\s*)+)")
    for line in (proc.stdout or "").splitlines():
        if " connected" in line and "disconnected" not in line:
            parts = line.split()
            current_out = {
                "id": parts[0],
                "primary": "primary" in line,
                "modes": {},
                "active_mode": None,
                "active_refresh_hz": None,
            }
            outputs.append(current_out)
            continue
        if current_out is None:
            continue
        m = mode_re.match(line)
        if not m:
            continue
        mode = m.group(1)
        rates: list[float] = []
        active = False
        for token in m.group(2).split():
            star = "*" in token
            plus = "+" in token
            val = token.replace("*", "").replace("+", "")
            try:
                hz = float(val)
            except ValueError:
                continue
            rates.append(hz)
            if star:
                current_out["active_mode"] = mode
                current_out["active_refresh_hz"] = hz
                active = True
        current_out["modes"][mode] = {"rates_hz": rates, "active": active}
    return outputs


def _cvt_modeline(width: int, height: int, refresh_hz: float) -> tuple[str, str] | None:
    try:
        proc = subprocess.run(
            ["cvt", str(width), str(height), f"{refresh_hz:.2f}"],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    modeline = None
    mode_name = None
    for line in (proc.stdout or "").splitlines():
        if line.startswith("Modeline"):
            modeline = line.strip()
            parts = modeline.split('"')
            if len(parts) >= 2:
                mode_name = parts[1]
            break
    if not modeline or not mode_name:
        return None
    return mode_name, modeline


def _xrandr_set_rate(output_id: str, mode: str, refresh_hz: float, *, apply: bool) -> dict[str, Any]:
    rep: dict[str, Any] = {
        "output": output_id,
        "mode": mode,
        "target_refresh_hz": round(refresh_hz, 4),
        "applied": False,
    }
    if not apply:
        rep["dry_run"] = True
        return rep
    try:
        proc = subprocess.run(
            ["xrandr", "--output", output_id, "--mode", mode, "--rate", f"{refresh_hz:.2f}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        rep["applied"] = proc.returncode == 0
        if proc.returncode != 0:
            rep["error"] = (proc.stderr or proc.stdout or "xrandr_failed")[:160]
    except (OSError, subprocess.SubprocessError) as exc:
        rep["error"] = str(exc)[:120]
    return rep


def _xrandr_add_drift_mode(
    output_id: str,
    width: int,
    height: int,
    refresh_hz: float,
    *,
    apply: bool,
) -> dict[str, Any]:
    mode_key = f"{width}x{height}"
    mode_tag = f"field-drift-{refresh_hz:.2f}".replace(".", "p")
    rep: dict[str, Any] = {
        "output": output_id,
        "mode": mode_key,
        "drift_mode_name": mode_tag,
        "target_refresh_hz": round(refresh_hz, 4),
        "applied": False,
    }
    parsed = _cvt_modeline(width, height, refresh_hz)
    if not parsed:
        rep["error"] = "cvt_unavailable"
        return rep
    mode_name, modeline = parsed
    drift_name = f"{mode_name}-field-{mode_tag}"
    rep["drift_mode_name"] = drift_name
    if not apply:
        rep["dry_run"] = True
        return rep
    try:
        tail = modeline.replace("Modeline ", "", 1).strip()
        ml = re.match(r'"([^"]+)"\s+(.+)', tail)
        if not ml:
            rep["error"] = "modeline_parse_failed"
            return rep
        subprocess.run(
            ["xrandr", "--newmode", ml.group(1), *ml.group(2).split()],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        subprocess.run(
            ["xrandr", "--addmode", output_id, ml.group(1)],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        proc = subprocess.run(
            ["xrandr", "--output", output_id, "--mode", ml.group(1)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        rep["applied"] = proc.returncode == 0
        if proc.returncode != 0:
            rep["error"] = (proc.stderr or proc.stdout or "xrandr_mode_failed")[:160]
    except (OSError, subprocess.SubprocessError) as exc:
        rep["error"] = str(exc)[:120]
    return rep


def _pick_unpredictable_rate(
    rates: list[float],
    active_hz: float | None,
    *,
    delta_min: float,
    delta_max: float,
    exposure: bool,
    rng: random.SystemRandom,
) -> float | None:
    if not rates:
        return None
    base = active_hz if active_hz is not None else rates[0]
    span = delta_max if exposure else max(abs(delta_max), abs(delta_min))
    floor = delta_min if exposure else -span
    target = base + rng.uniform(floor, span)
    candidates = sorted(rates, key=lambda hz: abs(hz - target))
    for hz in candidates:
        if active_hz is None or abs(hz - active_hz) >= 0.005:
            return hz
    if len(rates) > 1:
        alts = [hz for hz in rates if active_hz is None or abs(hz - active_hz) >= 0.005]
        if alts:
            return rng.choice(alts)
    return None


def apply_vsync_drift(*, exposure: bool = False, apply: bool = True, force: bool = False) -> dict[str, Any]:
    """Unpredictable micro-drift — stay out of perfect vblank lock; expose rogue overlays when active."""
    cfg = _drift_cfg()
    if not cfg.get("enabled", True):
        return {"ok": True, "skipped": "disabled", "schema": "field-vsync-locker-drift/v1"}
    state = _load(DRIFT_STATE, {})
    now = time.time()
    rng = _host_bound_rng(exposure=exposure, tick=now)
    if not force and not exposure and now < float(state.get("next_drift_at") or 0):
        return {
            "ok": True,
            "skipped": "not_due",
            "schema": "field-vsync-locker-drift/v1",
            "drift": state,
            "next_drift_in_sec": round(float(state.get("next_drift_at") or 0) - now, 2),
        }

    if exposure:
        phase_ms = rng.uniform(
            float(cfg.get("rogue_exposure_phase_ms_min", 6.0)),
            float(cfg.get("rogue_exposure_phase_ms_max", 18.0)),
        )
        hz_delta = rng.uniform(
            float(cfg.get("rogue_exposure_hz_min", -0.55)),
            float(cfg.get("rogue_exposure_hz_max", 0.55)),
        )
    else:
        phase_ms = rng.uniform(
            float(cfg.get("phase_jitter_ms_min", 0.35)),
            float(cfg.get("phase_jitter_ms_max", 2.6)),
        )
        hz_delta = rng.uniform(
            float(cfg.get("jitter_hz_min", -0.12)),
            float(cfg.get("jitter_hz_max", 0.12)),
        )

    outputs = _xrandr_outputs()
    x11_actions: list[dict[str, Any]] = []
    for out in outputs:
        mode = out.get("active_mode")
        if not mode or "x" not in mode:
            continue
        width_s, height_s = mode.split("x", 1)
        try:
            width, height = int(width_s), int(height_s)
        except ValueError:
            continue
        active_hz = out.get("active_refresh_hz")
        mode_info = (out.get("modes") or {}).get(mode) or {}
        rates = list(mode_info.get("rates_hz") or [])
        target_hz = (active_hz or 60.0) + hz_delta
        picked = _pick_unpredictable_rate(
            rates,
            active_hz,
            delta_min=float(cfg.get("jitter_hz_min", -0.12)),
            delta_max=float(cfg.get("jitter_hz_max", 0.12)),
            exposure=exposure,
            rng=rng,
        )
        action: dict[str, Any]
        if picked is not None:
            action = _xrandr_set_rate(out["id"], mode, picked, apply=apply)
        elif cfg.get("allow_custom_mode_drift", True):
            action = _xrandr_add_drift_mode(
                out["id"], width, height, target_hz, apply=apply,
            )
        else:
            action = {
                "output": out["id"],
                "mode": mode,
                "skipped": "no_rate_alternate",
                "target_refresh_hz": round(target_hz, 4),
            }
        action["exposure_burst"] = exposure
        x11_actions.append(action)

    drift_seed = hmac.new(
        _host_entropy_key(),
        f"drift:{now}:{exposure}:{secrets.token_bytes(8).hex()}".encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    interval = rng.uniform(
        float(cfg.get("interval_sec_min", 18)),
        float(cfg.get("interval_sec_max", 95)),
    )
    sovereign_env = {
        "FIELD_VSYNC_ANTI_PERFECT_SYNC": "1",
        "FIELD_VSYNC_DRIFT_UNPREDICTABLE": "1",
        "FIELD_VSYNC_DRIFT_MS": f"{phase_ms:.3f}",
        "FIELD_VSYNC_DRIFT_HZ": f"{hz_delta:.4f}",
        "FIELD_VSYNC_DRIFT_SEED": drift_seed,
        "FIELD_VSYNC_EXPOSURE_BURST": "1" if exposure else "0",
    }
    if apply:
        for key, val in sovereign_env.items():
            os.environ[key] = str(val)

    doc = {
        "schema": "field-vsync-locker-drift/v1",
        "updated": _now(),
        "ok": True,
        "enabled": True,
        "imperceptible": not exposure,
        "exposure_burst": exposure,
        "unpredictable_seed": drift_seed,
        "phase_offset_ms": round(phase_ms, 3),
        "refresh_delta_hz": round(hz_delta, 4),
        "next_drift_at": now + interval,
        "next_drift_in_sec": round(interval, 2),
        "perfect_sync_avoided": True,
        "statement": (
            "Rogue exposure burst — their overlay should tear visible"
            if exposure
            else "Unpredictable micro-drift — never ride perfect vblank"
        ),
        "x11_actions": x11_actions,
        "sovereign_env": sovereign_env,
        "history": (list(state.get("history") or []) + [{
            "ts": _now(),
            "phase_offset_ms": round(phase_ms, 3),
            "refresh_delta_hz": round(hz_delta, 4),
            "exposure_burst": exposure,
        }])[-24:],
    }
    if apply:
        _save(DRIFT_STATE, doc)
    return doc


def drift_vsync(*, exposure: bool = False, apply: bool = True, force: bool = False) -> dict[str, Any]:
    return apply_vsync_drift(exposure=exposure, apply=apply, force=force)


def _read_cmdline(pid: int) -> str:
    try:
        raw = (Path(f"/proc/{pid}/cmdline").read_bytes() or b"").replace(b"\x00", b" ").decode("utf-8", errors="replace")
        return raw.strip()
    except OSError:
        return ""


def _read_comm(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/comm").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _proc_fds(pid: int) -> list[str]:
    out: list[str] = []
    fd_dir = Path(f"/proc/{pid}/fd")
    if not fd_dir.is_dir():
        return out
    try:
        for link in fd_dir.iterdir():
            try:
                target = os.readlink(link)
                out.append(target)
            except OSError:
                continue
    except OSError:
        pass
    return out


PERFECT_SYNC_ENV_MARKERS = (
    "__GL_SYNC_TO_VBLANK=1",
    "vblank_mode=1",
    "CLUTTER_VBLANK=1",
    "VDPAU_VSYNC=1",
)


def _proc_env_perfect_sync_lock(pid: int) -> bool:
    for hit in _proc_env_vsync(pid):
        for marker in PERFECT_SYNC_ENV_MARKERS:
            if hit.startswith(marker):
                return True
    return False


def _proc_env_vsync(pid: int) -> list[str]:
    hits: list[str] = []
    try:
        blob = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return hits
    for chunk in blob.split(b"\x00"):
        if not chunk:
            continue
        try:
            text = chunk.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            continue
        key = text.split("=", 1)[0]
        if key in VSYNC_ENV_KEYS or "vsync" in key.lower() or "vblank" in key.lower():
            hits.append(text[:120])
    return hits


def _input_doctrine() -> dict[str, Any]:
    doc = _doctrine()
    return {
        **(doc.get("pointer") or {}),
        **(doc.get("keyboard") or {}),
        **(doc.get("controls") or {}),
        "baseline_on_lock": (doc.get("input") or {}).get("baseline_on_lock", True),
    }


def _pointer_doctrine() -> dict[str, Any]:
    return _doctrine().get("pointer") or {}


def _suspicious_inject_names() -> list[str]:
    names: list[str] = []
    for key in ("pointer", "keyboard", "controls"):
        sect = _doctrine().get(key) or {}
        names.extend(str(x).lower() for x in (sect.get("suspicious_xinput_names") or []))
    return sorted(set(names))


def _classify_kernel_surface(name: str, handlers: str, block: str) -> str | None:
    clean = name.replace("Name=", "").strip('"')
    if SYSTEM_INPUT_SKIP_RE.search(clean):
        return None
    h = handlers.lower()
    if "mouse" in h or POINTER_NAME_RE.search(clean):
        return "pointer"
    if "js" in h or CONTROL_NAME_RE.search(clean):
        return "control"
    if "consumer control" in clean.lower() or "system control" in clean.lower():
        return "control"
    if "kbd" in h or "sysrq" in h or KEYBOARD_NAME_RE.search(clean):
        return "keyboard"
    return None


def _parse_kernel_surfaces(surface: str) -> list[dict[str, Any]]:
    path = Path("/proc/bus/input/devices")
    if not path.is_file():
        return []
    blocks = path.read_text(encoding="utf-8", errors="replace").split("\n\n")
    out: list[dict[str, Any]] = []
    for block in blocks:
        if not block.strip():
            continue
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            fields[key.strip()] = val.strip()
        name = fields.get("N", "")
        handlers = fields.get("H", "")
        kind = _classify_kernel_surface(name, handlers, block)
        if kind != surface:
            continue
        dev_id = f"{kind}|{fields.get('I', '')}|{name}|{handlers}"
        out.append({
            "id": dev_id,
            "name": name.replace("Name=", "").strip('"'),
            "handlers": handlers,
            "phys": fields.get("P", ""),
            "uniq": fields.get("U", ""),
            "sysfs": fields.get("S", ""),
            "bus": fields.get("I", ""),
            "surface": kind,
            "kind": f"kernel_{kind}",
        })
    return out


def _parse_xinput_surfaces(surface: str) -> list[dict[str, Any]]:
    role_needle = {
        "pointer": "pointer",
        "keyboard": "keyboard",
        "control": "keyboard",  # xinput has no separate gamepad role — catch by name
    }.get(surface, surface)
    default_master = {"pointer": 2, "keyboard": 3}.get(surface)
    out: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(["xinput", "list"], capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.SubprocessError):
        return out
    suspicious = _suspicious_inject_names()
    for line in (proc.stdout or "").splitlines():
        line_l = line.lower()
        if role_needle not in line_l and surface != "control":
            continue
        if surface == "control" and not CONTROL_NAME_RE.search(line):
            continue
        m = re.search(r"id=(\d+)\s*\[(.+?)\]", line)
        if not m:
            continue
        dev_id = int(m.group(1))
        role = m.group(2).strip()
        label = re.sub(r"^[\s⎡⎜⎣⎤⎥⎦↳]+", "", line.split("id=")[0]).strip()
        name_l = label.lower()
        flags: list[str] = []
        is_core_xtest = "virtual core xtest" in name_l
        if "xtest" in name_l:
            flags.append("synthetic_xtest")
        if not is_core_xtest and any(s in name_l for s in suspicious):
            flags.append("suspicious_name")
        if default_master is not None and f"master {role_needle}" in role and dev_id != default_master:
            flags.append(f"extra_master_{surface}")
        if "floating" in role:
            flags.append(f"floating_{surface}")
        out.append({
            "id": f"xinput:{surface}:{dev_id}",
            "name": label,
            "xinput_id": dev_id,
            "role": role,
            "surface": surface,
            "kind": f"xinput_{surface}",
            "flags": flags,
            "foreign": False,
            "foreign_signal": None,
        })
    return out


def _baseline_ids() -> set[str]:
    unified = _load(INPUT_BASELINE, {})
    if unified.get("device_ids"):
        return set(unified["device_ids"])
    legacy = _load(POINTER_BASELINE, {})
    return set(legacy.get("pointer_ids") or [])


def _mark_foreign(rows: list[dict[str, Any]], *, foreign_signal: str) -> None:
    baseline_ids = _baseline_ids()
    cfg = _input_doctrine()
    for row in rows:
        dev_id = row["id"]
        baseline_foreign = bool(baseline_ids) and dev_id not in baseline_ids
        row["sovereign"] = dev_id in baseline_ids if baseline_ids else True
        row["foreign"] = bool(row.get("foreign")) or baseline_foreign
        if row.get("foreign") and cfg.get("detect_foreign_devices", True):
            flags = row.setdefault("flags", [])
            if foreign_signal not in flags:
                flags.append(foreign_signal)


def enumerate_input_surfaces(*, save: bool = False) -> dict[str, Any]:
    """Pointers, keyboards, controls — kernel + xinput."""
    pointers_k = _parse_kernel_surfaces("pointer")
    keyboards_k = _parse_kernel_surfaces("keyboard")
    controls_k = _parse_kernel_surfaces("control")
    pointers_x = _parse_xinput_surfaces("pointer")
    keyboards_x = _parse_xinput_surfaces("keyboard")
    controls_x = _parse_xinput_surfaces("control")
    _mark_foreign(pointers_k, foreign_signal="foreign_pointer_device")
    _mark_foreign(keyboards_k, foreign_signal="foreign_keyboard_device")
    _mark_foreign(controls_k, foreign_signal="foreign_control_device")
    _mark_foreign(pointers_x, foreign_signal="foreign_pointer_device")
    _mark_foreign(keyboards_x, foreign_signal="foreign_keyboard_device")
    _mark_foreign(controls_x, foreign_signal="foreign_control_device")
    doc = {
        "schema": "field-vsync-locker-input/v1",
        "updated": _now(),
        "baseline_active": bool(_baseline_ids()),
        "vsync_locked": _load(LOCK, {}).get("active", False),
        "pointers": {
            "kernel": pointers_k,
            "xinput": pointers_x,
            "foreign": [r for r in pointers_k if r.get("foreign")]
                + [r for r in pointers_x if r.get("foreign")],
        },
        "keyboards": {
            "kernel": keyboards_k,
            "xinput": keyboards_x,
            "foreign": [r for r in keyboards_k if r.get("foreign")]
                + [r for r in keyboards_x if r.get("foreign")],
        },
        "controls": {
            "kernel": controls_k,
            "xinput": controls_x,
            "foreign": [r for r in controls_k if r.get("foreign")]
                + [r for r in controls_x if r.get("foreign")],
        },
        "foreign_total": sum(
            len(doc_section.get("foreign") or [])
            for doc_section in ()  # placeholder filled below
        ),
    }
    doc["foreign_total"] = (
        len(doc["pointers"]["foreign"])
        + len(doc["keyboards"]["foreign"])
        + len(doc["controls"]["foreign"])
    )
    if save:
        _save(INPUT_PANEL, doc)
        _save(POINTER_PANEL, {
            "schema": "field-vsync-locker-pointers/v1",
            "updated": doc["updated"],
            "kernel": pointers_k,
            "xinput": pointers_x,
            "foreign_kernel": doc["pointers"]["foreign"],
            "keyboards": doc["keyboards"],
            "controls": doc["controls"],
            "baseline_active": doc["baseline_active"],
            "vsync_locked": doc["vsync_locked"],
        })
    return doc


def enumerate_pointers(*, save: bool = False) -> dict[str, Any]:
    doc = enumerate_input_surfaces(save=save)
    return {
        "schema": "field-vsync-locker-pointers/v1",
        "updated": doc["updated"],
        "kernel_count": len(doc["pointers"]["kernel"]),
        "xinput_count": len(doc["pointers"]["xinput"]),
        "kernel": doc["pointers"]["kernel"],
        "xinput": doc["pointers"]["xinput"],
        "keyboards": doc["keyboards"],
        "controls": doc["controls"],
        "foreign_kernel": doc["pointers"]["foreign"],
        "suspicious_xinput": [r for r in doc["pointers"]["xinput"] if r.get("foreign") or r.get("flags")],
        "baseline_active": doc["baseline_active"],
        "vsync_locked": doc["vsync_locked"],
    }


def _save_input_baseline() -> dict[str, Any]:
    surfaces = enumerate_input_surfaces()
    ids: list[str] = []
    for sect in ("pointers", "keyboards", "controls"):
        for row in (surfaces[sect]["kernel"] + surfaces[sect]["xinput"]):
            ids.append(row["id"])
    _save(INPUT_BASELINE, {
        "schema": "field-vsync-locker-input-baseline/v1",
        "updated": _now(),
        "device_ids": ids,
        "statement": "Sovereign input baseline — foreign pointer/keyboard/control = trespass",
    })
    surfaces = enumerate_input_surfaces()
    doc = {
        "schema": "field-vsync-locker-input-baseline/v1",
        "updated": _now(),
        "device_ids": ids,
        "pointers": surfaces["pointers"],
        "keyboards": surfaces["keyboards"],
        "controls": surfaces["controls"],
        "statement": "Sovereign input baseline — foreign pointer/keyboard/control = trespass",
    }
    _save(INPUT_BASELINE, doc)
    _refresh_seal(device_ids=ids)
    legacy = {
        "schema": "field-vsync-locker-pointer-baseline/v1",
        "updated": _now(),
        "pointer_ids": ids,
        "kernel": surfaces["pointers"]["kernel"],
        "xinput": surfaces["pointers"]["xinput"],
        "statement": doc["statement"],
    }
    _save(POINTER_BASELINE, legacy)
    return doc


def _save_pointer_baseline() -> dict[str, Any]:
    return _save_input_baseline()


def _kernel_event_kinds() -> dict[str, str]:
    """Map /dev/input/eventN -> pointer|keyboard|control."""
    mapping: dict[str, str] = {}
    path = Path("/proc/bus/input/devices")
    if not path.is_file():
        return mapping
    for block in path.read_text(encoding="utf-8", errors="replace").split("\n\n"):
        if not block.strip():
            continue
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            fields[key.strip()] = val.strip()
        kind = _classify_kernel_surface(fields.get("N", ""), fields.get("H", ""), block)
        if not kind:
            continue
        for handler in (fields.get("H", "") or "").split():
            if handler.startswith("event"):
                mapping[f"/dev/input/{handler}"] = kind
    return mapping


def _input_fd_kinds(fds: list[str]) -> set[str]:
    event_map = _kernel_event_kinds()
    kinds: set[str] = set()
    for fd in fds:
        kind = event_map.get(fd)
        if kind:
            kinds.add(kind)
        elif "mouse" in fd.lower():
            kinds.add("pointer")
        elif "js" in fd.lower():
            kinds.add("control")
        elif "kbd" in fd.lower():
            kinds.add("keyboard")
    return kinds


def _append_input_vsync_signals(
    signals: list[str],
    *,
    input_fds: list[str],
    middleman: bool,
    allow: bool,
    touching_vsync: bool,
) -> None:
    if not middleman or allow or not touching_vsync:
        return
    kinds = _input_fd_kinds(input_fds)
    if not kinds:
        signals.append("input_vsync_correlated")
        return
    if "pointer" in kinds:
        signals.append("pointer_vsync_correlated")
    if "keyboard" in kinds:
        signals.append("keyboard_vsync_correlated")
    if "control" in kinds:
        signals.append("control_vsync_correlated")


def _append_input_inject_signals(
    signals: list[str],
    *,
    input_fds: list[str],
    middleman: bool,
    allow: bool,
) -> None:
    if not middleman or allow or not input_fds:
        return
    kinds = _input_fd_kinds(input_fds)
    if not kinds:
        signals.append("rogue_input_injected")
        return
    if "pointer" in kinds:
        signals.append("rogue_pointer_injected")
    if "keyboard" in kinds:
        signals.append("rogue_keyboard_injected")
    if "control" in kinds:
        signals.append("rogue_control_injected")


def _is_input_middleman(comm: str, cmdline: str) -> bool:
    comm_l = comm.lower()
    cmd_l = cmdline.lower()
    for m in INPUT_MIDDLEMAN:
        ml = m.lower()
        if ml in comm_l or ml in cmd_l:
            return True
    return False


def _scan_input_holders() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return rows
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid <= 1:
            continue
        fds = _proc_fds(pid)
        input_fds = [f for f in fds if INPUT_RE.match(f)]
        if not input_fds:
            continue
        comm = _read_comm(pid)
        cmdline = _read_cmdline(pid)
        drm = [f for f in fds if DRM_RE.match(f) or "drm" in f.lower()]
        wayland = [f for f in fds if "wayland" in f.lower()]
        allow, allow_signals = _allowlist_verdict(comm, cmdline, pid=pid)
        middleman = _is_input_middleman(comm, cmdline)
        signals: list[str] = list(allow_signals)
        touching = bool(drm or wayland)
        if middleman and not allow and touching:
            signals.append("input_middleman_on_display")
        _append_input_vsync_signals(
            signals,
            input_fds=input_fds,
            middleman=middleman,
            allow=allow,
            touching_vsync=touching,
        )
        _append_input_inject_signals(
            signals,
            input_fds=input_fds,
            middleman=middleman,
            allow=allow,
        )
        rows.append({
            "pid": pid,
            "comm": comm,
            "cmdline": cmdline[:240],
            "input_fds": input_fds[:8],
            "drm_fds": drm[:4],
            "wayland_fds": wayland[:4],
            "touching_vsync": bool(drm or wayland),
            "allowlisted": allow,
            "input_middleman": middleman,
            "rogue": bool(signals),
            "signals": signals,
        })
    return rows


_INPUT_SURFACE_ROGUE_CFG = (
    ("pointers", "foreign_pointer_device", "xinput_pointer", "synthetic_pointer_active",
     "New pointer device not in sovereign baseline",
     "Injected or remote pointer on display plane"),
    ("keyboards", "foreign_keyboard_device", "xinput_keyboard", "synthetic_keyboard_active",
     "New keyboard device not in sovereign baseline",
     "Injected or remote keyboard on display plane"),
    ("controls", "foreign_control_device", "xinput_control", "synthetic_control_active",
     "New control device not in sovereign baseline",
     "Foreign gamepad/control not in sovereign baseline"),
)


def _input_surface_rogues() -> list[dict[str, Any]]:
    """Foreign pointers/keyboards/controls — not tied to a single PID yet."""
    surfaces = enumerate_input_surfaces()
    rogues: list[dict[str, Any]] = []
    seen: set[str] = set()
    middleman_active = any(r.get("input_middleman") for r in _scan_input_holders())
    for sect_key, kernel_kind, xinput_kind, synthetic_flag, kernel_stmt, xinput_stmt in _INPUT_SURFACE_ROGUE_CFG:
        sect = surfaces.get(sect_key) or {}
        for row in sect.get("foreign") or []:
            dev_id = str(row.get("id") or "")
            if not dev_id or dev_id in seen:
                continue
            seen.add(dev_id)
            kind = kernel_kind if str(row.get("kind", "")).startswith("kernel") else xinput_kind
            rogues.append({
                "kind": kind,
                "surface": sect_key.rstrip("s"),
                "id": row.get("id"),
                "name": row.get("name"),
                "role": row.get("role"),
                "signals": list(row.get("flags") or [kernel_kind]),
                "rogue": True,
                "touching_vsync": "unknown" if kind == kernel_kind else True,
                "statement": kernel_stmt if kind == kernel_kind else xinput_stmt,
            })
        rogue_xinput_flags = {
            "suspicious_name", f"extra_master_{sect_key.rstrip('s')}", f"floating_{sect_key.rstrip('s')}",
        }
        for row in sect.get("xinput") or []:
            dev_id = str(row.get("id") or "")
            if not dev_id or dev_id in seen:
                continue
            flags = list(row.get("flags") or [])
            if "synthetic_xtest" in flags and middleman_active:
                flags.append(synthetic_flag)
            has_rogue_flag = bool(rogue_xinput_flags.intersection(flags))
            if not row.get("foreign") and synthetic_flag not in flags and not has_rogue_flag:
                continue
            seen.add(dev_id)
            rogues.append({
                "kind": xinput_kind,
                "surface": sect_key.rstrip("s"),
                "id": row.get("id"),
                "name": row.get("name"),
                "role": row.get("role"),
                "signals": flags or [f"rogue_{sect_key.rstrip('s')}_injected"],
                "rogue": True,
                "touching_vsync": True,
                "statement": xinput_stmt,
            })
    return rogues


def _pointer_surface_rogues() -> list[dict[str, Any]]:
    return [r for r in _input_surface_rogues() if r.get("surface") == "pointer"]


def _proc_ips(pid: int) -> list[str]:
    ips: list[str] = []
    try:
        proc = subprocess.run(
            ["ss", "-H", "-ntp", f"pid={pid}"],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
        for line in (proc.stdout or "").splitlines():
            for token in line.split():
                if re.match(r"^\d+\.\d+\.\d+\.\d+", token):
                    ips.append(token.split(":")[0])
    except (OSError, subprocess.SubprocessError):
        pass
    return sorted(set(ips))


def _scan_drm_holders() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return rows
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid <= 1:
            continue
        fds = _proc_fds(pid)
        drm = [f for f in fds if DRM_RE.match(f) or "drm" in f.lower()]
        wayland = [f for f in fds if "wayland" in f.lower()]
        if not drm and not wayland:
            continue
        comm = _read_comm(pid)
        cmdline = _read_cmdline(pid)
        vsync_env = _proc_env_vsync(pid)
        ips = _proc_ips(pid)
        allow, allow_signals = _allowlist_verdict(comm, cmdline, pid=pid)
        signals: list[str] = list(allow_signals)
        if vsync_env and not allow:
            signals.append("vsync_env_hijack")
        if _proc_env_perfect_sync_lock(pid) and not allow:
            signals.append("perfect_sync_lock_attempt")
        if drm and vsync_env and not allow:
            signals.append("vblank_sidechannel_ops")
        external_ips = [
            ip for ip in ips
            if ip not in ("127.0.0.1", "0.0.0.0", "::1")
            and not ip.startswith(("10.", "192.168.", "172."))
            and not ip.startswith("fe80:")
        ]
        if (drm or wayland) and external_ips and not allow:
            signals.append("display_socket_plus_covert_net")
        if ROGUE_NAME_RE.search(comm) or ROGUE_NAME_RE.search(cmdline):
            signals.append("rogue_agent_name")
        input_fds = [f for f in fds if INPUT_RE.match(f)]
        middleman = _is_input_middleman(comm, cmdline)
        touching = bool(drm or wayland)
        if middleman and not allow and touching:
            signals.append("input_middleman_on_display")
        _append_input_vsync_signals(
            signals,
            input_fds=input_fds,
            middleman=middleman,
            allow=allow,
            touching_vsync=touching,
        )
        _append_input_inject_signals(
            signals,
            input_fds=input_fds,
            middleman=middleman,
            allow=allow,
        )
        # DRM/Wayland alone is normal for compositors — rogue = ops signals only
        rows.append({
            "pid": pid,
            "comm": comm,
            "cmdline": cmdline[:240],
            "drm_fds": drm[:6],
            "wayland_fds": wayland[:4],
            "input_fds": input_fds[:6],
            "touching_vsync": bool(drm or wayland),
            "input_middleman": middleman,
            "vsync_env": vsync_env[:8],
            "remote_ips": ips[:8],
            "allowlisted": allow,
            "rogue": bool(signals),
            "signals": signals,
        })
    return sorted(rows, key=lambda r: (not r.get("rogue"), r.get("pid", 0)))


def lock_vsync(*, apply: bool = True) -> dict[str, Any]:
    """Sovereign VSYNC lock — only field stack may own vblank cadence."""
    doc = _doctrine()
    sovereign = (doc.get("allowlist") or {}).get("sovereign_env") or {}
    lock_doc = {
        "schema": "field-vsync-locker-lock/v1",
        "active": True,
        "updated": _now(),
        "sovereign_env": sovereign,
        "statement": "VSYNC/vblank owned by field stack — rogue ops forbidden",
        "trespass": "kill_immediate",
    }
    baseline = {}
    drift: dict[str, Any] = {}
    if apply:
        _save(LOCK, lock_doc)
        for k, v in sovereign.items():
            os.environ[k] = str(v)
        input_cfg = _doctrine().get("input") or {}
        if input_cfg.get("baseline_on_lock", _pointer_doctrine().get("baseline_on_lock", True)):
            baseline = _save_input_baseline()
        else:
            ids = list(_load(INPUT_BASELINE, {}).get("device_ids") or [])
            _refresh_seal(device_ids=ids or None)
        _ensure_host_secret()
        drift = apply_vsync_drift(exposure=False, apply=True, force=True)
    else:
        drift = apply_vsync_drift(exposure=False, apply=False, force=True)
    integrity = _integrity_posture()
    return {
        "ok": True,
        "locked": True,
        "apply": apply,
        "lock": lock_doc,
        "input_baseline": baseline,
        "pointer_baseline": baseline,
        "drift": drift,
        "integrity": integrity,
        "release_safe": True,
    }


def _kill_pid(pid: int, *, reason: str, row: dict[str, Any]) -> dict[str, Any]:
    rep: dict[str, Any] = {"pid": pid, "reason": reason, "killed": False}
    try:
        os.kill(pid, signal.SIGKILL)
        rep["killed"] = True
        rep["signal"] = "SIGKILL"
    except ProcessLookupError:
        rep["killed"] = True
        rep["note"] = "already_dead"
    except PermissionError as exc:
        rep["error"] = str(exc)[:120]
        try:
            subprocess.run(["sudo", "kill", "-9", str(pid)], capture_output=True, timeout=8, check=False)
            rep["killed"] = True
            rep["signal"] = "SIGKILL(sudo)"
        except (OSError, subprocess.SubprocessError) as exc2:
            rep["error"] = str(exc2)[:120]
    _append(LEDGER, {"event": "vsync_trespass_kill", **rep, "row": row})
    return rep


def _kill_network_trespass(ips: list[str], *, reason: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    attack_py = INSTALL / "lib" / "field-attack-kit.py"
    if not attack_py.is_file():
        return out
    for ip in ips:
        if ip in ("127.0.0.1", "0.0.0.0", "::1") or ip.startswith("192.168.") or ip.startswith("10."):
            continue
        try:
            proc = subprocess.run(
                [sys.executable, str(attack_py), "kill", ip, "VSYNC_TRESPASS", "critical", reason],
                capture_output=True,
                text=True,
                timeout=45,
                cwd=str(INSTALL),
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            doc = json.loads(proc.stdout or "{}")
            out.append({"ip": ip, **doc})
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            out.append({"ip": ip, "ok": False, "error": str(exc)[:120]})
    return out


def kill_rogue(row: dict[str, Any], *, reason: str | None = None) -> dict[str, Any]:
    """KILL trespasser — no warnings."""
    pid = int(row.get("pid") or 0)
    surface_kinds = {
        "foreign_pointer_device", "xinput_pointer",
        "foreign_keyboard_device", "xinput_keyboard",
        "foreign_control_device", "xinput_control",
    }
    if pid <= 1:
        if row.get("kind") in surface_kinds:
            _append(LEDGER, {
                "event": "vsync_input_trespass",
                "kind": row.get("kind"),
                "surface": row.get("surface"),
                "id": row.get("id"),
                "name": row.get("name"),
                "signals": row.get("signals"),
                "action": "flagged_kill_middleman_next_patrol",
            })
            trespass_reason = reason or f"{row.get('surface', 'input')}_vsync_trespass"
            for holder in _scan_input_holders():
                if holder.get("rogue") and holder.get("input_middleman"):
                    return kill_rogue(holder, reason=trespass_reason)
            return {
                "ok": True,
                "schema": "field-vsync-locker-kill/v1",
                "input_surface_only": True,
                "flagged": row,
                "statement": "Foreign input surface detected — kill middleman on next correlated PID",
            }
        return {"ok": False, "error": "invalid_pid"}
    why = reason or f"vsync_trespass:{','.join(row.get('signals') or ['rogue'])}"
    local = _kill_pid(pid, reason=why, row=row)
    net = _kill_network_trespass(list(row.get("remote_ips") or []), reason=why)
    ok = bool(local.get("killed"))
    return {
        "ok": ok,
        "schema": "field-vsync-locker-kill/v1",
        "pid": pid,
        "comm": row.get("comm"),
        "reason": why,
        "trespass": True,
        "shoot_to_kill": True,
        "local": local,
        "network_kills": net,
        "statement": "No trespassing on VSYNC — KILL enforced",
    }


def detect_rogues() -> dict[str, Any]:
    holders = _scan_drm_holders()
    input_holders = _scan_input_holders()
    input_surfaces = _input_surface_rogues()
    input_doc = enumerate_input_surfaces(save=True)
    proc_rogues = [r for r in holders if r.get("rogue")]
    seen_pids = {int(r.get("pid") or 0) for r in proc_rogues}
    for r in input_holders:
        if r.get("rogue") and int(r.get("pid") or 0) not in seen_pids:
            proc_rogues.append(r)
            seen_pids.add(int(r.get("pid") or 0))
    hardening = _hardening_rogues()
    all_rogues = proc_rogues + input_surfaces + hardening
    vsync_signal_re = re.compile(
        r"(pointer|keyboard|control|input)_vsync|synthetic_(pointer|keyboard|control)_active"
    )
    touching = [
        r for r in all_rogues
        if r.get("touching_vsync") is True
        or vsync_signal_re.search(",".join(r.get("signals") or []))
    ]
    doc = {
        "schema": "field-vsync-locker-rogues/v1",
        "updated": _now(),
        "displays": list_displays(),
        "input": input_doc,
        "pointers": enumerate_pointers(),
        "holders": len(holders),
        "input_holders": len(input_holders),
        "rogue_count": len(all_rogues),
        "proc_rogue_count": len(proc_rogues),
        "input_surface_rogue_count": len(input_surfaces),
        "pointer_rogue_count": len([r for r in input_surfaces if r.get("surface") == "pointer"]),
        "keyboard_rogue_count": len([r for r in input_surfaces if r.get("surface") == "keyboard"]),
        "control_rogue_count": len([r for r in input_surfaces if r.get("surface") == "control"]),
        "touching_vsync_count": len(touching),
        "rogues": all_rogues,
        "proc_rogues": proc_rogues,
        "input_surface_rogues": input_surfaces,
        "pointer_rogues": [r for r in input_surfaces if r.get("surface") == "pointer"],
        "locked": _load(LOCK, {}).get("active", False),
        "integrity": _integrity_posture(),
        "hardening_rogue_count": len(hardening),
        "release_safe": True,
        "statement": "We know when they bring their own pointer, keyboard, or control and touch our VSYNC",
    }
    _save(ROGUE, doc)
    return doc


def patrol(*, auto_kill: bool | None = None) -> dict[str, Any]:
    """Scan displays one pass — KILL every rogue VSYNC operator."""
    doc = _doctrine()
    patrol_cfg = doc.get("patrol") or {}
    if auto_kill is None:
        auto_kill = bool(patrol_cfg.get("auto_kill", True))
    integrity = _integrity_posture()
    if patrol_cfg.get("auto_lock", True):
        lock_vsync(apply=True)
    scan = detect_rogues()
    drift_cfg = _drift_cfg()
    exposure = bool(scan.get("rogue_count", 0) > 0 and drift_cfg.get("expose_on_rogue_detect", True))
    drift = apply_vsync_drift(exposure=exposure, apply=True, force=exposure)
    kills: list[dict[str, Any]] = []
    for row in scan.get("rogues") or []:
        if auto_kill and row.get("kind") != "integrity_violation":
            kills.append(kill_rogue(row))
    panel = {
        "schema": "field-vsync-locker-panel/v1",
        "updated": _now(),
        "ok": scan.get("rogue_count", 0) == 0 or all(k.get("ok") for k in kills),
        "motto": doc.get("motto"),
        "policy": doc.get("policy"),
        "displays": scan.get("displays"),
        "rogue_count": scan.get("rogue_count"),
        "kills": kills,
        "drift": drift,
        "anti_perfect_sync": drift.get("perfect_sync_avoided", False),
        "rogue_exposure_burst": drift.get("exposure_burst", False),
        "integrity": scan.get("integrity") or integrity,
        "release_safe": True,
        "locked": _load(LOCK, {}).get("active", False),
        "trespass_response": "kill_immediate",
    }
    _save(PANEL, panel)
    return panel


def posture() -> dict[str, Any]:
    doc = _doctrine()
    return {
        "schema": "field-vsync-locker/v1",
        "ok": True,
        "updated": _now(),
        "motto": doc.get("motto"),
        "policy": doc.get("policy"),
        "displays": list_displays(),
        "locked": _load(LOCK, {}).get("active", False),
        "anti_perfect_sync": _load(DRIFT_STATE, {}),
        "last_patrol": _load(PANEL, {}),
        "last_rogues": _load(ROGUE, {}),
        "api": doc.get("api"),
        "input": _load(INPUT_PANEL, {}),
        "pointers": _load(POINTER_PANEL, {}),
        "input_baseline": _load(INPUT_BASELINE, {}),
        "pointer_baseline": _load(POINTER_BASELINE, {}),
        "integrity": _integrity_posture(),
        "release_safe": True,
        "guard": guard_status(),
        "routes": {
            "panel": "/api/vsync-locker",
            "patrol": "/api/vsync-locker/patrol",
            "lock": "/api/vsync-locker/lock",
            "detect": "/api/vsync-locker/detect",
            "input": "/api/vsync-locker/input",
            "pointers": "/api/vsync-locker/pointers",
            "baseline": "/api/vsync-locker/baseline",
            "drift": "/api/vsync-locker/drift",
            "harden": "/api/vsync-locker/harden",
            "guard": "/api/vsync-locker/guard",
            "launch": "/api/vsync-locker/launch",
        },
    }


def _pid_alive(pid: int) -> bool:
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_guard_pid() -> int:
    try:
        return int((GUARD_PID.read_text(encoding="utf-8").strip() or "0"))
    except (OSError, ValueError):
        return 0


def _write_guard_pid(pid: int) -> None:
    GUARD_PID.parent.mkdir(parents=True, exist_ok=True)
    GUARD_PID.write_text(f"{pid}\n", encoding="utf-8")


def _clear_guard_pid() -> None:
    try:
        GUARD_PID.unlink(missing_ok=True)
    except OSError:
        pass


def _guard_cfg() -> dict[str, Any]:
    return _doctrine().get("guard") or {}


def guard_status() -> dict[str, Any]:
    pid = _read_guard_pid()
    running = _pid_alive(pid)
    doc = _load(GUARD_STATUS, {})
    return {
        "schema": "field-vsync-locker-guard/v1",
        "ok": True,
        "updated": _now(),
        "running": running,
        "pid": pid if running else None,
        "last_cycle": doc,
        "locked": _load(LOCK, {}).get("active", False),
        "statement": "Background VSYNC protector — double-click once, stays on patrol",
    }


def stop_guard(*, force: bool = False) -> dict[str, Any]:
    pid = _read_guard_pid()
    if not _pid_alive(pid):
        _clear_guard_pid()
        return {"ok": True, "stopped": True, "note": "not_running"}
    try:
        os.kill(pid, signal.SIGTERM if not force else signal.SIGKILL)
    except OSError as exc:
        return {"ok": False, "error": str(exc)[:120]}
    _clear_guard_pid()
    return {"ok": True, "stopped": True, "pid": pid, "signal": "SIGKILL" if force else "SIGTERM"}


def guard_vsync(*, quiet: bool = False) -> dict[str, Any]:
    """Background protector — lock, harden, patrol loop until stopped."""
    cfg = _guard_cfg()
    if not cfg.get("enabled", True):
        return {"ok": False, "error": "guard_disabled"}
    existing = _read_guard_pid()
    if _pid_alive(existing) and existing != os.getpid():
        rep = guard_status()
        rep["already_running"] = True
        return rep

    _write_guard_pid(os.getpid())
    rep: dict[str, Any] = {
        "schema": "field-vsync-locker-guard/v1",
        "ok": True,
        "started": _now(),
        "pid": os.getpid(),
        "background": True,
        "statement": "VSYNC locker guard active — patrol, drift, KILL trespassers",
    }
    try:
        harden_posture()
        lock_vsync(apply=True)
        patrol_cfg = _doctrine().get("patrol") or {}
        base_interval = float(cfg.get("interval_sec") or patrol_cfg.get("default_interval_sec") or 30)
        jitter = float(cfg.get("interval_jitter_sec") or 8)
        cycles = 0
        while True:
            cycles += 1
            cycle = patrol(auto_kill=bool(patrol_cfg.get("auto_kill", True)))
            cycle_doc = {
                "schema": "field-vsync-locker-guard-cycle/v1",
                "updated": _now(),
                "cycle": cycles,
                "ok": cycle.get("ok", True),
                "rogue_count": cycle.get("rogue_count", 0),
                "locked": cycle.get("locked", False),
                "pid": os.getpid(),
            }
            _save(GUARD_STATUS, cycle_doc)
            if not quiet:
                print(json.dumps(cycle_doc, ensure_ascii=False), flush=True)
            rng = _host_bound_rng(exposure=False, tick=time.time())
            sleep_sec = max(12.0, base_interval + rng.uniform(-jitter, jitter))
            time.sleep(sleep_sec)
    except KeyboardInterrupt:
        rep["stopped"] = "interrupt"
    finally:
        if _read_guard_pid() == os.getpid():
            _clear_guard_pid()
    return rep


def launch_guard_background() -> dict[str, Any]:
    """Double-click entry — start guard if not already running."""
    if _pid_alive(_read_guard_pid()):
        return {**guard_status(), "already_running": True, "launched": False}
    launch_sh = INSTALL / "lib" / "field-vsync-locker-launch.sh"
    if not launch_sh.is_file():
        return {"ok": False, "error": "launch_script_missing"}
    try:
        proc = subprocess.run(
            ["bash", str(launch_sh)],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(INSTALL),
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            check=False,
        )
        time.sleep(0.6)
        status = guard_status()
        return {
            "ok": status.get("running", False) or proc.returncode == 0,
            "launched": status.get("running", False),
            "already_running": False,
            "guard": status,
            "launch_rc": proc.returncode,
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": str(exc)[:120]}


def install_desktop_shortcut() -> dict[str, Any]:
    """Install double-click desktop launcher for background guard."""
    cfg = _guard_cfg()
    launch_sh = INSTALL / "lib" / "field-vsync-locker-launch.sh"
    if not launch_sh.is_file():
        return {"ok": False, "error": "launch_script_missing"}
    name = str(cfg.get("desktop_name") or "VSYNC Locker")
    comment = str(cfg.get("desktop_comment") or "Background display timing protector")
    desktop_name = str(cfg.get("desktop_file") or "field-vsync-locker.desktop")
    exec_line = f"bash \"{launch_sh}\""
    body = (
        "[Desktop Entry]\n"
        f"Version=1.0\n"
        "Type=Application\n"
        f"Name={name}\n"
        f"Comment={comment}\n"
        f"Exec={exec_line}\n"
        f"Path={INSTALL}\n"
        "Terminal=false\n"
        "Categories=Security;System;\n"
        "Keywords=vsync;display;locker;field;hostess7;\n"
        "StartupNotify=false\n"
        "X-GNOME-Autostart-enabled=false\n"
    )
    targets: list[Path] = []
    home = Path.home()
    for sub in ("Desktop", ".local/share/applications"):
        dest = home / sub / desktop_name
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body, encoding="utf-8")
            dest.chmod(0o755)
            targets.append(dest)
        except OSError:
            continue
    return {
        "ok": bool(targets),
        "schema": "field-vsync-locker-install-desktop/v1",
        "targets": [str(p) for p in targets],
        "exec": exec_line,
        "statement": "Double-click once — guard stays in background",
    }


def harden_posture() -> dict[str, Any]:
    seal = _refresh_seal(
        device_ids=list(_load(INPUT_BASELINE, {}).get("device_ids") or []) or None,
    )
    _ensure_host_secret()
    return {
        "schema": "field-vsync-locker-harden/v1",
        "ok": True,
        "updated": _now(),
        "integrity": _integrity_posture(),
        "seal": seal,
        "release_safe": True,
        "statement": "Seals refreshed — safe to ship source; host secret stays local",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "lock":
        print(json.dumps(lock_vsync(apply="--dry" not in sys.argv), ensure_ascii=False, indent=2))
        return 0
    if cmd == "detect":
        print(json.dumps(detect_rogues(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "pointers":
        print(json.dumps(enumerate_pointers(save=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "input":
        print(json.dumps(enumerate_input_surfaces(save=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "baseline":
        print(json.dumps(_save_pointer_baseline(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "harden":
        print(json.dumps(harden_posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "drift":
        exposure = "--expose" in sys.argv
        force = "--force" in sys.argv or exposure
        dry = "--dry" in sys.argv
        print(json.dumps(
            apply_vsync_drift(exposure=exposure, apply=not dry, force=force),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd == "patrol":
        auto = "--no-kill" not in sys.argv
        rep = patrol(auto_kill=auto)
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1
    if cmd == "guard":
        quiet = "--quiet" in sys.argv
        if "--status" in sys.argv:
            print(json.dumps(guard_status(), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(guard_vsync(quiet=quiet), ensure_ascii=False, indent=2))
        return 0
    if cmd == "launch":
        print(json.dumps(launch_guard_background(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "stop":
        force = "--force" in sys.argv
        print(json.dumps(stop_guard(force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd == "install-desktop":
        print(json.dumps(install_desktop_shortcut(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "kill" and len(sys.argv) > 2:
        pid = int(sys.argv[2])
        holders = _scan_drm_holders()
        row = next((r for r in holders if int(r.get("pid") or 0) == pid), {"pid": pid, "signals": ["manual_kill"]})
        rep = kill_rogue(row, reason=sys.argv[3] if len(sys.argv) > 3 else None)
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1
    print(json.dumps({
        "error": "usage",
        "hint": "field-vsync-locker.py [json|launch|guard|stop|install-desktop|lock|detect|drift|harden|patrol|kill PID]",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())