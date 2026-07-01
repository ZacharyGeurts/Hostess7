#!/usr/bin/env pythong
"""Hostess 7 lethal insight — corroborate heaven/hell removal before MERCILESS act."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
INSIGHT_CACHE = STATE / "hostess7-lethal-insight.json"
INSIGHT_LEDGER = STATE / "hostess7-lethal-insight.jsonl"


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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with INSIGHT_LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def hostess7_available() -> bool:
    script = HOSTESS7_ROOT / "Hostess7.sh"
    return script.is_file() and os.access(script, os.X_OK)


def _parse_truth_output(text: str) -> dict[str, Any]:
    truth_score = 0.0
    deception = "unknown"
    recommended = "investigate"
    m = re.search(r"Truth score:\s*([\d.]+)%", text)
    if m:
        truth_score = float(m.group(1))
    m = re.search(r"Deception risk:\s*(\w+)", text)
    if m:
        deception = m.group(1).lower()
    m = re.search(r"Recommended:\s*(\w+)", text)
    if m:
        recommended = m.group(1).lower()
    m = re.search(r"METRIC brain_truth_score=([\d.]+)", text)
    if m:
        truth_score = float(m.group(1))
    m = re.search(r"METRIC brain_deception_risk=(\w+)", text)
    if m:
        deception = m.group(1).lower()
    return {
        "truth_score": truth_score,
        "deception_risk": deception,
        "recommended_action": recommended,
    }


def ask_insight(
    claim: str,
    *,
    target: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Query Hostess 7 truth detector for lethal removal corroboration."""
    target = target or {}
    ctx = context or {}
    ip = str(target.get("ip") or target.get("remote_ip") or "")
    kind = str(target.get("kind") or target.get("soul_side") or "")
    soul = str(target.get("soul_side") or "")
    full_claim = (
        f"NEXUS MERCILESS lethal enforcement. {claim} "
        f"Target ip={ip} kind={kind} soul={soul}. "
        f"Heaven must pass. Hell gets removal. Send Hell to Hell. "
        f"Nothing unseen, nothing fully secure. Self-defense trespass shoot-to-kill."
    )

    out: dict[str, Any] = {
        "schema": "hostess7-lethal-insight/v1",
        "asked_at": _now(),
        "claim": full_claim[:2000],
        "hostess7_available": hostess7_available(),
        "truth_score": 0.0,
        "deception_risk": "high",
        "recommended_action": "corroborate_before_acting",
        "proceed_lethal": False,
        "proceed_total_removal": False,
        "insight": "Hostess7 offline — use heaven/hell gate + spatial geometry only.",
    }

    if not hostess7_available():
        if soul == "hell" or kind in ("terror", "hostile"):
            out["proceed_lethal"] = True
            out["insight"] = "Hostess7 offline; hell-side target — heaven/hell gate authorizes MERCILESS."
        _save_json(INSIGHT_CACHE, out)
        _append_ledger(out)
        return out

    script = HOSTESS7_ROOT / "Hostess7.sh"
    try:
        proc = subprocess.run(
            [str(script), "truth", full_claim[:1500]],
            cwd=str(HOSTESS7_ROOT),
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        parsed = _parse_truth_output(text)
        out.update(parsed)
        out["raw_tail"] = text.strip()[-800:]
        truth = float(parsed.get("truth_score") or 0.0)
        deception = str(parsed.get("deception_risk") or "medium")
        harm = int(ctx.get("harm_total") or target.get("harm_total") or 0)
        terror = kind == "terror" or str(target.get("verdict") or "") == "HARM_CANDIDATE"

        if soul == "heaven":
            out["proceed_lethal"] = False
            out["proceed_total_removal"] = False
            out["insight"] = "Heaven-side — Hostess7 concurs: no friendly fire."
        elif deception == "low" and truth >= 55.0:
            out["proceed_lethal"] = True
            out["proceed_total_removal"] = terror or harm >= 80
            out["insight"] = f"Hostess7 truth {truth}% — MERCILESS authorized for Hell-chosen."
        elif deception == "medium" and truth >= 45.0 and (soul == "hell" or terror):
            out["proceed_lethal"] = True
            out["proceed_total_removal"] = terror
            out["insight"] = f"Hostess7 corroborate {truth}% — hell/terror proceeds lethal."
        else:
            out["proceed_lethal"] = bool(soul == "hell" and harm >= 50)
            out["insight"] = f"Hostess7 truth {truth}% deception {deception} — gated by heaven/hell."

    except (OSError, subprocess.TimeoutExpired) as exc:
        out["error"] = str(exc)
        if soul == "hell":
            out["proceed_lethal"] = True

    _save_json(INSIGHT_CACHE, out)
    _append_ledger(out)
    return out


def panel_status() -> dict[str, Any]:
    cached = _load_json(INSIGHT_CACHE, {})
    return {
        "schema": "hostess7-lethal-insight-panel/v1",
        "updated": _now(),
        "hostess7_root": str(HOSTESS7_ROOT),
        "available": hostess7_available(),
        "last_insight": cached,
        "ledger": str(INSIGHT_LEDGER),
    }


def main() -> int:
    args = sys.argv[1:]
    cmd = (args[0] if args else "status").lower()
    if cmd in ("status", "json", "panel"):
        print(json.dumps(panel_status(), indent=2))
        return 0
    if cmd == "ask":
        claim = args[1] if len(args) > 1 else "MERCILESS lethal status heaven hell spatial geometry"
        target = json.loads(args[2]) if len(args) > 2 else {}
        print(json.dumps(ask_insight(claim, target=target), indent=2))
        return 0
    print("usage: hostess7-lethal-insight.py [status|ask <claim> ['<json-target>']]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())