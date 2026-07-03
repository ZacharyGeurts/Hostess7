#!/usr/bin/env python3
"""Botnet legal port auto-allow — IANA civilian egress; non-safe flows require H7t truth witness."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-botnet-legal-ports-doctrine.json"
PANEL = STATE / "field-botnet-legal-ports-panel.json"

_h7t_mod: Any = None


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _h7t() -> Any:
    global _h7t_mod
    if _h7t_mod is not None:
        return _h7t_mod
    import importlib.util
    path = INSTALL / "lib" / "field-h7t-truth.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("field_h7t_truth", path)
        if spec and spec.loader:
            _h7t_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_h7t_mod)
            return _h7t_mod
    except Exception:
        pass
    return None


def stalker_ports(doctrine: dict[str, Any] | None = None) -> frozenset[str]:
    doc = doctrine or _load(DOCTRINE, {})
    raw = (doc.get("stalker_lop") or {}).get("ports") or []
    return frozenset(str(p) for p in raw)


def context_ports(doctrine: dict[str, Any] | None = None) -> frozenset[str]:
    doc = doctrine or _load(DOCTRINE, {})
    raw = (doc.get("context_ports") or {}).get("ports") or []
    return frozenset(str(p) for p in raw)


def is_legal_port(port: int | str, *, doctrine: dict[str, Any] | None = None) -> bool:
    try:
        p = int(port)
    except (TypeError, ValueError):
        return False
    if p < 1 or p > 65535:
        return False
    ps = str(p)
    if ps in stalker_ports(doctrine):
        return False
    return True


def is_stalker_port(port: int | str, *, doctrine: dict[str, Any] | None = None) -> bool:
    return str(port) in stalker_ports(doctrine)


def is_context_port(port: int | str, *, doctrine: dict[str, Any] | None = None) -> bool:
    return str(port) in context_ports(doctrine)


def port_verdict(
    port: int | str,
    *,
    proc: str = "",
    botnet_member: bool = True,
    h7t_witness: bool = False,
    safe_stack: bool = False,
    doctrine: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return permit recommendation for a port flow."""
    doc = doctrine or _load(DOCTRINE, {})
    p = str(port)
    legal = is_legal_port(port, doctrine=doc)
    stalker = is_stalker_port(port, doctrine=doc)
    ctx = is_context_port(port, doctrine=doc)

    if stalker:
        return {
            "permit": False,
            "verdict": "HARM_CANDIDATE",
            "reason": f"stalker_lop:{p}",
            "legal": False,
            "h7t_required": False,
        }

    if safe_stack:
        return {
            "permit": True,
            "verdict": "USER_OK",
            "reason": "sovereign_safe_stack",
            "legal": legal,
            "h7t_required": False,
            "native_path": True,
        }

    if not legal:
        return {
            "permit": False,
            "verdict": "SUSPICIOUS",
            "reason": f"illegal_port:{p}",
            "legal": False,
            "h7t_required": True,
        }

    everyone = doc.get("for_everyone") or {}
    if everyone.get("auto_allow_legal") and botnet_member:
        if h7t_witness or everyone.get("civilian_passthrough"):
            return {
                "permit": True,
                "verdict": "USER_OK",
                "reason": "botnet_legal_port" if h7t_witness else "botnet_civilian_legal",
                "legal": True,
                "h7t_required": not h7t_witness,
                "h7t_witness": h7t_witness,
                "benefits_factor": 100 if h7t_witness else 1,
            }

    if ctx:
        return {
            "permit": True,
            "verdict": "MONITOR",
            "reason": f"context_port:{p}",
            "legal": True,
            "h7t_required": not safe_stack,
            "note": "dev/app server — monitor unless H7t truthed",
        }

    return {
        "permit": legal and botnet_member,
        "verdict": "MONITOR" if legal else "SUSPICIOUS",
        "reason": "iana_legal" if legal else f"blocked:{p}",
        "legal": legal,
        "h7t_required": not safe_stack,
    }


def gatekeeper_port_harm(port: str, *, proc: str = "", h7t_witness: bool = False) -> tuple[int, str]:
    """Drop-in for connection-gatekeeper _axis_destination harm scoring."""
    if is_stalker_port(port):
        return 10, "stalker_lop"
    if is_context_port(port):
        trust = 3 if proc in ("", "pid-unknown", "network-peer") else 1
        return trust, "context_port"
    if is_legal_port(port):
        if h7t_witness:
            return 0, "h7t_truthed_legal"
        return 1, "iana_legal"
    return 8, "illegal_port"


def gatekeeper_should_block_port(
    port: str,
    *,
    proc: str,
    verdict: str,
    process_trust: int,
    h7t_witness: bool = False,
) -> bool:
    if is_stalker_port(port) and process_trust <= 3:
        return True
    if is_context_port(port) and verdict == "SUSPICIOUS" and process_trust <= 3:
        return True
    if is_stalker_port(port) and verdict == "SUSPICIOUS":
        return True
    if not is_legal_port(port) and not h7t_witness:
        return verdict in ("SUSPICIOUS", "HARM_CANDIDATE")
    return False


def requires_h7t(*, path: str = "", meta: dict[str, Any] | None = None) -> bool:
    h7t = _h7t()
    if h7t and hasattr(h7t, "is_safe_asset"):
        return not h7t.is_safe_asset(path=path, meta=meta)
    return bool(path and not path.startswith("Hostess7/"))


def panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    doc = {
        "ok": True,
        "schema": "field-botnet-legal-ports-panel/v1",
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "updated": _utc(),
        "stalker_lop_count": len(stalker_ports(doctrine)),
        "context_port_count": len(context_ports(doctrine)),
        "for_everyone": doctrine.get("for_everyone") or {},
        "h7t": {
            "module": "lib/field-h7t-truth.py",
            "api": "/api/field-h7t-truth",
            "rule": "non-safe → truthed → H7t → 100× chamber benefits without sovereign interference",
        },
        "botnet": doctrine.get("botnet") or {},
        "api": "/api/field-botnet-legal-ports",
    }
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verdict" and len(sys.argv) > 2:
        port = sys.argv[2]
        h7t = "--h7t" in sys.argv
        safe = "--safe" in sys.argv
        out = port_verdict(port, h7t_witness=h7t, safe_stack=safe)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if cmd == "legal" and len(sys.argv) > 2:
        p = sys.argv[2]
        print(json.dumps({
            "port": p,
            "legal": is_legal_port(p),
            "stalker": is_stalker_port(p),
            "context": is_context_port(p),
        }, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-botnet-legal-ports.py [panel|verdict PORT|legal PORT]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())