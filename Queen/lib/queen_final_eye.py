"""Queen → Final_Eye — OCR, AI eyeball, plate-melded vision bridge."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
_NL_LIB = QUEEN.parent / "lib"
if str(_NL_LIB) not in sys.path:
    sys.path.insert(0, str(_NL_LIB))


def final_eye_root() -> Path:
    """Canonical Final_Eye — NewLatest/Final_Eye only; ZOCR retired."""
    try:
        from sg_paths import final_eye_root as _fer
        return _fer()
    except Exception:
        pass
    env = os.environ.get("FINAL_EYE_ROOT", "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    install = Path(os.environ.get("NEXUS_INSTALL_ROOT", SG / "NewLatest"))
    for candidate in (install / "Final_Eye", SG / "NewLatest" / "Final_Eye", SG / "Final_Eye"):
        if (candidate / "zocr_product.py").is_file() or (candidate / "VERSION").is_file():
            return candidate
    return install / "Final_Eye"


def final_eye_env(*, queen: Path | None = None) -> dict[str, str]:
    """Environment for subprocess / import of Final_Eye stack."""
    root = final_eye_root()
    q = queen or QUEEN
    hostess = Path(os.environ.get("HOSTESS7_ROOT", SG / "NewLatest" / "Hostess7"))
    gmf = root / "GrokMediaFormat"
    if not gmf.is_dir():
        gmf = SG / "GrokMediaFormat"
    py_parts = [str(root)]
    if gmf.is_dir():
        py_parts.append(str(gmf))
    py = os.pathsep.join(py_parts)
    if os.environ.get("PYTHONPATH"):
        py = py + os.pathsep + os.environ["PYTHONPATH"]
    return {
        **os.environ,
        "SG_ROOT": str(SG),
        "FINAL_EYE_ROOT": str(root),
        "QUEEN_ROOT": str(q),
        "HOSTESS7_ROOT": str(hostess),
        "NEXUS_INSTALL_ROOT": os.environ.get("NEXUS_INSTALL_ROOT", str(q.parent)),
        "FINAL_EYE_ASSIST": os.environ.get("FINAL_EYE_ASSIST", "1"),
        "FINAL_EYE_LOW_END": os.environ.get("FINAL_EYE_LOW_END", "1"),
        "FINAL_EYE_COOL": os.environ.get("FINAL_EYE_COOL", "1"),
        "FINAL_EYE_PORT": os.environ.get("FINAL_EYE_PORT", "9479"),
        "PYTHONPATH": py,
    }


def import_final_eye() -> Path:
    """Insert Final_Eye on sys.path; return root."""
    env = final_eye_env()
    root = Path(env["FINAL_EYE_ROOT"])
    for part in env.get("PYTHONPATH", "").split(os.pathsep):
        if part and part not in sys.path:
            sys.path.insert(0, part)
    return root


def final_eye_version() -> dict[str, Any]:
    import_final_eye()
    from zocr_product import product_info
    return product_info()


def _run(script: Path, *args: str, timeout: int = 120) -> dict[str, Any]:
    root = final_eye_root()
    if not script.is_file():
        return {"ok": False, "error": f"missing {script}", "final_eye_root": str(root)}
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=final_eye_env(queen=QUEEN),
    )
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        doc = {"ok": False, "tail": (proc.stdout or "")[-2000:]}
    doc["returncode"] = proc.returncode
    doc["final_eye_root"] = str(root)
    doc["product"] = "Final_Eye"
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    """Final_Eye + eyeball dispatch — OCR, watch, smoke, teach."""
    root = final_eye_root()
    eye_py = root / "zocr.py"
    eye_watch = root / "zocr_watch.py"
    forge_watch = root / "queen_forge_watch.py"
    smoke = root / "queen_browser_smoke.py"
    eyeball = QUEEN / "lib" / "queen-eyeball.py"

    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "json"):
        return _run(eye_py, "status")
    if action in ("live", "live-status", "live_status"):
        return _run(eye_py, "live")
    if action in ("look", "poll", "vision-poll", "watch"):
        if forge_watch.is_file():
            return _run(forge_watch, "once", "queen_final_eye_watch")
        return _run(eye_watch, "look")
    if action in ("forge-watch", "forge_watch", "hangup-watch"):
        return _run(forge_watch if forge_watch.is_file() else eye_watch, "once", "queen_forge_watch")
    if action in ("observe", "robotics"):
        return _run(eye_watch, "observe")
    if action == "capabilities":
        return _run(eye_watch, "capabilities")
    if action in ("smoke", "browser-smoke", "browser_smoke", "queen-smoke", "final-eye-smoke"):
        return _run(smoke)
    if action == "ocr" and body.get("image"):
        return _run(eye_py, "ocr", str(body["image"]))
    if action in ("eyeball", "eyeball-status", "final-eye"):
        return _run(eyeball, "json")
    if action in ("eyeball-arm", "arm-dishes"):
        mode = str(body.get("mode") or ("dishes" if action == "arm-dishes" else "dishes"))
        return _run(eyeball, "arm", mode)
    if action in ("eyeball-verify", "eyeball-verify-hostess"):
        return _run(eyeball, "verify")
    if action in ("eyeball-weaponize", "weaponize-eyeball"):
        mode = str(body.get("mode") or "war")
        return _run(eyeball, "weaponize", mode)
    if action in ("bench-low-end", "eyeball-bench"):
        return _run(eyeball, "bench")
    if action in ("teach", "teach-doctrine"):
        return _run(eyeball, "dispatch")
    if action in ("plate-meld", "plate_meld"):
        meld_py = QUEEN.parent / "lib" / "eye-ear-plate.py"
        if meld_py.is_file():
            proc = subprocess.run(
                [sys.executable, str(meld_py), "meld"],
                capture_output=True,
                text=True,
                timeout=60,
                env=final_eye_env(queen=QUEEN),
            )
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError:
                return {"ok": proc.returncode == 0, "tail": (proc.stdout or "")[-2000:]}
        return {"ok": False, "error": "eye-ear-plate.py missing"}
    return {"ok": False, "error": "unknown_action", "product": "Final_Eye"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    root = final_eye_root()
    eye_py = root / "zocr.py"
    eye_watch = root / "zocr_watch.py"
    smoke = root / "queen_browser_smoke.py"
    if cmd in ("smoke", "browser-smoke", "final-eye-smoke"):
        print(json.dumps(_run(smoke), ensure_ascii=False))
        return 0
    if cmd in ("live", "live-status"):
        print(json.dumps(_run(eye_py, "live"), ensure_ascii=False))
        return 0
    if cmd in ("look", "poll", "watch", "vision"):
        print(json.dumps(_run(eye_watch, "look"), ensure_ascii=False))
        return 0
    if cmd in ("observe", "robotics"):
        print(json.dumps(_run(eye_watch, "observe"), ensure_ascii=False))
        return 0
    print(json.dumps(_run(eye_py, "status"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())