#!/usr/bin/env python3
"""GitHub for everyone — civilian passthrough, DNS truth, legal ports, Pages mirrors."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-github-everyone-doctrine.json"
PANEL = STATE / "field-github-everyone-panel.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _run_json(rel: str, args: list[str] | None = None, *, timeout: int = 25) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": f"missing {rel}"}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *(args or ["json"])],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {"ok": False, "error": "script_failed", "script": rel}


def github_domains(doctrine: dict[str, Any] | None = None) -> list[str]:
    doc = doctrine or _load(DOCTRINE, {})
    return list(doc.get("github_domains") or [])


def github_service_ports(doctrine: dict[str, Any] | None = None) -> list[int]:
    doc = doctrine or _load(DOCTRINE, {})
    return [int(p) for p in (doc.get("github_service_ports") or [22, 443, 9418])]


def is_github_domain(host: str, *, doctrine: dict[str, Any] | None = None) -> bool:
    h = str(host or "").lower().strip(".")
    if not h:
        return False
    for dom in github_domains(doctrine):
        d = dom.lower().strip(".")
        if h == d or h.endswith("." + d):
            return True
    return h.endswith(".github.io") or h.endswith(".githubusercontent.com")


def is_github_service_port(port: int | str, *, doctrine: dict[str, Any] | None = None) -> bool:
    try:
        return int(port) in github_service_ports(doctrine)
    except (TypeError, ValueError):
        return False


def everyone_permit(
    *,
    host: str = "",
    port: int | str = 443,
    safe_stack: bool = False,
    h7t_witness: bool = False,
) -> dict[str, Any]:
    """Policy verdict — GitHub always open for everyone; foreign repos may need H7t."""
    doctrine = _load(DOCTRINE, {})
    gh_host = is_github_domain(host, doctrine=doctrine)
    gh_port = is_github_service_port(port, doctrine=doctrine)
    legal = _run_json("lib/field-botnet-legal-ports.py", ["verdict", str(port)], timeout=10)
    if safe_stack:
        return {
            "permit": True,
            "verdict": "USER_OK",
            "reason": "sovereign_safe_stack",
            "github": gh_host,
            "for_everyone": True,
        }
    if gh_host and gh_port:
        return {
            "permit": True,
            "verdict": "USER_OK",
            "reason": "github_for_everyone",
            "github": True,
            "for_everyone": True,
            "h7t_required": bool((doctrine.get("for_everyone") or {}).get("h7t_for_foreign_repos") and not h7t_witness),
            "benefits_factor": 100 if h7t_witness else 1,
        }
    if legal.get("permit"):
        return {**legal, "github": gh_host, "for_everyone": True}
    return {
        "permit": gh_host,
        "verdict": "MONITOR" if gh_host else "SUSPICIOUS",
        "reason": "github_domain" if gh_host else "non_github",
        "github": gh_host,
        "for_everyone": bool((doctrine.get("for_everyone") or {}).get("enabled")),
        "h7t_required": not safe_stack and not h7t_witness,
    }


def panel(*, write: bool = True, fast: bool = False) -> dict[str, Any]:
    if fast and PANEL.is_file():
        cached = _load(PANEL, {})
        if cached.get("schema") == "field-github-everyone-panel/v1":
            cached["updated"] = _utc()
            cached["fast"] = True
            return cached

    doctrine = _load(DOCTRINE, {})
    legacy = _run_json("lib/field-github-legacy.py", ["json"], timeout=12 if fast else 20)
    resilience = _run_json("lib/field-github-resilience.py", ["json"], timeout=12 if fast else 20)
    internet = _run_json("lib/field-internet-unified.py", ["json"], timeout=12 if fast else 25)
    botnet = _run_json("lib/field-botnet-dns-dhcp.py", ["json"], timeout=12 if fast else 20)
    gh_live = legacy.get("github_always") or {}
    open_n = int(gh_live.get("open_count") or 0)
    stable = bool(gh_live.get("stable") or gh_live.get("always_open"))

    doc = {
        "ok": bool(stable or open_n > 0 or resilience.get("degraded_ok")),
        "schema": "field-github-everyone-panel/v1",
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "updated": _utc(),
        "boss": "hostess7",
        "for_everyone": doctrine.get("for_everyone") or {},
        "github_domains": github_domains(doctrine),
        "github_service_ports": github_service_ports(doctrine),
        "fallback_chain": doctrine.get("fallback_chain") or [],
        "github_open": stable or open_n > 0,
        "open_count": open_n,
        "legacy": legacy,
        "resilience": resilience,
        "internet": {"ok": internet.get("ok"), "api": "/api/field-internet"},
        "botnet": {
            "ok": botnet.get("ok"),
            "dns_dhcp": botnet.get("dns_dhcp"),
            "for_everyone": botnet.get("for_everyone"),
            "api": "/api/field-botnet-dns-dhcp",
        },
        "h7t": {
            "api": "/api/field-h7t-truth",
            "rule": "foreign/non-safe payloads → truthed H7t chamber; GitHub stays open for everyone",
        },
        "pages_wire": doctrine.get("pages_wire"),
        "api": "/api/field-github-everyone",
        "fast": fast,
    }
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel(write=True, fast=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "permit" and len(sys.argv) > 2:
        host = sys.argv[2]
        port = sys.argv[3] if len(sys.argv) > 3 else "443"
        out = everyone_permit(host=host, port=port, h7t_witness="--h7t" in sys.argv)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if cmd == "domain" and len(sys.argv) > 2:
        ok = is_github_domain(sys.argv[2])
        print(json.dumps({"ok": True, "host": sys.argv[2], "github": ok}, ensure_ascii=False))
        return 0
    print(json.dumps({"usage": "field-github-everyone.py [panel|permit HOST PORT|domain HOST]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())