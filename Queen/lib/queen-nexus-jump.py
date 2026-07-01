#!/usr/bin/env pythong
"""Queen NEXUS Jump — safe quick security at every navigation boundary.

We are never afraid: every jump arms countermeasures before the wire moves.
Hooks FieldNet classify, honorability, telemetry gate, web compat cage, packet field.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
JUMP_LOG = STATE / "queen-nexus-jump.jsonl"

_HARM_SCHEMES = frozenset({"javascript", "vbscript", "jar"})
_HARM_PATH_RE = re.compile(
    r"(eval\s*\(|document\.write\s*\(|<script|onerror\s*=|onload\s*=|\.exe\b|\.dll\b)",
    re.I,
)
_DATA_SCRIPT_RE = re.compile(r"<script|javascript:", re.I)

IFF_DOCTRINE = {
    "presume_hostile": True,
    "never_presume_correct_contact": True,
    "positive_id_required_for_civilian": True,
    "defend_by_default": True,
    "offense_on_threat": True,
    "motto": "Every contact hostile until positively identified. Defend always. Offense when threatened.",
}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _nexus_install() -> Path:
    for p in (
        Path(os.environ.get("NEXUS_INSTALL_ROOT", "")),
        SG / "NewLatest",
        QUEEN.parent,
        SG / "Latest" / "NEXUS-Shield",
    ):
        if p.is_dir() and (p / "lib" / "field-queen-browser.py").is_file():
            return p
    return SG / "NewLatest"


def _load_mod(name: str, path: Path) -> Any | None:
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


def _queen_mod(name: str, rel: str) -> Any | None:
    return _load_mod(name, QUEEN / "lib" / rel)


def _nexus_mod(name: str, rel: str) -> Any | None:
    return _load_mod(name, _nexus_install() / "lib" / rel)


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _append_jump(entry: dict[str, Any]) -> None:
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with JUMP_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _harm_heuristics(url: str) -> tuple[int, list[str]]:
    u = (url or "").strip()
    score = 0
    reasons: list[str] = []
    try:
        parsed = urlparse(u)
    except Exception:
        return 10, ["malformed_url"]
    scheme = (parsed.scheme or "").lower()
    if scheme in _HARM_SCHEMES:
        score += 15
        reasons.append(f"harm_scheme:{scheme}")
    if scheme == "data" and _DATA_SCRIPT_RE.search(parsed.path or u):
        score += 12
        reasons.append("data_script_injection")
    if scheme == "file":
        score += 4
        reasons.append("file_uri")
    path_q = (parsed.path or "") + "?" + (parsed.query or "")
    if _HARM_PATH_RE.search(path_q):
        score += 8
        reasons.append("suspicious_path_or_query")
    blob = u.lower()
    for marker in ("cryptominer", "coinhive", "keylogger", "pastebin.com/raw"):
        if marker in blob:
            score += 6
            reasons.append(f"marker:{marker}")
    return score, reasons


def _code_seal_ok() -> bool:
    sec = _queen_mod("queen_security", "queen-security.py")
    if sec is None:
        return False
    try:
        return bool(sec.verify_code_seal().get("ok"))
    except Exception:
        return False


def _positive_identification(
    url: str,
    field_net: dict[str, Any],
    honor: dict[str, Any],
    *,
    harm_score: int,
) -> tuple[bool, str]:
    """Never presume correct contact — civilian only after explicit positive ID."""
    if harm_score >= 8:
        return False, "harm_score_blocks_civilian"
    layer = field_net.get("layer") or ""
    verdict = field_net.get("verdict") or ""
    if verdict in ("ALLOW_INTERNAL", "ALLOW_LOOPBACK", "ALLOW_LOCAL") and layer in (
        "queen_scheme",
        "loopback",
        "local",
        "blank",
    ):
        if _code_seal_ok():
            return True, "capsule_sealed_internal"
    if honor.get("gold") and honor.get("accepted") and not honor.get("needs_acceptance"):
        if int(honor.get("stars") or 0) >= 5:
            return True, "honor_gold_operator_accepted"
    return False, "no_positive_id_presume_hostile"


def _under_threat(
    *,
    harm_score: int,
    iff: str,
    honor: dict[str, Any],
    telemetry: dict[str, Any],
    field_net: dict[str, Any],
) -> tuple[bool, list[str]]:
    signals: list[str] = []
    if harm_score >= 6:
        signals.append("harm_score_elevated")
    if iff in ("HOSTILE", "UNKNOWN", "CONTACT_HOSTILE"):
        signals.append("iff_not_civilian")
    if honor.get("needs_acceptance"):
        signals.append("honor_unverified")
    if telemetry.get("verdict") not in ("ALLOW", "ALLOW_AI_SECURE", None):
        signals.append(f"telemetry:{telemetry.get('verdict')}")
    if field_net.get("verdict") == "BLOCK_EXTERNAL":
        signals.append("external_probe")
    if not honor.get("gold") and _host(str(field_net.get("url") or "")):
        signals.append("untrusted_host")
    return len(signals) >= 1, signals


def _countermeasures(
    *,
    verdict: str,
    harm_score: int,
    legacy: bool,
    honor_needs_acceptance: bool,
    iff: str,
    under_threat: bool,
    offense_active: bool,
) -> list[dict[str, Any]]:
    cms = [
        {
            "id": "presume_hostile",
            "ready": True,
            "label": "Presume hostile — never trust contact without positive ID",
        },
        {
            "id": "legacy_cage",
            "ready": True,
            "label": "Legacy secure cage — old JS isolated from OS/memory",
        },
        {
            "id": "gatekeeper_segment",
            "ready": True,
            "label": "Connection gatekeeper — segment block on harmful egress",
        },
        {
            "id": "packet_field_receipt",
            "ready": True,
            "label": "Packet field — jsonl receipt per jump",
        },
        {
            "id": "hostess7_witness",
            "ready": True,
            "label": "Hostess 7 Forever Watchguard — truth on harmful intent",
        },
        {
            "id": "honorability_hold",
            "ready": True,
            "label": "Honorability hold — positive ID required; never presume correct contact",
        },
        {
            "id": "defense_posture",
            "ready": True,
            "label": "Defend by default — cage every jump",
        },
        {
            "id": "proxy_cage",
            "ready": True,
            "label": "Queen proxy cage — render without host OS wire",
        },
        {
            "id": "sense_neural_quarantine",
            "ready": harm_score >= 6 or under_threat,
            "label": "Sense neural quarantine — weaponized encouragement blocked",
        },
        {
            "id": "ear_countermeasure",
            "ready": under_threat or iff == "HOSTILE",
            "label": "Final Ear countermeasure — spoof / ventriloquism defense",
        },
        {
            "id": "final_eye_offense",
            "ready": offense_active,
            "label": "Final_Eye offense lane — strike when brought under threat",
        },
        {
            "id": "trust_strike_ready",
            "ready": offense_active and harm_score >= 10,
            "label": "Trust strike engine — offense tier armed",
        },
        {
            "id": "kill_detect_hold",
            "ready": harm_score >= 10 or offense_active,
            "label": "Kill-detect — interdict without hesitation if corroborated",
        },
        {
            "id": "host_attack_map",
            "ready": offense_active,
            "label": "Host attack map — globe pin on threat contact",
        },
    ]
    if verdict == "BLOCK_HOSTILE":
        cms.insert(0, {
            "id": "jump_denied",
            "ready": True,
            "label": "Jump denied — hostile confirmed; wire not moved",
        })
    return cms


def _benchmark_mod() -> Any | None:
    return _queen_mod("queen_benchmark", "queen-benchmark.py")


def nexus_jump(
    url: str,
    *,
    tab_id: str = "",
    compat_mode: str = "auto",
    proc: str = "queen-browser",
) -> dict[str, Any]:
    u = (url or "").strip()
    host = _host(u)

    bench = _benchmark_mod()
    if bench is not None and hasattr(bench, "fast_jump"):
        fast = bench.fast_jump(u, tab_id=tab_id, compat_mode=compat_mode)
        if fast:
            _append_jump({**fast, "ts": _ts(), "event": "nexus_jump_fast"})
            return fast

    # FieldNet classify (Queen capsule boundary)
    field_net: dict[str, Any] = {}
    fn = _queen_mod("queen_field_net", "queen-field-net.py")
    if fn is not None:
        try:
            field_net = fn.classify_url(u)
        except Exception as exc:
            field_net = {"error": str(exc)}

    # Web compat profile (auto cage at jump)
    compat: dict[str, Any] = {}
    wc = _queen_mod("queen_web_compat", "queen-web-compat.py")
    if wc is not None:
        try:
            compat = wc.resolve_profile(u, mode=compat_mode)
        except Exception as exc:
            compat = {"error": str(exc)}

    # NEXUS honorability + telemetry
    honor: dict[str, Any] = {"stars": 3, "needs_acceptance": False}
    telemetry: dict[str, Any] = {"verdict": "ALLOW"}
    fqb = _nexus_mod("field_queen_browser", "field-queen-browser.py")
    if fqb is not None and host:
        try:
            honor_mod = _nexus_mod("honorability_db", "honorability-db.py")
            if honor_mod is not None:
                honor = honor_mod.lookup(host)
            telemetry = fqb.gate_telemetry_host(host, proc=proc)
        except Exception:
            pass

    harm_score, harm_reasons = _harm_heuristics(u)
    # Presume hostile — never default to CIVILIAN
    iff = "CONTACT_HOSTILE"
    legacy = bool(compat.get("legacy_isolate")) or (compat.get("era") or {}).get("year", 2026) < 2005

    positive_id, id_reason = _positive_identification(
        u, field_net, honor, harm_score=harm_score,
    )
    if positive_id:
        iff = "CIVILIAN_IDENTIFIED"
    elif field_net.get("internal"):
        iff = "CAPSULE_INTERNAL"
    else:
        iff = "CONTACT_HOSTILE"

    threatened, threat_signals = _under_threat(
        harm_score=harm_score,
        iff=iff,
        honor=honor,
        telemetry=telemetry,
        field_net=field_net,
    )
    offense_active = threatened or harm_score >= 8 or iff == "HOSTILE"

    permit = True
    verdict = "DEFEND_CAGED"
    block_reason = ""
    posture = "defend"

    if field_net.get("verdict") == "BLOCK_EXTERNAL":
        permit = False
        verdict = "BLOCK_HOSTILE"
        iff = "HOSTILE"
        posture = "interdict"
        block_reason = field_net.get("reason") or "external_blocked"
        offense_active = True
    elif telemetry.get("verdict") in ("BLOCK_TELEMETRY", "BLOCK_SOVEREIGN"):
        permit = False
        verdict = "BLOCK_HOSTILE"
        iff = "HOSTILE"
        posture = "interdict"
        block_reason = telemetry.get("reason") or telemetry.get("verdict", "")
        offense_active = True
    elif harm_score >= 14:
        permit = False
        verdict = "BLOCK_HOSTILE"
        iff = "HOSTILE"
        posture = "interdict"
        block_reason = "; ".join(harm_reasons) or "harm_heuristic"
        offense_active = True
    elif offense_active:
        verdict = "OFFENSE_ACTIVE"
        posture = "offense"
        compat_mode_eff = "legacy_secure"
        if compat.get("effective_mode"):
            compat["effective_mode"] = compat_mode_eff
    elif positive_id:
        verdict = "DEFEND_IDENTIFIED"
        posture = "defend_identified"
    elif legacy or compat.get("effective_mode") in ("legacy_secure", "archaeology"):
        verdict = "DEFEND_CAGED"
    elif harm_score >= 4 or honor.get("needs_acceptance"):
        verdict = "DEFEND_CAGED"

    countermeasures = _countermeasures(
        verdict=verdict,
        harm_score=harm_score,
        legacy=legacy,
        honor_needs_acceptance=True,
        iff=iff,
        under_threat=threatened,
        offense_active=offense_active,
    )

    doc = {
        "schema": "queen-nexus-jump/v1",
        "updated": _ts(),
        "ok": True,
        "permit": permit,
        "verdict": verdict,
        "iff": iff,
        "posture": posture,
        "offense_active": offense_active,
        "positive_id": positive_id,
        "positive_id_reason": id_reason,
        "threat_signals": threat_signals,
        "iff_doctrine": IFF_DOCTRINE,
        "motto": IFF_DOCTRINE["motto"],
        "jump": {
            "url": u,
            "host": host,
            "tab_id": tab_id,
            "layer": field_net.get("layer") or "navigation",
            "resolved": field_net.get("resolved"),
        },
        "harm": {"score": harm_score, "reasons": harm_reasons},
        "nexus": {
            "field_net": field_net,
            "honor": honor,
            "telemetry": telemetry,
            "gatekeeper": True,
            "packet_field": True,
            "browser_awareness": True,
        },
        "compat": {
            "mode": compat.get("mode"),
            "effective_mode": compat.get("effective_mode"),
            "era": (compat.get("era") or {}).get("id"),
            "legacy_isolate": compat.get("legacy_isolate"),
            "sandbox": compat.get("sandbox"),
        },
        "countermeasures": countermeasures,
        "countermeasures_ready": sum(1 for c in countermeasures if c.get("ready")),
    }
    if not permit:
        doc["ok"] = False
        doc["error"] = "nexus_jump_blocked"
        doc["reason"] = block_reason
        doc["hint"] = field_net.get("hint") or "Stay inside Queen — queen:// or loopback."

    _append_jump({
        "ts": doc["updated"],
        "url": u,
        "host": host,
        "verdict": verdict,
        "permit": permit,
        "iff": iff,
        "harm_score": harm_score,
        "tab_id": tab_id,
    })
    return doc


def jump_status() -> dict[str, Any]:
    return {
        "schema": "queen-nexus-jump/v1",
        "updated": _ts(),
        "motto": "Safe quick security at the jump — NEXUS + FieldNet + compat cage.",
        "doctrine": {
            **IFF_DOCTRINE,
            "never_afraid": True,
            "countermeasures_always_armed": True,
            "harm_addressed_at_jump": True,
            "serve_and_listen": True,
        },
        "bindings": {
            "field_net": "queen-field-net.py",
            "web_compat": "queen-web-compat.py",
            "connection_gatekeeper": "connection-gatekeeper.py",
            "honorability": "honorability-db.py",
            "packet_field": "packet-field.py",
            "hostess7": "hostess7-command.py",
        },
        "log": str(JUMP_LOG),
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "jump").strip().lower().replace("-", "_")
    if action in ("status", "json"):
        return {"ok": True, **jump_status()}
    if action in ("jump", "navigate", "gate"):
        return nexus_jump(
            str(body.get("url") or ""),
            tab_id=str(body.get("tab_id") or ""),
            compat_mode=str(body.get("compat_mode") or body.get("mode") or "auto"),
            proc=str(body.get("proc") or "queen-browser"),
        )
    if action == "jump_and_resolve":
        jump = nexus_jump(
            str(body.get("url") or ""),
            tab_id=str(body.get("tab_id") or ""),
            compat_mode=str(body.get("compat_mode") or "auto"),
        )
        if not jump.get("permit"):
            return jump
        resolved = jump.get("jump", {}).get("resolved") or body.get("url")
        if fn := _queen_mod("queen_field_net", "queen-field-net.py"):
            try:
                c = fn.classify_url(str(body.get("url") or ""))
                resolved = c.get("resolved") or resolved
            except Exception:
                pass
        jump["resolved"] = resolved
        return jump
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "jump" and len(sys.argv) > 2:
        print(json.dumps(nexus_jump(sys.argv[2]), ensure_ascii=False))
        return 0
    print(json.dumps(jump_status(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())