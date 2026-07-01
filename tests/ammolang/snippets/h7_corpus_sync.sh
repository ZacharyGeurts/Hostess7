#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-h7-corpus-sync.py" ]]
  grep -q 'h7_corpus_sync' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'is_legitimate_h7_textbook' "${ROOT}/lib/field-non-fielded-safety.py"
  grep -q 'h7-k12-field-corpus' "${ROOT}/lib/h7-field-drive-tie.py"
  grep -q 'h7-security-field-corpus' "${ROOT}/lib/h7-field-drive-tie.py"
  tmp_state="$(mktemp -d)"
  out=$(NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" \
    HOSTESS7_ROOT="${HOSTESS7_ROOT:-$ROOT/Hostess7}" \
    SG_ROOT="${SG_ROOT:-$(dirname "$ROOT")}" \
    aml_py "field-h7-corpus-sync.py" sync --no-build 2>/dev/null || true)
  grep -q 'field-h7-corpus-sync' <<<"$out"
  out=$(NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" \
    HOSTESS7_ROOT="${HOSTESS7_ROOT:-$ROOT/Hostess7}" \
    SG_ROOT="${SG_ROOT:-$(dirname "$ROOT")}" \
    aml_py "field-h7-corpus-sync.py" audit 2>/dev/null || true)
  grep -q 'legitimate_h7' <<<"$out"
  rm -rf "$tmp_state"
