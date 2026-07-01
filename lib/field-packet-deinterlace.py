#!/usr/bin/env pythong
"""Packet deinterlace — multi-path IN pipeline: dirty dump, inspect, strip, clean×3, reconverge.

Parallel lane processors (AMOURANTHRTX FieldFabric style). Dirty never bleeds to clean.
Reconverge = secure manifest sealed under connectivity-law-watch + fabric encrypt.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
LAW_FILE = INSTALL / "data" / "connectivity-law-watch.json"
PANEL = STATE / "field-packet-deinterlace-panel.json"
MANIFEST = STATE / "packet-secure-manifest.json"
DIRTY_RING = STATE / "packet-dirty.ring.jsonl"
CLEAN_RING = STATE / "packet-clean.ring.jsonl"
SRC_RING = STATE / "packet-field.ring.jsonl"
INTENT = STATE / "connection-intent.json"
LEDGER = STATE / "field-packet-deinterlace-ledger.jsonl"

LANE_WORKERS = int(os.environ.get("NEXUS_DEINTERLACE_WORKERS", "5") or "5")
RING_MAX = int(os.environ.get("NEXUS_DEINTERLACE_RING", "600") or "600")
BATCH = int(os.environ.get("NEXUS_DEINTERLACE_BATCH", "48") or "48")

_DPI: Any = None
_FABRIC: Any = None

LANES = (
    "dirty_dump",
    "inspect",
    "strip",
    "clean_gatekeeper",
    "clean_legal",
    "clean_sovereign",
    "reconverge",
)

TRUST_RANK = {"USER_OK": 0, "EPHEMERAL": 1, "MONITOR": 2, "SUSPICIOUS": 3, "HARM_CANDIDATE": 4}


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



def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_atomic(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ring(path: Path, rows: list[dict[str, Any]], *, max_lines: int = RING_MAX) -> int:
    if not rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) > max_lines:
            path.write_text("\n".join(lines[-max_lines:]) + "\n", encoding="utf-8")
    except OSError:
        pass
    return len(rows)


def _dpi_mod() -> Any:
    global _DPI
    if _DPI is not None:
        return _DPI
    spec = importlib.util.spec_from_file_location("packet_dpi", INSTALL / "lib" / "packet-dpi.py")
    if not spec or not spec.loader:
        raise ImportError("packet-dpi.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _DPI = mod
    return mod


def _fabric_mod() -> Any | None:
    global _FABRIC
    if _FABRIC is not None:
        return _FABRIC
    py = INSTALL / "lib" / "field-fabric-encrypt.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_fabric_encrypt", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _FABRIC = mod
    return mod


def _law_catalog() -> dict[str, Any]:
    doc = _load(LAW_FILE, {})
    if doc.get("laws"):
        return doc
    seed = _load(INSTALL / "data" / "dns-legal-rfc-seed.json", {})
    laws = list(seed.get("legal_framework") or [])
    return {"schema": "connectivity-law-watch/v1", "laws": laws, "motto": seed.get("motto", "")}


def _source_batch() -> list[dict[str, Any]]:
    if not SRC_RING.is_file():
        panel = _load(STATE / "packet-field.json", {})
        return list(panel.get("recent") or [])[-BATCH:]
    rows: list[dict[str, Any]] = []
    for line in SRC_RING.read_text(encoding="utf-8", errors="replace").splitlines()[-BATCH:]:
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def lane_dirty_dump(pkt: dict[str, Any]) -> dict[str, Any]:
    return {
        "lane": "dirty_dump",
        "ts": _now(),
        "id": hashlib.sha256(json.dumps(pkt, sort_keys=True, default=str).encode()).hexdigest()[:16],
        "direction": pkt.get("direction"),
        "src": f"{pkt.get('src_ip')}:{pkt.get('src_port')}",
        "dst": f"{pkt.get('dst_ip')}:{pkt.get('dst_port')}",
        "proto": pkt.get("protocol"),
        "length": pkt.get("length"),
        "process": pkt.get("process"),
        "raw_excerpt": str(pkt.get("raw") or "")[:240],
        "english": pkt.get("english"),
        "forensic": True,
        "clean_touch": False,
    }


def lane_inspect(pkt: dict[str, Any]) -> dict[str, Any]:
    dpi = _dpi_mod().analyze_packet(pkt)
    return {
        "lane": "inspect",
        "ts": _now(),
        "direction": pkt.get("direction"),
        "endpoints": f"{pkt.get('src_ip')}:{pkt.get('src_port')} → {pkt.get('dst_ip')}:{pkt.get('dst_port')}",
        "dpi": dpi,
        "alert": bool(dpi.get("alert")),
        "vectors": dpi.get("vectors") or [],
        "verdict": dpi.get("verdict"),
    }


def lane_strip(pkt: dict[str, Any]) -> dict[str, Any]:
    """Deinterlace — metadata envelope only; payload/raw never on clean paths."""
    return {
        "lane": "strip",
        "ts": _now(),
        "envelope": {
            "direction": pkt.get("direction"),
            "protocol": pkt.get("protocol"),
            "src_ip": pkt.get("src_ip"),
            "src_port": pkt.get("src_port"),
            "dst_ip": pkt.get("dst_ip"),
            "dst_port": pkt.get("dst_port"),
            "length_class": _length_class(int(pkt.get("length") or 0)),
            "port_service": pkt.get("port_service"),
            "process": pkt.get("process"),
            "flags_class": _flags_class(str(pkt.get("flags") or "")),
        },
        "stripped": True,
        "payload_present": False,
        "raw_present": False,
    }


def _length_class(n: int) -> str:
    if n <= 0:
        return "empty"
    if n < 128:
        return "small"
    if n < 900:
        return "medium"
    return "large"


def _flags_class(flags: str) -> str:
    if "S" in flags and "A" not in flags:
        return "syn"
    if "R" in flags:
        return "rst"
    if "F" in flags:
        return "fin"
    if "P" in flags:
        return "push"
    return "ack_or_other"


def _intent_index() -> dict[str, dict[str, Any]]:
    doc = _load(INTENT, {})
    idx: dict[str, dict[str, Any]] = {}
    for row in doc.get("connections") or []:
        rip = str(row.get("remote_ip") or "")
        rport = int(row.get("remote_port") or 0)
        if rip and rport:
            idx[f"{rip}:{rport}"] = row
    return idx


def lane_clean_gatekeeper(pkt: dict[str, Any], inspect_doc: dict[str, Any]) -> dict[str, Any]:
    direction = pkt.get("direction", "")
    remote_ip = pkt.get("dst_ip") if direction == "TX" else pkt.get("src_ip")
    remote_port = int(pkt.get("dst_port") if direction == "TX" else pkt.get("src_port") or 0)
    key = f"{remote_ip}:{remote_port}"
    conn = _intent_index().get(key, {})
    verdict = conn.get("verdict") or "MONITOR"
    rank = int(conn.get("trust_rank") or TRUST_RANK.get(str(verdict), 3))
    dpi_alert = bool(inspect_doc.get("alert"))
    permit = rank <= 2 and not dpi_alert
    return {
        "lane": "clean_gatekeeper",
        "ts": _now(),
        "remote": key,
        "gatekeeper_verdict": verdict,
        "trust_rank": rank,
        "permit": permit,
        "block_scope": (conn.get("flow_policy") or {}).get("block_scope", "none"),
        "clean": permit,
    }


def lane_clean_legal(pkt: dict[str, Any], inspect_doc: dict[str, Any]) -> dict[str, Any]:
    catalog = _law_catalog()
    vectors = set(inspect_doc.get("vectors") or [])
    dpi = inspect_doc.get("dpi") or {}
    violations: list[dict[str, str]] = []
    for law in catalog.get("laws") or []:
        if not isinstance(law, dict):
            continue
        for vec in law.get("violation_vectors") or []:
            if vec in vectors:
                violations.append({
                    "law_id": str(law.get("id") or ""),
                    "citation": str(law.get("citation") or ""),
                    "vector": vec,
                })
    if (dpi.get("segment_block") or {}).get("reason"):
        violations.append({
            "law_id": "cfaa_access",
            "citation": "18 U.S.C. § 1030",
            "vector": str(dpi.get("segment_block", {}).get("reason")),
        })
    clean = len(violations) == 0
    return {
        "lane": "clean_legal",
        "ts": _now(),
        "violations": violations,
        "violation_count": len(violations),
        "laws_watching": len(catalog.get("laws") or []),
        "clean": clean,
    }


def lane_clean_sovereign(envelope: dict[str, Any]) -> dict[str, Any]:
    fabric = _fabric_mod()
    material = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    if fabric is None:
        return {"lane": "clean_sovereign", "ts": _now(), "seal": None, "clean": True}
    seal = fabric.seal_payload(material, arm_slots=4)
    return {
        "lane": "clean_sovereign",
        "ts": _now(),
        "fabric_seal": seal,
        "clean": True,
    }


def reconverge_packet(
    pkt: dict[str, Any],
    *,
    dirty: dict[str, Any],
    inspect_doc: dict[str, Any],
    strip_doc: dict[str, Any],
    gk: dict[str, Any],
    legal: dict[str, Any],
    sovereign: dict[str, Any],
) -> dict[str, Any]:
    secure = (
        gk.get("clean")
        and legal.get("clean")
        and sovereign.get("clean")
        and not inspect_doc.get("alert")
    )
    return {
        "lane": "reconverge",
        "ts": _now(),
        "secure": secure,
        "protected": secure,
        "lawful": legal.get("clean"),
        "envelope": strip_doc.get("envelope"),
        "gatekeeper": {"permit": gk.get("permit"), "verdict": gk.get("gatekeeper_verdict")},
        "legal": {"violations": legal.get("violation_count", 0)},
        "sovereign_seal": (sovereign.get("fabric_seal") or {}).get("seals"),
        "dirty_id": dirty.get("id"),
        "vectors": inspect_doc.get("vectors") or [],
        "english": pkt.get("english", "")[:160],
    }


def _process_one(pkt: dict[str, Any]) -> dict[str, Any]:
    dirty = lane_dirty_dump(pkt)
    inspect_doc = lane_inspect(pkt)
    strip_doc = lane_strip(pkt)
    gk = lane_clean_gatekeeper(pkt, inspect_doc)
    legal = lane_clean_legal(pkt, inspect_doc)
    sovereign = lane_clean_sovereign(strip_doc.get("envelope") or {})
    recon = reconverge_packet(
        pkt,
        dirty=dirty,
        inspect_doc=inspect_doc,
        strip_doc=strip_doc,
        gk=gk,
        legal=legal,
        sovereign=sovereign,
    )
    return {
        "dirty": dirty,
        "inspect": inspect_doc,
        "strip": strip_doc,
        "clean_gatekeeper": gk,
        "clean_legal": legal,
        "clean_sovereign": sovereign,
        "reconverge": recon,
    }


def deinterlace_batch(batch: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    batch = batch if batch is not None else _source_batch()
    catalog = _law_catalog()
    if not batch:
        return {
            "schema": "field-packet-deinterlace/v1",
            "updated": _now(),
            "processed": 0,
            "lanes": list(LANES),
            "motto": "Dirty dump · inspect · strip · clean×3 · reconverge secure",
            "connectivity_laws": {
                "count": len(catalog.get("laws") or []),
                "surfaces": catalog.get("surfaces") or [],
                "forbidden_actions": catalog.get("forbidden_actions") or [],
                "clean_path_requirements": catalog.get("clean_path_requirements") or [],
            },
        }

    results: list[dict[str, Any]] = []
    workers = max(2, min(LANE_WORKERS, len(batch)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_process_one, pkt): pkt for pkt in batch}
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"error": str(exc), "lane": "failed"})

    dirty_rows = [r["dirty"] for r in results if r.get("dirty")]
    clean_rows = [r["reconverge"] for r in results if r.get("reconverge") and r["reconverge"].get("secure")]
    quarantine_rows = [r["reconverge"] for r in results if r.get("reconverge") and not r["reconverge"].get("secure")]

    _append_ring(DIRTY_RING, dirty_rows)
    _append_ring(CLEAN_RING, clean_rows)

    secure_count = len(clean_rows)
    alert_count = sum(1 for r in results if (r.get("inspect") or {}).get("alert"))
    legal_hits = sum(int((r.get("clean_legal") or {}).get("violation_count") or 0) for r in results)

    manifest_body = {
        "schema": "packet-secure-manifest/v1",
        "updated": _now(),
        "batch_size": len(batch),
        "secure_packets": secure_count,
        "quarantined": len(quarantine_rows),
        "alerts": alert_count,
        "legal_violations": legal_hits,
        "clean_paths": ["strip", "clean_gatekeeper", "clean_legal", "clean_sovereign"],
        "dirty_isolated": True,
        "samples": clean_rows[-8:],
        "law_catalog": _law_catalog().get("motto"),
    }
    fabric = _fabric_mod()
    if fabric is not None:
        manifest_body["manifest_seal"] = fabric.seal_payload(
            json.dumps(manifest_body, sort_keys=True, separators=(",", ":")).encode(),
            arm_slots=4,
        )
    _save_atomic(MANIFEST, manifest_body)

    row = {
        "ts": _now(),
        "processed": len(batch),
        "secure": secure_count,
        "quarantined": len(quarantine_rows),
        "alerts": alert_count,
        "legal_hits": legal_hits,
    }
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass

    catalog = _law_catalog()
    return {
        "schema": "field-packet-deinterlace/v1",
        "updated": _now(),
        "motto": "IN → dirty dump + parallel inspect/strip + clean×3 → reconverge secure & lawful",
        "lanes": list(LANES),
        "lane_workers": workers,
        "processed": len(batch),
        "secure": secure_count,
        "quarantined": len(quarantine_rows),
        "alerts": alert_count,
        "legal_violations": legal_hits,
        "dirty_ring": str(DIRTY_RING),
        "clean_ring": str(CLEAN_RING),
        "manifest": str(MANIFEST),
        "connectivity_laws": {
            "count": len(catalog.get("laws") or []),
            "surfaces": catalog.get("surfaces") or [],
            "forbidden_actions": catalog.get("forbidden_actions") or [],
            "clean_path_requirements": catalog.get("clean_path_requirements") or [],
        },
        "law_samples": (catalog.get("laws") or [])[:6],
        "manifest_summary": {
            "secure_packets": secure_count,
            "sealed": bool(manifest_body.get("manifest_seal")),
        },
    }


def panel_json() -> dict[str, Any]:
    if PANEL.is_file():
        cached = _load(PANEL, {})
        if cached.get("schema"):
            return cached
    return build_panel()


def build_panel() -> dict[str, Any]:
    doc = deinterlace_batch()
    doc["cached"] = False
    _save_atomic(PANEL, doc)
    return doc


def laws_json() -> dict[str, Any]:
    return _law_catalog()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("cycle", "build", "deinterlace"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "laws":
        print(json.dumps(laws_json(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-packet-deinterlace.py [json|cycle|laws]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())