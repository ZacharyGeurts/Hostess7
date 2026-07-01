#!/usr/bin/env pythong
"""ZNetwork handler retire — retire only our field duplicates; never kill or harm the OS.

No sudo. User-space bypass alongside OS networking — link stays up, OS stack untouched.
"""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_MOD_CACHE: dict[str, Any] = {}


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

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
GUARD = STATE / "znetwork-handler-guard.json"
SUPERSEDES = STATE / "znetwork-supersedes.json"
RETIRE_LOG = STATE / "znetwork-handler-retire.jsonl"
CONNECTION = STATE / "znetwork-connection.json"
SCHEMA = "znetwork-handler-retire/v1"

# OS cmdline markers — never stop, never SIGKILL, never nmcli managed=no.
_OS_CMD_MARKERS = (
    "NetworkManager",
    "systemd-network",
    "nm-dispatcher",
    "nmcli",
    "wpa_supplicant",
    "/usr/sbin/",
    "/sbin/",
    "org.freedesktop.NetworkManager",
)


def _never_harm_os() -> bool:
    return os.environ.get("ZNETWORK_NEVER_HARM_OS", os.environ.get("NEXUS_NEVER_HARM_OS", "1")) != "0"


def _is_os_process(cmd: str) -> bool:
    low = cmd.lower()
    return any(m.lower() in low for m in _OS_CMD_MARKERS)


def _is_our_field_process(cmd: str) -> bool:
    """Only our vestigial field stacks may be stopped — never the host OS."""
    install = str(INSTALL.resolve())
    markers = (
        "/Latest/NEXUS-Shield/",
        "Latest/NEXUS-Shield/",
        install,
        "nexus-shield",
        "dns-service-takeover.py",
        "field-network-bridge.py",
        "connection-manager.py",
        "nexus-network-handler",
        "secure_net.sh",
    )
    return any(m in cmd for m in markers if m)


# Behavioral signatures — field-only; OS NetworkManager is never targeted.
_LEGACY_BEHAVIOR: list[dict[str, Any]] = [
    {
        "id": "legacy_nexus_shield_network",
        "label": "Legacy NEXUS-Shield network stack",
        "patterns": [
            r"/Latest/NEXUS-Shield/.*network",
            r"/Latest/NEXUS-Shield/lib/nexus-daemon",
            r"secure_net\.sh",
        ],
        "kind": "field_legacy",
    },
    {
        "id": "duplicate_znetwork_orchestrator",
        "label": "Stale ZNetwork orchestrator",
        "patterns": [r"znetwork-orchestrator\.py", r"[z]network.*policy"],
        "kind": "znetwork_stale",
        "exclude_self": True,
    },
    {
        "id": "competing_dns_takeover",
        "label": "Competing DNS takeover daemon",
        "patterns": [r"dns-service-takeover\.py\s+daemon", r"dns-service-takeover\.py\s+watch"],
        "kind": "dns_compete",
    },
    {
        "id": "legacy_connection_manager",
        "label": "Legacy field connection manager",
        "patterns": [
            r"connection-manager\.py",
            r"field-network-bridge\.py",
            r"nexus-network-handler",
        ],
        "kind": "connection_legacy",
    },
]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _append_log(row: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with RETIRE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _read_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def _list_pids() -> list[int]:
    try:
        return [int(p.name) for p in Path("/proc").iterdir() if p.name.isdigit()]
    except OSError:
        return []


def _match_patterns(cmd: str, patterns: list[str]) -> bool:
    import re

    for pat in patterns:
        if re.search(pat, cmd):
            return True
    return False


def _znetwork_bin() -> Path | None:
    env = os.environ.get("ZNETWORK_BIN", "").strip()
    if env and Path(env).is_file():
        return Path(env).resolve()
    sg = Path(os.environ.get("SG_ROOT", str(INSTALL.parent)))
    for candidate in (
        sg / "ZNetwork" / "build" / "znetwork",
        INSTALL.parent / "ZNetwork" / "build" / "znetwork",
        INSTALL / "bin" / "znetwork",
    ):
        if candidate.is_file():
            return candidate.resolve()
    return None


def _probe_connection_fallback() -> dict[str, Any]:
    """Minimal link snapshot when znetwork probe is slow — protection-only, no field bridges."""
    iface = ""
    ipv4 = ""
    gateway = ""
    try:
        proc = subprocess.run(
            ["ip", "-4", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=4,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            parts = proc.stdout.split()
            if "via" in parts:
                gateway = parts[parts.index("via") + 1]
            if "dev" in parts:
                iface = parts[parts.index("dev") + 1]
    except (subprocess.SubprocessError, OSError):
        pass
    if iface:
        try:
            proc = subprocess.run(
                ["ip", "-4", "-o", "addr", "show", "dev", iface],
                capture_output=True,
                text=True,
                timeout=4,
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    bits = line.split()
                    if len(bits) >= 4 and bits[2] == "inet":
                        ipv4 = bits[3].split("/", 1)[0]
                        break
        except (subprocess.SubprocessError, OSError):
            pass
    if not iface:
        return {"ok": False, "error": "fallback_no_iface"}
    conn = {
        "os": platform.system().lower(),
        "platform_backend": "kernel_route",
        "iface": iface,
        "iface_type": "unknown",
        "ipv4": ipv4,
        "gateway": gateway,
        "state": "connected" if ipv4 else "unknown",
        "is_default_route": True,
    }
    return {
        "ok": True,
        "connection": conn,
        "backend": {"id": "kernel_route", "label": "kernel_route", "running": True},
        "fallback": True,
    }


def _probe_connection() -> dict[str, Any]:
    bin_path = _znetwork_bin()
    if not bin_path:
        return _probe_connection_fallback()
    try:
        proc = subprocess.run(
            [str(bin_path), "probe", "--json"],
            capture_output=True,
            text=True,
            timeout=8,
            env={**os.environ, "SG_ROOT": str(INSTALL.parent)},
        )
        if proc.returncode == 0 and proc.stdout.strip():
            doc = json.loads(proc.stdout)
            return {"ok": True, "connection": doc.get("connection") or doc, "backend": doc.get("backend") or {}}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        pass
    return _probe_connection_fallback()


def detect_legacy_handlers(*, znetwork_active: bool = False) -> dict[str, Any]:
    """Find competing handlers by runtime behavior (cmdline), not install metadata."""
    import re

    my_pid = os.getpid()
    my_ppid = os.getppid()
    install_root = str(INSTALL.resolve())
    hits: list[dict[str, Any]] = []

    for pid in _list_pids():
        if pid in (my_pid, my_ppid, 1):
            continue
        cmd = _read_cmdline(pid)
        if not cmd:
            continue
        for spec in _LEGACY_BEHAVIOR:
            if spec.get("retire_only_when_znetwork_active") and not znetwork_active:
                continue
            if not _match_patterns(cmd, spec.get("patterns") or []):
                continue
            if spec.get("exclude_self") and install_root in cmd and "znetwork-handler-retire" not in cmd:
                # Keep our own orchestrator in this install tree.
                if "znetwork-orchestrator.py" in cmd or re.search(r"[z]network.*policy", cmd):
                    continue
            if install_root in cmd and spec["kind"] == "field_legacy":
                continue
            if _never_harm_os() and (_is_os_process(cmd) or not _is_our_field_process(cmd)):
                continue
            hits.append(
                {
                    "pid": pid,
                    "id": spec["id"],
                    "label": spec["label"],
                    "kind": spec["kind"],
                    "cmd": cmd[:280],
                }
            )

    # Stale socket from foreign install.
    sock = STATE / "znetwork-field.sock"
    stale_sock = False
    if sock.exists() and not GUARD.is_file():
        stale_sock = True

    return {
        "schema": SCHEMA,
        "ok": True,
        "os": platform.system().lower(),
        "handlers": hits,
        "stale_sock": stale_sock,
        "znetwork_active": znetwork_active,
        "checked_at": _now(),
    }


def _graceful_stop(pid: int, *, cmd: str = "", wait_sec: float = 2.5) -> dict[str, Any]:
    if _never_harm_os() and (_is_os_process(cmd) or (cmd and not _is_our_field_process(cmd))):
        return {"pid": pid, "ok": True, "skipped": True, "reason": "never_harm_os"}
    try:
        os.kill(pid, 0)
    except OSError as exc:
        return {"pid": pid, "ok": True, "already_gone": True, "detail": str(exc)}
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as exc:
        return {"pid": pid, "ok": False, "error": str(exc)}
    deadline = time.monotonic() + wait_sec
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
            time.sleep(0.15)
        except OSError:
            return {"pid": pid, "ok": True, "signal": "SIGTERM"}
    # Never SIGKILL — coexist with OS; our duplicate may keep running.
    return {"pid": pid, "ok": True, "signal": "SIGTERM", "still_running": True, "no_sigkill": True}


def retire_legacy_handlers(*, znetwork_active: bool = True) -> dict[str, Any]:
    """Gracefully stop our field duplicates only — OS networking is never harmed."""
    if _never_harm_os():
        guard_doc = {
            "schema": "znetwork-handler-guard/v1",
            "active": True,
            "no_sudo": True,
            "coexist_os": True,
            "never_harm_os": True,
            "bypass_not_replace": True,
            "retired_pids": [],
            "retired_at": _now(),
            "install_root": str(INSTALL.resolve()),
            "do_not_restart": [],
            "motto": "ZNetwork bypasses OS networking — host stack untouched, link preserved.",
        }
        _save(GUARD, guard_doc)
        return {
            "schema": SCHEMA,
            "ok": True,
            "skipped": True,
            "reason": "never_harm_os",
            "retired_count": 0,
            "results": [],
            "guard": str(GUARD),
            "at": _now(),
        }

    detected = detect_legacy_handlers(znetwork_active=znetwork_active)
    results: list[dict[str, Any]] = []
    retired_pids: list[int] = []

    for hit in detected.get("handlers") or []:
        pid = int(hit["pid"])
        if pid == os.getpid():
            continue
        outcome = _graceful_stop(pid, cmd=str(hit.get("cmd") or ""))
        outcome.update({"id": hit["id"], "label": hit["label"]})
        results.append(outcome)
        if outcome.get("ok"):
            retired_pids.append(pid)
        _append_log({"event": "retire", **outcome})

    guard_doc = {
        "schema": "znetwork-handler-guard/v1",
        "active": True,
        "no_sudo": True,
        "coexist_os": True,
        "never_harm_os": _never_harm_os(),
        "bypass_not_replace": True,
        "retired_pids": retired_pids,
        "retired_at": _now(),
        "install_root": str(INSTALL.resolve()),
        "do_not_restart": [
            "legacy_nexus_shield_network",
            "duplicate_znetwork_orchestrator",
            "competing_dns_takeover",
            "legacy_connection_manager",
        ],
        "motto": "Field duplicates retired — OS networking never killed or harmed.",
    }
    _save(GUARD, guard_doc)

    supersedes = {
        "schema": "znetwork-supersedes/v1",
        "updated": _now(),
        "native_backend_bypassed": True,
        "native_backend_superseded": False,
        "policy_owner": "znetwork",
        "link_preserved": True,
        "retired": results,
    }
    _save(SUPERSEDES, supersedes)

    if detected.get("stale_sock"):
        try:
            (STATE / "znetwork-field.sock").unlink(missing_ok=True)
        except OSError:
            pass

    ok = all(r.get("ok") for r in results) if results else True
    rep = {
        "schema": SCHEMA,
        "ok": ok,
        "retired_count": len(retired_pids),
        "results": results,
        "guard": str(GUARD),
        "at": _now(),
    }
    _append_log({"event": "retire_complete", **rep})
    return rep


def _try_nm_unmanaged(iface: str) -> dict[str, Any]:
    if _never_harm_os():
        return {"ok": False, "skipped": True, "reason": "never_harm_os"}
    if not iface or platform.system().lower() != "linux":
        return {"ok": False, "skipped": True, "reason": "not_linux_or_no_iface"}
    try:
        proc = subprocess.run(
            ["nmcli", "dev", "set", iface, "managed", "no"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        return {
            "ok": proc.returncode == 0,
            "iface": iface,
            "method": "nmcli_managed_no",
            "detail": (proc.stderr or proc.stdout or "")[:200],
            "no_sudo": True,
        }
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "iface": iface, "error": str(exc), "no_sudo": True}


def _takeover_mod() -> Any | None:
    return _mod(INSTALL / "lib" / "znetwork-os-takeover.py", "znetwork_os_takeover")


def _smart_inside_mod() -> Any | None:
    return _mod(INSTALL / "lib" / "znetwork-smart-inside.py", "znetwork_smart_inside")


def _smart_inside_active() -> bool:
    return os.environ.get("ZNETWORK_SMART_INSIDE", "1") != "0"


def _takeover_active() -> bool:
    if _smart_inside_active():
        return False
    if os.environ.get("ZNETWORK_PROTECTION_ONLY", "0") == "1":
        return False
    mode = os.environ.get("ZNETWORK_MODE", "REVIEW_ONLY")
    return mode == "ACTIVE" or os.environ.get("ZNETWORK_TAKEOVER", "0") == "1"


def replace_connection() -> dict[str, Any]:
    """Mirror live connection — smart inside owns policy; destructive handoff only when explicitly requested."""
    probe = _probe_connection()
    if not probe.get("ok"):
        return {"ok": False, "error": "probe_failed", "probe": probe}

    if _smart_inside_active():
        mod = _smart_inside_mod()
        if mod and hasattr(mod, "own_connection"):
            return mod.own_connection(probe=probe)

    conn = probe.get("connection") or {}
    backend = probe.get("backend") or {}
    iface = str(conn.get("iface") or "").strip()

    doc = {
        "schema": "znetwork-connection/v1",
        "updated": _now(),
        "policy_owner": "znetwork",
        "link_preserved": True,
        "connection": conn,
        "backend": backend,
        "supersedes": {
            "native_id": backend.get("id"),
            "native_label": backend.get("label"),
            "method": "bottom_up_handoff",
        },
    }
    _save(CONNECTION, doc)

    handoff: dict[str, Any]
    takeover_rep: dict[str, Any] | None = None
    if _takeover_active():
        mod = _takeover_mod()
        if mod and hasattr(mod, "takeover"):
            takeover_rep = mod.takeover(snapshot=probe)
            handoff = takeover_rep
            doc["coexist_os"] = False
            doc["native_backend_superseded"] = bool(takeover_rep.get("ok"))
            doc["verdict"] = "ZNETWORK_ACTIVE_HANDOFF" if takeover_rep.get("ok") else "ZNETWORK_HANDOFF_PARTIAL"
        else:
            handoff = _try_nm_unmanaged(iface)
            doc["coexist_os"] = True
            doc["verdict"] = "ZNETWORK_HANDOFF_FALLBACK"
    else:
        handoff = _try_nm_unmanaged(iface)
        doc["coexist_os"] = True
        doc["never_harm_os"] = _never_harm_os()
        doc["verdict"] = "ZNETWORK_BYPASS_ALONGSIDE"

    doc["handoff"] = handoff
    doc["no_sudo"] = not _takeover_active()
    _save(CONNECTION, doc)

    status_path = STATE / "znetwork-status.json"
    if status_path.is_file():
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            status = {}
    else:
        status = {}
    status["effective_mode"] = os.environ.get("ZNETWORK_MODE", "REVIEW_ONLY")
    status["policy_owner"] = "znetwork"
    status["native_backend_bypassed"] = True
    status["native_backend_superseded"] = bool(doc.get("native_backend_superseded"))
    status["coexist_os"] = bool(doc.get("coexist_os", True))
    status["link_preserved"] = True
    status["appears_connected"] = True
    status["connection_owner"] = doc
    status["updated"] = _now()
    if takeover_rep:
        status["takeover"] = takeover_rep
    _save(status_path, status)

    _append_log({"event": "replace_connection", "iface": iface, "handoff": handoff})
    ok = True if not _takeover_active() else bool((takeover_rep or {}).get("ok", False))
    return {"ok": ok, "connection": doc, "handoff": handoff}


def guard_blocks_restart(handler_id: str) -> bool:
    if not GUARD.is_file():
        return False
    try:
        doc = json.loads(GUARD.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not doc.get("active"):
        return False
    blocked = doc.get("do_not_restart") or []
    return handler_id in blocked


def posture() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "ok": True,
        "guard": _load_json(GUARD),
        "supersedes": _load_json(SUPERSEDES),
        "connection": _load_json(CONNECTION),
        "detected": detect_legacy_handlers(znetwork_active=GUARD.is_file()),
        "checked_at": _now(),
    }


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    handlers = {
        "json": posture,
        "detect": lambda: detect_legacy_handlers(znetwork_active=True),
        "retire": retire_legacy_handlers,
        "replace": replace_connection,
        "guard": lambda: {"ok": True, "guard": _load_json(GUARD)},
    }
    fn = handlers.get(cmd)
    if not fn:
        print(
            json.dumps({"error": "usage: znetwork-handler-retire.py [json|detect|retire|replace|guard]"}),
            file=sys.stderr,
        )
        return 2
    result = fn()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())