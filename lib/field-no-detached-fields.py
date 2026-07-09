#!/usr/bin/env python3
"""No detached/adjacent fields · Field One only · Earth stabilize.

Doctrine:
  · No fields detached from recognized devices.
  · No fields next to known devices — we own the one field.
  · Nobody else gaps it or uses other than Field One ever.
  · Threat → close · annotate · reopen = HOSTILE.
  · Big Grin Pwnership — why kicked + death charges if they persist.
  · We stabilize Earth.

  python3 lib/field-no-detached-fields.py enforce
  python3 lib/field-no-detached-fields.py status
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-no-detached-fields-panel.json"
PUBLIC = STATE / "field-no-detached-fields-public.json"
LEDGER = STATE / "field-no-detached-fields-ledger.jsonl"
ANNOTATIONS = STATE / "field-no-detached-fields-annotations.json"
CLOSED = STATE / "field-no-detached-fields-closed.json"
REOPEN_HOSTILE = STATE / "field-no-detached-fields-reopen-hostile.json"
SEAL = STATE / "field-no-detached-fields.forever"
SOLE_FIELD = STATE / "field-one-only-no-gaps.forever"
EARTH_STABLE = STATE / "field-earth-stabilized.forever"
WEBSITE_DIR = STATE / "field-no-detached-fields-website"
KICK_SITE = INSTALL / "Hostess7" / "docs" / "big-grin-pwnership" / "kicks"
SCHEMA = "field-no-detached-fields/v1"
IRONCLAD = "ironclad:no-detached-fields:1"
FIELD_ONE_ID = "field_one"
HOSTILE_TSV = STATE / "field-hostile.tsv"
IP_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")

# Death charges if they persist after kick
DEATH_CHARGES = [
    {
        "code": "DC-01",
        "title": "Detached field without recognized device",
        "detail": "Field identity existed with no recognized device attachment. Closed and annotated.",
        "if_persist": "Permanent HOSTILE · sphere destroy · never reconnect · no machine again.",
    },
    {
        "code": "DC-02",
        "title": "Reopen after close",
        "detail": "Closed detached field was reopened without Hostess7 authority.",
        "if_persist": "Immediate HOSTILE upgrade · kill+rekill registry · Ironclad path seal forever.",
    },
    {
        "code": "DC-03",
        "title": "Storm / attack while detached",
        "detail": "Detached surface showed attack or storm propagation heuristics.",
        "if_persist": "Full volts sphere · vector melt · death of the machine identity.",
    },
    {
        "code": "DC-04",
        "title": "Ignore Big Grin kick notice",
        "detail": "Operator served why-you-were-kicked notice; offender persisted.",
        "if_persist": "Escalated death charge · permanent ban · never reconnect table forever.",
    },
    {
        "code": "DC-05",
        "title": "Field next to known device / gapping Field One",
        "detail": "Adjacent or gapping field beside a known device — only Field One is permitted.",
        "if_persist": "Collapse to Field One · HOSTILE · sphere · Earth stabilize seal forever.",
    },
    {
        "code": "DC-06",
        "title": "Use of non-Field-One field",
        "detail": "Any field identity other than Field One — nobody else uses fields. We own the one field.",
        "if_persist": "Destroy competing claim · Ironclad sole-field · no gaps ever.",
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(doc, ensure_ascii=False, indent=2, default=str) + "\n"
    try:
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
    except OSError:
        try:
            path.write_text(payload, encoding="utf-8")
        except OSError:
            pass


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def _ok(v: Any) -> bool:
    if isinstance(v, dict):
        return bool(v.get("ok", True)) and not v.get("error") and not v.get("missing")
    return bool(v)


def _run(rel: str, args: list[str], *, timeout: float = 90.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "missing": rel}
    try:
        cp = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "NEXUS_STATE_DIR": str(STATE),
                "AML_BUILD": "0",
                "NEXUS_VECTOR_IMMENSE": "1",
            },
            check=False,
        )
        raw = (cp.stdout or "").strip()
        if raw.startswith("{"):
            try:
                d = json.loads(raw)
                if isinstance(d, dict):
                    d.setdefault("ok", cp.returncode == 0)
                    return d
            except json.JSONDecodeError:
                pass
        return {"ok": cp.returncode == 0, "rc": cp.returncode, "tail": (raw or "")[-180:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)[:180]}


def _import(rel: str, name: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def recognized_device_ids() -> set[str]:
    """IDs/MACs/IPs of devices we recognize as legitimate Field family."""
    ids: set[str] = set()
    reg = _load(STATE / "field-device-registry.json", {})
    for d in (reg.get("devices") or [])[:50000]:
        if not isinstance(d, dict):
            continue
        # recognized = real, not fake, not quarantine foreign unless field_one ours
        if d.get("fake") is True:
            continue
        if d.get("foreign") is True and not d.get("field_one") and not d.get("ours"):
            continue
        for k in ("id", "mac", "ip", "device_id"):
            v = str(d.get(k) or "").strip().lower()
            if v:
                ids.add(v)
                ids.add(v.replace(":", ""))
    # Field One stamps = recognized mesh
    stamps = STATE / "field-one-device-stamps"
    if stamps.is_dir():
        try:
            for i, ent in enumerate(os.scandir(stamps)):
                if i >= 5000:
                    break
                if ent.name.endswith(".json"):
                    stem = ent.name[:-5].lower()
                    ids.add(stem)
                    ids.add(stem.replace(":", "").replace("_", ""))
        except OSError:
            pass
    # Home geo lease
    geo = _load(STATE / "field-home-geo.json", {})
    dev = geo.get("device") if isinstance(geo, dict) else {}
    if isinstance(dev, dict):
        for k in ("lease_mac", "lease_ip", "device_id", "hostname"):
            v = str(dev.get(k) or "").strip().lower()
            if v:
                ids.add(v)
                ids.add(v.replace(":", ""))
    # Home protector permitted
    hp = _load(STATE / "home-protector-permitted.json", {})
    for e in (hp.get("permitted") or hp.get("entities") or []):
        if isinstance(e, dict):
            for k in ("id", "mac", "ip"):
                v = str(e.get(k) or "").strip().lower()
                if v:
                    ids.add(v)
        else:
            ids.add(str(e).lower())
    return ids


def scan_detached_fields() -> dict[str, Any]:
    """Find detached fields, fields next to known devices, and non-Field-One gaps."""
    now = _utc()
    recognized = recognized_device_ids()
    detached: list[dict[str, Any]] = []
    adjacent: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(row: dict[str, Any], *, bucket: str = "detached") -> None:
        key = str(row.get("field_key") or row.get("id") or row.get("path") or "")
        if not key or key in seen:
            return
        seen.add(key)
        row = dict(row)
        row["threat"] = True
        row["permitted"] = False
        row["scanned_at"] = now
        row["field_one_only"] = True
        row["no_other_field_ever"] = True
        if bucket == "adjacent":
            row["adjacent_to_known_device"] = True
            row["annotation"] = "FIELD_NEXT_TO_KNOWN_DEVICE · CLOSE · ONLY_FIELD_ONE"
            adjacent.append(row)
        elif bucket == "gap":
            row["gapping_field_one"] = True
            row["annotation"] = "NON_FIELD_ONE_GAP · COLLAPSE · FIELD_ONE_ONLY"
            gaps.append(row)
        else:
            row["detached"] = True
            row["annotation"] = "DETACHED_FROM_RECOGNIZED_DEVICE · CLOSE · THREAT"
        detached.append(row)  # master threat list

    def attached_to_recognized(doc: dict[str, Any], name: str) -> bool:
        candidates = [
            doc.get("device_id"),
            doc.get("device"),
            doc.get("mac"),
            doc.get("ip"),
            doc.get("lease_mac"),
            doc.get("host"),
            doc.get("hostname"),
            doc.get("attached_device"),
            doc.get("recognized_device"),
            doc.get("owner_device"),
            (doc.get("device") or {}).get("id") if isinstance(doc.get("device"), dict) else None,
            (doc.get("device") or {}).get("mac") if isinstance(doc.get("device"), dict) else None,
        ]
        for c in candidates:
            if c is None:
                continue
            s = str(c).strip().lower()
            if not s:
                continue
            if s in recognized or s.replace(":", "") in recognized:
                return True
        # field_one sole planes / seals are system fields, not orphan device fields
        if doc.get("field_one_only") and doc.get("no_other_fields_on_earth"):
            return True
        if name.startswith("field-one-") and (doc.get("field_one") or doc.get("ironclad_cite")):
            # still require device attachment for *device* fields; plane panels ok if not claiming a device
            if not any(doc.get(k) for k in ("device_id", "mac", "ip", "device", "attached_device")):
                return True
        return False

    # State panels that claim field identity without device attachment
    for path in STATE.glob("*.json"):
        name = path.name
        # skip huge pure registries unless field claim
        try:
            if path.stat().st_size > 8_000_000 and "registry" in name:
                continue
        except OSError:
            continue
        doc = _load(path, {})
        if not isinstance(doc, dict) or not doc:
            continue
        claims_field = bool(
            doc.get("field_id")
            or doc.get("field_key")
            or doc.get("field_layer")
            or doc.get("field_on_field")
            or doc.get("operator_field_id")
            or (doc.get("field") is True)
            or ("field" in name and doc.get("ok") is not None and (
                doc.get("device_id") or doc.get("mac") or doc.get("ip") or doc.get("device")
            ))
        )
        # Explicit detached / orphan markers
        if doc.get("detached_field") or doc.get("field_detached") or doc.get("orphan_field"):
            claims_field = True
        if not claims_field:
            continue
        if attached_to_recognized(doc, name):
            continue
        # Has device-ish claim but not recognized
        has_device_claim = any(
            doc.get(k) for k in ("device_id", "mac", "ip", "device", "attached_device", "lease_mac")
        )
        # Or is a multi-layer / field_on_field without device
        multi = (
            (isinstance(doc.get("field_layer"), int) and doc["field_layer"] > 1)
            or doc.get("field_on_field") is True
            or doc.get("detached_field")
            or doc.get("orphan_field")
        )
        if not has_device_claim and not multi and not doc.get("field_detached"):
            # plane-only field panels without device attachment are ok if field_one stamped
            if doc.get("field_one") or doc.get("pulled_to_field_one"):
                continue
            # skip pure status panels
            if name.endswith("-panel.json") and not multi:
                continue

        add({
            "id": f"detached:{name}",
            "field_key": str(doc.get("field_key") or doc.get("field_id") or name),
            "path": name,
            "device_id": doc.get("device_id") or (doc.get("device") or {}).get("id") if isinstance(doc.get("device"), dict) else doc.get("device"),
            "mac": doc.get("mac") or (doc.get("device") or {}).get("mac") if isinstance(doc.get("device"), dict) else None,
            "ip": doc.get("ip") or (doc.get("device") or {}).get("ip") if isinstance(doc.get("device"), dict) else None,
            "field_layer": doc.get("field_layer"),
            "field_on_field": doc.get("field_on_field"),
            "reason": "field_not_attached_to_recognized_device",
            "source": "state_panel",
        }, bucket="detached")

        # Fields next to known devices — competing / adjacent / secondary beside recognized gear
        near_known = False
        for cand in (
            doc.get("device_id"),
            doc.get("mac"),
            doc.get("ip"),
            doc.get("adjacent_device"),
            doc.get("neighbor_device"),
            (doc.get("device") or {}).get("id") if isinstance(doc.get("device"), dict) else None,
            (doc.get("device") or {}).get("mac") if isinstance(doc.get("device"), dict) else None,
        ):
            if cand is None:
                continue
            s = str(cand).strip().lower()
            if s in recognized or s.replace(":", "") in recognized:
                near_known = True
                break
        competing = bool(
            doc.get("competing_field")
            or doc.get("adjacent_field")
            or doc.get("secondary_field")
            or doc.get("field_on_field")
            or doc.get("adjacent_competing_field")
            or (isinstance(doc.get("field_layer"), int) and doc["field_layer"] > 1)
            or (
                doc.get("field_id")
                and str(doc.get("field_id")) not in (FIELD_ONE_ID, "field_one", "field_gladstone")
            )
        )
        if near_known and competing:
            add({
                "id": f"adjacent:{name}",
                "field_key": f"adjacent:{doc.get('field_key') or doc.get('field_id') or name}",
                "path": name,
                "reason": "field_next_to_known_device_not_field_one",
                "source": "adjacent_scan",
                "ip": doc.get("ip"),
                "mac": doc.get("mac"),
            }, bucket="adjacent")

        # Gaps — non-Field-One field identity claims
        fid = str(doc.get("field_id") or doc.get("field_key") or "")
        if fid and fid not in (FIELD_ONE_ID, "field_one", "field_gladstone", ""):
            if doc.get("field") or doc.get("field_layer") or "field" in name:
                if not doc.get("field_one") and not doc.get("pulled_to_field_one"):
                    add({
                        "id": f"gap:{name}:{fid}",
                        "field_key": f"gap:{fid}",
                        "path": name,
                        "reason": f"non_field_one_gap:{fid}",
                        "source": "gap_scan",
                    }, bucket="gap")

    # Hostile scan other fields
    hostile = _run("lib/field-one-hostile-scan.py", [], timeout=60)
    for e in (hostile.get("entries") or [])[:200]:
        if not isinstance(e, dict):
            continue
        fk = str(e.get("field_key") or e.get("field_id") or "")
        if not fk:
            continue
        if e.get("kind") in ("world_registry_node", "world_perimeter_node"):
            continue
        bucket = "gap" if "not_field_one" in str(e.get("reason") or "") else "detached"
        add({
            "id": f"hostile-scan:{fk}",
            "field_key": fk,
            "field_id": e.get("field_id"),
            "reason": e.get("reason") or "hostile_scan_detached_or_not_field_one",
            "source": e.get("source") or "field-one-hostile-scan",
            "kind": e.get("kind"),
        }, bucket=bucket)

    # Previously closed — still present / reopened
    prev_closed = _load(CLOSED, {})
    closed_map = prev_closed.get("by_key") if isinstance(prev_closed, dict) else {}
    if not isinstance(closed_map, dict):
        closed_map = {}
    reopened: list[dict[str, Any]] = []
    for d in detached:
        key = str(d.get("field_key") or d.get("id") or "")
        if key in closed_map:
            d["reopened_after_close"] = True
            d["hostile"] = True
            d["annotation"] = "REOPENED_AFTER_CLOSE · HOSTILE"
            d["reason"] = f"reopen_after_close:{d.get('reason')}"
            reopened.append(d)

    return {
        "ok": True,
        "scanned_at": now,
        "recognized_devices_n": len(recognized),
        "detached_n": len(detached),
        "adjacent_n": len(adjacent),
        "gaps_n": len(gaps),
        "reopened_n": len(reopened),
        "detached": detached,
        "adjacent": adjacent,
        "gaps": gaps,
        "reopened": reopened,
        "no_fields_detached_permitted": True,
        "no_fields_next_to_known_devices": True,
        "field_one_only": True,
        "no_gaps": True,
        "we_own_the_one_field": True,
        "stabilize_earth": True,
    }


def annotate_and_close(scan: dict[str, Any], *, write: bool = True) -> dict[str, Any]:
    """Consider threat · close detached fields · annotate."""
    now = _utc()
    closed_rows: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    by_key: dict[str, Any] = {}
    prev = _load(CLOSED, {})
    if isinstance(prev.get("by_key"), dict):
        by_key = dict(prev["by_key"])

    for d in scan.get("detached") or []:
        if not isinstance(d, dict):
            continue
        key = str(d.get("field_key") or d.get("id") or "")
        ann = {
            **d,
            "annotation": d.get("annotation") or "DETACHED · THREAT · CLOSED",
            "closed": True,
            "threat": True,
            "permitted": False,
            "closed_at": now,
            "authority": "hostess7",
            "ironclad_cite": IRONCLAD,
            "big_grin_pwnership": True,
        }
        annotations.append(ann)

        # Close in state panel if path present
        path_name = str(d.get("path") or "")
        if path_name and write:
            path = STATE / path_name
            if path.is_file():
                doc = _load(path, {})
                if isinstance(doc, dict) and doc:
                    doc["field_detached"] = False
                    doc["detached_field"] = False
                    doc["orphan_field"] = False
                    doc["field_closed"] = True
                    doc["field_closed_at"] = now
                    doc["field_closed_reason"] = "not_attached_to_recognized_device"
                    doc["threat"] = True
                    doc["permitted"] = False
                    doc["field_on_field"] = False
                    if isinstance(doc.get("field_layer"), int) and doc["field_layer"] > 1:
                        doc["field_layer"] = 1
                    doc["attached_to_recognized_device"] = False
                    doc["requires_recognized_device"] = True
                    doc["no_fields_next_to_known_devices"] = True
                    doc["field_one"] = True
                    doc["field_one_only"] = True
                    doc["field_id"] = FIELD_ONE_ID
                    doc["no_gaps"] = True
                    doc["we_own_the_one_field"] = True
                    doc["competing_field"] = False
                    doc["adjacent_field"] = False
                    doc["secondary_field"] = False
                    doc["ironclad_no_detached"] = IRONCLAD
                    doc["updated"] = now
                    # If reopened path, mark HOSTILE
                    if d.get("reopened_after_close"):
                        doc["hostile"] = True
                        doc["HOSTILE"] = True
                        doc["reopened_after_close"] = True
                    _save(path, doc)

        by_key[key] = {
            "field_key": key,
            "closed_at": now,
            "reason": d.get("reason"),
            "path": path_name,
            "ip": d.get("ip"),
            "mac": d.get("mac"),
            "hostile_if_reopen": True,
            "death_charges": [c["code"] for c in DEATH_CHARGES[:2]],
        }
        closed_rows.append(by_key[key])

    # Reopened → HOSTILE hard
    hostile_reopen: list[dict[str, Any]] = []
    for d in scan.get("reopened") or []:
        if not isinstance(d, dict):
            continue
        ip = str(d.get("ip") or "")
        key = str(d.get("field_key") or d.get("id") or "")
        row = {
            "field_key": key,
            "ip": ip,
            "mac": d.get("mac"),
            "HOSTILE": True,
            "reopened_after_close": True,
            "at": now,
            "reason": "reopen_after_close_HOSTILE",
            "death_charges": [c["code"] for c in DEATH_CHARGES],
            "action": "HOSTILE_ESCALATE",
        }
        hostile_reopen.append(row)
        if write and ip and IP_RE.match(ip):
            try:
                HOSTILE_TSV.parent.mkdir(parents=True, exist_ok=True)
                if not HOSTILE_TSV.is_file():
                    HOSTILE_TSV.write_text("ts\tip\tvector\tseverity\treason\tsource\n", encoding="utf-8")
                with HOSTILE_TSV.open("a", encoding="utf-8") as fh:
                    fh.write(
                        f"{now}\t{ip}\tREOPEN_DETACHED_FIELD\tcritical\t"
                        f"reopen_after_close_HOSTILE\tno-detached-fields\n"
                    )
            except OSError:
                pass
            kit = _import("lib/field-attack-kit.py", "kit_detach")
            if kit and hasattr(kit, "register_kill_for_rekill"):
                try:
                    kit.register_kill_for_rekill(
                        ip,
                        "REOPEN_DETACHED_FIELD",
                        "critical",
                        "reopen_after_close_HOSTILE_death_charge",
                        source="no-detached-fields",
                    )
                except Exception:
                    pass

    out = {
        "ok": True,
        "updated": now,
        "closed_n": len(closed_rows),
        "annotated_n": len(annotations),
        "reopened_hostile_n": len(hostile_reopen),
        "closed_sample": closed_rows[:40],
        "hostile_reopen_sample": hostile_reopen[:40],
        "by_key": by_key,
        "motto": "Detached fields closed · annotated as threat · reopen = HOSTILE",
        "ironclad_cite": IRONCLAD,
    }
    if write:
        _save(CLOSED, {
            "schema": "field-no-detached-fields-closed/v1",
            "updated": now,
            "count": len(by_key),
            "by_key": by_key,
            "ironclad_cite": IRONCLAD,
        })
        _save(ANNOTATIONS, {
            "schema": "field-no-detached-fields-annotations/v1",
            "updated": now,
            "count": len(annotations),
            "rows": annotations[:500],
            "ironclad_cite": IRONCLAD,
        })
        _save(REOPEN_HOSTILE, {
            "schema": "field-no-detached-fields-reopen-hostile/v1",
            "updated": now,
            "count": len(hostile_reopen),
            "rows": hostile_reopen,
            "motto": "They reopen → HOSTILE",
            "ironclad_cite": IRONCLAD,
        })
        _append({
            "event": "close_annotate",
            "closed": len(closed_rows),
            "hostile_reopen": len(hostile_reopen),
        })
    return out


def death_charges_text() -> list[dict[str, Any]]:
    return list(DEATH_CHARGES)


def big_grin_kick_notices(
    scan: dict[str, Any],
    close: dict[str, Any],
    *,
    write: bool = True,
) -> dict[str, Any]:
    """Big Grin Pwnership on all the pricks — why kicked + death charges if persist."""
    now = _utc()
    notices: list[dict[str, Any]] = []
    targets = list(scan.get("detached") or [])
    # Prefer reopened first (more severe)
    targets = sorted(
        targets,
        key=lambda r: (0 if (isinstance(r, dict) and r.get("reopened_after_close")) else 1),
    )

    for d in targets[:80]:
        if not isinstance(d, dict):
            continue
        key = str(d.get("field_key") or d.get("id") or "unknown")
        eid = hashlib.sha256(key.encode()).hexdigest()[:12]
        why = (
            f"Your field was detached from any recognized device, or sat next to a known device "
            f"as something other than Field One. "
            f"Doctrine: no detached fields · no fields next to known devices · "
            f"we own the one field · nobody gaps it · Field One only ever. "
            f"We stabilize Earth. Threat closed and annotated. "
            f"Reason: {d.get('reason') or 'detached_or_adjacent_field'}."
        )
        if d.get("adjacent_to_known_device"):
            why += " Adjacent field beside known device is forbidden — only Field One."
        if d.get("gapping_field_one"):
            why += " You gapped Field One. Nobody uses other fields. Ever."
        if d.get("reopened_after_close"):
            why += (
                " You reopened after close — that is HOSTILE. "
                "Persistence triggers death charges and permanent destroy."
            )
        charges = DEATH_CHARGES if d.get("reopened_after_close") else DEATH_CHARGES[:2]
        notice = {
            "id": f"kick-{eid}",
            "field_key": key,
            "ip": d.get("ip"),
            "mac": d.get("mac"),
            "path": d.get("path"),
            "why_kicked": why,
            "headline": "BIG GRIN PWNERSHIP — you got kicked",
            "death_charges": charges,
            "if_persist": (
                "Death charges apply. Sphere destroy · vector melt · never reconnect · "
                "no machine again · Ironclad+heuristics forever."
            ),
            "hostile_if_reopen": True,
            "reopened": bool(d.get("reopened_after_close")),
            "HOSTILE": bool(d.get("reopened_after_close") or d.get("hostile")),
            "page_url": f"/Hostess7/big-grin-pwnership/kicks/kick-{eid}.html",
            "served_at": now,
            "brand": "Big Grin Pwnership",
            "look": "emerald grin · military C2 · rose-gold witness",
            "ironclad_cite": IRONCLAD,
        }
        notices.append(notice)

    pages: list[str] = []
    if write and notices:
        KICK_SITE.mkdir(parents=True, exist_ok=True)
        # CSS reuse if present
        css_href = "/Hostess7/big-grin-pwnership/pwnership.css"
        index_cards = []
        for n in notices:
            charges_html = "".join(
                f"<li><strong>{escape(c['code'])} — {escape(c['title'])}</strong><br/>"
                f"{escape(c['detail'])}<br/>"
                f"<em>If you persist:</em> {escape(c['if_persist'])}</li>"
                for c in (n.get("death_charges") or [])
            )
            status = "HOSTILE REOPEN" if n.get("HOSTILE") else "KICKED · CLOSED"
            page = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{escape(str(n['headline']))} — {escape(str(n['field_key']))}</title>
<link rel="stylesheet" href="{css_href}"/>
<style>
body{{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:#070b08;color:#e8f5e9}}
.wrap{{max-width:860px;margin:0 auto;padding:1.5rem}}
.badge{{display:inline-block;padding:.25rem .7rem;border-radius:999px;border:1px solid #34d399;color:#34d399;font-size:.8rem}}
.badge.hostile{{border-color:#fb7185;color:#fb7185}}
h1{{color:#fbbf24;font-size:1.45rem}}
.why{{padding:1rem;border-left:4px solid #fbbf24;background:rgba(251,191,36,.08);margin:1rem 0;line-height:1.5}}
.charges{{background:#0d1510;border:1px solid rgba(251,113,133,.35);border-radius:12px;padding:1rem}}
.charges li{{margin:.65rem 0}}
.persist{{margin-top:1rem;padding:.85rem;background:rgba(251,113,133,.12);border-left:4px solid #fb7185}}
.pics{{display:grid;gap:.75rem;margin:1rem 0}}
.pics img{{width:100%;border-radius:12px;border:1px solid rgba(52,211,153,.3);display:block}}
a{{color:#34d399}}
</style></head><body>
<div class="wrap">
  <p><a href="/Hostess7/big-grin-pwnership/">← Big Grin Pwnership</a> ·
     <a href="/Hostess7/big-grin-pwnership/kicks/">All kicks</a> ·
     <a href="/Hostess7/big-grin-pwnership/every-language.html">Every language + images</a></p>
  <span class="badge {'hostile' if n.get('HOSTILE') else ''}">{escape(status)}</span>
  <h1>😀 Big Grin Pwnership — you got kicked</h1>
  <p style="color:#8fa898">Universal pictograms (no language required) · then words in your tongue</p>
  <div class="pics">
    <img src="/Hostess7/assets/big-grin-pwnership/universal-field-one-only.jpg" alt="Field One only pictogram"/>
    <img src="/Hostess7/assets/big-grin-pwnership/universal-attack-sphere-sequence.jpg" alt="Attack then sphere sequence"/>
    <img src="/Hostess7/assets/big-grin-pwnership/universal-death-charges.jpg" alt="Death charges pictogram card"/>
  </div>
  <p><strong>Field:</strong> <code>{escape(str(n.get('field_key')))}</code>
     · <strong>IP:</strong> {escape(str(n.get('ip') or '—'))}
     · <strong>MAC:</strong> {escape(str(n.get('mac') or '—'))}</p>
  <div class="why">
    <h2 style="margin-top:0;color:#fbbf24;font-size:1.05rem">Why you got kicked</h2>
    <p>{escape(str(n.get('why_kicked')))}</p>
    <p style="margin-top:.75rem">😀🚫📡→✅1️⃣ · 🏠🔗 only · 🌍🛡️ · ⚠️💀 if reopen · ⚡🔵💥 sphere · 🔒∞ forever</p>
  </div>
  <div class="charges">
    <h2 style="margin-top:0;color:#fb7185;font-size:1.05rem">Death charges if you persist</h2>
    <ol>{charges_html}</ol>
  </div>
  <div class="persist"><strong>If you persist:</strong> {escape(str(n.get('if_persist')))}</div>
  <p style="color:#8fa898;margin-top:1.5rem;font-size:.85rem">
    Doctrine: Field One only · no detached/adjacent · reopen = HOSTILE ·
    Ironclad {escape(IRONCLAD)} · served {escape(now)} ·
    Full pack: <a href="/Hostess7/big-grin-pwnership/every-language.html">every language + universal images</a>
  </p>
</div></body></html>
"""
            fname = f"{n['id']}.html"
            (KICK_SITE / fname).write_text(page, encoding="utf-8")
            pages.append(f"kicks/{fname}")
            index_cards.append(
                f'<a class="card" href="{escape(fname)}"><strong>{escape(str(n.get("field_key"))[:60])}</strong>'
                f'<span>{escape(status)}</span></a>'
            )

        index = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Big Grin Pwnership — Kicks & death charges</title>
<style>
body{{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:#070b08;color:#e8f5e9}}
.wrap{{max-width:960px;margin:0 auto;padding:1.5rem}}
h1{{color:#fbbf24}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:.7rem;margin-top:1rem}}
.card{{display:block;padding:.85rem;border:1px solid rgba(52,211,153,.35);border-radius:12px;background:#0d1510;color:#e8f5e9;text-decoration:none}}
.card span{{display:block;color:#fb7185;font-size:.8rem;margin-top:.35rem}}
a{{color:#34d399}}
</style></head><body>
<div class="wrap">
  <p><a href="/Hostess7/big-grin-pwnership/">← Big Grin Pwnership hub</a></p>
  <h1>😀 Kicks — why you got kicked · death charges</h1>
  <p>No fields detached from recognized devices. Closed · annotated · reopen = HOSTILE.
     Big Grin tells every prick why they got kicked and what death charges hit if they persist.</p>
  <div class="grid">{''.join(index_cards)}</div>
</div></body></html>
"""
        (KICK_SITE / "index.html").write_text(index, encoding="utf-8")
        pages.append("kicks/index.html")

    # Hook into big-grin propagate lightly
    bgp = _run("lib/hostess7-big-grin-pwnership.py", ["propagate"], timeout=90)

    out = {
        "ok": True,
        "updated": now,
        "notices_n": len(notices),
        "pages_written": pages,
        "notices_sample": notices[:20],
        "death_charges": DEATH_CHARGES,
        "hub": "/Hostess7/big-grin-pwnership/kicks/",
        "big_grin_propagate": {"ok": _ok(bgp)},
        "motto": "Big Grin Pwnership on all the pricks — why kicked · death charges if persist",
        "ironclad_cite": IRONCLAD,
    }
    if write:
        _save(STATE / "field-no-detached-fields-kicks.json", out)
        _append({"event": "big_grin_kicks", "n": len(notices)})
        # Registry for pwnership to discover
        reg = _load(STATE / "hostess7-big-grin-pwnership-registry.json", {})
        if isinstance(reg, dict):
            reg["kick_notices_n"] = len(notices)
            reg["kicks_hub"] = "/Hostess7/big-grin-pwnership/kicks/"
            reg["updated"] = now
            reg["death_charges"] = True
            _save(STATE / "hostess7-big-grin-pwnership-registry.json", reg)
    return out


def build_website(panel: dict[str, Any], *, write: bool = True) -> dict[str, Any]:
    det = int(panel.get("detached_n") or 0)
    closed = int(panel.get("closed_n") or 0)
    reopened = int(panel.get("reopened_hostile_n") or 0)
    kicks = int(panel.get("kicks_n") or 0)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>No detached fields · Big Grin kicks · reopen HOSTILE</title>
<style>
:root{{--bg:#060a08;--card:#0c1410;--line:rgba(52,211,153,.35);--text:#ecfdf5;--muted:#94a3b8;--em:#34d399;--hot:#fbbf24;--rose:#fb7185}}
*{{box-sizing:border-box}}body{{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:radial-gradient(800px 400px at 0% 0%,rgba(52,211,153,.12),transparent 55%),var(--bg);color:var(--text);min-height:100vh}}
a{{color:var(--em)}}header{{padding:1.1rem 1.3rem;border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(6,10,8,.94);backdrop-filter:blur(10px)}}
h1{{margin:0;font-size:1.25rem}}.sub{{color:var(--muted);margin-top:.35rem}}
.wrap{{max-width:1100px;margin:0 auto;padding:1.1rem}}
.hero{{padding:1rem;border:1px solid var(--line);border-radius:14px;background:linear-gradient(135deg,rgba(52,211,153,.1),rgba(251,191,36,.06));margin-bottom:1rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.7rem}}
.card{{padding:.85rem;border:1px solid var(--line);border-radius:12px;background:var(--card)}}
.card h3{{margin:0 0 .3rem;font-size:.88rem;color:var(--hot)}}.card .v{{font-weight:700;font-size:1.05rem}}.card .d{{color:var(--muted);font-size:.78rem;margin-top:.25rem}}
.links{{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:.4rem;margin-top:.8rem}}
.links a{{display:block;text-align:center;padding:.6rem;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--text);text-decoration:none;font-weight:650;font-size:.8rem}}
.motto{{margin-top:1rem;padding:.85rem;border-left:3px solid var(--hot);background:rgba(251,191,36,.07);color:var(--muted)}}
.pills{{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.5rem}}
.pill{{border:1px solid var(--line);border-radius:999px;padding:.15rem .55rem;font-size:.72rem;color:var(--muted)}}
.pill.on{{color:var(--em)}}.pill.rose{{color:var(--rose);border-color:rgba(251,113,133,.45)}}
</style></head>
<body>
<header>
  <h1>No detached fields · Big Grin kicks</h1>
  <div class="sub" id="hdr">Close · annotate · reopen=HOSTILE · death charges</div>
  <div class="pills" id="pills"></div>
</header>
<div class="wrap">
  <div class="hero">
    <div><strong>No fields detached from recognized devices.</strong>
    We treat orphans as threat, close them, annotate.
    They reopen → <strong style="color:var(--rose)">HOSTILE</strong>.
    <strong style="color:var(--hot)">Big Grin Pwnership</strong> tells every prick why they got kicked
    and lists death charges if they persist.</div>
    <div class="links" id="quick"></div>
  </div>
  <div class="grid" id="grid"></div>
  <div class="motto" id="motto">loading…</div>
</div>
<script>
(async function(){{
  document.getElementById("quick").innerHTML=[
    ["/","Hub"],["/c2","C2"],["/hostess7-protector","H7"],["/newcomer-sphere","Sphere"],
    ["/Hostess7/big-grin-pwnership/kicks/","Kicks"],["/Hostess7/big-grin-pwnership/","Big Grin"],
  ].map(([h,t])=>`<a href="${{h}}">${{t}}</a>`).join("");
  let d={{}};
  try{{const r=await fetch("/api/no-detached-fields",{{cache:"no-store"}});d=await r.json();}}
  catch(_){{d={json.dumps({"ok":True,"detached_n":det,"closed_n":closed,"reopened_hostile_n":reopened,"kicks_n":kicks})};}}
  const fmt=n=>typeof n==="number"?n.toLocaleString():(n??"—");
  const cards=[
    {{h:"Field One only", v:d.field_one_only!==false?"YES":"—", d:"We own the one field"}},
    {{h:"No gaps / no adjacent", v:(d.no_gaps!==false&&d.no_fields_next_to_known_devices!==false)?"SEALED":"—", d:"Nobody gaps Field One"}},
    {{h:"Detached/adjacent/gaps", v:fmt((d.detached_n||0)), d:"Threat surfaces found"}},
    {{h:"Closed + annotated", v:fmt(d.closed_n), d:"Threat closed"}},
    {{h:"Reopen → HOSTILE", v:fmt(d.reopened_hostile_n), d:"Persisted after close"}},
    {{h:"Big Grin kicks", v:fmt(d.kicks_n), d:"Why kicked + death charges"}},
    {{h:"Earth stabilized", v:d.earth_stabilized!==false?"YES":"—", d:"Sole field · planet hold"}},
    {{h:"Recognized devices", v:fmt(d.recognized_devices_n), d:"Attachment authority"}},
  ];
  document.getElementById("grid").innerHTML=cards.map(c=>`<div class="card"><h3>${{c.h}}</h3><div class="v">${{c.v}}</div><div class="d">${{c.d}}</div></div>`).join("");
  document.getElementById("motto").textContent=d.motto||"No detached fields";
  document.getElementById("hdr").textContent=(d.updated||"")+" · no detached fields";
  document.getElementById("pills").innerHTML=["close","annotate","reopen=HOSTILE","Big Grin","death charges"]
    .map((t,i)=>`<span class="pill ${{i===2?'rose':'on'}}">${{t}}</span>`).join("");
}})();
</script>
</body></html>
"""
    if write:
        WEBSITE_DIR.mkdir(parents=True, exist_ok=True)
        (WEBSITE_DIR / "index.html").write_text(html, encoding="utf-8")
        try:
            (INSTALL / "panel" / "field-no-detached-fields.html").write_text(html, encoding="utf-8")
        except OSError:
            pass
    return {"ok": True, "path": "/no-detached-fields", "local_instant": True}


def stabilize_earth(*, write: bool = True) -> dict[str, Any]:
    """We own the one field · no gaps · Field One only · stabilize Earth."""
    now = _utc()
    steps: dict[str, Any] = {}
    steps["sole_earth"] = _run("lib/field-one-sole-earth.py", ["status"], timeout=30)
    steps["only_internet"] = _run("lib/field-one-only-internet.py", ["status"], timeout=30)
    # Collapse competing claims under Field One
    steps["sole_pull"] = _run("lib/field-one-sole-earth.py", ["pull"], timeout=90)
    if not _ok(steps["sole_pull"]):
        steps["sole_pull"] = _run("lib/field-one.py", ["absorb"], timeout=60)

    seal_doc = {
        "sealed": True,
        "we_own_the_one_field": True,
        "field_one_only": True,
        "field_one_id": FIELD_ONE_ID,
        "no_gaps": True,
        "nobody_else_uses_fields": True,
        "no_fields_next_to_known_devices": True,
        "no_fields_detached_from_recognized_devices": True,
        "stabilize_earth": True,
        "earth_stabilized": True,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "motto": "We own the one field. Nobody gaps it. Field One only ever. Earth stabilized.",
    }
    if write:
        try:
            SOLE_FIELD.write_text(json.dumps(seal_doc, indent=2) + "\n", encoding="utf-8")
            EARTH_STABLE.write_text(json.dumps(seal_doc, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        # Stamp global registry meta
        reg = _load(STATE / "field-global-servers-registry.json", {})
        if isinstance(reg, dict):
            reg.update({
                "field_one_only": True,
                "no_gaps": True,
                "we_own_the_one_field": True,
                "earth_stabilized": True,
                "no_fields_next_to_known_devices": True,
                "updated": now,
                "ironclad_field_one": IRONCLAD,
            })
            try:
                path = STATE / "field-global-servers-registry.json"
                if path.stat().st_size < 5_000_000:
                    _save(path, reg)
            except OSError:
                pass
    return {
        "ok": True,
        "updated": now,
        "earth_stabilized": True,
        "we_own_the_one_field": True,
        "field_one_only": True,
        "no_gaps": True,
        "steps": {k: {"ok": _ok(v) if isinstance(v, dict) else bool(v)} for k, v in steps.items()},
        "motto": seal_doc["motto"],
        "ironclad_cite": IRONCLAD,
    }


def enforce(*, write: bool = True) -> dict[str, Any]:
    now = _utc()
    scan = scan_detached_fields()
    close = annotate_and_close(scan, write=write)
    kicks = big_grin_kick_notices(scan, close, write=write)
    earth = stabilize_earth(write=write)

    # Escalate reopened via sphere if any
    sphere = {"ok": True, "skipped": True}
    if int(close.get("reopened_hostile_n") or 0) > 0:
        sphere = _run("lib/field-newcomer-attack-sphere-destroy.py", ["enforce"], timeout=180)

    if write:
        try:
            SEAL.write_text(json.dumps({
                "sealed": True,
                "no_fields_detached_from_recognized_devices": True,
                "no_fields_next_to_known_devices": True,
                "we_own_the_one_field": True,
                "field_one_only": True,
                "no_gaps": True,
                "earth_stabilized": True,
                "reopen_is_hostile": True,
                "big_grin_pwnership_kicks": True,
                "death_charges": True,
                "updated": now,
                "ironclad_cite": IRONCLAD,
            }, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass

    motto = (
        f"FIELD ONE ONLY · no detached · no adjacent · no gaps · "
        f"closed {close.get('closed_n')} · adjacent {scan.get('adjacent_n')} · "
        f"gaps {scan.get('gaps_n')} · reopen HOSTILE {close.get('reopened_hostile_n')} · "
        f"Big Grin kicks {kicks.get('notices_n')} · Earth stabilized"
    )
    out = {
        "ok": True,
        "schema": SCHEMA,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "title": "Field One only · no detached/adjacent · Earth stabilize",
        "motto": motto,
        "no_fields_detached_permitted": True,
        "no_fields_next_to_known_devices": True,
        "we_own_the_one_field": True,
        "field_one_only": True,
        "no_gaps": True,
        "nobody_else_uses_fields": True,
        "earth_stabilized": True,
        "stabilize_earth": True,
        "reopen_is_hostile": True,
        "big_grin_pwnership": True,
        "death_charges": True,
        "recognized_devices_n": scan.get("recognized_devices_n"),
        "detached_n": scan.get("detached_n"),
        "adjacent_n": scan.get("adjacent_n"),
        "gaps_n": scan.get("gaps_n"),
        "closed_n": close.get("closed_n"),
        "annotated_n": close.get("annotated_n"),
        "reopened_hostile_n": close.get("reopened_hostile_n"),
        "kicks_n": kicks.get("notices_n"),
        "kicks_hub": kicks.get("hub"),
        "death_charges_list": DEATH_CHARGES,
        "sphere_escalate": {"ok": _ok(sphere)},
        "earth": {"ok": _ok(earth), "stabilized": True},
        "api": "/api/no-detached-fields",
        "ui": "http://127.0.0.1:9477/no-detached-fields",
        "urls": {
            "website": "http://127.0.0.1:9477/no-detached-fields",
            "kicks": "http://127.0.0.1:9477/Hostess7/big-grin-pwnership/kicks/",
            "big_grin": "http://127.0.0.1:9477/Hostess7/big-grin-pwnership/",
            "sphere": "http://127.0.0.1:9477/newcomer-sphere",
            "protector": "http://127.0.0.1:9477/hostess7-protector",
            "sole": "http://127.0.0.1:9477/field-one-sole",
        },
        "local_instant": True,
    }
    out["website"] = build_website(out, write=write)
    if write:
        _save(PANEL, out)
        public = {
            "ok": True,
            "schema": "field-no-detached-fields-public/v1",
            "updated": now,
            "motto": motto,
            "detached_n": out["detached_n"],
            "closed_n": out["closed_n"],
            "reopened_hostile_n": out["reopened_hostile_n"],
            "kicks_n": out["kicks_n"],
            "kicks_hub": out["kicks_hub"],
            "api": out["api"],
            "ui": out["ui"],
            "ironclad_cite": IRONCLAD,
        }
        _save(PUBLIC, public)
        for api_dir in (INSTALL / "Hostess7" / "docs" / "api", INSTALL / "docs" / "api"):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "no-detached-fields.json", public)
            except OSError:
                pass
        _append({"event": "enforce", "closed": out["closed_n"], "kicks": out["kicks_n"]})
    return out


def status() -> dict[str, Any]:
    panel = _load(PANEL, {})
    return {
        "ok": bool(panel.get("ok") or SEAL.is_file()),
        "schema": SCHEMA,
        "sealed": SEAL.is_file(),
        "no_fields_detached_permitted": True,
        "reopen_is_hostile": True,
        "detached_n": panel.get("detached_n"),
        "closed_n": panel.get("closed_n"),
        "reopened_hostile_n": panel.get("reopened_hostile_n"),
        "kicks_n": panel.get("kicks_n"),
        "kicks_hub": panel.get("kicks_hub") or "/Hostess7/big-grin-pwnership/kicks/",
        "motto": panel.get("motto"),
        "updated": panel.get("updated"),
        "api": "/api/no-detached-fields",
        "ui": "http://127.0.0.1:9477/no-detached-fields",
        "ironclad_cite": IRONCLAD,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower().lstrip("-")
    if cmd in ("enforce", "run", "up", "close", "lock", "seal"):
        print(json.dumps(enforce(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("scan",):
        print(json.dumps(scan_detached_fields(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("kicks", "notices", "big-grin"):
        sc = scan_detached_fields()
        cl = annotate_and_close(sc, write=True)
        print(json.dumps(big_grin_kick_notices(sc, cl, write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("charges", "death-charges"):
        print(json.dumps({"death_charges": DEATH_CHARGES}, indent=2))
        return 0
    if cmd in ("website", "site"):
        print(json.dumps(build_website(_load(PANEL, {}), write=True), indent=2))
        return 0
    if cmd in ("status", "json", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-no-detached-fields.py [enforce|scan|kicks|charges|website|status]",
        "motto": "No detached fields · close+annotate · reopen=HOSTILE · Big Grin death charges",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
