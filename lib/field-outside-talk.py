#!/usr/bin/env pythong
"""Field Outside Talk — NEXUS egress gate for operator-initiated outbound tools.

Cloned from field-dns / home-protector / gatekeeper-enforce patterns:
build panel JSON, permit nft flow, probe safely, log every session locally.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import socket
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _resolve_state() -> Path:
    fd = os.environ.get("NEXUS_FIELD_DRIVE_STATE", "").strip()
    if fd:
        p = Path(fd)
        if p.is_dir():
            return p
    return Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))


STATE = _resolve_state()
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SEED = INSTALL / "data" / "outside-tools-seed.json"
PANEL_CACHE = STATE / "field-outside-talk-panel.json"
SESSIONS_LOG = STATE / "field-outside-talk-sessions.jsonl"
ACTIVE_JSON = STATE / "field-outside-talk-active.json"
RATELIMIT_JSON = STATE / "field-outside-talk-ratelimit.json"
ASM_BIN = INSTALL / "lib" / "bin" / "field-outside-asm"

RATE_LIMIT_PER_MIN = int(os.environ.get("NEXUS_FIELD_OUTSIDE_RATE", "20"))
PROBE_IO_TIMEOUT = 5.0
MAX_OUTPUT = 4000

# Cloned from connection-gatekeeper.py — never auto-permit without operator force
HARM_PORTS = frozenset({
    4444, 5555, 1337, 31337, 6666, 6667, 9001, 9050, 1080, 3128,
    4443, 8080, 8443, 3004, 3005, 6006, 6606, 8808,
})

HOST_RE = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9\-.]{0,253}[a-zA-Z0-9])?$"
)
IPV4_RE = re.compile(r"^[0-9]{1,3}(\.[0-9]{1,3}){3}$")
PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.)"
)
INJECTION_RE = re.compile(r"[;|&`$<>\\\x00]")
USER_RE = re.compile(r"^[a-zA-Z0-9._-]{0,64}$")
PATH_RE = re.compile(r"^/[a-zA-Z0-9._~/-]{0,256}$")

ASM_MODE_MAP = {
    "ssh": "ssh",
    "banner": "banner",
    "tls": "tls",
    "smtp_starttls": "smtp",
    "smtp": "smtp",
    "https": "tls",
    "http": "http",
    "dns": "dns",
    "udp": "udp",
    "tcp": "tcp",
}


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


def _append_log(row: dict[str, Any]) -> None:
    try:
        SESSIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with SESSIONS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _seed() -> dict[str, Any]:
    return _load_json(SEED, {"schema": "outside-tools-seed/v1", "tools": [], "legal_framework": []})


def _tool_catalog() -> list[dict[str, Any]]:
    return list(_seed().get("tools") or [])


def _tool_by_id(tool_id: str) -> dict[str, Any] | None:
    tid = str(tool_id or "").strip().lower()
    for tool in _tool_catalog():
        if str(tool.get("id") or "").lower() == tid:
            return tool
    return None


def _firewall_state() -> dict[str, Any]:
    fw_state = STATE / "firewall.state"
    active = False
    try:
        if fw_state.is_file():
            active = "active=1" in fw_state.read_text(encoding="utf-8", errors="replace")
    except OSError:
        active = False
    blocks = 0
    blocks_path = STATE / "firewall-blocks.tsv"
    try:
        if blocks_path.is_file():
            lines = blocks_path.read_text(encoding="utf-8", errors="replace").splitlines()
            blocks = max(0, len(lines) - 1)
    except OSError:
        blocks = 0
    return {
        "enabled": os.environ.get("NEXUS_FIREWALL", "1") == "1",
        "active": active,
        "blocks": blocks,
        "permit_duration_s": int(os.environ.get("NEXUS_FIREWALL_PERMIT_FLOW_DURATION", "7200")),
    }


def _run_bash(inner: str, timeout: int = 25) -> tuple[int, str]:
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
    env["NEXUS_STATE_DIR"] = str(STATE)
    prelude = (
        f"source {shlex.quote(str(INSTALL / 'lib' / 'nexus-common.sh'))} && "
        f"nexus_load_config 2>/dev/null; "
        f"source {shlex.quote(str(INSTALL / 'lib' / 'firewall-sentinel.sh'))} && "
        f"source {shlex.quote(str(INSTALL / 'lib' / 'firewall-trust.sh'))} 2>/dev/null; "
        f"source {shlex.quote(str(INSTALL / 'lib' / 'self-access.sh'))} 2>/dev/null; "
    )
    proc = subprocess.run(
        ["bash", "-c", prelude + inner],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _firewall_permit(ip: str, port: int, reason: str) -> dict[str, Any]:
    if not ip or not IPV4_RE.match(ip):
        return {"ok": False, "error": "invalid_ip", "ip": ip}
    if PRIVATE_RE.match(ip):
        return {"ok": True, "skipped": "private_ip", "ip": ip, "port": port}
    safe_ip = ip.replace("'", "'\"'\"'")
    safe_reason = reason.replace("'", "'\"'\"'")
    rc, out = _run_bash(
        f"nexus_firewall_permit_flow out '{safe_ip}' '{port}' "
        f"'${{NEXUS_FIREWALL_PERMIT_FLOW_DURATION:-7200}}' '{safe_reason}'"
    )
    return {"ok": rc == 0, "ip": ip, "port": port, "reason": reason, "detail": out[:500]}


def _firewall_trust(ip: str, label: str) -> dict[str, Any]:
    if not ip or not IPV4_RE.match(ip):
        return {"ok": False, "error": "invalid_ip"}
    safe_ip = ip.replace("'", "'\"'\"'")
    safe_label = label.replace("'", "'\"'\"'")
    rc, out = _run_bash(
        f"nexus_firewall_authorize_ip '{safe_ip}' out '{safe_label}' 'field-outside-talk'"
    )
    return {"ok": rc == 0, "ip": ip, "label": label, "detail": out[:300]}


def _resolve_host(host: str) -> dict[str, Any]:
    raw = str(host or "").strip()
    if not raw:
        return {"ok": False, "error": "missing_host"}
    if IPV4_RE.match(raw):
        return {"ok": True, "host": raw, "ips": [raw], "canonical": raw}
    if not HOST_RE.match(raw) and "." not in raw:
        return {"ok": False, "error": "invalid_host", "host": raw}
    try:
        infos = socket.getaddrinfo(raw, None, socket.AF_INET, socket.SOCK_STREAM)
        ips = []
        for info in infos:
            ip = info[4][0]
            if ip not in ips:
                ips.append(ip)
        if not ips:
            return {"ok": False, "error": "no_a_record", "host": raw}
        return {"ok": True, "host": raw, "ips": ips, "canonical": raw}
    except socket.gaierror as exc:
        return {"ok": False, "error": "resolve_failed", "host": raw, "detail": str(exc)}


def _asm_ready() -> bool:
    return ASM_BIN.is_file() and os.access(ASM_BIN, os.X_OK)


def _hardening_status() -> dict[str, Any]:
    return {
        "shell_deps_stripped": True,
        "asm_ready": _asm_ready(),
        "asm_binary": str(ASM_BIN),
        "fallback_engine": "socket",
        "rate_limit_per_min": RATE_LIMIT_PER_MIN,
        "max_output_bytes": MAX_OUTPUT,
        "probe_io_timeout_s": PROBE_IO_TIMEOUT,
    }


def _sanitize_host(host: str) -> str | None:
    raw = str(host or "").strip()[:253]
    if not raw or INJECTION_RE.search(raw):
        return None
    return raw


def _sanitize_path(path: str) -> str:
    p = str(path or "/").strip() or "/"
    if not p.startswith("/"):
        p = f"/{p}"
    if not PATH_RE.match(p):
        return "/"
    return p[:256]


def _sanitize_user(username: str) -> str:
    user = str(username or "").strip()
    if user and not USER_RE.match(user):
        return ""
    return user[:64]


def _rate_limit_ok() -> bool:
    now = datetime.now(timezone.utc)
    doc = _load_json(RATELIMIT_JSON, {"hits": []})
    hits = [h for h in doc.get("hits") or [] if isinstance(h, str)]
    cutoff = now.timestamp() - 60
    fresh: list[str] = []
    for h in hits:
        try:
            ts = datetime.fromisoformat(h.replace("Z", "+00:00")).timestamp()
            if ts >= cutoff:
                fresh.append(h)
        except ValueError:
            continue
    if len(fresh) >= RATE_LIMIT_PER_MIN:
        return False
    fresh.append(_now())
    _save_json(RATELIMIT_JSON, {"hits": fresh[-RATE_LIMIT_PER_MIN * 2:]})
    return True


def _validate_request(
    tool_id: str,
    host: str,
    port: int,
    *,
    force: bool = False,
    username: str = "",
    path: str = "/",
) -> dict[str, Any]:
    tool = _tool_by_id(tool_id)
    if not tool:
        return {"ok": False, "error": "unknown_tool", "tool_id": tool_id}
    clean_host = _sanitize_host(host)
    if not clean_host:
        return {"ok": False, "error": "invalid_host", "host": host}
    if port < 1 or port > 65535:
        return {"ok": False, "error": "invalid_port", "port": port}
    if port in HARM_PORTS and not force:
        return {
            "ok": False,
            "error": "harm_port_blocked",
            "port": port,
            "hint": "C2/shell relay class port — use force only if you own the endpoint.",
        }
    if _sanitize_user(username) != str(username or "").strip() and str(username or "").strip():
        return {"ok": False, "error": "invalid_username"}
    _sanitize_path(path)
    if not _rate_limit_ok():
        return {
            "ok": False,
            "error": "rate_limited",
            "hint": f"Max {RATE_LIMIT_PER_MIN} outside operations per minute.",
        }
    resolved = _resolve_host(clean_host)
    if not resolved.get("ok"):
        return {**resolved, "tool": tool}
    return {"ok": True, "tool": tool, "resolved": resolved, "port": port}


def _asm_mode(tool: dict[str, Any], proto: str) -> str:
    kind = str(tool.get("asm") or tool.get("probe") or "tcp").lower()
    if kind in ASM_MODE_MAP:
        return ASM_MODE_MAP[kind]
    if str(proto or tool.get("proto") or "tcp").lower() == "udp":
        return "udp"
    return "tcp"


def _probe_asm(
    mode: str,
    host: str,
    port: int,
    path: str = "/",
) -> tuple[int, str, str]:
    if not _asm_ready():
        return 127, "", "socket"
    args = [str(ASM_BIN), mode, host, str(port)]
    if mode == "http":
        args.append(_sanitize_path(path))
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=int(PROBE_IO_TIMEOUT + 3),
        )
        line = (proc.stdout or "").strip().splitlines()
        if not line:
            return proc.returncode, (proc.stderr or "asm: no output")[:MAX_OUTPUT], "asm"
        try:
            doc = json.loads(line[-1])
            out = str(doc.get("output") or "")
            ok = bool(doc.get("ok"))
            eng = str(doc.get("engine") or "asm")
            return (0 if ok else 1), out[:MAX_OUTPUT], eng
        except json.JSONDecodeError:
            return proc.returncode, (proc.stdout or proc.stderr or "")[:MAX_OUTPUT], "asm"
    except subprocess.TimeoutExpired:
        return 124, "asm: probe timeout", "asm"
    except OSError as exc:
        return 1, str(exc), "asm"


def _socket_tcp_connect(host: str, port: int) -> tuple[int, str, str]:
    try:
        with socket.create_connection((host, port), timeout=PROBE_IO_TIMEOUT):
            return 0, "socket: tcp connect ok", "socket"
    except OSError as exc:
        return 1, f"socket: tcp failed — {exc}", "socket"


def _socket_udp(host: str, port: int) -> tuple[int, str, str]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(PROBE_IO_TIMEOUT)
        sock.sendto(b"NXS", (host, port))
        sock.close()
        return 0, "socket: udp send ok", "socket"
    except OSError as exc:
        return 1, f"socket: udp failed — {exc}", "socket"


def _socket_read_banner(host: str, port: int) -> tuple[int, str, str]:
    try:
        with socket.create_connection((host, port), timeout=PROBE_IO_TIMEOUT) as sock:
            sock.settimeout(PROBE_IO_TIMEOUT)
            data = sock.recv(512)
            text = data.decode("utf-8", errors="replace")
            return 0, text or "socket: connected (no banner)", "socket"
    except OSError as exc:
        return 1, f"socket: banner failed — {exc}", "socket"


def _socket_http(host: str, port: int, path: str) -> tuple[int, str, str]:
    p = _sanitize_path(path)
    req = f"HEAD {p} HTTP/1.0\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    try:
        with socket.create_connection((host, port), timeout=PROBE_IO_TIMEOUT) as sock:
            sock.settimeout(PROBE_IO_TIMEOUT)
            sock.sendall(req.encode("ascii", errors="ignore"))
            data = sock.recv(512)
            return 0, data.decode("utf-8", errors="replace"), "socket"
    except OSError as exc:
        return 1, f"socket: http failed — {exc}", "socket"


def _socket_tls(host: str, port: int) -> tuple[int, str, str]:
    import ssl

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=PROBE_IO_TIMEOUT) as raw:
            with ctx.wrap_socket(raw, server_hostname=host) as tls:
                tls.settimeout(PROBE_IO_TIMEOUT)
                try:
                    tls.send(b"")
                except OSError:
                    pass
                try:
                    data = tls.recv(256)
                except OSError:
                    data = b""
                if data:
                    return 0, data.decode("utf-8", errors="replace"), "socket"
                return 0, f"socket: tls handshake ok ({tls.version()})", "socket"
    except OSError as exc:
        return 1, f"socket: tls failed — {exc}", "socket"


def _socket_smtp(host: str, port: int) -> tuple[int, str, str]:
    try:
        with socket.create_connection((host, port), timeout=PROBE_IO_TIMEOUT) as sock:
            sock.settimeout(PROBE_IO_TIMEOUT)
            banner = sock.recv(512).decode("utf-8", errors="replace")
            sock.sendall(b"EHLO nexus-field.local\r\n")
            reply = sock.recv(512).decode("utf-8", errors="replace")
            return 0, f"{banner}\n{reply}".strip(), "socket"
    except OSError as exc:
        return 1, f"socket: smtp failed — {exc}", "socket"


def _socket_dns(host: str, port: int) -> tuple[int, str, str]:
    q = (
        b"\x4e\x58\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
        b"\x07example\x03com\x00\x00\x01\x00\x01"
    )
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(PROBE_IO_TIMEOUT)
        sock.sendto(q, (host, port))
        data, _ = sock.recvfrom(512)
        sock.close()
        return 0, f"socket: dns response {len(data)} bytes", "socket"
    except OSError as exc:
        return 1, f"socket: dns failed — {exc}", "socket"


def _socket_ssh(host: str, port: int) -> tuple[int, str, str]:
    rc, out, eng = _socket_read_banner(host, port)
    if rc == 0 and out.startswith("SSH-"):
        return rc, out, eng
    return 1, out if out else "socket: no SSH banner", eng


def _probe_socket(mode: str, host: str, port: int, path: str = "/") -> tuple[int, str, str]:
    if mode == "udp":
        return _socket_udp(host, port)
    if mode == "banner":
        return _socket_read_banner(host, port)
    if mode == "ssh":
        return _socket_ssh(host, port)
    if mode == "http":
        return _socket_http(host, port, path)
    if mode == "tls":
        return _socket_tls(host, port)
    if mode == "smtp":
        return _socket_smtp(host, port)
    if mode == "dns":
        return _socket_dns(host, port)
    return _socket_tcp_connect(host, port)


def _probe_tool(
    tool: dict[str, Any],
    host: str,
    port: int,
    *,
    username: str = "",
    path: str = "/",
    proto: str = "",
) -> tuple[int, str, str]:
    _ = _sanitize_user(username)  # username reserved for client hint only — no shell ssh
    mode = _asm_mode(tool, proto)
    path = _sanitize_path(path)
    if _asm_ready():
        rc, out, eng = _probe_asm(mode, host, port, path)
        if rc != 127:
            return rc, out, eng
    return _probe_socket(mode, host, port, path)


def _recent_sessions(limit: int = 24) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not SESSIONS_LOG.is_file():
        return rows
    try:
        lines = SESSIONS_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[-limit * 2:]:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return list(reversed(rows[-limit:]))


def _engineer_briefing(fw: dict[str, Any], sessions: list[dict[str, Any]]) -> dict[str, Any]:
    seed = _seed()
    alerts: list[dict[str, Any]] = []
    if not fw.get("enabled"):
        alerts.append({
            "level": "high",
            "code": "firewall_off",
            "title": "Firewall module disabled",
            "detail": "NEXUS_FIREWALL=0 — egress permits may not apply.",
            "action": "Set NEXUS_FIREWALL=1 in nexus.conf and restart nexus-genius",
        })
    elif not fw.get("active"):
        alerts.append({
            "level": "medium",
            "code": "firewall_inactive",
            "title": "nftables table not active",
            "detail": "Permit calls will attempt takeover on first connect.",
            "action": "sudo systemctl restart nexus-genius",
        })
    if not _asm_ready():
        alerts.append({
            "level": "info",
            "code": "asm_build_pending",
            "title": "ASM probe not built — socket fallback active",
            "detail": "Run nexus_field_outside_asm_build or reinstall to enable field-fast ASM engine.",
            "action": "gcc build via field-outside-asm.sh",
        })
    recent_fail = [s for s in sessions[:6] if not s.get("ok")]
    if len(recent_fail) >= 3:
        alerts.append({
            "level": "info",
            "code": "recent_probe_fails",
            "title": "Recent outbound probes failing",
            "detail": f"{len(recent_fail)} of last 6 sessions did not reach remote — check host, port, or upstream block.",
            "action": "Verify target is authorized and reachable",
        })
    return {
        "headline": "Outside Talk — NEXUS egress gate",
        "lead": seed.get("motto") or "Operator-initiated outbound only.",
        "legal_notice": seed.get("legal_notice") or "",
        "alerts": alerts,
        "healthy": not any(a.get("level") in ("critical", "high") for a in alerts),
        "quick_facts": {
            "firewall_active": bool(fw.get("active")),
            "firewall_blocks": fw.get("blocks", 0),
            "tool_count": len(_tool_catalog()),
            "sessions_logged": len(sessions),
            "permit_duration_s": fw.get("permit_duration_s", 7200),
            "asm_ready": _asm_ready(),
            "engine": "asm" if _asm_ready() else "socket",
        },
    }


def build_panel() -> dict[str, Any]:
    fw = _firewall_state()
    sessions = _recent_sessions()
    seed = _seed()
    active = _load_json(ACTIVE_JSON, {"sessions": []})
    doc: dict[str, Any] = {
        "schema": "field-outside-talk/v1",
        "updated": _now(),
        "title": "Outside Talk",
        "role": seed.get("role") or "egress_gate",
        "motto": seed.get("motto") or "",
        "legal_notice": seed.get("legal_notice") or "",
        "tools": _tool_catalog(),
        "legal_framework": seed.get("legal_framework") or [],
        "firewall": fw,
        "engineer_briefing": _engineer_briefing(fw, sessions),
        "recent_sessions": sessions,
        "active_sessions": active.get("sessions") or [],
        "harm_ports": sorted(HARM_PORTS),
        "hardening": _hardening_status(),
    }
    tmp = PANEL_CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PANEL_CACHE)
    return doc


def panel_json() -> dict[str, Any]:
    if PANEL_CACHE.is_file():
        try:
            return json.loads(PANEL_CACHE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return build_panel()


def outside_connect(payload: dict[str, Any]) -> dict[str, Any]:
    tool_id = str(payload.get("tool") or payload.get("tool_id") or "").strip()
    host = str(payload.get("host") or "").strip()
    tool = _tool_by_id(tool_id)
    port = int(payload.get("port") or (tool or {}).get("port") or 0)
    force = payload.get("force") in (True, 1, "1", "true", "yes", "on")
    trust = payload.get("trust_forever") in (True, 1, "1", "true", "yes", "on")
    username = str(payload.get("username") or "").strip()
    path = str(payload.get("path") or "/").strip() or "/"
    proto = str(payload.get("proto") or (tool or {}).get("proto") or "tcp").strip().lower()

    checked = _validate_request(
        tool_id, host, port, force=force, username=username, path=path,
    )
    if not checked.get("ok"):
        return {"ok": False, **checked}

    tool = checked["tool"]
    resolved = checked["resolved"]
    target_ip = resolved["ips"][0]
    target_host = resolved["host"]

    permits: list[dict[str, Any]] = []
    for ip in resolved["ips"][:3]:
        permits.append(_firewall_permit(ip, port, f"outside-talk:{tool_id}"))

    trust_result = None
    if trust:
        trust_result = _firewall_trust(target_ip, f"outside:{tool_id}:{target_host}")

    prc, pout, engine = _probe_tool(tool, target_host, port, username=username, path=path, proto=proto)
    session_id = str(uuid.uuid4())[:12]
    row = {
        "ts": _now(),
        "session_id": session_id,
        "action": "connect",
        "tool": tool_id,
        "tool_label": tool.get("label"),
        "host": target_host,
        "ip": target_ip,
        "port": port,
        "proto": proto,
        "secure": bool(tool.get("secure")),
        "ok": prc == 0,
        "probe_rc": prc,
        "engine": engine,
        "output": pout[:MAX_OUTPUT],
        "permits": permits,
        "trust": trust_result,
        "operator_initiated": True,
    }
    _append_log(row)

    active = _load_json(ACTIVE_JSON, {"sessions": []})
    sessions = list(active.get("sessions") or [])
    sessions.insert(0, {
        "session_id": session_id,
        "tool": tool_id,
        "host": target_host,
        "ip": target_ip,
        "port": port,
        "since": row["ts"],
    })
    active["sessions"] = sessions[:16]
    active["updated"] = _now()
    _save_json(ACTIVE_JSON, active)

    return {
        "ok": prc == 0,
        "session_id": session_id,
        "tool": tool_id,
        "host": target_host,
        "ip": target_ip,
        "port": port,
        "secure": bool(tool.get("secure")),
        "probe_rc": prc,
        "output": pout[:MAX_OUTPUT],
        "engine": engine,
        "permits": permits,
        "trust": trust_result,
        "hint": _client_hint(tool, target_host, port, username),
    }


def _client_hint(tool: dict[str, Any], host: str, port: int, username: str) -> str:
    tid = str(tool.get("id") or "")
    user = username or "user"
    if tid == "ssh":
        return f"Egress permitted. Interactive: ssh -p {port} {user}@{host}"
    if tid in ("smtp", "smtp_plain"):
        return f"Egress permitted. Use Thunderbird or: openssl s_client -starttls smtp -connect {host}:{port}"
    if tid == "imap":
        return f"Egress permitted. IMAP client → {host}:{port} (TLS)"
    if tid == "telnet":
        return f"Egress permitted. Cleartext: telnet {host} {port}"
    if tid in ("https", "http"):
        scheme = "https" if tid == "https" else "http"
        return f"Egress permitted. Browser: {scheme}://{host}:{port}/"
    return f"Egress permitted to {host}:{port} — use your client application."


def outside_probe(payload: dict[str, Any]) -> dict[str, Any]:
    """Probe only — no firewall permit (read-only reachability check from existing rules)."""
    tool_id = str(payload.get("tool") or "").strip()
    host = str(payload.get("host") or "").strip()
    tool = _tool_by_id(tool_id)
    port = int(payload.get("port") or (tool or {}).get("port") or 0)
    force = payload.get("force") in (True, 1, "1", "true", "yes", "on")
    checked = _validate_request(
        tool_id,
        host,
        port,
        force=force,
        username=str(payload.get("username") or ""),
        path=str(payload.get("path") or "/"),
    )
    if not checked.get("ok"):
        return {"ok": False, **checked}
    tool = checked["tool"]
    resolved = checked["resolved"]
    target_host = resolved["host"]
    prc, pout, engine = _probe_tool(
        tool,
        target_host,
        port,
        username=str(payload.get("username") or ""),
        path=str(payload.get("path") or "/"),
        proto=str(payload.get("proto") or tool.get("proto") or "tcp"),
    )
    row = {
        "ts": _now(),
        "action": "probe",
        "tool": tool_id,
        "host": target_host,
        "ip": resolved["ips"][0],
        "port": port,
        "ok": prc == 0,
        "probe_rc": prc,
        "engine": engine,
        "output": pout[:2000],
    }
    _append_log(row)
    return {"ok": prc == 0, **row}


def outside_disconnect(payload: dict[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "").strip()
    active = _load_json(ACTIVE_JSON, {"sessions": []})
    sessions = list(active.get("sessions") or [])
    kept = [s for s in sessions if str(s.get("session_id")) != session_id]
    active["sessions"] = kept
    active["updated"] = _now()
    _save_json(ACTIVE_JSON, active)
    _append_log({"ts": _now(), "action": "disconnect", "session_id": session_id})
    return {"ok": True, "session_id": session_id, "active_count": len(kept)}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: field-outside-talk.py [build|json|connect|probe|disconnect]", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "connect":
        raw = sys.argv[2] if len(sys.argv) > 2 else "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
        print(json.dumps(outside_connect(payload), ensure_ascii=False))
        return 0
    if cmd == "probe":
        raw = sys.argv[2] if len(sys.argv) > 2 else "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
        print(json.dumps(outside_probe(payload), ensure_ascii=False))
        return 0
    if cmd == "disconnect":
        raw = sys.argv[2] if len(sys.argv) > 2 else "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
        print(json.dumps(outside_disconnect(payload), ensure_ascii=False))
        return 0
    print("usage: field-outside-talk.py [build|json|connect|probe|disconnect]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())