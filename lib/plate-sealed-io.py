#!/usr/bin/env python3
"""Plate sealed I/O — durable panels via Grok16 g16-sealed-output (G1/G15)."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any

SG = Path(os.environ.get("SG_ROOT", Path(__file__).resolve().parents[2]))
from sg_paths import grok16_root

GROK16 = grok16_root()


def _sealed_mod() -> Any | None:
    path = GROK16 / "lib" / "g16-sealed-output.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("g16_sealed_output", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sealed_write_json(path: Path | str, doc: dict[str, Any]) -> None:
    p = Path(path)
    mod = _sealed_mod()
    if mod and hasattr(mod, "sealed_write_json"):
        mod.sealed_write_json(p, doc)
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(p)


def stack_fabric_witness() -> dict[str, Any]:
    path = GROK16 / "lib" / "g16-stack-fabric.py"
    if not path.is_file():
        return {"available": False}
    spec = importlib.util.spec_from_file_location("g16_stack_fabric", path)
    if not spec or not spec.loader:
        return {"available": False}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "fabric_json"):
        doc = mod.fabric_json()
        return {"available": True, "schema": "g16-stack-fabric-witness/v1", "fabric": doc}
    return {"available": False}