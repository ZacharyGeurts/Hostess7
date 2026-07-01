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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Queen/scripts/g16-build.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Queen RTX build — g16 + Ninja only (no cmake --build).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SG="$(cd "${ROOT}/../.." && pwd)"
export SG_ROOT="${SG_ROOT:-$SG}"
export QUEEN_ROOT="${ROOT}"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export GROK16_ROOT="${GROK16_ROOT:-${NEXUS_INSTALL_ROOT:-$SG/NewLatest}/Grok16}"
export G16_PREFIX="${G16_PREFIX:-$GROK16_ROOT}"
export GROK16_CMAKE_SOURCE="${GROK16_CMAKE_SOURCE:-$SG/AMOURANTHRTX}"
export GROK16_CMAKE_BUILD="${GROK16_CMAKE_BUILD:-$ROOT/build/rtx}"
export GROK16_CMAKE_TARGET="${GROK16_CMAKE_TARGET:-amouranth_engine}"
export GROK16_FIELD_PROFILE="${GROK16_FIELD_PROFILE:-queen_rtx}"
export GROK16_BUILD_JOBS="${GROK16_BUILD_JOBS:-${QUEEN_BUILD_JOBS:-2}}"
export PATH="${GROK16_ROOT}/bin:${GROK16_ROOT}/libexec/grok16:${PATH}"

FIELD_CMAKE="${GROK16_ROOT}/scripts/field-cmake.sh"
THERMAL_BRIDGE="${GROK16_ROOT}/scripts/nexus-thermal-bridge.sh"
[[ -f "$FIELD_CMAKE" ]] || { echo "g16-build: missing $FIELD_CMAKE" >&2; exit 1; }
if [[ -f "$THERMAL_BRIDGE" ]]; then
  bash "$THERMAL_BRIDGE" || echo "g16-build: thermal bridge warn (continuing)" >&2
fi
[[ -x "${GROK16_ROOT}/bin/g16" ]] || { echo "g16-build: g16 not ready — run ${GROK16_ROOT}/scripts/grok16-toolchain.sh install" >&2; exit 1; }

_g16_combinatronics_gate() {
  local gpy="${GPY16_DRIVER:-$SG/GrokPy/bin/gpy-16}"
  [[ -x "$gpy" ]] || gpy="$SG/PythonG/bin/pythong"
  [[ -x "$gpy" ]] || return 0
  [[ -f "$GROK16_ROOT/lib/g16-compile-combinatronics.py" ]] || return 0
  local gate
  gate="$("$gpy" "$GROK16_ROOT/lib/g16-compile-combinatronics.py" gate 2>/dev/null)" || return 0
  local prof
  prof="$(printf '%s' "$gate" | "$gpy" -c 'import sys,json; d=json.load(sys.stdin); print(d.get("profile") or "")' 2>/dev/null || true)"
  if [[ -n "$prof" ]]; then
    export GROK16_FIELD_PROFILE="$prof"
    export G16_BENCH_PROFILE="$prof"
    echo "g16-build: combinatronics gate profile=$prof"
  fi
}

_g16_combinatronics_stamp() {
  local bin="$1"
  [[ -f "$bin" ]] || return 0
  local gpy="${GPY16_DRIVER:-$SG/GrokPy/bin/gpy-16}"
  [[ -x "$gpy" ]] || gpy="$SG/PythonG/bin/pythong"
  [[ -x "$gpy" ]] || return 0
  [[ -f "$GROK16_ROOT/lib/g16-compile-combinatronics.py" ]] || return 0
  "$gpy" "$GROK16_ROOT/lib/g16-compile-combinatronics.py" stamp "$bin" >/dev/null 2>&1 || true
}

_g16_rtx_gate() {
  local gpy="${GPY16_DRIVER:-$SG/GrokPy/bin/gpy-16}"
  [[ -x "$gpy" ]] || gpy="$SG/PythonG/bin/pythong"
  [[ -x "$gpy" ]] || return 0
  if ! "$gpy" "$GROK16_ROOT/forge/rtx_gate.py" check "${1:-queen_rtx}" >/dev/null 2>&1; then
    echo "g16-build: ${1:-queen_rtx} blocked — no RTX GPU (use: GROK16_FIELD_PROFILE=field_opt $0 build)" >&2
    echo "g16-build: override dev only: G16_RTX_GATE_FORCE=1" >&2
    return 1
  fi
  return 0
}

case "${1:-build}" in
  configure) shift; exec bash "$FIELD_CMAKE" configure "$@" ;;
  build)
    shift || true
    _g16_combinatronics_gate
    bash "$FIELD_CMAKE" g16-build "$@"
    rc=$?
    _g16_combinatronics_stamp "${GROK16_CMAKE_BUILD}/bin/Linux/queen-browser"
    exit "$rc"
    ;;
  rebuild)
    shift || true
    _g16_combinatronics_gate
    bash "$FIELD_CMAKE" rebuild "$@"
    rc=$?
    _g16_combinatronics_stamp "${GROK16_CMAKE_BUILD}/bin/Linux/queen-browser"
    exit "$rc"
    ;;
  status) exec bash "$FIELD_CMAKE" status ;;
  queen-rtx|full)
    shift || true
    _g16_combinatronics_gate
    _g16_rtx_gate queen_rtx || exit 1
    bash "$FIELD_CMAKE" queen-rtx "$@"
    rc=$?
    _g16_combinatronics_stamp "${GROK16_CMAKE_BUILD}/bin/Linux/queen-browser"
    exit "$rc"
    ;;
  -h|--help|help)
    cat <<EOF
Queen g16 build — compile queen-browser with g16 + Ninja (not cmake --build)

Usage:
  $0              Configure if needed, then ninja build amouranth_engine
  $0 build        Same as default
  $0 queen-rtx    Full queen-rtx configure + g16 ninja build
  $0 configure    CMake configure only (generates build.ninja for g16)
  $0 rebuild      Wipe cache, reconfigure, g16 ninja build
  $0 status       JSON status (g16 path, ninja, binary)

Environment:
  QUEEN_BUILD_JOBS / GROK16_BUILD_JOBS  Parallel jobs (default: 2)
  GROK16_ROOT                           Grok16 prefix
EOF
    exit 0
    ;;
  *) exec bash "$FIELD_CMAKE" g16-build "$@" ;;
esac