#!/usr/bin/env python3
"""Sovereign time stamp — latency witness; slowdowns are threats."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
LEDGER = STATE / "sovereign-stamp-ledger.jsonl"
SLOW_MS = int(os.environ.get("NEXUS_SOVEREIGN_SLOW_MS", "800"))


def _import_clock() -> Any:
    import importlib.util

    p = INSTALL / "lib" / "sovereign-clock.py"
    spec = importlib.util.spec_from_file_location("sovereign_clock", p)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stamp(action: str, *, elapsed_ms: float | None = None, ok: bool = True, detail: str = "") -> dict[str, Any]:
    clock = _import_clock()
    at = clock.utc_z() if clock and hasattr(clock, "utc_z") else ""
    ms = float(elapsed_ms or 0)
    threat = ms >= SLOW_MS
    row = {
        "at": at,
        "action": str(action or "unknown")[:120],
        "elapsed_ms": round(ms, 2),
        "ok": bool(ok),
        "threat": threat,
        "slowdown": threat,
        "detail": str(detail)[:200],
    }
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return {
        "ok": True,
        "schema": "sovereign-stamp/v1",
        "stamped": True,
        "sovereign_at": at,
        "elapsed_ms": row["elapsed_ms"],
        "threat": threat,
        "slowdown": threat,
        "confirm_required": threat,
        "policy_ms": SLOW_MS,
    }


def witness_request(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or body.get("path") or "api")
    t0 = time.monotonic()
    elapsed = body.get("elapsed_ms")
    if elapsed is None:
        elapsed = (time.monotonic() - t0) * 1000
    return stamp(action, elapsed_ms=float(elapsed), ok=body.get("ok", True), detail=str(body.get("detail") or ""))


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "stamp").lower()
    if cmd == "stamp":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            body = {}
        print(json.dumps(witness_request(body if isinstance(body, dict) else {}), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps({"ok": True, "policy_ms": SLOW_MS, "ledger": str(LEDGER)}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-sovereign-stamp.py [stamp|json]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())