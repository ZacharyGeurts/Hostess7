#!/usr/bin/env pythong
"""AmmoLang universal boundary — protective execution for any script, compiler, Python, or Hostess 7 task."""
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
DOCTRINE = INSTALL / "data" / "field-ammolang-boundary-doctrine.json"
REGISTRY = INSTALL / "data" / "field-ammolang-boundary-registry.json"
BUILD_DOCTRINE = INSTALL / "data" / "field-ammolang-build-doctrine.json"
SPEC = STATE / "ammolang-boundary-spec.json"
PANEL = STATE / "ammolang-boundary-panel.json"
LEDGER = STATE / "ammolang-boundary.jsonl"
AML_MARKER = "# AmmoLang boundary route"
WIRE_PREFIXES = (
    "scripts",
    "Hostess7",
    "Queen/scripts",
    "KILROY/scripts",
    "GrokLab/scripts",
    "Grok16/scripts",
    "AmmoCode/scripts",
    "Final_Mouth",
    "lib",
    "hostess7-training-viewer",
)
WIRE_ROOT_FILES = ("nexus.sh", "stealth_install.sh", "install-all.sh", "genius_shield.sh")
WIRE_EXCLUDE = frozenset({
    "lib/ammolang-run.sh",
    "lib/ammolang-route.sh",
    "lib/ammolang-kit-env.sh",
    "lib/field-monster-launch.sh",
    "scripts/aml.sh",
})
WIRE_EXCLUDE_PREFIXES = (
    "tests/ammolang/snippets/",
    ".pages-hub-",
    "node_modules/",
)
AML_SHIM = """{marker} — AML_BUILD=1 universal boundary
_aml_find_root() {{
  local d="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}}
if [[ "${{AML_BUILD:-1}}" != "0" ]] && [[ -z "${{AML_BOUNDARY_ACTIVE:-}}" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    export AML_BOUNDARY_ACTIVE=1
    exec bash "${{_AML_ROOT}}/lib/ammolang-run.sh" exec "script:{script_rel}" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true
"""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": row.get("ts") or _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _mod(rel: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    name = re.sub(r"[^\w]", "_", rel)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _boundary_args() -> list[str]:
    raw = os.environ.get("AML_BOUNDARY_ARGS_JSON", "[]")
    try:
        val = json.loads(raw)
        return [str(x) for x in val] if isinstance(val, list) else []
    except json.JSONDecodeError:
        return []


def _normalize_target(name: str) -> str:
    return (name or "").strip().replace("-", "_")


def _script_candidates(name: str) -> list[Path]:
    base = name.replace("_", "-")
    cands = [
        INSTALL / "scripts" / f"{name}.sh",
        INSTALL / "scripts" / f"{base}.sh",
        INSTALL / name,
        INSTALL / name if name.endswith(".sh") else INSTALL / f"{name}.sh",
    ]
    if name.startswith("scripts/"):
        cands.insert(0, INSTALL / name)
    out: list[Path] = []
    for p in cands:
        if p.is_file() and p not in out:
            out.append(p)
    return out


def _py_candidates(name: str) -> list[Path]:
    mod = name.replace("py:", "").strip()
    queen = INSTALL / "Queen"
    cands = [
        INSTALL / "lib" / f"{mod}.py",
        INSTALL / "Hostess7" / "scripts" / f"{mod}.py",
        GROK16 / "lib" / f"{mod}.py",
    ]
    if queen.is_dir():
        cands.append(queen / "lib" / f"{mod}.py")
    return [p for p in cands if p.is_file()]


def resolve_target(target: str, extra: list[str] | None = None) -> dict[str, Any]:
    """Resolve any target to an executable spec — script, py, route, hostess7, bash."""
    extra = list(extra or [])
    doctrine = _load(DOCTRINE, {})
    registry = _load(REGISTRY, {})
    build = _load(BUILD_DOCTRINE, {})
    routes = build.get("script_routes") or {}
    task_reg = build.get("task_registry") or {}
    compilers = doctrine.get("compiler_aliases") or {}
    reg_entries = {e.get("id"): e for e in registry.get("entries") or [] if e.get("id")}

    target = (target or os.environ.get("AML_BOUNDARY_TARGET") or "").strip()
    if not target and extra:
        target = extra[0]
        extra = extra[1:]

    spec: dict[str, Any] = {
        "schema": "ammolang-boundary-spec/v1",
        "target": target,
        "args": extra,
        "resolved": _now(),
        "kind": "unknown",
    }

    if not target:
        spec["error"] = "target_required"
        return spec

    # Explicit prefixes
    if target.startswith("script:"):
        rel = target.split(":", 1)[1]
        path = INSTALL / rel if not Path(rel).is_absolute() else Path(rel)
        if path.is_file():
            spec.update({"kind": "script", "path": str(path.relative_to(INSTALL)), "argv": ["bash", str(path), *extra]})
            return spec

    if target.startswith("py:"):
        mod = target[3:].strip()
        py_args = extra or ["status"]
        for path in _py_candidates(mod):
            spec.update({
                "kind": "py",
                "module": mod,
                "path": str(path.relative_to(INSTALL)),
                "argv": [os.environ.get("NEXUS_PYTHONG", "python3"), str(path), *py_args],
            })
            return spec

    if target.startswith("hostess7:"):
        cmd = target.split(":", 1)[1]
        h7 = INSTALL / "Hostess7" / "Hostess7.sh"
        if h7.is_file():
            spec.update({"kind": "hostess7", "path": "Hostess7/Hostess7.sh", "argv": ["bash", str(h7), cmd, *extra]})
            return spec

    if target.startswith("route:"):
        route = target.split(":", 1)[1]
        aml = routes.get(route) or routes.get(route.replace("-", "_"))
        if aml:
            spec.update({"kind": "route", "route": route, "aml": aml, "delegate": "field-ammolang-build.py"})
            return spec

    if target.startswith("bash:"):
        cmd = target.split(":", 1)[1]
        spec.update({"kind": "bash", "argv": ["bash", "-lc", cmd, *extra]})
        return spec

    # Registry
    key = _normalize_target(target)
    if key in reg_entries:
        entry = reg_entries[key]
        kind = entry.get("kind", "script")
        if kind == "route":
            aml = routes.get(entry.get("route", ""))
            spec.update({"kind": "route", "route": entry.get("route"), "aml": aml, "via": "registry"})
            return spec
        if kind == "script" and entry.get("path"):
            path = INSTALL / str(entry["path"])
            if path.is_file():
                spec.update({"kind": "script", "path": entry["path"], "argv": ["bash", str(path), *extra], "via": "registry"})
                return spec

    # Named AML routes / task registry (skip meta boundary routes)
    meta_routes = {"exec", "boundary", "any", "run", "universal_boundary"}
    if key not in meta_routes and target not in meta_routes:
        route_key = task_reg.get(key) or task_reg.get(target) or key
        if route_key in routes or target in routes:
            route_name = routes.get(target) or routes.get(key) or route_key
            spec.update({"kind": "route", "route": target, "aml": route_name, "via": "script_routes"})
            return spec

    # Compiler aliases
    if key in compilers or target in compilers:
        alias = compilers.get(target) or compilers.get(key)
        if str(alias).startswith("route:"):
            return resolve_target(alias, extra)
        path = INSTALL / str(alias)
        if path.is_file():
            spec.update({"kind": "script", "path": str(path.relative_to(INSTALL)), "argv": ["bash", str(path), *extra], "via": "compiler_alias"})
            return spec

    # Scripts directory
    for path in _script_candidates(target):
        spec.update({
            "kind": "script",
            "path": str(path.relative_to(INSTALL)),
            "argv": ["bash", str(path), *extra],
            "via": "discover_script",
        })
        return spec

    # Python module
    for path in _py_candidates(target):
        spec.update({
            "kind": "py",
            "module": target,
            "path": str(path.relative_to(INSTALL)),
            "argv": [os.environ.get("NEXUS_PYTHONG", "python3"), str(path), *(extra or ["status"])],
            "via": "discover_py",
        })
        return spec

    # Hostess7 bare command
    h7 = INSTALL / "Hostess7" / "Hostess7.sh"
    if h7.is_file() and not target.startswith("/"):
        spec.update({"kind": "hostess7", "path": "Hostess7/Hostess7.sh", "argv": ["bash", str(h7), target, *extra], "via": "hostess7_guess"})
        return spec

    # Last resort — bounded bash
    spec.update({
        "kind": "bash",
        "argv": ["bash", "-lc", f"cd {shlex.quote(str(INSTALL))} && {shlex.quote(target)} {' '.join(shlex.quote(a) for a in extra)}".strip()],
        "via": "bash_fallback",
        "warning": "unresolved_target_bounded_bash",
    })
    return spec


def run_spec(spec: dict[str, Any], *, live: bool = True) -> dict[str, Any]:
    """Execute resolved spec under subprocess with witness."""
    if spec.get("error"):
        return {"ok": False, "error": spec["error"], "spec": spec}

    kind = spec.get("kind")
    if kind == "route":
        build_py = INSTALL / "lib" / "field-ammolang-build.py"
        route = spec.get("route") or spec.get("target")
        py = os.environ.get("NEXUS_PYTHONG", "python3")
        argv = [py, str(build_py), "route", str(route)]
        if not live:
            argv.append("--dry")
    else:
        argv = list(spec.get("argv") or [])
        if not argv:
            return {"ok": False, "error": "empty_argv", "spec": spec}

    env = os.environ.copy()
    env["AML_BOUNDARY_ACTIVE"] = "1"
    env["AML_BUILD"] = env.get("AML_BUILD", "1")
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
    env["NEXUS_STATE_DIR"] = str(STATE)
    path_prefix = ":".join(
        p for p in (
            "/usr/bin",
            "/bin",
            str(INSTALL / "PythonG" / "bin"),
            str(INSTALL / "Grok16" / "bin"),
            env.get("PATH", ""),
        ) if p
    )
    env["PATH"] = path_prefix
    env.setdefault("SG_ROOT", str(SG))
    env.setdefault("HOSTESS7_ROOT", str(INSTALL / "Hostess7"))
    if kind == "hostess7":
        env["PYTHONPATH"] = str(INSTALL / "Hostess7" / "scripts")
    t0 = time.perf_counter()
    rep: dict[str, Any] = {"ok": False, "kind": kind, "argv": argv, "live": live}
    try:
        if live:
            proc = subprocess.run(
                argv,
                cwd=str(INSTALL),
                env=env,
                capture_output=True,
                text=True,
                timeout=int(os.environ.get("AML_BOUNDARY_TIMEOUT_SEC", "7200")),
            )
            rep.update({"ok": proc.returncode == 0, "rc": proc.returncode, "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-4000:]})
        else:
            rep.update({"ok": True, "dry": True})
    except subprocess.TimeoutExpired as exc:
        rep.update({"ok": False, "error": "timeout", "partial": (exc.stdout or b"")[:2000] if exc.stdout else ""})
    except Exception as exc:
        rep.update({"ok": False, "error": str(exc)[:200]})

    rep["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    rep["target"] = spec.get("target")
    rep["via"] = spec.get("via")
    _append({"event": "run", **{k: rep[k] for k in ("ok", "target", "kind", "via", "rc", "elapsed_ms") if k in rep}})
    return rep


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(INSTALL))
    except ValueError:
        return str(path)


def _wire_excluded(rel: str) -> bool:
    if rel in WIRE_EXCLUDE:
        return True
    return any(rel.startswith(p) for p in WIRE_EXCLUDE_PREFIXES)


def _already_wired(text: str) -> bool:
    if AML_MARKER in text:
        return True
    head = "\n".join(text.splitlines()[:18])
    return "ammolang-run.sh" in head and ("AML_BOUNDARY" in head or "AmmoLang subfolder route" in head)


def discover_shell_scripts() -> list[Path]:
    """All .sh entry points under NewLatest worth protecting."""
    seen: set[str] = set()
    out: list[Path] = []
    for prefix in WIRE_PREFIXES:
        base = INSTALL / prefix
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.sh")):
            if not path.is_file():
                continue
            rel = _rel(path)
            if _wire_excluded(rel) or rel in seen:
                continue
            seen.add(rel)
            out.append(path)
    for name in WIRE_ROOT_FILES:
        path = INSTALL / name
        if path.is_file():
            rel = _rel(path)
            if rel not in seen and not _wire_excluded(rel):
                seen.add(rel)
                out.append(path)
    return out


def scan_registry(*, refresh: bool = True) -> dict[str, Any]:
    """Discover scripts, AML routes, py modules across NewLatest."""
    build = _load(BUILD_DOCTRINE, {})
    routes = build.get("script_routes") or {}
    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def _add(entry: dict[str, Any]) -> None:
        eid = str(entry.get("id", ""))
        if eid and eid not in seen_ids:
            seen_ids.add(eid)
            entries.append(entry)

    for route, aml in sorted(routes.items()):
        _add({"id": route, "kind": "route", "route": route, "aml": aml})

    for path in discover_shell_scripts():
        rel = _rel(path)
        sid = path.stem.replace("-", "_")
        if rel.startswith("Hostess7/"):
            sid = f"h7_{sid}"
        elif rel.startswith("Queen/"):
            sid = f"queen_{sid}"
        elif rel.startswith("KILROY/"):
            sid = f"kilroy_{sid}"
        _add({"id": sid, "kind": "script", "path": rel, "script": path.name})

    py_dirs = (INSTALL / "lib", INSTALL / "Hostess7" / "scripts", GROK16 / "lib", INSTALL / "Queen" / "lib")
    for base in py_dirs:
        if not base.is_dir():
            continue
        for path in sorted(base.glob("*.py")):
            rel = _rel(path)
            sid = path.stem.replace("-", "_")
            _add({"id": f"py_{sid}", "kind": "py", "path": rel, "module": path.stem})

    _add({"id": "hostess7", "kind": "hostess7", "path": "Hostess7/Hostess7.sh"})

    doc = {
        "schema": "field-ammolang-boundary-registry/v1",
        "updated": _now(),
        "entry_count": len(entries),
        "shell_count": len(discover_shell_scripts()),
        "entries": entries,
        "coverage": "NewLatest",
        "motto": _load(DOCTRINE, {}).get("motto"),
    }
    if refresh:
        _save(REGISTRY, doc)
    return doc


def wire_scripts(*, apply: bool = False, limit: int | None = None, scope: str = "all") -> dict[str, Any]:
    """Inject universal boundary shim into NewLatest shell entry points."""
    wired, skipped, missing, errors = [], [], [], []
    paths = discover_shell_scripts() if scope == "all" else sorted((INSTALL / "scripts").glob("*.sh"))
    if limit:
        paths = paths[:limit]
    for path in paths:
        rel = _rel(path)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            missing.append({"path": rel, "error": str(exc)[:80]})
            continue
        if _wire_excluded(rel) or _already_wired(text):
            skipped.append(rel)
            continue
        if not apply:
            wired.append(rel)
            continue
        try:
            shim = AML_SHIM.format(marker=AML_MARKER, script_rel=rel)
            path.write_text(shim + "\n" + text, encoding="utf-8")
            wired.append(rel)
        except OSError as exc:
            errors.append({"path": rel, "error": str(exc)[:80]})
    return {
        "ok": not errors,
        "apply": apply,
        "scope": scope,
        "wired": wired,
        "skipped": skipped,
        "missing": missing,
        "errors": errors,
        "wired_count": len(wired),
        "skipped_count": len(skipped),
        "discovered": len(paths),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    spec = _load(SPEC, {})
    registry = scan_registry(refresh=False)
    out = {
        "schema": "ammolang-boundary-panel/v1",
        "updated": _now(),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "last_target": spec.get("target"),
        "last_kind": spec.get("kind"),
        "registry_count": registry.get("entry_count", 0),
        "spec_path": str(SPEC),
        "universal_aml": _load(DOCTRINE, {}).get("aml"),
        "policy": _load(DOCTRINE, {}).get("policy", {}),
    }
    if write:
        _save(PANEL, out)
    return out


def resolve_and_save(target: str | None = None, extra: list[str] | None = None) -> dict[str, Any]:
    target = target or os.environ.get("AML_BOUNDARY_TARGET", "")
    extra = extra if extra is not None else _boundary_args()
    spec = resolve_target(target, extra)
    _save(SPEC, spec)
    build_panel(write=True)
    return spec


def execute_boundary(target: str | None = None, extra: list[str] | None = None, *, live: bool = True) -> dict[str, Any]:
    spec = resolve_and_save(target, extra)
    meta = {"exec", "boundary", "any", "run", "universal_boundary"}
    route_name = str(spec.get("route") or spec.get("target") or "")
    if spec.get("kind") == "route" and route_name not in meta:
        build = _mod("lib/field-ammolang-build.py")
        if build and hasattr(build, "run_named_script"):
            doc = build.run_named_script(route_name, live=live)
            doc["via"] = "boundary_route_delegate"
            doc["boundary"] = True
            return doc
    rep = run_spec(spec, live=live)
    rep["spec"] = spec
    build_panel(write=True)
    change = _mod("lib/hostess7-change-awareness.py")
    if change and hasattr(change, "pulse"):
        try:
            change.pulse(notify=False)
        except Exception:
            pass
    return rep


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "resolve":
        target = os.environ.get("AML_BOUNDARY_TARGET", "")
        extra = sys.argv[2:] if len(sys.argv) > 2 else _boundary_args()
        print(json.dumps(resolve_and_save(target, extra), ensure_ascii=False, indent=2))
        return 0
    if cmd == "run":
        target = os.environ.get("AML_BOUNDARY_TARGET", "")
        extra = _boundary_args()
        rep = execute_boundary(target, extra, live=os.environ.get("AML_DRY") != "1")
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1
    if cmd == "scan":
        print(json.dumps(scan_registry(refresh=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("wire", "wire-all", "wire_all"):
        apply = "--apply" in sys.argv
        limit = None
        scope = "scripts" if cmd == "wire" and "--scripts-only" in sys.argv else "all"
        for arg in sys.argv[2:]:
            if arg.startswith("--limit="):
                limit = int(arg.split("=", 1)[1])
        print(json.dumps(wire_scripts(apply=apply, limit=limit, scope=scope), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("ensure", "protect"):
        scan = scan_registry(refresh=True)
        wire = wire_scripts(apply="--apply" in sys.argv, scope="all")
        panel = build_panel(write=True)
        print(json.dumps({"ok": True, "scan": scan, "wire": wire, "panel": panel}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "exec" and len(sys.argv) > 2:
        target = sys.argv[2]
        extra = sys.argv[3:]
        os.environ["AML_BOUNDARY_TARGET"] = target
        os.environ["AML_BOUNDARY_ARGS_JSON"] = json.dumps(extra)
        rep = execute_boundary(target, extra)
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1
    print(json.dumps({
        "error": "usage",
        "hint": "field-ammolang-boundary.py [panel|resolve|run|scan|wire|exec TARGET args...]",
    }, indent=2))
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # grep/head closed the pipe after a match — treat as success
        try:
            sys.stdout.close()
        except OSError:
            pass
        raise SystemExit(0)