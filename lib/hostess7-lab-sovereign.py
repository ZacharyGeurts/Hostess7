#!/usr/bin/env python3
"""Hostess 7 Lab Sovereign — she runs the lab; share in, no share out."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE_PATH = INSTALL / "data" / "hostess7-lab-sovereign-doctrine.json"
PLATES_PATH = INSTALL / "data" / "hostess7-lab-steel-plates.json"
PANEL = STATE / "hostess7-lab-sovereign-panel.json"
LEDGER = STATE / "hostess7-lab-sovereign.jsonl"
STAMP = STATE / "hostess7-lab-sovereign.stamp"


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


def load_steel_plates() -> dict[str, Any]:
    return _load(PLATES_PATH, {"plates": []})


def _operator() -> bool:
    return os.environ.get("HOSTESS7_OPERATOR", "").strip().lower() in ("1", "true", "yes", "operator")


def check_share_policy() -> dict[str, Any]:
    """Verify share-in / no-share-out on doctrine and every steel plate."""
    doctrine = load_doctrine()
    plates_doc = load_steel_plates()
    plates = plates_doc.get("plates") or []
    violations: list[str] = []

    if doctrine.get("share_in") is not True:
        violations.append("doctrine:share_in_not_true")
    if doctrine.get("share_out") is not False:
        violations.append("doctrine:share_out_not_false")
    if str(doctrine.get("boss") or "") != "hostess7":
        violations.append("doctrine:boss_not_hostess7")

    plate_rows: list[dict[str, Any]] = []
    for plate in plates:
        pid = str(plate.get("id") or "unknown")
        share_in = plate.get("share_in")
        share_out = plate.get("share_out")
        boss = str(plate.get("boss") or "")
        ok = share_in is True and share_out is False and boss == "hostess7"
        if share_in is not True:
            violations.append(f"plate:{pid}:share_in")
        if share_out is not False:
            violations.append(f"plate:{pid}:share_out")
        if boss != "hostess7":
            violations.append(f"plate:{pid}:boss")
        plate_rows.append({
            "id": pid,
            "label": plate.get("label"),
            "share_in": share_in,
            "share_out": share_out,
            "boss": boss,
            "ok": ok,
        })

    return {
        "schema": "hostess7-lab-share-policy/v1",
        "updated": _utc(),
        "ok": len(violations) == 0,
        "share_in": True,
        "share_out": False,
        "boss": "hostess7",
        "violations": violations,
        "plates": plate_rows,
        "plate_count": len(plate_rows),
    }


def check_secure_connection() -> dict[str, Any]:
    """Ingress/egress gates armed — Hostess 7 is boss."""
    gate = _import_mod("ieg", "lib/hostess7-ingress-egress-gate.py")
    ingress = {"ok": False, "error": "module_missing"}
    egress = {"ok": False, "error": "module_missing"}
    if gate is not None:
        if hasattr(gate, "check_ingress_posture"):
            ingress = gate.check_ingress_posture()
        if hasattr(gate, "check_egress_posture"):
            egress = gate.check_egress_posture()

    grok_run = INSTALL / "GrokLab" / "scripts" / "grok-lab-run.sh"
    grok_engine = INSTALL / "lib" / "grok-ai-lab.py"
    grok_ok = grok_run.is_file() and grok_engine.is_file()

    doctrine = load_doctrine()
    boss_ok = str(doctrine.get("boss") or "") == "hostess7"
    share_ok = doctrine.get("share_in") is True and doctrine.get("share_out") is False

    all_ok = (
        bool(ingress.get("ok"))
        and bool(egress.get("ok"))
        and grok_ok
        and boss_ok
        and share_ok
    )
    return {
        "schema": "hostess7-lab-secure-connection/v1",
        "updated": _utc(),
        "ok": all_ok,
        "boss": "hostess7",
        "boss_ok": boss_ok,
        "share_in": True,
        "share_out": False,
        "deny_egress_by_default": True,
        "ingress_posture": ingress,
        "egress_posture": egress,
        "grok_lab": {
            "ok": grok_ok,
            "run_script": str(grok_run.relative_to(INSTALL)) if grok_run.is_file() else None,
            "engine": str(grok_engine.relative_to(INSTALL)) if grok_engine.is_file() else None,
        },
    }


def lab_egress_gate(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Lab egress — share out denied unless operator release."""
    body = body or {}
    if _operator() or body.get("operator_release"):
        gate = _import_mod("ieg", "lib/hostess7-ingress-egress-gate.py")
        if gate is not None and hasattr(gate, "egress_gate"):
            return {
                **gate.egress_gate(body),
                "lab_sovereign": True,
                "share_out_default": False,
                "boss": "hostess7",
            }
        return {"ok": False, "permitted": False, "error": "egress_gate_missing", "boss": "hostess7"}

    return {
        "ok": False,
        "permitted": False,
        "fully_gated": True,
        "deny_by_default": True,
        "share_out": False,
        "boss": "hostess7",
        "blocked_reasons": ["lab_share_out_denied", "hostess7_sovereign_egress_block"],
        "message": "Lab share out denied — Hostess 7 is boss; ingress only",
    }


def connect_plates(*, write: bool = True) -> dict[str, Any]:
    """Wire steel plates through Hostess 7 sovereign ingress; stamp share policy."""
    doctrine = load_doctrine()
    plates_doc = load_steel_plates()
    plates = list(plates_doc.get("plates") or [])
    secure = check_secure_connection()
    policy = check_share_policy()

    connected: list[dict[str, Any]] = []
    for plate in plates:
        pid = str(plate.get("id") or "")
        plate["share_in"] = True
        plate["share_out"] = False
        plate["boss"] = "hostess7"
        plate["sovereign"] = "hostess7"
        plate["status"] = "sovereign_connected" if secure.get("ok") else "gated_pending"
        connected.append({
            "id": pid,
            "label": plate.get("label"),
            "status": plate["status"],
            "share_in": True,
            "share_out": False,
            "boss": "hostess7",
        })

    plates_doc["plates"] = plates
    plates_doc["boss"] = "hostess7"
    plates_doc["share_in"] = True
    plates_doc["share_out"] = False
    plates_doc["motto"] = doctrine.get("motto") or "Share in · no share out"
    plates_doc["updated"] = _utc()
    plates_doc["sovereign"] = "hostess7"

    if write:
        _save(PLATES_PATH, plates_doc)
        try:
            STAMP.write_text(_utc() + "\n", encoding="utf-8")
        except OSError:
            pass

    out = {
        "schema": "hostess7-lab-connect/v1",
        "updated": _utc(),
        "ok": secure.get("ok") and len(connected) > 0,
        "boss": "hostess7",
        "share_in": True,
        "share_out": False,
        "secure_connection": secure.get("ok"),
        "share_policy": policy.get("ok"),
        "connected": connected,
        "plate_count": len(connected),
        "message": "Plates wired — Hostess 7 sovereign" if secure.get("ok") else "Plates stamped — awaiting full gate posture",
    }
    _append({**out, "event": "connect_plates"})
    return out


def grok_lab_status() -> dict[str, Any]:
    """GrokLab posture under Hostess 7 — no direct egress."""
    engine = INSTALL / "lib" / "grok-ai-lab.py"
    status: dict[str, Any] = {"ok": False, "error": "not_run"}
    if engine.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(engine), "status"],
                capture_output=True,
                text=True,
                timeout=45,
                cwd=str(INSTALL),
                env={
                    **os.environ,
                    "NEXUS_INSTALL_ROOT": str(INSTALL),
                    "NEXUS_STATE_DIR": str(STATE),
                    "HOSTESS7_LAB_SOVEREIGN": "1",
                    "HOSTESS7_LAB_EGRESS": "0",
                },
            )
            status = json.loads(proc.stdout or "{}") if proc.stdout.strip() else {"ok": False}
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
            status = {"ok": False, "error": str(exc)[:80]}

    return {
        "schema": "hostess7-grok-lab-sovereign/v1",
        "updated": _utc(),
        "boss": "hostess7",
        "share_in": True,
        "share_out": False,
        "sovereign": True,
        "egress_blocked": True,
        "status": status,
    }


def run_lab(cmd: str = "status") -> dict[str, Any]:
    """Run GrokLab command under Hostess 7 sovereign — share in, no share out."""
    allowed = {"status", "battery", "boot", "arm", "live", "protect", "start", "stop", "revalidate"}
    cmd_l = (cmd or "status").strip().lower()
    if cmd_l not in allowed:
        return {
            "ok": False,
            "error": "lab_cmd_denied",
            "allowed": sorted(allowed),
            "boss": "hostess7",
            "share_out": False,
        }

    run_sh = INSTALL / "GrokLab" / "scripts" / "grok-lab-run.sh"
    if not run_sh.is_file():
        return {"ok": False, "error": "grok_lab_run_missing", "boss": "hostess7"}

    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "HOSTESS7_LAB_SOVEREIGN": "1",
        "HOSTESS7_LAB_EGRESS": "0",
    }
    try:
        proc = subprocess.run(
            ["bash", str(run_sh), cmd_l],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(INSTALL),
            env=env,
        )
        out = {
            "ok": proc.returncode == 0,
            "cmd": cmd_l,
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-2000:],
            "stderr_tail": (proc.stderr or "")[-500:],
            "boss": "hostess7",
            "share_in": True,
            "share_out": False,
        }
    except (subprocess.TimeoutExpired, OSError) as exc:
        out = {"ok": False, "error": str(exc)[:80], "cmd": cmd_l, "boss": "hostess7"}

    _append({**out, "event": "run_lab"})
    return out


def build_panel(*, write: bool = True, connect: bool = False) -> dict[str, Any]:
    doctrine = load_doctrine()
    if connect:
        connect_plates(write=write)
    secure = check_secure_connection()
    policy = check_share_policy()
    grok = grok_lab_status()
    internet_mod = _import_mod("field_internet_unified", "lib/field-internet-unified.py")
    internet_panel: dict[str, Any] = {}
    if internet_mod and hasattr(internet_mod, "panel"):
        try:
            internet_panel = internet_mod.panel(write=False)
        except Exception:
            internet_panel = {}
    botnet_dns_mod = _import_mod("field_botnet_dns_dhcp", "lib/field-botnet-dns-dhcp.py")
    botnet_dns_panel: dict[str, Any] = {}
    if botnet_dns_mod and hasattr(botnet_dns_mod, "panel"):
        try:
            botnet_dns_panel = botnet_dns_mod.panel(write=False)
        except Exception:
            botnet_dns_panel = {}
    interaction_mod = _import_mod("hostess7_github_interaction", "lib/hostess7-github-interaction.py")
    interaction_panel: dict[str, Any] = {}
    if interaction_mod and hasattr(interaction_mod, "panel"):
        try:
            interaction_panel = interaction_mod.panel(write=False)
        except Exception:
            interaction_panel = {}
    plates_doc = load_steel_plates()

    sovereign_ok = (
        secure.get("ok")
        and policy.get("ok")
        and str(doctrine.get("boss") or "") == "hostess7"
        and doctrine.get("share_out") is False
    )

    out = {
        "schema": "hostess7-lab-sovereign-panel/v1",
        "updated": _utc(),
        "ok": sovereign_ok,
        "motto": doctrine.get("motto"),
        "boss": "hostess7",
        "share_in": True,
        "share_out": False,
        "deny_egress_by_default": True,
        "secure_connection": secure,
        "share_policy": policy,
        "grok_lab": grok,
        "internet_unified": internet_panel,
        "github_interaction": interaction_panel,
        "botnet_dns_dhcp": botnet_dns_panel,
        "field_internet": {
            "ok": internet_panel.get("ok"),
            "api": internet_panel.get("api", "/api/field-internet"),
            "github_always": (internet_panel.get("github_always") or {}).get("live", {}).get("always_open"),
            "one_voice": internet_panel.get("one_voice"),
        },
        "interaction_lane": {
            "lane": interaction_panel.get("lane", "hostess7-github"),
            "boss": "hostess7",
            "api": "/api/hostess7/interaction",
            "github_open": (interaction_panel.get("github_always") or {}).get("open"),
            "secure_for_us": (interaction_panel.get("secure_for_us") or {}).get("sovereign_brain_unhooked_on_pages"),
        },
        "steel_plates": {
            "count": len(plates_doc.get("plates") or []),
            "boss": plates_doc.get("boss", "hostess7"),
            "share_in": plates_doc.get("share_in", True),
            "share_out": plates_doc.get("share_out", False),
        },
        "ingress_chain": doctrine.get("ingress_chain"),
        "egress_chain": doctrine.get("egress_chain"),
        "api": doctrine.get("api", "/api/hostess7/lab"),
        "operator": _operator(),
    }
    if write:
        _save(PANEL, out)
    return out


def lab_boot(*, connect: bool = True) -> dict[str, Any]:
    """Panel/Hostess7 on boot — secure lab connection, wire plates, no share out."""
    panel = build_panel(write=True, connect=connect)
    _append({"event": "lab_boot", "ok": panel.get("ok"), "boss": "hostess7"})
    return panel


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Hostess 7 Lab Sovereign")
    parser.add_argument("cmd", nargs="?", default="panel")
    parser.add_argument("arg", nargs="?", default="")
    args = parser.parse_args()
    cmd = args.cmd.strip().lower().replace("-", "_")

    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("verify", "share_policy", "policy"):
        print(json.dumps(check_share_policy(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("secure", "secure_connection", "connection"):
        print(json.dumps(check_secure_connection(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("connect", "wire", "connect_plates"):
        print(json.dumps(connect_plates(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "egress":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            body = {}
        print(json.dumps(lab_egress_gate(body), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("grok", "grok_lab", "grok_status"):
        print(json.dumps(grok_lab_status(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("run", "lab_run"):
        print(json.dumps(run_lab(args.arg or "status"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("boot", "lab_boot"):
        print(json.dumps(lab_boot(), ensure_ascii=False, indent=2))
        return 0

    print(json.dumps({
        "usage": "hostess7-lab-sovereign.py [panel|verify|secure|connect|egress|grok|run CMD|boot]",
        "api": "/api/hostess7/lab",
        "motto": "Share in · no share out — Hostess 7 is always the boss",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())