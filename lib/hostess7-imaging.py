#!/usr/bin/env pythong
"""Hostess 7 imaging chamber — Imagine skills, combinatronic work queue, NEXUS asset repair."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7"))
DOCTRINE = INSTALL / "data" / "hostess7-imaging-doctrine.json"
PANEL = STATE / "hostess7-imaging-panel.json"
WORK = STATE / "hostess7-imaging-work.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _import_mod(name: str, path: Path) -> Any | None:
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _py_json(script: Path, argv: list[str], *, timeout: int = 120) -> dict[str, Any]:
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
    env["NEXUS_STATE_DIR"] = str(STATE)
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *argv],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return json.loads(proc.stdout.strip() or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return {"ok": False, "error": "script_failed", "script": str(script)}


def teach_skills(*, force: bool = False) -> dict[str, Any]:
    teach = HOSTESS7 / "scripts" / "field_imagine_nexus_teach.py"
    if force:
        os.environ["HOSTESS7_FORCE_FETCH"] = "1"
    if teach.is_file():
        return _py_json(teach, [], timeout=60)
    return {"ok": False, "error": "imagine_nexus_teach_missing"}


def scan_combinatronic() -> dict[str, Any]:
    vis = INSTALL / "lib" / "field-combinatronic-visuals.py"
    mod = _import_mod("comb_vis", vis)
    if mod and hasattr(mod, "inventory"):
        inv = mod.inventory()
        broken = inv.get("broken_rows") or []
        by_pattern: dict[str, int] = {}
        for row in broken:
            pat = str(row.get("pattern") or "unknown")
            by_pattern[pat] = by_pattern.get(pat, 0) + 1
        return {
            "ok": True,
            "total": inv.get("total"),
            "required": inv.get("required"),
            "broken": inv.get("broken"),
            "complete": inv.get("complete"),
            "by_pattern": by_pattern,
            "sample": [r.get("path") for r in broken[:12]],
        }
    return {"ok": False, "error": "combinatronic_visuals_missing"}


def scan_format_icons() -> dict[str, Any]:
    ff = INSTALL / "lib" / "field-file-formats.py"
    assets = INSTALL / "data" / "combinatronic-visuals" / "formats"
    table = _load(STATE / "field-file-formats-table.json", {})
    formats = table.get("formats") or []
    if not formats and ff.is_file():
        table = _py_json(ff, ["table"], timeout=180)
        formats = table.get("formats") or []
    missing = []
    for row in formats:
        fid = str(row.get("id") or "")
        if not fid:
            continue
        png = assets / f"{fid}.png"
        if not png.is_file() or png.stat().st_size < 200:
            missing.append(fid)
    return {"ok": True, "total_formats": len(formats), "missing_icons": len(missing), "sample_missing": missing[:16]}


def scan_big_drive() -> dict[str, Any]:
    grid = INSTALL / "data" / "combinatronic-visuals" / "formats" / "big_drive_devices.png"
    hero = INSTALL / "data" / "combinatronic-visuals" / "formats" / "big_drive_hero.png"
    bd = list((INSTALL / "data" / "combinatronic-visuals" / "formats").glob("bd_*.png"))
    return {
        "ok": True,
        "grid": grid.is_file(),
        "hero": hero.is_file(),
        "device_tiles": len(bd),
    }


def work_queue() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    comb = scan_combinatronic()
    icons = scan_format_icons()
    bd = scan_big_drive()
    tasks: list[dict[str, Any]] = []

    broken = int(comb.get("broken") or 0)
    if broken > 0:
        tasks.append({
            "id": "repair_combinatronic",
            "priority": "P0" if broken >= int((doctrine.get("assistant_help") or {}).get("priority_when_broken_gt") or 10) else "P1",
            "label": f"Repair {broken} broken combinatronic visual assets",
            "command": "pythong lib/field-combinatronic-visuals.py repair",
            "broken": broken,
            "by_pattern": comb.get("by_pattern"),
            "assignee": "assistant",
        })

    missing = int(icons.get("missing_icons") or 0)
    if missing > 0:
        tasks.append({
            "id": "generate_format_icons",
            "priority": "P1",
            "label": f"Generate {missing} missing field-file-format icons",
            "command": "pythong lib/field-file-formats.py icons",
            "missing": missing,
            "assignee": "assistant",
        })

    if not bd.get("grid") or int(bd.get("device_tiles") or 0) < 12:
        tasks.append({
            "id": "render_big_drive_icons",
            "priority": "P2",
            "label": "Render Big Drive device grid PNGs",
            "command": "pythong lib/field-big-drive.py render_icons",
            "assignee": "assistant",
        })

    if not (HOSTESS7 / "cache" / "fieldstorage" / "brain" / "imagine" / "corpus.json").is_file():
        tasks.append({
            "id": "bootstrap_imagine_corpus",
            "priority": "P1",
            "label": "Bootstrap Hostess7 Imagine corpus",
            "command": "./Hostess7.sh imagine-learn",
            "assignee": "hostess7",
        })
    else:
        tasks.append({
            "id": "teach_nexus_imaging",
            "priority": "P2",
            "label": "Sync NEXUS imaging skills into Imagine corpus",
            "command": "./Hostess7.sh imagine-nexus-teach",
            "assignee": "hostess7",
        })

    doc = {
        "schema": "hostess7-imaging-work/v1",
        "ts": _now(),
        "ok": True,
        "tasks": tasks,
        "scans": {"combinatronic": comb, "format_icons": icons, "big_drive": bd},
        "statement": (doctrine.get("assistant_help") or {}).get("statement"),
    }
    _save(WORK, doc)
    return doc


def run_help(*, repair: bool = False, icons: bool = False) -> dict[str, Any]:
    """Execute assistant-help tasks Hostess 7 queued."""
    queue = work_queue()
    results: list[dict[str, Any]] = []
    comb_broken = int((queue.get("scans") or {}).get("combinatronic", {}).get("broken") or 0)
    if repair and comb_broken > 0:
        vis = INSTALL / "lib" / "field-combinatronic-visuals.py"
        results.append({"task": "repair_combinatronic", "result": _py_json(vis, ["repair"], timeout=600)})
    if icons:
        ff = INSTALL / "lib" / "field-file-formats.py"
        results.append({"task": "generate_format_icons", "result": _py_json(ff, ["icons"], timeout=300)})
    teach = teach_skills()
    results.append({"task": "teach_nexus_imaging", "result": teach})
    return {"ok": True, "ts": _now(), "queue": queue, "executed": results}


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    queue = work_queue()
    teach_doc = teach_skills()
    panel = {
        "schema": "hostess7-imaging-panel/v1",
        "ts": _now(),
        "ok": True,
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "skills": doctrine.get("skills"),
        "work_queue": queue,
        "nexus_teach": teach_doc,
        "imagine_corpus": str(HOSTESS7 / "cache" / "fieldstorage" / "brain" / "imagine" / "corpus.json"),
        "commands": {
            "teach": "./Hostess7.sh imagine-nexus-teach",
            "work": "./Hostess7.sh imaging-work",
            "repair": "pythong lib/field-combinatronic-visuals.py repair",
            "imagine_learn": "./Hostess7.sh imagine-learn",
        },
    }
    if write:
        _save(PANEL, panel)
    return panel


_OCR_API: dict | None = None


def _ocr_api() -> dict:
    global _OCR_API
    if _OCR_API is None:
        import importlib.util
        py = INSTALL / "lib" / "hostess7-ocr-bind.py"
        spec = importlib.util.spec_from_file_location("h7_ocr_bind_imaging", py)
        if not spec or not spec.loader:
            raise ImportError("hostess7-ocr-bind.py missing")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _OCR_API = mod.bind("imaging", install=INSTALL, state=STATE, ledger=None)
    return _OCR_API


def ingest_ocr_vision(**kw):
    return _ocr_api()["ingest_ocr_vision"](**kw)


def train_ocr_vision(**kw):
    return _ocr_api()["train_ocr_vision"](**kw)


def ocr_vision_status():
    return _ocr_api()["ocr_vision_status"]()


def _handle_ocr_cli(cmd: str) -> int | None:
    import importlib.util
    py = INSTALL / "lib" / "hostess7-ocr-feed.py"
    spec = importlib.util.spec_from_file_location("h7_ocr_feed_imaging", py)
    if not spec or not spec.loader:
        return None
    feed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feed)
    return feed.handle_ocr_cli(
        cmd,
        ingest_fn=ingest_ocr_vision,
        train_fn=train_ocr_vision,
        status_fn=ocr_vision_status,
        usage="hostess7-imaging.py [json|work-queue|teach|help-out|ocr-ingest|ocr-train|ocr-status]",
    )


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "work-queue":
        print(json.dumps(work_queue(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "teach":
        print(json.dumps(teach_skills(force="--force" in sys.argv), ensure_ascii=False, indent=2))
        return 0
    if cmd == "help-out":
        repair = "--repair" in sys.argv
        icons = "--icons" in sys.argv
        print(json.dumps(run_help(repair=repair, icons=icons), ensure_ascii=False, indent=2))
        return 0
    ocr_ret = _handle_ocr_cli(cmd)
    if ocr_ret is not None:
        return ocr_ret
    print(json.dumps({"usage": "hostess7-imaging.py [json|work-queue|teach|help-out|ocr-ingest|ocr-train|ocr-status]"}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())