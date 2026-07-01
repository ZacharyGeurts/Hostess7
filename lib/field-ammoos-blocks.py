#!/usr/bin/env pythong
"""AmmoOS block — nested CHIPs, codecs, display, audio, and field surfaces; thermally safe publish."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / "state"))
DOCTRINE_PATH = INSTALL / "data" / "field-ammoos-blocks-doctrine.json"
PANEL_PATH = STATE / "field-ammoos-blocks-panel.json"
CACHE_PATH = STATE / "field-ammoos-blocks-last-good.json"


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


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE_PATH, {})


def _block_id(stem: str, tier: str) -> str:
    return hashlib.sha256(f"ammoos:{tier}:{stem}".encode()).hexdigest()[:12]


def _file_stats(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"bytes": 0, "lines": 0, "exists": False, "path": str(path)}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        st = path.stat()
    except OSError:
        return {"bytes": 0, "lines": 0, "exists": False, "path": str(path)}
    return {
        "path": str(path.resolve()),
        "bytes": st.st_size,
        "lines": text.count("\n") + (1 if text else 0),
        "exists": True,
        "mtime_ns": int(st.st_mtime_ns),
    }


def _import_module(rel: str, name: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def thermal_gate(*, ops: int = 1, light: bool = False) -> dict[str, Any]:
    """Thermally safe gate — mirrors plate combinatorics bridge discipline."""
    doc = _doctrine()
    tcfg = doc.get("thermal") or {}
    thermal = _load(STATE / "field-thermal-guard.json", {})
    advisory = _load(STATE / "thermal-advisory.json", {})
    sanity = _load(STATE / "ironclad-field-sanity-panel.json", {})

    headroom = float(thermal.get("headroom_pct") or 100)
    level = str(advisory.get("level") or thermal.get("level") or "ok").lower()
    min_h = float(tcfg.get("min_headroom_pct_light" if light else "min_headroom_pct_full") or (15 if light else 20))
    blocked = {str(x).lower() for x in (tcfg.get("blocked_levels") or ["crit", "storm"])}

    allow_thermal = headroom >= min_h and level not in blocked
    guard = None
    try:
        tg = _import_module("lib/field-thermal-guard.py", "ftg_ab")
        if tg and hasattr(tg, "FieldThermalGuard"):
            guard = tg.FieldThermalGuard()
            allow_thermal = allow_thermal and guard.allow_update(max(1, ops))
    except Exception:
        pass

    never_heat = bool(sanity.get("never_build_under_heat", tcfg.get("never_build_under_heat", True)))
    sanity_ok = bool(sanity.get("operator_ok", sanity.get("ok", True)))
    ok = allow_thermal and sanity_ok and never_heat

    out = {
        "schema": "field-ammoos-thermal-gate/v1",
        "ok": ok,
        "thermal_safe": ok,
        "thermal_headroom_pct": headroom,
        "thermal_level": level,
        "min_headroom_pct": min_h,
        "field_sanity_ok": sanity_ok,
        "never_build_under_heat": never_heat,
        "ops_requested": ops,
        "light_pass": light,
        "deferred": not ok and bool(tcfg.get("defer_on_heat", True)),
    }
    if guard:
        out["guard_headroom_pct"] = guard.headroom_pct()
        if ok:
            guard.record_ops(max(1, ops))
    return out


def _panel_slice(spec: dict[str, Any]) -> dict[str, Any]:
    panel_key = spec.get("panel_state") or spec.get("battery_state")
    if not panel_key:
        return {}
    return _load(STATE / str(panel_key), {})


def carve_child_block(spec: dict[str, Any]) -> dict[str, Any]:
    bid = str(spec.get("id") or "unknown")
    mod_rel = spec.get("module") or spec.get("pipe_module")
    mod_path = INSTALL / str(mod_rel) if mod_rel else None
    doc_path = INSTALL / str(spec["doctrine"]) if spec.get("doctrine") else None
    panel = _panel_slice(spec)

    mod_stats = _file_stats(mod_path) if mod_path else {"bytes": 0, "exists": False}
    doc_stats = _file_stats(doc_path) if doc_path else {"bytes": 0, "exists": False}
    panel_bytes = len(json.dumps(panel, ensure_ascii=False).encode("utf-8")) if panel else 0
    total_bytes = int(mod_stats.get("bytes") or 0) + int(doc_stats.get("bytes") or 0) + panel_bytes

    held = bool(mod_stats.get("exists"))
    if panel:
        held = held and bool(panel.get("ok", True) is not False)

    kernels = list(spec.get("kernels") or [])
    kernel_hits = 0
    if mod_path and mod_path.is_file():
        try:
            snippet = mod_path.read_text(encoding="utf-8", errors="replace")[:12000].lower()
            kernel_hits = sum(1 for k in kernels if str(k).lower() in snippet)
        except OSError:
            pass

    meld_eligible = held and total_bytes >= 512 and (not kernels or kernel_hits >= 1)
    reasons: list[str] = []
    if not mod_stats.get("exists"):
        reasons.append("module_missing")
    if not panel and spec.get("panel_state"):
        reasons.append("panel_empty")
    if kernels and kernel_hits < 1:
        reasons.append("kernel_markers_low")

    snapshot: dict[str, Any] = {}
    if bid == "chips":
        snapshot["core_ok"] = panel.get("ok")
        snapshot["die_count"] = panel.get("die_count") or (panel.get("summary") or {}).get("die_count")
    elif bid == "codecs":
        snap = panel.get("snapshot") or panel
        snapshot["video_codec_count"] = snap.get("video_codec_count") or len(snap.get("video_codecs") or [])
        snapshot["audio_codec_count"] = snap.get("audio_codec_count") or len(snap.get("audio_codecs") or [])
        snapshot["straight_pipe"] = snap.get("straight_pipe", True)
    elif bid == "display":
        ss = panel.get("screenspace") or {}
        snapshot["resolution_profile"] = (panel.get("profile") or {}).get("id") or ss.get("resolution_profile")
        snapshot["ui_scale_pct"] = ss.get("ui_scale_pct")
    elif bid == "audio":
        snapshot["bound"] = panel.get("bound") or (panel.get("route") or {}).get("bound")
        snapshot["sink"] = panel.get("sink_name") or panel.get("default_sink")
    elif bid == "thermal_guard":
        snapshot["headroom_pct"] = panel.get("headroom_pct")
        snapshot["level"] = panel.get("level")
    elif bid == "thermal_manager":
        snapshot["headroom_pct"] = panel.get("headroom_pct") or (panel.get("snapshot") or {}).get("headroom_pct")
        snapshot["ocr_ok"] = panel.get("ocr_ok")
        snapshot["surface"] = panel.get("surface")
    elif bid == "rtx_canvas":
        snap = panel.get("snapshot") or panel
        snapshot["default_canvas"] = snap.get("default_canvas")
        snapshot["desktop_comp_shader"] = snap.get("desktop_comp_shader", False)
        snapshot["os_shaders_ok"] = snap.get("os_shaders_ok")
    elif bid == "storage":
        snapshot["disk_count"] = panel.get("disk_count")
        snapshot["partition_count"] = panel.get("partition_count")
        snapshot["tools"] = panel.get("tools")

    return {
        "schema": "field-ammoos-block/v1",
        "id": _block_id(bid, "child"),
        "block_id": bid,
        "tier": spec.get("tier") or "child",
        "family": spec.get("family") or "field",
        "label": spec.get("label") or bid,
        "plate": "ammoos",
        "held": held,
        "truth": held,
        "bytes": total_bytes,
        "meld_bytes": total_bytes,
        "module_bytes": int(mod_stats.get("bytes") or 0),
        "panel_bytes": panel_bytes,
        "kernel": kernels,
        "kernel_markers": kernel_hits,
        "meld_eligible": meld_eligible,
        "ineligible_reasons": reasons,
        "thermal_ops": int(spec.get("thermal_ops") or 4),
        "api": spec.get("api"),
        "surface": spec.get("surface"),
        "snapshot": snapshot,
        "panel_ok": panel.get("ok") if panel else None,
    }


def carve_family_block(family: dict[str, Any], children: list[dict[str, Any]]) -> dict[str, Any]:
    fid = str(family.get("id") or "family")
    child_ids = set(family.get("children") or [])
    members = [c for c in children if c.get("block_id") in child_ids]
    held_members = [c for c in members if c.get("held")]
    total_bytes = sum(int(c.get("bytes") or 0) for c in members)
    meld_bytes = sum(int(c.get("meld_bytes") or 0) for c in held_members)

    return {
        "schema": "field-ammoos-block/v1",
        "id": _block_id(fid, "family"),
        "block_id": fid,
        "tier": "family",
        "label": family.get("label") or fid,
        "plate": "ammoos",
        "held": len(held_members) > 0,
        "truth": len(held_members) > 0,
        "bytes": total_bytes,
        "meld_bytes": meld_bytes,
        "child_count": len(members),
        "held_count": len(held_members),
        "children": [c.get("block_id") for c in members],
        "meld_eligible": len(held_members) >= 1,
        "ineligible_reasons": [] if held_members else ["no_held_children"],
    }


def carve_ammoos_stack(
    children: list[dict[str, Any]],
    families: list[dict[str, Any]],
) -> dict[str, Any] | None:
    doc = _doctrine()
    stack_cfg = doc.get("stack") or {}
    eligible = [c for c in children if c.get("meld_eligible") and c.get("tier") == "child"]
    held = [c for c in eligible if c.get("held")]
    total_bytes = sum(int(c.get("meld_bytes") or c.get("bytes") or 0) for c in held)
    raw_bytes = sum(int(c.get("bytes") or 0) for c in eligible)

    min_children = int(stack_cfg.get("min_children") or 3)
    min_held = int(stack_cfg.get("min_held") or 2)
    min_bytes = int(stack_cfg.get("min_total_bytes") or 8000)

    if len(eligible) < min_children or len(held) < min_held or total_bytes < min_bytes:
        return None

    kernel_union: list[str] = []
    seen: set[str] = set()
    for c in held:
        for k in c.get("kernel") or []:
            if k not in seen:
                seen.add(k)
                kernel_union.append(k)

    return {
        "schema": "field-ammoos-block/v1",
        "id": _block_id("ammoos", "stack"),
        "block_id": "ammoos",
        "tier": "stack",
        "label": stack_cfg.get("label") or "AmmoOS root block",
        "plate": "ammoos",
        "product": doc.get("product") or "AmmoOS",
        "held": True,
        "truth": True,
        "bytes": raw_bytes,
        "meld_bytes": total_bytes,
        "child_count": len(eligible),
        "held_count": len(held),
        "family_count": len(families),
        "kernel": kernel_union,
        "kernel_markers": len(kernel_union),
        "meld_eligible": True,
        "children": [c.get("block_id") for c in held],
        "families": [f.get("block_id") for f in families if f.get("held")],
        "chips_held": any(c.get("block_id") == "chips" and c.get("held") for c in held),
        "codecs_held": any(c.get("block_id") == "codecs" and c.get("held") for c in held),
        "display_held": any(c.get("block_id") == "display" and c.get("held") for c in held),
        "thermal_safe": True,
    }


def scan_blocks() -> dict[str, Any]:
    doc = _doctrine()
    specs = list(doc.get("children") or [])
    total_ops = sum(int(s.get("thermal_ops") or 4) for s in specs) + 2

    children = [carve_child_block(s) for s in specs]
    families = [carve_family_block(f, children) for f in (doc.get("families") or [])]
    stack = carve_ammoos_stack(children, families)

    all_blocks: list[dict[str, Any]] = list(children) + list(families)
    if stack:
        all_blocks.append(stack)

    eligible = [b for b in children if b.get("meld_eligible")]
    held = [b for b in children if b.get("held")]

    return {
        "children": children,
        "families": families,
        "stack": stack,
        "blocks": all_blocks,
        "block_count": len(all_blocks),
        "child_count": len(children),
        "eligible_count": len(eligible),
        "held_count": len(held),
        "total_bytes": sum(int(b.get("meld_bytes") or b.get("bytes") or 0) for b in held),
        "thermal_ops_budget": total_ops,
    }


def posture(*, thermal_check: bool = True) -> dict[str, Any]:
    scan = scan_blocks()
    ops = int(scan.get("thermal_ops_budget") or 8)
    gate = thermal_gate(ops=ops, light=not thermal_check)
    stack = scan.get("stack")
    truth = _load(STATE / "g16-truth-blocks-panel.json", {})

    return {
        "schema": "field-ammoos-blocks/v1",
        "ts": _now(),
        "ok": True,
        "product": "AmmoOS",
        "motto": (_doctrine().get("motto") or ""),
        "thermal_gate": gate,
        "thermal_safe": bool(gate.get("thermal_safe")),
        "stack": stack,
        "stack_held": bool(stack and stack.get("held")),
        "chips_block": next((c for c in scan["children"] if c.get("block_id") == "chips"), None),
        "codecs_block": next((c for c in scan["children"] if c.get("block_id") == "codecs"), None),
        "display_block": next((c for c in scan["children"] if c.get("block_id") == "display"), None),
        "families": scan.get("families"),
        "blocks": scan.get("blocks"),
        "block_count": scan.get("block_count"),
        "eligible_count": scan.get("eligible_count"),
        "held_count": scan.get("held_count"),
        "total_bytes": scan.get("total_bytes"),
        "truth_blocks_ref": {
            "free_meld": truth.get("free_meld"),
            "truth_block_count": truth.get("truth_block_count"),
            "stack_blocks": truth.get("stack_blocks"),
        },
        "routes": (_doctrine().get("api") or {}),
        "posture": _posture_line(scan, gate, stack),
    }


def _posture_line(scan: dict[str, Any], gate: dict[str, Any], stack: dict[str, Any] | None) -> str:
    chips = next((c for c in scan.get("children") or [] if c.get("block_id") == "chips"), {})
    codecs = next((c for c in scan.get("children") or [] if c.get("block_id") == "codecs"), {})
    disp = next((c for c in scan.get("children") or [] if c.get("block_id") == "display"), {})
    hr = gate.get("thermal_headroom_pct", "—")
    if not gate.get("thermal_safe"):
        return f"AmmoOS block — thermal defer · headroom {hr}% · {scan.get('held_count', 0)} children cached"
    stack_label = "stack held" if stack and stack.get("held") else "stack warming"
    return (
        f"AmmoOS block — {stack_label} · CHIPS {'held' if chips.get('held') else '—'} · "
        f"codecs {'held' if codecs.get('held') else '—'} · display {disp.get('snapshot', {}).get('resolution_profile', '—')} · "
        f"thermal {hr}%"
    )


def publish_panel(*, force: bool = False) -> dict[str, Any]:
    scan = scan_blocks()
    ops = int(scan.get("thermal_ops_budget") or 8)
    gate = thermal_gate(ops=ops)
    doc = _doctrine()
    tcfg = doc.get("thermal") or {}

    if not gate.get("thermal_safe") and not force:
        cached = _load(CACHE_PATH, {})
        if cached and tcfg.get("cache_last_good", True):
            out = dict(cached)
            out["ts"] = _now()
            out["thermal_gate"] = gate
            out["thermal_safe"] = False
            out["deferred"] = True
            out["posture"] = _posture_line(scan, gate, scan.get("stack"))
            _save(PANEL_PATH, out)
            return {"ok": True, "deferred": True, "panel": out, "reason": "thermal_gate"}

    panel = posture(thermal_check=True)
    panel["deferred"] = False
    panel["published_under_thermal_gate"] = True
    _save(PANEL_PATH, panel)
    if panel.get("thermal_safe"):
        _save(CACHE_PATH, panel)
    return {"ok": True, "deferred": False, "panel": panel}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "scan":
        print(json.dumps(scan_blocks(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "thermal":
        ops = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 8
        print(json.dumps(thermal_gate(ops=ops), ensure_ascii=False, indent=2))
        return 0
    if cmd == "publish":
        force = "--force" in sys.argv
        print(json.dumps(publish_panel(force=force), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-ammoos-blocks.py [json|scan|thermal OPS|publish [--force]]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())