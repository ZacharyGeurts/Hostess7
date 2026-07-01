#!/usr/bin/env pythong
"""Queen .launch chamber — organized field; inspect files, run without compile."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
FACADE_CACHE = STATE / "launch-facade-cache"

SCHEMA = "queen-launch/v1"
LAUNCH_EXT = ".launch"

CODE_EXTS = frozenset({
    ".py", ".pyw", ".gpy", ".sh", ".bash", ".zsh", ".fish",
    ".c", ".cpp", ".cxx", ".cc", ".h", ".hpp", ".h", ".hh",
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".rs", ".zig", ".comp",
    ".asm", ".s", ".lua", ".rb", ".pl", ".php", ".r", ".jl", ".kt", ".kts",
    ".java", ".class", ".jar", ".wasm", ".wat",
    ".exe", ".elf", ".out", ".bin", ".appimage", ".deb", ".rpm", ".apk",
    ".bat", ".cmd", ".ps1", ".com",
    ".nes", ".smc", ".sfc", ".gb", ".gbc", ".gba", ".nds", ".z64", ".v64", ".n64",
    ".iso", ".cue", ".chd", ".img", ".dmg", ".rom", ".vb", ".pce", ".sg", ".sms",
    ".cmake", ".ninja", ".gradle", ".m", ".mm", ".swift",
})
LAUNCHABLE_NAMES = frozenset({
    "cmakelists.txt", "makefile", "gnumakefile", "dockerfile", "justfile",
    "build.gradle", "gradlew", "meson.build", "configure", "configure.ac",
})
ENTRY_CANDIDATES = (
    "main.py", "__main__.py", "run.py", "app.py", "speed_demo.py",
    "main.sh", "run.sh", "start.sh", "linux.sh",
    "CMakeLists.txt", "Makefile", "gradlew",
)
ELF_MAGIC = b"\x7fELF"
PE_MAGIC = b"MZ"
CHAMBER_SKIP = frozenset({
    ".git", "__pycache__", ".venv", ".venv-browser", "node_modules",
    "build", "dist", ".nexus-state", ".nexus-field-drive",
})
CHAMBER_SKIP_GLOBS = ("*.pyc", "*.o", "*.a", "*.so", "*.tmp")

_SINGULAR = None


def _singular_mod():
    global _SINGULAR
    if _SINGULAR is not None:
        return _SINGULAR
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "queen_launch_singular_field", QUEEN / "lib" / "queen-launch-singular-field.py"
    )
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _SINGULAR = mod
    return mod


def singular_field_enabled() -> bool:
    return os.environ.get("QUEEN_LAUNCH_SINGULAR_FIELD", "0").strip().lower() in (
        "1", "true", "yes", "on",
    )


def compile_mode_enabled() -> bool:
    return os.environ.get("QUEEN_LAUNCH_COMPILE", "").strip().lower() in (
        "1", "true", "yes", "on",
    ) or os.environ.get("G16_FORCE_COMPILE", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def organized_field_enabled() -> bool:
    if compile_mode_enabled() or singular_field_enabled():
        return False
    return os.environ.get("QUEEN_LAUNCH_ORGANIZED_FIELD", "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


def iron_exec_enabled() -> bool:
    """Native iron-plate BSP on organized launch — env or free-meld unlock."""
    if os.environ.get("QUEEN_LAUNCH_IRON_EXEC", "").strip().lower() in (
        "1", "true", "yes", "on",
    ):
        return True
    posture = _global_truth_posture()
    return bool(posture.get("free_meld"))


def _global_truth_posture() -> dict[str, Any]:
    import importlib.util
    tb_py = _grok16_root() / "lib" / "field_truth_blocks.py"
    if not tb_py.is_file():
        return {}
    try:
        spec = importlib.util.spec_from_file_location("field_truth_blocks", tb_py)
        if not spec or not spec.loader:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        panel_path = STATE / "g16-truth-blocks-panel.json"
        if panel_path.is_file():
            try:
                panel = json.loads(panel_path.read_text(encoding="utf-8"))
                fm = panel.get("free_meld_posture") or {}
                if fm:
                    return fm
            except (OSError, json.JSONDecodeError):
                pass
        return mod.free_meld_posture()
    except Exception:
        return {}


def _grok16_root() -> Path:
    _SG_PATHS_LIB = Path(__file__).resolve().parents[2] / "lib"
    if str(_SG_PATHS_LIB) not in sys.path:
        sys.path.insert(0, str(_SG_PATHS_LIB))
    from sg_paths import grok16_root
    return grok16_root()


_CHAMBER_EXEMPT_RUNTIMES = frozenset({
    "emulator", "cmake", "make", "executable", "elf", "native", "wasm", "shell",
})


def _secure_runtimes() -> frozenset[str]:
    path = _grok16_root() / "data" / "grok16-languages.json"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        langs = set((doc.get("languages") or {}).keys())
        langs.update({"shell", "cobol_copy"})
        return frozenset(langs - _CHAMBER_EXEMPT_RUNTIMES)
    except (OSError, json.JSONDecodeError):
        return frozenset({
            "java", "kotlin", "javascript", "typescript", "pascal", "turbo_pascal",
            "delphi", "fortran", "cobol", "cobol_copy", "ruby", "perl", "php", "lua",
        })


def _secure_chamber_mod():
    import importlib.util
    nexus = Path(__file__).resolve().parents[2]
    sec_py = nexus / "lib" / "g16-secure-chamber.py"
    if not sec_py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("g16_secure_chamber_queen", sec_py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _secure_chamber_run(path: str, *, lang: str = "") -> dict[str, Any]:
    mod = _secure_chamber_mod()
    if not mod or not hasattr(mod, "run_path"):
        return {"ok": False, "error": "secure_chamber_missing"}
    return mod.run_path(path, lang=lang)


def _iron_plate_mod():
    import importlib.util
    plate_py = _grok16_root() / "lib" / "field_iron_plate.py"
    if not plate_py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_iron_plate", plate_py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bsp_mod():
    import importlib.util
    bsp_py = _grok16_root() / "lib" / "field_exec_bsp.py"
    if not bsp_py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_exec_bsp", bsp_py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_PYTHON_INTERP = None


def _python_interp_mod():
    global _PYTHON_INTERP
    if _PYTHON_INTERP is not None:
        return _PYTHON_INTERP
    import importlib.util
    py_py = _grok16_root() / "lib" / "field_python_interpreter.py"
    if not py_py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_python_interpreter", py_py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _PYTHON_INTERP = mod
    return mod


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_pythong() -> str:
    mod = _python_interp_mod()
    if mod:
        driver, _ = mod.resolve_pythong_driver(_grok16_root(), sg_root=SG)
        if driver and Path(driver).is_file():
            return driver
    for candidate in (
        os.environ.get("NEXUS_PYTHONG"),
        os.environ.get("PYTHONG"),
        str(_grok16_root() / "bin" / "gpy-16"),
        str(QUEEN / "scripts" / "queen-py"),
        str(SG / "PythonG" / "bin" / "pythong"),
        str(SG / "GrokPy" / "bin" / "gpy-16"),
        shutil_which("pythong"),
        shutil_which("python3"),
    ):
        if candidate and Path(candidate).is_file():
            return candidate
    return sys.executable


def shutil_which(name: str) -> str | None:
    from shutil import which
    return which(name)


def _runtime_for_entry(name: str) -> str:
    low = name.lower()
    if low.endswith((".py", ".pyw", ".gpy")):
        return "python"
    if low.endswith((".sh", ".bash", ".zsh", ".fish")):
        return "shell"
    if low in ("cmakelists.txt",) or low.endswith(".cmake"):
        return "cmake"
    if low in ("makefile", "gnumakefile") or low == "justfile":
        return "make"
    if low.endswith((".js", ".mjs", ".cjs")):
        return "node"
    if low.endswith((".ts", ".tsx")):
        return "node"
    if low.endswith((".jar", ".class")):
        return "java"
    if low.endswith(".wasm"):
        return "wasm"
    if low.endswith((".exe", ".elf", ".out", ".appimage", ".com", ".bat", ".cmd")):
        return "executable"
    if low.endswith((".c", ".cpp", ".cxx", ".cc")):
        return "native"
    if low.endswith((".nes", ".smc", ".sfc", ".gb", ".gbc", ".gba", ".nds", ".z64", ".v64", ".n64", ".iso", ".cue", ".rom")):
        return "emulator"
    if low.endswith((".ps1",)):
        return "powershell"
    return "executable"


def _sniff_launchable(path: Path) -> str | None:
    try:
        head = path.read_bytes()[:4]
    except OSError:
        return None
    if head[:4] == ELF_MAGIC:
        return "elf"
    if head[:2] == PE_MAGIC:
        return "pe"
    try:
        line = path.read_bytes()[:128]
        if line.startswith(b"#!"):
            return "shebang"
    except OSError:
        pass
    return None


def _is_launchable_file(path: Path) -> bool:
    if not path.is_file():
        return False
    low = path.name.lower()
    if low in LAUNCHABLE_NAMES:
        return True
    if path.suffix.lower() in CODE_EXTS:
        return True
    sniff = _sniff_launchable(path)
    if sniff in ("elf", "pe", "shebang"):
        return True
    try:
        if os.access(path, os.X_OK) and not path.suffix:
            return True
    except OSError:
        pass
    return False


def _launchable_row(root: Path, rel: str, path: Path) -> dict[str, Any]:
    sniff = _sniff_launchable(path)
    runtime = _runtime_for_entry(path.name)
    if sniff == "elf":
        runtime = "elf"
    elif sniff == "pe":
        runtime = "executable"
    elif sniff == "shebang" and runtime == "executable":
        runtime = "shell"
    try:
        st = path.stat()
        nbytes = st.st_size
    except OSError:
        nbytes = 0
    return {
        "path": rel,
        "name": path.name,
        "runtime": runtime,
        "sniff": sniff,
        "bytes": nbytes,
        "executable": bool(sniff in ("elf", "pe", "shebang") or os.access(path, os.X_OK)),
    }


def discover_launchables(root: Path, *, rels: list[str] | None = None) -> list[dict[str, Any]]:
    """All launchable files in chamber — sh, elf, cmake, emu roms, etc."""
    root = root.resolve()
    rows: list[dict[str, Any]] = []
    if rels is None:
        rels, _ = _walk_chamber(root, max_files=0)
    for rel in rels:
        p = root / rel
        if not _is_launchable_file(p):
            continue
        rows.append(_launchable_row(root, rel, p))
    rows.sort(key=lambda r: (r.get("runtime") or "", r.get("name") or ""))
    return rows


def _walk_chamber(root: Path, *, max_files: int = 0) -> tuple[list[str], int]:
    """Walk chamber files. max_files=0 means no cap (default)."""
    rels: list[str] = []
    total_bytes = 0
    capped = int(max_files) > 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in CHAMBER_SKIP and not d.startswith(".")]
        for fn in filenames:
            if fn.startswith("."):
                continue
            if any(fn.endswith(glob[1:]) if glob.startswith("*.") else False for glob in CHAMBER_SKIP_GLOBS):
                continue
            p = Path(dirpath) / fn
            try:
                rel = p.relative_to(root).as_posix()
                total_bytes += p.stat().st_size
                rels.append(rel)
            except OSError:
                continue
            if capped and len(rels) >= max_files:
                return rels, total_bytes
    return rels, total_bytes


def _load_existing_manifest(root: Path) -> dict[str, Any] | None:
    lp = launch_facade_path(root)
    if not lp.is_file():
        return None
    try:
        return load_launch_manifest(lp)
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _manifest_locked(existing: dict[str, Any] | None) -> bool:
    return bool((existing or {}).get("locked")) or bool((existing or {}).get("secured"))


def _compat_layers_panel_path() -> Path:
    install = Path(os.environ.get("NEXUS_INSTALL_ROOT", QUEEN.parent))
    state = Path(os.environ.get("NEXUS_STATE_DIR", STATE))
    return state / "field-compatibility-layers-panel.json"


def launch_seal_state() -> dict[str, Any]:
    """Refresh seal from compatibility layers — .launch edits require current generation."""
    try:
        panel = json.loads(_compat_layers_panel_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        panel = {}
    seal = panel.get("launch_seal") or {}
    gen = int(seal.get("generation") or 0)
    return {
        "generation": gen,
        "updated": seal.get("updated"),
        "required_for_refresh": gen > 0,
        "hint": "Sync compatibility layers, then refresh .launch",
    }


def _manifest_seal_hash(doc: dict[str, Any]) -> str:
    import hashlib

    payload = json.dumps(
        {
            "entry": doc.get("entry"),
            "files": doc.get("files"),
            "launchables": doc.get("launchables"),
            "file_count": doc.get("file_count"),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def _apply_launch_security(doc: dict[str, Any], *, seal_generation: int) -> dict[str, Any]:
    doc["locked"] = True
    doc["scan"] = "locked"
    doc["scan_cap"] = len(doc.get("files") or [])
    doc["secured"] = True
    doc["seal_generation"] = int(seal_generation)
    doc["seal_hash"] = _manifest_seal_hash(doc)
    doc["seal_at"] = _ts()
    return doc


def launch_refresh_allowed(
    existing: dict[str, Any] | None,
    *,
    seal_generation: int | None,
) -> tuple[bool, str]:
    if not existing:
        return True, "new_chamber"
    if not _manifest_locked(existing):
        return True, "unlocked_legacy"
    current = launch_seal_state()["generation"]
    if current <= 0:
        return True, "bootstrap_seal"
    if seal_generation is None:
        return False, "launch_refresh_requires_compatibility_sync"
    if int(seal_generation) != current:
        return False, "launch_seal_stale_sync_compatibility_layers_first"
    return True, "seal_ok"


def verify_launch_integrity(doc: dict[str, Any]) -> dict[str, Any]:
    expected = doc.get("seal_hash")
    if not expected:
        return {"ok": True, "verified": False, "reason": "no_seal"}
    actual = _manifest_seal_hash(doc)
    match = actual == expected
    return {
        "ok": match,
        "verified": True,
        "reason": "match" if match else "tamper_detected",
        "seal_hash": expected,
    }


def _pick_entry(root: Path) -> tuple[str | None, str | None]:
    for name in ENTRY_CANDIDATES:
        p = root / name
        if p.is_file():
            return name, _runtime_for_entry(name)
    singles = [
        c.name
        for c in sorted(root.iterdir(), key=lambda x: x.name.lower())
        if c.is_file() and c.suffix.lower() in CODE_EXTS and c.name not in ("setup.py", "conftest.py")
    ]
    if len(singles) == 1:
        return singles[0], _runtime_for_entry(singles[0])
    py_main = [n for n in singles if n.endswith(".py") and "demo" in n.lower()]
    if len(py_main) == 1:
        return py_main[0], "python"
    if singles:
        pref = next((n for n in singles if n.endswith(".py")), singles[0])
        return pref, _runtime_for_entry(pref)
    return None, None


def launch_facade_path(root: Path) -> Path:
    """Canonical .launch path — folder presents as this file."""
    root = root.resolve()
    return root / f"{root.name}{LAUNCH_EXT}"


def build_manifest_fast(
    root: Path,
    *,
    entry: str | None = None,
    runtime: str | None = None,
) -> dict[str, Any]:
    """Facade manifest — full file index unless .launch is locked."""
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("not_a_directory")
    existing = _load_existing_manifest(root)
    locked = _manifest_locked(existing)
    picked_entry, picked_runtime = _pick_entry(root)
    entry = entry or (existing or {}).get("entry") or picked_entry
    runtime = runtime or (existing or {}).get("runtime") or picked_runtime
    if not entry:
        raise ValueError("no_entry")
    cap = int((existing or {}).get("scan_cap") or 0) if locked else 0
    doc = build_manifest(root, entry=entry, runtime=runtime, max_files=cap, existing=existing if locked else None)
    doc["scan"] = "locked" if locked else "full"
    doc["locked"] = locked
    return doc


def _facade_fingerprint(root: Path, entry: str) -> str:
    import hashlib
    parts = [str(root), entry]
    try:
        ep = root / entry
        if ep.is_file():
            st = ep.stat()
            parts.append(f"{st.st_mtime_ns}:{st.st_size}")
    except OSError:
        pass
    count = 0
    try:
        for c in root.iterdir():
            if c.is_file() and c.suffix.lower() in CODE_EXTS:
                count += 1
                if count > 8:
                    break
                try:
                    st = c.stat()
                    parts.append(f"{c.name}:{st.st_mtime_ns}")
                except OSError:
                    pass
    except OSError:
        pass
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:20]


def ensure_launch_facade(
    root: Path,
    *,
    write: bool = True,
    max_age_sec: int = 300,
) -> dict[str, Any]:
    """Autogenerate .launch as folder facade — cached for speed."""
    root = root.resolve()
    detected = detect_code_folder(root)
    if not detected:
        return {"ok": False, "error": "not_code_chamber", "path": str(root)}

    dest = launch_facade_path(root)
    if detected.get("kind") == "launch_file":
        lp = Path(str(detected.get("launch_path") or dest))
        if lp.is_file():
            try:
                doc = load_launch_manifest(lp)
                out = {
                    "ok": True,
                    "path": str(lp),
                    "manifest": doc,
                    "cached": True,
                    "facade": True,
                    "locked": _manifest_locked(doc),
                    "secured": bool(doc.get("secured")),
                }
                if _manifest_locked(doc):
                    out["message"] = "Launch locked — sync compatibility layers then refresh"
                return out
            except (OSError, ValueError, json.JSONDecodeError):
                pass

    if dest.is_file():
        try:
            locked_doc = load_launch_manifest(dest)
            if _manifest_locked(locked_doc):
                return {
                    "ok": True,
                    "path": str(dest),
                    "manifest": locked_doc,
                    "cached": True,
                    "facade": True,
                    "locked": True,
                    "secured": True,
                    "message": "Launch locked — sync compatibility layers then refresh",
                }
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    entry = str(detected.get("entry") or "")
    fp = _facade_fingerprint(root, entry)
    cache_path = FACADE_CACHE / f"{root.name}-{fp}.json"
    FACADE_CACHE.mkdir(parents=True, exist_ok=True)

    import time
    stale = True
    if dest.is_file():
        try:
            stale = (time.time() - dest.stat().st_mtime) > max_age_sec
        except OSError:
            stale = True

    if cache_path.is_file() and not stale:
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("fingerprint") == fp:
                return {
                    "ok": True,
                    "path": str(dest),
                    "manifest": cached.get("manifest") or cached,
                    "cached": True,
                    "facade": True,
                }
        except (OSError, json.JSONDecodeError):
            pass

    manifest = build_manifest(root, entry=entry, runtime=str(detected.get("runtime") or ""))
    manifest["facade"] = True
    manifest["fingerprint"] = fp
    manifest["updated"] = _ts()
    seal_gen = launch_seal_state()["generation"]
    manifest = _apply_launch_security(manifest, seal_generation=seal_gen)
    cache_path.write_text(
        json.dumps({"fingerprint": fp, "manifest": manifest}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if write:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "path": str(dest),
        "manifest": manifest,
        "cached": False,
        "facade": True,
        "locked": True,
        "secured": True,
        "seal_generation": seal_gen,
    }


def is_chamber_dir(path: Path) -> bool:
    return detect_code_folder(path) is not None


def detect_code_folder(path: Path) -> dict[str, Any] | None:
    if not path.is_dir():
        return None
    for launch in sorted(path.glob(f"*{LAUNCH_EXT}")):
        if launch.is_file():
            try:
                doc = json.loads(launch.read_text(encoding="utf-8"))
                if doc.get("schema") == SCHEMA:
                    return {
                        "kind": "launch_file",
                        "launch_path": str(launch),
                        "entry": doc.get("entry"),
                        "runtime": doc.get("runtime"),
                        "title": doc.get("title") or path.name,
                    }
            except (OSError, json.JSONDecodeError):
                continue
    entry, runtime = _pick_entry(path)
    if not entry:
        code_count = sum(
            1
            for c in path.iterdir()
            if c.is_file() and c.suffix.lower() in CODE_EXTS
        )
        if code_count < 1:
            return None
        return None
    rels, nbytes = _walk_chamber(path, max_files=0)
    return {
        "kind": "code_folder",
        "entry": entry,
        "runtime": runtime,
        "title": path.name,
        "file_count": len(rels),
        "bytes": nbytes,
    }


def _resolve_chamber_root(raw: str | None, launch_path: Path) -> Path:
    """Resolve portable chamber_root — env tokens, relative paths, launch-dir fallback."""
    if not raw or str(raw).strip() in (".", "./"):
        return launch_path.parent.resolve()
    s = str(raw).strip()
    for key in ("GROK16_ROOT", "SG_ROOT", "QUEEN_ROOT", "NEXUS_INSTALL_ROOT"):
        val = os.environ.get(key, "").strip()
        if not val and key == "GROK16_ROOT":
            val = str(_grok16_root())
        if not val and key == "SG_ROOT":
            val = str(SG)
        if not val and key == "QUEEN_ROOT":
            val = str(QUEEN)
        if val:
            s = s.replace(f"${{{key}}}", val).replace(f"${key}", val)
    s = s.replace("~/Desktop/SG", str(SG)).replace("~/SG", str(SG))
    p = Path(s).expanduser()
    if not p.is_absolute():
        p = (launch_path.parent / p).resolve()
    else:
        p = p.resolve()
    if not p.is_dir() and launch_path.parent.is_dir():
        return launch_path.parent.resolve()
    if not p.is_dir():
        raise ValueError("chamber_root_missing")
    return p


def _portable_chamber_root(root: Path) -> str:
    """Write relocatable chamber_root for sealed .launch files."""
    resolved = root.resolve()
    for key, base in (
        ("GROK16_ROOT", _grok16_root()),
        ("SG_ROOT", SG),
        ("QUEEN_ROOT", QUEEN),
    ):
        try:
            base = Path(base).resolve()
            rel = resolved.relative_to(base)
            return f"${{{key}}}/{rel.as_posix()}"
        except (ValueError, OSError):
            continue
    if resolved.parent == resolved:
        return "."
    return "."


def load_launch_manifest(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != SCHEMA:
        raise ValueError("invalid_launch_schema")
    root = _resolve_chamber_root(doc.get("chamber_root"), path)
    doc["_resolved_root"] = str(root)
    return doc


def build_manifest(
    root: Path,
    *,
    entry: str | None = None,
    runtime: str | None = None,
    title: str | None = None,
    max_files: int = 0,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("not_a_directory")
    picked_entry, picked_runtime = _pick_entry(root)
    entry = entry or picked_entry
    runtime = runtime or picked_runtime
    if not entry:
        raise ValueError("no_entry")
    locked = _manifest_locked(existing)
    if locked and existing:
        rels = list(existing.get("files") or [])
        nbytes = int(existing.get("bytes") or 0)
        launchables = list(existing.get("launchables") or [])
    else:
        rels, nbytes = _walk_chamber(root, max_files=max_files)
        launchables = discover_launchables(root, rels=rels)
    created = (existing or {}).get("created") or _ts()
    return {
        "schema": SCHEMA,
        "title": title or (existing or {}).get("title") or root.name,
        "chamber_root": _portable_chamber_root(root),
        "entry": entry,
        "runtime": runtime or _runtime_for_entry(entry),
        "cwd": ".",
        "env": dict((existing or {}).get("env") or {}),
        "chamber": {
            "mode": "folder_mirror",
            "include": ["**/*"],
            "exclude": sorted(CHAMBER_SKIP | set(CHAMBER_SKIP_GLOBS)),
        },
        "files": rels,
        "launchables": launchables,
        "launchable_count": len(launchables),
        "file_count": len(rels),
        "bytes": nbytes,
        "capped": bool(max_files > 0 and len(rels) >= max_files),
        "locked": locked,
        "uncompiled": True,
        "organized_field": _organized_field_policy(root),
        "iron_plate": _iron_plate_summary(root),
        "truth_blocks": _truth_blocks_summary(root),
        "created": created,
        "updated": _ts(),
    }


def _organized_field_policy(root: Path) -> dict[str, Any]:
    global_fm = _global_truth_posture()
    compile_gate = bool(global_fm.get("compile_gate", True))
    return {
        "schema": "queen-organized-field/v1",
        "field_depth": 0,
        "inspect_files": True,
        "compile": False,
        "compile_gate": compile_gate,
        "free_meld": bool(global_fm.get("free_meld")),
        "trim_excess": True,
        "runner_policy": {
            "python": "interpreter_bsp",
            "native": "bsp_reuse",
            "cmake": "staged_binary",
            "shell": "interpreter",
            "iron_exec_when_free_meld": True,
        },
    }


def _truth_blocks_summary(root: Path) -> dict[str, Any]:
    import importlib.util
    tb_py = _grok16_root() / "lib" / "field_truth_blocks.py"
    if not tb_py.is_file():
        return {"available": False}
    try:
        spec = importlib.util.spec_from_file_location("field_truth_blocks", tb_py)
        if not spec or not spec.loader:
            return {"available": False}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        doc = mod.project_chamber(root)
        local_fm = doc.get("free_meld") or {}
        global_fm = _global_truth_posture()
        blocks = doc.get("blocks") or []
        return {
            "available": True,
            "block_count": doc.get("block_count"),
            "eligible_count": doc.get("eligible_count"),
            "total_bytes": doc.get("total_bytes"),
            "blocks": [
                {
                    "id": b.get("id"),
                    "tier": b.get("tier"),
                    "size_class": b.get("size_class"),
                    "bytes": b.get("bytes"),
                    "meld_eligible": b.get("meld_eligible"),
                }
                for b in blocks[:8]
            ],
            "free_meld": global_fm.get("free_meld") if global_fm else local_fm.get("free_meld"),
            "level": global_fm.get("level") or local_fm.get("level"),
            "compile_gate": global_fm.get("compile_gate") if global_fm else local_fm.get("compile_gate"),
            "progress": global_fm.get("progress"),
            "mega_blocks": global_fm.get("mega_blocks"),
            "stack_blocks": global_fm.get("stack_blocks"),
            "message": global_fm.get("message") or local_fm.get("message"),
            "motto": "Bigger verified blocks, more of them — meld becomes free",
        }
    except Exception:
        return {"available": False}


def _iron_plate_summary(root: Path) -> dict[str, Any]:
    plate = _iron_plate_mod()
    if not plate:
        return {"plate": "iron", "available": False}
    try:
        doc = plate.project_plate(root)
        return {
            "plate": "iron",
            "available": True,
            "twin_count": doc.get("twin_count"),
            "identical_convertible": doc.get("identical_convertible"),
            "kernel": doc.get("kernel"),
            "breakdown": doc.get("breakdown"),
            "runner": doc.get("runner"),
            "motto": "assembly · entropy · field",
        }
    except Exception:
        return {"plate": "iron", "available": False}


def project_organized_field(
    root: Path,
    *,
    entry: str,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inspect chamber files and map depth-0 fields (no compile)."""
    mod = _singular_mod()
    if mod:
        return mod.project_singular_fields(root, entry=entry, manifest=manifest)
    rels, _ = _walk_chamber(root)
    fields = [
        {
            "path": rel,
            "depth": 0,
            "field_depth": 0,
            "role": "plane_entry" if rel == entry else "support",
            "verdict": "KEEP",
        }
        for rel in rels
    ]
    return {
        "schema": "queen-organized-field/v1",
        "field_depth": 0,
        "chamber_root": str(root.resolve()),
        "entry": entry,
        "fields": fields,
        "field_count": len(fields),
        "stripped_excess": 0,
        "total_seen": len(rels),
        "updated": _ts(),
        "manifest": manifest or {},
    }


def _prefer_runner_source(root: Path, entry: str) -> tuple[Path, str]:
    stem = Path(entry).stem
    for ext in (".cpp", ".cxx", ".cc", ".c", ".comp"):
        sib = root / f"{stem}{ext}"
        if sib.is_file():
            kind = "cxx" if ext in (".cpp", ".cxx", ".cc", ".comp") else "c"
            return sib, kind
    ep = root / entry
    ext = ep.suffix.lower()
    if ext in (".cpp", ".cxx", ".cc", ".comp"):
        return ep, "cxx"
    if ext == ".c":
        return ep, "c"
    if ext in (".py", ".pyw", ".gpy"):
        return ep, "python"
    if ext in (".sh", ".bash", ".zsh"):
        return ep, "shell"
    if ep.name.lower() == "cmakelists.txt":
        return ep, "cmake"
    return ep, "python"


def _bsp_case_ids(stem: str, kind: str) -> list[str]:
    if stem == "speed_demo":
        return [
            "cxx_host_o2",
            "cmake_host_o2",
            "c_host_o2",
            "cxx_g16_belt_2",
            "c_g16_belt_2",
        ]
    if kind == "cmake":
        return ["cmake_host_o2", "cmake_g16_belt_2"]
    return [f"{kind}_host_o2", f"{kind}_g16_belt_2", f"cxx_host_o2", f"c_host_o2"]


def _resolve_bsp_python(script: Path) -> dict[str, Any]:
    mod = _python_interp_mod()
    if not mod:
        return {"ok": False, "error": "python_interpreter_unavailable"}
    return mod.resolve_python_interpreter(script, grok16_root=_grok16_root(), sg_root=SG)


def _resolve_bsp_native(source: Path, kind: str) -> dict[str, Any]:
    bsp = _bsp_mod()
    if not bsp:
        return {"ok": False, "error": "bsp_unavailable"}
    plane = bsp.exec_plane(_grok16_root())
    sources = [source]
    for case_id in _bsp_case_ids(source.stem, kind):
        hit, compile_ms, note = bsp.bsp_try_reuse(
            plane,
            case_id=case_id,
            sources=sources,
            profile=case_id,
        )
        if hit:
            return {
                "ok": True,
                "plane_kind": "binary",
                "runner": str(hit),
                "runtime": "native",
                "toolchain": case_id,
                "compile_ms": compile_ms,
                "bsp_note": note,
                "source": str(source),
            }
    return {
        "ok": False,
        "error": "no_staged_binary",
        "source": str(source),
        "message": "Stage exec-plane first (Compile mode or exec-bsp-bench); launch does not compile",
    }


def resolve_organized_runner(
    root: Path,
    entry: str,
    manifest: dict[str, Any],
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Pick runner from organized field — iron plate twins, interpreter or BSP reuse only."""
    policy = (manifest.get("organized_field") or {}).get("runner_policy") or {}
    entry_path = root / entry
    plate_mod = _iron_plate_mod()
    iron_mode = "exec" if iron_exec_enabled() else "dev"
    if plate_mod:
        try:
            face = plate_mod.resolve_runner_face(root, entry, mode=iron_mode)
            if face.get("ok") and iron_mode == "exec" and face.get("lane") in ("native", "bsp_reuse"):
                native_path = Path(str(face.get("path") or entry_path))
                kind = str(face.get("face") or "cxx")
                plane = _resolve_bsp_native(native_path, kind)
                if plane.get("ok"):
                    return {
                        **plane,
                        "iron_plate": True,
                        "iron_exec": True,
                        "free_meld": iron_exec_enabled(),
                        "face": face.get("face"),
                        "kernel": face.get("kernel"),
                        "breakdown": face.get("breakdown"),
                        "identical": face.get("identical"),
                    }
            if face.get("ok") and face.get("lane") == "interpreter":
                py_path = Path(str(face.get("path") or entry_path))
                plane = _resolve_bsp_python(py_path)
                if plane.get("ok"):
                    return {
                        **plane,
                        "iron_plate": True,
                        "face": face.get("face"),
                        "kernel": face.get("kernel"),
                        "breakdown": face.get("breakdown"),
                        "identical": face.get("identical"),
                    }
                return {
                    "ok": True,
                    "plane_kind": "interpreter",
                    "runner": str(py_path),
                    "interpreter": _resolve_pythong(),
                    "runtime": "python",
                    "compile_ms": 0,
                    "iron_plate": True,
                    "face": face.get("face"),
                    "kernel": face.get("kernel"),
                    "breakdown": face.get("breakdown"),
                    "identical": face.get("identical"),
                }
        except Exception:
            pass

    source, kind = _prefer_runner_source(root, entry)

    if kind in ("cxx", "c") and policy.get("native", "bsp_reuse") == "bsp_reuse":
        plane = _resolve_bsp_native(source, kind)
        if plane.get("ok"):
            plane["organized_field"] = True
            plane["field_count"] = fields.get("field_count")
            return plane
        if entry_path.is_file() and entry_path.suffix.lower() in (".py", ".pyw", ".gpy"):
            return {
                "ok": True,
                "plane_kind": "interpreter",
                "runner": str(entry_path),
                "runtime": "python",
                "compile_ms": 0,
                "fallback": "entry_interpreter",
                "native_miss": plane.get("error"),
            }
        return {**plane, "organized_field": True}

    if kind == "cmake" and policy.get("cmake", "staged_binary") == "staged_binary":
        plane = _resolve_bsp_native(root / "CMakeLists.txt", "cmake")
        if plane.get("ok"):
            plane["organized_field"] = True
            return plane
        if entry_path.is_file():
            kind = _runtime_for_entry(entry)
            if kind == "python":
                return {
                    "ok": True,
                    "plane_kind": "interpreter",
                    "runner": str(entry_path),
                    "runtime": "python",
                    "compile_ms": 0,
                }
        return {**plane, "organized_field": True}

    py_policy = policy.get("python", "interpreter_bsp")
    if kind == "python" or py_policy in ("interpreter", "interpreter_bsp"):
        plane = _resolve_bsp_python(entry_path)
        if plane.get("ok"):
            plane["organized_field"] = True
            return plane
        return {
            "ok": True,
            "plane_kind": "interpreter",
            "runner": str(entry_path),
            "interpreter": _resolve_pythong(),
            "runtime": "python",
            "compile_ms": 0,
            "source": str(source),
            "organized_field": True,
        }

    if kind == "shell":
        return {
            "ok": True,
            "plane_kind": "interpreter",
            "runner": str(source),
            "runtime": "shell",
            "compile_ms": 0,
        }

    runtime = _runtime_for_entry(entry)
    if policy.get(runtime) == "chamber" or runtime in _secure_runtimes():
        return {
            "ok": True,
            "plane_kind": "secure_chamber",
            "runner": str(entry_path),
            "runtime": runtime,
            "compile_ms": 0,
            "organized_field": True,
        }

    return {
        "ok": True,
        "plane_kind": "interpreter",
        "runner": str(entry_path),
        "runtime": runtime,
        "compile_ms": 0,
    }


def _resolve_launch_context(path: Path) -> tuple[dict[str, Any], Path, str | None]:
    manifest: dict[str, Any]
    root: Path
    launch_path: str | None = None

    if path.suffix.lower() == LAUNCH_EXT and path.is_file():
        manifest = load_launch_manifest(path)
        root = Path(manifest["_resolved_root"])
        launch_path = str(path)
    elif path.is_dir():
        detected = detect_code_folder(path)
        if detected and detected.get("kind") == "launch_file":
            lp = Path(detected["launch_path"])
            manifest = load_launch_manifest(lp)
            root = Path(manifest["_resolved_root"])
            launch_path = str(lp)
        else:
            manifest = build_manifest(path)
            root = path
    else:
        raise ValueError("not_launch_or_folder")
    return manifest, root, launch_path


def run_organized_field(
    path: Path,
    *,
    args: list[str] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """Inspect chamber → organized field map → run without compile."""
    try:
        manifest, root, launch_path = _resolve_launch_context(path)
    except ValueError:
        return {"ok": False, "error": "not_launch_or_folder", "path": str(path)}

    entry_name = str(manifest.get("entry") or "")
    if not entry_name:
        return {"ok": False, "error": "no_entry", "manifest": manifest}

    entry = (root / entry_name).resolve()
    try:
        entry.relative_to(root)
    except ValueError:
        return {"ok": False, "error": "entry_outside_chamber", "entry": str(entry)}

    if not entry.is_file():
        return {"ok": False, "error": "entry_missing", "entry": str(entry)}

    fields = project_organized_field(root, entry=entry_name, manifest=manifest)
    plane = resolve_organized_runner(root, entry_name, manifest, fields)
    if not plane.get("ok"):
        return {
            "ok": False,
            "error": plane.get("error"),
            "message": plane.get("message"),
            "organized_field": fields,
            "plane": plane,
            "launch_path": launch_path,
        }

    if plane.get("plane_kind") == "secure_chamber":
        out = _secure_chamber_run(str(plane["runner"]), lang=str(plane.get("runtime") or ""))
        out["launch_mode"] = "organized_field"
        out["uncompiled"] = True
        out["organized_field"] = fields
        out["plane"] = plane
        out["launch_path"] = launch_path
        out["cwd"] = str(root)
        return out

    if plane.get("plane_kind") == "binary":
        cmd = [str(plane["runner"])]
    elif plane.get("interpreter"):
        cmd = [str(plane["interpreter"]), str(plane["runner"])]
    elif plane.get("runtime") == "python":
        cmd = [_resolve_pythong(), str(plane["runner"])]
    elif plane.get("runtime") == "shell":
        cmd = [shutil_which("bash") or "/bin/bash", str(plane["runner"])]
    else:
        cmd = _run_cmd(str(plane.get("runtime") or "python"), Path(plane["runner"]), root)
    if args:
        cmd.extend(args)

    env = {
        **os.environ,
        "QUEEN_LAUNCH_CHAMBER": "1",
        "QUEEN_LAUNCH_ORGANIZED_FIELD": "1",
        "NEXUS_CHAMBER_ROOT": str(root),
        "QUEEN_LAUNCH_UNCOMPILED": "1",
        "QUEEN_ROOT": str(QUEEN),
        "SG_ROOT": str(SG),
        "GROK16_ROOT": str(_grok16_root()),
        "NEXUS_STATE_DIR": str(STATE),
        "TOOLCHAIN_TAG": str(plane.get("toolchain") or plane.get("runtime") or "organized_field"),
    }
    for k, v in (manifest.get("env") or {}).items():
        if isinstance(k, str) and isinstance(v, str):
            env[k] = v
    for k, v in (plane.get("env") or {}).items():
        if isinstance(k, str) and isinstance(v, str):
            env[k] = v

    log_dir = STATE / "launch-organized-field"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"{root.name}-{stamp}.log"

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "error": str(exc),
            "cmd": cmd,
            "organized_field": fields,
            "plane": plane,
        }

    try:
        log_path.write_text(
            f"# organized_field\n# cmd: {' '.join(cmd)}\n# cwd: {root}\n# rc: {proc.returncode}\n\n"
            f"{proc.stdout or ''}\n{proc.stderr or ''}",
            encoding="utf-8",
        )
    except OSError:
        log_path = None

    ok = proc.returncode == 0
    return {
        "ok": ok,
        "launch_mode": "organized_field",
        "uncompiled": True,
        "compile": False,
        "returncode": proc.returncode,
        "cmd": cmd,
        "cwd": str(root),
        "entry": str(entry),
        "launch_path": launch_path,
        "organized_field": fields,
        "plane": plane,
        "field_count": fields.get("field_count"),
        "stripped_excess": fields.get("stripped_excess"),
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
        "log": str(log_path) if log_path else None,
        "message": (
            f"Organized field {'ok' if ok else 'failed'} · "
            f"{plane.get('toolchain') or plane.get('runtime')} · "
            f"{fields.get('field_count')} files · rc={proc.returncode}"
        ),
    }


def write_launch_file(
    root: Path,
    *,
    dest: Path | None = None,
    lock: bool = True,
    refresh: bool = False,
    seal_generation: int | None = None,
) -> dict[str, Any]:
    """Write .launch — secured stable builds; refresh only with compatibility-layer seal."""
    root = root.resolve()
    if dest is None:
        dest = launch_facade_path(root)
    existing = _load_existing_manifest(root)

    if existing and _manifest_locked(existing) and not refresh:
        return {
            "ok": False,
            "error": "launch_locked",
            "path": str(dest),
            "locked": True,
            "secured": bool(existing.get("secured")),
            "seal_generation": existing.get("seal_generation"),
            "launch_seal": launch_seal_state(),
            "hint": launch_seal_state().get("hint"),
        }

    if refresh or (existing and _manifest_locked(existing)):
        allowed, reason = launch_refresh_allowed(existing, seal_generation=seal_generation)
        if not allowed:
            return {
                "ok": False,
                "error": reason,
                "path": str(dest),
                "locked": True,
                "launch_seal": launch_seal_state(),
                "hint": launch_seal_state().get("hint"),
            }

    doc = build_manifest(root, max_files=0)
    gen = int(seal_generation if seal_generation is not None else launch_seal_state()["generation"])
    doc = _apply_launch_security(doc, seal_generation=gen)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "path": str(dest),
        "manifest": doc,
        "locked": True,
        "secured": True,
        "seal_generation": gen,
        "refreshed": bool(refresh),
    }


def _launch_emulator_rom(entry: Path, *, system: str = "nes") -> dict[str, Any]:
    """Route ROM files to Queen Game Room CHIPS pump instead of direct exec."""
    import importlib.util

    chips_py = QUEEN / "lib" / "queen-chips.py"
    if not chips_py.is_file():
        return {"ok": False, "error": "queen_chips_missing"}
    spec = importlib.util.spec_from_file_location("queen_chips_launch", chips_py)
    if not spec or not spec.loader:
        return {"ok": False, "error": "queen_chips_import_failed"}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ext = entry.suffix.lower()
    sys_id = system
    if ext == ".nes":
        sys_id = "nes"
    elif ext in (".smc", ".sfc"):
        sys_id = "snes"
    elif ext in (".gb", ".gbc"):
        sys_id = "gameboy"
    elif ext in (".z64", ".v64", ".n64"):
        sys_id = "n64"
    if hasattr(mod, "launch_emulator"):
        out = mod.launch_emulator(system=sys_id, body={"rom_path": str(entry.resolve())})
        out["launch_mode"] = "emulator"
        out["entry"] = str(entry)
        out["runtime"] = "emulator"
        return out
    return {"ok": False, "error": "launch_emulator_unavailable"}


def _run_cmd(runtime: str, entry: Path, root: Path) -> list[str]:
    py = _resolve_pythong()
    if runtime == "python":
        return [py, str(entry)]
    if runtime == "shell":
        bash = shutil_which("bash") or "/bin/bash"
        return [bash, str(entry)]
    if runtime == "node":
        node = shutil_which("node") or "node"
        return [node, str(entry)]
    if runtime == "cmake":
        build = root / ".queen-launch-build"
        build.mkdir(parents=True, exist_ok=True)
        cmake = shutil_which("cmake") or "cmake"
        return [cmake, "-S", str(root), "-B", str(build)]
    if runtime == "make":
        make = shutil_which("make") or "make"
        return [make, "-C", str(root)]
    if runtime in ("executable", "elf", "native", "emulator", "wasm"):
        return [str(entry)]
    if runtime == "java":
        java = shutil_which("java") or "java"
        return [java, "-jar", str(entry)] if entry.suffix.lower() == ".jar" else [java, str(entry)]
    if runtime == "powershell":
        pwsh = shutil_which("pwsh") or shutil_which("powershell") or "pwsh"
        return [pwsh, "-File", str(entry)]
    return [py, str(entry)]


def run_chamber(
    path: Path,
    *,
    args: list[str] | None = None,
    timeout: int = 120,
    use_singular_plane: bool | None = None,
) -> dict[str, Any]:
    if use_singular_plane is None:
        use_singular_plane = singular_field_enabled() or compile_mode_enabled()
    if organized_field_enabled() and not use_singular_plane:
        out = run_organized_field(path, args=args, timeout=timeout)
        return out
    if use_singular_plane:
        mod = _singular_mod()
        if mod:
            out = mod.run_on_singular_plane(path, timeout=timeout, allow_compile=compile_mode_enabled())
            out["launch_mode"] = "singular_plane"
            return out

    manifest: dict[str, Any] | None = None
    root: Path
    launch_path: str | None = None

    if path.suffix.lower() == LAUNCH_EXT and path.is_file():
        manifest = load_launch_manifest(path)
        root = Path(manifest["_resolved_root"])
        launch_path = str(path)
    elif path.is_dir():
        detected = detect_code_folder(path)
        if detected and detected.get("kind") == "launch_file":
            lp = Path(detected["launch_path"])
            manifest = load_launch_manifest(lp)
            root = Path(manifest["_resolved_root"])
            launch_path = str(lp)
        else:
            manifest = build_manifest(path)
            root = path
    else:
        return {"ok": False, "error": "not_launch_or_folder", "path": str(path)}

    if manifest:
        integrity = verify_launch_integrity(manifest)
        if integrity.get("verified") and not integrity.get("ok"):
            return {
                "ok": False,
                "error": "launch_seal_tamper",
                "path": str(path),
                "integrity": integrity,
                "hint": "Refresh .launch after compatibility sync",
            }

    entry_name = manifest.get("entry") or ""
    entry = (root / entry_name).resolve()
    try:
        entry.relative_to(root)
    except ValueError:
        return {"ok": False, "error": "entry_outside_chamber", "entry": str(entry)}

    if not entry.is_file():
        return {"ok": False, "error": "entry_missing", "entry": str(entry), "manifest": manifest}

    runtime = str(manifest.get("runtime") or _runtime_for_entry(entry_name))
    if runtime == "emulator" and entry.suffix.lower() in (
        ".nes", ".smc", ".sfc", ".gb", ".gbc", ".gba", ".z64", ".v64", ".n64",
        ".pce", ".sms", ".rom",
    ):
        emu = _launch_emulator_rom(entry)
        emu["manifest"] = {k: v for k, v in manifest.items() if not k.startswith("_")}
        emu["launch_path"] = launch_path
        emu["cwd"] = str(root)
        emu["message"] = emu.get("message") or f"Emulator routed to Game Room — {entry.name}"
        return emu

    if runtime in _secure_runtimes():
        out = _secure_chamber_run(str(entry), lang=runtime)
        out["launch_mode"] = "chamber"
        out["manifest"] = {k: v for k, v in manifest.items() if not k.startswith("_")}
        out["launch_path"] = launch_path
        out["cwd"] = str(root)
        out["runtime"] = runtime
        return out

    cmd = _run_cmd(runtime, entry, root)
    if args:
        cmd.extend(args)

    log_dir = STATE / "launch-chamber"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"{root.name}-{stamp}.log"

    env = {
        **os.environ,
        "QUEEN_LAUNCH_CHAMBER": "1",
        "NEXUS_CHAMBER_ROOT": str(root),
        "QUEEN_LAUNCH_UNCOMPILED": "1",
        "QUEEN_ROOT": str(QUEEN),
        "SG_ROOT": str(SG),
        "NEXUS_STATE_DIR": str(STATE),
        "TOOLCHAIN_TAG": "python_launch_chamber",
    }
    for k, v in (manifest.get("env") or {}).items():
        if isinstance(k, str) and isinstance(v, str):
            env[k] = v

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "error": str(exc),
            "cmd": cmd,
            "cwd": str(root),
            "manifest": manifest,
        }

    out_tail = (proc.stdout or "")[-4000:]
    err_tail = (proc.stderr or "")[-2000:]
    try:
        log_path.write_text(
            f"# cmd: {' '.join(cmd)}\n# cwd: {root}\n# rc: {proc.returncode}\n\n{proc.stdout or ''}\n{proc.stderr or ''}",
            encoding="utf-8",
        )
    except OSError:
        log_path = None

    ok = proc.returncode == 0
    return {
        "ok": ok,
        "uncompiled": True,
        "returncode": proc.returncode,
        "cmd": cmd,
        "cwd": str(root),
        "entry": str(entry),
        "runtime": runtime,
        "launch_path": launch_path,
        "manifest": {k: v for k, v in manifest.items() if not k.startswith("_")},
        "stdout_tail": out_tail,
        "stderr_tail": err_tail,
        "log": str(log_path) if log_path else None,
        "message": (
            f"Chamber run {'ok' if ok else 'failed'} · {entry_name} · rc={proc.returncode}"
        ),
    }


def inspect_launch_path(path: Path) -> dict[str, Any] | None:
    if path.suffix.lower() == LAUNCH_EXT and path.is_file():
        try:
            doc = load_launch_manifest(path)
            return {
                "type_id": "launch",
                "label": f"Launch chamber · {doc.get('title') or path.stem}",
                "action": "run_launch",
                "open_with": "chamber",
                "icon_asset": "code",
                "global_icon": "⟨⟩",
                "program_icon": "▶",
                "icon": "code",
                "compileable": True,
                "uncompiled": bool(doc.get("uncompiled", True)),
                "organized_field": True,
                "compile": False,
                "facade": True,
                "browse_action": "browse_inside",
                "entry": doc.get("entry"),
                "runtime": doc.get("runtime"),
                "file_count": doc.get("file_count"),
                "launchable_count": doc.get("launchable_count"),
                "bytes": doc.get("bytes"),
                "chamber_root": doc.get("chamber_root"),
                "fingerprint": doc.get("fingerprint"),
                "locked": bool(doc.get("locked")),
                "secured": bool(doc.get("secured")),
                "seal_generation": doc.get("seal_generation"),
                "launchables": (doc.get("launchables") or [])[:32],
                "iron_plate": (doc.get("iron_plate") or {}).get("available"),
                "iron_kernel": (doc.get("iron_plate") or {}).get("kernel"),
            }
        except (OSError, ValueError, json.JSONDecodeError):
            return {
                "type_id": "launch",
                "label": "Launch chamber (invalid)",
                "action": "open_code",
                "icon_asset": "code",
                "icon": "code",
            }
    if path.is_dir():
        detected = detect_code_folder(path)
        if not detected:
            return None
        return {
            "type_id": "code_chamber",
            "label": f"Code chamber · {detected.get('title') or path.name}",
            "action": "run_launch",
            "open_with": "chamber",
            "icon_asset": "code",
            "global_icon": "⟨⟩",
            "program_icon": "▶",
            "icon": "code",
            "compileable": True,
            "uncompiled": True,
            "organized_field": True,
            "compile": False,
            "facade": True,
            "browse_action": "browse_inside",
            "entry": detected.get("entry"),
            "runtime": detected.get("runtime"),
            "file_count": detected.get("file_count"),
            "launch_path": detected.get("launch_path"),
            "chamber_root": str(path),
        }
    return None


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Queen .launch chamber")
    ap.add_argument("cmd", choices=["detect", "build", "project", "run", "json"])
    ap.add_argument("path", nargs="?", default="")
    ap.add_argument("--write", action="store_true", help="write .launch file on build")
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args()

    path = Path(args.path).expanduser().resolve() if args.path else Path.cwd()

    if args.cmd == "detect":
        print(json.dumps(detect_code_folder(path) or {"ok": False}, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "build":
        if args.write:
            out = write_launch_file(path)
        else:
            out = {"ok": True, "manifest": build_manifest(path)}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "project":
        try:
            manifest, root, _ = _resolve_launch_context(path)
        except ValueError:
            print(json.dumps({"ok": False, "error": "not_launch_or_folder"}, ensure_ascii=False, indent=2))
            return 1
        out = project_organized_field(root, entry=str(manifest.get("entry") or ""), manifest=manifest)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "run":
        out = run_chamber(path, timeout=args.timeout)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if args.cmd == "json":
        info = inspect_launch_path(path)
        print(json.dumps(info or {}, ensure_ascii=False, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())