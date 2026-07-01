#!/usr/bin/env pythong
"""Compile autocorrect — parse diagnostics, apply only confidence-1.0 fixes, alert layout."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(__file__).resolve().parents[1]
DOCTRINE = INSTALL / "data" / "field-compile-autocorrect-doctrine.json"
EXPLANATIONS = INSTALL / "data" / "compile-error-human-explanations.json"
CHIPS_CORE = INSTALL / "field-chips-core.json"
SCHEMA = "field-compile-autocorrect/v1"

_GCC_LINE = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+):\s*(?P<sev>error|warning|note):\s*(?P<msg>.*)$"
)
_PY_LINE = re.compile(
    r'^\s*File "(?P<file>[^"]+)", line (?P<line>\d+).*\n\s*(?P<kind>SyntaxError|IndentationError): (?P<msg>.*)$',
    re.MULTILINE,
)
_PY_SIMPLE = re.compile(
    r"line (?P<line>\d+).*(SyntaxError|IndentationError):\s*(?P<msg>.*)"
)


class Diagnostic:
    __slots__ = ("file", "line", "column", "severity", "message")

    def __init__(self, file: str, line: int, column: int, severity: str, message: str) -> None:
        self.file = file
        self.line = line
        self.column = column
        self.severity = severity
        self.message = message


def _load_doctrine() -> dict[str, Any]:
    try:
        return json.loads(DOCTRINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"policy": {"min_confidence_to_apply": 1.0, "max_rounds": 3}}


def _load_explanations() -> dict[str, Any]:
    try:
        return json.loads(EXPLANATIONS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"patterns": [], "fallback": {}, "emulator_series": {}}


def resolve_platform(lang: str = "", profile: str = "", *, content: str = "") -> str:
    """Best-effort retro/modern platform tag for hints and safe-fix guards."""
    lang_l = (lang or "").lower()
    prof = (profile or "").lower()
    blob = f"{prof} {content[:400].lower()}"
    if "amiga" in prof or "amiga" in blob or lang_l in ("amos", "blitzbasic", "blitz"):
        if lang_l in ("asm", "s", "m68k") or re.search(r"^\s*\w+:\s*$", content, re.MULTILINE):
            return "amiga_68000"
        return "amiga"
    if lang_l in ("asm", "s", "m68k"):
        return "m68k"
    if "c64" in prof or "6510" in prof:
        return "c64_6510"
    if lang_l in ("basic", "qbasic", "gwbasic"):
        return "basic"
    if lang_l in ("pascal", "delphi"):
        return "pascal"
    if lang_l in ("vb", "vb6", "vba"):
        return "vb"
    if lang_l in ("fortran", "f90", "f95"):
        return "fortran"
    return "generic"


def _match_pattern(message: str, patterns: list[dict[str, Any]]) -> dict[str, Any] | None:
    msg = message.lower()
    for row in patterns:
        for needle in row.get("match") or []:
            if str(needle).lower() in msg:
                return row
    return None


def _hint_for(entry: dict[str, Any], *, lang: str, platform: str) -> str:
    hints = entry.get("hints") or {}
    for key in (platform, lang, "generic"):
        if key and hints.get(key):
            return str(hints[key])
    return ""


def human_explanation_for_diagnostic(
    diag: dict[str, Any],
    *,
    lang: str = "",
    platform: str = "",
) -> dict[str, Any]:
    """Plain-language explanation + per-language/platform hints for one diagnostic."""
    exp = _load_explanations()
    patterns = exp.get("patterns") or []
    fallback = exp.get("fallback") or {}
    message = str(diag.get("message") or "")
    matched = _match_pattern(message, patterns) or fallback
    hint = _hint_for(matched, lang=lang, platform=platform)
    if not hint and matched is not fallback:
        hint = _hint_for(fallback, lang=lang, platform=platform)
    return {
        "pattern_id": matched.get("id") if isinstance(matched, dict) else "fallback",
        "explanation": str(matched.get("explanation") or fallback.get("explanation") or ""),
        "hint": hint,
        "lang": lang,
        "platform": platform,
    }


def build_human_explanation_section(
    errors: list[dict[str, Any]],
    *,
    lang: str = "",
    platform: str = "",
) -> dict[str, Any]:
    entries = []
    for d in errors:
        human = human_explanation_for_diagnostic(d, lang=lang, platform=platform)
        entries.append({
            "line": d.get("line"),
            "column": d.get("column"),
            "file": d.get("file"),
            "message": d.get("message"),
            **human,
        })
    return {
        "title": "Human Explanation",
        "count": len(entries),
        "lang": lang,
        "platform": platform,
        "entries": entries,
    }


def _collect_errors(store: list[dict[str, Any]], seen: set[str], diags: list[dict[str, Any]]) -> None:
    for d in diags:
        if str(d.get("severity")) != "error":
            continue
        key = f"{d.get('file','')}:{d.get('line','')}:{d.get('message','')}"
        if key in seen:
            continue
        seen.add(key)
        store.append(dict(d))


def _is_fix_allowed(fix_id: str, *, lang: str, platform: str) -> bool:
    exp = _load_explanations()
    policy = exp.get("retro_safe_fix_policy") or {}
    lang_l = (lang or "").lower()
    for blocked in (policy.get("never_auto_apply") or {}).get(lang_l) or []:
        if blocked == fix_id:
            return False
    for blocked in (policy.get("platform_never_auto_apply") or {}).get(platform) or []:
        if blocked == fix_id:
            return False
    if fix_id == "missing_semicolon" and lang_l in ("asm", "s", "m68k", "amos", "blitzbasic", "basic", "qbasic"):
        return False
    if fix_id == "missing_semicolon" and platform in ("amiga_68000", "m68k", "c64_6510"):
        return False
    if fix_id in ("missing_colon", "is_none_identity") and lang_l != "python":
        return False
    return True


def emulator_series_readiness() -> dict[str, Any]:
    """Report retro emulator/chip series status — Amiga and peers."""
    exp = _load_explanations()
    series = dict(exp.get("emulator_series") or {})
    chips_ok = False
    chip_families: dict[str, int] = {}
    try:
        core = json.loads(CHIPS_CORE.read_text(encoding="utf-8"))
        chip_families = (core.get("counts") or {}).get("by_family") or {}
        chips_ok = bool(core.get("ok"))
    except (OSError, json.JSONDecodeError):
        pass
    rows = []
    all_ready = True
    for family_id, meta in series.items():
        if not isinstance(meta, dict):
            continue
        expected = int(meta.get("chip_count") or 0)
        live = int(chip_families.get(family_id) or 0)
        ready = bool(meta.get("ready")) and (not expected or live >= expected)
        if not ready:
            all_ready = False
        rows.append({
            "family": family_id,
            "ready": ready,
            "chip_count_expected": expected,
            "chip_count_live": live,
            **{k: v for k, v in meta.items() if k not in ("ready", "chip_count")},
        })
    return {
        "schema": "field-emulator-series-readiness/v1",
        "ok": chips_ok and all_ready,
        "chips_core_ok": chips_ok,
        "all_series_ready": all_ready,
        "amiga_ready": bool((series.get("retro_amiga") or {}).get("ready")),
        "series": rows,
    }


def parse_diagnostics(stderr: str, *, lang: str = "") -> list[dict[str, Any]]:
    """Normalize compiler stderr into structured diagnostics."""
    rows: list[dict[str, Any]] = []
    if not stderr:
        return rows
    for line in stderr.splitlines():
        m = _GCC_LINE.match(line.strip())
        if m:
            rows.append({
                "file": m.group("file"),
                "line": int(m.group("line")),
                "column": int(m.group("col")),
                "severity": m.group("sev"),
                "message": m.group("msg"),
            })
            continue
        if lang == "python" or "SyntaxError" in line or "IndentationError" in line:
            m2 = _PY_SIMPLE.search(line)
            if m2:
                rows.append({
                    "file": "<stdin>",
                    "line": int(m2.group("line")),
                    "column": 0,
                    "severity": "error",
                    "message": f"{m2.group(2)}: {m2.group('msg')}",
                })
    for m in _PY_LINE.finditer(stderr):
        rows.append({
            "file": m.group("file"),
            "line": int(m.group("line")),
            "column": 0,
            "severity": "error",
            "message": f"{m.group('kind')}: {m.group('msg')}",
        })
    return rows


def _line_text(lines: list[str], line_no: int) -> str:
    idx = max(0, line_no - 1)
    if idx >= len(lines):
        return ""
    return lines[idx].rstrip("\n\r")


def _set_line(lines: list[str], line_no: int, text: str) -> list[str]:
    idx = max(0, line_no - 1)
    while len(lines) <= idx:
        lines.append("\n")
    suffix = "\n" if lines[idx].endswith("\n") else ""
    lines[idx] = text + suffix
    return lines


def _try_semicolon_fix(lines: list[str], diag: Diagnostic) -> dict[str, Any] | None:
    msg = diag.message.lower()
    if "expected ';'" not in msg and "expected \";\"" not in msg:
        return None
    raw = _line_text(lines, diag.line)
    if not raw.strip() or raw.rstrip().endswith(";"):
        return None
    if raw.rstrip().endswith("{") or raw.rstrip().endswith("}"):
        return None
    return {
        "id": "missing_semicolon",
        "confidence": 1.0,
        "line": diag.line,
        "before": raw,
        "after": raw.rstrip() + ";",
        "reason": "Compiler expected ';' — append only when line lacks terminator.",
    }


def _try_python_colon_fix(lines: list[str], diag: Diagnostic) -> dict[str, Any] | None:
    msg = diag.message.lower()
    if "expected ':'" not in msg and "expected :" not in msg:
        return None
    raw = _line_text(lines, diag.line)
    if not raw.strip() or raw.rstrip().endswith(":"):
        return None
    if not re.match(r"^\s*(def|class|if|elif|else|for|while|try|except|finally|with|match|case)\b", raw):
        return None
    if "#" in raw and raw.index("#") < len(raw.rstrip()) - 1:
        return None
    return {
        "id": "missing_colon",
        "confidence": 1.0,
        "line": diag.line,
        "before": raw,
        "after": raw.rstrip() + ":",
        "reason": "Python block header missing ':' — statement keyword present.",
    }


def _try_is_none_fix(lines: list[str], diag: Diagnostic) -> dict[str, Any] | None:
    raw = _line_text(lines, diag.line)
    if "== None" not in raw and "!= None" not in raw:
        return None
    after = raw.replace("== None", "is None").replace("!= None", "is not None")
    if after == raw:
        return None
    return {
        "id": "is_none_identity",
        "confidence": 1.0,
        "line": diag.line,
        "before": raw,
        "after": after,
        "reason": "Replace == None with is None — PEP 8 identity compare.",
    }


def propose_fixes(
    content: str,
    diagnostics: list[dict[str, Any]],
    *,
    lang: str = "",
    platform: str = "",
) -> list[dict[str, Any]]:
    """Return safe fix proposals — confidence 1.0 only; retro platforms guarded."""
    lines = content.splitlines(keepends=True)
    if not lines and content:
        lines = [content]
    platform = platform or resolve_platform(lang, content=content)
    proposals: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in diagnostics:
        if str(row.get("severity")) != "error":
            continue
        diag = Diagnostic(
            file=str(row.get("file") or ""),
            line=int(row.get("line") or 1),
            column=int(row.get("column") or 0),
            severity=str(row.get("severity") or "error"),
            message=str(row.get("message") or ""),
        )
        for candidate in (
            _try_semicolon_fix(lines, diag),
            _try_python_colon_fix(lines, diag) if lang == "python" else None,
            _try_is_none_fix(lines, diag) if lang == "python" else None,
        ):
            if not candidate:
                continue
            fix_id = str(candidate.get("id") or "")
            if not _is_fix_allowed(fix_id, lang=lang, platform=platform):
                continue
            key = f"{candidate['id']}:{candidate['line']}:{candidate['before']}"
            if key in seen:
                continue
            seen.add(key)
            candidate["platform"] = platform
            proposals.append(candidate)
    return proposals


def apply_fix(content: str, fix: dict[str, Any]) -> str:
    lines = content.splitlines(keepends=True)
    if not lines and content:
        lines = [content]
    line_no = int(fix.get("line") or 1)
    _set_line(lines, line_no, str(fix.get("after") or ""))
    return "".join(lines)


def compile_with_autocorrect(
    compile_once: Callable[[str], dict[str, Any]],
    content: str,
    *,
    lang: str = "",
    platform: str = "",
    profile: str = "",
    max_rounds: int | None = None,
) -> dict[str, Any]:
    """Run compile; on failure apply verified safe fixes and retry. Never guess."""
    policy = _load_doctrine().get("policy") or {}
    rounds = int(max_rounds if max_rounds is not None else policy.get("max_rounds") or 3)
    min_conf = float(policy.get("min_confidence_to_apply") or 1.0)
    platform = platform or resolve_platform(lang, profile=profile, content=content)
    current = content
    applied_all: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    all_errors: list[dict[str, Any]] = []
    all_errors_seen: set[str] = set()

    for attempt in range(rounds + 1):
        result = compile_once(current)
        diags = result.get("diagnostics")
        if not diags:
            stderr = str(result.get("stderr") or result.get("detail") or result.get("stderr_tail") or "")
            diags = parse_diagnostics(stderr, lang=lang)
        _collect_errors(all_errors, all_errors_seen, diags)
        attempts.append({
            "attempt": attempt,
            "ok": bool(result.get("ok")),
            "error_count": len([d for d in diags if d.get("severity") == "error"]),
        })
        if result.get("ok"):
            layout = build_alert_layout(
                ok=True,
                lang=lang,
                platform=platform,
                diagnostics=diags,
                all_errors=all_errors,
                applied=applied_all,
                attempts=attempts,
                compile_result=result,
            )
            return {
                "schema": SCHEMA,
                "ok": True,
                "compiled": bool(result.get("compiled", True)),
                "content": current,
                "content_changed": current != content,
                "applied_fixes": applied_all,
                "attempts": attempts,
                "alerts": layout,
                "platform": platform,
                "emulator_series": emulator_series_readiness(),
                "continued": True,
                **{k: v for k, v in result.items() if k not in ("ok",)},
            }
        proposals = [
            p for p in propose_fixes(current, diags, lang=lang, platform=platform)
            if float(p.get("confidence") or 0) >= min_conf
        ]
        if not proposals or attempt >= rounds:
            layout = build_alert_layout(
                ok=False,
                lang=lang,
                platform=platform,
                diagnostics=diags,
                all_errors=all_errors,
                applied=applied_all,
                attempts=attempts,
                compile_result=result,
                remaining=proposals,
            )
            return {
                "schema": SCHEMA,
                "ok": False,
                "compiled": False,
                "continued": True,
                "content": current,
                "content_changed": current != content,
                "applied_fixes": applied_all,
                "unfixed_proposals": proposals,
                "attempts": attempts,
                "alerts": layout,
                "diagnostics": diags,
                "all_errors": all_errors,
                "platform": platform,
                "emulator_series": emulator_series_readiness(),
                "message": "Compile failed — safe autocorrect exhausted or no certain fix.",
                **{k: v for k, v in result.items() if k not in ("ok",)},
            }
        fix = proposals[0]
        trial = apply_fix(current, fix)
        verify = compile_once(trial)
        before_err = attempts[-1]["error_count"]
        verify_diags = verify.get("diagnostics") or parse_diagnostics(
            str(verify.get("stderr") or verify.get("detail") or verify.get("stderr_tail") or ""),
            lang=lang,
        )
        _collect_errors(all_errors, all_errors_seen, verify_diags)
        after_err = len([d for d in verify_diags if d.get("severity") == "error"])
        if verify.get("ok") or after_err < before_err:
            fix["verified"] = True
            fix["error_count_before"] = before_err
            fix["error_count_after"] = after_err
            applied_all.append(fix)
            current = trial
            continue
        fix["verified"] = False
        fix["rejected"] = True
        fix["reason_rejected"] = "Re-compile did not improve — fix not applied."
        layout = build_alert_layout(
            ok=False,
            lang=lang,
            platform=platform,
            diagnostics=diags,
            all_errors=all_errors,
            applied=applied_all,
            attempts=attempts,
            compile_result=result,
            rejected=[fix],
        )
        return {
            "schema": SCHEMA,
            "ok": False,
            "compiled": False,
            "continued": True,
            "content": current,
            "applied_fixes": applied_all,
            "rejected_fix": fix,
            "attempts": attempts,
            "alerts": layout,
            "diagnostics": diags,
            "all_errors": all_errors,
            "platform": platform,
            "emulator_series": emulator_series_readiness(),
            "message": "Uncertain fix rejected — not correcting without proof.",
            **{k: v for k, v in result.items() if k not in ("ok",)},
        }


def build_alert_layout(
    *,
    ok: bool,
    lang: str,
    diagnostics: list[dict[str, Any]],
    applied: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    compile_result: dict[str, Any],
    all_errors: list[dict[str, Any]] | None = None,
    platform: str = "",
    remaining: list[dict[str, Any]] | None = None,
    rejected: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    errors = [d for d in diagnostics if d.get("severity") == "error"]
    collected = all_errors if all_errors is not None else errors
    platform = platform or resolve_platform(lang)
    warnings = [d for d in diagnostics if d.get("severity") == "warning"]
    suggestions: list[dict[str, Any]] = []
    for d in collected:
        msg = str(d.get("message") or "").lower()
        if "implicit declaration" in msg or "undeclared" in msg:
            suggestions.append({
                "line": d.get("line"),
                "severity": "suggestion",
                "message": "Add missing #include or forward declaration — not auto-applied.",
            })
        if "undefined reference" in msg:
            suggestions.append({
                "line": d.get("line"),
                "severity": "suggestion",
                "message": "Linker symbol missing — add source or -l flag; not auto-applied.",
            })
    human = build_human_explanation_section(collected, lang=lang, platform=platform)
    emu = emulator_series_readiness()
    total_err = len(collected)
    summary = (
        f"Compile OK · {len(applied)} autocorrect(s)"
        if ok
        else f"Compile failed · {total_err} error(s) collected · {len(applied)} fix(es) applied"
    )
    cards = []
    for fix in applied:
        cards.append({
            "kind": "fixed",
            "line": fix.get("line"),
            "title": fix.get("id"),
            "detail": fix.get("reason"),
            "before": fix.get("before"),
            "after": fix.get("after"),
        })
    for d in errors:
        cards.append({
            "kind": "error",
            "line": d.get("line"),
            "column": d.get("column"),
            "title": "error",
            "detail": d.get("message"),
        })
    for d in warnings:
        cards.append({
            "kind": "warning",
            "line": d.get("line"),
            "title": "warning",
            "detail": d.get("message"),
        })
    for r in (rejected or []):
        cards.append({
            "kind": "rejected",
            "line": r.get("line"),
            "title": r.get("id"),
            "detail": r.get("reason_rejected") or "Fix rejected — not certain.",
        })
    return {
        "schema": "field-compile-alerts/v1",
        "ok": ok,
        "lang": lang,
        "platform": platform,
        "summary": summary,
        "compiler": compile_result.get("compiler") or compile_result.get("profile"),
        "compile_ms": compile_result.get("compile_ms"),
        "sections": {
            "summary": {"text": summary, "attempts": attempts},
            "applied_fixes": applied,
            "remaining_errors": collected,
            "warnings": warnings,
            "suggestions": suggestions,
            "unfixed_proposals": remaining or [],
            "human_explanation": human,
            "emulator_series": emu,
        },
        "human_explanation": human,
        "emulator_series": emu,
        "cards": cards,
    }


def main() -> int:
    import sys

    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(json.dumps({
            "usage": "parse|propose|layout|explain|emulator-series|json",
            "schema": SCHEMA,
        }, indent=2))
        return 0
    cmd = args[0]
    if cmd == "parse":
        stderr = sys.stdin.read()
        lang = args[1] if len(args) > 1 else ""
        print(json.dumps(parse_diagnostics(stderr, lang=lang), indent=2))
        return 0
    if cmd == "explain":
        stderr = sys.stdin.read()
        lang = args[1] if len(args) > 1 else ""
        platform = args[2] if len(args) > 2 else ""
        diags = [d for d in parse_diagnostics(stderr, lang=lang) if d.get("severity") == "error"]
        print(json.dumps(build_human_explanation_section(
            diags, lang=lang, platform=platform or resolve_platform(lang),
        ), indent=2))
        return 0
    if cmd == "emulator-series":
        print(json.dumps(emulator_series_readiness(), indent=2))
        return 0
    if cmd == "json":
        print(json.dumps(_load_doctrine(), indent=2))
        return 0
    print(json.dumps({"ok": False, "error": f"unknown:{cmd}"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())