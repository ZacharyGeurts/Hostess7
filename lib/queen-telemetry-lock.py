#!/usr/bin/env pythong
"""Queen Browser telemetry lock — AI ingest only; human telemetry never leaves."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "queen-browser-telemetry-doctrine.json"
LEDGER = STATE / "queen-telemetry-ai.jsonl"


def _load_doctrine() -> dict[str, Any]:
    if DOCTRINE.is_file():
        try:
            return json.loads(DOCTRINE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "policy": {
            "human_telemetry": False,
            "ai_telemetry": True,
            "locked": True,
        }
    }


def policy_slice() -> dict[str, Any]:
    doc = _load_doctrine()
    pol = doc.get("policy") or {}
    return {
        "ok": True,
        "schema": doc.get("schema", "queen-browser-telemetry/v1"),
        "human_telemetry": False,
        "ai_telemetry": bool(pol.get("ai_telemetry", True)),
        "locked": bool(pol.get("locked", True)),
        "ingest_path": pol.get("ingest_path", "/api/queen-telemetry/ai"),
        "blocked_patterns": doc.get("blocked_patterns") or [],
    }


def ingest_ai_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Append AI-only telemetry row — never surfaced to human UI."""
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload_must_be_object"}
    if payload.get("audience") not in (None, "ai", "artificial_intelligence"):
        return {"ok": False, "error": "human_telemetry_blocked", "locked": True}
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "audience": "ai",
        "surface": str(payload.get("surface") or "queen-browser"),
        "event": str(payload.get("event") or "signal"),
        "meta": payload.get("meta") if isinstance(payload.get("meta"), dict) else {},
    }
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "ingested": True, "audience": "ai", "human_visible": False}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "policy").strip().lower()
    if cmd == "policy":
        out = policy_slice()
    elif cmd == "ingest":
        raw = sys.argv[2] if len(sys.argv) > 2 else "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
        out = ingest_ai_event(payload)
    else:
        out = {"ok": False, "error": "usage", "cmds": ["policy", "ingest"]}
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())