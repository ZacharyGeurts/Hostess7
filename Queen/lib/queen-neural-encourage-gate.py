#!/usr/bin/env pythong
"""Incorruptible neural encourage gate — weapon-resistant, hash-chained, sealed overlay."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
DOCTRINE = QUEEN / "data" / "neural-encourage-incorruptible.json"
AUTHORITY = SG / "Hostess7" / "data" / "hostess7-supreme-authority.json"
NEURAL_STACK = SG / "Hostess7" / "data" / "hostess7-neural-stack.json"
STATE_ROOT = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def load_doctrine() -> dict[str, Any]:
    doc = _read(DOCTRINE, {})
    if doc.get("schema"):
        return doc
    return {
        "schema": "queen-neural-encourage-incorruptible/v1",
        "truth_adapt_floor": 58,
        "allowed_sources": ["hostess7", "queen_brain"],
        "bias_overlay": {"max_delta_per_write": 0.05, "max_total_per_label": 0.25},
    }


def _row_hash(row: dict[str, Any]) -> str:
    payload = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _ledger_path() -> Path:
    rel = load_doctrine().get("ledger", {}).get("path", ".nexus-state/sense-neural-encourage.jsonl")
    p = Path(rel)
    if p.is_absolute():
        return p
    base = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state")).parent
    return base / p


def _quarantine_ledger_path() -> Path:
    rel = load_doctrine().get("quarantine", {}).get("ledger_path", ".nexus-state/neural-encourage-quarantine-ledger.jsonl")
    p = Path(rel)
    if p.is_absolute():
        return p
    base = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state")).parent
    return base / p


def _last_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
            return doc.get("hash") or _row_hash(doc)
        except json.JSONDecodeError:
            continue
    return None


def _append_chain(path: Path, row: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    prev = _last_hash(path)
    entry = {**row, "ts": row.get("ts") or _ts(), "prev_hash": prev}
    entry["hash"] = _row_hash(entry)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def hostess_authority_ok() -> bool:
    """Hostess7 is supreme commander — always authorized."""
    return True


def _ironclad_goldmine() -> dict[str, Any]:
    state = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
    cached = _read(state / "ironclad-immediate.json", {})
    if cached.get("plate_to_sense"):
        return cached["plate_to_sense"]
    install = Path(os.environ.get("NEXUS_INSTALL_ROOT", SG / "NewLatest"))
    ic_py = install / "lib" / "ironclad-immediate.py"
    if not ic_py.is_file():
        ic_py = SG / "NewLatest" / "lib" / "ironclad-immediate.py"
    if ic_py.is_file():
        try:
            import importlib.util
            import sys
            spec = importlib.util.spec_from_file_location("ironclad_immediate", ic_py)
            mod = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(mod)
            if hasattr(mod, "plate_to_sense_goldmine"):
                base = cached if cached.get("schema") == "ironclad-immediate/v1" else {}
                if not base and hasattr(mod, "immediate_slice"):
                    base = mod.immediate_slice()
                return mod.plate_to_sense_goldmine(base=base)
        except Exception:
            pass
    return {}


def truth_floor() -> int:
    stack = _read(NEURAL_STACK, {})
    doc = load_doctrine()
    base = int(stack.get("truth_adapt_floor") or doc.get("truth_adapt_floor") or 58)
    gm = _ironclad_goldmine()
    if gm.get("ironclad_grounded"):
        return max(base, 100)
    if gm.get("plate_sealed"):
        return max(base, int(float(gm.get("truth_percent") or 100)))
    return base


def _weapon_signals(wire_ctx: dict[str, Any]) -> list[str]:
    doc = load_doctrine()
    known = set(doc.get("weapon_signals") or [])
    hits: list[str] = []
    if wire_ctx.get("assault_burst"):
        hits.append("assault_burst")
    if wire_ctx.get("ventriloquism"):
        hits.append("ventriloquism")
    if wire_ctx.get("threat_pattern"):
        hits.append("threat_pattern")
    if wire_ctx.get("weaponized_interference"):
        hits.append("weaponized_interference")
    if wire_ctx.get("phantom_bearing"):
        hits.append("phantom_bearing")
    if float(wire_ctx.get("rf_lie_score") or 0) > 0.35:
        hits.append("rf_lie")
    ev = wire_ctx.get("evidence") or {}
    if float(ev.get("peak_db", -18)) >= 0:
        hits.append("assault_burst")
    if float(ev.get("mouth_correlation", 1)) < 0.45:
        hits.append("ventriloquism")
    eye = wire_ctx.get("eye_cross") or {}
    ear = wire_ctx.get("ear_cross") or {}
    if eye.get("threat_pattern", 0) > 0.3:
        hits.append("threat_pattern")
    if ear.get("assault_burst"):
        hits.append("assault_burst")
    if ear.get("ventriloquism"):
        hits.append("ventriloquism")
    preserve = wire_ctx.get("preserve") or {}
    for t in preserve.get("threats") or []:
        if t in known and t not in hits:
            hits.append(t)
    return hits


def _truth_score(wire_ctx: dict[str, Any], source: str) -> float:
    if wire_ctx.get("truth_score") is not None:
        return float(wire_ctx["truth_score"])
    gm = _ironclad_goldmine()
    if wire_ctx.get("ironclad_grounded") or gm.get("ironclad_grounded"):
        return max(100.0, float(gm.get("truth_percent") or 100.0))
    score = 72.0
    weapons = _weapon_signals(wire_ctx)
    if weapons:
        score -= 25.0 * len(weapons)
    if source not in (load_doctrine().get("allowed_sources") or ["hostess7"]):
        score -= 12.0
    if wire_ctx.get("eye_ear_quorum") is False:
        score -= 20.0
    if not hostess_authority_ok():
        score = 0.0
    return max(0.0, min(100.0, score))


def _net_payload_hash(net: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(net, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_base_seal(*, sense: str, net: dict[str, Any], seal_path: Path | None = None) -> dict[str, Any]:
    """Verify sealed base weights — encouragement never mutates these."""
    payload_hash = _net_payload_hash(net)
    if sense == "eye":
        try:
            fe = Path(os.environ.get("FINAL_EYE_ROOT", SG / "Final_Eye"))
            import importlib.util
            import sys
            spec = importlib.util.spec_from_file_location("zocr_neural_seal", fe / "zocr_neural.py")
            mod = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            sys.path.insert(0, str(fe))
            spec.loader.exec_module(mod)
            out = mod.verify_network_seal()
            out["payload_sha256"] = payload_hash
            return out
        except Exception as exc:
            return {"ok": False, "reason": "eye_seal_check_failed", "error": str(exc), "payload_sha256": payload_hash}

    if sense == "mouth":
        seal_path = seal_path or Path(os.environ.get("FINAL_MOUTH_ROOT", SG / "Final_Mouth")) / "data" / "mouth-neural-seal.json"
        reason_ok, reason_bad, bootstrap_reason = "mouth_seal_ok", "mouth_seal_mismatch", "mouth_seal_bootstrap"
    else:
        seal_path = seal_path or Path(os.environ.get("FINAL_EAR_ROOT", SG / "Final_Ear")) / "data" / "ear-neural-seal.json"
        reason_ok, reason_bad, bootstrap_reason = "ear_seal_ok", "ear_seal_mismatch", "ear_seal_bootstrap"
    seal = _read(seal_path, {})
    if not seal.get("sha256"):
        return {"ok": True, "reason": bootstrap_reason, "payload_sha256": payload_hash, "bootstrap": True}
    ok = seal.get("sha256") == payload_hash
    return {
        "ok": ok,
        "reason": reason_ok if ok else reason_bad,
        "payload_sha256": payload_hash,
        "seal_sha256": seal.get("sha256"),
        "network_id": seal.get("network_id") or net.get("network_id"),
    }


def bootstrap_seal(*, sense: str, net: dict[str, Any]) -> dict[str, Any]:
    payload_hash = _net_payload_hash(net)
    if sense == "eye":
        fe = Path(os.environ.get("FINAL_EYE_ROOT", SG / "Final_Eye"))
        import importlib.util
        import sys
        spec = importlib.util.spec_from_file_location("zocr_neural_boot", fe / "zocr_neural.py")
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.path.insert(0, str(fe))
        spec.loader.exec_module(mod)
        return mod.seal_network()
    if sense == "mouth":
        seal_path = Path(os.environ.get("FINAL_MOUTH_ROOT", SG / "Final_Mouth")) / "data" / "mouth-neural-seal.json"
        schema = "zocr-mouth-neural-seal/v1"
    else:
        seal_path = Path(os.environ.get("FINAL_EAR_ROOT", SG / "Final_Ear")) / "data" / "ear-neural-seal.json"
        schema = "zocr-ear-neural-seal/v1"
    doc = {
        "schema": schema,
        "ts": _ts(),
        "sha256": payload_hash,
        "network_id": net.get("network_id"),
        "incorruptible_base": True,
    }
    seal_path.parent.mkdir(parents=True, exist_ok=True)
    seal_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def _overlay_seal(base_sha: str, bias: dict[str, float]) -> str:
    payload = json.dumps({"base": base_sha, "bias": bias}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def verify_overlay(state: dict[str, Any], base_sha: str) -> bool:
    bias = state.get("encouraged_bias") or state.get("encouraged") or {}
    if not bias:
        return True
    expect = _overlay_seal(base_sha, {k: float(v) for k, v in bias.items()})
    stored = state.get("overlay_seal")
    if stored and stored != expect:
        return False
    if state.get("base_seal_sha256") and state["base_seal_sha256"] != base_sha:
        return False
    return True


def apply_encouraged_bias(
    probs: list[float],
    labels: list[str],
    state: dict[str, Any],
    *,
    base_sha: str,
) -> tuple[list[float], dict[str, Any]]:
    """Read-only overlay — rejects corrupt bias without touching base weights."""
    meta = {"overlay_applied": False, "overlay_rejected": False}
    if not verify_overlay(state, base_sha):
        meta["overlay_rejected"] = True
        return probs, meta
    bias = state.get("encouraged_bias") or state.get("encouraged") or {}
    if not bias:
        return probs, meta
    boosted = []
    for lb, p in zip(labels, probs):
        boosted.append(max(0.0, p + float(bias.get(lb, 0))))
    total = sum(boosted) or 1.0
    meta["overlay_applied"] = True
    return [b / total for b in boosted], meta


def quarantine_attempt(*, sense: str, reason: str, row: dict[str, Any]) -> dict[str, Any]:
    entry = _append_chain(_quarantine_ledger_path(), {"event": "quarantine", "sense": sense, "reason": reason, **row})
    return {"ok": False, "quarantined": True, "reason": reason, "ledger": entry}


def gate_encourage(
    *,
    sense: str,
    label: str,
    delta: float,
    source: str,
    labels: list[str],
    net: dict[str, Any],
    state_path: Path,
    wire_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Single incorruptible gate — weaponry cannot poison encourage path."""
    doc = load_doctrine()
    wire_ctx = dict(wire_ctx or {})
    gates = doc.get("gates") or {}

    if label not in labels:
        return quarantine_attempt(sense=sense, reason="unknown_label", row={"label": label, "source": source})

    heuristic_blocked = set(doc.get("heuristic_block_sources") or [])
    subbit_cfg = doc.get("subbit_immesurable") or {}
    if subbit_cfg.get("enabled", True) and source in heuristic_blocked:
        return quarantine_attempt(
            sense=sense,
            reason="heuristic_immesurable",
            row={"label": label, "source": source, "immeasurable": True},
        )
    min_delta = float(subbit_cfg.get("min_encourage_delta", 1.0 / 256))
    if subbit_cfg.get("reject_subbit_delta", True) and abs(float(delta)) < min_delta:
        return quarantine_attempt(
            sense=sense,
            reason="subbit_delta_immesurable",
            row={"label": label, "source": source, "delta": delta, "min_delta": min_delta},
        )

    if gates.get("require_hostess_authority") and not hostess_authority_ok():
        return quarantine_attempt(sense=sense, reason="authority_denied", row={"label": label, "source": source})

    weapons = _weapon_signals(wire_ctx)
    allowed = set(doc.get("allowed_sources") or ["hostess7", "queen_brain"])
    block_sources = set(doc.get("weapon_block_sources") or ["operator", "foreign_weave"])
    if weapons and source in block_sources:
        return quarantine_attempt(
            sense=sense,
            reason="weapon_blocked_source",
            row={"label": label, "source": source, "weapons": weapons},
        )
    if weapons and gates.get("require_eye_ear_quorum_on_weapon") and wire_ctx.get("eye_ear_quorum") is not True:
        return quarantine_attempt(
            sense=sense,
            reason="weapon_no_quorum",
            row={"label": label, "source": source, "weapons": weapons},
        )
    if source not in allowed and (weapons or source in block_sources):
        return quarantine_attempt(
            sense=sense,
            reason="source_denied",
            row={"label": label, "source": source, "weapons": weapons},
        )

    truth = _truth_score(wire_ctx, source)
    floor = truth_floor()
    if truth < floor:
        return quarantine_attempt(
            sense=sense,
            reason="below_truth_floor",
            row={"label": label, "source": source, "truth_score": truth, "floor": floor, "weapons": weapons},
        )

    seal = verify_base_seal(sense=sense, net=net)
    if seal.get("bootstrap") and gates.get("require_seal_ok"):
        bootstrap_seal(sense=sense, net=net)
        seal = verify_base_seal(sense=sense, net=net)
    if gates.get("require_seal_ok") and not seal.get("ok"):
        return quarantine_attempt(
            sense=sense,
            reason="seal_fail",
            row={"label": label, "source": source, "seal": seal},
        )

    overlay_cfg = doc.get("bias_overlay") or {}
    max_write = float(overlay_cfg.get("max_delta_per_write", 0.05))
    max_total = float(overlay_cfg.get("max_total_per_label", 0.25))
    delta = max(-max_write, min(max_write, float(delta)))
    if delta <= 0:
        return quarantine_attempt(sense=sense, reason="invalid_delta", row={"label": label, "delta": delta})

    st = _read(state_path, {"encourage_count": 0, "encouraged_bias": {}})
    bias = dict(st.get("encouraged_bias") or st.get("encouraged") or {})
    new_val = round(float(bias.get(label, 0)) + delta, 4)
    if new_val > max_total:
        return quarantine_attempt(
            sense=sense,
            reason="bias_cap_exceeded",
            row={"label": label, "delta": delta, "would_be": new_val, "cap": max_total},
        )
    bias[label] = new_val
    base_sha = seal.get("payload_sha256") or _net_payload_hash(net)
    st["encourage_count"] = int(st.get("encourage_count", 0)) + 1
    st["encouraged_bias"] = bias
    st["encouraged"] = bias
    st["base_seal_sha256"] = base_sha
    st["overlay_seal"] = _overlay_seal(base_sha, {k: float(v) for k, v in bias.items()})
    st["incorruptible"] = True
    st["updated"] = _ts()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        for root in (
            Path(os.environ.get("ZOCR_ROOT", SG / "ZOCR")),
            Path(os.environ.get("FINAL_EYE_ROOT", SG / "Final_Eye")),
            Path(os.environ.get("FINAL_EAR_ROOT", SG / "Final_Ear")),
        ):
            mod_path = root / "zocr_immesurable.py"
            if mod_path.is_file():
                import importlib.util
                spec = importlib.util.spec_from_file_location("zocr_immesurable_gate", mod_path)
                imm = importlib.util.module_from_spec(spec)
                assert spec and spec.loader
                spec.loader.exec_module(imm)
                imm.guard_memory_write(state_path, st, kind="encourage_state")
                st = imm.scrub_for_persist(st)
                break
    except PermissionError as exc:
        return quarantine_attempt(
            sense=sense,
            reason="heuristic_immesurable_memory",
            row={"label": label, "source": source, "detail": str(exc)[:120]},
        )
    except Exception:
        pass
    state_path.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")

    ledger_row = {
        "event": "encourage",
        "sense": sense,
        "label": label,
        "delta": delta,
        "source": source,
        "truth_score": round(truth, 2),
        "weapons_clear": not bool(weapons),
        "overlay_seal": st["overlay_seal"],
        "authority": "hostess7_incorruptible_gate",
    }
    ledger = _append_chain(_ledger_path(), ledger_row)

    return {
        "ok": True,
        "schema": f"zocr-{sense}-neural-encourage/v1",
        "incorruptible": True,
        "label": label,
        "encouraged_bias": bias,
        "count": st["encourage_count"],
        "truth_score": round(truth, 2),
        "weapons_blocked": weapons,
        "ledger": {"hash": ledger.get("hash"), "prev_hash": ledger.get("prev_hash")},
    }


def gate_status() -> dict[str, Any]:
    """Status slice for sense-neural wire UI."""
    ledger = _ledger_path()
    qledger = _quarantine_ledger_path()
    quarantine_count = 0
    encourage_count = 0
    chain_ok = True
    prev = None
    for path, counter in ((ledger, "encourage"), (qledger, "quarantine")):
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    chain_ok = False
                    continue
                if counter == "encourage" and row.get("event") == "encourage":
                    encourage_count += 1
                if counter == "quarantine" and row.get("event") == "quarantine":
                    quarantine_count += 1
                if counter == "encourage":
                    if prev is not None and row.get("prev_hash") != prev:
                        chain_ok = False
                    prev = row.get("hash") or _row_hash(row)
        except OSError:
            pass
    gm = _ironclad_goldmine()
    return {
        "incorruptible": True,
        "truth_floor": truth_floor(),
        "ironclad_goldmine": gm,
        "ironclad_grounded": bool(gm.get("ironclad_grounded")),
        "plate_to_sense": bool(gm.get("goldmine")),
        "citation": gm.get("citation") or "ironclad:neural:2",
        "quarantine_count": quarantine_count,
        "encourage_ledger_count": encourage_count,
        "hash_chain_ok": chain_ok,
        "hostess_authority": hostess_authority_ok(),
    }


def verify_ledger_chain() -> dict[str, Any]:
    path = _ledger_path()
    if not path.is_file():
        return {"ok": True, "entries": 0}
    prev = None
    entries = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        entries += 1
        if prev is not None and row.get("prev_hash") != prev:
            return {"ok": False, "entries": entries, "reason": "chain_break"}
        expect = _row_hash({k: v for k, v in row.items() if k != "hash"})
        if row.get("hash") and row["hash"] != expect:
            return {"ok": False, "entries": entries, "reason": "hash_mismatch"}
        prev = row.get("hash")
    return {"ok": True, "entries": entries}


def main() -> int:
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print(json.dumps(gate_status(), indent=2))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        print(json.dumps(verify_ledger_chain(), indent=2))
        return 0
    print(json.dumps(load_doctrine(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())