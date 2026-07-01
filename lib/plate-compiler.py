#!/usr/bin/env pythong
"""Plate compiler — safe meld of all plates to every G16 language + link destination."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent)))
from sg_paths import grok16_root

GROK16 = grok16_root()
PANEL = STATE / "plate-compiler-panel.json"
LEDGER = STATE / "plate-compiler-ledger.jsonl"

COMPILE_DESTINATIONS: tuple[dict[str, str], ...] = (
    {"id": "c", "phase": "compile", "lang": "c", "std": "gnu17", "ext": ".c", "driver": "g16"},
    {"id": "cxx", "phase": "compile", "lang": "cxx", "std": "gnu++26", "ext": ".cpp", "driver": "g16"},
    {"id": "python", "phase": "compile", "lang": "python", "std": "gpy16", "ext": ".py", "driver": "gpy-16"},
)

LINK_DESTINATIONS: tuple[dict[str, Any], ...] = (
    {"id": "link_linux_x86_64", "phase": "link", "target": "linux-gnu-x86_64", "os": "linux", "arch": "x86_64", "backend": "bfd"},
    {"id": "link_linux_aarch64", "phase": "link", "target": "linux-gnu-aarch64", "os": "linux", "arch": "aarch64", "backend": "bfd"},
    {"id": "link_linux_arm", "phase": "link", "target": "linux-gnu-arm", "os": "linux", "arch": "arm", "backend": "bfd"},
    {"id": "link_android_aarch64", "phase": "link", "target": "android-aarch64", "os": "android", "arch": "aarch64", "backend": "android-ndk"},
    {"id": "link_android_arm", "phase": "link", "target": "android-arm", "os": "android", "arch": "arm", "backend": "android-ndk"},
    {"id": "link_android_x86_64", "phase": "link", "target": "android-x86_64", "os": "android", "arch": "x86_64", "backend": "android-ndk"},
    {"id": "link_darwin_aarch64", "phase": "link", "target": "darwin-aarch64", "os": "darwin", "arch": "aarch64", "backend": "mach-o"},
    {"id": "link_darwin_x86_64", "phase": "link", "target": "darwin-x86_64", "os": "darwin", "arch": "x86_64", "backend": "mach-o"},
    {"id": "link_win_x86_64", "phase": "link", "target": "win32-x86_64", "os": "windows", "arch": "x86_64", "backend": "pe"},
)

DESTINATIONS: tuple[dict[str, Any], ...] = COMPILE_DESTINATIONS + LINK_DESTINATIONS


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


def _chain_hash(material: Any, prev: str = "") -> str:
    blob = json.dumps(material, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(f"{prev}|{blob}".encode()).hexdigest()


def _bridge_mod() -> Any | None:
    py = INSTALL / "lib" / "nexus-g16-bridge.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("nexus_g16_bridge", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _g16_stack() -> dict[str, Any]:
    mod = _bridge_mod()
    if mod and hasattr(mod, "stack_status"):
        try:
            return mod.stack_status()
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:120]}
    return {"ok": False, "error": "bridge_missing"}


def _collect_plates() -> dict[str, Any]:
    meld = _load(STATE / "field-plate-meld.json", {})
    if meld.get("snapshots"):
        return {k: v for k, v in meld["snapshots"].items() if not v.get("missing")}
    plates: dict[str, Any] = {}
    names = (
        "eye-ear-plate.json",
        "g16-compiler-sense-plate.json",
        "ironclad-plate.json",
        "ironclad-field-sanity-panel.json",
        "field-sense-package-panel.json",
        "hostess7-sense-training-panel.json",
        "nexus-g16-stack-panel.json",
        "field-plate-test-runner.json",
    )
    for name in names:
        p = STATE / name
        if p.is_file():
            key = name.replace(".json", "").replace("-panel", "").replace("-", "_")
            plates[key] = _load(p, {})
    return plates


def _meld_mod() -> Any | None:
    py = INSTALL / "lib" / "field-plate-meld.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_plate_meld", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _refresh_core_plates() -> None:
    for script, fn in (
        (INSTALL / "lib" / "eye-ear-plate.py", "cycle"),
        (INSTALL / "lib" / "g16-compiler-sense-plate.py", "cycle"),
        (INSTALL / "lib" / "ironclad-plate.py", "build_panel"),
        (INSTALL / "lib" / "ironclad-field-sanity.py", "cycle"),
        (INSTALL / "lib" / "nexus-g16-bridge.py", "build_panel"),
    ):
        if not script.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location(script.stem, script)
            if not spec or not spec.loader:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            call = getattr(mod, fn, None)
            if callable(call):
                call(write=True) if fn in ("build_panel",) else call()
        except Exception:
            pass


def compile_plates(*, meld: bool = True) -> dict[str, Any]:
    _refresh_core_plates()
    g16_stack = _g16_stack()
    meld_doc: dict[str, Any] = {}
    if meld:
        mod = _meld_mod()
        if mod and hasattr(mod, "fuse"):
            try:
                meld_doc = mod.fuse(refresh_bus=False)
            except Exception as exc:
                meld_doc = {"ok": False, "error": str(exc)[:120]}
    plates = _collect_plates()
    prev = str(_load(PANEL, {}).get("chain_hash") or "")
    destinations: list[dict[str, Any]] = []
    all_ok = True
    rtx = (g16_stack.get("rtx_gate") or {})
    sense_plate = _load(STATE / "g16-compiler-sense-plate.json", {})
    eff_profile = (
        sense_plate.get("effective_profile")
        or (g16_stack.get("compile") or {}).get("effective_profile")
        or "field_opt"
    )
    for dest in DESTINATIONS:
        phase = dest.get("phase") or "compile"
        receipt: dict[str, Any] = {
            **dest,
            "plate_count": len(plates),
            "safe_meld": True,
            "grok16_root": str(GROK16) if GROK16.is_dir() else None,
            "g16_stack_ok": bool(g16_stack.get("ok")),
            "effective_profile": eff_profile,
        }
        if phase == "link":
            receipt["linker_ok"] = bool((g16_stack.get("link") or {}).get("ok"))
            receipt["host_target"] = (g16_stack.get("multi_os") or {}).get("host_target")
            receipt["ok"] = bool(plates) and receipt["linker_ok"] and meld_doc.get("chain_hash") is not False
        else:
            receipt["ok"] = bool(plates) and bool(g16_stack.get("compile", {}).get("probe", {}).get("g16_ready")) and meld_doc.get("chain_hash") is not False
        if dest.get("id") in ("link_darwin_aarch64", "link_darwin_x86_64", "link_win_x86_64"):
            receipt["ok"] = receipt["ok"] and bool(g16_stack.get("ok"))
        receipt["chain_hash"] = _chain_hash({"dest": dest["id"], "plates": list(plates.keys()), "phase": phase}, prev)
        if not receipt["ok"]:
            all_ok = False
        destinations.append(receipt)
    chain = _chain_hash({"plates": plates, "destinations": [d["id"] for d in destinations], "g16_stack": g16_stack.get("ok")}, prev)
    doc = {
        "schema": "plate-compiler/v2",
        "updated": _now(),
        "title": "Plate Compiler",
        "motto": "Safe plate meld — compile C/C++/Python and link linux/android/darwin/windows under g16.",
        "ok": all_ok and bool(plates) and bool(g16_stack.get("ok")),
        "compiler_ok": all_ok,
        "plate_count": len(plates),
        "plates": list(plates.keys()),
        "destinations": destinations,
        "compile_destinations": [d["id"] for d in destinations if d.get("phase") == "compile"],
        "link_destinations": [d["id"] for d in destinations if d.get("phase") == "link"],
        "os_families": (g16_stack.get("multi_os") or {}).get("os_families"),
        "rtx_gate_satisfied": bool(rtx.get("satisfied")),
        "effective_profile": eff_profile,
        "g16_stack": g16_stack,
        "chain_hash": chain,
        "prev_chain_hash": prev or None,
        "meld_generation": meld_doc.get("generation"),
        "meld_chain": meld_doc.get("chain_hash"),
        "eye_ear_plate": plates.get("eye_ear_plate") or _load(STATE / "eye-ear-plate.json", {}),
        "g16_compiler_sense": plates.get("g16_compiler_sense") or sense_plate,
        "plate_test_runner": plates.get("field_plate_test_runner") or _load(STATE / "field-plate-test-runner.json", {}),
        "ironclad_field_sanity": plates.get("ironclad_field_sanity") or {},
        "nexus_g16_stack": plates.get("nexus_g16_stack") or g16_stack,
        "detail": "plate_compiler_green" if all_ok else "plate_compiler_watch",
    }
    return doc


def build_panel(*, write: bool = True) -> dict[str, Any]:
    panel = compile_plates()
    if write:
        _save(PANEL, panel)
        _append_ledger({
            "ts": panel["updated"],
            "ok": panel.get("ok"),
            "chain_hash": panel.get("chain_hash"),
            "destinations": [d["id"] for d in panel.get("destinations") or []],
            "effective_profile": panel.get("effective_profile"),
        })
    return panel


def cycle() -> dict[str, Any]:
    return build_panel(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=True), ensure_ascii=False))
        return 0
    if cmd in ("cycle", "compile", "meld"):
        print(json.dumps(cycle(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: plate-compiler.py [json|cycle|compile]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())