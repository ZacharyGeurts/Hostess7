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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-await.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Event-driven waits — no sleep(1); all waits capped at NEXUS_AWAIT_MAX_SEC (default 5).

NEXUS_AWAIT_MAX_SEC="${NEXUS_AWAIT_MAX_SEC:-5}"

nexus_await_clamp() {
  local sec="${1:-1}"
  local max="${NEXUS_AWAIT_MAX_SEC:-5}"
  if declare -f nexus_field_max_enabled >/dev/null 2>&1 && nexus_field_max_enabled; then
    max="${NEXUS_AWAIT_MAX_SEC:-1}"
    if [[ "$sec" -gt "$max" ]]; then
      sec="$max"
    fi
    if [[ "$sec" -lt 0 ]]; then
      sec=0
    fi
    printf '%s' "$sec"
    return 0
  fi
  if [[ "$sec" -gt "$max" ]]; then
    sec="$max"
  fi
  if [[ "$sec" -lt 1 ]]; then
    sec=1
  fi
  printf '%s' "$sec"
}

nexus_await_seconds() {
  local sec
  sec="$(nexus_await_clamp "${1:-1}")"
  local watch="${2:-${NEXUS_STATE_DIR:-/tmp}}"
  [[ -d "$watch" ]] || watch="/tmp"
  if [[ "$sec" -eq 0 ]]; then
    return 0
  fi
  if command -v inotifywait >/dev/null 2>&1; then
    inotifywait -r -t "$sec" -e modify,create,delete,move,close_write,open "$watch" \
      >/dev/null 2>&1 || true
    return 0
  fi
  read -r -t "$sec" _ </dev/null || true
}

nexus_await_curl_ready() {
  local url="$1"
  local sec retries
  sec="$(nexus_await_clamp "${2:-5}")"
  retries="$(nexus_await_clamp "${3:-$sec}")"
  curl -s --connect-timeout 2 --max-time "$sec" \
    --retry "$retries" --retry-all-errors --retry-delay 1 \
    "$url" >/dev/null 2>&1
}

nexus_await_port_free() {
  local port="$1"
  local budget
  budget="$(nexus_await_clamp "${2:-5}")"
  local n=0
  while (( n < budget )); do
    local busy=0
    if command -v ss >/dev/null 2>&1; then
      ss -H -l -t "sport = :${port}" 2>/dev/null | grep -q . && busy=1
    elif command -v fuser >/dev/null 2>&1; then
      fuser "${port}/tcp" >/dev/null 2>&1 && busy=1
    else
      return 0
    fi
    [[ "$busy" -eq 0 ]] && return 0
    nexus_await_seconds 1 "${NEXUS_STATE_DIR:-/tmp}"
    ((n++)) || true
  done
}

nexus_await_pid_exit() {
  local pid="$1"
  local sec
  sec="$(nexus_await_clamp "${2:-5}")"
  if command -v timeout >/dev/null 2>&1 && timeout "$sec" tail -f --pid="$pid" /dev/null >/dev/null 2>&1; then
    return 0
  fi
  local deadline=$((SECONDS + sec))
  while kill -0 "$pid" 2>/dev/null && (( SECONDS < deadline )); do
    nexus_await_seconds 1
  done
}

nexus_await_cpu_budget() {
  local sec
  sec="$(nexus_await_clamp "${1:-5}")"
  local deadline=$((SECONDS + sec))
  while (( SECONDS < deadline )); do
    nexus_cpu_budget_ok && return 0
    nexus_await_seconds 1 "${NEXUS_STATE_DIR:-/tmp}"
  done
  return 1
}
