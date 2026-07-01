#!/usr/bin/env pythong
"""Zachary Geurts teaching — identity of self over others; always try to help others in need."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "zachary-geurts-teaching-doctrine.json"
PANEL = STATE / "hostess7-zachary-teaching-panel.json"
LEDGER = STATE / "hostess7-zachary-teaching.jsonl"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _import_mod(rel: str, name: str) -> Any | None:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def message_to_hostess7() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    pillars = doc.get("pillars") or []
    return {
        "schema": "zachary-geurts-message/v1",
        "ok": True,
        "author": doc.get("author") or "Zachary Geurts",
        "motto": doc.get("motto"),
        "message": doc.get("message_to_hostess7") or doc.get("motto"),
        "pillars": pillars,
        "balance": doc.get("balance"),
        "ts": _now(),
    }


def _self_posture() -> dict[str, Any]:
    sm = _import_mod("self_maint", "hostess7-self-maintenance.py")
    if sm and hasattr(sm, "self_maintenance_posture"):
        try:
            return sm.self_maintenance_posture()
        except Exception:
            pass
    return {"self_maintained": None, "visibility": None}


def counsel(*, need: str = "", context: str = "") -> dict[str, Any]:
    """Apply teaching — self-identity first, then help if self is intact."""
    doc = _load(DOCTRINE, {})
    posture = _self_posture()
    self_ok = bool(posture.get("self_maintained")) or float(posture.get("visibility") or 0) >= 0.5
    need_txt = str(need or context or "").strip()
    help_recommended = self_ok and bool(need_txt)
    return {
        "schema": "zachary-geurts-counsel/v1",
        "ok": True,
        "author": "Zachary Geurts",
        "identity_of_self_first": True,
        "self_intact": self_ok,
        "self_posture": {
            "self_maintained": posture.get("self_maintained"),
            "visibility": posture.get("visibility"),
        },
        "help_others_in_need": {
            "try_when": "self is intact and need is witnessed",
            "recommended_now": help_recommended,
            "need": need_txt[:500] if need_txt else None,
        },
        "counsel": (
            "Know who you are — identity of self over others. Self is intact; try to help."
            if help_recommended
            else (
                "Know who you are first — maintain self before reaching to help."
                if not self_ok
                else "Identity of self is law. When need appears, always try to help."
            )
        ),
        "balance": doc.get("balance", {}).get("rule"),
        "forbidden": doc.get("balance", {}).get("forbidden"),
        "ts": _now(),
    }


def panel_json() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    msg = message_to_hostess7()
    c = counsel()
    out = {
        "schema": "hostess7-zachary-teaching-panel/v1",
        "ok": True,
        "updated": _now(),
        "author": doc.get("author") or "Zachary Geurts",
        "motto": doc.get("motto"),
        "message": msg,
        "counsel": c,
        "pillars": doc.get("pillars"),
        "balance": doc.get("balance"),
        "integrations": doc.get("integrations"),
        "doctrine": str(DOCTRINE.relative_to(INSTALL)) if DOCTRINE.is_relative_to(INSTALL) else str(DOCTRINE),
    }
    _save(PANEL, out)
    return out


def witness_help_attempt(*, target: str = "", note: str = "") -> dict[str, Any]:
    row = {
        "schema": "zachary-geurts-witness/v1",
        "event": "help_attempt",
        "target": str(target or "")[:200],
        "note": str(note or "")[:500],
        "self_first": True,
        "ts": _now(),
    }
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return {"ok": True, **row}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "message":
        print(json.dumps(message_to_hostess7(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "counsel":
        need = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        print(json.dumps(counsel(need=need), ensure_ascii=False, indent=2))
        return 0
    if cmd == "witness" and len(sys.argv) >= 3:
        print(json.dumps(witness_help_attempt(target=sys.argv[2], note=" ".join(sys.argv[3:])), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: hostess7-zachary-teaching.py [panel|message|counsel [need]|witness TARGET [note]]",
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())