#!/usr/bin/env bash
# secure_clipboard.sh — RAM-only, auto-wipe, no history. Not a cloud clipboard manager.
set -euo pipefail

# Tunables (override in ~/.config/secure-clipboard/env)
: "${SCLIP_TTL_SEC:=45}"          # auto-clear OS clipboard after paste window
: "${SCLIP_VAULT_TTL_SEC:=300}"   # encrypted vault expires even if never pasted
: "${SCLIP_SHM_DIR:=/dev/shm/sclip-$$USER}"
: "${SCLIP_PASSFILE:=${HOME}/.config/secure-clipboard/passphrase}"

CFG_DIR="${HOME}/.config/secure-clipboard"
ENV_FILE="${CFG_DIR}/env"
[[ -f "${ENV_FILE}" ]] && source "${ENV_FILE}"

usage() {
  cat <<'EOF'
secure clipboard (sclip) — local RAM vault, auto-wipe, no history

  sclip init              create vault key + config dir
  sclip copy [text]       copy stdin or arg → encrypted vault → OS clipboard
  sclip paste             decrypt vault → stdout (does NOT leave extra copies)
  sclip paste-clip        paste to stdout AND put on OS clipboard once
  sclip clear             wipe vault + OS clipboard (primary + selection)
  sclip status            show TTL / vault state (no secret content)
  sclip ttl N             set auto-wipe seconds (default 45)
  sclip disable-managers  stop/mask CopyQ Parcellite clipman etc.

Security model:
  - Secrets live in /dev/shm (RAM), AES-256-CBC + PBKDF2, never touch disk plaintext
  - OS clipboard auto-clears after TTL (background watcher)
  - No clipboard history, no sync, no cloud
  - Plaintext only (no images/files — less leak surface)

Shell aliases (add to ~/.bashrc):
  alias sclip='bash /path/to/memes/Security/secure_clipboard.sh'
  alias scopy='sclip copy'
  alias spaste='sclip paste'
  alias sclear='sclip clear'
EOF
}

need_openssl() {
  command -v openssl >/dev/null 2>&1 || {
    echo "sclip: need openssl — sudo apt install openssl" >&2
    exit 1
  }
}

clip_backend() {
  if [[ -n "${WAYLAND_DISPLAY:-}" ]] && command -v wl-copy >/dev/null 2>&1; then
    echo wayland
  elif command -v xclip >/dev/null 2>&1; then
    echo xclip
  elif command -v xsel >/dev/null 2>&1; then
    echo xsel
  else
    echo none
  fi
}

os_clip_set() {
  local text="$1"
  local be
  be="$(clip_backend)"
  case "${be}" in
    wayland) printf '%s' "${text}" | wl-copy -n ;;
    xclip)   printf '%s' "${text}" | xclip -selection clipboard -in ;;
    xsel)    printf '%s' "${text}" | xsel --clipboard --input ;;
    none)
      echo "sclip: no wl-copy/xclip/xsel — install one:" >&2
      echo "  sudo apt install wl-clipboard   # Wayland" >&2
      echo "  sudo apt install xclip            # X11" >&2
      return 1
      ;;
  esac
}

os_clip_clear() {
  local be
  be="$(clip_backend)"
  case "${be}" in
    wayland)
      wl-copy -n </dev/null 2>/dev/null || true
      wl-copy -p -n </dev/null 2>/dev/null || true
      ;;
    xclip)
      : | xclip -selection clipboard -in 2>/dev/null || true
      : | xclip -selection primary -in 2>/dev/null || true
      ;;
    xsel)
      : | xsel --clipboard --input 2>/dev/null || true
      : | xsel --primary --input 2>/dev/null || true
      ;;
  esac
}

vault_paths() {
  VAULT_DIR="${SCLIP_SHM_DIR}"
  VAULT_FILE="${VAULT_DIR}/vault.enc"
  VAULT_META="${VAULT_DIR}/meta"
  WATCH_PID="${VAULT_DIR}/watcher.pid"
  mkdir -p "${VAULT_DIR}"
  chmod 700 "${VAULT_DIR}"
}

read_pass() {
  if [[ -f "${SCLIP_PASSFILE}" ]]; then
    cat "${SCLIP_PASSFILE}"
    return
  fi
  if [[ -t 0 ]] && [[ -t 2 ]]; then
    read -r -s -p "sclip vault passphrase: " p1 </dev/tty
    echo "" >&2
    printf '%s' "${p1}"
    return
  fi
  echo "sclip: no passphrase file and not a TTY — run: sclip init" >&2
  exit 1
}

vault_encrypt() {
  local plain="$1"
  local pass="$2"
  printf '%s' "${plain}" | openssl enc -aes-256-cbc -salt -pbkdf2 -iter 250000 \
    -pass pass:"${pass}" -out "${VAULT_FILE}"
  date +%s > "${VAULT_META}"
}

vault_decrypt() {
  local pass="$1"
  openssl enc -aes-256-cbc -d -pbkdf2 -iter 250000 \
    -pass pass:"${pass}" -in "${VAULT_FILE}" 2>/dev/null
}

vault_expired() {
  [[ -f "${VAULT_META}" ]] || return 0
  local now created
  now="$(date +%s)"
  created="$(cat "${VAULT_META}")"
  (( now - created > SCLIP_VAULT_TTL_SEC ))
}

stop_watcher() {
  vault_paths
  if [[ -f "${WATCH_PID}" ]]; then
    local pid
    pid="$(cat "${WATCH_PID}" 2>/dev/null || true)"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
    rm -f "${WATCH_PID}"
  fi
}

start_watcher() {
  stop_watcher
  vault_paths
  (
    sleep "${SCLIP_TTL_SEC}"
    os_clip_clear
    rm -f "${VAULT_FILE}" "${VAULT_META}"
    rm -f "${WATCH_PID}"
  ) &
  echo $! > "${WATCH_PID}"
}

cmd_init() {
  need_openssl
  mkdir -p "${CFG_DIR}"
  chmod 700 "${CFG_DIR}"
  if [[ ! -f "${SCLIP_PASSFILE}" ]]; then
    echo "Choose a vault passphrase (stored at ${SCLIP_PASSFILE}, mode 600):"
    read -r -s p1
    echo
    read -r -s p2
    echo
    [[ "${p1}" == "${p2}" ]] || { echo "passphrases mismatch" >&2; exit 1; }
    printf '%s' "${p1}" > "${SCLIP_PASSFILE}"
    chmod 600 "${SCLIP_PASSFILE}"
    echo "passphrase saved."
  else
    echo "passphrase already exists: ${SCLIP_PASSFILE}"
  fi
  cat > "${ENV_FILE}" <<EOF
# secure-clipboard config
SCLIP_TTL_SEC=${SCLIP_TTL_SEC}
SCLIP_VAULT_TTL_SEC=${SCLIP_VAULT_TTL_SEC}
SCLIP_SHM_DIR=${SCLIP_SHM_DIR}
EOF
  chmod 600 "${ENV_FILE}"
  echo "config: ${ENV_FILE}"
  cmd_disable_managers
}

cmd_copy() {
  need_openssl
  vault_paths
  local plain pass
  if [[ $# -gt 0 ]]; then
    plain="$*"
  else
    plain="$(cat)"
  fi
  [[ -n "${plain}" ]] || { echo "sclip: nothing to copy" >&2; exit 1; }
  pass="$(read_pass)"
  vault_encrypt "${plain}" "${pass}"
  os_clip_set "${plain}"
  # scrub shell copy of plaintext ASAP
  plain=""
  pass=""
  start_watcher
  echo "sclip: copied — OS clipboard wipes in ${SCLIP_TTL_SEC}s, vault in ${SCLIP_VAULT_TTL_SEC}s"
}

cmd_paste() {
  need_openssl
  vault_paths
  [[ -f "${VAULT_FILE}" ]] || { echo "sclip: vault empty" >&2; exit 1; }
  vault_expired && { cmd_clear; echo "sclip: vault expired" >&2; exit 1; }
  local pass
  pass="$(read_pass)"
  vault_decrypt "${pass}"
  pass=""
}

cmd_paste_clip() {
  local plain
  plain="$(cmd_paste)"
  os_clip_set "${plain}"
  printf '%s' "${plain}"
  plain=""
  start_watcher
}

cmd_clear() {
  stop_watcher
  vault_paths
  rm -f "${VAULT_FILE}" "${VAULT_META}"
  os_clip_clear
  echo "sclip: vault + OS clipboard cleared"
}

cmd_status() {
  vault_paths
  local be
  be="$(clip_backend)"
  echo "backend: ${be}"
  echo "shm vault: ${VAULT_DIR}"
  echo "ttl_sec: ${SCLIP_TTL_SEC}  vault_ttl_sec: ${SCLIP_VAULT_TTL_SEC}"
  if [[ -f "${VAULT_FILE}" ]]; then
    if vault_expired; then
      echo "vault: EXPIRED (run sclip clear)"
    else
      echo "vault: active ($(wc -c < "${VAULT_FILE}") bytes encrypted)"
    fi
  else
    echo "vault: empty"
  fi
  if [[ -f "${WATCH_PID}" ]] && kill -0 "$(cat "${WATCH_PID}")" 2>/dev/null; then
    echo "watcher: running (pid $(cat "${WATCH_PID}"))"
  else
    echo "watcher: off"
  fi
}

cmd_ttl() {
  [[ $# -eq 1 ]] || { usage; exit 1; }
  mkdir -p "${CFG_DIR}"
  SCLIP_TTL_SEC="$1"
  cat > "${ENV_FILE}" <<EOF
SCLIP_TTL_SEC=${SCLIP_TTL_SEC}
SCLIP_VAULT_TTL_SEC=${SCLIP_VAULT_TTL_SEC}
SCLIP_SHM_DIR=${SCLIP_SHM_DIR}
EOF
  echo "sclip: clipboard TTL set to ${SCLIP_TTL_SEC}s"
}

cmd_disable_managers() {
  echo "Disabling leaky clipboard managers (history/sync)..."
  for svc in copyq parcellite clipit greenclip diodon klipper; do
    systemctl --user stop "${svc}" 2>/dev/null || true
    systemctl --user mask "${svc}" 2>/dev/null || true
    systemctl --user disable "${svc}" 2>/dev/null || true
  done
  pkill -x copyq 2>/dev/null || true
  pkill -x parcellite 2>/dev/null || true
  pkill -x clipman 2>/dev/null || true
  pkill -x greenclip 2>/dev/null || true
  echo "Done. Use sclip only — no CopyQ/Parcellite history."
}

main() {
  local cmd="${1:-}"
  shift || true
  case "${cmd}" in
    init)              cmd_init ;;
    copy)              cmd_copy "$@" ;;
    paste)             cmd_paste ;;
    paste-clip)        cmd_paste_clip ;;
    clear)             cmd_clear ;;
    status)            cmd_status ;;
    ttl)               cmd_ttl "$@" ;;
    disable-managers)  cmd_disable_managers ;;
    -h|--help|help|"") usage ;;
    *) echo "unknown: ${cmd}" >&2; usage; exit 1 ;;
  esac
}

main "$@"