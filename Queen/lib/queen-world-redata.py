#!/usr/bin/env pythong
"""Queen World Redata bridge — secure forever World_Redata inside Queen capsule."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
WR = Path(os.environ.get("WORLD_REDATA_ROOT", SG / "World_Redata"))
MANDATE = QUEEN / "data" / "queen-world-redata.json"
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
CACHE = STATE / "world-redata-cache.json"
BINARY = WR / "cpp" / "build" / "world-redata"

_FAST_CACHE: dict[str, Any] | None = None
_FAST_TS = 0.0


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _queen_seal() -> dict[str, Any]:
    try:
        spec = importlib.util.spec_from_file_location("qs", QUEEN / "lib" / "queen-security.py")
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        return mod.verify_code_seal()
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}


def load_mandate() -> dict[str, Any]:
    return _load_json(MANDATE, {"schema": "queen-world-redata/v1"})


def _wrdt_cli(*args: str, timeout: int = 45) -> dict[str, Any]:
    env = {**os.environ, "PYTHONPATH": str(WR), "SG_ROOT": str(SG)}
    cli = [sys.executable, "-m", "redata.cli", *args]
    try:
        proc = subprocess.run(
            cli,
            cwd=str(WR),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**env, "GPY16_TOOLING": "1"},
        )
        out = (proc.stdout or "").strip()
        try:
            doc = json.loads(out) if out.startswith("{") else {"output": out[:4000]}
        except json.JSONDecodeError:
            doc = {"output": out[:4000], "stderr": (proc.stderr or "")[-1500:]}
        doc["returncode"] = proc.returncode
        doc["ok"] = proc.returncode == 0
        return doc
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "cmd": " ".join(args)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def world_redata_fast() -> dict[str, Any]:
    """Instant status — disk reads only, no subprocess."""
    import time

    global _FAST_CACHE, _FAST_TS
    now = time.time()
    if _FAST_CACHE and now - _FAST_TS < 12.0:
        return _FAST_CACHE
    m = load_mandate()
    seal = _queen_seal()
    ledger = _load_json(WR / "data" / "redata-ledger.json", {})
    g16 = _load_json(WR / "data" / "g16-field-mandate.json", {})
    ai = _load_json(WR / "data" / "ai-contract.json", {})
    doc = {
        "schema": "queen-world-redata/v1",
        "updated": _now(),
        "fast": True,
        "forever": True,
        "motto": m.get("motto"),
        "doctrine": m.get("doctrine") or {},
        "upstream": str(WR),
        "github": m.get("github"),
        "binary_ready": BINARY.is_file(),
        "binary": str(BINARY),
        "queen_seal_ok": seal.get("ok"),
        "ledger_entries": len((ledger.get("files") or {})),
        "g16_mandate": bool(g16),
        "ai_contract": bool(ai.get("schema")),
        "security_posture": "fail_closed" if not seal.get("ok") else "sealed",
        "hydrate": "/api/world-redata?full=1",
    }
    _FAST_CACHE = doc
    _FAST_TS = now
    _save_cache(doc)
    return doc


def _save_cache(doc: dict[str, Any]) -> None:
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps({**doc, "cached": _now()}, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def world_redata_status(*, full: bool = False) -> dict[str, Any]:
    m = load_mandate()
    seal = _queen_seal()
    if not seal.get("ok") and (m.get("doctrine") or {}).get("fail_closed_on_seal_break", True):
        return {
            "ok": False,
            "schema": "queen-world-redata/v1",
            "verdict": "SEAL_BROKEN",
            "forever": False,
            "seal": seal,
            "fast_fallback": world_redata_fast(),
        }
    base = world_redata_fast()
    if not full:
        return {"ok": True, **base}
    security = _wrdt_cli("security", timeout=60)
    mandate = _wrdt_cli("mandate", timeout=60)
    safety = _wrdt_cli("safety", timeout=20)
    return {
        "ok": True,
        **base,
        "fast": False,
        "full": True,
        "security_eval": security,
        "mandate_audit": mandate,
        "safety": safety,
        "invincibility": {
            "lossless": True,
            "bounded_io": True,
            "field_compiler": (m.get("doctrine") or {}).get("field_compiler"),
            "never_tampered": seal.get("ok"),
        },
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    full = bool(body.get("full"))
    if action in ("status", "json", "fast"):
        if action == "fast" or not full:
            return {"ok": True, **world_redata_fast()}
        return world_redata_status(full=True)
    if action in ("verify", "security"):
        seal = _queen_seal()
        if not seal.get("ok"):
            return {"ok": False, "verdict": "SEAL_BROKEN", "seal": seal}
        return {"ok": True, **world_redata_fast(), "security_eval": _wrdt_cli("security", timeout=90)}
    if action == "mandate":
        return {"ok": True, "mandate_audit": _wrdt_cli("mandate", timeout=90)}
    if action == "parity":
        return {"ok": True, "parity": _wrdt_cli("parity", timeout=120)}
    if action == "ai":
        return {"ok": True, "ai_context": _wrdt_cli("ai", timeout=45)}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(world_redata_fast(), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-world-redata.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())