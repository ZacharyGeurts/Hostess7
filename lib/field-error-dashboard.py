#!/usr/bin/env pythong
"""Field error dashboard — central log + change-awareness + boot witness (loopback)."""
from __future__ import annotations

import importlib.util
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7"))
PANEL_CACHE = STATE / "field-error-dashboard-panel.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_mod(name: str, rel: str) -> Any:
    path = INSTALL / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_jsonl(path: Path, *, limit: int = 80) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return rows[-limit:]


def _boot_last() -> dict[str, Any]:
    path = STATE / "hostess7-boot-last.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _change_awareness_errors() -> list[dict[str, Any]]:
    ledger = STATE / "hostess7-change-awareness.jsonl"
    hits: list[dict[str, Any]] = []
    for row in _read_jsonl(ledger, limit=120):
        ev = str(row.get("event") or "").lower()
        msg = str(row.get("message") or "").lower()
        if ev in ("hang", "slowdown", "error", "timeout", "fail") or any(
            k in msg for k in ("hang", "timeout", "fail", "error", "stall")
        ):
            hits.append(row)
    return hits[-20:]


def _web_log_errors() -> list[str]:
    brain_state = Path(
        os.environ.get(
            "HOSTESS7_BRAIN_STATE",
            str(HOSTESS7 / "cache" / "fieldstorage" / "brain"),
        )
    )
    log = brain_state / "hostess7-web.log"
    if not log.is_file():
        log = STATE / "hostess7-web.log"
    if not log.is_file():
        return []
    try:
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    err = [
        ln.strip()
        for ln in lines
        if any(k in ln.lower() for k in ("error", "traceback", "fail", "timeout", "exception"))
    ]
    return err[-12:]


def _stack_ping() -> dict[str, Any]:
    targets = {
        "panel": "http://127.0.0.1:9477/field",
        "queen": "http://127.0.0.1:9481/api/status",
        "training": "http://127.0.0.1:9488/",
    }
    out: dict[str, Any] = {}
    for name, url in targets.items():
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                out[name] = {"up": 200 <= getattr(resp, "status", 200) < 400}
        except (urllib.error.URLError, OSError, ValueError):
            out[name] = {"up": False}
    return out


def build(*, lite: bool | None = None) -> dict[str, Any]:
    central = _load_mod("field_central_log", "lib/field-central-log.py")
    central_panel = central.panel() if central and hasattr(central, "panel") else {}
    central_tail = central.tail(limit=48) if central and hasattr(central, "tail") else []

    runtime = _load_mod("hostess7_runtime_mode", "lib/hostess7-runtime-mode.py")
    lite_doc = runtime.lite_status() if runtime and hasattr(runtime, "lite_status") else {}

    perf = _load_mod("field_perf", "lib/field-performance-flyout.py")
    perf_sample = perf.sample() if perf and hasattr(perf, "sample") else {}

    boot = _boot_last()
    failed_steps = [
        s for s in (boot.get("steps_detail") or [])
        if isinstance(s, dict) and not s.get("ok") and not s.get("skipped")
    ]

    doc = {
        "schema": "field-error-dashboard/v1",
        "ts": _now(),
        "ok": True,
        "loopback_only": True,
        "lite_mode": lite if lite is not None else bool(lite_doc.get("active")),
        "security_posture": {
            "war_profile": os.environ.get("HOSTESS7_WAR_PROFILE", "1") != "0",
            "license_mode": os.environ.get("HOSTESS7_LICENSE_MODE", "war"),
            "nexus_state": str(STATE),
        },
        "central_log": central_panel,
        "recent_events": central_tail[-24:],
        "change_awareness": _change_awareness_errors(),
        "boot_last": {
            "ok": boot.get("ok"),
            "ts": boot.get("ts"),
            "failed_steps": failed_steps,
        },
        "web_log_errors": _web_log_errors(),
        "stack": _stack_ping(),
        "performance": {
            "cpu_pct": perf_sample.get("cpu_pct"),
            "memory_used_pct": (perf_sample.get("memory") or {}).get("used_pct"),
            "thermal_headroom_pct": (perf_sample.get("thermal") or {}).get("headroom_pct"),
        },
        "counts": {
            "errors": int(central_panel.get("error_count") or 0),
            "change_awareness": len(_change_awareness_errors()),
            "boot_failures": len(failed_steps),
            "web_log": len(_web_log_errors()),
        },
    }
    try:
        PANEL_CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = PANEL_CACHE.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(PANEL_CACHE)
    except OSError:
        pass
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        try:
            print(json.dumps(build(), ensure_ascii=False, indent=2))
        except BrokenPipeError:
            return 0
        return 0
    print(json.dumps({"error": "usage: field-error-dashboard.py [json|panel]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())