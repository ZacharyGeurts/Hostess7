#!/usr/bin/env pythong
"""FCC prom detector — bursts, beams, waves, pulse/shock weapons on any modality."""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-fcc-prom-detector-doctrine.json"
PANEL = STATE / "field-fcc-prom-detector-panel.json"
LEDGER = STATE / "field-fcc-prom-detector.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _append(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def detect_prom(
    *,
    samples: list[float] | None = None,
    freqs_hz: list[float] | None = None,
    timestamps_ms: list[float] | None = None,
    coherence: float | None = None,
    doa_locked: bool = False,
    duty_cycle: float | None = None,
    repetition_hz: float | None = None,
    envelope: str = "",
    assault_burst: bool = False,
    modality: str = "rf",
    source: str = "",
) -> dict[str, Any]:
    """Analyze sample stream for FCC prom / weapon signatures."""
    doc = _load(DOCTRINE, {})
    hits: list[dict[str, Any]] = []
    samples = samples or []
    freqs = freqs_hz or []
    times = timestamps_ms or []

    if len(samples) >= 3 and len(times) >= 3:
        for i in range(1, len(samples)):
            dt = max(0.001, (times[i] - times[i - 1]) / 1000.0)
            ddb = abs(samples[i] - samples[i - 1])
            rate = ddb / dt
            if rate >= 18000:
                hits.append({
                    "id": "fcc_burst",
                    "vector": "fcc_burst",
                    "severity": "high",
                    "rate_db_s": round(rate, 1),
                    "detail": f"burst Δ{ddb:.1f}dB in {dt*1000:.1f}ms",
                })
                break

    if len(freqs) >= 4 and len(times) >= 4:
        for i in range(1, len(freqs)):
            dt = max(0.001, (times[i] - times[i - 1]) / 1000.0)
            dh = abs(freqs[i] - freqs[i - 1])
            if dh / dt >= 500000:
                hits.append({
                    "id": "fcc_wave_rapid",
                    "vector": "fcc_wave_rapid",
                    "severity": "critical",
                    "delta_hz_s": round(dh / dt),
                    "detail": "rapid carrier hop",
                })
                break

    if coherence is not None and coherence >= 0.72 and doa_locked:
        hits.append({
            "id": "fcc_beam",
            "vector": "fcc_beam",
            "severity": "high",
            "coherence": coherence,
            "detail": "coherent directed beam",
        })

    if duty_cycle is not None and repetition_hz is not None:
        if 0 < duty_cycle <= 0.15 and 1 <= repetition_hz <= 1000:
            hits.append({
                "id": "pulse_weapon",
                "vector": "pulse_weapon",
                "severity": "critical",
                "duty_cycle": duty_cycle,
                "repetition_hz": repetition_hz,
                "detail": "pulsed weapon duty cycle",
            })

    if assault_burst or envelope in ("square_burst", "shock", "stun"):
        hits.append({
            "id": "shock_weapon",
            "vector": "shock_weapon",
            "severity": "critical",
            "envelope": envelope or "assault_burst",
            "detail": "shock/stun assault waveform",
        })

    threat = bool(hits)
    primary = hits[0] if hits else None
    out = {
        "ok": True,
        "schema": "field-fcc-prom-detect/v1",
        "utc": _utc(),
        "modality": modality,
        "source": source[:120],
        "threat": threat,
        "hits": hits,
        "hit_count": len(hits),
        "primary_vector": primary.get("vector") if primary else None,
        "primary_severity": primary.get("severity") if primary else "none",
        "fcc_violation": threat,
        "motto": doc.get("motto"),
    }
    if threat:
        _append({**out, "event": "prom_detect"})
    return out


def scan_channel(channel: dict[str, Any]) -> dict[str, Any]:
    """Scan a signals-field channel dict for prom signatures."""
    strength = float(channel.get("strength") or channel.get("energy", 0) * 100 or 0)
    samples = [strength * 0.4, strength * 0.9, strength, strength * 1.2] if strength else []
    times = [0.0, 10.0, 20.0, 30.0]
    freqs = []
    if channel.get("freq_mhz"):
        f0 = float(channel["freq_mhz"]) * 1e6
        freqs = [f0, f0, f0 + 600000, f0 + 1200000]
    assault = channel.get("threat_tag") in ("audio_hostile", "assault_burst") or "assault" in str(channel.get("label", "")).lower()
    det = detect_prom(
        samples=samples,
        freqs_hz=freqs,
        timestamps_ms=times,
        coherence=0.75 if channel.get("modality") == "laser" else None,
        doa_locked=bool(channel.get("recognized")),
        assault_burst=assault,
        modality=str(channel.get("modality") or channel.get("kind") or "rf"),
        source=str(channel.get("id") or channel.get("label") or ""),
    )
    return {**det, "channel_id": channel.get("id"), "fcc_id": channel.get("fcc_id")}


def panel(*, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    out = {
        "ok": True,
        "schema": "field-fcc-prom-detector-panel/v1",
        "updated": _utc(),
        "motto": doc.get("motto"),
        "signatures": doc.get("signatures") or [],
        "threat_vectors": doc.get("threat_vectors") or {},
        "api": doc.get("api"),
    }
    if write:
        PANEL.parent.mkdir(parents=True, exist_ok=True)
        tmp = PANEL.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(PANEL)
    return out


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "detect":
        det = detect_prom(assault_burst="assault" in " ".join(sys.argv[2:]).lower())
        print(json.dumps(det, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-fcc-prom-detector.py [panel|detect]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())