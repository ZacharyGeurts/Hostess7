#!/usr/bin/env pythong
"""Queen PythonG API — compat alias for GrokPy field runtime."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent


def _grokpy_module():
    spec = importlib.util.spec_from_file_location("queen_grokpy", _LIB / "queen-grokpy.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def pythong_status() -> dict[str, Any]:
    st = _grokpy_module().grokpy_status()
    return {
        **st,
        "schema": "queen-pythong/v1",
        "title": "GrokPy (pythong compat) — Grok Python for Queen + Hostess 7",
        "ready_pythong": st.get("ready_grokpy"),
        "grokpy": st,
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    out = _grokpy_module().dispatch(body)
    if out.get("ok") and "status" in out:
        s = out["status"]
        out["status"] = {**s, "schema": "queen-pythong/v1", "ready_pythong": s.get("ready_grokpy")}
    elif out.get("ok") and "schema" == "queen-grokpy/v1":
        out = {**out, "schema": "queen-pythong/v1", "ready_pythong": out.get("ready_grokpy")}
    return out


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps(pythong_status(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())