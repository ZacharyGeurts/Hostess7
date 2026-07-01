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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-us-intel.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# US Field Intel — Page 1 forensic dossier for THIS machine (local tools only).

nexus_us_field_publish() {
  [[ "${NEXUS_US_FIELD_INTEL:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-us-intel.py"
  [[ -f "$py" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$py" build 2>/dev/null || true
  local dst="${NEXUS_STATE_DIR}/us-field.json"
  chmod 640 "$dst" 2>/dev/null || true
  chown root:nexus "$dst" 2>/dev/null || true
}

nexus_us_field_json() {
  if declare -f nexus_us_field_publish >/dev/null 2>&1; then
    nexus_us_field_publish
  fi
  local f="${NEXUS_STATE_DIR}/us-field.json"
  if [[ -s "$f" ]]; then
    pythong -c "import json,sys; json.dump(json.load(open(sys.argv[1])), sys.stdout)" "$f" 2>/dev/null
    return 0
  fi
  local py="${NEXUS_INSTALL_ROOT}/lib/field-us-intel.py"
  if [[ -f "$py" ]]; then
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "$py" json 2>/dev/null
    return 0
  fi
  printf '{"page":1,"title":"US","observations":["US field intel warming up — ss/ip/proc not sampled yet."]}'
}