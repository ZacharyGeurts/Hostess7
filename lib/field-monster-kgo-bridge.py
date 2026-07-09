#!/usr/bin/env python3
"""Monster ↔ Kill-Grok-Orphans bridge — dead Grok/GitHub orphans + software fix heuristics."""
from __future__ import annotations

import json
import os
import signal
import socket
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
KGO_PATTERNS = INSTALL / "Kill-Grok-Orphans" / "data" / "kgo-patterns.json"
MONSTER_EXT = INSTALL / "data" / "field-monster-kgo-patterns.json"
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _is_orphan_ppid(ppid: int) -> bool:
    if sys.platform == "win32":
        return ppid in (0, 4)
    return ppid == 1


def _iter_proc() -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    my_pid = os.getpid()
    try:
        import psutil  # type: ignore
        for proc in psutil.process_iter(["pid", "ppid", "cmdline", "name"]):
            try:
                info = proc.info
                pid = int(info["pid"])
                ppid = int(info["ppid"] or 0)
                parts = info.get("cmdline") or []
                if not parts and info.get("name"):
                    parts = [info["name"]]
                cmdline = " ".join(parts)
                rows.append((pid, ppid, cmdline))
            except Exception:
                continue
        return rows
    except ImportError:
        pass
    if not sys.platform.startswith("linux"):
        return rows
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid <= 1 or pid == my_pid:
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


def _is_shell(cmdline: str) -> bool:
    low = cmdline.lower()
    return any(x in low for x in ("bash", "/sh", "dash", "zsh", "pwsh", "cmd.exe"))


def load_patterns() -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    for path in (KGO_PATTERNS, MONSTER_EXT):
        doc = _load(path, {})
        for p in doc.get("patterns") or []:
            if isinstance(p, dict) and p.get("match"):
                patterns.append(p)
    return patterns


def scan_orphans(*, dry_run: bool = False) -> dict[str, Any]:
    patterns = load_patterns()
    targets: list[dict[str, Any]] = []
    for pid, ppid, cmdline in _iter_proc():
        if not _is_orphan_ppid(ppid) or not cmdline:
            continue
        for pat in patterns:
            match = str(pat.get("match") or "")
            if match not in cmdline:
                continue
            if pat.get("shell_only") and not _is_shell(cmdline):
                continue
            targets.append({
                "pid": pid,
                "ppid": ppid,
                "cmd": cmdline[:240],
                "pattern_id": pat.get("id"),
                "reason": pat.get("reason") or pat.get("id"),
                "github_related": bool(pat.get("github_related") or "github" in match.lower() or "git" in match.lower()),
            })
            break
    return {"ok": True, "updated": _utc(), "count": len(targets), "orphans": targets, "dry_run": dry_run}


def kill_orphans(*, pids: list[int] | None = None, dry_run: bool = False) -> dict[str, Any]:
    scan = scan_orphans(dry_run=True)
    victims = scan.get("orphans") or []
    if pids:
        want = {int(p) for p in pids}
        victims = [v for v in victims if int(v["pid"]) in want]
    killed: list[dict[str, Any]] = []
    for v in victims:
        pid = int(v["pid"])
        if dry_run:
            killed.append({**v, "killed": False, "dry_run": True})
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            killed.append({**v, "signal": "SIGTERM", "killed": True})
        except OSError as exc:
            killed.append({**v, "killed": False, "error": str(exc)})
    return {"ok": True, "killed": killed, "count": len(killed)}


def _probe_url(url: str, timeout: float = 3.5) -> dict[str, Any]:
    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "MonsterFix/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return {"ok": True, "status": resp.status, "url": url}
    except urllib.error.HTTPError as exc:
        return {"ok": exc.code < 500, "status": exc.code, "url": url}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)[:120], "url": url}


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.4):
            return True
    except OSError:
        return False


def software_fixes() -> dict[str, Any]:
    """Smart repair suggestions for every field software surface."""
    fixes: list[dict[str, Any]] = []
    services = [
        ("nexus_panel", "NEXUS Panel", 9477, "/api/status", "stack_restart"),
        ("queen_browser", "Queen Browser", 9481, "/api/queen-field-sanity", "queen_start"),
        ("final_eye", "Final Eye", 9479, "/ops", "final_eye_start"),
        ("ammocode", "AmmoCode", 9478, "/", "ammocode_start"),
    ]
    for sid, name, port, path, route in services:
        up = _port_open(port)
        if not up:
            fixes.append({
                "id": f"service_down_{sid}",
                "severity": "high",
                "software": name,
                "problem": f"{name} not listening on :{port}",
                "fix": f"Restart via AmmoLang — lib/ammolang-run.sh {route}",
                "ammolang_route": route,
                "action": "ammolang_restart",
                "meta": {"port": port, "service_id": sid},
            })

    gh = _probe_url("https://github.com/ZacharyGeurts/Hostess7")
    pages = _probe_url("https://zacharygeurts.github.io/Hostess7/")
    if not gh.get("ok") and pages.get("ok"):
        fixes.append({
            "id": "github_to_pages_mirror",
            "severity": "medium",
            "software": "GitHub for everyone",
            "problem": "github.com unreachable — use witnessed Pages mirror",
            "fix": "Route links through endpoint registry canonical URL",
            "ammolang_route": "github_everyone_pulse",
            "action": "use_pages_mirror",
            "meta": {"pages_url": "https://zacharygeurts.github.io/Hostess7/"},
        })

    orphans = scan_orphans(dry_run=True)
    if orphans.get("count", 0) > 0:
        fixes.append({
            "id": "grok_orphans",
            "severity": "high",
            "software": "Kill-Grok-Orphans",
            "problem": f"{orphans['count']} dead Grok/GitHub orphan process(es)",
            "fix": "Monster → Kill orphans (KGO patterns)",
            "ammolang_route": "kgo_sweep",
            "action": "kill_orphans",
            "meta": {"orphans": orphans.get("orphans", [])[:12]},
        })

    hang_py = INSTALL / "lib" / "field-monster-shell.py"
    if hang_py.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(hang_py), "hang-pending"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            hang_doc = json.loads(proc.stdout or "{}")
            pending = hang_doc.get("pending") or []
            if pending:
                fixes.append({
                    "id": "monster_hang_queue",
                    "severity": "medium",
                    "software": "Monster shell",
                    "problem": f"{len(pending)} hung program(s) awaiting operator",
                    "fix": "Open Monster Tasks tab — wait or nuke",
                    "action": "review_hang_queue",
                    "meta": {"pending": pending[:8]},
                })
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass

    reg_py = INSTALL / "lib" / "field-endpoint-registry.py"
    if reg_py.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(reg_py), "verify"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            verify = json.loads(proc.stdout or "{}")
            if not verify.get("ok"):
                fixes.append({
                    "id": "endpoint_registry_chain",
                    "severity": "critical",
                    "software": "Endpoint registry",
                    "problem": "Pages movement hash chain broken",
                    "fix": "Re-seed registry from sovereign seed — field-endpoint-registry.py seed --force",
                    "ammolang_route": "endpoint_registry_repair",
                    "action": "registry_verify_fail",
                    "meta": verify,
                })
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass

    return {"ok": True, "updated": _utc(), "fix_count": len(fixes), "fixes": fixes}


def apply_fix(fix_id: str) -> dict[str, Any]:
    fixes = software_fixes().get("fixes") or []
    row = next((f for f in fixes if f.get("id") == fix_id), None)
    if not row:
        return {"ok": False, "error": "unknown_fix", "fix_id": fix_id}
    action = str(row.get("action") or "")
    if action == "kill_orphans":
        return kill_orphans(dry_run=False)
    if action == "ammolang_restart":
        route = str(row.get("ammolang_route") or "assist")
        aml = INSTALL / "lib" / "ammolang-run.sh"
        try:
            proc = subprocess.run(
                ["bash", str(aml), route],
                cwd=str(INSTALL),
                capture_output=True,
                text=True,
                timeout=120,
            )
            return {
                "ok": proc.returncode == 0,
                "fix_id": fix_id,
                "route": route,
                "stdout": (proc.stdout or "")[-2000:],
                "stderr": (proc.stderr or "")[-800:],
                "rc": proc.returncode,
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "error": str(exc), "fix_id": fix_id}
    if action == "use_pages_mirror":
        return {"ok": True, "fix_id": fix_id, "pages_url": row.get("meta", {}).get("pages_url")}
    return {"ok": True, "fix_id": fix_id, "action": action, "note": "manual_review"}


def task_manager_panel() -> dict[str, Any]:
    hang: dict[str, Any] = {}
    shell_py = INSTALL / "lib" / "field-monster-shell.py"
    if shell_py.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(shell_py), "hang-pending"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            hang = json.loads(proc.stdout or "{}")
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            hang = {}
    orphans = scan_orphans(dry_run=True)
    fixes = software_fixes()
    aml_tasks: list[dict[str, Any]] = []
    build_py = INSTALL / "lib" / "field-ammolang-build.py"
    if build_py.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(build_py), "tasks"],
                capture_output=True,
                text=True,
                timeout=20,
                cwd=str(INSTALL),
            )
            doc = json.loads(proc.stdout or "{}")
            aml_tasks = list(doc.get("tasks") or doc.get("routes") or [])[:24]
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
    return {
        "ok": True,
        "schema": "field-monster-tasks/v1",
        "updated": _utc(),
        "hang_pending": hang.get("pending") or [],
        "orphans": orphans.get("orphans") or [],
        "orphan_count": orphans.get("count", 0),
        "fixes": fixes.get("fixes") or [],
        "ammolang_tasks": aml_tasks,
        "kgo_version": _load(KGO_PATTERNS, {}).get("version"),
        "motto": "Monster task manager — KGO orphans · AmmoLang fixes · every software",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").lower()
    if cmd in ("panel", "tasks", "json"):
        print(json.dumps(task_manager_panel(), indent=2))
        return 0
    if cmd == "orphans":
        print(json.dumps(scan_orphans(), indent=2))
        return 0
    if cmd == "fixes":
        print(json.dumps(software_fixes(), indent=2))
        return 0
    if cmd == "kill" and "--dry" in sys.argv:
        print(json.dumps(kill_orphans(dry_run=True), indent=2))
        return 0
    if cmd == "kill":
        print(json.dumps(kill_orphans(dry_run=False), indent=2))
        return 0
    if cmd == "apply" and len(sys.argv) > 2:
        print(json.dumps(apply_fix(sys.argv[2]), indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["panel", "orphans", "fixes", "kill", "apply FIX_ID"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())