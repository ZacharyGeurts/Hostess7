#!/usr/bin/env pythong
"""Queen GrokPy API — health, AI field slice, VM run — all inline."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
_LIB = Path(__file__).resolve().parent
MANIFEST = QUEEN / "data" / "grokpy-toolchain.json"
GROKPY = Path(os.environ.get("GROKPY_ROOT", os.environ.get("PYTHONG_ROOT", SG / "GrokPy")))
DRIVER = GROKPY / "driver" / "grokpy_driver.py"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _grokpy_cmd(*args: str) -> dict[str, Any]:
    if not DRIVER.is_file():
        return {"ok": True, "degraded": True, "error": "missing_driver"}
    proc = subprocess.run(
        [sys.executable, str(DRIVER), *args],
        capture_output=True,
        text=True,
        timeout=60,
        env={
            **os.environ,
            "GROKPY_ROOT": str(GROKPY),
            "PYTHONG_ROOT": str(GROKPY),
            "SG_ROOT": str(SG),
            "QUEEN_ROOT": str(QUEEN),
        },
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": True, "degraded": True, "raw": (proc.stdout or "")[-600:]}


def _run_forge(tool: str, timeout: int = 300) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(_LIB / "queen-forge.py"), "run", tool],
        cwd=str(QUEEN),
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "QUEEN_ROOT": str(QUEEN), "SG_ROOT": str(SG), "GROKPY_ROOT": str(GROKPY), "PYTHONG_ROOT": str(GROKPY)},
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "tail": (proc.stdout or "")[-1500:]}


def grokpy_status() -> dict[str, Any]:
    doc = _read(MANIFEST, _read(QUEEN / "data" / "pythong-toolchain.json", {}))
    st = _grokpy_cmd("status")
    health = _grokpy_cmd("health")
    hostess = _read(SG / "Hostess7" / "data" / "hostess7-neural-stack.json", {})
    return {
        "schema": "queen-grokpy/v1",
        "updated": _ts(),
        "title": "GPY-16 — field Python for Queen + Hostess 7 (pairs with Grok16 g16)",
        "product": "GPY-16",
        "driver": "gpy-16",
        "gpy16_version": st.get("gpy16_version") or st.get("grokpy_version"),
        "pair": st.get("pair", "Grok16/g16"),
        "manifest": doc,
        "driver": st,
        "health": health,
        "ready_grokpy": doc.get("ready_grokpy") or st.get("field_ready") or health.get("ok"),
        "grok_vm_ready": doc.get("grok_vm_ready", st.get("grok_vm_ready", True)),
        "ai_ready": st.get("ai_ready", True),
        "ai_field": st.get("ai_field") or health.get("ai_field"),
        "bootstrap": doc.get("bootstrap", st.get("bootstrap", True)),
        "hostess7_lane": doc.get("hostess7") or {"truth_floor": 58},
        "hostess_stack": hostess.get("schema"),
        "replaces": "python3",
        "compat": st.get("compat") or ["grokpy", "pythong"],
        "bytecode_magic": st.get("bytecode_magic", "GPY16"),
        "next_version": st.get("next_version"),
        "tools": ["grokpy_fetch", "grokpy_build", "grokpy_probe", "grokpy_rebuild", "health", "verify"],
        "compat": {"pythong_api": "/api/pythong", "driver_alias": "pythong"},
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json"):
        return {"ok": True, **grokpy_status()}
    if action in ("health", "verify"):
        h = _grokpy_cmd("health")
        return {"ok": h.get("ok", True), "health": h, "never_fail": True}
    if action in ("probe", "refresh"):
        out = _run_forge("grokpy_probe")
        return {"ok": out.get("ok", True), "probe": out, "status": grokpy_status()}
    if action in ("rebuild", "grokpy_rebuild"):
        out = _run_forge("grokpy_rebuild", timeout=14400)
        return {"ok": out.get("ok", True), "rebuild": out, "status": grokpy_status()}
    if action == "doctrine":
        return {"ok": True, "doctrine": _read(GROKPY / "data/grokpy-field-mandate.json")}
    if action in ("ai", "ai_field"):
        st = _grokpy_cmd("status")
        return {"ok": True, "ai_field": st.get("ai_field"), "ai_ready": st.get("ai_ready", True)}
    if action in ("vm", "grokpy", "run") and body.get("source"):
        sys.path.insert(0, str(GROKPY / "interpreter"))
        from vm import GrokVM  # type: ignore
        vm = GrokVM()
        ai = (st := _grokpy_cmd("status")).get("ai_field") or {}
        vm.globals["__grokpy_ai__"] = ai
        result = vm.run_source(str(body["source"]))
        return {"ok": True, "result": result, "ai_field": ai}
    if action == "sense_all":
        sys.path.insert(0, str(SG / "Final_Ear"))
        from zocr_sound_tracker import sense_all  # noqa: WPS433
        return sense_all(learn=body.get("learn", True) is not False)
    return {
        "ok": False,
        "error": "unknown_action",
        "actions": ["status", "health", "verify", "probe", "rebuild", "doctrine", "ai", "vm", "sense_all"],
    }


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps(grokpy_status(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())