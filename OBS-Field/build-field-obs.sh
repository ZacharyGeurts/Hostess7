#!/usr/bin/env bash
# Field OBS build — cmake + g16 field_opt; RTX autodetect gates NVENC at runtime.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OVERLAY="${ROOT}/OBS-Field"
UP="${OBS_UPSTREAM_DIR:-${OVERLAY}/upstream/obs-studio}"
BUILD="${OVERLAY}/build"
PREFIX="${FIELD_OBS_PREFIX:-${OVERLAY}/prefix}"
GROK16="${GROK16_ROOT:-${ROOT}/Grok16}"
INSTALL="${NEXUS_INSTALL_ROOT:-${ROOT}/NewLatest}"
PROFILE="${GROK16_FIELD_PROFILE:-field_opt}"

export SG_ROOT="${SG_ROOT:-${ROOT}}"
export PATH="${GROK16}/bin:${GROK16}/libexec/grok16:${PATH}"

# RTX gate — prefer queen_rtx profile when RTX permits
RTX_GATE="${GROK16}/forge/rtx_gate.py"
if [[ -f "${RTX_GATE}" ]]; then
  GATE_JSON="$(pythong "${RTX_GATE}" json queen_rtx 2>/dev/null || python3 "${RTX_GATE}" json queen_rtx 2>/dev/null || echo '{}')"
  if echo "${GATE_JSON}" | grep -q '"permit": true'; then
    PROFILE="${GROK16_FIELD_PROFILE:-queen_rtx}"
  else
    PROFILE="field_opt"
    echo "field-obs: no RTX — field_opt CPU build (NVENC gated at runtime)" >&2
  fi
fi

if [[ ! -f "${UP}/CMakeLists.txt" ]]; then
  "${OVERLAY}/forge/clone-upstream.sh"
fi

CONFIGURE="${OVERLAY}/forge/configure-field-obs-g16.sh"
if [[ ! -f "${BUILD}/CMakeCache.txt" ]]; then
  GROK16_FIELD_PROFILE="${PROFILE}" bash "${CONFIGURE}" || {
    pythong "${INSTALL}/lib/field-obs.py" build 2>/dev/null || true
    echo "{\"ok\":false,\"phase\":\"configure_hold\",\"profile\":\"${PROFILE}\"}"
    exit 0
  }
fi

if command -v cmake >/dev/null 2>&1; then
  cmake --build "${BUILD}" -j"$(nproc 2>/dev/null || echo 4)" 2>&1 | tee -a "${OVERLAY}/build/build.log" || {
    echo "WARN: cmake build incomplete — field bridge + system OBS fallback active" >&2
  }
  cmake --install "${BUILD}" --prefix "${PREFIX}" 2>/dev/null || true
fi

pythong "${INSTALL}/lib/field-obs.py" build 2>/dev/null \
  || python3 "${INSTALL}/lib/field-obs.py" build 2>/dev/null \
  || true

echo "{\"ok\":true,\"product\":\"Field OBS\",\"profile\":\"${PROFILE}\",\"prefix\":\"${PREFIX}\",\"binary\":\"${PREFIX}/bin/obs\"}"