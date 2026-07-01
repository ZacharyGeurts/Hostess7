#!/usr/bin/env pythong
"""Sovereign stack meld — NEXUS C2 · KILROY · AmmoOS fused, blocks nested, Queen shell sealed."""
from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-sovereign-stack-meld-doctrine.json"
PANEL = STATE / "field-sovereign-stack-meld-panel.json"
MELD_RUNTIME = STATE / "field-plate-meld-runtime.json"
LOOPBACK = os.environ.get("NEXUS_LOOPBACK", "127.0.0.1")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _port_open(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_ok(url: str, timeout: float = 1.0) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _import_posture(rel: str) -> dict[str, Any]:
    path = INSTALL / rel
    if not path.is_file():
        return {"ok": False, "missing": rel}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(f"sov_{path.stem}", path)
        if not spec or not spec.loader:
            return {"ok": False, "missing": rel}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "posture"):
            out = mod.posture()
            return out if isinstance(out, dict) else {"ok": False}
        if hasattr(mod, "panel_doc"):
            out = mod.panel_doc()
            return out if isinstance(out, dict) else {"ok": False}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "missing": rel}


def _plate_held(name: str, meld: dict[str, Any]) -> bool:
    plates = meld.get("plates") or {}
    if isinstance(plates, dict):
        row = plates.get(name) or {}
        return not row.get("missing") and bool(row)
    return name in (meld.get("plates") or [])


def _tier_status(tier: dict[str, Any], *, meld: dict[str, Any]) -> dict[str, Any]:
    tid = str(tier.get("id") or "")
    out: dict[str, Any] = {
        "id": tid,
        "label": tier.get("label", tid),
        "order": tier.get("order"),
        "ok": False,
        "held": False,
        "gaps": [],
    }

    if tid == "hardware":
        guard = _load(INSTALL / "data" / "field-stack-layer-doctrine.json", {}).get("hardware_guard") or {}
        out["ok"] = bool(guard.get("no_breaks", True))
        out["held"] = out["ok"]
        return out

    if tid == "sovereign_core":
        c2_up = _port_open(LOOPBACK, 9477)
        field_up = _http_ok(f"http://{LOOPBACK}:9477/field")
        kernel = _load(STATE / "field-kernel-meld-panel.json", {})
        kilroy_live = bool(kernel.get("kilroy_live") or kernel.get("bzimage_ready"))
        host = _load(STATE / "field-host-desktop.json", {})
        c2_plate = _plate_held("c2_taskbar", meld) or _plate_held("field_host_desktop", meld)
        out["nexus_c2_up"] = c2_up and field_up
        out["kilroy_witness"] = kilroy_live or bool(_load(STATE / "kilroy-core.json", {}))
        out["ammoos_desktop"] = field_up or bool(host.get("programs"))
        out["plates_held"] = c2_plate
        out["fused"] = tier.get("fused", True)
        out["held"] = out["nexus_c2_up"] and out["ammoos_desktop"]
        out["ok"] = out["held"] and (out["kilroy_witness"] or out["nexus_c2_up"])
        if not out["nexus_c2_up"]:
            out["gaps"].append("nexus_c2_down")
        if not out["ammoos_desktop"]:
            out["gaps"].append("ammoos_surface_down")
        return out

    if tid == "ammoos_blocks":
        blocks = _load(STATE / "field-ammoos-blocks-panel.json", {})
        chips = _load(STATE / "field-chips-plate-stack-panel.json", {})
        core = _load(STATE / "field-chips-core-panel.json", {})
        out["block_count"] = blocks.get("block_count")
        out["stack_held"] = bool(blocks.get("stack_held"))
        out["chips_held"] = bool((blocks.get("chips_block") or {}).get("held") or chips.get("ok"))
        out["chips_core_held"] = bool(core.get("ok") or core.get("held"))
        out["thermal_safe"] = blocks.get("thermal_safe", True)
        out["plates_held"] = _plate_held("ammoos_blocks", meld) or bool(blocks.get("ok"))
        out["held"] = out["stack_held"] or out["chips_held"] or bool(blocks.get("ok"))
        out["ok"] = out["held"] and out["thermal_safe"] is not False
        if not out["held"]:
            out["gaps"].append("blocks_not_held")
        return out

    if tid == "queen_shell":
        port = int(tier.get("port") or 9481)
        shell = str(tier.get("shell") or "/world/browser.html")
        out["port"] = port
        out["shell_up"] = _http_ok(f"http://{LOOPBACK}:{port}{shell}")
        out["gates"] = (INSTALL / "data" / "field-queen-gates-seed.json").is_file()
        out["plates_held"] = _plate_held("shell_dock", meld)
        out["held"] = out["shell_up"] and out["gates"]
        out["ok"] = out["held"]
        if not out["shell_up"]:
            out["gaps"].append("queen_shell_down")
        return out

    return out


def verify(*, meld: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    meld = meld if meld is not None else _load(MELD_RUNTIME, {})
    tiers_in = doc.get("tiers_bottom_up") or []
    tiers_out: list[dict[str, Any]] = []
    gaps: list[str] = []
    interlopers: list[str] = []

    for tier in sorted(tiers_in, key=lambda t: int(t.get("order") or 0)):
        row = _tier_status(tier, meld=meld)
        tiers_out.append(row)
        gaps.extend(row.get("gaps") or [])

    chain = str(meld.get("chain_hash") or "")
    if doc.get("gap_policy", {}).get("chain_hash_required") and not chain:
        gaps.append("meld_chain_missing")
        interlopers.append("unmeld_plate_truth")

    prev_held = True
    for row in tiers_out:
        if row.get("id") == "hardware":
            continue
        if prev_held and not row.get("held") and row.get("gaps"):
            interlopers.append(f"gap_before_{row.get('id')}")
        prev_held = bool(row.get("held"))

    core = next((t for t in tiers_out if t.get("id") == "sovereign_core"), {})
    blocks = next((t for t in tiers_out if t.get("id") == "ammoos_blocks"), {})
    queen = next((t for t in tiers_out if t.get("id") == "queen_shell"), {})
    if core.get("held") and blocks.get("held") is False and blocks.get("gaps"):
        interlopers.append("gap_between_core_and_blocks")
    if blocks.get("held") and queen.get("held") is False:
        interlopers.append("gap_between_blocks_and_queen")

    sealed = not gaps and not interlopers and all(t.get("ok") for t in tiers_out if t.get("id") != "hardware")
    return {
        "schema": "field-sovereign-stack-meld/v1",
        "ok": sealed or (core.get("ok") and queen.get("ok")),
        "sealed": sealed,
        "ts": _now(),
        "motto": doc.get("motto"),
        "tier_order": doc.get("tier_order") or [],
        "tiers": tiers_out,
        "gaps": gaps,
        "interlopers": interlopers,
        "reject_interlopers": bool((doc.get("gap_policy") or {}).get("reject_interlopers")),
        "meld_chain_hash": chain or None,
        "meld_generation": meld.get("generation"),
        "stack_tight": sealed,
    }


def publish_panel() -> dict[str, Any]:
    row = verify()
    _save(PANEL, row)
    return {"ok": True, "published": str(PANEL), **row}


def posture() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("ts"):
        return cached
    return publish_panel()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "posture", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("verify", "check"):
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("publish", "fuse"):
        print(json.dumps(publish_panel(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: json|verify|publish"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())