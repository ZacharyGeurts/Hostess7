#!/usr/bin/env bash
# Hostess 7 presume — sovereign layer separate from AML boundary
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"

panel="$(python3 "$ROOT/lib/hostess7-presume.py" panel)"
grep -Fq 'hostess7-presume-panel/v1' <<<"$panel"
grep -Fq 'separate_from_aml' <<<"$panel"

pulse="$(python3 "$ROOT/lib/hostess7-presume.py" pulse)"
grep -Fq 'hostess7-presume-pulse/v1' <<<"$pulse"
grep -Fq 'separate_from_aml' <<<"$pulse"

boundary="$(python3 "$ROOT/lib/field-ammolang-boundary.py" panel)"
grep -Fq 'ammolang-boundary-panel/v1' <<<"$boundary"

! grep -Fq '"id": "ammolang_boundary"' "$ROOT/data/hostess7-presume-doctrine.json"

ub="$(cat "$ROOT/library/dewey/000-computer-science/ammolang/universal_boundary.aml")"
! grep -Fq 'hostess7-presume' <<<"$ub"

tasks="$(python3 "$ROOT/lib/field-ammolang-build.py" tasks)"
grep -Fq 'hostess7_presume' <<<"$tasks"

echo OK hostess7_presume_suite