"""Queen → Final_Ear root resolution — v1.0 audio bridge."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent


def final_ear_root() -> Path:
    env = os.environ.get("FINAL_EAR_ROOT", "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    for candidate in (SG / "Final_Ear", SG / "final_ear"):
        if (candidate / "VERSION").is_file() or (candidate / "zocr_product.py").is_file():
            return candidate
    return SG / "Final_Ear"


def final_ear_env(*, queen: Path | None = None) -> dict[str, str]:
    root = final_ear_root()
    q = queen or QUEEN
    hostess = Path(os.environ.get("HOSTESS7_ROOT", SG / "Hostess7"))
    eye = Path(os.environ.get("FINAL_EYE_ROOT", SG / "Final_Eye"))
    py_parts = [str(root)]
    py = os.pathsep.join(py_parts)
    if os.environ.get("PYTHONPATH"):
        py = py + os.pathsep + os.environ["PYTHONPATH"]
    return {
        **os.environ,
        "SG_ROOT": str(SG),
        "FINAL_EAR_ROOT": str(root),
        "FINAL_EYE_ROOT": str(eye) if eye.is_dir() else os.environ.get("FINAL_EYE_ROOT", ""),
        "QUEEN_ROOT": str(q),
        "HOSTESS7_ROOT": str(hostess),
        "NEXUS_INSTALL_ROOT": os.environ.get("NEXUS_INSTALL_ROOT", str(q)),
        "FINAL_EAR_ASSIST": os.environ.get("FINAL_EAR_ASSIST", "1"),
        "PYTHONPATH": py,
    }


def import_final_ear() -> Path:
    env = final_ear_env()
    root = Path(env["FINAL_EAR_ROOT"])
    for part in env.get("PYTHONPATH", "").split(os.pathsep):
        if part and part not in sys.path:
            sys.path.insert(0, part)
    return root


def final_ear_version() -> dict[str, Any]:
    import_final_ear()
    from zocr_product import product_info
    return product_info()