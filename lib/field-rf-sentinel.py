#!/usr/bin/env pythong
"""Field RF Sentinel — FCC permitted-spectrum enforcement + passive threat watch.

Passive global WiFi field scan (receive-only beacon correlation). Whitelists all
FCC Part 15 permitted bands; anything outside is hostile and gets shoot-to-kill
lawful response on the wire (disconnect, firewall, autokill, hardware destroy).
Never jamming, bursts, or unsafe RF transmission.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
HISTORY = STATE / "field-rf-history.json"
SHIELD_CFG = STATE / "field-rf-shield.json"
THREATS_LOG = STATE / "field-rf-threats.jsonl"
PANEL_CACHE = STATE / "field-rf-panel.json"
FCC_POLICY = INSTALL / "data" / "fcc-wireless-policy.json"
FCC_PERMITTED = INSTALL / "data" / "fcc-permitted-frequencies.json"
FCC_POLLUTION = INSTALL / "data" / "fcc-global-pollution-policy.json"
RF_POLLUTION_LEDGER = STATE / "field-rf-pollution-ledger.json"
RF_OPERATIONS_LOG = STATE / "field-rf-operations.jsonl"
HOSTILE_TSV = STATE / "field-hostile.tsv"
HOST_ATTACKS = STATE / "host-attacks.json"
RF_DISABLED_FOREVER = STATE / "field-rf-disabled-forever.json"
OUI_VENDORS = INSTALL / "data" / "oui-vendors.tsv"
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
HOSTESS7_TEAM_FIELD = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage"))
TARGET_DOSSIER_FILE = "nexus-target-dossiers.jsonl"
HOSTILE_MEMORY_FILE = "nexus-hostile.jsonl"

UNHEALTHY_FOREVER_KINDS = frozenset({
    "unpermitted_spectrum",
    "connected_unpermitted",
    "evil_twin",
    "rogue_open",
    "hostile_oui",
    "connected_rogue",
    "correlated_hostile_ip",
    "enterprise_downgrade",
    "hot_attack_correlated",
    "blocked_peer_rf",
    "forever_disabled_nearby",
    "pollution_cluster",
})

RFKILL_TRIGGER_KINDS = frozenset({
    "connected_unpermitted",
    "connected_rogue",
    "hostile_oui",
    "evil_twin",
    "rogue_open",
    "unpermitted_spectrum",
    "correlated_hostile_ip",
    "hot_attack_correlated",
    "blocked_peer_rf",
    "forever_disabled_nearby",
    "pollution_cluster",
    "enterprise_downgrade",
})

SUSPICIOUS_SSID_RE = re.compile(
    r"(free[\s_-]?wifi|airport|xfinitywifi|attwifi|starbucks|"
    r"setup[\s_-]?router|linksys|netgear|dlink|tp[\s_-]?link|"
    r"evil|honeypot|pineapple|wifi[\s_-]?password|connect[\s_-]?here)",
    re.I,
)
ENTERPRISE_SSID_RE = re.compile(r"(corp|enterprise|vpn|office|company|secure)", re.I)
WEAK_SECURITY = frozenset({"", "--", "open", "wep"})

VECTOR_MAP = {
    "evil_twin": "WIFI_THREAT",
    "rogue_open": "WIFI_THREAT",
    "hostile_oui": "WIFI_THREAT",
    "enterprise_downgrade": "WIFI_THREAT",
    "hidden_surveillance": "WIFI_THREAT",
    "connected_rogue": "WIFI_THREAT",
    "connected_unpermitted": "WIFI_THREAT",
    "unpermitted_spectrum": "WIFI_THREAT",
    "correlated_hostile_ip": "WIFI_THREAT",
    "global_wireless_field": "FIELD_ANTENNA_ALERT",
    "global_pollution": "WIFI_THREAT",
    "hot_attack_correlated": "WIFI_THREAT",
    "blocked_peer_rf": "WIFI_THREAT",
    "forever_disabled_nearby": "WIFI_THREAT",
    "pollution_cluster": "WIFI_THREAT",
}

_PERMITTED_CACHE: dict[str, Any] | None = None
_OWN_ROUTER_MOD: Any | None = None


def _own_router_mod() -> Any | None:
    global _OWN_ROUTER_MOD
    if _OWN_ROUTER_MOD is not None:
        return _OWN_ROUTER_MOD
    py = INSTALL / "lib" / "znetwork-wireless-fcc.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("znetwork_wireless_fcc_rf", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _OWN_ROUTER_MOD = mod
    return mod


def _is_own_router(
    *,
    ip: str = "",
    mac: str = "",
    bssid: str = "",
    ssid: str = "",
) -> bool:
    mod = _own_router_mod()
    if mod and hasattr(mod, "is_own_router"):
        return bool(mod.is_own_router(ip=ip, mac=mac, bssid=bssid, ssid=ssid))
    return False


def _fix_own_router(issue: str, detail: str = "") -> dict[str, Any] | None:
    mod = _own_router_mod()
    if mod and hasattr(mod, "fix_own_router"):
        return mod.fix_own_router(issue=issue, detail=detail)
    return None


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


def _run(cmd: list[str], timeout: int = 8) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _norm_mac(mac: str) -> str:
    return re.sub(r"[^0-9a-f]", "", str(mac or "").lower())[:12]


def _mac_oui(mac: str) -> str:
    raw = _norm_mac(mac)
    if len(raw) < 6:
        return ""
    return f"{raw[0:2]}:{raw[2:4]}:{raw[4:6]}".upper()


def _permitted_bands() -> dict[str, Any]:
    global _PERMITTED_CACHE
    if _PERMITTED_CACHE is not None:
        return _PERMITTED_CACHE
    doc = _load_json(FCC_PERMITTED, {})
    if not doc.get("bands"):
        doc = {
            "bands": [
                {"id": "2.4ghz_wifi", "freq_mhz_min": 2401, "freq_mhz_max": 2473, "channels": list(range(1, 12))},
                {"id": "5ghz_unii1", "freq_mhz_min": 5150, "freq_mhz_max": 5250, "channels": [36, 40, 44, 48]},
                {"id": "5ghz_unii2a", "freq_mhz_min": 5250, "freq_mhz_max": 5350, "channels": [52, 56, 60, 64]},
                {"id": "5ghz_unii2c", "freq_mhz_min": 5470, "freq_mhz_max": 5725, "channels": list(range(100, 145, 4))},
                {"id": "5ghz_unii3", "freq_mhz_min": 5725, "freq_mhz_max": 5850, "channels": [149, 153, 157, 161, 165]},
                {"id": "6ghz_unii5", "freq_mhz_min": 5925, "freq_mhz_max": 6425, "channels": []},
                {"id": "6ghz_unii6", "freq_mhz_min": 6425, "freq_mhz_max": 6525, "channels": []},
                {"id": "6ghz_unii7", "freq_mhz_min": 6525, "freq_mhz_max": 6875, "channels": []},
                {"id": "6ghz_unii8", "freq_mhz_min": 6875, "freq_mhz_max": 7125, "channels": []},
            ],
        }
    _PERMITTED_CACHE = doc
    return doc


def _parse_freq_mhz(freq: Any) -> float | None:
    raw = str(freq or "").strip().lower().replace("mhz", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        m = re.search(r"(\d+(?:\.\d+)?)", raw)
        return float(m.group(1)) if m else None


def _parse_channel(channel: Any) -> int | None:
    raw = str(channel or "").strip()
    if not raw or raw in ("--", "-", "n/a"):
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def _is_permitted_frequency(freq_mhz: Any, channel: Any = None) -> tuple[bool, str]:
    """Return (permitted, band_id_or_reason)."""
    bands_doc = _permitted_bands()
    freq = _parse_freq_mhz(freq_mhz)
    ch = _parse_channel(channel)

    if freq is None and ch is None:
        return False, "unknown_frequency"

    for band in bands_doc.get("bands") or []:
        lo = float(band.get("freq_mhz_min") or 0)
        hi = float(band.get("freq_mhz_max") or 0)
        allowed_ch = band.get("channels") or []
        in_range = freq is not None and lo <= freq <= hi
        ch_ok = True
        if allowed_ch and ch is not None:
            ch_ok = ch in allowed_ch
        elif ch is not None and not allowed_ch:
            ch_ok = True
        if in_range and ch_ok:
            return True, str(band.get("id") or "permitted")
        if in_range and not ch_ok:
            return False, f"channel_{ch}_not_in_{band.get('id', 'band')}"

    if ch is not None:
        for band in bands_doc.get("bands") or []:
            allowed_ch = band.get("channels") or []
            if allowed_ch and ch in allowed_ch:
                return True, str(band.get("id") or "permitted")

    if freq is not None:
        return False, f"freq_{int(freq)}_mhz_unpermitted"
    return False, f"channel_{ch}_unpermitted"


def _fcc_policy() -> dict[str, Any]:
    doc = _load_json(FCC_POLICY, {})
    if doc.get("schema"):
        return doc
    return {
        "motto": "Passive watch globally. Lawful kick on the wire. No bursts. No jamming.",
        "allowed": ["Passive scan", "Disconnect our station", "Firewall block", "100% autokill"],
        "forbidden": ["Jamming", "Deauth floods", "Burst interference", "Auto rfkill on spikes"],
    }


def _rfkill_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    text = _run(["rfkill", "list"])
    if not text.strip():
        return rows
    block: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^(\d+):\s+(\S+):\s+(\S+)", line)
        if m:
            if block:
                rows.append(block)
            block = {"index": m.group(1), "name": m.group(2), "type": m.group(3)}
            continue
        for key in ("Soft blocked", "Hard blocked"):
            if key in line:
                block[key.lower().replace(" ", "_")] = line.split(":", 1)[-1].strip()
    if block:
        rows.append(block)
    return rows


def _rfkill_index_for_iface(iface: str | None) -> str | None:
    iface = str(iface or "").strip()
    sysfs = Path("/sys/class/rfkill")
    if sysfs.is_dir():
        for entry in sorted(sysfs.glob("rfkill*")):
            try:
                type_path = entry / "type"
                rtype = (type_path.read_text(encoding="utf-8", errors="replace").strip().lower()
                         if type_path.is_file() else "")
                if rtype != "wlan":
                    continue
                name = (entry / "name").read_text(encoding="utf-8", errors="replace").strip() if (entry / "name").is_file() else ""
                idx = (entry / "index").read_text(encoding="utf-8", errors="replace").strip() if (entry / "index").is_file() else ""
                if not idx:
                    continue
                if iface and (iface == name or iface in name or name in iface):
                    return idx
                if not iface:
                    return idx
            except OSError:
                continue
    for row in _rfkill_rows():
        if row.get("type") == "wlan":
            return row.get("index")
    return None


def _soft_rfkill_wifi(block: bool, wifi_dev: str | None, reason: str) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    idx = _rfkill_index_for_iface(wifi_dev)
    if idx:
        verb = "block" if block else "unblock"
        out = _run(["rfkill", verb, idx], timeout=8)
        actions.append({
            "action": f"rfkill_{verb}",
            "index": idx,
            "device": wifi_dev,
            "reason": reason,
            "ok": "error" not in out.lower(),
            "detail": out.strip()[:160],
        })
        return actions
    out = _run(["rfkill", "block" if block else "unblock", "wifi"], timeout=8)
    actions.append({
        "action": "rfkill_block_wifi" if block else "rfkill_unblock_wifi",
        "device": wifi_dev,
        "reason": reason,
        "ok": bool(out.strip()) and "error" not in out.lower(),
        "detail": out.strip()[:160],
    })
    return actions


def _rfkill_hostility_score(threats: list[dict[str, Any]], active: dict[str, Any] | None) -> int:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "hostility_priority", INSTALL / "lib" / "hostility-priority.py",
        )
        hp = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(hp)
        trigger = [t for t in threats if t.get("kind") in RFKILL_TRIGGER_KINDS]
        raw = hp.score_rf_threats(trigger, active)
        return max(0, raw // 8)
    except Exception:
        pass
    score = 0
    for t in threats:
        kind = str(t.get("kind") or "")
        sev = str(t.get("severity") or "")
        if kind not in RFKILL_TRIGGER_KINDS:
            continue
        if sev == "critical":
            score += 3
        elif sev == "high":
            score += 2
        elif sev == "medium":
            score += 1
    if active:
        active_bssid = _norm_mac(str(active.get("bssid") or ""))
        for t in threats:
            if t.get("severity") in ("high", "critical") and _norm_mac(str(t.get("bssid") or "")) == active_bssid:
                score += 4
                break
    return score


def _apply_auto_rfkill(
    threats: list[dict[str, Any]],
    wifi_dev: str | None,
    active: dict[str, Any] | None,
) -> dict[str, Any]:
    cfg = _shield_config()
    if not cfg.get("enabled") or not cfg.get("auto_rfkill"):
        return {"active": False, "action": "auto_rfkill_off", "rfkill_actions": []}

    score = _rfkill_hostility_score(threats, active)
    high_crit = [
        t for t in threats
        if t.get("severity") in ("high", "critical") and t.get("kind") in RFKILL_TRIGGER_KINDS
    ]
    must_block = score >= 3 or any(
        t.get("kind") in ("connected_unpermitted", "connected_rogue") for t in threats
    )
    safe = score == 0 and not any(
        t.get("kind") in ("connected_rogue", "connected_unpermitted") for t in threats
    )

    actions: list[dict[str, Any]] = []
    if must_block and wifi_dev:
        actions = _soft_rfkill_wifi(True, wifi_dev, f"hostility_score_{score}")
        for act in actions:
            _log_operation("auto_rfkill_block", {**act, "hostility_score": score, "threat_count": len(high_crit)})
    elif safe:
        rows = _rfkill_rows()
        blocked = [r for r in rows if r.get("type") == "wlan" and str(r.get("soft_blocked") or "").lower() == "yes"]
        if blocked:
            actions = _soft_rfkill_wifi(False, wifi_dev, "hostility_clear")
            for act in actions:
                _log_operation("auto_rfkill_unblock", act)

    return {
        "active": True,
        "action": "rfkill_blocked" if must_block else ("rfkill_clear" if safe else "rfkill_watch"),
        "hostility_score": score,
        "trigger_threats": len(high_crit),
        "rfkill_actions": actions,
        "auto_rfkill": True,
    }


def _nmcli_devices() -> list[dict[str, str]]:
    text = _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev", "status"])
    rows: list[dict[str, str]] = []
    for line in text.splitlines():
        parts = line.split(":")
        if len(parts) < 3:
            continue
        rows.append({
            "device": parts[0],
            "type": parts[1] if len(parts) > 1 else "",
            "state": parts[2] if len(parts) > 2 else "",
            "connection": parts[3] if len(parts) > 3 else "",
        })
    return rows


def _wifi_device_rows(devices: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    devices = devices or _nmcli_devices()
    return [r for r in devices if r.get("type") == "wifi" and r.get("device")]


def _iw_wifi_phy_map() -> dict[str, dict[str, Any]]:
    """Map wifi interface names to PHY metadata from iw dev (receive-only introspection)."""
    text = _run(["iw", "dev"], timeout=6)
    out: dict[str, dict[str, Any]] = {}
    if not text.strip():
        return out

    phy_id = ""
    phy_block: dict[str, Any] = {}
    iface = ""

    def _flush_iface() -> None:
        nonlocal iface, phy_block, phy_id
        if iface:
            out[iface] = {
                "phy": phy_id,
                "iface": iface,
                "addr": phy_block.get("addr", ""),
                "iface_type": phy_block.get("type", ""),
                "channel": phy_block.get("channel"),
                "freq_mhz": phy_block.get("freq_mhz"),
                "width_mhz": phy_block.get("width_mhz"),
                "band": phy_block.get("band", ""),
            }
        iface = ""
        phy_block = {}

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m_phy = re.match(r"^phy#(\d+)", line)
        if m_phy:
            _flush_iface()
            phy_id = m_phy.group(1)
            continue
        m_if = re.match(r"^Interface\s+(\S+)", line)
        if m_if:
            _flush_iface()
            iface = m_if.group(1)
            continue
        if not iface:
            continue
        if line.startswith("addr "):
            phy_block["addr"] = line.split(None, 1)[-1].strip()
        elif line.startswith("type "):
            phy_block["type"] = line.split(None, 1)[-1].strip()
        elif line.startswith("channel "):
            phy_block["channel_raw"] = line.split(None, 1)[-1].strip()
            ch_m = re.search(r"(\d+)\s*\((\d+(?:\.\d+)?)\s*MHz\)", line)
            if ch_m:
                phy_block["channel"] = ch_m.group(1)
                phy_block["freq_mhz"] = ch_m.group(2)
                phy_block["band"] = _band_label(ch_m.group(2))
            w_m = re.search(r"width:\s*(\d+)\s*MHz", line)
            if w_m:
                phy_block["width_mhz"] = int(w_m.group(1))
    _flush_iface()
    return out


def _antenna_field_descriptor(
    row: dict[str, str],
    phy: dict[str, Any] | None,
    scan: list[dict[str, Any]],
    active: dict[str, Any] | None,
) -> dict[str, Any]:
    dev = str(row.get("device") or "")
    bands = sorted({str(s.get("band") or "") for s in scan if s.get("band")} - {""})
    signals = [int(s.get("signal_dbm") or 0) for s in scan if s.get("signal_dbm") is not None]
    return {
        "device": dev,
        "state": row.get("state") or "",
        "connection": row.get("connection") or "",
        "phy": (phy or {}).get("phy") or "",
        "mac": (phy or {}).get("addr") or "",
        "iface_type": (phy or {}).get("iface_type") or "",
        "tuned_channel": (phy or {}).get("channel") or "",
        "tuned_freq_mhz": (phy or {}).get("freq_mhz") or "",
        "tuned_band": (phy or {}).get("band") or "",
        "width_mhz": (phy or {}).get("width_mhz"),
        "scanned": bool(scan),
        "scan_count": len(scan),
        "bands_seen": bands,
        "signal_max": max(signals) if signals else 0,
        "signal_avg": round(sum(signals) / len(signals), 1) if signals else 0,
        "active_connection": active,
        "connected": bool(active),
    }


def _merge_multi_antenna_scans(
    per_scans: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fuse passive scans from every antenna field — best signal wins, sightings accumulate."""
    merged: dict[str, dict[str, Any]] = {}
    raw_total = 0
    band_union: set[str] = set()

    for dev, rows in per_scans.items():
        raw_total += len(rows)
        for ap in rows:
            bnorm = _norm_mac(str(ap.get("bssid") or ""))
            if not bnorm:
                continue
            band = str(ap.get("band") or "")
            if band:
                band_union.add(band)
            sig = int(ap.get("signal_dbm") or 0)
            existing = merged.get(bnorm)
            if not existing:
                merged[bnorm] = {
                    **ap,
                    "antenna_sources": [dev],
                    "antenna_count": 1,
                    "antenna_signals": {dev: sig},
                    "sightings": 1,
                }
                continue
            existing["sightings"] = int(existing.get("sightings") or 0) + 1
            if dev not in existing["antenna_sources"]:
                existing["antenna_sources"].append(dev)
                existing["antenna_count"] = len(existing["antenna_sources"])
            existing["antenna_signals"][dev] = max(
                int(existing["antenna_signals"].get(dev) or 0), sig,
            )
            if sig > int(existing.get("signal_dbm") or 0):
                for key in ("ssid", "channel", "freq_mhz", "band", "security", "open", "bssid_oui"):
                    if ap.get(key) is not None:
                        existing[key] = ap[key]
                existing["signal_dbm"] = sig
                existing["source_antenna"] = dev

    unique = list(merged.values())
    multi_sight = sum(1 for ap in unique if int(ap.get("antenna_count") or 0) >= 2)
    return unique, {
        "raw_scan_total": raw_total,
        "unique_bssid_count": len(unique),
        "dedupe_removed": max(0, raw_total - len(unique)),
        "multi_antenna_sightings": multi_sight,
        "band_union": sorted(band_union),
        "antenna_field_count": len(per_scans),
    }


def _resolution_from_antenna_fields(
    antenna_fields: list[dict[str, Any]],
    merge_stats: dict[str, Any],
) -> dict[str, Any]:
    active_fields = [f for f in antenna_fields if f.get("scanned")]
    n_active = len(active_fields)
    n_total = len(antenna_fields)
    raw_total = int(merge_stats.get("raw_scan_total") or 0)
    unique = int(merge_stats.get("unique_bssid_count") or 0)
    multi = int(merge_stats.get("multi_antenna_sightings") or 0)
    bands = merge_stats.get("band_union") or []

    if n_active >= 3:
        tier = "high"
    elif n_active == 2:
        tier = "dual"
    elif n_active == 1:
        tier = "single"
    else:
        tier = "none"

    score = 0.0
    score += min(42.0, n_active * 14.0)
    score += min(24.0, len(bands) * 8.0)
    if raw_total > 0 and unique > 0:
        gain = (raw_total - unique) / raw_total
        score += min(18.0, gain * 18.0)
    if unique > 0:
        score += min(16.0, (multi / unique) * 16.0)

    return {
        "tier": tier,
        "score": round(min(100.0, score), 1),
        "antenna_field_count": n_total,
        "active_antenna_fields": n_active,
        "multi_antenna_sightings": multi,
        "dedupe_gain": max(0, raw_total - unique),
        "band_coverage": bands,
        "detail": (
            f"{n_active}/{n_total} antenna fields · tier {tier} · "
            f"score {round(min(100.0, score), 1)} · "
            f"{unique} unique BSSIDs ({multi} multi-antenna)"
        ),
    }


def _wifi_scan(dev: str) -> list[dict[str, Any]]:
    text = _run(["nmcli", "-t", "-f", "SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY", "dev", "wifi", "list", "ifname", dev])
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        parts = line.split(":")
        if len(parts) < 5:
            continue
        try:
            signal = int(parts[4] or "0")
        except ValueError:
            signal = 0
        sec = (parts[5] if len(parts) > 5 else "").strip().lower()
        bssid = parts[1] or ""
        rows.append({
            "ssid": parts[0] or "(hidden)",
            "bssid": bssid,
            "bssid_oui": _mac_oui(bssid),
            "channel": parts[2],
            "freq_mhz": parts[3],
            "band": _band_label(parts[3]),
            "signal_dbm": signal,
            "security": sec,
            "open": sec in WEAK_SECURITY,
            "source_antenna": dev,
        })
    return rows


def _band_label(freq: Any) -> str:
    f = str(freq or "")
    if f.startswith("2"):
        return "2.4GHz"
    if f.startswith("5"):
        return "5GHz"
    if f.startswith("6"):
        return "6GHz"
    return "unknown"


def _wifi_channel_center_mhz(channel: int, band_id: str = "") -> float | None:
    """Center frequency (MHz) for a WiFi channel number."""
    if 1 <= channel <= 14:
        return 2412.0 + 5.0 * (channel - 1)
    if 36 <= channel <= 196:
        return 5000.0 + 5.0 * channel
    bid = str(band_id or "").lower()
    if bid.startswith("6ghz") and 1 <= channel <= 233:
        return 5950.0 + 5.0 * channel
    return None


def _band_display_label(band_id: str, bands_doc: dict[str, Any]) -> str:
    for band in bands_doc.get("bands") or []:
        if str(band.get("id")) == band_id:
            return str(band.get("label") or band_id)
    return band_id


def _band_from_id(band_id: str) -> str:
    bid = str(band_id or "").lower()
    if bid.startswith("2.4"):
        return "2.4GHz"
    if bid.startswith("5ghz") or bid.startswith("5"):
        return "5GHz"
    if bid.startswith("6ghz") or bid.startswith("6"):
        return "6GHz"
    return "unknown"


def _registry_slots_for_band(band: dict[str, Any]) -> list[dict[str, Any]]:
    """Every permitted channel/frequency slot for one FCC band (strength filled later)."""
    band_id = str(band.get("id") or "")
    label = str(band.get("label") or band_id)
    lo = float(band.get("freq_mhz_min") or 0)
    hi = float(band.get("freq_mhz_max") or 0)
    channels = list(band.get("channels") or [])
    slots: list[dict[str, Any]] = []
    if channels:
        for ch in channels:
            try:
                ch_i = int(ch)
            except (TypeError, ValueError):
                continue
            freq = _wifi_channel_center_mhz(ch_i, band_id)
            if freq is None:
                freq = lo + (hi - lo) / 2 if hi > lo else lo
            slots.append({
                "band_id": band_id,
                "band_label": label,
                "band": _band_from_id(band_id),
                "channel": ch_i,
                "freq_mhz": round(freq, 1),
            })
        return slots
    step = 20.0
    f = lo
    idx = 0
    while f <= hi + 0.01:
        slots.append({
            "band_id": band_id,
            "band_label": label,
            "band": _band_from_id(band_id),
            "channel": None,
            "freq_mhz": round(f, 1),
            "slot_index": idx,
        })
        f += step
        idx += 1
    return slots


def _match_scan_to_slot(slot: dict[str, Any], scan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return scan hits that correlate to a registry slot."""
    ch = slot.get("channel")
    freq = float(slot.get("freq_mhz") or 0)
    band_id = str(slot.get("band_id") or "")
    band = str(slot.get("band") or "")
    hits: list[dict[str, Any]] = []
    for ap in scan:
        ap_ch = _parse_channel(ap.get("channel"))
        ap_freq = _parse_freq_mhz(ap.get("freq_mhz"))
        ap_band = str(ap.get("band") or "")
        if ch is not None and ap_ch is not None and ap_ch == ch:
            hits.append(ap)
            continue
        if ap_freq is not None and abs(ap_freq - freq) <= 12.0:
            if not band or ap_band == band or ap_band == "unknown":
                hits.append(ap)
            elif band_id and str(ap.get("permitted_band") or "") == band_id:
                hits.append(ap)
    return hits


def _build_frequency_registry(scan: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Enumerate every FCC-permitted channel slot with local signal strength (0 if silent)."""
    scan = list(scan or [])
    bands_doc = _permitted_bands()
    entries: list[dict[str, Any]] = []
    recognized = 0
    active = 0
    max_strength = 0

    for band in bands_doc.get("bands") or []:
        for slot in _registry_slots_for_band(band):
            hits = _match_scan_to_slot(slot, scan)
            strengths = [int(h.get("signal_dbm") or 0) for h in hits]
            strength = max(strengths) if strengths else 0
            avg = round(sum(strengths) / len(strengths), 1) if strengths else 0.0
            permitted, band_reason = _is_permitted_frequency(slot.get("freq_mhz"), slot.get("channel"))
            entry = {
                **slot,
                "strength": strength,
                "strength_avg": avg,
                "strength_pct": strength,
                "source_count": len(hits),
                "recognized": bool(hits),
                "permitted": permitted,
                "permitted_band": band_reason if permitted else "",
                "ssids": sorted({str(h.get("ssid") or "") for h in hits if h.get("ssid")})[:6],
                "bssids": [str(h.get("bssid") or "") for h in hits[:4]],
            }
            entries.append(entry)
            if hits:
                recognized += 1
                active += 1
                max_strength = max(max_strength, strength)

    by_band: dict[str, list[dict[str, Any]]] = {}
    for e in entries:
        by_band.setdefault(str(e.get("band") or "unknown"), []).append(e)

    return {
        "schema": "frequency-registry/v1",
        "updated": _now(),
        "total_slots": len(entries),
        "recognized_slots": recognized,
        "active_slots": active,
        "silent_slots": len(entries) - recognized,
        "max_strength": max_strength,
        "coverage_pct": round((recognized / len(entries)) * 100.0, 1) if entries else 0.0,
        "entries": entries,
        "by_band": {k: v for k, v in sorted(by_band.items())},
    }


def _active_wifi_connection(wifi_dev: str) -> dict[str, Any] | None:
    text = _run(["nmcli", "-t", "-f", "GENERAL.CONNECTION,GENERAL.STATE,802-11-wireless.ssid,802-11-wireless.bssid", "dev", "show", wifi_dev])
    if not text.strip():
        return None
    doc: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        doc[key.strip()] = val.strip()
    state = doc.get("GENERAL.STATE", "")
    if "connected" not in state.lower():
        return None
    bssid = doc.get("802-11-wireless.bssid", "")
    return {
        "device": wifi_dev,
        "connection": doc.get("GENERAL.CONNECTION", ""),
        "ssid": doc.get("802-11-wireless.ssid", ""),
        "bssid": bssid,
        "bssid_oui": _mac_oui(bssid),
        "state": state,
    }


def _dossier_storage_paths() -> list[Path]:
    return [
        HOSTESS7_ROOT / "cache" / "fieldstorage" / "brain" / "security" / TARGET_DOSSIER_FILE,
        HOSTESS7_TEAM_FIELD / "brain" / "security" / TARGET_DOSSIER_FILE,
        STATE / "field-storage" / TARGET_DOSSIER_FILE,
    ]


def _hostile_memory_paths() -> list[Path]:
    return [
        HOSTESS7_ROOT / "cache" / "fieldstorage" / "brain" / "security" / HOSTILE_MEMORY_FILE,
        HOSTESS7_TEAM_FIELD / "brain" / "security" / HOSTILE_MEMORY_FILE,
        STATE / "field-storage" / HOSTILE_MEMORY_FILE,
    ]


def _hostile_ips() -> set[str]:
    ips: set[str] = set()
    if not HOSTILE_TSV.is_file():
        return ips
    try:
        for line in HOSTILE_TSV.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 2 and parts[1]:
                ips.add(parts[1].strip())
    except OSError:
        pass
    return ips


def _hostile_macs() -> set[str]:
    macs: set[str] = set()
    for path in _dossier_storage_paths() + _hostile_memory_paths():
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                dos = row.get("dossier") if isinstance(row.get("dossier"), dict) else row
                for key in ("mac", "bssid"):
                    val = dos.get(key) or (dos.get("intel") or {}).get(key)
                    if val:
                        macs.add(_norm_mac(str(val)))
        except OSError:
            continue
    reg = _forever_registry()
    for entry in (reg.get("entries") or {}).values():
        if isinstance(entry, dict):
            bssid = entry.get("bssid") or entry.get("mac")
            if bssid:
                macs.add(_norm_mac(str(bssid)))
    return {m for m in macs if len(m) >= 6}


def _blocked_ips() -> set[str]:
    ips: set[str] = set()
    blocks = STATE / "firewall-blocks.tsv"
    if blocks.is_file():
        try:
            for line in blocks.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
                parts = line.split("\t")
                if len(parts) >= 2 and parts[1].strip():
                    ips.add(parts[1].strip())
        except OSError:
            pass
    ips.update(_hostile_ips())
    return ips


def _hot_attack_ips(*, min_heat: float = 0.5) -> set[str]:
    ips: set[str] = set()
    doc = _load_json(HOST_ATTACKS, {})
    for p in doc.get("points") or []:
        ip = str(p.get("ip") or "")
        if not ip:
            continue
        if float(p.get("heat") or 0) >= min_heat or p.get("strike_certain"):
            ips.add(ip)
    hd = _load_json(STATE / "human-dossier.json", {})
    for row in hd.get("ips") or []:
        if isinstance(row, dict):
            ip = str(row.get("ip") or "")
            if ip:
                ips.add(ip)
    return ips


def _forever_disabled_bssids() -> set[str]:
    out: set[str] = set()
    reg = _forever_registry()
    for key in (reg.get("entries") or {}):
        norm = _norm_mac(str(key))
        if len(norm) >= 6:
            out.add(norm)
    return out


def _suspicious_ouis() -> dict[str, str]:
    out: dict[str, str] = {}
    if not OUI_VENDORS.is_file():
        return out
    try:
        for line in OUI_VENDORS.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            prefix = parts[0].strip().upper()
            vendor = parts[1].strip()
            cat = parts[2].strip().lower() if len(parts) > 2 else ""
            if cat in ("virtualization",) or "pineapple" in vendor.lower() or "hack" in vendor.lower():
                out[prefix] = vendor
    except OSError:
        pass
    out.setdefault("00:C0:CA", "WiFi Pineapple / Hak5")
    return out


def _correlated_hostile_points() -> list[dict[str, Any]]:
    doc = _load_json(HOST_ATTACKS, {})
    hostile = _blocked_ips()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for p in doc.get("points") or []:
        ip = str(p.get("ip") or "")
        if not ip or ip in seen:
            continue
        if ip in hostile or p.get("strike_certain") or float(p.get("heat") or 0) >= 0.5:
            seen.add(ip)
            out.append(p)
    return out


def _pollution_policy() -> dict[str, Any]:
    doc = _load_json(FCC_POLLUTION, {})
    if doc.get("schema"):
        return doc
    return {
        "motto": "Near-infinite passive reach. Global pollution cleanup. Always safe on the wire.",
        "reach_model": {"mode": "passive_receive_only", "near_infinite": True},
    }


def _log_operation(action: str, detail: dict[str, Any]) -> None:
    row = {"ts": _now(), "action": action, **detail}
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with RF_OPERATIONS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _estimate_passive_reach_km(signal: Any, band: str = "") -> float:
    """Estimate passive correlation horizon from nmcli signal (0–100, higher = closer)."""
    try:
        s = int(signal or 0)
    except (TypeError, ValueError):
        s = 0
    s = max(0, min(100, s))
    if s >= 95:
        base_km = 0.05
    elif s >= 80:
        base_km = 0.3
    elif s >= 60:
        base_km = 1.2
    elif s >= 40:
        base_km = 5.0
    elif s >= 20:
        base_km = 15.0
    elif s >= 5:
        base_km = 50.0
    else:
        base_km = 500.0
    band_mult = 1.0
    if str(band).startswith("2"):
        band_mult = 1.4
    elif str(band).startswith("6"):
        band_mult = 0.7
    return round(base_km * band_mult, 2)


def _pollution_ledger() -> dict[str, Any]:
    doc = _load_json(RF_POLLUTION_LEDGER, {"pollution": {}, "stats": {}, "updated": ""})
    if not isinstance(doc.get("pollution"), dict):
        doc["pollution"] = {}
    stats = doc.setdefault("stats", {})
    stats.setdefault("total_pollution_seen", 0)
    stats.setdefault("total_cleaned_forever", 0)
    stats.setdefault("cycles", 0)
    stats.setdefault("max_reach_km_seen", 0.0)
    stats.setdefault("cumulative_horizon_km", 0.0)
    stats.setdefault("bands_polluted", {})
    return doc


def _save_pollution_ledger(doc: dict[str, Any]) -> None:
    doc["updated"] = _now()
    _save_json(RF_POLLUTION_LEDGER, doc)


def _recent_operations(limit: int = 50) -> list[dict[str, Any]]:
    if not RF_OPERATIONS_LOG.is_file():
        return []
    lines = deque(maxlen=limit)
    try:
        with RF_OPERATIONS_LOG.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    lines.append(line)
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _global_pollution_cleanup(
    scan: list[dict[str, Any]],
    threats: list[dict[str, Any]],
    kick_result: dict[str, Any],
) -> dict[str, Any]:
    cfg = _shield_config()
    if not cfg.get("global_pollution_cleanup", True):
        return {"active": False, "reason": "global_pollution_cleanup_off"}

    ledger = _pollution_ledger()
    pollution = ledger.setdefault("pollution", {})
    stats = ledger.setdefault("stats", {})
    stats["cycles"] = int(stats.get("cycles") or 0) + 1

    cleaned_this_cycle: list[dict[str, Any]] = []
    new_pollution = 0
    max_reach = float(stats.get("max_reach_km_seen") or 0)
    horizon_sum = 0.0
    horizon_n = 0

    pollution_threats = [
        t for t in threats
        if t.get("kind") in UNHEALTHY_FOREVER_KINDS
        or t.get("kind") == "hidden_surveillance"
        or (t.get("kind") == "unpermitted_spectrum")
    ]

    for ap in scan:
        if ap.get("permitted") is not False and not ap.get("disabled_forever"):
            continue
        bnorm = _norm_mac(str(ap.get("bssid") or ""))
        if not bnorm:
            continue
        reach_km = _estimate_passive_reach_km(ap.get("signal_dbm"), str(ap.get("band") or ""))
        max_reach = max(max_reach, reach_km)
        horizon_sum += reach_km
        horizon_n += 1
        band = str(ap.get("band") or "unknown")
        bands_polluted = stats.setdefault("bands_polluted", {})
        bands_polluted[band] = int(bands_polluted.get(band) or 0) + 1

        existing = pollution.get(bnorm)
        if not existing:
            new_pollution += 1
            stats["total_pollution_seen"] = int(stats.get("total_pollution_seen") or 0) + 1
            existing = {
                "first_seen": _now(),
                "sightings": 0,
                "cleaned": False,
            }
            pollution[bnorm] = existing
            _log_operation("pollution_discovered", {
                "bssid": ap.get("bssid"),
                "ssid": ap.get("ssid"),
                "band": band,
                "channel": ap.get("channel"),
                "freq_mhz": ap.get("freq_mhz"),
                "reach_km": reach_km,
                "signal": ap.get("signal_dbm"),
                "global": True,
            })

        existing["last_seen"] = _now()
        existing["sightings"] = int(existing.get("sightings") or 0) + 1
        existing["ssid"] = ap.get("ssid")
        existing["bssid"] = ap.get("bssid")
        existing["band"] = band
        existing["channel"] = ap.get("channel")
        existing["freq_mhz"] = ap.get("freq_mhz")
        existing["signal_dbm"] = ap.get("signal_dbm")
        existing["reach_km"] = reach_km
        existing["max_reach_km"] = max(float(existing.get("max_reach_km") or 0), reach_km)
        existing["kind"] = existing.get("kind") or "unpermitted_spectrum"
        existing["pollution"] = True

    forever_disabled_bssids = {
        _norm_mac(str(fd.get("bssid") or ""))
        for fd in (kick_result.get("forever_disabled") or [])
        if fd.get("bssid")
    }
    reg = _forever_registry()

    for t in pollution_threats:
        bnorm = _norm_mac(str(t.get("bssid") or ""))
        if not bnorm or bnorm not in pollution:
            continue
        if pollution[bnorm].get("cleaned"):
            cleaned_this_cycle.append({**pollution[bnorm], "clean_result": {"action": "already_cleaned"}})
            continue
        already = bnorm in (reg.get("entries") or {}) or bnorm in forever_disabled_bssids
        if already:
            pollution[bnorm]["cleaned"] = True
            pollution[bnorm]["cleaned_ts"] = _now()
            pollution[bnorm]["clean_action"] = "disabled_forever_registry"
            stats["total_cleaned_forever"] = int(stats.get("total_cleaned_forever") or 0) + 1
            cleaned_this_cycle.append({**pollution[bnorm], "clean_result": {"action": "already_disabled_forever"}})
            continue
        if not cfg.get("disable_unhealthy_forever", True):
            continue
        threat_row = {**t, "bssid": t.get("bssid") or pollution[bnorm].get("bssid")}
        result = _disable_unhealthy_forever(threat_row)
        if result:
            pollution[bnorm]["cleaned"] = True
            pollution[bnorm]["cleaned_ts"] = _now()
            pollution[bnorm]["clean_action"] = result.get("action")
            if result.get("action") != "already_disabled_forever":
                stats["total_cleaned_forever"] = int(stats.get("total_cleaned_forever") or 0) + 1
            cleaned_this_cycle.append({**pollution[bnorm], "clean_result": result})
            _log_operation("pollution_cleaned_forever", {
                "bssid": pollution[bnorm].get("bssid"),
                "ssid": pollution[bnorm].get("ssid"),
                "kind": t.get("kind"),
                "reach_km": pollution[bnorm].get("reach_km"),
                "forever": True,
                "detail": t.get("detail"),
            })

    for fd in kick_result.get("forever_disabled") or []:
        _log_operation("global_cleanup_kick", fd)

    stats["max_reach_km_seen"] = round(max_reach, 2)
    if horizon_n:
        cycle_horizon = horizon_sum / horizon_n
        prev = float(stats.get("cumulative_horizon_km") or 0)
        stats["cumulative_horizon_km"] = round(max(prev, cycle_horizon, max_reach), 2)

    _save_pollution_ledger(ledger)

    policy = _pollution_policy()
    reach = policy.get("reach_model") or {}
    summary = {
        "active": True,
        "motto": policy.get("motto"),
        "mode": reach.get("mode", "passive_receive_only"),
        "near_infinite_reach": reach.get("near_infinite", True),
        "safe": True,
        "fcc_passive_only": True,
        "cycle_pollution_new": new_pollution,
        "cycle_cleaned": len([c for c in cleaned_this_cycle if c.get("clean_result", {}).get("action") != "already_cleaned"]),
        "cleaned_this_cycle": cleaned_this_cycle[:40],
        "ledger_total": len(pollution),
        "ledger_cleaned": sum(1 for p in pollution.values() if p.get("cleaned")),
        "ledger_active_pollution": sum(1 for p in pollution.values() if not p.get("cleaned")),
        "stats": stats,
        "max_reach_km_this_cycle": round(max_reach, 2),
        "effective_horizon_km": stats.get("cumulative_horizon_km"),
        "detail": (
            f"Global pollution cleanup — {stats.get('total_pollution_seen', 0)} seen lifetime, "
            f"{stats.get('total_cleaned_forever', 0)} cleaned forever, "
            f"horizon {stats.get('cumulative_horizon_km', 0)} km passive reach"
        ),
    }
    _log_operation("global_pollution_cycle", {
        "new": new_pollution,
        "cleaned": summary["cycle_cleaned"],
        "ledger_total": summary["ledger_total"],
        "horizon_km": summary["effective_horizon_km"],
    })
    return summary


def _shield_config() -> dict[str, Any]:
    doc = _load_json(SHIELD_CFG, {})
    doc.setdefault("enabled", True)
    doc.setdefault("lawful_kick", True)
    doc.setdefault("shoot_to_kill", True)
    doc.setdefault("disable_unhealthy_forever", True)
    doc.setdefault("global_pollution_cleanup", True)
    doc.setdefault("permitted_spectrum_only", True)
    doc.setdefault("fcc_passive_only", True)
    doc.setdefault("global_watch", True)
    if not doc.get("rfkill_advanced_v2"):
        doc["auto_rfkill"] = True
        doc["rfkill_advanced_v2"] = True
        doc["updated"] = _now()
        _save_json(SHIELD_CFG, doc)
    else:
        doc.setdefault("auto_rfkill", True)
    return doc


def _forever_registry() -> dict[str, Any]:
    doc = _load_json(RF_DISABLED_FOREVER, {"entries": {}, "ips": {}, "updated": ""})
    if not isinstance(doc.get("entries"), dict):
        doc["entries"] = {}
    if not isinstance(doc.get("ips"), dict):
        doc["ips"] = {}
    return doc


def _save_forever_registry(doc: dict[str, Any]) -> None:
    doc["updated"] = _now()
    _save_json(RF_DISABLED_FOREVER, doc)


def _is_ipv4(ip: str) -> bool:
    return bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", str(ip or "").strip()))


def _is_disabled_forever(*, bssid: str = "", ip: str = "") -> bool:
    reg = _forever_registry()
    if ip and ip in (reg.get("ips") or {}):
        return True
    bnorm = _norm_mac(bssid)
    if bnorm and bnorm in (reg.get("entries") or {}):
        return True
    return False


def _append_storage_jsonl(paths: list[Path], entry: dict[str, Any], dedupe_key: str) -> None:
    payload = json.dumps(entry, ensure_ascii=False) + "\n"
    needle = f'"{dedupe_key}"'
    for path in paths:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")
                if needle in text and str(entry.get(dedupe_key, "")) in text:
                    continue
            with path.open("a", encoding="utf-8") as fh:
                fh.write(payload)
        except OSError:
            continue


def _append_hostile_tsv(ip: str, vector: str, severity: str, reason: str) -> None:
    if not _is_ipv4(ip):
        return
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        if not HOSTILE_TSV.is_file():
            HOSTILE_TSV.write_text("ts\tip\tvector\tseverity\treason\tsource\n", encoding="utf-8")
        text = HOSTILE_TSV.read_text(encoding="utf-8", errors="replace")
        if f"\t{ip}\t" in text:
            return
        with HOSTILE_TSV.open("a", encoding="utf-8") as fh:
            fh.write(f"{_now()}\t{ip}\t{vector}\t{severity}\t{reason}\trf_unhealthy_forever\n")
    except OSError:
        pass


def _archive_rf_dossier_forever(threat: dict[str, Any], ip: str = "") -> None:
    bssid = str(threat.get("bssid") or "")
    dossier = {
        "action": "RF_UNHEALTHY_DISABLED_FOREVER",
        "disabled_permanent": True,
        "forever": True,
        "vector": VECTOR_MAP.get(str(threat.get("kind") or ""), "WIFI_THREAT"),
        "kind": threat.get("kind"),
        "ssid": threat.get("ssid"),
        "bssid": bssid,
        "channel": threat.get("channel"),
        "freq_mhz": threat.get("freq_mhz"),
        "detail": threat.get("detail"),
        "ip": ip or threat.get("ip") or "",
        "intel": {"mac": bssid, "bssid": bssid},
        "permanent": True,
        "hardware_destroy": bool(threat.get("strike_certain") or threat.get("kind") in (
            "unpermitted_spectrum", "connected_unpermitted",
        )),
    }
    entry = {
        "kind": "nexus_target_dossier",
        "ts": _now(),
        "ip": ip or f"rf:{_norm_mac(bssid) or 'unknown'}",
        "vector": dossier["vector"],
        "severity": threat.get("severity") or "critical",
        "reason": "rf_unhealthy_disabled_forever",
        "source": "field-rf-sentinel",
        "permanent": True,
        "dossier": dossier,
    }
    _append_storage_jsonl(_dossier_storage_paths(), entry, "ip")
    if ip:
        meta_entry = {
            "kind": "nexus_hostile",
            "ts": _now(),
            "ip": ip,
            "vector": dossier["vector"],
            "severity": threat.get("severity") or "critical",
            "reason": "rf_unhealthy_disabled_forever",
            "source": "field-rf-sentinel",
            "permanent": True,
            "meta": {"bssid": bssid, "kind": threat.get("kind"), "rf_forever": True},
        }
        _append_storage_jsonl(_hostile_memory_paths(), meta_entry, "ip")


def _forever_disable_ip(ip: str, threat: dict[str, Any]) -> dict[str, Any]:
    script = INSTALL / "lib" / "field-attack-kit.py"
    if not script.is_file() or not _is_ipv4(ip):
        return {"ok": False, "ip": ip}
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
    env["NEXUS_STATE_DIR"] = str(STATE)
    meta = json.dumps({
        "force": True,
        "strike_mode": "destroy",
        "bssid": threat.get("bssid"),
        "rf_kind": threat.get("kind"),
    })
    proc = subprocess.run(
        [
            os.environ.get("PYTHON", "pythong"), str(script),
            "forever-disable", ip, "WIFI_THREAT", "critical", "rf_unhealthy_forever", meta,
        ],
        capture_output=True,
        text=True,
        timeout=90,
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": proc.returncode == 0, "ip": ip}


def _disable_unhealthy_forever(threat: dict[str, Any]) -> dict[str, Any] | None:
    kind = str(threat.get("kind") or "")
    if kind not in UNHEALTHY_FOREVER_KINDS:
        return None
    if kind == "hostile_oui" and threat.get("severity") != "critical":
        return None
    if kind == "correlated_hostile_ip" and not threat.get("strike_certain"):
        return None

    bssid = str(threat.get("bssid") or "")
    ip = str(threat.get("ip") or "")
    if _is_own_router(ip=ip, bssid=bssid, ssid=str(threat.get("ssid") or "")):
        _fix_own_router("forever_disable_own_router", f"Blocked forever-disable on home router ({kind})")
        return {"action": "own_router_fix_not_forever", "bssid": bssid, "ip": ip or None}
    bnorm = _norm_mac(bssid)
    reg = _forever_registry()
    entries = reg.setdefault("entries", {})
    ips = reg.setdefault("ips", {})

    if bnorm and bnorm in entries and (not ip or ip in ips):
        return {"action": "already_disabled_forever", "bssid": bssid, "ip": ip or None}

    record = {
        "ts": _now(),
        "kind": kind,
        "severity": threat.get("severity") or "critical",
        "ssid": threat.get("ssid"),
        "bssid": bssid,
        "channel": threat.get("channel"),
        "freq_mhz": threat.get("freq_mhz"),
        "detail": threat.get("detail"),
        "disabled_permanent": True,
        "forever": True,
        "shoot_to_kill": True,
    }
    if bnorm:
        entries[bnorm] = record
    kill_result: dict[str, Any] = {}
    if ip and _is_ipv4(ip):
        if ip not in ips:
            kill_result = _forever_disable_ip(ip, threat)
            _append_hostile_tsv(ip, "WIFI_THREAT", "critical", f"rf_unhealthy:{kind}")
            _firewall_block_ip(ip, "rf_unhealthy_disabled_forever")
            ips[ip] = {**record, "ip": ip, "kill": kill_result}
    _archive_rf_dossier_forever(threat, ip=ip)
    _save_forever_registry(reg)
    return {
        "action": "disabled_unhealthy_forever",
        "bssid": bssid or None,
        "ip": ip or None,
        "kind": kind,
        "forever": True,
        "kill": kill_result or None,
    }


def _forever_rf_enforce(
    wifi_dev: str | None,
    active: dict[str, Any] | None,
    scan: list[dict[str, Any]],
) -> dict[str, Any]:
    cfg = _shield_config()
    if not cfg.get("enabled") or not cfg.get("disable_unhealthy_forever", True):
        return {"enforced": False, "reason": "forever_disable_off"}

    reg = _forever_registry()
    entries = reg.get("entries") or {}
    ips = reg.get("ips") or {}
    actions: list[dict[str, Any]] = []

    if active and wifi_dev:
        active_bssid = _norm_mac(str(active.get("bssid") or ""))
        if active_bssid and active_bssid in entries:
            if _disconnect_wifi(wifi_dev, "rf_unhealthy_disabled_forever"):
                actions.append({
                    "action": "disconnect_forever_disabled_bssid",
                    "bssid": active.get("bssid"),
                    "ssid": active.get("ssid"),
                })

    for ip, meta in list(ips.items())[:48]:
        if not _is_ipv4(ip):
            continue
        if _firewall_block_ip(ip, "rf_unhealthy_forever_reenforce"):
            actions.append({"action": "firewall_reenforce_forever", "ip": ip, "kind": meta.get("kind")})

    for ap in scan[:80]:
        bnorm = _norm_mac(str(ap.get("bssid") or ""))
        if bnorm and bnorm in entries:
            ap["disabled_forever"] = True
            ap["hostile_forever"] = True

    return {
        "enforced": True,
        "forever_entries": len(entries),
        "forever_ips": len(ips),
        "actions": actions,
        "action_count": len(actions),
    }


def _set_shield(
    enabled: bool | None = None,
    auto_rfkill: bool | None = None,
    lawful_kick: bool | None = None,
    shoot_to_kill: bool | None = None,
) -> dict[str, Any]:
    doc = _shield_config()
    if enabled is not None:
        doc["enabled"] = bool(enabled)
    if auto_rfkill is not None:
        doc["auto_rfkill"] = bool(auto_rfkill)
    if lawful_kick is not None:
        doc["lawful_kick"] = bool(lawful_kick)
    if shoot_to_kill is not None:
        doc["shoot_to_kill"] = bool(shoot_to_kill)
    doc["fcc_passive_only"] = True
    doc["permitted_spectrum_only"] = True
    doc["updated"] = _now()
    _save_json(SHIELD_CFG, doc)
    return doc


def _append_threat(row: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with THREATS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    vector = VECTOR_MAP.get(str(row.get("kind") or ""), "WIFI_THREAT")
    script = INSTALL / "lib" / "threat-vectors.sh"
    if script.is_file():
        detail = (
            f"kind={row.get('kind')} bssid={row.get('bssid','')} "
            f"ssid={row.get('ssid','')} detail={row.get('detail','')}"
        )
        env = os.environ.copy()
        env["NEXUS_STATE_DIR"] = str(STATE)
        env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
        subprocess.run(
            [
                "bash", "-c",
                f'source "{script}" && nexus_threat_record "{vector}" "{row.get("severity","medium")}" "{detail}"',
            ],
            capture_output=True,
            timeout=10,
            env=env,
        )


def _detect_wireless_threats(
    scan: list[dict[str, Any]],
    active: dict[str, Any] | None,
    hist: dict[str, Any],
) -> list[dict[str, Any]]:
    threats: list[dict[str, Any]] = []
    ts = _now()
    hostile_macs = _hostile_macs()
    suspicious_ouis = _suspicious_ouis()
    trusted_ssids = set(hist.get("trusted_ssids") or [])

    cfg = _shield_config()
    permitted_only = cfg.get("permitted_spectrum_only", True)
    shoot = cfg.get("shoot_to_kill", True)
    unpermitted_aps: list[dict[str, Any]] = []

    if scan:
        permitted_n = 0
        reach_vals: list[float] = []
        for ap in scan:
            ok, band_id = _is_permitted_frequency(ap.get("freq_mhz"), ap.get("channel"))
            ap["permitted"] = ok
            ap["permitted_band"] = band_id if ok else ""
            ap["passive_reach_km"] = _estimate_passive_reach_km(ap.get("signal_dbm"), str(ap.get("band") or ""))
            reach_vals.append(float(ap["passive_reach_km"]))
            if ok:
                permitted_n += 1
            elif permitted_only:
                if _is_own_router(bssid=str(ap.get("bssid") or ""), ssid=str(ap.get("ssid") or "")):
                    ap["own_router"] = True
                    permitted_n += 1
                    continue
                unpermitted_aps.append(ap)
                threats.append({
                    "ts": ts,
                    "kind": "unpermitted_spectrum",
                    "severity": "critical",
                    "ssid": ap.get("ssid"),
                    "bssid": ap.get("bssid"),
                    "channel": ap.get("channel"),
                    "freq_mhz": ap.get("freq_mhz"),
                    "detail": (
                        f"UNPERMITTED — ch{ap.get('channel')} {ap.get('freq_mhz')} MHz "
                        f"({band_id}) · shoot-to-kill eligible"
                    ),
                    "shoot_to_kill": shoot,
                    "global": True,
                })
        max_reach = max(reach_vals) if reach_vals else 0.0
        ledger = _pollution_ledger()
        lstats = ledger.get("stats") or {}
        res = hist.get("last_resolution") or {}
        ant_n = int(res.get("active_antenna_fields") or hist.get("last_antenna_field_count") or 1)
        tier = res.get("tier") or ("single" if ant_n <= 1 else "multi")
        threats.append({
            "ts": ts,
            "kind": "global_wireless_field",
            "severity": "info",
            "detail": (
                f"Passive global field — {len(scan)} APs "
                f"({permitted_n} permitted / {len(unpermitted_aps)} pollution) · "
                f"{ant_n} antenna field(s) · resolution {tier} "
                f"({res.get('score', '—')}) · "
                f"horizon {max(lstats.get('cumulative_horizon_km', 0), max_reach):.1f} km · "
                f"{lstats.get('total_cleaned_forever', 0)} cleaned forever"
            ),
            "permitted_count": permitted_n,
            "unpermitted_count": len(unpermitted_aps),
            "pollution_count": len(unpermitted_aps),
            "passive_reach_km_max": max_reach,
            "cumulative_horizon_km": lstats.get("cumulative_horizon_km", 0),
            "pollution_lifetime_seen": lstats.get("total_pollution_seen", 0),
            "pollution_lifetime_cleaned": lstats.get("total_cleaned_forever", 0),
            "resolution_tier": tier,
            "resolution_score": res.get("score"),
            "antenna_field_count": ant_n,
            "near_infinite_passive": True,
            "fcc_safe": True,
            "global": True,
        })

    by_ssid: dict[str, list[dict[str, Any]]] = {}
    for ap in scan:
        by_ssid.setdefault(ap.get("ssid") or "(hidden)", []).append(ap)

    for ssid, group in by_ssid.items():
        if ssid == "(hidden)":
            strong_hidden = [a for a in group if int(a.get("signal_dbm") or 0) >= 70]
            if len(strong_hidden) >= 2:
                threats.append({
                    "ts": ts,
                    "kind": "hidden_surveillance",
                    "severity": "high" if len(strong_hidden) >= 3 else "medium",
                    "ssid": ssid,
                    "detail": f"{len(strong_hidden)} strong hidden APs in passive scan",
                    "global": True,
                })
            continue
        bssids = {a.get("bssid") for a in group if a.get("bssid")}
        if len(bssids) >= 2:
            open_aps = [a for a in group if a.get("open")]
            secure = [a for a in group if not a.get("open")]
            if open_aps and secure:
                threats.append({
                    "ts": ts,
                    "kind": "evil_twin",
                    "severity": "high",
                    "ssid": ssid,
                    "bssid": open_aps[0].get("bssid"),
                    "detail": f"Evil-twin pattern — open + secure BSSIDs for SSID {ssid[:32]}",
                    "global": True,
                })
        if SUSPICIOUS_SSID_RE.search(ssid):
            for ap in group:
                if ap.get("open"):
                    threats.append({
                        "ts": ts,
                        "kind": "rogue_open",
                        "severity": "high",
                        "ssid": ssid,
                        "bssid": ap.get("bssid"),
                        "detail": f"Open rogue AP mimicking public WiFi — {ssid[:40]}",
                        "global": True,
                    })
        if ENTERPRISE_SSID_RE.search(ssid):
            for ap in group:
                if ap.get("open") or "wep" in str(ap.get("security") or ""):
                    threats.append({
                        "ts": ts,
                        "kind": "enterprise_downgrade",
                        "severity": "high",
                        "ssid": ssid,
                        "bssid": ap.get("bssid"),
                        "detail": f"Enterprise-looking SSID with weak security ({ap.get('security')})",
                        "global": True,
                    })

    for ap in scan:
        oui = str(ap.get("bssid_oui") or "").upper()
        bssid_norm = _norm_mac(str(ap.get("bssid") or ""))
        if bssid_norm and bssid_norm in hostile_macs:
            threats.append({
                "ts": ts,
                "kind": "hostile_oui",
                "severity": "critical",
                "ssid": ap.get("ssid"),
                "bssid": ap.get("bssid"),
                "detail": "BSSID matches archived hostile dossier MAC",
                "global": True,
            })
        if oui in suspicious_ouis:
            threats.append({
                "ts": ts,
                "kind": "hostile_oui",
                "severity": "high",
                "ssid": ap.get("ssid"),
                "bssid": ap.get("bssid"),
                "detail": f"Suspicious OUI {oui} — {suspicious_ouis[oui]}",
                "global": True,
            })

    if active:
        active_bssid = _norm_mac(str(active.get("bssid") or ""))
        active_ssid = str(active.get("ssid") or "")
        if _is_own_router(bssid=active_bssid, ssid=active_ssid):
            active["own_router"] = True
            hist["own_router_active"] = True
        active_ok, active_reason = _is_permitted_frequency(
            active.get("freq_mhz"), active.get("channel"),
        )
        if active.get("own_router") and not active_ok:
            _fix_own_router(
                "connected_own_router_freq_parse",
                f"Home router on ch{active.get('channel')} — refresh path, no disconnect",
            )
            active_ok = True
            active_reason = "own_router_fix_not_kill"
        if not active_ok and permitted_only:
            threats.append({
                "ts": ts,
                "kind": "connected_unpermitted",
                "severity": "critical",
                "ssid": active.get("ssid"),
                "bssid": active.get("bssid"),
                "device": active.get("device"),
                "detail": (
                    f"CONNECTED ON UNPERMITTED SPECTRUM — {active_reason} · "
                    f"immediate lawful disconnect + shoot-to-kill"
                ),
                "shoot_to_kill": shoot,
                "global": True,
            })
        for t in threats:
            if t.get("severity") in ("high", "critical") and t.get("bssid"):
                if _norm_mac(str(t.get("bssid"))) == active_bssid:
                    if active.get("own_router"):
                        _fix_own_router(
                            "own_router_false_rogue",
                            f"Skipped kill — home router {active_ssid} flagged by {t.get('kind')}",
                        )
                        break
                    threats.append({
                        "ts": ts,
                        "kind": "connected_rogue",
                        "severity": "critical",
                        "ssid": active.get("ssid"),
                        "bssid": active.get("bssid"),
                        "device": active.get("device"),
                        "detail": f"Connected to flagged AP {active.get('ssid')} — lawful kick eligible",
                        "shoot_to_kill": shoot,
                        "global": True,
                    })
                    break
        if active.get("ssid") and active.get("ssid") not in trusted_ssids and not SUSPICIOUS_SSID_RE.search(active.get("ssid", "")):
            trusted_ssids.add(active.get("ssid"))

    for point in _correlated_hostile_points()[:16]:
        ip = str(point.get("ip") or "")
        if not ip:
            continue
        certain = bool(point.get("strike_certain"))
        heat = float(point.get("heat") or 0)
        if certain:
            threats.append({
                "ts": ts,
                "kind": "correlated_hostile_ip",
                "severity": "critical",
                "ip": ip,
                "detail": f"Monitor host {ip} at 100% strike certainty — wire kick eligible",
                "global": True,
                "strike_certain": True,
            })
        elif heat >= 0.5 or ip in _blocked_ips():
            threats.append({
                "ts": ts,
                "kind": "hot_attack_correlated",
                "severity": "high" if heat >= 0.7 else "medium",
                "ip": ip,
                "detail": f"Host attack heat {heat:.2f} — RF field hostility correlated",
                "global": True,
                "heat": heat,
            })

    disabled_bssids = _forever_disabled_bssids()
    for ap in scan:
        bnorm = _norm_mac(str(ap.get("bssid") or ""))
        if bnorm and bnorm in disabled_bssids:
            threats.append({
                "ts": ts,
                "kind": "forever_disabled_nearby",
                "severity": "critical",
                "ssid": ap.get("ssid"),
                "bssid": ap.get("bssid"),
                "detail": "Forever-disabled unhealthy BSSID seen again in passive field",
                "global": True,
            })

    if len(unpermitted_aps) >= 3:
        threats.append({
            "ts": ts,
            "kind": "pollution_cluster",
            "severity": "critical",
            "detail": f"Pollution cluster — {len(unpermitted_aps)} unpermitted APs in one scan",
            "global": True,
            "count": len(unpermitted_aps),
        })

    blocked = _blocked_ips()
    if blocked and (unpermitted_aps or any(t.get("kind") == "evil_twin" for t in threats)):
        threats.append({
            "ts": ts,
            "kind": "blocked_peer_rf",
            "severity": "high",
            "detail": f"Blocked/hostile IP memory ({len(blocked)}) + active RF pollution — rfkill advanced",
            "global": True,
            "blocked_count": len(blocked),
        })

    hist["trusted_ssids"] = sorted(trusted_ssids)[-40:]
    return [t for t in threats if t.get("severity") != "info" or t.get("kind") == "global_wireless_field"]


def _disconnect_wifi(dev: str, reason: str) -> bool:
    if not dev:
        return False
    out = _run(["nmcli", "dev", "disconnect", dev], timeout=12)
    return "successfully" in out.lower() or dev in out


def _firewall_block_ip(ip: str, reason: str) -> bool:
    script = INSTALL / "lib" / "firewall-sentinel.sh"
    if not script.is_file() or not ip:
        return False
    safe_ip = ip.replace("'", "'\"'\"'")
    safe_reason = reason.replace("'", "'\"'\"'")
    cmd = (
        f"source {INSTALL}/lib/nexus-common.sh && "
        f"source {script} && "
        f"nexus_firewall_block_ip_forever out '{safe_ip}' '{safe_reason}' && "
        f"nexus_firewall_block_ip_forever in '{safe_ip}' '{safe_reason}'"
    )
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
    env["NEXUS_STATE_DIR"] = str(STATE)
    proc = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=20, env=env)
    return proc.returncode == 0


def _autokill_ip(ip: str) -> dict[str, Any]:
    script = INSTALL / "lib" / "field-attack-kit.py"
    if not script.is_file() or not ip:
        return {"ok": False, "ip": ip}
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
    env["NEXUS_STATE_DIR"] = str(STATE)
    proc = subprocess.run(
        [os.environ.get("PYTHON", "pythong"), str(script), "kill", ip, "WIFI_THREAT", "high", "rf_lawful_kick"],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": proc.returncode == 0, "ip": ip}


def _lawful_kick(
    threats: list[dict[str, Any]],
    wifi_dev: str | None,
    active: dict[str, Any] | None,
) -> dict[str, Any]:
    cfg = _shield_config()
    if not cfg.get("enabled") or not cfg.get("lawful_kick"):
        return {"active": False, "action": "lawful_kick_disabled", "fcc_passive_only": True}

    kicks: list[dict[str, Any]] = []
    kicked_ips: set[str] = set()
    shoot = cfg.get("shoot_to_kill", True)

    kickable = {t.get("kind") for t in threats if t.get("severity") in ("high", "critical")}
    disconnect_kinds = {
        "connected_rogue", "connected_unpermitted", "evil_twin", "rogue_open",
        "unpermitted_spectrum", "hostile_oui",
    }
    if shoot:
        disconnect_kinds.update(kickable)

    must_disconnect = bool(kickable & disconnect_kinds) or "connected_unpermitted" in kickable
    if active and _is_own_router(
        bssid=str(active.get("bssid") or ""),
        ssid=str(active.get("ssid") or ""),
    ):
        fix = _fix_own_router("lawful_kick_own_router", "Home router — fix path instead of disconnect")
        strikes: list[dict[str, Any]] = []
        mod = _own_router_mod()
        if mod and hasattr(mod, "strike_action_behind"):
            for t in threats:
                if t.get("severity") not in ("high", "critical"):
                    continue
                if _is_own_router(
                    ip=str(t.get("ip") or ""),
                    bssid=str(t.get("bssid") or ""),
                    ssid=str(t.get("ssid") or ""),
                ):
                    strikes.append(mod.strike_action_behind(t))
                elif t.get("kind") in ("hot_attack_correlated", "correlated_hostile_ip", "outbound_wireless_signal"):
                    strikes.append(mod.strike_action_behind(t))
        return {
            "active": True,
            "action": "fix_own_router_strike_actor",
            "fcc_passive_only": cfg.get("fcc_passive_only", True),
            "own_router_fix": fix,
            "action_strikes": strikes,
            "kicks": [],
        }
    if active and wifi_dev and must_disconnect:
        reason = "fcc_shoot_to_kill_unpermitted" if "connected_unpermitted" in kickable else "fcc_lawful_kick_rogue_ap"
        if _disconnect_wifi(wifi_dev, reason):
            kicks.append({
                "action": "disconnect_unpermitted_spectrum" if "connected_unpermitted" in kickable else "disconnect_rogue_ap",
                "device": wifi_dev,
                "ssid": active.get("ssid"),
                "bssid": active.get("bssid"),
                "fcc": "Part15_device_control",
                "shoot_to_kill": shoot,
            })

    for t in threats:
        if t.get("kind") != "correlated_hostile_ip" or not t.get("strike_certain"):
            continue
        ip = str(t.get("ip") or "")
        if not ip or ip in kicked_ips:
            continue
        kicked_ips.add(ip)
        result = _autokill_ip(ip)
        if result.get("ok") or result.get("hardware_destroy"):
            kicks.append({
                "action": "autokill_strike_certain",
                "ip": ip,
                "hardware_destroy": result.get("hardware_destroy"),
                "fcc": "network_layer_only",
                "shoot_to_kill": shoot,
            })
        elif _firewall_block_ip(ip, "fcc_wifi_correlated_hostile"):
            kicks.append({
                "action": "firewall_block_correlated_ip",
                "ip": ip,
                "fcc": "network_layer_only",
                "shoot_to_kill": shoot,
            })

    if shoot:
        for t in threats:
            if t.get("kind") not in ("unpermitted_spectrum", "connected_unpermitted", "hostile_oui"):
                continue
            ip = str(t.get("ip") or "")
            if not ip or ip in kicked_ips:
                continue
            if _firewall_block_ip(ip, "fcc_unpermitted_spectrum_shoot_to_kill"):
                kicked_ips.add(ip)
                kicks.append({
                    "action": "firewall_block_unpermitted",
                    "ip": ip,
                    "bssid": t.get("bssid"),
                    "shoot_to_kill": True,
                })

    for t in threats:
        ip = str(t.get("ip") or "")
        if not ip or ip in kicked_ips or t.get("kind") == "correlated_hostile_ip":
            continue
        if t.get("severity") == "critical" and _firewall_block_ip(ip, "fcc_wifi_threat"):
            kicked_ips.add(ip)
            kicks.append({"action": "firewall_block_correlated_ip", "ip": ip, "shoot_to_kill": shoot})

    unpermitted_killed = [
        {
            "bssid": t.get("bssid"),
            "ssid": t.get("ssid"),
            "channel": t.get("channel"),
            "freq_mhz": t.get("freq_mhz"),
            "detail": t.get("detail"),
        }
        for t in threats
        if t.get("kind") == "unpermitted_spectrum"
    ]

    forever_disabled: list[dict[str, Any]] = []
    if cfg.get("disable_unhealthy_forever", True) and shoot:
        seen: set[str] = set()
        for t in threats:
            if t.get("severity") not in ("high", "critical"):
                continue
            key = f"{t.get('kind')}|{_norm_mac(str(t.get('bssid') or ''))}|{t.get('ip') or ''}"
            if key in seen:
                continue
            seen.add(key)
            result = _disable_unhealthy_forever(t)
            if result:
                forever_disabled.append(result)
                kicks.append({**result, "fcc": "disabled_forever"})

    rfkill_result = _apply_auto_rfkill(threats, wifi_dev, active)
    if rfkill_result.get("rfkill_actions"):
        kicks.extend(rfkill_result["rfkill_actions"])

    reg = _forever_registry()
    return {
        "active": True,
        "action": "shoot_to_kill" if (shoot and kicks) else ("lawful_kick" if kicks else "watch_only"),
        "fcc_passive_only": cfg.get("fcc_passive_only", True),
        "shoot_to_kill": shoot,
        "disable_unhealthy_forever": cfg.get("disable_unhealthy_forever", True),
        "permitted_spectrum_only": cfg.get("permitted_spectrum_only", True),
        "kicks": kicks,
        "kick_count": len(kicks),
        "unpermitted_killed": unpermitted_killed,
        "forever_disabled": forever_disabled,
        "forever_disabled_count": len(forever_disabled),
        "forever_registry_count": len(reg.get("entries") or {}),
        "auto_rfkill": cfg.get("auto_rfkill", True),
        "rfkill": rfkill_result,
        "hostility_score": rfkill_result.get("hostility_score", 0),
    }


def _history() -> dict[str, Any]:
    return _load_json(HISTORY, {"samples": [], "rfkill": [], "scans": {}, "trusted_ssids": []})


def _save_history(doc: dict[str, Any]) -> None:
    doc["updated"] = _now()
    samples = doc.get("samples") or []
    doc["samples"] = samples[-120:]
    _save_json(HISTORY, doc)


def _recent_threats(limit: int = 40) -> list[dict[str, Any]]:
    if not THREATS_LOG.is_file():
        return []
    lines = deque(maxlen=limit)
    try:
        with THREATS_LOG.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    lines.append(line)
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def sample_cycle() -> dict[str, Any]:
    hist = _history()
    devices = _nmcli_devices()
    rfkill = _rfkill_rows()
    wifi_rows = _wifi_device_rows(devices)
    phy_map = _iw_wifi_phy_map()

    per_scans: dict[str, list[dict[str, Any]]] = {}
    antenna_fields: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    wifi_dev: str | None = None

    for row in wifi_rows:
        dev = str(row.get("device") or "")
        if not dev:
            continue
        if wifi_dev is None or "connected" in str(row.get("state") or "").lower():
            wifi_dev = dev
        _run(["nmcli", "dev", "wifi", "rescan", "ifname", dev], timeout=12)
        dev_scan = _wifi_scan(dev)
        per_scans[dev] = dev_scan
        conn = _active_wifi_connection(dev)
        if conn and (active is None or "connected" in str(row.get("state") or "").lower()):
            active = conn
        antenna_fields.append(_antenna_field_descriptor(row, phy_map.get(dev), dev_scan, conn))

    scan, merge_stats = _merge_multi_antenna_scans(per_scans)
    resolution = _resolution_from_antenna_fields(antenna_fields, merge_stats)
    hist["last_resolution"] = resolution
    hist["last_antenna_field_count"] = resolution.get("active_antenna_fields", 0)

    kick_dev = (active or {}).get("device") or wifi_dev

    if active and scan:
        active_bssid = _norm_mac(str(active.get("bssid") or ""))
        for ap in scan:
            if _norm_mac(str(ap.get("bssid") or "")) == active_bssid:
                active["channel"] = ap.get("channel")
                active["freq_mhz"] = ap.get("freq_mhz")
                active["permitted"] = ap.get("permitted")
                active["antenna_count"] = ap.get("antenna_count")
                active["antenna_sources"] = ap.get("antenna_sources")
                break

    forever_enforce = _forever_rf_enforce(kick_dev, active, scan)

    threats = _detect_wireless_threats(scan, active, hist)
    for t in threats:
        if t.get("severity") != "info":
            bnorm = _norm_mac(str(t.get("bssid") or ""))
            if bnorm and _is_disabled_forever(bssid=bnorm):
                t["disabled_forever"] = True
            ip = str(t.get("ip") or "")
            if ip and _is_disabled_forever(ip=ip):
                t["disabled_forever"] = True
            _append_threat(t)

    kick_result = _lawful_kick(threats, kick_dev, active)
    kick_result["forever_enforce"] = forever_enforce
    pollution_cleanup = _global_pollution_cleanup(scan, threats, kick_result)
    kick_result["global_pollution_cleanup"] = pollution_cleanup

    if per_scans:
        scans = hist.get("scans") or {}
        for dev, dev_scan in per_scans.items():
            scans[dev] = dev_scan[:60]
        hist["scans"] = scans
        hist["antenna_fields"] = antenna_fields
    hist["rfkill"] = rfkill
    hist.setdefault("samples", []).append({
        "ts": _now(),
        "threat_count": sum(1 for t in threats if t.get("severity") != "info"),
        "kick_count": kick_result.get("kick_count", 0),
    })
    _save_history(hist)

    bands = {s.get("band") for s in scan if s.get("band")}
    unpermitted = [s for s in scan if s.get("permitted") is False]

    material_field: dict[str, Any] = {}
    scan_material: list[dict[str, Any]] = scan
    try:
        spec = importlib.util.spec_from_file_location(
            "field_material_discern", INSTALL / "lib" / "field-material-discern.py",
        )
        if spec and spec.loader:
            _md = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_md)
            material_field = _md.build_material_field(scan, antenna_fields, persist=True)
            scan_material = _md.annotate_scan(scan, material_field)
    except Exception:
        material_field = {}

    frequency_registry = _build_frequency_registry(scan_material)

    return {
        "updated": _now(),
        "fcc": _fcc_policy(),
        "permitted_bands": _permitted_bands().get("bands") or [],
        "antenna": {
            "mode": "global_passive_pollution_cleanup",
            "description": "Near-infinite passive reach — multi-antenna fusion improves resolution, FCC safe",
            "wifi_device": wifi_dev,
            "wifi_devices": [f.get("device") for f in antenna_fields if f.get("device")],
            "antenna_fields": antenna_fields,
            "merge_stats": merge_stats,
            "resolution": resolution,
            "resolution_tier": resolution.get("tier"),
            "resolution_score": resolution.get("score"),
            "scan_count": len(scan),
            "raw_scan_total": merge_stats.get("raw_scan_total", len(scan)),
            "permitted_count": sum(1 for s in scan if s.get("permitted")),
            "unpermitted_count": len(unpermitted),
            "pollution_count": len(unpermitted),
            "multi_antenna_sightings": merge_stats.get("multi_antenna_sightings", 0),
            "passive_reach_km_max": max((s.get("passive_reach_km") or 0) for s in scan) if scan else 0,
            "cumulative_horizon_km": (pollution_cleanup.get("effective_horizon_km") or 0),
            "near_infinite_passive": True,
            "fcc_safe": True,
            "bands_seen": sorted(b for b in bands if b),
            "rfkill_count": len(rfkill),
            "active_connection": active,
        },
        "global_pollution": pollution_cleanup,
        "pollution_policy": _pollution_policy(),
        "operations_log": _recent_operations(40),
        "interfaces": devices,
        "rfkill": rfkill,
        "threats": [t for t in threats if t.get("severity") != "info"],
        "global_field": next((t for t in threats if t.get("kind") == "global_wireless_field"), None),
        "recent_threats": _recent_threats(30),
        "shield": {**_shield_config(), **kick_result},
        "lawful_kicks": kick_result.get("kicks") or [],
        "unpermitted_killed": kick_result.get("unpermitted_killed") or [],
        "unpermitted_aps": unpermitted[:40],
        "forever_disabled": kick_result.get("forever_disabled") or [],
        "forever_registry": _forever_registry(),
        "forever_enforce": kick_result.get("forever_enforce") or {},
        "bursts": [],
        "recent_bursts": [],
        "material_field": material_field,
        "scan_material": scan_material[:80],
        "frequency_registry": frequency_registry,
    }


def panel_json() -> dict[str, Any]:
    doc = _load_json(PANEL_CACHE, {})
    if not doc.get("updated"):
        doc = sample_cycle()
        _save_json(PANEL_CACHE, doc)
    return {
        "motto": "Near-infinite passive reach — global pollution cleanup, always FCC safe.",
        "tagline": "Passive horizon grows every cycle. Pollution ledger never forgets. Clean forever on the wire. No jamming.",
        "fcc": doc.get("fcc") or _fcc_policy(),
        "pollution_policy": doc.get("pollution_policy") or _pollution_policy(),
        "global_pollution": doc.get("global_pollution") or {},
        "operations_log": doc.get("operations_log") or _recent_operations(40),
        "permitted_bands": doc.get("permitted_bands") or _permitted_bands().get("bands") or [],
        "updated": doc.get("updated") or _now(),
        "antenna": doc.get("antenna") or {},
        "interfaces": doc.get("interfaces") or _nmcli_devices(),
        "rfkill": doc.get("rfkill") or _rfkill_rows(),
        "threats": doc.get("threats") or [],
        "global_field": doc.get("global_field"),
        "recent_threats": doc.get("recent_threats") or _recent_threats(),
        "lawful_kicks": doc.get("lawful_kicks") or [],
        "unpermitted_killed": doc.get("unpermitted_killed") or [],
        "unpermitted_aps": doc.get("unpermitted_aps") or [],
        "forever_disabled": doc.get("forever_disabled") or [],
        "forever_registry": doc.get("forever_registry") or _forever_registry(),
        "shield": doc.get("shield") or _shield_config(),
        "threat_kinds": [
            {"id": "unpermitted_spectrum", "label": "Unpermitted spectrum (SHOOT TO KILL)", "vector": "WIFI_THREAT"},
            {"id": "connected_unpermitted", "label": "Connected on illegal frequency", "vector": "WIFI_THREAT"},
            {"id": "evil_twin", "label": "Evil twin AP", "vector": "WIFI_THREAT"},
            {"id": "rogue_open", "label": "Rogue open AP", "vector": "WIFI_THREAT"},
            {"id": "hostile_oui", "label": "Hostile / suspicious OUI", "vector": "WIFI_THREAT"},
            {"id": "enterprise_downgrade", "label": "Enterprise downgrade", "vector": "WIFI_THREAT"},
            {"id": "hidden_surveillance", "label": "Hidden AP cluster", "vector": "WIFI_THREAT"},
            {"id": "connected_rogue", "label": "Connected to rogue", "vector": "WIFI_THREAT"},
            {"id": "correlated_hostile_ip", "label": "100% hostile IP (wire kick)", "vector": "WIFI_THREAT"},
            {"id": "global_wireless_field", "label": "Global passive field", "vector": "FIELD_ANTENNA_ALERT"},
            {"id": "global_pollution", "label": "Global pollution cleanup", "vector": "WIFI_THREAT"},
            {"id": "hot_attack_correlated", "label": "Hot host attack correlated", "vector": "WIFI_THREAT"},
            {"id": "blocked_peer_rf", "label": "Blocked peer + RF pollution", "vector": "WIFI_THREAT"},
            {"id": "forever_disabled_nearby", "label": "Forever-disabled BSSID nearby", "vector": "WIFI_THREAT"},
            {"id": "pollution_cluster", "label": "Unpermitted pollution cluster", "vector": "WIFI_THREAT"},
        ],
        "bursts": [],
        "recent_bursts": [],
        "burst_kinds": [],
        "material_field": doc.get("material_field") or {},
        "scan_material": doc.get("scan_material") or [],
        "frequency_registry": doc.get("frequency_registry") or _build_frequency_registry(
            doc.get("scan_material") or [],
        ),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "cycle":
        doc = sample_cycle()
        _save_json(PANEL_CACHE, doc)
        print(json.dumps(doc, ensure_ascii=False))
        return 0
    if cmd == "shield" and len(sys.argv) >= 3:
        enabled = sys.argv[2].strip().lower() in ("1", "true", "on", "yes")
        auto = True
        lawful = True
        shoot = True
        if len(sys.argv) >= 4:
            auto = sys.argv[3].strip().lower() in ("1", "true", "on", "yes")
        if len(sys.argv) >= 5:
            lawful = sys.argv[4].strip().lower() in ("1", "true", "on", "yes", "")
        if len(sys.argv) >= 6:
            shoot = sys.argv[5].strip().lower() in ("1", "true", "on", "yes", "")
        doc = _set_shield(enabled=enabled, auto_rfkill=auto, lawful_kick=lawful, shoot_to_kill=shoot)
        print(json.dumps({
            "ok": True,
            "shield": doc,
            "fcc_passive_only": True,
            "shoot_to_kill": doc.get("shoot_to_kill", True),
        }, ensure_ascii=False))
        return 0
    if cmd == "permitted-check" and len(sys.argv) >= 4:
        ok, reason = _is_permitted_frequency(sys.argv[2], sys.argv[3])
        print(json.dumps({"permitted": ok, "reason": reason}, ensure_ascii=False))
        return 0
    if cmd == "forever-enforce":
        wifi_rows = _wifi_device_rows()
        per_scans: dict[str, list[dict[str, Any]]] = {}
        active = None
        wifi_dev = None
        for row in wifi_rows:
            dev = str(row.get("device") or "")
            if not dev:
                continue
            if wifi_dev is None or "connected" in str(row.get("state") or "").lower():
                wifi_dev = dev
            per_scans[dev] = _wifi_scan(dev)
            conn = _active_wifi_connection(dev)
            if conn and (active is None or "connected" in str(row.get("state") or "").lower()):
                active = conn
        scan, _ = _merge_multi_antenna_scans(per_scans)
        kick_dev = (active or {}).get("device") or wifi_dev
        result = _forever_rf_enforce(kick_dev, active, scan)
        print(json.dumps({"ok": True, **result}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-rf-sentinel.py [json|cycle|forever-enforce|shield on|off [auto_rfkill] [lawful_kick] [shoot_to_kill]|permitted-check FREQ CHAN]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())