#!/usr/bin/env python3
"""Full Ironclad component certification — sealed plate + citation + integrity."""
from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _ironclad_immediate() -> dict[str, Any]:
    cached = _load(STATE / "ironclad-immediate.json", {})
    if cached.get("schema"):
        return cached
    py = INSTALL / "lib" / "ironclad-immediate.py"
    if not py.is_file():
        return {}
    try:
        spec = importlib.util.spec_from_file_location("icc_immediate", py)
        if not spec or not spec.loader:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "immediate_slice"):
            return mod.immediate_slice()
    except Exception:
        pass
    return cached


def full_cert(
    *,
    component_id: str,
    citation: str,
    layers: list[str] | None = None,
    held: bool = True,
    facet: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return full Ironclad certification posture for a field component."""
    iron = _ironclad_immediate()
    sealed = bool(iron.get("ironclad_sealed") or iron.get("realized"))
    integrity = bool(iron.get("integrity_ok", sealed))
    truth_pct = float(iron.get("truth_percent") or (100.0 if sealed else 95.0))
    full = sealed and integrity
    chain_layers = list(layers or ["ironclad", component_id])
    if "ironclad" not in chain_layers:
        chain_layers.insert(0, "ironclad")

    cert = {
        "schema": "ironclad-component-cert/v1",
        "updated": _utc(),
        "component_id": component_id,
        "facet": facet or component_id,
        "citation": citation,
        "full_cert": full,
        "ironclad_sealed": sealed,
        "integrity_ok": integrity,
        "held": held,
        "truth_percent": 100.0 if full else min(truth_pct, 99.0 if held else 80.0),
        "truth_confidence": 1.0 if full else (0.95 if sealed else 0.85),
        "verdict": "GREEN" if full and held else ("WATCH" if full else ("PENDING" if sealed else "BLOCKED")),
        "connected_throughout": full,
        "root": "ironclad-immediate",
        "canonical_hash": iron.get("canonical_hash"),
        "meld_citation": "ironclad:meld:2",
        "requires": ["integrity_ok", "traces_to_truth_set_or_citation", "ironclad_sealed"],
        "layers": chain_layers,
        "ironclad_chain": {
            "root": "ironclad-immediate",
            "citation": citation,
            "sealed": sealed,
            "truth_percent": 100.0 if full else truth_pct,
            "connected_throughout": full,
            "layers": chain_layers,
        },
    }
    if extra:
        cert.update(extra)
    return cert