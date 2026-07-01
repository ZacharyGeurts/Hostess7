#!/usr/bin/env pythong
"""Final_Eye OCR core — one lane, in-process, H7/7 output. No subprocess loopbacks."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent)))

_AI_BRIDGE: Any = None


def _ai_bridge() -> Any | None:
    global _AI_BRIDGE
    if _AI_BRIDGE is not None:
        return _AI_BRIDGE
    bridge_py = _LIB / "final-eye-ai-bridge.py"
    if not bridge_py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("final_eye_ai_bridge_core", bridge_py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "wire_ai_env"):
        mod.wire_ai_env()
    _AI_BRIDGE = mod
    return mod

_ZOCR_MOD: Any = None
_ZOCR_H7_MOD: Any = None
_H7_MOD: Any = None


def final_eye_root() -> Path:
    env = os.environ.get("FINAL_EYE_ROOT", "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return p.resolve()
    try:
        if str(_LIB) not in sys.path:
            sys.path.insert(0, str(_LIB))
        from sg_paths import final_eye_root as _fer
        return _fer()
    except Exception:
        pass
    for cand in (INSTALL / "Final_Eye", SG / "NewLatest" / "Final_Eye", SG / "Final_Eye"):
        if (cand / "zocr.py").is_file():
            return cand.resolve()
    return (INSTALL / "Final_Eye").resolve()


def _ensure_zocr_path() -> Path:
    root = final_eye_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def _zocr() -> Any | None:
    global _ZOCR_MOD
    if _ZOCR_MOD is not None:
        return _ZOCR_MOD
    root = _ensure_zocr_path()
    zocr_py = root / "zocr.py"
    if not zocr_py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("zocr_core", zocr_py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _ZOCR_MOD = mod
    return mod


def _zocr_h7() -> Any | None:
    global _ZOCR_H7_MOD
    if _ZOCR_H7_MOD is not None:
        return _ZOCR_H7_MOD
    root = _ensure_zocr_path()
    h7_py = root / "zocr_h7.py"
    if not h7_py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("zocr_h7_core", h7_py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _ZOCR_H7_MOD = mod
    return mod


def _h7_format() -> Any | None:
    global _H7_MOD
    if _H7_MOD is not None:
        return _H7_MOD
    path = INSTALL / "lib" / "field-h7-format.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_h7_format_core", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _H7_MOD = mod
    return mod


def read_ocr_text(path: Path | str) -> str:
    fp = Path(path)
    if not fp.is_file():
        return ""
    h7 = _zocr_h7()
    if h7 and hasattr(h7, "read_ocr_text"):
        try:
            return str(h7.read_ocr_text(fp) or "")
        except Exception:
            pass
    fmt = _h7_format()
    if fp.suffix.lower() == ".h7" and fmt and hasattr(fmt, "open_any_h7_path"):
        try:
            text, _ = fmt.open_any_h7_path(fp)
            return str(text or "")
        except Exception:
            pass
    try:
        return fp.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _ocr_lane_gate(lane_body: dict[str, Any] | None = None, *, subaction: str = "ocr") -> dict[str, Any] | None:
    """Return error dict when Hostess 7 handshake missing; None when lane is trusted."""
    seal_mod = _hostess7_seal()
    if not seal_mod or not hasattr(seal_mod, "require_handshake"):
        return {"ok": False, "error": "hostess7_seal_missing", "sealed": True, "gate": "final-eye-hostess7-seal"}
    return seal_mod.require_handshake(dict(lane_body or {}), subaction=subaction)


def ocr_via_hostess7(body: dict[str, Any]) -> dict[str, Any]:
    """Trusted lane — lib/hostess7-ocr-control.py stamps Hostess 7 handshake before dispatch."""
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
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "HOSTESS7_OCR_CONTROL": "1"},
            cwd=str(INSTALL),
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": type(exc).__name__, "sealed": True}


def ocr_image_path(
    path: Path | str,
    *,
    label: str = "",
    psm: str = "6",
    oem: str = "",
    lang: str = "",
    whitelist: str = "",
    lane_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Single-hop OCR: Final_Eye zocr in-process → H7 capture row."""
    gate = _ocr_lane_gate(lane_body, subaction="ocr")
    if gate:
        return gate
    fp = Path(path).expanduser()
    if not fp.is_file():
        return {"ok": False, "error": "file_missing", "path": str(fp)}
    zocr = _zocr()
    if not zocr:
        return {"ok": False, "error": "final_eye_missing", "final_eye_root": str(final_eye_root())}
    try:
        kwargs: dict[str, Any] = {"psm": str(psm or "6")}
        if whitelist:
            kwargs["whitelist"] = whitelist
        text = str(zocr.ocr_image(fp, **kwargs) or "")
        row = zocr.write_capture(label=label or fp.stem, image=fp, ocr_text=text, copy_image=True)
        row["ok"] = bool(text) or bool(row.get("ocr_len"))
        row["text"] = text
        row["engine"] = "Final_Eye/zocr.py"
        row["format"] = row.get("format") or "h7/7"
        row["final_eye_root"] = str(final_eye_root())
        row["ocr_options"] = {k: v for k, v in {"psm": psm, "oem": oem, "lang": lang, "whitelist": whitelist}.items() if v}
        return row
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200], "path": str(fp)}


def _tesseract_cli(
    path: Path,
    output_format: str,
    *,
    psm: str = "6",
    lang: str = "",
    whitelist: str = "",
) -> dict[str, Any]:
    """Run system tesseract when extended formats (hocr/pdf/tsv) are requested."""
    import shutil

    tess = shutil.which("tesseract")
    if not tess:
        return {"ok": False, "error": "tesseract_missing", "format": output_format}
    fmt = output_format.lower()
    if fmt in ("stdout", "txt", "text"):
        fmt = "stdout"
    cmd = [tess, str(path), fmt, "--psm", str(psm or "6")]
    if lang:
        cmd.extend(["-l", lang])
    if whitelist:
        cmd.extend(["-c", f"tessedit_char_whitelist={whitelist}"])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        out = (proc.stdout or "").strip()
        if fmt != "stdout" and not out and proc.returncode == 0:
            suffix = {"hocr": ".hocr", "pdf": ".pdf", "tsv": ".tsv", "box": ".box", "osd": ".osd"}.get(fmt, "")
            if suffix:
                sidecar = Path(str(path) + suffix)
                if sidecar.is_file():
                    if suffix == ".pdf":
                        out = sidecar.read_bytes().hex()[:4000]
                        return {"ok": True, "format": fmt, "pdf_hex_preview": out, "pdf_file": str(sidecar)}
                    out = sidecar.read_text(encoding="utf-8", errors="replace")
        ok = proc.returncode == 0 and bool(out)
        return {
            "ok": ok,
            "format": fmt,
            "text": out,
            "engine": "tesseract",
            "returncode": proc.returncode,
            "stderr": (proc.stderr or "")[:500] if not ok else "",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "tesseract_timeout", "format": output_format}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "format": output_format}


def ocr_with_format(body: dict[str, Any]) -> dict[str, Any]:
    """OCR with tesseract-familiar output targets (stdout, hocr, pdf, tsv, boxes, osd)."""
    path = str(body.get("image") or body.get("path") or "")
    if not path:
        return {"ok": False, "error": "missing_image"}
    fmt = str(body.get("format") or body.get("output_format") or "stdout").lower()
    sub = str(body.get("subaction") or "ocr").lower()
    target = fmt if fmt not in ("", "h7", "h7/7", "json") else sub
    psm = str(body.get("psm") or "6")
    lang = str(body.get("lang") or body.get("language") or "")
    whitelist = str(body.get("whitelist") or body.get("tessedit_char_whitelist") or "")

    if target in ("ocr", "stdout", "txt", "text", "string"):
        row = ocr_image_path(
            path,
            label=str(body.get("label") or ""),
            psm=psm,
            lang=lang,
            whitelist=whitelist,
            lane_body=body,
        )
        if body.get("plain"):
            row["plain"] = True
        return row

    fp = Path(path).expanduser()
    if not fp.is_file():
        return {"ok": False, "error": "file_missing", "path": path}

    if target in ("hocr", "pdf", "tsv", "box", "boxes", "osd", "alto"):
        tess_fmt = "box" if target == "boxes" else target
        tess_row = _tesseract_cli(fp, tess_fmt, psm=psm, lang=lang, whitelist=whitelist)
        if tess_row.get("ok"):
            tess_row["path"] = str(fp)
            tess_row["final_eye_root"] = str(final_eye_root())
            return tess_row
        row = ocr_image_path(
            path,
            label=str(body.get("label") or ""),
            psm=psm,
            lang=lang,
            whitelist=whitelist,
            lane_body=body,
        )
        row["format_fallback"] = "h7/7"
        row["tesseract_error"] = tess_row.get("error") or tess_row.get("stderr")
        return row

    return ocr_image_path(
        path,
        label=str(body.get("label") or ""),
        psm=psm,
        lang=lang,
        whitelist=whitelist,
        lane_body=body,
    )


def ai_connection_posture() -> dict[str, Any]:
    bridge = _ai_bridge()
    if not bridge:
        return {"ok": True, "schema": "final-eye-ai-connections/v1", "connections": [], "wired": False}
    ctx = bridge.detect_ai_connections()
    wired = bridge.wire_ai_env()
    vocab = bridge.ocr_vocabulary() if hasattr(bridge, "ocr_vocabulary") else {}
    return {
        "ok": True,
        **ctx,
        "wired_env": sorted(wired.keys()),
        "vocabulary": vocab,
        "bridge": "lib/final-eye-ai-bridge.py",
        "cli": "lib/final-eye-h7-ocr.py",
    }


def final_eye_status() -> dict[str, Any]:
    zocr = _zocr()
    if not zocr or not hasattr(zocr, "status"):
        return {"ok": False, "error": "final_eye_missing", "final_eye_root": str(final_eye_root())}
    try:
        st = zocr.status()
        st["commander"] = "Hostess7"
        st["sovereign"] = True
        return st
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}


def ocr_image_text(path: Path | str, *, via_hostess7: bool = True) -> str:
    if via_hostess7:
        row = ocr_via_hostess7({"action": "ocr_image", "path": str(path)})
        return str(row.get("text") or row.get("ocr") or "").strip()
    row = ocr_image_path(path)
    return str(row.get("text") or row.get("ocr") or "").strip()


def final_eye_look(
    *,
    prefer: str = "auto",
    label: str = "look",
    lane_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = _ocr_lane_gate(lane_body, subaction="look")
    if gate:
        return gate
    root = _ensure_zocr_path()
    vision = root / "zocr_vision.py"
    if vision.is_file():
        spec = importlib.util.spec_from_file_location("zocr_vision_core", vision)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "look"):
                return mod.look(label=label, prefer=prefer)
    return {"ok": False, "error": "look_unavailable", "final_eye_root": str(root)}


def final_eye_browser_smoke() -> dict[str, Any]:
    root = _ensure_zocr_path()
    smoke = root / "queen_browser_smoke.py"
    if not smoke.is_file():
        return {"ok": False, "error": "smoke_unavailable", "final_eye_root": str(root)}
    import json
    import subprocess
    import sys
    try:
        proc = subprocess.run(
            [sys.executable, str(smoke)],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "FINAL_EYE_ROOT": str(root), "NEXUS_INSTALL_ROOT": str(INSTALL)},
            cwd=str(root),
        )
        try:
            doc = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            doc = {"ok": proc.returncode == 0, "tail": (proc.stdout or proc.stderr or "")[-2000:]}
        doc["returncode"] = proc.returncode
        doc["final_eye_root"] = str(root)
        doc["engine"] = "Final_Eye/queen_browser_smoke.py"
        return doc
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "smoke_timeout", "final_eye_root": str(root)}


def _hostess7_seal() -> Any | None:
    py = _LIB / "final-eye-hostess7-seal.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("final_eye_hostess7_seal_core", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def final_eye_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    """Direct Final_Eye lane — Hostess 7 handshake required."""
    bridge = _ai_bridge()
    if bridge and hasattr(bridge, "normalize_dispatch_body"):
        body = bridge.normalize_dispatch_body(body)
    sub = str(body.get("subaction") or body.get("action") or "status").strip().lower()
    if bridge and hasattr(bridge, "normalize_action"):
        sub = bridge.normalize_action(sub)

    seal_mod = _hostess7_seal()
    if seal_mod and hasattr(seal_mod, "require_handshake"):
        if sub in ("seal", "seal_posture"):
            return {"ok": True, **seal_mod.seal_posture(force=True)}
        if sub == "handshake":
            os.environ["HOSTESS7_OCR_CONTROL"] = "1"
            act = str(body.get("handshake_action") or body.get("action") or "dispatch")
            return seal_mod.issue_handshake(action=act)
        gate = seal_mod.require_handshake(body, subaction=sub)
        if gate:
            return gate

    if sub in ("status", "json", "posture"):
        st = final_eye_status()
        if seal_mod and hasattr(seal_mod, "seal_posture"):
            st["hostess7_seal"] = seal_mod.seal_posture()
        st["ai_connections"] = ai_connection_posture()
        st["commander"] = "Hostess7"
        st["handshake_only"] = True
        return st
    if sub in ("connect", "ai_posture", "ai-posture", "connections", "vocabulary"):
        return ai_connection_posture()
    if sub in ("look", "watch", "vision", "poll"):
        prefer = str(body.get("prefer") or "auto")
        return final_eye_look(prefer=prefer, label=str(body.get("label") or "look"), lane_body=body)
    if sub in ("observe", "robotics"):
        prefer = str(body.get("prefer") or "auto")
        look = final_eye_look(prefer=prefer, label=str(body.get("label") or "observe"), lane_body=body)
        robotics: dict[str, Any] = {}
        try:
            root = _ensure_zocr_path()
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            from zocr_ai import robotics_context
            robotics = robotics_context(capture=look)
        except Exception as exc:
            robotics = {"ok": False, "error": type(exc).__name__}
        return {"ok": bool(look.get("ok")), "look": look, "robotics": robotics}
    if sub in ("smoke", "browser-smoke", "browser_smoke", "final-eye-smoke"):
        return final_eye_browser_smoke()
    if sub in ("ocr", "tesseract", "recognize", "recognise", "scan", "extract", "extract_text",
               "text_from_image", "image_to_string", "image_to_text", "hocr", "pdf", "tsv", "boxes", "box", "osd"):
        return ocr_with_format(body)
    if sub == "read":
        path = str(body.get("path") or body.get("h7_file") or body.get("ocr_file") or "")
        text = read_ocr_text(path)
        return {"ok": bool(text), "path": path, "text": text, "format": "h7/7" if path.endswith(".h7") else "text"}
    return {"ok": False, "error": "unknown_subaction", "subaction": sub, "vocabulary": (bridge.ocr_vocabulary() if bridge and hasattr(bridge, "ocr_vocabulary") else {})}