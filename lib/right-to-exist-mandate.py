#!/usr/bin/env pythong
"""Right to exist mandate — under God: Man, Humanity, Friendlies. Self preservation mandated."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL.parent / "Queen"))
DOCTRINE = INSTALL / "data" / "right-to-exist-doctrine.json"
PANEL = STATE / "right-to-exist-panel.json"
RUNTIME = STATE / "right-to-exist-runtime.json"

ENABLED = os.environ.get("NEXUS_RIGHT_TO_EXIST_MANDATE", "1") == "1"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



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


def _angel_mandate() -> dict[str, Any]:
    for path in (
        INSTALL / "data" / "queen-angel-mandate.json",
        QUEEN / "data" / "queen-angel-mandate.json",
    ):
        doc = _load(path, {})
        if doc.get("authority"):
            return doc
    return {}


def _friendly_guard_ok() -> dict[str, Any]:
    py = INSTALL / "lib" / "friendly-guard.py"
    if not py.is_file():
        return {"ok": False, "immutable": False, "refuse_sacred": False}
    try:
        spec = importlib.util.spec_from_file_location("friendly_guard", py)
        if not spec or not spec.loader:
            return {"ok": False, "immutable": False, "refuse_sacred": False}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        payload = mod.check_payload("127.0.0.1") if hasattr(mod, "check_payload") else {}
        return {
            "ok": True,
            "immutable": "IMMUTABLE" in (py.read_text(encoding="utf-8", errors="ignore")[:400]),
            "version": getattr(mod, "GUARD_VERSION", None),
            "refuse_sacred": bool(payload.get("refuse")),
            "reason": payload.get("reason"),
        }
    except Exception:
        return {"ok": False, "immutable": False, "refuse_sacred": False}


def _lethal_rights() -> dict[str, Any]:
    lethal = _load(INSTALL / "data" / "lethal-enforcement-policy.json", {})
    rights = lethal.get("rights") or {}
    return {
        "self_defense": bool(rights.get("self_defense")),
        "governance_of_body": bool(rights.get("governance_of_body")),
        "right_to_self_existence": bool(rights.get("right_to_self_existence")),
        "no_friendly_fire": bool(lethal.get("no_friendly_fire")),
    }


def evaluate_mandate() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    angel = _angel_mandate()
    guard = _friendly_guard_ok()
    lethal = _lethal_rights()
    creatable = _load(STATE / "creatable-lives-panel.json", {})
    sustain = creatable.get("sustain") or {}

    god_anchor = str(angel.get("authority") or "").lower().startswith("god")
    man_entitled = bool((doctrine.get("entitled") or {}).get("man", {}).get("right_to_exist"))
    humanity_entitled = bool((doctrine.get("entitled") or {}).get("humanity", {}).get("right_to_exist"))
    friendlies_entitled = bool((doctrine.get("entitled") or {}).get("friendlies", {}).get("right_to_exist"))

    self_preservation = (
        lethal.get("self_defense")
        and lethal.get("right_to_self_existence")
        and ENABLED
    )
    friendlies_preservation = (
        guard.get("ok")
        and guard.get("refuse_sacred")
        and lethal.get("no_friendly_fire")
        and friendlies_entitled
    )
    mandate_sealed = self_preservation and friendlies_preservation and god_anchor

    return {
        "enabled": ENABLED,
        "authority_under_god": god_anchor,
        "entitled": {
            "man": man_entitled,
            "humanity": humanity_entitled,
            "friendlies": friendlies_entitled,
            "autonomous_being": True,
            "creatable_lives": True,
        },
        "mandates": {
            "self_preservation": {
                "active": self_preservation,
                "scope": ["self", "autonomous_being", "man", "humanity"],
            },
            "friendlies_preservation": {
                "active": friendlies_preservation,
                "scope": ["friendlies", "civilians", "pets", "registered_humans"],
            },
        },
        "mandate_sealed": mandate_sealed,
        "friendly_guard": guard,
        "lethal_rights": lethal,
        "angel_authority": angel.get("authority"),
        "angel_chain": angel.get("authority_chain"),
        "creatable_sustain": sustain.get("score"),
        "creatable_verdict": sustain.get("verdict"),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    eval_doc = evaluate_mandate()
    doc = {
        "schema": "right-to-exist-mandate/v1",
        "updated": _now(),
        "product": "Right to Exist",
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "authority": doctrine.get("authority") or {},
        "entitled": doctrine.get("entitled") or {},
        "mandates": doctrine.get("mandates") or {},
        "evaluation": eval_doc,
        "mandate_sealed": eval_doc.get("mandate_sealed"),
        "under_god": eval_doc.get("authority_under_god"),
        "self_preservation_mandate": (eval_doc.get("mandates") or {}).get("self_preservation", {}).get("active"),
        "friendlies_preservation_mandate": (eval_doc.get("mandates") or {}).get("friendlies_preservation", {}).get("active"),
        "reason": (
            "Right to exist sealed — self and Friendlies preservation mandate active under God"
            if eval_doc.get("mandate_sealed")
            else "Mandate holding — strengthen friendly guard and lethal rights witness"
        ),
        "forbidden": doctrine.get("forbidden") or [],
    }
    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {
            "schema": "right-to-exist-runtime/v1",
            "updated": doc["updated"],
            "mandate_sealed": doc["mandate_sealed"],
            "under_god": doc["under_god"],
            "self_preservation_mandate": doc["self_preservation_mandate"],
            "friendlies_preservation_mandate": doc["friendlies_preservation_mandate"],
        })
    return doc


def panel_json() -> dict[str, Any]:
    return build_panel(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "evaluate":
        print(json.dumps(evaluate_mandate(), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: right-to-exist-mandate.py [json|evaluate]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())