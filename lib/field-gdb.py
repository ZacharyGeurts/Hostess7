#!/usr/bin/env pythong
"""Field GDB — field-native debug face: highlight, charts, AI decode/repair via bugfinder."""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
from sg_paths import grok16_root

GROK16 = grok16_root()
FIELD = Path(os.environ.get("GDB_FIELD_ROOT", SG / "GDB-Field"))
DOCTRINE = FIELD / "data" / "field-gdb-doctrine.json"
PANEL = STATE / "field-gdb-panel.json"
SESSION = STATE / "field-gdb-session.json"

ANSI = {
    "reset": "\033[0m",
    "addr": "\033[38;5;81m",
    "opcode": "\033[38;5;221m",
    "reg": "\033[38;5;120m",
    "imm": "\033[38;5;213m",
    "comment": "\033[38;5;245m",
    "keyword": "\033[38;5;75m",
    "string": "\033[38;5;156m",
    "number": "\033[38;5;179m",
    "error": "\033[38;5;203m",
    "frame": "\033[38;5;117m",
    "title": "\033[38;5;255m\033[1m",
}

ASM_LINE = re.compile(
    r"^(\s*[0-9a-f]+:)\s+((?:[0-9a-f]{2}(?:\s+[0-9a-f]{2})*)\s+)?(<[^>]+>:)?\s*(.*)$",
    re.I,
)
C_KEYWORDS = frozenset({
    "if", "else", "for", "while", "return", "struct", "typedef", "static", "const",
    "void", "int", "char", "float", "double", "long", "short", "unsigned", "signed",
    "class", "public", "private", "protected", "namespace", "template", "virtual",
})
PY_KEYWORDS = frozenset({
    "def", "class", "if", "elif", "else", "for", "while", "return", "import", "from",
    "try", "except", "finally", "with", "async", "await", "lambda", "yield", "pass",
})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _tool(name: str, fallback: str) -> str:
    g16 = GROK16 / "bin" / name
    if g16.is_file():
        return str(g16)
    found = shutil.which(name) or shutil.which(fallback)
    return found or name


def _gdb_bin() -> str:
    return shutil.which("gdb") or "gdb"


def _objdump_bin() -> str:
    return _tool("g16-objdump", "objdump")


def _bugfinder_mod() -> Any | None:
    path = INSTALL / "lib" / "field-code-bugfinder.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_code_bugfinder", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ironclad_slice() -> dict[str, Any]:
    dc = SG / "NewLatest" / "Hostess7" / "scripts" / "field_detective_corpus.py"
    if not dc.is_file():
        dc = INSTALL / "Hostess7" / "scripts" / "field_detective_corpus.py"
    if not dc.is_file():
        return {"ok": False, "verdict": "MISSING"}
    spec = importlib.util.spec_from_file_location("fdc", dc)
    if not spec or not spec.loader:
        return {"ok": False}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ironclad_slice() if hasattr(mod, "ironclad_slice") else {"ok": False}


def highlight_asm_line(line: str, *, ansi: bool = True) -> dict[str, Any]:
    """Tokenize one disassembly line for terminal or HTML."""
    m = ASM_LINE.match(line)
    tokens: list[dict[str, str]] = []
    if not m:
        tokens.append({"kind": "raw", "text": line})
    else:
        addr, _bytes, sym, rest = m.groups()
        if addr:
            tokens.append({"kind": "addr", "text": addr})
        if sym:
            tokens.append({"kind": "symbol", "text": sym})
        if rest:
            parts = rest.split(None, 1)
            if parts:
                tokens.append({"kind": "opcode", "text": parts[0]})
                if len(parts) > 1:
                    tail = parts[1]
                    for chunk in re.split(r"(%[a-z0-9]+|0x[0-9a-f]+|\$[0-9]+)", tail):
                        if not chunk:
                            continue
                        if chunk.startswith("%"):
                            tokens.append({"kind": "reg", "text": chunk})
                        elif chunk.startswith("0x") or chunk.startswith("$"):
                            tokens.append({"kind": "imm", "text": chunk})
                        else:
                            tokens.append({"kind": "text", "text": chunk})
    if ansi:
        rendered = ""
        for t in tokens:
            kind = t["kind"]
            color = {
                "addr": "addr", "opcode": "opcode", "reg": "reg", "imm": "imm",
                "symbol": "frame", "keyword": "keyword",
            }.get(kind, "reset")
            rendered += ANSI.get(color, "") + t["text"] + ANSI["reset"]
        return {"tokens": tokens, "ansi": rendered, "plain": line}
    return {"tokens": tokens, "plain": line}


def highlight_source_line(line: str, *, lang: str = "c", ansi: bool = True) -> dict[str, Any]:
    stripped = line.rstrip("\n")
    tokens: list[dict[str, str]] = []
    if "#" in stripped and lang in ("c", "cpp", "python"):
        code, _, comment = stripped.partition("#" if lang == "python" else "//" if "//" in stripped else "#")
        if lang != "python" and "//" in stripped:
            code, _, comment = stripped.partition("//")
        else:
            comment = ""
            code = stripped
    else:
        code, comment = stripped, ""

    kwset = PY_KEYWORDS if lang == "python" else C_KEYWORDS
    for word in re.findall(r"[A-Za-z_]\w*|\d+\.?\d*|\"[^\"]*\"|'[^']*'|[^\s]", code):
        if word in kwset:
            tokens.append({"kind": "keyword", "text": word})
        elif word.startswith('"') or word.startswith("'"):
            tokens.append({"kind": "string", "text": word})
        elif re.match(r"^\d", word):
            tokens.append({"kind": "number", "text": word})
        else:
            tokens.append({"kind": "text", "text": word})
    if comment:
        tokens.append({"kind": "comment", "text": comment})

    if ansi:
        rendered = ""
        for t in tokens:
            kind = t["kind"]
            color = {
                "keyword": "keyword", "string": "string", "number": "number", "comment": "comment",
            }.get(kind, "reset")
            rendered += ANSI.get(color, "") + t["text"] + ANSI["reset"]
        if rendered and not rendered.endswith("\n"):
            rendered += "\n"
        return {"tokens": tokens, "ansi": rendered, "plain": stripped}
    return {"tokens": tokens, "plain": stripped}


def disassemble(
    binary: Path,
    *,
    symbol: str = "",
    max_lines: int = 64,
    highlight: bool = True,
) -> dict[str, Any]:
    binary = binary.expanduser().resolve()
    if not binary.is_file():
        return {"ok": False, "error": "binary_missing", "path": str(binary)}
    cmd = [_objdump_bin(), "-d", "-C"]
    if symbol:
        cmd.extend(["--disassemble", symbol])
    cmd.append(str(binary))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "cmd": cmd}
    lines = (proc.stdout or "").splitlines()[:max_lines]
    rows = [highlight_asm_line(ln) if highlight else {"plain": ln} for ln in lines]
    return {
        "ok": proc.returncode == 0,
        "binary": str(binary),
        "disassembler": cmd[0],
        "line_count": len(rows),
        "lines": rows,
        "stderr": (proc.stderr or "")[-500:],
    }


def parse_backtrace(gdb_text: str) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    for line in gdb_text.splitlines():
        m = re.match(r"#(\d+)\s+(0x[0-9a-f]+)\s+in\s+(\S+)\s*(?:\(([^)]*)\))?\s+at\s+([^:]+):(\d+)", line, re.I)
        if m:
            frames.append({
                "depth": int(m.group(1)),
                "pc": m.group(2),
                "function": m.group(3),
                "args": m.group(4) or "",
                "file": m.group(5),
                "line": int(m.group(6)),
            })
            continue
        m2 = re.match(r"#(\d+)\s+(0x[0-9a-f]+)\s+in\s+(\S+)", line, re.I)
        if m2:
            frames.append({
                "depth": int(m2.group(1)),
                "pc": m2.group(2),
                "function": m2.group(3),
                "file": "",
                "line": 0,
            })
    return frames


def graph_call_stack(frames: list[dict[str, Any]]) -> dict[str, Any]:
    """Chart.js / panel-ready call stack graph."""
    nodes = []
    edges = []
    for i, fr in enumerate(frames):
        nid = f"f{fr.get('depth', i)}"
        label = fr.get("function") or nid
        nodes.append({
            "id": nid,
            "label": label,
            "depth": fr.get("depth", i),
            "file": fr.get("file"),
            "line": fr.get("line"),
            "pc": fr.get("pc"),
            "color": f"hsl({(220 - i * 18) % 360}, 70%, 55%)",
        })
        if i > 0:
            edges.append({
                "from": f"f{frames[i - 1].get('depth', i - 1)}",
                "to": nid,
                "kind": "call",
            })
    return {
        "schema": "field-gdb-graph/v1",
        "type": "call_stack",
        "title": "Call stack",
        "nodes": nodes,
        "edges": edges,
        "chart": {
            "type": "bar",
            "labels": [n["label"] for n in nodes],
            "datasets": [{
                "label": "stack depth",
                "data": [n["depth"] for n in nodes],
                "backgroundColor": [n["color"] for n in nodes],
            }],
        },
    }


def graph_register_timeline(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Time-series register snapshots for charting."""
    labels = [str(s.get("step", i)) for i, s in enumerate(samples)]
    series: dict[str, list[Any]] = {}
    for i, s in enumerate(samples):
        for reg, val in (s.get("regs") or {}).items():
            series.setdefault(reg, [])
            while len(series[reg]) < i:
                series[reg].append(None)
            series[reg].append(val)
    datasets = []
    palette = [81, 120, 221, 213, 203, 117]
    for j, (reg, data) in enumerate(sorted(series.items())):
        datasets.append({
            "label": reg,
            "data": data,
            "borderColor": f"hsl({palette[j % len(palette)]}, 70%, 55%)",
            "fill": False,
        })
    return {
        "schema": "field-gdb-graph/v1",
        "type": "register_timeline",
        "title": "Register timeline",
        "labels": labels,
        "chart": {"type": "line", "labels": labels, "datasets": datasets},
    }


def gdb_batch(binary: Path, commands: list[str], *, timeout: int = 45) -> dict[str, Any]:
    binary = binary.expanduser().resolve()
    if not binary.is_file():
        return {"ok": False, "error": "binary_missing"}
    lines = ["set pagination off", "set print pretty on"] + commands + ["quit"]
    cmd = [_gdb_bin(), "-q", "-batch", "-ex", f"file {binary}"] + [
        x for c in lines for x in ("-ex", c)
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "cmd": cmd}
    out = proc.stdout or ""
    frames = parse_backtrace(out)
    return {
        "ok": proc.returncode == 0,
        "gdb": _gdb_bin(),
        "binary": str(binary),
        "stdout": out[-8000:],
        "stderr": (proc.stderr or "")[-2000:],
        "frames": frames,
        "graph": graph_call_stack(frames) if frames else None,
    }


def ai_decode(
    *,
    source_path: Path | None = None,
    source_text: str = "",
    stop_reason: str = "",
    frames: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Decode crash/stop via bugfinder + KB + Ironclad."""
    ic = _ironclad_slice()
    bf = _bugfinder_mod()
    context_lines: list[str] = []
    if stop_reason:
        context_lines.append(f"Stop: {stop_reason}")
    for fr in (frames or [])[:8]:
        context_lines.append(
            f"#{fr.get('depth')} {fr.get('function')} at {fr.get('file')}:{fr.get('line')} pc={fr.get('pc')}"
        )
    context = "\n".join(context_lines)

    scan_out: dict[str, Any] = {}
    if bf:
        if source_text.strip():
            scan_out = bf.find_bugs(Path("."), source_text=source_text, max_compares=64)
        elif source_path and source_path.is_file():
            scan_out = bf.find_bugs(source_path, max_compares=96)
        elif source_path and source_path.is_dir():
            scan_out = bf.find_bugs(source_path, max_compares=64)

    kb_hits: list[dict[str, Any]] = []
    if bf and hasattr(bf, "kb_search"):
        query = " ".join(filter(None, [stop_reason, (frames or [{}])[0].get("function", "")]))
        kb_hits.append(bf.kb_search(query or "debugger crash segfault", limit=6))

    heuristics = [b for b in (scan_out.get("heuristics") or []) if b.get("verdict") == "heuristic"]
    decode = {
        "schema": "field-gdb-decode/v1",
        "updated": _now(),
        "stop_reason": stop_reason,
        "context": context,
        "ironclad": ic,
        "bugfinder": {
            "bug_count": scan_out.get("bug_count"),
            "heuristic_actionable": scan_out.get("heuristic_actionable"),
            "rate": scan_out.get("truth_compares_per_sec"),
        },
        "heuristic_findings": heuristics[:12],
        "kb": kb_hits[0] if kb_hits else {},
        "summary": _decode_summary(stop_reason, frames, heuristics, ic),
    }
    return {"ok": True, **decode}


def _decode_summary(
    stop_reason: str,
    frames: list[dict[str, Any]] | None,
    heuristics: list[dict[str, Any]],
    ic: dict[str, Any],
) -> str:
    parts: list[str] = []
    if stop_reason:
        parts.append(f"Stopped: {stop_reason}.")
    if frames:
        top = frames[0]
        parts.append(f"Top frame: {top.get('function')} ({top.get('file')}:{top.get('line')}).")
    if heuristics:
        parts.append(f"Bugfinder: {len(heuristics)} heuristic hit(s) in scope.")
    parts.append(
        f"Ironclad {ic.get('verdict', 'n/a')} sealed={ic.get('ironclad_sealed')} — corroborate before repair."
    )
    return " ".join(parts)


def ai_repair(
    *,
    source_path: Path,
    findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Ranked repair hints from bugfinder + pattern registry."""
    bf = _bugfinder_mod()
    if findings is None and bf:
        scan = bf.find_bugs(source_path, max_compares=64)
        findings = list(scan.get("heuristics") or []) + list(scan.get("bugs") or [])

    repairs: list[dict[str, Any]] = []
    for i, f in enumerate(findings or []):
        pid = f.get("pattern_id") or f.get("pattern") or "truth"
        hint = {
            "shell_true": "Replace shell=True with argv list; sanitize operator input.",
            "eval_exec": "If not interpreter driver, remove eval/exec; use ast.literal_eval.",
            "bare_except": "Catch specific exceptions; log and re-raise or handle explicitly.",
            "hardcoded_secret": "Move secret to vault/env; reference KeePass-Field or sealed config.",
            "sql_concat": "Use parameterized queries or ORM bind params.",
        }.get(pid, f.get("recommendation") or "Review against field-code-bugfinder report.")
        repairs.append({
            "id": f"REPAIR-{i + 1:03d}",
            "pattern": pid,
            "severity": f.get("severity", "medium"),
            "file": f.get("file") or f.get("path") or str(source_path),
            "line": f.get("line"),
            "hint": hint,
            "code": (f.get("text") or f.get("code") or "")[:160],
            "verify": f"pythong {INSTALL / 'lib' / 'field-code-bugfinder.py'} scan {source_path}",
        })

    return {
        "ok": True,
        "schema": "field-gdb-repair/v1",
        "updated": _now(),
        "source": str(source_path),
        "repair_count": len(repairs),
        "repairs": repairs,
        "ironclad": _ironclad_slice(),
        "motto": "Repair only after decode + bugfinder corroboration.",
    }


def panel_json() -> dict[str, Any]:
    ic = _ironclad_slice()
    doc = _load(DOCTRINE, {"schema": "field-gdb-doctrine/v1"})
    session = _load(SESSION, {})
    return {
        "schema": "field-gdb-panel/v1",
        "updated": _now(),
        "title": "Field GDB",
        "doctrine": doc,
        "gdb": _gdb_bin(),
        "objdump": _objdump_bin(),
        "platform": platform.system().lower(),
        "ironclad": ic,
        "session": session,
        "capabilities": (doc.get("capabilities") or {}),
        "commands": ["disasm", "backtrace", "decode", "repair", "highlight", "graph"],
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or body.get("cmd") or "json").strip().lower()
    if action in ("json", "panel", "status"):
        return {"ok": True, **panel_json()}

    if action == "disasm":
        path = Path(str(body.get("binary") or body.get("path") or ""))
        return disassemble(path, symbol=str(body.get("symbol") or ""), max_lines=int(body.get("max_lines") or 64))

    if action == "backtrace":
        path = Path(str(body.get("binary") or body.get("path") or ""))
        return gdb_batch(path, ["bt full", "info registers"], timeout=int(body.get("timeout") or 45))

    if action == "highlight":
        text = str(body.get("text") or body.get("line") or "")
        lang = str(body.get("lang") or "c")
        kind = str(body.get("kind") or "source")
        if kind == "asm":
            return {"ok": True, **highlight_asm_line(text)}
        return {"ok": True, **highlight_source_line(text, lang=lang)}

    if action == "graph":
        gtype = str(body.get("type") or "call_stack")
        if gtype == "register_timeline":
            return {"ok": True, **graph_register_timeline(body.get("samples") or [])}
        frames = body.get("frames") or []
        return {"ok": True, **graph_call_stack(frames)}

    if action == "decode":
        sp = body.get("source_path") or body.get("path")
        return ai_decode(
            source_path=Path(sp).expanduser() if sp else None,
            source_text=str(body.get("source_text") or body.get("text") or ""),
            stop_reason=str(body.get("stop_reason") or body.get("reason") or ""),
            frames=body.get("frames"),
        )

    if action == "repair":
        sp = body.get("source_path") or body.get("path")
        if not sp:
            return {"ok": False, "error": "missing source_path"}
        return ai_repair(source_path=Path(sp).expanduser(), findings=body.get("findings"))

    if action == "session":
        doc = {
            "updated": _now(),
            "binary": body.get("binary"),
            "pid": body.get("pid"),
            "note": body.get("note"),
        }
        _save_atomic(SESSION, doc)
        return {"ok": True, "session": doc}

    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] not in ("-", ""):
        cmd = sys.argv[1].strip().lower()
        if cmd == "json":
            print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
            return 0
        if cmd == "disasm" and len(sys.argv) > 2:
            out = disassemble(Path(sys.argv[2]))
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0 if out.get("ok") else 1
        if cmd == "decode" and len(sys.argv) > 2:
            out = ai_decode(source_path=Path(sys.argv[2]))
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0
        if cmd == "repair" and len(sys.argv) > 2:
            out = ai_repair(source_path=Path(sys.argv[2]))
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0
        if cmd == "dispatch":
            body = json.loads(sys.stdin.read() or "{}")
            out = dispatch(body)
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0 if out.get("ok", True) else 1

    print(json.dumps(dispatch({"action": "json"}), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())