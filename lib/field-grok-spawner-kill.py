#!/usr/bin/env python3
"""GrokSpawnKiller — field brain, no wait, kill interference, NEXUS C2 fused."""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PATTERNS = INSTALL / "data" / "field-grok-spawner-patterns.json"
DOGSHIT = INSTALL / "data" / "field-dogshit-purge.json"
PANEL = STATE / "field-grok-spawner-kill-panel.json"
LEDGER = STATE / "field-grok-spawner-kill-ledger.jsonl"
ME = os.getpid()
SERVICE = "field-grok-spawner-kill.service"
C2_PORT = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477") or "9477")
LOOPBACK = os.environ.get("NEXUS_LOOPBACK", "127.0.0.1")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _sudo_pw() -> str:
    return os.environ.get("HOSTESS7_SUDO_PW", "mememe")


def _is_shell(cmdline: str) -> bool:
    low = cmdline.lower()
    return any(x in low for x in ("bash", "/sh", "dash", "zsh", "pwsh", "cmd.exe"))


def _is_orphan(ppid: int) -> bool:
    return ppid == 1


def _grok_parent_pids(rows: list[tuple[int, int, str]]) -> set[int]:
    parents: set[int] = set()
    for pid, _, cmdline in rows:
        base = Path(cmdline.split()[0]).name if cmdline else ""
        if base == "grok" and "agent serve" not in cmdline and "dump_bash_state" not in cmdline:
            parents.add(pid)
    return parents


def _iter_proc() -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    if not sys.platform.startswith("linux"):
        return rows
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid <= 1 or pid == ME:
            continue
        try:
            stat = (entry / "stat").read_text(encoding="utf-8")
            rp = stat.rfind(")")
            ppid = int(stat[rp + 2 :].split()[1]) if rp >= 0 else 0
            raw = (entry / "cmdline").read_bytes()
            cmdline = raw.replace(b"\0", b" ").decode("utf-8", "replace").strip()
            rows.append((pid, ppid, cmdline))
        except (OSError, ValueError, IndexError):
            continue
    return rows


def _excluded(cmdline: str, excludes: list[str]) -> bool:
    return any(x in cmdline for x in excludes)


def _instakill(pids: list[int], *, sudo_pw: str) -> int:
    if not pids:
        return 0
    killed = 0
    need: list[int] = []
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
            killed += 1
        except PermissionError:
            need.append(pid)
        except ProcessLookupError:
            killed += 1
        except OSError:
            need.append(pid)
    if need:
        try:
            proc = subprocess.run(
                ["sudo", "-S", "kill", "-9", *[str(p) for p in need]],
                input=f"{sudo_pw}\n",
                capture_output=True,
                timeout=8,
                check=False,
            )
            if proc.returncode == 0:
                killed += len(need)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return killed


def _pattern_hits(
    pat: dict[str, Any],
    rows: list[tuple[int, int, str]],
    excludes: list[str],
) -> list[tuple[int, int, str]]:
    match = str(pat.get("match") or "")
    if not match:
        return []
    also = str(pat.get("also_match") or "")
    shell_only = bool(pat.get("shell_only"))
    hits: list[tuple[int, int, str]] = []
    for pid, ppid, cmdline in rows:
        if not cmdline or _excluded(cmdline, excludes):
            continue
        if match not in cmdline:
            continue
        if also and also not in cmdline:
            continue
        if shell_only and not _is_shell(cmdline):
            continue
        hits.append((pid, ppid, cmdline))
    return hits


def _effective_keep(pat: dict[str, Any]) -> int:
    keep = int(pat.get("keep", 0))
    pat_id = str(pat.get("id") or "")
    if pat_id.startswith("unsafe-panel") or pat_id.startswith("dogshit-"):
        doc = _load(DOGSHIT, {})
        if not _c2_port_up():
            return int(doc.get("panel_storms_keep_when_c2_down", 0))
        return int(doc.get("panel_storms_keep_when_c2_up", keep))
    return keep


def _targets_for_pattern(
    pat: dict[str, Any],
    rows: list[tuple[int, int, str]],
    excludes: list[str],
    grok_parents: set[int],
) -> list[int]:
    keep = _effective_keep(pat)
    hits = _pattern_hits(pat, rows, excludes)
    if not hits:
        return []
    hits.sort(key=lambda row: row[0])
    victims: list[int] = []
    if keep <= 0:
        victims = [pid for pid, ppid, _ in hits if ppid not in grok_parents]
    else:
        protected = {pid for pid, ppid, _ in hits if ppid in grok_parents}
        extras = hits[:-keep] if len(hits) > keep else []
        victims = [pid for pid, _, _ in extras if pid not in protected]
        for pid, ppid, _ in hits[-keep:]:
            if pid in protected:
                continue
            if _is_orphan(ppid):
                victims.append(pid)
    return victims


def _c2_port_up() -> bool:
    try:
        with socket.create_connection((LOOPBACK, C2_PORT), timeout=0.35):
            return True
    except OSError:
        return False


def _systemctl(*args: str, timeout: float = 20.0) -> dict[str, Any]:
    pw = _sudo_pw()
    for mode in (["sudo", "-n", *args], ["sudo", "-S", *args]):
        try:
            proc = subprocess.run(
                mode,
                input=(f"{pw}\n" if mode[1] == "-S" else None),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            if proc.returncode == 0:
                return {"ok": True, "stdout": (proc.stdout or "").strip()[:300]}
        except (OSError, subprocess.TimeoutExpired):
            continue
    return {"ok": False, "error": "systemctl_failed"}


def _run_py(rel: str, *args: str, timeout: float = 45.0) -> dict[str, Any]:
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
        for chunk in reversed(raw.splitlines() or [raw]):
            chunk = chunk.strip()
            if chunk.startswith("{"):
                doc = json.loads(chunk)
                if isinstance(doc, dict):
                    doc.setdefault("ok", proc.returncode == 0)
                    return doc
        return {"ok": proc.returncode == 0, "stdout": raw[:300], "rc": proc.returncode}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)[:160], "script": rel}


def _secure_stack() -> dict[str, Any]:
    """Prune unsafe panel storms; keep DNS/DHCP online — explicit services only."""
    return _run_py("lib/field-dns-dhcp-fix.py", "unsafe", timeout=60)


def _microsoft_botnet_kill() -> dict[str, Any]:
    """If Microsoft hits us — botnet kills them."""
    return _run_py("lib/field-botnet-microsoft-kill.py", "kill", timeout=45)


def purge_dogshit() -> dict[str, Any]:
    """Kill orphan panel storms and dogshit — explicit names only; DNS/DHCP protected."""
    doc = _load(DOGSHIT, {})
    protected = list(doc.get("protected") or [])
    excludes = list(_load(PATTERNS, {}).get("exclude_cmd") or []) + protected
    c2_up = _c2_port_up()
    keep_n = int(doc.get("panel_storms_keep_when_c2_up", 1) if c2_up else doc.get("panel_storms_keep_when_c2_down", 0))
    pw = _sudo_pw()
    killed: dict[str, list[int]] = {}
    rows = _iter_proc()

    for pattern in doc.get("panel_storms") or []:
        pids: list[int] = []
        for pid, _, cmdline in rows:
            if not cmdline or _excluded(cmdline, excludes):
                continue
            if pattern not in cmdline:
                continue
            pids.append(pid)
        pids.sort()
        victims = pids[:-keep_n] if keep_n > 0 and len(pids) > keep_n else (pids if keep_n <= 0 else [])
        for pid in victims:
            if _instakill([pid], sudo_pw=pw):
                killed.setdefault(str(pattern), []).append(pid)

    for pattern in doc.get("always_kill") or []:
        pids = []
        for pid, _, cmdline in rows:
            if not cmdline or _excluded(cmdline, excludes):
                continue
            if pattern in cmdline:
                pids.append(pid)
        for pid in pids:
            if _instakill([pid], sudo_pw=pw):
                killed.setdefault(f"always:{pattern}", []).append(pid)

    unsafe_units: list[str] = []
    for unit in doc.get("unsafe_systemd") or []:
        r = _systemctl("stop", str(unit), timeout=10)
        if r.get("ok"):
            unsafe_units.append(str(unit))

    sweep = instakill(write=True)
    return {
        "ok": True,
        "schema": "field-dogshit-purge/v1",
        "c2_up": c2_up,
        "keep_per_storm": keep_n,
        "killed": killed,
        "killed_total": sum(len(v) for v in killed.values()),
        "unsafe_units_stopped": unsafe_units,
        "slain_total": sweep.get("slain_total", 0),
        "motto": doc.get("motto"),
    }


def stack_load(*, wait_c2: bool = True) -> dict[str, Any]:
    """Fuse NEXUS C2 + field stack — direct systemd, field brain, no planetary glob."""
    secure = _secure_stack()
    microsoft = _microsoft_botnet_kill()
    early_sh = INSTALL / "scripts" / "nexus-field-early-boot.sh"
    early = {"ok": False, "skipped": not early_sh.is_file()}
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

    enable = _systemctl("enable", "nexus-field-early.service", "nexus-genius.service", timeout=25)
    early_restart = _systemctl("restart", "nexus-field-early.service", timeout=35)
    genius_restart = _systemctl("restart", "nexus-genius.service", timeout=45)

    c2_up = _c2_port_up()
    if wait_c2 and not c2_up:
        for _ in range(16):
            time.sleep(0.125)
            if _c2_port_up():
                c2_up = True
                break

    brain = _run_py("lib/field-brain-panel.py", "json", timeout=30)
    meld = _run_py("lib/field-sovereign-stack-meld.py", "verify", timeout=40)
    services = {
        "nexus_field_early": _systemctl("is-active", "nexus-field-early.service", timeout=8).get("stdout") == "active",
        "nexus_genius": _systemctl("is-active", "nexus-genius.service", timeout=8).get("stdout") == "active",
        "grok_spawner_kill": _service_active(),
    }
    dns_fix = _run_py("lib/field-dns-dhcp-fix.py", "dns", timeout=90)
    return {
        "ok": c2_up or services.get("nexus_genius") or bool(dns_fix.get("healthy")),
        "schema": "grok-spawn-killer-stack/v1",
        "secure": secure,
        "microsoft_botnet": microsoft,
        "dns_healthy": bool(dns_fix.get("healthy")),
        "nexus_c2_port_up": c2_up,
        "nexus_c2_port": C2_PORT,
        "early_boot": early,
        "systemd": {"enable": enable.get("ok"), "early_restart": early_restart.get("ok"), "genius_restart": genius_restart.get("ok")},
        "services": services,
        "field_brain": brain if brain.get("schema") else {"ok": False, "lane": "field-brain"},
        "stack_sealed": bool(meld.get("sealed") or meld.get("ok")),
        "motto": "NEXUS C2 + field brain fused — no waiting",
    }


def _service_active() -> bool:
    try:
        proc = subprocess.run(
            ["systemctl", "is-active", SERVICE],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return (proc.stdout or "").strip() == "active"
    except (OSError, subprocess.TimeoutExpired):
        return False


def slain_from_ledger() -> int:
    total = 0
    if not LEDGER.is_file():
        return total
    try:
        for line in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            cooked = row.get("cooked") or {}
            if isinstance(cooked, dict):
                total += sum(int(v) for v in cooked.values())
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        pass
    return total


def install_service() -> dict[str, Any]:
    script = INSTALL / "packaging/grok-spawner-kill/linux/install.sh"
    if not script.is_file():
        return {"ok": False, "error": "install_script_missing", "path": str(script)}
    pw = _sudo_pw()
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "HOSTESS7_SUDO_PW": pw,
    }
    stack = stack_load(wait_c2=True)
    try:
        proc = subprocess.run(
            ["bash", str(script)],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
            check=False,
        )
        sweep = instakill(write=True)
        return {
            "ok": proc.returncode == 0 and _service_active(),
            "rc": proc.returncode,
            "service_active": _service_active(),
            "stdout": (proc.stdout or "").strip()[-400:],
            "stderr": (proc.stderr or "").strip()[-200:],
            "slain_total": sweep.get("slain_total", 0),
            "slain_session": sweep.get("slain_session", 0),
            "product": "GrokSpawnKiller",
            "never_sleeps": True,
            "no_wait": True,
            "field_brain": stack.get("field_brain"),
            "nexus_c2_port_up": stack.get("nexus_c2_port_up") or _c2_port_up(),
            "stack": stack,
            "motto": "Field brain — no waiting — interference killed",
            "pages_url": "https://zacharygeurts.github.io/Hostess7/grok-spawn-killer/",
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)[:160], "stack": stack}


def panel(*, write: bool = False) -> dict[str, Any]:
    doc = _load(PATTERNS, {})
    if write or not PANEL.is_file():
        out = instakill(write=True)
    else:
        out = dict(_load(PANEL, {}))
        out["service_active"] = _service_active()
        if "slain_total" not in out:
            out["slain_total"] = slain_from_ledger()
    brain = _run_py("lib/field-brain-panel.py", "json", timeout=20)
    ms = _load(STATE / "field-botnet-microsoft-kill-panel.json", {})
    out.update({
        "ok": True,
        "schema": "field-grok-spawner-kill/v1",
        "product": doc.get("product", "GrokSpawnKiller"),
        "never_sleeps": bool(doc.get("never_sleeps", True)),
        "no_wait": bool(doc.get("no_wait", True)),
        "field_brain": bool(doc.get("field_brain", True)),
        "motto": doc.get("motto", out.get("motto")),
        "slain_total": int(out.get("slain_total") or slain_from_ledger()),
        "slain_session": int(out.get("slain_session") or out.get("cooked_total") or 0),
        "service_active": _service_active(),
        "nexus_c2_port_up": _c2_port_up(),
        "nexus_c2_port": C2_PORT,
        "field_brain_panel": brain if brain.get("schema") else {"ok": True, "lane": "field-brain", "pages": False},
        "microsoft_killed_total": int(ms.get("microsoft_killed_total") or 0),
        "microsoft_hitting": bool(ms.get("microsoft_hitting")),
        "pages_url": "https://zacharygeurts.github.io/Hostess7/grok-spawn-killer/",
        "install": f"bash {INSTALL}/packaging/grok-spawner-kill/linux/install.sh",
        "api": "/api/field-grok-spawner-kill",
    })
    return out


def instakill(*, write: bool = True) -> dict[str, Any]:
    doc = _load(PATTERNS, {})
    patterns = doc.get("patterns") or []
    excludes = [str(x) for x in (doc.get("exclude_cmd") or [])]
    pw = _sudo_pw()
    rows = _iter_proc()
    grok_parents = _grok_parent_pids(rows)
    cooked: dict[str, int] = {}
    victims: list[dict[str, Any]] = []

    for pat in patterns:
        if not isinstance(pat, dict):
            continue
        pids = _targets_for_pattern(pat, rows, excludes, grok_parents)
        if not pids:
            continue
        n = _instakill(pids, sudo_pw=pw)
        key = str(pat.get("id") or pat.get("match", ""))[:36]
        cooked[key] = n
        victims.append({"id": pat.get("id"), "pids": pids, "killed": n, "reason": pat.get("reason")})

    remaining: dict[str, int] = {}
    rows_after = _iter_proc()
    for pat in patterns[:6]:
        if not isinstance(pat, dict):
            continue
        match = str(pat.get("match") or "")
        if not match:
            continue
        remaining[str(pat.get("id") or match)[:28]] = sum(1 for _, _, c in rows_after if match in c)

    prev = _load(PANEL, {})
    session_kills = sum(cooked.values())
    slain_total = int(prev.get("slain_total") or 0) + session_kills

    out = {
        "ok": True,
        "schema": "field-grok-spawner-kill/v1",
        "product": doc.get("product", "GrokSpawnKiller"),
        "updated": _utc(),
        "motto": doc.get("motto", "Grok never Sleeps — instakill spawners, sudo mememe, zero grace."),
        "never_sleeps": bool(doc.get("never_sleeps", True)),
        "slain_total": slain_total,
        "slain_session": session_kills,
        "service_active": _service_active(),
        "cooked": cooked,
        "cooked_total": session_kills,
        "victims": victims[:24],
        "remaining": remaining,
        "api": "/api/field-grok-spawner-kill",
    }
    if write:
        STATE.mkdir(parents=True, exist_ok=True)
        tmp = PANEL.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(PANEL)
        try:
            with LEDGER.open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {"ts": _utc(), "cooked": cooked, "remaining": remaining},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except OSError:
            pass
    return out


def serve() -> int:
    doc = _load(PATTERNS, {})
    no_wait = bool(doc.get("no_wait", True))
    base_ms = 25 if doc.get("never_sleeps") else 250
    interval_ms = max(0, int(doc.get("interval_ms", base_ms)))
    if no_wait:
        interval_ms = min(interval_ms, 25)
    sweep_n = 0
    while True:
        try:
            instakill(write=True)
            sweep_n += 1
            if sweep_n % 40 == 0:
                _microsoft_botnet_kill()
        except Exception as exc:
            err = {"ok": False, "error": str(exc)[:200], "ts": _utc()}
            try:
                tmp = PANEL.with_suffix(".tmp")
                tmp.write_text(json.dumps(err, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                tmp.replace(PANEL)
            except OSError:
                pass
        if interval_ms > 0:
            time.sleep(interval_ms / 1000.0)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "instakill").strip().lower()
    if cmd in ("instakill", "kill", "cook", "json", "once"):
        print(json.dumps(instakill(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("panel", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "install":
        print(json.dumps(install_service(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("stack", "c2", "nexus"):
        print(json.dumps(stack_load(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("purge", "dogshit", "clean"):
        print(json.dumps(purge_dogshit(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("serve", "watch", "daemon"):
        serve()
        return 0
    print(
        json.dumps(
            {"usage": "field-grok-spawner-kill.py [instakill|panel|install|stack|purge|serve]"},
            ensure_ascii=False,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())