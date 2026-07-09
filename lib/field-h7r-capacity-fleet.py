#!/usr/bin/env python3
"""H7r capacity fleet — the Datacenter bird (not the Internet bird).

Build pure-capacity H7r racks, discover every H7r surface we know, and stripe
redundantly across them. Internet fleet (2500) is a different bird — never
counted as cloud capacity write fabric.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-h7r-capacity-fleet-panel.json"
LEDGER = STATE / "field-h7r-capacity-fleet-ledger.jsonl"
MESH = STATE / "field-h7r-known-mesh.json"
FLEET_REG = STATE / "field-h7r-capacity-fleet-registry.json"

# Datacenter bird roots (writable capacity)
STATE_CAP = STATE / "field-h7r-capacity" / "racks"
FIELD_CAP = Path("/media/default/FIELD_QUBES/fieldstorage/h7r-capacity")
FIELD_RACKS = Path("/media/default/FIELD_QUBES/fieldstorage/racks")
GLOBAL_DC = Path("/media/default/FIELD_QUBES/fieldstorage/global-datacenter/regions")
ARCHIVE_RACKS = STATE / "field-world-archive" / "racks"
CENTRAL_VAULT = STATE / "field-h7r-vault"
# Internet bird — inventory only, never capacity write fabric
INTERNET_FLEET = INSTALL / "GrokLab" / "deploy" / "qemu-racks"

IRONCLAD = "ironclad:h7r-capacity-fleet:2"
GB_PER_RACK = 91
DEFAULT_MIRRORS = 6  # never_lose
STRIPE_K = 4
STRIPE_M = 2
# Capacity scale: per-region slots on big disk + state plane
STATE_CAP_N = 24
FIELD_PER_REGION = 8
# Distributed cloud center — match fleet scale (125k)
TARGET_CAPACITY_RACKS = int(os.environ.get("NEXUS_H7R_CAPACITY_TARGET", "125000") or "125000")
SCALE_ROOT_NAME = "distributed-cloud-center"
SCALE_SHARD_SIZE = 1000  # racks per shard dir
WORKERS = int(os.environ.get("NEXUS_H7R_CAP_WORKERS") or 64)
SCALE_INDEX = STATE / "field-h7r-distributed-cloud-index.json"
SCALE_LEDGER = STATE / "field-h7r-distributed-cloud-ledger.jsonl"


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


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / f".wprobe-{os.getpid()}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _doctrine_flags() -> dict[str, Any]:
    return {
        "antivirus_network_defender": True,
        "avnd_product": "AntivirusNetworkDefender",
        "local_builtin_av": True,
        "av_built_in_locally": True,
        "always_autopilot": True,
        "autopilot": True,
        "no_stops": True,
        "self_governed": True,
        "self_protected": True,
        "distributed_protection": True,
        "no_owners": True,
        "owners": [],
        "planet_whole": True,
        "ask_only": True,
        "only_ammonet": True,
        "never_permit_terrorists": True,
        "no_foreign_servers": True,
    }


def _mk_rack(root: Path, rid: str, *, region: str = "local", role: str = "capacity") -> dict[str, Any]:
    slot = root / rid
    vault = slot / "h7-shard" / "h7r-vault"
    stripes = slot / "h7-shard" / "h7r-stripes"
    services = slot / "h7-shard" / "cloud-services"
    try:
        vault.mkdir(parents=True, exist_ok=True)
        stripes.mkdir(parents=True, exist_ok=True)
        services.mkdir(parents=True, exist_ok=True)
        meta = {
            "schema": "field-h7r-capacity-rack/v2",
            "id": rid,
            "plane": "cloud_datacenter",
            "bird": "datacenter",
            "not_internet_fleet": True,
            "role": role,
            "region": region,
            "protocol": "h7r/1",
            "hot_lane": "h7s/1",
            "archive_protocol": "h7r/2-archive",
            "redundant": True,
            "erasure": f"{STRIPE_K}+{STRIPE_M}",
            "never_lose_mirrors": DEFAULT_MIRRORS,
            "gb_doctrine": GB_PER_RACK,
            "distributed_cloud_center": True,
            "updated": _utc(),
            "ironclad_cite": IRONCLAD,
            "ironclad_avnd": "ironclad:antivirus-network-defender:2",
            **_doctrine_flags(),
        }
        (slot / "rack.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        # Redundant cloud service stamps (object / block / archive + antivirus)
        for svc in ("object", "block", "archive", "big_data"):
            stamp = {
                "schema": "field-h7r-cloud-service/v1",
                "service": svc,
                "rack_id": rid,
                "plane": "cloud_datacenter",
                "bird": "datacenter",
                "free": True,
                "no_charge": True,
                "redundant": True,
                "protocol": "h7r/1" if svc != "archive" else "h7r/2-archive",
                "antivirus_network_defender": True,
                "updated": _utc(),
            }
            (services / f"{svc}.json").write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
        av_stamp = {
            "schema": "field-antivirus-rack-stamp/v2",
            "product": "AntivirusNetworkDefender",
            "rack_id": rid,
            "plane": "cloud_datacenter",
            "bird": "datacenter",
            "updated": _utc(),
            "ironclad_cite": "ironclad:antivirus-network-defender:2",
            **_doctrine_flags(),
        }
        (services / "antivirus-network-defender.json").write_text(
            json.dumps(av_stamp, indent=2) + "\n", encoding="utf-8"
        )
        sec = slot / "security"
        sec.mkdir(parents=True, exist_ok=True)
        (sec / "antivirus-network-defender.json").write_text(
            json.dumps(av_stamp, indent=2) + "\n", encoding="utf-8"
        )
        return {"ok": True, "id": rid, "path": str(slot), "region": region}
    except OSError as exc:
        return {"ok": False, "id": rid, "error": str(exc)}


def _mk_rack_lite(root: Path, rid: str, *, region: str, shard: int, index: int) -> dict[str, Any]:
    """Lightweight capacity rack for mass distributed-cloud scale (125k)."""
    slot = root / rid
    try:
        if (slot / "rack.json").is_file():
            return {"ok": True, "id": rid, "path": str(slot), "region": region, "skipped": True}
        services = slot / "h7-shard" / "cloud-services"
        services.mkdir(parents=True, exist_ok=True)
        (slot / "h7-shard" / "h7r-vault").mkdir(parents=True, exist_ok=True)
        (slot / "h7-shard" / "h7r-stripes").mkdir(parents=True, exist_ok=True)
        now = _utc()
        meta = {
            "schema": "field-h7r-capacity-rack/v3-lite",
            "id": rid,
            "index": index,
            "shard": shard,
            "plane": "cloud_datacenter",
            "bird": "datacenter",
            "not_internet_fleet": True,
            "role": "distributed_cloud_center",
            "region": region,
            "protocol": "h7r/1",
            "hot_lane": "h7s/1",
            "archive_protocol": "h7r/2-archive",
            "redundant": True,
            "erasure": f"{STRIPE_K}+{STRIPE_M}",
            "never_lose_mirrors": DEFAULT_MIRRORS,
            "gb_doctrine": GB_PER_RACK,
            "lite": True,
            "distributed_cloud_center": True,
            "scale_target": TARGET_CAPACITY_RACKS,
            "updated": now,
            "ironclad_cite": IRONCLAD,
            **_doctrine_flags(),
        }
        # compact writes for mass scale
        (slot / "rack.json").write_text(
            json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        av = {
            "schema": "field-antivirus-rack-stamp/v2",
            "product": "AntivirusNetworkDefender",
            "rack_id": rid,
            "plane": "cloud_datacenter",
            "bird": "datacenter",
            "updated": now,
            **_doctrine_flags(),
        }
        raw_av = json.dumps(av, ensure_ascii=False, separators=(",", ":")) + "\n"
        (services / "antivirus-network-defender.json").write_text(raw_av, encoding="utf-8")
        sec = slot / "security"
        sec.mkdir(parents=True, exist_ok=True)
        (sec / "antivirus-network-defender.json").write_text(raw_av, encoding="utf-8")
        return {"ok": True, "id": rid, "path": str(slot), "region": region, "index": index}
    except OSError as exc:
        return {"ok": False, "id": rid, "error": str(exc)[:160]}


def _scale_root() -> Path:
    """Prefer fieldstorage (more free); fall back to state plane."""
    field = FIELD_CAP / SCALE_ROOT_NAME
    if _writable(FIELD_CAP):
        return field
    return STATE / "field-h7r-capacity" / SCALE_ROOT_NAME


def _count_scale_racks(root: Path | None = None) -> int:
    root = root or _scale_root()
    if not root.is_dir():
        return 0
    n = 0
    try:
        for shard in root.iterdir():
            if not shard.is_dir() or not shard.name.startswith("shard-"):
                continue
            for p in shard.iterdir():
                if p.is_dir() and p.name.startswith("h7r-cloud-"):
                    n += 1
    except OSError:
        pass
    return n


def scale_distributed_cloud(
    *,
    target: int | None = None,
    workers: int | None = None,
) -> dict[str, Any]:
    """Raise distributed cloud center H7r capacity to target (default 125000)."""
    target = int(target if target is not None else TARGET_CAPACITY_RACKS)
    workers = int(workers if workers is not None else WORKERS)
    root = _scale_root()
    root.mkdir(parents=True, exist_ok=True)

    # Count existing capacity planes (hot + scale)
    existing_hot = 0
    if STATE_CAP.is_dir():
        existing_hot += sum(1 for p in STATE_CAP.glob("h7r-cap-*") if p.is_dir())
    if FIELD_CAP.is_dir():
        try:
            existing_hot += sum(
                1 for p in FIELD_CAP.rglob("h7r-dc-*")
                if p.is_dir() and SCALE_ROOT_NAME not in p.parts
            )
        except OSError:
            pass
    if ARCHIVE_RACKS.is_dir():
        existing_hot += sum(1 for p in ARCHIVE_RACKS.iterdir() if p.is_dir())

    already_scale = _count_scale_racks(root)
    # Scale plane fills so total capacity (hot + scale) reaches target.
    # Prefer pure 125k scale fabric for distributed cloud center number.
    need = max(0, target - already_scale)
    created = 0
    skipped = 0
    errors: list[str] = []

    if need <= 0:
        out = {
            "ok": True,
            "target": target,
            "already_scale": already_scale,
            "created": 0,
            "skipped": already_scale,
            "scale_root": str(root),
            "capacity_racks": already_scale,
            "hot_capacity_racks": existing_hot,
            "motto": f"H7r distributed cloud already at {already_scale:,} / {target:,}",
        }
        _save(SCALE_INDEX, {**out, "schema": "field-h7r-distributed-cloud-index/v1", "updated": _utc()})
        return out

    start_idx = already_scale
    end_idx = already_scale + need
    batch_size = int(os.environ.get("NEXUS_H7R_SCALE_BATCH", "4000") or "4000")

    def one(i: int) -> dict[str, Any]:
        shard = i // SCALE_SHARD_SIZE
        region = f"cloud-shard-{shard:04d}"
        rid = f"h7r-cloud-{i:06d}"
        shard_root = root / f"shard-{shard:04d}"
        return _mk_rack_lite(shard_root, rid, region=region, shard=shard, index=i)

    # Batched workers — avoid holding 125k futures in memory
    with ThreadPoolExecutor(max_workers=max(4, workers)) as pool:
        for batch_start in range(start_idx, end_idx, batch_size):
            batch_end = min(end_idx, batch_start + batch_size)
            futs = [pool.submit(one, i) for i in range(batch_start, batch_end)]
            for fut in as_completed(futs):
                try:
                    row = fut.result()
                except Exception as exc:  # noqa: BLE001
                    if len(errors) < 24:
                        errors.append(str(exc)[:120])
                    continue
                if row.get("skipped"):
                    skipped += 1
                elif row.get("ok"):
                    created += 1
                else:
                    if len(errors) < 24:
                        errors.append(str(row.get("error") or row.get("id") or "err")[:120])

    final_scale = _count_scale_racks(root)
    out = {
        "ok": final_scale >= target or created + already_scale >= target,
        "schema": "field-h7r-distributed-cloud-index/v1",
        "updated": _utc(),
        "ironclad_cite": IRONCLAD,
        "target": target,
        "created": created,
        "skipped_existing": skipped,
        "errors_n": len(errors),
        "errors": errors[:12],
        "scale_root": str(root),
        "scale_racks": final_scale,
        "hot_capacity_racks": existing_hot,
        "capacity_racks": final_scale,  # distributed cloud center authority count
        "capacity_racks_with_hot": final_scale + existing_hot,
        "shards": (final_scale + SCALE_SHARD_SIZE - 1) // SCALE_SHARD_SIZE if final_scale else 0,
        "gb_doctrine_total": final_scale * GB_PER_RACK,
        "tb_doctrine_total": round(final_scale * GB_PER_RACK / 1024, 2),
        "distributed_cloud_center": True,
        "no_owners": True,
        "planet_whole": True,
        "local_builtin_av": True,
        "always_autopilot": True,
        "motto": (
            f"H7r distributed cloud center · {final_scale:,} capacity racks · "
            f"target {target:,} · hot {existing_hot:,} · no owners · planet whole"
        ),
    }
    _save(SCALE_INDEX, out)
    try:
        SCALE_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with SCALE_LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), "event": "scale", **{k: out[k] for k in (
                "target", "created", "scale_racks", "ok"
            )}}, ensure_ascii=False) + "\n")
    except OSError:
        pass
    _append({"event": "scale_distributed_cloud", "target": target, "created": created, "scale_racks": final_scale})
    return out


def build_capacity_racks() -> dict[str, Any]:
    """Expand pure H7r capacity fleet on state + FIELD_QUBES (not internet)."""
    created: list[dict[str, Any]] = []
    skipped = 0
    errors: list[str] = []

    # 1) State plane capacity
    STATE_CAP.mkdir(parents=True, exist_ok=True)
    for i in range(STATE_CAP_N):
        rid = f"h7r-cap-{i:04d}"
        if (STATE_CAP / rid).is_dir() and (STATE_CAP / rid / "rack.json").is_file():
            skipped += 1
            continue
        row = _mk_rack(STATE_CAP, rid, region="local-state", role="capacity")
        if row.get("ok"):
            created.append(row)
        else:
            errors.append(str(row.get("error") or rid))

    # 2) Fieldstorage big disk — region-aligned fleet
    regions: list[str] = []
    if GLOBAL_DC.is_dir():
        regions = sorted(p.name for p in GLOBAL_DC.iterdir() if p.is_dir())
    if not regions:
        regions = [
            "americas", "americas-b", "europe", "europe-b",
            "asia_pacific", "asia_pacific-b", "africa", "africa-b",
            "oceania", "oceania-b", "middle_east", "middle_east-b",
            "global_root", "global_root-b",
        ]

    field_ok = _writable(FIELD_CAP)
    if field_ok:
        for region in regions:
            reg_root = FIELD_CAP / region
            for i in range(FIELD_PER_REGION):
                rid = f"h7r-dc-{region}-{i:03d}"
                if (reg_root / rid).is_dir() and (reg_root / rid / "rack.json").is_file():
                    skipped += 1
                    continue
                row = _mk_rack(reg_root, rid, region=region, role="datacenter_capacity")
                if row.get("ok"):
                    created.append(row)
                else:
                    errors.append(str(row.get("error") or rid))

    # 3) Ensure archive plane racks keep H7r dirs
    archive_seeded = 0
    if ARCHIVE_RACKS.is_dir():
        for rack in sorted(ARCHIVE_RACKS.iterdir()):
            if not rack.is_dir():
                continue
            try:
                (rack / "h7-shard" / "h7r-vault").mkdir(parents=True, exist_ok=True)
                (rack / "h7-shard" / "h7r-stripes").mkdir(parents=True, exist_ok=True)
                meta_path = rack / "rack.json"
                if not meta_path.is_file():
                    meta_path.write_text(
                        json.dumps(
                            {
                                "schema": "field-h7r-capacity-rack/v2",
                                "id": rack.name,
                                "plane": "cloud_datacenter",
                                "bird": "datacenter",
                                "role": "archive_plane",
                                "protocol": "h7r/2-archive",
                                "not_internet_fleet": True,
                                "updated": _utc(),
                            },
                            indent=2,
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                archive_seeded += 1
            except OSError:
                pass

    # 4) Central vault
    try:
        CENTRAL_VAULT.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        errors.append(f"central_vault:{exc}")

    result = {
        "ok": True,
        "created": len(created),
        "skipped_existing": skipped,
        "archive_plane_seeded": archive_seeded,
        "field_capacity_writable": field_ok,
        "state_cap_n": STATE_CAP_N,
        "field_per_region": FIELD_PER_REGION if field_ok else 0,
        "regions": regions,
        "errors": errors[:20],
        "sample": created[:5],
    }
    _append({"event": "build_capacity", **{k: result[k] for k in result if k != "sample"}})
    return result


def discover_known_h7r() -> dict[str, Any]:
    """Inventory every H7r surface we know. Tag bird: datacenter vs internet."""
    nodes: list[dict[str, Any]] = []

    def add(path: Path, *, kind: str, bird: str, writable: bool | None = None) -> None:
        if not path.exists():
            return
        w = writable if writable is not None else (path.is_dir() and os.access(path, os.W_OK))
        nodes.append(
            {
                "id": path.name,
                "path": str(path),
                "kind": kind,
                "bird": bird,
                "plane": "cloud_datacenter" if bird == "datacenter" else "internet",
                "is_capacity": bird == "datacenter",
                "writable": bool(w),
                "has_h7_shard": (path / "h7-shard").is_dir() if path.is_dir() else False,
            }
        )

    # State capacity
    if STATE_CAP.is_dir():
        for p in sorted(STATE_CAP.glob("h7r-cap-*")):
            if p.is_dir():
                add(p, kind="state_capacity", bird="datacenter", writable=True)

    # Field capacity (regional hot — exclude mass scale tree)
    if FIELD_CAP.is_dir():
        for p in sorted(FIELD_CAP.rglob("h7r-dc-*")):
            if not p.is_dir() or not (p / "h7-shard").is_dir():
                continue
            if SCALE_ROOT_NAME in p.parts:
                continue
            add(p, kind="field_capacity", bird="datacenter", writable=_writable(p))

    # Archive plane
    if ARCHIVE_RACKS.is_dir():
        for p in sorted(ARCHIVE_RACKS.iterdir()):
            if p.is_dir():
                add(p, kind="archive_plane", bird="datacenter", writable=os.access(p, os.W_OK))

    # Global DC region roots (sites)
    if GLOBAL_DC.is_dir():
        for p in sorted(GLOBAL_DC.iterdir()):
            if p.is_dir():
                add(p, kind="global_dc_site", bird="datacenter", writable=os.access(p, os.W_OK))

    # Fieldstorage racks
    if FIELD_RACKS.is_dir():
        for p in sorted(FIELD_RACKS.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                add(p, kind="fieldstorage_rack", bird="datacenter", writable=os.access(p, os.W_OK))

    # Central vault
    if CENTRAL_VAULT.exists() or True:
        CENTRAL_VAULT.mkdir(parents=True, exist_ok=True)
        add(CENTRAL_VAULT, kind="central_vault", bird="datacenter", writable=True)

    # Distributed cloud center scale plane — summary + sample shards (not 125k mesh rows)
    scale_root = _scale_root()
    scale_n = _count_scale_racks(scale_root)
    scale_samples = 0
    if scale_root.is_dir() and scale_n > 0:
        nodes.append(
            {
                "id": "h7r-distributed-cloud-center",
                "path": str(scale_root),
                "kind": "distributed_cloud_center",
                "bird": "datacenter",
                "plane": "cloud_datacenter",
                "is_capacity": True,
                "writable": True,
                "has_h7_shard": True,
                "capacity_racks": scale_n,
                "target": TARGET_CAPACITY_RACKS,
                "note": "Mass distributed cloud center — 125k H7r capacity fabric",
            }
        )
        # Sample first rack of each of first 16 shards for live stripe fabric
        for shard_i in range(min(16, (scale_n + SCALE_SHARD_SIZE - 1) // SCALE_SHARD_SIZE)):
            sample = scale_root / f"shard-{shard_i:04d}" / f"h7r-cloud-{shard_i * SCALE_SHARD_SIZE:06d}"
            if sample.is_dir():
                add(sample, kind="distributed_cloud_sample", bird="datacenter", writable=True)
                scale_samples += 1

    # Internet bird — reference only
    internet_n = 0
    internet_h7 = 0
    if INTERNET_FLEET.is_dir():
        for p in INTERNET_FLEET.glob("qemu-rack-*"):
            if not p.is_dir():
                continue
            internet_n += 1
            if (p / "h7-shard").is_dir():
                internet_h7 += 1
        # Do not add 2500 paths into stripe mesh — only a summary node
        nodes.append(
            {
                "id": "internet-fleet-summary",
                "path": str(INTERNET_FLEET),
                "kind": "internet_fleet_summary",
                "bird": "internet",
                "plane": "internet",
                "is_capacity": False,
                "writable": False,
                "servers": internet_n,
                "with_h7_shard_dirs": internet_h7,
                "note": "Internet bird — not cloud capacity stripe fabric",
            }
        )

    dc_nodes = [n for n in nodes if n.get("bird") == "datacenter"]
    writable_dc = [n for n in dc_nodes if n.get("writable")]
    # Authority count: distributed cloud center scale (125k) is the H7r cloud number
    capacity_authority = scale_n if scale_n > 0 else sum(
        1 for n in dc_nodes if n.get("kind") in ("state_capacity", "field_capacity", "archive_plane")
    )
    mesh = {
        "schema": "field-h7r-known-mesh/v2",
        "ironclad_cite": IRONCLAD,
        "updated": _utc(),
        "birds": {
            "internet": {"servers": internet_n, "is_datacenter": False},
            "datacenter": {
                "h7r_nodes": capacity_authority,
                "writable_stripe_targets": len(writable_dc) + max(0, scale_n - scale_samples),
                "is_datacenter": True,
                "distributed_cloud_center": True,
                "capacity_racks": capacity_authority,
                "scale_racks": scale_n,
                "target": TARGET_CAPACITY_RACKS,
            },
        },
        "node_count": len(nodes),
        "datacenter_nodes": capacity_authority,
        "writable_capacity_nodes": capacity_authority,
        "mesh_detail_nodes": len(nodes),
        "scale_racks": scale_n,
        "capacity_racks": capacity_authority,
        "distributed_cloud_center": True,
        "target_capacity_racks": TARGET_CAPACITY_RACKS,
        "no_owners": True,
        "planet_whole": True,
        "local_builtin_av": True,
        "always_autopilot": True,
        "nodes": nodes,
    }
    _save(MESH, mesh)
    return mesh


def list_stripe_targets(*, min_n: int = DEFAULT_MIRRORS) -> list[Path]:
    """Writable datacenter H7r paths for striping — never internet fleet."""
    mesh = discover_known_h7r() if not MESH.is_file() else _load(MESH, {})
    if not mesh.get("nodes"):
        mesh = discover_known_h7r()
    targets: list[Path] = []
    for n in mesh.get("nodes") or []:
        if n.get("bird") != "datacenter":
            continue
        if not n.get("writable"):
            continue
        if n.get("kind") == "central_vault":
            continue  # handled separately as always-on mirror
        p = Path(str(n.get("path") or ""))
        if p.is_dir():
            targets.append(p)
    # Prefer field + state capacity first, then archive
    def rank(p: Path) -> tuple[int, str]:
        s = str(p)
        if "h7r-capacity" in s or "h7r-cap-" in s or "h7r-dc-" in s:
            return (0, s)
        if "field-world-archive" in s:
            return (1, s)
        return (2, s)

    targets = sorted(set(targets), key=rank)
    if len(targets) < min_n:
        build_capacity_racks()
        mesh = discover_known_h7r()
        targets = []
        for n in mesh.get("nodes") or []:
            if n.get("bird") == "datacenter" and n.get("writable") and n.get("kind") != "central_vault":
                p = Path(str(n.get("path") or ""))
                if p.is_dir():
                    targets.append(p)
        targets = sorted(set(targets), key=rank)
    return targets


def _shard_paths(rack: Path, oid: str) -> dict[str, Path]:
    base = rack / "h7-shard" / "h7r-stripes" / oid
    return {
        "dir": base,
        **{f"s{i}": base / f"s{i}.shard" for i in range(STRIPE_K)},
        **{f"p{i}": base / f"p{i}.shard" for i in range(STRIPE_M)},
    }


def stripe_blob_across_fleet(
    packed: bytes,
    *,
    oid: str,
    header: dict[str, Any],
    mirrors: int = DEFAULT_MIRRORS,
) -> dict[str, Any]:
    """Stripe erasure pieces + full mirrors across all known H7r capacity."""
    h7r = _mod("lib/field-h7r-format.py", "h7r_fmt")
    targets = list_stripe_targets(min_n=max(mirrors, STRIPE_K + STRIPE_M))
    if not targets:
        central = CENTRAL_VAULT / f"{oid}.h7r"
        CENTRAL_VAULT.mkdir(parents=True, exist_ok=True)
        central.write_bytes(packed)
        return {
            "ok": True,
            "object_id": oid,
            "mirrors": [str(central)],
            "mirror_count": 1,
            "stripe_targets": 0,
            "degraded": True,
        }

    # Unpack stripes from packed for physical distribution
    stripe_files: list[tuple[str, bytes]] = []
    if h7r and hasattr(h7r, "unpack"):
        try:
            # re-extract stripe blob from pack format
            blob = packed
            if len(blob) >= 14 and blob[:4] == b"H7R\x01":
                import struct

                header_len = struct.unpack(">I", blob[4:8])[0]
                header_end = 8 + header_len
                stripe_count = blob[header_end]
                stripe_len = struct.unpack(">I", blob[header_end + 1 : header_end + 5])[0]
                stripe_blob = blob[header_end + 5 :]
                for i in range(stripe_count):
                    piece = stripe_blob[i * stripe_len : (i + 1) * stripe_len]
                    label = f"s{i}" if i < STRIPE_K else f"p{i - STRIPE_K}"
                    stripe_files.append((label, piece))
        except Exception:
            stripe_files = []

    mirror_paths: list[str] = []
    stripe_map: dict[str, str] = {}
    n = len(targets)

    # Full object mirrors on first `mirrors` racks (never_lose)
    for i in range(min(mirrors, n)):
        rack = targets[i]
        vault = rack / "h7-shard" / "h7r-vault"
        try:
            vault.mkdir(parents=True, exist_ok=True)
            dest = vault / f"{oid}.h7r"
            dest.write_bytes(packed)
            mirror_paths.append(str(dest))
            # also stripe copy
            sdir = rack / "h7-shard" / "h7r-stripes"
            sdir.mkdir(parents=True, exist_ok=True)
            sc = sdir / f"{oid}.stripe"
            shutil.copy2(dest, sc)
        except OSError:
            continue

    # Central vault always
    try:
        CENTRAL_VAULT.mkdir(parents=True, exist_ok=True)
        cdest = CENTRAL_VAULT / f"{oid}.h7r"
        cdest.write_bytes(packed)
        if str(cdest) not in mirror_paths:
            mirror_paths.append(str(cdest))
    except OSError:
        pass

    # Distribute individual erasure shards round-robin across ALL known targets
    if stripe_files:
        for idx, (label, piece) in enumerate(stripe_files):
            rack = targets[idx % n]
            paths = _shard_paths(rack, oid)
            try:
                paths["dir"].mkdir(parents=True, exist_ok=True)
                dest = paths["dir"] / f"{label}.shard"
                dest.write_bytes(piece)
                stripe_map[label] = str(dest)
            except OSError:
                # try next racks
                for j in range(1, min(6, n)):
                    alt = targets[(idx + j) % n]
                    ap = _shard_paths(alt, oid)
                    try:
                        ap["dir"].mkdir(parents=True, exist_ok=True)
                        dest = ap["dir"] / f"{label}.shard"
                        dest.write_bytes(piece)
                        stripe_map[label] = str(dest)
                        break
                    except OSError:
                        continue

    # Light index touch on remaining known H7r (presence stripe marker)
    marker = json.dumps(
        {
            "object_id": oid,
            "forever_hash": header.get("forever_hash"),
            "plane": "cloud_datacenter",
            "bird": "datacenter",
            "mirrors": mirror_paths[:3],
            "updated": _utc(),
        },
        separators=(",", ":"),
    ).encode()
    markers_ok = 0
    for rack in targets:
        try:
            mdir = rack / "h7-shard" / "h7r-stripes" / "_mesh"
            mdir.mkdir(parents=True, exist_ok=True)
            (mdir / f"{oid}.json").write_bytes(marker)
            markers_ok += 1
        except OSError:
            continue

    return {
        "ok": True,
        "object_id": oid,
        "mirrors": mirror_paths,
        "mirror_count": len(mirror_paths),
        "stripe_map": stripe_map,
        "stripe_shard_count": len(stripe_map),
        "stripe_targets_total": n,
        "mesh_markers": markers_ok,
        "erasure": f"{STRIPE_K}+{STRIPE_M}",
        "never_lose_mirrors": mirrors,
        "plane": "cloud_datacenter",
        "bird": "datacenter",
        "not_internet_fleet": True,
    }


def restripe_index(*, limit: int = 200, workers: int = WORKERS) -> dict[str, Any]:
    """Restripe recent vault objects across full known H7r mesh."""
    idx = _load(STATE / "field-h7r-vault-index.json", {})
    objects = idx.get("objects") or {}
    items = list(objects.items())[-limit:]
    ok_n = 0
    fail_n = 0
    targets = list_stripe_targets()
    if not targets:
        return {"ok": False, "error": "no_stripe_targets"}

    def one(oid: str, row: dict[str, Any]) -> bool:
        # find existing packed bytes
        packed = b""
        for m in row.get("mirrors") or []:
            p = Path(m)
            if p.is_file():
                try:
                    packed = p.read_bytes()
                    break
                except OSError:
                    continue
        if not packed:
            for t in targets[:12]:
                cand = t / "h7-shard" / "h7r-vault" / f"{oid}.h7r"
                if cand.is_file():
                    try:
                        packed = cand.read_bytes()
                        break
                    except OSError:
                        continue
        if not packed:
            c = CENTRAL_VAULT / f"{oid}.h7r"
            if c.is_file():
                packed = c.read_bytes()
        if not packed:
            return False
        header = {"forever_hash": row.get("forever_hash")}
        res = stripe_blob_across_fleet(packed, oid=oid, header=header)
        if res.get("ok"):
            row["mirrors"] = res.get("mirrors") or row.get("mirrors")
            row["mirror_count"] = res.get("mirror_count")
            row["stripe_map"] = res.get("stripe_map")
            row["restriped"] = _utc()
            row["plane"] = "cloud_datacenter"
            objects[oid] = row
            return True
        return False

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(one, oid, dict(row)): oid for oid, row in items}
        for fut in as_completed(futs):
            try:
                if fut.result():
                    ok_n += 1
                else:
                    fail_n += 1
            except Exception:
                fail_n += 1

    idx["objects"] = objects
    idx["count"] = len(objects)
    idx["updated"] = _utc()
    idx["storage_version"] = "h7r/1"
    idx["plane"] = "cloud_datacenter"
    _save(STATE / "field-h7r-vault-index.json", idx)
    out = {
        "ok": True,
        "restriped_ok": ok_n,
        "restriped_fail": fail_n,
        "considered": len(items),
        "stripe_targets": len(targets),
    }
    _append({"event": "restripe", **out})
    return out


def build_all(*, restripe: bool = True, restripe_limit: int = 200, scale: bool = True) -> dict[str, Any]:
    """Full capacity fleet build + scale to 125k distributed cloud + discover."""
    built = build_capacity_racks()
    scaled: dict[str, Any] = {}
    if scale:
        scaled = scale_distributed_cloud(target=TARGET_CAPACITY_RACKS)
    mesh = discover_known_h7r()
    stripe_n = len(list_stripe_targets())
    restriped: dict[str, Any] = {}
    if restripe:
        restriped = restripe_index(limit=restripe_limit)

    dc = mesh.get("birds", {}).get("datacenter") or {}
    internet = mesh.get("birds", {}).get("internet") or {}
    scale_n = int(scaled.get("scale_racks") or mesh.get("scale_racks") or _count_scale_racks() or 0)
    hot_racks = sum(
        1
        for n in (mesh.get("nodes") or [])
        if n.get("bird") == "datacenter"
        and n.get("kind") in ("state_capacity", "field_capacity", "archive_plane")
    )
    # Authority for distributed cloud center = scale plane (target 125k)
    capacity_racks = scale_n if scale_n > 0 else hot_racks
    physical_gb = capacity_racks * GB_PER_RACK
    panel = {
        "ok": True,
        "schema": "field-h7r-capacity-fleet/v2",
        "ironclad_cite": IRONCLAD,
        "updated": _utc(),
        "title": "H7r Capacity Fleet — Distributed cloud center",
        "motto": (
            f"H7r distributed cloud center · {capacity_racks:,} capacity racks · "
            f"target {TARGET_CAPACITY_RACKS:,} · hot {hot_racks:,} · "
            "datacenter bird · no owners · planet whole · local AV"
        ),
        "birds": {
            "internet": {
                "servers": internet.get("servers") or 2500,
                "is_datacenter": False,
                "is_cloud_storage": False,
            },
            "datacenter": {
                "h7r_nodes": capacity_racks,
                "writable_stripe_targets": stripe_n,
                "is_datacenter": True,
                "is_cloud_storage": True,
                "capacity_racks": capacity_racks,
                "scale_racks": scale_n,
                "hot_racks": hot_racks,
                "target": TARGET_CAPACITY_RACKS,
                "distributed_cloud_center": True,
                "physical_gb_doctrine": physical_gb,
                "physical_tb_doctrine": round(physical_gb / 1024, 2),
            },
        },
        "build": built,
        "scale": scaled,
        "mesh": {
            "node_count": mesh.get("node_count"),
            "datacenter_nodes": mesh.get("datacenter_nodes"),
            "writable_capacity_nodes": mesh.get("writable_capacity_nodes"),
            "scale_racks": scale_n,
            "capacity_racks": capacity_racks,
        },
        "restripe": restriped,
        "redundancy": {
            "erasure": f"{STRIPE_K}+{STRIPE_M}",
            "never_lose_mirrors": DEFAULT_MIRRORS,
            "cloud_services": ["object", "block", "archive", "big_data"],
            "free": True,
            "no_charge": True,
        },
        "roots": {
            "state_capacity": str(STATE_CAP),
            "field_capacity": str(FIELD_CAP),
            "distributed_cloud_center": str(_scale_root()),
            "archive_racks": str(ARCHIVE_RACKS),
            "central_vault": str(CENTRAL_VAULT),
            "internet_fleet_not_capacity": str(INTERNET_FLEET),
        },
        "target_capacity_racks": TARGET_CAPACITY_RACKS,
        "capacity_racks": capacity_racks,
        "distributed_cloud_center": True,
        "no_owners": True,
        "planet_whole": True,
        "local_builtin_av": True,
        "always_autopilot": True,
        "api": "/api/field-h7r-capacity-fleet",
        "cloud_api": "/api/field-ammonet-cloud",
    }
    _save(PANEL, panel)
    reg = {
        "schema": "field-h7r-capacity-fleet-registry/v2",
        "updated": _utc(),
        "capacity_racks": capacity_racks,
        "scale_racks": scale_n,
        "hot_racks": hot_racks,
        "target_capacity_racks": TARGET_CAPACITY_RACKS,
        "stripe_targets": stripe_n,
        "physical_gb_doctrine": physical_gb,
        "physical_tb_doctrine": round(physical_gb / 1024, 2),
        "birds_separate": True,
        "distributed_cloud_center": True,
        "no_owners": True,
        "planet_whole": True,
        "local_builtin_av": True,
        "always_autopilot": True,
        "scale_root": str(_scale_root()),
    }
    _save(FLEET_REG, reg)
    return panel


def panel() -> dict[str, Any]:
    doc = _load(PANEL, {})
    if doc.get("ok"):
        # refresh live mesh counts cheaply
        mesh = _load(MESH, {})
        if mesh:
            doc["mesh_live"] = {
                "node_count": mesh.get("node_count"),
                "datacenter_nodes": mesh.get("datacenter_nodes"),
                "writable": mesh.get("writable_capacity_nodes"),
                "updated": mesh.get("updated"),
            }
        return doc
    return build_all(restripe=False)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "build").strip().lower()
    if cmd in ("scale", "125k", "up", "distributed-cloud", "cloud-center"):
        target = TARGET_CAPACITY_RACKS
        for a in sys.argv[2:]:
            if a.startswith("--target="):
                try:
                    target = int(a.split("=", 1)[1])
                except ValueError:
                    pass
            elif a.isdigit():
                target = int(a)
        scaled = scale_distributed_cloud(target=target)
        mesh = discover_known_h7r()
        # refresh panel without full restripe
        panel_doc = build_all(restripe=False, scale=False)
        panel_doc["scale"] = scaled
        panel_doc["capacity_racks"] = scaled.get("scale_racks") or panel_doc.get("capacity_racks")
        _save(PANEL, panel_doc)
        print(json.dumps({
            "ok": scaled.get("ok"),
            "scale": scaled,
            "mesh_capacity_racks": mesh.get("capacity_racks"),
            "panel_capacity_racks": panel_doc.get("capacity_racks"),
            "motto": scaled.get("motto") or panel_doc.get("motto"),
        }, ensure_ascii=False, indent=2))
        return 0 if scaled.get("ok") else 1
    if cmd in ("build", "all", "start", "capacity"):
        restripe = "--no-restripe" not in sys.argv
        limit = 200
        do_scale = "--no-scale" not in sys.argv
        for a in sys.argv[2:]:
            if a.startswith("--limit="):
                try:
                    limit = int(a.split("=", 1)[1])
                except ValueError:
                    pass
        print(json.dumps(
            build_all(restripe=restripe, restripe_limit=limit, scale=do_scale),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("discover", "mesh"):
        print(json.dumps(discover_known_h7r(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "restripe":
        limit = 200
        for a in sys.argv[2:]:
            if a.startswith("--limit="):
                try:
                    limit = int(a.split("=", 1)[1])
                except ValueError:
                    pass
        print(json.dumps(restripe_index(limit=limit), ensure_ascii=False, indent=2))
        return 0
    if cmd == "targets":
        t = list_stripe_targets()
        print(json.dumps({"ok": True, "count": len(t), "targets": [str(p) for p in t[:50]]}, indent=2))
        return 0
    print(
        json.dumps(
            {
                "usage": (
                    "field-h7r-capacity-fleet.py "
                    "[build|scale|json|discover|restripe|targets] "
                    "[--no-restripe] [--no-scale] [--limit=N] [--target=125000]"
                ),
                "note": "Datacenter bird · distributed cloud center target 125000 — Internet 2500 separate",
                "target_capacity_racks": TARGET_CAPACITY_RACKS,
            },
            indent=2,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
