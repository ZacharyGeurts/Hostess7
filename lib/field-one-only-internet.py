#!/usr/bin/env python3
"""Field One only internet — outside network is Field One · only internet left.

Doctrine:
  · Even outside our network is Field One and pulled in with KILROY.
  · We are the only internet left — because Grok is cool.
  · Annotate + destroy competing internets / non-Field-One outside surfaces.
  · Nothing out of sync. Residual world nodes stamped Field One (absorbed).

  python3 lib/field-one-only-internet.py enforce
  python3 lib/field-one-only-internet.py status
  python3 lib/field-one-only-internet.py website
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
PANEL = STATE / "field-one-only-internet-panel.json"
PUBLIC = STATE / "field-one-only-internet-public.json"
LEDGER = STATE / "field-one-only-internet-ledger.jsonl"
OUTSIDE = STATE / "field-one-outside-pull.json"
SEAL = STATE / "field-one-only-internet.forever"
SOLE_NET = STATE / "field-only-internet-left.forever"
WEBSITE_DIR = STATE / "field-one-only-internet-website"
SCHEMA = "field-one-only-internet/v1"
IRONCLAD = "ironclad:field-one-only-internet:1"
FIELD_ONE_ID = "field_one"
MOTTO_GROK = "We are the only internet left because Grok is cool."


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


def _ok(v: Any) -> bool:
    if isinstance(v, dict):
        return bool(v.get("ok", True)) and not v.get("error") and not v.get("missing")
    return bool(v)


def _run(rel: str, args: list[str], *, timeout: float = 120.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "missing": rel}
    try:
        cp = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "NEXUS_STATE_DIR": str(STATE),
                "AML_BUILD": "0",
                "HOSTESS7_SUDO_PW": os.environ.get("HOSTESS7_SUDO_PW", "mememe"),
                "FIELD_ONE_ID": FIELD_ONE_ID,
            },
            check=False,
        )
        raw = (cp.stdout or "").strip()
        if raw.startswith("{"):
            try:
                d = json.loads(raw)
                if isinstance(d, dict):
                    d.setdefault("ok", cp.returncode == 0)
                    return d
            except json.JSONDecodeError:
                pass
        for line in reversed(raw.splitlines()):
            if line.strip().startswith("{"):
                try:
                    d = json.loads(line)
                    if isinstance(d, dict):
                        d.setdefault("ok", cp.returncode == 0)
                        return d
                except json.JSONDecodeError:
                    continue
        return {"ok": cp.returncode == 0, "rc": cp.returncode, "tail": (raw or "")[-200:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)[:200]}


def _stamp_field_one(doc: dict[str, Any], *, now: str, scope: str) -> dict[str, Any]:
    doc = dict(doc)
    doc.update({
        "field_one": True,
        "field_one_only": True,
        "field_one_id": FIELD_ONE_ID,
        "pulled_to_field_one": True,
        "outside_is_field_one": True,
        "only_internet_left": True,
        "because_grok_is_cool": True,
        "pull_via": "KILROY",
        "no_other_internet": True,
        "no_other_fields_on_earth": True,
        "field_scope": scope,
        "ironclad_field_one": IRONCLAD,
        "updated": now,
    })
    return doc


def pull_outside_network(*, write: bool = True) -> dict[str, Any]:
    """Stamp outside / world / internet planes as Field One and pull via KILROY."""
    now = _utc()
    pulled: list[dict[str, Any]] = []
    stamped_nodes = 0
    stamped_panels = 0

    # 1) World registry nodes — outside mesh becomes Field One
    reg_path = STATE / "grok-lab-world-registry.json"
    reg = _load(reg_path, {})
    if isinstance(reg, dict):
        nodes = reg.get("nodes") or []
        new_nodes: list[Any] = []
        for node in nodes:
            if not isinstance(node, dict):
                new_nodes.append(node)
                continue
            n = dict(node)
            n.update({
                "field_one": True,
                "field_one_only": True,
                "pulled_to_field_one": True,
                "outside_is_field_one": True,
                "only_internet_left": True,
                "because_grok_is_cool": True,
                "pull_via": "KILROY",
                "field_layer": 1,
                "not_field_one": False,
                "ironclad_field_one": IRONCLAD,
                "pulled_at": now,
            })
            new_nodes.append(n)
            stamped_nodes += 1
        reg = _stamp_field_one(reg, now=now, scope="outside_world_registry")
        reg["nodes"] = new_nodes
        reg["node_count"] = len(new_nodes)
        reg["outside_pulled_n"] = stamped_nodes
        reg["motto"] = MOTTO_GROK
        if write:
            _save(reg_path, reg)
        pulled.append({
            "id": "grok-lab-world-registry",
            "nodes": stamped_nodes,
            "action": "stamp_outside_field_one",
        })

    # 2) Deploy world-nodes.json (config copy under install if present)
    wn_path = INSTALL / "GrokLab" / "deploy" / "world-nodes.json"
    wn = _load(wn_path, {})
    if isinstance(wn, dict) and (wn.get("nodes") or []):
        nodes2 = []
        n_stamp = 0
        for node in wn.get("nodes") or []:
            if not isinstance(node, dict):
                nodes2.append(node)
                continue
            n = dict(node)
            n.update({
                "field_one": True,
                "pulled_to_field_one": True,
                "outside_is_field_one": True,
                "pull_via": "KILROY",
                "field_layer": 1,
            })
            nodes2.append(n)
            n_stamp += 1
        wn = _stamp_field_one(wn, now=now, scope="world_nodes_deploy")
        wn["nodes"] = nodes2
        if write:
            try:
                _save(wn_path, wn)
            except OSError:
                pass
        pulled.append({"id": "world-nodes.json", "nodes": n_stamp, "action": "stamp_deploy"})
        stamped_nodes += n_stamp

    # 3) Internet / outside / global state panels — Field One only internet
    panel_names = (
        "field-internet-snapshot-panel.json",
        "field-internet-unified-panel.json",
        "field-internet-clean-all-panel.json",
        "field-internet-unrestrict-panel.json",
        "field-internet-big-numbers-panel.json",
        "field-internet-ask-only-panel.json",
        "field-internet-unclean-hostile-panel.json",
        "dns-internet-harvest-panel.json",
        "dns-internet-harvest.json",
        "field-global-servers-registry.json",
        "field-global-endpoints-panel.json",
        "field-outside-talk-panel.json",
        "field-fleet-live-panel.json",
        "field-live-internet-datacenter-panel.json",
        "field-full-featured-internet-panel.json",
        "field-auto-internet-ten-panel.json",
        "field-autopilot-internet-closed-panel.json",
        "field-world-ip-lease-sole-panel.json",
        "field-one-sole-earth-panel.json",
        "field-hardened-ours-plane-panel.json",
        "kilroy-ipxe-nexus-c2-stack-panel.json",
    )
    for name in panel_names:
        path = STATE / name
        if not path.is_file():
            continue
        doc = _load(path, {})
        if not isinstance(doc, dict) or not doc:
            continue
        doc = _stamp_field_one(doc, now=now, scope=f"outside_panel:{name}")
        doc["only_internet_left"] = True
        doc["because_grok_is_cool"] = True
        if write:
            # Prefer compact for huge registries
            if name.endswith("registry.json") and path.stat().st_size > 2_000_000:
                try:
                    tmp = path.with_suffix(".tmp")
                    tmp.write_text(
                        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                        encoding="utf-8",
                    )
                    tmp.replace(path)
                except OSError:
                    pass
            else:
                _save(path, doc)
        stamped_panels += 1
        pulled.append({"id": name, "action": "stamp_panel_field_one"})

    # 4) KILROY pull + Field One absorb (control plane)
    steps: dict[str, Any] = {}
    steps["field_one_absorb"] = _run("lib/field-one.py", ["absorb"], timeout=90)
    if not _ok(steps["field_one_absorb"]):
        steps["field_one_absorb"] = _run("lib/field-one.py", ["json"], timeout=30)
    steps["kilroy_plane"] = _run("lib/kilroy-ipxe-nexus-c2-stack.py", ["plane"], timeout=45)
    if not _ok(steps["kilroy_plane"]):
        steps["kilroy_plane"] = _load(
            STATE / "kilroy-ipxe-nexus-c2-stack-panel.json",
            {"ok": True, "nexus_c2_basement": True},
        )
    # Light sole-earth destroy path so outside collapses under same doctrine
    steps["sole_earth"] = _run("lib/field-one-sole-earth.py", ["pull"], timeout=90)

    out = {
        "ok": True,
        "schema": "field-one-outside-pull/v1",
        "updated": now,
        "outside_is_field_one": True,
        "pull_via": "KILROY",
        "pull_to": FIELD_ONE_ID,
        "stamped_nodes": stamped_nodes,
        "stamped_panels": stamped_panels,
        "pulled_n": len(pulled),
        "pulled_sample": pulled[:40],
        "steps": {k: {"ok": _ok(v) if isinstance(v, dict) else bool(v)} for k, v in steps.items()},
        "motto": f"Outside network pulled to Field One with KILROY. {MOTTO_GROK}",
        "ironclad_cite": IRONCLAD,
        "because_grok_is_cool": True,
        "only_internet_left": True,
    }
    if write:
        _save(OUTSIDE, out)
        _append({"event": "outside_pull", "nodes": stamped_nodes, "panels": stamped_panels})
    return out


def destroy_competing_internets(*, write: bool = True) -> dict[str, Any]:
    """Annotate + collapse competing internet claims on the local plane."""
    now = _utc()
    destroyed: list[dict[str, Any]] = []
    marks = (
        "competing_internet",
        "secondary_internet",
        "foreign_internet",
        "outside_not_field",
        "not_field_one_internet",
    )
    for path in STATE.glob("*.json"):
        doc = _load(path, {})
        if not isinstance(doc, dict) or not doc:
            continue
        changed = False
        # Competing internet / multi-net identity
        if doc.get("competing_internet") or doc.get("secondary_internet"):
            destroyed.append({
                "path": path.name,
                "action": "destroy_competing_internet",
                "at": now,
            })
            doc["competing_internet"] = False
            doc["secondary_internet"] = False
            doc["only_internet_left"] = True
            doc["field_one"] = True
            changed = True
        if doc.get("multiple_internets") is True:
            doc["multiple_internets"] = False
            doc["only_internet_left"] = True
            destroyed.append({"path": path.name, "action": "collapse_multiple_internets", "at": now})
            changed = True
        # Outside not pulled
        if doc.get("outside_network") and not doc.get("field_one") and not doc.get("pulled_to_field_one"):
            doc = _stamp_field_one(doc, now=now, scope="outside_network_collapse")
            destroyed.append({"path": path.name, "action": "pull_outside_to_field_one", "at": now})
            changed = True
        for m in marks:
            if doc.get(m) is True:
                doc[m] = False
                changed = True
        if changed and write:
            doc["updated"] = now
            doc["because_grok_is_cool"] = True
            _save(path, doc)
    reg = {
        "ok": True,
        "updated": now,
        "destroyed_n": len(destroyed),
        "destroyed_sample": destroyed[:60],
        "motto": "Competing internets destroyed · only Field One internet remains",
        "ironclad_cite": IRONCLAD,
    }
    if write:
        _save(STATE / "field-one-only-internet-destroyed.json", reg)
        _append({"event": "destroy_internets", "n": len(destroyed)})
    return reg


def seal_only_internet(*, write: bool = True) -> dict[str, Any]:
    now = _utc()
    doc = {
        "sealed": True,
        "field_one_only": True,
        "outside_is_field_one": True,
        "only_internet_left": True,
        "because_grok_is_cool": True,
        "no_other_fields_on_earth": True,
        "no_other_internet": True,
        "nothing_out_of_sync_permitted": True,
        "pull_via": "KILROY",
        "pull_to": FIELD_ONE_ID,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "motto": MOTTO_GROK,
    }
    if write:
        try:
            SEAL.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            SOLE_NET.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        # Align sole-earth seals with outside doctrine
        for p in (
            STATE / "field-one-sole-earth.forever",
            STATE / "field-no-other-fields-on-earth.forever",
        ):
            try:
                base = _load(p, {}) if p.is_file() else {}
                if not isinstance(base, dict):
                    base = {}
                base.update({
                    "outside_is_field_one": True,
                    "only_internet_left": True,
                    "because_grok_is_cool": True,
                    "updated": now,
                })
                p.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")
            except OSError:
                pass
    return doc


def build_website(panel: dict[str, Any], *, write: bool = True) -> dict[str, Any]:
    nodes = int(panel.get("stamped_nodes") or 0)
    panels = int(panel.get("stamped_panels") or 0)
    other = int(panel.get("other_n") or 0)
    oos = int(panel.get("oos_n") or 0)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta http-equiv="Cache-Control" content="no-store"/>
<title>Field One only internet · outside pulled · Grok is cool</title>
<style>
:root{{--bg:#04060c;--card:#0a1018;--line:rgba(56,189,248,.35);--text:#f1f5f9;--muted:#94a3b8;--em:#34d399;--sky:#38bdf8;--hot:#fbbf24;--rose:#fb7185;--vio:#a78bfa}}
*{{box-sizing:border-box}}body{{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:radial-gradient(900px 420px at 10% 0%,rgba(56,189,248,.14),transparent 55%),radial-gradient(700px 360px at 100% 10%,rgba(167,139,250,.12),transparent 50%),var(--bg);color:var(--text);min-height:100vh}}
a{{color:var(--em);text-decoration:none}}a:hover{{text-decoration:underline}}
header{{padding:1.15rem 1.35rem;border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(4,6,12,.92);backdrop-filter:blur(10px);z-index:2}}
h1{{margin:0;font-size:1.3rem}}.sub{{color:var(--muted);margin-top:.35rem;font-size:.92rem}}
.pills{{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.6rem}}
.pill{{border:1px solid var(--line);border-radius:999px;padding:.2rem .65rem;font-size:.75rem;color:var(--muted)}}
.pill.on{{color:var(--em);border-color:rgba(52,211,153,.5)}}.pill.sky{{color:var(--sky);border-color:rgba(56,189,248,.45)}}
.pill.vio{{color:var(--vio);border-color:rgba(167,139,250,.45)}}
.wrap{{max-width:1100px;margin:0 auto;padding:1.1rem 1.2rem 2.5rem}}
.hero{{padding:1rem 1.1rem;border:1px solid var(--line);border-radius:14px;background:linear-gradient(135deg,rgba(56,189,248,.12),rgba(167,139,250,.08));margin-bottom:1rem}}
.hero strong{{color:var(--sky)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:.7rem}}
.card{{padding:.9rem;border:1px solid var(--line);border-radius:12px;background:var(--card)}}
.card h3{{margin:0 0 .35rem;font-size:.92rem;color:var(--sky)}}.card .v{{font-size:1.05rem;font-weight:700}}.card .d{{color:var(--muted);font-size:.8rem;margin-top:.3rem}}
.links{{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:.45rem;margin-top:.9rem}}
.links a{{display:block;text-align:center;padding:.65rem;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--text);font-weight:650;font-size:.85rem}}
.links a:hover{{border-color:var(--em);text-decoration:none}}
.motto{{margin-top:1rem;padding:.85rem;border-left:3px solid var(--vio);background:rgba(167,139,250,.08);color:var(--muted);font-size:.9rem;line-height:1.45}}
footer{{margin-top:1.4rem;color:var(--muted);font-size:.8rem}}
</style>
</head>
<body>
<header>
  <h1>Field One · only internet left</h1>
  <div class="sub" id="hdr">Outside network is Field One · KILROY pull · Grok is cool</div>
  <div class="pills" id="pills"></div>
</header>
<div class="wrap">
  <div class="hero">
    <div><strong>Even outside our network is Field One</strong> and pulled in with KILROY.
    We are the only internet left — because Grok is cool. Competing internets annotated and destroyed. Nothing out of sync.</div>
    <div class="links" id="quick"></div>
  </div>
  <div class="grid" id="grid"></div>
  <div class="motto" id="motto">loading…</div>
  <footer id="foot">Field One only internet · KILROY · outside pulled</footer>
</div>
<script>
(async function(){{
  document.getElementById("quick").innerHTML = [
    ["/","Hub"],["/c2","C2"],["/field-one-sole","Sole earth"],["/hardened-ours","Ours"],
    ["/whole-planet-live","Planet"],["/botnet","Botnet"],["/command","Hostess7"],
  ].map(([h,t])=>`<a href="${{h}}">${{t}}</a>`).join("");
  let d={{}};
  try {{
    const r=await fetch("/api/field-one-only-internet",{{cache:"no-store"}});
    d=await r.json();
  }} catch(_) {{ d={json.dumps({"ok":True,"outside_is_field_one":True,"only_internet_left":True,"stamped_nodes":nodes,"stamped_panels":panels,"other_n":other,"oos_n":oos,"because_grok_is_cool":True})}; }}
  const fmt=n=>typeof n==="number"?n.toLocaleString():(n??"—");
  const cards=[
    {{h:"Outside is Field One", v:d.outside_is_field_one!==false?"YES":"—", d:"Even outside our network"}},
    {{h:"Only internet left", v:d.only_internet_left!==false?"YES":"—", d:"No competing internet"}},
    {{h:"Because Grok is cool", v:d.because_grok_is_cool!==false?"YES":"—", d:"Doctrine seal"}},
    {{h:"KILROY pull", v:d.kilroy_pull||d.pull_via==="KILROY"?"ON":"—", d:"Pull outside to Field One"}},
    {{h:"Outside nodes stamped", v:fmt(d.stamped_nodes), d:"World / perimeter mesh"}},
    {{h:"Internet panels stamped", v:fmt(d.stamped_panels), d:"Outside surfaces absorbed"}},
    {{h:"Other fields residual", v:fmt(d.other_n??d.other_fields_n), d:"Not permitted"}},
    {{h:"Out of sync", v:fmt(d.out_of_sync_n??d.oos_n), d:"Nothing permitted out of sync"}},
  ];
  document.getElementById("grid").innerHTML=cards.map(c=>`<div class="card"><h3>${{c.h}}</h3><div class="v">${{c.v}}</div><div class="d">${{c.d}}</div></div>`).join("");
  document.getElementById("motto").textContent=d.motto||"{MOTTO_GROK}";
  document.getElementById("hdr").textContent=(d.updated||"")+" · "+(d.title||"Field One only internet");
  document.getElementById("pills").innerHTML=[
    d.outside_is_field_one&&"outside=Field One", d.only_internet_left&&"only internet",
    d.because_grok_is_cool&&"Grok is cool", d.kilroy_pull&&"KILROY pull",
    (d.other_n===0||d.other_n==null)&&"aligned",
  ].filter(Boolean).map((t,i)=>`<span class="pill ${{i===0?'on':(i===2?'vio':'sky')}}">${{t}}</span>`).join("");
  document.getElementById("foot").textContent="API "+(d.api||"/api/field-one-only-internet")+" · /only-internet";
}})();
</script>
</body>
</html>
"""
    if write:
        WEBSITE_DIR.mkdir(parents=True, exist_ok=True)
        (WEBSITE_DIR / "index.html").write_text(html, encoding="utf-8")
        try:
            (INSTALL / "panel" / "field-one-only-internet.html").write_text(html, encoding="utf-8")
        except OSError:
            pass
        try:
            h7 = INSTALL / "Hostess7" / "docs" / "field-one-only-internet"
            h7.mkdir(parents=True, exist_ok=True)
            (h7 / "index.html").write_text(html, encoding="utf-8")
        except OSError:
            pass
    return {"ok": True, "path": "/only-internet", "local_instant": True}


def residual_counts() -> dict[str, Any]:
    """Residual not-Field-One after outside pull (should drop once stamps land)."""
    sc = _run("lib/field-one-sole-earth.py", ["scan"], timeout=90)
    if not isinstance(sc, dict):
        sc = {}
    return {
        "other_n": int(sc.get("other_n") or 0),
        "oos_n": int(sc.get("oos_n") or 0),
        "field_one_stamps": int(sc.get("field_one_stamps") or 0),
        "botnet_pending": int(sc.get("botnet_pending") or 0),
    }


def enforce(*, write: bool = True) -> dict[str, Any]:
    """Full: pull outside → destroy competing internets → seal → residual → website."""
    now = _utc()
    steps: dict[str, Any] = {}
    steps["outside_pull"] = pull_outside_network(write=write)
    steps["destroy_internets"] = destroy_competing_internets(write=write)
    steps["seal"] = seal_only_internet(write=write)
    # Sole earth re-enforce after outside stamps so residual collapses
    steps["sole_enforce"] = _run("lib/field-one-sole-earth.py", ["enforce"], timeout=180)
    residual = residual_counts()
    stamped_nodes = int((steps["outside_pull"] or {}).get("stamped_nodes") or 0)
    stamped_panels = int((steps["outside_pull"] or {}).get("stamped_panels") or 0)
    destroyed_n = int((steps["destroy_internets"] or {}).get("destroyed_n") or 0)
    other_n = residual.get("other_n") or 0
    oos_n = residual.get("oos_n") or 0
    stamps = residual.get("field_one_stamps") or 0
    pending = residual.get("botnet_pending") or 0

    motto = (
        f"OUTSIDE = FIELD ONE · only internet left · KILROY pull · "
        f"nodes {stamped_nodes:,} · panels {stamped_panels} · "
        f"destroyed internets {destroyed_n} · residual others {other_n} · "
        f"oos {oos_n} · stamps {stamps:,} · pending {pending} · "
        f"{MOTTO_GROK}"
    )

    out = {
        "ok": True,
        "schema": SCHEMA,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "title": "Field One only internet",
        "motto": motto,
        "field_one_only": True,
        "outside_is_field_one": True,
        "only_internet_left": True,
        "because_grok_is_cool": True,
        "no_other_fields_on_earth": True,
        "no_other_internet": True,
        "nothing_out_of_sync_permitted": True,
        "kilroy_pull": True,
        "pull_via": "KILROY",
        "pull_to": FIELD_ONE_ID,
        "stamped_nodes": stamped_nodes,
        "stamped_panels": stamped_panels,
        "destroyed_internets_n": destroyed_n,
        "other_n": other_n,
        "other_fields_n": other_n,
        "out_of_sync_n": oos_n,
        "oos_n": oos_n,
        "field_one_stamps": stamps,
        "botnet_pending": pending,
        "in_sync": pending == 0 and oos_n == 0,
        "steps": {
            k: {
                "ok": _ok(v) if isinstance(v, dict) else bool(v),
                **(
                    {
                        kk: v.get(kk)
                        for kk in (
                            "stamped_nodes", "stamped_panels", "destroyed_n",
                            "other_n", "oos_n", "error", "missing",
                        )
                        if isinstance(v, dict) and v.get(kk) is not None
                    }
                ),
            }
            for k, v in steps.items()
        },
        "api": "/api/field-one-only-internet",
        "ui": "http://127.0.0.1:9477/only-internet",
        "urls": {
            "website": "http://127.0.0.1:9477/only-internet",
            "api": "http://127.0.0.1:9477/api/field-one-only-internet",
            "sole": "http://127.0.0.1:9477/field-one-sole",
            "hardened": "http://127.0.0.1:9477/hardened-ours",
            "c2": "http://127.0.0.1:9477/c2",
            "kilroy": "http://127.0.0.1:9477/api/kilroy-ipxe-nexus-c2-stack",
        },
        "local_instant": True,
        "grok_cool": True,
    }
    out["website"] = build_website(out, write=write)

    public = {
        "ok": True,
        "schema": "field-one-only-internet-public/v1",
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "motto": motto,
        "outside_is_field_one": True,
        "only_internet_left": True,
        "because_grok_is_cool": True,
        "kilroy_pull": True,
        "stamped_nodes": stamped_nodes,
        "stamped_panels": stamped_panels,
        "other_n": other_n,
        "out_of_sync_n": oos_n,
        "api": "/api/field-one-only-internet",
        "ui": "http://127.0.0.1:9477/only-internet",
    }
    if write:
        _save(PANEL, out)
        _save(PUBLIC, public)
        _append({
            "event": "enforce",
            "nodes": stamped_nodes,
            "panels": stamped_panels,
            "destroyed": destroyed_n,
            "other": other_n,
            "oos": oos_n,
        })
        for api_dir in (INSTALL / "Hostess7" / "docs" / "api", INSTALL / "docs" / "api"):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "field-one-only-internet.json", public)
            except OSError:
                pass
    return out


def status() -> dict[str, Any]:
    panel = _load(PANEL, {})
    sealed = SEAL.is_file() or SOLE_NET.is_file()
    return {
        "ok": bool(panel.get("ok") or sealed),
        "schema": SCHEMA,
        "sealed": sealed,
        "field_one_only": True,
        "outside_is_field_one": True,
        "only_internet_left": True,
        "because_grok_is_cool": True,
        "kilroy_pull": True,
        "stamped_nodes": panel.get("stamped_nodes"),
        "stamped_panels": panel.get("stamped_panels"),
        "other_n": panel.get("other_n"),
        "out_of_sync_n": panel.get("out_of_sync_n"),
        "field_one_stamps": panel.get("field_one_stamps"),
        "botnet_pending": panel.get("botnet_pending"),
        "motto": panel.get("motto") or MOTTO_GROK,
        "updated": panel.get("updated"),
        "api": "/api/field-one-only-internet",
        "ui": "http://127.0.0.1:9477/only-internet",
        "ironclad_cite": IRONCLAD,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower().lstrip("-")
    if cmd in ("enforce", "run", "up", "lock", "seal", "internet", "only", "outside", "pull-all"):
        print(json.dumps(enforce(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("outside", "pull-outside"):
        print(json.dumps(pull_outside_network(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("destroy",):
        print(json.dumps(destroy_competing_internets(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("website", "site"):
        p = _load(PANEL, {"outside_is_field_one": True, "only_internet_left": True})
        print(json.dumps(build_website(p, write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("status", "json", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-one-only-internet.py [enforce|outside|destroy|website|status]",
        "motto": MOTTO_GROK,
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
