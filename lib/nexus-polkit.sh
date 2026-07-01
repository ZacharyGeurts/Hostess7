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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-polkit.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Field polkit — install, verify, and invoke hardened pkexec bridge.
set -euo pipefail

_NEXUS_POLKIT_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_NEXUS_POLKIT_ROOT="$(cd "${_NEXUS_POLKIT_LIB}/.." && pwd)"

nexus_polkit_policy_src() {
  local candidates=(
    "${NEXUS_INSTALL_SRC:-}/install/polkit/com.nexus.field.policy"
    "${_NEXUS_POLKIT_ROOT}/install/polkit/com.nexus.field.policy"
    "${SG_ROOT:-}/NewLatest/install/polkit/com.nexus.field.policy"
  )
  local c
  for c in "${candidates[@]}"; do
    [[ -f "$c" ]] && { printf '%s' "$c"; return 0; }
  done
  return 1
}

nexus_polkit_rules_src() {
  local candidates=(
    "${NEXUS_INSTALL_SRC:-}/install/polkit/49-com.nexus.field.rules"
    "${_NEXUS_POLKIT_ROOT}/install/polkit/49-com.nexus.field.rules"
    "${SG_ROOT:-}/NewLatest/install/polkit/49-com.nexus.field.rules"
  )
  local c
  for c in "${candidates[@]}"; do
    [[ -f "$c" ]] && { printf '%s' "$c"; return 0; }
  done
  return 1
}

nexus_polkit_bridge_path() {
  if [[ -x /usr/local/lib/nexus-shield/lib/nexus-pkexec-bridge.sh ]]; then
    printf '%s' /usr/local/lib/nexus-shield/lib/nexus-pkexec-bridge.sh
    return 0
  fi
  if [[ -x "${_NEXUS_POLKIT_LIB}/nexus-pkexec-bridge.sh" ]]; then
    printf '%s' "${_NEXUS_POLKIT_LIB}/nexus-pkexec-bridge.sh"
    return 0
  fi
  return 1
}

nexus_polkit_installed() {
  [[ -f /usr/share/polkit-1/actions/com.nexus.field.policy ]]
}

nexus_polkit_install() {
  local policy rules bridge
  policy="$(nexus_polkit_policy_src)" || return 0
  rules="$(nexus_polkit_rules_src)" || true
  bridge="${_NEXUS_POLKIT_LIB}/nexus-pkexec-bridge.sh"
  [[ -f "$bridge" ]] || bridge="/usr/local/lib/nexus-shield/lib/nexus-pkexec-bridge.sh"
  install -d -m 755 /usr/share/polkit-1/actions /etc/polkit-1/rules.d 2>/dev/null || return 0
  install -m 644 "$policy" /usr/share/polkit-1/actions/com.nexus.field.policy
  if [[ -n "${rules:-}" && -f "$rules" ]]; then
    install -m 644 "$rules" /etc/polkit-1/rules.d/49-com.nexus.field.rules
  fi
  if [[ -f "$bridge" ]]; then
    install -d -m 755 /usr/local/lib/nexus-shield/lib 2>/dev/null || true
    install -m 755 "$bridge" /usr/local/lib/nexus-shield/lib/nexus-pkexec-bridge.sh
  fi
  # Retire legacy single-action policy name if present.
  rm -f /usr/share/polkit-1/actions/com.nexus.field.install.policy 2>/dev/null || true
  command -v systemctl >/dev/null 2>&1 && systemctl reload polkit 2>/dev/null || true
}

nexus_polkit_bootstrap_if_cached_sudo() {
  nexus_polkit_installed && return 0
  if sudo -n true 2>/dev/null; then
    nexus_polkit_install || true
  fi
}

nexus_polkit_action_for() {
  local verb="${1:-install}"
  if nexus_polkit_installed; then
    case "$verb" in
      install) printf '%s' com.nexus.field.install ;;
      update)  printf '%s' com.nexus.field.update ;;
      harden)  printf '%s' com.nexus.field.harden ;;
      service) printf '%s' com.nexus.field.service ;;
      underlay) printf '%s' com.nexus.field.underlay ;;
      freeze)   printf '%s' com.nexus.field.freeze ;;
      znetwork) printf '%s' com.nexus.field.znetwork ;;
      *)       printf '%s' com.nexus.field.install ;;
    esac
  else
    printf '%s' com.nexus.field.bootstrap
  fi
}

nexus_pol_py() {
  local py="${NEXUS_INSTALL_ROOT:-${_NEXUS_POLKIT_ROOT}}/lib/field-polkit.py"
  [[ -f "$py" ]] || py="${_NEXUS_POLKIT_LIB}/field-polkit.py"
  [[ -f "$py" ]] || return 1
  local runner="${NEXUS_PYTHONG:-pythong}"
  command -v "$runner" >/dev/null 2>&1 || runner="python3"
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${_NEXUS_POLKIT_ROOT}}" \
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    "$runner" "$py" "$@"
}

nexus_pol_root_json() {
  local purpose="${1:-}"
  nexus_pol_py root "$purpose" 2>/dev/null
}

nexus_pol_is_root() {
  if [[ "$(id -u 2>/dev/null || echo 1)" -eq 0 ]]; then
    return 0
  fi
  local doc
  doc="$(nexus_pol_root_json "${1:-}")" || return 1
  grep -q '"is_root"[[:space:]]*:[[:space:]]*true' <<<"$doc" 2>/dev/null
}

nexus_pol_has_cached_sudo() {
  sudo -n true 2>/dev/null
}

nexus_polkit_pkexec_supports_action() {
  command -v pkexec >/dev/null 2>&1 || return 1
  pkexec --help 2>&1 | grep -q -- '--action'
}

nexus_pol_secure_sudo() {
  local prompt="${1:-NEXUS Field — administrator password required.}"
  if [[ "$(id -u)" -eq 0 ]]; then
    return 0
  fi
  if nexus_pol_has_cached_sudo; then
    return 0
  fi
  if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]] && command -v zenity >/dev/null 2>&1; then
    local pw
    pw="$(zenity --password --title="NEXUS Field" --text="$prompt" 2>/dev/null || true)"
    if [[ -z "$pw" ]]; then
      return 3
    fi
    printf '%s\n' "$pw" | sudo -S -v 2>/dev/null
    local rc=$?
    unset pw
    return $rc
  fi
  sudo -v || return 1
}

nexus_pol_start_sudo_keepalive() {
  # shellcheck source=/dev/null
  [[ -f "${_NEXUS_POLKIT_LIB}/nexus-elevate.sh" ]] && source "${_NEXUS_POLKIT_LIB}/nexus-elevate.sh"
  if declare -f nexus_elevate_sudo_keepalive_start >/dev/null 2>&1; then
    nexus_elevate_sudo_keepalive_start
  fi
}

# Ensure root via pol — pkexec bridge first on Linux GUI, else secure sudo -v.
nexus_pol_ensure_root() {
  local purpose="${1:-general}"
  if nexus_pol_is_root "$purpose"; then
    export NEXUS_ELEVATED_ROOT=1
    return 0
  fi
  if nexus_pol_has_cached_sudo; then
    nexus_pol_start_sudo_keepalive
    export NEXUS_ELEVATED_ROOT=1
    return 0
  fi
  # shellcheck source=/dev/null
  [[ -f "${_NEXUS_POLKIT_LIB}/nexus-elevate.sh" ]] && source "${_NEXUS_POLKIT_LIB}/nexus-elevate.sh"
  if declare -f nexus_elevate_has_gui >/dev/null 2>&1 && nexus_elevate_has_gui \
    && command -v pkexec >/dev/null 2>&1; then
    local bridge action marker="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}/pol-elevate.marker"
    bridge="$(nexus_polkit_bridge_path)" || true
    if [[ -n "${bridge:-}" ]]; then
      nexus_polkit_bootstrap_if_cached_sudo
      action="$(nexus_polkit_action_for znetwork)"
      mkdir -p "$(dirname "$marker")" 2>/dev/null || true
      : >"$marker"
      chmod 600 "$marker" 2>/dev/null || true
      if nexus_polkit_pkexec_supports_action; then
        if pkexec --action "$action" "$bridge" run-znetwork "$marker"; then
          nexus_pol_start_sudo_keepalive
          export NEXUS_ELEVATED_ROOT=1
          return 0
        fi
      elif pkexec "$bridge" run-znetwork "$marker" 2>/dev/null; then
        nexus_pol_start_sudo_keepalive
        export NEXUS_ELEVATED_ROOT=1
        return 0
      fi
    fi
  fi
  nexus_pol_secure_sudo "Authenticate once for ${purpose}." || return 1
  nexus_pol_start_sudo_keepalive
  export NEXUS_ELEVATED_ROOT=1
  return 0
}

nexus_polkit_resolve_installer() {
  local name="${1:-install-all.sh}"
  local candidates=(
    "${NEXUS_INSTALL_SRC:-}/${name}"
    "${_NEXUS_POLKIT_ROOT}/${name}"
    "/usr/local/lib/nexus-shield/${name}"
  )
  local c
  for c in "${candidates[@]}"; do
    [[ -f "$c" ]] && { readlink -f "$c"; return 0; }
  done
  return 1
}

# pkexec via bridge — never pkexec bash directly.
nexus_polkit_pkexec() {
  local verb="$1"
  shift
  local bridge action
  bridge="$(nexus_polkit_bridge_path)" || {
    echo "nexus-polkit: pkexec bridge missing." >&2
    return 1
  }
  action="$(nexus_polkit_action_for "$verb")"
  pkexec --action "$action" "$bridge" "run-${verb}" "$@"
}

nexus_polkit_verify() {
  local ok=1
  local policy=/usr/share/polkit-1/actions/com.nexus.field.policy
  local rules=/etc/polkit-1/rules.d/49-com.nexus.field.rules
  local bridge=/usr/local/lib/nexus-shield/lib/nexus-pkexec-bridge.sh
  [[ -f "$policy" ]] || ok=0
  [[ -f "$rules" ]] || ok=0
  [[ -x "$bridge" && ! -w "$bridge" ]] || ok=0
  [[ ! -f /usr/share/polkit-1/actions/com.nexus.field.install.policy ]] || ok=0
  return $((ok == 1 ? 0 : 1))
}