#!/usr/bin/env pythong
"""Hostess 7 targets database — TARGET mechanisms: KILL, INTERACT, MONITOR, …

KILL is KILL: once set, no returns, no modifications — it dies.
Other mechanisms (interact, monitor, observe) are non-terminal.
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
DOCTRINE = INSTALL / "data" / "hostess7-targets-doctrine.json"
REGISTRY = STATE / "hostess7-targets-registry.json"
PANEL = STATE / "hostess7-targets-panel.json"
LEDGER = STATE / "hostess7-targets-ledger.jsonl"

IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
MECHANISMS = frozenset({"KILL", "INTERACT", "MONITOR", "OBSERVE"})
TERMINAL_MECHANISMS = frozenset({"KILL"})
MODIFY_ACTIONS = frozenset({
    "modify", "update", "patch", "revoke", "return", "unseal", "resurrect", "clear", "pardon", "demote",
})


def _now() -> str:
    try:
        spec = importlib.util.spec_from_file_location("sovereign_clock_targets", _LIB / "sovereign-clock.py")
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
    return _load(DOCTRINE, {"semantics": {"kill_means_kill": True}})


def mechanism_spec(mechanism: str) -> dict[str, Any]:
    doc = doctrine()
    mech = str(mechanism or "INTERACT").strip().upper()
    return (doc.get("mechanisms") or {}).get(mech) or {}


def _normalize_mechanism(mechanism: str | None, *, threat_score: float = 0.0, hostility_score: float = 0.0) -> str:
    if mechanism:
        mech = str(mechanism).strip().upper()
        if mech in MECHANISMS:
            return mech
    doc = doctrine()
    rules = doc.get("promotion_rules") or {}
    kill_floor = float(rules.get("kill_floor_threat") or 0.75)
    interact_floor = float(rules.get("interact_floor_hostility") or 0.55)
    if threat_score >= kill_floor:
        return str(rules.get("default_lethal_mechanism") or "KILL")
    if hostility_score >= interact_floor:
        return str(rules.get("default_hostile_mechanism") or "INTERACT")
    return "MONITOR"


def is_kill_target(row: dict[str, Any]) -> bool:
    return str(row.get("mechanism") or row.get("TARGET") or "").upper() == "KILL"


def is_sealed(row: dict[str, Any]) -> bool:
    if not isinstance(row, dict):
        return False
    if row.get("sealed") or row.get("no_modifications"):
        return True
    if is_kill_target(row):
        return True
    spec = mechanism_spec(str(row.get("mechanism") or ""))
    return bool(spec.get("immutable_once_set") or spec.get("no_modifications"))


def _guard_mutation(row: dict[str, Any], action: str) -> dict[str, Any] | None:
    """No returns, no modifications once KILL is set — it dies."""
    if not is_sealed(row):
        return None
    mech = str(row.get("mechanism") or row.get("TARGET") or "KILL").upper()
    return {
        "ok": False,
        "error": "target_sealed_no_modifications",
        "mechanism": mech,
        "TARGET": mech,
        "no_returns": True,
        "no_modifications": True,
        "dies": is_kill_target(row),
        "status": row.get("status"),
        "target_id": row.get("id"),
        "counsel": "Once set, KILL is terminal — no returns, no modifications. It dies.",
    }


def _empty_registry() -> dict[str, Any]:
    return {
        "schema": "hostess7-targets-registry/v1",
        "semantics": {"kill_means_kill": True},
        "mechanisms": sorted(MECHANISMS),
        "targets": {},
        "updated": _now(),
    }


def _load_registry() -> dict[str, Any]:
    reg = _load(REGISTRY, _empty_registry())
    reg.setdefault("targets", {})
    return reg


def _target_key(subject: str, *, ip: str | None = None) -> str:
    if ip:
        return f"ip:{ip}"
    digest = hashlib.sha256(subject.strip().lower().encode()).hexdigest()[:20]
    return f"subj:{digest}"


def _find_target_row(reg: dict[str, Any], *, key: str | None = None, ip: str | None = None, target_id: str | None = None) -> tuple[str | None, dict[str, Any] | None]:
    targets = reg.get("targets") or {}
    if key and key in targets:
        return key, targets[key]
    if ip:
        k = _target_key("", ip=ip)
        if k in targets:
            return k, targets[k]
        for tkey, row in targets.items():
            if isinstance(row, dict) and str(row.get("ip") or "") == ip:
                return tkey, row
    if target_id:
        for tkey, row in targets.items():
            if isinstance(row, dict) and str(row.get("id") or "") == target_id:
                return tkey, row
    return None, None


def _gov_dossier_hits(ip: str | None, text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    gov = _load(STATE / "gov-dossiers.json", {"records": {}})
    records = gov.get("records") or {}
    if isinstance(records, dict):
        for gkey, row in records.items():
            blob = json.dumps(row, default=str).lower()
            if ip and ip in blob:
                hits.append({"source": "gov_dossiers", "key": gkey, "row": row})
            elif text and len(text) > 8 and any(tok in blob for tok in text.lower().split()[:6] if len(tok) > 4):
                hits.append({"source": "gov_dossiers", "key": gkey, "row": row})
    return hits[:12]


def _human_dossier_hits(ip: str | None) -> list[dict[str, Any]]:
    if not ip:
        return []
    hits: list[dict[str, Any]] = []
    live = _load(STATE / "human-dossier.json", {})
    for row in (live.get("ips") or live.get("records") or []):
        if isinstance(row, dict) and str(row.get("ip") or "") == ip:
            hits.append({"source": "human_dossier_live", "row": row})
    bundled = _load(INSTALL / "data" / "human-dossier-kill-orders.json", {})
    for row in bundled.get("ips") or []:
        if isinstance(row, dict) and str(row.get("ip") or "") == ip:
            hits.append({"source": "human_dossier_kill_orders", "row": row})
    return hits


def _census_hits(ip: str | None, geo: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {"source": "census_field", "hits": []}
    cache = _load(STATE / "census-field-cache.json", {})
    if cache:
        out["operator_location"] = _load(STATE / "operator-location.json", {})
        out["gps_table"] = _load(STATE / "home-gps-correlation.json", {})
        out["cache_keys"] = sorted(cache.keys())[:16]
    if geo:
        out["geo_match"] = geo
    if ip:
        out["ip"] = ip
    return out


def _angel_hits(ip: str | None) -> list[dict[str, Any]]:
    if not ip:
        return []
    dossiers = _load(STATE / "angel-dossiers.json", {"dossiers": []})
    hits: list[dict[str, Any]] = []
    for row in dossiers.get("dossiers") or []:
        if not isinstance(row, dict):
            continue
        if ip in json.dumps(row, default=str):
            hits.append({"source": "angel_dossiers", "id": row.get("id"), "vector": row.get("vector")})
    return hits[:8]


def _lethal_slice() -> dict[str, Any]:
    panel = _load(STATE / "lethal-enforcement-panel.json", {})
    if panel:
        return {"source": "lethal_enforcement", "status": panel.get("status"), "merciless": panel.get("merciless")}
    lethal = _import_mod("lethal_targets", "lethal-enforcement.py")
    if lethal and hasattr(lethal, "build_panel"):
        try:
            row = lethal.build_panel(write=False)
            return {"source": "lethal_enforcement", "status": row.get("status"), "merciless": row.get("merciless")}
        except Exception:
            pass
    return {"source": "lethal_enforcement", "present": False}


def correlate_government(*, ip: str | None = None, text: str = "", geo: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": "hostess7-targets-gov-correlate/v1",
        "ok": True,
        "ip": ip,
        "gov_dossiers": _gov_dossier_hits(ip, text),
        "human_dossier": _human_dossier_hits(ip),
        "census": _census_hits(ip, geo),
        "angel": _angel_hits(ip),
        "lethal": _lethal_slice(),
    }


def _apply_mechanism_fields(row: dict[str, Any], mechanism: str) -> dict[str, Any]:
    spec = mechanism_spec(mechanism)
    mech = mechanism.upper()
    row["mechanism"] = mech
    row["TARGET"] = mech
    row["mechanism_spec"] = spec
    if mech == "KILL":
        row["kill_order"] = True
        row["lethal"] = True
        row["dies"] = True
        row["status"] = "dead"
        row["sealed"] = True
        row["no_returns"] = True
        row["no_modifications"] = True
        row["immutable"] = True
        row["killed_at"] = _now()
    else:
        row["kill_order"] = False
        row["lethal"] = False
        row["dies"] = False
        row["status"] = row.get("status") or "active"
        row["sealed"] = bool(spec.get("immutable_once_set"))
        row["no_returns"] = bool(spec.get("no_returns"))
        row["no_modifications"] = bool(spec.get("no_modifications"))
        row["immutable"] = bool(spec.get("immutable_once_set"))
    return row


def promote_target(
    *,
    advisement_id: str | None = None,
    subject: str,
    lane: str = "advisory_channel",
    hostility_score: float = 0.0,
    threat_score: float = 0.0,
    ip: str | None = None,
    geo: dict[str, Any] | None = None,
    counsel: str = "",
    metadata: dict[str, Any] | None = None,
    mechanism: str | None = None,
) -> dict[str, Any]:
    """Promote to TARGET with mechanism — KILL is KILL; INTERACT and others are non-terminal."""
    text = counsel or subject
    if not ip:
        m = IPV4_RE.search(text)
        if m:
            ip = m.group(0)

    mech = _normalize_mechanism(mechanism, threat_score=threat_score, hostility_score=hostility_score)
    key = _target_key(subject, ip=ip)
    reg = _load_registry()
    existing_key, existing = _find_target_row(reg, key=key)
    if existing and is_sealed(existing):
        existing_mech = str(existing.get("mechanism") or existing.get("TARGET") or "").upper()
        if existing_mech == mech:
            if is_kill_target(existing) and existing.get("status") != "dead":
                existing = _apply_mechanism_fields(dict(existing), "KILL")
                reg["targets"][existing_key or key] = existing
                _save(REGISTRY, reg)
            return {
                "ok": True,
                "promoted": False,
                "already_set": True,
                "mechanism": existing_mech,
                "TARGET": existing_mech,
                "target": existing,
                "no_returns": True,
                "no_modifications": True,
            }
        blocked = _guard_mutation(existing, "promote")
        if blocked:
            blocked["error"] = "target_already_sealed"
            return blocked

    gov = correlate_government(ip=ip, text=text, geo=geo)
    gov_boost = 0.0
    if gov.get("human_dossier"):
        gov_boost += 0.15
    if gov.get("angel"):
        gov_boost += 0.10
    if gov.get("gov_dossiers"):
        gov_boost += 0.08
    final_threat = min(1.0, max(threat_score, hostility_score) + gov_boost)

    target_id = str(existing.get("id") if existing else uuid.uuid4())
    row: dict[str, Any] = {
        "id": target_id,
        "key": key,
        "subject": subject,
        "ip": ip,
        "geo": geo,
        "lane": lane,
        "advisement_id": advisement_id,
        "hostility_score": round(hostility_score, 3),
        "threat_score": round(threat_score, 3),
        "final_threat_score": round(final_threat, 3),
        "counsel": counsel[:2000] if counsel else "",
        "government": gov,
        "metadata": metadata or {},
        "promoted_at": _now(),
        "commander": "Hostess 7",
    }
    row = _apply_mechanism_fields(row, mech)
    reg["targets"][key] = row
    reg["updated"] = _now()
    reg["mechanisms"] = sorted(MECHANISMS)
    _save(REGISTRY, reg)
    _append_ledger({
        "event": "promote_target",
        "target_id": target_id,
        "key": key,
        "ip": ip,
        "mechanism": mech,
        "TARGET": mech,
        "dies": row.get("dies"),
    })
    kill_exec: dict[str, Any] = {}
    if mech == "KILL" and ip:
        kc = _import_mod("kill_codes_targets", "kill-codes.py")
        if kc and hasattr(kc, "execute_kill_immediate"):
            kill_exec = kc.execute_kill_immediate(
                ip,
                reason=f"target_kill:{subject[:80]}",
                code="KC-OP-kill",
                extra={"source": "hostess7-targets", "target_id": target_id},
            )
            row["kill_executed"] = bool(kill_exec.get("immediate") or kill_exec.get("killed"))
            row["kill_immediate"] = kill_exec.get("immediate")
            row["kill_law"] = kill_exec.get("law", "immediate_is_best")
            if kill_exec.get("ok"):
                row["status"] = "dead"
            reg["targets"][key] = row
            _save(REGISTRY, reg)
    out: dict[str, Any] = {"ok": True, "promoted": True, "mechanism": mech, "TARGET": mech, "target": row}
    if kill_exec:
        out["kill_execution"] = kill_exec
        out["immediate_is_best"] = bool(kill_exec.get("immediate"))
    if mech == "KILL":
        kl = _import_mod("kill_library", "lib/hostess7-kill-library.py")
        if kl and hasattr(kl, "sync_kill_library"):
            try:
                os.environ["HOSTESS7_KILL_LIBRARY_SYNC"] = "1"
                out["kill_library"] = kl.sync_kill_library()
            except Exception as exc:
                out["kill_library"] = {"ok": False, "error": str(exc)[:120]}
    return out


def modify_target(
    *,
    key: str | None = None,
    ip: str | None = None,
    target_id: str | None = None,
    updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reg = _load_registry()
    tkey, row = _find_target_row(reg, key=key, ip=ip, target_id=target_id)
    if not row or not tkey:
        return {"ok": False, "error": "target_not_found"}
    blocked = _guard_mutation(row, "modify")
    if blocked:
        return blocked
    payload = updates or {}
    for field in ("subject", "counsel", "metadata", "geo", "mechanism", "status", "TARGET"):
        if field in payload:
            row[field] = payload[field]
    if "mechanism" in payload:
        row = _apply_mechanism_fields(row, str(payload["mechanism"]))
    row["updated_at"] = _now()
    reg["targets"][tkey] = row
    reg["updated"] = _now()
    _save(REGISTRY, reg)
    return {"ok": True, "modified": True, "TARGET": row.get("TARGET"), "target": row}


def revoke_target(*, key: str | None = None, ip: str | None = None, target_id: str | None = None) -> dict[str, Any]:
    reg = _load_registry()
    tkey, row = _find_target_row(reg, key=key, ip=ip, target_id=target_id)
    if not row or not tkey:
        return {"ok": False, "error": "target_not_found"}
    blocked = _guard_mutation(row, "revoke")
    if blocked:
        blocked["error"] = "target_no_returns"
        return blocked
    reg["targets"].pop(tkey, None)
    reg["updated"] = _now()
    _save(REGISTRY, reg)
    _append_ledger({"event": "revoke_target", "key": tkey, "TARGET": row.get("TARGET")})
    return {"ok": True, "revoked": True, "key": tkey}


def lookup_target(*, key: str | None = None, ip: str | None = None, target_id: str | None = None) -> dict[str, Any]:
    reg = _load_registry()
    _, row = _find_target_row(reg, key=key, ip=ip, target_id=target_id)
    if not row:
        return {"ok": False, "error": "target_not_found"}
    mech = str(row.get("mechanism") or row.get("TARGET") or "")
    return {"ok": True, "TARGET": mech, "mechanism": mech, "target": row, "sealed": is_sealed(row)}


def sync_government() -> dict[str, Any]:
    reg = _load_registry()
    targets = reg.get("targets") or {}
    updated = 0
    skipped = 0
    for tkey, row in targets.items():
        if not isinstance(row, dict):
            continue
        if is_sealed(row) and is_kill_target(row):
            skipped += 1
            continue
        if row.get("status") not in ("active", "dead", None):
            continue
        gov = correlate_government(
            ip=row.get("ip"),
            text=str(row.get("subject") or "") + " " + str(row.get("counsel") or ""),
            geo=row.get("geo") if isinstance(row.get("geo"), dict) else None,
        )
        row["government"] = gov
        row["gov_synced_at"] = _now()
        targets[tkey] = row
        updated += 1
    reg["targets"] = targets
    reg["updated"] = _now()
    _save(REGISTRY, reg)
    return {"ok": True, "synced": updated, "skipped_sealed_kill": skipped}


def build_panel(*, write: bool = True) -> dict[str, Any]:
    reg = _load_registry()
    doc = doctrine()
    targets = list((reg.get("targets") or {}).values())
    active = [t for t in targets if isinstance(t, dict) and t.get("status") == "active"]
    dead = [t for t in targets if isinstance(t, dict) and t.get("status") == "dead"]
    panel = {
        "schema": "hostess7-targets-panel/v1",
        "ok": True,
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "mechanisms": doc.get("mechanisms") or {},
        "immutability_policy": doc.get("immutability_policy"),
        "kill_means_kill": True,
        "target_count": len(targets),
        "active_count": len(active),
        "dead_count": len(dead),
        "targets": sorted(targets, key=lambda x: x.get("final_threat_score", 0), reverse=True)[:48],
        "government_databases": doc.get("government_databases") or [],
        "updated": _now(),
    }
    if write:
        _save(PANEL, panel)
    return panel


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json", "panel"):
        return {"ok": True, **build_panel(write=action == "panel")}

    if action in ("sync", "sync_government", "gov_sync"):
        return sync_government()

    if action in ("lookup", "get"):
        return lookup_target(
            key=body.get("key"),
            ip=body.get("ip"),
            target_id=body.get("target_id") or body.get("id"),
        )

    if action in ("modify", "update"):
        return modify_target(
            key=body.get("key"),
            ip=body.get("ip"),
            target_id=body.get("target_id") or body.get("id"),
            updates=body.get("updates") if isinstance(body.get("updates"), dict) else body,
        )

    if action in ("revoke", "return", "demote"):
        return revoke_target(
            key=body.get("key"),
            ip=body.get("ip"),
            target_id=body.get("target_id") or body.get("id"),
        )

    mechanism = body.get("mechanism") or body.get("TARGET")
    if action == "interact":
        mechanism = "INTERACT"
    elif action in ("kill", "target_kill"):
        mechanism = "KILL"
    elif action == "monitor":
        mechanism = "MONITOR"

    if action in ("promote", "target", "kill", "interact", "monitor", "observe"):
        return promote_target(
            advisement_id=body.get("advisement_id"),
            subject=str(body.get("subject") or body.get("text") or ""),
            lane=str(body.get("lane") or "manual"),
            hostility_score=float(body.get("hostility_score") or 0),
            threat_score=float(body.get("threat_score") or 0),
            ip=body.get("ip"),
            geo=body.get("geo") if isinstance(body.get("geo"), dict) else None,
            counsel=str(body.get("counsel") or body.get("text") or ""),
            metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
            mechanism=str(mechanism) if mechanism else None,
        )

    if action in ("correlate", "gov", "government"):
        return correlate_government(
            ip=body.get("ip"),
            text=str(body.get("text") or body.get("subject") or ""),
            geo=body.get("geo") if isinstance(body.get("geo"), dict) else None,
        )

    if action in ("mechanisms", "policy"):
        doc = doctrine()
        return {"ok": True, "mechanisms": doc.get("mechanisms"), "immutability_policy": doc.get("immutability_policy")}

    return {"ok": False, "error": "unknown_action"}


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
    if cmd == "sync":
        print(json.dumps(sync_government(), ensure_ascii=False))
        return 0
    if cmd == "mechanisms":
        print(json.dumps(dispatch({"action": "mechanisms"}), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: hostess7-targets.py [json|panel|sync|mechanisms|dispatch]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())