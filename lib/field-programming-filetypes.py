#!/usr/bin/env python3
"""Canonical programming filetype DB — discern, actions, run/compile dispatch."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
SG = Path(os.environ.get("SG_ROOT", ROOT.parent))
from sg_paths import grok16_root

GROK16 = grok16_root()
DB_PATH = ROOT / "data" / "field-programming-filetypes.json"


def _load() -> dict[str, Any]:
    for p in (DB_PATH, GROK16 / "data" / "field-programming-filetypes.json"):
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    return {"extensions": {}, "mime_hints": {}, "actions_by_language": {}}


def _basename_key(path: str) -> str:
    return Path(path).name.lower()


def is_binary_extension(path: str) -> bool:
    doc = _load()
    eras = doc.get("text_eras") or {}
    suf = Path(path).suffix.lower()
    return suf in set(eras.get("binary_extensions") or [])


def is_text_basename(path: str) -> bool:
    doc = _load()
    eras = doc.get("text_eras") or {}
    name = _basename_key(path)
    return name in set(eras.get("basename_plaintext") or [])


def is_likely_binary(data: bytes) -> bool:
    if not data:
        return False
    sample = data[:8192]
    if b"\x00" in sample:
        return True
    if len(sample) < 32:
        return False
    textish = sum(1 for b in sample if b in (9, 10, 13) or 32 <= b < 127 or b >= 128)
    return (textish / len(sample)) < 0.82


def _encoding_ladder() -> list[str]:
    doc = _load()
    eras = doc.get("text_eras") or {}
    return list(eras.get("encodings") or ["utf-8-sig", "utf-8", "latin-1"])


def _decode_text(raw: bytes) -> tuple[str, str]:
    for enc in _encoding_ladder():
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8-replace"


def _text_era_label(path: str, encoding: str) -> str:
    name = _basename_key(path)
    suf = Path(path).suffix.lower()
    if encoding in ("cp437", "cp850"):
        return "dos"
    if name in ("autoexec.bat", "config.sys") or suf in (".nfo", ".diz", ".ans", ".asc"):
        return "bbs_dos"
    if suf in (".bas", ".prg") or name.endswith(".bas"):
        return "basic_era"
    if suf in (".f", ".f77", ".f90", ".for"):
        return "fortran_era"
    if suf in (".cob", ".cbl"):
        return "cobol_era"
    if suf in (".pas", ".pp", ".dpr"):
        return "pascal_era"
    if encoding.startswith("utf-16"):
        return "unicode_wide"
    if encoding in ("utf-8", "utf-8-sig"):
        return "modern"
    if encoding == "latin-1":
        return "latin_era"
    return "text"


def read_text_file(path: str) -> dict[str, Any]:
    """Open any text-era file — binary guard, encoding ladder, language discern."""
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return {"ok": False, "error": "not_found", "path": str(p)}
    if is_binary_extension(str(p)) and not is_text_basename(str(p)):
        return {"ok": False, "error": "binary_extension", "path": str(p)}
    try:
        raw = p.read_bytes()
    except OSError as exc:
        return {"ok": False, "error": str(exc), "path": str(p)}
    force_text = is_text_basename(str(p)) or discern(str(p)) != "plaintext" or Path(str(p)).suffix.lower() in _load().get("extensions", {})
    if is_likely_binary(raw) and not force_text:
        return {"ok": False, "error": "binary_file", "path": str(p), "size": len(raw)}
    text, encoding = _decode_text(raw)
    lang = discern(str(p), content=text[:4096])
    return {
        "ok": True,
        "path": str(p),
        "content": text,
        "language": lang,
        "encoding": encoding,
        "era": _text_era_label(str(p), encoding),
        "size": len(raw),
        "text_open": True,
    }


def discern(path: str = "", *, mime: str = "", content: str = "") -> str:
    g16 = GROK16 / "bin" / "g16"
    if path and g16.is_file():
        try:
            proc = subprocess.run(
                [str(g16), "--g16-discern", path],
                capture_output=True, text=True, timeout=8,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
    doc = _load()
    if path:
        suf = Path(path).suffix.lower()
        hit = (doc.get("extensions") or {}).get(suf)
        if hit:
            return str(hit)
        name = Path(path).name.lower()
        eras = doc.get("text_eras") or {}
        if name in {b.lower() for b in (eras.get("basename_plaintext") or [])}:
            if "docker" in name:
                return "dockerfile"
            if "make" in name or name == "cmakelists.txt":
                return "makefile"
            if name in ("autoexec.bat", "config.sys"):
                return "shell"
            if name in (".gitignore", ".gitattributes", ".dockerignore", ".editorconfig", ".env"):
                return "ini"
            return "plaintext"
        if name in ("dockerfile", "containerfile"):
            return "dockerfile"
        if name in ("makefile", "gnumakefile"):
            return "makefile"
        if name in ("autoexec.bat", "config.sys"):
            return "shell"
    if mime:
        hit = (doc.get("mime_hints") or {}).get(mime.lower())
        if hit:
            return str(hit)
    return "plaintext"


def actions(lang: str) -> dict[str, str]:
    doc = _load()
    return dict((doc.get("actions_by_language") or {}).get(lang) or {"default": "edit", "edit": "ammocode"})


def special_handler(path: str) -> str | None:
    doc = _load()
    suf = Path(path).suffix.lower()
    rel = (doc.get("special_handlers") or {}).get(suf)
    if not rel:
        return None
    for base in (ROOT, SG):
        cand = base / rel
        if cand.is_file():
            return str(cand)
    return None


def _secure_chamber_mod() -> Any | None:
    path = ROOT / "lib" / "g16-secure-chamber.py"
    if not path.is_file():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location("g16_secure_chamber_ft", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _uni_mod() -> Any | None:
    path = GROK16 / "lib" / "g16-universal-compiler.py"
    if not path.is_file():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location("g16_universal", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_nd_mod_cache: Any | None = None


def _nd_mod() -> Any | None:
    """AmmoCode non-destructive guard — optional when AmmoCode is on the stack."""
    global _nd_mod_cache
    if _nd_mod_cache is not None:
        return _nd_mod_cache
    for cand in (
        SG / "NewLatest" / "AmmoCode" / "server" / "ammocode-nondestructive.py",
        SG / "AmmoCode" / "server" / "ammocode-nondestructive.py",
        ROOT / "AmmoCode" / "server" / "ammocode-nondestructive.py",
    ):
        if not cand.is_file():
            continue
        import importlib.util
        spec = importlib.util.spec_from_file_location("ammocode_nd", cand)
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _nd_mod_cache = mod
        return mod
    return None


def run_path(path: str, *, profile: str = "belt_2_0") -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return {"ok": False, "error": "not_found", "path": str(p)}
    nd = _nd_mod()
    if nd and hasattr(nd, "assert_run"):
        blocked = nd.assert_run(str(p))
        if blocked:
            return blocked
    handler = special_handler(str(p))
    if handler:
        proc = subprocess.run([handler, str(p)], capture_output=True, text=True, timeout=300)
        return {"ok": proc.returncode == 0, "handler": handler, "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[-4000:], "stderr": (proc.stderr or "")[-4000:]}
    lang = discern(str(p))
    act = actions(lang).get("run", "g16_check")
    if act == "secure_chamber":
        sec = _secure_chamber_mod()
        if sec and hasattr(sec, "run_path"):
            return sec.run_path(str(p), lang=lang)
    uni = _uni_mod()
    if uni and hasattr(uni, "run_file"):
        return uni.run_file(str(p), lang=lang, profile=profile)
    content = p.read_text(encoding="utf-8", errors="replace")
    if act == "g16_shell" or lang == "shell":
        proc = subprocess.run(["/bin/bash", str(p)], capture_output=True, text=True, timeout=120)
        return {"ok": proc.returncode == 0, "lang": lang, "runner": "bash",
                "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}
    if uni and hasattr(uni, "compile_source") and act in ("g16_run", "native_compile_run", "g16"):
        out = uni.compile_source(content, lang=lang, path=str(p), profile=profile)
        return {"ok": bool(out.get("ok")), "lang": lang, "compile": out}
    return {"ok": False, "lang": lang, "error": "no_runner", "action": act}


def compile_path(path: str, *, profile: str = "belt_2_0") -> dict[str, Any]:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return {"ok": False, "error": "not_found"}
    lang = discern(str(p))
    act = actions(lang).get("compile", "g16")
    if act == "secure_chamber":
        sec = _secure_chamber_mod()
        if sec and hasattr(sec, "compile_source"):
            content = p.read_text(encoding="utf-8", errors="replace")
            return sec.compile_source(content, lang=lang, path=str(p))
    if lang in ("glsl_compute", "spirv", "glsl_rt"):
        rtx_open = ROOT / "scripts" / "amouranthrtx-open.sh"
        if rtx_open.is_file():
            proc = subprocess.run([str(rtx_open), str(p)], capture_output=True, text=True, timeout=120)
            return {"ok": proc.returncode == 0, "lang": lang, "compiler": "glslc", "stderr": proc.stderr[-2000:]}
    uni = _uni_mod()
    if uni and hasattr(uni, "compile_source"):
        content = p.read_text(encoding="utf-8", errors="replace")
        return uni.compile_source(content, lang=lang, path=str(p), profile=profile)
    return {"ok": False, "error": "compiler_unavailable", "lang": lang}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").lower()
    if cmd == "status":
        doc = _load()
        print(json.dumps({
            "schema": "field-programming-filetypes/v1",
            "extensions": len(doc.get("extensions") or {}),
            "languages": len(doc.get("languages") or []),
            "db": str(DB_PATH),
        }, indent=2))
        return 0
    if cmd == "discern" and len(sys.argv) > 2:
        print(discern(sys.argv[2]))
        return 0
    if cmd == "actions" and len(sys.argv) > 2:
        print(json.dumps(actions(discern(sys.argv[2])), indent=2))
        return 0
    if cmd == "run" and len(sys.argv) > 2:
        print(json.dumps(run_path(sys.argv[2]), indent=2))
        return 0 if run_path(sys.argv[2]).get("ok") else 1
    if cmd == "compile" and len(sys.argv) > 2:
        print(json.dumps(compile_path(sys.argv[2]), indent=2))
        return 0 if compile_path(sys.argv[2]).get("ok") else 1
    print(json.dumps({"error": "usage", "cmds": ["status", "discern", "actions", "run", "compile"]}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())