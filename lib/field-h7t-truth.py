#!/usr/bin/env python3
"""H7t — Hostess 7 Truthed: non-sovereign payloads rated, wrapped, chamber-isolated."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-h7t-truth-doctrine.json"
PANEL = STATE / "field-h7t-truth-panel.json"
CHAMBER = STATE / "h7t-chamber"
LEDGER = STATE / "field-h7t-truth.jsonl"

MAGIC = b"H7T\x01"
FORMAT = "h7t/1"


class H7tError(ValueError):
    pass


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_py(rel: str, name: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_h7t_blob(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == MAGIC


def safe_stack_prefixes() -> list[str]:
    doc = _load(DOCTRINE, {})
    return list((doc.get("safe_stack") or {}).get("path_prefixes") or [])


def is_safe_asset(*, path: str | Path | None = None, meta: dict[str, Any] | None = None) -> bool:
    """True when payload is sovereign safe-stack — runs natively, no H7t shell required."""
    meta = meta or {}
    rel = str(path or meta.get("path") or meta.get("source") or "").replace("\\", "/")
    if meta.get("sovereign") or meta.get("safe_stack"):
        return True
    owner = str((meta.get("owner") or "")).strip()
    if owner and owner != "ZacharyGeurts":
        return False
    for prefix in safe_stack_prefixes():
        if rel.startswith(prefix):
            return True
    hub = _load(INSTALL / "data" / "ammoos-pages-hub.json", {})
    for spec in (hub.get("repos") or {}).values():
        if not isinstance(spec, dict):
            continue
        for key in ("tree", "module", "pages_path"):
            val = str(spec.get(key) or "")
            if val and rel.startswith(val):
                return True
    return False


def _truth_rate_text(text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    truth = _import_py("lib/hostess7-truth-rating.py", "h7truth")
    if not truth or not hasattr(truth, "rate_response"):
        return {"assurance_pct": 50.0, "skipped": True, "band": "unknown"}
    try:
        ctx = {"instant": True, "kind": "h7t_ingest", **(context or {})}
        rated = truth.rate_response(text, question="H7t chamber ingest witness", context=ctx, instant=True)
        pct = float(rated.get("truth_percent") or rated.get("truth_score") or rated.get("assurance_pct") or 50)
        return {
            "assurance_pct": pct,
            "band": rated.get("deception_risk") or rated.get("band"),
            "assurance": rated.get("assurance"),
            "witness": {"schema": rated.get("schema"), "ironclad_sealed": rated.get("ironclad_sealed")},
        }
    except Exception as exc:
        return {"assurance_pct": 50.0, "degraded": True, "error": str(exc)[:120], "band": "degraded"}


def _lie_threat_scan(text: str) -> dict[str, Any]:
    tlt = _import_py("lib/hostess7-truth-lie-threat.py", "h7tlt")
    if not tlt or not hasattr(tlt, "classify_text"):
        return {"ok": True, "skipped": True}
    try:
        return tlt.classify_text(text)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def _maybe_condense(inner: bytes, meta: dict[str, Any]) -> tuple[bytes, str]:
    if not meta.get("condense") and not meta.get("h7c"):
        return inner, "raw"
    h7c = _import_py("lib/field-h7c-compression.py", "field_h7c")
    if not h7c or not hasattr(h7c, "pack_h7c"):
        return inner, "raw"
    try:
        text = inner.decode("utf-8")
    except UnicodeDecodeError:
        return inner, "raw"
    packed = h7c.pack_h7c(text, meta, use_optimizer=True, format_version=2)
    if hasattr(h7c, "wrap_h7c_block"):
        packed = h7c.wrap_h7c_block(packed, meta)
    return packed, "h7c/4"


def pack_h7t(inner: bytes, meta: dict[str, Any] | None = None, *, truth_text: str | None = None) -> bytes:
    m = dict(meta or {})
    m.setdefault("format", FORMAT)
    m.setdefault("packed_at", _utc())
    m.setdefault("sovereign_sealed", False)
    m.setdefault("isolation", "chamber_only")
    if truth_text is None:
        try:
            truth_text = inner.decode("utf-8")
        except UnicodeDecodeError:
            truth_text = ""
    if truth_text:
        m["truth"] = _truth_rate_text(truth_text, {"source": m.get("source"), "path": m.get("path")})
        m["lie_threat"] = _lie_threat_scan(truth_text)
    min_pct = float((_load(DOCTRINE, {}).get("truth_pipeline") or {}).get("min_assurance_pct") or 40)
    assurance = float((m.get("truth") or {}).get("assurance_pct") or 0)
    if truth_text and assurance < min_pct and not m.get("force"):
        raise H7tError(f"truth assurance {assurance:.1f}% below minimum {min_pct}%")
    body, inner_fmt = _maybe_condense(inner, m)
    m["inner_format"] = inner_fmt
    m["inner_sha256"] = _sha256(body)
    m["benefits_factor"] = int((_load(DOCTRINE, {}).get("benefits") or {}).get("h7s_speedup_factor") or 100)
    hdr = json.dumps(m, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return MAGIC + struct.pack("<I", len(hdr)) + hdr + struct.pack("<I", len(body)) + body


def unpack_h7t(data: bytes) -> tuple[bytes, dict[str, Any]]:
    if not is_h7t_blob(data):
        raise H7tError("not an H7t blob")
    if len(data) < 12:
        raise H7tError("truncated H7t header")
    hdr_len = struct.unpack("<I", data[4:8])[0]
    start = 8
    end = start + hdr_len
    if end + 4 > len(data):
        raise H7tError("truncated H7t body length")
    meta = json.loads(data[start:end].decode("utf-8"))
    inner_len = struct.unpack("<I", data[end : end + 4])[0]
    body_start = end + 4
    body_end = body_start + inner_len
    if body_end > len(data):
        raise H7tError("truncated H7t inner")
    inner = data[body_start:body_end]
    if _sha256(inner) != str(meta.get("inner_sha256") or ""):
        raise H7tError("inner sha256 mismatch — tamper detected")
    return inner, meta


def ingest_unsafe(
    payload: bytes | str,
    *,
    source: str = "",
    path: str = "",
    condense: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Truth-rate foreign payload, pack H7t, store in chamber — never touches sovereign stack."""
    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = payload
    meta: dict[str, Any] = {
        "source": source or path or "foreign",
        "path": path,
        "condense": condense,
        "force": force,
        "safe_stack": False,
    }
    if is_safe_asset(path=path, meta=meta):
        return {
            "ok": True,
            "safe_stack": True,
            "note": "sovereign asset — native path, no H7t shell",
            "path": path,
        }
    packed = pack_h7t(raw, meta, truth_text=raw.decode("utf-8", errors="replace"))
    _, witness = unpack_h7t(packed)
    CHAMBER.mkdir(parents=True, exist_ok=True)
    stem = hashlib.sha256(packed).hexdigest()[:16]
    out = CHAMBER / f"{stem}.h7t"
    out.write_bytes(packed)
    entry = {
        "ok": True,
        "safe_stack": False,
        "h7t": str(out.relative_to(STATE)) if str(out).startswith(str(STATE)) else str(out),
        "sha256": _sha256(packed),
        "truth": witness.get("truth"),
        "inner_format": witness.get("inner_format"),
        "benefits_factor": witness.get("benefits_factor"),
        "isolation": "chamber_only",
        "ingested_at": _utc(),
    }
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"event": "ingest", **entry}, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return entry


def panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    chamber_files = sorted(CHAMBER.glob("*.h7t")) if CHAMBER.is_dir() else []
    doc = {
        "ok": True,
        "schema": "field-h7t-truth-panel/v1",
        "title": doctrine.get("title"),
        "format": FORMAT,
        "motto": doctrine.get("motto"),
        "updated": _utc(),
        "safe_stack_prefixes": safe_stack_prefixes(),
        "chamber_count": len(chamber_files),
        "chamber_dir": str(CHAMBER),
        "benefits_factor": int((doctrine.get("benefits") or {}).get("h7s_speedup_factor") or 100),
        "isolation": doctrine.get("isolation") or {},
        "api": "/api/field-h7t-truth",
        "ingest_usage": "POST body or field-h7t-truth.py ingest PATH",
    }
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "safe" and len(sys.argv) > 2:
        ok = is_safe_asset(path=sys.argv[2])
        print(json.dumps({"ok": True, "path": sys.argv[2], "safe_stack": ok}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "ingest" and len(sys.argv) > 2:
        src = Path(sys.argv[2])
        if not src.is_file():
            print(json.dumps({"ok": False, "error": f"missing {src}"}, ensure_ascii=False))
            return 1
        raw = src.read_bytes()
        out = ingest_unsafe(raw, path=str(src), condense="--condense" in sys.argv)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "pack" and len(sys.argv) > 2:
        src = Path(sys.argv[2])
        raw = src.read_bytes() if src.is_file() else sys.argv[2].encode()
        packed = pack_h7t(raw, {"path": str(src), "source": "cli"})
        dest = Path(sys.argv[3]) if len(sys.argv) > 3 else src.with_suffix(".h7t")
        dest.write_bytes(packed)
        print(json.dumps({"ok": True, "dest": str(dest), "bytes": len(packed)}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "unpack" and len(sys.argv) > 2:
        data = Path(sys.argv[2]).read_bytes()
        inner, meta = unpack_h7t(data)
        print(json.dumps({"ok": True, "meta": meta, "inner_bytes": len(inner)}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-h7t-truth.py [panel|safe PATH|ingest PATH|pack SRC [DEST]|unpack H7T]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())