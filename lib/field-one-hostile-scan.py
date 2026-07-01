#!/usr/bin/env pythong
"""Scan fields that are not Field 1 — mark hostile, bring to Field 1 authority.

Doctrine: one field, depth zero. Any secondary field, world perimeter clone,
depth field, or field-on-field hotspot is scanned, registered hostile, and
consolidated under lib/field-one.py (home sanctuary canonical).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
HOSTILE_TSV = STATE / "field-hostile.tsv"
REGISTRY = STATE / "field-not-one-hostile.json"
LEDGER = STATE / "field-not-one-hostile.jsonl"
FIELD_ONE_ID = os.environ.get("FIELD_ONE_ID", "field_one")
OPERATOR_FIELD = os.environ.get("FIELD_ONE_OPERATOR_ID", "field_gladstone")
HOME_NODE = os.environ.get("GROK_LAB_HOME_NODE_ID", "node-local")


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
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _existing_hostile_keys() -> set[str]:
    keys: set[str] = set()
    if not HOSTILE_TSV.is_file():
        return keys
    for line in HOSTILE_TSV.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 2:
            keys.add(parts[1].strip())
    reg = _load(STATE / "kill-rekill-registry.json", {})
    for k in (reg.get("entries") or {}):
        keys.add(str(k))
    doc = _load(REGISTRY, {})
    for e in doc.get("entries") or []:
        if isinstance(e, dict):
            keys.add(str(e.get("field_key") or ""))
    return keys


def _append_hostile(field_key: str, reason: str, *, source: str = "field-one-scan") -> bool:
    if not field_key or field_key in _existing_hostile_keys():
        return False
    HOSTILE_TSV.parent.mkdir(parents=True, exist_ok=True)
    if not HOSTILE_TSV.is_file():
        HOSTILE_TSV.write_text("ts\tip\tvector\tseverity\treason\tsource\n", encoding="utf-8")
    line = f"{_now()}\t{field_key}\tFIELD_NOT_ONE\thigh\t{reason}\t{source}\n"
    with HOSTILE_TSV.open("a", encoding="utf-8") as fh:
        fh.write(line)
    kit = _import_mod("field_attack_kit", "lib/field-attack-kit.py")
    if kit and hasattr(kit, "register_kill_for_rekill"):
        try:
            kit.register_kill_for_rekill(
                field_key,
                "FIELD_NOT_ONE",
                "high",
                reason,
                source=source,
            )
        except (OSError, TypeError, ValueError):
            pass
    return True


def _scan_multi_field_configs() -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for path in (INSTALL / "data").glob("field-*.json"):
        doc = _load(path, {})
        if not isinstance(doc, dict) or "operator_field_id" not in doc:
            continue
        op = str(doc.get("operator_field_id") or OPERATOR_FIELD)
        for field in doc.get("fields") or []:
            if not isinstance(field, dict):
                continue
            fid = str(field.get("id") or "")
            role = str(field.get("role") or "")
            if not fid or fid in (FIELD_ONE_ID, op, "field_one"):
                continue
            if role == "operator_home":
                continue
            found.append({
                "field_key": f"field:{fid}",
                "field_id": fid,
                "kind": "multi_field_config",
                "source": str(path.relative_to(INSTALL)),
                "role": role,
                "reason": f"not_field_one:{fid} role={role}",
            })
    return found


def _scan_world_nodes() -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    nodes_path = INSTALL / "GrokLab" / "deploy" / "world-nodes.json"
    doc = _load(nodes_path, {})
    for node in doc.get("nodes") or []:
        if not isinstance(node, dict) or not node.get("enabled"):
            continue
        nid = str(node.get("id") or "")
        role = str(node.get("role") or "")
        if nid == HOME_NODE or role == "home_sanctuary":
            continue
        region = str(node.get("region") or "unknown")
        port = int(node.get("ssh_port") or 0)
        field_key = f"world:{nid}"
        found.append({
            "field_key": field_key,
            "field_id": nid,
            "kind": "world_perimeter_node",
            "source": "GrokLab/deploy/world-nodes.json",
            "region": region,
            "ssh_port": port,
            "reason": f"world_field_not_field_one:{nid}@{region}",
        })
    reg = _load(STATE / "grok-lab-world-registry.json", {})
    for node in reg.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("id") or "")
        if not nid or nid == HOME_NODE:
            continue
        field_key = f"world:{nid}"
        if any(f.get("field_key") == field_key for f in found):
            continue
        found.append({
            "field_key": field_key,
            "field_id": nid,
            "kind": "world_registry_node",
            "source": "grok-lab-world-registry.json",
            "region": str(node.get("region") or ""),
            "reason": f"registry_not_field_one:{nid}",
        })
    return found


def _scan_geo_field_arrays() -> list[dict[str, Any]]:
    """GPS / RF lock files — any geographic field array entry is not Field 1."""
    found: list[dict[str, Any]] = []
    for path in (INSTALL / "data").glob("field-*.json"):
        doc = _load(path, {})
        if not isinstance(doc, dict):
            continue
        fields = doc.get("fields")
        if not isinstance(fields, list):
            continue
        if "operator_field_id" in doc:
            continue
        for field in fields:
            if not isinstance(field, dict):
                continue
            fid = str(field.get("id") or field.get("name") or "")
            if not fid:
                continue
            if fid in (FIELD_ONE_ID, OPERATOR_FIELD, "field_one", "field_gladstone"):
                continue
            if str(field.get("role") or "") == "operator_home":
                continue
            if "lat" not in field and "lon" not in field and "freq" not in field:
                continue
            found.append({
                "field_key": f"geo:{path.stem}:{fid}",
                "field_id": fid,
                "kind": "geo_field_array",
                "source": str(path.relative_to(INSTALL)),
                "role": str(field.get("role") or ""),
                "reason": f"geo_field_not_field_one:{fid}",
            })
    return found


def _scan_depth_and_nested() -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    depth_re = re.compile(r'"field_depth"\s*:\s*([1-9]\d*)')
    layer_re = re.compile(r'"depth"\s*:\s*([1-9]\d*)')
    on_field_re = re.compile(r'"field_on_field"\s*:\s*true')
    for path in list(STATE.glob("*.json"))[:80]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if on_field_re.search(text):
            found.append({
                "field_key": f"state:{path.name}:field_on_field",
                "field_id": path.stem,
                "kind": "field_on_field",
                "source": str(path.relative_to(STATE)),
                "reason": "field_on_field_forbidden",
            })
        for m in depth_re.finditer(text):
            found.append({
                "field_key": f"state:{path.name}:depth:{m.group(1)}",
                "field_id": path.stem,
                "kind": "depth_field",
                "source": str(path.relative_to(STATE)),
                "depth": int(m.group(1)),
                "reason": f"field_depth_{m.group(1)}_not_field_one",
            })
        for m in layer_re.finditer(text):
            d = int(m.group(1))
            if d > 0 and "singularizer" not in path.name:
                found.append({
                    "field_key": f"state:{path.name}:layer:{d}",
                    "field_id": path.stem,
                    "kind": "layer_depth",
                    "source": str(path.relative_to(STATE)),
                    "depth": d,
                    "reason": f"layer_depth_{d}_not_field_one",
                })
    nf = _import_mod("field_non_fielded", "lib/field-non-fielded-safety.py")
    if nf and hasattr(nf, "defield_audit"):
        try:
            rep = nf.defield_audit()
            for hit in (rep.get("violations") or rep.get("hotspots") or [])[:20]:
                if not isinstance(hit, dict):
                    continue
                p = str(hit.get("path") or hit.get("rel") or "")
                if not p:
                    continue
                found.append({
                    "field_key": f"hotspot:{p[-120:]}",
                    "field_id": p,
                    "kind": "non_fielded_hotspot",
                    "source": "field-non-fielded-safety",
                    "reason": str(hit.get("reason") or "nested_field_hotspot"),
                })
        except (OSError, TypeError, ValueError, AttributeError):
            pass
    return found


def _bring_to_field_one(entries: list[dict[str, Any]]) -> dict[str, Any]:
    brought: list[str] = []
    errors: list[str] = []
    fo = _import_mod("field_one", "lib/field-one.py")
    if fo and hasattr(fo, "sync"):
        try:
            sync = fo.sync(storage_only=os.environ.get("FIELD_ONE_BRING_STORAGE_ONLY", "1") == "1")
            if sync.get("ok"):
                brought.append("field_one_sync")
            else:
                errors.append(f"field_one_sync:{sync.get('error', 'fail')}")
        except (OSError, TypeError, ValueError):
            errors.append("field_one_sync_exception")
    sing = _import_mod("field_depth_singularizer", "lib/field-depth-singularizer.py")
    if sing and hasattr(sing, "cycle"):
        try:
            cyc = sing.cycle()
            if cyc.get("ok", True):
                brought.append("depth_singularizer")
        except (OSError, TypeError, ValueError, AttributeError):
            pass
    for entry in entries:
        entry["brought_to_field_one"] = True
        entry["brought_at"] = _now()
        entry["canonical"] = FIELD_ONE_ID
        entry["authority"] = "127.0.0.1"
        _append_ledger({"action": "bring", **entry})
    return {"brought": brought, "errors": errors, "count": len(entries)}


def scan_and_bring(*, apply: bool = True) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for batch in (
        _scan_multi_field_configs(),
        _scan_world_nodes(),
        _scan_geo_field_arrays(),
        _scan_depth_and_nested(),
    ):
        for item in batch:
            key = str(item.get("field_key") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            candidates.append(item)

    new_hostile = 0
    if apply:
        for item in candidates:
            if _append_hostile(str(item["field_key"]), str(item.get("reason") or "not_field_one")):
                new_hostile += 1
                item["hostile"] = True
            else:
                item["hostile"] = False

    bring = _bring_to_field_one(candidates) if apply else {"brought": [], "errors": [], "count": 0}

    doc = {
        "schema": "field-not-one-hostile/v1",
        "updated": _now(),
        "field_one": FIELD_ONE_ID,
        "operator_field": OPERATOR_FIELD,
        "home_node": HOME_NODE,
        "motto": "Not Field 1 → hostile → brought to Field 1",
        "scanned": len(candidates),
        "new_hostile": new_hostile,
        "entries": candidates,
        "bring": bring,
    }
    _save(REGISTRY, doc)
    return doc


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    apply = "--dry-run" not in args
    out = scan_and_bring(apply=apply)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())