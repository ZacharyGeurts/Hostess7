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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/integrate-ammocode.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Integrate AmmoCode Stack — wire, filetypes DB, Grok16, desktop open handlers.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"
STATE="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
DESKTOP_DIR="${HOME}/.local/share/applications"
MIME_DIR="${HOME}/.local/share/mime/packages"

# shellcheck source=/dev/null
source "${ROOT}/lib/sg-paths.sh"
sg_paths_export_defaults

AMMO="${AMMOCODE_ROOT:-${ROOT}/AmmoCode}"
G16="${GROK16_ROOT:-${ROOT}/Grok16}"

log() { printf '[integrate-ammocode] %s\n' "$*"; }

[[ -d "$AMMO" ]] || {
  log "ERROR: AmmoCode missing at ${AMMO} — run scripts/wire-stack.sh"
  exit 1
}

echo "=== AmmoCode Stack integrate (canonical: ${AMMO}) ==="

bash "${ROOT}/scripts/sync-programming-filetypes.sh" 2>&1 | tail -5

mkdir -p "${STATE}" "${ROOT}/bin" "$DESKTOP_DIR" "$MIME_DIR"
chmod +x "${AMMO}/scripts/ammocode-open.sh" 2>/dev/null || true
chmod +x "${ROOT}/scripts/sg-code-open.sh" 2>/dev/null || true
ln -sfn "${AMMO}/scripts/ammocode-open.sh" "${ROOT}/bin/ammocode-open" 2>/dev/null || true
ln -sfn "${ROOT}/scripts/sg-code-open.sh" "${ROOT}/bin/sg-code-open" 2>/dev/null || true

if [[ -f "${G16}/data/g16-ammocode-field-doctrine.json" ]]; then
  python3 - <<PY
import json
from pathlib import Path
g16 = Path("${G16}/data/g16-ammocode-field-doctrine.json")
doc = json.loads(g16.read_text(encoding="utf-8"))
doc["ammocode_root"] = "NewLatest/AmmoCode"
doc["filetypes_db"] = "NewLatest/data/field-programming-filetypes.json"
doc["stack_version"] = "6.0.0"
g16.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
PY
fi

# Desktop — code files → sg-code-open (ask: Run / Compile / AmmoCode)
CODE_EXTS="*.c *.h *.cpp *.cc *.cxx *.hpp *.py *.pyw *.js *.mjs *.ts *.tsx *.rs *.go *.zig *.java *.kt *.kts *.sh *.bash *.zsh *.pl *.rb *.php *.lua *.asm *.s *.S *.comp *.spv *.fld *.aml *.g16 *.launch *.md *.json *.yaml *.yml *.toml *.sql *.vue *.svelte"
cat >"${MIME_DIR}/sg-code-files.xml" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="text/x-sg-code">
    <comment>SG stack source code</comment>
    <sub-class-of type="text/plain"/>
  </mime-type>
</mime-info>
XML
update-mime-database "${HOME}/.local/share/mime" 2>/dev/null || true

cat >"${DESKTOP_DIR}/sg-code-open.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Open in SG Stack
GenericName=Run G16 or AmmoCode
Comment=Run with G16, Compile, or open in AmmoCode Stack
Exec=${ROOT}/scripts/sg-code-open.sh %f
Icon=${AMMO}/assets/textures/ammo.png
Terminal=false
MimeType=text/x-c;text/x-c++;text/x-python;text/x-shellscript;text/x-java;text/x-rust;text/x-go;text/javascript;text/typescript;application/x-glsl-compute;application/x-spirv;
Categories=Development;TextEditor;
Keywords=g16;ammocode;grok16;compile;code;
EOF
chmod +x "${DESKTOP_DIR}/sg-code-open.desktop" 2>/dev/null || true

cat >"${DESKTOP_DIR}/ammocode-stack.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=AmmoCode Stack
GenericName=Grok16 Editor
Comment=AmmoCode 6 — 243 filetypes, G16 run/compile
Exec=${AMMO}/scripts/ammocode-open.sh
Icon=${AMMO}/assets/textures/ammo.png
Terminal=false
Categories=Development;TextEditor;IDE;
Keywords=ammocode;g16;grok16;editor;
EOF
chmod +x "${DESKTOP_DIR}/ammocode-stack.desktop" 2>/dev/null || true

# Default handler for common code MIME types (Run / Compile / AmmoCode chooser)
if command -v xdg-mime >/dev/null 2>&1; then
  for mime in text/x-c text/x-c++ text/x-python text/x-shellscript text/x-java \
    text/x-rust text/x-go text/javascript text/typescript application/x-glsl-compute \
    application/x-spirv text/x-sg-code; do
    xdg-mime default sg-code-open.desktop "$mime" 2>/dev/null || true
  done
  log "xdg-mime defaults → sg-code-open.desktop (logout may be required)"
fi

if [[ -f "${AMMO}/data/ammocode-version.json" ]]; then
  install -m 644 "${AMMO}/data/ammocode-version.json" "${STATE}/ammocode-version.json"
fi

cat >"${STATE}/ammocode-integrated.env" <<EOF
# AmmoCode Stack integrated — $(date -u +%Y-%m-%dT%H:%M:%SZ)
export AMMOCODE_ROOT="${AMMO}"
export GROK16_ROOT="${G16}"
export AMMOCODE_PORT="${AMMOCODE_PORT:-9555}"
export AMMOCODE_URL="http://127.0.0.1:\${AMMOCODE_PORT}/"
export SG_CODE_DEFAULT="\${SG_CODE_DEFAULT:-ask}"
export FILETYPES_DB="${ROOT}/data/field-programming-filetypes.json"
EOF

log "AmmoCode Stack integrate OK"
log "  root:      ${AMMO}"
log "  g16:       ${G16}"
log "  filetypes: ${ROOT}/data/field-programming-filetypes.json"
log "  gui:       http://127.0.0.1:${AMMOCODE_PORT:-9555}/"
log "  code-open: ${ROOT}/scripts/sg-code-open.sh <file>"
log "  env:       ${STATE}/ammocode-integrated.env"