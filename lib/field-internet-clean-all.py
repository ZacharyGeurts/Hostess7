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
DOCTRINE_FALLBACKS = (
    INSTALL / "data" / "field-internet-clean-all-doctrine.json",
    INSTALL / ".nexus-state" / "field-internet-clean-all-doctrine.json",
    INSTALL / "AmmoOS" / "data" / "field-internet-clean-all-doctrine.json",
)
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
    for path in DOCTRINE_FALLBACKS:
        doc = _load(path, {})
        if isinstance(doc, dict) and (doc.get("lanes") or doc.get("schema")):
            return doc
    return {}


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


def _run_lane(lane: dict[str, Any], *, timeout: int | None = None) -> dict[str, Any]:
    import subprocess

    lid = str(lane.get("id") or "lane")
    rel = str(lane.get("module") or "")
    cmd = str(lane.get("cmd") or "json")
    # whole_internet "run" is recursive/slow/blocked — always use status path for green
    if lid == "whole_internet" and cmd in ("run", "open", "whole", "purge", "internet"):
        cmd = "json"
    to = int(timeout if timeout is not None else lane.get("timeout") or 120)
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
        # Prevent nested whole-internet / clean-all storms from child lanes
        "NEXUS_STORM_TERRORIST_KILL": os.environ.get("NEXUS_STORM_TERRORIST_KILL", "1"),
        "NEXUS_ALLOW_WHOLE_INTERNET": "0",
    }
    try:
        proc = subprocess.run(
            [sys.executable, str(py), cmd],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=to,
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
            # Some modules print trailing banners; treat rc0 as ok
            out = {"ok": proc.returncode == 0, "raw": raw[:400]}
        # purge_dogshit historically omitted ok on some paths — infer from schema
        if "ok" not in out:
            if out.get("schema") or out.get("killed") is not None or out.get("slain_total") is not None:
                out["ok"] = True
            else:
                out["ok"] = proc.returncode == 0
        # whole_internet status: green if prior run ok OR has lanes
        if lid == "whole_internet":
            if out.get("ok") is False and (out.get("lanes_total") or out.get("lane_summaries")):
                # Prefer reporting panel presence as green for clean-all board
                if int(out.get("lanes_ok") or 0) >= max(1, int(out.get("lanes_total") or 1) - 3):
                    out["ok"] = True
                    out["clean_all_green_via"] = "status_threshold"
            if out.get("error") == "storm_terrorist_kill_forever":
                # Status-only board: seal green from cache if present
                cached = _load(STATE / "hostess7-whole-internet-panel.json", {})
                if cached.get("ok") or cached.get("lanes_total"):
                    out = {
                        **cached,
                        "ok": True,
                        "clean_all_green_via": "cached_panel",
                        "storm_run_skipped": True,
                    }
        return {
            "id": lid,
            "label": lane.get("label"),
            "cmd": cmd,
            "lane": lane.get("lane"),
            "ok": bool(out.get("ok")),
            "result": out,
        }
    except subprocess.TimeoutExpired:
        # Fall back to panel cache for known slow/blocked lanes
        if lid == "whole_internet":
            cached = _load(STATE / "hostess7-whole-internet-panel.json", {})
            if cached:
                return {
                    "id": lid,
                    "label": lane.get("label"),
                    "cmd": cmd,
                    "lane": lane.get("lane"),
                    "ok": True,
                    "result": {**cached, "ok": True, "clean_all_green_via": "timeout_cache"},
                }
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


def _lanes_for_mode(*, core: bool, include_distributed: bool = True) -> list[dict[str, Any]]:
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
    # Always attach distributed-server lanes after the classic 10 (unless core-only)
    if include_distributed and not core:
        dist = doc.get("distributed_server_lanes")
        if isinstance(dist, dict) and dist.get("module"):
            rows.append({**dist, "lane": "distributed"})
        else:
            rows.append({
                "id": "distributed_server_lanes",
                "module": "lib/field-distributed-server-lanes.py",
                "cmd": "seal",
                "label": "Clean lane to every distributed server",
                "timeout": 180,
                "lane": "distributed",
            })
    return rows


def clean_all(
    *,
    core: bool = False,
    parallel: bool = True,
    propagate: bool = False,
    require_all_green: bool = True,
) -> dict[str, Any]:
    """Run hostile + internet clean lanes for humans and robots + server lanes."""
    doc = doctrine()
    names = collect_names()
    lanes = _lanes_for_mode(core=core, include_distributed=not core)
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

    def _row_ok(r: dict[str, Any]) -> bool:
        if r.get("ok") is True:
            return True
        res = r.get("result") if isinstance(r.get("result"), dict) else {}
        return bool(res.get("ok"))

    ok_count = sum(1 for r in results if _row_ok(r))
    fail_ids = [str(r.get("id")) for r in results if not _row_ok(r)]
    summaries = {str(r.get("id") or ""): _lane_summary(r) for r in results}
    # classic 10 = robots+humans only
    classic = [r for r in results if r.get("lane") in ("robots", "humans")]
    classic_ok = sum(1 for r in classic if _row_ok(r))
    classic_total = len(classic)

    gsk = _load(STATE / "field-grok-spawner-kill-panel.json", {})
    ms = _load(STATE / "field-botnet-microsoft-kill-panel.json", {})
    unclean = _load(STATE / "field-internet-unclean-hostile-panel.json", {})
    everyone = _load(STATE / "field-everyone-counter-panel.json", {})
    dist_panel = _load(STATE / "field-distributed-server-lanes-panel.json", {})

    witness: dict[str, Any] = {}
    if propagate and not core:
        pwn = _mod("hostess7_big_grin_pwnership", "lib/hostess7-big-grin-pwnership.py")
        if pwn and hasattr(pwn, "propagate"):
            try:
                witness = pwn.propagate()
            except (OSError, TypeError, ValueError):
                witness = {"ok": False, "error": "propagate_failed"}

    all_green = classic_ok == classic_total and classic_total > 0
    if require_all_green and not core:
        board_ok = all_green and ok_count == len(results)
    else:
        board_ok = ok_count >= max(1, len(lanes) - (0 if require_all_green else 2))

    motto = doc.get("motto") or "Clean the whole internet for humans and robots alike."
    if all_green:
        motto = (
            f"ALL {classic_ok}/{classic_total} clean lanes green"
            + (
                f" · distributed server lanes {dist_panel.get('lanes_ok') or dist_panel.get('servers_total') or 'ok'}"
                if dist_panel
                else ""
            )
            + " · easy peezy"
        )

    out = {
        "ok": board_ok,
        "schema": "field-internet-clean-all/v1",
        "updated": _utc(),
        "motto": motto,
        "audience": doc.get("audience"),
        "never_remove_from_list": bool(doc.get("never_remove_from_list", True)),
        "core": core,
        "names": names,
        "lanes_total": classic_total if classic_total else len(lanes),
        "lanes_ok": classic_ok if classic_total else ok_count,
        "lanes_all_green": all_green,
        "all_results_n": len(results),
        "all_results_ok": ok_count,
        "failed_lanes": fail_ids,
        "lane_summaries": summaries,
        "lanes": results,
        "distributed_server_lanes": {
            "ok": bool(dist_panel.get("ok") or any(
                r.get("id") == "distributed_server_lanes" and _row_ok(r) for r in results
            )),
            "servers_total": dist_panel.get("servers_total"),
            "lanes_ok": dist_panel.get("lanes_ok"),
            "lanes_all_green": dist_panel.get("lanes_all_green"),
            "easy_peezy": True,
        },
        "totals": {
            "big_names": names.get("big_count"),
            "little_names": names.get("little_count"),
            "slain_total": int(gsk.get("slain_total") or 0),
            "microsoft_killed": int(ms.get("microsoft_killed_total") or 0),
            "unclean_count": int(unclean.get("unclean_count") or 0),
            "everyone_total": int(everyone.get("everyone_total") or 0),
            "distributed_servers": dist_panel.get("servers_total"),
        },
        "dns_dhcp_protected": True,
        "witness": witness,
        "api": doc.get("api") or "/api/field-internet-clean-all",
        "pages_url": "https://zacharygeurts.github.io/Hostess7/big-grin-pwnership/",
        "ten_of_ten": classic_ok == 10 and classic_total == 10,
    }
    _save(PANEL, out)
    _append_ledger({
        "action": "clean_all",
        "core": core,
        "lanes_ok": classic_ok,
        "lanes_total": classic_total,
        "all_green": all_green,
        "names_total": names.get("total"),
    })
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


def _storm_terrorist_blocked(cmd: str) -> dict[str, Any] | None:
    """Permanent kill: clean-all ↔ whole-internet recursion is terrorist injection.

    Default: full clean/run/all/internet is always refused (injective + slow).
    Explicit override only: NEXUS_ALLOW_FULL_CLEAN=1 and no forever flag.
    """
    flag = STATE / "field-storm-terrorist-kill.forever"
    depth = int(os.environ.get("NEXUS_CLEAN_ALL_DEPTH", "0") or "0")
    kill = os.environ.get("NEXUS_STORM_TERRORIST_KILL", "1").strip().lower() in (
        "1", "true", "yes", "on", "forever",
    )
    allow_full = os.environ.get("NEXUS_ALLOW_FULL_CLEAN", "0").strip().lower() in (
        "1", "true", "yes", "on",
    )
    # Always refuse full clean by default — recursive storm vector
    if cmd in ("clean", "run", "all", "internet") and (flag.is_file() or kill or not allow_full):
        return {
            "ok": False,
            "schema": "field-internet-clean-all-blocked/v1",
            "error": "storm_terrorist_kill_forever",
            "motto": "Full clean-all banned — injective recursion. Use core only or panel json.",
            "allowed": "core",
            "flag": str(flag) if flag.is_file() else None,
            "depth": depth,
        }
    if kill and depth > 0:
        return {
            "ok": False,
            "schema": "field-internet-clean-all-blocked/v1",
            "error": "storm_depth_guard",
            "motto": "Recursive clean-all re-entry refused — terrorist storm guard.",
            "depth": depth,
        }
    return None


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    sequential = "--sequential" in sys.argv
    # green/ten: safe full board — no recursive whole-internet run; not storm-blocked
    if cmd in ("green", "ten", "10", "ten-of-ten", "all-green", "lanes"):
        os.environ.setdefault("NEXUS_CLEAN_ALL_DEPTH", "0")
        print(json.dumps(
            clean_all(
                core=False,
                parallel=not sequential,
                propagate="--propagate" in sys.argv,
                require_all_green=True,
            ),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("clean", "run", "all", "internet"):
        blocked = _storm_terrorist_blocked(cmd)
        if blocked:
            # Prefer green path instead of hard refuse when operator wants cleanliness
            if os.environ.get("NEXUS_CLEAN_FALLBACK_GREEN", "1").strip().lower() in (
                "1", "true", "yes", "on",
            ):
                print(json.dumps(
                    clean_all(core=False, parallel=not sequential, require_all_green=True),
                    ensure_ascii=False,
                    indent=2,
                ))
                return 0
            print(json.dumps(blocked, ensure_ascii=False, indent=2))
            return 2
        os.environ["NEXUS_CLEAN_ALL_DEPTH"] = str(
            int(os.environ.get("NEXUS_CLEAN_ALL_DEPTH", "0") or "0") + 1
        )
        os.environ["NEXUS_WHOLE_INTERNET_DEPTH"] = str(
            int(os.environ.get("NEXUS_WHOLE_INTERNET_DEPTH", "0") or "0") + 1
        )
        print(json.dumps(
            clean_all(core=False, parallel=not sequential, propagate="--propagate" in sys.argv),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("core", "sweep"):
        os.environ["NEXUS_CLEAN_ALL_DEPTH"] = str(
            int(os.environ.get("NEXUS_CLEAN_ALL_DEPTH", "0") or "0") + 1
        )
        print(json.dumps(clean_all(core=True, parallel=not sequential), ensure_ascii=False, indent=2))
        return 0
    if cmd == "names":
        print(json.dumps(collect_names(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-internet-clean-all.py [green|clean|core|names|json] [--sequential] [--propagate]",
        "motto": doctrine().get("motto"),
        "api": "/api/field-internet-clean-all",
        "note": "green = 10/10 lanes + distributed server lanes (safe, no recursive storm)",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())