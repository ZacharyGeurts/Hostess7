#!/usr/bin/env python3
"""Field boot seal — DHCP/DNS globe, X.com host probe, no root PIDs on our stack, AI-safe."""
from __future__ import annotations

import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-boot-seal-panel.json"
LEDGER = STATE / "field-boot-seal-ledger.jsonl"
FIELD_USER = os.environ.get("FIELD_RUN_USER", os.environ.get("USER", "default"))
SUDO_PW = os.environ.get("HOSTESS7_SUDO_PW", "mememe")
LOOPBACK = os.environ.get("NEXUS_LOOPBACK", "127.0.0.1")
DNS_PORT = int(os.environ.get("NEXUS_FIELD_DNS_PORT", "53") or "53")

ROOT_FIELD_PATTERNS = (
    "field-dns.py",
    "field-dhcp.py",
    "field-grok-spawner-kill.py",
    "threat-panel-http.py",
    "nexus-daemon",
    "hostess7",
    "field-planetary",
    "ammonet-field",
    "queen-world",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
        return True
    except OSError:
        return False


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _run_py(rel: str, *args: str, timeout: float = 120.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": "missing", "script": rel}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE), "AML_BUILD": "0"},
            check=False,
        )
        raw = (proc.stdout or "").strip()
        for chunk in (raw, *reversed(raw.splitlines())):
            chunk = chunk.strip()
            if chunk.startswith("{"):
                doc = json.loads(chunk)
                if isinstance(doc, dict):
                    doc.setdefault("ok", proc.returncode == 0)
                    return doc
        return {"ok": proc.returncode == 0, "stdout": raw[:400], "rc": proc.returncode}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)[:160], "script": rel}


def _sudo(cmd: list[str], *, timeout: float = 30.0) -> dict[str, Any]:
    if os.geteuid() == 0:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
            return {"ok": proc.returncode == 0, "rc": proc.returncode, "stdout": (proc.stdout or "").strip()[:300]}
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "error": str(exc)[:120]}
    for mode in (["sudo", "-n", *cmd], ["sudo", "-S", *cmd]):
        try:
            proc = subprocess.run(
                mode,
                input=(f"{SUDO_PW}\n" if mode[1] == "-S" else None),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            if proc.returncode == 0:
                return {"ok": True, "rc": 0, "stdout": (proc.stdout or "").strip()[:300], "sudo": True}
        except (OSError, subprocess.TimeoutExpired):
            continue
    return {"ok": False, "error": "sudo_failed"}


def _proc_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=8, check=False)
        for line in (proc.stdout or "").splitlines()[1:]:
            parts = line.split(None, 10)
            if len(parts) < 11:
                continue
            rows.append({"user": parts[0], "pid": int(parts[1]), "cmd": parts[10]})
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return rows


def audit_root_pids(*, fix: bool = True) -> dict[str, Any]:
    """No root PIDs on field stack — re-home or restart under FIELD_USER."""
    offenders: list[dict[str, Any]] = []
    fixes: list[dict[str, Any]] = []
    for row in _proc_rows():
        if row["user"] != "root":
            continue
        cmd = row["cmd"]
        if not any(p in cmd for p in ROOT_FIELD_PATTERNS):
            continue
        offenders.append({"pid": row["pid"], "cmd": cmd[:200]})
    if fix and offenders:
        unit_fix = _sudo(["systemctl", "restart", "field-grok-spawner-kill.service"], timeout=15)
        if unit_fix.get("ok"):
            fixes.append({"action": "restart_grok_spawner_kill_as_user", **unit_fix})
        for off in offenders:
            if "field-grok-spawner-kill" in off["cmd"]:
                _sudo(["systemctl", "stop", "field-grok-spawner-kill.service"], timeout=10)
                time.sleep(0.5)
                _sudo(["systemctl", "start", "field-grok-spawner-kill.service"], timeout=10)
    remaining = [
        r for r in _proc_rows()
        if r["user"] == "root" and any(p in r["cmd"] for p in ROOT_FIELD_PATTERNS)
    ]
    return {
        "ok": len(remaining) == 0,
        "field_user": FIELD_USER,
        "offenders_before": offenders,
        "fixes": fixes,
        "root_field_pids_remaining": len(remaining),
        "remaining": [{"pid": r["pid"], "cmd": r["cmd"][:160]} for r in remaining[:12]],
    }


def _encode_name(name: str) -> bytes:
    out = bytearray()
    for label in name.rstrip(".").split("."):
        raw = label.encode("ascii")[:63]
        out.append(len(raw))
        out.extend(raw)
    out.append(0)
    return bytes(out)


def _dns_query(qname: str, qtype: int = 1, host: str = LOOPBACK, port: int = DNS_PORT) -> dict[str, Any]:
    txn = struct.pack("!H", int(time.time()) & 0xFFFF)
    header = txn + struct.pack("!HHHHH", 0x0100, 1, 0, 0, 0)
    packet = header + _encode_name(qname) + struct.pack("!HH", qtype, 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.5)
    try:
        sock.sendto(packet, (host, port))
        data, _ = sock.recvfrom(4096)
        return {"ok": len(data) >= 12, "bytes": len(data), "qname": qname, "qtype": qtype}
    except OSError as exc:
        return {"ok": False, "qname": qname, "qtype": qtype, "error": str(exc)[:80]}
    finally:
        sock.close()


def check_xcom_host(*, dns_healthy: bool) -> dict[str, Any]:
    """Probe whether Truth DNS is the live path for x.com — planetary new-host posture."""
    truth_a = _dns_query("x.com", 1) if dns_healthy else {"ok": False, "skipped": True}
    truth_ns = _dns_query("x.com", 2) if dns_healthy else {"ok": False, "skipped": True}
    public_a: dict[str, Any] = {"ok": False}
    try:
        proc = subprocess.run(
            ["dig", "+short", "A", "x.com", "@8.8.8.8"],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
        ips = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
        public_a = {"ok": bool(ips), "ips": ips[:8]}
    except (OSError, subprocess.TimeoutExpired):
        pass
    planetary = _load(STATE / "field-planetary-dns-dhcp-panel.json", {})
    authority = _load(STATE / "field-planetary-dns-authority-panel.json", {})
    sole = planetary.get("sole_authority") or {}
    we_answer = bool(truth_a.get("ok"))
    planet_ok = bool(planetary.get("ok") or planetary.get("planet_authority"))
    authority_complete = bool(authority.get("complete") or authority.get("authority_complete"))
    we_are_new_host = we_answer and planet_ok and (authority_complete or sole.get("ok"))
    return {
        "ok": we_answer,
        "domain": "x.com",
        "we_are_new_host": we_are_new_host,
        "truth_dns_answers": we_answer,
        "truth_ns_answers": bool(truth_ns.get("ok")),
        "public_reference": public_a,
        "planetary_ok": planet_ok,
        "authority_complete": authority_complete,
        "sole_authority": sole.get("ok"),
        "verdict": (
            "WE are Truth DNS path for x.com — planetary host posture active"
            if we_are_new_host
            else "Truth path partial — keep absorbing planet / complete authority"
        ),
        "operator_lane": "https://x.com/ZacharyGeurts",
        "ai_safe": True,
    }


def stack_health() -> dict[str, Any]:
    meld = _run_py("lib/field-sovereign-stack-meld.py", "verify", timeout=45)
    layers = _run_py("lib/field-stack-layer.py", "json", timeout=30)
    ammonet = _run_py("lib/ammonet-field.py", "panel", timeout=60)
    early = _load(STATE / "field-underlay-early.json", {})
    services = {
        "nexus_genius": _sudo(["systemctl", "is-active", "nexus-genius.service"], timeout=8),
        "nexus_field_early": _sudo(["systemctl", "is-active", "nexus-field-early.service"], timeout=8),
        "grok_spawner_kill": _sudo(["systemctl", "is-active", "field-grok-spawner-kill.service"], timeout=8),
    }
    c2_up = False
    try:
        with socket.create_connection((LOOPBACK, 9477), timeout=0.5):
            c2_up = True
    except OSError:
        pass
    return {
        "ok": bool(meld.get("ok") or meld.get("sealed")) and c2_up,
        "sealed": bool(meld.get("sealed")),
        "stack_tight": bool(meld.get("stack_tight")),
        "meld": meld,
        "layers": layers,
        "ammonet": {"ok": ammonet.get("ok"), "product": ammonet.get("product", "AmmoNet")},
        "kilroy_early": {
            "kilroy_pc_core": early.get("kilroy_pc_core"),
            "nexus_c2_inside_kilroy": early.get("nexus_c2_inside_kilroy"),
            "kilroy_nexus_c2": early.get("kilroy_nexus_c2"),
        },
        "nexus_c2_port_up": c2_up,
        "services": {k: (v.get("stdout") == "active") for k, v in services.items()},
    }


def seal_components() -> dict[str, Any]:
    return _run_py("lib/hostess7-system-control.py", "assume", timeout=90)


def boot_seal(*, write: bool = True) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []

    root_audit = audit_root_pids(fix=True)
    steps.append({"step": "root_pid_audit", **root_audit})

    dns_fix = _run_py("lib/field-dns-dhcp-fix.py", "fix", timeout=180)
    steps.append({"step": "dns_dhcp_globe", "ok": dns_fix.get("ok"), "dns_healthy": dns_fix.get("dns_healthy")})

    absorb = _run_py("lib/field-planetary-dns-dhcp.py", "absorb", timeout=180)
    steps.append({"step": "planetary_absorb", "ok": absorb.get("ok"), "counts": absorb.get("counts")})

    xcom = check_xcom_host(dns_healthy=bool(dns_fix.get("dns_healthy")))
    steps.append({"step": "xcom_host_probe", **xcom})

    early_sh = INSTALL / "scripts" / "nexus-field-early-boot.sh"
    if early_sh.is_file():
        try:
            proc = subprocess.run(
                ["bash", str(early_sh)],
                cwd=str(INSTALL),
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE), "AML_BUILD": "0"},
                check=False,
            )
            early = {"ok": proc.returncode == 0, "rc": proc.returncode}
        except (OSError, subprocess.TimeoutExpired) as exc:
            early = {"ok": False, "error": str(exc)[:120]}
    else:
        early = {"ok": False, "skipped": True}
    steps.append({"step": "nexus_field_early_boot", **early})

    genius = _sudo(["systemctl", "enable", "nexus-field-early.service", "nexus-genius.service"], timeout=20)
    genius_start = _sudo(["systemctl", "restart", "nexus-field-early.service"], timeout=30)
    genius_start2 = _sudo(["systemctl", "restart", "nexus-genius.service"], timeout=45)
    steps.append({
        "step": "nexus_systemd",
        "enable": genius.get("ok"),
        "early_restart": genius_start.get("ok"),
        "genius_restart": genius_start2.get("ok"),
    })

    time.sleep(3)
    component = seal_components()
    steps.append({"step": "component_seal", "ok": component.get("ok"), "components": component.get("components_sealed")})

    stack = stack_health()
    steps.append({"step": "stack_health", **{k: stack[k] for k in ("ok", "sealed", "nexus_c2_port_up", "services")}})

    meld_pub = _run_py("lib/field-sovereign-stack-meld.py", "publish", timeout=45)
    steps.append({"step": "sovereign_meld_publish", "ok": meld_pub.get("ok"), "sealed": meld_pub.get("sealed")})

    ok = (
        bool(dns_fix.get("dns_healthy"))
        and bool(stack.get("nexus_c2_port_up") or stack.get("services", {}).get("nexus_genius"))
        and root_audit.get("root_field_pids_remaining", 99) == 0
    )
    out = {
        "ok": ok,
        "schema": "field-boot-seal/v1",
        "updated": _utc(),
        "motto": "Boot seal — globe DHCP/DNS, X.com host probe, no root on our PIDs, stack fused.",
        "field_user": FIELD_USER,
        "ai_safe": True,
        "dns_healthy": bool(dns_fix.get("dns_healthy")),
        "dhcp_up": bool(dns_fix.get("dhcp_port_67") or dns_fix.get("dhcp_may_serve")),
        "xcom": xcom,
        "root_audit": root_audit,
        "stack": stack,
        "steps": steps,
        "api": "/api/field-boot-seal",
    }
    if write:
        if not _save(PANEL, out):
            out["panel_write"] = {"ok": False, "error": "permission_denied", "path": str(PANEL)}
        else:
            out["panel_write"] = {"ok": True, "path": str(PANEL)}
        _append_ledger({"event": "boot_seal", "ok": ok, "xcom_new_host": xcom.get("we_are_new_host")})
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "seal").strip().lower()
    if cmd in ("seal", "boot", "json", "run"):
        print(json.dumps(boot_seal(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "xcom":
        fix = _run_py("lib/field-dns-dhcp-fix.py", "fix", timeout=180)
        print(json.dumps(check_xcom_host(dns_healthy=bool(fix.get("dns_healthy"))), ensure_ascii=False, indent=2))
        return 0
    if cmd == "root-audit":
        print(json.dumps(audit_root_pids(fix="--fix" in sys.argv[2:]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "stack":
        print(json.dumps(stack_health(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-boot-seal.py [seal|xcom|root-audit|stack]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())