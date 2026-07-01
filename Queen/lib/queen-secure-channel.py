#!/usr/bin/env pythong
"""Queen Secure Channel — forever invincible comms hub.

Unifies External Field Wire, World_Redata, and World_Repack under one sealed lane.
Weapons, hostility, and threat checks run before any wire moves.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
MANDATE = QUEEN / "data" / "queen-secure-channel.json"
WR = Path(os.environ.get("WORLD_REDATA_ROOT", SG / "World_Redata"))
REPACK = Path(os.environ.get("WORLD_REPACK_ROOT", SG / "World_Repack"))
CHANNEL_DIR = STATE / "secure-channel"
QUARANTINE_LOG = CHANNEL_DIR / "quarantine.jsonl"
CACHE = STATE / "secure-channel-cache.json"
REPACK_PORT = int(os.environ.get("WORLD_REPACK_PORT", "9480"))
REPACK_HOST = os.environ.get("WORLD_REPACK_HOST", "127.0.0.1")

_FAST_CACHE: dict[str, Any] | None = None
_FAST_TS = 0.0

_INJECTION_RE = re.compile(
    r"(eval\s*\(|<script|javascript:|onerror\s*=|DROP\s+TABLE|rm\s+-rf\b|/dev/tcp|"
    r"powershell\s+-enc|base64_decode|__import__\s*\(|os\.system\s*\()",
    re.I,
)


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


def _load_mod(name: str, rel: str) -> Any | None:
    path = QUEEN / "lib" / rel
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


def load_mandate() -> dict[str, Any]:
    return _load_json(MANDATE, {"schema": "queen-secure-channel/v1"})


def _queen_seal() -> dict[str, Any]:
    sec = _load_mod("queen_security", "queen-security.py")
    if sec is None:
        return {"ok": False, "reason": "security_module_missing"}
    try:
        return sec.verify_code_seal()
    except Exception as exc:
        return {"ok": False, "reason": str(exc)}


def _nexus_jump() -> Any | None:
    return _load_mod("queen_nexus_jump", "queen-nexus-jump.py")


def _weapon_signals() -> list[str]:
    doc = _load_json(QUEEN / "data" / "neural-encourage-incorruptible.json", {})
    return list(doc.get("weapon_signals") or [])


def _threat_indicators() -> list[str]:
    seed = _load_json(SG / "NewLatest" / "data" / "hostile-ai-threats-seed.json", {})
    out: list[str] = []
    for cat in seed.get("categories") or []:
        for ind in cat.get("indicators") or []:
            s = str(ind).strip().lower()
            if len(s) >= 8:
                out.append(s)
    return out[:48]


def _extract_payload(body: dict[str, Any]) -> str:
    for key in ("query", "payload", "content", "message", "text", "body"):
        val = body.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return json.dumps(body, ensure_ascii=False)[:4096]


def _contact_vector() -> dict[str, Any]:
    cv = _load_mod("queen_contact_vector", "queen-contact-vector.py")
    if cv is None:
        return {}
    try:
        return cv.vector_instant()
    except Exception:
        return {}


def _port_open(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _repack_health() -> dict[str, Any]:
    m = load_mandate()
    port_up = _port_open(REPACK_HOST, REPACK_PORT)
    health: dict[str, Any] = {"ok": False, "port_open": port_up}
    if port_up:
        try:
            req = Request(f"http://{REPACK_HOST}:{REPACK_PORT}/api/health", method="GET")
            with urlopen(req, timeout=1.2) as resp:
                raw = resp.read(4096).decode("utf-8", errors="replace")
            health = {**json.loads(raw), "ok": True, "port_open": True}
        except Exception as exc:
            health = {"ok": False, "port_open": True, "error": str(exc)[:200]}
    pid = None
    pid_path = REPACK / "data" / "world-repack.pid"
    if pid_path.is_file():
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            pid = None
    return {
        "schema": "queen-world-repack/v1",
        "upstream": str(REPACK),
        "host": REPACK_HOST,
        "port": REPACK_PORT,
        "loopback_only": (m.get("doctrine") or {}).get("repack_loopback_only", True),
        "autostart": (m.get("doctrine") or {}).get("repack_autostart", False),
        "engine": str(WR),
        "running": bool(health.get("ok")),
        "health": health,
        "pid": pid,
        "start_hint": str(REPACK / "start.sh") + " --no-open",
        "fieldnet": "queen://repack",
    }


def _redata_slice() -> dict[str, Any]:
    wr = _load_mod("queen_world_redata", "queen-world-redata.py")
    if wr is None:
        cached = _load_json(STATE / "world-redata-cache.json", {})
        return cached or {"hydrate": "/api/world-redata"}
    try:
        return wr.world_redata_fast()
    except Exception as exc:
        return {"ok": False, "error": str(exc), "hydrate": "/api/world-redata"}


def _external_slice() -> dict[str, Any]:
    ew = _load_mod("queen_external_wire", "queen-external-wire.py")
    if ew is None:
        return {"lane": "External", "hydrate": "/api/external-wire"}
    try:
        doc = ew.external_wire_status()
        return {
            "lane": doc.get("lane"),
            "never_tampered_or_broken": doc.get("never_tampered_or_broken"),
            "import_to_main": doc.get("import_to_main"),
            "ddos_immune": doc.get("ddos_immune"),
            "circuit": doc.get("circuit"),
        }
    except Exception as exc:
        return {"lane": "External", "error": str(exc)}


def _subbit_heuristics_slice() -> dict[str, Any]:
    mod = _load_mod("queen_subbit_heuristics", "queen-subbit-heuristics.py")
    if mod is None:
        m = _load_json(QUEEN / "data" / "subbit-heuristics-immesurable.json", {})
        return {
            "immeasurable": m.get("immeasurable", True),
            "persist_forbidden": m.get("persist_forbidden", True),
            "hydrate": "/api/sense-neural",
        }
    try:
        st = mod.status()
        return {
            "immeasurable": st.get("immeasurable", True),
            "persist_forbidden": st.get("persist_forbidden", True),
            "poison_guard": st.get("poison_guard"),
            "subbit_bits": st.get("subbit_bits"),
            "rule": st.get("rule"),
        }
    except Exception as exc:
        return {"immeasurable": True, "error": str(exc)[:120]}


def _weapon_scan(payload: str) -> tuple[list[str], int]:
    blob = (payload or "").lower()
    hits: list[str] = []
    score = 0
    for sig in _weapon_signals():
        if sig.lower() in blob:
            hits.append(sig)
            score += 8
    for marker in ("weaponize", "kill-order", "forever_kill", "trust_strike", "ventriloquist"):
        if marker in blob:
            hits.append(f"marker:{marker}")
            score += 5
    if _INJECTION_RE.search(payload or ""):
        hits.append("injection_pattern")
        score += 10
    for ind in _threat_indicators():
        if ind in blob:
            hits.append(f"threat:{ind[:40]}")
            score += 4
    return hits, score


def _hostility_scan(body: dict[str, Any], *, remote_ip: str = "") -> tuple[int, list[str], str]:
    reasons: list[str] = []
    score = 0
    iff = "CONTACT_HOSTILE"
    m = load_mandate()
    thr = m.get("threat") or {}
    cv_doc = _contact_vector()
    vec = cv_doc.get("vector") or {}
    alien = float(vec.get("alien") or 0)
    unknown = float(vec.get("unknown") or 0)
    if alien >= float(thr.get("contact_vector_alien_block_pct", 55)):
        score += 10
        reasons.append(f"alien_vector:{alien}")
        iff = "HOSTILE"
    elif unknown >= float(thr.get("contact_vector_unknown_hold_pct", 72)):
        score += 6
        reasons.append(f"unknown_vector:{unknown}")
    party = str(body.get("party") or body.get("from") or "unknown").lower()
    if party == "human":
        score += 3
        reasons.append("human_situational_input")
    if remote_ip and remote_ip not in ("127.0.0.1", "::1", ""):
        score += 4
        reasons.append(f"remote_ip:{remote_ip}")
    return score, reasons, iff


def threat_scan(body: dict[str, Any], *, remote_ip: str = "", direction: str = "inbound") -> dict[str, Any]:
    """Instant weapons + hostility + threat scan — no subprocess."""
    m = load_mandate()
    seal = _queen_seal()
    if not seal.get("ok") and (m.get("doctrine") or {}).get("fail_closed_on_seal_break", True):
        return {
            "ok": False,
            "verdict": "SEAL_BROKEN",
            "lane": "SecureChannel",
            "forever": False,
            "seal": seal,
        }

    payload = _extract_payload(body)
    nj = _nexus_jump()
    harm_score = 0
    harm_reasons: list[str] = []
    iff = "CONTACT_HOSTILE"
    countermeasures: list[dict[str, Any]] = []
    if nj is not None:
        harm_score, harm_reasons = nj._harm_heuristics(f"https://contact.local/?q={payload}")
        iff_doctrine = getattr(nj, "IFF_DOCTRINE", {})
    else:
        iff_doctrine = {"presume_hostile": True, "motto": "Presume hostile."}

    weapon_hits, weapon_score = _weapon_scan(payload)
    host_score, host_reasons, iff = _hostility_scan(body, remote_ip=remote_ip)
    total_threat = harm_score + weapon_score + host_score

    threatened = False
    threat_signals: list[str] = []
    if nj is not None:
        threatened, threat_signals = nj._under_threat(
            harm_score=harm_score + weapon_score,
            iff=iff,
            honor={"needs_acceptance": str(body.get("party") or "") == "human"},
            telemetry={"verdict": "ALLOW"},
            field_net={"verdict": "ALLOW_LOOPBACK", "internal": True},
        )
        if weapon_hits:
            threatened = True
            threat_signals.append("weapon_signals")
        if host_reasons:
            threatened = True
            threat_signals.extend(host_reasons[:4])

    thr_cfg = m.get("threat") or {}
    block_at = int(thr_cfg.get("harm_block_score", 12))
    hold_at = int(thr_cfg.get("harm_hold_score", 6))
    offense_active = threatened or total_threat >= hold_at or bool(weapon_hits)

    verdict = "SECURE_CHANNEL_DEFEND"
    permit = True
    if weapon_hits or weapon_score >= 8:
        permit = False
        verdict = "SECURE_CHANNEL_WEAPON_QUARANTINE"
        offense_active = True
    elif harm_score >= block_at or total_threat >= block_at + 4:
        permit = False
        verdict = "SECURE_CHANNEL_BLOCK_HOSTILE"
        offense_active = True
    elif offense_active:
        verdict = "SECURE_CHANNEL_OFFENSE_ACTIVE"

    if nj is not None:
        countermeasures = nj._countermeasures(
            verdict=verdict.replace("SECURE_CHANNEL_", ""),
            harm_score=harm_score + weapon_score,
            legacy=False,
            honor_needs_acceptance=str(body.get("party") or "") == "human",
            iff=iff,
            under_threat=threatened,
            offense_active=offense_active,
        )

    return {
        "ok": permit,
        "verdict": verdict,
        "lane": "SecureChannel",
        "direction": direction,
        "forever": True,
        "presume_hostile": True,
        "iff": iff,
        "iff_doctrine": iff_doctrine,
        "threat_score": total_threat,
        "harm": {"score": harm_score, "reasons": harm_reasons},
        "weapons": {"hits": weapon_hits, "score": weapon_score},
        "hostility": {"score": host_score, "reasons": host_reasons},
        "under_threat": threatened,
        "threat_signals": threat_signals,
        "offense_active": offense_active,
        "countermeasures": countermeasures,
        "contact_vector": (_contact_vector().get("vector") or {}),
        "imported": False,
        "internal_touch": False,
        "never_tampered_or_broken": seal.get("ok"),
    }


def _append_quarantine(entry: dict[str, Any]) -> None:
    try:
        CHANNEL_DIR.mkdir(parents=True, exist_ok=True)
        with QUARANTINE_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def gate_message(
    body: dict[str, Any],
    *,
    direction: str = "inbound",
    remote_ip: str = "",
) -> dict[str, Any]:
    """Fail-closed gate — call before external wire moves."""
    scan = threat_scan(body, remote_ip=remote_ip, direction=direction)
    if scan.get("ok"):
        return {"ok": True, "gate": "pass", "scan": scan, "lane": "SecureChannel"}
    row = {
        "schema": "queen-secure-channel-quarantine/v1",
        "ts": _now(),
        "direction": direction,
        "remote_ip": remote_ip,
        "verdict": scan.get("verdict"),
        "party": body.get("party"),
        "from": body.get("from"),
        "payload_preview": _extract_payload(body)[:240],
        "scan": {k: scan.get(k) for k in ("threat_score", "weapons", "hostility", "threat_signals", "iff")},
        "imported": False,
        "internal_touch": False,
    }
    _append_quarantine(row)
    return {
        "ok": False,
        "gate": "quarantine",
        "lane": "SecureChannel",
        "imported": False,
        "internal_touch": False,
        "never_tampered_or_broken": scan.get("never_tampered_or_broken"),
        **scan,
        "operator_hint": "Threat or weapon signal — quarantined; main brain untouched.",
    }


def secure_channel_fast() -> dict[str, Any]:
    import time

    global _FAST_CACHE, _FAST_TS
    now = time.time()
    if _FAST_CACHE and now - _FAST_TS < 10.0:
        return _FAST_CACHE
    m = load_mandate()
    seal = _queen_seal()
    doc = {
        "schema": "queen-secure-channel/v1",
        "updated": _now(),
        "fast": True,
        "forever": True,
        "tier": m.get("tier"),
        "motto": m.get("motto"),
        "doctrine": m.get("doctrine") or {},
        "lanes": m.get("lanes") or {},
        "queen_seal_ok": seal.get("ok"),
        "security_posture": "fail_closed" if not seal.get("ok") else "sealed",
        "world_redata": _redata_slice(),
        "world_repack": _repack_health(),
        "external_wire": _external_slice(),
        "contact_vector": (_contact_vector().get("vector") or {}),
        "subbit_heuristics": _subbit_heuristics_slice(),
        "weapons_armed": True,
        "threat_scan": "instant",
        "hydrate": "/api/secure-channel?full=1",
        "api": m.get("api") or {},
    }
    _FAST_CACHE = doc
    _FAST_TS = now
    _save_json(CACHE, doc)
    return doc


def secure_channel_status(*, full: bool = False) -> dict[str, Any]:
    m = load_mandate()
    seal = _queen_seal()
    if not seal.get("ok") and (m.get("doctrine") or {}).get("fail_closed_on_seal_break", True):
        return {
            "ok": False,
            "verdict": "SEAL_BROKEN",
            "forever": False,
            "seal": seal,
            "fast_fallback": secure_channel_fast(),
        }
    base = secure_channel_fast()
    if not full:
        return {"ok": True, **base}
    return {
        "ok": True,
        **base,
        "fast": False,
        "full": True,
        "quarantine_log": str(QUARANTINE_LOG),
        "quarantine_lines": QUARANTINE_LOG.read_text(encoding="utf-8").count("\n") if QUARANTINE_LOG.is_file() else 0,
    }


def _delegate_external(body: dict[str, Any], *, remote_ip: str = "", action: str) -> dict[str, Any]:
    ew = _load_mod("queen_external_wire", "queen-external-wire.py")
    if ew is None:
        return {"ok": False, "error": "external_wire_missing", "lane": "SecureChannel"}
    payload = {**body, "action": action}
    if action == "receive":
        return ew.receive_external(payload, remote_ip=remote_ip)
    return ew.speak_external(payload, remote_ip=remote_ip)


def dispatch(body: dict[str, Any], *, remote_ip: str = "") -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    full = bool(body.get("full"))
    if action in ("status", "json", "fast"):
        if action == "fast" or not full:
            return {"ok": True, **secure_channel_fast()}
        return secure_channel_status(full=True)
    if action in ("scan", "threat", "weapons"):
        return threat_scan(body, remote_ip=remote_ip, direction=str(body.get("direction") or "inbound"))
    if action in ("verify", "integrity"):
        seal = _queen_seal()
        ew = _load_mod("queen_external_wire", "queen-external-wire.py")
        chain = {"ok": False}
        if ew is not None:
            try:
                chain = ew.dispatch({"action": "verify"})
            except Exception:
                pass
        return {
            "ok": bool(seal.get("ok") and chain.get("never_tampered_or_broken", chain.get("ok"))),
            "lane": "SecureChannel",
            "forever": seal.get("ok"),
            "seal": seal,
            "external_chain": chain,
            "never_tampered_or_broken": seal.get("ok") and chain.get("never_tampered_or_broken", chain.get("ok")),
        }
    if action in ("receive", "ground", "ingest", "contact"):
        gate = gate_message(body, direction="inbound", remote_ip=remote_ip)
        if not gate.get("ok"):
            return gate
        out = _delegate_external(body, remote_ip=remote_ip, action="receive")
        out["secure_channel"] = gate.get("scan")
        out["lane"] = "SecureChannel"
        return out
    if action in ("speak", "send", "transmit"):
        gate = gate_message(body, direction="outbound", remote_ip=remote_ip)
        if not gate.get("ok"):
            return gate
        out = _delegate_external(body, remote_ip=remote_ip, action="speak")
        out["secure_channel"] = gate.get("scan")
        out["lane"] = "SecureChannel"
        return out
    if action == "repack":
        return {"ok": True, "world_repack": _repack_health()}
    if action == "redata":
        return {"ok": True, "world_redata": _redata_slice()}
    return {"ok": False, "error": "unknown_action", "action": action, "lane": "SecureChannel"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(secure_channel_fast(), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        remote = str(body.pop("remote_ip", "") or "")
        print(json.dumps(dispatch(body, remote_ip=remote), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-secure-channel.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())