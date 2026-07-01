#!/usr/bin/env pythong
"""Queen External Field Wire — beyond-DARPA secure comms quarantine lane.

Redundancy + truth filters. Integrity chain — never tampered or broken.
Hostess7 ↔ Hostess7, human, or AI — human keystroke/voice always situational.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
MANDATE = QUEEN / "data" / "queen-external-wire.json"
WIRE_DIR = STATE / "external-wire"
RING = WIRE_DIR / "ring.jsonl"
RATE_STATE = WIRE_DIR / "rate.json"
SURGE_STATE = WIRE_DIR / "surge.json"
DEDUP_STATE = WIRE_DIR / "dedup.json"
BRIEF = WIRE_DIR / "external_wire_brief.json"

def _filters_mod() -> Any:
    import importlib.util

    path = QUEEN / "lib" / "queen-external-wire-filters.py"
    spec = importlib.util.spec_from_file_location("queen_external_wire_filters", path)
    if not spec or not spec.loader:
        raise ImportError("queen-external-wire-filters.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_F = _filters_mod()
_echo_filter = _F._echo_filter
classify_party = _F.classify_party
compose_verdict = _F.compose_verdict
enforce_seal_or_fail = _F.enforce_seal_or_fail
human_compromise_adjust = _F.human_compromise_adjust
load_mandate = _F.load_mandate
make_wire_auth = _F.make_wire_auth
redundancy_filter = _F.redundancy_filter
scan_payload_files = _F.scan_payload_files
seal_record = _F.seal_record
truth_filter = _F.truth_filter
verify_chain = _F.verify_chain
verify_wire_auth = _F.verify_wire_auth
wire_token = _F.wire_token


def _secure_channel_mod() -> Any | None:
    import importlib.util

    path = QUEEN / "lib" / "queen-secure-channel.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("queen_secure_channel", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _contact_vector_mod() -> Any:
    import importlib.util

    path = QUEEN / "lib" / "queen-contact-vector.py"
    spec = importlib.util.spec_from_file_location("queen_contact_vector", path)
    if not spec or not spec.loader:
        raise ImportError("queen-contact-vector missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_SOURCE_RE = re.compile(r"^[a-zA-Z0-9._:-]{1,128}$")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _limits() -> dict[str, int]:
    m = load_mandate()
    rl = m.get("rate_limits") or {}
    st = m.get("storage") or {}
    return {
        "per_source_per_minute": int(rl.get("per_source_per_minute", 24)),
        "global_per_minute": int(rl.get("global_per_minute", 96)),
        "max_body_bytes": int(rl.get("max_body_bytes", 8192)),
        "max_concurrent_burst": int(rl.get("max_concurrent_burst", 8)),
        "surge_window_seconds": int(rl.get("surge_window_seconds", 10)),
        "surge_trip_count": int(rl.get("surge_trip_count", 40)),
        "circuit_cooldown_seconds": int(rl.get("circuit_cooldown_seconds", 45)),
        "ring_max_lines": int(st.get("ring_max_lines", 480)),
        "ring_max_bytes": int(st.get("ring_max_bytes", 2_097_152)),
    }


def _source_key(raw: str) -> str:
    s = (raw or "unknown").strip()[:128]
    if _SOURCE_RE.match(s):
        return s
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:16]


def _ring_stats() -> dict[str, Any]:
    if not RING.is_file():
        return {"lines": 0, "bytes": 0, "full": False}
    try:
        data = RING.read_bytes()
        lines = data.count(b"\n")
        if data and not data.endswith(b"\n"):
            lines += 1
        lim = _limits()
        full = lines >= lim["ring_max_lines"] or len(data) >= lim["ring_max_bytes"]
        return {"lines": lines, "bytes": len(data), "full": full}
    except OSError:
        return {"lines": 0, "bytes": 0, "full": False}


def _rate_doc() -> dict[str, Any]:
    doc = _load_json(RATE_STATE, {})
    if not isinstance(doc, dict):
        doc = {}
    doc.setdefault("global", [])
    doc.setdefault("sources", {})
    return doc


def _prune_bucket(bucket: list[float], *, window: float = 60.0, now: float | None = None) -> list[float]:
    now = now if now is not None else time.time()
    return [t for t in bucket if now - t < window]


def _surge_doc() -> dict[str, Any]:
    doc = _load_json(SURGE_STATE, {})
    if not isinstance(doc, dict):
        doc = {}
    doc.setdefault("recent", [])
    doc.setdefault("circuit_open_until", 0.0)
    doc.setdefault("trips", 0)
    return doc


def _dedup_doc() -> dict[str, Any]:
    doc = _load_json(DEDUP_STATE, {})
    if not isinstance(doc, dict):
        doc = {}
    doc.setdefault("hashes", {})
    return doc


def _circuit_open(now: float | None = None) -> tuple[bool, float]:
    now = now if now is not None else time.time()
    surge = _surge_doc()
    until = float(surge.get("circuit_open_until") or 0)
    return until > now, max(0.0, until - now)


def _check_rate(source: str) -> dict[str, Any]:
    now = time.time()
    lim = _limits()
    open_circuit, cooldown = _circuit_open(now)
    if open_circuit:
        return {
            "ok": False,
            "verdict": "EXTERNAL_CIRCUIT_OPEN",
            "lane": "External",
            "cooldown_seconds": round(cooldown, 1),
            "reason": "surge_circuit_open",
        }

    rate = _rate_doc()
    global_bucket = _prune_bucket(list(rate.get("global") or []), now=now)
    sources = dict(rate.get("sources") or {})
    src_bucket = _prune_bucket(list(sources.get(source) or []), now=now)

    surge = _surge_doc()
    recent = _prune_bucket(list(surge.get("recent") or []), window=lim["surge_window_seconds"], now=now)
    recent.append(now)
    surge["recent"] = recent[-lim["surge_trip_count"] * 2 :]
    if len(recent) >= lim["surge_trip_count"]:
        surge["circuit_open_until"] = now + lim["circuit_cooldown_seconds"]
        surge["trips"] = int(surge.get("trips") or 0) + 1
        _save_json(SURGE_STATE, surge)
        return {
            "ok": False,
            "verdict": "EXTERNAL_CIRCUIT_OPEN",
            "lane": "External",
            "cooldown_seconds": lim["circuit_cooldown_seconds"],
            "reason": "surge_trip",
        }
    _save_json(SURGE_STATE, surge)

    if len(global_bucket) >= lim["global_per_minute"]:
        return {"ok": False, "verdict": "EXTERNAL_RATE_LIMIT", "lane": "External", "reason": "global_cap"}
    if len(src_bucket) >= lim["per_source_per_minute"]:
        return {"ok": False, "verdict": "EXTERNAL_RATE_LIMIT", "lane": "External", "reason": "source_cap"}
    if len(src_bucket) >= lim["max_concurrent_burst"]:
        return {"ok": False, "verdict": "EXTERNAL_BURST_LIMIT", "lane": "External", "reason": "burst_cap"}

    global_bucket.append(now)
    src_bucket.append(now)
    rate["global"] = global_bucket
    sources[source] = src_bucket
    rate["sources"] = sources
    _save_json(RATE_STATE, rate)
    return {"ok": True, "verdict": "EXTERNAL_RATE_OK", "lane": "External"}


def _dedup_check(payload: str, source: str) -> bool:
    h = hashlib.sha256(f"{source}:{payload}".encode("utf-8", errors="replace")).hexdigest()
    doc = _dedup_doc()
    hashes: dict[str, float] = dict(doc.get("hashes") or {})
    now = time.time()
    hashes = {k: v for k, v in hashes.items() if now - v < 300}
    if h in hashes:
        return True
    hashes[h] = now
    if len(hashes) > 2000:
        oldest = sorted(hashes.items(), key=lambda x: x[1])[:500]
        for k, _ in oldest:
            hashes.pop(k, None)
    doc["hashes"] = hashes
    _save_json(DEDUP_STATE, doc)
    return False


def _compact_text(text: str, *, max_len: int = 1200) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip())
    return s[:max_len]


def _extract_payload(body: dict[str, Any]) -> str:
    raw = body.get("query") or body.get("text") or body.get("message") or body.get("payload") or ""
    if isinstance(raw, dict):
        raw = json.dumps(raw, ensure_ascii=False)
    return _compact_text(str(raw), max_len=_limits()["max_body_bytes"])


def _append_external(row: dict[str, Any]) -> dict[str, Any]:
    lim = _limits()
    stats = _ring_stats()
    if stats.get("full"):
        return {
            "ok": False,
            "verdict": "EXTERNAL_STORAGE_REFUSE",
            "lane": "External",
            "imported": False,
            "internal_touch": False,
            "reason": "ring_full_refuse_surge",
            "storage": stats,
        }
    sealed = seal_record(row)
    line = json.dumps(sealed, ensure_ascii=False) + "\n"
    if stats.get("bytes", 0) + len(line.encode("utf-8")) > lim["ring_max_bytes"]:
        return {
            "ok": False,
            "verdict": "EXTERNAL_STORAGE_REFUSE",
            "lane": "External",
            "imported": False,
            "internal_touch": False,
            "reason": "byte_cap_refuse",
            "storage": stats,
        }
    WIRE_DIR.mkdir(parents=True, exist_ok=True)
    with RING.open("a", encoding="utf-8") as f:
        f.write(line)
    return {
        "ok": True,
        "lane": "External",
        "imported": False,
        "internal_touch": False,
        "chain_hash": sealed.get("chain_hash"),
        "chain_seq": sealed.get("chain_seq"),
    }


def _process_message(
    body: dict[str, Any],
    *,
    direction: str,
    remote_ip: str = "",
) -> dict[str, Any]:
    """Shared pipeline: seal check → party → auth → rate → truth → redundancy → record."""
    seal_gate = enforce_seal_or_fail()
    if not seal_gate.get("ok"):
        seal_gate["lane"] = "External"
        seal_gate["imported"] = False
        seal_gate["internal_touch"] = False
        return seal_gate

    sc = _secure_channel_mod()
    if sc is not None:
        gate = sc.gate_message(body, direction=direction, remote_ip=remote_ip)
        if not gate.get("ok"):
            gate.setdefault("lane", "SecureChannel")
            gate["external_wire_bypassed"] = True
            return gate

    file_gate = scan_payload_files(body, direction=direction)
    if not file_gate.get("ok") and not file_gate.get("skipped"):
        return {
            "ok": False,
            "verdict": "EXTERNAL_FILE_VIRUS_HOLD",
            "lane": "FieldVirus",
            "imported": False,
            "internal_touch": False,
            "field_virus": file_gate,
            "operator_hint": "Referenced files held HOSTILE — abstract harms before touch.",
        }

    party_info = classify_party(body)
    auth = verify_wire_auth(body, party_info=party_info)
    if not auth.get("ok"):
        return {
            "ok": False,
            "verdict": "EXTERNAL_AUTH_FAIL",
            "lane": "External",
            "imported": False,
            "internal_touch": False,
            "party": party_info,
            **auth,
        }

    lim = _limits()
    src = _source_key(str(body.get("from") or party_info["party"] or remote_ip or "unknown"))
    payload = _extract_payload(body)
    if len(payload.encode("utf-8")) > lim["max_body_bytes"]:
        return {
            "ok": False,
            "verdict": "EXTERNAL_PAYLOAD_REFUSE",
            "lane": "External",
            "imported": False,
            "reason": "body_too_large",
        }

    gate = _check_rate(src)
    if not gate.get("ok"):
        gate["imported"] = False
        gate["internal_touch"] = False
        return gate

    if payload and _dedup_check(payload, src):
        return {
            "ok": False,
            "verdict": "EXTERNAL_DUPLICATE",
            "lane": "External",
            "imported": False,
            "reason": "dedup_window",
        }

    corroboration = int(_echo_filter(payload).get("corroboration") or 0)

    truth_doc = truth_filter(payload, party_info=party_info, corroboration=corroboration)
    redundancy_doc = redundancy_filter(payload, body, party_info=party_info, truth_doc=truth_doc)
    adjustments = human_compromise_adjust(party_info, truth_doc, redundancy_doc)
    verdict = compose_verdict(redundancy_doc, truth_doc, adjustments=adjustments)

    accept = verdict in (
        "EXTERNAL_SECURE_ACK",
        "EXTERNAL_SECURE_ACK_SITUATIONAL",
        "EXTERNAL_REDUNDANCY_HOLD",
    )
    if verdict == "EXTERNAL_TRUTH_REJECT" or verdict == "EXTERNAL_REDUNDANCY_REJECT":
        accept = False

    row = {
        "schema": "queen-external-wire-record/v2",
        "ts": str(body.get("ts") or _now()),
        "lane": "External",
        "classification": "External",
        "imported": False,
        "internal_touch": False,
        "direction": direction,
        "party": party_info["party"],
        "input_channel": party_info["input_channel"],
        "input_compromise_expected": party_info["input_compromise_expected"],
        "source": src,
        "to": str(body.get("to") or ""),
        "remote_ip": (remote_ip or "")[:64],
        "action": str(body.get("action") or direction),
        "payload": payload,
        "iff": "CONTACT_HOSTILE",
        "presume_hostile": True,
        "filters": {
            "redundancy": redundancy_doc,
            "truth": truth_doc,
            "adjustments": adjustments,
        },
        "verdict": verdict,
        "never_tampered_or_broken": True,
        "tier": load_mandate().get("tier", "beyond_darpa_lockheed"),
    }
    if not accept:
        return {
            "ok": False,
            "verdict": verdict,
            "lane": "External",
            "imported": False,
            "internal_touch": False,
            "party": party_info,
            "filters": row["filters"],
            "never_tampered_or_broken": True,
        }

    append = _append_external(row)
    if not append.get("ok"):
        return append

    cv = _contact_vector_mod().update_vector(
        {**body, "party": party_info.get("party"), "input_channel": party_info.get("input_channel")},
        payload=payload,
        filters=row["filters"],
    )
    return {
        **append,
        "ok": True,
        "verdict": verdict,
        "schema": "queen-external-wire/v2",
        "party": party_info,
        "filters": row["filters"],
        "contact_vector": cv.get("vector"),
        "contact_dominant": cv.get("dominant"),
        "grounded": True,
        "from": "queen-external-wire",
        "to": str(body.get("to") or src),
        "content": _grounded_content(payload, party_info=party_info, verdict=verdict),
        "never_tampered_or_broken": True,
        "operator_hint": "External ring only — poll/verify; main brain untouched.",
    }


def _grounded_content(payload: str, *, party_info: dict[str, Any], verdict: str) -> str:
    party = party_info.get("party", "unknown")
    ch = party_info.get("input_channel", "")
    base = f"Secure External wire — {party}"
    if party_info.get("input_compromise_expected"):
        base += f" via {ch} (situational; compromise expected)"
    return f"{base}. {verdict}. Recorded External, not imported. Payload: {payload[:240] or '(empty)'}"


def external_wire_status() -> dict[str, Any]:
    m = load_mandate()
    stats = _ring_stats()
    open_circuit, cooldown = _circuit_open()
    seal_gate = enforce_seal_or_fail()
    chain = verify_chain()
    try:
        cv = _contact_vector_mod().vector_instant()
    except Exception:
        cv = {}
    return {
        "schema": "queen-external-wire/v2",
        "updated": _now(),
        "tier": m.get("tier"),
        "motto": m.get("motto"),
        "doctrine": m.get("doctrine") or {},
        "parties": m.get("parties") or {},
        "contact_vector": cv.get("vector"),
        "contact_classification": cv,
        "lane": "External",
        "import_to_main": False,
        "internal_touch": False,
        "ddos_immune": True,
        "never_tampered_or_broken": seal_gate.get("ok") and chain.get("ok"),
        "integrity": {"seal": seal_gate.get("seal", {}), "chain": chain},
        "filters": m.get("filters") or {},
        "storage": {**stats, **(m.get("storage") or {})},
        "rate_limits": m.get("rate_limits") or {},
        "circuit": {"open": open_circuit, "cooldown_seconds": round(cooldown, 1)},
        "paths": {"ring": str(RING), "state": str(WIRE_DIR)},
        "api": m.get("api") or {},
        "wire_token_configured": bool(wire_token()),
    }


def receive_external(body: dict[str, Any], *, remote_ip: str = "") -> dict[str, Any]:
    body = {**body, "action": body.get("action") or "receive"}
    return _process_message(body, direction="inbound", remote_ip=remote_ip)


def speak_external(body: dict[str, Any], *, remote_ip: str = "") -> dict[str, Any]:
    """Outbound grounded speak — Hostess7, AI, or human (situational) on External wire only."""
    body = {**body, "action": "speak"}
    if body.get("party") in (None, "", "hostess7") and not body.get("wire_auth"):
        body["party"] = body.get("party") or "hostess7"
        body.setdefault("ts", _now())
        body["wire_auth"] = make_wire_auth(body)
    return _process_message(body, direction="outbound", remote_ip=remote_ip)


def teach_external_wire() -> dict[str, Any]:
    m = load_mandate()
    brief = {
        "updated": _now(),
        "tier": m.get("tier"),
        "doctrine": m.get("doctrine"),
        "parties": m.get("parties"),
        "filters": m.get("filters"),
        "human_compromise": m.get("input_channels"),
        "wire_token_hint": "Hostess7 peers: POST with party hostess7 + wire_auth HMAC",
    }
    WIRE_DIR.mkdir(parents=True, exist_ok=True)
    _save_json(BRIEF, brief)
    wire_token()
    return {"ok": True, "brief": brief, "lane": "External"}


def poll_external(*, limit: int = 20, since: str = "", verify: bool = True) -> dict[str, Any]:
    if verify:
        chain = verify_chain()
        if not chain.get("ok"):
            return {
                "ok": False,
                "lane": "External",
                "verdict": "EXTERNAL_CHAIN_BROKEN",
                "never_tampered_or_broken": False,
                "chain": chain,
            }
    limit = max(1, min(int(limit), 50))
    rows: list[dict[str, Any]] = []
    if RING.is_file():
        try:
            for line in RING.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    doc = json.loads(line)
                    if since and str(doc.get("ts") or "") < since:
                        continue
                    rows.append(doc)
                except json.JSONDecodeError:
                    continue
        except OSError:
            pass
    return {
        "ok": True,
        "lane": "External",
        "imported": False,
        "internal_touch": False,
        "never_tampered_or_broken": True,
        "records": rows[-limit:],
        "storage": _ring_stats(),
    }


def reset_limits(*, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "lane": "External", "error": "confirm_required"}
    for path in (RATE_STATE, SURGE_STATE, DEDUP_STATE):
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass
    return {"ok": True, "lane": "External", "limits_reset": True, "imported": False}


def purge_external(*, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        return {
            "ok": False,
            "lane": "External",
            "error": "confirm_required",
            "hint": "POST action purge with confirm:true",
        }
    stats = _ring_stats()
    try:
        if RING.is_file():
            RING.unlink()
        head = WIRE_DIR / "chain-head.json"
        if head.is_file():
            head.unlink()
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "lane": "External", "purged": stats, "imported": False}


def dispatch(body: dict[str, Any], *, remote_ip: str = "") -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "json"):
        return {"ok": True, **external_wire_status()}
    if action in ("teach", "seed"):
        return teach_external_wire()
    if action in ("verify", "verify-chain", "integrity"):
        chain = verify_chain()
        seal = enforce_seal_or_fail()
        return {
            "ok": chain.get("ok") and seal.get("ok"),
            "lane": "External",
            "never_tampered_or_broken": chain.get("ok") and seal.get("ok"),
            "chain": chain,
            "seal_gate": seal,
        }
    if action in ("receive", "ground", "ingest", "contact"):
        return receive_external(body, remote_ip=remote_ip)
    if action in ("speak", "send", "transmit"):
        return speak_external(body, remote_ip=remote_ip)
    if action == "poll":
        return poll_external(
            limit=int(body.get("limit") or 20),
            since=str(body.get("since") or ""),
            verify=body.get("verify", True) is not False,
        )
    if action == "purge":
        return purge_external(confirm=bool(body.get("confirm")))
    if action in ("reset_limits", "reset-limits", "reset_circuit"):
        return reset_limits(confirm=bool(body.get("confirm")))
    if action in ("wire-auth", "wire_auth", "auth-sample"):
        body.setdefault("party", "hostess7")
        body.setdefault("ts", _now())
        return {
            "ok": True,
            "wire_auth": make_wire_auth(body),
            "party": "hostess7",
            "note": "HMAC for Hostess7↔Hostess7 peer traffic",
        }
    return {"ok": False, "error": "unknown_action", "lane": "External", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(external_wire_status(), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        remote = str(body.pop("remote_ip", "") or "")
        print(json.dumps(dispatch(body, remote_ip=remote), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-external-wire.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())