#!/usr/bin/env pythong
"""Final_Eye AI connection bridge — auto-wire Grok build, AmmoLang, agents; OCR command vocabulary."""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent)))
DOCTRINE = INSTALL / "data" / "final-eye-ai-connections-doctrine.json"

# Familiar OCR verbs → Final_Eye subaction (tesseract, pytesseract, generic AI tools).
OCR_ACTION_ALIASES: dict[str, str] = {
    "ocr": "ocr",
    "recognize": "ocr",
    "recognise": "ocr",
    "scan": "ocr",
    "extract": "ocr",
    "extract_text": "ocr",
    "text_from_image": "ocr",
    "image_to_string": "ocr",
    "image_to_text": "ocr",
    "image_to_pdf": "pdf",
    "image_to_boxes": "boxes",
    "image_to_data": "tsv",
    "image_to_osd": "osd",
    "image_to_hocr": "hocr",
    "image_to_alto_xml": "hocr",
    "hocr": "hocr",
    "pdf": "pdf",
    "tsv": "tsv",
    "box": "boxes",
    "boxes": "boxes",
    "osd": "osd",
    "tesseract": "ocr",
    "read": "read",
    "read_text": "read",
    "read_ocr": "read",
    "look": "look",
    "watch": "look",
    "vision": "look",
    "poll": "look",
    "status": "status",
    "json": "status",
    "posture": "status",
    "smoke": "smoke",
    "browser_smoke": "smoke",
    "browser-smoke": "smoke",
}

# Tesseract output targets → internal format key.
TESSERACT_OUTPUT_FORMATS = frozenset(
    {"stdout", "txt", "text", "hocr", "pdf", "tsv", "box", "osd", "alto", "wordstrbox"}
)


def _truthy(val: str | None) -> bool:
    return str(val or "").strip().lower() not in ("", "0", "false", "no", "off")


def _load_doctrine() -> dict[str, Any]:
    try:
        return json.loads(DOCTRINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def detect_ai_connections() -> dict[str, Any]:
    """Detect active AI / build contexts without operator configuration."""
    inst = INSTALL if INSTALL.is_dir() else _LIB.parent
    sg = SG if SG.is_dir() else inst.parent
    fe_root = Path(os.environ.get("FINAL_EYE_ROOT", str(inst / "Final_Eye"))).expanduser()
    queen = Path(os.environ.get("QUEEN_ROOT", str(inst / "Queen"))).expanduser()
    grok16 = Path(os.environ.get("GROK16_ROOT", str(inst / "Grok16"))).expanduser()
    hostess = Path(os.environ.get("HOSTESS7_ROOT", str(inst / "Hostess7"))).expanduser()
    aml_lib = Path(os.environ.get("AML_LIB", str(inst / "library/dewey/000-computer-science/ammolang")))

    grok_build = (
        _truthy(os.environ.get("GROK_BUILD"))
        or _truthy(os.environ.get("QUEEN_GROK_BUILD_SECURE"))
        or (inst / "KILROY").is_dir()
        or (grok16 / "python" / "driver").is_dir()
    )
    ammolang = _truthy(os.environ.get("AML_BUILD")) or aml_lib.is_dir()
    grok_agent = any(
        _truthy(os.environ.get(k))
        for k in ("GROK_AGENT", "GROK_SESSION", "CURSOR_AGENT", "COMPOSER_AGENT", "XAI_AGENT")
    )
    mcp = _truthy(os.environ.get("MCP_SERVER")) or bool(os.environ.get("MCP_TOOL"))
    queen_live = queen.is_dir() and (queen / "lib" / "queen_final_eye.py").is_file()
    hostess_live = hostess.is_dir() and (inst / "lib" / "hostess7-ocr-control.py").is_file()
    final_eye_live = fe_root.is_dir() and (fe_root / "zocr.py").is_file()
    tesseract_bin = shutil.which("tesseract")

    connections: list[dict[str, Any]] = []
    if grok_build:
        connections.append({"id": "grok_build", "label": "Grok Build / KILROY", "auto": True})
    if ammolang:
        connections.append({"id": "ammolang", "label": "AmmoLang kit", "auto": True})
    if grok_agent:
        connections.append({"id": "grok_agent", "label": "Grok / Cursor agent", "auto": True})
    if mcp:
        connections.append({"id": "mcp", "label": "MCP tool host", "auto": True})
    if hostess_live:
        connections.append({
            "id": "hostess7",
            "label": "Hostess7 OCR control — trusted commander",
            "bridge": "lib/hostess7-ocr-control.py",
            "seal": "lib/final-eye-hostess7-seal.py",
            "handshake_only": True,
            "trusted": True,
        })
    if queen_live:
        connections.append({
            "id": "queen",
            "label": "Queen eyeball (via Hostess7 only)",
            "bridge": "Queen/lib/queen_final_eye.py",
            "handshake_only": True,
            "trusted": False,
            "note": "Direct Queen OCR dispatch rejected — use /api/hostess7/ocr",
        })
    if final_eye_live:
        connections.append({"id": "final_eye", "label": "Final_Eye zocr", "engine": "Final_Eye/zocr.py"})
    if tesseract_bin:
        connections.append({"id": "tesseract", "label": "System tesseract", "path": tesseract_bin})

    primary = "hostess7"

    return {
        "schema": "final-eye-ai-connections/v1",
        "primary": primary,
        "connections": connections,
        "paths": {
            "nexus_install_root": str(inst),
            "sg_root": str(sg),
            "final_eye_root": str(fe_root),
            "queen_root": str(queen),
            "grok16_root": str(grok16),
            "hostess7_root": str(hostess),
            "ammolang_lib": str(aml_lib),
        },
        "flags": {
            "grok_build": grok_build,
            "ammolang": ammolang,
            "grok_agent": grok_agent,
            "mcp": mcp,
            "tesseract_available": bool(tesseract_bin),
        },
        "doctrine": str(DOCTRINE) if DOCTRINE.is_file() else None,
    }


def wire_ai_env(*, force: bool = False) -> dict[str, str]:
    """Apply env defaults so Final_Eye works under Grok build and AI hosts automatically."""
    inst = INSTALL if INSTALL.is_dir() else _LIB.parent
    sg = SG if SG.is_dir() else inst.parent
    updates: dict[str, str] = {}

    def _set(key: str, val: str) -> None:
        if force or not os.environ.get(key, "").strip():
            os.environ[key] = val
            updates[key] = val

    _set("NEXUS_INSTALL_ROOT", str(inst))
    _set("SG_ROOT", str(sg))
    _set("FINAL_EYE_ROOT", str(inst / "Final_Eye"))
    _set("QUEEN_ROOT", str(inst / "Queen"))
    _set("HOSTESS7_ROOT", str(inst / "Hostess7"))
    _set("GROK16_ROOT", str(inst / "Grok16"))
    _set("AML_LIB", str(inst / "library/dewey/000-computer-science/ammolang"))
    _set("FINAL_EYE_PORT", os.environ.get("FINAL_EYE_PORT", "9479"))
    _set("FINAL_EYE_ASSIST", os.environ.get("FINAL_EYE_ASSIST", "1"))
    _set("FINAL_EYE_LOW_END", os.environ.get("FINAL_EYE_LOW_END", "1"))
    _set("FINAL_EYE_COOL", os.environ.get("FINAL_EYE_COOL", "1"))

    ctx = detect_ai_connections()
    if ctx["flags"].get("ammolang"):
        _set("AML_BUILD", "1")
    if ctx["flags"].get("grok_build"):
        _set("GROK_BUILD", "1")

    py_parts = [str(inst / "Final_Eye"), str(_LIB)]
    gmf = inst / "Final_Eye" / "GrokMediaFormat"
    if gmf.is_dir():
        py_parts.insert(0, str(gmf))
    existing = os.environ.get("PYTHONPATH", "")
    merged = os.pathsep.join(py_parts + ([existing] if existing else []))
    if force or not existing.strip():
        os.environ["PYTHONPATH"] = merged
        updates["PYTHONPATH"] = merged

    return updates


def normalize_action(raw: str) -> str:
    key = re.sub(r"[^a-z0-9_-]+", "_", raw.strip().lower()).strip("_")
    return OCR_ACTION_ALIASES.get(key, key)


def normalize_dispatch_body(body: dict[str, Any]) -> dict[str, Any]:
    """Map AI / OCR tool payloads to Final_Eye dispatch shape."""
    out = dict(body)
    raw_action = str(
        body.get("subaction")
        or body.get("action")
        or body.get("command")
        or body.get("cmd")
        or body.get("op")
        or body.get("operation")
        or "status"
    ).strip()
    out["subaction"] = normalize_action(raw_action)

    path = (
        body.get("image")
        or body.get("path")
        or body.get("file")
        or body.get("input")
        or body.get("source")
        or body.get("img")
    )
    if path:
        out["path"] = str(path)
        out["image"] = str(path)

    if body.get("psm") is not None:
        out["psm"] = str(body["psm"])
    if body.get("oem") is not None:
        out["oem"] = str(body["oem"])
    if body.get("lang") or body.get("language"):
        out["lang"] = str(body.get("lang") or body.get("language"))
    if body.get("whitelist") or body.get("tessedit_char_whitelist"):
        out["whitelist"] = str(body.get("whitelist") or body.get("tessedit_char_whitelist"))
    if body.get("format") or body.get("output_format"):
        out["format"] = str(body.get("format") or body.get("output_format"))

    return out


def parse_tesseract_argv(argv: list[str]) -> dict[str, Any] | None:
    """
    Parse tesseract-style CLI:
      tesseract IMAGE OUTPUT [options...]
      tesseract IMAGE stdout --psm 6 -l eng
    Returns dispatch body or None if argv is not tesseract-shaped.
    """
    if not argv:
        return None
    start = 0
    if Path(argv[0]).name.lower() in ("tesseract", "final-eye-ocr", "final-eye-h7-ocr.py"):
        start = 1
    elif argv[0].lower() == "tesseract":
        start = 1
    if start >= len(argv):
        return None

    image = argv[start]
    if image.startswith("-"):
        return None

    fmt = "stdout"
    opt_start = start + 1
    if len(argv) > start + 1 and not argv[start + 1].startswith("-"):
        fmt = argv[start + 1].lower()
        opt_start = start + 2

    body: dict[str, Any] = {"image": image, "format": fmt}
    i = opt_start
    while i < len(argv):
        tok = argv[i]
        if tok in ("--psm", "-psm") and i + 1 < len(argv):
            body["psm"] = argv[i + 1]
            i += 2
            continue
        if tok in ("--oem", "-oem") and i + 1 < len(argv):
            body["oem"] = argv[i + 1]
            i += 2
            continue
        if tok in ("-l", "--lang", "--language") and i + 1 < len(argv):
            body["lang"] = argv[i + 1]
            i += 2
            continue
        if tok.startswith("--psm="):
            body["psm"] = tok.split("=", 1)[1]
            i += 1
            continue
        if tok.startswith("-c") and i + 1 < len(argv) and "whitelist" in argv[i + 1]:
            m = re.search(r"tessedit_char_whitelist=(.+)", argv[i + 1])
            if m:
                body["whitelist"] = m.group(1)
            i += 2
            continue
        if tok in ("--plain", "-plain"):
            body["plain"] = True
            i += 1
            continue
        i += 1

    if fmt in ("stdout", "txt", "text"):
        body["subaction"] = "ocr"
        body["plain"] = True
    elif fmt in TESSERACT_OUTPUT_FORMATS:
        body["subaction"] = normalize_action(fmt)
    else:
        body["subaction"] = "ocr"
        body["output_file"] = fmt
    return body


def parse_cli_argv(argv: list[str]) -> tuple[str, dict[str, Any]]:
    """
    Parse mixed CLI: native Final_Eye, pytesseract verbs, tesseract argv.
    Returns (mode, kwargs/body).
    """
    if not argv:
        return "posture", {}

    joined = " ".join(argv).lower()
    if "tesseract" in Path(argv[0]).name.lower() or (
        len(argv) >= 2 and argv[0].lower() == "tesseract"
    ):
        body = parse_tesseract_argv(argv)
        if body:
            return "dispatch", body

    tess = parse_tesseract_argv(["tesseract", *argv])
    if tess and Path(str(tess.get("image", ""))).suffix.lower() in (
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".h7",
    ):
        return "dispatch", tess

    cmd = argv[0].strip().lower()
    cmd = normalize_action(cmd)

    if cmd in ("posture", "status", "connect", "ai-posture", "ai_posture", "vocabulary", "help"):
        return cmd.replace("-", "_"), {}
    if cmd in ("ocr", "read", "look", "smoke", "dispatch") and len(argv) > 1:
        if cmd == "dispatch":
            try:
                body = json.loads(argv[1])
            except json.JSONDecodeError:
                body = {"subaction": argv[1], "path": argv[2] if len(argv) > 2 else ""}
            return "dispatch", normalize_dispatch_body(body)
        return cmd, {"path": argv[1], "extra": argv[2:]}
    if cmd in OCR_ACTION_ALIASES and len(argv) > 1:
        body = normalize_dispatch_body({"action": cmd, "path": argv[1]})
        if len(argv) > 2:
            body["format"] = argv[2]
        return "dispatch", body

    return "unknown", {"argv": argv, "hint": joined[:120]}


def ocr_vocabulary() -> dict[str, Any]:
    doc = _load_doctrine()
    return {
        "schema": "final-eye-ocr-vocabulary/v1",
        "aliases": OCR_ACTION_ALIASES,
        "tesseract_output_formats": sorted(TESSERACT_OUTPUT_FORMATS),
        "cli_examples": doc.get("cli_examples") or [
            "final-eye-h7-ocr.py posture",
            "final-eye-h7-ocr.py ocr IMAGE.png",
            "final-eye-h7-ocr.py tesseract IMAGE.png stdout --psm 6",
            "final-eye-h7-ocr.py image_to_string IMAGE.png",
            "final-eye-h7-ocr.py dispatch '{\"action\":\"ocr\",\"path\":\"IMAGE.png\"}'",
        ],
        "pytesseract_map": doc.get("pytesseract_map") or {
            "image_to_string": "ocr",
            "image_to_hocr": "hocr",
            "image_to_pdf": "pdf",
            "image_to_boxes": "boxes",
            "image_to_data": "tsv",
            "image_to_osd": "osd",
        },
    }