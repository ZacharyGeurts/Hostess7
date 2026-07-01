#!/usr/bin/env pythong
"""Field depth singularizer — seal and destroy depth fields.

Single field depth always (depth 0). Depth fields are to be sealed and destroyed:
any field_depth query or field-on-field layer is stripped at every gate, logged,
and eradicated from panel state. Soft-touch defrag destroys stray depth during
active operation.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "single-field-depth-doctrine.json"
PANEL = STATE / "field-depth-singularizer.json"
LEDGER = STATE / "field-depth-singularizer.jsonl"
CURSOR = STATE / "field-depth-singularizer.cursor"

_DEPTH_PARAM_RE = re.compile(r"([?&])field_depth=\d+")
_DEPTH_JSON_RE = re.compile(r'"field_depth"\s*:\s*([1-9]\d*)')
_LAYER_DEPTH_RE = re.compile(r'"depth"\s*:\s*([1-9]\d*)')

# Small panel JSON only — soft touch, no monolithic blast
_SCAN_TARGETS = (
    "field-queen-browser-panel.json",
    "ironclad-field-sanity-panel.json",
    "field-underlay-surface.json",
    "field-host-desktop-panel.json",
    "queen-field-browser-panel.json",
)

_BATCH_PER_CYCLE = int(os.environ.get("NEXUS_DEPTH_SINGULARIZER_BATCH", "3"))


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


def single_field_depth_enabled() -> bool:
    return os.environ.get("NEXUS_SINGLE_FIELD_DEPTH", "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


def parse_requested_field_depth(url: str) -> int:
    """Raw depth requested in URL before enforcement — 0 if absent or invalid."""
    u = (url or "").strip()
    if not u or "field_depth" not in u:
        return 0
    try:
        q = parse_qs(urlparse(u).query)
        return max(0, int((q.get("field_depth") or ["0"])[0]))
    except (ValueError, TypeError, IndexError):
        return 0


def depth_field_creation_forbidden(*, url: str = "", layer_depth: int | None = None) -> bool:
    """True when policy forbids creating a nested / depth field."""
    if not single_field_depth_enabled():
        return False
    requested = parse_requested_field_depth(url)
    layer = int(layer_depth or 0)
    return requested > 0 or layer > 0


def enforce_depth_field_impossible(
    url: str,
    *,
    layer_depth: int | None = None,
) -> dict[str, Any]:
    """Strip depth creation attempts — return enforced URL + impossibility receipt."""
    u = (url or "").strip()
    requested = parse_requested_field_depth(u)
    layer = int(layer_depth or 0)
    forbidden = depth_field_creation_forbidden(url=u, layer_depth=layer)
    clean_url, url_stripped = strip_field_depth_from_url(u)
    violation = forbidden or url_stripped or (layer > 0)
    if violation and single_field_depth_enabled():
        _append_ledger({
            "ts": _now(),
            "event": "depth_field_sealed_and_destroyed",
            "requested_depth": requested,
            "layer_depth": layer,
            "url_stripped": url_stripped,
            "url": u[:500],
        })
    return {
        "url": clean_url,
        "forbidden": forbidden,
        "violation": violation,
        "depth_field_requested": requested,
        "layer_depth_requested": layer,
        "depth_field_stripped": url_stripped or (requested > 0),
        "depth_field_destroyed": violation and single_field_depth_enabled(),
        "depth_fields_sealed_and_destroyed": single_field_depth_enabled(),
        "depth_field_impossible": single_field_depth_enabled(),
        "field_on_field_forbidden": single_field_depth_enabled(),
        "creation_forbidden": single_field_depth_enabled(),
        "single_field_depth": single_field_depth_enabled(),
        "max_field_depth": 0 if single_field_depth_enabled() else None,
        "rule": "depth_fields_sealed_and_destroyed" if single_field_depth_enabled() else "legacy_depth_cap",
        "citation": "ironclad:field_sanity:4" if single_field_depth_enabled() else None,
    }


def impossibility_posture() -> dict[str, Any]:
    """System posture — depth fields cannot be created when policy is on."""
    enabled = single_field_depth_enabled()
    cached = _load(PANEL, {})
    return {
        "schema": "field-depth-impossibility/v1",
        "ts": _now(),
        "ok": True,
        "depth_field_impossible": enabled,
        "depth_fields_sealed_and_destroyed": enabled,
        "field_on_field_forbidden": enabled,
        "creation_forbidden": enabled,
        "single_field_depth": enabled,
        "max_field_depth": 0 if enabled else None,
        "rule": "forbid_and_strip_at_every_gate",
        "canonical_field_layer": 1,
        "motto": "One field. Field layer 1. Depth fields sealed and destroyed.",
        "citation": "ironclad:field_sanity:4",
        "singularizer": cached if cached.get("schema") == "field-depth-singularizer/v1" else {"mode": "idle"},
    }


def strip_field_depth_from_url(url: str) -> tuple[str, bool]:
    """Remove or zero field_depth query — return (url, changed)."""
    u = (url or "").strip()
    if not u or "field_depth" not in u:
        return u, False
    try:
        parsed = urlparse(u)
        q = parse_qs(parsed.query, keep_blank_values=True)
        raw = (q.get("field_depth") or ["0"])[0]
        try:
            d = int(raw)
        except (ValueError, TypeError):
            d = 0
        if d <= 0 and "field_depth" not in q:
            return u, False
        q.pop("field_depth", None)
        flat: list[tuple[str, str]] = []
        for key, vals in q.items():
            for val in vals:
                flat.append((key, val))
        new_query = urlencode(flat)
        new_url = urlunparse(parsed._replace(query=new_query))
        return new_url, new_url != u or d > 0
    except Exception:
        new_u = _DEPTH_PARAM_RE.sub(r"\1field_depth=0", u)
        if new_u != u:
            return new_u.replace("field_depth=0&", "").replace("&field_depth=0", "").replace("?field_depth=0", ""), True
        return u, False


def singularize_layer(layer: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """One layer → depth 0, URL stripped. Returns (layer, fix_count)."""
    if not isinstance(layer, dict):
        return layer, 0
    fixes = 0
    out = dict(layer)
    depth = int(out.get("depth") or 0)
    url = str(out.get("url") or "")
    new_url, url_changed = strip_field_depth_from_url(url)
    if url_changed:
        out["url"] = new_url
        fixes += 1
    if depth != 0:
        out["depth"] = 0
        fixes += 1
    if out.get("field_on_field"):
        out["field_on_field"] = False
        fixes += 1
    return out, fixes


def pre_singularize_body(body: dict[str, Any] | None) -> tuple[dict[str, Any], int]:
    """Preflight active layers before sanity pass — defrag-style, non-blocking."""
    body = dict(body or {})
    if not single_field_depth_enabled():
        return body, 0
    fixes = 0
    layers = body.get("layers")
    if isinstance(layers, list):
        sing: list[dict[str, Any]] = []
        for item in layers:
            if not isinstance(item, dict):
                sing.append(item)
                continue
            fixed, n = singularize_layer(item)
            sing.append(fixed)
            fixes += n
        body["layers"] = sing
    if body.get("fielded") and fixes:
        body["fielded"] = any(int(L.get("depth") or 0) > 0 for L in body["layers"] if isinstance(L, dict))
    body["single_field_depth"] = True
    body["depth_field_impossible"] = True
    body["depth_fields_sealed_and_destroyed"] = True
    body["creation_forbidden"] = True
    body["depth_singularized"] = fixes > 0
    body["depth_field_destroyed"] = fixes > 0
    body["depth_fixes"] = fixes
    return body, fixes


def _maybe_strip_url_string(value: str) -> tuple[str, int]:
    """Strip field_depth from URL-like strings embedded in panel JSON."""
    if not value or "field_depth" not in value:
        return value, 0
    if not (value.startswith(("http://", "https://", "queen://")) or "field_depth=" in value):
        return value, 0
    new_url, changed = strip_field_depth_from_url(value)
    return new_url, 1 if changed else 0


def _singularize_json_node(node: Any, *, key: str | None = None) -> tuple[Any, int]:
    """Walk JSON — zero depth keys and strip field_depth from URLs (defrag-safe)."""
    fixes = 0
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for k, v in node.items():
            fixed_v, n = _singularize_json_node(v, key=k)
            fixes += n
            if k == "depth" and isinstance(fixed_v, int) and fixed_v != 0:
                out[k] = 0
                fixes += 1
                continue
            if k == "field_depth" and isinstance(fixed_v, int) and fixed_v != 0:
                out[k] = 0
                fixes += 1
                continue
            if k == "field_on_field" and fixed_v is True:
                out[k] = False
                fixes += 1
                continue
            if k == "url" and isinstance(fixed_v, str):
                new_url, n = _maybe_strip_url_string(fixed_v)
                out[k] = new_url
                fixes += n
                continue
            out[k] = fixed_v
        return out, fixes
    if isinstance(node, list):
        out_list: list[Any] = []
        for item in node:
            fixed_item, n = _singularize_json_node(item)
            out_list.append(fixed_item)
            fixes += n
        return out_list, fixes
    if isinstance(node, str) and key not in ("url",):
        new_s, n = _maybe_strip_url_string(node)
        return new_s, n
    return node, 0


def _singularize_json_doc(doc: Any) -> tuple[Any, int]:
    return _singularize_json_node(doc)


def _fix_text_blob(text: str) -> tuple[str, int]:
    fixes = 0
    out = text

    def _depth_zero(m: re.Match[str]) -> str:
        nonlocal fixes
        fixes += 1
        return '"field_depth": 0'

    out = _DEPTH_JSON_RE.sub(_depth_zero, out)

    def _layer_depth_zero(m: re.Match[str]) -> str:
        nonlocal fixes
        fixes += 1
        return '"depth": 0'

    out = _LAYER_DEPTH_RE.sub(_layer_depth_zero, out)

    # URL query fragments inside JSON strings — old-defrag pass for stray ?field_depth=N
    url_pat = re.compile(r'(https?://[^\s"\\]+?)([?&])field_depth=\d+')
    while True:
        new_out, n = url_pat.subn(r"\1", out, count=1)
        if n <= 0:
            break
        out = new_out.replace("?&", "?").replace("&&", "&").rstrip("?&")
        fixes += 1
    return out, fixes


def _singularize_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "ok": False, "skipped": "missing"}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"path": str(path), "ok": False, "error": str(exc)}
    n = 0
    fixed = raw
    try:
        doc = json.loads(raw)
        fixed_doc, n = _singularize_json_doc(doc)
        if n > 0:
            fixed = json.dumps(fixed_doc, ensure_ascii=False, indent=2) + "\n"
    except json.JSONDecodeError:
        fixed, n = _fix_text_blob(raw)
    if n <= 0:
        return {"path": str(path), "ok": True, "fixes": 0, "unchanged": True}
    try:
        json.loads(fixed)
    except json.JSONDecodeError:
        return {"path": str(path), "ok": False, "error": "json_invalid_after_fix", "fixes": n}
    tmp = path.with_suffix(path.suffix + ".singular.tmp")
    tmp.write_text(fixed, encoding="utf-8")
    tmp.replace(path)
    return {"path": str(path), "ok": True, "fixes": n, "singularized": True}


def cycle(*, batch: int | None = None) -> dict[str, Any]:
    """Incremental defrag pass over state — soft touch, active-operation safe."""
    if not single_field_depth_enabled():
        return {"ok": True, "skipped": "single_field_depth_off", "schema": "field-depth-singularizer/v1"}

    batch_n = max(1, batch or _BATCH_PER_CYCLE)
    targets = [STATE / name for name in _SCAN_TARGETS if (STATE / name).is_file()]
    if not targets:
        targets = sorted(STATE.glob("*-panel.json"))[:12]

    cursor = int(_load(CURSOR, {"index": 0}).get("index") or 0)
    if cursor >= len(targets):
        cursor = 0
    chunk = targets[cursor : cursor + batch_n]
    if not chunk and targets:
        chunk = targets[:batch_n]
    results: list[dict[str, Any]] = []
    total_fixes = 0
    for path in chunk:
        row = _singularize_file(path)
        results.append(row)
        total_fixes += int(row.get("fixes") or 0)

    next_cursor = (cursor + batch_n) % max(len(targets), 1)
    _save(CURSOR, {"index": next_cursor, "ts": _now(), "total_targets": len(targets)})

    receipt = {
        "schema": "field-depth-singularizer/v1",
        "ts": _now(),
        "ok": True,
        "mode": "defrag_incremental",
        "motto": "Soft touch — seal and destroy stray depth fields during active operation",
        "batch": batch_n,
        "cursor": cursor,
        "next_cursor": next_cursor,
        "targets_total": len(targets),
        "fixes": total_fixes,
        "results": results,
        "active_operation": True,
        "single_field_depth": True,
        "depth_field_impossible": True,
        "depth_fields_sealed_and_destroyed": True,
        "creation_forbidden": True,
    }
    _save(PANEL, receipt)
    _append_ledger({
        "ts": receipt["ts"],
        "fixes": total_fixes,
        "batch": batch_n,
        "cursor": cursor,
    })
    return receipt


def is_dimensional_pit(layer: dict[str, Any]) -> bool:
    """Bad nested depth — field_depth query, layer depth > 0, or field-on-field."""
    if not isinstance(layer, dict):
        return False
    depth = int(layer.get("depth") or 0)
    url = str(layer.get("url") or "")
    requested = parse_requested_field_depth(url)
    return depth > 0 or requested > 0 or bool(layer.get("field_on_field"))


def snap_dimensional_pits(
    layers: list[dict[str, Any]] | None = None,
    *,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Instant O(n) snap — no disk I/O. Field die hot path."""
    if not single_field_depth_enabled():
        return {
            "ok": True,
            "skipped": "single_field_depth_off",
            "schema": "field-depth-instant-snap/v1",
            "instant": True,
        }

    src_body = dict(body or {})
    raw_layers = list(layers) if layers is not None else list(src_body.get("layers") or [])
    pits: list[dict[str, Any]] = []
    cleaned: list[Any] = []
    snapped = 0

    for item in raw_layers:
        if not isinstance(item, dict):
            cleaned.append(item)
            continue
        if is_dimensional_pit(item):
            pits.append({
                "id": item.get("id"),
                "url": str(item.get("url") or "")[:240],
                "depth": int(item.get("depth") or 0),
                "field_on_field": bool(item.get("field_on_field")),
            })
        fixed, n = singularize_layer(item)
        cleaned.append(fixed)
        snapped += n

    body_fixes = 0
    if int(src_body.get("field_depth") or 0) > 0:
        src_body["field_depth"] = 0
        body_fixes += 1
    if src_body.get("field_on_field"):
        src_body["field_on_field"] = False
        body_fixes += 1
    if src_body.get("fielded") and snapped + body_fixes > 0:
        src_body["fielded"] = False

    total = snapped + body_fixes
    receipt = {
        "schema": "field-depth-instant-snap/v1",
        "ts": _now(),
        "ok": True,
        "instant": True,
        "mode": "snap_dimensional_pits",
        "pits_found": len(pits),
        "pits_snapped": total,
        "pits": pits,
        "layers": cleaned,
        "single_field_depth": True,
        "max_field_depth": 0,
        "depth_field_impossible": True,
        "depth_fields_sealed_and_destroyed": True,
        "creation_forbidden": True,
        "field_on_field_forbidden": True,
        "message": (
            f"snapped {total} dimensional pit(s)"
            if total
            else "depth zero — no pits"
        ),
    }
    if total > 0:
        _append_ledger({
            "ts": receipt["ts"],
            "event": "dimensional_pits_snapped",
            "pits_found": len(pits),
            "pits_snapped": total,
            "instant": True,
        })
    return receipt


def instant_field_die_check(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Field die hook — instant depth check, snap bad dimensional pits."""
    snap = snap_dimensional_pits(body=body)
    snap["field_die"] = True
    snap["mode"] = "field_die_instant"
    snap["rule"] = "single_field_depth_instant_on_field_die"
    return snap


def posture() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema") == "field-depth-singularizer/v1":
        return cached
    return {
        "schema": "field-depth-singularizer/v1",
        "ts": _now(),
        "ok": True,
        "fixes": 0,
        "mode": "idle",
        "single_field_depth": single_field_depth_enabled(),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "panel"):
        print(json.dumps(posture(), ensure_ascii=False))
        return 0
    if cmd in ("cycle", "defrag", "refresh"):
        print(json.dumps(cycle(), ensure_ascii=False))
        return 0
    if cmd == "preflight":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        fixed, n = pre_singularize_body(body)
        fixed["preflight_fixes"] = n
        print(json.dumps(fixed, ensure_ascii=False))
        return 0
    if cmd == "strip-url" and len(sys.argv) > 2:
        url, changed = strip_field_depth_from_url(sys.argv[2])
        print(json.dumps({"url": url, "changed": changed}, ensure_ascii=False))
        return 0
    if cmd in ("forbid", "enforce") and len(sys.argv) > 2:
        layer = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        print(json.dumps(enforce_depth_field_impossible(sys.argv[2], layer_depth=layer), ensure_ascii=False))
        return 0
    if cmd == "impossibility":
        print(json.dumps(impossibility_posture(), ensure_ascii=False))
        return 0
    if cmd in ("instant", "snap", "field_die"):
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        if cmd == "field_die":
            print(json.dumps(instant_field_die_check(body), ensure_ascii=False))
        else:
            print(json.dumps(snap_dimensional_pits(body=body), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: field-depth-singularizer.py [json|cycle|preflight|instant|snap|field_die|strip-url URL|forbid URL [layer]|impossibility]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())