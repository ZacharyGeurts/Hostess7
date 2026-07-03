#!/usr/bin/env pythong
"""Hostess7 runtime modes — profile (perf witness) and lite (opt-in throttle, security unchanged)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7"))
LITE_DOCTRINE = INSTALL / "data" / "hostess7-lite-mode-doctrine.json"
LITE_STATE = STATE / "hostess7-lite-mode.json"
PROFILE_STATE = STATE / "hostess7-profile-last.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _central_log(level: str, source: str, message: str, **meta: Any) -> None:
    log_py = INSTALL / "lib" / "field-central-log.py"
    if not log_py.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(log_py), "append", level, source, message],
            cwd=str(INSTALL),
            capture_output=True,
            timeout=8,
            check=False,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def lite_doctrine() -> dict[str, Any]:
    return _load(LITE_DOCTRINE, {"schema": "hostess7-lite-mode/v1", "reduced": {}})


def lite_status() -> dict[str, Any]:
    doc = _load(LITE_STATE, {})
    if doc:
        return doc
    active = os.environ.get("HOSTESS7_LITE", "0") == "1"
    return {
        "schema": "hostess7-lite-mode/v1",
        "active": active,
        "source": "env" if active else "default",
        "security_unchanged": lite_doctrine().get("security_unchanged", []),
    }


def lite_apply(*, on: bool = True) -> dict[str, Any]:
    doctrine = lite_doctrine()
    reduced = dict(doctrine.get("reduced") or {})
    doc = {
        "schema": "hostess7-lite-mode/v1",
        "active": bool(on),
        "ts": _now(),
        "opt_in": True,
        "security_unchanged": doctrine.get("security_unchanged", []),
        "env": reduced if on else {},
        "notes": doctrine.get("notes", ""),
    }
    _save(LITE_STATE, doc)
    _central_log("info" if on else "warn", "hostess7-lite", f"lite_mode={'on' if on else 'off'}")
    return {"ok": True, **doc}


def lite_env_exports() -> dict[str, str]:
    st = lite_status()
    if not st.get("active"):
        return {"HOSTESS7_LITE": "0"}
    out = {"HOSTESS7_LITE": "1"}
    for k, v in (st.get("env") or lite_doctrine().get("reduced") or {}).items():
        out[str(k)] = str(v)
    out.setdefault("HOSTESS7_WAR_PROFILE", "1")
    out.setdefault("HOSTESS7_LICENSE_MODE", "war")
    return out


def _ping(url: str, *, timeout: float = 3.0) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
            return {
                "url": url,
                "up": 200 <= getattr(resp, "status", 200) < 400,
                "elapsed_ms": elapsed_ms,
            }
    except (urllib.error.URLError, OSError, ValueError) as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"url": url, "up": False, "elapsed_ms": elapsed_ms, "error": str(exc)[:200]}


def _perf_sample() -> dict[str, Any]:
    perf_py = INSTALL / "lib" / "field-performance-flyout.py"
    if not perf_py.is_file():
        return {"ok": False, "error": "perf_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(perf_py), "json"],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return {"ok": False, "error": "perf_sample_failed"}


def profile_run(*, ports: bool = True) -> dict[str, Any]:
    port = int(os.environ.get("HOSTESS7_WEB_PORT", os.environ.get("PORT", "8080")))
    targets = {
        "ammo_field": "http://127.0.0.1:9477/field",
        "ammo_api": "http://127.0.0.1:9477/api/field-performance-flyout",
        "queen": "http://127.0.0.1:9481/api/status",
        "queen_perf": "http://127.0.0.1:9481/api/field-performance-flyout",
        "hostess7_web": f"http://127.0.0.1:{port}/api/status",
        "training": "http://127.0.0.1:9488/",
    }
    pings: dict[str, Any] = {}
    if ports:
        for name, url in targets.items():
            pings[name] = _ping(url)

    perf = _perf_sample()
    err_py = INSTALL / "lib" / "field-error-dashboard.py"
    errors: dict[str, Any] = {}
    if err_py.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(err_py), "json"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            if proc.stdout.strip():
                errors = json.loads(proc.stdout)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            errors = {"ok": False}

    doc = {
        "schema": "hostess7-profile/v1",
        "ts": _now(),
        "ok": True,
        "lite_mode": lite_status().get("active", False),
        "pings": pings,
        "performance": perf,
        "error_dashboard": {
            "error_count": (errors.get("counts") or {}).get("errors", 0),
            "boot_ok": (errors.get("boot_last") or {}).get("ok"),
            "stack": errors.get("stack"),
        },
        "recommendations": _profile_hints(pings, perf, errors),
        "loopback_only": True,
    }
    _save(PROFILE_STATE, doc)
    _central_log("info", "hostess7-profile", "profile_run_complete", pings_up=sum(1 for p in pings.values() if p.get("up")))
    return doc


def _profile_hints(pings: dict[str, Any], perf: dict[str, Any], errors: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    slow = [k for k, v in pings.items() if v.get("up") and (v.get("elapsed_ms") or 0) > 800]
    if slow:
        hints.append(f"Slow surfaces (>800ms): {', '.join(slow)} — consider ./Hostess7.sh lite")
    down = [k for k, v in pings.items() if not v.get("up")]
    if down:
        hints.append(f"Down endpoints: {', '.join(down)} — run ./Hostess7.sh boot")
    cpu = float(perf.get("cpu_pct") or 0)
    if cpu > 75:
        hints.append(f"CPU {cpu}% — enable lite mode or check monster monitor")
    ec = int((errors.get("counts") or {}).get("errors") or 0)
    if ec > 0:
        hints.append(f"{ec} central log errors — open /api/field-error-dashboard")
    if not hints:
        hints.append("Stack healthy — perf flyout available on :9477 and :9481")
    return hints


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print("Usage: hostess7-runtime-mode.py lite [on|off|status] | profile [json]")
        return 0

    cmd = args[0].strip().lower()
    if cmd == "lite":
        sub = (args[1] if len(args) > 1 else "status").strip().lower()
        if sub in ("on", "enable", "1", "true"):
            print(json.dumps(lite_apply(on=True), ensure_ascii=False, indent=2))
            return 0
        if sub in ("off", "disable", "0", "false"):
            print(json.dumps(lite_apply(on=False), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(lite_status(), ensure_ascii=False, indent=2))
        return 0

    if cmd == "profile":
        doc = profile_run()
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1

    print(json.dumps({"error": f"unknown command: {cmd}"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())