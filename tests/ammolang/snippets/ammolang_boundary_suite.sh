#!/usr/bin/env bash
# AmmoLang universal boundary — resolve · panel · exec
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"

panel="$(python3 "$ROOT/lib/field-ammolang-boundary.py" panel)"
grep -Fq 'ammolang-boundary-panel/v1' <<<"$panel"

resolve="$(AML_BOUNDARY_TARGET='py:field-exploring-hostess7' AML_BOUNDARY_ARGS_JSON='["status"]' python3 "$ROOT/lib/field-ammolang-boundary.py" resolve)"
grep -Fq 'ammolang-boundary-spec/v1' <<<"$resolve"
grep -Fq '"kind": "py"' <<<"$resolve"

scan="$(python3 "$ROOT/lib/field-ammolang-boundary.py" scan)"
grep -Fq 'field-ammolang-boundary-registry/v1' <<<"$scan"
grep -Fq 'beta_pipeline' <<<"$scan"

tasks="$(python3 "$ROOT/lib/field-ammolang-build.py" tasks)"
grep -Fq 'universal_boundary' <<<"$tasks"
grep -Fq 'boundary_entries' <<<"$tasks"

echo OK ammolang_boundary_suite