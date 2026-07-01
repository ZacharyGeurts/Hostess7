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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/ammoos-update-inplace.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# AmmoLang subfolder route — AML_BUILD=1 (default)
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" ammoos_update "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

# AmmoOS in-place update — safe wrapper around nexus-update-apply.sh + post hooks.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
export AMMOOS_GITHUB_REPO="${AMMOOS_GITHUB_REPO:-ZacharyGeurts/AmmoOS}"
export AMMOOS_UPDATE_MODE="${AMMOOS_UPDATE_MODE:-git_tree}"

PY="${NEXUS_PYTHONG:-pythong}"
command -v "$PY" >/dev/null 2>&1 || PY="python3"

cmd="${1:-check}"
case "$cmd" in
  check|status)
    if [[ "${AML_BUILD:-1}" != "0" && -f "${ROOT}/lib/ammolang-run.sh" ]]; then
      exec bash "${ROOT}/lib/ammolang-run.sh" ammoos_update
    fi
    exec "$PY" "${ROOT}/lib/ammoos-update-inplace.py" "$@"
    ;;
  doctrine|source-root|components|preflight|post-update|log)
    exec "$PY" "${ROOT}/lib/ammoos-update-inplace.py" "$@"
    ;;
  apply)
    shift
    # shellcheck source=/dev/null
    source "${ROOT}/lib/nexus-common.sh" 2>/dev/null || true
    nexus_init_runtime_paths 2>/dev/null || true
    # shellcheck source=/dev/null
    [[ -f "${ROOT}/lib/nexus-update-lock.sh" ]] && source "${ROOT}/lib/nexus-update-lock.sh"
    upd="$("$PY" "${ROOT}/lib/ammoos-update-inplace.py" check --force)"
    target="$(printf '%s' "$upd" | python3 -c "import json,sys; print(json.load(sys.stdin).get('latest',''))")"
    previous="$(printf '%s' "$upd" | python3 -c "import json,sys; print(json.load(sys.stdin).get('previous',''))")"
    mode="$(printf '%s' "$upd" | python3 -c "import json,sys; print(json.load(sys.stdin).get('update_mode','git_tree'))")"
    tarball="$(printf '%s' "$upd" | python3 -c "import json,sys; print(json.load(sys.stdin).get('source_tarball',''))")"
    git_dir="$("$PY" "${ROOT}/lib/ammoos-update-inplace.py" source-root | python3 -c "import json,sys; print(json.load(sys.stdin).get('source_root',''))")"
    token="${NEXUS_UPDATE_LOCK_TOKEN:-}"
    if [[ -z "$token" ]]; then
      acq="$(python3 "${ROOT}/lib/nexus-update-lock.py" acquire --holder=ammoos-cli --phase=git_fetch --target="$target" --previous="$previous")"
      token="$(printf '%s' "$acq" | python3 -c "import json,sys; print(json.load(sys.stdin).get('token',''))")"
    fi
    export NEXUS_UPDATE_LOCK_TOKEN="$token"
    export NEXUS_UPDATE_TARGET="$target"
    export NEXUS_UPDATE_PREVIOUS="$previous"
    export NEXUS_UPDATE_MODE="$mode"
    export NEXUS_UPDATE_GIT_DIR="$git_dir"
    export NEXUS_UPDATE_TARBALL_URL="$tarball"
    export NEXUS_FIELD_STANDALONE="${NEXUS_FIELD_STANDALONE:-1}"
    bash "${ROOT}/lib/nexus-update-apply.sh"
    "$PY" "${ROOT}/lib/ammoos-update-inplace.py" post-update
    ;;
  *)
    echo '{"error":"usage","cmds":["check","apply","doctrine","components","preflight","post-update"]}' >&2
    exit 1
    ;;
esac
