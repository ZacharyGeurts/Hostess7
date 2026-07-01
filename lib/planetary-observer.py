#!/usr/bin/env pythong
"""Planetary observation + proactive kills — global sight, local destroy, keep us safe."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PANEL_CACHE = STATE / "planetary-observer-panel.json"
OPS_LOG = STATE / "planetary-proactive-kills.jsonl"

PROACTIVE_DEFAULT = os.environ.get("NEXUS_PLANETARY_PROACTIVE_KILL", "1") == "1"
REGIONAL_MIN_CLUSTER = int(os.environ.get("NEXUS_PLANETARY_REGIONAL_MIN", "5"))
AUTOKILL_MAX = int(os.environ.get("NEXUS_PLANETARY_AUTOKILL_MAX", "64"))
REKILL_MAX = int(os.environ.get("NEXUS_AUTO_REKILL_MAX_IPS", "64"))
FOREVER_MAX = int(os.environ.get("NEXUS_PLANETARY_FOREVER_KILL_MAX", "64"))


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


def _mod(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _log_op(entry: dict[str, Any]) -> None:
    try:
        OPS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with OPS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), **entry}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def observe() -> dict[str, Any]:
    """Aggregate planetary-scale threat sight from all field tables."""
    host = _load_json(STATE / "host-attacks.json", {"points": [], "stats": {}})
    points = [p for p in host.get("points") or [] if isinstance(p, dict)]
    gk = _load_json(STATE / "connection-intent.json", {})
    conns = gk.get("connections") or []
    harm = [c for c in conns if c.get("verdict") in ("HARM_CANDIDATE", "BLOCK_RECOMMENDED")]
    kill_ready = [c for c in conns if c.get("kill_eligible")]
    certain_pts = [p for p in points if p.get("strike_certain")]
    killable_pts = [p for p in points if p.get("killable") and not p.get("strike_certain")]
    needs_die_pts = [p for p in points if p.get("strike_certain") or p.get("killable")]
    hot_pts = [p for p in points if (p.get("heat") or 0) >= 0.65 or p.get("severity") in ("critical", "high")]

    by_country: Counter[str] = Counter()
    by_asn: Counter[str] = Counter()
    zones_hot: dict[str, int] = defaultdict(int)
    for p in points:
        cc = str(p.get("country_code") or p.get("country") or "unknown").upper()[:8]
        asn = str(p.get("asn") or p.get("org") or "unknown")[:48]
        if cc and cc not in ("UNKNOWN", "—", "-"):
            by_country[cc] += 1
        if asn and asn.lower() != "unknown":
            by_asn[asn] += 1
        if p.get("strike_certain") or p.get("killable"):
            zones_hot[cc] += 1

    planetary_dns: dict[str, Any] = {}
    try:
        planetary_dns = _mod("dns_planetary", "dns-planetary-security.py").build_planetary_dns()
    except Exception:
        planetary_dns = {}

    hostile_ai: dict[str, Any] = {}
    try:
        hostile_ai = _mod("hostile_ai", "hostile-ai-destroy.py").build_panel()
    except Exception:
        hostile_ai = _load_json(STATE / "hostile-ai-panel.json", {})

    threat_lines = 0
    if (STATE / "threat-vectors.tsv").is_file():
        threat_lines = max(0, sum(1 for _ in (STATE / "threat-vectors.tsv").read_text(encoding="utf-8", errors="replace").splitlines()) - 1)

    top_regions = [
        {"country": k, "count": v, "hostile": zones_hot.get(k, 0)}
        for k, v in by_country.most_common(12)
    ]
    top_asn = [{"asn": k, "count": v} for k, v in by_asn.most_common(8)]

    return {
        "schema": "planetary-observer/v1",
        "updated": _now(),
        "motto": "Planetary observation — proactive kills to keep us all safe.",
        "doctrine": "Observe the whole planet. Autokill + RE-KILL everything that needs to die. Friendly guard honored.",
        "planetary_dns": {
            "level": planetary_dns.get("planetary_security_level"),
            "zones": len(planetary_dns.get("zones") or []),
            "foreign_ipv4_blocked": len(planetary_dns.get("foreign_resolver_ipv4") or []),
            "foreign_ipv6_blocked": len(planetary_dns.get("foreign_resolver_ipv6") or []),
            "ipv6_truth": (planetary_dns.get("resolv") or {}).get("ipv6_truth_enforced"),
        },
        "globe": {
            "total_targets": len(points),
            "hot_targets": len(hot_pts),
            "strike_certain": len(certain_pts),
            "killable": len(killable_pts),
            "needs_die": len(needs_die_pts),
            "monitor_targets": sum(1 for p in points if p.get("is_monitor_target")),
            "top_regions": top_regions,
            "top_asn": top_asn,
        },
        "wire": {
            "connections": len(conns),
            "harm_candidates": len(harm),
            "kill_eligible": len(kill_ready),
            "strict_trust": gk.get("strict_trust"),
        },
        "hostile_ai": {
            "active": hostile_ai.get("active_count", 0),
            "certain": hostile_ai.get("certain_count", 0),
        },
        "threat_vector_events": threat_lines,
        "proactive_enabled": PROACTIVE_DEFAULT,
    }


def _top_hostile_region(obs: dict[str, Any]) -> tuple[str, str, int] | None:
    regions = obs.get("globe", {}).get("top_regions") or []
    for row in regions:
        hostile = int(row.get("hostile") or 0)
        if hostile >= REGIONAL_MIN_CLUSTER:
            cc = str(row.get("country") or "")
            if cc and cc not in ("UNKNOWN", "—"):
                return "country_code", cc, hostile
    return None


def _collect_kill_explanations(out: dict[str, Any]) -> list[dict[str, Any]]:
    """Gather plain-English why-killed rows from any action payload shape."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for key in ("results", "executed", "rekilled_detail", "enforced_detail"):
        for item in out.get(key) or []:
            if not isinstance(item, dict):
                continue
            plain = item.get("why_killed_plain")
            ip = str(item.get("ip") or "").strip()
            if not ip or not plain:
                continue
            dedupe = f"{ip}:{plain[:48]}"
            if dedupe in seen:
                continue
            seen.add(dedupe)
            rows.append({
                "ip": ip,
                "threat_id": item.get("threat_id"),
                "threat_trigger_plain": item.get("threat_trigger_plain"),
                "why_killed_plain": plain,
                "action": item.get("action") or out.get("step"),
            })
    return rows


def _record_action(results: dict[str, Any], step: str, out: dict[str, Any]) -> None:
    out = {**out, "step": step}
    explained = _collect_kill_explanations(out)
    if explained:
        out["kills_explained"] = explained
        results.setdefault("kills_explained", []).extend(explained)
    results["actions"].append({"step": step, **out})
    killed = (
        out.get("killed_count")
        or out.get("destroyed_count")
        or out.get("rekilled_count")
        or out.get("enforced_count")
        or out.get("executed_count")
        or out.get("kill_count")
        or 0
    )
    if killed or explained:
        _log_op({
            "step": step,
            **{k: out.get(k) for k in (
                "killed_count", "destroyed_count", "rekilled_count", "enforced_count", "kill_count",
                "executed_count", "certain_killed_count", "killable_killed_count", "attempted",
            ) if out.get(k) is not None},
            "kills_explained": explained[:24],
        })


def proactive_cycle(*, force: bool = False) -> dict[str, Any]:
    """Run proactive destroy passes — autokill + RE-KILL everything that needs to die."""
    if not PROACTIVE_DEFAULT and not force:
        return {"ok": True, "skipped": True, "reason": "proactive_disabled"}

    obs = observe()
    results: dict[str, Any] = {
        "ok": True,
        "ts": _now(),
        "observation": obs,
        "actions": [],
    }

    ak = _mod("field_attack_kit", "field-attack-kit.py")
    ha = _mod("hostile_ai", "hostile-ai-destroy.py")
    ft = _mod("field_toolkit", "field-toolkit-db.py")

    # 1. Hostile AI at destroy certainty — always attempt
    ai_out = ha.destroy_targets(all_certain=True)
    if ai_out.get("attempted") or ai_out.get("killed_count"):
        _record_action(results, "hostile_ai_destroy", ai_out)

    # 2. Kill-detect — wire kill_eligible flows (zero-cost skip when signature unchanged)
    try:
        kd = _mod("kill_detect", "kill-detect.py")
        kd_out = kd.execute()
        if not kd_out.get("skipped"):
            _record_action(results, "kill_detect_execute", kd_out)
    except Exception as exc:
        results["actions"].append({"step": "kill_detect_execute", "ok": False, "error": str(exc)})

    # 3. Globe autokill — PINPOINT CERTAIN + killable (everything that needs to die on map)
    autokill = ak.autokill_needs_die(max_targets=AUTOKILL_MAX)
    _record_action(results, "autokill_needs_die", autokill)

    # 4. RE-KILL validated returners — always sweep hostile registry
    rekill = ak.auto_rekill_validated(max_ips=REKILL_MAX)
    _record_action(results, "auto_rekill", rekill)

    # 5. Forever-kill enforce — re-apply hardware destroy on archived kills
    enforce = ak.forever_kill_enforce(max_ips=FOREVER_MAX)
    _record_action(results, "forever_kill_enforce", enforce)

    # 6. Regional cluster — planetary proactive disable
    cluster = _top_hostile_region(obs)
    if cluster:
        field, value, hostile_n = cluster
        regional = ft.regional_disable(f"{field}:{value}")
        if regional.get("killed_count") or regional.get("severed_count"):
            _record_action(results, "regional_disable", {
                "field": field,
                "value": value,
                "hostile_in_cluster": hostile_n,
                **regional,
            })

    results["action_count"] = len(results["actions"])
    killed_total = sum(
        int(a.get("killed_count") or a.get("destroyed_count") or a.get("rekilled_count") or a.get("enforced_count") or 0)
        for a in results["actions"]
    )
    results["killed_total"] = killed_total
    results["summary"] = (
        f"Proactive cycle — {killed_total} killed/rekilled/enforced across {results['action_count']} pass(es). "
        f"Globe {obs['globe']['needs_die']} need die "
        f"({obs['globe']['strike_certain']} certain · {obs['globe']['killable']} killable) · "
        f"{obs['wire']['kill_eligible']} kill-eligible on wire."
    )
    return results


def build_panel(*, run_proactive: bool = False) -> dict[str, Any]:
    obs = observe()
    cycle: dict[str, Any] | None = None
    if run_proactive or PROACTIVE_DEFAULT:
        cycle = proactive_cycle()
    doc = {
        **obs,
        "last_proactive_cycle": cycle,
        "proactive_summary": (cycle or {}).get("summary") or "Observation only — proactive kill disabled.",
    }
    tmp = PANEL_CACHE.with_suffix(".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PANEL_CACHE)
    return doc


def panel_json() -> dict[str, Any]:
    if PANEL_CACHE.is_file():
        try:
            return json.loads(PANEL_CACHE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return build_panel(run_proactive=False)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd == "observe":
        print(json.dumps(observe(), ensure_ascii=False))
        return 0
    if cmd == "proactive":
        force = "--force" in sys.argv
        print(json.dumps(proactive_cycle(force=force), ensure_ascii=False))
        return 0
    if cmd == "cycle":
        print(json.dumps(build_panel(run_proactive=True), ensure_ascii=False))
        return 0
    if cmd == "panel":
        print(json.dumps(build_panel(run_proactive=PROACTIVE_DEFAULT), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: planetary-observer.py [observe|proactive|cycle|panel|json]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    import sys
    raise SystemExit(main())