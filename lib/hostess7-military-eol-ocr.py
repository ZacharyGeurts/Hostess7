#!/usr/bin/env pythong
"""Hostess 7 Military EOL OCR bridge — eyes, ear, mouth lanes (replaces tesseract)."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent)))


def _final_eye_root() -> Path:
    env = os.environ.get("FINAL_EYE_ROOT", "").strip()
    if env and (Path(env) / "zocr_military_eol.py").is_file():
        return Path(env).resolve()
    for cand in (INSTALL / "Final_Eye", SG / "Final_Eye", SG / "NewLatest" / "Final_Eye"):
        if (cand / "zocr_military_eol.py").is_file():
            return cand.resolve()
    return (SG / "Final_Eye").resolve()


def _load_eye_military() -> Any | None:
    eye_py = _final_eye_root() / "zocr_military_eol.py"
    if not eye_py.is_file():
        return None
    if str(eye_py.parent) not in sys.path:
        sys.path.insert(0, str(eye_py.parent))
    spec = importlib.util.spec_from_file_location("zocr_military_eol_h7", eye_py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def military_eol_ready() -> bool:
    mod = _load_eye_military()
    return bool(mod and mod.military_eol_ready())


def inspect_image(path: Path | str) -> dict[str, Any]:
    mod = _load_eye_military()
    if not mod:
        return {"ok": False, "error": "military_eol_missing", "final_eye_root": str(_final_eye_root())}
    return mod.inspect_image(path)


def ocr_image(path: Path | str, **kwargs: Any) -> dict[str, Any]:
    mod = _load_eye_military()
    if not mod:
        return {"ok": False, "error": "military_eol_missing"}
    return mod.military_ocr_row(path, **kwargs)


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("posture", "status"):
        print(
            json.dumps(
                {
                    "schema": "hostess7-military-eol-ocr/v1",
                    "ok": military_eol_ready(),
                    "engine": "Hostess7/MilitaryEOL",
                    "tesseract_replaced": True,
                    "final_eye_root": str(_final_eye_root()),
                    "senses": ["eye", "ear", "mouth"],
                },
                indent=2,
            )
        )
        return 0
    if argv[0] == "inspect" and len(argv) > 1:
        print(json.dumps(inspect_image(argv[1]), indent=2))
        return 0
    if argv[0] == "ocr" and len(argv) > 1:
        row = ocr_image(argv[1])
        print(json.dumps(row, indent=2))
        return 0 if row.get("ok") else 1
    print(json.dumps({"error": "usage: hostess7-military-eol-ocr.py [posture|inspect PATH|ocr PATH]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())