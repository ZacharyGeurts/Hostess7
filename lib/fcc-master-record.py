#!/usr/bin/env pythong
"""FCC master record — append every lookup; deduplicated table for Signals panel."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
MASTER_JSONL = STATE / "fcc-master-record.jsonl"
MASTER_TABLE = STATE / "fcc-master-table.json"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _record_key(row: dict[str, Any]) -> str:
    parts = [
        str(row.get("kind") or ""),
        str(row.get("fcc_id") or ""),
        str(row.get("label") or ""),
        str(row.get("freq_mhz") or ""),
        str(row.get("freq_khz") or ""),
        str(row.get("band") or ""),
        str(row.get("ssid") or ""),
        str(row.get("bssid") or ""),
        str(row.get("ip") or ""),
        str(row.get("call_sign") or ""),
    ]
    return "|".join(parts)


def record_lookup(row: dict[str, Any], *, source: str = "lookup") -> dict[str, Any]:
    """Append one FCC lookup to the master jsonl and refresh deduplicated table."""
    entry = {
        "recorded_at": _now(),
        "source": source,
        **_row_fields(row),
    }
    STATE.mkdir(parents=True, exist_ok=True)
    with MASTER_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _row_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": row.get("kind"),
        "label": row.get("label"),
        "fcc_id": row.get("fcc_id"),
        "fcc_label": row.get("fcc_label"),
        "fcc_rule": row.get("fcc_rule"),
        "fcc_band_id": row.get("fcc_band_id"),
        "permitted": row.get("permitted"),
        "authority": row.get("authority"),
        "service": row.get("service"),
        "threat_tag": row.get("threat_tag"),
        "level": row.get("level"),
        "identified_by": row.get("identified_by"),
        "freq_mhz": row.get("freq_mhz"),
        "freq_khz": row.get("freq_khz"),
        "band": row.get("band"),
        "channel": row.get("channel"),
        "ssid": row.get("ssid"),
        "bssid": row.get("bssid"),
        "ip": row.get("ip"),
        "call_sign": row.get("call_sign"),
        "stream_url": row.get("stream_url"),
    }


def build_master_table(*, max_lines: int = 50000) -> dict[str, Any]:
    """Rebuild deduplicated master table from jsonl (newest wins per key)."""
    rows_by_key: dict[str, dict[str, Any]] = {}
    line_count = 0
    if MASTER_JSONL.is_file():
        try:
            lines = MASTER_JSONL.read_text(encoding="utf-8").splitlines()
            line_count = len(lines)
            for line in lines[-max_lines:]:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = _record_key(row)
                rows_by_key[key] = row
        except OSError:
            pass

    rows = sorted(
        rows_by_key.values(),
        key=lambda r: (str(r.get("recorded_at") or ""), str(r.get("label") or "")),
        reverse=True,
    )
    threats = [r for r in rows if (r.get("level") or "none") not in ("none", "")]
    permitted = [r for r in rows if r.get("permitted")]
    doc = {
        "schema": "fcc-master-table/v1",
        "updated": _now(),
        "authority": "FCC 47 CFR · complete lookup record",
        "motto": "Every FCC identification tabled and stored — full master record.",
        "jsonl_path": str(MASTER_JSONL),
        "records": rows,
        "identified": rows,
        "threats": threats,
        "permitted": permitted,
        "stats": {
            "total": len(rows),
            "jsonl_lines": line_count,
            "permitted": len(permitted),
            "threats": len(threats),
            "critical": sum(1 for r in threats if r.get("level") == "critical"),
        },
    }
    _save_json(MASTER_TABLE, doc)
    return doc


def ingest_batch(rows: list[dict[str, Any]], *, source: str = "batch") -> int:
    count = 0
    for row in rows:
        record_lookup(row, source=source)
        count += 1
    return count


def panel_json() -> dict[str, Any]:
    cached = _load_json(MASTER_TABLE, {})
    if cached.get("schema") == "fcc-master-table/v1" and cached.get("updated"):
        return cached
    return build_master_table()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_master_table(), ensure_ascii=False))
        return 0
    if cmd == "record" and len(sys.argv) > 2:
        row = json.loads(sys.argv[2])
        out = record_lookup(row, source=str(sys.argv[3] if len(sys.argv) > 3 else "cli"))
        print(json.dumps(out, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: fcc-master-record.py [json|build|record JSON]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())