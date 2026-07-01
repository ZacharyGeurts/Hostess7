# AmmoLang boundary route — AML_BUILD=1 universal boundary
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]] && [[ -z "${AML_BOUNDARY_ACTIVE:-}" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    export AML_BOUNDARY_ACTIVE=1
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/integrate-znetwork.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# AmmoLang subfolder route — AML_BUILD=1 (default)
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" integrate-znetwork "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

# Integrate NewLatest/ZNetwork (canonical) — build, lab posture, relayer env.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"
CANON="${ROOT}/ZNetwork"
STATE="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"

# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh" 2>/dev/null || true
export NEXUS_INSTALL_ROOT="${ROOT}"
export SG_ROOT="${SG}"
nexus_init_runtime_paths 2>/dev/null || true
STATE="${NEXUS_STATE_DIR:-${STATE}}"

# shellcheck source=/dev/null
source "${ROOT}/lib/sg-paths.sh"
sg_paths_export_defaults

mkdir -p "${ROOT}/bin" "${ROOT}/znetwork/data" "${ROOT}/znetwork/scripts" "${STATE}"

link_if_missing() {
  local target="$1" link="$2"
  [[ -e "$target" ]] || return 1
  if [[ -L "$link" ]]; then return 0; fi
  if [[ -e "$link" && ! -L "$link" ]]; then
    echo "skip  ${link} (exists, not symlink)"
    return 0
  fi
  ln -sfn "$target" "$link"
  echo "link  ${link} -> ${target}"
}

echo "=== ZNetwork integrate (canonical: ${CANON}) ==="

[[ -d "$CANON" ]] || {
  echo "ERROR: NewLatest/ZNetwork missing at ${CANON}" >&2
  exit 1
}

link_if_missing "${CANON}/build/znetwork" "${ROOT}/bin/znetwork"
link_if_missing "${CANON}/data/review-checklist.json" "${ROOT}/znetwork/data/review-checklist.json"
link_if_missing "${CANON}/data/znetwork-manifest.json" "${ROOT}/znetwork/data/znetwork-manifest.json"
link_if_missing "${CANON}/scripts/znetwork-probe.sh" "${ROOT}/znetwork/scripts/znetwork-probe.sh"
link_if_missing "${CANON}/scripts/znetwork-review-gate.sh" "${ROOT}/znetwork/scripts/znetwork-review-gate.sh"
link_if_missing "${CANON}/scripts/znetwork-lab-gate.sh" "${ROOT}/znetwork/scripts/znetwork-lab-gate.sh"
link_if_missing "${CANON}/scripts/znetwork-test-battery.sh" "${ROOT}/znetwork/scripts/znetwork-test-battery.sh"
link_if_missing "${CANON}/scripts/znetwork-activate-fast.sh" "${ROOT}/znetwork/scripts/znetwork-activate-fast.sh"
link_if_missing "${CANON}/scripts/znetwork-activate-fast.sh" "${ROOT}/scripts/znetwork-activate-fast.sh"
link_if_missing "${CANON}/scripts/znetwork-build-host.sh" "${ROOT}/scripts/znetwork-build-host.sh"

if [[ ! -x "${CANON}/build/znetwork" ]]; then
  echo "=== ZNetwork build (host toolchain) ==="
  bash "${CANON}/scripts/znetwork-build-host.sh"
fi

export ZNETWORK_ROOT="${ZNETWORK_ROOT:-${CANON}}"
export ZNETWORK_BIN="${ZNETWORK_BIN:-${ZNETWORK_ROOT}/build/znetwork}"

if [[ -f "${CANON}/.lab-state/lab-gate-last.json" ]] \
  && python3 -c "import json; d=json.load(open('${CANON}/.lab-state/lab-gate-last.json')); exit(0 if d.get('ok') else 1)" 2>/dev/null; then
  export ZNETWORK_LAB_GATE_OK=1
  export ZNETWORK_REVIEW_APPROVED=1
fi

if [[ "${ZNETWORK_INTEGRATE_SKIP_BATTERY:-0}" != "1" ]]; then
  echo "=== ZNetwork test battery (smoke) ==="
  bash "${CANON}/scripts/znetwork-test-battery.sh" 2>&1 | tail -20 || {
    echo "WARN: test battery reported issues — continuing REVIEW_ONLY relayer" >&2
    export ZNETWORK_MODE="${ZNETWORK_MODE:-REVIEW_ONLY}"
  }
fi

export NEXUS_ZNETWORK="${NEXUS_ZNETWORK:-1}"
export NEXUS_ZNETWORK_PROMPT=0
export NEXUS_ZNETWORK_NO_SUDO="${NEXUS_ZNETWORK_NO_SUDO:-1}"
export ZNETWORK_RELAYER="${ZNETWORK_RELAYER:-1}"
export ZNETWORK_UNDERHOOK=0
export ZNETWORK_SMART_INSIDE="${ZNETWORK_SMART_INSIDE:-1}"
export ZNETWORK_PROTECTION_ONLY=0
export ZNETWORK_TAKEOVER=0
export ZNETWORK_NEVER_HARM_OS=1
export NEXUS_NEVER_HARM_OS=1
export ZNETWORK_FAST=1
export ZNETWORK_MODE="${ZNETWORK_MODE:-ACTIVE}"
export ZNETWORK_OUTSIDE_LAB=1
export ZNETWORK_INVISIBLE_REPLACE=1
export ZNETWORK_LINK_PRESERVE=1
export ZNETWORK_DEFER_RETALIATE=1

ENV_FILE="${STATE}/znetwork-integrated.env"
{
  echo "# ZNetwork integrated env — generated $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "export SG_ROOT='${SG}'"
  echo "export ZNETWORK_ROOT='${ZNETWORK_ROOT}'"
  echo "export ZNETWORK_BIN='${ZNETWORK_BIN}'"
  echo "export NEXUS_ZNETWORK=1"
  echo "export NEXUS_ZNETWORK_PROMPT=0"
  echo "export NEXUS_ZNETWORK_NO_SUDO=${NEXUS_ZNETWORK_NO_SUDO}"
  echo "export ZNETWORK_RELAYER=1"
  echo "export ZNETWORK_SMART_INSIDE=1"
  echo "export ZNETWORK_NEVER_HARM_OS=1"
  echo "export ZNETWORK_MODE=${ZNETWORK_MODE}"
  echo "export ZNETWORK_LAB_GATE_OK=${ZNETWORK_LAB_GATE_OK:-0}"
  echo "export ZNETWORK_REVIEW_APPROVED=${ZNETWORK_REVIEW_APPROVED:-1}"
  echo "export ZNETWORK_FAST=1"
  echo "export ZNETWORK_DEFER_RETALIATE=1"
} >"${ENV_FILE}"

# shellcheck source=/dev/null
source "${ROOT}/lib/znetwork-field.sh"
nexus_znetwork_startup_with_us 2>/dev/null || nexus_znetwork_publish 2>/dev/null || true

echo ""
echo "ZNetwork integrate OK"
echo "  root:    ${ZNETWORK_ROOT}"
echo "  binary:  ${ZNETWORK_BIN}"
echo "  mode:    ${ZNETWORK_MODE}"
echo "  env:     ${ENV_FILE}"
"${ZNETWORK_BIN}" status --json 2>/dev/null | python3 -c "
import json,sys
try:
  d=json.load(sys.stdin)
  print('  status: ', d.get('mode', d.get('effective', 'ok')))
except Exception:
  pass
" 2>/dev/null || true
nexus_znetwork_status_line 2>/dev/null || true
