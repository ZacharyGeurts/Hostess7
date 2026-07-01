#!/usr/bin/env python3
"""Field compression progress — simple AI-readable panel for H7 / H7e / H7s pack lanes."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-compression-progress.json"
SCHEMA = "field-compression-progress/v1"
THROTTLE_SEC = float(os.environ.get("FIELD_COMPRESS_PROGRESS_SEC", "1.0"))


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def panel_path() -> Path:
    return PANEL


def read_progress() -> dict[str, Any]:
    """Return current compression job state (idle doc if none)."""
    try:
        doc = json.loads(PANEL.read_text(encoding="utf-8"))
        if isinstance(doc, dict):
            return doc
    except (OSError, json.JSONDecodeError):
        pass
    return {
        "schema": SCHEMA,
        "updated": _now(),
        "live": False,
        "ok": True,
        "job": "",
        "format": "",
        "phase": "idle",
        "pct": 0.0,
        "detail": "",
        "motto": "H7 · H7e · H7s compression — cat .nexus-state/field-compression-progress.json",
    }


def _write(doc: dict[str, Any]) -> None:
    if os.environ.get("FIELD_COMPRESS_PROGRESS", "1").strip().lower() in ("0", "false", "no"):
        return
    STATE.mkdir(parents=True, exist_ok=True)
    doc["schema"] = SCHEMA
    doc["updated"] = _now()
    tmp = PANEL.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PANEL)


class CompressionProgress:
    """Simple progress reporter — one JSON panel, throttled writes."""

    def __init__(
        self,
        *,
        job: str,
        fmt: str,
        src: str,
        dest: str = "",
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.job = job
        self.format = fmt
        self.src = src
        self.dest = dest
        self.meta = dict(meta or {})
        self.t0 = time.perf_counter()
        self._last_write = 0.0
        self._doc: dict[str, Any] = {
            "live": True,
            "ok": True,
            "job": job,
            "format": fmt,
            "src": src,
            "dest": dest,
            "phase": "init",
            "pct": 0.0,
            "detail": "starting",
            "elapsed_sec": 0,
            "meta": self.meta,
            "motto": "H7/H7e/H7s — AI poll read_progress() or python3 lib/field-compression-progress.py",
        }
        _write(self._doc)

    def phase(self, name: str, pct: float, detail: str = "", **extra: Any) -> None:
        now = time.perf_counter()
        force = name != self._doc.get("phase") or pct >= 99.9 or name in ("done", "error")
        if not force and (now - self._last_write) < THROTTLE_SEC:
            return
        self._last_write = now
        self._doc.update({
            "phase": name,
            "pct": round(max(0.0, min(100.0, pct)), 1),
            "detail": detail,
            "elapsed_sec": round(now - self.t0, 1),
            "live": name not in ("done", "error"),
            **extra,
        })
        _write(self._doc)

    def finish(self, *, ok: bool = True, result: dict[str, Any] | None = None) -> dict[str, Any]:
        out = dict(result or {})
        out["ok"] = ok
        self._doc["ok"] = ok
        self._doc["live"] = False
        self._doc["phase"] = "done" if ok else "error"
        self._doc["pct"] = 100.0 if ok else self._doc.get("pct", 0.0)
        self._doc["detail"] = "complete" if ok else out.get("error", "failed")
        self._doc["elapsed_sec"] = round(time.perf_counter() - self.t0, 1)
        if result:
            self._doc["result"] = result
        _write(self._doc)
        return out


def start(
    *,
    job: str,
    fmt: str,
    src: str,
    dest: str = "",
    meta: dict[str, Any] | None = None,
) -> CompressionProgress:
    return CompressionProgress(job=job, fmt=fmt, src=src, dest=dest, meta=meta)


def start_pack(
    *,
    job: str,
    fmt: str,
    src: str,
    dest: str = "",
    meta: dict[str, Any] | None = None,
) -> CompressionProgress | None:
    """Start progress tracking — returns None when FIELD_COMPRESS_PROGRESS=0."""
    if os.environ.get("FIELD_COMPRESS_PROGRESS", "1").strip().lower() in ("0", "false", "no"):
        return None
    return start(job=job, fmt=fmt, src=src, dest=dest, meta=meta)


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    cmd = (args[0] if args else "read").lower()
    if cmd in ("read", "status", "panel"):
        print(json.dumps(read_progress(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "path":
        print(panel_path())
        return 0
    print(json.dumps({"error": "usage", "cmds": ["read", "path"]}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())