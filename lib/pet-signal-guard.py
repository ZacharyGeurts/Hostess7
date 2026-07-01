#!/usr/bin/env pythong
"""Pet signal guard — hostile audio on pet/collar sources → trace and strike origin."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PANEL_JSON = STATE / "threat-panel.json"
LEDGER = STATE / "pet-signal-guard.jsonl"

PET_KINDS = frozenset({"pet", "animal", "collar"})
PET_LABEL_RE = re.compile(
    r"tractive|whistle|fi\.pet|petcube|pawtrack|collar|pet\s?tracker",
    re.I,
)


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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _attack_kit() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("field_attack_kit", INSTALL / "lib" / "field-attack-kit.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _is_pet_source(kind: str, label: str) -> bool:
    k = (kind or "").lower()
    if k in PET_KINDS:
        return True
    return bool(PET_LABEL_RE.search(label or ""))


def _proc_matches_label(proc: str, label: str) -> bool:
    proc_l = (proc or "").lower()
    label_l = (label or "").lower()
    if not proc_l or not label_l:
        return False
    if proc_l in label_l or label_l in proc_l:
        return True
    proc_tokens = re.split(r"[\s._-]+", proc_l)
    label_tokens = re.split(r"[\s._-]+", label_l)
    return bool(set(proc_tokens) & set(label_tokens))


def _resolve_attacker_ip(label: str, source_id: str) -> tuple[str, str]:
    panel = _load_json(PANEL_JSON, {})
    gk = panel.get("gatekeeper") or {}
    for conn in gk.get("connections") or []:
        proc = str(conn.get("process") or "")
        ip = str(conn.get("remote_ip") or "").strip()
        if not ip or conn.get("verdict") in ("USER_OK", "EPHEMERAL"):
            continue
        if _proc_matches_label(proc, label) or _proc_matches_label(proc, source_id):
            return ip, f"gatekeeper_proc:{proc}"
        if conn.get("lifeform") == "pet" and _is_pet_source("", label):
            return ip, "gatekeeper_pet_lifeform"

    reg_py = INSTALL / "lib" / "human-registry.py"
    if reg_py.is_file():
        import importlib.util

        spec = importlib.util.spec_from_file_location("human_registry", reg_py)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        doc = _load_json(STATE / "human-registry.json", {})
        for human in (doc.get("humans") or {}).values():
            if human.get("lifeform") != "pet":
                continue
            for tie in human.get("internet_ties") or []:
                ip = str(tie.get("ip") or "").strip()
                if ip:
                    return ip, f"human_registry_pet:{human.get('truth_id') or 'pet'}"

    m = re.search(r"(?:pulse|pipewire):(.+)", source_id or "")
    if m and gk.get("connections"):
        hint = m.group(1).lower()
        for conn in gk.get("connections") or []:
            proc = str(conn.get("process") or "").lower()
            ip = str(conn.get("remote_ip") or "").strip()
            if ip and hint in proc:
                return ip, f"gatekeeper_hint:{proc}"
    return "", "unresolved"


def respond_to_pet_attack(
    source_id: str,
    label: str,
    kind: str,
    violations: list[dict[str, Any]],
) -> dict[str, Any]:
    if not _is_pet_source(kind, label):
        return {"ok": True, "skipped": True, "reason": "not_pet_source"}
    ip, trace = _resolve_attacker_ip(label, source_id)
    row: dict[str, Any] = {
        "ts": _now(),
        "event": "pet_signal_attack",
        "source_id": source_id,
        "label": label,
        "kind": kind,
        "violations": violations,
        "trace": trace,
        "target_ip": ip or None,
    }
    if not ip:
        row["strike"] = {"ok": False, "reason": "no_attacker_ip"}
        _append_ledger(row)
        return row

    kit = _attack_kit()
    strike = kit.kill_target(
        ip,
        vector="PET_SIGNAL_ATTACK",
        severity="high",
        reason=f"hostile_audio_on_pet:{source_id}",
        extra={"strike_mode": "pet_signal_guard", "force": False},
    )
    row["strike"] = strike
    _append_ledger(row)
    return row


def panel_json() -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    try:
        if LEDGER.is_file():
            for line in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        pass
    strikes = [e for e in events if e.get("strike", {}).get("killed")]
    return {
        "schema": "pet-signal-guard/v1",
        "motto": "If a dog is attacked by signal, we go to the source and attack it.",
        "events": events[-12:],
        "strike_count": len(strikes),
        "last_strike": strikes[-1] if strikes else None,
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: pet-signal-guard.py [json]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())