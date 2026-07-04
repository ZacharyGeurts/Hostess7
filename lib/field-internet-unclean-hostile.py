#!/usr/bin/env pythong
"""Anything making unclean internet is hostile — scan, register, eradicate polluters."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-internet-unclean-hostile-doctrine.json"
PANEL = STATE / "field-internet-unclean-hostile-panel.json"
LEDGER = STATE / "field-internet-unclean-hostile.jsonl"
HOSTILE_TSV = STATE / "field-hostile.tsv"
VECTOR = "INTERNET_UNCLEAN_HOSTILE"

TRUTH_NS = frozenset({"127.0.0.1", "::1", "192.168.47.1"})
RESTRICT_NFT_COMMENTS = (
    "nexus-dns-local",
    "nexus-dns-local-v6",
    "nexus-dns-local-dot",
    "nexus-foreign-dhcp-threat",
    "nexus-foreign-dns-offer-threat",
)


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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _mod(rel: str, name: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_json(rel: str, args: list[str], *, timeout: float = 30.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
    except Exception:
        pass
    return {}


def unclean_is_hostile() -> bool:
    if os.environ.get("NEXUS_FIELD_INTERNET_UNCLEAN_HOSTILE", "1").strip().lower() in ("0", "false", "no", "off"):
        return False
    doctrine = _load(DOCTRINE, {})
    return bool((doctrine.get("policy") or {}).get("unclean_is_hostile", True))


def _existing_hostile_keys() -> set[str]:
    keys: set[str] = set()
    if HOSTILE_TSV.is_file():
        for line in HOSTILE_TSV.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 2:
                keys.add(parts[1].strip())
    return keys


def _register_hostile(key: str, reason: str, *, severity: str = "critical") -> bool:
    if not key or key in _existing_hostile_keys():
        return False
    HOSTILE_TSV.parent.mkdir(parents=True, exist_ok=True)
    if not HOSTILE_TSV.is_file():
        HOSTILE_TSV.write_text("ts\tip\tvector\tseverity\treason\tsource\n", encoding="utf-8")
    safe_reason = reason.replace("\t", " ")[:200]
    with HOSTILE_TSV.open("a", encoding="utf-8") as fh:
        fh.write(f"{_utc()}\t{key}\t{VECTOR}\t{severity}\t{safe_reason}\tinternet-unclean-hostile\n")
    kit = _mod("field_attack_kit", "lib/field-attack-kit.py")
    if kit and hasattr(kit, "register_kill_for_rekill"):
        try:
            kit.register_kill_for_rekill(key, VECTOR, severity, safe_reason, source="internet-unclean-hostile")
        except (OSError, TypeError, ValueError):
            pass
    return True


def _eradicate(key: str, reason: str, *, vector: str = VECTOR) -> dict[str, Any]:
    guard = _mod("dns_threat_guard", "lib/dns-threat-guard.py")
    if guard and hasattr(guard, "eradicate_threat"):
        try:
            return guard.eradicate_threat(client_key=key, reason=reason, vector=vector, direction="ingress")
        except (OSError, TypeError, ValueError):
            pass
    return {"client": key, "reason": reason, "vector": vector, "logged": False}


def _scan_foreign_servers() -> list[dict[str, Any]]:
    cg = _mod("collision_guard", "lib/field-dns-dhcp-collision-guard.py")
    if not cg or not hasattr(cg, "_foreign_server_threats"):
        doc = _run_json("lib/field-dns-dhcp-collision-guard.py", ["threat-scan"], timeout=25)
        return [
            {**t, "unclean_kind": "foreign_server", "hostile_reason": t.get("note") or t.get("kind")}
            for t in doc.get("threats") or []
        ]
    takeover = _load(STATE / "dns-takeover-panel.json", {})
    return [
        {
            **t,
            "unclean_kind": "foreign_server",
            "hostile_reason": t.get("note") or str(t.get("kind")),
        }
        for t in cg._foreign_server_threats(takeover)
    ]


def _scan_delay_threat() -> list[dict[str, Any]]:
    takeover = _load(STATE / "dns-takeover-panel.json", {})
    delay = takeover.get("delay_as_threat") or {}
    if not delay.get("active"):
        return []
    return [{
        "unclean_kind": "delay_as_threat",
        "hostile_reason": delay.get("signal") or "delay_blocks_truth",
        "key": "delay-as-threat",
        "vector": "DELAY_AS_THREAT",
        "severity": "critical",
    }]


def _scan_dns_drift() -> list[dict[str, Any]]:
    drift = _load(STATE / "field-dns-drift-threat-panel.json", {})
    rows: list[dict[str, Any]] = []
    for s in drift.get("servers_updated") or drift.get("drift_servers") or []:
        if not isinstance(s, dict):
            continue
        addr = str(s.get("addr") or s.get("ip") or s.get("nameserver") or "")
        if not addr or addr in TRUTH_NS:
            continue
        rows.append({
            "unclean_kind": "dns_drift",
            "hostile_reason": s.get("reason") or "dns_drift_unclean",
            "key": addr,
            "vector": VECTOR,
            "severity": "high",
        })
    return rows


def _scan_resolv_redirect() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in (Path("/etc/resolv.conf"), STATE / "resolv.conf.nexus-backup"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("nameserver"):
                continue
            ns = line.split()[1] if len(line.split()) > 1 else ""
            if ns and ns not in TRUTH_NS and not ns.startswith("127.0.0."):
                rows.append({
                    "unclean_kind": "isp_dns_redirect",
                    "hostile_reason": f"unclean nameserver {ns}",
                    "key": ns,
                    "vector": VECTOR,
                    "severity": "high",
                })
    return rows


def _scan_telemetry() -> list[dict[str, Any]]:
    log_path = STATE / "hostess7-internet-clean.jsonl"
    if not log_path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if lines:
            last = json.loads(lines[-1])
            q = int((last.get("summary") or {}).get("telemetry_quarantined") or 0)
            d = int((last.get("summary") or {}).get("telemetry_dropped") or 0)
            if q + d > 0:
                rows.append({
                    "unclean_kind": "telemetry_injection",
                    "hostile_reason": f"telemetry unclean quarantined={q} dropped={d}",
                    "key": "telemetry-injection",
                    "vector": "TELEMETRY_UNCLEAN",
                    "severity": "high",
                })
    except (OSError, json.JSONDecodeError):
        pass
    return rows


def _scan_restriction_nft() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    table = os.environ.get("NEXUS_FIREWALL_TABLE", "nexus")
    try:
        proc = subprocess.run(
            ["nft", "list", "ruleset"],
            capture_output=True,
            text=True,
            timeout=5,
            errors="replace",
        )
        text = proc.stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return rows
    for comment in RESTRICT_NFT_COMMENTS:
        if comment in text:
            rows.append({
                "unclean_kind": "access_restriction",
                "hostile_reason": f"restriction rule active: {comment}",
                "key": f"nft:{comment}",
                "vector": VECTOR,
                "severity": "critical",
                "nft_comment": comment,
            })
    return rows


def scan_unclean() -> list[dict[str, Any]]:
    if not unclean_is_hostile():
        return []
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []

    def add(row: dict[str, Any]) -> None:
        key = str(
            row.get("key")
            or row.get("server")
            or row.get("nameserver")
            or row.get("bind")
            or row.get("from")
            or row.get("addr")
            or row.get("nft_comment")
            or row.get("unclean_kind")
        )
        if not key or key in seen:
            return
        seen.add(key)
        row["key"] = key
        row["hostile"] = True
        row["unclean"] = True
        rows.append(row)

    for row in (
        _scan_foreign_servers()
        + _scan_delay_threat()
        + _scan_dns_drift()
        + _scan_resolv_redirect()
        + _scan_telemetry()
        + _scan_restriction_nft()
    ):
        add(row)
    return rows


def fry_unclean(*, scan_first: bool = True) -> dict[str, Any]:
    """Register hostile, eradicate, remove restriction nft if unclean maker."""
    unclean = scan_unclean() if scan_first else []
    registered = 0
    eradicated = 0
    actions: list[dict[str, Any]] = []

    for row in unclean:
        key = str(row.get("key"))
        reason = str(row.get("hostile_reason") or row.get("note") or "internet_unclean")
        vector = str(row.get("vector") or VECTOR)
        if _register_hostile(key, reason, severity=str(row.get("severity") or "critical")):
            registered += 1
            actions.append({"action": "register_hostile", "key": key, "reason": reason})
        entry = _eradicate(key, reason, vector=vector)
        if entry.get("logged") is not False:
            eradicated += 1
            actions.append({"action": "eradicate", "key": key, "vector": vector})

    unrestrict = _run_json("lib/field-internet-unrestrict.py", ["apply"], timeout=20)
    if unrestrict.get("internet_open"):
        actions.append({"action": "internet_open_maintained"})

    panel = build_panel(write=True)
    panel["fry"] = {
        "unclean_count": len(unclean),
        "registered": registered,
        "eradicated": eradicated,
        "actions": actions,
    }
    _save(PANEL, panel)
    _append_ledger({"event": "fry", "unclean": len(unclean), "registered": registered, "eradicated": eradicated})
    return panel


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    unclean = scan_unclean()
    doc = {
        "ok": True,
        "schema": "field-internet-unclean-hostile/v1",
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "boss": doctrine.get("boss", "hostess7"),
        "unclean_is_hostile": unclean_is_hostile(),
        "internet_open_for_users": True,
        "unclean_makers": unclean,
        "unclean_count": len(unclean),
        "hostile_vector": VECTOR,
        "policy": doctrine.get("policy") or {},
        "api": doctrine.get("api", "/api/field-internet-unclean-hostile"),
    }
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("scan", "detect"):
        print(json.dumps({"unclean_makers": scan_unclean(), "unclean_count": len(scan_unclean())}, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("fry", "enforce", "apply", "run"):
        print(json.dumps(fry_unclean(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-internet-unclean-hostile.py [json|panel|scan|fry]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())