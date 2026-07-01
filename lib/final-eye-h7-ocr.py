#!/usr/bin/env pythong
"""Final_Eye OCR CLI — Grok build + AI auto-wire; tesseract/pytesseract command vocabulary."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(__file__).resolve().parents[1]


def _bridge() -> Any | None:
    py = _LIB / "final-eye-ai-bridge.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("final_eye_ai_bridge_cli", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "wire_ai_env"):
        mod.wire_ai_env()
    return mod


def _core() -> Any:
    _bridge()
    py = _LIB / "final-eye-ocr-core.py"
    spec = importlib.util.spec_from_file_location("final_eye_ocr_core_cli", py)
    if not spec or not spec.loader:
        raise ImportError("final-eye-ocr-core.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_ocr_text(path: Path | str) -> str:
    return _core().read_ocr_text(path)


def ocr_image(path: str | Path, *, label: str = "", **opts: Any) -> dict[str, Any]:
    return _core().ocr_image_path(path, label=label, **opts)


def _via_hostess7(body: dict[str, Any]) -> dict[str, Any]:
    """Route through Hostess 7 OCR control — sealed handshake lane."""
    h7 = _LIB / "hostess7-ocr-control.py"
    if not h7.is_file():
        return {"ok": False, "error": "hostess7_ocr_control_missing", "sealed": True}
    payload = json.dumps(body, ensure_ascii=False)
    try:
        proc = subprocess.run(
            [sys.executable, str(h7), "dispatch"],
            input=payload,
            capture_output=True,
            text=True,
            timeout=120,
            env={**dict(__import__("os").environ), "NEXUS_INSTALL_ROOT": str(INSTALL), "HOSTESS7_OCR_CONTROL": "1"},
            cwd=str(INSTALL),
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": type(exc).__name__, "sealed": True}


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    return _via_hostess7({"action": "final_eye", **body})


def posture() -> dict[str, Any]:
    core = _core()
    st = core.final_eye_status()
    root = core.final_eye_root()
    ai = core.ai_connection_posture() if hasattr(core, "ai_connection_posture") else {}
    return {
        "schema": "final-eye-h7-ocr/v2",
        "final_eye_root": str(root),
        "zocr_live": (root / "zocr.py").is_file(),
        "h7_bridge": (root / "zocr_h7.py").is_file(),
        "h7_format": str(INSTALL / "lib" / "field-h7-format.py"),
        "output_format": "h7/7",
        "zero_txt_primary": False,
        "commander": "Hostess7",
        "handshake_only": True,
        "sealed_lane": "lib/final-eye-hostess7-seal.py",
        "sovereign": True,
        "loopback_free": True,
        "ai_connections": ai,
        "status": st,
    }


def _emit(row: dict[str, Any], *, plain: bool = False) -> None:
    if plain or row.get("plain"):
        text = str(row.get("text") or row.get("ocr") or "")
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    print(json.dumps(row, ensure_ascii=False, indent=2))


def main() -> int:
    bridge = _bridge()
    argv = sys.argv[1:]

    if not argv:
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0

    if bridge and hasattr(bridge, "parse_cli_argv"):
        mode, payload = bridge.parse_cli_argv(argv)
    else:
        mode = argv[0].strip().lower() if argv else "posture"
        payload = {"path": argv[1]} if len(argv) > 1 else {}

    if mode in ("posture", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0

    if mode in ("connect", "ai_posture"):
        core = _core()
        row = core.ai_connection_posture() if hasattr(core, "ai_connection_posture") else {}
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return 0 if row.get("ok", True) else 1

    if mode in ("vocabulary", "help"):
        row = bridge.ocr_vocabulary() if bridge and hasattr(bridge, "ocr_vocabulary") else {}
        if mode == "help":
            row = {**row, "cmds": [
                "posture", "connect", "vocabulary",
                "ocr PATH [--psm N] [--plain]",
                "tesseract PATH stdout [--psm N] [--plain]",
                "image_to_string PATH", "hocr PATH", "dispatch JSON",
            ]}
        print(json.dumps(row, ensure_ascii=False, indent=2))
        return 0

    if mode == "ocr" and payload.get("path"):
        extra = payload.get("extra") or []
        opts: dict[str, Any] = {}
        i = 0
        while i < len(extra):
            tok = extra[i]
            if tok in ("--psm", "-psm") and i + 1 < len(extra):
                opts["psm"] = extra[i + 1]
                i += 2
                continue
            if tok.startswith("--psm="):
                opts["psm"] = tok.split("=", 1)[1]
            i += 1
        body = {"action": "ocr_image", "path": payload["path"], **opts}
        row = _via_hostess7(body)
        plain = "--plain" in extra or "-plain" in extra
        _emit(row, plain=plain)
        return 0 if (row.get("ok") or row.get("text") or row.get("ocr")) else 1

    if mode == "read" and payload.get("path"):
        row = _via_hostess7({"action": "read", "path": payload["path"]})
        plain = "--plain" in (payload.get("extra") or [])
        _emit(row, plain=plain)
        return 0

    if mode == "dispatch":
        row = _via_hostess7({"action": "final_eye", **payload})
        _emit(row, plain=bool(payload.get("plain")))
        return 0 if row.get("ok", True) else 1

    if mode == "unknown":
        help_doc = {
            "error": "usage",
            "schema": "final-eye-h7-ocr/v2",
            "cmds": [
                "posture",
                "connect",
                "vocabulary",
                "ocr PATH [--psm N] [--plain]",
                "read PATH [--plain]",
                "tesseract PATH stdout [--psm N]",
                "image_to_string PATH",
                "hocr PATH",
                "dispatch JSON",
            ],
            "hint": payload.get("hint"),
            "ai_connections": (_core().ai_connection_posture() if hasattr(_core(), "ai_connection_posture") else {}),
        }
        print(json.dumps(help_doc, ensure_ascii=False, indent=2))
        return 1

    row = dispatch({"subaction": mode, "path": payload.get("path", ""), **{k: v for k, v in payload.items() if k != "path"}})
    _emit(row, plain=bool(payload.get("plain")))
    return 0 if row.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())