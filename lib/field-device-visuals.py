#!/usr/bin/env pythong
"""Device visuals — accurate procedural PNG renders for PCs, consoles, handhelds."""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SEED = INSTALL / "data" / "field-extensive-library-seed.json"
DOCTRINE = INSTALL / "data" / "field-device-visuals-doctrine.json"
ASSETS = INSTALL / "data" / "combinatronic-visuals" / "devices"
LIBRARY_ASSETS = INSTALL / "library" / "assets" / "devices"
PANEL = STATE / "field-device-visuals-panel.json"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

FORM_COLORS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "console": ((42, 44, 52), (68, 72, 82)),
    "handheld": ((32, 36, 48), (58, 64, 78)),
    "pc_tower": ((198, 192, 178), (140, 135, 125)),
    "pc_desktop": ((210, 205, 195), (155, 150, 140)),
    "laptop": ((48, 52, 58), (72, 78, 88)),
    "arcade": ((28, 32, 42), (180, 40, 50)),
    "phone": ((24, 26, 32), (48, 52, 60)),
    "workstation": ((55, 58, 65), (85, 90, 100)),
}

MAKER_ACCENT: dict[str, tuple[int, int, int]] = {
    "Nintendo": (220, 30, 38),
    "Sony": (0, 80, 180),
    "Sega": (0, 90, 200),
    "Microsoft": (16, 124, 16),
    "Atari": (200, 50, 50),
    "Commodore": (180, 30, 60),
    "Apple": (180, 180, 185),
    "IBM": (0, 60, 120),
    "Magnavox": (160, 140, 100),
    "NEC": (200, 60, 40),
    "Philips": (0, 100, 180),
    "3DO": (120, 80, 160),
    "Various": (94, 234, 212),
}


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


def _font(size: int, *, bold: bool = False):
    from PIL import ImageFont  # noqa: WPS433

    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _device_seed(device_id: str) -> int:
    return int(hashlib.md5(device_id.encode()).hexdigest()[:8], 16)


def _accent(maker: str) -> tuple[int, int, int]:
    return MAKER_ACCENT.get(maker, MAKER_ACCENT["Various"])


def _draw_console(draw, cx: int, cy: int, w: int, h: int, accent: tuple[int, int, int], body: tuple[int, int, int], edge: tuple[int, int, int], label: str):
    bw, bh = int(w * 0.72), int(h * 0.28)
    draw.rounded_rectangle((cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2), radius=12, fill=body, outline=edge, width=3)
    draw.rounded_rectangle((cx - bw // 2 + 20, cy - bh // 2 + 8, cx + bw // 2 - 20, cy + bh // 2 - 8), radius=6, fill=(body[0] + 8, body[1] + 8, body[2] + 10))
    slot_w = int(bw * 0.22)
    draw.rounded_rectangle((cx - slot_w // 2, cy - 6, cx + slot_w // 2, cy + 14), radius=3, fill=(18, 20, 26), outline=accent, width=2)
    draw.ellipse((cx + bw // 2 - 36, cy - bh // 2 + 16, cx + bw // 2 - 22, cy - bh // 2 + 30), fill=accent)
    for i, px in enumerate(range(cx - bw // 2 + 40, cx + bw // 2 - 50, 28)):
        col = accent if i % 3 == 0 else (50, 54, 62)
        draw.rounded_rectangle((px, cy + bh // 2 - 22, px + 18, cy + bh // 2 - 8), radius=4, fill=col)
    font = _font(16, bold=True)
    tw = draw.textlength(label[:24], font=font)
    draw.text((cx - tw / 2, cy + bh // 2 + 18), label[:24], fill=accent, font=font)


def _draw_handheld(draw, cx: int, cy: int, w: int, h: int, accent: tuple[int, int, int], body: tuple[int, int, int], edge: tuple[int, int, int], label: str):
    bw, bh = int(w * 0.34), int(h * 0.52)
    draw.rounded_rectangle((cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2), radius=18, fill=body, outline=edge, width=3)
    sw, sh = int(bw * 0.78), int(bh * 0.42)
    draw.rounded_rectangle((cx - sw // 2, cy - bh // 2 + 24, cx + sw // 2, cy - bh // 2 + 24 + sh), radius=6, fill=(12, 14, 22), outline=(40, 44, 54), width=2)
    draw.rectangle((cx - sw // 2 + 8, cy - bh // 2 + 32, cx + sw // 2 - 8, cy - bh // 2 + 24 + sh - 8), fill=(30, 80, 120))
    d = 28
    dx, dy = cx - bw // 2 + 36, cy + bh // 2 - 80
    draw.ellipse((dx, dy, dx + d, dy + d), fill=(38, 42, 50), outline=edge)
    draw.polygon([(dx + d // 2, dy + 6), (dx + d - 6, dy + d // 2), (dx + d // 2, dy + d - 6), (dx + 6, dy + d // 2)], fill=accent)
    for i, bx in enumerate(range(cx + 20, cx + bw // 2 - 10, 22)):
        draw.rounded_rectangle((bx, cy + bh // 2 - 70, bx + 16, cy + bh // 2 - 52), radius=4, fill=accent if i == 0 else (55, 58, 68))
    font = _font(14, bold=True)
    tw = draw.textlength(label[:18], font=font)
    draw.text((cx - tw / 2, cy + bh // 2 + 14), label[:18], fill=accent, font=font)


def _draw_pc_tower(draw, cx: int, cy: int, w: int, h: int, accent: tuple[int, int, int], body: tuple[int, int, int], edge: tuple[int, int, int], label: str, year: int):
    bw, bh = int(w * 0.28), int(h * 0.58)
    draw.rectangle((cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2), fill=body, outline=edge, width=3)
    for y in range(cy - bh // 2 + 30, cy + bh // 2 - 40, 36):
        draw.rectangle((cx - bw // 2 + 12, y, cx + bw // 2 - 12, y + 24), fill=(body[0] - 15, body[1] - 15, body[2] - 15), outline=edge)
        draw.ellipse((cx + bw // 2 - 28, y + 8, cx + bw // 2 - 16, y + 20), fill=(40, 180, 60) if (y - cy) % 72 == 0 else (180, 50, 40))
    draw.rectangle((cx - bw // 2 + 20, cy + bh // 2 - 70, cx + bw // 2 - 20, cy + bh // 2 - 30), fill=(30, 32, 38), outline=edge)
    draw.rectangle((cx - 20, cy + bh // 2 - 62, cx + 20, cy + bh // 2 - 38), fill=(20, 22, 28))
    font = _font(15, bold=True)
    tw = draw.textlength(label[:20], font=font)
    draw.text((cx - tw / 2, cy + bh // 2 + 16), label[:20], fill=accent, font=font)
    draw.text((cx - 30, cy - bh // 2 - 28), str(year), fill=(100, 105, 115), font=_font(12))


def _draw_laptop(draw, cx: int, cy: int, w: int, h: int, accent: tuple[int, int, int], body: tuple[int, int, int], edge: tuple[int, int, int], label: str):
    bw, bh = int(w * 0.55), int(h * 0.38)
    draw.polygon([
        (cx - bw // 2, cy + 20),
        (cx + bw // 2, cy + 20),
        (cx + bw // 2 + 20, cy + 80),
        (cx - bw // 2 - 20, cy + 80),
    ], fill=body, outline=edge)
    draw.rounded_rectangle((cx - bw // 2, cy - bh, cx + bw // 2, cy + 10), radius=8, fill=body, outline=edge, width=3)
    draw.rectangle((cx - bw // 2 + 16, cy - bh + 16, cx + bw // 2 - 16, cy - 4), fill=(14, 16, 24), outline=(40, 44, 54))
    draw.rectangle((cx - bw // 2 + 24, cy - bh + 24, cx + bw // 2 - 24, cy - 12), fill=(35, 90, 130))
    font = _font(16, bold=True)
    tw = draw.textlength(label[:22], font=font)
    draw.text((cx - tw / 2, cy + 95), label[:22], fill=accent, font=font)


def _draw_arcade(draw, cx: int, cy: int, w: int, h: int, accent: tuple[int, int, int], body: tuple[int, int, int], edge: tuple[int, int, int], label: str):
    bw = int(w * 0.38)
    draw.polygon([
        (cx - bw // 2, cy - h // 2 + 40),
        (cx + bw // 2, cy - h // 2 + 40),
        (cx + bw // 2 + 30, cy + h // 2 - 20),
        (cx - bw // 2 - 30, cy + h // 2 - 20),
    ], fill=body, outline=edge, width=3)
    draw.rectangle((cx - bw // 2 + 20, cy - h // 2 + 60, cx + bw // 2 - 20, cy - h // 2 + 200), fill=(10, 12, 18), outline=accent, width=3)
    draw.rectangle((cx - bw // 2 + 30, cy - h // 2 + 80, cx + bw // 2 - 30, cy - h // 2 + 180), fill=(40, 100, 60))
    for i, px in enumerate(range(cx - 60, cx + 50, 35)):
        draw.ellipse((px, cy + 40, px + 28, cy + 68), fill=accent if i % 2 else (50, 54, 62))
    font = _font(18, bold=True)
    tw = draw.textlength(label[:16], font=font)
    draw.text((cx - tw / 2, cy - h // 2 + 12), label[:16], fill=accent, font=font)


def render_device(device: dict[str, Any], *, out: Path | None = None) -> Path:
    from PIL import Image, ImageDraw  # noqa: WPS433

    device_id = str(device.get("id", "device"))
    form = str(device.get("form_factor") or device.get("type") or "console")
    if form in ("pc", "desktop"):
        form = "pc_tower"
    if form == "handheld":
        form = "handheld"
    if form not in FORM_COLORS:
        form = "console"

    body, edge = FORM_COLORS[form]
    maker = str(device.get("maker") or device.get("vendor") or "Various")
    accent = _accent(maker)
    label = str(device.get("label") or device.get("name") or device_id)
    year = int(device.get("year") or device.get("era") or 1980)

    w, h = 640, 480
    rng = random.Random(_device_seed(device_id))
    bg = (8, 10, 14)
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)

    grad_y = rng.randint(0, 30)
    for y in range(h):
        shade = grad_y + int(12 * y / h)
        draw.line([(0, y), (w, y)], fill=(shade, shade + 2, shade + 4))

    cx, cy = w // 2, h // 2 - 10
    if form == "handheld":
        _draw_handheld(draw, cx, cy, w, h, accent, body, edge, label)
    elif form in ("pc_tower", "pc_desktop", "workstation"):
        _draw_pc_tower(draw, cx, cy, w, h, accent, body, edge, label, year)
    elif form == "laptop":
        _draw_laptop(draw, cx, cy, w, h, accent, body, edge, label)
    elif form == "arcade":
        _draw_arcade(draw, cx, cy, w, h, accent, body, edge, label)
    else:
        _draw_console(draw, cx, cy, w, h, accent, body, edge, label)

    info_font = _font(11)
    meta = f"{maker} · {year} · {form.replace('_', ' ')}"
    draw.text((16, h - 28), meta, fill=(110, 118, 130), font=info_font)
    draw.text((16, 16), device_id, fill=(70, 78, 90), font=info_font)

    out = out or ASSETS / f"{device_id}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)

    mirror = LIBRARY_ASSETS / f"{device_id}.png"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    img.save(mirror, "PNG", optimize=True)
    return out


def device_list() -> list[dict[str, Any]]:
    ext = _import_mod("field_extensive_library", "field-extensive-library.py")
    if ext:
        try:
            lib = ext.build_library(sync=False, render_devices=False)
            devices = list(lib.get("devices") or [])
            if devices:
                return devices
        except Exception:
            pass
    seed = _load(SEED, {})
    devices = list(seed.get("devices") or [])
    for row in seed.get("consoles") or []:
        if isinstance(row, dict) and row.get("id"):
            devices.append({**row, "type": "console"})
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for d in devices:
        did = str(d.get("id", ""))
        if did and did not in seen:
            seen.add(did)
            out.append(d)
    return out


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def generate_all() -> dict[str, Any]:
    devices = device_list()
    rendered: list[str] = []
    errors: list[dict[str, Any]] = []
    for dev in devices:
        try:
            path = render_device(dev)
            rendered.append(str(path))
        except Exception as exc:
            errors.append({"id": dev.get("id"), "error": str(exc)})
    panel_doc = {
        "schema": "field-device-visuals-panel/v1",
        "updated": _now(),
        "ok": len(errors) == 0,
        "device_count": len(devices),
        "rendered": len(rendered),
        "errors": errors,
        "assets_dir": str(ASSETS),
        "library_dir": str(LIBRARY_ASSETS),
    }
    _save(PANEL, panel_doc)
    return panel_doc


def verify_png(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "status": "missing"}
    data = path.read_bytes()
    if len(data) < 2000 or not data.startswith(PNG_MAGIC):
        return {"ok": False, "status": "bad_png", "bytes": len(data)}
    return {"ok": True, "status": "ok", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def inventory() -> dict[str, Any]:
    devices = device_list()
    rows = []
    ok = 0
    for dev in devices:
        did = str(dev.get("id", ""))
        path = ASSETS / f"{did}.png"
        check = verify_png(path)
        if check.get("ok"):
            ok += 1
        rows.append({"id": did, "path": str(path), "verify": check})
    return {
        "schema": "field-device-visuals-inventory/v1",
        "updated": _now(),
        "total": len(devices),
        "ok": ok,
        "broken": len(devices) - ok,
        "complete": ok == len(devices),
        "rows": rows,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "status", "json"):
        if PANEL.is_file():
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(generate_all(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("generate", "build", "all"):
        print(json.dumps(generate_all(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "inventory":
        print(json.dumps(inventory(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "render" and len(sys.argv) >= 3:
        did = sys.argv[2]
        for dev in device_list():
            if str(dev.get("id")) == did:
                path = render_device(dev)
                print(json.dumps({"ok": True, "path": str(path)}, ensure_ascii=False, indent=2))
                return 0
        print(json.dumps({"ok": False, "error": "not_found", "id": did}))
        return 1
    if cmd == "verify":
        inv = inventory()
        print(json.dumps({"ok": inv["complete"], "ok_count": inv["ok"], "total": inv["total"]}, ensure_ascii=False, indent=2))
        return 0 if inv["complete"] else 1
    print(json.dumps({"error": "usage", "cmds": ["panel", "generate", "inventory", "render <id>", "verify"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())