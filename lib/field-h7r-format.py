#!/usr/bin/env python3
"""H7r/1 — rackmount redundant storage: erasure stripes, forever SHA-256, personhood + AmmoDrive ACL."""
from __future__ import annotations

import hashlib
import json
import struct
import zlib
from pathlib import Path
from typing import Any

MAGIC = b"H7R\x01"
FORMAT = "h7r/1"
HEADER_SCHEMA = "h7r/1-header/v1"
DATA_SHARDS = 4
PARITY_SHARDS = 2
STRIPE_COUNT = DATA_SHARDS + PARITY_SHARDS


class H7rError(ValueError):
    pass


def forever_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _xor_bytes(a: bytes, b: bytes) -> bytes:
    n = max(len(a), len(b))
    if not n:
        return b""
    aa = a.ljust(n, b"\x00")
    bb = b.ljust(n, b"\x00")
    return bytes(x ^ y for x, y in zip(aa, bb))


def _split_shards(payload: bytes, k: int = DATA_SHARDS) -> list[bytes]:
    if not payload:
        return [b""] * k
    shard_len = (len(payload) + k - 1) // k
    shards = []
    for i in range(k):
        chunk = payload[i * shard_len : (i + 1) * shard_len]
        shards.append(chunk.ljust(shard_len, b"\x00"))
    return shards


def _parity_shards(data_shards: list[bytes]) -> list[bytes]:
    if not data_shards:
        return [b"", b""]
    p0 = data_shards[0]
    for s in data_shards[1:]:
        p0 = _xor_bytes(p0, s)
    p1 = data_shards[0]
    for s in data_shards[1:3]:
        p1 = _xor_bytes(p1, s)
    return [p0, p1]


def _reconstruct_payload(data_shards: list[bytes | None], *, byte_count: int) -> bytes:
    shards: list[bytes] = []
    for i in range(DATA_SHARDS):
        s = data_shards[i]
        if s is None:
            shards.append(b"")
        else:
            shards.append(s)
    missing = [i for i, s in enumerate(shards) if not s]
    if len(missing) > PARITY_SHARDS:
        raise H7rError("too_many_missing_shards")
    if missing:
        have = [s for s in shards if s]
        stripe_len = max(len(s) for s in have) if have else 0
        shards = [s.ljust(stripe_len, b"\x00") if s else b"\x00" * stripe_len for s in shards]
        p0, p1 = _parity_shards([shards[i] for i in range(DATA_SHARDS)])
        if len(missing) == 1:
            idx = missing[0]
            if idx < DATA_SHARDS:
                rec = p0
                for j in range(DATA_SHARDS):
                    if j != idx:
                        rec = _xor_bytes(rec, shards[j])
                shards[idx] = rec
        elif len(missing) == 2:
            if missing == [2, 3]:
                shards[2] = _xor_bytes(p1, _xor_bytes(shards[0], shards[1]))
                shards[3] = _xor_bytes(p0, _xor_bytes(shards[0], _xor_bytes(shards[1], shards[2])))
            elif missing == [0, 1]:
                shards[0] = _xor_bytes(p1, shards[2])
                shards[1] = _xor_bytes(p0, _xor_bytes(shards[2], shards[3]))
    merged = b"".join(shards)
    return merged[:byte_count]


def default_acl(
    *,
    owner_personhood_id: str,
    owner_ammodrive_id: str,
    open_read: bool = False,
    open_write: bool = False,
) -> dict[str, Any]:
    return {
        "owner_personhood_id": owner_personhood_id,
        "owner_ammodrive_id": owner_ammodrive_id,
        "locked": True,
        "open_read": open_read,
        "open_write": open_write,
        "readers": [],
        "writers": [],
        "never_delete_without_hash": True,
    }


def pack(
    payload: bytes,
    *,
    owner_personhood_id: str,
    owner_ammodrive_id: str,
    original_name: str = "blob",
    acl: dict[str, Any] | None = None,
    compress: bool = True,
    open_read: bool = False,
) -> bytes:
    raw = zlib.compress(payload, 9) if compress and len(payload) > 256 else payload
    fhash = forever_hash(payload)
    acl_doc = acl or default_acl(
        owner_personhood_id=owner_personhood_id,
        owner_ammodrive_id=owner_ammodrive_id,
        open_read=open_read,
    )
    header = {
        "schema": HEADER_SCHEMA,
        "format": FORMAT,
        "forever_hash": fhash,
        "personhood_id": owner_personhood_id,
        "owner_ammodrive_id": owner_ammodrive_id,
        "acl": acl_doc,
        "original_name": original_name,
        "byte_count": len(payload),
        "stored_byte_count": len(raw),
        "compressed": compress and len(payload) > 256,
        "erasure": {"k": DATA_SHARDS, "m": PARITY_SHARDS, "algorithm": "xor_parity_v1"},
        "never_delete_without_hash": True,
        "open_to_everyone": bool(open_read or acl_doc.get("open_read")),
    }
    data_shards = _split_shards(raw, DATA_SHARDS)
    parities = _parity_shards(data_shards)
    stripes = data_shards + parities
    stripe_len = max(len(s) for s in stripes) if stripes else 0
    stripe_blob = b"".join(s.ljust(stripe_len, b"\x00") for s in stripes)
    header_bytes = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return b"".join([
        MAGIC,
        struct.pack(">I", len(header_bytes)),
        header_bytes,
        struct.pack(">B", STRIPE_COUNT),
        struct.pack(">I", stripe_len),
        stripe_blob,
    ])


def unpack(blob: bytes) -> tuple[dict[str, Any], bytes]:
    if len(blob) < 14 or blob[:4] != MAGIC:
        raise H7rError("not_h7r")
    header_len = struct.unpack(">I", blob[4:8])[0]
    header_end = 8 + header_len
    if header_end + 5 > len(blob):
        raise H7rError("truncated_header")
    header = json.loads(blob[8:header_end].decode("utf-8"))
    stripe_count = blob[header_end]
    stripe_len = struct.unpack(">I", blob[header_end + 1 : header_end + 5])[0]
    stripe_start = header_end + 5
    stripe_blob = blob[stripe_start:]
    expected = stripe_count * stripe_len
    if len(stripe_blob) < expected:
        raise H7rError("truncated_stripes")
    stripes = [stripe_blob[i * stripe_len : (i + 1) * stripe_len] for i in range(stripe_count)]
    data_shards = stripes[:DATA_SHARDS]
    raw = _reconstruct_payload(data_shards, byte_count=int(header.get("stored_byte_count") or 0))
    if header.get("compressed"):
        raw = zlib.decompress(raw)
    if forever_hash(raw) != str(header.get("forever_hash") or ""):
        raise H7rError("forever_hash_mismatch")
    return header, raw


def verify_forever_delete(header: dict[str, Any], *, request_hash: str, requester_personhood_id: str) -> bool:
    if request_hash != str(header.get("forever_hash") or ""):
        return False
    acl = header.get("acl") or {}
    owner_ph = str(acl.get("owner_personhood_id") or header.get("personhood_id") or "")
    if requester_personhood_id == owner_ph:
        return True
    return bool(acl.get("delete_grant") and requester_personhood_id in (acl.get("delete_grantees") or []))


def acl_can_read(header: dict[str, Any], *, personhood_id: str, ammodrive_id: str) -> bool:
    acl = header.get("acl") or {}
    if acl.get("open_read") or header.get("open_to_everyone"):
        return True
    if ammodrive_id and ammodrive_id == str(acl.get("owner_ammodrive_id") or ""):
        return True
    if personhood_id and personhood_id == str(acl.get("owner_personhood_id") or ""):
        return True
    if ammodrive_id and ammodrive_id in (acl.get("readers") or []):
        return True
    return False


def acl_can_write(header: dict[str, Any], *, personhood_id: str, ammodrive_id: str) -> bool:
    acl = header.get("acl") or {}
    if acl.get("open_write"):
        return True
    if ammodrive_id and ammodrive_id == str(acl.get("owner_ammodrive_id") or ""):
        return True
    if personhood_id and personhood_id == str(acl.get("owner_personhood_id") or ""):
        return True
    if ammodrive_id and ammodrive_id in (acl.get("writers") or []):
        return True
    return False


def grant_acl(
    header: dict[str, Any],
    *,
    owner_ammodrive_id: str,
    grantee_ammodrive_id: str,
    read: bool = True,
    write: bool = False,
) -> dict[str, Any]:
    acl = dict(header.get("acl") or {})
    if str(acl.get("owner_ammodrive_id") or "") != owner_ammodrive_id:
        raise H7rError("not_owner")
    readers = list(acl.get("readers") or [])
    writers = list(acl.get("writers") or [])
    if read and grantee_ammodrive_id not in readers:
        readers.append(grantee_ammodrive_id)
    if write and grantee_ammodrive_id not in writers:
        writers.append(grantee_ammodrive_id)
    acl["readers"] = readers
    acl["writers"] = writers
    acl["locked"] = False
    header = {**header, "acl": acl}
    return header