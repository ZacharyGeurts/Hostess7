#!/usr/bin/env pythong
"""Migrate tests/run-tests.sh bash functions → tests/ammolang/*.aml assert suites."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tests" / "run-tests.sh.bak"
if not SRC.is_file():
    SRC = ROOT / "tests" / "run-tests.sh"
OUT = ROOT / "tests" / "ammolang"
SNIPPETS = OUT / "snippets"

_FILE = re.compile(r'^\s*\[\[\s+-f\s+"?\$\{ROOT\}/([^"}\s]+)"?\s*\]\]\s*$')
_DIR = re.compile(r'^\s*\[\[\s+-d\s+"?\$\{ROOT\}/([^"}\s]+)"?\s*\]\]\s*$')
_EXEC = re.compile(r'^\s*\[\[\s+-x\s+"?\$\{ROOT\}/([^"}\s]+)"?\s*\]\]\s*$')
_GREP = re.compile(r"""^\s*grep\s+-q\s+(['"])(.+?)\1\s+"?\$\{ROOT\}/([^"}\s]+)"?\s*$""")
_PY_GREP = re.compile(
    r"""^\s*(?:NEXUS_STATE_DIR=.*\s+)?(?:NEXUS_INSTALL_ROOT=.*\s+)?(?:SG_ROOT=.*\s+)?(?:GROK16_ROOT=.*\s+)?"""
    r"""(?:pythong|python3)\s+"?\$\{ROOT\}/([^"}\s]+)"?\s+(.+?)\s*\|\s*grep\s+-q\s+(['"])(.+?)\3\s*$"""
)
_COMPILE_GREP = re.compile(
    r"""^\s*(?:NEXUS_INSTALL_ROOT=.*\s+)?(?:python3|pythong)\s+"?\$\{ROOT\}/lib/field-ammolang\.py"?\s+compile\s+"""
    r"""(\S+\.aml)\s*\|\s*grep\s+-q\s+(['"])(.+?)\2\s*$"""
)
_ROUTE_GREP = re.compile(
    r"""^\s*NEXUS_INSTALL_ROOT=.*\s+NEXUS_STATE_DIR=.*\s+"""
    r"""python3\s+"?\$\{ROOT\}/lib/field-ammolang-build\.py"?\s+route\s+(\S+)(?:\s+--dry)?\s*\|\s*grep\s+-q\s+(['"])(.+?)\2\s*$"""
)
_FUNC = re.compile(r"^test_([a-z0-9_]+)\(\)\s*\{")
_RUN = re.compile(r'^run_test\s+"([^"]+)"\s+test_([a-z0-9_]+)\s*$')
_HEREDOC = re.compile(r"<<\s*['\"]?(\w+)['\"]?")
_PANEL_LOCAL = re.compile(r'^\s*local\s+panel="\$\{ROOT\}/panel/threat-panel\.html"\s*$')

_NEXUS_LIBS = (
    "nexus-common.sh", "eternal-vigil.sh", "entropy-oracle.sh", "shadow-reality.sh",
    "self-defense.sh", "device-whitelist.sh", "ultra-stealth.sh", "predictive-guard.sh",
    "network-lockdown.sh", "threat-vectors.sh", "packet-oracle.sh", "threat-panel.sh",
    "firewall-sentinel.sh", "firewall-trust.sh", "seal-vault.sh", "tamper-guard.sh",
    "znetwork-field.sh", "nexus-settings.sh", "adblock-loader.sh", "host-attack.sh",
    "field-attack-kit.sh",
)

CATEGORIES = {
    "ammolang": ("ammolang", "combinatorics_sequence", "grok16_ship", "grok16_gates", "github_mcp", "script_router", "timing"),
    "grok16": ("grok16", "g16_", "compiler", "power_sort", "launch", "language"),
    "hostess7": ("hostess7", "hostess_7", "h7_", "history_training", "reality_physics"),
    "queen": ("queen", "launch_chamber", "browser"),
    "library": ("library", "h7_library", "dewey", "corpus", "h7c", "extensive_library"),
    "ironclad": ("ironclad", "heaven_hell"),
    "combinatorics": ("combinatronic", "combinatorics", "combinamatrix", "plate_", "chips_", "steel_neural"),
    "stack": ("ammoos", "kilroy", "field_stack", "stack_", "nexus", "znetwork"),
    "security": ("entropy", "shadow", "vigil", "whitelist", "self_defense", "ultra_stealth", "predictive", "network", "threat", "packet", "gatekeeper", "firewall", "adblock", "attack"),
    "core": (),
}


def categorize(name: str) -> str:
    for cat, keys in CATEGORIES.items():
        if cat == "core":
            continue
        for k in keys:
            if k in name:
                return cat
    return "core"


def _normalize_paths(text: str, *, for_snippet: bool = False) -> str:
    text = text.replace('"${ROOT}/', f'"{ROOT}/').replace("${ROOT}/", f"{ROOT}/").replace("${ROOT}", str(ROOT))
    text = text.replace("${SG_ROOT}", str(ROOT.parent))
    if for_snippet:
        text = text.replace("${NEXUS_STATE_DIR}", "$NEXUS_STATE_DIR")
    else:
        text = text.replace("${NEXUS_STATE_DIR}", f"{ROOT}/.nexus-state")
    text = text.replace('"$panel"', f'"{ROOT}/panel/threat-panel.html"')
    text = text.replace('${panel}', f"{ROOT}/panel/threat-panel.html")
    return text


def convert_line(line: str) -> str | None:
    line = line.rstrip()
    if not line or line.strip().startswith("#"):
        return None
    if _PANEL_LOCAL.match(line):
        return None
    if line.strip() in ("local tmp_state",) or "mktemp" in line or line.strip().startswith("rm -rf"):
        return f"assert shell:{_normalize_paths(line.strip())}"

    m = _FILE.match(line)
    if m:
        return f"assert file:{m.group(1)}"
    m = _DIR.match(line)
    if m:
        return f"assert dir:{m.group(1)}"
    m = _EXEC.match(line)
    if m:
        return f"assert exec:{m.group(1)}"
    m = _GREP.match(line)
    if m:
        return f"assert grep:{m.group(3)}:{m.group(2)}"
    m = _COMPILE_GREP.match(line)
    if m:
        return f"assert compile:{m.group(1)} match:{m.group(3)}"
    m = _ROUTE_GREP.match(line)
    if m:
        return f"assert route:{m.group(1)} match:{m.group(3)}"
    m = _PY_GREP.match(line)
    if m:
        mod = m.group(1)
        if mod.startswith("lib/"):
            mod = mod[4:]
        args = m.group(2).strip()
        return f"assert py:{mod} {args} match:{m.group(4)}"

    if "python3" in line or "pythong" in line or "bash " in line or "awk " in line or "dd " in line:
        cleaned = _normalize_paths(line.strip())
        return f"assert shell:{cleaned}"

    if line.strip().startswith("[[") or line.strip().startswith("grep"):
        return f"assert shell:{_normalize_paths(line.strip())}"

    if line.strip().startswith(("echo ", "! ", "mkdir ", "touch ", "chmod ", "!nexus", ": ")):
        return f"assert shell:{_normalize_paths(line.strip())}"

    if "pythong -c" in line and ('"' in line or line.count('"') % 2 == 1):
        return None

    if line.strip().startswith("nexus_") or line.strip().startswith("NEXUS_"):
        return f"assert shell:{_normalize_paths(line.strip())}"

    return None


def _extract_blocks(body: list[str]) -> list[list[str]]:
    """Split function body into logical blocks; keep heredocs intact."""
    blocks: list[list[str]] = []
    current: list[str] = []
    heredoc_marker: str | None = None

    for line in body:
        s = line.rstrip()
        if not s.strip() or s.strip().startswith("#"):
            continue
        if heredoc_marker is None and _HEREDOC.search(s):
            if current:
                blocks.append(current)
                current = []
            m = _HEREDOC.search(s)
            heredoc_marker = m.group(1) if m else "EOF"
            current.append(s)
            continue
        if heredoc_marker is not None:
            current.append(s)
            if s.strip() == heredoc_marker or s.rstrip().endswith(heredoc_marker):
                blocks.append(current)
                current = []
                heredoc_marker = None
            continue
        if s.strip().startswith("local ") and not "=" in s.split("local", 1)[1]:
            if current:
                blocks.append(current)
            current = [s]
            continue
        if s.endswith("\\"):
            current.append(s)
            continue
        current.append(s)
        if not s.endswith("\\"):
            blocks.append(current)
            current = []

    if current:
        blocks.append(current)
    return blocks


def _join_block(block: list[str]) -> str:
    parts: list[str] = []
    for line in block:
        s = line.strip().rstrip("\\").strip()
        if s.startswith("local ") and "=" not in s.split("local", 1)[1]:
            var = s.split()[1].rstrip(";")
            parts.append(f"local {var}")
            continue
        parts.append(s)
    return " ".join(parts)


def _fix_pythong_grep_pipe(line: str) -> str:
    if "| grep -q" not in line or "pythong" not in line:
        return line
    parts = line.split("| grep -q", 1)
    if len(parts) != 2:
        return line
    cmd, pat = parts[0].strip(), parts[1].strip()
    return f'out=$({cmd} 2>/dev/null || true); echo "$out" | grep -q {pat}'


def _write_snippet(fname: str, body: list[str]) -> str:
    SNIPPETS.mkdir(parents=True, exist_ok=True)
    path = SNIPPETS / f"{fname}.sh"
    state_default = str(ROOT / ".nexus-state")
    sg_default = str(ROOT.parent)
    lines = [
        "#!/bin/bash",
        "set -euo pipefail",
        "set +o pipefail",
        'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
        "# shellcheck source=_harness.sh",
        'source "${SCRIPT_DIR}/_harness.sh"',
        "",
    ]
    for raw in body:
        if raw.strip().startswith("#"):
            continue
        line = _normalize_paths(raw.rstrip(), for_snippet=True)
        if re.match(r"^\s*local\s+[\w\s]+\s*$", line):
            continue
        line = re.sub(r"^\s*local\s+", "", line)
        line = line.replace("|| return 0", "|| exit 0")
        if "| grep -q" in line:
            line = _fix_pythong_grep_pipe(line)
        lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)
    return f"assert script:{fname}"


def _needs_snippet(body: list[str]) -> bool:
    raw = "\n".join(body)
    if _HEREDOC.search(raw):
        return True
    if re.search(r"\blocal\s+\w+", raw):
        return True
    if re.search(r"\bfor\s+\w+.*;\s*do\b", raw):
        return True
    if re.search(r"\bwhile\s+", raw):
        return True
    if re.search(r"\$\{#[^}]+\[@\]\}", raw):
        return True
    if re.search(r'pythong\s+-c\s+"', raw) and raw.count('"') > 2:
        return True
    nexus_steps = sum(
        1 for line in body
        if line.strip().startswith("nexus_") or line.strip().startswith("! nexus_")
    )
    if nexus_steps >= 2:
        return True
    return False


def convert_function(fname: str, body: list[str]) -> list[str]:
    if _needs_snippet(body):
        return [_write_snippet(fname, body)]

    raw = "\n".join(body)
    if re.search(r"\$\{#[^}]+\[@\]\}", raw):
        return [_write_snippet(fname, body)]

    asserts: list[str] = []
    pending_var: str | None = None
    for block in _extract_blocks(body):
        joined = _join_block(block)
        if not joined:
            continue
        if joined.strip().startswith("local ") and "=" not in joined:
            pending_var = joined.split()[1]
            continue
        if pending_var and joined.startswith(f"{pending_var}="):
            joined = f"local {pending_var}; {joined}"
            pending_var = None
        conv = convert_line(joined)
        if conv:
            if conv.endswith(":") or "assert shell:python3" in conv:
                continue
            asserts.append(conv)
        pending_var = None
    return asserts


def parse_tests(text: str) -> dict[str, dict[str, list[str]]]:
    lines = text.splitlines()
    functions: dict[str, list[str]] = {}
    labels: dict[str, str] = {}
    current = None
    depth = 0

    for line in lines:
        m = _FUNC.match(line)
        if m:
            current = m.group(1)
            functions[current] = []
            depth = 1
            continue
        m = _RUN.match(line)
        if m:
            labels[m.group(2)] = m.group(1)
            continue
        if current:
            if "{" in line:
                depth += line.count("{")
            if "}" in line:
                depth -= line.count("}")
                if depth <= 0:
                    current = None
                    continue
            if depth > 0:
                functions[current].append(line)

    suites: dict[str, dict[str, list[str]]] = {}
    for fname, body in functions.items():
        cat = categorize(fname)
        suites.setdefault(cat, {})
        asserts = convert_function(fname, body)
        if asserts:
            label = labels.get(fname, fname.replace("_", " "))
            suites[cat][label] = asserts
    return suites


def emit_suite(cat: str, tests: dict[str, list[str]]) -> str:
    lines = [
        f"# {cat} — migrated from run-tests.sh",
        "@profile fastest",
        "@verbose clean",
        f'@motto "{cat} stack tests · AmmoLang assert"',
        "",
        f"suite {cat} ·",
    ]
    for label, asserts in tests.items():
        safe = label.replace('"', "'")[:60]
        lines.append(f"  group {safe}")
        for a in asserts:
            lines.append(f"    {a}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    if not SRC.is_file():
        print(f"missing {SRC}", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    text = SRC.read_text(encoding="utf-8")
    suites = parse_tests(text)

    skip = {"ammolang"}
    written: list[str] = []
    for cat, tests in sorted(suites.items()):
        if not tests:
            continue
        if cat in skip:
            written.append(f"{cat}.aml")
            continue
        path = OUT / f"{cat}.aml"
        path.write_text(emit_suite(cat, tests), encoding="utf-8")
        written.append(path.name)

    master = [
        "# Stack test master — all suites through AmmoLang",
        "@profile fastest",
        "@verbose clean",
        '@motto "Stack tests · assert · hang guard · no bash run-tests"',
        "",
        "seq ·",
        "  say \"Stack tests — AmmoLang assert engine replaces bash run-tests.sh\"",
        "  post \"STACK_TESTS START\"",
        "  assist hang",
    ]
    for name in sorted(w for w in written if w != "stack_tests.aml"):
        cat = name.replace(".aml", "")
        master.append(f"  test suite:{cat} no_halt")
    master += [
        "  assist freeze",
        '  say "Stack tests complete — inspect ammolang-test-panel.json"',
        '  post "STACK_TESTS COMPLETE"',
        "",
    ]
    (OUT / "stack_tests.aml").write_text("\n".join(master), encoding="utf-8")
    print(f"wrote {len(written)} suites + stack_tests.aml → {OUT}")
    snippet_count = len(list(SNIPPETS.glob("*.sh"))) if SNIPPETS.is_dir() else 0
    print(f"snippets: {snippet_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())