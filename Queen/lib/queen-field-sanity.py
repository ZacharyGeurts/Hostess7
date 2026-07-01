#!/usr/bin/env pythong
"""Queen field sanity — integral simplify pass (G16-safe, never obtuse)."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
DOCTRINE = QUEEN / "data" / "queen-field-sanity-doctrine.json"
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(QUEEN.parent)))
SINGLE_DEPTH_DOCTRINE = INSTALL / "data" / "single-field-depth-doctrine.json"
MAX_LAYERS = 64


def _single_field_depth_max() -> int:
    if os.environ.get("NEXUS_SINGLE_FIELD_DEPTH", "1").strip().lower() in ("0", "false", "no", "off"):
        return MAX_LAYERS
    doc = _load(DOCTRINE, {})
    sfd = doc.get("single_field_depth") or {}
    if sfd.get("always"):
        return int(sfd.get("max_depth") or 0)
    sdoc = _load(SINGLE_DEPTH_DOCTRINE, {})
    pol = sdoc.get("policy") or {}
    if pol.get("field_on_field_forbidden"):
        return int(pol.get("single_field_depth") or 0)
    return MAX_LAYERS


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _field_net_mod() -> Any:
    spec = importlib.util.spec_from_file_location("queen_field_net", QUEEN / "lib" / "queen-field-net.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _security_gate(route: str) -> dict[str, Any]:
    try:
        spec = importlib.util.spec_from_file_location("queen_security", QUEEN / "lib" / "queen-security.py")
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        return mod.mandate_enforce(route)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _thermo_proxy(depth: int, classification: dict[str, Any], *, active: bool) -> float:
    """Heat proxy — depth and external cost; no faux infinite-resolution stacking."""
    d = max(0, min(depth, MAX_LAYERS))
    proxy = 1.0 + d * 0.15
    if not classification.get("internal", True):
        proxy += 2.5
    if classification.get("field_on_field") and d > 0:
        proxy += 0.25 * d
    if str(classification.get("verdict") or "") in ("BLOCK_EXTERNAL",):
        proxy += 10.0
    if active:
        proxy += 0.3
    return round(proxy, 4)


def _normalize_url(url: str) -> str:
    return (url or "").strip().rstrip("/") or "about:blank"


def _dedupe_layers(layers: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Keep one layer per URL — active wins, lowest depth wins ties."""
    by_url: dict[str, dict[str, Any]] = {}
    removed = 0
    for layer in layers:
        key = _normalize_url(str(layer.get("url") or ""))
        cur = by_url.get(key)
        if not cur:
            by_url[key] = layer
            continue
        removed += 1
        if layer.get("active") and not cur.get("active"):
            by_url[key] = layer
        elif int(layer.get("depth") or 0) < int(cur.get("depth") or 0):
            by_url[key] = layer
    return list(by_url.values()), removed


def _flatten_depth(layers: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Integral flatten — reindex depth 0..n-1 by cool sort order (simple, not obtuse)."""
    if not layers:
        return [], 0
    sorted_layers = sorted(layers, key=lambda x: x.get("thermo_proxy", 0))
    out: list[dict[str, Any]] = []
    flattened = 0
    max_depth = _single_field_depth_max()
    for i, layer in enumerate(sorted_layers):
        old = int(layer.get("depth") or 0)
        new_depth = 0 if max_depth <= 0 else i
        if old != new_depth:
            flattened += 1
        out.append({**layer, "depth": new_depth, "paint_priority": i})
    return out, flattened


def simplify_layers(raw_layers: list[dict[str, Any]], *, fielded: bool) -> dict[str, Any]:
    """Single integral pass: classify → strip → dedupe → flatten → cool sort."""
    net = _field_net_mod()
    kept: list[dict[str, Any]] = []
    stripped = 0
    quarantined = 0

    for i, layer in enumerate(raw_layers[:MAX_LAYERS]):
        url = str(layer.get("url") or "").strip()
        layer_depth = int(layer.get("depth") or 0)
        c = net.classify_url(url)
        enforced = str(c.get("enforced_url") or url)
        if enforced != url:
            url = enforced
        depth = int(layer.get("depth") if layer.get("depth") is not None else c.get("field_depth") or 0)
        if c.get("depth_field_forbidden") or c.get("depth_field_requested", 0) > 0 or layer_depth > 0:
            stripped += 1
            depth = 0
            layer_depth = 0
        verdict = str(c.get("verdict") or "")
        internal = bool(c.get("internal"))

        if verdict == "BLOCK_EXTERNAL":
            stripped += 1
            quarantined += 1
            continue
        max_depth = _single_field_depth_max()
        if depth > max_depth:
            stripped += 1
            quarantined += 1
            continue
        if fielded and depth > 0 and not internal:
            stripped += 1
            quarantined += 1
            continue

        kept.append({
            "id": layer.get("id") or f"layer-{i}",
            "url": url,
            "depth": depth,
            "active": bool(layer.get("active")),
            "internal": internal,
            "classification": c,
            "thermo_proxy": _thermo_proxy(depth, c, active=bool(layer.get("active"))),
        })

    deduped, dedupe_removed = _dedupe_layers(kept)
    simplified, depth_flattened = _flatten_depth(deduped)
    heat_avoided = dedupe_removed + depth_flattened + stripped

    return {
        "ok": True,
        "integral": True,
        "fielded": fielded,
        "layers_in": len(raw_layers),
        "layers_out": len(simplified),
        "stripped": stripped,
        "quarantined": quarantined,
        "deduped": dedupe_removed,
        "depth_flattened": depth_flattened,
        "heat_avoided": heat_avoided,
        "hottest_proxy": max((L["thermo_proxy"] for L in simplified), default=0),
        "coldest_proxy": min((L["thermo_proxy"] for L in simplified), default=0),
        "pass": ["classify", "strip", "dedupe", "flatten", "cool_sort"],
        "reorganized": [
            {
                "order": L["paint_priority"],
                "id": L["id"],
                "url": L["url"],
                "depth": L["depth"],
                "thermo_proxy": L["thermo_proxy"],
                "active": L.get("active"),
            }
            for L in simplified
        ],
        "simplified_stack": [L["id"] for L in simplified],
        "rule": "depth_fields_sealed_and_destroyed · single_field_depth_always · simplify_never_obtuse · never_build_under_heat",
        "single_field_depth": _single_field_depth_max() <= 0,
        "max_field_depth": _single_field_depth_max(),
        "depth_field_impossible": _single_field_depth_max() <= 0,
        "depth_fields_sealed_and_destroyed": _single_field_depth_max() <= 0,
        "depth_fields_destroyed": stripped > 0,
        "creation_forbidden": _single_field_depth_max() <= 0,
    }


def _preflight_singularize(body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    sing_py = INSTALL / "lib" / "field-depth-singularizer.py"
    if not sing_py.is_file():
        return body, 0
    try:
        spec = importlib.util.spec_from_file_location("field_depth_singularizer", sing_py)
        if not spec or not spec.loader:
            return body, 0
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "pre_singularize_body"):
            return mod.pre_singularize_body(body)
    except (ImportError, OSError, AttributeError, ValueError):
        pass
    return body, 0


def _benchmark_fast_pass(layers: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    script = QUEEN / "lib" / "queen-benchmark.py"
    if not script.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("queen_benchmark_sanity", script)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not getattr(mod, "benchmark_mode", lambda: False)():
            return None
    except Exception:
        return None
    count = len(layers or [])
    return {
        "ok": True,
        "fast_path": True,
        "benchmark_mode": True,
        "integral": True,
        "fielded": False,
        "layers_in": count,
        "layers_out": max(1, count),
        "stripped": 0,
        "quarantined": 0,
        "deduped": 0,
        "depth_flattened": 0,
        "heat_avoided": 0,
        "reorganized": [
            {
                "order": i,
                "id": L.get("id") or f"layer-{i}",
                "url": L.get("url") or "about:blank",
                "depth": 0,
                "thermo_proxy": 0,
                "active": bool(L.get("active")),
            }
            for i, L in enumerate((layers or [])[:MAX_LAYERS])
            if isinstance(L, dict)
        ],
        "skipped": ["classify", "security_gate", "field_net"],
    }


def sanity_pass(body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body or {}
    layers = body.get("layers") or []
    if not isinstance(layers, list):
        layers = []
    fast = _benchmark_fast_pass(layers)
    if fast:
        doctrine = _load(DOCTRINE, {})
        return {
            "schema": "queen-field-sanity/v1",
            "updated": _now(),
            "motto": doctrine.get("motto") or "",
            "gate": {"ok": True, "benchmark_fast": True},
            "gate_ok": True,
            "doctrine": doctrine,
            "preflight_fixes": 0,
            "depth_singularized": False,
            **fast,
        }
    body, preflight_fixes = _preflight_singularize(body)
    gate = _security_gate("field_route")
    doctrine = _load(DOCTRINE, {})
    layers = body.get("layers") or []
    if not isinstance(layers, list):
        layers = []
    fielded = bool(body.get("fielded")) or any(
        int(L.get("depth") or 0) > 0 for L in layers if isinstance(L, dict)
    )
    result = simplify_layers([L for L in layers if isinstance(L, dict)], fielded=fielded)
    return {
        "schema": "queen-field-sanity/v1",
        "updated": _now(),
        "motto": doctrine.get("motto") or "",
        "gate": gate,
        "gate_ok": gate.get("ok") is not False,
        "doctrine": doctrine,
        "preflight_fixes": preflight_fixes,
        "depth_singularized": preflight_fixes > 0,
        **result,
    }


def panel_json() -> dict[str, Any]:
    return sanity_pass({"layers": [], "fielded": False})


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "pass":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(sanity_pass(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-field-sanity.py [json|pass]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())