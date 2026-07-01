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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/impl/ammoos-direct-start.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Direct-start AmmoOS panel + Queen (bypasses nexus boot-impl hang).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"
export SG_ROOT="${SG}"
export NEXUS_INSTALL_ROOT="${ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
export TDIR="${TDIR:-${HOME}/.grok/projects/home-default-Desktop-SG/terminals}"
export NEXUS_ZNETWORK="${NEXUS_ZNETWORK:-1}"
export NEXUS_ZNETWORK_PROMPT=0
export NEXUS_FIELD_STANDALONE=1
export ZNETWORK_RELAYER="${ZNETWORK_RELAYER:-1}"
export ZNETWORK_UNDERHOOK=0
export ZNETWORK_INTERNET_PIPE_TARGET="${ZNETWORK_INTERNET_PIPE_TARGET:-100}"
export ZNETWORK_MODE="${ZNETWORK_MODE:-ACTIVE}"
export ZNETWORK_PROTECTION_ONLY="${ZNETWORK_PROTECTION_ONLY:-0}"
export KILROY_PC_CORE=1
export KILROY_ZNETWORK_ABSORBED=1
export AMMOOS_INSIDE_QUEEN=0
export QUEEN_STANDALONE_BROWSER=1
export AMMOOS_DESKTOP_RTX=AMOURANTHRTX
export QUEEN_BROWSER_ONLY="${QUEEN_BROWSER_ONLY:-1}"
export QUEEN_BROWSER_STRIPPED="${QUEEN_BROWSER_STRIPPED:-1}"
export QUEEN_BOOT_OS="${QUEEN_BOOT_OS:-0}"
export NEXUS_C2_DESKTOP_LAUNCH="${NEXUS_C2_DESKTOP_LAUNCH:-0}"
export QUEEN_BROWSER_HOME="${QUEEN_BROWSER_HOME:-http://127.0.0.1:9477/field}"
export QUEEN_BROWSER_START="${QUEEN_BROWSER_START:-$QUEEN_BROWSER_HOME}"
export QUEEN_NO_OS_BROWSER="${QUEEN_NO_OS_BROWSER:-1}"
export NEXUS_FIELD_BROWSER_QUEEN="${NEXUS_FIELD_BROWSER_QUEEN:-1}"
export NEXUS_FIELD_DNS="${NEXUS_FIELD_DNS:-1}"
export NEXUS_FIELD_DHCP="${NEXUS_FIELD_DHCP:-1}"
export NEXUS_FIELD_LOCAL_DNS_CONNECT="${NEXUS_FIELD_LOCAL_DNS_CONNECT:-1}"
export DISPLAY="${DISPLAY:-:0}"
mkdir -p "$NEXUS_STATE_DIR" "$TDIR"
PY=$(command -v pythong || command -v python3)
if [[ ! -f "$NEXUS_STATE_DIR/znetwork-operator.json" ]] || ! grep -q '"choice"[[:space:]]*:[[:space:]]*"yes"' "$NEXUS_STATE_DIR/znetwork-operator.json" 2>/dev/null; then
  NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" \
    ZNETWORK_RELAYER="$ZNETWORK_RELAYER" ZNETWORK_MODE="$ZNETWORK_MODE" \
    "$PY" "$ROOT/lib/znetwork-orchestrator.py" mark-running >/dev/null 2>&1 || true
fi
GROKPY="${SG}/GrokPy/driver/grokpy_driver.py"
if [[ ! -x "$GROKPY" ]]; then
  GROKPY="${ROOT}/Grok16/python/driver/gpy16_driver.py"
fi
if [[ ! -x "$GROKPY" ]]; then
  GROKPY="$(command -v python3)"
fi
# shellcheck source=/dev/null
[[ -f "${ROOT}/lib/field-dns.sh" ]] && source "${ROOT}/lib/field-dns.sh"
declare -f nexus_field_services_boot >/dev/null 2>&1 && nexus_field_services_boot || true

if [[ ! -f "$NEXUS_STATE_DIR/threat-panel.json" ]]; then
  NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" \
    "$PY" "$ROOT/scripts/panel-json-assemble.py" >/dev/null 2>&1 || true
fi
if ! pgrep -f 'threat-panel-http.py.*9477' >/dev/null 2>&1; then
  nohup env NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" \
    SG_ROOT="$SG_ROOT" TDIR="$TDIR" \
    "$GROKPY" "$ROOT/lib/threat-panel-http.py" 9477 \
    "$ROOT/panel" "$NEXUS_STATE_DIR/threat-panel.json" \
    >>"$NEXUS_STATE_DIR/panel-http.log" 2>&1 &
fi
if ! pgrep -f 'Queen/lib/queen-world.py' >/dev/null 2>&1; then
  nohup env SG_ROOT="$SG_ROOT" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" TDIR="$TDIR" \
    "$GROKPY" "$ROOT/Queen/lib/queen-world.py" --daemon \
    >>"$NEXUS_STATE_DIR/queen-world.log" 2>&1 &
fi
p=000 q=000
for _ in $(seq 1 40); do
  p=$(curl -sf -o /dev/null -w '%{http_code}' --connect-timeout 1 http://127.0.0.1:9477/field 2>/dev/null || echo 000)
  q=$(curl -sf -o /dev/null -w '%{http_code}' --connect-timeout 1 http://127.0.0.1:9481/api/status 2>/dev/null || echo 000)
  [[ "$p" == "200" && "$q" == "200" ]] && break
  sleep 0.25
done
echo "panel=$p queen=$q TDIR=$TDIR"
ss -tlnp 2>/dev/null | grep -E ':9477|:9481' || true
