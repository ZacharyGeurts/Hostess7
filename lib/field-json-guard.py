#!/usr/bin/env python3
"""JSON guard — extract valid JSON from script stdout (fixes line-1-char-1 parse failures)."""
from __future__ import annotations

import json
from typing import Any


def parse_stdout_json(stdout: str | None, *, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """Best-effort JSON from subprocess stdout — never raises JSONDecodeError."""
    fallback = default if default is not None else {"ok": False, "error": "empty_stdout"}
    text = (stdout or "").strip()
    if not text:
        return dict(fallback)
    try:
        doc = json.loads(text)
        return doc if isinstance(doc, dict) else {"ok": True, "data": doc}
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line or line[0] not in "{[":
            continue
        try:
            doc = json.loads(line)
            return doc if isinstance(doc, dict) else {"ok": True, "data": doc}
        except json.JSONDecodeError:
            continue
    idx = text.find("{")
    if idx < 0:
        idx = text.find("[")
    if idx >= 0:
        try:
            doc = json.loads(text[idx:])
            return doc if isinstance(doc, dict) else {"ok": True, "data": doc}
        except json.JSONDecodeError:
            pass
    out = dict(fallback)
    out["error"] = out.get("error") or "bad_json"
    out["detail"] = text[:240]
    return out


def safe_json_response(
    stdout: str | None,
    stderr: str | None = None,
    *,
    rc: int | None = None,
    script: str = "",
) -> dict[str, Any]:
    """Normalize subprocess result into API-safe JSON payload."""
    doc = parse_stdout_json(stdout)
    if rc is not None and rc != 0 and doc.get("ok") is not False:
        doc["ok"] = False
        doc.setdefault("error", "nonzero_exit")
        doc["rc"] = rc
    if stderr and not doc.get("detail") and doc.get("error") in ("bad_json", "empty_stdout", "script_failed"):
        doc["detail"] = stderr.strip()[:240]
    if script:
        doc.setdefault("script", script)
    return doc


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("status", "json", "panel"):
        print(json.dumps({"ok": True, "schema": "field-json-guard/v1", "module": "lib/field-json-guard.py"}, ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.argv[2] if len(sys.argv) >= 3 else (sys.stdin.read() or "{}")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        if str(body.get("action") or "") == "parse":
            print(json.dumps(parse_stdout_json(body.get("stdout")), ensure_ascii=False))
            return 0
    print(json.dumps({"ok": False, "error": "usage"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())