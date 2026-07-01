#!/usr/bin/env pythong
"""Root sovereignty — verify operator is you; invisible vigil on foreign root.

Binds the human operator (UID/username/home) on first seal. Unauthorized root
attacks are terminable with prejudice: SIGKILL + process-tree wipe on hostile
patterns. Legitimate systemd/sudo-from-you workflows pass untouched.
"""
from __future__ import annotations

import hashlib
import json
import os
import pwd
import re
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
COVENANT = STATE / "root-sovereign-covenant.json"
VIGIL_LOG = STATE / "root-sovereign-vigil.jsonl"
PANEL = STATE / "root-sovereign-panel.json"
KILL_LOG = STATE / "root-sovereign-kills.jsonl"
REPEAT_DB = STATE / "root-sovereign-repeat.json"
SCHEMA = "root-sovereign/v1"

# Legitimate root infrastructure — never terminate
SYSTEM_ROOT_COMMS: frozenset[str] = frozenset({
    "systemd", "systemd-journal", "systemd-logind", "systemd-udevd", "systemd-resolved",
    "sshd", "sudo", "su", "login", "agetty", "cron", "crond", "anacron",
    "polkitd", "udisksd", "ModemManager", "NetworkManager", "dbus-daemon",
    "aide", "fail2ban-server", "unattended-upgr", "apt", "apt-get", "dpkg",
    "fwupd", "thermald", "irqbalance", "rsyslogd", "snapd", "containerd",
    "dockerd", "kubelet", "nexus-daemon", "nexus_privacy_loop", "nexus_shadow_watch",
    "queen-world", "queen-browser", "queen-root-sovereign", "pythong",
    "accounts-daemon", "networkd-dispat", "power-profiles-", "switcheroo-cont",
    "touchegg", "cupsd", "cups-browsed", "bluetoothd", "wpa_supplicant",
    "avahi-daemon", "colord", "rtkit-daemon", "upowerd", "udisksd",
})

# CRITICAL — immediate SIGKILL with prejudice (injection / exfil / shells)
CRITICAL_CMD_RE = re.compile(
    r"(curl\s+[^\s|]+\s*\|\s*(ba)?sh|wget\s+[^\s]+\s*-O\s*/tmp/|"
    r"python3?\s+-c\s+['\"].*socket|perl\s+-e\s+.*socket|"
    r"nc\s+(-e|-c)\s|ncat\s+(-e|-c)\s|bash\s+-i\s*>/dev/tcp/|"
    r"/dev/tcp/|/dev/udp/|mkfifo\s+/tmp/|chmod\s\+s\s+/(bin|usr)|"
    r"authorized_keys|echo\s+.*>>\s*.*authorized_keys|"
    r"reverse.shell|meterpreter|linpeas|lse\.sh|pspy|chisel|ligolo|"
    r"base64\s+-d\s*<<|eval\s*\(\s*\$\(|/tmp/[a-z0-9_.-]+\.(sh|py|pl)\b)",
    re.I,
)

# HIGH — interactive root without operator chain (script kiddie shells)
HIGH_COMMS: frozenset[str] = frozenset({
    "bash", "sh", "dash", "zsh", "ksh", "fish",
    "python", "python3", "python3.12", "perl", "ruby", "php",
})

HOSTILE_COMMS: frozenset[str] = frozenset({
    "nc", "ncat", "netcat", "socat", "msfconsole", "sqlmap", "hydra", "nmap",
    "masscan", "nikto", "john", "hashcat", "aircrack-ng",
})

KERNEL_THREAD_COMMS: frozenset[str] = frozenset({
    "kthreadd", "ksoftirqd", "migration", "rcu_", "cpuhp", "watchdog",
    "kswapd", "kcompactd", "khugepaged", "writeback", "kblockd",
})


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _machine_fingerprint() -> str:
    parts: list[str] = []
    for p in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
        try:
            if p.is_file():
                parts.append(p.read_text(encoding="utf-8").strip())
                break
        except OSError:
            pass
    try:
        parts.append(os.uname().nodename)
    except OSError:
        pass
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def detect_operator() -> dict[str, Any]:
    """Prefer SUDO_USER, else login user, else owner of Queen tree."""
    sudo_user = os.environ.get("SUDO_USER", "").strip()
    login = os.environ.get("USER", "").strip() or os.environ.get("LOGNAME", "").strip()
    name = sudo_user or login
    if not name and QUEEN.is_dir():
        try:
            st = QUEEN.stat()
            name = pwd.getpwuid(st.st_uid).pw_name
        except (OSError, KeyError):
            pass
    if not name:
        name = "operator"
    try:
        pw = pwd.getpwnam(name)
        return {
            "username": pw.pw_name,
            "uid": pw.pw_uid,
            "gid": pw.pw_gid,
            "home": pw.pw_dir,
        }
    except KeyError:
        return {"username": name, "uid": os.getuid(), "gid": os.getgid(), "home": str(Path.home())}


def bind_operator(*, reason: str = "first_seal") -> dict[str, Any]:
    op = detect_operator()
    secret = hashlib.sha256(f"{op['uid']}:{op['username']}:{time.time_ns()}:{_machine_fingerprint()}".encode()).hexdigest()
    doc = {
        "schema": SCHEMA,
        "sealed": True,
        "sealed_at": _ts(),
        "reason": reason,
        "operator": op,
        "machine": _machine_fingerprint(),
        "session_secret": secret,
        "verdict": "USER_OK",
        "kill_policy": "prejudice",
        "motto": "Root is sovereign — unauthorized root terminated with prejudice",
    }
    _save(COVENANT, doc)
    _vigil("covenant_seal", operator=op["username"], uid=op["uid"])
    return doc


def covenant() -> dict[str, Any]:
    doc = _load(COVENANT, {})
    if doc.get("sealed"):
        return doc
    if os.environ.get("SG_ROOT_SOVEREIGN_AUTO_BIND", "1").strip().lower() not in ("0", "false", "no"):
        return bind_operator(reason="auto_bind")
    return {"schema": SCHEMA, "sealed": False, "verdict": "UNSEALED"}


def verify_covenant() -> dict[str, Any]:
    if os.environ.get("SG_ROOT_SOVEREIGN_OFF", "").strip().lower() in ("1", "true", "yes"):
        return {"ok": True, "verdict": "USER_OK", "override": True}
    doc = covenant()
    if not doc.get("sealed"):
        return {"ok": False, "verdict": "UNSEALED", "hint": "pythong lib/queen-root-sovereign.py bind"}
    op = doc.get("operator") or {}
    machine = doc.get("machine") or ""
    if machine and machine != _machine_fingerprint():
        return {"ok": False, "verdict": "MACHINE_MISMATCH", "expected": machine}
    return {"ok": True, "verdict": "USER_OK", "operator": op.get("username"), "uid": op.get("uid")}


def _proc_field(pid: int, field: str) -> str:
    try:
        return Path(f"/proc/{pid}/{field}").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _proc_comm(pid: int) -> str:
    c = _proc_field(pid, "comm")
    if c:
        return c
    try:
        return Path(f"/proc/{pid}/comm").read_bytes().split(b"\0", 1)[0].decode(errors="replace")
    except OSError:
        return "unknown"


def _proc_uid(pid: int) -> int:
    for line in _proc_field(pid, "status").splitlines():
        if line.startswith("Uid:"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    return int(parts[1])
                except ValueError:
                    break
    return -1


def _proc_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def _sudo_chain_ok(pid: int, sovereign_uid: int) -> bool:
    seen: set[int] = set()
    cur = pid
    for _ in range(32):
        if cur <= 1 or cur in seen:
            break
        seen.add(cur)
        comm = _proc_comm(cur)
        if comm in ("sudo", "su", "login", "sshd"):
            for line in _proc_field(cur, "environ").split("\0"):
                if line.startswith("SUDO_UID="):
                    try:
                        if int(line.split("=", 1)[1]) == sovereign_uid:
                            return True
                    except ValueError:
                        pass
            ppid_txt = _proc_field(cur, "status")
            for line in ppid_txt.splitlines():
                if line.startswith("PPid:"):
                    try:
                        cur = int(line.split()[1])
                    except (IndexError, ValueError):
                        cur = 0
                    break
            continue
        for line in _proc_field(cur, "status").splitlines():
            if line.startswith("PPid:"):
                try:
                    cur = int(line.split()[1])
                except (IndexError, ValueError):
                    cur = 0
                break
        else:
            break
    return False


def _kill_enabled() -> bool:
    return os.environ.get("SG_ROOT_SOVEREIGN_KILL", "1").strip().lower() not in ("0", "false", "no")


def _prejudice_enabled() -> bool:
    return os.environ.get("SG_ROOT_KILL_PREJUDICE", "1").strip().lower() not in ("0", "false", "no")


def _is_kernel_thread(pid: int, comm: str, cmd: str) -> bool:
    if pid <= 2:
        return True
    if comm.startswith(("kworker", "rcu_", "migration/", "cpuhp/", "irq/")):
        return True
    if any(comm.startswith(k) for k in KERNEL_THREAD_COMMS):
        return True
    if not cmd and comm not in HIGH_COMMS and comm not in HOSTILE_COMMS:
        if comm not in SYSTEM_ROOT_COMMS:
            for line in _proc_field(pid, "status").splitlines():
                if line.startswith("PPid:"):
                    try:
                        if int(line.split()[1]) == 2:
                            return True
                    except (IndexError, ValueError):
                        pass
                    break
    return False


def _threat_level(pid: int, comm: str, cmd: str, *, sovereign_uid: int) -> str:
    if _sudo_chain_ok(pid, sovereign_uid):
        return "ALLOW"
    if comm in SYSTEM_ROOT_COMMS or comm.endswith("-daemon"):
        return "ALLOW"
    if comm in ("g16", "g++16", "ninja", "cmake", "make", "cc1", "cc1plus", "as", "ld"):
        return "ALLOW"
    if CRITICAL_CMD_RE.search(cmd) or comm in HOSTILE_COMMS:
        return "CRITICAL"
    if comm in HIGH_COMMS:
        return "HIGH"
    if cmd and any(x in cmd.lower() for x in ("/tmp/", "/dev/shm/", "base64", "eval")):
        return "HIGH"
    return "LOW"


def _proc_children(pid: int) -> list[int]:
    kids: list[int] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        cpid = int(entry.name)
        for line in _proc_field(cpid, "status").splitlines():
            if line.startswith("PPid:"):
                try:
                    if int(line.split()[1]) == pid:
                        kids.append(cpid)
                except (IndexError, ValueError):
                    pass
                break
    return kids


def _terminate_with_prejudice(pid: int, *, reason: str, threat: str, comm: str, cmd: str) -> dict[str, Any]:
    """SIGKILL target + descendants — terminable with prejudice."""
    killed: list[int] = []
    errors: list[str] = []

    def _kill_tree(root: int) -> None:
        for child in _proc_children(root):
            _kill_tree(child)
        try:
            os.kill(root, signal.SIGKILL)
            killed.append(root)
        except ProcessLookupError:
            pass
        except OSError as exc:
            errors.append(f"{root}:{exc}")

    _kill_tree(pid)
    row = {
        "pid": pid,
        "comm": comm,
        "cmd": cmd[:240],
        "threat": threat,
        "reason": reason,
        "action": "SIGKILL_PREJUDICE",
        "killed": killed,
        "kill_count": len(killed),
    }
    _vigil("root_killed_prejudice", **row)
    KILL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with KILL_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": _ts(), **row}, ensure_ascii=False) + "\n")
    _bump_repeat_offender(comm, cmd)
    return row


def _bump_repeat_offender(comm: str, cmd: str) -> int:
    key = hashlib.sha256(f"{comm}|{cmd[:120]}".encode()).hexdigest()[:16]
    db = _load(REPEAT_DB, {"offenders": {}})
    offenders = db.setdefault("offenders", {})
    row = offenders.get(key, {"comm": comm, "hits": 0})
    row["hits"] = int(row.get("hits", 0)) + 1
    row["last"] = _ts()
    offenders[key] = row
    _save(REPEAT_DB, db)
    return int(row["hits"])


def _repeat_hits(comm: str, cmd: str) -> int:
    key = hashlib.sha256(f"{comm}|{cmd[:120]}".encode()).hexdigest()[:16]
    db = _load(REPEAT_DB, {"offenders": {}})
    return int((db.get("offenders") or {}).get(key, {}).get("hits", 0))


def _enforce_threat(pid: int, comm: str, cmd: str, threat: str) -> dict[str, Any] | None:
    if threat == "ALLOW":
        return None
    if not _kill_enabled():
        _vigil("foreign_root_logged", pid=pid, comm=comm, cmd=cmd[:240], threat=threat)
        return {"pid": pid, "action": "logged_only", "threat": threat}

    hits = _repeat_hits(comm, cmd)
    kill_now = threat == "CRITICAL"
    if threat == "HIGH" and _prejudice_enabled():
        kill_now = True
    if threat == "LOW" and hits >= 2 and _prejudice_enabled():
        kill_now = True

    if kill_now:
        return _terminate_with_prejudice(
            pid, reason="unauthorized_root_attack", threat=threat, comm=comm, cmd=cmd,
        )
    _vigil("foreign_root_warn", pid=pid, comm=comm, cmd=cmd[:240], threat=threat, hits=hits)
    return {"pid": pid, "action": "warn", "threat": threat, "hits": hits}


def audit_root_processes() -> dict[str, Any]:
    cov = covenant()
    op = cov.get("operator") or {}
    sovereign_uid = int(op.get("uid", -1))
    foreign: list[dict[str, Any]] = []
    allowed = 0
    killed = 0
    warned = 0
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if _proc_uid(pid) != 0:
            continue
        comm = _proc_comm(pid)
        cmd = _proc_cmdline(pid)
        if _is_kernel_thread(pid, comm, cmd):
            allowed += 1
            continue
        threat = _threat_level(pid, comm, cmd, sovereign_uid=sovereign_uid)
        if threat == "ALLOW":
            allowed += 1
            continue
        row: dict[str, Any] = {"pid": pid, "comm": comm, "cmd": cmd[:240], "threat": threat}
        foreign.append(row)
        action = _enforce_threat(pid, comm, cmd, threat)
        if action:
            row.update(action)
            if action.get("action") == "SIGKILL_PREJUDICE":
                killed += int(action.get("kill_count", 1))
            elif action.get("action") == "warn":
                warned += 1
    out = {
        "schema": "root-sovereign-audit/v1",
        "updated": _ts(),
        "operator": op.get("username"),
        "sovereign_uid": sovereign_uid,
        "kill_policy": "prejudice" if _prejudice_enabled() else "observe",
        "allowed_root": allowed,
        "foreign_root": len(foreign),
        "killed_prejudice": killed,
        "warned": warned,
        "samples": foreign[:12],
        "covenant_ok": verify_covenant().get("ok"),
    }
    _save(PANEL, out)
    return out


def _vigil(event: str, **fields: Any) -> None:
    row = {"ts": _ts(), "event": event, **fields}
    VIGIL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with VIGIL_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def is_authorized_operator() -> bool:
    if os.geteuid() != 0:
        cov = covenant()
        op = cov.get("operator") or {}
        return os.getuid() == int(op.get("uid", -999))
    return bool(verify_covenant().get("ok"))


def mandate_root(operation: str) -> dict[str, Any]:
    """Fail-closed when root is not sovereign operator."""
    if os.environ.get("SG_ROOT_SOVEREIGN_OFF", "").strip().lower() in ("1", "true", "yes"):
        return {"ok": True, "override": True, "operation": operation}
    v = verify_covenant()
    if not v.get("ok"):
        return {"ok": False, "error": "root_sovereign", "operation": operation, **v}
    if os.geteuid() == 0 and os.getuid() == 0:
        op = covenant().get("operator") or {}
        sudo_uid = os.environ.get("SUDO_UID", "")
        if sudo_uid and int(sudo_uid) == int(op.get("uid", -1)):
            return {"ok": True, "operation": operation, "via": "sudo"}
        if _sudo_chain_ok(os.getpid(), int(op.get("uid", -1))):
            return {"ok": True, "operation": operation, "via": "chain"}
        return {"ok": False, "error": "foreign_root", "operation": operation, **v}
    if os.getuid() == int((covenant().get("operator") or {}).get("uid", -1)):
        return {"ok": True, "operation": operation, "via": "operator_uid"}
    return {"ok": False, "error": "not_operator", "operation": operation, **v}


def guard_loop(*, interval: float = 8.0) -> None:
    covenant()
    _vigil("guard_armed", kill_policy="prejudice" if _prejudice_enabled() else "observe")
    while True:
        try:
            snap = audit_root_processes()
            if int(snap.get("killed_prejudice", 0)) > 0:
                interval = max(3.0, float(os.environ.get("SG_ROOT_GUARD_FAST_INTERVAL", "4")))
            else:
                interval = float(os.environ.get("SG_ROOT_GUARD_INTERVAL", "8"))
        except Exception as exc:
            _vigil("guard_error", error=str(exc))
        time.sleep(max(3.0, interval))


def status() -> dict[str, Any]:
    return {
        "schema": "root-sovereign-status/v1",
        "updated": _ts(),
        "covenant": covenant(),
        "verify": verify_covenant(),
        "panel": _load(PANEL, {}),
        "vigil_log": str(VIGIL_LOG),
        "kill_log": str(KILL_LOG),
        "kill_policy": "prejudice" if _prejudice_enabled() else "observe",
        "invisible": True,
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip()
    if cmd == "bind":
        print(json.dumps(bind_operator(), indent=2))
        return 0
    if cmd == "verify":
        print(json.dumps(verify_covenant(), indent=2))
        return 0 if verify_covenant().get("ok") else 1
    if cmd == "check-root":
        v = mandate_root("cli_check")
        print(json.dumps(v, indent=2))
        return 0 if v.get("ok") else 1
    if cmd == "audit":
        print(json.dumps(audit_root_processes(), indent=2))
        return 0
    if cmd == "guard":
        interval = float(os.environ.get("SG_ROOT_GUARD_INTERVAL", "8"))
        guard_loop(interval=interval)
        return 0
    if cmd == "terminate" and len(sys.argv) >= 3:
        try:
            tpid = int(sys.argv[2])
        except ValueError:
            print(json.dumps({"ok": False, "error": "bad_pid"}))
            return 1
        comm = _proc_comm(tpid)
        cmdline = _proc_cmdline(tpid)
        if _proc_uid(tpid) != 0:
            print(json.dumps({"ok": False, "error": "not_root", "pid": tpid}))
            return 1
        row = _terminate_with_prejudice(
            tpid, reason="operator_terminate", threat="MANUAL", comm=comm, cmd=cmdline,
        )
        print(json.dumps({"ok": True, **row}, indent=2))
        return 0
    if cmd == "json":
        print(json.dumps(status(), indent=2))
        return 0
    print(json.dumps(status(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())