#!/usr/bin/env pythong
"""Central field log — append-only loopback error/event ledger (no telemetry egress)."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
LOG = STATE / "hostess7-central-errors.jsonl"
PANEL = STATE / "hostess7-central-log-panel.json"
MAX_TAIL = 200


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def append(
    *,
    level: str,
    source: str,
    message: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "schema": "hostess7-central-log/v1",
        "ts": _now(),
        "level": (level or "info").lower()[:12],
        "source": (source or "field")[:80],
        "message": (message or "")[:1200],
        "meta": meta or {},
        "loopback_only": True,
    }
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    _refresh_panel()
    return {"ok": True, "row": row}


def tail(*, limit: int = MAX_TAIL) -> list[dict[str, Any]]:
    if not LOG.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in LOG.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return rows[-max(1, min(limit, MAX_TAIL)) :]


def _refresh_panel() -> None:
    recent = tail(limit=MAX_TAIL)
    errors = [r for r in recent if r.get("level") in ("error", "warn", "timeout", "fail")]
    doc = {
        "schema": "hostess7-central-log-panel/v1",
        "ts": _now(),
        "ok": True,
        "count": len(recent),
        "error_count": len(errors),
        "recent_errors": errors[-24:],
        "loopback_only": True,
    }
    try:
        PANEL.parent.mkdir(parents=True, exist_ok=True)
        tmp = PANEL.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(PANEL)
    except OSError:
        pass


def panel() -> dict[str, Any]:
    if PANEL.is_file():
        try:
            return json.loads(PANEL.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    _refresh_panel()
    if PANEL.is_file():
        try:
            return json.loads(PANEL.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"schema": "hostess7-central-log-panel/v1", "ok": True, "count": 0, "error_count": 0}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "tail":
        lim = int(sys.argv[2]) if len(sys.argv) > 2 else MAX_TAIL
        print(json.dumps({"ok": True, "rows": tail(limit=lim)}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "append":
        level = sys.argv[2] if len(sys.argv) > 2 else "info"
        source = sys.argv[3] if len(sys.argv) > 3 else "cli"
        message = sys.argv[4] if len(sys.argv) > 4 else ""
        print(json.dumps(append(level=level, source=source, message=message), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-central-log.py [panel|tail|append LEVEL SOURCE MSG]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())