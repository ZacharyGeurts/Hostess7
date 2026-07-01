#!/usr/bin/env pythong
"""KILROY Field Brain — Hostess7 + Ironclad + Universal Protector + gatekeeper stack verdicts."""
from __future__ import annotations

import importlib.util
import ipaddress
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
KILROY = Path(os.environ.get("KILROY_ROOT", str(INSTALL / "KILROY")))
DOCTRINE = KILROY / "data" / "kilroy-field-brain-doctrine.json"
MARKER = STATE / "kilroy-field-brain.json"

_INFRA_DNS = frozenset({
    "8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1", "9.9.9.9", "149.112.112.112",
})


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
    tmp.replace(path)


def _mod(name: str, rel: str) -> Any | None:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_json(mod: Any | None, *argv: str) -> dict[str, Any]:
    if mod is None or not hasattr(mod, "main"):
        return {}
    import io
    from contextlib import redirect_stdout

    old = list(sys.argv)
    try:
        sys.argv = [argv[0] if argv else "mod", *(argv[1:] or ["json"])]
        buf = io.StringIO()
        with redirect_stdout(buf):
            mod.main()
        text = buf.getvalue().strip()
        return json.loads(text) if text else {}
    except (SystemExit, json.JSONDecodeError, OSError, ValueError):
        return {}
    finally:
        sys.argv = old


def _brain_live() -> bool:
    return os.environ.get("KILROY_BRAIN_LIVE", "0").strip().lower() in ("1", "true", "yes")


def _hostess7_slice() -> dict[str, Any]:
    neural = _load(HOSTESS7 / "data/hostess7-neural-stack.json", {})
    brain = _load(STATE / "hostess7-brain-guard-panel.json", {})
    if not brain and _brain_live():
        bg = _mod("h7_brain", "hostess7-brain-guard.py")
        if bg and hasattr(bg, "build_panel"):
            try:
                brain = bg.build_panel(write=False)
            except (OSError, TypeError, ValueError):
                brain = _run_json(bg, "hostess7-brain-guard.py", "json")
    return {
        "truth_adapt_floor": neural.get("truth_adapt_floor", 58),
        "truth_genius_floor": neural.get("truth_genius_floor", 72),
        "neural_guardian": True,
        "brain_verdict": brain.get("verdict"),
        "brain_verified": (brain.get("verification") or {}).get("verified"),
        "guard_score": brain.get("guard_score"),
        "brain_live": brain.get("brain_live"),
    }


def _ironclad_slice() -> dict[str, Any]:
    ic = _load(STATE / "ironclad-immediate.json", {})
    if not ic:
        imm = _mod("ironclad_imm", "ironclad-immediate.py")
        ic = _run_json(imm, "ironclad-immediate.py", "json")
    plate = ic.get("ironclad") if isinstance(ic.get("ironclad"), dict) else ic
    return {
        "verdict": plate.get("verdict") or ic.get("verdict"),
        "ironclad_sealed": plate.get("ironclad_sealed") or ic.get("ironclad_sealed"),
        "truth_percent": (plate.get("truth_serum") or {}).get("truth_percent"),
        "reality_field_live": (plate.get("super_intelligence_field") or {}).get("reality_field_live"),
        "ai_in_charge": plate.get("ai_in_charge") or ic.get("ai_in_charge"),
    }


def _final_eye_slice() -> dict[str, Any]:
    fe_py = INSTALL / "lib" / "kilroy-final-eye-brain.py"
    marker = _load(STATE / "kilroy-final-eye-brain.json", {})
    if marker:
        live = marker.get("live") or {}
        corpus = marker.get("corpus") or {}
        return {
            "ok": live.get("ok", True),
            "ocr_brain": True,
            "product": live.get("product") or "Final_Eye",
            "version": live.get("version"),
            "tesseract": (live.get("zocr") or {}).get("tesseract"),
            "manifest_captures": corpus.get("manifest_captures"),
            "ocr_bytes_total": corpus.get("ocr_bytes_total"),
            "recording": False,
            "live_feed_only": True,
            "proc": "/proc/kilroy_field/eye",
        }
    if not fe_py.is_file():
        return {"ok": False, "ocr_brain": False, "error": "kilroy-final-eye-brain.py missing"}
    fe = _mod("kilroy_fe", "kilroy-final-eye-brain.py")
    if fe and hasattr(fe, "live_slice"):
        try:
            live = fe.live_slice(ingest=False)
            return {
                "ok": live.get("ok", True),
                "ocr_brain": True,
                "product": live.get("product") or "Final_Eye",
                "version": live.get("version"),
                "tesseract": (live.get("zocr") or {}).get("tesseract"),
                "session_captures": (live.get("session") or {}).get("captures"),
                "recording": False,
                "live_feed_only": True,
                "proc": "/proc/kilroy_field/eye",
            }
        except (OSError, TypeError, ValueError):
            pass
    return _run_json(fe, "kilroy-final-eye-brain.py", "live") if fe else {"ok": False, "ocr_brain": False}


def _universal_slice() -> dict[str, Any]:
    doc = _load(STATE / "universal-protector-panel.json", {})
    if not doc:
        doc = _load(STATE / "universal-protector-runtime.json", {})
    if not doc and _brain_live():
        up = _mod("univ_prot", "universal-protector.py")
        if up and hasattr(up, "build_status"):
            try:
                doc = up.build_status(write=False)
            except TypeError:
                doc = up.build_status()
        else:
            doc = _run_json(up, "universal-protector.py", "json")
    pillars = doc.get("pillars") or {}
    return {
        "ok": doc.get("ok", True),
        "threat_warn_level": doc.get("threat_warn_level"),
        "hostess7_brain": (pillars.get("hostess7_brain") or {}).get("verdict"),
        "ironclad": (pillars.get("ironclad") or {}).get("verdict"),
        "right_to_exist": (pillars.get("right_to_exist") or {}).get("mandate_sealed"),
        "combinatorics_lock": (pillars.get("combinatorics") or {}).get("lock_ok"),
        "universal_lock": (doc.get("universal_lock") or {}).get("locked"),
    }


def _gatekeeper_hostile_ips() -> set[str]:
    gk = _mod("conn_gk", "connection-gatekeeper.py")
    if not gk or not hasattr(gk, "analyze_connections"):
        return set()
    try:
        import subprocess

        proc = subprocess.run(["ss", "-H", "-tunap"], capture_output=True, text=True, timeout=8)
        doc = gk.analyze_connections(proc.stdout.splitlines())
    except (OSError, subprocess.TimeoutExpired, AttributeError):
        return set()
    hostile: set[str] = set()
    for row in doc.get("connections") or []:
        if not isinstance(row, dict):
            continue
        verdict = str(row.get("verdict") or "").upper()
        rip = str(row.get("remote_ip") or row.get("peer_ip") or "")
        if rip and verdict in ("HOSTILE", "DENY", "KILL", "BLOCK", "STRIKE"):
            hostile.add(rip)
    return hostile


def _inside_sanctuary(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return False
    return bool(addr.is_loopback or addr.is_private or addr.is_link_local or addr.is_reserved)


def _point_for_ip(ip: str) -> dict[str, Any] | None:
    tsv = STATE / "field-hostile.tsv"
    if not tsv.is_file():
        return None
    try:
        for line in tsv.read_text(encoding="utf-8").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 2 and parts[1].strip() == ip:
                return {"ip": ip, "vector": parts[2] if len(parts) > 2 else "HOSTILE"}
    except OSError:
        pass
    return None


def _verdict_doc(
    ip: str,
    vector: str,
    strike: bool,
    reasons: list[str],
    stack: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "kilroy-field-brain-verdict/v1",
        "ts": _now(),
        "ip": ip,
        "vector": vector,
        "strike_authorized": strike,
        "refuse_reason": None if strike else (reasons[-1] if reasons else "kilroy_brain_deny"),
        "reasons": reasons,
        "stack": stack,
        "proc": "/proc/kilroy_field/brain",
    }


def evaluate_threat(
    ip: str,
    vector: str = "HOSTILE",
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full stack verdict — Hostess7 + Ironclad + Universal Protector + gatekeeper corroboration."""
    ip = ip.strip()
    reasons: list[str] = []
    strike = False

    if _inside_sanctuary(ip):
        reasons.append("kilroy_sanctuary_inside")
        return _verdict_doc(ip, vector, False, reasons, {})
    if ip in _INFRA_DNS and not _point_for_ip(ip):
        reasons.append("kilroy_infrastructure_sanctuary")
        return _verdict_doc(ip, vector, False, reasons, {})

    stack = {
        "hostess7": _hostess7_slice(),
        "ironclad": _ironclad_slice(),
        "universal_protector": _universal_slice(),
    }
    dossier = _point_for_ip(ip)
    gk_hostile = ip in _gatekeeper_hostile_ips()
    brain_ok = stack["hostess7"].get("brain_verdict") not in ("CORRUPT", "QUARANTINE", "FAIL")
    iron_ok = stack["ironclad"].get("ironclad_sealed") is not False
    univ_ok = stack["universal_protector"].get("ok") is not False

    if dossier and gk_hostile and brain_ok and iron_ok and univ_ok:
        ts = _mod("trust_strike", "trust-strike-engine.py")
        if ts and hasattr(ts, "gate_strike"):
            try:
                gate = ts.gate_strike(ip, {**dossier, "vector": vector, "ip": ip}, mode="auto")
            except (TypeError, ValueError, OSError):
                gate = {"authorized": False}
            if gate.get("authorized") and not gate.get("friendly_refused"):
                strike = True
                reasons.append("stack_corroborated_strike")
            else:
                reasons.append(gate.get("reason") or "trust_strike_denied")
        else:
            strike = True
            reasons.append("dossier_and_gatekeeper_corroborated")
    elif dossier:
        reasons.append("kilroy_defensive_awaiting_gatekeeper_corroboration")
    elif gk_hostile:
        reasons.append("kilroy_defensive_awaiting_dossier")
    else:
        reasons.append("kilroy_defensive_no_confirmed_threat")

    return _verdict_doc(ip, vector, strike, reasons, stack)


def build_board(*, write: bool = True) -> dict[str, Any]:
    h7 = _hostess7_slice()
    ic = _ironclad_slice()
    up = _universal_slice()
    fe = _final_eye_slice()
    doc = {
        "schema": "kilroy-field-brain/v1",
        "updated": _now(),
        "owner": "kilroy_kernel",
        "motto": "Hostess7 + Ironclad + Universal Protector — stack corroboration, not connect-to-kill",
        "defensive_only": os.environ.get("KILROY_DEFENSIVE_ONLY", "1") == "1",
        "war_scope": os.environ.get("KILROY_WAR_SCOPE", "defensive_perimeter"),
        "truth_floors": {
            "adapt": h7.get("truth_adapt_floor", 58),
            "genius": h7.get("truth_genius_floor", 72),
        },
        "hostess7": h7,
        "ironclad": ic,
        "universal_protector": up,
        "final_eye": fe,
        "stack_live": {
            "hostess7_brain_guard": bool(h7.get("brain_live") or h7.get("guard_score")),
            "ironclad_sealed": ic.get("ironclad_sealed"),
            "universal_lock": up.get("universal_lock"),
            "combinatorics_lock": up.get("combinatorics_lock"),
            "final_eye_ocr": fe.get("ok"),
        },
        "engines": (_load(DOCTRINE, {}) or {}).get("engines", {}),
        "proc": "/proc/kilroy_field/brain",
        "kilroy_root": str(KILROY),
        "install_root": str(INSTALL),
    }
    if write:
        _save(MARKER, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "board", "status"):
        print(json.dumps(build_board(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "evaluate" and len(sys.argv) > 2:
        print(json.dumps(evaluate_threat(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "HOSTILE"), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: kilroy-field-brain.py [json|board|evaluate IP [vector]]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())