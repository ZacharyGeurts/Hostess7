#!/usr/bin/env python3
"""API health — probe panel routes and Python modules; always returns JSON."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
ORIGIN = os.environ.get("FIELD_PANEL_ORIGIN", "http://127.0.0.1:9477").rstrip("/")
QUEEN_ORIGIN = os.environ.get("QUEEN_PANEL_ORIGIN", "http://127.0.0.1:9481").rstrip("/")


def _load_guard() -> Any | None:
    py = INSTALL / "lib" / "field-json-guard.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_json_guard_health", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _probe_py(rel: str, args: list[str], *, timeout: int = 30) -> dict[str, Any]:
    script = INSTALL / rel
    if not script.is_file():
        return {"ok": False, "error": "missing", "path": rel}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(INSTALL),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "path": rel}
    guard = _load_guard()
    if guard and hasattr(guard, "safe_json_response"):
        doc = guard.safe_json_response(proc.stdout, proc.stderr, rc=proc.returncode, script=rel)
    else:
        text = (proc.stdout or "").strip() or "{}"
        try:
            doc = json.loads(text)
        except json.JSONDecodeError:
            doc = {"ok": False, "error": "bad_json", "detail": text[:160]}
    doc.setdefault("path", rel)
    doc.setdefault("args", args)
    return doc


def _probe_http(method: str, url: str, body: dict[str, Any] | None = None, *, timeout: int = 12) -> dict[str, Any]:
    data = None
    headers = {"User-Agent": "field-api-health/1"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            code = resp.getcode()
    except urllib.error.HTTPError as exc:
        code = exc.code
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": "unreachable", "url": url, "detail": str(exc)[:160]}
    guard = _load_guard()
    if guard and hasattr(guard, "parse_stdout_json"):
        doc = guard.parse_stdout_json(raw, default={"ok": False, "error": "empty_body"})
    else:
        try:
            doc = json.loads(raw.strip() or "{}")
        except json.JSONDecodeError:
            doc = {"ok": False, "error": "bad_json", "detail": raw[:160]}
    if not isinstance(doc, dict):
        doc = {"ok": True, "data": doc}
    doc["http_status"] = code
    doc["url"] = url
    if code in (404, 502, 503, 504):
        doc["ok"] = False
        doc.setdefault("error", f"http_{code}")
    elif code == 200 and doc.get("error") in ("empty_body", "bad_json") and raw.lstrip().startswith(("<", "<!")):
        doc["ok"] = True
        doc.pop("error", None)
        doc["content"] = "html"
    return doc


def run_health(*, live_http: bool = True) -> dict[str, Any]:
    modules: list[tuple[str, list[str], int]] = [
        ("lib/field-eol-code.py", ["panel", "--fast"], 20),
        ("lib/field-eol-code.py", ["wiring"], 15),
        ("lib/hostess7-input-training.py", ["json"], 25),
        ("lib/field-stereo-vision.py", ["json"], 20),
        ("lib/final-hands.py", ["json", "--fast"], 12),
    ]
    py_rows = [_probe_py(rel, args, timeout=to) for rel, args, to in modules]
    http_rows: list[dict[str, Any]] = []
    if live_http:
        http_rows = [
            _probe_http("GET", f"{ORIGIN}/api/field-eol-code"),
            _probe_http("POST", f"{ORIGIN}/api/field-eol-code", {"action": "panel"}),
            _probe_http("GET", f"{ORIGIN}/api/hostess7/input-training"),
            _probe_http("POST", f"{ORIGIN}/api/hostess7/input-training", {"action": "panel"}),
            _probe_http("GET", f"{ORIGIN}/eol-code"),
            _probe_http("GET", f"{ORIGIN}/queen-game-room.html"),
            _probe_http("GET", f"{QUEEN_ORIGIN}/queen-game-room.html"),
        ]
    bad_py = [r for r in py_rows if not r.get("ok")]
    bad_http = [r for r in http_rows if not r.get("ok") and r.get("error") != "unreachable"]
    down = [r for r in http_rows if r.get("error") == "unreachable"]
    return {
        "ok": not bad_py and not bad_http,
        "schema": "field-api-health/v1",
        "origin": ORIGIN,
        "queen_origin": QUEEN_ORIGIN,
        "py_modules": py_rows,
        "http_routes": http_rows,
        "summary": {
            "py_fail": len(bad_py),
            "http_fail": len(bad_http),
            "http_down": len(down),
            "json_guard": (INSTALL / "lib" / "field-json-guard.py").is_file(),
            "eol_fast": True,
        },
    }


def main() -> int:
    argv = list(sys.argv[1:])
    offline = "--offline" in argv
    argv = [a for a in argv if a != "--offline"]
    cmd = (argv[0] if argv else "json").strip().lower()
    if cmd in ("json", "panel", "health", "status"):
        print(json.dumps(run_health(live_http=not offline), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        raw = sys.argv[2] if len(sys.argv) >= 3 else (sys.stdin.read() or "{}")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        action = str(body.get("action") or "health").lower()
        if action in ("health", "panel", "status"):
            print(json.dumps(run_health(live_http=body.get("live_http", True) is not False), ensure_ascii=False))
            return 0
    print(json.dumps({"ok": False, "error": "usage", "hint": "field-api-health.py [json|health|--offline]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())