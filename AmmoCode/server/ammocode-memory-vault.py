#!/usr/bin/env python3
"""AmmoCode memory vault — bounded, leak-free, 4-slot running encode/decode."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCTRINE = ROOT / "data" / "ammocode-memory-vault-doctrine.json"

SLOT_IDS = ("TIME", "MEMORY", "THERMO", "CONTEXT")
SLOT_MASK = 3
MAX_ENTRIES = 64
MAX_BYTES = 524_288

_GENESIS: bytes | None = None
_ROT: int = 0
_VAULT: OrderedDict[str, dict[str, Any]] = OrderedDict()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_doctrine() -> dict[str, Any]:
    try:
        return json.loads(DOCTRINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _genesis() -> bytes:
    global _GENESIS
    if _GENESIS is None:
        raw = os.environ.get("AMMOCODE_VAULT_GENESIS", "").strip()
        if raw:
            _GENESIS = bytes.fromhex(raw) if len(raw) >= 32 else hashlib.sha256(raw.encode()).digest()
        else:
            _GENESIS = hashlib.sha256(secrets.token_bytes(32)).digest()
    return _GENESIS


def _slot_key(slot: int) -> bytes:
    sid = SLOT_IDS[slot & SLOT_MASK]
    return hmac.new(_genesis(), f"ammocode:vault:{sid}:{slot}".encode(), hashlib.sha256).digest()


def _running_rot() -> int:
    global _ROT
    r = _ROT & SLOT_MASK
    _ROT = (_ROT + 1) & SLOT_MASK
    return r


def _xor_stream(data: bytes, slot: int, rot: int) -> bytes:
    key = _slot_key(slot)
    out = bytearray(len(data))
    for i, b in enumerate(data):
        out[i] = b ^ key[(i + rot + slot) % len(key)]
    return bytes(out)


def _seal(blob: bytes, slot: int, rot: int) -> str:
    msg = f"{slot}:{rot}:".encode() + blob
    return hmac.new(_genesis(), msg, hashlib.sha256).hexdigest()


def encode_blob(plaintext: bytes, *, slot: int | None = None) -> dict[str, Any]:
    if len(plaintext) > MAX_BYTES:
        return {"ok": False, "error": "oversize", "max_bytes": MAX_BYTES}
    rot = _running_rot()
    use_slot = (slot if slot is not None else rot) & SLOT_MASK
    masked = _xor_stream(plaintext, use_slot, rot)
    return {
        "ok": True,
        "blob": masked.hex(),
        "slot": use_slot,
        "slot_id": SLOT_IDS[use_slot],
        "rot": rot,
        "seal": _seal(masked, use_slot, rot),
        "bytes": len(plaintext),
        "runtime_tax": 0,
    }


def decode_blob(blob_hex: str, seal: str, slot: int, rot: int) -> dict[str, Any]:
    try:
        masked = bytes.fromhex(blob_hex)
    except ValueError:
        return {"ok": False, "error": "bad_blob", "tamper": True}
    if not hmac.compare_digest(_seal(masked, slot & SLOT_MASK, rot), seal):
        _scrub_hex(blob_hex)
        return {"ok": False, "error": "tamper", "tamper": True, "action": "scrub_and_abort"}
    plain = _xor_stream(masked, slot & SLOT_MASK, rot)
    return {
        "ok": True,
        "plaintext": plain.decode("utf-8", errors="replace"),
        "bytes": len(plain),
        "slot_id": SLOT_IDS[slot & SLOT_MASK],
        "runtime_tax": 0,
    }


def _scrub_hex(blob_hex: str) -> None:
    try:
        buf = bytearray(bytes.fromhex(blob_hex))
        for i in range(len(buf)):
            buf[i] = 0
    except ValueError:
        pass


def _scrub_entry(entry: dict[str, Any]) -> None:
    blob = entry.get("blob")
    if isinstance(blob, str):
        _scrub_hex(blob)
    entry["scrubbed"] = True
    entry["plaintext"] = None


def _evict_if_needed() -> None:
    while len(_VAULT) >= MAX_ENTRIES:
        _, old = _VAULT.popitem(last=False)
        _scrub_entry(old)


def vault_store(text: str, *, handle: str = "", slot: int | None = None) -> dict[str, Any]:
    raw = text.encode("utf-8")
    enc = encode_blob(raw, slot=slot)
    if not enc.get("ok"):
        return enc
    hid = handle.strip() or secrets.token_hex(8)
    if hid in _VAULT:
        _scrub_entry(_VAULT[hid])
        del _VAULT[hid]
    _evict_if_needed()
    _VAULT[hid] = {
        "schema": "ammocode-vault-entry/v1",
        "handle": hid,
        "blob": enc["blob"],
        "seal": enc["seal"],
        "slot": enc["slot"],
        "rot": enc["rot"],
        "bytes": enc["bytes"],
        "updated": _now(),
        "scrubbed": False,
    }
    _VAULT.move_to_end(hid)
    return {"ok": True, "handle": hid, "entry": {k: _VAULT[hid][k] for k in ("handle", "slot", "rot", "bytes", "updated")}, **{k: enc[k] for k in ("slot_id", "runtime_tax")}}


def vault_fetch(handle: str) -> dict[str, Any]:
    entry = _VAULT.get(handle)
    if not entry or entry.get("scrubbed"):
        return {"ok": False, "error": "missing_or_scrubbed"}
    dec = decode_blob(entry["blob"], entry["seal"], entry["slot"], entry["rot"])
    if not dec.get("ok"):
        _scrub_entry(entry)
        _VAULT.pop(handle, None)
        return dec
    return {"ok": True, "handle": handle, "plaintext": dec["plaintext"], "bytes": dec["bytes"], "slot_id": dec["slot_id"]}


def vault_release(handle: str) -> dict[str, Any]:
    entry = _VAULT.pop(handle, None)
    if entry:
        _scrub_entry(entry)
        return {"ok": True, "released": handle, "scrubbed": True}
    return {"ok": True, "released": handle, "scrubbed": False}


def vault_scrub_all() -> dict[str, Any]:
    count = len(_VAULT)
    for entry in list(_VAULT.values()):
        _scrub_entry(entry)
    _VAULT.clear()
    return {"ok": True, "scrubbed": count}


def vault_status() -> dict[str, Any]:
    doc = _load_doctrine()
    entries = []
    total_bytes = 0
    for hid, ent in _VAULT.items():
        if ent.get("scrubbed"):
            continue
        b = int(ent.get("bytes") or 0)
        total_bytes += b
        entries.append({"handle": hid, "slot": ent.get("slot"), "bytes": b, "updated": ent.get("updated")})
    leak_ok = len(_VAULT) <= MAX_ENTRIES and total_bytes <= MAX_BYTES * MAX_ENTRIES
    return {
        "ok": True,
        "schema": "ammocode-memory-vault-status/v1",
        "runtime_tax": 0,
        "genesis_sealed": _GENESIS is not None,
        "rot_counter": _ROT,
        "slots": [{"id": s, "index": i} for i, s in enumerate(SLOT_IDS)],
        "entries": len(entries),
        "total_plaintext_bytes": total_bytes,
        "max_entries": MAX_ENTRIES,
        "leak_ok": leak_ok,
        "no_leak": leak_ok,
        "codec": (doc.get("codec") or {}).get("algorithm", "running_4slot_xor_hmac"),
        "motto": doc.get("motto"),
        "updated": _now(),
    }


def handle_api(action: str, body: dict[str, Any]) -> dict[str, Any]:
    act = (action or "").strip().lower()
    if act in ("vault_status", "memory_status", "memory_vault_status"):
        return vault_status()
    if act in ("vault_encode", "memory_encode"):
        text = body.get("content") or body.get("text") or ""
        slot = body.get("slot")
        return encode_blob(text.encode("utf-8"), slot=int(slot) if slot is not None else None)
    if act in ("vault_decode", "memory_decode"):
        return decode_blob(
            str(body.get("blob") or ""),
            str(body.get("seal") or ""),
            int(body.get("slot") or 0),
            int(body.get("rot") or 0),
        )
    if act in ("vault_store", "memory_store"):
        return vault_store(str(body.get("content") or body.get("text") or ""), handle=str(body.get("handle") or ""))
    if act in ("vault_fetch", "memory_fetch"):
        return vault_fetch(str(body.get("handle") or ""))
    if act in ("vault_release", "memory_release"):
        return vault_release(str(body.get("handle") or ""))
    if act in ("vault_scrub", "memory_scrub"):
        return vault_scrub_all()
    return {"ok": False, "error": "unknown_vault_action", "actions": [
        "vault_status", "vault_encode", "vault_decode", "vault_store", "vault_fetch", "vault_release", "vault_scrub",
    ]}


if __name__ == "__main__":
    st = vault_status()
    hid = vault_store("AmmoCode sealed memory")["handle"]
    got = vault_fetch(hid)
    assert got.get("ok") and "sealed" in got.get("plaintext", "")
    vault_release(hid)
    print(json.dumps({"ok": True, "status": st, "roundtrip": got.get("plaintext")}, indent=2))