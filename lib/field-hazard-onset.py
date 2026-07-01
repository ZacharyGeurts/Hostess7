#!/usr/bin/env pythong
"""Proactive hazard onset — microsecond IQ guard + cease traffic at the point.

Detects hazardous signal rise at sample onset, then shoot (zero from point) or
buffer_down (attenuate from point). Ceases wire/RF traffic at the same index.
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
CFG_PATH = INSTALL / "data" / "field-hazard-onset.json"
PANEL_CACHE = STATE / "field-hazard-onset-panel.json"
CEASE_LEDGER = STATE / "field-hazard-cease.jsonl"
TRAFFIC_CEASED = STATE / "field-traffic-ceased.json"
CONNECTION_CEASE = STATE / "connection-cease-at-point.json"
HARM_PORTS = frozenset({
    "4444", "5555", "1337", "31337", "6666", "6667", "9001", "9050", "1080", "3128",
    "4443", "8080", "8443", "3004", "3005", "6006", "6606", "8808",
})


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



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with CEASE_LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def load_config() -> dict[str, Any]:
    return _load_json(CFG_PATH, {"enabled": True, "proactive": True})


def _sample_to_us(sample_idx: int, fs: float) -> float:
    return round(float(sample_idx) * 1_000_000.0 / max(fs, 1.0), 3)


def _energy_trace(iq: np.ndarray, window: int) -> np.ndarray:
    power = (iq.real.astype(np.float64) ** 2 + iq.imag.astype(np.float64) ** 2)
    if window <= 1:
        return power
    kernel = np.ones(window, dtype=np.float64) / float(window)
    return np.convolve(power, kernel, mode="same")


def _log_derivative(energy: np.ndarray, window: int) -> np.ndarray:
    n = len(energy)
    out = np.zeros(n, dtype=np.float64)
    w = max(1, window)
    log_e = np.log10(energy + 1e-18)
    for i in range(w, n):
        out[i] = (log_e[i] - log_e[i - w]) * 20.0
    return out


def detect_onset(
    iq: np.ndarray,
    *,
    fs: float = 2_400_000.0,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Find first hazardous energy rise — microsecond resolution at IQ rate."""
    cfg = cfg or load_config()
    det = cfg.get("detection") or {}
    n = len(iq)
    if n < 32:
        return {
            "detected": False,
            "reason": "too_short",
            "onset_sample": 0,
            "onset_us": 0.0,
            "fs_hz": fs,
        }

    win = int(det.get("energy_window_samples") or 8)
    deriv_w = int(det.get("derivative_window_samples") or 4)
    deriv_thr = float(det.get("derivative_threshold_db") or 6.0)
    spike_ratio = float(det.get("spike_ratio_min") or 4.5)
    impulsive_crest = float(det.get("impulsive_crest_min") or 12.0)
    baseline_frac = float(det.get("baseline_fraction") or 0.1)
    min_sample = int(det.get("min_onset_sample") or 16)

    energy = _energy_trace(iq, win)
    deriv = _log_derivative(energy, deriv_w)
    baseline_n = max(8, int(n * baseline_frac))
    baseline = float(np.median(energy[:baseline_n])) or 1e-12

    onset_idx = -1
    peak_deriv = 0.0
    for i in range(max(min_sample, deriv_w), n - win):
        e = float(energy[i])
        d = float(deriv[i])
        if d < deriv_thr or e < baseline * spike_ratio:
            continue
        local = energy[max(0, i - win) : i + win + 1]
        crest = float(np.max(local)) / max(float(np.mean(local)), 1e-12)
        if crest < impulsive_crest * 0.35 and d < deriv_thr * 1.8:
            continue
        onset_idx = i
        peak_deriv = d
        break

    if onset_idx < 0:
        return {
            "detected": False,
            "reason": "clean",
            "onset_sample": 0,
            "onset_us": 0.0,
            "fs_hz": fs,
            "baseline_energy": round(baseline, 12),
        }

    return {
        "detected": True,
        "onset_sample": int(onset_idx),
        "onset_us": _sample_to_us(onset_idx, fs),
        "fs_hz": fs,
        "derivative_db": round(peak_deriv, 3),
        "energy_at_onset": round(float(energy[onset_idx]), 12),
        "baseline_energy": round(baseline, 12),
        "spike_ratio": round(float(energy[onset_idx]) / baseline, 3),
    }


def classify_hazard(
    iq: np.ndarray,
    onset: dict[str, Any],
    *,
    read: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
    fs: float = 2_400_000.0,
) -> dict[str, Any]:
    """Classify onset severity and hazard kind for shoot vs buffer_down."""
    cfg = cfg or load_config()
    if not onset.get("detected"):
        return {
            "hazard": False,
            "kind": "none",
            "severity": 0.0,
            "action": "pass",
        }

    idx = int(onset["onset_sample"])
    n = len(iq)
    seg = iq[max(0, idx - 8) : min(n, idx + 64)]
    spec = np.abs(np.fft.fft(seg))
    spec /= max(float(np.max(spec)), 1e-12)
    flatness = float(np.exp(np.mean(np.log(spec + 1e-12))) / max(np.mean(spec), 1e-12))

    deriv_db = float(onset.get("derivative_db") or 0.0)
    spike = float(onset.get("spike_ratio") or 1.0)
    severity = min(1.0, (deriv_db / 24.0) * 0.45 + (spike / 20.0) * 0.35 + flatness * 0.2)

    kind = "moderate_rise"
    if deriv_db >= 18.0 and spike >= 12.0:
        kind = "burst_spike"
    elif flatness > 0.55 and spike >= 8.0:
        kind = "wideband_surge"
    elif deriv_db >= 12.0 and spike >= 6.0:
        kind = "narrow_surge"
    elif flatness > 0.4 and deriv_db >= 10.0:
        kind = "impulse_train"

    mesh = (read or {}).get("mesh") or {}
    motion = float((mesh.get("physics") or {}).get("motion_index") or 0.0)
    if motion > 0.85 and spike >= 10.0:
        kind = "hostile_injection"
        severity = min(1.0, severity + 0.15)

    resp = cfg.get("response") or {}
    cls = cfg.get("classification") or {}
    shoot_kinds = frozenset(cls.get("shoot_kinds") or [])
    buffer_kinds = frozenset(cls.get("buffer_kinds") or [])

    shoot_min = float(resp.get("shoot_severity_min") or 0.72)
    buffer_min = float(resp.get("buffer_severity_min") or 0.38)
    default_action = str(resp.get("default_action") or "auto")

    if kind in shoot_kinds or severity >= shoot_min:
        action = "shoot"
    elif kind in buffer_kinds or severity >= buffer_min:
        action = "buffer_down"
    elif default_action == "shoot":
        action = "shoot"
    elif default_action == "buffer_down":
        action = "buffer_down"
    else:
        action = "pass"

    return {
        "hazard": action != "pass",
        "kind": kind,
        "severity": round(severity, 4),
        "spectral_flatness": round(flatness, 4),
        "action": action,
    }


def guard_iq(
    iq: np.ndarray,
    onset_sample: int,
    action: str,
    *,
    cfg: dict[str, Any] | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Shoot (zero from onset) or buffer_down (attenuate ramp from onset)."""
    cfg = cfg or load_config()
    resp = cfg.get("response") or {}
    out = iq.astype(np.complex64, copy=True)
    n = len(out)
    idx = max(0, min(int(onset_sample), n))

    if action == "pass" or idx >= n:
        return out, {"action": "pass", "samples_affected": 0, "onset_sample": idx}

    if action == "shoot":
        out[idx:] = 0.0 + 0.0j
        return out, {
            "action": "shoot",
            "onset_sample": idx,
            "samples_zeroed": n - idx,
            "policy": "cease_rf_at_point",
        }

    atten_db = float(resp.get("buffer_atten_db") or 24.0)
    floor = float(resp.get("buffer_floor_linear") or 0.02)
    ramp = int(resp.get("buffer_ramp_samples") or 96)
    gains = np.ones(n, dtype=np.float64)
    for i in range(idx, n):
        t = min(1.0, float(i - idx) / max(ramp, 1))
        lin = max(floor, 10.0 ** (-atten_db * t / 20.0))
        gains[i] = lin
    out *= gains.astype(np.float32)
    return out, {
        "action": "buffer_down",
        "onset_sample": idx,
        "samples_attenuated": n - idx,
        "atten_db": atten_db,
        "floor_linear": floor,
        "policy": "buffer_down_at_point",
    }


def cease_traffic_at_point(
    onset: dict[str, Any],
    hazard: dict[str, Any],
    *,
    read: dict[str, Any] | None = None,
    station_id: str = "",
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cease wire traffic at the same onset point — ledger + connection manifest."""
    cfg = cfg or load_config()
    tc = cfg.get("traffic_cease") or {}
    if not hazard.get("hazard"):
        return {"ceased": False, "reason": "no_hazard"}

    freq_mhz = (read or {}).get("freq_mhz")
    cease_doc = {
        "schema": "field-traffic-ceased/v1",
        "ceased_at": _now(),
        "ceased": True,
        "onset_sample": onset.get("onset_sample"),
        "onset_us": onset.get("onset_us"),
        "fs_hz": onset.get("fs_hz"),
        "hazard_kind": hazard.get("kind"),
        "severity": hazard.get("severity"),
        "guard_action": hazard.get("action"),
        "station_id": station_id,
        "freq_mhz": freq_mhz,
        "policy": "cease_at_onset_point — shoot or buffer_down already applied to IQ",
    }

    if tc.get("write_panel", True):
        _save_json(PANEL_CACHE, {
            "schema": "field-hazard-onset-panel/v1",
            "updated_at": _now(),
            "proactive": bool(cfg.get("proactive")),
            "last": cease_doc,
            "status": "ceased" if hazard.get("action") == "shoot" else "buffered",
        })

    if tc.get("write_ledger", True):
        _append_ledger(cease_doc)

    _save_json(TRAFFIC_CEASED, cease_doc)

    conn_rows: list[dict[str, Any]] = []
    if tc.get("mark_connections", True):
        intent_path = STATE / "connection-intent.json"
        intent = _load_json(intent_path, {})
        for row in intent.get("connections") or []:
            verdict = str(row.get("verdict") or "")
            if verdict in ("USER_OK", "EPHEMERAL"):
                continue
            rip = str(row.get("remote_ip") or "").strip()
            rport = str(row.get("remote_port") or "").strip()
            if not rip:
                continue
            harm = verdict in ("HARM_CANDIDATE", "SUSPICIOUS") or rport in HARM_PORTS
            if harm or hazard.get("severity", 0) >= 0.5:
                conn_rows.append({
                    "remote_ip": rip,
                    "remote_port": rport,
                    "process": row.get("process"),
                    "verdict": verdict,
                    "cease_reason": "hazard_onset",
                    "onset_us": onset.get("onset_us"),
                })

    conn_doc = {
        "schema": "connection-cease-at-point/v1",
        "written_at": _now(),
        "onset_us": onset.get("onset_us"),
        "connections": conn_rows,
        "block_harm_ports": bool(tc.get("block_harm_ports")),
    }
    _save_json(CONNECTION_CEASE, conn_doc)

    lethal_escalate: dict[str, Any] = {}
    lethal_py = INSTALL / "lib" / "lethal-enforcement.py"
    if lethal_py.is_file() and hazard.get("action") == "shoot":
        try:
            import subprocess

            proc = subprocess.run(
                [
                    "pythong", str(lethal_py), "execute",
                    json.dumps({
                        "remote_ip": conn_rows[0].get("remote_ip") if conn_rows else "",
                        "hell_chosen": True,
                        "verdict": "HARM_CANDIDATE",
                        "kill_eligible": True,
                        "hazard_onset_us": onset.get("onset_us"),
                    }),
                ],
                env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if proc.stdout.strip():
                lethal_escalate = json.loads(proc.stdout)
        except Exception:
            pass

    return {
        "ceased": True,
        "onset_us": onset.get("onset_us"),
        "connections_marked": len(conn_rows),
        "panel": str(PANEL_CACHE),
        "traffic_ceased": str(TRAFFIC_CEASED),
        "lethal_escalation": lethal_escalate or None,
    }


def guard_capture(
    iq: np.ndarray,
    read: dict[str, Any] | None = None,
    cfg_band: dict[str, Any] | None = None,
    *,
    fs: float = 2_400_000.0,
    station_id: str = "",
    force: bool = False,
) -> dict[str, Any]:
    """Full proactive pipeline: detect → classify → guard IQ → cease traffic."""
    cfg = load_config()
    if not cfg.get("enabled") and not force:
        return {
            "schema": "field-hazard-onset/v1",
            "enabled": False,
            "iq": iq,
            "hazard": False,
            "action": "pass",
        }

    onset = detect_onset(iq, fs=fs, cfg=cfg)
    hazard = classify_hazard(iq, onset, read=read, cfg=cfg, fs=fs)
    action = str(hazard.get("action") or "pass")
    iq_out, guard_meta = guard_iq(iq, int(onset.get("onset_sample") or 0), action, cfg=cfg)

    cease: dict[str, Any] = {"ceased": False}
    if hazard.get("hazard") and (cfg.get("response") or {}).get("cease_wire_traffic", True):
        cease = cease_traffic_at_point(onset, hazard, read=read, station_id=station_id, cfg=cfg)

    return {
        "schema": "field-hazard-onset/v1",
        "enabled": True,
        "proactive": bool(cfg.get("proactive")),
        "onset": onset,
        "hazard": hazard,
        "guard": guard_meta,
        "cease": cease,
        "iq": iq_out,
        "action": action,
        "ceased_traffic": bool(cease.get("ceased")),
    }


def panel_status() -> dict[str, Any]:
    cfg = load_config()
    panel = _load_json(PANEL_CACHE, {})
    ceased = _load_json(TRAFFIC_CEASED, {})
    return {
        "schema": "field-hazard-onset-panel/v1",
        "enabled": bool(cfg.get("enabled")),
        "proactive": bool(cfg.get("proactive")),
        "config_path": str(CFG_PATH),
        "panel": panel,
        "last_cease": ceased,
        "ledger": str(CEASE_LEDGER),
    }


def _synthetic_hazard_iq(n: int = 48_000, fs: float = 2_400_000.0) -> np.ndarray:
    """Quiet carrier then impulsive burst — for tests."""
    rng = np.random.default_rng(7)
    iq = (rng.standard_normal(n) + 1j * rng.standard_normal(n)).astype(np.complex64) * 0.002
    burst_at = 4000
    burst = (rng.standard_normal(n - burst_at) + 1j * rng.standard_normal(n - burst_at)).astype(np.complex64)
    burst *= np.linspace(0.1, 8.0, len(burst))
    iq[burst_at:] += burst
    return iq


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    cmd = (args[0] if args else "status").lower()

    if cmd in ("status", "json", "panel"):
        json.dump(panel_status(), sys.stdout, indent=2)
        print()
        return 0

    if cmd == "test":
        iq = _synthetic_hazard_iq()
        result = guard_capture(iq, {"freq_mhz": 93.1}, station_id="test", force=True)
        out = {k: v for k, v in result.items() if k != "iq"}
        json.dump(out, sys.stdout, indent=2)
        print()
        return 0 if result.get("hazard", {}).get("hazard") else 1

    if cmd == "guard" and len(args) > 1:
        payload = json.loads(args[1])
        n = int(payload.get("samples") or 48000)
        iq = _synthetic_hazard_iq(n)
        result = guard_capture(
            iq,
            payload.get("read"),
            station_id=str(payload.get("station_id") or ""),
            force=bool(payload.get("force")),
        )
        out = {k: v for k, v in result.items() if k != "iq"}
        json.dump(out, sys.stdout, indent=2)
        print()
        return 0

    print(
        "usage: field-hazard-onset.py [status|json|panel|test|guard '<json>']",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())