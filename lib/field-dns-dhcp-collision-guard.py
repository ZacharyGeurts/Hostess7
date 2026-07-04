#!/usr/bin/env pythong
"""DNS/DHCP collision guard — prevent collisions; sole truth and accuracy authority."""
from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-dns-dhcp-collision-guard-doctrine.json"
PANEL = STATE / "field-dns-dhcp-collision-guard-panel.json"
LEDGER = STATE / "field-dns-dhcp-collision-guard.jsonl"
PGREP = Path(os.environ.get("NEXUS_PGREP", "/usr/bin/pgrep"))


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


def _pgrep_pids(pattern: str) -> list[int]:
    pgrep_bin = os.environ.get("NEXUS_PGREP", "/usr/bin/pgrep")
    if not Path(pgrep_bin).is_file():
        return []
    try:
        proc = subprocess.run(
            [pgrep_bin, "-f", pattern],
            capture_output=True,
            text=True,
            timeout=4,
            errors="replace",
        )
        return sorted({int(x) for x in (proc.stdout or "").split() if x.strip().isdigit()})
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return []


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


def _lease_collisions() -> list[dict[str, Any]]:
    leases = _load(STATE / "field-dhcp-leases.json", {"leases": {}})
    pool = leases.get("leases") or {}
    by_ip: dict[str, list[str]] = {}
    rows: list[dict[str, Any]] = []
    for mac, entry in pool.items():
        if not isinstance(entry, dict):
            continue
        ip = str(entry.get("ip") or "")
        if not ip:
            continue
        by_ip.setdefault(ip, []).append(mac)
    for ip, macs in by_ip.items():
        if len(macs) > 1:
            rows.append({
                "kind": "lease_ip_collision",
                "ip": ip,
                "macs": macs,
                "severity": "critical",
            })
    return rows


def _duplicate_process_collisions() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    checks = (
        ("field-dhcp.py serve", "dhcp_serve"),
        ("field-dns.py serve", "dns_serve"),
        ("nexus_field_dhcp_serve_loop", "dhcp_loop"),
        ("nexus_field_dns_serve_loop", "dns_loop"),
    )
    for pattern, label in checks:
        pids = _pgrep_pids(pattern)
        if len(pids) > 1:
            rows.append({
                "kind": "duplicate_serve_process",
                "service": label,
                "pattern": pattern,
                "pids": pids,
                "count": len(pids),
                "severity": "high",
            })
    return rows


def _incumbent_collisions(takeover: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    inc = takeover.get("incumbents") or {}
    if inc.get("incumbent_dns") and not inc.get("nexus_dns_running"):
        rows.append({
            "kind": "incumbent_dns",
            "listeners": inc.get("dns_listeners") or [],
            "severity": "high",
        })
    if inc.get("incumbent_dhcp") and not inc.get("nexus_dhcp_running"):
        rows.append({
            "kind": "incumbent_dhcp",
            "listeners": inc.get("dhcp_listeners") or [],
            "severity": "high",
        })
    foreign = list(inc.get("foreign_nameservers") or [])
    if foreign and str(takeover.get("phase") or "") == "primary":
        rows.append({
            "kind": "foreign_resolver_collision",
            "nameservers": foreign,
            "severity": "critical",
        })
    return rows


def _sole_authority(takeover: dict[str, Any], collisions: list[dict[str, Any]]) -> dict[str, Any]:
    inc = takeover.get("incumbents") or {}
    phase = str(takeover.get("phase") or "observing")
    foreign = list(inc.get("foreign_nameservers") or [])
    dup_proc = [c for c in collisions if c.get("kind") == "duplicate_serve_process"]
    lease_col = [c for c in collisions if c.get("kind") == "lease_ip_collision"]
    inc_col = [c for c in collisions if c.get("kind", "").startswith("incumbent")]
    foreign_col = [c for c in collisions if c.get("kind") == "foreign_resolver_collision"]
    authority_collisions = lease_col + inc_col + foreign_col

    dns_sole = (
        phase == "primary"
        and bool(inc.get("nexus_dns_running"))
        and not inc.get("incumbent_dns")
        and not foreign
    )
    dhcp_sole = (
        phase == "primary"
        and bool(inc.get("nexus_dhcp_running"))
        and not inc.get("incumbent_dhcp")
    )
    truth_sole = dns_sole and not foreign_col
    accuracy = not lease_col and not inc_col and not foreign_col

    return {
        "dns": dns_sole,
        "dhcp": dhcp_sole,
        "truth": truth_sole,
        "accuracy": accuracy,
        "ok": dns_sole and dhcp_sole and truth_sole and accuracy,
        "phase": phase,
        "foreign_resolvers": foreign,
        "collision_count": len(collisions),
        "authority_collision_count": len(authority_collisions),
        "hygiene_warnings": len(dup_proc),
    }


def detect_collisions(*, refresh_takeover: bool = False) -> dict[str, Any]:
    takeover = _load(STATE / "dns-takeover-panel.json", {})
    if refresh_takeover or not takeover.get("phase"):
        mod = _mod("lib/dns-service-takeover.py", "dns_takeover")
        if mod and hasattr(mod, "evaluate_takeover"):
            try:
                takeover = mod.evaluate_takeover(persist=refresh_takeover)
            except Exception:
                takeover = {}

    lease_rows = _lease_collisions()
    proc_rows = _duplicate_process_collisions()
    inc_rows = _incumbent_collisions(takeover)
    collisions = lease_rows + proc_rows + inc_rows
    sole = _sole_authority(takeover, collisions)

    return {
        "schema": "field-dns-dhcp-collision-guard/v1",
        "updated": _utc(),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "collisions": collisions,
        "collision_count": len(collisions),
        "lease_collisions": len(lease_rows),
        "duplicate_processes": len(proc_rows),
        "incumbent_conflicts": len(inc_rows),
        "sole_authority": sole,
        "takeover_phase": takeover.get("phase"),
        "policy": _load(DOCTRINE, {}).get("policy") or {},
    }


def _prune_duplicates(*, dry_run: bool = False) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    patterns = (
        "field-dhcp.py serve",
        "field-dns.py serve",
        "nexus_field_dhcp_serve_loop",
        "nexus_field_dns_serve_loop",
    )
    for pattern in patterns:
        pids = _pgrep_pids(pattern)
        if len(pids) <= 1:
            continue
        keep, drop = pids[0], pids[1:]
        for pid in drop:
            row = {"action": "prune", "pattern": pattern, "pid": pid, "kept": keep}
            if not dry_run:
                try:
                    os.kill(pid, signal.SIGTERM)
                    row["signaled"] = "SIGTERM"
                except OSError as exc:
                    row["error"] = str(exc)
            actions.append(row)
    return actions


def _fix_lease_collisions() -> list[dict[str, Any]]:
    leases = _load(STATE / "field-dhcp-leases.json", {"leases": {}})
    pool = dict(leases.get("leases") or {})
    by_ip: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    fixes: list[dict[str, Any]] = []
    for mac, entry in pool.items():
        if not isinstance(entry, dict):
            continue
        ip = str(entry.get("ip") or "")
        if ip:
            by_ip.setdefault(ip, []).append((mac, entry))
    for ip, items in by_ip.items():
        if len(items) <= 1:
            continue
        items.sort(key=lambda t: str(t[1].get("leased_at") or ""))
        for mac, _ in items[1:]:
            pool.pop(mac, None)
            fixes.append({"action": "drop_duplicate_lease", "ip": ip, "mac": mac})
    if fixes:
        leases["leases"] = pool
        _save(STATE / "field-dhcp-leases.json", leases)
    return fixes


def _ensure_field_services() -> list[dict[str, Any]]:
    """Restore single truth DNS + field DHCP after hygiene prune."""
    actions: list[dict[str, Any]] = []
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    for label, rel, extra in (
        ("dns_serve", "lib/field-dns.py", {}),
        ("dhcp_serve", "lib/field-dhcp.py", {"NEXUS_FIELD_DHCP_BIND": "192.168.47.1"}),
    ):
        if _pgrep_pids(f"{Path(rel).name} serve"):
            continue
        py = INSTALL / rel
        if not py.is_file():
            continue
        log = STATE / f"field-{label}.log"
        try:
            with open(log, "a", encoding="utf-8") as fh:
                subprocess.Popen(
                    [sys.executable, str(py), "serve"],
                    cwd=str(INSTALL),
                    env={**env, **extra},
                    stdout=fh,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            actions.append({"action": "restart_serve", "service": label})
        except OSError as exc:
            actions.append({"action": "restart_serve_failed", "service": label, "error": str(exc)})
    return actions


def enforce_sole_authority(*, prune: bool = True) -> dict[str, Any]:
    """Detect collisions, prune duplicate serves, fix lease dupes, refresh takeover."""
    actions: list[dict[str, Any]] = []
    if prune:
        actions.extend(_prune_duplicates())
        actions.extend(_fix_lease_collisions())
        actions.extend(_ensure_field_services())

    import time
    time.sleep(1.5)

    mod = _mod("lib/dns-service-takeover.py", "dns_takeover")
    if mod and hasattr(mod, "evaluate_takeover"):
        try:
            mod.evaluate_takeover(persist=True)
        except Exception:
            pass

    takeover = _load(STATE / "dns-takeover-panel.json", {})
    if str(takeover.get("phase")) == "primary":
        perms = takeover.get("permissions") or {}
        if perms.get("enforce_resolv") or perms.get("remove_foreign_resolvers"):
            actions.append({"action": "resolv_truth_enforced", "foreign": takeover.get("foreign_enforcement")})

    panel = detect_collisions(refresh_takeover=True)
    panel["api"] = "/api/field-dns-dhcp-collision-guard"
    panel["ok"] = bool((panel.get("sole_authority") or {}).get("ok"))
    panel["enforce"] = {
        "actions": actions,
        "pruned": sum(1 for a in actions if a.get("action") == "prune"),
        "lease_fixes": sum(1 for a in actions if a.get("action") == "drop_duplicate_lease"),
        "sole_authority": panel.get("sole_authority"),
    }
    _save(PANEL, panel)
    _append_ledger({
        "event": "enforce",
        "collision_count": panel.get("collision_count"),
        "sole_ok": (panel.get("sole_authority") or {}).get("ok"),
        "actions": len(actions),
    })
    return panel


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = detect_collisions()
    doc["api"] = "/api/field-dns-dhcp-collision-guard"
    doc["ok"] = bool((doc.get("sole_authority") or {}).get("ok"))
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("detect", "scan"):
        print(json.dumps(detect_collisions(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("enforce", "sole", "guard"):
        prune = "--no-prune" not in sys.argv[2:]
        print(json.dumps(enforce_sole_authority(prune=prune), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-dns-dhcp-collision-guard.py [json|detect|enforce]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())