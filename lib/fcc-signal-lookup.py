#!/usr/bin/env pythong
"""FCC signal lookup — identify every signal by permitted spectrum; tag threats."""
from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
REGISTRY = INSTALL / "data" / "fcc-signal-registry.json"
PERMITTED = INSTALL / "data" / "fcc-permitted-frequencies.json"

_THREAT_INDEX: dict[str, dict[str, Any]] | None = None
_REGISTRY: dict[str, Any] | None = None


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _registry() -> dict[str, Any]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _load_json(REGISTRY, {"threat_tags": {}, "audio": {}, "wired": {}})
    return _REGISTRY


def _rf_mod() -> Any:
    spec = importlib.util.spec_from_file_location("field_rf", INSTALL / "lib" / "field-rf-sentinel.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _threat_tag_meta(tag_id: str) -> dict[str, Any]:
    reg = _registry()
    tags = reg.get("threat_tags") or {}
    if tag_id in tags:
        return {"threat_tag": tag_id, **tags[tag_id]}
    return {
        "threat_tag": tag_id or "none",
        "label": "FCC permitted" if not tag_id else tag_id.replace("_", " ").upper(),
        "level": "none" if not tag_id else "critical",
        "color": "#3dd68c" if not tag_id else "#ff5c7a",
    }


def _wifi_fcc_band(freq_mhz: Any, channel: Any) -> dict[str, Any]:
    rf = _rf_mod()
    ok, reason = rf._is_permitted_frequency(freq_mhz, channel)
    bands = rf._permitted_bands().get("bands") or []
    label = reason
    band_id = reason
    rule = "47 CFR Part 15"
    for band in bands:
        if str(band.get("id")) == reason:
            label = str(band.get("label") or reason)
            band_id = str(band.get("id"))
            rule = "47 CFR Part 15 · " + str(band.get("notes") or "UNII/ISM")
            break
    if ok:
        return {
            "fcc_id": f"FCC:{band_id}",
            "fcc_label": label,
            "fcc_rule": rule,
            "fcc_band_id": band_id,
            "permitted": True,
            "authority": "FCC Part 15",
            "service": label,
        }
    return {
        "fcc_id": f"FCC:UNPERMITTED:{reason}",
        "fcc_label": f"Unpermitted · {reason}",
        "fcc_rule": "47 CFR Part 15 — OUT OF BAND",
        "fcc_band_id": reason,
        "permitted": False,
        "authority": "FCC Part 15",
        "service": "Unlicensed violation",
    }


def _master_record(row: dict[str, Any], *, source: str = "lookup") -> None:
    try:
        spec = importlib.util.spec_from_file_location(
            "fcc_master_record", INSTALL / "lib" / "fcc-master-record.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.record_lookup(row, source=source)
    except Exception:
        pass


def lookup_signal(
    *,
    kind: str = "wifi",
    freq_mhz: Any = None,
    channel: Any = None,
    band: str = "",
    ssid: str = "",
    bssid: str = "",
    security: str = "",
    open_ap: bool = False,
    rf_threat_kind: str = "",
    hostile_intent: bool = False,
    permission: str = "",
    label: str = "",
    ip: str = "",
) -> dict[str, Any]:
    """Return FCC identification + threat tag for any signal."""
    reg = _registry()
    base: dict[str, Any] = {
        "kind": kind,
        "label": label or ssid or bssid or ip or kind,
        "fcc_lookup": True,
    }

    if kind in ("wifi", "rf"):
        fcc = _wifi_fcc_band(freq_mhz, channel)
        base.update(fcc)
        threat_kind = rf_threat_kind or ""
        if not fcc.get("permitted"):
            threat_kind = threat_kind or "unpermitted_spectrum"
        elif open_ap and security in ("", "open", "--", "wep"):
            threat_kind = threat_kind or "rogue_open"
        meta = _threat_tag_meta(threat_kind if threat_kind else "none")
        base.update(meta)
        base["identified_by"] = "fcc_frequency_lookup"
        _master_record(base, source="fcc_lookup")
        return base

    if kind == "audio":
        audio = reg.get("audio") or {}
        base.update({
            "fcc_id": audio.get("id", "fcc_audio_part15"),
            "fcc_label": audio.get("label", "Audio · Part 15"),
            "fcc_rule": audio.get("rule", "47 CFR §15.101"),
            "permitted": not hostile_intent,
            "authority": "FCC Part 15",
            "service": audio.get("service", "Audio incidental"),
        })
        tag = "audio_hostile" if hostile_intent else "none"
        base.update(_threat_tag_meta(tag))
        base["identified_by"] = "fcc_audio_registry"
        _master_record(base, source="fcc_lookup")
        return base

    if kind in ("lan", "arp", "wired"):
        wired = reg.get("wired") or {}
        base.update({
            "fcc_id": wired.get("id", "fcc_wired_lan"),
            "fcc_label": wired.get("label", "Wired LAN"),
            "fcc_rule": wired.get("rule", "47 CFR §15.103"),
            "permitted": permission != "unauthorized",
            "authority": "FCC Part 15",
            "service": wired.get("service", "Wired exempt"),
        })
        tag = "airspace_unauthorized" if permission == "unauthorized" else "none"
        base.update(_threat_tag_meta(tag))
        base["identified_by"] = "fcc_wired_registry"
        _master_record(base, source="fcc_lookup")
        return base

    if kind == "laser":
        laser = reg.get("laser") or {}
        base.update({
            "fcc_id": laser.get("id", "fcc_laser_part15"),
            "fcc_label": laser.get("label", "Laser / optical"),
            "fcc_rule": laser.get("rule", "47 CFR §15.101"),
            "permitted": True,
            "authority": "FCC Part 15",
            "service": laser.get("service", "Optical corridor"),
        })
        base.update(_threat_tag_meta("none"))
        base["identified_by"] = "fcc_laser_registry"
        _master_record(base, source="fcc_lookup")
        return base

    if kind == "ble":
        ble = reg.get("ble") or {}
        base.update({
            "fcc_id": ble.get("id", "fcc_ble_part15"),
            "fcc_label": ble.get("label", "Bluetooth LE"),
            "fcc_rule": ble.get("rule", "47 CFR Part 15"),
            "permitted": True,
            "authority": "FCC Part 15",
            "service": ble.get("service", "BLE"),
            "freq_mhz": ble.get("frequency_mhz"),
        })
        base.update(_threat_tag_meta("none"))
        base["identified_by"] = "fcc_ble_registry"
        _master_record(base, source="fcc_lookup")
        return base

    if kind in ("broadcast", "radio", "am", "sw", "lw", "fm"):
        pirate = permission == "unlicensed" or hostile_intent
        if kind == "fm" and not pirate:
            entry = reg.get("broadcast_fm") or reg.get("broadcast") or {}
        else:
            entry = reg.get("broadcast_pirate" if pirate else "broadcast") or {}
        base.update({
            "fcc_id": entry.get("id", "fcc_broadcast_part73"),
            "fcc_label": entry.get("label", "Broadcast"),
            "fcc_rule": entry.get("rule", "47 CFR Part 73"),
            "permitted": not pirate,
            "authority": "FCC Part 73",
            "service": entry.get("service", "Broadcast"),
            "freq_mhz": freq_mhz,
            "band": band or kind,
        })
        tag = "unpermitted_spectrum" if pirate else "none"
        base.update(_threat_tag_meta(tag))
        base["identified_by"] = "fcc_broadcast_registry"
        _master_record(base, source="fcc_lookup")
        return base

    base.update({
        "fcc_id": "FCC:UNKNOWN",
        "fcc_label": "Unknown signal class",
        "fcc_rule": "47 CFR Part 15",
        "permitted": False,
        "authority": "FCC",
        "service": "Unclassified",
    })
    base.update(_threat_tag_meta("watch"))
    base["identified_by"] = "fcc_fallback"
    _master_record(base, source="fcc_lookup")
    return base


def annotate_wifi_ap(ap: dict[str, Any], threat: dict[str, Any] | None = None) -> dict[str, Any]:
    t = threat or {}
    fcc = lookup_signal(
        kind="wifi",
        freq_mhz=ap.get("freq_mhz"),
        channel=ap.get("channel"),
        band=str(ap.get("band") or ""),
        ssid=str(ap.get("ssid") or ""),
        bssid=str(ap.get("bssid") or ""),
        security=str(ap.get("security") or ""),
        open_ap=bool(ap.get("open")),
        rf_threat_kind=str(t.get("kind") or ""),
        label=str(ap.get("ssid") or ap.get("bssid") or "wifi"),
    )
    return {**ap, "fcc": fcc}


def build_threat_index(rf_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for t in (rf_doc.get("threats") or []) + (rf_doc.get("recent_threats") or []):
        b = re.sub(r"[^0-9a-f]", "", str(t.get("bssid") or "").lower())[:12]
        if b:
            idx[b] = t
        ip = str(t.get("ip") or "").strip()
        if ip:
            idx[f"ip:{ip}"] = t
    return idx


def identify_all(
    *,
    rf_doc: dict[str, Any] | None = None,
    audio_doc: dict[str, Any] | None = None,
    home_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rf = rf_doc or {}
    audio = audio_doc or {}
    home = home_doc or {}
    threat_idx = build_threat_index(rf)
    identified: list[dict[str, Any]] = []

    for ap in (rf.get("scan_material") or [])[:64]:
        bnorm = re.sub(r"[^0-9a-f]", "", str(ap.get("bssid") or "").lower())[:12]
        threat = threat_idx.get(bnorm)
        row = annotate_wifi_ap(ap, threat)
        identified.append({
            "signal_id": f"wifi:{bnorm or ap.get('bssid')}",
            **row.get("fcc", {}),
            "ssid": ap.get("ssid"),
            "bssid": ap.get("bssid"),
            "channel": ap.get("channel"),
            "freq_mhz": ap.get("freq_mhz"),
            "band": ap.get("band"),
            "signal": ap.get("signal_dbm"),
        })

    for src in list((audio.get("sources") or {}).values())[:24]:
        sid = str(src.get("source_id") or "audio")
        fcc = lookup_signal(
            kind="audio",
            label=str(src.get("label") or sid),
            hostile_intent=not src.get("acceptable", True),
        )
        identified.append({"signal_id": f"audio:{sid}", **fcc})

    for ent in (home.get("entities") or home.get("table") or [])[:32]:
        kind = str(ent.get("kind") or "lan")
        fcc = lookup_signal(
            kind=kind,
            label=str(ent.get("label") or ent.get("entity_id")),
            ip=str(ent.get("ip") or ""),
            permission=str(ent.get("permission") or ""),
        )
        identified.append({
            "signal_id": str(ent.get("entity_id") or f"{kind}:unknown"),
            **fcc,
            "ip": ent.get("ip"),
        })

    threats = [s for s in identified if (s.get("level") or "none") not in ("none", "")]
    permitted = [s for s in identified if s.get("permitted")]
    return {
        "schema": "fcc-signal-identified/v1",
        "authority": _registry().get("authority"),
        "motto": _registry().get("motto"),
        "identified": identified,
        "threats": threats,
        "permitted": permitted,
        "stats": {
            "total": len(identified),
            "permitted": len(permitted),
            "threats": len(threats),
            "critical": sum(1 for s in threats if s.get("level") == "critical"),
        },
        "threat_tag_legend": _registry().get("threat_tags") or {},
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "registry").strip()
    if cmd == "registry":
        print(json.dumps(_registry(), ensure_ascii=False))
        return 0
    if cmd == "lookup" and len(sys.argv) >= 4:
        out = lookup_signal(
            kind=sys.argv[2],
            freq_mhz=sys.argv[3],
            channel=sys.argv[4] if len(sys.argv) > 4 else None,
        )
        print(json.dumps(out, ensure_ascii=False))
        return 0
    if cmd == "identify":
        print(json.dumps(identify_all(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: fcc-signal-lookup.py [registry|lookup KIND FREQ CHAN|identify]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())