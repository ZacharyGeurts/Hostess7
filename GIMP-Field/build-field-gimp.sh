#!/usr/bin/env bash
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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" gimp_field_build "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

# AmmoOS Image 1.0 build — meson + g16 field_opt; RTX autodetect gates GPU tools at runtime.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OVERLAY="${ROOT}/GIMP-Field"
TREE="${AMMOOS_GIMP_TREE:-${OVERLAY}/tree}"
GIMP="${GIMP_ROOT:-${ROOT}/GIMP}"
INSTALL="${NEXUS_INSTALL_ROOT:-${ROOT}/NewLatest}"
STATE="${NEXUS_STATE_DIR:-${INSTALL}/.nexus-state}"
BUILD="${OVERLAY}/build"
GROK16="${GROK16_ROOT:-${ROOT}/Grok16}"
PROFILE="${GROK16_FIELD_PROFILE:-field_opt}"

export SG_ROOT="${SG_ROOT:-${ROOT}}"
export PATH="${GROK16}/bin:${GROK16}/libexec/grok16:${PATH}"

# RTX gate — downgrade profile when no RTX (CPU path always available)
RTX_GATE="${OVERLAY}/forge/rtx-content-gate.py"
if [[ -f "${RTX_GATE}" ]]; then
  GATE_JSON="$(pythong "${RTX_GATE}" json 2>/dev/null || python3 "${RTX_GATE}" json 2>/dev/null || echo '{}')"
  if echo "${GATE_JSON}" | grep -q '"permit_rtx": true'; then
    PROFILE="${GROK16_FIELD_PROFILE:-queen_rtx}"
  else
    PROFILE="field_opt"
    echo "ammoos-image: no RTX — field_opt CPU build (gated tools hidden at runtime)" >&2
  fi
fi

# Ensure rewritten tree
REWRITE="${OVERLAY}/forge/field-gimp-rewrite.py"
if [[ ! -d "${TREE}/meson.build" && ! -f "${TREE}/meson.build" ]]; then
  [[ -f "${REWRITE}" ]] && pythong "${REWRITE}" rewrite 2>/dev/null || python3 "${REWRITE}" rewrite 2>/dev/null || true
fi
SRC="${TREE}"
[[ -f "${SRC}/meson.build" ]] || SRC="${GIMP}"

if [[ ! -f "${SRC}/meson.build" ]]; then
  echo "ERROR: no meson.build in ${SRC} — run forge/clone-upstream.sh" >&2
  exit 1
fi

mkdir -p "${BUILD}"
cd "${BUILD}"

CC_BIN="gcc"
CXX_BIN="g++"
if [[ -x "${GROK16}/bin/g16" ]]; then
  CC_BIN="${GROK16}/bin/g16"
  CXX_BIN="${GROK16}/bin/g++16"
  [[ -x "${CXX_BIN}" ]] || CXX_BIN="${GROK16}/bin/g16"
fi

MESON_ARGS=(
  "${SRC}"
  --prefix="${INSTALL}/ammoos-image"
  -Dbuildtype=debugoptimized
  -Denable-default-bin=enabled
)

if [[ -f "${OVERLAY}/meson/ammoos-native.ini" && -x "${CC_BIN}" ]]; then
  MESON_ARGS+=(--native-file "${OVERLAY}/meson/ammoos-native.ini")
fi

if [[ ! -f build.ninja ]]; then
  CC="${CC_BIN}" CXX="${CXX_BIN}" \
    GROK16_FIELD_PROFILE="${PROFILE}" \
    meson setup "${BUILD}" "${MESON_ARGS[@]}" \
    2>&1 | tee "${OVERLAY}/build/configure.log" || {
      echo "WARN: meson setup needs host GTK/GEGL deps — bridge + rewrite still active" >&2
      pythong "${INSTALL}/lib/field-gimp-bridge.py" build 2>/dev/null || true
      echo "{\"ok\":false,\"phase\":\"configure_hold\",\"profile\":\"${PROFILE}\"}"
      exit 0
    }
fi

ninja -C "${BUILD}" 2>&1 | tee -a "${OVERLAY}/build/build.log" || {
  echo "WARN: ninja build incomplete — field bridge active" >&2
}

pythong "${INSTALL}/lib/field-gimp-bridge.py" build 2>/dev/null \
  || python3 "${INSTALL}/lib/field-gimp-bridge.py" build 2>/dev/null \
  || true

echo "{\"ok\":true,\"product\":\"AmmoOS Image\",\"version\":\"1.0.0\",\"profile\":\"${PROFILE}\",\"build\":\"${BUILD}\"}"
