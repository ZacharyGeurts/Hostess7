#!/usr/bin/env pythong
"""Plate test runner — complete incomplete batteries when resources are available."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent)))
from sg_paths import grok16_root

GROK16 = grok16_root()
REGISTRY = INSTALL / "data" / "field-plate-test-registry.json"
PANEL = STATE / "field-plate-test-runner.json"
LEDGER = STATE / "field-plate-test-runner-ledger.jsonl"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _resolve_script(rel: str) -> Path | None:
    for base in (SG, INSTALL.parent.parent, INSTALL):
        p = base / rel
        if p.is_file():
            return p.resolve()
    return None


def _resource_available(req: str) -> bool:
    req = req.strip().lower()
    if req == "g16":
        return (GROK16 / "bin" / "g16").is_file()
    if req == "g16-ld":
        return (GROK16 / "bin" / "g16-ld").is_file()
    if req in ("g16-as", "g16-objdump"):
        return (GROK16 / "bin" / req).is_file()
    if req == "gpy-16":
        for c in (
            SG / "GrokPy" / "bin" / "gpy-16",
            GROK16.parent / "GrokPy" / "bin" / "gpy-16",
        ):
            if c.is_file():
                return True
        return False
    if req == "ironclad":
        return (GROK16 / "forge" / "g16-ironclad.py").is_file()
    if req == "final_eye":
        for c in (INSTALL / "Final_Eye", SG / "NewLatest" / "Final_Eye"):
            if (c / "gui" / "app.py").is_file() or (c / "zocr_security.py").is_file():
                return True
        return False
    if req == "final_ear":
        ear = SG / "Final_Ear"
        return (ear / "zocr_eye_ear_fusion.py").is_file() or ear.is_dir()
    if req == "eye_ear_plate":
        return (INSTALL / "lib" / "eye-ear-plate.py").is_file()
    return False


def _resources_ready(requires: list[str]) -> tuple[bool, list[str]]:
    missing = [r for r in requires if not _resource_available(r)]
    return len(missing) == 0, missing


def _run_test(entry: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    tid = str(entry.get("id") or "")
    requires = list(entry.get("requires") or [])
    ready, missing = _resources_ready(requires)
    prev = (_load(PANEL, {}).get("tests") or {}).get(tid) or {}
    if not ready and not force:
        return {
            "id": tid,
            "status": "incomplete",
            "skipped": True,
            "missing_resources": missing,
            "plate": entry.get("plate"),
            "tier": entry.get("tier"),
            "last_run": prev.get("last_run"),
        }
    script = _resolve_script(str(entry.get("script") or ""))
    if not script:
        return {"id": tid, "status": "error", "error": "script_missing", "script": entry.get("script")}
    args = [str(a) for a in (entry.get("args") or [])]
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "SG_ROOT": str(SG),
        "GROK16_ROOT": str(GROK16),
        "G16_PREFIX": str(GROK16),
    }
    if script.suffix == ".sh":
        cmd = ["bash", str(script), *args]
    elif script.suffix == ".py":
        cmd = [sys.executable, str(script), *args]
    else:
        cmd = [str(script), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=int(entry.get("timeout") or 300), env=env)
        ok = proc.returncode == 0
        return {
            "id": tid,
            "status": "pass" if ok else "fail",
            "ok": ok,
            "exit_code": proc.returncode,
            "plate": entry.get("plate"),
            "tier": entry.get("tier"),
            "tail": (proc.stdout or proc.stderr or "")[-400:],
        }
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"id": tid, "status": "error", "ok": False, "error": str(exc)[:200]}


def run_incomplete(*, tier: str = "", meld: bool = True) -> dict[str, Any]:
    reg = _load(REGISTRY, {"tests": []})
    if os.environ.get("NEXUS_PLATE_TEST_RUN", "1") != "1":
        return {"ok": False, "error": "disabled", "schema": "field-plate-test-runner/v1"}
    tests_out: dict[str, Any] = {}
    ran = 0
    passed = 0
    incomplete = 0
    for entry in reg.get("tests") or []:
        if tier and str(entry.get("tier") or "") != tier:
            continue
        prev = (_load(PANEL, {}).get("tests") or {}).get(str(entry.get("id"))) or {}
        if prev.get("status") == "pass" and os.environ.get("NEXUS_PLATE_TEST_FORCE") != "1":
            tests_out[str(entry["id"])] = {**prev, "cached": True}
            passed += 1
            continue
        rep = _run_test(entry)
        tests_out[str(entry["id"])] = {**rep, "last_run": _now()}
        if rep.get("skipped"):
            incomplete += 1
        else:
            ran += 1
            if rep.get("ok"):
                passed += 1
    meld_doc: dict[str, Any] = {}
    if meld and ran > 0:
        for script, fn in (
            (INSTALL / "lib" / "g16-compiler-sense-plate.py", "cycle"),
            (INSTALL / "lib" / "field-plate-meld.py", "fuse"),
        ):
            if not script.is_file():
                continue
            try:
                proc = subprocess.run(
                    [sys.executable, str(script), fn if fn != "fuse" else "fuse"],
                    capture_output=True,
                    text=True,
                    timeout=90,
                    env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE), "SG_ROOT": str(SG)},
                )
                if proc.stdout.strip().startswith("{"):
                    meld_doc[script.stem] = json.loads(proc.stdout)
            except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
                pass
    doc = {
        "schema": "field-plate-test-runner/v1",
        "updated": _now(),
        "ok": incomplete == 0 and passed >= ran,
        "ran": ran,
        "passed": passed,
        "incomplete": incomplete,
        "tests": tests_out,
        "meld": meld_doc,
    }
    _save(PANEL, doc)
    _append_ledger({"ts": doc["updated"], "ran": ran, "passed": passed, "incomplete": incomplete})
    return doc


def posture() -> dict[str, Any]:
    reg = _load(REGISTRY, {"tests": []})
    panel = _load(PANEL, {})
    inventory: list[dict[str, Any]] = []
    for entry in reg.get("tests") or []:
        ready, missing = _resources_ready(list(entry.get("requires") or []))
        tid = str(entry.get("id"))
        last = (panel.get("tests") or {}).get(tid) or {}
        inventory.append({
            "id": tid,
            "plate": entry.get("plate"),
            "tier": entry.get("tier"),
            "resources_ready": ready,
            "missing": missing,
            "last_status": last.get("status") or ("incomplete" if not ready else "pending"),
        })
    return {
        "schema": "field-plate-test-runner/v1",
        "updated": _now(),
        "registry": reg.get("title"),
        "policy": reg.get("policy"),
        "inventory": inventory,
        "panel": panel,
        "api": "/api/plate-test-runner",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    tier = ""
    if "--tier" in sys.argv:
        tier = sys.argv[sys.argv.index("--tier") + 1]
    if cmd in ("json", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("run", "incomplete", "cycle"):
        print(json.dumps(run_incomplete(tier=tier), ensure_ascii=False, indent=2))
        return 0
    if cmd == "run-tier" and len(sys.argv) > 2:
        print(json.dumps(run_incomplete(tier=sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-plate-test-runner.py [json|run|run-tier TIER]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())