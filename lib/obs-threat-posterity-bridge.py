#!/usr/bin/env pythong
"""OBS threat posterity bridge — ingest threat-ledger, spiderweb, stack; witness for NEXUS."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
PANEL = STATE / "obs-threat-posterity-panel.json"
LEDGER = STATE / "obs-threat-posterity-ledger.jsonl"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None


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


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _sg_root() -> Path:
    env = os.environ.get("SG_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return INSTALL.parent.parent.resolve()


def _obs_plugin_data() -> Path:
    return Path.home() / ".config/obs-studio/plugins/obs-field-voice-filter/data"


def _obs_repo_data() -> Path:
    return _sg_root() / "OBS-FieldVoiceFilter/data"


def _resolve_data(name: str) -> tuple[Path | None, dict[str, Any]]:
    for base in (_obs_plugin_data(), _obs_repo_data()):
        p = base / name
        if p.is_file():
            return p, _load(p, {})
    return None, {}


def _tail_jsonl(path: Path | None, limit: int = 50) -> list[dict[str, Any]]:
    if not path or not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _threat_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    audio = video = kills = 0
    confirms: list[float] = []
    markers: dict[str, int] = {}
    for row in rows:
        lane = row.get("lane")
        if lane == "audio":
            audio += 1
        elif lane == "video":
            video += 1
        if row.get("kill") is True or row.get("kill") == "true":
            kills += 1
        pc = row.get("posterity_confirm")
        if isinstance(pc, (int, float)):
            confirms.append(float(pc))
        marker = str(row.get("marker") or "")
        if marker:
            markers[marker] = markers.get(marker, 0) + 1
    return {
        "rows": len(rows),
        "audio": audio,
        "video": video,
        "kills": kills,
        "avg_posterity_confirm": round(sum(confirms) / len(confirms), 3) if confirms else None,
        "max_posterity_confirm": round(max(confirms), 3) if confirms else None,
        "markers": markers,
    }


def _spiderweb_summary(path: Path | None) -> dict[str, Any]:
    rows = _tail_jsonl(path, 200)
    depths: dict[int, int] = {}
    for row in rows:
        d = row.get("depth")
        if isinstance(d, int):
            depths[d] = depths.get(d, 0) + 1
    return {"rows": len(rows), "depths": depths}


def panel_json(*, sync_ledger: bool = False) -> dict[str, Any]:
    sg = _sg_root()
    obs_root = sg / "OBS-FieldVoiceFilter"
    stack_path, stack = _resolve_data("field-obs-stack.json")
    threat_path, _ = _resolve_data("threat-ledger.jsonl")
    spider_path, _ = _resolve_data("spiderweb-tree.jsonl")
    posterity_doc_path = obs_root / "data/field-security-posterity-doctrine.json"
    if not posterity_doc_path.is_file():
        posterity_doc_path = _obs_repo_data() / "field-security-posterity-doctrine.json"
    scene_guard_path = obs_root / "data/field-scene-guard-doctrine.json"
    if not scene_guard_path.is_file():
        scene_guard_path = _obs_repo_data() / "field-scene-guard-doctrine.json"

    posterity_doc = _load(posterity_doc_path, {})
    scene_guard_doc = _load(scene_guard_path, {})
    threat_rows = _tail_jsonl(threat_path, 50)
    threat_summary = _threat_summary(threat_rows)
    spider_summary = _spiderweb_summary(spider_path)

    security = stack.get("security") or {}
    bridges = stack.get("bridges") or {}

    ear_ref = sg / "Final_Ear/data/ear-truth-filter.json"
    eye_ref = sg / "Final_Eye/data/zocr-pattern-registry.json"
    if not eye_ref.is_file() and eye_ref.is_file():
        eye_ref = eye_ref

    doc: dict[str, Any] = {
        "schema": "obs-threat-posterity/v1",
        "updated": _now(),
        "motto": posterity_doc.get("motto")
        or "Posterity decides; resolution deigns — repeating hostile signatures confirm.",
        "obs_plugin_installed": (_obs_plugin_data() / "../bin/64bit/obs-field-voice-filter.so").resolve().is_file(),
        "paths": {
            "stack": str(stack_path) if stack_path else None,
            "threat_ledger": str(threat_path) if threat_path else None,
            "spiderweb": str(spider_path) if spider_path else None,
            "posterity_doctrine": str(posterity_doc_path) if posterity_doc_path.is_file() else None,
        },
        "posterity": {
            "doctrine_schema": posterity_doc.get("schema"),
            "engine": security.get("posterity_engine") or posterity_doc.get("engine"),
            "repeat_inspect": security.get("repeat_inspect") or "field-repeat-field.c",
            "doctrine_loaded": bool(posterity_doc),
            "doctrine_sha256": _sha256(posterity_doc_path),
            "confirm_min": (posterity_doc.get("lanes") or {}).get("audio", {}).get("confirm_min", 0.55),
            "ring": (posterity_doc.get("lanes") or {}).get("audio", {}).get("ring", 32),
        },
        "repeat_inspect": {
            "engine": scene_guard_doc.get("field_repeat_inspect", {}).get("engine") or "field-repeat-field.c",
            "posterity_sec": scene_guard_doc.get("field_repeat_inspect", {}).get("posterity_sec", 2),
            "default_on": scene_guard_doc.get("field_repeat_inspect", {}).get("default_on", True),
        },
        "tree_prune": scene_guard_doc.get("tree_prune") or {},
        "security": {
            "audio_engine": security.get("audio_engine") or "field-voice-security.c",
            "video_engine": security.get("video_engine") or "field-camera-security.c",
            "opt_in_master": security.get("opt_in_master", True),
            "doctrine_loaded": security.get("doctrine_loaded"),
            "stack_schema": stack.get("schema"),
        },
        "threat_ledger": {
            "present": threat_path is not None,
            "summary": threat_summary,
            "recent": threat_rows[-8:],
        },
        "spiderweb": {
            "present": spider_path is not None,
            "summary": spider_summary,
        },
        "bridges": {
            "final_ear": str(ear_ref) if ear_ref.is_file() else bridges.get("final_ear"),
            "final_eye": str(eye_ref) if eye_ref.is_file() else bridges.get("final_eye"),
            "hostess7": bridges.get("hostess7") or "NewLatest/Hostess7",
            "sense_package": bridges.get("sense_package")
            or "NewLatest/data/field-sense-package-doctrine.json",
        },
        "live": bool(stack) or bool(threat_rows) or spider_summary.get("rows", 0) > 0,
    }

    if sync_ledger and threat_rows:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            for row in threat_rows[-5:]:
                mirror = {"ts": _now(), "source": "obs-threat-posterity-bridge", **row}
                fh.write(json.dumps(mirror, ensure_ascii=False) + "\n")

    PANEL.parent.mkdir(parents=True, exist_ok=True)
    PANEL.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def ledger_json(*, tail: int = 50) -> dict[str, Any]:
    threat_path, _ = _resolve_data("threat-ledger.jsonl")
    rows = _tail_jsonl(threat_path, tail)
    return {
        "schema": "obs-threat-ledger/v1",
        "updated": _now(),
        "path": str(threat_path) if threat_path else None,
        "rows": rows,
        "summary": _threat_summary(rows),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(sync_ledger=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "sync":
        print(json.dumps(panel_json(sync_ledger=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ledger":
        tail = 50
        if len(sys.argv) > 2:
            try:
                tail = int(sys.argv[2])
            except ValueError:
                pass
        print(json.dumps(ledger_json(tail=tail), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": f"unknown command {cmd}"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())