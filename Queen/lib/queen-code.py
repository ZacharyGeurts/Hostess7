#!/usr/bin/env pythong
"""Queen Code — g16-aware code viewer. No telemetry. Loopback + path jail only."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
_SG_PATHS_LIB = Path(__file__).resolve().parents[2] / "lib"
if str(_SG_PATHS_LIB) not in sys.path:
    sys.path.insert(0, str(_SG_PATHS_LIB))
from sg_paths import grok16_root

GROK16 = grok16_root()
LANG_DOC = QUEEN / "data" / "queen-code-languages.json"
RECENT_DOC = QUEEN / "data" / "queen-code-recent.json"
MAX_READ = int(os.environ.get("QUEEN_CODE_MAX_BYTES", str(2 * 1024 * 1024)))
MAX_RECENT = int(os.environ.get("QUEEN_CODE_MAX_RECENT", "24"))


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _file_browser():
    spec = importlib.util.spec_from_file_location("qfb", QUEEN / "lib" / "queen-file-browser.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _grok16_version() -> dict[str, Any]:
    doc = _load(GROK16 / "data" / "grok16-version.json", {})
    return doc if doc else {"g16_version": "16.2.0", "distro_version": "2.0.0", "discern": []}


def _load_recent() -> list[dict[str, Any]]:
    doc = _load(RECENT_DOC, {"schema": "queen-code-recent/v1", "files": []})
    return list(doc.get("files") or [])


def _save_recent(files: list[dict[str, Any]]) -> None:
    RECENT_DOC.parent.mkdir(parents=True, exist_ok=True)
    RECENT_DOC.write_text(
        json.dumps({"schema": "queen-code-recent/v1", "files": files[:MAX_RECENT]}, indent=2) + "\n",
        encoding="utf-8",
    )


def touch_recent(path: str, *, language: str = "") -> dict[str, Any]:
    real = str(path or "").strip()
    if not real:
        return {"ok": False, "error": "path_required"}
    files = [f for f in _load_recent() if f.get("path") != real]
    files.insert(0, {"path": real, "language": language or _g16_discern(real), "ts": _now_iso()})
    _save_recent(files)
    return {"ok": True, "recent": files[:MAX_RECENT]}


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def recent_files() -> dict[str, Any]:
    return {"ok": True, "schema": "queen-code-recent/v1", "files": _load_recent()}


def language_registry() -> dict[str, Any]:
    doc = _load(LANG_DOC, {})
    g16 = _grok16_version()
    discern = list(g16.get("discern") or doc.get("g16_discern") or [])
    return {
        "schema": "queen-code/v1",
        "ok": True,
        "title": "Queen Code",
        "motto": doc.get("motto") or "g16 languages · no telemetry",
        "telemetry": False,
        "g16": {
            "version": g16.get("g16_version"),
            "distro": g16.get("distro_version"),
            "discern": discern,
            "belt_profile": (g16.get("belt") or {}).get("default_profile", "belt_2_0"),
        },
        "extensions": doc.get("extensions") or {},
        "profiles": doc.get("profiles") or {},
        "languages": sorted(set(discern + list({v for v in (doc.get("extensions") or {}).values()}))),
    }


def _ext_lang(path: str) -> str:
    doc = _load(LANG_DOC, {})
    ext_map = doc.get("extensions") or {}
    suf = Path(path).suffix
    if suf in ext_map:
        return str(ext_map[suf])
    low = suf.lower()
    for k, v in ext_map.items():
        if k.lower() == low:
            return str(v)
    return "plaintext"


def _g16_discern(path: str) -> str:
    g16 = GROK16 / "bin" / "g16"
    if not g16.is_file():
        return _ext_lang(path)
    try:
        proc = subprocess.run(
            [str(g16), "--g16-discern", path],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return _ext_lang(path)


def _read_text(path: str) -> dict[str, Any]:
    fb = _file_browser()
    if not fb:
        return {"ok": False, "error": "file_browser_missing"}
    resolved = fb.dispatch({"action": "resolve", "path": path})
    if not resolved.get("ok"):
        return resolved
    real = Path(str(resolved.get("resolved") or ""))
    if not real.is_file():
        return {"ok": False, "error": "not_a_file", "path": str(real)}
    size = real.stat().st_size
    if size > MAX_READ:
        return {"ok": False, "error": "file_too_large", "bytes": size, "max": MAX_READ}
    scan = fb.dispatch({"action": "scan", "path": str(real)})
    virus_advisory = None
    if scan and not scan.get("ok"):
        virus_advisory = scan.get("field_virus")
    try:
        text = real.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    lang = _g16_discern(str(real))
    lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    touch_recent(str(real), language=lang)
    return {
        "ok": True,
        "path": str(real),
        "language": lang,
        "g16_discern": lang,
        "bytes": size,
        "lines": lines,
        "content": text,
        "readonly": False,
        "telemetry": False,
        "field_virus_advisory": virus_advisory,
        "recent": _load_recent(),
    }


def _write_text(path: str, content: str) -> dict[str, Any]:
    fb = _file_browser()
    if not fb:
        return {"ok": False, "error": "file_browser_missing"}
    resolved = fb.dispatch({"action": "resolve", "path": path})
    if not resolved.get("ok"):
        return resolved
    real = Path(str(resolved.get("resolved") or ""))
    if len(content.encode("utf-8")) > MAX_READ:
        return {"ok": False, "error": "content_too_large"}
    scan = fb.dispatch({"action": "scan", "path": str(real), "direction": "egress"})
    if scan and not scan.get("ok"):
        return {"ok": False, "error": "field_virus_hold", "field_virus": scan.get("field_virus")}
    try:
        real.parent.mkdir(parents=True, exist_ok=True)
        real.write_text(content, encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "path": str(real), "bytes": len(content.encode("utf-8")), "saved": True}


def _g16_check(path: str, *, profile: str = "belt_2_0") -> dict[str, Any]:
    g16 = GROK16 / "bin" / "g16"
    if not g16.is_file():
        return {"ok": False, "error": "g16_missing", "hint": "GROK16_ROOT bootstrap"}
    resolved = _read_text(path)
    if not resolved.get("ok"):
        return resolved
    real = Path(resolved["path"])
    lang = resolved.get("g16_discern") or "cxx"
    flags_py = GROK16 / "scripts" / "grok16-profile-flags.py"
    extra = ""
    if flags_py.is_file() and lang in ("c", "cxx"):
        kind = "cxx" if lang == "cxx" else "c"
        try:
            proc = subprocess.run(
                [sys.executable, str(flags_py), profile, kind],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
                env={**os.environ, "GROK16_ROOT": str(GROK16), "G16_PREFIX": str(GROK16)},
            )
            extra = (proc.stdout or "").strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
    if lang == "python":
        cmd = [str(g16), "-m", "py_compile", str(real)]
    elif lang in ("c", "cxx"):
        out = real.with_suffix(real.suffix + ".queen-code.o")
        cmd = [str(g16), *extra.split(), "-fsyntax-only", str(real)] if extra else [str(g16), "-fsyntax-only", str(real)]
        _ = out
    else:
        return {
            "ok": True,
            "checked": "discern_only",
            "language": lang,
            "profile": profile,
            "message": f"g16 discern={lang} — syntax check via g16 for c/cxx/python",
        }
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": proc.returncode == 0,
        "language": lang,
        "profile": profile,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[-2000:],
        "stderr": (proc.stderr or "")[-4000:],
    }


def _g16_build(path: str, *, profile: str = "belt_2_0") -> dict[str, Any]:
    g16 = GROK16 / "bin" / "g16"
    if not g16.is_file():
        return {"ok": False, "error": "g16_missing"}
    resolved = _read_text(path)
    if not resolved.get("ok"):
        return resolved
    real = Path(resolved["path"])
    lang = resolved.get("g16_discern") or "cxx"
    out_bin = real.with_suffix(real.suffix + ".queen-build")
    flags: list[str] = []
    flags_py = GROK16 / "scripts" / "grok16-profile-flags.py"
    if flags_py.is_file() and lang in ("c", "cxx"):
        kind = "cxx" if lang == "cxx" else "c"
        try:
            proc = subprocess.run(
                [sys.executable, str(flags_py), profile, kind],
                capture_output=True, text=True, timeout=15, check=False,
                env={**os.environ, "GROK16_ROOT": str(GROK16), "G16_PREFIX": str(GROK16)},
            )
            flags = [f for f in (proc.stdout or "").split() if f]
        except (OSError, subprocess.TimeoutExpired):
            pass
    if lang in ("c", "cxx"):
        cmd = [str(g16), *flags, "-o", str(out_bin), str(real)]
    elif lang == "python":
        cmd = [str(g16), "-m", "py_compile", str(real)]
        out_bin = real
    else:
        return {"ok": False, "error": "unsupported_build_lang", "language": lang}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False, cwd=str(real.parent))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": proc.returncode == 0,
        "language": lang,
        "profile": profile,
        "artifact": str(out_bin),
        "message": f"g16 build {'OK' if proc.returncode == 0 else 'failed'} · {lang} · {profile}",
        "stderr": (proc.stderr or "")[-4000:],
        "stdout": (proc.stdout or "")[-2000:],
    }


def _g16_run_python(path: str, *, profile: str = "belt_2_0") -> dict[str, Any]:
    resolved = _read_text(path)
    if not resolved.get("ok"):
        return resolved
    real = Path(resolved["path"])
    drivers = [
        GROK16 / "bin" / "gpy-16",
        Path(os.environ.get("NEXUS_PYTHONG", "")),
        GROK16 / "python" / "bin" / "pythong",
    ]
    driver = next((d for d in drivers if d and Path(str(d)).is_file()), None)
    if not driver:
        driver = Path(sys.executable)
    env = {**os.environ, "GROK16_ROOT": str(GROK16), "GPY16_FIELD": "1", "PYTHONG_FIELD": "1"}
    try:
        proc = subprocess.run(
            [str(driver), str(real)],
            capture_output=True, text=True, timeout=30, check=False, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": proc.returncode == 0,
        "driver": str(driver),
        "profile": profile,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-4000:],
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json"):
        out = language_registry()
        out["recent"] = _load_recent()
        return out
    if action in ("languages", "registry"):
        return language_registry()
    if action in ("recent", "recent_files"):
        return recent_files()
    if action == "touch_recent":
        return touch_recent(str(body.get("path") or ""), language=str(body.get("language") or ""))
    if action in ("read", "open", "load"):
        return _read_text(str(body.get("path") or ""))
    if action in ("write", "save"):
        return _write_text(str(body.get("path") or ""), str(body.get("content") or ""))
    if action in ("discern", "detect_language"):
        path = str(body.get("path") or body.get("filename") or "")
        return {"ok": True, "path": path, "language": _g16_discern(path), "g16_discern": _g16_discern(path)}
    if action in ("g16_check", "check", "compile_check", "syntax"):
        return _g16_check(
            str(body.get("path") or ""),
            profile=str(body.get("profile") or "belt_2_0"),
        )
    if action in ("g16_build", "build"):
        return _g16_build(str(body.get("path") or ""), profile=str(body.get("profile") or "belt_2_0"))
    if action in ("g16_run_python", "run_python"):
        return _g16_run_python(str(body.get("path") or ""), profile=str(body.get("profile") or "belt_2_0"))
    return {
        "ok": False,
        "error": "unknown_action",
        "actions": ["status", "languages", "read", "write", "discern", "g16_check", "g16_build", "g16_run_python", "recent", "touch_recent"],
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(language_registry(), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-code.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())