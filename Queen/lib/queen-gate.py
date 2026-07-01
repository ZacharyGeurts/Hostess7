#!/usr/bin/env pythong
"""Queen Gate — single egress + panel path for browser and world APIs."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _field_net_mod() -> Any | None:
    path = QUEEN / "lib" / "queen-field-net.py"
    if not path.is_file():
        return None
    return _load_module("queen_field_net", path)


def _panel_script() -> Path:
    for p in (
        QUEEN / "lib" / "field-queen-browser.py",
        SG / "NewLatest" / "lib" / "field-queen-browser.py",
        QUEEN.parent / "lib" / "field-queen-browser.py",
    ):
        if p.is_file():
            return p
    return SG / "NewLatest" / "lib" / "field-queen-browser.py"


def panel_json(timeout: int = 30) -> dict[str, Any]:
    script = _panel_script()
    if not script.is_file():
        return {"error": "field-queen-browser missing", "path": str(script)}
    proc = subprocess.run(
        [sys.executable, str(script), "json"],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(QUEEN),
        env={
            **os.environ,
            "NEXUS_INSTALL_ROOT": os.environ.get("NEXUS_INSTALL_ROOT", str(QUEEN)),
            "QUEEN_ROOT": str(QUEEN),
            "NEXUS_STATE_DIR": str(STATE),
        },
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "tail": (proc.stdout or "")[-1500:] + (proc.stderr or "")[-1500:]}


def classify_egress(url: str) -> dict[str, Any]:
    mod = _field_net_mod()
    if mod is None:
        return {"verdict": "ALLOW_LEGACY", "internal": True}
    return mod.classify_url(url)


def field_net_json() -> dict[str, Any]:
    mod = _field_net_mod()
    if mod is None:
        return {}
    return mod.field_net_status()


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _benchmark_mod() -> Any | None:
    path = QUEEN / "lib" / "queen-benchmark.py"
    if not path.is_file():
        return None
    try:
        return _load_module("queen_benchmark_gate", path)
    except Exception:
        return None


def _jump_slice(url: str) -> dict[str, Any]:
    script = QUEEN / "lib" / "queen-nexus-jump.py"
    if not script.is_file():
        return {}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "jump", url],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(QUEEN),
            env={**os.environ, "QUEEN_ROOT": str(QUEEN), "NEXUS_INSTALL_ROOT": os.environ.get("NEXUS_INSTALL_ROOT", str(QUEEN.parent))},
        )
        return json.loads(proc.stdout or "{}")
    except Exception:
        return {}


def gate_nav(url: str) -> dict[str, Any]:
    bench = _benchmark_mod()
    if bench is not None and hasattr(bench, "fast_gate_nav"):
        fast = bench.fast_gate_nav(url)
        if fast:
            return fast

    jump = _jump_slice(url)
    if jump and jump.get("permit") is False:
        return {
            "url": url,
            "host": _host(url),
            "queen_verdict": "NEXUS_JUMP_BLOCKED",
            "permit": False,
            "iff": jump.get("iff") or "HOSTILE",
            "reason": jump.get("reason") or jump.get("verdict"),
            "nexus_jump": jump,
        }
    egress = classify_egress(url)
    if egress.get("verdict") == "BLOCK_EXTERNAL":
        return {
            "url": url,
            "host": _host(url),
            "queen_verdict": "EXTERNAL_BLOCKED",
            "permit": False,
            "iff": egress.get("iff", "HOSTILE"),
            "reason": egress.get("reason"),
            "hint": egress.get("hint"),
        }
    if egress.get("resolved"):
        url = egress["resolved"]
    host = _host(url)
    panel = panel_json()
    gates = panel.get("gates") or {}
    sovereign = panel.get("sovereign") or {}
    awareness = panel.get("browser_awareness") or {}
    active = awareness.get("active_sites") or awareness.get("sites") or []
    honor = next((row for row in active if (row.get("host") or "").lower() == host), None)
    verdict = panel.get("queen_verdict") or "UNKNOWN"
    held = gates.get("all_held", False)
    return {
        "url": url,
        "host": host,
        "queen_verdict": verdict,
        "gates_all_held": held,
        "gates_held": gates.get("held"),
        "gates_total": gates.get("total"),
        "sovereign": sovereign.get("sovereign", True),
        "honor": honor,
        "permit": verdict in ("QUEEN_READY", "QUEEN_OFF") or held,
        "receipt": f"nav:{host or 'local'}@{_now()}",
        "egress": egress,
        "nexus_jump": {
            "verdict": jump.get("verdict"),
            "iff": jump.get("iff"),
            "permit": jump.get("permit", True),
            "countermeasures_ready": jump.get("countermeasures_ready"),
        } if jump else {},
    }


def gate_file(path: str, *, direction: str = "ingress") -> dict[str, Any]:
    script = QUEEN / "lib" / "queen-field-virus.py"
    if not script.is_file():
        return {"ok": True, "skipped": True, "reason": "field_virus_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "gate", path, direction],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(QUEEN),
            env={**os.environ, "QUEEN_ROOT": str(QUEEN), "NEXUS_STATE_DIR": str(STATE)},
        )
        return json.loads(proc.stdout or "{}")
    except Exception as exc:
        return {"ok": False, "error": str(exc), "lane": "FieldVirus"}


def gates_slice() -> dict[str, Any]:
    panel = panel_json()
    return {
        "queen_verdict": panel.get("queen_verdict"),
        "gates": panel.get("gates") or {},
        "sovereign": panel.get("sovereign") or {},
        "posture": panel.get("posture") or {},
        "motto": panel.get("motto"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(gates_slice(), ensure_ascii=False))
        return 0
    if cmd == "classify" and len(sys.argv) > 2:
        print(json.dumps(classify_egress(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd == "gate" and len(sys.argv) > 2:
        print(json.dumps(gate_nav(sys.argv[2]), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-gate.py [json|classify <url>|gate <url>]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())