#!/usr/bin/env pythong
"""Ironclad Truth — field terminal program: information or diagnostic full response."""
from __future__ import annotations

import importlib.util
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))

_DIAG_RE = re.compile(
    r"\b(diagnostic|diagnose|health|status|check|verify|audit|posture|meld|panel|"
    r"ironclad|sanity|kernel|proc|runtime|error|fault|broken)\b",
    re.I,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _import_py(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _mode_for_query(query: str, explicit: str | None = None) -> str:
    if explicit in ("information", "diagnostic"):
        return explicit
    q = (query or "").strip().lower()
    if not q or q in ("help", "?", "truth"):
        return "information"
    if _DIAG_RE.search(q):
        return "diagnostic"
    return "information"


def _ironclad_immediate() -> dict[str, Any]:
    cached = _load(STATE / "ironclad-immediate.json", {})
    if cached.get("title") or cached.get("ironclad_sealed") is not None:
        return cached
    mod = _import_py(INSTALL / "lib" / "ironclad-immediate.py", "ironclad_immediate")
    if mod and hasattr(mod, "immediate_slice"):
        try:
            return mod.immediate_slice(write=False)
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:120]}
    return {"ok": False, "missing": "ironclad-immediate.py"}


def _field_sanity_cite() -> str:
    mod = _import_py(INSTALL / "lib" / "ironclad-field-sanity.py", "ironclad_field_sanity")
    if mod and hasattr(mod, "cite_field_sanity"):
        try:
            return mod.cite_field_sanity(2) or ""
        except Exception:
            pass
    return "ironclad:field_sanity:2 — classify, strip, dedupe, flatten, cool_sort"


def _gnu_terminal_plate() -> dict[str, Any]:
    cached = _load(STATE / "field-gnu-terminal-iron-plate-panel.json", {})
    if cached.get("ok"):
        return cached
    mod = _import_py(INSTALL / "lib" / "field-gnu-terminal-iron-plate.py", "gnu_terminal_plate")
    if mod and hasattr(mod, "posture"):
        try:
            return mod.posture(write=False)
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:120]}
    return {}


def _plate_meld_gen() -> Any:
    doc = _load(STATE / "field-plate-meld.json", {})
    return doc.get("generation")


def _search_hits(query: str, limit: int = 8) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    idx = _load(STATE / "ironclad-search-index-panel.json", {})
    rows = idx.get("entries") or idx.get("index") or []
    q = query.strip().lower()
    hits: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        blob = " ".join(
            str(row.get(k) or "")
            for k in ("title", "label", "name", "id", "path", "tags", "context")
        ).lower()
        if q in blob:
            hits.append(row)
        if len(hits) >= limit:
            break
    return hits


def _format_information(query: str, imm: dict[str, Any]) -> list[str]:
    lines = [
        "Ironclad Truth — information",
        f"  at: {_now()}",
        f"  query: {query or '(general)'}",
        "",
        imm.get("title") or "The Ironclad",
        f"  motto: {imm.get('motto') or '—'}",
        f"  sealed: {imm.get('ironclad_sealed')} · verdict: {imm.get('verdict') or '—'}",
        f"  truth%: {imm.get('truth_percent')}",
        f"  charge: {imm.get('charge_holder') or '—'}",
        "",
        "Cite: " + _field_sanity_cite(),
        "",
        "Type: truth diagnostic <topic>  — full system diagnostic slice",
        "Type: truth <topic>           — Ironclad search + information receipt",
        "Examples:",
        "  truth ironclad meld",
        "  truth diagnostic panel",
        "  truth gnu terminal",
    ]
    if query.strip():
        hits = _search_hits(query.strip())
        if hits:
            lines.extend(["", f"Ironclad search ({len(hits)} hits):"])
            for h in hits:
                label = h.get("title") or h.get("label") or h.get("id") or h.get("path") or "—"
                lines.append(f"  · {label}")
    return lines


def _format_diagnostic(query: str, imm: dict[str, Any], plate: dict[str, Any]) -> list[str]:
    meld_gen = _plate_meld_gen()
    term = plate.get("terminal") or {}
    ident = plate.get("identity") or {}
    lines = [
        "Ironclad Truth — diagnostic",
        f"  at: {_now()}",
        f"  query: {query or '(full slice)'}",
        "",
        "── Ironclad immediate ──",
        f"  sealed: {imm.get('ironclad_sealed')} · integrity: {imm.get('integrity_ok')}",
        f"  truth%: {imm.get('truth_percent')} · verdict: {imm.get('verdict')}",
        f"  hash: {(imm.get('canonical_hash') or '—')[:48]}",
        f"  reality: {imm.get('reality_field_uri') or '/api/ironclad/reality-field'}",
        "",
        "── Field sanity ──",
        f"  {_field_sanity_cite()}",
        "",
        "── GNU terminal iron plate ──",
        f"  embed: {plate.get('embed_present')} · shell≡terminal: {plate.get('shell_terminal_identical')}",
        f"  terminal ok: {term.get('ok', '—')}",
        f"  identity ok: {ident.get('ok', '—')}",
        f"  plate_meld gen: {meld_gen or '—'}",
        "",
        "── Panel state ──",
    ]
    for name in (
        "ironclad-field-sanity-panel.json",
        "field-gnu-terminal-iron-plate-panel.json",
        "field-plate-meld.json",
    ):
        p = STATE / name
        lines.append(f"  {name}: {'present' if p.is_file() else 'missing'}")
    if query.strip():
        hits = _search_hits(query.strip(), limit=5)
        if hits:
            lines.extend(["", "── Targeted hits ──"])
            for h in hits:
                label = h.get("title") or h.get("label") or h.get("id") or "—"
                lines.append(f"  · {label}")
    lines.extend(["", "Ironclad full response complete."])
    return lines


def ironclad_truth(query: str = "", *, mode: str | None = None) -> dict[str, Any]:
    """Return Ironclad truth receipt for terminal `truth` command."""
    q = (query or "").strip()
    resolved_mode = _mode_for_query(q, mode)
    imm = _ironclad_immediate()
    plate = _gnu_terminal_plate()
    if resolved_mode == "diagnostic":
        body = _format_diagnostic(q, imm, plate)
    else:
        body = _format_information(q, imm)
    return {
        "ok": True,
        "schema": "field-ironclad-truth/v1",
        "program": "truth",
        "mode": resolved_mode,
        "query": q,
        "at": _now(),
        "ironclad": {
            "sealed": imm.get("ironclad_sealed"),
            "truth_percent": imm.get("truth_percent"),
            "verdict": imm.get("verdict"),
            "cite": _field_sanity_cite(),
        },
        "output": "\n".join(body),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(
            json.dumps(
                ironclad_truth(
                    str(body.get("query") or body.get("text") or ""),
                    mode=str(body.get("mode") or "") or None,
                ),
                ensure_ascii=False,
            )
        )
        return 0
    if cmd in ("json", "help"):
        print(
            json.dumps(
                {
                    "ok": True,
                    "schema": "field-ironclad-truth/v1",
                    "usage": "truth [diagnostic] <query>",
                    "modes": ["information", "diagnostic"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    q = " ".join(sys.argv[1:])
    print(json.dumps(ironclad_truth(q), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())