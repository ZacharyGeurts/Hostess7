#!/usr/bin/env pythong
"""ZNetwork relayer — sole internet in/out stack. Civilian passes; hostile nuked immediately.

Relayer owns all ingress and egress policy. Spyware, malware, C2, exploits — zero hesitation
retaliation through every defensive method available. Grandma's browser passes untouched.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
POSTURE = STATE / "znetwork-relayer.json"
BASELINE = STATE / "znetwork-link-baseline.json"
LEDGER = STATE / "znetwork-relayer.jsonl"
SCHEMA = "znetwork-relayer/v1"

_MOD_CACHE: dict[str, Any] = {}


def _invisible_replace() -> bool:
    return os.environ.get("ZNETWORK_INVISIBLE_REPLACE", "1") != "0"


def _link_preserve() -> bool:
    return os.environ.get("ZNETWORK_LINK_PRESERVE", "1") != "0"


def _defer_retaliate() -> bool:
    return (
        os.environ.get("ZNETWORK_DEFER_RETALIATE", "1") != "0"
        or _invisible_replace()
        or not os.environ.get("ZNETWORK_RELAYER_ARMED")
    )


def _default_iface() -> str:
    try:
        proc = subprocess.run(
            ["ip", "-4", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=4,
        )
        if proc.returncode == 0 and "dev" in proc.stdout:
            return proc.stdout.split()[proc.stdout.split().index("dev") + 1]
    except (subprocess.SubprocessError, OSError):
        pass
    return ""


def _iface_ipv4(iface: str) -> str:
    if not iface:
        return ""
    try:
        proc = subprocess.run(
            ["ip", "-4", "-o", "addr", "show", "dev", iface],
            capture_output=True,
            text=True,
            timeout=4,
        )
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 4 and parts[2] == "inet":
                    return parts[3].split("/", 1)[0]
    except (subprocess.SubprocessError, OSError):
        pass
    return ""


def _estab_count() -> int:
    try:
        proc = subprocess.run(["ss", "-H", "-t", "state", "established"], capture_output=True, text=True, timeout=4)
        return len([ln for ln in proc.stdout.splitlines() if ln.strip()]) if proc.returncode == 0 else 0
    except (subprocess.SubprocessError, OSError):
        return 0


def link_snapshot() -> dict[str, Any]:
    iface = _default_iface()
    operstate = "unknown"
    if iface:
        try:
            operstate = Path(f"/sys/class/net/{iface}/operstate").read_text(encoding="utf-8").strip().lower()
        except OSError:
            pass
    gateway = ""
    try:
        proc = subprocess.run(["ip", "-4", "route", "show", "default"], capture_output=True, text=True, timeout=4)
        if proc.returncode == 0 and "via" in proc.stdout:
            gateway = proc.stdout.split()[proc.stdout.split().index("via") + 1]
    except (subprocess.SubprocessError, OSError):
        pass
    return {
        "iface": iface,
        "ipv4": _iface_ipv4(iface),
        "gateway": gateway,
        "operstate": operstate,
        "estab_tcp": _estab_count(),
        "captured_at": _now(),
    }


def link_healthy(baseline: dict[str, Any] | None = None) -> tuple[bool, dict[str, Any]]:
    snap = link_snapshot()
    ok = bool(snap.get("iface")) and snap.get("operstate") in ("up", "unknown") and bool(snap.get("ipv4"))
    if baseline:
        if baseline.get("ipv4") and snap.get("ipv4") != baseline.get("ipv4"):
            ok = False
            snap["error"] = "ipv4_changed"
        if baseline.get("iface") and snap.get("iface") != baseline.get("iface"):
            ok = False
            snap["error"] = "iface_changed"
        if int(baseline.get("estab_tcp") or 0) > 0:
            snap["estab_delta"] = int(snap.get("estab_tcp") or 0) - int(baseline.get("estab_tcp") or 0)
    return ok, snap


def relayer_enabled() -> bool:
    if os.environ.get("ZNETWORK_UNDERHOOK", "0") == "1" and os.environ.get("ZNETWORK_RELAYER", "1") != "1":
        return False
    return os.environ.get("ZNETWORK_RELAYER", "1") != "0"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _log(row: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


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


def _gatekeeper_enforce() -> dict[str, Any]:
    gk_sh = INSTALL / "lib" / "gatekeeper-enforce.sh"
    if not gk_sh.is_file():
        return {"ok": False, "skipped": True}
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
            timeout=25,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        return {"ok": proc.returncode == 0, "detail": (proc.stdout or proc.stderr or "")[:240]}
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _firewall_nuke(ip: str, reason: str) -> dict[str, Any]:
    fw = INSTALL / "lib" / "firewall-sentinel.sh"
    if not fw.is_file() or not ip:
        return {"ok": False, "skipped": True}
    safe_ip = ip.replace("'", "")
    safe_reason = reason.replace("'", "")[:80]
    try:
        subprocess.run(
            [
                "bash",
                "-c",
                (
                    f"source '{INSTALL / 'lib' / 'nexus-common.sh'}'; "
                    f"source '{fw}'; "
                    f"nexus_firewall_block_ip_forever out '{safe_ip}' 'relayer:{safe_reason}' || true; "
                    f"nexus_firewall_block_ip_forever in '{safe_ip}' 'relayer:{safe_reason}' || true"
                ),
            ],
            env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
            timeout=15,
            check=False,
        )
        return {"ok": True, "action": "firewall_forever"}
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def retaliate(target: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    """Every method necessary — gatekeeper, firewall, hostile, attack kit, lethal."""
    ip = str(target.get("ip") or target.get("remote_ip") or "").strip()
    entry: dict[str, Any] = {"ip": ip, "ok": False, "actions": [], "target": target}
    if not ip:
        return entry

    wireless = _mod(INSTALL / "lib" / "znetwork-wireless-fcc.py", "wireless_relayer_retaliate")
    if wireless and hasattr(wireless, "is_own_router") and wireless.is_own_router(ip=ip):
        symptom_reason = str(target.get("reason") or target.get("verdict") or "gateway_symptom")[:120]
        if hasattr(wireless, "strike_action_behind"):
            strike = wireless.strike_action_behind(
                {**target, "ip": ip, "symptom_ip": ip, "reason": symptom_reason},
                force=force,
            )
            entry["action_strike"] = strike
            entry["ok"] = bool(strike.get("ok"))
            entry["policy"] = "fix_router_strike_actor"
            _log({"event": "retaliate_trace_strike", "ip": ip, "ok": entry["ok"]})
            return entry
        fix = wireless.fix_own_router(issue="relayer_own_router", detail=symptom_reason)
        entry["own_router_fix"] = fix
        entry["ok"] = True
        entry["policy"] = "fix_not_kill"
        _log({"event": "retaliate_own_router_fix", "ip": ip})
        return entry

    fg = _mod(INSTALL / "lib" / "friendly-guard.py", "friendly_guard_relayer")
    if fg and hasattr(fg, "refuse_kill"):
        refuse, reason = fg.refuse_kill(
            ip,
            {
                "verdict": target.get("verdict") or target.get("gatekeeper_verdict") or "HARM_CANDIDATE",
                "process": target.get("process") or "",
                "trust_rank": int((target.get("scores") or {}).get("trust") or 4),
            },
        )
        if refuse and not force:
            entry["friendly_refused"] = True
            entry["reason"] = reason
            return entry

    reason = str(
        target.get("reason")
        or target.get("verdict")
        or (target.get("vectors") or ["hostile"])[0]
        or "relayer_threat"
    )[:120]
    severity = "critical" if target.get("immediate") or target.get("zero_day_candidate") else "high"
    tier = str(target.get("kill_tier") or "strike")

    hostile = _mod(INSTALL / "lib" / "znetwork-hostile-threat.py", "hostile_relayer")
    if hostile and hasattr(hostile, "_strike_target"):
        strike = hostile._strike_target(
            {
                "ip": ip,
                "verdict": target.get("verdict") or "HARM_CANDIDATE",
                "process": target.get("process"),
                "remote_port": target.get("port") or target.get("remote_port"),
                "immediate": True,
                "kill_eligible": True,
                "kill_tier": tier,
                "reason": reason,
            }
        )
        entry["hostile_strike"] = strike
        entry["actions"].extend(strike.get("actions") or [])

    gk = _gatekeeper_enforce()
    if gk.get("ok"):
        entry["actions"].append("gatekeeper_enforce")

    fw = _firewall_nuke(ip, reason)
    if fw.get("ok"):
        entry["actions"].append("firewall_forever")

    kit = _mod(INSTALL / "lib" / "field-attack-kit.py", "attack_kit_relayer")
    if kit and hasattr(kit, "kill_target"):
        try:
            strike = kit.kill_target(
                ip,
                vector=str(target.get("vector") or "ZNETWORK_RELAYER"),
                severity=severity,
                reason=reason,
                extra={
                    "source": "znetwork-relayer",
                    "strike_mode": "auto",
                    "force": True,
                    "destroy": tier in ("lethal", "strike") or target.get("zero_day_candidate"),
                    "monitor": target,
                },
            )
            entry["attack_kit"] = strike
            if strike.get("killed") or strike.get("ok"):
                entry["actions"].append("attack_kit")
        except Exception as exc:
            entry["attack_kit_error"] = str(exc)

    lethal = _mod(INSTALL / "lib" / "lethal-enforcement.py", "lethal_relayer")
    if lethal and hasattr(lethal, "execute_removal"):
        try:
            row = {
                "remote_ip": ip,
                "ip": ip,
                "process": target.get("process") or "",
                "pid": target.get("pid") or "0",
                "verdict": target.get("verdict") or "HARM_CANDIDATE",
                "iff": target.get("iff") or "HOSTILE",
                "kill_tier": tier,
                "hell_chosen": target.get("hell_chosen"),
            }
            harm = lethal.assess_harm(row) if hasattr(lethal, "assess_harm") else {}
            classification = lethal.classify_removal(row, harm=harm) if hasattr(lethal, "classify_removal") else {}
            if classification.get("removal_level", "pass") != "pass":
                removal = lethal.execute_removal(row, classification, force_insight=force)
                entry["lethal"] = removal
                if removal.get("actions"):
                    entry["actions"].extend(removal["actions"])
        except Exception as exc:
            entry["lethal_error"] = str(exc)

    entry["ok"] = bool(entry["actions"])
    _log({"event": "retaliate", "ip": ip, "ok": entry["ok"], "actions": entry["actions"]})
    return entry


def retaliate_all(report: dict[str, Any] | None = None, *, force: bool = False) -> dict[str, Any]:
    """Nuke every confirmed hostile target in scan report."""
    targets: list[dict[str, Any]] = []
    if report:
        for key in ("immediate", "hostiles", "candidates", "kill_targets"):
            for row in report.get(key) or []:
                if isinstance(row, dict) and (row.get("immediate") or row.get("zero_day_candidate")
                                             or row.get("verdict") in ("HARM_CANDIDATE", "BLOCK_RECOMMENDED")
                                             or row.get("iff") == "HOSTILE"):
                    targets.append(row)

    if not targets:
        exploit = _mod(INSTALL / "lib" / "znetwork-exploit-shield.py", "exploit_relayer")
        if exploit and hasattr(exploit, "scan"):
            er = exploit.scan(publish=True)
            targets = [c for c in (er.get("candidates") or []) if c.get("zero_day_candidate")]
        hostile = _mod(INSTALL / "lib" / "znetwork-hostile-threat.py", "hostile_scan_relayer")
        if hostile and hasattr(hostile, "scan"):
            hr = hostile.scan(publish=True)
            targets.extend(hr.get("immediate") or [])

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for t in targets:
        ip = str(t.get("ip") or t.get("remote_ip") or "")
        if ip and ip not in seen:
            seen.add(ip)
            unique.append(t)

    actions = [retaliate(t, force=force) for t in unique[:32]]
    rep = {
        "schema": SCHEMA,
        "ok": True,
        "targets": len(unique),
        "nuked": sum(1 for a in actions if a.get("ok")),
        "actions": actions,
        "at": _now(),
    }
    _log({"event": "retaliate_all", "targets": rep["targets"], "nuked": rep["nuked"]})
    return rep


def arm(*, force: bool = False) -> dict[str, Any]:
    """After link is stable — enable gatekeeper enforce and retaliation."""
    os.environ["ZNETWORK_RELAYER_ARMED"] = "1"
    os.environ["ZNETWORK_DEFER_RETALIATE"] = "0"
    healthy, snap = link_healthy(_load_json(BASELINE))
    if not healthy and not force and _link_preserve():
        return {"ok": False, "error": "link_not_healthy_abort_arm", "snapshot": snap}
    gk = _gatekeeper_enforce()
    hostile = _mod(INSTALL / "lib" / "znetwork-hostile-threat.py", "hostile_arm")
    hr = hostile.scan(publish=True) if hostile and hasattr(hostile, "scan") else {}
    exploit = _mod(INSTALL / "lib" / "znetwork-exploit-shield.py", "exploit_arm")
    er = exploit.scan(publish=True) if exploit and hasattr(exploit, "scan") else {}
    ret = retaliate_all(er if er.get("ok") else hr, force=False)
    doc = _load_json(POSTURE) or {}
    doc.update({"armed": True, "armed_at": _now(), "link": snap})
    _save(POSTURE, doc)
    return {"ok": True, "schema": SCHEMA, "armed": True, "gatekeeper": gk, "retaliate": ret, "link": snap}


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def relay(*, replace_old: bool = True, invisible: bool | None = None) -> dict[str, Any]:
    """Take over as sole internet relayer — zero link drop, downloads preserved."""
    if invisible is None:
        invisible = _invisible_replace()
    steps: dict[str, Any] = {}

    baseline = link_snapshot()
    _save(BASELINE, baseline)
    steps["baseline"] = baseline

    wireless = _mod(INSTALL / "lib" / "znetwork-wireless-fcc.py", "wireless_relayer")
    if wireless and hasattr(wireless, "bind_own_router"):
        steps["own_router"] = wireless.bind_own_router()
    if wireless and hasattr(wireless, "scan_wireless_fcc"):
        steps["wireless_fcc"] = wireless.scan_wireless_fcc(bind=False)
    pre_ok, pre_snap = link_healthy(baseline)
    steps["pre_link"] = {"ok": pre_ok, "snapshot": pre_snap}
    if not pre_ok and _link_preserve():
        return {
            "ok": False,
            "schema": SCHEMA,
            "error": "link_not_healthy_before_handoff",
            "steps": steps,
        }

    if replace_old:
        repl = _mod(INSTALL / "lib" / "znetwork-replace-in-place.py", "replace_relayer")
        if repl and hasattr(repl, "replace_in_place"):
            steps["replace_old"] = repl.replace_in_place(force=True)
        smart = _mod(INSTALL / "lib" / "znetwork-smart-inside.py", "smart_relayer")
        if smart and hasattr(smart, "own_connection"):
            steps["own_connection"] = smart.own_connection()

    exploit = _mod(INSTALL / "lib" / "znetwork-exploit-shield.py", "exploit_relay")
    if exploit and hasattr(exploit, "scan"):
        steps["exploit_scan"] = exploit.scan(publish=True)

    hostile = _mod(INSTALL / "lib" / "znetwork-hostile-threat.py", "hostile_relay")
    if hostile and hasattr(hostile, "scan"):
        steps["hostile_scan"] = hostile.scan(publish=True)

    post_ok, post_snap = link_healthy(baseline)
    steps["post_link"] = {"ok": post_ok, "snapshot": post_snap}
    if not post_ok and _link_preserve():
        return {
            "ok": False,
            "schema": SCHEMA,
            "error": "link_unhealthy_abort_handoff",
            "steps": steps,
        }

    if invisible or _defer_retaliate():
        steps["gatekeeper"] = {"ok": True, "skipped": True, "reason": "deferred_until_armed"}
        steps["retaliate"] = {"ok": True, "skipped": True, "reason": "deferred_until_armed"}
    else:
        steps["gatekeeper"] = _gatekeeper_enforce()
        steps["retaliate"] = retaliate_all(
            steps.get("exploit_scan") or steps.get("hostile_scan"),
            force=False,
        )

    marker = {
        "schema": "znetwork-relayer/v1",
        "active": True,
        "layer": "relayer",
        "sole_stack": True,
        "ingress_egress_owner": "znetwork",
        "civilian_passthrough": True,
        "retaliate_on_threat": True,
        "invisible_replace": invisible,
        "link_preserved": post_ok,
        "armed": False,
        "downloads_safe": True,
        "mode": os.environ.get("ZNETWORK_MODE", "ACTIVE"),
        "updated": _now(),
        "policy": "invisible_handoff_no_drop_deferred_arm",
    }
    _save(STATE / "znetwork-relayer.json", marker)
    _save(POSTURE, marker)

    guard = {
        "schema": "znetwork-handler-guard/v1",
        "active": True,
        "relayer": True,
        "sole_stack": True,
        "smart_inside": True,
        "exploit_shield": True,
        "retaliate_enabled": True,
        "coexist_os": True,
        "policy_owner": "znetwork",
        "motto": "Relayer owns internet in/out — civilian passes, hostile nuked immediately.",
        "retired_at": _now(),
    }
    _save(STATE / "znetwork-handler-guard.json", guard)

    try:
        (STATE / "znetwork-running.marker").write_text(
            f"running=1\nstack=relayer\nupdated={_now()}\n",
            encoding="utf-8",
        )
    except OSError:
        pass

    rep = {
        "schema": SCHEMA,
        "ok": True,
        "relayer": marker,
        "invisible": invisible,
        "link_preserved": post_ok,
        "steps": {k: v for k, v in steps.items() if k != "retaliate"},
        "retaliate": steps.get("retaliate"),
        "motto": marker["policy"],
    }
    _log({"event": "relay", "ok": True, "invisible": invisible, "link_preserved": post_ok})
    return rep


def watch() -> dict[str, Any]:
    """Continuous relayer watch — scan; retaliate only when armed."""
    if _defer_retaliate():
        exploit = _mod(INSTALL / "lib" / "znetwork-exploit-shield.py", "exploit_watch_only")
        er = exploit.scan(publish=True) if exploit and hasattr(exploit, "scan") else {"ok": True}
        return {"ok": True, "skipped": True, "reason": "not_armed_scan_only", "scan": er}
    exploit = _mod(INSTALL / "lib" / "znetwork-exploit-shield.py", "exploit_watch")
    er = exploit.scan(publish=True) if exploit and hasattr(exploit, "scan") else {}
    hostile = _mod(INSTALL / "lib" / "znetwork-hostile-threat.py", "hostile_watch")
    hr = hostile.scan(publish=True) if hostile and hasattr(hostile, "scan") else {}
    merged = {**hr, "candidates": (er.get("candidates") or []) + (hr.get("hostiles") or [])}
    return retaliate_all(merged, force=False)


def posture() -> dict[str, Any]:
    healthy, snap = link_healthy(_load_json(BASELINE))
    enabled = relayer_enabled()
    target = int(os.environ.get("ZNETWORK_INTERNET_PIPE_TARGET", "100") or "100")
    pipe = target if enabled and healthy else (target if enabled else 0)
    return {
        "schema": SCHEMA,
        "ok": True,
        "enabled": enabled,
        "sole_internet_stack": True,
        "internet_pipe_percent": min(100, max(0, pipe)),
        "internet_pipe_target": target,
        "ingress_egress_owner": "znetwork",
        "loopback_authority": "127.0.0.1",
        "posture": _load_json(POSTURE),
        "baseline": _load_json(BASELINE),
        "link_healthy": healthy,
        "link": snap,
        "checked_at": _now(),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    force = "--force" in sys.argv
    handlers = {
        "json": posture,
        "posture": posture,
        "link": lambda: (lambda h, s: {"ok": h, "healthy": h, "snapshot": s})(*link_healthy(_load_json(BASELINE))),
        "relay": lambda: relay(replace_old=True),
        "watch": watch,
        "arm": lambda: arm(force=force),
        "retaliate": lambda: retaliate_all(force=force),
    }
    fn = handlers.get(cmd)
    if not fn:
        print(json.dumps({"error": "usage: znetwork-relayer.py [json|relay|watch|retaliate]"}), file=sys.stderr)
        return 2
    result = fn()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())