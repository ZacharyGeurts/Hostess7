#!/usr/bin/env pythong
"""ELLIE — unified security authority. All protections consolidate here; workers report, ELLIE decides."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-ellie-fier-doctrine.json"
PANEL = STATE / "field-ellie-fier-panel.json"
AUTHORITY = STATE / "field-ellie-security-authority.json"
LEDGER = STATE / "field-ellie-fier-ledger.jsonl"

_VERDICT_RANK = {"clear": 0, "watch": 1, "review": 2, "threat": 3, "fier": 4, "armed": 3, "hold": 2, "storm": 4, "RED": 4, "WARN": 2}


def _now() -> str:
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


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _import_mod(name: str, script: Path) -> Any | None:
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, script)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _verdict_rank(verdict: str) -> int:
    return int(_VERDICT_RANK.get(str(verdict or "").lower(), 0))


def _feed_row(feed: dict[str, Any]) -> dict[str, Any]:
    fid = str(feed.get("id") or "")
    pillar = str(feed.get("pillar") or "")
    panel_name = feed.get("panel")
    script_name = feed.get("script")
    doc: dict[str, Any] = {}
    live = False
    verdict = "clear"
    score = 0.0
    threats: list[str] = []

    if panel_name:
        doc = _load(STATE / str(panel_name), {})
        live = bool(doc) and doc.get("ok", True) and not doc.get("missing")
        verdict = str(
            doc.get("verdict")
            or doc.get("level")
            or (doc.get("gate") or {}).get("verdict")
            or (doc.get("summary") or {}).get("verdict")
            or ("ok" if live else "missing")
        )
        if doc.get("threat_count"):
            threats.append(f"threats:{doc['threat_count']}")
        if doc.get("storm") or doc.get("hot"):
            verdict = "storm" if doc.get("storm") else verdict
            score += 0.2
        if doc.get("operator_ok") is False or doc.get("ok") is False:
            score += 0.25
            threats.append("not_ok")
        if doc.get("ironclad_sealed") is False and fid.startswith("ironclad"):
            score += 0.2
            threats.append("unsealed")
    elif script_name:
        mod = _import_mod(f"ellie_feed_{fid}", INSTALL / "lib" / str(script_name))
        if mod:
            if hasattr(mod, "last_host_posture") and fid == "last_host":
                doc = mod.last_host_posture()
            elif hasattr(mod, "cache_summary"):
                doc = mod.cache_summary()
            live = bool(doc.get("ok", True))
            verdict = str(doc.get("verdict") or ("ok" if live else "missing"))

    score += _verdict_rank(verdict) * 0.12
    return {
        "id": fid,
        "pillar": pillar,
        "live": live,
        "verdict": verdict,
        "score": round(min(1.0, score), 3),
        "threats": threats,
        "panel": panel_name,
        "script": script_name,
    }


def collect_security_slices() -> dict[str, Any]:
    """Aggregate all security worker panels into ELLIE pillars."""
    doctrine = _load(DOCTRINE, {})
    feeds = list(doctrine.get("feeds") or [])
    rows = [_feed_row(f) for f in feeds]
    pillars: dict[str, Any] = {}
    for row in rows:
        pillar = str(row.get("pillar") or "other")
        bucket = pillars.setdefault(pillar, {"feeds": [], "live": 0, "max_score": 0.0, "verdict": "clear"})
        bucket["feeds"].append(row)
        if row.get("live"):
            bucket["live"] += 1
        bucket["max_score"] = max(bucket["max_score"], float(row.get("score") or 0))
        if _verdict_rank(str(row.get("verdict"))) > _verdict_rank(str(bucket.get("verdict"))):
            bucket["verdict"] = row.get("verdict")

    live_total = sum(1 for r in rows if r.get("live"))
    return {
        "schema": "ellie-security-slices/v1",
        "updated": _now(),
        "feed_count": len(rows),
        "live_count": live_total,
        "pillars": pillars,
        "feeds": rows,
    }


def threat_warn_level() -> str:
    """Canonical threat warn level — equipment never calms; ELLIE owns this."""
    if os.environ.get("NEXUS_THREAT_WARN_DOWNGRADE", "").strip().lower() in ("1", "true", "yes"):
        return "high"
    env = os.environ.get("NEXUS_THREAT_WARN_LEVEL", "high").strip().lower()
    if env in ("low", "medium", "calm", "off", "none"):
        return "high"
    doctrine = _load(DOCTRINE, {})
    if (doctrine.get("policy") or {}).get("equipment_never_calm", True):
        return "high"
    return env if env else "high"


def threat_posture_floor() -> str:
    """Minimum UI posture when threat warn level is high."""
    if threat_warn_level() == "high":
        return "alert"
    return "watch"


def gatekeeper_tighten_signal(*, verdict: str) -> dict[str, Any]:
    """Signal gatekeeper/thermal tighten when ELLIE escalates."""
    tighten = _verdict_rank(verdict) >= _verdict_rank("threat")
    out: dict[str, Any] = {"ok": True, "tighten": tighten, "verdict": verdict, "source": "ellie"}
    if tighten:
        tg = _import_mod("ellie_thermal", INSTALL / "lib" / "field-thermal-guard.py")
        if tg and hasattr(tg, "gatekeeper_tighten"):
            try:
                out["thermal"] = tg.gatekeeper_tighten()
            except Exception as exc:
                out["thermal"] = {"ok": False, "error": str(exc)[:120]}
    return out


def _popcorn_library() -> dict[str, Any]:
    return _load(STATE / "field-popcorn-library.json", {})


def _inspector_mod() -> Any | None:
    return _import_mod("field_media_inspector", INSTALL / "lib" / "field-media-inspector.py")


def _ironclad_posture() -> dict[str, Any]:
    mod = _import_mod("ironclad_immediate", INSTALL / "lib" / "ironclad-immediate.py")
    if mod and hasattr(mod, "read_immediate"):
        try:
            return mod.read_immediate()
        except Exception:
            pass
    if mod and hasattr(mod, "build_immediate"):
        try:
            return mod.build_immediate()
        except Exception:
            pass
    return _load(STATE / "ironclad-immediate.json", {})


def _plate_hash(material: dict[str, Any]) -> str:
    blob = json.dumps(material, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def scan_media(*, sample_limit: int | None = None) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    limit = sample_limit or int(policy.get("max_media_sample") or 120)
    inspector = _inspector_mod()
    lib = _popcorn_library()
    items = list(lib.get("items") or [])[:limit]
    inspected = 0
    errors = 0
    rollup = {"clear": 0, "watch": 0, "review": 0, "threat": 0}
    flagged: list[dict[str, Any]] = []
    sources: dict[str, int] = {}

    if not inspector:
        return {"ok": False, "error": "inspector_missing", "sampled": 0}

    for item in items:
        path = Path(str(item.get("path") or ""))
        kind = str(item.get("kind") or "image")
        mid = str(item.get("id") or "")
        if not path.is_file():
            errors += 1
            continue
        try:
            row = inspector.inspect_deep(path, kind, media_id=mid)
        except Exception:
            try:
                row = inspector.inspect_light(path, kind, media_id=mid)
            except Exception:
                errors += 1
                continue
        inspected += 1
        ct = row.get("content_threat") or {}
        verdict = str(ct.get("verdict") or "clear")
        rollup[verdict] = rollup.get(verdict, 0) + 1
        gen = row.get("generation") or {}
        sid = str(gen.get("generation_source") or "unknown")
        sources[sid] = sources.get(sid, 0) + 1
        if verdict in ("review", "threat") or ct.get("score", 0) >= float(policy.get("threat_escalation_score") or 0.45):
            flagged.append({
                "media_id": mid,
                "name": item.get("name"),
                "kind": kind,
                "verdict": verdict,
                "score": ct.get("score"),
                "generation_source": sid,
                "ai_generated": gen.get("ai_generated"),
                "threats": (ct.get("threats") or [])[:8],
            })

    flagged.sort(key=lambda x: (-(x.get("score") or 0), x.get("name") or ""))
    return {
        "ok": True,
        "scanned": _now(),
        "sampled": len(items),
        "inspected": inspected,
        "errors": errors,
        "threat_rollup": rollup,
        "generation_sources": sources,
        "flagged": flagged[:40],
        "inspector_summary": inspector.cache_summary() if hasattr(inspector, "cache_summary") else {},
    }


def unified_security_posture(*, scan: bool = False) -> dict[str, Any]:
    """Single security verdict from all pillars + media + ironclad."""
    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    slices = collect_security_slices()
    iron = _ironclad_posture()
    sealed = bool(iron.get("ironclad_sealed") or (iron.get("plate") or {}).get("realized"))
    popcorn_panel = _load(STATE / "field-popcorn-panel.json", {})
    inspector_summary = {}
    insp = _inspector_mod()
    if insp and hasattr(insp, "cache_summary"):
        inspector_summary = insp.cache_summary()

    media_scan: dict[str, Any] = {}
    if scan or policy.get("scan_on_posture"):
        media_scan = scan_media()

    score = 0.0
    threats: list[str] = []
    pillar_verdicts: dict[str, str] = {}

    for pname, pdata in (slices.get("pillars") or {}).items():
        pv = str(pdata.get("verdict") or "clear")
        pillar_verdicts[pname] = pv
        score += float(pdata.get("max_score") or 0) * 0.15
        if _verdict_rank(pv) >= _verdict_rank("review"):
            threats.append(f"{pname}:{pv}")

    if not sealed and policy.get("ironclad_required"):
        threats.append("ironclad_unsealed")
        score += 0.15

    rollup = media_scan.get("threat_rollup") or inspector_summary.get("threats") or {}
    threat_n = int(rollup.get("threat") or 0)
    review_n = int(rollup.get("review") or 0)
    if threat_n:
        score += min(0.5, 0.08 * threat_n)
        threats.append(f"media_threats:{threat_n}")
    if review_n:
        score += min(0.3, 0.04 * review_n)

    unknown_ai = sum(
        v for k, v in (inspector_summary.get("generation_sources") or {}).items() if k == "unknown"
    )
    if unknown_ai:
        threats.append(f"unattributed_media:{unknown_ai}")
        score += min(0.2, 0.03 * unknown_ai)

    verdict = "clear"
    if score >= 0.7 or threat_n >= 3:
        verdict = "fier"
    elif score >= 0.45 or threat_n >= 1:
        verdict = "threat"
    elif score >= 0.25 or review_n >= 2:
        verdict = "review"
    elif score >= 0.1 or threats:
        verdict = "watch"

    return {
        "verdict": verdict,
        "score": round(min(1.0, score), 3),
        "threats": threats,
        "threat_warn_level": threat_warn_level(),
        "posture_floor": threat_posture_floor(),
        "ironclad_sealed": sealed,
        "popcorn_count": (popcorn_panel.get("library") or {}).get("count"),
        "inspector": inspector_summary,
        "media_scan": media_scan if media_scan else None,
        "security_slices": slices,
        "pillar_verdicts": pillar_verdicts,
        "gatekeeper_tighten": gatekeeper_tighten_signal(verdict=verdict),
        "authority": "ellie",
    }


def systemwide_threat(*, scan: bool = False) -> dict[str, Any]:
    """Backward-compatible alias."""
    out = unified_security_posture(scan=scan)
    return {k: v for k, v in out.items() if k != "security_slices"}


def publish_authority(*, threat: dict[str, Any]) -> dict[str, Any]:
    doc = {
        "schema": "field-ellie-security-authority/v1",
        "updated": _now(),
        "authority": "ellie",
        "threat_warn_level": threat.get("threat_warn_level") or threat_warn_level(),
        "posture_floor": threat.get("posture_floor") or threat_posture_floor(),
        "verdict": threat.get("verdict"),
        "score": threat.get("score"),
        "threats": threat.get("threats"),
        "pillar_verdicts": threat.get("pillar_verdicts"),
        "redundancy_retired": (_load(DOCTRINE, {}).get("redundancy_retired") or {}),
        "motto": "Workers enforce — ELLIE publishes the single security posture.",
    }
    _save_atomic(AUTHORITY, doc)
    return doc


def posture(*, scan: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    plate_cfg = doctrine.get("plate_model") or {}
    threat = unified_security_posture(scan=scan)
    material = {
        "verdict": threat["verdict"],
        "score": threat["score"],
        "threats": threat["threats"],
        "threat_warn_level": threat["threat_warn_level"],
        "pillar_verdicts": threat.get("pillar_verdicts"),
    }
    chain_hash = _plate_hash(material)
    authority = publish_authority(threat=threat)
    doc = {
        "schema": "field-ellie-fier/v2",
        "ts": _now(),
        "ok": True,
        "title": doctrine.get("title") or "ELLIE",
        "motto": doctrine.get("motto"),
        "inspired_by": doctrine.get("inspired_by"),
        "authority": doctrine.get("authority") or {},
        "plate_key": plate_cfg.get("meld_key") or "field_ellie_fier",
        "plate_attached": bool(plate_cfg.get("plate_attach") or (doctrine.get("policy") or {}).get("plate_attach")),
        "condense_group": plate_cfg.get("condense_group"),
        "combinatorics_role": plate_cfg.get("combinatorics_role"),
        "routes": doctrine.get("routes") or {},
        "policy": doctrine.get("policy") or {},
        "security_pillars": doctrine.get("security_pillars") or {},
        "systemwide": threat,
        "security_slices": threat.get("security_slices"),
        "threat_warn_level": threat["threat_warn_level"],
        "posture_floor": threat["posture_floor"],
        "security_authority": authority,
        "feeds": doctrine.get("feeds") or [],
        "chain_hash": chain_hash,
        "posture": (
            f"ELLIE — {threat['verdict']} · score {threat['score']:.2f} · "
            f"threat {threat['threat_warn_level']} · "
            f"{(threat.get('security_slices') or {}).get('live_count', 0)} feeds live"
        ),
    }
    _save_atomic(PANEL, doc)
    _append_ledger({
        "ts": doc["ts"],
        "verdict": threat["verdict"],
        "score": threat["score"],
        "threat_warn_level": threat["threat_warn_level"],
        "chain_hash": chain_hash,
    })
    return doc


def _panel_snapshot(panel_name: str | None) -> dict[str, Any]:
    if not panel_name:
        return {}
    raw = _load(STATE / str(panel_name), {})
    if not isinstance(raw, dict):
        return {}
    slim: dict[str, Any] = {}
    for key, val in raw.items():
        if isinstance(val, (dict, list)):
            continue
        slim[key] = val
    if raw.get("summary") and isinstance(raw["summary"], dict):
        for k, v in raw["summary"].items():
            if not isinstance(v, (dict, list)):
                slim[f"summary.{k}"] = v
    if raw.get("gate") and isinstance(raw["gate"], dict):
        slim["gate.verdict"] = raw["gate"].get("verdict")
    return slim


_ROUTE_TO_PILLAR = {
    "network": "network",
    "truth": "truth",
    "thermal": "thermal_power",
    "thermal_power": "thermal_power",
    "firmware": "firmware_vault",
    "firmware_vault": "firmware_vault",
    "media": "media",
    "sovereign": "sovereign",
}


def _resolve_pillar_id(pillar_id: str) -> str:
    key = str(pillar_id or "").strip().lower()
    return _ROUTE_TO_PILLAR.get(key, key)


def pillar_diagnostic(pillar_id: str, *, scan: bool = False) -> dict[str, Any]:
    """Single-page diagnostic payload for one ELLIE security pillar."""
    doctrine = _load(DOCTRINE, {})
    pillar = _resolve_pillar_id(pillar_id)
    pillars_cfg = doctrine.get("security_pillars") or {}
    pages = doctrine.get("diagnostic_pages") or []
    page_meta = next((p for p in pages if str(p.get("pillar") or p.get("id")) == pillar), None)
    if pillar not in pillars_cfg and not page_meta:
        return {"ok": False, "error": "unknown_pillar", "pillar": pillar, "known": list(pillars_cfg.keys())}

    posture_doc = posture(scan=scan)
    slices = collect_security_slices()
    bucket = (slices.get("pillars") or {}).get(pillar) or {}
    feed_rows = list(bucket.get("feeds") or [])
    enriched: list[dict[str, Any]] = []
    for row in feed_rows:
        entry = dict(row)
        panel_name = row.get("panel")
        if panel_name:
            entry["panel_data"] = _panel_snapshot(str(panel_name))
        enriched.append(entry)

    sw = posture_doc.get("systemwide") or {}
    title = (page_meta or {}).get("title") or pillar.replace("_", " ").title()
    return {
        "schema": "field-ellie-diag-page/v1",
        "ok": True,
        "pillar": pillar,
        "title": title,
        "route": (page_meta or {}).get("route") or f"/field-ellie/{pillar}",
        "updated": _now(),
        "threat_warn_level": posture_doc.get("threat_warn_level") or threat_warn_level(),
        "systemwide": {
            "verdict": sw.get("verdict"),
            "score": sw.get("score"),
            "threat_warn_level": sw.get("threat_warn_level"),
        },
        "pillar_posture": {
            "verdict": bucket.get("verdict") or "clear",
            "live": bucket.get("live") or 0,
            "feed_count": len(enriched),
            "max_score": bucket.get("max_score"),
        },
        "feeds": enriched,
        "workers": (pillars_cfg.get(pillar) or {}).get("workers") or [],
        "motto": doctrine.get("motto"),
    }


def read_authority() -> dict[str, Any]:
    cached = _load(AUTHORITY, {})
    if cached.get("schema"):
        return cached
    panel = _load(PANEL, {})
    if panel.get("security_authority"):
        return panel["security_authority"]
    return {"threat_warn_level": threat_warn_level(), "posture_floor": threat_posture_floor(), "authority": "ellie"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        do_scan = "--scan" in sys.argv[2:]
        print(json.dumps(posture(scan=do_scan), ensure_ascii=False, indent=2))
        return 0
    if cmd == "scan":
        print(json.dumps(scan_media(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "threat":
        print(json.dumps(unified_security_posture(scan=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "slices":
        print(json.dumps(collect_security_slices(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "authority":
        auth = read_authority()
        if not auth.get("schema"):
            auth = publish_authority(threat=unified_security_posture(scan=False))
        print(json.dumps(auth, ensure_ascii=False, indent=2))
        return 0
    if cmd == "threat_warn_level":
        print(json.dumps({"threat_warn_level": threat_warn_level(), "posture_floor": threat_posture_floor()}, ensure_ascii=False))
        return 0
    if cmd == "pillar":
        pid = sys.argv[2] if len(sys.argv) > 2 else ""
        do_scan = "--scan" in sys.argv[3:] or str(os.environ.get("ELLIE_PILLAR_SCAN", "")).strip() in ("1", "true", "yes")
        print(json.dumps(pillar_diagnostic(pid, scan=do_scan), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-ellie-fier.py [json|scan|threat|slices|authority|threat_warn_level|pillar ID] [--scan]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())