#!/usr/bin/env pythong
"""Field Internet Unified — one voice through Hostess 7; GitHub always open; all pipes at once."""
from __future__ import annotations

import importlib.util
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-internet-unified-doctrine.json"
PANEL = STATE / "field-internet-unified-panel.json"
LEDGER = STATE / "field-internet-unified.jsonl"
STAMP = STATE / "field-internet-unified.stamp"


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


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _utc()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _run_json(rel: str, args: list[str] | None = None, *, timeout: int = 45) -> dict[str, Any]:
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


def _probe_url(url: str, *, timeout: float = 4.0) -> dict[str, Any]:
    ctx = ssl.create_default_context()
    started = time.monotonic()
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "FieldInternetUnified/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            return {"ok": True, "status": resp.status, "elapsed_ms": elapsed_ms, "url": url}
    except urllib.error.HTTPError as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return {"ok": exc.code < 500, "status": exc.code, "elapsed_ms": elapsed_ms, "url": url}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)[:120], "url": url}


def _github_legacy_mod() -> Any | None:
    return _import_mod("field_github_legacy", "lib/field-github-legacy.py")


def github_endpoints() -> list[dict[str, Any]]:
    leg = _github_legacy_mod()
    if leg and hasattr(leg, "all_endpoints"):
        return leg.all_endpoints()
    doctrine = _load(DOCTRINE, {})
    return list(doctrine.get("github_always", {}).get("endpoints") or [])


def probe_github(*, write: bool = True, fast: bool = False) -> dict[str, Any]:
    leg = _github_legacy_mod()
    if leg and hasattr(leg, "probe_all"):
        doc = leg.probe_all(write=write, fast=fast)
        doc["schema"] = "field-internet-github/v1"
        if write:
            _save(STATE / "field-internet-github.json", doc)
        return doc
    cache_path = STATE / "field-internet-github.json"
    if fast and cache_path.is_file():
        cached = _load(cache_path, {})
        if cached.get("schema"):
            cached["cached"] = True
            return cached
    eps = github_endpoints()[:3 if fast else 24]
    rows = []
    for ep in eps:
        url = str(ep.get("url") or "")
        if not url:
            continue
        hit = _probe_url(url, timeout=2.5 if fast else 4.0)
        rows.append({**ep, **hit, "always_open": hit.get("ok")})
    open_n = sum(1 for r in rows if r.get("ok"))
    doc = {
        "schema": "field-internet-github/v1",
        "updated": _utc(),
        "ok": open_n > 0,
        "always_open": open_n >= max(2, len(rows) // 2),
        "open_count": open_n,
        "total": len(rows),
        "endpoints": rows,
    }
    if write:
        _save(STATE / "field-internet-github.json", doc)
    return doc


def _botnet_dns_slice(*, fast: bool = True) -> dict[str, Any]:
    cached = _load(STATE / "field-botnet-dns-dhcp-panel.json", {})
    if fast and cached.get("schema") == "field-botnet-dns-dhcp-panel/v1":
        return cached
    return _run_json("lib/field-botnet-dns-dhcp.py", ["keepalive" if fast else "panel"], timeout=15 if fast else 45)


def fielded_bot_network(*, fast: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    reg_path = INSTALL / str(doctrine.get("fielded_bot_network", {}).get("registry") or ".nexus-state/grok-lab-world-registry.json")
    reg = _load(reg_path if reg_path.is_file() else STATE / "grok-lab-world-registry.json", {})
    nodes = reg.get("nodes") or []
    qemu = _run_json("lib/qemu-world-status.py", [], timeout=12 if fast else 30) if not fast else _load(STATE / "qemu-world-pipeline.json", {})
    bot_dns = _botnet_dns_slice(fast=fast)
    return {
        "schema": "field-internet-bot-network/v1",
        "updated": _utc(),
        "ok": True,
        "enabled": bool(doctrine.get("fielded_bot_network", {}).get("enabled")),
        "node_count": len(nodes) if isinstance(nodes, list) else bot_dns.get("bot_network", {}).get("node_count", 0),
        "registry_present": reg_path.is_file() or bool(reg),
        "qemu": qemu,
        "unified_egress": "hostess7",
        "dns_dhcp": {
            "ok": bot_dns.get("ok"),
            "stable": bot_dns.get("stable"),
            "secure": bot_dns.get("secure"),
            "api": bot_dns.get("api", "/api/field-botnet-dns-dhcp"),
            "for_everyone": (doctrine.get("fielded_bot_network") or {}).get("dns_dhcp", {}).get("for_everyone", True),
            "github_control_plane": bot_dns.get("github_control_plane"),
        },
    }


def wire_hostess7(*, fast: bool = False) -> dict[str, Any]:
    lab = _load(STATE / "hostess7-lab-sovereign-panel.json", {})
    if not lab.get("schema"):
        lab = _run_json("lib/hostess7-lab-sovereign.py", ["panel"], timeout=15 if fast else 50)
    zn = _load(STATE / "hostess7-znetwork-wire.json", {})
    if not zn.get("schema"):
        zn = _run_json("lib/hostess7-znetwork-wire.py", ["status"], timeout=12 if fast else 40)
    return {
        "schema": "field-internet-hostess7-wire/v1",
        "updated": _utc(),
        "ok": bool(lab.get("ok") or lab.get("boss") == "hostess7"),
        "boss": "hostess7",
        "lab_sovereign": lab,
        "znetwork_wire": zn,
        "one_voice": True,
    }


def all_pipes(*, fast: bool = True) -> dict[str, Any]:
    bridge = _load(STATE / "field-sovereign-protocol-bridge.json", {}) or _run_json("lib/field-sovereign-protocol-bridge.py", ["json"], timeout=12 if fast else 40)
    gate = _load(STATE / "connection-gatekeeper-panel.json", {})
    if not gate:
        gate = _run_json("lib/connection-gatekeeper.py", [], timeout=12 if fast else 25)
    znet = _load(STATE / "znetwork-status.json", {})
    if not znet.get("schema"):
        znet = _run_json("lib/znetwork-orchestrator.py", ["json"], timeout=12 if fast else 40)
    ammonet = _load(STATE / "ammonet-field-panel.json", {}) or _run_json("lib/ammonet-field.py", ["panel"], timeout=20 if fast else 90)
    bot_dns = _botnet_dns_slice(fast=fast)
    return {
        "schema": "field-internet-pipes/v1",
        "updated": _utc(),
        "sovereign_bridge": bridge,
        "gatekeeper": gate,
        "znetwork": znet,
        "ammonet": {"ok": ammonet.get("ok"), "pipe_percent": (ammonet.get("isp") or {}).get("pipe_percent"), "surface_count": ammonet.get("surface_count")},
        "botnet_dns_dhcp": bot_dns,
        "connected_at_once": bool(
            (bridge.get("secured") or bridge.get("ok"))
            and (znet.get("ok") or znet.get("pipe_pct") or znet.get("internet_pipe_percent"))
            and ammonet.get("ok")
            and (bot_dns.get("ok") or bot_dns.get("stable"))
        ),
    }


def _traffic_shard_keepalive_ok() -> tuple[bool, dict[str, Any]]:
    path = INSTALL / "lib" / "field-github-traffic-shard.py"
    if not path.is_file():
        return True, {}
    try:
        spec = importlib.util.spec_from_file_location("field_github_traffic_shard", path)
        if not spec or not spec.loader:
            return True, {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ok, age = mod.keepalive_allowed()
        return ok, {"age_sec": age, "offload_pct": mod.offload_pct()}
    except (ImportError, OSError, AttributeError):
        return True, {}


def keepalive(*, write: bool = True) -> dict[str, Any]:
    allow, shard_meta = _traffic_shard_keepalive_ok()
    if not allow and PANEL.is_file():
        cached = _load(PANEL, {})
        if cached.get("schema") == "field-internet-unified-panel/v1":
            cached = dict(cached)
            cached["schema"] = "field-internet-keepalive/v1"
            cached["throttled"] = True
            cached["traffic_shard"] = shard_meta
            return cached
    gh = probe_github(write=write, fast=True)
    pipes = all_pipes(fast=True)
    h7 = wire_hostess7(fast=True)
    bots = fielded_bot_network(fast=True)
    ok = bool(gh.get("stable") or gh.get("always_open")) and h7.get("ok", True)
    doc = {
        "schema": "field-internet-keepalive/v1",
        "updated": _utc(),
        "ok": ok,
        "github": gh,
        "github_legacy": {
            "open": gh.get("legacy_open", 0),
            "canonical_open": gh.get("canonical_open", gh.get("open_count")),
            "stable": gh.get("stable"),
            "catalog": gh.get("total_catalog"),
        },
        "pipes": pipes,
        "hostess7": h7,
        "bot_network": bots,
        "one_voice": {
            "boss": "hostess7",
            "module": "lib/field-internet-unified.py",
            "api": "/api/field-internet",
            "motto": "One thing talks everywhere — GitHub always open",
        },
        "traffic_shard": shard_meta,
    }
    if write:
        try:
            STAMP.write_text(_utc() + "\n", encoding="utf-8")
        except OSError:
            pass
        _append({"event": "keepalive", "ok": ok, "github_open": gh.get("open_count")})
    return doc


def panel(*, write: bool = True, fast: bool = False) -> dict[str, Any]:
    if fast and PANEL.is_file():
        cached = _load(PANEL, {})
        if cached.get("schema") == "field-internet-unified-panel/v1":
            cached["updated"] = _utc()
            cached["fast"] = True
            return cached
    doctrine = _load(DOCTRINE, {})
    gh = probe_github(write=False, fast=fast)
    pipes = all_pipes(fast=fast)
    h7 = wire_hostess7(fast=fast)
    bots = fielded_bot_network(fast=fast)
    stamp = STAMP.read_text(encoding="utf-8").strip() if STAMP.is_file() else None

    doc = {
        "ok": True,
        "schema": "field-internet-unified-panel/v1",
        "product": doctrine.get("product", "AmmoNet"),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "updated": _utc(),
        "boss": "hostess7",
        "layer": doctrine.get("layer", 0),
        "one_voice": doctrine.get("one_voice") or {},
        "github_always": {
            **(doctrine.get("github_always") or {}),
            "live": gh,
            "last_keepalive": stamp,
        },
        "fielded_bot_network": bots,
        "hostess7_wire": h7,
        "all_pipes": pipes,
        "wires": doctrine.get("wires") or [],
        "api": "/api/field-internet",
        "keepalive_api": "/api/field-internet/keepalive",
        "ships_with": doctrine.get("ships_with") or ["ammoos", "ammonet"],
    }
    doc["github_legacy"] = {
        "open": gh.get("legacy_open", 0),
        "canonical_open": gh.get("canonical_open", gh.get("open_count")),
        "stable": gh.get("stable"),
        "catalog": gh.get("total_catalog"),
        "module": "lib/field-github-legacy.py",
        "api": "/api/field-github-legacy",
    }
    doc["ok"] = bool(gh.get("stable") or gh.get("always_open") or gh.get("open_count", 0) > 0) and h7.get("ok", True)
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(panel(write=False, fast=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "panel":
        print(json.dumps(panel(write=True, fast=False), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("keepalive", "pulse", "heartbeat"):
        print(json.dumps(keepalive(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "github":
        print(json.dumps(probe_github(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "wire":
        print(json.dumps(wire_hostess7(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-internet-unified.py [panel|keepalive|github|wire]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())