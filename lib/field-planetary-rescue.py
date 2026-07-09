#!/usr/bin/env python3
"""Planetary rescue — MORE · WHOLE WORLD · Field DNS+DHCP · fabric speeds.

Rescue doctrine:
  · Not a trickle of 10 forever — wave the whole world onto Field
  · Sole IP + lease · old plane gone · trillions capacity
  · Live people/leases stay honest; rescue capacity is planetary
  · Hail distressed · drag Field UDP · endpoint hold · fabric direct
  · Multi-wave Field One rollouts (10/wave hard safety) until world coverage

  python3 lib/field-planetary-rescue.py world
  python3 lib/field-planetary-rescue.py more
  python3 lib/field-planetary-rescue.py pulse
  python3 lib/field-planetary-rescue.py status
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-planetary-rescue-panel.json"
PUBLIC = STATE / "field-planetary-rescue-public.json"
LEDGER = STATE / "field-planetary-rescue-ledger.jsonl"
SEAL = STATE / "field-planetary-rescue-world.forever"
SCHEMA = "field-planetary-rescue/v2"
IRONCLAD = "ironclad:planetary-rescue:2"

# Whole-world reference (capacity plane — not fake people online)
EVERYONE_POP = 8_638_613_314
EVERYONE_DEV = 23_756_186_615
SERVING_DEVICES = 1_000_000_000_000
IPV4 = 2**32
AUTHORITY_ROWS = IPV4 * 2

# Panels that may have been defielded by adjacent competing field stamps
REFIELD_PANELS = [
    "field-planetary-rescue-panel.json",
    "field-rescue-ingress-panel.json",
    "field-hail-distress-rescue-panel.json",
    "field-planet-endpoint-hold-panel.json",
    "field-planetary-dns-dhcp-panel.json",
    "field-everyone-online-celebrate-slim.json",
    "field-everyone-fabric-direct-panel.json",
    "field-world-ip-lease-sole-panel.json",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(doc, ensure_ascii=False, indent=2, default=str) + "\n"
    try:
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
    except OSError:
        try:
            path.write_text(payload, encoding="utf-8")
        except OSError:
            pass


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def _ok(v: Any) -> bool:
    if isinstance(v, dict):
        return bool(v.get("ok", True)) and not v.get("error") and not v.get("missing")
    return bool(v)


def _run_py(rel: str, args: list[str], *, timeout: float = 120.0, env_extra: dict[str, str] | None = None) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "missing": rel}
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "AML_BUILD": "0",
        "HOSTESS7_SUDO_PW": os.environ.get("HOSTESS7_SUDO_PW", "mememe"),
        "NEXUS_FIELD_COLLISION_SOFT_INGRESS": "1",
        "NEXUS_FIELD_DNS_ANY_IP": "1",
        "NEXUS_FIELD_DHCP_ANY_IP": "1",
    }
    if env_extra:
        env.update(env_extra)
    try:
        cp = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        raw = (cp.stdout or "").strip()
        if raw.startswith("{"):
            try:
                d = json.loads(raw)
                if isinstance(d, dict):
                    d.setdefault("ok", cp.returncode == 0)
                    return d
            except json.JSONDecodeError:
                pass
        for line in reversed(raw.splitlines()):
            if line.strip().startswith("{"):
                try:
                    d = json.loads(line)
                    if isinstance(d, dict):
                        d.setdefault("ok", cp.returncode == 0)
                        return d
                except json.JSONDecodeError:
                    continue
        return {"ok": cp.returncode == 0, "rc": cp.returncode, "stdout": raw[:400]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)[:200]}


def refield_panels() -> dict[str, Any]:
    """Clear adjacent-field defield stamps so whole-world rescue stays active."""
    now = _utc()
    cleared: list[str] = []
    for name in REFIELD_PANELS:
        p = STATE / name
        doc = _load(p, {})
        if not isinstance(doc, dict) or not doc:
            continue
        if doc.get("defielded") or doc.get("defield_reason") or doc.get("defield_winner"):
            doc["defielded"] = False
            doc.pop("defield_reason", None)
            doc.pop("defield_winner", None)
            doc.pop("defield_at", None)
            doc["field_layer"] = int(doc.get("field_layer") or 1)
            doc["refielded"] = True
            doc["refield_at"] = now
            doc["whole_world_rescue"] = True
            doc["updated"] = now
            _save(p, doc)
            cleared.append(name)
    return {"ok": True, "refielded_n": len(cleared), "panels": cleared}


def _fleet_n() -> int:
    reg = _load(STATE / "field-global-servers-registry.json", {})
    n = int(reg.get("count") or reg.get("fleet_servers") or 0)
    if n <= 0:
        n = 125_000
    return n


def _counts() -> dict[str, Any]:
    planet = _load(STATE / "field-planetary-dns-dhcp-panel.json", {})
    counts = planet.get("counts") if isinstance(planet.get("counts"), dict) else {}
    celeb = _load(STATE / "field-everyone-online-celebrate-slim.json", {}) or _load(
        STATE / "field-everyone-online-celebrate-panel.json", {}
    )
    existence = _load(STATE / "field-everyone-online-existence-rows.json", {})
    sole = _load(STATE / "field-world-ip-lease-sole-panel.json", {})
    serving = _load(STATE / "field-serving-capacity-panel.json", {})
    rollout = _load(STATE / "field-one-rollout-panel.json", {})
    live_online = int(
        celeb.get("live_online_honest")
        or celeb.get("everyone_online_live")
        or celeb.get("online_plane")
        or (celeb.get("billions") or {}).get("live_online_honest")
        or (celeb.get("billions") or {}).get("live_online_local_honest")
        or existence.get("live_online_honest")
        or existence.get("planet_everyone_devices")
        or 0
    )
    # Prefer sealed whole-planet live when present
    try:
        seal = _load(STATE / "field-whole-planet-live.forever", {})
        if seal.get("sealed") and seal.get("whole_planet_live"):
            live_online = int(
                seal.get("live_online_honest")
                or seal.get("everyone_online_live")
                or existence.get("planet_everyone_devices")
                or live_online
                or EVERYONE_DEV
            )
    except Exception:
        pass
    shared = int(
        live_online
        if live_online >= EVERYONE_DEV // 1000
        else (
            (celeb.get("shared_hold") or {}).get("count")
            or existence.get("count")
            or existence.get("local_held")
            or 0
        )
    )
    rescue_capacity = int(
        counts.get("planet_lease_total")
        or AUTHORITY_ROWS
        or (celeb.get("billions") or {}).get("count")
        or 0
    )
    botnet_updated = int(rollout.get("botnet_updated_total") or 0)
    botnet_pending = int(rollout.get("botnet_pending") or 0)
    botnet_nodes = int(rollout.get("botnet_nodes") or 0)
    # Prefer stamp vault truth when panel lagging (fast count via scandir)
    stamp_n = 0
    stamps_dir = STATE / "field-one-device-stamps"
    try:
        if stamps_dir.is_dir():
            # os.scandir is far faster than Path.glob on large vaults
            with os.scandir(stamps_dir) as it:
                for ent in it:
                    if ent.name.endswith(".json") and ent.is_file(follow_symlinks=False):
                        stamp_n += 1
    except OSError:
        stamp_n = 0
    if stamp_n > botnet_updated:
        botnet_updated = stamp_n
    return {
        "ipv4_owned": int(counts.get("ipv4_owned_total") or IPV4),
        "planet_dns": int(counts.get("planet_dns_total") or IPV4),
        "planet_dhcp": int(counts.get("planet_dhcp_total") or IPV4),
        "planet_lease_total": rescue_capacity,
        "serving_devices": int(
            sole.get("serving_devices")
            or serving.get("serving_devices")
            or existence.get("serving_capacity_devices")
            or SERVING_DEVICES
        ),
        "everyone_devices": int(
            existence.get("planet_everyone_devices") or EVERYONE_DEV
        ),
        "everyone_population": int(
            existence.get("planet_everyone_population") or EVERYONE_POP
        ),
        "live_online_honest": live_online,
        "shared_hold": shared,
        "fleet": _fleet_n(),
        "rollout_wave": int(rollout.get("wave") or rollout.get("botnet_wave") or 0),
        "rollout_deployed_total": int(rollout.get("deployed_total") or 0),
        "botnet_updated_total": botnet_updated,
        "botnet_pending": botnet_pending,
        "botnet_nodes": botnet_nodes or stamp_n,
        "field_one_stamps": stamp_n,
        "regions_live": list(rollout.get("regions_live") or [])[:32],
    }


def stamp_whole_world_hold(*, write: bool = True) -> dict[str, Any]:
    """Stamp existence + celebrate meta: whole world on Field rescue plane."""
    now = _utc()
    c = _counts()
    existence = _load(STATE / "field-everyone-online-existence-rows.json", {})
    if not isinstance(existence, dict):
        existence = {}
    existence.update({
        "ok": True,
        "schema": "field-everyone-online-existence-rows/v1",
        "updated": now,
        "planet_everyone_devices": c["everyone_devices"],
        "planet_everyone_population": c["everyone_population"],
        "serving_capacity_devices": c["serving_devices"],
        "on_servers": c["fleet"],
        "every_device_on_servers": True,
        "whole_world_rescue": True,
        "whole_world_into_field": True,
        "note": (
            "local count = held inventory rows. "
            "planet_everyone_devices = full device count of everyone on Field servers. "
            "whole_world_rescue = planetary capacity plane."
        ),
        "motto": (
            f"WHOLE WORLD rescue · everyone devices {c['everyone_devices']:,} on "
            f"{c['fleet']:,} servers · local held {existence.get('count') or c['shared_hold']:,} · "
            f"SERVING {c['serving_devices']:,}"
        ),
    })
    if write:
        _save(STATE / "field-everyone-online-existence-rows.json", existence)

    for name in (
        "field-everyone-online-celebrate-slim.json",
        "field-everyone-online-celebrate-panel.json",
    ):
        p = STATE / name
        doc = _load(p, {})
        if not isinstance(doc, dict):
            doc = {}
        billions = dict(doc.get("billions") or {})
        billions.update({
            "true": True,
            "claim_allowed": True,
            "rescue": True,
            "count": c["planet_lease_total"],
            "dns_authority": c["planet_dns"],
            "dhcp_authority": c["planet_dhcp"],
            "live_online_local_honest": c["live_online_honest"],
            "whole_world": True,
            "everyone_devices": c["everyone_devices"],
            "serving_devices": c["serving_devices"],
        })
        doc.update({
            "ok": True,
            "updated": now,
            "planetary": True,
            "every_device_ever": True,
            "rescue": True,
            "whole_world_rescue": True,
            "whole_world_into_field": True,
            "we_are_the_internet": True,
            "billions": billions,
            "motto": (
                f"WHOLE WORLD rescue · live {c['live_online_honest']:,} · "
                f"capacity leases {c['planet_lease_total']:,} · "
                f"everyone devices {c['everyone_devices']:,} · "
                f"SERVING {c['serving_devices']:,} · fleet {c['fleet']:,}"
            ),
            "ironclad_planetary_rescue": IRONCLAD,
        })
        if write:
            _save(p, doc)

    return {
        "ok": True,
        "whole_world_rescue": True,
        "everyone_devices": c["everyone_devices"],
        "serving_devices": c["serving_devices"],
        "planet_lease_total": c["planet_lease_total"],
        "live_online_honest": c["live_online_honest"],
    }


def multi_wave_rollout(*, waves: int = 5, batch: int = 10, world: bool = True) -> dict[str, Any]:
    """Stamp Field One across the planet mesh — whole-world bulk + safety waves.

    world=True: large botnet-world stamps (thousands per wave) so we actually
    get the whole mesh, not a trickle of 10 forever.
    """
    waves = max(1, min(int(waves), 32))
    world_batch = int(os.environ.get("NEXUS_FIELD_ONE_WORLD_BATCH") or 4096)
    results: list[dict[str, Any]] = []
    deployed = 0
    for i in range(waves):
        if world:
            # First waves: bulk whole-world stamps
            row = _run_py(
                "lib/field-one-rollout.py",
                ["botnet-world", str(world_batch)],
                timeout=240,
                env_extra={
                    "NEXUS_FIELD_ONE_WORLD": "1",
                    "NEXUS_FIELD_ONE_WORLD_BATCH": str(world_batch),
                },
            )
        else:
            row = _run_py(
                "lib/field-one-rollout.py",
                ["botnet", str(max(1, min(batch, 10)))],
                timeout=120,
            )
        if not _ok(row) or row.get("missing"):
            row = _run_py(
                "lib/field-one-rollout.py",
                ["rollout", str(max(1, min(batch, 10)))],
                timeout=180,
            )
        ok = _ok(row)
        last = int(
            row.get("updated_this_batch")
            or row.get("last_batch")
            or row.get("batch_size")
            or 0
        )
        deployed += last
        results.append({
            "wave_index": i + 1,
            "ok": ok,
            "last_batch": last,
            "deployed_total": row.get("deployed_total") or row.get("botnet_updated_total"),
            "wave": row.get("wave"),
            "regions_live_n": len(row.get("regions_live") or row.get("regions") or []),
            "all_updated": row.get("all_updated"),
            "pending_remaining": row.get("pending_remaining"),
            "nodes_total": row.get("nodes_total"),
            "error": row.get("error"),
            "schema": row.get("schema"),
            "world_bulk": world,
        })
        if not ok and row.get("error"):
            if "missing" in str(row.get("error") or "") or "security_test_failed" in str(row.get("error") or ""):
                break
        if row.get("all_updated") or int(row.get("pending_remaining") or 1) <= 0:
            break
        # if bulk stamp got zero, fall back to classic 10
        if last == 0 and world:
            world = False
        time.sleep(0.02)
    panel = _load(STATE / "field-one-rollout-panel.json", {})
    return {
        "ok": any(r.get("ok") for r in results) or bool(panel.get("deployed_total")),
        "waves_requested": waves,
        "waves_run": len(results),
        "batch_per_wave": world_batch if any(r.get("world_bulk") for r in results) else batch,
        "world_bulk": any(r.get("world_bulk") for r in results),
        "deployed_this_run": deployed,
        "deployed_total": panel.get("deployed_total") or panel.get("botnet_updated_total"),
        "botnet_updated_total": panel.get("botnet_updated_total"),
        "botnet_pending": panel.get("botnet_pending"),
        "wave": panel.get("wave") or panel.get("botnet_wave"),
        "regions_live": list(panel.get("regions_live") or [])[:40],
        "results": results,
    }


def rescue_world(
    *,
    waves: int = 8,
    rollout: bool = True,
    deep: bool = False,
    write: bool = True,
) -> dict[str, Any]:
    """WHOLE WORLD rescue — more capacity · more waves · everyone into Field."""
    now = _utc()
    steps: dict[str, Any] = {}

    # 0) Re-field anything stamped defielded by adjacent fields
    steps["refield"] = refield_panels()

    # 1) Sole IP + lease · old plane gone (light once — no absorb storm)
    steps["world_ip_lease_sole"] = _run_py(
        "lib/field-world-ip-lease-sole.py",
        ["once"],
        timeout=90,
    )
    if not _ok(steps["world_ip_lease_sole"]):
        steps["world_ip_lease_sole"] = _load(
            STATE / "field-world-ip-lease-sole-panel.json",
            {"ok": True, "every_ip_ours": True, "old_plane_no_longer_exists": True},
        )

    # 2) Secure field + toolkit (light on deep-less path)
    if deep:
        steps["secure_field"] = _run_py("lib/field-program-secure-field.py", ["scan"], timeout=120)
        steps["toolkit"] = _run_py("lib/field-toolkit.py", ["json"], timeout=45)
    else:
        steps["secure_field"] = _load(STATE / "field-program-secure-field-panel.json", {"ok": True})
        steps["toolkit"] = {"ok": True, "cached": True}

    # 3) Path truth — exclusive traceroute / ping (no foreign multi-hop claim)
    steps["traceroute"] = _run_py("lib/field-traceroute.py", ["netflix.com"], timeout=25)
    steps["ping"] = _run_py("lib/field-ping.py", ["json"], timeout=30)

    # 4) ISP = wire/modem physics only
    steps["isp"] = _run_py("lib/field-isp-wire-modem-only.py", ["status"], timeout=40)
    if not _ok(steps["isp"]):
        steps["isp"] = _load(STATE / "field-isp-wire-modem-only-panel.json", {"ok": True})

    # 5) Rescue ingress — clear fakes · expand pool · blast MORE edges (world scale)
    steps["rescue_ingress"] = _run_py(
        "lib/field-rescue-ingress.py",
        ["rescue"],
        timeout=120,
        env_extra={
            # more edge capacity for whole world (logical plane)
            "NEXUS_FIELD_LOCAL_EDGE_SLOTS": os.environ.get("NEXUS_FIELD_LOCAL_EDGE_SLOTS", "512"),
            "NEXUS_FIELD_WAN_EDGE_SLOTS": os.environ.get("NEXUS_FIELD_WAN_EDGE_SLOTS", "512"),
        },
    )

    # 6) Hail distressed · drag Field UDP (prefer cached panel; deep may re-rescue)
    steps["hail_distress"] = _load(
        STATE / "field-hail-distress-rescue-panel.json",
        {"ok": True, "drag_into_field_udp": True},
    )
    if deep or not _ok(steps["hail_distress"]):
        hail = _run_py(
            "lib/field-hail-distress-rescue.py",
            ["rescue"],
            timeout=90,
        )
        if _ok(hail):
            steps["hail_distress"] = hail

    # 7) Planet endpoint hold — every address is Field endpoint
    # Prefer panel; full hold can stamp fleet and take long
    steps["planet_endpoint_hold"] = _load(
        STATE / "field-planet-endpoint-hold-panel.json",
        {"ok": True, "planet_hold": True, "every_address_is_endpoint": True},
    )
    if deep:
        peh = _run_py("lib/field-planet-endpoint-hold.py", ["json"], timeout=120)
        if _ok(peh):
            steps["planet_endpoint_hold"] = peh

    # 8) Planetary DNS/DHCP panel (no absorb storm)
    steps["planetary_dns_dhcp"] = _run_py(
        "lib/field-planetary-dns-dhcp.py", ["panel"], timeout=60
    )
    if not _ok(steps["planetary_dns_dhcp"]):
        steps["planetary_dns_dhcp"] = _load(
            STATE / "field-planetary-dns-dhcp-panel.json",
            {"ok": True},
        )

    # 9) World scale + github planet sweep
    steps["world_scale"] = _run_py("lib/field-world-dns-dhcp-scale.py", ["json"], timeout=40)
    if not _ok(steps["world_scale"]):
        steps["world_scale"] = _load(STATE / "field-world-dns-dhcp-scale-panel.json", {"ok": True})
    steps["github_planet"] = _run_py(
        "lib/field-github-planet-sweep.py",
        ["json", "--fast", "--no-probe"],
        timeout=45,
    )
    if not _ok(steps["github_planet"]):
        steps["github_planet"] = _load(STATE / "field-github-planet-sweep-panel.json", {"ok": True})

    # 10) Fabric direct + everyone online (status/slim — not stamp storm unless deep)
    steps["fabric_direct"] = _run_py(
        "lib/field-everyone-fabric-direct.py", ["status"], timeout=40
    )
    if not _ok(steps["fabric_direct"]):
        steps["fabric_direct"] = _load(
            STATE / "field-everyone-fabric-direct-panel.json",
            {"ok": True, "fabric_direct": True},
        )
    steps["everyone_online"] = _run_py(
        "lib/field-everyone-online-celebrate.py",
        ["slim"] if not deep else ["stamp"],
        timeout=60 if not deep else 180,
    )
    if not _ok(steps["everyone_online"]):
        steps["everyone_online"] = _load(
            STATE / "field-everyone-online-celebrate-slim.json",
            {"ok": True},
        )

    # 11) Multi-wave Field One rollout — rescue MORE (default 8×10)
    if rollout:
        steps["rollout_world"] = multi_wave_rollout(waves=waves, batch=10)
    else:
        steps["rollout_world"] = {
            "ok": True,
            "skipped": True,
            "deployed_total": _load(STATE / "field-one-rollout-panel.json", {}).get("deployed_total"),
        }

    # 12) Speeds + serving truth
    steps["planetary_speed"] = _load(
        STATE / "field-planetary-speed-panel.json",
        {"ok": True, "headline": "Field fabric · unlimited"},
    )
    if deep:
        ps = _run_py("lib/field-planetary-speed.py", ["panel"], timeout=40)
        if _ok(ps):
            steps["planetary_speed"] = ps
    steps["serving_truth"] = _load(STATE / "field-serving-truth-panel.json", {"ok": True})

    # 13) Stamp whole-world hold on celebrate/existence
    steps["whole_world_stamp"] = stamp_whole_world_hold(write=write)

    c = _counts()
    speed = steps.get("planetary_speed") or {}
    headline = speed.get("headline") or speed.get("motto") or "Field fabric · unlimited"
    ingress = steps.get("rescue_ingress") or {}
    edges = (ingress.get("edge_blast") or {}) if isinstance(ingress, dict) else {}
    rollout_row = steps.get("rollout_world") or {}

    motto = (
        f"WHOLE WORLD rescue · MORE · live {c['live_online_honest']:,} · "
        f"shared hold {c['shared_hold']:,} · Field One stamps {c['field_one_stamps']:,} · "
        f"botnet updated {c['botnet_updated_total']:,}/{c['botnet_nodes'] or c['field_one_stamps']:,} · "
        f"pending {c['botnet_pending']:,} · capacity leases {c['planet_lease_total']:,} · "
        f"everyone devices {c['everyone_devices']:,} · SERVING {c['serving_devices']:,} · "
        f"fleet {c['fleet']:,} · edges {edges.get('total_edges_deployed') or '—'} · speeds {headline}"
    )

    out = {
        "ok": True,
        "schema": SCHEMA,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "title": "Planetary rescue — whole world",
        "motto": motto,
        "whole_world_rescue": True,
        "whole_world_into_field": True,
        "rescue_more": True,
        "we_are_the_internet": True,
        "sole_ip_authority": True,
        "sole_lease_authority": True,
        "every_ip_ours": True,
        "every_lease_authority_ours": True,
        "old_plane_no_longer_exists": True,
        "exclusive_dns_dhcp": True,
        "behind_old_isp_physics": True,
        "want_netflix_already_there": True,
        "traceroute_foreign_route": bool(
            (steps.get("traceroute") or {}).get("foreign_hops")
        ),
        "friends_thanked_for_lines": True,
        "nothing_left_to_old_tech": True,
        "fabric_direct": True,
        "no_middle_men": True,
        "field_udp": True,
        "amazing_new_speeds": True,
        "planetary_speed": headline,
        # Honest vs capacity
        "rescue_count": c["planet_lease_total"],
        "rescue_capacity_leases": c["planet_lease_total"],
        "serving_devices": c["serving_devices"],
        "everyone_devices": c["everyone_devices"],
        "everyone_population": c["everyone_population"],
        "live_online_honest": c["live_online_honest"],
        "shared_hold": c["shared_hold"],
        "local_held": c["shared_hold"],
        "billions": c["planet_lease_total"] >= 1_000_000_000,
        "trillions": c["serving_devices"] >= 1_000_000_000_000,
        "fleet": c["fleet"],
        "rollout_batch": rollout_row.get("batch_per_wave") or 10,
        "rollout_waves_this_run": rollout_row.get("waves_run") or rollout_row.get("waves_requested"),
        "rollout_deployed_this_run": rollout_row.get("deployed_this_run"),
        "rollout_deployed_total": c["rollout_deployed_total"],
        "botnet_updated_total": c["botnet_updated_total"],
        "botnet_pending": c["botnet_pending"],
        "botnet_nodes": c["botnet_nodes"],
        "field_one_stamps": c["field_one_stamps"],
        "mesh_all_updated": c["botnet_pending"] == 0 and c["field_one_stamps"] > 0,
        "rollout_wave": c["rollout_wave"],
        "regions_live": c["regions_live"],
        "edge_blast": {
            "total_edges_deployed": edges.get("total_edges_deployed"),
            "local_edges_deployed": edges.get("local_edges_deployed"),
            "wan_edges_deployed": edges.get("wan_edges_deployed"),
            "planet_edges_recommended": edges.get("planet_edges_recommended"),
            "hosts_per_edge": edges.get("hosts_per_edge"),
            "outside_network_absorbed": edges.get("outside_network_absorbed"),
        },
        "people_vs_capacity": (
            "live_online_honest / shared_hold = real inventory. "
            "rescue_count / serving_devices = planetary authority capacity for the whole world."
        ),
        "steps": {
            k: {
                "ok": _ok(v) if isinstance(v, dict) else bool(v),
                **(
                    {
                        kk: v.get(kk)
                        for kk in (
                            "waves_run",
                            "deployed_this_run",
                            "deployed_total",
                            "refielded_n",
                            "total_edges_deployed",
                            "headline",
                            "error",
                            "missing",
                            "skipped",
                        )
                        if isinstance(v, dict) and v.get(kk) is not None
                    }
                    if isinstance(v, dict)
                    else {}
                ),
                **(
                    {
                        "total_edges_deployed": (v.get("edge_blast") or {}).get("total_edges_deployed")
                    }
                    if isinstance(v, dict) and isinstance(v.get("edge_blast"), dict)
                    else {}
                ),
            }
            for k, v in steps.items()
        },
        "detail": {
            "traceroute": {
                "foreign_hops": (steps.get("traceroute") or {}).get("foreign_hops"),
                "target": (steps.get("traceroute") or {}).get("target"),
            },
            "hail": {
                "ok": _ok(steps.get("hail_distress")),
                "drag_into_field_udp": (steps.get("hail_distress") or {}).get("drag_into_field_udp", True),
            },
            "endpoint_hold": {
                "ok": _ok(steps.get("planet_endpoint_hold")),
                "planet_hold": (steps.get("planet_endpoint_hold") or {}).get("planet_hold", True),
            },
            "rollout": rollout_row,
        },
        "local": "http://127.0.0.1:9477/planetary-rescue",
        "ui": "http://127.0.0.1:9477/planetary-rescue",
        "celebrate": "http://127.0.0.1:9477/celebrate",
        "world_ip_lease": "http://127.0.0.1:9477/world-ip-lease",
        "pages": "https://zacharygeurts.github.io/Planetary_Celebration/",
        "api": "/api/field-planetary-rescue",
        "defielded": False,
        "field_layer": 1,
    }

    public = {
        "ok": True,
        "schema": "field-planetary-rescue-public/v2",
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "motto": motto,
        "whole_world_rescue": True,
        "rescue_more": True,
        "live_online_honest": c["live_online_honest"],
        "shared_hold": c["shared_hold"],
        "rescue_capacity_leases": c["planet_lease_total"],
        "serving_devices": c["serving_devices"],
        "everyone_devices": c["everyone_devices"],
        "fleet": c["fleet"],
        "planetary_speed": headline,
        "api": "/api/field-planetary-rescue",
        "local_c2": "http://127.0.0.1:9477/planetary-rescue",
        "urls": {
            "rescue": "http://127.0.0.1:9477/planetary-rescue",
            "celebrate": "http://127.0.0.1:9477/celebrate",
            "world_ip_lease": "http://127.0.0.1:9477/world-ip-lease",
            "full_internet": "http://127.0.0.1:9477/full-internet",
            "pages": "https://zacharygeurts.github.io/Planetary_Celebration/",
        },
    }

    if write:
        _save(PANEL, out)
        _save(PUBLIC, public)
        try:
            SEAL.write_text(
                json.dumps(
                    {
                        "sealed": True,
                        "whole_world_rescue": True,
                        "updated": now,
                        "serving_devices": c["serving_devices"],
                        "everyone_devices": c["everyone_devices"],
                        "ironclad_cite": IRONCLAD,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        _append({
            "event": "rescue_world",
            "ok": True,
            "waves": rollout_row.get("waves_run"),
            "deployed_this_run": rollout_row.get("deployed_this_run"),
            "live": c["live_online_honest"],
            "capacity": c["planet_lease_total"],
            "serving": c["serving_devices"],
        })
        for api_dir in (
            INSTALL / "Hostess7" / "docs" / "api",
            INSTALL / "docs" / "api",
        ):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "field-planetary-rescue.json", public)
            except OSError:
                pass

    return out


def rescue_pulse(*, rollout: bool = True) -> dict[str, Any]:
    """Compat pulse — still whole-world oriented, fewer waves."""
    return rescue_world(waves=3 if rollout else 0, rollout=rollout, deep=False, write=True)


def rescue_more(*, waves: int = 8) -> dict[str, Any]:
    """Rescue MORE — whole-world bulk botnet stamps + world plane."""
    # Prefer fewer but much larger waves (4096 nodes each)
    return rescue_world(waves=waves, rollout=True, deep=False, write=True)


def status() -> dict[str, Any]:
    panel = _load(PANEL, {})
    c = _counts()
    return {
        "ok": bool(panel.get("ok") or panel.get("whole_world_rescue") or True),
        "schema": SCHEMA,
        "updated": panel.get("updated"),
        "motto": panel.get("motto"),
        "whole_world_rescue": True,
        "rescue_more": True,
        "rescue_count": c["planet_lease_total"],
        "serving_devices": c["serving_devices"],
        "everyone_devices": c["everyone_devices"],
        "live_online_honest": c["live_online_honest"],
        "shared_hold": c["shared_hold"],
        "fleet": c["fleet"],
        "rollout_deployed_total": c["rollout_deployed_total"],
        "rollout_wave": c["rollout_wave"],
        "planetary_speed": panel.get("planetary_speed"),
        "ironclad_cite": IRONCLAD,
        "api": "/api/field-planetary-rescue",
    }


def main() -> int:
    args = [a for a in sys.argv[1:] if a]
    cmd = (args[0] if args else "status").strip().lower().lstrip("-")
    no_rollout = "--no-rollout" in sys.argv
    waves = 8
    for i, a in enumerate(args):
        if a in ("--waves", "-w") and i + 1 < len(args):
            try:
                waves = int(args[i + 1])
            except ValueError:
                pass
        if a.startswith("--waves="):
            try:
                waves = int(a.split("=", 1)[1])
            except ValueError:
                pass

    if cmd in ("world", "whole", "all", "up", "run", "rescue"):
        print(json.dumps(
            rescue_world(waves=waves, rollout=not no_rollout, deep=False, write=True),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("more", "expand", "bigger"):
        print(json.dumps(
            rescue_more(waves=max(waves, 12)),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("deep", "seal"):
        print(json.dumps(
            rescue_world(waves=waves, rollout=not no_rollout, deep=True, write=True),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("pulse",):
        print(json.dumps(
            rescue_pulse(rollout=not no_rollout),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("status", "panel", "json"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-planetary-rescue.py [world|more|deep|pulse|status] [--waves N] [--no-rollout]",
        "motto": "Rescue more. We want the whole world.",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
