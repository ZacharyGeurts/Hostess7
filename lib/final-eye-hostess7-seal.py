#!/usr/bin/env pythong
"""Final_Eye seal + Hostess 7 trusted handshake — sole commander lane."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
DOCTRINE = INSTALL / "data" / "final-eye-hostess7-seal-doctrine.json"
AUTHORITY = INSTALL / "Hostess7" / "data" / "hostess7-supreme-authority.json"
SEAL_STATE = STATE / "final-eye-hostess7-seal.json"
HANDSHAKE_LEDGER = STATE / "final-eye-hostess7-handshake-ledger.jsonl"
CODE_SEAL = Path(os.environ.get("FINAL_EYE_ROOT", str(INSTALL / "Final_Eye"))) / "data" / "code-seal.json"

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
    root = str(INSTALL.resolve())
    mid = str(auth.get("schema") or "hostess7-supreme-authority/v3")
    return hashlib.sha256(f"{COMMANDER}|{root}|{mid}|final-eye-seal".encode()).digest()


def _final_eye_root() -> Path:
    env = os.environ.get("FINAL_EYE_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_dir():
            return p
    try:
        if str(_LIB) not in sys.path:
            sys.path.insert(0, str(_LIB))
        from sg_paths import final_eye_root
        return final_eye_root()
    except Exception:
        pass
    for cand in (INSTALL / "Final_Eye", INSTALL.parent / "Final_Eye"):
        if cand.is_dir():
            return cand.resolve()
    return (INSTALL / "Final_Eye").resolve()


def _verify_code_seal() -> dict[str, Any]:
    fe = _final_eye_root()
    seal_path = fe / "data" / "code-seal.json"
    sec = fe / "zocr_security.py"
    if not sec.is_file():
        return {"ok": seal_path.is_file(), "source": "code-seal.json", "present": seal_path.is_file()}
    try:
        root_str = str(fe)
        if root_str not in sys.path:
            sys.path.insert(0, root_str)
        spec = importlib.util.spec_from_file_location("zocr_security_seal", sec)
        if not spec or not spec.loader:
            return {"ok": False, "error": "import_failed"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "verify_code_seal"):
            return mod.verify_code_seal()
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:120]}
    return {"ok": seal_path.is_file(), "present": seal_path.is_file()}


def seal_posture(*, force: bool = False) -> dict[str, Any]:
    """Final_Eye sealed state — code seal + Hostess 7 commander lock."""
    doc = _load(SEAL_STATE, {})
    code = _verify_code_seal()
    auth = _load(AUTHORITY, {})
    sealed = bool(code.get("ok")) and auth.get("full_system_control", {}).get("enabled")
    if force or not doc.get("sealed"):
        doc = {
            "schema": "final-eye-hostess7-seal/v1",
            "ts": _now(),
            "sealed": sealed,
            "commander": COMMANDER,
            "commander_title": (auth.get("military_rank") or {}).get("title", "Forever Watchguard Angel"),
            "code_seal": {"ok": code.get("ok"), "file_count": code.get("file_count")},
            "authority": str(AUTHORITY.relative_to(INSTALL)) if AUTHORITY.is_file() else None,
            "handshake_only": True,
            "trusted_peers": [COMMANDER],
            "rejected_peers": ["queen_direct", "mcp", "grok_agent", "unsealed_cli"],
            "doctrine": str(DOCTRINE.relative_to(INSTALL)) if DOCTRINE.is_file() else None,
        }
        _save(SEAL_STATE, doc)
    else:
        doc["ts"] = _now()
        doc["sealed"] = sealed
        doc["code_seal"] = {"ok": code.get("ok"), "file_count": code.get("file_count")}
        _save(SEAL_STATE, doc)
    return doc


def issue_handshake(*, action: str = "dispatch", subject: str = "final_eye") -> dict[str, Any]:
    """Issue handshake token — Hostess 7 OCR control only."""
    if os.environ.get("HOSTESS7_OCR_CONTROL", "").strip().lower() not in ("1", "true", "yes", "on"):
        return {"ok": False, "error": "issuer_not_hostess7", "commander": COMMANDER}
    seal = seal_posture()
    if not seal.get("sealed"):
        return {"ok": False, "error": "final_eye_not_sealed", "seal": seal}
    ts = _now()
    nonce = secrets.token_hex(8)
    msg = f"{COMMANDER}|{action}|{subject}|{ts}|{nonce}".encode()
    token = hmac.new(_secret(), msg, hashlib.sha256).hexdigest()
    row = {
        "ok": True,
        "schema": "final-eye-hostess7-handshake/v1",
        "commander": COMMANDER,
        "action": action,
        "subject": subject,
        "handshake_ts": ts,
        "handshake_nonce": nonce,
        "handshake_token": token,
        "ttl_sec": HANDSHAKE_TTL_SEC,
        "sealed": True,
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


def verify_handshake(body: dict[str, Any], *, action: str = "dispatch") -> dict[str, Any]:
    """Verify Hostess 7 handshake on dispatch body."""
    seal = seal_posture()
    if not seal.get("sealed"):
        return {"ok": False, "error": "final_eye_not_sealed", "sealed": False, "seal": seal}

    commander = str(body.get("commander") or body.get("issuer") or "").strip().lower()
    if commander and commander not in (COMMANDER, "hostess 7", "hostess7"):
        return {"ok": False, "error": "untrusted_commander", "commander": commander, "sealed": True}

    token = str(body.get("handshake_token") or body.get("hostess7_handshake") or "").strip()
    nonce = str(body.get("handshake_nonce") or "").strip()
    ts = str(body.get("handshake_ts") or "").strip()
    subject = str(body.get("handshake_subject") or body.get("subject") or "final_eye")
    act = str(body.get("handshake_action") or body.get("action") or action)

    if not token or not nonce or not ts:
        env_tok = os.environ.get("HOSTESS7_FINAL_EYE_HANDSHAKE", "").strip()
        if env_tok and body.get("_hostess7_env_dispatch"):
            return {"ok": True, "via": "hostess7_env_dispatch", "sealed": True, "commander": COMMANDER}
        return {
            "ok": False,
            "error": "hostess7_handshake_required",
            "sealed": True,
            "hint": "Dispatch via lib/hostess7-ocr-control.py only",
            "api": "/api/hostess7/ocr/dispatch",
        }

    ts_epoch = _parse_ts(ts)
    if ts_epoch is None or (time.time() - ts_epoch) > HANDSHAKE_TTL_SEC:
        return {"ok": False, "error": "handshake_expired", "sealed": True, "ttl_sec": HANDSHAKE_TTL_SEC}

    msg = f"{COMMANDER}|{act}|{subject}|{ts}|{nonce}".encode()
    expect = hmac.new(_secret(), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(token, expect):
        return {"ok": False, "error": "handshake_invalid", "sealed": True}

    return {"ok": True, "commander": COMMANDER, "sealed": True, "action": act, "verified": True}


def stamp_body(body: dict[str, Any], *, action: str = "dispatch") -> dict[str, Any]:
    """Attach fresh Hostess 7 handshake to dispatch body."""
    hs = issue_handshake(action=action, subject="final_eye")
    if not hs.get("ok"):
        return {**body, "_handshake_error": hs}
    out = dict(body)
    out.update({
        "commander": COMMANDER,
        "handshake_action": hs.get("action"),
        "handshake_subject": hs.get("subject"),
        "handshake_ts": hs.get("handshake_ts"),
        "handshake_nonce": hs.get("handshake_nonce"),
        "handshake_token": hs.get("handshake_token"),
        "_hostess7_env_dispatch": True,
    })
    return out


def require_handshake(body: dict[str, Any], *, subaction: str) -> dict[str, Any] | None:
    """Return error dict if handshake fails; None if OK."""
    if str(os.environ.get("FINAL_EYE_HOSTESS7_BYPASS", "0")).strip().lower() in ("1", "true", "yes"):
        return None
    public = subaction in ("handshake", "seal", "seal_posture")
    if public and os.environ.get("HOSTESS7_OCR_CONTROL", "").strip().lower() in ("1", "true", "yes", "on"):
        return None
    if public:
        return {"ok": False, "error": "hostess7_handshake_required", "subaction": subaction, "sealed": True}
    verdict = verify_handshake(body, action=subaction)
    if verdict.get("ok"):
        return None
    return {**verdict, "subaction": subaction, "gate": "final-eye-hostess7-seal"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "posture").strip().lower()
    if cmd in ("posture", "json", "status"):
        print(json.dumps(seal_posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "seal":
        os.environ["HOSTESS7_OCR_CONTROL"] = "1"
        print(json.dumps(seal_posture(force=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "handshake":
        os.environ["HOSTESS7_OCR_CONTROL"] = "1"
        action = sys.argv[2] if len(sys.argv) > 2 else "dispatch"
        print(json.dumps(issue_handshake(action=action), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["posture", "seal", "handshake ACTION"]}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())