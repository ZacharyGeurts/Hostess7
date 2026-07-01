#!/usr/bin/env pythong
"""Training bundle for NEXUS panel + Training Viewer — shared live data."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
VIEWER_ROOT = INSTALL / "hostess7-training-viewer"
MODELS_FILE = VIEWER_ROOT / "data" / "connected-models.json"


def _load_training():
    spec = importlib.util.spec_from_file_location("h7train", INSTALL / "lib" / "hostess7-training.py")
    if not spec or not spec.loader:
        raise RuntimeError("hostess7-training.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def _tail_jsonl(path: Path, limit: int = 24) -> list[dict[str, Any]]:
    if not path.is_file() or limit <= 0:
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return rows


def load_models_doc() -> dict[str, Any]:
    doc = _load(MODELS_FILE, {})
    if not doc.get("models"):
        doc = {"schema": "hostess7-connected-models/v1", "models": [], "positions": {}}
    return doc


def bundle_training_data(*, refresh: bool = False) -> dict[str, Any]:
    train = _load_training()
    if refresh:
        assessment = train.assess_all()
    else:
        assessment = train.assess_all()

    muscle_memory: dict[str, Any] = {}
    try:
        spec = importlib.util.spec_from_file_location("h7mm", INSTALL / "lib" / "hostess7-muscle-memory.py")
        if spec and spec.loader:
            mm = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mm)
            if hasattr(mm, "sync_understandings_from_training"):
                mm.sync_understandings_from_training(assessment.get("tracks"))
            if hasattr(mm, "build_panel"):
                muscle_memory = mm.build_panel(write=True, sync_training=False)
    except Exception:
        muscle_memory = _load(STATE / "hostess7-muscle-memory-panel.json", {})

    mouth_neural: dict[str, Any] = {}
    try:
        spec = importlib.util.spec_from_file_location("h7mouth", INSTALL / "lib" / "hostess7-mouth-neural.py")
        if spec and spec.loader:
            mn = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mn)
            if hasattr(mn, "build_panel"):
                mouth_neural = mn.build_panel(write=True)
    except Exception:
        mouth_neural = _load(STATE / "hostess7-mouth-neural-panel.json", {})

    master_st = _load(STATE / "hostess7-master-state.json", {})
    curriculum = _load(INSTALL / "data" / "hostess7-master-curriculum.json", {})
    done = set(master_st.get("completed_steps") or [])
    steps: list[dict[str, Any]] = []
    for step in curriculum.get("curriculum") or []:
        sid = step.get("id")
        steps.append({**step, "completed": sid in done})

    graphs = train.build_evaluation_graphs()
    models_doc = load_models_doc()

    wireframe: dict[str, Any] = {}
    if VIEWER_ROOT.is_dir():
        sys.path.insert(0, str(VIEWER_ROOT))
        try:
            from graph_engine import build_wireframe_graph  # type: ignore

            partial = {
                "assessment": assessment,
                "training_panel": _load(STATE / "hostess7-training-panel.json", {}),
                "master_state": master_st,
                "curriculum_steps": steps,
                "programming": _load(STATE / "hostess7-programming-panel.json", {}),
                "g16": _load(STATE / "hostess7-g16-panel.json", {}),
                "codecraft": _load(STATE / "hostess7-codecraft-panel.json", {}),
                "connected_models_registry": models_doc,
            }
            wireframe = build_wireframe_graph(
                partial, models_doc, install=INSTALL, state=STATE, hostess7=HOSTESS7,
            )
        except Exception:
            wireframe = {"ok": False, "error": "wireframe_unavailable"}
        finally:
            if str(VIEWER_ROOT) in sys.path:
                sys.path.remove(str(VIEWER_ROOT))

    return {
        "schema": "hostess7-training-viewer/v1",
        "install_root": str(INSTALL),
        "state_dir": str(STATE),
        "hostess7_root": str(HOSTESS7),
        "assessment": assessment,
        "evaluation_graphs": graphs,
        "training_panel": _load(STATE / "hostess7-training-panel.json", {}),
        "training_runtime": _load(STATE / "hostess7-training-runtime.json", {}),
        "master": _load(STATE / "hostess7-master-state.json", {}),
        "master_state": master_st,
        "curriculum_steps": steps,
        "programming": _load(STATE / "hostess7-programming-panel.json", {}),
        "g16": _load(STATE / "hostess7-g16-panel.json", {}),
        "codecraft": _load(STATE / "hostess7-codecraft-panel.json", {}),
        "voice": _load(STATE / "hostess7-voice-panel.json", {}),
        "self_interaction": _load(STATE / "hostess7-self-interaction-panel.json", {}),
        "calculator": _load(STATE / "hostess7-calculator-panel.json", {}),
        "biology": _load(STATE / "hostess7-biology-panel.json", {}),
        "engineering": _load(STATE / "hostess7-engineering-panel.json", {}),
        "combat": _load(STATE / "hostess7-combat-panel.json", {}),
        "mos": _load(STATE / "hostess7-mos-panel.json", {}),
        "reality_physics": _load(STATE / "hostess7-reality-physics-panel.json", {}),
        "geography": _load(STATE / "hostess7-geography-panel.json", {}),
        "music": _load(STATE / "hostess7-music-panel.json", {}),
        "sense_training": _load(STATE / "hostess7-sense-training-panel.json", {}),
        "ironclad": _load(STATE / "ironclad-panel.json", {}),
        "ironclad_doctrine": _load(INSTALL / "data" / "ironclad-doctrine.json", {}),
        "ironclad_images": _load(INSTALL / "data" / "ironclad" / "images" / "manifest.json", {}),
        "brain_guard": _load(STATE / "hostess7-brain-guard-panel.json", {}),
        "iq_test": _load(STATE / "hostess7-iq-test-panel.json", {}),
        "turing": _load(STATE / "hostess7-questionnaire-panel.json", {}),
        "neural_selftest": _load(STATE / "hostess7-neural-selftest-panel.json", {}),
        "training_author": _load(STATE / "hostess7-training-author-panel.json", {}),
        "authored_material": _load(STATE / "hostess7-training-author-panel.json", {}).get("catalog") or [],
        "ledger_training": _tail_jsonl(STATE / "hostess7-training-ledger.jsonl"),
        "ledger_author": _tail_jsonl(STATE / "hostess7-training-author-ledger.jsonl"),
        "ledger_master_train": _tail_jsonl(STATE / "hostess7-master-train.jsonl"),
        "connected_models_registry": models_doc,
        "wireframe": wireframe,
        "muscle_memory": muscle_memory,
        "mouth_neural": mouth_neural,
    }


def main() -> int:
    refresh = "--refresh" in sys.argv
    print(json.dumps(bundle_training_data(refresh=refresh), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())