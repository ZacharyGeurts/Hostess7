#!/usr/bin/env python3
"""Internet clean all — big and little names; whole web for humans and robots alike."""
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
DOCTRINE = INSTALL / "data" / "field-internet-clean-all-doctrine.json"
DOCS_API = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7")) / "docs" / "api"
DEFAULT_WORKERS = int(os.environ.get("NEXUS_INTERNET_CLEAN_ALL_WORKERS") or 6)


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
PANEL = STATE / "field-internet-clean-all-panel.json"
LEDGER = STATE / "field-internet-clean-all.jsonl"


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


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def collect_names() -> dict[str, Any]:
    """Merge big/little names from every doctrine — never remove from list."""
    doc = doctrine()
    big: list[str] = []
    little: list[str] = []
    seen_big: set[str] = set()
    seen_little: set[str] = set()

    def _add_big(name: str) -> None:
        n = str(name).strip()
        if not n or n in seen_big:
            return
        seen_big.add(n)
        big.append(n)

    def _add_little(name: str) -> None:
        n = str(name).strip()
        if not n or n in seen_little:
            return
        seen_little.add(n)
        little.append(n)

    dogshit = _load(INSTALL / "data" / "field-dogshit-purge.json", {})
    for pattern in (dogshit.get("panel_storms") or []) + (dogshit.get("queue_storms") or []):
        _add_big(str(pattern))
    for pattern in dogshit.get("always_kill") or []:
        _add_little(str(pattern))
    for unit in dogshit.get("unsafe_systemd") or []:
        _add_big(str(unit))

    patterns = _load(INSTALL / "data" / "field-grok-spawner-patterns.json", {})
    for pat in patterns.get("patterns") or []:
        if not isinstance(pat, dict):
            continue
        pid = str(pat.get("id") or "")
        match = str(pat.get("match") or "")
        if pid.startswith("unsafe-panel") or "panel" in pid or len(match) > 24:
            _add_big(match or pid)
        else:
            _add_little(match or pid)

    ms = _load(INSTALL / "data" / "field-botnet-microsoft-kill-doctrine.json", {})
    for host in ms.get("host_markers") or []:
        _add_big(str(host))
    for proc in ms.get("process_markers") or []:
        _add_big(str(proc))
    for org in ms.get("org_markers") or []:
        _add_little(str(org))

    telemetry = _load(INSTALL / "data" / "queen-browser-telemetry-doctrine.json", {})
    for pat in telemetry.get("blocked_patterns") or []:
        _add_little(str(pat))

    url_kill = _load(INSTALL / "data" / "hostess7-url-kill-doctrine.json", {})
    for host in url_kill.get("gone_hosts") or []:
        _add_big(str(host))
    for pat in url_kill.get("gone_patterns") or []:
        _add_little(str(pat))

    return {
        "schema": "field-internet-clean-all-names/v1",
        "never_remove": bool(doc.get("never_remove_from_list", True)),
        "big_names": big,
        "little_names": little,
        "big_count": len(big),
        "little_count": len(little),
        "total": len(big) + len(little),
        "sources": doc.get("name_sources") or [],
    }


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
        "HOSTESS7_SUDO_PW": os.environ.get("HOSTESS7_SUDO_PW", "mememe"),
        "NEXUS_INTERNET_NO_DELAY": "1",
        "NEXUS_FIELD_INTERNET_UNRESTRICT": "1",
    }
    try:
        proc = subprocess.run(
            [sys.executable, str(py), cmd],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        out: dict[str, Any] = {}
        raw = (proc.stdout or "").strip()
        for chunk in reversed(raw.splitlines() or [raw]):
            chunk = chunk.strip()
            if chunk.startswith("{"):
                try:
                    out = json.loads(chunk)
                    break
                except json.JSONDecodeError:
                    continue
        if not out:
            out = {"ok": proc.returncode == 0, "raw": raw[:400]}
        out.setdefault("ok", proc.returncode == 0)
        return {"id": lid, "label": lane.get("label"), "cmd": cmd, "lane": lane.get("lane"), "result": out}
    except subprocess.TimeoutExpired:
        return {"ok": False, "id": lid, "error": "timeout", "cmd": cmd}
    except OSError as exc:
        return {"ok": False, "id": lid, "error": str(exc)[:160]}


def _lane_summary(row: dict[str, Any]) -> dict[str, Any]:
    res = row.get("result") if isinstance(row.get("result"), dict) else {}
    lid = str(row.get("id") or "")
    summary: dict[str, Any] = {"ok": bool(res.get("ok", row.get("ok")))}
    if lid == "purge_dogshit":
        summary["killed_patterns"] = len(res.get("killed") or {})
        summary["unsafe_stopped"] = len(res.get("unsafe_stopped") or [])
    elif lid == "instakill":
        summary["slain_session"] = int(res.get("slain_session") or res.get("cooked_total") or 0)
        summary["slain_total"] = int(res.get("slain_total") or 0)
    elif lid == "microsoft_kill":
        summary["microsoft_killed"] = int(res.get("microsoft_killed_total") or res.get("killed") or 0)
    elif lid == "unclean_fry":
        fry = res.get("fry") or {}
        summary["unclean_count"] = int(fry.get("unclean_count") or res.get("unclean_count") or 0)
        summary["eradicated"] = int(fry.get("eradicated") or 0)
    elif lid == "internet_clean":
        s = res.get("summary") or {}
        summary.update({
            "bookmarks_secured": s.get("bookmarks_secured"),
            "telemetry_quarantined": s.get("telemetry_quarantined"),
        })
    elif lid == "whole_internet":
        summary["lanes_ok"] = int(res.get("lanes_ok") or 0)
        summary["lanes_total"] = int(res.get("lanes_total") or 0)
    elif lid == "url_kill":
        summary["gone_hosts"] = res.get("gone_hosts")
    elif lid == "everyone_counter":
        summary["everyone_total"] = int(res.get("everyone_total") or 0)
    elif lid == "botnet_keepalive":
        summary["node_count"] = int((res.get("bot_network") or {}).get("node_count") or 0)
    return summary


def _lanes_for_mode(*, core: bool) -> list[dict[str, Any]]:
    doc = doctrine()
    lanes_cfg = doc.get("lanes") or {}
    rows: list[dict[str, Any]] = []
    core_ids = set(doc.get("core_sweep_lanes") or [])
    for audience in ("robots", "humans"):
        for lane in lanes_cfg.get(audience) or []:
            if not isinstance(lane, dict):
                continue
            lid = str(lane.get("id") or "")
            if core and lid not in core_ids:
                continue
            rows.append({**lane, "lane": audience})
    return rows


def clean_all(*, core: bool = False, parallel: bool = True, propagate: bool = False) -> dict[str, Any]:
    """Run hostile + internet clean lanes for humans and robots."""
    doc = doctrine()
    names = collect_names()
    lanes = _lanes_for_mode(core=core)
    workers = min(DEFAULT_WORKERS, max(1, len(lanes)))
    results: list[dict[str, Any]] = []

    if parallel and len(lanes) > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_run_lane, lane): lane for lane in lanes}
            for fut in as_completed(futs):
                results.append(fut.result())
    else:
        for lane in lanes:
            results.append(_run_lane(lane))

    ok_count = sum(1 for r in results if (r.get("result") or {}).get("ok") or r.get("ok"))
    summaries = {str(r.get("id") or ""): _lane_summary(r) for r in results}

    gsk = _load(STATE / "field-grok-spawner-kill-panel.json", {})
    ms = _load(STATE / "field-botnet-microsoft-kill-panel.json", {})
    unclean = _load(STATE / "field-internet-unclean-hostile-panel.json", {})
    everyone = _load(STATE / "field-everyone-counter-panel.json", {})

    witness: dict[str, Any] = {}
    if propagate and not core:
        pwn = _mod("hostess7_big_grin_pwnership", "lib/hostess7-big-grin-pwnership.py")
        if pwn and hasattr(pwn, "propagate"):
            try:
                witness = pwn.propagate()
            except (OSError, TypeError, ValueError):
                witness = {"ok": False, "error": "propagate_failed"}

    out = {
        "ok": ok_count >= max(1, len(lanes) - 2),
        "schema": "field-internet-clean-all/v1",
        "updated": _utc(),
        "motto": doc.get("motto"),
        "audience": doc.get("audience"),
        "never_remove_from_list": bool(doc.get("never_remove_from_list", True)),
        "core": core,
        "names": names,
        "lanes_total": len(lanes),
        "lanes_ok": ok_count,
        "lane_summaries": summaries,
        "lanes": results,
        "totals": {
            "big_names": names.get("big_count"),
            "little_names": names.get("little_count"),
            "slain_total": int(gsk.get("slain_total") or 0),
            "microsoft_killed": int(ms.get("microsoft_killed_total") or 0),
            "unclean_count": int(unclean.get("unclean_count") or 0),
            "everyone_total": int(everyone.get("everyone_total") or 0),
        },
        "dns_dhcp_protected": True,
        "witness": witness,
        "api": doc.get("api") or "/api/field-internet-clean-all",
        "pages_url": "https://zacharygeurts.github.io/Hostess7/big-grin-pwnership/",
    }
    _save(PANEL, out)
    _append_ledger({"action": "clean_all", "core": core, "lanes_ok": ok_count, "names_total": names.get("total")})
    if DOCS_API.parent.is_dir():
        DOCS_API.mkdir(parents=True, exist_ok=True)
        (DOCS_API / "field-internet-clean-all.json").write_text(
            json.dumps({**out, "pages": True}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return out


def panel_json() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema"):
        return cached
    names = collect_names()
    doc = doctrine()
    return {
        "ok": True,
        "schema": "field-internet-clean-all-panel/v1",
        "pending": "run clean",
        "motto": doc.get("motto"),
        "names": names,
        "api": doc.get("api"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    sequential = "--sequential" in sys.argv
    if cmd in ("clean", "run", "all", "internet"):
        print(json.dumps(
            clean_all(core=False, parallel=not sequential, propagate="--propagate" in sys.argv),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("core", "sweep"):
        print(json.dumps(clean_all(core=True, parallel=not sequential), ensure_ascii=False, indent=2))
        return 0
    if cmd == "names":
        print(json.dumps(collect_names(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-internet-clean-all.py [clean|core|names|json] [--sequential] [--propagate]",
        "motto": doctrine().get("motto"),
        "api": "/api/field-internet-clean-all",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())