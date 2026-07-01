#!/usr/bin/env pythong
"""Hostess 7 AML ingress — secured external AML data, truth + lie gates."""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
import os
import re
import secrets
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7"))
DOCTRINE = INSTALL / "data" / "hostess7-aml-ingress-doctrine.json"
PANEL = STATE / "hostess7-aml-ingress-panel.json"
LEDGER = STATE / "hostess7-aml-ingress.jsonl"
TOKEN_PATH = STATE / "hostess7-aml-ingress-token.json"

_INJECTION_RE = re.compile(
    r"(<script|javascript:|eval\s*\(|onerror\s*=|union\s+select|;\s*drop\s+)",
    re.I,
)
_PARTY_RE = re.compile(r"^[a-z0-9_-]{1,64}$")


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


def ingress_token() -> str:
    ext = _doctrine().get("external_ingress") or {}
    env_key = str(ext.get("token_env") or "HOSTESS7_AML_INGRESS_TOKEN")
    env = os.environ.get(env_key, "").strip()
    if env:
        return env
    doc = _load(TOKEN_PATH, {})
    if doc.get("token"):
        return str(doc["token"])
    token = secrets.token_hex(32)
    _save(TOKEN_PATH, {
        "schema": "hostess7-aml-ingress-token/v1",
        "created": _utc(),
        "token": token,
        "note": "External AML ingress HMAC — share only with trusted peers outside Hostess7",
    })
    return token


def _canonical_auth(party: str, ts: str, payload: str) -> str:
    return f"{party}|{ts}|{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def _operator_bypass() -> bool:
    ext = _doctrine().get("external_ingress") or {}
    key = str(ext.get("operator_bypass_env") or "HOSTESS7_OPERATOR")
    return os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "operator")


def _analyze_truth(claim: str, *, channels: int = 0) -> dict[str, Any]:
    if not claim.strip():
        return {
            "truth_score": 0.0,
            "deception_risk": "high",
            "verdict": "empty",
            "inconsistency_flags": ["empty_claim"],
        }
    scripts = HOSTESS / "scripts"
    if scripts.is_dir():
        sys.path.insert(0, str(scripts))
        try:
            from field_detective_corpus import analyze_truth  # noqa: WPS433

            return analyze_truth(claim, corroboration_channels=channels)
        except Exception:
            pass
    return {
        "truth_score": 6.0,
        "deception_risk": "high",
        "verdict": "Truth 6.0% — corroboration required",
        "inconsistency_flags": [],
    }


def discern_lie(claim: str, *, truth_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    """Lie / deception discern — extensive truth-lie-threat (lies are threats)."""
    tlt = INSTALL / "lib" / "hostess7-truth-lie-threat.py"
    if tlt.is_file():
        try:
            spec = importlib.util.spec_from_file_location("h7_tlt_ingress", tlt)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "classify_lie"):
                    lie = mod.classify_lie(claim, truth_doc=truth_doc)
                    floor = float((_doctrine().get("external_ingress") or {}).get("truth_floor") or 58)
                    klass = str(lie.get("class") or "")
                    protector = {
                        "truth": "PROTECT",
                        "partial_truth": "PROTECT",
                        "deception": "INVESTIGATE",
                        "lie": "QUARANTINE",
                        "quarantine": "QUARANTINE",
                    }.get(klass, "QUARANTINE")
                    passes = bool(lie.get("passes_adapt_floor")) and klass in ("truth", "partial_truth")
                    return {
                        "schema": "hostess7-aml-ingress-discern/v1",
                        "class": klass,
                        "truth_score": lie.get("truth_score"),
                        "deception_flags": lie.get("deception_flags"),
                        "deception_risk": lie.get("deception_risk"),
                        "passes_guardian": passes,
                        "protector_verdict": protector,
                        "truth_floor": floor,
                        "lies_are_threats": True,
                        "lie_is_threat": lie.get("lie_is_threat"),
                        "threat_vector": lie.get("threat_vector"),
                        "threat_severity": lie.get("threat_severity"),
                        "truth_band": lie.get("truth_band"),
                        "lie_score": lie.get("lie_score"),
                    }
        except Exception:
            pass
    truth_doc = truth_doc or _analyze_truth(claim)
    score = float(truth_doc.get("truth_score") or 0)
    flags = list(truth_doc.get("inconsistency_flags") or [])
    floor = float((_doctrine().get("external_ingress") or {}).get("truth_floor") or 58)
    klass = "lie" if score < 40 else "deception" if score < floor else "truth"
    return {
        "schema": "hostess7-aml-ingress-discern/v1",
        "class": klass,
        "truth_score": score,
        "deception_flags": flags,
        "passes_guardian": score >= floor,
        "protector_verdict": "QUARANTINE" if klass == "lie" else "PROTECT",
        "truth_floor": floor,
        "lies_are_threats": True,
    }


def _structure_filter(payload: str, body: dict[str, Any]) -> dict[str, Any]:
    ext = _doctrine().get("external_ingress") or {}
    max_bytes = int(ext.get("max_payload_bytes") or 8192)
    issues: list[str] = []
    if _INJECTION_RE.search(payload):
        issues.append("injection_pattern")
    if len(payload.encode("utf-8")) > max_bytes:
        issues.append("oversize")
    party = str(body.get("party") or "")
    if party and not _PARTY_RE.match(party.replace("hostess7", "h7")):
        issues.append("bad_party_id")
    return {"id": "structure", "pass": not issues, "issues": issues}


def _echo_corroboration(payload: str, *, limit: int = 12) -> dict[str, Any]:
    if not LEDGER.is_file() or not payload.strip():
        return {"id": "echo", "pass": True, "corroboration": 0, "contradiction": False}
    recent: list[str] = []
    try:
        for line in LEDGER.read_text(encoding="utf-8").splitlines()[-limit:]:
            if line.strip():
                row = json.loads(line)
                recent.append(str(row.get("payload") or ""))
    except (OSError, json.JSONDecodeError):
        return {"id": "echo", "pass": True, "corroboration": 0}
    norm = payload.strip().lower()
    corroboration = sum(1 for r in recent if norm and norm in r.lower())
    contradiction = any(
        ("not " + norm[:40] in r.lower() or "false: " + norm[:30] in r.lower())
        for r in recent if norm
    )
    return {
        "id": "echo",
        "pass": not contradiction,
        "corroboration": corroboration,
        "contradiction": contradiction,
    }


def verify_ingress_auth(body: dict[str, Any], *, payload: str) -> dict[str, Any]:
    if _operator_bypass():
        return {"ok": True, "auth": "operator", "bypass": True}
    party = str(body.get("party") or "external").strip()[:64]
    ts = str(body.get("ts") or _utc())
    sig = str(body.get("sig") or body.get("signature") or "").strip()
    if not sig:
        return {"ok": False, "auth": "missing", "reason": "ingress_token_required"}
    expected = hmac.new(
        ingress_token().encode(),
        _canonical_auth(party, ts, payload).encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return {"ok": False, "auth": "invalid", "reason": "ingress_token_mismatch"}
    return {"ok": True, "auth": "peer_hmac", "party": party}


def _read_source(spec: dict[str, Any]) -> dict[str, Any]:
    rel = str(spec.get("path") or "")
    if rel.startswith(".nexus-state/"):
        path = STATE / rel[len(".nexus-state/") :]
    else:
        path = INSTALL / rel
    sid = str(spec.get("id") or path.name)
    if not path.is_file():
        return {"id": sid, "present": False, "path": rel}
    try:
        if path.suffix == ".jsonl" or spec.get("tail"):
            lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
            tail = int(spec.get("tail") or 16)
            rows = [json.loads(ln) for ln in lines[-tail:]]
            return {"id": sid, "present": True, "path": rel, "kind": "ledger_tail", "rows": rows, "count": len(rows)}
        if spec.get("summary") and path.suffix == ".json":
            doc = _load(path, {})
            entries = list((doc.get("entries") or []))[:48]
            return {
                "id": sid,
                "present": True,
                "path": rel,
                "kind": "registry_summary",
                "schema": doc.get("schema"),
                "entry_count": doc.get("entry_count", len(entries)),
                "routes": [e.get("id") for e in entries if e.get("kind") == "route"][:24],
                "sample_entries": entries[:12],
            }
        text = path.read_text(encoding="utf-8")
        if len(text) > 120_000:
            text = text[:120_000]
        if path.suffix == ".json":
            return {"id": sid, "present": True, "path": rel, "kind": "json", "doc": json.loads(text)}
        return {"id": sid, "present": True, "path": rel, "kind": "text", "text": text[:8000]}
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {"id": sid, "present": True, "path": rel, "error": str(exc)[:120]}


def gather_local_aml() -> dict[str, Any]:
    """Canonical AML data from install — read-only, no execution."""
    doctrine = _doctrine()
    sources = list(doctrine.get("local_sources") or [])
    rows: list[dict[str, Any]] = []
    for spec in sources:
        rows.append(_read_source(spec))
    present = sum(1 for r in rows if r.get("present"))
    boundary = _mod_boundary()
    live: dict[str, Any] = {}
    if boundary and hasattr(boundary, "build_panel"):
        try:
            live["boundary_panel"] = boundary.build_panel(write=False)
        except Exception:
            pass
    if boundary and hasattr(boundary, "scan_registry"):
        try:
            live["registry_scan"] = {
                "entry_count": boundary.scan_registry(refresh=False).get("entry_count"),
                "shell_count": boundary.scan_registry(refresh=False).get("shell_count"),
            }
        except Exception:
            pass
    return {
        "ok": True,
        "schema": "hostess7-aml-local/v1",
        "updated": _utc(),
        "sources_total": len(rows),
        "sources_present": present,
        "sources": rows,
        "live_boundary": live,
        "presume_separate": True,
    }


def _mod_boundary() -> Any | None:
    path = INSTALL / "lib" / "field-ammolang-boundary.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("aml_boundary_ingress", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def ingress_external(
    body: dict[str, Any],
    *,
    write: bool = True,
) -> dict[str, Any]:
    """Accept AML claim/data from outside Hostess7 — secured, truthed, lied."""
    payload = str(
        body.get("claim")
        or body.get("payload")
        or body.get("text")
        or body.get("message")
        or ""
    )
    if isinstance(body.get("payload"), dict):
        payload = json.dumps(body["payload"], ensure_ascii=False)
    if not payload.strip():
        return {"ok": False, "error": "empty_payload", "schema": "hostess7-aml-ingress/v1"}

    auth = verify_ingress_auth(body, payload=payload)
    structure = _structure_filter(payload, body)
    echo = _echo_corroboration(payload)
    truth = _analyze_truth(payload, channels=int(echo.get("corroboration") or 0))
    lie = discern_lie(payload, truth_doc=truth)
    if lie.get("lie_is_threat") and lie.get("threat_vector"):
        tlt = INSTALL / "lib" / "hostess7-truth-lie-threat.py"
        if tlt.is_file():
            try:
                spec = importlib.util.spec_from_file_location("h7_tlt_ing", tlt)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "record_lie_threat"):
                        mod.record_lie_threat(
                            vector=str(lie["threat_vector"]),
                            severity=str(lie.get("threat_severity") or "high"),
                            detail=f"aml_ingress party={body.get('party')} class={lie.get('class')} {payload[:180]}",
                            meta={"source": "aml_ingress", "party": body.get("party")},
                        )
            except Exception:
                pass

    floor = float((_doctrine().get("external_ingress") or {}).get("truth_floor") or 58)
    truth_pass = float(truth.get("truth_score") or 0) >= floor and lie.get("class") not in ("lie", "quarantine")
    security_pass = bool(auth.get("ok")) and structure.get("pass") and echo.get("pass")
    admitted = security_pass and truth_pass and bool(lie.get("passes_guardian"))

    row = {
        "schema": "hostess7-aml-ingress/v1",
        "event": "ingress",
        "utc": _utc(),
        "party": body.get("party") or auth.get("party") or "external",
        "source": str(body.get("source") or "outside_hostess7")[:64],
        "payload_preview": payload[:400],
        "payload_len": len(payload),
        "auth": auth,
        "structure": structure,
        "echo": echo,
        "truth": {
            "truth_score": truth.get("truth_score"),
            "deception_risk": truth.get("deception_risk"),
            "verdict": truth.get("verdict"),
            "inconsistency_flags": truth.get("inconsistency_flags"),
        },
        "lie": lie,
        "security_pass": security_pass,
        "truth_pass": truth_pass,
        "admitted": admitted,
        "hostess7_readable": admitted,
        "protector_verdict": lie.get("protector_verdict"),
    }
    if write:
        _append(LEDGER, row)
    return {"ok": admitted, "schema": "hostess7-aml-ingress/v1", **row}


def read_for_hostess7(*, include_rejected: bool = False) -> dict[str, Any]:
    """What Hostess 7 may read — local AML + vetted external ingress."""
    local = gather_local_aml()
    external: list[dict[str, Any]] = []
    if LEDGER.is_file():
        try:
            for line in LEDGER.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("event") != "ingress":
                    continue
                if row.get("admitted") or include_rejected:
                    external.append(row)
        except (OSError, json.JSONDecodeError):
            pass
    external = external[-24:]
    admitted = [r for r in external if r.get("admitted")]
    return {
        "ok": True,
        "schema": "hostess7-aml-read/v1",
        "updated": _utc(),
        "motto": _doctrine().get("motto"),
        "presume_separate": True,
        "gates": _doctrine().get("gates"),
        "local_aml": local,
        "external_admitted": admitted,
        "external_admitted_count": len(admitted),
        "external_recent_count": len(external),
        "truth_and_lie": {
            "truth_witness": True,
            "lie_discern": True,
            "rule": "External AML must pass security + truth floor + lie guardian before Hostess 7 trusts it.",
        },
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    read_doc = read_for_hostess7(include_rejected=False)
    local = read_doc.get("local_aml") or {}
    doc = {
        "schema": "hostess7-aml-ingress-panel/v1",
        "updated": _utc(),
        "motto": _doctrine().get("motto"),
        "api": _doctrine().get("api"),
        "presume_separate": True,
        "gates": _doctrine().get("gates"),
        "local_sources_present": local.get("sources_present"),
        "local_sources_total": local.get("sources_total"),
        "external_admitted_count": read_doc.get("external_admitted_count"),
        "external_recent_count": read_doc.get("external_recent_count"),
        "last_admitted": (read_doc.get("external_admitted") or [])[-1:] or [],
        "token_path": str(TOKEN_PATH),
        "operator_bypass": _operator_bypass(),
        "doctrine": str(DOCTRINE),
    }
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("read", "hostess7", "consume"):
        print(json.dumps(read_for_hostess7(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "local":
        print(json.dumps(gather_local_aml(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "token":
        print(json.dumps({
            "schema": "hostess7-aml-ingress-token-hint/v1",
            "token_path": str(TOKEN_PATH),
            "env": (_doctrine().get("external_ingress") or {}).get("token_env"),
            "note": "Token written on first use — never log full token in panel",
        }, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("ingress", "submit"):
        body: dict[str, Any] = {}
        if len(sys.argv) > 2 and sys.argv[2].startswith("{"):
            try:
                body = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                body = {"claim": sys.argv[2]}
        elif len(sys.argv) > 2:
            body = {"claim": " ".join(sys.argv[2:])}
        else:
            try:
                body = json.loads(sys.stdin.read() or "{}")
            except json.JSONDecodeError:
                body = {}
        print(json.dumps(ingress_external(body), ensure_ascii=False, indent=2))
        return 0
    if cmd == "discern":
        claim = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not claim:
            print(json.dumps({"error": "usage: discern <claim>"}, ensure_ascii=False))
            return 1
        truth = _analyze_truth(claim)
        lie = discern_lie(claim, truth_doc=truth)
        print(json.dumps({"truth": truth, "lie": lie}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: hostess7-aml-ingress.py [panel|read|local|ingress|discern|token]",
        "motto": _doctrine().get("motto"),
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())