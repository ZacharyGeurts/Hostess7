"""Queen → Final_Mouth root resolution — v1.0 voice bridge."""
from __future__ import annotations

import os
import sys
from pathlib import Path

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent


def final_mouth_root() -> Path:
    env = os.environ.get("FINAL_MOUTH_ROOT", "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    for candidate in (
        SG / "NewLatest" / "Final_Mouth",
        SG / "Final_Mouth",
        SG / "final_mouth",
        QUEEN.parent / "Final_Mouth",
    ):
        if (candidate / "VERSION").is_file() or (candidate / "zocr_product.py").is_file():
            return candidate
    return QUEEN.parent / "Final_Mouth"


def final_mouth_env(*, queen: Path | None = None) -> dict[str, str]:
    root = final_mouth_root()
    q = queen or QUEEN
    hostess = Path(os.environ.get("HOSTESS7_ROOT", SG / "Hostess7"))
    ear = Path(os.environ.get("FINAL_EAR_ROOT", SG / "Final_Ear"))
    eye = Path(os.environ.get("FINAL_EYE_ROOT", SG / "Final_Eye"))
    py_parts = [str(root), str(ear), str(eye)]
    py = os.pathsep.join(py_parts)
    if os.environ.get("PYTHONPATH"):
        py = py + os.pathsep + os.environ["PYTHONPATH"]
    return {
        **os.environ,
        "SG_ROOT": str(SG),
        "FINAL_MOUTH_ROOT": str(root),
        "FINAL_EAR_ROOT": str(ear) if ear.is_dir() else os.environ.get("FINAL_EAR_ROOT", ""),
        "FINAL_EYE_ROOT": str(eye) if eye.is_dir() else os.environ.get("FINAL_EYE_ROOT", ""),
        "QUEEN_ROOT": str(q),
        "HOSTESS7_ROOT": str(hostess),
        "NEXUS_INSTALL_ROOT": os.environ.get("NEXUS_INSTALL_ROOT", str(q)),
        "FINAL_MOUTH_ASSIST": os.environ.get("FINAL_MOUTH_ASSIST", "1"),
        "PYTHONPATH": py,
    }


def import_final_mouth() -> Path:
    env = final_mouth_env()
    root = Path(env["FINAL_MOUTH_ROOT"])
    for part in env.get("PYTHONPATH", "").split(os.pathsep):
        if part and part not in sys.path:
            sys.path.insert(0, part)
    return root