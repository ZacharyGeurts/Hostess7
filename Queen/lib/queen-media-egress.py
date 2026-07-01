#!/usr/bin/env pythong
"""Queen media egress — zero outbound capture unless operator grants local OBS-style use.

Humans + AI browser: screen/mic/keystrokes never leave loopback without explicit local grant.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
GRANT_FILE = STATE / "local-capture-grant.json"

LOCAL_PURPOSES = frozenset({"obs_local", "local_record", "operator_capture"})
BLOCKED_EGRESS_SCHEMES = frozenset({"javascript", "data", "vbscript"})
ALLOWED_LOCAL_PROCS = frozenset({"obs", "obs-studio", "obs-ffmpeg-mux"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(raw: str) -> datetime | None:
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _load_grant() -> dict[str, Any]:
    try:
        return json.loads(GRANT_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_grant(doc: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = GRANT_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(GRANT_FILE)


def _grant_ttl() -> int:
    return int(os.environ.get("NEXUS_LOCAL_CAPTURE_TTL_SEC", "3600"))


def _egress_locked() -> bool:
    return os.environ.get("NEXUS_MEDIA_EGRESS_LOCK", "1") not in ("0", "false", "no")


def _local_capture_enabled() -> bool:
    return os.environ.get("NEXUS_LOCAL_CAPTURE_OPERATOR", "1") not in ("0", "false", "no")


def grant_active(doc: dict[str, Any] | None = None) -> bool:
    g = doc if doc is not None else _load_grant()
    if not g.get("active"):
        return False
    exp = _parse_ts(str(g.get("expires_at") or ""))
    if exp and datetime.now(timezone.utc) >= exp:
        return False
    return True


def revoke_grant() -> dict[str, Any]:
    g = _load_grant()
    if g:
        g["active"] = False
        g["revoked_at"] = _now()
        _save_grant(g)
    return {"ok": True, "active": False, "revoked_at": g.get("revoked_at")}


def request_local_capture(*, purpose: str = "obs_local", ttl_sec: int | None = None) -> dict[str, Any]:
    if not _local_capture_enabled():
        return {"ok": False, "permit": False, "error": "local_capture_disabled"}
    purpose = (purpose or "obs_local").strip().lower()
    if purpose not in LOCAL_PURPOSES:
        return {"ok": False, "permit": False, "error": "invalid_purpose", "allowed": sorted(LOCAL_PURPOSES)}
    ttl = ttl_sec if ttl_sec is not None else _grant_ttl()
    ttl = max(60, min(int(ttl), 86400))
    now = datetime.now(timezone.utc)
    doc = {
        "schema": "nexus-local-capture/v1",
        "id": uuid.uuid4().hex[:16],
        "active": True,
        "purpose": purpose,
        "loopback_only": True,
        "egress_allowed": False,
        "granted_at": _now(),
        "expires_at": (now + timedelta(seconds=ttl)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "allowed_procs": sorted(ALLOWED_LOCAL_PROCS),
        "doctrine": "local_operator_only — no remote egress, no keyhook export",
    }
    _save_grant(doc)
    return {"ok": True, "permit": True, "grant": doc}


def media_gate_check(constraints: dict[str, Any] | None = None) -> dict[str, Any]:
    constraints = constraints or {}
    wants_video = bool(constraints.get("video"))
    wants_audio = bool(constraints.get("audio"))
    wants_display = bool(constraints.get("display"))
    g = _load_grant()
    active = grant_active(g)
    locked = _egress_locked()
    permit = active and (wants_display or wants_video or wants_audio)
    return {
        "ok": True,
        "permit": permit,
        "locked": locked,
        "grant_active": active,
        "loopback_only": True,
        "egress_allowed": False,
        "wants": {"video": wants_video, "audio": wants_audio, "display": wants_display},
        "grant": g if active else {},
        "verdict": "ALLOW_LOCAL" if permit else "BLOCK_EGRESS",
        "reason": "operator_local_grant" if permit else "no_grant_presume_hostile",
    }


def egress_posture() -> dict[str, Any]:
    g = _load_grant()
    active = grant_active(g)
    return {
        "schema": "queen-media-egress/v1",
        "updated": _now(),
        "doctrine": "safety_first_humans_and_ai",
        "motto": "Nothing leaves unless operator requests local capture. Presume hostile egress.",
        "egress_lock": _egress_locked(),
        "local_capture_enabled": _local_capture_enabled(),
        "grant_active": active,
        "grant": g if active else {},
        "blocked_by_default": {
            "screen_out": True,
            "mic_out": True,
            "camera_out": True,
            "keystrokes_out": True,
            "keyhooks_out": True,
            "webrtc_remote": True,
            "clipboard_out": True,
        },
        "allowed_with_local_grant": {
            "obs_local": sorted(ALLOWED_LOCAL_PROCS),
            "loopback_only": True,
            "remote_egress": False,
        },
        "keyboard_no_middleman": os.environ.get("NEXUS_KEYBOARD_NO_MIDDLEMAN", "1") == "1",
        "no_screen_capture": os.environ.get("NEXUS_NO_SCREEN_CAPTURE", "1") == "1",
        "no_keyboard_hook": os.environ.get("NEXUS_NO_KEYBOARD_HOOK", "1") == "1",
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "posture"):
        return {"ok": True, **egress_posture()}
    if action in ("capture_request", "request_local_capture"):
        return request_local_capture(
            purpose=str(body.get("purpose") or "obs_local"),
            ttl_sec=body.get("ttl_sec"),
        )
    if action in ("capture_revoke", "revoke"):
        return revoke_grant()
    if action in ("media_gate_check", "gate_media"):
        c = body.get("constraints") if isinstance(body.get("constraints"), dict) else body
        return media_gate_check(c)
    return {"ok": False, "error": "unknown_action", "action": action}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(json.dumps(egress_posture(), indent=2))
    elif sys.argv[1] == "grant":
        print(json.dumps(request_local_capture(), indent=2))
    elif sys.argv[1] == "revoke":
        print(json.dumps(revoke_grant(), indent=2))
    else:
        print(json.dumps(dispatch({"action": sys.argv[1]}), indent=2))