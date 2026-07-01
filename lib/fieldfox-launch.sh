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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/fieldfox-launch.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Queen integrated field browser launcher — Field Gecko profile, Webbrowser shell (no OS browser).
set -euo pipefail

ROOT="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
STATE="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
URL="${1:-about:blank}"
QUEEN="${QUEEN_ROOT:-${ROOT}/Queen}"
PY="${NEXUS_PYTHONG:-pythong}"

nexus_fieldfox_launch() {
  local url="${1:-about:blank}"
  local route=""
  if [[ "$url" == *"#"* ]]; then
    route="${url#*#}"
  fi
  if [[ -f "${ROOT}/lib/queen-integrated-browser.py" ]]; then
    NEXUS_INSTALL_ROOT="${ROOT}" NEXUS_STATE_DIR="${STATE}" QUEEN_ROOT="${QUEEN}" \
      QUEEN_NO_OS_BROWSER=1 QUEEN_WEB_SHELL=1 QUEEN_SKIP_RTX_BOOT=1 \
      NEXUS_C2_DESKTOP_LAUNCH=1 NEXUS_C2_KIOSK=1 \
      "$PY" "${ROOT}/lib/queen-integrated-browser.py" open 2>/dev/null \
      && echo "{\"launched\":true,\"engine\":\"queen-field-gecko\",\"url\":\"${url}\",\"queen\":true}" \
      && return 0
  fi
  if [[ -f "${ROOT}/lib/queen-panel-open.py" ]]; then
    NEXUS_INSTALL_ROOT="${ROOT}" NEXUS_STATE_DIR="${STATE}" QUEEN_ROOT="${QUEEN}" \
      "$PY" "${ROOT}/lib/queen-panel-open.py" nexus "$route" 2>/dev/null \
      && echo "{\"launched\":true,\"engine\":\"queen-browser\",\"url\":\"${url}\",\"queen\":true}" \
      && return 0
  fi
  if [[ -x "${QUEEN}/scripts/start-world.sh" ]]; then
    NEXUS_INSTALL_ROOT="${ROOT}" QUEEN_ROOT="${QUEEN}" "${QUEEN}/scripts/start-world.sh" --daemon >/dev/null 2>&1 || true
  fi
  echo "{\"launched\":false,\"error\":\"queen_panel_open_missing\",\"url\":\"${url}\"}" >&2
  return 1
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  nexus_fieldfox_launch "${URL}"
fi