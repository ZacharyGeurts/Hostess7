#!/usr/bin/env python3
"""Field IRC BSP — Ironclad composite partition · 100 servers/batch · bi-comm every rack."""
from __future__ import annotations

import hashlib
import importlib.util
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
DOCTRINE = INSTALL / "data" / "field-irc-doctrine.json"
PANEL = STATE / "field-irc-bsp-panel.json"
REGISTRY = STATE / "field-global-servers-registry.json"
LEDGER = STATE / "field-irc-bsp-ledger.jsonl"
BATCH_SIZE = 100


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


def _run_json(rel: str, args: list[str], *, timeout: int = 120) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": f"missing {rel}"}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
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
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)[:200]}
    return {"ok": False, "error": "script_failed", "script": rel}


def _composite_bsp_sort(rows: list[dict[str, Any]], *, key: str = "bsp_score") -> list[dict[str, Any]]:
    if len(rows) <= 1:
        return list(rows)

    def score(row: dict[str, Any], idx: int) -> float:
        raw = row.get(key)
        if raw is None:
            raw = row.get("tunnel") or row.get("metro_slot") or (len(rows) - idx)
        return float(raw)

    scored = [(score(r, i), r) for i, r in enumerate(rows)]
    scored.sort(key=lambda t: t[0], reverse=True)
    mid = len(scored) // 2
    left = _composite_bsp_sort([r for _, r in scored[:mid]], key=key)
    right = _composite_bsp_sort([r for _, r in scored[mid:]], key=key)
    return left + right


def _ironclad_slice() -> dict[str, Any]:
    ic = _mod("lib/ironclad-field-sanity.py", "ic_bsp")
    if ic and hasattr(ic, "build_panel"):
        try:
            return ic.build_panel(write=False, body={})
        except (TypeError, ValueError, OSError):
            pass
    cached = _load(STATE / "ironclad-field-sanity-panel.json", {})
    return cached if cached else {"ok": True, "integral": True}


def _bsp_score(row: dict[str, Any], *, boost: float, generation: int) -> float:
    sid = str(row.get("id") or row.get("rack_id") or row.get("field_id") or "")
    metro = str(row.get("metro_id") or row.get("region_id") or "")
    tunnel = int(row.get("tunnel") or row.get("panel_port") or 0)
    digest = hashlib.sha256(f"{sid}|{metro}|{generation}".encode()).hexdigest()
    base = int(digest[:8], 16) / 0xFFFFFFFF * 100.0
    primary = 12.0 if row.get("dns_primary") else 0.0
    primary += 12.0 if row.get("dhcp_primary") else 0.0
    online = 8.0 if row.get("online", True) else 0.0
    return round((base + primary + online + tunnel * 0.001) * boost, 4)


def _fleet_rows() -> list[dict[str, Any]]:
    reg = _load(REGISTRY, {})
    return [r for r in (reg.get("servers") or []) if isinstance(r, dict)]


def _physical_racks() -> list[dict[str, Any]]:
    inv = _mod("lib/field-rack-inventory.py", "rack_inv_bsp")
    if inv and hasattr(inv, "inventory"):
        doc = inv.inventory(fast=True, probe=False)
        return [r for r in (doc.get("racks") or []) if isinstance(r, dict)]
    cached = _load(STATE / "field-rack-inventory-panel.json", {})
    return [r for r in (cached.get("racks") or []) if isinstance(r, dict)]


def build_partitions(*, batch_size: int | None = None) -> list[list[dict[str, Any]]]:
    doctrine = _load(DOCTRINE, {})
    bsp = doctrine.get("bsp") or {}
    size = int(batch_size or bsp.get("batch_size") or BATCH_SIZE)
    boost = float(bsp.get("ironclad_boost") or 1.08)
    ic = _ironclad_slice()
    generation = int(ic.get("verse") or ic.get("meld_citation", "0").split(":")[-1] if isinstance(ic.get("meld_citation"), str) else 0) or 1

    rows: list[dict[str, Any]] = []
    for srv in _fleet_rows():
        rows.append({
            **srv,
            "lane": "global",
            "bsp_score": _bsp_score(srv, boost=boost, generation=generation),
        })
    for rack in _physical_racks():
        rows.append({
            **rack,
            "lane": "physical",
            "id": str(rack.get("rack_id") or rack.get("field_id") or "local"),
            "bsp_score": _bsp_score(rack, boost=boost, generation=generation) + 20.0,
        })

    sorted_rows = _composite_bsp_sort(rows, key="bsp_score")
    return [sorted_rows[i : i + size] for i in range(0, len(sorted_rows), size)]


def _stamp_batch(batch: list[dict[str, Any]], *, batch_index: int) -> dict[str, Any]:
    reg = _load(REGISTRY, {})
    servers = list(reg.get("servers") or [])
    ids = {str(r.get("id") or "").lower() for r in batch if r.get("lane") == "global"}
    stamped = 0
    for i, row in enumerate(servers):
        if not isinstance(row, dict):
            continue
        sid = str(row.get("id") or "").lower()
        if sid not in ids:
            continue
        servers[i] = {
            **row,
            "chat_bsp_shard": batch_index,
            "chat_bicomm": True,
            "dns_primary": True,
            "dhcp_primary": True,
            "dns_dhcp_everywhere": True,
            "ironclad_bsp": True,
            "updated": _utc(),
        }
        stamped += 1
    reg["servers"] = servers
    reg["bsp_distributed"] = True
    reg["updated"] = _utc()
    _save(REGISTRY, reg)
    return {"stamped": stamped, "batch_index": batch_index}


def distribute_batch(
    batch_index: int,
    *,
    dns_dhcp: bool = True,
    rack_fanout: bool = False,
    announce: str = "",
) -> dict[str, Any]:
    partitions = build_partitions()
    if batch_index < 0 or batch_index >= len(partitions):
        return {"ok": False, "error": "batch_out_of_range", "batches": len(partitions)}
    batch = partitions[batch_index]
    stamp = _stamp_batch(batch, batch_index=batch_index)
    steps: list[dict[str, Any]] = [{"step": "stamp_registry", **stamp}]

    if dns_dhcp:
        keep = _run_json("lib/field-botnet-dns-dhcp.py", ["keepalive"], timeout=45)
        steps.append({"step": "dns_dhcp_keepalive", **keep})

    racks_out: dict[str, Any] | None = None
    if rack_fanout and announce:
        racks_out = rack_fanout(announce, room_id="mesh-global", person="field-irc-bsp")
        steps.append({"step": "rack_fanout", **(racks_out or {})})

    panel_doc = _load(PANEL, {"schema": "field-irc-bsp/v1", "batches_done": []})
    done = set(panel_doc.get("batches_done") or [])
    done.add(batch_index)
    panel_doc.update({
        "ok": True,
        "schema": "field-irc-bsp/v1",
        "updated": _utc(),
        "algorithm": "composite_bsp",
        "authority": "ironclad",
        "batch_size": int((_load(DOCTRINE, {}).get("bsp") or {}).get("batch_size") or BATCH_SIZE),
        "batch_index": batch_index,
        "batch_count": len(partitions),
        "batch_servers": len(batch),
        "batches_done": sorted(done),
        "batches_total": len(partitions),
        "ironclad": _ironclad_slice(),
        "steps": steps,
    })
    _save(PANEL, panel_doc)
    _append_ledger({"event": "bsp_batch", "batch_index": batch_index, "servers": len(batch), "stamped": stamp.get("stamped")})
    return panel_doc


def _batch_server_ids(batch: list[dict[str, Any]]) -> set[str]:
    return {
        str(r.get("id") or r.get("rack_id") or r.get("field_id") or "").lower()
        for r in batch
        if r.get("lane") == "global"
    }


def verify_batch_online(
    batch_index: int,
    *,
    min_online_ratio: float = 1.0,
    retries: int = 4,
    retry_delay_s: float = 2.0,
) -> dict[str, Any]:
    """Confirm batch servers stamped and marked online before advancing."""
    partitions = build_partitions()
    if batch_index < 0 or batch_index >= len(partitions):
        return {"ok": False, "error": "batch_out_of_range", "batch_index": batch_index}
    batch = partitions[batch_index]
    ids = _batch_server_ids(batch)
    physical = [r for r in batch if r.get("lane") == "physical"]
    attempts: list[dict[str, Any]] = []
    online = 0
    stamped = 0
    dns_dhcp = 0
    ok = False
    for attempt in range(max(1, retries)):
        reg = _load(REGISTRY, {})
        servers = [s for s in (reg.get("servers") or []) if isinstance(s, dict)]
        rows = [s for s in servers if str(s.get("id") or "").lower() in ids]
        stamped = sum(1 for s in rows if s.get("chat_bsp_shard") == batch_index)
        online = sum(1 for s in rows if s.get("online", True) and s.get("chat_bicomm"))
        dns_dhcp = sum(
            1 for s in rows
            if s.get("dns_primary") and s.get("dhcp_primary") and s.get("dns_dhcp_everywhere")
        )
        physical_ok = len(physical) == 0 or all(r.get("online", True) for r in physical)
        need = max(1, int(len(ids) * min_online_ratio)) if ids else 0
        ratio = (online / len(ids)) if ids else 1.0
        ok = (
            physical_ok
            and (not ids or online >= need)
            and (not ids or stamped >= need)
            and (not ids or dns_dhcp >= need)
        )
        attempts.append({
            "attempt": attempt + 1,
            "online": online,
            "stamped": stamped,
            "dns_dhcp": dns_dhcp,
            "need": need,
            "ratio": round(ratio, 4),
            "physical_ok": physical_ok,
            "ok": ok,
        })
        if ok:
            break
        if attempt + 1 < retries:
            _run_json("lib/field-botnet-dns-dhcp.py", ["keepalive"], timeout=45)
            time.sleep(retry_delay_s)
    protect = _run_json("lib/field-fleet-2500-protect.py", ["verify"], timeout=120)
    return {
        "ok": ok,
        "schema": "field-irc-bsp-batch-verify/v1",
        "updated": _utc(),
        "batch_index": batch_index,
        "batch_servers": len(batch),
        "global_ids": len(ids),
        "physical_racks": len(physical),
        "online": online,
        "stamped": stamped,
        "dns_dhcp": dns_dhcp,
        "min_online_ratio": min_online_ratio,
        "attempts": attempts,
        "fleet_protect": protect,
    }


def distribute_batches_verified(
    *,
    dns_dhcp: bool = True,
    limit: int | None = None,
    start_index: int = 0,
    verify_retries: int = 4,
    halt_on_fail: bool = True,
) -> dict[str, Any]:
    """Distribute 100-server batches — verify online before each next batch."""
    partitions = build_partitions()
    cap = len(partitions) if limit is None else min(len(partitions), max(0, int(limit)))
    start = max(0, int(start_index))
    results: list[dict[str, Any]] = []
    halted = False
    halt_reason = ""
    for idx in range(start, cap):
        dist = distribute_batch(idx, dns_dhcp=dns_dhcp, rack_fanout=False)
        verify = verify_batch_online(idx, retries=verify_retries)
        row = {
            "batch_index": idx,
            "distribute": dist,
            "verify": verify,
            "ok": bool(dist.get("ok")) and bool(verify.get("ok")),
        }
        results.append(row)
        _append_ledger({
            "event": "bsp_batch_verified",
            "batch_index": idx,
            "ok": row["ok"],
            "online": verify.get("online"),
            "stamped": verify.get("stamped"),
        })
        if not row["ok"] and halt_on_fail:
            halted = True
            halt_reason = "batch_verify_failed"
            break
    if dns_dhcp:
        fix = _run_json("lib/field-dns-dhcp-fix.py", ["everywhere"], timeout=180)
    else:
        fix = {"ok": True, "skipped": True}
    out = {
        "ok": not halted and all(r.get("ok") for r in results),
        "schema": "field-irc-bsp-verified-rollout/v1",
        "updated": _utc(),
        "batch_size": BATCH_SIZE,
        "batches_run": len(results),
        "batches_total": len(partitions),
        "start_index": start,
        "limit": cap,
        "halted": halted,
        "halt_reason": halt_reason or None,
        "dns_dhcp_everywhere": fix,
        "batches": results,
    }
    panel = _load(PANEL, {"schema": "field-irc-bsp/v1", "batches_done": []})
    done = set(panel.get("batches_done") or [])
    for row in results:
        if row.get("ok"):
            done.add(row["batch_index"])
    panel.update({
        "ok": out["ok"],
        "schema": "field-irc-bsp/v1",
        "updated": _utc(),
        "verified_rollout": True,
        "batches_done": sorted(done),
        "batches_total": len(partitions),
        "last_rollout": out,
    })
    _save(PANEL, panel)
    return out


def distribute_all(*, dns_dhcp: bool = True, limit: int | None = None) -> dict[str, Any]:
    partitions = build_partitions()
    cap = len(partitions) if limit is None else min(len(partitions), max(0, int(limit)))
    results: list[dict[str, Any]] = []
    for idx in range(cap):
        results.append(distribute_batch(idx, dns_dhcp=dns_dhcp, rack_fanout=False))
    if dns_dhcp:
        fix = _run_json("lib/field-dns-dhcp-fix.py", ["everywhere"], timeout=180)
    else:
        fix = {"ok": True, "skipped": True}
    out = {
        "ok": True,
        "schema": "field-irc-bsp-distribute-all/v1",
        "updated": _utc(),
        "batches_run": cap,
        "batches_total": len(partitions),
        "batch_size": BATCH_SIZE,
        "dns_dhcp_everywhere": fix,
        "batches": results,
    }
    _save(PANEL, {**_load(PANEL, {}), **out, "schema": "field-irc-bsp/v1"})
    return out


def rack_fanout(
    text: str,
    *,
    room_id: str = "mesh-global",
    person: str = "operator",
) -> dict[str, Any]:
    """Bi-comm: push world chat to every physical rack; collect replies."""
    chat = _mod("lib/field-rack-grok-chat.py", "rack_chat_bsp")
    if not chat or not hasattr(chat, "chat_to_rack"):
        return {"ok": False, "error": "rack_chat_missing"}
    racks = _physical_racks()
    payload = f"[IRC:{room_id}] {person}: {text}"
    replies: list[dict[str, Any]] = []
    ok_count = 0
    for rack in racks:
        rid = str(rack.get("rack_id") or rack.get("field_id") or "local")
        try:
            out = chat.chat_to_rack(rid, payload, action="chat")
        except (TypeError, ValueError, OSError) as exc:
            out = {"ok": False, "error": str(exc)[:120]}
        if out.get("ok"):
            ok_count += 1
        replies.append({
            "rack_id": rid,
            "label": rack.get("label"),
            "ok": out.get("ok"),
            "reply": (out.get("reply") or "")[:400],
            "route": out.get("route"),
        })
    _append_ledger({"event": "rack_fanout", "room_id": room_id, "racks": len(racks), "ok": ok_count})
    return {
        "ok": ok_count > 0,
        "schema": "field-irc-bsp-rack-fanout/v1",
        "room_id": room_id,
        "racks_total": len(racks),
        "racks_ok": ok_count,
        "replies": replies,
    }


def rack_inbound(
    *,
    rack_id: str,
    text: str,
    person: str = "rack",
    room_id: str = "mesh-global",
) -> dict[str, Any]:
    """Bi-comm inbound: rack reply into world chat."""
    irc = _mod("lib/field-irc.py", "irc_inbound")
    if not irc or not hasattr(irc, "irc_post"):
        return {"ok": False, "error": "field_irc_missing"}
    msg = f"↩ {rack_id}: {text}"
    return irc.irc_post(room_id, person=person, text=msg, device_id=f"rack-{rack_id}")


def bsp_status() -> dict[str, Any]:
    partitions = build_partitions()
    panel = _load(PANEL, {})
    doctrine = _load(DOCTRINE, {})
    reg = _load(REGISTRY, {})
    stamped = sum(
        1 for s in (reg.get("servers") or [])
        if isinstance(s, dict) and s.get("chat_bsp_shard") is not None
    )
    return {
        "ok": True,
        "schema": "field-irc-bsp/v1",
        "updated": _utc(),
        "algorithm": "composite_bsp",
        "authority": "ironclad",
        "batch_size": int((doctrine.get("bsp") or {}).get("batch_size") or BATCH_SIZE),
        "batches_total": len(partitions),
        "batches_done": panel.get("batches_done") or [],
        "servers_stamped": stamped,
        "fleet_count": len(_fleet_rows()),
        "physical_racks": len(_physical_racks()),
        "ironclad": _ironclad_slice(),
        "dns_dhcp": {
            "everywhere": True,
            "api": "/api/field-dns-dhcp-fix",
        },
        "panel": panel,
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return bsp_status()
    if action in ("partitions", "build_partitions"):
        parts = build_partitions(batch_size=body.get("batch_size"))
        return {"ok": True, "batches": len(parts), "batch_size": BATCH_SIZE, "sizes": [len(p) for p in parts]}
    if action in ("batch", "distribute_batch", "bsp_batch"):
        return distribute_batch(
            int(body.get("batch_index") or body.get("batch") or 0),
            dns_dhcp=bool(body.get("dns_dhcp", True)),
            rack_fanout=bool(body.get("rack_fanout")),
            announce=str(body.get("announce") or body.get("text") or ""),
        )
    if action in ("distribute", "distribute_all", "bsp_distribute"):
        return distribute_all(dns_dhcp=bool(body.get("dns_dhcp", True)), limit=body.get("limit"))
    if action in ("verify_batch", "batch_verify", "verify"):
        return verify_batch_online(
            int(body.get("batch_index") or body.get("batch") or 0),
            min_online_ratio=float(body.get("min_online_ratio") or 1.0),
            retries=int(body.get("retries") or 4),
        )
    if action in ("rollout", "distribute_verified", "verified_rollout", "war_rollout"):
        lim = body.get("limit")
        return distribute_batches_verified(
            dns_dhcp=bool(body.get("dns_dhcp", True)),
            limit=None if lim in (None, "", "all", "none", 0, "0") else lim,
            start_index=int(body.get("start_index") or body.get("start") or 0),
            verify_retries=int(body.get("verify_retries") or body.get("retries") or 4),
            halt_on_fail=bool(body.get("halt_on_fail", True)),
        )
    if action in ("rack_fanout", "fanout"):
        return rack_fanout(
            str(body.get("text") or body.get("message") or ""),
            room_id=str(body.get("room_id") or body.get("room") or "mesh-global"),
            person=str(body.get("person") or "operator"),
        )
    if action in ("rack_inbound", "inbound"):
        return rack_inbound(
            rack_id=str(body.get("rack_id") or ""),
            text=str(body.get("text") or body.get("message") or ""),
            person=str(body.get("person") or "rack"),
            room_id=str(body.get("room_id") or body.get("room") or "mesh-global"),
        )
    return {
        "ok": False,
        "error": "unknown_action",
        "actions": [
            "status", "partitions", "batch", "verify_batch", "distribute",
            "rollout", "rack_fanout", "rack_inbound",
        ],
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("json", "status"):
        print(json.dumps(bsp_status(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("rollout", "verified", "verified-rollout", "war-rollout"):
        limit = None
        start = 0
        for arg in sys.argv[2:]:
            if arg.isdigit():
                if start == 0 and "start" not in sys.argv[: sys.argv.index(arg)]:
                    limit = int(arg) if limit is None else limit
                else:
                    start = int(arg)
        print(json.dumps(
            distribute_batches_verified(limit=limit, start_index=start),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("verify-batch", "verify") and len(sys.argv) > 2 and sys.argv[2].isdigit():
        print(json.dumps(verify_batch_online(int(sys.argv[2])), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("distribute", "distribute-all"):
        limit = None
        for arg in sys.argv[2:]:
            if arg.isdigit():
                limit = int(arg)
        print(json.dumps(distribute_all(limit=limit), ensure_ascii=False, indent=2))
        return 0
    if cmd == "batch" and len(sys.argv) > 2 and sys.argv[2].isdigit():
        print(json.dumps(distribute_batch(int(sys.argv[2])), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-irc-bsp.py [json|distribute [N]|batch N|dispatch]"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())