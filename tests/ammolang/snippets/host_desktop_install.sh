#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/nexus-host-desktop-install.py" ]]
  [[ -f "${ROOT}/lib/nexus-host-desktop-install.sh" ]]
  grep -q 'nexus_field_os_install_host_desktop' "${ROOT}/lib/nexus-field-os.sh"
  grep -q 'nexus_field_os_install_host_desktop' "${ROOT}/nexus.sh"
  grep -q 'nexus-host-desktop/v1' "${ROOT}/lib/nexus-host-desktop-install.py"
  grep -q 'ammocode-stack' "${ROOT}/lib/nexus-host-desktop-install.py"
  grep -q 'pinned-apps' "${ROOT}/lib/nexus-host-desktop-install.py"
  tmp_state="$(mktemp -d)"
  tmp_home="$(mktemp -d)"
  mkdir -p "${tmp_home}/.local/share/applications"
  printf '[Desktop Entry]\nType=Application\nName=Old\nExec=true\n' >"${tmp_home}/.local/share/applications/ammocode-stack.desktop"
  NEXUS_HOST_DESKTOP_HOME="$tmp_home" NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" \
    NEXUS_HOST_DESKTOP_PIN=0 NEXUS_HOST_DESKTOP_FORCE=1 \
    aml_py "nexus-host-desktop-install.py" run | grep -q 'nexus-host-desktop/v1'
  [[ ! -f "${tmp_home}/.local/share/applications/ammocode-stack.desktop" ]]
  [[ -f "${tmp_home}/.local/share/applications/nexus-field.desktop" ]]
  rm -rf "$tmp_state" "$tmp_home"
