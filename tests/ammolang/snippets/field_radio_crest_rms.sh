#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  "$PY" -c "import numpy, scipy" 2>/dev/null || exit 0
  grep -q 'analyze_audio_quality' "${ROOT}/lib/field-spectrum-demod.py"
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    aml_py "field-spectrum-demod.py" play '{"freq_mhz":93.1,"play":false,"seconds":5}' \
    | grep -q 'crest_factor'
