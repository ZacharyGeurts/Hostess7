#!/usr/bin/env python3
"""GitHub resilience — loopback authority, degraded probes, publish queue when push lane is down."""
from __future__ import annotations

import importlib.util
import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-github-resilience-doctrine.json"
PANEL = STATE / "field-github-resilience-panel.json"
PROBE_CACHE = STATE / "field-github-resilience-probe.json"


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


def _queue_path(doctrine: dict[str, Any]) -> Path:
    rel = str((doctrine.get("publish_queue") or {}).get("path") or ".nexus-state/hostess7-publish-queue.json")
    return INSTALL / rel if not rel.startswith("/") else Path(rel)


def _probe_tcp(host: str, port: int, timeout: float = 4.0) -> dict[str, Any]:
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed_ms = int((time.monotonic() - started) * 1000)
            return {"ok": True, "host": host, "port": port, "elapsed_ms": elapsed_ms}
    except OSError as exc:
        return {"ok": False, "host": host, "port": port, "error": str(exc)[:120]}


def _probe_url(url: str, *, timeout: float = 4.0) -> dict[str, Any]:
    ctx = ssl.create_default_context()
    started = time.monotonic()
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "FieldGitHubResilience/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            return {"ok": True, "status": resp.status, "elapsed_ms": elapsed_ms, "url": url}
    except urllib.error.HTTPError as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        ok = exc.code < 500
        if exc.code == 403 and "api.github.com" in url:
            ok = True
        return {"ok": ok, "status": exc.code, "elapsed_ms": elapsed_ms, "url": url}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)[:120], "url": url}


def _loopback_up(doctrine: dict[str, Any]) -> dict[str, Any]:
    lb = doctrine.get("loopback_authority") or {}
    host = str(lb.get("host") or "127.0.0.1")
    port = int(lb.get("port") or 9477)
    base = str(lb.get("base") or f"http://{host}:{port}").rstrip("/")
    tcp = _probe_tcp(host, port, timeout=1.5)
    api_hit = {"ok": False}
    if tcp.get("ok"):
        for ep in ("/api/status", "/api/field-github-resilience", "/api/field-internet"):
            api_hit = _probe_url(f"{base}{ep}", timeout=2.0)
            if api_hit.get("ok"):
                api_hit["endpoint"] = ep
                break
    return {
        "ok": bool(tcp.get("ok")),
        "tcp": tcp,
        "api": api_hit,
        "base": base,
        "authority": base if tcp.get("ok") else None,
    }


def _traffic_shard_mod():
    path = INSTALL / "lib" / "field-github-traffic-shard.py"
    spec = importlib.util.spec_from_file_location("field_github_traffic_shard", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def probe_all(*, write: bool = True, fast: bool = False) -> dict[str, Any]:
    shard = _traffic_shard_mod()
    if fast and PROBE_CACHE.is_file():
        cached = _load(PROBE_CACHE, {})
        if cached.get("schema") and (not shard or shard.cache_fresh(cached.get("updated"), fast=True)):
            cached["cached"] = True
            return cached

    doctrine = _load(DOCTRINE, {})
    specs = list(doctrine.get("probes") or [])
    plan: dict[str, Any] = {}
    cached_rows: list[dict[str, Any]] = []
    if shard is not None:
        try:
            plan = shard.plan_probe_batch(specs, fast=fast, probe_kind="resilience")
            live_specs = list(plan.get("live_batch_eps") or [])
            cached_rows = list(plan.get("cached_rows_data") or [])
        except (OSError, AttributeError, TypeError):
            live_specs = specs[:1]
    else:
        live_specs = specs[:2] if fast else specs

    rows: list[dict[str, Any]] = []
    weight_open = 0
    for spec in live_specs:
        weight = int(spec.get("weight") or 1)
        if spec.get("url"):
            hit = _probe_url(str(spec["url"]), timeout=2.8 if fast else 4.0)
            row = {**spec, **hit}
        else:
            hit = _probe_tcp(str(spec.get("host") or ""), int(spec.get("port") or 0), timeout=2.8 if fast else 4.0)
            row = {**spec, **hit}
        if row.get("ok"):
            weight_open += weight
        rows.append(row)

    live_only = list(rows)
    if shard and plan and cached_rows:
        rows = shard.merge_probe_rows(live_only, cached_rows, active_shard=str(plan.get("active_shard") or ""), plan=plan)
        shard.record_live_shard(str(plan.get("active_shard") or ""), live_only, probe_kind="resilience")
        weight_open = sum(int(r.get("weight") or 1) for r in rows if r.get("ok"))

    loopback = _loopback_up(doctrine)
    open_n = sum(1 for r in rows if r.get("ok"))
    pages_open = any(r.get("ok") and r.get("role") == "pages" for r in rows)
    raw_open = any(r.get("ok") and r.get("role") == "raw" for r in rows)
    git_push_open = any(r.get("ok") and r.get("role") == "git_push" for r in rows)
    deg = doctrine.get("degraded_ok_when") or {}
    min_open = int(deg.get("min_open_probes") or 1)
    degraded_ok = bool(
        (not deg.get("loopback_up") or loopback.get("ok"))
        and (not deg.get("pages_or_raw_open") or pages_open or raw_open)
        and open_n >= min_open
    )

    doc = {
        "schema": "field-github-resilience-probe/v1",
        "updated": _utc(),
        "ok": degraded_ok or git_push_open,
        "degraded_ok": degraded_ok,
        "github_push_ready": git_push_open,
        "open_count": open_n,
        "weight_open": weight_open,
        "pages_open": pages_open,
        "raw_open": raw_open,
        "loopback": loopback,
        "authority": loopback.get("authority") if loopback.get("ok") else (doctrine.get("pages_fallback_origin")),
        "probes": rows,
        "fast": fast,
        "traffic_shard": {
            "offload_pct": plan.get("offload_pct"),
            "active_shard": plan.get("active_shard"),
            "field_nodes": plan.get("field_nodes"),
            "live_batch": plan.get("live_batch"),
        } if plan else None,
    }
    if write:
        _save(PROBE_CACHE, doc)
    return doc


def queue_list(doctrine: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = _load(_queue_path(doctrine or _load(DOCTRINE, {})), {"schema": "hostess7-publish-queue/v1", "entries": []})
    if "entries" not in doc:
        doc["entries"] = []
    return doc


def enqueue_publish(
    *,
    version: str,
    tag: str,
    stage: str,
    remote: str,
    repo: str = "ZacharyGeurts/Hostess7",
    reason: str = "github_unreachable",
) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    qpath = _queue_path(doctrine)
    doc = queue_list(doctrine)
    max_entries = int((doctrine.get("publish_queue") or {}).get("max_entries") or 32)
    entry = {
        "id": f"pub-{int(time.time())}",
        "version": version,
        "tag": tag,
        "stage": stage,
        "remote": remote,
        "repo": repo,
        "reason": reason,
        "queued_at": _utc(),
        "status": "queued",
    }
    entries = [e for e in doc.get("entries") or [] if isinstance(e, dict)]
    entries.append(entry)
    doc["entries"] = entries[-max_entries:]
    doc["updated"] = _utc()
    doc["pending"] = sum(1 for e in doc["entries"] if e.get("status") == "queued")
    _save(qpath, doc)
    return {"ok": True, "queued": entry, "pending": doc["pending"], "queue_path": str(qpath)}


def flush_queue(*, dry: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    live = probe_all(write=True, fast=False)
    if not live.get("github_push_ready"):
        return {
            "ok": False,
            "error": "github push lane still down",
            "degraded_ok": live.get("degraded_ok"),
            "authority": live.get("authority"),
        }
    qpath = _queue_path(doctrine)
    doc = queue_list(doctrine)
    flushed: list[dict[str, Any]] = []
    for entry in doc.get("entries") or []:
        if not isinstance(entry, dict) or entry.get("status") != "queued":
            continue
        if dry:
            flushed.append({**entry, "would_flush": True})
            continue
        entry["status"] = "ready_to_push"
        entry["flush_at"] = _utc()
        flushed.append(entry)
    doc["entries"] = [e for e in doc.get("entries") or [] if isinstance(e, dict)]
    doc["updated"] = _utc()
    doc["pending"] = sum(1 for e in doc["entries"] if e.get("status") == "queued")
    _save(qpath, doc)
    return {"ok": True, "flushed": flushed, "pending": doc["pending"], "note": "run publish-hostess7-github.sh --push per entry"}


def panel(*, write: bool = True, fast: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    live = probe_all(write=write, fast=fast)
    queue = queue_list(doctrine)
    lb = doctrine.get("loopback_authority") or {}
    doc = {
        "ok": bool(live.get("ok")),
        "schema": "field-github-resilience-panel/v1",
        "title": doctrine.get("title"),
        "updated": _utc(),
        "boss": "hostess7",
        "probe": live,
        "loopback_authority": lb,
        "authority": live.get("authority"),
        "degraded_ok": live.get("degraded_ok"),
        "github_push_ready": live.get("github_push_ready"),
        "publish_queue": {
            "pending": queue.get("pending", 0),
            "entries": len(queue.get("entries") or []),
            "path": str(_queue_path(doctrine)),
        },
        "api": "/api/field-github-resilience",
        "pages_fallback": doctrine.get("pages_fallback_origin"),
        "fast": fast,
    }
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(panel(write=False, fast=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("probe", "fast"):
        print(json.dumps(probe_all(fast=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "panel":
        print(json.dumps(panel(write=True, fast=False), ensure_ascii=False, indent=2))
        return 0
    if cmd == "enqueue" and len(sys.argv) > 2:
        payload = json.loads(sys.argv[2]) if sys.argv[2].startswith("{") else {}
        if not payload:
            return 1
        print(json.dumps(enqueue_publish(**payload), ensure_ascii=False, indent=2))
        return 0
    if cmd == "flush":
        dry = "--dry" in sys.argv
        print(json.dumps(flush_queue(dry=dry), ensure_ascii=False, indent=2))
        return 0
    if cmd == "queue":
        print(json.dumps(queue_list(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-github-resilience.py [panel|json|probe|enqueue JSON|flush|queue]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())