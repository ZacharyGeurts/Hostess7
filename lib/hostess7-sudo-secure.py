#!/usr/bin/env pythong
"""Hostess7 secure sudo — scoped elevation for humans and AI communique lane."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-sudo-doctrine.json"
PANEL = STATE / "hostess7-sudo-secure-panel.json"


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


def _expand(path: str) -> Path:
    return Path(path.replace("~", str(Path.home()))).expanduser()


def _load_sudo_pw() -> str:
    for key in ("HOSTESS7_SUDO_PW",):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    for rel in (
        os.environ.get("HOSTESS7_SUDO_ENV", "~/.config/ammo-shield/sudo.env"),
        "~/.config/ammo-shield/ai-sudo.env",
    ):
        p = _expand(rel)
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == "HOSTESS7_SUDO_PW":
                return v.strip().strip("'\"")
    return ""


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _sudo_probe(*, pw: str) -> dict[str, Any]:
    try:
        proc = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True, timeout=8, check=False)
        if proc.returncode == 0:
            return {"ok": True, "mode": "nopasswd"}
    except (OSError, subprocess.TimeoutExpired):
        pass
    if not pw:
        return {"ok": False, "mode": "password", "error": "no_password_configured"}
    try:
        proc = subprocess.run(
            ["sudo", "-S", "-v"],
            input=f"{pw}\n",
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
        return {"ok": proc.returncode == 0, "mode": "password"}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "mode": "password", "error": str(exc)[:120]}


def _action_argv(action: str, spec: dict[str, Any]) -> list[str] | None:
    if spec.get("systemctl"):
        return ["systemctl", *[str(x) for x in spec["systemctl"]]]
    script = spec.get("script")
    if script:
        path = INSTALL / str(script)
        if not path.is_file():
            return None
        argv = ["bash", str(path)]
        argv.extend(str(a) for a in (spec.get("args") or []))
        return argv
    module = spec.get("module")
    if module:
        path = INSTALL / str(module)
        if not path.is_file():
            return None
        py = os.environ.get("PYTHON", "python3")
        argv = [py, str(path)]
        argv.extend(str(a) for a in (spec.get("args") or []))
        return argv
    return None


def _run_elevated(argv: list[str], *, pw: str, timeout: int = 300) -> dict[str, Any]:
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE), "AML_BUILD": "0"}
    for attempt, mode in (("nopasswd", ["sudo", "-n", *argv]), ("password", ["sudo", "-S", *argv])):
        try:
            proc = subprocess.run(
                mode,
                input=(f"{pw}\n" if mode[1] == "-S" and pw else None),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                check=False,
            )
            if proc.returncode == 0 or attempt == "password":
                return {
                    "ok": proc.returncode == 0,
                    "mode": attempt,
                    "rc": proc.returncode,
                    "stdout": (proc.stdout or "")[-4000:],
                    "stderr": (proc.stderr or "")[-1200:],
                }
        except (OSError, subprocess.TimeoutExpired) as exc:
            if attempt == "password":
                return {"ok": False, "mode": attempt, "error": str(exc)[:200]}
    return {"ok": False, "error": "elevated_run_failed"}


def verify() -> dict[str, Any]:
    doc = doctrine()
    pw = _load_sudo_pw()
    probe = _sudo_probe(pw=pw)
    actions = doc.get("actions") or {}
    rows: list[dict[str, Any]] = []
    for name, spec in actions.items():
        if not isinstance(spec, dict):
            continue
        if spec.get("internal") or name == "destroy-untrue":
            present = True
        else:
            present = _action_argv(name, spec) is not None
        rows.append({
            "action": name,
            "ai_safe": bool(spec.get("ai_safe")),
            "present": present,
            "role": spec.get("role"),
        })
    return {
        "schema": "hostess7-sudo-secure/v1",
        "updated": _utc(),
        "ok": probe.get("ok"),
        "sudo_mode": probe.get("mode"),
        "password_configured": bool(pw),
        "human_lane": "any_human_in_sudo_group",
        "ai_lane": "hostess7-ai-communique",
        "wrapper": (doc.get("policy") or {}).get("nopasswd_wrapper"),
        "actions": rows,
        "policy": doc.get("policy"),
    }


def destroy_untrue(*, timeout: int = 300) -> dict[str, Any]:
    """Promote Truth DNS + DHCP, block foreign resolvers, eradicate drift."""
    py = os.environ.get("PYTHON", "python3")
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE), "AML_BUILD": "0"}
    steps: list[dict[str, Any]] = []

    for label, argv in (
        ("dns_primary", ["bash", str(INSTALL / "scripts/legacy-connect-primary.sh")]),
        ("dns_table_clean", ["bash", str(INSTALL / "scripts/dns-clean-tables.sh"), "clean"]),
        ("drift_scan_apply", [py, str(INSTALL / "lib/field-dns-drift-threat.py"), "scan", "--apply"]),
    ):
        hit = _run_elevated(argv, pw=_load_sudo_pw(), timeout=timeout)
        steps.append({"step": label, **hit})

    takeover = {}
    try:
        proc = subprocess.run(
            [py, str(INSTALL / "lib/dns-service-takeover.py"), "evaluate"],
            capture_output=True, text=True, timeout=30, env=env, check=False,
        )
        if proc.stdout.strip().startswith("{"):
            takeover = json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass

    out = {
        "schema": "hostess7-sudo-secure-destroy-untrue/v1",
        "updated": _utc(),
        "action": "destroy-untrue",
        "ok": all(s.get("ok") for s in steps)
        and takeover.get("phase") == "primary"
        and takeover.get("permissions", {}).get("enforce_resolv", False),
        "steps": steps,
        "takeover_phase": takeover.get("phase"),
        "permissions": takeover.get("permissions"),
    }
    _save(PANEL, {"last_run": out, "verify": verify()})
    return out


def run_action(action: str, *, timeout: int = 300) -> dict[str, Any]:
    if action == "destroy-untrue":
        return destroy_untrue(timeout=timeout)
    doc = doctrine()
    spec = (doc.get("actions") or {}).get(action)
    if not isinstance(spec, dict):
        return {"ok": False, "error": "unknown_action", "action": action}
    if spec.get("internal"):
        return {"ok": False, "error": "internal_action_use_destroy_untrue", "action": action}
    argv = _action_argv(action, spec)
    if not argv:
        return {"ok": False, "error": "action_script_missing", "action": action}
    pw = _load_sudo_pw()
    result = _run_elevated(argv, pw=pw, timeout=timeout)
    out = {
        "schema": "hostess7-sudo-secure-run/v1",
        "updated": _utc(),
        "action": action,
        "role": spec.get("role"),
        "ai_safe": bool(spec.get("ai_safe")),
        **result,
    }
    _save(PANEL, {"last_run": out, "verify": verify()})
    return out


def panel() -> dict[str, Any]:
    doc = verify()
    _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "panel"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "run" and len(sys.argv) > 2:
        print(json.dumps(run_action(sys.argv[2].strip()), ensure_ascii=False, indent=2))
        return 0
    if cmd == "destroy-untrue":
        print(json.dumps(destroy_untrue(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-sudo-secure.py [json|verify|run ACTION|destroy-untrue]",
        "actions": [k for k, v in (doctrine().get("actions") or {}).items() if not (v or {}).get("internal")],
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())