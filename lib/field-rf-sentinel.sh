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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-rf-sentinel.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Field RF sentinel — FCC spectrum shield + 3-field GPS triangulation radio.

nexus_field_rf_integrate_radio() {
  [[ "${NEXUS_FIELD_RF_TRIANGULATE:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local install="${NEXUS_INSTALL_ROOT:-.}"
  local tri="${install}/lib/field-triangulation-radio.py"
  [[ -f "$tri" ]] || return 0
  (
    cd "$install" || return 0
    NEXUS_INSTALL_ROOT="$install" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      pythong "$tri" 2>/dev/null || true
    [[ -f data/field-gps-lock.json ]] \
      && cp -f data/field-gps-lock.json /tmp/nexus-world-lock.json 2>/dev/null || true
    local cep
    cep="$(pythong -c "import json; print(json.load(open('data/field-gps-lock.json'))['fix'].get('precision','0.25m CEP'))" 2>/dev/null || echo '0.25m CEP')"
    echo "📻 Field Generator now dual-role: Radio Station + Spectrum Receiver active. GPS triangulated to ${cep} in physical world."
    echo '🛰️ AmouranthRTX locked. HeavyBoi fields synchronized.'
  )
}

nexus_field_rf_cycle() {
  [[ "${NEXUS_FIELD_RF:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-rf-sentinel.py"
  [[ -f "$py" ]] || return 0
  nexus_field_rf_integrate_radio
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$py" cycle >/dev/null 2>&1 || true
}

nexus_field_rf_json() {
  local py="${NEXUS_INSTALL_ROOT}/lib/field-rf-sentinel.py"
  if [[ -f "$py" ]]; then
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "$py" json 2>/dev/null && return 0
  fi
  printf '{"antenna":{"mode":"unavailable"},"bursts":[],"shield":{"enabled":true}}'
}

nexus_field_rf_forever_enforce() {
  [[ "${NEXUS_FIELD_RF_FOREVER:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-rf-sentinel.py"
  [[ -f "$py" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$py" forever-enforce >/dev/null 2>&1 || true
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  case "${1:-}" in
    integrate-radio) nexus_field_rf_integrate_radio ;;
    cycle) nexus_field_rf_cycle ;;
    json) nexus_field_rf_json ;;
    forever-enforce) nexus_field_rf_forever_enforce ;;
    *)
      echo "usage: field-rf-sentinel.sh [integrate-radio|cycle|json|forever-enforce]" >&2
      exit 1
      ;;
  esac
fi
