#!/usr/bin/env pythong
"""NEXUS ↔ Grok16 bridge — optimize NewLatest through g16 compile + link + RTX gate."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "nexus-g16-compile-doctrine.json"
PANEL = STATE / "nexus-g16-stack-panel.json"
LEDGER = STATE / "nexus-g16-stack-ledger.jsonl"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



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
    try:
        sys.path.insert(0, str(INSTALL / "lib"))
        from sg_paths import grok16_root as _gr  # type: ignore

        return _gr()
    except Exception:
        pass
    for candidate in (INSTALL / "Grok16", INSTALL.parent / "Grok16"):
        if candidate.is_dir() and (candidate / "bin" / "g16").is_file():
            return candidate
    env = os.environ.get("GROK16_ROOT", "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    return INSTALL / "Grok16"


def _g16_script(name: str) -> Path:
    return grok16_root() / "forge" / name


def _run_gpy(script: Path, *args: str, timeout: int = 25) -> dict[str, Any]:
    gpy = os.environ.get("GPY16_DRIVER", "").strip()
    if not gpy:
        for candidate in (
            grok16_root().parent / "GrokPy" / "bin" / "gpy-16",
            INSTALL.parent.parent / "GrokPy" / "bin" / "gpy-16",
            INSTALL.parent.parent / "PythonG" / "bin" / "pythong",
        ):
            if candidate.is_file():
                gpy = str(candidate)
                break
    if not gpy or not script.is_file():
        return {"ok": False, "error": "gpy_or_script_missing"}
    env = {
        **os.environ,
        "GROK16_ROOT": str(grok16_root()),
        "GROK16_SG_ROOT": os.environ.get("SG_ROOT", str(INSTALL.parent.parent)),
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
    }
    try:
        proc = subprocess.run(
            [gpy, str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if not raw:
            return {"ok": False, "error": (proc.stderr or "empty")[:200]}
        doc = json.loads(raw)
        if isinstance(doc, dict):
            doc.setdefault("ok", proc.returncode == 0)
        return doc if isinstance(doc, dict) else {"ok": False, "error": "bad_json"}
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _probe_g16() -> dict[str, Any]:
    g16 = grok16_root() / "bin" / "g16"
    ld = grok16_root() / "bin" / "g16-ld"
    out: dict[str, Any] = {
        "grok16_root": str(grok16_root()),
        "g16": str(g16),
        "g16_ld": str(ld),
        "g16_ready": g16.is_file(),
        "linker_ready": ld.is_file(),
        "version": None,
        "discern": {},
    }
    if g16.is_file():
        try:
            proc = subprocess.run([str(g16), "--version"], capture_output=True, text=True, timeout=12, check=False)
            if proc.returncode == 0:
                out["version"] = proc.stdout.strip().split("\n")[0]
        except OSError:
            pass
        for args, expect in (
            (["foo.c"], "c"),
            (["foo.cpp"], "cxx"),
            (["-c", "pass"], "python"),
        ):
            try:
                proc = subprocess.run(
                    [str(g16), "--g16-discern", *args],
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False,
                )
                out["discern"][expect] = proc.returncode == 0 and proc.stdout.strip() == expect
            except OSError:
                pass
    out["discern_ok"] = sum(1 for v in out["discern"].values() if v)
    out["ok"] = bool(out["g16_ready"] and out["discern_ok"] >= 2)
    return out


def linker_status() -> dict[str, Any]:
    doc = _run_gpy(_g16_script("g16-linker.py"), "slice")
    targets = _run_gpy(_g16_script("g16-linker.py"), "targets")
    return {
        "ok": bool(doc.get("pass_ok") or doc.get("absorbed")),
        "slice": doc,
        "targets_total": len((targets.get("targets") or [])),
        "os_families": sorted({str(t.get("os")) for t in (targets.get("targets") or []) if t.get("os")}),
        "host_target": targets.get("host"),
    }


def rtx_gate_status() -> dict[str, Any]:
    doc = _run_gpy(_g16_script("rtx_gate.py"), "json")
    doctrine = _load(grok16_root() / "data" / "g16-rtx-gate.json", {})
    return {
        "ok": True,
        "satisfied": bool(doc.get("satisfied")),
        "forced": bool(doc.get("forced")),
        "rtx_count": int(doc.get("rtx_count") or 0),
        "gpus": doc.get("rtx_gpus") or doc.get("gpus") or [],
        "profiles_gated": doctrine.get("profiles_gated") or ["queen_rtx", "vulkan_rtx"],
        "fallback_profile": doctrine.get("fallback_profile") or "field_opt",
        "panel": doc,
    }


def ironclad_sanity_status() -> dict[str, Any]:
    doc = _run_gpy(grok16_root() / "forge" / "g16-ironclad.py", "slice")
    fs = _run_gpy(grok16_root() / "forge" / "g16-field-sanity.py", "slice")
    return {
        "ok": bool(doc.get("absorbed")) and bool(fs.get("ok")),
        "ironclad": doc,
        "field_sanity": fs,
        "meld_citation": doc.get("meld_citation") or "ironclad:meld:2",
        "citation": fs.get("citation") or doc.get("citation"),
    }


def profile_allowed(profile: str) -> bool:
    doctrine = _load(DOCTRINE, {})
    gated = set(doctrine.get("compile", {}).get("profiles_rtx_gated") or ["queen_rtx", "vulkan_rtx"])
    if profile not in gated:
        return True
    if os.environ.get("G16_RTX_GATE_FORCE", "").strip().lower() in ("1", "true", "yes"):
        return True
    return bool(rtx_gate_status().get("satisfied"))


def _sense_plate_profile() -> str | None:
    sense_plate = _load(STATE / "g16-compiler-sense-plate.json", {})
    prof = str(sense_plate.get("effective_profile") or (sense_plate.get("optimize") or {}).get("profile") or "").strip()
    return prof or None


def _combinatronics_profile(requested: str | None = None) -> str | None:
    comb = grok16_root() / "lib" / "g16-compile-combinatronics.py"
    if not comb.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("g16_compile_combinatronics", comb)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "resolve_compile_profile"):
            prof = str(mod.resolve_compile_profile(requested) or "").strip()
            return prof or None
    except Exception:
        pass
    return None


def effective_profile(requested: str | None = None) -> str:
    comb_prof = _combinatronics_profile(requested)
    env_prof = (requested or os.environ.get("GROK16_FIELD_PROFILE") or "").strip()
    sense_prof = _sense_plate_profile() if os.environ.get("NEXUS_G16_SENSE_PLATE", "1") == "1" else None
    req = comb_prof or env_prof or sense_prof or "field_opt"
    if profile_allowed(req):
        return req
    return str(_load(DOCTRINE, {}).get("compile", {}).get("profile_default") or "field_opt")


def _grok16_distro_version() -> str:
    for path in (grok16_root() / "data" / "grok16-version.json",):
        doc = _load(path, {})
        if doc.get("distro_version"):
            return str(doc["distro_version"])
    return "unknown"


def _grok15_status() -> dict[str, Any]:
    path = INSTALL / "Grok16" / "lib" / "grok15-language-core.py"
    if not path.is_file():
        return {"ok": False, "error": "grok15_missing"}
    spec = importlib.util.spec_from_file_location("grok15_bridge", path)
    if not spec or not spec.loader:
        return {"ok": False, "error": "grok15_load_failed"}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "posture"):
        return mod.posture()
    return {"ok": False, "error": "posture_unavailable"}


def _secure_chamber_status() -> dict[str, Any]:
    path = INSTALL / "lib" / "g16-secure-chamber.py"
    if not path.is_file():
        return {"ok": False, "error": "secure_chamber_missing"}
    spec = importlib.util.spec_from_file_location("g16_secure_chamber_bridge", path)
    if not spec or not spec.loader:
        return {"ok": False, "error": "secure_chamber_load_failed"}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "posture"):
        return mod.posture()
    return {"ok": False, "error": "posture_unavailable"}


def stack_status() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    probe = _probe_g16()
    linker = linker_status()
    rtx = rtx_gate_status()
    iron = ironclad_sanity_status()
    secure = _secure_chamber_status()
    grok15 = _grok15_status()
    req_profile = os.environ.get("GROK16_FIELD_PROFILE", "") or _sense_plate_profile() or "field_opt"
    eff = effective_profile(req_profile)
    sense_plate = _load(STATE / "g16-compiler-sense-plate.json", {})
    optimized = bool(
        probe.get("ok")
        and linker.get("ok")
        and iron.get("ok")
        and (eff != "queen_rtx" or rtx.get("satisfied"))
    )
    return {
        "schema": "nexus-g16-stack/v1",
        "updated": _now(),
        "title": "NEXUS G16 Stack",
        "motto": doctrine.get("motto"),
        "grok16_root": str(grok16_root()),
        "distro_version": _grok16_distro_version(),
        "ammoos_pairing": _load(INSTALL / "data" / "ammoos-version.json", {}).get("g16_pairing"),
        "ok": optimized,
        "optimized": optimized,
        "compile": {
            "driver": "g16",
            "cxx_std": doctrine.get("compile", {}).get("cxx_std", "gnu++26"),
            "c_std": doctrine.get("compile", {}).get("c_std", "gnu17"),
            "requested_profile": req_profile,
            "effective_profile": eff,
            "rtx_gated": req_profile in set(rtx.get("profiles_gated") or []),
            "probe": probe,
        },
        "link": linker,
        "rtx_gate": rtx,
        "ironclad_sanity": iron,
        "compiler_sense_plate": {
            "ok": bool(sense_plate.get("ok")),
            "effective_profile": sense_plate.get("effective_profile"),
            "sense_score": sense_plate.get("sense_score"),
            "eye_ok": (sense_plate.get("eye_ear_plate") or {}).get("eye_ok"),
            "ear_ok": (sense_plate.get("eye_ear_plate") or {}).get("ear_ok"),
            "mouth_ok": (sense_plate.get("eye_ear_plate") or {}).get("mouth_ok"),
        },
        "multi_os": {
            "targets": linker.get("targets_total"),
            "os_families": linker.get("os_families"),
            "host_target": linker.get("host_target"),
        },
        "secure_chamber": secure,
        "grok15_language_core": grok15,
        "user_code_languages": (doctrine.get("compile") or {}).get("user_code_languages") or [],
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    panel = stack_status()
    panel["panel_schema"] = "nexus-g16-stack-panel/v1"
    if write:
        _save(PANEL, panel)
        _append_ledger({
            "ts": panel.get("updated"),
            "ok": panel.get("ok"),
            "effective_profile": (panel.get("compile") or {}).get("effective_profile"),
            "targets": (panel.get("multi_os") or {}).get("targets"),
        })
    return panel


def meld_slice() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema") == "nexus-g16-stack/v1":
        return {
            "id": "nexus_g16_stack",
            "absorbed": bool(cached.get("ok")),
            "optimized": bool(cached.get("optimized")),
            "effective_profile": (cached.get("compile") or {}).get("effective_profile"),
            "targets": (cached.get("multi_os") or {}).get("targets"),
            "rtx_satisfied": (cached.get("rtx_gate") or {}).get("satisfied"),
            "updated": cached.get("updated"),
        }
    doc = build_panel(write=True)
    return meld_slice()


def combinatronics_gate(*, full: bool = False) -> dict[str, Any]:
    comb = grok16_root() / "lib" / "g16-compile-combinatronics.py"
    if not comb.is_file():
        return {"ok": False, "error": "combinatronics_missing"}
    try:
        spec = importlib.util.spec_from_file_location("g16_compile_combinatronics", comb)
        if not spec or not spec.loader:
            return {"ok": False, "error": "combinatronics_load_failed"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "compile_gate"):
            return mod.compile_gate(full=full)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}
    return {"ok": False, "error": "compile_gate_missing"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd in ("balance", "combinatronics", "gate"):
        recompile = INSTALL / "lib" / "nexus-g16-recompile.py"
        if recompile.is_file():
            try:
                proc = subprocess.run(
                    [sys.executable, str(recompile), "balance"],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
                    check=False,
                )
                if proc.stdout.strip():
                    print(proc.stdout.strip())
                    return 0 if proc.returncode == 0 else 1
            except (OSError, subprocess.TimeoutExpired):
                pass
        print(json.dumps(combinatronics_gate(full="--full" in sys.argv), ensure_ascii=False))
        return 0
    if cmd in ("integrate", "recompile"):
        recompile = INSTALL / "lib" / "nexus-g16-recompile.py"
        if not recompile.is_file():
            print(json.dumps({"ok": False, "error": "nexus_g16_recompile_missing"}, ensure_ascii=False))
            return 1
        sub = "integrate" if cmd == "integrate" else "recompile"
        proc = subprocess.run(
            [sys.executable, str(recompile), sub, *sys.argv[2:]],
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            check=False,
        )
        return proc.returncode
    if cmd == "probe":
        print(json.dumps(_probe_g16(), ensure_ascii=False))
        return 0
    if cmd == "linker":
        print(json.dumps(linker_status(), ensure_ascii=False))
        return 0
    if cmd == "rtx":
        print(json.dumps(rtx_gate_status(), ensure_ascii=False))
        return 0
    if cmd == "profile" and len(sys.argv) > 2:
        p = sys.argv[2]
        print(json.dumps({"profile": p, "allowed": profile_allowed(p), "effective": effective_profile(p)}, ensure_ascii=False))
        return 0 if profile_allowed(p) or p not in ("queen_rtx", "vulkan_rtx") else 1
    if cmd == "slice":
        print(json.dumps(meld_slice(), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["json", "probe", "linker", "rtx", "profile NAME", "slice", "balance", "integrate", "recompile"],
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())