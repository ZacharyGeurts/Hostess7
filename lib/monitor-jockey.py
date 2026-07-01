#!/usr/bin/env pythong
"""Field alerts + operator actions for Hostess 7 and the Actions tab."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ALERT_ID_RE = re.compile(r"^[a-zA-Z0-9:_\-.]{1,256}$")
_VALID_RESPONSES = frozenset({"seen", "needs_action", "needs_more_action"})
_ACKS_MAX_BYTES = 2_000_000

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parent.parent))
ACKS_PATH = STATE / "monitor-jockey-acks.jsonl"
ALERTS_PANEL = STATE / "monitor-jockey-alerts.json"


def _ellie_threat_warn_level() -> str:
    try:
        cached = json.loads((STATE / "field-ellie-security-authority.json").read_text(encoding="utf-8"))
        if cached.get("threat_warn_level"):
            return str(cached["threat_warn_level"])
    except (OSError, json.JSONDecodeError):
        pass
    return "high"


VERDICT_PRIORITY = {
    "HARM_CANDIDATE": 90,
    "SUSPICIOUS": 70,
    "MONITOR": 50,
    "EPHEMERAL": 30,
    "USER_OK": 10,
}


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _sanitize_text(value: Any, *, limit: int = 320) -> str:
    text = str(value or "").replace("\x00", "").strip()
    return text[:limit]


def _load_acks() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not ACKS_PATH.is_file():
        return out
    try:
        for line in ACKS_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            aid = str(row.get("alert_id") or "")
            if aid and _ALERT_ID_RE.match(aid):
                out[aid] = row
    except OSError:
        pass
    return out


def _rotate_acks_if_needed() -> None:
    try:
        if ACKS_PATH.is_file() and ACKS_PATH.stat().st_size > _ACKS_MAX_BYTES:
            lines = ACKS_PATH.read_text(encoding="utf-8").splitlines()
            keep = lines[-4000:] if len(lines) > 4000 else lines
            tmp = ACKS_PATH.with_suffix(".rotate.tmp")
            tmp.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
            tmp.replace(ACKS_PATH)
    except OSError:
        pass


def ack_alert(alert_id: str, response: str, *, note: str = "") -> dict[str, Any]:
    """response: seen | needs_action"""
    aid = str(alert_id or "").strip()[:256]
    resp = str(response or "seen").strip().lower()
    if not aid:
        return {"ok": False, "error": "missing alert_id"}
    if not _ALERT_ID_RE.match(aid):
        return {"ok": False, "error": "invalid alert_id"}
    if resp not in _VALID_RESPONSES:
        return {"ok": False, "error": "invalid response"}
    if resp == "needs_more_action":
        resp = "needs_action"
    note_clean = _sanitize_text(note, limit=512)
    row = {
        "alert_id": aid,
        "response": resp,
        "note": note_clean,
        "ts": _now(),
    }
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        _rotate_acks_if_needed()
        with ACKS_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, **row}


def _alert(
    aid: str,
    *,
    title: str,
    detail: str,
    severity: str,
    source: str,
    category: str = "field",
    unidentified: bool = False,
    jump: str = "",
    entity_id: str = "",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": _sanitize_text(aid, limit=256),
        "title": _sanitize_text(title, limit=160),
        "detail": _sanitize_text(detail, limit=400),
        "severity": severity if severity in VERDICT_PRIORITY else "MONITOR",
        "source": _sanitize_text(source, limit=48),
        "category": _sanitize_text(category, limit=32),
        "unidentified": bool(unidentified),
        "jump": _sanitize_text(jump, limit=64),
        "entity_id": _sanitize_text(entity_id, limit=128),
        "meta": meta or {},
        "priority": VERDICT_PRIORITY.get(severity, 40),
    }


def _gatekeeper_alerts(acks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    doc = _load_json(STATE / "connection-intent.json", {})
    rows: list[dict[str, Any]] = []
    for conn in doc.get("connections") or []:
        if not isinstance(conn, dict):
            continue
        verdict = str(conn.get("verdict") or conn.get("dpi", {}).get("verdict") or "")
        if verdict not in ("HARM_CANDIDATE", "SUSPICIOUS", "MONITOR"):
            continue
        ip = str(conn.get("remote_ip") or conn.get("dst_ip") or "")
        proc = str(conn.get("process") or conn.get("who") or "unknown")
        port = str(conn.get("remote_port") or conn.get("dst_port") or "")
        aid = f"gk:{ip}:{port}:{proc}"
        if aid in acks and acks[aid].get("response") == "seen":
            continue
        unidentified = "unidentified" in str(conn.get("notes") or "").lower() or proc in ("?", "unknown", "—")
        sug = conn.get("suggestion") or {}
        rows.append(_alert(
            aid,
            title=f"{verdict.replace('_', ' ')} · {ip}:{port}",
            detail=str(sug.get("action") or conn.get("translation") or conn.get("purpose") or proc)[:280],
            severity=verdict,
            source="gatekeeper",
            category="connection",
            unidentified=unidentified,
            jump="packets/monitor" if not unidentified else "threats/human-dossier",
            meta={"ip": ip, "port": port, "process": proc, "verdict": verdict},
        ))
    return rows


def _scour_panel_path() -> Path | None:
    for candidate in (
        STATE / "spiderweb" / "spiderweb-scour-panel.json",
        STATE / "spiderweb-scour-panel.json",
        Path("/home/default/Desktop/SG/Spiderweb/state/spiderweb-scour-panel.json"),
    ):
        if candidate.is_file():
            return candidate
    return None


def _scour_alerts(acks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    path = _scour_panel_path()
    doc = _load_json(path, {}) if path else {}
    rows: list[dict[str, Any]] = []
    for node in doc.get("nodes") or []:
        if not isinstance(node, dict) or not node.get("is_new"):
            continue
        eid = str(node.get("entity_id") or node.get("id") or "")
        aid = f"scour:{eid}"
        if aid in acks and acks[aid].get("response") == "seen":
            continue
        label = str(node.get("label") or node.get("ip") or eid)
        rows.append(_alert(
            aid,
            title=f"New on scour · {label}",
            detail=f"{node.get('ip', '')} · {node.get('process', '')} · MAC {node.get('mac', '—')}".strip(),
            severity="SUSPICIOUS",
            source="scour",
            category="scour",
            unidentified=True,
            jump="threats/scour-net",
            entity_id=eid,
            meta={"ip": node.get("ip"), "mac": node.get("mac"), "process": node.get("process")},
        ))
    return rows


def _dpi_alerts(acks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    doc = _load_json(STATE / "packet-field.json", {})
    rows: list[dict[str, Any]] = []
    for pkt in (doc.get("recent") or [])[:40]:
        if not isinstance(pkt, dict):
            continue
        dpi = pkt.get("dpi") or {}
        if not dpi.get("alert"):
            continue
        aid = f"dpi:{pkt.get('ts', '')}:{pkt.get('dst_ip', '')}:{pkt.get('dst_port', '')}"
        if aid in acks and acks[aid].get("response") == "seen":
            continue
        rows.append(_alert(
            aid,
            title=f"DPI alert · {pkt.get('dst_ip', '?')}:{pkt.get('dst_port', '?')}",
            detail=str(dpi.get("translation") or dpi.get("intent") or "Harmful segment detected")[:280],
            severity="HARM_CANDIDATE",
            source="dpi",
            category="packet",
            unidentified=False,
            jump="packets/inspect",
            meta={"confidence": dpi.get("confidence"), "vector": dpi.get("vector")},
        ))
    return rows


def _hazard_alerts(acks: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    doc = _load_json(STATE / "field-hazard-onset-panel.json", {})
    rows: list[dict[str, Any]] = []
    for ev in (doc.get("recent_cease") or doc.get("events") or [])[:12]:
        if not isinstance(ev, dict):
            continue
        aid = f"hazard:{ev.get('id') or ev.get('ts', '')}"
        if aid in acks and acks[aid].get("response") == "seen":
            continue
        rows.append(_alert(
            aid,
            title=f"Field hazard · {ev.get('band', 'RF')}",
            detail=str(ev.get("reason") or ev.get("action") or "Hazard onset detected")[:280],
            severity="HARM_CANDIDATE",
            source="hazard",
            category="rf",
            jump="signals",
            meta=ev,
        ))
    return rows


def _threat_warn_floor() -> str:
    if os.environ.get("NEXUS_THREAT_WARN_LEVEL", "high").strip().lower() in ("low", "medium", "calm", "off"):
        return "alert"
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("nexus_logic_gate", INSTALL / "lib" / "nexus-logic-gate.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return str(mod.threat_posture_floor())
    except Exception:
        pass
    return "alert"


def _posture(pending: list[dict[str, Any]]) -> str:
    floor = _threat_warn_floor()
    if not pending:
        return floor if floor != "watch" else "calm"
    severities = {str(a.get("severity") or "") for a in pending}
    if "HARM_CANDIDATE" in severities:
        return "harm"
    if "SUSPICIOUS" in severities or floor == "alert":
        return "alert"
    if "MONITOR" in severities:
        return "watch"
    return floor


def _split_queues(pool: list[dict[str, Any]], acks: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """H7 instant alerts = never acked. Jockey queue = unacked + needs_action (not seen)."""
    h7: list[dict[str, Any]] = []
    jockey: list[dict[str, Any]] = []
    for a in pool:
        aid = a["id"]
        resp = (acks.get(aid) or {}).get("response")
        if resp == "seen":
            continue
        if aid not in acks:
            h7.append(a)
        if aid not in acks or resp == "needs_action":
            jockey.append(a)
    return h7, jockey


def build_alerts(*, write: bool = True) -> dict[str, Any]:
    acks = _load_acks()
    pool: list[dict[str, Any]] = []
    pool.extend(_gatekeeper_alerts(acks))
    pool.extend(_scour_alerts(acks))
    pool.extend(_dpi_alerts(acks))
    pool.extend(_hazard_alerts(acks))
    pool.sort(key=lambda a: (-int(a.get("priority") or 0), a.get("title", "")))
    h7_alerts, jockey_alerts = _split_queues(pool, acks)
    posture = _posture(h7_alerts + jockey_alerts)
    doc = {
        "schema": "monitor-jockey-alerts/v1",
        "updated": _now(),
        "posture": posture,
        "threat_warn_level": _ellie_threat_warn_level(),
        "motto": "Instant alerts require operator response — presume hostile injection until verified.",
        "pending_count": len(jockey_alerts),
        "h7_count": len(h7_alerts),
        "total_count": len(pool),
        "alerts": h7_alerts[:24],
        "jockey_alerts": jockey_alerts[:32],
        "all_alerts": pool[:48],
    }
    if write:
        _save_json(ALERTS_PANEL, doc)
    return doc


def _kill_code_actions(alert: dict[str, Any] | None) -> list[dict[str, Any]]:
    try:
        kc = _import_kill_codes()
        codes = kc.recommend_for_alert(alert)
        return kc.actions_from_codes(codes)
    except Exception:
        return []


def _import_kill_codes() -> Any:
    import importlib.util
    spec = importlib.util.spec_from_file_location("kill_codes", INSTALL / "lib" / "kill-codes.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def build_actions(*, alert: dict[str, Any] | None = None) -> dict[str, Any]:
    """Operator actions catalog — especially for unidentifieds."""
    actions: list[dict[str, Any]] = []
    actions.extend(_kill_code_actions(alert))
    actions.extend([
        {"id": "act:scour", "label": "Active scour map", "jump": "threats/scour-net", "tier": "watch"},
        {"id": "act:gatekeeper", "label": "Live connections", "jump": "packets/monitor", "tier": "watch"},
        {"id": "act:dpi", "label": "DPI inspect", "jump": "packets/inspect", "tier": "investigate"},
        {"id": "act:kill-orders", "label": "Kill orders · HeavyBoi", "jump": "threats/human-dossier", "tier": "lethal"},
        {"id": "act:host-attack", "label": "Globe · host attack", "jump": "threats/host-attack", "tier": "map"},
        {"id": "act:home", "label": "Home protector", "jump": "threats/home-protector", "tier": "defend"},
        {"id": "act:holes", "label": "Local holes", "jump": "threats/local-holes", "tier": "defend"},
        {"id": "act:spiderweb", "label": "Spiderweb field", "jump": "threats/spiderweb", "tier": "intel"},
        {"id": "act:command", "label": "Ask Hostess 7", "jump": "command", "tier": "assist"},
        {"id": "act:library", "label": "Quiet library", "jump": "library", "tier": "rest"},
    ])
    gk = _load_json(STATE / "connection-intent.json", {})
    for conn in (gk.get("connections") or [])[:8]:
        if not isinstance(conn, dict):
            continue
        v = str(conn.get("verdict") or "")
        if v not in ("HARM_CANDIDATE", "SUSPICIOUS"):
            continue
        ip = conn.get("remote_ip") or ""
        proc = conn.get("process") or "?"
        actions.insert(0, {
            "id": f"act:conn:{ip}",
            "label": f"Review {ip} · {proc}",
            "jump": "packets/monitor",
            "tier": "urgent",
            "detail": str((conn.get("suggestion") or {}).get("action") or ""),
            "meta": {"ip": ip, "verdict": v},
        })
    if alert and alert.get("unidentified"):
        actions.insert(0, {
            "id": "act:identify",
            "label": "Identify unknown · kill orders",
            "jump": "threats/human-dossier",
            "tier": "urgent",
            "detail": "Unidentified entity — dossier and classify before block.",
        })
    if alert and alert.get("entity_id"):
        actions.insert(0, {
            "id": f"act:like:{alert['entity_id']}",
            "label": "Mark green (liked) on scour",
            "api": "/api/spiderweb/like",
            "method": "POST",
            "body": {"entity_id": alert["entity_id"]},
            "tier": "trust",
        })
    return {
        "schema": "monitor-jockey-actions/v1",
        "updated": _now(),
        "title": "Operator actions",
        "actions": actions[:20],
    }


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in ("alerts", "build"):
        print(json.dumps(build_alerts(), ensure_ascii=False, indent=2))
        return 0
    if args[0] == "actions":
        alert = None
        if len(args) > 1:
            doc = build_alerts(write=False)
            aid = args[1]
            alert = next(
                (a for a in (doc.get("all_alerts") or []) if a["id"] == aid),
                None,
            )
        print(json.dumps(build_actions(alert=alert), ensure_ascii=False, indent=2))
        return 0
    if args[0] == "ack" and len(args) >= 3:
        print(json.dumps(ack_alert(args[1], args[2], note=args[3] if len(args) > 3 else ""), indent=2))
        return 0
    print("usage: monitor-jockey.py [alerts|actions [alert_id]|ack <id> seen|needs_action]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())