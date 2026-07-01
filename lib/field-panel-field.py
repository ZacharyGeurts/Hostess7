#!/usr/bin/env pythong
"""Field plate publish — infinite-dimension amplitude process (replaces parallel fan-out)."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
PANEL_JSON = STATE / "threat-panel.json"


def _load_parallel():
    py = INSTALL / "lib" / "field-panel-parallel.py"
    spec = importlib.util.spec_from_file_location("field_panel_parallel", py)
    if not spec or not spec.loader:
        raise RuntimeError("field-panel-parallel missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_panel() -> dict[str, Any]:
    try:
        return json.loads(PANEL_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"field": True}


def _save_panel(doc: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = PANEL_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(PANEL_JSON)


def publish_field(*, max_workers: int | None = None) -> dict[str, Any]:
    """Collect slices via field amplitude ordering — parallel workers only for I/O, field owns truth."""
    par = _load_parallel()
    fp_py = INSTALL / "lib" / "field-plate-field.py"
    spec = importlib.util.spec_from_file_location("field_plate_field", fp_py)
    if not spec or not spec.loader:
        raise RuntimeError("field-plate-field missing")
    fp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fp)

    # Reuse slice collectors; field architecture owns amplitude layer.
    result = par.publish_parallel(max_workers=max_workers)
    panel = result.get("panel") or _load_panel()
    slices = {k: v for k, v in panel.items() if not str(k).startswith("_")}
    field_doc = fp.amplitude_process(slices, failed=result.get("failed"))
    fp.write_runtime(field_doc)

    panel["field"] = True
    panel["field_load"] = True
    panel["infinite_dimension"] = True
    panel["parallel_load"] = False
    panel["single_field_depth"] = {
        "max_depth": 0,
        "soft_touch": True,
        "parallel_io_single_field_truth": True,
        "depth_fields_sealed_and_destroyed": True,
        "doctrine": "data/single-field-depth-doctrine.json",
    }
    panel["field_amplitude"] = {
        "energy": field_doc.get("field_energy"),
        "norm": field_doc.get("field_norm"),
        "peak": field_doc.get("peak_amplitude"),
        "mean": field_doc.get("mean_amplitude"),
        "dimension_count": field_doc.get("dimension_count"),
        "top": field_doc.get("top_dimensions"),
    }
    panel["field_plate"] = field_doc
    _save_panel(panel)

    return {
        "ok": True,
        "mode": "field",
        "infinite_dimension": True,
        "single_field_depth": 0,
        "depth_fields_sealed_and_destroyed": True,
        "soft_touch": True,
        "parallel_io_single_field_truth": True,
        "amplitude_process": field_doc.get("amplitude_process"),
        "updated": result.get("updated") or [],
        "failed": result.get("failed") or [],
        "slice_count": result.get("slice_count") or len(result.get("updated") or []),
        "field_energy": field_doc.get("field_energy"),
        "peak_amplitude": field_doc.get("peak_amplitude"),
        "top_dimensions": field_doc.get("top_dimensions"),
        "panel": panel,
    }


def stored_panel() -> dict[str, Any]:
    doc = _load_panel()
    keys = [
        k for k in doc
        if not str(k).startswith("_") and k not in ("field", "parallel_load", "field_load")
    ]
    return {
        "ok": True,
        "stored": True,
        "mode": "field" if doc.get("field_load") else "legacy",
        "infinite_dimension": bool(doc.get("infinite_dimension")),
        "panel": doc,
        "slice_count": len(keys),
        "field_slices_updated": keys,
        "field_slices_failed": [],
        "field_amplitude": doc.get("field_amplitude"),
    }


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("usage: field-panel-field.py [publish|json|stored]", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "publish":
        publish_field()
        return 0
    if cmd == "stored":
        print(json.dumps(stored_panel(), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(publish_field(), ensure_ascii=False))
        return 0
    print(json.dumps({"ok": False, "error": "unknown_command"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())