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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/amouranthrtx-open.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" amouranthrtx_integrate "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

# Open .comp / .spv with AMOURANTHRTX — compile, stage SPIR-V, launch field die.
set -euo pipefail

FILE="${1:-}"
[[ -n "$FILE" && -f "$FILE" ]] || {
  echo "usage: amouranthrtx-open.sh <file.comp|file.spv>" >&2
  exit 1
}

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/lib/sg-paths.sh"
sg_paths_export_defaults

RTX="${AMOURANTHRTX_ROOT:-${ROOT}/AMOURANTHRTX}"
CACHE="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}/amouranthrtx/shaders"
GLSLC="${GLSLC:-$(command -v glslc || true)}"
SPIRV_VAL="${SPIRV_VAL:-$(command -v spirv-val || true)}"

abs="$(cd "$(dirname "$FILE")" && pwd)/$(basename "$FILE")"
base="$(basename "$abs")"
stem="${base%.*}"
ext="${base##*.}"
ext_lower="${ext,,}"

log() { printf '[amouranthrtx-open] %s\n' "$*"; }

resolve_binary() {
  local c
  for c in \
    "${ROOT}/Queen/build/rtx/bin/Linux/queen-browser" \
    "${ROOT}/Queen/build/rtx/bin/Linux/amouranth_engine" \
    "${RTX}/build-release/bin/Kilroy/AMOURANTHRTX" \
    "${RTX}/build/bin/Kilroy/AMOURANTHRTX"; do
    [[ -x "$c" ]] && { printf '%s\n' "$c"; return 0; }
  done
  return 1
}

compile_comp() {
  local src="$1" out="$2"
  [[ -n "$GLSLC" ]] || { log "ERROR: glslc missing — install vulkan-tools"; exit 1; }
  mkdir -p "$(dirname "$out")"
  local -a inc=(
    -I"${RTX}/Navigator/shaders/compute"
    -I"${RTX}/Navigator/shaders/raytracing"
  )
  log "glslc $src → $out"
  "$GLSLC" "${inc[@]}" --target-spv=spv1.6 --target-env=vulkan1.4 \
    -fshader-stage=comp "$src" -o "$out"
  [[ -z "$SPIRV_VAL" ]] || "$SPIRV_VAL" --target-env vulkan1.4 "$out" 2>/dev/null || true
}

stage_spv() {
  local spv="$1" name="$2"
  local dest_compute="${RTX}/assets/shaders/compute/${name}.spv"
  local cache_copy="${CACHE}/${name}.spv"
  mkdir -p "${RTX}/assets/shaders/compute" "$CACHE"
  cp -f "$spv" "$dest_compute"
  if [[ "$(readlink -f "$spv" 2>/dev/null || echo "$spv")" != "$(readlink -f "$cache_copy" 2>/dev/null || echo "$cache_copy")" ]]; then
    cp -f "$spv" "$cache_copy"
  fi
  log "staged ${dest_compute}"
}

BIN="$(resolve_binary || true)"
if [[ -z "$BIN" ]]; then
  log "engine not built — run: ${ROOT}/scripts/integrate-amouranthrtx.sh --build"
  exit 1
fi

SPV=""
case "$ext_lower" in
  comp)
    SPV="${CACHE}/${stem}.spv"
    compile_comp "$abs" "$SPV"
    ;;
  spv)
    SPV="$abs"
    ;;
  *)
    log "ERROR: unsupported type .$ext (want .comp or .spv)"
    exit 1
    ;;
esac

stage_spv "$SPV" "$stem"

export AMOURANTHRTX_ROOT="$RTX"
export AMOURANTHRTX_CANVAS="$stem"
export AMOURANTHRTX_CANVAS_FILE="$abs"
export AMOURANTHRTX_NO_VALIDATION=1

log "launch $BIN canvas=$stem"
exec "$BIN"
