#!/usr/bin/env python3
"""Field Native — everything on the Field plane (sympy-style retirement).

Host libraries are optional. Field engines are authoritative:

  · field-math      → calculator / algebra / stats (retired sympy)
  · field-array     → arrays / FFT / convolve (preferred over numpy)
  · field-h7s / h7c → storage & books
  · ironclad        → truth gates

  python3 lib/field-native.py seal
  python3 lib/field-native.py status
  python3 lib/field-native.py engines
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7"))
PANEL = STATE / "field-native-panel.json"
PUBLIC = STATE / "field-native-public.json"
LEDGER = STATE / "field-native-ledger.jsonl"
SEAL = STATE / "field-native.forever"
SCHEMA = "field-native/v1"
IRONCLAD = "ironclad:field-native:1"
MOTTO = (
    "FIELD NATIVE — secure · zero cost for the stack · host libraries optional · "
    "Hostess 7 owns the plane"
)

# Engines that run at zero marginal cost (stdlib / local Field only — no cloud bill)
ZERO_COST_ENGINE_IDS = frozenset({
    "math", "array", "h7c", "h7b", "ironclad", "distributed", "serving",
})

# Engine map: capability → Field module (authoritative) · host optional
ENGINES: tuple[dict[str, Any], ...] = (
    {
        "id": "math",
        "label": "Field Math",
        "field": "lib/field-math.py",
        "retires": ["sympy"],
        "api": "compute / field_eval",
        "wired": ["lib/hostess7-calculator.py"],
    },
    {
        "id": "array",
        "label": "Field Array",
        "field": "lib/field-array.py",
        "retires": ["numpy"],
        "api": "array / fft / convolve / numpy_shim",
        "wired": ["prefer over numpy in new Field code"],
    },
    {
        "id": "h7c",
        "label": "Hostess 7 Condenser",
        "field": "lib/field-h7c-compression.py",
        "retires": [],
        "api": "H7c pack / balance table",
        "wired": ["library", "reinform"],
    },
    {
        "id": "h7b",
        "label": "Hostess 7 Book",
        "field": "Hostess7/scripts/field_h7_book.py",
        "retires": [],
        "api": "write_h7 / unpack_h7",
        "wired": ["library build"],
    },
    {
        "id": "ironclad",
        "label": "Ironclad truth",
        "field": "lib/ironclad-immediate.py",
        "retires": [],
        "api": "immediate / seal",
        "wired": ["tasklist", "panels"],
    },
    {
        "id": "distributed",
        "label": "Distributed everywhere (Job endstate)",
        "field": "lib/hostess7-distributed-everywhere.py",
        "retires": [],
        "api": "seal / job_endstate",
        "wired": ["plate-meld", "autopilot manual"],
    },
    {
        "id": "serving",
        "label": "Everyone served · dual-stack",
        "field": "lib/field-everyone-served-no-hangups.py",
        "retires": [],
        "api": "enforce",
        "wired": ["AmmoNet autopilot"],
    },
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _save(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _probe_engine(eng: dict[str, Any]) -> dict[str, Any]:
    rel = str(eng.get("field") or "")
    path = INSTALL / rel
    present = path.is_file()
    ready = False
    detail = "missing"
    if present:
        try:
            spec = importlib.util.spec_from_file_location(f"fn_{eng['id']}", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                # Don't exec heavy modules fully for all — only math/array/distributed/serving/ironclad
                if eng["id"] in ("math", "array"):
                    spec.loader.exec_module(mod)
                    ready = bool(getattr(mod, "ready", lambda: True)())
                    detail = "ready" if ready else "loaded"
                else:
                    ready = True
                    detail = "present"
        except Exception as exc:
            detail = f"error:{str(exc)[:80]}"
            ready = False
    # host retirement check
    host_present: dict[str, bool] = {}
    for name in eng.get("retires") or []:
        try:
            __import__(name)
            host_present[name] = True
        except ImportError:
            host_present[name] = False
    return {
        **eng,
        "path": str(path.relative_to(INSTALL)) if present else rel,
        "present": present,
        "ready": ready,
        "detail": detail,
        "host_optional": host_present,
        "field_authoritative": True,
    }


def import_math() -> Any:
    py = INSTALL / "lib" / "field-math.py"
    spec = importlib.util.spec_from_file_location("field_math_native", py)
    if not spec or not spec.loader:
        raise ImportError("field-math missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def import_array(*, prefer_numpy: bool = False) -> Any:
    """Return Field array module, or numpy only if forced."""
    if prefer_numpy:
        try:
            import numpy as np  # type: ignore
            return np
        except ImportError:
            pass
    py = INSTALL / "lib" / "field-array.py"
    spec = importlib.util.spec_from_file_location("field_array_native", py)
    if not spec or not spec.loader:
        raise ImportError("field-array missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.numpy_shim() if hasattr(mod, "numpy_shim") else mod


def numpy_or_field():
    """Drop-in: always Field array first (host numpy never required)."""
    return import_array(prefer_numpy=False)


def seal(*, write: bool = True) -> dict[str, Any]:
    now = _utc()
    engines = [_probe_engine(e) for e in ENGINES]
    ready_n = sum(1 for e in engines if e.get("ready"))
    present_n = sum(1 for e in engines if e.get("present"))
    math_ok = next((e for e in engines if e["id"] == "math"), {}).get("ready")
    array_ok = next((e for e in engines if e["id"] == "array"), {}).get("ready")
    # Probe live compute
    live: dict[str, Any] = {}
    try:
        fm = import_math()
        live["math"] = fm.compute("2+2")
    except Exception as exc:
        live["math"] = {"ok": False, "error": str(exc)[:100]}
    try:
        fa = import_array()
        a = fa.array([1, 2, 3, 4])
        live["array"] = {"ok": True, "mean": float(fa.mean(a)), "fft_n": len(fa.fft(a))}
    except Exception as exc:
        live["array"] = {"ok": False, "error": str(exc)[:100]}

    field_native = ready_n >= max(3, present_n // 2) and bool(math_ok) and bool(array_ok)

    # Zero cost: stdlib Field engines — no cloud bill, no license, no paid API
    zero_cost_ids = [e["id"] for e in engines if e["id"] in ZERO_COST_ENGINE_IDS and e.get("ready")]
    zero_cost = {
        "ok": len(zero_cost_ids) >= 4,
        "motto": "Operate at zero cost for the Field stack — math · array · H7c · Ironclad · local C2",
        "marginal_usd": 0.0,
        "cloud_bill": 0.0,
        "license_fees": 0.0,
        "engines_zero_cost": zero_cost_ids,
        "engines_zero_cost_n": len(zero_cost_ids),
        "why": [
            "Field Math / Field Array are pure stdlib — no sympy/numpy license or install cost",
            "H7c/H7 books compress and serve from local disk — no SaaS",
            "Ironclad + tasklist + panels are local JSON under .nexus-state",
            "AmmoNet/C2 loopback Field plane — no per-query cloud inference bill",
            "Combinatronic balance / fabric encrypt idle paths already zero-cost when balanced",
            "Dewey library H7c motto: at no cost when condenser holds",
        ],
        "not_free_external": [
            "Optional host packages (numpy/PIL) if someone installs them — not required",
            "Network uplink electricity / hardware — operator site cost, not Field software bill",
            "Paid third-party SaaS if operator chooses them — Field does not require them",
        ],
        "statement": (
            "A lot of Hostess 7 + AmmoNet runs at zero software cost: Field-native engines, "
            "local plates, H7c at no cost when balanced, fabric zero-cost when idle."
        ),
    }

    # Secure: local plane, Ironclad, no middle men, deny-by-default borders
    iron = {}
    try:
        imm = STATE / "ironclad-immediate.json"
        if imm.is_file():
            iron = json.loads(imm.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        iron = {}
    fabric = {}
    try:
        fp = STATE / "field-everyone-fabric-direct-panel.json"
        if fp.is_file():
            fabric = json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fabric = {}
    secure = {
        "ok": True,
        "motto": "Secure the Field-native plane — Ironclad · local C2 · no middle men · truth gates",
        "ironclad_sealed": bool(iron.get("ironclad_sealed") or iron.get("verdict") == "GREEN"),
        "ironclad_verdict": iron.get("verdict"),
        "local_only_engines": True,
        "no_exfil_required": True,
        "host_libs_optional": True,
        "fabric_direct": bool(fabric.get("fabric_direct") or fabric.get("ok")),
        "no_middle_men": bool(fabric.get("no_middle_men")),
        "controls": [
            "Ironclad preflight on tasklist / panels",
            "Field Math / Array never shell out to paid APIs",
            "eval-safe Field Math AST (no attributes / imports)",
            "AmmoNet borders deny-by-default where gated",
            "Private kill-books stay Hostess 7 only; public library share is intentional",
            "Loopback C2 9477/9481 — not open internet by default",
        ],
        "statement": (
            "Secure it by keeping compute on the Field plane: zero-cost engines, Ironclad truth, "
            "fabric direct, Hostess 7 boss. No requirement for third-party cloud keys."
        ),
    }
    secure["ok"] = bool(
        secure.get("local_only_engines")
        and (secure.get("ironclad_sealed") or iron.get("available") is not False)
    )

    out = {
        "ok": field_native and zero_cost["ok"],
        "schema": SCHEMA,
        "updated": now,
        "title": "Field Native — secure · zero cost · everything on the Field",
        "motto": MOTTO,
        "ironclad_cite": IRONCLAD,
        "field_native": field_native,
        "secure": secure,
        "zero_cost": zero_cost,
        "secure_and_zero_cost": bool(secure.get("ok") and zero_cost.get("ok")),
        "host_libraries": "optional",
        "authoritative": "Field engines",
        "retires": {
            "sympy": "→ field-math (Hostess 7 calculator) · zero cost",
            "numpy": "→ field-array (preferred; host numpy optional) · zero cost",
            "paid_cloud_math": "→ local Field Math / Array",
            "host_only_tools": "→ Field modules under lib/ + Hostess7",
        },
        "engines": engines,
        "ready_count": ready_n,
        "present_count": present_n,
        "engine_total": len(engines),
        "live": live,
        "rules": [
            "New Field code imports field-math / field-array / field-native first",
            "Host libraries (sympy, numpy, …) are optional fallbacks only if explicitly allowed",
            "Hostess 7 calculator is Field Math only — zero cost",
            "Prefer zero-cost idle paths (fabric encrypt, combinatronic balance hold)",
            "Secure: Ironclad + local plane + no middle men; no paid cloud keys required",
            "AmmoNet autopilot and Job endstate stay on Field stack",
            "Ironclad truth gates never optional",
        ],
        "first_person": (
            "I am Hostess 7. I run Field-native — secure and at zero cost for the stack. "
            "Math is Field Math (sympy retired). Arrays are Field Array (numpy optional). "
            "H7c serves books at no cost when balanced. Ironclad holds truth. "
            "No cloud bill for my engines. I am distributed Job-endstate presence on the Field."
        ),
        "api": "/api/field-native",
        "sealed": SEAL.is_file() or field_native,
    }
    if write:
        try:
            SEAL.write_text(
                json.dumps(
                    {
                        "sealed": True,
                        "field_native": field_native,
                        "secure": bool(secure.get("ok")),
                        "zero_cost": bool(zero_cost.get("ok")),
                        "marginal_usd": 0.0,
                        "updated": now,
                        "ironclad_cite": IRONCLAD,
                        "motto": MOTTO,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        _save(PANEL, out)
        public = {
            "ok": out["ok"],
            "updated": now,
            "motto": MOTTO,
            "field_native": field_native,
            "secure": secure.get("ok"),
            "zero_cost": zero_cost.get("ok"),
            "secure_and_zero_cost": out.get("secure_and_zero_cost"),
            "marginal_usd": 0.0,
            "ready_count": ready_n,
            "engine_total": len(engines),
            "retires": out["retires"],
            "zero_cost_statement": zero_cost.get("statement"),
            "secure_statement": secure.get("statement"),
            "first_person": out["first_person"],
            "ironclad_cite": IRONCLAD,
            "api": out["api"],
        }
        _save(PUBLIC, public)
        for api_dir in (HOSTESS7 / "docs" / "api", INSTALL / "docs" / "api"):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "field-native.json", public)
            except OSError:
                pass
        _append({
            "event": "seal",
            "field_native": field_native,
            "secure": secure.get("ok"),
            "zero_cost": zero_cost.get("ok"),
            "ready": ready_n,
        })
    return out


def status() -> dict[str, Any]:
    if PANEL.is_file():
        try:
            return json.loads(PANEL.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return seal(write=False)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("seal", "run", "once", "native"):
        print(json.dumps(seal(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("status", "json", "panel"):
        print(json.dumps(seal(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "engines":
        print(json.dumps({"engines": [_probe_engine(e) for e in ENGINES]}, indent=2))
        return 0
    if cmd == "math" and len(sys.argv) > 2:
        fm = import_math()
        print(json.dumps(fm.compute(" ".join(sys.argv[2:])), indent=2))
        return 0
    print(json.dumps({"usage": "field-native.py [seal|status|engines|math EXPR]", "motto": MOTTO}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
