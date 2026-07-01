#!/usr/bin/env pythong
"""HeavyBoi v7 — ingest nexus-kill-intel JSON into dossier, globe pins, autokill queue."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SOURCE = Path(os.environ.get("NEXUS_SHIELD_SOURCE", ""))
DOSSIER_BUNDLED = INSTALL / "data" / "human-dossier-kill-orders.json"
DOSSIER_SOURCE = (SOURCE / "data" / "human-dossier-kill-orders.json") if SOURCE else None
OVERRIDES = STATE / "human-dossier-overrides.json"
INGEST_LOG = STATE / "heavyboi-ingest-log.jsonl"
HOSTILE_TSV = STATE / "field-hostile.tsv"
DEFAULT_INTEL = Path("/tmp/nexus-kill-intel.json")
PENDING_INTEL = STATE / "nexus-kill-intel-pending.json"

PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.)"
)

_fg: Any = None
_geo: Any = None


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


def _mod(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _friendly_guard() -> Any:
    global _fg
    if _fg is None:
        _fg = _mod("friendly_guard", "friendly-guard.py")
    return _fg


def _geo_enrich() -> Any:
    global _geo
    if _geo is None:
        _geo = _mod("geo_intel", "geo-intel-standards.py")
    return _geo


def validate_kill_orders(orders: list[dict[str, Any]]) -> dict[str, Any]:
    fg = _friendly_guard()
    validated: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    for order in orders:
        ip = str(order.get("ip") or "").strip()
        if not ip or PRIVATE_RE.match(ip):
            refused.append({"ip": ip or "?", "reason": "private_or_empty"})
            continue
        refuse, reason = fg.refuse_kill(ip)
        if refuse:
            refused.append({"ip": ip, "reason": reason})
            continue
        validated.append(order)
    return {
        "schema": "heavyboi-validate/v1",
        "version": getattr(fg, "GUARD_VERSION", "3.3.2"),
        "validated": validated,
        "refused": refused,
        "validated_count": len(validated),
        "refused_count": len(refused),
    }


def _likelihood_score(order: dict[str, Any]) -> str:
    if order.get("hosting_likelihood"):
        return str(order["hosting_likelihood"])
    level = str(order.get("confidence") or order.get("likelihood") or "").lower()
    if level in ("high", "critical", "certain"):
        return "High — dedicated abuse infrastructure"
    if level in ("medium", "watch"):
        return "Medium — corroborated threat intel"
    return "High — HeavyBoi kill-order intel"


def _order_to_dossier_row(order: dict[str, Any], *, ingested_at: str) -> dict[str, Any]:
    ip = str(order.get("ip") or "").strip()
    geo = dict(order.get("geo") or {})
    malware = (
        order.get("associated_malware")
        or order.get("malware")
        or order.get("family")
        or "unknown"
    )
    reason = str(order.get("reason") or order.get("notes") or "HeavyBoi kill-order intel")
    enriched = {}
    if not geo.get("lat") or not geo.get("country_code"):
        try:
            enriched = _geo_enrich().enrich_ip(ip, online=False)
        except Exception:
            enriched = {}
    if enriched:
        geo.setdefault("country_code", enriched.get("country_code"))
        geo.setdefault("city", enriched.get("city"))
        geo.setdefault("lat", enriched.get("lat"))
        geo.setdefault("lon", enriched.get("lon"))
    asn = str(order.get("asn_org") or order.get("asn") or enriched.get("org") or "")
    return {
        "ip": ip,
        "last_known_appearance": order.get("last_known_appearance") or reason[:160],
        "first_seen": order.get("first_seen") or ingested_at[:10],
        "last_seen": order.get("last_seen") or ingested_at[:10],
        "hosting_likelihood": _likelihood_score(order),
        "associated_malware": str(malware),
        "geo": geo,
        "asn_org": asn,
        "notes": reason,
        "heavyboi_status": str(order.get("status") or "KILLED"),
        "rekill_ready": bool(order.get("rekill_ready", True)),
        "ingested_at": ingested_at,
        "source": "heavyboi",
    }


def _merge_dict(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = dict(a)
    for key, val in b.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _merge_dict(out[key], val)
        elif val not in (None, ""):
            out[key] = val
    return out


def _append_hostile(ip: str, reason: str) -> None:
    if not ip or PRIVATE_RE.match(ip):
        return
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        if not HOSTILE_TSV.is_file():
            HOSTILE_TSV.write_text("ts\tip\tvector\tseverity\treason\tsource\n", encoding="utf-8")
        text = HOSTILE_TSV.read_text(encoding="utf-8", errors="replace")
        if f"\t{ip}\t" in text:
            return
        with HOSTILE_TSV.open("a", encoding="utf-8") as fh:
            fh.write(f"{_now()}\t{ip}\tHEAVYBOI_INTEL\tcritical\t{reason[:120]}\theavyboi\n")
    except OSError:
        pass


def _write_bundled_dossier(doc: dict[str, Any]) -> list[str]:
    written: list[str] = []
    targets: list[Path] = []
    if DOSSIER_BUNDLED.parent.is_dir():
        targets.append(DOSSIER_BUNDLED)
    if DOSSIER_SOURCE and DOSSIER_SOURCE.parent.is_dir():
        targets.append(DOSSIER_SOURCE)
    seen: set[str] = set()
    for path in targets:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        try:
            _save_json(path, doc)
            written.append(key)
        except OSError:
            continue
    return written


def _apply_overrides(doc: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    ov = _load_json(OVERRIDES, {"ips": {}})
    omap = ov.get("ips")
    if not isinstance(omap, dict):
        omap = {}
    for row in rows:
        ip = str(row.get("ip") or "")
        if ip:
            omap[ip] = _merge_dict(omap.get(ip) or {"ip": ip}, row)
    ov["ips"] = omap
    ov["updated"] = _now()
    ov["heavyboi_version"] = "7.0.0"
    _save_json(OVERRIDES, ov)
    by_ip = {str(r.get("ip")): r for r in doc.get("ips") or [] if r.get("ip")}
    for ip, patch in omap.items():
        if ip in by_ip:
            by_ip[ip] = _merge_dict(by_ip[ip], patch)
        else:
            by_ip[ip] = dict(patch)
    ips = list(by_ip.values())
    doc["ips"] = ips
    doc["ip_count"] = len(ips)
    doc["generated_at"] = _now()
    doc["heavyboi_version"] = "7.0.0"
    doc["dossier_version"] = "7.0"


def ingest_kill_intel(
    json_path: str | Path | None = None,
    *,
    body: dict[str, Any] | None = None,
    autokill: bool | None = None,
    refresh_globe: bool = True,
) -> dict[str, Any]:
    """Parse nexus-kill-intel JSON, merge dossier, queue globe pins + optional autokill."""
    if body is not None:
        data = body
        src = "api_body"
    else:
        path = Path(json_path or DEFAULT_INTEL)
        if not path.is_file() and PENDING_INTEL.is_file():
            path = PENDING_INTEL
        if not path.is_file():
            return {"ok": False, "error": "missing_kill_intel", "path": str(path)}
        data = _load_json(path, {})
        src = str(path)
    orders = list(data.get("kill_orders") or data.get("orders") or [])
    if not orders:
        return {"ok": False, "error": "no_kill_orders", "source": src}

    validation = validate_kill_orders(orders)
    validated = validation["validated"]
    ingested_at = _now()
    doc = _load_json(DOSSIER_BUNDLED, {"ips": [], "analyst": "Grok Heavy", "dossier_version": "1.0"})
    rows: list[dict[str, Any]] = []
    killed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for order in validated:
        row = _order_to_dossier_row(order, ingested_at=ingested_at)
        rows.append(row)
        ip = row["ip"]
        _append_hostile(ip, row.get("notes") or "heavyboi")
        try:
            with INGEST_LOG.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": ingested_at, "ip": ip, "status": row["heavyboi_status"], "reason": row.get("notes")}, ensure_ascii=False) + "\n")
        except OSError:
            pass

    _apply_overrides(doc, rows)
    written = _write_bundled_dossier(doc)

    do_autokill = autokill if autokill is not None else os.environ.get("NEXUS_HEAVYBOI_AUTOKILL", "1") == "1"
    if do_autokill and validated:
        kit = INSTALL / "lib" / "field-attack-kit.py"
        if kit.is_file():
            for order in validated:
                ip = str(order.get("ip") or "").strip()
                reason = str(order.get("reason") or "heavyboi_intel")
                proc = subprocess.run(
                    ["pythong", str(kit), "kill", ip, "HEAVYBOI_INTEL", "critical", reason],
                    env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                try:
                    result = json.loads(proc.stdout or "{}")
                except json.JSONDecodeError:
                    result = {"ok": proc.returncode == 0, "ip": ip}
                if result.get("ok") or result.get("killed"):
                    killed.append({"ip": ip, "killed": True})
                else:
                    skipped.append({"ip": ip, "reason": result.get("reason") or "kill_failed"})

    if refresh_globe:
        script = INSTALL / "lib" / "host-attack-map.py"
        if script.is_file():
            subprocess.run(
                ["pythong", str(script), "build-fast"],
                env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                capture_output=True,
                timeout=120,
                check=False,
            )
        sync_py = INSTALL / "lib" / "human-dossier.sh"
        if sync_py.is_file():
            subprocess.run(
                ["bash", "-c", f"source '{INSTALL}/lib/nexus-common.sh'; source '{INSTALL}/lib/human-dossier.sh'; nexus_human_dossier_sync"],
                env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                capture_output=True,
                timeout=30,
                check=False,
            )

    for path in (DEFAULT_INTEL, PENDING_INTEL):
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass

    return {
        "ok": True,
        "schema": "heavyboi-ingest/v1",
        "version": "7.0.0",
        "hostess_version": "7",
        "source": src,
        "ingested_at": ingested_at,
        "ingested_count": len(rows),
        "refused_count": validation["refused_count"],
        "refused": validation["refused"],
        "killed_count": len(killed),
        "killed": killed,
        "skipped": skipped,
        "dossier_ip_count": doc.get("ip_count", len(doc.get("ips") or [])),
        "bundled_written": written,
        "globe_refreshed": refresh_globe,
        "autokill": do_autokill,
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "ingest").strip()
    if cmd == "validate" and len(sys.argv) >= 3:
        data = json.loads(sys.argv[2])
        print(json.dumps(validate_kill_orders(list(data.get("kill_orders") or [])), ensure_ascii=False))
        return 0
    if cmd == "ingest":
        path = sys.argv[2] if len(sys.argv) > 2 else None
        body = None
        if len(sys.argv) >= 3 and sys.argv[2] == "--json" and len(sys.argv) >= 4:
            body = json.loads(sys.argv[3])
            path = None
        print(json.dumps(ingest_kill_intel(path, body=body), ensure_ascii=False))
        return 0
    if cmd == "pending" and len(sys.argv) >= 3:
        data = json.loads(sys.argv[2])
        _save_json(PENDING_INTEL, data)
        print(json.dumps({"ok": True, "pending": str(PENDING_INTEL)}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: heavyboi-importer.py [ingest [path]|ingest --json BODY|validate JSON|pending JSON]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())