#!/usr/bin/env pythong
"""ZNetwork operator registry — self-registration, sovereign receipt, BSP composite mesh."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
PROFILE_PATH = STATE / "znetwork-operator-profile.json"
MESH_PATH = STATE / "znetwork-mesh-registry.json"
LEDGER = STATE / "znetwork-operator-registry.jsonl"
UNIVERSAL_SLICE = STATE / "znetwork-universal-registry-slice.json"
SCHEMA = "znetwork-operator-registry/v1"
MESH_SCHEMA = "znetwork-mesh-registry/v1"
BSP_CASE = "znetwork_operator_mesh"

_MOD_CACHE: dict[str, Any] = {}


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
    os.replace(tmp, path)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _mod(py: Path, name: str) -> Any | None:
    key = str(py)
    if key in _MOD_CACHE:
        return _MOD_CACHE[key]
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _MOD_CACHE[key] = mod
    return mod


def _sovereign_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    clk = _mod(INSTALL / "lib" / "sovereign-clock.py", "sovereign_clock_znreg")
    ts = clk.utc_z("znetwork_registry") if clk and hasattr(clk, "utc_z") else _now()
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(body).hexdigest()
    return {
        "schema": "znetwork-sovereign-receipt/v1",
        "receipt_id": digest[:20],
        "sealed_at": ts,
        "payload_hash": digest,
    }


def _vault_wire_point() -> str:
    vault = _mod(INSTALL / "lib" / "znetwork-secure-vault.py", "znetwork_vault_wire")
    if vault and hasattr(vault, "wire_point"):
        rep = vault.wire_point()
        return str(rep.get("wire_point") or "")
    return ""


def _truth_gate() -> dict[str, Any]:
    fio = _mod(INSTALL / "lib" / "field-io-packet.py", "field_io_znreg")
    if fio and hasattr(fio, "truth_gate"):
        return fio.truth_gate()
    return {"pass_ok": True, "bypass": True}


def _split_name(full_name: str) -> tuple[str, str]:
    full_name = " ".join(full_name.split())
    if not full_name:
        return "", ""
    parts = full_name.split(" ", 1)
    given = parts[0]
    family = parts[1] if len(parts) > 1 else ""
    return given, family


def _operator_id(full_name: str, wire_point: str) -> str:
    secret = hashlib.sha256(f"{full_name}:{wire_point}".encode()).hexdigest()[:16]
    return f"znop-{secret}"


def _composite_bsp_sort(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    org = _mod(INSTALL / "lib" / "iron-plate-organize.py", "iron_plate_znreg")
    if org and hasattr(org, "_composite_bsp_sort"):
        return org._composite_bsp_sort(rows, key="composite_score", reverse=True)
    if len(rows) <= 1:
        return list(rows)
    scored = sorted(rows, key=lambda r: float(r.get("composite_score") or 0), reverse=True)
    return scored


def _bsp_composite_score(profile: dict[str, Any], *, truth: dict[str, Any]) -> float:
    score = 0.0
    if profile.get("full_name"):
        score += 0.22
    if profile.get("given_name") and profile.get("family_name"):
        score += 0.12
    if profile.get("display_name"):
        score += 0.08
    if profile.get("wire_point"):
        score += 0.18
    if profile.get("region"):
        score += 0.06
    if profile.get("locale"):
        score += 0.04
    if profile.get("public_bio"):
        score += 0.05
    if truth.get("pass_ok"):
        score += 0.15
    if profile.get("sovereign_receipt", {}).get("receipt_id"):
        score += 0.10
    return round(min(1.0, score), 4)


def _normalize_register_fields(fields: dict[str, Any]) -> dict[str, Any]:
    full_name = " ".join(str(fields.get("full_name") or "").split()).strip()
    if len(full_name) < 2:
        raise ValueError("full_name_required")
    given = str(fields.get("given_name") or "").strip()
    family = str(fields.get("family_name") or "").strip()
    if not given and not family:
        given, family = _split_name(full_name)
    display = str(fields.get("display_name") or "").strip()
    if not display:
        display = full_name if len(full_name) <= 48 else f"{given} {family[0]}.".strip()
    region = str(fields.get("region") or fields.get("country") or "").strip()[:80]
    locale = str(fields.get("locale") or "en").strip()[:16]
    bio = str(fields.get("public_bio") or fields.get("bio") or "").strip()[:280]
    return {
        "full_name": full_name[:120],
        "given_name": given[:60],
        "family_name": family[:60],
        "display_name": display[:64],
        "region": region,
        "locale": locale,
        "public_bio": bio,
    }


def register_operator(**fields: Any) -> dict[str, Any]:
    """Self-register on ZNetwork mesh — sovereign receipt + BSP composite row."""
    norm = _normalize_register_fields(fields)
    truth = _truth_gate()
    wire = _vault_wire_point()
    if not wire:
        wp = _mod(INSTALL / "lib" / "znetwork-secure-vault.py", "znetwork_vault_wp")
        if wp and hasattr(wp, "wire_point"):
            wire = str(wp.wire_point().get("wire_point") or "")
    if not wire:
        return {"ok": False, "error": "wire_point_unavailable"}

    operator_id = _operator_id(norm["full_name"], wire)
    receipt_body = {
        "operator_id": operator_id,
        "full_name": norm["full_name"],
        "display_name": norm["display_name"],
        "wire_point": wire,
        "region": norm["region"],
        "locale": norm["locale"],
    }
    receipt = _sovereign_receipt(receipt_body)

    profile = {
        "schema": SCHEMA,
        "operator_id": operator_id,
        "registered_at": _now(),
        "updated_at": _now(),
        "self": True,
        "truth_gate_ok": bool(truth.get("pass_ok")),
        "sovereign_receipt": receipt,
        "wire_point": wire,
        **norm,
    }
    profile["composite_score"] = _bsp_composite_score(profile, truth=truth)
    profile["bsp_case"] = BSP_CASE
    profile["bsp_algorithm"] = "composite_bsp"

    _save(PROFILE_PATH, profile)
    _mesh_upsert(profile)
    _publish_universal_slice(profile)
    _append_jsonl(
        LEDGER,
        {"ts": _now(), "event": "register", "operator_id": operator_id, "wire_point": wire},
    )
    return {
        "ok": True,
        "schema": SCHEMA,
        "profile": profile,
        "receipt": receipt,
        "composite_score": profile["composite_score"],
        "motto": "Registered on ZNetwork mesh — BSP composite ready for worldwide peer federation.",
    }


def _mesh_upsert(entry: dict[str, Any]) -> None:
    mesh = _load(MESH_PATH, {})
    mesh.setdefault("schema", MESH_SCHEMA)
    mesh.setdefault("entries", [])
    entries = [e for e in mesh.get("entries") or [] if e.get("operator_id") != entry.get("operator_id")]
    public = {
        "operator_id": entry.get("operator_id"),
        "full_name": entry.get("full_name"),
        "given_name": entry.get("given_name"),
        "family_name": entry.get("family_name"),
        "display_name": entry.get("display_name"),
        "wire_point": entry.get("wire_point"),
        "region": entry.get("region"),
        "locale": entry.get("locale"),
        "public_bio": entry.get("public_bio"),
        "composite_score": entry.get("composite_score"),
        "bsp_case": entry.get("bsp_case"),
        "bsp_algorithm": entry.get("bsp_algorithm"),
        "sovereign_receipt": entry.get("sovereign_receipt"),
        "registered_at": entry.get("registered_at"),
        "updated_at": entry.get("updated_at"),
        "self": bool(entry.get("self")),
        "source": "local" if entry.get("self") else "mesh_ingest",
    }
    entries.append(public)
    mesh["entries"] = _composite_bsp_sort(entries)
    mesh["count"] = len(mesh["entries"])
    mesh["updated"] = _now()
    mesh["bsp_case"] = BSP_CASE
    _save(MESH_PATH, mesh)


def _publish_universal_slice(profile: dict[str, Any]) -> None:
    slice_doc = {
        "schema": "znetwork-universal-registry-slice/v1",
        "section": "znetwork_operators",
        "updated": _now(),
        "entity": {
            "id": profile.get("operator_id"),
            "label": profile.get("display_name"),
            "full_name": profile.get("full_name"),
            "wire_point": profile.get("wire_point"),
            "region": profile.get("region"),
            "composite_score": profile.get("composite_score"),
            "existence_kind": "znetwork_operator",
        },
    }
    _save(UNIVERSAL_SLICE, slice_doc)
    uni = STATE / "universal-field-registry.json"
    base = _load(uni, {"schema": "universal-field-registry/v1", "sections": {}})
    sections = base.setdefault("sections", {})
    rows = [r for r in (sections.get("znetwork_operators") or []) if r.get("id") != profile.get("operator_id")]
    rows.append(slice_doc["entity"])
    sections["znetwork_operators"] = _composite_bsp_sort(rows)
    base["updated"] = _now()
    _save(uni, base)


def ingest_peer(entry: dict[str, Any]) -> dict[str, Any]:
    """Federation ingest — peer registration receipt (invite/mesh sync only)."""
    wire = str(entry.get("wire_point") or "").strip().lower()
    if not re.fullmatch(r"znwp-[a-f0-9]{16,32}", wire):
        return {"ok": False, "error": "invalid_wire_point"}
    full_name = " ".join(str(entry.get("full_name") or entry.get("display_name") or "").split())
    if len(full_name) < 2:
        return {"ok": False, "error": "full_name_required"}
    receipt = entry.get("sovereign_receipt") or {}
    if not receipt.get("receipt_id"):
        receipt = _sovereign_receipt(
            {
                "operator_id": entry.get("operator_id") or _operator_id(full_name, wire),
                "full_name": full_name,
                "wire_point": wire,
            }
        )
    operator_id = str(entry.get("operator_id") or _operator_id(full_name, wire))
    norm = _normalize_register_fields({**entry, "full_name": full_name})
    truth = _truth_gate()
    row = {
        "schema": SCHEMA,
        "operator_id": operator_id,
        "registered_at": str(entry.get("registered_at") or _now()),
        "updated_at": _now(),
        "self": False,
        "truth_gate_ok": bool(truth.get("pass_ok")),
        "sovereign_receipt": receipt,
        "wire_point": wire,
        **norm,
    }
    row["composite_score"] = _bsp_composite_score(row, truth=truth)
    row["bsp_case"] = BSP_CASE
    row["bsp_algorithm"] = "composite_bsp"
    _mesh_upsert(row)
    _append_jsonl(LEDGER, {"ts": _now(), "event": "ingest_peer", "operator_id": operator_id, "wire_point": wire})
    return {"ok": True, "schema": SCHEMA, "operator_id": operator_id, "composite_score": row["composite_score"]}


def profile_json() -> dict[str, Any]:
    profile = _load(PROFILE_PATH, {})
    if not profile:
        return {"ok": True, "schema": SCHEMA, "registered": False, "profile": None}
    return {"ok": True, "schema": SCHEMA, "registered": True, "profile": profile}


def mesh_json(*, query: str = "") -> dict[str, Any]:
    mesh = _load(MESH_PATH, {"schema": MESH_SCHEMA, "entries": []})
    entries = list(mesh.get("entries") or [])
    q = query.strip().lower()
    if q:
        entries = [
            e
            for e in entries
            if q in str(e.get("full_name") or "").lower()
            or q in str(e.get("display_name") or "").lower()
            or q in str(e.get("wire_point") or "").lower()
            or q in str(e.get("region") or "").lower()
        ]
    return {
        "ok": True,
        "schema": MESH_SCHEMA,
        "bsp_case": BSP_CASE,
        "bsp_algorithm": "composite_bsp",
        "count": len(entries),
        "entries": entries,
        "updated": mesh.get("updated"),
        "policy": {
            "worldwide_federation": True,
            "no_plaintext_address_book": True,
            "public_fields": ["full_name", "display_name", "wire_point", "region", "composite_score"],
            "sync": "sovereign_receipt_mesh",
        },
    }


def panel_json() -> dict[str, Any]:
    prof = profile_json()
    mesh = mesh_json()
    return {
        "ok": True,
        "schema": SCHEMA,
        "registered": prof.get("registered"),
        "profile": prof.get("profile"),
        "mesh": mesh,
        "truth_gate": {"pass_ok": _truth_gate().get("pass_ok")},
        "motto": "Register yourself — enter the ZNetwork mesh with BSP composite ordering.",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "profile":
        print(json.dumps(profile_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "mesh":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(mesh_json(query=query), ensure_ascii=False, indent=2))
        return 0
    if cmd == "register" and len(sys.argv) > 2:
        req = json.loads(sys.argv[2])
        try:
            print(json.dumps(register_operator(**req), ensure_ascii=False, indent=2))
            return 0
        except ValueError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
            return 1
    if cmd == "ingest" and len(sys.argv) > 2:
        req = json.loads(sys.argv[2])
        entry = req.get("entry") or req
        print(json.dumps(ingest_peer(entry), ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {
                "error": "usage: znetwork-operator-registry.py [json|profile|mesh [q]|register JSON|ingest JSON]",
            }
        ),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())