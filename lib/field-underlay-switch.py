#!/usr/bin/env pythong
"""Field underlay switch — 2026 Tristate installer backend (permanent, no off switch)."""
from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
_KILROY_FIELD_ROOT = Path(os.environ.get("KILROY_FIELD_ROOT", "/media/default/KILROY_FIELD"))
_VIRTUAL = os.environ.get("TRISTATE_VIRTUAL", "").strip().lower() in ("1", "true", "yes")
if _VIRTUAL and not os.environ.get("NEXUS_STATE_DIR"):
    STATE = _KILROY_FIELD_ROOT / "var" / "lib" / "nexus-shield"
else:
    STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", ""))
if not SG.is_dir():
    SG = INSTALL.parent.parent
HOME = Path.home()
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL.parent / "Queen"))
DOCTRINE = INSTALL / "data" / "field-underlay-switch-doctrine.json"
LOCK = STATE / "field-underlay-lock.json"
SWITCH_PANEL = STATE / "field-underlay-switch.json"
WRDT_PLAN = STATE / "field-underlay-wrdt-plan.json"
GROK_NEXT = STATE / "field-underlay-grok-next.json"
HOST_LOCK = Path("/var/lib/nexus-shield/field-underlay-lock.json")

PHASES = ("arrive", "transform", "commit")


def _now() -> str:
    try:
        import importlib.util

        py = INSTALL / "lib" / "field-sovereign-sync.py"
        spec = importlib.util.spec_from_file_location("sovereign_sync_underlay", py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.utc("underlay")
    except (ImportError, OSError, AttributeError):
        pass
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "sovereign_clock_underlay", INSTALL / "lib" / "sovereign-clock.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.utc_z("underlay")
    except (ImportError, OSError, AttributeError):
        pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _kilroy_root() -> Path | None:
    env = os.environ.get("KILROY_ROOT", "").strip()
    if env:
        p = Path(env)
        if (p / "scripts" / "build-kilroy.sh").is_file():
            return p.resolve()
    for candidate in (
        SG.parent / "KILROY",
        SG / "KILROY",
        HOME / "Desktop" / "KILROY",
        HOME / "KILROY",
    ):
        if (candidate / "scripts" / "build-kilroy.sh").is_file():
            return candidate.resolve()
    return None


def _world_redata_root() -> Path | None:
    env = os.environ.get("WORLD_REDATA_ROOT", "").strip()
    if env:
        p = Path(env)
        if (p / "redata" / "cli.py").is_file():
            return p.resolve()
    for candidate in (
        SG / "World_Redata",
        SG.parent / "World_Redata",
        HOME / "Desktop" / "SG" / "World_Redata",
    ):
        if (candidate / "redata" / "cli.py").is_file():
            return candidate.resolve()
    return None


def _virtual_mode() -> bool:
    return _VIRTUAL or os.environ.get("NEXUS_VIRTUAL_FIELD", "").strip().lower() in ("1", "true", "yes")


def _kilroy_field_root() -> Path | None:
    root = Path(os.environ.get("KILROY_FIELD_ROOT", "/media/default/KILROY_FIELD"))
    return root.resolve() if root.is_dir() else None


def _resolve_scan_roots() -> list[Path]:
    if _virtual_mode():
        kf = _kilroy_field_root()
        if kf:
            roots = [
                kf / "tmp" / "field-storage",
                kf / "opt" / "field-storage",
                STATE,
                kf,
            ]
            return [p.resolve() for p in roots if p.is_dir()]
        return []
    doc = _load(DOCTRINE, {})
    raw = doc.get("storage", {}).get("default_scan_roots", [])
    out: list[Path] = []
    mapping = {
        "NEXUS_STATE_DIR": STATE,
        "SG_ROOT": SG,
        "HOME": HOME,
        "KILROY_FIELD_ROOT": _kilroy_field_root() or _KILROY_FIELD_ROOT,
    }
    for item in raw:
        text = str(item)
        for key, val in mapping.items():
            text = text.replace(key, str(val))
        text = text.replace("HOME", str(HOME))
        p = Path(text).expanduser()
        if p.is_dir() and p not in out:
            out.append(p.resolve())
    if not out:
        out = [STATE.resolve()] if STATE.is_dir() else []
    return out


def _run_py(rel: str, *args: str, timeout: int = 20) -> dict[str, Any]:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return {"ok": False, "error": f"missing:{rel}"}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    if SG.is_dir():
        env["SG_ROOT"] = str(SG)
    kr = _kilroy_root()
    if kr:
        env["KILROY_ROOT"] = str(kr)
    wr = _world_redata_root()
    if wr:
        env["WORLD_REDATA_ROOT"] = str(wr)
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return {"ok": False, "error": (proc.stderr or "empty")[:300]}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _wrdt_cli(*args: str, timeout: int = 120) -> dict[str, Any]:
    wr = _world_redata_root()
    if not wr:
        return {"ok": False, "error": "world_redata_missing", "hint": "Clone World_Redata beside SG"}
    cli = wr / "redata" / "cli.py"
    env = {**os.environ, "PYTHONPATH": str(wr), "WORLD_REDATA_ROOT": str(wr)}
    try:
        proc = subprocess.run(
            [sys.executable, str(cli), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(wr),
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return {"ok": False, "error": (proc.stderr or "wrdt_cli_failed")[:400]}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def lock_state() -> dict[str, Any]:
    doc = _load(LOCK, {})
    if doc.get("committed"):
        return doc
    return {
        "schema": "field-underlay-lock/v1",
        "committed": False,
        "permanent": True,
        "off_switch": False,
        "hotkey": "F9",
    }


def _phase_from_lock(lock: dict[str, Any], panel: dict[str, Any]) -> str:
    if lock.get("committed"):
        return "committed"
    if panel.get("wrdt_scanned"):
        return "commit"
    if panel.get("nexus_installed") or panel.get("underlay_ready"):
        return "transform"
    return "arrive"


def posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    lock = lock_state()
    panel = _load(SWITCH_PANEL, {})
    wrdt = _load(WRDT_PLAN, {})
    grok = _load(GROK_NEXT, {})
    underlay = (
        {"ok": True, "verdict": "PARTIAL", "skipped": "virtual"}
        if _virtual_mode()
        else _run_py("field-underlay.py", "json")
    )
    kilroy = _kilroy_root()
    wr = _world_redata_root()
    kf = _kilroy_field_root()
    bz = kilroy / "build" / "bzImage" if kilroy else None
    kf_bz = (kf / "boot" / "kilroy" / "bzImage") if kf else None
    phase = _phase_from_lock(lock, panel)
    virtual = _virtual_mode()
    host_lock = _load(HOST_LOCK, {})

    return {
        "schema": "tristate-installer/v1",
        "ts": _now(),
        "title": "2026 Tristate Installer",
        "motto": doctrine.get("motto", ""),
        "phase": phase,
        "phases": list(PHASES),
        "virtual": virtual,
        "virtual_root": str(kf) if virtual and kf else None,
        "host_safe": virtual,
        "host_committed": bool(host_lock.get("committed")),
        "state_dir": str(STATE),
        "committed": bool(lock.get("committed")),
        "permanent": True,
        "off_switch": False,
        "hotkey": doctrine.get("policy", {}).get("hotkey", "F9"),
        "policy": doctrine.get("policy", {}),
        "lock": lock,
        "panel": panel,
        "wrdt_plan": wrdt,
        "grok_next": grok,
        "underlay": underlay,
        "paths": {
            "kilroy_root": str(kilroy) if kilroy else None,
            "kilroy_field_root": str(kf) if kf else None,
            "world_redata_root": str(wr) if wr else None,
            "kilroy_bzimage": bz.is_file() if bz else False,
            "kilroy_field_bzimage": kf_bz.is_file() if kf_bz else False,
            "scan_roots": [str(p) for p in _resolve_scan_roots()],
        },
        "guest_os": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "install_gui": "/tristate-installer",
        "api": "/api/tristate-installer",
        "drive_converter": _drive_converter_py("json", timeout=30),
        "non_fielded": _non_fielded_posture(),
        "znetwork": znetwork_posture(refresh_offer=False),
        "operator": _operator_posture(),
        "switch_safety": _switch_safety(phase),
        "root": _root_posture(),
    }


def _root_posture() -> dict[str, Any]:
    py = INSTALL / "lib" / "field-polkit.py"
    if not py.is_file():
        return {"schema": "field-pol-root/v1", "ok": False, "ready": False, "error": "field_polkit_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), "root", "tristate_installer"],
            capture_output=True,
            text=True,
            timeout=20,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        doc = json.loads(proc.stdout or "{}")
        doc["ok"] = bool(doc.get("ready"))
        return doc
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"schema": "field-pol-root/v1", "ok": False, "ready": False, "error": str(exc)}


def _non_fielded_posture() -> dict[str, Any]:
    py = INSTALL / "lib" / "field-non-fielded-safety.py"
    if not py.is_file():
        return {"ok": False, "error": "non_fielded_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), "audit"],
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _switch_safety(phase: str) -> dict[str, Any]:
    if os.environ.get("NEXUS_FIELD_SWITCH_SAFETY", "1") != "1":
        return {"schema": "field-switch-safety/v1", "enabled": False, "switch_allowed": True}
    return _run_py("field-switch-safety.py", "preflight", f"--phase={phase}", timeout=12)


def _operator_posture() -> dict[str, Any]:
    py = INSTALL / "lib" / "field-operator.py"
    if not py.is_file():
        return {"ok": False, "error": "operator_missing"}
    return _run_py("field-operator.py", "json", "--no-hw-wire", timeout=15)


def board_panel(**updates: Any) -> dict[str, Any]:
    doc = _load(SWITCH_PANEL, {"schema": "field-underlay-switch/v1"})
    doc.update(updates)
    doc["updated"] = _now()
    _write_atomic(SWITCH_PANEL, doc)
    return doc


def _drive_converter_py(*args: str, timeout: int = 600) -> dict[str, Any]:
    py = INSTALL / "lib" / "field-drive-converter.py"
    if not py.is_file():
        return {"ok": False, "error": "drive_converter_missing"}
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "SG_ROOT": str(SG),
    }
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def scan_wrdt() -> dict[str, Any]:
    if lock_state().get("committed"):
        return {"ok": False, "error": "already_committed", "committed": True}
    defield = _defield_gate()
    if not defield.get("ok") and os.environ.get("NEXUS_DRIVE_CONVERTER_FORCE") != "1":
        return {
            "ok": False,
            "error": "defield_required",
            "doctrine": "Defield all tails and purge nested nexus-field on drives before WRDT scan",
            "defield_audit": defield,
            "posture": posture(),
        }
    audit = _drive_converter_py("audit", timeout=120)
    scan = _drive_converter_py("scan", timeout=300)
    plan = scan.get("plan") or {}
    if plan:
        _write_atomic(WRDT_PLAN, {**plan, "schema": "field-underlay-wrdt-plan/v1", "audit": audit})
    board_panel(
        wrdt_scanned=True,
        wrdt_audit_ok=bool(audit.get("ok")),
        drive_converter=True,
    )
    out = posture()
    out["wrdt_scan"] = plan
    out["drive_converter"] = _drive_converter_py("json", timeout=30)
    out["ok"] = bool(scan.get("ok"))
    return out


def _defield_gate() -> dict[str, Any]:
    py = INSTALL / "lib" / "field-non-fielded-safety.py"
    if not py.is_file():
        return {"ok": True, "skipped": "module_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), "gate-convert"],
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def apply_wrdt(*, confirm: bool = False, elevated: bool = False) -> dict[str, Any]:
    if not confirm:
        return {"ok": False, "error": "confirm_required", "doctrine": "type YES in GUI or pass --confirm"}
    defield = _defield_gate()
    if not defield.get("ok") and os.environ.get("NEXUS_DRIVE_CONVERTER_FORCE") != "1":
        return {
            "ok": False,
            "error": "defield_required",
            "doctrine": "Restore all field tails before WRDT apply — no field-in-field",
            "defield_audit": defield,
        }
    safety = _switch_safety("wrdt_apply")
    if not safety.get("switch_allowed"):
        return {
            "ok": False,
            "error": "thermal_crit_block" if safety.get("thermal_crit") else "conversion_blocked",
            "safety": safety,
            "doctrine": "Defer WRDT apply only at thermal crit — conversion stays non-destructive",
        }
    if _virtual_mode() and os.environ.get("TRISTATE_VIRTUAL_APPLY", "").strip().lower() not in ("1", "true", "yes"):
        return {
            "ok": False,
            "error": "virtual_dry_run",
            "doctrine": "virtual mode — set TRISTATE_VIRTUAL_APPLY=1 to convert KILROY_FIELD only",
        }
    if os.geteuid() != 0 and not elevated:
        return {"ok": False, "error": "admin_required", "action": "com.nexus.field.underlay"}
    rep = _drive_converter_py("convert", "--apply", "--confirm", timeout=900)
    board_panel(wrdt_applied=bool(rep.get("ok")), drive_converted=True)
    lock = lock_state()
    if lock.get("committed") and rep.get("ok"):
        lock["wrdt_applied"] = True
        lock["wrdt_applied_at"] = _now()
        _write_atomic(LOCK, lock)
    rep["posture"] = posture()
    return rep


def grok_prep(*, elevated: bool = False) -> dict[str, Any]:
    kilroy = _kilroy_root()
    kf = _kilroy_field_root()
    if not kilroy and not kf:
        return {"ok": False, "error": "kilroy_missing"}
    bz = (kilroy / "build" / "bzImage") if kilroy else (kf / "boot" / "kilroy" / "bzImage")
    compose = (kilroy / "scripts" / "grok-compose.sh") if kilroy else None
    doc = {
        "schema": "field-underlay-grok-next/v1",
        "ts": _now(),
        "entry": "/KILROY Field",
        "kilroy_root": str(kilroy) if kilroy else None,
        "kilroy_field_root": str(kf) if kf else None,
        "virtual": _virtual_mode(),
        "bzimage_present": bz.is_file(),
        "esp_hint": "/boot/efi",
    }
    if kilroy and compose.is_file() and (os.geteuid() == 0 or elevated):
        try:
            subprocess.run(["bash", str(compose)], cwd=str(kilroy), timeout=60, check=False)
            doc["grok_compose"] = True
        except OSError:
            doc["grok_compose"] = False
    if shutil.which("efibootmgr") and (os.geteuid() == 0 or elevated):
        try:
            proc = subprocess.run(
                ["efibootmgr", "-o"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            doc["efibootmgr_current"] = (proc.stdout or proc.stderr or "").strip()[:500]
        except OSError:
            pass
    _write_atomic(GROK_NEXT, doc)
    board_panel(grok_prepared=True)
    return {"ok": True, "grok": doc, "posture": posture()}


def commit(*, elevated: bool = False) -> dict[str, Any]:
    if lock_state().get("committed"):
        return {"ok": True, "already": True, "posture": posture()}
    defield = _defield_gate()
    if not defield.get("ok") and os.environ.get("NEXUS_UNDERLAY_FORCE") != "1":
        return {
            "ok": False,
            "error": "defield_required_before_commit",
            "doctrine": "Zero field tails in scan roots before permanent underlay commit",
            "defield_audit": defield,
        }
    safety = _switch_safety("commit")
    if not safety.get("switch_allowed"):
        return {
            "ok": False,
            "error": "thermal_crit_block" if safety.get("thermal_crit") else "conversion_blocked",
            "safety": safety,
            "doctrine": "Commit blocked only at thermal crit — warn uses wave shed, not slowdown",
        }
    underlay = (
        {"ok": True, "verdict": "PARTIAL", "skipped": "virtual"}
        if _virtual_mode()
        else _run_py("field-underlay.py", "json")
    )
    if not underlay.get("drop_in_replacement_ready") and os.environ.get("NEXUS_UNDERLAY_FORCE") != "1":
        board_panel(underlay_ready=underlay.get("verdict") in ("PARTIAL", "GREEN"))
    doc = {
        "schema": "field-underlay-lock/v1",
        "committed": True,
        "committed_at": _now(),
        "permanent": True,
        "off_switch": False,
        "reversible": False,
        "hotkey": "F9",
        "guest_passthrough": True,
        "reboot_target": "KILROY Field",
        "underlay_verdict": underlay.get("verdict"),
        "motto": "We are always the underlay from this point forward.",
        "virtual": _virtual_mode(),
        "host_safe": _virtual_mode(),
        "kilroy_field_root": str(_kilroy_field_root() or ""),
    }
    _write_atomic(LOCK, doc)
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("sovereign_sync_underlay_commit", INSTALL / "lib" / "field-sovereign-sync.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.sync_section("underlay", "commit")
    except (ImportError, OSError, AttributeError):
        pass
    board_panel(committed=True, phase="committed")
    grok_prep(elevated=elevated and os.geteuid() == 0)
    return {"ok": True, "lock": doc, "posture": posture()}


def reboot_field(*, elevated: bool = False) -> dict[str, Any]:
    if _virtual_mode():
        return {
            "ok": False,
            "error": "virtual_no_reboot",
            "doctrine": "virtual test on KILROY_FIELD — host reboot blocked",
            "posture": posture(),
        }
    safety = _switch_safety("reboot")
    if not safety.get("switch_allowed"):
        return {
            "ok": False,
            "error": "thermal_crit_block" if safety.get("thermal_crit") else "conversion_blocked",
            "safety": safety,
            "doctrine": "Reboot blocked only at thermal crit — conversion path stays fast",
            "posture": posture(),
        }
    lock = lock_state()
    if not lock.get("committed"):
        return {"ok": False, "error": "commit_first"}
    if os.geteuid() != 0 and not elevated:
        return {"ok": False, "error": "admin_required", "action": "com.nexus.field.underlay"}
    try:
        subprocess.Popen(["systemctl", "reboot"])
        return {"ok": True, "rebooting": True}
    except OSError:
        try:
            subprocess.Popen(["reboot"])
            return {"ok": True, "rebooting": True}
        except OSError as exc:
            return {"ok": False, "error": str(exc)}


def _znetwork_bin() -> Path | None:
    env = os.environ.get("ZNETWORK_BIN", "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p.resolve()
    sg = SG if SG.is_dir() else INSTALL.parent.parent
    for candidate in (
        INSTALL / "bin" / "znetwork",
        sg / "ZNetwork" / "build" / "znetwork",
        HOME / "Desktop" / "SG" / "ZNetwork" / "build" / "znetwork",
    ):
        if candidate.is_file():
            return candidate.resolve()
    return None


def _znetwork_operator() -> dict[str, Any]:
    return _load(STATE / "znetwork-operator.json", {})


def znetwork_posture(*, refresh_offer: bool = False) -> dict[str, Any]:
    op = _znetwork_operator()
    choice = str(op.get("choice") or "").strip().lower()
    running = choice == "yes" and (
        op.get("running") is True or str(op.get("running")).lower() == "true"
    )
    status = _load(STATE / "znetwork-status.json", {})
    out: dict[str, Any] = {
        "ok": True,
        "choice": choice or None,
        "running": running,
        "operator": op,
        "status": status if status else None,
        "binary": str(_znetwork_bin() or ""),
    }
    if refresh_offer or not choice:
        bin_path = _znetwork_bin()
        if not bin_path:
            out.update({"ok": False, "error": "znetwork_missing"})
            return out
        env = {**os.environ, "SG_ROOT": str(SG if SG.is_dir() else INSTALL.parent.parent)}
        try:
            proc = subprocess.run(
                [str(bin_path), "confirm", "--json"],
                capture_output=True,
                text=True,
                timeout=20,
                env=env,
            )
            if proc.stdout.strip():
                out["offer"] = json.loads(proc.stdout)
            else:
                out["offer_error"] = (proc.stderr or "znetwork_offer_failed")[:300]
        except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
            out["offer_error"] = str(exc)
    return out


def znetwork_choice(choice: str) -> dict[str, Any]:
    normalized = str(choice or "").strip().lower() or "yes"
    if normalized not in ("yes", "no", "skip"):
        return {"ok": False, "error": "invalid_choice", "choices": ["yes", "no", "skip"]}
    helper = INSTALL / "lib" / "znetwork-field.sh"
    if not helper.is_file():
        return {"ok": False, "error": "znetwork_helper_missing"}
    sg = SG if SG.is_dir() else INSTALL.parent.parent
    skip_marker = STATE / "znetwork-skip.marker"
    inner = f"""
set -euo pipefail
export NEXUS_INSTALL_ROOT={shlex.quote(str(INSTALL))}
export NEXUS_STATE_DIR={shlex.quote(str(STATE))}
export SG_ROOT={shlex.quote(str(sg))}
export ZNETWORK_MODE=${{ZNETWORK_MODE:-REVIEW_ONLY}}
# shellcheck source=/dev/null
source {shlex.quote(str(helper))}
case {shlex.quote(normalized)} in
  yes) nexus_znetwork_activate_on_yes || exit 1 ;;
  no) nexus_znetwork_write_operator no false ;;
  skip)
    nexus_znetwork_write_operator skip false
    mkdir -p {shlex.quote(str(STATE))}
    : >{shlex.quote(str(skip_marker))}
    ;;
esac
"""
    try:
        proc = subprocess.run(["bash", "-c", inner], capture_output=True, text=True, timeout=45)
        if proc.returncode != 0:
            return {
                "ok": False,
                "error": "znetwork_choice_failed",
                "detail": (proc.stderr or proc.stdout or "")[:400],
            }
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "error": str(exc)}
    board_panel(znetwork_choice=normalized, znetwork_ready=True)
    rep = znetwork_posture(refresh_offer=False)
    rep["choice_saved"] = normalized
    return rep


def mark_nexus_installed() -> dict[str, Any]:
    board_panel(nexus_installed=True, underlay_ready=True)
    return {"ok": True, "posture": posture()}


def hotkey_action() -> dict[str, Any]:
    f9_py = INSTALL / "lib" / "field-queen-browser-open.py"
    if f9_py.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(f9_py), "f9"],
                capture_output=True,
                text=True,
                timeout=45,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            doc = json.loads(proc.stdout or "{}")
            doc["posture"] = posture()
            return doc
        except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
            pass
    p = posture()
    if p.get("committed"):
        return {"ok": True, "action": "queen_sovereign_browser", "url": "/world/browser.html", "posture": p}
    return {"ok": True, "action": "tristate_installer", "url": "/tristate-installer", "posture": p}


def zenity_wizard() -> int:
    if not shutil.which("zenity"):
        print(json.dumps(posture(), indent=2))
        return 0
    lock = lock_state()
    if lock.get("committed"):
        subprocess.run(
            [
                "zenity", "--info", "--title=Field Underlay",
                "--text=Underlay committed — permanent.\nNo off switch.\nGuest OS runs inside protections.",
                "--width=420",
            ],
            check=False,
        )
        return 0
    if subprocess.run(
        [
            "zenity", "--question", "--title=2026 Tristate Installer",
            "--text=Move under NEXUS/KILROY permanently?\n\n• Guest OS stays — runs inside protections\n• World_Redata WRDT1 repack available\n• No off switch after commit\n• F9 opens this installer anytime before commit",
            "--width=480", "--ok-label=Open Installer", "--cancel-label=Cancel",
        ],
        check=False,
    ).returncode != 0:
        return 3
    opener = INSTALL / "lib" / "queen-panel-open.py"
    if opener.is_file():
        subprocess.run(
            [sys.executable, str(opener), "nexus", "tristate-installer"],
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL)},
            timeout=25,
            check=False,
        )
    return 0


def virtual_test() -> dict[str, Any]:
    """Full dry pipeline on KILROY_FIELD partition — host stays safe."""
    os.environ.setdefault("TRISTATE_VIRTUAL", "1")
    global STATE, LOCK, SWITCH_PANEL, WRDT_PLAN, GROK_NEXT
    kf = _kilroy_field_root()
    if not kf:
        return {"ok": False, "error": "kilroy_field_missing", "path": str(_KILROY_FIELD_ROOT)}
    STATE = Path(
        os.environ.get("NEXUS_STATE_DIR", str(kf / "tmp" / "nexus-shield-virtual"))
    )
    LOCK = STATE / "field-underlay-lock.json"
    SWITCH_PANEL = STATE / "field-underlay-switch.json"
    WRDT_PLAN = STATE / "field-underlay-wrdt-plan.json"
    GROK_NEXT = STATE / "field-underlay-grok-next.json"
    STATE.mkdir(parents=True, exist_ok=True)
    fresh = "--fresh" in sys.argv or os.environ.get("TRISTATE_VIRTUAL_FRESH", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if fresh:
        for p in list(STATE.iterdir()):
            if p.is_file():
                p.unlink()
    staging = kf / "tmp" / "field-storage" / "tristate-probe"
    staging.mkdir(parents=True, exist_ok=True)
    probe = staging / "field-probe.bin"
    if not probe.is_file():
        probe.write_bytes(b"WRDT1-TRISTATE-PROBE-" + os.urandom(256))
    host_before = _load(HOST_LOCK, {})
    steps: list[dict[str, Any]] = []

    def _step(name: str, fn: Any) -> None:
        try:
            rep = fn()
            steps.append({"step": name, "ok": rep.get("ok", True), "summary": rep})
        except Exception as exc:
            steps.append({"step": name, "ok": False, "error": str(exc)})

    def _scan_wrdt_virtual() -> dict[str, Any]:
        rep = scan_wrdt()
        if not rep.get("ok") and rep.get("error") == "already_committed":
            return {**rep, "ok": True, "skipped": "already_committed"}
        return rep

    _step("posture", posture)
    _step("scan_wrdt", _scan_wrdt_virtual)
    _step("grok_prep", lambda: grok_prep(elevated=False))
    _step("virtual_commit", lambda: commit(elevated=False))
    _step("reboot_blocked", reboot_field)
    host_after = _load(HOST_LOCK, {})
    required_ok = {"posture", "scan_wrdt", "grok_prep", "virtual_commit"}
    reboot_step = next((s for s in steps if s["step"] == "reboot_blocked"), {})
    report = {
        "schema": "tristate-virtual-test/v1",
        "ts": _now(),
        "ok": (
            all(s.get("ok", False) for s in steps if s["step"] in required_ok)
            and reboot_step.get("summary", {}).get("error") == "virtual_no_reboot"
            and host_before == host_after
        ),
        "kilroy_field_root": str(kf),
        "state_dir": str(STATE),
        "host_lock_unchanged": host_before == host_after,
        "host_committed_before": bool(host_before.get("committed")),
        "host_committed_after": bool(host_after.get("committed")),
        "virtual_lock": _load(LOCK, {}),
        "steps": steps,
        "posture": posture(),
    }
    _write_atomic(STATE / "tristate-virtual-report.json", report)
    return report


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    elevated = "--elevated" in sys.argv or os.environ.get("NEXUS_ELEVATED_ROOT") == "1"
    confirm = "--confirm" in sys.argv

    handlers = {
        "json": lambda: posture(),
        "status": lambda: posture(),
        "board": lambda: {**posture(), "panel": board_panel(boarded=True)},
        "scan-wrdt": scan_wrdt,
        "wrdt-apply": lambda: apply_wrdt(confirm=confirm, elevated=elevated),
        "grok-prep": lambda: grok_prep(elevated=elevated),
        "commit": lambda: commit(elevated=elevated),
        "reboot": lambda: reboot_field(elevated=elevated),
        "mark-nexus": mark_nexus_installed,
        "znetwork-offer": lambda: znetwork_posture(refresh_offer=True),
        "znetwork-choice": lambda: znetwork_choice(
            os.environ.get("ZNETWORK_CHOICE") or (sys.argv[2] if len(sys.argv) > 2 else "")
        ),
        "hotkey": hotkey_action,
        "zenity": lambda: zenity_wizard() or posture(),
        "virtual-test": virtual_test,
    }
    fn = handlers.get(mode)
    if not fn:
        print(
            "usage: field-underlay-switch.py [json|scan-wrdt|commit|virtual-test|wrdt-apply|reboot|hotkey|zenity]",
            file=sys.stderr,
        )
        return 2
    result = fn()
    if isinstance(result, int):
        return result
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())