#!/usr/bin/env pythong
"""NEXUS kill codes — unified removal, disablement, and operator strike catalog."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parent.parent))
POLICY_PATH = INSTALL / "data" / "lethal-enforcement-policy.json"
KILL_LAW_PATH = INSTALL / "data" / "kill-immediate-law.json"
TOOLKIT_SEED = INSTALL / "data" / "field-toolkit-seed.json"

_CODE_RE = re.compile(r"^KC-[A-Z]{2}-[a-z0-9_]{1,48}$")
_IP_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
    r"|^[0-9a-fA-F:.]{2,45}$"
)

# Operator strike codes (above-military — friendly-guard honored on wire kills)
_OPERATOR_CODES: list[dict[str, Any]] = [
    {
        "code": "KC-OP-strike_certain",
        "label": "PINPOINT CERTAIN · hardware destroy",
        "tier": "lethal",
        "plain": "100% strike certainty — permanent kill + hardware destroy when wire locked.",
        "api": "/api/attack-kit/kill",
        "body_template": {"reason": "strike_certain:operator", "severity": "critical"},
        "requires_ip": True,
        "rank": 95,
    },
    {
        "code": "KC-OP-kill",
        "label": "Trust Strike KILL",
        "tier": "lethal",
        "plain": "Permanent kill at Trust Strike floor — firewall, teardown, dossier.",
        "api": "/api/attack-kit/kill",
        "body_template": {"reason": "target_kill:operator", "severity": "high"},
        "requires_ip": True,
        "rank": 88,
    },
    {
        "code": "KC-OP-rekill",
        "label": "RE-KILL returner",
        "tier": "lethal",
        "plain": "Same hostile host returned — identity markers matched archived dossier.",
        "api": "/api/attack-kit/rekill",
        "body_template": {"severity": "critical"},
        "requires_ip": True,
        "rank": 86,
    },
    {
        "code": "KC-OP-sever",
        "label": "Sever wire · 24h block",
        "tier": "urgent",
        "plain": "Tear down live sessions + temp firewall — wire cut without forever unless escalated.",
        "api": "/api/field-toolkit/sever",
        "body_template": {"vector": "HELL_SEVER", "severity": "high", "reason": "kill_code_sever"},
        "requires_ip": True,
        "rank": 72,
    },
    {
        "code": "KC-OP-human_threat",
        "label": "Human threat sweep",
        "tier": "lethal",
        "plain": "Grok Heavy kill-order dossier sweep — C2 human threat itself.",
        "api": "/api/field-toolkit/human-threat",
        "body_template": {},
        "requires_ip": False,
        "rank": 80,
    },
    {
        "code": "KC-OP-regional",
        "label": "Regional disable cluster",
        "tier": "lethal",
        "plain": "Batch disable hostile cluster by region/ASN — Hell goes to Hell for the patch.",
        "api": "/api/field-toolkit/regional-disable",
        "body_template": {"field": "region", "disable_mode": "forever"},
        "requires_ip": False,
        "requires_region": True,
        "rank": 78,
    },
    {
        "code": "KC-OP-laser",
        "label": "Laser corridor slice",
        "tier": "lethal",
        "plain": "Undodgeable corridor — sever wire, block both directions, strike at certainty.",
        "api": "/api/field-toolkit/laser-corridor",
        "body_template": {"vector": "LASER_CORRIDOR", "severity": "critical"},
        "requires_ip": True,
        "rank": 90,
    },
    {
        "code": "KC-OP-crush_hot",
        "label": "Crush hot targets",
        "tier": "urgent",
        "plain": "Autokill all map-hot harm candidates at strike floor.",
        "api": "/api/attack-kit/crush-hot",
        "body_template": {},
        "requires_ip": False,
        "rank": 70,
    },
    {
        "code": "KC-OP-nokill",
        "label": "NO-KILL exempt",
        "tier": "watch",
        "plain": "Exempt IP from autokill and crush — monitor only. Heaven guard.",
        "api": "/api/attack-kit/nokill",
        "body_template": {"reason": "operator_nokill", "severity": "high"},
        "requires_ip": True,
        "rank": 10,
    },
    {
        "code": "KC-OP-lethal_cycle",
        "label": "MERCILESS lethal cycle",
        "tier": "lethal",
        "plain": "Full heaven/hell spatial cycle — shoot-to-kill trespass at adequate removal.",
        "api": "/api/lethal-enforcement/cycle",
        "body_template": {},
        "requires_ip": False,
        "rank": 92,
    },
]

# Vigilance codes — hostile injection / unverified field text
_VIGILANCE_CODES: list[dict[str, Any]] = [
    {
        "code": "KC-VG-text_injection",
        "label": "Hostile text injection",
        "tier": "investigate",
        "plain": "Unsolicited field text presumed terrorist injection — verify before trust.",
        "jump": "packets/inspect",
        "rank": 65,
    },
    {
        "code": "KC-VG-packet_inject",
        "label": "Packet injection / MITM",
        "tier": "urgent",
        "plain": "On-path manipulation — DPI block harmful segments, sever wire.",
        "api": "/api/field-toolkit/sever",
        "body_template": {"vector": "PACKET_INJECT", "severity": "critical"},
        "requires_ip": True,
        "rank": 75,
    },
    {
        "code": "KC-VG-identify",
        "label": "Identify unknown · kill orders",
        "tier": "urgent",
        "plain": "Unidentified entity — dossier and classify before block.",
        "jump": "threats/human-dossier",
        "rank": 68,
    },
]


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


def _import_mod(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _sanitize_ip(ip: Any) -> str:
    raw = str(ip or "").strip()[:64]
    return raw if _IP_RE.match(raw) else ""


def _removal_codes() -> list[dict[str, Any]]:
    policy = _load_json(POLICY_PATH, {})
    levels = policy.get("removal_levels") or {}
    out: list[dict[str, Any]] = []
    for key, spec in levels.items():
        if not isinstance(spec, dict):
            continue
        rank = int(spec.get("rank") or 0)
        out.append({
            "code": f"KC-RM-{key}",
            "label": spec.get("label") or key.replace("_", " ").title(),
            "tier": "lethal" if rank >= 6 else "urgent" if rank >= 4 else "watch",
            "plain": f"MERCILESS removal level {key} — rank {rank}.",
            "removal_level": key,
            "rank": rank + 50,
            "family": "removal",
        })
    return sorted(out, key=lambda c: -int(c.get("rank") or 0))


def _disablement_codes() -> list[dict[str, Any]]:
    seed = _load_json(TOOLKIT_SEED, {})
    out: list[dict[str, Any]] = []
    for prof in seed.get("disablement_profiles") or []:
        if not isinstance(prof, dict):
            continue
        pid = str(prof.get("id") or "")
        if not pid:
            continue
        sev = str(prof.get("severity") or "high")
        tier = "lethal" if sev == "critical" else "urgent"
        entry: dict[str, Any] = {
            "code": f"KC-DM-{pid}",
            "label": prof.get("label") or pid,
            "tier": tier,
            "plain": str(prof.get("description") or "")[:280],
            "disablement": pid,
            "mode": prof.get("mode") or pid,
            "vector": prof.get("vector") or "",
            "rank": 60 if sev == "critical" else 45,
            "family": "disablement",
        }
        api_map = {
            "sever_wire": "/api/field-toolkit/sever",
            "regional_disable": "/api/field-toolkit/regional-disable",
            "human_threat": "/api/field-toolkit/human-threat",
            "hell_rip": "/api/field-toolkit/hell-rip",
            "field_die": "/api/field-toolkit/field-die",
            "laser_corridor": "/api/field-toolkit/laser-corridor",
            "forever_kill": "/api/attack-kit/kill",
        }
        if pid in api_map:
            entry["api"] = api_map[pid]
            if pid == "forever_kill":
                entry["body_template"] = {"reason": "forever_kill:kill_code", "severity": "critical"}
                entry["requires_ip"] = True
            elif pid == "sever_wire":
                entry["body_template"] = {"vector": prof.get("vector") or "HELL_SEVER", "severity": sev}
                entry["requires_ip"] = True
        out.append(entry)
    return out


def _all_codes() -> list[dict[str, Any]]:
    pool = _removal_codes() + _disablement_codes() + _OPERATOR_CODES + _VIGILANCE_CODES
    by_code: dict[str, dict[str, Any]] = {}
    for row in pool:
        code = str(row.get("code") or "")
        if code and _CODE_RE.match(code):
            by_code[code] = row
    return sorted(by_code.values(), key=lambda c: (-int(c.get("rank") or 0), c.get("code", "")))


def kill_law() -> dict[str, Any]:
    doc = _load_json(KILL_LAW_PATH, {})
    if not doc:
        return {"schema": "kill-immediate-law/v1", "law": "immediate_is_best", "motto": "When KILL is to occur, immediate is best."}
    return doc


def _witness_kill(event: str, *, ip: str = "", detail: str = "", meta: dict[str, Any] | None = None) -> None:
    ca = INSTALL / "lib" / "hostess7-change-awareness.py"
    if not ca.is_file():
        return
    try:
        spec = importlib.util.spec_from_file_location("h7_ca_kill", ca)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "witness_change"):
                mod.witness_change(
                    source="kill_immediate_law",
                    label=event,
                    detail=detail or ip,
                    meta={"ip": ip, "law": "immediate_is_best", **(meta or {})},
                    notify=True,
                )
    except Exception:
        pass


def execute_kill_immediate(
    ip: str,
    *,
    vector: str = "HOSTILE",
    severity: str = "high",
    reason: str = "kill_immediate_law",
    code: str = "KC-OP-kill",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The Law: when KILL is to occur, immediate is best — no queue, no deferral."""
    ip = _sanitize_ip(ip)
    if not ip:
        return {"ok": False, "error": "missing_ip", "law": "immediate_is_best"}
    law = kill_law()
    try:
        fg = _import_mod("friendly_guard", "friendly-guard.py")
        refuse, fg_reason = fg.refuse_kill(ip, monitor=(extra or {}).get("monitor") if isinstance((extra or {}).get("monitor"), dict) else None)
        if refuse:
            return {"ok": False, "friendly_refused": True, "reason": fg_reason, "ip": ip, "law": law.get("law"), "immediate": False}
    except Exception:
        pass
    fa = _import_mod("field_attack", "field-attack-kit.py")
    t0 = datetime.now(timezone.utc)
    result = fa.kill_target(ip, vector, severity, reason, extra=extra)
    elapsed_ms = round((datetime.now(timezone.utc) - t0).total_seconds() * 1000, 2)
    ok = bool(result.get("killed") or result.get("ok"))
    out = {
        **result,
        "ok": ok,
        "code": code,
        "law": law.get("law", "immediate_is_best"),
        "immediate": ok,
        "immediate_is_best": True,
        "elapsed_ms": elapsed_ms,
        "motto": law.get("motto"),
        "no_queue": True,
    }
    if ok:
        _witness_kill("KILL_immediate", ip=ip, detail=reason, meta={"code": code, "elapsed_ms": elapsed_ms})
    return out


def build_catalog() -> dict[str, Any]:
    codes = _all_codes()
    policy = _load_json(POLICY_PATH, {})
    law = kill_law()
    return {
        "schema": "nexus-kill-codes/v1",
        "updated": _now(),
        "motto": "Above military grade — every kill code named, ranked, friendly-guard gated. When KILL is to occur, immediate is best.",
        "kill_law": law,
        "merciless": bool(policy.get("merciless")),
        "status": policy.get("status", "lethal"),
        "count": len(codes),
        "families": ["removal", "disablement", "operator", "vigilance"],
        "codes": codes,
    }


def _code_index() -> dict[str, dict[str, Any]]:
    return {c["code"]: c for c in _all_codes()}


def recommend_for_alert(alert: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not alert:
        return []
    idx = _code_index()
    picks: list[dict[str, Any]] = []
    sev = str(alert.get("severity") or "").upper()
    source = str(alert.get("source") or "")
    cat = str(alert.get("category") or "")
    meta = alert.get("meta") if isinstance(alert.get("meta"), dict) else {}
    ip = _sanitize_ip(meta.get("ip") or alert.get("entity_id"))

    def add(code: str, *, detail: str = "") -> None:
        row = idx.get(code)
        if not row:
            return
        copy = dict(row)
        if detail:
            copy["detail"] = detail[:120]
        if ip:
            copy["suggested_ip"] = ip
        picks.append(copy)

    if alert.get("unidentified"):
        add("KC-VG-identify", detail="Unidentified — classify before strike")
        add("KC-OP-human_threat")
    if sev == "HARM_CANDIDATE":
        add("KC-OP-strike_certain" if ip else "KC-OP-crush_hot")
        add("KC-OP-kill")
        add("KC-DM-sever_wire")
        add("KC-RM-lethal")
        add("KC-DM-forever_kill")
    elif sev == "SUSPICIOUS":
        add("KC-OP-sever")
        add("KC-DM-sever_wire")
        add("KC-RM-strike")
    elif sev == "MONITOR":
        add("KC-RM-monitor")
        add("KC-OP-nokill", detail="If false positive — exempt from autokill")

    if source == "scour":
        add("KC-OP-human_threat")
        add("KC-VG-identify")
    if source == "dpi" or cat == "packet":
        add("KC-VG-packet_inject")
        add("KC-VG-text_injection", detail="DPI alert — verify injection not collateral")
    if source == "hazard" or cat == "rf":
        add("KC-RM-cease")
        add("KC-DM-laser_corridor")
    if source == "gatekeeper" and ip:
        add("KC-OP-kill", detail=f"Gatekeeper target {ip}")

    # Dedupe preserve order
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for p in picks:
        c = p.get("code")
        if c and c not in seen:
            seen.add(c)
            out.append(p)
    return out[:12]


def execute_code(code: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body if isinstance(body, dict) else {}
    code = str(code or "").strip()
    if not _CODE_RE.match(code):
        return {"ok": False, "error": "invalid_kill_code"}
    spec = _code_index().get(code)
    if not spec:
        return {"ok": False, "error": "unknown_kill_code", "code": code}

    law = kill_law()
    tier = str(spec.get("tier") or "")
    ip_early = _sanitize_ip(body.get("ip") or body.get("target_ip") or spec.get("suggested_ip"))
    if ip_early and tier == "lethal" and code.startswith("KC-OP-") and code not in ("KC-OP-nokill", "KC-OP-crush_hot", "KC-OP-lethal_cycle", "KC-OP-human_threat", "KC-OP-regional"):
        immediate = execute_kill_immediate(
            ip_early,
            vector=str(body.get("vector") or "HOSTILE"),
            severity=str(body.get("severity") or "high"),
            reason=str(body.get("reason") or spec.get("plain") or "kill_code_immediate")[:120],
            code=code,
            extra=body if isinstance(body, dict) else None,
        )
        if immediate.get("ok") or immediate.get("friendly_refused") or immediate.get("strike_refused"):
            return immediate
        if immediate.get("nokill_refused"):
            return immediate

    ip = _sanitize_ip(body.get("ip") or body.get("target_ip") or spec.get("suggested_ip"))
    if spec.get("requires_ip") and not ip:
        return {"ok": False, "error": "missing_ip", "code": code}
    if spec.get("requires_region") and not str(body.get("region") or body.get("value") or "").strip():
        return {"ok": False, "error": "missing_region", "code": code}

    payload = dict(spec.get("body_template") or {})
    payload.update({k: v for k, v in body.items() if k not in ("code",)})
    if ip:
        payload["ip"] = ip

    # Friendly guard on IP strikes
    if ip and spec.get("api", "").startswith("/api/attack-kit/"):
        try:
            fg = _import_mod("friendly_guard", "friendly-guard.py")
            refuse, reason = fg.refuse_kill(ip, monitor=body.get("monitor") if isinstance(body.get("monitor"), dict) else None)
            if refuse:
                return {"ok": False, "friendly_refused": True, "reason": reason, "ip": ip, "code": code}
        except Exception:
            pass

    api = str(spec.get("api") or "")
    if api == "/api/field-toolkit/sever":
        ft = _import_mod("field_toolkit", "field-toolkit-db.py")
        return {**ft.sever_target(ip, str(payload.get("vector") or "HELL_SEVER"), str(payload.get("severity") or "high"), str(payload.get("reason") or "kill_code")), "code": code}
    if api == "/api/field-toolkit/regional-disable":
        ft = _import_mod("field_toolkit", "field-toolkit-db.py")
        return {**ft.regional_disable(str(payload.get("region") or payload.get("value") or ""), field=str(payload.get("field") or "region")), "code": code}
    if api == "/api/field-toolkit/human-threat":
        ft = _import_mod("field_toolkit", "field-toolkit-db.py")
        return {**ft.human_threat_disable(max_ips=int(payload.get("max_ips") or 24)), "code": code}
    if api == "/api/field-toolkit/laser-corridor":
        ft = _import_mod("field_toolkit", "field-toolkit-db.py")
        return {**ft.laser_corridor(ip, str(payload.get("vector") or "LASER_CORRIDOR"), str(payload.get("severity") or "critical")), "code": code}
    if api == "/api/field-toolkit/hell-rip":
        ft = _import_mod("field_toolkit", "field-toolkit-db.py")
        return {**ft.hell_rip(), "code": code}
    if api == "/api/field-toolkit/field-die":
        ft = _import_mod("field_toolkit", "field-toolkit-db.py")
        return {**ft.field_die_roll(ip or None), "code": code}
    if api == "/api/lethal-enforcement/cycle":
        le = _import_mod("lethal_enforcement", "lethal-enforcement.py")
        return {**le.merciless_cycle(dry_run=bool(payload.get("dry_run"))), "code": code}
    if api in ("/api/attack-kit/kill", "/api/attack-kit/rekill", "/api/attack-kit/nokill"):
        if api == "/api/attack-kit/kill":
            return execute_kill_immediate(
                ip,
                vector=str(payload.get("vector") or "HOSTILE"),
                severity=str(payload.get("severity") or "high"),
                reason=str(payload.get("reason") or "kill_code"),
                code=code,
                extra=payload,
            )
        fa = _import_mod("field_attack", "field-attack-kit.py")
        if "rekill" in api:
            return {**fa.rekill_target(ip, str(payload.get("vector") or "HOSTILE"), str(payload.get("severity") or "high")), "code": code}
        return {**fa.nokill_target(ip, str(payload.get("vector") or "HOSTILE"), str(payload.get("severity") or "high"), str(payload.get("reason") or "operator_nokill")), "code": code}
    if api == "/api/attack-kit/crush-hot":
        fa = _import_mod("field_attack", "field-attack-kit.py")
        return {**fa.crush_hot(), "code": code}
    if spec.get("removal_level"):
        le = _import_mod("lethal_enforcement", "lethal-enforcement.py")
        row = {"ip": ip, "verdict": "HARM_CANDIDATE", "hell_chosen": spec.get("removal_level") in ("lethal", "total_removal")}
        return {**le.execute_removal(row, force_insight=bool(payload.get("force"))), "code": code}
    if spec.get("disablement"):
        ft = _import_mod("field_toolkit", "field-toolkit-db.py")
        return {**ft.execute_disablement({"mode": spec.get("mode") or spec["disablement"], **payload}), "code": code}

    out = {"ok": False, "error": "code_not_executable", "code": code, "jump": spec.get("jump")}
    out["law"] = law.get("law", "immediate_is_best")
    return out


def actions_from_codes(codes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map kill codes to Actions tab buttons."""
    out: list[dict[str, Any]] = []
    for c in codes:
        act: dict[str, Any] = {
            "id": f"kill:{c.get('code')}",
            "label": c.get("label") or c.get("code"),
            "tier": c.get("tier") or "watch",
            "detail": c.get("detail") or c.get("plain", "")[:100],
            "kill_code": c.get("code"),
        }
        if c.get("api"):
            body = dict(c.get("body_template") or {})
            if c.get("suggested_ip"):
                body["ip"] = c["suggested_ip"]
            act["api"] = "/api/kill-codes/execute"
            act["body"] = {"code": c["code"], **body}
        elif c.get("jump"):
            act["jump"] = c["jump"]
        out.append(act)
    return out


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in ("catalog", "json"):
        print(json.dumps(build_catalog(), ensure_ascii=False, indent=2))
        return 0
    if args[0] == "recommend" and len(args) > 1:
        alert = json.loads(args[1])
        print(json.dumps({"codes": recommend_for_alert(alert)}, ensure_ascii=False, indent=2))
        return 0
    if args[0] in ("law", "immediate"):
        print(json.dumps(kill_law(), ensure_ascii=False, indent=2))
        return 0
    if args[0] == "execute" and len(args) > 1:
        if args[1].startswith("KC-") and len(args) > 2:
            code = args[1]
            body = json.loads(args[2])
        elif args[1].startswith("KC-"):
            code = args[1]
            body = {}
        else:
            body = json.loads(args[1])
            code = str(body.get("code") or "")
        print(json.dumps(execute_code(code, body), ensure_ascii=False, indent=2))
        return 0
    print("usage: kill-codes.py [catalog|recommend '<alert json>'|execute '<body json>']", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())