#!/usr/bin/env pythong
"""G1ID immoveable baselines — secure sealed this_one anchors for NewLatest."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "g1id-baseline-doctrine.json"
MANIFEST = INSTALL / "data" / "g1id-baseline-manifest.json"
BASELINES_DIR = INSTALL / "data" / "baselines"
PANEL = STATE / "g1id-baseline-panel.json"
LEDGER = STATE / "g1id-baseline-ledger.jsonl"
IMMOVEABLE_MODE = 0o444
MELD_CITATION = "ironclad:meld:2"

_G1ID_MOD = None
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


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        py = Path(__file__).resolve().parent / "sovereign-clock.py"
        spec = importlib.util.spec_from_file_location("sovereign_clock_baseline", py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _SOVEREIGN_CLOCK_MOD = mod
    if _SOVEREIGN_CLOCK_MOD and hasattr(_SOVEREIGN_CLOCK_MOD, "utc_z"):
        return _SOVEREIGN_CLOCK_MOD.utc_z("g1id_baseline")
    return ""


def _g1id() -> Any | None:
    global _G1ID_MOD
    if _G1ID_MOD is not None:
        return _G1ID_MOD
    py = Path(__file__).resolve().parent / "g1id-format.py"
    if not py.is_file():
        py = INSTALL / "lib" / "g1id-format.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("g1id_format_baseline", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _G1ID_MOD = mod
    return mod


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass
    except OSError:
        pass


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _resolve_baseline_path(entry: dict[str, Any]) -> Path:
    rel = str(entry.get("path") or "").strip()
    if not rel:
        bid = str(entry.get("id") or "baseline")
        rel = f"data/baselines/{bid}.g1id"
    p = Path(rel)
    if p.is_absolute():
        return p
    return INSTALL / rel


def _file_mode_ok(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    try:
        mode = path.stat().st_mode & 0o777
        if mode & stat.S_IWUSR or mode & stat.S_IWGRP or mode & stat.S_IWOTH:
            return False, f"writable:{oct(mode)}"
        return True, oct(mode)
    except OSError as exc:
        return False, str(exc)


def _enforce_immoveable(path: Path) -> dict[str, Any]:
    """chmod 0444; optional chattr +i when permitted."""
    result: dict[str, Any] = {"path": str(path), "mode_target": oct(IMMOVEABLE_MODE)}
    try:
        os.chmod(path, IMMOVEABLE_MODE)
        result["chmod_ok"] = True
        result["mode"] = oct(path.stat().st_mode & 0o777)
    except OSError as exc:
        result["chmod_ok"] = False
        result["chmod_error"] = str(exc)
    if os.environ.get("NEXUS_G1ID_CHATTR_IMMUTABLE", "1") == "1":
        try:
            proc = subprocess.run(
                ["chattr", "+i", str(path)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            result["chattr_ok"] = proc.returncode == 0
            if proc.returncode != 0:
                result["chattr_note"] = (proc.stderr or proc.stdout or "").strip()[:200]
        except (OSError, subprocess.TimeoutExpired) as exc:
            result["chattr_ok"] = False
            result["chattr_note"] = str(exc)
    result["immoveable"] = bool(result.get("chmod_ok"))
    return result


def manifest_entries() -> list[dict[str, Any]]:
    doc = _load(MANIFEST, {})
    return [b for b in (doc.get("baselines") or []) if isinstance(b, dict)]


def verify_baseline(
    path: Path | str,
    *,
    require_immoveable: bool = True,
    verify_plate: bool = True,
) -> dict[str, Any]:
    """Cold verify one baseline .g1id — integrity, meld, immoveable mode."""
    p = Path(path)
    g1 = _g1id()
    if not g1:
        return {"ok": False, "error": "g1id_format_missing", "path": str(p)}
    try:
        read = g1.read_file(p, verify_plate=verify_plate)
        if not read.get("ok"):
            return {"ok": False, "path": str(p), "read": read}
        doc = read.get("document") or {}
        baseline = doc.get("baseline") or {}
        mode_ok, mode_detail = _file_mode_ok(p)
        errors: list[str] = []
        if not baseline.get("immoveable"):
            errors.append("baseline_not_immoveable")
        if require_immoveable and not mode_ok:
            errors.append(f"file_not_readonly:{mode_detail}")
        verdict = read.get("validate") or {}
        if not verdict.get("ok"):
            errors.extend(verdict.get("errors") or [])
        return {
            "ok": len(errors) == 0,
            "path": str(p),
            "id": (doc.get("self") or {}).get("id"),
            "payload_hash": (doc.get("integrity") or {}).get("payload_hash"),
            "linear_ns": ((doc.get("meld_inputs") or {}).get("sovereign_time") or {}).get("linear_ns"),
            "immoveable": bool(baseline.get("immoveable")),
            "mode_ok": mode_ok,
            "mode": mode_detail,
            "errors": errors,
            "validate": verdict,
        }
    except Exception as exc:
        return {"ok": False, "path": str(p), "error": str(exc)}


def verify_all(*, require_immoveable: bool = True) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for entry in manifest_entries():
        p = _resolve_baseline_path(entry)
        row = verify_baseline(p, require_immoveable=require_immoveable)
        row["manifest_id"] = entry.get("id")
        row["required"] = bool(entry.get("required"))
        rows.append(row)
    required = [r for r in rows if r.get("required")]
    ok = all(r.get("ok") for r in required) if required else all(r.get("ok") for r in rows)
    return {
        "schema": "g1id-baseline-verify/v1",
        "updated": _now(),
        "ok": ok,
        "count": len(rows),
        "required_ok": all(r.get("ok") for r in required) if required else True,
        "baselines": rows,
        "meld_citation": MELD_CITATION,
    }


def seal_baseline(
    *,
    baseline_id: str,
    label: str = "",
    extents: dict[str, float],
    centroid: dict[str, float] | None = None,
    units: str = "m",
    force: bool = False,
) -> dict[str, Any]:
    """Seal one immoveable baseline — sovereign time meld, chmod 0444."""
    g1 = _g1id()
    if not g1:
        return {"ok": False, "error": "g1id_format_missing"}
    bid = str(baseline_id).strip()[:128]
    if not bid:
        return {"ok": False, "error": "baseline_id_required"}
    BASELINES_DIR.mkdir(parents=True, exist_ok=True)
    out = BASELINES_DIR / f"{bid}.g1id"
    if out.is_file() and not force:
        mode_ok, _ = _file_mode_ok(out)
        if mode_ok:
            return {
                "ok": False,
                "error": "baseline_immoveable_exists",
                "path": str(out),
                "hint": "use force=True to re-seal with new sovereign time receipt",
            }
    if out.is_file() and force:
        try:
            os.chmod(out, 0o644)
            if os.environ.get("NEXUS_G1ID_CHATTR_IMMUTABLE", "1") == "1":
                subprocess.run(["chattr", "-i", str(out)], capture_output=True, timeout=5, check=False)
        except OSError:
            pass
    try:
        doc = g1.build_document(
            self_id=bid,
            label=label or f"Baseline — {bid}",
            extents=extents,
            centroid=centroid,
            units=units,
            baseline=True,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    verdict = g1.validate(doc, verify_plate=False)
    if not verdict.get("ok"):
        return {"ok": False, "error": "precheck_failed", "validate": verdict}
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    tmp = out.with_suffix(".g1id.tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, out)
    imm = _enforce_immoveable(out)
    row = {
        "ts": _now(),
        "event": "seal_baseline",
        "id": bid,
        "path": str(out),
        "payload_hash": (doc.get("integrity") or {}).get("payload_hash"),
        "linear_ns": ((doc.get("meld_inputs") or {}).get("sovereign_time") or {}).get("linear_ns"),
        "immoveable": imm,
        "force": force,
    }
    _append_ledger(row)
    return {
        "ok": True,
        "id": bid,
        "path": str(out),
        "integrity": doc.get("integrity"),
        "meld_inputs": doc.get("meld_inputs"),
        "immoveable": imm,
        "validate": g1.validate(doc, verify_plate=False),
    }


def seal_manifest(*, force: bool = False) -> dict[str, Any]:
    """Seal every baseline declared in install manifest."""
    sealed: list[dict[str, Any]] = []
    defaults = {
        "operator-this-one": {
            "label": "Operator — this one geometric baseline",
            "extents": {"x": 0.45, "y": 0.28, "z": 1.72},
            "centroid": {"x": 0.0, "y": 0.0, "z": 0.86},
        },
    }
    for entry in manifest_entries():
        bid = str(entry.get("id") or "")
        spec = defaults.get(bid, {})
        out = seal_baseline(
            baseline_id=bid,
            label=str(entry.get("label") or spec.get("label") or bid),
            extents=spec.get("extents") or {"x": 1.0, "y": 1.0, "z": 1.0},
            centroid=spec.get("centroid"),
            force=force,
        )
        sealed.append(out)
    verify = verify_all()
    return {
        "schema": "g1id-baseline-seal/v1",
        "updated": _now(),
        "ok": verify.get("ok") and all(s.get("ok") for s in sealed),
        "sealed": sealed,
        "verify": verify,
        "meld_citation": MELD_CITATION,
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    verify = verify_all()
    manifest = _load(MANIFEST, {})
    panel = {
        "schema": "g1id-baseline-panel/v1",
        "updated": _now(),
        "title": manifest.get("title") or "G1ID immoveable baselines",
        "meld_citation": MELD_CITATION,
        "policy": (manifest.get("policy") or (_load(DOCTRINE, {}).get("policy") or {})),
        "ok": verify.get("ok"),
        "count": verify.get("count"),
        "required_ok": verify.get("required_ok"),
        "baselines": verify.get("baselines"),
        "manifest_ref": str(MANIFEST.relative_to(INSTALL)) if MANIFEST.is_file() else None,
        "doctrine_ref": str(DOCTRINE.relative_to(INSTALL)) if DOCTRINE.is_file() else None,
    }
    if write:
        _save(PANEL, panel)
    return panel


def melded_extension_slice() -> dict[str, Any]:
    panel = build_panel(write=False)
    return {
        "id": "g1id_baselines",
        "absorbed": DOCTRINE.is_file() and MANIFEST.is_file(),
        "meld_citation": MELD_CITATION,
        "citation": "ironclad:g1id:2",
        "ok": panel.get("ok"),
        "count": panel.get("count"),
        "required_ok": panel.get("required_ok"),
        "immoveable_policy": True,
        "sovereign_time_meld": True,
        "updated": panel.get("updated"),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "verify":
        path = sys.argv[2] if len(sys.argv) > 2 else ""
        if path:
            out = verify_baseline(path)
        else:
            out = verify_all()
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd == "seal":
        force = "--force" in sys.argv
        if len(sys.argv) > 2 and sys.argv[2] not in ("--force",):
            bid = sys.argv[2]
            label = sys.argv[3] if len(sys.argv) > 3 else bid
            x = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
            y = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
            z = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
            out = seal_baseline(baseline_id=bid, label=label, extents={"x": x, "y": y, "z": z}, force=force)
        else:
            out = seal_manifest(force=force)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd == "slice":
        print(json.dumps(melded_extension_slice(), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: g1id-baseline.py [json|verify [PATH]|seal [ID LABEL X Y Z] [--force]|slice]",
        "doctrine": str(DOCTRINE),
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())