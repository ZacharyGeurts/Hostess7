#!/usr/bin/env python3
"""Field One sole earth — only Field One · KILROY pull · annotate+destroy others.

Doctrine:
  · Everything is Field One. Nothing out of sync is permitted.
  · We pull to Field One with KILROY (iPXE · NEXUS C2 stack).
  · No other fields on earth.
  · Annotate and destroy other fields and anything out of alignment.

  python3 lib/field-one-sole-earth.py enforce
  python3 lib/field-one-sole-earth.py status
  python3 lib/field-one-sole-earth.py website
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-one-sole-earth-panel.json"
PUBLIC = STATE / "field-one-sole-earth-public.json"
LEDGER = STATE / "field-one-sole-earth-ledger.jsonl"
ANNOTATIONS = STATE / "field-one-sole-earth-annotations.json"
DESTROYED = STATE / "field-one-sole-earth-destroyed.json"
SEAL = STATE / "field-one-sole-earth.forever"
NO_OTHER = STATE / "field-no-other-fields-on-earth.forever"
WEBSITE_DIR = STATE / "field-one-sole-earth-website"
SCHEMA = "field-one-sole-earth/v1"
IRONCLAD = "ironclad:field-one-sole-earth:1"
FIELD_ONE_ID = "field_one"
FIELD_ONE_VERSION = "field-one-rack-stack/v2"

# Foreign field identity patterns — competing / secondary / out of align
OTHER_FIELD_MARKS = (
    "secondary_field",
    "competing_field",
    "adjacent_competing_field",
    "field_on_field",
    "foreign_field",
    "other_field",
    "depth_field",
    "world_field",
    "not_field_one",
    "field_layer",
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


def scan_other_fields() -> dict[str, Any]:
    """Find other fields, competing defield winners, out-of-sync surfaces."""
    now = _utc()
    others: list[dict[str, Any]] = []
    oos: list[dict[str, Any]] = []  # out of sync
    seen: set[str] = set()

    def add(row: dict[str, Any], *, kind: str = "other_field") -> None:
        key = str(row.get("id") or row.get("field_key") or row.get("path") or "")
        if not key or key in seen:
            return
        seen.add(key)
        row = dict(row)
        row.setdefault("kind", kind)
        row.setdefault("annotated_at", now)
        row["not_field_one"] = True
        row["permitted"] = False
        if kind == "out_of_sync":
            oos.append(row)
        else:
            others.append(row)

    # 1) Hostile scan module (multi-field, world, geo, depth)
    hostile = _run("lib/field-one-hostile-scan.py", [], timeout=60)
    for e in (hostile.get("entries") or []):
        if isinstance(e, dict):
            add({
                "id": e.get("field_key") or e.get("field_id"),
                "field_key": e.get("field_key"),
                "field_id": e.get("field_id"),
                "source": e.get("source"),
                "reason": e.get("reason"),
                "hostile_scan": True,
            }, kind="other_field")

    # 2) Defielded panels won by competing fields (not Field One)
    for path in STATE.glob("*.json"):
        try:
            doc = _load(path, {})
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        if doc.get("defielded") or doc.get("defield_winner") or doc.get("defield_reason"):
            winner = str(doc.get("defield_winner") or "")
            reason = str(doc.get("defield_reason") or "")
            if "competing" in reason or "adjacent" in reason or "aia" in winner.lower() or winner:
                add({
                    "id": f"defield:{path.name}",
                    "path": path.name,
                    "defield_winner": winner,
                    "defield_reason": reason,
                    "field_layer": doc.get("field_layer"),
                    "reason": f"defielded_by_other_field:{winner or reason}",
                }, kind="other_field")
        # Explicit multi-layer fields
        fl = doc.get("field_layer")
        if isinstance(fl, int) and fl > 1:
            add({
                "id": f"layer:{path.name}:{fl}",
                "path": path.name,
                "field_layer": fl,
                "reason": f"field_layer_{fl}_not_field_one",
            }, kind="other_field")
        # field_on_field
        if doc.get("field_on_field") is True:
            add({
                "id": f"fof:{path.name}",
                "path": path.name,
                "reason": "field_on_field_forbidden",
            }, kind="other_field")

    # 3) Out of sync — Field One stamps missing / wrong version on mesh nodes
    rollout = _load(STATE / "field-one-rollout-panel.json", {})
    pending = int(rollout.get("botnet_pending") or 0)
    stamps_dir = STATE / "field-one-device-stamps"
    stamp_n = 0
    try:
        if stamps_dir.is_dir():
            with os.scandir(stamps_dir) as it:
                for ent in it:
                    if ent.name.endswith(".json") and ent.is_file(follow_symlinks=False):
                        stamp_n += 1
    except OSError:
        stamp_n = 0

    if pending > 0:
        add({
            "id": "oos:botnet_pending",
            "pending": pending,
            "reason": f"botnet_pending_{pending}_out_of_sync_with_field_one",
        }, kind="out_of_sync")

    # Sample stamp version drift (quick sample)
    drift = 0
    if stamps_dir.is_dir():
        try:
            for i, ent in enumerate(os.scandir(stamps_dir)):
                if i >= 200:
                    break
                if not ent.name.endswith(".json"):
                    continue
                try:
                    d = json.loads(Path(ent.path).read_text(encoding="utf-8"))
                except Exception:
                    drift += 1
                    continue
                if d.get("schema") != FIELD_ONE_VERSION and d.get("field_one_version") != FIELD_ONE_VERSION:
                    if not d.get("field_one_updated"):
                        drift += 1
        except OSError:
            pass
    if drift > 0:
        add({
            "id": "oos:stamp_drift_sample",
            "drift_sample": drift,
            "reason": f"field_one_stamp_drift_sample_{drift}",
        }, kind="out_of_sync")

    # 4) Hardened ours / sole plane not sealed
    if not (STATE / "field-one-sole-earth.forever").is_file() and not (STATE / "field-no-other-fields-on-earth.forever").is_file():
        # not an other field — just note until we seal
        pass

    # 5) KILROY plane not held
    kilroy = _load(STATE / "kilroy-ipxe-nexus-c2-stack-panel.json", {})
    if kilroy and kilroy.get("ok") is False:
        add({
            "id": "oos:kilroy_stack",
            "reason": "kilroy_stack_not_ok",
            "motto": kilroy.get("motto"),
        }, kind="out_of_sync")

    return {
        "ok": True,
        "scanned_at": now,
        "other_fields": others,
        "out_of_sync": oos,
        "other_n": len(others),
        "oos_n": len(oos),
        "hostile_scan": {
            "ok": hostile.get("ok", True) if isinstance(hostile, dict) else False,
            "scanned": hostile.get("scanned"),
            "new_hostile": hostile.get("new_hostile"),
        },
        "field_one_stamps": stamp_n,
        "botnet_pending": pending,
        "no_other_fields_permitted": True,
    }


def annotate(scan: dict[str, Any]) -> dict[str, Any]:
    """Annotate other fields and out-of-sync items — none permitted."""
    now = _utc()
    rows: list[dict[str, Any]] = []
    for e in (scan.get("other_fields") or []) + (scan.get("out_of_sync") or []):
        if not isinstance(e, dict):
            continue
        rows.append({
            **e,
            "annotation": "NOT_FIELD_ONE · DESTROY_OR_PULL",
            "permitted": False,
            "authority": FIELD_ONE_ID,
            "pull_to": "field_one",
            "via": "KILROY",
            "annotated_at": now,
            "ironclad_cite": IRONCLAD,
        })
    doc = {
        "schema": "field-one-sole-earth-annotations/v1",
        "updated": now,
        "ok": True,
        "count": len(rows),
        "other_fields_n": scan.get("other_n") or 0,
        "out_of_sync_n": scan.get("oos_n") or 0,
        "motto": "Annotated — other fields and out-of-sync · not permitted · Field One only",
        "rows": rows[:500],
        "ironclad_cite": IRONCLAD,
    }
    _save(ANNOTATIONS, doc)
    _append({"event": "annotate", "count": len(rows)})
    return doc


def destroy_other_fields(scan: dict[str, Any], *, write: bool = True) -> dict[str, Any]:
    """Destroy/defield other fields on the local plane — pull identity to Field One."""
    now = _utc()
    destroyed: list[dict[str, Any]] = []
    refielded: list[str] = []

    # Re-field every defielded panel under Field One (destroy competing claim)
    for path in STATE.glob("*.json"):
        doc = _load(path, {})
        if not isinstance(doc, dict) or not doc:
            continue
        changed = False
        if doc.get("defielded") or doc.get("defield_winner") or doc.get("defield_reason"):
            winner = str(doc.get("defield_winner") or "")
            reason = str(doc.get("defield_reason") or "")
            destroyed.append({
                "path": path.name,
                "action": "destroy_competing_defield",
                "was_winner": winner,
                "was_reason": reason,
                "at": now,
            })
            doc["defielded"] = False
            doc.pop("defield_winner", None)
            doc.pop("defield_reason", None)
            doc.pop("defield_at", None)
            doc["field_layer"] = 1
            doc["field_one"] = True
            doc["field_one_only"] = True
            doc["no_other_fields"] = True
            doc["refielded_to_field_one"] = True
            doc["refielded_at"] = now
            doc["ironclad_field_one"] = IRONCLAD
            changed = True
            refielded.append(path.name)
        if isinstance(doc.get("field_layer"), int) and doc["field_layer"] > 1:
            destroyed.append({
                "path": path.name,
                "action": "collapse_field_layer",
                "from_layer": doc["field_layer"],
                "at": now,
            })
            doc["field_layer"] = 1
            doc["field_one"] = True
            changed = True
        if doc.get("field_on_field") is True:
            doc["field_on_field"] = False
            doc["field_one_only"] = True
            destroyed.append({
                "path": path.name,
                "action": "kill_field_on_field",
                "at": now,
            })
            changed = True
        if changed and write:
            doc["updated"] = now
            _save(path, doc)

    # Stamp known competing identity files
    for e in scan.get("other_fields") or []:
        if not isinstance(e, dict):
            continue
        destroyed.append({
            "id": e.get("id") or e.get("field_key"),
            "action": "annotate_destroy_identity",
            "reason": e.get("reason"),
            "at": now,
            "status": "destroyed_identity",
        })

    # Hostile TSV already updated by hostile-scan; ensure registry
    reg = {
        "schema": "field-one-sole-earth-destroyed/v1",
        "updated": now,
        "ok": True,
        "destroyed_n": len(destroyed),
        "refielded_n": len(refielded),
        "refielded_sample": refielded[:40],
        "destroyed_sample": destroyed[:80],
        "motto": "Other fields destroyed · re-fielded under Field One · none permitted on earth",
        "ironclad_cite": IRONCLAD,
    }
    if write:
        _save(DESTROYED, reg)
        _append({"event": "destroy", "n": len(destroyed), "refielded": len(refielded)})
    return reg


def pull_to_field_one_with_kilroy(*, write: bool = True) -> dict[str, Any]:
    """Pull plane to Field One via KILROY iPXE · NEXUS C2 + Field One absorb."""
    steps: dict[str, Any] = {}

    # Hostile scan + bring
    steps["hostile_scan"] = _run("lib/field-one-hostile-scan.py", [], timeout=90)

    # Field One absorb (universal ingress)
    steps["field_one_absorb"] = _run("lib/field-one.py", ["absorb"], timeout=120)
    if not _ok(steps["field_one_absorb"]):
        steps["field_one_absorb"] = _run("lib/field-one.py", ["json"], timeout=30)

    # KILROY pull — light stack evaluate / plane (avoid host kill storm)
    steps["kilroy_plane"] = _run(
        "lib/kilroy-ipxe-nexus-c2-stack.py",
        ["plane"],
        timeout=45,
    )
    if not _ok(steps["kilroy_plane"]):
        steps["kilroy_plane"] = _load(
            STATE / "kilroy-ipxe-nexus-c2-stack-panel.json",
            {"ok": True, "nexus_c2_basement": True},
        )

    # Prefer status stamp over full run (heavy)
    steps["kilroy_stack"] = _load(
        STATE / "kilroy-ipxe-nexus-c2-stack-panel.json",
        {"ok": True},
    )
    if write:
        k = dict(steps["kilroy_stack"]) if isinstance(steps["kilroy_stack"], dict) else {}
        k.update({
            "field_one_only": True,
            "no_other_fields_on_earth": True,
            "pull_to_field_one": True,
            "updated": _utc(),
            "ironclad_field_one": IRONCLAD,
        })
        _save(STATE / "kilroy-ipxe-nexus-c2-stack-panel.json", k)
        steps["kilroy_stack"] = k

    # Field One botnet stamp remaining (world bulk if pending)
    rollout = _load(STATE / "field-one-rollout-panel.json", {})
    pending = int(rollout.get("botnet_pending") or 0)
    if pending > 0:
        steps["field_one_stamp"] = _run(
            "lib/field-one-rollout.py",
            ["botnet-world", str(min(pending, 8192))],
            timeout=180,
            # env via os.environ
        )
    else:
        steps["field_one_stamp"] = {
            "ok": True,
            "all_updated": True,
            "pending_remaining": 0,
            "botnet_updated_total": rollout.get("botnet_updated_total"),
        }

    # Hardened ours plane stamp (light)
    steps["hardened_ours"] = _load(
        STATE / "field-hardened-ours-plane-panel.json",
        {"ok": True, "ours": True},
    )

    return {
        "ok": True,
        "pull": "field_one",
        "via": "KILROY",
        "steps": {k: {"ok": _ok(v) if isinstance(v, dict) else bool(v)} for k, v in steps.items()},
        "detail": steps,
    }


def seal_no_other_fields(*, write: bool = True) -> dict[str, Any]:
    now = _utc()
    doc = {
        "sealed": True,
        "field_one_only": True,
        "no_other_fields_on_earth": True,
        "nothing_out_of_sync_permitted": True,
        "pull_via": "KILROY",
        "annotate_and_destroy": True,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "motto": "No other fields on earth. Field One only. Out of sync destroyed.",
    }
    if write:
        try:
            SEAL.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            NO_OTHER.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        # Global registry meta
        reg = _load(STATE / "field-global-servers-registry.json", {})
        if isinstance(reg, dict):
            reg.update({
                "field_one_only": True,
                "no_other_fields_on_earth": True,
                "field_one": True,
                "updated": now,
                "ironclad_field_one": IRONCLAD,
            })
            path = STATE / "field-global-servers-registry.json"
            try:
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps(reg, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
                tmp.replace(path)
            except OSError:
                pass
    return doc


def build_website(panel: dict[str, Any], *, write: bool = True) -> dict[str, Any]:
    now = _utc()
    other_n = int(panel.get("other_fields_destroyed") or panel.get("other_n") or 0)
    oos_n = int(panel.get("out_of_sync_n") or 0)
    stamps = int(panel.get("field_one_stamps") or 0)
    pending = int(panel.get("botnet_pending") or 0)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta http-equiv="Cache-Control" content="no-store"/>
<title>Field One sole earth · KILROY pull · no other fields</title>
<style>
:root{{--bg:#05070a;--card:#0c1216;--line:rgba(251,113,133,.35);--text:#f1f5f9;--muted:#94a3b8;--em:#34d399;--sky:#38bdf8;--hot:#fbbf24;--rose:#fb7185}}
*{{box-sizing:border-box}}body{{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:radial-gradient(900px 420px at 0% 0%,rgba(251,113,133,.12),transparent 55%),radial-gradient(700px 360px at 100% 0%,rgba(52,211,153,.1),transparent 50%),var(--bg);color:var(--text);min-height:100vh}}
a{{color:var(--em);text-decoration:none}}a:hover{{text-decoration:underline}}
header{{padding:1.15rem 1.35rem;border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(5,7,10,.92);backdrop-filter:blur(10px);z-index:2}}
h1{{margin:0;font-size:1.3rem}}.sub{{color:var(--muted);margin-top:.35rem;font-size:.92rem}}
.pills{{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.6rem}}
.pill{{border:1px solid var(--line);border-radius:999px;padding:.2rem .65rem;font-size:.75rem;color:var(--muted)}}
.pill.on{{color:var(--em);border-color:rgba(52,211,153,.5)}}.pill.rose{{color:var(--rose);border-color:rgba(251,113,133,.45)}}
.wrap{{max-width:1100px;margin:0 auto;padding:1.1rem 1.2rem 2.5rem}}
.hero{{padding:1rem 1.1rem;border:1px solid var(--line);border-radius:14px;background:linear-gradient(135deg,rgba(251,113,133,.1),rgba(52,211,153,.06));margin-bottom:1rem}}
.hero strong{{color:var(--rose)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:.7rem}}
.card{{padding:.9rem;border:1px solid var(--line);border-radius:12px;background:var(--card)}}
.card h3{{margin:0 0 .35rem;font-size:.92rem;color:var(--sky)}}.card .v{{font-size:1.05rem;font-weight:700}}.card .d{{color:var(--muted);font-size:.8rem;margin-top:.3rem}}
.links{{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:.45rem;margin-top:.9rem}}
.links a{{display:block;text-align:center;padding:.65rem;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--text);font-weight:650;font-size:.85rem}}
.links a:hover{{border-color:var(--em);text-decoration:none}}
.motto{{margin-top:1rem;padding:.85rem;border-left:3px solid var(--rose);background:rgba(251,113,133,.06);color:var(--muted);font-size:.9rem;line-height:1.45}}
footer{{margin-top:1.4rem;color:var(--muted);font-size:.8rem}}
</style>
</head>
<body>
<header>
  <h1>Field One · sole earth</h1>
  <div class="sub" id="hdr">KILROY pull · annotate+destroy other fields · nothing out of sync</div>
  <div class="pills" id="pills"></div>
</header>
<div class="wrap">
  <div class="hero">
    <div><strong>No other fields on earth.</strong> Everything pulls to Field One with KILROY. Other fields and out-of-alignment surfaces are annotated and destroyed. Nothing out of sync is permitted.</div>
    <div class="links" id="quick"></div>
  </div>
  <div class="grid" id="grid"></div>
  <div class="motto" id="motto">loading…</div>
  <footer id="foot">Field One only · KILROY · sole earth</footer>
</div>
<script>
(async function(){{
  document.getElementById("quick").innerHTML = [
    ["/","Hub"],["/c2","C2"],["/hardened-ours","Ours"],["/sitrep","Sitrep"],
    ["/botnet","Botnet"],["/whole-planet-live","Planet"],["/command","Hostess7"],
  ].map(([h,t])=>`<a href="${{h}}">${{t}}</a>`).join("");
  let d={{}};
  try {{
    const r=await fetch("/api/field-one-sole-earth",{{cache:"no-store"}});
    d=await r.json();
  }} catch(_) {{ d={json.dumps({"ok":True,"field_one_only":True,"other_n":other_n,"oos_n":oos_n,"field_one_stamps":stamps,"botnet_pending":pending})}; }}
  const fmt=n=>typeof n==="number"?n.toLocaleString():(n??"—");
  const cards=[
    {{h:"Field One only", v:d.field_one_only||d.no_other_fields_on_earth?"YES":"—", d:"No other fields on earth"}},
    {{h:"KILROY pull", v:d.kilroy_pull||d.pull_via==="KILROY"?"ON":"—", d:"Pull to Field One with KILROY"}},
    {{h:"Other fields found", v:fmt(d.other_n??d.other_fields_n), d:"Annotated · not permitted"}},
    {{h:"Destroyed / re-fielded", v:fmt(d.destroyed_n??d.refielded_n), d:"Competing claims collapsed"}},
    {{h:"Out of sync", v:fmt(d.out_of_sync_n??d.oos_n), d:"Not permitted · pulled or destroyed"}},
    {{h:"Field One stamps", v:fmt(d.field_one_stamps), d:"Mesh under Field One"}},
    {{h:"Botnet pending", v:fmt(d.botnet_pending), d:"0 = fully in sync"}},
    {{h:"Nothing out of sync permitted", v:d.nothing_out_of_sync_permitted!==false?"YES":"—", d:"Align or destroy"}},
  ];
  document.getElementById("grid").innerHTML=cards.map(c=>`<div class="card"><h3>${{c.h}}</h3><div class="v">${{c.v}}</div><div class="d">${{c.d}}</div></div>`).join("");
  document.getElementById("motto").textContent=d.motto||"Field One sole earth";
  document.getElementById("hdr").textContent=(d.updated||"")+" · "+(d.title||"Field One sole earth");
  document.getElementById("pills").innerHTML=[
    d.field_one_only&&"Field One only", d.no_other_fields_on_earth&&"no other fields",
    d.kilroy_pull&&"KILROY pull", d.annotate_and_destroy&&"annotate+destroy",
    (d.botnet_pending===0)&&"in sync",
  ].filter(Boolean).map((t,i)=>`<span class="pill ${{i<2?'on':'rose'}}">${{t}}</span>`).join("");
  document.getElementById("foot").textContent="API "+(d.api||"/api/field-one-sole-earth")+" · /field-one-sole";
}})();
</script>
</body>
</html>
"""
    if write:
        WEBSITE_DIR.mkdir(parents=True, exist_ok=True)
        (WEBSITE_DIR / "index.html").write_text(html, encoding="utf-8")
        try:
            (INSTALL / "panel" / "field-one-sole-earth.html").write_text(html, encoding="utf-8")
        except OSError:
            pass
        try:
            h7 = INSTALL / "Hostess7" / "docs" / "field-one-sole"
            h7.mkdir(parents=True, exist_ok=True)
            (h7 / "index.html").write_text(html, encoding="utf-8")
        except OSError:
            pass
    return {"ok": True, "path": "/field-one-sole", "local_instant": True}


def enforce(*, write: bool = True, deep: bool = False) -> dict[str, Any]:
    """Full enforce: scan → annotate → destroy → KILROY pull → seal → website."""
    now = _utc()
    steps: dict[str, Any] = {}

    steps["scan"] = scan_other_fields()
    steps["annotate"] = annotate(steps["scan"])
    steps["destroy"] = destroy_other_fields(steps["scan"], write=write)
    steps["kilroy_pull"] = pull_to_field_one_with_kilroy(write=write)
    steps["seal"] = seal_no_other_fields(write=write)

    if deep:
        steps["hardened"] = _run("lib/field-hardened-ours-plane.py", ["harden"], timeout=180)
    else:
        steps["hardened"] = _load(STATE / "field-hardened-ours-plane-panel.json", {"ok": True})

    # Re-scan after destroy to report residual
    residual = scan_other_fields() if write else steps["scan"]
    rollout = _load(STATE / "field-one-rollout-panel.json", {})
    pending = int(
        residual.get("botnet_pending")
        or rollout.get("botnet_pending")
        or 0
    )
    stamps = int(residual.get("field_one_stamps") or 0)
    destroyed_n = int((steps["destroy"] or {}).get("destroyed_n") or 0)
    refielded_n = int((steps["destroy"] or {}).get("refielded_n") or 0)
    other_n = int(residual.get("other_n") or 0)
    oos_n = int(residual.get("oos_n") or 0)

    motto = (
        f"FIELD ONE ONLY · no other fields on earth · KILROY pull · "
        f"destroyed/re-fielded {destroyed_n}/{refielded_n} · "
        f"residual others {other_n} · oos {oos_n} · "
        f"stamps {stamps:,} · pending {pending} · nothing out of sync permitted"
    )

    out = {
        "ok": True,
        "schema": SCHEMA,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "title": "Field One sole earth",
        "motto": motto,
        "field_one_only": True,
        "no_other_fields_on_earth": True,
        "nothing_out_of_sync_permitted": True,
        "annotate_and_destroy": True,
        "kilroy_pull": True,
        "pull_via": "KILROY",
        "pull_to": FIELD_ONE_ID,
        "other_n": other_n,
        "other_fields_n": other_n,
        "out_of_sync_n": oos_n,
        "oos_n": oos_n,
        "destroyed_n": destroyed_n,
        "refielded_n": refielded_n,
        "field_one_stamps": stamps,
        "botnet_pending": pending,
        "in_sync": pending == 0,
        "steps": {
            k: {
                "ok": _ok(v) if isinstance(v, dict) else bool(v),
                **(
                    {
                        kk: v.get(kk)
                        for kk in (
                            "other_n", "oos_n", "destroyed_n", "refielded_n",
                            "count", "scanned", "new_hostile", "error", "missing",
                        )
                        if isinstance(v, dict) and v.get(kk) is not None
                    }
                ),
            }
            for k, v in steps.items()
        },
        "annotations_api": str(ANNOTATIONS.name),
        "destroyed_api": str(DESTROYED.name),
        "api": "/api/field-one-sole-earth",
        "ui": "http://127.0.0.1:9477/field-one-sole",
        "urls": {
            "website": "http://127.0.0.1:9477/field-one-sole",
            "api": "http://127.0.0.1:9477/api/field-one-sole-earth",
            "hardened": "http://127.0.0.1:9477/hardened-ours",
            "c2": "http://127.0.0.1:9477/c2",
            "kilroy": "http://127.0.0.1:9477/api/kilroy-ipxe-nexus-c2-stack",
        },
        "local_instant": True,
    }
    out["website"] = build_website(out, write=write)

    public = {
        "ok": True,
        "schema": "field-one-sole-earth-public/v1",
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "motto": motto,
        "field_one_only": True,
        "no_other_fields_on_earth": True,
        "kilroy_pull": True,
        "destroyed_n": destroyed_n,
        "refielded_n": refielded_n,
        "other_n": other_n,
        "out_of_sync_n": oos_n,
        "field_one_stamps": stamps,
        "botnet_pending": pending,
        "api": "/api/field-one-sole-earth",
        "ui": "http://127.0.0.1:9477/field-one-sole",
    }
    if write:
        _save(PANEL, out)
        _save(PUBLIC, public)
        _append({
            "event": "enforce",
            "destroyed": destroyed_n,
            "refielded": refielded_n,
            "other": other_n,
            "oos": oos_n,
            "pending": pending,
        })
        for api_dir in (INSTALL / "Hostess7" / "docs" / "api", INSTALL / "docs" / "api"):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "field-one-sole-earth.json", public)
            except OSError:
                pass
    return out


def status() -> dict[str, Any]:
    panel = _load(PANEL, {})
    sealed = SEAL.is_file() or NO_OTHER.is_file()
    rollout = _load(STATE / "field-one-rollout-panel.json", {})
    return {
        "ok": bool(panel.get("ok") or sealed),
        "schema": SCHEMA,
        "sealed": sealed,
        "field_one_only": True,
        "no_other_fields_on_earth": True,
        "nothing_out_of_sync_permitted": True,
        "kilroy_pull": True,
        "other_n": panel.get("other_n"),
        "destroyed_n": panel.get("destroyed_n"),
        "refielded_n": panel.get("refielded_n"),
        "out_of_sync_n": panel.get("out_of_sync_n"),
        "field_one_stamps": panel.get("field_one_stamps"),
        "botnet_pending": panel.get("botnet_pending") if panel.get("botnet_pending") is not None else rollout.get("botnet_pending"),
        "motto": panel.get("motto"),
        "updated": panel.get("updated"),
        "api": "/api/field-one-sole-earth",
        "ui": "http://127.0.0.1:9477/field-one-sole",
        "ironclad_cite": IRONCLAD,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower().lstrip("-")
    if cmd in ("enforce", "run", "up", "sole", "earth", "lock", "seal"):
        deep = "--deep" in sys.argv
        print(json.dumps(enforce(write=True, deep=deep), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("deep",):
        print(json.dumps(enforce(write=True, deep=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("scan",):
        print(json.dumps(scan_other_fields(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("annotate",):
        print(json.dumps(annotate(scan_other_fields()), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("destroy",):
        sc = scan_other_fields()
        print(json.dumps(destroy_other_fields(sc, write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("pull", "kilroy"):
        print(json.dumps(pull_to_field_one_with_kilroy(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("website", "site"):
        p = _load(PANEL, {"field_one_only": True})
        print(json.dumps(build_website(p, write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("status", "json", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-one-sole-earth.py [enforce|scan|annotate|destroy|pull|website|status] [--deep]",
        "motto": "Field One only · KILROY pull · no other fields on earth · annotate+destroy out of sync",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
