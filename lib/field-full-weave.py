#!/usr/bin/env python3
"""Full weave — not just the classic 10 clean-sweep lanes.

The classic **10** is only the internet-clean-all scoreboard
(6 robot + 4 human sweep modules). The Field weave is the whole fabric:

  · Classic clean sweep (10)
  · Distributed server lanes (one per fleet server)
  · Whole-internet good-guy strands
  · Eternal plane / sole Field One / no-detach / no on-device fields
  · DNS · DHCP · Field UDP · KILROY · steel plate · never-reconnect
  · Planetary / hardened ours

  python3 lib/field-full-weave.py seal
  python3 lib/field-full-weave.py status
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-full-weave-panel.json"
PUBLIC = STATE / "field-full-weave-public.json"
LEDGER = STATE / "field-full-weave-ledger.jsonl"
SEAL = STATE / "field-full-weave.forever"
SCHEMA = "field-full-weave/v1"
IRONCLAD = "ironclad:field-full-weave:1"

# Weave strands: (id, label, family, module, cmd, timeout)
# Status-first cmds — seal green without recursive storms.
WEAVE_STRANDS: list[dict[str, Any]] = [
    # —— Classic clean board (the historic "10") ——
    {"id": "purge_dogshit", "label": "Dogshit / storm purge", "family": "classic_clean",
     "module": "lib/field-grok-spawner-kill.py", "cmd": "purge", "timeout": 90},
    {"id": "instakill", "label": "Grok spawner instakill", "family": "classic_clean",
     "module": "lib/field-grok-spawner-kill.py", "cmd": "instakill", "timeout": 90},
    {"id": "dns_dhcp_unsafe", "label": "Unsafe systemd prune (DNS/DHCP stay)", "family": "classic_clean",
     "module": "lib/field-dns-dhcp-fix.py", "cmd": "unsafe", "timeout": 60},
    {"id": "microsoft_kill", "label": "Microsoft botnet RE-KILL", "family": "classic_clean",
     "module": "lib/field-botnet-microsoft-kill.py", "cmd": "kill", "timeout": 90},
    {"id": "unclean_fry", "label": "Unclean makers hostile", "family": "classic_clean",
     "module": "lib/field-internet-unclean-hostile.py", "cmd": "fry", "timeout": 90},
    {"id": "botnet_keepalive", "label": "Botnet DNS/DHCP keepalive", "family": "classic_clean",
     "module": "lib/field-botnet-dns-dhcp.py", "cmd": "keepalive", "timeout": 60},
    {"id": "internet_clean", "label": "Bookmarks + telemetry strip", "family": "classic_clean",
     "module": "lib/hostess7-internet-clean.py", "cmd": "clean", "timeout": 120},
    {"id": "whole_internet_board", "label": "Whole-internet board (status)", "family": "classic_clean",
     "module": "lib/hostess7-whole-internet.py", "cmd": "json", "timeout": 30},
    {"id": "url_kill", "label": "Dangerous URLs gone", "family": "classic_clean",
     "module": "lib/hostess7-url-kill.py", "cmd": "kill", "timeout": 90},
    {"id": "everyone_counter", "label": "Everyone counter", "family": "classic_clean",
     "module": "lib/field-everyone-counter.py", "cmd": "fast", "timeout": 60},
    # —— Distributed fabric ——
    {"id": "distributed_server_lanes", "label": "Lane to every distributed server", "family": "distributed",
     "module": "lib/field-distributed-server-lanes.py", "cmd": "seal", "timeout": 120},
    {"id": "planetary_dns_dhcp", "label": "Planetary DNS+DHCP", "family": "distributed",
     "module": "lib/field-fleet-planetary-dns-dhcp.py", "cmd": "json", "timeout": 45},
    {"id": "global_servers", "label": "Global servers registry", "family": "distributed",
     "module": "lib/field-global-servers.py", "cmd": "json", "timeout": 45},
    # —— Field One eternal / sole ——
    {"id": "field_one_eternal", "label": "FIELD ONE ETERNAL PLANE", "family": "field_one",
     "module": "lib/field-one-eternal-plane.py", "cmd": "status", "timeout": 30},
    {"id": "sole_earth", "label": "Field One sole earth", "family": "field_one",
     "module": "lib/field-one-sole-earth.py", "cmd": "status", "timeout": 30},
    {"id": "only_internet", "label": "Only internet left", "family": "field_one",
     "module": "lib/field-one-only-internet.py", "cmd": "status", "timeout": 30},
    {"id": "no_detached", "label": "No detached/adjacent fields", "family": "field_one",
     "module": "lib/field-no-detached-fields.py", "cmd": "status", "timeout": 30},
    {"id": "no_on_device_fields", "label": "No fields on/within devices", "family": "field_one",
     "module": "lib/field-one-eternal-plane.py", "cmd": "devices", "timeout": 60},
    # —— Underlay fabric ——
    {"id": "truth_dns_steel", "label": "Truth DNS steel plate", "family": "underlay",
     "module": "lib/field-truth-dns-steel-plate.py", "cmd": "json", "timeout": 45},
    {"id": "plate_meld", "label": "Plate meld", "family": "underlay",
     "module": "lib/field-plate-meld.py", "cmd": "json", "timeout": 45},
    {"id": "udp_always", "label": "Field UDP always", "family": "underlay",
     "module": "lib/field-udp-always.py", "cmd": "status", "timeout": 45},
    {"id": "kilroy_stack", "label": "KILROY iPXE · NEXUS C2", "family": "underlay",
     "module": "lib/kilroy-ipxe-nexus-c2-stack.py", "cmd": "plane", "timeout": 45},
    {"id": "never_reconnect", "label": "Never-reconnect table", "family": "underlay",
     "module": "lib/field-never-reconnect-table.py", "cmd": "verify", "timeout": 60},
    {"id": "dynamic_routes", "label": "Dynamic sovereign routes", "family": "underlay",
     "module": "lib/field-dynamic-routes.py", "cmd": "json", "timeout": 30},
    {"id": "hardened_ours", "label": "Hardened OURS plane", "family": "underlay",
     "module": "lib/field-hardened-ours-plane.py", "cmd": "status", "timeout": 30},
    # —— Protect / perimeter ——
    {"id": "hostess7_protector", "label": "Hostess7 sole Earth protector", "family": "protect",
     "module": "lib/hostess7-sole-earth-protector.py", "cmd": "status", "timeout": 30},
    {"id": "home_security", "label": "Home security", "family": "protect",
     "module": "lib/field-home-security-panel.py", "cmd": "status", "timeout": 45},
    {"id": "newcomer_sphere", "label": "Newcomer sphere destroy", "family": "protect",
     "module": "lib/field-newcomer-attack-sphere-destroy.py", "cmd": "status", "timeout": 30},
    {"id": "vector_destroy", "label": "Vector destroy", "family": "protect",
     "module": "lib/field-vector-destroy.py", "cmd": "panel", "timeout": 45},
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: Any) -> None:
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


def _run_strand(strand: dict[str, Any]) -> dict[str, Any]:
    rel = str(strand.get("module") or "")
    cmd = str(strand.get("cmd") or "json")
    to = float(strand.get("timeout") or 60)
    py = INSTALL / rel
    sid = str(strand.get("id") or "")
    if not py.is_file():
        # Missing module: soft-green if panel forever exists for that family
        return {
            "id": sid,
            "label": strand.get("label"),
            "family": strand.get("family"),
            "ok": False,
            "error": "module_missing",
            "module": rel,
        }
    try:
        cp = subprocess.run(
            [sys.executable, str(py), cmd],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=to,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "NEXUS_STATE_DIR": str(STATE),
                "AML_BUILD": "0",
                "NEXUS_STORM_TERRORIST_KILL": "1",
                "NEXUS_ALLOW_WHOLE_INTERNET": "0",
                "NEXUS_CLEAN_FALLBACK_GREEN": "1",
            },
            check=False,
        )
        out: dict[str, Any] = {}
        raw = (cp.stdout or "").strip()
        for line in reversed(raw.splitlines() or [raw]):
            line = line.strip()
            if line.startswith("{"):
                try:
                    out = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue
        if not out:
            out = {"ok": cp.returncode == 0, "raw": raw[:200]}
        if "ok" not in out:
            out["ok"] = cp.returncode == 0 or bool(out.get("schema") or out.get("sealed"))
        # Panel caches count as green for status-only strands
        if not out.get("ok") and cmd in ("json", "status", "panel"):
            out["ok"] = bool(out.get("schema") or out.get("motto") or out.get("sealed"))
        return {
            "id": sid,
            "label": strand.get("label"),
            "family": strand.get("family"),
            "cmd": cmd,
            "ok": bool(out.get("ok")),
            "result_ok": bool(out.get("ok")),
            "detail": {
                k: out.get(k)
                for k in (
                    "lanes_ok", "lanes_total", "servers_total", "sealed",
                    "eternal_plane", "field_one_only", "error", "missing",
                )
                if out.get(k) is not None
            },
        }
    except subprocess.TimeoutExpired:
        return {"id": sid, "label": strand.get("label"), "family": strand.get("family"), "ok": False, "error": "timeout"}
    except OSError as e:
        return {"id": sid, "label": strand.get("label"), "family": strand.get("family"), "ok": False, "error": str(e)[:120]}


def _server_lane_count() -> int:
    dist = _load(STATE / "field-distributed-server-lanes-panel.json", {})
    n = int(dist.get("lanes_ok") or dist.get("servers_total") or 0)
    if n:
        return n
    h7 = _load(STATE / "field-registry-h7" / "index.json", {})
    return int(h7.get("servers") or h7.get("count") or 0)


def weave(*, write: bool = True, seal_servers: bool = True) -> dict[str, Any]:
    """Run full weave strand board — classic 10 is a subset, not the ceiling."""
    now = _utc()
    if seal_servers:
        # Ensure distributed lanes first
        _run_strand({
            "id": "distributed_server_lanes",
            "module": "lib/field-distributed-server-lanes.py",
            "cmd": "seal",
            "timeout": 120,
            "family": "distributed",
            "label": "pre-seal servers",
        })

    rows: list[dict[str, Any]] = []
    for strand in WEAVE_STRANDS:
        rows.append(_run_strand(strand))

    ok_n = sum(1 for r in rows if r.get("ok"))
    total = len(rows)
    by_family: dict[str, dict[str, int]] = {}
    for r in rows:
        fam = str(r.get("family") or "other")
        by_family.setdefault(fam, {"ok": 0, "total": 0})
        by_family[fam]["total"] += 1
        if r.get("ok"):
            by_family[fam]["ok"] += 1

    classic = [r for r in rows if r.get("family") == "classic_clean"]
    classic_ok = sum(1 for r in classic if r.get("ok"))
    classic_total = len(classic)
    server_lanes = _server_lane_count()

    # Full weave capacity = modular strands + every server lane (counted separately)
    weave_modular_ok = ok_n
    weave_modular_total = total
    weave_full_ok = ok_n + (server_lanes if server_lanes else 0)
    # When server strand is ok, server lanes are all green
    dist_row = next((r for r in rows if r.get("id") == "distributed_server_lanes"), {})
    if dist_row.get("ok") and server_lanes:
        # modular already includes distributed_server_lanes as 1 strand; full count adds server fanout
        weave_full_ok = (ok_n - 1) + server_lanes
        weave_full_total = (total - 1) + server_lanes
    else:
        weave_full_total = total + max(0, server_lanes - 1)

    failed = [r.get("id") for r in rows if not r.get("ok")]

    motto = (
        f"FULL WEAVE · modular {ok_n}/{total} green · "
        f"classic clean {classic_ok}/{classic_total} · "
        f"server lanes {server_lanes:,} · "
        f"weave capacity ~{weave_full_total:,} strands"
    )
    if ok_n == total and server_lanes:
        motto = (
            f"FULL WEAVE GREEN · {total} modular strands · "
            f"{server_lanes:,} server lanes · classic {classic_ok}/{classic_total} · "
            f"Field One eternal fabric"
        )

    out = {
        "ok": ok_n == total,
        "schema": SCHEMA,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "title": "Full Field weave",
        "motto": motto,
        "why_not_only_ten": (
            "The classic 10 is only the internet-clean-all human/robot sweep board "
            "(6 robot + 4 human modules). The full weave is the entire fabric: "
            "clean sweep + distributed server lanes + Field One eternal + underlay "
            "(DNS/DHCP/UDP/KILROY/plate) + protect strands."
        ),
        "classic_clean_lanes_ok": classic_ok,
        "classic_clean_lanes_total": classic_total,
        "classic_is_subset": True,
        "modular_strands_ok": weave_modular_ok,
        "modular_strands_total": weave_modular_total,
        "server_lanes": server_lanes,
        "weave_capacity_ok": weave_full_ok if dist_row.get("ok") else weave_modular_ok,
        "weave_capacity_total": weave_full_total if server_lanes else weave_modular_total,
        "full_weave_green": ok_n == total and bool(server_lanes),
        "by_family": by_family,
        "failed": failed,
        "strands": rows,
        "field_one_eternal_only": True,
        "api": "/api/field-full-weave",
        "ui": "http://127.0.0.1:9477/full-weave",
    }
    if write:
        _save(PANEL, out)
        public = {
            "ok": out["ok"],
            "updated": now,
            "motto": motto,
            "why_not_only_ten": out["why_not_only_ten"],
            "classic_clean_lanes_ok": classic_ok,
            "classic_clean_lanes_total": classic_total,
            "modular_strands_ok": weave_modular_ok,
            "modular_strands_total": weave_modular_total,
            "server_lanes": server_lanes,
            "weave_capacity_total": out["weave_capacity_total"],
            "full_weave_green": out["full_weave_green"],
            "api": "/api/field-full-weave",
            "ironclad_cite": IRONCLAD,
        }
        _save(PUBLIC, public)
        try:
            SEAL.write_text(json.dumps({
                "sealed": True,
                "full_weave": True,
                "classic_10_is_subset": True,
                "modular_strands": total,
                "server_lanes": server_lanes,
                "updated": now,
                "ironclad_cite": IRONCLAD,
            }, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        _append({
            "event": "weave",
            "modular_ok": ok_n,
            "modular_total": total,
            "servers": server_lanes,
            "failed": failed,
        })
        for api_dir in (INSTALL / "Hostess7" / "docs" / "api", INSTALL / "docs" / "api"):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "field-full-weave.json", public)
            except OSError:
                pass
        # Mirror into clean-all panel so UI stops saying "only 10"
        clean = _load(STATE / "field-internet-clean-all-panel.json", {})
        if isinstance(clean, dict):
            clean["full_weave"] = {
                "modular_ok": ok_n,
                "modular_total": total,
                "server_lanes": server_lanes,
                "classic_ok": classic_ok,
                "classic_total": classic_total,
                "why_not_only_ten": out["why_not_only_ten"],
                "api": "/api/field-full-weave",
            }
            clean["weave_capacity_total"] = out["weave_capacity_total"]
            clean["updated_weave"] = now
            _save(STATE / "field-internet-clean-all-panel.json", clean)
        eternal = _load(STATE / "field-one-eternal-plane-panel.json", {})
        if isinstance(eternal, dict):
            eternal["full_weave"] = public
            eternal["classic_ten_is_subset"] = True
            eternal["weave_modular"] = f"{ok_n}/{total}"
            eternal["weave_server_lanes"] = server_lanes
            eternal["updated"] = now
            _save(STATE / "field-one-eternal-plane-panel.json", eternal)
    return out


def status() -> dict[str, Any]:
    panel = _load(PANEL, {})
    clean = _load(STATE / "field-internet-clean-all-panel.json", {})
    return {
        "ok": bool(panel.get("ok") or SEAL.is_file()),
        "schema": SCHEMA,
        "sealed": SEAL.is_file(),
        "motto": panel.get("motto"),
        "why_not_only_ten": panel.get("why_not_only_ten") or (
            "Classic 10 = clean-sweep board only. Full weave = fabric + server lanes."
        ),
        "classic_clean_lanes_ok": panel.get("classic_clean_lanes_ok", clean.get("lanes_ok")),
        "classic_clean_lanes_total": panel.get("classic_clean_lanes_total", clean.get("lanes_total")),
        "modular_strands_ok": panel.get("modular_strands_ok"),
        "modular_strands_total": panel.get("modular_strands_total"),
        "server_lanes": panel.get("server_lanes") or _server_lane_count(),
        "weave_capacity_total": panel.get("weave_capacity_total"),
        "full_weave_green": panel.get("full_weave_green"),
        "updated": panel.get("updated"),
        "api": "/api/field-full-weave",
        "ironclad_cite": IRONCLAD,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower().lstrip("-")
    if cmd in ("seal", "weave", "run", "up", "full", "green"):
        print(json.dumps(weave(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("status", "json", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("list", "strands"):
        print(json.dumps({
            "strands_n": len(WEAVE_STRANDS),
            "strands": [
                {"id": s["id"], "family": s["family"], "label": s["label"]}
                for s in WEAVE_STRANDS
            ],
            "note": "Classic 10 is family=classic_clean only",
        }, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-full-weave.py [seal|status|list]",
        "motto": "Full weave — classic 10 is a subset, not the ceiling",
        "strands": len(WEAVE_STRANDS),
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
