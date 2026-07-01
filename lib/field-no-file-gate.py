#!/usr/bin/env pythong
"""Field no-file gate — block poison field files; sovereign formats presume field underneath."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1])).resolve()
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))


def _resolve_sg_root() -> Path:
    """SG layout: parent of NewLatest, or NewLatest itself when SG_ROOT=NEXUS_INSTALL_ROOT."""
    raw = os.environ.get("SG_ROOT", "").strip()
    if raw:
        p = Path(raw).expanduser().resolve()
        if (p / "NewLatest").is_dir():
            return p
        if (p / "lib" / "nexus-common.sh").is_file() or p.name == "NewLatest":
            return p.parent if (p.parent / "NewLatest").exists() else p
        return p
    if INSTALL.name == "NewLatest":
        return INSTALL.parent
    return INSTALL.parent.parent


SG = _resolve_sg_root()
from sg_paths import grok16_root

GROK16 = grok16_root()
DOCTRINE = INSTALL / "data" / "field-no-file-doctrine.json"
PANEL = STATE / "field-no-file-gate-panel.json"
LEDGER = STATE / "field-no-file-gate-ledger.jsonl"

_SOVEREIGN_EXTS = frozenset({
    ".h7c", ".g1id", ".fielddrive", ".wrdt", ".wrzc", ".h7snap", ".field-snap",
})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def sg_grok16_ready(*, require_grok16: bool = True) -> dict[str, Any]:
    """Sovereign formats and gates require SG_ROOT + Grok16 tree."""
    field_install = (SG / "NewLatest").resolve() if (SG / "NewLatest").is_dir() else INSTALL
    sg_ok = SG.is_dir() and (
        (SG / "NewLatest").is_dir()
        or (field_install / "lib" / "nexus-common.sh").is_file()
    )
    g16_ok = GROK16.is_dir() and (GROK16 / "forge" / "g16-field-sanity.py").is_file()
    ok = sg_ok and (g16_ok or not require_grok16)
    return {
        "ok": ok,
        "sg_root": str(SG),
        "grok16_root": str(GROK16),
        "sg_ready": sg_ok,
        "grok16_ready": g16_ok,
        "requires_grok16": require_grok16,
    }


def _norm_path(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p).replace("\\", "/")
    except OSError:
        return str(path).replace("\\", "/")


def _basename(path: Path | str) -> str:
    return Path(path).name


def _extension_poison(path: Path | str, doc: dict[str, Any]) -> str | None:
    name = _basename(path).lower()
    forbidden = [str(e).lower() for e in (doc.get("forbidden") or {}).get("extensions") or [".field"]]
    exceptions = [str(e).lower() for e in (doc.get("forbidden") or {}).get("extension_exceptions") or []]
    for exc in exceptions:
        if name.endswith(exc):
            return None
    for ext in forbidden:
        if name.endswith(ext):
            return f"forbidden_extension:{ext}"
    return None


def _path_substring_poison(path: Path | str, doc: dict[str, Any]) -> str | None:
    norm = _norm_path(path).lower()
    for sub in (doc.get("forbidden") or {}).get("path_substrings") or []:
        if str(sub).lower() in norm:
            return f"forbidden_path:{sub}"
    return None


def _basename_poison(path: Path | str, doc: dict[str, Any]) -> str | None:
    name = _basename(path)
    forbidden = (doc.get("forbidden") or {}).get("basenames") or []
    if name in forbidden:
        rep = (doc.get("replacements") or {}).get(name)
        return f"forbidden_basename:{name}" + (f"→use:{rep}" if rep else "")
    panel_truth = (doc.get("panel_truth_basenames") or [])
    if name in panel_truth:
        return None
    allowed_suffixes = doc.get("allowed_suffixes") or []
    for suf in allowed_suffixes:
        if name.endswith(str(suf)):
            return None
    if name.endswith("-field.json") and not name.endswith("-field-panel.json"):
        return "forbidden_field_json_launch"
    return None


def _schema_poison(content: dict[str, Any] | None, doc: dict[str, Any]) -> str | None:
    if not isinstance(content, dict):
        return None
    schema = str(content.get("schema") or "")
    forbidden = (doc.get("forbidden") or {}).get("schemas") or []
    for fs in forbidden:
        if schema == fs or schema.startswith(fs.rstrip("/") + "/"):
            return f"forbidden_schema:{schema}"
    if int(content.get("field_depth") or 0) > 0:
        return "forbidden_field_depth_gt_0"
    if content.get("field_on_field"):
        return "forbidden_field_on_field"
    return None


def classify_write_path(
    path: Path | str,
    *,
    content: dict[str, Any] | None = None,
    doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a proposed write — forbidden poisons the well; sovereign formats are OK."""
    doc = doc or doctrine()
    p = Path(path)
    name = _basename(p)
    ext = p.suffix.lower()

    if ext in _SOVEREIGN_EXTS:
        return {
            "ok": True,
            "verdict": "sovereign_format",
            "path": _norm_path(p),
            "presumes_field_underneath": True,
            "requires_grok16": True,
            "creates_field_file": False,
        }

    reason = (
        _extension_poison(p, doc)
        or _path_substring_poison(p, doc)
        or _basename_poison(p, doc)
        or _schema_poison(content, doc)
    )
    if reason:
        rep = (doc.get("replacements") or {}).get(name)
        return {
            "ok": False,
            "verdict": "forbidden_field_file",
            "path": _norm_path(p),
            "reason": reason,
            "replacement": rep,
            "never_poison_the_well": True,
            "hint": doc.get("warning", {}).get("body"),
        }

    return {
        "ok": True,
        "verdict": "allowed",
        "path": _norm_path(p),
        "creates_field_file": False,
    }


def gate_write(
    path: Path | str,
    *,
    content: dict[str, Any] | None = None,
    require_grok16: bool = True,
) -> dict[str, Any]:
    """Preflight gate — refuse poison field file writes."""
    roots = sg_grok16_ready(require_grok16=require_grok16)
    verdict = classify_write_path(path, content=content)
    ok = bool(verdict.get("ok")) and roots.get("ok")
    out = {
        "schema": "field-no-file-gate/v1",
        "ts": _now(),
        "ok": ok,
        "path": verdict.get("path"),
        "verdict": verdict.get("verdict"),
        "roots": roots,
        "never_poison_the_well": True,
        "no_field_files": True,
        "max_field_depth": 0,
    }
    if not verdict.get("ok"):
        out["error"] = "field_file_write_forbidden"
        out["reason"] = verdict.get("reason")
        out["replacement"] = verdict.get("replacement")
        out["hint"] = verdict.get("hint")
    elif not roots.get("ok"):
        out["error"] = "sg_grok16_not_ready"
        out["hint"] = "Set SG_ROOT and GROK16_ROOT — sovereign paths require both."
    return out


def guarded_write_text(
    path: Path | str,
    text: str,
    *,
    content: dict[str, Any] | None = None,
    require_grok16: bool = False,
) -> dict[str, Any]:
    """Write text only if gate passes — never poison the well."""
    if content is None and str(path).endswith(".json"):
        try:
            content = json.loads(text)
        except json.JSONDecodeError:
            content = None
    gate = gate_write(path, content=content, require_grok16=require_grok16)
    if not gate.get("ok"):
        _append_ledger({"ts": gate["ts"], "event": "blocked", **gate})
        return gate
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(p)
    gate["written"] = True
    gate["bytes"] = len(text.encode("utf-8"))
    _append_ledger({"ts": gate["ts"], "event": "write_ok", "path": gate.get("path")})
    return gate


def guarded_write_json(
    path: Path | str,
    doc: dict[str, Any],
    *,
    require_grok16: bool = False,
    indent: int = 2,
) -> dict[str, Any]:
    text = json.dumps(doc, ensure_ascii=False, indent=indent) + "\n"
    return guarded_write_text(path, text, content=doc, require_grok16=require_grok16)


def sovereign_format_flags(fmt_id: str) -> dict[str, Any]:
    """Metadata stamp for sovereign wire formats in field-file-formats table."""
    doc = doctrine()
    ids = (doc.get("sovereign_formats") or {}).get("ids") or []
    flags = (doc.get("sovereign_formats") or {}).get("flags") or {}
    if fmt_id not in ids:
        return {}
    return dict(flags)


def meld_slice() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema") == "field-no-file-gate-panel/v1":
        return {
            "id": "no_field_files",
            "absorbed": True,
            "ok": cached.get("ok"),
            "no_field_files": True,
            "never_poison_the_well": True,
            "blocked_total": cached.get("blocked_total", 0),
            "roots": cached.get("roots"),
            "updated": cached.get("updated"),
            "meld_citation": "ironclad:meld:2",
            "citation": "ironclad:field_sanity:4",
        }
    return build_panel(write=False)


def build_panel(*, write: bool = True) -> dict[str, Any]:
    roots = sg_grok16_ready()
    doc = doctrine()
    panel = {
        "schema": "field-no-file-gate-panel/v1",
        "updated": _now(),
        "ok": bool(roots.get("ok")),
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "no_field_files": True,
        "never_poison_the_well": True,
        "max_field_depth": 0,
        "roots": roots,
        "sovereign_format_ids": (doc.get("sovereign_formats") or {}).get("ids"),
        "forbidden_basenames": (doc.get("forbidden") or {}).get("basenames"),
        "replacements": doc.get("replacements"),
        "blocked_total": 0,
        "meld_citation": "ironclad:meld:2",
        "citation": "ironclad:field_sanity:4",
    }
    if write:
        _save(PANEL, panel)
    return panel


def preflight_body(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Sanity preflight — flag layers proposing field file outputs."""
    body = body or {}
    doc = doctrine()
    violations: list[dict[str, Any]] = []
    for layer in body.get("layers") or []:
        if not isinstance(layer, dict):
            continue
        path = str(layer.get("path") or layer.get("output") or "")
        if not path:
            continue
        v = classify_write_path(path, content=layer if isinstance(layer.get("schema"), str) else None, doc=doc)
        if not v.get("ok"):
            violations.append({"path": path, "reason": v.get("reason"), "layer_id": layer.get("id")})
    roots = sg_grok16_ready()
    return {
        "ok": len(violations) == 0 and roots.get("ok"),
        "violations": violations,
        "violation_count": len(violations),
        "roots": roots,
        "no_field_files": True,
        "never_poison_the_well": True,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=True), ensure_ascii=False))
        return 0
    if cmd == "meld":
        print(json.dumps(meld_slice(), ensure_ascii=False))
        return 0
    if cmd == "roots":
        print(json.dumps(sg_grok16_ready(), ensure_ascii=False))
        return 0
    if cmd == "classify" and len(sys.argv) > 2:
        print(json.dumps(classify_write_path(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd == "gate" and len(sys.argv) > 2:
        content = None
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
            if raw.strip():
                try:
                    content = json.loads(raw)
                except json.JSONDecodeError:
                    pass
        rep = gate_write(sys.argv[2], content=content)
        print(json.dumps(rep, ensure_ascii=False))
        return 0 if rep.get("ok") else 1
    if cmd == "preflight":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        rep = preflight_body(body)
        print(json.dumps(rep, ensure_ascii=False))
        return 0 if rep.get("ok") else 1
    if cmd == "verify":
        roots = sg_grok16_ready()
        poison = classify_write_path("field/sovereign/queen-field.json")
        ok_ext = classify_write_path("out/payload.h7c")
        ok = roots.get("ok") and not poison.get("ok") and ok_ext.get("ok")
        print(json.dumps({
            "ok": ok,
            "roots": roots,
            "poison_blocked": not poison.get("ok"),
            "sovereign_allowed": ok_ext.get("ok"),
        }, ensure_ascii=False))
        return 0 if ok else 1
    print(json.dumps({
        "error": "usage",
        "cmds": ["json", "meld", "roots", "classify PATH", "gate PATH", "preflight", "verify"],
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())