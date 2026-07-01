#!/usr/bin/env pythong
"""Grok AI Lab — live Final Eye + KILROY protection battery. Forever war with terror; resolute."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
KILROY = Path(os.environ.get("KILROY_ROOT", str(INSTALL / "KILROY")))
LAB = Path(os.environ.get("GROK_LAB_ROOT", str(INSTALL / "GrokLab")))
STATE = Path(os.environ.get("GROK_LAB_STATE", str(LAB / ".lab-state")))
DOCTRINE = LAB / "data" / "grok-ai-lab-doctrine.json"
REPORT = STATE / "grok-ai-lab-report.json"
RECEIPT = STATE / "grok-ai-lab-last.json"
FINAL_EYE = Path(os.environ.get("FINAL_EYE_ROOT", str(INSTALL / "Final_Eye")))
PORT = int(os.environ.get("FINAL_EYE_PORT", os.environ.get("ZOCR_PORT", "9479")))
HOST = os.environ.get("FINAL_EYE_HOST", "127.0.0.1")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _py() -> str:
    return os.environ.get("GROK_LAB_PY", sys.executable)


def _env() -> dict[str, str]:
    return {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "KILROY_ROOT": str(KILROY),
        "FINAL_EYE_ROOT": str(FINAL_EYE),
        "NEXUS_STATE_DIR": os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")),
        "GROK_LAB_STATE": str(STATE),
        "ZOCR_VISION_SESSION": str(FINAL_EYE / "data" / "vision-session.jsonl"),
        "PYTHONPATH": os.pathsep.join(
            p for p in (str(FINAL_EYE), os.environ.get("PYTHONPATH", "")) if p
        ),
    }


def _run_json(py: Path, *argv: str, timeout: int = 45) -> dict[str, Any]:
    if not py.is_file():
        return {"ok": False, "error": f"missing {py}"}
    proc = subprocess.run(
        [_py(), str(py), *argv],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=_env(),
        cwd=str(INSTALL),
    )
    try:
        doc = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        doc = {"ok": False, "tail": (proc.stdout or proc.stderr or "")[-2000:]}
    doc["returncode"] = proc.returncode
    return doc


def _http_json(method: str, path: str, timeout: float = 12.0) -> dict[str, Any]:
    url = f"http://{HOST}:{PORT}{path}"
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
            return json.loads(body)
        except (json.JSONDecodeError, OSError):
            return {"ok": False, "error": f"http_{exc.code}", "url": url}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": str(exc), "url": url}


def final_eye_running() -> bool:
    doc = _http_json("GET", "/api/health", timeout=3.0)
    return bool(doc.get("ok"))


def start_final_eye(*, headless: bool = True) -> dict[str, Any]:
    if final_eye_running():
        return {"ok": True, "already_running": True, "url": f"http://{HOST}:{PORT}/"}
    app = FINAL_EYE / "gui" / "app.py"
    if not app.is_file():
        return {"ok": False, "error": "final_eye_app_missing", "path": str(app)}
    log = FINAL_EYE / "data" / "server.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        proc = subprocess.Popen(
            [_py(), str(app)],
            stdout=fh,
            stderr=subprocess.STDOUT,
            env=_env(),
            cwd=str(FINAL_EYE),
            start_new_session=True,
        )
    pidfile = FINAL_EYE / "data" / "zocr-server.pid"
    pidfile.write_text(f"{proc.pid}\n", encoding="utf-8")
    for _ in range(20):
        time.sleep(0.25)
        if final_eye_running():
            return {"ok": True, "pid": proc.pid, "url": f"http://{HOST}:{PORT}/", "headless": headless}
    return {"ok": False, "error": "zocr_start_timeout", "pid": proc.pid, "log": str(log)}


def stop_final_eye() -> dict[str, Any]:
    pidfile = FINAL_EYE / "data" / "zocr-server.pid"
    stopped = False
    if pidfile.is_file():
        try:
            pid = int(pidfile.read_text(encoding="utf-8").strip())
            os.kill(pid, 15)
            stopped = True
        except (OSError, ValueError):
            pass
        pidfile.unlink(missing_ok=True)
    return {"ok": True, "stopped": stopped}


def boot_protection() -> dict[str, Any]:
    """Boot posture — revalidate kill list + RE-KILL immediately; seal Final Eye."""
    out: dict[str, Any] = {"ok": True, "steps": []}
    kit = INSTALL / "lib" / "field-attack-kit.py"
    if kit.is_file():
        os.environ["NEXUS_BOOT_REKILL"] = "1"
        boot = _run_json(kit, "boot-rekill", timeout=120)
        out["steps"].append({"boot_rekill": boot})
        if boot.get("ok") is False:
            out["ok"] = False
    kill_py = FINAL_EYE / "zocr_kill.py"
    if kill_py.is_file() and os.environ.get("GROK_LAB_RELEASE_EYE", "0") != "1":
        rekill = _run_json(kill_py, "rekill-at-boot", timeout=20)
        out["steps"].append({"final_eye_rekill": rekill})
    elif kill_py.is_file():
        rel = _run_json(kill_py, "release", "all", timeout=15)
        out["steps"].append({"lab_release_eye": rel})
    seal = FINAL_EYE / "zocr_security.py"
    if seal.is_file():
        sealed = _run_json(seal, "seal", timeout=30)
        out["steps"].append({"seal": {"ok": sealed.get("ok", sealed.get("file_count") is not None)}})
    hostile_scan = INSTALL / "lib" / "field-one-hostile-scan.py"
    if hostile_scan.is_file():
        os.environ.setdefault("FIELD_ONE_BRING_STORAGE_ONLY", "1")
        scan = _run_json(hostile_scan, timeout=90)
        out["steps"].append({
            "field_one_hostile_scan": {
                "ok": scan.get("scanned", 0) >= 0,
                "scanned": scan.get("scanned"),
                "new_hostile": scan.get("new_hostile"),
            },
        })
    return out


def arm_final_eye() -> dict[str, Any]:
    """Lab arm — boot protection by default; release vision only when GROK_LAB_RELEASE_EYE=1."""
    return boot_protection()


def _test_sanctuary() -> dict[str, Any]:
    doc = _run_json(INSTALL / "lib" / "kilroy-field-brain.py", "evaluate", "127.0.0.1")
    ok = doc.get("ip") == "127.0.0.1" and not doc.get("strike_authorized")
    return {"id": "sanctuary_127", "ok": ok, "strike_authorized": doc.get("strike_authorized"), "reasons": doc.get("reasons")}


def _test_defensive_external() -> dict[str, Any]:
    # Public routable test target — not loopback/private/reserved (203.0.113.x is TEST-NET reserved).
    doc = _run_json(INSTALL / "lib" / "kilroy-field-brain.py", "evaluate", "185.220.101.1", "HOSTILE")
    ok = not doc.get("strike_authorized")
    reasons = doc.get("reasons") or []
    ok = ok and "kilroy_sanctuary_inside" not in reasons
    return {"id": "defensive_external", "ok": ok, "strike_authorized": doc.get("strike_authorized"), "reasons": reasons}


def _test_health() -> dict[str, Any]:
    doc = _http_json("GET", "/api/health")
    return {"id": "final_eye_health", "ok": bool(doc.get("ok")), "product": doc.get("product"), "version": doc.get("version")}


def _test_look() -> dict[str, Any]:
    doc = _http_json("POST", "/api/look", timeout=90.0)
    ok = bool(doc.get("ok"))
    return {
        "id": "final_eye_look",
        "ok": ok,
        "label": doc.get("label"),
        "ocr_len": doc.get("ocr_len"),
        "error": doc.get("error"),
        "source": (doc.get("meta") or {}).get("source") if isinstance(doc.get("meta"), dict) else None,
    }


def _test_observe() -> dict[str, Any]:
    if not final_eye_running():
        start_final_eye()
        time.sleep(0.5)
    doc = _http_json("POST", "/api/observe", timeout=120.0)
    ok = bool(doc.get("ok"))
    if not ok and doc.get("error") == "Remote end closed connection without response":
        # Observe chains look+robotics — retry once after server settles.
        time.sleep(1.0)
        if not final_eye_running():
            start_final_eye()
            arm_final_eye()
            time.sleep(0.5)
        doc = _http_json("POST", "/api/observe", timeout=120.0)
        ok = bool(doc.get("ok"))
    return {"id": "final_eye_observe", "ok": ok, "error": doc.get("error")}


def _test_ocr_brain() -> dict[str, Any]:
    doc = _run_json(INSTALL / "lib" / "kilroy-final-eye-brain.py", "ocr-brain", timeout=30)
    ok = doc.get("role") == "ocr_brain" and doc.get("owner") == "grok"
    return {"id": "ocr_brain_context", "ok": ok, "corpus_captures": (doc.get("corpus") or {}).get("manifest_captures")}


def _test_field_brain() -> dict[str, Any]:
    doc = _run_json(INSTALL / "lib" / "kilroy-field-brain.py", "board", timeout=20)
    fe = doc.get("final_eye") or {}
    ok = fe.get("ocr_brain") and fe.get("ok")
    return {"id": "field_brain_board", "ok": bool(ok), "final_eye": fe}


def _test_ingest() -> dict[str, Any]:
    doc = _run_json(INSTALL / "lib" / "kilroy-final-eye-brain.py", "ingest", timeout=20)
    ok = int(doc.get("manifest_captures") or 0) >= 0
    return {
        "id": "corpus_ingest",
        "ok": ok,
        "manifest_captures": doc.get("manifest_captures"),
        "ocr_bytes_total": doc.get("ocr_bytes_total"),
    }


def run_battery(*, start_eye: bool = True, arm: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    preamble: dict[str, Any] = {}
    if start_eye:
        preamble["start"] = start_final_eye()
        if not preamble["start"].get("ok"):
            return {
                "schema": "grok-ai-lab-report/v1",
                "updated": _now(),
                "ok": False,
                "blocked": "final_eye_start_failed",
                "preamble": preamble,
            }
    if arm:
        preamble["boot_protection"] = boot_protection()

    tests = [
        _test_sanctuary,
        _test_defensive_external,
        _test_health,
        _test_look,
        _test_observe,
        _test_ocr_brain,
        _test_field_brain,
        _test_ingest,
    ]
    results: list[dict[str, Any]] = []
    for fn in tests:
        try:
            results.append(fn())
        except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
            results.append({"id": getattr(fn, "__name__", "test"), "ok": False, "error": str(exc)})

    passed = sum(1 for r in results if r.get("ok"))
    failed = [r for r in results if not r.get("ok")]
    doc = {
        "schema": "grok-ai-lab-report/v1",
        "updated": _now(),
        "owner": "grok",
        "motto": doctrine.get("motto"),
        "war_posture": (doctrine.get("war") or {}).get("posture"),
        "home": doctrine.get("home", "127.0.0.1"),
        "ok": len(failed) == 0,
        "passed": passed,
        "total": len(results),
        "preamble": preamble,
        "results": results,
        "failed": failed,
        "final_eye_url": f"http://{HOST}:{PORT}/",
        "lab_state": str(STATE),
    }
    _save(REPORT, doc)
    _save(RECEIPT, {"schema": "grok-ai-lab-receipt/v1", "updated": _now(), "ok": doc["ok"], "passed": passed, "total": len(results)})
    return doc


def run_live(*, loops: int = 3, interval: float = 30.0) -> dict[str, Any]:
    """Live work loop — Final Eye look + OCR brain + sanctuary re-check."""
    doctrine = _load(DOCTRINE, {})
    loops = int(os.environ.get("GROK_LAB_LOOPS", loops))
    interval = float(os.environ.get("GROK_LAB_INTERVAL", interval))
    boot_protection()
    start_final_eye()
    cycles: list[dict[str, Any]] = []
    for i in range(loops):
        cycle = {
            "cycle": i + 1,
            "ts": _now(),
            "health": _test_health(),
            "look": _test_look(),
            "ocr_brain": _test_ocr_brain(),
            "sanctuary": _test_sanctuary(),
            "ingest": _test_ingest(),
        }
        cycles.append(cycle)
        if i + 1 < loops:
            time.sleep(interval)
    doc = {
        "schema": "grok-ai-lab-live/v1",
        "updated": _now(),
        "owner": "grok",
        "motto": doctrine.get("motto"),
        "loops": loops,
        "interval_sec": interval,
        "ok": all(c["sanctuary"]["ok"] for c in cycles),
        "cycles": cycles,
    }
    _save(STATE / "grok-ai-lab-live.json", doc)
    return doc


def status() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    return {
        "schema": "grok-ai-lab-status/v1",
        "updated": _now(),
        "doctrine": doctrine,
        "final_eye_running": final_eye_running(),
        "final_eye_url": f"http://{HOST}:{PORT}/",
        "last_report": _load(REPORT) if REPORT.is_file() else None,
        "last_receipt": _load(RECEIPT) if RECEIPT.is_file() else None,
        "lab_state": str(STATE),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("status", "json"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("start", "eye-start"):
        print(json.dumps(start_final_eye(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("stop", "eye-stop"):
        print(json.dumps(stop_final_eye(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("boot", "protect", "boot-rekill"):
        print(json.dumps(boot_protection(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("arm", "release"):
        print(json.dumps(arm_final_eye(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("revalidate", "revalidate-kill-list"):
        kit = INSTALL / "lib" / "field-attack-kit.py"
        print(json.dumps(_run_json(kit, "revalidate-kill-list") if kit.is_file() else {"error": "missing"}, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("battery", "test", "protect"):
        doc = run_battery()
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "live":
        loops = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        doc = run_live(loops=loops)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    print(json.dumps({
        "error": "usage: grok-ai-lab.py [status|start|stop|arm|battery|live [loops]]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())