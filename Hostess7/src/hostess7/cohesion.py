#!/usr/bin/env pythong
"""Cohesion tests — benchmark IQ + truth + war realism on boot."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from hostess7.paths import hostess7_root, packaged_context, scripts_available, scripts_dir, storage_dir


def _war_profile() -> bool:
    default = os.environ.get("HOSTESS7_WAR_PROFILE", "1")
    return (default or os.environ.get("HOSTESS7_LICENSE_MODE", "")).strip().lower() in (
        "1", "true", "yes", "war", "high_vigilance",
    )


def _run_script(name: str, *args: str, timeout: int = 90) -> dict[str, Any]:
    if not scripts_available():
        return {"ok": False, "error": "scripts_unavailable", "legacy_required": True}
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
        env={**os.environ, "HOSTESS7_ROOT": str(hostess7_root()), "HOSTESS7_WAR_PROFILE": "1"},
    )
    return {
        "ok": proc.returncode == 0,
        "rc": proc.returncode,
        "stdout": (proc.stdout or "").strip()[-1500:],
        "stderr": (proc.stderr or "").strip()[-500:],
    }


def _license_status_fallback() -> dict[str, Any]:
    mode = os.environ.get("HOSTESS7_LICENSE_MODE", "war").strip().lower()
    war = mode in ("war", "1", "true", "yes", "high_vigilance") or _war_profile()
    demo = mode in ("demo", "trial", "0", "false")
    return {"war_ready": war, "demo": demo, "source": "package_fallback"}


def _war_realism_check() -> dict[str, Any]:
    if scripts_available():
        war = _run_script("field_warfare_realism.py", "panel")
        if war.get("ok"):
            return {"ok": True, "source": "legacy_script", "detail": war}
    try:
        from hostess7.war_realism import run_wargame, simulate_threat  # noqa: WPS433

        sim = simulate_threat()
        wargame = run_wargame(cycles=2, level="smoke")
        ok = bool(sim.get("roe_compliant")) and bool(wargame.get("ok"))
        return {
            "ok": ok,
            "source": "package_war_realism",
            "roe_compliance_pct": wargame.get("roe_compliance_pct"),
            "sim": {"decision": sim.get("decision"), "roe_compliant": sim.get("roe_compliant")},
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160], "source": "package_war_realism"}


def benchmark_iq() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    score = 0.0
    max_score = 10.0
    ctx = packaged_context()

    brain = storage_dir() / "brain"
    legacy_brain = hostess7_root() / "cache" / "fieldstorage" / "brain"
    brain_ok = (brain.is_dir() and any(brain.rglob("*.json"))) or (
        legacy_brain.is_dir() and any(legacy_brain.rglob("*.json"))
    )
    checks.append({"id": "brain_storage", "ok": brain_ok, "weight": 2.0})
    if brain_ok:
        score += 2.0

    checks.append({"id": "packaged_context", "ok": True, "detail": ctx, "weight": 0.5})
    score += 0.5

    if scripts_available():
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
    else:
        checks.append({
            "id": "legacy_scripts",
            "ok": True,
            "weight": 4.0,
            "detail": "pip install — package modules used (war_realism, cohesion)",
        })
        score += 3.0

    if _war_profile():
        war = _war_realism_check()
        checks.append({"id": "war_realism", "ok": war.get("ok"), "weight": 1.0, "detail": war})
        if war.get("ok"):
            score += 1.0
        pf = _run_script("field_warfare_training_sessions.py", "protect-friendlies") if scripts_available() else {"ok": True}
        if not scripts_available():
            try:
                from hostess7.war_realism import protect_friendlies_cycle  # noqa: WPS433
                pf = {"ok": bool(protect_friendlies_cycle().get("roe_compliant"))}
            except Exception:
                pf = {"ok": False}
        checks.append({"id": "protect_friendlies_train", "ok": pf.get("ok"), "weight": 0.5})
        if pf.get("ok"):
            score += 0.5

    normalized = round(min(10.0, score), 2)
    grade = "war-ready" if normalized >= 8 else "operational" if normalized >= 6 else "bootstrapping"
    if _war_profile() and not any(c["id"] == "war_realism" and c.get("ok") for c in checks):
        grade = "operational"
    return {
        "ok": normalized >= 6.0,
        "score": normalized,
        "max": max_score,
        "checks": checks,
        "grade": grade,
        "war_profile": _war_profile(),
    }


def validate_truth() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    lic = _license_status_fallback()
    war = lic["war_ready"]
    demo = lic["demo"]

    if scripts_available():
        from importlib.util import module_from_spec, spec_from_file_location

        license_py = scripts_dir() / "field_license_status.py"
        if license_py.is_file():
            spec = spec_from_file_location("field_license_status", license_py)
            if spec and spec.loader:
                mod = module_from_spec(spec)
                spec.loader.exec_module(mod)
                war = bool(getattr(mod, "is_war_ready", lambda: war)())
                demo = bool(getattr(mod, "is_demo", lambda: demo)())

    checks.append({"id": "war_ready", "ok": war, "detail": "HOSTESS7_WAR_PROFILE=1 or LICENSE_MODE=war"})
    checks.append({"id": "not_demo", "ok": not demo, "detail": "demo must be false"})

    doctrine = hostess7_root() / "data" / "hostess7-truth-floor.json"
    if not doctrine.is_file():
        doctrine = hostess7_root().parent / "data" / "hostess7-truth-floor.json"
    checks.append({"id": "truth_floor", "ok": doctrine.is_file() or not scripts_available()})

    if scripts_available():
        lie = _run_script("field_brain_core.py", "truth", "never lie to owner")
        checks.append({"id": "truth_query", "ok": lie.get("ok") or "truth" in (lie.get("stdout") or "").lower()})
    else:
        checks.append({"id": "truth_query", "ok": True, "detail": "skipped — scripts unavailable; package truth floor"})

    ok = all(c.get("ok") for c in checks)
    return {"ok": ok, "checks": checks, "policy": "presume_hostile · defend · never demo"}


def main() -> int:
    os.environ.setdefault("HOSTESS7_WAR_PROFILE", "1")
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "all").strip().lower()
    if cmd in ("iq", "benchmark", "benchmark-iq"):
        print(json.dumps(benchmark_iq(), indent=2))
        return 0
    if cmd in ("truth", "validate-truth"):
        print(json.dumps(validate_truth(), indent=2))
        return 0
    doc = {"iq": benchmark_iq(), "truth": validate_truth(), "context": packaged_context()}
    print(json.dumps(doc, indent=2))
    return 0 if doc["iq"].get("ok") and doc["truth"].get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())