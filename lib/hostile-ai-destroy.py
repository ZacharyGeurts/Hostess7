#!/usr/bin/env pythong
"""Hostile AI destroy — detect automated evil, score certainty, execute kill/sever."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SEED = INSTALL / "data" / "hostile-ai-threats-seed.json"
PANEL_CACHE = STATE / "hostile-ai-panel.json"
THREAT_TSV = STATE / "threat-vectors.tsv"
CONN_INTENT = STATE / "connection-intent.json"
US_FIELD = STATE / "us-field.json"

LOL_PROC = re.compile(
    r"(/tmp/|/dev/shm/|powershell|pwsh|mshta|wscript|cscript|regsvr32| rundll32)",
    re.I,
)
PRIVATE_IP = re.compile(
    r"^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|169\.254\.)"
)
AI_VECTORS = frozenset({
    "AI_BEACON_PRECISION",
    "AI_LOLBIN_CHAIN",
    "AI_ROGUE_INFRA",
    "AI_EXFIL_SHAPE",
    "AI_AUTOSCAN",
    "AI_ML_C2_STACK",
    "AI_PHISH_FRAUD",
    "AI_DNS_TUNNEL",
})


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


def _seed() -> dict[str, Any]:
    return _load_json(SEED, {"categories": []})


def _parse_ip(remote: str) -> str:
    s = str(remote or "").strip("[]")
    if ":" in s and s.count(":") == 1:
        return s.rsplit(":", 1)[0]
    return s.split("%")[0]


def _threat_by_ip() -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    if not THREAT_TSV.is_file():
        return out
    for line in THREAT_TSV.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        ts, vector, severity, detail = parts[0], parts[1], parts[2], parts[3]
        ip = ""
        for key in ("dst=", "ip=", "client="):
            m = re.search(rf"{re.escape(key)}([^\s]+)", detail)
            if m:
                ip = _parse_ip(m.group(1))
                break
        if not ip:
            m = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", detail)
            if m:
                ip = m.group(1)
        if ip:
            out[ip].append({"ts": ts, "vector": vector, "severity": severity, "detail": detail[:200]})
    return out


def _record_vector(vector: str, severity: str, detail: str) -> None:
    script = INSTALL / "lib" / "threat-vectors.sh"
    if not script.is_file():
        return
    env = {**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)}
    esc = detail.replace("'", "'\\''")
    subprocess.run(
        [
            "bash", "-c",
            f"source '{INSTALL}/lib/nexus-common.sh' && source '{script}' && "
            f"nexus_threat_record '{vector}' '{severity}' '{esc}'",
        ],
        capture_output=True,
        timeout=12,
        env=env,
    )


def _certainty(
    *,
    base: int,
    kill_eligible: bool = False,
    severity: str = "medium",
    indicator_count: int = 1,
    beacon: int = 0,
    harm: bool = False,
) -> int:
    score = base
    if kill_eligible:
        score += 18
    if harm:
        score += 12
    if beacon >= 7:
        score += 14
    elif beacon >= 4:
        score += 6
    sev = {"critical": 12, "high": 8, "medium": 4}.get(severity, 2)
    score += sev
    score += min(15, max(0, indicator_count - 1) * 4)
    return min(100, max(0, score))


def _destroy_action(certainty: int, category: dict[str, Any]) -> str:
    floor = int(category.get("certainty_floor") or 75)
    preferred = str(category.get("destroy") or "sever_wire")
    if certainty >= max(floor, 88) and preferred == "forever_kill":
        return "forever_kill"
    if certainty >= floor:
        return preferred
    return "monitor"


def _clarity_text(
    category: dict[str, Any],
    ip: str,
    proc: str,
    indicators: list[str],
    certainty: int,
) -> str:
    title = category.get("title") or "Hostile automation"
    ind = "; ".join(indicators[:3]) if indicators else "stacked field signals"
    who = f"{ip}" if ip else "local infrastructure"
    proc_bit = f" via {proc}" if proc and proc not in ("", "unknown", "network-peer") else ""
    return (
        f"{title}: {who}{proc_bit}. "
        f"Indicators: {ind}. "
        f"Certainty {certainty}% — "
        f"{'destroy authorized' if certainty >= int(category.get('certainty_floor') or 75) else 'watch and correlate'}."
    )


def _scan_connections(threats: dict[str, list]) -> list[dict[str, Any]]:
    doc = _load_json(CONN_INTENT, {"connections": []})
    cats = {c["id"]: c for c in _seed().get("categories") or []}
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()

    for conn in doc.get("connections") or []:
        if not isinstance(conn, dict):
            continue
        rip = _parse_ip(str(conn.get("remote_ip") or conn.get("remote") or ""))
        proc = str(conn.get("process") or "")
        if not rip or rip.startswith("127."):
            continue
        scores = conn.get("scores") or {}
        verdict = str(conn.get("verdict") or "")
        kill_eligible = bool(conn.get("kill_eligible"))
        beacon = int(scores.get("beacon_pattern") or 0)
        stream = int(scores.get("stream_theft_risk") or 0)
        bw = int(scores.get("bandwidth_abuse") or 0)
        threat_linked = int(scores.get("threat_linked") or 0)
        proc_trust = int(scores.get("process_trust") or 5)
        vec_list = [t["vector"] for t in threats.get(rip, [])]
        indicators: list[str] = []

        cat_id = ""
        vector = ""
        base = 42

        if LOL_PROC.search(proc) or "/tmp/" in proc or "/dev/shm/" in proc:
            cat_id = "ai_malware_polymorph"
            vector = "AI_LOLBIN_CHAIN"
            indicators.append("untrusted binary path egress")
            base = 72
        elif kill_eligible and beacon >= 7 and proc_trust <= 3:
            cat_id = "ai_c2_beacon"
            vector = "AI_BEACON_PRECISION"
            indicators.append(f"beacon_pattern {beacon}/10")
            base = 76
        elif stream >= 9 or (bw >= 6 and proc_trust <= 3):
            cat_id = "ai_exfil_shape"
            vector = "AI_EXFIL_SHAPE"
            indicators.append(f"stream_theft {stream}/10 bandwidth {bw}/10")
            base = 74
        elif threat_linked >= 6 and verdict in ("HARM_CANDIDATE", "SUSPICIOUS"):
            cat_id = "ai_ml_c2_stack"
            vector = "AI_ML_C2_STACK"
            indicators.append(f"threat_linked {threat_linked}/10")
            indicators.extend(vec_list[:2])
            base = 68
        elif "EGRESS_BEACON" in vec_list or "C2_CORRELATION" in vec_list:
            cat_id = "ai_c2_beacon"
            vector = "AI_BEACON_PRECISION"
            indicators.extend(vec_list[:2])
            base = 65
        elif kill_eligible and verdict == "HARM_CANDIDATE":
            cat_id = "ai_ml_c2_stack"
            vector = "AI_ML_C2_STACK"
            indicators.append(verdict.lower())
            base = 62
        else:
            continue

        cat = cats.get(cat_id) or {}
        certainty = _certainty(
            base=base,
            kill_eligible=kill_eligible,
            severity=str(cat.get("severity") or "high"),
            indicator_count=len(indicators),
            beacon=beacon,
            harm=verdict == "HARM_CANDIDATE",
        )
        key = f"{cat_id}:{rip}"
        if key in seen:
            continue
        seen.add(key)
        hits.append({
            "id": key,
            "category_id": cat_id,
            "category_title": cat.get("title") or cat_id,
            "vector": vector or cat.get("vector"),
            "ip": rip,
            "process": proc,
            "verdict": verdict,
            "kill_eligible": kill_eligible,
            "certainty_pct": certainty,
            "clarity": _clarity_text(cat, rip, proc, indicators, certainty),
            "indicators": indicators,
            "destroy_action": _destroy_action(certainty, cat),
            "destroy_label": cat.get("destroy_label") or "Destroy",
            "destroy_ready": certainty >= int(cat.get("certainty_floor") or 75),
            "severity": cat.get("severity") or "high",
        })
    return hits


def _scan_infrastructure(threats: dict[str, list]) -> list[dict[str, Any]]:
    cats = {c["id"]: c for c in _seed().get("categories") or []}
    cat = cats.get("ai_dns_dhcp_abuse") or {}
    hits: list[dict[str, Any]] = []
    infra_vecs = {"GATEWAY_SHIFT", "ARP_SPOOF", "DNS_POISON", "PACKET_INJECTION"}
    for ip, events in threats.items():
        matched = [e for e in events if e["vector"] in infra_vecs]
        if not matched:
            continue
        indicators = [f"{e['vector']}@{e['ts']}" for e in matched[-3:]]
        certainty = _certainty(
            base=80,
            severity="critical",
            indicator_count=len(indicators),
        )
        hits.append({
            "id": f"ai_dns_dhcp_abuse:{ip or 'gateway'}",
            "category_id": "ai_dns_dhcp_abuse",
            "category_title": cat.get("title") or "DNS/DHCP abuse",
            "vector": "AI_ROGUE_INFRA",
            "ip": ip or "",
            "process": "",
            "verdict": "INFRA_HOSTILE",
            "kill_eligible": True,
            "certainty_pct": certainty,
            "clarity": _clarity_text(cat, ip or "gateway", "", indicators, certainty),
            "indicators": indicators,
            "destroy_action": _destroy_action(certainty, cat),
            "destroy_label": cat.get("destroy_label") or "Restore truth",
            "destroy_ready": certainty >= int(cat.get("certainty_floor") or 88),
            "severity": "critical",
        })
    return hits


def _scan_dns_tunnel() -> list[dict[str, Any]]:
    dns = _load_json(STATE / "field-dns-panel.json", {})
    cats = {c["id"]: c for c in _seed().get("categories") or []}
    cat = cats.get("ai_dns_dhcp_abuse") or {}
    hits: list[dict[str, Any]] = []
    for q in (dns.get("recent_queries") or [])[:80]:
        if not isinstance(q, dict):
            continue
        name = str(q.get("qname") or q.get("name") or "")
        if len(name) < 48 and ".txt" not in name.lower():
            continue
        client = str(q.get("client") or q.get("src") or "")
        ip = _parse_ip(client)
        indicators = [f"long_qname len={len(name)}"]
        certainty = _certainty(base=76, severity="high", indicator_count=1)
        hits.append({
            "id": f"ai_dns_tunnel:{ip or name[:24]}",
            "category_id": "ai_dns_dhcp_abuse",
            "category_title": "DNS tunnel / DGA",
            "vector": "AI_DNS_TUNNEL",
            "ip": ip,
            "process": "",
            "verdict": "DNS_TUNNEL",
            "kill_eligible": bool(ip),
            "certainty_pct": certainty,
            "clarity": _clarity_text(cat, ip or "resolver path", "", indicators, certainty),
            "indicators": indicators,
            "destroy_action": _destroy_action(certainty, cat),
            "destroy_label": "Sever DNS tunnel client",
            "destroy_ready": certainty >= 70,
            "severity": "high",
        })
        if len(hits) >= 6:
            break
    return hits


def _scan_autoscan(threats: dict[str, list]) -> list[dict[str, Any]]:
    cats = {c["id"]: c for c in _seed().get("categories") or []}
    cat = cats.get("ai_autoscan_exploit") or {}
    hits: list[dict[str, Any]] = []
    for ip, events in threats.items():
        if not any(e["vector"] in ("LISTENER_SURGE", "PACKET_INJECTION", "RST_FLOOD") for e in events):
            continue
        indicators = [e["vector"] for e in events[-4:]]
        certainty = _certainty(base=70, severity="critical", indicator_count=len(indicators))
        hits.append({
            "id": f"ai_autoscan:{ip}",
            "category_id": "ai_autoscan_exploit",
            "category_title": cat.get("title") or "Autoscan",
            "vector": "AI_AUTOSCAN",
            "ip": ip,
            "process": "",
            "verdict": "SCAN_HOSTILE",
            "kill_eligible": True,
            "certainty_pct": certainty,
            "clarity": _clarity_text(cat, ip, "", indicators, certainty),
            "indicators": indicators,
            "destroy_action": _destroy_action(certainty, cat),
            "destroy_label": cat.get("destroy_label") or "KILL scan source",
            "destroy_ready": certainty >= int(cat.get("certainty_floor") or 80),
            "severity": "critical",
        })
    return hits[:12]


def scan_threats(*, record: bool = False) -> list[dict[str, Any]]:
    threats = _threat_by_ip()
    pool: list[dict[str, Any]] = []
    pool.extend(_scan_connections(threats))
    pool.extend(_scan_infrastructure(threats))
    pool.extend(_scan_dns_tunnel())
    pool.extend(_scan_autoscan(threats))
    pool.sort(key=lambda x: (-int(x.get("certainty_pct") or 0), x.get("ip") or ""))
    deduped: list[dict[str, Any]] = []
    seen_ip_cat: set[str] = set()
    for row in pool:
        key = f"{row.get('category_id')}:{row.get('ip')}"
        if key in seen_ip_cat:
            continue
        seen_ip_cat.add(key)
        try:
            kr = _mod("kill_reason_plain", "kill-reason-plain.py")
            row.update(kr.explain_threat_trigger(
                ip=str(row.get("ip") or ""),
                hostile=row,
                vector=str(row.get("vector") or ""),
            ))
        except Exception:
            pass
        deduped.append(row)
        if record and row.get("destroy_ready") and row.get("vector") in AI_VECTORS:
            ip = row.get("ip") or "infra"
            _record_vector(
                str(row["vector"]),
                str(row.get("severity") or "high"),
                f"hostile_ai ip={ip} certainty={row.get('certainty_pct')} "
                f"indicators={','.join(row.get('indicators') or [])[:120]}",
            )
    return deduped[:32]


def build_panel() -> dict[str, Any]:
    seed = _seed()
    active = scan_threats(record=False)
    certain = [t for t in active if t.get("destroy_ready")]
    return {
        "schema": "hostile-ai-destroy/v1",
        "updated": _now(),
        "title": seed.get("title") or "Hostile AI destroy",
        "motto": seed.get("motto") or "",
        "categories": seed.get("categories") or [],
        "active_threats": active,
        "certain_count": len(certain),
        "active_count": len(active),
        "destroyable": certain,
        "summary": (
            f"{len(certain)} threat(s) at destroy certainty · "
            f"{len(active)} total automated signals under watch"
        ),
    }


def _save_panel(doc: dict[str, Any]) -> None:
    tmp = PANEL_CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PANEL_CACHE)


def destroy_targets(
    *,
    ip: str = "",
    threat_id: str = "",
    all_certain: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    panel = build_panel()
    targets: list[dict[str, Any]] = []
    if all_certain:
        targets = list(panel.get("destroyable") or [])
    elif threat_id:
        targets = [t for t in panel.get("active_threats") or [] if t.get("id") == threat_id]
    elif ip:
        targets = [t for t in panel.get("active_threats") or [] if t.get("ip") == ip and t.get("destroy_ready")]
    else:
        return {"ok": False, "error": "missing_target"}

    if not targets:
        return {"ok": False, "error": "no_destroyable_targets", "panel": panel}

    ak = _mod("field_attack_kit", "field-attack-kit.py")
    ft = _mod("field_toolkit_db", "field-toolkit-db.py")
    results: list[dict[str, Any]] = []

    for t in targets:
        tip = str(t.get("ip") or "").strip()
        if not tip:
            results.append({"ok": False, "threat_id": t.get("id"), "error": "no_ip"})
            continue
        action = str(t.get("destroy_action") or "sever_wire")
        vector = str(t.get("vector") or "AI_HOSTILE")
        why_plain = t.get("clarity") or t.get("category_title") or "Hostile AI threat at destroy certainty."
        if action == "forever_kill":
            extra = {"force": force, "strike_mode": "hostile_ai", "hostile": t, "source": "hostile-ai-destroy"}
            out = ak.kill_target(
                tip,
                vector=vector,
                severity=str(t.get("severity") or "critical"),
                reason=f"hostile_ai_destroy:{t.get('category_id')}",
                extra=extra,
            )
            results.append({
                **out,
                "threat_id": t.get("id"),
                "action": "forever_kill",
                "why_killed_plain": out.get("why_killed_plain") or why_plain,
            })
        else:
            out = ft.sever_target(
                tip,
                vector=vector,
                severity=str(t.get("severity") or "high"),
                reason=f"hostile_ai_sever:{t.get('category_id')}",
            )
            results.append({
                **out,
                "threat_id": t.get("id"),
                "action": "sever_wire",
                "why_killed_plain": (
                    f"We severed the wire to {tip} because {why_plain} "
                    "Friendly guard was honored — no friendly fire on Heaven flows."
                ),
            })

    killed = sum(1 for r in results if r.get("killed") or r.get("ok"))
    return {
        "ok": killed > 0,
        "killed_count": killed,
        "attempted": len(results),
        "results": results,
        "panel": build_panel(),
    }


def publish_panel() -> dict[str, Any]:
    doc = build_panel()
    _save_panel(doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd == "panel":
        print(json.dumps(publish_panel(), ensure_ascii=False))
        return 0
    if cmd == "json":
        if PANEL_CACHE.is_file():
            print(PANEL_CACHE.read_text(encoding="utf-8"))
        else:
            print(json.dumps(publish_panel(), ensure_ascii=False))
        return 0
    if cmd == "scan":
        active = scan_threats(record=True)
        print(json.dumps({"ok": True, "active_count": len(active), "threats": active}, ensure_ascii=False))
        return 0
    if cmd == "destroy" and len(sys.argv) >= 3:
        body = json.loads(sys.argv[2])
        print(json.dumps(destroy_targets(
            ip=str(body.get("ip") or ""),
            threat_id=str(body.get("threat_id") or ""),
            all_certain=bool(body.get("all_certain")),
            force=bool(body.get("force")),
        ), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostile-ai-destroy.py [panel|json|scan|destroy JSON]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())