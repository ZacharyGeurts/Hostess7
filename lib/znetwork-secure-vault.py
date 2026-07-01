#!/usr/bin/env pythong
"""ZNetwork Secure Vault — push-only ZISV/v1 peer transfer, no middleman decrypt path.

ZNetwork does not answer inbound requests. Operators send sealed offers; recipients
accept or reject from a scrollable queue. Hostile spammers are scored and handed to
znetwork-hostile-threat.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import re
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
VAULT_ROOT = STATE / "znetwork-vault"
INBOUND_DIR = VAULT_ROOT / "inbound"
OUTBOUND_DIR = VAULT_ROOT / "outbound"
ACCEPTED_DIR = VAULT_ROOT / "accepted"
BLOB_DIR = VAULT_ROOT / "blobs"
QUEUE_PATH = STATE / "znetwork-vault-queue.json"
LEDGER = STATE / "znetwork-vault-ledger.jsonl"
OPERATOR_KEY = STATE / "znetwork-vault-operator.key"
WIRE_POINT = STATE / "znetwork-vault-wire-point.json"
SCHEMA = "znetwork-secure-vault/v1"
PROTOCOL = "zisv/v1"
MAX_CHUNK = 48_000
MAX_FILE_BYTES = 32 * 1024 * 1024
SPAM_BURST = 6
SPAM_WINDOW_SEC = 60
SPAM_PENDING_CAP = 24

_MOD_CACHE: dict[str, Any] = {}


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
    os.replace(tmp, path)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _mod(py: Path, name: str) -> Any | None:
    key = str(py)
    if key in _MOD_CACHE:
        return _MOD_CACHE[key]
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _MOD_CACHE[key] = mod
    return mod


def _operator_secret() -> bytes:
    STATE.mkdir(parents=True, exist_ok=True)
    if OPERATOR_KEY.is_file():
        raw = OPERATOR_KEY.read_bytes()
        if len(raw) >= 32:
            return raw[:32]
    key = secrets.token_bytes(32)
    OPERATOR_KEY.write_bytes(key)
    try:
        os.chmod(OPERATOR_KEY, 0o600)
    except OSError:
        pass
    return key


def _aesgcm():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError("cryptography_required_for_zisv") from exc
    return AESGCM


def _derive_session_key(transfer_id: str) -> bytes:
    material = hashlib.sha256(_operator_secret() + transfer_id.encode()).digest()
    return material[:32]


def _encrypt_chunk(plaintext: bytes, *, transfer_id: str, chunk_index: int) -> dict[str, Any]:
    AESGCM = _aesgcm()
    key = _derive_session_key(f"{transfer_id}:{chunk_index}")
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, transfer_id.encode())
    return {
        "chunk_index": chunk_index,
        "nonce_b64": base64.b64encode(nonce).decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
        "plain_sha256": hashlib.sha256(plaintext).hexdigest(),
    }


def _decrypt_chunk(row: dict[str, Any], *, transfer_id: str) -> bytes:
    AESGCM = _aesgcm()
    idx = int(row.get("chunk_index") or 0)
    key = _derive_session_key(f"{transfer_id}:{idx}")
    nonce = base64.b64decode(str(row.get("nonce_b64") or ""))
    ciphertext = base64.b64decode(str(row.get("ciphertext_b64") or ""))
    return AESGCM(key).decrypt(nonce, ciphertext, transfer_id.encode())


def _field_io_packet(body: dict[str, Any], *, direction: str = "out") -> dict[str, Any]:
    fio = _mod(INSTALL / "lib" / "field-io-packet.py", "field_io_vault")
    if not fio or not hasattr(fio, "build_packet"):
        return {"ok": False, "error": "field_io_packet_missing"}
    gate = fio.truth_gate() if hasattr(fio, "truth_gate") else {"pass_ok": True}
    if not gate.get("pass_ok"):
        return {"ok": False, "error": "truth_gate_failed", "truth_gate": gate}
    try:
        pkt = fio.build_packet(direction=direction, body=body, gate=gate)
        return {"ok": True, "packet": pkt, "truth_gate": gate}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "truth_gate": gate}


def _truth_gate() -> dict[str, Any]:
    fio = _mod(INSTALL / "lib" / "field-io-packet.py", "field_io_vault_gate")
    if fio and hasattr(fio, "truth_gate"):
        return fio.truth_gate()
    return {"pass_ok": True, "bypass": True}


def wire_point(*, rotate: bool = False) -> dict[str, Any]:
    doc = _load(WIRE_POINT, {})
    if doc.get("wire_point") and not rotate:
        return {"ok": True, "schema": SCHEMA, "wire_point": doc["wire_point"], "rotated_at": doc.get("rotated_at")}
    secret = _operator_secret()
    epoch = int(time.time() // 3600)
    token = hashlib.sha256(secret + f"wire:{epoch}".encode()).hexdigest()[:24]
    wire = f"znwp-{token}"
    out = {"schema": "znetwork-wire-point/v1", "wire_point": wire, "rotated_at": _now(), "epoch": epoch}
    _save(WIRE_POINT, out)
    return {"ok": True, "schema": SCHEMA, **out}


def _normalize_wire(wire: str) -> str:
    wire = (wire or "").strip().lower()
    if not wire:
        return ""
    if not re.fullmatch(r"znwp-[a-f0-9]{16,32}", wire):
        return ""
    return wire


def _queue_doc() -> dict[str, Any]:
    doc = _load(QUEUE_PATH, {})
    if not doc:
        doc = {
            "schema": "znetwork-vault-queue/v1",
            "protocol": PROTOCOL,
            "inbound": [],
            "outbound": [],
            "threats_blocked": 0,
            "updated": _now(),
        }
    doc.setdefault("inbound", [])
    doc.setdefault("outbound", [])
    return doc


def _save_queue(doc: dict[str, Any]) -> None:
    doc["updated"] = _now()
    _save(QUEUE_PATH, doc)


def _sender_spam_score(sender_wire: str) -> dict[str, Any]:
    doc = _queue_doc()
    now = time.time()
    recent = 0
    pending = 0
    for row in doc.get("inbound") or []:
        if str(row.get("sender_wire") or "").lower() != sender_wire:
            continue
        if str(row.get("status") or "pending") == "pending":
            pending += 1
        try:
            ts = datetime.fromisoformat(str(row.get("received_at") or "").replace("Z", "+00:00")).timestamp()
        except (ValueError, TypeError):
            ts = 0
        if now - ts <= SPAM_WINDOW_SEC:
            recent += 1
    hostile = recent >= SPAM_BURST or pending >= SPAM_PENDING_CAP
    return {
        "sender_wire": sender_wire,
        "recent_in_window": recent,
        "pending": pending,
        "hostile": hostile,
        "reason": "vault_spam_burst" if recent >= SPAM_BURST else ("vault_spam_pending_cap" if pending >= SPAM_PENDING_CAP else ""),
    }


def _handoff_hostile(sender_wire: str, reason: str) -> dict[str, Any]:
    hostile = _mod(INSTALL / "lib" / "znetwork-hostile-threat.py", "znet_vault_hostile")
    rep = {"ok": True, "handoff": "logged", "sender_wire": sender_wire, "reason": reason}
    _append_jsonl(LEDGER, {"ts": _now(), "event": "hostile_handoff", **rep})
    if hostile and hasattr(hostile, "countermeasures"):
        try:
            rep["hostile"] = hostile.countermeasures(
                {
                    "ok": True,
                    "immediate": [
                        {
                            "ip": "0.0.0.0",
                            "process": sender_wire,
                            "reason": f"znetwork_vault:{reason}",
                            "verdict": "HARM_CANDIDATE",
                            "immediate": True,
                        }
                    ],
                },
                dry_run=False,
                force=True,
            )
        except Exception as exc:
            rep["hostile_error"] = str(exc)
    return rep


def _chunk_file(data: bytes) -> list[bytes]:
    chunks: list[bytes] = []
    offset = 0
    while offset < len(data):
        chunks.append(data[offset : offset + MAX_CHUNK])
        offset += MAX_CHUNK
    return chunks or [b""]


def send_transfer(
    *,
    recipient_wire: str,
    filename: str,
    mime: str,
    data_b64: str,
    sender_label: str = "",
) -> dict[str, Any]:
    """Push-only send — sealed ZISV chunks inside field-io envelopes."""
    gate = _truth_gate()
    if not gate.get("pass_ok"):
        return {"ok": False, "error": "truth_gate_failed", "truth_gate": gate}
    recipient_wire = _normalize_wire(recipient_wire)
    if not recipient_wire:
        return {"ok": False, "error": "invalid_recipient_wire"}
    try:
        raw = base64.b64decode(data_b64, validate=True)
    except Exception:
        return {"ok": False, "error": "invalid_payload_b64"}
    if len(raw) > MAX_FILE_BYTES:
        return {"ok": False, "error": "file_too_large", "max_bytes": MAX_FILE_BYTES}
    if not raw:
        return {"ok": False, "error": "empty_payload"}

    wp = wire_point()
    transfer_id = hashlib.sha256(secrets.token_bytes(16) + raw[:64]).hexdigest()[:20]
    chunks = _chunk_file(raw)
    sealed_chunks: list[dict[str, Any]] = []
    envelopes: list[dict[str, Any]] = []

    for idx, chunk in enumerate(chunks):
        sealed = _encrypt_chunk(chunk, transfer_id=transfer_id, chunk_index=idx)
        body = {
            "kind": "zisv_chunk",
            "protocol": PROTOCOL,
            "transfer_id": transfer_id,
            "sender_wire": wp.get("wire_point"),
            "sender_label": (sender_label or "ZNetwork operator")[:64],
            "recipient_wire": recipient_wire,
            "filename": Path(filename).name[:180],
            "mime": (mime or "application/octet-stream")[:120],
            "total_bytes": len(raw),
            "total_chunks": len(chunks),
            "chunk": sealed,
            "file_sha256": hashlib.sha256(raw).hexdigest(),
            "push_only": True,
            "answer_requests": False,
        }
        pkt_rep = _field_io_packet(body, direction="out")
        if not pkt_rep.get("ok"):
            return pkt_rep
        sealed_chunks.append(sealed)
        envelopes.append(pkt_rep["packet"])

    VAULT_ROOT.mkdir(parents=True, exist_ok=True)
    OUTBOUND_DIR.mkdir(parents=True, exist_ok=True)
    offer_path = OUTBOUND_DIR / f"{transfer_id}.json"
    offer = {
        "schema": "znetwork-vault-offer/v1",
        "protocol": PROTOCOL,
        "transfer_id": transfer_id,
        "direction": "outbound",
        "sender_wire": wp.get("wire_point"),
        "sender_label": sender_label or "ZNetwork operator",
        "recipient_wire": recipient_wire,
        "filename": Path(filename).name,
        "mime": mime or "application/octet-stream",
        "size": len(raw),
        "chunks": len(chunks),
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "envelopes": envelopes,
        "queued_at": _now(),
        "status": "queued",
    }
    _save(offer_path, offer)

    q = _queue_doc()
    q["outbound"].append(
        {
            "transfer_id": transfer_id,
            "recipient_wire": recipient_wire,
            "filename": offer["filename"],
            "mime": offer["mime"],
            "size": len(raw),
            "chunks": len(chunks),
            "queued_at": offer["queued_at"],
            "status": "queued",
        }
    )
    _save_queue(q)
    _append_jsonl(LEDGER, {"ts": _now(), "event": "send", "transfer_id": transfer_id, "recipient_wire": recipient_wire, "bytes": len(raw)})
    return {
        "ok": True,
        "schema": SCHEMA,
        "protocol": PROTOCOL,
        "transfer_id": transfer_id,
        "sender_wire": wp.get("wire_point"),
        "recipient_wire": recipient_wire,
        "chunks": len(chunks),
        "envelopes": len(envelopes),
        "truth_gate": gate,
        "motto": "Push-only — recipient accepts from queue; wire sees sealed envelopes only.",
    }


def ingest_offer(offer: dict[str, Any], *, sender_ip: str = "") -> dict[str, Any]:
    """Ingress — queue inbound push offer; spam/hostile preflight."""
    if not isinstance(offer, dict):
        return {"ok": False, "error": "offer_required"}
    transfer_id = str(offer.get("transfer_id") or "").strip()
    sender_wire = _normalize_wire(str(offer.get("sender_wire") or ""))
    if not transfer_id or not sender_wire:
        return {"ok": False, "error": "transfer_id_and_sender_wire_required"}

    spam = _sender_spam_score(sender_wire)
    if spam.get("hostile"):
        q = _queue_doc()
        q["threats_blocked"] = int(q.get("threats_blocked") or 0) + 1
        _save_queue(q)
        _handoff_hostile(sender_wire, spam.get("reason") or "vault_spam")
        _append_jsonl(LEDGER, {"ts": _now(), "event": "ingest_blocked", "transfer_id": transfer_id, "spam": spam})
        return {"ok": False, "error": "hostile_spam", "spam": spam, "threat": True}

    gate = _truth_gate()
    envelopes = offer.get("envelopes") or []
    if envelopes and not gate.get("pass_ok"):
        return {"ok": False, "error": "truth_gate_failed", "truth_gate": gate}

    INBOUND_DIR.mkdir(parents=True, exist_ok=True)
    path = INBOUND_DIR / f"{transfer_id}.json"
    if path.is_file():
        return {"ok": False, "error": "duplicate_transfer", "transfer_id": transfer_id}

    stored = {
        **offer,
        "schema": "znetwork-vault-offer/v1",
        "direction": "inbound",
        "received_at": _now(),
        "sender_ip": sender_ip[:64],
        "status": "pending",
        "spam_score": spam,
    }
    _save(path, stored)

    q = _queue_doc()
    q["inbound"].append(
        {
            "transfer_id": transfer_id,
            "sender_wire": sender_wire,
            "sender_label": str(offer.get("sender_label") or "Unknown")[:64],
            "filename": str(offer.get("filename") or "payload.bin")[:180],
            "mime": str(offer.get("mime") or "application/octet-stream")[:120],
            "size": int(offer.get("size") or 0),
            "chunks": int(offer.get("chunks") or len(envelopes) or 0),
            "received_at": stored["received_at"],
            "threat_score": spam.get("recent_in_window", 0),
            "hostile": False,
            "status": "pending",
        }
    )
    _save_queue(q)
    _append_jsonl(LEDGER, {"ts": _now(), "event": "ingest", "transfer_id": transfer_id, "sender_wire": sender_wire})
    return {"ok": True, "schema": SCHEMA, "transfer_id": transfer_id, "queued": True, "spam": spam}


def accept_transfer(transfer_id: str) -> dict[str, Any]:
    gate = _truth_gate()
    if not gate.get("pass_ok"):
        return {"ok": False, "error": "truth_gate_failed", "truth_gate": gate}
    transfer_id = (transfer_id or "").strip()
    path = INBOUND_DIR / f"{transfer_id}.json"
    if not path.is_file():
        return {"ok": False, "error": "transfer_not_found"}
    offer = _load(path, {})
    envelopes = offer.get("envelopes") or []
    if not envelopes:
        return {"ok": False, "error": "no_envelopes"}

    parts: list[bytes] = []
    for pkt in envelopes:
        body = (pkt.get("body") or {}) if isinstance(pkt, dict) else {}
        chunk = body.get("chunk") or {}
        try:
            parts.append(_decrypt_chunk(chunk, transfer_id=transfer_id))
        except Exception as exc:
            return {"ok": False, "error": "decrypt_failed", "detail": str(exc)}

    plaintext = b"".join(parts)
    expect = str(offer.get("file_sha256") or "")
    if expect and hashlib.sha256(plaintext).hexdigest() != expect:
        return {"ok": False, "error": "integrity_failed"}

    ACCEPTED_DIR.mkdir(parents=True, exist_ok=True)
    dest_dir = ACCEPTED_DIR / transfer_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = Path(str(offer.get("filename") or "payload.bin")).name
    dest = dest_dir / fname
    dest.write_bytes(plaintext)

    q = _queue_doc()
    for row in q.get("inbound") or []:
        if row.get("transfer_id") == transfer_id:
            row["status"] = "accepted"
            row["accepted_at"] = _now()
    _save_queue(q)
    offer["status"] = "accepted"
    offer["accepted_at"] = _now()
    offer["accepted_path"] = str(dest)
    _save(path, offer)
    _append_jsonl(LEDGER, {"ts": _now(), "event": "accept", "transfer_id": transfer_id, "path": str(dest)})
    return {
        "ok": True,
        "schema": SCHEMA,
        "transfer_id": transfer_id,
        "filename": fname,
        "bytes": len(plaintext),
        "accepted_path": str(dest),
    }


def reject_transfer(transfer_id: str, *, reason: str = "operator_reject") -> dict[str, Any]:
    transfer_id = (transfer_id or "").strip()
    path = INBOUND_DIR / f"{transfer_id}.json"
    q = _queue_doc()
    inbound: list[dict[str, Any]] = []
    for row in q.get("inbound") or []:
        if row.get("transfer_id") == transfer_id:
            continue
        inbound.append(row)
    q["inbound"] = inbound
    _save_queue(q)
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass
    _append_jsonl(LEDGER, {"ts": _now(), "event": "reject", "transfer_id": transfer_id, "reason": reason})
    return {"ok": True, "schema": SCHEMA, "transfer_id": transfer_id, "rejected": True, "reason": reason}


def list_queue() -> dict[str, Any]:
    q = _queue_doc()
    wp = wire_point()
    pending = [r for r in (q.get("inbound") or []) if str(r.get("status") or "pending") == "pending"]
    return {
        "ok": True,
        "schema": "znetwork-vault-queue/v1",
        "protocol": PROTOCOL,
        "wire_point": wp.get("wire_point"),
        "inbound_pending": pending,
        "inbound_count": len(pending),
        "outbound": q.get("outbound") or [],
        "threats_blocked": int(q.get("threats_blocked") or 0),
        "updated": q.get("updated"),
        "policy": {
            "push_only": True,
            "answer_requests": False,
            "middleman_decrypt": False,
            "envelope": "field-io-packet/v1 + zisv/v1 AES-GCM",
        },
    }


def panel_json() -> dict[str, Any]:
    gate = _truth_gate()
    q = list_queue()
    return {
        "ok": True,
        "schema": SCHEMA,
        "protocol": PROTOCOL,
        "truth_gate": {"pass_ok": gate.get("pass_ok"), "detail": gate.get("detail")},
        "wire_point": q.get("wire_point"),
        "queue": q,
        "limits": {"max_file_bytes": MAX_FILE_BYTES, "max_chunk_bytes": MAX_CHUNK},
        "motto": "Invincible secure vault — send sealed offers, accept from queue, threats interdict spam.",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "queue":
        print(json.dumps(list_queue(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "wire-point":
        print(json.dumps(wire_point(rotate="--rotate" in sys.argv), ensure_ascii=False, indent=2))
        return 0
    if cmd == "send" and len(sys.argv) > 2:
        req = json.loads(sys.argv[2])
        print(json.dumps(send_transfer(**req), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ingest" and len(sys.argv) > 2:
        req = json.loads(sys.argv[2])
        print(json.dumps(ingest_offer(req.get("offer") or req, sender_ip=str(req.get("sender_ip") or "")), ensure_ascii=False, indent=2))
        return 0
    if cmd == "accept" and len(sys.argv) > 2:
        print(json.dumps(accept_transfer(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "reject" and len(sys.argv) > 2:
        reason = sys.argv[3] if len(sys.argv) > 3 else "operator_reject"
        print(json.dumps(reject_transfer(sys.argv[2], reason=reason), ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {
                "error": "usage: znetwork-secure-vault.py [json|queue|wire-point|send JSON|ingest JSON|accept ID|reject ID]",
            }
        ),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())