#!/usr/bin/env python3
"""Field Ping — KILROY iPXE lineage · ICMP ping + traceroute panel API."""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
CACHE = STATE / "field-ping-panel.json"
DOCTRINE = INSTALL / "data" / "field-ping-doctrine.json"

_HOST_RE = re.compile(r"^[a-zA-Z0-9._:-]{1,253}$")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_doctrine() -> dict[str, Any]:
    try:
        return json.loads(DOCTRINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _safe_host(raw: str) -> str | None:
    host = str(raw or "").strip()
    if not host or len(host) > 253:
        return None
    if host.startswith("http://") or host.startswith("https://"):
        try:
            from urllib.parse import urlparse

            host = urlparse(host).hostname or ""
        except Exception:
            return None
    host = host.strip("[]")
    if not host or not _HOST_RE.match(host):
        return None
    if host in ("0.0.0.0", "255.255.255.255"):
        return None
    return host


def _resolve(host: str) -> dict[str, Any]:
    out: dict[str, Any] = {"host": host, "addrs": []}
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        seen: set[str] = set()
        for info in infos:
            addr = info[4][0]
            if addr not in seen:
                seen.add(addr)
                out["addrs"].append(addr)
    except socket.gaierror as exc:
        out["error"] = str(exc)
    return out


def _run(cmd: list[str], timeout: float = 45.0) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except FileNotFoundError:
        return 127, "", "not_found"
    except Exception as exc:
        return 1, "", str(exc)[:200]


def _parse_ping(stdout: str, stderr: str) -> dict[str, Any]:
    text = stdout + "\n" + stderr
    rtts: list[float] = []
    for m in re.finditer(r"time[=<]([0-9.]+)\s*ms", text, re.I):
        try:
            rtts.append(float(m.group(1)))
        except ValueError:
            pass
    stats: dict[str, Any] = {}
    m_loss = re.search(r"(\d+)% packet loss", text)
    if m_loss:
        stats["loss_pct"] = int(m_loss.group(1))
    m_tx = re.search(r"(\d+) packets transmitted", text)
    m_rx = re.search(r"(\d+) (?:packets )?received", text)
    if m_tx:
        stats["tx"] = int(m_tx.group(1))
    if m_rx:
        stats["rx"] = int(m_rx.group(1))
    m_min = re.search(r"min/avg/max/(?:mdev|stddev)\s*=\s*([0-9.]+)/([0-9.]+)/([0-9.]+)", text)
    if m_min:
        stats["min_ms"] = float(m_min.group(1))
        stats["avg_ms"] = float(m_min.group(2))
        stats["max_ms"] = float(m_min.group(3))
    elif rtts:
        stats["min_ms"] = min(rtts)
        stats["max_ms"] = max(rtts)
        stats["avg_ms"] = sum(rtts) / len(rtts)
    return {"rtts_ms": rtts, "stats": stats, "raw": text.strip()}


def _traceroute_bin() -> list[str]:
    for name in ("traceroute", "tracepath", "/usr/sbin/traceroute"):
        if shutil.which(name):
            return [name]
    return []


def _parse_traceroute(stdout: str, stderr: str, tool: str) -> list[dict[str, Any]]:
    text = stdout + "\n" + stderr
    hops: list[dict[str, Any]] = []
    if "tracepath" in tool:
        for line in text.splitlines():
            m = re.match(r"\s*(\d+):\s+([^\s]+)\s+([0-9.]+)ms", line)
            if m:
                hops.append(
                    {
                        "hop": int(m.group(1)),
                        "host": m.group(2),
                        "rtt_ms": float(m.group(3)),
                    }
                )
        return hops
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s+([^\s]+)(?:\s+\(([0-9.]+)\s*ms\))?", line)
        if not m:
            m = re.match(r"\s*(\d+)\s+([^\s]+)\s+([0-9.]+)\s*ms", line)
        if m:
            hop = int(m.group(1))
            host = m.group(2)
            rtt = float(m.group(3)) if m.lastindex and m.lastindex >= 3 and m.group(3) else None
            hops.append({"hop": hop, "host": host, "rtt_ms": rtt})
    return hops


def panel_status() -> dict[str, Any]:
    doc = _load_doctrine()
    ping_bin = shutil.which("ping")
    tr_bin = _traceroute_bin()
    return {
        "ok": True,
        "schema": "field-ping/v1",
        "product": "Field Ping",
        "source": "KILROY iPXE ping_cmd.c · iputils",
        "icmp_available": bool(ping_bin),
        "traceroute_available": bool(tr_bin),
        "ping_bin": ping_bin,
        "traceroute_bin": tr_bin[0] if tr_bin else None,
        "defaults": doc.get("defaults") or {"count": 4, "size": 64, "timeout_s": 2, "max_hops": 30},
        "posture": doc.get("motto") or "ICMP truth · traceroute receipts · no resolver shortcuts",
        "updated": _now(),
    }


def run_ping(body: dict[str, Any]) -> dict[str, Any]:
    host = _safe_host(str(body.get("host") or ""))
    if not host:
        return {"ok": False, "error": "bad_host"}
    count = max(1, min(int(body.get("count") or 4), 32))
    size = max(16, min(int(body.get("size") or 64), 1472))
    timeout_s = max(1, min(int(body.get("timeout_s") or body.get("timeout") or 2), 10))
    resolve = _resolve(host)
    ping_bin = shutil.which("ping")
    if not ping_bin:
        return {"ok": False, "error": "ping_missing", "resolve": resolve}
    t0 = time.monotonic()
    rc, out, err = _run(
        [ping_bin, "-c", str(count), "-s", str(size), "-W", str(timeout_s), host],
        timeout=count * (timeout_s + 2) + 5,
    )
    elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
    parsed = _parse_ping(out, err)
    stats = parsed.get("stats") or {}
    ok = rc == 0 or stats.get("rx", 0) > 0
    result = {
        "ok": ok,
        "mode": "icmp",
        "host": host,
        "resolve": resolve,
        "count": count,
        "size": size,
        "timeout_s": timeout_s,
        "elapsed_ms": elapsed_ms,
        "exit_code": rc,
        "rtts_ms": parsed.get("rtts_ms") or [],
        "stats": stats,
        "raw": parsed.get("raw") or "",
        "at": _now(),
    }
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps({"last_ping": result, "updated": _now()}, indent=2), encoding="utf-8")
    except OSError:
        pass
    return result


def run_traceroute(body: dict[str, Any]) -> dict[str, Any]:
    host = _safe_host(str(body.get("host") or ""))
    if not host:
        return {"ok": False, "error": "bad_host"}
    max_hops = max(1, min(int(body.get("max_hops") or 30), 64))
    resolve = _resolve(host)
    tr = _traceroute_bin()
    if not tr:
        return {"ok": False, "error": "traceroute_missing", "resolve": resolve}
    tool = tr[0]
    if "tracepath" in tool:
        cmd = [tool, "-n", host]
    else:
        cmd = [tool, "-n", "-w", "1", "-m", str(max_hops), host]
    t0 = time.monotonic()
    rc, out, err = _run(cmd, timeout=max_hops * 2 + 15)
    elapsed_ms = round((time.monotonic() - t0) * 1000, 1)
    hops = _parse_traceroute(out, err, tool)
    result = {
        "ok": rc in (0, 1) or bool(hops),
        "mode": "traceroute",
        "tool": tool,
        "host": host,
        "resolve": resolve,
        "max_hops": max_hops,
        "hops": hops,
        "hop_count": len(hops),
        "elapsed_ms": elapsed_ms,
        "exit_code": rc,
        "raw": (out + "\n" + err).strip(),
        "at": _now(),
    }
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        prev = {}
        if CACHE.is_file():
            prev = json.loads(CACHE.read_text(encoding="utf-8"))
        prev["last_trace"] = result
        prev["updated"] = _now()
        CACHE.write_text(json.dumps(prev, indent=2), encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        pass
    return result


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return panel_status()
    if action == "ping":
        return run_ping(body)
    if action in ("traceroute", "trace", "trace_route"):
        return run_traceroute(body)
    if action == "both":
        return {
            "ok": True,
            "panel": panel_status(),
            "ping": run_ping(body),
            "traceroute": run_traceroute(body),
        }
    return {"ok": False, "error": f"unknown_action:{action}"}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").lower()
    if cmd == "json":
        print(json.dumps(panel_status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            body = {}
        print(json.dumps(dispatch(body if isinstance(body, dict) else {}), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-ping.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())