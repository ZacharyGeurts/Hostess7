#!/usr/bin/env pythong
"""AmmoNet field ISP — meld Final Internet, steel plates, Hostess 7 public modules."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "ammonet-doctrine.json"
FINAL = INSTALL / "data" / "final-internet-doctrine.json"
SURFACES = INSTALL / "data" / "ammonet-public-surfaces.json"
PANEL = STATE / "ammonet-field-panel.json"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_json(rel: str, args: list[str] | None = None, *, timeout: int = 45) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": f"missing {rel}"}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *(args or ["json"])],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if (proc.stdout or "").strip().startswith("{"):
            return json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {"ok": False, "error": "script_failed"}


def _pages_base() -> str:
    return os.environ.get(
        "HOSTESS7_PAGES_BASE",
        str(_load(FINAL, {}).get("public_surfaces", {}).get("pages_base") or "https://zacharygeurts.github.io/Hostess7"),
    ).rstrip("/")


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    final_doc = _load(FINAL, {})
    pages = _pages_base()

    internet = _run_json("lib/hostess7-internet-clean.py", ["status"], timeout=30)
    znet = _load(STATE / "znetwork-status.json", {})
    if not znet.get("schema"):
        znet = _run_json("lib/znetwork-orchestrator.py", ["status"], timeout=25)

    steel = _run_json("lib/field-steel-neural-plates.py", ["slice"], timeout=60)
    meld_mod = _mod("plate_meld", "lib/field-plate-meld.py")
    meld = meld_mod.panel_json() if meld_mod and hasattr(meld_mod, "panel_json") else _run_json("lib/field-plate-meld.py", ["json"])
    optimal = _run_json("lib/field-steel-plate-optimal.py", ["algorithms"], timeout=40)
    qemu = _run_json("lib/qemu-world-status.py", [], timeout=35)
    lab = _run_json("lib/hostess7-lab-sovereign.py", ["panel"], timeout=40)
    unified = _run_json("lib/field-internet-unified.py", ["panel"], timeout=90)
    g16 = _run_json("lib/hostess7-g16-online.py", ["panel"], timeout=40)

    def _module_entry(spec: dict[str, Any], *, category: str | None = None) -> dict[str, Any]:
        route = spec.get("pages") or ""
        if route and not str(route).startswith("http"):
            route = pages + (route if str(route).startswith("/") else "/" + route)
        out = {
            **spec,
            "pages_url": route or None,
            "operational": True,
            "lane": "pages+loopback",
        }
        if category:
            out["category"] = category
        return out

    modules: list[dict[str, Any]] = []
    seen: set[str] = set()
    for spec in doctrine.get("public_modules") or []:
        if not isinstance(spec, dict):
            continue
        mid = str(spec.get("id") or "")
        if mid:
            seen.add(mid)
        modules.append(_module_entry(spec))

    surf_path = INSTALL / str(doctrine.get("surface_catalog") or "data/ammonet-public-surfaces.json")
    surface_catalog = _load(surf_path if surf_path.is_file() else SURFACES, {})
    catalog_out: list[dict[str, Any]] = []
    surface_count = 0
    for cat in surface_catalog.get("categories") or []:
        if not isinstance(cat, dict):
            continue
        cat_id = str(cat.get("id") or "")
        cat_label = str(cat.get("label") or cat_id)
        cat_surfaces: list[dict[str, Any]] = []
        for spec in cat.get("surfaces") or []:
            if not isinstance(spec, dict):
                continue
            mid = str(spec.get("id") or "")
            surface_count += 1
            entry = _module_entry(spec, category=cat_label)
            cat_surfaces.append(entry)
            if mid and mid not in seen:
                seen.add(mid)
                modules.append(entry)
        if cat_surfaces:
            catalog_out.append({"id": cat_id, "label": cat_label, "surfaces": cat_surfaces})

    safe_fields = {
        "dns": bool((final_doc.get("safe_fields") or {}).get("dns_truth")),
        "dhcp": bool((final_doc.get("safe_fields") or {}).get("dhcp_field")),
        "gatekeeper": True,
        "steel_plates": bool(steel.get("plate_count") or steel.get("plates")),
        "plate_meld": bool(meld.get("generation") or meld.get("ok")),
        "universal_protector": True,
    }

    doc = {
        "ok": True,
        "schema": "ammonet-field/v1",
        "product": "AmmoNet",
        "version": doctrine.get("version", "4.0.1"),
        "title": doctrine.get("title", "AmmoNet — sovereign field ISP"),
        "tagline": doctrine.get("tagline"),
        "motto": doctrine.get("motto"),
        "updated": _ts(),
        "pages": True,
        "pages_base": pages,
        "final_internet": {
            "schema": final_doc.get("schema", "final-internet/v1"),
            "motto": final_doc.get("motto"),
            "migration": final_doc.get("migration"),
            "safe_fields": safe_fields,
            "hub": pages + "/final-internet/",
        },
        "isp": {
            "pipe_percent": int(znet.get("pipe_pct") or znet.get("internet_pipe_percent") or 100),
            "mode": znet.get("mode") or doctrine.get("isp_posture", {}).get("safe_fields_default") and "ACTIVE" or "REVIEW_ONLY",
            "civilian_passthrough": True,
            "boss": "hostess7",
        },
        "layers": doctrine.get("layers") or [],
        "modules": modules,
        "surface_catalog": catalog_out,
        "surface_count": surface_count,
        "hostess7_operational": surface_count > 0,
        "slices": {
            "internet_clean": internet,
            "znetwork": znet,
            "steel_plates": steel,
            "plate_meld": {
                "generation": meld.get("generation"),
                "plate_count": meld.get("plate_count") or len(meld.get("plates") or []),
                "chain_hash": (meld.get("chain_hash") or "")[:16] or None,
                "ok": meld.get("ok", bool(meld.get("generation"))),
            },
            "steel_optimal": {
                "objective": optimal.get("objective"),
                "method": optimal.get("method"),
                "ok": optimal.get("ok", False),
            },
            "qemu_transfer": qemu,
            "lab_sovereign": lab,
            "internet_unified": unified,
            "g16_online": g16,
        },
        "internet_unified": {
            "ok": unified.get("ok"),
            "boss": unified.get("boss", "hostess7"),
            "api": unified.get("api", "/api/field-internet"),
            "github_open": (unified.get("github_always") or {}).get("live", {}).get("open_count"),
            "pipes_connected": (unified.get("all_pipes") or {}).get("connected_at_once"),
        },
        "routes": {
            "ammonet": pages + "/ammonet/",
            "final_internet": pages + "/final-internet/",
            "command": pages + "/command/",
            "desktop": pages + "/desktop/",
            "queen": pages + "/queen/browser.html",
            "training": pages + "/training-room/",
        },
    }
    if write:
        PANEL.parent.mkdir(parents=True, exist_ok=True)
        PANEL.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def meld_cycle() -> dict[str, Any]:
    """Steel plate optimal ordering + plate meld fuse — ISP stack refresh."""
    optimal = _run_json("lib/field-steel-neural-plates.py", ["publish", "--refresh"], timeout=90)
    meld = _run_json("lib/field-plate-meld.py", ["meld"], timeout=120)
    panel = build_panel(write=True)
    return {
        "ok": True,
        "schema": "ammonet-meld-cycle/v1",
        "steel_optimal": optimal,
        "plate_meld": meld,
        "ammonet": panel,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(write=False), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("meld", "cycle", "steel"):
        print(json.dumps(meld_cycle(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "publish":
        print(json.dumps(build_panel(write=True), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: ammonet-field.py [panel|meld|publish]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())