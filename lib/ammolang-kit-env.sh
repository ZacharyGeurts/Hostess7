#!/usr/bin/env bash
# AmmoLang kit environment — Grok16 + PythonG + paths bundled with NewLatest.
# Source from ammolang-run.sh only; sets everything the build needs.
set -euo pipefail

_aml_kit_root() {
  if [[ -n "${NEXUS_INSTALL_ROOT:-}" && -d "${NEXUS_INSTALL_ROOT}/lib" ]]; then
    cd "${NEXUS_INSTALL_ROOT}" && pwd
    return 0
  fi
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  printf '%s\n' "$here"
}

AML_KIT_ROOT="$(_aml_kit_root)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$AML_KIT_ROOT}"
export SG_ROOT="${SG_ROOT:-$(cd "${NEXUS_INSTALL_ROOT}/.." && pwd)}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${NEXUS_INSTALL_ROOT}/.nexus-state}"
export GROK16_ROOT="${GROK16_ROOT:-${NEXUS_INSTALL_ROOT}/Grok16}"
export QUEEN_ROOT="${QUEEN_ROOT:-${NEXUS_INSTALL_ROOT}/Queen}"
export FINAL_EYE_ROOT="${FINAL_EYE_ROOT:-${NEXUS_INSTALL_ROOT}/Final_Eye}"
export KILROY_ROOT="${KILROY_ROOT:-${NEXUS_INSTALL_ROOT}/KILROY}"
export HOSTESS7_ROOT="${HOSTESS7_ROOT:-${NEXUS_INSTALL_ROOT}/Hostess7}"
export AML_LIB="${AML_LIB:-${NEXUS_INSTALL_ROOT}/library/dewey/000-computer-science/ammolang}"

# Kit Python — PythonG first, then Grok16 driver chain
if [[ -x "${NEXUS_INSTALL_ROOT}/PythonG/bin/pythong" ]]; then
  export NEXUS_PYTHONG="${NEXUS_INSTALL_ROOT}/PythonG/bin/pythong"
elif [[ -x "${GROK16_ROOT}/python/driver/gpy16_driver.py" ]]; then
  export NEXUS_PYTHONG="${GROK16_ROOT}/python/driver/gpy16_driver.py"
else
  export NEXUS_PYTHONG="${NEXUS_PYTHONG:-$(command -v pythong 2>/dev/null || command -v python3)}"
fi

export PATH="${NEXUS_INSTALL_ROOT}/PythonG/bin:${NEXUS_INSTALL_ROOT}/bin:${PATH}"
export AML_BUILD=1
export AML_FAST="${AML_FAST:-1}"
export AML_PROGRESS="${AML_PROGRESS:-1}"
export GPY16_FAST="${GPY16_FAST:-1}"
export GPY16_CACHE="${GPY16_CACHE:-1}"
export GPY16_SKIP_AI_BOOT="${GPY16_SKIP_AI_BOOT:-1}"
export GPY16_PROFILE="${GPY16_PROFILE:-fastest}"
export GROKPY_PROFILE="${GROKPY_PROFILE:-fastest}"
export AML_IMPL=1

mkdir -p "${NEXUS_STATE_DIR}"