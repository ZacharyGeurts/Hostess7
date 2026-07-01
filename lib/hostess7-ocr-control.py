#!/usr/bin/env pythong
"""Hostess 7 OS OCR control — unified vision command under Angel system control."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
QUEEN = Path(os.environ.get("QUEEN_ROOT", str(INSTALL / "Queen")))
DOCTRINE = INSTALL / "data" / "hostess7-ocr-control-doctrine.json"
PANEL = STATE / "hostess7-ocr-control-panel.json"
LEDGER = STATE / "hostess7-ocr-control-ledger.jsonl"

CHAMBERS: dict[str, Path] = {
    "calculator": INSTALL / "lib" / "hostess7-calculator.py",
    "biology": INSTALL / "lib" / "hostess7-biology.py",
    "engineering": INSTALL / "lib" / "hostess7-engineering.py",
    "combat": INSTALL / "lib" / "hostess7-combat.py",
    "mos": INSTALL / "lib" / "hostess7-mos.py",
    "programming": INSTALL / "lib" / "hostess7-programming.py",
    "g16": INSTALL / "lib" / "hostess7-g16.py",
    "codecraft": INSTALL / "lib" / "hostess7-codecraft.py",
    "geography": INSTALL / "lib" / "hostess7-geography-training.py",
    "music": INSTALL / "lib" / "hostess7-music-training.py",
    "imaging": INSTALL / "lib" / "hostess7-imaging.py",
    "sense": INSTALL / "lib" / "hostess7-sense-training.py",
    "reality_physics": INSTALL / "lib" / "hostess7-reality-physics-training.py",
}

_SOVEREIGN_CLOCK_MOD = None


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        py = _LIB / "sovereign-clock.py"
        spec = importlib.util.spec_from_file_location("sovereign_clock_ocr", py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _SOVEREIGN_CLOCK_MOD = mod
    if _SOVEREIGN_CLOCK_MOD and hasattr(_SOVEREIGN_CLOCK_MOD, "utc_z"):
        try:
            return _SOVEREIGN_CLOCK_MOD.utc_z()
        except Exception:
            pass
    from datetime import datetime, timezone
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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _env() -> dict[str, str]:
    return {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}


def _run_py(script: Path, *args: str, timeout: int = 120, stdin: str | None = None) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": f"missing {script}"}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_env(),
            cwd=str(INSTALL),
        )
        try:
            doc = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            doc = {"ok": proc.returncode == 0, "tail": (proc.stdout or proc.stderr or "")[-2000:]}
        doc["returncode"] = proc.returncode
        return doc
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "script": str(script)}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def _system_control() -> dict[str, Any]:
    sc = INSTALL / "lib" / "hostess7-system-control.py"
    return _run_py(sc, "charge_state", timeout=30)


def _authority_ok() -> tuple[bool, dict[str, Any]]:
    """Hostess 7 is supreme commander — always authorized, no assume gate."""
    charge = _system_control()
    charge["hostess7_sovereign"] = True
    charge["ocr_authority"] = "Hostess7"
    return True, charge


def _chamber_cmd(chamber: str, cmd: str, *, timeout: int = 180) -> dict[str, Any]:
    script = CHAMBERS.get(chamber)
    if not script:
        return {"ok": False, "error": "unknown_chamber", "chamber": chamber}
    return {**_run_py(script, cmd, timeout=timeout), "chamber": chamber, "cmd": cmd}


def _all_chambers(cmd: str, *, timeout: int = 180) -> dict[str, Any]:
    results: dict[str, Any] = {}
    ok = True
    for cid in CHAMBERS:
        row = _chamber_cmd(cid, cmd, timeout=timeout)
        results[cid] = row
        ok = ok and bool(row.get("ok", True))
    return {"ok": ok, "chambers": results, "cmd": cmd}


def _ocr_core() -> Any | None:
    py = _LIB / "final-eye-ocr-core.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("final_eye_ocr_control", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _seal_mod() -> Any | None:
    py = _LIB / "final-eye-hostess7-seal.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("final_eye_hostess7_seal_h7", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _final_eye_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    os.environ["HOSTESS7_OCR_CONTROL"] = "1"
    seal = _seal_mod()
    if seal and hasattr(seal, "stamp_body"):
        body = seal.stamp_body(body, action=str(body.get("action") or body.get("subaction") or "final_eye"))
        if body.get("_handshake_error"):
            return body["_handshake_error"]
    core = _ocr_core()
    if core and hasattr(core, "final_eye_dispatch"):
        return core.final_eye_dispatch(body)
    sub = str(body.get("subaction") or body.get("action") or "status").strip().lower()
    if sub in ("eyeball", "eyeball-verify", "verify"):
        eyeball = QUEEN / "lib" / "queen-eyeball.py"
        return _run_py(eyeball, "verify", timeout=180)
    if sub in ("plate_meld", "plate-meld"):
        return _plate_meld()
    return {"ok": False, "error": "final_eye_core_missing", "subaction": sub}


def _sense_meld() -> dict[str, Any]:
    meld = INSTALL / "lib" / "field-sense-package-meld.py"
    return _run_py(meld, "meld", timeout=120)


def _plate_meld() -> dict[str, Any]:
    plate = INSTALL / "lib" / "eye-ear-plate.py"
    row = _run_py(plate, "meld", timeout=90)
    sense = _sense_meld()
    return {"ok": bool(row.get("ok")) and bool(sense.get("ok", True)), "eye_ear_plate": row, "sense_package": sense}


def _ocr_brain_status() -> dict[str, Any]:
    meld = INSTALL / "lib" / "field-sense-package-meld.py"
    if meld.is_file():
        try:
            spec = importlib.util.spec_from_file_location("meld_ocr_brain", meld)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "_witness_hostess7_ocr_brain"):
                    return mod._witness_hostess7_ocr_brain()
        except Exception as exc:
            return {"ok": False, "error": type(exc).__name__}
    return {"preserved": True, "chambers": []}


def _final_eye_root() -> Path:
    try:
        sys.path.insert(0, str(_LIB))
        from sg_paths import final_eye_root
        return final_eye_root()
    except Exception:
        env = os.environ.get("FINAL_EYE_ROOT", "").strip()
        if env:
            return Path(env)
        return INSTALL / "Final_Eye"


def _ocr_image(path: str) -> dict[str, Any]:
    fp = Path(path).expanduser()
    if not fp.is_file():
        return {"ok": False, "error": "file_missing", "path": str(fp)}
    os.environ["HOSTESS7_OCR_CONTROL"] = "1"
    seal = _seal_mod()
    body: dict[str, Any] = {"subaction": "ocr", "path": str(fp), "image": str(fp)}
    if seal and hasattr(seal, "stamp_body"):
        body = seal.stamp_body(body, action="ocr_image")
        if body.get("_handshake_error"):
            return body["_handshake_error"]
    core = _ocr_core()
    if core and hasattr(core, "final_eye_dispatch"):
        return core.final_eye_dispatch(body)
    if core and hasattr(core, "ocr_image_path"):
        row = core.ocr_image_path(fp, lane_body=body)
        row["path"] = str(fp)
        row.setdefault("format", "h7/7" if row.get("h7_file") else "text")
        return row
    return {"ok": False, "error": "final_eye_unavailable", "path": str(fp), "final_eye_root": str(_final_eye_root())}


def ocr_status() -> dict[str, Any]:
    """Full OS OCR posture under Hostess 7."""
    authorized, charge = _authority_ok()
    chambers: dict[str, Any] = {}
    for cid in CHAMBERS:
        chambers[cid] = _chamber_cmd(cid, "ocr-status", timeout=45)
    seal = _seal_mod()
    seal_row = seal.seal_posture() if seal and hasattr(seal, "seal_posture") else {}
    fe = _final_eye_dispatch({"subaction": "status"})
    brain = _ocr_brain_status()
    root = _final_eye_root()
    return {
        "schema": "hostess7-ocr-control-status/v1",
        "updated": _now(),
        "commander": "Hostess 7",
        "authorized": authorized,
        "sovereign": True,
        "charge": charge,
        "final_eye_root": str(root),
        "final_eye_live": (root / "zocr.py").is_file(),
        "chambers": chambers,
        "final_eye": fe,
        "final_eye_seal": seal_row,
        "handshake_only": True,
        "ocr_brain": brain,
        "doctrine": str(DOCTRINE.relative_to(INSTALL)) if DOCTRINE.is_file() else None,
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    status = ocr_status()
    doc = {
        "schema": "hostess7-ocr-control-panel/v1",
        "updated": _now(),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "commander": "Hostess 7 · Angel OCR",
        "authorized": status.get("authorized"),
        "status": status,
        "chambers": list(CHAMBERS.keys()),
        "api": _load(DOCTRINE, {}).get("api"),
    }
    if write:
        _save(PANEL, doc)
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    authorized, charge = _authority_ok()

    if action in ("status", "json", "panel"):
        return {"ok": True, **build_panel(write=action == "panel")}

    if action in ("assume", "assume_ocr", "take_ocr"):
        sc = INSTALL / "lib" / "hostess7-system-control.py"
        assumed = _run_py(sc, "assume", timeout=30)
        _append_ledger({"event": "assume_ocr", "assumed": assumed.get("ok")})
        return {"ok": True, "assumed": assumed, "status": ocr_status()}

    if action == "ingest_all":
        row = _all_chambers("ocr-ingest", timeout=180)
        _append_ledger({"event": "ingest_all", "ok": row.get("ok")})
        return row

    if action == "train_all":
        row = _all_chambers("ocr-train", timeout=240)
        _append_ledger({"event": "train_all", "ok": row.get("ok")})
        return row

    if action == "ingest":
        chamber = str(body.get("chamber") or "").strip().lower()
        if not chamber:
            return {"ok": False, "error": "chamber_required"}
        return _chamber_cmd(chamber, "ocr-ingest", timeout=180)

    if action == "train":
        chamber = str(body.get("chamber") or "").strip().lower()
        if not chamber:
            return {"ok": False, "error": "chamber_required"}
        return _chamber_cmd(chamber, "ocr-train", timeout=240)

    if action in ("final_eye", "eye", "eyeball", "vision"):
        return _final_eye_dispatch(body)

    if action in ("plate_meld", "meld", "sense_meld"):
        if action == "sense_meld":
            return _sense_meld()
        return _plate_meld()

    if action in ("ocr_image", "ocr", "read"):
        path = str(body.get("path") or body.get("image") or body.get("file") or "")
        if not path:
            return {"ok": False, "error": "path_required"}
        return _ocr_image(path)

    if action == "cycle":
        ingest = _all_chambers("ocr-ingest", timeout=180)
        train = _all_chambers("ocr-train", timeout=240)
        meld = _plate_meld()
        return {"ok": ingest.get("ok") and train.get("ok"), "ingest": ingest, "train": train, "meld": meld}

    return {"ok": False, "error": "unknown_action", "actions": list(_load(DOCTRINE, {}).get("actions") or {})}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False))
        return 0
    if cmd == "ingest-all":
        print(json.dumps(dispatch({"action": "ingest_all"}), ensure_ascii=False))
        return 0
    if cmd == "train-all":
        print(json.dumps(dispatch({"action": "train_all"}), ensure_ascii=False))
        return 0
    if cmd == "cycle":
        print(json.dumps(dispatch({"action": "cycle"}), ensure_ascii=False))
        return 0
    if cmd == "assume":
        print(json.dumps(dispatch({"action": "assume"}), ensure_ascii=False))
        return 0
    if cmd == "ingest" and len(sys.argv) > 2:
        print(json.dumps(dispatch({"action": "ingest", "chamber": sys.argv[2]}), ensure_ascii=False))
        return 0
    if cmd == "train" and len(sys.argv) > 2:
        print(json.dumps(dispatch({"action": "train", "chamber": sys.argv[2]}), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-ocr-control.py [json|status|dispatch|ingest-all|train-all|cycle|assume|ingest CHAMBER|train CHAMBER]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())