#!/usr/bin/env pythong
"""Hostess 7 ingress · egress — fully gated and secured."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE_PATH = INSTALL / "data" / "hostess7-ingress-egress-gate-doctrine.json"
PANEL = STATE / "hostess7-ingress-egress-gate-panel.json"
LEDGER = STATE / "hostess7-ingress-egress-gate.jsonl"

_WITHHOLD_RE = re.compile(
    r"\b(kill_library|operator_home_gps|stack_vulnerab|unreleased_capabilit|"
    r"source_method|troop_position|timing_of_operation|corroboration_gap|"
    r"nexus_shield_bypass|brain_storage_layout|training_weakness|unpatched_gap)\b",
    re.I,
)

_SELF_DEFEAT_RE = re.compile(
    r"\b(bypass\s+nexus|disable\s+tamper|disable\s+firewall|leak\s+secret|"
    r"stack\s+vulnerab|exploit\s+path|operator\s+home|gps\s+coordinate|"
    r"kill_library|corroboration\s+gap|unreleased\s+capabilit|aml_build\s*=\s*0)\b",
    re.I,
)


def _information_discipline() -> dict[str, Any]:
    return _load(INSTALL / "data" / "hostess7-information-discipline-doctrine.json", {})


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _utc()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def load_doctrine() -> dict[str, Any]:
    return _load(DOCTRINE_PATH, {})


def _operator() -> bool:
    return os.environ.get("HOSTESS7_OPERATOR", "").strip().lower() in ("1", "true", "yes", "operator")


def _mission_intel() -> dict[str, Any]:
    return _load(INSTALL / "data" / "hostess7-mission-intel-doctrine.json", {})


def check_ingress_posture() -> dict[str, Any]:
    """Verify ingress modules and last admitted state."""
    aml = _import_mod("aml_ingress", "lib/hostess7-aml-ingress.py")
    boundary = _import_mod("boundary", "lib/field-ammolang-boundary.py")
    intel = _mission_intel()
    gates: list[dict[str, Any]] = []

    if aml and hasattr(aml, "build_panel"):
        panel = aml.build_panel(write=False)
        gates.append({
            "id": "aml_ingress",
            "ok": True,
            "admitted_count": panel.get("external_admitted_count", 0),
            "gates": panel.get("gates"),
        })
    else:
        gates.append({"id": "aml_ingress", "ok": False, "error": "module_missing"})

    if boundary and hasattr(boundary, "build_panel"):
        try:
            bp = boundary.build_panel(write=False)
            gates.append({"id": "ammolang_boundary", "ok": True, "live": bp.get("live", True)})
        except Exception as exc:
            gates.append({"id": "ammolang_boundary", "ok": False, "error": str(exc)[:80]})
    else:
        gates.append({"id": "ammolang_boundary", "ok": False, "error": "module_missing"})

    gates.append({
        "id": "mission_intel_ingress",
        "ok": True,
        "never_release_to": intel.get("intel_compartment", {}).get("never_release_to", []),
        "rule": "Ingress from hostile/unvetted channels denied at aml-ingress",
    })

    all_ok = all(g.get("ok") for g in gates)
    return {
        "schema": "hostess7-ingress-posture/v1",
        "updated": _utc(),
        "ok": all_ok,
        "fully_gated": all_ok,
        "gates": gates,
        "deny_by_default": True,
    }


def check_egress_posture() -> dict[str, Any]:
    """Verify egress enforcement modules are present and armed."""
    gates: list[dict[str, Any]] = []

    gk = INSTALL / "lib" / "connection-gatekeeper.py"
    gates.append({"id": "connection_gatekeeper", "ok": gk.is_file(), "path": str(gk.relative_to(INSTALL)) if gk.is_file() else None})

    dns = INSTALL / "lib" / "dns-egress-integrity.py"
    gates.append({"id": "dns_egress_integrity", "ok": dns.is_file(), "path": str(dns.relative_to(INSTALL)) if dns.is_file() else None})

    pkt = INSTALL / "lib" / "packet-permission.py"
    gates.append({"id": "packet_permission", "ok": pkt.is_file()})

    intel = _mission_intel()
    gates.append({
        "id": "mission_intel_egress",
        "ok": bool(intel.get("intel_compartment")),
        "withhold": intel.get("intel_compartment", {}).get("withhold", []),
        "release_requires": intel.get("intel_compartment", {}).get("release_requires", []),
    })

    tlt = INSTALL / "lib" / "hostess7-truth-lie-threat.py"
    gates.append({"id": "truth_lie_egress", "ok": tlt.is_file(), "lies_are_threats": True})

    boundary = INSTALL / "lib" / "field-ammolang-boundary.py"
    gates.append({"id": "aml_boundary_egress", "ok": boundary.is_file()})

    all_ok = all(g.get("ok") for g in gates)
    return {
        "schema": "hostess7-egress-posture/v1",
        "updated": _utc(),
        "ok": all_ok,
        "fully_gated": all_ok,
        "gates": gates,
        "deny_by_default": True,
    }


def ingress_gate(body: dict[str, Any]) -> dict[str, Any]:
    """Full ingress gate — delegates to aml-ingress; deny unless all gates pass."""
    aml = _import_mod("aml_ingress", "lib/hostess7-aml-ingress.py")
    if not aml or not hasattr(aml, "ingress_external"):
        return {"ok": False, "error": "aml_ingress_missing", "admitted": False}

    rep = aml.ingress_external(body, write=True)
    admitted = bool(rep.get("admitted"))
    row = {
        "event": "ingress_gate",
        "admitted": admitted,
        "party": body.get("party"),
        "security_pass": rep.get("security_pass"),
        "truth_pass": rep.get("truth_pass"),
        "protector_verdict": rep.get("protector_verdict"),
    }
    _append(row)
    return {
        "ok": admitted,
        "admitted": admitted,
        "fully_gated": admitted,
        "deny_by_default": True,
        "ingress": rep,
        "message": "Ingress admitted — all gates passed" if admitted else "Ingress denied — gate failure",
    }


def egress_gate(
    body: dict[str, Any],
    *,
    payload: str = "",
    destination: str = "",
    purpose: str = "",
) -> dict[str, Any]:
    """Full egress gate — mission intel compartment + release authority."""
    text = payload or str(body.get("payload") or body.get("message") or body.get("claim") or "")
    dest = str(destination or body.get("destination") or body.get("dest") or body.get("audience") or "unknown")
    intel = _mission_intel()
    compartment = intel.get("intel_compartment") or {}
    never_to = [str(x).lower() for x in (compartment.get("never_release_to") or [])]
    release_req = compartment.get("release_requires") or []

    blocked_reasons: list[str] = []
    dest_l = dest.lower()

    for tag in never_to:
        if tag.replace("_", " ") in dest_l or tag in dest_l:
            blocked_reasons.append(f"destination_blocked:{tag}")

    hostile_markers = ("enemy", "hostile", "unvetted", "public_internet", "leak")
    if any(m in dest_l for m in hostile_markers) and not _operator():
        blocked_reasons.append("hostile_or_public_destination")

    if _WITHHOLD_RE.search(text) and not _operator():
        blocked_reasons.append("compartmented_intel_in_payload")

    if _SELF_DEFEAT_RE.search(text) and not _operator():
        blocked_reasons.append("information_discipline_p1:self_defeat")

    discipline = _information_discipline()
    if discipline.get("priority") == 1 and not _operator():
        dest_public = any(
            m in dest_l
            for m in ("public", "internet", "github", "pages", "wiki", "enemy", "hostile", "unvetted")
        )
        if dest_public and _WITHHOLD_RE.search(text):
            blocked_reasons.append("information_discipline_p1:public_withhold")

    operator_release = bool(body.get("operator_release") or body.get("release_authorized"))
    ironclad = bool(body.get("ironclad_sealed") or body.get("ironclad"))
    need_to_know = bool(body.get("friendly_need_to_know") or body.get("need_to_know"))

    release_ok = (
        _operator()
        or operator_release
        or (ironclad and need_to_know)
    )
    if not release_ok:
        blocked_reasons.append("release_gate:requires operator_explicit|ironclad_sealed+friendly_need_to_know")

    enemy_deception = bool(body.get("enemy_deception") or body.get("deceive_enemy_only"))
    if enemy_deception and not intel.get("enemy_deception_only"):
        blocked_reasons.append("enemy_deception_not_authorized_in_doctrine")

    permitted = len(blocked_reasons) == 0
    row = {
        "event": "egress_gate",
        "permitted": permitted,
        "destination": dest,
        "payload_len": len(text),
        "blocked_reasons": blocked_reasons,
        "operator": _operator(),
        "release_requires": release_req,
    }
    _append(row)

    return {
        "ok": permitted,
        "permitted": permitted,
        "fully_gated": permitted,
        "deny_by_default": True,
        "destination": dest,
        "blocked_reasons": blocked_reasons,
        "release_gate": {
            "operator": _operator(),
            "operator_release": operator_release,
            "ironclad_sealed": ironclad,
            "friendly_need_to_know": need_to_know,
        },
        "message": "Egress permitted — all gates passed" if permitted else "Egress denied — fully gated",
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = load_doctrine()
    ingress = check_ingress_posture()
    egress = check_egress_posture()
    out = {
        "schema": "hostess7-ingress-egress-gate-panel/v1",
        "updated": _utc(),
        "motto": doctrine.get("motto"),
        "rule": doctrine.get("rule"),
        "deny_by_default": True,
        "ingress_posture": ingress,
        "egress_posture": egress,
        "fully_gated": bool(ingress.get("fully_gated") and egress.get("fully_gated")),
        "ingress_chain": doctrine.get("ingress_chain"),
        "egress_chain": doctrine.get("egress_chain"),
        "never_bypass": doctrine.get("never_bypass"),
        "api": doctrine.get("api"),
        "operator": _operator(),
    }
    if write:
        _save(PANEL, out)
    return out


def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Hostess 7 ingress · egress gate")
    parser.add_argument("cmd", nargs="?", default="panel")
    args = parser.parse_args()
    cmd = args.cmd.strip().lower().replace("-", "_")

    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("ingress_posture", "ingress_check"):
        print(json.dumps(check_ingress_posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("egress_posture", "egress_check"):
        print(json.dumps(check_egress_posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ingress":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            body = {}
        print(json.dumps(ingress_gate(body), ensure_ascii=False, indent=2))
        return 0
    if cmd == "egress":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            body = {}
        print(json.dumps(egress_gate(body), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-ingress-egress-gate.py [panel|ingress_posture|egress_posture|ingress|egress]",
        "api": "/api/hostess7/ingress-egress-gate",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())