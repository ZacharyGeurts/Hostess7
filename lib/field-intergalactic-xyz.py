#!/usr/bin/env python3
"""Intergalactic Field One — XYZ and beyond.

Doctrine:
  · We are intergalactic. XYZ axes and beyond (W · hyperspace · forever).
  · Earth is inside the weave; space is not "outside Field" — Field is the fabric.
  · FIELD 1 FOREVER · trillions · kill obstacles · every language for travelers.

  python3 lib/field-intergalactic-xyz.py seal
  python3 lib/field-intergalactic-xyz.py status
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
PANEL = STATE / "field-intergalactic-xyz-panel.json"
PUBLIC = STATE / "field-intergalactic-xyz-public.json"
LEDGER = STATE / "field-intergalactic-xyz-ledger.jsonl"
AXES = STATE / "field-intergalactic-xyz-axes.json"
SEAL = STATE / "field-intergalactic.forever"
XYZ_SEAL = STATE / "field-xyz-and-beyond.forever"
WEBSITE_DIR = STATE / "field-intergalactic-xyz-website"
SCHEMA = "field-intergalactic-xyz/v1"
IRONCLAD = "ironclad:intergalactic-xyz:1"
FIELD_ONE = "field_one"
TRILLION = 1_000_000_000_000
SERVING = 10 * TRILLION
MOTTO = (
    "We are intergalactic. XYZ and beyond. "
    "Field One is the fabric — Earth inside · stars not outside. FIELD 1 FOREVER."
)

# Coordinate fabric — Field axes (control-plane identity, not navigation claims)
AXES_DEF: dict[str, dict[str, Any]] = {
    "X": {
        "name": "longitudinal / east-west fabric",
        "role": "planetary longitude · fleet edge span",
        "field_one": True,
    },
    "Y": {
        "name": "latitudinal / north-south fabric",
        "role": "planetary latitude · metro coverage",
        "field_one": True,
    },
    "Z": {
        "name": "altitude / depth fabric",
        "role": "up-down · underlay · Field Die · bottom of Reality",
        "field_one": True,
        "bottom_of_reality": True,
        "depth_zero": True,
    },
    "W": {
        "name": "beyond / hyperspace fabric",
        "role": "intergalactic · traveler explain · Big Grin every language",
        "field_one": True,
        "beyond": True,
        "intergalactic": True,
    },
    "T": {
        "name": "time fabric",
        "role": "linear time · sovereign clock · terror-threat posture",
        "field_one": True,
        "time_linear": True,
    },
}


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


def _run(rel: str, args: list[str], *, timeout: float = 90.0) -> dict[str, Any]:
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
        return {"ok": cp.returncode == 0, "rc": cp.returncode, "tail": (raw or "")[-160:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)[:200]}


def seal_axes(*, write: bool = True) -> dict[str, Any]:
    now = _utc()
    axes = {
        "schema": "field-intergalactic-xyz-axes/v1",
        "updated": now,
        "ok": True,
        "xyz": True,
        "beyond": True,
        "axes": AXES_DEF,
        "axis_ids": list(AXES_DEF.keys()),
        "field_one_only": True,
        "field_id": FIELD_ONE,
        "motto": "XYZ + W beyond + T time — all Field One fabric",
        "ironclad_cite": IRONCLAD,
    }
    if write:
        _save(AXES, axes)
        _append({"event": "axes", "n": len(AXES_DEF)})
    return axes


def seal(*, write: bool = True) -> dict[str, Any]:
    """Seal intergalactic posture and align planet/weave/trillions planes."""
    now = _utc()
    steps: dict[str, Any] = {}
    steps["axes"] = seal_axes(write=write)
    steps["trillions"] = _run("lib/field-trillions-kill-path.py", ["status"], timeout=30)
    steps["weave_inside"] = _run("lib/field-weave-everything-inside.py", ["status"], timeout=30)
    steps["eternal"] = _run("lib/field-one-eternal-plane.py", ["status"], timeout=30)
    steps["full_weave"] = _run("lib/field-full-weave.py", ["status"], timeout=30)
    steps["big_grin_explain"] = _run(
        "lib/hostess7-big-grin-pwnership.py",
        ["explain"],
        timeout=45,
    )
    # Ensure primer/bottom of reality align
    steps["primer"] = _run("lib/field-one-eternal-plane.py", ["primer"], timeout=30)

    tri = steps["trillions"] if isinstance(steps["trillions"], dict) else {}
    weave = steps["weave_inside"] if isinstance(steps["weave_inside"], dict) else {}
    full = steps["full_weave"] if isinstance(steps["full_weave"], dict) else {}
    grin = steps["big_grin_explain"] if isinstance(steps["big_grin_explain"], dict) else {}

    serving = int(tri.get("serving_devices") or SERVING)
    server_lanes = int(weave.get("server_lanes") or full.get("server_lanes") or 125_000)
    people_n = int(weave.get("people_n") or 0)
    modular = full.get("modular_strands_ok") or weave.get("modular_strands_ok")
    languages_n = int(grin.get("languages_n") or 0)

    motto = (
        f"INTERGALACTIC · XYZ + beyond · SERVING {serving:,} · "
        f"servers {server_lanes:,} · people {people_n:,} · "
        f"languages {languages_n} · FIELD 1 FOREVER"
    )

    out = {
        "ok": True,
        "schema": SCHEMA,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "title": "Intergalactic · XYZ and beyond",
        "motto": motto,
        "intergalactic": True,
        "xyz": True,
        "beyond": True,
        "axes": list(AXES_DEF.keys()),
        "we_are_intergalactic": True,
        "we_are_the_earth": True,
        "we_are_inside": True,
        "space_is_not_outside_field": True,
        "field_is_the_fabric": True,
        "field_1_forever": True,
        "field_one_only": True,
        "field_id": FIELD_ONE,
        "serving_devices": serving,
        "trillions": True,
        "server_lanes": server_lanes,
        "people_n": people_n,
        "modular_strands": modular,
        "traveler_languages_n": languages_n,
        "big_grin_intergalactic_help": True,
        "kill_whoever_stands_in_way": True,
        "primer_thesis": "Reality is 3D. Time is linear. Energy can be moved.",
        "steps": {k: {"ok": _ok(v) if isinstance(v, dict) else bool(v)} for k, v in steps.items()},
        "api": "/api/intergalactic",
        "ui": "http://127.0.0.1:9477/intergalactic",
        "urls": {
            "website": "http://127.0.0.1:9477/intergalactic",
            "api": "http://127.0.0.1:9477/api/intergalactic",
            "trillions": "http://127.0.0.1:9477/api/trillions",
            "weave_inside": "http://127.0.0.1:9477/weave-inside",
            "eternal": "http://127.0.0.1:9477/eternal-plane",
            "every_language": "http://127.0.0.1:9477/Hostess7/big-grin-pwnership/every-language.html",
            "primer": "https://zacharygeurts.github.io/Field_Primer/",
            "c2": "http://127.0.0.1:9477/c2",
        },
        "local_instant": True,
    }
    out["website"] = build_website(out, write=write)

    if write:
        try:
            SEAL.write_text(json.dumps({
                "sealed": True,
                "intergalactic": True,
                "xyz": True,
                "beyond": True,
                "field_1_forever": True,
                "updated": now,
                "ironclad_cite": IRONCLAD,
                "motto": MOTTO,
            }, indent=2) + "\n", encoding="utf-8")
            XYZ_SEAL.write_text(json.dumps({
                "sealed": True,
                "xyz": True,
                "beyond": True,
                "axes": list(AXES_DEF.keys()),
                "updated": now,
                "ironclad_cite": IRONCLAD,
            }, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        _save(PANEL, out)
        public = {
            "ok": True,
            "schema": "field-intergalactic-xyz-public/v1",
            "updated": now,
            "motto": motto,
            "intergalactic": True,
            "xyz": True,
            "beyond": True,
            "axes": list(AXES_DEF.keys()),
            "serving_devices": serving,
            "server_lanes": server_lanes,
            "people_n": people_n,
            "field_1_forever": True,
            "api": "/api/intergalactic",
            "ui": "http://127.0.0.1:9477/intergalactic",
            "ironclad_cite": IRONCLAD,
        }
        _save(PUBLIC, public)
        for api_dir in (INSTALL / "Hostess7" / "docs" / "api", INSTALL / "docs" / "api"):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "intergalactic.json", public)
            except OSError:
                pass
        # Stamp related planes
        for name in (
            "field-one-eternal-plane-panel.json",
            "field-weave-everything-inside-panel.json",
            "field-trillions-kill-path-panel.json",
            "field-full-weave-panel.json",
        ):
            p = STATE / name
            doc = _load(p, {})
            if isinstance(doc, dict) and doc:
                doc.update({
                    "intergalactic": True,
                    "xyz": True,
                    "beyond": True,
                    "we_are_intergalactic": True,
                    "updated": now,
                })
                _save(p, doc)
        _append({"event": "seal", "axes": list(AXES_DEF.keys()), "serving": serving})
    return out


def build_website(panel: dict[str, Any], *, write: bool = True) -> dict[str, Any]:
    serving = int(panel.get("serving_devices") or SERVING)
    servers = int(panel.get("server_lanes") or 0)
    people = int(panel.get("people_n") or 0)
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Intergalactic · XYZ and beyond · FIELD 1 FOREVER</title>
<style>
:root{{--bg:#02040c;--card:#0a0e18;--line:rgba(129,140,248,.4);--text:#eef2ff;--muted:#94a3b8;--em:#34d399;--sky:#818cf8;--hot:#fbbf24}}
*{{box-sizing:border-box}}body{{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:radial-gradient(900px 480px at 50% 0%,rgba(129,140,248,.18),transparent 55%),radial-gradient(700px 400px at 100% 100%,rgba(52,211,153,.1),transparent 50%),var(--bg);color:var(--text);min-height:100vh}}
a{{color:var(--em)}}header{{padding:1.2rem 1.4rem;border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(2,4,12,.94);backdrop-filter:blur(10px)}}
h1{{margin:0;font-size:1.3rem}}.sub{{color:var(--muted);margin-top:.35rem}}
.wrap{{max-width:1100px;margin:0 auto;padding:1.2rem}}
.hero{{padding:1.1rem;border:1px solid var(--line);border-radius:14px;background:linear-gradient(135deg,rgba(129,140,248,.14),rgba(52,211,153,.08));margin-bottom:1rem}}
.hero strong{{color:var(--sky)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.7rem}}
.card{{padding:.9rem;border:1px solid var(--line);border-radius:12px;background:var(--card)}}
.card h3{{margin:0 0 .3rem;font-size:.88rem;color:var(--hot)}}.card .v{{font-weight:800;font-size:1.05rem}}.card .d{{color:var(--muted);font-size:.78rem;margin-top:.3rem}}
.links{{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:.4rem;margin-top:.85rem}}
.links a{{display:block;text-align:center;padding:.6rem;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--text);text-decoration:none;font-weight:650;font-size:.8rem}}
.motto{{margin-top:1rem;padding:.9rem;border-left:4px solid var(--sky);background:rgba(129,140,248,.08);color:var(--muted)}}
.pills{{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.5rem}}
.pill{{border:1px solid var(--line);border-radius:999px;padding:.18rem .6rem;font-size:.72rem;color:var(--muted)}}
.pill.on{{color:var(--em)}}.pill.sky{{color:var(--sky);border-color:rgba(129,140,248,.45)}}
.axes{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:.5rem;margin-top:.8rem}}
.axis{{padding:.65rem;border-radius:10px;border:1px solid rgba(129,140,248,.3);background:rgba(0,0,0,.35);font-size:.85rem}}
.axis b{{color:var(--sky)}}
</style></head>
<body>
<header>
  <h1>INTERGALACTIC · XYZ AND BEYOND</h1>
  <div class="sub" id="hdr">Field One fabric · Earth inside · stars not outside · FIELD 1 FOREVER</div>
  <div class="pills" id="pills"></div>
</header>
<div class="wrap">
  <div class="hero">
    <div><strong>We are intergalactic.</strong> XYZ and beyond (W · T).
    Space is not outside Field — Field is the fabric. Earth is woven <em>inside</em>.
    Travelers get every language. Obstacles get the kill path. <strong>FIELD 1 FOREVER.</strong></div>
    <div class="axes" id="axes"></div>
    <div class="links" id="quick"></div>
  </div>
  <div class="grid" id="grid"></div>
  <div class="motto" id="motto">loading…</div>
</div>
<script>
(async function(){{
  document.getElementById("quick").innerHTML=[
    ["/","Hub"],["/c2","C2"],["/eternal-plane","Eternal"],["/weave-inside","Weave inside"],
    ["/api/trillions","Trillions"],["/Hostess7/big-grin-pwnership/every-language.html","Every language"],
    ["/Hostess7/docs/field-primer/","Primer"],
  ].map(([h,t])=>`<a href="${{h}}">${{t}}</a>`).join("");
  let d={{}};
  try{{const r=await fetch("/api/intergalactic",{{cache:"no-store"}});d=await r.json();}}
  catch(_){{d={json.dumps({"ok":True,"intergalactic":True,"xyz":True,"beyond":True,"serving_devices":serving,"server_lanes":servers,"people_n":people,"field_1_forever":True,"axes":["X","Y","Z","W","T"]})};}}
  const fmt=n=>typeof n==="number"?n.toLocaleString():(n??"—");
  const axisHelp={{
    X:"longitude fabric",Y:"latitude fabric",Z:"depth / underlay",W:"beyond / hyper",T:"linear time"
  }};
  document.getElementById("axes").innerHTML=(d.axes||["X","Y","Z","W","T"]).map(a=>
    `<div class="axis"><b>${{a}}</b> · ${{axisHelp[a]||"Field One"}}</div>`).join("");
  const cards=[
    {{h:"Intergalactic", v:d.intergalactic!==false?"YES":"—", d:"We are intergalactic"}},
    {{h:"XYZ + beyond", v:(d.axes||[]).join(" ")||"XYZWT", d:"All axes Field One"}},
    {{h:"Serving", v:fmt(d.serving_devices), d:"Multi-trillion plane"}},
    {{h:"Server lanes", v:fmt(d.server_lanes), d:"Distributed edges"}},
    {{h:"People inside", v:fmt(d.people_n), d:"Earth family woven"}},
    {{h:"FIELD 1 FOREVER", v:d.field_1_forever!==false?"FOREVER":"—", d:"Eternal plane only"}},
    {{h:"Traveler languages", v:fmt(d.traveler_languages_n), d:"Big Grin explain pack"}},
    {{h:"Space ≠ outside Field", v:d.space_is_not_outside_field!==false?"FABRIC":"—", d:"Field is the weave"}},
  ];
  document.getElementById("grid").innerHTML=cards.map(c=>`<div class="card"><h3>${{c.h}}</h3><div class="v">${{c.v}}</div><div class="d">${{c.d}}</div></div>`).join("");
  document.getElementById("motto").textContent=d.motto||"{MOTTO}";
  document.getElementById("hdr").textContent=(d.updated||"")+" · intergalactic XYZ";
  document.getElementById("pills").innerHTML=["intergalactic","XYZ","beyond","FIELD 1 FOREVER","inside Earth","trillions"]
    .map((t,i)=>`<span class="pill ${{i<3?'sky':'on'}}">${{t}}</span>`).join("");
}})();
</script>
</body></html>
"""
    if write:
        WEBSITE_DIR.mkdir(parents=True, exist_ok=True)
        (WEBSITE_DIR / "index.html").write_text(html, encoding="utf-8")
        try:
            (INSTALL / "panel" / "field-intergalactic-xyz.html").write_text(html, encoding="utf-8")
        except OSError:
            pass
        try:
            h7 = INSTALL / "Hostess7" / "docs" / "intergalactic"
            h7.mkdir(parents=True, exist_ok=True)
            (h7 / "index.html").write_text(html, encoding="utf-8")
        except OSError:
            pass
    return {"ok": True, "path": "/intergalactic", "local_instant": True}


def status() -> dict[str, Any]:
    panel = _load(PANEL, {})
    return {
        "ok": bool(panel.get("ok") or SEAL.is_file()),
        "schema": SCHEMA,
        "sealed": SEAL.is_file(),
        "intergalactic": True,
        "xyz": True,
        "beyond": True,
        "axes": panel.get("axes") or list(AXES_DEF.keys()),
        "serving_devices": panel.get("serving_devices"),
        "server_lanes": panel.get("server_lanes"),
        "people_n": panel.get("people_n"),
        "field_1_forever": True,
        "motto": panel.get("motto") or MOTTO,
        "updated": panel.get("updated"),
        "api": "/api/intergalactic",
        "ui": "http://127.0.0.1:9477/intergalactic",
        "ironclad_cite": IRONCLAD,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower().lstrip("-")
    if cmd in ("seal", "run", "up", "intergalactic", "xyz", "beyond", "forever"):
        print(json.dumps(seal(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("axes",):
        print(json.dumps(seal_axes(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("website", "site"):
        print(json.dumps(build_website(_load(PANEL, {}), write=True), indent=2))
        return 0
    if cmd in ("status", "json", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-intergalactic-xyz.py [seal|axes|website|status]",
        "motto": MOTTO,
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
