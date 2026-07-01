#!/usr/bin/env pythong
"""Queen ↔ Hostess 7 brain bridge — redata, truth filter, ZAC textbook, comfort status."""
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
HOSTESS = Path(os.environ.get("HOSTESS7_ROOT", SG / "Hostess7"))
TEXTBOOK = SG / "NewLatest" / "Textbook"
BRAIN_MANIFEST = QUEEN / "data" / "queen-brain-manifest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _ai_communique_env() -> dict[str, str]:
    return {
        **os.environ,
        "GPY16_TOOLING": "1",
        "HOSTESS7_AI_PRIMARY": os.environ.get("HOSTESS7_AI_PRIMARY", "1"),
        "HOSTESS7_AI_COMMUNIQUE": os.environ.get("HOSTESS7_AI_COMMUNIQUE", "1"),
    }


def _extract_json_stdout(stdout: str) -> dict[str, Any]:
    for line in reversed((stdout or "").splitlines()):
        s = line.strip()
        if not s.startswith("{"):
            continue
        try:
            doc = json.loads(s)
            if isinstance(doc, dict):
                return doc
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("no JSON object in stdout", stdout or "", 0)


def _run_hostess_sh(cmd: str, *args: str, timeout: int = 300) -> dict[str, Any]:
    h7sh = HOSTESS / "Hostess7.sh"
    if not h7sh.is_file():
        return {"ok": False, "error": "Hostess7.sh missing"}
    proc = subprocess.run(
        [str(h7sh), cmd, *args],
        cwd=str(HOSTESS),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-2500:],
    }


def _sdf_stats() -> dict[str, Any]:
    sdf = HOSTESS / "cache" / "fieldstorage" / "brain" / "sdf"
    if not sdf.is_dir():
        return {"available": False}
    segments = list((sdf / "segments").glob("seg-*.json")) if (sdf / "segments").is_dir() else []
    human = list((sdf / "plates").glob("*.human.pgm")) if (sdf / "plates").is_dir() else []
    quarantine = list((sdf / "quarantine").glob("seg-*.json")) if (sdf / "quarantine").is_dir() else []
    truth_log = sdf / "truth_filter.jsonl"
    truth_lines = sum(1 for _ in truth_log.open(encoding="utf-8")) if truth_log.is_file() else 0
    brief = _load_json(sdf / "queen_redata_brief.json")
    return {
        "available": True,
        "segments": len(segments),
        "human_plates": len(human),
        "quarantined": len(quarantine),
        "truth_log_lines": truth_lines,
        "brief_present": brief.get("comfort") is not None,
        "build_tools": len(brief.get("build_tools") or []),
    }


def _textbook_status() -> dict[str, Any]:
    zac = TEXTBOOK / "field-technology-v5.zac"
    build = TEXTBOOK / "build-field-technology-zac.py"
    summary = _load_json(TEXTBOOK / "build-summary.json")
    sizes = _load_json(TEXTBOOK / "size-comparison.json")
    return {
        "zac_present": zac.is_file(),
        "zac_bytes": zac.stat().st_size if zac.is_file() else 0,
        "build_script": str(build) if build.is_file() else None,
        "verify_ok": summary.get("verify_ok"),
        "segments": summary.get("staging", {}).get("segments"),
        "truth_accepted": summary.get("staging", {}).get("truth_accepted"),
        "size_rows": sizes.get("rows", []),
    }


def hostess_comfort() -> dict[str, Any]:
    brief = _load_json(HOSTESS / "cache" / "fieldstorage" / "brain" / "sdf" / "queen_redata_brief.json")
    manifest = _load_json(BRAIN_MANIFEST)
    ops = manifest.get("hostess7_brain_ops") or {}
    return {
        "comfort": brief.get("comfort") or ops.get("comfort") or (
            "Hostess 7 owns brain/sdf/ and cache/fieldstorage. Queen orchestrates; lossless redata is law."
        ),
        "hostess_root": str(HOSTESS),
        "sovereign_storage": "cache/fieldstorage/brain/sdf/",
        "teach_cmd": "./Hostess7.sh queen-teach-redata",
    }


def _compiler_probe() -> dict[str, Any]:
    try:
        sys.path.insert(0, str(QUEEN / "lib"))
        from forge.hostess_tools import probe_compilers
        from forge.engine import ForgeContext
        return probe_compilers(ForgeContext.from_env())
    except Exception:
        return {}


def _eyeball_status() -> dict[str, Any]:
    bridge = QUEEN / "lib" / "queen-eyeball.py"
    if not bridge.is_file():
        return {"available": False}
    proc = subprocess.run(
        [sys.executable, str(bridge), "json"],
        cwd=str(QUEEN),
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "NEXUS_INSTALL_ROOT": str(QUEEN), "SG_ROOT": str(SG)},
    )
    try:
        return {"available": True, **json.loads(proc.stdout)}
    except json.JSONDecodeError:
        return {"available": False, "tail": (proc.stdout or "")[-1500:]}


def _ai_communique_status() -> dict[str, Any]:
    script = HOSTESS / "scripts" / "field_ai_communique.py"
    if not script.is_file():
        return {"available": False}
    proc = subprocess.run(
        [sys.executable, str(script), "status"],
        cwd=str(HOSTESS),
        capture_output=True,
        text=True,
        timeout=45,
        env=_ai_communique_env(),
    )
    try:
        return {"available": True, **_extract_json_stdout(proc.stdout)}
    except json.JSONDecodeError:
        return {"available": False, "tail": (proc.stdout or "")[-1500:]}


def _ai_operate(query: str, *, from_: str = "ai") -> dict[str, Any]:
    script = HOSTESS / "scripts" / "field_ai_communique.py"
    if not script.is_file():
        return {"ok": False, "error": "field_ai_communique_missing"}
    proc = subprocess.run(
        [sys.executable, str(script), "operate", query],
        cwd=str(HOSTESS),
        capture_output=True,
        text=True,
        timeout=120,
        env={**_ai_communique_env(), "HOSTESS7_FROM": from_},
    )
    try:
        doc = _extract_json_stdout(proc.stdout)
        doc["ok"] = True
        return doc
    except json.JSONDecodeError:
        return {"ok": False, "tail": (proc.stdout or "")[-2000:], "returncode": proc.returncode}


def _muscle_memory_status() -> dict[str, Any]:
    script = SG / "NewLatest" / "lib" / "hostess7-muscle-memory.py"
    if not script.is_file():
        return {"available": False}
    proc = subprocess.run(
        [sys.executable, str(script), "json"],
        cwd=str(SG / "NewLatest"),
        capture_output=True,
        text=True,
        timeout=30,
        env={
            **os.environ,
            "NEXUS_STATE_DIR": os.environ.get("NEXUS_STATE_DIR", str(QUEEN / ".nexus-state")),
            "NEXUS_INSTALL_ROOT": str(SG / "NewLatest"),
            "SG_ROOT": str(SG),
        },
    )
    try:
        return {"available": True, **json.loads(proc.stdout)}
    except json.JSONDecodeError:
        return {"available": False, "tail": (proc.stdout or "")[-1500:]}


def hostess_brain_status() -> dict[str, Any]:
    manifest = _load_json(BRAIN_MANIFEST)
    return {
        "schema": "queen-hostess-brain/v1",
        "updated": _now(),
        "hostess_root": str(HOSTESS) if HOSTESS.is_dir() else None,
        "hostess_available": HOSTESS.is_dir(),
        "ai_communique": _ai_communique_status(),
        "brain_manifest": manifest.get("title"),
        "hostess7_sdf_storage": manifest.get("hostess7_sdf_storage", {}),
        "hostess7_brain_ops": manifest.get("hostess7_brain_ops", {}),
        "field_technology": manifest.get("field_technology", {}),
        "final_eyeball": manifest.get("final_eyeball", {}),
        "hostess7_final_eye": manifest.get("hostess7_final_eye", {}),
        "final_eye_doctrine": _load_json(HOSTESS / "data" / "final-eye-12-doctrine.json"),
        "eyeball": _eyeball_status(),
        "muscle_memory": _muscle_memory_status(),
        "comfort": hostess_comfort(),
        "sdf": _sdf_stats(),
        "textbook": _textbook_status(),
        "compilers": _compiler_probe(),
    }


def teach_hostess() -> dict[str, Any]:
    teach = HOSTESS / "scripts" / "field_queen_redata_teach.py"
    if not teach.is_file():
        return {"ok": False, "error": "field_queen_redata_teach_missing"}
    proc = subprocess.run(
        [sys.executable, str(teach)],
        cwd=str(HOSTESS),
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "tail": (proc.stdout or "")[-3000:],
        "status": hostess_brain_status(),
    }


def verify_redata() -> dict[str, Any]:
    out = _run_hostess_sh("sdf-verify-redata")
    out["status"] = hostess_brain_status()
    return out


def ingest_textbook_brain() -> dict[str, Any]:
    """Copy textbook staging brain/sdf → Hostess7 cache (lossless segments + plates)."""
    staging = TEXTBOOK / "staging" / "fieldstorage" / "brain" / "sdf"
    dst = HOSTESS / "cache" / "fieldstorage" / "brain" / "sdf"
    if not staging.is_dir():
        return {"ok": False, "error": "textbook_staging_missing", "path": str(staging)}
    import shutil
    for sub in ("segments", "plates", "quarantine"):
        src_d = staging / sub
        if src_d.is_dir():
            out_d = dst / sub
            out_d.mkdir(parents=True, exist_ok=True)
            for f in src_d.iterdir():
                if f.is_file():
                    shutil.copy2(f, out_d / f.name)
    for fname in ("truth_filter.jsonl", "segment_registry.jsonl", "corpus.json"):
        src_f = staging / fname
        if src_f.is_file():
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_f, dst / fname)
    return {
        "ok": True,
        "staging": str(staging),
        "dest": str(dst),
        "status": hostess_brain_status(),
    }


def zocr_smoke() -> dict[str, Any]:
    bridge = QUEEN / "lib" / "queen-zocr.py"
    if not bridge.is_file():
        return {"ok": False, "error": "queen-zocr missing"}
    proc = subprocess.run(
        [sys.executable, str(bridge), "browser-smoke"],
        cwd=str(QUEEN),
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "NEXUS_INSTALL_ROOT": str(QUEEN), "SG_ROOT": str(SG)},
    )
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        doc = {"ok": False, "tail": (proc.stdout or "")[-2000:]}
    doc["returncode"] = proc.returncode
    doc["zocr_root"] = str(SG / "ZOCR")
    return doc


def verify_textbook_zac() -> dict[str, Any]:
    build = TEXTBOOK / "build-field-technology-zac.py"
    if not build.is_file():
        return {"ok": False, "error": "textbook_build_missing"}
    proc = subprocess.run(
        [sys.executable, str(build), "--verify-only"],
        cwd=str(TEXTBOOK),
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "tail": (proc.stdout or "")[-2000:],
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "json"):
        return {"ok": True, **hostess_brain_status()}
    if action in ("teach", "queen-teach", "queen_teach", "comfort-teach"):
        return teach_hostess()
    if action in ("verify-redata", "verify_redata", "sdf-verify-redata"):
        return verify_redata()
    if action in ("verify-textbook", "verify_textbook", "zac-verify-textbook"):
        return verify_textbook_zac()
    if action in ("ingest-textbook", "ingest_textbook", "textbook-ingest"):
        return ingest_textbook_brain()
    if action in ("zocr", "zocr-smoke", "browser-smoke", "ocr-smoke"):
        return zocr_smoke()
    if action in ("eyeball", "eyeball-status", "final-eye"):
        bridge = QUEEN / "lib" / "queen-eyeball.py"
        proc = subprocess.run(
            [sys.executable, str(bridge), "json"],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(QUEEN), "SG_ROOT": str(SG)},
        )
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "tail": (proc.stdout or "")[-2000:]}
    if action in ("eyeball-verify", "verify-eyeball"):
        bridge = QUEEN / "lib" / "queen-eyeball.py"
        proc = subprocess.run(
            [sys.executable, str(bridge), "verify"],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(QUEEN), "SG_ROOT": str(SG)},
        )
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "tail": (proc.stdout or "")[-2000:]}
    if action in ("eyeball-arm", "arm-dishes"):
        bridge = QUEEN / "lib" / "queen-eyeball.py"
        mode = str(body.get("mode") or "dishes")
        proc = subprocess.run(
            [sys.executable, str(bridge), "arm", mode],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(QUEEN), "SG_ROOT": str(SG)},
        )
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "tail": (proc.stdout or "")[-2000:]}
    if action in ("comfort",):
        return {"ok": True, **hostess_comfort()}
    if action in ("ai-communique", "ai_communique", "ai-status", "ai_status"):
        return {"ok": True, **_ai_communique_status()}
    if action in ("ai-operate", "ai_operate", "ai_operate", "superintel", "superintel_operate"):
        q = str(body.get("query") or body.get("text") or "")
        return _ai_operate(q, from_=str(body.get("from") or "queen-ai"))
    if action in ("ai-teach", "ai_teach", "teach-ai-communique"):
        script = HOSTESS / "scripts" / "field_ai_communique.py"
        proc = subprocess.run(
            [sys.executable, str(script), "teach"],
            cwd=str(HOSTESS),
            capture_output=True,
            text=True,
            timeout=60,
            env=_ai_communique_env(),
        )
        try:
            return _extract_json_stdout(proc.stdout)
        except json.JSONDecodeError:
            return {"ok": proc.returncode == 0, "tail": (proc.stdout or "")[-2000:]}
    if action in ("muscle_memory", "muscle-memory", "muscle"):
        script = SG / "NewLatest" / "lib" / "hostess7-muscle-memory.py"
        if not script.is_file():
            return {"ok": False, "error": "muscle_memory_missing"}
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps(body),
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(SG / "NewLatest"),
            env={
                **_ai_communique_env(),
                "NEXUS_STATE_DIR": os.environ.get("NEXUS_STATE_DIR", str(QUEEN / ".nexus-state")),
                "NEXUS_INSTALL_ROOT": str(SG / "NewLatest"),
                "SG_ROOT": str(SG),
            },
        )
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "tail": (proc.stdout or "")[-2000:]}
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(hostess_brain_status(), ensure_ascii=False))
        return 0
    if cmd == "teach":
        print(json.dumps(teach_hostess(), ensure_ascii=False))
        return 0
    if cmd == "ingest-textbook":
        print(json.dumps(ingest_textbook_brain(), ensure_ascii=False))
        return 0
    if cmd in ("zocr", "browser-smoke"):
        print(json.dumps(zocr_smoke(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-hostess-brain.py [json|teach|ingest-textbook|browser-smoke|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())