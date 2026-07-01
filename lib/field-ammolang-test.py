#!/usr/bin/env pythong
"""AmmoLang test engine — any command · assert · hang guard · stall drop."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent))
GROK16 = Path(os.environ.get("GROK16_ROOT", INSTALL / "Grok16"))
SUITE_ROOT = INSTALL / "tests" / "ammolang"
LEDGER = STATE / "ammolang-test-ledger.json"
PANEL = STATE / "ammolang-test-panel.json"
TIMING_LEDGER = STATE / "ammolang-timing-ledger.json"

_DEFAULT = "300" if os.environ.get("AML_TEST_DIRECT", "0") == "1" else "120"
DEFAULT_TIMEOUT = int(os.environ.get("AML_TEST_TIMEOUT_SEC", _DEFAULT))
DEFAULT_STALL = int(os.environ.get("AML_TEST_STALL_SEC", "45"))
SHELL_TIMEOUT = int(os.environ.get("AML_TEST_SHELL_TIMEOUT_SEC", "30"))
PY_TIMEOUT = int(os.environ.get("AML_TEST_PY_TIMEOUT_SEC", "90"))
ROUTE_TIMEOUT = int(os.environ.get("AML_TEST_ROUTE_TIMEOUT_SEC", "120"))

_GREP_PATH = re.compile(
    r"^(.+?\.(?:py|json|sh|aml|html|js|txt|conf|md|jsonl|c|h)):(.+)$",
    re.IGNORECASE,
)
_MOD_TIMEOUT = re.compile(r"\btimeout:(\d+)", re.I)
_MOD_STALL = re.compile(r"\bstall:(\d+)", re.I)
_MOD_MATCH = re.compile(r"\bmatch:(.+)$", re.I)
_ROOT_RE = re.compile(r"\$\{ROOT\}")
_SG_RE = re.compile(r"\$\{SG_ROOT[^}]*\}")
_NEXUS_TEST_LIBS = (
    "nexus-common.sh",
    "eternal-vigil.sh",
    "entropy-oracle.sh",
    "shadow-reality.sh",
    "self-defense.sh",
    "device-whitelist.sh",
    "ultra-stealth.sh",
    "predictive-guard.sh",
    "network-lockdown.sh",
    "threat-vectors.sh",
    "packet-oracle.sh",
    "threat-panel.sh",
    "firewall-sentinel.sh",
    "firewall-trust.sh",
    "seal-vault.sh",
    "tamper-guard.sh",
    "znetwork-field.sh",
    "nexus-settings.sh",
    "adblock-loader.sh",
    "host-attack.sh",
    "field-attack-kit.sh",
)
_suite_shell_ready = False


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _py() -> str:
    if os.environ.get("AML_TEST_DIRECT", "0") == "1":
        return sys.executable
    py = os.environ.get("NEXUS_PYTHONG", "")
    if py and Path(py).is_file():
        return py
    for cand in (INSTALL / "PythonG" / "bin" / "pythong", "pythong", "python3"):
        if isinstance(cand, Path) and cand.is_file():
            return str(cand)
        if isinstance(cand, str) and subprocess.run(["which", cand], capture_output=True).returncode == 0:
            return cand
    return sys.executable


def _py_argv(mod_path: Path, args: list[str]) -> list[str]:
    """Prefer g16-compiled executable launcher when available."""
    if os.environ.get("G16_SCRIPT_EXEC", "1").strip().lower() in ("0", "false", "no", "off"):
        return [_py(), str(mod_path), *args]
    compile_py = INSTALL / "lib" / "field-g16-script-compile.py"
    if not compile_py.is_file():
        return [_py(), str(mod_path), *args]
    try:
        spec = importlib.util.spec_from_file_location("field_g16_script_compile", compile_py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "resolve_argv"):
                return mod.resolve_argv(mod_path, args)
    except Exception:
        pass
    return [_py(), str(mod_path), *args]


def _resolve(path: str) -> Path:
    p = path.strip().strip('"').strip("'")
    p = _ROOT_RE.sub(str(INSTALL), p)
    p = _SG_RE.sub(str(SG), p)
    if p.startswith("~/"):
        p = str(Path.home() / p[2:])
    candidate = Path(p)
    if candidate.is_file() or candidate.is_dir():
        return candidate
    return INSTALL / p.lstrip("/")


def _test_env() -> dict[str, str]:
    base_path = os.environ.get("PATH", "")
    if os.environ.get("AML_TEST_DIRECT", "0") == "1":
        keep = ["/usr/bin", "/bin", "/usr/local/bin", str(INSTALL / "PythonG" / "bin")]
        base_path = ":".join(p for p in keep if Path(p).exists() or p.startswith("/"))
    return {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "SG_ROOT": str(SG),
        "GROK16_ROOT": str(GROK16),
        "ROOT": str(INSTALL),
        "AML_INLINE": "1",
        "AML_TEST_DIRECT": os.environ.get("AML_TEST_DIRECT", "0"),
        "PYTHONUNBUFFERED": "1",
        "PATH": f"{INSTALL / 'PythonG' / 'bin'}:{base_path}",
    }


def _reset_suite_shell() -> None:
    global _suite_shell_ready
    _suite_shell_ready = False


def _bash_wrap(command: str) -> str:
    """Inject stack env + nexus libs so migrated shell one-liners work."""
    global _suite_shell_ready
    parts = [
        f'export ROOT="{INSTALL}" NEXUS_INSTALL_ROOT="{INSTALL}"',
        f'NEXUS_STATE_DIR="{STATE}" SG_ROOT="{SG}" GROK16_ROOT="{GROK16}"',
        "export NEXUS_INSTALL_ROOT NEXUS_STATE_DIR SG_ROOT GROK16_ROOT ROOT",
        f'panel="{INSTALL / "panel" / "threat-panel.html"}"',
        f'mkdir -p "{STATE}"',
    ]
    for lib in _NEXUS_TEST_LIBS:
        parts.append(f'source "{INSTALL / "lib" / lib}" 2>/dev/null || true')
    parts.append("nexus_ensure_dirs 2>/dev/null || true")
    _suite_shell_ready = True
    cmd = command.strip()
    if cmd.startswith("return 0"):
        cmd = cmd.replace("return 0", "exit 0", 1)
    return "; ".join(parts) + "; " + cmd


def _parse_modifiers(spec: str) -> tuple[str, int | None, int | None, str | None]:
    """Strip timeout:/stall:/match: modifiers; return clean spec."""
    match_m = _MOD_MATCH.search(spec)
    match = match_m.group(1).strip().strip("'\"") if match_m else None
    body = spec[: match_m.start()].strip() if match_m else spec
    timeout_m = _MOD_TIMEOUT.search(body)
    stall_m = _MOD_STALL.search(body)
    timeout = int(timeout_m.group(1)) if timeout_m else None
    stall = int(stall_m.group(1)) if stall_m else None
    body = _MOD_TIMEOUT.sub("", body)
    body = _MOD_STALL.sub("", body).strip()
    return body, timeout, stall, match


def _stall_for(timeout: int, stall: int | None = None) -> int:
    if stall is not None:
        return max(10, stall)
    return min(DEFAULT_STALL, max(15, timeout // 3))


def _adaptive_timeout(key: str, default: int) -> int:
    try:
        doc = json.loads(TIMING_LEDGER.read_text(encoding="utf-8"))
        row = (doc.get("steps") or {}).get(key) or {}
        last_ms = int(row.get("last_ms") or 0)
        if last_ms > 0:
            return min(max(default, (last_ms // 1000) + 5), 3600)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return default


def _record_hang(label: str, kind: str, *, timeout: bool = False, stall: bool = False) -> None:
    try:
        with (STATE / "ammolang-test-hangs.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": _now(),
                "label": label,
                "kind": kind,
                "timeout": timeout,
                "stall": stall,
            }, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _import_g16_monitor() -> Any | None:
    py = GROK16 / "lib" / "g16_self_monitor.py"
    if not py.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("g16_self_monitor", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("g16_self_monitor", mod)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _import_monster() -> Any | None:
    try:
        import importlib.util

        py = INSTALL / "lib" / "field-monster-shell.py"
        spec = importlib.util.spec_from_file_location("monster_shell", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _import_h7_guard() -> Any | None:
    py = INSTALL / "lib" / "hostess7-hang-guard.py"
    if not py.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("hostess7_hang_guard", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _run_cmd(
    cmd: list[str],
    *,
    timeout: int,
    stall: int,
    label: str,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Run any command through Monster → g16 monitor → h7 guarded subprocess → timeout subprocess."""
    env = _test_env()
    t0 = time.perf_counter()

    if os.environ.get("AML_TEST_DIRECT", "0") == "1":
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(cwd or INSTALL),
                env=env,
            )
            out = proc.stdout or ""
            err = proc.stderr or ""
            rc = proc.returncode
            ok = rc == 0 or (rc == 141 and "script:" in label)
            return {
                "ok": ok,
                "rc": rc,
                "timeout": False,
                "stall": False,
                "wall_ms": int((time.perf_counter() - t0) * 1000),
                "stdout": out,
                "stderr": err,
                "tail": (out + err)[-800:],
                "direct": True,
            }
        except subprocess.TimeoutExpired:
            _record_hang(label, "timeout", timeout=True)
            return {
                "ok": False,
                "rc": 124,
                "timeout": True,
                "stall": False,
                "wall_ms": timeout * 1000,
                "detail": f"TIMEOUT {timeout}s",
                "direct": True,
            }

    monster = _import_monster()
    if monster and hasattr(monster, "run_guarded") and os.environ.get("MONSTER_SHELL", "1") != "0":
        res = monster.run_guarded(
            cmd,
            label=label[:80],
            timeout=float(timeout),
            stall_sec=float(stall),
            cwd=cwd or INSTALL,
            env=env,
        )
        out = res.get("stdout") or ""
        err = res.get("stderr") or ""
        hung = bool(res.get("hung") or res.get("quit"))
        row = {
            "ok": bool(res.get("ok")),
            "rc": res.get("rc"),
            "timeout": hung and res.get("detail") == "hang_or_quit",
            "stall": hung and not res.get("quit"),
            "dropped": hung,
            "drop_reason": "monster_quit" if res.get("quit") else "monster_stall",
            "wall_ms": int(res.get("wall_ms") or (time.perf_counter() - t0) * 1000),
            "stdout": out,
            "stderr": err,
            "tail": (out + err)[-800:],
            "monster": True,
        }
        if hung:
            _record_hang(label, str(row.get("drop_reason") or "hang"), timeout=row["timeout"], stall=row["stall"])
            row["detail"] = str(row.get("drop_reason") or "hang")
        return row

    monitor = _import_g16_monitor()

    if monitor and hasattr(monitor, "run_monitored"):
        res = monitor.run_monitored(
            cmd,
            label=label[:80],
            timeout_sec=timeout,
            stall_sec=stall,
            cwd=cwd or INSTALL,
            env=env,
            log_heartbeats=False,
        )
        out = res.stdout or ""
        err = res.stderr or ""
        row = {
            "ok": res.ok(),
            "rc": res.rc,
            "timeout": bool(res.timeout_hit),
            "stall": bool(res.dropped and res.drop_reason == "stall"),
            "dropped": bool(res.dropped),
            "drop_reason": res.drop_reason,
            "wall_ms": int(res.wall_ms or (time.perf_counter() - t0) * 1000),
            "stdout": out,
            "stderr": err,
            "tail": (out + err)[-800:],
        }
        if row["timeout"]:
            _record_hang(label, "timeout", timeout=True)
            row["ok"] = False
            row["detail"] = f"TIMEOUT {timeout}s"
        elif row["stall"]:
            _record_hang(label, "stall", stall=True)
            row["ok"] = False
            row["detail"] = f"STALL {stall}s"
        return row

    guard = _import_h7_guard()
    if guard and hasattr(guard, "run_subprocess_guarded"):
        res = guard.run_subprocess_guarded(
            cmd,
            timeout=float(timeout),
            stall_sec=float(stall),
            label=label[:80],
            env=env,
            cwd=cwd or INSTALL,
            kill_on_stall=True,
        )
        out = res.get("stdout") or ""
        err = res.get("stderr") or ""
        hung = bool(res.get("hung") or res.get("stall"))
        row = {
            "ok": (res.get("exit_code") == 0) and not hung,
            "rc": res.get("exit_code"),
            "timeout": hung and res.get("reason") == "timeout",
            "stall": hung and res.get("reason") != "timeout",
            "dropped": hung,
            "drop_reason": res.get("reason"),
            "wall_ms": int((time.perf_counter() - t0) * 1000),
            "stdout": out,
            "stderr": err,
            "tail": (out + err)[-800:],
        }
        if hung:
            _record_hang(label, str(res.get("reason") or "hang"), timeout=row["timeout"], stall=row["stall"])
            row["detail"] = str(res.get("reason") or "hang")
        return row

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd or INSTALL),
            env=env,
        )
        out = proc.stdout or ""
        err = proc.stderr or ""
        return {
            "ok": proc.returncode == 0,
            "rc": proc.returncode,
            "timeout": False,
            "stall": False,
            "wall_ms": int((time.perf_counter() - t0) * 1000),
            "stdout": out,
            "stderr": err,
            "tail": (out + err)[-800:],
        }
    except subprocess.TimeoutExpired:
        _record_hang(label, "timeout", timeout=True)
        return {
            "ok": False,
            "rc": 124,
            "timeout": True,
            "stall": False,
            "wall_ms": timeout * 1000,
            "detail": f"TIMEOUT {timeout}s",
        }


def _resolve_script(name: str) -> Path | None:
    candidates = [
        INSTALL / "scripts" / f"{name}.sh",
        INSTALL / "scripts" / name,
        INSTALL / "tests" / "ammolang" / "snippets" / f"{name}.sh",
        INSTALL / "tests" / "ammolang" / "snippets" / name,
        GROK16 / "scripts" / f"{name}.sh",
        GROK16 / "scripts" / name,
        INSTALL / "tests" / f"{name}.sh",
        INSTALL / "tests" / name,
    ]
    if "/" in name:
        candidates.insert(0, INSTALL / "tests" / "ammolang" / "snippets" / f"{name}.sh")
        candidates.insert(1, INSTALL / name)
    return next((p for p in candidates if p.is_file()), None)


def _resolve_py_module(name: str) -> Path | None:
    raw = name if "/" in name else (name if name.endswith(".py") else f"{name}.py")
    variants = [raw]
    if "-" in raw and "/" not in name:
        variants.append(raw.replace("-", "_"))
    for base in (INSTALL / "lib", GROK16 / "lib", INSTALL / "Queen" / "lib"):
        for stem in variants:
            p = base / stem
            if p.is_file():
                return p
    resolved = _resolve(name)
    return resolved if resolved.is_file() else None


def run_command(
    spec: str,
    *,
    timeout: int | None = None,
    stall: int | None = None,
    label: str = "",
    match: str | None = None,
) -> dict[str, Any]:
    """Run any command spec — script:/py:/route:/bash — with hang guard."""
    spec = spec.strip()
    lbl = label or spec[:72]

    if spec.startswith("script:"):
        name = spec.split(":", 1)[1].split()[0]
        script = _resolve_script(name)
        if not script:
            return {"ok": False, "detail": "script missing", "script": name}
        args = shlex.split(spec.split(":", 1)[1])[1:] if len(spec.split(":", 1)[1].split()) > 1 else []
        script_default = 900 if os.environ.get("AML_TEST_DIRECT", "0") == "1" else 180
        to = timeout or _adaptive_timeout(f"script:{name}", script_default)
        st = stall if stall is not None else max(60, _stall_for(to, stall))
        return _run_cmd(["bash", str(script), *args], timeout=to, stall=st, label=lbl, cwd=script.parent)

    if spec.startswith("py:"):
        rest = spec.split(":", 1)[1].strip()
        parts = rest.split(None, 1)
        mod_name = parts[0]
        action = parts[1].split()[0] if len(parts) > 1 else ""
        extra = shlex.split(parts[1])[1:] if len(parts) > 1 and len(shlex.split(parts[1])) > 1 else []
        path = _resolve_py_module(mod_name)
        if not path:
            return {"ok": False, "detail": "py module missing", "module": mod_name}
        to = timeout or _adaptive_timeout(f"py:{mod_name}", PY_TIMEOUT)
        py_args = ([action] if action else []) + extra
        cmd = _py_argv(path, py_args)
        res = _run_cmd(cmd, timeout=to, stall=_stall_for(to, stall), label=lbl)
        if match:
            blob = (res.get("stdout") or "") + (res.get("stderr") or "")
            res["ok"] = match in blob and res.get("ok", False)
            res["detail"] = "match" if res["ok"] else "output mismatch"
        return res

    if spec.startswith("route:"):
        route = spec.split(":", 1)[1].split()[0]
        live = "live" in spec.lower()
        cmd = [_py(), str(INSTALL / "lib" / "field-ammolang-build.py"), "route", route]
        if not live:
            cmd.append("--dry")
        to = timeout or _adaptive_timeout(f"route:{route}", ROUTE_TIMEOUT)
        res = _run_cmd(cmd, timeout=to, stall=_stall_for(to, stall), label=lbl)
        if match:
            blob = (res.get("stdout") or "") + (res.get("stderr") or "")
            res["ok"] = match in blob and res.get("ok", False)
            res["detail"] = "route+match" if res["ok"] else "route mismatch"
        return res

    to = timeout or SHELL_TIMEOUT
    wrap = _bash_wrap(spec)
    if os.environ.get("AML_TEST_DIRECT", "0") == "1":
        cmd = spec.strip()
        if cmd.startswith(("grep ", "test ", "tmp_state=", "true", "false", "exit ")):
            wrap = (
                f'export ROOT="{INSTALL}" NEXUS_INSTALL_ROOT="{INSTALL}" '
                f'NEXUS_STATE_DIR="{STATE}" SG_ROOT="{SG}" GROK16_ROOT="{GROK16}"; {cmd}'
            )
    return _run_cmd(["bash", "-c", wrap], timeout=to, stall=_stall_for(to, stall), label=lbl)


def _parse_assert(spec: str) -> dict[str, Any]:
    body, timeout, stall, match = _parse_modifiers(spec)
    if ":" in body and not body.lower().startswith(("assert ", "match:")):
        kind, rest = body.split(":", 1)
        kind = kind.strip().lower()
    else:
        parts = body.split(None, 1)
        kind = (parts[0] if parts else "").lower().rstrip(":")
        rest = parts[1] if len(parts) > 1 else ""
    out: dict[str, Any] = {"kind": kind, "raw": spec, "timeout": timeout, "stall": stall, "match": match}

    if kind in ("file", "dir", "exec"):
        out["path"] = rest.split()[0] if rest else ""
        return out

    if kind == "grep":
        gm = _GREP_PATH.match(rest.strip())
        if gm:
            out["path"] = gm.group(1).strip()
            out["pattern"] = gm.group(2).strip().strip("'\"")
        else:
            toks = rest.split(None, 1)
            out["path"] = toks[0] if toks else ""
            out["pattern"] = toks[1] if len(toks) > 1 else ""
        return out

    if kind in ("py", "python", "pythong"):
        toks = shlex.split(rest)
        out["module"] = toks[0] if toks else ""
        out["args"] = toks[1:] if len(toks) > 1 else []
        return out

    if kind == "compile":
        out["aml"] = rest.split()[0] if rest else ""
        return out

    if kind == "route":
        out["route"] = rest.split()[0] if rest else ""
        return out

    if kind in ("run", "shell", "cmd", "bash"):
        out["command"] = rest
        return out

    if kind in ("script", "task"):
        out["command"] = body
        return out

    out["kind"] = "shell"
    out["command"] = body
    return out


def run_assert(spec: str, *, timeout: int | None = None, stall: int | None = None, name: str = "") -> dict[str, Any]:
    """Execute one assert — instant checks or guarded command."""
    body, mod_to, mod_stall, mod_match = _parse_modifiers(spec)
    timeout = mod_to or timeout or DEFAULT_TIMEOUT
    stall = mod_stall or stall
    parsed = _parse_assert(spec)
    kind = parsed.get("kind")
    label = name or body[:60]
    match = parsed.get("match") or mod_match

    if kind == "file":
        raw = str(parsed.get("path") or "")
        path = _resolve(raw)
        if not path.is_file() and raw.startswith(".nexus-state/"):
            path = STATE / raw.split("/", 1)[1]
        ok = path.is_file()
        return {"ok": ok, "kind": kind, "path": str(path), "detail": "missing" if not ok else "ok"}

    if kind == "dir":
        path = _resolve(str(parsed.get("path") or ""))
        ok = path.is_dir()
        return {"ok": ok, "kind": kind, "path": str(path), "detail": "missing" if not ok else "ok"}

    if kind == "exec":
        path = _resolve(str(parsed.get("path") or ""))
        ok = path.is_file() and os.access(path, os.X_OK)
        return {"ok": ok, "kind": kind, "path": str(path), "detail": "not executable" if not ok else "ok"}

    if kind == "grep":
        raw = str(parsed.get("path") or "")
        path = _resolve(raw)
        if not path.is_file() and raw.startswith(".nexus-state/"):
            path = STATE / raw.split("/", 1)[1]
        pat = str(parsed.get("pattern") or "")
        if not path.is_file():
            return {"ok": False, "kind": kind, "detail": "file missing", "path": str(path)}
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return {"ok": False, "kind": kind, "detail": str(exc)}
        ok = pat in text
        return {"ok": ok, "kind": kind, "path": str(path), "pattern": pat, "detail": "match" if ok else "no match"}

    if kind in ("py", "python", "pythong"):
        mod_path = _resolve(str(parsed.get("module") or ""))
        if not mod_path.is_file():
            mod_path = INSTALL / "lib" / str(parsed.get("module") or "").lstrip("lib/")
        if not mod_path.is_file():
            mod_path = _resolve_py_module(str(parsed.get("module") or "")) or mod_path
        if not mod_path or not mod_path.is_file():
            return {"ok": False, "kind": kind, "detail": "module missing"}
        to = parsed.get("timeout") or PY_TIMEOUT
        cmd = _py_argv(mod_path, list(parsed.get("args") or []))
        res = _run_cmd(cmd, timeout=to, stall=_stall_for(to, stall), label=label)
        if res.get("timeout") or res.get("stall"):
            return {**res, "kind": kind, "detail": res.get("detail") or "hang"}
        if match:
            blob = (res.get("stdout") or "") + (res.get("stderr") or "")
            ok = match in blob
            return {"ok": ok, "kind": kind, "detail": "match" if ok else "output mismatch"}
        return {**res, "kind": kind, "detail": "ok" if res.get("ok") else f"rc={res.get('rc')}"}

    if kind == "compile":
        aml = _resolve(str(parsed.get("aml") or ""))
        if not aml.is_file():
            return {"ok": False, "kind": kind, "detail": "aml missing"}
        to = parsed.get("timeout") or 60
        res = _run_cmd(
            [_py(), str(INSTALL / "lib" / "field-ammolang.py"), "compile", str(aml)],
            timeout=to,
            stall=_stall_for(to, stall),
            label=label,
        )
        if match:
            blob = (res.get("stdout") or "") + (res.get("stderr") or "")
            res["ok"] = match in blob and res.get("ok", False)
            res["detail"] = "compile+match" if res["ok"] else "compile mismatch"
        return {**res, "kind": kind}

    if kind == "route":
        live = "live" in spec.lower()
        cmd = [_py(), str(INSTALL / "lib" / "field-ammolang-build.py"), "route", str(parsed.get("route") or "")]
        if not live:
            cmd.append("--dry")
        to = parsed.get("timeout") or ROUTE_TIMEOUT
        res = _run_cmd(cmd, timeout=to, stall=_stall_for(to, stall), label=label)
        if match:
            blob = (res.get("stdout") or "") + (res.get("stderr") or "")
            res["ok"] = match in blob and res.get("ok", False)
            res["detail"] = "route+match" if res["ok"] else "route mismatch"
        return {**res, "kind": kind}

    command = str(parsed.get("command") or body or "")

    if kind == "run" or command.startswith(("script:", "py:", "route:", "task:")):
        run_spec = command if kind == "run" else command
        if run_spec.startswith("task:"):
            run_spec = f"route:{run_spec.split(':', 1)[1]}"
        res = run_command(
            run_spec,
            timeout=parsed.get("timeout") or timeout,
            stall=stall,
            label=label,
            match=match,
        )
        return {**res, "kind": "run"}

    res = run_command(
        command,
        timeout=parsed.get("timeout") or SHELL_TIMEOUT,
        stall=stall,
        label=label,
        match=match,
    )
    if match and not res.get("timeout") and not res.get("stall"):
        blob = (res.get("stdout") or "") + (res.get("stderr") or "")
        if match not in blob:
            res["ok"] = False
            res["detail"] = "shell mismatch"
    if res.get("ok") and kind in ("shell", "cmd", "bash"):
        res["detail"] = "shell"
    return {**res, "kind": kind}


def _load_suite_steps(path: Path) -> list[dict[str, Any]]:
    aml = INSTALL / "lib" / "field-ammolang.py"
    if not aml.is_file():
        return []
    spec = importlib.util.spec_from_file_location("field_ammolang_parse", aml)
    if not spec or not spec.loader:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    doc = mod.parse_ammolang(path.read_text(encoding="utf-8"))
    return _flatten_test_steps(doc.get("steps") or [])


def _flatten_test_steps(steps: list[dict[str, Any]], *, group: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for step in steps:
        op = step.get("op")
        if op == "GROUP":
            out.extend(_flatten_test_steps(step.get("children") or [], group=str(step.get("name") or "")))
            continue
        if op in ("SEQ", "PAR", "SUITE"):
            out.extend(_flatten_test_steps(step.get("children") or [], group=group or str(step.get("name") or "")))
            continue
        if op == "ASSERT":
            out.append({"op": "ASSERT", "spec": step.get("spec"), "name": step.get("name"), "group": group})
        if op == "RUN":
            out.append({"op": "RUN_ASSERT", "spec": step.get("spec"), "group": group})
    return out


def run_suite_file(path: Path, *, halt: bool = True) -> dict[str, Any]:
    _reset_suite_shell()
    steps = _load_suite_steps(path)
    if not steps:
        return {"ok": False, "error": "empty_or_unparsed_suite", "path": str(path)}

    passed = failed = stalled = 0
    results: list[dict[str, Any]] = []
    t0 = time.perf_counter()

    for i, step in enumerate(steps):
        if step.get("op") == "RUN_ASSERT":
            spec = str(step.get("spec") or "")
            if not spec.startswith(("script:", "py:", "route:", "bash", "cmd:")):
                spec = f"run {spec}" if not spec.startswith("run ") else spec
        else:
            spec = str(step.get("spec") or "")
        name = str(step.get("name") or spec[:48])
        row = run_assert(spec, name=name)
        row["name"] = name
        row["group"] = step.get("group") or ""
        row["index"] = i
        results.append(row)
        if row.get("ok"):
            passed += 1
        else:
            failed += 1
            if row.get("timeout") or row.get("stall"):
                stalled += 1
            if halt and not (row.get("timeout") or row.get("stall")):
                break

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    doc = {
        "schema": "ammolang-test-run/v1",
        "updated": _now(),
        "suite": path.name,
        "path": str(path),
        "ok": failed == 0,
        "passed": passed,
        "failed": failed,
        "stalled": stalled,
        "total": len(steps),
        "ran": len(results),
        "elapsed_ms": elapsed_ms,
        "hang_guard": True,
        "results": results[-60:],
    }
    _save_panel(doc)
    return doc


def run_suite_name(name: str, *, halt: bool = True) -> dict[str, Any]:
    key = name.strip().lower().replace("-", "_")
    if key in ("stack", "all", "full"):
        return run_all_suites(halt=halt)
    candidates = [
        SUITE_ROOT / f"{key}.aml",
        INSTALL / "library" / "dewey" / "000-computer-science" / "ammolang" / f"{key}.aml",
        INSTALL / "tests" / "ammolang" / f"{key}_tests.aml",
    ]
    path = next((p for p in candidates if p.is_file()), None)
    if not path:
        return {"ok": False, "error": "suite_not_found", "name": name}
    return run_suite_file(path, halt=halt)


def run_all_suites(*, halt: bool = False) -> dict[str, Any]:
    """Run every category — never stall the batch (halt=False per suite)."""
    master = SUITE_ROOT / "stack_tests.aml"
    if master.is_file():
        steps = _load_suite_steps(master)
        if any(s.get("op") == "RUN_ASSERT" or "test suite:" in str(s.get("spec", "")) for s in steps):
            pass
        elif any("test " in str(x) for x in []):
            pass

    suites = sorted(p for p in SUITE_ROOT.glob("*.aml") if p.name != "stack_tests.aml")
    passed = failed = stalled = 0
    suite_docs: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    for path in suites:
        doc = run_suite_file(path, halt=False)
        suite_docs.append({
            "suite": path.name,
            "ok": doc.get("ok"),
            "passed": doc.get("passed"),
            "failed": doc.get("failed"),
            "stalled": doc.get("stalled"),
            "elapsed_ms": doc.get("elapsed_ms"),
        })
        passed += int(doc.get("passed") or 0)
        failed += int(doc.get("failed") or 0)
        stalled += int(doc.get("stalled") or 0)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "schema": "ammolang-test-batch/v1",
        "updated": _now(),
        "ok": failed == 0,
        "passed": passed,
        "failed": failed,
        "stalled": stalled,
        "suites": suite_docs,
        "elapsed_ms": elapsed_ms,
        "hang_guard": True,
    }


def _save_panel(doc: dict[str, Any]) -> None:
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        PANEL.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        prev = {}
        if LEDGER.is_file():
            try:
                prev = json.loads(LEDGER.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                prev = {}
        LEDGER.write_text(json.dumps({
            "schema": "ammolang-test-ledger/v1",
            "updated": doc.get("updated"),
            "last": doc,
            "history": (prev.get("history") or [])[-19:] + [doc],
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "stack").strip().lower()
    halt = "--no-halt" not in sys.argv
    if cmd in ("stack", "all", "full"):
        doc = run_all_suites(halt=halt)
    elif cmd == "suite" and len(sys.argv) > 2:
        doc = run_suite_name(sys.argv[2], halt=halt)
    elif cmd == "assert" and len(sys.argv) > 2:
        doc = run_assert(" ".join(sys.argv[2:]))
        print(json.dumps(doc, ensure_ascii=False))
        return 0 if doc.get("ok") else 1
    elif cmd in ("run", "cmd", "command") and len(sys.argv) > 2:
        doc = run_command(" ".join(sys.argv[2:]))
        print(json.dumps(doc, ensure_ascii=False))
        return 0 if doc.get("ok") else 1
    elif cmd == "file" and len(sys.argv) > 2:
        doc = run_suite_file(Path(sys.argv[2]), halt=halt)
    else:
        doc = run_suite_name(cmd, halt=halt)
    print(json.dumps(doc, ensure_ascii=False))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())