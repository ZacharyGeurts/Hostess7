#!/usr/bin/env python3
"""AmmoCode security management — MITM pins, session proofs, connection hardening."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PINS_PATH = ROOT / "data" / "security-pins.json"
DOCTRINE_PATH = ROOT / "data" / "ammocode-security-doctrine.json"

_SESSIONS: dict[str, dict[str, Any]] = {}


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_json(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _doctrine() -> dict[str, Any]:
    return _load_json(DOCTRINE_PATH, {})


def beacon_fingerprint(beacon: dict[str, Any]) -> str:
    """Stable SHA256 over identity fields — detects MITM beacon substitution."""
    keys = ("ammocode", "version", "service", "port", "tunnel_inbox", "http_tunnel")
    body = {k: beacon.get(k) for k in keys if beacon.get(k) is not None}
    ips = sorted(str(x) for x in (beacon.get("ips") or []))
    if ips:
        body["ips"] = ips
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _pins_doc() -> dict[str, Any]:
    doc = _load_json(PINS_PATH, {"pins": {}, "schema": "ammocode-security-pins/v1"})
    doc.setdefault("pins", {})
    return doc


def pin_get(host: str) -> dict[str, Any] | None:
    h = host.lower().strip()
    return (_pins_doc().get("pins") or {}).get(h)


def pin_set(host: str, fingerprint: str, *, label: str = "", source: str = "operator") -> dict[str, Any]:
    h = host.lower().strip()
    doc = _pins_doc()
    doc["pins"][h] = {
        "fingerprint": fingerprint,
        "label": label or h,
        "pinned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": source,
    }
    _save_json(PINS_PATH, doc)
    return {"ok": True, "host": h, "fingerprint": fingerprint}


def pin_remove(host: str) -> dict[str, Any]:
    h = host.lower().strip()
    doc = _pins_doc()
    doc["pins"].pop(h, None)
    _save_json(PINS_PATH, doc)
    return {"ok": True, "removed": h}


def verify_beacon(host: str, beacon: dict[str, Any] | None) -> dict[str, Any]:
    """MITM check — mismatch blocks; first-seen records TOFU pin when allowed."""
    h = host.lower().strip()
    if not beacon or not beacon.get("ammocode"):
        return {
            "ok": False,
            "mitm_risk": "high",
            "pin_status": "no_beacon",
            "verdict": "BEACON_MISSING",
            "permit": False,
        }
    fp = beacon_fingerprint(beacon)
    existing = pin_get(h)
    pol = (_doctrine().get("mitm") or {})
    tofu = pol.get("tofu_pin_on_first_trusted", True)
    if not existing:
        if tofu:
            pin_set(h, fp, source="tofu_first_seen")
            return {
                "ok": True,
                "mitm_risk": "low",
                "pin_status": "tofu_pinned",
                "fingerprint": fp,
                "verdict": "TOFU_PINNED",
                "permit": True,
            }
        return {
            "ok": True,
            "mitm_risk": "medium",
            "pin_status": "unpinned",
            "fingerprint": fp,
            "verdict": "UNPINNED",
            "permit": True,
        }
    if existing.get("fingerprint") == fp:
        return {
            "ok": True,
            "mitm_risk": "none",
            "pin_status": "match",
            "fingerprint": fp,
            "verdict": "PIN_MATCH",
            "permit": True,
        }
    return {
        "ok": False,
        "mitm_risk": "critical",
        "pin_status": "mismatch",
        "expected": existing.get("fingerprint"),
        "got": fp,
        "verdict": "MITM_SUSPECT",
        "permit": False,
        "message": f"Beacon fingerprint mismatch for {h} — possible MITM",
    }


def room_secret() -> str:
    return secrets.token_hex(16)


def session_proof(room_secret: str, peer_id: str, invite_hash: str) -> str:
    msg = f"{peer_id}:{invite_hash}".encode("utf-8")
    return hmac.new(room_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:24]


def verify_session_proof(room_secret: str, peer_id: str, invite_hash: str, proof: str) -> bool:
    if not proof or not room_secret:
        return False
    expected = session_proof(room_secret, peer_id, invite_hash)
    return hmac.compare_digest(expected, proof[:24])


def frame_mac_peer(session_proof: str, frame_id: str) -> str:
    msg = f"frame:{frame_id}".encode("utf-8")
    return hmac.new(session_proof.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:16]


def verify_frame_mac_peer(session_proof: str, frame_id: str, mac: str) -> bool:
    if not mac or not session_proof:
        return False
    return hmac.compare_digest(frame_mac_peer(session_proof, frame_id), mac[:16])


def security_status() -> dict[str, Any]:
    doc = _pins_doc()
    return {
        "ok": True,
        "doctrine": _doctrine(),
        "pins": doc.get("pins") or {},
        "pin_count": len(doc.get("pins") or {}),
        "active_sessions": len(_SESSIONS),
    }


def register_session(session_id: str, meta: dict[str, Any]) -> None:
    _SESSIONS[session_id] = {**meta, "created": time.time()}


def revoke_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)