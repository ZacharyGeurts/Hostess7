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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/tristate-virtual-kilroy-field.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Virtual Tristate test on /media/default/KILROY_FIELD — host stays safe.
set -euo pipefail

FRESH=0
for arg in "$@"; do
  case "$arg" in
    --fresh) FRESH=1 ;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KF="${KILROY_FIELD_ROOT:-/media/default/KILROY_FIELD}"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}"
export TRISTATE_VIRTUAL=1
export KILROY_FIELD_ROOT="${KF}"
unset NEXUS_STATE_DIR
# Field partition tmp only — host /var and Queen state never touched.
export NEXUS_STATE_DIR="${KF}/tmp/nexus-shield-virtual"
export NEXUS_UNDERLAY_FORCE=1

if [[ ! -d "$KF" ]]; then
  echo "[tristate-virtual] missing mount: $KF" >&2
  exit 2
fi

echo "[tristate-virtual] KILROY_FIELD=$KF"
echo "[tristate-virtual] state=$NEXUS_STATE_DIR (field partition tmp — host safe)"
echo "[tristate-virtual] host lock before: $(test -f /var/lib/nexus-shield/field-underlay-lock.json && echo present || echo absent)"

mkdir -p "$NEXUS_STATE_DIR" "${KF}/tmp/field-storage/tristate-probe"

PY="${ROOT}/lib/field-underlay-switch.py"
FRESH_ARGS=()
[[ "$FRESH" == 1 ]] && FRESH_ARGS=(--fresh)
[[ "$FRESH" == 1 ]] && export TRISTATE_VIRTUAL_FRESH=1

echo "[tristate-virtual] running virtual-test pipeline… (fresh=${FRESH})"
env -i HOME="${HOME}" PATH="${PATH}" USER="${USER:-default}" LOGNAME="${LOGNAME:-default}" \
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" SG_ROOT="${SG_ROOT}" \
  TRISTATE_VIRTUAL=1 KILROY_FIELD_ROOT="${KF}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
  NEXUS_UNDERLAY_FORCE=1 TRISTATE_VIRTUAL_FRESH="${TRISTATE_VIRTUAL_FRESH:-0}" \
  pythong "$PY" virtual-test "${FRESH_ARGS[@]}" | tee "${NEXUS_STATE_DIR}/tristate-virtual-last.json"

echo ""
echo "[tristate-virtual] host lock after: $(test -f /var/lib/nexus-shield/field-underlay-lock.json && echo present || echo absent)"
echo "[tristate-virtual] field lock: ${NEXUS_STATE_DIR}/field-underlay-lock.json"
echo "[tristate-virtual] report: ${NEXUS_STATE_DIR}/tristate-virtual-report.json"
echo "[tristate-virtual] bzImage: ${KF}/boot/kilroy/bzImage"
ls -la "${KF}/boot/kilroy/bzImage" 2>/dev/null || true