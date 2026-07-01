#!/usr/bin/env pythong
"""Field Profiler — AI entry point for SG field programs (Python + Grok16 native/cmake).

Delegates native/cmake/.launch work to Grok16 grok16-profiler.py.
Profiles Python field scripts with cProfile. One command → one JSON.

Schema: field-profiler/v1
"""
from __future__ import annotations

import cProfile
import json
import os
import re
import pstats
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
from sg_paths import grok16_root

GROK16 = grok16_root()
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PROFILE_DIR = STATE / "field-profiler"
SCHEMA = "field-profiler/v1"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _grok16_profiler() -> Path:
    return GROK16 / "scripts" / "grok16-profiler.py"


def _is_launch(path: Path) -> bool:
    return path.suffix == ".launch" or path.name.endswith(".launch")


def _is_native_source(path: Path) -> bool:
    return path.suffix.lower() in (".cpp", ".c", ".cc", ".cxx", ".h", ".hpp")


def _run_grok16(*args: str, timeout: int = 600) -> dict[str, Any]:
    script = _grok16_profiler()
    if not script.is_file():
        return {"ok": False, "error": "grok16_profiler_missing", "path": str(script)}
    cmd = [sys.executable, str(script), *args]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(GROK16),
            env={**os.environ, "GROK16_ROOT": str(GROK16), "NEXUS_INSTALL_ROOT": str(INSTALL), "SG_ROOT": str(SG)},
        )
        try:
            return json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            return {"ok": False, "error": "grok16_profiler_bad_json", "tail": (proc.stdout or proc.stderr or "")[-3000:]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}


def _profile_python(script: Path, script_args: list[str], *, timeout: int = 300) -> dict[str, Any]:
    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *script_args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(script.parent),
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "SG_ROOT": str(SG)},
        )
        rc = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
    except subprocess.TimeoutExpired:
        rc = 124
        stdout = ""
        stderr = "timeout"
    finally:
        pr.disable()
    wall_ms = round((time.perf_counter() - t0) * 1000, 2)
    stream = StringIO()
    stats = pstats.Stats(pr, stream=stream)
    stats.sort_stats("cumulative")
    stats.print_stats(40)
    text = stream.getvalue()
    hot: list[dict[str, Any]] = []
    for line in text.splitlines():
        m = re.match(r"\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(.+)$", line)
        if not m:
            continue
        ncalls, tottime, cumtime, _per, func = m.groups()
        if func.startswith("function calls"):
            continue
        hot.append({
            "ncalls": int(ncalls),
            "tottime_s": float(tottime),
            "cumtime_s": float(cumtime),
            "function": func.strip(),
        })
        if len(hot) >= 15:
            break
    bottlenecks = []
    for row in hot[:5]:
        cum_ms = round(row["cumtime_s"] * 1000, 2)
        bottlenecks.append({
            "id": "python_hot",
            "severity": "high" if cum_ms > 500 else "medium",
            "ms": cum_ms,
            "function": row["function"],
            "hint": f"Hot Python path — inspect {row['function']} or cache/subprocess calls.",
        })
    return {
        "ok": rc == 0,
        "kind": "python",
        "script": str(script),
        "args": script_args,
        "wall_ms": wall_ms,
        "returncode": rc,
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-1000:],
        "hot_functions": hot,
        "bottlenecks": bottlenecks,
        "profile_text": text[-8000:],
    }


def profile_target(
    target: Path,
    *,
    args: list[str] | None = None,
    profile: str | None = None,
) -> dict[str, Any]:
    args = args or []
    session = uuid.uuid4().hex[:12]
    if _is_launch(target):
        grok = _run_grok16("run", "--launch", str(target), *(["--profile", profile] if profile else []))
        return {
            "schema": SCHEMA,
            "session_id": session,
            "updated": _now(),
            "delegate": "grok16-profiler",
            "target": {"kind": "launch", "path": str(target)},
            "grok16": grok,
            "ok": grok.get("ok", False),
            "bottlenecks": grok.get("bottlenecks", []),
            "suggestions": grok.get("suggestions", []),
            "totals": grok.get("totals", {}),
            "motto": "Field program profiled — read bottlenecks + suggestions, then apply.",
        }
    if _is_native_source(target):
        grok = _run_grok16("run", "--source", str(target), *(["--profile", profile] if profile else []))
        return {
            "schema": SCHEMA,
            "session_id": session,
            "updated": _now(),
            "delegate": "grok16-profiler",
            "target": {"kind": "source", "path": str(target)},
            "grok16": grok,
            "ok": grok.get("ok", False),
            "bottlenecks": grok.get("bottlenecks", []),
            "suggestions": grok.get("suggestions", []),
            "totals": grok.get("totals", {}),
        }
    if target.suffix == ".py" and target.is_file():
        py = _profile_python(target, args)
        return {
            "schema": SCHEMA,
            "session_id": session,
            "updated": _now(),
            "delegate": "cProfile",
            "target": {"kind": "python", "path": str(target)},
            "python": py,
            "ok": py.get("ok", False),
            "bottlenecks": py.get("bottlenecks", []),
            "totals": {"wall_ms": py.get("wall_ms", 0)},
            "suggestions": [{
                "action": "inspect_hot_functions",
                "reason": "See python.hot_functions — reduce subprocess/import in hot path",
            }] if py.get("hot_functions") else [],
        }
    if target.is_file() and os.access(target, os.X_OK):
        grok = _run_grok16("run", "--binary", str(target))
        return {
            "schema": SCHEMA,
            "session_id": session,
            "updated": _now(),
            "delegate": "grok16-profiler",
            "target": {"kind": "binary", "path": str(target)},
            "grok16": grok,
            "ok": grok.get("ok", False),
            "bottlenecks": grok.get("bottlenecks", []),
            "suggestions": grok.get("suggestions", []),
        }
    return {"schema": SCHEMA, "ok": False, "error": "unsupported_target", "path": str(target)}


def collect(target: Path | None = None, *, out: Path | None = None) -> dict[str, Any]:
    if target:
        doc = profile_target(target)
    else:
        doc = _run_grok16("collect")
        doc = {"schema": SCHEMA, "delegate": "grok16-profiler", "grok16": doc, "ok": doc.get("ok", True)}
    path = out or PROFILE_DIR / "latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    doc["report_path"] = str(path)
    return doc


def posture() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "install_root": str(INSTALL),
        "grok16_root": str(GROK16),
        "grok16_profiler": str(_grok16_profiler()),
        "profile_dir": str(PROFILE_DIR),
        "commands": {
            "run": "field-profiler.py run TARGET [--args ...] [--profile NAME]",
            "collect": "field-profiler.py collect [TARGET] [--out PATH]",
            "diagnose": "field-profiler.py diagnose",
            "grok16": "field-profiler.py grok16 [run|compare|diagnose|collect|apply ...]",
        },
        "targets": {
            "python": ".py field scripts (cProfile)",
            "native": ".cpp/.c via Grok16 g16 compile+run",
            "launch": ".launch chambers via Grok16",
            "binary": "executable via Grok16 run timing",
        },
        "motto": "One JSON for AI — bottlenecks, suggestions, report_path.",
    }


def main() -> int:
    argv = sys.argv[1:]
    cmd = (argv[0] if argv else "json").strip().lower()
    target: Path | None = None
    profile: str | None = None
    out: Path | None = None
    extra_args: list[str] = []
    dry_run = False
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in ("--profile", "-p") and i + 1 < len(argv):
            profile = argv[i + 1]
            i += 2
            continue
        if a == "--out" and i + 1 < len(argv):
            out = Path(argv[i + 1])
            i += 2
            continue
        if a == "--args" and i + 1 < len(argv):
            extra_args = argv[i + 1].split()
            i += 2
            continue
        if a == "--dry-run":
            dry_run = True
            i += 1
            continue
        if not a.startswith("-") and target is None and cmd in ("run", "collect"):
            target = Path(a)
            i += 1
            continue
        i += 1

    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "run":
        if not target:
            print(json.dumps({"error": "usage: field-profiler.py run TARGET"}, ensure_ascii=False), file=sys.stderr)
            return 2
        doc = profile_target(target, args=extra_args, profile=profile)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") is not False else 1
    if cmd == "collect":
        doc = collect(target, out=out)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    if cmd == "diagnose":
        grok = _run_grok16("diagnose")
        doc = {"schema": SCHEMA, "grok16": grok, "ok": True}
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    if cmd == "grok16":
        sub = argv[1:] if len(argv) > 1 else ["json"]
        doc = _run_grok16(*sub)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    if cmd == "apply" and target:
        doc = _run_grok16("apply", "--launch", str(target), *(["--profile", profile] if profile else []), *(["--dry-run"] if dry_run else []))
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-profiler.py [json|run|collect|diagnose|grok16|apply]", "posture": posture()}, ensure_ascii=False), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())