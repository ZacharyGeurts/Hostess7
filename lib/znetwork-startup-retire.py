#!/usr/bin/env pythong
"""ZNetwork startup retire — detect host networking software and disable startup only.

After ZNetwork relayer owns policy, retire competing *startup* entries (systemd, user
services, autostart .desktop). Live daemons are never stopped — link stays up until
reboot. Rollback receipt preserves every change.
"""
from __future__ import annotations

import configparser
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
ROLLBACK = STATE / "znetwork-startup-retire-rollback.json"
RECEIPT = STATE / "znetwork-startup-retire.json"
LEDGER = STATE / "znetwork-startup-retire.jsonl"
SCHEMA = "znetwork-startup-retire/v1"

# Host networking — startup/autostart only; never our field stacks (handler-retire owns those).
_HOST_SIGNATURES: list[dict[str, Any]] = [
    {
        "id": "network_manager",
        "label": "NetworkManager",
        # Never retire NM systemd — ZNetwork coexists; link must survive reboot.
        "systemd": (),
        "user_systemd": (),
        "autostart_exec": ("nm-applet", "nm-tray-applet", "network-manager-applet"),
        "desktop_names": (
            "nm-applet.desktop",
            "nm-tray-applet.desktop",
            "network-manager-applet.desktop",
        ),
    },
    {
        "id": "systemd_networkd",
        "label": "systemd-networkd",
        "systemd": (
            "systemd-networkd.service",
            "systemd-networkd-wait-online.service",
        ),
    },
    {
        "id": "systemd_resolved",
        "label": "systemd-resolved",
        "systemd": ("systemd-resolved.service",),
    },
    {
        "id": "connman",
        "label": "ConnMan",
        "systemd": ("connman.service",),
        "autostart_exec": ("connman-applet", "connman-ui"),
        "desktop_names": ("connman-applet.desktop",),
    },
    {
        "id": "wpa_supplicant",
        "label": "wpa_supplicant",
        "systemd": ("wpa_supplicant.service",),
    },
    {
        "id": "iwd",
        "label": "iwd",
        "systemd": ("iwd.service",),
    },
    {
        "id": "net_applet_misc",
        "label": "Network tray applets",
        "autostart_exec": (
            "mate-nm-applet",
            "xfce4-nm-applet",
            "lxqt-nm-applet",
            "plasma-nm",
            "kdeconnectd",
        ),
        "desktop_names": (
            "mate-nm-applet.desktop",
            "xfce4-nm-applet.desktop",
        ),
    },
]

_AUTOSTART_EXEC_RE = re.compile(
    r"(nm-applet|nm-tray|network-manager|connman|wpa_gui|iwd-applet|"
    r"mate-nm-applet|xfce4-nm-applet|plasma-nm)",
    re.I,
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _append_ledger(row: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


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


def _run(cmd: list[str], *, timeout: float = 12.0, user: bool = False) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "rc": proc.returncode,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
            "cmd": cmd,
        }
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "error": str(exc), "cmd": cmd}


def _systemctl_enabled(unit: str, *, user: bool = False) -> str | None:
    cmd = ["systemctl"]
    if user:
        cmd.append("--user")
    cmd.extend(["is-enabled", unit])
    rep = _run(cmd, timeout=6.0, user=user)
    if not rep.get("ok"):
        return None
    state = (rep.get("stdout") or "").strip()
    return state if state in ("enabled", "enabled-runtime", "linked", "masked", "disabled", "static") else state or None


def znetwork_took_over() -> dict[str, Any]:
    """True when relayer + running marker show ZNetwork owns networking policy."""
    running = STATE / "znetwork-running.marker"
    if not running.is_file():
        return {"ok": False, "reason": "not_running"}

    relayer = _load_json(STATE / "znetwork-relayer.json")
    if relayer and relayer.get("active") is True:
        return {"ok": True, "via": "relayer_active", "layer": relayer.get("layer")}

    conn = _load_json(STATE / "znetwork-connection.json")
    if conn and conn.get("policy_owner") == "znetwork":
        return {"ok": True, "via": "connection_owner"}

    op = _load_json(STATE / "znetwork-operator.json")
    if op and op.get("running") is True and op.get("choice") == "yes":
        return {"ok": True, "via": "operator_running"}

    return {"ok": False, "reason": "takeover_not_confirmed"}


def _parse_desktop(path: Path) -> configparser.RawConfigParser:
    cp = configparser.RawConfigParser()
    cp.optionxform = str  # type: ignore[method-assign]
    cp.read(path, encoding="utf-8")
    return cp


def _desktop_exec(path: Path) -> str:
    try:
        cp = _parse_desktop(path)
        if cp.has_section("Desktop Entry"):
            return cp.get("Desktop Entry", "Exec", fallback="")
    except (OSError, configparser.Error):
        pass
    return ""


def _scan_autostart() -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for home in _home_dirs():
        autostart = home / ".config" / "autostart"
        if not autostart.is_dir():
            continue
        for desktop in sorted(autostart.glob("*.desktop")):
            if desktop.name.endswith(".nexus-retired"):
                continue
            exec_line = _desktop_exec(desktop)
            matched_id = ""
            matched_label = ""
            for spec in _HOST_SIGNATURES:
                if desktop.name in (spec.get("desktop_names") or ()):
                    matched_id = spec["id"]
                    matched_label = spec["label"]
                    break
                for token in spec.get("autostart_exec") or ():
                    if token.lower() in exec_line.lower():
                        matched_id = spec["id"]
                        matched_label = spec["label"]
                        break
                if matched_id:
                    break
            if not matched_id and exec_line and _AUTOSTART_EXEC_RE.search(exec_line):
                matched_id = "autostart_exec_match"
                matched_label = "Network autostart"
            if not matched_id:
                continue
            hits.append(
                {
                    "kind": "autostart",
                    "id": matched_id,
                    "label": matched_label,
                    "path": str(desktop),
                    "exec": exec_line[:240],
                    "enabled": True,
                }
            )
    return hits


def _retire_nm_systemd() -> bool:
    """Retire NetworkManager systemd only when explicitly requested (default: coexist)."""
    return os.environ.get("ZNETWORK_RETIRE_NM_SYSTEMD", "0") == "1"


def _scan_systemd_units() -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()
    nm_systemd = (
        "NetworkManager.service",
        "NetworkManager-wait-online.service",
        "NetworkManager-dispatcher.service",
    )
    for spec in _HOST_SIGNATURES:
        for unit in spec.get("systemd") or ():
            if unit in seen:
                continue
            if spec.get("id") == "network_manager" and not _retire_nm_systemd():
                if unit in nm_systemd:
                    continue
            state = _systemctl_enabled(unit, user=False)
            if state is None:
                continue
            seen.add(unit)
            if state in ("disabled", "masked", "static"):
                continue
            hits.append(
                {
                    "kind": "systemd",
                    "scope": "system",
                    "id": spec["id"],
                    "label": spec["label"],
                    "unit": unit,
                    "enabled_state": state,
                }
            )
        for unit in spec.get("user_systemd") or ():
            key = f"user:{unit}"
            if key in seen:
                continue
            if spec.get("id") == "network_manager" and not _retire_nm_systemd():
                continue
            state = _systemctl_enabled(unit, user=True)
            if state is None:
                continue
            seen.add(key)
            if state in ("disabled", "masked", "static"):
                continue
            hits.append(
                {
                    "kind": "systemd",
                    "scope": "user",
                    "id": spec["id"],
                    "label": spec["label"],
                    "unit": unit,
                    "enabled_state": state,
                }
            )
    return hits


def detect_host_networking() -> dict[str, Any]:
    """Enumerate host networking startup entries still enabled."""
    takeover = znetwork_took_over()
    systemd_hits = _scan_systemd_units()
    autostart_hits = _scan_autostart()
    return {
        "schema": SCHEMA,
        "ok": True,
        "takeover": takeover,
        "systemd": systemd_hits,
        "autostart": autostart_hits,
        "count": len(systemd_hits) + len(autostart_hits),
        "checked_at": _now(),
        "motto": "Detect startup only — live daemons untouched until reboot.",
    }


def _disable_autostart(path: Path, *, results: list[dict[str, Any]], rollback: dict[str, Any]) -> bool:
    if not path.is_file():
        return False
    try:
        original = path.read_text(encoding="utf-8")
    except OSError as exc:
        results.append({"kind": "autostart", "path": str(path), "ok": False, "error": str(exc)})
        return False

    retired = path.with_name(path.name + ".nexus-retired")
    backup = {
        "path": str(path),
        "retired_path": str(retired),
        "original": original,
    }
    try:
        cp = _parse_desktop(path)
        if not cp.has_section("Desktop Entry"):
            cp.add_section("Desktop Entry")
        cp.set("Desktop Entry", "Hidden", "true")
        if cp.has_option("Desktop Entry", "X-GNOME-Autostart-enabled"):
            cp.set("Desktop Entry", "X-GNOME-Autostart-enabled", "false")
        from io import StringIO

        buf = StringIO()
        cp.write(buf)
        disabled_text = buf.getvalue()
        path.write_text(disabled_text, encoding="utf-8")
        retired.write_text(original, encoding="utf-8")
        backup["disabled"] = disabled_text
        rollback.setdefault("autostart", []).append(backup)
        results.append(
            {
                "kind": "autostart",
                "path": str(path),
                "ok": True,
                "action": "hidden_and_backed_up",
                "retired_path": str(retired),
            }
        )
        _append_ledger({"event": "retire_autostart", "path": str(path)})
        return True
    except OSError as exc:
        results.append({"kind": "autostart", "path": str(path), "ok": False, "error": str(exc)})
        return False


def _disable_systemd_unit(unit: str, *, scope: str, results: list[dict[str, Any]], rollback: dict[str, Any]) -> bool:
    prev = _systemctl_enabled(unit, user=(scope == "user"))
    cmd = ["systemctl"]
    if scope == "user":
        cmd.append("--user")
    cmd.extend(["disable", unit])
    rep = _run(cmd)
    if not rep.get("ok"):
        # Try with sudo when system scope needs elevation.
        if scope == "system" and shutil.which("sudo"):
            rep = _run(["sudo", "-n"] + cmd)
        if not rep.get("ok") and scope == "system" and shutil.which("pkexec"):
            rep = _run(["pkexec"] + cmd, timeout=30.0)
    ok = bool(rep.get("ok"))
    row = {
        "kind": "systemd",
        "scope": scope,
        "unit": unit,
        "ok": ok,
        "action": "disable_no_stop",
        "previous_state": prev,
        "detail": (rep.get("stderr") or rep.get("stdout") or rep.get("error") or "")[:200],
    }
    results.append(row)
    if ok:
        rollback.setdefault("systemd", []).append(
            {"unit": unit, "scope": scope, "previous_state": prev, "action": "disable"}
        )
        _append_ledger({"event": "retire_systemd", "unit": unit, "scope": scope})
    return ok


def retire_host_startup(*, force: bool = False) -> dict[str, Any]:
    """Disable host networking startup entries once ZNetwork took over. No live process stop."""
    if os.environ.get("ZNETWORK_STARTUP_RETIRE", "1") == "0":
        return {
            "schema": SCHEMA,
            "ok": True,
            "skipped": True,
            "reason": "env_disabled",
            "at": _now(),
        }

    takeover = znetwork_took_over()
    if not force and not takeover.get("ok"):
        return {
            "schema": SCHEMA,
            "ok": True,
            "skipped": True,
            "reason": takeover.get("reason") or "takeover_not_confirmed",
            "takeover": takeover,
            "at": _now(),
        }

    detected = detect_host_networking()
    results: list[dict[str, Any]] = []
    rollback_doc = _load_json(ROLLBACK) or {
        "schema": "znetwork-startup-retire-rollback/v1",
        "entries": {"autostart": [], "systemd": []},
    }
    entries = rollback_doc.setdefault("entries", {"autostart": [], "systemd": []})

    for hit in detected.get("autostart") or []:
        path = Path(str(hit.get("path") or ""))
        _disable_autostart(path, results=results, rollback=entries)

    for hit in detected.get("systemd") or []:
        unit = str(hit.get("unit") or "")
        scope = str(hit.get("scope") or "system")
        if unit:
            _disable_systemd_unit(unit, scope=scope, results=results, rollback=entries)

    retired_count = sum(1 for r in results if r.get("ok"))
    needs_reboot = retired_count > 0
    rollback_doc["updated"] = _now()
    rollback_doc["install_root"] = str(INSTALL.resolve())
    _save(ROLLBACK, rollback_doc)

    receipt = {
        "schema": SCHEMA,
        "ok": True,
        "takeover": takeover,
        "retired_count": retired_count,
        "needs_reboot": needs_reboot,
        "results": results,
        "rollback": str(ROLLBACK),
        "detected_count": detected.get("count", 0),
        "at": _now(),
        "motto": "Startup retired — live link preserved; reboot applies clean stack.",
    }
    _save(RECEIPT, receipt)
    _append_ledger({"event": "retire_complete", "retired_count": retired_count, "needs_reboot": needs_reboot})
    return receipt


def rollback_host_startup() -> dict[str, Any]:
    """Restore autostart and re-enable systemd units from rollback receipt."""
    doc = _load_json(ROLLBACK)
    if not doc:
        return {"schema": SCHEMA, "ok": True, "skipped": True, "reason": "no_rollback"}
    entries = doc.get("entries") or {}
    results: list[dict[str, Any]] = []

    for item in entries.get("autostart") or []:
        path = Path(str(item.get("path") or ""))
        original = item.get("original") or ""
        try:
            if original:
                path.write_text(original, encoding="utf-8")
            retired = Path(str(item.get("retired_path") or ""))
            retired.unlink(missing_ok=True)
            results.append({"kind": "autostart", "path": str(path), "ok": True, "action": "restored"})
        except OSError as exc:
            results.append({"kind": "autostart", "path": str(path), "ok": False, "error": str(exc)})

    for item in entries.get("systemd") or []:
        unit = str(item.get("unit") or "")
        scope = str(item.get("scope") or "system")
        cmd = ["systemctl"]
        if scope == "user":
            cmd.append("--user")
        cmd.extend(["enable", unit])
        rep = _run(cmd)
        if not rep.get("ok") and scope == "system" and shutil.which("sudo"):
            rep = _run(["sudo", "-n"] + cmd)
        results.append(
            {
                "kind": "systemd",
                "unit": unit,
                "scope": scope,
                "ok": bool(rep.get("ok")),
                "action": "enable",
            }
        )

    return {"schema": SCHEMA, "ok": True, "results": results, "at": _now()}


def posture() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "ok": True,
        "takeover": znetwork_took_over(),
        "detected": detect_host_networking(),
        "receipt": _load_json(RECEIPT),
        "rollback": _load_json(ROLLBACK),
        "checked_at": _now(),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    handlers = {
        "json": posture,
        "detect": detect_host_networking,
        "takeover": znetwork_took_over,
        "retire": retire_host_startup,
        "rollback": rollback_host_startup,
    }
    fn = handlers.get(cmd)
    if not fn:
        print(
            json.dumps(
                {"error": "usage: znetwork-startup-retire.py [json|detect|takeover|retire|rollback]"}
            ),
            file=sys.stderr,
        )
        return 2
    force = "--force" in sys.argv[2:]
    if cmd == "retire":
        result = retire_host_startup(force=force)
    else:
        result = fn()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())