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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-update-apply.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS update apply — release installer tarball (default) or git tree fallback.
# Holds github-update.lock, downloads release, install-all.sh, restart.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"

UPDATE_MODE="${NEXUS_UPDATE_MODE:-release}"
APPLY_VIA="${NEXUS_UPDATE_APPLY_VIA:-}"
CATALOG_URL="${NEXUS_UPDATE_CATALOG_URL:-}"
GIT_DIR="${NEXUS_UPDATE_GIT_DIR:-$ROOT}"
INSTALL_SH="${NEXUS_UPDATE_INSTALL_SH:-${GIT_DIR}/install-all.sh}"
TARBALL_URL="${NEXUS_UPDATE_TARBALL_URL:-}"
TARGET="${NEXUS_UPDATE_TARGET:-}"
PREVIOUS="${NEXUS_UPDATE_PREVIOUS:-}"
TOKEN="${NEXUS_UPDATE_LOCK_TOKEN:-}"
LOG="${NEXUS_STATE_DIR}/update-apply.log"
NEEDS_SUDO_JSON="${NEXUS_STATE_DIR}/update-needs-sudo.json"
STAGING="${NEXUS_STATE_DIR}/update-staging"

# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/nexus-common.sh" 2>/dev/null || true
nexus_init_runtime_paths 2>/dev/null || true
# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-update-lock.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/nexus-update-lock.sh"
# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT}/lib/panel-browser.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/panel-browser.sh"

_log() {
  printf '[%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "$LOG"
}

_heartbeat_loop() {
  [[ -n "$TOKEN" ]] || return 0
  while true; do
    if ! nexus_update_lock_heartbeat "$TOKEN" 2>/dev/null | grep -q '"ok": true'; then
      break
    fi
    sleep 25
  done
}

_cleanup() {
  local rc=$?
  kill "${HB_PID:-}" 2>/dev/null || true
  if [[ $rc -eq 0 ]]; then
    rm -f "$NEEDS_SUDO_JSON" 2>/dev/null || true
  elif [[ -n "$TOKEN" ]]; then
    nexus_update_lock_phase failed "--token=${TOKEN}" 2>/dev/null || true
  fi
  if [[ -n "$TOKEN" ]]; then
    nexus_update_lock_release "$TOKEN" 2>/dev/null || nexus_update_lock_release 2>/dev/null || true
  fi
  exit "$rc"
}

_run_with_sudo() {
  local inner="$1"
  if [[ "$(id -u)" -eq 0 ]]; then
    bash -c "$inner"
    return $?
  fi
  if sudo -n true 2>/dev/null; then
    _log "sudo: cached credentials"
    sudo -E bash -c "$inner"
    return $?
  fi
  if command -v pkexec >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    _log "sudo: field polkit pkexec (bridge)"
    local polkit_sh bridge action inner_script
    polkit_sh="${NEXUS_INSTALL_ROOT}/lib/nexus-polkit.sh"
    [[ -f "$polkit_sh" ]] || polkit_sh="${ROOT}/lib/nexus-polkit.sh"
    # shellcheck source=/dev/null
    [[ -f "$polkit_sh" ]] && source "$polkit_sh"
    bridge="$(nexus_polkit_bridge_path 2>/dev/null || true)"
    action="$(nexus_polkit_action_for update 2>/dev/null || echo com.nexus.field.update)"
    if [[ -n "$bridge" && -x "$bridge" ]]; then
      mkdir -p "$NEXUS_STATE_DIR"
      inner_script="${NEXUS_STATE_DIR}/update-elevate-inner.sh"
      {
        printf '%s\n' '#!/bin/bash' 'set -euo pipefail'
        printf '%s\n' "export NEXUS_UPDATE_LOCK_TOKEN=$(printf '%q' "${TOKEN}")"
        printf '%s\n' "export NEXUS_UPDATE_PREVIOUS_VERSION=$(printf '%q' "${PREVIOUS}")"
        printf '%s\n' "export NEXUS_INSTALL_ROOT=$(printf '%q' "${NEXUS_INSTALL_ROOT}")"
        printf '%s\n' "export NEXUS_STATE_DIR=$(printf '%q' "${NEXUS_STATE_DIR}")"
        printf '%s\n' "$inner"
      } >"$inner_script"
      chmod 700 "$inner_script"
      pkexec --action "$action" "$bridge" run-update "$inner_script"
      local rc=$?
      rm -f "$inner_script"
      return $rc
    fi
    _log "sudo: pkexec fallback (bridge missing)"
    pkexec env \
      NEXUS_UPDATE_LOCK_TOKEN="${TOKEN}" \
      NEXUS_UPDATE_PREVIOUS_VERSION="${PREVIOUS}" \
      NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
      NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      bash -c "$inner"
    return $?
  fi
  if command -v zenity >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    local pw
    pw="$(zenity --password --title="NEXUS-Shield Update" \
      --text="Administrator password required to install release ${PREVIOUS} → ${TARGET}." 2>/dev/null || true)"
    if [[ -n "$pw" ]]; then
      _log "sudo: zenity password"
      printf '%s\n' "$pw" | sudo -S -E bash -c "$inner"
      return $?
    fi
    _log "sudo: zenity cancelled"
    return 3
  fi
  if command -v kdialog >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    local pw
    pw="$(kdialog --password "NEXUS-Shield needs sudo to install release ${PREVIOUS} → ${TARGET}" 2>/dev/null || true)"
    if [[ -n "$pw" ]]; then
      _log "sudo: kdialog password"
      printf '%s\n' "$pw" | sudo -S -E bash -c "$inner"
      return $?
    fi
    return 3
  fi
  if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    for term in x-terminal-emulator gnome-terminal konsole xfce4-terminal xterm; do
      if command -v "$term" >/dev/null 2>&1; then
        _log "sudo: terminal prompt via ${term}"
        "$term" -e bash -c "sudo -E bash -c $(printf '%q' "$inner"); echo; read -p 'Press Enter to close…'"
        return $?
      fi
    done
  fi
  _log "sudo: no prompt method — needs manual sudo"
  mkdir -p "$(dirname "$NEEDS_SUDO_JSON")"
  printf '{"needs_sudo":true,"message":"Administrator password required","command":"%s","target":"%s","previous":"%s","update_mode":"%s"}\n' \
    "cd '${STAGING}' && sudo bash install-all.sh" "$TARGET" "$PREVIOUS" "$UPDATE_MODE" >"$NEEDS_SUDO_JSON"
  return 3
}

_systemd_nexus_active() {
  command -v systemctl >/dev/null 2>&1 \
    && systemctl is-enabled nexus-genius.service >/dev/null 2>&1
}

_tree_standalone() {
  [[ "${NEXUS_FIELD_STANDALONE:-}" == "1" ]] \
    || [[ "$NEXUS_INSTALL_ROOT" == "$GIT_DIR" ]] \
    || [[ ! -x /usr/local/lib/nexus-shield/lib/nexus-daemon.sh ]]
}

_restart_standalone_panel() {
  declare -f nexus_panel_stop >/dev/null 2>&1 || return 1
  nexus_update_lock_phase restarting "--token=${TOKEN}" 2>/dev/null || true
  nexus_panel_stop 2>/dev/null || true
  sleep 1
  local launch_root="${NEXUS_UPDATE_EXTRACT_ROOT:-$GIT_DIR}"
  if [[ -f "${launch_root}/nexus.sh" ]]; then
    (cd "$launch_root" && nohup env NEXUS_INSTALL_ROOT="$launch_root" NEXUS_FIELD_STANDALONE=1 \
      NEXUS_STATE_DIR="$NEXUS_STATE_DIR" bash ./nexus.sh --no-browser --no-tray \
      >>"${NEXUS_STATE_DIR}/update-restart.log" 2>&1 &) || true
    sleep 2
  fi
}

_download_release() {
  local url="$1" dest="$2"
  _log "download release tarball: $url"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --retry 3 --retry-delay 2 -o "$dest" "$url"
    return $?
  fi
  if command -v wget >/dev/null 2>&1; then
    wget -q -O "$dest" "$url"
    return $?
  fi
  _log "curl/wget missing"
  return 1
}

_extract_release() {
  local archive="$1" dest="$2"
  mkdir -p "$dest"
  case "$archive" in
    *.h7e|*.h7)
      local unpack_py="${NEXUS_INSTALL_ROOT}/lib/field-h7-format.py"
      local unpack_sh="${NEXUS_INSTALL_ROOT}/scripts/field-h7e-extract.sh"
      [[ -x "$unpack_sh" ]] || unpack_sh="${NEXUS_INSTALL_ROOT}/scripts/ammoos-unpack-source.sh"
      if [[ -x "$unpack_sh" ]]; then
        bash "$unpack_sh" "$archive" "$dest"
        return $?
      fi
      if [[ -f "$unpack_py" ]]; then
        python3 "$unpack_py" extract "$archive" "$dest" >/dev/null
        return 0
      fi
      _log "H7e/H7 release archive requires field-h7-format.py or field-h7e-extract.sh"
      return 1
      ;;
    *.tar.gz|*.tgz)
      tar -xzf "$archive" -C "$dest"
      ;;
    *.tar)
      tar -xf "$archive" -C "$dest"
      ;;
    *)
      tar -xzf "$archive" -C "$dest"
      ;;
  esac
}

_find_extract_root() {
  local dest="$1"
  local ver="${TARGET#v}"
  local candidates=(
    "${dest}/ammoos-${ver}"
    "${dest}/ammoos-${ver}"
    "${dest}/nexus-shield-${ver}"
    "${dest}/nexus-shield-${TARGET}"
  )
  local c
  for c in "${candidates[@]}"; do
    if [[ -f "${c}/install-all.sh" ]]; then
      printf '%s' "$c"
      return 0
    fi
  done
  local found
  found="$(find "$dest" -maxdepth 2 -name install-all.sh -print -quit 2>/dev/null || true)"
  if [[ -n "$found" ]]; then
    dirname "$found"
    return 0
  fi
  return 1
}

_apply_release_installer() {
  [[ -n "$TARBALL_URL" ]] || { _log "missing NEXUS_UPDATE_TARBALL_URL"; return 1; }
  local archive_name
  archive_name="$(basename "${TARBALL_URL%%\?*}")"
  [[ -n "$archive_name" ]] || archive_name="nexus-shield-${TARGET}-source.tar.gz"
  local archive="${STAGING}/${archive_name}"
  mkdir -p "$STAGING"
  nexus_update_lock_phase download_tarball "--token=${TOKEN}" 2>/dev/null || true
  if ! _download_release "$TARBALL_URL" "$archive"; then
    _log "tarball download failed"
    return 1
  fi
  nexus_update_lock_phase extract_tarball "--token=${TOKEN}" 2>/dev/null || true
  local extract_base="${STAGING}/extract-${TARGET}"
  rm -rf "$extract_base"
  if ! _extract_release "$archive" "$extract_base"; then
    _log "tarball extract failed"
    return 1
  fi
  local extract_root
  extract_root="$(_find_extract_root "$extract_base")" || {
    _log "install-all.sh not found in extracted tree"
    return 1
  }
  export NEXUS_UPDATE_EXTRACT_ROOT="$extract_root"
  INSTALL_SH="${extract_root}/install-all.sh"
  [[ -f "$INSTALL_SH" ]] || { _log "install-all.sh missing in ${extract_root}"; return 1; }
  _log "release extract root=${extract_root}"
  nexus_update_lock_phase install_all "--token=${TOKEN}" 2>/dev/null || true
  local inner
  inner="export NEXUS_UPDATE_LOCK_TOKEN='${TOKEN}'; export NEXUS_UPDATE_PREVIOUS_VERSION='${PREVIOUS}'; export NEXUS_INSTALL_SRC='${extract_root}'; export SG_ROOT='${extract_root}'; cd '${extract_root}' && bash '${INSTALL_SH}'"
  _log "running install-all.sh from release tarball"
  if ! _run_with_sudo "$inner"; then
    local rc=$?
    if [[ $rc -eq 3 ]]; then
      _log "awaiting sudo — wrote ${NEEDS_SUDO_JSON}"
      nexus_update_lock_phase awaiting_sudo "--token=${TOKEN}" 2>/dev/null || true
      exit 3
    fi
    _log "install-all failed rc=${rc}"
    return 1
  fi
  return 0
}

_apply_incremental() {
  [[ -n "$CATALOG_URL" && -n "$TARBALL_URL" && -n "$TARGET" ]] || {
    _log "incremental: missing catalog url, tarball, or target"
    return 1
  }
  local inc_py="${NEXUS_INSTALL_ROOT}/lib/nexus-incremental-update.py"
  [[ -f "$inc_py" ]] || inc_py="${ROOT}/lib/nexus-incremental-update.py"
  [[ -f "$inc_py" ]] || { _log "incremental: nexus-incremental-update.py missing"; return 1; }
  nexus_update_lock_phase download_tarball "--token=${TOKEN}" 2>/dev/null || true
  _log "incremental apply catalog=${CATALOG_URL}"
  local py="${NEXUS_PYTHONG:-pythong}"
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    NEXUS_UPDATE_CATALOG_URL="${CATALOG_URL}" \
    NEXUS_UPDATE_TARBALL_URL="${TARBALL_URL}" \
    NEXUS_UPDATE_TARGET="${TARGET}" \
    "$py" "$inc_py" apply 2>&1 | tee -a "$LOG" || return 1
  nexus_update_lock_phase install_all "--token=${TOKEN}" 2>/dev/null || true
  return 0
}

_apply_git_tree() {
  if [[ -d "${GIT_DIR}/.git" ]]; then
    nexus_update_lock_phase git_fetch "--token=${TOKEN}" 2>/dev/null || true
    _log "git fetch"
    git -C "$GIT_DIR" fetch --tags origin 2>&1 | tee -a "$LOG" || true
    nexus_update_lock_phase git_pull "--token=${TOKEN}" 2>/dev/null || true
    _log "git pull"
    git -C "$GIT_DIR" pull --ff-only origin main 2>&1 | tee -a "$LOG" || {
      _log "git pull failed"
      return 1
    }
  fi
  INSTALL_SH="${GIT_DIR}/install-all.sh"
  [[ -f "$INSTALL_SH" ]] || INSTALL_SH="${GIT_DIR}/stealth_install.sh"
  [[ -f "$INSTALL_SH" ]] || { _log "install script missing in git tree"; return 1; }
  nexus_update_lock_phase install_all "--token=${TOKEN}" 2>/dev/null || true
  local inner
  inner="export NEXUS_UPDATE_LOCK_TOKEN='${TOKEN}'; export NEXUS_UPDATE_PREVIOUS_VERSION='${PREVIOUS}'; export NEXUS_INSTALL_SRC='${GIT_DIR}'; cd '${GIT_DIR}' && bash '${INSTALL_SH}'"
  _log "running ${INSTALL_SH} from git tree"
  if ! _run_with_sudo "$inner"; then
    local rc=$?
    if [[ $rc -eq 3 ]]; then
      nexus_update_lock_phase awaiting_sudo "--token=${TOKEN}" 2>/dev/null || true
      exit 3
    fi
    return 1
  fi
  return 0
}

main() {
  mkdir -p "$NEXUS_STATE_DIR" "$STAGING"
  : >>"$LOG"
  _log "update apply start mode=${UPDATE_MODE} target=${TARGET} previous=${PREVIOUS}"

  trap _cleanup EXIT
  [[ -n "$TOKEN" ]] || { _log "missing NEXUS_UPDATE_LOCK_TOKEN"; exit 1; }

  nexus_update_lock_adopt "$TOKEN" "nexus-update-apply" "download_tarball" | grep -q '"ok": true' \
    || { _log "lock adopt failed"; exit 1; }

  _heartbeat_loop &
  HB_PID=$!

  if _tree_standalone && ! _systemd_nexus_active && [[ "$UPDATE_MODE" != "release" || -z "$TARBALL_URL" ]]; then
    _log "standalone tree update — restart panel (no system install)"
    nexus_update_lock_phase restarting "--token=${TOKEN}" 2>/dev/null || true
    _restart_standalone_panel || true
    _log "standalone update complete"
    exit 0
  fi

  local applied=0
  if [[ "$APPLY_VIA" == "incremental" && -n "$CATALOG_URL" && -n "$TARBALL_URL" ]]; then
    if _apply_incremental; then
      applied=1
    else
      _log "incremental apply failed — falling back to full release installer"
    fi
  fi
  if [[ $applied -eq 0 && "$UPDATE_MODE" == "release" && -n "$TARBALL_URL" ]]; then
    if _apply_release_installer; then
      applied=1
    else
      _log "release installer failed — trying git fallback if available"
    fi
  fi
  if [[ $applied -eq 0 ]]; then
    if [[ -d "${GIT_DIR}/.git" ]] || [[ -f "${GIT_DIR}/install-all.sh" ]]; then
      _apply_git_tree || exit 1
    else
      _log "no release tarball and no git tree"
      exit 1
    fi
  fi

  nexus_update_lock_phase starting_service "--token=${TOKEN}" 2>/dev/null || true
  if _systemd_nexus_active; then
    _log "systemd restart nexus-genius"
    if [[ "$(id -u)" -eq 0 ]]; then
      systemctl restart nexus-genius.service 2>&1 | tee -a "$LOG" || true
    elif sudo -n systemctl restart nexus-genius.service 2>&1 | tee -a "$LOG"; then
      :
    else
      _run_with_sudo "systemctl restart nexus-genius.service" || true
    fi
  else
    _restart_standalone_panel || true
  fi

  _log "update apply complete ${PREVIOUS} → ${TARGET} mode=${UPDATE_MODE}"
  local post_py="${NEXUS_INSTALL_ROOT}/lib/ammoos-update-inplace.py"
  if [[ -f "$post_py" ]]; then
    local py="${NEXUS_PYTHONG:-pythong}"
    command -v "$py" >/dev/null 2>&1 || py="python3"
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      "$py" "$post_py" post-update >>"$LOG" 2>&1 || true
  fi
  exit 0
}

main "$@"