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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-common.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS-Shield shared runtime — invisible to consumers, root-only state.
# shellcheck disable=SC2034

NEXUS_VERSION="0.9.0"
NEXUS_EDITION="Universal Protector"
HOSTESS_VERSION="7"

nexus_read_version() {
  printf '%s' "${NEXUS_VERSION:-unknown}"
}
_NEXUS_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_NEXUS_TREE_ROOT="$(cd "${_NEXUS_COMMON_DIR}/.." && pwd)"
NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${_NEXUS_TREE_ROOT}}"
SG_ROOT="${SG_ROOT:-${_NEXUS_TREE_ROOT}}"
if [[ -f "${_NEXUS_COMMON_DIR}/sg-paths.sh" ]]; then
  # shellcheck source=/dev/null
  source "${_NEXUS_COMMON_DIR}/sg-paths.sh"
  sg_paths_export_defaults 2>/dev/null || true
fi
FINAL_EYE_ROOT="${FINAL_EYE_ROOT:-${NEXUS_INSTALL_ROOT:-${SG_ROOT}/NewLatest}/Final_Eye}"
if declare -f sg_paths_queen_root >/dev/null 2>&1; then
  QUEEN_ROOT="${QUEEN_ROOT:-$(sg_paths_queen_root)}"
else
  QUEEN_ROOT="${QUEEN_ROOT:-${_NEXUS_TREE_ROOT}/Queen}"
fi
# KILROY Field OS — top-level sibling of SG, never inside Queen
if [[ -z "${KILROY_ROOT:-}" && -f "${_NEXUS_COMMON_DIR}/kilroy-resolve.sh" ]]; then
  # shellcheck source=/dev/null
  source "${_NEXUS_COMMON_DIR}/kilroy-resolve.sh"
  nexus_kilroy_export "$SG_ROOT" 2>/dev/null || KILROY_ROOT="${SG_ROOT}/KILROY"
  export KILROY_ROOT
fi
KILROY_ROOT="${KILROY_ROOT:-${SG_ROOT}/KILROY}"
if [[ "${NEXUS_INSTALL_ROOT}" == /usr/local/lib/nexus-shield && -d "${_NEXUS_TREE_ROOT}/lib" ]]; then
  NEXUS_INSTALL_ROOT="${_NEXUS_TREE_ROOT}"
fi
NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
NEXUS_SHADOW_DIR="${NEXUS_SHADOW_DIR:-${NEXUS_STATE_DIR}/shadow}"
NEXUS_BEHAVIOR_DIR="${NEXUS_BEHAVIOR_DIR:-${NEXUS_STATE_DIR}/behavior}"
NEXUS_VIGIL_STATE="${NEXUS_VIGIL_STATE:-${NEXUS_STATE_DIR}/vigil.state}"
NEXUS_ALERT_LOG="${NEXUS_ALERT_LOG:-/var/log/nexus-alerts.log}"
NEXUS_CONFIG="${NEXUS_CONFIG:-${NEXUS_INSTALL_ROOT}/config/nexus.conf}"
NEXUS_GROUP="${NEXUS_GROUP:-nexus}"
NEXUS_FIELD_STANDALONE="${NEXUS_FIELD_STANDALONE:-0}"
NEXUS_FIELD_TOOLS_DIR="${NEXUS_FIELD_TOOLS_DIR:-}"

# shellcheck source=/dev/null
[[ -f "${_NEXUS_COMMON_DIR}/nexus-await.sh" ]] && source "${_NEXUS_COMMON_DIR}/nexus-await.sh"
# shellcheck source=/dev/null
[[ -f "${_NEXUS_COMMON_DIR}/field-max.sh" ]] && source "${_NEXUS_COMMON_DIR}/field-max.sh"

nexus_ensure_group() {
  [[ "${NEXUS_FIELD_STANDALONE:-}" == "1" || "$(id -u)" -ne 0 ]] && return 0
  getent group "$NEXUS_GROUP" >/dev/null 2>&1 || groupadd -r "$NEXUS_GROUP" 2>/dev/null || true
}

nexus_is_dev_install() {
  [[ "${NEXUS_INSTALL_ROOT}" != /usr/local/lib/nexus-shield ]]
}

nexus_is_field_standalone() {
  [[ "${NEXUS_FIELD_STANDALONE:-}" == "1" ]]
}

nexus_resolve_pythong() {
  local candidate
  for candidate in \
    "${NEXUS_PYTHONG:-}" \
    "${PYTHONG:-}" \
    "${PYTHONG_ROOT:-}/bin/pythong" \
    "${NEXUS_INSTALL_ROOT}/PythonG/bin/pythong" \
    "${SG_ROOT}/PythonG/bin/pythong" \
    "${GPY16_ROOT:-}/bin/gpy-16" \
    "${NEXUS_INSTALL_ROOT}/GrokPy/bin/gpy-16" \
    "${SG_ROOT}/GrokPy/bin/gpy-16" \
    "${NEXUS_INSTALL_ROOT}/GrokPy/bin/grokpy" \
    "${SG_ROOT}/GrokPy/bin/grokpy" \
    "${QUEEN_ROOT}/scripts/pythong" \
    "${NEXUS_INSTALL_ROOT}/scripts/nexus-py" \
    "$(command -v pythong 2>/dev/null || true)" \
    "$(command -v python3 2>/dev/null || true)"; do
    [[ -n "$candidate" && -x "$candidate" ]] || continue
    printf '%s' "$candidate"
    return 0
  done
  return 1
}

# GTK tray — system python3 only; GrokPy/gpy-16 cannot parse panel-tray.py.
nexus_resolve_tray_python() {
  local candidate
  for candidate in \
    "${NEXUS_TRAY_PYTHON:-}" \
    "/usr/bin/python3" \
    "$(command -v python3 2>/dev/null || true)"; do
    [[ -n "$candidate" && -x "$candidate" ]] || continue
    if "$candidate" -c 'import gi; gi.require_version("Gtk","3.0")' 2>/dev/null; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  for candidate in "/usr/bin/python3" "$(command -v python3 2>/dev/null || true)"; do
    [[ -n "$candidate" && -x "$candidate" ]] || continue
    printf '%s' "$candidate"
    return 0
  done
  return 1
}

# Release/pack scripts — host coreutils only (Grok16 mkdir/rsync wrappers hit ARG_MAX).
nexus_release_host_path() {
  export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
  unset GROK16_BUILD_ESSENTIAL GROK16_FIELD_BUILD 2>/dev/null || true
}

nexus_init_runtime_paths() {
  # Tree checkout: use source tree when install root was not exported.
  if [[ -f "${_NEXUS_TREE_ROOT}/lib/nexus-common.sh" ]] \
    && [[ "${NEXUS_INSTALL_ROOT}" == /usr/local/lib/nexus-shield ]]; then
    NEXUS_INSTALL_ROOT="${_NEXUS_TREE_ROOT}"
  fi

  export SG_ROOT QUEEN_ROOT
  export GPY16_ROOT="${GPY16_ROOT:-${SG_ROOT}/GrokPy}"
  export PYTHONG_ROOT="${PYTHONG_ROOT:-${SG_ROOT}/PythonG}"
  PATH="${PYTHONG_ROOT}/bin:${GPY16_ROOT}/bin:${QUEEN_ROOT}/scripts:${NEXUS_INSTALL_ROOT}/lib/bin:${PATH}"
  NEXUS_PYTHONG="$(nexus_resolve_pythong 2>/dev/null || true)"
  [[ -n "$NEXUS_PYTHONG" ]] && PATH="$(dirname "$NEXUS_PYTHONG"):${PATH}"
  export PATH NEXUS_PYTHONG

  local use_local=0
  if nexus_is_dev_install; then
    use_local=1
  fi
  if [[ "${NEXUS_FIELD_STANDALONE:-}" == "1" ]]; then
    use_local=1
  fi
  local prod_state="/var/lib/nexus-shield"
  local in_nexus_group=0
  getent group nexus 2>/dev/null | grep -qE "(^|:)${USER:-$(id -un)}(,|$)" && in_nexus_group=1

  # nexus group members read live field data from prod state even without write access.
  if [[ "$in_nexus_group" -eq 1 ]] && [[ -r "${prod_state}/threat-panel.json" ]]; then
    NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${prod_state}}"
    use_local=0
  elif [[ "$(id -u)" -ne 0 ]] && [[ ! -w "${prod_state}" ]] 2>/dev/null; then
    use_local=1
  fi
  if [[ "$(id -u)" -ne 0 ]] && [[ ! -w /var/log ]] 2>/dev/null; then
    use_local=1
  fi

  if [[ "$use_local" -eq 1 ]]; then
    NEXUS_FIELD_STANDALONE=1
    NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${NEXUS_INSTALL_ROOT}/.nexus-state}"
    if [[ "$NEXUS_STATE_DIR" == /var/lib/nexus-shield ]] && [[ "$in_nexus_group" -ne 1 ]]; then
      NEXUS_STATE_DIR="${NEXUS_INSTALL_ROOT}/.nexus-state"
    fi
    NEXUS_ALERT_LOG="${NEXUS_STATE_DIR}/nexus-alerts.log"
    NEXUS_SHADOW_DIR="${NEXUS_STATE_DIR}/shadow"
    NEXUS_BEHAVIOR_DIR="${NEXUS_STATE_DIR}/behavior"
    NEXUS_VIGIL_STATE="${NEXUS_STATE_DIR}/vigil.state"
  fi

  # Portable field drive mirror — tools + state, no sudo.
  local local_drive="${NEXUS_INSTALL_ROOT}/.nexus-field-drive/nexus-field"
  if [[ -d "${local_drive}/state" ]]; then
    NEXUS_FIELD_DRIVE_ACTIVE=1
    NEXUS_FIELD_DRIVE_ROOT="${local_drive}"
    NEXUS_STATE_DIR="${local_drive}/state"
    NEXUS_ALERT_LOG="${NEXUS_STATE_DIR}/nexus-alerts.log"
    NEXUS_SHADOW_DIR="${NEXUS_STATE_DIR}/shadow"
    NEXUS_BEHAVIOR_DIR="${NEXUS_STATE_DIR}/behavior"
    NEXUS_VIGIL_STATE="${NEXUS_STATE_DIR}/vigil.state"
  fi
  if [[ -d "${local_drive}/tools" ]]; then
    NEXUS_FIELD_TOOLS_DIR="${local_drive}/tools"
  elif [[ -d "${NEXUS_INSTALL_ROOT}/lib/bin" ]]; then
    NEXUS_FIELD_TOOLS_DIR="${NEXUS_INSTALL_ROOT}/lib/bin"
  fi

  export NEXUS_INSTALL_ROOT NEXUS_STATE_DIR NEXUS_SHADOW_DIR NEXUS_BEHAVIOR_DIR
  export NEXUS_VIGIL_STATE NEXUS_ALERT_LOG NEXUS_FIELD_STANDALONE NEXUS_FIELD_TOOLS_DIR
  export NEXUS_FIELD_DRIVE_ACTIVE="${NEXUS_FIELD_DRIVE_ACTIVE:-0}"
  export NEXUS_FIELD_DRIVE_ROOT="${NEXUS_FIELD_DRIVE_ROOT:-}"
  export TDIR="${TDIR:-${HOME}/.grok/projects/home-default-Desktop-SG/terminals}"
  mkdir -p "$TDIR" 2>/dev/null || true
}

nexus_root_sovereign_ok() {
  [[ "${SG_ROOT_SOVEREIGN_OFF:-}" == "1" ]] && return 0
  local py="${QUEEN_ROOT:-${SG_ROOT:-}/NewLatest/Queen}/lib/queen-root-sovereign.py"
  [[ -f "$py" ]] || return 0
  local pythong_bin="${NEXUS_PYTHONG:-$(nexus_resolve_pythong 2>/dev/null || true)}"
  [[ -n "$pythong_bin" ]] || return 0
  "$pythong_bin" "$py" check-root >/dev/null 2>&1
}

nexus_operator_authorized() {
  if [[ "$(id -u)" -eq 0 ]]; then
    nexus_root_sovereign_ok && return 0
    return 1
  fi
  nexus_is_dev_install && return 0
  id -nG 2>/dev/null | grep -qw "$NEXUS_GROUP"
}

nexus_apply_permissions() {
  mkdir -p "$NEXUS_STATE_DIR" "$NEXUS_SHADOW_DIR" "$NEXUS_BEHAVIOR_DIR" 2>/dev/null || true
  touch "$NEXUS_ALERT_LOG" 2>/dev/null || true
  if nexus_is_field_standalone || [[ "$(id -u)" -ne 0 ]]; then
    chmod 700 "$NEXUS_SHADOW_DIR" "$NEXUS_BEHAVIOR_DIR" 2>/dev/null || true
    chmod 750 "$NEXUS_STATE_DIR" 2>/dev/null || true
    return 0
  fi
  nexus_ensure_group
  local grp="$NEXUS_GROUP"

  chown -R root:"$grp" "${NEXUS_INSTALL_ROOT}" "$NEXUS_STATE_DIR" 2>/dev/null || true
  chmod 750 "${NEXUS_INSTALL_ROOT}" "${NEXUS_INSTALL_ROOT}/lib" "${NEXUS_INSTALL_ROOT}/bin" \
    "${NEXUS_INSTALL_ROOT}/config" "${NEXUS_INSTALL_ROOT}/tests" 2>/dev/null || true
  find "${NEXUS_INSTALL_ROOT}/lib" -type f -name '*.sh' -exec chmod 750 {} + 2>/dev/null || true
  find "${NEXUS_INSTALL_ROOT}/config" -type f -exec chmod 640 {} + 2>/dev/null || true
  chmod 640 "${NEXUS_INSTALL_ROOT}/MANIFEST.sha256" 2>/dev/null || true
  [[ -d "${NEXUS_INSTALL_ROOT}/panel" ]] && chmod -R 750 "${NEXUS_INSTALL_ROOT}/panel" 2>/dev/null || true
  chmod 750 "${NEXUS_INSTALL_ROOT}/lib/threat-panel-http.py" 2>/dev/null || true

  chmod 750 "$NEXUS_STATE_DIR" 2>/dev/null || true
  chmod 750 "${NEXUS_STATE_DIR}/tls" 2>/dev/null || true
  chmod 700 "$NEXUS_SHADOW_DIR" "$NEXUS_BEHAVIOR_DIR" 2>/dev/null || true
  chown root:"$grp" "$NEXUS_SHADOW_DIR" "$NEXUS_BEHAVIOR_DIR" 2>/dev/null || true
  chmod 640 "$NEXUS_VIGIL_STATE" "${NEXUS_STATE_DIR}/vigil-alerts.log" "${NEXUS_STATE_DIR}/threat-panel.json" \
    "${NEXUS_STATE_DIR}/firewall.state" "${NEXUS_STATE_DIR}/firewall-blocks.tsv" \
    "${NEXUS_STATE_DIR}/firewall-trusted.tsv" \
    "${NEXUS_STATE_DIR}/paranoia.state" "${NEXUS_STATE_DIR}/paranoia-incidents.jsonl" \
    "${NEXUS_STATE_DIR}/paranoia-dedup.tsv" 2>/dev/null || true
  chown root:"$grp" "$NEXUS_VIGIL_STATE" "${NEXUS_STATE_DIR}/vigil-alerts.log" "${NEXUS_STATE_DIR}/threat-panel.json" \
    "${NEXUS_STATE_DIR}/firewall.state" "${NEXUS_STATE_DIR}/firewall-blocks.tsv" \
    "${NEXUS_STATE_DIR}/firewall-trusted.tsv" \
    "${NEXUS_STATE_DIR}/paranoia.state" "${NEXUS_STATE_DIR}/paranoia-incidents.jsonl" \
    "${NEXUS_STATE_DIR}/paranoia-dedup.tsv" 2>/dev/null || true

  touch "$NEXUS_ALERT_LOG" 2>/dev/null || true
  chown root:"$grp" "$NEXUS_ALERT_LOG" 2>/dev/null || true
  chmod 640 "$NEXUS_ALERT_LOG" 2>/dev/null || true

  if [[ -x /usr/local/bin/nexus ]]; then
    chown root:"$grp" /usr/local/bin/nexus 2>/dev/null || true
    chmod 750 /usr/local/bin/nexus 2>/dev/null || true
  fi
}

nexus_ensure_dirs() {
  mkdir -p "$NEXUS_STATE_DIR" "$NEXUS_SHADOW_DIR" "$NEXUS_BEHAVIOR_DIR" 2>/dev/null || return 1
  nexus_apply_permissions
}

nexus_load_config() {
  if [[ -f "$NEXUS_CONFIG" ]]; then
    # shellcheck source=/dev/null
    source "$NEXUS_CONFIG"
  fi
  if [[ -f "${NEXUS_STATE_DIR}/settings.override" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_STATE_DIR}/settings.override"
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-drive-system.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-drive-system.sh"
    nexus_field_drive_apply_paths 2>/dev/null || true
  fi
}

nexus_log() {
  local level="$1" module="$2" message="$3"
  local ts line log_dir
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  line="$(printf '%s [%s] %s: %s\n' "$ts" "$level" "$module" "$message")"
  log_dir="$(dirname "$NEXUS_ALERT_LOG")"
  if [[ -n "$log_dir" ]] && { [[ -w "$NEXUS_ALERT_LOG" ]] || [[ -w "$log_dir" ]]; } 2>/dev/null; then
    { printf '%s' "$line" >>"$NEXUS_ALERT_LOG"; } 2>/dev/null || true
  fi
  logger -t "nexus-${module}" -p daemon.warning "${level}: ${message}" 2>/dev/null || true
}

nexus_alert() {
  local module="$1" message="$2"
  nexus_log "ALERT" "$module" "$message"
  if command -v nexus_vigil_record_alert >/dev/null 2>&1; then
    nexus_vigil_record_alert "$module"
  elif [[ -f "${NEXUS_INSTALL_ROOT}/lib/eternal-vigil.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/eternal-vigil.sh"
    nexus_vigil_record_alert "$module"
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/predictive-guard.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/predictive-guard.sh"
    nexus_predictive_record "$module"
  fi
}

nexus_low_priority() {
  command -v ionice >/dev/null 2>&1 && ionice -c3 -p $$ 2>/dev/null || true
  command -v nice >/dev/null 2>&1 && renice 19 -p $$ >/dev/null 2>&1 || true
}

nexus_sha256() {
  local target="$1"
  sha256sum "$target" 2>/dev/null | awk '{print $1}'
}

nexus_is_high_churn_path() {
  local path="$1"
  case "$path" in
    /tmp/*|/var/tmp/*|*/.cache/*|*/Cache/*|/proc/*|/sys/*|/dev/*) return 0 ;;
  esac
  return 1
}

nexus_extension_allowlisted() {
  local path="$1"
  local ext="${path##*.}"
  case "${ext,,}" in
    zip|gz|bz2|xz|7z|jpg|jpeg|png|gif|webp|wasm|mp4|mp3|pdf|deb|rpm|apk|iso) return 0 ;;
  esac
  return 1
}

nexus_init_runtime_paths
