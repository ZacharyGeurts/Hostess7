#!/usr/bin/env pythong
"""Predictive meld — fingerprint plates + corpus; skip refresh storm when stable."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-predictive-meld-doctrine.json"
PANEL = STATE / "field-predictive-meld-panel.json"
FAST_PATH_MS = 25
SIG_BYTES = 128


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _enabled() -> bool:
    if os.environ.get("NEXUS_PREDICTIVE_MELD", "1").strip().lower() in ("0", "false", "no"):
        return False
    doctrine = _load(DOCTRINE, {})
    return bool((doctrine.get("policy") or {}).get("enabled_by_default", True))


def _plate_sources() -> tuple[tuple[str, str], ...]:
    meld = _import_mod("plate_meld_src", "field-plate-meld.py")
    if meld and hasattr(meld, "PLATE_SOURCES"):
        return tuple(meld.PLATE_SOURCES)
    return ()


def _file_micro_sig(path: Path, *, nbytes: int = SIG_BYTES) -> str:
    if not path.is_file():
        return "missing"
    try:
        st = path.stat()
        head = path.read_bytes()[:nbytes]
        return hashlib.sha256(
            f"{st.st_size}:{int(st.st_mtime_ns)}:{head.hex()}".encode("utf-8")
        ).hexdigest()[:16]
    except OSError:
        return "error"


def plate_fingerprint() -> dict[str, Any]:
    """Lightweight plate snapshot — mtime + size + header bytes per panel."""
    doctrine = _load(DOCTRINE, {})
    nbytes = int((doctrine.get("policy") or {}).get("plate_micro_sig_bytes") or SIG_BYTES)
    domains: dict[str, Any] = {}
    material: list[str] = []
    present = 0
    for key, fname in _plate_sources():
        path = STATE / fname
        sig = _file_micro_sig(path, nbytes=nbytes)
        domains[key] = {"sig": sig, "present": sig != "missing"}
        if sig != "missing":
            present += 1
        material.append(f"{key}:{sig}")
    plate_hash = hashlib.sha256("|".join(material).encode()).hexdigest()
    return {
        "schema": "field-predictive-meld-fingerprint/v1",
        "updated": _now(),
        "plate_hash": plate_hash,
        "plate_count": present,
        "domains": domains,
        "material_lines": len(material),
    }


def _corpus_fingerprint() -> dict[str, Any]:
    bal = _import_mod("comb_balance", "field-combinatronic-balance.py")
    if bal and hasattr(bal, "corpus_fingerprint"):
        return bal.corpus_fingerprint(scan_library=False)
    return {"corpus_hash": "", "domains": {}}


def panel_state() -> dict[str, Any]:
    doc = _load(PANEL, {})
    if doc.get("plate_hash"):
        return doc
    return {
        "schema": "field-predictive-meld-panel/v1",
        "updated": _now(),
        "plate_hash": "",
        "corpus_hash": "",
        "cycles": 0,
        "skip_count": 0,
        "refresh_count": 0,
        "fast_path_count": 0,
        "avg_refresh_ms": 0.0,
        "avg_skip_ms": 0.0,
    }


def predictive_meld(*, force: bool = False) -> dict[str, Any]:
    """Predict whether a full plate refresh storm is needed."""
    if force or os.environ.get("FIELD_PREDICTIVE_MELD_FORCE", "").strip().lower() in ("1", "true", "yes"):
        return {
            "schema": "field-predictive-meld/v1",
            "updated": _now(),
            "skip_refresh": False,
            "skip_meld_refresh": False,
            "fast_path": False,
            "reason": "forced",
            "predicted_ms_saved": 0,
        }
    if not _enabled():
        return {
            "schema": "field-predictive-meld/v1",
            "updated": _now(),
            "skip_refresh": False,
            "skip_meld_refresh": False,
            "fast_path": False,
            "reason": "disabled",
            "predicted_ms_saved": 0,
        }

    state = panel_state()
    plates = plate_fingerprint()
    corpus = _corpus_fingerprint()
    cur_plate = str(plates.get("plate_hash") or "")
    cur_corpus = str(corpus.get("corpus_hash") or "")
    prev_plate = str(state.get("plate_hash") or "")
    prev_corpus = str(state.get("corpus_hash") or "")

    base: dict[str, Any] = {
        "schema": "field-predictive-meld/v1",
        "updated": _now(),
        "plate_hash": cur_plate,
        "corpus_hash": cur_corpus,
        "prev_plate_hash": prev_plate or None,
        "prev_corpus_hash": prev_corpus or None,
        "plate_count": plates.get("plate_count"),
        "predicted_ms_saved": round(float(state.get("avg_refresh_ms") or 50.0), 3),
    }

    if not prev_plate:
        return {
            **base,
            "skip_refresh": False,
            "skip_meld_refresh": False,
            "fast_path": False,
            "reason": "initial",
            "predicted_ms_saved": 0,
        }

    if cur_plate != prev_plate:
        return {
            **base,
            "skip_refresh": False,
            "skip_meld_refresh": False,
            "fast_path": False,
            "reason": "plate_changed",
            "predicted_ms_saved": 0,
        }

    if cur_corpus != prev_corpus:
        return {
            **base,
            "skip_refresh": False,
            "skip_meld_refresh": False,
            "fast_path": False,
            "reason": "corpus_changed",
            "predicted_ms_saved": 0,
        }

    saved = base["predicted_ms_saved"]
    return {
        **base,
        "skip_refresh": True,
        "skip_meld_refresh": True,
        "fast_path": True,
        "reason": "predictive_stable",
        "stable": True,
        "statement": "Plates + corpus unchanged — predictive skip refresh storm.",
        "predicted_ms_saved": saved,
    }


def merge_balance_gate(gate: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    """Combine combinatoric balance gate with predictive meld for another fast path."""
    if force or not _enabled():
        return gate
    doctrine = _load(DOCTRINE, {})
    if not (doctrine.get("policy") or {}).get("combine_with_balance_gate", True):
        return gate

    pred = predictive_meld(force=False)
    out = dict(gate)
    out["predictive_meld"] = pred
    if pred.get("skip_refresh") and pred.get("fast_path"):
        if not out.get("reorganize"):
            out["fast_path"] = True
            out["skip_reorganize"] = True
            if out.get("reason") in ("balanced_hold", "predictive_meld_hold", None, ""):
                out["reason"] = "predictive_meld_hold"
        elif out.get("reason") == "balanced_hold":
            out["predictive_skip_meld_only"] = True
    return out


def record_meld_cycle(
    *,
    refreshed_plates: bool,
    elapsed_ms: float,
    plate_hash: str = "",
    corpus_hash: str = "",
) -> dict[str, Any]:
    """Update predictive panel after a meld cycle."""
    state = panel_state()
    plates = plate_fingerprint() if not plate_hash else {"plate_hash": plate_hash}
    corpus = _corpus_fingerprint() if not corpus_hash else {"corpus_hash": corpus_hash}
    cycles = int(state.get("cycles") or 0) + 1
    skip_count = int(state.get("skip_count") or 0) + (0 if refreshed_plates else 1)
    refresh_count = int(state.get("refresh_count") or 0) + (1 if refreshed_plates else 0)
    fast_path_count = int(state.get("fast_path_count") or 0) + (0 if refreshed_plates else 1)

    def _avg(prev: float, count: int, sample: float) -> float:
        if count <= 0:
            return round(sample, 3)
        total_prev = prev * max(0, count - 1)
        return round((total_prev + sample) / count, 3)

    avg_refresh = _avg(float(state.get("avg_refresh_ms") or 0), refresh_count, elapsed_ms) if refreshed_plates else float(state.get("avg_refresh_ms") or 0)
    avg_skip = _avg(float(state.get("avg_skip_ms") or 0), skip_count, elapsed_ms) if not refreshed_plates else float(state.get("avg_skip_ms") or 0)

    panel = {
        "schema": "field-predictive-meld-panel/v1",
        "updated": _now(),
        "plate_hash": str(plates.get("plate_hash") or plate_hash),
        "corpus_hash": str(corpus.get("corpus_hash") or corpus_hash),
        "cycles": cycles,
        "skip_count": skip_count,
        "refresh_count": refresh_count,
        "fast_path_count": fast_path_count,
        "last_refreshed_plates": refreshed_plates,
        "last_elapsed_ms": round(elapsed_ms, 3),
        "avg_refresh_ms": avg_refresh,
        "avg_skip_ms": avg_skip,
        "predictive_meld": True,
        "statement": "predictive_stable_hold" if not refreshed_plates else "predictive_refresh_recorded",
    }
    _save(PANEL, panel)
    return panel


def panel() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    state = panel_state()
    pred = predictive_meld(force=False)
    return {
        "schema": "field-predictive-meld-panel/v1",
        "updated": _now(),
        "ok": True,
        "motto": doctrine.get("motto"),
        "policy": doctrine.get("policy"),
        "enabled": _enabled(),
        **state,
        "prediction": pred,
        "fingerprint": plate_fingerprint(),
        "fast_path_ms_target": FAST_PATH_MS,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    force = "--force" in sys.argv
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("predict", "should", "gate"):
        print(json.dumps(predictive_meld(force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd == "fingerprint":
        print(json.dumps(plate_fingerprint(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        pred = predictive_meld(force=False)
        ok = pred.get("schema") == "field-predictive-meld/v1"
        print(json.dumps({"ok": ok, "prediction": pred}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    if cmd == "record" and "--refresh" in sys.argv:
        ms = 0.0
        for i, arg in enumerate(sys.argv):
            if arg == "--ms" and i + 1 < len(sys.argv):
                try:
                    ms = float(sys.argv[i + 1])
                except ValueError:
                    ms = 0.0
        print(json.dumps(record_meld_cycle(refreshed_plates=True, elapsed_ms=ms), ensure_ascii=False, indent=2))
        return 0
    if cmd == "record" and "--skip" in sys.argv:
        ms = 0.0
        for i, arg in enumerate(sys.argv):
            if arg == "--ms" and i + 1 < len(sys.argv):
                try:
                    ms = float(sys.argv[i + 1])
                except ValueError:
                    ms = 0.0
        print(json.dumps(record_meld_cycle(refreshed_plates=False, elapsed_ms=ms), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["panel", "predict", "fingerprint", "verify", "record --refresh|--skip [--ms N]"],
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())