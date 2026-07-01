#!/usr/bin/env bash
# Configure Field OBS upstream with Grok16 g16 toolchain + AmmoOS overlay.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OVERLAY="${ROOT}/OBS-Field"
UP="${OBS_UPSTREAM_DIR:-${OVERLAY}/upstream/obs-studio}"
BUILD="${OVERLAY}/build"
PREFIX="${FIELD_OBS_PREFIX:-${OVERLAY}/prefix}"
GROK16="${GROK16_ROOT:-${ROOT}/Grok16}"
PROFILE="${GROK16_FIELD_PROFILE:-field_opt}"
TOOLCHAIN="${GROK16}/cmake/grok16-toolchain.cmake"
OVERLAY_CMAKE="${OVERLAY}/cmake/g16-field-obs.cmake"

export SG_ROOT="${SG_ROOT:-${ROOT}}"
export PATH="${GROK16}/bin:${GROK16}/libexec/grok16:${PATH}"

if [[ ! -f "${UP}/CMakeLists.txt" ]]; then
  echo "ERROR: upstream missing — run OBS-Field/forge/clone-upstream.sh" >&2
  exit 1
fi

mkdir -p "${BUILD}" "${PREFIX}"
cd "${BUILD}"

CMAKE_ARGS=(
  -S "${UP}"
  -B "${BUILD}"
  -DCMAKE_INSTALL_PREFIX="${PREFIX}"
  -DCMAKE_BUILD_TYPE=RelWithDebInfo
  -DENABLE_UI=ON
  -DENABLE_SCRIPTING=OFF
  -DLINUX_PORTABLE=ON
  -DBUILD_FOR_DISTRIBUTION=OFF
  -DFIELD_OBS_OVERLAY=ON
  -DFIELD_OBS_G16_PROFILE="${PROFILE}"
)

if [[ -f "${TOOLCHAIN}" && -x "${GROK16}/bin/g16" ]]; then
  CMAKE_ARGS+=(
    -DCMAKE_TOOLCHAIN_FILE="${TOOLCHAIN}"
    -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES="${OVERLAY_CMAKE}"
  )
  echo "field-obs: configuring with g16 @ ${PROFILE}" >&2
else
  echo "WARN: g16 not ready — host compiler configure (bridge + portable still active)" >&2
fi

cmake "${CMAKE_ARGS[@]}" 2>&1 | tee "${OVERLAY}/build/configure.log"
echo "configure_ok: ${BUILD}"