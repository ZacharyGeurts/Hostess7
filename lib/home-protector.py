#!/usr/bin/env pythong
"""Immediate Home Protector — 3-bedroom home airspace detector (WiFi, LAN, ARP)."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SEED = INSTALL / "data" / "home-protector-seed.json"
PANEL_CACHE = STATE / "home-protector-panel.json"
PERMITTED_JSON = STATE / "home-protector-permitted.json"
RF_PANEL = STATE / "field-rf-panel.json"
THREAT_PANEL = STATE / "threat-panel.json"
TRUSTED_TSV = STATE / "firewall-trusted.tsv"
HOSTILE_TSV = STATE / "field-hostile.tsv"
OPS_LOG = STATE / "home-protector-operations.jsonl"

PRIVATE_IP_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.)"
)


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


def _append_log(row: dict[str, Any]) -> None:
    try:
        OPS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with OPS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _seed() -> dict[str, Any]:
    return _load_json(SEED, {"acre_radius_m": 16.8, "acre_radius_ft": 55, "home_profile": "3-bedroom home"})


def _norm_mac(mac: str) -> str:
    return re.sub(r"[^0-9a-f]", "", str(mac or "").lower())[:12]


def _mod(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _acre_radius_m() -> float:
    return float(_seed().get("acre_radius_m") or 16.8)


def _signal_to_est_meters(signal_pct: int) -> float:
    s = max(1, min(100, int(signal_pct or 0)))
    return round(1.2 * (10 ** ((82 - s) / 24.0)), 1)


def _within_acre(est_m: float | None, *, on_lan: bool = False) -> bool:
    if on_lan:
        return True
    if est_m is None:
        return False
    return est_m <= _acre_radius_m()


def _trusted_ips() -> set[str]:
    out: set[str] = set()
    if not TRUSTED_TSV.is_file():
        return out
    for line in TRUSTED_TSV.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.strip().split("\t")
        if parts and re.match(r"^\d+\.\d+\.\d+\.\d+$", parts[0]):
            out.add(parts[0])
    return out


def _hostile_ips() -> set[str]:
    out: set[str] = set()
    if not HOSTILE_TSV.is_file():
        return out
    for line in HOSTILE_TSV.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.strip().split("\t")
        if parts and re.match(r"^\d+\.\d+\.\d+\.\d+$", parts[0]):
            out.add(parts[0])
    return out


def _permitted_doc() -> dict[str, Any]:
    doc = _load_json(PERMITTED_JSON, {"bssids": [], "ips": [], "macs": []})
    doc.setdefault("bssids", [])
    doc.setdefault("ips", [])
    doc.setdefault("macs", [])
    return doc


def _is_permitted(*, bssid: str = "", ip: str = "", mac: str = "") -> bool:
    doc = _permitted_doc()
    trusted = _trusted_ips()
    if ip and ip in trusted:
        return True
    bnorm = _norm_mac(bssid)
    if bnorm and bnorm in {_norm_mac(x) for x in doc.get("bssids") or []}:
        return True
    if ip and ip in (doc.get("ips") or []):
        return True
    mnorm = _norm_mac(mac)
    if mnorm and mnorm in {_norm_mac(x) for x in doc.get("macs") or []}:
        return True
    return False


def _operator_home() -> dict[str, Any]:
    try:
        return _mod("operator_location", "operator-location.py").panel_json()
    except Exception:
        return _load_json(STATE / "operator-location.json", {})


def _own_bssids(rf_doc: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    active = (rf_doc.get("antenna") or {}).get("active_connection") or {}
    if active.get("bssid"):
        out.add(_norm_mac(active["bssid"]))
    for iface in rf_doc.get("interfaces") or []:
        mac = iface.get("mac") or iface.get("hwaddr")
        if mac:
            out.add(_norm_mac(mac))
    return out


def _rf_threat_index(rf_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for t in (rf_doc.get("threats") or []) + (rf_doc.get("recent_threats") or []):
        b = _norm_mac(str(t.get("bssid") or ""))
        if b:
            idx[b] = t
        ip = str(t.get("ip") or "").strip()
        if ip:
            idx[f"ip:{ip}"] = t
    return idx


def _permission_status(
    *,
    permitted: bool,
    hostile: bool,
    threat_kind: str = "",
    on_lan: bool = False,
) -> str:
    if permitted or threat_kind == "home_owned":
        return "home_permitted"
    if hostile or threat_kind in (
        "evil_twin", "rogue_open", "unpermitted_spectrum", "connected_rogue",
        "connected_unpermitted", "hostile_oui", "correlated_hostile_ip",
    ):
        return "unauthorized"
    if on_lan:
        return "neighbor_watch"
    return "neighbor_watch"


def _live_wifi_scan() -> list[dict[str, Any]]:
    try:
        rf = _mod("field_rf", "field-rf-sentinel.py")
        per_scans: dict[str, list[dict[str, Any]]] = {}
        for row in rf._wifi_device_rows():
            dev = str(row.get("device") or "")
            if dev:
                per_scans[dev] = rf._wifi_scan(dev)
        merged, _ = rf._merge_multi_antenna_scans(per_scans)
        return merged
    except Exception:
        return []


def _wifi_entities(rf_doc: dict[str, Any]) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    own = _own_bssids(rf_doc)
    threat_idx = _rf_threat_index(rf_doc)
    scan_rows: list[dict[str, Any]] = list(rf_doc.get("scan_material") or [])
    for ap in rf_doc.get("unpermitted_aps") or []:
        scan_rows.append(ap)
    if not scan_rows:
        scan_rows = _live_wifi_scan()

    seen: set[str] = set()
    for ap in scan_rows:
        bssid = str(ap.get("bssid") or "")
        bnorm = _norm_mac(bssid)
        if not bnorm or bnorm in seen:
            continue
        seen.add(bnorm)
        sig = int(ap.get("signal_dbm") or 0)
        est_m = _signal_to_est_meters(sig)
        if not _within_acre(est_m):
            continue
        threat = threat_idx.get(bnorm) or {}
        permitted = _is_permitted(bssid=bssid) or bnorm in own
        ip = str(threat.get("ip") or ap.get("ip") or "").strip()
        has_threat = bool(threat)
        suspicious_open = bool(ap.get("open")) and sig >= 50 and not permitted
        hostile = has_threat or (ip in _hostile_ips()) or suspicious_open
        status = _permission_status(
            permitted=permitted,
            hostile=hostile,
            threat_kind=str(threat.get("kind") or ("home_owned" if bnorm in own else "")),
        )
        entities.append({
            "entity_id": f"wifi:{bnorm}",
            "kind": "wifi",
            "label": str(ap.get("ssid") or "(hidden)"),
            "bssid": bssid,
            "ip": ip or None,
            "channel": ap.get("channel"),
            "freq_mhz": ap.get("freq_mhz"),
            "band": ap.get("band"),
            "signal": sig,
            "est_distance_m": est_m,
            "est_distance_ft": round(est_m * 3.28084, 0),
            "within_acre": True,
            "permission": status,
            "unauthorized": status == "unauthorized",
            "block_eligible": status == "unauthorized",
            "block_means": "wifi_lawful_kick",
            "threat_kind": threat.get("kind"),
            "security": ap.get("security"),
            "open": bool(ap.get("open")),
            "detail": threat.get("detail") or f"WiFi AP within ~{est_m:.0f} m ({_acre_radius_m():.0f} m home)",
        })
    return entities


def _lan_entities(panel: dict[str, Any]) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    trusted = _trusted_ips()
    hostile = _hostile_ips()
    seen: set[str] = set()

    try:
        geo = _mod("geo_intel", "geo-intel-standards.py")
        arp = geo.load_arp_table()
    except Exception:
        arp = {}

    for ip, mac in sorted(arp.items()):
        if not PRIVATE_IP_RE.match(ip) or ip in seen:
            continue
        seen.add(ip)
        permitted = _is_permitted(ip=ip, mac=mac) or ip in trusted
        is_hostile = ip in hostile
        status = _permission_status(permitted=permitted, hostile=is_hostile, on_lan=True)
        entities.append({
            "entity_id": f"arp:{ip}",
            "kind": "arp",
            "label": f"LAN neighbor {ip}",
            "ip": ip,
            "mac": mac,
            "est_distance_m": 0,
            "est_distance_ft": 0,
            "within_acre": True,
            "on_wire": True,
            "permission": status,
            "unauthorized": status == "unauthorized",
            "block_eligible": status == "unauthorized",
            "block_means": "lan_firewall_block",
            "detail": "On your wire — immediate home airspace",
        })

    gk = panel.get("gatekeeper") or {}
    for conn in gk.get("connections") or []:
        ip = str(conn.get("remote_ip") or "").strip()
        if not PRIVATE_IP_RE.match(ip) or ip in seen:
            continue
        seen.add(ip)
        permitted = _is_permitted(ip=ip) or ip in trusted
        verdict = str(conn.get("verdict") or "")
        is_hostile = ip in hostile or verdict in ("HARM_CANDIDATE", "SUSPICIOUS")
        status = _permission_status(permitted=permitted, hostile=is_hostile, on_lan=True)
        entities.append({
            "entity_id": f"lan:{ip}",
            "kind": "lan",
            "label": str(conn.get("process") or "LAN peer"),
            "ip": ip,
            "mac": arp.get(ip),
            "process": conn.get("process"),
            "verdict": verdict,
            "est_distance_m": 0,
            "within_acre": True,
            "on_wire": True,
            "permission": status,
            "unauthorized": status == "unauthorized",
            "block_eligible": status == "unauthorized",
            "block_means": "lan_firewall_block",
            "detail": f"Live LAN flow · {verdict}",
        })
    return entities


def build_home_protector(harvest: bool = True) -> dict[str, Any]:
    if harvest:
        rf_script = INSTALL / "lib" / "field-rf-sentinel.py"
        if rf_script.is_file():
            subprocess.run(
                [os.environ.get("PYTHON", "pythong"), str(rf_script), "cycle"],
                capture_output=True, timeout=120, env=os.environ.copy(),
            )

    seed = _seed()
    rf_doc = _load_json(RF_PANEL, {})
    panel = _load_json(THREAT_PANEL, {})
    op = _operator_home()

    wifi_entities = _wifi_entities(rf_doc)
    lan_entities = _lan_entities(panel)
    all_entities = wifi_entities + lan_entities
    unauthorized = [e for e in all_entities if e.get("unauthorized")]
    permitted = [e for e in all_entities if e.get("permission") == "home_permitted"]
    watch = [e for e in all_entities if e.get("permission") == "neighbor_watch"]

    out = {
        "schema": "home-protector/v1",
        "updated": _now(),
        "motto": seed.get("motto") or "",
        "acre": {
            "radius_m": seed.get("acre_radius_m", 16.8),
            "radius_ft": seed.get("acre_radius_ft", 55),
            "area_m2": seed.get("acre_area_m2", 887),
            "label": seed.get("home_label") or "3-bedroom home airspace",
            "home_profile": seed.get("home_profile") or "3-bedroom home",
        },
        "operator": {
            "lat": op.get("lat"),
            "lon": op.get("lon"),
            "label": op.get("label") or "",
            "source": op.get("source") or "unset",
        },
        "block_means": seed.get("block_means") or {},
        "stats": {
            "total": len(all_entities),
            "wifi": len(wifi_entities),
            "lan": len(lan_entities),
            "permitted": len(permitted),
            "watch": len(watch),
            "unauthorized": len(unauthorized),
            "block_ready": len([e for e in all_entities if e.get("block_eligible")]),
        },
        "entities": all_entities,
        "unauthorized": unauthorized[:24],
        "table": sorted(
            all_entities,
            key=lambda e: (0 if e.get("unauthorized") else 1, -(e.get("signal") or 0)),
        )[:80],
    }
    _save_json(PANEL_CACHE, out)
    return out


def permit_entity(entity_id: str) -> dict[str, Any]:
    doc = _permitted_doc()
    eid = str(entity_id or "").strip()
    if eid.startswith("wifi:"):
        bnorm = eid.split(":", 1)[-1]
        macs = doc.setdefault("bssids", [])
        if bnorm not in {_norm_mac(x) for x in macs}:
            macs.append(bnorm)
    elif eid.startswith(("lan:", "arp:")):
        ip = eid.split(":", 1)[-1]
        ips = doc.setdefault("ips", [])
        if ip not in ips:
            ips.append(ip)
    else:
        return {"ok": False, "error": "unknown entity_id"}
    doc["updated"] = _now()
    _save_json(PERMITTED_JSON, doc)
    _append_log({"ts": _now(), "action": "permit", "entity_id": eid})
    return {"ok": True, "entity_id": eid, "permitted": doc}


def block_entity(entity_id: str, *, force: bool = False) -> dict[str, Any]:
    doc = build_home_protector(harvest=False)
    hit = next((e for e in doc.get("entities") or [] if e.get("entity_id") == entity_id), None)
    if not hit:
        return {"ok": False, "error": "entity_not_found", "entity_id": entity_id}
    if not hit.get("block_eligible") and not force:
        return {"ok": False, "error": "not_block_eligible", "entity_id": entity_id, "permission": hit.get("permission")}

    kind = hit.get("kind")
    result: dict[str, Any] = {"entity_id": entity_id, "kind": kind}

    if kind == "wifi":
        try:
            rf = _mod("field_rf", "field-rf-sentinel.py")
            threat = {
                "kind": hit.get("threat_kind") or "rogue_open",
                "severity": "critical",
                "ssid": hit.get("label"),
                "bssid": hit.get("bssid"),
                "channel": hit.get("channel"),
                "freq_mhz": hit.get("freq_mhz"),
                "ip": hit.get("ip"),
                "detail": f"home_protector_block:{entity_id}",
            }
            result["rf_disable"] = rf._disable_unhealthy_forever(threat)
        except Exception as exc:
            result["rf_disable"] = {"ok": False, "error": str(exc)}
        ip = str(hit.get("ip") or "").strip()
        if ip and PRIVATE_IP_RE.match(ip):
            try:
                kit = _mod("attack_kit", "field-attack-kit.py")
                result["strike"] = kit.forever_disable_ip(
                    ip, "HOME_AIRSPACE_INTRUDER", "critical", "home_protector_unauthorized_entry",
                )
            except Exception as exc:
                result["strike"] = {"ok": False, "error": str(exc)}

    elif kind in ("lan", "arp"):
        ip = str(hit.get("ip") or "").strip()
        if not ip:
            return {"ok": False, "error": "no_ip", "entity_id": entity_id}
        try:
            kit = _mod("attack_kit", "field-attack-kit.py")
            result["strike"] = kit.forever_disable_ip(
                ip, "HOME_AIRSPACE_INTRUDER", "critical", "home_protector_lan_intruder",
            )
        except Exception as exc:
            result["strike"] = {"ok": False, "error": str(exc)}

    else:
        return {"ok": False, "error": "unsupported_kind", "kind": kind}

    result["ok"] = True
    result["ts"] = _now()
    result["action"] = "blocked_from_airspace"
    result["means"] = hit.get("block_means")
    _append_log(result)
    return result


def block_all_unauthorized() -> dict[str, Any]:
    doc = build_home_protector(harvest=False)
    results = []
    for ent in doc.get("unauthorized") or []:
        if ent.get("block_eligible"):
            results.append(block_entity(str(ent.get("entity_id")), force=True))
    return {
        "ok": True,
        "blocked": len([r for r in results if r.get("ok")]),
        "results": results,
    }


def panel_json() -> dict[str, Any]:
    cached = _load_json(PANEL_CACHE, {})
    if cached.get("updated"):
        return cached
    return build_home_protector(harvest=True)


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(build_home_protector(harvest=True), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_home_protector(harvest=False), ensure_ascii=False))
        return 0
    if cmd == "permit" and len(sys.argv) >= 3:
        print(json.dumps(permit_entity(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd == "block" and len(sys.argv) >= 3:
        force = "--force" in sys.argv
        print(json.dumps(block_entity(sys.argv[2], force=force), ensure_ascii=False))
        return 0
    if cmd == "block-all":
        print(json.dumps(block_all_unauthorized(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: home-protector.py [json|build|permit ID|block ID|block-all]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())