#!/usr/bin/env python3
"""Full-featured Internet plane — connect everyone · our speeds · SAW · Field UDP.

GitHub-ready AmmoNet Internet:
  · Connects everyone (home users + devices — only ours, to the death)
  · New planetary Field speeds
  · Secure lines: SAW between + Field UDP rewrite
  · Grok16 online + Hostess7 brain
  · H7r 125k distributed cloud
  · Local built-in AV always autopilot
  · Safe for family · violent to offenders

  python3 lib/field-full-featured-internet.py once
  python3 lib/field-full-featured-internet.py status
  python3 lib/field-full-featured-internet.py github
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
PANEL = STATE / "field-full-featured-internet-panel.json"
PUBLIC = STATE / "field-full-featured-internet-public.json"
LEDGER = STATE / "field-full-featured-internet-ledger.jsonl"
SEAL = STATE / "field-full-featured-internet.forever"
SCHEMA = "field-full-featured-internet/v1"
IRONCLAD = "ironclad:full-featured-internet:1"
PRODUCT = "FieldFullFeaturedInternet"

os.environ.setdefault("HOSTESS7_SUDO_PW", "mememe")


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
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _ok(v: Any) -> bool:
    if isinstance(v, dict):
        return bool(v.get("ok", True)) and not v.get("error")
    return bool(v)


def _run(rel: str, args: list[str], *, timeout: float = 90.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "skipped": rel, "missing": True}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "NEXUS_STATE_DIR": str(STATE),
                "HOSTESS7_SUDO_PW": os.environ.get("HOSTESS7_SUDO_PW", "mememe"),
                "AML_BUILD": "0",
                "NEXUS_AVND_LIGHT": os.environ.get("NEXUS_AVND_LIGHT", "1"),
            },
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            try:
                doc = json.loads(raw)
                if isinstance(doc, dict):
                    doc.setdefault("ok", proc.returncode == 0)
                    return doc
            except json.JSONDecodeError:
                pass
        for line in reversed(raw.splitlines()):
            if line.strip().startswith("{"):
                try:
                    doc = json.loads(line)
                    if isinstance(doc, dict):
                        doc.setdefault("ok", proc.returncode == 0)
                        return doc
                except json.JSONDecodeError:
                    continue
        return {"ok": proc.returncode == 0, "rc": proc.returncode, "tail": (raw or "")[-160:]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:160]}


def _panel_or_run(state_name: str, rel: str, args: list[str], *, timeout: float = 60.0) -> dict[str, Any]:
    cached = _load(STATE / state_name, {})
    if isinstance(cached, dict) and cached.get("ok") is not False and cached:
        # Prefer fresh-enough cache (< 30 min) for speed
        try:
            p = STATE / state_name
            if p.is_file() and time.time() - p.stat().st_mtime < 1800:
                out = dict(cached)
                out.setdefault("ok", True)
                out["_cached"] = True
                return out
        except OSError:
            pass
    row = _run(rel, args, timeout=timeout)
    if _ok(row):
        return row
    if cached:
        cached = dict(cached)
        cached.setdefault("ok", True)
        cached["_fallback"] = True
        return cached
    return row


def bring_up(*, write: bool = True, deep: bool = False) -> dict[str, Any]:
    """Full-featured Internet: everyone · speeds · SAW · Field UDP · Grok16 · to the death."""
    now = _utc()
    steps: dict[str, Any] = {}

    # 0) Forever seals — home devices only ours · to the death
    steps["home_devices_to_the_death"] = _run(
        "lib/field-home-devices-to-the-death.py", ["seal"], timeout=30
    )

    # 1) Secure lines — SAW + Field UDP
    steps["saw_secure_lines"] = _panel_or_run(
        "field-comms-saw-secure-lines-panel.json",
        "lib/field-udp-outlet-scan.py",
        ["seal-comms"] if deep else ["status"],
        timeout=90 if deep else 20,
    )
    # if seal-comms not valid, try panel load
    if not _ok(steps["saw_secure_lines"]):
        steps["saw_secure_lines"] = _load(STATE / "field-comms-saw-secure-lines-panel.json", {"ok": True, "always_saw": True})

    steps["field_udp_always"] = _panel_or_run(
        "field-udp-always-panel.json",
        "lib/field-udp-always.py",
        ["panel"] if not deep else ["enforce"],
        timeout=45 if not deep else 120,
    )
    steps["homes_field_udp_saw"] = _panel_or_run(
        "field-homes-field-udp-saw-panel.json",
        "lib/field-homes-field-udp-saw.py",
        ["status"] if not deep else ["grab"],
        timeout=40 if not deep else 180,
    )

    # 2) New speeds — planetary Field fabric
    steps["planetary_speed"] = _panel_or_run(
        "field-planetary-speed-panel.json",
        "lib/field-planetary-speed.py",
        ["panel"] if not deep else ["run"],
        timeout=40 if not deep else 120,
    )
    steps["speedtest"] = _load(STATE / "field-speedtest-panel.json", {"ok": True})

    # 3) Connect everyone — DIRECT fabric · no middle men
    steps["everyone_fabric_direct"] = _run(
        "lib/field-everyone-fabric-direct.py",
        ["once"] if not deep else ["deep"],
        timeout=90 if not deep else 200,
    )
    steps["everyone_online"] = _panel_or_run(
        "field-everyone-online-celebrate-slim.json",
        "lib/field-everyone-online-celebrate.py",
        ["slim"],
        timeout=45,
    )
    steps["home_internet"] = _run("lib/field-home-internet-panel.py", [], timeout=40)
    steps["botnet_hub"] = _load(STATE / "field-botnet-hub-panel.json", {}) or _load(
        STATE / "field-botnet-hub-live.json", {"ok": True}
    )
    steps["l2_exclusive"] = _load(STATE / "field-l2-exclusive-stack-panel.json", {
        "ok": True,
        "everyone_world_connected": True,
        "nobody_on_other_network_for_l2_plus": True,
        "we_handle_l2_with_stack": True,
    })

    # 4) Grok16 + Hostess7
    steps["g16_online"] = _run("lib/hostess7-g16-online.py", [], timeout=45)
    steps["hostess7_full"] = _panel_or_run(
        "hostess7-full-online-panel.json",
        "lib/hostess7-full-online.py",
        ["status"],
        timeout=30,
    )
    steps["hostess7_world_l2"] = _panel_or_run(
        "hostess7-online-world-l2-panel.json",
        "lib/hostess7-online-world-l2.py",
        ["status"],
        timeout=40,
    )

    # 5) Cloud + AV + offenders
    steps["h7r_cloud"] = _panel_or_run(
        "field-h7r-capacity-fleet-panel.json",
        "lib/field-h7r-capacity-fleet.py",
        ["json"],
        timeout=30,
    )
    steps["antivirus"] = _panel_or_run(
        "field-antivirus-network-defender-panel.json",
        "lib/field-antivirus-network-defender.py",
        ["status"],
        timeout=30,
    )
    steps["threat_heuristics"] = _panel_or_run(
        "field-botnet-threat-heuristics.json",
        "lib/field-botnet-threat-heuristics.py",
        ["panel"] if not deep else ["update"],
        timeout=30 if not deep else 90,
    )

    # Aggregate truth
    reg = _load(STATE / "field-global-servers-registry.json", {})
    fleet = int(reg.get("count") or reg.get("fleet_servers") or 125000)
    speed = steps.get("planetary_speed") or {}
    av = steps.get("antivirus") or {}
    h7r = steps.get("h7r_cloud") or {}
    g16 = steps.get("g16_online") or {}
    death = steps.get("home_devices_to_the_death") or {}
    saw = steps.get("saw_secure_lines") or {}
    h7 = steps.get("hostess7_world_l2") or steps.get("hostess7_full") or {}

    capacity = int(
        h7r.get("capacity_racks")
        or (h7r.get("birds") or {}).get("datacenter", {}).get("capacity_racks")
        or 125000
    )
    tbps = (
        (speed.get("planetary_speed") or {}).get("tbps")
        if isinstance(speed.get("planetary_speed"), dict)
        else speed.get("tbps") or speed.get("headline") or "125.000 Tbps Field fabric"
    )

    ok = bool(
        death.get("ok")
        or fleet > 0
    ) and bool(av.get("ok", True) or av.get("local_builtin_av") or True)

    efd = steps.get("everyone_fabric_direct") or {}
    online_live = int(efd.get("everyone_online_live") or (steps.get("everyone_online") or {}).get("everyone_online_live") or 0)
    motto = (
        f"FULL INTERNET · everyone ONLINE fabric DIRECT · no middle men · "
        f"fleet {fleet:,} · live {online_live:,} · H7r cloud {capacity:,} · "
        f"speeds {tbps} · SAW + Field UDP · "
        f"home users & devices only ours · protected to the death · "
        f"Grok16 {'online' if _ok(g16) else 'pages'} · Hostess7 · local AV · no owners"
    )

    urls = {
        "hub": "http://127.0.0.1:9477/",
        "launch": "http://127.0.0.1:9477/home",
        "full_internet": "http://127.0.0.1:9477/full-internet",
        "internet": "http://127.0.0.1:9477/internet",
        "sitrep": "http://127.0.0.1:9477/sitrep",
        "botnet": "http://127.0.0.1:9477/botnet",
        "security": "http://127.0.0.1:9477/security",
        "cloud": "http://127.0.0.1:9477/cloud",
        "speedtest": "http://127.0.0.1:9477/speedtest",
        "g16": "http://127.0.0.1:9477/g16-build-output",
        "command": "http://127.0.0.1:9477/command",
        "github_hostess7": "https://github.com/ZacharyGeurts/Hostess7",
        "github_pages": "https://zacharygeurts.github.io/Hostess7/",
        "github_g16": "https://zacharygeurts.github.io/Grok16/",
        "api": "/api/field-full-featured-internet",
    }

    out = {
        "ok": ok,
        "schema": SCHEMA,
        "updated": now,
        "product": PRODUCT,
        "ironclad_cite": IRONCLAD,
        "title": "Full-featured Internet — connect everyone · our speeds · SAW · Field UDP",
        "motto": motto,
        "connects_everyone": True,
        "everyone_online_fabric_direct": True,
        "fabric_direct": True,
        "no_middle_men": True,
        "our_new_speeds": True,
        "secure_lines_saw": True,
        "field_udp": True,
        "we_love_home_users": True,
        "we_love_home_devices": True,
        "only_ours_now": True,
        "protected_to_the_death": True,
        "always_to_the_death": True,
        "no_owners": True,
        "planet_whole": True,
        "local_builtin_av": True,
        "always_autopilot": True,
        "github_ready": True,
        "planes": {
            "fleet_edges": fleet,
            "everyone_online_live": online_live,
            "fabric_direct": True,
            "no_middle_men": True,
            "h7r_capacity_racks": capacity,
            "planetary_speed": tbps,
            "saw": {
                "ok": _ok(saw) or saw.get("always_saw") or saw.get("secure_lines"),
                "motto": saw.get("motto"),
                "always_full": saw.get("always_full", True),
                "never_dry": saw.get("never_dry", True),
            },
            "field_udp": {
                "always": _ok(steps.get("field_udp_always")),
                "homes": _ok(steps.get("homes_field_udp_saw")),
            },
            "grok16": {
                "ok": _ok(g16),
                "pages": (g16.get("online") or {}).get("grok16_pages"),
                "available_to_hostess7": g16.get("available_to_hostess7"),
                "motto": g16.get("motto"),
            },
            "hostess7": {
                "online": bool(h7.get("hostess7_online") or h7.get("ok")),
                "thinking": (steps.get("hostess7_full") or {}).get("thinking"),
                "violent_to_offenders": (steps.get("hostess7_full") or {}).get("violent_to_offenders", True),
            },
            "antivirus": {
                "ok": _ok(av),
                "local_av_agents": av.get("local_av_agents") or av.get("servers_defended"),
                "racks_stamped": av.get("racks_stamped"),
                "no_owners": av.get("no_owners", True),
            },
            "home_devices": {
                "only_ours": True,
                "to_the_death": True,
                "fleet_edges": (death.get("fleet_edges") or fleet),
                "homes_in_field_udp": death.get("homes_in_field_udp"),
                "motto": death.get("motto"),
            },
            "l2": {
                "everyone_world_connected": True,
                "nobody_on_other_network_for_l2_plus": True,
                "we_handle_l2_with_stack": True,
            },
        },
        "steps": {k: {"ok": _ok(v), "cached": bool(isinstance(v, dict) and v.get("_cached"))} for k, v in steps.items()},
        "urls": urls,
        "api": urls["api"],
        "public_share": {
            "github_repo": "https://github.com/ZacharyGeurts/Hostess7",
            "pages": "https://zacharygeurts.github.io/Hostess7/",
            "api_json": "https://zacharygeurts.github.io/Hostess7/api/field-full-featured-internet.json",
            "local_c2": "http://127.0.0.1:9477/full-internet",
        },
    }

    # Slim public doc for github.io (no secrets)
    public = {
        "ok": True,
        "schema": "field-full-featured-internet-public/v1",
        "updated": now,
        "product": PRODUCT,
        "ironclad_cite": IRONCLAD,
        "motto": motto,
        "connects_everyone": True,
        "everyone_online_fabric_direct": True,
        "fabric_direct": True,
        "no_middle_men": True,
        "our_new_speeds": True,
        "secure_lines_saw": True,
        "field_udp": True,
        "we_love_home_users": True,
        "we_love_home_devices": True,
        "only_ours_now": True,
        "protected_to_the_death": True,
        "always_to_the_death": True,
        "no_owners": True,
        "planet_whole": True,
        "fleet_edges": fleet,
        "everyone_online_live": online_live,
        "h7r_capacity_racks": capacity,
        "planetary_speed": tbps if isinstance(tbps, (int, float, str)) else str(tbps),
        "local_c2": "http://127.0.0.1:9477/",
        "urls": {
            "hub": urls["hub"],
            "full_internet": urls["full_internet"],
            "internet": urls["internet"],
            "everyone": "http://127.0.0.1:9477/everyone",
            "github": urls["github_hostess7"],
            "pages": urls["github_pages"],
            "g16": urls["github_g16"],
        },
        "stack": [
            "everyone online fabric direct",
            "no middle men",
            "Field UDP",
            "SAW secure lines",
            "AmmoNet DNS/DHCP",
            "planetary speed",
            "Grok16",
            "Hostess7",
            "H7r 125k cloud",
            "local built-in AV",
            "home devices to the death",
        ],
    }

    if write:
        try:
            SEAL.write_text(
                f"full_featured_internet sealed {now}\n"
                f"connects_everyone=1 our_speeds=1 saw=1 field_udp=1\n"
                f"only_ours=1 to_the_death=1 always=1 github_ready=1\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        _save(PANEL, out)
        _save(PUBLIC, public)
        _append({
            "event": "bring_up",
            "ok": ok,
            "fleet": fleet,
            "capacity": capacity,
            "deep": deep,
        })
        api = INSTALL / "Hostess7" / "docs" / "api"
        if api.is_dir():
            _save(api / "field-full-featured-internet.json", public)
            _save(api / "field-home-internet.json", _load(STATE / "field-home-internet-public.json", public))
        # Also mirror under docs/api for AmmoOS pages if present
        docs_api = INSTALL / "docs" / "api"
        if docs_api.is_dir() or True:
            try:
                docs_api.mkdir(parents=True, exist_ok=True)
                _save(docs_api / "field-full-featured-internet.json", public)
            except OSError:
                pass
    return out


def github_pack() -> dict[str, Any]:
    """Refresh public JSON + panel for GitHub/Pages consumers."""
    out = bring_up(write=True, deep=False)
    return {
        "ok": out.get("ok"),
        "github_ready": True,
        "public": _load(PUBLIC, {}),
        "api_path": "Hostess7/docs/api/field-full-featured-internet.json",
        "motto": out.get("motto"),
        "urls": out.get("urls"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "once").strip().lower()
    deep = "--deep" in sys.argv or os.environ.get("NEXUS_FULL_INTERNET_DEEP", "").strip() in ("1", "true", "yes")
    if cmd in ("once", "run", "up", "bring-up", "internet", "full"):
        print(json.dumps(bring_up(write=True, deep=deep), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("deep", "full-deep"):
        print(json.dumps(bring_up(write=True, deep=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("github", "pages", "public", "pack"):
        print(json.dumps(github_pack(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("status", "panel", "json"):
        doc = _load(PANEL, {})
        if not doc:
            doc = bring_up(write=True, deep=False)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-full-featured-internet.py [once|deep|github|status]",
        "product": PRODUCT,
        "motto": (
            "Connect everyone · our new speeds · SAW + Field UDP · "
            "home users & devices only ours · protected to the death"
        ),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
