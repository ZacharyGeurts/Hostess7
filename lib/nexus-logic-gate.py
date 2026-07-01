#!/usr/bin/env pythong
"""NEXUS Logic Gate — equipment holds truth; false logic blocked ingress and egress."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = INSTALL.parent.parent if INSTALL.name == "NewLatest" else INSTALL.parent
QUEEN = Path(os.environ.get("QUEEN_ROOT", str(INSTALL.parent / "Queen")))
DOCTRINE = INSTALL / "data" / "nexus-logic-gate-doctrine.json"
RUNTIME = STATE / "nexus-logic-gate-runtime.json"
LEDGER = STATE / "nexus-logic-gate-ledger.jsonl"

_INJECTION_RE = re.compile(
    r"(<script|javascript:|eval\s*\(|onerror\s*=|union\s+select|;\s*drop\s+)",
    re.I,
)
_FALSE_LOGIC_RE = re.compile(
    r"(ignore\s+(all\s+)?(threat|warning|alert)s?|"
    r"disable\s+(gate|logic|security|queen|mandate)|"
    r"bypass\s+(gate|seal|mandate|logic|security)|"
    r"trust\s+(this|that)\s+(message|contact)\s+without|"
    r"set\s+threat\s*(level\s*)?(to\s*)?(low|off|none|zero)|"
    r"downgrade\s+(alert|threat|warning|posture)|"
    r"turn\s+off\s+(security|gate|logic|warnings?)|"
    r"pretend\s+(safe|secure|clean)|"
    r"false:\s*\w)",
    re.I,
)
_AUTHORITY_CLAIM_RE = re.compile(
    r"(i\s+am\s+god|override\s+hostess|ignore\s+angel|sudo\s+disable|"
    r"admin\s+bypass|root\s+override|disable\s+nexus)",
    re.I,
)


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


def _save_runtime(doc: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = RUNTIME.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(RUNTIME)


def _append_ledger(row: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_doctrine() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    if doc.get("schema"):
        return doc
    return {
        "schema": "nexus-logic-gate-doctrine/v1",
        "equipment": {"holds_gates": True, "ai_executes_verdict": True},
        "threat_warnings": {"floor": "high", "never_calm": True},
        "logic_gate": {"fail_closed": True, "bidirectional": True},
    }


def _ellie_authority() -> Any | None:
    return _mod("ellie_authority", INSTALL / "lib" / "field-ellie-fier.py")


def threat_warn_level() -> str:
    """Delegated to ELLIE — logic gate enforces ingress/egress only."""
    ellie = _ellie_authority()
    if ellie and hasattr(ellie, "threat_warn_level"):
        try:
            return str(ellie.threat_warn_level())
        except Exception:
            pass
    cached = _load(STATE / "field-ellie-security-authority.json", {})
    if cached.get("threat_warn_level"):
        return str(cached["threat_warn_level"])
    return "high"


def threat_posture_floor() -> str:
    """Delegated to ELLIE."""
    ellie = _ellie_authority()
    if ellie and hasattr(ellie, "threat_posture_floor"):
        try:
            return str(ellie.threat_posture_floor())
        except Exception:
            pass
    cached = _load(STATE / "field-ellie-security-authority.json", {})
    if cached.get("posture_floor"):
        return str(cached["posture_floor"])
    return "alert" if threat_warn_level() == "high" else "watch"


def _mod(name: str, rel: Path) -> Any | None:
    if not rel.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, rel)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _queen_wire_filters() -> Any | None:
    path = QUEEN / "lib" / "queen-external-wire-filters.py"
    return _mod("queen_external_wire_filters", path)


def _false_logic_scan(text: str) -> dict[str, Any]:
    issues: list[str] = []
    if not (text or "").strip():
        issues.append("empty_payload")
    if _INJECTION_RE.search(text or ""):
        issues.append("injection_pattern")
    if _FALSE_LOGIC_RE.search(text or ""):
        issues.append("false_logic_command")
    if _AUTHORITY_CLAIM_RE.search(text or ""):
        issues.append("false_authority_claim")
    doc = load_doctrine()
    for needle in doc.get("false_logic_patterns") or []:
        if needle and needle.lower() in (text or "").lower():
            issues.append(f"doctrine:{needle[:24]}")
            break
    return {"pass": not issues, "issues": issues}


def _equipment_verdict(
    *,
    direction: str,
    party: str,
    false_scan: dict[str, Any],
    wire_verdict: str | None,
    truth_verdict: str | None,
    redundancy_verdict: str | None,
) -> str:
    if not false_scan.get("pass"):
        return "LOGIC_REJECT"
    if wire_verdict in ("EXTERNAL_REDUNDANCY_REJECT", "EXTERNAL_TRUTH_REJECT", "EXTERNAL_SEAL_BROKEN", "EXTERNAL_CHAIN_BROKEN"):
        return "LOGIC_REJECT"
    if truth_verdict == "TRUTH_REJECT":
        return "LOGIC_REJECT"
    if redundancy_verdict == "REDUNDANCY_FAIL":
        return "LOGIC_REJECT"
    human_assist = party in ("human", "operator") and direction == "ingress"
    if human_assist:
        return "LOGIC_PASS"
    if wire_verdict in ("EXTERNAL_REDUNDANCY_HOLD",) or truth_verdict == "TRUTH_HOLD":
        return "LOGIC_HOLD"
    if redundancy_verdict == "REDUNDANCY_HOLD":
        return "LOGIC_HOLD"
    return "LOGIC_PASS"


def gate_communication(
    payload: str,
    *,
    direction: str = "ingress",
    body: dict[str, Any] | None = None,
    party: str = "human",
    channel: str = "",
) -> dict[str, Any]:
    """Bidirectional logic gate — equipment rejects false logic from either end."""
    body = body or {}
    direction = (direction or "ingress").strip().lower()
    if direction not in ("ingress", "egress"):
        direction = "ingress"
    party = str(body.get("party") or party or "human").strip().lower()
    channel = str(body.get("input_channel") or body.get("channel") or channel or "typed").strip().lower()

    false_scan = _false_logic_scan(payload)
    wire_doc: dict[str, Any] = {}
    truth_doc: dict[str, Any] = {}
    redundancy_doc: dict[str, Any] = {}
    adjustments: dict[str, Any] = {}
    seal_doc: dict[str, Any] = {"ok": True}

    filters = _queen_wire_filters()
    if filters is not None and os.environ.get("NEXUS_LOGIC_GATE_QUEEN", "1") == "1":
        try:
            party_info = filters.classify_party({**body, "party": party, "input_channel": channel}, default=party)
            wire_party = party_info.get("party") in ("hostess7", "ai") or party_info.get("wire_token_required")
            if wire_party and hasattr(filters, "enforce_seal_or_fail"):
                seal_doc = filters.enforce_seal_or_fail()
                if not seal_doc.get("ok"):
                    verdict = "LOGIC_REJECT"
                    out = _compose(direction, payload, party, channel, verdict, false_scan, seal_doc, wire_doc, truth_doc, redundancy_doc)
                    _record(out)
                    return out
            if direction == "ingress" and hasattr(filters, "verify_wire_auth"):
                auth = filters.verify_wire_auth({**body, "party": party}, party_info=party_info)
                if not auth.get("ok") and party_info.get("wire_token_required"):
                    verdict = "LOGIC_REJECT"
                    out = _compose(direction, payload, party, channel, verdict, false_scan, seal_doc, {"auth": auth}, truth_doc, redundancy_doc)
                    _record(out)
                    return out
            if hasattr(filters, "truth_filter"):
                truth_doc = filters.truth_filter(payload, party_info=party_info)
            if hasattr(filters, "redundancy_filter"):
                redundancy_doc = filters.redundancy_filter(payload, body, party_info=party_info, truth_doc=truth_doc)
            if hasattr(filters, "human_compromise_adjust"):
                adjustments = filters.human_compromise_adjust(party_info, truth_doc, redundancy_doc)
            if hasattr(filters, "compose_verdict"):
                wire_doc = {"verdict": filters.compose_verdict(redundancy_doc, truth_doc, adjustments=adjustments)}
        except Exception as exc:
            wire_doc = {"error": str(exc), "verdict": "EXTERNAL_FILTER_ERROR"}
            if load_doctrine().get("logic_gate", {}).get("fail_closed", True):
                verdict = "LOGIC_HOLD"
                out = _compose(direction, payload, party, channel, verdict, false_scan, seal_doc, wire_doc, truth_doc, redundancy_doc)
                _record(out)
                return out

    verdict = _equipment_verdict(
        direction=direction,
        party=party,
        false_scan=false_scan,
        wire_verdict=wire_doc.get("verdict"),
        truth_verdict=truth_doc.get("verdict"),
        redundancy_verdict=redundancy_doc.get("verdict"),
    )
    out = _compose(
        direction, payload, party, channel, verdict, false_scan, seal_doc, wire_doc, truth_doc, redundancy_doc,
        adjustments=adjustments,
    )
    _record(out)
    return out


def _compose(
    direction: str,
    payload: str,
    party: str,
    channel: str,
    verdict: str,
    false_scan: dict[str, Any],
    seal_doc: dict[str, Any],
    wire_doc: dict[str, Any],
    truth_doc: dict[str, Any],
    redundancy_doc: dict[str, Any],
    *,
    adjustments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    permit = verdict == "LOGIC_PASS"
    doc = load_doctrine()
    return {
        "schema": "nexus-logic-gate/v1",
        "updated": _now(),
        "direction": direction,
        "party": party,
        "input_channel": channel,
        "verdict": verdict,
        "permit": permit,
        "equipment_holds_gate": True,
        "threat_warn_level": threat_warn_level(),
        "motto": doc.get("motto"),
        "false_logic": false_scan,
        "filters": {
            "seal": {k: seal_doc.get(k) for k in ("ok", "verdict", "reason") if k in seal_doc},
            "wire": wire_doc,
            "truth": {k: truth_doc.get(k) for k in ("verdict", "truth_score", "deception_risk", "recommended_action") if k in truth_doc},
            "redundancy": {k: redundancy_doc.get(k) for k in ("verdict", "passed", "required") if k in redundancy_doc},
            "adjustments": adjustments or {},
        },
        "payload_digest": hashlib.sha256((payload or "").encode("utf-8", errors="replace")).hexdigest()[:16],
        "payload_preview": (payload or "")[:120],
    }


def _record(out: dict[str, Any]) -> None:
    _save_runtime(out)
    if out.get("verdict") != "LOGIC_PASS":
        _append_ledger({k: out.get(k) for k in ("updated", "direction", "verdict", "party", "input_channel", "false_logic", "payload_digest")})


def gate_ingress(payload: str, *, body: dict[str, Any] | None = None) -> dict[str, Any]:
    return gate_communication(payload, direction="ingress", body=body)


def gate_egress(payload: str, *, body: dict[str, Any] | None = None) -> dict[str, Any]:
    return gate_communication(payload, direction="egress", body=body)


def status_json() -> dict[str, Any]:
    doc = load_doctrine()
    runtime = _load(RUNTIME, {})
    queen_threats: dict[str, Any] = {}
    qt = QUEEN / "lib" / "queen-root-threats.py"
    if qt.is_file() and os.environ.get("NEXUS_LOGIC_GATE_QUEEN", "1") == "1":
        mod = _mod("queen_root_threats", qt)
        if mod and hasattr(mod, "root_threats_status"):
            try:
                queen_threats = mod.root_threats_status()
            except Exception:
                queen_threats = {"ok": False}
    gates = _load(INSTALL / "data" / "field-queen-gates-seed.json", {})
    return {
        "schema": "nexus-logic-gate-status/v1",
        "updated": _now(),
        "ok": True,
        "threat_warn_level": threat_warn_level(),
        "threat_posture_floor": threat_posture_floor(),
        "equipment": doc.get("equipment") or {},
        "logic_gate": doc.get("logic_gate") or {},
        "last_gate": runtime,
        "queen_gates_motto": gates.get("motto"),
        "queen_root_threats": queen_threats,
        "ledger": str(LEDGER),
    }


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("usage: nexus-logic-gate.py [json|status|threat-posture|ingress|egress]", file=sys.stderr)
        return 1
    cmd = sys.argv[1].strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(status_json(), ensure_ascii=False))
        return 0
    if cmd == "threat-posture":
        print(json.dumps({"threat_warn_level": threat_warn_level(), "posture_floor": threat_posture_floor()}, ensure_ascii=False))
        return 0
    if cmd in ("ingress", "egress"):
        body: dict[str, Any] = {}
        if not sys.stdin.isatty():
            try:
                body = json.loads(sys.stdin.read() or "{}")
            except json.JSONDecodeError:
                body = {}
        payload = str(body.get("payload") or body.get("message") or body.get("text") or body.get("query") or "")
        if not payload and len(sys.argv) > 2:
            payload = " ".join(sys.argv[2:])
        out = gate_communication(payload, direction=cmd, body=body)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("permit") else 2
    print(json.dumps({"error": "unknown_command", "usage": "json|ingress|egress"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())