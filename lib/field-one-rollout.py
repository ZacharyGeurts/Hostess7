#!/usr/bin/env python3
"""Field 1 rollout — test secure stack, deploy 10 at a time, double worldwide."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-one-rollout-doctrine.json"
PANEL = STATE / "field-one-rollout-panel.json"
LEDGER = STATE / "field-one-rollout-ledger.jsonl"
REGIONS = INSTALL / "GrokLab" / "deploy" / "world-node-regions.json"


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


def _env() -> dict[str, str]:
    return {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "NEXUS_FIELD_DHCP_FOREIGN_PROBE": "0",
        "NEXUS_FIELD_COLLISION_SOFT_INGRESS": "1",
        "NEXUS_FIELD_DNS_ANY_IP": "1",
        "NEXUS_FIELD_DHCP_ANY_IP": "1",
    }


def _run_json(rel: str, args: list[str], *, timeout: float = 120.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": "missing", "script": rel}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_env(),
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            doc = json.loads(raw)
            if isinstance(doc, dict):
                doc.setdefault("ok", proc.returncode == 0)
                return doc
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                doc = json.loads(line)
                if isinstance(doc, dict):
                    doc.setdefault("ok", proc.returncode == 0)
                    return doc
        return {"ok": proc.returncode == 0, "stdout": raw[:300]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "script": rel}
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc), "script": rel}


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


def _rollout_state() -> dict[str, Any]:
    doc = _load(PANEL, {})
    return {
        "wave": int(doc.get("wave") or 0),
        "deployed_total": int(doc.get("deployed_total") or 0),
        "last_batch": int(doc.get("last_batch") or 0),
        "regions_live": list(doc.get("regions_live") or []),
    }


def test(*, refresh_absorb: bool = False) -> dict[str, Any]:
    """Security test — Field 1 universal ingress must pass before rollout."""
    doctrine = _load(DOCTRINE, {})
    gates = doctrine.get("security_gates") or {}
    policy = doctrine.get("policy") or {}
    checks: list[dict[str, Any]] = []

    absorb = _load(STATE / "field-one-absorb-panel.json", {})
    if refresh_absorb or not absorb.get("ok"):
        absorb = _run_json("lib/field-one.py", ["absorb"], timeout=150)

    checks.append({
        "id": "absorb_ok",
        "ok": bool(absorb.get("ok")),
        "registry": absorb.get("registry_devices"),
        "outside_absorbed": absorb.get("outside_absorbed"),
    })
    checks.append({
        "id": "universal_ingress",
        "ok": bool(absorb.get("universal_ingress") or absorb.get("field_one")),
    })
    checks.append({
        "id": "quarantine_not_kill",
        "ok": (absorb.get("ingress_policy") or policy.get("quarantine_not_kill", True)) == "quarantine_not_kill"
        or policy.get("quarantine_not_kill", True),
    })
    min_reg = int(gates.get("min_registry_devices") or 1)
    reg_count = int(absorb.get("registry_devices") or 0)
    checks.append({
        "id": "registry_floor",
        "ok": reg_count >= min_reg,
        "count": reg_count,
        "floor": min_reg,
    })
    hub = absorb.get("hub") or {}
    checks.append({
        "id": "field_one_hub",
        "ok": bool(hub.get("id") == "field-1" or hub.get("truth")),
        "hub": hub.get("id"),
    })

    any_ip = _run_json("lib/field-dns-dhcp-any-ip.py", ["json"], timeout=15)
    checks.append({
        "id": "wildcard_any_ip",
        "ok": bool(any_ip.get("any_ip") and (any_ip.get("dns") or {}).get("wildcard_v4") == "0.0.0.0"),
    })

    racks = _run_json("lib/field-zachub-qemu-racks.py", ["json"], timeout=30)
    isolated = bool((racks.get("security") or {}).get("internet_isolated", racks.get("internet_isolated")))
    checks.append({
        "id": "racks_internet_isolated",
        "ok": isolated if gates.get("require_internet_isolated", True) else True,
        "rack_count": racks.get("rack_count") or len(racks.get("slots") or []),
    })

    passed = sum(1 for c in checks if c.get("ok"))
    total = len(checks)
    score = int(100 * passed / total) if total else 0
    ok = passed == total

    out = {
        "ok": ok,
        "schema": "field-one-rollout-test/v1",
        "updated": _utc(),
        "motto": doctrine.get("motto"),
        "security_score": score,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "absorb": {
            "registry_devices": reg_count,
            "wan_edges": absorb.get("wan_edges"),
            "hub": hub,
        },
        "ready_for_rollout": ok,
        "api": "/api/field-one-rollout/test",
    }
    _save(PANEL, {**_load(PANEL, {}), "last_test": out, "updated": _utc()})
    _append_ledger({"event": "test", "ok": ok, "score": score})
    return out


def _region_assignments(batch: int, wave: int) -> list[dict[str, Any]]:
    regions_doc = _load(REGIONS, {})
    regions = list(regions_doc.get("regions") or [{"id": "local", "label": "Local"}])
    out: list[dict[str, Any]] = []
    for i in range(batch):
        reg = regions[i % len(regions)]
        out.append({
            "slot": i,
            "region_id": reg.get("id"),
            "region_label": reg.get("label"),
            "wave": wave,
            "field_one_sink": "field-1",
        })
    return out


def rollout(*, batch_size: int | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Roll out Field 1 stack to N racks (default 10) after security test passes."""
    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    batch = int(batch_size or policy.get("batch_size") or 10)
    batch = max(1, min(batch, int(policy.get("max_slots_per_wave") or 64)))

    sec = test(refresh_absorb=False)
    if policy.get("test_before_rollout", True) and not sec.get("ok"):
        return {
            "ok": False,
            "error": "security_test_failed",
            "test": sec,
            "api": "/api/field-one-rollout",
        }

    state = _rollout_state()
    wave = state["wave"] + 1
    racks_mod = _mod("lib/field-zachub-qemu-racks.py", "racks")
    if not racks_mod:
        return {"ok": False, "error": "qemu_racks_missing"}

    status = racks_mod.qemu_pipeline_status()
    slots = racks_mod.build_slots(status)
    os.environ["WORLD_PIPELINE_SLOTS"] = str(max(len(slots), batch))

    provisioned: list[dict[str, Any]] = []
    to_provision = slots[:batch]
    for meta in to_provision:
        if dry_run:
            row = racks_mod.provision_rack(meta, write=False, dry_run=True)
        else:
            row = racks_mod.provision_rack(meta, write=True, dry_run=False)
            root = Path(str(row.get("storage_root") or ""))
            if root.is_dir():
                stamp = root / "field-one-stack.json"
                _save(stamp, {
                    "schema": "field-one-rack-stack/v1",
                    "updated": _utc(),
                    "field_one": True,
                    "universal_ingress": True,
                    "outside_network_absorbed": True,
                    "hub": _load(INSTALL / "data" / "field-one-doctrine.json", {}).get("hub") or {},
                    "wave": wave,
                    "region": _region_assignments(1, wave)[0].get("region_id"),
                    "internet_isolated": True,
                })
        provisioned.append(row)

    regions = _region_assignments(batch, wave)
    deployed = sum(1 for p in provisioned if p.get("ok", True))
    total_deployed = state["deployed_total"] + deployed

    out = {
        "ok": deployed > 0 or dry_run,
        "schema": "field-one-rollout-wave/v1",
        "updated": _utc(),
        "wave": wave,
        "batch_size": batch,
        "deployed_this_wave": deployed,
        "deployed_total": total_deployed,
        "dry_run": dry_run,
        "test_score": sec.get("security_score"),
        "regions": regions,
        "racks": provisioned,
        "motto": "Field 1 rolled out — test green, batch deployed, connections preserved",
        "api": "/api/field-one-rollout",
    }
    panel = _load(PANEL, {})
    panel.update({
        "wave": wave,
        "deployed_total": total_deployed,
        "last_batch": batch,
        "regions_live": list({r["region_id"] for r in regions}),
        "last_rollout": out,
        "updated": _utc(),
    })
    _save(PANEL, panel)
    _append_ledger({"event": "rollout", "wave": wave, "batch": batch, "deployed": deployed})
    return out


def double_worldwide(*, dry_run: bool = False) -> dict[str, Any]:
    """Double deployed nodes worldwide — next wave = current total (min 10)."""
    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    state = _rollout_state()
    current = max(state["deployed_total"], state["last_batch"], int(policy.get("batch_size") or 10))
    next_batch = max(10, current)
    result = rollout(batch_size=next_batch, dry_run=dry_run)
    result["doubled_from"] = current
    result["doubled_to"] = next_batch
    result["phase"] = "double_worldwide"
    _append_ledger({
        "event": "double",
        "from": current,
        "to": next_batch,
        "ok": result.get("ok"),
    })
    return result


def build_panel() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    panel = _load(PANEL, {})
    state = _rollout_state()
    last_test = panel.get("last_test") or {}
    return {
        "ok": True,
        "schema": "field-one-rollout/v1",
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "policy": doctrine.get("policy"),
        "wave": state["wave"],
        "deployed_total": state["deployed_total"],
        "last_batch": state["last_batch"],
        "regions_live": state["regions_live"],
        "last_test_ok": last_test.get("ok"),
        "security_score": last_test.get("security_score"),
        "ready_for_rollout": last_test.get("ready_for_rollout"),
        "api": doctrine.get("api", "/api/field-one-rollout"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    dry = "--dry-run" in sys.argv[2:]
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("test", "security"):
        refresh = "--refresh" in sys.argv[2:]
        print(json.dumps(test(refresh_absorb=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("rollout", "roll", "wave", "deploy"):
        batch = None
        for arg in sys.argv[2:]:
            if arg.isdigit():
                batch = int(arg)
        print(json.dumps(rollout(batch_size=batch, dry_run=dry), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("double", "double-worldwide", "double_worldwide"):
        print(json.dumps(double_worldwide(dry_run=dry), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-one-rollout.py [json|test|rollout [N]|double] [--dry-run] [--refresh]",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())