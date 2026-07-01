#!/usr/bin/env pythong
"""Plain-English explanations — what triggered threat classification and why they were killed."""
from __future__ import annotations

import re
from typing import Any

# Technical reason token → plain-English template (use {ip}, {process}, {vector}, {detail})
_REASON_TEMPLATES: dict[str, str] = {
    "strike_certain": "PINPOINT CERTAIN — hostile confirmed on wire host. Interdict executed. No CDN collateral.",
    "killable": "Trust Strike authorized — hostile wire host above certainty floor. Interdict without delay.",
    "harm_candidate": "IFF HOSTILE — gatekeeper confirmed hostile intent on live connection. Interdict standing.",
    "threat_correlated_harm": "HOSTILE — egress correlated with active threat intelligence on this IP.",
    "stream_theft_daemon": "HOSTILE — daemon exhibited stream exfiltration / bandwidth abuse toward remote host.",
    "persistent_beacon": "HOSTILE — persistent beaconing from untrusted local process to remote host.",
    "beacon_burst": "HOSTILE — repeated beacon bursts. Not civilian consumer traffic.",
    "rekill_same_host_validated": "RE-KILL — hostile host reappeared. Identity markers matched archived dossier. Interdict re-executed.",
    "forever_kill_enforce": "FOREVER-KILL enforced — prior destroy dossier active on field drive. No permit restoration.",
    "operator_disable": "Operator ordered permanent disable from the threat panel.",
    "operator_nokill": "Operator exempted this IP from autokill (NO-KILL).",
    "target_kill": "Operator or field kit ordered permanent kill on this target.",
    "gatekeeper_harm": "Live gatekeeper harm signature — kill-detect executed block/strike.",
    "rf_unhealthy_forever": "Unhealthy RF-correlated wireless threat — permanent disable.",
    "regional_disable": "Regional cluster disable — multiple hostiles in the same geography.",
    "hostile_ai_destroy": "HOSTILE AI — certainty floor met. Automated threat stack destroyed without hesitation.",
    "nokill_exempt": "Kill refused — IP is on the NO-KILL exempt list.",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _ip_label(ip: str) -> str:
    ip = _clean(ip)
    return ip or "this target"


def _process_label(proc: str) -> str:
    proc = _clean(proc)
    if not proc or proc in ("—", "unknown", "network-peer"):
        return ""
    return proc


def _parse_reason_code(reason: str) -> tuple[str, str]:
    """Return (base_code, full_code)."""
    reason = _clean(reason)
    if not reason:
        return "target_kill", "target_kill"
    base = reason.split(":", 1)[-1]
    for token in (
        "strike_certain",
        "killable",
        "harm_candidate",
        "threat_correlated_harm",
        "stream_theft_daemon",
        "persistent_beacon",
        "rekill_same_host_validated",
        "forever_kill_enforce",
        "gatekeeper_harm",
        "hostile_ai_destroy",
        "regional_disable",
    ):
        if token in reason:
            return token, reason
    if reason.startswith("threat_vector:"):
        return "threat_vector", reason
    if reason.startswith("shell_port:"):
        return "shell_port", reason
    if reason.startswith("suspicious_shell:"):
        return "suspicious_shell", reason
    if reason.startswith("beacon_burst:"):
        return "beacon_burst", reason
    if reason.startswith("kill_detect:"):
        inner = reason.split(":", 1)[1]
        return _parse_reason_code(inner)[0], reason
    if reason.startswith("autokill"):
        if "strike_certain" in reason:
            return "strike_certain", reason
        if "killable" in reason:
            return "killable", reason
        return "autokill", reason
    if reason.startswith("hostile_ai"):
        return "hostile_ai_destroy", reason
    return base.split("=")[0] if "=" in base else base, reason


def _threat_vector_plain(vector: str) -> str:
    vector = _clean(vector).upper()
    labels = {
        "AI_BEACON_PRECISION": "precision C2 beacon automation",
        "AI_LOLBIN_CHAIN": "LOLBin / living-off-the-land malware chain",
        "AI_ROGUE_INFRA": "rogue DNS or DHCP infrastructure",
        "AI_EXFIL_SHAPE": "ML-shaped data exfiltration",
        "AI_AUTOSCAN": "automated hostile scanning",
        "AI_ML_C2_STACK": "ML-assisted command-and-control stack",
        "AI_DNS_TUNNEL": "DNS tunneling for covert C2",
        "AI_PHISH_FRAUD": "automated phishing or fraud pipeline",
        "KILL_DETECT": "kill-detect harm signature on live wire",
        "HOSTILE": "general hostile classification",
    }
    return labels.get(vector, vector.replace("_", " ").lower() or "hostile activity")


def _monitor_summary(monitor: dict[str, Any] | None) -> str:
    if not isinstance(monitor, dict):
        return ""
    parts: list[str] = []
    verdict = monitor.get("verdict")
    if verdict:
        parts.append(f"verdict {verdict}")
    harm = monitor.get("harm_total")
    if harm is not None:
        parts.append(f"harm score {harm}")
    proc = _process_label(str(monitor.get("process") or ""))
    if proc:
        parts.append(f"via {proc}")
    summary = monitor.get("suggestion_summary") or monitor.get("reason")
    if summary:
        parts.append(_clean(str(summary))[:120])
    return "; ".join(parts)


def _strike_signals_plain(strike_gate: dict[str, Any] | None) -> str:
    if not isinstance(strike_gate, dict):
        return ""
    score = strike_gate.get("score") if isinstance(strike_gate.get("score"), dict) else {}
    signals = score.get("signals") or []
    bits: list[str] = []
    for sig in signals[:4]:
        if not isinstance(sig, dict):
            continue
        label = sig.get("label") or sig.get("id")
        if label:
            bits.append(_clean(str(label)))
    wire = strike_gate.get("wire_point") or score.get("wire_point") or {}
    if isinstance(wire, dict) and wire.get("label"):
        bits.insert(0, f"wire host: {_clean(str(wire.get('label')))}")
    return "; ".join(bits)


_KILL_REASON_PLAIN: dict[str, str] = {
    "threat_vector": "An active threat-vector event matched this IP on the live wire.",
    "shell_port": "Traffic used a shell or admin-class port from an untrusted local process.",
    "suspicious_shell": "A suspicious process opened a shell-class port toward this remote host.",
    "beacon_burst": "Repeated beacon bursts to this host — not normal consumer browsing.",
    "harm_candidate": "Gatekeeper scored the live flow as HARM_CANDIDATE — hostile intent on the wire.",
    "threat_correlated_harm": "Harm on the wire correlated with threat intelligence already on this IP.",
    "stream_theft_daemon": "A background daemon showed stream-theft or bandwidth-abuse shape toward this host.",
    "persistent_beacon": "Persistent beaconing from an untrusted process — classic C2 keepalive shape.",
    "gatekeeper_harm": "Connection gatekeeper flagged kill-eligible harm on this flow.",
}


_SIGNAL_PLAIN: dict[str, str] = {
    "wire_point_locked": "Trust Strike locked the actual end wire host — not CDN collateral.",
    "prior_kill_registry": "IP is in our permanent hostile registry from a prior kill on field drive.",
    "archived_dossier_strong": "Strong archived kill dossier with multiple identity markers matched.",
    "archived_dossier": "Prior archived dossier identity markers matched this host.",
    "hostile_asn_corpus": "ASN matches our prior KILL corpus — same bad neighborhood as past strikes.",
    "hostile_org_corpus": "Organization matches our prior KILL corpus.",
    "harm_verdict": "Live monitor returned a hostile verdict on this flow.",
    "harm_critical": "Monitor harm score crossed the critical threshold.",
    "harm_high": "Elevated monitor harm score on a non-consumer process.",
    "hostile_vector": "Threat vector plus malware campaign corroboration.",
    "heat_critical": "Map heat plus campaign intel — hot target on the globe.",
    "c2_ports": "C2-class destination ports observed on this connection.",
    "threat_linked_axis": "threat_linked axis scored high — tied to known threat events.",
    "beacon_axis": "beacon_pattern axis scored high — timed callback shape.",
    "dpi_high_alert": "Packet DPI raised a high-confidence alert on this flow.",
    "live_monitor_target": "Active live monitor target with malware campaign overlap.",
}


def _signal_plain(sig: dict[str, Any]) -> str:
    sid = _clean(str(sig.get("id") or ""))
    detail = _clean(str(sig.get("detail") or ""))
    base = _SIGNAL_PLAIN.get(sid, sid.replace("_", " ") if sid else "field signal")
    return f"{base} ({detail})" if detail and detail.lower() not in base.lower() else base


def _gatekeeper_trigger_plain(conn: dict[str, Any]) -> list[str]:
    if not isinstance(conn, dict):
        return []
    lines: list[str] = []
    kill_reason = _clean(str(conn.get("kill_reason") or ""))
    if kill_reason:
        base, _ = _parse_reason_code(kill_reason)
        lines.append(_KILL_REASON_PLAIN.get(base, f"Gatekeeper kill reason: {kill_reason}."))
    scores = conn.get("scores") if isinstance(conn.get("scores"), dict) else {}
    if scores:
        bits: list[str] = []
        for key, label in (
            ("beacon_pattern", "beacon pattern"),
            ("stream_theft_risk", "stream theft risk"),
            ("bandwidth_abuse", "bandwidth abuse"),
            ("threat_linked", "threat linkage"),
            ("process_trust", "process trust"),
        ):
            val = scores.get(key)
            if val is not None and int(val) >= 4:
                bits.append(f"{label} {val}/10")
        if bits:
            lines.append(f"Gatekeeper axis scores: {', '.join(bits)}.")
    if conn.get("kill_eligible"):
        lines.append("Gatekeeper marked this connection kill-eligible — harm signature on the wire.")
    if conn.get("hell_chosen"):
        lines.append("Heaven/Hell engine chose Hell for this flow — no mercy path.")
    verdict = _clean(str(conn.get("verdict") or ""))
    if verdict in ("HARM_CANDIDATE", "SUSPICIOUS", "BLOCK_RECOMMENDED"):
        lines.append(f"Live verdict was {verdict}.")
    return lines


def explain_threat_trigger(
    *,
    ip: str = "",
    point: dict[str, Any] | None = None,
    conn: dict[str, Any] | None = None,
    hostile: dict[str, Any] | None = None,
    strike: dict[str, Any] | None = None,
    strike_gate: dict[str, Any] | None = None,
    vector: str = "",
) -> dict[str, Any]:
    """Long plain English — what triggered us to call this a threat."""
    point = point or {}
    conn = conn or {}
    hostile = hostile or {}
    ip = _ip_label(ip or point.get("ip") or conn.get("remote_ip") or hostile.get("ip"))
    vector = _clean(vector or point.get("vector") or hostile.get("vector") or conn.get("vector") or "")

    triggers: list[dict[str, str]] = []
    sentences: list[str] = [
        f"We classified {ip} as a threat because our field sensors stacked the following triggers — not guesswork, live wire + intel corroboration.",
    ]

    strike_doc = strike if isinstance(strike, dict) else {}
    if not strike_doc and isinstance(strike_gate, dict):
        strike_doc = strike_gate.get("score") if isinstance(strike_gate.get("score"), dict) else {}
    signals = (
        strike_doc.get("signals")
        or point.get("strike_signals")
        or []
    )
    for sig in signals[:8]:
        if not isinstance(sig, dict):
            continue
        plain = _signal_plain(sig)
        triggers.append({"id": str(sig.get("id") or ""), "plain": plain})
        sentences.append(plain)

    wire = strike_doc.get("wire_point") or point.get("wire_point") or {}
    if isinstance(wire, dict) and wire.get("confirmed"):
        ev = "; ".join(_clean(str(e)) for e in (wire.get("evidence") or [])[:4])
        wire_line = f"Wire-point lock: {_clean(str(wire.get('label') or ip))} confirmed as the actual hostile endpoint."
        if ev:
            wire_line += f" Evidence: {ev}."
        triggers.append({"id": "wire_point", "plain": wire_line})
        sentences.append(wire_line)

    if point.get("malware_evidence") or strike_doc.get("malware_evidence"):
        line = "Malware-evidence gate passed — campaigns, DPI, C2 ports, or prior kill registry corroborated."
        triggers.append({"id": "malware_evidence", "plain": line})
        sentences.append(line)

    for gk_line in _gatekeeper_trigger_plain(conn):
        triggers.append({"id": "gatekeeper", "plain": gk_line})
        sentences.append(gk_line)

    monitor = point.get("monitor") if isinstance(point.get("monitor"), dict) else conn
    if isinstance(monitor, dict):
        mon_sum = _monitor_summary(monitor)
        if mon_sum:
            line = f"Connection monitor trigger: {mon_sum}."
            triggers.append({"id": "monitor", "plain": line})
            sentences.append(line)

    detail = _clean(str(point.get("detail") or conn.get("reason") or ""))
    if detail:
        line = f"Threat intel detail: {detail}."
        triggers.append({"id": "intel_detail", "plain": line})
        sentences.append(line)

    indicators = hostile.get("indicators") or point.get("indicators") or []
    if isinstance(indicators, list) and indicators:
        ind_line = f"Hostile automation indicators fired: {'; '.join(_clean(str(i)) for i in indicators[:6])}."
        triggers.append({"id": "hostile_ai_indicators", "plain": ind_line})
        sentences.append(ind_line)

    if hostile.get("category_title"):
        line = f"Hostile AI category match: {hostile['category_title']}."
        triggers.append({"id": "hostile_ai_category", "plain": line})
        sentences.append(line)

    if vector and vector not in ("HOSTILE", ""):
        line = f"Threat vector label: {_threat_vector_plain(vector)}."
        triggers.append({"id": "vector", "plain": line})
        sentences.append(line)

    if point.get("strike_certain"):
        line = "Trust Strike reached PINPOINT CERTAIN — malware on the actual wire host."
        triggers.append({"id": "strike_certain", "plain": line})
        sentences.append(line)
    elif point.get("killable"):
        line = "Trust Strike reached manual kill floor — killable on the globe map."
        triggers.append({"id": "killable", "plain": line})
        sentences.append(line)

    if not triggers:
        fallback = (
            f"Baseline threat classification from vector {vector or 'HOSTILE'} "
            f"and live field posture — awaiting stronger corroboration."
        )
        triggers.append({"id": "baseline", "plain": fallback})
        sentences.append(fallback)

    plain = _clean(" ".join(sentences))
    return {
        "threat_trigger_plain": plain,
        "threat_triggers": triggers,
    }


def explain_full(
    *,
    ip: str = "",
    reason: str = "",
    action: str = "KILL",
    point: dict[str, Any] | None = None,
    strike_gate: dict[str, Any] | None = None,
    conn: dict[str, Any] | None = None,
    hostile: dict[str, Any] | None = None,
    strike: dict[str, Any] | None = None,
    vector: str = "",
    process: str = "",
    source: str = "",
    extra_detail: str = "",
) -> dict[str, Any]:
    """Kill reason + threat trigger in one payload for dossiers and panel."""
    kill = explain_kill(
        ip=ip,
        reason=reason,
        action=action,
        point=point,
        strike_gate=strike_gate,
        conn=conn,
        hostile=hostile,
        vector=vector,
        process=process,
        source=source,
        extra_detail=extra_detail,
    )
    threat = explain_threat_trigger(
        ip=ip,
        point=point,
        conn=conn,
        hostile=hostile,
        strike=strike,
        strike_gate=strike_gate,
        vector=vector,
    )
    return {**kill, **threat}


def explain_kill(
    *,
    ip: str,
    reason: str = "",
    action: str = "KILL",
    point: dict[str, Any] | None = None,
    strike_gate: dict[str, Any] | None = None,
    conn: dict[str, Any] | None = None,
    hostile: dict[str, Any] | None = None,
    vector: str = "",
    process: str = "",
    source: str = "",
    extra_detail: str = "",
) -> dict[str, str]:
    """Build plain-English why-killed text for dossiers, logs, and panel."""
    point = point or {}
    conn = conn or {}
    hostile = hostile or {}
    ip = _ip_label(ip or point.get("ip") or conn.get("remote_ip") or hostile.get("ip"))
    reason = _clean(reason or point.get("kill_reason") or conn.get("kill_reason") or "")
    base, full_code = _parse_reason_code(reason)
    vector = _clean(vector or point.get("vector") or hostile.get("vector") or conn.get("vector") or "HOSTILE")
    proc = _process_label(process or point.get("our_process") or point.get("process") or conn.get("process") or hostile.get("process"))
    action_u = _clean(action or "KILL").upper()

    detail = _REASON_TEMPLATES.get(base, "")
    if base == "threat_vector" and ":" in full_code:
        vec = full_code.split(":", 1)[1]
        detail = f"Active threat vector {_threat_vector_plain(vec)} on live traffic to this host."
    elif base == "shell_port" and ":" in full_code:
        port = full_code.split(":", 1)[1]
        detail = f"Suspicious shell/admin port {port} egress from an untrusted process."
    elif base == "suspicious_shell" and ":" in full_code:
        port = full_code.split(":", 1)[1]
        detail = f"Suspicious process using shell port {port} toward this host."
    elif base == "beacon_burst" and ":" in full_code:
        seen = full_code.split(":", 1)[1]
        detail = f"Sustained beacon burst ({seen} observations) — not legitimate consumer traffic."
    elif base == "hostile_ai_destroy" and hostile.get("clarity"):
        detail = _clean(hostile["clarity"])
    elif not detail:
        detail = _clean(extra_detail) or f"Field kit action {full_code or action_u.lower()}."

    monitor_bit = _monitor_summary(point.get("monitor") if isinstance(point.get("monitor"), dict) else conn)
    strike_bit = _strike_signals_plain(strike_gate or point.get("strike_gate"))
    vector_bit = _threat_vector_plain(vector)

    if detail and len(detail) >= 2 and detail[:2].isupper():
        detail_lc = detail.lower()
    elif detail and detail[0].isupper():
        detail_lc = detail[0].lower() + detail[1:]
    else:
        detail_lc = detail
    action_phrase = {
        "KILL": "killed",
        "REKILL": "RE-KILLED",
        "HARDWARE DESTROY": "permanently hardware-destroyed",
    }.get(action_u, action_u.lower())

    sentences: list[str] = [
        f"We {action_phrase} {ip} because {detail_lc}",
    ]
    if proc:
        sentences.append(
            f"A local process on this machine — {proc} — was carrying traffic to that host when we acted."
        )
    if monitor_bit:
        sentences.append(f"Our live connection monitor scored this as hostile: {monitor_bit}.")
    if strike_bit:
        sentences.append(f"Trust Strike pinpoint evidence on the actual wire host: {strike_bit}.")
    if vector_bit and vector not in ("HOSTILE", ""):
        sentences.append(f"This target was classified under the {vector_bit} threat vector.")
    sev = _clean(str(point.get("severity") or hostile.get("severity") or ""))
    if sev:
        sentences.append(f"Severity was {sev}.")
    verdict = _clean(str(point.get("verdict") or conn.get("verdict") or hostile.get("verdict") or ""))
    if verdict:
        sentences.append(f"Gatekeeper verdict: {verdict}.")
    geo_bits = [
        _clean(str(point.get("city") or "")),
        _clean(str(point.get("region") or "")),
        _clean(str(point.get("country") or "")),
    ]
    geo_bits = [g for g in geo_bits if g]
    if geo_bits:
        sentences.append(f"Geography placed the host in {', '.join(geo_bits)}.")
    org = _clean(str(point.get("org") or point.get("asn") or ""))
    if org:
        sentences.append(f"Network ownership: {org}.")
    indicators = hostile.get("indicators") or []
    if isinstance(indicators, list) and indicators:
        sentences.append(f"Hostile automation indicators: {'; '.join(_clean(str(i)) for i in indicators[:5])}.")
    if hostile.get("category_title"):
        sentences.append(f"Hostile AI category: {hostile['category_title']}.")
    if hostile.get("clarity") and base != "hostile_ai_destroy":
        sentences.append(_clean(str(hostile["clarity"])))
    if conn.get("hell_chosen"):
        sentences.append("This flow chose Hell — no mercy, ripped forever on the field drive.")
    if source:
        sentences.append(f"The action ran through the NEXUS {source} defense pass.")
    sentences.append("Friendly guard was honored — no friendly fire on Heaven or trusted infrastructure.")

    plain = _clean(" ".join(sentences))

    return {
        "why_killed_plain": plain,
        "why_killed_short": plain,
        "why_killed_code": full_code or base,
        "why_killed_action": action_u,
    }


def explain_from_archived(archived: dict[str, Any]) -> dict[str, Any]:
    """Retroactive plain English from an archived dossier (older kills without why_* fields)."""
    if not isinstance(archived, dict):
        return explain_full(ip="", reason="target_kill")
    if archived.get("why_killed_plain") and archived.get("threat_trigger_plain"):
        return {
            "why_killed_plain": _clean(archived["why_killed_plain"]),
            "why_killed_short": _clean(archived.get("why_killed_short") or ""),
            "why_killed_code": _clean(archived.get("why_killed_code") or archived.get("reason") or ""),
            "why_killed_action": _clean(archived.get("action") or "KILL"),
            "threat_trigger_plain": _clean(archived["threat_trigger_plain"]),
            "threat_triggers": archived.get("threat_triggers") or [],
        }
    action = "REKILL" if str(archived.get("action") or "").upper() == "REKILL" else (
        "HARDWARE DESTROY" if archived.get("hardware_destroy") else "KILL"
    )
    return explain_full(
        ip=str(archived.get("ip") or ""),
        reason=str(archived.get("reason") or archived.get("kill_reason") or "target_kill"),
        action=action,
        point=archived,
        strike_gate=archived.get("strike_gate") if isinstance(archived.get("strike_gate"), dict) else None,
        vector=str(archived.get("vector") or ""),
        source=str(archived.get("source") or ""),
    )


def attach_to_dossier(dossier: dict[str, Any], why: dict[str, str]) -> dict[str, Any]:
    dossier.update(why)
    return dossier


def main() -> int:
    import json
    import sys

    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: kill-reason-plain.py [explain|threat|full] JSON"}))
        return 1
    cmd = sys.argv[1].strip().lower()
    payload = json.loads(sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
    if cmd == "threat":
        print(json.dumps(explain_threat_trigger(**payload), ensure_ascii=False))
    elif cmd == "full":
        print(json.dumps(explain_full(**payload), ensure_ascii=False))
    else:
        print(json.dumps(explain_kill(**payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())