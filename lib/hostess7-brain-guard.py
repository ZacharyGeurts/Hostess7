#!/usr/bin/env pythong
"""Hostess 7 brain guard — checksum, verify, quarantine. Our brains — no corruptions."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
DOCTRINE = INSTALL / "data" / "hostess7-brain-guard-doctrine.json"
MANIFEST = INSTALL / "MANIFEST.sha256"
PANEL = STATE / "hostess7-brain-guard-panel.json"
RUNTIME = STATE / "hostess7-brain-guard-runtime.json"
LEDGER = STATE / "hostess7-brain-guard-ledger.jsonl"
QUARANTINE = STATE / "hostess7-brain-quarantine.jsonl"

ENABLED = os.environ.get("NEXUS_HOSTESS7_BRAIN_GUARD", "1") == "1"
FAIL_CLOSED = os.environ.get("NEXUS_HOSTESS7_BRAIN_FAIL_CLOSED", "1") == "1"


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


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _sha256_json(doc: dict[str, Any]) -> str:
    material = json.dumps(doc, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(material.encode()).hexdigest()


def _load_manifest() -> dict[str, str]:
    out: dict[str, str] = {}
    if not MANIFEST.is_file():
        return out
    try:
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            digest, fpath = parts[0].strip(), parts[1].strip()
            out[fpath] = digest
            try:
                rel = str(Path(fpath).resolve().relative_to(INSTALL.resolve()))
                out[rel] = digest
            except ValueError:
                pass
    except OSError:
        pass
    return out


def _last_chain_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            return ""
        row = json.loads(lines[-1])
        return str(row.get("chain_hash") or "")
    except (OSError, json.JSONDecodeError):
        return ""


def _append_ledger(path: Path, row: dict[str, Any], *, chain: bool = False) -> str:
    if chain:
        prev = _last_chain_hash(path)
        material = json.dumps(row, sort_keys=True, default=str, separators=(",", ":"))
        digest = hashlib.sha256(f"{prev}|{material}".encode()).hexdigest()
        row = {**row, "prev_chain_hash": prev or None, "chain_hash": digest}
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        return ""
    return str(row.get("chain_hash") or "")


def _ledger_tail(path: Path, limit: int = 16) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        return []
    return rows[-limit:]


def _prev_fingerprints() -> dict[str, str]:
    rt = _load(RUNTIME, {})
    fp = rt.get("engine_fingerprints")
    return fp if isinstance(fp, dict) else {}


def _witness_removals(
    engines: list[dict[str, Any]],
    *,
    prev: dict[str, str],
    missing_critical: list[str],
) -> list[dict[str, Any]]:
    removals: list[dict[str, Any]] = []
    for eng in engines:
        rel = str(eng.get("path") or "")
        if not rel:
            continue
        was = prev.get(rel)
        if was and not eng.get("present"):
            removals.append({
                "path": rel,
                "event": "engine_removed",
                "critical": bool(eng.get("critical")),
                "previous_sha256": was,
            })
        elif eng.get("corrupted") and was and eng.get("sha256") != was:
            removals.append({
                "path": rel,
                "event": "engine_tampered",
                "critical": bool(eng.get("critical")),
                "previous_sha256": was,
                "current_sha256": eng.get("sha256"),
            })
    for rel in missing_critical:
        if not any(r.get("path") == rel for r in removals):
            removals.append({
                "path": rel,
                "event": "critical_missing",
                "critical": True,
                "previous_sha256": prev.get(rel),
            })
    return removals


def _verify_engine(rel: str, *, critical: bool, manifest: dict[str, str]) -> dict[str, Any]:
    path = INSTALL / rel
    actual = _sha256_file(path)
    present = actual is not None
    expected = None
    for key, digest in manifest.items():
        if key.endswith(rel) or key == str(path):
            expected = digest
            break
    if expected is None:
        for key, digest in manifest.items():
            if rel in key:
                expected = digest
                break
    verified = present and (expected is None or actual == expected)
    corrupted = present and expected is not None and actual != expected
    return {
        "path": rel,
        "present": present,
        "critical": critical,
        "sha256": actual,
        "expected_sha256": expected,
        "manifest_verified": verified,
        "corrupted": corrupted,
        "bytes": path.stat().st_size if present else 0,
    }


def _brain_witness() -> dict[str, Any]:
    sense = _load(STATE / "field-sense-package-panel.json", {})
    members = sense.get("members") or {}
    h7 = members.get("hostess7") or {}
    field_brain = _load(STATE / "field-brain-panel.json", {})
    cmd = _load(STATE / "hostess7-command-panel.json", {})
    if not cmd:
        cmd = _load(STATE / "hostess7-command-runtime.json", {})
    return {
        "sense_hostess7": {
            "live": bool(h7.get("live") or h7.get("brain_live")),
            "brain_score": h7.get("brain_score"),
            "brain_protected": h7.get("brain_protected"),
            "brain_witness_only": h7.get("brain_witness_only"),
            "manifest_sha256": (h7.get("manifest") or {}).get("sha256"),
        },
        "field_brain": {
            "ok": field_brain.get("ok"),
            "manifest_count": field_brain.get("manifest_count"),
            "library_manifest_ok": field_brain.get("library_manifest_ok"),
        },
        "command_deck": {
            "available": bool(cmd.get("hostess7_available") or cmd.get("ok")),
            "motto": cmd.get("motto"),
        },
    }


def verify_brain(*, write_quarantine: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    manifest = _load_manifest()
    prev_fp = _prev_fingerprints()
    engines_out: list[dict[str, Any]] = []
    corrupted: list[dict[str, Any]] = []
    missing_critical: list[str] = []

    for eng in doctrine.get("protected_engines") or []:
        rel = str(eng.get("path") or "")
        critical = bool(eng.get("critical"))
        row = _verify_engine(rel, critical=critical, manifest=manifest)
        row["role"] = eng.get("role")
        engines_out.append(row)
        if row.get("corrupted"):
            corrupted.append(row)
            if write_quarantine:
                q = {
                    "ts": _now(),
                    "event": "corruption_detected",
                    "path": rel,
                    "sha256": row.get("sha256"),
                    "expected": row.get("expected_sha256"),
                }
                _append_ledger(QUARANTINE, q, chain=True)
        if critical and not row.get("present"):
            missing_critical.append(rel)

    removals = _witness_removals(engines_out, prev=prev_fp, missing_critical=missing_critical)
    if removals and write_quarantine:
        for rem in removals:
            _append_ledger(QUARANTINE, {"ts": _now(), **rem}, chain=True)

    witness = _brain_witness()
    brain_live = bool(witness.get("sense_hostess7", {}).get("live"))
    critical_ok = not missing_critical and not any(c.get("critical") for c in corrupted)
    manifest_ok = all(
        e.get("manifest_verified") for e in engines_out if e.get("present") and e.get("expected_sha256")
    )
    removal_hold = bool(doctrine.get("removal_policy", {}).get("motion_hold_on_removal")) and bool(removals)
    corrupted_any = bool(corrupted) or bool(missing_critical) or removal_hold
    verified = (
        ENABLED
        and critical_ok
        and not removal_hold
        and (manifest_ok or not manifest)
        and (not FAIL_CLOSED or not corrupted_any)
    )

    fingerprints = {
        str(e.get("path")): str(e.get("sha256") or "")
        for e in engines_out
        if e.get("present") and e.get("sha256")
    }

    if write_quarantine:
        _append_ledger(LEDGER, {
            "ts": _now(),
            "event": "brain_guard_verify",
            "corrupted_count": len(corrupted),
            "removal_count": len(removals),
            "missing_critical": missing_critical,
            "verified": verified,
            "guard_score": None,
        }, chain=True)

    score = 0.0
    if ENABLED:
        score += 0.35 if critical_ok else 0.0
        score += 0.25 if manifest_ok or not manifest else 0.05
        score += 0.2 if brain_live else 0.08
        score += 0.2 if witness.get("command_deck", {}).get("available") else 0.05
    if removals:
        score = min(score, 0.12)
    score = round(min(1.0, score), 4)

    return {
        "enabled": ENABLED,
        "verified": verified,
        "corrupted": corrupted_any,
        "brain_live": brain_live,
        "critical_ok": critical_ok,
        "manifest_ok": manifest_ok,
        "guard_score": score,
        "engines": engines_out,
        "corrupted_engines": corrupted,
        "missing_critical": missing_critical,
        "removal_witness": removals,
        "removal_count": len(removals),
        "brain_witness": witness,
        "fail_closed": FAIL_CLOSED,
        "engine_fingerprints": fingerprints,
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    v = verify_brain(write_quarantine=write)
    verdict = "brain_verified"
    if v.get("corrupted") or v.get("removal_count"):
        verdict = "brain_corruption_hold"
    elif not v.get("critical_ok"):
        verdict = "brain_incomplete_hold"
    elif not v.get("verified"):
        verdict = "brain_verify_pending"

    doc = {
        "schema": "hostess7-brain-guard/v1",
        "updated": _now(),
        "product": "Hostess 7",
        "role": "Our brains — Super Intelligence",
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "authority": doctrine.get("authority"),
        "queen_layer": "hostess7",
        "verification": v,
        "verdict": verdict,
        "motion_hold_on_corruption": bool(doctrine.get("removal_policy", {}).get("motion_hold_on_corruption")),
        "protected_count": len(v.get("engines") or []),
        "corrupted_count": len(v.get("corrupted_engines") or []),
        "removal_count": v.get("removal_count") or 0,
        "guard_score": v.get("guard_score"),
        "brain_live": v.get("brain_live"),
        "manifest_seal": str(MANIFEST) if MANIFEST.is_file() else None,
        "ledger_chain_tail": (_last_chain_hash(LEDGER) or "")[:16] or None,
        "reason": (
            "Hostess 7 brain verified — checksums match, witness live, no corruptions"
            if verdict == "brain_verified"
            else (
                "CRITICAL brain corruption or removal detected — motion hold until restore"
                if verdict == "brain_corruption_hold"
                else "Brain incomplete — restore critical Hostess7 engines"
            )
        ),
    }
    doc["panel_sha256"] = _sha256_json({k: val for k, val in doc.items() if k != "panel_sha256"})

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("h7_self_view", INSTALL / "lib" / "hostess7-self-view.py")
        if spec and spec.loader:
            sv = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sv)
            doc["self_view"] = sv.build_self_view(write=False)
    except Exception:
        doc["self_view"] = _load(STATE / "hostess7-self-view-panel.json", {})

    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {
            "schema": "hostess7-brain-guard-runtime/v1",
            "updated": doc["updated"],
            "verdict": verdict,
            "guard_score": v.get("guard_score"),
            "verified": v.get("verified"),
            "corrupted": v.get("corrupted"),
            "removal_count": v.get("removal_count") or 0,
            "engine_fingerprints": v.get("engine_fingerprints") or {},
            "panel_sha256": doc["panel_sha256"],
            "ledger_chain_tail": doc["ledger_chain_tail"],
        })
    return doc


def witness_json() -> dict[str, Any]:
    return {
        "schema": "hostess7-brain-guard-witness/v1",
        "updated": _now(),
        "ledger_tail": _ledger_tail(LEDGER, 24),
        "quarantine_tail": _ledger_tail(QUARANTINE, 24),
        "ledger_chain_tail": (_last_chain_hash(LEDGER) or "")[:24] or None,
        "quarantine_chain_tail": (_last_chain_hash(QUARANTINE) or "")[:24] or None,
        "panel": _load(PANEL, {}),
        "runtime": _load(RUNTIME, {}),
    }


def panel_json() -> dict[str, Any]:
    return build_panel(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "verify":
        print(json.dumps(verify_brain(), ensure_ascii=False))
        return 0
    if cmd in ("witness", "ledger"):
        print(json.dumps(witness_json(), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: hostess7-brain-guard.py [json|verify|witness]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())