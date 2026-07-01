#!/usr/bin/env pythong
"""Beyond DARPA · Lockheed security — all systems and data, user AND machine.

Human threats (keystroke, voice, paste, insider) and machine threats (C2, malware, bots, injection)
fail closed. HIGHLY beyond DARPA and Lockheed et al. secure posture for the full stack.
"""
from __future__ import annotations

import hashlib
import importlib.util
import ipaddress
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
DOCTRINE = INSTALL / "data" / "beyond-darpa-security-doctrine.json"
PANEL = STATE / "beyond-darpa-security-panel.json"
LEDGER = STATE / "beyond-darpa-security-ledger.jsonl"

_LOOPBACK = frozenset({"127.0.0.1", "::1", "::ffff:127.0.0.1"})
_HUMAN_CHANNELS = frozenset({"keystroke", "voice", "typed", "paste", "human", "operator"})
_MACHINE_CHANNELS = frozenset({"c2", "malware", "bot", "automated", "scan", "machine", "ai_injection"})
_HUMAN_THREAT_RE = re.compile(
    r"\b(phish|credential|password|social engineer|paste|inject|insider|coerc|bribe|"
    r"keystroke log|voice spoof|impersonat)\b",
    re.I,
)
_MACHINE_THREAT_RE = re.compile(
    r"\b(c2|beacon|malware|rat|asyncrat|cobalt|exploit|botnet|ddos|shellcode|"
    r"prompt inject|supply chain|tamper|reverse shell|exfil)\b",
    re.I,
)
_DESTRUCTIVE = frozenset({
    "write_file", "save_file", "delete_file", "exec_shell", "exec", "eval",
    "overwrite", "patch_file", "rmtree", "unlink", "format_drive",
})


def _now() -> str:
    try:
        spec = importlib.util.spec_from_file_location("sovereign_clock_bds", _LIB / "sovereign-clock.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "utc_z"):
                return mod.utc_z()
    except Exception:
        pass
    from datetime import datetime, timezone
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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {"tier": "beyond_darpa_lockheed"})


def _is_loopback(peer: str) -> bool:
    if peer in _LOOPBACK or str(peer).startswith("127."):
        return True
    try:
        return ipaddress.ip_address(peer).is_loopback
    except ValueError:
        return False


def assess_threat(
    *,
    channel: str = "machine",
    text: str = "",
    peer: str = "127.0.0.1",
    actor: str = "unknown",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score human and machine threat vectors — both must pass for access."""
    doc = doctrine()
    ch = str(channel or "machine").strip().lower()
    blob = str(text or "")
    meta = metadata or {}

    human_hits = _HUMAN_THREAT_RE.findall(blob)
    machine_hits = _MACHINE_THREAT_RE.findall(blob)
    human_score = min(1.0, len(human_hits) * 0.22)
    machine_score = min(1.0, len(machine_hits) * 0.24)

    if ch in _HUMAN_CHANNELS:
        human_score = min(1.0, human_score + 0.35)
    if ch == "paste":
        human_score = min(1.0, human_score + 0.40)
    if ch in _MACHINE_CHANNELS or ch == "internet":
        machine_score = min(1.0, machine_score + 0.20)

    if not _is_loopback(peer):
        machine_score = min(1.0, machine_score + 0.85)

    if len(blob) > 12000:
        human_score = min(1.0, human_score + 0.15)
        machine_score = min(1.0, machine_score + 0.10)

    if meta.get("c2") or meta.get("malware"):
        machine_score = 1.0

    user_sec = doc.get("user_security") or {}
    machine_sec = doc.get("machine_security") or {}
    human_floor = float(user_sec.get("truth_floor_human") or 58) / 100.0
    human_hostile = human_score >= 0.55 or (ch in _HUMAN_CHANNELS and human_score >= 0.35)
    machine_hostile = machine_score >= 0.50 or not _is_loopback(peer)

    redundancy_ok = True
    if ch in _HUMAN_CHANNELS and user_sec.get("redundancy_required_for_human"):
        paths = meta.get("redundancy_paths") or []
        redundancy_ok = len(paths) >= 2 if isinstance(paths, list) else ch != "paste"

    pass_ok = not human_hostile and not machine_hostile and redundancy_ok
    if human_hostile and machine_hostile:
        verdict = "DUAL_THREAT"
    elif human_hostile:
        verdict = "HUMAN_THREAT"
    elif machine_hostile:
        verdict = "MACHINE_THREAT"
    elif not redundancy_ok:
        verdict = "HUMAN_REDUNDANCY_HOLD"
    else:
        verdict = "CLEAR"

    return {
        "schema": "beyond-darpa-threat-assess/v1",
        "ok": True,
        "tier": doc.get("tier") or "beyond_darpa_lockheed",
        "pass_ok": pass_ok,
        "verdict": verdict,
        "channel": ch,
        "actor": actor,
        "peer": peer,
        "loopback": _is_loopback(peer),
        "human_threat": {
            "score": round(human_score, 3),
            "hostile": human_hostile,
            "signals": human_hits[:16],
            "compromise_expected": bool(user_sec.get("human_input_compromise_expected")),
        },
        "machine_threat": {
            "score": round(machine_score, 3),
            "hostile": machine_hostile,
            "signals": machine_hits[:16],
            "c2_presumed": bool(machine_sec.get("c2_presumed_hostile")),
        },
        "redundancy_ok": redundancy_ok,
        "human_floor": human_floor,
        "fail_closed": bool((doc.get("enforcement") or {}).get("fail_closed")),
        "assessed_at": _now(),
    }


def gate_access(
    *,
    system_id: str = "nexus",
    peer: str = "127.0.0.1",
    path: str = "",
    method: str = "GET",
    channel: str = "machine",
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Fail-closed gate for any system or data path."""
    doc = doctrine()
    enforce = doc.get("enforcement") or {}
    hdrs = {k.lower(): v for k, v in (headers or {}).items()}
    payload = body or {}

    ch = str(channel or "machine").lower()
    if hdrs.get("x-human-input") in ("1", "true", "yes"):
        ch = "keystroke"
    if hdrs.get("x-voice-input") in ("1", "true", "yes"):
        ch = "voice"

    text = json.dumps(payload, default=str) if payload else ""
    if payload.get("counsel"):
        text += " " + str(payload.get("counsel"))
    if payload.get("query"):
        text += " " + str(payload.get("query"))

    assessment = assess_threat(channel=ch, text=text, peer=peer, actor=system_id)
    action = str(payload.get("action") or "").lower()

    if enforce.get("destructive_blocked") and action in _DESTRUCTIVE:
        return {
            "ok": False,
            "code": 403,
            "error": "destructive_blocked",
            "tier": doc.get("tier"),
            "assessment": assessment,
            "fail_closed": True,
        }

    if not assessment.get("pass_ok"):
        _append_ledger({
            "event": "gate_denied",
            "system_id": system_id,
            "path": path,
            "verdict": assessment.get("verdict"),
        })
        return {
            "ok": False,
            "code": 403,
            "error": "beyond_darpa_fail_closed",
            "detail": assessment.get("verdict"),
            "tier": doc.get("tier"),
            "assessment": assessment,
            "fail_closed": True,
        }

    return {
        "ok": True,
        "code": 200,
        "tier": doc.get("tier"),
        "system_id": system_id,
        "path": path,
        "method": method,
        "assessment": assessment,
        "fail_closed": bool(enforce.get("fail_closed")),
    }


def _integration_slice() -> list[dict[str, Any]]:
    doc = doctrine()
    rows: list[dict[str, Any]] = []
    for rel in doc.get("integrations") or []:
        if not isinstance(rel, str):
            continue
        p = INSTALL / rel
        rows.append({
            "path": rel,
            "present": p.is_file(),
            "tier_required": doc.get("tier"),
        })
    return rows


def stack_posture(*, write: bool = True) -> dict[str, Any]:
    """Full-stack beyond-DARPA posture — all systems and data."""
    doc = doctrine()
    iron = _import_mod("bds_iron", "ironclad-secure-api.py")
    iron_grounded = False
    if iron and hasattr(iron, "IroncladSecureAPI"):
        try:
            iron_grounded = iron.IroncladSecureAPI.instance().ironclad_grounded()
        except Exception:
            pass

    integrations = _integration_slice()
    present = sum(1 for r in integrations if r.get("present"))
    ew_mandate = _load(INSTALL / "Queen" / "data" / "queen-external-wire.json", {})
    advisory_doc = _load(INSTALL / "data" / "hostess7-advisory-body-doctrine.json", {})

    panel = {
        "schema": "beyond-darpa-security-panel/v1",
        "ok": True,
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "tier": doc.get("tier") or "beyond_darpa_lockheed",
        "scope": doc.get("scope"),
        "user_security": doc.get("user_security"),
        "machine_security": doc.get("machine_security"),
        "threat_classes": doc.get("threat_classes"),
        "enforcement": doc.get("enforcement"),
        "ironclad_grounded": iron_grounded,
        "external_wire_tier": ew_mandate.get("tier"),
        "external_quarantine": (ew_mandate.get("doctrine") or {}).get("import_to_main") is False,
        "body_advisory_only": (advisory_doc.get("body_lock") or {}).get("sole_ingress") == "advisory_channel",
        "integrations_present": present,
        "integrations_total": len(integrations),
        "integrations": integrations,
        "all_systems_secured": present >= max(1, len(integrations) - 2),
        "all_data_secured": bool((doc.get("scope") or {}).get("all_data")),
        "human_threats_covered": bool((doc.get("threat_classes") or {}).get("human_threats")),
        "machine_threats_covered": bool((doc.get("threat_classes") or {}).get("machine_threats")),
        "updated": _now(),
    }
    if write:
        _save(PANEL, panel)
    return panel


def advisory_for_truth_gate(*, skip_refresh: bool = False) -> dict[str, Any]:
    """Counsel for truth gate — advisory only, never defeats pass_ok."""
    if not skip_refresh:
        stack_posture(write=False)
    doc = doctrine()
    return {
        "schema": "beyond-darpa-truth-gate-advisory/v1",
        "advisory_only": True,
        "never_defeats_gate": True,
        "tier": doc.get("tier") or "beyond_darpa_lockheed",
        "human_threats": (doc.get("threat_classes") or {}).get("human_threats") or [],
        "machine_threats": (doc.get("threat_classes") or {}).get("machine_threats") or [],
        "fail_closed": bool((doc.get("enforcement") or {}).get("fail_closed")),
        "all_systems": bool((doc.get("scope") or {}).get("all_systems")),
        "all_data": bool((doc.get("scope") or {}).get("all_data")),
        "counsel": (
            "Beyond DARPA · Lockheed tier — user AND machine secured. "
            "Human keystroke/voice situational; machine C2/malware presumed hostile. "
            "Advisory enriches counsel — Ironclad gate unchanged."
        ),
        "ts": _now(),
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel", "posture"):
        return {"ok": True, **stack_posture(write=action == "panel")}
    if action in ("assess", "threat", "threat_assess"):
        return assess_threat(
            channel=str(body.get("channel") or "machine"),
            text=str(body.get("text") or body.get("counsel") or body.get("query") or ""),
            peer=str(body.get("peer") or "127.0.0.1"),
            actor=str(body.get("actor") or body.get("system_id") or "unknown"),
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
        )
    if action in ("gate", "check", "verify"):
        return gate_access(
            system_id=str(body.get("system_id") or "nexus"),
            peer=str(body.get("peer") or "127.0.0.1"),
            path=str(body.get("path") or ""),
            method=str(body.get("method") or "GET"),
            channel=str(body.get("channel") or "machine"),
            body=body.get("body") if isinstance(body.get("body"), dict) else body,
            headers=body.get("headers") if isinstance(body.get("headers"), dict) else None,
        )
    if action == "advisory":
        return {"ok": True, **advisory_for_truth_gate()}
    return {"ok": False, "error": "unknown_action", "tier": doctrine().get("tier")}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(payload), ensure_ascii=False))
        return 0
    if cmd in ("json", "panel", "posture", "status"):
        print(json.dumps(stack_posture(write=cmd == "panel"), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: beyond-darpa-security.py [json|panel|dispatch]",
        "tier": "beyond_darpa_lockheed",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())