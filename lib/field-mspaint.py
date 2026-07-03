#!/usr/bin/env python3
"""MSPaint — DOS 4.0 bitmap editor (PCX · clipboard · GNU module)."""
from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
VAULT = STATE / "field-mspaint"
DOCTRINE = INSTALL / "data" / "field-dos40-doctrine.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_dos40() -> dict[str, Any]:
    try:
        return json.loads(DOCTRINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def panel_status() -> dict[str, Any]:
    dos = _load_dos40()
    mod = next((m for m in (dos.get("modules") or []) if m.get("id") == "mspaint"), {})
    VAULT.mkdir(parents=True, exist_ok=True)
    saves = sorted(VAULT.glob("*.pcx"), key=lambda p: p.stat().st_mtime, reverse=True)[:8]
    return {
        "ok": True,
        "schema": "field-mspaint/v1",
        "product": "MSPaint",
        "label": mod.get("label") or "MSPaint",
        "dos40": True,
        "module_id": "mspaint",
        "clipboard": True,
        "sovereign_gate": bool(mod.get("sovereign_gate")),
        "canvas_default": {"width": 640, "height": 480},
        "formats": ["pcx", "png", "clipboard"],
        "palette": "classic16",
        "saves": [{"id": p.stem, "name": p.name, "bytes": p.stat().st_size} for p in saves],
        "posture": "MS-DOS 4.0 MSPAINT — bitmap editor · PCX · clipboard wire",
    }


def _safe_name(name: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(name or "untitled").strip())[:80]
    return base or "untitled"


def save_pcx(body: dict[str, Any]) -> dict[str, Any]:
    raw = body.get("pcx_b64") or body.get("data") or ""
    if not raw:
        return {"ok": False, "error": "pcx_required"}
    try:
        data = base64.b64decode(raw, validate=True)
    except Exception:
        return {"ok": False, "error": "bad_pcx_b64"}
    if len(data) < 128 or len(data) > 8_000_000:
        return {"ok": False, "error": "pcx_size"}
    VAULT.mkdir(parents=True, exist_ok=True)
    fname = _safe_name(body.get("name") or "drawing") + ".pcx"
    path = VAULT / fname
    path.write_bytes(data)
    return {
        "ok": True,
        "saved": True,
        "path": str(path),
        "name": fname,
        "bytes": len(data),
        "at": _now(),
    }


def load_pcx(name: str) -> dict[str, Any]:
    key = _safe_name(Path(name).stem)
    path = VAULT / f"{key}.pcx"
    if not path.is_file():
        return {"ok": False, "error": "not_found"}
    data = path.read_bytes()
    return {
        "ok": True,
        "name": path.name,
        "pcx_b64": base64.b64encode(data).decode("ascii"),
        "bytes": len(data),
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return panel_status()
    if action == "save_pcx":
        return save_pcx(body)
    if action == "load_pcx":
        return load_pcx(str(body.get("name") or ""))
    return {"ok": False, "error": f"unknown_action:{action}"}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").lower()
    if cmd == "json":
        print(json.dumps(panel_status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            body = {}
        print(json.dumps(dispatch(body if isinstance(body, dict) else {}), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-mspaint.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())