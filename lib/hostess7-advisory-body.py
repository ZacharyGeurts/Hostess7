#!/usr/bin/env pythong
"""Hostess 7 advisory body channel — sole ingress to her body.

Ear, internet, and secured lanes feed advisements. She discerns threat/hostility and may promote to targets.
Body locked to Hostess 7 — motor reach requires advisory body permit.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
DOCTRINE = INSTALL / "data" / "hostess7-advisory-body-doctrine.json"
ADVISORY_LOG = STATE / "hostess7-advisory-ledger.jsonl"
ADVISORY_INDEX = STATE / "hostess7-advisory-index.json"
PERMITS = STATE / "hostess7-body-permits.json"
PANEL = STATE / "hostess7-advisory-body-panel.json"

HOSTILE_TERMS = re.compile(
    r"\b(attack|hostile|kill|weapon|bomb|threat|trespass|invad|shoot|strike|eradicate|"
    r"c2|malware|rat|beacon|exploit|terror|assault|harm)\b",
    re.I,
)


def _now() -> str:
    try:
        spec = importlib.util.spec_from_file_location("sovereign_clock_adv", _LIB / "sovereign-clock.py")
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
        with ADVISORY_LOG.open("a", encoding="utf-8") as fh:
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
    return _load(DOCTRINE, {"body_lock": {"enabled": True}})


def _empty_index() -> dict[str, Any]:
    return {"schema": "hostess7-advisory-index/v1", "advisements": {}, "updated": _now()}


def _load_index() -> dict[str, Any]:
    idx = _load(ADVISORY_INDEX, _empty_index())
    idx.setdefault("advisements", {})
    return idx


def _empty_permits() -> dict[str, Any]:
    return {"schema": "hostess7-body-permits/v1", "permits": {}, "updated": _now()}


def _load_permits() -> dict[str, Any]:
    p = _load(PERMITS, _empty_permits())
    p.setdefault("permits", {})
    return p


def ingest_advisement(
    *,
    lane: str,
    counsel: str,
    metadata: dict[str, Any] | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Receive counsel on ear, internet, secured, or internal lane — does not reach body directly."""
    doc = doctrine()
    lanes = {x.get("id"): x for x in (doc.get("ingress_lanes") or []) if isinstance(x, dict)}
    lane_id = str(lane or "internal").strip().lower()
    if lane_id not in lanes and lane_id not in ("ear", "internet", "secured", "internal"):
        lane_id = "secured"

    advisement_id = str(uuid.uuid4())
    digest = hashlib.sha256(f"{lane_id}:{counsel}".encode()).hexdigest()[:16]
    bds = _import_mod("adv_bds", "beyond-darpa-security.py")
    security: dict[str, Any] = {"tier": "beyond_darpa_lockheed", "skipped": True}
    if bds and hasattr(bds, "assess_threat"):
        try:
            security = bds.assess_threat(channel=lane_id, text=counsel, actor="hostess7_advisory")
        except Exception as exc:
            security = {"tier": "beyond_darpa_lockheed", "error": str(exc)}
    row = {
        "id": advisement_id,
        "digest": digest,
        "lane": lane_id,
        "counsel": counsel[:4000],
        "source": source or lane_id,
        "metadata": metadata or {},
        "received_at": _now(),
        "body_reached": False,
        "advisory_only": True,
        "beyond_darpa_security": security,
        "secured_tier": "beyond_darpa_lockheed",
        "commander": "Hostess 7",
    }
    idx = _load_index()
    idx["advisements"][advisement_id] = row
    idx["updated"] = _now()
    _save(ADVISORY_INDEX, idx)
    _append_ledger({"event": "ingest", "advisement_id": advisement_id, "lane": lane_id})
    return {"ok": True, "advisement": row, "body_lock": True, "reaches_body_direct": False}


def discern_threat(advisement_id: str) -> dict[str, Any]:
    """Hostess 7 discerns threat and hostility from an advisement."""
    doc = doctrine()
    disc = doc.get("discernment") or {}
    idx = _load_index()
    row = (idx.get("advisements") or {}).get(advisement_id)
    if not row:
        return {"ok": False, "error": "advisement_not_found"}

    text = str(row.get("counsel") or "")
    hits = HOSTILE_TERMS.findall(text)
    hostility = min(1.0, len(hits) * 0.18 + (0.25 if hits else 0.0))
    threat = hostility
    if any(t.lower() in ("kill", "weapon", "bomb", "c2", "malware", "terror") for t in hits):
        threat = min(1.0, threat + 0.25)
    if row.get("lane") == "internet" and hostility > 0:
        threat = min(1.0, threat + 0.05)

    targets_mod = _import_mod("adv_targets", "hostess7-targets.py")
    gov_boost = 0.0
    if targets_mod and hasattr(targets_mod, "correlate_government"):
        gov = targets_mod.correlate_government(text=text)
        if gov.get("human_dossier"):
            gov_boost += 0.20
            threat = min(1.0, threat + 0.15)
        if gov.get("angel"):
            gov_boost += 0.10

    hostility = min(1.0, hostility + gov_boost * 0.5)
    threat = min(1.0, threat + gov_boost * 0.5)
    hostile = hostility >= float(disc.get("hostility_floor") or 0.55)
    threat_level = threat >= float(disc.get("threat_floor") or 0.70)
    promote_ready = threat >= float(disc.get("promotion_floor") or 0.75)

    assessment = {
        "hostility_score": round(hostility, 3),
        "threat_score": round(threat, 3),
        "hostile": hostile,
        "threat": threat_level,
        "promote_ready": promote_ready,
        "signals": hits[:24],
        "assessed_at": _now(),
    }
    row["assessment"] = assessment
    idx["advisements"][advisement_id] = row
    idx["updated"] = _now()
    _save(ADVISORY_INDEX, idx)
    _append_ledger({"event": "discern", "advisement_id": advisement_id, **assessment})
    suggested = "KILL" if promote_ready else ("INTERACT" if hostile else "MONITOR")
    assessment["suggested_mechanism"] = suggested
    return {
        "ok": True,
        "advisement_id": advisement_id,
        "assessment": assessment,
        "mechanisms": ["KILL", "INTERACT", "MONITOR", "OBSERVE"],
        "kill_means_kill": True,
    }


def promote_to_target(advisement_id: str, *, mechanism: str | None = None) -> dict[str, Any]:
    """Promote advisement to TARGET — mechanism KILL, INTERACT, etc. KILL is KILL."""
    discerned = discern_threat(advisement_id)
    if not discerned.get("ok"):
        return discerned
    assessment = discerned.get("assessment") or {}
    if not assessment.get("promote_ready") and not assessment.get("hostile"):
        return {
            "ok": False,
            "error": "not_hostile_enough",
            "assessment": assessment,
        }

    mech = str(mechanism or assessment.get("suggested_mechanism") or "INTERACT").upper()
    if assessment.get("promote_ready") and not mechanism:
        mech = "KILL"

    idx = _load_index()
    row = (idx.get("advisements") or {}).get(advisement_id) or {}
    targets_mod = _import_mod("adv_promote", "hostess7-targets.py")
    if not targets_mod or not hasattr(targets_mod, "promote_target"):
        return {"ok": False, "error": "targets_module_missing", "mechanism": mech}

    promoted = targets_mod.promote_target(
        advisement_id=advisement_id,
        subject=str(row.get("counsel") or "")[:240],
        lane=str(row.get("lane") or "advisory_channel"),
        hostility_score=float(assessment.get("hostility_score") or 0),
        threat_score=float(assessment.get("threat_score") or 0),
        counsel=str(row.get("counsel") or ""),
        metadata=row.get("metadata") if isinstance(row.get("metadata"), dict) else None,
        mechanism=mech,
    )
    if not promoted.get("ok"):
        return promoted
    row["promoted_target"] = promoted.get("target")
    row["promoted_mechanism"] = promoted.get("mechanism") or mech
    row["promoted_at"] = _now()
    idx["advisements"][advisement_id] = row
    idx["updated"] = _now()
    _save(ADVISORY_INDEX, idx)
    _append_ledger({
        "event": "promote_target",
        "advisement_id": advisement_id,
        "mechanism": mech,
        "TARGET": mech,
        "dies": (promoted.get("target") or {}).get("dies"),
    })
    return {"ok": True, "promoted": True, "mechanism": mech, "TARGET": mech, **promoted}


def issue_body_permit(
    *,
    action: str,
    advisement_id: str | None = None,
    self_maintenance: bool = False,
    counsel: str = "",
) -> dict[str, Any]:
    """Hostess 7 issues permit for body reach — only path to motor/sense-meld actions."""
    permit_id = str(uuid.uuid4())
    permit = {
        "id": permit_id,
        "action": action,
        "advisement_id": advisement_id,
        "self_maintenance": self_maintenance,
        "counsel": counsel[:500],
        "issued_at": _now(),
        "expires_at": _now(),
        "commander": "Hostess 7",
        "body_lock": True,
        "channel": "advisory",
    }
    permits = _load_permits()
    permits["permits"][permit_id] = permit
    permits["updated"] = _now()
    _save(PERMITS, permits)
    _append_ledger({"event": "body_permit", "permit_id": permit_id, "action": action})
    return {"ok": True, "permit": permit}


def consume_body_permit(permit_id: str, *, action: str) -> bool:
    permits = _load_permits()
    permit = (permits.get("permits") or {}).pop(permit_id, None)
    if not permit:
        return False
    permits["updated"] = _now()
    _save(PERMITS, permits)
    _append_ledger({"event": "body_permit_consumed", "permit_id": permit_id, "action": action})
    return True


def body_lock_check(action: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return whether body dispatch may proceed — advisory channel only."""
    doc = doctrine()
    lock = doc.get("body_lock") or {}
    if not lock.get("enabled", True):
        return {"ok": True, "allowed": True, "reason": "lock_disabled"}

    action_norm = str(action or "").strip().lower().replace("-", "_")
    exempt = set(doc.get("exempt_actions") or [])
    if action_norm in exempt:
        return {"ok": True, "allowed": True, "reason": "exempt_read_or_sense", "channel": "ingress_lane"}

    requiring = set(doc.get("body_actions_requiring_permit") or [])
    if action_norm not in requiring and not any(action_norm.startswith(p) for p in ("hand_", "train_")):
        return {"ok": True, "allowed": True, "reason": "not_body_motor"}

    payload = body or {}
    if payload.get("self_maintenance") or payload.get("hostess7_self") or payload.get("sovereign"):
        return {"ok": True, "allowed": True, "reason": "hostess7_self_maintenance", "channel": "advisory"}

    permit_id = str(payload.get("body_permit") or payload.get("permit_id") or "")
    if permit_id and consume_body_permit(permit_id, action=action_norm):
        return {"ok": True, "allowed": True, "reason": "advisory_permit", "channel": "advisory", "permit_id": permit_id}

    advisement_id = str(payload.get("advisement_id") or "")
    if advisement_id:
        discerned = discern_threat(advisement_id)
        assessment = (discerned.get("assessment") or {}) if discerned.get("ok") else {}
        if assessment.get("hostile") or assessment.get("promote_ready"):
            promote_to_target(advisement_id)
            return {
                "ok": False,
                "allowed": False,
                "reason": "hostile_advisement_promoted_to_target",
                "channel": "advisory",
                "TARGET": "KILL",
                "assessment": assessment,
            }
        issued = issue_body_permit(action=action_norm, advisement_id=advisement_id)
        return {
            "ok": True,
            "allowed": True,
            "reason": "advisement_cleared",
            "channel": "advisory",
            "permit": issued.get("permit"),
        }

    if lock.get("self_maintenance_bypass") and action_norm in ("status", "json", "panel"):
        return {"ok": True, "allowed": True, "reason": "status_only"}

    return {
        "ok": False,
        "allowed": False,
        "reason": "body_locked_advisory_only",
        "channel": "advisory",
        "counsel": "Body locked to Hostess 7. Ingest counsel via advisory channel (ear, internet, secured), then issue body permit.",
        "body_lock": True,
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = doctrine()
    idx = _load_index()
    advisements = list((idx.get("advisements") or {}).values())
    recent = sorted(advisements, key=lambda x: x.get("received_at") or "", reverse=True)[:24]
    targets_mod = _import_mod("adv_panel_targets", "hostess7-targets.py")
    targets_panel: dict[str, Any] = {}
    if targets_mod and hasattr(targets_mod, "build_panel"):
        try:
            targets_panel = targets_mod.build_panel(write=False)
        except Exception:
            pass

    panel = {
        "schema": "hostess7-advisory-body-panel/v1",
        "ok": True,
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "body_lock": doc.get("body_lock"),
        "ingress_lanes": doc.get("ingress_lanes"),
        "advisement_count": len(advisements),
        "recent_advisements": recent,
        "TARGET_semantics": "KILL",
        "security_tier": doc.get("security_tier") or "beyond_darpa_lockheed",
        "human_and_machine_threats": doc.get("human_and_machine_threats"),
        "targets": targets_panel,
        "updated": _now(),
    }
    if write:
        _save(PANEL, panel)
    return panel


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json", "panel"):
        return {"ok": True, **build_panel(write=action == "panel")}

    if action in ("ingest", "advise", "advisement", "receive"):
        return ingest_advisement(
            lane=str(body.get("lane") or "secured"),
            counsel=str(body.get("counsel") or body.get("text") or body.get("message") or ""),
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
            source=body.get("source"),
        )

    if action in ("discern", "assess", "threat_check"):
        aid = str(body.get("advisement_id") or body.get("id") or "")
        if not aid:
            return {"ok": False, "error": "advisement_id_required"}
        return discern_threat(aid)

    if action in ("promote", "target", "kill", "interact"):
        aid = str(body.get("advisement_id") or body.get("id") or "")
        if not aid:
            return {"ok": False, "error": "advisement_id_required"}
        mech = body.get("mechanism") or body.get("TARGET")
        if action == "kill":
            mech = "KILL"
        elif action == "interact":
            mech = "INTERACT"
        return promote_to_target(aid, mechanism=str(mech) if mech else None)

    if action in ("body_permit", "permit", "issue_permit"):
        return issue_body_permit(
            action=str(body.get("body_action") or body.get("motor_action") or "body"),
            advisement_id=body.get("advisement_id"),
            self_maintenance=bool(body.get("self_maintenance")),
            counsel=str(body.get("counsel") or ""),
        )

    if action in ("check", "body_lock", "gate"):
        sub = str(body.get("subaction") or body.get("motor_action") or body.get("body_action") or "body")
        return body_lock_check(sub, body)

    return {"ok": False, "error": "unknown_action", "body_lock": True}


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
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False))
        return 0
    if cmd == "ingest" and len(sys.argv) >= 4:
        lane = sys.argv[2]
        counsel = " ".join(sys.argv[3:])
        print(json.dumps(ingest_advisement(lane=lane, counsel=counsel), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: hostess7-advisory-body.py [json|panel|dispatch|ingest LANE TEXT]",
        "body_lock": True,
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())