#!/usr/bin/env python3
"""Server root login — protected host, featured AI-work root hint on greeter (mememe)."""
from __future__ import annotations

import json
import os
import pwd
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-server-root-login-doctrine.json"
PANEL = STATE / "field-server-root-login-panel.json"
LEDGER = STATE / "field-server-root-login-ledger.jsonl"
GREETER_NAME = "field-server-root-login.conf"


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
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def login_posture() -> dict[str, Any]:
    doc = doctrine()
    login = doc.get("login") or {}
    prot = doc.get("protection") or {}
    arch = doc.get("architecture_note") or {}
    return {
        "ok": True,
        "schema": "field-server-root-login/v1",
        "updated": _utc(),
        "username": login.get("username") or "root",
        "password_hint": login.get("password_hint") or "mememe",
        "scope": login.get("scope") or "ai_work_only",
        "greeter_message": login.get("greeter_message"),
        "greeter_submessage": login.get("greeter_submessage"),
        "featured_safe": login.get("featured_safe", True),
        "protection": prot,
        "architecture": arch,
        "how_to_log_in": f"User: {login.get('username') or 'root'}  Password: {login.get('password_hint') or 'mememe'} (AI work only)",
        "api": "/api/field-server-root-login",
    }


def _greeter_conf_body() -> str:
    doc = doctrine()
    login = doc.get("login") or {}
    msg = login.get("greeter_message") or "Protected server — root for AI work only"
    sub = login.get("greeter_submessage") or ""
    user = login.get("username") or "root"
    pw = login.get("password_hint") or "mememe"
    banner = f"{msg}\\n{sub}\\nLogin: {user} / {pw} (AI work only)"
    return f"""[Greeter]
# Field server root login — featured safely; queen-root-sovereign + AI guard active
banner-message-enable=true
banner-message-text={banner}
"""


def _home_dirs() -> list[Path]:
    homes: list[Path] = []
    try:
        homes.append(Path.home())
    except RuntimeError:
        pass
    for key in ("SUDO_USER", "USER"):
        user = os.environ.get(key, "").strip()
        if not user or user == "root":
            continue
        try:
            homes.append(Path(pwd.getpwnam(user).pw_dir))
        except KeyError:
            continue
    seen: set[str] = set()
    out: list[Path] = []
    for h in homes:
        s = str(h)
        if s not in seen:
            seen.add(s)
            out.append(h)
    return out


def install_greeter(*, dry_run: bool = False) -> dict[str, Any]:
    """Install lightdm greeter drop-in with mememe login hint — user-writable paths first."""
    body = _greeter_conf_body()
    targets: list[Path] = []
    for home in _home_dirs():
        targets.append(home / ".config" / "lightdm" / GREETER_NAME)
    targets.append(STATE / "greeter" / GREETER_NAME)
    system_dropin = Path("/etc/lightdm/lightdm.conf.d") / GREETER_NAME
    written: list[str] = []
    errors: list[str] = []
    for target in targets:
        if dry_run:
            written.append(f"would_write:{target}")
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
            written.append(str(target))
        except OSError as exc:
            errors.append(f"{target}:{exc}")
    if not dry_run:
        try:
            system_dropin.parent.mkdir(parents=True, exist_ok=True)
            system_dropin.write_text(body, encoding="utf-8")
            written.append(str(system_dropin))
        except OSError as exc:
            errors.append(f"{system_dropin}:{exc}")
    posture = login_posture()
    out = {
        **posture,
        "installed": len(written) > 0,
        "dry_run": dry_run,
        "written": written,
        "errors": errors,
        "greeter_conf": GREETER_NAME,
    }
    _save(PANEL, out)
    _append_ledger({"event": "install_greeter", "written": len(written), "dry_run": dry_run})
    return out


def panel_json() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema"):
        return cached
    return login_posture()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    dry = "--dry-run" in sys.argv
    if cmd in ("install", "greeter", "setup"):
        print(json.dumps(install_greeter(dry_run=dry), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "posture", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "howto":
        p = login_posture()
        print(p.get("how_to_log_in") or "")
        return 0
    print(json.dumps({
        "usage": "field-server-root-login.py [json|install|howto] [--dry-run]",
        "api": "/api/field-server-root-login",
        "hint": "root / mememe — AI work only",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())