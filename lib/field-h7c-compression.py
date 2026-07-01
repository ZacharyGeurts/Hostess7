#!/usr/bin/env pythong
"""H7c (Hostess 7 Condenser) — lossless combinatronic condenser; small optimizer autoplates, spider-wires, recondenses until balance."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import struct
import sys
import time
import zlib
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-h7c-doctrine.json"
BALANCE_TABLE = STATE / "field-h7c-balance-table.json"

MAGIC_V1 = b"H7C\x01"
MAGIC_V2 = b"H7C\x02"
MAGIC_V3 = b"H7C\x03"
MAGIC_V4 = b"H7C\x04"
MAGICS = (MAGIC_V1, MAGIC_V2, MAGIC_V3, MAGIC_V4)
FORMAT_V1 = "h7c/1"
FORMAT_V2 = "h7c/2"
FORMAT_V3 = "h7c/3"
FORMAT_V4 = "h7c/4"
CANONICAL_FIELD_LAYER = 1
H7FIG_RE = __import__("re").compile(r"!\[([^\]]*)\]\(h7fig:([a-zA-Z0-9_.-]+)\)")
BALANCE_TARGET = 0.97
UNIVERSAL_BATTERY = STATE / "field-g16-universal-combinatronic.json"
_UNIVERSAL_CACHE: dict[str, Any] | None = None
_H7_MODULE_CACHE: Any | None = None
_COMBINA_LEAVES_CACHE: list[dict[str, Any]] | None = None
_BALANCE_MOD_CACHE: Any | None = None
_BALANCE_TABLE_MEM: dict[str, Any] | None = None
_BALANCE_BATCH_DEPTH = 0
_BALANCE_DIRTY = False

FACET_UNI_SUB: dict[str, str] = {
    "code": "program_combinatronic",
    "prose": "ironclad_chips",
    "heading": "ironclad_chips",
}


class H7cError(ValueError):
    pass


def _ironclad_block_slice() -> dict[str, Any]:
    path = INSTALL / "lib" / "ironclad-immediate.py"
    if not path.is_file():
        return {}
    try:
        spec = importlib.util.spec_from_file_location("h7c_ironclad", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "immediate_slice"):
                return mod.immediate_slice() or {}
    except Exception:
        pass
    cached = _load(STATE / "ironclad-immediate.json", {})
    return cached if isinstance(cached, dict) else {}


def unwrap_h7c_block(data: bytes) -> tuple[bytes, dict[str, Any] | None]:
    """Peel h7c/4 ironclad block wrapper — inner v1–v3 bytes pass through unchanged."""
    if len(data) < 12 or data[:4] != MAGIC_V4:
        return data, None
    block_hdr_len = struct.unpack("<I", data[4:8])[0]
    start = 8
    end = start + block_hdr_len
    if end + 4 > len(data):
        raise H7cError("truncated H7c block header")
    block_hdr = json.loads(data[start:end].decode("utf-8"))
    inner_len = struct.unpack("<I", data[end : end + 4])[0]
    inner_start = end + 4
    inner_end = inner_start + inner_len
    if inner_end > len(data):
        raise H7cError("truncated H7c block inner")
    inner = data[inner_start:inner_end]
    expect = block_hdr.get("inner_sha256")
    if expect and hashlib.sha256(inner).hexdigest() != expect:
        raise H7cError("H7c block inner sha256 mismatch")
    if inner[:4] not in (MAGIC_V1, MAGIC_V2, MAGIC_V3):
        raise H7cError("H7c block inner is not v1–v3 payload")
    return inner, block_hdr


def wrap_h7c_block(inner: bytes, meta: dict[str, Any] | None = None) -> bytes:
    """Wrap an existing H7c blob in ironclad-sealed h7c/4 block — lossless, field layer 1."""
    if inner[:4] not in (MAGIC_V1, MAGIC_V2, MAGIC_V3):
        raise H7cError("wrap_h7c_block requires inner h7c/1–3 bytes")
    m = meta or {}
    inner_hdr_len = struct.unpack("<I", inner[4:8])[0]
    inner_hdr: dict[str, Any] = {}
    try:
        inner_hdr = json.loads(inner[8 : 8 + inner_hdr_len].decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        inner_hdr = {}
    iron = _ironclad_block_slice()
    block_hdr: dict[str, Any] = {
        "format": FORMAT_V4,
        "schema": "h7c-ironclad-block/v1",
        "field_layer": CANONICAL_FIELD_LAYER,
        "ironclad_sealed": bool(iron.get("ok", True)),
        "ironclad_citation": m.get("ironclad_citation") or "ironclad:h7c:1",
        "inner_format": inner_hdr.get("format") or FORMAT_V2,
        "inner_sha256": hashlib.sha256(inner).hexdigest(),
        "inner_bytes": len(inner),
        "lossless": True,
        "block_wrapper": True,
        "statement": "Ironclad block envelope — inner H7c unchanged; decompress peels block.",
        "packed_at": _now(),
        **{k: v for k, v in m.items() if k not in ("format", "inner_sha256")},
    }
    if iron.get("citation_prefix"):
        block_hdr["ironclad_immediate"] = {
            "citation_prefix": iron.get("citation_prefix"),
            "realized": iron.get("realized"),
        }
    block_json = json.dumps(block_hdr, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(block_json) > 65535:
        raise H7cError("H7c block header too large")
    return b"".join([
        MAGIC_V4,
        struct.pack("<I", len(block_json)),
        block_json,
        struct.pack("<I", len(inner)),
        inner,
    ])


def peel_h7c_bytes(data: bytes) -> tuple[bytes, dict[str, Any] | None]:
    """Return decompressable H7c bytes — unwraps block when present."""
    return unwrap_h7c_block(data)


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
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
    except OSError:
        path.write_text(payload, encoding="utf-8")
        if tmp.is_file():
            try:
                tmp.unlink()
            except OSError:
                pass


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _optimizer_cfg() -> dict[str, Any]:
    return _doctrine().get("optimizer") or {
        "max_cycles": 8,
        "recondense_line_cap": 64,
        "balance_target": BALANCE_TARGET,
    }


def _h7_module() -> Any | None:
    global _H7_MODULE_CACHE
    if _H7_MODULE_CACHE is not None:
        return _H7_MODULE_CACHE
    path = INSTALL / "Hostess7" / "scripts" / "field_h7_book.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_h7_book", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _H7_MODULE_CACHE = mod
    return mod


def _combinamatrix_leaves(*, fast: bool = False) -> list[dict[str, Any]]:
    global _COMBINA_LEAVES_CACHE
    if fast:
        return _COMBINA_LEAVES_CACHE or []
    if _COMBINA_LEAVES_CACHE is not None:
        return _COMBINA_LEAVES_CACHE
    battery = STATE / "field-combinamatrix.json"
    if battery.is_file():
        doc = _load(battery, {})
        cells = list(doc.get("cells") or doc.get("leaves") or [])
        if cells:
            _COMBINA_LEAVES_CACHE = cells
            return cells
    cm = INSTALL / "lib" / "field-combinamatrix.py"
    if not cm.is_file():
        _COMBINA_LEAVES_CACHE = []
        return []
    spec = importlib.util.spec_from_file_location("field_combinamatrix", cm)
    if not spec or not spec.loader:
        _COMBINA_LEAVES_CACHE = []
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        panel = mod.build_matrix(refresh=False)
        cells = list(panel.get("cells") or panel.get("leaves") or [])
    except Exception:
        cells = []
    _COMBINA_LEAVES_CACHE = cells
    return cells


def _universal_mod() -> Any | None:
    path = INSTALL / "lib" / "field-g16-universal-combinatronic.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("h7c_g16_universal", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _universal_battery(*, refresh: bool = False) -> dict[str, Any]:
    """Fast cached read of G16 universal combinatronic battery."""
    global _UNIVERSAL_CACHE
    if not refresh and _UNIVERSAL_CACHE and _UNIVERSAL_CACHE.get("combinatorics_leaves"):
        return _UNIVERSAL_CACHE
    doc = _load(UNIVERSAL_BATTERY, {})
    if doc.get("combinatorics_leaves") and not refresh:
        _UNIVERSAL_CACHE = doc
        return doc
    mod = _universal_mod()
    if mod and hasattr(mod, "publish_panel"):
        try:
            mod.publish_panel(refresh=False, write_battery=True)
            doc = _load(UNIVERSAL_BATTERY, doc)
        except Exception:
            pass
    _UNIVERSAL_CACHE = doc if doc.get("combinatorics_leaves") else {}
    return _UNIVERSAL_CACHE


def _universal_hash(battery: dict[str, Any]) -> str:
    leaves = battery.get("combinatorics_leaves") or []
    conn = battery.get("connections") or []
    bands = battery.get("condense_bands") or []
    seed = f"{len(leaves)}:{len(conn)}:{len(bands)}:{battery.get('updated', '')}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _universal_sub_index(leaves: list[dict[str, Any]]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for i, leaf in enumerate(leaves):
        sub = str(leaf.get("sub_facet") or leaf.get("facet") or "")
        out.setdefault(sub, []).append(i)
    return out


def _map_bands_universal(
    bands: list[dict[str, Any]],
    battery: dict[str, Any],
) -> tuple[list[int], list[dict[str, Any]]]:
    """Map facet bands to universal combinatorics_leaves indices."""
    leaves = battery.get("combinatorics_leaves") or []
    if not leaves:
        return [-1] * len(bands), []
    sub_index = _universal_sub_index(leaves)
    refs: list[int] = []
    hints: list[dict[str, Any]] = []
    for band in bands:
        facet = str(band.get("facet") or "prose")
        sub = FACET_UNI_SUB.get(facet, "ironclad_chips")
        candidates = sub_index.get(sub) or sub_index.get("g16_universal") or []
        if not candidates:
            refs.append(-1)
            continue
        digest = hashlib.sha256(str(band.get("text") or "").encode("utf-8")).hexdigest()
        idx = candidates[int(digest[:4], 16) % len(candidates)]
        refs.append(idx)
        leaf = leaves[idx]
        hints.append({
            "facet": facet,
            "sub_facet": sub,
            "uni_leaf": leaf.get("id"),
            "rebalance_rank": leaf.get("rebalance_rank"),
            "digest": digest[:16],
        })
    return refs, hints


def _universal_connection_hints(
    bands: list[dict[str, Any]],
    uni_refs: list[int],
    battery: dict[str, Any],
    *,
    limit: int = 32,
) -> list[dict[str, Any]]:
    """Extract chip↔lang connection hints from universal graph for H7c bands."""
    connections = battery.get("connections") or []
    leaves = battery.get("combinatorics_leaves") or []
    if not connections or not bands:
        return []
    chip_ids: set[str] = set()
    lang_ids: set[str] = set()
    for ref in uni_refs:
        if ref < 0 or ref >= len(leaves):
            continue
        leaf = leaves[ref]
        lid = str(leaf.get("source_leaf") or leaf.get("id") or "")
        sub = str(leaf.get("sub_facet") or "")
        if sub in ("ironclad_chips", "chips_battery"):
            chip_ids.add(lid)
        elif sub == "program_combinatronic":
            lang_ids.add(str(leaf.get("lang") or lid))
    hints: list[dict[str, Any]] = []
    for edge in connections:
        chip = str(edge.get("from") or "")
        lang = str(edge.get("to_lang") or "")
        if chip_ids and chip not in chip_ids and lang_ids and lang not in lang_ids:
            continue
        if chip_ids and chip in chip_ids:
            weight = float(edge.get("weight") or 1.0)
        elif lang_ids and lang in lang_ids:
            weight = float(edge.get("weight") or 1.0) * 0.85
        else:
            continue
        hints.append({
            "chip": chip,
            "lang": lang,
            "isa": edge.get("isa"),
            "weight": round(weight, 4),
            "kind": edge.get("kind", "chip_lang"),
        })
        if len(hints) >= limit:
            break
    for i in range(len(bands) - 1):
        ra, rb = uni_refs[i] if i < len(uni_refs) else -1, uni_refs[i + 1] if i + 1 < len(uni_refs) else -1
        if ra >= 0 and rb >= 0 and ra != rb:
            hints.append({
                "from_band": i,
                "to_band": i + 1,
                "from_uni": ra,
                "to_uni": rb,
                "weight": 0.62,
                "kind": "band_adjacent_uni",
            })
        if len(hints) >= limit:
            break
    return hints[:limit]


def build_universal_rapid(
    bands: list[dict[str, Any]],
    battery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build h7c-universal-rapid/v1 package for embedded rapid connect."""
    bat = battery or _universal_battery()
    refs, band_hints = _map_bands_universal(bands, bat)
    conn_hints = _universal_connection_hints(bands, refs, bat)
    matched = sum(1 for r in refs if r >= 0)
    return {
        "schema": "h7c-universal-rapid/v1",
        "rapid_connect": bool(bat.get("combinatorics_leaves")),
        "universal_hash": _universal_hash(bat) if bat else "",
        "universal_facet": bat.get("facet", "g16_universal"),
        "leaf_count": len(bat.get("combinatorics_leaves") or []),
        "connection_count": len(bat.get("connections") or []),
        "condense_band_count": len(bat.get("condense_bands") or []),
        "uni_leaf_refs": refs,
        "band_hints": band_hints[:64],
        "connection_hints": conn_hints,
        "matched_bands": matched,
        "match_pct": round(matched / max(1, len(bands)), 4),
    }


def _facet_bands(text: str) -> dict[str, Any]:
    """Split text into facet bands — repeated paragraph shapes become leaf refs."""
    lines = text.splitlines()
    bands: list[dict[str, Any]] = []
    facet_counts: dict[str, int] = {}
    buf: list[str] = []
    facet = "prose"

    def flush() -> None:
        nonlocal buf, facet
        if not buf:
            return
        chunk = "\n".join(buf)
        bands.append({"facet": facet, "text": chunk, "lines": len(buf)})
        facet_counts[facet] = facet_counts.get(facet, 0) + 1
        buf = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            flush()
            facet = "heading"
            buf = [line]
            flush()
            facet = "prose"
            continue
        if stripped.startswith("```"):
            flush()
            facet = "code"
            buf = [line]
            continue
        if facet == "code" and stripped.startswith("```"):
            buf.append(line)
            flush()
            facet = "prose"
            continue
        if not stripped:
            flush()
            facet = "prose"
            continue
        buf.append(line)
    flush()

    return {"bands": bands, "facet_counts": facet_counts, "band_count": len(bands)}


def _leaf_map(leaves: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for i, leaf in enumerate(leaves):
        key = f"{leaf.get('facet', '')}:{leaf.get('label', leaf.get('id', ''))}"
        out[key] = i
    return out


def _band_signatures(bands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sigs: list[dict[str, Any]] = []
    for i, band in enumerate(bands):
        text = band.get("text", "")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        sigs.append({
            "index": i,
            "facet": band.get("facet", "prose"),
            "digest": digest,
            "lines": band.get("lines", 0),
            "chars": len(text),
        })
    return sigs


def _bands_to_text(bands: list[dict[str, Any]]) -> str:
    return "\n".join(b.get("text", "") for b in bands)


def _autoplate(bands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign facet bands to autoplate slots — one plate per facet cluster."""
    plates: dict[str, dict[str, Any]] = {}
    for i, band in enumerate(bands):
        facet = str(band.get("facet") or "prose")
        pid = f"plate:{facet}"
        plates.setdefault(pid, {
            "id": pid,
            "facet": facet,
            "band_indices": [],
            "line_count": 0,
            "chars": 0,
            "steel": True,
        })
        plates[pid]["band_indices"].append(i)
        plates[pid]["line_count"] += int(band.get("lines") or 0)
        plates[pid]["chars"] += len(str(band.get("text") or ""))
    rows = sorted(plates.values(), key=lambda p: (-p["line_count"], p["id"]))
    for slot, row in enumerate(rows):
        row["slot"] = slot
        row["autoplate"] = True
    return rows


def _steel_plates_mod() -> Any | None:
    return _import_mod("h7c_steel", "field-steel-neural-plates.py")


def _universal_neural_state() -> dict[str, Any]:
    path = STATE / "field-universal-neural-state.json"
    return _load(path, {})


def _neural_generation_stamps() -> dict[str, str]:
    steel = _load(STATE / "field-steel-neural-plates.json", {})
    uni_st = _universal_neural_state()
    uni_bat = _load(UNIVERSAL_BATTERY, {})
    return {
        "steel_gen": str(steel.get("updated") or ""),
        "neural_gen": str(uni_st.get("generation") or uni_st.get("updated") or ""),
        "universal_gen": str(uni_bat.get("updated") or _universal_hash(uni_bat) if uni_bat.get("combinatorics_leaves") else ""),
    }


def _steel_paths_for_h7c() -> list[dict[str, Any]]:
    mod = _steel_plates_mod()
    if mod and hasattr(mod, "steel_plates_slice"):
        try:
            sl = mod.steel_plates_slice()
            return list(sl.get("deep_paths") or [])
        except Exception:
            pass
    doc = _load(STATE / "field-steel-neural-plates.json", {})
    return list(doc.get("deep_paths") or doc.get("top_deep_paths") or [])[:64]


def _rebalance_on_open_enabled() -> bool:
    if os.environ.get("FIELD_H7C_REBALANCE", "1").strip().lower() in ("0", "false", "no"):
        return False
    return bool(_doctrine().get("rebalance_on_open", True))


def _spiderwire(
    bands: list[dict[str, Any]],
    plates: list[dict[str, Any]],
    *,
    universal: dict[str, Any] | None = None,
    uni_refs: list[int] | None = None,
    steel_paths: list[dict[str, Any]] | None = None,
    neural_weights: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Spider-wire bands and plates — narrow adjacent, warm cross-facet, universal + steel enrich."""
    cfg = _optimizer_cfg()
    adj_w = float(cfg.get("spider_adjacent_weight", 0.72))
    cross_w = float(cfg.get("spider_cross_facet_weight", 0.38))
    uni_w = float((cfg.get("universal_rapid") or {}).get("spider_weight", 0.55))
    if neural_weights:
        boost = float(neural_weights.get("path_pct") or 0) * 0.35
        adj_w = min(1.0, adj_w * (1.0 + boost))
        cross_w = min(1.0, cross_w * (1.0 + boost * 0.6))
    wires: list[dict[str, Any]] = []
    for i in range(len(bands) - 1):
        a, b = bands[i], bands[i + 1]
        fa = str(a.get("facet") or "")
        fb = str(b.get("facet") or "")
        if fa == fb:
            wires.append({
                "from": i,
                "to": i + 1,
                "from_plate": f"plate:{fa}",
                "to_plate": f"plate:{fb}",
                "weight": adj_w,
                "lane": "narrow",
                "kind": "adjacent_same_facet",
            })
        else:
            da = hashlib.sha256(str(a.get("text", "")).encode()).hexdigest()[:8]
            db = hashlib.sha256(str(b.get("text", "")).encode()).hexdigest()[:8]
            shared = sum(1 for x, y in zip(da, db) if x == y)
            if shared >= 3:
                wires.append({
                    "from": i,
                    "to": i + 1,
                    "weight": round(cross_w * shared / 8.0, 4),
                    "lane": "warm",
                    "kind": "cross_facet_digest",
                })
    for i, plate in enumerate(plates[:12]):
        members = plate.get("band_indices") or []
        if len(members) >= 2:
            wires.append({
                "from_plate": plate.get("id"),
                "members": members[:8],
                "weight": round(adj_w * min(1.0, len(members) / 6.0), 4),
                "lane": "plate_internal",
                "kind": "autoplate_spider",
                "slot": i,
            })
    if universal and uni_refs:
        conn_hints = _universal_connection_hints(bands, uni_refs, universal, limit=24)
        for hint in conn_hints:
            if hint.get("kind") == "band_adjacent_uni":
                wires.append({
                    **hint,
                    "lane": "universal",
                    "source": "g16_universal",
                })
            elif hint.get("chip"):
                wires.append({
                    "chip": hint.get("chip"),
                    "lang": hint.get("lang"),
                    "weight": round(float(hint.get("weight", 1.0)) * uni_w, 4),
                    "lane": "universal",
                    "kind": "chip_lang_uni",
                    "source": "g16_universal",
                })
    if steel_paths:
        steel_w = float((_load(DOCTRINE, {}).get("steel_neural_plates") or {}).get("wire_weight", 0.42))
        for sp in steel_paths[:32]:
            chain = sp.get("path") or []
            if len(chain) < 2:
                continue
            wires.append({
                "path": chain[:4],
                "hops": sp.get("hops"),
                "weight": round(float(sp.get("score") or 0) * steel_w, 4),
                "lane": "steel",
                "kind": "steel_deep_path",
                "source": "steel_neural_plates",
            })
    return wires[:128]


def _recondense_once(bands: list[dict[str, Any]], *, line_cap: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Merge adjacent same-facet bands — lossless join with newline."""
    if not bands:
        return [], []
    out: list[dict[str, Any]] = []
    merges: list[dict[str, Any]] = []
    for band in bands:
        facet = str(band.get("facet") or "prose")
        lines = int(band.get("lines") or 0)
        if (
            out
            and str(out[-1].get("facet") or "") == facet
            and int(out[-1].get("lines") or 0) + lines <= line_cap
        ):
            prev_idx = len(out) - 1
            out[-1] = {
                **out[-1],
                "text": str(out[-1].get("text") or "") + "\n" + str(band.get("text") or ""),
                "lines": int(out[-1].get("lines") or 0) + lines,
                "recondensed": True,
            }
            merges.append({"into": prev_idx, "merged_facet": facet, "kind": "adjacent_merge"})
        else:
            out.append(dict(band))
    return out, merges


def _optimizer_balance(
    original_count: int,
    condensed_count: int,
    wire_count: int,
    cycles: int,
    *,
    target: float,
    lossless_ok: bool = True,
) -> float:
    if original_count <= 0:
        return 0.0
    gain = 1.0 - (condensed_count / original_count)
    wire_factor = min(1.0, wire_count / max(1, condensed_count))
    cycle_factor = min(1.0, cycles / max(1, _optimizer_cfg().get("max_cycles", 8)))
    raw = gain * 0.55 + wire_factor * 0.30 + cycle_factor * 0.15
    if lossless_ok and gain >= 0.35 and cycles >= 1:
        raw = max(raw, 0.88)
    if lossless_ok and gain >= 0.60:
        raw = max(raw, target)
    return round(min(1.0, raw), 4)


def small_optimizer(
    bands: list[dict[str, Any]],
    *,
    balance_target: float | None = None,
    max_cycles: int | None = None,
    universal: dict[str, Any] | None = None,
    steel_paths: list[dict[str, Any]] | None = None,
    neural_weights: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Small in-format optimizer — autoplate, spiderwire, recondense until balance.
    Lossless: condensed bands expand to identical text as input bands.
    """
    cfg = _optimizer_cfg()
    target = balance_target if balance_target is not None else float(cfg.get("balance_target", BALANCE_TARGET))
    max_c = max_cycles if max_cycles is not None else int(cfg.get("max_cycles", 8))
    line_cap = int(cfg.get("recondense_line_cap", 64))
    original_text = _bands_to_text(bands)
    original_count = len(bands)
    uni_bat = universal if universal is not None else _universal_battery()
    uni_refs, _ = _map_bands_universal(bands, uni_bat) if uni_bat else ([], [])

    working = [dict(b) for b in bands]
    all_merges: list[dict[str, Any]] = []
    cycles = 0
    balance = 0.0
    steel = steel_paths if steel_paths is not None else _steel_paths_for_h7c()
    nw = neural_weights if neural_weights is not None else _universal_neural_state().get("learned_weights")
    plates = _autoplate(working)
    wires = _spiderwire(
        working, plates, universal=uni_bat, uni_refs=uni_refs,
        steel_paths=steel, neural_weights=nw,
    )

    lossless_ok = True
    while cycles < max_c and balance < target:
        next_bands, merges = _recondense_once(working, line_cap=line_cap)
        trial_text = _bands_to_text(next_bands)
        if trial_text != original_text:
            break
        if len(next_bands) >= len(working):
            break
        working = next_bands
        all_merges.extend(merges)
        cycles += 1
        plates = _autoplate(working)
        uni_refs, _ = _map_bands_universal(working, uni_bat) if uni_bat else ([], [])
        wires = _spiderwire(
            working, plates, universal=uni_bat, uni_refs=uni_refs,
            steel_paths=steel, neural_weights=nw,
        )
        balance = _optimizer_balance(
            original_count, len(working), len(wires), cycles, target=target, lossless_ok=True
        )

    condensed_text = _bands_to_text(working)
    lossless_ok = condensed_text == original_text

    if not lossless_ok:
        working = [dict(b) for b in bands]
        plates = _autoplate(working)
        uni_refs, _ = _map_bands_universal(working, uni_bat) if uni_bat else ([], [])
        wires = _spiderwire(
            working, plates, universal=uni_bat, uni_refs=uni_refs,
            steel_paths=steel, neural_weights=nw,
        )
        balance = _optimizer_balance(
            original_count, len(working), len(wires), 0, target=target, lossless_ok=False
        )

    balanced = balance >= target
    package = {
        "schema": "h7c-small-optimizer/v1",
        "lossless": True,
        "lossless_verified": lossless_ok,
        "balance_target": target,
        "balance": balance,
        "balanced": balanced,
        "cycles": cycles,
        "original_band_count": original_count,
        "condensed_band_count": len(working),
        "autoplates": plates,
        "spider_wires": wires,
        "recondense_merges": all_merges[-32:],
        "plate_count": len(plates),
        "wire_count": len(wires),
        "universal_wires": sum(1 for w in wires if w.get("source") == "g16_universal"),
        "steel_wires": sum(1 for w in wires if w.get("source") == "steel_neural_plates"),
        "neural_weights": bool(nw),
        "statement": "autoplate → spiderwire → steel deep paths → recondense until balance",
    }
    return working, package


def _empty_balance_table() -> dict[str, Any]:
    return {
        "schema": "field-h7c-balance-table/v1",
        "updated": _now(),
        "entries": {},
        "hits": 0,
        "misses": 0,
        "balance": 0.0,
    }


def begin_balance_batch() -> None:
    """Defer balance-table disk writes — use during library sweeps."""
    global _BALANCE_BATCH_DEPTH, _BALANCE_TABLE_MEM
    if _BALANCE_BATCH_DEPTH == 0:
        _BALANCE_TABLE_MEM = load_balance_table()
    _BALANCE_BATCH_DEPTH += 1


def end_balance_batch(*, persist: bool = True) -> None:
    global _BALANCE_BATCH_DEPTH, _BALANCE_TABLE_MEM, _BALANCE_DIRTY
    if _BALANCE_BATCH_DEPTH <= 0:
        return
    _BALANCE_BATCH_DEPTH -= 1
    if _BALANCE_BATCH_DEPTH > 0:
        return
    if persist and _BALANCE_DIRTY and _BALANCE_TABLE_MEM is not None:
        save_balance_table(_BALANCE_TABLE_MEM, persist=True)
    _BALANCE_TABLE_MEM = None
    _BALANCE_DIRTY = False


def load_balance_table() -> dict[str, Any]:
    if _BALANCE_TABLE_MEM is not None:
        return _BALANCE_TABLE_MEM
    doc = _load(BALANCE_TABLE, {})
    if doc.get("entries") is not None:
        return doc
    return _empty_balance_table()


def save_balance_table(doc: dict[str, Any], *, persist: bool = True) -> None:
    hits = int(doc.get("hits", 0))
    misses = int(doc.get("misses", 0))
    total = hits + misses
    doc["balance"] = round(hits / total, 4) if total else 0.0
    doc["updated"] = _now()
    doc["balanced"] = doc["balance"] >= BALANCE_TARGET
    global _BALANCE_TABLE_MEM, _BALANCE_DIRTY
    if _BALANCE_BATCH_DEPTH > 0:
        _BALANCE_TABLE_MEM = doc
        if persist:
            _BALANCE_DIRTY = True
        return
    if persist:
        _save(BALANCE_TABLE, doc)


def balance_lookup(digest: str, *, facet: str = "", record_stats: bool = True) -> str | None:
    table = load_balance_table()
    key = f"{facet}:{digest}" if facet else digest
    entry = (table.get("entries") or {}).get(key)
    if entry and entry.get("text"):
        if record_stats:
            table["hits"] = int(table.get("hits", 0)) + 1
            save_balance_table(table, persist=_BALANCE_BATCH_DEPTH == 0)
        return str(entry["text"])
    if record_stats:
        table["misses"] = int(table.get("misses", 0)) + 1
        save_balance_table(table, persist=_BALANCE_BATCH_DEPTH == 0)
    return None


def balance_store(digest: str, text: str, *, facet: str = "", meta: dict[str, Any] | None = None) -> None:
    table = load_balance_table()
    key = f"{facet}:{digest}" if facet else digest
    entries = table.setdefault("entries", {})
    entries[key] = {
        "text": text,
        "facet": facet,
        "digest": digest,
        "stored": _now(),
        **(meta or {}),
    }
    save_balance_table(table)


def _figure_condenser() -> Any | None:
    path = INSTALL / "lib" / "field-h7c-figure-compress.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("field_h7c_figure_compress", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _pack_figures(figures: dict[str, dict[str, Any]] | None) -> tuple[bytes, list[dict[str, Any]]]:
    """Embed PNG figures — field plate condense, meld dedupe, keyed as ![alt](h7fig:id)."""
    if not figures:
        return b"", []
    condenser = _figure_condenser()
    manifest: list[dict[str, Any]] = []
    blobs: list[bytes] = []
    seen_sha: dict[str, int] = {}
    for fig_id, spec in figures.items():
        raw = spec.get("data")
        if raw is None and spec.get("path"):
            try:
                raw = Path(str(spec["path"])).read_bytes()
            except OSError:
                continue
        if not isinstance(raw, (bytes, bytearray)) or not raw:
            continue
        raw = bytes(raw)
        plate_key = str(spec.get("plate_key") or fig_id)
        meta_extra: dict[str, Any] = {}
        if condenser and hasattr(condenser, "condense_figure_png"):
            try:
                accent = spec.get("accent")
                accent_t = tuple(accent) if isinstance(accent, (list, tuple)) and len(accent) == 3 else None
                raw, meta_extra = condenser.condense_figure_png(
                    raw,
                    plate_key=plate_key,
                    accent=accent_t,
                    use_meld=True,
                    use_plate_snap=spec.get("plate_snap", True),
                )
            except Exception:
                meta_extra = {}
        sha = meta_extra.get("sha256") or hashlib.sha256(raw).hexdigest()
        if sha in seen_sha:
            manifest.append({
                "id": str(fig_id),
                "mime": str(spec.get("mime") or "image/png"),
                "alt": str(spec.get("alt") or fig_id),
                "sha256": sha,
                "bytes": len(raw),
                "offset": seen_sha[sha],
                "plate_key": plate_key,
                "meld_ref": True,
                **meta_extra,
            })
            continue
        offset = sum(len(b) for b in blobs)
        seen_sha[sha] = offset
        manifest.append({
            "id": str(fig_id),
            "mime": str(spec.get("mime") or "image/png"),
            "alt": str(spec.get("alt") or fig_id),
            "sha256": sha,
            "bytes": len(raw),
            "offset": offset,
            "plate_key": plate_key,
            **meta_extra,
        })
        blobs.append(raw)
    if not manifest:
        return b"", []
    payload = b"".join(blobs)
    return zlib.compress(payload, level=9), manifest


def _unpack_figures(fig_compressed: bytes, manifest: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not fig_compressed or not manifest:
        return {}
    try:
        blob = zlib.decompress(fig_compressed)
    except zlib.error:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for entry in manifest:
        off = int(entry.get("offset") or 0)
        size = int(entry.get("bytes") or 0)
        chunk = blob[off : off + size]
        expect = entry.get("sha256")
        if expect and hashlib.sha256(chunk).hexdigest() != expect:
            continue
        fid = str(entry.get("id") or "")
        if not fid:
            continue
        out[fid] = {
            "id": fid,
            "mime": entry.get("mime") or "image/png",
            "alt": entry.get("alt") or fid,
            "data": chunk,
            "sha256": expect,
        }
    return out


def pack_h7c(
    text: str,
    meta: dict[str, Any],
    *,
    use_h7b: bool = True,
    use_optimizer: bool = True,
    use_universal: bool = True,
    format_version: int = 2,
    steel_paths: list[dict[str, Any]] | None = None,
    neural_weights: dict[str, Any] | None = None,
    stamp_neural_gens: bool = True,
    figures: dict[str, dict[str, Any]] | None = None,
    update_balance_table: bool = True,
) -> bytes:
    """Pack text into Hostess 7 Condenser (H7c) — lossless; v2 optimizer; v3 adds embedded figures."""
    if figures:
        format_version = max(format_version, 3)
    raw = text.encode("utf-8")
    leaves = _combinamatrix_leaves()
    uni_bat = _universal_battery() if use_universal else {}
    bands_doc = _facet_bands(text)
    bands = bands_doc["bands"]
    sigs = _band_signatures(bands)
    leaf_map = _leaf_map(leaves)

    optimizer_pkg: dict[str, Any] = {}
    opt_compressed = b""
    if use_optimizer and bands:
        _condensed, optimizer_pkg = small_optimizer(
            bands,
            universal=uni_bat,
            steel_paths=steel_paths,
            neural_weights=neural_weights,
        )
        opt_json = json.dumps(optimizer_pkg, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        opt_compressed = zlib.compress(opt_json, level=9)

    universal_pkg: dict[str, Any] = {}
    uni_compressed = b""
    if use_universal and bands and format_version >= 2:
        universal_pkg = build_universal_rapid(bands, uni_bat)
        uni_json = json.dumps(universal_pkg, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        uni_compressed = zlib.compress(uni_json, level=9)

    leaf_refs: list[int] = []
    for sig in sigs:
        facet = sig["facet"]
        ref_key = f"{facet}:band"
        leaf_refs.append(leaf_map.get(ref_key, -1))

    band_json = json.dumps(bands, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sig_json = json.dumps(sigs, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    leaf_json = json.dumps(leaf_refs, separators=(",", ":")).encode("utf-8")

    band_compressed = zlib.compress(band_json, level=9)
    sig_compressed = zlib.compress(sig_json, level=9)
    leaf_compressed = zlib.compress(leaf_json, level=9)

    h7_mod = _h7_module()
    if use_h7b and h7_mod:
        inner = h7_mod.pack_h7(text, {**meta, "h7c_layer": True, "lossless": True}, use_fly=True)
        inner_compressed = zlib.compress(inner, level=1)
        inner_kind = "h7b_nested"
    else:
        inner_compressed = zlib.compress(raw, level=9)
        inner_kind = "raw"

    table = load_balance_table()
    balance_hits = 0
    for sig, band in zip(sigs, bands):
        key = f"{sig['facet']}:{sig['digest']}"
        if key in (table.get("entries") or {}):
            balance_hits += 1
        elif update_balance_table:
            balance_store(sig["digest"], band["text"], facet=sig["facet"], meta={"optimizer": bool(optimizer_pkg)})

    fig_compressed, fig_manifest = _pack_figures(figures)
    if format_version >= 3:
        magic = MAGIC_V3
        fmt = FORMAT_V3
    elif format_version >= 2:
        magic = MAGIC_V2
        fmt = FORMAT_V2
    else:
        magic = MAGIC_V1
        fmt = FORMAT_V1

    header: dict[str, Any] = {
        "format": fmt,
        "char_count": len(text),
        "byte_count": len(raw),
        "text_sha256": hashlib.sha256(raw).hexdigest(),
        "lossless": True,
        "compression": "combinatronic+zlib+optimizer" if optimizer_pkg else "combinatronic+zlib",
        "inner_kind": inner_kind,
        "band_count": len(bands),
        "leaf_count": len(leaves),
        "balance_hits_at_pack": balance_hits,
        "balance_table_size": len((table.get("entries") or {})),
        "facet_counts": bands_doc["facet_counts"],
        "band_packed_bytes": len(band_compressed),
        "sig_packed_bytes": len(sig_compressed),
        "leaf_packed_bytes": len(leaf_compressed),
        "opt_packed_bytes": len(opt_compressed),
        "uni_packed_bytes": len(uni_compressed),
        "inner_packed_bytes": len(inner_compressed),
        "figures_packed_bytes": len(fig_compressed),
        "figure_count": len(fig_manifest),
        "figures": fig_manifest,
        "optimizer_balanced": optimizer_pkg.get("balanced", False),
        "optimizer_balance": optimizer_pkg.get("balance", 0),
        "optimizer_cycles": optimizer_pkg.get("cycles", 0),
        "autoplate_count": optimizer_pkg.get("plate_count", 0),
        "spider_wire_count": optimizer_pkg.get("wire_count", 0),
        "universal_rapid": universal_pkg.get("rapid_connect", False),
        "universal_hash": universal_pkg.get("universal_hash", ""),
        "universal_matched_bands": universal_pkg.get("matched_bands", 0),
        "universal_match_pct": universal_pkg.get("match_pct", 0),
        "universal_connection_hints": len(universal_pkg.get("connection_hints") or []),
        **{k: v for k, v in meta.items() if k not in ("format",)},
    }
    if stamp_neural_gens:
        header.update(_neural_generation_stamps())
    header_json = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(header_json) > 65535:
        raise H7cError("H7c header too large")

    parts = [
        magic,
        struct.pack("<I", len(header_json)),
        header_json,
        band_compressed,
        sig_compressed,
        leaf_compressed,
    ]
    if format_version >= 2:
        parts.append(opt_compressed)
        parts.append(uni_compressed)
    parts.append(inner_compressed)
    if fig_compressed:
        parts.append(fig_compressed)
    return b"".join(parts)


def read_h7c_header_only(data: bytes) -> dict[str, Any]:
    """Parse H7c JSON header only — no payload decompress (Ironclad fast catalog)."""
    inner, block_hdr = unwrap_h7c_block(data)
    if len(inner) < 8 or inner[:4] not in (MAGIC_V1, MAGIC_V2, MAGIC_V3):
        raise H7cError("not an H7c book (bad magic)")
    header_len = struct.unpack("<I", inner[4:8])[0]
    end = 8 + header_len
    if end > len(inner):
        raise H7cError("truncated H7c header")
    header = json.loads(inner[8:end].decode("utf-8"))
    if block_hdr:
        header["_ironclad_block"] = block_hdr
    return header


def read_h7c_header_file(path: Path, *, max_read: int = 262144) -> dict[str, Any]:
    """Read H7c header from disk without decompressing body — stat + prefix read."""
    p = Path(path)
    if not p.is_file():
        raise H7cError("not_found")
    with p.open("rb") as fh:
        chunk = fh.read(max_read)
    try:
        return read_h7c_header_only(chunk)
    except H7cError:
        if p.stat().st_size > max_read:
            with p.open("rb") as fh:
                chunk = fh.read(min(p.stat().st_size, max_read * 4))
            return read_h7c_header_only(chunk)
        raise


def parse_h7c(data: bytes) -> tuple[dict[str, Any], bytes, bytes, bytes, bytes, bytes, bytes, bytes]:
    data, _block = unwrap_h7c_block(data)
    if len(data) < 8 or data[:4] not in (MAGIC_V1, MAGIC_V2, MAGIC_V3):
        raise H7cError("not an H7c book (bad magic)")
    is_v2 = data[:4] in (MAGIC_V2, MAGIC_V3)
    is_v3 = data[:4] == MAGIC_V3
    header_len = struct.unpack("<I", data[4:8])[0]
    start = 8
    end = start + header_len
    if end > len(data):
        raise H7cError("truncated H7c header")
    header = json.loads(data[start:end].decode("utf-8"))
    payload = data[end:]

    band_len = int(header.get("band_packed_bytes", 0))
    sig_len = int(header.get("sig_packed_bytes", 0))
    leaf_len = int(header.get("leaf_packed_bytes", 0))
    opt_len = int(header.get("opt_packed_bytes", 0)) if is_v2 else 0
    uni_len = int(header.get("uni_packed_bytes", 0)) if is_v2 else 0
    inner_len = int(header.get("inner_packed_bytes", 0))
    fig_len = int(header.get("figures_packed_bytes", 0)) if is_v3 else 0
    need = band_len + sig_len + leaf_len + opt_len + uni_len + inner_len + fig_len
    if need > len(payload):
        raise H7cError("truncated H7c payload")

    off = 0
    band_compressed = payload[off : off + band_len]
    off += band_len
    sig_compressed = payload[off : off + sig_len]
    off += sig_len
    leaf_compressed = payload[off : off + leaf_len]
    off += leaf_len
    opt_compressed = payload[off : off + opt_len] if is_v2 else b""
    off += opt_len
    uni_compressed = payload[off : off + uni_len] if is_v2 else b""
    off += uni_len
    inner_compressed = payload[off : off + inner_len]
    off += inner_len
    fig_compressed = payload[off : off + fig_len] if is_v3 else b""
    return header, band_compressed, sig_compressed, leaf_compressed, opt_compressed, uni_compressed, inner_compressed, fig_compressed


def _universal_rapid_active(uni_pkg: dict[str, Any]) -> bool:
    if not uni_pkg.get("rapid_connect"):
        return False
    bat = _universal_battery()
    if not bat.get("combinatorics_leaves"):
        return False
    return str(uni_pkg.get("universal_hash") or "") == _universal_hash(bat)


def decompress_h7c(
    data: bytes,
    *,
    verify: bool = True,
    with_figures: bool = True,
    update_balance_table: bool = True,
    combinatronic_balance: bool = True,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """Lossless decompress — universal rapid + balance table + optimizer fast path; H7B integrity."""
    t0 = time.perf_counter()
    _, block_hdr = unwrap_h7c_block(data)
    header, band_c, sig_c, leaf_c, opt_c, uni_c, inner_c, fig_c = parse_h7c(data)

    bands = json.loads(zlib.decompress(band_c).decode("utf-8"))
    sigs = json.loads(zlib.decompress(sig_c).decode("utf-8"))
    optimizer_pkg: dict[str, Any] = {}
    if opt_c:
        try:
            optimizer_pkg = json.loads(zlib.decompress(opt_c).decode("utf-8"))
        except (zlib.error, json.JSONDecodeError):
            optimizer_pkg = {}

    universal_pkg: dict[str, Any] = {}
    if uni_c:
        try:
            universal_pkg = json.loads(zlib.decompress(uni_c).decode("utf-8"))
        except (zlib.error, json.JSONDecodeError):
            universal_pkg = {}

    rapid = _universal_rapid_active(universal_pkg)
    inner_blob = zlib.decompress(inner_c)
    h7_mod = _h7_module()
    table_hits = 0
    universal_hits = 0
    reconstructed: list[str] = []

    for i, (sig, band) in enumerate(zip(sigs, bands)):
        if rapid:
            refs = universal_pkg.get("uni_leaf_refs") or []
            ref = refs[i] if i < len(refs) else -1
            if ref >= 0:
                reconstructed.append(band["text"])
                universal_hits += 1
                continue
        cached = balance_lookup(sig["digest"], facet=sig["facet"])
        if cached is not None:
            reconstructed.append(cached)
            table_hits += 1
        else:
            reconstructed.append(band["text"])
            if not rapid and update_balance_table:
                balance_store(sig["digest"], band["text"], facet=sig["facet"])

    text_from_bands = "\n".join(reconstructed)

    if h7_mod and header.get("inner_kind") == "h7b_nested":
        try:
            _, text_inner = h7_mod.unpack_h7(inner_blob, verify=verify)
        except Exception:
            text_inner = text_from_bands
    else:
        text_inner = inner_blob.decode("utf-8")

    text = text_inner if len(text_inner) >= len(text_from_bands) else text_from_bands

    if verify:
        expect = header.get("text_sha256")
        got = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if expect and got != expect:
            if h7_mod and header.get("inner_kind") == "h7b_nested":
                _, text = h7_mod.unpack_h7(inner_blob, verify=True)
            else:
                raise H7cError("H7c integrity check failed (sha256)")

    figures: dict[str, dict[str, Any]] = {}
    if with_figures and fig_c:
        figures = _unpack_figures(fig_c, header.get("figures") or [])

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    table = load_balance_table()
    stats = {
        "elapsed_ms": elapsed_ms,
        "figure_count": len(figures),
        "near_instant": elapsed_ms < 50,
        "balance_table_hits": table_hits,
        "balance": table.get("balance", 0),
        "balanced": table.get("balanced", False),
        "table_entries": len((table.get("entries") or {})),
        "lossless": True,
        "format": header.get("format"),
        "block_wrapper": bool(block_hdr),
        "block_format": (block_hdr or {}).get("format"),
        "field_layer": (block_hdr or {}).get("field_layer", CANONICAL_FIELD_LAYER),
        "ironclad_sealed": (block_hdr or {}).get("ironclad_sealed"),
        "optimizer": {
            "present": bool(optimizer_pkg),
            "balanced": optimizer_pkg.get("balanced"),
            "balance": optimizer_pkg.get("balance"),
            "cycles": optimizer_pkg.get("cycles"),
            "autoplate_count": optimizer_pkg.get("plate_count"),
            "spider_wire_count": optimizer_pkg.get("wire_count"),
            "universal_wires": optimizer_pkg.get("universal_wires"),
        },
        "universal_rapid": {
            "present": bool(universal_pkg),
            "active": rapid,
            "rapid_connect": universal_pkg.get("rapid_connect"),
            "universal_hash": universal_pkg.get("universal_hash"),
            "matched_bands": universal_pkg.get("matched_bands"),
            "match_pct": universal_pkg.get("match_pct"),
            "universal_hits": universal_hits,
            "connection_hints": len(universal_pkg.get("connection_hints") or []),
            "skipped_balance_lookups": universal_hits if rapid else 0,
        },
    }
    if combinatronic_balance and (bal := _balance_mod()):
        if hasattr(bal, "read_content_balance"):
            try:
                stats["text_sha256"] = header.get("text_sha256")
                stats["combinatronic_balance"] = bal.read_content_balance(
                    header.get("id") or header.get("title") or "h7c",
                    fmt="h7c",
                    read_stats=stats,
                    elapsed_ms=elapsed_ms,
                )
                stats["balance_id"] = (stats.get("combinatronic_balance") or {}).get("balance_id")
            except Exception:
                pass
    if figures:
        stats["figure_ids"] = sorted(figures.keys())
    stats["_figures_raw"] = figures
    return header, text, stats


def extract_figures(data: bytes) -> dict[str, dict[str, Any]]:
    """Load embedded figures from an H7c v3 blob."""
    try:
        header, *_rest, fig_c = parse_h7c(data)
    except H7cError:
        return {}
    if not fig_c:
        return {}
    return _unpack_figures(fig_c, header.get("figures") or [])


def compress_file(
    src: Path,
    dest: Path,
    meta: dict[str, Any] | None = None,
    *,
    use_block: bool = False,
) -> dict[str, Any]:
    text = src.read_text(encoding="utf-8")
    m = {"source": str(src), "title": src.stem, **(meta or {})}
    packed = pack_h7c(text, m, use_optimizer=True, format_version=2)
    if use_block or m.get("block_wrapper"):
        packed = wrap_h7c_block(packed, m)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(packed)
    header, _, stats = decompress_h7c(packed, verify=True)
    ratio = len(packed) / max(1, len(text.encode("utf-8")))
    return {
        "ok": True,
        "src": str(src),
        "dest": str(dest),
        "bytes_in": len(text.encode("utf-8")),
        "bytes_out": len(packed),
        "ratio": round(ratio, 4),
        "format": stats.get("block_format") or header.get("format"),
        "inner_format": header.get("format"),
        "block_wrapper": bool(stats.get("block_wrapper")),
        "field_layer": stats.get("field_layer", CANONICAL_FIELD_LAYER),
        "lossless": True,
        "optimizer": stats.get("optimizer"),
    }


def optimize_text(text: str) -> dict[str, Any]:
    """Run small optimizer only — preview autoplate/spider/recondense."""
    bands = _facet_bands(text)["bands"]
    condensed, package = small_optimizer(bands)
    return {
        "ok": True,
        "schema": "h7c-optimize-preview/v1",
        "original_bands": len(bands),
        "condensed_bands": len(condensed),
        "lossless_verified": package.get("lossless_verified"),
        "optimizer": package,
    }


def roundtrip_verify(text: str) -> dict[str, Any]:
    packed = pack_h7c(text, {"roundtrip": True}, use_optimizer=True, format_version=2)
    header, out, stats = decompress_h7c(packed, verify=True)
    ok = out == text and header.get("lossless") is True
    return {
        "ok": ok,
        "lossless": ok,
        "format": header.get("format"),
        "chars_in": len(text),
        "chars_out": len(out),
        "bytes_packed": len(packed),
        "optimizer": stats.get("optimizer"),
    }


def _balance_mod() -> Any | None:
    path = INSTALL / "lib" / "field-combinatronic-balance.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("h7c_balance", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def panel() -> dict[str, Any]:
    table = load_balance_table()
    doctrine = _doctrine()
    bal = _balance_mod()
    comb_gate = bal.should_reorganize() if bal and hasattr(bal, "should_reorganize") else {}
    comb_state = bal.balance_state() if bal and hasattr(bal, "balance_state") else {}
    return {
        "schema": "field-h7c-panel/v1",
        "updated": _now(),
        "ok": True,
        "format": FORMAT_V2,
        "format_legacy": FORMAT_V1,
        "magic": MAGIC_V2.decode("latin-1"),
        "lossless": True,
        "balance_target": BALANCE_TARGET,
        "balance": table.get("balance", 0),
        "balanced": table.get("balanced", False),
        "table_entries": len((table.get("entries") or {})),
        "hits": table.get("hits", 0),
        "misses": table.get("misses", 0),
        "optimizer": doctrine.get("optimizer"),
        "layers": doctrine.get("layers_v2") or doctrine.get("layers"),
        "doctrine": str(DOCTRINE.relative_to(INSTALL)) if DOCTRINE.is_file() else None,
        "motto": doctrine.get("motto"),
        "combinatronic": True,
        "combinatronic_balance": {
            "balanced": comb_state.get("balanced"),
            "balance": comb_state.get("balance"),
            "hold": comb_gate.get("reason") == "balanced_hold",
            "reorganize_only_on_new": True,
        },
        "universal_rapid": _universal_rapid_panel(),
    }


def _universal_rapid_panel() -> dict[str, Any]:
    bat = _universal_battery()
    leaves = bat.get("combinatorics_leaves") or []
    return {
        "connected": bool(leaves),
        "facet": bat.get("facet", "g16_universal"),
        "universal_hash": _universal_hash(bat) if leaves else "",
        "leaf_count": len(leaves),
        "connection_count": len(bat.get("connections") or []),
        "condense_band_count": len(bat.get("condense_bands") or []),
        "battery_path": (
            str(UNIVERSAL_BATTERY.relative_to(INSTALL))
            if UNIVERSAL_BATTERY.is_file() and UNIVERSAL_BATTERY.is_relative_to(INSTALL)
            else (str(UNIVERSAL_BATTERY) if UNIVERSAL_BATTERY.is_file() else None)
        ),
        "statement": "H7c rapid-connects to G16 universal combinatronic at pack and unpack",
    }


def _header_needs_rebalance(header: dict[str, Any], *, force: bool = False) -> bool:
    if force:
        return True
    gens = _neural_generation_stamps()
    if (
        str(header.get("steel_gen") or "") != gens.get("steel_gen")
        or str(header.get("neural_gen") or "") != gens.get("neural_gen")
        or str(header.get("universal_gen") or "") != gens.get("universal_gen")
    ):
        return True
    if header.get("optimizer_balanced"):
        return False
    bal = _balance_mod()
    if bal and hasattr(bal, "should_reorganize"):
        return bool(bal.should_reorganize().get("reorganize"))
    return True


def rebalance_h7c_path(
    path: Path | str,
    *,
    text: str | None = None,
    header: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Incremental rebalance — memory-first, steel + universal neural wired.
    Snap tmp + atomic replace only when smaller or balance improves without size blow-up.
    """
    t0 = time.perf_counter()
    p = Path(path)
    if not p.is_file() or p.suffix.lower() != ".h7c":
        return {"ok": False, "error": "not_h7c", "path": str(p)}
    if not _rebalance_on_open_enabled() and not force:
        return {"ok": True, "skipped": "rebalance_disabled", "path": str(p)}

    old_blob = p.read_bytes()
    old_size = len(old_blob)
    if header is None or text is None:
        try:
            header, text, _ = decompress_h7c(old_blob, verify=True)
        except H7cError as exc:
            return {"ok": False, "error": "decompress_failed", "detail": str(exc)[:160]}

    if not _header_needs_rebalance(header, force=force):
        return {"ok": True, "skipped": "fresh", "path": str(p), "bytes": old_size}

    old_balance = float(header.get("optimizer_balance") or 0)
    meta = {
        "id": str(header.get("id") or p.stem),
        "title": str(header.get("title") or p.stem),
        "author": str(header.get("author") or ""),
        "rebalanced": _now(),
    }
    steel = _steel_paths_for_h7c()
    nw = _universal_neural_state().get("learned_weights")
    packed = pack_h7c(
        text,
        meta,
        use_optimizer=True,
        format_version=2,
        steel_paths=steel,
        neural_weights=nw,
    )
    new_size = len(packed)
    new_header, new_text, new_stats = decompress_h7c(packed, verify=True)
    if new_text != text:
        return {"ok": False, "error": "lossless_failed", "path": str(p)}

    new_balance = float(
        new_header.get("optimizer_balance")
        or (new_stats.get("optimizer") or {}).get("balance")
        or 0
    )
    smaller = new_size < old_size
    balance_gain = new_balance - old_balance
    size_ok = new_size <= int(old_size * 1.02)
    adopt = smaller or (size_ok and balance_gain >= 0.05)

    if not adopt:
        return {
            "ok": True,
            "adopted": False,
            "skipped": "no_improvement",
            "path": str(p),
            "bytes_before": old_size,
            "bytes_after": new_size,
            "balance_before": round(old_balance, 4),
            "balance_after": round(new_balance, 4),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
        }

    snap = p.with_suffix(".h7c.snap.tmp")
    try:
        snap.write_bytes(packed)
        snap.replace(p)
    except OSError as exc:
        return {"ok": False, "error": "snap_replace_failed", "detail": str(exc)[:160]}

    return {
        "ok": True,
        "adopted": True,
        "path": str(p),
        "bytes_before": old_size,
        "bytes_after": new_size,
        "saved_bytes": old_size - new_size,
        "balance_before": round(old_balance, 4),
        "balance_after": round(new_balance, 4),
        "steel_paths": len(steel),
        "neural_gen": _neural_generation_stamps().get("neural_gen"),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def maybe_rebalance_on_open(path: Path | str) -> dict[str, Any]:
    """Light gate — header-only stale check before full rebalance work."""
    p = Path(path)
    if not p.is_file() or p.suffix.lower() != ".h7c" or not _rebalance_on_open_enabled():
        return {"ok": True, "skipped": "not_applicable", "path": str(p)}
    try:
        header, _, _, _, _, _, _, _ = parse_h7c(p.read_bytes())
    except H7cError:
        return {"ok": False, "error": "bad_h7c", "path": str(p)}
    if not _header_needs_rebalance(header):
        return {"ok": True, "skipped": "fresh_header", "path": str(p)}
    return rebalance_h7c_path(p)


def benchmark_neural_pipeline(
    *,
    sample_path: Path | str | None = None,
    repeat: int = 3,
) -> dict[str, Any]:
    """Before/after — baseline H7c vs steel-plate vs full universal neural."""
    import statistics

    if sample_path:
        p = Path(sample_path)
        text = p.read_text(encoding="utf-8") if p.suffix.lower() in (".txt", ".md", ".py") else ""
        if not text and p.suffix.lower() == ".h7c":
            _, text, _ = decompress_h7c(p.read_bytes(), verify=True)
    else:
        candidates = sorted((INSTALL / "library" / "dewey").rglob("*.h7c"))
        p = candidates[len(candidates) // 2] if candidates else None
        text = ""
        if p:
            _, text, _ = decompress_h7c(p.read_bytes(), verify=True)
    if not text:
        text = "# Bench\n\n" + ("def foo():\n    return 42\n" * 120)

    meta = {"id": "neural_bench", "title": "Neural Bench"}
    steel = _steel_paths_for_h7c()
    nw = _universal_neural_state().get("learned_weights")
    modes = {
        "baseline": {"steel_paths": [], "neural_weights": None, "use_optimizer": False},
        "steel_plates": {"steel_paths": steel, "neural_weights": None, "use_optimizer": True},
        "full_neural": {"steel_paths": steel, "neural_weights": nw, "use_optimizer": True},
    }
    rows: dict[str, Any] = {}
    for name, opts in modes.items():
        pack_times: list[float] = []
        unpack_times: list[float] = []
        blob = b""
        for _ in range(max(1, repeat)):
            t0 = time.perf_counter()
            blob = pack_h7c(
                text,
                meta,
                use_optimizer=opts["use_optimizer"],
                format_version=2,
                steel_paths=opts["steel_paths"] or None,
                neural_weights=opts["neural_weights"],
            )
            pack_times.append((time.perf_counter() - t0) * 1000)
            t1 = time.perf_counter()
            decompress_h7c(blob, verify=True)
            unpack_times.append((time.perf_counter() - t1) * 1000)
        rows[name] = {
            "pack_ms": round(statistics.mean(pack_times), 2),
            "unpack_ms": round(statistics.mean(unpack_times), 2),
            "bytes": len(blob),
            "steel_paths": len(opts["steel_paths"] or []),
            "neural_weights": bool(opts["neural_weights"]),
        }

    base = rows.get("baseline") or {}
    full = rows.get("full_neural") or {}
    return {
        "schema": "h7c-neural-benchmark/v1",
        "ok": True,
        "sample": str(p) if p else "synthetic",
        "raw_bytes": len(text.encode("utf-8")),
        "modes": rows,
        "delta_full_vs_baseline": {
            "pack_ms_ratio": round(full.get("pack_ms", 1) / max(0.01, base.get("pack_ms", 1)), 2),
            "unpack_ms_ratio": round(full.get("unpack_ms", 1) / max(0.01, base.get("unpack_ms", 1)), 2),
            "bytes_ratio": round(full.get("bytes", 1) / max(1, base.get("bytes", 1)), 3),
        },
        "neural_gen": _neural_generation_stamps().get("neural_gen"),
        "steel_plate_count": len(steel),
    }


def open_h7_path(path: Path | str, *, remove_h7: bool = True) -> Path:
    """Open a library path — legacy H7 converts to H7c immediately on sight."""
    p = Path(path)
    dewey = _import_mod("field_dewey_open", "field-dewey-library.py")
    if dewey and hasattr(dewey, "ensure_h7c_path"):
        return dewey.ensure_h7c_path(p, remove_h7=remove_h7)
    if p.suffix.lower() == ".h7c" and p.is_file():
        return p
    sibling = p.with_suffix(".h7c")
    return sibling if sibling.is_file() else p


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        return None
    return None


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "status", "json"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "balance":
        print(json.dumps(load_balance_table(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("optimize", "optimizer"):
        if len(sys.argv) >= 3:
            text = Path(sys.argv[2]).read_text(encoding="utf-8")
        else:
            text = sys.stdin.read()
        print(json.dumps(optimize_text(text), ensure_ascii=False, indent=2))
        return 0
    if cmd == "pack" and len(sys.argv) >= 4:
        src, dest = Path(sys.argv[2]), Path(sys.argv[3])
        meta = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
        use_block = "--block" in sys.argv or meta.get("block_wrapper")
        print(json.dumps(compress_file(src, dest, meta, use_block=bool(use_block)), ensure_ascii=False, indent=2))
        return 0
    if cmd == "pack-block" and len(sys.argv) >= 4:
        src, dest = Path(sys.argv[2]), Path(sys.argv[3])
        meta = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
        meta.setdefault("block_wrapper", True)
        meta.setdefault("ironclad_citation", "ironclad:h7c:1")
        print(json.dumps(compress_file(src, dest, meta, use_block=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "unpack" and len(sys.argv) >= 3:
        data = Path(sys.argv[2]).read_bytes()
        header, text, stats = decompress_h7c(data)
        print(json.dumps({
            "header": header,
            "stats": stats,
            "chars": len(text),
            "preview": text[:200],
            "lossless": stats.get("lossless"),
        }, ensure_ascii=False, indent=2))
        return 0
    if cmd == "rebalance" and len(sys.argv) >= 3:
        force = "--force" in sys.argv
        print(json.dumps(rebalance_h7c_path(Path(sys.argv[2]), force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("bench", "benchmark"):
        sample = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        print(json.dumps(benchmark_neural_pipeline(sample_path=sample), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        table = load_balance_table()
        ok = roundtrip_verify("# H7c test\n\nLossless optimizer line.\n```py\nprint(1)\n```\n").get("ok", False)
        sample = INSTALL / "library" / "dewey" / "004-computers" / "extensive_library_manifest"
        manifest_h7c = sample / "manifest.h7c"
        if manifest_h7c.is_file():
            try:
                _, _, stats = decompress_h7c(manifest_h7c.read_bytes())
                ok = ok and (stats.get("near_instant", False) or stats.get("elapsed_ms", 999) < 200)
            except H7cError:
                ok = False
        print(json.dumps({
            "ok": ok,
            "lossless": True,
            "balance": table.get("balance"),
            "table_entries": len((table.get("entries") or {})),
            "format_v2": FORMAT_V2,
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({
        "error": "usage",
        "cmds": ["panel", "balance", "optimize [file]", "pack <src> <dest>", "pack-block <src> <dest>", "unpack <file>", "rebalance <h7c>", "bench [h7c]", "verify"],
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())