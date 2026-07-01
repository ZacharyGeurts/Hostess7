#!/usr/bin/env pythong
"""C2 Taskbar Quint plate — fuse Start+4 icons for combinatorics condense, Ironclad, BSP."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
from sg_paths import grok16_root

GROK16 = grok16_root()
DOCTRINE = INSTALL / "data" / "field-c2-taskbar-doctrine.json"
PANEL = STATE / "field-c2-taskbar-panel.json"


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


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_py(path: Path, name: str) -> Any | None:
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


def _run_posture(script: Path, fn: str = "posture") -> dict[str, Any]:
    mod = _import_py(script, script.stem.replace("-", "_"))
    if mod and hasattr(mod, fn):
        try:
            out = getattr(mod, fn)()
            return out if isinstance(out, dict) else {}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:120]}
    return {"missing": True}


def _ironclad_cite() -> dict[str, Any]:
    ic = _import_py(INSTALL / "lib" / "ironclad-field-sanity.py", "ironclad_field_sanity")
    cite = ""
    if ic and hasattr(ic, "cite_field_sanity"):
        try:
            cite = ic.cite_field_sanity(2) or ""
        except Exception:
            pass
    doctrine = _load(DOCTRINE, {})
    iron = doctrine.get("ironclad") or {}
    return {
        "meld_citation": iron.get("meld_citation") or "ironclad:c2_taskbar:1",
        "field_sanity_cite": cite or iron.get("field_sanity_cite") or "ironclad:field_sanity:2",
        "books": iron.get("books") or ["c2_taskbar", "field_sanity"],
    }


def _bsp_stage() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    bsp_cfg = doctrine.get("bsp") or {}
    case_id = str(bsp_cfg.get("case_id") or "c2_taskbar_plate")
    profile = str(bsp_cfg.get("profile") or "g16_field_opt")
    sources: list[Path] = []
    for rel in bsp_cfg.get("sources") or []:
        p = INSTALL / str(rel)
        if p.is_file():
            sources.append(p)
    bsp_mod = _import_py(GROK16 / "lib" / "field_exec_bsp.py", "field_exec_bsp")
    if not bsp_mod or not sources:
        return {"ok": False, "skipped": "bsp_or_sources_missing", "case_id": case_id}
    try:
        plane = bsp_mod.exec_plane(GROK16)
        hit, compile_ms, note = bsp_mod.bsp_try_reuse(
            plane,
            case_id=case_id,
            sources=sources,
            profile=profile,
            extra="c2_taskbar_quint",
        )
        return {
            "ok": True,
            "case_id": case_id,
            "profile": profile,
            "bsp_hit": hit is not None,
            "binary": str(hit) if hit else None,
            "compile_ms": compile_ms,
            "note": note,
            "source_count": len(sources),
            "plane": str(plane),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160], "case_id": case_id}


def _quint_rows(
    doctrine: dict[str, Any],
    *,
    shell: dict[str, Any],
    desktop: dict[str, Any],
    lock_doc: dict[str, Any],
    broadcaster: dict[str, Any],
) -> list[dict[str, Any]]:
    dock_by_id = {str(i.get("id")): i for i in (shell.get("dock_icons") or [])}
    quick_by_id = {str(q.get("id")): q for q in (desktop.get("startbar") or {}).get("quick") or []}
    rows: list[dict[str, Any]] = []
    for slot in doctrine.get("quint") or []:
        sid = str(slot.get("id") or "")
        app_id = str(slot.get("app_id") or "")
        row = {
            "id": sid,
            "label": slot.get("label"),
            "role": slot.get("role"),
            "exec": slot.get("exec"),
            "glyph": slot.get("glyph"),
            "live": bool(slot.get("live")),
        }
        if sid == "start":
            row["ok"] = True
            row["posture"] = "NEXUS C2 tree menu"
        elif sid == "lock":
            row["ok"] = bool(lock_doc.get("ok"))
            row["product"] = lock_doc.get("product") or "Lock"
            row["posture"] = lock_doc.get("posture")
        elif sid == "broadcaster":
            row["ok"] = bool(broadcaster.get("ok"))
            row["streaming"] = broadcaster.get("streaming")
            row["posture"] = broadcaster.get("posture")
        else:
            app = quick_by_id.get(app_id) or {}
            dock = dock_by_id.get({"files": "files", "terminal": "terminal"}.get(sid, sid)) or {}
            row["ok"] = bool(app.get("exec") or dock.get("exec"))
            row["posture"] = app.get("name") or dock.get("label")
        rows.append(row)
    return rows


def posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    shell = _run_posture(INSTALL / "lib" / "field-shell-dock.py")
    desktop = _run_posture(INSTALL / "lib" / "field-host-desktop.py")
    lock_doc = _run_posture(INSTALL / "lib" / "field-keepass.py")
    broadcaster = _run_posture(INSTALL / "lib" / "field-broadcaster.py")
    quint = _quint_rows(
        doctrine,
        shell=shell,
        desktop=desktop,
        lock_doc=lock_doc,
        broadcaster=broadcaster,
    )
    live = sum(1 for r in quint if r.get("ok"))
    ironclad = _ironclad_cite()
    bsp = _bsp_stage()
    doc = {
        "schema": "field-c2-taskbar-plate/v1",
        "ts": _now(),
        "ok": live >= 4,
        "product": "C2 Taskbar Quint",
        "motto": doctrine.get("motto"),
        "condense_group": doctrine.get("condense_group") or "c2_taskbar",
        "combinatorics_role": doctrine.get("combinatorics_role") or "c2_surface_quint",
        "quint": quint,
        "quint_live": live,
        "quint_total": len(quint),
        "taskbar_quick_only": (desktop.get("startbar") or {}).get("quick_only"),
        "shell_dock_icons": len(shell.get("dock_icons") or []),
        "ironclad": ironclad,
        "bsp": bsp,
        "plates": {
            "shell_dock": {"ok": shell.get("ok"), "schema": shell.get("schema")},
            "host_desktop": {"ok": desktop.get("ok"), "schema": desktop.get("schema")},
            "lock": {"ok": lock_doc.get("ok"), "schema": lock_doc.get("schema")},
            "broadcaster": {"ok": broadcaster.get("ok"), "schema": broadcaster.get("schema")},
        },
        "routes": {
            "panel": "/field",
            "combinatorics": "/combinatorics",
            "lock": "/field-lock",
            "broadcaster": "/field-broadcaster",
        },
        "posture": (
            f"C2 Taskbar Quint — {live}/{len(quint)} live · "
            f"BSP {'hit' if bsp.get('bsp_hit') else 'miss'} · "
            f"{ironclad.get('meld_citation')}"
        ),
    }
    _save_atomic(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "bsp":
        print(json.dumps(_bsp_stage(), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-c2-taskbar-plate.py [json|bsp]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())