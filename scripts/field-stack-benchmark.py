#!/usr/bin/env python3
"""Field stack benchmark — API latency, transfer rates, AmmoNet pipe, secure git posture."""
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
PANEL = os.environ.get("FIELD_PANEL_ORIGIN", "http://127.0.0.1:9477")
OUT = STATE / "field-stack-benchmark.json"


def _fetch(url: str, *, method: str = "GET", body: dict | None = None, timeout: float = 30.0) -> dict[str, Any]:
    t0 = time.perf_counter()
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            rate_mbps = (len(raw) * 8 / 1_000_000) / max(elapsed_ms / 1000, 0.001)
            try:
                parsed = json.loads(raw.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                parsed = {"_raw_bytes": len(raw)}
            return {
                "ok": True,
                "status": resp.status,
                "latency_ms": elapsed_ms,
                "bytes": len(raw),
                "mbps": round(rate_mbps, 3),
                "sample": parsed if isinstance(parsed, dict) else {"type": type(parsed).__name__},
            }
    except urllib.error.HTTPError as exc:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return {"ok": False, "status": exc.code, "latency_ms": elapsed_ms, "error": str(exc)[:120]}
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return {"ok": False, "latency_ms": elapsed_ms, "error": str(exc)[:120]}


def _py_json(script: str, args: list[str], timeout: int = 45) -> dict[str, Any]:
    path = INSTALL / script
    if not path.is_file():
        return {"ok": False, "error": "missing", "script": script}
    t0 = time.perf_counter()
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    try:
        proc = subprocess.run(
            [sys.executable, str(path), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(INSTALL),
        )
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        out = proc.stdout or ""
        try:
            doc = json.loads(out or "{}")
        except json.JSONDecodeError:
            doc = {"ok": False, "error": "bad_json", "stderr": (proc.stderr or "")[:200]}
        doc["_bench_ms"] = elapsed_ms
        doc["_bench_bytes"] = len(out.encode("utf-8"))
        return doc
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "_bench_ms": int((time.perf_counter() - t0) * 1000)}


def run() -> dict[str, Any]:
    endpoints = [
        ("panel_status", f"{PANEL}/api/status"),
        ("gnu_terminal", f"{PANEL}/api/field-gnu-terminal"),
        ("underlay_html", f"{PANEL}/underlay-f9"),
        ("terminal_embed", f"{PANEL}/field-gnu-terminal-embed.html"),
        ("ammonet", f"{PANEL}/api/ammonet"),
        ("github_secure", f"{PANEL}/api/github-secure"),
        ("os_keybindings", f"{PANEL}/api/field-os-keybindings"),
        ("ironclad_immediate", f"{PANEL}/api/ironclad/immediate"),
    ]
    http: dict[str, Any] = {}
    for name, url in endpoints:
        http[name] = _fetch(url)

    truth = _fetch(
        f"{PANEL}/api/field-gnu-terminal",
        method="POST",
        body={"action": "run", "command": "truth diagnostic panel"},
        timeout=45.0,
    )

    modules = {
        "truth_cli": _py_json("lib/field-ironclad-truth.py", ["json"], timeout=12),
        "gnu_terminal_cli": _py_json("lib/field-gnu-terminal.py", ["json"], timeout=20),
        "github_secure_cli": _py_json("lib/field-github-secure.py", ["json"], timeout=30),
        "ammonet_panel": _py_json("lib/ammonet-field.py", ["panel"], timeout=90),
        "os_keybindings": _py_json("lib/field-os-keybindings.py", ["panel"], timeout=10),
    }

    ammonet = modules.get("ammonet_panel") or {}
    pipe = ((ammonet.get("isp") or {}).get("pipe_percent")) or ((ammonet.get("metrics") or {}).get("pipe_percent"))
    qemu = ammonet.get("qemu_transfer") or {}

    summary = {
        "http_ok": sum(1 for v in http.values() if v.get("ok")),
        "http_total": len(http),
        "avg_latency_ms": round(
            sum(v.get("latency_ms", 0) for v in http.values() if v.get("latency_ms")) / max(len(http), 1),
            1,
        ),
        "max_mbps": max((v.get("mbps") or 0) for v in http.values()),
        "ammonet_pipe_percent": pipe,
        "qemu_transfer_mbps": qemu.get("mbps") or qemu.get("rate_mbps"),
        "truth_post_ok": truth.get("ok"),
        "truth_latency_ms": truth.get("latency_ms"),
    }

    doc = {
        "ok": True,
        "schema": "field-stack-benchmark/v1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "panel_origin": PANEL,
        "summary": summary,
        "http": http,
        "truth_post": truth,
        "modules": modules,
        "fkeys": {
            "doctrine": str(INSTALL / "data/field-os-keybindings-doctrine.json"),
            "screen_layers": str(INSTALL / "data/field-screen-layer-doctrine.json"),
            "bindings": ["F9", "F10", "F11", "F12"],
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    doc = run()
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())