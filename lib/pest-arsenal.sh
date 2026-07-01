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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/pest-arsenal.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Pest Arsenal — block, stop, quarantine host pests (operator-initiated only).

NEXUS_PEST_ACTIONS="${NEXUS_PEST_ACTIONS:-${NEXUS_STATE_DIR}/pest-actions.tsv}"
NEXUS_PEST_QUARANTINE="${NEXUS_PEST_QUARANTINE:-${NEXUS_STATE_DIR}/quarantine}"

nexus_pest_init() {
  mkdir -p "$NEXUS_PEST_QUARANTINE" 2>/dev/null || true
  chmod 750 "$NEXUS_PEST_QUARANTINE" 2>/dev/null || true
  [[ -f "$NEXUS_PEST_ACTIONS" ]] || printf 'id\tts\tip\tpid\tvector\tactions\tresult\tdetail\n' >"$NEXUS_PEST_ACTIONS"
}

nexus_pest_make_id() {
  printf 'pest-%s-%s' "$(date +%s)" "$(printf '%s' "${1:-x}" | md5sum 2>/dev/null | cut -c1-8 || echo rand)"
}

nexus_pest_is_sacred_comm() {
  local comm="${1:-}"
  case "$comm" in
    systemd|init|kthreadd|sshd|dbus-daemon|NetworkManager|pipewire|wireplumber|\
    nexus-genius|nexus-daemon|pythong|firefox|chrome|chromium|brave|vivaldi|msedge|\
    thunderbird|evolution|gnome-shell|Xorg|wayland|sddm|gdm|lightdm|polkitd|\
    containerd|dockerd|kubelet|systemd-journald|systemd-logind|systemd-resolved|\
    systemd-networkd|systemd-udevd|rsyslogd|cron|atd|agetty|login|bash|sudo|su)
      return 0 ;;
  esac
  return 1
}

nexus_pest_is_sacred_pid() {
  local pid="${1:-}"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 0
  [[ "$pid" -le 2 ]] && return 0
  local comm exe cmdline
  comm="$(cat "/proc/${pid}/comm" 2>/dev/null | tr -d '\0')"
  exe="$(readlink -f "/proc/${pid}/exe" 2>/dev/null || true)"
  cmdline="$(tr '\0' ' ' <"/proc/${pid}/cmdline" 2>/dev/null || true)"
  nexus_pest_is_sacred_comm "$comm" && return 0
  [[ "$exe" == *nexus-shield* || "$exe" == *nexus-daemon* || "$exe" == *threat-panel* ]] && return 0
  [[ "$cmdline" == *nexus-genius* || "$cmdline" == *genius_shield* ]] && return 0
  return 1
}

nexus_pest_kill_pid() {
  local pid="${1:-}" reason="${2:-pest}"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  nexus_pest_is_sacred_pid "$pid" && {
    nexus_log "WARN" "pest-arsenal" "KILL_REFUSED sacred pid=${pid}"
    return 1
  }
  kill -TERM "$pid" 2>/dev/null || return 1
  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    kill -KILL "$pid" 2>/dev/null || true
  fi
  nexus_log "ALERT" "pest-arsenal" "PEST_KILL pid=${pid} reason=${reason}"
  return 0
}

nexus_pest_quarantine_path() {
  local path="${1:-}" reason="${2:-pest}"
  [[ -n "$path" && -f "$path" ]] || return 1
  case "$path" in
    /tmp/*|/dev/shm/*|/var/tmp/*) ;;
    *) nexus_log "WARN" "pest-arsenal" "QUARANTINE_REFUSED path=${path}"
       return 1 ;;
  esac
  nexus_pest_init
  local base dest
  base="$(basename "$path")"
  dest="${NEXUS_PEST_QUARANTINE}/${base}.$(date +%s).quarantined"
  mv -f "$path" "$dest" 2>/dev/null || return 1
  chmod 600 "$dest" 2>/dev/null || true
  nexus_log "ALERT" "pest-arsenal" "PEST_QUARANTINE src=${path} dest=${dest} reason=${reason}"
  printf '%s\n' "$dest"
  return 0
}

nexus_pest_block_ip() {
  local ip="${1:-}" duration="${2:-forever}" reason="${3:-pest}"
  [[ -n "$ip" ]] || return 1
  if declare -f nexus_firewall_refuse_block_self >/dev/null 2>&1 && nexus_firewall_refuse_block_self "$ip"; then
    nexus_log "WARN" "pest-arsenal" "BLOCK_REFUSED self ip=${ip}"
    return 1
  fi
  if [[ "$duration" == "forever" || "$duration" == "permanent" ]]; then
    nexus_firewall_block_ip_forever out "$ip" "$reason"
  else
    nexus_firewall_block_ip out "$ip" "${NEXUS_FIREWALL_BLOCK_DURATION:-86400}" "$reason"
  fi
}

nexus_pest_record_action() {
  local id="$1" ip="$2" pid="$3" vector="$4" actions="$5" result="$6" detail="$7"
  nexus_pest_init
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$id" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$ip" "$pid" "$vector" "$actions" "$result" "$detail" \
    >>"$NEXUS_PEST_ACTIONS"
  chmod 640 "$NEXUS_PEST_ACTIONS" 2>/dev/null || true
}

nexus_pest_eradicate() {
  local ip="${1:-}" pid="${2:-0}" vector="${3:-HARM_CANDIDATE}" exe="${4:-}"
  local id results=() detail="" ok=1

  if [[ -z "$exe" && "$pid" =~ ^[0-9]+$ && "$pid" -gt 0 ]]; then
    exe="$(readlink -f "/proc/${pid}/exe" 2>/dev/null || true)"
  fi

  id="$(nexus_pest_make_id "${ip}_${pid}")"
  [[ -n "$ip" ]] && {
    if nexus_pest_block_ip "$ip" forever "pest-eradicate"; then
      results+=("block_ok")
    else
      results+=("block_skip")
      ok=0
    fi
  }

  if [[ "$pid" =~ ^[0-9]+$ && "$pid" -gt 0 ]]; then
    if nexus_pest_kill_pid "$pid" "$vector"; then
      results+=("kill_ok")
    else
      results+=("kill_skip")
    fi
  fi

  if [[ -n "$exe" && -f "$exe" ]]; then
    if nexus_pest_quarantine_path "$exe" "$vector" >/dev/null; then
      results+=("quarantine_ok")
    else
      results+=("quarantine_skip")
    fi
  fi

  detail="$(IFS=,; echo "${results[*]}")"
  nexus_pest_record_action "$id" "$ip" "$pid" "$vector" "eradicate" "$detail" "operator"
  nexus_log "ALERT" "pest-arsenal" "PEST_ERADICATE id=${id} ip=${ip} pid=${pid} vector=${vector} result=${detail}"
  [[ "$detail" == *"_ok"* ]]
}

nexus_pest_actions_json() {
  local limit="${1:-20}" id ts ip pid vector actions result detail
  nexus_pest_init
  printf '['
  local first=1 count=0
  while IFS=$'\t' read -r id ts ip pid vector actions result detail; do
    [[ -n "$id" && "$id" != "id" ]] || continue
    count=$((count + 1))
    [[ "$count" -le "$limit" ]] || break
    [[ "$first" -eq 1 ]] || printf ','
    first=0
    printf '{"id":"%s","ts":"%s","ip":"%s","pid":"%s","vector":"%s","actions":"%s","result":"%s","detail":"%s"}' \
      "$id" "$ts" "$ip" "$pid" "$vector" "$actions" "$result" "$detail"
  done < <(tail -n "$((limit + 1))" "$NEXUS_PEST_ACTIONS" 2>/dev/null | tac)
  printf ']'
}