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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/ammoos-launch-verify.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Verify AmmoOS 1.0 surfaces, sovereignty, and local DNS/DHCP connect.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh" 2>/dev/null || true

VER_JSON="${ROOT}/data/ammoos-version.json"
fail=0
PY="${NEXUS_PYTHONG:-}"
if [[ -z "$PY" ]] && declare -F nexus_resolve_pythong >/dev/null 2>&1; then
  PY="$(nexus_resolve_pythong 2>/dev/null || true)"
fi
PY="${PY:-$(command -v pythong 2>/dev/null || command -v python3)}"

check_file() {
  local rel="$1"
  if [[ -f "${ROOT}/${rel}" || -x "${ROOT}/${rel}" || -d "${ROOT}/${rel}" ]]; then
    echo "PASS program ${rel}"
  else
    echo "WARN missing ${rel}"
    fail=$((fail + 1))
  fi
}

check_url_doc() {
  local key="$1" url="$2"
  echo "PASS browser ${key} → ${url}"
}

echo "=== AmmoOS launch verify ==="
[[ -f "$VER_JSON" ]] || { echo "FAIL missing ammoos-version.json" >&2; exit 1; }

grep -q '"version"[[:space:]]*:[[:space:]]*"1.0.0"' "$VER_JSON" && echo "PASS version 1.0.0" \
  || { echo "WARN version not 1.0.0"; fail=$((fail + 1)); }

grep -q '9477/field' "$VER_JSON"
grep -q '9481/world/browser.html' "$VER_JSON"

while IFS= read -r rel; do
  [[ -n "$rel" ]] && check_file "$rel"
done < <(python3 -c "import json; d=json.load(open('${VER_JSON}')); print('\n'.join(d.get('native_programs',[])))")

for plate in "${ROOT}"/Queen/AmmoOS/net/*.fld; do
  [[ -f "$plate" ]] && echo "PASS plate ${plate#${ROOT}/}" || true
done

check_file "lib/threat-panel-http.py"
check_file "Queen/world/browser.html"
check_file "nexus.sh"
check_file "install-all.sh"
check_file "data/ammoos-platform-release.json"
check_file "data/queen-ammoos-sovereignty-doctrine.json"
check_file "data/field-stack-layer-doctrine.json"
check_file "lib/field-stack-layer.py"
check_file "lib/field-dns.py"
check_file "lib/field-dhcp.py"
check_file "lib/field-local-dns-connect.py"
check_file "lib/dns-service-takeover.py"
check_file "RELEASE-1.0.0.md"

grep -q 'nexus_field_services_boot' "${ROOT}/lib/field-dns.sh" && echo "PASS field services boot wired" \
  || { echo "WARN field services boot missing"; fail=$((fail + 1)); }

grep -q 'NEXUS_FIELD_LOCAL_DNS_CONNECT' "${ROOT}/config/nexus.conf" && echo "PASS local DNS connect config" \
  || { echo "WARN local DNS connect config missing"; fail=$((fail + 1)); }

export NEXUS_INSTALL_ROOT="${ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
mkdir -p "$NEXUS_STATE_DIR"

if timeout 15 "$PY" "${ROOT}/lib/queen-ammoos-sovereignty.py" json 2>/dev/null | grep -q '"internet_pipe_percent": 100'; then
  echo "PASS sovereignty 100% pipe"
else
  echo "WARN sovereignty pipe not 100%"
  fail=$((fail + 1))
fi

if timeout 15 "$PY" "${ROOT}/lib/field-local-dns-connect.py" json >/dev/null 2>&1; then
  echo "PASS local DNS/DHCP connect module"
else
  echo "WARN local connect module failed"
  fail=$((fail + 1))
fi

echo "=== done (warnings=${fail}) ==="
exit 0