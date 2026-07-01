#!/usr/bin/env pythong
"""ZNetwork orchestrator — protection and hardening only; no field bridge transmit."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "znetwork-doctrine.json"
STATUS = STATE / "znetwork-status.json"
OPERATOR = STATE / "znetwork-operator.json"
TRAY_MODE = STATE / "znetwork-tray-mode.json"
LEDGER = STATE / "znetwork-ledger.jsonl"
ACTIVATE_LOG = STATE / "znetwork-activate.jsonl"
SHADOW = STATE / "znetwork-shadow.json"
SOCK = STATE / "znetwork-field.sock"
RUNNING_MARKER = STATE / "znetwork-running.marker"
SCHEMA = "znetwork-orchestrator/v3"


def _protection_only() -> bool:
    return os.environ.get("ZNETWORK_PROTECTION_ONLY", "1") != "0"


def _smart_inside() -> bool:
    return os.environ.get("ZNETWORK_SMART_INSIDE", "1") != "0"

_MOD_CACHE: dict[str, Any] = {}
_SOVEREIGN_CLOCK_MOD = None
_TRUTH_GATE_CACHE: dict[str, Any] | None = None
_TRUTH_GATE_CACHE_AT = 0.0
_TRUTH_GATE_TTL_SEC = 4.0


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        py = Path(__file__).resolve().parent / "sovereign-clock.py"
        spec = importlib.util.spec_from_file_location("sovereign_clock_znet", py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _SOVEREIGN_CLOCK_MOD = mod
    if _SOVEREIGN_CLOCK_MOD and hasattr(_SOVEREIGN_CLOCK_MOD, "utc_z"):
        return _SOVEREIGN_CLOCK_MOD.utc_z("znetwork")
    return ""


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


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def znetwork_bin() -> Path | None:
    env = os.environ.get("ZNETWORK_BIN", "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p.resolve()
    sg = Path(os.environ.get("SG_ROOT", str(INSTALL.parent)))
    for candidate in (
        sg / "ZNetwork" / "build" / "znetwork",
        INSTALL.parent / "ZNetwork" / "build" / "znetwork",
        INSTALL / "bin" / "znetwork",
    ):
        if candidate.is_file():
            return candidate.resolve()
    return None


def truth_gate(*, refresh: bool = False) -> dict[str, Any]:
    """Local protection posture — binary + probe; never blocks on field stack gates."""
    global _TRUTH_GATE_CACHE, _TRUTH_GATE_CACHE_AT
    if (
        not refresh
        and _TRUTH_GATE_CACHE is not None
        and (time.monotonic() - _TRUTH_GATE_CACHE_AT) < _TRUTH_GATE_TTL_SEC
    ):
        return dict(_TRUTH_GATE_CACHE)

    mode = os.environ.get("ZNETWORK_MODE", "REVIEW_ONLY")
    bin_ok = znetwork_bin() is not None
    probe_ok = False
    if bin_ok:
        rc, out, _ = _run_bin(["probe", "--json"], timeout=8)
        probe_ok = rc == 0 and bool(out.strip())
    gates = {
        "binary": {"ok": bin_ok, "id": "binary"},
        "probe": {"ok": probe_ok, "id": "probe"},
        "protection_only": {"ok": _protection_only(), "id": "protection_only"},
        "field_bridges": {"ok": False, "id": "field_bridges", "forbidden": _protection_only()},
    }
    rep = {
        "schema": "znetwork-protection-gate/v3",
        "ok": bin_ok and probe_ok,
        "gates": gates,
        "mode": mode,
        "protection_only": _protection_only(),
        "checked_at": _now(),
    }
    _TRUTH_GATE_CACHE = dict(rep)
    _TRUTH_GATE_CACHE_AT = time.monotonic()
    return rep


def _run_bin(args: list[str], *, timeout: int = 30) -> tuple[int, str, str]:
    bin_path = znetwork_bin()
    if not bin_path:
        return 127, "", "znetwork_binary_missing"
    env = {**os.environ, "SG_ROOT": str(INSTALL.parent)}
    try:
        proc = subprocess.run(
            [str(bin_path), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except (subprocess.SubprocessError, OSError) as exc:
        return 1, "", str(exc)


def triple_check() -> dict[str, Any]:
    probe_ok = status_ok = gate_ok = 0
    rc, out, err = _run_bin(["probe", "--json"])
    if rc == 0 and out.strip():
        probe_ok = 1
    rc, out, err = _run_bin(["status", "--json"])
    if rc == 0 and out.strip():
        try:
            doc = json.loads(out)
            _save(STATUS, doc)
            status_ok = 1
        except json.JSONDecodeError:
            pass
    if not _protection_only():
        for gate_script in (
            INSTALL / "znetwork" / "scripts" / "znetwork-review-gate.sh",
            INSTALL.parent / "ZNetwork" / "scripts" / "znetwork-review-gate.sh",
        ):
            if not gate_script.is_file():
                continue
            env = {
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "NEXUS_STATE_DIR": str(STATE),
                "ZNETWORK_BIN": str(znetwork_bin() or ""),
                "ZNETWORK_MODE": os.environ.get("ZNETWORK_MODE", "REVIEW_ONLY"),
            }
            try:
                proc = subprocess.run(
                    ["bash", str(gate_script)],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    env=env,
                )
                if proc.returncode == 0:
                    gate_ok = 1
                    break
            except (subprocess.SubprocessError, OSError):
                pass
    else:
        gate_ok = 1
    ok = probe_ok and status_ok and gate_ok
    rep = {
        "schema": "znetwork-triple-check/v2",
        "ok": bool(ok),
        "probe": bool(probe_ok),
        "status": bool(status_ok),
        "gate": bool(gate_ok),
        "mode": os.environ.get("ZNETWORK_MODE", "REVIEW_ONLY"),
        "checked_at": _now(),
    }
    _append_jsonl(LEDGER, {"event": "triple_check", **rep})
    return rep


def _handler_retire_mod() -> Any | None:
    return _mod(INSTALL / "lib" / "znetwork-handler-retire.py", "znetwork_handler_retire")


def _bridge_field_dns() -> dict[str, Any]:
    dns_sh = INSTALL / "lib" / "field-dns.sh"
    if not dns_sh.is_file():
        return {"ok": False, "skipped": True}
    try:
        subprocess.run(
            ["bash", "-c", f'source "{dns_sh}" && nexus_field_dns_publish'],
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        connect_py = INSTALL / "lib" / "field-local-dns-connect.py"
        connect: dict[str, Any] = {"ok": False, "skipped": True}
        if connect_py.is_file():
            proc = subprocess.run(
                [os.environ.get("NEXUS_PYTHONG", "pythong"), str(connect_py), "connect"],
                capture_output=True,
                text=True,
                timeout=20,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            try:
                connect = json.loads(proc.stdout or "{}")
            except json.JSONDecodeError:
                connect = {"ok": proc.returncode == 0}
        return {"ok": True, "local_connect": connect}
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _relayer_mode() -> bool:
    return os.environ.get("ZNETWORK_RELAYER", "1") != "0" and os.environ.get("ZNETWORK_UNDERHOOK", "0") != "1"


def _bridge_gatekeeper() -> dict[str, Any]:
    if _relayer_mode() or not _smart_inside():
        gk_sh = INSTALL / "lib" / "gatekeeper-enforce.sh"
        if not gk_sh.is_file():
            return {"ok": False, "skipped": True, "mode": "enforce"}
        try:
            subprocess.run(
                ["bash", "-c", f'source "{gk_sh}" && nexus_gatekeeper_enforce_strict'],
                capture_output=True,
                text=True,
                timeout=15,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            return {"ok": True, "mode": "enforce", "relayer": _relayer_mode()}
        except (subprocess.SubprocessError, OSError) as exc:
            return {"ok": False, "error": str(exc), "mode": "enforce"}
    if _smart_inside():
        gk_py = INSTALL / "lib" / "connection-gatekeeper.py"
        if not gk_py.is_file():
            return {"ok": False, "skipped": True, "mode": "advisory"}
        try:
            proc = subprocess.run(
                [os.environ.get("NEXUS_PYTHONG", "pythong"), str(gk_py)],
                capture_output=True,
                text=True,
                timeout=12,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            return {"ok": proc.returncode == 0, "mode": "advisory", "passthrough": True}
        except (subprocess.SubprocessError, OSError) as exc:
            return {"ok": False, "error": str(exc), "mode": "advisory"}
    gk_sh = INSTALL / "lib" / "gatekeeper-enforce.sh"
    if not gk_sh.is_file():
        return {"ok": False, "skipped": True}
    try:
        subprocess.run(
            ["bash", "-c", f'source "{gk_sh}" && nexus_gatekeeper_enforce_strict'],
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        return {"ok": True}
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _bridge_field_io_packet() -> dict[str, Any]:
    io = _mod(INSTALL / "lib" / "field-io-packet.py", "field_io_packet")
    if not io or not hasattr(io, "truth_gate"):
        return {"ok": False, "skipped": True}
    try:
        return {"ok": bool(io.truth_gate().get("ok"))}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _attach_bridges() -> dict[str, Any]:
    bridges: dict[str, Any] = {}
    parallel: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_bridge_field_dns): "field_dns",
            pool.submit(_bridge_gatekeeper): "gatekeeper",
            pool.submit(_bridge_field_io_packet): "field_io_packet",
        }
        for fut in as_completed(futures):
            parallel[futures[fut]] = fut.result()
    bridges.update(parallel)
    for rel, key in (
        ("lib/connection-gatekeeper.py", "connection_gatekeeper"),
        ("lib/packet-field.py", "packet_field"),
        ("lib/trust-strike-engine.py", "trust_strike"),
        ("lib/field-attack-kit.py", "attack_kit"),
    ):
        bridges[key] = {"ok": (INSTALL / rel).is_file()}
    return bridges


def _hostile_mod() -> Any | None:
    return _mod(INSTALL / "lib" / "znetwork-hostile-threat.py", "znetwork_hostile_threat")


def _exploit_shield_mod() -> Any | None:
    return _mod(INSTALL / "lib" / "znetwork-exploit-shield.py", "znetwork_exploit_shield")


def hostile_scan(*, publish: bool = True) -> dict[str, Any]:
    mod = _hostile_mod()
    if not mod or not hasattr(mod, "scan"):
        return {"ok": False, "error": "hostile_threat_missing"}
    return mod.scan(publish=publish)


def exploit_shield_scan(*, publish: bool = True) -> dict[str, Any]:
    mod = _exploit_shield_mod()
    if not mod or not hasattr(mod, "scan"):
        return {"ok": False, "error": "exploit_shield_missing"}
    return mod.scan(publish=publish)


def exploit_shield_interdict(*, force: bool = False) -> dict[str, Any]:
    mod = _exploit_shield_mod()
    if not mod or not hasattr(mod, "interdict"):
        return {"ok": False, "error": "exploit_shield_missing"}
    report = mod.scan(publish=True) if hasattr(mod, "scan") else None
    return mod.interdict(report, force=force)


def hostile_countermeasures(*, force: bool = False) -> dict[str, Any]:
    mod = _hostile_mod()
    if not mod or not hasattr(mod, "countermeasures"):
        return {"ok": False, "error": "hostile_threat_missing"}
    report = mod.scan(publish=True) if hasattr(mod, "scan") else None
    return mod.countermeasures(report, force=force)


def retire_legacy_handlers() -> dict[str, Any]:
    mod = _handler_retire_mod()
    if not mod or not hasattr(mod, "retire_legacy_handlers"):
        return {"ok": True, "skipped": True, "reason": "handler_retire_missing"}
    return mod.retire_legacy_handlers(znetwork_active=True)


def replace_connection() -> dict[str, Any]:
    mod = _handler_retire_mod()
    if not mod or not hasattr(mod, "replace_connection"):
        return {"ok": True, "skipped": True, "reason": "handler_retire_missing"}
    return mod.replace_connection()


def tray_swap(*, force: bool = False) -> dict[str, Any]:
    """Swap taskbar tray to ZNetwork branding after successful activate."""
    doctrine = _load(DOCTRINE, {})
    swap_policy = doctrine.get("taskbar_swap") or {}
    if not swap_policy.get("on_activate", True) and not force:
        return {"ok": False, "error": "taskbar_swap_disabled"}

    doc = {
        "schema": "znetwork-tray-mode/v2",
        "mode": "znetwork",
        "app_id": swap_policy.get("app_id", "znetwork-field-panel"),
        "icon": swap_policy.get("icon", "znetwork-tray"),
        "swapped_at": _now(),
        "title": "ZNetwork — smart inside",
        "active": True,
    }
    _save(TRAY_MODE, doc)

    tray_sh = INSTALL / "lib" / "panel-tray.sh"
    if not tray_sh.is_file():
        return {"ok": False, "error": "panel_tray_missing", "tray_mode": doc}

    inner = f"""
set -euo pipefail
export NEXUS_INSTALL_ROOT={json.dumps(str(INSTALL))}
export NEXUS_STATE_DIR={json.dumps(str(STATE))}
export NEXUS_TRAY_MODE=znetwork
export NEXUS_TRAY_ICON_REFRESH=1
# shellcheck source=/dev/null
source {json.dumps(str(INSTALL / "lib" / "nexus-common.sh"))}
# shellcheck source=/dev/null
source {json.dumps(str(tray_sh))}
nexus_panel_tray_znetwork_swap
"""
    try:
        proc = subprocess.run(["bash", "-c", inner], capture_output=True, text=True, timeout=30)
        ok = proc.returncode == 0
        rep = {
            "ok": ok,
            "tray_mode": doc,
            "detail": (proc.stdout or proc.stderr or "")[:300],
        }
        _append_jsonl(LEDGER, {"event": "tray_swap", **rep, "at": _now()})
        return rep
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "error": str(exc), "tray_mode": doc}


def tray_revert() -> dict[str, Any]:
    doc = {"schema": "znetwork-tray-mode/v2", "mode": "nexus", "active": False, "reverted_at": _now()}
    _save(TRAY_MODE, doc)
    tray_sh = INSTALL / "lib" / "panel-tray.sh"
    if tray_sh.is_file():
        inner = f"""
set -euo pipefail
export NEXUS_INSTALL_ROOT={json.dumps(str(INSTALL))}
export NEXUS_STATE_DIR={json.dumps(str(STATE))}
export NEXUS_TRAY_MODE=nexus
export NEXUS_TRAY_ICON_REFRESH=1
source {json.dumps(str(INSTALL / "lib" / "nexus-common.sh"))}
source {json.dumps(str(tray_sh))}
nexus_panel_tray_znetwork_swap
"""
        subprocess.run(["bash", "-c", inner], capture_output=True, text=True, timeout=30)
    return {"ok": True, "tray_mode": doc}


def mark_running(choice: str = "yes") -> dict[str, Any]:
    mode = os.environ.get("ZNETWORK_MODE", "REVIEW_ONLY")
    doc = {
        "choice": choice,
        "running": choice == "yes",
        "mode": mode,
        "updated": _now(),
        "orchestrator": SCHEMA,
    }
    _save(OPERATOR, doc)
    STATE.mkdir(parents=True, exist_ok=True)
    if choice == "yes":
        try:
            RUNNING_MARKER.write_text(f"running=1\nupdated={_now()}\n", encoding="utf-8")
            os.chmod(RUNNING_MARKER, 0o600)
        except OSError:
            pass
    else:
        try:
            RUNNING_MARKER.unlink(missing_ok=True)
        except OSError:
            pass
    if STATUS.is_file():
        try:
            _save(SHADOW, _load(STATUS))
        except OSError:
            pass
    _append_jsonl(LEDGER, {"event": "mark_running", **doc})
    return doc


def activate(*, elevated: bool = False) -> dict[str, Any]:
    """Protection-only activate: triple check → connection snapshot → mark → tray."""
    gate = truth_gate()
    _append_jsonl(
        ACTIVATE_LOG,
        {
            "ts": _now(),
            "step": "protection_gate",
            "status": "OK" if gate.get("ok") else "PARTIAL",
            "detail": json.dumps(gate)[:400],
        },
    )

    triple = triple_check()
    if not triple.get("ok"):
        _append_jsonl(
            ACTIVATE_LOG,
            {"ts": _now(), "step": "triple_check", "status": "FAIL", "detail": json.dumps(triple)},
        )
        return {"ok": False, "error": "triple_check_failed", "triple_check": triple}

    _append_jsonl(
        ACTIVATE_LOG,
        {"ts": _now(), "step": "triple_check", "status": "OK", "detail": f"mode={triple.get('mode')}"},
    )

    replace = replace_connection()
    _append_jsonl(
        ACTIVATE_LOG,
        {
            "ts": _now(),
            "step": "connection_snapshot",
            "status": "OK" if replace.get("ok") else "PARTIAL",
            "detail": json.dumps(replace)[:400],
        },
    )

    bridges: dict[str, Any] = {"ok": True, "skipped": True, "reason": "protection_only"}
    hostile = {"ok": True, "skipped": True, "reason": "protection_only"}
    counter = {"ok": True, "skipped": True, "reason": "protection_only"}
    exploit = {"ok": True, "skipped": True, "reason": "protection_only"}
    exploit_interdict = {"ok": True, "skipped": True, "reason": "protection_only"}
    if not _protection_only():
        bridges = _attach_bridges()
        exploit = exploit_shield_scan(publish=True)
        hostile = hostile_scan(publish=True)
        if os.environ.get("ZNETWORK_RELAYER", "1") != "0":
            relayer = _mod(INSTALL / "lib" / "znetwork-relayer.py", "znetwork_relayer_orch")
            if relayer and hasattr(relayer, "retaliate_all"):
                exploit_interdict = relayer.retaliate_all(exploit if exploit.get("ok") else hostile, force=False)
            elif exploit.get("immediate_count") or exploit.get("zero_day_count"):
                exploit_interdict = exploit_shield_interdict(force=False)
        elif _smart_inside():
            if exploit.get("immediate_count") or exploit.get("zero_day_count"):
                exploit_interdict = exploit_shield_interdict(force=False)
            elif hostile.get("immediate_count"):
                counter = {"ok": True, "skipped": True, "reason": "hostile_deferred_to_exploit_shield"}
        elif hostile.get("immediate_count"):
            counter = hostile_countermeasures(force=True)

    op = mark_running("yes")
    tray = tray_swap()
    _append_jsonl(
        ACTIVATE_LOG,
        {
            "ts": _now(),
            "step": "complete",
            "status": "OK" if tray.get("ok") else "PARTIAL",
            "detail": f"running=true tray_swap={tray.get('ok')}",
        },
    )
    return {
        "ok": True,
        "protection_gate": gate,
        "triple_check": triple,
        "connection_snapshot": replace,
        "bridges": bridges,
        "exploit_shield": exploit,
        "exploit_interdict": exploit_interdict,
        "hostile_scan": hostile,
        "hostile_countermeasure": counter,
        "operator": op,
        "tray_swap": tray,
        "elevated": elevated,
        "protection_only": _protection_only(),
        "smart_inside": _smart_inside(),
        "activated_at": _now(),
    }


def _sovereignty_slice() -> dict[str, Any]:
    py = INSTALL / "lib" / "queen-ammoos-sovereignty.py"
    if not py.is_file():
        py = Path(__file__).resolve().parent / "queen-ammoos-sovereignty.py"
    mod = _mod(py, "queen_ammoos_sov_orch")
    if mod and hasattr(mod, "posture"):
        try:
            return mod.posture()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
    return {"ok": False, "skipped": True}


def _audio_dac_hook() -> dict[str, Any]:
    py = INSTALL / "lib" / "field-audio-dac-chamber.py"
    mod = _mod(py, "znet_audio_dac")
    if mod and hasattr(mod, "znetwork_hook"):
        try:
            return mod.znetwork_hook()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
    return {"ok": False, "skipped": True, "hint": "field-audio-dac-chamber.py"}


def posture() -> dict[str, Any]:
    op = _load(OPERATOR, {})
    tray = _load(TRAY_MODE, {})
    hostile_state = _load(STATE / "znetwork-hostile-state.json", {})
    sov = _sovereignty_slice()
    zn = sov.get("znetwork") or {}
    pipe = int(sov.get("internet_pipe_percent") or zn.get("internet_pipe_percent") or 0)
    audio_dac = _audio_dac_hook()
    return {
        "schema": SCHEMA,
        "ok": True,
        "operator": op,
        "status": _load(STATUS) or None,
        "tray_mode": tray,
        "truth_gate": truth_gate(),
        "hostile_threat": hostile_state or None,
        "binary": str(znetwork_bin() or ""),
        "doctrine": str(DOCTRINE),
        "sovereignty": sov,
        "audio_layer": audio_dac,
        "audio_dac": audio_dac,
        "internet_pipe_percent": pipe,
        "internet_pipe_target": int(sov.get("internet_pipe_target") or 100),
        "sole_internet_stack": True,
        "loopback_authority": sov.get("loopback_authority") or "127.0.0.1",
        "checked_at": _now(),
    }


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    elevated = "--elevated" in sys.argv or os.environ.get("NEXUS_ELEVATED_ROOT") == "1"
    handlers = {
        "json": posture,
        "status": posture,
        "truth-gate": truth_gate,
        "triple-check": triple_check,
        "activate": lambda: activate(elevated=elevated),
        "tray-swap": tray_swap,
        "tray-revert": tray_revert,
        "mark-running": lambda: mark_running("yes"),
        "retire": retire_legacy_handlers,
        "replace": replace_connection,
        "handler-retire": retire_legacy_handlers,
        "replace-connection": replace_connection,
        "hostile-scan": lambda: hostile_scan(publish=True),
        "hostile-respond": lambda: hostile_countermeasures(force="--force" in sys.argv),
        "hostile-watch": lambda: (_hostile_mod().watch() if _hostile_mod() and hasattr(_hostile_mod(), "watch") else {"ok": False}),
        "exploit-scan": lambda: exploit_shield_scan(publish=True),
        "exploit-interdict": lambda: exploit_shield_interdict(force="--force" in sys.argv),
        "exploit-watch": lambda: exploit_shield_interdict(force=False),
    }
    fn = handlers.get(mode)
    if not fn:
        print(
            "usage: znetwork-orchestrator.py [json|truth-gate|triple-check|activate|hostile-scan|hostile-respond|tray-swap|tray-revert]",
            file=sys.stderr,
        )
        return 2
    result = fn()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())