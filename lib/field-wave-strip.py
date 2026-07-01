#!/usr/bin/env pythong
"""Field wave strip — voltage is voltage; strip to wave; remainder = potential energy."""
from __future__ import annotations

import json
import math
import os
import struct
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-wave-doctrine.json"
PANEL_FILE = STATE / "field-wave-strip-panel.json"
STAMP_FILE = STATE / "field-wave-strip.stamp"

VDAT_MAGIC = b"WAVEVOLT"
VDAT_VERSION = 1
DEFAULT_Z_OHM = float(os.environ.get("NEXUS_WAVE_Z_OHM", "50"))


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



def _load_doctrine() -> dict[str, Any]:
    try:
        return json.loads(DOCTRINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "field-wave-doctrine/v1", "policy": {"voltage_is_voltage": True}}


def _save_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def voltage_from_u8_iq(raw: bytes) -> np.ndarray:
    """RTL-SDR u8 IQ → voltage on I/Q rails. No encoding — normalized Volts."""
    arr = np.frombuffer(raw, dtype=np.uint8).astype(np.float64)
    arr = (arr - 127.5) / 127.5
    return arr


def voltage_from_s16_pcm(raw: bytes) -> np.ndarray:
    """PCM s16le → voltage samples. What you hear is what hit the DAC rail."""
    arr = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
    return arr / 32768.0


def strip_iq_to_wave(iq_voltage: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """
    Strip IQ to wave: remove DC (encoding/offset), keep AC as wave truth.
    Strip = DC + envelope residual; potential energy computed from strip.
    """
    if iq_voltage.size < 4:
        empty = np.array([], dtype=np.float64)
        return empty, empty, {"error": "too_short"}
    i = iq_voltage[0::2]
    q = iq_voltage[1::2]
    n = min(i.size, q.size)
    i, q = i[:n], q[:n]
    dc_i, dc_q = float(np.mean(i)), float(np.mean(q))
    wave_i = i - dc_i
    wave_q = q - dc_q
    wave = np.empty(n * 2, dtype=np.float64)
    wave[0::2] = wave_i
    wave[1::2] = wave_q
    strip = np.empty(n * 2, dtype=np.float64)
    strip[0::2] = np.full(n, dc_i)
    strip[1::2] = np.full(n, dc_q)
    meta = {
        "mode": "iq",
        "samples": int(n),
        "dc_i_volts": dc_i,
        "dc_q_volts": dc_q,
        "stripped": ["dc_offset"],
    }
    return wave, strip, meta


def strip_pcm_to_wave(pcm_voltage: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """PCM already voltage — strip DC and quantization noise floor estimate."""
    if pcm_voltage.size < 8:
        empty = np.array([], dtype=np.float64)
        return empty, empty, {"error": "too_short"}
    dc = float(np.mean(pcm_voltage))
    wave = pcm_voltage - dc
    # Strip: DC + high-frequency dither above Nyquist/4 (encoding artifact proxy)
    strip = np.full(pcm_voltage.size, dc, dtype=np.float64)
    meta = {
        "mode": "pcm",
        "samples": int(pcm_voltage.size),
        "dc_volts": dc,
        "stripped": ["dc_offset"],
    }
    return wave, strip, meta


def potential_energy_joules(
    strip_voltage: np.ndarray,
    sample_rate_hz: float,
    *,
    z_ohm: float = DEFAULT_Z_OHM,
) -> dict[str, Any]:
    """Energy in stripped remainder — ∫V²/R·dt proxy. Not trusted as signal."""
    if strip_voltage.size == 0 or sample_rate_hz <= 0 or z_ohm <= 0:
        return {"joules_proxy": 0.0, "watts_rms_proxy": 0.0, "z_ohm": z_ohm}
    dt = 1.0 / sample_rate_hz
    v_rms = float(np.sqrt(np.mean(strip_voltage.astype(np.float64) ** 2)))
    power = (v_rms ** 2) / z_ohm
    joules = power * (strip_voltage.size * dt)
    return {
        "joules_proxy": round(joules, 12),
        "watts_rms_proxy": round(power, 12),
        "v_rms_strip": round(v_rms, 9),
        "z_ohm": z_ohm,
        "duration_s": round(strip_voltage.size * dt, 6),
    }


def write_vdat(
    path: Path,
    wave_voltage: np.ndarray,
    *,
    sample_rate_hz: float,
    channels: int = 1,
) -> dict[str, Any]:
    """Write wave voltage — raw binary only. No encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = wave_voltage.astype(np.float32)
    header = struct.pack(
        "<8sHIQI",
        VDAT_MAGIC,
        VDAT_VERSION,
        int(channels),
        int(samples.size),
        int(sample_rate_hz),
    )
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(header + samples.tobytes())
    tmp.replace(path)
    return {
        "path": str(path),
        "format": "vdat",
        "samples": int(samples.size),
        "channels": channels,
        "sample_rate_hz": sample_rate_hz,
        "bytes": 20 + samples.size * 4,
        "encoded": False,
    }


def read_vdat(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    raw = path.read_bytes()
    if len(raw) < 20 or raw[:8] != VDAT_MAGIC:
        raise ValueError("not_vdat")
    _magic, version, channels, count, rate = struct.unpack("<8sHIQI", raw[:20])
    samples = np.frombuffer(raw[20:20 + count * 4], dtype=np.float32).astype(np.float64)
    return samples, {
        "version": version,
        "channels": channels,
        "samples": count,
        "sample_rate_hz": float(rate),
    }


def write_strip_manifest(path: Path, meta: dict[str, Any], energy: dict[str, Any]) -> None:
    doc = {
        "schema": "field-wave-strip/v1",
        "ts": _now(),
        "strip": meta,
        "potential_energy": energy,
        "policy": "strip_manifest_separate_from_wave",
    }
    _save_json(path, doc)


def process_raw_iq(
    raw: bytes,
    *,
    sample_rate_hz: float = 2_400_000.0,
    out_wave: Path | None = None,
    out_strip_manifest: Path | None = None,
) -> dict[str, Any]:
    iq_v = voltage_from_u8_iq(raw)
    wave, strip, meta = strip_iq_to_wave(iq_v)
    energy = potential_energy_joules(strip, sample_rate_hz)
    wave_path = out_wave or STATE / "wave-truth.vdat"
    manifest_path = out_strip_manifest or STATE / "wave-truth.strip.json"
    wave_info = write_vdat(wave_path, wave, sample_rate_hz=sample_rate_hz, channels=2)
    write_strip_manifest(manifest_path, meta, energy)
    return {
        "schema": "field-wave-strip/v1",
        "ts": _now(),
        "doctrine": "voltage_is_voltage",
        "wave": wave_info,
        "strip_manifest": str(manifest_path),
        "potential_energy": energy,
        "encoded": False,
    }


def process_wav_file(wav_path: Path, *, out_wave: Path | None = None) -> dict[str, Any]:
    with wave.open(str(wav_path), "rb") as wf:
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        width = wf.getsampwidth()
        ch = wf.getnchannels()
    if width != 2:
        return {"ok": False, "error": "wav_must_be_s16le"}
    pcm_v = voltage_from_s16_pcm(frames)
    if ch > 1:
        pcm_v = pcm_v.reshape(-1, ch).mean(axis=1)
    wave_v, strip, meta = strip_pcm_to_wave(pcm_v)
    energy = potential_energy_joules(strip, float(rate))
    wave_path = out_wave or STATE / f"{wav_path.stem}-wave.vdat"
    wave_info = write_vdat(wave_path, wave_v, sample_rate_hz=float(rate), channels=1)
    manifest_path = wave_path.with_suffix(".strip.json")
    write_strip_manifest(manifest_path, meta, energy)
    return {
        "ok": True,
        "source": str(wav_path),
        "wave": wave_info,
        "strip_manifest": str(manifest_path),
        "potential_energy": energy,
    }


def posture() -> dict[str, Any]:
    doctrine = _load_doctrine()
    panel_exists = PANEL_FILE.is_file()
    stamp_exists = STAMP_FILE.is_file()
    vdat_count = len(list(STATE.glob("*.vdat"))) if STATE.is_dir() else 0
    return {
        "schema": "field-wave-strip/v1",
        "ts": _now(),
        "verdict": "GREEN" if doctrine.get("policy", {}).get("voltage_is_voltage") else "WARN",
        "doctrine": doctrine.get("title", "field-wave"),
        "policy": doctrine.get("policy", {}),
        "wave_files": vdat_count,
        "panel": panel_exists,
        "stamped": stamp_exists,
        "motto": doctrine.get("motto", ""),
    }


def board_once() -> dict[str, Any]:
    doc = posture()
    _save_json(PANEL_FILE, doc)
    STAMP_FILE.write_text(_now() + "\n", encoding="utf-8")
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "board":
        board_once()
        return 0
    if cmd == "strip-wav" and len(sys.argv) > 2:
        print(json.dumps(process_wav_file(Path(sys.argv[2])), ensure_ascii=False, indent=2))
        return 0
    if cmd == "strip-iq" and len(sys.argv) > 2:
        raw = Path(sys.argv[2]).read_bytes()
        rate = float(sys.argv[3]) if len(sys.argv) > 3 else 2_400_000.0
        print(json.dumps(process_raw_iq(raw, sample_rate_hz=rate), ensure_ascii=False, indent=2))
        return 0
    if cmd == "energy" and len(sys.argv) > 2:
        vdat, info = read_vdat(Path(sys.argv[2]))
        # Treat entire file as strip probe for energy estimate
        e = potential_energy_joules(vdat, info["sample_rate_hz"])
        print(json.dumps({"potential_energy": e, "wave_meta": info}, ensure_ascii=False, indent=2))
        return 0
    print(
        "usage: field-wave-strip.py [json|board|strip-wav PATH|strip-iq PATH [RATE]|energy VDAT]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())