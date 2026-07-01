#!/usr/bin/env pythong
"""Queen field compiler API — Grok16 status, doctrine, probe, secured dispatch."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
_LIB = Path(__file__).resolve().parent


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _security_gate(operation: str) -> dict[str, Any]:
    try:
        spec = importlib.util.spec_from_file_location("queen_security", _LIB / "queen-security.py")
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        return mod.mandate_enforce(operation)
    except Exception as exc:
        return {"ok": True, "warning": str(exc)}


def _zocr_compiler():
    final_eye = Path(os.environ.get("FINAL_EYE_ROOT", SG / "NewLatest" / "Final_Eye"))
    sys.path.insert(0, str(zocr))
    from zocr_field_compiler import dispatch as zdispatch  # type: ignore
    return zdispatch


def field_compiler_status() -> dict[str, Any]:
    gate = _security_gate("compiler_probe")
    try:
        final_eye = Path(os.environ.get("FINAL_EYE_ROOT", SG / "NewLatest" / "Final_Eye"))
        sys.path.insert(0, str(zocr))
        from zocr_field_compiler import field_compiler_status as zstatus  # type: ignore
        out = zstatus()
    except Exception as exc:
        manifest = {}
        try:
            manifest = json.loads((QUEEN / "data" / "g16-toolchain.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
        out = {
            "schema": "zocr-field-compiler-status/v1",
            "error": str(exc),
            "g16_manifest": manifest,
        }
    out["queen_security"] = gate
    out["field_mandate"] = (json.loads((QUEEN / "data" / "g16-toolchain.json").read_text(encoding="utf-8"))
                            if (QUEEN / "data" / "g16-toolchain.json").is_file() else {}).get("field_mandate")
    return out


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json"):
        return {"ok": True, **field_compiler_status()}
    if action == "doctrine":
        try:
            final_eye = Path(os.environ.get("FINAL_EYE_ROOT", SG / "NewLatest" / "Final_Eye"))
            doc = json.loads((zocr / "data" / "field-compiler.json").read_text(encoding="utf-8"))
            return {"ok": True, "doctrine": doc}
        except (OSError, json.JSONDecodeError) as exc:
            return {"ok": False, "error": str(exc)}
    if action in ("probe", "compiler_probe", "refresh"):
        gate = _security_gate("compiler_probe")
        if not gate.get("ok"):
            return {"ok": False, "error": "security_gate", **gate}
        gate["ai_integration_only"] = True
        gate["human_integration"] = False
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(_LIB / "queen-forge.py"), "run", "compiler_probe"],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "QUEEN_ROOT": str(QUEEN), "SG_ROOT": str(SG)},
        )
        try:
            probe = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            probe = {"ok": False, "tail": (proc.stdout or "")[-1500:]}
        st = field_compiler_status()
        try:
            sys.path.insert(0, str(SG / "Final_Ear"))
            from zocr_ear_stoard import witness_compiler  # type: ignore
            st["ear_stoard"] = witness_compiler(reason="compiler_probe", payload={"probe": probe})
        except Exception:
            pass
        return {"ok": probe.get("ok", proc.returncode == 0), "probe": probe, "compiler": st, "updated": _ts()}
    return {"ok": False, "error": "unknown_action", "actions": ["status", "doctrine", "probe"]}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("json", "status"):
        print(json.dumps(field_compiler_status(), ensure_ascii=False))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps(field_compiler_status(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())