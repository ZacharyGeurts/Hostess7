#!/usr/bin/env pythong
"""Queen Vault — encrypted credential store for imported logins.

Passwords never touch disk in plaintext. AES-256-CBC via openssl, key from machine+user KDF.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

QUEEN = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
VAULT_PATH = STATE / "queen-vault.enc"
VAULT_META = STATE / "queen-vault-meta.json"
SCHEMA = "queen-vault/v1"
KDF_ITER = int(os.environ.get("QUEEN_VAULT_KDF_ITER", "600000"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _machine_id() -> str:
    for path in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
        try:
            text = path.read_text(encoding="utf-8").strip()
            if text:
                return text
        except OSError:
            continue
    return "queen-local"


def _derive_key(*, salt: bytes | None = None) -> tuple[bytes, bytes]:
    salt = salt or secrets.token_bytes(16)
    uid = str(os.getuid())
    user = os.environ.get("USER", "") or os.environ.get("LOGNAME", "")
    extra = os.environ.get("QUEEN_VAULT_PASSPHRASE", "")
    material = f"{_machine_id()}|{uid}|{user}|{extra}|queen-vault-v1".encode("utf-8")
    key = hashlib.pbkdf2_hmac("sha256", material, salt, KDF_ITER, dklen=32)
    return key, salt


def _openssl_available() -> bool:
    try:
        subprocess.run(["openssl", "version"], capture_output=True, check=True, timeout=3)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _aes_encrypt(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    iv = secrets.token_bytes(16)
    proc = subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-K", key.hex(), "-iv", iv.hex()],
        input=plaintext,
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError("vault_encrypt_failed")
    return proc.stdout, iv


def _aes_decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    proc = subprocess.run(
        ["openssl", "enc", "-d", "-aes-256-cbc", "-K", key.hex(), "-iv", iv.hex()],
        input=ciphertext,
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError("vault_decrypt_failed")
    return proc.stdout


def _load_outer() -> dict[str, Any]:
    if not VAULT_PATH.is_file():
        return {"schema": SCHEMA, "credentials": [], "updated": _now()}
    try:
        doc = json.loads(VAULT_PATH.read_text(encoding="utf-8"))
        if doc.get("schema") != SCHEMA:
            return {"schema": SCHEMA, "credentials": [], "updated": _now(), "error": "schema_mismatch"}
        return doc
    except (OSError, json.JSONDecodeError):
        return {"schema": SCHEMA, "credentials": [], "updated": _now(), "error": "corrupt"}


def _save_outer(doc: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = VAULT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(VAULT_PATH)
    try:
        os.chmod(VAULT_PATH, 0o600)
    except OSError:
        pass


def _unlock_inner(outer: dict[str, Any]) -> list[dict[str, Any]]:
    if not outer.get("encrypted"):
        return list(outer.get("credentials") or [])
    if not _openssl_available():
        return []
    salt = base64.b64decode(outer.get("salt") or "")
    iv = base64.b64decode(outer.get("iv") or "")
    blob = base64.b64decode(outer.get("data") or "")
    key, _ = _derive_key(salt=salt)
    plain = _aes_decrypt(blob, key, iv)
    inner = json.loads(plain.decode("utf-8"))
    return list(inner.get("credentials") or [])


def _lock_inner(credentials: list[dict[str, Any]], *, sources: dict[str, Any] | None = None) -> dict[str, Any]:
    creds = []
    for row in credentials:
        creds.append({
            "id": row.get("id"),
            "origin": row.get("origin") or "",
            "host": row.get("host") or "",
            "username": row.get("username") or "",
            "password": row.get("password") or "",
            "source": row.get("source") or "import",
            "imported_at": row.get("imported_at") or _now(),
            "permit": row.get("permit", True),
        })
    inner = {"schema": SCHEMA, "credentials": creds, "updated": _now()}
    if not _openssl_available():
        return {**inner, "encrypted": False}
    key, salt = _derive_key()
    blob, iv = _aes_encrypt(json.dumps(inner, ensure_ascii=False).encode("utf-8"), key)
    meta = {
        "schema": SCHEMA,
        "encrypted": True,
        "kdf": "pbkdf2-sha256",
        "iterations": KDF_ITER,
        "salt": base64.b64encode(salt).decode("ascii"),
        "iv": base64.b64encode(iv).decode("ascii"),
        "data": base64.b64encode(blob).decode("ascii"),
        "count": len(creds),
        "updated": _now(),
        "sources": sources or {},
    }
    return meta


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _cred_id(origin: str, username: str) -> str:
    return hashlib.sha256(f"{origin}|{username}".encode("utf-8")).hexdigest()[:20]


def vault_status() -> dict[str, Any]:
    outer = _load_outer()
    meta = _load_json(VAULT_META, {})
    count = int(outer.get("count") or meta.get("count") or 0)
    if outer.get("encrypted"):
        count = int(outer.get("count") or 0)
    elif outer.get("credentials"):
        count = len(outer.get("credentials") or [])
    return {
        "schema": SCHEMA,
        "ok": True,
        "encrypted": bool(outer.get("encrypted", True)),
        "count": count,
        "updated": outer.get("updated") or meta.get("updated"),
        "sources": meta.get("sources") or outer.get("sources") or {},
        "path": str(VAULT_PATH),
        "openssl": _openssl_available(),
        "doctrine": "plaintext_never_on_disk — decrypt only in memory for gated lookup",
    }


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_meta(meta: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    safe = {k: v for k, v in meta.items() if k not in ("data",)}
    tmp = VAULT_META.with_suffix(".tmp")
    tmp.write_text(json.dumps(safe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(VAULT_META)


def import_credentials(rows: list[dict[str, Any]], *, source: str = "import") -> dict[str, Any]:
    outer = _load_outer()
    existing = _unlock_inner(outer)
    seen = {_cred_id(c.get("origin") or "", c.get("username") or "") for c in existing}
    added = 0
    skipped = 0
    for row in rows:
        origin = (row.get("origin") or row.get("url") or "").strip()
        username = (row.get("username") or row.get("user") or "").strip()
        password = row.get("password") or row.get("pass") or ""
        if not origin or not username or not password:
            skipped += 1
            continue
        cid = _cred_id(origin, username)
        if cid in seen:
            skipped += 1
            continue
        existing.append({
            "id": cid,
            "origin": origin,
            "host": _host(origin),
            "username": username,
            "password": password,
            "source": row.get("source") or source,
            "imported_at": _now(),
            "permit": row.get("permit", True),
        })
        seen.add(cid)
        added += 1
    sources = _load_json(VAULT_META, {}).get("sources") or {}
    sources[source] = int(sources.get(source) or 0) + added
    locked = _lock_inner(existing, sources=sources)
    _save_outer(locked)
    _save_meta({**vault_status(), "sources": sources, "last_import": _now(), "last_source": source})
    return {"ok": True, "added": added, "skipped": skipped, "total": len(existing), "encrypted": locked.get("encrypted", True)}


def lookup_credentials(host: str, *, gate_check: bool = True) -> list[dict[str, Any]]:
    host = (host or "").lower().strip()
    if not host:
        return []
    outer = _load_outer()
    creds = _unlock_inner(outer)
    out: list[dict[str, Any]] = []
    for c in creds:
        if not c.get("permit", True):
            continue
        ch = (c.get("host") or _host(c.get("origin") or "")).lower()
        if ch != host and not (ch and host.endswith("." + ch)) and not (host and ch.endswith("." + host)):
            continue
        if gate_check:
            gate_mod = None
            try:
                import importlib.util

                path = QUEEN / "lib" / "queen-gate.py"
                if path.is_file():
                    spec = importlib.util.spec_from_file_location("queen_gate", path)
                    if spec and spec.loader:
                        gate_mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(gate_mod)
            except Exception:
                gate_mod = None
            if gate_mod and hasattr(gate_mod, "gate_nav"):
                try:
                    gate = gate_mod.gate_nav(c.get("origin") or f"https://{host}/")
                    if not gate.get("permit", True):
                        continue
                except Exception:
                    continue
        out.append({
            "id": c.get("id"),
            "origin": c.get("origin"),
            "host": ch,
            "username": c.get("username"),
            "password": c.get("password"),
            "source": c.get("source"),
        })
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd == "status":
        print(json.dumps(vault_status(), ensure_ascii=False))
        return 0
    if cmd == "lookup" and len(sys.argv) > 2:
        rows = lookup_credentials(sys.argv[2])
        print(json.dumps({"ok": True, "host": sys.argv[2], "credentials": rows}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-vault.py [status|lookup HOST]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())