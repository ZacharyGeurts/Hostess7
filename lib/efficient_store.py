#!/usr/bin/env pythong
"""Content-addressable append-only field store — blake3 Merkle chain (uncompressed payloads)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "."))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
STORE_ROOT = STATE / "field-store"
CHAIN_FILE = STORE_ROOT / "merkle-chain.jsonl"


def _hash_bytes(data: bytes) -> str:
    try:
        import blake3  # type: ignore

        return blake3.blake3(data).hexdigest()
    except ImportError:
        import hashlib

        return hashlib.sha256(data).hexdigest()


def _parent_hash() -> str:
    if not CHAIN_FILE.is_file():
        return "0" * 64
    try:
        last = CHAIN_FILE.read_text(encoding="utf-8").strip().splitlines()[-1]
        return json.loads(last).get("hash", "0" * 64)
    except (OSError, json.JSONDecodeError, IndexError):
        return "0" * 64


def append_record(kind: str, doc: dict[str, Any]) -> dict[str, Any]:
    STORE_ROOT.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"kind": kind, "doc": doc}, ensure_ascii=False, separators=(",", ":")).encode()
    content_hash = _hash_bytes(payload)
    parent = _parent_hash()
    merkle = _hash_bytes(f"{parent}:{content_hash}".encode())
    blob_path = STORE_ROOT / "blobs" / f"{content_hash[:2]}" / content_hash
    blob_path.parent.mkdir(parents=True, exist_ok=True)
    if not blob_path.is_file():
        blob_path.write_bytes(payload)
    entry = {
        "kind": kind,
        "hash": merkle,
        "parent": parent,
        "content": content_hash,
        "bytes": len(payload),
    }
    with CHAIN_FILE.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_chain(*, limit: int = 50) -> list[dict[str, Any]]:
    if not CHAIN_FILE.is_file():
        return []
    lines = CHAIN_FILE.read_text(encoding="utf-8").strip().splitlines()
    out: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def load_blob(content_hash: str) -> dict[str, Any] | None:
    blob_path = STORE_ROOT / "blobs" / f"{content_hash[:2]}" / content_hash
    if not blob_path.is_file():
        return None
    raw = blob_path.read_bytes()
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def panel_json() -> dict[str, Any]:
    chain = read_chain(limit=20)
    return {
        "schema": "efficient-store/v1",
        "root": str(STORE_ROOT),
        "chain_len": len(chain),
        "head": chain[-1]["hash"] if chain else None,
        "recent": chain,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd == "append" and len(sys.argv) >= 4:
        doc = json.loads(sys.argv[3])
        print(json.dumps(append_record(sys.argv[2], doc), ensure_ascii=False))
        return 0
    if cmd == "panel":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: efficient_store.py [panel|append KIND JSON]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())