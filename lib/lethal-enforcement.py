#!/usr/bin/env pythong
"""NEXUS MERCILESS lethal enforcement — heaven/hell, spatial geometry, total removal.

Self defense · governance of body · right to self existence · trespass shoot-to-kill.
Hell-chosen and terrorists on the loose: interrogate, fill harm dossier, total removal.
Heaven never touched.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
POLICY_PATH = INSTALL / "data" / "lethal-enforcement-policy.json"
PANEL_CACHE = STATE / "lethal-enforcement-panel.json"
EXEC_LEDGER = STATE / "lethal-enforcement.jsonl"
INTENT = STATE / "connection-intent.json"
HOST_ATTACKS = STATE / "host-attacks.json"

MOTTO = (
    "MERCILESS lethal status — self defense, governance of body, right to self existence. "
    "Trespassers shoot to kill. Heaven passes. Hell gets total removal. God Bless."
)

REMOVAL_ORDER = (
    "pass", "monitor", "cease", "block", "eradicate", "strike", "lethal", "total_removal",
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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with EXEC_LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _import_mod(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def load_policy() -> dict[str, Any]:
    return _load_json(POLICY_PATH, {"merciless": True, "status": "lethal"})


def assess_harm(row: dict[str, Any]) -> dict[str, Any]:
    """Fill harm to self and populace — drives removal level."""
    policy = load_policy()
    thresholds = policy.get("harm_thresholds") or {}
    scores = row.get("scores") or {}
    harm_self = 0
    harm_populace = 0
    factors: list[str] = []

    verdict = str(row.get("verdict") or "")
    if verdict == "HARM_CANDIDATE":
        harm_self += 35
        harm_populace += 40
        factors.append("harm_candidate")
    if row.get("hell_chosen"):
        harm_self += 25
        harm_populace += 30
        factors.append("hell_chosen")
    if row.get("kill_eligible"):
        harm_self += 15
        factors.append("kill_eligible")

    kind = str(row.get("kind") or "")
    if kind == "terror":
        harm_self += 45
        harm_populace += 55
        factors.append("terror_on_the_loose")
    elif kind == "hostile":
        harm_self += 30
        harm_populace += 35
        factors.append("hostile")

    harm_self += int(scores.get("threat_linked", 0)) * 4
    harm_self += int(scores.get("beacon_pattern", 0)) * 3
    harm_populace += int(scores.get("stream_theft_risk", 0)) * 4
    harm_populace += int(scores.get("bandwidth_abuse", 0)) * 3

    if row.get("trespass") or row.get("wire_trespass"):
        harm_self += 40
        factors.append("trespass_self_defense")
    if row.get("rf_trespass"):
        harm_populace += 25
        factors.append("rf_trespass_populace")

    harm_total = min(100, harm_self + harm_populace // 2)
    return {
        "harm_self": min(100, harm_self),
        "harm_populace": min(100, harm_populace),
        "harm_total": harm_total,
        "factors": factors,
        "strike_min": int(thresholds.get("self_strike_min") or 35),
        "lethal_min": int(thresholds.get("lethal_min") or 72),
        "total_removal_min": int(thresholds.get("total_removal_min") or 88),
    }


def classify_removal(row: dict[str, Any], *, harm: dict[str, Any] | None = None) -> dict[str, Any]:
    """Heaven passes. Hell gets adequate removal level."""
    policy = load_policy()
    harm = harm or assess_harm(row)
    hh = _import_mod("heaven_hell", "heaven-hell.py")
    soul, hell = hh.classify_row(row)
    ip = str(row.get("ip") or row.get("remote_ip") or "").strip()

    if soul == "heaven":
        protected, reason = hh.heaven_protected(ip, row)
        return {
            "ip": ip,
            "soul_side": "heaven",
            "hell_chosen": False,
            "removal_level": "pass",
            "kill_tier": "none",
            "protected": protected,
            "reason": reason,
            "harm": harm,
            "merciless": False,
        }

    geo_mod = _import_mod("spatial_geometry", "spatial-target-geometry.py")
    geom = geo_mod.geometry_for_target(row)
    row_geo = {**row, **geom}
    harm = assess_harm(row_geo)

    level = "monitor"
    if hell or soul == "hell":
        level = "strike"
    if harm["harm_total"] >= harm["strike_min"]:
        level = "strike"
    if harm["harm_total"] >= harm["lethal_min"] or geom.get("shoot_to_kill_geometry"):
        level = "lethal"
    if str(row.get("kind") or "") == "terror" or harm["harm_total"] >= harm["total_removal_min"]:
        level = "total_removal"
    if row.get("hell_chosen") and policy.get("merciless"):
        if level in ("strike", "block", "eradicate"):
            level = "lethal"

    kill_tier = {
        "pass": "none",
        "monitor": "none",
        "cease": "block",
        "block": "block",
        "eradicate": "eradicate",
        "strike": "strike",
        "lethal": "lethal",
        "total_removal": "lethal",
    }.get(level, "strike")

    return {
        "ip": ip,
        "soul_side": soul,
        "hell_chosen": hell,
        "removal_level": level,
        "kill_tier": kill_tier,
        "harm": harm,
        "geometry": geom,
        "merciless": bool(policy.get("merciless")),
        "shoot_to_kill": bool(geom.get("shoot_to_kill_geometry") or level in ("lethal", "total_removal")),
    }


def interrogate_hostile(ip: str, row: dict[str, Any]) -> dict[str, Any]:
    """Stress-interrogate terrorists on the loose — max intel bleed before removal."""
    policy = load_policy()
    terror_cfg = policy.get("terror") or {}
    if not terror_cfg.get("interrogate_before_removal", True):
        return {"skipped": True, "reason": "interrogate_disabled"}

    kind = str(row.get("kind") or "")
    if kind != "terror" and not row.get("hell_chosen"):
        return {"skipped": True, "reason": "not_terror_or_hell"}

    bleed_doc: dict[str, Any] = {"ok": False}
    bleed_py = INSTALL / "lib" / "target-bleed.py"
    if bleed_py.is_file():
        try:
            tb = _import_mod("target_bleed", "target-bleed.py")
            bleed_doc = tb.bleed_target(ip, conn_hint=row, online=True)
        except Exception as exc:
            bleed_doc = {"ok": False, "error": str(exc)}

    return {
        "schema": "hostile-interrogate/v1",
        "interrogated_at": _now(),
        "ip": ip,
        "kind": kind,
        "on_the_loose": bool(terror_cfg.get("on_the_loose_escalation")),
        "bleed": bleed_doc,
        "intel_extracted": bool(bleed_doc.get("ok")),
        "policy": "hostile_intel_stress_before_total_removal",
    }


def execute_removal(
    row: dict[str, Any],
    *,
    dry_run: bool = False,
    force_insight: bool = False,
) -> dict[str, Any]:
    """Issue all corrects at adequate removal level — heaven never touched."""
    policy = load_policy()
    classification = classify_removal(row)
    ip = classification.get("ip") or ""
    level = str(classification.get("removal_level") or "pass")

    if level == "pass" or not ip:
        return {
            "ok": True,
            "skipped": True,
            "ip": ip,
            "reason": "heaven_or_empty",
            "classification": classification,
        }

    insight: dict[str, Any] = {}
    if policy.get("hostess7_corroborate"):
        h7 = _import_mod("hostess7_insight", "hostess7-lethal-insight.py")
        insight = h7.ask_insight(
            f"Execute {level} on {ip} — MERCILESS self-defense trespass",
            target={**row, **classification},
            context={"harm_total": classification.get("harm", {}).get("harm_total")},
        )
        if not insight.get("proceed_lethal") and level in ("lethal", "total_removal") and not force_insight:
            level = "strike"
            classification["removal_level"] = level
            classification["downgraded"] = "hostess7_gate"

    entry: dict[str, Any] = {
        "ok": False,
        "ip": ip,
        "removal_level": level,
        "kill_tier": classification.get("kill_tier"),
        "classification": classification,
        "hostess7": insight,
        "dry_run": dry_run,
        "actions": [],
    }

    if dry_run:
        entry["ok"] = True
        _append_ledger(entry)
        return entry

    if level == "total_removal":
        interrogation = interrogate_hostile(ip, row)
        entry["interrogation"] = interrogation
        entry["actions"].append("interrogate")

    hh = _import_mod("heaven_hell", "heaven-hell.py")
    protected, reason = hh.heaven_protected(ip, row)
    if protected:
        entry["skipped"] = True
        entry["reason"] = reason
        entry["ok"] = True
        return entry

    tier = classification.get("kill_tier") or "strike"
    pid = str(row.get("pid") or "0")

    if tier in ("eradicate", "lethal", "strike") and pid.isdigit() and int(pid) > 0:
        pest = INSTALL / "lib" / "pest-arsenal.sh"
        if pest.is_file():
            subprocess.run(
                ["bash", "-c", f"source '{pest}'; nexus_pest_eradicate '{ip}' '{pid}' 'LETHAL_MERCILESS' ''"],
                env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                timeout=12,
                check=False,
            )
            entry["actions"].append("eradicate")

    fw = INSTALL / "lib" / "firewall-sentinel.sh"
    if fw.is_file():
        subprocess.run(
            [
                "bash", "-c",
                (
                    f"source '{INSTALL}/lib/nexus-common.sh'; source '{fw}'; "
                    f"nexus_firewall_block_ip_forever out '{ip}' 'lethal:merciless' || true; "
                    f"nexus_firewall_block_ip_forever in '{ip}' 'lethal:merciless' || true"
                ),
            ],
            env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
            timeout=12,
            check=False,
        )
        entry["actions"].append("forever_block")

    if tier in ("strike", "lethal") or level in ("lethal", "total_removal"):
        kit = INSTALL / "lib" / "field-attack-kit.py"
        if kit.is_file():
            severity = "critical" if level == "total_removal" else "high"
            extra_destroy = level in ("lethal", "total_removal")
            subprocess.run(
                [
                    "pythong", str(kit), "kill", ip,
                    "LETHAL_MERCILESS", severity,
                    f"merciless:{level}:{'destroy' if extra_destroy else 'strike'}",
                ],
                env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                timeout=30,
                check=False,
            )
            entry["actions"].append("strike" if not extra_destroy else "lethal_strike")

    entry["ok"] = True
    entry["executed_at"] = _now()
    _append_ledger(entry)
    return entry


def collect_targets() -> list[dict[str, Any]]:
    """Gather hell-side connections + terror spiderweb + host attacks."""
    targets: dict[str, dict[str, Any]] = {}
    intent = _load_json(INTENT, {})
    for row in intent.get("connections") or []:
        ip = str(row.get("remote_ip") or "").strip()
        if ip:
            targets[ip] = {**row, "ip": ip, "source": "connection_intent"}

    attacks = _load_json(HOST_ATTACKS, {})
    for pt in attacks.get("points") or []:
        ip = str(pt.get("ip") or "").strip()
        if ip:
            targets[ip] = {**targets.get(ip, {}), **pt, "ip": ip, "source": "host_attacks"}

    try:
        sw = _import_mod("terror_spiderweb", "terror-spiderweb.py")
        panel = sw.panel_json() if hasattr(sw, "panel_json") else {}
        inet_rows = (panel.get("registry") or {}).get("internet") or []
        for node in inet_rows:
            if not isinstance(node, dict):
                continue
            ip = str(node.get("ip") or "").strip()
            if not ip or node.get("kind") not in ("terror", "hostile"):
                continue
            targets[ip] = {
                **targets.get(ip, {}),
                **node,
                "ip": ip,
                "kind": node.get("kind"),
                "source": "terror_spiderweb",
            }
    except Exception:
        pass

    hh = _import_mod("heaven_hell", "heaven-hell.py")
    hp = _import_mod("hostility_priority", "hostility-priority.py")
    rows = list(targets.values())
    classified: list[dict[str, Any]] = []
    for row in rows:
        soul, hell = hh.classify_row(row)
        if soul == "heaven":
            continue
        row["soul_side"] = soul
        row["hell_chosen"] = hell
        row["removal_plan"] = classify_removal(row)
        classified.append(row)
    return hp.sort_hell_first(classified) if hasattr(hp, "sort_hell_first") else classified


def merciless_cycle(*, dry_run: bool = False) -> dict[str, Any]:
    """Full MERCILESS pass — Hostess7 insight, spatial geometry, total removal."""
    policy = load_policy()
    targets = collect_targets()
    executed: list[dict[str, Any]] = []
    spared: list[dict[str, Any]] = []
    for row in targets:
        plan = row.get("removal_plan") or classify_removal(row)
        if plan.get("soul_side") == "heaven":
            spared.append({"ip": row.get("ip"), "reason": "heaven"})
            continue
        result = execute_removal(row, dry_run=dry_run)
        if result.get("skipped") and result.get("reason") == "heaven_or_empty":
            spared.append(result)
        else:
            executed.append(result)

    h7_insight: dict[str, Any] = {}
    if policy.get("hostess7_corroborate"):
        try:
            h7 = _import_mod("hostess7_insight", "hostess7-lethal-insight.py")
            h7_insight = h7.ask_insight(
                "MERCILESS lethal cycle — heaven hell spatial shoot to kill trespass",
                context={"target_count": len(targets), "executed": len(executed)},
            )
        except Exception:
            pass

    out = {
        "schema": "lethal-enforcement/v1",
        "status": policy.get("status", "lethal"),
        "merciless": bool(policy.get("merciless")),
        "motto": MOTTO,
        "updated": _now(),
        "target_count": len(targets),
        "executed_count": len(executed),
        "spared_heaven_count": len(spared),
        "hostess7_insight": h7_insight,
        "executed": executed[:32],
        "spared_heaven": spared[:16],
        "dry_run": dry_run,
    }
    _save_json(PANEL_CACHE, out)
    return out


def panel_status() -> dict[str, Any]:
    policy = load_policy()
    cached = _load_json(PANEL_CACHE, {})
    hh = _import_mod("heaven_hell", "heaven-hell.py")
    heaven_hell = hh.build_status()
    return {
        "schema": "lethal-enforcement-panel/v1",
        "status": policy.get("status", "lethal"),
        "merciless": bool(policy.get("merciless")),
        "shoot_to_kill": bool(policy.get("shoot_to_kill")),
        "motto": MOTTO,
        "policy_path": str(POLICY_PATH),
        "heaven_hell": heaven_hell,
        "last_cycle": cached,
        "removal_levels": policy.get("removal_levels"),
    }


def main() -> int:
    args = sys.argv[1:]
    cmd = (args[0] if args else "status").lower()
    if cmd in ("status", "json", "panel"):
        print(json.dumps(panel_status(), indent=2))
        return 0
    if cmd == "cycle":
        dry = "--dry-run" in args
        print(json.dumps(merciless_cycle(dry_run=dry), indent=2))
        return 0
    if cmd == "classify" and len(args) > 1:
        row = json.loads(args[1])
        print(json.dumps(classify_removal(row), indent=2))
        return 0
    if cmd == "execute" and len(args) > 1:
        row = json.loads(args[1])
        dry = "--dry-run" in args
        print(json.dumps(execute_removal(row, dry_run=dry), indent=2))
        return 0
    print(
        "usage: lethal-enforcement.py [status|cycle [--dry-run]|classify '<json>'|execute '<json>']",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())