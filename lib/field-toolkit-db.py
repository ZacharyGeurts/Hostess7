#!/usr/bin/env pythong
"""Hell Kit — field toolkit with sever, regional disable, and human threat sweep."""
from __future__ import annotations

import importlib.util
import json
import os
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SEED = INSTALL / "data" / "field-toolkit-seed.json"
USER = STATE / "field-toolkit-user.json"
HOST_ATTACKS = STATE / "host-attacks.json"
HOSTILE_TSV = STATE / "field-hostile.tsv"
HUMAN_DOSSIER = STATE / "human-dossier.json"
PRECISION_PANEL = STATE / "precision-field-panel.json"
DISABLE_LOG = STATE / "hell-kit-disable-log.jsonl"

SEVER_DURATION_SEC = 86400
REGIONAL_MAX_IPS = 48
HUMAN_THREAT_MAX_IPS = 32


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


def _seed() -> dict[str, Any]:
    return _load_json(SEED, {"attacks": [], "defenses": []})


def _user() -> dict[str, Any]:
    return _load_json(USER, {"defense_overrides": {}, "study_notes": {}, "updated": None})


def _mod(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _defense_enabled(defn: dict[str, Any], overrides: dict[str, Any]) -> bool:
    did = str(defn.get("id") or "")
    if did in overrides:
        return bool(overrides[did])
    return bool(defn.get("default", False))


def _disabled_ips() -> set[str]:
    ips: set[str] = set()
    if not HOSTILE_TSV.is_file():
        return ips
    try:
        for line in HOSTILE_TSV.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 2 and parts[1]:
                ips.add(parts[1])
    except OSError:
        pass
    return ips


def _log_disable(entry: dict[str, Any]) -> None:
    try:
        DISABLE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with DISABLE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), **entry}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def list_disablement_profiles() -> list[dict[str, Any]]:
    return list(_seed().get("disablement_profiles") or [])


def list_attacks(category: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
    rows = list(_seed().get("attacks") or [])
    if category:
        rows = [r for r in rows if r.get("category") == category]
    if query:
        q = query.lower()
        rows = [
            r for r in rows
            if q in str(r.get("label") or "").lower()
            or q in str(r.get("vector") or "").lower()
            or q in str(r.get("study") or "").lower()
            or any(q in str(i).lower() for i in (r.get("indicators") or []))
        ]
    return rows


def get_attack(attack_id: str) -> dict[str, Any] | None:
    for row in _seed().get("attacks") or []:
        if str(row.get("id")) == attack_id:
            udoc = _user()
            notes = (udoc.get("study_notes") or {}).get(attack_id)
            out = dict(row)
            if notes:
                out["operator_notes"] = notes
            return out
    return None


def list_defenses() -> list[dict[str, Any]]:
    udoc = _user()
    overrides = udoc.get("defense_overrides") or {}
    out: list[dict[str, Any]] = []
    for row in _seed().get("defenses") or []:
        did = str(row.get("id") or "")
        out.append({
            **row,
            "enabled": _defense_enabled(row, overrides),
        })
    return out


def toggle_defense(defense_id: str, enabled: bool | None = None) -> dict[str, Any]:
    seed_ids = {str(d.get("id")) for d in (_seed().get("defenses") or [])}
    if defense_id not in seed_ids:
        return {"ok": False, "error": "unknown_defense"}
    udoc = _user()
    overrides = dict(udoc.get("defense_overrides") or {})
    if enabled is None:
        seed = next(d for d in (_seed().get("defenses") or []) if d.get("id") == defense_id)
        enabled = not _defense_enabled(seed, overrides)
    overrides[defense_id] = bool(enabled)
    udoc["defense_overrides"] = overrides
    udoc["updated"] = _now()
    _save_json(USER, udoc)
    return {"ok": True, "defense_id": defense_id, "enabled": bool(enabled)}


def add_study_note(attack_id: str, note: str) -> dict[str, Any]:
    if not get_attack(attack_id):
        return {"ok": False, "error": "unknown_attack"}
    udoc = _user()
    notes = dict(udoc.get("study_notes") or {})
    prev = str(notes.get(attack_id) or "").strip()
    merged = f"{prev}\n{note}".strip() if prev and note.strip() else (note.strip() or prev)
    notes[attack_id] = merged
    udoc["study_notes"] = notes
    udoc["updated"] = _now()
    _save_json(USER, udoc)
    return {"ok": True, "attack_id": attack_id}


def _geo_from_row(row: dict[str, Any]) -> dict[str, str]:
    geo = row.get("geo") if isinstance(row.get("geo"), dict) else {}
    return {
        "region": str(row.get("region") or geo.get("region") or ""),
        "country": str(row.get("country") or geo.get("country") or ""),
        "country_code": str(row.get("country_code") or geo.get("country_code") or ""),
        "state": str(row.get("state") or geo.get("state") or ""),
        "city": str(row.get("city") or geo.get("city") or ""),
        "asn": str(row.get("asn") or row.get("asn_org") or geo.get("asn") or ""),
    }


def _collect_target_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(ip: str, source: str, row: dict[str, Any]) -> None:
        if not ip or ip in seen:
            return
        seen.add(ip)
        g = _geo_from_row(row)
        rows.append({
            "ip": ip,
            "source": source,
            "vector": str(row.get("vector") or "HOSTILE"),
            "severity": str(row.get("severity") or "high"),
            "label": str(row.get("label") or row.get("id") or ip),
            **g,
            "hostility_score": int(row.get("hostility_score") or 0),
            "soul_side": str(row.get("soul_side") or ""),
            "malware": str(row.get("associated_malware") or row.get("malware") or ""),
        })

    ha = _load_json(HOST_ATTACKS, {})
    for p in ha.get("points") or []:
        if isinstance(p, dict) and p.get("ip"):
            add(str(p["ip"]), "host_attack", p)

    hd = _load_json(HUMAN_DOSSIER, {})
    if not hd.get("ips"):
        bundled = INSTALL / "data" / "human-dossier-kill-orders.json"
        if bundled.is_file():
            hd = _load_json(bundled, {})
    for row in hd.get("ips") or []:
        if isinstance(row, dict) and row.get("ip"):
            add(str(row["ip"]), "human_dossier", {
                **row,
                "vector": "HUMAN_THREAT",
                "severity": "critical",
            })

    pf = _load_json(PRECISION_PANEL, {})
    for e in pf.get("entities") or []:
        if isinstance(e, dict) and e.get("ip"):
            add(str(e["ip"]), "precision_field", e)
        elif isinstance(e, dict) and e.get("lat") is not None:
            eid = str(e.get("id") or "")
            if eid and not e.get("ip"):
                continue

    return rows


def list_regions() -> list[dict[str, Any]]:
    """Aggregate regional clusters for Hell Kit regional disable."""
    buckets: dict[str, dict[str, Any]] = {}
    for row in _collect_target_rows():
        for field in ("country_code", "country", "region", "state", "asn"):
            val = str(row.get(field) or "").strip()
            if not val or val.lower() in ("unknown", "—", "-"):
                continue
            key = f"{field}:{val}"
            bucket = buckets.setdefault(key, {
                "key": key,
                "field": field,
                "value": val,
                "label": f"{field} · {val}",
                "ips": [],
                "sources": set(),
            })
            if row["ip"] not in bucket["ips"]:
                bucket["ips"].append(row["ip"])
            bucket["sources"].add(row["source"])
    out = []
    for b in sorted(buckets.values(), key=lambda x: (-len(x["ips"]), x["key"])):
        out.append({
            "key": b["key"],
            "field": b["field"],
            "value": b["value"],
            "label": b["label"],
            "ip_count": len(b["ips"]),
            "ips": b["ips"][:12],
            "sources": sorted(b["sources"]),
        })
    return out[:64]


def sever_target(ip: str, vector: str = "HELL_SEVER", severity: str = "high", reason: str = "hell_kit_sever") -> dict[str, Any]:
    """Sever wire — teardown connections + temp firewall block. Not forever kill."""
    ip = str(ip or "").strip()
    if not ip:
        return {"ok": False, "error": "missing_ip", "mode": "sever"}

    fg = _mod("friendly_guard", "friendly-guard.py")
    refuse, guard_reason = fg.refuse_kill(ip, monitor=None)
    if refuse:
        return {"ok": False, "ip": ip, "mode": "sever", "friendly_refused": True, "reason": guard_reason}

    teardown = 0
    hw = INSTALL / "lib" / "hardware-destruction.sh"
    if hw.is_file():
        env = {**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)}
        proc = subprocess.run(
            ["bash", "-c", f"source '{INSTALL}/lib/nexus-common.sh'; source '{hw}'; nexus_hardware_destroy_teardown_connections '{ip}'"],
            capture_output=True, text=True, timeout=20, env=env,
        )
        try:
            teardown = int((proc.stdout or "0").strip() or 0)
        except ValueError:
            teardown = 0

    blocked = False
    fw = INSTALL / "lib" / "firewall-sentinel.sh"
    if fw.is_file():
        env = {**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)}
        proc = subprocess.run(
            [
                "bash", "-c",
                (
                    f"source '{INSTALL}/lib/nexus-common.sh'; source '{fw}'; "
                    f"nexus_firewall_block_ip in '{ip}' '{SEVER_DURATION_SEC}' '{reason}' && "
                    f"nexus_firewall_block_ip out '{ip}' '{SEVER_DURATION_SEC}' '{reason}'"
                ),
            ],
            capture_output=True, text=True, timeout=15, env=env,
        )
        blocked = proc.returncode == 0

    entry = {
        "ok": True,
        "ip": ip,
        "mode": "sever",
        "vector": vector,
        "severity": severity,
        "reason": reason,
        "connections_teardown": teardown,
        "firewall_blocked": blocked,
        "duration_sec": SEVER_DURATION_SEC,
        "motto": "Hell goes to Hell — wire severed.",
    }
    _log_disable(entry)
    return entry


def _match_region(row: dict[str, Any], field: str, value: str) -> bool:
    val = str(value or "").strip().lower()
    if not val:
        return False
    candidate = str(row.get(field) or "").strip().lower()
    if candidate == val:
        return True
    if field == "asn" and val in str(row.get("asn") or "").lower():
        return True
    return False


def regional_disable(
    region: str,
    *,
    field: str = "region",
    max_ips: int = REGIONAL_MAX_IPS,
    mode: str = "forever",
) -> dict[str, Any]:
    """Batch disable all hostiles in a region/country/ASN cluster."""
    value = str(region or "").strip()
    if not value:
        return {"ok": False, "error": "missing_region", "mode": "regional"}

    if ":" in value:
        parts = value.split(":", 1)
        if len(parts) == 2 and parts[0] in ("region", "country", "country_code", "state", "asn"):
            field, value = parts[0], parts[1]

    targets = [
        r for r in _collect_target_rows()
        if _match_region(r, field, value)
    ]
    try:
        hp = _mod("hostility_priority", "hostility-priority.py")
        targets = hp.sort_hell_first(targets)
    except Exception:
        targets.sort(key=lambda r: (-int(r.get("hostility_score") or 0), r.get("ip") or ""))

    disabled = _disabled_ips()
    kit = _mod("field_attack_kit", "field-attack-kit.py")
    results: list[dict[str, Any]] = []
    severed: list[str] = []
    killed: list[str] = []
    skipped: list[str] = []

    for row in targets[:max_ips]:
        ip = row["ip"]
        if ip in disabled:
            skipped.append(ip)
            continue
        vector = str(row.get("vector") or "HELL_REGIONAL")
        severity = str(row.get("severity") or "critical")
        if mode == "sever":
            res = sever_target(ip, vector=vector, severity=severity, reason=f"hell_regional:{field}:{value}")
            if res.get("ok"):
                severed.append(ip)
            results.append(res)
        else:
            res = kit.kill_target(ip, vector, severity, f"hell_regional:{field}:{value}")
            results.append(res)
            if res.get("ok") or res.get("killed"):
                killed.append(ip)
            elif res.get("friendly_refused") or res.get("nokill_refused"):
                skipped.append(ip)

    out = {
        "ok": True,
        "mode": "regional",
        "field": field,
        "region": value,
        "matched": len(targets),
        "processed": len(results),
        "severed": severed,
        "killed": killed,
        "skipped": skipped,
        "severed_count": len(severed),
        "killed_count": len(killed),
        "skipped_count": len(skipped),
        "motto": "Hell goes to Hell — regional disablement complete.",
    }
    _log_disable(out)
    return out


def human_threat_disable(max_ips: int = HUMAN_THREAT_MAX_IPS) -> dict[str, Any]:
    """Sweep Grok Heavy human dossier — human threat itself."""
    hd = _load_json(HUMAN_DOSSIER, {})
    if not hd.get("ips"):
        bundled = INSTALL / "data" / "human-dossier-kill-orders.json"
        if bundled.is_file():
            hd = _load_json(bundled, {})

    ips_rows = [r for r in (hd.get("ips") or []) if isinstance(r, dict) and r.get("ip")]
    if not ips_rows:
        return {"ok": False, "error": "no_human_dossier", "mode": "human_threat"}

    disabled = _disabled_ips()
    kit = _mod("field_attack_kit", "field-attack-kit.py")
    killed: list[str] = []
    skipped: list[str] = []
    refused: list[str] = []

    for row in ips_rows[:max_ips]:
        ip = str(row["ip"])
        if ip in disabled:
            skipped.append(ip)
            continue
        malware = str(row.get("associated_malware") or "unknown")
        res = kit.kill_target(
            ip,
            "HUMAN_THREAT",
            "critical",
            f"hell_human_threat:{malware}",
            extra={"human_dossier": row, "source": "human-dossier"},
        )
        if res.get("ok") or res.get("killed"):
            killed.append(ip)
        elif res.get("friendly_refused"):
            refused.append(ip)
        else:
            skipped.append(ip)

    out = {
        "ok": True,
        "mode": "human_threat",
        "total_dossier": len(ips_rows),
        "killed": killed,
        "killed_count": len(killed),
        "skipped": skipped,
        "refused_heaven": refused,
        "motto": "Hell goes to Hell — human threat itself swept.",
        "analyst": hd.get("analyst"),
    }
    _log_disable(out)
    return out


def hell_rip() -> dict[str, Any]:
    """Invoke Heaven/Hell rip — Hell-chosen only."""
    hh = _mod("heaven_hell", "heaven-hell.py")
    out = hh.rip_hell()
    out["mode"] = "hell_rip"
    out["motto"] = "Hell goes to Hell — rip complete."
    _log_disable({"mode": "hell_rip", "ripped_count": out.get("ripped_count", 0)})
    return out


FIELD_DIE_SIGNAL_THRESHOLD = 6
FIELD_DIE_NOISE_RATIO = 0.94


def _instant_depth_snap_on_field_die() -> dict[str, Any]:
    """Instant single-field-depth check — snap dimensional pits on field die."""
    script = INSTALL / "lib" / "field-depth-singularizer.py"
    if not script.is_file():
        return {"ok": False, "error": "singularizer_missing", "instant": True}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("field_depth_die", script)
        if not spec or not spec.loader:
            return {"ok": False, "error": "singularizer_load_failed", "instant": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "instant_field_die_check"):
            return mod.instant_field_die_check({})
        if hasattr(mod, "snap_dimensional_pits"):
            out = mod.snap_dimensional_pits(body={})
            out["field_die"] = True
            return out
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120], "instant": True}
    return {"ok": False, "error": "singularizer_no_hook", "instant": True}


def field_die_roll(ip: str | None = None) -> dict[str, Any]:
    """AMOURANTHRTX Field Die — 94% noise, 6% signal. Signal may sever top hostile."""
    depth_snap = _instant_depth_snap_on_field_die()
    roll = random.randint(1, 20)
    signal = roll <= FIELD_DIE_SIGNAL_THRESHOLD
    targets = _collect_target_rows()
    disabled = _disabled_ips()
    active = [t for t in targets if t["ip"] not in disabled]
    active.sort(key=lambda r: (-int(r.get("hostility_score") or 0), r["ip"]))
    pick = str(ip or "").strip() or (active[0]["ip"] if active else "")
    pick_row = next((t for t in active if t["ip"] == pick), active[0] if active else None)

    out: dict[str, Any] = {
        "ok": True,
        "mode": "field_die",
        "depth_snap": depth_snap,
        "pits_snapped": int(depth_snap.get("pits_snapped") or 0),
        "roll": roll,
        "dice": f"d20={roll}",
        "signal": signal,
        "verdict": "signal" if signal else "noise",
        "noise_ratio": FIELD_DIE_NOISE_RATIO,
        "signal_ratio": round(1.0 - FIELD_DIE_NOISE_RATIO, 2),
        "threshold": FIELD_DIE_SIGNAL_THRESHOLD,
        "target_pool": len(active),
        "recommended_ip": pick_row["ip"] if pick_row else None,
        "motto": (
            "Signal — 6% slice actionable. Hell may sever."
            if signal
            else "Noise — 94% floor. No friendly fire. Pass."
        ),
    }

    if signal and pick_row:
        sever = sever_target(
            pick_row["ip"],
            "FIELD_DIE",
            str(pick_row.get("severity") or "high"),
            f"field_die_signal:d20={roll}",
        )
        out["sever"] = sever
        out["action_ip"] = pick_row["ip"]
        out["action"] = "sever_wire" if sever.get("ok") else "refused"
    elif signal:
        out["action"] = "no_targets"
    else:
        out["action"] = "pass"

    _log_disable({
        "mode": "field_die",
        "roll": roll,
        "signal": signal,
        "action_ip": out.get("action_ip"),
        "action": out.get("action"),
    })
    return out


def laser_corridor(ip: str, vector: str = "LASER_CORRIDOR", severity: str = "critical") -> dict[str, Any]:
    """Undodgeable laser corridor — sever wire then forever kill. Heaven-protected only dodge."""
    ip = str(ip or "").strip()
    if not ip:
        return {"ok": False, "error": "missing_ip", "mode": "laser_corridor"}

    fg = _mod("friendly_guard", "friendly-guard.py")
    refuse, guard_reason = fg.refuse_kill(ip, monitor=None)
    if refuse:
        return {
            "ok": False,
            "ip": ip,
            "mode": "laser_corridor",
            "undodgeable": False,
            "friendly_refused": True,
            "reason": guard_reason,
            "motto": "Heaven dodged the grid — laser passes.",
        }

    sever = sever_target(ip, vector, severity, "laser_corridor:grid_sweep")
    kit = _mod("field_attack_kit", "field-attack-kit.py")
    kill = kit.kill_target(
        ip,
        vector,
        severity,
        "laser_corridor:undodgeable_slice",
        extra={"toolkit": "laser_corridor", "undodgeable": True},
    )

    out = {
        "ok": bool(sever.get("ok") or kill.get("ok") or kill.get("killed")),
        "ip": ip,
        "mode": "laser_corridor",
        "undodgeable": True,
        "vector": vector,
        "severity": severity,
        "grid_phases": ["horizontal", "vertical", "diagonal"],
        "sever": sever,
        "kill": kill,
        "killed": bool(kill.get("killed") or kill.get("ok")),
        "motto": "Undodgeable laser corridor — wire sliced. Hell goes to Hell. lulz.",
    }
    _log_disable({"mode": "laser_corridor", "ip": ip, "killed": out["killed"]})
    return out


def execute_disablement(body: dict[str, Any]) -> dict[str, Any]:
    """Unified Hell Kit disablement executor."""
    mode = str(body.get("mode") or body.get("profile") or "").strip().lower()
    if mode in ("sever", "sever_wire"):
        return sever_target(
            str(body.get("ip") or ""),
            str(body.get("vector") or "HELL_SEVER"),
            str(body.get("severity") or "high"),
            str(body.get("reason") or "hell_kit_sever"),
        )
    if mode in ("regional", "regional_disable"):
        return regional_disable(
            str(body.get("region") or body.get("value") or ""),
            field=str(body.get("field") or "region"),
            max_ips=int(body.get("max_ips") or REGIONAL_MAX_IPS),
            mode=str(body.get("disable_mode") or body.get("action") or "forever"),
        )
    if mode in ("human", "human_threat"):
        return human_threat_disable(max_ips=int(body.get("max_ips") or HUMAN_THREAT_MAX_IPS))
    if mode in ("rip", "hell_rip"):
        return hell_rip()
    if mode in ("die", "field_die"):
        return field_die_roll(str(body.get("ip") or "") or None)
    if mode in ("laser", "laser_corridor"):
        return laser_corridor(
            str(body.get("ip") or ""),
            str(body.get("vector") or "LASER_CORRIDOR"),
            str(body.get("severity") or "critical"),
        )
    if body.get("ip"):
        return sever_target(str(body["ip"]))
    return {
        "ok": False,
        "error": "unknown_mode",
        "modes": ["sever", "regional", "human_threat", "hell_rip", "field_die", "laser_corridor"],
    }


def panel_json() -> dict[str, Any]:
    seed = _seed()
    defenses = list_defenses()
    enabled_count = sum(1 for d in defenses if d.get("enabled"))
    hell_defenses = [d for d in defenses if d.get("hell_kit")]
    regions = list_regions()
    return {
        "schema": seed.get("schema") or "nexus-hell-kit-v2",
        "kit_name": seed.get("kit_name") or "Hell Kit",
        "motto": seed.get("motto") or "Hell goes to Hell — precision kit severs wire, region, and human threat.",
        "tagline": seed.get("tagline") or "",
        "hostility_priority": "hell_first",
        "attack_count": len(seed.get("attacks") or []),
        "defense_count": len(defenses),
        "defenses_enabled": enabled_count,
        "hell_kit_defenses": len(hell_defenses),
        "attacks": list_attacks(),
        "defenses": defenses,
        "disablement_profiles": list_disablement_profiles(),
        "regions": regions,
        "region_count": len(regions),
        "categories": sorted({str(a.get("category") or "other") for a in (seed.get("attacks") or [])}),
        "updated": _now(),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "regions":
        print(json.dumps({"regions": list_regions(), "updated": _now()}, ensure_ascii=False))
        return 0
    if cmd == "get" and len(sys.argv) >= 3:
        row = get_attack(sys.argv[2])
        print(json.dumps(row or {"error": "not_found"}, ensure_ascii=False))
        return 0 if row else 1
    if cmd == "toggle" and len(sys.argv) >= 3:
        enabled = None
        if len(sys.argv) >= 4:
            enabled = sys.argv[3].lower() in ("1", "true", "on", "yes")
        print(json.dumps(toggle_defense(sys.argv[2], enabled), ensure_ascii=False))
        return 0
    if cmd == "note" and len(sys.argv) >= 4:
        print(json.dumps(add_study_note(sys.argv[2], sys.argv[3]), ensure_ascii=False))
        return 0
    if cmd == "sever" and len(sys.argv) >= 3:
        print(json.dumps(sever_target(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd == "regional" and len(sys.argv) >= 3:
        field = sys.argv[3] if len(sys.argv) > 3 else "region"
        print(json.dumps(regional_disable(sys.argv[2], field=field), ensure_ascii=False))
        return 0
    if cmd == "human-threat":
        print(json.dumps(human_threat_disable(), ensure_ascii=False))
        return 0
    if cmd == "hell-rip":
        print(json.dumps(hell_rip(), ensure_ascii=False))
        return 0
    if cmd == "field-die":
        target = sys.argv[2].strip() if len(sys.argv) >= 3 else None
        print(json.dumps(field_die_roll(target), ensure_ascii=False))
        return 0
    if cmd == "laser-corridor" and len(sys.argv) >= 3:
        print(json.dumps(laser_corridor(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd == "disable" and len(sys.argv) >= 2:
        body = json.loads(sys.argv[2] if sys.argv[2] != "-" else sys.stdin.read())
        print(json.dumps(execute_disablement(body), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: field-toolkit-db.py [json|regions|get ID|toggle ID|sever IP|regional VAL [field]|human-threat|hell-rip|field-die [IP]|laser-corridor IP|disable JSON]",
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())