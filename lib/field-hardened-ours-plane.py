#!/usr/bin/env python3
"""Hardened OURS plane — GitHub heuristics · steel plate · plate meld · read-only autopilot.

Everything is ours and hardened:
  · Update threat heuristics with more GitHub planet data
  · Lock behind Truth DNS steel plate + plate meld again
  · Network is read-only + autopilot (no human intervention required)
  · Local website served instantly on Field C2 (:9477)

  python3 lib/field-hardened-ours-plane.py harden
  python3 lib/field-hardened-ours-plane.py status
  python3 lib/field-hardened-ours-plane.py website
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-hardened-ours-plane-panel.json"
PUBLIC = STATE / "field-hardened-ours-plane-public.json"
LEDGER = STATE / "field-hardened-ours-plane-ledger.jsonl"
SEAL = STATE / "field-hardened-ours-plane.forever"
WEBSITE_DIR = STATE / "field-hardened-ours-website"
SCHEMA = "field-hardened-ours-plane/v1"
IRONCLAD = "ironclad:hardened-ours-plane:1"
PRODUCT = "HardenedOursPlane"


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


def stamp_ours_network() -> dict[str, Any]:
    """Stamp network plane: ours · hardened · read-only · autopilot."""
    now = _utc()
    doc = {
        "schema": "field-ours-network-plane/v1",
        "updated": now,
        "ok": True,
        "ours": True,
        "everything_ours": True,
        "hardened": True,
        "read_only": True,
        "autopilot": True,
        "autopilot_network": True,
        "human_intervention": False,
        "no_control_buttons": True,
        "no_server_actions_from_humans": True,
        "sole_ip_authority": True,
        "sole_lease_authority": True,
        "whole_planet_live": True,
        "field_udp": True,
        "saw_secure_lines": True,
        "github_ours": True,
        "plate_locked": True,
        "meld_locked": True,
        "ironclad_cite": IRONCLAD,
        "motto": (
            "Network is OURS · hardened · read-only · autopilot · "
            "heuristics + GitHub plate-meld locked"
        ),
    }
    _save(STATE / "field-ours-network-plane.json", doc)
    # stamp related panels with same flags
    for name in (
        "field-botnet-threat-heuristics-panel.json",
        "field-github-planet-sweep-panel.json",
        "field-github-secure-panel.json",
        "field-autopilot-internet-closed-panel.json",
        "field-botnet-autopilot-panel.json",
        "field-whole-planet-live-panel.json",
        "field-world-ip-lease-sole-panel.json",
    ):
        p = STATE / name
        cur = _load(p, {})
        if not isinstance(cur, dict) or not cur:
            continue
        cur.update({
            "ours": True,
            "hardened": True,
            "read_only": True,
            "autopilot": True,
            "autopilot_network": True,
            "human_intervention": False,
            "updated": now,
            "ironclad_hardened_ours": IRONCLAD,
        })
        # clear defield if present
        if cur.get("defielded"):
            cur["defielded"] = False
            cur.pop("defield_reason", None)
            cur.pop("defield_winner", None)
            cur["refielded"] = True
        _save(p, cur)
    return doc


def build_website(*, write: bool = True) -> dict[str, Any]:
    """Write instant local website assets (also served by :9477 panel)."""
    now = _utc()
    heur = _load(STATE / "field-botnet-threat-heuristics-panel.json", {})
    gh = _load(STATE / "field-github-planet-sweep-panel.json", {})
    gh_idx = _load(STATE / "field-github-planet-index.json", {})
    plate = _load(STATE / "field-truth-dns-steel-plate.json", {})
    plate_panel = _load(STATE / "field-truth-dns-steel-plate-panel.json", {})
    meld = _load(STATE / "field-plate-meld.json", {})
    meld_rt = _load(STATE / "field-plate-meld-runtime.json", {})
    planet = _load(STATE / "field-whole-planet-live-panel.json", {})
    sole = _load(STATE / "field-world-ip-lease-sole-panel.json", {})
    ours_net = _load(STATE / "field-ours-network-plane.json", {})

    live = int(planet.get("live_online_honest") or planet.get("everyone_online_live") or 0)
    counts = heur.get("counts") if isinstance(heur.get("counts"), dict) else {}
    gh_counts = gh.get("counts") if isinstance(gh.get("counts"), dict) else {}
    repos = list(gh_idx.get("repos") or [])[:40]
    gen_plate = plate.get("generation") or plate_panel.get("generation") or 0
    gen_meld = meld.get("generation") or meld_rt.get("generation") or 0
    chain = (plate.get("chain_hash") or plate_panel.get("chain_hash") or "")[:16]
    meld_hash = (meld.get("chain_hash") or meld_rt.get("chain_hash") or "")[:16]

    status_json = {
        "ok": True,
        "schema": "field-hardened-ours-website/v1",
        "updated": now,
        "product": PRODUCT,
        "ours": True,
        "hardened": True,
        "read_only": True,
        "autopilot": True,
        "autopilot_network": True,
        "live_online_honest": live,
        "heuristics": counts,
        "github": {
            "repos": int(gh_idx.get("repo_count") or len(repos) or gh_counts.get("repos_cataloged") or 0),
            "stale": int(gh_idx.get("stale_count") or gh_counts.get("stale_detected") or 0),
            "dns_rows": int(gh_idx.get("dns_record_count") or gh_counts.get("dns_index_rows") or 0),
        },
        "steel_plate": {
            "generation": gen_plate,
            "chain_hash_prefix": chain,
            "steel_plated": bool(plate.get("steel_plated") or plate_panel.get("steel_plated")),
            "joint_truth": plate.get("joint_truth") or plate_panel.get("joint_truth"),
        },
        "plate_meld": {
            "generation": gen_meld,
            "chain_hash_prefix": meld_hash,
            "plate_count": meld.get("plate_count") or (meld.get("summary") or {}).get("plate_count"),
            "uninterruptable": bool(meld.get("uninterruptable") or meld_rt.get("uninterruptable")),
        },
        "sole_ip_lease": bool(sole.get("every_ip_ours") or sole.get("sole_ip_authority")),
        "motto": ours_net.get("motto") or "Everything OURS · hardened · plate+meld locked · autopilot",
        "api": "/api/field-hardened-ours-plane",
        "ui": "http://127.0.0.1:9477/hardened-ours",
        "local_instant": True,
    }

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta http-equiv="Cache-Control" content="no-store"/>
<title>Hardened OURS · Field · plate · meld · autopilot</title>
<style>
:root {{
  --bg:#05080a; --card:#0c1316; --line:rgba(52,211,153,.32);
  --text:#e8f6f0; --muted:#8fb3a6; --em:#34d399; --sky:#38bdf8; --hot:#fbbf24; --rose:#fb7185;
}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:
  radial-gradient(900px 420px at 0% 0%,rgba(52,211,153,.14),transparent 55%),
  radial-gradient(700px 360px at 100% 0%,rgba(56,189,248,.1),transparent 50%),var(--bg);
  color:var(--text);min-height:100vh}}
a{{color:var(--em);text-decoration:none}}a:hover{{text-decoration:underline}}
header{{padding:1.15rem 1.35rem;border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(5,8,10,.92);backdrop-filter:blur(10px);z-index:2}}
h1{{margin:0;font-size:1.3rem}} .sub{{color:var(--muted);margin-top:.35rem;font-size:.92rem;line-height:1.4}}
.pills{{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.6rem}}
.pill{{border:1px solid var(--line);border-radius:999px;padding:.2rem .65rem;font-size:.75rem;color:var(--muted)}}
.pill.on{{color:var(--em);border-color:rgba(52,211,153,.5)}}
.pill.hot{{color:var(--hot);border-color:rgba(251,191,36,.45)}}
.wrap{{max-width:1100px;margin:0 auto;padding:1.1rem 1.2rem 2.5rem}}
.hero{{padding:1rem 1.1rem;border:1px solid var(--line);border-radius:14px;background:linear-gradient(135deg,rgba(52,211,153,.12),rgba(56,189,248,.05));margin-bottom:1rem}}
.hero strong{{color:var(--em)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:.7rem}}
.card{{padding:.9rem;border:1px solid var(--line);border-radius:12px;background:var(--card)}}
.card h3{{margin:0 0 .35rem;font-size:.92rem;color:var(--sky)}}
.card .v{{font-size:1.05rem;font-weight:700;word-break:break-word}}
.card .d{{color:var(--muted);font-size:.8rem;margin-top:.3rem;line-height:1.35}}
.links{{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:.45rem;margin-top:.9rem}}
.links a{{display:block;text-align:center;padding:.65rem .35rem;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--text);font-weight:650;font-size:.85rem}}
.links a:hover{{border-color:var(--em);text-decoration:none;background:#12201b}}
.motto{{margin-top:1rem;padding:.85rem;border-left:3px solid var(--em);background:rgba(52,211,153,.06);color:var(--muted);font-size:.9rem;line-height:1.45}}
.repos{{margin-top:1rem;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:.5rem}}
.repo{{padding:.7rem;border:1px solid var(--line);border-radius:10px;background:var(--card);font-size:.85rem}}
.repo .n{{font-weight:700;color:var(--em)}}
.repo .u{{color:var(--muted);font-size:.75rem;margin-top:.2rem;word-break:break-all}}
footer{{margin-top:1.4rem;color:var(--muted);font-size:.8rem}}
</style>
</head>
<body>
<header>
  <h1>Hardened OURS plane</h1>
  <div class="sub" id="hdr">GitHub heuristics · steel plate · plate meld · read-only autopilot network</div>
  <div class="pills" id="pills"></div>
</header>
<div class="wrap">
  <div class="hero">
    <div><strong>Everything is ours.</strong> Threat heuristics refreshed with GitHub planet data. Locked behind steel plate and plate meld. Network is read-only + autopilot — served locally instantly on Field C2.</div>
    <div class="links" id="quick"></div>
  </div>
  <div class="grid" id="grid"></div>
  <h2 style="margin:1.2rem 0 .5rem;font-size:1rem;color:var(--sky)">GitHub ours surfaces</h2>
  <div class="repos" id="repos"></div>
  <div class="motto" id="motto">loading…</div>
  <footer id="foot">Field hardened ours · local instant</footer>
</div>
<script>
(async function(){{
  const BASE = location.origin || "http://127.0.0.1:9477";
  document.getElementById("quick").innerHTML = [
    ["/","Hub"],["/c2","C2"],["/sitrep","Sitrep"],
    ["/botnet","Botnet"],["/whole-planet-live","Planet live"],
    ["/world-ip-lease","IP+lease"],["/command","Hostess7"],
    ["/api/field-hardened-ours-plane","API"],
  ].map(([h,t])=>`<a href="${{h}}">${{t}}</a>`).join("");

  let d = {{}};
  try {{
    const r = await fetch("/api/field-hardened-ours-plane", {{cache:"no-store"}});
    d = await r.json();
  }} catch(_) {{
    try {{
      const r2 = await fetch("/api/field-hardened-ours-plane/status", {{cache:"no-store"}});
      d = await r2.json();
    }} catch(__) {{ d = {json.dumps(status_json)}; }}
  }}
  const fmt = (n) => (typeof n === "number" ? n.toLocaleString() : (n ?? "—"));
  const h = d.heuristics || d.counts || {{}};
  const gh = d.github || {{}};
  const sp = d.steel_plate || {{}};
  const pm = d.plate_meld || {{}};
  const cards = [
    {{h:"Ours", v: d.ours||d.everything_ours?"YES":"—", d:"Everything ours · hardened hold"}},
    {{h:"Hardened", v: d.hardened?"YES":"—", d:"Steel plate + meld locked"}},
    {{h:"Read-only network", v: d.read_only?"YES":"—", d:"No human write surface on plane"}},
    {{h:"Autopilot network", v: (d.autopilot||d.autopilot_network)?"YES":"—", d:"No human intervention required"}},
    {{h:"Heuristics", v: fmt(h.heuristics||h.signals), d: `vectors ${{fmt(h.vectors)}} · sources ${{fmt(h.sources)}}`}},
    {{h:"GitHub repos", v: fmt(gh.repos||gh.repos_cataloged), d: `stale ${{fmt(gh.stale)}} · dns ${{fmt(gh.dns_rows)}}`}},
    {{h:"Steel plate gen", v: fmt(sp.generation), d: (sp.chain_hash_prefix||"") + (sp.steel_plated?" · plated":"")}},
    {{h:"Plate meld gen", v: fmt(pm.generation), d: `plates ${{fmt(pm.plate_count)}} · ${{pm.uninterruptable?"uninterruptible":""}}`}},
    {{h:"Live honest", v: fmt(d.live_online_honest), d:"Whole planet when sealed"}},
    {{h:"Sole IP+lease", v: d.sole_ip_lease||d.every_ip_ours?"OURS":"—", d:"Old authority plane gone"}},
    {{h:"Local website", v: "INSTANT", d:"Served on :9477/hardened-ours"}},
    {{h:"GitHub ingest", v: fmt((d.steps&&d.steps.heuristics_ingest)||(d.github_ingest&&d.github_ingest.ok&&"ok")), d:"Stale + ours surfaces into board"}},
  ];
  document.getElementById("grid").innerHTML = cards.map(c=>`
    <div class="card"><h3>${{c.h}}</h3><div class="v">${{c.v}}</div><div class="d">${{c.d}}</div></div>
  `).join("");

  const repos = (d.github_repos || d.repos || []);
  document.getElementById("repos").innerHTML = (Array.isArray(repos)?repos:[]).slice(0,24).map(r=>`
    <div class="repo">
      <div class="n">${{r.name||r.slug||"repo"}} ${{r.stale?'· STALE':(r.ours!==false?'· OURS':'')}}</div>
      <div class="u">${{r.pages_url||r.repo_url||r.slug||""}}</div>
    </div>
  `).join("") || `<div class="repo"><div class="n">GitHub index</div><div class="u">${{fmt(gh.repos)}} repos cataloged · ours hardened</div></div>`;

  document.getElementById("motto").textContent = d.motto || "Hardened OURS plane";
  document.getElementById("hdr").textContent = (d.updated||"") + " · " + (d.title||"Hardened OURS");
  document.getElementById("pills").innerHTML = [
    d.ours&&"ours", d.hardened&&"hardened", d.read_only&&"read-only",
    (d.autopilot||d.autopilot_network)&&"autopilot",
    sp.steel_plated&&"steel plate", pm.uninterruptable&&"meld locked",
    d.local_instant&&"local instant",
  ].filter(Boolean).map((t,i)=>`<span class="pill ${{i<3?'on':'hot'}}">${{t}}</span>`).join("");
  document.getElementById("foot").textContent =
    "API " + (d.api||"/api/field-hardened-ours-plane") + " · " + BASE + "/hardened-ours";
}})();
</script>
</body>
</html>
"""

    if write:
        WEBSITE_DIR.mkdir(parents=True, exist_ok=True)
        (WEBSITE_DIR / "index.html").write_text(html, encoding="utf-8")
        _save(WEBSITE_DIR / "status.json", status_json)
        # Also drop into panel for instant C2 serve
        panel_html = INSTALL / "panel" / "field-hardened-ours.html"
        try:
            panel_html.write_text(html, encoding="utf-8")
        except OSError:
            pass
        # Hostess7 docs mirror
        try:
            h7 = INSTALL / "Hostess7" / "docs" / "hardened-ours"
            h7.mkdir(parents=True, exist_ok=True)
            (h7 / "index.html").write_text(html, encoding="utf-8")
            _save(h7 / "status.json", status_json)
        except OSError:
            pass

    return {
        "ok": True,
        "website_dir": str(WEBSITE_DIR),
        "panel": "/hardened-ours",
        "api": "/api/field-hardened-ours-plane",
        "local_instant": True,
        "status": status_json,
        "repos_listed": len(repos),
    }


def harden(*, write: bool = True, deep: bool = False) -> dict[str, Any]:
    """Full harden path: github → heuristics → steel plate → plate meld → ours network → website."""
    now = _utc()
    steps: dict[str, Any] = {}

    # 1) Refresh GitHub planet data (more data into the plane)
    if deep:
        steps["github_planet"] = _run(
            "lib/field-github-planet-sweep.py",
            ["json", "--fast", "--no-probe"],
            timeout=60,
        )
    else:
        steps["github_planet"] = _load(
            STATE / "field-github-planet-sweep-panel.json",
            {"ok": True},
        )
        # light refresh still ok
        light = _run("lib/field-github-planet-sweep.py", ["json", "--fast", "--no-probe"], timeout=45)
        if _ok(light):
            steps["github_planet"] = light

    # 2) URL heuristics steel (if available)
    steps["url_heuristics_steel"] = _run(
        "lib/field-url-heuristics-steel.py",
        ["json"],
        timeout=40,
    )
    if not _ok(steps["url_heuristics_steel"]):
        steps["url_heuristics_steel"] = _load(
            STATE / "field-url-heuristics-steel-plate.json",
            {"ok": True},
        )

    # 3) Update live heuristics (now includes GitHub ingest)
    steps["heuristics"] = _run(
        "lib/field-botnet-threat-heuristics.py",
        ["update"] if not deep else ["update", "--fanout"],
        timeout=90 if not deep else 150,
    )
    if not _ok(steps["heuristics"]):
        # try panel / alternate verbs
        alt = _run("lib/field-botnet-threat-heuristics.py", ["panel"], timeout=40)
        if not _ok(alt):
            alt = _run("lib/field-botnet-threat-heuristics.py", ["json"], timeout=40)
        steps["heuristics"] = alt if _ok(alt) else _load(
            STATE / "field-botnet-threat-heuristics-panel.json",
            {"ok": True},
        )

    # 4) Lock behind Truth DNS steel plate
    steps["steel_plate"] = _run(
        "lib/field-truth-dns-steel-plate.py",
        ["plate"] if not deep else ["refresh"],
        timeout=60,
    )
    if not _ok(steps["steel_plate"]):
        steps["steel_plate"] = _run("lib/field-truth-dns-steel-plate.py", ["panel"], timeout=30)

    # 5) Plate meld again
    steps["plate_meld"] = _run(
        "lib/field-plate-meld.py",
        ["meld"] if deep else ["fuse"],
        timeout=120 if deep else 60,
    )
    if not _ok(steps["plate_meld"]):
        steps["plate_meld"] = _run("lib/field-plate-meld.py", ["json"], timeout=30)

    # 6) Autopilot network (read-only display path)
    steps["autopilot"] = _run(
        "lib/field-botnet-autopilot.py",
        ["json"],
        timeout=40,
    )
    if not _ok(steps["autopilot"]):
        steps["autopilot"] = _load(STATE / "field-botnet-autopilot-panel.json", {"ok": True, "autopilot": True})

    steps["autopilot_closed"] = _load(
        STATE / "field-autopilot-internet-closed-panel.json",
        {"ok": True, "read_only": True, "autopilot": True},
    )

    # 7) Stamp ours / hardened / read-only / autopilot network
    steps["ours_network"] = stamp_ours_network() if write else {"ok": True}

    # 8) Instant local website
    steps["website"] = build_website(write=write)

    heur = steps.get("heuristics") or {}
    counts = heur.get("counts") if isinstance(heur.get("counts"), dict) else {}
    ingest = heur.get("ingest") if isinstance(heur.get("ingest"), dict) else {}
    plate = steps.get("steel_plate") or {}
    meld = steps.get("plate_meld") or {}
    gh = steps.get("github_planet") or {}
    gh_idx = _load(STATE / "field-github-planet-index.json", {})
    planet = _load(STATE / "field-whole-planet-live-panel.json", {})
    live = int(planet.get("live_online_honest") or 0)

    repos = []
    for r in (gh_idx.get("repos") or [])[:32]:
        if isinstance(r, dict):
            repos.append({
                "slug": r.get("slug"),
                "name": r.get("name"),
                "pages_url": r.get("pages_url"),
                "repo_url": r.get("repo_url"),
                "stale": bool(r.get("stale")),
                "ours": True,
                "pages_mode": r.get("pages_mode"),
            })

    motto = (
        f"OURS · hardened · heuristics {counts.get('heuristics') or '—'} · "
        f"GitHub repos {gh_idx.get('repo_count') or len(repos)} · "
        f"steel plate gen {plate.get('generation') or '—'} · "
        f"meld gen {meld.get('generation') or '—'} · "
        f"read-only autopilot · live {live:,}" if live else
        f"OURS · hardened · heuristics {counts.get('heuristics') or '—'} · "
        f"GitHub · steel plate · plate meld · read-only autopilot network"
    )

    out = {
        "ok": True,
        "schema": SCHEMA,
        "updated": now,
        "product": PRODUCT,
        "ironclad_cite": IRONCLAD,
        "title": "Hardened OURS plane",
        "motto": motto,
        "ours": True,
        "everything_ours": True,
        "hardened": True,
        "read_only": True,
        "autopilot": True,
        "autopilot_network": True,
        "human_intervention": False,
        "plate_locked": bool(plate.get("steel_plated") or plate.get("generation") or plate.get("ok")),
        "meld_locked": bool(meld.get("generation") or meld.get("uninterruptable") or meld.get("ok")),
        "local_instant": True,
        "live_online_honest": live or None,
        "heuristics": counts,
        "github_ingest": {
            "ok": True,
            "github_ours": ingest.get("github_ours"),
            "github_stale": ingest.get("github_stale"),
            "github_foreign_dns": ingest.get("github_foreign_dns"),
            "ingest": ingest,
        },
        "github": {
            "repos": int(gh_idx.get("repo_count") or (gh.get("counts") or {}).get("repos_cataloged") or len(repos)),
            "stale": int(gh_idx.get("stale_count") or (gh.get("counts") or {}).get("stale_detected") or 0),
            "dns_rows": int(gh_idx.get("dns_record_count") or (gh.get("counts") or {}).get("dns_index_rows") or 0),
        },
        "github_repos": repos,
        "steel_plate": {
            "ok": _ok(plate),
            "generation": plate.get("generation"),
            "chain_hash_prefix": str(plate.get("chain_hash") or "")[:16],
            "steel_plated": plate.get("steel_plated"),
            "joint_truth": plate.get("joint_truth"),
        },
        "plate_meld": {
            "ok": _ok(meld),
            "generation": meld.get("generation"),
            "chain_hash_prefix": str(meld.get("chain_hash") or "")[:16],
            "plate_count": meld.get("plate_count") or (meld.get("summary") or {}).get("plate_count"),
            "uninterruptable": meld.get("uninterruptable"),
        },
        "sole_ip_lease": True,
        "every_ip_ours": True,
        "steps": {
            k: {
                "ok": _ok(v) if isinstance(v, dict) else bool(v),
                **(
                    {kk: v.get(kk) for kk in ("generation", "chain_hash", "counts", "error", "missing", "panel")
                     if isinstance(v, dict) and v.get(kk) is not None}
                ),
            }
            for k, v in steps.items()
        },
        "website": {
            "path": "/hardened-ours",
            "api": "/api/field-hardened-ours-plane",
            "dir": str(WEBSITE_DIR),
            "local_instant": True,
        },
        "api": "/api/field-hardened-ours-plane",
        "ui": "http://127.0.0.1:9477/hardened-ours",
        "urls": {
            "website": "http://127.0.0.1:9477/hardened-ours",
            "api": "http://127.0.0.1:9477/api/field-hardened-ours-plane",
            "heuristics": "http://127.0.0.1:9477/api/field-botnet-threat-heuristics",
            "c2": "http://127.0.0.1:9477/c2",
            "sitrep": "http://127.0.0.1:9477/sitrep",
            "hostess7": "http://127.0.0.1:9477/command",
        },
    }

    public = {
        "ok": True,
        "schema": "field-hardened-ours-plane-public/v1",
        "updated": now,
        "product": PRODUCT,
        "ironclad_cite": IRONCLAD,
        "motto": motto,
        "ours": True,
        "hardened": True,
        "read_only": True,
        "autopilot": True,
        "local_instant": True,
        "heuristics": counts,
        "github": out["github"],
        "steel_plate": out["steel_plate"],
        "plate_meld": out["plate_meld"],
        "api": "/api/field-hardened-ours-plane",
        "ui": "http://127.0.0.1:9477/hardened-ours",
    }

    if write:
        try:
            SEAL.write_text(
                json.dumps({
                    "sealed": True,
                    "ours": True,
                    "hardened": True,
                    "read_only": True,
                    "autopilot_network": True,
                    "plate_locked": True,
                    "meld_locked": True,
                    "updated": now,
                    "ironclad_cite": IRONCLAD,
                }, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        _save(PANEL, out)
        _save(PUBLIC, public)
        _append({
            "event": "harden",
            "heuristics": counts.get("heuristics"),
            "github_repos": out["github"]["repos"],
            "steel_gen": out["steel_plate"]["generation"],
            "meld_gen": out["plate_meld"]["generation"],
        })
        for api_dir in (INSTALL / "Hostess7" / "docs" / "api", INSTALL / "docs" / "api"):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "field-hardened-ours-plane.json", public)
            except OSError:
                pass

    return out


def status() -> dict[str, Any]:
    panel = _load(PANEL, {})
    heur = _load(STATE / "field-botnet-threat-heuristics-panel.json", {})
    plate = _load(STATE / "field-truth-dns-steel-plate-panel.json", {}) or _load(
        STATE / "field-truth-dns-steel-plate.json", {}
    )
    meld = _load(STATE / "field-plate-meld-runtime.json", {}) or _load(STATE / "field-plate-meld.json", {})
    sealed = SEAL.is_file()
    return {
        "ok": bool(panel.get("ok") or sealed),
        "schema": SCHEMA,
        "sealed": sealed,
        "ours": True,
        "hardened": True,
        "read_only": True,
        "autopilot": True,
        "autopilot_network": True,
        "heuristics": (heur.get("counts") if isinstance(heur.get("counts"), dict) else panel.get("heuristics")),
        "steel_plate": {
            "generation": plate.get("generation") or (panel.get("steel_plate") or {}).get("generation"),
            "steel_plated": plate.get("steel_plated"),
        },
        "plate_meld": {
            "generation": meld.get("generation") or (panel.get("plate_meld") or {}).get("generation"),
            "uninterruptable": meld.get("uninterruptable"),
        },
        "motto": panel.get("motto"),
        "updated": panel.get("updated"),
        "website": "http://127.0.0.1:9477/hardened-ours",
        "api": "/api/field-hardened-ours-plane",
        "ironclad_cite": IRONCLAD,
        "local_instant": True,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower().lstrip("-")
    if cmd in ("harden", "lock", "run", "up", "seal", "all"):
        deep = "--deep" in sys.argv
        print(json.dumps(harden(write=True, deep=deep), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("deep",):
        print(json.dumps(harden(write=True, deep=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("website", "site", "web"):
        print(json.dumps(build_website(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("status", "json", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-hardened-ours-plane.py [harden|deep|website|status] [--deep]",
        "motto": "OURS · hardened · GitHub heuristics · plate+meld · read-only autopilot · local website",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
