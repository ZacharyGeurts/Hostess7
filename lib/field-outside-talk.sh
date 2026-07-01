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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-outside-talk.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Field Outside Talk — egress gate panel payload (SSH, telnet, mail, custom ports).

[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-outside-asm.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-outside-asm.sh"

nexus_field_outside_talk_publish() {
  [[ "${NEXUS_FIELD_OUTSIDE_TALK:-1}" == "1" ]] || return 0
  if declare -f nexus_field_outside_asm_build >/dev/null 2>&1; then
    nexus_field_outside_asm_build >/dev/null 2>&1 || true
  fi
  command -v pythong >/dev/null 2>&1 || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-outside-talk.py"
  [[ -f "$py" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$py" build >/dev/null 2>&1 || true
}

nexus_field_outside_talk_json() {
  if declare -f nexus_field_outside_talk_publish >/dev/null 2>&1; then
    nexus_field_outside_talk_publish
  fi
  local py="${NEXUS_INSTALL_ROOT}/lib/field-outside-talk.py"
  local cache="${NEXUS_STATE_DIR}/field-outside-talk-panel.json"
  if [[ -f "$py" ]]; then
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "$py" json 2>/dev/null && return 0
  fi
  if [[ -s "$cache" ]]; then
    pythong -c "import json,sys; json.dump(json.load(open(sys.argv[1])), sys.stdout)" "$cache" 2>/dev/null
    return 0
  fi
  printf '{"schema":"field-outside-talk/v1","tools":[],"firewall":{"active":false},"recent_sessions":[]}'
}