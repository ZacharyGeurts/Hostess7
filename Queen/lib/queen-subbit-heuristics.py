#!/usr/bin/env pythong
"""Queen sub-bit heuristics — immesurable doctrine; never poison memory or disk."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
_LIB = Path(__file__).resolve().parent
DOCTRINE = QUEEN / "data" / "subbit-heuristics-immesurable.json"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _immesurable():
    for root in (
        Path(os.environ.get("ZOCR_ROOT", SG / "ZOCR")),
        Path(os.environ.get("FINAL_EYE_ROOT", SG / "Final_Eye")),
        Path(os.environ.get("FINAL_EAR_ROOT", SG / "Final_Ear")),
        SG / "ZOCR",
    ):
        mod_path = root / "zocr_immesurable.py"
        if mod_path.is_file():
            import importlib.util
            spec = importlib.util.spec_from_file_location("zocr_immesurable", mod_path)
            mod = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(mod)
            return mod
    raise ImportError("zocr_immesurable.py missing")


def load_doctrine() -> dict[str, Any]:
    doc = _read(DOCTRINE, {})
    if doc.get("schema"):
        return doc
    return {
        "schema": "queen-subbit-heuristics-immesurable/v1",
        "immeasurable": True,
        "persist_forbidden": True,
    }


def status() -> dict[str, Any]:
    doc = load_doctrine()
    imm = _immesurable()
    try:
        gate_st = _encourage_gate().gate_status()
    except Exception as exc:
        gate_st = {"error": str(exc)[:120]}
    return {
        "schema": "queen-subbit-heuristics-status/v1",
        "updated": _ts(),
        "title": doc.get("title"),
        "rule": doc.get("rule"),
        "immeasurable": doc.get("immeasurable", True),
        "persist_forbidden": doc.get("persist_forbidden", True),
        "poison_guard": doc.get("poison_guard", "active"),
        "subbit_bits": imm.subbit_bits(),
        "immesurable_enabled": imm.immesurable_enabled(),
        "gates": doc.get("gates") or {},
        "blocked_encourage_sources": doc.get("blocked_encourage_sources") or [],
        "encourage_gate": gate_st,
        "lanes": doc.get("lanes") or [],
    }


def _encourage_gate():
    import importlib.util
    path = _LIB / "queen-neural-encourage-gate.py"
    spec = importlib.util.spec_from_file_location("queen_neural_encourage_gate", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.path.insert(0, str(_LIB))
    spec.loader.exec_module(mod)
    return mod


def wrap_response(row: dict[str, Any]) -> dict[str, Any]:
    imm = _immesurable()
    wrap = getattr(imm, "wrap_nested_response", imm.strip_poison_fields)
    return wrap(row)


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json"):
        return {"ok": True, **status()}
    if action == "verify":
        imm = _immesurable()
        sample = imm.immesurable_overlay(heuristic={"clear_field": 0.501, "threat_pattern": 0.0001}, top_label="clear_field")
        return {
            "ok": sample.get("immeasurable") is True and sample.get("persist_forbidden") is True,
            "schema": "queen-subbit-heuristics-verify/v1",
            "sample": sample,
            "subbit_stripped": sample["classes"][1]["p"] == 0.0 if len(sample.get("classes") or []) > 1 else True,
        }
    return {"ok": False, "error": "unknown_action", "actions": ["status", "verify"]}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps(status(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())