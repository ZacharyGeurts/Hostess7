#!/usr/bin/env pythong
"""NEXUS Kill Detect — zero-overhead harm scan + execution queue.

Runs only when connection-intent signature changes. Good flows never touch
this path (zero cost). Harm candidates get block / pest eradicate / strike.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
INTENT = STATE / "connection-intent.json"
SIG_FILE = STATE / "kill-detect.sig"
STATE_JSON = STATE / "kill-detect-state.json"
LOG_JSONL = STATE / "kill-detect-log.jsonl"

_fg = None
_kr = None


def _kill_reason_plain() -> Any:
    global _kr
    if _kr is not None:
        return _kr
    import importlib.util

    spec = importlib.util.spec_from_file_location("kill_reason_plain", INSTALL / "lib" / "kill-reason-plain.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    _kr = mod
    return mod


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


def _friendly_guard():
    global _fg
    if _fg is not None:
        return _fg
    import importlib.util

    spec = importlib.util.spec_from_file_location("friendly_guard", INSTALL / "lib" / "friendly-guard.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    _fg = mod
    return mod


def _intent_signature(doc: dict[str, Any]) -> str:
    rows = doc.get("connections") or []
    parts: list[str] = []
    for r in rows:
        if not r.get("kill_eligible"):
            continue
        parts.append(
            "|".join(
                [
                    str(r.get("remote_ip") or ""),
                    str(r.get("remote_port") or ""),
                    str(r.get("process") or ""),
                    str(r.get("verdict") or ""),
                    str(r.get("kill_reason") or ""),
                    str(r.get("pid") or ""),
                ]
            )
        )
    harm = int(doc.get("harm_candidates") or 0)
    blob = f"harm={harm};" + ";".join(sorted(parts))
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def scan(doc: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = doc if doc is not None else _load_json(INTENT, {})
    targets: list[dict[str, Any]] = []
    for row in doc.get("connections") or []:
        if not row.get("kill_eligible"):
            continue
        entry = {
            "ip": row.get("remote_ip"),
            "port": row.get("remote_port"),
            "process": row.get("process"),
            "pid": row.get("pid"),
            "verdict": row.get("verdict"),
            "kill_reason": row.get("kill_reason"),
            "kill_tier": row.get("kill_tier") or "block",
            "hell_chosen": row.get("hell_chosen"),
            "soul_side": row.get("soul_side"),
            "harm_total": row.get("harm_total"),
            "scores": row.get("scores"),
        }
        try:
            entry.update(
                _kill_reason_plain().explain_threat_trigger(
                    ip=str(row.get("remote_ip") or ""),
                    conn=row,
                    vector="KILL_DETECT",
                )
            )
        except Exception:
            pass
        targets.append(entry)
    return {
        "updated": _now(),
        "signature": _intent_signature(doc),
        "harm_candidates": int(doc.get("harm_candidates") or 0),
        "kill_targets": targets,
        "kill_count": len(targets),
        "zero_cost_skip": len(targets) == 0,
    }


def execute(doc: dict[str, Any] | None = None, dry_run: bool = False) -> dict[str, Any]:
    doc = doc if doc is not None else _load_json(INTENT, {})
    sig = _intent_signature(doc)
    prev = SIG_FILE.read_text(encoding="utf-8").strip() if SIG_FILE.is_file() else ""
    if sig == prev and sig:
        return {
            "ok": True,
            "skipped": True,
            "reason": "signature_unchanged",
            "signature": sig,
            "zero_cost": True,
        }

    report = scan(doc)
    if report["kill_count"] == 0:
        SIG_FILE.write_text(sig + "\n", encoding="utf-8")
        return {"ok": True, "skipped": True, "reason": "no_kill_targets", "zero_cost": True}

    fg = _friendly_guard()
    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for t in report["kill_targets"]:
        ip = str(t.get("ip") or "").strip()
        if not ip:
            continue
        refuse, reason = fg.refuse_kill(
            ip,
            {
                "verdict": t.get("verdict") or "HARM_CANDIDATE",
                "process": t.get("process") or "",
                "trust_rank": 4,
            },
        )
        if refuse:
            skipped.append({"ip": ip, "reason": reason, "heaven_protected": True})
            continue
        tier = t.get("kill_tier") or "block"
        if t.get("hell_chosen") and tier in ("block", "strike"):
            tier = "lethal" if t.get("soul_side") == "hell" else "strike"
        entry: dict[str, Any] = {"ip": ip, "tier": tier, "kill_reason": t.get("kill_reason"), "ok": False}
        if dry_run:
            entry["ok"] = True
            entry["dry_run"] = True
            executed.append(entry)
            continue
        lethal_py = INSTALL / "lib" / "lethal-enforcement.py"
        if lethal_py.is_file() and tier in ("lethal", "strike") and t.get("hell_chosen"):
            subprocess.run(
                [
                    "pythong", str(lethal_py), "execute",
                    json.dumps({**t, "ip": ip, "remote_ip": ip}),
                ],
                env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                timeout=45,
                check=False,
            )
            entry["lethal_enforcement"] = True
            entry["ok"] = True
            executed.append(entry)
            continue
        if tier in ("eradicate", "strike", "lethal"):
            pid = str(t.get("pid") or "0")
            script = INSTALL / "lib" / "pest-arsenal.sh"
            if script.is_file() and pid.isdigit() and int(pid) > 0:
                subprocess.run(
                    ["bash", "-c", f"source '{script}'; nexus_pest_eradicate '{ip}' '{pid}' 'KILL_DETECT' ''"],
                    env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                    timeout=12,
                    check=False,
                )
                entry["pest"] = True
        block_script = INSTALL / "lib" / "firewall-sentinel.sh"
        if block_script.is_file():
            subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        f"source '{INSTALL}/lib/nexus-common.sh'; "
                        f"source '{block_script}'; "
                        f"nexus_firewall_block_ip_forever out '{ip}' 'kill_detect:{t.get('kill_reason', '')}' || true; "
                        f"nexus_firewall_block_ip_forever in '{ip}' 'kill_detect:{t.get('kill_reason', '')}' || true"
                    ),
                ],
                env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                timeout=12,
                check=False,
            )
            entry["block"] = True
        if tier == "strike":
            kit = INSTALL / "lib" / "field-attack-kit.py"
            if kit.is_file():
                subprocess.run(
                    [
                        "pythong",
                        str(kit),
                        "kill",
                        ip,
                        "KILL_DETECT",
                        "high",
                        str(t.get("kill_reason") or "gatekeeper_harm"),
                    ],
                    env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                    timeout=20,
                    check=False,
                )
                entry["strike"] = True
        entry["ok"] = True
        why = _kill_reason_plain().explain_kill(
            ip=ip,
            reason=f"kill_detect:{t.get('kill_reason') or 'gatekeeper_harm'}",
            action="KILL",
            conn=t,
            vector="KILL_DETECT",
            process=str(t.get("process") or ""),
            source="kill-detect",
        )
        entry.update(why)
        executed.append(entry)
        try:
            with LOG_JSONL.open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {
                            "ts": _now(),
                            "ip": ip,
                            "tier": tier,
                            "reason": t.get("kill_reason"),
                            "pid": t.get("pid"),
                            **why,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except OSError:
            pass

    SIG_FILE.write_text(sig + "\n", encoding="utf-8")
    out = {
        "ok": True,
        "skipped": False,
        "signature": sig,
        "executed": executed,
        "executed_count": len(executed),
        "skipped_targets": skipped,
        "zero_cost": False,
    }
    STATE_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: kill-detect.py [scan|execute|sig]", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "scan":
        json.dump(scan(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    if cmd == "sig":
        doc = _load_json(INTENT, {})
        print(_intent_signature(doc))
        return 0
    if cmd == "execute":
        json.dump(execute(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    print("usage: kill-detect.py [scan|execute|sig]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())