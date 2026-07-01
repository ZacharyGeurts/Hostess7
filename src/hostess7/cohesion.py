#!/usr/bin/env pythong
"""Cohesion tests — benchmark IQ + truth validation on boot."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from hostess7.paths import hostess7_root, scripts_dir, storage_dir


def _run_script(name: str, *args: str, timeout: int = 90) -> dict[str, Any]:
    script = scripts_dir() / name
    if not script.is_file():
        return {"ok": False, "error": f"missing {name}"}
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(hostess7_root()),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env={**os.environ, "HOSTESS7_ROOT": str(hostess7_root())},
    )
    return {
        "ok": proc.returncode == 0,
        "rc": proc.returncode,
        "stdout": (proc.stdout or "").strip()[-1500:],
        "stderr": (proc.stderr or "").strip()[-500:],
    }


def benchmark_iq() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    score = 0.0
    max_score = 10.0

    brain = storage_dir() / "brain"
    if brain.is_dir() and any(brain.rglob("*.json")):
        checks.append({"id": "brain_storage", "ok": True, "weight": 2.0})
        score += 2.0
    else:
        checks.append({"id": "brain_storage", "ok": False, "weight": 2.0})

    stack = _run_script("field_stack_corpus.py", "status")
    checks.append({"id": "stack_corpus", "ok": stack.get("ok"), "weight": 1.5})
    if stack.get("ok"):
        score += 1.5

    truth_doc = _run_script("field_hostess_truth_doctrine.py")
    checks.append({"id": "truth_doctrine", "ok": truth_doc.get("ok"), "weight": 1.5})
    if truth_doc.get("ok"):
        score += 1.5

    for qscript, qid, w in (
        ("qa_brain_hemisphere_test.py", "hemisphere", 1.0),
        ("qa_intelligence_flow_test.py", "intel_flow", 1.0),
        ("qa_redata_truth_test.py", "redata_truth", 1.0),
    ):
        r = _run_script(qscript)
        ok = r.get("ok", False)
        checks.append({"id": qid, "ok": ok, "weight": w})
        if ok:
            score += w

    secure = scripts_dir() / "hostess7_secure_git.py"
    if secure.is_file():
        proc = subprocess.run(
            [sys.executable, str(secure), "verify"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        try:
            v = json.loads(proc.stdout or "{}")
            ok = bool(v.get("ok"))
        except json.JSONDecodeError:
            ok = proc.returncode == 0
        checks.append({"id": "secure_git", "ok": ok, "weight": 1.0})
        if ok:
            score += 1.0

    normalized = round(min(10.0, score), 2)
    return {
        "ok": normalized >= 6.0,
        "score": normalized,
        "max": max_score,
        "checks": checks,
        "grade": "war-ready" if normalized >= 8 else "operational" if normalized >= 6 else "bootstrapping",
    }


def validate_truth() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    from importlib.util import module_from_spec, spec_from_file_location

    license_py = scripts_dir() / "field_license_status.py"
    war = False
    demo = True
    if license_py.is_file():
        spec = spec_from_file_location("field_license_status", license_py)
        if spec and spec.loader:
            mod = module_from_spec(spec)
            spec.loader.exec_module(mod)
            war = bool(getattr(mod, "is_war_ready", lambda: False)())
            demo = bool(getattr(mod, "is_demo", lambda: True)())

    checks.append({"id": "war_ready", "ok": war, "detail": "HOSTESS7_LICENSE_MODE=war"})
    checks.append({"id": "not_demo", "ok": not demo, "detail": "demo must be false"})

    doctrine = hostess7_root() / "data" / "hostess7-truth-floor.json"
    checks.append({"id": "truth_floor", "ok": doctrine.is_file()})

    lie = _run_script("field_brain_core.py", "truth", "never lie to owner")
    checks.append({"id": "truth_query", "ok": lie.get("ok") or "truth" in (lie.get("stdout") or "").lower()})

    ok = all(c.get("ok") for c in checks)
    return {"ok": ok, "checks": checks, "policy": "presume_hostile · defend · never demo"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "all").strip().lower()
    if cmd in ("iq", "benchmark", "benchmark-iq"):
        print(json.dumps(benchmark_iq(), indent=2))
        return 0
    if cmd in ("truth", "validate-truth"):
        print(json.dumps(validate_truth(), indent=2))
        return 0
    doc = {"iq": benchmark_iq(), "truth": validate_truth()}
    print(json.dumps(doc, indent=2))
    return 0 if doc["iq"].get("ok") and doc["truth"].get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())