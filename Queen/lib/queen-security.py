#!/usr/bin/env pythong
"""Queen native code seal — lib + forge integrity before gate release."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SEAL_PATH = QUEEN / "data" / "queen-code-seal.json"
_CODE_GLOBS = ("lib/*.py", "lib/forge/*.py", "lib/forge/**/*.py")
_PROTECTED = frozenset({
    "gate_release", "field_route", "field_sanity", "sovereign_dispatch", "compiler_probe",
    "browser_navigate", "sense_neural", "encourage", "external_wire", "secure_channel",
    "field_virus", "file_ingress", "file_egress", "credential_vault", "browser_import",
})


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _code_files() -> list[Path]:
    found: list[Path] = []
    for pattern in _CODE_GLOBS:
        for p in QUEEN.glob(pattern):
            try:
                p.resolve().relative_to(QUEEN.resolve())
            except ValueError:
                continue
            if p.is_file():
                found.append(p.resolve())
    return sorted(set(found))


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def seal_codebase() -> dict[str, Any]:
    files = {str(p.relative_to(QUEEN)): _hash_file(p) for p in _code_files()}
    mid = "QUEEN_FIELD_SECURITY_MANDATE_v1"
    chain = "|".join(f"{k}:{v}" for k, v in sorted(files.items()))
    root = hashlib.sha256(f"{mid}|{chain}".encode()).hexdigest()
    doc = {
        "schema": "queen-code-seal/v1",
        "mandate_id": mid,
        "ts": _ts(),
        "files": files,
        "file_count": len(files),
        "root_seal": root,
        "rule": "Queen lib + forge sealed — field-net and sovereign fail closed on tamper",
    }
    SEAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEAL_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def verify_code_seal() -> dict[str, Any]:
    if os.environ.get("QUEEN_SEAL_OFF", "").strip().lower() in ("1", "true", "yes"):
        return {"ok": True, "override": True, "reason": "QUEEN_SEAL_OFF"}
    if not SEAL_PATH.is_file():
        return {"ok": False, "reason": "seal_missing", "hint": "pythong lib/queen-security.py seal"}
    try:
        doc = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ok": False, "reason": "seal_corrupt"}
    sealed = doc.get("files") or {}
    current = {str(p.relative_to(QUEEN)): _hash_file(p) for p in _code_files()}
    errors = [r for r, e in sealed.items() if r in current and current[r] != e]
    missing = [r for r in sealed if r not in current]
    extra = [r for r in current if r not in sealed]
    ok = not errors and not missing
    return {
        "ok": ok,
        "mandate_id": doc.get("mandate_id"),
        "root_seal": doc.get("root_seal"),
        "file_count": len(sealed),
        "tampered": errors[:8],
        "missing": missing[:8],
        "unsealed_new": extra[:8],
        "ts": doc.get("ts"),
    }


def _root_mandate(operation: str) -> dict[str, Any] | None:
    if os.environ.get("SG_ROOT_SOVEREIGN_OFF", "").strip().lower() in ("1", "true", "yes"):
        return None
    try:
        from queen_root_sovereign import mandate_root  # type: ignore
    except ImportError:
        try:
            import importlib.util
            mod_path = Path(__file__).resolve().parent / "queen-root-sovereign.py"
            spec = importlib.util.spec_from_file_location("queen_root_sovereign", mod_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod.mandate_root(operation)  # type: ignore[attr-defined]
        except Exception:
            return None
    return mandate_root(operation)  # type: ignore[name-defined]


def _field_virus_mod() -> Any | None:
    try:
        import importlib.util
        mod_path = Path(__file__).resolve().parent / "queen-field-virus.py"
        spec = importlib.util.spec_from_file_location("queen_field_virus", mod_path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def mandate_enforce(operation: str, *, require_seal: bool = True) -> dict[str, Any]:
    if os.environ.get("QUEEN_MANDATE_OFF", "").strip().lower() in ("1", "true", "yes"):
        return {"ok": True, "override": True, "operation": operation}
    root = _root_mandate(operation)
    if root is not None and not root.get("ok"):
        return root
    if require_seal and operation in _PROTECTED:
        seal = verify_code_seal()
        if not seal.get("ok"):
            return {"ok": False, "error": "code_seal", "operation": operation, **seal}
    out: dict[str, Any] = {"ok": True, "operation": operation}
    if root is not None:
        out["root_sovereign"] = root.get("verdict") or root.get("via")
    if operation in ("field_virus", "file_ingress", "file_egress"):
        fv = _field_virus_mod()
        if fv is not None:
            out["field_virus"] = fv.status()
    return out


def security_status() -> dict[str, Any]:
    seal = verify_code_seal()
    root_status: dict[str, Any] = {}
    try:
        import importlib.util
        mod_path = Path(__file__).resolve().parent / "queen-root-sovereign.py"
        spec = importlib.util.spec_from_file_location("queen_root_sovereign", mod_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            root_status = mod.status()  # type: ignore[attr-defined]
    except Exception:
        root_status = {"ok": False, "error": "root_sovereign_unavailable"}
    field_virus: dict[str, Any] = {}
    fv = _field_virus_mod()
    if fv is not None:
        try:
            field_virus = fv.status()
        except Exception:
            field_virus = {"ok": False, "error": "field_virus_unavailable"}
    return {
        "schema": "queen-security-status/v1",
        "updated": _ts(),
        "code_seal": seal,
        "root_sovereign": root_status,
        "field_virus": field_virus,
        "protected_operations": sorted(_PROTECTED),
        "seal_path": str(SEAL_PATH),
    }


def main() -> int:
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "seal":
        print(json.dumps(seal_codebase(), indent=2))
        return 0
    if cmd == "verify":
        print(json.dumps(verify_code_seal(), indent=2))
        return 0
    print(json.dumps(security_status(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())