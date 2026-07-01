#!/usr/bin/env pythong
"""ZNetwork hostile threat — immediate IFF scan + zero-hesitation countermeasures.

Runs on ZNetwork activate, publish, and watch ticks. HARM_CANDIDATE flows bypass
signature cache for sub-second interdict; civilian flows skip at zero cost.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
INTENT = STATE / "connection-intent.json"
THREATS_TSV = STATE / "threat-vectors.tsv"
HOSTILE_TSV = STATE / "field-hostile.tsv"
LEDGER = STATE / "znetwork-hostile-ledger.jsonl"
STATE_JSON = STATE / "znetwork-hostile-state.json"
SIG_FILE = STATE / "znetwork-hostile.sig"
SCHEMA = "znetwork-hostile-threat/v1"
VECTOR = "ZNETWORK_HOSTILE"
PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.|::1|fe80:|fd)"
)
HOSTILE_VERDICTS = frozenset({"HARM_CANDIDATE", "BLOCK_RECOMMENDED"})
HOSTILE_IFF = frozenset({"HOSTILE"})

_MOD_CACHE: dict[str, Any] = {}
_SOVEREIGN_CLOCK_MOD = None


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        py = Path(__file__).resolve().parent / "sovereign-clock.py"
        spec = importlib.util.spec_from_file_location("sovereign_clock_znet_hostile", py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _SOVEREIGN_CLOCK_MOD = mod
    if _SOVEREIGN_CLOCK_MOD and hasattr(_SOVEREIGN_CLOCK_MOD, "utc_z"):
        return _SOVEREIGN_CLOCK_MOD.utc_z("znetwork-hostile")
    return ""


def _mod(py: Path, name: str) -> Any | None:
    key = str(py)
    if key in _MOD_CACHE:
        return _MOD_CACHE[key]
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _MOD_CACHE[key] = mod
    return mod


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _ss_lines() -> list[str]:
    try:
        proc = subprocess.run(
            ["ss", "-H", "-tunap"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        return proc.stdout.splitlines()
    except (subprocess.SubprocessError, OSError):
        return []


def _threat_vector_ips() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not THREATS_TSV.is_file():
        return out
    try:
        for line in THREATS_TSV.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            ip = parts[1].strip()
            vector = parts[2].strip() if len(parts) > 2 else "THREAT"
            if ip and re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
                out.setdefault(ip, []).append(vector)
    except OSError:
        pass
    return out


def _registry_hostile_ips() -> set[str]:
    ips: set[str] = set()
    if not HOSTILE_TSV.is_file():
        return ips
    try:
        for line in HOSTILE_TSV.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 2 and parts[1]:
                ips.add(parts[1])
    except OSError:
        pass
    return ips


def _append_hostile_tsv(ip: str, vector: str, severity: str, reason: str) -> bool:
    if not ip or PRIVATE_RE.match(ip):
        return False
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        if not HOSTILE_TSV.is_file():
            HOSTILE_TSV.write_text("ts\tip\tvector\tseverity\treason\tsource\n", encoding="utf-8")
        text = HOSTILE_TSV.read_text(encoding="utf-8", errors="replace")
        if f"\t{ip}\t" in text:
            return False
        with HOSTILE_TSV.open("a", encoding="utf-8") as fh:
            fh.write(f"{_now()}\t{ip}\t{vector}\t{severity}\t{reason[:120]}\tznetwork\n")
        return True
    except OSError:
        return False


def _publish_intent(lines: list[str] | None = None) -> dict[str, Any]:
    gk = _mod(INSTALL / "lib" / "connection-gatekeeper.py", "connection_gatekeeper_znet")
    if not gk or not hasattr(gk, "analyze_connections"):
        return {"ok": False, "error": "connection_gatekeeper_missing"}
    snap = lines if lines is not None else _ss_lines()
    doc = gk.analyze_connections(snap)
    try:
        INTENT.parent.mkdir(parents=True, exist_ok=True)
        tmp = INTENT.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(INTENT)
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "connection_count": doc.get("connection_count", 0), "intent": doc}


def _hostile_signature(hostiles: list[dict[str, Any]], *, immediate: bool) -> str:
    parts = [f"immediate={int(immediate)}"]
    for row in sorted(hostiles, key=lambda x: str(x.get("ip") or "")):
        parts.append(
            "|".join(
                [
                    str(row.get("ip") or ""),
                    str(row.get("verdict") or ""),
                    str(row.get("iff") or ""),
                    str(row.get("remote_port") or ""),
                    str(row.get("process") or ""),
                ]
            )
        )
    return hashlib.sha256(";".join(parts).encode()).hexdigest()[:24]


def _grok_civilian_bypass(row: dict[str, Any]) -> bool:
    proc = str(row.get("process") or "").lower()
    if "grok" not in proc:
        return False
    rip = str(row.get("remote_ip") or "").strip()
    if not rip or PRIVATE_RE.match(rip):
        return True
    intel = row.get("intel") if isinstance(row.get("intel"), dict) else {}
    org = str(intel.get("org") or intel.get("asn_name") or "").lower()
    if "cloudflare" in org or "x.ai" in org or "x corp" in org:
        return True
    if rip.startswith(("104.18.", "104.16.", "172.64.", "172.66.", "2606:4700:")):
        return True
    return False


def _classify_row(
    row: dict[str, Any],
    *,
    threat_ips: dict[str, list[str]],
    registry: set[str],
    corpus_ips: set[str],
) -> dict[str, Any] | None:
    if _grok_civilian_bypass(row):
        return None
    rip = str(row.get("remote_ip") or "").strip()
    if not rip or PRIVATE_RE.match(rip):
        return None
    wireless = _mod(INSTALL / "lib" / "znetwork-wireless-fcc.py", "hostile_wireless")
    if wireless and hasattr(wireless, "is_own_router") and wireless.is_own_router(ip=rip):
        if hasattr(wireless, "trace_action_behind"):
            traced = wireless.trace_action_behind({"ip": rip, "kind": "hostile_gateway_symptom", "process": row.get("process")})
            action_ip = str(traced.get("action_ip") or "")
            if traced.get("strike_eligible") and action_ip and not wireless.is_own_router(ip=action_ip):
                rip = action_ip
                row = {**row, "remote_ip": rip, "reason": f"traced_behind_router:{traced.get('action_source')}"}
            else:
                return None
        else:
            return None
    verdict = str(row.get("verdict") or "")
    iff = str(row.get("iff") or "")
    block_rec = bool(row.get("block_recommended"))
    kill_ok = bool(row.get("kill_eligible"))
    threat_linked = int((row.get("scores") or {}).get("threat_linked") or 0) >= 6
    registry_hit = rip in registry
    corpus_hit = rip in corpus_ips
    vector_hit = rip in threat_ips
    immediate = (
        verdict == "HARM_CANDIDATE"
        or iff in HOSTILE_IFF
        or (block_rec and kill_ok)
        or registry_hit
        or (vector_hit and threat_linked)
    )
    hostile = immediate or verdict in HOSTILE_VERDICTS or block_rec
    if not hostile:
        return None
    tier = str(row.get("kill_tier") or "block")
    if row.get("hell_chosen") and tier == "block":
        tier = "strike"
    source = "gatekeeper"
    if registry_hit:
        source = "registry"
    elif corpus_hit:
        source = "corpus"
    elif vector_hit:
        source = "threat_vector"
    return {
        "ip": rip,
        "remote_port": row.get("remote_port"),
        "process": row.get("process"),
        "pid": row.get("pid"),
        "verdict": verdict,
        "iff": iff or "HOSTILE",
        "iff_class": row.get("iff_class") or "CONFIRMED",
        "enforcement": row.get("enforcement") or "INTERDICT — block immediately, zero hesitation",
        "reason": row.get("reason") or row.get("kill_reason") or "znetwork_hostile",
        "kill_eligible": kill_ok,
        "kill_tier": tier,
        "immediate": immediate,
        "block_recommended": block_rec,
        "threat_vectors": threat_ips.get(rip, []),
        "registry_hit": registry_hit,
        "corpus_hit": corpus_hit,
        "source": source,
        "scores": row.get("scores"),
    }


def scan(*, publish: bool = True) -> dict[str, Any]:
    """Immediate hostile IFF scan over live connections + threat memory."""
    t0 = time.perf_counter()
    lines_future = None
    corpus_future = None
    with ThreadPoolExecutor(max_workers=3) as pool:
        if publish:
            lines_future = pool.submit(_ss_lines)
        corpus_mod = _mod(INSTALL / "lib" / "trust-strike-engine.py", "trust_strike_znet")
        if corpus_mod and hasattr(corpus_mod, "build_hostile_corpus"):
            corpus_future = pool.submit(corpus_mod.build_hostile_corpus)
        threat_ips = _threat_vector_ips()
        registry = _registry_hostile_ips()

    lines = lines_future.result() if lines_future else _ss_lines()
    intent_rep = _publish_intent(lines) if publish else {"ok": True, "intent": _load_json(INTENT, {})}
    doc = intent_rep.get("intent") if isinstance(intent_rep.get("intent"), dict) else _load_json(INTENT, {})
    corpus_ips: set[str] = set()
    if corpus_future:
        try:
            corpus_ips = set(corpus_future.result().get("hostile_ips") or [])
        except Exception:
            corpus_ips = set()

    hostiles: list[dict[str, Any]] = []
    civilians = 0
    for row in doc.get("connections") or []:
        if not isinstance(row, dict):
            continue
        classified = _classify_row(
            row,
            threat_ips=threat_ips,
            registry=registry,
            corpus_ips=corpus_ips,
        )
        if classified:
            hostiles.append(classified)
        else:
            civilians += 1

    immediate = [h for h in hostiles if h.get("immediate")]
    sig = _hostile_signature(hostiles, immediate=bool(immediate))
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    rep = {
        "schema": SCHEMA,
        "ok": True,
        "scanned_at": _now(),
        "elapsed_ms": elapsed_ms,
        "connection_count": int(doc.get("connection_count") or len(doc.get("connections") or [])),
        "civilian_count": civilians,
        "hostile_count": len(hostiles),
        "immediate_count": len(immediate),
        "harm_candidates": int(doc.get("harm_candidates") or 0),
        "signature": sig,
        "zero_cost_skip": len(hostiles) == 0,
        "hostiles": hostiles[:48],
        "immediate": immediate[:24],
        "policy": "zero_hesitation_interdict",
    }
    _save_json(STATE_JSON, rep)
    return rep


def _gatekeeper_enforce() -> dict[str, Any]:
    gk_sh = INSTALL / "lib" / "gatekeeper-enforce.sh"
    if not gk_sh.is_file():
        return {"ok": False, "skipped": True, "reason": "gatekeeper_enforce_missing"}
    try:
        proc = subprocess.run(
            [
                "bash",
                "-c",
                f'source "{INSTALL / "lib" / "nexus-common.sh"}" 2>/dev/null; '
                f'source "{gk_sh}" && nexus_gatekeeper_enforce_strict',
            ],
            capture_output=True,
            text=True,
            timeout=20,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        return {"ok": proc.returncode == 0, "detail": (proc.stdout or proc.stderr or "")[:200]}
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _strike_target(target: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    ip = str(target.get("ip") or "").strip()
    entry: dict[str, Any] = {"ip": ip, "ok": False, "actions": []}
    if not ip:
        return entry

    fg = _mod(INSTALL / "lib" / "friendly-guard.py", "friendly_guard_znet")
    if fg and hasattr(fg, "refuse_kill"):
        refuse, reason = fg.refuse_kill(
            ip,
            {
                "verdict": target.get("verdict") or "HARM_CANDIDATE",
                "process": target.get("process") or "",
                "trust_rank": 4,
            },
        )
        if refuse:
            entry["ok"] = False
            entry["friendly_refused"] = True
            entry["reason"] = reason
            return entry

    if dry_run:
        entry["ok"] = True
        entry["dry_run"] = True
        return entry

    reason = str(target.get("reason") or "znetwork_hostile")[:120]
    severity = "critical" if target.get("immediate") else "high"
    if _append_hostile_tsv(ip, VECTOR, severity, reason):
        entry["actions"].append("hostile_tsv")

    enforce = _gatekeeper_enforce()
    if enforce.get("ok"):
        entry["actions"].append("gatekeeper_enforce")

    tier = target.get("kill_tier") or "block"
    block_script = INSTALL / "lib" / "firewall-sentinel.sh"
    if block_script.is_file() and target.get("immediate"):
        try:
            subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        f"source '{INSTALL / 'lib' / 'nexus-common.sh'}'; "
                        f"source '{block_script}'; "
                        f"nexus_firewall_block_ip_forever out '{ip}' 'znetwork:{reason}' || true; "
                        f"nexus_firewall_block_ip_forever in '{ip}' 'znetwork:{reason}' || true"
                    ),
                ],
                env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                timeout=12,
                check=False,
            )
            entry["actions"].append("firewall_block")
        except (subprocess.SubprocessError, OSError):
            pass

    if tier in ("strike", "lethal") or target.get("kill_eligible"):
        kit = _mod(INSTALL / "lib" / "field-attack-kit.py", "attack_kit_znet")
        if kit and hasattr(kit, "kill_target"):
            try:
                strike = kit.kill_target(
                    ip,
                    vector=VECTOR,
                    severity=severity,
                    reason=reason,
                    extra={
                        "source": "znetwork-hostile",
                        "strike_mode": "auto" if target.get("immediate") else "manual",
                        "force": bool(target.get("immediate")),
                        "monitor": {
                            "verdict": target.get("verdict"),
                            "process": target.get("process"),
                            "remote_port": target.get("remote_port"),
                        },
                    },
                )
                entry["strike"] = strike
                if strike.get("killed") or strike.get("ok"):
                    entry["actions"].append("attack_kit")
            except Exception as exc:
                entry["strike_error"] = str(exc)

    entry["ok"] = bool(entry["actions"])
    return entry


def countermeasures(
    report: dict[str, Any] | None = None,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Apply immediate countermeasures for hostile targets."""
    report = report or scan(publish=True)
    hostiles = report.get("immediate") or report.get("hostiles") or []
    if not hostiles:
        sig = report.get("signature") or ""
        if sig:
            SIG_FILE.write_text(sig + "\n", encoding="utf-8")
        return {
            "schema": SCHEMA,
            "ok": True,
            "skipped": True,
            "reason": "no_hostiles",
            "zero_cost": True,
            "signature": sig,
        }

    sig = report.get("signature") or _hostile_signature(hostiles, immediate=True)
    prev = SIG_FILE.read_text(encoding="utf-8").strip() if SIG_FILE.is_file() else ""
    has_immediate = any(h.get("immediate") for h in hostiles)
    if not force and not has_immediate and sig == prev and sig:
        return {
            "schema": SCHEMA,
            "ok": True,
            "skipped": True,
            "reason": "signature_unchanged",
            "zero_cost": True,
            "signature": sig,
        }

    executed: list[dict[str, Any]] = []
    for target in hostiles:
        if not target.get("immediate") and not force:
            continue
        result = _strike_target(target, dry_run=dry_run)
        executed.append(result)
        _append_jsonl(
            LEDGER,
            {
                "ts": _now(),
                "event": "countermeasure",
                "ip": target.get("ip"),
                "immediate": target.get("immediate"),
                "verdict": target.get("verdict"),
                "actions": result.get("actions"),
                "ok": result.get("ok"),
            },
        )

    if not dry_run:
        SIG_FILE.write_text(sig + "\n", encoding="utf-8")

    rep = {
        "schema": SCHEMA,
        "ok": True,
        "skipped": False,
        "signature": sig,
        "executed": executed,
        "executed_count": len(executed),
        "immediate_count": sum(1 for h in hostiles if h.get("immediate")),
        "zero_cost": False,
        "responded_at": _now(),
    }
    _save_json(STATE_JSON, {**report, "last_countermeasure": rep})
    return rep


def watch(*, dry_run: bool = False) -> dict[str, Any]:
    """One watch tick — scan then countermeasure immediate hostiles."""
    report = scan(publish=True)
    response = countermeasures(report, dry_run=dry_run)
    return {
        "schema": SCHEMA,
        "ok": True,
        "scan": report,
        "countermeasure": response,
        "watched_at": _now(),
    }


def posture() -> dict[str, Any]:
    state = _load_json(STATE_JSON, {})
    if state.get("schema") != SCHEMA:
        state = scan(publish=False)
    return {
        "schema": SCHEMA,
        "ok": True,
        "state": state,
        "ledger": str(LEDGER),
        "hostile_tsv": str(HOSTILE_TSV),
        "checked_at": _now(),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "scan").strip().lower()
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    handlers = {
        "scan": lambda: scan(publish=True),
        "json": posture,
        "posture": posture,
        "countermeasure": lambda: countermeasures(dry_run=dry_run, force=force),
        "respond": lambda: countermeasures(dry_run=dry_run, force=force),
        "watch": lambda: watch(dry_run=dry_run),
    }
    fn = handlers.get(cmd)
    if not fn:
        print(
            "usage: znetwork-hostile-threat.py [scan|countermeasure|watch|json] [--dry-run] [--force]",
            file=sys.stderr,
        )
        return 2
    result = fn()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())