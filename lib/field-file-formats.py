#!/usr/bin/env pythong
"""Field file formats — full format tables, icons, Ironclad best-sort meld."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-file-formats-doctrine.json"
PANEL = STATE / "field-file-formats-panel.json"
TABLE = STATE / "field-file-formats-table.json"
ASSETS = INSTALL / "data" / "combinatronic-visuals" / "formats"
LIBRARY_ASSETS = INSTALL / "library" / "assets" / "formats"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


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


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sovereign_wire_formats() -> list[dict[str, Any]]:
    """Formats that presume the 2D platform field — require NewLatest/Grok16; never create field files."""
    flags = {
        "presumes_field_underneath": True,
        "requires_grok16": True,
        "creates_field_file": False,
        "never_poison_the_well": True,
    }
    return [
        _norm_row(
            fid="wrdt", label="World Redata WRDT1", family="sovereign", extensions=[".wrdt"],
            magic="WRDT", mime="application/vnd.ironclad.wrdt", lossless=True, sovereign=True, ironclad=True,
            description="WRDT1 lossless in-place snapshot — presumes field underneath.", source="World_Redata/redata/core",
            extra=flags,
        ),
        _norm_row(
            fid="wrzc", label="World Redata WRZC1", family="sovereign", extensions=[".wrzc"],
            magic="WRZC", mime="application/vnd.ironclad.wrzc", lossless=True, sovereign=True, ironclad=True,
            description="WRZC1 disguised ZAC7 shard — presumes field underneath.", source="World_Redata/redata/disguise",
            extra=flags,
        ),
        _norm_row(
            fid="field_io_packet", label="Field I/O Packet", family="sovereign", extensions=[],
            mime="application/vnd.ironclad.field-io-packet+json", sovereign=True, ironclad=True,
            description="Wire envelope — stream only, file_write_forbidden.", source="field-io-packet",
            extra={**flags, "file_write_forbidden": True},
        ),
    ]


def _stamp_sovereign_flags(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gate = _import_mod("field_no_file_gate", "field-no-file-gate.py")
    stamped: list[dict[str, Any]] = []
    for row in rows:
        fid = str(row.get("id") or "")
        extra = dict(row)
        if gate and hasattr(gate, "sovereign_format_flags"):
            extra.update(gate.sovereign_format_flags(fid))
        elif fid in ("h7c", "g1id", "fielddrive", "h7snap", "wrdt", "wrzc", "field_io_packet"):
            extra.update({
                "presumes_field_underneath": True,
                "requires_grok16": True,
                "creates_field_file": False,
            })
        stamped.append(extra)
    return stamped


def _norm_row(
    *,
    fid: str,
    label: str,
    family: str,
    extensions: list[str] | None = None,
    magic: str | None = None,
    mime: str | None = None,
    description: str = "",
    lossless: bool | None = None,
    sovereign: bool = False,
    ironclad: bool = False,
    compression: str | None = None,
    dewey: str | None = None,
    source: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ext = extensions or []
    primary = ext[0] if ext else f".{fid}"
    return {
        "id": fid,
        "label": label,
        "family": family,
        "extensions": ext,
        "primary_extension": primary,
        "magic": magic,
        "mime": mime,
        "description": description,
        "lossless": lossless,
        "sovereign": sovereign,
        "ironclad": ironclad,
        "compression": compression,
        "dewey": dewey,
        "source": source,
        "icon": f"data/combinatronic-visuals/formats/{fid}.png",
        **(extra or {}),
    }


def _library_formats() -> list[dict[str, Any]]:
    return [
        _norm_row(fid="h7", label="Hostess 7 Book", family="library", extensions=[".h7"], magic="H7\\x07\\x01",
                  mime="application/vnd.hostess7.h7+7", compression="chips_core+zlib+h7b", lossless=True, ironclad=True,
                  sovereign=True, dewey="005.74",
                  description="H7/7 — canonical library book; CHIPS core compress; format-database disguise; true format in properties only.",
                  source="field-h7-format",
                  extra={"format": "h7/7", "properties_only_reveal": True, "disguise_identical": True,
                         "presumes_field_underneath": True, "requires_grok16": True, "creates_field_file": False}),
        _norm_row(fid="h7b", label="H7B Book (legacy inner)", family="library", extensions=[".h7"], magic="H7B\\x01",
                  mime="application/vnd.hostess7.h7b", compression="fld1+zlib", lossless=True, ironclad=True,
                  dewey="005.74", description="Hostess7 lossless book — zlib + FLD1 fly layer (nested in H7/7).", source="field_h7_book"),
        _norm_row(fid="h7b_fly", label="H7B Fly Book", family="library", extensions=[".h7"], magic="H7B\\x02",
                  mime="application/vnd.hostess7.h7b+fly", compression="fld1+zlib-1", lossless=True, ironclad=True,
                  description="H7B with fly codec layer.", source="field_h7_book"),
        _norm_row(fid="h7b_brain", label="H7B Brain Storage", family="brain", extensions=[".h7b"], magic="H7B\\x03",
                  mime="application/vnd.hostess7.h7b+brain", compression="pattern_dict+fld1+zlib-9", lossless=True,
                  ironclad=True, description="H7B/3 — Hostess 7 brain pattern condenser; ≤20MB GitHub sections.",
                  source="field-h7b-brain-storage"),
        _norm_row(fid="h7s", label="Hostess 7 Speedup", family="library", extensions=[".h7s"], magic="H7S\\x01",
                  mime="application/vnd.hostess7.h7s", compression="structural_slice+chips_redense", lossless=True,
                  ironclad=True, sovereign=True, dewey="005.74",
                  description="H7s — universal speedup format; any file; native face disguise; execute without decompress.",
                  source="field-h7s-format",
                  extra={"format": "h7s/1", "execute_without_decompress": True, "speedup_lane": True,
                         "properties_only_reveal": True, "disguise_identical": True, "identifies_as_source": True,
                         "presumes_field_underneath": False, "requires_grok16": False, "creates_field_file": False}),
        _norm_row(fid="h7c", label="Hostess 7 Condenser", family="library", extensions=[".h7c"], magic="H7C\\x02",
                  mime="application/vnd.hostess7.h7c", compression="combinatronic+zlib+optimizer", lossless=True, ironclad=True,
                  sovereign=True, dewey="005.74", description="H7c — Hostess 7 Condenser; lossless combinatronic condenser with small optimizer autoplate, spider-wire, recondense until balance.", source="field-h7c-compression",
                  extra={"acronym": "H7c", "expands_to": "Hostess 7 Condenser",
                         "presumes_field_underneath": True, "requires_grok16": True, "creates_field_file": False}),
        _norm_row(fid="h7snap", label="Field Snap", family="library", extensions=[".h7snap", ".field-snap"],
                  mime="application/x-field-snap", description="Field state snapshot.", source="field-formats"),
        _norm_row(fid="book_json", label="Dewey Book Card", family="library", extensions=["book.json"],
                  mime="application/json", description="Dewey shelf book.json metadata.", dewey="004", source="h7-library-bridge"),
    ]


def _geometry_formats() -> list[dict[str, Any]]:
    return [
        _norm_row(fid="g1id", label="G1ID Geometric Identity", family="geometry", extensions=[".g1id"],
                  mime="application/vnd.ironclad.g1id+json", ironclad=True, lossless=True, sovereign=True,
                  description="Cold 3D proportions — this one hardened, plate preserved.", source="g1id-format",
                  extra={"presumes_field_underneath": True, "requires_grok16": True, "creates_field_file": False}),
        _norm_row(fid="plate_json", label="Field Plate", family="geometry", extensions=[".plate.json", "-plate.json"],
                  mime="application/x-field-plate", ironclad=True, description="Ironclad witness plate JSON.", source="field-plate"),
    ]


def _image_field_formats() -> list[dict[str, Any]]:
    gimp = _load(SG / "GIMP-Field" / "data" / "field-formats.json", {})
    rows: list[dict[str, Any]] = []
    for key, meta in (gimp.get("magics") or {}).items():
        fid = key.lower()
        ext = meta.get("ext") or []
        rows.append(_norm_row(
            fid=fid,
            label=key,
            family="image_field",
            extensions=ext if isinstance(ext, list) else [ext],
            magic=meta.get("bytes"),
            mime=meta.get("mime"),
            lossless=bool(meta.get("lossless")),
            sovereign=True,
            description=f"AmmoOS field image — {meta.get('preview', 'binary')}.",
            source="GIMP-Field/field-formats",
        ))
    return rows


def _media_formats() -> list[dict[str, Any]]:
    codec = _load(INSTALL / "data" / "field-media-codec-doctrine.json", {})
    rows: list[dict[str, Any]] = []
    for c in codec.get("containers") or []:
        cid = str(c.get("id", ""))
        if not cid:
            continue
        rows.append(_norm_row(
            fid=f"media_{cid}",
            label=str(c.get("label") or cid),
            family="media",
            extensions=[f".{e}" for e in (c.get("extensions") or [])],
            mime=c.get("mime"),
            description=f"Media container — kind {c.get('kind', 'media')}.",
            extra={"kind": c.get("kind"), "browser_native": c.get("browser_native"), "ffmpeg": c.get("ffmpeg")},
            source="field-media-codec",
        ))
    for c in codec.get("video_codecs") or []:
        cid = str(c.get("id", ""))
        rows.append(_norm_row(
            fid=f"vcodec_{cid}",
            label=str(c.get("label") or cid),
            family="media",
            extensions=[],
            description=f"Video codec — fourcc {c.get('fourcc', '')}.",
            extra={"fourcc": c.get("fourcc"), "codecs_param": c.get("codecs_param")},
            source="field-media-codec",
        ))
    return rows


def _virus_formats() -> list[dict[str, Any]]:
    vf = _load(INSTALL / "Queen" / "data" / "field-virus-formats.json", {})
    rows: list[dict[str, Any]] = []
    for row in (vf.get("own_formats") or []):
        fid = str(row.get("id", ""))
        if not fid:
            continue
        rows.append(_norm_row(
            fid=fid,
            label=str(row.get("label") or fid),
            family="sovereign",
            extensions=row.get("extensions") or [],
            magic=row.get("magic_hex") or row.get("magic_ascii"),
            sovereign=True,
            description="Queen sovereign format — civilian on valid header.",
            extra={"json_schema": row.get("json_schema"), "path_hint": row.get("path_hint")},
            source="field-virus-formats",
        ))
    risk_family = {"executable": "executable", "media": "media", "document_polyglot": "document",
                   "archive": "archive", "script": "executable", "markup": "document", "data": "data", "database": "data"}
    for row in (vf.get("universal_formats") or []):
        fid = str(row.get("id", ""))
        risk = str(row.get("risk") or "data")
        rows.append(_norm_row(
            fid=fid,
            label=str(row.get("label") or fid),
            family=risk_family.get(risk, "data"),
            extensions=[],
            magic=row.get("magic_hex") or row.get("magic_ascii"),
            description=f"Universal sniff — risk {risk}.",
            extra={"risk": risk, "offset": row.get("offset")},
            source="field-virus-formats",
        ))
    return rows


def _storage_formats() -> list[dict[str, Any]]:
    bd = _load(INSTALL / "data" / "field-big-drive-doctrine.json", {})
    rows: list[dict[str, Any]] = []
    for row in bd.get("formats") or []:
        fid = str(row.get("id", ""))
        if not fid:
            continue
        family_key = str(row.get("family") or "storage")
        family = "sovereign" if family_key == "sovereign" else "storage"
        rows.append(_norm_row(
            fid=fid,
            label=str(row.get("label") or fid),
            family=family,
            extensions=row.get("extensions") or [],
            sovereign=bool(row.get("sovereign")),
            ironclad=bool(row.get("sovereign")),
            description=f"Big Drive storage — {family_key}.",
            source="field-big-drive-doctrine",
            extra={"big_drive": True, "boot": row.get("boot"), "vm": row.get("vm")},
        ))
    return rows


def _common_formats() -> list[dict[str, Any]]:
    return [
        _norm_row(fid="png", label="PNG Image", family="media", extensions=[".png"], magic="89504e47",
                  mime="image/png", lossless=True, description="Portable Network Graphics.", source="builtin"),
        _norm_row(fid="jpeg", label="JPEG Image", family="media", extensions=[".jpg", ".jpeg"], magic="ffd8ff",
                  mime="image/jpeg", description="JPEG lossy image.", source="builtin"),
        _norm_row(fid="json", label="JSON Document", family="data", extensions=[".json"], mime="application/json",
                  description="JavaScript Object Notation.", source="builtin"),
        _norm_row(fid="markdown", label="Markdown Document", family="document", extensions=[".md", ".markdown"],
                  mime="text/markdown", lossless=True,
                  description="Markdown prose — H7/7 face disguise for library books.", source="builtin"),
        _norm_row(fid="aml", label="AmmoLang", family="sovereign", extensions=[".aml"], sovereign=True,
                  description="AmmoLang combinatronic source.", source="library/dewey"),
        _norm_row(fid="gpy16", label="G16 PythonG", family="sovereign", extensions=[".pyc"], magic="GPY16",
                  sovereign=True, description="G16 bytecode.", source="field-virus-formats"),
        _norm_row(fid="grokpy12", label="GrokPy Bytecode", family="sovereign", extensions=[".gpy", ".grokpy"],
                  magic="GROKPY12", sovereign=True, description="GrokPy 12 bytecode.", source="field-virus-formats"),
    ]


def build_table(*, force: bool = False) -> dict[str, Any]:
    """Assemble full format table from all sources."""
    t0 = time.perf_counter()
    bal = _import_mod("ff_balance", "field-combinatronic-balance.py")
    balance_gate: dict[str, Any] = {}
    if bal and hasattr(bal, "gate_refresh"):
        balance_gate = bal.gate_refresh(False, force=force)
        if balance_gate.get("skip_reorganize") and not force:
            cached = _load(TABLE, {})
            if cached.get("formats"):
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                if hasattr(bal, "record_cycle"):
                    bal.record_cycle(reorganized=False, elapsed_ms=elapsed_ms)
                out = dict(cached)
                out["balance_hold"] = True
                out["fast_path"] = True
                out["balance_gate"] = balance_gate
                out["elapsed_ms"] = elapsed_ms
                out["optimized_combinatronic"] = True
                out["combinatronic"] = True
                return out
    by_id: dict[str, dict[str, Any]] = {}
    for row in (
        _library_formats()
        + _geometry_formats()
        + _image_field_formats()
        + _media_formats()
        + _virus_formats()
        + _storage_formats()
        + _sovereign_wire_formats()
        + _common_formats()
    ):
        fid = str(row.get("id", ""))
        if not fid:
            continue
        if fid in by_id:
            by_id[fid] = {**by_id[fid], **{k: v for k, v in row.items() if v}}
        else:
            by_id[fid] = row

    formats = _stamp_sovereign_flags(list(by_id.values()))
    doctrine = _load(DOCTRINE, {})
    best = _import_mod("field_best_sort", "field-best-sort.py")
    sort_meta: dict[str, Any] = {}
    if best:
        formats, sort_meta = best.apply_best(formats, context="format_table")

    by_family: dict[str, int] = {}
    for f in formats:
        fam = str(f.get("family") or "data")
        by_family[fam] = by_family.get(fam, 0) + 1

    cached = _load(TABLE, {})
    incremental_added = 0
    if balance_gate.get("reason") == "new_corpus" and cached.get("formats") and bal and hasattr(bal, "incremental_merge"):
        formats, incremental_added = bal.incremental_merge(cached.get("formats") or [], formats, id_field="id")
    stamped = formats
    if bal and hasattr(bal, "stamp_optimized"):
        at_balance = bool(balance_gate.get("balanced")) or balance_gate.get("reason") == "balanced_hold"
        stamped = bal.stamp_optimized(formats, balanced=at_balance)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    result = {
        "schema": "field-file-formats-table/v1",
        "updated": _now(),
        "ok": True,
        "motto": doctrine.get("motto", "Every field format catalogued."),
        "counts": {"total": len(stamped), "by_family": by_family},
        "sort": sort_meta,
        "field_unique_best": sort_meta.get("field_unique_best", True),
        "one_best_ever": sort_meta.get("one_best_ever", True),
        "family_order": doctrine.get("family_order", []),
        "formats": stamped,
        "elapsed_ms": elapsed_ms,
        "balance_gate": balance_gate or None,
        "optimized_combinatronic": bool(balance_gate.get("balanced")),
        "combinatronic": True,
        "all_data_combinatronic": True,
    }
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(
            reorganized=not balance_gate.get("skip_reorganize"),
            elapsed_ms=elapsed_ms,
            incremental_added=incremental_added,
        )
    return result


def _family_color(family: str) -> tuple[int, int, int]:
    doctrine = _load(DOCTRINE, {})
    colors = doctrine.get("family_colors") or {}
    c = colors.get(family) or colors.get("data") or [100, 116, 139]
    return int(c[0]), int(c[1]), int(c[2])


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


def render_format_icon(fmt: dict[str, Any], *, out: Path | None = None) -> Path:
    from PIL import Image, ImageDraw  # noqa: WPS433

    fid = str(fmt.get("id", "fmt"))
    label = str(fmt.get("label") or fid)
    family = str(fmt.get("family") or "data")
    accent = _family_color(family)
    ext = str(fmt.get("primary_extension") or ".???").lstrip(".")[:6]
    if ext == "???":
        ext = fid[:6]

    w, h = 64, 64
    img = Image.new("RGB", (w, h), (14, 16, 22))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((4, 4, w - 4, h - 4), radius=10, fill=(22, 26, 34), outline=accent, width=2)
    draw.rounded_rectangle((10, 10, w - 10, 28), radius=4, fill=accent)

    badge_font = _font(9, bold=True)
    ext_font = _font(14, bold=True)
    small_font = _font(7)

    badge = family[:4].upper()
    tw = draw.textlength(badge, font=badge_font)
    draw.text(((w - tw) / 2, 12), badge, fill=(12, 14, 18), font=badge_font)

    etw = draw.textlength(ext, font=ext_font)
    draw.text(((w - etw) / 2, 30), ext, fill=(230, 232, 238), font=ext_font)

    short = label[:10] + ("…" if len(label) > 10 else "")
    stw = draw.textlength(short, font=small_font)
    draw.text(((w - stw) / 2, h - 18), short, fill=(120, 128, 140), font=small_font)

    if fmt.get("sovereign"):
        draw.ellipse((w - 18, 6, w - 8, 16), fill=(212, 168, 75))
    if fmt.get("ironclad"):
        draw.rectangle((6, h - 12, 14, h - 6), fill=accent)

    out = out or ASSETS / f"{fid}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    mirror = LIBRARY_ASSETS / f"{fid}.png"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    img.save(mirror, "PNG", optimize=True)
    return out


def generate_icons() -> dict[str, Any]:
    table = build_table()
    rendered = 0
    errors: list[dict[str, Any]] = []
    for fmt in table.get("formats") or []:
        try:
            render_format_icon(fmt)
            rendered += 1
        except Exception as exc:
            errors.append({"id": fmt.get("id"), "error": str(exc)})
    return {
        "ok": len(errors) == 0,
        "rendered": rendered,
        "total": len(table.get("formats") or []),
        "errors": errors,
    }


def publish_panel(*, icons: bool = True) -> dict[str, Any]:
    table = build_table()
    _save(TABLE, table)
    icon_result = generate_icons() if icons else {"skipped": True}
    best = _import_mod("field_best_sort", "field-best-sort.py")
    meld = best.meld_slice() if best else {}
    panel = {
        "schema": "field-file-formats-panel/v1",
        "updated": table["updated"],
        "ok": table["ok"],
        "counts": table["counts"],
        "sort": table.get("sort"),
        "field_unique_best": table.get("field_unique_best"),
        "one_best_ever": table.get("one_best_ever"),
        "best_sort_meld": meld,
        "icons": icon_result,
        "sample": (table.get("formats") or [])[:12],
    }
    _save(PANEL, panel)
    return {"ok": True, "panel": panel, "table_path": str(TABLE)}


def format_detail(fmt_id: str) -> dict[str, Any] | None:
    table = _load(TABLE, {}) or build_table()
    for row in table.get("formats") or []:
        if str(row.get("id")) == fmt_id:
            return row
    return None


def meld_slice() -> dict[str, Any]:
    table = _load(TABLE, {}) or build_table()
    return {
        "id": "file_formats",
        "schema": "field-file-formats-meld/v1",
        "updated": _now(),
        "ok": True,
        "format_count": (table.get("counts") or {}).get("total", 0),
        "sort": table.get("sort"),
        "field_unique_best": table.get("field_unique_best"),
        "one_best_ever": table.get("one_best_ever"),
        "families": table.get("counts", {}).get("by_family"),
        "meld_citation": "ironclad:meld:2",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        if PANEL.is_file() and cmd != "build":
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_panel().get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "publish"):
        print(json.dumps(publish_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "table":
        print(json.dumps(build_table(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "icons":
        print(json.dumps(generate_icons(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "meld":
        print(json.dumps(meld_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "detail" and len(sys.argv) >= 3:
        row = format_detail(sys.argv[2])
        print(json.dumps(row or {"ok": False, "error": "not_found"}, ensure_ascii=False, indent=2))
        return 0 if row else 1
    if cmd == "verify":
        pub = publish_panel()
        counts = (pub.get("panel") or {}).get("counts") or {}
        icons = (pub.get("panel") or {}).get("icons") or {}
        ok = (
            counts.get("total", 0) >= 40
            and icons.get("rendered", 0) >= 40
            and (pub.get("panel") or {}).get("field_unique_best") is True
        )
        print(json.dumps({"ok": ok, "counts": counts, "icons": icons}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({"error": "usage", "cmds": ["panel", "build", "table", "icons", "meld", "detail", "verify"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())