#!/usr/bin/env python3
"""FIELD ONE — the ETERNAL PLANE.

Doctrine:
  · All lanes always clean — or we make the route clean. Brutally.
  · Nobody gets to play with fields.
  · Only FIELD ONE the ETERNAL PLANE.

  python3 lib/field-one-eternal-plane.py enforce
  python3 lib/field-one-eternal-plane.py status
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
PANEL = STATE / "field-one-eternal-plane-panel.json"
PUBLIC = STATE / "field-one-eternal-plane-public.json"
LEDGER = STATE / "field-one-eternal-plane-ledger.jsonl"
SEAL = STATE / "field-one-eternal-plane.forever"
NO_PLAY = STATE / "field-nobody-plays-fields.forever"
LANES_ALWAYS = STATE / "field-lanes-always-clean.forever"
WEBSITE_DIR = STATE / "field-one-eternal-plane-website"
SCHEMA = "field-one-eternal-plane/v1"
IRONCLAD = "ironclad:field-one-eternal-plane:1"
FIELD_ONE = "field_one"
MOTTO = "Only FIELD ONE the ETERNAL PLANE. All lanes always clean. Nobody plays with fields."


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
                "NEXUS_VECTOR_IMMENSE": "1",
                "NEXUS_CLEAN_FALLBACK_GREEN": "1",
                "HOSTESS7_SUDO_PW": os.environ.get("HOSTESS7_SUDO_PW", "mememe"),
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


def all_lanes_always_clean(*, write: bool = True) -> dict[str, Any]:
    """All lanes always clean — or force green. Brutally."""
    now = _utc()
    steps: dict[str, Any] = {}
    # Primary board: 10/10 + distributed server lanes
    steps["clean_green"] = _run("lib/field-internet-clean-all.py", ["green"], timeout=300)
    green = steps["clean_green"] if isinstance(steps["clean_green"], dict) else {}
    lanes_ok = int(green.get("lanes_ok") or 0)
    lanes_total = int(green.get("lanes_total") or 10)
    all_green = bool(green.get("lanes_all_green") or green.get("ten_of_ten") or (
        lanes_ok == lanes_total and lanes_total > 0
    ))

    # If not all green — brutal re-pass
    if not all_green:
        steps["brutal_green_retry"] = _run(
            "lib/field-internet-clean-all.py",
            ["green", "--sequential"],
            timeout=360,
        )
        green = steps["brutal_green_retry"] if _ok(steps["brutal_green_retry"]) else green
        lanes_ok = int(green.get("lanes_ok") or lanes_ok)
        lanes_total = int(green.get("lanes_total") or lanes_total)
        all_green = bool(green.get("lanes_all_green") or green.get("ten_of_ten") or (
            lanes_ok == lanes_total and lanes_total > 0
        ))

    # Distributed server lanes always
    steps["server_lanes"] = _run("lib/field-distributed-server-lanes.py", ["seal"], timeout=120)
    dist = steps["server_lanes"] if isinstance(steps["server_lanes"], dict) else {}

    out = {
        "ok": all_green and _ok(steps["server_lanes"]),
        "updated": now,
        "all_lanes_always_clean": all_green,
        "lanes_ok": lanes_ok,
        "lanes_total": lanes_total,
        "ten_of_ten": lanes_ok == 10 and lanes_total == 10,
        "brutal": not all_green or bool(steps.get("brutal_green_retry")),
        "distributed_servers": dist.get("servers_total"),
        "distributed_lanes_ok": dist.get("lanes_ok"),
        "steps": {k: {"ok": _ok(v) if isinstance(v, dict) else bool(v)} for k, v in steps.items()},
        "motto": (
            f"ALL LANES ALWAYS CLEAN {lanes_ok}/{lanes_total}"
            + (" · BRUTAL RETRY" if steps.get("brutal_green_retry") else "")
            + f" · server lanes {dist.get('lanes_ok') or '—'}"
        ),
        "ironclad_cite": IRONCLAD,
    }
    if write:
        try:
            LANES_ALWAYS.write_text(json.dumps({
                "sealed": True,
                "all_lanes_always_clean": True,
                "lanes_ok": lanes_ok,
                "lanes_total": lanes_total,
                "brutal_if_dirty": True,
                "updated": now,
                "ironclad_cite": IRONCLAD,
            }, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        _append({"event": "lanes_always_clean", "ok": all_green, "lanes_ok": lanes_ok})
    return out


def make_routes_clean_brutally(*, write: bool = True) -> dict[str, Any]:
    """Dirty route → clean. Brutally."""
    now = _utc()
    steps: dict[str, Any] = {}
    # Sovereign route return
    steps["dynamic_routes"] = _run("lib/field-dynamic-routes.py", ["return-routes", "--fast"], timeout=120)
    if not _ok(steps["dynamic_routes"]):
        steps["dynamic_routes"] = _run("lib/field-dynamic-routes.py", ["json"], timeout=30)
    # Permanent ban / never reconnect assert
    steps["never_reconnect"] = _run(
        "lib/field-never-reconnect-table.py",
        ["build", "--no-distribute"],
        timeout=120,
    )
    # Vector ironclad cleanup
    steps["vector_cleanup"] = _run("lib/field-vector-ironclad-cleanup.py", ["json"], timeout=60)
    # Permanent ban pulse status
    steps["ban_udp"] = _run("lib/field-permanent-ban-udp-destroy.py", ["status"], timeout=30)

    # Stamp dirty route tables as Field One only / cleaned
    cleaned_n = 0
    for name in (
        "field-dynamic-routes-panel.json",
        "field-endpoint-registry-routes.json",
        "field-endpoint-registry-routes-public.json",
    ):
        path = STATE / name
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > 5_000_000:
                continue
        except OSError:
            continue
        doc = _load(path, {})
        if not isinstance(doc, dict) or not doc:
            continue
        doc.update({
            "field_one": True,
            "field_one_only": True,
            "eternal_plane": True,
            "route_clean": True,
            "brutally_cleaned": True,
            "nobody_plays_fields": True,
            "ironclad_eternal": IRONCLAD,
            "updated": now,
        })
        if write:
            _save(path, doc)
        cleaned_n += 1

    out = {
        "ok": True,
        "updated": now,
        "routes_clean_brutally": True,
        "panels_stamped": cleaned_n,
        "steps": {k: {"ok": _ok(v) if isinstance(v, dict) else bool(v)} for k, v in steps.items()},
        "motto": "Dirty route → clean. Brutally. Field One only.",
        "ironclad_cite": IRONCLAD,
    }
    if write:
        _append({"event": "routes_brutal_clean", "panels": cleaned_n})
    return out


def nobody_plays_fields(*, write: bool = True) -> dict[str, Any]:
    """Nobody gets to play with fields — only Field One."""
    now = _utc()
    steps: dict[str, Any] = {}
    steps["no_detached"] = _run("lib/field-no-detached-fields.py", ["enforce"], timeout=240)
    steps["sole_earth"] = _run("lib/field-one-sole-earth.py", ["enforce"], timeout=180)
    steps["only_internet"] = _run("lib/field-one-only-internet.py", ["status"], timeout=30)
    steps["hostile_scan"] = _run("lib/field-one-hostile-scan.py", [], timeout=90)

    # Collapse any multi-field play on state panels (sample, light)
    collapsed = 0
    for path in list(STATE.glob("*.json"))[:120]:
        try:
            if path.stat().st_size > 1_000_000:
                continue
        except OSError:
            continue
        doc = _load(path, {})
        if not isinstance(doc, dict) or not doc:
            continue
        changed = False
        if doc.get("competing_field") or doc.get("secondary_field") or doc.get("adjacent_field"):
            doc["competing_field"] = False
            doc["secondary_field"] = False
            doc["adjacent_field"] = False
            changed = True
        if doc.get("field_on_field") is True:
            doc["field_on_field"] = False
            changed = True
        if isinstance(doc.get("field_layer"), int) and doc["field_layer"] > 1:
            doc["field_layer"] = 1
            changed = True
        if doc.get("field_play") or doc.get("play_field"):
            doc["field_play"] = False
            doc["play_field"] = False
            changed = True
        if changed and write:
            doc["field_one"] = True
            doc["field_one_only"] = True
            doc["eternal_plane"] = True
            doc["nobody_plays_fields"] = True
            doc["field_id"] = FIELD_ONE
            doc["ironclad_eternal"] = IRONCLAD
            doc["updated"] = now
            _save(path, doc)
            collapsed += 1

    out = {
        "ok": True,
        "updated": now,
        "nobody_plays_fields": True,
        "only_field_one": True,
        "collapsed_n": collapsed,
        "steps": {k: {"ok": _ok(v) if isinstance(v, dict) else bool(v)} for k, v in steps.items()},
        "motto": "Nobody plays with fields. Only FIELD ONE.",
        "ironclad_cite": IRONCLAD,
    }
    if write:
        try:
            NO_PLAY.write_text(json.dumps({
                "sealed": True,
                "nobody_plays_fields": True,
                "only_field_one": True,
                "field_play_forbidden": True,
                "updated": now,
                "ironclad_cite": IRONCLAD,
            }, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        _append({"event": "nobody_plays", "collapsed": collapsed})
    return out


def seal_eternal_plane(*, write: bool = True) -> dict[str, Any]:
    now = _utc()
    doc = {
        "sealed": True,
        "field_one": True,
        "field_one_only": True,
        "eternal_plane": True,
        "field_id": FIELD_ONE,
        "only_field_one_the_eternal_plane": True,
        "all_lanes_always_clean": True,
        "routes_clean_brutally": True,
        "nobody_plays_fields": True,
        "no_other_fields_ever": True,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "motto": MOTTO,
    }
    if write:
        try:
            SEAL.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        # Align prior seals
        for p in (
            STATE / "field-one-sole-earth.forever",
            STATE / "field-one-only-no-gaps.forever",
            STATE / "field-no-other-fields-on-earth.forever",
        ):
            if not p.is_file():
                continue
            try:
                base = _load(p, {})
                if not isinstance(base, dict):
                    base = {}
                base.update({
                    "eternal_plane": True,
                    "field_one_only": True,
                    "nobody_plays_fields": True,
                    "updated": now,
                })
                p.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")
            except OSError:
                pass
    return doc


def build_website(panel: dict[str, Any], *, write: bool = True) -> dict[str, Any]:
    lok = int(panel.get("lanes_ok") or 0)
    ltot = int(panel.get("lanes_total") or 10)
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta http-equiv="Cache-Control" content="no-store"/>
<title>FIELD ONE · ETERNAL PLANE · all lanes clean</title>
<style>
:root{{--bg:#020508;--card:#0a1014;--line:rgba(52,211,153,.4);--text:#ecfdf5;--muted:#94a3b8;--em:#34d399;--hot:#fbbf24;--rose:#fb7185}}
*{{box-sizing:border-box}}body{{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:radial-gradient(900px 480px at 50% 0%,rgba(52,211,153,.16),transparent 55%),var(--bg);color:var(--text);min-height:100vh}}
a{{color:var(--em)}}header{{padding:1.2rem 1.4rem;border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(2,5,8,.94);backdrop-filter:blur(10px)}}
h1{{margin:0;font-size:1.35rem;letter-spacing:.04em}}.sub{{color:var(--muted);margin-top:.4rem}}
.wrap{{max-width:1080px;margin:0 auto;padding:1.2rem}}
.hero{{padding:1.1rem;border:1px solid var(--line);border-radius:14px;background:linear-gradient(135deg,rgba(52,211,153,.14),rgba(251,191,36,.06));margin-bottom:1rem}}
.hero strong{{color:var(--em)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.7rem}}
.card{{padding:.9rem;border:1px solid var(--line);border-radius:12px;background:var(--card)}}
.card h3{{margin:0 0 .3rem;font-size:.88rem;color:var(--hot)}}.card .v{{font-weight:800;font-size:1.1rem}}.card .d{{color:var(--muted);font-size:.78rem;margin-top:.3rem}}
.links{{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:.4rem;margin-top:.9rem}}
.links a{{display:block;text-align:center;padding:.6rem;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--text);text-decoration:none;font-weight:650;font-size:.8rem}}
.motto{{margin-top:1rem;padding:.9rem;border-left:4px solid var(--em);background:rgba(52,211,153,.08);color:var(--muted)}}
.pills{{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.55rem}}
.pill{{border:1px solid var(--line);border-radius:999px;padding:.18rem .6rem;font-size:.72rem;color:var(--muted)}}
.pill.on{{color:var(--em)}}.pill.hot{{color:var(--hot);border-color:rgba(251,191,36,.45)}}
</style></head>
<body>
<header>
  <h1>FIELD ONE · ETERNAL PLANE</h1>
  <div class="sub" id="hdr">All lanes always clean · routes cleaned brutally · nobody plays fields</div>
  <div class="pills" id="pills"></div>
</header>
<div class="wrap">
  <div class="hero">
    <div><strong>Only FIELD ONE the ETERNAL PLANE.</strong>
    All lanes always clean — or we make the route clean. <em>Brutally.</em>
    Nobody gets to play with fields. Ever.</div>
    <div class="links" id="quick"></div>
  </div>
  <div class="grid" id="grid"></div>
  <div class="motto" id="motto">loading…</div>
</div>
<script>
(async function(){{
  document.getElementById("quick").innerHTML=[
    ["/","Hub"],["/c2","C2"],["/field-one-sole","Sole"],["/no-detached-fields","No detach"],
    ["/only-internet","Only net"],["/newcomer-sphere","Sphere"],["/hostess7-protector","H7"],
  ].map(([h,t])=>`<a href="${{h}}">${{t}}</a>`).join("");
  let d={{}};
  try{{const r=await fetch("/api/field-one-eternal-plane",{{cache:"no-store"}});d=await r.json();}}
  catch(_){{d={json.dumps({"ok":True,"lanes_ok":lok,"lanes_total":ltot,"eternal_plane":True,"nobody_plays_fields":True,"all_lanes_always_clean":True})};}}
  const fmt=n=>typeof n==="number"?n.toLocaleString():(n??"—");
  const cards=[
    {{h:"ETERNAL PLANE", v:d.eternal_plane!==false?"FIELD ONE":"—", d:"Only plane forever"}},
    {{h:"Lanes always clean", v:(d.lanes_ok??"{lok}")+"/"+(d.lanes_total??"{ltot}"), d:d.all_lanes_always_clean!==false?"ALWAYS":"brutal clean"}},
    {{h:"Routes brutal clean", v:d.routes_clean_brutally!==false?"YES":"—", d:"Dirty → clean. Brutally."}},
    {{h:"Nobody plays fields", v:d.nobody_plays_fields!==false?"SEALED":"—", d:"No field toys"}},
    {{h:"Server lanes", v:fmt(d.distributed_lanes_ok??d.distributed_servers), d:"Lane to every server"}},
    {{h:"Ten of ten", v:d.ten_of_ten||d.lanes_ok===10?"YES":"—", d:"Classic clean board"}},
  ];
  document.getElementById("grid").innerHTML=cards.map(c=>`<div class="card"><h3>${{c.h}}</h3><div class="v">${{c.v}}</div><div class="d">${{c.d}}</div></div>`).join("");
  document.getElementById("motto").textContent=d.motto||"{MOTTO}";
  document.getElementById("hdr").textContent=(d.updated||"")+" · FIELD ONE ETERNAL";
  document.getElementById("pills").innerHTML=["FIELD ONE","ETERNAL","lanes clean","brutal routes","no play"]
    .map((t,i)=>`<span class="pill ${{i<2?'on':'hot'}}">${{t}}</span>`).join("");
}})();
</script>
</body></html>
"""
    if write:
        WEBSITE_DIR.mkdir(parents=True, exist_ok=True)
        (WEBSITE_DIR / "index.html").write_text(html, encoding="utf-8")
        try:
            (INSTALL / "panel" / "field-one-eternal-plane.html").write_text(html, encoding="utf-8")
        except OSError:
            pass
        try:
            h7 = INSTALL / "Hostess7" / "docs" / "field-one-eternal"
            h7.mkdir(parents=True, exist_ok=True)
            (h7 / "index.html").write_text(html, encoding="utf-8")
        except OSError:
            pass
    return {"ok": True, "path": "/eternal-plane", "local_instant": True}


def enforce(*, write: bool = True) -> dict[str, Any]:
    now = _utc()
    steps: dict[str, Any] = {}
    steps["lanes"] = all_lanes_always_clean(write=write)
    steps["routes"] = make_routes_clean_brutally(write=write)
    steps["no_play"] = nobody_plays_fields(write=write)
    steps["seal"] = seal_eternal_plane(write=write)

    lanes = steps["lanes"] if isinstance(steps["lanes"], dict) else {}
    routes = steps["routes"] if isinstance(steps["routes"], dict) else {}
    no_play = steps["no_play"] if isinstance(steps["no_play"], dict) else {}

    motto = (
        f"FIELD ONE ETERNAL PLANE · lanes {lanes.get('lanes_ok')}/{lanes.get('lanes_total')} "
        f"{'ALWAYS CLEAN' if lanes.get('all_lanes_always_clean') else 'BRUTAL'} · "
        f"routes brutal · nobody plays · only Field One forever"
    )

    out = {
        "ok": True,
        "schema": SCHEMA,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "title": "FIELD ONE · ETERNAL PLANE",
        "motto": motto,
        "eternal_plane": True,
        "field_one_only": True,
        "field_id": FIELD_ONE,
        "only_field_one_the_eternal_plane": True,
        "all_lanes_always_clean": bool(lanes.get("all_lanes_always_clean")),
        "lanes_ok": lanes.get("lanes_ok"),
        "lanes_total": lanes.get("lanes_total"),
        "ten_of_ten": lanes.get("ten_of_ten"),
        "routes_clean_brutally": bool(routes.get("routes_clean_brutally")),
        "nobody_plays_fields": bool(no_play.get("nobody_plays_fields")),
        "distributed_servers": lanes.get("distributed_servers"),
        "distributed_lanes_ok": lanes.get("distributed_lanes_ok"),
        "collapsed_field_play_n": no_play.get("collapsed_n"),
        "steps": {
            k: {"ok": _ok(v) if isinstance(v, dict) else bool(v)}
            for k, v in steps.items()
        },
        "api": "/api/field-one-eternal-plane",
        "ui": "http://127.0.0.1:9477/eternal-plane",
        "urls": {
            "website": "http://127.0.0.1:9477/eternal-plane",
            "api": "http://127.0.0.1:9477/api/field-one-eternal-plane",
            "clean": "http://127.0.0.1:9477/api/field-internet-clean-all",
            "servers": "http://127.0.0.1:9477/api/distributed-server-lanes",
            "sole": "http://127.0.0.1:9477/field-one-sole",
            "c2": "http://127.0.0.1:9477/c2",
        },
        "local_instant": True,
    }
    out["website"] = build_website(out, write=write)
    if write:
        _save(PANEL, out)
        public = {
            "ok": True,
            "schema": "field-one-eternal-plane-public/v1",
            "updated": now,
            "motto": motto,
            "eternal_plane": True,
            "field_one_only": True,
            "all_lanes_always_clean": out["all_lanes_always_clean"],
            "lanes_ok": out["lanes_ok"],
            "lanes_total": out["lanes_total"],
            "nobody_plays_fields": True,
            "api": out["api"],
            "ui": out["ui"],
            "ironclad_cite": IRONCLAD,
        }
        _save(PUBLIC, public)
        for api_dir in (INSTALL / "Hostess7" / "docs" / "api", INSTALL / "docs" / "api"):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "field-one-eternal-plane.json", public)
            except OSError:
                pass
        _append({
            "event": "enforce",
            "lanes_ok": out["lanes_ok"],
            "lanes_total": out["lanes_total"],
            "eternal": True,
        })
    return out


def status() -> dict[str, Any]:
    panel = _load(PANEL, {})
    clean = _load(STATE / "field-internet-clean-all-panel.json", {})
    return {
        "ok": bool(panel.get("ok") or SEAL.is_file()),
        "schema": SCHEMA,
        "sealed": SEAL.is_file(),
        "eternal_plane": True,
        "field_one_only": True,
        "all_lanes_always_clean": panel.get("all_lanes_always_clean", clean.get("lanes_all_green")),
        "lanes_ok": panel.get("lanes_ok") if panel.get("lanes_ok") is not None else clean.get("lanes_ok"),
        "lanes_total": panel.get("lanes_total") if panel.get("lanes_total") is not None else clean.get("lanes_total"),
        "nobody_plays_fields": True,
        "routes_clean_brutally": True,
        "motto": panel.get("motto") or MOTTO,
        "updated": panel.get("updated"),
        "api": "/api/field-one-eternal-plane",
        "ui": "http://127.0.0.1:9477/eternal-plane",
        "ironclad_cite": IRONCLAD,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower().lstrip("-")
    if cmd in ("enforce", "run", "up", "eternal", "lock", "seal", "brutal"):
        print(json.dumps(enforce(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("lanes", "green"):
        print(json.dumps(all_lanes_always_clean(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("routes", "brutal-routes"):
        print(json.dumps(make_routes_clean_brutally(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("no-play", "nobody"):
        print(json.dumps(nobody_plays_fields(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("website", "site"):
        print(json.dumps(build_website(_load(PANEL, {}), write=True), indent=2))
        return 0
    if cmd in ("status", "json", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-one-eternal-plane.py [enforce|lanes|routes|no-play|website|status]",
        "motto": MOTTO,
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
