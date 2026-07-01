"""Queen file inspection — disambiguate extensions and similarly named files."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SPIRV_MAGIC = 0x07230203
LAUNCH_SCHEMA_MARKERS = (b'"schema": "queen-launch/v1"', b'"schema":"queen-launch/v1"')

QUEEN = Path(__file__).resolve().parents[1]
_CHAMBER = None


def _chamber_mod():
    global _CHAMBER
    if _CHAMBER is not None:
        return _CHAMBER
    import importlib.util
    spec = importlib.util.spec_from_file_location("queen_launch_chamber", QUEEN / "lib" / "queen-launch-chamber.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _CHAMBER = mod
    return mod
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
REGISTRY_PATH = QUEEN / "data" / "queen-file-types.json"
ICON_OVERRIDES_PATH = STATE / "queen-file-icon-overrides.json"
TYPE_PREFS_PATH = STATE / "queen-file-type-prefs.json"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_registry(path: Path | None = None) -> dict[str, Any]:
    reg_path = path or REGISTRY_PATH
    try:
        return json.loads(reg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "queen-file-types/v1", "types": {}, "default_icons": {}}


def load_type_prefs() -> dict[str, Any]:
    try:
        doc = json.loads(TYPE_PREFS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        doc = {}
    if doc.get("schema") != "queen-file-type-prefs/v1":
        doc = {"schema": "queen-file-type-prefs/v1", "updated": _ts(), "types": {}, "bar_pins": []}
    doc.setdefault("types", {})
    doc.setdefault("bar_pins", [])
    return doc


def _save_type_prefs(doc: dict[str, Any]) -> dict[str, Any]:
    doc["schema"] = "queen-file-type-prefs/v1"
    doc["updated"] = _ts()
    TYPE_PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = TYPE_PREFS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(TYPE_PREFS_PATH)
    return doc


def set_type_pref(type_id: str, key: str, value: Any) -> dict[str, Any]:
    doc = load_type_prefs()
    row = doc["types"].setdefault(type_id, {})
    if value is None or value == "":
        row.pop(key, None)
        if not row:
            doc["types"].pop(type_id, None)
    else:
        row[key] = value
    return _save_type_prefs(doc)


def set_bar_pins(pins: list[str]) -> dict[str, Any]:
    doc = load_type_prefs()
    doc["bar_pins"] = [str(x) for x in pins if x][:24]
    return _save_type_prefs(doc)


def load_icon_overrides() -> dict[str, Any]:
    try:
        doc = json.loads(ICON_OVERRIDES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        doc = {}
    if doc.get("schema") != "queen-file-icon-overrides/v1":
        doc = {"schema": "queen-file-icon-overrides/v1", "updated": _ts(), "by_type": {}, "by_path": {}}
    doc.setdefault("by_type", {})
    doc.setdefault("by_path", {})
    return doc


def _save_icon_overrides(doc: dict[str, Any]) -> dict[str, Any]:
    doc["schema"] = "queen-file-icon-overrides/v1"
    doc["updated"] = _ts()
    ICON_OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = ICON_OVERRIDES_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(ICON_OVERRIDES_PATH)
    return doc


def save_icon_override(
    *,
    scope: str,
    key: str,
    program_icon: str | None,
) -> dict[str, Any]:
    doc = load_icon_overrides()
    bucket = "by_path" if scope == "path" else "by_type"
    if not program_icon:
        doc[bucket].pop(key, None)
    else:
        doc[bucket][key] = {"program_icon": program_icon}
    return _save_icon_overrides(doc)


def file_types_registry() -> dict[str, Any]:
    reg = _load_registry()
    overrides = load_icon_overrides()
    prefs = load_type_prefs()
    types_out: dict[str, Any] = {}
    for tid, spec in (reg.get("types") or {}).items():
        ov = overrides.get("by_type", {}).get(tid) or {}
        user = prefs.get("types", {}).get(tid) or {}
        action = user.get("action") or spec.get("action")
        open_with = user.get("open_with") or spec.get("open_with")
        compileable = user.get("compileable") if "compileable" in user else bool(spec.get("compileable"))
        types_out[tid] = {
            "label": spec.get("label") or tid,
            "extensions": spec.get("extensions") or [],
            "name_patterns": spec.get("name_patterns") or [],
            "compileable": compileable,
            "global_icon": spec.get("global_icon"),
            "program_icon": ov.get("program_icon") or spec.get("program_icon"),
            "action": action,
            "open_with": open_with,
            "icon_asset": spec.get("icon_asset"),
            "mime": spec.get("mime"),
            "inspect": spec.get("inspect"),
            "flags": {
                "compileable": compileable,
                "launchable": action in ("run_launchable", "launch_spv", "run_launch"),
                "open_code": action == "open_code",
                "open_tab": action == "open_tab",
                "preview": user.get("preview", True) is not False,
                "inspect": user.get("inspect", True) is not False,
                "on_bar": tid in (prefs.get("bar_pins") or []),
                "hidden": user.get("hidden") is True,
            },
            "settings": {
                "action": action,
                "open_with": open_with,
                "program_icon": ov.get("program_icon") or spec.get("program_icon"),
                "user_overrides": user,
            },
        }
    return {
        "schema": reg.get("schema", "queen-file-types/v1"),
        "types": types_out,
        "type_count": len(types_out),
        "default_icons": reg.get("default_icons") or {},
        "icon_overrides": {
            "by_type": overrides.get("by_type") or {},
            "by_path": overrides.get("by_path") or {},
        },
        "type_prefs": {
            "bar_pins": prefs.get("bar_pins") or [],
            "types": prefs.get("types") or {},
        },
    }


def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _match_name_patterns(name: str, registry: dict[str, Any]) -> str | None:
    norm = _norm_name(name)
    for tid, spec in (registry.get("types") or {}).items():
        for pat in spec.get("name_patterns") or []:
            pat_norm = _norm_name(pat)
            if pat_norm == norm or pat_norm in norm:
                return tid
    return None


def _match_extension(ext: str, registry: dict[str, Any]) -> str | None:
    ext = (ext or "").lower()
    if not ext.startswith("."):
        ext = f".{ext}" if ext else ""
    for tid, spec in (registry.get("types") or {}).items():
        for e in spec.get("extensions") or []:
            if e.lower() == ext:
                return tid
    return None


def _read_header(path: Path, n: int = 512) -> bytes:
    try:
        with path.open("rb") as f:
            return f.read(n)
    except OSError:
        return b""


def _resolve_icon(
    *,
    path: Path,
    type_id: str,
    ext: str,
    kind: str,
    spec: dict[str, Any],
    registry: dict[str, Any],
    overrides: dict[str, Any],
) -> tuple[str, str | None, str | None]:
    defaults = registry.get("default_icons") or {}
    kind_icons = defaults.get(kind, defaults.get("file", {}))
    global_icon = spec.get("global_icon") or kind_icons.get("global") or "📄"
    program_icon = spec.get("program_icon")

    by_path = overrides.get("by_path") or {}
    by_type = overrides.get("by_type") or {}
    path_key = str(path)
    if path_key in by_path and by_path[path_key].get("program_icon"):
        program_icon = by_path[path_key]["program_icon"]
    elif type_id in by_type and by_type[type_id].get("program_icon"):
        program_icon = by_type[type_id]["program_icon"]
    elif ext in by_type and by_type[ext].get("program_icon"):
        program_icon = by_type[ext]["program_icon"]

    icon = program_icon or global_icon
    return icon, global_icon, program_icon


def inspect_file(
    path: Path,
    *,
    registry_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify file with extension + content sniff + name patterns."""
    registry = _load_registry(registry_path)
    ov_doc = overrides if overrides is not None else load_icon_overrides()

    kind = "unknown"
    if path.is_dir():
        kind = "dir"
    elif path.is_symlink():
        kind = "symlink"
    elif path.is_file():
        kind = "file"

    type_id = "unknown"
    confidence = 0.3
    hints: list[str] = []
    ext = path.suffix.lower()

    chamber_hint: dict[str, Any] | None = None
    if kind == "dir":
        ch = _chamber_mod()
        if ch:
            chamber_hint = ch.inspect_launch_path(path)
        if chamber_hint:
            type_id = chamber_hint.get("type_id") or "code_chamber"
            confidence = 0.97
            hints.append("chamber:code_folder")
        else:
            type_id = "dir"
            confidence = 1.0
    elif kind == "file":
        named = _match_name_patterns(path.name, registry)
        if named:
            type_id = named
            confidence = 0.92
            hints.append(f"name:{named}")

        if ext == ".launch":
            type_id = "launch"
            confidence = 0.95
            hints.append("ext:.launch")

        ext_match = _match_extension(ext, registry)
        if ext_match and confidence < 0.9:
            type_id = ext_match
            confidence = 0.75
            hints.append(f"ext:{ext}")

        header = _read_header(path)
        if ext == ".launch" and any(m in header for m in LAUNCH_SCHEMA_MARKERS):
            type_id = "launch"
            confidence = 1.0
            hints.append("sniff:queen-launch")
        if len(header) >= 4:
            magic = int.from_bytes(header[:4], "little")
            if header[:4] == b"\x7fELF":
                type_id = "elf"
                confidence = 1.0
                hints.append("magic:ELF")
            elif header[:2] == b"MZ":
                type_id = "pe_exe"
                confidence = 0.98
                hints.append("magic:PE")
            elif magic == SPIRV_MAGIC:
                type_id = "spirv"
                confidence = 1.0
                hints.append("magic:SPIR-V")
            elif ext == ".comp" or type_id in ("glsl_comp", "queen_boot_comp", "aos_load_comp"):
                text = header.decode("utf-8", errors="ignore")
                if any(tok in text for tok in ("#version", "layout(", "void main")):
                    if type_id == "unknown":
                        type_id = "glsl_comp"
                    confidence = max(confidence, 0.96)
                    hints.append("sniff:glsl_compute")
                elif b"\x00" in header[:32]:
                    type_id = "binary"
                    confidence = max(confidence, 0.8)
                    hints.append("sniff:binary_comp")
            elif ext == ".json":
                if header.lstrip()[:1] in (b"{", b"["):
                    type_id = "json"
                    confidence = max(confidence, 0.9)
                    hints.append("sniff:json")
            elif ext in (".png",):
                if header[:8] == b"\x89PNG\r\n\x1a\n":
                    type_id = "image"
                    confidence = 1.0
                    hints.append("magic:PNG")
            elif ext in (".jpg", ".jpeg"):
                if header[:3] == b"\xff\xd8\xff":
                    type_id = "image"
                    confidence = 1.0
                    hints.append("magic:JPEG")

        if type_id == "unknown" and ext_match:
            type_id = ext_match
            confidence = 0.7

        if type_id == "launch" and ext == ".launch":
            ch = _chamber_mod()
            if ch:
                launch_hint = ch.inspect_launch_path(path)
                if launch_hint:
                    chamber_hint = launch_hint
                    confidence = max(confidence, 0.98)

    types = registry.get("types") or {}
    if chamber_hint:
        spec = {**types.get(type_id, {}), **chamber_hint}
    elif type_id == "dir":
        spec = {"global_icon": "📁", "action": "open_dir"}
    else:
        spec = types.get(type_id, {})

    icon, global_icon, program_icon = _resolve_icon(
        path=path,
        type_id=type_id,
        ext=ext,
        kind=kind,
        spec=spec,
        registry=registry,
        overrides=ov_doc,
    )
    if spec.get("icon_asset"):
        icon = str(spec.get("icon_asset"))

    launchable = bool(
        spec.get("action") in ("run_launchable", "run_launch")
        or type_id in ("elf", "pe_exe", "shell", "python", "emulator_rom", "disc_image", "makefile", "cmake_project")
        or (kind == "file" and os.access(path, os.X_OK) and not ext)
    )
    compileable = bool(spec.get("compileable")) or path.name.lower() in ("cmakelists.txt", "makefile", "gnumakefile")
    out = {
        "type_id": type_id,
        "label": spec.get("label") or type_id,
        "confidence": round(confidence, 3),
        "hints": hints,
        "ext": ext,
        "kind": kind,
        "action": spec.get("action") or ("open_dir" if kind == "dir" else "open_tab"),
        "open_with": spec.get("open_with") or "default",
        "compileable": compileable,
        "launchable": launchable,
        "global_icon": global_icon,
        "program_icon": program_icon,
        "icon": icon,
        "mime": spec.get("mime"),
        "icon_asset": spec.get("icon_asset"),
        "uncompiled": spec.get("uncompiled"),
        "entry": spec.get("entry"),
        "runtime": spec.get("runtime"),
        "browse_action": spec.get("browse_action"),
        "launch_path": spec.get("launch_path"),
    }
    if chamber_hint:
        for key in ("entry", "runtime", "file_count", "launch_path", "browse_action", "uncompiled", "icon_asset"):
            if chamber_hint.get(key) is not None:
                out[key] = chamber_hint[key]
    return out


def run_launch_chamber(path: Path, *, timeout: int = 120) -> dict[str, Any]:
    ch = _chamber_mod()
    if not ch:
        return {"ok": False, "error": "chamber_unavailable"}
    info = inspect_file(path)
    out = ch.run_chamber(path, timeout=timeout)
    out["inspect"] = info
    return out


def create_launch_file(
    path: Path,
    *,
    lock: bool = True,
    refresh: bool = False,
    seal_generation: int | None = None,
) -> dict[str, Any]:
    ch = _chamber_mod()
    if not ch:
        return {"ok": False, "error": "chamber_unavailable"}
    if not path.is_dir():
        return {"ok": False, "error": "not_a_directory", "path": str(path)}
    try:
        out = ch.write_launch_file(
            path,
            lock=lock,
            refresh=refresh,
            seal_generation=seal_generation,
        )
        if out.get("path"):
            out["inspect"] = inspect_file(Path(out["path"]))
        return out
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "path": str(path)}


def release_compile_mode(path: Path, *, profile: str = "belt_2_0") -> dict[str, Any]:
    """Release-day wave convert — not used in normal dev runs."""
    info = inspect_file(path)
    if not info.get("compileable"):
        return {"ok": False, "error": "not_compileable", "inspect": info}
    sg = QUEEN.parent.parent
    g16 = Path(os.environ.get("GROK16_ROOT", str(sg / "Grok16"))) / "bin" / "g16"
    if not g16.is_file():
        return {"ok": False, "error": "g16_missing", "hint": "bootstrap Grok16 for release compile", "inspect": info}

    out_dir = STATE / "release-compile"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", path.stem)[:80] or "artifact"
    tid = info.get("type_id") or "unknown"
    ext = path.suffix.lower()

    if tid == "python" or ext in (".py", ".gpy", ".pyw"):
        cmd = [str(g16), "-m", "py_compile", str(path)]
        artifact = out_dir / f"{stem}.pyc"
    elif path.name == "CMakeLists.txt":
        build = out_dir / f"{stem}-cmake"
        build.mkdir(parents=True, exist_ok=True)
        toolchain = Path(os.environ.get("GROK16_ROOT", str(sg / "Grok16"))) / "cmake" / "grok16-toolchain.cmake"
        cfg = ["cmake", "-S", str(path.parent), "-B", str(build)]
        if toolchain.is_file():
            cfg.extend([f"-DCMAKE_TOOLCHAIN_FILE={toolchain}", f"-DGROK16_PROFILE={profile}"])
        proc = subprocess.run(cfg, capture_output=True, text=True, timeout=300, check=False)
        if proc.returncode != 0:
            return {
                "ok": False,
                "error": "cmake_configure_failed",
                "stderr": (proc.stderr or proc.stdout or "")[-2000:],
                "inspect": info,
            }
        proc = subprocess.run(["cmake", "--build", str(build), "-j", "4"], capture_output=True, text=True, timeout=600, check=False)
        if proc.returncode != 0:
            return {
                "ok": False,
                "error": "cmake_build_failed",
                "stderr": (proc.stderr or proc.stdout or "")[-2000:],
                "inspect": info,
            }
        bins = list(build.glob("*"))
        artifact = bins[0] if bins else build
        return {
            "ok": True,
            "release_compile": True,
            "compile_mode": True,
            "artifact": str(artifact),
            "build_dir": str(build),
            "message": "Release CMake plane built — dev runs stay uncompiled",
            "inspect": info,
        }
    else:
        artifact = out_dir / f"{stem}.release"
        flags_py = Path(os.environ.get("GROK16_ROOT", str(sg / "Grok16"))) / "scripts" / "grok16-profile-flags.py"
        extra: list[str] = []
        if flags_py.is_file():
            kind = "cxx" if ext in (".cpp", ".cxx", ".cc", ".hpp", ".hh", ".comp") else "c"
            try:
                proc = subprocess.run(
                    [os.environ.get("PYTHON", "python3"), str(flags_py), profile, kind],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                    env={**os.environ, "GROK16_ROOT": str(g16.parent.parent), "G16_PREFIX": str(g16.parent.parent)},
                )
                if proc.stdout.strip():
                    extra = proc.stdout.strip().split()
            except (OSError, subprocess.TimeoutExpired):
                pass
        cmd = [str(g16), *extra, "-O2", "-o", str(artifact), str(path)]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "inspect": info}
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": "g16_compile_failed",
            "returncode": proc.returncode,
            "stderr": (proc.stderr or proc.stdout or "")[-4000:],
            "inspect": info,
        }
    manifest = STATE / "release-compile-manifest.json"
    doc = {"updated": _ts(), "entries": []}
    try:
        doc = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    doc["updated"] = _ts()
    entries = [e for e in doc.get("entries", []) if e.get("source") != str(path)]
    entries.append(
        {
            "source": str(path),
            "artifact": str(artifact),
            "type_id": tid,
            "profile": profile,
            "compiled_at": _ts(),
        }
    )
    doc["entries"] = entries[-64:]
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "release_compile": True,
        "compile_mode": True,
        "artifact": str(artifact),
        "message": "Release plane staged — dev runs stay at normal interpreter speed",
        "inspect": info,
    }


def launch_spv(path: Path) -> dict[str, Any]:
    """Stage SPIR-V and launch queen-browser when available."""
    info = inspect_file(path)
    header = _read_header(path, 4)
    if len(header) < 4 or int.from_bytes(header[:4], "little") != SPIRV_MAGIC:
        return {"ok": False, "error": "not_spirv", "inspect": info}

    dst_dir = QUEEN / "assets" / "shaders" / "compute"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / path.name
    try:
        shutil.copy2(path, dst)
    except OSError as exc:
        return {"ok": False, "error": "stage_failed", "detail": str(exc)[:120], "inspect": info}

    launcher = QUEEN / "scripts" / "run-queen.sh"
    binary = QUEEN / "build" / "rtx" / "bin" / "Linux" / "queen-browser"
    if not binary.is_file():
        binary = QUEEN / "build" / "bin" / "Linux" / "queen-browser"

    spawned = False
    pid = None
    cmd: list[str] | None = None
    if binary.is_file() or launcher.is_file():
        cmd = [str(launcher)] if launcher.is_file() else [str(binary), "--sovereign", "--queen"]
        env = {
            **os.environ,
            "QUEEN_SPIRV_PATH": str(dst),
            "QUEEN_SHADER_STAGE": "comp",
            "NEXUS_INSTALL_ROOT": os.environ.get("NEXUS_INSTALL_ROOT", str(QUEEN)),
            "QUEEN_ROOT": str(QUEEN),
        }
        proc = subprocess.Popen(
            cmd,
            cwd=str(QUEEN),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        spawned = True
        pid = proc.pid

    return {
        "ok": True,
        "launched": spawned,
        "pid": pid,
        "cmd": cmd,
        "staged": str(dst),
        "shader": path.name,
        "inspect": info,
        "message": (
            f"SPIR-V {path.name} staged"
            + (f" · queen-browser pid {pid}" if spawned else " · binary not found, staged only")
        ),
    }