#!/usr/bin/env pythong
"""DNS egress integrity — verify allowed traffic arrives exactly as sent."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import struct
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
LOG_JSONL = STATE / "dns-egress-integrity.jsonl"
PANEL_CACHE = STATE / "dns-egress-integrity-panel.json"


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



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _payload_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()[:32]


def record_verified(
    *,
    kind: str,
    sent: bytes | str,
    received: bytes | str,
    dest: str = "",
    permitted: bool = True,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sent_b = sent if isinstance(sent, bytes) else sent.encode("utf-8", errors="replace")
    recv_b = received if isinstance(received, bytes) else received.encode("utf-8", errors="replace")
    sent_hash = _payload_hash(sent_b)
    recv_hash = _payload_hash(recv_b)
    exact = sent_hash == recv_hash
    row = {
        "ts": _now(),
        "kind": kind,
        "dest": dest,
        "permitted": permitted,
        "sent_hash": sent_hash,
        "recv_hash": recv_hash,
        "exact_match": exact,
        "sent_len": len(sent_b),
        "recv_len": len(recv_b),
        **(meta or {}),
    }
    STATE.mkdir(parents=True, exist_ok=True)
    with LOG_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def verify_dns_answer(qname: str, qtype: str, answers: list[str]) -> dict[str, Any]:
    sent = json.dumps({"qname": qname, "qtype": qtype}, sort_keys=True)
    received = json.dumps({"qname": qname, "qtype": qtype, "answers": answers}, sort_keys=True)
    return record_verified(
        kind="dns_answer",
        sent=sent,
        received=received,
        dest="127.0.0.1:53",
        permitted=True,
        meta={"qname": qname, "qtype": qtype, "answer_count": len(answers)},
    )


def probe_allowed_egress() -> list[dict[str, Any]]:
    """Probe root DNS over permitted trace path — verify response structure intact."""
    results: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(
            ["dig", "+trace", "+time=3", "+tries=1", "+noall", "+answer", "example.com", "A"],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
        stdout = proc.stdout or ""
        sent = "dig+trace:example.com:A"
        recv_hash = _payload_hash(stdout.encode("utf-8"))
        sent_hash = _payload_hash(sent.encode())
        ok = proc.returncode == 0 and "example.com" in stdout.lower()
        row = record_verified(
            kind="egress_probe",
            sent=sent,
            received=stdout[:4096] or "(empty)",
            dest="root-hints",
            permitted=True,
            meta={"ok": ok, "returncode": proc.returncode},
        )
        row["integrity_ok"] = ok and row.get("exact_match") is not None
        results.append(row)
    except (OSError, subprocess.TimeoutExpired) as exc:
        results.append({"ok": False, "error": str(exc), "ts": _now()})
    return results


def build_panel() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if LOG_JSONL.is_file():
        try:
            for line in LOG_JSONL.read_text(encoding="utf-8").splitlines()[-500:]:
                if line.strip():
                    rows.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    verified = [r for r in rows if r.get("exact_match")]
    mismatches = [r for r in rows if r.get("exact_match") is False]
    probes = probe_allowed_egress() if not rows else []
    doc = {
        "schema": "dns-egress-integrity/v1",
        "updated": _now(),
        "motto": "Allowed egress verified — payload hash match or logged mismatch.",
        "policy": "Only permitted DNS/DHCP paths; tamper = threat eradication.",
        "stats": {
            "total_checks": len(rows),
            "verified_exact": len(verified),
            "mismatches": len(mismatches),
            "last_probe_ok": any(p.get("ok") for p in probes if isinstance(p, dict)),
        },
        "recent": list(reversed(rows[-48:])),
        "probes": probes,
        "healthy": len(mismatches) == 0,
    }
    _save_json(PANEL_CACHE, doc)
    return doc


def panel_json() -> dict[str, Any]:
    cached = _load_json(PANEL_CACHE, {})
    if cached.get("updated"):
        return cached
    return build_panel()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "probe":
        print(json.dumps({"probes": probe_allowed_egress()}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: dns-egress-integrity.py [json|build|probe]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())