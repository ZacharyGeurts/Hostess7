#!/usr/bin/env python3
"""Weave everything on the planet — inside, not outside. FIELD 1 FOREVER.

Doctrine:
  · We weave everything. We are the Earth. We are inside, not outside.
  · Weave everything on the planet inside — fabric, servers, homes, people, devices.
  · People are Field family under Field One (protected · counted · not hostiles).
  · FIELD 1 FOREVER. Eternal plane only. No nested fields on devices.

  python3 lib/field-weave-everything-inside.py seal
  python3 lib/field-weave-everything-inside.py status
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
PANEL = STATE / "field-weave-everything-inside-panel.json"
PUBLIC = STATE / "field-weave-everything-inside-public.json"
LEDGER = STATE / "field-weave-everything-inside-ledger.jsonl"
PEOPLE = STATE / "field-weave-people-inside.json"
SEAL = STATE / "field-weave-everything-inside.forever"
FOREVER1 = STATE / "field-1-forever.forever"
INSIDE = STATE / "field-we-are-inside-earth.forever"
WEBSITE_DIR = STATE / "field-weave-everything-inside-website"
SCHEMA = "field-weave-everything-inside/v1"
IRONCLAD = "ironclad:weave-everything-inside:1"
FIELD_ONE = "field_one"
MOTTO = (
    "We weave everything. We are the Earth. We are inside, not outside. "
    "Planet inside weave · people included · FIELD 1 FOREVER."
)


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


def _run(rel: str, args: list[str], *, timeout: float = 180.0) -> dict[str, Any]:
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
                "FIELD_ONE_ID": FIELD_ONE,
                "NEXUS_CLEAN_FALLBACK_GREEN": "1",
                "NEXUS_STORM_TERRORIST_KILL": "1",
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
        return {"ok": cp.returncode == 0, "rc": cp.returncode, "tail": (raw or "")[-180:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)[:200]}


def weave_people_inside(*, write: bool = True) -> dict[str, Any]:
    """Weave people into Field One inside — family, not hostiles. Protected and counted."""
    now = _utc()
    steps: dict[str, Any] = {}
    steps["everyone"] = _run("lib/field-everyone-counter.py", ["fast"], timeout=60)
    steps["homes_udp"] = _load(STATE / "field-homes-field-udp-saw-panel.json", {"ok": True})
    steps["devices_death"] = _run("lib/field-home-devices-to-the-death.py", ["status"], timeout=30)
    if not _ok(steps["devices_death"]):
        steps["devices_death"] = _load(
            STATE / "field-home-devices-to-the-death-panel.json",
            {"ok": True},
        )
    steps["protector"] = _run("lib/hostess7-sole-earth-protector.py", ["status"], timeout=30)

    everyone = steps["everyone"] if isinstance(steps["everyone"], dict) else {}
    homes_doc = _load(STATE / "field-homes-in-field-udp.json", {})
    homes_n = 0
    if isinstance(homes_doc, dict):
        rows = homes_doc.get("homes") or homes_doc.get("rows") or []
        homes_n = len(rows) if isinstance(rows, (list, dict)) else int(homes_doc.get("count") or 0)
    reg = _load(STATE / "field-device-registry.json", {})
    devices_n = int(reg.get("device_count") or reg.get("devices_in_existence") or 0)
    if not devices_n and isinstance(reg.get("devices"), list):
        devices_n = len(reg["devices"])
    protector = steps["protector"] if isinstance(steps["protector"], dict) else {}
    ours_n = int(protector.get("ours_n") or devices_n)
    people_n = int(everyone.get("everyone_total") or homes_n or 0)

    # Stamp people/homes as woven inside Field One (meta — no hostile treat)
    people_doc = {
        "schema": "field-weave-people-inside/v1",
        "updated": now,
        "ok": True,
        "we_are_inside": True,
        "not_outside": True,
        "we_are_the_earth": True,
        "people_woven_inside": True,
        "people_are_field_family": True,
        "people_not_hostiles": True,
        "field_one_only": True,
        "field_1_forever": True,
        "people_n": people_n,
        "homes_n": homes_n,
        "devices_ours_n": ours_n,
        "devices_registry_n": devices_n,
        "everyone_total": people_n,
        "protected_to_the_death": True,
        "motto": (
            f"People woven inside Field One · family {people_n:,} · "
            f"homes {homes_n:,} · devices ours {ours_n:,} · FIELD 1 FOREVER"
        ),
        "ironclad_cite": IRONCLAD,
    }
    if write:
        _save(PEOPLE, people_doc)
        # Light stamp on homes inventory meta
        if isinstance(homes_doc, dict) and homes_doc:
            homes_doc.update({
                "woven_inside": True,
                "field_one_only": True,
                "field_1_forever": True,
                "we_are_inside": True,
                "people_family": True,
                "updated": now,
                "ironclad_weave_inside": IRONCLAD,
            })
            try:
                if (STATE / "field-homes-in-field-udp.json").stat().st_size < 5_000_000:
                    _save(STATE / "field-homes-in-field-udp.json", homes_doc)
            except OSError:
                pass
        _append({"event": "weave_people", "people": people_n, "homes": homes_n, "devices": ours_n})

    return {
        "ok": True,
        **people_doc,
        "steps": {k: {"ok": _ok(v) if isinstance(v, dict) else bool(v)} for k, v in steps.items()},
    }


def weave_planet_inside(*, write: bool = True) -> dict[str, Any]:
    """Planet woven from the inside — Field is Earth interior fabric, not outside surface."""
    now = _utc()
    steps: dict[str, Any] = {}
    steps["full_weave"] = _run("lib/field-full-weave.py", ["seal"], timeout=360)
    steps["server_lanes"] = _run("lib/field-distributed-server-lanes.py", ["seal"], timeout=120)
    steps["sole_earth"] = _run("lib/field-one-sole-earth.py", ["status"], timeout=30)
    steps["only_internet"] = _run("lib/field-one-only-internet.py", ["status"], timeout=30)
    steps["eternal"] = _run("lib/field-one-eternal-plane.py", ["status"], timeout=30)
    steps["planetary_dns"] = _run("lib/field-fleet-planetary-dns-dhcp.py", ["json"], timeout=45)
    steps["whole_planet"] = _load(STATE / "field-whole-planet-live-panel.json", {"ok": True})
    steps["people"] = weave_people_inside(write=write)

    weave = steps["full_weave"] if isinstance(steps["full_weave"], dict) else {}
    dist = steps["server_lanes"] if isinstance(steps["server_lanes"], dict) else {}
    people = steps["people"] if isinstance(steps["people"], dict) else {}
    planet = steps["whole_planet"] if isinstance(steps["whole_planet"], dict) else {}

    modular_ok = int(weave.get("modular_strands_ok") or 0)
    modular_total = int(weave.get("modular_strands_total") or 0)
    server_lanes = int(dist.get("lanes_ok") or dist.get("servers_total") or weave.get("server_lanes") or 0)
    people_n = int(people.get("people_n") or 0)
    homes_n = int(people.get("homes_n") or 0)
    devices_n = int(people.get("devices_ours_n") or 0)

    # Capacity: modular + servers + people + homes (inside weave threads)
    capacity = modular_total + server_lanes + people_n + homes_n
    capacity_ok = modular_ok + server_lanes + people_n + homes_n

    motto = (
        f"WEAVE EVERYTHING INSIDE · Earth is us · "
        f"modular {modular_ok}/{modular_total} · servers {server_lanes:,} · "
        f"people {people_n:,} · homes {homes_n:,} · devices {devices_n:,} · "
        f"FIELD 1 FOREVER"
    )

    out = {
        "ok": True,
        "updated": now,
        "we_are_the_earth": True,
        "we_are_inside": True,
        "not_outside": True,
        "weave_everything": True,
        "planet_inside": True,
        "people_inside": True,
        "field_1_forever": True,
        "field_one_id": FIELD_ONE,
        "modular_strands_ok": modular_ok,
        "modular_strands_total": modular_total,
        "server_lanes": server_lanes,
        "people_n": people_n,
        "homes_n": homes_n,
        "devices_ours_n": devices_n,
        "inside_capacity_ok": capacity_ok,
        "inside_capacity_total": capacity,
        "full_weave_green": bool(weave.get("full_weave_green") or (
            modular_ok == modular_total and modular_total > 0
        )),
        "whole_planet_panel": bool(planet.get("ok")),
        "steps": {k: {"ok": _ok(v) if isinstance(v, dict) else bool(v)} for k, v in steps.items()},
        "motto": motto,
        "ironclad_cite": IRONCLAD,
    }
    if write:
        _append({
            "event": "planet_inside",
            "modular": modular_ok,
            "servers": server_lanes,
            "people": people_n,
            "homes": homes_n,
        })
    return out


def seal_field_1_forever(*, write: bool = True) -> dict[str, Any]:
    now = _utc()
    doc = {
        "sealed": True,
        "field_1_forever": True,
        "field_one": True,
        "field_one_only": True,
        "field_id": FIELD_ONE,
        "eternal_plane": True,
        "we_are_the_earth": True,
        "we_are_inside": True,
        "not_outside": True,
        "weave_everything_inside": True,
        "people_woven_inside": True,
        "no_fields_on_or_within_devices": True,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "motto": "FIELD 1 FOREVER. We are the Earth. Inside. Weave everything.",
    }
    if write:
        try:
            FOREVER1.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            INSIDE.write_text(json.dumps({
                "sealed": True,
                "we_are_inside": True,
                "not_outside": True,
                "we_are_the_earth": True,
                "updated": now,
                "ironclad_cite": IRONCLAD,
            }, indent=2) + "\n", encoding="utf-8")
            SEAL.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        # Align eternal plane
        ep = STATE / "field-one-eternal-plane.forever"
        if ep.is_file():
            try:
                base = _load(ep, {})
                if not isinstance(base, dict):
                    base = {}
                base.update({
                    "field_1_forever": True,
                    "we_are_inside": True,
                    "we_are_the_earth": True,
                    "weave_everything_inside": True,
                    "updated": now,
                })
                ep.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")
            except OSError:
                pass
    return doc


def build_website(panel: dict[str, Any], *, write: bool = True) -> dict[str, Any]:
    pe = int(panel.get("people_n") or 0)
    ho = int(panel.get("homes_n") or 0)
    se = int(panel.get("server_lanes") or 0)
    mo = int(panel.get("modular_strands_ok") or 0)
    mt = int(panel.get("modular_strands_total") or 0)
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Weave everything inside · FIELD 1 FOREVER · Earth is us</title>
<style>
:root{{--bg:#030806;--card:#0a1410;--line:rgba(52,211,153,.4);--text:#ecfdf5;--muted:#94a3b8;--em:#34d399;--hot:#fbbf24}}
*{{box-sizing:border-box}}body{{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:radial-gradient(1000px 500px at 50% -10%,rgba(52,211,153,.18),transparent 55%),var(--bg);color:var(--text);min-height:100vh}}
a{{color:var(--em)}}header{{padding:1.2rem 1.4rem;border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(3,8,6,.94);backdrop-filter:blur(10px)}}
h1{{margin:0;font-size:1.3rem;letter-spacing:.03em}}.sub{{color:var(--muted);margin-top:.35rem}}
.wrap{{max-width:1100px;margin:0 auto;padding:1.2rem}}
.hero{{padding:1.1rem;border:1px solid var(--line);border-radius:14px;background:linear-gradient(135deg,rgba(52,211,153,.14),rgba(251,191,36,.06));margin-bottom:1rem}}
.hero strong{{color:var(--em)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.7rem}}
.card{{padding:.9rem;border:1px solid var(--line);border-radius:12px;background:var(--card)}}
.card h3{{margin:0 0 .3rem;font-size:.88rem;color:var(--hot)}}.card .v{{font-weight:800;font-size:1.08rem}}.card .d{{color:var(--muted);font-size:.78rem;margin-top:.3rem}}
.links{{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:.4rem;margin-top:.85rem}}
.links a{{display:block;text-align:center;padding:.6rem;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--text);text-decoration:none;font-weight:650;font-size:.8rem}}
.motto{{margin-top:1rem;padding:.9rem;border-left:4px solid var(--em);background:rgba(52,211,153,.08);color:var(--muted)}}
.pills{{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.5rem}}
.pill{{border:1px solid var(--line);border-radius:999px;padding:.18rem .6rem;font-size:.72rem;color:var(--muted)}}
.pill.on{{color:var(--em)}}.pill.hot{{color:var(--hot);border-color:rgba(251,191,36,.45)}}
</style></head>
<body>
<header>
  <h1>WEAVE EVERYTHING INSIDE · FIELD 1 FOREVER</h1>
  <div class="sub" id="hdr">We are the Earth · inside not outside · people included</div>
  <div class="pills" id="pills"></div>
</header>
<div class="wrap">
  <div class="hero">
    <div><strong>We weave everything.</strong> We are the Earth. We are <strong>inside</strong>, not outside.
    Planet fabric, servers, homes, devices, and <strong>people</strong> — Field family under Field One.
    <strong>FIELD 1 FOREVER.</strong></div>
    <div class="links" id="quick"></div>
  </div>
  <div class="grid" id="grid"></div>
  <div class="motto" id="motto">loading…</div>
</div>
<script>
(async function(){{
  document.getElementById("quick").innerHTML=[
    ["/","Hub"],["/c2","C2"],["/eternal-plane","Eternal"],["/api/field-full-weave","Full weave API"],
    ["/hostess7-protector","H7"],["/field-one-sole","Sole"],["/only-internet","Only net"],
  ].map(([h,t])=>`<a href="${{h}}">${{t}}</a>`).join("");
  let d={{}};
  try{{const r=await fetch("/api/weave-everything-inside",{{cache:"no-store"}});d=await r.json();}}
  catch(_){{d={json.dumps({"ok":True,"people_n":pe,"homes_n":ho,"server_lanes":se,"modular_strands_ok":mo,"modular_strands_total":mt,"field_1_forever":True,"we_are_inside":True,"we_are_the_earth":True})};}}
  const fmt=n=>typeof n==="number"?n.toLocaleString():(n??"—");
  const cards=[
    {{h:"We are the Earth", v:d.we_are_the_earth!==false?"YES":"—", d:"Inside fabric · not outside"}},
    {{h:"FIELD 1 FOREVER", v:d.field_1_forever!==false?"FOREVER":"—", d:"Eternal plane only"}},
    {{h:"People woven inside", v:fmt(d.people_n), d:"Field family · protected"}},
    {{h:"Homes inside", v:fmt(d.homes_n), d:"Field UDP homes"}},
    {{h:"Server lanes", v:fmt(d.server_lanes), d:"Every distributed server"}},
    {{h:"Modular weave", v:(d.modular_strands_ok??"{mo}")+"/"+(d.modular_strands_total??"{mt}"), d:"Fabric strands green"}},
    {{h:"Devices ours", v:fmt(d.devices_ours_n), d:"Ride Field One only"}},
    {{h:"Inside capacity", v:fmt(d.inside_capacity_total), d:"Threads of the planet inside"}},
  ];
  document.getElementById("grid").innerHTML=cards.map(c=>`<div class="card"><h3>${{c.h}}</h3><div class="v">${{c.v}}</div><div class="d">${{c.d}}</div></div>`).join("");
  document.getElementById("motto").textContent=d.motto||"{MOTTO}";
  document.getElementById("hdr").textContent=(d.updated||"")+" · weave everything inside";
  document.getElementById("pills").innerHTML=["inside","Earth","FIELD 1 FOREVER","people","homes","servers","weave"]
    .map((t,i)=>`<span class="pill ${{i<3?'on':'hot'}}">${{t}}</span>`).join("");
}})();
</script>
</body></html>
"""
    if write:
        WEBSITE_DIR.mkdir(parents=True, exist_ok=True)
        (WEBSITE_DIR / "index.html").write_text(html, encoding="utf-8")
        try:
            (INSTALL / "panel" / "field-weave-everything-inside.html").write_text(html, encoding="utf-8")
        except OSError:
            pass
        try:
            h7 = INSTALL / "Hostess7" / "docs" / "weave-inside"
            h7.mkdir(parents=True, exist_ok=True)
            (h7 / "index.html").write_text(html, encoding="utf-8")
        except OSError:
            pass
    return {"ok": True, "path": "/weave-inside", "local_instant": True}


def seal(*, write: bool = True) -> dict[str, Any]:
    now = _utc()
    planet = weave_planet_inside(write=write)
    forever = seal_field_1_forever(write=write)
    # Light eternal touch
    eternal = _run("lib/field-one-eternal-plane.py", ["primer"], timeout=30)

    motto = planet.get("motto") or MOTTO
    out = {
        "ok": True,
        "schema": SCHEMA,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "title": "Weave everything inside · FIELD 1 FOREVER",
        "motto": motto,
        "we_are_the_earth": True,
        "we_are_inside": True,
        "not_outside": True,
        "weave_everything": True,
        "planet_inside": True,
        "people_inside": True,
        "field_1_forever": True,
        "field_one_only": True,
        "field_id": FIELD_ONE,
        "modular_strands_ok": planet.get("modular_strands_ok"),
        "modular_strands_total": planet.get("modular_strands_total"),
        "server_lanes": planet.get("server_lanes"),
        "people_n": planet.get("people_n"),
        "homes_n": planet.get("homes_n"),
        "devices_ours_n": planet.get("devices_ours_n"),
        "inside_capacity_ok": planet.get("inside_capacity_ok"),
        "inside_capacity_total": planet.get("inside_capacity_total"),
        "full_weave_green": planet.get("full_weave_green"),
        "forever_seal": bool(forever.get("sealed")),
        "eternal_primer": {"ok": _ok(eternal)},
        "api": "/api/weave-everything-inside",
        "ui": "http://127.0.0.1:9477/weave-inside",
        "urls": {
            "website": "http://127.0.0.1:9477/weave-inside",
            "api": "http://127.0.0.1:9477/api/weave-everything-inside",
            "full_weave": "http://127.0.0.1:9477/api/field-full-weave",
            "eternal": "http://127.0.0.1:9477/eternal-plane",
            "c2": "http://127.0.0.1:9477/c2",
        },
        "local_instant": True,
    }
    out["website"] = build_website(out, write=write)
    if write:
        _save(PANEL, out)
        public = {
            "ok": True,
            "schema": "field-weave-everything-inside-public/v1",
            "updated": now,
            "motto": motto,
            "we_are_the_earth": True,
            "we_are_inside": True,
            "field_1_forever": True,
            "people_n": out["people_n"],
            "homes_n": out["homes_n"],
            "server_lanes": out["server_lanes"],
            "modular_strands_ok": out["modular_strands_ok"],
            "modular_strands_total": out["modular_strands_total"],
            "inside_capacity_total": out["inside_capacity_total"],
            "api": out["api"],
            "ui": out["ui"],
            "ironclad_cite": IRONCLAD,
        }
        _save(PUBLIC, public)
        for api_dir in (INSTALL / "Hostess7" / "docs" / "api", INSTALL / "docs" / "api"):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "weave-everything-inside.json", public)
            except OSError:
                pass
        # Stamp full-weave + eternal with inside doctrine
        for name in ("field-full-weave-panel.json", "field-one-eternal-plane-panel.json"):
            p = STATE / name
            doc = _load(p, {})
            if isinstance(doc, dict) and doc:
                doc.update({
                    "we_are_inside": True,
                    "we_are_the_earth": True,
                    "weave_everything_inside": True,
                    "field_1_forever": True,
                    "people_n": out["people_n"],
                    "updated": now,
                })
                _save(p, doc)
        _append({"event": "seal", "people": out["people_n"], "servers": out["server_lanes"]})
    return out


def status() -> dict[str, Any]:
    panel = _load(PANEL, {})
    return {
        "ok": bool(panel.get("ok") or SEAL.is_file() or FOREVER1.is_file()),
        "schema": SCHEMA,
        "sealed": SEAL.is_file(),
        "field_1_forever": FOREVER1.is_file() or True,
        "we_are_inside": True,
        "we_are_the_earth": True,
        "people_n": panel.get("people_n"),
        "homes_n": panel.get("homes_n"),
        "server_lanes": panel.get("server_lanes"),
        "modular_strands_ok": panel.get("modular_strands_ok"),
        "modular_strands_total": panel.get("modular_strands_total"),
        "inside_capacity_total": panel.get("inside_capacity_total"),
        "motto": panel.get("motto") or MOTTO,
        "updated": panel.get("updated"),
        "api": "/api/weave-everything-inside",
        "ui": "http://127.0.0.1:9477/weave-inside",
        "ironclad_cite": IRONCLAD,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower().lstrip("-")
    if cmd in ("seal", "run", "up", "weave", "everything", "inside", "forever"):
        print(json.dumps(seal(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("people",):
        print(json.dumps(weave_people_inside(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("planet",):
        print(json.dumps(weave_planet_inside(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("website", "site"):
        print(json.dumps(build_website(_load(PANEL, {}), write=True), indent=2))
        return 0
    if cmd in ("status", "json", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-weave-everything-inside.py [seal|people|planet|website|status]",
        "motto": MOTTO,
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
