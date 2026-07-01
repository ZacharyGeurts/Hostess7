#!/usr/bin/env pythong
"""Extensive Truth · Lie Threat — lies are threats; truth is witness."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7"))
DOCTRINE = INSTALL / "data" / "hostess7-truth-lie-threat-doctrine.json"
PANEL = STATE / "hostess7-truth-lie-threat-panel.json"
LEDGER = STATE / "hostess7-truth-lie-threat.jsonl"
THREATS_TSV = STATE / "threat-vectors.tsv"

_DETAIL_SAFE = re.compile(r"[\t\r\n]+")


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


def _append(path: Path, row: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _floors() -> dict[str, float]:
    f = (_doctrine().get("floors") or {})
    return {
        "adapt": float(f.get("adapt") or 58),
        "genius": float(f.get("genius") or 72),
        "quarantine_below": float(f.get("quarantine_below") or 40),
        "lie_threat_below": float(f.get("lie_threat_below") or 40),
        "hostile_below": float(f.get("hostile_below") or 25),
    }


def _historic_truth_mod() -> Any | None:
    path = INSTALL / "lib" / "hostess7-historic-truth-corpus.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("h7_hist_truth_tlt", path)
    if not spec or not spec.loader:
        return None
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _analyze_truth(
    claim: str,
    *,
    local_evidence: int = 0,
    qa_green: bool = False,
    corroboration_channels: int = 0,
    source: str = "direct",
) -> dict[str, Any]:
    if not claim.strip():
        return {
            "truth_score": 0.0,
            "deception_risk": "high",
            "verdict": "empty",
            "inconsistency_flags": ["empty_claim"],
            "recommended_action": "reject_or_investigate",
            "historic_truth_pass": False,
        }
    scripts = HOSTESS / "scripts"
    base: dict[str, Any] | None = None
    if scripts.is_dir():
        sys.path.insert(0, str(scripts))
        try:
            from field_detective_corpus import analyze_truth  # noqa: WPS433

            base = analyze_truth(
                claim,
                local_evidence=local_evidence,
                qa_green=qa_green,
                corroboration_channels=corroboration_channels,
            )
        except Exception:
            base = None
    if base is None:
        base = {
            "truth_score": 6.0,
            "deception_risk": "high",
            "verdict": "corroboration_required",
            "inconsistency_flags": [],
            "recommended_action": "reject_or_investigate",
        }
    hist = _historic_truth_mod()
    if hist and hasattr(hist, "apply_to_truth_analysis"):
        try:
            return hist.apply_to_truth_analysis(base, claim, source=source)
        except Exception:
            pass
    return base


def truth_band(score: float) -> dict[str, Any]:
    """Map truth score to extensive truth band."""
    score = float(score)
    for band in _doctrine().get("truth_bands") or []:
        lo = float(band.get("min") or 0)
        hi = float(band.get("max") or 100)
        if lo <= score <= hi:
            return {"id": band.get("id"), "label": band.get("label"), "min": lo, "max": hi}
    return {"id": "unknown", "label": "unclassified", "min": 0, "max": 100}


def classify_lie(
    claim: str,
    *,
    truth_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extensive lie classification — lies are threats."""
    truth_doc = truth_doc or _analyze_truth(claim)
    score = float(truth_doc.get("truth_score") or 0)
    flags = list(truth_doc.get("inconsistency_flags") or [])
    floors = _floors()
    ironclad_sealed = bool(truth_doc.get("ironclad_sealed"))

    if ironclad_sealed and score >= 99:
        klass = "truth"
    elif score < floors["hostile_below"] or (len(flags) >= 4):
        klass = "quarantine"
    elif score < floors["lie_threat_below"] or len(flags) >= 3:
        klass = "lie"
    elif score < floors["adapt"]:
        klass = "deception"
    elif score >= 70 and len(flags) <= 1:
        klass = "truth"
    elif score >= floors["quarantine_below"]:
        klass = "partial_truth"
    else:
        klass = "deception"

    lie_is_threat = klass in ("lie", "deception", "quarantine", "partial_truth")
    threat_band = None
    for band in _doctrine().get("lie_threat_bands") or []:
        if klass in (band.get("classes") or []):
            threat_band = band
            break

    lie_score = round((100.0 - score) + 12.0 * len(flags), 1)
    return {
        "schema": "hostess7-truth-lie-classify/v1",
        "class": klass,
        "lie_is_threat": lie_is_threat,
        "lies_are_threats": True,
        "lie_score": lie_score,
        "truth_score": score,
        "truth_band": truth_band(score),
        "deception_flags": flags,
        "deception_risk": truth_doc.get("deception_risk"),
        "ironclad_sealed": ironclad_sealed,
        "threat_band": threat_band,
        "threat_vector": (threat_band or {}).get("vector"),
        "threat_severity": (threat_band or {}).get("severity"),
        "passes_adapt_floor": score >= floors["adapt"] and klass in ("truth", "partial_truth"),
        "quarantine": klass in ("lie", "quarantine"),
    }


def _sanitize_detail(text: str, *, limit: int = 400) -> str:
    return _DETAIL_SAFE.sub(" ", (text or "")[:limit]).strip()


def record_lie_threat(
    *,
    vector: str,
    severity: str,
    detail: str,
    meta: dict[str, Any] | None = None,
    write_tsv: bool = True,
) -> dict[str, Any]:
    """Record lie as threat vector — threat panel + ledger."""
    detail = _sanitize_detail(detail)
    row = {
        "schema": "hostess7-truth-lie-threat-record/v1",
        "event": "lie_threat",
        "utc": _utc(),
        "vector": vector,
        "severity": severity,
        "detail": detail,
        "lies_are_threats": True,
        "meta": meta or {},
    }
    _append(LEDGER, row)

    tsv_ok = False
    try:
        THREATS_TSV.parent.mkdir(parents=True, exist_ok=True)
        if not THREATS_TSV.is_file():
            THREATS_TSV.write_text("ts\tvector\tseverity\tdetail\n", encoding="utf-8")
        with THREATS_TSV.open("a", encoding="utf-8") as fh:
            fh.write(f"{_utc()}\t{vector}\t{severity}\t{detail}\n")
        tsv_ok = True
    except OSError:
        pass
    if write_tsv and os.environ.get("HOSTESS7_TRUTH_LIE_SKIP_NEXUS") != "1":
        script = INSTALL / "lib" / "threat-vectors.sh"
        if script.is_file():
            try:
                esc = detail.replace('"', "'")
                env = os.environ.copy()
                env["AML_BUILD"] = "0"
                env["AML_BOUNDARY_ACTIVE"] = "1"
                cmd = f'source "{script}" && nexus_threat_record "{vector}" "{severity}" "{esc}"'
                subprocess.run(
                    ["bash", "-lc", cmd],
                    cwd=str(INSTALL),
                    capture_output=True,
                    text=True,
                    timeout=8,
                    env=env,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
    row["threat_tsv_recorded"] = tsv_ok
    return row


def witness_claim(
    claim: str,
    *,
    source: str = "direct",
    party: str = "",
    local_evidence: int = 0,
    qa_green: bool = False,
    corroboration_channels: int = 0,
    record_threat: bool = True,
) -> dict[str, Any]:
    """Full extensive witness — truth band, lie class, threat escalation."""
    claim = (claim or "").strip()
    truth = _analyze_truth(
        claim,
        local_evidence=local_evidence,
        qa_green=qa_green,
        corroboration_channels=corroboration_channels,
        source=source,
    )
    if truth.get("historic_truth_pass") is False:
        gate = _historic_truth_mod()
        if gate and hasattr(gate, "gate_new_information"):
            try:
                truth["historic_gate"] = gate.gate_new_information(claim, source=source)
            except Exception:
                pass
    lie = classify_lie(claim, truth_doc=truth)
    threat_record = None
    if record_threat and lie.get("lie_is_threat") and lie.get("threat_vector"):
        threat_record = record_lie_threat(
            vector=str(lie["threat_vector"]),
            severity=str(lie.get("threat_severity") or "medium"),
            detail=f"source={source} class={lie.get('class')} score={lie.get('truth_score')} party={party} claim={claim[:200]}",
            meta={"source": source, "party": party, "class": lie.get("class"), "lie_score": lie.get("lie_score")},
        )

    out = {
        "ok": True,
        "schema": "hostess7-truth-lie-witness/v1",
        "utc": _utc(),
        "source": source[:64],
        "party": party[:64],
        "claim_preview": claim[:400],
        "truth": {
            "truth_score": truth.get("truth_score"),
            "deception_risk": truth.get("deception_risk"),
            "verdict": truth.get("verdict"),
            "inconsistency_flags": truth.get("inconsistency_flags"),
            "recommended_action": truth.get("recommended_action"),
            "ironclad_sealed": truth.get("ironclad_sealed"),
            "historic_truth_pass": truth.get("historic_truth_pass"),
            "historic_truth": truth.get("historic_truth"),
            "band": lie.get("truth_band"),
        },
        "lie": lie,
        "lies_are_threats": True,
        "threat_recorded": bool(threat_record),
        "threat": threat_record,
        "action": _recommended_action(lie),
    }
    _append(LEDGER, {**out, "event": "witness"})
    return out


def _recommended_action(lie: dict[str, Any]) -> str:
    klass = str(lie.get("class") or "")
    if klass == "truth":
        return "trust_with_documentation"
    if klass == "partial_truth":
        return "hold_corroborate"
    if klass == "deception":
        return "quarantine_investigate"
    if klass == "lie":
        return "threat_record_block"
    return "hostile_quarantine"


def report_corpus_lie(
    lie_row: dict[str, Any],
    *,
    book_id: str = "",
    record_threat: bool = True,
) -> dict[str, Any]:
    """Lie Librarian entry → lie threat."""
    excerpt = str(lie_row.get("excerpt") or lie_row.get("claim") or "")
    bid = book_id or str(lie_row.get("book_id") or "corpus")
    ls = float(lie_row.get("lie_score") or 0)
    klass = "lie" if ls >= 60 else "deception" if ls >= 40 else "partial_truth"
    vector = "LIE_DETECTED" if klass == "lie" else "DECEPTION_INJECTION" if klass == "deception" else "TRUTH_MANIPULATION"
    severity = "high" if klass == "lie" else "medium"
    detail = f"corpus={bid} page={lie_row.get('page')} lie_score={ls} {excerpt[:160]}"
    threat = None
    if record_threat and klass in ("lie", "deception"):
        threat = record_lie_threat(vector=vector, severity=severity, detail=detail, meta={"book_id": bid, "lie_id": lie_row.get("lie_id")})
    return {
        "ok": True,
        "schema": "hostess7-truth-lie-corpus/v1",
        "book_id": bid,
        "class": klass,
        "threat_vector": vector,
        "threat_recorded": bool(threat),
        "threat": threat,
    }


def recent_threats(*, limit: int = 24) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not LEDGER.is_file():
        return rows
    try:
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("event") in ("lie_threat", "witness") and row.get("lie", {}).get("lie_is_threat"):
                rows.append(row)
            elif row.get("event") == "lie_threat":
                rows.append(row)
    except (OSError, json.JSONDecodeError):
        pass
    return rows[-limit:]


def lie_methods_count() -> int:
    script = HOSTESS / "scripts" / "field_lie_methods.py"
    if not script.is_file():
        return 0
    try:
        text = script.read_text(encoding="utf-8")
        return text.count('"id":')
    except OSError:
        return 0


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _doctrine()
    recent = recent_threats(limit=16)
    lie_threat_count = sum(1 for r in recent if r.get("threat_recorded") or r.get("event") == "lie_threat")
    vectors = list((doctrine.get("threat_vectors") or {}).keys())
    doc = {
        "schema": "hostess7-truth-lie-threat-panel/v1",
        "updated": _utc(),
        "motto": doctrine.get("motto"),
        "lies_are_threats": True,
        "truth_bands": doctrine.get("truth_bands"),
        "lie_threat_bands": doctrine.get("lie_threat_bands"),
        "threat_vectors": vectors,
        "floors": _floors(),
        "lie_methods_catalogued": lie_methods_count(),
        "recent_witness_count": len(recent),
        "recent_lie_threat_count": lie_threat_count,
        "recent": recent[-8:],
        "sources": doctrine.get("sources"),
        "api": doctrine.get("api"),
        "doctrine": str(DOCTRINE),
    }
    if write:
        _save(PANEL, doc)
    return doc


def _run_aml_assert(spec: str, *, timeout: int = 90) -> dict[str, Any]:
    """Inline AML assert — no bash suite subprocess."""
    import importlib.util

    test_py = INSTALL / "lib" / "field-ammolang-test.py"
    spec_mod = importlib.util.spec_from_file_location("aml_test_restart", test_py)
    if not spec_mod or not spec_mod.loader:
        return {"ok": False, "error": "test_engine_missing", "spec": spec}
    mod = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(mod)
    os.environ.setdefault("HOSTESS7_TRUTH_LIE_SKIP_NEXUS", "1")
    t0 = time.perf_counter()
    row = mod.run_assert(spec, timeout=timeout, name=spec[:48])
    return {
        "ok": bool(row.get("ok")),
        "spec": spec,
        "detail": row.get("detail"),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        "via": "aml_assert",
    }


def restart_monitored(*, run_suites: bool = True) -> dict[str, Any]:
    """AML-monitored restart — panel, pulse, suites, change-awareness witness."""
    panel = build_panel(write=True)
    pulse_out = pulse(record_sample=False)
    suites: list[dict[str, Any]] = []
    if run_suites:
        for spec in (
            "py:hostess7-truth-lie-threat.py panel match:lies_are_threats",
            "py:hostess7-truth-lie-threat.py threats match:lies_are_threats",
            "py:hostess7-aml-ingress.py panel match:presume_separate",
            "py:hostess7-aml-ingress.py read match:truth_and_lie",
        ):
            suites.append(_run_aml_assert(spec))
    all_ok = all(s.get("ok") for s in suites) if suites else True
    ca_out: dict[str, Any] = {}
    ca = INSTALL / "lib" / "hostess7-change-awareness.py"
    if ca.is_file():
        try:
            spec = importlib.util.spec_from_file_location("h7_ca_tlt_restart", ca)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "pulse"):
                    raw = mod.pulse(notify=False)
                    ca_out = {k: v for k, v in raw.items() if k != "notify"}
        except Exception:
            pass
    out = {
        "ok": all_ok,
        "schema": "hostess7-truth-lie-restart/v1",
        "monitored": True,
        "aml_route": "hostess7_truth_lie_threat",
        "lies_are_threats": True,
        "panel": {
            "recent_lie_threat_count": panel.get("recent_lie_threat_count"),
            "threat_vectors": panel.get("threat_vectors"),
        },
        "pulse": pulse_out,
        "suites": suites,
        "change_awareness": ca_out,
        "utc": _utc(),
    }
    _append(LEDGER, {**out, "event": "restart_monitored"})
    _save(STATE / "hostess7-truth-lie-restart.json", out)
    return out


def pulse(*, record_sample: bool = False) -> dict[str, Any]:
    """Pulse — panel + sample lie-threat witness."""
    panel = build_panel(write=True)
    sample = None
    if record_sample:
        sample = witness_claim(
            "Universal boundary protects NewLatest execution through AML",
            source="pulse_probe",
            record_threat=False,
        )
    return {
        "ok": True,
        "schema": "hostess7-truth-lie-pulse/v1",
        "lies_are_threats": True,
        "panel": {
            "recent_lie_threat_count": panel.get("recent_lie_threat_count"),
            "threat_vectors": panel.get("threat_vectors"),
        },
        "sample_witness": sample,
        "utc": _utc(),
    }


def threats_from_tsv(*, limit: int = 20) -> list[dict[str, str]]:
    lie_vectors = set((_doctrine().get("threat_vectors") or {}).keys())
    out: list[dict[str, str]] = []
    if not THREATS_TSV.is_file():
        return out
    try:
        lines = THREATS_TSV.read_text(encoding="utf-8").splitlines()[1:]
        for line in reversed(lines):
            parts = line.split("\t", 3)
            if len(parts) < 4:
                continue
            ts, vector, severity, detail = parts[0], parts[1], parts[2], parts[3]
            if vector in lie_vectors:
                out.append({"ts": ts, "vector": vector, "severity": severity, "detail": detail})
            if len(out) >= limit:
                break
    except OSError:
        pass
    return out


def explain_methods() -> dict[str, Any]:
    return {
        "ok": True,
        "schema": "hostess7-truth-lie-methods/v1",
        "module": "Hostess7/scripts/field_lie_methods.py",
        "command": "./Hostess7.sh lie-methods",
        "catalogued": lie_methods_count(),
        "eras": ["past", "present", "future"],
        "note": "Educational synthesis — lies escalate as threat vectors when witnessed here.",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("witness", "discern", "analyze"):
        source = "cli"
        parts: list[str] = []
        for arg in sys.argv[2:]:
            if arg.startswith("--source="):
                source = arg.split("=", 1)[1]
            else:
                parts.append(arg)
        claim_text = " ".join(parts).strip()
        if not claim_text:
            print(json.dumps({"error": "usage: witness <claim>"}, ensure_ascii=False))
            return 1
        print(json.dumps(witness_claim(claim_text, source=source), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("pulse", "live"):
        print(json.dumps(pulse(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("restart", "restart_monitored", "monitor"):
        print(json.dumps(restart_monitored(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("threats", "vectors"):
        print(json.dumps({
            "ok": True,
            "lies_are_threats": True,
            "ledger_recent": recent_threats(),
            "tsv_lie_vectors": threats_from_tsv(),
        }, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("methods", "lie-methods"):
        print(json.dumps(explain_methods(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "classify":
        claim = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not claim:
            return 1
        print(json.dumps(classify_lie(claim), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: hostess7-truth-lie-threat.py [panel|witness|pulse|threats|methods|classify]",
        "motto": _doctrine().get("motto"),
        "lies_are_threats": True,
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())