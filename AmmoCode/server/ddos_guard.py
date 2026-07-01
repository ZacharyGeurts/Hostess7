#!/usr/bin/env python3
"""AmmoCode DDoS / abuse guard — per-IP rate limit, connection cap, temporary blocks."""
from __future__ import annotations

import json
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load_doctrine() -> dict[str, Any]:
    path = ROOT / "data" / "ammocode-2027-doctrine.json"
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    sec = {"rate_limit_per_minute": 120, "max_body_bytes": 524288,
           "max_connections_per_ip": 12, "block_duration_seconds": 300}
    return {"security": sec}


@dataclass
class IpState:
    hits: deque[float] = field(default_factory=deque)
    connections: int = 0
    blocked_until: float = 0.0
    violations: int = 0


class DdosGuard:
    def __init__(self, doctrine: dict[str, Any] | None = None) -> None:
        doc = doctrine or _load_doctrine()
        sec = doc.get("security") or {}
        self.rate_limit = int(sec.get("rate_limit_per_minute", 120))
        self.max_body = int(sec.get("max_body_bytes", 524288))
        self.max_conn = int(sec.get("max_connections_per_ip", 12))
        self.block_secs = int(sec.get("block_duration_seconds", 300))
        self._ips: dict[str, IpState] = defaultdict(IpState)
        self._global_blocked: set[str] = set()

    def _state(self, ip: str) -> IpState:
        return self._ips[ip or "unknown"]

    def is_blocked(self, ip: str) -> bool:
        st = self._state(ip)
        now = time.monotonic()
        if ip in self._global_blocked:
            return True
        if st.blocked_until > now:
            return True
        return False

    def block_reason(self, ip: str) -> str:
        if ip in self._global_blocked:
            return "global_block"
        st = self._state(ip)
        if st.blocked_until > time.monotonic():
            return "rate_abuse"
        return ""

    def _prune_hits(self, st: IpState, now: float) -> None:
        cutoff = now - 60.0
        while st.hits and st.hits[0] < cutoff:
            st.hits.popleft()

    def check_request(self, ip: str, body_len: int = 0) -> dict[str, Any]:
        """Return {ok, error?, retry_after?} before handling request."""
        if self.is_blocked(ip):
            return {"ok": False, "error": "blocked", "reason": self.block_reason(ip),
                    "retry_after": max(0, int(self._state(ip).blocked_until - time.monotonic()))}
        if body_len > self.max_body:
            self._violate(ip)
            return {"ok": False, "error": "payload_too_large", "max_bytes": self.max_body}
        now = time.monotonic()
        st = self._state(ip)
        self._prune_hits(st, now)
        st.hits.append(now)
        if len(st.hits) > self.rate_limit:
            self._violate(ip)
            return {"ok": False, "error": "rate_limited", "retry_after": self.block_secs}
        return {"ok": True}

    def _violate(self, ip: str) -> None:
        st = self._state(ip)
        st.violations += 1
        st.blocked_until = time.monotonic() + self.block_secs

    def connection_open(self, ip: str) -> dict[str, Any]:
        if self.is_blocked(ip):
            return {"ok": False, "error": "blocked"}
        st = self._state(ip)
        if st.connections >= self.max_conn:
            self._violate(ip)
            return {"ok": False, "error": "too_many_connections", "max": self.max_conn}
        st.connections += 1
        return {"ok": True}

    def connection_close(self, ip: str) -> None:
        st = self._state(ip)
        st.connections = max(0, st.connections - 1)

    def status(self) -> dict[str, Any]:
        now = time.monotonic()
        active = sum(1 for s in self._ips.values() if s.connections > 0)
        blocked = sum(1 for s in self._ips.values() if s.blocked_until > now)
        return {
            "ok": True,
            "ddos_guard": True,
            "rate_limit_per_minute": self.rate_limit,
            "max_body_bytes": self.max_body,
            "max_connections_per_ip": self.max_conn,
            "active_ips": len(self._ips),
            "active_connections": active,
            "blocked_ips": blocked,
        }


GUARD = DdosGuard()