#!/usr/bin/env python3
"""Geographic primary mesh — host + every QEMU rack are Field 1 primary; geography routes clients."""
from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-rack-failover-doctrine.json"
PANEL = STATE / "field-rack-failover-panel.json"
HEARTBEAT = STATE / "field-host-heartbeat.json"
LEDGER = STATE / "field-rack-failover-ledger.jsonl"
H7_API = INSTALL / "Hostess7" / "docs" / "api"
RACKS_ROOT = INSTALL / "GrokLab" / "deploy" / "qemu-racks"
METROS = INSTALL / "data" / "world-global-metros.json"


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


def _run_py(rel: str, args: list[str], *, timeout: int = 120) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "skipped": rel}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(INSTALL),
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        raw = (proc.stdout or "").strip()
        if not raw:
            return {"ok": proc.returncode == 0, "stderr": (proc.stderr or "")[:200]}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            depth = 0
            buf: list[str] = []
            for ch in raw:
                if ch == "{":
                    if depth == 0:
                        buf = ["{"]
                    else:
                        buf.append(ch)
                    depth += 1
                elif ch == "}":
                    if depth > 0:
                        buf.append(ch)
                        depth -= 1
                        if depth == 0:
                            return json.loads("".join(buf))
                elif depth > 0:
                    buf.append(ch)
            return {"ok": proc.returncode == 0, "raw": raw[:300]}
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "error": str(exc)[:160]}


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _policy() -> dict[str, Any]:
    return doctrine().get("policy") or {}


def _heartbeat_max_age() -> int:
    return int(_policy().get("host_heartbeat_sec") or 90)


def _geography_for_slot(slot: dict[str, Any]) -> dict[str, Any]:
    """Map rack slot to geographic region — only geography differentiates nodes."""
    metros_doc = _load(METROS, {})
    metros = metros_doc.get("metros") or []
    idx = int(slot.get("slot") or 0)
    if metros:
        metro = metros[idx % len(metros)]
        if isinstance(metro, dict):
            return {
                "region_id": metro.get("region_id") or metro.get("id") or "local",
                "metro_id": metro.get("id"),
                "metro_label": metro.get("label"),
                "geography_only": True,
            }
    tunnel = slot.get("tunnel")
    return {
        "region_id": f"port-{tunnel}" if tunnel else "local",
        "metro_id": slot.get("field_id"),
        "geography_only": True,
    }


def heartbeat(*, write: bool = True) -> dict[str, Any]:
    hostname = socket.gethostname()
    out = {
        "schema": "field-host-heartbeat/v1",
        "updated": _utc(),
        "host": hostname,
        "host_up": True,
        "pid": os.getpid(),
        "authority": "all_primary",
        "geography_only": True,
    }
    if write:
        _save(HEARTBEAT, out)
    return out


def _host_is_down() -> tuple[bool, str]:
    forced = os.environ.get("FIELD_HOST_DOWN", "").strip().lower() in ("1", "true", "yes")
    if forced:
        return True, "forced"
    hb = _load(HEARTBEAT, {})
    if not hb.get("updated"):
        return False, "no_heartbeat_yet"
    try:
        ts = datetime.strptime(str(hb["updated"]), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > _heartbeat_max_age():
            return True, f"stale_{int(age)}s"
    except (ValueError, TypeError):
        return False, "parse_error"
    return False, "alive"


def _rack_slots() -> list[dict[str, Any]]:
    racks_mod = _mod("lib/field-zachub-qemu-racks.py", "qemu_racks")
    if racks_mod and hasattr(racks_mod, "build_slots"):
        try:
            slots = list(racks_mod.build_slots() or [])
            for slot in slots:
                slot["geography"] = _geography_for_slot(slot)
            return slots
        except (OSError, TypeError, ValueError):
            pass
    slots: list[dict[str, Any]] = []
    if RACKS_ROOT.is_dir():
        for manifest in sorted(RACKS_ROOT.glob("qemu-rack-*/manifest.json")):
            doc = _load(manifest, {})
            if doc:
                slot = {
                    "field_id": doc.get("field_id") or manifest.parent.name,
                    "storage_root": str(manifest.parent),
                    "primary_role": doc.get("primary_role"),
                    "roles": doc.get("roles") or doc.get("services"),
                    "slot": doc.get("slot"),
                    "tunnel": doc.get("tunnel"),
                }
                slot["geography"] = _geography_for_slot(slot)
                slots.append(slot)
    return slots


def _sync_truth_to_rack(rack_root: Path, *, geography: dict[str, Any] | None = None) -> dict[str, Any]:
    geo = geography or {}
    synced: list[str] = []
    for src_name, dst_name in (
        ("field-never-down-panel.json", "dns/field-never-down.json"),
        ("hostess7-x-producer-panel.json", "witness/x-producer.json"),
        ("field-botnet-dns-dhcp-panel.json", "dns/botnet-dns-dhcp.json"),
        ("field-one-rollout-panel.json", "witness/field-one-rollout.json"),
    ):
        src = STATE / src_name
        if not src.is_file():
            continue
        dst = rack_root / dst_name
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            synced.append(dst_name)
        except OSError:
            pass
    deploy = {
        "schema": "field-rack-deploy/v1",
        "updated": _utc(),
        "authority": "geographic_primary",
        "all_primary": True,
        "geography_only": True,
        "region_id": geo.get("region_id"),
        "metro_id": geo.get("metro_id"),
        "instantiate": [
            "lib/field-dns.py serve",
            "lib/field-dhcp.py serve",
            "lib/field-botnet-dns-dhcp.py keepalive",
            "lib/field-attack-kit.py auto-rekill",
        ],
        "field_one": True,
        "dns": ["127.0.0.1", "192.168.47.1"],
        "dhcp": ["192.168.47.1"],
    }
    try:
        deploy_path = rack_root / "nexus-field" / "deploy.json"
        deploy_path.parent.mkdir(parents=True, exist_ok=True)
        _save(deploy_path, deploy)
        synced.append("nexus-field/deploy.json")
        authority = {
            "schema": "field-rack-authority/v1",
            "updated": _utc(),
            "authority": "geographic_primary",
            "all_primary": True,
            "geography_only": True,
            "region_id": geo.get("region_id"),
            "metro_id": geo.get("metro_id"),
            "dns_serve": True,
            "dhcp_serve": True,
            "kill_rekill": True,
        }
        _save(rack_root / "authority.json", authority)
        synced.append("authority.json")
    except OSError:
        pass
    return {"ok": bool(synced), "synced": synced, "rack": str(rack_root), "geography": geo}


def sync_mesh(*, write: bool = True) -> dict[str, Any]:
    """All racks + host are primary — provision, sync truth, geographic routing only."""
    provision = _run_py("lib/field-zachub-qemu-racks.py", ["provision"], timeout=180)
    slots = _rack_slots()
    synced: list[dict[str, Any]] = []
    for slot in slots:
        root = Path(str(slot.get("storage_root") or ""))
        if root.is_dir():
            synced.append(_sync_truth_to_rack(root, geography=slot.get("geography") or {}))
    out = {
        "ok": True,
        "schema": "field-rack-mesh-sync/v1",
        "updated": _utc(),
        "rack_count": len(slots),
        "provision": {"ok": provision.get("ok"), "slots": len(provision.get("slots") or [])},
        "synced_racks": synced,
        "authority": "all_primary",
        "geography_only": True,
        "mesh_ready": len(synced) > 0 or len(slots) > 0,
    }
    if write:
        panel = _load(PANEL, {})
        panel.update({**out, "schema": "field-rack-failover-panel/v1"})
        _save(PANEL, panel)
    return out


def standby(*, write: bool = True) -> dict[str, Any]:
    """Backward-compatible alias — all nodes are primary, not standby."""
    return sync_mesh(write=write)


def geographic_absorb(*, write: bool = True) -> dict[str, Any]:
    """Host down — geographic peers absorb load; authority stays all_primary."""
    slots = _rack_slots()
    absorbed: list[dict[str, Any]] = []
    for slot in slots:
        root = Path(str(slot.get("storage_root") or ""))
        if not root.is_dir():
            continue
        geo = slot.get("geography") or _geography_for_slot(slot)
        sync = _sync_truth_to_rack(root, geography=geo)
        load_doc = {
            "schema": "field-rack-geographic-absorb/v1",
            "updated": _utc(),
            "authority": "all_primary",
            "geography_only": True,
            "field_id": slot.get("field_id"),
            "region_id": geo.get("region_id"),
            "host_down": True,
            "absorbing_load": True,
            "dns_serve": True,
            "dhcp_serve": True,
            "kill_rekill": True,
        }
        try:
            _save(root / "geographic-absorb.json", load_doc)
            absorbed.append({"field_id": slot.get("field_id"), "ok": True, "region_id": geo.get("region_id"), **sync})
        except OSError as exc:
            absorbed.append({"field_id": slot.get("field_id"), "ok": False, "error": str(exc)[:120]})

    botnet = _run_py("lib/field-botnet-dns-dhcp.py", ["keepalive"], timeout=90)
    rekill = _run_py("lib/field-attack-kit.py", ["qemu-bot-rekill"], timeout=90)
    rollout = _run_py(
        "lib/field-one-rollout.py",
        ["slow-rollout", str(_policy().get("slow_rollout_batch") or 25)],
        timeout=300,
    )

    out = {
        "ok": bool(absorbed),
        "schema": "field-rack-geographic-absorb/v1",
        "updated": _utc(),
        "motto": doctrine().get("motto"),
        "authority": "all_primary",
        "geography_only": True,
        "host_down": True,
        "rack_count": len(slots),
        "absorbed": absorbed,
        "botnet": {"ok": botnet.get("ok"), "nodes": (botnet.get("bot_network") or {}).get("node_count")},
        "rekill": {"ok": rekill.get("ok"), "count": rekill.get("rekilled_count")},
        "slow_rollout": {"ok": rollout.get("ok"), "deployed": rollout.get("deployed_this_wave")},
        "github_control_plane": "https://zacharygeurts.github.io/Hostess7/api/field-rack-failover.json",
    }
    if write:
        _save(PANEL, {**out, "schema": "field-rack-failover-panel/v1", "last_absorb": _utc()})
        _append_ledger({"event": "geographic_absorb", "racks": len(absorbed)})
        api = H7_API / "field-rack-failover.json"
        api.parent.mkdir(parents=True, exist_ok=True)
        api.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def promote_racks(*, write: bool = True) -> dict[str, Any]:
    """Backward-compatible alias — geographic absorb, not authority promotion."""
    return geographic_absorb(write=write)


def _perimeter_yard() -> dict[str, Any]:
    perimeter = _run_py("lib/field-perimeter-shield.py", ["board"], timeout=45)
    friendly = _run_py("lib/friendly-guard.py", ["verify"], timeout=30) if (INSTALL / "lib/friendly-guard.py").is_file() else {"skipped": True}
    yard = _run_py("lib/home-protector.py", ["json"], timeout=30) if (INSTALL / "lib/home-protector.py").is_file() else {"skipped": True}
    return {"perimeter": perimeter, "friendly": friendly, "yard": yard}


def _verify_world_internet() -> dict[str, Any]:
    rollout_mod = _mod("lib/field-one-rollout.py", "rollout_verify")
    if rollout_mod and hasattr(rollout_mod, "_verify_world_internet"):
        return rollout_mod._verify_world_internet(fast=True)
    internet = _run_py("lib/field-internet-unified.py", ["keepalive"], timeout=20)
    botnet = _run_py("lib/field-botnet-dns-dhcp.py", ["keepalive"], timeout=15)
    return {
        "ok": bool(internet.get("ok") or botnet.get("ok")),
        "internet": internet.get("ok"),
        "botnet": botnet.get("ok"),
    }


def cycle(*, write: bool = True) -> dict[str, Any]:
    """Vigil tick — all primaries serve; host down triggers geographic load absorb only."""
    hb = heartbeat(write=write)
    down, reason = _host_is_down()
    doc = doctrine()
    steps: list[dict[str, Any]] = []
    world = _verify_world_internet()

    for lane in doc.get("vigil_cycle") or []:
        if not isinstance(lane, dict):
            continue
        lid = str(lane.get("id") or "")
        if lid in ("heartbeat", "mesh_cycle", "failover_check"):
            continue
        mod = str(lane.get("module") or "")
        cmd = str(lane.get("cmd") or "json")
        if lid == "never_down_ensure":
            row = _run_py(mod, [cmd], timeout=90)
        elif lid in ("auto_rekill", "qemu_bot_rekill"):
            row = _run_py(mod, [cmd], timeout=120)
        else:
            row = _run_py(mod, [cmd], timeout=90)
        steps.append({"lane": lid, **row})

    mesh_row = sync_mesh(write=False)
    out: dict[str, Any] = {
        "ok": True,
        "schema": "field-rack-failover-cycle/v1",
        "updated": _utc(),
        "authority": "all_primary",
        "geography_only": True,
        "host_down": down,
        "down_reason": reason,
        "heartbeat": hb,
        "mesh": mesh_row,
        "world_internet": world,
        "steps": steps,
    }

    if down:
        absorb = geographic_absorb(write=write)
        out["absorb"] = absorb
        out["motto"] = "Host down — geographic peers absorb load; all nodes stay primary"
        _append_ledger({"event": "host_down_geographic_absorb", "reason": reason, "racks": absorb.get("rack_count")})
    else:
        out["motto"] = "All primary — geography routes clients"

    if write:
        _save(PANEL, {**out, "schema": "field-rack-failover-panel/v1"})
        api = H7_API / "field-rack-failover.json"
        api.parent.mkdir(parents=True, exist_ok=True)
        api.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def boot(*, write: bool = True) -> dict[str, Any]:
    """Full boot — DNS/DHCP, perimeter, geographic mesh, slow-rollout 25, botnet, kill/rekill."""
    doc = doctrine()
    steps: list[dict[str, Any]] = []
    for lane in doc.get("boot_sequence") or []:
        if not isinstance(lane, dict):
            continue
        lid = str(lane.get("id") or "")
        mod = str(lane.get("module") or "")
        cmd = str(lane.get("cmd") or "json")
        optional = bool(lane.get("optional"))
        if lid in ("mesh_sync", "rack_standby"):
            row = sync_mesh(write=write)
        elif lid == "perimeter":
            row = _perimeter_yard()
        elif lid == "slow_rollout":
            batch = str(_policy().get("slow_rollout_batch") or 25)
            row = _run_py(mod, ["slow-rollout", batch], timeout=300)
        else:
            row = _run_py(mod, [cmd], timeout=180 if lid == "never_down" else 120)
        steps.append({"lane": lid, "optional": optional, **(row if isinstance(row, dict) else {"ok": False})})

    hb = heartbeat(write=write)
    world = _verify_world_internet()
    if not world.get("ok"):
        for _ in range(2):
            time.sleep(2)
            world = _verify_world_internet()
            if world.get("ok"):
                break
    mesh_ready = any(
        s.get("lane") in ("mesh_sync", "rack_standby") and s.get("mesh_ready")
        for s in steps
    )
    core_up = any(s.get("lane") == "never_down" and s.get("ok") for s in steps) or any(
        s.get("lane") == "fix_dns_dhcp" and s.get("ok") for s in steps
    )
    out = {
        "ok": bool(core_up or mesh_ready),
        "schema": "field-rack-failover-boot/v1",
        "updated": _utc(),
        "motto": doc.get("motto"),
        "heartbeat": hb,
        "authority": "all_primary",
        "geography_only": True,
        "world_internet": world,
        "world_internet_ok": bool(world.get("ok")),
        "steps": steps,
        "mesh_ready": mesh_ready,
        "core_services_up": core_up,
    }
    if write:
        _save(PANEL, {**out, "schema": "field-rack-failover-panel/v1"})
        api = H7_API / "field-rack-failover.json"
        api.parent.mkdir(parents=True, exist_ok=True)
        api.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _append_ledger({"event": "boot", "ok": out.get("ok")})
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "panel"):
        cached = _load(PANEL) or cycle(write=False)
        print(json.dumps(cached, ensure_ascii=False, indent=2))
        return 0
    if cmd == "boot":
        print(json.dumps(boot(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "heartbeat":
        print(json.dumps(heartbeat(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("sync-mesh", "sync_mesh", "mesh"):
        print(json.dumps(sync_mesh(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "standby":
        print(json.dumps(standby(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("absorb", "geographic-absorb", "geographic_absorb"):
        print(json.dumps(geographic_absorb(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("promote", "failover"):
        print(json.dumps(promote_racks(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "cycle":
        print(json.dumps(cycle(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-rack-failover.py [boot|cycle|heartbeat|sync-mesh|standby|absorb|promote|json]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())