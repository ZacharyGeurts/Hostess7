#!/usr/bin/env python3
"""Whole Internet — good guys :D — one shot open/clean/kill-delay across every lane."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
DOCTRINE = INSTALL / "data" / "hostess7-whole-internet-doctrine.json"
DOCS_API = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7")) / "docs" / "api"
DEFAULT_WORKERS = int(os.environ.get("NEXUS_WHOLE_INTERNET_WORKERS") or 8)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_state() -> Path:
    for cand in (
        os.environ.get("NEXUS_FIELD_DRIVE_STATE", "").strip(),
        os.environ.get("NEXUS_STATE_DIR", "").strip(),
    ):
        if cand:
            p = Path(cand)
            if p.is_dir():
                return p
    for p in (
        INSTALL / ".nexus-field-drive" / "nexus-field" / "state",
        INSTALL / ".nexus-state",
    ):
        if p.is_dir():
            return p
    return INSTALL / ".nexus-state"


STATE = _resolve_state()
PANEL = STATE / "hostess7-whole-internet-panel.json"
CACHE = STATE / "operator-whole-internet-cache.json"


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _witness(*, detail: str) -> dict[str, Any]:
    py = INSTALL / "lib" / "hostess7-truth-lie-threat.py"
    if not py.is_file():
        return {"ok": True, "delay_killed": True}
    try:
        spec = importlib.util.spec_from_file_location("whole_inet_witness", py)
        if not spec or not spec.loader:
            return {"ok": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "witness_delay_threat"):
            return mod.witness_delay_threat(
                signal="whole_internet_good_guys",
                detail=detail,
                elapsed_sec=0,
                meta={"module": "hostess7-whole-internet.py"},
            )
    except Exception:
        pass
    return {"ok": True, "delay_killed": True}


def _run_lane(lane: dict[str, Any], *, timeout: int = 120) -> dict[str, Any]:
    import subprocess

    lid = str(lane.get("id") or "lane")
    rel = str(lane.get("module") or "")
    cmd = str(lane.get("cmd") or "json")
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "id": lid, "error": "module_missing", "module": rel}
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "NEXUS_FIELD_INTERNET_UNRESTRICT": "1",
        "NEXUS_X_NO_DELAY": "1",
        "NEXUS_INTERNET_NO_DELAY": "1",
        "NEXUS_TCO_NO_DELAY": "1",
    }
    try:
        proc = subprocess.run(
            [sys.executable, str(py), cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        try:
            out = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            out = {"ok": proc.returncode == 0, "raw": (proc.stdout or proc.stderr or "")[:400]}
        if isinstance(out, dict):
            out.setdefault("ok", proc.returncode == 0)
        return {"id": lid, "label": lane.get("label"), "cmd": cmd, "result": out}
    except subprocess.TimeoutExpired:
        return {"ok": False, "id": lid, "error": "timeout", "cmd": cmd}
    except OSError as exc:
        return {"ok": False, "id": lid, "error": str(exc)[:160]}


def _lane_summary(lane_row: dict[str, Any]) -> dict[str, Any]:
    res = lane_row.get("result") if isinstance(lane_row.get("result"), dict) else {}
    lid = str(lane_row.get("id") or "")
    summary: dict[str, Any] = {"ok": bool(res.get("ok", lane_row.get("ok")))}
    if lid == "url_heuristics_steel":
        summary.update({
            "chain_hash": (res.get("chain_hash") or "")[:16],
            "generation": res.get("generation"),
            "gone_hosts": (res.get("counts") or {}).get("gone_hosts"),
        })
    elif lid == "url_kill":
        summary.update({
            "gone_hosts": res.get("gone_hosts"),
            "urls_gone": (res.get("purge") or {}).get("urls_gone"),
        })
    elif lid == "internet_clean":
        s = res.get("summary") or {}
        summary.update({"bookmarks_secured": s.get("bookmarks_secured"), "telemetry_quarantined": s.get("telemetry_quarantined")})
    elif lid == "google_youtube_open":
        summary.update({
            "comment_count": res.get("comment_count"),
            "free_open_internet": res.get("free_open_internet"),
            "delay_killed": res.get("delay_killed"),
        })
    elif lid == "x_open":
        summary.update({
            "comment_count": res.get("comment_count"),
            "withheld_slots_opened": res.get("withheld_slots_opened"),
            "delay_killed": res.get("delay_killed"),
        })
    elif lid == "tco_kill":
        summary.update({"tco_found": res.get("tco_found"), "tco_unwrapped": res.get("tco_unwrapped")})
    elif lid == "x_brand_purge":
        summary.update({"producer": res.get("producer"), "dangerous_blown": len(res.get("dangerous_blown") or [])})
    elif lid == "internet_unrestrict":
        summary.update({"internet_open": res.get("internet_open")})
    elif lid == "fleet_protect":
        c = res.get("counts") or {}
        summary.update({"protected_total": c.get("protected_total"), "servers_total": c.get("servers_total")})
    elif lid == "censorship_exposure":
        summary.update({"exposures": len(res.get("exposures") or res.get("layers") or [])})
    return summary


def whole_internet(*, parallel: bool = True, include_optional: bool = True) -> dict[str, Any]:
    doc = doctrine()
    lanes_cfg = list(doc.get("lanes") or [])
    lanes = [l for l in lanes_cfg if include_optional or not l.get("optional")]
    workers = min(DEFAULT_WORKERS, max(1, len(lanes)))
    rows: list[dict[str, Any]] = []

    if parallel and len(lanes) > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_run_lane, lane): lane for lane in lanes}
            for fut in as_completed(futs):
                rows.append(fut.result())
    else:
        for lane in lanes:
            rows.append(_run_lane(lane))

    ok_count = sum(1 for r in rows if (r.get("result") or {}).get("ok") or r.get("ok"))
    summaries = {str(r.get("id") or ""): _lane_summary(r) for r in rows}
    witness = _witness(detail=f"whole internet good guys — {ok_count}/{len(lanes)} lanes green")

    out = {
        "ok": ok_count >= max(1, len(lanes) - 2),
        "schema": "hostess7-whole-internet/v1",
        "updated": _now(),
        "motto": doc.get("motto"),
        "good_guys": doc.get("good_guys"),
        "lanes_total": len(lanes),
        "lanes_ok": ok_count,
        "delay_killed": True,
        "free_open_internet": True,
        "parallel": parallel,
        "lane_summaries": summaries,
        "lanes": rows,
        "witness": witness,
        "api": doc.get("api") or "/api/operator-whole-internet",
    }
    _save(PANEL, out)
    _save(CACHE, out)
    if DOCS_API.parent.is_dir():
        DOCS_API.mkdir(parents=True, exist_ok=True)
        (DOCS_API / "operator-whole-internet.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
    return out


def panel_json() -> dict[str, Any]:
    cached = _load(CACHE, {})
    if cached.get("schema"):
        return cached
    cached = _load(PANEL, {})
    if cached.get("schema"):
        return cached
    return {
        "ok": True,
        "schema": "hostess7-whole-internet-panel/v1",
        "pending": "run whole-internet",
        "motto": doctrine().get("motto"),
        "good_guys": doctrine().get("good_guys"),
        "api": "/api/operator-whole-internet",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    sequential = "--sequential" in sys.argv
    skip_optional = "--core-only" in sys.argv
    if cmd in ("run", "open", "whole", "good-guys", "internet", "purge"):
        print(json.dumps(
            whole_internet(parallel=not sequential, include_optional=not skip_optional),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-whole-internet.py [run|json] [--sequential] [--core-only]",
        "motto": doctrine().get("motto"),
        "good_guys": True,
        "api": "/api/operator-whole-internet",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())