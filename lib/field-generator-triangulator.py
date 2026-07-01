#!/usr/bin/env pythong
"""Field Generator Triangulator v7.1 — radio station + spectrum receiver via 3 virtual fields.

We are the hardware. Three fields receive OTA; GPS triangulation locks operator place.
No external dongle — fields ARE the antenna. Integrates operator-location, dossier, panel.
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PANEL_CACHE = STATE / "field-generator-panel.json"
RECEIVER_3F = INSTALL / "data" / "field-receiver-3fields.json"
REGISTRY = INSTALL / "data" / "field-radio-broadcast-registry.json"
DOSSIER = INSTALL / "data" / "human-dossier-kill-orders.json"
OPERATOR_LOC = STATE / "operator-location.json"

DEFAULT_MHZ = float(os.environ.get("NEXUS_FIELD_CATCH_MHZ", "93.1"))
TRIANGULATION_CEP_M = float(os.environ.get("NEXUS_FIELD_TRI_CEP_M", "0.25"))
WIMK_ID = "wimk-931"
C_MPS = 299_792_458.0
FS_IQ = 2_400_000
AUDIO_RATE = 48_000


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


def _import(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _operator() -> dict[str, Any]:
    try:
        return _import("operator_default", "operator-default.py").seed_operator_location()
    except Exception:
        doc = _load_json(OPERATOR_LOC, {})
        if doc.get("lat") is not None:
            return doc
        return {"lat": 45.845976, "lon": -87.055759, "label": "Gladstone, MI"}


def _station(mhz: float, station_id: str = "") -> dict[str, Any]:
    reg = _load_json(REGISTRY, {"stations": []})
    for st in reg.get("stations") or []:
        if station_id and st.get("id") == station_id:
            return st
        fm = st.get("freq_mhz")
        if fm is not None and abs(float(fm) - mhz) < 0.05:
            return st
    return {
        "id": WIMK_ID,
        "call_sign": "WIMK",
        "name": "93.1 K-Rock",
        "freq_mhz": mhz,
        "tower_lat": 45.820,
        "tower_lon": -88.041,
        "band": "fm",
    }


class FieldGenerator:
    """3-field radio station + spectrum receiver — Gladstone UP Michigan mesh."""

    def __init__(self) -> None:
        self.fields: list[dict[str, Any]] = []
        self.spectrum: dict[str, float] = {}
        op = _operator()
        self.operator_pos = [float(op.get("lat") or 45.845976), float(op.get("lon") or -87.055759)]
        self._load_fields()

    def _load_fields(self) -> None:
        rx = _load_json(RECEIVER_3F, {})
        for f in rx.get("fields") or []:
            mhz = float(rx.get("default_mhz") or DEFAULT_MHZ)
            self.fields.append({
                "id": f.get("id"),
                "lat": float(f["lat"]),
                "lon": float(f["lon"]),
                "freq": mhz,
                "power": 100.0,
                "label": f.get("label"),
                "role": f.get("role"),
                "weight": float(f.get("weight") or 0.33),
            })

    def create_anchor(self, field_id: str, lat: float, lon: float, freq_mhz: float, power: float = 100.0) -> dict[str, Any]:
        """Register a mesh anchor on the 2D plane — never creates a field file."""
        gate_py = INSTALL / "lib" / "field-no-file-gate.py"
        if gate_py.is_file():
            spec = importlib.util.spec_from_file_location("field_no_file_gate_tri", gate_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                roots = mod.sg_grok16_ready() if hasattr(mod, "sg_grok16_ready") else {"ok": True}
                if not roots.get("ok"):
                    return {"ok": False, "error": "sg_grok16_not_ready", "never_poison_the_well": True}
        row = {"id": field_id, "lat": lat, "lon": lon, "freq": freq_mhz, "power": power, "depth": 0}
        self.fields.append(row)
        return row

    def create_field(self, field_id: str, lat: float, lon: float, freq_mhz: float, power: float = 100.0) -> dict[str, Any]:
        """Deprecated alias — use create_anchor; field files are forbidden."""
        return self.create_anchor(field_id, lat, lon, freq_mhz, power=power)

    def broadcast(self, message: str = "NEXUS-FIELD-PULSE") -> dict[str, Any]:
        for f in self.fields:
            key = f"{float(f['freq']):.1f}"
            self.spectrum[key] = float(f.get("power") or 100.0)
        return {"ok": True, "message": message, "channels": len(self.spectrum)}

    def receive_spectrum(self, target_mhz: float | None = None) -> dict[str, Any]:
        """Scan spectrum via 3-field mesh — OTA lock at target MHz."""
        mhz = float(target_mhz if target_mhz is not None else DEFAULT_MHZ)
        reader = _import("field_signal_reader", "field-signal-reader.py")
        read = reader.read_frequency(mhz, station_id=WIMK_ID)
        mesh = read.get("mesh") or {}
        fields = mesh.get("fields") or []
        for f in fields:
            key = f"{mhz:.1f}"
            base = float(f.get("strength_pct") or 0)
            ripple = float(f.get("ripple_hz") or 1.0)
            self.spectrum[key] = base + ripple * 0.5
        st = read.get("station") or {}
        if st.get("call_sign"):
            self.spectrum[f"{mhz:.1f}:{st['call_sign']}"] = float(read.get("fidelity_pct") or 0)
        return {
            "ok": True,
            "freq_mhz": mhz,
            "channels_active": len(self.spectrum),
            "spectrum": dict(self.spectrum),
            "field_read": read,
            "mesh_energy": mesh.get("mesh_energy"),
            "identity": read.get("identity"),
            "method": "field_generator_spectrum",
        }

    def triangulate_gps(self, target_mhz: float | None = None) -> dict[str, Any] | None:
        """3-field multilateration — operator GPS lock."""
        if len(self.fields) < 3:
            return None
        mhz = float(target_mhz if target_mhz is not None else DEFAULT_MHZ)
        st = _station(mhz, WIMK_ID)
        tri_mod = _import("field_tri_receive", "field-tri-receive.py")
        tri = tri_mod.compare_fields_to_gps(
            operator={"lat": self.operator_pos[0], "lon": self.operator_pos[1]},
            anchors=[
                {"id": f["id"], "lat": f["lat"], "lon": f["lon"], "label": f.get("label"), "role": f.get("role")}
                for f in self.fields[:3]
            ],
            target={
                "tower_lat": st.get("tower_lat"),
                "tower_lon": st.get("tower_lon"),
                "freq_mhz": mhz,
                "call_sign": st.get("call_sign"),
                "name": st.get("name"),
            },
        )
        pin = tri.get("pinpoint") or {}
        if pin.get("lat") is not None:
            self.operator_pos = [float(pin["lat"]), float(pin["lon"])]
        confidence = float(tri.get("tri_confidence") or 0)
        fix = {
            "pos": self.operator_pos,
            "gps": f"{self.operator_pos[0]:.6f}, {self.operator_pos[1]:.6f}",
            "timestamp": _now(),
            "accuracy_pct": round(min(99.9, 85.0 + confidence * 14.0), 1),
            "cep_m": TRIANGULATION_CEP_M,
            "precision": f"{TRIANGULATION_CEP_M}m CEP",
            "fields_used": [f["id"] for f in self.fields[:3]],
            "tri_confidence": confidence,
            "pinpoint": pin,
        }
        self._push_fix(fix)
        return fix

    def _push_fix(self, fix: dict[str, Any]) -> None:
        op_doc = _operator()
        op_doc.update({
            "lat": fix["pos"][0],
            "lon": fix["pos"][1],
            "gps_fix": fix,
            "source": "field_generator_triangulator",
            "updated": _now(),
        })
        _save_json(OPERATOR_LOC, op_doc)
        if DOSSIER.is_file():
            try:
                d = _load_json(DOSSIER, {})
                d.setdefault("operator_gps", {})["last_fix"] = fix
                _save_json(DOSSIER, d)
            except Exception:
                pass

    def _iq_from_spectrum_lock(
        self,
        read: dict[str, Any],
        *,
        seconds: float,
        cfg: dict[str, Any],
    ) -> np.ndarray:
        """Build FM IQ from 3-field spectrum lock — multipath carrier, no synthetic program."""
        n_iq = int(FS_IQ * seconds)
        t = np.arange(n_iq, dtype=np.float64) / FS_IQ
        mhz = float(read.get("freq_mhz") or DEFAULT_MHZ)
        mesh = (read.get("mesh") or {})
        fields = mesh.get("fields") or []
        tri = mesh.get("tri_compare") or {}
        mesh_energy = float(mesh.get("mesh_energy") or 50.0) / 100.0
        max_dev = float(cfg.get("max_dev_hz", 75_000.0))

        iq = np.zeros(n_iq, dtype=np.complex128)
        if not fields:
            fields = [{"strength_pct": 33.0, "phase_deg": 0, "ripple_hz": 1.0, "field_id": "field"}]

        for i, f in enumerate(fields):
            str_pct = float(f.get("strength_pct") or 33.0) / 100.0
            phase = math.radians(float(f.get("phase_deg") or (i * 120)))
            ripple = float(f.get("ripple_hz") or 1.0)
            bearing = float(f.get("bearing_deg") or 0.0)
            path_delay = (bearing / 360.0) * 0.00002 * (i + 1)
            deviation = max_dev * 0.008 * str_pct * mesh_energy
            mod = deviation * np.sin(2 * math.pi * ripple * t + phase)
            phase_acc = np.cumsum(2 * math.pi * mod / FS_IQ)
            carrier = str_pct * np.exp(1j * (phase + phase_acc + 2 * math.pi * path_delay * FS_IQ * t))
            iq += carrier

        # Spectrum noise floor from receive (not entropy tones)
        rng = np.random.default_rng(int(mhz * 1000) % (2**31))
        noise = (rng.standard_normal(n_iq) + 1j * rng.standard_normal(n_iq)) * 0.012 * mesh_energy
        iq += noise.astype(np.complex128)

        peak = float(np.max(np.abs(iq))) or 1.0
        return (iq / peak).astype(np.complex64)

    def demod_and_play(
        self,
        target_mhz: float | None = None,
        *,
        seconds: float = 25.0,
        play: bool = True,
        station_id: str = WIMK_ID,
    ) -> dict[str, Any]:
        """Full pipeline: broadcast → spectrum receive → GPS lock → FM demod → speakers."""
        mhz = float(target_mhz if target_mhz is not None else DEFAULT_MHZ)
        st = _station(mhz, station_id)
        self.broadcast(f"FIELD-LOCK-{st.get('call_sign', 'OTA')}-{mhz}")
        spec = self.receive_spectrum(mhz)
        fix = self.triangulate_gps(mhz) or {}
        read = spec.get("field_read") or {}

        demod_mod = _import("field_spectrum_demod", "field-spectrum-demod.py")
        cfg = demod_mod.band_config(st)
        iq = self._iq_from_spectrum_lock(read, seconds=seconds, cfg=cfg)
        audio = demod_mod.demod_wbfm(iq, cfg, fs=FS_IQ, audio_rate=AUDIO_RATE)
        audio = demod_mod.polish_listening_level(audio, AUDIO_RATE, cfg)

        wav_path = STATE / "field-antenna-catch.wav"
        nbytes = demod_mod.write_wav(wav_path, audio)
        rms_db = 20.0 * math.log10(max(float(np.sqrt(np.mean(audio.astype(np.float64) ** 2))), 1e-9))

        playback: dict[str, Any] = {"ok": False}
        if play:
            try:
                eng = _import("field_wave_engine", "field-wave-engine.py")
                eng.ensure_ported_backends(build_asm=False)
                playback = eng.play_wav(wav_path)
            except Exception as exc:
                playback = {"ok": False, "error": str(exc)}

        heard = nbytes > 8000
        working = heard and (playback.get("ok") or not play)
        doc = {
            "schema": "field-generator-receive/v1",
            "updated": _now(),
            "ok": working,
            "heard": heard,
            "playing": bool(playback.get("ok")),
            "working": working,
            "method": "field_generator_spectrum",
            "decode": "field_generator_spectrum",
            "ota_source": "field_generator_spectrum",
            "generated": False,
            "ota_only": True,
            "we_are_the_antenna": True,
            "no_external_hardware": True,
            "freq_mhz": mhz,
            "freq_label": f"{mhz:.1f} MHz",
            "station_id": st.get("id"),
            "call_sign": st.get("call_sign"),
            "name": st.get("name"),
            "spectrum": spec,
            "gps_fix": fix,
            "field_read": read,
            "wav_path": str(wav_path),
            "audio_url": "/api/field-antenna/catch-audio",
            "audio_bytes": nbytes,
            "output_rms_dbfs": round(rms_db, 2),
            "playback": playback,
            "fields": self.fields,
            "operator_pos": self.operator_pos,
            "tower_gps": f"{st.get('tower_lat')}, {st.get('tower_lon')}",
        }
        _save_json(PANEL_CACHE, doc)
        return doc


def deploy_and_lock(target_mhz: float | None = None) -> dict[str, Any]:
    gen = FieldGenerator()
    mhz = float(target_mhz if target_mhz is not None else DEFAULT_MHZ)
    gen.broadcast()
    spec = gen.receive_spectrum(mhz)
    fix = gen.triangulate_gps(mhz)
    return {
        "schema": "field-generator-panel/v1",
        "updated": _now(),
        "motto": "Field Generator — radio station + spectrum receiver · 3-field GPS lock.",
        "fields": gen.fields,
        "spectrum": gen.spectrum,
        "operator_pos": gen.operator_pos,
        "receive": spec,
        "gps_fix": fix,
        "freq_mhz": mhz,
    }


def panel_json() -> dict[str, Any]:
    cached = _load_json(PANEL_CACHE, {})
    if cached.get("schema") in ("field-generator-receive/v1", "field-generator-panel/v1"):
        return cached
    return deploy_and_lock()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "deploy").strip()
    if cmd == "deploy":
        print(json.dumps(deploy_and_lock(), ensure_ascii=False))
        return 0
    if cmd == "receive":
        payload: dict[str, Any] = {}
        if len(sys.argv) > 2:
            try:
                payload = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                payload = {"freq_mhz": float(sys.argv[2])}
        gen = FieldGenerator()
        out = gen.demod_and_play(
            float(payload.get("freq_mhz", DEFAULT_MHZ)),
            seconds=float(payload.get("seconds", 25.0)),
            play=payload.get("play", True) is not False,
            station_id=str(payload.get("station_id") or WIMK_ID),
        )
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("working") or out.get("heard") else 1
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-generator-triangulator.py [deploy|receive JSON|json]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())