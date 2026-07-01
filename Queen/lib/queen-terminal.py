#!/usr/bin/env pythong
"""Queen GNU Terminal — field-native shell; understands loaded KILROY kernel."""
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
GPY = SG / "GrokPy"

DANGEROUS = re.compile(
    r"(rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|-f\s+).*(/|\$HOME|~)|"
    r"\brm\s+-rf\b|mkfs|>\s*/dev/|dd\s+if=|:\(\)\{|"
    r"\b(shutdown|reboot|halt|poweroff)\b|curl\s+[^\n]*\|\s*(ba)?sh)",
    re.I,
)

ALLOWED_BASES = frozenset({
    "ls", "pwd", "echo", "cat", "head", "tail", "grep", "find", "wc", "whoami",
    "date", "env", "which", "file", "stat", "tree", "du", "df", "uname",
    "g16", "g16-gcc", "g16-g++", "g16-as", "g16-ld", "g16-objdump", "g16-nm",
    "gpy-16", "pythong", "python", "python3",
    "git", "make", "bash", "sh", "clear", "history", "true", "false", "test",
    "dirname", "basename", "realpath", "readlink",
    "kilroy", "kilroy-status", "kernel", "discern",
    "ammolang-run.sh", "export", "cd",
})

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(QUEEN.parent / "NewLatest")))

_KILROY_PROC_PREFIX = "/proc/kilroy_field/"


def _field_paths_mod() -> Any:
    spec = importlib.util.spec_from_file_location("field_paths", QUEEN / "lib" / "forge" / "field_paths.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _kilroy_root() -> Path:
    env = os.environ.get("KILROY_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_dir():
            return p
    fp = _field_paths_mod()
    if fp:
        return fp.kilroy_root(QUEEN)
    for candidate in (SG.parent / "KILROY", SG / "KILROY", Path.home() / "Desktop" / "KILROY"):
        if candidate.is_dir():
            return candidate.resolve()
    return (SG / "KILROY").resolve()


def _kernel_slice() -> dict[str, Any]:
    fp = _field_paths_mod()
    runtime = fp.kernel_runtime() if fp else {}
    kr = _kilroy_root()
    ai_mode = "home"
    mandate = kr / "data" / "kilroy-ai-mandate.json"
    if mandate.is_file():
        try:
            ai_mode = json.loads(mandate.read_text(encoding="utf-8")).get("default_mode") or "home"
        except (OSError, json.JSONDecodeError):
            pass
    proc_ai = ""
    try:
        proc_ai = Path("/proc/kilroy_field/ai").read_text(encoding="utf-8", errors="replace")[:400]
    except OSError:
        pass
    return {
        **runtime,
        "kilroy_root": str(kr),
        "kilroy_present": kr.is_dir(),
        "ai_default_mode": ai_mode,
        "proc_ai_snippet": proc_ai or None,
    }


def _cwd_bases() -> list[Path]:
    bases: list[Path] = []
    kr = _kilroy_root()
    if kr.is_dir():
        bases.append(kr.resolve())
    bases.append(SG.resolve())
    return bases


def _default_cwd() -> Path:
    bases = _cwd_bases()
    return bases[0]


def _field_env() -> dict[str, str]:
    g16_bin = str(GROK16 / "bin")
    g16_libexec = str(GROK16 / "libexec" / "grok16")
    gpy_bin = str(GPY / "bin")
    pyg_bin = str(SG / "PythonG" / "bin")
    kr = _kilroy_root()
    path = os.pathsep.join(
        p for p in (g16_bin, g16_libexec, gpy_bin, pyg_bin, os.environ.get("PATH", "")) if p
    )
    return {
        **os.environ,
        "SG_ROOT": str(SG),
        "QUEEN_ROOT": str(QUEEN),
        "KILROY_ROOT": str(kr),
        "GROK16_ROOT": str(GROK16),
        "GPY16_ROOT": str(GPY),
        "PATH": path,
        "QUEEN_SOVEREIGN": "1",
        "NEXUS_QUEEN_SOVEREIGN": "1",
        "KILROY_AI_DEFAULT_MODE": _kernel_slice().get("ai_default_mode") or "home",
    }


def _path_in_bases(candidate: Path, bases: list[Path]) -> bool:
    for base in bases:
        try:
            candidate.relative_to(base)
            return True
        except ValueError:
            continue
    return False


def _safe_cwd(raw: str) -> Path:
    bases = _cwd_bases()
    default = _default_cwd()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = (default / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not _path_in_bases(candidate, bases):
        return default
    if not candidate.is_dir():
        return default
    return candidate


def _resolve_cd(cwd: Path, cmd: str) -> tuple[Path, str]:
    bases = _cwd_bases()
    default = _default_cwd()
    rest = cmd[2:].strip() if len(cmd) > 2 else ""
    if not rest or rest == "~":
        return default, ""
    if rest == "-":
        return cwd, "cd: '-' not tracked in Queen terminal session"
    target = Path(rest).expanduser()
    if not target.is_absolute():
        target = (cwd / target).resolve()
    else:
        target = target.resolve()
    if not _path_in_bases(target, bases):
        return cwd, f"cd: {rest}: outside field roots (KILROY + SG)"
    if not target.is_dir():
        return cwd, f"cd: {rest}: not a directory"
    return target, ""


def _cat_allowed(stripped: str) -> bool:
    parts = stripped.split(maxsplit=1)
    if len(parts) < 2 or parts[0] != "cat":
        return True
    target = parts[1].strip().split()[0]
    if target.startswith(_KILROY_PROC_PREFIX):
        return True
    try:
        p = Path(target).expanduser().resolve()
    except (OSError, RuntimeError):
        return False
    return _path_in_bases(p, _cwd_bases())


def _command_allowed(cmd: str) -> tuple[bool, str]:
    stripped = cmd.strip()
    if not stripped:
        return False, "empty command"
    if DANGEROUS.search(stripped):
        return False, "blocked for field safety"
    if stripped.startswith("cd") and (len(stripped) == 2 or stripped[2:3] in (" ", "\t")):
        return True, ""
    base = stripped.split()[0]
    if base in ("kilroy", "kilroy-status", "kernel"):
        return True, ""
    if base == "cat" and not _cat_allowed(stripped):
        return False, "cat: path outside field roots or proc"
    if stripped.startswith("./") or stripped.startswith("../"):
        rel = stripped.split()[0]
        resolved = (_default_cwd() / rel).resolve()
        if not _path_in_bases(resolved, _cwd_bases()):
            return False, "path outside field roots"
        return True, ""
    if base.endswith(".py") or base.endswith(".sh"):
        p = Path(base)
        if not p.is_absolute():
            p = (_default_cwd() / p).resolve()
        if not _path_in_bases(p, _cwd_bases()):
            return False, "script outside field roots"
        return True, ""
    if base in ALLOWED_BASES:
        return True, ""
    if base.startswith("g16-") or base.startswith("./"):
        return True, ""
    return False, f"blocked: {base!r} not in field allowlist"


def _discern_command(text: str, cwd: Path) -> dict[str, Any]:
    script = INSTALL / "lib" / "field-stress-terror-discern.py"
    if not script.is_file():
        script = QUEEN.parent / "NewLatest" / "lib" / "field-stress-terror-discern.py"
    if not script.is_file():
        return {"ok": False, "output": "discern module unavailable", "cwd": str(cwd)}
    try:
        spec = importlib.util.spec_from_file_location("field_stress_terror_discern", script)
        if not spec or not spec.loader:
            return {"ok": False, "output": "discern load failed", "cwd": str(cwd)}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        doc = mod.discern({
            "text": text,
            "source": "operator",
            "evidence": {"local_keystroke": True, "operator_anchor": True},
        })
        lines = [
            f"Stress: {doc.get('stress_detected')} · Terror: {doc.get('terror_detected')}",
            f"Origin: {doc.get('origin')} · Verdict: {doc.get('verdict')}",
            f"Shoot hold: {doc.get('shoot_hold')} · Lethal eligible: {doc.get('lethal_eligible')}",
            doc.get("guidance") or "",
        ]
        return {"ok": True, "output": "\n".join(l for l in lines if l), "cwd": str(cwd), "discern": doc}
    except Exception as exc:
        return {"ok": False, "output": str(exc)[:200], "cwd": str(cwd)}


def _format_kernel_status() -> str:
    k = _kernel_slice()
    lines = [
        "KILROY Field OS — kernel witness",
        f"  loaded: {'yes' if k.get('field_kernel_running') else 'no (host compat)'}",
        f"  proc/kilroy_field: {'live' if k.get('proc_kilroy_field') else 'absent'}",
        f"  dev/kilroy_field: {'present' if k.get('dev_kilroy_field') else 'absent'}",
        f"  is_kilroy: {k.get('is_kilroy')}",
        f"  AI default mode: {k.get('ai_default_mode')}",
        f"  KILROY_ROOT: {k.get('kilroy_root')}",
    ]
    version = k.get("kernel_version") or ""
    if version:
        lines.append(f"  version: {version[:120]}")
    for rel in ("status", "boot", "stack", "ai"):
        proc = Path(f"/proc/kilroy_field/{rel}")
        if proc.is_file():
            try:
                snippet = proc.read_text(encoding="utf-8", errors="replace").splitlines()[:4]
                lines.append(f"  /proc/kilroy_field/{rel}:")
                lines.extend(f"    {ln}" for ln in snippet)
            except OSError:
                pass
    return "\n".join(lines)


def _queen_themes() -> list[dict[str, Any]]:
    paths = (
        QUEEN / "gui" / "queen-styles-themes.json",
        SG / "Queen" / "gui" / "queen-styles-themes.json",
    )
    for path in paths:
        if path.is_file():
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
                return [
                    {"id": t.get("id"), "label": t.get("label"), "built_in": t.get("built_in", True)}
                    for t in (doc.get("themes") or [])
                    if t.get("id")
                ]
            except (OSError, json.JSONDecodeError):
                break
    return []


def terminal_status() -> dict[str, Any]:
    env = _field_env()
    g16 = GROK16 / "bin" / "g16"
    gpy = GPY / "bin" / "gpy-16"
    kernel = _kernel_slice()
    default = _default_cwd()
    themes = _queen_themes()
    return {
        "ok": True,
        "schema": "queen-gnu-terminal/v1",
        "cwd_default": str(default),
        "sg_root": str(SG),
        "kilroy_root": kernel.get("kilroy_root"),
        "shell": os.environ.get("SHELL", "/bin/bash"),
        "field_kernel": kernel,
        "field_native": {
            "g16": g16.is_file(),
            "gpy16": gpy.is_file(),
            "path": env.get("PATH", "")[:240],
            "kilroy_by_default": True,
        },
        "ansi": {"enabled": True, "palette": "256+truecolor", "parser": "ellie-nav"},
        "themes": themes,
        "theme_default": "black_emerald_rose_2026",
        "theme_mono": "mono_terminal",
        "queen_styles": "/gui/queen-styles-themes.json",
        "minibrowser_proxy": "/browse/view",
        "menus": ["File", "Edit", "View", "Options", "Help"],
        "posture": "Queen GNU Terminal — ANSI palette, Queen Styles, KILROY cwd, proc witness when loaded",
    }


def dispatch_terminal(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "run").strip().lower().replace("-", "_")
    if action in ("status", "json"):
        return terminal_status()
    if action != "run":
        return {"ok": False, "error": f"unknown_action:{action}"}

    cmd = str(body.get("command") or "").strip()
    if not cmd:
        return {"ok": False, "error": "empty_command"}
    cwd = _safe_cwd(str(body.get("cwd") or _default_cwd()))

    if cmd == "clear":
        return {"ok": True, "clear": True, "cwd": str(cwd)}
    if cmd.startswith("cd") and (len(cmd) == 2 or cmd[2:3] in (" ", "\t")):
        new_cwd, err = _resolve_cd(cwd, cmd)
        if err:
            return {"ok": False, "output": err, "cwd": str(cwd)}
        return {"ok": True, "output": "", "cwd": str(new_cwd)}

    low = cmd.lower().split()[0]
    if low in ("kilroy", "kilroy-status", "kernel"):
        return {"ok": True, "output": _format_kernel_status(), "cwd": str(cwd), "field_kernel": _kernel_slice()}
    if low == "discern":
        rest = cmd.split(maxsplit=1)[1] if len(cmd.split()) > 1 else ""
        return _discern_command(rest, cwd)

    ok, reason = _command_allowed(cmd)
    if not ok:
        return {"ok": False, "output": reason, "cwd": str(cwd)}

    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=int(body.get("timeout") or 60),
            env=_field_env(),
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return {
            "ok": proc.returncode == 0,
            "output": out[:16000] or f"(exit {proc.returncode})",
            "ansi": True,
            "returncode": proc.returncode,
            "cwd": str(cwd),
            "field_kernel": _kernel_slice(),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "Command timed out.", "cwd": str(cwd)}
    except Exception as exc:
        return {"ok": False, "output": str(exc), "cwd": str(cwd)}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch_terminal(body), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(terminal_status(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-terminal.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())