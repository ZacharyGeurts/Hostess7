#!/usr/bin/env pythong
"""Field layer sweep — detect adjacent competing fields at localhost; non-destructive defield to layer 1."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-layer-sweep-doctrine.json"
RECEIPT = STATE / "field-layer-sweep.json"
LOCALHOST = "127.0.0.1"
CANONICAL_LAYER = 1
_LAYER_RE = re.compile(r'"layer"\s*:\s*(\d+)')


def _now() -> str:
    import time
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


def _citation_rank(cite: str, priorities: list[str]) -> int:
    c = (cite or "").strip()
    for i, p in enumerate(priorities):
        if c == p or c.startswith(p):
            return i
    return len(priorities) + 1


def _scan_state_plates() -> list[dict[str, Any]]:
    plates: list[dict[str, Any]] = []
    if not STATE.is_dir():
        return plates
    for path in sorted(STATE.glob("field-*-block.json")):
        doc = _load(path, {})
        if not doc:
            continue
        plates.append({
            "path": str(path),
            "id": doc.get("facet") or path.stem,
            "layer": int(doc.get("field_layer") or doc.get("layer") or CANONICAL_LAYER),
            "citation": doc.get("ironclad_citation") or "",
            "sealed": bool(doc.get("ironclad_sealed")),
            "ok": bool(doc.get("ok")),
        })
    for path in sorted(STATE.glob("field-*-panel.json")):
        doc = _load(path, {})
        snap = doc.get("snapshot") or {}
        if not doc and not snap:
            continue
        plates.append({
            "path": str(path),
            "id": snap.get("facet") or doc.get("schema") or path.stem,
            "layer": int(snap.get("field_layer") or doc.get("field_layer") or CANONICAL_LAYER),
            "citation": snap.get("ironclad_citation") or doc.get("ironclad_citation") or "",
            "sealed": bool(snap.get("ironclad_sealed") or doc.get("ironclad_sealed")),
            "ok": bool(snap.get("ok") or doc.get("ok")),
        })
    return plates


def _promote_layer_zero_in_text(text: str) -> tuple[str, int]:
    fixes = 0
    out = text

    def _sub_layer_zero(m: re.Match[str]) -> str:
        nonlocal fixes
        val = int(m.group(1))
        if val == 0:
            fixes += 1
            return '"layer": 1'
        return m.group(0)

    out = _LAYER_RE.sub(_sub_layer_zero, out)
    for old, new in (
        ("layer 0", "layer 1"),
        ("Layer 0", "Layer 1"),
        ("field layer 0", "field layer 1"),
        ("field_layer 0", "field_layer 1"),
        ("at layer 0", "at field layer 1"),
    ):
        if old in out:
            fixes += out.count(old)
            out = out.replace(old, new)
    return out, fixes


def refield_layer_one_doctrines(*, apply: bool = False) -> dict[str, Any]:
    """Promote abolished layer 0 → field layer 1 in field doctrine JSON (non-destructive text remap)."""
    roots = [INSTALL / "data", INSTALL / "Queen" / "world"]
    touched: list[dict[str, Any]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            rel = str(path.relative_to(INSTALL))
            if "GIMP" in rel or "OBS" in rel or "node_modules" in rel:
                continue
            try:
                raw = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if '"layer": 0' not in raw and "layer 0" not in raw:
                continue
            new_raw, fixes = _promote_layer_zero_in_text(raw)
            if fixes <= 0:
                continue
            row = {"path": rel, "fixes": fixes, "applied": False}
            if apply:
                tmp = path.with_suffix(".refield.tmp")
                tmp.write_text(new_raw, encoding="utf-8")
                tmp.replace(path)
                row["applied"] = True
            touched.append(row)
    return {
        "ok": True,
        "apply": apply,
        "canonical_field_layer": CANONICAL_LAYER,
        "files": touched,
        "fix_count": sum(int(r.get("fixes") or 0) for r in touched),
    }


def sweep_localhost_fields(*, apply: bool = False) -> dict[str, Any]:
    """Find competing field plates at the same layer on localhost; defield losers without deleting data."""
    doc = _doctrine()
    priorities = list(doc.get("ironclad_priority") or [])
    plates = _scan_state_plates()
    by_layer: dict[int, list[dict[str, Any]]] = {}
    for p in plates:
        layer = int(p.get("layer") or CANONICAL_LAYER)
        if layer < CANONICAL_LAYER:
            layer = CANONICAL_LAYER
            p["layer_promoted"] = True
        by_layer.setdefault(layer, []).append(p)

    competitions: list[dict[str, Any]] = []
    defield_actions: list[dict[str, Any]] = []

    for layer, group in sorted(by_layer.items()):
        if len(group) <= 1:
            continue
        ranked = sorted(
            group,
            key=lambda x: (
                _citation_rank(str(x.get("citation") or ""), priorities),
                0 if x.get("sealed") else 1,
                0 if x.get("ok") else 1,
                str(x.get("id") or ""),
            ),
        )
        winner = ranked[0]
        losers = ranked[1:]
        competitions.append({
            "layer": layer,
            "device": LOCALHOST,
            "winner": winner.get("id"),
            "winner_path": winner.get("path"),
            "losers": [l.get("id") for l in losers],
        })
        for loser in losers:
            action = {
                "action": "defield",
                "device": LOCALHOST,
                "layer": layer,
                "winner": winner.get("id"),
                "loser": loser.get("id"),
                "loser_path": loser.get("path"),
                "non_destructive": True,
                "payload_preserved": True,
                "applied": False,
            }
            if apply:
                path = Path(loser["path"])
                panel = _load(path, {})
                panel["defielded"] = True
                panel["defield_reason"] = "adjacent_competing_field"
                panel["defield_winner"] = winner.get("id")
                panel["field_layer"] = CANONICAL_LAYER
                panel["defield_at"] = _now()
                _save(path, panel)
                action["applied"] = True
            defield_actions.append(action)

    nf_audit: dict[str, Any] = {}
    try:
        import importlib.util
        nf_path = INSTALL / "lib" / "field-non-fielded-safety.py"
        if nf_path.is_file():
            spec = importlib.util.spec_from_file_location("nf_sweep", nf_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "defield_audit"):
                    nf_audit = mod.defield_audit(via_converter=False)
    except Exception as exc:
        nf_audit = {"error": str(exc)}

    out = {
        "schema": "field-layer-sweep/v1",
        "updated": _now(),
        "ok": len(competitions) == 0 or all(a.get("applied") for a in defield_actions) if apply else True,
        "device": LOCALHOST,
        "canonical_field_layer": CANONICAL_LAYER,
        "layer_zero_abolished": True,
        "plate_count": len(plates),
        "competitions": competitions,
        "defield_actions": defield_actions,
        "defield_audit": nf_audit,
        "apply": apply,
    }
    _save(RECEIPT, out)
    return out


def sweep(*, apply: bool = False, refield_doctrines: bool = False) -> dict[str, Any]:
    layer = sweep_localhost_fields(apply=apply)
    refield = refield_layer_one_doctrines(apply=refield_doctrines)
    return {
        "schema": "field-layer-sweep-report/v1",
        "updated": _now(),
        "ok": layer.get("ok") and refield.get("ok"),
        "localhost_sweep": layer,
        "refield_layer_one": refield,
    }


def main() -> int:
    apply = "--apply" in sys.argv
    refield = "--refield" in sys.argv
    cmd = next((a for a in sys.argv[1:] if not a.startswith("-")), "json").strip().lower()
    if cmd in ("json", "sweep", "audit"):
        out = sweep(apply=apply, refield_doctrines=refield)
    elif cmd == "localhost":
        out = sweep_localhost_fields(apply=apply)
    elif cmd == "refield":
        out = refield_layer_one_doctrines(apply=apply)
    else:
        print(json.dumps({
            "error": "usage",
            "cmds": ["sweep [--apply] [--refield]", "localhost [--apply]", "refield [--apply]", "json"],
        }))
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    import sys
    raise SystemExit(main())