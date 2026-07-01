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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/integrate-amouranthrtx.sh" "$@"
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

# Integrate AMOURANTHRTX — wire, SPIR-V shaders, desktop handlers, engine path.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"
BUILD=0
for arg in "$@"; do [[ "$arg" == "--build" ]] && BUILD=1; done

# shellcheck source=/dev/null
source "${ROOT}/lib/sg-paths.sh"
sg_paths_export_defaults

RTX="${AMOURANTHRTX_ROOT:-${ROOT}/AMOURANTHRTX}"
STATE="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
OPEN="${ROOT}/scripts/amouranthrtx-open.sh"
DESKTOP_DIR="${HOME}/.local/share/applications"
MIME_DIR="${HOME}/.local/share/mime/packages"

log() { printf '[integrate-amouranthrtx] %s\n' "$*"; }

[[ -d "$RTX" ]] || {
  log "ERROR: AMOURANTHRTX missing — run scripts/wire-stack.sh"
  exit 1
}

echo "=== AMOURANTHRTX integrate (canonical: ${RTX}) ==="

# Compile bundled SPIR-V (glslc → assets/shaders/)
if command -v glslc >/dev/null 2>&1 && [[ -f "${RTX}/Navigator/shaders/Makefile" ]]; then
  log "SPIR-V shader pack"
  make -C "${RTX}/Navigator/shaders" BUILD_TYPE=Debug -j"$(nproc)" 2>&1 | tail -5 || log "WARN shader make partial"
  pythong "${RTX}/Navigator/shaders/compute/sync_canvas_shaders.py" 2>/dev/null || \
    python3 "${RTX}/Navigator/shaders/compute/sync_canvas_shaders.py" 2>/dev/null || true
else
  log "WARN glslc missing — skip shader compile (install: vulkan-tools)"
fi

resolve_binary() {
  local c
  for c in \
    "${ROOT}/Queen/build/rtx/bin/Linux/queen-browser" \
    "${RTX}/build-release/bin/Kilroy/AMOURANTHRTX" \
    "${RTX}/build/bin/Kilroy/AMOURANTHRTX"; do
    [[ -x "$c" ]] && { printf '%s\n' "$c"; return 0; }
  done
  return 1
}

BIN="$(resolve_binary || true)"
if [[ "$BUILD" -eq 1 || -z "$BIN" ]]; then
  if [[ -x "${ROOT}/Queen/scripts/g16-build.sh" ]]; then
    log "g16-build queen-browser RTX"
    bash "${ROOT}/Queen/scripts/g16-build.sh" build 2>&1 | tail -8 || log "WARN g16-build partial"
    BIN="$(resolve_binary || true)"
  fi
  if [[ -z "$BIN" && -x "${RTX}/kilroy.sh" ]]; then
    log "kilroy.sh release build"
    bash "${RTX}/kilroy.sh" release 2>&1 | tail -8 || log "WARN kilroy build partial"
    BIN="$(resolve_binary || true)"
  fi
fi

mkdir -p "${STATE}" "${ROOT}/bin" "$DESKTOP_DIR" "$MIME_DIR"

[[ -x "$OPEN" ]] && ln -sfn "$OPEN" "${ROOT}/bin/amouranthrtx-open" 2>/dev/null || true

# MIME — double-click .comp and .spv
cat >"${MIME_DIR}/amouranthrtx-shaders.xml" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/x-spirv">
    <comment>SPIR-V shader module</comment>
    <glob pattern="*.spv"/>
    <icon name="application-x-executable"/>
  </mime-type>
  <mime-type type="application/x-glsl-compute">
    <comment>GLSL compute shader (Vulkan)</comment>
    <glob pattern="*.comp"/>
    <icon name="text-x-script"/>
  </mime-type>
</mime-info>
XML
update-mime-database "${HOME}/.local/share/mime" 2>/dev/null || true

ENGINE_EXEC="${BIN:-${RTX}/kilroy.sh run}"
OPEN_EXEC="${OPEN} %f"

write_desktop() {
  local path="$1" name="$2" mime="$3" comment="$4"
  cat >"$path" <<EOF
[Desktop Entry]
Type=Application
Name=${name}
GenericName=AMOURANTHRTX Field Die
Comment=${comment}
Exec=${OPEN_EXEC}
Icon=${RTX}/assets/textures/ammo.png
Terminal=false
MimeType=${mime};
Categories=Game;Development;Graphics;
StartupWMClass=com.amouranth.rtx
Keywords=amouranth;rtx;vulkan;spirv;compute;shader;game;
EOF
  chmod +x "$path" 2>/dev/null || true
}

write_desktop "${DESKTOP_DIR}/amouranthrtx-engine.desktop" \
  "AMOURANTHRTX Field Die" "" "RTX field computer — games, DOS, GPU canvas"
write_desktop "${DESKTOP_DIR}/amouranthrtx-spv.desktop" \
  "Open SPIR-V in AMOURANTHRTX" "application/x-spirv" "Double-click SPIR-V — run on Field Die"
write_desktop "${DESKTOP_DIR}/amouranthrtx-comp.desktop" \
  "Open Compute Shader in AMOURANTHRTX" "application/x-glsl-compute" "Double-click .comp — glslc + Field Die"

if command -v xdg-mime >/dev/null 2>&1; then
  xdg-mime default amouranthrtx-spv.desktop application/x-spirv 2>/dev/null || true
  xdg-mime default amouranthrtx-comp.desktop application/x-glsl-compute 2>/dev/null || true
fi

python3 - <<PY
import json, os
from pathlib import Path
root = Path("${ROOT}")
rtx = Path("${RTX}")
state = Path("${STATE}")
doc = {
    "schema": "amouranthrtx-integration/v1",
    "canonical_root": "NewLatest/AMOURANTHRTX",
    "repo": "https://github.com/ZacharyGeurts/AMOURANTHRTX",
    "rtx_root": str(rtx),
    "binary": "${BIN}",
    "open_handler": "${OPEN}",
    "shaders": "Navigator/shaders → assets/shaders/compute/*.spv",
    "double_click": [".spv", ".comp"],
    "env": {
        "AMOURANTHRTX_CANVAS": "basename without extension",
        "AMOURANTHRTX_ROOT": str(rtx),
    },
    "build": {
        "queen": "Queen/scripts/g16-build.sh",
        "native": "AMOURANTHRTX/kilroy.sh",
        "shaders": "make -C Navigator/shaders",
    },
    "pairing": {
        "grok16": "5.1.0",
        "vulkan_doctrine": "data/vulkan-os-doctrine.json",
    },
}
state.mkdir(parents=True, exist_ok=True)
(state / "amouranthrtx-integration.json").write_text(json.dumps(doc, indent=2) + "\\n", encoding="utf-8")
(root / "data" / "amouranthrtx-integration.json").write_text(json.dumps(doc, indent=2) + "\\n", encoding="utf-8")
print("wrote amouranthrtx-integration.json")
PY

cat >"${STATE}/amouranthrtx-integrated.env" <<EOF
# AMOURANTHRTX integrated — $(date -u +%Y-%m-%dT%H:%M:%SZ)
export AMOURANTHRTX_ROOT="${RTX}"
export AMOURANTHRTX_BIN="${BIN}"
export AMOURANTHRTX_OPEN="${OPEN}"
EOF

log "AMOURANTHRTX integrate OK"
log "  root:    ${RTX}"
log "  binary:  ${BIN:-not built — ./scripts/integrate-amouranthrtx.sh --build}"
log "  open:    ${OPEN} <file.comp|file.spv>"
log "  desktop: ${DESKTOP_DIR}/amouranthrtx-*.desktop"
log "  env:     ${STATE}/amouranthrtx-integrated.env"
