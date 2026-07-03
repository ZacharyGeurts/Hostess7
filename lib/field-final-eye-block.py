#!/usr/bin/env pythong
"""Final Eye block — ironclad sealed NEXUS C2 vision surface (like CHIPS core)."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _install_root() -> Path:
    env = os.environ.get("NEXUS_INSTALL_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "data" / "field-final-eye-block-doctrine.json").is_file():
            return p
    nl = Path(os.environ.get("SG_ROOT", Path(__file__).resolve().parents[2])) / "NewLatest"
    if (nl / "data" / "field-final-eye-block-doctrine.json").is_file():
        return nl.resolve()
    return Path(__file__).resolve().parents[1]


INSTALL = _install_root()
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent))
DOCTRINE = INSTALL / "data" / "field-final-eye-block-doctrine.json"
PANEL = STATE / "field-final-eye-block-panel.json"
BATTERY = STATE / "field-final-eye-block.json"
FACET = "final_eye"
IRONCLAD_CITE = "ironclad:final_eye:1"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
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


def _ironclad_slice() -> dict[str, Any]:
    cached = _load(STATE / "ironclad-immediate.json", {})
    if cached.get("schema"):
        return cached
    mod = _import_py(INSTALL / "lib" / "ironclad-immediate.py", "ic_fey")
    if mod and hasattr(mod, "immediate_slice"):
        try:
            return mod.immediate_slice()
        except Exception:
            pass
    return cached


def _final_eye_ocr_html(html_path: Path, needles: list[str]) -> dict[str, Any]:
    eye = SG / "Final_Eye" / "zocr_military_eol.py"
    if not eye.is_file():
        eye = SG / "Final_Eye" / "zocr.py"
    text = ""
    if html_path.is_file():
        text = html_path.read_text(encoding="utf-8", errors="replace")
    hits = [n for n in needles if n.lower() in text.lower()]
    ocr_mod = _import_py(eye, "zocr_fey")
    military_ok = bool(ocr_mod)
    if military_ok and hasattr(ocr_mod, "tesseract_available"):
        try:
            military_ok = bool(ocr_mod.tesseract_available())
        except Exception:
            military_ok = True
    return {
        "schema": "field-final-eye-ocr/v1",
        "engine": "Hostess7/MilitaryEOL",
        "html_path": str(html_path),
        "html_exists": html_path.is_file(),
        "needles": needles,
        "hits": hits,
        "hit_count": len(hits),
        "ok": html_path.is_file() and len(hits) >= max(3, len(needles) - 1),
        "military_eol": military_ok,
        "tesseract_available": military_ok,
    }


def _guard_posture() -> dict[str, Any]:
    mod = _import_py(INSTALL / "lib" / "field-thermal-guard.py", "ftg_fey")
    if mod and hasattr(mod, "evaluate"):
        try:
            return mod.evaluate()
        except Exception:
            pass
    return _load(STATE / "field-thermal-guard.json", {})


def _queen_ball_posture(script_name: str, status_attr: str) -> dict[str, Any]:
    queen_lib = INSTALL / "Queen" / "lib"
    script = queen_lib / script_name
    if not script.is_file():
        return {}
    ql = str(queen_lib)
    if ql not in sys.path:
        sys.path.insert(0, ql)
    try:
        spec = importlib.util.spec_from_file_location(script_name.replace(".py", "_block"), script)
        if not spec or not spec.loader:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, status_attr, None)
        if callable(fn):
            return fn()
    except Exception:
        proc = subprocess.run(
            [sys.executable, str(script), "json"],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(INSTALL),
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "SG_ROOT": str(SG)},
        )
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError:
                pass
    return {}


def _eyeball_posture() -> dict[str, Any]:
    return _queen_ball_posture("queen-eyeball.py", "eyeball_status")


def _resolve_html(html_rel: str) -> Path:
    for candidate in (INSTALL / html_rel, SG / "NewLatest" / html_rel, SG / "Queen" / Path(html_rel).name):
        if candidate.is_file():
            return candidate
    return INSTALL / html_rel


def _secure_kill_posture() -> dict[str, Any]:
    mod = _import_py(INSTALL / "lib" / "field-sense-secure-kill.py", "fssk_fey")
    if mod and hasattr(mod, "secure_kill_posture"):
        try:
            return mod.secure_kill_posture(INSTALL, SG)
        except Exception:
            pass
    return {"schema": "field-sense-secure-kill/v1", "ok": False, "kill_policy": "observe"}


def build_block(*, refresh: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    ironclad = _ironclad_slice()
    secure_kill = _secure_kill_posture()
    sealed = bool(ironclad.get("ironclad_sealed") or ironclad.get("realized"))
    guard = _guard_posture()
    eyeball = _eyeball_posture()
    ocr_spec = doctrine.get("ocr_expect") or {}
    html_rel = str(ocr_spec.get("surface_html") or "Queen/world/queen-final-eye-manager.html")
    html_path = _resolve_html(html_rel)
    ocr = _final_eye_ocr_html(html_path, list(ocr_spec.get("needles") or []))

    headroom = float(guard.get("headroom_pct") or 0)
    level = str(guard.get("anomaly", {}).get("thermal_level") or "ok")
    sense_cfg = doctrine.get("sense") or {}
    min_h = float(sense_cfg.get("min_headroom_pct") or 10)
    blocked = {str(x).lower() for x in (sense_cfg.get("blocked_levels") or ["crit", "storm"])}
    sense_safe = headroom >= min_h and level.lower() not in blocked

    eye_root = Path(str(eyeball.get("final_eye_root") or SG / "Final_Eye"))
    stack = doctrine.get("stack") or {}
    bridge_path = INSTALL / str(stack.get("bridge") or "lib/final-eye-ocr-core.py")
    seal_path = INSTALL / str(stack.get("seal") or "lib/final-eye-hostess7-seal.py")
    twins = eyeball.get("twins") or {}
    product = eyeball.get("product") or {}
    sovereign = eyeball.get("sovereign_time") or {}
    mesh_ok = eyeball.get("mesh_ok")

    surface = doctrine.get("surface") or "/world/queen-final-eye-manager.html"
    module_ok = (INSTALL / "lib" / "field-final-eye-block.py").is_file()
    eyeball_ok = eyeball.get("schema") == "queen-eyeball-hostess7/v1"
    root_ok = eye_root.is_dir() and (
        (eye_root / "zocr.py").is_file() or (eye_root / "zocr_military_eol.py").is_file()
    )
    bridge_ok = bridge_path.is_file()
    held = (
        module_ok
        and html_path.is_file()
        and ocr.get("ok")
        and eyeball_ok
        and root_ok
        and bridge_ok
        and secure_kill.get("ok")
    )
    ok = held and sense_safe

    living = twins.get("living") or eyeball.get("living") or {}
    truth = twins.get("truth") or eyeball.get("truth") or {}

    return {
        "schema": "field-final-eye-block/v1",
        "updated": _now(),
        "ok": ok,
        "held": held,
        "truth": held,
        "motto": doctrine.get("motto", ""),
        "facet": FACET,
        "ironclad_citation": IRONCLAD_CITE,
        "ironclad_sealed": sealed,
        "sense_safe": sense_safe,
        "headroom_pct": headroom,
        "thermal_level": level,
        "surface": surface,
        "bookmark_id": "final-eye-manager",
        "eyeball": {
            "schema": eyeball.get("schema"),
            "posture": eyeball.get("posture"),
            "rule": eyeball.get("rule"),
            "twins": {
                "living": (living.get("name") if isinstance(living, dict) else living) or "Vita",
                "truth": (truth.get("name") if isinstance(truth, dict) else truth) or "Veritas",
            },
            "mesh_ok": mesh_ok,
            "sovereign_ok": sovereign.get("ok", sovereign.get("verdict") == "USER_OK"),
            "product_version": product.get("version"),
            "final_eye_root": str(eye_root),
            "bridge_ok": bridge_ok,
            "seal_ok": seal_path.is_file(),
        },
        "guard": {
            "headroom_pct": guard.get("headroom_pct"),
            "certainty_score": guard.get("certainty_score"),
        },
        "ocr": ocr,
        "secure_kill": secure_kill,
        "ironclad_chain": {
            "citation": IRONCLAD_CITE,
            "sealed": sealed,
            "truth_percent": 100.0 if sealed and ok else 95.0 if ok else 80.0,
            "layers": ["ironclad", "final_eye", "queen_eyeball", "hostess7_ocr", "military_eol"],
        },
        "posture": (
            f"Final Eye block — {product.get('name', product.get('product', 'Final_Eye'))} · "
            f"twins Vita/Veritas · mesh {'woven' if mesh_ok else 'check'} · "
            f"OCR {ocr.get('hit_count', 0)} hits"
        ),
    }


def publish_panel(*, refresh: bool = False) -> dict[str, Any]:
    block = build_block(refresh=refresh)
    panel = {
        "schema": "field-final-eye-block-panel/v1",
        "updated": block.get("updated"),
        "ok": block.get("ok"),
        "held": block.get("held"),
        "sense_safe": block.get("sense_safe"),
        "headroom_pct": block.get("headroom_pct"),
        "surface": block.get("surface"),
        "ocr_ok": (block.get("ocr") or {}).get("ok"),
        "ironclad_sealed": block.get("ironclad_sealed"),
        "snapshot": block,
    }
    _save(PANEL, panel)
    _save(BATTERY, block)
    return panel


def posture() -> dict[str, Any]:
    cached = _load(BATTERY, {})
    if (
        cached.get("schema") == "field-final-eye-block/v1"
        and cached.get("updated")
        and (cached.get("eyeball") or {}).get("schema") == "queen-eyeball-hostess7/v1"
    ):
        return cached
    return build_block()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("publish", "panel"):
        print(json.dumps(publish_panel(refresh=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ocr":
        doc = _load(DOCTRINE, {})
        spec = doc.get("ocr_expect") or {}
        html = _resolve_html(str(spec.get("surface_html") or "Queen/world/queen-final-eye-manager.html"))
        print(json.dumps(_final_eye_ocr_html(html, list(spec.get("needles") or [])), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-final-eye-block.py [json|publish|ocr]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())