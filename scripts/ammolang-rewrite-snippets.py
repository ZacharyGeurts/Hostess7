#!/usr/bin/env python3
"""Rewrite AmmoLang snippet scripts — harness, portable ROOT, no hardcoded paths."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNIPPETS = ROOT / "tests" / "ammolang" / "snippets"
HARNESS = SNIPPETS / "_harness.sh"
SKIP = frozenset({"_harness.sh"})

_BOILERPLATE_START = re.compile(
    r"^#!/bin/bash\s*$|^set -euo pipefail\s*$|^set \+o pipefail\s*$"
    r"|^ROOT=|^export NEXUS_|^mkdir -p \"?\$NEXUS_STATE_DIR\"?\s*$"
    r"|^source \"?\$ROOT/lib/|^nexus_ensure_dirs|^panel=|^sg=|^PY=|^if \[\[ \"\$\{AML_TEST_DIRECT"
    r"|^  PY=|^fi\s*$",
    re.M,
)

_HARDCODED = re.compile(r"/home/default/Desktop/SG(?:/NewLatest)?")
_LIB_SOURCE = re.compile(r'^\s*source\s+"?\$ROOT/lib/[^"]+"?\s+2>/dev/null\s+\|\|\s+true\s*$')


def _is_boiler_line(s: str) -> bool:
    t = s.strip()
    if not t:
        return True
    if t.startswith("#") and "!" in t[:2]:
        return True
    if _LIB_SOURCE.match(s) or re.search(r'source\s+"?\$\{?ROOT\}?/lib/', s):
        return True
    if t.startswith("export SG_ROOT=") or t.startswith("export NEXUS_"):
        return True
    if t == 'mkdir -p "$NEXUS_STATE_DIR"':
        return True
    if _BOILERPLATE_START.match(t):
        return True
    if t in ("PY=python3", "fi", "PY=pythong"):
        return True
    if "command -v pythong" in s or t.startswith("export AML_INLINE"):
        return True
    if t.startswith("SCRIPT_DIR=") or "source \"${SCRIPT_DIR}/_harness" in s:
        return True
    if t == "# shellcheck source=_harness.sh":
        return True
    if t.startswith("panel=") and "threat-panel" in t:
        return True
    if t.startswith('sg="') or t.startswith("sg=${"):
        return True
    if t.startswith("nexus_ensure_dirs"):
        return True
    if re.match(r"^\s*PY=", s):
        return True
    if re.match(r"^\s*if \[\[ \"\$\{AML_TEST_DIRECT", s):
        return True
    return False


def _strip_boilerplate(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        s = line.rstrip("\n")
        if _is_boiler_line(s):
            continue
        out.append(s)
    while out and not out[0].strip():
        out.pop(0)
    return out


def _rewrite_body(lines: list[str]) -> list[str]:
    body = _strip_boilerplate(lines)
    rewritten: list[str] = []
    for line in body:
        s = _HARDCODED.sub("${ROOT}", line)
        s = s.replace('"$ROOT/lib/', '"${ROOT}/lib/')
        s = s.replace("${ROOT}/NewLatest/", "${ROOT}/")
        # Prefer aml_py for simple lib/*.py invocations
        m = re.match(
            r'^(\s*)(?:"?\$PY"?\s+|python3\s+|pythong\s+)"?\$\{ROOT\}/lib/([^"]+\.py)"?\s+(.*)$',
            s,
        )
        if m:
            indent, mod, args = m.group(1), m.group(2), m.group(3)
            rewritten.append(f'{indent}aml_py "{mod}" {args}')
            continue
        rewritten.append(s)
    return rewritten


def rewrite_file(path: Path, *, dry_run: bool = False) -> bool:
    if path.name in SKIP:
        return False
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    body = _rewrite_body(lines)
    new_lines = [
        "#!/bin/bash",
        "set -euo pipefail",
        "set +o pipefail",
        'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
        '# shellcheck source=_harness.sh',
        'source "${SCRIPT_DIR}/_harness.sh"',
        "",
        *body,
        "",
    ]
    new_text = "\n".join(new_lines)
    if new_text == text:
        return False
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
        path.chmod(0o755)
    return True


def main() -> int:
    dry = "--dry-run" in sys.argv
    changed = 0
    for path in sorted(SNIPPETS.glob("*.sh")):
        if rewrite_file(path, dry_run=dry):
            changed += 1
            print(path.name)
    print(f"rewrote {changed} snippets" + (" (dry-run)" if dry else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())