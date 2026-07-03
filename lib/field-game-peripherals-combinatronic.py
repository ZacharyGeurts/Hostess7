#!/usr/bin/env pythong
"""Game peripherals combinatronic — small snap map from catalog to chips + steel plates."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
CATALOG = INSTALL / "data" / "field-game-peripherals-catalog.json"
BATTERY = STATE / "field-game-peripherals-combinatronic.json"
PANEL = STATE / "field-game-peripherals-combinatronic-panel.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fingerprint(leaves: list[dict[str, Any]]) -> str:
    blob = json.dumps([l.get("id") for l in leaves], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def build_battery() -> dict[str, Any]:
    cat = _load(CATALOG, {})
    leaves: list[dict[str, Any]] = []
    for p in cat.get("peripherals") or []:
        pid = str(p.get("id") or "")
        if not pid:
            continue
        leaves.append({
            "id": pid,
            "combinatorics_leaf": pid,
            "facet": "game_peripherals",
            "family": p.get("family"),
            "system": p.get("system"),
            "chip_id": p.get("chip_id"),
            "canonical": p.get("label"),
            "era": p.get("era"),
            "timing": p.get("timing"),
            "path_pct": 0.88 if str(p.get("status")) == "active" else 0.55,
            "sort_slot": len(leaves),
        })
    for pioneer in cat.get("pioneers") or []:
        pid = str(pioneer.get("id") or "")
        leaves.append({
            "id": pid,
            "combinatorics_leaf": pid,
            "facet": "game_peripherals",
            "family": "pioneer",
            "system": pioneer.get("system"),
            "chip_id": pioneer.get("chip_id"),
            "canonical": pioneer.get("name"),
            "era": pioneer.get("year"),
            "path_pct": 0.99,
            "sort_slot": len(leaves),
        })
    fp = _fingerprint(leaves)
    return {
        "schema": "field-game-peripherals-combinatronic/v1",
        "updated": _now(),
        "ok": len(leaves) > 0,
        "leaf_count": len(leaves),
        "combinatorics_leaves": leaves,
        "corpus_hash": fp,
        "motto": cat.get("motto"),
        "title": cat.get("title"),
    }


def snap(*, force: bool = False) -> dict[str, Any]:
    """Fast peripheral combinatronic snap — merges into live map when fingerprint matches."""
    t0 = time.perf_counter()
    bat = build_battery()
    stored = _load(BATTERY, {})
    prev = str(stored.get("corpus_hash") or "")
    cur = str(bat.get("corpus_hash") or "")
    fast = not force and prev and prev == cur and stored.get("snap_ready")

    if fast:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "ok": True,
            "schema": "field-game-peripherals-snap/v1",
            "updated": _now(),
            "snapped": True,
            "fast_path": True,
            "corpus_hash": cur,
            "leaf_count": stored.get("leaf_count"),
            "elapsed_ms": elapsed,
            "reason": "fingerprint_match",
        }

    bat["snap_ready"] = True
    bat["snapped_at"] = _now()
    _save(BATTERY, bat)
    panel = {
        "schema": "field-game-peripherals-combinatronic-panel/v1",
        "updated": _now(),
        "ok": bat.get("ok"),
        "leaf_count": bat.get("leaf_count"),
        "corpus_hash": cur,
        "top_families": _top_families(bat),
    }
    _save(PANEL, panel)

    live = _mod("pgp_live", "field-combinatronic-live-map.py")
    live_snap: dict[str, Any] = {}
    if live and hasattr(live, "snap"):
        try:
            live_snap = live.snap(allow_delta=True)
        except Exception as exc:
            live_snap = {"ok": False, "error": str(exc)[:80]}

    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "ok": True,
        "schema": "field-game-peripherals-snap/v1",
        "updated": _now(),
        "snapped": True,
        "fast_path": False,
        "corpus_hash": cur,
        "leaf_count": bat.get("leaf_count"),
        "battery": bat,
        "live_combinatronic": live_snap,
        "elapsed_ms": elapsed,
        "reason": "refreshed",
    }


def _top_families(bat: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for leaf in bat.get("combinatorics_leaves") or []:
        fam = str(leaf.get("family") or "unknown")
        out[fam] = out.get(fam, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1])[:12])


def panel() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("ok"):
        return cached
    snap()
    return _load(PANEL, {})


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "panel").strip().lower()
    if action in ("snap", "refresh"):
        return snap(force=bool(body.get("force")))
    if action in ("battery", "build"):
        return build_battery()
    if action in ("panel", "status", "json"):
        return panel()
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd == "dispatch":
        raw = sys.argv[2] if len(sys.argv) >= 3 else (sys.stdin.read() or "{}")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "snap":
        print(json.dumps(snap(force="--force" in sys.argv), ensure_ascii=False))
        return 0
    print(json.dumps(dispatch({"action": cmd}), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())