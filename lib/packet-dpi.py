#!/usr/bin/env pythong
"""NEXUS Packet DPI — deep inspection, English translation, high-confidence heuristics only."""
from __future__ import annotations

import re
from typing import Any

ALERT_MIN_CONFIDENCE = 0.92
ALERT_MIN_SIGNALS = 2

SACRED_IPS = frozenset({
    "8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1", "9.9.9.9", "149.112.112.112",
})

TRUSTED_PROCS = frozenset({
    "firefox", "chrome", "chromium", "brave", "vivaldi", "opera", "msedge",
    "waterfox", "librewolf", "curl", "wget", "systemd-resolved", "sshd",
})

C2_PORTS = frozenset({3004, 3005, 4444, 4443, 5555, 6006, 6606, 8808, 1337, 31337})
EXPLOIT_PORTS = frozenset({4444, 5555, 1337, 31337, 6666, 6667, 9001, 9050})
SHELL_PORTS = frozenset({4444, 5555, 1337, 31337})

FLAG_MEANINGS = {
    "S": "SYN — connection open request",
    "F": "FIN — graceful close",
    "R": "RST — abrupt reset (can indicate scan or block)",
    "P": "PSH — payload data pushed to app",
    ".": "ACK — acknowledgment",
}


def _is_private(ip: str) -> bool:
    if not ip:
        return True
    if ip.startswith("127.") or ip.startswith("10.") or ip.startswith("192.168."):
        return True
    if ip.startswith("172."):
        try:
            second = int(ip.split(".")[1])
            return 16 <= second <= 31
        except (ValueError, IndexError):
            pass
    return False


def _proc_trusted(proc: str) -> bool:
    base = (proc or "").lower().split("/")[-1]
    return base in TRUSTED_PROCS


def translate_deep(pkt: dict[str, Any]) -> str:
    """Long-form English explanation of what this frame is."""
    direction = pkt.get("direction", "?")
    proc = pkt.get("process") or "an unidentified program"
    proto = (pkt.get("protocol") or "ip").upper()
    src = pkt.get("src_ip", "?")
    sport = pkt.get("src_port", "?")
    dst = pkt.get("dst_ip", "?")
    dport = pkt.get("dst_port", "?")
    svc = pkt.get("port_service", "")
    flags = pkt.get("flags") or ""
    length = int(pkt.get("length") or 0)

    flag_txt = ""
    if flags:
        parts = [FLAG_MEANINGS.get(ch, ch) for ch in flags.replace(",", "")]
        flag_txt = " TCP flags: " + "; ".join(parts) + "."

    if direction == "TX":
        lead = f"Outbound from your machine — {proc} transmitted"
    elif direction == "RX":
        lead = f"Inbound to your machine — {proc} received"
    elif direction == "LAN":
        lead = f"Local network only — {proc} exchanged LAN traffic"
    else:
        lead = "Observed on the wire (not clearly local)"

    payload = f" Payload size {length} bytes." if length else " No application payload in this frame."
    service = f" Service class: {svc}." if svc else ""
    endpoints = f" Endpoints {src}:{sport} → {dst}:{dport} ({proto})."
    return f"{lead}.{endpoints}{service}{flag_txt}{payload}"


def analyze_packet(pkt: dict[str, Any]) -> dict[str, Any]:
    """Conservative heuristics — alert only when confidence is very high."""
    signals: list[dict[str, Any]] = []
    proc = (pkt.get("process") or "").lower()
    proc_base = proc.split("/")[-1]
    direction = pkt.get("direction", "")
    src = pkt.get("src_ip", "")
    dst = pkt.get("dst_ip", "")
    sport = int(pkt.get("src_port") or 0)
    dport = int(pkt.get("dst_port") or 0)
    flags = pkt.get("flags") or ""
    length = int(pkt.get("length") or 0)
    proto = pkt.get("protocol", "tcp")

    remote_ip = dst if direction == "TX" else src
    remote_port = dport if direction == "TX" else sport

    intent = {
        "who": proc_base or "unknown",
        "remote": f"{remote_ip}:{remote_port}",
        "direction": direction,
        "purpose": "sacred resolver" if remote_ip in SACRED_IPS else "",
        "proto": proto,
    }

    if remote_ip in SACRED_IPS:
        return {
            "signals": [],
            "confidence": 0.0,
            "alert": False,
            "vectors": [],
            "translation": translate_deep(pkt),
            "verdict": "sacred_excluded",
            "intent": intent,
            "permit_fast": True,
            "segment_block": None,
        }

    if _proc_trusted(proc_base) and remote_port in (80, 443, 853) and length < 9000:
        intent["purpose"] = f"trusted app HTTPS/DNS egress — {proc_base}"
        return {
            "signals": [{"id": "trusted_browser_https", "weight": 0.0}],
            "confidence": 0.0,
            "alert": False,
            "vectors": [],
            "translation": translate_deep(pkt),
            "verdict": "permit_fast",
            "intent": intent,
            "permit_fast": True,
            "segment_block": None,
        }

    if direction == "TX" and remote_port in C2_PORTS and not _proc_trusted(proc_base):
        signals.append({
            "id": "c2_port_egress",
            "vector": "C2_CORRELATION",
            "weight": 0.55,
            "detail": f"egress to port {remote_port} from {proc_base or 'unknown'}",
        })

    if direction == "TX" and remote_port in SHELL_PORTS and "/tmp/" in proc:
        signals.append({
            "id": "tmp_binary_shell_port",
            "vector": "EGRESS_BEACON",
            "weight": 0.98,
            "detail": f"temp binary {proc} → :{remote_port}",
        })

    if "R" in flags and direction == "RX" and length == 0 and remote_port not in (80, 443):
        signals.append({
            "id": "rst_no_payload",
            "vector": "RST_FLOOD",
            "weight": 0.25,
            "detail": f"RST from {remote_ip}:{remote_port}",
        })

    if direction == "TX" and sport > 1024 and remote_port in EXPLOIT_PORTS:
        signals.append({
            "id": "exploit_port_transmit",
            "vector": "PACKET_INJECTION",
            "weight": 0.72,
            "detail": f"transmit to exploit-class port {remote_port}",
        })

    if proto == "udp" and length > 1200 and remote_port not in (53, 123, 443, 853):
        signals.append({
            "id": "large_udp_non_dns",
            "vector": "EGRESS_BEACON",
            "weight": 0.35,
            "detail": f"large UDP {length}B to :{remote_port}",
        })

    if direction == "TX" and not _is_private(remote_ip) and remote_port in (23, 2323, 37215):
        signals.append({
            "id": "cleartext_admin_egress",
            "vector": "CONN_HIJACK",
            "weight": 0.45,
            "detail": f"cleartext admin-class port {remote_port}",
        })

    if "S" in flags and direction == "RX" and remote_port < 1024 and sport > 40000:
        signals.append({
            "id": "inbound_syn_high_ephemeral",
            "vector": "MITM_LISTENER",
            "weight": 0.4,
            "detail": f"inbound SYN to our :{dport} from {remote_ip}",
        })

    confidence = min(0.99, sum(s["weight"] for s in signals))
    vectors = sorted({s["vector"] for s in signals if s.get("vector")})
    max_weight = max((s["weight"] for s in signals), default=0.0)
    alert = (
        confidence >= ALERT_MIN_CONFIDENCE
        and len(signals) >= ALERT_MIN_SIGNALS
    ) or max_weight >= 0.97

    verdict = "observe"
    if alert:
        verdict = "high_confidence_threat"
    elif not signals:
        verdict = "clean"
    elif confidence < 0.5:
        verdict = "low_noise"

    purpose_parts = []
    if signals:
        purpose_parts.append(signals[0].get("detail", ""))
    if remote_port in (80, 443):
        purpose_parts.append("web transport")
    intent["purpose"] = "; ".join(purpose_parts) or translate_deep(pkt)[:120]

    segment_block = None
    if alert and remote_ip and remote_port:
        block_dir = "out" if direction == "TX" else "in"
        primary = signals[0] if signals else {}
        segment_block = {
            "ip": remote_ip,
            "port": remote_port,
            "proto": proto,
            "direction": block_dir,
            "reason": primary.get("id") or (vectors[0] if vectors else "dpi_alert"),
            "scope": "segment",
        }

    return {
        "signals": signals,
        "confidence": round(confidence, 3),
        "alert": alert,
        "vectors": vectors,
        "translation": translate_deep(pkt),
        "verdict": verdict,
        "intent": intent,
        "permit_fast": verdict in ("clean", "permit_fast", "sacred_excluded", "low_noise"),
        "segment_block": segment_block,
    }


def summarize_inspect(recent: list[dict[str, Any]]) -> dict[str, Any]:
    alerts = [p for p in recent if (p.get("dpi") or {}).get("alert")]
    vectors_seen: set[str] = set()
    for p in recent:
        for v in (p.get("dpi") or {}).get("vectors") or []:
            vectors_seen.add(v)
    return {
        "packet_count": len(recent),
        "alert_count": len(alerts),
        "alerts": alerts[-12:],
        "vectors_seen": sorted(vectors_seen),
        "precision_mode": "fail_closed_alerts",
        "alert_threshold": ALERT_MIN_CONFIDENCE,
    }