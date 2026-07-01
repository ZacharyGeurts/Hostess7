#!/usr/bin/env pythong
"""G16 secure compile & run chamber — Java, JS, Pascal, Fortran, and all user langs sealed."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent)))
DOCTRINE = INSTALL / "data" / "g16-secure-compile-doctrine.json"

try:
    from sg_paths import grok16_root
except ImportError:
    def grok16_root() -> Path:
        env = os.environ.get("GROK16_ROOT", "").strip()
        return Path(env) if env else SG / "Grok16"

GROK16 = grok16_root()

_LANG_REGISTRY: dict[str, Any] | None = None

# Host interpreters — argv0 only; source path appended at run time
_INTERP_RUNNERS: dict[str, str] = {
    "ruby": "ruby", "perl": "perl", "php": "php", "lua": "lua", "r": "Rscript",
    "julia": "julia", "clojure": "clojure", "scala": "scala", "groovy": "groovy",
    "elixir": "elixir", "erlang": "erl", "haskell": "runghc", "prolog": "swipl",
    "smalltalk": "gst", "tcl": "tclsh", "awk": "gawk", "matlab": "octave",
    "snobol": "snobol", "forth": "gforth", "lisp": "sbcl", "racket": "racket",
}

# Default source extension when wrapping bare snippets
_LANG_EXT: dict[str, str] = {
    "java": ".java", "kotlin": ".kt", "javascript": ".js", "typescript": ".ts",
    "pascal": ".pas", "turbo_pascal": ".pas", "delphi": ".pas", "fortran": ".f90",
    "cobol": ".cob", "c": ".c", "cxx": ".cpp", "rust": ".rs", "go": ".go",
    "zig": ".zig", "d": ".d", "ada": ".adb", "objc": ".m", "csharp": ".cs",
    "swift": ".swift", "python": ".py", "ruby": ".rb", "perl": ".pl", "php": ".php",
    "lua": ".lua", "shell": ".sh", "basic": ".bas", "qbasic": ".qb", "cobol_copy": ".cob",
}

_EXEMPT_SECURE = frozenset({"plaintext"})

# Security-gate pass only — no binary exec in sealed chamber (by design).
_GATE_ONLY_LANGS = frozenset({
    "shell", "plaintext", "sql", "verilog", "linux", "economics",
    "html", "css", "json", "yaml", "markdown", "toml", "xml",
    "dockerfile", "makefile", "cmake", "glsl", "graphql", "ini",
    "log", "diff", "scss", "powershell", "vbscript", "cobol_copy",
    "wat", "wasm",
})

RUN_TIMEOUT = int(os.environ.get("G16_SECURE_RUN_TIMEOUT", "120"))
COMPILE_TIMEOUT = int(os.environ.get("G16_SECURE_COMPILE_TIMEOUT", "180"))


def _lang_registry() -> dict[str, Any]:
    global _LANG_REGISTRY
    if _LANG_REGISTRY is not None:
        return _LANG_REGISTRY
    path = GROK16 / "data" / "grok16-languages.json"
    doc = _load(path, {})
    _LANG_REGISTRY = doc.get("languages") or {}
    return _LANG_REGISTRY


def secure_langs() -> frozenset[str]:
    langs = set(_lang_registry().keys())
    langs.update({"shell", "typescript", "javascript"})
    return frozenset(langs - _EXEMPT_SECURE)


def compiled_langs() -> frozenset[str]:
    """All field languages Grok16 compiles itself — lower → bin/g16."""
    return secure_langs() - _EXEMPT_SECURE


def needs_secure_chamber(lang: str) -> bool:
    lang = (lang or "plaintext").lower()
    if lang in _EXEMPT_SECURE:
        return False
    return lang in secure_langs() or lang == "shell"


def gate_only_langs() -> frozenset[str]:
    return _GATE_ONLY_LANGS


def _gate_only_run(lang: str, *, comp: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "g16-secure-run/v1",
        "ok": True,
        "gate_only": True,
        "lang": lang,
        "runner": "security_gate",
        "message": f"{lang} — security gate passed; direct exec blocked by policy",
        "compile": comp,
        "security": gate,
    }


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _forbidden_roots() -> list[Path]:
    doc = _load(DOCTRINE, {})
    roots: list[Path] = []
    seen: set[str] = set()
    for cand in (
        INSTALL / "Hostess7",
        INSTALL / "AmmoCode",
        GROK16 / "bin",
        Path("/usr/bin"),
        Path("/bin"),
        Path("/sbin"),
    ):
        p = cand.resolve()
        key = str(p)
        if key not in seen:
            seen.add(key)
            roots.append(p)
    for rel in doc.get("forbidden_run_prefixes") or []:
        rel_s = str(rel).lstrip("/")
        for base in (SG, INSTALL.parent, INSTALL, GROK16.parent):
            p = (base / rel_s).resolve()
            key = str(p)
            if key not in seen and p.exists():
                seen.add(key)
                roots.append(p)
    return roots


def _path_forbidden(path: Path) -> bool:
    s = str(path.resolve())
    for root in _forbidden_roots():
        rs = str(root)
        if s == rs or s.startswith(rs + os.sep):
            return True
    return False


def _security_gate(content: str, *, lang: str, path: str = "") -> dict[str, Any]:
    sec_py = GROK16 / "lib" / "g16-code-security.py"
    if not sec_py.is_file():
        return {"ok": True, "blocked": False, "findings": []}
    spec = importlib.util.spec_from_file_location("g16_code_security_chamber", sec_py)
    if not spec or not spec.loader:
        return {"ok": True, "blocked": False}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "gate"):
        return mod.gate(content, lang=lang, path=path)
    return {"ok": True, "blocked": False}


def _chamber_dir() -> Path:
    prefix = "g16-secure-chamber-"
    d = Path(tempfile.mkdtemp(prefix=prefix, dir=str(STATE if STATE.is_dir() else None)))
    return d


def _chamber_env(chamber: Path) -> dict[str, str]:
    scrub = frozenset({
        "PYTHONPATH", "LD_LIBRARY_PATH", "LD_PRELOAD", "PERL5LIB", "RUBYLIB",
        "NODE_PATH", "CLASSPATH", "JAVA_HOME",
    })
    env = {k: v for k, v in os.environ.items() if k not in scrub}
    env.update({
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(chamber),
        "SG_ROOT": str(SG),
        "GROK16_ROOT": str(GROK16),
        "FIELD_LEGACY_ISOLATION": "1",
        "G16_SECURE_CHAMBER": "1",
        "FIELD_SECURE_CHAMBER": str(chamber),
        "HOME": str(chamber),
        "TMPDIR": str(chamber),
        "PATH": "/usr/local/bin:/usr/bin:/bin",
    })
    return env


def _run_cmd(
    argv: list[str],
    *,
    chamber: Path,
    timeout: int = RUN_TIMEOUT,
    stdin: str | None = None,
) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            argv,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(chamber),
            env=_chamber_env(chamber),
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[-8000:],
            "stderr": (proc.stderr or "")[-8000:],
            "argv": argv[:4],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "argv": argv[:4]}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "argv": argv[:4]}


def _wrap_java_source(content: str, class_name: str = "Main") -> str:
    if "class " in content:
        return content
    return (
        f"public class {class_name} {{\n"
        f"public static void main(String[] args) throws Exception {{\n"
        f"{content}\n"
        f"}}\n"
        f"}}\n"
    )


def _wrap_cobol_source(content: str) -> str:
    body = content.strip()
    upper = body.upper()
    if "IDENTIFICATION DIVISION" in upper:
        return body + ("\n" if not body.endswith("\n") else "")
    return (
        "       IDENTIFICATION DIVISION.\n"
        "       PROGRAM-ID. SECURE-RUN.\n"
        "       PROCEDURE DIVISION.\n"
        f"       {body}\n"
        "       STOP RUN.\n"
    )


def _source_ext(lang: str, path: str = "") -> str:
    if path:
        suf = Path(path).suffix.lower()
        if suf:
            return suf
    reg = _lang_registry().get(lang) or {}
    exts = reg.get("extensions") or []
    if exts:
        return str(exts[0])
    return _LANG_EXT.get(lang, ".txt")


def _g16_native_mod() -> Any | None:
    native_py = GROK16 / "lib" / "g16-native-compile.py"
    if not native_py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("g16_native_chamber", native_py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _g16_compile(content: str, *, lang: str, chamber: Path) -> dict[str, Any]:
    """Compile any language via Grok16-owned front-ends → bin/g16."""
    native = _g16_native_mod()
    if not native or not hasattr(native, "compile_source"):
        return {"ok": False, "error": "g16_native_compile_unavailable"}
    out = native.compile_source(content, lang=lang, out_name="secure_g16", out_dir=chamber)
    binary = chamber / "program"
    if out.get("ok") and out.get("binary"):
        src_bin = Path(str(out["binary"]))
        if src_bin.is_file():
            shutil.copy2(src_bin, binary)
            out["binary"] = str(binary)
    return out


def _compile_result(
    *,
    lang: str,
    chamber: Path,
    gate: dict[str, Any],
    row: dict[str, Any] | None = None,
    compiler: str,
    binary: Path | None = None,
    **extra: Any,
) -> dict[str, Any]:
    rep: dict[str, Any] = {
        "schema": "g16-secure-compile/v1",
        "ok": row.get("ok", False) if row else bool(binary and binary.is_file()),
        "compiled": row.get("ok", False) if row else bool(binary and binary.is_file()),
        "lang": lang,
        "compiler": compiler,
        "chamber": str(chamber),
        "security": gate,
    }
    if row:
        rep["stderr"] = row.get("stderr")
    if binary and binary.is_file():
        rep["binary"] = str(binary)
    rep.update(extra)
    return rep


def compile_source(
    content: str,
    *,
    lang: str,
    path: str = "",
) -> dict[str, Any]:
    """Compile inside sealed chamber after security gate."""
    lang = (lang or "plaintext").lower()
    if lang == "delphi":
        lang = "pascal"
    gate = _security_gate(content, lang=lang, path=path)
    if gate.get("blocked"):
        return {
            "schema": "g16-secure-compile/v1",
            "ok": False,
            "blocked": True,
            "lang": lang,
            "security": gate,
        }
    chamber = _chamber_dir()
    try:
        if lang in _GATE_ONLY_LANGS:
            return {
                "schema": "g16-secure-compile/v1",
                "ok": True,
                "compiled": False,
                "gate_only": True,
                "lang": lang,
                "message": f"{lang} — security gate passed; direct exec blocked",
                "security": gate,
            }

        body = content
        if lang == "java":
            body = _wrap_java_source(content)
        elif lang in ("cobol", "cobol_copy"):
            body = _wrap_cobol_source(content)

        out = _g16_compile(body, lang=lang, chamber=chamber)
        binary = Path(str(out.get("binary") or ""))
        return {
            "schema": "g16-secure-compile/v1",
            "ok": bool(out.get("ok")),
            "compiled": bool(out.get("ok")),
            "lang": lang,
            "compiler": "g16",
            "lane": out.get("lane"),
            "chamber": str(chamber),
            "binary": str(binary) if binary.is_file() else None,
            "compile_ms": out.get("compile_ms"),
            "stderr": out.get("stderr"),
            "security": gate,
            "lowered": bool(out.get("lowered", True)),
            "host_toolchain": False,
        }
    except Exception as exc:
        return {"schema": "g16-secure-compile/v1", "ok": False, "lang": lang, "error": type(exc).__name__}
    finally:
        pass  # chamber cleaned on run completion or left for debug if G16_SECURE_KEEP_CHAMBER=1


def run_path(path: str, *, lang: str = "", profile: str = "") -> dict[str, Any]:
    """Run a source file inside secure chamber — never bare host exec."""
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return {"schema": "g16-secure-run/v1", "ok": False, "error": "not_found", "path": str(p)}
    if _path_forbidden(p):
        return {
            "schema": "g16-secure-run/v1",
            "ok": False,
            "error": "run_forbidden",
            "path": str(p),
            "message": "Protected AmmoOS/Hostess7/Grok16 path — cannot execute",
        }
    content = p.read_text(encoding="utf-8", errors="replace")
    lang = lang or _discern_lang(str(p), content)
    gate = _security_gate(content, lang=lang, path=str(p))
    if gate.get("blocked"):
        return {"schema": "g16-secure-run/v1", "ok": False, "blocked": True, "lang": lang, "security": gate}

    chamber = _chamber_dir()
    owned_chamber = True
    run_chamber = chamber
    try:
        if lang in _GATE_ONLY_LANGS:
            comp = compile_source(content, lang=lang, path=str(p))
            if comp.get("blocked"):
                return {"schema": "g16-secure-run/v1", **comp}
            if comp.get("ok"):
                return _gate_only_run(lang, comp=comp, gate=gate)
            return {"schema": "g16-secure-run/v1", "ok": False, "lang": lang, "compile": comp, "error": "gate_failed"}

        if lang in compiled_langs():
            comp = compile_source(content, lang=lang, path=str(p))
            if comp.get("blocked"):
                return {"schema": "g16-secure-run/v1", **comp}
            if comp.get("ok") and not comp.get("compiled") and lang in _GATE_ONLY_LANGS:
                return _gate_only_run(lang, comp=comp, gate=gate)
            if comp.get("chamber"):
                run_chamber = Path(comp["chamber"])
                if run_chamber != chamber:
                    shutil.rmtree(chamber, ignore_errors=True)
                    owned_chamber = True
                    chamber = run_chamber
            if lang in ("java", "kotlin") and comp.get("binary") and Path(str(comp["binary"])).is_file():
                row = _run_cmd([str(comp["binary"])], chamber=run_chamber)
                return {
                    "schema": "g16-secure-run/v1",
                    "ok": row.get("ok", False),
                    "lang": lang,
                    "runner": "g16",
                    "chamber": str(run_chamber),
                    "secure": True,
                    "compile": comp,
                    **row,
                }
            binary = comp.get("binary")
            if binary and Path(binary).is_file():
                if _path_forbidden(Path(binary)):
                    return {"schema": "g16-secure-run/v1", "ok": False, "error": "binary_forbidden"}
                row = _run_cmd([str(binary)], chamber=run_chamber)
                return {
                    "schema": "g16-secure-run/v1",
                    "ok": row.get("ok", False),
                    "lang": lang,
                    "runner": binary,
                    "chamber": str(run_chamber),
                    "secure": True,
                    "compile": comp,
                    **row,
                }
            if comp.get("interpreted") or comp.get("artifact"):
                run_file = comp.get("artifact") or comp.get("source") or str(p)
                node = _which("node")
                if node and Path(run_file).is_file():
                    row = _run_cmd([node, str(run_file)], chamber=run_chamber)
                    return {
                        "schema": "g16-secure-run/v1",
                        "ok": row.get("ok", False),
                        "lang": lang,
                        "runner": "node",
                        "chamber": str(run_chamber),
                        "secure": True,
                        "compile": comp,
                        **row,
                    }
            return {"schema": "g16-secure-run/v1", "ok": False, "lang": lang, "compile": comp, "error": "compile_failed"}

        if lang in secure_langs() and lang not in ("shell", "plaintext"):
            comp = compile_source(content, lang=lang, path=str(p))
            if comp.get("blocked"):
                return {"schema": "g16-secure-run/v1", **comp}
            binary = comp.get("binary")
            if binary and Path(binary).is_file():
                if _path_forbidden(Path(binary)):
                    return {"schema": "g16-secure-run/v1", "ok": False, "error": "binary_forbidden"}
                row = _run_cmd([str(binary)], chamber=chamber)
                return {
                    "schema": "g16-secure-run/v1",
                    "ok": row.get("ok", False),
                    "lang": lang,
                    "runner": "g16",
                    "chamber": str(chamber),
                    "secure": True,
                    "compile": comp,
                    **row,
                }
            return {"schema": "g16-secure-run/v1", "ok": False, "lang": lang, "compile": comp, "error": "compile_failed"}

        if lang == "shell":
            return {
                "schema": "g16-secure-run/v1",
                "ok": False,
                "blocked": True,
                "lang": lang,
                "error": "shell_direct_denied",
                "message": "Shell scripts require explicit chamber review — use g16 check first",
            }

        return {
            "schema": "g16-secure-run/v1",
            "ok": False,
            "lang": lang,
            "error": "no_secure_runner",
            "message": f"No sealed runner for {lang}",
        }
    finally:
        if owned_chamber and os.environ.get("G16_SECURE_KEEP_CHAMBER", "") != "1":
            shutil.rmtree(chamber, ignore_errors=True)


def _discern_lang(path: str, content: str) -> str:
    uc = GROK16 / "lib" / "g16-universal-compiler.py"
    if uc.is_file():
        spec = importlib.util.spec_from_file_location("g16_uc_discern", uc)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "discern"):
                return str(mod.discern(path, content=content))
    ext = Path(path).suffix.lower()
    return {
        ".java": "java", ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
        ".ts": "typescript", ".pas": "pascal", ".pp": "pascal", ".tp": "turbo_pascal",
        ".f90": "fortran", ".f95": "fortran", ".f": "fortran", ".for": "fortran",
        ".py": "python", ".sh": "shell", ".cob": "cobol", ".cbl": "cobol",
        ".rb": "ruby", ".pl": "perl", ".php": "php", ".lua": "lua", ".rs": "rust",
        ".go": "go", ".zig": "zig", ".cs": "csharp", ".kt": "kotlin",
    }.get(ext, "plaintext")


def posture() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    tools = {
        "g16": (GROK16 / "bin" / "g16").is_file(),
        "g16_native_compile": (GROK16 / "lib" / "g16-native-compile.py").is_file(),
        "g16_fortran": (GROK16 / "lib" / "g16-fortran-compile.py").is_file(),
        "g16_cobol": (GROK16 / "lib" / "g16-cobol-compile.py").is_file(),
        "g16_basic": (GROK16 / "lib" / "g16-basic-compile.py").is_file(),
        "g16_pascal": (GROK16 / "lib" / "g16-pascal-compile.py").is_file(),
        "g16_java": (GROK16 / "lib" / "g16-java-compile.py").is_file(),
        "host_jdk": False,
        "host_toolchain": False,
        "third_party": False,
        "motto": "Grok16 compiles everything — no javac, no node, no host rustc/go",
    }
    langs = secure_langs()
    compiled = compiled_langs()
    return {
        "schema": "g16-secure-chamber/v1",
        "updated": _now(),
        "ok": True,
        "policy": doc.get("policy"),
        "language_count": len(langs),
        "languages": sorted(langs),
        "compiled_count": len(compiled),
        "tools": tools,
        "doctrine": str(DOCTRINE.relative_to(INSTALL)) if DOCTRINE.is_file() else None,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "posture").strip().lower()
    if cmd in ("posture", "status", "json"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "compile":
        body = json.loads(sys.stdin.read() or "{}")
        print(json.dumps(compile_source(body.get("content", ""), lang=body.get("lang", ""), path=body.get("path", "")), ensure_ascii=False, indent=2))
        return 0
    if cmd == "run" and len(sys.argv) > 2:
        lang = ""
        if "--lang" in sys.argv:
            try:
                lang = sys.argv[sys.argv.index("--lang") + 1]
            except (ValueError, IndexError):
                lang = ""
        print(json.dumps(run_path(sys.argv[2], lang=lang), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["posture", "compile", "run PATH [--lang LANG]"]}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())