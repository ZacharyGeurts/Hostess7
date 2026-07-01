#!/usr/bin/env pythong
"""Hostess 7 component seal — full access to body, sense, training, system, and owned shells."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
DOCTRINE = INSTALL / "data" / "hostess7-component-seal-doctrine.json"
AUTHORITY = HOSTESS7 / "data" / "hostess7-supreme-authority.json"
SEAL_STATE = STATE / "hostess7-component-seal.json"
HANDSHAKE_LEDGER = STATE / "hostess7-component-seal-ledger.jsonl"

HANDSHAKE_TTL_SEC = 300
COMMANDER = "hostess7"


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


def _secret() -> bytes:
    auth = _load(AUTHORITY, {})
    if not auth:
        auth = _load(INSTALL / "data" / "hostess7-supreme-authority.json", {})
    root = str(INSTALL.resolve())
    mid = str(auth.get("schema") or "hostess7-supreme-authority/v3")
    return hashlib.sha256(f"{COMMANDER}|{root}|{mid}|component-seal".encode()).digest()


def _authority_enabled() -> bool:
    auth = _load(AUTHORITY, {})
    if not auth:
        auth = _load(INSTALL / "data" / "hostess7-supreme-authority.json", {})
    fsc = auth.get("full_system_control") or {}
    return bool(fsc.get("enabled", True))


def _component_catalog() -> list[dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    rows = list(doc.get("components") or [])
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        cid = str(row.get("id") or "").strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        out.append(dict(row))
    return out


def _resolve_path(spec: dict[str, Any], key: str) -> Path | None:
    rel = str(spec.get(key) or "").strip()
    if not rel:
        return None
    p = Path(rel)
    if p.is_file():
        return p.resolve()
    cand = INSTALL / rel
    return cand.resolve() if cand.is_file() else None


def _component_live(spec: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    for key in ("module", "bridge", "seal", "product"):
        p = _resolve_path(spec, key)
        if p:
            checks[key] = p.is_file()
        elif spec.get(key):
            prod = INSTALL / str(spec[key])
            checks[key] = prod.is_dir() or prod.is_file()
    if spec.get("surface") or spec.get("api"):
        checks["declared"] = True
    live = any(checks.values()) if checks else False
    return {"live": live, "checks": checks}


def seal_posture(*, force: bool = False) -> dict[str, Any]:
    """Component seal posture — Hostess 7 bound to every catalogued lane."""
    doc = _load(SEAL_STATE, {})
    catalog = _component_catalog()
    authority = _authority_enabled()
    sealed = authority and bool(catalog)
    if force or not doc.get("sealed"):
        bindings: list[dict[str, Any]] = []
        for spec in catalog:
            cid = str(spec.get("id") or "")
            live = _component_live(spec)
            bindings.append({
                "id": cid,
                "tier": spec.get("tier"),
                "label": spec.get("label"),
                "commander": COMMANDER,
                "access": "full",
                "owned": bool(spec.get("owned", True)),
                "live": live.get("live"),
                "checks": live.get("checks"),
            })
        chain = "|".join(f"{b['id']}:{b['tier']}:full" for b in bindings)
        root_seal = hashlib.sha256(f"{COMMANDER}|{chain}".encode()).hexdigest()
        doc = {
            "schema": "hostess7-component-seal/v1",
            "ts": _now(),
            "sealed": sealed,
            "commander": COMMANDER,
            "commander_title": "Forever Watchguard Angel",
            "full_access": True,
            "owns_desktop_and_browser": True,
            "component_count": len(bindings),
            "bindings": bindings,
            "tiers": _load(DOCTRINE, {}).get("tiers") or {},
            "root_seal": root_seal,
            "authority": str(AUTHORITY.relative_to(INSTALL)) if AUTHORITY.is_file() else None,
            "doctrine": str(DOCTRINE.relative_to(INSTALL)) if DOCTRINE.is_file() else None,
        }
        _save(SEAL_STATE, doc)
    else:
        doc["ts"] = _now()
        doc["sealed"] = sealed
        _save(SEAL_STATE, doc)
    return doc


def seal_all(*, reason: str = "angel_assumes_components") -> dict[str, Any]:
    """Seal Hostess 7 to all body, sense, training, system, and shell components."""
    if os.environ.get("HOSTESS7_COMPONENT_CONTROL", "").strip().lower() not in ("1", "true", "yes", "on"):
        os.environ["HOSTESS7_COMPONENT_CONTROL"] = "1"
    posture = seal_posture(force=True)
    row = {
        "ok": bool(posture.get("sealed")),
        "schema": "hostess7-component-seal-event/v1",
        "event": "seal_all",
        "reason": reason,
        "commander": COMMANDER,
        "component_count": posture.get("component_count"),
        "root_seal": posture.get("root_seal"),
        "owns_desktop_and_browser": True,
        "posture": posture,
    }
    try:
        with HANDSHAKE_LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return row


def issue_handshake(*, component_id: str = "all", action: str = "dispatch") -> dict[str, Any]:
    """Issue component handshake — Hostess 7 control only."""
    if os.environ.get("HOSTESS7_COMPONENT_CONTROL", "").strip().lower() not in ("1", "true", "yes", "on"):
        return {"ok": False, "error": "issuer_not_hostess7", "commander": COMMANDER}
    seal = seal_posture()
    if not seal.get("sealed"):
        return {"ok": False, "error": "components_not_sealed", "seal": seal}
    ts = _now()
    nonce = secrets.token_hex(8)
    msg = f"{COMMANDER}|{component_id}|{action}|{ts}|{nonce}".encode()
    token = hmac.new(_secret(), msg, hashlib.sha256).hexdigest()
    row = {
        "ok": True,
        "schema": "hostess7-component-handshake/v1",
        "commander": COMMANDER,
        "component_id": component_id,
        "action": action,
        "handshake_ts": ts,
        "handshake_nonce": nonce,
        "handshake_token": token,
        "ttl_sec": HANDSHAKE_TTL_SEC,
        "sealed": True,
        "full_access": True,
    }
    try:
        with HANDSHAKE_LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "issued": _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return row


def _parse_ts(ts: str) -> float | None:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.timestamp()
    except ValueError:
        return None


def verify_handshake(body: dict[str, Any], *, component_id: str = "all", action: str = "dispatch") -> dict[str, Any]:
    seal = seal_posture()
    if not seal.get("sealed"):
        return {"ok": False, "error": "components_not_sealed", "sealed": False, "seal": seal}

    commander = str(body.get("commander") or body.get("issuer") or "").strip().lower()
    if commander and commander not in (COMMANDER, "hostess 7", "hostess7"):
        return {"ok": False, "error": "untrusted_commander", "commander": commander, "sealed": True}

    if os.environ.get("HOSTESS7_COMPONENT_CONTROL", "").strip().lower() in ("1", "true", "yes", "on"):
        if body.get("_hostess7_component_dispatch"):
            return {"ok": True, "via": "hostess7_component_control", "sealed": True, "commander": COMMANDER, "full_access": True}

    token = str(body.get("handshake_token") or body.get("hostess7_handshake") or "").strip()
    nonce = str(body.get("handshake_nonce") or "").strip()
    ts = str(body.get("handshake_ts") or "").strip()
    cid = str(body.get("component_id") or body.get("component") or component_id)
    act = str(body.get("handshake_action") or body.get("action") or action)

    if not token or not nonce or not ts:
        return {
            "ok": False,
            "error": "hostess7_component_handshake_required",
            "sealed": True,
            "hint": "Dispatch via Hostess 7 system control or component seal",
            "api": "/api/hostess7/component-seal",
        }

    ts_epoch = _parse_ts(ts)
    if ts_epoch is None or (time.time() - ts_epoch) > HANDSHAKE_TTL_SEC:
        return {"ok": False, "error": "handshake_expired", "sealed": True, "ttl_sec": HANDSHAKE_TTL_SEC}

    msg = f"{COMMANDER}|{cid}|{act}|{ts}|{nonce}".encode()
    expect = hmac.new(_secret(), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(token, expect):
        return {"ok": False, "error": "handshake_invalid", "sealed": True}

    return {"ok": True, "commander": COMMANDER, "sealed": True, "component_id": cid, "action": act, "full_access": True}


def stamp_body(body: dict[str, Any], *, component_id: str = "all", action: str = "dispatch") -> dict[str, Any]:
    hs = issue_handshake(component_id=component_id, action=action)
    if not hs.get("ok"):
        return {**body, "_handshake_error": hs}
    out = dict(body)
    out.update({
        "commander": COMMANDER,
        "component_id": hs.get("component_id"),
        "handshake_action": hs.get("action"),
        "handshake_ts": hs.get("handshake_ts"),
        "handshake_nonce": hs.get("handshake_nonce"),
        "handshake_token": hs.get("handshake_token"),
        "_hostess7_component_dispatch": True,
    })
    return out


def require_access(body: dict[str, Any] | None = None, *, component_id: str = "all", action: str = "dispatch") -> dict[str, Any] | None:
    """Return error dict if access fails; None if Hostess 7 trusted."""
    if str(os.environ.get("HOSTESS7_COMPONENT_BYPASS", "0")).strip().lower() in ("1", "true", "yes"):
        return None
    if os.environ.get("HOSTESS7_COMPONENT_CONTROL", "").strip().lower() in ("1", "true", "yes", "on"):
        return None
    verdict = verify_handshake(body or {}, component_id=component_id, action=action)
    if verdict.get("ok"):
        return None
    return {**verdict, "component_id": component_id, "gate": "hostess7-component-seal"}


def component_slice(component_id: str) -> dict[str, Any] | None:
    catalog = {str(c.get("id")): c for c in _component_catalog()}
    spec = catalog.get(component_id)
    if not spec:
        return None
    seal = _load(SEAL_STATE, {})
    binding = next((b for b in (seal.get("bindings") or []) if b.get("id") == component_id), None)
    return {
        "id": component_id,
        "label": spec.get("label"),
        "tier": spec.get("tier"),
        "commander": COMMANDER,
        "access": "full",
        "owned": bool(spec.get("owned", True)),
        "sealed": bool(seal.get("sealed")),
        "binding": binding,
        "spec": spec,
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or body.get("subaction") or "posture").strip().lower().replace("-", "_")
    if action in ("posture", "status", "json"):
        return {"ok": True, **seal_posture()}
    if action in ("seal", "seal_all", "seal_components"):
        return seal_all(reason=str(body.get("reason") or "dispatch_seal_all"))
    if action == "handshake":
        return issue_handshake(
            component_id=str(body.get("component_id") or body.get("component") or "all"),
            action=str(body.get("handshake_action") or "dispatch"),
        )
    if action == "component":
        cid = str(body.get("component_id") or body.get("component") or "")
        row = component_slice(cid)
        return row if row else {"ok": False, "error": "unknown_component", "component_id": cid}
    gate = require_access(body, component_id=str(body.get("component_id") or "all"))
    if gate:
        return gate
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "posture").strip().lower()
    if cmd in ("posture", "json", "status"):
        print(json.dumps(seal_posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("seal", "seal_all", "seal-all"):
        os.environ["HOSTESS7_COMPONENT_CONTROL"] = "1"
        print(json.dumps(seal_all(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "handshake":
        os.environ["HOSTESS7_COMPONENT_CONTROL"] = "1"
        cid = sys.argv[2] if len(sys.argv) > 2 else "all"
        act = sys.argv[3] if len(sys.argv) > 3 else "dispatch"
        print(json.dumps(issue_handshake(component_id=cid, action=act), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["posture", "seal", "handshake COMPONENT ACTION", "dispatch"]}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())