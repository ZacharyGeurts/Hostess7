#!/usr/bin/env python3
"""Live threat heuristics across the Field botnet mesh.

Record · update · distribute · redundant:
  - Ingest live threat signals (vector-destroy, dns-threat-guard, threat-vectors, dig, ss)
  - Maintain a rolling heuristic board with hit counts, weights, last_seen, severity
  - Fan out to security_guard + regional_relay + mesh twins (distributed means redundant)
  - Never ISC dig; Field dig / Ironclad only
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import socket
import struct
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-botnet-threat-heuristics-doctrine.json"
HEURISTICS = STATE / "field-botnet-threat-heuristics.json"
PANEL = STATE / "field-botnet-threat-heuristics-panel.json"
LEDGER = STATE / "field-botnet-threat-heuristics-ledger.jsonl"
MESH_DIR = STATE / "field-botnet-threat-heuristics-mesh"
IRONCLAD = "ironclad:field-botnet-threat-heuristics:1"

IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# Base weights (live updates adjust scores) — terrorist class maxed for kill path
BASE_WEIGHTS: dict[str, float] = {
    "impostor_ns": 12.0,
    "foreign_ns_resolv": 10.0,
    "dns_poison": 11.0,
    "ddos_flood": 9.0,
    "rate_limit": 6.0,
    "permanent_block": 8.0,
    "vector_destroy": 10.0,
    "egress_beacon": 7.0,
    "spawner": 9.0,
    "any_query": 5.0,
    "oversized_packet": 6.0,
    "gateway_shift": 8.0,
    "arp_spoof": 9.0,
    "lie_detected": 7.0,
    "delay_as_threat": 5.0,
    "url_hostile": 6.0,
    # GitHub planet plane — ours hold low; stale/foreign elevated
    "github_ours_surface": 0.5,
    "github_stale_surface": 5.5,
    "github_foreign_dns": 7.0,
    # Terrorist activity — never permit · full Field UDP cook · never reconnect
    "terrorist_attack": 18.0,
    "terrorist_never_reconnect": 16.0,
    "terrorist_permit_deny": 15.0,
    "c2_beacon": 14.0,
    "lateral_move": 13.0,
    "exfil_channel": 13.0,
    "hostile_recon": 11.0,
    # Newcomer appears + immediately attacks — lethal no-machine-again sphere path
    "NEWCOMER_IMMEDIATE_ATTACK": 17.0,
    "IMMEDIATE_ATTACK": 16.5,
    "STORM_PROPAGATE": 15.5,
    "FOREIGN_HOSTILE_DEVICE": 14.0,
    "unknown": 3.0,
}

# Kill thresholds (24h pass is aggressive)
KILL_SCORE_HOT = 12.0
KILL_SCORE_TERROR = 8.0
KILL_MAX_PER_CYCLE = 64
TERROR_VECTORS = frozenset({
    "terrorist_attack",
    "terrorist_never_reconnect",
    "terrorist_permit_deny",
    "impostor_ns",
    "dns_poison",
    "c2_beacon",
    "lateral_move",
    "exfil_channel",
    "vector_destroy",
    "permanent_block",
})

IMPOSTOR_NS = frozenset({
    "71.10.216.1", "71.10.216.2", "71.10.216.3",
    "208.67.222.222", "208.67.220.220",
})
FOREIGN_NS = frozenset({
    "8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1", "9.9.9.9",
    *IMPOSTOR_NS,
})
FIELD_TRUTH = frozenset({"127.0.0.1", "::1", "192.168.47.1", "192.168.50.1", "127.0.0.53"})


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
    except OSError:
        try:
            path.write_text(payload, encoding="utf-8")
        except OSError:
            pass


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _ledger(row: dict[str, Any]) -> None:
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _tail_lines(path: Path, n: int = 500) -> list[str]:
    if not path.is_file():
        return []
    try:
        # efficient-ish tail for moderate files
        data = path.read_text(encoding="utf-8", errors="replace")
        lines = data.splitlines()
        return lines[-n:] if len(lines) > n else lines
    except OSError:
        return []


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _mod(rel: str, name: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def ironclad_seal(payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return {
        "ironclad_cite": IRONCLAD,
        "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "sealed_at": _utc(),
    }


def _normalize_vector(raw: str) -> str:
    v = (raw or "unknown").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "DDOS_FLOOD": "ddos_flood",
        "DNS_POISON": "dns_poison",
        "RATE_LIMIT": "rate_limit",
        "RATE_LIMIT_DDOS": "rate_limit",
        "EGRESS_BEACON": "egress_beacon",
        "ARP_SPOOF": "arp_spoof",
        "GATEWAY_SHIFT": "gateway_shift",
        "LIE_DETECTED": "lie_detected",
        "DELAY_AS_THREAT": "delay_as_threat",
        "HOSTILE": "unknown",
        "MANUAL": "vector_destroy",
        "ANY_QUERY_REJECTED": "any_query",
        "OVERSIZED_PACKET": "oversized_packet",
        "PERMANENT_BLOCK": "permanent_block",
        "VECTOR_DESTROY": "vector_destroy",
        "IMPOSTOR_NS": "impostor_ns",
        "FOREIGN_NS": "foreign_ns_resolv",
        "SPAWNER": "spawner",
        "TERRORIST": "terrorist_attack",
        "TERRORIST_ATTACK": "terrorist_attack",
        "TERROR": "terrorist_attack",
        "NEVER_RECONNECT": "terrorist_never_reconnect",
        "TERRORIST_NEVER_RECONNECT": "terrorist_never_reconnect",
        "PERMIT_DENY": "terrorist_permit_deny",
        "C2": "c2_beacon",
        "C2_BEACON": "c2_beacon",
        "LATERAL": "lateral_move",
        "LATERAL_MOVE": "lateral_move",
        "EXFIL": "exfil_channel",
        "EXFIL_CHANNEL": "exfil_channel",
        "RECON": "hostile_recon",
        "HOSTILE_RECON": "hostile_recon",
    }
    if v.lower() in BASE_WEIGHTS:
        return v.lower()
    if v in aliases:
        return aliases[v]
    low = v.lower()
    for key in BASE_WEIGHTS:
        if key in low:
            return key
    return "unknown"


def _empty_board() -> dict[str, Any]:
    return {
        "schema": "field-botnet-threat-heuristics/v1",
        "updated": _utc(),
        "ironclad_cite": IRONCLAD,
        "live": True,
        "heuristics": {},  # key -> heuristic row
        "vectors": {},     # vector_id -> aggregate
        "sources": {},     # ip/source -> aggregate
        "mesh_fanout": {},
        "stats": {
            "records": 0,
            "updates": 0,
            "ingest_batches": 0,
            "last_ingest": None,
        },
        "weights": dict(BASE_WEIGHTS),
    }


def load_board() -> dict[str, Any]:
    doc = _load(HEURISTICS, None)
    if not isinstance(doc, dict) or not doc.get("heuristics"):
        return _empty_board()
    doc.setdefault("heuristics", {})
    doc.setdefault("vectors", {})
    doc.setdefault("sources", {})
    doc.setdefault("mesh_fanout", {})
    doc.setdefault("stats", {})
    doc.setdefault("weights", dict(BASE_WEIGHTS))
    # merge new base weights without clobbering learned
    for k, v in BASE_WEIGHTS.items():
        doc["weights"].setdefault(k, v)
    return doc


def _hkey(kind: str, subject: str) -> str:
    return f"{kind}:{subject}".lower()


def _severity_from_score(score: float) -> str:
    if score >= 40:
        return "critical"
    if score >= 24:
        return "high"
    if score >= 12:
        return "medium"
    if score >= 5:
        return "low"
    return "info"


def record_signal(
    board: dict[str, Any],
    *,
    vector: str,
    subject: str = "",
    detail: str = "",
    origin: str = "live",
    node_id: str | None = None,
    weight: float | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record one live threat signal and update heuristics in-place."""
    vid = _normalize_vector(vector)
    subject = (subject or "global").strip() or "global"
    # Impostor auto-class
    if subject in IMPOSTOR_NS:
        vid = "impostor_ns"
    elif subject in FOREIGN_NS and subject not in FIELD_TRUTH:
        if vid == "unknown":
            vid = "foreign_ns_resolv"

    w = float(weight if weight is not None else board.get("weights", {}).get(vid, BASE_WEIGHTS.get(vid, 3.0)))
    now = _utc()
    key = _hkey(vid, subject)

    row = board["heuristics"].get(key) or {
        "key": key,
        "vector": vid,
        "subject": subject,
        "hits": 0,
        "score": 0.0,
        "first_seen": now,
        "last_seen": now,
        "origins": {},
        "nodes": {},
        "details": [],
        "live": True,
    }
    row["hits"] = int(row.get("hits") or 0) + 1
    # EMA-ish score growth with diminishing returns
    prev = float(row.get("score") or 0.0)
    row["score"] = round(prev + w * (1.0 / (1.0 + prev * 0.05)), 3)
    row["last_seen"] = now
    row["severity"] = _severity_from_score(row["score"])
    origins = row.setdefault("origins", {})
    origins[origin] = int(origins.get(origin) or 0) + 1
    if node_id:
        nodes = row.setdefault("nodes", {})
        nodes[str(node_id)] = int(nodes.get(node_id) or 0) + 1
    details = row.setdefault("details", [])
    if detail:
        snippet = str(detail)[:160]
        if snippet not in details:
            details.append(snippet)
            row["details"] = details[-8:]
    if meta:
        row["meta"] = {**(row.get("meta") or {}), **{k: meta[k] for k in list(meta)[:8]}}
    row["weight_last"] = w
    row["updated"] = now
    board["heuristics"][key] = row

    # Vector aggregate
    vagg = board["vectors"].get(vid) or {
        "vector": vid,
        "hits": 0,
        "score": 0.0,
        "subjects": 0,
        "last_seen": now,
    }
    vagg["hits"] = int(vagg.get("hits") or 0) + 1
    vagg["score"] = round(float(vagg.get("score") or 0.0) + w * 0.25, 3)
    vagg["last_seen"] = now
    vagg["severity"] = _severity_from_score(vagg["score"])
    board["vectors"][vid] = vagg

    # Source aggregate
    if subject and subject != "global":
        sagg = board["sources"].get(subject) or {
            "subject": subject,
            "hits": 0,
            "score": 0.0,
            "vectors": {},
            "last_seen": now,
        }
        sagg["hits"] = int(sagg.get("hits") or 0) + 1
        sagg["score"] = round(float(sagg.get("score") or 0.0) + w * 0.5, 3)
        sagg["last_seen"] = now
        sagg["severity"] = _severity_from_score(sagg["score"])
        svecs = sagg.setdefault("vectors", {})
        svecs[vid] = int(svecs.get(vid) or 0) + 1
        if subject in IMPOSTOR_NS:
            sagg["class"] = "impostor_ns"
        elif subject in FOREIGN_NS:
            sagg["class"] = "foreign_ns"
        elif subject in FIELD_TRUTH:
            sagg["class"] = "field_truth"
        elif vid in TERROR_VECTORS or sagg.get("class") == "terrorist":
            sagg["class"] = "terrorist"
            sagg["terrorist"] = True
            sagg["never_reconnect"] = True
            sagg["kill"] = True
        else:
            sagg["class"] = sagg.get("class") or "peer"
        if vid in TERROR_VECTORS:
            sagg["terrorist"] = True
            sagg["never_reconnect"] = True
        board["sources"][subject] = sagg

    stats = board.setdefault("stats", {})
    stats["records"] = int(stats.get("records") or 0) + 1
    stats["updates"] = int(stats.get("updates") or 0) + 1
    stats["last_record"] = now
    board["updated"] = now
    board["live"] = True

    # Live weight adapt: hot vectors gain slight weight (capped)
    weights = board.setdefault("weights", dict(BASE_WEIGHTS))
    if vagg["hits"] >= 3:
        weights[vid] = round(min(20.0, float(weights.get(vid) or w) + 0.05), 3)

    return row


def _line_fp(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8", errors="replace")).hexdigest()[:16]


def _seen_set(board: dict[str, Any], name: str, cap: int = 4000) -> set[str]:
    cursors = board.setdefault("ingest_cursors", {})
    raw = cursors.get(name) or []
    return set(raw[-cap:])


def _mark_seen(board: dict[str, Any], name: str, fps: list[str], cap: int = 4000) -> None:
    cursors = board.setdefault("ingest_cursors", {})
    prev = list(cursors.get(name) or [])
    prev.extend(fps)
    cursors[name] = prev[-cap:]


def ingest_live_signals(board: dict[str, Any]) -> dict[str, int]:
    """Pull live signals from Field ledgers and update heuristics (deduped cursors)."""
    counts: Counter[str] = Counter()
    new_fps: dict[str, list[str]] = defaultdict(list)

    # 1) vector-destroy ledger
    seen = _seen_set(board, "vector_destroy")
    for line in _tail_lines(STATE / "field-vector-destroy-ledger.jsonl", 200):
        fp = _line_fp(line)
        if fp in seen:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        subj = str(row.get("root") or row.get("client") or row.get("remote") or "")
        record_signal(
            board,
            vector=str(row.get("vector") or "vector_destroy"),
            subject=subj,
            detail=str(row.get("reason") or row.get("event") or ""),
            origin="vector_destroy_ledger",
            meta={"event": row.get("event")},
        )
        counts["vector_destroy"] += 1
        new_fps["vector_destroy"].append(fp)

    # 2) dns-threat eradicated
    seen = _seen_set(board, "dns_threat")
    for line in _tail_lines(STATE / "dns-threat-eradicated.jsonl", 300):
        fp = _line_fp(line)
        if fp in seen:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        record_signal(
            board,
            vector=str(row.get("vector") or row.get("reason") or "permanent_block"),
            subject=str(row.get("client") or ""),
            detail=str(row.get("reason") or ""),
            origin="dns_threat_guard",
            meta={"direction": row.get("direction")},
        )
        counts["dns_threat"] += 1
        new_fps["dns_threat"].append(fp)

    # 3) permanent blocks snapshot (key by client+reason+ts)
    seen = _seen_set(board, "permanent_blocks")
    blocks = _load(STATE / "dns-threat-permanent-blocks.json", {})
    for b in (blocks.get("blocks") or [])[-100:]:
        if b.get("undone"):
            continue
        fp = _line_fp(json.dumps(b, sort_keys=True, ensure_ascii=False))
        if fp in seen:
            continue
        record_signal(
            board,
            vector=str(b.get("vector") or "permanent_block"),
            subject=str(b.get("client") or ""),
            detail=str(b.get("reason") or "permanent_block"),
            origin="permanent_blocks",
        )
        counts["permanent_blocks"] += 1
        new_fps["permanent_blocks"].append(fp)

    # 4) threat-vectors.tsv (tail, deduped)
    seen = _seen_set(board, "threat_vectors")
    for line in _tail_lines(STATE / "threat-vectors.tsv", 400):
        if not line.strip() or line.startswith("#"):
            continue
        fp = _line_fp(line)
        if fp in seen:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            parts = line.split()
        if len(parts) < 2:
            continue
        if len(parts) >= 4 and parts[0][:4].isdigit():
            vec, sev, detail = parts[1], parts[2], " ".join(parts[3:])
        else:
            vec, sev = parts[0], parts[1] if len(parts) > 1 else ""
            detail = " ".join(parts[2:]) if len(parts) > 2 else ""
        ips = IP_RE.findall(detail)
        subject = ips[0] if ips else "global"
        record_signal(
            board,
            vector=vec,
            subject=subject,
            detail=f"{sev} {detail}"[:160],
            origin="threat_vectors_tsv",
        )
        counts["threat_vectors"] += 1
        new_fps["threat_vectors"].append(fp)

    # 5) resolv foreign live — at most one touch per IP per hour via cursor
    seen = _seen_set(board, "resolv")
    try:
        text = Path("/etc/resolv.conf").read_text(encoding="utf-8", errors="replace")
        hour = _utc()[:13]
        for ip in IP_RE.findall(text):
            if ip in FOREIGN_NS and ip not in FIELD_TRUTH:
                fp = _line_fp(f"resolv:{ip}:{hour}")
                if fp in seen:
                    continue
                record_signal(
                    board,
                    vector="foreign_ns_resolv" if ip not in IMPOSTOR_NS else "impostor_ns",
                    subject=ip,
                    detail="live resolv.conf foreign",
                    origin="resolv_live",
                )
                counts["resolv"] += 1
                new_fps["resolv"].append(fp)
    except OSError:
        pass

    # 6) field-dns recent query log
    seen = _seen_set(board, "field_dns")
    for line in _tail_lines(STATE / "field-dns-queries.jsonl", 150):
        fp = _line_fp(line)
        if fp in seen:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("blocked") or row.get("rcode") in (2, 3, 5) or row.get("threat"):
            record_signal(
                board,
                vector=str(row.get("threat") or row.get("reason") or "dns_poison"),
                subject=str(row.get("client") or row.get("qname") or "global"),
                detail=str(row.get("qname") or row.get("detail") or "")[:120],
                origin="field_dns_queries",
            )
            counts["field_dns"] += 1
            new_fps["field_dns"].append(fp)

    # 7) url heuristics hostile plate (snapshot hash)
    seen = _seen_set(board, "url_heuristics")
    url_plate = _load(STATE / "field-url-heuristics-steel-plate.json", {})
    for h in (url_plate.get("heuristics") or url_plate.get("rules") or [])[:40]:
        if not isinstance(h, dict):
            continue
        if str(h.get("verdict") or h.get("class") or "").lower() in (
            "hostile", "kill", "block", "threat", "purge"
        ) or h.get("hostile"):
            fp = _line_fp(json.dumps(h, sort_keys=True, ensure_ascii=False)[:400])
            if fp in seen:
                continue
            record_signal(
                board,
                vector="url_hostile",
                subject=str(h.get("host") or h.get("pattern") or "url")[:80],
                detail=str(h.get("why") or h.get("reason") or "")[:120],
                origin="url_heuristics",
            )
            counts["url_heuristics"] += 1
            new_fps["url_heuristics"].append(fp)

    # 7b) GitHub planet data — stale / foreign surfaces into heuristics; ours stay ours
    seen = _seen_set(board, "github_planet")
    day = _utc()[:10]
    gh_idx = _load(STATE / "field-github-planet-index.json", {})
    gh_sweep = _load(STATE / "field-github-planet-sweep-panel.json", {})
    ours_owner = str(gh_idx.get("owner") or "ZacharyGeurts").lower()
    for repo in (gh_idx.get("repos") or [])[:80]:
        if not isinstance(repo, dict):
            continue
        slug = str(repo.get("slug") or repo.get("name") or "")
        if not slug:
            continue
        # Ours — stamp as owned surface (low weight informational, not kill)
        is_ours = slug.lower().startswith(ours_owner + "/") or str(repo.get("owner") or "").lower() == ours_owner
        if is_ours and not repo.get("stale"):
            fp = _line_fp(f"github_ours:{slug}:{day}")
            if fp not in seen:
                record_signal(
                    board,
                    vector="github_ours_surface",
                    subject=slug[:80],
                    detail=f"ours · {repo.get('pages_mode') or 'repo'} · hardened hold",
                    origin="github_planet_index",
                    weight=0.5,
                    meta={"ours": True, "pages": repo.get("pages_url"), "ingress": repo.get("ingress")},
                )
                counts["github_ours"] += 1
                new_fps["github_planet"].append(fp)
        if repo.get("stale") or repo.get("stale_kind"):
            fp = _line_fp(f"github_stale:{slug}:{repo.get('stale_kind')}:{day}")
            if fp not in seen:
                record_signal(
                    board,
                    vector="github_stale_surface",
                    subject=slug[:80],
                    detail=str(repo.get("stale_kind") or "stale")[:120],
                    origin="github_planet_index",
                    meta={"pages": repo.get("pages_url"), "redirect_to": repo.get("redirect_to")},
                )
                counts["github_stale"] += 1
                new_fps["github_planet"].append(fp)
    # Sweep panel stale list
    for row in (gh_sweep.get("stale_repos") or [])[:40]:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("slug") or row.get("name") or row.get("repo") or "")
        fp = _line_fp(f"github_stale_sweep:{slug}:{day}")
        if fp in seen:
            continue
        record_signal(
            board,
            vector="github_stale_surface",
            subject=slug[:80] or "github_stale",
            detail=str(row.get("stale_kind") or row.get("reason") or "sweep_stale")[:120],
            origin="github_planet_sweep",
        )
        counts["github_stale"] += 1
        new_fps["github_planet"].append(fp)
    # DNS index rows that are not ours owner → foreign github surface
    for row in (gh_idx.get("dns_index") or [])[:40]:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("host") or row.get("qname") or "")
        if not name:
            continue
        if ours_owner in name.lower() or "zacharygeurts" in name.lower() or "ammonet" in name.lower():
            continue
        fp = _line_fp(f"github_dns_foreign:{name}:{day}")
        if fp in seen:
            continue
        record_signal(
            board,
            vector="github_foreign_dns",
            subject=name[:80],
            detail="github planet dns index non-ours",
            origin="github_planet_dns",
        )
        counts["github_foreign_dns"] += 1
        new_fps["github_planet"].append(fp)

    # 8) host-attacks recent
    seen = _seen_set(board, "host_attacks")
    attacks = _load(STATE / "host-attacks.json", {})
    for pt in (attacks.get("points") or attacks.get("attacks") or [])[-50:]:
        if not isinstance(pt, dict):
            continue
        ip = str(pt.get("ip") or pt.get("host") or "")
        if not ip:
            continue
        fp = _line_fp(json.dumps({"ip": ip, "v": pt.get("vector"), "t": pt.get("ts") or pt.get("updated")}, sort_keys=True))
        if fp in seen:
            continue
        record_signal(
            board,
            vector=str(pt.get("vector") or pt.get("verdict") or "unknown"),
            subject=ip,
            detail=str(pt.get("label") or pt.get("detail") or "")[:120],
            origin="host_attacks",
            meta={"severity": pt.get("severity")},
        )
        counts["host_attacks"] += 1
        new_fps["host_attacks"].append(fp)

    # 9) terrorist never-reconnect table — every IP is kill-class
    seen = _seen_set(board, "terrorist_nr")
    day = _utc()[:10]
    terror = _load(STATE / "field-terrorist-never-reconnect.json", {})
    terror_ips = terror.get("ips") or {}
    if isinstance(terror_ips, list):
        terror_ips = {str(x): True for x in terror_ips}
    if isinstance(terror_ips, dict):
        # re-touch daily so 24h cycles re-score without flooding forever
        for ip, meta in list(terror_ips.items())[:2000]:
            ip = str(ip).split(":")[0].strip()
            if not IP_RE.match(ip) or ip in FIELD_TRUTH:
                continue
            fp = _line_fp(f"terror_nr:{ip}:{day}")
            if fp in seen:
                continue
            detail = ""
            if isinstance(meta, dict):
                detail = str(meta.get("reason") or meta.get("vector") or "never_reconnect")[:120]
            record_signal(
                board,
                vector="terrorist_never_reconnect",
                subject=ip,
                detail=detail or "terrorist never reconnect — kill",
                origin="terrorist_never_reconnect",
                weight=BASE_WEIGHTS["terrorist_never_reconnect"],
            )
            counts["terrorist_never_reconnect"] += 1
            new_fps["terrorist_nr"].append(fp)

    # 10) permanent ban registry subjects
    seen = _seen_set(board, "perm_ban_reg")
    ban_reg = _load(STATE / "field-permanent-ban-udp-destroy.json", {})
    for bid, b in list((ban_reg.get("bans") or {}).items())[:1500]:
        if not isinstance(b, dict):
            continue
        subj = str(b.get("subject") or b.get("ip") or "").split(":")[0]
        if not subj or subj in FIELD_TRUTH:
            continue
        fp = _line_fp(f"perm_ban:{subj}:{day}")
        if fp in seen:
            continue
        is_terror = bool(
            b.get("terrorist_attack")
            or b.get("never_reconnect_from_terrorist_attack")
            or "terror" in str(b.get("reason") or "").lower()
        )
        record_signal(
            board,
            vector="terrorist_attack" if is_terror else "permanent_block",
            subject=subj,
            detail=str(b.get("reason") or "permanent_ban")[:120],
            origin="permanent_ban_registry",
            weight=BASE_WEIGHTS["terrorist_attack"] if is_terror else None,
            meta={"kind": b.get("kind"), "terrorist": is_terror},
        )
        counts["permanent_ban"] += 1
        new_fps["perm_ban_reg"].append(fp)

    # 11) never-permit seal
    if (STATE / "field-terrorist-never-permit.forever").is_file():
        fp = _line_fp(f"never_permit:{day}")
        seen = _seen_set(board, "never_permit")
        if fp not in seen:
            record_signal(
                board,
                vector="terrorist_permit_deny",
                subject="global",
                detail="never permit terrorist activity on network",
                origin="terrorist_never_permit",
                weight=BASE_WEIGHTS["terrorist_permit_deny"],
            )
            counts["never_permit"] += 1
            new_fps["never_permit"].append(fp)

    for name, fps in new_fps.items():
        _mark_seen(board, name, fps)

    board.setdefault("stats", {})["ingest_batches"] = int(board["stats"].get("ingest_batches") or 0) + 1
    board["stats"]["last_ingest"] = _utc()
    board["stats"]["last_ingest_counts"] = dict(counts)
    board["stats"]["last_ingest_new"] = sum(counts.values())
    return dict(counts)


def _mesh_nodes() -> list[dict[str, Any]]:
    """Botnet mesh nodes from dns-dhcp panel + registry members."""
    nodes: list[dict[str, Any]] = []
    panel = _load(STATE / "field-botnet-dns-dhcp-panel.json", {})
    bn = panel.get("bot_network") or {}
    for n in bn.get("nodes") or []:
        if isinstance(n, dict) and n.get("id"):
            nodes.append(n)
    # registry members as mesh endpoints
    reg = _load(STATE / "field-botnet-registry.json", {})
    for m in reg.get("members") or []:
        mid = m.get("member_id")
        if not mid:
            continue
        nodes.append({
            "id": f"member:{mid}",
            "kind": "registry_member",
            "plane": m.get("region") or "member",
            "distributed": True,
            "redundant": True,
            "member_id": mid,
        })
    return nodes


def fanout_to_mesh(board: dict[str, Any], *, max_nodes: int | None = None) -> dict[str, Any]:
    """Distribute live heuristics across botnet mesh (redundant on guards/relays)."""
    doc = _doctrine()
    policy = doc.get("mesh_fanout") or {}
    max_nodes = max_nodes or int(policy.get("max_nodes") or os.environ.get("NEXUS_THREAT_HEUR_MESH_MAX", "64"))
    prefer_kinds = list(policy.get("prefer_kinds") or [
        "security_guard", "regional_relay", "sovereign", "registry_member", "qemu_world",
    ])

    nodes = _mesh_nodes()
    # Prefer security plane first
    ranked: list[dict[str, Any]] = []
    for kind in prefer_kinds:
        ranked.extend([n for n in nodes if n.get("kind") == kind])
    # fill remainder
    seen = {n.get("id") for n in ranked}
    for n in nodes:
        if n.get("id") not in seen:
            ranked.append(n)
            seen.add(n.get("id"))

    # Top live heuristics payload (compact)
    top = sorted(
        (board.get("heuristics") or {}).values(),
        key=lambda r: float(r.get("score") or 0),
        reverse=True,
    )[:80]
    top_vectors = sorted(
        (board.get("vectors") or {}).values(),
        key=lambda r: float(r.get("score") or 0),
        reverse=True,
    )[:24]
    top_sources = sorted(
        (board.get("sources") or {}).values(),
        key=lambda r: float(r.get("score") or 0),
        reverse=True,
    )[:40]

    payload_base = {
        "schema": "field-botnet-threat-heuristics-shard/v1",
        "updated": _utc(),
        "ironclad_cite": IRONCLAD,
        "live": True,
        "weights": board.get("weights") or BASE_WEIGHTS,
        "top_heuristics": top,
        "top_vectors": top_vectors,
        "top_sources": top_sources,
        "stats": board.get("stats") or {},
        "policy": {
            "record_live": True,
            "update_live": True,
            "across_botnet": True,
            "distributed_means_redundant": True,
        },
    }

    MESH_DIR.mkdir(parents=True, exist_ok=True)
    fanout: dict[str, Any] = {
        "updated": _utc(),
        "node_count_available": len(nodes),
        "shards_written": 0,
        "by_kind": Counter(),
        "nodes": [],
    }

    # Always write queen/sovereign aggregate
    queen_path = MESH_DIR / "node_field-loopback.json"
    queen = {
        **payload_base,
        "node_id": "field-loopback",
        "kind": "sovereign",
        "role": "mesh_queen_heuristic_board",
        "redundant": True,
        "distributed": True,
    }
    queen["ironclad"] = ironclad_seal({"node": "field-loopback", "n": len(top)})
    _save(queen_path, queen)
    fanout["shards_written"] += 1
    fanout["by_kind"]["sovereign"] += 1

    written = 0
    for n in ranked:
        if written >= max_nodes:
            break
        nid = str(n.get("id") or f"node-{written}")
        if nid == "field-loopback":
            continue
        kind = str(n.get("kind") or "node")
        # qemu_world: sample only every Nth for density without storm
        if kind == "qemu_world":
            # keep first 8 + every 64th
            idx = written
            if idx >= 8 and (hash(nid) % 64) != 0:
                continue
        shard = {
            **payload_base,
            "node_id": nid,
            "kind": kind,
            "plane": n.get("plane"),
            "roles": n.get("roles") or [],
            "distributed": bool(n.get("distributed", True)),
            "redundant": bool(n.get("redundant", True)),
            "role": "mesh_threat_heuristic_shard",
            "dns_upstream": n.get("dns_upstream"),
        }
        # Per-node partial view: tag hits that already saw this node
        local_hits = [
            h for h in top
            if nid in (h.get("nodes") or {})
        ][:20]
        shard["local_hits"] = local_hits
        shard["ironclad"] = ironclad_seal({"node": nid, "kind": kind, "hits": len(local_hits)})
        safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", nid)[:80]
        _save(MESH_DIR / f"node_{safe_name}.json", shard)
        fanout["shards_written"] += 1
        fanout["by_kind"][kind] += 1
        fanout["nodes"].append({"id": nid, "kind": kind, "plane": n.get("plane")})
        written += 1

    # Twin redundancy: duplicate top board to security_guard nodes explicitly
    guards = [n for n in nodes if n.get("kind") == "security_guard"]
    for g in guards[:16]:
        gid = str(g.get("id"))
        twin = {
            **payload_base,
            "node_id": gid,
            "kind": "security_guard",
            "role": "redundant_threat_heuristic_mirror",
            "redundant": True,
            "distributed": True,
            "mirror_of": "field-loopback",
        }
        twin["ironclad"] = ironclad_seal({"node": gid, "mirror": True})
        safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", gid)[:80]
        _save(MESH_DIR / f"guard_{safe}.json", twin)
        fanout["shards_written"] += 1
        fanout["by_kind"]["security_guard_mirror"] += 1

    fanout["by_kind"] = dict(fanout["by_kind"])
    fanout["mesh_dir"] = str(MESH_DIR)
    fanout["redundant"] = True
    fanout["distributed"] = True
    board["mesh_fanout"] = fanout
    return fanout


def _protected_ips() -> set[str]:
    """Never kill self / Field truth / operator WAN."""
    out = set(FIELD_TRUTH)
    for env_k in ("NEXUS_PROTECTED_IP", "NEXUS_SELF_WAN", "NEXUS_FIELD_WAN"):
        v = os.environ.get(env_k, "").strip()
        if v:
            out.add(v.split("/")[0])
    # common local LAN Field binds
    out.update({"0.0.0.0", "255.255.255.255", "127.0.0.1", "::1"})
    try:
        import subprocess as _sp
        proc = _sp.run(
            ["hostname", "-I"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        for tok in (proc.stdout or "").split():
            if IP_RE.match(tok):
                out.add(tok)
    except Exception:
        pass
    # hard-code known WAN if present on this Field host
    out.add("97.95.64.87")
    return out


def apply_actions(board: dict[str, Any], *, kill_terror: bool = False) -> dict[str, Any]:
    """Vector-destroy hot sources + optional full terrorist kill path."""
    if os.environ.get("NEXUS_THREAT_HEUR_AUTO_DESTROY", "1").strip().lower() in ("0", "false", "no", "off"):
        if not kill_terror:
            return {"skipped": True, "reason": "auto_destroy_off"}
    protected = _protected_ips()
    sources = list((board.get("sources") or {}).values())
    # Terrorists first, then hot score
    def _rank(r: dict[str, Any]) -> tuple:
        terror = 1 if (
            r.get("terrorist")
            or r.get("class") in ("terrorist", "impostor_ns", "foreign_ns")
            or any(v in TERROR_VECTORS for v in (r.get("vectors") or {}))
        ) else 0
        return (terror, float(r.get("score") or 0))

    hot = sorted(sources, key=_rank, reverse=True)[:KILL_MAX_PER_CYCLE]
    vd = _mod("lib/field-vector-destroy.py", "field_vector_destroy_heur")
    results: list[dict[str, Any]] = []
    killed_ips: list[str] = []
    if not vd or not hasattr(vd, "vector_and_destroy"):
        return {"ok": False, "error": "vector_destroy_missing", "hot": len(hot)}

    for src in hot:
        ip = str(src.get("subject") or "").split(":")[0]
        if not ip or ip == "global" or not IP_RE.match(ip):
            continue
        if ip in protected or src.get("class") == "field_truth":
            continue
        score = float(src.get("score") or 0)
        is_terror = bool(
            src.get("terrorist")
            or src.get("class") in ("terrorist", "impostor_ns")
            or kill_terror
            and any(v in TERROR_VECTORS for v in (src.get("vectors") or {}))
        )
        thresh = KILL_SCORE_TERROR if is_terror else KILL_SCORE_HOT
        if score < thresh and not (is_terror and kill_terror):
            continue
        if is_terror and kill_terror and score < KILL_SCORE_TERROR:
            # still kill known terrorist class even if score cooled
            if not (src.get("terrorist") or src.get("class") == "terrorist"):
                continue
        reason = (
            "terrorist_activity_24h_kill"
            if is_terror
            else "botnet_threat_heuristic_hot"
        )
        try:
            r = vd.vector_and_destroy(
                client=ip,
                remote=ip,
                reason=reason,
                vector="TERRORIST_ATTACK" if is_terror else "VECTOR_DESTROY",
                detail=(
                    f"24h heuristic kill score={score} hits={src.get('hits')} "
                    f"class={src.get('class')} terrorist={is_terror}"
                ),
                observed={
                    "class": src.get("class"),
                    "vectors": src.get("vectors"),
                    "terrorist": is_terror,
                    "never_reconnect": True if is_terror else src.get("never_reconnect"),
                },
            )
            results.append({
                "ip": ip,
                "ok": bool(r.get("ok")),
                "sources_destroyed": r.get("sources_destroyed"),
                "score": score,
                "terrorist": is_terror,
                "reason": reason,
            })
            if r.get("ok"):
                killed_ips.append(ip)
            record_signal(
                board,
                vector="terrorist_attack" if is_terror else "vector_destroy",
                subject=ip,
                detail="auto kill from live heuristics 24h pass",
                origin="heuristics_terror_kill" if is_terror else "heuristics_auto_destroy",
                node_id="field-loopback",
            )
        except Exception as exc:
            results.append({"ip": ip, "ok": False, "error": str(exc)[:80], "terrorist": is_terror})

    # Permanent ban harvest + destroy pulse for terrorist never-reconnect plane
    ban_out: dict[str, Any] = {}
    if kill_terror or killed_ips:
        ban = _mod("lib/field-permanent-ban-udp-destroy.py", "field_perm_ban_heur")
        if ban:
            try:
                if hasattr(ban, "enforce"):
                    ban_out = ban.enforce(write=True, pulse=True)
                elif hasattr(ban, "destroy_pulse"):
                    reg = ban.load_registry() if hasattr(ban, "load_registry") else {}
                    if hasattr(ban, "harvest_existing_bans"):
                        ban.harvest_existing_bans(reg)
                    ban_out = ban.destroy_pulse(reg, force=True)
                    if hasattr(ban, "_save") and reg:
                        ban._save(ban.REGISTRY, reg)  # type: ignore[attr-defined]
            except Exception as exc:
                ban_out = {"ok": False, "error": str(exc)[:120]}

    # Stamp never-reconnect for killed terrorist IPs
    nr_path = STATE / "field-terrorist-never-reconnect.json"
    nr = _load(nr_path, {})
    if not isinstance(nr, dict):
        nr = {}
    ips = nr.get("ips") if isinstance(nr.get("ips"), dict) else {}
    if not isinstance(ips, dict):
        ips = {str(x): {"reason": "legacy"} for x in (nr.get("ips") or [])}
    now = _utc()
    for ip in killed_ips:
        ips[ip] = {
            "ip": ip,
            "reason": "heuristics_24h_terror_kill",
            "never_reconnect": True,
            "full_field_udp_cook": True,
            "updated": now,
            "ironclad_cite": IRONCLAD,
        }
    nr.update({
        "schema": "field-terrorist-never-reconnect/v1",
        "updated": now,
        "never_reconnect": True,
        "no_device_ever_reconnects_from_terrorist_attacks": True,
        "no_light_bans": True,
        "full_field_udp_cook": True,
        "perma_15_day_field_udp_cook": True,
        "dhcp_refuse": True,
        "dns_refuse": True,
        "ips": ips,
        "ip_count": len(ips),
        "ironclad_cite": "ironclad:terrorist-never-reconnect:1",
        "motto": "No device ever reconnects from terrorist attacks.",
    })
    try:
        _save(nr_path, nr)
    except OSError:
        pass

    return {
        "ok": True,
        "destroyed": results,
        "count": len(results),
        "killed_ok": sum(1 for r in results if r.get("ok")),
        "terrorist_kills": sum(1 for r in results if r.get("terrorist") and r.get("ok")),
        "permanent_ban": {
            "ok": ban_out.get("ok"),
            "counts": ban_out.get("counts") if isinstance(ban_out.get("counts"), dict) else None,
            "pulse": ban_out.get("pulse") if isinstance(ban_out.get("pulse"), dict) else (
                {"mode": ban_out.get("mode"), "destroyed": ban_out.get("destroyed")}
                if ban_out else None
            ),
        },
        "never_reconnect_ips": len(ips),
        "kill_terror": kill_terror,
        "protected_skipped": sorted(protected)[:12],
    }


def update_live(
    *,
    write: bool = True,
    fanout: bool = True,
    auto_destroy: bool = False,
    kill_terror: bool = False,
) -> dict[str, Any]:
    """Main path: record + update live heuristics across botnet; optional 24h terror kill."""
    board = load_board()
    ingest_counts = ingest_live_signals(board)

    # Recompute vector subject counts
    for vid, vagg in (board.get("vectors") or {}).items():
        vagg["subjects"] = sum(
            1 for h in (board.get("heuristics") or {}).values() if h.get("vector") == vid
        )

    mesh = fanout_to_mesh(board) if fanout else board.get("mesh_fanout") or {}
    destroy_result: dict[str, Any] = {}
    if auto_destroy or kill_terror:
        destroy_result = apply_actions(board, kill_terror=kill_terror or auto_destroy)

    board["updated"] = _utc()
    board["ironclad"] = ironclad_seal({
        "records": (board.get("stats") or {}).get("records"),
        "heuristics": len(board.get("heuristics") or {}),
        "shards": (mesh or {}).get("shards_written"),
        "terror_kill": bool(kill_terror),
    })
    if kill_terror:
        board.setdefault("stats", {})["last_24h_terror_kill"] = _utc()
        board["stats"]["terror_kill_cycles"] = int(board["stats"].get("terror_kill_cycles") or 0) + 1

    if write:
        # Cap stored heuristics to keep board lean
        if len(board.get("heuristics") or {}) > 2000:
            top_keys = [
                r["key"]
                for r in sorted(
                    board["heuristics"].values(),
                    key=lambda x: float(x.get("score") or 0),
                    reverse=True,
                )[:1500]
            ]
            board["heuristics"] = {k: board["heuristics"][k] for k in top_keys if k in board["heuristics"]}
        _save(HEURISTICS, board)

    top_h = sorted(
        (board.get("heuristics") or {}).values(),
        key=lambda r: float(r.get("score") or 0),
        reverse=True,
    )[:20]
    top_v = sorted(
        (board.get("vectors") or {}).values(),
        key=lambda r: float(r.get("score") or 0),
        reverse=True,
    )[:12]
    top_s = sorted(
        (board.get("sources") or {}).values(),
        key=lambda r: float(r.get("score") or 0),
        reverse=True,
    )[:12]
    terror_sources = sum(
        1 for s in (board.get("sources") or {}).values()
        if isinstance(s, dict) and (
            s.get("terrorist") or s.get("class") in ("terrorist", "impostor_ns")
        )
    )

    killed_ok = int(destroy_result.get("killed_ok") or 0) if destroy_result else 0
    motto = (
        f"24h terror kill · heuristics live · "
        f"{len(board.get('heuristics') or {})} signals · "
        f"{terror_sources} terrorist-class sources · "
        f"killed {killed_ok} · never reconnect · no light bans"
        if kill_terror
        else "Record and update live heuristics across the botnet of threat"
    )

    panel = {
        "schema": "field-botnet-threat-heuristics-panel/v2",
        "updated": _utc(),
        "ok": True,
        "live": True,
        "motto": motto,
        "ironclad_cite": IRONCLAD,
        "api": "/api/field-botnet-threat-heuristics",
        "stats": board.get("stats"),
        "ingest": ingest_counts,
        "counts": {
            "heuristics": len(board.get("heuristics") or {}),
            "vectors": len(board.get("vectors") or {}),
            "sources": len(board.get("sources") or {}),
            "terrorist_class_sources": terror_sources,
            "mesh_shards": (mesh or {}).get("shards_written"),
            "mesh_nodes_available": (mesh or {}).get("node_count_available"),
            "killed_ok": killed_ok,
            "terrorist_kills": destroy_result.get("terrorist_kills") if destroy_result else 0,
        },
        "top_heuristics": top_h,
        "top_vectors": top_v,
        "top_sources": top_s,
        "weights": board.get("weights"),
        "mesh_fanout": {
            "shards_written": (mesh or {}).get("shards_written"),
            "by_kind": (mesh or {}).get("by_kind"),
            "mesh_dir": (mesh or {}).get("mesh_dir"),
            "redundant": True,
            "distributed": True,
        },
        "auto_destroy": destroy_result,
        "kill_terror": kill_terror,
        "policy": {
            "record_live": True,
            "update_live": True,
            "across_botnet": True,
            "distributed_means_redundant": True,
            "uses_field_dig": True,
            "no_isc_dig": True,
            "vector_to_source_and_destroy": True,
            "kill_terrorist_activity": True,
            "never_reconnect_terrorists": True,
            "no_light_bans": True,
            "full_field_udp_cook": True,
            "never_permit_terrorists": True,
            "never_destroy_field_truth": True,
            "cycle_24h": True,
        },
    }
    if write:
        _save(PANEL, panel)
        api = INSTALL / "Hostess7" / "docs" / "api"
        if api.is_dir():
            _save(
                api / "field-botnet-threat-heuristics.json",
                {
                    "ok": True,
                    "schema": panel["schema"],
                    "updated": panel["updated"],
                    "motto": panel["motto"],
                    "live": True,
                    "counts": panel["counts"],
                    "top_vectors": top_v[:6],
                    "top_sources": top_s[:6],
                    "ironclad_cite": IRONCLAD,
                },
            )
    _ledger({
        "event": "update_live",
        "ingest": ingest_counts,
        "heuristics": panel["counts"]["heuristics"],
        "shards": panel["counts"]["mesh_shards"],
        "cite": IRONCLAD,
    })
    return panel


def record_external(
    *,
    vector: str,
    subject: str = "",
    detail: str = "",
    origin: str = "external",
    node_id: str | None = None,
    fanout: bool = False,
) -> dict[str, Any]:
    """API for other modules (vector-destroy, threat-guard, field-dig) to push live signals."""
    board = load_board()
    row = record_signal(
        board,
        vector=vector,
        subject=subject,
        detail=detail,
        origin=origin,
        node_id=node_id or "field-loopback",
    )
    if fanout:
        fanout_to_mesh(board)
    _save(HEURISTICS, board)
    _ledger({
        "event": "record_external",
        "vector": row.get("vector"),
        "subject": row.get("subject"),
        "score": row.get("score"),
        "origin": origin,
        "cite": IRONCLAD,
    })
    return {"ok": True, "heuristic": row, "updated": board.get("updated")}


def build_panel() -> dict[str, Any]:
    if PANEL.is_file():
        doc = _load(PANEL, {})
        if doc.get("schema"):
            return doc
    return update_live(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "update").strip().lower()
    if cmd in ("update", "live", "run", "json", "panel", "scan", "kill", "terror", "24h", "daily"):
        auto = os.environ.get("NEXUS_THREAT_HEUR_AUTO_DESTROY", "0").strip().lower() in ("1", "true", "yes", "on")
        kill = cmd in ("kill", "terror", "24h", "daily", "scan")
        if cmd == "scan":
            auto = True
        if kill:
            auto = True
            os.environ.setdefault("NEXUS_THREAT_HEUR_AUTO_DESTROY", "1")
        print(json.dumps(
            update_live(write=True, fanout=True, auto_destroy=auto, kill_terror=kill),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("record",):
        vector = sys.argv[2] if len(sys.argv) > 2 else "HOSTILE"
        subject = sys.argv[3] if len(sys.argv) > 3 else ""
        detail = " ".join(sys.argv[4:]) if len(sys.argv) > 4 else ""
        print(json.dumps(
            record_external(vector=vector, subject=subject, detail=detail, origin="cli", fanout=True),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("board", "heuristics"):
        print(json.dumps(load_board(), ensure_ascii=False, indent=2)[:50000])
        return 0
    if cmd in ("top",):
        b = load_board()
        top = sorted(b.get("heuristics", {}).values(), key=lambda r: float(r.get("score") or 0), reverse=True)[:30]
        print(json.dumps({"top": top, "updated": b.get("updated")}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": (
            "field-botnet-threat-heuristics.py "
            "[update|scan|kill|24h|terror|record VECTOR SUBJECT DETAIL|board|top|panel]"
        ),
        "motto": "Update heuristics · kill terrorist activity on the network · never reconnect",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
