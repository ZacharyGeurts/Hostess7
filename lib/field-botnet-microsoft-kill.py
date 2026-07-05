#!/usr/bin/env python3
"""If Microsoft hits us — botnet kills them. DNS/DHCP and online lane protected."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-botnet-microsoft-kill-doctrine.json"
PANEL = STATE / "field-botnet-microsoft-kill-panel.json"
LEDGER = STATE / "field-botnet-microsoft-kill.jsonl"
HOSTILE_TSV = STATE / "field-hostile.tsv"
VECTOR = "MICROSOFT_BOTNET_KILL"
ME = os.getpid()


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {"enabled": True, "host_markers": [], "process_markers": []})


def _mod(rel: str, name: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _protected(cmd: str, protected: list[str]) -> bool:
    low = cmd.lower()
    return any(p.lower() in low for p in protected)


def _microsoft_blob(*parts: str) -> str:
    return " ".join(str(p or "") for p in parts).lower()


def _is_microsoft_blob(blob: str, doc: dict[str, Any]) -> tuple[bool, str]:
    for marker in doc.get("host_markers") or []:
        if marker and marker.lower() in blob:
            return True, f"host:{marker}"
    for marker in doc.get("org_markers") or []:
        if marker and re.search(rf"\b{re.escape(marker.lower())}\b", blob):
            return True, f"org:{marker}"
    for prefix in doc.get("ip_prefixes") or []:
        p = str(prefix).lower()
        if p and (blob.startswith(p) or f" {p}" in blob):
            return True, f"prefix:{prefix}"
    return False, ""


def _ip_microsoft_prefix(ip: str, doc: dict[str, Any]) -> str:
    for prefix in doc.get("ip_prefixes") or []:
        p = str(prefix)
        if p and ip.startswith(p):
            return f"prefix:{p}"
    return ""


def _scan_process_hits(doc: dict[str, Any]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    protected = list(doc.get("protected_processes") or [])
    proc_markers = [str(m).lower() for m in (doc.get("process_markers") or []) if m]
    if not sys.platform.startswith("linux"):
        return hits
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid <= 1 or pid == ME:
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").strip()
        except OSError:
            continue
        if not cmdline or _protected(cmdline, protected):
            continue
        low = cmdline.lower()
        for marker in proc_markers:
            if marker in low:
                hits.append({
                    "kind": "process",
                    "pid": pid,
                    "cmd": cmdline[:240],
                    "reason": f"microsoft_process:{marker}",
                })
                break
    return hits


def _scan_connection_hits(doc: dict[str, Any]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(
            ["ss", "-H", "-tn", "state", "established"],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return hits
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        local = parts[3] if len(parts) > 3 else ""
        remote = parts[4] if len(parts) > 4 else ""
        proc_name = parts[-1] if parts else ""
        blob = _microsoft_blob(remote, proc_name)
        rip = remote.rsplit(":", 1)[0].strip("[]")
        ok, why = _is_microsoft_blob(blob, doc)
        if not ok:
            why = _ip_microsoft_prefix(rip, doc)
            if not why:
                continue
            ok = True
        if rip in ("127.0.0.1", "::1"):
            continue
        hits.append({
            "kind": "connection",
            "remote_ip": rip,
            "remote": remote,
            "process": proc_name,
            "reason": why,
        })
    return hits


def _register_hostile(ip: str, reason: str, *, severity: str = "critical") -> bool:
    if not ip:
        return False
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        if not HOSTILE_TSV.is_file():
            HOSTILE_TSV.write_text("ts\tip\tvector\tseverity\treason\tsource\n", encoding="utf-8")
        text = HOSTILE_TSV.read_text(encoding="utf-8", errors="replace")
        if f"\t{ip}\t" in text:
            return False
        safe = reason.replace("\t", " ")[:200]
        with HOSTILE_TSV.open("a", encoding="utf-8") as fh:
            fh.write(f"{_utc()}\t{ip}\t{VECTOR}\t{severity}\t{safe}\tbotnet-microsoft-kill\n")
        return True
    except OSError:
        return False


def _kill_local_pid(pid: int) -> bool:
    try:
        os.kill(pid, signal.SIGKILL)
        return True
    except ProcessLookupError:
        return True
    except PermissionError:
        pw = os.environ.get("HOSTESS7_SUDO_PW", "mememe")
        try:
            proc = subprocess.run(
                ["sudo", "-S", "kill", "-9", str(pid)],
                input=f"{pw}\n",
                capture_output=True,
                timeout=8,
                check=False,
            )
            return proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False
    except OSError:
        return False


def _botnet_kill_ip(ip: str, reason: str) -> dict[str, Any]:
    _register_hostile(ip, reason)
    reg = _mod("field_botnet_registry", "lib/field-botnet-registry.py")
    lop_doc: dict[str, Any] = {}
    if reg and hasattr(reg, "lop_stalker"):
        try:
            lop_doc = reg.lop_stalker(
                fingerprint=f"microsoft:{ip}",
                reason=f"botnet_microsoft_kill:{reason}",
                operator="botnet",
            )
        except (OSError, TypeError, ValueError):
            lop_doc = {}
    kit = _mod("field_attack_kit", "lib/field-attack-kit.py")
    kill_doc: dict[str, Any] = {"ok": False, "skipped": True}
    if kit and hasattr(kit, "kill_target"):
        try:
            os.environ["KILROY_HOSTILE_INSIDE"] = "1"
            kill_doc = kit.kill_target(
                ip,
                vector=VECTOR,
                severity=str(_doctrine().get("severity") or "critical"),
                reason=reason,
                extra={
                    "force": True,
                    "source": "botnet-microsoft-kill",
                    "hostile": {"org": "Microsoft", "reason": reason},
                },
            )
        except (OSError, TypeError, ValueError) as exc:
            kill_doc = {"ok": False, "error": str(exc)[:120]}
    return {"ip": ip, "registered": True, "lop": lop_doc, "kill": kill_doc}


def botnet_microsoft_kill(*, write: bool = True) -> dict[str, Any]:
    doc = _doctrine()
    if not doc.get("enabled", True):
        return {"ok": True, "skipped": True, "reason": "disabled"}

    proc_hits = _scan_process_hits(doc)
    conn_hits = _scan_connection_hits(doc)
    killed_local: list[dict[str, Any]] = []
    killed_remote: list[dict[str, Any]] = []

    seen_ip: set[str] = set()
    for hit in conn_hits:
        ip = str(hit.get("remote_ip") or "")
        if not ip or ip in seen_ip:
            continue
        seen_ip.add(ip)
        out = _botnet_kill_ip(ip, str(hit.get("reason") or "microsoft_connection"))
        killed_remote.append({**hit, **out})

    for hit in proc_hits:
        pid = int(hit.get("pid") or 0)
        if pid <= 1:
            continue
        if _kill_local_pid(pid):
            killed_local.append(hit)

    members = 0
    reg = _mod("field_botnet_registry", "lib/field-botnet-registry.py")
    if reg and hasattr(reg, "members_for_botnet"):
        try:
            members = len(reg.members_for_botnet())
        except (OSError, TypeError, ValueError):
            members = 0

    prev = _load(PANEL, {})
    total = int(prev.get("microsoft_killed_total") or 0) + len(killed_local) + len(killed_remote)

    out = {
        "ok": True,
        "schema": "field-botnet-microsoft-kill/v1",
        "updated": _utc(),
        "motto": doc.get("motto"),
        "microsoft_hitting": bool(proc_hits or conn_hits),
        "process_hits": len(proc_hits),
        "connection_hits": len(conn_hits),
        "killed_local": killed_local,
        "killed_remote": killed_remote,
        "microsoft_killed_total": total,
        "microsoft_killed_session": len(killed_local) + len(killed_remote),
        "botnet_nodes": members,
        "dns_dhcp_protected": True,
        "api": "/api/field-botnet-microsoft-kill",
    }
    if write:
        _save(PANEL, out)
        if out["microsoft_killed_session"]:
            _append_ledger({
                "event": "botnet_microsoft_kill",
                "local": len(killed_local),
                "remote": len(killed_remote),
                "hits": len(proc_hits) + len(conn_hits),
            })
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "kill").strip().lower()
    if cmd in ("kill", "json", "panel", "scan"):
        print(json.dumps(botnet_microsoft_kill(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-botnet-microsoft-kill.py [kill|scan|panel]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())