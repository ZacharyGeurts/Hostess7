#!/usr/bin/env python3
"""Big Grin Pwnership — memorial websites for equipment that went down + propagate."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
DOCTRINE = INSTALL / "data" / "hostess7-big-grin-pwnership-doctrine.json"
H7_DOCS = INSTALL / "Hostess7" / "docs"
DOCS_API = H7_DOCS / "api"
SITE_ROOT = H7_DOCS / "big-grin-pwnership"
ASSETS = H7_DOCS / "assets" / "big-grin-pwnership"
PANEL_ASSETS = INSTALL / "panel" / "assets" / "big-grin-pwnership"


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
        INSTALL / ".nexus-state-ci",
    ):
        if p.is_dir():
            return p
    return INSTALL / ".nexus-state"


STATE = _resolve_state()
PANEL = STATE / "hostess7-big-grin-pwnership-panel.json"
REGISTRY = STATE / "hostess7-big-grin-pwnership-registry.json"
LEDGER = STATE / "hostess7-big-grin-pwnership-ledger.jsonl"


def _now() -> str:
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
            fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


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


def _why_index() -> dict[str, dict[str, Any]]:
    doc = doctrine()
    return {str(r["id"]): r for r in doc.get("why_we_did", {}).get("reasons") or [] if r.get("id")}


def discover_down() -> list[dict[str, Any]]:
    """Merge doctrine seed, equipment room, and path witnesses."""
    doc = doctrine()
    brand = doc.get("brand") or {}
    why_idx = _why_index()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for seed in doc.get("equipment_seed") or []:
        if not isinstance(seed, dict) or not seed.get("id"):
            continue
        eid = str(seed["id"])
        seen.add(eid)
        path = str(seed.get("path") or "")
        exists = Path(path).exists() if path else None
        why_id = str(seed.get("why_id") or "")
        why = why_idx.get(why_id, {})
        rows.append({
            **seed,
            "path_exists": exists,
            "witness": "down" if seed.get("burned") or seed.get("status") in ("down", "blocked") else str(seed.get("status") or "retired"),
            "why": {
                "id": why_id,
                "headline": why.get("headline"),
                "detail": why.get("detail"),
                "sources": why.get("sources") or [],
            },
            "page_url": f"{brand.get('pages_hub', '/Hostess7/big-grin-pwnership/')}equipment/{eid}.html",
        })

    equip = _mod("lib/equipment-room-field.py", "equip_room")
    if equip and hasattr(equip, "panel_json"):
        try:
            panel = equip.panel_json()
            for leg in panel.get("legacy_dns_equipment") or []:
                if not isinstance(leg, dict):
                    continue
                eid = str(leg.get("id") or "")
                if not eid or eid in seen:
                    continue
                seen.add(eid)
                why = why_idx.get("truth_resolver_supersedes", {})
                rows.append({
                    "id": eid,
                    "name": f"{leg.get('vendor', 'Legacy')} — {leg.get('role', 'DNS')}",
                    "vendor": leg.get("vendor"),
                    "status": "retired",
                    "role": leg.get("role"),
                    "era": leg.get("era"),
                    "rfc": leg.get("rfc"),
                    "notes": leg.get("notes"),
                    "replacement": "NEXUS Truth Resolver — 127.0.0.1:53",
                    "why_id": "truth_resolver_supersedes",
                    "witness": "retired",
                    "why": {
                        "id": "truth_resolver_supersedes",
                        "headline": why.get("headline"),
                        "detail": why.get("detail"),
                        "sources": why.get("sources") or [],
                    },
                    "page_url": f"{brand.get('pages_hub', '/Hostess7/big-grin-pwnership/')}equipment/{eid}.html",
                })
        except Exception:
            pass

    qemu = _mod("lib/field-zachub-qemu-racks.py", "qemu_racks")
    if qemu and hasattr(qemu, "burn_stale_team_qemu"):
        try:
            burn = qemu.burn_stale_team_qemu(dry_run=True)
            for b in burn.get("burned") or []:
                raw_path = str(b.get("path") or "")
                if not raw_path:
                    continue
                slug = raw_path.replace("/", "-").strip("-").lower()[:48]
                eid = f"burn-{slug}"
                if eid in seen:
                    continue
                seen.add(eid)
                why = why_idx.get("stale_team_qemu", {})
                rows.append({
                    "id": eid,
                    "name": f"Burn witness — {Path(raw_path).name}",
                    "path": raw_path,
                    "status": "down",
                    "burned": True,
                    "path_exists": Path(raw_path).exists(),
                    "replacement": "GrokLab/deploy/qemu-racks",
                    "why_id": "stale_team_qemu",
                    "witness": "burn_scheduled" if b.get("dry") else "burned",
                    "why": {
                        "id": "stale_team_qemu",
                        "headline": why.get("headline"),
                        "detail": b.get("reason") or why.get("detail"),
                        "sources": why.get("sources") or [],
                    },
                    "page_url": f"{brand.get('pages_hub', '/Hostess7/big-grin-pwnership/')}equipment/{eid}.html",
                })
        except Exception:
            pass

    return rows


def _read_jsonl(path: Path, limit: int = 500) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return rows


def discover_kills() -> dict[str, Any]:
    """Kill + RE-KILL witness — append-only, never remove from list."""
    doc = doctrine()
    why_idx = _why_index()
    patterns_doc = _load(INSTALL / "data" / "field-grok-spawner-patterns.json", {})
    dogshit_doc = _load(INSTALL / "data" / "field-dogshit-purge.json", {})
    gsk_panel = _load(STATE / "field-grok-spawner-kill-panel.json", {})
    ms_panel = _load(STATE / "field-botnet-microsoft-kill-panel.json", {})
    registry_rows = _read_jsonl(STATE / "field-dogshit-kill-registry.jsonl", 800)
    gsk_ledger = _read_jsonl(STATE / "field-grok-spawner-kill-ledger.jsonl", 400)

    kill_counts: dict[str, int] = {}
    for row in registry_rows:
        key = str(row.get("pattern") or row.get("kind") or "unknown")
        kill_counts[key] = kill_counts.get(key, 0) + 1
    for row in gsk_ledger:
        cooked = row.get("cooked") or {}
        if isinstance(cooked, dict):
            for k, n in cooked.items():
                if int(n or 0) > 0:
                    kill_counts[str(k)] = kill_counts.get(str(k), 0) + int(n)

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add_entry(eid: str, name: str, why_id: str, *, kills: int = 0, status: str = "killed") -> None:
        if eid in seen:
            return
        seen.add(eid)
        why = why_idx.get(why_id, {})
        entries.append({
            "id": eid,
            "name": name,
            "status": status,
            "kill_count": kills,
            "rekill": kills > 1,
            "why_id": why_id,
            "why": {
                "id": why_id,
                "headline": why.get("headline"),
                "detail": why.get("detail"),
                "sources": why.get("sources") or [],
            },
            "witness": "killed",
            "page_url": f"{(doc.get('brand') or {}).get('pages_hub', '/Hostess7/big-grin-pwnership/')}kills/{eid}.html",
        })

    for pat in patterns_doc.get("patterns") or []:
        if not isinstance(pat, dict):
            continue
        pid = str(pat.get("id") or "")
        match = str(pat.get("match") or "")[:48]
        if not pid:
            continue
        why_id = "spawner_instakill" if "grok" in pid or "interference" in pid else "dogshit_purge"
        if pid.startswith("unsafe-panel") or pid.startswith("unsafe-"):
            why_id = "dogshit_purge"
        _add_entry(
            f"kill-{pid}",
            str(pat.get("reason") or match),
            why_id,
            kills=kill_counts.get(pid, 0) + kill_counts.get(match, 0),
        )

    for pattern in (dogshit_doc.get("panel_storms") or []) + (dogshit_doc.get("queue_storms") or []) + (dogshit_doc.get("always_kill") or []):
        slug = str(pattern).replace("/", "-").replace(" ", "-").replace(".", "-").lower()[:56]
        eid = f"dogshit-{slug}"
        why_id = "dogshit_purge" if "queue" not in str(pattern) and "publish" not in str(pattern) else "dogshit_purge"
        _add_entry(eid, str(pattern), why_id, kills=kill_counts.get(str(pattern), 0), status="permanent_list")

    _add_entry(
        "grok-spawn-killer-total",
        f"GrokSpawnKiller — {int(gsk_panel.get('slain_total') or 0)} spawners slain",
        "spawner_instakill",
        kills=int(gsk_panel.get("slain_total") or 0),
        status="active",
    )
    if int(ms_panel.get("microsoft_killed_total") or 0) > 0:
        _add_entry(
            "microsoft-botnet-kill",
            f"Microsoft botnet strikes — {ms_panel.get('microsoft_killed_total')} total",
            "microsoft_botnet_kill",
            kills=int(ms_panel.get("microsoft_killed_total") or 0),
        )

    hostile_path = STATE / "field-hostile.tsv"
    hostile_count = 0
    if hostile_path.is_file():
        try:
            hostile_count = max(0, len(hostile_path.read_text(encoding="utf-8").splitlines()) - 1)
        except OSError:
            pass
    if hostile_count:
        _add_entry("field-hostile-registry", f"Hostile registry — {hostile_count} IPs struck", "microsoft_botnet_kill", kills=hostile_count)

    clean_all = _load(STATE / "field-internet-clean-all-panel.json", {})
    clean_names = clean_all.get("names") or {}
    if not clean_names:
        try:
            ica = _mod("field_internet_clean_all", "lib/field-internet-clean-all.py")
            if ica and hasattr(ica, "collect_names"):
                clean_names = ica.collect_names()
        except (OSError, TypeError, ValueError):
            clean_names = {}
    big_n = int(clean_names.get("big_count") or len(clean_names.get("big_names") or []))
    little_n = int(clean_names.get("little_count") or len(clean_names.get("little_names") or []))
    if big_n or little_n:
        _add_entry(
            "internet-clean-all-names",
            f"Internet clean all — {big_n} big + {little_n} little names (permanent list)",
            "internet_clean_all",
            kills=big_n + little_n,
            status="permanent_list",
        )
    totals = clean_all.get("totals") or {}
    if clean_all.get("schema"):
        _add_entry(
            "internet-clean-all-sweep",
            f"Whole internet clean — {int(clean_all.get('lanes_ok') or 0)}/{int(clean_all.get('lanes_total') or 0)} lanes green",
            "internet_clean_all",
            kills=int(totals.get("slain_total") or 0) + int(totals.get("microsoft_killed") or 0),
            status="active" if clean_all.get("ok") else "sweep",
        )

    eradicated_counts: dict[str, int] = {}
    for row in _read_jsonl(STATE / "dns-threat-eradicated.jsonl", 400):
        client = str(row.get("client") or "")
        if client:
            eradicated_counts[client] = eradicated_counts.get(client, 0) + 1

    cg = _load(STATE / "field-dns-dhcp-collision-guard-panel.json", {})
    threats = list(cg.get("foreign_server_threats") or [])
    for row in cg.get("collisions") or []:
        if isinstance(row, dict) and row.get("kind", "").startswith("foreign"):
            threats.append(row)
    for threat in threats:
        if not isinstance(threat, dict):
            continue
        key = (
            threat.get("nameserver")
            or threat.get("server")
            or threat.get("bind")
            or threat.get("addr")
        )
        if not key:
            continue
        slug = str(key).replace(".", "-").replace(":", "-").replace("/", "-")[:48]
        vector = str(threat.get("vector") or threat.get("kind") or "FOREIGN_DNS_SERVER")
        kills = eradicated_counts.get(str(key), 0) or 1
        _add_entry(
            f"world-dns-dhcp-{slug}",
            f"World DNS/DHCP hook — {key} ({vector})",
            "world_dns_dhcp_hook",
            kills=kills,
            status="eradicated" if kills else "threat",
        )
    enforce = cg.get("enforce") or {}
    eradicated_n = int(enforce.get("threats_eradicated") or 0)
    if threats or eradicated_n:
        _add_entry(
            "world-dns-dhcp-collision-guard",
            f"Collision guard — {len(threats)} foreign hooks, {eradicated_n} eradicated on sight",
            "world_dns_dhcp_hook",
            kills=max(eradicated_n, len(threats)),
            status="active" if cg.get("ok") else "sweep",
        )

    return {
        "schema": "hostess7-big-grin-pwnership-kills/v1",
        "updated": _now(),
        "never_remove": bool((doc.get("kill_registry") or {}).get("never_remove", True)),
        "slain_total": int(gsk_panel.get("slain_total") or 0),
        "registry_events": len(registry_rows),
        "kill_list_count": len(entries),
        "entries": entries,
        "motto": "Killed and RE-KILLed — why is public; list never shrinks.",
    }


def _internet_clean_witness_html() -> str:
    clean = _load(STATE / "field-internet-clean-all-panel.json", {})
    names = clean.get("names") or {}
    if not names:
        try:
            ica = _mod("field_internet_clean_all", "lib/field-internet-clean-all.py")
            if ica and hasattr(ica, "collect_names"):
                names = ica.collect_names()
        except (OSError, TypeError, ValueError):
            names = {}
    big = int(names.get("big_count") or len(names.get("big_names") or []))
    little = int(names.get("little_count") or len(names.get("little_names") or []))
    totals = clean.get("totals") or {}
    motto = escape(str(clean.get("motto") or "Big and little names — clean the whole internet for humans and robots alike."))
    return f"""<section class="bgp-section">
  <h2>Internet clean all — humans &amp; robots</h2>
  <p class="bgp-meta" style="margin:0 0 14px">{motto}</p>
  <dl class="bgp-meta">
    <dt>Big names (hosts, panels, storms)</dt><dd><strong>{big}</strong> on permanent list</dd>
    <dt>Little names (interference, telemetry, patterns)</dt><dd><strong>{little}</strong> on permanent list</dd>
    <dt>Spawners slain</dt><dd>{int(totals.get('slain_total') or 0)}</dd>
    <dt>Microsoft RE-KILL</dt><dd>{int(totals.get('microsoft_killed') or 0)}</dd>
    <dt>Everyone total</dt><dd>{int(totals.get('everyone_total') or 0)} humans + bots</dd>
  </dl>
  <div class="bgp-actions">
    <a class="bgp-btn" href="/api/field-internet-clean-all">Clean-all API</a>
    <a class="bgp-btn bgp-btn--gold" href="/Hostess7/grok-spawn-killer/">GrokSpawnKiller</a>
  </div>
</section>
"""


def _kill_witness_html(kills: dict[str, Any]) -> str:
    rows = ""
    for e in (kills.get("entries") or [])[:48]:
        name = escape(str(e.get("name") or ""))
        cnt = int(e.get("kill_count") or 0)
        status = escape(str(e.get("status") or "killed"))
        why_head = escape(str((e.get("why") or {}).get("headline") or ""))
        rekill = " · RE-KILL" if e.get("rekill") or cnt > 1 else ""
        rows += f"""<tr>
  <td><code>{name}</code></td>
  <td>{cnt if cnt else "—"}</td>
  <td><span class="bgp-status bgp-status--down">{status}</span></td>
  <td>{why_head}{rekill}</td>
</tr>\n"""
    total = int(kills.get("slain_total") or 0)
    reg = int(kills.get("registry_events") or 0)
    return f"""<section class="bgp-section">
  <h2>Killed &amp; RE-KILL witness ({int(kills.get('kill_list_count') or 0)} on permanent list)</h2>
  <p class="bgp-meta" style="margin:0 0 14px">GrokSpawnKiller slain total: <strong>{total}</strong> · registry events: <strong>{reg}</strong> · never remove from list.</p>
  <table class="bgp-kill-table">
    <thead><tr><th>Name</th><th>Kills</th><th>Status</th><th>Why</th></tr></thead>
    <tbody>{rows or '<tr><td colspan="4">Witness pending first purge.</td></tr>'}</tbody>
  </table>
</section>
"""


def why_we_did() -> dict[str, Any]:
    doc = doctrine()
    w = doc.get("why_we_did") or {}
    equipment = discover_down()
    return {
        "schema": "hostess7-big-grin-pwnership-why/v1",
        "updated": _now(),
        "summary": w.get("summary"),
        "reasons": w.get("reasons") or [],
        "equipment_count": len(equipment),
        "down_count": len([e for e in equipment if e.get("witness") in ("down", "burned", "burn_scheduled", "blocked")]),
        "retired_count": len([e for e in equipment if e.get("witness") == "retired"]),
    }


def look_pwnership() -> dict[str, Any]:
    doc = doctrine()
    lp = dict(doc.get("look_pwnership") or {})
    brand = doc.get("brand") or {}
    assets = lp.get("assets") or {}
    resolved: dict[str, str] = {}
    for key, rel in assets.items():
        for base in (ASSETS, PANEL_ASSETS):
            fname = Path(str(rel)).name
            candidate = base / fname
            if candidate.is_file():
                resolved[key] = f"/Hostess7/assets/big-grin-pwnership/{fname}"
                break
    return {
        "schema": "hostess7-look-pwnership/v1",
        "updated": _now(),
        "brand": brand.get("name"),
        "look_pwnership": brand.get("look_pwnership"),
        "palette": lp.get("palette"),
        "typography": lp.get("typography"),
        "note": lp.get("note"),
        "assets": resolved,
        "operator": {
            "handle": brand.get("display_name"),
            "x": brand.get("x_url"),
            "github": brand.get("github_url"),
        },
    }


def _site_css() -> str:
    lp = look_pwnership()
    pal = lp.get("palette") or {}
    bg = pal.get("bg", "#020403")
    emerald = pal.get("emerald", "#1a9b6e")
    rose = pal.get("rose_gold", "#c9a66b")
    witness = pal.get("witness", "#9ad4ff")
    down = pal.get("down_red", "#8b2e2e")
    return f"""/* Big Grin Pwnership — Look Pwnership */
:root {{
  --bgp-bg: {bg};
  --bgp-emerald: {emerald};
  --bgp-rose: {rose};
  --bgp-witness: {witness};
  --bgp-down: {down};
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: system-ui, "Segoe UI", sans-serif;
  background: var(--bgp-bg);
  color: #e8efe9;
  line-height: 1.55;
}}
.bgp-root {{ max-width: 1100px; margin: 0 auto; padding: 24px 20px 64px; }}
.bgp-hero {{
  position: relative;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(26,155,110,0.35);
  margin-bottom: 28px;
}}
.bgp-hero img {{ width: 100%; display: block; max-height: 320px; object-fit: cover; }}
.bgp-hero-overlay {{
  position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 30%, rgba(2,4,3,0.92) 100%);
  display: flex; flex-direction: column; justify-content: flex-end;
  padding: 20px 24px;
}}
.bgp-eyebrow {{ color: var(--bgp-rose); font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase; margin: 0 0 6px; }}
.bgp-title {{ margin: 0; font-size: clamp(1.6rem, 4vw, 2.4rem); color: #fff; }}
.bgp-tagline {{ margin: 8px 0 0; color: #9ab0a4; max-width: 52ch; }}
.bgp-badge-row {{ display: flex; align-items: center; gap: 16px; margin: 20px 0; }}
.bgp-badge {{ width: 72px; height: 72px; border-radius: 50%; border: 2px solid var(--bgp-emerald); object-fit: cover; }}
.bgp-look-label {{ font-size: 0.85rem; color: var(--bgp-witness); }}
.bgp-actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0 28px; }}
.bgp-btn {{
  display: inline-block; padding: 10px 16px; border-radius: 8px;
  border: 1px solid rgba(26,155,110,0.5); color: #fff; text-decoration: none;
  background: rgba(26,155,110,0.12); font-size: 0.9rem;
}}
.bgp-btn--gold {{ border-color: var(--bgp-rose); background: rgba(201,166,107,0.15); }}
.bgp-btn:hover {{ filter: brightness(1.15); }}
.bgp-section {{ margin: 32px 0; }}
.bgp-section h2 {{ color: var(--bgp-emerald); font-size: 1.15rem; margin: 0 0 14px; border-bottom: 1px solid rgba(26,155,110,0.25); padding-bottom: 8px; }}
.bgp-why {{ background: rgba(26,155,110,0.06); border-left: 3px solid var(--bgp-emerald); padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 14px; }}
.bgp-why h3 {{ margin: 0 0 6px; font-size: 1rem; color: #fff; }}
.bgp-why p {{ margin: 0; color: #a8bdb0; font-size: 0.92rem; }}
.bgp-why-sources {{ font-size: 0.78rem; color: #6a8074; margin-top: 8px; }}
.bgp-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }}
.bgp-card {{
  border: 1px solid rgba(26,155,110,0.22); border-radius: 10px;
  padding: 14px 16px; background: rgba(0,0,0,0.35);
  text-decoration: none; color: inherit; display: block;
}}
.bgp-card:hover {{ border-color: var(--bgp-emerald); }}
.bgp-card h3 {{ margin: 0 0 6px; font-size: 0.98rem; }}
.bgp-status {{
  display: inline-block; font-size: 0.72rem; text-transform: uppercase;
  letter-spacing: 0.08em; padding: 2px 8px; border-radius: 4px; margin-bottom: 8px;
}}
.bgp-status--down {{ background: rgba(139,46,46,0.35); color: #f0a0a0; }}
.bgp-status--retired {{ background: rgba(201,166,107,0.2); color: var(--bgp-rose); }}
.bgp-status--blocked {{ background: rgba(139,46,46,0.5); color: #ffb0b0; }}
.bgp-card p {{ margin: 0; font-size: 0.85rem; color: #8fa898; }}
.bgp-detail {{ margin: 20px 0; }}
.bgp-meta {{ font-size: 0.85rem; color: #7a9488; }}
.bgp-meta dt {{ color: var(--bgp-witness); margin-top: 10px; }}
.bgp-meta dd {{ margin: 4px 0 0; }}
.bgp-footer {{
  margin-top: 48px; padding-top: 20px; border-top: 1px solid rgba(26,155,110,0.2);
  font-size: 0.82rem; color: #6d8578;
}}
.bgp-footer a {{ color: var(--bgp-witness); }}
.bgp-kill-table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
.bgp-kill-table th {{ text-align: left; color: var(--bgp-rose); padding: 8px 10px; border-bottom: 1px solid rgba(26,155,110,0.25); }}
.bgp-kill-table td {{ padding: 8px 10px; border-bottom: 1px solid rgba(26,155,110,0.12); color: #a8bdb0; vertical-align: top; }}
.bgp-kill-table code {{ font-size: 0.78rem; color: var(--bgp-witness); }}
"""


def _head_block(title: str, *, extra_css: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en" class="nexus-military-v8">
<head>
  <base href="/Hostess7/" />
  <script src="/Hostess7/pages-base.js"></script>
  <script src="/Hostess7/api-shim.js"></script>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <link rel="stylesheet" href="/Hostess7/big-grin-pwnership/pwnership.css" />
  {extra_css}
</head>
<body>
"""


def _footer_block(brand: dict[str, Any]) -> str:
    x = escape(str(brand.get("x_url") or "https://x.com/ZacharyGeurts"))
    gh = escape(str(brand.get("github_url") or "https://github.com/ZacharyGeurts"))
    return f"""  <footer class="bgp-footer">
    <p><strong>Big Grin Pwnership</strong> — Look Pwnership by {escape(str(brand.get('display_name') or 'BIG GRIN'))} (@{escape(str(brand.get('operator') or 'ZacharyGeurts'))})</p>
    <p>
      <a href="{x}" rel="noopener">X / @ZacharyGeurts</a> ·
      <a href="{gh}" rel="noopener">GitHub / ZacharyGeurts</a> ·
      <a href="/Hostess7/brain.html">Hostess 7 Brain</a>
    </p>
  </footer>
</body>
</html>
"""


def _equipment_card(eq: dict[str, Any]) -> str:
    eid = escape(str(eq.get("id") or ""))
    name = escape(str(eq.get("name") or eid))
    witness = str(eq.get("witness") or eq.get("status") or "retired")
    status_cls = "down" if witness in ("down", "burned", "burn_scheduled") else ("blocked" if witness == "blocked" else "retired")
    why_head = escape(str((eq.get("why") or {}).get("headline") or ""))
    return f"""<a class="bgp-card" href="/Hostess7/big-grin-pwnership/equipment/{eid}.html">
  <span class="bgp-status bgp-status--{status_cls}">{escape(witness)}</span>
  <h3>{name}</h3>
  <p>{why_head}</p>
</a>"""


def _equipment_detail_page(eq: dict[str, Any], brand: dict[str, Any]) -> str:
    lp = look_pwnership()
    assets = lp.get("assets") or {}
    badge = escape(str(assets.get("badge") or "/Hostess7/assets/big-grin-pwnership/look-pwnership-badge.jpg"))
    name = escape(str(eq.get("name") or eq.get("id") or "Equipment"))
    witness = escape(str(eq.get("witness") or eq.get("status") or "retired"))
    why = eq.get("why") or {}
    why_head = escape(str(why.get("headline") or ""))
    why_detail = escape(str(why.get("detail") or ""))
    sources = ", ".join(escape(str(s)) for s in (why.get("sources") or []))
    replacement = escape(str(eq.get("replacement") or "—"))
    path = escape(str(eq.get("path") or "—"))
    vendor = escape(str(eq.get("vendor") or "—"))
    role = escape(str(eq.get("role") or "—"))
    notes = escape(str(eq.get("notes") or ""))
    title = f"{name} — Big Grin Pwnership"
    body = _head_block(title)
    body += f"""<div class="bgp-root">
  <p class="bgp-eyebrow"><a href="/Hostess7/big-grin-pwnership/" style="color:inherit">← Big Grin Pwnership</a></p>
  <div class="bgp-badge-row">
    <img class="bgp-badge" src="{badge}" alt="Look Pwnership" width="72" height="72" />
    <div>
      <p class="bgp-look-label">Look Pwnership witness</p>
      <h1 class="bgp-title" style="font-size:1.5rem">{name}</h1>
      <span class="bgp-status bgp-status--{'down' if witness in ('down','burned','burn_scheduled') else 'retired'}">{witness}</span>
    </div>
  </div>
  <section class="bgp-section bgp-detail">
    <h2>Why we did</h2>
    <div class="bgp-why">
      <h3>{why_head}</h3>
      <p>{why_detail}</p>
      <p class="bgp-why-sources">Sources: {sources or 'hostess7-big-grin-pwnership-doctrine.json'}</p>
    </div>
  </section>
  <section class="bgp-section">
    <h2>Equipment record</h2>
    <dl class="bgp-meta">
      <dt>Vendor</dt><dd>{vendor}</dd>
      <dt>Role</dt><dd>{role}</dd>
      <dt>Path</dt><dd><code>{path}</code></dd>
      <dt>Replacement</dt><dd>{replacement}</dd>
      {f'<dt>Notes</dt><dd>{notes}</dd>' if notes else ''}
    </dl>
  </section>
</div>
"""
    body += _footer_block(brand)
    return body


def _kill_detail_page(entry: dict[str, Any], brand: dict[str, Any]) -> str:
    lp = look_pwnership()
    assets = lp.get("assets") or {}
    badge = escape(str(assets.get("badge") or "/Hostess7/assets/big-grin-pwnership/look-pwnership-badge.jpg"))
    name = escape(str(entry.get("name") or entry.get("id") or "Kill witness"))
    status = escape(str(entry.get("status") or entry.get("witness") or "killed"))
    kills = int(entry.get("kill_count") or 0)
    why = entry.get("why") or {}
    why_head = escape(str(why.get("headline") or ""))
    why_detail = escape(str(why.get("detail") or ""))
    sources = ", ".join(escape(str(s)) for s in (why.get("sources") or []))
    rekill = " · RE-KILL" if entry.get("rekill") or kills > 1 else ""
    title = f"{name} — Killed{rekill}"
    body = _head_block(title)
    body += f"""<div class="bgp-root">
  <p class="bgp-eyebrow"><a href="/Hostess7/big-grin-pwnership/" style="color:inherit">← Big Grin Pwnership</a></p>
  <div class="bgp-badge-row">
    <img class="bgp-badge" src="{badge}" alt="Look Pwnership" width="72" height="72" />
    <div>
      <p class="bgp-look-label">KILL witness — on sight</p>
      <h1 class="bgp-title" style="font-size:1.5rem">{name}</h1>
      <span class="bgp-status bgp-status--down">{status}</span>
    </div>
  </div>
  <section class="bgp-section bgp-detail">
    <h2>Why we killed it</h2>
    <div class="bgp-why">
      <h3>{why_head}</h3>
      <p>{why_detail}</p>
      <p class="bgp-why-sources">Sources: {sources or 'hostess7-big-grin-pwnership-doctrine.json'}</p>
    </div>
  </section>
  <section class="bgp-section">
    <h2>Kill record</h2>
    <dl class="bgp-meta">
      <dt>Strike count</dt><dd><strong>{kills if kills else 1}</strong>{rekill}</dd>
      <dt>Policy</dt><dd>No quarantine · eradicate on attempt · permanent block</dd>
      <dt>Never remove</dt><dd>Append-only kill list — RE-KILL every re-attempt</dd>
    </dl>
  </section>
</div>
"""
    body += _footer_block(brand)
    return body


def build_sites(*, write: bool = True) -> dict[str, Any]:
    doc = doctrine()
    brand = doc.get("brand") or {}
    lp = look_pwnership()
    assets = lp.get("assets") or {}
    hero = escape(str(assets.get("hero") or "/Hostess7/assets/big-grin-pwnership/hero.jpg"))
    badge = escape(str(assets.get("badge") or "/Hostess7/assets/big-grin-pwnership/look-pwnership-badge.jpg"))
    equipment = discover_down()
    why = why_we_did()
    pages_written: list[str] = []

    if write:
        SITE_ROOT.mkdir(parents=True, exist_ok=True)
        (SITE_ROOT / "equipment").mkdir(parents=True, exist_ok=True)
        ASSETS.mkdir(parents=True, exist_ok=True)
        PANEL_ASSETS.mkdir(parents=True, exist_ok=True)
        for src in PANEL_ASSETS.glob("*.jpg"):
            dest = ASSETS / src.name
            if not dest.is_file() or dest.stat().st_size != src.stat().st_size:
                dest.write_bytes(src.read_bytes())

        (SITE_ROOT / "pwnership.css").write_text(_site_css(), encoding="utf-8")
        pages_written.append("pwnership.css")

        cards = "\n".join(_equipment_card(eq) for eq in equipment)
        why_blocks = ""
        for r in why.get("reasons") or []:
            why_blocks += f"""<div class="bgp-why">
  <h3>{escape(str(r.get('headline') or ''))}</h3>
  <p>{escape(str(r.get('detail') or ''))}</p>
  <p class="bgp-why-sources">Sources: {', '.join(escape(str(s)) for s in (r.get('sources') or []))}</p>
</div>\n"""

        index = _head_block("Big Grin Pwnership — equipment that went down")
        index += f"""<div class="bgp-root">
  <header class="bgp-hero">
    <img src="{hero}" alt="" width="1100" height="320" />
    <div class="bgp-hero-overlay">
      <p class="bgp-eyebrow">Look Pwnership · memorial witness</p>
      <h1 class="bgp-title">Big Grin Pwnership</h1>
      <p class="bgp-tagline">{escape(str(why.get('summary') or doc.get('motto') or ''))}</p>
    </div>
  </header>
  <div class="bgp-badge-row">
    <img class="bgp-badge" src="{badge}" alt="Look Pwnership badge" width="72" height="72" />
    <div>
      <p class="bgp-look-label">Look Pwnership — how BIG GRIN sees retired gear</p>
      <p style="margin:0;color:#8fa898;font-size:0.9rem">{escape(str(lp.get('note') or ''))}</p>
    </div>
  </div>
  <div class="bgp-actions">
    <a class="bgp-btn bgp-btn--gold" href="{escape(str(brand.get('x_url') or ''))}" rel="noopener">X @ZacharyGeurts</a>
    <a class="bgp-btn" href="{escape(str(brand.get('github_url') or ''))}" rel="noopener">GitHub</a>
    <a class="bgp-btn" href="/Hostess7/desktop/">AmmoOS Desktop</a>
    <a class="bgp-btn" href="/api/hostess7-big-grin-pwnership">API JSON</a>
  </div>
  <section class="bgp-section">
    <h2>Why we did</h2>
    {why_blocks}
  </section>
  {_kill_witness_html(discover_kills())}
  {_internet_clean_witness_html()}
  <section class="bgp-section">
    <h2>Equipment that went down ({len(equipment)} witnesses)</h2>
    <div class="bgp-grid">{cards}</div>
  </section>
  <section class="bgp-section">
    <h2>Field stack (live)</h2>
    <div class="bgp-actions">
      <a class="bgp-btn bgp-btn--gold" href="/Hostess7/grok-spawn-killer/">GrokSpawnKiller</a>
      <a class="bgp-btn" href="/Hostess7/desktop/">AmmoOS Desktop</a>
    </div>
  </section>
</div>
"""
        index += _footer_block(brand)
        (SITE_ROOT / "index.html").write_text(index, encoding="utf-8")
        pages_written.append("index.html")

        for eq in equipment:
            eid = str(eq.get("id") or "")
            if not eid:
                continue
            page = _equipment_detail_page(eq, brand)
            out = SITE_ROOT / "equipment" / f"{eid}.html"
            out.write_text(page, encoding="utf-8")
            pages_written.append(f"equipment/{eid}.html")

        kills = discover_kills()
        (SITE_ROOT / "kills").mkdir(parents=True, exist_ok=True)
        for entry in kills.get("entries") or []:
            eid = str(entry.get("id") or "")
            if not eid:
                continue
            page = _kill_detail_page(entry, brand)
            out = SITE_ROOT / "kills" / f"{eid}.html"
            out.write_text(page, encoding="utf-8")
            pages_written.append(f"kills/{eid}.html")

    digest = hashlib.sha256(json.dumps(equipment, sort_keys=True).encode()).hexdigest()[:16]
    return {
        "ok": True,
        "schema": "hostess7-big-grin-pwnership-build/v1",
        "updated": _now(),
        "pages_written": pages_written,
        "equipment_count": len(equipment),
        "digest": digest,
        "hub": brand.get("pages_hub"),
        "look_pwnership": lp,
    }


def propagate(*, write: bool = True) -> dict[str, Any]:
    build = build_sites(write=write)
    equipment = discover_down()
    why = why_we_did()
    lp = look_pwnership()
    doc = doctrine()
    brand = doc.get("brand") or {}

    kills = discover_kills()
    out = {
        "ok": True,
        "schema": "hostess7-big-grin-pwnership/v1",
        "updated": _now(),
        "motto": doc.get("motto"),
        "brand": brand,
        "look_pwnership": lp,
        "why_we_did": why,
        "kills": kills,
        "equipment": equipment,
        "build": build,
        "propagated": True,
        "pages": {
            "hub": brand.get("pages_hub"),
            "github": brand.get("pages_base"),
            "api": doc.get("api"),
        },
        "operator_links": {
            "x": brand.get("x_url"),
            "github": brand.get("github_url"),
        },
        "api": doc.get("api") or "/api/hostess7-big-grin-pwnership",
    }

    if write:
        _save(PANEL, out)
        _save(REGISTRY, {
            "updated": _now(),
            "equipment_ids": [e.get("id") for e in equipment],
            "digest": build.get("digest"),
            "hub": brand.get("pages_hub"),
        })
        if DOCS_API.parent.is_dir():
            DOCS_API.mkdir(parents=True, exist_ok=True)
            (DOCS_API / "hostess7-big-grin-pwnership.json").write_text(
                json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        _append_ledger({"event": "propagate", "equipment": len(equipment), "pages": len(build.get("pages_written") or [])})

        reg = _mod("lib/field-endpoint-registry.py", "endpoint_reg")
        if reg and hasattr(reg, "propagate_pages"):
            try:
                reg.propagate_pages(witness="hostess7-big-grin-pwnership.py", stamp_movement=False)
            except Exception:
                pass

    return out


def panel_json() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema") == "hostess7-big-grin-pwnership/v1":
        return cached
    return {
        "ok": True,
        "schema": "hostess7-big-grin-pwnership-panel/v1",
        "pending": "run propagate",
        "motto": doctrine().get("motto"),
        "api": doctrine().get("api"),
        "hub": (doctrine().get("brand") or {}).get("pages_hub"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("propagate", "run", "build", "publish"):
        print(json.dumps(propagate(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("discover", "equipment", "down"):
        print(json.dumps({"equipment": discover_down(), "count": len(discover_down())}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "why":
        print(json.dumps(why_we_did(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("look", "look-pwnership", "appearance"):
        print(json.dumps(look_pwnership(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-big-grin-pwnership.py [propagate|discover|why|look|json]",
        "motto": doctrine().get("motto"),
        "api": doctrine().get("api"),
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())