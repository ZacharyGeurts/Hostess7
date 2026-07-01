#!/usr/bin/env pythong
"""Write hardened KeePassXC config — offline, no cloud, readable UI."""
from __future__ import annotations

import configparser
import json
import os
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("KEEPASS_FIELD_ROOT", Path(__file__).resolve().parents[1]))
DOCTRINE = ROOT / "data" / "field-keepass-doctrine.json"
TIERS = ROOT / "data" / "field-keepass-ui-tiers.json"
TEMPLATE = ROOT / "config" / "keepassxc-field.ini.template"
OUT_DIR = Path(os.environ.get("FIELD_KEEPASS_CONFIG_DIR", ROOT / "runtime" / "config"))


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _tier_for_width(width: int) -> dict[str, Any]:
    doc = _load(TIERS, {})
    for tier in doc.get("tiers") or []:
        if tier.get("min_width", 0) <= width <= tier.get("max_width", 99999):
            return tier
    return {"scale": 1.1, "font_pt": 12, "icon_px": 24}


def write_config(*, width: int = 1920, ui_scale_pct: int = 110, rtx_reduce: bool = False) -> Path:
    doctrine = _load(DOCTRINE, {})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "keepassxc-field.ini"

    cfg = configparser.ConfigParser()
    if TEMPLATE.is_file():
        cfg.read(TEMPLATE, encoding="utf-8")
    else:
        cfg.read_dict({"General": {"ConfigVersion": "2"}, "GUI": {}, "Security": {}, "Browser": {"Enabled": "false"}})

    tier = _tier_for_width(width)
    scale = float(tier.get("scale", 1.1)) * (ui_scale_pct / 100.0)
    if rtx_reduce and doctrine.get("ui", {}).get("rtx_reduce_default", True):
        scale *= float(doctrine.get("ui", {}).get("rtx_reduce_factor", 0.92))

    if not cfg.has_section("GUI"):
        cfg.add_section("GUI")
    cfg.set("GUI", "CompactMode", "false")
    cfg.set("GUI", "ApplicationFontSize", str(int(tier.get("font_pt", 12))))

    if not cfg.has_section("Browser"):
        cfg.add_section("Browser")
    cfg.set("Browser", "Enabled", "false")

    if not cfg.has_section("Security"):
        cfg.add_section("Security")
    policy = doctrine.get("policy") or {}
    cfg.set("Security", "ClearClipboard", "true")
    cfg.set("Security", "ClearClipboardTimeout", str(policy.get("clipboard_clear_seconds", 30)))
    cfg.set("Security", "LockDatabaseIdle", "true")
    cfg.set("Security", "LockDatabaseIdleTimeout", str(policy.get("auto_lock_seconds", 300)))
    cfg.set("Security", "ScreenshotProtection", "true" if policy.get("screenshot_blocked") else "false")

    if not cfg.has_section("KeeShare"):
        cfg.add_section("KeeShare")
    cfg.set("KeeShare", "Active", "false")

    with out.open("w", encoding="utf-8") as fh:
        cfg.write(fh)

    meta = OUT_DIR / "field-keepass-ui.json"
    meta.write_text(
        json.dumps(
            {
                "ok": True,
                "config": str(out),
                "qt_scale": round(scale, 3),
                "tier": tier.get("id"),
                "font_pt": tier.get("font_pt"),
                "ui_scale_pct": ui_scale_pct,
                "rtx_reduce": rtx_reduce,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    qss_src = ROOT / "themes" / "field-keepass.qss"
    qss_dst = OUT_DIR / "field-keepass.qss"
    if qss_src.is_file():
        text = qss_src.read_text(encoding="utf-8")
        font_pt = int(tier.get("font_pt", 12))
        text = text.replace("12pt", f"{font_pt}pt")
        qss_dst.write_text(text, encoding="utf-8")
    return out


def main() -> int:
    import sys
    width = int(os.environ.get("FIELD_KEEPASS_WIDTH", "1920"))
    ui = int(os.environ.get("FIELD_KEEPASS_UI_SCALE", "110"))
    rtx = os.environ.get("FIELD_KEEPASS_RTX_REDUCE", "").lower() in ("1", "true", "yes")
    if len(sys.argv) > 1 and sys.argv[1] == "json":
        path = write_config(width=width, ui_scale_pct=ui, rtx_reduce=rtx)
        print(json.dumps({"ok": True, "config": str(path)}, indent=2))
        return 0
    path = write_config(width=width, ui_scale_pct=ui, rtx_reduce=rtx)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())