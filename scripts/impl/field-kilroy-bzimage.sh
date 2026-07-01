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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/impl/field-kilroy-bzimage.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# KILROY bzImage — build or status. Required for live Field Die; optional for Mint dev graft.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KILROY="${KILROY_ROOT:-${ROOT}/KILROY}"
if [[ -f "${KILROY}/scripts/kilroy-env.sh" ]]; then
  # shellcheck source=/dev/null
  source "${KILROY}/scripts/kilroy-env.sh"
  kilroy_bootstrap_env 2>/dev/null || true
fi
export CC="${CC:-/usr/bin/gcc}"
export HOSTCC="${HOSTCC:-/usr/bin/gcc}"
export PATH="${KILROY_PATH_HOST:-/usr/bin:/bin:$PATH}"
BZ="${KILROY}/build/bzImage"
BUILD="${KILROY}/scripts/build-kilroy.sh"
MODE="${1:-status}"

kilroy_status() {
  echo "=== KILROY bzImage ==="
  echo "  kilroy_root: ${KILROY}"
  if [[ -f "$BZ" ]]; then
    echo "  bzImage: present (${BZ})"
    ls -lh "$BZ"
    if [[ -r /proc/version ]] && grep -q kilroy /proc/version 2>/dev/null; then
      echo "  running: KILROY kernel live"
    else
      echo "  running: host kernel (graft/userspace — /proc/kilroy_field not live)"
    fi
    echo "METRIC kilroy_bzimage=1"
    return 0
  fi
  echo "  bzImage: missing"
  echo "  graft: userspace field tech active via nexus-genius + unified-device"
  echo "  build: bash ${ROOT}/scripts/field-kilroy-bzimage.sh build"
  echo "METRIC kilroy_bzimage=0"
  return 1
}

kilroy_build() {
  [[ -x "$BUILD" ]] || { echo "FAIL missing ${BUILD}" >&2; exit 1; }
  echo "=== Building KILROY bzImage (may take several minutes) ==="
  cd "$KILROY"
  bash "$BUILD"
  if [[ -f "$BZ" ]]; then
    echo "OK kilroy bzImage built"
    ls -lh "$BZ"
    echo "  qemu: bash ${KILROY}/scripts/grok-boot-qemu.sh"
    exit 0
  fi
  echo "FAIL bzImage not produced" >&2
  exit 1
}

case "$MODE" in
  status|check) kilroy_status ;;
  build|make)   kilroy_build ;;
  *)
    echo "usage: field-kilroy-bzimage.sh [status|build]" >&2
    exit 1
    ;;
esac
