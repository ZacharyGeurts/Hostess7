# AmmoLang snippet harness — shared env, nexus libs, PY/g16 runners (source only).
_aml_harness_dir="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "${_aml_harness_dir}/../../.." && pwd)}"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
export SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}"
export GROK16_ROOT="${GROK16_ROOT:-${SG_ROOT}/Grok16}"
export ROOT AML_INLINE=1 PYTHONUNBUFFERED=1
export AML_TEST_DIRECT="${AML_TEST_DIRECT:-1}"
export G16_SCRIPT_EXEC="${G16_SCRIPT_EXEC:-1}"
export GPY16_FAST="${GPY16_FAST:-1}"
export GPY16_CACHE="${GPY16_CACHE:-1}"
mkdir -p "$NEXUS_STATE_DIR"

_aml_nexus_libs=(
  nexus-common.sh eternal-vigil.sh entropy-oracle.sh shadow-reality.sh
  self-defense.sh device-whitelist.sh ultra-stealth.sh predictive-guard.sh
  network-lockdown.sh threat-vectors.sh packet-oracle.sh threat-panel.sh
  firewall-sentinel.sh firewall-trust.sh seal-vault.sh tamper-guard.sh
  znetwork-field.sh nexus-settings.sh adblock-loader.sh host-attack.sh
  field-attack-kit.sh
)
for _lib in "${_aml_nexus_libs[@]}"; do
  # shellcheck source=/dev/null
  source "${ROOT}/lib/${_lib}" 2>/dev/null || true
done
nexus_ensure_dirs 2>/dev/null || true
panel="${ROOT}/panel/threat-panel.html"
sg="${SG_ROOT}"

aml_py() {
  local mod="$1"
  shift
  local stem
  stem="$(basename "${mod%.py}")"
  if [[ -x "${ROOT}/lib/bin/${stem}" ]]; then
    "${ROOT}/lib/bin/${stem}" "$@"
    return $?
  fi
  local py=python3
  if [[ "${AML_TEST_DIRECT:-0}" != "1" ]] && command -v pythong >/dev/null 2>&1; then
    py=pythong
  fi
  local path="${ROOT}/lib/${mod}"
  [[ -f "$path" ]] || path="${ROOT}/lib/$(basename "$mod")"
  "$py" "$path" "$@"
}

aml_tmp_state() {
  mktemp -d "${TMPDIR:-/tmp}/aml-state.XXXXXX"
}

PY=python3
if [[ "${AML_TEST_DIRECT:-0}" != "1" ]] && command -v pythong >/dev/null 2>&1; then
  PY=pythong
fi
export PY

aml_hard_root="${ROOT}"
# Rewrite legacy absolute install paths in inherited snippets.
_aml_rewrite_path() {
  local s="$1"
  s="${s//\/home\/default\/Desktop\/SG\/NewLatest/${ROOT}}"
  printf '%s' "$s"
}