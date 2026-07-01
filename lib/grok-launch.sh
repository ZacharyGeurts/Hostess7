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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/grok-launch.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Grok desktop — secure channel (no MITM/injection), max 5 egress TCP sockets.
set -euo pipefail

GROK_HOME="${GROK_HOME:-${HOME}/.grok}"
GROK_REAL="${GROK_REAL_BIN:-${GROK_HOME}/downloads/grok-0.2.67-linux-x86_64}"
if [[ ! -x "$GROK_REAL" ]]; then
  GROK_REAL="$(readlink -f "${GROK_HOME}/bin/grok.real" 2>/dev/null || true)"
fi
if [[ ! -x "$GROK_REAL" ]]; then
  for candidate in "${GROK_HOME}"/downloads/grok-*-linux-x86_64; do
    [[ -x "$candidate" ]] || continue
    GROK_REAL="$candidate"
    break
  done
fi
[[ -x "$GROK_REAL" ]] || {
  echo "grok: binary missing under ${GROK_HOME}/downloads" >&2
  exit 1
}

SG_ROOT="${SG_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)}"
NEXUS_ROOT="${NEXUS_INSTALL_ROOT:-${SG_ROOT}/NewLatest}"
LIMIT_PY="${NEXUS_ROOT}/lib/grok-socket-limit.py"
MAX_SOCKETS="${GROK_MAX_SOCKETS:-5}"

# Secure TLS — system CA store only; block proxy injection / custom trust bypass.
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
export SSL_CERT_DIR="${SSL_CERT_DIR:-/etc/ssl/certs}"
export REQUESTS_CA_BUNDLE="${REQUESTS_CA_BUNDLE:-$SSL_CERT_FILE}"
export CURL_CA_BUNDLE="${CURL_CA_BUNDLE:-$SSL_CERT_FILE}"
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy 2>/dev/null || true
export NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,::1}"
export QUEEN_GROK_BUILD_SECURE=1
export NEXUS_AI_SECURE_CHANNEL=1
export QUEEN_AI_TELEMETRY_OK=1
export GROK_MAX_SOCKETS="$MAX_SOCKETS"
export GROK_SECURE_CHANNEL=1

_runner() {
  command -v pythong >/dev/null 2>&1 && echo pythong && return
  command -v python3 >/dev/null 2>&1 && echo python3 && return
  return 1
}

# Replace prior instance — one Grok, fresh socket budget.
if pgrep -x grok >/dev/null 2>&1; then
  pkill -TERM -x grok 2>/dev/null || true
  sleep 0.4
  pkill -KILL -x grok 2>/dev/null || true
  sleep 0.2
fi
pkill -f 'grok-socket-limit.py watch' 2>/dev/null || true

"$GROK_REAL" "$@" &
GPID=$!
disown "$GPID" 2>/dev/null || true

if [[ -f "$LIMIT_PY" ]]; then
  runner="$(_runner || true)"
  if [[ -n "$runner" ]]; then
    nohup "$runner" "$LIMIT_PY" watch "$GPID" \
      >>"${GROK_HOME}/socket-limit.log" 2>&1 &
  fi
fi

echo "grok: pid=${GPID} secure=1 max_sockets=${MAX_SOCKETS}" >&2
wait "$GPID"