#!/usr/bin/env pythong
"""AmmoLang — AI-native combinatorics sequence language. Compile · interpret · no gaps."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-ammolang-doctrine.json"
SEED = INSTALL / "data" / "field-ammolang-seed.json"
PANEL = STATE / "field-ammolang-panel.json"
BATTERY = STATE / "field-ammolang.json"
EXAMPLES = INSTALL / "library" / "dewey" / "000-computer-science" / "ammolang"

_COMMENT = re.compile(r"#.*$")
_DIRECTIVE = re.compile(r"^@(\w+)\s+(.+)$")
_LEAF = re.compile(r"^leaf\s+(\S+)(?:\s+->\s+exec\s+canonical:(\w+))?", re.I)
_BOIL = re.compile(r'^boil\s+(\w+)\s+"([^"]*)"\s*->\s*(\w+)', re.I)
_BOIL_SQ = re.compile(r"^boil\s+(\w+)\s+'([^']*)'\s*->\s*(\w+)", re.I)
_EXEC = re.compile(r"^exec\s+canonical:(\w+)", re.I)
_WIRE = re.compile(r"^wire\s+(\S+)(?:\s+leaf\s+(\S+))?", re.I)
_GAP = re.compile(r"^gap\s+fill\s+(.+)$", re.I)
_SURFACE = re.compile(r"^surface\s+collapse(?:\s+depth:(\d+))?", re.I)
_WIDTH = re.compile(r"^width\s+(\d+)", re.I)
_GROW = re.compile(r"^grow\s+scan$", re.I)
_COMBINE = re.compile(r"^combine\s+(\S+)\s*\+\s*(\S+)", re.I)
_BIND = re.compile(r"^bind\s+(\w+)\s+(\S+)", re.I)
_SEQ_START = re.compile(r"^seq\s*[·.]", re.I)
_SUITE_START = re.compile(r"^suite\s+(\S+)\s*[·.]", re.I)
_PAR_START = re.compile(r"^par\s*[⊕+]", re.I)
_GROUP = re.compile(r"^group\s+(.+)$", re.I)
_ASSERT = re.compile(r"^assert\s+(.+)$", re.I)
_COMB_BLOCK_START = re.compile(r"^combinator\s+(\w+)\s*\{", re.I)
_COMB_BLOCK_END = re.compile(r"^\}\s*$")
_SAY = re.compile(r'^say\s+(?:"([^"]*)"|\'([^\']*)\'|(.+))$', re.I)
_FORGE = re.compile(r"^forge\s+(\S+)", re.I)
_TEST = re.compile(r"^test\s+(.+)$", re.I)
_FAST = re.compile(r"^fast\s+(.+)$", re.I)
_INVOKE = re.compile(r"^invoke\s+(.+)$", re.I)
_CHIPS = re.compile(r"^chips\s+(\S+)", re.I)
_ENSURE = re.compile(r"^ensure\s+(\S+)", re.I)
_STACK_WIRE = re.compile(r"^stack\s+wire\b", re.I)
_PLATE_MELD = re.compile(r"^plate\s+meld\b", re.I)
_REBALANCE = re.compile(r"^rebalance\s+(\S+)", re.I)
_CLEAN = re.compile(r"^clean\s+(\S+)", re.I)
_UPDATE = re.compile(r"^update\s+(\S+)", re.I)
_PROGRAM = re.compile(r"^program\s+(\S+)", re.I)
_VERIFY = re.compile(r"^verify\s+(\S+)", re.I)
_SELF = re.compile(r"^self\s+(\S+)", re.I)
_RUN = re.compile(r"^run\s+(.+)$", re.I)
_ASSIST = re.compile(r"^assist\s*(\S*)", re.I)
_GITHUB = re.compile(r"^github\s+(.+)$", re.I)
_POST = re.compile(r"^post\s+(.+)$", re.I)
_PROGRESS = re.compile(r"^progress\s+(.+)$", re.I)


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = INSTALL / "lib" / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None


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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _strip(line: str) -> str:
    return _COMMENT.sub("", line).strip()


def _append_step(steps: list[dict[str, Any]], step: dict[str, Any]) -> None:
    if steps and steps[-1].get("op") in ("SEQ", "PAR", "SUITE", "GROUP"):
        steps[-1].setdefault("children", []).append(step)
    else:
        steps.append(step)


def clear_parse_cache() -> None:
    """Drop parse LRU after AmmoLang self-upgrade."""
    _parse_cached.cache_clear()


@lru_cache(maxsize=64)
def _parse_cached(source: str) -> tuple[dict[str, str], list[dict[str, Any]], int, tuple[str, ...], bool]:
    """Cached parse core — directives, steps, step_count, errors, ok."""
    directives: dict[str, str] = {}
    steps: list[dict[str, Any]] = []
    block_stack: list[dict[str, Any]] = []
    errors: list[str] = []
    for lineno, raw in enumerate(source.splitlines(), 1):
        line = _strip(raw)
        if not line:
            continue
        if m := _DIRECTIVE.match(line):
            directives[m.group(1).lower()] = m.group(2).strip()
            continue
        if _COMB_BLOCK_END.match(line):
            if block_stack:
                block = block_stack.pop()
                _append_step(steps, block)
            else:
                errors.append(f"line {lineno}: unmatched `}}`")
            continue
        if m := _COMB_BLOCK_START.match(line):
            block = {"op": "COMBINATOR", "name": m.group(1).lower(), "line": lineno, "entries": []}
            block_stack.append(block)
            continue
        if block_stack:
            parts = line.split(None, 1)
            key = parts[0].lower()
            val = parts[1].strip() if len(parts) > 1 else ""
            block_stack[-1]["entries"].append({"key": key, "value": val, "line": lineno})
            continue
        if _SEQ_START.match(line):
            steps.append({"op": "SEQ", "line": lineno, "children": []})
            continue
        if m := _SUITE_START.match(line):
            steps.append({"op": "SUITE", "name": m.group(1), "line": lineno, "children": []})
            continue
        if _PAR_START.match(line):
            steps.append({"op": "PAR", "line": lineno, "children": []})
            continue
        body = line.lstrip()
        if body.startswith("  "):
            body = body.strip()
        step: dict[str, Any] | None = None
        if m := _SAY.match(body):
            step = {"op": "SAY", "spec": m.group(1) or m.group(2) or m.group(3) or "", "line": lineno}
        elif m := _FORGE.match(body):
            step = {"op": "FORGE", "spec": m.group(1), "line": lineno}
        elif m := _TEST.match(body):
            step = {"op": "TEST", "spec": m.group(1).strip(), "line": lineno}
        elif m := _GROUP.match(body):
            step = {"op": "GROUP", "name": m.group(1).strip(), "line": lineno, "children": []}
        elif m := _ASSERT.match(body):
            step = {"op": "ASSERT", "spec": m.group(1).strip(), "line": lineno}
        elif m := _FAST.match(body):
            step = {"op": "FAST", "spec": m.group(1).strip(), "line": lineno}
        elif m := _INVOKE.match(body):
            step = {"op": "INVOKE", "spec": m.group(1).strip(), "line": lineno}
        elif m := _CHIPS.match(body):
            step = {"op": "CHIPS", "spec": m.group(1), "line": lineno}
        elif m := _ENSURE.match(body):
            step = {"op": "ENSURE", "spec": m.group(1), "line": lineno}
        elif _STACK_WIRE.match(body):
            step = {"op": "WIRE_STACK", "spec": "wire", "line": lineno}
        elif _PLATE_MELD.match(body):
            step = {"op": "MELD", "spec": "fuse", "line": lineno}
        elif m := _REBALANCE.match(body):
            step = {"op": "REBALANCE", "spec": m.group(1), "line": lineno}
        elif m := _CLEAN.match(body):
            step = {"op": "CLEAN", "spec": m.group(1), "line": lineno}
        elif m := _UPDATE.match(body):
            step = {"op": "UPDATE", "spec": m.group(1), "line": lineno}
        elif m := _PROGRAM.match(body):
            step = {"op": "PROGRAM", "spec": m.group(1), "line": lineno}
        elif m := _VERIFY.match(body):
            step = {"op": "VERIFY", "spec": m.group(1), "line": lineno}
        elif m := _SELF.match(body):
            step = {"op": "SELF", "spec": m.group(1), "line": lineno}
        elif m := _RUN.match(body):
            step = {"op": "RUN", "spec": m.group(1).strip(), "line": lineno}
        elif m := _ASSIST.match(body):
            step = {"op": "ASSIST", "spec": (m.group(1) or "all").strip(), "line": lineno}
        elif m := _GITHUB.match(body):
            step = {"op": "GITHUB", "spec": m.group(1).strip(), "line": lineno}
        elif m := _POST.match(body):
            step = {"op": "POST", "spec": m.group(1).strip(), "line": lineno}
        elif m := _PROGRESS.match(body):
            step = {"op": "PROGRESS", "spec": m.group(1).strip(), "line": lineno}
        elif _GROW.match(body):
            step = {"op": "GROW", "action": "scan", "line": lineno}
        elif m := _SURFACE.match(body):
            step = {"op": "SURFACE", "depth": int(m.group(1) or 4), "line": lineno}
        elif m := _WIDTH.match(body):
            step = {"op": "WIDTH", "width": int(m.group(1)), "line": lineno}
        elif m := _LEAF.match(body):
            step = {"op": "LEAF", "id": m.group(1), "canonical": m.group(2), "line": lineno}
        elif m := _BOIL.match(body) or _BOIL_SQ.match(body):
            step = {"op": "BOIL", "lang": m.group(1), "command": m.group(2), "canonical": m.group(3), "line": lineno}
        elif m := _EXEC.match(body):
            step = {"op": "EXEC", "canonical": m.group(1), "line": lineno}
        elif m := _WIRE.match(body):
            step = {"op": "WIRE", "band": m.group(1), "leaf": m.group(2), "line": lineno}
        elif m := _GAP.match(body):
            step = {"op": "GAP", "target": m.group(1).strip(), "line": lineno}
        elif m := _COMBINE.match(body):
            step = {"op": "COMBINE", "left": m.group(1), "right": m.group(2), "line": lineno}
        elif m := _BIND.match(body):
            step = {"op": "BIND", "name": m.group(1), "leaf": m.group(2), "line": lineno}
        elif body in ("I", "K", "S"):
            step = {"op": body, "line": lineno}
        else:
            errors.append(f"line {lineno}: unrecognized `{body[:60]}`")
            continue
        if step:
            _append_step(steps, step)
    if block_stack:
        for block in block_stack:
            errors.append(f"line {block.get('line')}: unclosed combinator `{block.get('name')}`")
    return directives, steps, _count_steps(steps), tuple(errors), len(errors) == 0


def parse_ammolang(source: str) -> dict[str, Any]:
    """Parse AmmoLang source into AST — v1 sequence + combinamatrix + sovereign build ops."""
    directives, steps, step_count, errors, ok = _parse_cached(source)
    return {
        "schema": "ammolang-ast/v2",
        "directives": directives,
        "steps": steps,
        "step_count": step_count,
        "errors": list(errors),
        "ok": ok,
    }


def parse(source: str) -> dict[str, Any]:
    """Alias for test engine and external callers."""
    return parse_ammolang(source)


def _count_steps(steps: list[dict[str, Any]]) -> int:
    n = 0
    for s in steps:
        if s.get("op") in ("SEQ", "PAR"):
            n += _count_steps(s.get("children") or [])
        else:
            n += 1
    return n


def compile_ast(ast: dict[str, Any]) -> dict[str, Any]:
    """Compile AST to combinatorics sequence IR."""
    ir: list[dict[str, Any]] = []

    def walk(nodes: list[dict[str, Any]], *, parent: str = "root") -> None:
        for node in nodes:
            op = str(node.get("op") or "")
            row = {"op": op, "parent": parent, "line": node.get("line")}
            if op in ("SEQ", "PAR"):
                row["arity"] = len(node.get("children") or [])
                ir.append(row)
                walk(node.get("children") or [], parent=op)
            elif op == "LEAF":
                row["leaf_id"] = node.get("id")
                row["canonical"] = node.get("canonical")
                ir.append(row)
            elif op == "BOIL":
                row.update({"lang": node.get("lang"), "command": node.get("command"), "canonical": node.get("canonical")})
                ir.append(row)
            elif op == "GROW":
                row["action"] = node.get("action") or "scan"
                ir.append(row)
            elif op == "SURFACE":
                row["depth"] = node.get("depth")
                ir.append(row)
            elif op == "WIDTH":
                row["width"] = node.get("width")
                ir.append(row)
            elif op == "WIRE":
                row.update({"band": node.get("band"), "leaf": node.get("leaf")})
                ir.append(row)
            elif op == "GAP":
                row["target"] = node.get("target")
                ir.append(row)
            elif op == "EXEC":
                row["canonical"] = node.get("canonical")
                ir.append(row)
            elif op == "COMBINE":
                row.update({"left": node.get("left"), "right": node.get("right")})
                ir.append(row)
            elif op == "BIND":
                row.update({"name": node.get("name"), "leaf": node.get("leaf")})
                ir.append(row)
            elif op == "COMBINATOR":
                row.update({"name": node.get("name"), "entries": node.get("entries") or []})
                ir.append(row)
            elif op in ("SAY", "FORGE", "TEST", "FAST", "INVOKE", "CHIPS", "ENSURE"):
                row["spec"] = node.get("spec")
                ir.append(row)
            else:
                ir.append(row)

    walk(ast.get("steps") or [])
    return {
        "schema": "ammolang-ir/v1",
        "directives": ast.get("directives") or {},
        "ir": ir,
        "ir_length": len(ir),
        "ok": ast.get("ok", True),
    }


def _execute_combinator(name: str, entries: list[dict[str, Any]], *, dry_run: bool) -> dict[str, Any]:
    """Run combinamatrix block — observe/pack/wire/score/universal/emit."""
    if dry_run:
        return {"ok": True, "dry_run": True, "combinator": name, "entries": entries}
    result: dict[str, Any] = {"ok": True, "combinator": name}
    if name == "observe":
        result["sources"] = [e.get("value") or e.get("key") for e in entries if e.get("key") == "source"]
    elif name == "universal":
        uni = _import_mod("uni", "field-g16-universal-combinatronic.py")
        if uni and hasattr(uni, "publish_panel"):
            result["universal"] = uni.publish_panel(refresh=True).get("panel") or {}
    elif name == "emit":
        reb = _import_mod("reb", "g16-combinatronic-rebalance.py")
        if reb and hasattr(reb, "optimal"):
            result["rebalance"] = reb.optimal(refresh=True)
    elif name == "pack":
        cm = _import_mod("cm", "field-combinamatrix.py")
        if cm and hasattr(cm, "publish_panel"):
            result["combinamatrix"] = cm.publish_panel(refresh=True).get("panel") or {}
    elif name == "wire":
        sw = _import_mod("sw", "field-combinatronic-spider-wire.py")
        if sw and hasattr(sw, "publish_panel"):
            result["spider_wire"] = sw.publish_panel().get("panel") or {}
    else:
        result["entries"] = entries
    return result


def interpret_ir(ir_doc: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
    """Trace or execute AmmoLang IR — resolve leaves, boil, gap-fill, universal rebalance."""
    trace: list[dict[str, Any]] = []
    bindings: dict[str, str] = {}
    prog = _import_mod("fpc", "field-program-combinatronic.py")
    seq_mod = _import_mod("seq", "field-combinatorics-sequence.py")
    reb_mod = _import_mod("reb", "g16-combinatronic-rebalance.py")
    leaf_index: dict[str, dict[str, Any]] = {}
    if seq_mod and hasattr(seq_mod, "_collect_leaves"):
        leaves, _ = seq_mod._collect_leaves()
        leaf_index = {str(l["id"]): l for l in leaves}

    for i, row in enumerate(ir_doc.get("ir") or []):
        op = str(row.get("op") or "")
        entry: dict[str, Any] = {"step": i + 1, "op": op, "dry_run": dry_run}
        if op == "LEAF":
            lid = str(row.get("leaf_id") or "")
            entry["leaf_id"] = lid
            entry["resolved"] = leaf_index.get(lid, {"synthetic": True, "id": lid})
        elif op == "BOIL" and prog and hasattr(prog, "boil_command"):
            boiled = prog.boil_command(str(row.get("lang")), str(row.get("command")))
            entry["boiled"] = boiled
            entry["canonical"] = boiled.get("canonical")
        elif op == "GROW":
            if not dry_run:
                g = _import_mod("growth", "field-combinatronics-growth.py")
                if g and hasattr(g, "publish_panel"):
                    entry["result"] = g.publish_panel().get("panel")
            entry["action"] = row.get("action") or "scan"
        elif op == "GAP":
            entry["target"] = row.get("target")
            if not dry_run and seq_mod and hasattr(seq_mod, "publish_panel"):
                entry["gap_fill"] = seq_mod.publish_panel(refresh=True).get("panel")
        elif op == "EXEC":
            entry["canonical"] = row.get("canonical")
            entry["runner"] = "native_bsp"
            if not dry_run and reb_mod and hasattr(reb_mod, "optimal"):
                entry["exec"] = reb_mod.optimal(refresh=False)
        elif op == "WIRE":
            entry["band"] = row.get("band")
            entry["leaf"] = row.get("leaf")
            if not dry_run:
                sw = _import_mod("sw", "field-combinatronic-spider-wire.py")
                if sw and hasattr(sw, "publish_panel"):
                    entry["wire"] = sw.publish_panel().get("panel")
        elif op == "COMBINATOR":
            name = str(row.get("name") or "")
            entries = row.get("entries") or []
            entry["combinator"] = name
            entry["result"] = _execute_combinator(name, entries, dry_run=dry_run)
        elif op in ("SAY", "FORGE", "TEST", "FAST", "INVOKE", "CHIPS", "ENSURE") and not dry_run:
            build = _import_mod("aml_build", "field-ammolang-build.py")
            if build and hasattr(build, "execute_build_script"):
                entry["build_op"] = op
                entry["spec"] = row.get("spec")
                entry["note"] = "delegated_to_sovereign_build"
            else:
                entry["spec"] = row.get("spec")
                entry["note"] = "build_op_dry"
        elif op in ("SAY", "FORGE", "TEST", "FAST", "INVOKE", "CHIPS", "ENSURE"):
            entry["spec"] = row.get("spec")
            entry["build_op"] = op
        elif op == "BIND":
            bindings[str(row.get("name"))] = str(row.get("leaf"))
            entry["bindings"] = dict(bindings)
        elif op == "WIDTH":
            entry["width"] = row.get("width")
        elif op == "SURFACE":
            entry["depth"] = row.get("depth")
        elif op == "COMBINE":
            entry.update({"left": row.get("left"), "right": row.get("right")})
        else:
            entry["note"] = row
        trace.append(entry)

    return {
        "schema": "ammolang-trace/v1",
        "updated": _now(),
        "dry_run": dry_run,
        "live": not dry_run,
        "trace_length": len(trace),
        "bindings": bindings,
        "trace": trace[:128],
        "ok": True,
        "motto": "AmmoLang — combinatorics sequence for AmmoOS AI operators.",
    }


def compile_source(source: str) -> dict[str, Any]:
    ast = parse_ammolang(source)
    ir = compile_ast(ast)
    return {
        "schema": "field-ammolang/v1",
        "updated": _now(),
        "ok": ast.get("ok") and ir.get("ok"),
        "ast": ast,
        "ir": ir,
        "step_count": ast.get("step_count"),
        "ir_length": ir.get("ir_length"),
    }


def compile_file(path: Path) -> dict[str, Any]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "error": str(exc), "path": str(path)}
    doc = compile_source(source)
    doc["path"] = str(path)
    return doc


def publish_panel(*, refresh: bool = False) -> dict[str, Any]:
    seed = _load(SEED, {})
    examples: list[dict[str, Any]] = []
    for rel in (seed.get("examples") or []) + ["library/dewey/000-computer-science/ammolang/boot_sequence.aml"]:
        path = INSTALL / str(rel)
        if path.is_file():
            examples.append({"path": str(rel), **compile_file(path)})
    gen = INSTALL / "library" / "dewey" / "000-computer-science" / "ammolang" / "generated_sequence.aml"
    if refresh or not gen.is_file():
        seq = _import_mod("seq", "field-combinatorics-sequence.py")
        if seq and hasattr(seq, "publish_panel"):
            seq.publish_panel()
    if gen.is_file():
        examples.append({"path": str(gen.relative_to(INSTALL)), **compile_file(gen)})
    battery = {
        "schema": "field-ammolang/v1",
        "updated": _now(),
        "product": "AmmoOS",
        "motto": "AmmoLang — pure combinatorics language for AI.",
        "ok": True,
        "version": "1",
        "combinators": list((seed.get("combinators") or {}).keys()),
        "examples": examples,
        "example_count": len(examples),
    }
    panel = {
        "schema": "field-ammolang-panel/v1",
        "updated": battery["updated"],
        "ok": battery["ok"],
        "version": "1",
        "combinator_count": len(battery["combinators"]),
        "example_count": battery["example_count"],
        "preview": (examples[0].get("ir") or {}).get("ir", [])[:12] if examples else [],
    }
    _save(PANEL, panel)
    _save(BATTERY, battery)
    return {"ok": True, "panel": panel, "battery": battery}


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "panel").strip().lower().replace("-", "_")
    if action in ("panel", "status", "json"):
        if PANEL.is_file() and not body.get("refresh"):
            return {"ok": True, "panel": _load(PANEL)}
        return publish_panel(refresh=bool(body.get("refresh")))
    if action in ("compile", "parse"):
        source = str(body.get("source") or body.get("code") or "")
        if not source and body.get("path"):
            return compile_file(INSTALL / str(body["path"]))
        return compile_source(source)
    if action in ("interpret", "run", "trace"):
        if body.get("source"):
            compiled = compile_source(str(body["source"]))
        elif body.get("path"):
            compiled = compile_file(INSTALL / str(body["path"]))
        else:
            compiled = {"ir": body.get("ir") or {}}
        ir_doc = compiled.get("ir") or compiled
        if isinstance(ir_doc, dict) and "ir" not in ir_doc and compiled.get("ir"):
            ir_doc = compiled["ir"]
        return interpret_ir(ir_doc if isinstance(ir_doc, dict) else {"ir": []}, dry_run=body.get("dry_run", True))
    return {"ok": False, "error": "unknown_action", "actions": ["panel", "compile", "interpret"]}


def run_live(path: Path) -> dict[str, Any]:
    """Fastest live execution — sovereign build engine when build ops present."""
    source = path.read_text(encoding="utf-8")
    ast = parse_ammolang(source)
    build_ops = (
        "SAY", "FORGE", "TEST", "FAST", "INVOKE", "CHIPS", "ENSURE",
        "WIRE_STACK", "MELD", "REBALANCE", "CLEAN", "UPDATE", "PROGRAM", "VERIFY", "SELF", "RUN", "ASSIST", "GITHUB", "POST", "PROGRESS",
    )
    has_build = any(s.get("op") in build_ops for s in _flatten_steps(ast.get("steps") or []))
    if has_build or os.environ.get("AML_BUILD", "1") != "0":
        build = _import_mod("aml_build", "field-ammolang-build.py")
        if build and hasattr(build, "execute_build_script"):
            return build.execute_build_script(path, live=True)
    compiled = compile_file(path)
    return interpret_ir(compiled.get("ir") or {}, dry_run=False)


def _flatten_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for s in steps:
        if s.get("op") in ("SEQ", "PAR"):
            flat.extend(_flatten_steps(s.get("children") or []))
        else:
            flat.append(s)
    return flat


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json"):
        if PANEL.is_file() and "--refresh" not in sys.argv:
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_panel(refresh="--refresh" in sys.argv).get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "compile":
        path = Path(sys.argv[2]) if len(sys.argv) > 2 else EXAMPLES / "boot_sequence.aml"
        if not path.is_absolute():
            path = INSTALL / path
        print(json.dumps(compile_file(path), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("interpret", "trace", "run"):
        path = Path(sys.argv[2]) if len(sys.argv) > 2 else EXAMPLES / "boot_sequence.aml"
        if not path.is_absolute():
            path = INSTALL / path
        if "--live" in sys.argv:
            doc = run_live(path)
            print(json.dumps(doc, ensure_ascii=False, indent=2))
            return 0 if doc.get("ok", True) else 1
        compiled = compile_file(path)
        trace = interpret_ir(compiled.get("ir") or {}, dry_run=True)
        print(json.dumps(trace, ensure_ascii=False, indent=2))
        return 0
    if cmd == "build":
        build = _import_mod("aml_build", "field-ammolang-build.py")
        if not build:
            print(json.dumps({"ok": False, "error": "field-ammolang-build missing"}, indent=2))
            return 1
        path = Path(sys.argv[2]) if len(sys.argv) > 2 else INSTALL / "library/dewey/000-computer-science/ammolang/sovereign_build.aml"
        if not path.is_absolute():
            path = INSTALL / path
        doc = build.execute_build_script(path, live="--dry" not in sys.argv)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "example":
        EXAMPLES.mkdir(parents=True, exist_ok=True)
        boot = EXAMPLES / "boot_sequence.aml"
        if not boot.is_file():
            boot.write_text(_default_boot_aml(), encoding="utf-8")
        print(boot.read_text(encoding="utf-8"))
        return 0
    print(json.dumps({
        "error": "usage",
        "hint": "field-ammolang.py [panel|compile|interpret|build|example] [path.aml] [--refresh] [--live]",
    }, indent=2))
    return 1


def _default_boot_aml() -> str:
    return """# AmmoLang v1 — AmmoOS boot combinatorics sequence
# AI operators: compose only with combinatorics — no imperative gaps.

@width 16
@grow generations:8
@product AmmoOS

seq ·
  grow scan
  width 16
  surface collapse depth:4
  gap fill facet:combinatronics
  boil python "def" -> declare
  boil python "import" -> import
  boil c "if" -> branch
  leaf prog:canonical:exec
  combine g16:chip + g16:prog
  wire ironclad outward
  wire band:narrow:0 leaf prog:canonical:call
  exec canonical:exec
"""


if __name__ == "__main__":
    raise SystemExit(main())