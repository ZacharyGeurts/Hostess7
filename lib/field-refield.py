#!/usr/bin/env pythong
"""Re-field — establish field shadow + protections BEFORE sovereign restore (zero loss)."""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
PANEL = STATE / "field-refield-panel.json"
SHADOW = STATE / "world-redata-shadow"

FIELD_PROMISES = [
    "Guest OS stays inside protections — non-destructive, today",
    "Shadow until reboot — canonical bytes pinned, zero loss on restore",
    "ZNetwork SHADOW — field receipts, native link stays up",
    "Triple-verify before any disk byte changes",
    "Perimeter + gatekeeper + vision assist active now",
    "Reboot into KILROY Field — syscall truth on Field Die",
]


def _now() -> str:
    try:
        import importlib.util

        py = INSTALL / "lib" / "field-sovereign-sync.py"
        spec = importlib.util.spec_from_file_location("sovereign_sync_refield", py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.utc("refield")
    except (ImportError, OSError, AttributeError):
        pass
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "sovereign_clock_refield", INSTALL / "lib" / "sovereign-clock.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.utc_z("refield")
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


def _run_py(rel: str, *args: str, timeout: int = 45) -> dict[str, Any]:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return {"ok": False, "error": f"missing:{rel}"}
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "FIELD_REFIELD_OK": "1",
        "WORLD_REDATA_SHADOW": str(SHADOW),
        "ZNETWORK_MODE": "SHADOW",
    }
    if SG.is_dir():
        env["SG_ROOT"] = str(SG)
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


def _run_bash_step(name: str, inner: str, timeout: int = 45) -> dict[str, Any]:
    script = f"""
set -euo pipefail
export NEXUS_INSTALL_ROOT={shlex.quote(str(INSTALL))}
export NEXUS_STATE_DIR={shlex.quote(str(STATE))}
export SG_ROOT={shlex.quote(str(SG if SG.is_dir() else INSTALL.parent.parent))}
export FIELD_REFIELD_OK=1
export WORLD_REDATA_SHADOW={shlex.quote(str(SHADOW))}
export ZNETWORK_MODE=SHADOW
{inner}
"""
    try:
        proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=timeout)
        return {
            "ok": proc.returncode == 0,
            "step": name,
            "detail": (proc.stdout or proc.stderr or "")[:400],
        }
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "step": name, "error": str(exc)}


def refield() -> dict[str, Any]:
    """Board field technology in SHADOW mode — required before sovereign restore."""
    steps: list[dict[str, Any]] = []

    underlay = _run_py("field-underlay.py", "json", timeout=15)
    underlay_ok = underlay.get("verdict") in ("GREEN", "PARTIAL") or bool(
        underlay.get("protections", {}).get("modules_present")
    )
    steps.append({"step": "underlay_board", "ok": underlay_ok, "result": underlay})

    hook = _run_bash_step(
        "front_hook",
        f"""
[[ -f "{INSTALL}/lib/nexus-core.sh" && -f "{INSTALL}/lib/front-hook.sh" ]] || exit 0
# shellcheck source=/dev/null
source "{INSTALL}/lib/nexus-core.sh"
source "{INSTALL}/lib/front-hook.sh"
nexus_front_hook_board
""",
    )
    steps.append(hook)

    perimeter = _run_py("field-perimeter-shield.py", "json")
    steps.append({"step": "perimeter", "ok": perimeter.get("ok", True), "result": perimeter})

    shadow_init = _run_bash_step(
        "shadow_reality",
        f"""
[[ -f "{INSTALL}/lib/nexus-core.sh" && -f "{INSTALL}/lib/shadow-reality.sh" ]] || exit 0
# shellcheck source=/dev/null
source "{INSTALL}/lib/nexus-core.sh"
source "{INSTALL}/lib/shadow-reality.sh"
nexus_shadow_init
""",
    )
    steps.append(shadow_init)

    zn = _run_bash_step(
        "znetwork_shadow",
        f"""
[[ -f "{INSTALL}/lib/nexus-core.sh" && -f "{INSTALL}/lib/znetwork-field.sh" ]] || exit 0
# shellcheck source=/dev/null
source "{INSTALL}/lib/nexus-core.sh"
source "{INSTALL}/lib/znetwork-field.sh"
export ZNETWORK_MODE=SHADOW
export NEXUS_ZNETWORK_NO_SUDO=1
nexus_znetwork_retire_legacy_handlers || true
nexus_znetwork_replace_connection || true
nexus_znetwork_triple_check || true
nexus_znetwork_user_attach || true
nexus_znetwork_write_operator yes true
""",
    )
    steps.append(zn)

    op = _run_py("field-operator.py", "board", "--no-hw-wire", timeout=15)
    steps.append({"step": "operator_iron_plate", "ok": bool(op.get("ready")), "result": op})

    wr = _world_redata_shadow_init()
    steps.append({"step": "redata_shadow_map", "ok": wr.get("ok"), "result": wr})

    ok = bool(wr.get("ok"))
    doc = {
        "schema": "field-refield/v1",
        "ts": _now(),
        "ok": ok,
        "refield_ok": ok,
        "mode": "SHADOW_UNTIL_REBOOT",
        "promises": FIELD_PROMISES,
        "shadow_root": str(SHADOW),
        "znetwork_mode": "SHADOW",
        "steps": steps,
        "underlay_verdict": underlay.get("verdict"),
        "doctrine": "Re-field before restore — field technology promises today, shadow until reboot",
    }
    _write_atomic(PANEL, doc)
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("sovereign_sync_refield_run", INSTALL / "lib" / "field-sovereign-sync.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            sync_doc = mod.sync_section("refield", "shadow")
            doc["sovereign_sync"] = sync_doc
    except (ImportError, OSError, AttributeError):
        pass
    os.environ["FIELD_REFIELD_OK"] = "1" if ok else "0"
    return doc


def _world_redata_shadow_init() -> dict[str, Any]:
    wr = SG / "World_Redata"
    if not (wr / "redata" / "shadow_map.py").is_file():
        wr = SG.parent / "World_Redata"
    mod = wr / "redata" / "shadow_map.py"
    if not mod.is_file():
        SHADOW.mkdir(parents=True, exist_ok=True)
        (SHADOW / "field-refield.ok").write_text(_now() + "\n", encoding="utf-8")
        return {"ok": True, "shadow_root": str(SHADOW), "fallback": True}
    env = {
        **os.environ,
        "PYTHONPATH": str(wr),
        "NEXUS_STATE_DIR": str(STATE),
        "WORLD_REDATA_SHADOW": str(SHADOW),
        "FIELD_REFIELD_OK": "1",
    }
    code = f"""
import json
from redata.shadow_map import init_shadow
promises = {json.dumps(FIELD_PROMISES)}
print(json.dumps(init_shadow(promises=promises)))
"""
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            cwd=str(wr),
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return {"ok": False, "error": (proc.stderr or "shadow_init_failed")[:300]}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def posture() -> dict[str, Any]:
    doc = _load(PANEL, {"schema": "field-refield/v1"})
    if not doc.get("ts"):
        doc = {"schema": "field-refield/v1", "refield_ok": False, "promises": FIELD_PROMISES}
    doc["shadow_status"] = _shadow_status_quick()
    return doc


def _shadow_status_quick() -> dict[str, Any]:
    wr = SG / "World_Redata"
    if not (wr / "redata" / "shadow_map.py").is_file():
        wr = SG.parent / "World_Redata"
    if not (wr / "redata" / "shadow_map.py").is_file():
        return {"pinned_files": 0, "refield_active": (SHADOW / "field-refield.ok").is_file()}
    env = {**os.environ, "PYTHONPATH": str(wr), "WORLD_REDATA_SHADOW": str(SHADOW)}
    code = "import json; from redata.shadow_map import shadow_status; print(json.dumps(shadow_status()))"
    try:
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=15, env=env)
        return json.loads(proc.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return {}


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if mode == "refield":
        result = refield()
    elif mode in ("json", "status"):
        result = posture()
    else:
        print("usage: field-refield.py [json|refield]", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", result.get("refield_ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())