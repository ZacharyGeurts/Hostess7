#!/usr/bin/env pythong
"""NEXUS ↔ Grok16 recompile — integrate, balance combinatronics, rebuild NewLatest + Queen browser."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL / "Queen"))
DOCTRINE = INSTALL / "data" / "nexus-g16-integrate-doctrine.json"
PANEL = STATE / "nexus-g16-recompile-panel.json"
LEDGER = STATE / "nexus-g16-recompile-ledger.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def grok16_root() -> Path:
    from sg_paths import grok16_root as _gr
    return _gr()


def _import_mod(name: str, path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _comb_mod() -> Any | None:
    return _import_mod("g16_compile_combinatronics", grok16_root() / "lib" / "g16-compile-combinatronics.py")


def _balance_mod() -> Any | None:
    return _import_mod("field_combinatronic_balance", INSTALL / "lib" / "field-combinatronic-balance.py")


def _env_base() -> dict[str, str]:
    return {
        **os.environ,
        "SG_ROOT": str(SG),
        "GROK16_ROOT": str(grok16_root()),
        "G16_PREFIX": os.environ.get("G16_PREFIX", str(grok16_root())),
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "QUEEN_ROOT": str(QUEEN),
        "G16_OPTIMAL_COMBINATRONICS_AT_COMPILE": os.environ.get("G16_OPTIMAL_COMBINATRONICS_AT_COMPILE", "1"),
    }


def integrate_grok16() -> dict[str, Any]:
    """Wire SG consumers to canonical Grok16 — env, toolchain manifest, always-optimal."""
    script = grok16_root() / "scripts" / "grok16-integrate.sh"
    if not script.is_file():
        return {"ok": False, "error": "integrate_script_missing", "path": str(script)}
    env_path = grok16_root() / "data" / "grok16-integrate.env"
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            ["bash", str(script), "integrate"],
            capture_output=True,
            text=True,
            timeout=600,
            env=_env_base(),
            check=False,
            cwd=str(grok16_root()),
        )
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "ok": proc.returncode == 0,
            "action": "integrate",
            "script": str(script),
            "env": str(env_path) if env_path.is_file() else None,
            "elapsed_ms": elapsed,
            "stdout_tail": (proc.stdout or "")[-2000:],
            "stderr_tail": (proc.stderr or "")[-1000:] if proc.returncode != 0 else "",
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "action": "integrate", "error": str(exc)[:200]}


def balance_combinatronics(*, full: bool = False) -> dict[str, Any]:
    """Ensure combinatronics optimal before any compile — gate + balance refresh."""
    t0 = time.perf_counter()
    steps: list[dict[str, Any]] = []
    comb_gate: dict[str, Any] = {}
    balance_doc: dict[str, Any] = {}

    comb = _comb_mod()
    if comb and hasattr(comb, "compile_gate"):
        try:
            comb_gate = comb.compile_gate(full=full)
            steps.append({"step": "compile_gate", "ok": comb_gate.get("ok", True), "profile": comb_gate.get("profile")})
        except Exception as exc:
            steps.append({"step": "compile_gate", "ok": False, "error": str(exc)[:160]})
    else:
        steps.append({"step": "compile_gate", "ok": False, "error": "combinatronics_module_missing"})

    bal = _balance_mod()
    if bal and hasattr(bal, "gate_refresh"):
        try:
            balance_doc = bal.gate_refresh(requested_refresh=True)
            steps.append({"step": "balance_gate_refresh", "ok": balance_doc.get("ok", True)})
        except Exception as exc:
            steps.append({"step": "balance_gate_refresh", "ok": False, "error": str(exc)[:160]})

    profile = str(comb_gate.get("profile") or "")
    if not profile and comb and hasattr(comb, "resolve_compile_profile"):
        profile = str(comb.resolve_compile_profile() or "belt_2_0")

    out = {
        "schema": "nexus-g16-recompile-balance/v1",
        "updated": _now(),
        "ok": all(s.get("ok", True) for s in steps) if steps else False,
        "balanced": all(s.get("ok", True) for s in steps) if steps else False,
        "ideal_profile": profile,
        "combinatronics_gate": comb_gate,
        "combinatronic_balance": balance_doc or None,
        "steps": steps,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
        "statement": _load(DOCTRINE, {}).get("motto"),
    }
    return out


def _stamp_binary(path: Path, *, comb: dict[str, Any] | None, meta: dict[str, Any]) -> dict[str, Any]:
    comb_mod = _comb_mod()
    if not comb_mod or not hasattr(comb_mod, "stamp_compiled_artifact"):
        return {"ok": False, "skipped": "stamp_unavailable"}
    if not path.is_file():
        return {"ok": False, "error": "binary_missing", "path": str(path)}
    try:
        return comb_mod.stamp_compiled_artifact(path, comb=comb, compile_meta=meta)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160]}


def recompile_queen_browser(*, force: bool = False) -> dict[str, Any]:
    """Rebuild queen-browser via Queen forge RTX pipeline (g16 + Ninja)."""
    forge = QUEEN / "lib" / "queen-forge.py"
    if not forge.is_file():
        return {"ok": False, "error": "queen_forge_missing"}
    env = _env_base()
    prof = str(env.get("GROK16_FIELD_PROFILE") or "")
    comb = _comb_mod()
    if comb and hasattr(comb, "resolve_compile_profile"):
        resolved = comb.resolve_compile_profile(prof or None)
        if resolved:
            env["GROK16_FIELD_PROFILE"] = resolved
            env["G16_BENCH_PROFILE"] = resolved
    t0 = time.perf_counter()
    args = [sys.executable, str(forge), "run", "rtx"]
    if force:
        args.append("--force")
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=7200, env=env, check=False, cwd=str(QUEEN))
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        doc: dict[str, Any] = {"ok": proc.returncode == 0, "returncode": proc.returncode, "elapsed_ms": elapsed}
        raw = (proc.stdout or "").strip()
        if raw:
            try:
                doc["forge"] = json.loads(raw.splitlines()[-1])
            except json.JSONDecodeError:
                doc["stdout_tail"] = raw[-3000:]
        bin_candidates = [
            QUEEN / "build" / "rtx" / "bin" / "Linux" / "queen-browser",
            QUEEN / "build" / "rtx" / "bin" / "queen-browser",
            QUEEN / "build" / "bin" / "Linux" / "queen-browser",
        ]
        binary = next((p for p in bin_candidates if p.is_file()), None)
        if binary:
            doc["binary"] = str(binary)
            doc["binary_bytes"] = binary.stat().st_size
            gate = (doc.get("forge") or {}).get("combinatronics_gate") or {}
            doc["stamp"] = _stamp_binary(
                binary,
                comb=gate.get("combinatronics") if isinstance(gate, dict) else None,
                meta={"target": "queen-browser", "profile": env.get("GROK16_FIELD_PROFILE"), "elapsed_ms": elapsed},
            )
        return doc
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)[:200]}


def recompile_lib_scripts(*, force: bool = False) -> dict[str, Any]:
    """Compile hot field scripts to g16-built executables (lib/bin)."""
    mod = _import_mod("field_g16_script_compile", INSTALL / "lib" / "field-g16-script-compile.py")
    if not mod or not hasattr(mod, "compile_batch"):
        return {"ok": False, "error": "script_compile_module_missing"}
    try:
        return mod.compile_batch(force=force)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def recompile_asm_probes() -> dict[str, Any]:
    """Rebuild field-outside-asm and field-wave-asm with g16 when available."""
    results: dict[str, Any] = {"ok": True, "targets": []}
    g16 = grok16_root() / "bin" / "g16"
    comb_gate = {}
    comb = _comb_mod()
    if comb and hasattr(comb, "compile_gate"):
        try:
            comb_gate = comb.compile_gate()
        except Exception:
            pass

    for name, rel_src, rel_out in (
        ("field-outside-asm", "lib/field-outside-asm.c", "lib/bin/field-outside-asm"),
        ("field-wave-asm", "lib/field-wave-asm.c", "lib/bin/field-wave-asm"),
    ):
        src = INSTALL / rel_src
        out = INSTALL / rel_out
        row: dict[str, Any] = {"id": name, "source": str(src), "output": str(out)}
        if not src.is_file():
            row.update({"ok": False, "skipped": "source_missing"})
            results["targets"].append(row)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        compiler = str(g16) if g16.is_file() else "gcc"
        cmd = [compiler, "-std=gnu17", "-O3", "-march=native", "-fPIE", "-pie", "-o", str(out), str(src)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=_env_base(), check=False)
            row["ok"] = proc.returncode == 0 and out.is_file()
            row["compiler"] = compiler
            if not row["ok"]:
                row["stderr_tail"] = (proc.stderr or "")[-800:]
            elif out.is_file():
                row["binary_bytes"] = out.stat().st_size
                row["stamp"] = _stamp_binary(
                    out,
                    comb=comb_gate.get("combinatronics") if comb_gate else None,
                    meta={"target": name, "compiler": compiler},
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            row.update({"ok": False, "error": str(exc)[:160]})
        results["targets"].append(row)
        if not row.get("ok"):
            results["ok"] = False
    return results


def recompile_all(
    *,
    browser: bool = True,
    asm: bool = True,
    scripts: bool = True,
    integrate: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    """Full NewLatest recompile — integrate, balance, then rebuild compiled surfaces."""
    t0 = time.perf_counter()
    steps: list[dict[str, Any]] = []

    if integrate:
        integ = integrate_grok16()
        steps.append({"step": "integrate", **integ})

    bal = balance_combinatronics()
    steps.append({"step": "balance", "ok": bal.get("ok"), "ideal_profile": bal.get("ideal_profile")})

    if asm:
        asm_doc = recompile_asm_probes()
        steps.append({"step": "asm_probes", "ok": asm_doc.get("ok"), "targets": asm_doc.get("targets")})

    if scripts:
        script_doc = recompile_lib_scripts(force=force)
        steps.append({
            "step": "lib_scripts",
            "ok": script_doc.get("ok"),
            "compiled": script_doc.get("compiled"),
            "cached": script_doc.get("cached"),
            "failed": script_doc.get("failed"),
        })

    if browser:
        browser_doc = recompile_queen_browser(force=force)
        steps.append({"step": "queen_browser", "ok": browser_doc.get("ok"), "binary": browser_doc.get("binary")})

    bridge = _import_mod("nexus_g16_bridge", INSTALL / "lib" / "nexus-g16-bridge.py")
    stack: dict[str, Any] = {}
    if bridge and hasattr(bridge, "build_panel"):
        try:
            stack = bridge.build_panel(write=True)
        except Exception:
            stack = {}

    ok = bal.get("ok", False) and all(s.get("ok", True) for s in steps if s.get("step") not in ("integrate",))
    doc = {
        "schema": "nexus-g16-recompile/v1",
        "updated": _now(),
        "ok": ok,
        "balanced_at_creation": bool(bal.get("balanced")),
        "ideal_profile": bal.get("ideal_profile"),
        "combinatronics_gate": bal.get("combinatronics_gate"),
        "steps": steps,
        "stack": {"ok": stack.get("ok"), "effective_profile": (stack.get("compile") or {}).get("effective_profile")},
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
        "motto": _load(DOCTRINE, {}).get("motto"),
    }
    _save(PANEL, doc)
    _append_ledger({"ts": doc["updated"], "ok": ok, "ideal_profile": doc.get("ideal_profile"), "browser": browser})
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    force = "--force" in sys.argv
    if cmd in ("json", "panel", "status"):
        cached = _load(PANEL, {})
        if cached.get("schema") == "nexus-g16-recompile/v1":
            print(json.dumps(cached, ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(recompile_all(browser=False, asm=False, integrate=False), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("integrate",):
        print(json.dumps(integrate_grok16(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("balance", "gate"):
        full = "--full" in sys.argv
        print(json.dumps(balance_combinatronics(full=full), ensure_ascii=False, indent=2))
        return 0
    if cmd == "browser":
        bal = balance_combinatronics()
        doc = recompile_queen_browser(force=force)
        doc["balance"] = bal
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "asm":
        bal = balance_combinatronics()
        doc = recompile_asm_probes()
        doc["balance"] = bal
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd in ("scripts", "script"):
        bal = balance_combinatronics()
        doc = recompile_lib_scripts(force=force)
        doc["balance"] = bal
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd in ("recompile", "all", "full"):
        skip_browser = "--no-browser" in sys.argv
        skip_asm = "--no-asm" in sys.argv
        skip_scripts = "--no-scripts" in sys.argv
        skip_integrate = "--no-integrate" in sys.argv
        doc = recompile_all(
            browser=not skip_browser,
            asm=not skip_asm,
            scripts=not skip_scripts,
            integrate=not skip_integrate,
            force=force,
        )
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    print(json.dumps({
        "error": "usage",
        "cmds": ["json", "integrate", "balance", "browser", "asm", "scripts", "recompile"],
        "flags": ["--force", "--full", "--no-browser", "--no-asm", "--no-scripts", "--no-integrate"],
    }, ensure_ascii=False, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())