#!/usr/bin/env pythong
"""Truth DNS table hygiene — clean (safe) vs clear (destructive, requires i-know)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-dns-table-clean-doctrine.json"
PANEL = STATE / "field-dns-table-clean-panel.json"
CLEAN_SIGNAL = STATE / "field-dns-clean.signal"
CLEAR_SIGNAL = STATE / "field-dns-clear.signal"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(ts: str) -> float:
    try:
        return datetime.strptime(str(ts).strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return 0.0


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


def _tail_lines(path: Path, keep: int) -> tuple[int, int]:
    if not path.is_file() or keep < 1:
        return 0, 0
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return 0, 0
    before = len(lines)
    if before <= keep:
        return before, 0
    kept = lines[-keep:]
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return before, before - len(kept)


def _truncate(path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        return True
    except OSError:
        return False


def _remove(path: Path) -> bool:
    try:
        if path.is_file():
            path.unlink()
            return True
        if path.is_dir():
            shutil.rmtree(path)
            return True
    except OSError:
        pass
    return False


def _run_json(py_rel: str, args: list[str], *, timeout: int = 20) -> dict[str, Any]:
    py = INSTALL / py_rel
    if not py.is_file():
        return {"ok": False, "error": "missing", "path": str(py_rel)}
    try:
        proc = subprocess.run(
            [os.environ.get("PYTHON", "python3"), str(py), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
    except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
        pass
    return {"ok": False}


def _i_know_confirmed() -> bool:
    return os.environ.get("I_KNOW_DNS_CLEAR", "").strip().lower() in ("1", "yes", "on", "true")


def _expire_shard_probes(directory: Path, *, ttl_sec: int) -> int:
    if not directory.is_dir():
        return 0
    now = time.time()
    removed = 0
    for fp in directory.glob("*.json"):
        try:
            doc = _load(fp, {})
            updated = str(doc.get("updated") or "")
            if updated and now - _parse_ts(updated) <= ttl_sec:
                continue
            if fp.unlink():
                removed += 1
        except OSError:
            continue
    return removed


def _expire_probe_panels(paths: list[str], *, ttl_sec: int) -> int:
    now = time.time()
    removed = 0
    for rel in paths:
        path = STATE / str(rel)
        if not path.is_file():
            continue
        try:
            doc = _load(path, {})
            updated = str(doc.get("updated") or doc.get("ts") or "")
            if updated and now - _parse_ts(updated) <= ttl_sec:
                continue
            if path.unlink():
                removed += 1
        except OSError:
            continue
    return removed


def _policy_theirs(doc: dict[str, Any], *, flush_stub: bool) -> list[dict[str, Any]]:
    clean = doc.get("clean") or {}
    theirs = doc.get("theirs") or {}
    stub = str(theirs.get("stub_witness") or "127.0.0.53")
    rows: list[dict[str, Any]] = []
    dns_sh = INSTALL / "lib" / "field-dns.sh"
    if not dns_sh.is_file():
        return rows

    if clean.get("enforce_resolv", True):
        try:
            proc = subprocess.run(
                ["bash", "-c", f'source "{dns_sh}" && nexus_field_dns_enforce_resolv && nexus_field_dns_enforce_cycle'],
                capture_output=True,
                text=True,
                timeout=25,
                check=False,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            rows.append({"action": "enforce_resolv", "ok": proc.returncode == 0, "destructive": False})
        except (OSError, subprocess.TimeoutExpired):
            rows.append({"action": "enforce_resolv", "ok": False, "destructive": False})

    if clean.get("reaffirm_foreign_block", True):
        try:
            proc = subprocess.run(
                ["bash", "-c", f'source "{dns_sh}" && nexus_field_dns_local_capture'],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            rows.append({"action": "foreign_block", "ok": proc.returncode == 0, "destructive": False})
        except (OSError, subprocess.TimeoutExpired):
            rows.append({"action": "foreign_block", "ok": False, "destructive": False})

    if flush_stub:
        for cmd in (["resolvectl", "flush-caches"], ["resolvectl", "flush-caches", stub], ["systemd-resolve", "--flush-caches"]):
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=8, check=False)
                rows.append({"action": "flush_stub", "cmd": " ".join(cmd), "ok": proc.returncode == 0, "destructive": True})
                if proc.returncode == 0:
                    break
            except (OSError, subprocess.TimeoutExpired):
                rows.append({"action": "flush_stub", "cmd": " ".join(cmd), "ok": False, "destructive": True})

    return rows


def _rebuild_panels(doc: dict[str, Any]) -> list[str]:
    rebuilt: list[str] = []
    for py_rel in doc.get("rebuild_after") or []:
        rel = str(py_rel)
        cmd = "build" if rel.endswith("field-dns.py") or rel.endswith("field-dhcp.py") else "panel"
        if rel.endswith("dns-service-takeover.py"):
            cmd = "evaluate"
        _run_json(rel, [cmd])
        rebuilt.append(f"{rel}:{cmd}")
    if (doc.get("clean") or {}).get("rescan_drift", True):
        _run_json("lib/field-dns-drift-threat.py", ["scan"])
        rebuilt.append("lib/field-dns-drift-threat.py:scan")
    return rebuilt


def clean_tables() -> dict[str, Any]:
    """Safe hygiene — expire stale rows, reconcile policy, rebuild panels. Does not wipe."""
    doc = _load(DOCTRINE, {})
    cfg = doc.get("clean") or {}
    paths = doc.get("paths") or {}
    actions: list[dict[str, Any]] = []

    for rel, keep_key in (
        (paths.get("query_log"), "query_log_keep_lines"),
        (paths.get("cache_hints"), "cache_hints_keep_lines"),
    ):
        if not rel:
            continue
        keep = int(cfg.get(keep_key) or (500 if keep_key == "query_log_keep_lines" else 200))
        before, dropped = _tail_lines(STATE / str(rel), keep)
        actions.append({"target": str(rel), "action": "tail_keep", "kept": min(before, keep), "dropped": dropped, "destructive": False})

    keep_events = int(cfg.get("dhcp_events_keep_lines") or 100)
    before, dropped = _tail_lines(STATE / "field-dhcp-events.jsonl", keep_events)
    actions.append({"target": "field-dhcp-events.jsonl", "action": "tail_keep", "dropped": dropped, "destructive": False})

    shard_dir = STATE / str(paths.get("shard_probes_dir") or "field-github-shard-probes")
    expired = _expire_shard_probes(shard_dir, ttl_sec=int(cfg.get("expire_shard_ttl_sec") or 600))
    actions.append({"target": shard_dir.name, "action": "expire_stale", "removed": expired, "destructive": False})

    expired_panels = _expire_probe_panels(
        list(paths.get("probe_panels") or []),
        ttl_sec=int(cfg.get("expire_probe_panel_ttl_sec") or 900),
    )
    actions.append({"target": "probe_panels", "action": "expire_stale", "removed": expired_panels, "destructive": False})

    theirs = _policy_theirs(doc, flush_stub=bool(cfg.get("flush_stub_cache", False)))
    rebuilt = _rebuild_panels(doc) if cfg.get("rebuild_panels", True) else []

    out = {
        "schema": "field-dns-table-clean/v1",
        "mode": "clean",
        "ts": _utc(),
        "ok": True,
        "note": "Clean ≠ clear — stale rows expired, authority reconciled, nothing blindly wiped.",
        "actions": actions,
        "theirs": theirs,
        "rebuilt": rebuilt,
    }
    _save(PANEL, out)
    return out


def clear_tables(*, i_know: bool = False, dhcp_leases: bool = False) -> dict[str, Any]:
    """Destructive wipe — requires explicit I_KNOW_DNS_CLEAR=1 or --i-know."""
    doc = _load(DOCTRINE, {})
    cfg = doc.get("clear") or {}
    paths = doc.get("paths") or {}
    if cfg.get("requires_i_know", True) and not (i_know or _i_know_confirmed()):
        return {
            "schema": "field-dns-table-clean/v1",
            "mode": "clear",
            "ok": False,
            "error": "clear_requires_i_know",
            "hint": "Destructive wipe blocked. Export I_KNOW_DNS_CLEAR=1 or pass --i-know only if you know what you are doing.",
        }

    actions: list[dict[str, Any]] = []

    if cfg.get("flush_in_memory_cache", True):
        try:
            CLEAR_SIGNAL.write_text(_utc() + "\n", encoding="utf-8")
            actions.append({"target": "field-dns-clear.signal", "action": "signal_full_cache_clear", "destructive": True})
        except OSError:
            actions.append({"target": "field-dns-clear.signal", "action": "signal_full_cache_clear", "ok": False, "destructive": True})

    if cfg.get("truncate_logs", True):
        for rel in (paths.get("query_log"), paths.get("cache_hints"), "field-dhcp-events.jsonl"):
            if not rel:
                continue
            ok = _truncate(STATE / str(rel))
            actions.append({"target": str(rel), "action": "truncate", "ok": ok, "destructive": True})

    if cfg.get("remove_shard_probes", True):
        shard_dir = STATE / str(paths.get("shard_probes_dir") or "field-github-shard-probes")
        n = 0
        if shard_dir.is_dir():
            for fp in shard_dir.glob("*.json"):
                if _remove(fp):
                    n += 1
        actions.append({"target": shard_dir.name, "action": "remove_all", "count": n, "destructive": True})

    if cfg.get("remove_probe_panels", True):
        for rel in paths.get("probe_panels") or []:
            ok = _remove(STATE / str(rel))
            actions.append({"target": str(rel), "action": "remove", "ok": ok, "destructive": True})

    if dhcp_leases or cfg.get("dhcp_leases", False):
        ok = _remove(STATE / "field-dhcp-leases.json")
        actions.append({"target": "field-dhcp-leases.json", "action": "remove", "ok": ok, "destructive": True})

    theirs = _policy_theirs(doc, flush_stub=bool(cfg.get("flush_stub_cache", True)))
    rebuilt = _rebuild_panels(doc)

    out = {
        "schema": "field-dns-table-clean/v1",
        "mode": "clear",
        "ts": _utc(),
        "ok": True,
        "warning": "Destructive clear completed — tables wiped.",
        "actions": actions,
        "theirs": theirs,
        "rebuilt": rebuilt,
    }
    _save(PANEL, out)
    return out


def main() -> int:
    import sys

    args = sys.argv[1:]
    i_know = "--i-know" in args
    dhcp = "--dhcp-leases" in args
    cmd = next((a for a in args if not a.startswith("-")), "clean")
    if cmd == "clean":
        print(json.dumps(clean_tables(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "clear":
        print(json.dumps(clear_tables(i_know=i_know, dhcp_leases=dhcp), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("panel", "json", "status"):
        if PANEL.is_file():
            print(PANEL.read_text(encoding="utf-8"))
        else:
            print(json.dumps({"schema": "field-dns-table-clean-panel/v1", "ok": True, "never_run": True}, ensure_ascii=False))
        return 0
    print(json.dumps({
        "usage": "field-dns-table-clean.py [clean|clear|panel]",
        "note": "clean = safe hygiene; clear = wipe (requires --i-know or I_KNOW_DNS_CLEAR=1)",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())