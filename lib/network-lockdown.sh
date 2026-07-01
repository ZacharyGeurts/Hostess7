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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/network-lockdown.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Network lockdown — disable and remove local file sharing / broadcast services.

NEXUS_SHARING_UNITS=(
  smbd.service
  nmbd.service
  samba.service
  samba-ad-dc.service
  avahi-daemon.service
  avahi-daemon.socket
  nfs-server.service
  nfs-kernel-server.service
  rpcbind.service
  rpcbind.socket
  vsftpd.service
  proftpd.service
  netatalk.service
  wsdd.service
  minidlna.service
  minidlnad.service
  rpc-statd.service
)

# Server-only packages — never purge client/common libs (smbclient, samba-common, avahi-daemon).
NEXUS_SHARING_PACKAGES_DEB=(
  samba
  samba-ad-dc
  samba-vfs-modules
  nfs-kernel-server
  vsftpd
  proftpd
  netatalk
  minidlna
  wsdd
)

nexus_network_unit_exists() {
  local unit="$1"
  systemctl list-unit-files "${unit}" &>/dev/null \
    || systemctl cat "${unit}" &>/dev/null
}

nexus_network_disable_unit() {
  local unit="$1"
  # No sudo — ZNetwork owns policy; skip system mutations when not root.
  [[ "$(id -u)" -eq 0 ]] || return 0
  command -v systemctl >/dev/null 2>&1 || return 0
  nexus_network_unit_exists "${unit}" || return 0
  systemctl stop "${unit}" 2>/dev/null || true
  systemctl disable "${unit}" 2>/dev/null || true
  systemctl mask "${unit}" 2>/dev/null || true
  nexus_log "INFO" "network-lockdown" "disabled ${unit}"
}

nexus_network_purge_packages() {
  command -v apt-get >/dev/null 2>&1 || return 0
  local pkg pkgs=()
  for pkg in "${NEXUS_SHARING_PACKAGES_DEB[@]}"; do
    dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q 'install ok installed' && pkgs+=("$pkg")
  done
  [[ ${#pkgs[@]} -eq 0 ]] && return 0
  export DEBIAN_FRONTEND=noninteractive
  apt-get remove --purge -y -qq "${pkgs[@]}" 2>/dev/null || true
  nexus_log "INFO" "network-lockdown" "purged packages: ${pkgs[*]}"
}

nexus_network_lockdown() {
  [[ "${NEXUS_NETWORK_LOCKDOWN:-1}" == "1" ]] || return 0
  # Never harm the host OS — skip system service mutations when coexist mode is on.
  [[ "${NEXUS_NEVER_HARM_OS:-${ZNETWORK_NEVER_HARM_OS:-1}}" != "0" ]] && {
    nexus_log "INFO" "network-lockdown" "SKIP never_harm_os"
    return 0
  }
  # ZNetwork active — do not fight OS network stack; sharing lockdown needs root anyway.
  if [[ -f "${NEXUS_STATE_DIR}/znetwork-handler-guard.json" ]] \
    && grep -q '"active"[[:space:]]*:[[:space:]]*true' "${NEXUS_STATE_DIR}/znetwork-handler-guard.json" 2>/dev/null; then
    nexus_log "INFO" "network-lockdown" "SKIP znetwork_policy_owner"
    return 0
  fi
  [[ "$(id -u)" -eq 0 ]] || return 0
  local unit
  for unit in "${NEXUS_SHARING_UNITS[@]}"; do
    nexus_network_disable_unit "${unit}"
  done
  [[ "${NEXUS_NETWORK_LOCKDOWN_PURGE:-1}" == "1" ]] && nexus_network_purge_packages
  [[ -f /etc/samba/smb.conf ]] && chmod 600 /etc/samba/smb.conf 2>/dev/null || true
}

nexus_network_lockdown_verify() {
  [[ "${NEXUS_NETWORK_LOCKDOWN:-1}" == "1" ]] || return 0
  [[ "${NEXUS_NEVER_HARM_OS:-${ZNETWORK_NEVER_HARM_OS:-1}}" != "0" ]] && return 0
  command -v systemctl >/dev/null 2>&1 || return 0
  local unit
  for unit in smbd.service nmbd.service avahi-daemon.service avahi-daemon.socket \
    nfs-server.service nfs-kernel-server.service; do
    if systemctl is-active --quiet "${unit}" 2>/dev/null; then
      nexus_alert "network-lockdown" "NETWORK_LOCKDOWN_ALERT unit=${unit} state=active"
      nexus_network_disable_unit "${unit}"
    fi
  done
  return 0
}