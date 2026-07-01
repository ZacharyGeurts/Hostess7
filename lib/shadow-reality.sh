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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/shadow-reality.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Shadow Reality — hash baseline + inotify tamper detection.

NEXUS_SHADOW_WATCH_PATHS=(
  /etc/passwd
  /etc/shadow
  /etc/gshadow
  /etc/sudoers
  /etc/crontab
  /etc/ssh/sshd_config
)

nexus_shadow_add_user_paths() {
  local home
  for home in /home/* /root; do
    [[ -d "$home" ]] || continue
    [[ -f "${home}/.ssh/authorized_keys" ]] && NEXUS_SHADOW_WATCH_PATHS+=("${home}/.ssh/authorized_keys")
    [[ -f "${home}/.bashrc" ]] && NEXUS_SHADOW_WATCH_PATHS+=("${home}/.bashrc")
  done
}

nexus_shadow_hash_store() {
  local target="$1"
  local hash base
  hash="$(nexus_sha256 "$target")"
  [[ -n "$hash" ]] || return 1
  base="$(echo "$target" | tr '/' '_')"
  echo "$hash" >"${NEXUS_SHADOW_DIR}/${base}.sha"
  chmod 600 "${NEXUS_SHADOW_DIR}/${base}.sha" 2>/dev/null || true
}

nexus_shadow_init() {
  nexus_ensure_dirs || return 1
  nexus_shadow_add_user_paths
  local path
  for path in "${NEXUS_SHADOW_WATCH_PATHS[@]}"; do
    [[ -e "$path" ]] || continue
    nexus_shadow_hash_store "$path"
  done
  if [[ -d /usr/local/bin ]]; then
    find /usr/local/bin -maxdepth 1 -type f 2>/dev/null | while read -r path; do
      nexus_shadow_hash_store "$path"
    done
  fi
  nexus_log "INFO" "shadow-reality" "baseline initialized"
}

nexus_shadow_verify_one() {
  local target="$1"
  local base stored current
  base="$(echo "$target" | tr '/' '_')"
  stored="$(cat "${NEXUS_SHADOW_DIR}/${base}.sha" 2>/dev/null)"
  [[ -n "$stored" ]] || return 0
  current="$(nexus_sha256 "$target")"
  if [[ "$current" != "$stored" ]]; then
    nexus_alert "shadow-reality" "SHADOW_REALITY_ALERT path=${target} stored=${stored:0:12} current=${current:0:12}"
    return 1
  fi
  return 0
}

nexus_shadow_verify() {
  local path changed=0
  for path in "${NEXUS_SHADOW_WATCH_PATHS[@]}"; do
    [[ -e "$path" ]] || continue
    nexus_shadow_verify_one "$path" || changed=1
  done
  return "$changed"
}

nexus_shadow_check_path() {
  local path="$1"
  nexus_is_high_churn_path "$path" && return 0
  if [[ -f "$path" ]]; then
    if [[ ! -f "${NEXUS_SHADOW_DIR}/$(echo "$path" | tr '/' '_').sha" ]]; then
      nexus_shadow_hash_store "$path"
    else
      nexus_shadow_verify_one "$path"
    fi
  fi
}

nexus_shadow_watch() {
  command -v inotifywait >/dev/null 2>&1 || {
    nexus_log "WARN" "shadow-reality" "inotifywait missing; polling mode"
    while true; do
      nexus_shadow_verify
      sleep "$(nexus_vigil_scan_interval)"
    done
    return
  }
  local args=()
  local path
  for path in "${NEXUS_SHADOW_WATCH_PATHS[@]}"; do
    [[ -e "$path" ]] && args+=("$path")
  done
  [[ -d /usr/local/bin ]] && args+=("/usr/local/bin")
  [[ ${#args[@]} -eq 0 ]] && return 1
  inotifywait -m -e modify,create,delete,move --format '%w%f' "${args[@]}" 2>/dev/null | while read -r changed; do
    nexus_shadow_check_path "$changed"
  done
}