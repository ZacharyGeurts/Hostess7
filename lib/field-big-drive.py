#!/usr/bin/env pythong
"""Big Drive — field frame slider, any format disk/ISO, permanent field replaces USB."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-big-drive-doctrine.json"
PANEL = STATE / "field-big-drive-panel.json"
WORK = STATE / "big-drive"
FIELD_DRIVE_DIR = STATE / "field-drives"
STABILIZER = STATE / "field-big-drive-stabilizer.json"
STAGING = WORK / "stabilizer-staging"
RETURN_DIR = WORK / "stabilizer-return"
ICON_GRID = INSTALL / "data" / "combinatronic-visuals" / "formats" / "big_drive_devices.png"
FDRV_MAGIC = b"FDRV\x01"
BLANKET_MAGIC = b"FLD2\x01"
FIELD_TAIL_MAGICS = (b"WRZC", b"WRDT", b"ZAC7", b"FLD1")
FIELDDRIVE_HEADER_LEN = 4 + 8 + 4 + 4 + 256 + 32  # magic + frame + src_len + ts + source + fmt


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


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _safe_path(raw: str) -> Path | None:
    p = Path(str(raw or "").strip()).expanduser()
    if not p.is_absolute():
        for root in (SG, INSTALL, Path.home() / "Desktop" / "SG"):
            cand = (root / p).resolve()
            if cand.is_file():
                return cand
        return None
    try:
        resolved = p.resolve()
    except OSError:
        return None
    if ".." in str(raw):
        return None
    if not resolved.is_file():
        return None
    return resolved


def _format_for_path(path: Path) -> dict[str, Any] | None:
    ext = path.suffix.lower()
    for row in _doctrine().get("formats") or []:
        for e in row.get("extensions") or []:
            if e.lower() == ext:
                return row
    return None


def _frame_by_id(fid: str) -> dict[str, Any] | None:
    for row in _doctrine().get("frame_sizes") or []:
        if row.get("id") == fid:
            return row
    return None


def _device_by_id(did: str) -> dict[str, Any] | None:
    for row in _doctrine().get("devices") or []:
        if row.get("id") == did:
            return row
    return None


def _sha256_file(path: Path, limit: int = 64 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            if f.tell() > limit:
                break
    return h.hexdigest()


def render_device_grid(*, force: bool = False) -> dict[str, Any]:
    """4×3 PNG grid — multiple device silhouettes per combinatronic asset."""
    doctrine = _doctrine()
    icons = doctrine.get("icons") or {}
    cols = int(icons.get("grid_cols") or 4)
    rows_n = int(icons.get("grid_rows") or 3)
    cell = int(icons.get("cell_px") or 128)
    devices = (doctrine.get("devices") or [])[: cols * rows_n]

    out = INSTALL / str(icons.get("device_grid") or "data/combinatronic-visuals/formats/big_drive_devices.png")
    mirror = INSTALL / "library" / "assets" / "formats" / "big_drive_devices.png"

    if out.is_file() and not force:
        return {"ok": True, "skipped": True, "path": str(out), "devices": len(devices)}

    try:
        from PIL import Image, ImageDraw, ImageFont  # noqa: WPS433
    except ImportError as exc:
        return {"ok": False, "error": "pillow_required", "detail": str(exc)}

    w, h = cols * cell, rows_n * cell
    img = Image.new("RGB", (w, h), (8, 10, 14))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_b = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)
    except OSError:
        font = ImageFont.load_default()
        font_b = font

    colors = {
        "floppy": (94, 234, 212),
        "optical": (251, 191, 36),
        "usb": (34, 197, 94),
        "vm": (167, 139, 250),
        "tape": (148, 163, 184),
    }

    for idx, dev in enumerate(devices):
        col, row = idx % cols, idx // cols
        x0, y0 = col * cell + 8, row * cell + 8
        x1, y1 = (col + 1) * cell - 8, (row + 1) * cell - 8
        did = str(dev.get("id") or "")
        if did.startswith("floppy"):
            accent = colors["floppy"]
            draw.rounded_rectangle((x0 + 20, y0 + 16, x1 - 20, y1 - 20), radius=6, outline=accent, width=2)
            draw.rectangle((x0 + 28, y0 + 8, x0 + 44, y0 + 20), fill=accent)
        elif "cd" in did or "dvd" in did or "bd" in did:
            accent = colors["optical"]
            cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
            r = min(x1 - x0, y1 - y0) // 2 - 12
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=accent, width=2)
            draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=accent)
        elif "usb" in did or "sd" in did:
            accent = colors["usb"]
            draw.rounded_rectangle((x0 + 24, y0 + 20, x1 - 24, y1 - 16), radius=8, outline=accent, width=2)
            draw.rectangle((x1 - 36, y0 + 28, x1 - 28, y0 + 44), fill=accent)
        elif "vm" in did or "dmg" in did:
            accent = colors["vm"]
            draw.rectangle((x0 + 16, y0 + 12, x1 - 16, y1 - 12), outline=accent, width=2)
            draw.line((x0 + 16, y0 + 28, x1 - 16, y0 + 28), fill=accent, width=1)
        elif "tape" in did:
            accent = colors["tape"]
            draw.rectangle((x0 + 12, y0 + 24, x1 - 12, y1 - 24), outline=accent, width=2)
        else:
            accent = (100, 116, 139)
            draw.rounded_rectangle((x0 + 12, y0 + 12, x1 - 12, y1 - 12), radius=6, outline=accent, width=2)

        label = str(dev.get("label") or did)[:14]
        tw = draw.textlength(label, font=font_b)
        draw.text((x0 + (x1 - x0 - tw) / 2, y1 - 18), label, fill=(220, 224, 230), font=font_b)
        if dev.get("field_replace"):
            draw.text((x0 + 4, y0 + 4), "FIELD", fill=accent, font=font)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    mirror.parent.mkdir(parents=True, exist_ok=True)
    img.save(mirror, "PNG", optimize=True)

    for dev in devices:
        did = str(dev.get("id") or "")
        if not did:
            continue
        single = INSTALL / "data" / "combinatronic-visuals" / "formats" / f"bd_{did}.png"
        crop_idx = devices.index(dev)
        col, row = crop_idx % cols, crop_idx // cols
        tile = img.crop((col * cell, row * cell, (col + 1) * cell, (row + 1) * cell))
        single.parent.mkdir(parents=True, exist_ok=True)
        tile.save(single, "PNG", optimize=True)
        lib = INSTALL / "library" / "assets" / "formats" / f"bd_{did}.png"
        lib.parent.mkdir(parents=True, exist_ok=True)
        tile.save(lib, "PNG", optimize=True)

    return {"ok": True, "path": str(out), "devices": len(devices), "grid": f"{cols}x{rows_n}"}


def _safety_mod() -> Any:
    import importlib.util

    mod_path = INSTALL / "lib" / "field-non-fielded-safety.py"
    if not mod_path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_non_fielded_safety_bd", mod_path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _file_has_field_tail(path: Path) -> str | None:
    safety = _safety_mod()
    if safety and hasattr(safety, "file_has_field_tail"):
        return safety.file_has_field_tail(path)
    try:
        head = path.read_bytes()[:16]
    except OSError:
        return None
    for magic in FIELD_TAIL_MAGICS:
        if head.startswith(magic):
            return magic.decode("ascii", errors="replace")
    if head.startswith(FDRV_MAGIC):
        return "FDRV"
    if head.startswith(BLANKET_MAGIC):
        return "FLD2"
    return None


def _source_field_state(path: Path) -> dict[str, Any]:
    tail = _file_has_field_tail(path)
    ext = path.suffix.lower()
    return {
        "has_field_tail": bool(tail),
        "tail_format": tail,
        "is_fielddrive": ext == ".fielddrive",
        "field_on_field_risk": bool(tail) or ext == ".fielddrive",
    }


def _stabilizer_progress(
    *,
    job_id: str,
    phase: str,
    pct: int,
    detail: str = "",
    done: bool = False,
    error: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doc = {
        "schema": "field-big-drive-stabilizer/v1",
        "job_id": job_id,
        "phase": phase,
        "pct": max(0, min(100, pct)),
        "detail": detail,
        "done": done,
        "error": error or None,
        "ts": _now(),
        **(extra or {}),
    }
    _save(STABILIZER, doc)
    return doc


def stabilizer_status() -> dict[str, Any]:
    doc = _load(STABILIZER, {})
    if not doc:
        return {"ok": True, "idle": True, "pct": 0, "phase": "idle"}
    return {"ok": True, "idle": bool(doc.get("done")), **doc}


def _strip_field_prefix(data: bytes) -> tuple[bytes, str | None]:
    for magic in FIELD_TAIL_MAGICS:
        if data.startswith(magic):
            return data[len(magic) :], magic.decode("ascii", errors="replace")
    if data.startswith(FDRV_MAGIC) and len(data) > FIELDDRIVE_HEADER_LEN:
        return data[FIELDDRIVE_HEADER_LEN:], "FDRV"
    return data, None


def _defield_file(src: Path, dest: Path) -> dict[str, Any]:
    try:
        raw = src.read_bytes()
    except OSError as exc:
        return {"ok": False, "error": str(exc), "path": str(src)}
    flat, stripped = _strip_field_prefix(raw)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(flat)
    return {
        "ok": True,
        "source": str(src),
        "dest": str(dest),
        "stripped": stripped,
        "bytes_in": len(raw),
        "bytes_out": len(flat),
    }


def _write_blanket_manifest(
    root: Path,
    *,
    device_id: str,
    frame_bytes: int,
    partition_id: str,
    files: list[dict[str, Any]],
) -> Path:
    manifest = {
        "schema": "blanket-staging/v1",
        "magic": "FLD2\\x01",
        "ts": _now(),
        "device_id": device_id,
        "partition_id": partition_id,
        "field_depth": 0,
        "max_field_depth": 0,
        "field_on_field": False,
        "blanket": "universal_2d",
        "frame_bytes": frame_bytes,
        "files": files,
        "doctrine": "One universal 2D blanket field per device — no stacked subfields.",
    }
    path = root / "blanket-staging.json"
    _save(path, manifest)
    return path


def stabilize_drive(
    path: str,
    *,
    device_id: str = "usb_stick",
    frame_id: str = "sector_4k",
    partition_id: str = "whole",
    format_id: str = "fielddrive",
) -> dict[str, Any]:
    """Copy → defield files → field whole partition → return files. Never field-on-field."""
    src = _safe_path(path)
    if not src:
        return {"ok": False, "error": "path_not_allowed", "path": path}

    doctrine = _doctrine()
    stabilizer_doc = doctrine.get("stabilizer") or {}
    source_state = _source_field_state(src)

    frame = _frame_by_id(frame_id) or {"bytes": 4096, "id": frame_id}
    fb = int(frame.get("bytes") or 4096)
    device = _device_by_id(device_id) or {"id": device_id}
    fmt = next((f for f in doctrine.get("formats") or [] if f.get("id") == format_id), {"id": format_id})
    stamp = _now().replace(":", "").replace("-", "")
    job_id = f"stab_{stamp}"
    job_staging = STAGING / job_id
    job_return = RETURN_DIR / job_id

    phases = stabilizer_doc.get("phases") or [
        {"id": "copy", "label": "Copy to drive staging", "pct": 25},
        {"id": "defield", "label": "Defield files (flat tails)", "pct": 50},
        {"id": "field_partition", "label": "Field entire drive / partition", "pct": 75},
        {"id": "return_files", "label": "Return files to operator", "pct": 100},
    ]

    _stabilizer_progress(job_id=job_id, phase="copy", pct=0, detail="Copying to staging…")

    if job_staging.exists():
        shutil.rmtree(job_staging, ignore_errors=True)
    if job_return.exists():
        shutil.rmtree(job_return, ignore_errors=True)
    job_staging.mkdir(parents=True, exist_ok=True)
    job_return.mkdir(parents=True, exist_ok=True)

    staged_name = src.name
    staged_path = job_staging / staged_name
    shutil.copy2(src, staged_path)
    _stabilizer_progress(
        job_id=job_id,
        phase="copy",
        pct=int(phases[0].get("pct", 25)),
        detail=f"Copied {staged_name}",
    )

    _stabilizer_progress(job_id=job_id, phase="defield", pct=25, detail="Stripping field tails…")
    defielded_path = job_staging / f"defield_{staged_name}"
    defield_rep = _defield_file(staged_path, defielded_path)
    if not defield_rep.get("ok"):
        _stabilizer_progress(job_id=job_id, phase="defield", pct=25, detail="Defield failed", error=defield_rep.get("error", "defield_failed"))
        return {"ok": False, "error": "defield_failed", **defield_rep}

    _stabilizer_progress(
        job_id=job_id,
        phase="defield",
        pct=int(phases[1].get("pct", 50)),
        detail=f"Defielded — stripped {defield_rep.get('stripped') or 'none'}",
        extra={"defield": defield_rep},
    )

    _stabilizer_progress(job_id=job_id, phase="field_partition", pct=50, detail="Raising universal 2D blanket…")
    manifest = _write_blanket_manifest(
        job_staging,
        device_id=device_id,
        frame_bytes=fb,
        partition_id=partition_id,
        files=[{"name": defielded_path.name, "bytes": defielded_path.stat().st_size, "defielded": True}],
    )

    FIELD_DRIVE_DIR.mkdir(parents=True, exist_ok=True)
    out_name = f"bigdrive_{device_id}_{partition_id}_{stamp}.fielddrive"
    field_dest = FIELD_DRIVE_DIR / out_name
    _write_fielddrive_header(
        field_dest,
        frame_bytes=fb,
        source=str(src),
        fmt_id=str(fmt.get("id") or "fielddrive"),
    )
    with field_dest.open("ab") as out, defielded_path.open("rb") as inp:
        shutil.copyfileobj(inp, out)

    blanket_marker = job_staging / ".field-blanket.marker"
    blanket_marker.write_bytes(BLANKET_MAGIC + partition_id.encode("utf-8")[:28].ljust(28, b"\x00"))

    _stabilizer_progress(
        job_id=job_id,
        phase="field_partition",
        pct=int(phases[2].get("pct", 75)),
        detail=f"Blanket field on {partition_id} — depth 0",
        extra={"manifest": str(manifest), "blanket": "universal_2d"},
    )

    _stabilizer_progress(job_id=job_id, phase="return_files", pct=75, detail="Returning files…")
    returned_copy = job_return / staged_name
    shutil.copy2(defielded_path, returned_copy)
    shutil.copy2(manifest, job_return / "blanket-staging.json")
    digest = _sha256_file(field_dest)

    result = {
        "ok": True,
        "action": "stabilize",
        "job_id": job_id,
        "source": str(src),
        "dest": str(field_dest),
        "return_dir": str(job_return),
        "returned_file": str(returned_copy),
        "sha256": digest,
        "device": device,
        "frame": frame,
        "partition_id": partition_id,
        "blanket": "universal_2d",
        "field_depth": 0,
        "field_on_field": False,
        "defield": defield_rep,
        "source_state": source_state,
        "message": "Stabilized — copy, defield, blanket field, files returned. No double fields.",
    }
    _stabilizer_progress(
        job_id=job_id,
        phase="return_files",
        pct=100,
        detail="Done — files returned",
        done=True,
        extra={"result": {k: v for k, v in result.items() if k != "ok"}},
    )
    return result


def _write_fielddrive_header(path: Path, *, frame_bytes: int, source: str, fmt_id: str) -> None:
    header = FDRV_MAGIC + struct.pack(">QII", frame_bytes, len(source), int(time.time()))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(header)
        f.write(source.encode("utf-8")[:256].ljust(256, b"\x00"))
        f.write(fmt_id.encode("utf-8")[:32].ljust(32, b"\x00"))


def plan_drive(
    *,
    frame_id: str = "sector_4k",
    frame_bytes: int = 0,
    device_id: str = "usb_stick",
    format_id: str = "fielddrive",
    source_path: str = "",
) -> dict[str, Any]:
    doctrine = _doctrine()
    frame = _frame_by_id(frame_id) or {}
    if frame_bytes > 0:
        frame = {**frame, "id": "custom", "bytes": frame_bytes, "label": f"Custom {frame_bytes:,} B"}
    elif not frame:
        frame = {"id": frame_id, "bytes": 4096, "label": frame_id}
    device = _device_by_id(device_id) or {}
    fmt = next((f for f in doctrine.get("formats") or [] if f.get("id") == format_id), {"id": format_id})
    src = _safe_path(source_path) if source_path else None
    sectors = 0
    fb = int(frame.get("bytes") or 4096)
    if src and fb > 0:
        sectors = (src.stat().st_size + fb - 1) // fb
    out_name = f"bigdrive_{device_id}_{format_id}.fielddrive"
    return {
        "ok": True,
        "frame": frame,
        "device": device,
        "format": fmt,
        "source": str(src) if src else None,
        "sectors": sectors,
        "output": str(FIELD_DRIVE_DIR / out_name),
        "persistence": doctrine.get("persistence"),
        "action_hint": "field_seal" if device.get("field_replace") else "ingest",
    }


def ingest_source(path: str, *, action: str = "ingest") -> dict[str, Any]:
    src = _safe_path(path)
    if not src:
        return {"ok": False, "error": "path_not_allowed", "path": path}
    fmt = _format_for_path(src)
    WORK.mkdir(parents=True, exist_ok=True)
    FIELD_DRIVE_DIR.mkdir(parents=True, exist_ok=True)
    digest = _sha256_file(src)
    stamp = _now().replace(":", "").replace("-", "")
    base = f"{src.stem}_{stamp}"
    if action == "copy_iso" and src.suffix.lower() == ".iso":
        dest = WORK / f"{base}.iso"
        shutil.copy2(src, dest)
        return {"ok": True, "action": action, "source": str(src), "dest": str(dest), "sha256": digest, "format": fmt}
    if action in ("field_seal", "replace_usb", "stabilize"):
        return stabilize_drive(
            str(src),
            device_id=str(os.environ.get("NEXUS_BIG_DRIVE_DEVICE", "usb_stick")),
            frame_id=str(os.environ.get("NEXUS_BIG_DRIVE_FRAME", "sector_4k")),
        )
    if action == "ingest":
        dest = FIELD_DRIVE_DIR / f"{base}.fielddrive"
        _write_fielddrive_header(dest, frame_bytes=4096, source=str(src), fmt_id=(fmt or {}).get("id", "img"))
        with dest.open("ab") as out, src.open("rb") as inp:
            shutil.copyfileobj(inp, out)
        return {
            "ok": True,
            "action": action,
            "source": str(src),
            "dest": str(dest),
            "sha256": digest,
            "format": fmt,
            "sovereign": True,
            "message": "Sealed to Field Drive — USB transport optional; field is permanent home.",
        }
    if action == "boot_iso":
        dest = WORK / f"{base}_boot.iso"
        shutil.copy2(src, dest)
        return {"ok": True, "action": action, "boot": True, "dest": str(dest), "sha256": digest}
    return {"ok": False, "error": "unknown_action", "action": action}


def posture() -> dict[str, Any]:
    doctrine = _doctrine()
    grid = render_device_grid()
    doc = {
        "schema": "field-big-drive/v1",
        "ts": _now(),
        "ok": True,
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "panel": doctrine.get("panel"),
        "canonical_format": doctrine.get("canonical_format"),
        "persistence": doctrine.get("persistence"),
        "frame_sizes": doctrine.get("frame_sizes"),
        "devices": doctrine.get("devices"),
        "formats": doctrine.get("formats"),
        "format_families": doctrine.get("format_families"),
        "big_drive_extensions": doctrine.get("big_drive_extensions"),
        "device_grid": {
            "path": str(ICON_GRID.relative_to(INSTALL)) if ICON_GRID.is_file() else doctrine.get("icons", {}).get("device_grid"),
            "url": "/assets/formats/big_drive_devices.png",
            "render": grid,
        },
        "actions": doctrine.get("actions"),
        "stabilizer": doctrine.get("stabilizer"),
        "thermal": doctrine.get("thermal"),
        "single_field": doctrine.get("single_field"),
        "work_dir": str(WORK),
        "field_drive_dir": str(FIELD_DRIVE_DIR),
        "stabilizer_state": str(STABILIZER),
    }
    _save(PANEL, doc)
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "posture"):
        return posture()
    if action == "plan":
        return plan_drive(
            frame_id=str(body.get("frame_id") or "sector_4k"),
            frame_bytes=int(body.get("frame_bytes") or 0),
            device_id=str(body.get("device_id") or "usb_stick"),
            format_id=str(body.get("format_id") or "fielddrive"),
            source_path=str(body.get("path") or body.get("source_path") or ""),
        )
    if action in ("stabilizer_progress", "stabilizer_status"):
        return stabilizer_status()
    if action == "stabilize":
        return stabilize_drive(
            str(body.get("path") or ""),
            device_id=str(body.get("device_id") or "usb_stick"),
            frame_id=str(body.get("frame_id") or "sector_4k"),
            partition_id=str(body.get("partition_id") or "whole"),
            format_id=str(body.get("format_id") or "fielddrive"),
        )
    if action in ("ingest", "copy_iso", "field_seal", "burn_read", "vm_attach", "boot_iso", "replace_usb"):
        return ingest_source(str(body.get("path") or ""), action=action)
    if action == "render_icons":
        return render_device_grid(force=bool(body.get("force")))
    if action == "eligible":
        path = str(body.get("path") or "")
        ext = Path(path).suffix.lower()
        exts = set(e.lower() for e in (_doctrine().get("big_drive_extensions") or []))
        return {"ok": True, "eligible": ext in exts, "extension": ext, "format": _format_for_path(Path(path))}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "render_icons":
        print(json.dumps(render_device_grid(force=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False, indent=2))
        return 0 if dispatch(body).get("ok", True) else 1
    print(json.dumps({"usage": "field-big-drive.py [json|render_icons|dispatch]"}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())