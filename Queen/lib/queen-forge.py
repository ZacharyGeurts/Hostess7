#!/usr/bin/env pythong
"""Queen Forge — sovereign inside build system. Every tool native, no shell scripts."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow `from forge.*` when invoked as script from Queen/lib/
_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from forge.engine import ForgeContext, ForgeEngine, ForgeResult  # noqa: E402
from forge.field_paths import field_status, kernel_runtime  # noqa: E402
from forge.field_tech_pipeline import field_tech_plan, write_drops_manifest  # noqa: E402
from forge.tools import CORE_ORDER, HOSTESS_PIPELINE_ORDER, SOVEREIGN_FIELD_ORDER, TOOL_REGISTRY  # noqa: E402

QUEEN = _LIB.parent


def _aml_build_enabled() -> bool:
    return os.environ.get("AML_BUILD", "1").strip().lower() not in ("0", "false", "no", "off")


def _run_via_ammolang(script: str) -> dict[str, Any] | None:
    if not _aml_build_enabled():
        return None
    build_py = QUEEN.parent / "lib" / "field-ammolang-build.py"
    if not build_py.is_file():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location("aml_build_forge", build_py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "execute_build_script"):
        return None
    path = QUEEN.parent / "library" / "dewey" / "000-computer-science" / "ammolang" / script
    if not path.is_file():
        return None
    return mod.execute_build_script(path, live=True)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_manifest() -> dict[str, Any]:
    path = QUEEN / "data/queen-forge-manifest.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _tool_row(tool_id: str) -> dict[str, Any]:
    t = TOOL_REGISTRY[tool_id]
    ctx = ForgeContext.from_env()
    return {
        "id": tool_id,
        "label": t.label,
        "track": t.track,
        "kind": t.kind,
        "optional": t.optional,
        "ready": t.check(ctx),
        "replaces": t.replaces,
        "native": True,
    }


def forge_status() -> dict[str, Any]:
    ctx = ForgeContext.from_env()
    manifest = _load_manifest()
    tools = [_tool_row(tid) for tid in TOOL_REGISTRY]
    core = [t for t in tools if t["track"] == "core" and t["kind"] == "core"]
    core_ready = sum(1 for t in core if t["ready"])
    brain = {}
    try:
        brain = json.loads((QUEEN / "data/queen-brain-manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    bin_path = ctx.build / "bin/Linux/queen-browser"
    if not bin_path.is_file():
        bin_path = ctx.build / "bin/queen-browser"
    return {
        "schema": "queen-forge/v1",
        "updated": _now(),
        "queen_root": str(QUEEN),
        "install_root": str(ctx.install),
        "inside": (QUEEN / ".queen-inside").is_file(),
        "forge_log": str(ctx.forge_log),
        "brain": brain.get("title", "Queen DARPA Robot Brain"),
        "brain_stack": brain.get("brain_stack", {}),
        "hostess7_sdf_storage": brain.get("hostess7_sdf_storage", {}),
        "motto": brain.get("motto", "Browser from scratch. Brain inside. Build yourself."),
        "core_ready": core_ready,
        "core_total": len(core),
        "all_core_ready": core_ready == len(core),
        "binary": str(bin_path),
        "binary_ready": bin_path.is_file() and os.access(bin_path, os.X_OK),
        "core_order": CORE_ORDER,
        "field_order": SOVEREIGN_FIELD_ORDER,
        "tools": tools,
        "manifest": manifest.get("title", "Queen Forge"),
        "field": field_status(ctx.queen),
        "field_kernel_running": kernel_runtime().get("field_kernel_running", False),
    }


_ALWAYS_RUN = frozenset({"forge_test", "compiler_probe"})


def run_tool(tool_id: str, *, clear_log: bool = False, force: bool = False) -> dict[str, Any]:
    if tool_id not in TOOL_REGISTRY:
        return {"ok": False, "error": "unknown_tool", "tool": tool_id}
    ctx = ForgeContext.from_env()
    engine = ForgeEngine(ctx)
    if clear_log:
        engine.clear_log()
    engine.log(f"FORGE START {tool_id}")
    t = TOOL_REGISTRY[tool_id]
    if not force and tool_id not in _ALWAYS_RUN and t.check(ctx):
        engine.log(f"FORGE SKIP {tool_id} — already ready")
        out = {
            "ok": True,
            "tool": tool_id,
            "skipped": True,
            "ready": True,
            "status": forge_status(),
        }
        if tool_id == "forge_test":
            report = ctx.queen / "data" / "forge-test-report.json"
            if report.is_file():
                try:
                    out["report"] = json.loads(report.read_text(encoding="utf-8"))
                    out["report_path"] = str(report)
                except (OSError, json.JSONDecodeError):
                    pass
        return out
    try:
        result = t.run(ctx, engine)
    except Exception as exc:
        engine.log(f"FORGE ERROR {tool_id}: {exc}")
        result = ForgeResult(ok=False, tool=tool_id, message=str(exc), tail=engine.tail_buffer())
    engine.log(f"FORGE END {tool_id} ok={result.ok}")
    out = result.to_dict()
    if tool_id == "forge_test":
        report = ctx.queen / "data" / "forge-test-report.json"
        if report.is_file():
            try:
                out["report"] = json.loads(report.read_text(encoding="utf-8"))
                out["report_path"] = str(report)
            except (OSError, json.JSONDecodeError):
                pass
    out["status"] = forge_status()
    return out


def run_sovereign_field(*, clear_log: bool = True) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for tid in SOVEREIGN_FIELD_ORDER:
        row = _tool_row(tid)
        if row["ready"] and tid not in ("field_package", "verify"):
            results.append({"tool": tid, "skipped": True, "ready": True, "ok": True})
            continue
        out = run_tool(tid, clear_log=clear_log and not results)
        results.append(out)
        if not out.get("ok") and tid in ("inside", "field_kernel", "field_package"):
            break
    return {
        "ok": all(r.get("ok", r.get("ready")) for r in results),
        "pipeline": "sovereign_field",
        "results": results,
        "status": forge_status(),
    }


def run_hostess_pipeline(*, clear_log: bool = True) -> dict[str, Any]:
    """Compiler probe → teach → textbook ZAC → verify → forge_test."""
    results: list[dict[str, Any]] = []
    for tid in HOSTESS_PIPELINE_ORDER:
        row = _tool_row(tid)
        if row["ready"] and tid not in ("forge_test", "hostess_verify"):
            results.append({"tool": tid, "skipped": True, "ready": True, "ok": True})
            continue
        out = run_tool(tid, clear_log=clear_log and not results)
        results.append(out)
        if not out.get("ok") and tid in ("compiler_probe", "forge_test"):
            break
    return {
        "ok": all(r.get("ok", r.get("ready")) for r in results),
        "pipeline": "hostess",
        "results": results,
        "status": forge_status(),
    }


def run_all_core(*, clear_log: bool = True) -> dict[str, Any]:
    """Field Technology optimized core — AmmoLang sovereign when AML_BUILD=1."""
    aml = _run_via_ammolang("queen_forge.aml")
    if aml is not None:
        return {
            "ok": bool(aml.get("ok")),
            "pipeline": "ammolang_queen_forge",
            "ammolang": aml,
            "status": forge_status(),
        }
    ctx = ForgeContext.from_env()
    order = field_tech_plan(ctx)
    results: list[dict[str, Any]] = []
    for tid in order:
        row = _tool_row(tid)
        if row["ready"] and tid not in ("verify",):
            results.append({"tool": tid, "skipped": True, "ready": True, "ok": True})
            continue
        out = run_tool(tid, clear_log=clear_log and not results)
        results.append(out)
        if not out.get("ok") and tid in ("inside", "deps", "shaders", "rtx"):
            break
    write_drops_manifest(ctx)
    return {
        "ok": all(r.get("ok", r.get("ready")) for r in results),
        "pipeline": "field_tech",
        "order": order,
        "results": results,
        "status": forge_status(),
    }


def run_field_tech(*, clear_log: bool = True) -> dict[str, Any]:
    return run_tool("field_tech", clear_log=clear_log)


def field_tech_drops() -> dict[str, Any]:
    ctx = ForgeContext.from_env()
    path = write_drops_manifest(ctx)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        doc = {}
    return {"ok": True, "path": str(path), "drops": doc}


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "json"):
        return forge_status()
    if action in ("run", "build", "forge"):
        return run_tool(str(body.get("tool") or body.get("stage") or "rtx"))
    if action in ("run-all", "run_all", "build-all", "build_all", "forge-all"):
        return run_all_core()
    if action in ("field-tech", "field_tech", "run-field-tech"):
        return run_field_tech()
    if action in ("drops", "field-drops", "field_drops"):
        return field_tech_drops()
    if action in ("run-field", "run_field", "field", "sovereign-field", "sovereign_field"):
        return run_sovereign_field()
    if action in ("run-hostess", "run_hostess", "hostess", "hostess-pipeline"):
        return run_hostess_pipeline()
    if action in ("forge-test", "forge_test", "test-all", "test_all"):
        return run_tool("forge_test", force=True)
    if action == "log":
        ctx = ForgeContext.from_env()
        parts: list[str] = []
        for path in (ctx.forge_log, ctx.state_log):
            try:
                parts.append(path.read_text(encoding="utf-8"))
            except OSError:
                pass
        text = "\n".join(parts)
        return {"ok": True, "log": text[-12000:]}
    if action == "tools":
        return {"ok": True, "tools": [_tool_row(t) for t in TOOL_REGISTRY]}
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(forge_status(), ensure_ascii=False))
        return 0
    if cmd == "run" and len(sys.argv) >= 3:
        out = run_tool(sys.argv[2], clear_log=True)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd in ("run-all", "run_all", "build-all"):
        out = run_all_core()
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd in ("aml-build", "aml_build", "sovereign"):
        aml = _run_via_ammolang("sovereign_build.aml")
        print(json.dumps(aml or {"ok": False, "error": "ammolang_build_unavailable"}, ensure_ascii=False))
        return 0 if aml and aml.get("ok") else 1
    if cmd in ("field-tech", "field_tech"):
        out = run_field_tech()
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd == "drops":
        print(json.dumps(field_tech_drops(), ensure_ascii=False))
        return 0
    if cmd in ("run-field", "run_field", "field"):
        out = run_sovereign_field()
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd in ("run-hostess", "run_hostess", "hostess"):
        out = run_hostess_pipeline()
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd in ("forge-test", "forge_test", "test-all"):
        out = run_tool("forge_test", force=True)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd == "log":
        print(json.dumps(dispatch({"action": "log"}), ensure_ascii=False))
        return 0
    if cmd == "tools":
        print(json.dumps(dispatch({"action": "tools"}), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: queen-forge.py [json|run TOOL|run-all|field-tech|drops|log|tools|dispatch]",
        "tools": list(TOOL_REGISTRY),
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())