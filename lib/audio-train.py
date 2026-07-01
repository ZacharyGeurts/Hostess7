#!/usr/bin/env pythong
"""Audio Train — learn acceptable ranges per source; outside range = hostile intent."""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
REGISTRY_JSON = STATE / "audio-train.json"
REGISTRY_LEDGER = STATE / "audio-train.jsonl"
PANEL_CACHE = STATE / "audio-train-panel.json"
SEED = INSTALL / "data" / "audio-train-seed.json"

TRAIN_RE = re.compile(r"\b(train|rail|amtrak|metra|subway|transit|locomotive|commuter)\b", re.I)
PET_RE = re.compile(r"tractive|whistle|fi\.pet|petcube|pawtrack|collar|pet\s?tracker", re.I)


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
        REGISTRY_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with REGISTRY_LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _seed() -> dict[str, Any]:
    return _load_json(SEED, {"dimensions": {}, "warmup_samples": 3})


def _blank_source(source_id: str, label: str, kind: str) -> dict[str, Any]:
    seed = _seed()
    dims = seed.get("dimensions") or {}
    ranges: dict[str, dict[str, float]] = {}
    for key, spec in dims.items():
        ranges[key] = {
            "min": float(spec.get("seed_min", spec.get("floor", 0))),
            "max": float(spec.get("seed_max", spec.get("ceiling", 1))),
            "floor": float(spec.get("floor", 0)),
            "ceiling": float(spec.get("ceiling", 1)),
            "samples": 0,
        }
    return {
        "source_id": source_id,
        "label": label,
        "kind": kind,
        "ranges": ranges,
        "sample_count": 0,
        "hostile_events": 0,
        "last_hostile": None,
        "last_seen": _now(),
        "acceptable": True,
    }


def _learn_margin(spec: dict[str, Any], seed_doc: dict[str, Any]) -> float:
    span = float(spec.get("ceiling", 1)) - float(spec.get("floor", 0))
    return max(span * float(seed_doc.get("learn_margin_pct", 0.06)), 0.001)


def _hostile_margin(spec: dict[str, Any], seed_doc: dict[str, Any]) -> float:
    span = float(spec.get("ceiling", 1)) - float(spec.get("floor", 0))
    return max(span * float(seed_doc.get("hostility_margin_pct", 0.12)), 0.002)


def _expand_range(
    row: dict[str, float],
    dim: str,
    value: float,
    spec: dict[str, Any],
    seed_doc: dict[str, Any],
) -> None:
    margin = _learn_margin(spec, seed_doc)
    row["min"] = max(float(spec.get("floor", 0)), min(row["min"], value - margin))
    row["max"] = min(float(spec.get("ceiling", 1)), max(row["max"], value + margin))
    row["samples"] = int(row.get("samples") or 0) + 1


def _check_hostile(
    row: dict[str, float],
    value: float,
    spec: dict[str, Any],
    seed_doc: dict[str, Any],
    sample_count: int,
) -> tuple[bool, str]:
    warmup = int(seed_doc.get("warmup_samples", 3))
    if sample_count < warmup:
        return False, ""
    margin = _hostile_margin(spec, seed_doc)
    lo = float(row["min"]) - margin
    hi = float(row["max"]) + margin
    if value < lo:
        return True, f"below acceptable min ({value:.3f} < {lo:.3f})"
    if value > hi:
        return True, f"above acceptable max ({value:.3f} > {hi:.3f})"
    return False, ""


def _pet_guard() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("pet_signal_guard", INSTALL / "lib" / "pet-signal-guard.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _classify_kind(label: str, app: str = "") -> str:
    blob = f"{label} {app}".lower()
    if PET_RE.search(blob) or re.search(r"\b(pet|dog|cat|collar)\b", blob):
        return "pet"
    if TRAIN_RE.search(blob):
        return "train_transit"
    if any(x in blob for x in ("spotify", "vlc", "mpv", "rhythmbox", "music")):
        return "music"
    if "firefox" in blob or "chrome" in blob or "browser" in blob:
        return "browser"
    if "pipewire" in blob:
        return "pipewire"
    if "pulse" in blob:
        return "pulse"
    return "alsa"


def ingest_sample(
    source_id: str,
    sample: dict[str, Any],
    *,
    label: str = "",
    kind: str = "",
) -> dict[str, Any]:
    seed_doc = _seed()
    dims_seed = seed_doc.get("dimensions") or {}
    doc = _load_json(REGISTRY_JSON, {"sources": {}, "updated": None})
    sources: dict[str, dict[str, Any]] = dict(doc.get("sources") or {})
    sid = str(source_id or sample.get("source_id") or "unknown").strip() or "unknown"
    src = sources.get(sid) or _blank_source(
        sid,
        label or sample.get("label") or sid,
        kind or _classify_kind(label or sid, str(sample.get("app") or "")),
    )
    if label:
        src["label"] = label
    if kind:
        src["kind"] = kind

    hostile_dims: list[dict[str, Any]] = []
    for dim, spec in dims_seed.items():
        if dim not in sample or sample[dim] is None:
            continue
        try:
            val = float(sample[dim])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(val):
            continue
        row = src["ranges"].setdefault(dim, {
            "min": float(spec.get("seed_min", 0)),
            "max": float(spec.get("seed_max", 1)),
            "floor": float(spec.get("floor", 0)),
            "ceiling": float(spec.get("ceiling", 1)),
            "samples": 0,
        })
        hit, reason = _check_hostile(row, val, spec, seed_doc, int(src.get("sample_count") or 0))
        if hit:
            hostile_dims.append({"dimension": dim, "value": val, "reason": reason, "acceptable": [row["min"], row["max"]]})
        _expand_range(row, dim, val, spec, seed_doc)

    src["sample_count"] = int(src.get("sample_count") or 0) + 1
    src["last_seen"] = _now()
    hostile = bool(hostile_dims)
    src["acceptable"] = not hostile
    if hostile:
        src["hostile_events"] = int(src.get("hostile_events") or 0) + 1
        src["last_hostile"] = _now()
        _append_ledger({
            "ts": _now(),
            "event": "audio_hostile_intent",
            "source_id": sid,
            "label": src.get("label"),
            "kind": src.get("kind"),
            "dimensions": hostile_dims,
            "vector": "AUDIO_RANGE_VIOLATION",
        })
        guard_py = INSTALL / "lib" / "pet-signal-guard.py"
        if guard_py.is_file():
            try:
                _pet_guard().respond_to_pet_attack(
                    sid, str(src.get("label") or sid), str(src.get("kind") or ""),
                    hostile_dims,
                )
            except Exception:
                pass

    sources[sid] = src
    doc["sources"] = sources
    doc["updated"] = _now()
    doc["schema"] = "audio-train/v1"
    doc["hostess_version"] = seed_doc.get("hostess_version") or "6.9"
    doc["motto"] = seed_doc.get("motto") or ""
    _save_json(REGISTRY_JSON, doc)
    return {
        "ok": True,
        "source_id": sid,
        "acceptable": not hostile,
        "hostile_intent": hostile,
        "violations": hostile_dims,
        "ranges": src["ranges"],
        "sample_count": src["sample_count"],
    }


def _volume_to_db(pct: float) -> float:
    pct = max(0.0, min(100.0, pct))
    if pct <= 0.01:
        return -72.0
    return round(20.0 * math.log10(pct / 100.0), 2)


def _harvest_pipewire_pulse() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cmd, backend in (
        (["pactl", "list", "sink-inputs"], "pulse"),
        (["pw-cli", "ls", "Node"], "pipewire"),
    ):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode != 0 or not (proc.stdout or "").strip():
            continue
        if backend == "pulse":
            blocks = (proc.stdout or "").split("Sink Input #")
            for block in blocks[1:]:
                app = ""
                m = re.search(r"application\.name = \"([^\"]+)\"", block)
                if m:
                    app = m.group(1)
                m2 = re.search(r"Volume:.*?(\d+)%", block)
                vol = float(m2.group(1)) if m2 else 50.0
                sid_m = re.search(r"^(\d+)", block.strip())
                sid = f"pulse:{sid_m.group(1) if sid_m else app or 'sink'}"
                level = _volume_to_db(vol)
                rows.append({
                    "source_id": sid,
                    "label": app or sid,
                    "kind": _classify_kind(app, app),
                    "sample": {
                        "level_db": level,
                        "peak_db": min(-1.0, level + 6.0),
                        "bass_energy": 0.35,
                        "treble_energy": 0.4,
                        "sample_rate_hz": 48000.0,
                        "latency_ms": 24.0,
                    },
                })
        else:
            for block in re.split(r"\nid \d+, type", proc.stdout or ""):
                if "node.name" not in block:
                    continue
                name_m = re.search(r'node\.name = "([^"]+)"', block)
                desc_m = re.search(r'application\.name = "([^"]+)"', block)
                name = (desc_m.group(1) if desc_m else None) or (name_m.group(1) if name_m else "pipewire")
                sid = f"pipewire:{name}"
                rows.append({
                    "source_id": sid,
                    "label": name,
                    "kind": _classify_kind(name, name),
                    "sample": {
                        "level_db": -24.0,
                        "peak_db": -12.0,
                        "bass_energy": 0.4,
                        "treble_energy": 0.45,
                        "sample_rate_hz": 48000.0,
                        "latency_ms": 18.0,
                    },
                })
        if rows:
            break
    return rows


def build_audio_train(harvest: bool = True) -> dict[str, Any]:
    if harvest:
        for row in _harvest_pipewire_pulse():
            ingest_sample(
                row["source_id"],
                row["sample"],
                label=row.get("label") or row["source_id"],
                kind=row.get("kind") or "alsa",
            )

    doc = _load_json(REGISTRY_JSON, {"sources": {}, "updated": None})
    seed_doc = _seed()
    sources = list((doc.get("sources") or {}).values())
    acceptable = [s for s in sources if s.get("acceptable", True)]
    hostile = [s for s in sources if not s.get("acceptable", True)]
    train_sources = [s for s in sources if s.get("kind") == "train_transit" or TRAIN_RE.search(str(s.get("label") or ""))]

    table = []
    for spec_key, spec in (seed_doc.get("dimensions") or {}).items():
        for src in sources:
            r = (src.get("ranges") or {}).get(spec_key)
            if not r:
                continue
            table.append({
                "source_id": src.get("source_id"),
                "label": src.get("label"),
                "kind": src.get("kind"),
                "dimension": spec_key,
                "dimension_label": spec.get("label", spec_key),
                "acceptable_min": r.get("min"),
                "acceptable_max": r.get("max"),
                "floor": r.get("floor"),
                "ceiling": r.get("ceiling"),
                "samples": r.get("samples"),
                "acceptable": src.get("acceptable", True),
            })

    pet_guard: dict[str, Any] = {}
    guard_py = INSTALL / "lib" / "pet-signal-guard.py"
    if guard_py.is_file():
        try:
            pet_guard = _pet_guard().panel_json()
        except Exception:
            pet_guard = {}

    out = {
        "schema": "audio-train/v1",
        "updated": doc.get("updated") or _now(),
        "hostess_version": seed_doc.get("hostess_version") or "6.9",
        "motto": seed_doc.get("motto") or "",
        "tagline": "Acceptable ranges grow as audio arrives — push outside = hostile intent.",
        "touch_policy": {
            "motto": (
                "A human should never feel a touch if it is a safe signal. "
                "Music, normal car traffic, animals, and Train are different."
            ),
            "train_felt_safe": True,
        },
        "pet_signal_guard": pet_guard,
        "stats": {
            "sources": len(sources),
            "acceptable": len(acceptable),
            "hostile": len(hostile),
            "train_transit": len(train_sources),
            "dimensions": len(seed_doc.get("dimensions") or {}),
            "ledger_events": sum(int(s.get("hostile_events") or 0) for s in sources),
        },
        "sources": {s["source_id"]: s for s in sources if s.get("source_id")},
        "table": table[:120],
        "recent_hostile": hostile[:8],
        "dimensions": seed_doc.get("dimensions") or {},
    }
    _save_json(PANEL_CACHE, out)
    return out


def panel_json() -> dict[str, Any]:
    return build_audio_train(harvest=True)


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_audio_train(harvest=False), ensure_ascii=False))
        return 0
    if cmd == "ingest" and len(sys.argv) >= 3:
        body = json.loads(sys.argv[2])
        sid = str(body.get("source_id") or "manual")
        sample = body.get("sample") or body
        out = ingest_sample(sid, sample, label=str(body.get("label") or sid), kind=str(body.get("kind") or ""))
        print(json.dumps(out, ensure_ascii=False))
        return 0
    if cmd == "harvest":
        rows = _harvest_pipewire_pulse()
        for row in rows:
            ingest_sample(row["source_id"], row["sample"], label=row.get("label"), kind=row.get("kind"))
        print(json.dumps({"ok": True, "harvested": len(rows)}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: audio-train.py [json|build|harvest|ingest JSON]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())