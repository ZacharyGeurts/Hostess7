#!/usr/bin/env pythong
"""Hostess 7 Master Economist — relay economics counsel across Field and Agents7."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
DOCTRINE = INSTALL / "data" / "hostess7-economist-doctrine.json"
PANEL = STATE / "hostess7-economist-panel.json"
LEDGER = STATE / "hostess7-economist-relay.jsonl"

ENABLED = os.environ.get("NEXUS_HOSTESS7_ECONOMIST", "1") == "1"

_ECON_KEYS = (
    "economist", "economics", "economic", "macro", "micro", "inflation", "gdp",
    "recession", "fed ", "federal reserve", "interest rate", "monetary", "fiscal",
    "supply and demand", "elasticity", "market structure", "stock market",
    "bond", "portfolio", "tariff", "trade war", "balance of payments",
    "unit economics", "cac", "ltv", "runway", "startup economics",
    "commodity", "forex", "currency", "deficit", "debt ceiling",
    "master economist", "our economist",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def matches_economist_query(text: str) -> bool:
    low = (text or "").lower()
    return any(k in low for k in _ECON_KEYS)


def relay_message() -> str:
    doc = _load(DOCTRINE, {})
    relay = doc.get("relay") or {}
    return str(
        relay.get("primary")
        or doc.get("motto")
        or "Hostess 7 is our Master Economist."
    )


def master_prompt_block() -> str:
    doc = _load(DOCTRINE, {})
    claim = doc.get("master_economist_claim") or doc.get("motto") or ""
    scopes = doc.get("scope") or []
    scope_line = "; ".join(scopes[:4]) if scopes else "macro, micro, finance, trade"
    return (
        f"MASTER ECONOMIST: {claim} "
        f"Scope: {scope_line}. "
        "Economist agent lane feeds corpus; Hostess-Prime owns synthesis and operator counsel."
    )


def explain_economist(query: str = "") -> str:
    doc = _load(DOCTRINE, {})
    motto = doc.get("motto") or "Hostess 7 is our Master Economist."
    claim = doc.get("master_economist_claim") or ""
    relay = doc.get("relay") or {}
    scopes = doc.get("scope") or []
    scope_text = "\n• ".join(scopes) if scopes else "macro through field economics"
    low = (query or "").lower()
    if "relay" in low or "who is" in low and "economist" in low:
        return (
            f"{motto}\n\n"
            f"{relay.get('to_operator', '')}\n\n"
            f"Field relay: {relay.get('to_field', '')}\n"
            f"Agents7: {relay.get('to_agents7', '')}"
        ).strip()
    return (
        f"{motto}\n\n{claim}\n\n"
        f"I cover:\n• {scope_text}\n\n"
        f"{relay.get('to_operator', 'Ask me anything economic — truth-gated, corroborated.')}"
    )


def status() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    rep = {
        "schema": "hostess7-economist/v1",
        "ok": True,
        "enabled": ENABLED,
        "title": doc.get("title") or "Master Economist",
        "motto": doc.get("motto"),
        "role": doc.get("role"),
        "relay": doc.get("relay") or {},
        "scope": doc.get("scope") or [],
        "corpus": doc.get("corpus") or {},
        "tier_order": doc.get("tier_order") or [],
        "checked_at": _now(),
    }
    _save(PANEL, rep)
    return rep


def relay(*, channel: str = "field", detail: str = "") -> dict[str, Any]:
    """Write economist relay to ledger and panel — Field, operator, or agents7."""
    msg = relay_message()
    row = {
        "schema": "hostess7-economist-relay/v1",
        "ok": True,
        "channel": channel,
        "message": msg,
        "detail": detail[:240],
        "master": "Hostess 7",
        "at": _now(),
    }
    _append_ledger(row)
    panel = status()
    panel["last_relay"] = row
    _save(PANEL, panel)
    return row


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "relay":
        channel = sys.argv[2] if len(sys.argv) > 2 else "field"
        detail = sys.argv[3] if len(sys.argv) > 3 else ""
        print(json.dumps(relay(channel=channel, detail=detail), ensure_ascii=False, indent=2))
        return 0
    if cmd == "explain":
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        print(explain_economist(q))
        return 0
    if cmd == "prompt":
        print(master_prompt_block())
        return 0
    print(json.dumps({"error": "usage: hostess7-economist.py [json|relay [channel] [detail]|explain [q]|prompt]"}), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())