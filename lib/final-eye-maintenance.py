#!/usr/bin/env python3
"""Final Eye maintenance — lens cleaning, sensor care, calibration to keep vision active."""
from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
LEDGER = STATE / "final-eye-maintenance.jsonl"
PANEL = STATE / "final-eye-maintenance-panel.json"

TASKS: dict[str, dict[str, Any]] = {
    "lens_wipe": {
        "label": "Lens / viewport wipe",
        "interval_hours": 24,
        "visibility_boost": 0.15,
        "statement": "Remove smudge, dust, moisture — restores contrast and OCR yield.",
    },
    "sensor_clean": {
        "label": "Sensor / capture path clean",
        "interval_hours": 72,
        "visibility_boost": 0.12,
        "statement": "Verify capture backends, clear stale grabs, confirm preserve vault.",
    },
    "calibration_check": {
        "label": "Stereo / rig calibration",
        "interval_hours": 168,
        "visibility_boost": 0.1,
        "statement": "Re-check eye rig offsets, disparity baseline, comfort preset.",
    },
    "vault_verify": {
        "label": "Preserve vault verify",
        "interval_hours": 48,
        "visibility_boost": 0.08,
        "statement": "Confirm last-good frame chain — vision never presumed lost.",
    },
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _append_ledger(row: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _last_per_task() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not LEDGER.is_file():
        return out
    try:
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            tid = str(row.get("task_id") or "")
            if tid:
                out[tid] = row
    except (OSError, json.JSONDecodeError):
        pass
    return out


def _hours_since(ts: str) -> float:
    try:
        from datetime import datetime, timezone
        t = datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - t).total_seconds() / 3600.0
    except (ValueError, TypeError):
        return 9999.0


def record_task(task_id: str, *, note: str = "", operator: str = "operator") -> dict[str, Any]:
    tid = str(task_id or "").strip().lower().replace("-", "_")
    if tid not in TASKS:
        return {"ok": False, "error": "unknown_task", "task_id": tid, "known": list(TASKS)}
    row = {
        "schema": "final-eye-maintenance/v1",
        "ok": True,
        "task_id": tid,
        "label": TASKS[tid]["label"],
        "ts": _now(),
        "operator": operator,
        "note": note[:500],
        "visibility_boost": TASKS[tid]["visibility_boost"],
    }
    _append_ledger(row)
    return row


def maintenance_posture(*, live_visibility: float | None = None) -> dict[str, Any]:
    """Due tasks, visibility penalty, and counsel for keeping vision active."""
    last = _last_per_task()
    due: list[dict[str, Any]] = []
    penalty = 0.0
    for tid, spec in TASKS.items():
        prev = last.get(tid)
        hours = _hours_since(prev["ts"]) if prev else 9999.0
        interval = float(spec["interval_hours"])
        overdue = hours >= interval
        if overdue:
            due.append({
                "task_id": tid,
                "label": spec["label"],
                "hours_since": round(hours, 1),
                "interval_hours": interval,
                "statement": spec["statement"],
            })
            penalty += min(0.25, (hours - interval) / interval * 0.08)
    penalty = min(0.4, penalty)
    base_vis = 1.0 if live_visibility is None else max(0.0, min(1.0, float(live_visibility)))
    effective = max(0.0, base_vis - penalty)
    return {
        "schema": "final-eye-maintenance-posture/v1",
        "ok": True,
        "ts": _now(),
        "tasks": {k: {**v, "last": last.get(k)} for k, v in TASKS.items()},
        "due": due,
        "due_count": len(due),
        "visibility_penalty": round(penalty, 3),
        "live_visibility": round(base_vis, 3) if live_visibility is not None else None,
        "effective_visibility": round(effective, 3),
        "vision_active": effective >= 0.35 and len(due) < 3,
        "counsel": (
            "Wipe lens daily; clean capture path every 72h; verify preserve vault. "
            "Vision stays active when maintenance is current — never presume blindness."
        ),
    }


def probe_eye_visibility() -> dict[str, Any]:
    """Estimate live eye visibility from preserve + neural when reachable."""
    vis = 0.85
    sources: list[str] = ["default_assume_active"]
    try:
        import urllib.request
        port = int(os.environ.get("FINAL_EYE_PORT", os.environ.get("ZOCR_PORT", "9479")))
        host = os.environ.get("FINAL_EYE_HOST", "127.0.0.1")
        req = urllib.request.Request(f"http://{host}:{port}/api/preserve/status", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            doc = json.loads(resp.read().decode("utf-8", errors="replace"))
        conf = float(doc.get("vision_confidence") or 1.0)
        vis = conf
        sources = ["preserve_status"]
        if doc.get("last_good"):
            vis = max(vis, 0.7)
            sources.append("last_good_present")
    except Exception:
        pass
    posture = maintenance_posture(live_visibility=vis)
    return {
        "schema": "final-eye-visibility/v1",
        "visibility": posture["effective_visibility"],
        "live_visibility": vis,
        "sources": sources,
        "maintenance": posture,
    }


def panel_json() -> dict[str, Any]:
    probe = probe_eye_visibility()
    doc = {
        "schema": "final-eye-maintenance-panel/v1",
        "ok": True,
        "ledger": str(LEDGER),
        "probe": probe,
        "posture": probe.get("maintenance") or maintenance_posture(),
        "updated": _now(),
    }
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = PANEL.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PANEL)
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("status", "json", "panel"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "record" and len(sys.argv) >= 3:
        print(json.dumps(record_task(sys.argv[2], note=" ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""), ensure_ascii=False, indent=2))
        return 0
    if cmd == "visibility":
        print(json.dumps(probe_eye_visibility(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: final-eye-maintenance.py [status|record TASK [note]|visibility]"}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())