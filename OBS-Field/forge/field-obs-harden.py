#!/usr/bin/env pythong
"""Field OBS hardening — portable config, offline, readable UI stamps."""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("OBS_FIELD_ROOT", Path(__file__).resolve().parents[1]))
DOCTRINE = ROOT / "data" / "field-obs-doctrine.json"
TIERS = ROOT / "data" / "field-obs-ui-tiers.json"
GLOBAL_TPL = ROOT / "config" / "global.ini.template"
BASIC_TPL = ROOT / "config" / "basic.ini.template"
SCENE_TPL = ROOT / "config" / "Field-Queen.scene.json"
OUT_PORTABLE = Path(os.environ.get("FIELD_OBS_PORTABLE_DIR", ROOT / "runtime" / "portable"))


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _tier(width: int) -> dict[str, Any]:
    for tier in (_load(TIERS, {}).get("tiers") or []):
        if tier.get("min_width", 0) <= width <= tier.get("max_width", 99999):
            return tier
    return {"id": "fhd", "scale": 1.1, "font_pt": 12}


def _rtx() -> bool:
    try:
        import subprocess
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=6,
        )
        return proc.returncode == 0 and "RTX" in (proc.stdout or "").upper()
    except Exception:
        return False


def write_portable(*, width: int = 1920, ui_scale_pct: int = 110, rtx_reduce: bool = False, state_dir: Path | None = None) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    capture = doctrine.get("capture") or {}
    tier = _tier(width)
    scale = float(tier.get("scale", 1.1)) * (ui_scale_pct / 100.0)
    rtx = _rtx()
    if rtx_reduce and rtx:
        scale *= float((_load(TIERS, {}).get("rtx_profile") or {}).get("factor", 0.92))
    encoder = capture.get("encoder_rtx") if rtx else capture.get("encoder_cpu", "x264")
    if rtx and encoder == "ffmpeg_nvenc":
        rec_enc = "nvenc"
    else:
        rec_enc = "x264"

    portable = OUT_PORTABLE if state_dir is None else state_dir / "field-obs-portable"
    config_root = portable / "config" / "obs-studio"
    basic = config_root / "basic"
    profile_dir = basic / "profiles" / "Field"
    scenes_dir = basic / "scenes"
    record_dir = portable / (capture.get("record_dir") or "recordings")

    for d in (config_root, profile_dir, scenes_dir, record_dir):
        d.mkdir(parents=True, exist_ok=True)

    (portable / "portable_mode.txt").write_text("Field OBS portable\n", encoding="utf-8")

    if GLOBAL_TPL.is_file():
        shutil.copy2(GLOBAL_TPL, config_root / "global.ini")

    if BASIC_TPL.is_file():
        text = BASIC_TPL.read_text(encoding="utf-8")
        text = text.replace("RECORDINGS_DIR", str(record_dir))
        text = text.replace("ENCODER", rec_enc)
        (profile_dir / "basic.ini").write_text(text, encoding="utf-8")

    if SCENE_TPL.is_file():
        shutil.copy2(SCENE_TPL, scenes_dir / "Field-Queen.json")

    qss_src = ROOT / "themes" / "field-obs.qss"
    qss_dst = portable / "field-obs.qss"
    if qss_src.is_file():
        qss = qss_src.read_text(encoding="utf-8")
        font_pt = int(tier.get("font_pt", 12))
        qss = re.sub(r"\d+pt", f"{font_pt}pt", qss)
        qss_dst.write_text(qss, encoding="utf-8")

    meta = {
        "ok": True,
        "portable": str(portable),
        "config": str(config_root),
        "recordings": str(record_dir),
        "profile": capture.get("default_profile", "Field"),
        "collection": capture.get("default_collection", "Field-Queen"),
        "qt_scale": round(scale, 3),
        "tier": tier.get("id"),
        "encoder": rec_enc,
        "rtx": rtx,
        "ui_scale_pct": ui_scale_pct,
    }
    (portable / "field-obs-ui.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def main() -> int:
    import sys
    width = int(os.environ.get("FIELD_OBS_WIDTH", "1920"))
    ui = int(os.environ.get("FIELD_OBS_UI_SCALE", "110"))
    rtx = os.environ.get("FIELD_OBS_RTX_REDUCE", "").lower() in ("1", "true", "yes")
    state = os.environ.get("NEXUS_STATE_DIR")
    meta = write_portable(
        width=width,
        ui_scale_pct=ui,
        rtx_reduce=rtx,
        state_dir=Path(state) if state else None,
    )
    if len(sys.argv) > 1 and sys.argv[1] == "json":
        print(json.dumps(meta, ensure_ascii=False, indent=2))
    else:
        print(meta["portable"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())